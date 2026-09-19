"""Check the running, guarded API against the independently built source receipts."""
import json
from pathlib import Path
import time
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8813'

def call(path,body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token:headers['X-Mentat-Token']=token
    request=Request(BASE+'/api/contributions/'+path,
                    data=json.dumps(body).encode() if body is not None else None,headers=headers)
    with urlopen(request,timeout=180) as response:return json.load(response)

def main():
    reference=json.loads((ROOT/'data-validation.json').read_text(encoding='utf-8-sig'))
    assert len(reference)==8 and all(item['status']=='passed' for item in reference), 'Complete all eight source validations first.'
    session=call('session')
    catalog=call('catalog')
    assert len(catalog['datasets'])==8 and all(item['available'] for item in catalog['datasets'])
    assert {item['industry'] for item in reference}=={item['id'] for item in catalog['datasets']}
    results=[]
    for item in reference:
        request={'dataset':item['industry'],'basis':'receipt','dimensions':['cycle'],
                 'measures':['amount','records','contributors'],'sort':[{'field':'cycle','direction':'asc'}],
                 'limit':20,'offset':0}
        started=time.perf_counter()
        response=call('query',request,session['token'])
        elapsed=round(time.perf_counter()-started,3)
        assert response['status']=='ready', (item['industry'],response)
        assert response['totals']['amount']==item['receipt']['totals']['amount']
        assert {row['cycle']:row['amount'] for row in response['rows']}==item['cycle_expected_cents']
        assert response['reconciliation']['receipt_matches_workbook'] is True
        assert response['reconciliation']['conserved'] is True
        assert response['provenance']['source_financial_universe_verified'] is True
        assert len(response['provenance']['query_engine_sha256'])==64
        assert response['verified_unique'] is False
        results.append({'industry':item['industry'],'status':'passed','seconds':elapsed,'request':request,'response':response})
        (ROOT/'live-api-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(item['industry'],response['totals']['amount'],elapsed,'seconds',flush=True)
    print('All eight guarded live API datasets reconcile exactly.',flush=True)

if __name__=='__main__':main()
