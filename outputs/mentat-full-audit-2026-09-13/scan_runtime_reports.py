"""Read-only runtime, report ZIP/formula, and accepted-state audit."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
from urllib.request import urlopen
import zipfile
from xml.etree import ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
REPORTS=Path('C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files')
os.chdir(REPORTS)
sys.path.insert(0,str(ROOT/'mentat/app'))
import contribution_data as data
import contribution_workbook_guard as guard
import contribution_source_guard as source_guard
source_guard.CACHE_ROOT=OUT/'source-proof-cache'
N='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
R='{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'

def health(port):
    try:
        with urlopen(f'http://127.0.0.1:{port}/api/health',timeout=4) as response: value=json.load(response)
        value.pop('token',None)
        value.update(port=port,matches_working_server=value.get('server_code_sha256')==hashlib.sha256((ROOT/'mentat/app/server.py').read_bytes()).hexdigest())
        return value
    except Exception as error:return {'port':port,'error':str(error)}

runtime=list(ThreadPoolExecutor(max_workers=6).map(health,[8802,8803,8804,8808,8813,8841]))
(OUT/'runtime-health.json').write_text(json.dumps(runtime,indent=2),encoding='utf-8')
print('health '+json.dumps(runtime),flush=True)
sources=data._sources(REPORTS)
(OUT/'report-sources.json').write_text(json.dumps(sources,indent=2,default=str),encoding='utf-8')
checks=[]
for source in sources:
    if not source['available']:
        checks.append({'dataset':source['id'],'available':False,'message':source.get('message')})
        continue
    try:
        checks.extend(guard.verify_sources(REPORTS,source['id'],strict=False))
    except Exception as error: checks.append({'dataset':source['id'],'error':str(error)})
    (OUT/'source-checks.json').write_text(json.dumps(checks,indent=2,default=str),encoding='utf-8')
    print('source '+json.dumps(checks[-1],default=str),flush=True)

def book_scan(path):
    start=time.monotonic()
    initial=data._stamp(path)
    value={'path':str(path),'sha256':data._hash(path),'bytes':path.stat().st_size,'modified_utc':datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),'sheets':[]}
    with zipfile.ZipFile(path) as z:
        root=ET.fromstring(z.read('xl/workbook.xml'))
        rels={r.get('Id'):r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
        value['external_links']=[n for n in z.namelist() if n.startswith('xl/externalLinks/') and n.endswith('.xml')]
        value['macros']=[n for n in z.namelist() if n.endswith('vbaProject.bin')]
        for sheet in root.find(N+'sheets'):
            target=rels[sheet.get(R+'id')]
            target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
            count=formulas=missing_cache=0
            errors=[]
            bad_refs=[]
            with z.open(target) as stream:
                for event,element in ET.iterparse(stream,events=('end',)):
                    if element.tag==N+'row':
                        count+=1
                        for cell in element:
                            if cell.tag!=N+'c':continue
                            formula=cell.find(N+'f'); cached=cell.find(N+'v')
                            if cell.get('t')=='e':errors.append({'cell':cell.get('r'),'value':cached.text if cached is not None else None})
                            if formula is not None:
                                formulas+=1
                                if cached is None or cached.text is None:missing_cache+=1
                                if '#REF!' in (formula.text or ''):bad_refs.append(cell.get('r'))
                        element.clear()
            value['sheets'].append({'name':sheet.get('name'),'rows':count,'formula_cells':formulas,'formula_missing_cache':missing_cache,'error_count':len(errors),'errors':errors[:12],'broken_formula_refs':bad_refs[:12]})
    try:value['cycle_totals_cents']=guard.cycle_totals(initial)
    except Exception as error:value['cycle_totals_error']=str(error)
    value['unchanged_during_scan']=data._stamp(path)==initial
    value['seconds']=round(time.monotonic()-start,2)
    print('workbook '+json.dumps({'name':path.name,'sheets':len(value['sheets']),'errors':sum(s['error_count'] for s in value['sheets']),'formulas':sum(s['formula_cells'] for s in value['sheets']),'missing_caches':sum(s['formula_missing_cache'] for s in value['sheets']),'seconds':value['seconds']}),flush=True)
    return value

books=[]
for path in sorted(REPORTS.glob('*.xlsx')):
    try:books.append(book_scan(path))
    except Exception as error:books.append({'path':str(path),'error':str(error)})
    (OUT/'workbook-scan.json').write_text(json.dumps(books,indent=2),encoding='utf-8')

state=[]
for pointer in sorted((ROOT/'mentat/state/accepted-report-sources').glob('*/**/current.json')):
    value=json.loads(pointer.read_text(encoding='utf-8-sig'))
    result={'pointer':str(pointer),'industry':value.get('industry'),'status':value.get('status')}
    snapshot=Path(value.get('snapshot',''))
    result['snapshot_exists']=snapshot.is_file()
    if snapshot.is_file():
        result['snapshot_hash_matches']=data._hash(snapshot)==value.get('snapshot_sha256')
        with sqlite3.connect(snapshot.resolve().as_uri()+'?mode=ro',uri=True) as db:
            result['quick_check']=[r[0] for r in db.execute('PRAGMA quick_check')]
            result['facts']=db.execute('SELECT COUNT(*) FROM facts').fetchone()[0]
    state.append(result)
(OUT/'accepted-state-checks.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print('accepted_state '+json.dumps(state),flush=True)
