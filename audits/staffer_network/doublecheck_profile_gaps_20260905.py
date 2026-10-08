"""Fresh source and rendered-page checks of records previously rejected as gaps."""
import asyncio
import contextlib
import hashlib
import json
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c
from playwright.async_api import async_playwright

DOM = r"""() => ({
  names:[...document.querySelectorAll('.profile-header__name')].map(x=>x.textContent.trim()),
  positions:[...document.querySelectorAll('.profile-header__desc')].map(x=>x.textContent.trim()),
  employment:[...document.querySelectorAll('.profile-employment-history__item')].map(x=>({
    employer:x.querySelector('.profile-employment-history__employer')?.textContent.trim() || '',
    title:x.querySelector('.profile-employment-history__title')?.textContent.trim() || '',
    dates:x.querySelector('.profile-employment-history__date')?.textContent.trim() || ''
  }))
})"""

async def main():
    root=c.OUTPUT_DEFAULT
    profiles=c.read_ndjson(root/'profiles.ndjson')
    by_id={r['profile_uuid']:r for r in profiles}
    directory=c.read_ndjson(c.DIRECTORY_DEFAULT)
    pending=[r for r in directory if r['profile_uuid'] not in by_id]
    old=c.read_ndjson(root/'api_projected_evidence_20260905.ndjson')
    latest={r['profile_uuid']:r for r in old}
    report={'generated_at':c.utc_now(),'fresh_api_checks':[],'rendered_checks':[]}
    async with async_playwright() as pw:
        context,_,_=await c.browser_context(c.parse_args([]),pw)
        try:
            page=context.pages[0]
            await c.initialize_directory(page)
            for expected in pending:
                uuid=expected['profile_uuid']
                raw=await asyncio.wait_for(page.evaluate(api.FETCH,uuid),25)
                prior=latest.get(uuid)
                data=raw.get('data',{})
                report['fresh_api_checks'].append({'profile_uuid':uuid,'expected_name':expected['name'],'status':raw['status'],
                    'same_projected_data_as_previous_observation':bool(prior and api.canonical(data)==api.canonical(prior['data'])),
                    'source_name':data.get('name',{}).get('displayName'),'api_person_id':data.get('id'),'api_lexicon_id':data.get('lexiconId'),
                    'employment_entries':len(data.get('employmentItems',[])),'current_position_entries':len(data.get('stafferPositions',[])),
                    'projected_data':data})
                await asyncio.sleep(0.5)
            examples=['30bcddb2-0a94-4c09-a7ba-74aec2e32fbb','5fa75588-542f-46b1-881b-18b2224741e6','049072ca-e56c-4e95-9bff-48cdcd5028cb']
            examples += [r['profile_uuid'] for r in pending if r['profile_uuid'] not in examples][:2]
            for uuid in examples:
                item={'profile_uuid':uuid,'source_url':c.PROFILE_BASE_URL+uuid}
                try:
                    await c.initialize_directory(page)
                    response=await page.goto(item['source_url'],wait_until='domcontentloaded',timeout=30000)
                    item['http_status']=response.status if response else None
                    await asyncio.sleep(2)
                    item['rendered']=await asyncio.wait_for(page.evaluate(DOM),10)
                except Exception as exc:
                    item['render_error']=type(exc).__name__
                    with contextlib.suppress(Exception): await asyncio.wait_for(page.close(),3)
                    page=await context.new_page()
                report['rendered_checks'].append(item)
                print(json.dumps(item),flush=True)
            c.atomic_json(root.parent/'PROFILE_GAP_DOUBLECHECK_20260905.json',report)
            print(json.dumps({'fresh_api_checks':len(report['fresh_api_checks']),'rendered_checks':len(report['rendered_checks'])}),flush=True)
        finally:
            for page in list(context.pages):
                with contextlib.suppress(Exception): await asyncio.wait_for(page.close(),3)
            with contextlib.suppress(Exception): await asyncio.wait_for(context.close(),5)

asyncio.run(main())
