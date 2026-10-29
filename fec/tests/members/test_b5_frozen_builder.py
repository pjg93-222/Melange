"""Regression tests for no-refit rendering and identical audit eligibility."""
from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from members import b5_gold_multitrait_validate as model


class FrozenBuilderTests(unittest.TestCase):
    def setUp(self):
        self.spec, self.spec_hash = model.frozen_spec()
        self.roster = [{"member": "Member " + str(i), "bioguide": "X%06d" % i,
                        "chamber": "Senate"} for i in range(1, 7)]
        self.channels = {
            trait: {channel: {row["member"]: float(i) for i, row in enumerate(self.roster)}
                    for channel in accepted["selected_weights"]}
            for trait, accepted in self.spec["traits"].items()
        }

    def build(self, previous=None, hashes=None):
        def load(name):
            if name == "data/engine/roster.json":
                return {"members": self.roster}
            raise AssertionError("routine rendering must not read gold values: " + name)
        with patch.object(model, "load", side_effect=load), \
             patch.object(model, "raw_channels", return_value=self.channels), \
             patch.object(model, "input_hashes", return_value=hashes or {"input": "unchanged"}), \
             patch.object(model, "choose_weights", side_effect=AssertionError("no fitting")), \
             patch.object(model, "variants_for", side_effect=AssertionError("no model selection")), \
             patch.object(model, "oof_variant", side_effect=AssertionError("no refitting")), \
             patch.object(model, "evaluate_fixed", side_effect=AssertionError("explicit audit required")):
            return model.build(previous=previous)

    def test_routine_build_never_fits_or_evaluates_gold(self):
        doc = self.build()
        self.assertEqual("NOT_REAUDITED_INPUTS_CHANGED", doc["validation_status"])
        for trait, accepted in self.spec["traits"].items():
            self.assertEqual(accepted["selected_weights"], doc["traits"][trait]["selected_weights"])
            self.assertEqual(6, doc["traits"][trait]["coverage_n"])
            self.assertEqual({}, doc["traits"][trait]["validation"]["panels"])

    def test_missing_primary_never_enters_scores_or_audit(self):
        channels = {"primary": {str(i): float(i) for i in range(7)},
                    "observer": {str(i): float(i) for i in range(6)}}
        scores = model.fixed_scores(channels, {"primary": .5, "observer": .5},
                                    ["primary", "observer"], set(map(str, range(7))))
        panels = {p: {str(i): {t: i for t in ("O", "C", "E", "A", "ES")}
                      for i in range(7)} for p in model.PANEL_NAMES}
        with patch.object(model, "one_sided_permutation_p", return_value=(1., .01)):
            result = model.evaluate_fixed(scores, panels, "C")
        for row in result["panels"].values():
            self.assertEqual(6, row["n"])
            self.assertEqual(["6"], row["excluded_missing_required_channels"])
            self.assertNotIn("6", row["member_names"])

    def test_optional_missing_uses_fixed_centered_contribution(self):
        scores = model.fixed_scores({"a": {"x": 2.}, "b": {"x": 1.}, "optional": {}},
                                    {"a": .4, "b": .4, "optional": .2}, ["a", "b"], {"x"})
        self.assertAlmostEqual(1.2, scores["x"])

    def test_departed_does_not_enter_final_scores_or_percentiles(self):
        for channels in self.channels.values():
            for values in channels.values():
                values["Departed"] = 99999.
        doc = self.build()
        for row in doc["traits"].values():
            self.assertEqual(6, row["coverage_n"])
            self.assertNotIn("Departed", row["members"])
            self.assertEqual(1., row["members"]["Member 6"]["percentile"])

    def test_departed_cannot_affect_channel_standardization(self):
        blue = {"traits": {"a": {t: 1. for t in model.TRAITS},
                           "b": {t: 3. for t in model.TRAITS},
                           "Departed": {t: 100000. for t in model.TRAITS}}}
        with patch.object(model, "load", side_effect=lambda name: blue if "blue_validated" in name else {}):
            values = model.raw_channels({"a", "b"})["O"]["blue_text_o"]
        self.assertEqual({"a", "b"}, set(values))
        self.assertAlmostEqual(0., sum(values.values()))
        self.assertAlmostEqual(2 ** -.5, values["b"])

    def test_nonfinite_primary_is_ineligible(self):
        self.assertEqual([], model.eligible_members({"a": {"x": float("nan")}}, ["a"], {"x"}))
        self.assertEqual({}, model.zmap({}))
        self.assertEqual({"x": 0.}, model.zmap({"x": 4.}))

    def test_exact_input_receipt_can_carry_diagnostic_without_new_look(self):
        previous = self.build()
        previous["validation_status"] = "CURRENT_FIXED_DIAGNOSTIC"
        for row in previous["traits"].values():
            row["validation"] = {"evaluation_kind": "fixed_accepted_weight_correction_audit",
                                 "predictions_are_out_of_fold": False, "diagnostic_only": True,
                                 "panels": {p: {"n": 6, "r": .2, "permutation_p_one_sided": .2,
                                                "member_names": [r["member"] for r in self.roster],
                                                "max_abs_heterotrait": .3, "diagonal_dominant": False,
                                                "discrimination_n": 6, "gold_row": {}}
                                            for p in model.PANEL_NAMES}}
        doc = self.build(previous=previous)
        self.assertEqual("CURRENT_FIXED_DIAGNOSTIC", doc["validation_status"])
        changed = self.build(previous=previous, hashes={"input": "changed"})
        self.assertEqual("NOT_REAUDITED_INPUTS_CHANGED", changed["validation_status"])
        self.assertEqual({}, changed["traits"]["C"]["validation"]["panels"])

    def test_current_flag_cannot_replace_an_actual_audit(self):
        previous = self.build()
        previous["validation_status"] = "CURRENT_FIXED_DIAGNOSTIC"
        self.assertEqual("NOT_REAUDITED_INPUTS_CHANGED", self.build(previous=previous)["validation_status"])

    def test_registry_or_spec_change_invalidates_cached_diagnostic(self):
        previous = self.build()
        previous["validation_status"] = "CURRENT_FIXED_DIAGNOSTIC"
        for field in ("frozen_spec_sha256", "identity_registry_sha256", "score_code_sha256", "code_dependencies_sha256"):
            changed = copy.deepcopy(previous)
            changed["design"][field] = "bad"
            self.assertEqual("NOT_REAUDITED_INPUTS_CHANGED", self.build(previous=changed)["validation_status"])

    def test_discrimination_uses_same_complete_cases_for_all_traits(self):
        scores = {str(i): float(i) for i in range(7)}
        panel = {str(i): {t: i for t in ("O", "C", "E", "A", "ES")} for i in range(7)}
        panel["6"]["A"] = None
        with patch.object(model, "one_sided_permutation_p", return_value=(1., .01)):
            result = model.evaluate_fixed(scores, {p: panel for p in model.PANEL_NAMES}, "C")
        for row in result["panels"].values():
            self.assertEqual(7, row["n"])
            self.assertEqual(6, row["discrimination_n"])
            self.assertEqual({6}, set(row["gold_row_n"].values()))

    def test_concurrent_input_change_aborts_before_publication(self):
        with patch.object(model, "load", return_value={"members": self.roster}), \
             patch.object(model, "raw_channels", return_value=self.channels), \
             patch.object(model, "input_hashes", side_effect=[{"input": "before"}, {"input": "after"}]):
            with self.assertRaisesRegex(RuntimeError, "changed during build"):
                model.build()


if __name__ == "__main__":
    unittest.main()
