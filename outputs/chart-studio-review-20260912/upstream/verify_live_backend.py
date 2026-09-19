import json,sys,time
from pathlib import Path
sys.path.insert(0,r'C:\Users\pgoff\Mentat\mentat\app')
import contribution_data as c
directory=Path(r'C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files')
out=Path('outputs/chart-studio-implementation-20260912/data-validation.json');out.parent.mkdir(parents=True,exist_ok=True)
results=[]
original_progress=c._progress
def progress(token,**values):
    original_progress(token,**values)
    count=values.get('processed_records',0)
    if values.get('message') or (count and count%100000==0):print('PROGRESS '+str(values),flush=True)
c._progress=progress
for industry in ['Community Banks','Crypto','Fintech','Credit Union','Banking','Credit Arms','Property & Casualty Insurance','Telecom']:
    start=time.monotonic()
    try:
        source=c._source(directory,{'dataset':industry})
        print('BUILD '+industry,flush=True)
        path,pending=c._ready(source,wait=True)
        receipt=c.query(directory,{'dataset':industry,'basis':'receipt','dimensions':['cycle'],'measures':['amount','records','contributors']})
        original=c.query(directory,{'dataset':industry,'basis':'original_observed','dimensions':['zip5'],'measures':['amount'],'limit':100000})
        with c._ro(path) as db: manifest=json.loads(db.execute("SELECT value FROM metadata WHERE key='manifest'").fetchone()[0])
        result={'cycle_expected_cents':manifest['expected_receipt_cycles'],'cycle_actual_cents':manifest['receipt_cycles'],'industry':industry,'status':'passed','seconds':round(time.monotonic()-start,2),'receipt':receipt,'original':{k:v for k,v in original.items() if k!='rows'},'zip_group_count':len(original.get('rows',[]))}
        assert receipt['reconciliation']['receipt_matches_workbook']
        assert original['reconciliation']['conserved']
        assert not original['has_more']
        print(industry+' PASSED '+str(receipt['totals'])+' '+str(result['seconds'])+'s',flush=True)
    except Exception as e:
        result={'industry':industry,'status':'failed','error':str(e)}
        print(industry+' FAILED '+str(e),flush=True)
    results.append(result)
    out.write_text(json.dumps(results,indent=2),encoding='utf-8')
