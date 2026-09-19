"""Read-only independent compact payload comparison to original accepted facts."""
from collections import Counter
from contextlib import closing
from datetime import date
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'mentat/app'))
from contribution_data import _payload_metadata, _payload_rows

def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def cents(value):return int((Decimal(str(value))*100).quantize(Decimal('1')))
def normalized(value):return ' '.join(str(value or '').upper().split())

start=time.perf_counter()
pointer=ROOT/'mentat/state/accepted-report-sources/telecom/2022-2024-2026/current.json'
accepted=json.loads(pointer.read_text(encoding='utf-8-sig'))
snapshot=Path(accepted['snapshot'])
payload=ROOT/'mentat/.cache/industry-report/telecom/industry_data-34ef41793b3ab4c9.json'
assert sha(snapshot)==accepted['snapshot_sha256']
assert sha(payload)==accepted['payload_sha256']
with closing(sqlite3.connect(snapshot.resolve().as_uri()+'?mode=ro',uri=True)) as db:
    db.execute('PRAGMA query_only=ON')
    original=dict(db.execute('SELECT id,raw FROM facts'))
counts=Counter();cycles=Counter();receipt_cents=Counter();mismatches=[];seen=set();keys=Counter()
for row in _payload_rows(payload):
    counts['payload_rows']+=1;keys.update(row.keys())
    sid=str(row['source_id'])
    if sid in seen:counts['duplicate_payload_ids']+=1
    seen.add(sid)
    if sid not in original:
        counts['missing_from_snapshot']+=1
        continue
    raw=json.loads(original[sid]);day=date.fromisoformat(raw['date']);cycle=day.year+day.year%2
    fields=[]
    if cents(row['amount'])!=raw['amount_cents']:fields.append('amount')
    if normalized(row.get('contributor'))!=normalized(raw.get('contributor_name')):fields.append('contributor')
    if str(row.get('committee_id') or '')!=str(raw.get('committee_id') or ''):fields.append('committee_id')
    if int(row['cycle'])!=cycle:fields.append('cycle')
    if row.get('cycle_label')!=f'{cycle-1}-{cycle}':fields.append('cycle_label')
    if 'date' not in row:counts['date_key_absent']+=1
    elif str(row.get('date') or '')[:10]!=raw['date']:fields.append('date')
    if fields:
        counts['mismatched_rows']+=1
        if len(mismatches)<10:mismatches.append({'id':sid,'fields':fields,'raw':raw,'payload':row})
    cycles[str(cycle)]+=1
    if row.get('include_in_analysis')=='Yes':receipt_cents[str(cycle)]+=cents(row['amount'])
metadata=_payload_metadata(payload)
result={'payload':str(payload),'payload_sha256':accepted['payload_sha256'],
    'snapshot':str(snapshot),'snapshot_sha256':accepted['snapshot_sha256'],
    'original_database_sha256':accepted['database_sha256'],
    'payload_compaction':metadata.get('payload_compaction'),
    'snapshot_financial_ids':len(original),'counts':dict(counts),
    'source_date_derived_cycle_counts':dict(cycles),'receipt_cents_by_cycle':dict(receipt_cents),
    'all_payload_keys':sorted(keys),'mismatches':mismatches,'seconds':round(time.perf_counter()-start,2)}
out=Path(__file__).with_suffix('.json')
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
assert not mismatches and not counts['missing_from_snapshot'] and not counts['duplicate_payload_ids']
