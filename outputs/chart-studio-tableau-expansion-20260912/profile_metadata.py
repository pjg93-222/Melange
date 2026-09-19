import sys,time,json
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'mentat/app'))
import contribution_data as data,contribution_query as query,contribution_query_store as store,contribution_semantics as sem
from report_directory import report_directory
source=data._source(report_directory(),{'dataset':'Banking'});path,_=data._ready(source);projected=store.view(path)
request={'dataset':'Banking','basis':'receipt','dimensions':['reported_filing_form','reported_amendment_indicator'],'measures':['amount','records'],'limit':1000}
results=[];reference=None
for mode in ['default','memory']:
    with closing(store._readonly(projected)) as db:
        db.execute('ATTACH DATABASE ? AS original',(path.as_uri()+'?mode=ro',))
        relation=sem.raw_relation(db,source,request['dimensions'])
        if mode=='memory':
            db.execute('PRAGMA temp_store=MEMORY')
            for name in ['main','original','receipt_source']:db.execute('PRAGMA '+name+'.cache_size=-32768')
        plan=query._plan(request,*sem.validate(request),raw_relation=relation)
        start=time.perf_counter();rows=[dict(r) for r in db.execute(plan['grouped_sql'],plan['grouped_params'])];seconds=time.perf_counter()-start
        if reference is None:reference=rows
        else:assert rows==reference
        results.append({'mode':mode,'seconds':seconds,'rows':len(rows),'identical':True})
        print(results[-1],flush=True)
Path(__file__).with_name('metadata-profile.json').write_text(json.dumps(results,indent=2))
