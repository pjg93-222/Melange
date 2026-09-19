"""Compare identical local assets/geometry with negotiated delivery modes."""
import gzip
import json
from pathlib import Path
import re
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=Path(__file__).resolve().parent
BASE='http://127.0.0.1:8813'

def read(path,headers=None,body=None):
    request=Request(BASE+path,headers=headers or {},data=json.dumps(body).encode() if body is not None else None)
    started=time.perf_counter()
    try:
        response=urlopen(request,timeout=90)
    except HTTPError as error:
        if error.code != 304:raise
        response=error
    with response:
        payload=response.read()
        return {'status':response.status,'bytes':len(payload),'seconds':time.perf_counter()-started,
                'etag':response.headers.get('ETag'),'encoding':response.headers.get('Content-Encoding')},payload

paths=sorted(set(re.findall(r'(?:src|href)="(/[^"?#]+\.(?:js|css))"', (ROOT/'mentat/app/index.html').read_text(encoding='utf-8'))))
results={}
for mode in ('identity','gzip','revalidated'):
    timings=[]; sizes=[]; statuses=[]
    for path in paths:
        headers={'Accept-Encoding':'gzip'} if mode=='gzip' else {'If-None-Match':etags[path]} if mode=='revalidated' else {}
        result,payload=read(path,headers)
        if mode=='identity':
            if 'etags' not in locals():etags={}; contents={}
            etags[path]=result['etag'];contents[path]=payload
        elif mode=='gzip':
            assert (gzip.decompress(payload) if result['encoding']=='gzip' else payload)==contents[path]
        else:assert result['status']==304 and payload==b''
        timings.append(result['seconds']);sizes.append(result['bytes']);statuses.append(result['status'])
    results[mode]={'asset_count':len(paths),'bytes':sum(sizes),'sequential_request_seconds':round(sum(timings),6),'statuses':sorted(set(statuses))}

_,session=read('/api/contributions/session')
token=json.loads(session)['token']
request={'zips':['02134'],'layers':['states','districts'],'congress':'119'}
geography={}
for mode in ('identity','gzip'):
    headers={'Content-Type':'application/json','X-Mentat-Token':token}
    if mode=='gzip':headers['Accept-Encoding']='gzip'
    result,payload=read('/api/contributions/geography',headers,request)
    decoded=gzip.decompress(payload) if result['encoding']=='gzip' else payload
    if mode=='identity':original=json.loads(decoded)
    else:assert json.loads(decoded)==original
    geography[mode]=result
results['geometry']=geography
target=OUTPUT/'delivery-after.json'
target.write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps(results,indent=2))
