"""Inspect live directory search surfaces for replacement-profile checks."""
import asyncio
import contextlib
import json
from urllib.parse import urlsplit,parse_qs
import politico_profile_crawl_playwright as c
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as pw:
        context,_,_=await c.browser_context(c.parse_args([]),pw)
        try:
            page=context.pages[0]
            observed=[]
            def on_request(req):
                u=urlsplit(req.url)
                if u.hostname=='directory.politicopro.com' and '/proxy/' in u.path:
                    observed.append({'method':req.method,'path':u.path,'query_keys':list(parse_qs(u.query))})
                    if u.path=='/proxy/sail/sail/api/v1/search':
                        print(json.dumps({'search_request':req.post_data_json}),flush=True)
            async def on_response(response):
                if urlsplit(response.url).path=='/proxy/sail/sail/api/v1/search':
                    data=await response.json()
                    def shape(x,depth=0):
                        if depth>4: return type(x).__name__
                        if isinstance(x,dict): return {k:shape(v,depth+1) for k,v in x.items()}
                        if isinstance(x,list): return {'length':len(x),'first':shape(x[0],depth+1) if x else None}
                        return type(x).__name__
                    print(json.dumps({'search_response_shape':shape(data)}),flush=True)
                    hit=data['results'][0]['hits'][0]
                    print(json.dumps({'person_shape':shape(hit.get('person')),'id':hit.get('id'),'identifiers':hit.get('identifiers')}),flush=True)
                    person=hit.get('person') or {}
                    print(json.dumps({'person_identity':{k:v for k,v in person.items() if k in ('id','lexiconId','name','displayName','slug')}}),flush=True)
            page.on('request',on_request)
            page.on('response',on_response)
            await c.initialize_directory(page)
            print(json.dumps({'requests':observed}),flush=True)
            print(json.dumps(await page.evaluate("""() => ({
              inputs:[],
              links:[...document.querySelectorAll('a[href*="/congress/staffer/"]')].slice(0,3).map(x=>({name:x.textContent.trim(),url:x.href}))
            })""")),flush=True)
        finally:
            for p in list(context.pages):
                with contextlib.suppress(Exception): await asyncio.wait_for(p.close(),3)
            with contextlib.suppress(Exception): await asyncio.wait_for(context.close(),5)

asyncio.run(main())
