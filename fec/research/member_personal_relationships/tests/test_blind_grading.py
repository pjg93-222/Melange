# -*- coding: utf-8 -*-
"""Tests for the blind two-pass grading harness. No network: the one API entry
point (GradingClient._once) is monkeypatched in every test that reaches it."""
import json
import tempfile
import unittest
from pathlib import Path

from fec.research.member_personal_relationships import blind_grading as bg


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def mention(mid, date="2021-03-04", source="CREC", text=None):
    return {"mention_id": mid, "date": date, "source": source, "package": "CREC-%s" % date,
            "context_650": text or ("Mr. Speaker, I rise to recognise the gentleman, with whom I "
                                    "have worked on this measure for some years. %s" % mid)}


def packet(pair_id="A000001__B000002", n_a=4, n_b=3, split="development", extras=None):
    row = {
        "pair_id": pair_id,
        "pair": ["A000001", "B000002"],
        "names": ["Alice Adams", "Bob Baker"],
        "split": split,
        "stratum": "LH|different|House+House",
        "design_weight": 1378.8,
        "coverage_tiers": ["high", "low"],
        "directions": {
            "a_to_b": {"mention_total": n_a, "mention_by_source": {"CREC": n_a},
                       "hidden_cue_counts": {"cue_warm": 2, "cue_hostile": 0},
                       "mentions": [mention("m-a%d" % i) for i in range(n_a)]},
            "b_to_a": {"mention_total": n_b, "mention_by_source": {"CREC": n_b},
                       "hidden_cue_counts": {"cue_warm": 1, "cue_hostile": 1},
                       "mentions": [mention("m-b%d" % i) for i in range(n_b)]},
        },
        "hearing_coappearances": {"count": 2, "packages": ["CHRG-1"], "dates": ["2021-05-06"]},
    }
    if extras:
        row.update(extras)
    return row


def wire_direction(affinity="1", friction="unassessable", ritual=False,
                   arange=("1", "2"), frange=("unassessable", "unassessable")):
    return {
        "affinity_degree": affinity,
        "affinity_range": {"lo": arange[0], "hi": arange[1]},
        "affinity_cited_mention_ids": ["m-a0"],
        "friction_degree": friction,
        "friction_range": {"lo": frange[0], "hi": frange[1]},
        "friction_cited_mention_ids": [],
        "closeness_trust_evidence": [],
        "ritual_courtesy_only": ritual,
        "episode_dates_used": ["2021-03-04"],
        "period_covered": {"first": "2021-03-04", "last": "2021-03-04"},
    }


def wire_grade(a_to_b=None, b_to_a=None, neutral="unknown", mixed=False,
               coverage="thin", confidence="medium"):
    return {
        "directions": {"a_to_b": a_to_b or wire_direction(),
                       "b_to_a": b_to_a or wire_direction()},
        "observation_coverage": coverage,
        "observation_coverage_basis": "4 encounters, 2021, CREC only",
        "neutral_assessment": neutral,
        "mixed_ambivalent": mixed,
        "rationale": "Ceremonial courtesy only.",
        "confidence": confidence,
    }


def graded(affinity_ab, friction_ab="unassessable", affinity_ba="1", ritual_ab=False,
           neutral="unknown", mixed=False):
    """A normalised grade, via the real normaliser."""
    arange = ("0", "4") if affinity_ab != "unassessable" else ("unassessable", "unassessable")
    frange = ("0", "4") if friction_ab != "unassessable" else ("unassessable", "unassessable")
    return bg.normalise_pair_grade(wire_grade(
        a_to_b=wire_direction(affinity_ab, friction_ab, ritual_ab, arange, frange),
        b_to_a=wire_direction(affinity_ba, "unassessable", False,
                              ("0", "4") if affinity_ba != "unassessable"
                              else ("unassessable", "unassessable")),
        neutral=neutral, mixed=mixed))


def calib_row(mid="cal-1"):
    return {"mention_id": mid, "actor": "A000001", "target": "B000002",
            "actor_name": "Alice Adams", "target_name": "Bob Baker", "date": "2021-03-04",
            "source": "CREC", "chamber": "House", "package": "CREC-2021-03-04",
            "source_rowid": 99, "context_650": "I thank my friend for yielding.",
            "review_status": "unreviewed",
            "sampling_basis": "systematic_encounter_random_sample"}


def review(**over):
    base = {"speaker_verified": True, "target_verified": True, "quoted_only": False,
            "content_status": "resolved", "substantive_warmth": False,
            "personal_hostility": False, "promptedness": "prompted", "ritual_language": True,
            "personal_act": False, "escalation": "none", "reciprocity": False, "repair": False,
            "alternative_explanation": "institutional_courtesy",
            "speech_purpose": "procedural_yield", "rationale": "Routine yield."}
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# blinding
# ---------------------------------------------------------------------------

class BlindingTests(unittest.TestCase):
    def test_prompt_strips_party_state_work_and_cue_fields(self):
        dirty = packet(extras={
            "party": ["Democrat", "Republican"],
            "state": ["California", "Wisconsin"],
            "work_scores": {"direct_propensity": 0.42, "shared_bills_label": "many shared bills"},
            "model_scores": {"affinity_hat": 0.77},
            "personality_values": {"extraversion": 1.2},
        })
        payload, rendered = bg.pair_prompt(dirty, "A")
        keys = bg._all_keys(payload)
        for forbidden in ("party", "state", "work_scores", "model_scores", "personality_values",
                          "hidden_cue_counts", "coverage_tiers", "design_weight", "stratum",
                          "split"):
            self.assertNotIn(forbidden, keys)
            self.assertNotIn(forbidden, rendered)
        for value in ("Democrat", "Republican", "California", "Wisconsin",
                      "many shared bills", "LH|different|House+House"):
            self.assertNotIn(value, rendered)
        # the whitelisted content is still there
        self.assertIn("Alice Adams", rendered)
        self.assertIn("m-a0", rendered)

    def test_assert_blind_raises_on_a_leaked_dropped_value(self):
        # a key name that is NOT on the forbidden list, so only check 3 can fire
        source = packet(extras={"caucus_label": "Democratic Caucus"})
        payload, rendered = bg.pair_prompt(source, "A")   # clean: must not raise
        with self.assertRaises(bg.BlindingError):
            bg.assert_blind(payload, rendered + "\ncaucus: Democratic Caucus", source=source)

    def test_dropped_bioguides_inside_the_whitelisted_pair_id_are_not_a_leak(self):
        source = packet()
        payload, rendered = bg.pair_prompt(source, "A")
        self.assertIn("A000001__B000002", rendered)
        self.assertNotIn("A000001", bg._string_values(payload) - {"A000001__B000002"})

    def test_assert_blind_raises_on_a_forbidden_payload_key(self):
        with self.assertRaises(bg.BlindingError):
            bg.assert_blind({"stratum": "x"}, "clean text")

    def test_source_excerpt_may_legitimately_say_state(self):
        p = packet(n_a=1, n_b=1)
        p["directions"]["a_to_b"]["mentions"][0]["context_650"] = (
            "I thank the gentleman from the great State of Wisconsin for his party's cooperation "
            "on this work.")
        payload, rendered = bg.pair_prompt(p, "A")  # must not raise
        self.assertIn("great State of Wisconsin", rendered)


# ---------------------------------------------------------------------------
# shuffle
# ---------------------------------------------------------------------------

class ShuffleTests(unittest.TestCase):
    def test_order_is_deterministic_and_differs_between_passes(self):
        ids = ["m-%02d" % i for i in range(12)]
        a1 = bg.seeded_order(ids, "PAIR", "A")
        a2 = bg.seeded_order(ids, "PAIR", "A")
        b1 = bg.seeded_order(ids, "PAIR", "B")
        self.assertEqual(a1, a2)
        self.assertNotEqual(a1, b1)
        self.assertEqual(sorted(a1), sorted(ids))
        self.assertEqual(sorted(b1), sorted(ids))

    def test_order_differs_between_pairs(self):
        ids = ["m-%02d" % i for i in range(12)]
        self.assertNotEqual(bg.seeded_order(ids, "PAIR1", "A"), bg.seeded_order(ids, "PAIR2", "A"))

    def test_prompt_mention_order_differs_between_passes(self):
        p = packet(n_a=10, n_b=2)
        _, ra = bg.pair_prompt(p, "A")
        _, rb = bg.pair_prompt(p, "B")
        self.assertNotEqual(ra, rb)
        self.assertEqual(sorted(bg.build_pair_payload(p, "A")["directions"]["a_to_b"]["mentions"],
                                key=lambda m: m["mention_id"]),
                         sorted(bg.build_pair_payload(p, "B")["directions"]["a_to_b"]["mentions"],
                                key=lambda m: m["mention_id"]))


# ---------------------------------------------------------------------------
# loaders
# ---------------------------------------------------------------------------

class LoaderTests(unittest.TestCase):
    def _write(self, rows):
        handle = tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False, encoding="utf-8")
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_heldout_rows_are_refused(self):
        path = self._write([packet(), packet(pair_id="C__D", split="heldout")])
        with self.assertRaises(bg.SealedSplitError):
            bg.load_pair_packets(path)

    def test_heldout_is_refused_even_as_the_first_row(self):
        path = self._write([packet(pair_id="C__D", split="heldout")])
        with self.assertRaises(bg.SealedSplitError):
            bg.load_pair_packets(path)

    def test_schema_drift_fails_loudly(self):
        broken = packet()
        del broken["directions"]["b_to_a"]
        with self.assertRaises(bg.SchemaDrift):
            bg.load_pair_packets(self._write([broken]))
        missing_key = packet()
        del missing_key["directions"]["a_to_b"]["mentions"][0]["context_650"]
        with self.assertRaises(bg.SchemaDrift):
            bg.load_pair_packets(self._write([missing_key]))
        dup = packet(n_a=2)
        dup["directions"]["a_to_b"]["mentions"][1]["mention_id"] = "m-a0"
        with self.assertRaises(bg.SchemaDrift):
            bg.load_pair_packets(self._write([dup]))

    def test_calibration_loader_refuses_cue_columns(self):
        with self.assertRaises(bg.BlindingError):
            bg.load_calibration(self._write([dict(calib_row(), cue_warm=True)]))

    def test_producer_direction_keys_are_canonicalised(self):
        """systematic_encounters.py:782 keys directions '<actor>-><target>'."""
        raw = packet()
        raw["directions"] = {
            "B000002->A000001": dict(raw["directions"]["b_to_a"], actor="B000002",
                                     target="A000001"),
            "A000001->B000002": dict(raw["directions"]["a_to_b"], actor="A000001",
                                     target="B000002"),
        }
        loaded = bg.load_pair_packets(self._write([raw]))[0]
        self.assertEqual(sorted(loaded["directions"]), ["a_to_b", "b_to_a"])
        self.assertEqual(loaded["directions"]["a_to_b"]["mentions"][0]["mention_id"], "m-a0")
        self.assertEqual(loaded["directions"]["b_to_a"]["mentions"][0]["mention_id"], "m-b0")
        _, rendered = bg.pair_prompt(loaded, "A")
        self.assertNotIn("A000001->B000002", rendered)

    def test_unmappable_direction_keys_fail_loudly(self):
        raw = packet()
        raw["directions"] = {"X->Y": raw["directions"]["a_to_b"],
                             "Y->X": raw["directions"]["b_to_a"]}
        with self.assertRaises(bg.SchemaDrift):
            bg.load_pair_packets(self._write([raw]))

    def test_hearing_dates_are_read_from_package_entries(self):
        """systematic_encounters.py:800 emits packages=[{package, date}], no dates key."""
        raw = packet()
        raw["hearing_coappearances"] = {
            "count": 2,
            "packages": [{"package": "CHRG-118a", "date": "2023-04-05"},
                         {"package": "CHRG-118b", "date": "2023-06-07"}]}
        payload, rendered = bg.pair_prompt(raw, "A")
        self.assertEqual(payload["hearing_coappearances"]["dates"], ["2023-04-05", "2023-06-07"])
        self.assertIn("2023-04-05", rendered)
        self.assertNotIn("CHRG-118a", rendered)

    def test_limit_is_honoured(self):
        path = self._write([packet(pair_id="P%d__Q" % i) for i in range(5)])
        self.assertEqual(len(bg.load_pair_packets(path, limit=2)), 2)


# ---------------------------------------------------------------------------
# rubric invariants
# ---------------------------------------------------------------------------

class InvariantTests(unittest.TestCase):
    def test_neutral_cannot_be_true_when_any_degree_is_two_or_more(self):
        for a, f in (("2", "unassessable"), ("0", "3"), ("4", "0")):
            out = bg.normalise_pair_grade(wire_grade(
                a_to_b=wire_direction(a, f, arange=("0", "4"),
                                      frange=("0", "4") if f != "unassessable"
                                      else ("unassessable", "unassessable")),
                b_to_a=wire_direction("0", "0", arange=("0", "0"), frange=("0", "0")),
                neutral="true"))
            self.assertEqual(out["neutral_assessment"], "unknown")
            self.assertTrue(any("neutral_assessment forced" in c for c in out["coercions"]))

    def test_neutral_cannot_be_true_when_a_degree_is_unassessable(self):
        out = bg.normalise_pair_grade(wire_grade(
            a_to_b=wire_direction("1", "unassessable", arange=("0", "1")),
            b_to_a=wire_direction("0", "0", arange=("0", "0"), frange=("0", "0")),
            neutral="true"))
        self.assertEqual(out["neutral_assessment"], "unknown")

    def test_neutral_true_survives_when_every_degree_is_low_and_assessed(self):
        low = wire_direction("1", "0", arange=("0", "1"), frange=("0", "1"))
        out = bg.normalise_pair_grade(wire_grade(a_to_b=low, b_to_a=low, neutral="true"))
        self.assertIs(out["neutral_assessment"], True)
        self.assertEqual(out["coercions"], [])

    def test_mixed_is_forced_false_without_a_doubly_high_direction(self):
        out = bg.normalise_pair_grade(wire_grade(
            a_to_b=wire_direction("3", "0", arange=("0", "4"), frange=("0", "1")),
            b_to_a=wire_direction("0", "0", arange=("0", "0"), frange=("0", "0")),
            mixed=True))
        self.assertFalse(out["mixed_ambivalent"])

    def test_range_is_widened_to_contain_the_degree_and_the_coercion_is_recorded(self):
        out = bg.normalise_pair_grade(wire_grade(
            a_to_b=wire_direction("4", "unassessable", arange=("0", "2"))))
        self.assertEqual(out["directions"]["a_to_b"]["affinity_range"], [0, 4])
        self.assertTrue(any("widened" in c for c in out["coercions"]))

    def test_unassessable_degree_carries_a_null_range(self):
        out = bg.normalise_pair_grade(wire_grade(
            a_to_b=wire_direction("unassessable", "unassessable",
                                  arange=("unassessable", "unassessable"))))
        self.assertIsNone(out["directions"]["a_to_b"]["affinity_range"])
        self.assertEqual(out["directions"]["a_to_b"]["affinity_degree"], "unassessable")


# ---------------------------------------------------------------------------
# schema validation
# ---------------------------------------------------------------------------

class SchemaTests(unittest.TestCase):
    def test_valid_grade_passes(self):
        self.assertEqual(bg.validate_against_schema(wire_grade(), bg.pair_grade_schema()), [])

    def test_malformed_grades_are_rejected(self):
        schema = bg.pair_grade_schema()
        bad_enum = wire_grade()
        bad_enum["directions"]["a_to_b"]["affinity_degree"] = "7"
        self.assertTrue(bg.validate_against_schema(bad_enum, schema))

        missing = wire_grade()
        del missing["confidence"]
        self.assertTrue(bg.validate_against_schema(missing, schema))

        wrong_type = wire_grade()
        wrong_type["mixed_ambivalent"] = "yes"
        self.assertTrue(bg.validate_against_schema(wrong_type, schema))

        extra = wire_grade()
        extra["party"] = "D"
        self.assertTrue(bg.validate_against_schema(extra, schema))

        bad_nested = wire_grade()
        bad_nested["directions"]["b_to_a"]["closeness_trust_evidence"] = [
            {"indicator": "telepathy", "mention_ids": []}]
        self.assertTrue(bg.validate_against_schema(bad_nested, schema))

    def test_calibration_schema_round_trip(self):
        self.assertEqual(bg.validate_against_schema(review(), bg.calibration_schema()), [])
        self.assertTrue(bg.validate_against_schema(review(escalation="a lot"),
                                                   bg.calibration_schema()))
        self.assertTrue(bg.validate_against_schema(review(speaker_verified="true"),
                                                   bg.calibration_schema()))

    def test_no_forbidden_key_appears_in_the_response_schema(self):
        for schema in (bg.pair_grade_schema(), bg.calibration_schema()):
            self.assertFalse(sorted(k for k in bg._all_keys(schema)
                                    if k.lower() in bg.FORBIDDEN_KEYS))


# ---------------------------------------------------------------------------
# agreement
# ---------------------------------------------------------------------------

class AgreementTests(unittest.TestCase):
    def test_kappa_is_one_when_the_passes_are_identical(self):
        a = {"p%d" % i: graded(str(i % 5)) for i in range(10)}
        b = {k: json.loads(json.dumps(v)) for k, v in a.items()}
        report = bg.pair_agreement(a, b)
        cell = report["dimensions"]["affinity"]["a_to_b"]
        self.assertEqual(cell["quadratic_weighted_kappa"], 1.0)
        self.assertEqual(cell["exact_agreement"]["rate"], 1.0)
        self.assertEqual(cell["within_1_agreement"]["rate"], 1.0)
        self.assertEqual(report["disagreements"], [])
        self.assertEqual(report["pairs_needing_adjudication"], 0)

    def test_kappa_is_one_on_a_constant_pair_of_identical_ratings(self):
        self.assertEqual(bg.quadratic_weighted_kappa([2, 2, 2], [2, 2, 2]), 1.0)

    def test_exact_and_within_one_counts(self):
        a = {"p1": graded("2"), "p2": graded("2"), "p3": graded("2"), "p4": graded("2")}
        b = {"p1": graded("2"), "p2": graded("3"), "p3": graded("4"), "p4": graded("0")}
        cell = bg.pair_agreement(a, b)["dimensions"]["affinity"]["a_to_b"]
        self.assertEqual(cell["both_assessed_n"], 4)
        self.assertEqual(cell["exact_agreement"]["agree"], 1)
        self.assertEqual(cell["within_1_agreement"]["agree"], 2)

    def test_queue_picks_delta_ge_two_and_assessability_mismatches(self):
        a = {"p1": graded("0"), "p2": graded("unassessable"), "p3": graded("2")}
        b = {"p1": graded("3"), "p2": graded("2"), "p3": graded("3")}
        report = bg.pair_agreement(a, b)
        cats = {(r["pair_id"], r["category"]) for r in report["disagreements"]}
        self.assertIn(("p1", "degree_delta_ge2"), cats)
        self.assertIn(("p2", "assessability_mismatch"), cats)
        self.assertNotIn(("p3", "degree_delta_ge2"), cats)  # |delta| == 1 is not queued
        self.assertEqual(report["pairs_needing_adjudication"], 2)

    def test_neutral_and_mixed_mismatches_are_queued(self):
        a = {"p1": graded("1", neutral="true"), "p2": graded("2", "2", mixed=True)}
        b = {"p1": graded("1", neutral="false"), "p2": graded("2", "2", mixed=False)}
        cats = {(r["pair_id"], r["category"]) for r in bg.pair_agreement(a, b)["disagreements"]}
        self.assertIn(("p1", "neutral_mismatch"), cats)
        self.assertIn(("p2", "mixed_mismatch"), cats)

    def test_assessability_agreement_counts_both_unassessable_as_agreement(self):
        a = {"p1": graded("unassessable")}
        b = {"p1": graded("unassessable")}
        cell = bg.pair_agreement(a, b)["dimensions"]["affinity"]["a_to_b"]
        self.assertEqual(cell["assessability_agreement"]["rate"], 1.0)
        self.assertEqual(cell["both_assessed_n"], 0)
        self.assertIsNone(cell["quadratic_weighted_kappa"])


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

class MergeTests(unittest.TestCase):
    meta = {"model": "m", "effort": "medium", "rubric_sha256": "r", "packet_sha256": "p",
            "run_id": "run"}

    def _merge(self, a, b, pid="p1"):
        return bg.merge_labels({pid: packet(pair_id=pid)}, {pid: a}, {pid: b}, dict(self.meta))[0]

    def test_ritual_courtesy_only_caps_affinity_at_one(self):
        row = self._merge(graded("3", ritual_ab=True), graded("3", ritual_ab=True))
        entry = row["directions"]["a_to_b"]["affinity"]
        self.assertEqual(entry["value"], 1)
        self.assertEqual(entry["pre_cap_value"], 3)
        self.assertTrue(entry["ritual_cap_applied"])
        self.assertEqual(entry["range"][1], 1)

    def test_no_cap_when_the_passes_disagree_about_ritual_courtesy(self):
        row = self._merge(graded("3", ritual_ab=True), graded("3", ritual_ab=False))
        entry = row["directions"]["a_to_b"]["affinity"]
        self.assertFalse(entry["ritual_cap_applied"])
        self.assertTrue(entry["adjudication_needed"])
        self.assertEqual(entry["adjudication_reason"], "ritual_courtesy_mismatch")
        self.assertTrue(row["directions"]["a_to_b"]["ritual_courtesy_mismatch"])

    def test_agreed_values_are_filled(self):
        row = self._merge(graded("2"), graded("2"))
        self.assertEqual(row["directions"]["a_to_b"]["affinity"]["value"], 2)
        self.assertEqual(row["directions"]["a_to_b"]["affinity"]["merge_rule"], "exact")
        self.assertFalse(row["adjudication_needed"])
        self.assertEqual(row["sampling_basis"], "development_probability_sample")
        self.assertEqual(row["reviewer_blinding"],
                         {"model_scores": False, "personality_values": False, "work_scores": False})
        self.assertEqual(row["design_weight"], 1378.8)

    def test_disagreements_are_marked_not_averaged(self):
        row = self._merge(graded("0"), graded("4"))
        entry = row["directions"]["a_to_b"]["affinity"]
        self.assertIsNone(entry["value"])
        self.assertTrue(entry["adjudication_needed"])
        self.assertEqual(entry["adjudication_reason"], "degree_delta_ge2")
        self.assertTrue(row["adjudication_needed"])

    def test_adjacent_disagreement_takes_the_lower_degree(self):
        row = self._merge(graded("3"), graded("2"))
        entry = row["directions"]["a_to_b"]["affinity"]
        self.assertEqual(entry["value"], 2)
        self.assertEqual(entry["merge_rule"], "min_of_adjacent")
        self.assertFalse(entry["adjudication_needed"])

    def test_assessability_mismatch_blocks_the_merge(self):
        row = self._merge(graded("unassessable"), graded("2"))
        entry = row["directions"]["a_to_b"]["affinity"]
        self.assertIsNone(entry["value"])
        self.assertEqual(entry["adjudication_reason"], "assessability_mismatch")

    def test_confidence_merges_to_the_lower_of_the_two(self):
        a = bg.normalise_pair_grade(wire_grade(confidence="high"))
        b = bg.normalise_pair_grade(wire_grade(confidence="low"))
        self.assertEqual(self._merge(a, b)["confidence"]["value"], "low")

    def test_adjudication_queue_renders_the_queued_items(self):
        a, b = {"p1": graded("0")}, {"p1": graded("4")}
        packets = {"p1": packet(pair_id="p1")}
        report = bg.pair_agreement(a, b)
        merged = bg.merge_labels(packets, a, b, dict(self.meta))
        text = bg.adjudication_queue_markdown(report, merged, packets, a, b, dict(self.meta))
        self.assertIn("degree_delta_ge2", text)
        self.assertIn("Alice Adams", text)
        self.assertIn("Most-cited excerpts", text)
        self.assertIn("m-a0", text)
        self.assertIn("STATUS: EXPLORATORY", text)


# ---------------------------------------------------------------------------
# calibration gate and cue scoring
# ---------------------------------------------------------------------------

class CalibrationTests(unittest.TestCase):
    meta = {"model": "m", "effort": "medium", "rubric_sha256": "r", "run_id": "run"}

    def _gate(self, a, b, mid="cal-1"):
        return bg.calibration_gate({mid: calib_row(mid)}, {mid: a}, {mid: b}, dict(self.meta))[0]

    def test_context_reviewed_only_on_full_agreement(self):
        row = self._gate(review(), review())
        self.assertEqual(row["review_status"], "context_reviewed")
        self.assertEqual(row["sampling_basis"], "systematic_encounter_review")
        self.assertIs(row["substantive_warmth"], False)
        self.assertIs(row["personal_hostility"], False)
        self.assertFalse(row["adjudication_needed"])

    def test_warmth_disagreement_yields_ambiguous_and_no_boolean(self):
        row = self._gate(review(substantive_warmth=True), review(substantive_warmth=False))
        self.assertEqual(row["review_status"], "ambiguous")
        self.assertIsNone(row["substantive_warmth"])
        self.assertTrue(row["adjudication_needed"])

    def test_verification_disagreement_yields_ambiguous(self):
        row = self._gate(review(target_verified=True), review(target_verified=False))
        self.assertEqual(row["review_status"], "ambiguous")

    def test_unresolved_content_yields_ambiguous(self):
        row = self._gate(review(content_status="unresolved"), review(content_status="unresolved"))
        self.assertEqual(row["review_status"], "ambiguous")

    def test_speech_purpose_disagreement_yields_ambiguous(self):
        row = self._gate(review(speech_purpose="floor_debate"),
                         review(speech_purpose="floor_tribute"))
        self.assertEqual(row["review_status"], "ambiguous")
        self.assertIsNone(row["speech_purpose"])

    def test_gate_rows_satisfy_the_chamber_expression_field_gate(self):
        row = self._gate(review(), review())
        self.assertEqual(row["review_status"], "context_reviewed")
        self.assertEqual(row["sampling_basis"], "systematic_encounter_review")
        self.assertTrue(row["speaker_verified"])
        self.assertTrue(row["target_verified"])
        self.assertFalse(row["quoted_only"])
        self.assertEqual(row["content_status"], "resolved")
        self.assertTrue(row["speech_purpose"])
        for key in ("substantive_warmth", "personal_hostility"):
            self.assertIs(type(row[key]), bool)
        self.assertTrue(row["venue"])
        self.assertTrue(row["source_family"])
        self.assertTrue(row["episode_id"])

    def test_calibration_agreement_kappa_and_rates(self):
        ids = ["c%d" % i for i in range(6)]
        a = {i: review(substantive_warmth=(int(i[1:]) % 2 == 0)) for i in ids}
        b = dict(a)
        report = bg.calibration_agreement(a, b)
        self.assertEqual(report["keys"]["substantive_warmth"]["rate"], 1.0)
        self.assertEqual(report["keys"]["substantive_warmth"]["cohen_kappa"], 1.0)
        self.assertEqual(report["gate_agreement"]["rate"], 1.0)

    def test_cue_precision_recall_uses_reviewed_rows_only(self):
        rows = []
        for i, (warm_review, status) in enumerate([(True, "ok"), (True, "ok"), (False, "ok"),
                                                   (True, "ambiguous")]):
            a = review(substantive_warmth=warm_review)
            b = review(substantive_warmth=warm_review if status == "ok" else not warm_review)
            rows.append(bg.calibration_gate({"c%d" % i: calib_row("c%d" % i)},
                                            {"c%d" % i: a}, {"c%d" % i: b}, {})[0])
        cues = {"c0": {"cue_warm": True, "cue_hostile": False},
                "c1": {"cue_warm": False, "cue_hostile": False},
                "c2": {"cue_warm": True, "cue_hostile": False},
                "c3": {"cue_warm": True, "cue_hostile": False}}
        out = bg.cue_precision_recall(rows, cues)
        self.assertEqual(out["excluded_ambiguous_rows"], 1)
        cell = out["overall"]["cue_warm_vs_substantive_warmth"]
        self.assertEqual(cell["tp"], 1)   # c0
        self.assertEqual(cell["fn"], 1)   # c1
        self.assertEqual(cell["fp"], 1)   # c2
        self.assertEqual(cell["precision"], 0.5)
        self.assertEqual(cell["recall"], 0.5)
        self.assertEqual(out["overall"]["n"], 3)
        self.assertEqual(sorted(out["strata"]), ["House|CREC"])


# ---------------------------------------------------------------------------
# API call policy (monkeypatched: no network)
# ---------------------------------------------------------------------------

class FakeTransport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.bodies = []

    def __call__(self, body):
        self.bodies.append(body)
        return self.responses.pop(0)


def api_response(stop_reason="end_turn", data=None, text=None):
    return {"stop_reason": stop_reason,
            "text": text if text is not None else json.dumps(data or wire_grade()),
            "usage": {"input_tokens": 100, "output_tokens": 50,
                      "cache_creation_input_tokens": 0, "cache_read_input_tokens": 900},
            "stop_details": None, "transport_attempts": 1}


class CallPolicyTests(unittest.TestCase):
    def _client(self, responses):
        client = bg.GradingClient.__new__(bg.GradingClient)
        client.model, client.effort, client.max_tokens = bg.MODEL, bg.EFFORT, bg.MAX_TOKENS
        client.sdk, client.path, client._key = None, "fake", "unused"
        transport = FakeTransport(responses)
        client._once = transport
        return client, transport

    def test_happy_path_returns_validated_data(self):
        client, transport = self._client([api_response()])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertTrue(out["ok"])
        self.assertEqual(out["usage"]["cache_read_input_tokens"], 900)
        body = transport.bodies[0]
        self.assertEqual(body["thinking"], {"type": "adaptive"})
        self.assertEqual(body["output_config"]["effort"], bg.EFFORT)
        self.assertEqual(body["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(body["system"][0]["cache_control"], {"type": "ephemeral"})
        self.assertNotIn("temperature", body)
        self.assertNotIn("top_p", body)
        self.assertEqual([m["role"] for m in body["messages"]], ["user"])

    def test_refusal_is_recorded_retried_once_then_failed(self):
        client, transport = self._client([api_response("refusal", text=""),
                                          api_response("refusal", text="")])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "refusal")
        self.assertEqual(len(out["attempts"]), 2)
        self.assertEqual(len(transport.bodies), 2)

    def test_max_tokens_retry_raises_the_ceiling_once(self):
        client, transport = self._client([api_response("max_tokens", text=""), api_response()])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertTrue(out["ok"])
        self.assertEqual(transport.bodies[0]["max_tokens"], bg.MAX_TOKENS)
        self.assertEqual(transport.bodies[1]["max_tokens"],
                         bg.MAX_TOKENS * bg.MAX_TOKENS_RETRY_MULTIPLIER)
        self.assertEqual(out["attempts"][0]["outcome"], "max_tokens")

    def test_schema_invalid_output_is_retried_then_failed(self):
        bad = wire_grade()
        bad["confidence"] = "certain"
        client, _ = self._client([api_response(data=bad), api_response(data=bad)])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "schema_invalid")

    def test_unparseable_json_is_retried_then_recovered(self):
        client, _ = self._client([api_response(text="not json at all"), api_response()])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertTrue(out["ok"])
        self.assertEqual(out["attempts"][0]["outcome"], "unparseable_json")

    def test_non_retryable_4xx_is_not_retried(self):
        """A 400 (bad request, dead key, no credit) fails identically every time.
        Retrying it only doubles the bill, so the item fails on the first response."""
        class Boom:
            calls = 0

            def __call__(self, body):
                Boom.calls += 1
                raise bg.NonRetryableAPIError("400 credit balance too low")

        client, _ = self._client([])
        client._once = Boom()
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertFalse(out["ok"])
        self.assertEqual(Boom.calls, 1)
        self.assertEqual(out["attempts"][0]["outcome"], "non_retryable_4xx")
        self.assertEqual(len(out["attempts"]), 1)

    def test_retryable_transport_error_gets_the_second_content_attempt(self):
        class Flaky:
            calls = 0

            def __call__(self, body):
                Flaky.calls += 1
                if Flaky.calls == 1:
                    raise RuntimeError("503 upstream")
                return api_response()

        client, _ = self._client([])
        client._once = Flaky()
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertTrue(out["ok"])
        self.assertEqual(Flaky.calls, 2)

    def test_usage_accumulates_across_content_attempts(self):
        client, _ = self._client([api_response("max_tokens", text=""), api_response()])
        out = client.call("sys", "user", bg.pair_grade_schema())
        self.assertEqual(out["usage"]["input_tokens"], 200)
        self.assertEqual(out["usage"]["output_tokens"], 100)


# ---------------------------------------------------------------------------
# cost and receipts
# ---------------------------------------------------------------------------

class CostTests(unittest.TestCase):
    def test_cost_uses_the_cache_discount_and_write_premium(self):
        usage = {"input_tokens": 1_000_000, "output_tokens": 1_000_000,
                 "cache_creation_input_tokens": 1_000_000, "cache_read_input_tokens": 1_000_000}
        self.assertAlmostEqual(bg.estimate_cost(usage, "claude-sonnet-5"),
                               2.0 + 2.5 + 0.2 + 10.0, places=6)

    def test_unknown_model_refuses_to_price(self):
        with self.assertRaises(SystemExit):
            bg.estimate_cost({"input_tokens": 1}, "claude-not-a-model")

    def test_report_carries_status_and_denominators(self):
        a = {"p1": graded("2"), "p2": graded("2")}
        b = {"p1": graded("2"), "p2": graded("0")}
        agreement = bg.pair_agreement(a, b)
        receipt = {"run_id": "r", "started_utc": "t", "model": "claude-sonnet-5",
                   "effort": "medium", "max_tokens": 4000, "api_path": "fake",
                   "rubric_sha256": "abc", "counts": {"pairs_attempted": 2, "api_calls": 4},
                   "usage_total": {"input_tokens": 1, "output_tokens": 1,
                                   "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
                   "estimated_cost_usd": 0.0001, "failures": []}
        text = bg.build_report(receipt, agreement)
        self.assertIn("STATUS: EXPLORATORY", text)
        self.assertIn("of 2", text)
        self.assertIn("does not establish", text)


# ---------------------------------------------------------------------------
# the no-evidence short circuit
# ---------------------------------------------------------------------------

NO_HEARINGS = {"hearing_coappearances": {"count": 0, "packages": []}}


def empty_packet(pair_id="E000001__F000002"):
    row = packet(pair_id=pair_id, n_a=0, n_b=0, extras=dict(NO_HEARINGS))
    return row


class ExplodingClient:
    """Any API call through this is a test failure."""

    def __init__(self):
        self.calls = 0

    def call(self, *_a, **_k):
        self.calls += 1
        raise AssertionError("the harness made an API call for a packet with no evidence")


class ScriptedClient:
    """Returns a canned OK result, except for pair ids listed in `explode`."""

    def __init__(self, explode=()):
        self.explode = set(explode)
        self.calls = 0

    def call(self, _system, user_text, _schema):
        self.calls += 1
        for pid in self.explode:
            if pid in user_text:
                raise RuntimeError("boom in %s" % pid)
        return {"ok": True, "data": wire_grade(), "attempts": [{"outcome": "ok"}],
                "usage": {"input_tokens": 10, "output_tokens": 5,
                          "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
                "raw_text": "{}"}


class NoEvidenceTests(unittest.TestCase):
    def test_an_empty_packet_has_no_evidence(self):
        ev = bg.packet_evidence(empty_packet())
        self.assertFalse(ev["has_evidence"])
        self.assertEqual(ev["mentions_supplied_total"], 0)
        self.assertEqual(ev["mention_turns_total"], 0)
        self.assertEqual(ev["hearing_coappearances"], 0)

    def test_one_supplied_excerpt_is_evidence(self):
        self.assertTrue(bg.has_evidence(packet(n_a=1, n_b=0, extras=dict(NO_HEARINGS))))

    def test_a_shared_hearing_alone_is_evidence(self):
        row = packet(n_a=0, n_b=0, extras={"hearing_coappearances": {"count": 2,
                                                                     "packages": [],
                                                                     "dates": ["2021-05-06"]}})
        self.assertTrue(bg.has_evidence(row))

    def test_a_recorded_turn_with_no_supplied_excerpt_is_still_evidence(self):
        """mention_total counts turns and the excerpt list can be capped away;
        a packet that records contact must never be short-circuited."""
        row = empty_packet()
        row["directions"]["a_to_b"]["mention_total"] = 3
        self.assertTrue(bg.has_evidence(row))

    def test_partition_preserves_order_and_drops_nothing(self):
        rows = [empty_packet("A__1"), packet(pair_id="B__2", n_a=2, n_b=0, extras=dict(NO_HEARINGS)),
                empty_packet("C__3")]
        gradable, empty = bg.partition_by_evidence(rows)
        self.assertEqual([p["pair_id"] for p in gradable], ["B__2"])
        self.assertEqual([p["pair_id"] for p in empty], ["A__1", "C__3"])
        self.assertEqual(len(gradable) + len(empty), len(rows))

    def test_no_evidence_row_is_unassessable_none_and_unknown(self):
        row = bg.no_evidence_label_row(empty_packet(), {})
        self.assertEqual(row["label_status"], bg.NO_EVIDENCE_LABEL_STATUS)
        self.assertEqual(row["graded_via"], "no_evidence_short_circuit")
        self.assertEqual(row["api_calls"], 0)
        self.assertEqual(row["observation_coverage"]["value"], "none")
        self.assertEqual(row["neutral_assessment"]["value"], "unknown")
        self.assertFalse(row["adjudication_needed"])
        for d in bg.DIRECTIONS:
            for dim in bg.DIMENSIONS:
                self.assertEqual(row["directions"][d][dim]["value"], "unassessable")
                self.assertIsNone(row["directions"][d][dim]["range"])
                self.assertIsNone(row["directions"][d][dim]["pass_a"])
                self.assertIsNone(row["directions"][d][dim]["pass_b"])

    def test_no_evidence_row_never_claims_a_zero(self):
        row = bg.no_evidence_label_row(empty_packet(), {})
        values = [row["directions"][d][dim]["value"]
                  for d in bg.DIRECTIONS for dim in bg.DIMENSIONS]
        self.assertNotIn(0, values)
        self.assertNotIn("0", values)
        self.assertNotEqual(row["neutral_assessment"]["value"], True)

    def test_no_evidence_grade_has_the_same_shape_as_a_normalised_grade(self):
        real = bg.normalise_pair_grade(wire_grade())
        synthetic = bg.no_evidence_grade()
        self.assertEqual(sorted(real), sorted(synthetic))
        for d in bg.DIRECTIONS:
            self.assertEqual(sorted(real["directions"][d]), sorted(synthetic["directions"][d]))

    def test_no_evidence_row_carries_the_evidence_it_was_judged_on(self):
        row = bg.no_evidence_label_row(empty_packet(), {})
        self.assertIn("evidence", row)
        self.assertFalse(row["evidence"]["has_evidence"])

    def test_run_pairs_makes_no_call_for_an_all_empty_batch(self):
        client = ExplodingClient()
        with tempfile.TemporaryDirectory() as tmp:
            result = bg.run_pairs([empty_packet("A__1"), empty_packet("B__2")], client,
                                  "SYSTEM", tmp, concurrency=2, log=lambda *_a: None)
        self.assertEqual(client.calls, 0)
        self.assertEqual(result["partition"]["pairs_no_evidence"], 2)
        self.assertEqual(result["partition"]["api_calls_planned"], 0)
        self.assertEqual(result["partition"]["api_calls_avoided"], 4)
        self.assertEqual([p["pair_id"] for p in result["no_evidence"]], ["A__1", "B__2"])

    def test_run_pairs_calls_only_for_the_evidenced_packets(self):
        client = ScriptedClient()
        rows = [empty_packet("A__1"), packet(pair_id="B__2", n_a=2, n_b=1, extras=dict(NO_HEARINGS)),
                empty_packet("C__3")]
        with tempfile.TemporaryDirectory() as tmp:
            result = bg.run_pairs(rows, client, "SYSTEM", tmp, concurrency=2, log=lambda *_a: None)
        self.assertEqual(client.calls, 2)  # one evidenced packet, two passes
        self.assertEqual(result["partition"]["pairs_with_evidence"], 1)
        self.assertEqual(result["partition"]["api_calls_avoided"], 4)
        self.assertEqual([r["pair_id"] for r in result["raw"]["A"]], ["B__2"])

    def test_dry_run_separates_sent_prompts_from_never_sent_ones(self):
        rows = [empty_packet("A__1"), packet(pair_id="B__2", n_a=2, n_b=1, extras=dict(NO_HEARINGS))]
        with tempfile.TemporaryDirectory() as tmp:
            bg.run_pairs(rows, None, "SYSTEM", tmp, dry_run=True, log=lambda *_a: None)
            sent = sorted(p.name for p in (Path(tmp) / "prompts" / "pairs").glob("*.txt"))
            skipped = sorted(p.name for p in
                             (Path(tmp) / "prompts" / "pairs_no_evidence_not_sent").glob("*.txt"))
            partition = json.loads((Path(tmp) / "prompts" / "pair_partition.json")
                                   .read_text(encoding="utf-8"))
        self.assertEqual(sent, ["B__2__passA.txt", "B__2__passB.txt"])
        self.assertEqual(skipped, ["A__1__passA.txt", "A__1__passB.txt"])
        self.assertEqual(partition["pairs_with_evidence"], 1)
        self.assertEqual(partition["no_evidence_pair_ids"], ["A__1"])

    def test_most_evidenced_picks_the_largest_and_is_deterministic(self):
        rows = [empty_packet("Z__0"),
                packet(pair_id="M__1", n_a=1, n_b=0, extras=dict(NO_HEARINGS)),
                packet(pair_id="L__2", n_a=9, n_b=4, extras=dict(NO_HEARINGS)),
                packet(pair_id="K__3", n_a=3, n_b=3, extras=dict(NO_HEARINGS))]
        picked = [p["pair_id"] for p in bg.most_evidenced(rows, 3)]
        self.assertEqual(picked, ["L__2", "K__3", "M__1"])
        self.assertEqual(picked, [p["pair_id"] for p in bg.most_evidenced(list(reversed(rows)), 3)])

    def test_most_evidenced_breaks_ties_on_pair_id(self):
        rows = [packet(pair_id="B__2", n_a=2, n_b=0, extras=dict(NO_HEARINGS)),
                packet(pair_id="A__1", n_a=2, n_b=0, extras=dict(NO_HEARINGS))]
        self.assertEqual([p["pair_id"] for p in bg.most_evidenced(rows, 2)], ["A__1", "B__2"])

    def test_a_worker_exception_fails_one_item_not_the_whole_pass(self):
        rows = [packet(pair_id="A__1", n_a=1, n_b=1, extras=dict(NO_HEARINGS)),
                packet(pair_id="B__2", n_a=1, n_b=1, extras=dict(NO_HEARINGS)),
                packet(pair_id="C__3", n_a=1, n_b=1, extras=dict(NO_HEARINGS))]
        client = ScriptedClient(explode=["B__2"])
        with tempfile.TemporaryDirectory() as tmp:
            result = bg.run_pairs(rows, client, "SYSTEM", tmp, concurrency=2,
                                  log=lambda *_a: None)
        by_id = {r["pair_id"]: r for r in result["raw"]["A"]}
        self.assertEqual(sorted(by_id), ["A__1", "B__2", "C__3"])
        self.assertTrue(by_id["A__1"]["ok"])
        self.assertTrue(by_id["C__3"]["ok"])
        self.assertFalse(by_id["B__2"]["ok"])
        self.assertIn("worker_exception", by_id["B__2"]["error"])

    def test_label_summary_counts_both_row_kinds(self):
        packets = {"p1": packet(pair_id="p1", n_a=2, n_b=1, extras=dict(NO_HEARINGS))}
        merged = bg.merge_labels(packets, {"p1": graded("2")}, {"p1": graded("2")}, {})
        rows = merged + [bg.no_evidence_label_row(empty_packet("p2"), {})]
        summary = bg.label_summary(rows)
        self.assertEqual(summary["rows"], 2)
        self.assertEqual(summary["by_graded_via"], {"api": 1, "no_evidence_short_circuit": 1})
        self.assertEqual(summary["by_label_status"][bg.NO_EVIDENCE_LABEL_STATUS], 1)
        affinity_ab = summary["assessability"]["affinity"]["a_to_b"]
        self.assertEqual(affinity_ab["assessable"], 1)
        self.assertEqual(affinity_ab["unassessable"], 1)
        # friction is unassessable in the graded row too, and in both no-evidence
        # directions, so all four direction-slots read unassessable
        self.assertEqual(summary["assessability"]["friction"]["a_to_b"]["unassessable"], 2)
        self.assertEqual(summary["observation_coverage"]["none"], 1)
        self.assertEqual(summary["neutral_assessment"]["unknown"], 2)

    def test_label_summary_marks_a_blocked_merge_as_awaiting_adjudication(self):
        packets = {"p1": packet(pair_id="p1", n_a=2, n_b=1, extras=dict(NO_HEARINGS))}
        merged = bg.merge_labels(packets, {"p1": graded("4")}, {"p1": graded("0")}, {})
        summary = bg.label_summary(merged)
        self.assertEqual(summary["assessability"]["affinity"]["a_to_b"]["adjudication_pending"], 1)
        self.assertEqual(summary["pairs_needing_adjudication"], 1)

    def test_no_evidence_and_merged_rows_never_cover_the_same_pair(self):
        rows = [empty_packet("A__1"), packet(pair_id="B__2", n_a=2, n_b=1, extras=dict(NO_HEARINGS))]
        gradable, empty = bg.partition_by_evidence(rows)
        merged = bg.merge_labels({p["pair_id"]: p for p in gradable},
                                 {"B__2": graded("1")}, {"B__2": graded("1")}, {})
        synthetic = [bg.no_evidence_label_row(p, {}) for p in empty]
        self.assertFalse({r["pair_id"] for r in merged} & {r["pair_id"] for r in synthetic})
        self.assertEqual(len(merged) + len(synthetic), len(rows))

    def test_queue_states_the_no_evidence_denominator(self):
        a = {"p1": graded("4")}
        b = {"p1": graded("0")}
        agreement = bg.pair_agreement(a, b)
        packets = {"p1": packet(pair_id="p1", n_a=2, n_b=1, extras=dict(NO_HEARINGS))}
        merged = bg.merge_labels(packets, a, b, {})
        text = bg.adjudication_queue_markdown(agreement, merged, packets, a, b,
                                              {"no_evidence_pairs": 133, "pairs_total": 180})
        self.assertIn("133 of the 180 pairs", text)
        self.assertIn("no_evidence", text)

    def test_report_states_the_two_denominators(self):
        a = {"p1": graded("2")}
        b = {"p1": graded("2")}
        agreement = bg.pair_agreement(a, b)
        receipt = {"run_id": "r", "started_utc": "t", "model": "claude-sonnet-5",
                   "effort": "medium", "max_tokens": 4000, "api_path": "fake",
                   "rubric_sha256": "abc",
                   "counts": {"pairs_total": 180, "pairs_with_evidence_sent_to_api": 47,
                              "pairs_no_evidence_deterministic_rows": 133,
                              "api_calls_avoided_by_no_evidence": 266, "api_calls": 94},
                   "usage_total": {"input_tokens": 1, "output_tokens": 1,
                                   "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
                   "estimated_cost_usd": 0.01, "failures": []}
        text = bg.build_report(receipt, agreement)
        self.assertIn("133 carried none at all", text)
        self.assertIn("266 calls not made", text)
        self.assertIn("API-graded pairs only", text)


class PromptHonestyTests(unittest.TestCase):
    def test_supplied_and_recorded_turns_are_stated_separately(self):
        """mention_total counts turns, the excerpts are per-occurrence, so
        supplied can exceed it. The prompt must not render '5 of 3'."""
        row = packet(n_a=5, n_b=0, extras=dict(NO_HEARINGS))
        row["directions"]["a_to_b"]["mention_total"] = 3
        _, rendered = bg.pair_prompt(row, "A")
        self.assertIn("excerpts supplied: 5; distinct turns recorded in this direction: 3",
                      rendered)
        self.assertNotIn("5 (of 3", rendered)

    def test_an_empty_direction_still_says_so(self):
        row = packet(n_a=2, n_b=0, extras=dict(NO_HEARINGS))
        _, rendered = bg.pair_prompt(row, "A")
        self.assertIn("(no encounters supplied for this direction)", rendered)


# ---------------------------------------------------------------------------
# subagent file transport (--transport subagent_files): grading performed by
# independent Claude Code subagents reading exported prompts, offline, while
# the Anthropic key has no credit.
# ---------------------------------------------------------------------------

class TransportConstantsTests(unittest.TestCase):
    def test_cli_selector_and_recorded_label_are_deliberately_different_strings(self):
        """The documented contract is the CLI flag `--transport subagent_files`
        but a row/receipt records `transport='claude_code_subagent'` once that
        transport is used -- two different strings for two different jobs
        (selecting the transport vs. labelling what happened). A regression
        that collapses them back into one constant would silently break the
        exact CLI syntax the offline grading run-book depends on."""
        self.assertEqual(bg.TRANSPORT_SUBAGENT_FILES, "subagent_files")
        self.assertEqual(bg.TRANSPORT_LABEL_SUBAGENT_FILES, "claude_code_subagent")
        self.assertNotEqual(bg.TRANSPORT_SUBAGENT_FILES, bg.TRANSPORT_LABEL_SUBAGENT_FILES)
        self.assertEqual(bg.SubagentFileClient.transport, bg.TRANSPORT_LABEL_SUBAGENT_FILES)
        self.assertEqual(bg.GradingClient.transport, bg.TRANSPORT_API)


class SubagentFileTransportTests(unittest.TestCase):
    def _pair_prompt(self, row=None, pass_tag="A"):
        row = row or packet()
        _, rendered = bg.pair_prompt(row, pass_tag)
        return row, rendered

    def test_reads_and_validates_a_well_formed_response(self):
        row, rendered = self._pair_prompt()
        with tempfile.TemporaryDirectory() as tmp:
            resp_dir = Path(tmp) / "A"
            resp_dir.mkdir()
            (resp_dir / ("%s.json" % row["pair_id"])).write_text(json.dumps(wire_grade()),
                                                                  encoding="utf-8")
            client = bg.SubagentFileClient(tmp)
            out = client.call("SYSTEM", rendered, bg.pair_grade_schema())
        self.assertTrue(out["ok"])
        self.assertIsNone(out["usage"])
        self.assertEqual(out["data"]["neutral_assessment"], "unknown")
        self.assertEqual(client.transport, bg.TRANSPORT_LABEL_SUBAGENT_FILES)

    def test_malformed_response_is_rejected_and_an_error_file_is_written(self):
        row, rendered = self._pair_prompt()
        bad = wire_grade()
        bad["confidence"] = "extremely"  # not in CONFIDENCE_VALUES -> schema_invalid
        with tempfile.TemporaryDirectory() as tmp:
            resp_dir = Path(tmp) / "A"
            resp_dir.mkdir()
            (resp_dir / ("%s.json" % row["pair_id"])).write_text(json.dumps(bad),
                                                                  encoding="utf-8")
            client = bg.SubagentFileClient(tmp)
            out = client.call("SYSTEM", rendered, bg.pair_grade_schema())
            error_path = resp_dir / ("%s.error.txt" % row["pair_id"])
            self.assertTrue(error_path.exists())
            self.assertIn("confidence", error_path.read_text(encoding="utf-8"))
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "schema_invalid")
        self.assertIsNone(out["usage"])

    def test_unparseable_json_response_is_rejected_with_an_error_file(self):
        row, rendered = self._pair_prompt()
        with tempfile.TemporaryDirectory() as tmp:
            resp_dir = Path(tmp) / "A"
            resp_dir.mkdir()
            (resp_dir / ("%s.json" % row["pair_id"])).write_text("not json at all",
                                                                  encoding="utf-8")
            client = bg.SubagentFileClient(tmp)
            out = client.call("SYSTEM", rendered, bg.pair_grade_schema())
            self.assertTrue((resp_dir / ("%s.error.txt" % row["pair_id"])).exists())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "unparseable_json")

    def test_missing_response_file_is_a_failure_not_a_crash(self):
        row, rendered = self._pair_prompt()
        with tempfile.TemporaryDirectory() as tmp:
            client = bg.SubagentFileClient(tmp)  # nothing written for this item at all
            out = client.call("SYSTEM", rendered, bg.pair_grade_schema())
            error_path = Path(tmp) / "A" / ("%s.error.txt" % row["pair_id"])
            self.assertFalse(error_path.exists())
        self.assertFalse(out["ok"])
        self.assertEqual(out["error"], "response_file_missing")
        self.assertIsNone(out["usage"])
        self.assertEqual(out["data"], None)

    def test_calibration_items_are_identified_by_their_mention_header(self):
        row = calib_row("cal-xyz")
        _, rendered = bg.calibration_prompt(row, "B")
        with tempfile.TemporaryDirectory() as tmp:
            resp_dir = Path(tmp) / "B"
            resp_dir.mkdir()
            (resp_dir / "cal-xyz.json").write_text(json.dumps(review()), encoding="utf-8")
            client = bg.SubagentFileClient(tmp)
            out = client.call("SYSTEM", rendered, bg.calibration_schema())
        self.assertTrue(out["ok"])

    def test_a_missing_item_does_not_crash_run_pairs_and_is_counted_as_a_failure(self):
        rows = [packet(pair_id="A__1", n_a=1, n_b=1, extras=dict(NO_HEARINGS)),
                packet(pair_id="B__2", n_a=1, n_b=1, extras=dict(NO_HEARINGS))]
        with tempfile.TemporaryDirectory() as tmp:
            responses_dir = Path(tmp) / "responses"
            (responses_dir / "A").mkdir(parents=True)
            (responses_dir / "B").mkdir(parents=True)
            for pass_tag in ("A", "B"):  # only A__1 gets a response; B__2 stays missing
                (responses_dir / pass_tag / "A__1.json").write_text(json.dumps(wire_grade()),
                                                                     encoding="utf-8")
            client = bg.SubagentFileClient(responses_dir)
            result = bg.run_pairs(rows, client, "SYSTEM", Path(tmp) / "out", concurrency=2,
                                  log=lambda *_a: None)
        by_id = {r["pair_id"]: r for r in result["raw"]["A"]}
        self.assertTrue(by_id["A__1"]["ok"])
        self.assertFalse(by_id["B__2"]["ok"])
        self.assertEqual(by_id["B__2"]["error"], "response_file_missing")
        self.assertIsNone(by_id["B__2"]["usage"])
        self.assertEqual(by_id["A__1"]["transport"], bg.TRANSPORT_LABEL_SUBAGENT_FILES)
        self.assertIn("B__2", {f["pair_id"] for f in result["failures"]})


# ---------------------------------------------------------------------------
# --export-prompts: the self-contained offline grading kit
# ---------------------------------------------------------------------------

class ExportPromptsTests(unittest.TestCase):
    def _write_ndjson(self, rows):
        handle = tempfile.NamedTemporaryFile("w", suffix=".ndjson", delete=False, encoding="utf-8")
        for row in rows:
            handle.write(json.dumps(row) + "\n")
        handle.close()
        self.addCleanup(lambda: Path(handle.name).unlink(missing_ok=True))
        return handle.name

    def test_index_excludes_no_evidence_pairs_and_includes_both_passes(self):
        packets_path = self._write_ndjson([packet(pair_id="EVIDENCED__1", n_a=2, n_b=1),
                                           empty_packet("EMPTY__2")])
        calib_path = self._write_ndjson([calib_row("cal-1"), calib_row("cal-2")])
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "kit"
            result = bg.export_prompt_kit(out_dir, packets_path, calib_path, "RUBRIC TEXT",
                                          log=lambda *_a: None)
            index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
            for it in index["items"]:
                self.assertTrue(Path(it["prompt_path"]).exists())
                text = Path(it["prompt_path"]).read_text(encoding="utf-8")
                self.assertIn(bg.PROMPT_KIT_USER_HEADER, text)
                self.assertTrue(text.startswith(bg.PROMPT_KIT_SYSTEM_HEADER))

        pair_items = [it for it in index["items"] if it["phase"] == "pairs"]
        pair_ids = {it["item_id"] for it in pair_items}
        self.assertEqual(pair_ids, {"EVIDENCED__1"})
        self.assertNotIn("EMPTY__2", pair_ids)
        self.assertEqual(sorted(it["pass"] for it in pair_items), ["A", "B"])

        calib_items = [it for it in index["items"] if it["phase"] == "calibration"]
        self.assertEqual({it["item_id"] for it in calib_items}, {"cal-1", "cal-2"})
        for mid in ("cal-1", "cal-2"):
            self.assertEqual(sorted(it["pass"] for it in calib_items if it["item_id"] == mid),
                             ["A", "B"])

        self.assertEqual(index["meta"]["pairs_total"], 2)
        self.assertEqual(index["meta"]["pairs_with_evidence"], 1)
        self.assertEqual(index["meta"]["pairs_no_evidence_excluded"], 1)
        self.assertEqual(index["meta"]["no_evidence_pair_ids"], ["EMPTY__2"])
        self.assertEqual(index["meta"]["calibration_total"], 2)
        self.assertEqual(index["meta"]["items_total"], 6)  # 1 pair x2 passes + 2 calib x2 passes
        self.assertEqual(result["meta"]["items_total"], 6)

    def test_response_path_naming_is_stable_and_matches_what_the_transport_reads(self):
        packets_path = self._write_ndjson([packet(pair_id="STABLE__1", n_a=1, n_b=1)])
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "kit"
            bg.export_prompt_kit(out_dir, packets_path, "does-not-exist.ndjson", "RUBRIC TEXT",
                                 log=lambda *_a: None)
            index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
            item_a = next(it for it in index["items"] if it["pass"] == "A")
            # export_prompt_kit resolves out_dir to an absolute path (a "self
            # contained" kit's recorded paths must not depend on the caller's
            # cwd at export time), so the expected path is resolved the same way.
            expected = str(out_dir.resolve() / "responses" / "A" / "STABLE__1.json")
            self.assertEqual(item_a["response_path"], expected)

            # Write exactly that response, then confirm SubagentFileClient finds
            # it using only the identity parsed out of the SAME exported prompt --
            # the responses dir is derived from the recorded response_path itself,
            # not re-built from this test's own (unresolved) out_dir variable.
            response_path = Path(item_a["response_path"])
            response_path.write_text(json.dumps(wire_grade()), encoding="utf-8")
            rendered_full = Path(item_a["prompt_path"]).read_text(encoding="utf-8")
            user_only = rendered_full.split(bg.PROMPT_KIT_USER_HEADER, 1)[1]
            client = bg.SubagentFileClient(response_path.parents[1])
            out = client.call("SYSTEM", user_only, bg.pair_grade_schema())
        self.assertTrue(out["ok"])

    def test_export_is_deterministic_across_repeated_runs(self):
        packets_path = self._write_ndjson([packet(pair_id="P__1", n_a=1, n_b=0,
                                                   extras=dict(NO_HEARINGS))])
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "kit"
            bg.export_prompt_kit(out_dir, packets_path, "missing.ndjson", "RUBRIC TEXT",
                                 log=lambda *_a: None)
            first_index = (out_dir / "index.json").read_text(encoding="utf-8")
            first_batches = (out_dir / "batches.json").read_text(encoding="utf-8")
            bg.export_prompt_kit(out_dir, packets_path, "missing.ndjson", "RUBRIC TEXT",
                                 log=lambda *_a: None)
            second_index = (out_dir / "index.json").read_text(encoding="utf-8")
            second_batches = (out_dir / "batches.json").read_text(encoding="utf-8")
        self.assertEqual(first_index, second_index)
        self.assertEqual(first_batches, second_batches)

    def test_batches_respect_the_size_caps_and_cover_every_item_exactly_once(self):
        rows = [packet(pair_id="P%02d__Q" % i, n_a=1, n_b=0, extras=dict(NO_HEARINGS))
                for i in range(20)]
        packets_path = self._write_ndjson(rows)
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "kit"
            bg.export_prompt_kit(out_dir, packets_path, "missing.ndjson", "RUBRIC TEXT",
                                 log=lambda *_a: None)
            batches = json.loads((out_dir / "batches.json").read_text(encoding="utf-8"))
            index = json.loads((out_dir / "index.json").read_text(encoding="utf-8"))
        pair_batches = [b for b in batches["batches"] if b["phase"] == "pairs"]
        for b in pair_batches:
            self.assertLessEqual(b["item_count"], bg.PAIR_KIT_BATCH_MAX)
        # 20 pairs x 2 passes; ceil(20/16) == 2 batches per pass -> 4 pair batches total
        self.assertEqual(len(pair_batches), 4)
        covered = sorted((b["phase"], b["pass"], it["item_id"])
                         for b in batches["batches"] for it in b["items"])
        expected = sorted((it["phase"], it["pass"], it["item_id"]) for it in index["items"])
        self.assertEqual(covered, expected)

    def test_missing_input_files_export_nothing_for_that_phase_without_crashing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "kit"
            result = bg.export_prompt_kit(out_dir, "no-such-packets.ndjson",
                                          "no-such-calibration.ndjson", "RUBRIC TEXT",
                                          log=lambda *_a: None)
        self.assertEqual(result["meta"]["items_total"], 0)
        self.assertEqual(result["batch_count"], 0)


if __name__ == "__main__":
    unittest.main()
