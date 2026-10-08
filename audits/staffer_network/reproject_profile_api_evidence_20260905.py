"""Rebuild only API-derived modeled records from their hash-bound observations."""
import hashlib
import shutil
import politico_profile_crawl_api as api
import politico_profile_crawl_playwright as c

root=c.OUTPUT_DEFAULT
with c.CrawlLock(root/'.politico-python-crawl.lock'):
    source=root/'profiles.ndjson'
    rows=c.read_ndjson(source)
    directory={r['profile_uuid']:r for r in c.read_ndjson(c.DIRECTORY_DEFAULT)}
    evidence={hashlib.sha256(api.canonical(r['data'])).hexdigest():r for r in c.read_ndjson(root/'api_projected_evidence_20260905.ndjson')}
    changed=0
    output=[]
    for row in rows:
        if row.get('extraction_method')=='AUTHENTICATED_PERSON_API_V1':
            raw=evidence[row['projected_api_sha256']]
            new=api.normalize(raw,directory[row['profile_uuid']],allow_source_gaps=True)
            new['observed_at']=row['observed_at']
            changed+=int(api.canonical(new)!=api.canonical(row))
            row=new
        output.append(row)
    backup=root/'profiles_before_lossless_api_reprojection_20260905.ndjson'
    if changed:
        if backup.exists(): raise RuntimeError('Backup already exists; inspect before replacing')
        shutil.copy2(source,backup)
        temporary=root/'profiles.reproject.tmp'
        with temporary.open('wb') as stream:
            for row in output: stream.write(api.canonical(row)+b'\n')
        temporary.replace(source)
    print({'api_records_updated':changed,'total_profiles':len(output)})
