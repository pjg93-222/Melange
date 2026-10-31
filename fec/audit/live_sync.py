"""audit_full [SYNC] sub-checks: each live ledger/snapshot still equals the bytes its receipt names.

Every function returns (ok, detail), or None when this tree has nothing to check (audit_full prints SKIP).
Read-only; the only hashing is of the files a receipt names.
"""
import hashlib
import json
import os
import re

# Outcome vocabularies of the two writers: weekly_refresh.py _write_status(last_outcome=...) and
# legislation/refresh_congress_pipeline.py state['status'] (INTERRUPTED is health()'s reading of a dead RUNNING).
WEEKLY_OUTCOMES = ('RUNNING', 'RUNNING_AFTER_KNOWN_FAILURE', 'ABORTED_NO_TERMINAL_OUTCOME', 'KILLED_SIGBREAK',
                   'FATAL_PRESTEP', 'HARD_FAILURE', 'COMPLETE', 'COMPLETE_WITH_KNOWN_GATED_FAILURES', 'DEGRADED',
                   'DEGRADED_WITH_KNOWN_GATED_FAILURES')
CONGRESS_STATUSES = ('RUNNING', 'PASS', 'FAILED', 'INTERRUPTED')


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path):
    with open(path, encoding='utf-8') as handle:
        return json.load(handle)


def chain_journal(root):
    import chain_transaction
    return chain_transaction.journal_closed(root, chain_transaction._recovery_bases(root))


def sentinel_ledger(receipt_path, ledger_path, cached_sha=None):
    """The receipt's live_ledger_workbook sha256/size equal the installed xlsx. cached_sha: ledger_path's hash, if known."""
    if not os.path.exists(receipt_path):
        return None
    block = _json(receipt_path).get('live_ledger_workbook') or {}
    if not block.get('sha256'):
        return None
    path = block.get('path') or ''
    if not os.path.isfile(path):
        return False, 'receipt workbook missing: %s' % path
    same = os.path.normcase(os.path.abspath(path)) == os.path.normcase(os.path.abspath(ledger_path))
    have, size = (cached_sha if same and cached_sha else file_sha256(path)), os.path.getsize(path)
    return (have.casefold() == block['sha256'].casefold() and size == block.get('size'),
            'sha %s vs receipt %s; size %d vs %s' % (have[:12], block['sha256'][:12], size, block.get('size')))


def staffer_inputs(section_path, meta, rehash_ok):
    """Every meta.inputs role carries a sha256 (the edge file included), the audit's re-hash passed, and meta.bound_against
    names exactly those roles. A section built before the producer wrote bound_against is judged on meta.inputs."""
    if not os.path.exists(section_path):
        return None
    inputs, bound = meta.get('inputs') or {}, meta.get('bound_against')
    nosha = sorted(r for r, v in inputs.items() if not re.fullmatch(r'[0-9a-fA-F]{64}', str((v or {}).get('sha256'))))
    legacy = bound is None
    bound = sorted(inputs) if legacy else bound
    ok = (bool(inputs) and not nosha and 'staffer_social_edges' in inputs and rehash_ok is True
          and sorted(bound) == sorted(inputs))
    return ok, '%d roles, no sha256: %s; re-hash ok=%s; bound_against %s' % (
        len(inputs), nosha, rehash_ok, 'absent (pre-2026-10-28 build), judged on meta.inputs' if legacy
        else 'matches inputs' if sorted(bound) == sorted(inputs) else '%s != inputs' % sorted(bound))


def press_body_ledger(feed):
    """The run the press feed promoted last: its retry receipt is the one the feed bound, and that receipt's
    body_attempt_ledger_sha256 equals press_body_attempt_ledger.rds. A feed naming a vanished run FAILS."""
    runs = feed.get('accepted_runs') or []
    if not runs:
        return None
    run, run_dir = runs[-1], runs[-1].get('source_run') or ''
    receipt_path = os.path.join(run_dir, 'press_network_retry_receipt.json')
    if not os.path.isfile(receipt_path):
        return False, 'feed names run %r but its press_network_retry_receipt.json is missing' % run_dir
    receipt = _json(receipt_path)
    if 'body_attempt_ledger_sha256' not in receipt:
        return None
    bound = file_sha256(receipt_path) == (run.get('source_sha256') or {}).get('press_network_retry_receipt.json')
    ledger = os.path.join(run_dir, 'press_body_attempt_ledger.rds')
    have = file_sha256(ledger) if os.path.isfile(ledger) else 'missing'
    return (bound and have == receipt['body_attempt_ledger_sha256'],
            '%s: receipt bound to feed=%s; ledger %s vs receipt %s' % (
                os.path.basename(run_dir), bound, have[:12], str(receipt['body_attempt_ledger_sha256'])[:12]))


def status_files(weekly_path, congress_path):
    """Both run-status files parse with a known outcome; congress names a run_dir that exists.
    weekly_refresh_status.json records no run dir or log path, so it is checked for parse + outcome only."""
    if not (os.path.exists(weekly_path) or os.path.exists(congress_path)):
        return None
    why = []
    if os.path.exists(weekly_path):
        outcome = _json(weekly_path).get('last_outcome')
        if outcome not in WEEKLY_OUTCOMES:
            why.append('weekly last_outcome %r unknown' % outcome)
    if os.path.exists(congress_path):
        state = _json(congress_path)
        if state.get('status') not in CONGRESS_STATUSES:
            why.append('congress status %r unknown' % state.get('status'))
        if not os.path.isdir(str(state.get('run_dir') or '')):
            why.append('congress run_dir missing: %r' % state.get('run_dir'))
    return not why, '; '.join(why) or 'both parse; outcomes known'
