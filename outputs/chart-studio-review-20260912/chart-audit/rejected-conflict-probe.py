import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'mentat' / 'tools'))
from cross_reference_engine import analyze
from run_cross_reference import coalesce_source_observations

base = {'sub_id':'rejected-test', 'source_table':'contributions', 'company':'Example',
        'industry':'Example', 'company_match_status':'rejected', 'excluded_reason':'',
        'entity_type':'IND', 'filing_form':'F3', 'line_number':'11AI',
        'contribution_receipt_amount':100, 'contribution_receipt_date':'2024-01-01',
        'committee_id':'C00000001', 'contributor_name':'EXAMPLE, DONOR',
        'cycle':2024, 'current_receipt_cents':0, 'source_conflicts':[], 'attribution_claims':[]}
rows = [{**base, 'contributor_zip':'10001'}, {**base, 'contributor_zip':'10002'}]
canonical = coalesce_source_observations(rows)
decision = analyze(canonical)['decisions'][0]
print(json.dumps({'case':'all_rejected_metadata_conflict',
                  'canonical_match':canonical[0]['company_match_status'],
                  'conflicts':canonical[0]['source_conflicts'],
                  'decision':{k:decision[k] for k in ('counted_cents','baseline_cents','status','bucket','reasons')}}))

ledger=Path(r'C:\Users\pgoff\Mentat\mentat\state\cross-reference\20260912T204736-ed3b2a351279\ledger.sqlite')
with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as db:
    aggregates=defaultdict(lambda:[0,0])
    for payload, in db.execute('SELECT payload_json FROM links'):
        row=json.loads(payload)
        aggregates[row['kind']][0]+=1
        aggregates[row['kind']][1]+=row['amount_cents']
    print(json.dumps({'linked_exclusions_by_kind_count_signed_amount_cents':aggregates}))
