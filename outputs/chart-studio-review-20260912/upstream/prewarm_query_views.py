"""Prewarm all current validated indexes without triggering money rebuilds."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'mentat/app');sys.path.insert(0,'mentat/tools')
import contribution_data as d,contribution_query as q,contribution_query_store as store
from report_directory import report_directory
directory=report_directory();results=[]
out=Path('outputs/chart-studio-implementation-20260912/query-prewarm-validation.json')
for source in d._sources(directory):
 started=time.perf_counter();token=d._token(source);original=d.CACHE_ROOT/(token+'.sqlite')
 assert original.exists(),'Prewarm must not trigger an original accounting rebuild.'
 original_sha=d._hash(original)
 request={'dataset':source['id'],'basis':'receipt','dimensions':['company'],'measures':['amount'],
   'filters':[],'aggregate_filters':[],'sort':[{'field':'amount','direction':'desc'}],'limit':40,'offset':0}
 before=time.perf_counter();result=q._query_ready(original,request,source,*d._validate(request));first_seconds=time.perf_counter()-before
 before=time.perf_counter();again=q.query(directory,request);repeat_seconds=time.perf_counter()-before
 assert again==result and result['reconciliation']['receipt_matches_workbook'] and result['reconciliation']['conserved']
 assert d._hash(original)==original_sha and d._token(source)==token
 projected=store.view(original);proof=json.loads(projected.with_suffix('.json').read_text())
 item={'dataset':source['id'],'status':'passed','request':request,'receipt_cents':result['totals']['amount'],
  'contributors':result['totals']['contributors'],'first_query_including_preparation_seconds':round(first_seconds,6),
  'repeat_public_query_seconds':round(repeat_seconds,6),'elapsed_seconds':round(time.perf_counter()-started,6),
  'projection_preparation_seconds':proof['seconds'],'source_index_sha256':original_sha,'source_index_unchanged':True,
  'fact_count':proof['fact_count'],'field_mismatches':proof['field_mismatches'],'source_index_token':token,
  'projection_sha256':proof['sha256'],'query_code_sha256':q.LOADED_SHA256,'projection_code_sha256':store.LOADED_SHA}
 results.append(item);out.write_text(json.dumps(results,indent=2));print(json.dumps(item),flush=True)
assert len(results)==8
