"""Read-only latency check for the existing guided Graph workspace."""
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

rows=[]
queries=['/api/graph-catalog?id=published-reports']
request={'id':'published-reports','industry':'Banking','company':'','tier':'','cycle':'','funding':'all','mode':'direct','direction':'Support','category':'','recipient':'','latest':'1'}
queries += ['/api/graph?'+urlencode(request)]*2
for endpoint in queries:
    started=time.perf_counter()
    with urlopen('http://127.0.0.1:8813'+endpoint,timeout=180) as response:
        body=response.read();result=json.loads(body)
    row={'endpoint':endpoint,'seconds':round(time.perf_counter()-started,6),'bytes':len(body),'totals':result.get('totals')}
    rows.append(row);print(json.dumps(row),flush=True)
    Path(__file__).with_name('guided-graph-baseline.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
