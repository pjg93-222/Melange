import sys, time
sys.path.insert(0,'.')
from osc.fetch import Fetcher
D='C:/melange-data/forecast-redesign-20261001-review/standardized-collector/data'
f=Fetcher(D,concurrency=2,min_interval=0.5)
urls=sys.argv[1:]
t=time.time()
for u in urls:
    r=f.get(u)
    print(r.status, len(r.body or b''), r.meta.get('transport'), r.meta.get('final_url'), r.meta.get('error'))
print(f.stats, round(time.time()-t,1))
