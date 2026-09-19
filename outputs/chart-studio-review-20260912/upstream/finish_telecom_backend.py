import json,sys,time
from pathlib import Path
sys.path.insert(0,'mentat/app');import contribution_data as c;import contribution_query as q
directory=Path(r'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files')
out=Path('outputs/chart-studio-implementation-20260912/data-validation.json')
results=json.loads(out.read_text());original_progress=c._progress
def progress(token,**values):
 original_progress(token,**values)
 count=values.get('processed_records',0)
 if values.get('message') and (count%100000==0 or values.get('status') or not count):print('PROGRESS '+str(values),flush=True)
c._progress=progress
start=time.monotonic();source=c._source(directory,{'dataset':'Telecom'})
path,pending=c._ready(source,wait=True)
receipt=q.query(directory,{'dataset':'Telecom','basis':'receipt','dimensions':['cycle'],'measures':['amount','records','contributors']})
original=q.query(directory,{'dataset':'Telecom','basis':'original_observed','dimensions':['zip5'],'measures':['amount'],'limit':100000})
with c._ro(path) as db:manifest=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
assert receipt['reconciliation']['receipt_matches_workbook'] and original['reconciliation']['conserved'] and not original['has_more']
result={'cycle_expected_cents':manifest['expected_receipt_cycles'],'cycle_actual_cents':manifest['receipt_cycles'],'industry':'Telecom','status':'passed',
 'seconds':round(time.monotonic()-start,2),'receipt':receipt,'original':{k:v for k,v in original.items() if k!='rows'},'zip_group_count':len(original['rows']),
 'query_implementation':'optimized read-only planner, equivalence-tested against the original reference',
 'initial_rejection':'Compact published payload intentionally omits dates. The adapter now requires declared schema plus a full financial source-universe proof and exact source-date-derived cycle; other identity fields remain exact.'}
results=[r for r in results if r['industry']!='Telecom']+[result]
out.write_text(json.dumps(results,indent=2));print(json.dumps({'industry':'Telecom','status':'passed','totals':receipt['totals'],'seconds':result['seconds']}),flush=True)
