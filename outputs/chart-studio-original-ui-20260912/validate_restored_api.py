"""Final original-UI queries reconcile to the same authoritative receipts."""
import gzip
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen

HERE=Path(__file__).resolve().parent
reference=json.loads((HERE.parent/'chart-studio-implementation-20260912/data-validation.json').read_text(encoding='utf-8-sig'))
assert len(reference)==8 and all(row['status']=='passed' for row in reference)
BASE='http://127.0.0.1:8813/api/contributions/'

def request(path,body=None,token=None):
    headers={'Content-Type':'application/json','Accept-Encoding':'gzip'}
    if token:headers['X-Mentat-Token']=token
    started=time.perf_counter()
    with urlopen(Request(BASE+path,headers=headers,data=json.dumps(body).encode() if body is not None else None),timeout=180) as response:
        payload=response.read();size=len(payload)
        if response.headers.get('Content-Encoding')=='gzip':payload=gzip.decompress(payload)
        value=json.loads(payload)
    return value,round(time.perf_counter()-started,6),size

session,_,_=request('session')
catalog,_,_=request('catalog')
assert len(catalog['datasets'])==8 and all(item['available'] for item in catalog['datasets'])
checks=[]
for industry in reference:
    for label,dimensions,measures,limit in [('cycles',['cycle'],['amount','records','contributors'],20),('original_ui',['company'],['amount'],40)]:
        query={'dataset':industry['industry'],'basis':'receipt','dimensions':dimensions,'measures':measures,
               'filters':[],'aggregate_filters':[],'sort':[{'field':'cycle','direction':'asc'}] if label=='cycles' else [{'field':'amount','direction':'desc'}],'limit':limit,'offset':0}
        result,elapsed,size=request('query',query,session['token'])
        assert result['status']=='ready'
        assert result['totals']['amount']==industry['receipt']['totals']['amount']
        assert result['reconciliation']['receipt_matches_workbook'] is True
        assert result['reconciliation']['conserved'] is True
        assert result['provenance']['source_financial_universe_verified'] is True
        assert result['verified_unique'] is False
        if label=='cycles':assert {row['cycle']:row['amount'] for row in result['rows']}==industry['cycle_expected_cents']
        repeated,repeat_seconds,_=request('query',query,session['token'])
        assert repeated==result
        check={'industry':industry['industry'],'view':label,'status':'passed','seconds':elapsed,'repeat_seconds':repeat_seconds,'wire_bytes':size,'request':query,'response':result}
        checks.append(check)
        (HERE/'live-api-validation.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
        print(industry['industry'],label,elapsed,repeat_seconds,flush=True)
print('All eight original-UI and cycle queries match their published receipts.',flush=True)
