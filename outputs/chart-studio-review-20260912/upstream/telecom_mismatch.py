import json,sys,sqlite3,time
from pathlib import Path
sys.path.insert(0,'mentat/app');import contribution_data as c
start=time.monotonic();source=c._source(Path(r'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files'),{'dataset':'Telecom'})
db=sqlite3.connect(':memory:',uri=True)
db.execute('CREATE TABLE published(source_id TEXT PRIMARY KEY,amount INTEGER,committee TEXT,day TEXT,name TEXT,company TEXT,included TEXT,cycle INTEGER)')
for raw in c._payload_rows(source['payload']):
 db.execute('INSERT OR REPLACE INTO published VALUES (?,?,?,?,?,?,?,?)',(str(raw['source_id']),c._cents(raw['amount']),str(raw.get('committee_id') or ''),str(raw.get('date') or '')[:10],' '.join(str(raw.get('contributor') or '').upper().split()),str(raw.get('company') or ''),raw.get('include_in_analysis'),raw.get('cycle')))
db.execute('ATTACH DATABASE ? AS source',(source['database'].resolve().as_uri()+'?mode=ro',))
results=[];counts={};matched=0;omitted_dates=0;mismatch_count=0
for table in ('contributions','corporate_giving'):
 query=f'''SELECT s.sub_id,s.contribution_receipt_amount,s.committee_id,s.contribution_receipt_date,s.contributor_name,s.company,p.*
 FROM source.{table} s JOIN published p ON p.source_id=CAST(s.sub_id AS TEXT) WHERE s.industry='Telecom' '''
 for sid,amount,committee,day,name,company,psid,pamount,pcommittee,pday,pname,pcompany,pincluded,pcycle in db.execute(query):
  matched+=1;year=int(str(day)[:4])
  actual={'amount_cents':c._cents(amount),'committee':str(committee or ''),'date':str(day or '')[:10],'name':' '.join(str(name or '').upper().split()),'cycle':year+year%2}
  expected={'amount_cents':pamount,'committee':pcommittee,'date':pday,'name':pname,'cycle':pcycle}
  if not pday:omitted_dates+=1;expected['date']=actual['date']
  differences={k:{'source':actual[k],'payload':expected[k]} for k in actual if actual[k]!=expected[k]}
  if differences:
   mismatch_count+=1
   if len(results)<100:results.append({'source_id':sid,'source_table':table,'source_company':company,'payload_company':pcompany,'included':pincluded,'differences':differences})
   for k in differences:counts[k]=counts.get(k,0)+1
out={'dataset':'Telecom','seconds':round(time.monotonic()-start,2),'provenance':c._provenance(source),'matched_source_observations':matched,'payload_dates_omitted':omitted_dates,'mismatch_count':mismatch_count,'field_counts':counts,'mismatches':results,'note':'Compact payload supplies cycle, not date. Dates remain verified against the complete original source snapshot; this check verifies the payload cycle against each source date.'}
Path('outputs/chart-studio-implementation-20260912/telecom-payload-mismatch.json').write_text(json.dumps(out,indent=2))
print(json.dumps({**out,'mismatches':results[:30]}),flush=True)
