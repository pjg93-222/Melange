"""Retry only inconclusive 5xx/timeout observations from the 404 recheck."""
import asyncio
import contextlib
import json
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c
from playwright.async_api import async_playwright

async def main():
    root=c.OUTPUT_DEFAULT
    path=root/'api_recheck_observations_20260905.ndjson'
    latest={r['profile_uuid']:r for r in c.read_ndjson(path)}
    targets=[uuid for uuid,row in latest.items() if row.get('status') not in (200,404)]
    async with async_playwright() as pw:
        context,_,_=await c.browser_context(c.parse_args([]),pw)
        try:
            page=context.pages[0]
            await c.initialize_directory(page)
            for uuid in targets:
                for attempt in range(3):
                    raw=await asyncio.wait_for(page.evaluate(api.FETCH,uuid),25)
                    observation={'profile_uuid':uuid,'status':raw['status'],'observed_at':c.utc_now(),'source_api_url':raw['url']}
                    c.append_ndjson(path,[observation])
                    print(json.dumps(observation),flush=True)
                    if raw['status'] in (200,404):
                        if raw['status']==200:
                            c.append_ndjson(root/'api_projected_evidence_20260905.ndjson',[{'profile_uuid':uuid,'observed_at':observation['observed_at'],**raw}])
                        break
                    if raw['status'] in (400,401,403,429): raise RuntimeError('Access or rate response; stopped')
                    await asyncio.sleep(2)
        finally:
            for page in list(context.pages):
                with contextlib.suppress(Exception): await asyncio.wait_for(page.close(),3)
            with contextlib.suppress(Exception): await asyncio.wait_for(context.close(),5)

asyncio.run(main())
