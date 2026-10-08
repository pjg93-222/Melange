import sys, json, re
sys.path.insert(0,'.')
from osc.fetch import Fetcher
from bs4 import BeautifulSoup
D='C:/melange-data/forecast-redesign-20261001-review/standardized-collector/data'
f=Fetcher(D,cache_only=True)
u=sys.argv[1]; r=f.get(u)
s=BeautifulSoup(r.text,'html.parser')
print('TITLE',s.title.get_text(strip=True) if s.title else None)
for h in s.select('h1,h2'): print('H',h.name,h.get_text(' ',strip=True)[:120])
for i,t in enumerate(s.select('table')):
    dc=t.get('data-collection')
    hd=[th.get_text(' ',strip=True) for th in t.select('thead th')] or [c.get_text(' ',strip=True) for c in t.select('tr')[0].select('th,td')] if t.select('tr') else []
    n=None; first=None
    if dc:
        try: j=json.loads(dc); n=len(j); first=j[0] if j else None
        except Exception as e: n='ERR'
    print('TABLE',i,t.get('class'),'rows_html',len(t.select('tbody tr')),'dc',n,'hdr',hd[:10]); 
    if first: print('   first',json.dumps(first)[:400])
    if dc is None and t.select('tbody tr'): print('   firsthtml',[c.get_text(' ',strip=True) for c in t.select('tbody tr')[0].select('td,th')])
for sel in s.select('select'):
    print('SELECT',sel.get('name'),sel.get('id'),[(o.get('value'),o.get_text(strip=True)) for o in sel.select('option')][:30],'SEL=',[o.get_text(strip=True) for o in sel.select('option[selected]')])
for el in s.select('[data-source]'):
    try: j=json.loads(el['data-source']); print('DATASRC',el.name,el.get('class'),str(j)[:300])
    except Exception as e: print('DATASRC bad',str(el['data-source'])[:100])
txt=s.get_text(' ',strip=True)
for m in re.finditer(r'.{0,100}(released|Downloaded|as of|updated)[^.]{0,120}\.',txt): print('NOTE',m.group(0)[:260])
