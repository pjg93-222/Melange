# -*- coding: utf-8 -*-
"""D-330 (Paul, 2026-10-26): which attempt-9 audit_full residuals the unattended gate tolerates.

Tolerated by exact name: collection_intake REJECTED (until the media gate passes). NOT tolerated:
the personal-texture precision check (6244 < 6545, a quality check with its own lane) and the 6 A2b
repo.* staleness checks (refreshed by a run, not waived). The 9 gated and the 6 expected-at-535 are
covered elsewhere (KNOWN_GATED_FAILURES / KNOWN_GATED_PATTERNS; audit_full's roster tolerance)."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location('audit_failure_gate_d330_under_test', ROOT / 'fec' / 'audit_failure_gate.py')
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)

INTAKE = 'accepted audio manifest is fully partitioned into a candidate-only review intake'
PRECISION = 'personal-texture artifact precision/schema/provenance (no volume reward)'
A2B_REPO = ['A2b repo.%s sentinels unchanged' % s
            for s in ('source_data', 'data_lobbying', 'data_network', 'data_engine', 'data_district', 'worktrees')]


def _run(names):
    out = 'FULL-BODY AUDIT — 540 passed, %d FAILED\nFAILURES: %r\n' % (len(names), names)
    return gate.tolerate_known_gated(out, '')[0]


def test_collection_intake_rejected_is_tolerated_by_exact_name():
    assert INTAKE in gate.KNOWN_GATED_FAILURES
    assert _run([INTAKE]) is True


def test_personal_texture_precision_still_fails_the_gate():
    assert PRECISION not in gate.KNOWN_GATED_FAILURES
    assert _run([PRECISION]) is False
    assert _run([INTAKE, PRECISION]) is False


def test_a2b_repo_staleness_is_refreshed_not_tolerated():
    for n in A2B_REPO:
        assert _run([n]) is False, n


LONGFORM_AGE = 'chain_tolerated_failures'


def test_longform_age_is_tolerated_until_the_rebind():
    # D-330 ruling 8: re-bind longform after attempt 10; tolerate the 47-day last-good age until then.
    assert LONGFORM_AGE in gate.KNOWN_GATED_FAILURES
    assert _run([LONGFORM_AGE, INTAKE]) is True
