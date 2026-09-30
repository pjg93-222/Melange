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

    @staticmethod
    def _accepted_controls(validator):
        """Ids of the bundle negative controls a validator wrongly accepts (empty = every control was rejected)."""
        example = contract.example('models')
        return [c['id'] for c in contract.negative_controls() if c['target'] == 'models'
                and not validator(contract.apply_mutation(example, c))]

    def test_every_bundle_negative_control_fails_validation(self):
        self.assertGreaterEqual(len([c for c in contract.negative_controls() if c['target'] == 'models']), 10)
        self.assertEqual(self._accepted_controls(lambda doc: contract.validate_kind(doc, 'models')), [])

    def test_a_validator_that_accepts_everything_is_caught_by_the_negative_controls(self):
        # Negative control of the negative controls: a permissive validator must be reported, control by control.
        accepted = self._accepted_controls(lambda doc: [])
        self.assertEqual(len(accepted), len([c for c in contract.negative_controls() if c['target'] == 'models']))

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
