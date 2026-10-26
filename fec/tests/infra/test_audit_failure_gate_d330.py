# -*- coding: utf-8 -*-
"""D-330 (Paul, 2026-10-26): which attempt-9 audit_full residuals the unattended gate tolerates.

Tolerated ONLY on the adjudicated sub-condition (re-derived from the live files, fail closed):
  * the intake check: collection_intake receipt REJECTED, until the media gate passes. Hash binding,
    candidate-only status, partition completeness and no-active-writes must still hold.
  * chain_tolerated_failures (ruling 8): the longform last-good AGE, until the re-bind after attempt
    10. Pinned to the adjudicated artifact's bytes, so it expires when the re-bind writes a new one.
    A missing or malformed receipt, a missing artifact, or another step going stale still fails.
NOT tolerated: the personal-texture precision check (6244 < 6545, a quality check with its own lane)
and the 6 A2b repo.* staleness checks (refreshed by a run, not waived). The 9 gated and the 6
expected-at-535 are covered elsewhere (KNOWN_GATED_FAILURES / KNOWN_GATED_PATTERNS; audit_full's
roster tolerance)."""
import hashlib
import importlib.util
import json
import os
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('audit_failure_gate_d330_under_test', ROOT / 'fec' / 'audit_failure_gate.py')
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

INTAKE = 'accepted audio manifest is fully partitioned into a candidate-only review intake'
LONGFORM_AGE = 'chain_tolerated_failures'
PRECISION = 'personal-texture artifact precision/schema/provenance (no volume reward)'
A2B_REPO = ['A2b repo.%s sentinels unchanged' % s
            for s in ('source_data', 'data_lobbying', 'data_network', 'data_engine', 'data_district', 'worktrees')]
LONGFORM_BYTES = b'{"adjudicated longform last-good": true}\n'
DAY = 86400.0


def _write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding='utf-8')
    return path


def _age(path, days):
    t = time.time() - days * DAY
    os.utime(path, (t, t))


@pytest.fixture
def live(tmp_path, monkeypatch):
    """A Moneyball root shaped like today's live files (2026-10-26): intake REJECTED with every other
    intake conjunct passing (6911/6911); longform last-good 51 d old, the two others 14.7 d."""
    manifest = tmp_path / 'melange-data' / 'clips_manifest.jsonl'
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(b'{"clip": 1}\n')
    msha = hashlib.sha256(manifest.read_bytes()).hexdigest()
    intake = _write(tmp_path / 'data' / 'engine' / 'collection_intake_receipt.json', {
        'schema': 'collection-intake-receipt-v1', 'status': 'REJECTED',
        'inputs': {'clip_manifest_sha256': msha}, 'house': {'all_clip_rows': 6911}})
    cand = _write(tmp_path / 'data' / 'members' / 'b5_audio_reviews_v2.json.candidate', {
        'schema': 'b5-audio-review-v2-candidate',
        'status': 'CANDIDATE_ONLY_CONSUMED_BY_NOTHING_AWAITING_DOUBLE_REVIEW',
        'source_manifest': {'path': str(manifest), 'sha256': msha},
        'partition': {'total': 6911, 'queued': 6000, 'excluded': 911},
        'contract': {'active_artifacts_written': False}})
    longform = tmp_path / 'data' / 'speech' / 'member_longform_turn_features_v1.json'
    longform.parent.mkdir(parents=True)
    longform.write_bytes(LONGFORM_BYTES)
    monkeypatch.setattr(gate, 'LONGFORM_LAST_GOOD_SHA256', hashlib.sha256(LONGFORM_BYTES).hexdigest())
    ledger = _write(tmp_path / 'data' / 'members' / 'member_narrative_evidence_v4.json', {})
    profiles = _write(tmp_path / 'member_narratives_v2.json', {})
    _age(longform, 51.0); _age(ledger, 14.7); _age(profiles, 14.7)
    receipt = _write(tmp_path / 'data' / 'engine' / 'chain_tolerated_failures.json', [
        {'step': 'build_member_longform_turn_features.py', 'last_good_path': str(longform), 'status': 'LAST_GOOD'},
        {'step': 'build_member_narrative_ledger.py', 'last_good_path': str(ledger), 'status': 'LAST_GOOD'},
        {'step': 'regenerate_member_profiles.py', 'last_good_path': str(profiles), 'status': 'LAST_GOOD'}])

    class Live:
        pass
    lv = Live()
    lv.root, lv.manifest, lv.intake, lv.cand = tmp_path, manifest, intake, cand
    lv.longform, lv.ledger, lv.profiles, lv.receipt = longform, ledger, profiles, receipt
    return lv


def _run(names, root=None):
    out = 'FULL-BODY AUDIT — 540 passed, %d FAILED\nFAILURES: %r\n' % (len(names), names)
    return gate.tolerate_known_gated(out, '', log=lambda line: None, root=root)[0]


def _patch(path, **changes):
    obj = json.loads(path.read_text(encoding='utf-8'))
    for k, v in changes.items():
        obj[k] = v
    _write(path, obj)


# --- names are conditional, never blanket ---------------------------------------------------------

def test_d330_names_are_conditional_not_blanket():
    assert INTAKE not in gate.KNOWN_GATED_FAILURES
    assert LONGFORM_AGE not in gate.KNOWN_GATED_FAILURES
    assert set(gate.CONDITIONALLY_GATED_FAILURES) == {INTAKE, LONGFORM_AGE}
    for n in (INTAKE, LONGFORM_AGE):
        assert not any(p.match(n) for p in gate.KNOWN_GATED_PATTERNS)


def test_conditional_names_still_exist_verbatim_in_audit_full():
    source = (ROOT / 'fec' / 'audit' / 'audit_full.py').read_text(encoding='utf-8-sig')
    assert "ck('%s'" % INTAKE in source
    assert "ck('chain_tolerated_failures'" in source
    assert '_CTF_MAX_AGE_DAYS=%d' % gate.CTF_MAX_AGE_DAYS in source


def test_conditions_fail_closed_on_an_empty_root(tmp_path):
    assert _run([INTAKE], root=tmp_path) is False
    assert _run([LONGFORM_AGE], root=tmp_path) is False


# --- today's live shape is tolerated --------------------------------------------------------------

def test_todays_live_shape_is_tolerated(live):
    assert _run([INTAKE], live.root) is True
    assert _run([LONGFORM_AGE], live.root) is True
    assert _run([LONGFORM_AGE, INTAKE], live.root) is True


# --- intake: only REJECTED is adjudicated ---------------------------------------------------------

def test_intake_status_other_than_rejected_is_not_tolerated(live):
    for status in ('PENDING', None, 'ACCEPTED'):
        _patch(live.intake, status=status)
        assert _run([INTAKE], live.root) is False, status


def test_intake_rejected_plus_hash_binding_broken_is_not_tolerated(live):
    live.manifest.write_bytes(b'{"clip": 2}\n')          # candidate sha no longer binds the manifest
    assert _run([INTAKE], live.root) is False


def test_intake_rejected_plus_intake_hash_mismatch_is_not_tolerated(live):
    _patch(live.intake, inputs={'clip_manifest_sha256': '0' * 64})
    assert _run([INTAKE], live.root) is False


def test_intake_rejected_plus_manifest_missing_is_not_tolerated(live):
    live.manifest.unlink()
    assert _run([INTAKE], live.root) is False


def test_intake_rejected_plus_not_candidate_only_is_not_tolerated(live):
    _patch(live.cand, status='PROMOTED')
    assert _run([INTAKE], live.root) is False


def test_intake_rejected_plus_partition_incomplete_is_not_tolerated(live):
    _patch(live.cand, partition={'total': 6911, 'queued': 6000, 'excluded': 900})
    assert _run([INTAKE], live.root) is False
    _patch(live.cand, partition={'total': 6900, 'queued': 6000, 'excluded': 900})   # total != all_clip_rows
    assert _run([INTAKE], live.root) is False


def test_intake_rejected_plus_active_writes_is_not_tolerated(live):
    for flag in (True, None):
        _patch(live.cand, contract={'active_artifacts_written': flag})
        assert _run([INTAKE], live.root) is False, flag


def test_intake_rejected_plus_wrong_schema_is_not_tolerated(live):
    _patch(live.cand, schema='b5-audio-review-v1')
    assert _run([INTAKE], live.root) is False
    _patch(live.cand, schema='b5-audio-review-v2-candidate')
    _patch(live.intake, schema='collection-intake-receipt-v0')
    assert _run([INTAKE], live.root) is False


# --- chain_tolerated_failures: only the adjudicated longform age ----------------------------------

def test_ctf_missing_receipt_is_not_tolerated(live):
    live.receipt.unlink()
    assert _run([LONGFORM_AGE], live.root) is False


def test_ctf_malformed_receipt_is_not_tolerated(live):
    _write(live.receipt, {'not': 'a list'})
    assert _run([LONGFORM_AGE], live.root) is False
    _write(live.receipt, [['not', 'an object']])
    assert _run([LONGFORM_AGE], live.root) is False
    live.receipt.write_text('{broken', encoding='utf-8')
    assert _run([LONGFORM_AGE], live.root) is False


def test_ctf_missing_artifact_is_not_tolerated(live):
    live.ledger.unlink()
    assert _run([LONGFORM_AGE], live.root) is False


def test_ctf_another_step_going_stale_is_not_tolerated(live):
    _age(live.ledger, 21.5)
    assert _run([LONGFORM_AGE], live.root) is False
    _age(live.ledger, 14.7); _age(live.profiles, 30.0)
    assert _run([LONGFORM_AGE], live.root) is False


def test_ctf_longform_fresh_means_nothing_adjudicated_explains_the_failure(live):
    _age(live.longform, 1.0)
    assert _run([LONGFORM_AGE], live.root) is False


# --- expiry: the re-bind ends the tolerance -------------------------------------------------------

def test_tolerance_expires_once_the_longform_artifact_is_rebound(live):
    assert _run([LONGFORM_AGE], live.root) is True
    live.longform.write_bytes(b'{"re-bound after attempt 10": true}\n')   # the re-bind writes new bytes
    _age(live.longform, 22.0)                                            # ... which later go stale too
    assert _run([LONGFORM_AGE], live.root) is False


def test_pinned_hash_is_the_attempt9_longform_artifact():
    # sha256 of data/speech/member_longform_turn_features_v1.json as served at attempt 9
    # (mtime 2026-09-05T20:58:27Z, read 2026-10-26).
    assert gate.LONGFORM_LAST_GOOD_SHA256 == '02da7ca4884066f3a6e046e5e92e8a5b90f5681ab095862e25352fb9101dbc39'
    assert gate.LONGFORM_STEP == 'build_member_longform_turn_features.py'


# --- rulings that stay untolerated ----------------------------------------------------------------

def test_personal_texture_precision_still_fails_the_gate(live):
    assert PRECISION not in gate.KNOWN_GATED_FAILURES
    assert _run([PRECISION], live.root) is False
    assert _run([INTAKE, PRECISION], live.root) is False


def test_a2b_repo_staleness_is_refreshed_not_tolerated(live):
    for n in A2B_REPO:
        assert _run([n], live.root) is False, n
