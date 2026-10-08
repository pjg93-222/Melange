"""Fetch replacement candidates; never merge people on a search hit alone."""
import asyncio
import contextlib
import hashlib
import json
import re
from pathlib import Path
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c
from check_unavailable_profiles_20260905 import SEARCH,namekey
from playwright.async_api import async_playwright

def role_key(role):
    role=re.sub(r'(?:Democratic|Republican|Independent|Nonpartisan)(?:[A-Z]{2}(?:-\d+)?)?$','',role).strip()
    return namekey(role)

def classify(expected, hit, evidence):
    data=evidence.get('data') or {}
    uid=str(hit.get('lexiconId') or hit.get('id'))
    bound=evidence.get('status')==200 and evidence.get('url')==api.API_BASE+uid and str(data.get('lexiconId') or data.get('id'))==uid
    exact_name=bound and namekey((data.get('name') or {}).get('displayName'))==namekey(expected['name'])
    old_roles={role_key(r) for r in expected.get('roles',[])}
    hit_roles={role_key(f'{e.get("title", "")} for {e.get("employer", "")}') for e in hit.get('employments',[])}
    api_roles=set()
    if bound:
        projected=api.normalize(evidence,{'profile_uuid':uid,'name':hit['displayName'],'roles':[],'issue_areas':[]},allow_source_gaps=True)
        api_roles={role_key(r) for r in projected['current_header_positions']}
    matching_roles=old_roles & hit_roles & api_roles
    if exact_name and matching_roles:
        result='PROBABLE_REPLACEMENT_EXACT_NAME_CURRENT_ROLE_AND_EMPLOYER'
    elif exact_name:
        result='SAME_NAME_DIFFERENT_OR_UNCONFIRMED_EMPLOYMENT_REVIEW_REQUIRED'
    else:
        result='SEARCH_HIT_NOT_AN_IDENTITY_MATCH'
    return {'classification':result,'identity_bound':bound,'exact_name':exact_name,'matching_current_roles':sorted(matching_roles)}

async def main():
    folder=c.OUTPUT_DEFAULT.parent
    searches=c.read_ndjson(folder/'UNAVAILABLE_DIRECTORY_NAME_SEARCH_20260905.ndjson')
    expected={r['profile_uuid']:r for r in c.read_ndjson(c.DIRECTORY_DEFAULT)}
    profiles={r['profile_uuid']:r for r in c.read_ndjson(c.OUTPUT_DEFAULT/'profiles.ndjson')}
    evidence_path=folder/'UNAVAILABLE_REPLACEMENT_API_EVIDENCE_20260905.ndjson'
    supplementary=folder/'UNAVAILABLE_REPLACEMENT_PROFILES_20260905.ndjson'
    previous={r['profile_uuid']:r for r in c.read_ndjson(evidence_path)} if evidence_path.exists() else {}
    existing_supplement={r['profile_uuid'] for r in c.read_ndjson(supplementary)} if supplementary.exists() else set()
    report={'started_at':c.utc_now(),'canonical_profiles_mutated':False,'automatic_identity_merges':0,'candidates':[]}
    async with async_playwright() as pw:
        context,_,_=await c.browser_context(c.parse_args([]),pw)
        try:
            page=context.pages[0]
            await c.initialize_directory(page)
            canary=await page.evaluate(SEARCH,{'start':0,'limit':25,'query':'Mikaela Aaland'})
            report['search_canary']={'status':canary['status'],'matched':any(h.get('displayName')=='Mikaela Aaland' for h in canary.get('hits',[]))}
            if not report['search_canary']['matched']:
                raise RuntimeError('Positive search canary failed')
            for search in searches:
                unique={str(h.get('lexiconId') or h.get('id')):h for h in search['hits']}
                for uid,hit in unique.items():
                    if uid not in previous:
                        evidence={'profile_uuid':uid,'observed_at':c.utc_now(),**await page.evaluate(api.FETCH,uid)}
                        if evidence['status'] in (401,403,429):
                            raise RuntimeError(f'Candidate API HTTP {evidence["status"]}')
                        c.append_ndjson(evidence_path,[evidence])
                        previous[uid]=evidence
                        await asyncio.sleep(0.4)
                    evidence=previous[uid]
                    classification=classify(expected[search['profile_uuid']],hit,evidence)
                    item={'old_profile_uuid':search['profile_uuid'],'expected_name':search['expected_name'],
                        'candidate_profile_uuid':uid,'candidate_name':hit.get('displayName'),'candidate_url':c.PROFILE_BASE_URL+uid,
                        'already_in_corpus':uid in profiles,'api_status':evidence['status'],'source_card_roles':expected[search['profile_uuid']].get('roles',[]),
                        'live_directory_employment':hit.get('employments',[]),**classification}
                    report['candidates'].append(item)
                    if classification['identity_bound'] and uid not in existing_supplement:
                        row=api.normalize(evidence,{'profile_uuid':uid,'name':hit['displayName'],'roles':[],'issue_areas':[]},allow_source_gaps=True)
                        row['supplementary_acquisition_status']='REPLACEMENT_SEARCH_CANDIDATE_NOT_MERGED'
                        c.append_ndjson(supplementary,[row])
                        existing_supplement.add(uid)
            report['finished_at']=c.utc_now()
            report['unique_candidates']=len({r['candidate_profile_uuid'] for r in report['candidates']})
            report['probable_replacements']=sum(r['classification'].startswith('PROBABLE_REPLACEMENT') for r in report['candidates'])
            report['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (evidence_path,folder/'UNAVAILABLE_DIRECTORY_NAME_SEARCH_20260905.ndjson') if p.exists()}
            c.atomic_json(folder/'UNAVAILABLE_REPLACEMENT_REVIEW_20260905.json',report)
            print(json.dumps(report),flush=True)
        finally:
            for p in list(context.pages):
                with contextlib.suppress(Exception): await asyncio.wait_for(p.close(),3)
            with contextlib.suppress(Exception): await asyncio.wait_for(context.close(),5)

if __name__=='__main__':
    asyncio.run(main())
