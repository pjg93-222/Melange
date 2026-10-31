"""audit_full [SYNC] live-sync gate: check names, edge-file re-hash, chain-tail guard literal, journal verdict, and the
audit/live_sync.py sub-checks (pass / fail / skip each).

Source text and tmp_path fixtures only; audit_full itself is never run (it executes the engine at import).
"""
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timedelta, timezone

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if FEC not in sys.path:
    sys.path.insert(0, FEC)

import chain_transaction as C
import refresh_tick as R
from audit import live_sync as L

LIVE_SYNC = ('live_sync_chain_journal_closed', 'live_sync_sentinel_ledger_sha', 'live_sync_staffer_inputs_bound',
             'live_sync_press_body_ledger_sha', 'live_sync_status_files_consistent')


def _read(*parts):
    with open(os.path.join(FEC, *parts), encoding='utf-8') as handle:
        return handle.read()


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _dump(path, doc):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding='utf-8')
    return str(path)


# ---- source text -----------------------------------------------------------------------------------------------------------

def test_audit_full_names_every_live_sync_check_and_rehashes_the_edge_file():
    src = _read('audit', 'audit_full.py')
    for name in LIVE_SYNC:
        assert "_live_sync('%s'," % name in src, name
    assert '[SYNC] Live sync: ledgers, snapshots, chain' in src
    # The staffer re-hash loop must not exempt the not_recomputed (edge) record or skip on size.
    loop = src[src.index("for _role,_rec in sorted((_staff_meta.get('inputs')"):src.index("ck('staffer_section_inputs_current'")]
    assert 'not_recomputed' not in loop and 'staffer_social_edges' not in loop
    assert not re.search(r'getsize|bytes', loop)
    assert '1.5 GB' not in src


def test_weekly_refresh_guard_requires_the_literal():
    src = _read('weekly_refresh.py')
    body = src[src.index('def _chain_tail_is_audit_full'):]
    body = body[:body.index('\ndef ')]
    assert "\"'live_sync_chain_journal_closed'\" not in audit_src" in body


CHAIN = "CHAIN = [\n    ('compute_pillars.py', []),\n    ('audit_full.py', []),\n]\n"


def _tree(tmp_path, audit_text):
    fec = tmp_path / 'fec'
    (fec / 'audit').mkdir(parents=True)
    (fec / 'run_pipeline.py').write_text(CHAIN, encoding='utf-8')
    if audit_text is not None:
        (fec / 'audit' / 'audit_full.py').write_text(audit_text, encoding='utf-8')
    return str(fec / 'run_pipeline.py')


def test_chain_tail_guard_with_and_without_the_literal(tmp_path):
    logs = []
    live = _read('audit', 'audit_full.py')
    assert R._chain_tail_is_audit_full(_tree(tmp_path / 'a', live), logs.append) is True
    stripped = live.replace("'live_sync_chain_journal_closed'", "'renamed_check'")
    assert R._chain_tail_is_audit_full(_tree(tmp_path / 'b', stripped), logs.append) is False
    assert R._chain_tail_is_audit_full(_tree(tmp_path / 'c', None), logs.append) is False
    assert any('live_sync_chain_journal_closed' in line for line in logs)
    assert any('cannot read audit_full.py' in line for line in logs)


# ---- chain journal ---------------------------------------------------------------------------------------------------------

ROOT = os.path.abspath(os.sep + 'melange_root')
NOW = datetime.now(timezone.utc)
CLEAN = {'counts': {'errors': 0, 'unrestorable_modified': 0, 'unrestorable_missing': 0, 'restored': 3}}
DEAD = dict(alive=lambda pid: False, start_time=lambda pid: None)


def _stamp(when):
    return when.strftime('%Y-%m-%dT%H:%M:%SZ')


def _journal(base, name, state, pid=1, rollback=None, root=ROOT, started=NOW):
    doc = {'schema': C.SCHEMA, 'state': state, 'run_id': name, 'pid': pid, 'root': root, 'started_utc': _stamp(started)}
    if rollback is not None:
        doc['rollback'] = rollback
    _dump(base / name / 'journal.json', doc)


def test_journal_states(tmp_path):
    assert C.journal_closed(ROOT, [str(tmp_path / 'none')], **DEAD) is None
    cases = [('OPEN', None, False), ('COMMITTED', None, True), ('ROLLED_BACK', CLEAN, True),
             ('ROLLED_BACK', {'counts': {'errors': 1, 'unrestorable_modified': 0, 'unrestorable_missing': 0}}, False),
             ('ROLLED_BACK', None, False), ('ROLLBACK_FAILED', CLEAN, False)]
    for i, (state, rollback, want) in enumerate(cases):
        base = tmp_path / str(i)
        _journal(base, '20261001T000000Z-old', 'COMMITTED')
        _journal(base, '20261028T000000Z-new', state, rollback=rollback)
        ok, detail = C.journal_closed(ROOT, [str(base)], **DEAD)
        assert ok is want, (state, rollback, detail)
        assert '20261028T000000Z-new' in detail


def test_live_open_journal_is_the_running_chain_and_falls_through(tmp_path):
    _journal(tmp_path, '20261027T000000Z-prev', 'ROLLED_BACK', rollback=CLEAN)
    _journal(tmp_path, '20261028T000000Z-this', 'OPEN', pid=os.getpid())   # this process began before NOW: it owns it
    ok, detail = C.journal_closed(ROOT, [str(tmp_path)])
    assert ok is True and '20261027T000000Z-prev' in detail and 'live OPEN skipped' in detail
    assert C.journal_closed(ROOT, [str(tmp_path)], **DEAD)[0] is False   # same OPEN, owner dead: never finalized
    shutil.rmtree(tmp_path / '20261027T000000Z-prev')
    assert C.journal_closed(ROOT, [str(tmp_path)]) is None   # only the running chain's own journal


def test_open_journal_older_than_its_live_pid_is_a_recycled_pid(tmp_path):
    _journal(tmp_path, '20261028T000000Z-old', 'OPEN', pid=os.getpid(), started=NOW - timedelta(days=3650))
    ok, detail = C.journal_closed(ROOT, [str(tmp_path)])
    assert ok is False and 'state=OPEN' in detail


def test_foreign_root_journals_are_ignored(tmp_path):
    _journal(tmp_path, '20261027T000000Z-mine', 'COMMITTED')
    _journal(tmp_path, '20261028T000000Z-foreign', 'OPEN', root=os.path.abspath(os.sep + 'other_root'))
    ok, detail = C.journal_closed(ROOT, [str(tmp_path)], **DEAD)
    assert ok is True and '20261027T000000Z-mine' in detail


# ---- sentinel ledger -------------------------------------------------------------------------------------------------------

def test_sentinel_ledger(tmp_path):
    ledger = tmp_path / 'Sentinel Bill Ledger.xlsx'
    ledger.write_bytes(b'workbook')
    receipt = tmp_path / 'receipt.json'
    good = {'path': str(ledger), 'sha256': _sha(b'workbook'), 'size': 8}
    assert L.sentinel_ledger(str(tmp_path / 'absent.json'), str(ledger)) is None
    _dump(receipt, {'status': 'SKIPPED_RUNTIME_ABSENT', 'live_ledger_workbook': None})
    assert L.sentinel_ledger(str(receipt), str(ledger)) is None
    _dump(receipt, {'live_ledger_workbook': good})
    assert L.sentinel_ledger(str(receipt), str(ledger))[0] is True
    assert L.sentinel_ledger(str(receipt), str(ledger), cached_sha='0' * 64)[0] is False   # the cached hash is used
    _dump(receipt, {'live_ledger_workbook': dict(good, size=9)})
    assert L.sentinel_ledger(str(receipt), str(ledger))[0] is False
    _dump(receipt, {'live_ledger_workbook': dict(good, path=str(tmp_path / 'gone.xlsx'))})
    assert L.sentinel_ledger(str(receipt), str(ledger))[0] is False


# ---- staffer inputs --------------------------------------------------------------------------------------------------------

def test_staffer_inputs(tmp_path):
    section = tmp_path / 'staffer_network_section.json'
    inputs = {'staffer_social_edges': {'sha256': 'a' * 64}, 'staffer_trajectories': {'sha256': 'b' * 64}}
    meta = {'inputs': inputs, 'bound_against': sorted(inputs)}
    assert L.staffer_inputs(str(section), meta, True) is None
    section.write_text('{}', encoding='utf-8')
    assert L.staffer_inputs(str(section), meta, True)[0] is True
    assert L.staffer_inputs(str(section), meta, False)[0] is False                      # re-hash failed
    assert L.staffer_inputs(str(section), meta, None)[0] is False                       # re-hash never ran
    assert L.staffer_inputs(str(section), dict(meta, bound_against=[]), True)[0] is False
    legacy = L.staffer_inputs(str(section), {'inputs': inputs}, True)
    assert legacy[0] is True and 'absent' in legacy[1]
    no_edges = {'inputs': {'staffer_trajectories': inputs['staffer_trajectories']}}
    assert L.staffer_inputs(str(section), no_edges, True)[0] is False
    no_sha = {'inputs': dict(inputs, staffer_social_edges={'sha256': None})}
    assert L.staffer_inputs(str(section), no_sha, True)[0] is False


# ---- press body ledger -----------------------------------------------------------------------------------------------------

def _press_run(tmp_path, ledger=b'rds', claimed=None):
    run = tmp_path / 'press_refresh_20261020'
    run.mkdir(parents=True)
    (run / 'press_body_attempt_ledger.rds').write_bytes(ledger)
    receipt = json.dumps({'body_attempt_ledger_sha256': claimed or _sha(b'rds')}).encode()
    (run / 'press_network_retry_receipt.json').write_bytes(receipt)
    return {'accepted_runs': [{'source_run': str(run),
                               'source_sha256': {'press_network_retry_receipt.json': _sha(receipt)}}]}


def test_press_body_ledger(tmp_path):
    assert L.press_body_ledger({}) is None
    assert L.press_body_ledger(_press_run(tmp_path / 'ok'))[0] is True
    assert L.press_body_ledger(_press_run(tmp_path / 'drift', ledger=b'changed'))[0] is False
    feed = _press_run(tmp_path / 'rebound')
    feed['accepted_runs'][-1]['source_sha256']['press_network_retry_receipt.json'] = '0' * 64
    assert L.press_body_ledger(feed)[0] is False                                         # receipt is not the feed's
    old = tmp_path / 'old'
    _dump(old / 'press_network_retry_receipt.json', {'status': 'PASS'})
    assert L.press_body_ledger({'accepted_runs': [{'source_run': str(old)}]}) is None    # pre-ledger receipt


def test_press_feed_naming_a_vanished_run_fails(tmp_path):
    feed = _press_run(tmp_path / 'gone')
    shutil.rmtree(tmp_path / 'gone')
    ok, detail = L.press_body_ledger(feed)
    assert ok is False and 'missing' in detail


# ---- status files ----------------------------------------------------------------------------------------------------------

def test_status_files(tmp_path):
    weekly, congress = tmp_path / 'weekly.json', tmp_path / 'congress.json'
    assert L.status_files(str(weekly), str(congress)) is None
    _dump(weekly, {'last_outcome': 'HARD_FAILURE'})
    _dump(congress, {'status': 'FAILED', 'run_dir': str(tmp_path)})
    assert L.status_files(str(weekly), str(congress))[0] is True
    _dump(weekly, {'last_outcome': 'SOMETHING_NEW'})
    assert L.status_files(str(weekly), str(congress))[0] is False
    _dump(weekly, {'last_outcome': 'COMPLETE'})
    _dump(congress, {'status': 'PASS', 'run_dir': str(tmp_path / 'vanished')})
    assert L.status_files(str(weekly), str(congress))[0] is False
