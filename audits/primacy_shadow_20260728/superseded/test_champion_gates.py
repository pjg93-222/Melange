# -*- coding: utf-8 -*-
"""Kernel tests for the Champion gates (fec/tests/). Add to run_tests.py's suite.

Contract under test: gates only ever REMOVE Tier-1 eligibility; they never promote,
never reorder the score, and never touch rank. Fail-open on a missing artifact,
fail-loud on a malformed one.
"""
import unittest
from tier_util_gates_patch import (champion_gate_status, load_champion_gates,
                             load_open_breaches, CU_PRIMACY_FLOOR)

def G(credit=1.0, advanced=1, authored=1, role=''):
    return {'cu_primary_credit': credit, 'cu_advanced': advanced,
            'cu_authored': authored, 'committee_role': role}

class ChampionGates(unittest.TestCase):
    def test_clean_member_passes(self):
        ok, d = champion_gate_status('X', {'X': G()}, {})
        self.assertTrue(ok); self.assertEqual(d['reasons'], [])

    def test_primacy_floor_blocks_no_cu_record(self):
        # French Hill case: 0.00 CU-primary credit
        ok, d = champion_gate_status('Hill', {'Hill': G(credit=0.0, advanced=0, authored=0)}, {})
        self.assertFalse(ok); self.assertFalse(d['gate1_primacy'])

    def test_primacy_floor_is_inclusive_at_boundary(self):
        ok, _ = champion_gate_status('X', {'X': G(credit=CU_PRIMACY_FLOOR)}, {})
        self.assertTrue(ok)

    def test_chair_needs_advancement_not_just_authorship(self):
        # Tim Scott case: chair of jurisdiction, authored but nothing advanced
        ok, d = champion_gate_status('Scott', {'Scott': G(advanced=0, authored=1, role='chair')}, {})
        self.assertFalse(ok); self.assertFalse(d['gate2_delivery'])

    def test_non_chair_authorship_suffices(self):
        # Waters case: minority author, nothing advanced -> still passes delivery
        ok, d = champion_gate_status('Waters', {'Waters': G(advanced=0, authored=1)}, {})
        self.assertTrue(ok); self.assertTrue(d['gate2_delivery'])

    def test_ranking_member_is_not_held_to_chair_test(self):
        # a minority ranking member does not control the calendar
        ok, _ = champion_gate_status('R', {'R': G(advanced=0, authored=1, role='ranking')}, {})
        self.assertTrue(ok)

    def test_open_severity3_blocks_otherwise_clean_member(self):
        # Andy Barr case: passes primacy and delivery; the ledger is the only disqualifier
        gates = {'Barr': G(credit=1.13, advanced=1, authored=1, role='chair')}
        ok, _ = champion_gate_status('Barr', gates, {})
        self.assertTrue(ok, 'Barr must pass gates 1 and 2 — the ledger is load-bearing')
        ok, d = champion_gate_status('Barr', gates, {'Barr': ['MS-2026-002']})
        self.assertFalse(ok); self.assertFalse(d['gate3_conduct'])
        self.assertIn('MS-2026-002', d['open_events'])

    def test_unknown_member_is_gated_not_crashed(self):
        ok, d = champion_gate_status('Ghost', {}, {})
        self.assertFalse(ok); self.assertEqual(d['cu_primary_credit'], 0.0)

    def test_missing_artifact_fails_open(self):
        self.assertEqual(load_champion_gates('/nonexistent-root'), {})
        self.assertEqual(load_open_breaches('/nonexistent-root'), {})

    def test_malformed_artifact_raises(self):
        import tempfile, os
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'champion_gates.json'), 'w') as fh:
                fh.write('{not json')
            with self.assertRaises(ValueError):
                load_champion_gates(td)

if __name__ == '__main__':
    unittest.main(verbosity=2)
