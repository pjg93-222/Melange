"""Read-only canary diagnostics; never appends or changes crawl checkpoint data."""
import asyncio
import json
import contextlib
import re
from urllib.parse import urlsplit
from playwright.async_api import async_playwright
import politico_profile_crawl_playwright as crawl


async def main():
    args = crawl.parse_args([])
    rows = crawl.read_ndjson(args.output_dir / 'profiles.ndjson')
    good = next(row for row in reversed(rows) if row.get('employment_history'))
    missing = next((row for row in reversed(rows) if row.get('identity_status') == 'PROFILE_UNAVAILABLE_404'), None)
    if missing is None:
        missing = crawl.read_ndjson(args.output_dir / 'quarantine_api400_20260904T211000Z.ndjson')[-1]['row']
    excluded = {row['profile_uuid'] for row in rows}
    for audit_path in args.output_dir.glob('quarantine*.ndjson'):
        for entry in crawl.read_ndjson(audit_path):
            excluded.add(entry.get('row', entry).get('profile_uuid'))
    fresh = [row for row in crawl.read_ndjson(args.directory) if row['profile_uuid'] not in excluded][:2]
    with crawl.CrawlLock(args.output_dir / '.politico-python-crawl.lock'):
        async with async_playwright() as playwright:
            context, _, _ = await crawl.browser_context(args, playwright)
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_extra_http_headers({'Cache-Control': 'no-cache'})
            failures = []
            person_responses = []
            async def response_seen(response):
                if '/proxy/lava/api/v1/person/' in response.url:
                    person_responses.append(response.status)
                if response.status >= 400:
                    url = urlsplit(response.url)
                    try:
                        body = await response.text()
                    except Exception:
                        body = ''
                    safe_error = []
                    if url.path.startswith('/proxy/lava/'):
                        try:
                            payload = json.loads(body)
                            def collect_errors(value):
                                if isinstance(value, dict):
                                    for key, child in value.items():
                                        if key.lower() in {'error', 'message', 'detail', 'reason', 'description'} and isinstance(child, str):
                                            text = re.sub(r'[\w.+-]+@[\w.-]+', '[redacted-email]', child)
                                            text = re.sub(r'[A-Za-z0-9_+=/.-]{24,}', '[redacted-id]', text)
                                            safe_error.append(text[:250])
                                        elif isinstance(child, (dict, list)):
                                            collect_errors(child)
                                elif isinstance(value, list):
                                    for child in value: collect_errors(child)
                            collect_errors(payload)
                        except ValueError:
                            pass
                    # Emit fixed diagnostic categories, never raw response data.
                    markers = [label for label, pattern in {
                        'expired': r'expir', 'unauthorized': r'unauthoriz|not authenticated',
                        'token_error': r'invalid.{0,30}token|token.{0,30}invalid|jwt',
                        'csrf': r'csrf|xsrf', 'bad_request': r'bad request',
                        'large_headers': r'header.{0,30}(?:large|long)|cookie.{0,30}(?:large|long)',
                    }.items() if re.search(pattern, body, re.I)]
                    failures.append({'status': response.status, 'service': url.path.split('/')[2] if url.path.startswith('/proxy/') else url.hostname, 'markers': markers, 'safe_error': safe_error, 'body_length': len(body)})
            page.on('response', response_seen)
            try:
                await page.goto(crawl.DIRECTORY_URL, wait_until='domcontentloaded', timeout=30000)
                await asyncio.sleep(2)
                location = urlsplit(page.url)
                print(json.dumps({'event': 'NORMAL_DIRECTORY_NAVIGATION', 'host': location.hostname, 'path': location.path}), flush=True)
                for label, row in [('known_content', good), ('recent_unavailable', missing), *[(f'fresh_{i}', row) for i, row in enumerate(fresh)]]:
                    failures.clear()
                    person_responses.clear()
                    target_url = crawl.PROFILE_BASE_URL + row['profile_uuid']
                    if label != 'known_content':
                        await page.goto(crawl.DIRECTORY_URL, wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(2)
                        failures.clear()
                        person_responses.clear()
                    response = await page.goto(target_url, wait_until='domcontentloaded', timeout=30000)
                    for delay in (0, 2):
                        if delay:
                            await asyncio.sleep(delay)
                        snap = await asyncio.wait_for(page.evaluate(crawl.SNAPSHOT_SCRIPT), timeout=10)
                        print(json.dumps({'canary': label, 'delay': delay, 'document_status': response.status,
                            'names': len(snap.get('profile_names', [])), 'history': len(snap.get('employment_history', [])),
                            'education': len(snap.get('education', [])), 'flags': snap.get('flags'),
                            'person_response_statuses': person_responses, 'response_failures': failures}), flush=True)
            finally:
                for owned_page in context.pages:
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(owned_page.close(), timeout=3)
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(context.close(), timeout=10)


if __name__ == '__main__':
    asyncio.run(main())
