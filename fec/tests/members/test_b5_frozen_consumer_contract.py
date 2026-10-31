"""Negative controls for fixed-weight Big Five consumers, independent of live data."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from members.validate_guarded_profile_artifacts import (  # noqa: E402
    ACCEPTED_BIG5_WEIGHTS,
    validate_frozen_gold_contract,
)


class FrozenConsumerContractTests(unittest.TestCase):
    def setUp(self):
        self.spec_hash = "a" * 64
        self.doc = {
            "design": {
                "production_weights": "frozen_accepted_weights",
                "validation": "fixed_accepted_weight_correction_audit",
                "predictions_are_out_of_fold": False,
                "historical_gold_used_to_fit_weights": True,
                "frozen_spec_sha256": self.spec_hash,
            },
            "coverage": {"roster_n": 1},
            "traits": {
                trait: {
                    "selected_weights": copy.deepcopy(weights),
                    "members": {"Current Member": {trait: 0.0, "percentile": 0.0}},
                    "coverage_n": 1,
                    "validation": {
                        "predictions_are_out_of_fold": False,
                        "diagnostic_only": True,
                        "evaluation_kind": "not_reaudited",
                        "panels": {},
                    },
                    "historical_validation": {"predictions_are_out_of_fold": True},
                }
                for trait, weights in ACCEPTED_BIG5_WEIGHTS.items()
            },
        }

    def errors(self):
        return validate_frozen_gold_contract(self.doc, {"Current Member"}, self.spec_hash)

    def test_render_without_new_audit_is_valid_and_not_confirmation(self):
        self.assertEqual([], self.errors())

    def test_auto_refitted_weights_are_rejected(self):
        self.doc["traits"]["O"]["selected_weights"] = {
            "blue_text_o": .4, "pink_observer_o": .4, "legislative_breadth": .2}
        self.assertIn("accepted Big Five weights changed: O", self.errors())

    def test_fixed_score_correlation_cannot_claim_out_of_fold(self):
        self.doc["traits"]["C"]["validation"]["predictions_are_out_of_fold"] = True
        self.assertIn("fixed-weight diagnostic mislabeled as confirmation: C", self.errors())

    def test_departed_member_rejected_even_with_consistent_count(self):
        self.doc["traits"]["A"]["members"]["Departed Member"] = {"A": 1.0}
        self.doc["traits"]["A"]["coverage_n"] = 2
        self.assertIn("external-gold contains noncurrent members: A", self.errors())

    def test_wrong_spec_hash_is_rejected(self):
        self.doc["design"]["frozen_spec_sha256"] = "b" * 64
        self.assertIn("multitrait frozen specification hash mismatch", self.errors())

    def test_coverage_and_denominator_must_reconcile(self):
        self.doc["coverage"]["roster_n"] = 2
        self.doc["traits"]["N"]["coverage_n"] = 2
        self.assertIn("external-gold roster denominator mismatch", self.errors())
        self.assertIn("external-gold coverage count mismatch: N", self.errors())

    def test_historical_receipt_cannot_be_replaced_by_current_diagnostic(self):
        self.doc["traits"]["E"]["historical_validation"] = {}
        self.assertIn("historical Big Five validation receipt missing: E", self.errors())

    def test_current_claim_requires_complete_correction_diagnostic(self):
        self.doc["validation_status"] = "CURRENT_FIXED_DIAGNOSTIC"
        self.assertIn("current correction diagnostic incomplete: E", self.errors())

    def current_panels(self):
        self.doc["validation_status"] = "CURRENT_FIXED_DIAGNOSTIC"
        for row in self.doc["traits"].values():
            row["validation"]["evaluation_kind"] = "fixed_accepted_weight_correction_audit"
            row["validation"]["panels"] = {
                panel: {"r": None, "n": 1, "member_names": ["Current Member"],
                        "permutation_p_one_sided": None,
                        "gold_row": {trait: None for trait in ACCEPTED_BIG5_WEIGHTS},
                        "max_abs_heterotrait": None, "diagonal_dominant": False}
                for panel in ("senate_insiders", "academic_experts")
            }

    def test_current_diagnostic_may_honestly_report_insufficient_data(self):
        self.current_panels()
        self.assertEqual([], self.errors())

    def test_current_diagnostic_cannot_include_an_unpublished_member(self):
        self.current_panels()
        self.doc["traits"]["A"]["validation"]["panels"]["academic_experts"]["member_names"] = ["Missing Input"]
        self.assertIn("current correction panel malformed: A academic_experts", self.errors())


if __name__ == "__main__":
    unittest.main()
