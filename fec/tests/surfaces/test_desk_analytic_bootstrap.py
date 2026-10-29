"""Exercise the desk's real bootstrap branch without importing live data.

The analytic bundle supplies names and bills to the factor producer. Reading
the preceding cycle's board first makes a roster refresh impossible. Public
and ordinary data builds must still refuse incomplete board evidence.
"""
from __future__ import annotations

import ast
import copy
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


SOURCE = Path(__file__).resolve().parents[2] / 'surfaces' / 'make_member_desk.py'
sys.path.insert(0, str(SOURCE.parents[1]))
from engine import primacy_factors

TREE = ast.parse(SOURCE.read_text(encoding='utf-8'), filename=str(SOURCE))
BUILD = next(node for node in TREE.body
             if isinstance(node, ast.FunctionDef) and node.name == 'build_bundle')
CODE = compile(ast.Module(body=[BUILD], type_ignores=[]), str(SOURCE), 'exec')
RECORD = next(node for node in ast.walk(BUILD)
              if isinstance(node, ast.Dict)
              and any(isinstance(key, ast.Constant) and key.value == 'tierrank'
                      for key in node.keys))
BOARD_FIELDS = {key.value: value for key, value in zip(RECORD.keys, RECORD.values)
                if isinstance(key, ast.Constant)
                and key.value in ('tier', 'tierrank', 'tier_detail')}


class ReachedAnalyticPreflight(Exception):
    pass


class AnalyticBootstrapTest(unittest.TestCase):
    def namespace(self, flags, *, valid_board=False):
        tier_reader = Mock(return_value=({'Continuing': 1}, {'Continuing': 1}, {}))
        if not valid_board:
            tier_reader.side_effect = ValueError("no primacy factor for 'Arrival'")
        preflight = Mock(side_effect=ReachedAnalyticPreflight)
        namespace = {
            'sys': SimpleNamespace(argv=['desk', *flags]),
            'B': 'synthetic-root',
            'MD': {'members': [{'name': 'Continuing'}, {'name': 'Arrival'}]},
            'load_honors': Mock(return_value={'generation_id': 'fixture'}),
            '_district_briefs_for': Mock(return_value=({}, {})),
            'legislative_press_tiers': tier_reader,
            'DI': SimpleNamespace(preflight=preflight),
            'CS': {}, 'SNA': {}, 'ARCH': {},
        }
        exec(CODE, namespace)
        return namespace

    def test_internal_bundle_reaches_preflight_without_previous_board_or_honors(self):
        namespace = self.namespace(['--data', '--analytic-inputs-only'])
        with self.assertRaises(ReachedAnalyticPreflight):
            namespace['build_bundle']()
        namespace['legislative_press_tiers'].assert_not_called()
        namespace['load_honors'].assert_not_called()
        namespace['DI'].preflight.assert_called_once_with(
            ['Continuing', 'Arrival'], {}, {}, {}, analytic_inputs_only=True)

    def test_ordinary_data_and_public_builds_keep_missing_factor_failure(self):
        for flags in ([], ['--data']):
            with self.subTest(flags=flags):
                namespace = self.namespace(flags)
                with self.assertRaisesRegex(ValueError, 'no primacy factor'):
                    namespace['build_bundle']()
                namespace['legislative_press_tiers'].assert_called_once_with(
                    ['Continuing', 'Arrival'], with_detail=True)
                namespace['DI'].preflight.assert_not_called()

    def test_internal_flag_without_data_refuses_before_reading_any_board(self):
        namespace = self.namespace(['--analytic-inputs-only'])
        with self.assertRaisesRegex(RuntimeError, 'requires --data'):
            namespace['build_bundle']()
        namespace['legislative_press_tiers'].assert_not_called()
        namespace['load_honors'].assert_not_called()

    def test_valid_public_board_still_reaches_normal_preflight(self):
        namespace = self.namespace([], valid_board=True)
        with self.assertRaises(ReachedAnalyticPreflight):
            namespace['build_bundle']()
        namespace['legislative_press_tiers'].assert_called_once()
        namespace['load_honors'].assert_called_once_with('synthetic-root')
        self.assertFalse(namespace['DI'].preflight.call_args.kwargs['analytic_inputs_only'])

    def test_internal_records_mark_board_fields_unavailable_instead_of_scoring_zero(self):
        for field, expression in BOARD_FIELDS.items():
            with self.subTest(field=field):
                namespace = {'analytic_inputs_only': True, 'name': 'Arrival',
                             '_tier': {}, '_trank': {}, '_tier_detail': {}}
                actual = eval(compile(ast.Expression(expression), str(SOURCE), 'eval'), namespace)
                self.assertIsNone(actual)

    def test_public_records_preserve_board_values(self):
        namespace = {'analytic_inputs_only': False, 'name': 'Continuing',
                     '_tier': {'Continuing': 2}, '_trank': {'Continuing': 20},
                     '_tier_detail': {'Continuing': {'reason': 'observed'}}}
        actual = {field: eval(compile(ast.Expression(expression), str(SOURCE), 'eval'), namespace)
                  for field, expression in BOARD_FIELDS.items()}
        self.assertEqual(actual, {'tier': 2, 'tierrank': 20,
                                  'tier_detail': {'reason': 'observed'}})

    def test_factor_producer_uses_actual_bills_without_an_earlier_board(self):
        bundle = {'members': [
            {'name': 'Continuing', 'bills': [
                {'bill': 'H.R.1', 'congress': '119', 'role': 'sponsor'}]},
            {'name': 'Arrival', 'bills': []},
        ]}
        tags = {'H.R.1|119': {'class': 'cu_primary'}}
        expected = primacy_factors.compute(bundle, tags)
        internal = copy.deepcopy(bundle)
        for member in internal['members']:
            member.update(tier=None, tierrank=None, tier_detail=None)
        self.assertEqual(primacy_factors.compute(internal, tags), expected)
        # The producer supplies existing shrinkage and evidence rules, without
        # borrowing a predecessor's score or inventing an arrival's actions.
        self.assertEqual(expected[0]['Arrival']['agenda_credit'], 0)
        self.assertEqual(expected[0]['Arrival']['lambda'], 0)
        self.assertEqual(expected[0]['Arrival']['mix'], {})


if __name__ == '__main__':
    unittest.main()
