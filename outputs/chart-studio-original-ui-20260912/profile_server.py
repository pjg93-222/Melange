"""Measure local read-only endpoints without copying response contents."""
import argparse
import json
from pathlib import Path
import time
from urllib.request import urlopen

OUTPUT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--label',default='after')
parser.add_argument('--full',action='store_true')
options=parser.parse_args()
rows=[]
endpoints=['health','session?light=1','report-sources','reports?id=published-reports','contributions/catalog']
if options.full:endpoints += ['session?include_archived=1','runs?include_archived=1']
for endpoint in endpoints:
    samples=[]
    for _ in range(1 if 'include_archived' in endpoint else 3):
        start=time.perf_counter()
        with urlopen('http://127.0.0.1:8813/api/'+endpoint,timeout=180) as response:
            payload=response.read()
            status=response.status
        samples.append(round(time.perf_counter()-start,6))
    row={'endpoint':endpoint,'seconds':samples,'bytes':len(payload),'status':status}
    rows.append(row)
    print(json.dumps(row),flush=True)
    (OUTPUT/('server-'+options.label+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
