"""Independent behavior tests for the isolated PEV candidate.

These synthetic cases encode the agreed observation and ordering contracts.
They never import the production Moneyball package or read production artifacts.
"""
from copy import deepcopy
from pathlib import Path
from itertools import permutations
import json
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pev import Policy, compute_metrics, percentiles, rank_members, wilson_lower


BIO = "A000001"
MID = "118:hr:100"
STAGES = ("AIC", "ABC", "PASS", "LAW")


def bill(mid=MID, intro="2023-01-10", events=None, congress=118):
    milestones = {
        "BILL": {"state": "observed", "reached": True, "date": intro},
        **{s: {"state": "observed", "reached": False, "date": None}
           for s in STAGES},
    }
    for stage, when in (events or {}).items():
        milestones[stage] = {"state": "observed", "reached": True, "date": when}
    return {"measure_id": mid, "congress": congress, "chamber": "House",
            "measure_type": "hr", "eligible": True, "introduced_date": intro,
            "milestones": milestones, "as_of": "2024-12-31"}


def role(mid=MID, joined="2023-01-10", *, kind="sponsor", withdrawn=None,
         bio=BIO, chronology="verified"):
    return {"measure_id": mid, "bioguide_id": bio, "role": kind,
            "joined_date": joined, "withdrawn_date": withdrawn,
            "introduced_date": "2023-01-10", "chronology_status": chronology}


def signal(mid=MID, value=1.0, *, bio=BIO, accepted=True, category="CU Tax Status"):
    return {"measure_id": mid, "bioguide_id": bio, "accepted": accepted,
            "tensor_cu": value, "standard_direction": 1,
            "category": category}


def person(bio=BIO, periods=None):
    periods = periods if periods is not None else [
        {"start": "2023-01-03", "end": "2025-01-03"}]
    return {"bioguide_id": bio, "congress": 118, "chamber": "House",
            "name": "Synthetic Member", "service_periods": periods,
            "service_start": min((p["start"] for p in periods), default=None),
            "service_end": max((p["end"] for p in periods), default=None),
            "coverage_status": "dated_service_reconciled"}


def evaluate(bills=None, roles=None, signals=None, roster=None,
             as_of="2024-12-31", policy=None):
    result = compute_metrics(
        bills if bills is not None else [bill()],
        roles if roles is not None else [role()],
        signals if signals is not None else [signal()],
        roster if roster is not None else [person()],
        congress=118, as_of=as_of, policy=policy or Policy())
    return result["members"][BIO + "|house"]


class WilsonTests(unittest.TestCase):
    def test_reference_binomial_result(self):
        self.assertAlmostEqual(wilson_lower(8, 10), 0.49015684672072335, places=12)
        self.assertEqual(wilson_lower(0, 10), 0.0)
        self.assertGreater(wilson_lower(8, 10), wilson_lower(1, 1))

    def test_no_observations_is_undefined(self):
        self.assertIsNone(wilson_lower(0, 0))

    def test_invalid_counts_and_uncertainty_parameters_rejected(self):
        for successes, attempts, z in [(-1, 2, 1.96), (3, 2, 1.96),
                                        (0, -1, 1.96), (0.5, 2, 1.96),
                                        (1, 2.5, 1.96), (1, 2, -1),
                                        (1, 2, math.nan), (1, 2, math.inf)]:
            with self.subTest(successes=successes, attempts=attempts, z=z):
                with self.assertRaises(ValueError):
                    wilson_lower(successes, attempts, z=z)


class ObservationTests(unittest.TestCase):
    def test_mature_attempt_without_progress_is_observed_failure(self):
        m = evaluate()
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 0))
        self.assertEqual(m["efficiency_raw"], 0.0)
        self.assertEqual(m["efficiency_score"], 0.0)

    def test_observed_advancement_is_one_conversion(self):
        m = evaluate([bill(events={"AIC": "2023-03-01", "ABC": "2023-04-01",
                                   "PASS": "2023-05-01", "LAW": "2023-06-01"})])
        self.assertEqual((m["useful_volume"], m["eligible_attempts"], m["successes"]),
                         (1, 1, 1))
        self.assertEqual(m["efficiency_raw"], 1.0)
        self.assertAlmostEqual(m["efficiency_score"], wilson_lower(1, 1))
        self.assertEqual(m["stages"]["LAW"]["successes"], 1)

    def test_progress_after_horizon_does_not_count(self):
        m = evaluate([bill(events={"AIC": "2023-07-10"})])
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 0))

    def test_progress_on_horizon_endpoint_counts(self):
        # January 10 plus 180 days is July 9, 2023.
        m = evaluate([bill(events={"LAW": "2023-07-09"})])
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 1))

    def test_immature_success_and_unresolved_attempt_are_both_excluded(self):
        other = "118:hr:101"
        m = evaluate([bill(events={"AIC": "2023-01-20"}), bill(other)],
                     [role(), role(other)], [signal(), signal(other)],
                     as_of="2023-02-01")
        self.assertEqual(m["useful_volume"], 2)
        self.assertEqual((m["eligible_attempts"], m["successes"]), (0, 0))
        self.assertIsNone(m["efficiency_score"])
        self.assertTrue(m["coverage"])

    def test_late_term_attempt_cannot_borrow_next_congress_observation(self):
        b = bill(intro="2024-12-01", events={"PASS": "2024-12-15"})
        r = role(joined="2024-12-01")
        r["introduced_date"] = "2024-12-01"
        m = evaluate([b], [r], as_of="2026-01-01")
        self.assertEqual(m["eligible_attempts"], 0)
        self.assertIsNone(m["efficiency_score"])

    def test_service_must_cover_full_window(self):
        m = evaluate(roster=[person(periods=[{"start": "2023-01-03",
                                             "end": "2023-04-01"}])])
        self.assertEqual(m["eligible_attempts"], 0)
        self.assertIsNone(m["efficiency_score"])

    def test_service_gap_cannot_be_bridged_by_minimum_and_maximum_dates(self):
        m = evaluate(roster=[person(periods=[
            {"start": "2023-01-03", "end": "2023-02-01"},
            {"start": "2023-03-01", "end": "2025-01-03"}])])
        self.assertEqual(m["eligible_attempts"], 0)

    def test_withdrawal_retains_denominator_and_blocks_later_credit(self):
        m = evaluate([bill(events={"AIC": "2023-03-01"})],
                     [role(kind="cosponsor", withdrawn="2023-02-01")])
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 0))

    def test_same_day_withdrawal_is_exclusive(self):
        m = evaluate([bill(events={"AIC": "2023-03-01"})],
                     [role(kind="cosponsor", withdrawn="2023-03-01")])
        self.assertEqual(m["successes"], 0)

    def test_rejoining_does_not_restart_horizon_or_duplicate_attempt(self):
        roles = [role(kind="cosponsor", withdrawn="2023-02-01"),
                 role(joined="2023-05-01", kind="cosponsor")]
        m = evaluate([bill(events={"AIC": "2023-08-01"})], roles)
        self.assertEqual((m["eligible_attempts"], m["successes"], m["useful_volume"]),
                         (1, 0, 1))

    def test_rejoined_active_episode_can_earn_progress_in_original_window(self):
        roles = [role(kind="cosponsor", withdrawn="2023-02-01"),
                 role(joined="2023-05-01", kind="cosponsor")]
        m = evaluate([bill(events={"AIC": "2023-06-01"})], roles)
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 1))

    def test_only_stage_higher_than_prejoin_maximum_is_progress(self):
        r = role(joined="2023-03-01", kind="cosponsor")
        events = {"PASS": "2023-02-01", "AIC": "2023-04-01"}
        m = evaluate([bill(events=events)], [r])
        self.assertEqual(m["successes"], 0)
        self.assertEqual(m["stages"]["PASS"]["attempts"], 0)
        events["LAW"] = "2023-05-01"
        m = evaluate([bill(events=events)], [r])
        self.assertEqual(m["successes"], 1)

    def test_law_before_join_leaves_no_advancement_opportunity(self):
        m = evaluate([bill(events={"LAW": "2023-02-01"})],
                     [role(joined="2023-03-01", kind="cosponsor")])
        self.assertEqual(m["eligible_attempts"], 0)
        self.assertIsNone(m["efficiency_score"])

    def test_same_day_join_and_milestone_is_inclusive(self):
        m = evaluate([bill(events={"AIC": "2023-01-10"})])
        self.assertEqual(m["successes"], 1)

    def test_unknown_milestone_makes_efficiency_partial_unknown(self):
        b = bill()
        b["milestones"]["AIC"] = {"state": "unknown", "reached": None,
                                      "date": None}
        m = evaluate([b])
        self.assertIsNone(m["efficiency_score"])
        self.assertEqual(m["efficiency_status"], "partial_unknown")

    def test_unknown_signal_is_not_neutral_or_a_measured_failure(self):
        other = "118:hr:101"
        m = evaluate([bill(events={"AIC": "2023-02-01"}), bill(other)],
                     [role(), role(other)], [signal(), signal(other, None)])
        self.assertEqual((m["useful_volume"], m["unknown_volume"], m["neutral_volume"]),
                         (1, 1, 0))
        self.assertIsNone(m["efficiency_score"])
        self.assertEqual(m["efficiency_status"], "partial_unknown")

    def test_conflicting_signs_are_unknown_even_when_one_is_positive(self):
        m = evaluate(signals=[signal(value=1), signal(value=-1)])
        self.assertEqual((m["useful_volume"], m["harmful_volume"], m["unknown_volume"]),
                         (0, 0, 1))
        self.assertIsNone(m["efficiency_score"])

    def test_harmful_and_neutral_activity_never_add_useful_volume(self):
        negative, neutral = "118:hr:101", "118:hr:102"
        m = evaluate([bill(), bill(negative), bill(neutral)],
                     [role(), role(negative), role(neutral)],
                     [signal(), signal(negative, -1), signal(neutral, 0)])
        self.assertEqual((m["useful_volume"], m["harmful_volume"], m["neutral_volume"]),
                         (1, 1, 1))
        self.assertEqual(m["eligible_attempts"], 1)

    def test_duplicate_categories_roles_and_identical_bills_collapse(self):
        b, r, s = bill(events={"AIC": "2023-03-01"}), role(), signal()
        m = evaluate([b, deepcopy(b)], [r, deepcopy(r)],
                     [s, deepcopy(s), signal(category="Lending")])
        self.assertEqual((m["useful_volume"], m["eligible_attempts"], m["successes"]),
                         (1, 1, 1))

    def test_conflicting_bill_records_raise(self):
        a, b = bill(), bill(events={"LAW": "2023-03-01"})
        with self.assertRaises(ValueError):
            evaluate([a, b])

    def test_unaccepted_other_member_and_other_congress_are_out_of_scope(self):
        other, old = "118:hr:101", "117:hr:100"
        m = evaluate([bill(), bill(other), bill(old, congress=117)],
                     [role(), role(other), role(old)],
                     [signal(accepted=False), signal(other, bio="B000002"), signal(old)])
        self.assertEqual(m["useful_volume"], 0)
        self.assertEqual(m["eligible_attempts"], 0)

    def test_inconsistent_sponsor_join_is_quarantined(self):
        m = evaluate(roles=[role(joined="2023-02-01", kind="sponsor")])
        self.assertEqual(m["eligible_attempts"], 0)
        self.assertIsNone(m["efficiency_score"])
        self.assertEqual(m["efficiency_status"], "partial_unknown")


class OrderingTests(unittest.TestCase):
    @staticmethod
    def row(bio, p, e, volume=1, name="Synthetic Member"):
        return {"bioguide_id": bio, "name": name, "P": p,
                "efficiency_score": e, "useful_volume": volume}

    def test_primacy_cannot_be_bought_with_efficiency_or_volume(self):
        rows = [self.row("B", .60, 1.0, 1000), self.row("A", .61, None, 0)]
        ranked = rank_members(rows)
        self.assertEqual([r["bioguide_id"] for r in ranked], ["A", "B"])
        self.assertEqual([r["candidate_rank"] for r in ranked], [1, 2])

    def test_efficiency_precedes_volume_at_equal_primacy(self):
        ranked = rank_members([self.row("B", .6, .60, 1000),
                               self.row("A", .6, .61, 1)])
        self.assertEqual([r["bioguide_id"] for r in ranked], ["A", "B"])
        ranked = rank_members([self.row("A", .6, .61, 1),
                               self.row("B", .6, .61, 2)])
        self.assertEqual([r["bioguide_id"] for r in ranked], ["B", "A"])

    def test_missing_efficiency_is_not_zero_and_volume_cannot_rescue_it(self):
        ranked = rank_members([self.row("C", .6, None, 1000),
                               self.row("B", .6, 0.0, 0),
                               self.row("A", .6, None, 1)])
        self.assertEqual([r["bioguide_id"] for r in ranked], ["B", "A", "C"])

    def test_identity_breaks_complete_ties_independently_of_name(self):
        rows = [self.row("B", .6, .7, name="Aaron"),
                self.row("A", .6, .7, name="Zelda")]
        original = deepcopy(rows)
        ranked = rank_members(rows)
        self.assertEqual([r["bioguide_id"] for r in ranked], ["A", "B"])
        self.assertEqual(rows, original, "Ranking must not mutate caller-owned rows")


class RegressionTests(unittest.TestCase):
    def test_numeric_milestone_boolean_is_unknown_not_a_failure(self):
        b = bill(events={"AIC": "2023-03-01"})
        b["milestones"]["AIC"]["reached"] = 1
        m = evaluate([b])
        self.assertEqual(m["efficiency_status"], "partial_unknown")
        self.assertIsNone(m["efficiency_score"])
        self.assertEqual(m["eligible_attempts"], 0)

    def test_string_bill_eligibility_is_unknown_and_never_rewarded(self):
        b = bill()
        b["eligible"] = "false"
        result = compute_metrics([b], [role()], [signal()], [person()],
                                 congress=118, as_of="2024-12-31")
        m = result["members"][BIO + "|house"]
        self.assertEqual((m["useful_volume"], m["unknown_volume"]), (0, 1))
        self.assertIsNone(m["efficiency_score"])
        self.assertEqual(result["opportunities"][0]["status"], "invalid_bill_eligibility")

    def test_contradictory_withdrawal_dates_quarantine_role(self):
        for second_end in (None, "2023-04-01"):
            with self.subTest(second_end=second_end):
                roles = [role(kind="cosponsor", withdrawn="2023-02-01"),
                         role(kind="cosponsor", withdrawn=second_end)]
                m = evaluate([bill(events={"AIC": "2023-03-01"})], roles)
                self.assertEqual(m["efficiency_status"], "partial_unknown")
                self.assertEqual((m["useful_volume"], m["eligible_attempts"]), (0, 0))
                self.assertIsNone(m["efficiency_score"])

    def test_all_future_role_rows_are_future_participation_not_unknown(self):
        roles = [role(joined="2024-03-01", kind="cosponsor"),
                 role(joined="2024-04-01", kind="cosponsor")]
        m = evaluate(roles=roles, as_of="2023-12-31")
        self.assertEqual(m["coverage"].get("future_participation"), 1)
        self.assertEqual((m["unknown_volume"], m["useful_volume"]), (0, 0))
        self.assertNotEqual(m["efficiency_status"], "partial_unknown")

    def test_future_participation_does_not_poison_an_observed_record(self):
        other = "118:hr:101"
        m = evaluate([bill(events={"AIC": "2023-03-01"}), bill(other)],
                     [role(), role(other, joined="2024-03-01", kind="cosponsor")],
                     [signal(), signal(other)], as_of="2023-12-31")
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 1))
        self.assertEqual(m["coverage"].get("future_participation"), 1)
        self.assertEqual(m["unknown_volume"], 0)
        self.assertAlmostEqual(m["efficiency_score"], wilson_lower(1, 1))

    def test_future_episode_of_observed_measure_is_ignored(self):
        m = evaluate([bill(events={"AIC": "2023-03-01"})],
                     [role(), role(joined="2024-03-01", kind="cosponsor")],
                     as_of="2023-12-31")
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 1))
        self.assertNotEqual(m["efficiency_status"], "partial_unknown")

    def test_malformed_effective_date_is_unknown_alignment(self):
        s = signal()
        s["effective_date"] = "not-a-date"
        m = evaluate(signals=[s])
        self.assertEqual((m["unknown_volume"], m["useful_volume"]), (1, 0))
        self.assertEqual(m["efficiency_status"], "partial_unknown")
        self.assertIsNone(m["efficiency_score"])

    def test_stale_bill_snapshot_cannot_prove_a_mature_failure(self):
        b = bill()
        b["as_of"] = "2023-02-01"
        m = evaluate([b], as_of="2023-12-31")
        self.assertEqual(m["eligible_attempts"], 0)
        self.assertEqual(m["efficiency_status"], "partial_unknown")
        self.assertIsNone(m["efficiency_score"])

    def test_missing_or_malformed_snapshot_is_unknown(self):
        for snapshot in (None, "not-a-date"):
            with self.subTest(snapshot=snapshot):
                b = bill(events={"AIC": "2023-03-01"})
                b["as_of"] = snapshot
                m = evaluate([b])
                self.assertEqual(m["efficiency_status"], "partial_unknown")
                self.assertEqual(m["eligible_attempts"], 0)
                self.assertIsNone(m["efficiency_score"])

    def test_bill_snapshot_at_horizon_is_sufficient(self):
        b = bill(events={"AIC": "2023-07-09"})
        b["as_of"] = "2023-07-09"
        m = evaluate([b])
        self.assertEqual((m["eligible_attempts"], m["successes"]), (1, 1))
        self.assertIsNotNone(m["efficiency_score"])

    def test_percentile_convention_truncates_first_ties_and_excludes_unknowns(self):
        result = percentiles({"a": 0, "b": 1, "c": 2, "d": 3, "missing": None})
        self.assertEqual(result, {"a": 0.0, "b": .33333, "c": .66666, "d": 1.0})
        self.assertEqual(percentiles({"a": 0, "b": 1, "c": 1}),
                         {"a": 0.0, "b": .5, "c": .5})
        self.assertEqual(percentiles({"a": 5}), {"a": 0.0})

    def test_efficiency_normalization_uses_only_observed_same_chamber_peers(self):
        bills, roles, signals, roster = [], [], [], []
        for index, bio in enumerate((BIO, "B000002", "C000003", "D000004", "E000005")):
            senate = index == 4
            mid = f"118:{'s' if senate else 'hr'}:{100 + index}"
            b = bill(mid, events={"AIC": "2023-03-01"} if index in (1, 2, 4) else {})
            p = person(bio)
            if senate:
                b.update(chamber="Senate", measure_type="s")
                p["chamber"] = "Senate"
            bills.append(b)
            roles.append(role(mid, bio=bio))
            signals.append(signal(mid, value=None if index == 3 else 1, bio=bio))
            roster.append(p)
        members = compute_metrics(bills, roles, signals, roster, congress=118,
                                  as_of="2024-12-31")["members"]
        self.assertEqual(members[BIO + "|house"]["efficiency_percentile"], 0.0)
        self.assertEqual(members["B000002|house"]["efficiency_percentile"], .5)
        self.assertEqual(members["C000003|house"]["efficiency_percentile"], .5)
        self.assertEqual(members["B000002|house"]["efficiency_peer_count"], 3)
        self.assertIsNone(members["D000004|house"]["efficiency_percentile"])
        self.assertEqual(members["D000004|house"]["efficiency_peer_count"], 3)
        self.assertEqual(members["E000005|senate"]["efficiency_peer_count"], 1)
        self.assertEqual(members["E000005|senate"]["efficiency_percentile"], 0.0)

    def test_own_success_improves_score_and_added_failure_reduces_it(self):
        other, extra = "118:hr:101", "118:hr:102"
        first = bill(events={"AIC": "2023-03-01"})
        base = evaluate([first, bill(other)], [role(), role(other)],
                        [signal(), signal(other)])
        improved = evaluate([first, bill(other, events={"PASS": "2023-04-01"})],
                            [role(), role(other)], [signal(), signal(other)])
        expanded = evaluate([first, bill(other), bill(extra)],
                            [role(), role(other), role(extra)],
                            [signal(), signal(other), signal(extra)])
        self.assertGreater(improved["efficiency_score"], base["efficiency_score"])
        self.assertLess(expanded["efficiency_score"], base["efficiency_score"])
        self.assertGreater(expanded["useful_volume"], base["useful_volume"])

    def test_complete_output_is_independent_of_input_order(self):
        second, third = "118:hr:101", "118:hr:102"
        bills = [bill(events={"AIC": "2023-03-01"}), bill(second),
                 bill(third, events={"LAW": "2023-05-01"})]
        roles = [role(), role(second), role(third, bio="B000002")]
        signals = [signal(), signal(second), signal(third, bio="B000002")]
        roster = [person(), person("B000002")]
        expected = compute_metrics(bills, roles, signals, roster,
                                   congress=118, as_of="2024-12-31")
        expected_json = json.dumps(expected, sort_keys=True, separators=(",", ":"))
        for bs in permutations(bills):
            for rs in permutations(roles):
                for ss in permutations(signals):
                    for ps in permutations(roster):
                        actual = compute_metrics(bs, rs, ss, ps,
                                                 congress=118, as_of="2024-12-31")
                        self.assertEqual(actual, expected)
                        self.assertEqual(json.dumps(actual, sort_keys=True, separators=(",", ":")),
                                         expected_json)

    def test_invalid_bill_chamber_cannot_silently_drop_an_accepted_attempt(self):
        b = bill()
        b["chamber"] = "Housee"
        with self.assertRaises(ValueError):
            evaluate([b])

    def test_measure_kind_chamber_mismatch_raises(self):
        b = bill()
        b["chamber"] = "Senate"
        with self.assertRaises(ValueError):
            evaluate([b])

    def test_equivalent_integer_float_signs_have_identical_canonical_json(self):
        a, b = signal(value=1), signal(value=1.0, category="Lending")
        outputs = [compute_metrics([bill()], [role()], ss, [person()],
                                   congress=118, as_of="2024-12-31")
                   for ss in ((a, b), (b, a))]
        canonical = [json.dumps(out, sort_keys=True, separators=(",", ":"))
                     for out in outputs]
        self.assertEqual(canonical[0], canonical[1])
        self.assertEqual(outputs[0]["members"][BIO + "|house"]["useful_volume"], 1)
        self.assertIsInstance(outputs[0]["opportunities"][0]["tensor_cu"], float)


if __name__ == "__main__":
    unittest.main()
