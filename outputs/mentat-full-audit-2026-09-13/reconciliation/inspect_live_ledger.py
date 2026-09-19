"""Read-only verification of the current cross-reference snapshot."""
import hashlib
import json
import sqlite3
import time
from pathlib import Path
from contextlib import closing

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[2] / 'mentat'
ROOT = PROJECT / 'state/cross-reference'
started = time.monotonic()
latest = json.loads((ROOT/'latest.json').read_text())
directory = ROOT / latest['run_id']
report_path, ledger_path = directory/'report.json', directory/'ledger.sqlite'
report = json.loads(report_path.read_text())
def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()
before = {p.name:(p.stat().st_size,p.stat().st_mtime_ns) for p in (report_path,ledger_path)}
wal=Path(str(ledger_path)+'-wal')
if wal.exists() and wal.stat().st_size:
    raise ValueError('Live ledger has an active WAL, audit requires quiescence')
result = dict(run_id=latest['run_id'], industry=report['scope']['industries'],
    report_sha256=sha(report_path), ledger_bytes=ledger_path.stat().st_size)
result['report_hash_matches_pointer'] = result['report_sha256']==latest['report_sha256']
print(json.dumps({'phase':'report_hash','matches':result['report_hash_matches_pointer']}),flush=True)
result['ledger_sha256']=sha(ledger_path)
result['ledger_hash_matches_report']=result['ledger_sha256']==report['ledger_sha256']
print(json.dumps({'phase':'ledger_hash','matches':result['ledger_hash_matches_report']}),flush=True)
with closing(sqlite3.connect(ledger_path.as_uri()+'?mode=ro',uri=True)) as db:
    db.execute('PRAGMA query_only=ON')
    result['sqlite_quick_check']=[r[0] for r in db.execute('PRAGMA quick_check')]
    print(json.dumps({'phase':'quick_check','result':result['sqlite_quick_check']}),flush=True)
    tables=('source_records','decisions','changes','links','review_queue','coverage_queue',
            'evidence','filing_headers','evidence_documents','evidence_observations')
    result['table_counts']={t:db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in tables}
    result['source_distinct_ids']=db.execute('SELECT count(DISTINCT source_id) FROM source_records').fetchone()[0]
    result['decision_distinct_ids']=db.execute('SELECT count(DISTINCT source_id) FROM decisions').fetchone()[0]
    result['decision_totals']=dict(zip(['baseline_cents','original_cents','pac_activity_cents','supported_unique_cents'],
        db.execute("SELECT sum(json_extract(payload_json,'$.baseline_cents')), sum(json_extract(payload_json,'$.counted_cents')), sum(json_extract(payload_json,'$.pac_activity_cents')), sum(json_extract(payload_json,'$.supported_unique_cents')) FROM decisions").fetchone()))
    result['ledger_metadata_totals']=json.loads(db.execute("SELECT payload_json FROM run_metadata WHERE name='totals'").fetchone()[0])
    result['ledger_change_delta_cents']=db.execute("SELECT sum(json_extract(payload_json,'$.delta_cents')) FROM changes").fetchone()[0]
    overlaps=[r[0] for r in db.execute('SELECT source_id FROM source_records GROUP BY source_id HAVING count(*)>1')]
    result['same_id_observation_groups']=len(overlaps)
    memo_conflicts=[]
    for sid in overlaps:
        rows=[json.loads(r[0]) for r in db.execute('SELECT payload_json FROM source_records WHERE source_id=?',(sid,))]
        codes={str(r.get('memo_code') or '') for r in rows}
        if '' in codes and 'X' in codes:
            memo_conflicts.append(sid)
    result['same_id_blank_vs_x_memo_conflicts']=memo_conflicts
summary=report['summary'];scope=report['scope'];counts=result['table_counts'];totals=result['decision_totals']
result['consistency_checks']={
    'source_observation_count':counts['source_records']==scope['source_observations'],
    'source_distinct_count':result['source_distinct_ids']==scope['distinct_source_ids'],
    'decision_count':counts['decisions']==result['decision_distinct_ids']==summary['input_records'],
    'link_count':counts['links']==report['link_count'],
    'coverage_task_count':counts['coverage_queue']==report['coverage_task_count'],
    'baseline_amount':round(summary['baseline_amount']*100)==totals['baseline_cents'],
    'original_giving_amount':round(summary['observed_original_giving']*100)==totals['original_cents'],
    'pac_outgoing_amount':round(summary['pac_outgoing']*100)==totals['pac_activity_cents'],
    'supported_unique_amount':round(summary['supported_original_giving']*100)==totals['supported_unique_cents'],
    'cent_reconciliation':totals['baseline_cents']+result['ledger_change_delta_cents']==totals['original_cents']}
result['unchanged_during_check']=before=={p.name:(p.stat().st_size,p.stat().st_mtime_ns) for p in (report_path,ledger_path)}
result['pointer_unchanged']=latest==json.loads((ROOT/'latest.json').read_text())
result['elapsed_seconds']=round(time.monotonic()-started,2)
(OUT/'live-ledger-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2),flush=True)
