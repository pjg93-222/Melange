import json, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

root = Path(__file__).parent
for url in sys.argv[1:]:
    response = requests.get(url, timeout=40, headers={'User-Agent':'MentatResearchCollector/1.0'})
    response.encoding = 'utf-8'
    soup = BeautifulSoup(response.text, 'html.parser')
    import hashlib
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    (root / 'probe_cache').mkdir(exist_ok=True)
    (root / 'probe_cache' / (key+'.html')).write_text(response.text, encoding='utf-8')
    tables = [[[c.get_text(' ',strip=True) for c in r.select('th,td')] for r in t.select('tr')] for t in soup.select('table')]
    links = [(a.get_text(' ',strip=True), a.get('href')) for a in soup.select('a[href]') if any(k in a.get('href','') for k in ['/industries/','/federal-lobbying/','/elections-overview/','/political-action-committees','/pacs/','/industries.php'])]
    text = soup.get_text(' ',strip=True)
    record = {'url':url,'status':response.status_code,'title':soup.title.get_text() if soup.title else '', 'tables':tables, 'links':[(a.get_text(' ',strip=True),a.get('href')) for a in soup.select('main a[href], #main a[href]')], 'selects':[(s.get('name'),[(o.get_text(),o.get('value')) for o in s.select('option')]) for s in soup.select('select')], 'text':text}
    (root / 'probe_cache' / (key+'.json')).write_text(json.dumps(record,ensure_ascii=True),encoding='utf-8')
    print(json.dumps({**{k:record[k] for k in ['url','status','title']},'tables':[t[:3] for t in tables], 'links':[x for x in record['links'] if any(z in (x[0]+' '+x[1]).lower() for z in ['pac','individual','in-house','outside','tele','life','crypto'])][-30:]}, ensure_ascii=True),flush=True)
    time.sleep(1)
