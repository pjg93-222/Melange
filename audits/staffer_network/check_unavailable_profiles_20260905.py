"""Audit unavailable IDs against fresh directory search and alternate numeric IDs.

Read-only against the source and canonical corpus; evidence goes to separate files.
Only identity and professional employment fields leave the browser.
"""
import asyncio
import contextlib
import hashlib
import json
import re
import time
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c
from playwright.async_api import async_playwright

SEARCH = r"""async ({start,limit,query}) => {
 const r=await fetch('/proxy/sail/sail/api/v1/search', {
  method:'POST',headers:{'Content-Type':'application/json'},signal:AbortSignal.timeout(30000),
  body:JSON.stringify({collections:['directory'],context:'pro:directory-state',query:query||'',dateFields:[],start,limit,
   fields:[{name:'DIRECTORY',values:['cd']},{name:'DIRECTORY_ENTRY_TYPE',values:['staffer']}],includeFacets:true})});
 if(r.status!==200) return {status:r.status,url:r.url};
 const data=await r.json(); const result=data.results[0];
 return {status:r.status,url:r.url,total:result.totalHitCount,hits:result.hits.map(h=>{
  const p=h.person||{};
  return {hit_id:h.id,id:p.id,lexiconId:p.lexiconId,link:p.link,displayName:p.displayName,
   firstName:p.firstName,lastName:p.lastName,employments:(p.employments||[]).map(e=>({employer:e.employer?.name,employerType:e.employer?.type,title:e.jobTitle}))};
 })};
}"""

def namekey(name):
    return re.sub(r'[^a-z0-9]','',(name or '').casefold())

async def main():
    root=c.OUTPUT_DEFAULT
    folder=root.parent
    snapshot=folder/'LIVE_DIRECTORY_UNAVAILABLE_CHECK_20260905.ndjson'
    receipt=folder/'UNAVAILABLE_PROFILE_AUDIT_20260905.json'
    numeric_evidence=folder/'UNAVAILABLE_NUMERIC_API_EVIDENCE_20260905.ndjson'
    targeted_evidence=folder/'UNAVAILABLE_DIRECTORY_NAME_SEARCH_20260905.ndjson'
    rows=c.read_ndjson(root/'profiles.ndjson')
    unavailable=[r for r in rows if r.get('identity_status')=='PROFILE_UNAVAILABLE_404']
    report={'started_at':c.utc_now(),'canonical_profiles_mutated':False,'unavailable_count':len(unavailable),'directory_pages':[], 'numeric_checks':[], 'rendered_checks':[]}
    async with async_playwright() as pw:
        context,_,_=await c.browser_context(c.parse_args([]),pw)
        try:
            page=context.pages[0]
            await c.initialize_directory(page)
            canary_name='Mikaela Aaland'
            canary=await page.evaluate(SEARCH,{'start':0,'limit':25,'query':canary_name})
            report['authenticated_search_canary']={'query':canary_name,'status':canary['status'],'matched':any(h.get('displayName')==canary_name for h in canary.get('hits',[]))}
            if not report['authenticated_search_canary']['matched']:
                raise RuntimeError('Authenticated search canary failed')
            hits=[]
            if snapshot.exists():
                hits=c.read_ndjson(snapshot)
                report['snapshot_reused']=True
            else:
                start=0
                while True:
                    result=await page.evaluate(SEARCH,{'start':start,'limit':100,'query':''})
                    if result['status']!=200:
                        raise RuntimeError(f'Directory HTTP {result["status"]}')
                    report['directory_pages'].append({'start':start,'count':len(result['hits']),'total':result['total'],'observed_at':c.utc_now()})
                    hits.extend(result['hits'])
                    start+=len(result['hits'])
                    if len(report['directory_pages'])%20==0:
                        print(json.dumps({'event':'DIRECTORY_PROGRESS','fetched':start,'total':result['total']}),flush=True)
                    if start>=result['total'] or not result['hits']:
                        break
                    await asyncio.sleep(0.4)
                c.append_ndjson(snapshot,hits)
            report['live_directory_count']=len(hits)
            # The search backend caps unfiltered pagination at 10,000. Do not
            # confuse a truncated census with evidence of removal: query every
            # unavailable name separately, retaining all returned candidates.
            report['unfiltered_snapshot_complete']=False
            report['unfiltered_snapshot_limitation']='10,000-hit search pagination cap; targeted searches used for every unavailable profile'
            prior_search={r['profile_uuid']:r for r in c.read_ndjson(targeted_evidence)} if targeted_evidence.exists() else {}
            pacer=c.AsyncRequestPacer(lambda:180)
            sem=asyncio.Semaphore(3)
            async def search_name(row):
                uid=row['profile_uuid']
                if uid in prior_search and prior_search[uid].get('complete'):
                    return prior_search[uid]
                async with sem:
                    collected=[]
                    start=0
                    while True:
                        await pacer.wait_turn()
                        result=await page.evaluate(SEARCH,{'start':start,'limit':100,'query':row['expected_name']})
                        if result['status']!=200:
                            raise RuntimeError(f'Targeted directory HTTP {result["status"]}')
                        collected.extend(result['hits'])
                        start+=len(result['hits'])
                        if start>=result['total'] or not result['hits']:
                            break
                    evidence={'profile_uuid':uid,'expected_name':row['expected_name'],'query':row['expected_name'],
                        'observed_at':c.utc_now(),'total':result['total'],'complete':start>=result['total'],'hits':collected}
                    c.append_ndjson(targeted_evidence,[evidence])
                    prior_search[uid]=evidence
                    if len(prior_search)%100==0:
                        print(json.dumps({'event':'TARGETED_SEARCH_PROGRESS','checked':len(prior_search),'total':len(unavailable)}),flush=True)
                    return evidence
            searches=await asyncio.gather(*(search_name(row) for row in unavailable))
            report['targeted_search_count']=len(searches)
            report['targeted_search_incomplete']=[r['profile_uuid'] for r in searches if not r['complete']]
            for result in searches:
                hits.extend(result['hits'])
            by_id={str(h.get('lexiconId') or h.get('id')):h for h in hits}
            by_name={}
            for h in by_id.values():
                by_name.setdefault(namekey(h.get('displayName')),[]).append(h)
            report['live_directory_unique_ids']=len(by_id)
            report['same_id_still_listed']=[]
            report['old_id_absent']=[]
            report['alternate_name_candidates']=[]
            for row in unavailable:
                uid=row['profile_uuid']
                item={'profile_uuid':uid,'expected_name':row['expected_name']}
                if uid in by_id:
                    report['same_id_still_listed'].append({**item,'directory_record':by_id[uid]})
                else:
                    report['old_id_absent'].append(item)
                alternatives=[h for h in by_name.get(namekey(row['expected_name']),[]) if str(h.get('lexiconId') or h.get('id'))!=uid]
                if alternatives:
                    report['alternate_name_candidates'].append({**item,'candidates':alternatives,'identity_status':'REVIEW_REQUIRED_NOT_A_MERGE'})
            c.atomic_json(receipt,report)
            print(json.dumps({'event':'DIRECTORY_COMPARISON','live':len(hits),'still_listed':len(report['same_id_still_listed']),'absent':len(report['old_id_absent']),'alternate_name_candidates':len(report['alternate_name_candidates'])}),flush=True)
            # Search binds the numeric record to the exact old lexicon ID. Probe
            # that source-native alternate key without guessing UUIDs or names.
            previous={r['profile_uuid']:r for r in c.read_ndjson(numeric_evidence)} if numeric_evidence.exists() else {}
            for i,item in enumerate(report['same_id_still_listed']):
                uid=item['profile_uuid']
                numeric=str(item['directory_record'].get('id') or '')
                if not numeric.isdigit() or numeric==uid:
                    continue
                if uid in previous:
                    evidence=previous[uid]
                else:
                    result=await page.evaluate(api.FETCH,numeric)
                    evidence={'profile_uuid':uid,'numeric_id':numeric,'observed_at':c.utc_now(),**result}
                    c.append_ndjson(numeric_evidence,[evidence])
                    await asyncio.sleep(0.4)
                data=evidence.get('data') or {}
                report['numeric_checks'].append({'profile_uuid':uid,'expected_name':item['expected_name'],'numeric_id':numeric,
                    'status':evidence['status'],'source_api_url':evidence.get('url'),'observed_at':evidence['observed_at'],
                    'returned_lexicon_id':data.get('lexiconId'),'returned_numeric_id':data.get('id'),
                    'returned_name':(data.get('name') or {}).get('displayName'),
                    'employment_entries':len(data.get('employmentItems',[])), 'current_position_entries':len(data.get('stafferPositions',[])),
                    'projected_api_sha256':hashlib.sha256(api.canonical(data)).hexdigest() if evidence['status']==200 else None})
                if evidence['status'] in (401,403,429):
                    raise RuntimeError(f'Numeric API HTTP {evidence["status"]}')
                if (i+1)%100==0:
                    c.atomic_json(receipt,report)
                    print(json.dumps({'event':'NUMERIC_PROGRESS','checked':len(report['numeric_checks']),'available':sum(x['status']==200 for x in report['numeric_checks'])}),flush=True)
            # Render a deterministic spread of currently listed unavailable IDs.
            sample=unavailable
            for item in [sample[i] for i in sorted({0,len(sample)//2,len(sample)-1})] if sample else []:
                uid=item['profile_uuid']
                obs={'profile_uuid':uid,'expected_name':item['expected_name'],'observed_at':c.utc_now()}
                try:
                    response=await page.goto(c.PROFILE_BASE_URL+uid,wait_until='domcontentloaded',timeout=30000)
                    await asyncio.sleep(2)
                    obs.update(http_status=response.status if response else None,final_url=page.url,
                        rendered=await page.evaluate("""() => ({name:document.querySelector('.profile-header__name')?.textContent.trim()||'',history_entries:document.querySelectorAll('.profile-employment-history__item').length,error404:/404|page (?:was )?not found/i.test(document.body.innerText)})"""))
                except Exception as exc:
                    obs['error']=type(exc).__name__
                report['rendered_checks'].append(obs)
            report['finished_at']=c.utc_now()
            report['snapshot_sha256']=hashlib.sha256(snapshot.read_bytes()).hexdigest()
            report['targeted_search_sha256']=hashlib.sha256(targeted_evidence.read_bytes()).hexdigest()
            report['numeric_evidence_sha256']=hashlib.sha256(numeric_evidence.read_bytes()).hexdigest() if numeric_evidence.exists() else None
            c.atomic_json(receipt,report)
            print(json.dumps({'event':'AUDIT_COMPLETE','numeric_checked':len(report['numeric_checks']),'numeric_200':sum(x['status']==200 for x in report['numeric_checks']),'rendered':report['rendered_checks']}),flush=True)
        finally:
            for page in list(context.pages):
                with contextlib.suppress(Exception): await asyncio.wait_for(page.close(),3)
            with contextlib.suppress(Exception): await asyncio.wait_for(context.close(),5)

if __name__=='__main__':
    asyncio.run(main())
