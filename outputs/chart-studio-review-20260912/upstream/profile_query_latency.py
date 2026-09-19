import json,sys,time
from pathlib import Path
sys.path.insert(0,'mentat/app');sys.path.insert(0,'mentat/tools')
import contribution_data as d,contribution_query as q
from report_directory import report_directory
start=time.perf_counter();source=d._source(report_directory(),{'dataset':'Banking'});path,pending=d._ready(source)
print(json.dumps({'phase':'source_and_ready','seconds':time.perf_counter()-start,'pending':pending,'path':str(path)}),flush=True)
results=[]
for mode in ('default','memory'):
 for name,request in [('cycle',{'dimensions':['cycle']}),('zip_state',{'dimensions':['zip5','state'],'limit':100000})]:
  request.update(dataset='Banking',basis='receipt')
  plan=q._plan(request,*d._validate(request))
  for repeat in range(2):
   db=d._ro(path);db.create_aggregate('median_cent',1,d._Median)
   if mode=='memory':db.execute('PRAGMA temp_store=MEMORY');db.execute('PRAGMA cache_size=-65536')
   row={'mode':mode,'workload':name,'repeat':repeat,'index_token':d._token(source),'phases':{}}
   for part in ('summary','grouped'):
    started=time.perf_counter();data=list(db.execute(plan[part+'_sql'],plan[part+'_params']));row['phases'][part]=round(time.perf_counter()-started,6)
    row[part+'_rows']=len(data)
    if repeat==0:row[part+'_plan']=[r[3] for r in db.execute('EXPLAIN QUERY PLAN '+plan[part+'_sql'],plan[part+'_params'])]
   db.close();results.append(row);print(json.dumps(row),flush=True)
   Path('outputs/chart-studio-implementation-20260912/query-latency-profile.json').write_text(json.dumps(results,indent=2))
