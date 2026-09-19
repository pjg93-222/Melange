import json,sys,time
from contextlib import closing
from pathlib import Path
sys.path.insert(0,'mentat/app');sys.path.insert(0,'mentat/tools')
import contribution_data as d,contribution_query as q,contribution_query_store as store
from report_directory import report_directory
directory=report_directory();source=d._source(directory,{'dataset':'Banking'});path,pending=d._ready(source)
out=Path('outputs/chart-studio-implementation-20260912/query-acceleration-validation.json')
results=[];original_sha=d._hash(path)
workloads=[('cycle',{'dimensions':['cycle']}),('zip_state',{'dimensions':['zip5','state'],'limit':100000}),
 ('filtered_company',{'dimensions':['company'],'filters':[{'field':'cycle','op':'eq','value':'2023-2024'}]}),
 ('recipient_category',{'dimensions':['recipient_category'],'measures':['amount','contributors']})]
for name,options in workloads:
 request={'dataset':'Banking','basis':'receipt',**options};row={'workload':name,'request':request,'times':{}}
 identity={'index':d._stamp(path),'query_code':q.LOADED_SHA256,'dataset':source['id'],'request':request}
 response_key=store._key([store.LOADED_SHA,'results',identity])
 row['response_cache_present_before_first_call']=(store.ROOT/'responses'/'results'/(response_key+'.json')).exists()
 for repeat in range(2):
  started=time.perf_counter();result=q.query(directory,request);row['times']['new_'+str(repeat)]=round(time.perf_counter()-started,6)
  print(json.dumps({'workload':name,'repeat':repeat,'seconds':row['times']['new_'+str(repeat)],'total_cents':result['totals']['amount'],'groups':result['group_count']}),flush=True)
  if repeat==0:first=result
  else:assert result==first
 plan=q._plan(request,*d._validate(request));started=time.perf_counter()
 with closing(d._ro(path)) as db:
  db.create_aggregate('median_cent',1,d._Median)
  summary=dict(db.execute(plan['summary_sql'],plan['summary_params']).fetchone())
  groups=list(db.execute(plan['grouped_sql'],plan['grouped_params']))
 row['times']['previous_sql_plan']=round(time.perf_counter()-started,6)
 assert summary['total__amount']==result['totals']['amount'] and summary['total__contributors']==result['totals']['contributors']
 assert groups[0]['_grouped_amount']==result['reconciliation']['grouped_amount_cents']
 expected_rows=[{k:r[k] for k in options['dimensions']+request.get('measures',['amount'])} for r in groups[1:]]
 assert expected_rows==result['rows']
 row.update(total_cents=result['totals']['amount'],contributors=result['totals']['contributors'],groups=result['group_count'],all_rows_match_previous_plan=True,provenance=result['provenance'])
 results.append(row);out.write_text(json.dumps(results,indent=2))
projected=store.view(path);proof=json.loads(projected.with_suffix('.json').read_text())
assert d._hash(path)==original_sha
proof.update(source_index_unchanged=True,original_bytes=path.stat().st_size,projected_bytes=projected.stat().st_size)
Path('outputs/chart-studio-implementation-20260912/query-projection-validation.json').write_text(json.dumps(proof,indent=2))
print(json.dumps({'projection':proof}),flush=True)
