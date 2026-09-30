"""The Giving Forecast contract (brain DE-021): schemas, shared examples, shared negative controls, and the validator itself.

The same example files and negative controls are asserted against the R pipeline's bundle writer (mentat/forecast/refit) and
against the anchor builder (mentat/forecast/anchors); this suite holds the Python side and proves the validator can fail.
"""
import json
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'forecast' / 'contracts'))
import contract  # noqa: E402


def _schema_nodes(node, path='$'):
    """Every schema node of a schema document, skipping the maps whose keys are names, not keywords."""
    yield path, node
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key in ('properties', '$defs'):
            for name, child in value.items():
                yield from _schema_nodes(child, path + '.' + key + '.' + name)
        elif key == 'additionalProperties' and isinstance(value, dict):
            yield from _schema_nodes(value, path + '.additionalProperties')
        elif key == 'items' and isinstance(value, dict):
            yield from _schema_nodes(value, path + '.items')


class ContractTests(unittest.TestCase):
    def test_schemas_only_use_the_documented_keyword_subset(self):
        for kind in contract.SCHEMAS:
            for path, node in _schema_nodes(contract.schema(kind)):
                with self.subTest(kind=kind, path=path):
                    self.assertEqual(set(node) - contract.SUPPORTED_KEYWORDS, set())

    def test_the_bundle_example_validates(self):
        self.assertEqual(contract.validate_kind(contract.example('models'), 'models'), [])
        self.assertEqual(contract.check_model_invariants(contract.example('models')), [])

    @staticmethod
    def _accepted_controls(validator, target='models'):
        """Ids of the negative controls of one target a validator wrongly accepts (empty = every control was rejected)."""
        example = contract.example(target)
        out = []
        for c in contract.negative_controls():
            if c['target'] == target:
                path = ['commercial_banks' if step == '<industry>' else step for step in c['path']]
                if not validator(contract.apply_mutation(example, {**c, 'path': path})):
                    out.append(c['id'])
        return out

    def test_every_bundle_negative_control_fails_validation(self):
        self.assertGreaterEqual(len([c for c in contract.negative_controls() if c['target'] == 'models']), 10)
        self.assertEqual(self._accepted_controls(contract.validate_model), [])

    def test_a_schema_only_validator_misses_the_model_invariant_controls(self):
        missed = self._accepted_controls(lambda doc: contract.validate_kind(doc, 'models'))
        kinds = {c['id']: c['kind'] for c in contract.negative_controls() if c['target'] == 'models'}
        self.assertEqual(sorted(missed), sorted(i for i, k in kinds.items() if k == 'invariant'))
        self.assertGreaterEqual(len(missed), 3)

    def test_the_anchor_selection_rule_is_an_invariant(self):
        import copy
        base = contract.example('models')
        entry = lambda doc: doc['share_models']['control_House']['anchors']['commercial_banks']
        # same_phase chosen although it does not win in every design (the example's chrono gain is negative for banks House)
        doc = copy.deepcopy(base)
        entry(doc)['anchor'] = 'same_phase'
        doc['share_models']['control_House']['prediction']['industries']['commercial_banks'] = dict(entry(doc)['prediction']['same_phase'])
        self.assertTrue(any('same_phase chosen without beating' in p for p in contract.check_model_invariants(doc)))
        # previous_cycle kept although same_phase wins in both designs
        doc = copy.deepcopy(base)
        a = entry(doc)
        a['backtest']['same_phase'].update(loeo_mae=a['backtest']['previous_cycle']['loeo_mae'] * 0.5, chrono_mae=a['backtest']['previous_cycle']['chrono_mae'] * 0.5)
        a['backtest']['same_phase_gain'] = dict(loeo=0.5, chrono=0.5)
        self.assertTrue(any('previous_cycle kept although' in p for p in contract.check_model_invariants(doc)))
        # ...and the consistent flip is accepted
        a['anchor'] = 'same_phase'
        doc['share_models']['control_House']['prediction']['industries']['commercial_banks'] = dict(a['prediction']['same_phase'])
        self.assertEqual(contract.check_model_invariants(doc), [])
        self.assertEqual(contract.validate_kind(doc, 'models'), [])

    def test_a_validator_that_accepts_everything_is_caught_by_the_negative_controls(self):
        # Negative control of the negative controls: a permissive validator must be reported, control by control.
        accepted = self._accepted_controls(lambda doc: [])
        self.assertEqual(len(accepted), len([c for c in contract.negative_controls() if c['target'] == 'models']))

    def test_the_anchor_example_validates_and_is_consistent(self):
        example = contract.example('anchors')
        self.assertEqual(contract.validate_kind(example, 'anchors'), [])
        self.assertEqual(contract.check_anchor_invariants(example), [])
        self.assertEqual({'commercial_banks', 'credit_unions'} <= set(example['industries']), True)
        self.assertNotIn('auto_light_duty_manufacturing', example['industries'])       # auto has no Mentat data
        self.assertEqual(example['industries']['community_banks']['forecast_industry'], None)   # separate, never merged into banks

    def _anchor_validator(self, doc):
        return contract.validate_kind(doc, 'anchors') or contract.check_anchor_invariants(doc)

    def test_every_anchor_negative_control_fails_validation_or_the_invariants(self):
        self.assertEqual(self._accepted_controls(self._anchor_validator, 'anchors'), [])
        self.assertEqual(len([c for c in contract.negative_controls() if c['target'] == 'anchors']), 18)

    def test_a_schema_only_validator_misses_the_invariant_controls(self):
        # The invariant controls are schema-valid by design: only the cross-field checks catch them.
        missed = self._accepted_controls(lambda doc: contract.validate_kind(doc, 'anchors'), 'anchors')
        kinds = {c['id']: c['kind'] for c in contract.negative_controls() if c['target'] == 'anchors'}
        self.assertEqual(sorted(missed), sorted(i for i, k in kinds.items() if k == 'invariant'))

    def test_the_example_itself_is_not_changed_by_a_mutation(self):
        example = contract.example('models')
        before = json.dumps(example, sort_keys=True)
        contract.apply_mutation(example, {'op': 'delete', 'path': ['pac_model']})
        self.assertEqual(json.dumps(example, sort_keys=True), before)

    def test_a_v1_bundle_is_not_a_v2_bundle(self):
        v1 = contract.read_json(ROOT / 'app' / 'data' / 'giving-models-v1.json')
        problems = contract.validate_kind(v1, 'models')
        self.assertTrue(any('schema_version' in p for p in problems))
        self.assertTrue(any('anchor_contract' in p for p in problems))

    def test_validator_reports_each_kind_of_violation(self):
        doc = {'type': 'object', 'properties': {'a': {'type': 'integer', 'minimum': 1}, 'b': {'type': 'string', 'pattern': '^x'}},
               'required': ['a'], 'additionalProperties': False}
        self.assertEqual(contract.validate({'a': 1, 'b': 'xy'}, doc), [])
        self.assertTrue(contract.validate({'b': 'xy'}, doc))
        self.assertTrue(contract.validate({'a': 0}, doc))
        self.assertTrue(contract.validate({'a': 1, 'b': 'y'}, doc))
        self.assertTrue(contract.validate({'a': 1, 'c': 1}, doc))
        self.assertTrue(contract.validate({'a': True}, doc))            # a boolean is not an integer
        self.assertTrue(contract.validate({'a': float('inf')}, doc))     # non-finite numbers are rejected
        self.assertTrue(contract.validate({'a': 1.5}, doc))
        self.assertEqual(contract.validate({'a': 2.0}, doc), [])        # an integral float is an integer (R writes 2024 as 2024.0)

    def test_validator_refuses_keywords_outside_the_subset(self):
        with self.assertRaises(ValueError):
            contract.validate({}, {'type': 'object', 'oneOf': []})

    def test_the_bundle_example_has_no_non_finite_numbers(self):
        def walk(node):
            if isinstance(node, float):
                self.assertTrue(math.isfinite(node))
            elif isinstance(node, dict):
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)
        walk(contract.example('models'))


if __name__ == '__main__':
    unittest.main()
