"""Guarded API checks for expanded Tableau-like analysis, no source writes."""
import gzip,json,time
from pathlib import Path
from urllib.request import Request,urlopen
BASE='http://127.0.0.1:8813'
OUT=Path(__file__).resolve().parent
def call(path,body=None):
    headers={'Accept-Encoding':'gzip','Content-Type':'application/json'}
    if body is not None:headers['X-Mentat-Token']=token
    start=time.perf_counter()
    with urlopen(Request(BASE+path,headers=headers,data=json.dumps(body).encode() if body is not None else None),timeout=180) as r:
        raw=r.read();value=json.loads(gzip.decompress(raw) if r.headers.get('Content-Encoding')=='gzip' else raw)
    return value,round(time.perf_counter()-start,4)
token=call('/api/contributions/session')[0]['token']
catalog,seconds=call('/api/contributions/catalog')
assert len(catalog['datasets'])==8
assert len(catalog['fields'])==94
reports={'catalog_seconds':seconds,'field_count':len(catalog['fields']),'dimensions':sum(f['role']=='dimension' for f in catalog['fields']),'measures':sum(f['role']=='measure' for f in catalog['fields']),'sources':[],'analyses':[]}
expected={'Banking':5476284405,'Community Banks':86350598,'Credit Arms':2393244525,'Credit Union':142200565,'Crypto':24994948317,'Fintech':980389131,'Property & Casualty Insurance':1668736559,'Telecom':3769812109}
for item in catalog['datasets']:
    request={'dataset':item['id'],'basis':'receipt','dimensions':['company'],'measures':['amount'],'filters':[],'aggregate_filters':[],'sort':[{'field':'amount','direction':'desc'}],'limit':40,'offset':0}
    result,elapsed=call('/api/contributions/query',request)
    assert result['status']=='ready',result
    assert result['totals']['amount']==expected[item['id']]
    assert result['reconciliation']['conserved'] and result['reconciliation']['receipt_matches_workbook']
    repeat,repeat_time=call('/api/contributions/query',request);assert repeat==result
    reports['sources'].append({'dataset':item['id'],'seconds':elapsed,'repeat_seconds':repeat_time,'total_cents':result['totals']['amount'],'provenance':result['provenance']})
    print(item['id'],elapsed,repeat_time,flush=True)
for name,options in [
 ('month-party',{'dimensions':['month','party'],'measures':['amount','records'],'limit':10000}),
 ('histogram',{'dimensions':['amount_bin'],'measures':['records','amount'],'bin_width_cents':10000,'sort':[{'field':'amount_bin','direction':'asc'}],'limit':10000}),
 ('box',{'dimensions':['company'],'measures':['min_amount','q1_amount','median_amount','q3_amount','max_amount'],'limit':1000}),
 ('date-span',{'dimensions':['company'],'measures':['first_date','last_date','span_days'],'limit':1000}),
 ('filing-metadata',{'dimensions':['reported_filing_form','reported_amendment_indicator'],'measures':['amount','records'],'limit':1000}),
 ('source-audit',{'dimensions':['source_table','review_required'],'measures':['amount','records','committees'],'limit':1000})]:
    request={'dataset':'Banking','basis':'receipt',**options}
    result,elapsed=call('/api/contributions/query',request)
    assert result['totals']['amount']==expected['Banking'] and result['reconciliation']['conserved']
    assert not result['has_more']
    repeat,repeat_time=call('/api/contributions/query',request);assert repeat==result
    reports['analyses'].append({'name':name,'request':request,'seconds':elapsed,'repeat_seconds':repeat_time,'result':result})
    print(name,elapsed,len(result['rows']),flush=True)
OUT.joinpath('live-validation.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
OUT.joinpath('field-catalog.json').write_text(json.dumps(catalog['fields'],indent=2),encoding='utf-8')
print('All sources and analytical families reconciled.',flush=True)
