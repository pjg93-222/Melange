import json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,r'C:\Users\pgoff\Mentat\mentat\app')
import contribution_data as c
from run_cross_reference import coalesce_source_observations

def raw(company,status):
 return {'sub_id':'test-source','source_table':'contributions','company':company,'industry':'Example','company_match_status':status,'excluded_reason':'','entity_type':'IND','filing_form':'F3','line_number':'11AI','contribution_receipt_amount':100,'contribution_receipt_date':'2024-01-01','committee_id':'C00000001','contributor_name':'EXAMPLE, DONOR','cycle':2024,'current_receipt_cents':0,'source_conflicts':[],'attribution_claims':[]}
for statuses in [('rejected','accepted'),('rejected','rejected')]:
 rows=[raw('A',statuses[0]),raw('B',statuses[1])]
 # Exact present fallback: sorted company partition + first seen source + all claims asserted accepted.
 fallback=dict(rows[0]);fallback['attribution_claims']=[{'company':r['company'],'status':'accepted'} for r in rows]
 result=c.analyze(coalesce_source_observations([fallback]))['decisions'][0]
 canonical=c.analyze(coalesce_source_observations(rows))['decisions'][0]
 print(json.dumps({'case':'cross_company_first_seen','statuses':statuses,'current':{k:result[k] for k in ['company','counted_cents','status','bucket','reasons']},'canonical':{k:canonical[k] for k in ['company','counted_cents','status','bucket','reasons']}}))

source=Path(r'C:\Users\pgoff\Mentat\mentat\.cache\report-repairs\banking-20260910\data\mentat.db')
db=sqlite3.connect(source.as_uri()+'?mode=ro',uri=True);db.execute('PRAGMA query_only=ON')
for name in ['contributions','corporate_giving','attribution_claims','attribution_conflicts','source_record_conflicts']:
 try:
  count=db.execute('SELECT COUNT(*) FROM '+name).fetchone()[0]
  print(json.dumps({'table':name,'count':count,'schema':db.execute('PRAGMA table_info('+name+')').fetchall() if 'conflict' in name or 'claims' in name else []}))
 except Exception as e:print(json.dumps({'table':name,'error':str(e)}))
meta=c._payload_metadata(Path(r'C:\Users\pgoff\Mentat\mentat\.cache\industry-report\banking\industry_data-4abdea581b99cec1.json'))
print(json.dumps({'expected_cycle_totals':meta.get('expected_cycle_totals'),'expected_sum_cents':sum(c._cents(x) for x in meta.get('expected_cycle_totals',{}).values()),'metadata_keys':list(meta)}))
