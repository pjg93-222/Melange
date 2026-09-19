import json,sys,sqlite3,re
from pathlib import Path
sys.path.insert(0,'mentat/app');import contribution_data as c
out=Path('outputs/chart-studio-implementation-20260912/source-only-observations.json')
result=json.loads(out.read_text()) if out.exists() else []
migration_path=out.parent/'cache-migration/receipt.json'
migrations=json.loads(migration_path.read_text()) if migration_path.exists() else []
for row in result:
 for migration in migrations:
  if row.get('industry')==migration['industry'] and row.get('provenance',{}).get('index_token')==migration['original_index_token'] and migration['status']=='passed':
   row['current_index_token']=migration['new_index_token']
   row['cache_compatibility']={'receipt':str(migration_path),'facts_sha256':migration['facts']['sha256'],'reason':'Every fact is unchanged under the explicit strict-date index compatibility copy.'}
for source in c._sources(Path(r'C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files')):
 cache=c.CACHE_ROOT/(c._token(source)+'.sqlite')
 if not cache.exists():continue
 if any(r.get('industry')==source['id'] and c._token(source) in (r.get('provenance',{}).get('index_token'),r.get('current_index_token')) and 'company_cycle_receipt_matches' in r for r in result):continue
 db=sqlite3.connect(':memory:',uri=True);db.execute('CREATE TABLE published(source_id TEXT PRIMARY KEY)')
 expected_groups={}
 for raw in c._payload_rows(source['payload']):
  db.execute('INSERT OR IGNORE INTO published VALUES (?)',(str(raw['source_id']),))
  if raw.get('include_in_analysis')=='Yes':
   if raw.get('date'):
    year=int(str(raw['date'])[:4]);cycle=year+year%2
   else:cycle=int(raw['cycle'])
   key=(str(raw.get('company') or ''),str(cycle-1)+'-'+str(cycle))
   expected_groups[key]=expected_groups.get(key,0)+c._cents(raw['amount'])
 db.execute('ATTACH DATABASE ? AS analytical',(cache.resolve().as_uri()+'?mode=ro',))
 db.row_factory=sqlite3.Row
 row=dict(db.execute('''SELECT COUNT(*) AS facts,COUNT(p.source_id) AS payload_ids,
 SUM(CASE WHEN p.source_id IS NULL THEN 1 ELSE 0 END) AS source_only_records,
 SUM(CASE WHEN p.source_id IS NULL THEN f.raw_cents ELSE 0 END) AS source_only_raw_cents,
 SUM(CASE WHEN p.source_id IS NULL THEN f.original_cents ELSE 0 END) AS source_only_original_cents,
 SUM(CASE WHEN p.source_id IS NULL THEN f.pac_cents ELSE 0 END) AS source_only_pac_cents
 FROM analytical.facts f LEFT JOIN published p USING(source_id)''').fetchone())
 row['source_only_by_status']=[dict(r) for r in db.execute('''SELECT decision_status,funding_source,COUNT(*) AS records,SUM(raw_cents) AS raw_cents,SUM(original_cents) AS original_cents FROM analytical.facts f LEFT JOIN published p USING(source_id) WHERE p.source_id IS NULL GROUP BY decision_status,funding_source''')]
 actual_groups={(r[0],r[1]):r[2] for r in db.execute('SELECT company,cycle,SUM(receipt_cents) FROM analytical.facts NOT INDEXED GROUP BY company,cycle')}
 row['company_cycle_mismatches']=[{'company':key[0],'cycle':key[1],'payload_cents':expected_groups.get(key,0),'index_cents':actual_groups.get(key,0)} for key in sorted(set(expected_groups)|set(actual_groups)) if expected_groups.get(key,0)!=actual_groups.get(key,0)]
 row['company_cycle_receipt_matches']=not row['company_cycle_mismatches']
 row['industry']=source['id'];row['provenance']={**c._provenance(source),'index_token':c._token(source)}
 result=[r for r in result if r.get('industry')!=source['id']]+[row]
 out.write_text(json.dumps(result,indent=2));print(json.dumps(row),flush=True);db.close()

# Reports apply this existing user-owned display register; compare economic
# company groups without losing the original source-label differences.
register=Path('mentat/R/ingest.R')
code=register.read_text(encoding='utf-8')
names=re.search(r'canonical_name\s*=\s*c\((.*?)\),\s*display_name\s*=\s*c\((.*?)\)',code,re.S)
aliases=dict(zip(re.findall(r'"([^"]*)"',names[1]),re.findall(r'"([^"]*)"',names[2])))
for row in result:
 if 'company_cycle_mismatches' not in row:continue
 raw=row.setdefault('raw_company_cycle_mismatches',row['company_cycle_mismatches'])
 normalized={}
 for mismatch in raw:
  key=(aliases.get(mismatch['company'],mismatch['company']),mismatch['cycle'])
  values=normalized.setdefault(key,[0,0])
  values[0]+=mismatch['payload_cents'];values[1]+=mismatch['index_cents']
 row['company_cycle_mismatches']=[{'company':k[0],'cycle':k[1],'payload_cents':v[0],'index_cents':v[1]} for k,v in sorted(normalized.items()) if v[0]!=v[1]]
 row['company_cycle_receipt_matches']=not row['company_cycle_mismatches']
 row['company_display_register']={'path':str(register),'sha256':c._hash(register),'aliases_applied':{k:v for k,v in aliases.items() if k!=v and any(x['company']==k for x in raw)}}
out.write_text(json.dumps(result,indent=2))

