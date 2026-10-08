"""Account for every sealed source record, preserving explicit source gaps.

Does not claim complete histories or promote identities; the strict terminal
full-content gate remains in force in verify_politico_profile_crawl.py.
"""
import json
import shutil
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c

root=c.OUTPUT_DEFAULT
with c.CrawlLock(root/'.politico-python-crawl.lock'):
    profiles=c.read_ndjson(root/'profiles.ndjson')
    known={r['profile_uuid'] for r in profiles}
    directory=c.read_ndjson(c.DIRECTORY_DEFAULT)
    evidence={r['profile_uuid']:r for r in c.read_ndjson(root/'api_projected_evidence_20260905.ndjson')}
    observations={r['profile_uuid']:r for r in c.read_ndjson(root/'api_recheck_observations_20260905.ndjson')}
    rows=[]
    for expected in directory:
        uuid=expected['profile_uuid']
        if uuid in known: continue
        observation=observations.get(uuid,{})
        if observation.get('status')==404:
            row=c.parse_snapshot({},expected,unavailable_404=True)
            row.update(observed_at=observation['observed_at'],source_api_url=observation['source_api_url'],
                       profile_api_status=404,unavailable_evidence='PERSON_API_HTTP_404',
                       api_observation_sha256=api.hashlib.sha256(api.canonical(observation)).hexdigest())
        elif observation.get('status')==200 and uuid in evidence:
            raw=evidence[uuid]
            row=api.normalize(raw,expected,allow_source_gaps=True)
            row['observed_at']=raw['observed_at']
        else:
            raise RuntimeError(f'No conclusive observation for {uuid}; no changes made')
        rows.append(row)
    if rows:
        backup=root/'profiles_before_final_observations_20260905.ndjson'
        if backup.exists(): raise RuntimeError('Backup already exists; inspect previous finalization before rerunning')
        shutil.copy2(root/'profiles.ndjson',backup)
        c.append_ndjson(root/'profiles.ndjson',rows)
    prior=c.load_checkpoint(root/'state.json')
    rate=c.RateState.from_checkpoint(prior)
    payload=c.state_payload(scope='ALL_CURRENT_PROFILES',total=len(directory),succeeded=len(known)+len(rows),failed=0,
        attempted_this_session=0,halted=False,rate=rate,last_batch={'attempted':0,'succeeded':0,'retryable_failures':0,'hard_failures':0})
    payload.update(browser_driver='PYTHON_PLAYWRIGHT_AUTHENTICATED_PERSON_API',active_workers=0,
        acquisition_status='ALL_DIRECTORY_RECORDS_ACCOUNTED',source_content_complete=not any(r.get('source_missing_collections') for r in profiles+rows))
    c.atomic_json(root/'state.json',payload)
    print(json.dumps({'added':len(rows),'accounted':payload['total_succeeded'],'remaining':payload['remaining'],
                      'source_incomplete':sum(bool(r.get('source_missing_collections')) for r in profiles+rows)}))
