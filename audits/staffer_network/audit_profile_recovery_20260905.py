"""Verify API evidence fidelity and audit duplicates without name-only merging."""
import collections
import hashlib
import json
import re
from pathlib import Path
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c

def main():
    root=c.OUTPUT_DEFAULT
    profiles=c.read_ndjson(root/'profiles.ndjson')
    directory=c.read_ndjson(c.DIRECTORY_DEFAULT)
    expected={r['profile_uuid']:r for r in directory}
    evidence=c.read_ndjson(root/'api_projected_evidence_20260905.ndjson')
    evidence_by_hash={hashlib.sha256(api.canonical(r['data'])).hexdigest():r for r in evidence}
    failures=[]
    checked=0
    fields=['profile_uuid','expected_name','verified_name','identity_status','source_card_roles','source_card_issue_areas',
            'current_header_positions','employment_history','education','profile_issue_areas','explicit_side_labels']
    for row in profiles:
        if row.get('extraction_method')!='AUTHENTICATED_PERSON_API_V1': continue
        checked+=1
        raw=evidence_by_hash.get(row.get('projected_api_sha256'))
        if not raw:
            failures.append({'uuid':row['profile_uuid'],'failure':'missing hash-bound evidence'}); continue
        try:
            modeled=api.normalize(raw,expected[row['profile_uuid']],allow_source_gaps=True)
            for key in fields:
                if modeled[key]!=row[key]: failures.append({'uuid':row['profile_uuid'],'field':key,'failure':'source projection mismatch'})
            if len(row['employment_history'])!=len(raw['data'].get('employmentItems',[])):
                failures.append({'uuid':row['profile_uuid'],'failure':'employment row count mismatch'})
        except Exception as exc: failures.append({'uuid':row['profile_uuid'],'failure':str(exc)})
    ids=collections.Counter(r['profile_uuid'] for r in profiles)
    names=collections.defaultdict(list)
    for row in profiles:
        key=' '.join(re.findall(r'\w+',str(row.get('verified_name') or row['expected_name']).casefold()))
        names[key].append({'profile_uuid':row['profile_uuid'],'name':row.get('verified_name') or row['expected_name'],
                           'current_positions':row['current_header_positions']})
    entity_ids=collections.defaultdict(set)
    for row in evidence:
        if row['data'].get('id'): entity_ids[str(row['data']['id'])].add(row['profile_uuid'])
    identity_path=root.parent.parent/'staffer_live_runtime'/'identity_resolution_receipt.json'
    identity=json.loads(identity_path.read_text(encoding='utf-8')) if identity_path.exists() else {}
    groups=identity.get('identity_groups',[])
    targets=collections.defaultdict(set)
    for group in groups:
        for alias in group.get('alias_ids',[]): targets[alias].add(group['primary_id'])
    conflicts={alias:sorted(vals) for alias,vals in targets.items() if len(vals)>1}
    same_source={key:sorted(vals) for key,vals in entity_ids.items() if len(vals)>1}
    duplicate_ids=[key for key,count in ids.items() if count>1]
    report={'generated_at':c.utc_now(),'status':'PASS' if not failures and not duplicate_ids and not conflicts else 'FAIL',
            'api_profiles_verified':checked,'api_source_projection_failures':failures,'duplicate_profile_ids':duplicate_ids,
            'same_name_candidate_groups':[{'name_key':name,'records':rows,'resolution':'KEEP_SEPARATE_PENDING_IDENTITY_EVIDENCE'} for name,rows in sorted(names.items()) if len(rows)>1],
            'same_api_person_id_groups':same_source,'existing_evidence_backed_identity_groups':len(groups),
            'existing_aliases':len(targets),'alias_target_conflicts':conflicts,
            'notes':['Same-name candidates are not confirmed duplicate people.','Raw source IDs remain separate; evidence-backed display aliases apply in the dashboard.']}
    c.atomic_json(root.parent/'PROFILE_RECOVERY_AND_DUPLICATE_AUDIT_20260905.json',report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('same_name_candidate_groups','notes')},ensure_ascii=False))
    print('same_name_candidate_groups',len(report['same_name_candidate_groups']))
    return 0 if report['status']=='PASS' else 2

if __name__=='__main__': raise SystemExit(main())
