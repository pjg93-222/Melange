"""Offline audit probes. All database mutations are confined to ./fixtures/."""
import sys
sys.dont_write_bytecode = True
import json
import sqlite3
from pathlib import Path
from contextlib import closing
import uuid

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2] / 'mentat'
sys.path.insert(0, str(PROJECT / 'tools'))
from report_source_guard import prepare, check_payload, accept
from run_cross_reference import baseline_rows, coalesce_source_observations
from cross_reference_engine import analyze

fixture = ROOT / 'fixtures' / uuid.uuid4().hex
fixture.mkdir(parents=True)

def source_db(directory):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'source.db'
    with closing(sqlite3.connect(path)) as db, db:
        for table in ('contributions', 'corporate_giving'):
            db.execute(f'CREATE TABLE {table}(sub_id TEXT, industry TEXT, company TEXT, committee_id TEXT, contributor_name TEXT, contribution_receipt_date TEXT, contribution_receipt_amount REAL)')
        db.execute("INSERT INTO contributions VALUES('1','Fixture','Acme','C00000001','PERSON, ONE','2024-01-01',100)")
    return path

base_row = dict(source_id='1', cycle=2024, amount=100, company='Acme',
                committee_id='C00000001', contributor='PERSON, ONE', date='2024-01-01',
                include_in_analysis='Yes', inclusion_reason='Included',
                receipt_role='contribution', filing_form='F3X', line_number='11AI')

# An accepted cycle should not disappear simply because the next report is wider.
case = fixture / 'scope_expansion'
database = source_db(case)
receipt, payload, states = case/'receipt.json', case/'payload.json', case/'states'
prepare(database, 'Fixture', (2024,), states, receipt)
payload.write_text(json.dumps({'metadata': {'industry': 'Fixture'}, 'raw_rows': [base_row]}))
check_payload(receipt, payload)
accept(receipt)
with closing(sqlite3.connect(database)) as db, db:
    db.execute('DELETE FROM contributions')
    db.execute("INSERT INTO contributions VALUES('2','Fixture','Acme','C00000001','PERSON, TWO','2026-01-01',25)")
result = prepare(database, 'Fixture', (2022, 2024, 2026), states, case/'wider.json')
runner_baseline, runner_info = baseline_rows(states, 'Fixture', (2022,2024,2026))
payload.write_text(json.dumps({'metadata': {'industry': 'Fixture'},
    'raw_rows':[dict(base_row, source_id='2', cycle=2026, amount=25, contributor='PERSON, TWO',date='2026-01-01')]}))
check_payload(case/'wider.json', payload)
wider_accepted=accept(case/'wider.json')
findings = {'scope_expansion': {'status': result['status'], 'counts': result['counts'],
    'comparison_baseline': result['previous'], 'runner_baseline_count': len(runner_baseline),
    'runner_baseline_info': runner_info, 'wider_accept_status':wider_accepted['status'],
    'expected': 'block missing accepted 2024 source 1'}}

# The persisted source facts include donor/committee/date but the payload check omits them.
case = fixture / 'identity'
database = source_db(case)
receipt, payload = case/'receipt.json', case/'payload.json'
prepare(database, 'Fixture', (2024,), case/'states', receipt)
payload.write_text(json.dumps({'metadata': {'industry':'Fixture'}, 'raw_rows':[base_row]}))
check_payload(receipt,payload)
accept(receipt)
prepare(database, 'Fixture', (2024,), case/'states', receipt)
wrong = dict(base_row, committee_id='C99999999', contributor='DIFFERENT, DONOR', date='2024-12-31')
payload.write_text(json.dumps({'metadata': {'industry':'Fixture'}, 'raw_rows':[wrong]}))
checked = check_payload(receipt, payload)
accepted = accept(receipt)
findings['payload_identity'] = {'check_status':checked['status'], 'accept_status':accepted['status'],
    'changed_decisions':checked['changed_decisions'], 'delta_cents':checked['delta_cents'],
    'source': {k:base_row[k] for k in ('committee_id','contributor','date')},
    'payload': {k:wrong[k] for k in ('committee_id','contributor','date')},
    'expected':'reject changed financial identity'}

def source(sid, **changes):
    value = dict(sub_id=sid, source_table='contributions', company='Acme',industry='Fixture',
        cycle=2024,current_receipt_cents=10000,contribution_receipt_amount=100,
        contributor_name='PERSON, ONE', contribution_receipt_date='2024-01-01',
        committee_id='C00000001',transaction_id=sid,file_num=10,filing_form='F3X',
        line_number='11AI',entity_type='IND',company_match_status='accepted',memo_code='',
        attribution_claims=[],source_conflicts=[])
    value.update(changes)
    return value

# Blank versus X is explicit non-memo versus memo evidence, not missing identity.
parent = source('parent', transaction_id='TX')
ordinary = source('child', back_reference_transaction_id='TX')
memo = dict(ordinary, source_table='corporate_giving', memo_code='X')
coalesced = coalesce_source_observations([parent, ordinary, memo])
analyzed = analyze(coalesced)
findings['conflicting_memo_observations'] = {
    'input_physical_observations':3, 'distinct_source_ids':2,
    'observed_memo_codes':['','X'],
    'merged_child_conflicts':next(r for r in coalesced if r['sub_id']=='child')['source_conflicts'],
    'counted_cents':analyzed['totals']['provisional_original_giving_cents'],
    'child_decision':next(d for d in analyzed['decisions'] if d['source_id']=='child'),
    'review_queue':analyzed['review_queue'],
    'expected':'hold conflicting child memo evidence; do not silently exclude its $100'}

findings['fixture_directory'] = str(fixture)
out = ROOT / 'reproduction-results.json'
out.write_text(json.dumps(findings,indent=2),encoding='utf-8')
print(json.dumps(findings,indent=2))
