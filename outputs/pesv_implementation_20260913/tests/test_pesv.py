"""Hand-derived contracts for the pure PESV candidate; entirely synthetic data."""
from copy import deepcopy
from itertools import permutations
import json
import math
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pesv import Policy, compute_metrics, percentiles, rank_members

BIO = "A000001"
MID = "118:hr:1"
STAGES = ("BILL", "AIC", "ABC", "PASS", "LAW")
DATES = dict(zip(STAGES, ("2023-01-10", "2023-02-01", "2023-03-01", "2023-08-01", "2023-12-01")))


def bill(mid=MID, through="LAW", **updates):
    reached = STAGES.index(through)
    out = {"measure_id": mid, "congress": 118, "chamber": "House", "measure_type": "hr",
           "eligible": True, "introduced_date": DATES["BILL"], "as_of": "2024-12-31",
           "milestones": {s: {"state": "observed", "reached": i <= reached,
                               "date": DATES[s] if i <= reached else None}
                          for i, s in enumerate(STAGES)}}
    out.update(updates)
    return out


def impact(mid=MID, weight=5, **updates):
    out = {"measure_id": mid, "weight": weight, "as_of": "2024-12-31",
           "coverage_status": "adjudicated", "class": {1: "C", 5: "S", 10: "SS"}.get(weight)}
    out.update(updates)
    return out


def person(bio=BIO, **updates):
    out = {"bioguide_id": bio, "congress": 118, "chamber": "House", "name": bio,
           "service_periods": [{"start": "2023-01-03", "end": "2025-01-03"}]}
    out.update(updates)
    return out


def role(mid=MID, bio=BIO, kind="sponsor", joined="2023-01-10", withdrawn=None, **updates):
    out = {"measure_id": mid, "bioguide_id": bio, "role": kind, "joined_date": joined,
           "withdrawn_date": withdrawn, "chronology_status": "verified"}
    out.update(updates)
    return out


def signal(mid=MID, bio=BIO, value=1, **updates):
    out = {"measure_id": mid, "bioguide_id": bio, "accepted": True, "tensor_cu": value,
           "category": "CU Tax Status"}
    out.update(updates)
    return out


def evaluate(bills=None, roles=None, signals=None, roster=None, impacts=None,
             as_of="2024-12-31", policy=None):
    return compute_metrics(bills if bills is not None else [bill()],
                           roles if roles is not None else [role()],
                           signals if signals is not None else [signal()],
                           roster if roster is not None else [person()],
                           impacts if impacts is not None else [impact()],
                           congress=118, as_of=as_of, policy=policy)


def member(result, bio=BIO, c="house"):
    return result["members"][bio + "|" + c]


class FiveStageTests(unittest.TestCase):
    def test_hand_math_uses_all_five_additive_full_chamber_denominators(self):
        bills = [bill(f"118:hr:{i+1}", through=STAGES[4-i]) for i in range(5)]
        roster = [person(f"A00000{i+1}") for i in range(5)]
        result = evaluate(bills=bills, roster=roster,
                          impacts=[impact(b["measure_id"]) for b in bills])
        self.assertEqual(result["terms"]["house"]["denominators"],
                         dict(zip(STAGES, (25, 20, 15, 10, 5))))
        self.assertAlmostEqual(member(result)["efficiency_raw"], 1/5 + 1/4 + 1/3 + 1/2 + 1)
        stages = {r["stage"]: r["contribution"] for r in result["contributions"] if r["kind"] == "stage"}
        self.assertAlmostEqual(stages["LAW"], 1.0)
        self.assertAlmostEqual(stages["BILL"], .2)

    def test_sponsor_reference_population_mean_is_one_when_every_bill_attributed(self):
        bills = [bill(f"118:hr:{i+1}", through=STAGES[4-i]) for i in range(5)]
        roster = [person(f"A00000{i+1}") for i in range(5)]
        roles = [role(b["measure_id"], p["bioguide_id"]) for b, p in zip(bills, roster)]
        signals = [signal(b["measure_id"], p["bioguide_id"]) for b, p in zip(bills, roster)]
        result = evaluate(bills, roles, signals, roster, [impact(b["measure_id"]) for b in bills])
        self.assertAlmostEqual(sum(m["efficiency_raw"] for m in result["members"].values())/5, 1)

    def test_unselected_bill_changes_denominator_without_becoming_selected_volume(self):
        baseline = evaluate()
        other = "118:hr:2"
        expanded = evaluate(bills=[bill(), bill(other, through="BILL")],
                            impacts=[impact(), impact(other)])
        self.assertAlmostEqual(member(baseline)["efficiency_raw"], 1.0)
        self.assertAlmostEqual(member(expanded)["efficiency_raw"], .9)
        self.assertEqual(member(expanded)["useful_volume"], 1)

    def test_impact_enters_once_and_rebuilds_stage_denominators(self):
        second, third = "118:hr:2", "118:hr:3"
        result = evaluate(bills=[bill(), bill(second, through="BILL"), bill(third, through="BILL")],
                          impacts=[impact(weight=10), impact(second, 5), impact(third, 1)])
        self.assertAlmostEqual(member(result)["efficiency_raw"], (10/16 + 4)/5)
        self.assertEqual(member(result)["substance_raw"], 10)
        self.assertEqual(member(result)["volume_raw"], 1)

    def test_tensor_roles_keep_one_half_and_quarter_credit(self):
        roster = [person(), person("B000002"), person("C000003")]
        roles = [role(), role(bio="B000002", kind="original"), role(bio="C000003", kind="cosponsor")]
        signals = [signal(bio=p["bioguide_id"]) for p in roster]
        result = evaluate(roles=roles, signals=signals, roster=roster)
        self.assertEqual([member(result, p["bioguide_id"])["efficiency_raw"] for p in roster],
                         [3., 1.5, .75])
        self.assertEqual([member(result, p["bioguide_id"])["volume_raw"] for p in roster],
                         [1., .5, .25])

    def test_half_life_applies_only_later_cosponsors_and_only_future_stages(self):
        # Exactly 180 days after introduction: .25 base credit * .5 time credit.
        result = evaluate(roles=[role(kind="cosponsor", joined="2023-07-09")])
        self.assertAlmostEqual(member(result)["volume_raw"], .125)
        self.assertAlmostEqual(member(result)["efficiency_raw"], .2*.125*2)
        credited = [r["stage"] for r in result["contributions"] if r["kind"] == "stage"]
        self.assertEqual(credited, ["PASS", "LAW"])
        faster = evaluate(roles=[role(kind="cosponsor", joined="2023-07-09")],
                          policy=Policy(cosponsor_half_life_days=90))
        self.assertAlmostEqual(member(faster)["volume_raw"], .0625)

    def test_scoring_date_does_not_age_existing_participation_credit(self):
        roles = [role(kind="cosponsor", joined="2023-04-10")]
        a, b = evaluate(roles=roles), evaluate(roles=roles, as_of="2024-06-01")
        self.assertEqual(member(a)["volume_raw"], member(b)["volume_raw"])
        self.assertEqual(member(a)["efficiency_raw"], member(b)["efficiency_raw"])

    def test_rejoin_neither_resets_delay_nor_duplicates_stages(self):
        roles = [role(kind="cosponsor", joined="2023-01-20", withdrawn="2023-02-01"),
                 role(kind="cosponsor", joined="2023-06-01")]
        result = evaluate(roles=roles)
        credit = .25 * 2**(-10/180)
        self.assertAlmostEqual(member(result)["volume_raw"], credit)
        self.assertAlmostEqual(member(result)["efficiency_raw"], .2*credit*2)
        self.assertEqual(member(result)["useful_volume"], 1)

    def test_same_day_join_inclusive_withdrawal_exclusive(self):
        joined = evaluate(roles=[role(kind="cosponsor", joined="2023-02-01")])
        self.assertEqual(member(joined)["stages"]["AIC"]["credited_measures"], 1)
        withdrawn = evaluate(roles=[role(withdrawn="2023-02-01")])
        self.assertEqual(member(withdrawn)["stages"]["AIC"]["credited_measures"], 0)
        self.assertAlmostEqual(member(withdrawn)["efficiency_raw"], .2)

    def test_positive_negative_and_zero_are_signed_results_not_absolute_rewards(self):
        for sign, expected in ((1, 1), (-1, -1), (0, 0)):
            with self.subTest(sign=sign):
                m = member(evaluate(signals=[signal(value=sign)]))
                self.assertAlmostEqual(m["efficiency_raw"], expected)
                self.assertEqual(m["volume_raw"], max(sign, 0))
                self.assertEqual(m["harmful_volume"], int(sign < 0))

    def test_future_milestones_are_not_credited_and_zero_denominator_is_unavailable(self):
        result = evaluate(as_of="2023-06-01")
        self.assertEqual(result["terms"]["house"]["denominators"]["LAW"], 0)
        self.assertIsNone(member(result)["efficiency_raw"])
        self.assertEqual(member(result)["volume_raw"], 1)

    def test_no_invented_preceding_milestones_from_law(self):
        b = bill()
        b["milestones"]["ABC"] = {"state": "observed", "reached": False, "date": None}
        result = evaluate(bills=[b])
        self.assertEqual(result["terms"]["house"]["denominators"]["ABC"], 0)
        self.assertIsNone(member(result)["efficiency_score"])


class SubstanceVolumeTests(unittest.TestCase):
    def test_substance_is_credit_weighted_mean_and_volume_has_no_impact_weight(self):
        other = "118:hr:2"
        result = evaluate(bills=[bill(), bill(other)], roles=[role(), role(other, kind="cosponsor")],
                          signals=[signal(), signal(other)], impacts=[impact(weight=10), impact(other, 1)])
        self.assertAlmostEqual(member(result)["substance_raw"], (10 + .25)/1.25)
        self.assertAlmostEqual(member(result)["volume_raw"], 1.25)
        self.assertEqual(member(result)["useful_volume"], 2)

    def test_uniform_provisional_five_is_exactly_nondiscriminating(self):
        bios = (BIO, "B000002", "C000003")
        result = evaluate(roles=[role(), role(bio=bios[1], kind="cosponsor", joined="2023-03-02"),
                                 role(bio=bios[2], kind="original")],
                          signals=[signal(bio=bio, value=.1) for bio in bios],
                          roster=[person(bio) for bio in bios],
                          impacts=[impact(coverage_status="provisional_cs_only")])
        self.assertEqual([member(result, bio)["substance_raw"] for bio in bios], [5., 5., 5.])
        self.assertEqual([member(result, bio)["substance_score"] for bio in bios], [0., 0., 0.])
        self.assertFalse(result["terms"]["house"]["substance_discriminating"])
        self.assertEqual(member(result)["substance_status"], "provisional_recorded_impact")

    def test_adding_same_importance_volume_does_not_raise_mean_substance(self):
        other = "118:hr:2"
        one = member(evaluate())
        two = member(evaluate(bills=[bill(), bill(other)], roles=[role(), role(other)],
                              signals=[signal(), signal(other)], impacts=[impact(), impact(other)]))
        self.assertEqual((one["substance_raw"], two["substance_raw"]), (5., 5.))
        self.assertEqual((one["volume_raw"], two["volume_raw"]), (1., 2.))

    def test_letter_receipt_has_no_fabricated_bill_or_participation(self):
        result = evaluate(signals=[signal(), signal("118:letter:LTR-X")])
        m = member(result)
        self.assertEqual(m["useful_volume"], 1)
        self.assertEqual(m["coverage"]["excluded_nonlaw_or_letter"], 1)


class IntegrityTests(unittest.TestCase):
    def test_unknown_unselected_measure_blocks_full_chamber_denominator(self):
        other = "118:hr:2"
        b = bill(other)
        b["milestones"]["ABC"] = {"state": "unknown", "reached": None, "date": None}
        result = evaluate(bills=[bill(), b], impacts=[impact(), impact(other)])
        self.assertFalse(result["terms"]["house"]["denominators_available"])
        self.assertIsNone(member(result)["efficiency_score"])
        self.assertEqual(member(result)["substance_raw"], 5.)

    def test_unknown_signal_and_missing_role_do_not_become_zero(self):
        cases = ({"signals": [signal(value=None)]}, {"roles": []},
                 {"signals": [signal(value=1), signal(value=-1)]})
        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                m = member(evaluate(**kwargs))
                self.assertIsNone(m["efficiency_raw"])
                self.assertIsNone(m["substance_raw"])
                self.assertIsNone(m["volume_raw"])
                self.assertEqual(m["unknown_volume"], 1)

    def test_incomplete_impact_is_never_invented_as_substantive_five(self):
        for impacts in ([], [impact(weight=True)], [impact(weight=7)]):
            with self.subTest(impacts=impacts):
                m = member(evaluate(impacts=impacts))
                self.assertIsNone(m["efficiency_raw"])
                self.assertIsNone(m["substance_raw"])
                self.assertEqual(m["volume_raw"], 1.)

    def test_invalid_stage_boolean_and_stale_snapshot_make_results_unavailable(self):
        for change in ("boolean", "snapshot"):
            b = bill()
            if change == "boolean":
                b["milestones"]["PASS"]["reached"] = 1
            else:
                b["as_of"] = "2023-02-01"
            with self.subTest(change=change):
                self.assertIsNone(member(evaluate(bills=[b]))["efficiency_raw"])

    def test_invalid_bill_eligibility_never_rewards_substance_or_volume(self):
        m = member(evaluate(bills=[bill(eligible="false")]))
        self.assertEqual(m["unknown_volume"], 1)
        self.assertEqual(m["useful_volume"], 0)
        self.assertIsNone(m["efficiency_raw"])
        self.assertIsNone(m["substance_raw"])
        self.assertIsNone(m["volume_raw"])

    def test_disagreeing_recorded_impact_class_and_weight_are_unknown(self):
        data = impact(weight=10)
        data["class"] = "C"
        m = member(evaluate(impacts=[data]))
        self.assertIsNone(m["efficiency_raw"])
        self.assertIsNone(m["substance_raw"])
        self.assertEqual(m["volume_raw"], 1.)

    def test_invalid_chronology_and_conflicting_withdrawals_quarantine(self):
        cases = ([role(joined="2023-02-01")],
                 [role(withdrawn="2023-02-01"), role(withdrawn="2023-03-01")],
                 [role(chronology_status="quarantined")])
        for roles in cases:
            with self.subTest(roles=roles):
                self.assertEqual(member(evaluate(roles=roles))["efficiency_status"], "partial_unknown")

    def test_official_role_continues_to_attribute_after_service_exit(self):
        result = evaluate(roster=[person(service_periods=[{"start": "2023-01-03", "end": "2023-02-01"}])])
        self.assertAlmostEqual(member(result)["efficiency_raw"], 1.)
        self.assertEqual(member(result)["stages"]["LAW"]["credited_measures"], 1)

    def test_join_outside_verified_service_remains_quarantined(self):
        result = evaluate(roster=[person(service_periods=[{"start": "2023-02-01", "end": "2025-01-03"}])])
        self.assertEqual(member(result)["efficiency_status"], "partial_unknown")
        self.assertEqual(member(result)["unknown_volume"], 1)

    def test_official_pre_introduction_hearing_enters_denominator_without_member_credit(self):
        b = bill()
        b["milestones"]["AIC"]["date"] = "2023-01-05"
        result = evaluate(bills=[b])
        term = result["terms"]["house"]
        self.assertTrue(term["denominators_available"])
        self.assertEqual(term["denominators"]["AIC"], 5)
        self.assertEqual(term["coverage"]["pre_introduction_AIC"], 1)
        self.assertEqual(member(result)["stages"]["AIC"]["credited_measures"], 0)
        self.assertAlmostEqual(member(result)["efficiency_raw"], .8)

    def test_canonical_closing_day_introduction_is_retained_with_boundary_diagnostic(self):
        # Congress ends at noon; a January 3 date alone cannot establish invalid membership.
        other = "118:hr:10564"
        closing = bill(other, through="BILL", introduced_date="2025-01-03")
        closing["milestones"]["BILL"]["date"] = "2025-01-03"
        result = evaluate(bills=[bill(), closing], impacts=[impact(), impact(other)], as_of="2026-01-01")
        # Extend snapshots to the requested replay cutoff independently of term membership.
        self.assertFalse(result["terms"]["house"]["denominators_available"])
        for b in (closing,):
            b["as_of"] = "2026-01-01"
        ordinary = bill(as_of="2026-01-01")
        impacts = [impact(as_of="2026-01-01"), impact(other, as_of="2026-01-01")]
        result = evaluate(bills=[ordinary, closing], impacts=impacts, as_of="2026-01-01")
        term = result["terms"]["house"]
        self.assertTrue(term["denominators_available"])
        self.assertEqual(term["denominators"]["BILL"], 10)
        self.assertEqual(term["coverage"]["closing_day_introduction"], 1)
        self.assertEqual(term["coverage"].get("invalid_introduction", 0), 0)

    def test_closing_day_official_join_is_flagged_and_not_assumed_after_noon(self):
        other = "118:hr:10564"
        closing = bill(other, through="BILL", introduced_date="2025-01-03", as_of="2026-01-01")
        closing["milestones"]["BILL"]["date"] = "2025-01-03"
        result = evaluate(bills=[bill(as_of="2026-01-01"), closing],
                          roles=[role(other, joined="2025-01-03")], signals=[signal(other)],
                          impacts=[impact(as_of="2026-01-01"), impact(other, as_of="2026-01-01")],
                          as_of="2026-01-01")
        m = member(result)
        self.assertEqual(m["unknown_volume"], 0)
        self.assertEqual(m["useful_volume"], 1)
        self.assertEqual(m["coverage"]["closing_day_participation_date_uncertainty"], 1)
        self.assertAlmostEqual(m["efficiency_raw"], .1)

    def test_future_participation_is_separate_from_unknown(self):
        result = evaluate(roles=[role(kind="cosponsor", joined="2024-07-01")], as_of="2024-06-01")
        m = member(result)
        self.assertEqual(m["coverage"]["future_participation"], 1)
        self.assertEqual(m["unknown_volume"], 0)
        self.assertIsNone(m["volume_raw"])

    def test_duplicate_rows_collapse_and_conflicting_identity_records_raise(self):
        b, i, r, s = bill(), impact(), role(), signal()
        result = evaluate([b, deepcopy(b)], [r, deepcopy(r)], [s, deepcopy(s)], impacts=[i, deepcopy(i)])
        self.assertAlmostEqual(member(result)["efficiency_raw"], 1.)
        self.assertEqual(member(result)["useful_volume"], 1)
        with self.assertRaises(ValueError):
            evaluate(bills=[bill(), bill(through="PASS")])
        with self.assertRaises(ValueError):
            evaluate(bills=[bill(chamber="Senate")])
        with self.assertRaises(ValueError):
            evaluate(roster=[person(), person()])

    def test_canonical_json_is_invariant_to_input_order_and_numeric_sign_representation(self):
        bs = [bill(), bill("118:hr:2", through="BILL")]
        rs = [role(), role(bio="B000002", kind="original")]
        ss = [signal(value=1), signal(value=1.0), signal(bio="B000002")]
        ps = [person(), person("B000002")]
        ims = [impact(), impact("118:hr:2")]
        expected = None
        for b_order in permutations(bs):
            for r_order in permutations(rs):
                for s_order in permutations(ss):
                    for p_order in permutations(ps):
                        output = evaluate(b_order, r_order, s_order, p_order, ims)
                        current = json.dumps(output, sort_keys=True, separators=(",", ":"))
                        if expected is None:
                            expected = current
                        self.assertEqual(current, expected)


class RankingTests(unittest.TestCase):
    def row(self, bio, p=.6, e=.5, s=.5, v=.5, **other):
        return dict(bioguide_id=bio, P=p, efficiency_score=e, substance_score=s, volume_score=v, **other)

    def test_each_priority_dominates_every_lower_dimension(self):
        cases = [([self.row("B", p=.6, e=1, s=1, v=1), self.row("A", p=.61, e=0, s=0, v=0)], ["A", "B"]),
                 ([self.row("B", e=.5, s=1, v=1), self.row("A", e=.51, s=0, v=0)], ["A", "B"]),
                 ([self.row("B", s=.5, v=1), self.row("A", s=.51, v=0)], ["A", "B"]),
                 ([self.row("A", v=.5), self.row("B", v=.51)], ["B", "A"])]
        for rows, expected in cases:
            self.assertEqual([r["bioguide_id"] for r in rank_members(rows)], expected)

    def test_missing_dimension_stops_lower_dimensions(self):
        for rows in ([self.row("B", e=None, s=1, v=1), self.row("A", e=None, s=0, v=0)],
                     [self.row("B", s=None, v=1), self.row("A", s=None, v=0)]):
            self.assertEqual([r["bioguide_id"] for r in rank_members(rows)], ["A", "B"])
        self.assertEqual([r["bioguide_id"] for r in rank_members([
            self.row("B", p=.6, e=1), self.row("A", p=.61, e=None)])], ["A", "B"])

    def test_institutional_power_is_not_an_input_and_ranking_does_not_mutate(self):
        rows = [self.row("B", institutional_power=1000000), self.row("A", institutional_power=0)]
        before = deepcopy(rows)
        result = rank_members(rows)
        self.assertEqual([r["bioguide_id"] for r in result], ["A", "B"])
        self.assertEqual(rows, before)
        self.assertEqual([r["candidate_rank"] for r in result], [1, 2])

    def test_percentiles_use_first_tie_and_only_available_peers(self):
        self.assertEqual(percentiles({"a": -1, "b": 0, "c": 1, "d": 1, "x": None}),
                         {"a": 0., "b": .33333, "c": .66666, "d": .66666})

    def test_policy_and_rank_invalid_values_raise(self):
        for value in (0, -1, True, math.inf, math.nan):
            with self.assertRaises(ValueError):
                Policy(cosponsor_half_life_days=value)
        with self.assertRaises(ValueError):
            rank_members([self.row("A", s=math.nan)])
        with self.assertRaises(ValueError):
            rank_members([self.row("A"), self.row("A")])


if __name__ == "__main__":
    unittest.main()
