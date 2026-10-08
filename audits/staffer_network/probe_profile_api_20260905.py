"""Bounded authenticated diagnostic; prints structure, never contact values."""
import asyncio
import json
import politico_profile_crawl_playwright as crawl
from playwright.async_api import async_playwright


async def main():
    args = crawl.parse_args(["--workers", "1"])
    async with async_playwright() as pw:
        context, _, _ = await crawl.browser_context(args, pw)
        try:
            page = context.pages[0]
            await crawl.initialize_directory(page)
            old = crawl.read_ndjson(crawl.OUTPUT_DEFAULT / 'profiles.ndjson')
            examples = [next(r for r in old if r.get('explicit_side_labels')), next(r for r in old if r.get('profile_issue_areas'))]
            for uuid in ['049072ca-e56c-4e95-9bff-48cdcd5028cb']:
                result = await page.evaluate("""async uuid => {
                    const r = await fetch('/proxy/lava/api/v1/person/' + uuid);
                    const data = await r.json();
                    function shape(x, depth=0) {
                      if (x === null) return null;
                      if (depth > 3) return typeof x;
                      if (Array.isArray(x)) return {length:x.length, sample:x.length?shape(x[0],depth+1):null};
                      if (typeof x === 'object') return Object.fromEntries(Object.entries(x).filter(([k])=> !/email|phone|address|contact|token|secret/i.test(k)).map(([k,v])=>[k,shape(v,depth+1)]));
                      return typeof x;
                    }
                    const allowed = new Set(['id','name','full','displayName','title','label','slug','startDate','endDate','employerName','institution','degree','stafferPositions','member','committee','stafferRoles','issueAreas','employmentItems','educationItems','side','majority','minority','party','stafferType','positionType']);
                    const project = x => Array.isArray(x)?x.map(project):x && typeof x==='object'?Object.fromEntries(Object.entries(x).filter(([k])=>allowed.has(k)).map(([k,v])=>[k,project(v)])):x;
                    return {status:r.status, keys:Object.keys(data), positionsShape:shape(data.stafferPositions), modeled:project(data)};
                }""", uuid)
                print(json.dumps({"uuid":uuid, **result}), flush=True)
        finally:
            for p in list(context.pages):
                try:
                    await asyncio.wait_for(p.close(), 3)
                except Exception:
                    pass
            try:
                await asyncio.wait_for(context.close(), 5)
            except Exception:
                pass


asyncio.run(main())
