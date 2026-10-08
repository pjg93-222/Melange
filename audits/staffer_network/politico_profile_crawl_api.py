"""Resume through the site's observed person endpoint in the existing login session.

Only modeled fields cross the browser boundary. Raw projected evidence is retained
and hash-bound; API observations are never presented as rendered DOM observations.
"""
from __future__ import annotations
import argparse
import asyncio
import calendar
import contextlib
import hashlib
import json
import re
import time
from pathlib import Path
import politico_profile_crawl_playwright as c
from playwright.async_api import async_playwright

API_BASE = 'https://directory.politicopro.com/proxy/lava/api/v1/person/'
FETCH = r"""async uuid => {
  const response = await fetch('/proxy/lava/api/v1/person/' + uuid, {signal:AbortSignal.timeout(20000),cache:'no-cache'});
  if(response.status !== 200) return {status:response.status,url:response.url};
  const raw = await response.json();
  const keys = new Set(['id','lexiconId','name','full','displayName','title','label','slug','startDate','endDate','employerName','institution','degree','stafferPositions','member','committee','office','fullName','parentCommittee','stafferRoles','issueAreas','employmentItems','educationItems']);
  const project = x => Array.isArray(x)?x.map(project):x && typeof x==='object'?Object.fromEntries(Object.entries(x).filter(([k])=>keys.has(k)).map(([k,v])=>[k,project(v)])):x;
  return {status:response.status,url:response.url,data:project(raw)};
}"""

def canonical(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()

ACTUAL_CONTACT_VALUE=re.compile(r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b|(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}',re.I)

def modeled_text(value):
    value=c.clean(value)
    if ACTUAL_CONTACT_VALUE.search(value):
        raise ValueError('Unexpected direct-contact value in a modeled API field')
    return value

def modeled_unique(values):
    return list(dict.fromkeys(text for value in values if (text:=modeled_text(value))))

def date_label(value):
    value = c.clean(value)
    if len(value)==7 and value[4]=='-' and value[:4].isdigit() and value[5:].isdigit():
        month=int(value[5:])
        if 1<=month<=12:
            return f'{calendar.month_abbr[month]} {value[:4]}'
    return value

def interval(item, employment=False):
    start,end = date_label(item.get('startDate')), date_label(item.get('endDate'))
    if not start and not end:
        return ''
    return f'{start} - {end or ("Present" if employment else "")}'.strip(' -')

def normalize(evidence, expected, *, allow_source_gaps=False):
    uuid=expected['profile_uuid']
    if evidence['status'] != 200 or evidence['url'] != API_BASE+uuid:
        raise ValueError('not a successful response from the requested person endpoint')
    data=evidence['data']
    numeric_source_id = uuid.isdigit() and str(data.get('id')) == uuid and not data.get('lexiconId')
    if data.get('lexiconId') != uuid and not numeric_source_id:
        raise ValueError(f'API lexicon UUID mismatch: {data.get("lexiconId")} != {uuid}')
    name=data.get('name',{}).get('displayName') or data.get('name',{}).get('full')
    positions=[]
    for item in data.get('stafferPositions',[]):
        member=item.get('member') or {}
        committee=item.get('committee') or {}
        employer=(member.get('name') or {}).get('displayName') or committee.get('fullName') or committee.get('name') or (item.get('office') or {}).get('label')
        if item.get('title') and employer:
            positions.append(f'{item["title"]} for {employer}')
    history=[dict(employer=x.get('employerName',''),title=x.get('title',''),date_text=interval(x,True)) for x in data.get('employmentItems',[])]
    education=[dict(institution=x.get('institution',''),degree=x.get('degree',''),date_text=interval(x)) for x in data.get('educationItems',[])]
    if not name or (not allow_source_gaps and (not positions or not history)):
        raise ValueError(f'API required content: name={bool(name)} positions={len(positions)} stafferPositions={len(data.get("stafferPositions",[]))} history={len(history)} incomplete_history={sum(not x["title"] or not x["employer"] for x in history)}')
    row=c.parse_snapshot({},expected)
    # A job such as Telephone Operator is professional history, not a phone
    # number. Retain every source job and apply a value check to allowlisted fields.
    matched=modeled_text(name)==row['expected_name']
    row.update(verified_name=modeled_text(name),identity_status='UUID_AND_NAME_MATCH' if matched else 'LIVE_NAME_CHANGED_SAME_UUID',
        review_status='REVIEW_REQUIRED' if matched else 'IDENTITY_EXCEPTION_REVIEW_REQUIRED',
        source_card_roles=modeled_unique(expected.get('roles',[])),source_card_issue_areas=sorted(modeled_unique(expected.get('issue_areas',[]))),
        current_header_positions=modeled_unique(positions),
        employment_history=[{k:modeled_text(v) for k,v in item.items()} for item in history],
        education=[{k:modeled_text(v) for k,v in item.items()} for item in education],
        profile_issue_areas=sorted(modeled_unique(x['label'] for x in data.get('issueAreas',[]) if x.get('label'))))
    # API has no explicit majority/minority DOM label; never infer it from party.
    row.update(extraction_method='AUTHENTICATED_PERSON_API_V1',source_api_url=evidence['url'],
               source_api_lexicon_id=data.get('lexiconId'),source_api_person_id=data.get('id'),profile_api_status=200,
               projected_api_sha256=hashlib.sha256(canonical(data)).hexdigest(),
               date_text_origin='FORMATTED_SOURCE_API_DATES_PRESERVING_PRECISION')
    row['source_field_gaps']=[{'collection':'employment_history','ordinal':i,'missing_fields':[k for k in ('title','employer') if not item[k]]}
                              for i,item in enumerate(history,1) if not item['title'] or not item['employer']]
    missing=[field for field in ('current_header_positions','employment_history') if not row[field]]
    if missing:
        row.update(content_status='SOURCE_CONFIRMED_MISSING_FIELDS',source_missing_collections=missing)
    return row

async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-profiles',type=int,default=0)
    parser.add_argument('--recheck-404',action='store_true')
    opts=parser.parse_args()
    args=c.parse_args([])
    root=c.OUTPUT_DEFAULT
    profiles=root/'profiles.ndjson'
    evidence_path=root/'api_projected_evidence_20260905.ndjson'
    observations=root/'api_recheck_observations_20260905.ndjson'
    source_omissions=root/'api_source_omissions_20260905.ndjson'
    with c.CrawlLock(root/'.politico-python-crawl.lock'):
        c.assert_checkpoint_stale(root/'state.json',90)
        existing=c.read_ndjson(profiles)
        by_id={r['profile_uuid']:r for r in existing}
        directory=c.read_ndjson(c.DIRECTORY_DEFAULT)
        if opts.recheck_404:
            queue=[r for r in directory if by_id.get(r['profile_uuid'],{}).get('identity_status')=='PROFILE_UNAVAILABLE_404']
        else:
            queue=[r for r in directory if r['profile_uuid'] not in by_id]
        if opts.max_profiles:
            queue=queue[:opts.max_profiles]
        rate=c.RateState()
        pacer=c.AsyncRequestPacer(lambda:rate.rpm)
        attempted=good=omitted=0
        started=time.monotonic()
        halted=False
        async with async_playwright() as pw:
            context,_,_=await c.browser_context(args,pw)
            try:
                page=context.pages[0]
                await c.initialize_directory(page,pacer)
                # Validate a previously rendered profile through the same API.
                canary=next(r for r in existing if r.get('employment_history') and not r.get('explicit_side_labels'))
                expected=next(r for r in directory if r['profile_uuid']==canary['profile_uuid'])
                await pacer.wait_turn()
                observed=await page.evaluate(FETCH,expected['profile_uuid'])
                normalized=normalize(observed,expected)
                if normalized['verified_name'] != canary['verified_name'] or len(normalized['employment_history']) != len(canary['employment_history']):
                    raise RuntimeError('API vs rendered canary name/history count mismatch')
                print(json.dumps({'event':'API_CANARY_PASS','remaining_targets':len(queue)}),flush=True)
                for expected in queue:
                    await pacer.wait_turn()
                    attempted+=1
                    tick=time.monotonic()
                    try:
                        result=await asyncio.wait_for(page.evaluate(FETCH,expected['profile_uuid']),25)
                        status=result['status']
                        c.append_ndjson(observations,[{'profile_uuid':expected['profile_uuid'],'status':status,'observed_at':c.utc_now(),'source_api_url':result.get('url')}])
                        if status in (400,401,403,429):
                            halted=True
                            raise RuntimeError(f'API_HTTP_{status}')
                        if status!=200:
                            raise ValueError(f'API_HTTP_{status}')
                        c.append_ndjson(evidence_path,[{'profile_uuid':expected['profile_uuid'],'observed_at':c.utc_now(),**result}])
                        try:
                            row=normalize(result,expected)
                        except ValueError as exc:
                            if not str(exc).startswith('API required content:'):
                                raise
                            omitted+=1
                            c.append_ndjson(source_omissions,[{'profile_uuid':expected['profile_uuid'],'expected_name':expected['name'],
                                'observed_at':c.utc_now(),'reason':str(exc),'source_api_url':result['url'],
                                'projected_api_sha256':hashlib.sha256(canonical(result['data'])).hexdigest(),
                                'status':'SOURCE_DATA_INCOMPLETE_REVIEW_REQUIRED'}])
                            row=None
                        if row is None:
                            rate.record(attempted=1,succeeded=1,retryable=0,hard=0,slow=int(time.monotonic()-tick>12))
                            outcome={'attempted':1,'succeeded':1,'retryable_failures':0,'hard_failures':0}
                        elif opts.recheck_404:
                            # Preserve the old complete artifact before any replacements.
                            backup=root/'profiles_before_api404_recovery_20260905.ndjson'
                            if not backup.exists():
                                import shutil
                                shutil.copy2(profiles,backup)
                            by_id[row['profile_uuid']]=row
                        elif row is not None:
                            c.append_ndjson(profiles,[row])
                            by_id[row['profile_uuid']]=row
                        if row is not None:
                            good+=1
                            rate.record(attempted=1,succeeded=1,retryable=0,hard=0,slow=int(time.monotonic()-tick>12))
                        outcome={'attempted':1,'succeeded':1,'retryable_failures':0,'hard_failures':0}
                    except Exception as exc:
                        confirmed_404 = opts.recheck_404 and str(exc)=='API_HTTP_404'
                        rate.record(attempted=1,succeeded=int(confirmed_404),retryable=int(not confirmed_404),hard=0,slow=0)
                        outcome={'attempted':1,'succeeded':int(confirmed_404),'retryable_failures':int(not confirmed_404),'hard_failures':0}
                        if not confirmed_404:
                            print(json.dumps({'event':'API_DEFERRED','uuid':expected['profile_uuid'],'error':str(exc),'halted':halted}),flush=True)
                    if opts.recheck_404 and good and (attempted%25==0 or halted or attempted==len(queue)):
                        temporary=root/'profiles.api_recovery.tmp'
                        with temporary.open('wb') as out:
                            for old in existing:
                                out.write(canonical(by_id[old['profile_uuid']])+b'\n')
                        temporary.replace(profiles)
                    payload=c.state_payload(scope='ALL_CURRENT_PROFILES',total=len(directory),succeeded=len(by_id),failed=0,
                                            attempted_this_session=attempted,halted=halted,rate=rate,last_batch=outcome)
                    payload.update(browser_driver='PYTHON_PLAYWRIGHT_AUTHENTICATED_PERSON_API',active_workers=1,
                                   api_recovery_mode=opts.recheck_404,api_recovery_saved=good,api_source_omissions=omitted)
                    c.atomic_json(root/'state.json',payload)
                    if attempted%25==0 or halted or attempted==len(queue):
                        print(json.dumps({'event':'API_PROGRESS','attempted':attempted,'saved':good,'source_omissions':omitted,'remaining':payload['remaining'],
                                          'rpm':rate.rpm,'measured_per_minute':round(good*60/(time.monotonic()-started),1),'halted':halted}),flush=True)
                        await asyncio.to_thread(c.emit_glassbox,args.glassbox_emit,payload)
                    if halted:
                        break
            finally:
                for p in list(context.pages):
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(p.close(),3)
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(context.close(),5)
    return 3 if halted else 0

if __name__=='__main__':
    raise SystemExit(asyncio.run(main()))
