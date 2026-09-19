"""Independent synthetic PESV adapter and output-safety tests.

Fixtures are local temporary files. No production helper, corpus or pipeline is
imported. Engine behavior tests belong to test_pesv.py; these check the boundary
between frozen evidence, normalized metrics, candidate gates and the review UI.
"""
from copy import deepcopy
from html.parser import HTMLParser
import hashlib
import json
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pesv
import replay_pesv as replay


BIO = "A000001"
MID = "118:hr:100"
UNSELECTED = "118:hr:101"
NO_ROLE = "118:hr:102"
GLOBAL = "118:hr:103"
LETTER = "118:letter:LTR-X"
CUTOFF = "2024-12-31"
FROZEN_INPUTS = ("accepted_signals.ndjson", "bill_impact.ndjson", "bill_milestones.ndjson",
                 "member_measure_roles.ndjson", "member_population.ndjson")


def bill(mid=MID, weight=5):
    return {"measure_id": mid, "congress": 118, "chamber": "House",
            "eligible": True, "measure_type": "hr", "introduced_date": "2023-01-10",
            "as_of": CUTOFF,
            "milestones": {"BILL": {"state": "observed", "reached": True,
                                      "date": "2023-01-10"},
                           **{stage: {"state": "observed", "reached": False, "date": None}
                              for stage in ("AIC", "ABC", "PASS", "LAW")}}}


def role(mid=MID, bio=BIO):
    return {"measure_id": mid, "bioguide_id": bio, "role": "sponsor",
            "introduced_date": "2023-01-10", "joined_date": "2023-01-10",
            "withdrawn_date": None, "chronology_status": "verified"}


def signal(mid=MID, bio=BIO, accepted=True):
    return {"measure_id": mid, "bioguide_id": bio, "accepted": accepted,
            "tensor_cu": 1, "standard_direction": 1, "category": "Synthetic CU issue"}


def person(bio=BIO):
    return {"bioguide_id": bio, "congress": 118, "chamber": "House",
            "name": "Synthetic " + bio,
            "service_periods": [{"start": "2023-01-03", "end": "2025-01-03"}],
            "coverage_status": "dated_service_reconciled"}


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_object(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def term_fixture(root):
    evidence = root / "data/legislation"
    source_bills = [bill(MID), bill(UNSELECTED), bill(NO_ROLE), bill(GLOBAL)]
    write_rows(evidence / "bill_milestones.ndjson", source_bills)
    write_rows(evidence / "bill_impact.ndjson", [
        {"measure_id": mid, "class": cls, "weight": weight, "as_of": CUTOFF,
         "basis": "synthetic reviewed impact", "needs_content_review": False}
        for mid, cls, weight in ((MID, "S", 5), (UNSELECTED, "SS", 10),
                                (NO_ROLE, "C", 1), (GLOBAL, "S", 5))])
    write_rows(evidence / "member_measure_roles.ndjson", [
        role(), role(bio="B000002"), role(UNSELECTED),
        role(GLOBAL, bio="B000002"), role(GLOBAL, bio="C000003")])
    write_rows(evidence / "accepted_signals.ndjson", [
        signal(), signal(UNSELECTED, accepted=False), signal(NO_ROLE),
        signal(GLOBAL, bio=None), signal(LETTER)])
    write_rows(evidence / "member_population.ndjson", [
        person(), person("B000002"), person("C000003")])
    write_rows(evidence / "congressional_letter_coverage.ndjson", [{
        "measure_id": LETTER, "verification_status": "unverified_signature_dates",
        "accepted_rows": [{"member": BIO}, {"member": "B000002"}]}])
    write_object(evidence / "accepted_evidence_coverage.json", {"fixture": "accepted scope"})
    write_object(evidence / "population_receipt.json", {"fixture": "dated roster"})
    write_object(evidence / "effectiveness_universe_manifest.json", {
        "congress": 118, "as_of": CUTOFF, "fixture": "full official universe"})
    write_object(root / "data/engine/legislative_effectiveness_comparison_v1.json", {
        "congress": 118, "as_of": CUTOFF, "members": {}})
    return source_bills


def frozen_manifest_fixture(root):
    evidence = root / "data/legislation"
    artifacts = {}
    for filename in FROZEN_INPUTS:
        path = evidence / filename
        write_rows(path, [{"fixture_row": 1}, {"fixture_row": 2}])
        content = path.read_bytes()
        artifacts[filename] = {"sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content)}
    manifest = {"schema_version": 1, "as_of": CUTOFF, "artifacts": artifacts}
    write_object(evidence / "effectiveness_universe_manifest.json", manifest)
    return manifest


def actual_initial_hashes(root):
    evidence = root / "data/legislation"
    return {str(path.resolve()): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [*(evidence / filename for filename in FROZEN_INPUTS),
                         evidence / "effectiveness_universe_manifest.json"]}


def observed_metric(e_raw, e_score, s_raw, s_score, v_raw, v_score, count):
    return {"efficiency_raw": e_raw, "efficiency_score": e_score,
            "substance_raw": s_raw, "substance_score": s_score,
            "volume_raw": v_raw, "volume_score": v_score,
            "useful_volume": count, "useful_measures": count,
            "harmful_volume": 0, "neutral_volume": 0, "unknown_volume": 0,
            "efficiency_status": "observed", "substance_status": "observed",
            "volume_status": "observed", "coverage": {}, "roles": {}, "stages": {}}


def board_fixture(passed=True):
    rows = {
        "Higher raw": {"member": "Higher raw", "bioguide": "A000001",
                       "chamber": "House", "tierrank": 1, "tier": 1},
        "Higher percentile": {"member": "Higher percentile", "bioguide": "B000002",
                              "chamber": "Senate", "tierrank": 2, "tier": 1},
        "No historical record": {"member": "No historical record", "bioguide": "C000003",
                                 "chamber": "House", "tierrank": 3, "tier": 1},
    }
    base = {"rows": rows, "factors": dict.fromkeys(rows, .6),
            "rankable": set(rows), "passed": passed}
    comparison = {"members": {
        name: {"bioguide": row["bioguide"], "chamber": row["chamber"]}
        for name, row in rows.items()}}
    metrics = {"congress": 118, "as_of": CUTOFF, "policy": {"fixture": True},
               "members": {
                   "A000001|house": observed_metric(9.5, .2, 5, .7, 20, .8, 20),
                   "B000002|senate": observed_metric(.5, .8, 10, .3, 2, .2, 2),
               }}
    return metrics, comparison, base


def fake_policy(helper, order, baseline):
    return ({name: {"rank": index + 1, "tier": 1} for index, name in enumerate(order)},
            {}, [], {"fixture_policy": True})


def make_board(metrics=None, comparison=None, base=None, passed=True, policy=fake_policy):
    fixture_metrics, fixture_comparison, fixture_base = board_fixture(passed)
    metrics = fixture_metrics if metrics is None else metrics
    comparison = fixture_comparison if comparison is None else comparison
    base = fixture_base if base is None else base
    with patch.object(replay, "apply_policy", side_effect=policy) as apply:
        result = replay.term_board(pesv, metrics, comparison, base,
                                   SimpleNamespace(), Path("synthetic-not-opened"))
    return result, apply


class OutputSafetyTests(unittest.TestCase):
    def test_output_cannot_overlap_or_contain_any_protected_root(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, shadow, code = root / "source", root / "shadow", root / "package/src"
            for protected in (source, shadow, code):
                for candidate in (protected, protected / "generation", protected.parent):
                    with self.subTest(protected=protected, candidate=candidate):
                        with self.assertRaises(ValueError):
                            replay.validate_output(candidate, source, shadow, code)
            self.assertFalse(source.exists(), "Validation must not create protected paths")

    def test_nonempty_output_and_existing_file_are_refused_without_changes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "result"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("existing user data", encoding="utf-8")
            for candidate in (target, marker):
                with self.subTest(candidate=candidate):
                    with self.assertRaises(ValueError):
                        replay.validate_output(candidate, root / "source", root / "shadow", root / "code")
            self.assertEqual(marker.read_text(encoding="utf-8"), "existing user data")

    def test_existing_staging_directory_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            output, staging = root / "generation", root / "generation.building"
            staging.mkdir()
            with self.assertRaises(ValueError):
                replay.validate_output(output, root / "source", root / "shadow", root / "code")
            self.assertTrue(staging.is_dir())
            self.assertFalse(output.exists())

    def test_sibling_generation_and_empty_output_directory_are_allowed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, shadow, code = root / "source", root / "shadow", root / "package/src"
            output = root / "package/generations/run1"
            validated, staging = replay.validate_output(output, source, shadow, code)
            self.assertEqual(validated, output.resolve())
            self.assertEqual(staging, output.with_name("run1.building").resolve())
            self.assertFalse(output.exists(), "Validation is read-only")
            output.mkdir(parents=True)
            self.assertEqual(replay.validate_output(output, source, shadow, code)[0], output.resolve())


class FrozenManifestTests(unittest.TestCase):
    def test_five_complete_frozen_artifacts_pass(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen_manifest_fixture(root)
            result = replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)
            self.assertIs(result["passed"], True)
            self.assertEqual(result["checked_artifacts"], 5)

    def test_clean_truncation_fails_even_with_fresh_actual_initial_hashes(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen_manifest_fixture(root)
            # This is valid NDJSON and its new hash is recorded before the guard.
            # Only comparison with the frozen receipt can reveal lost records.
            write_rows(root / "data/legislation/member_measure_roles.ndjson", [{"fixture_row": 1}])
            with self.assertRaises(ValueError):
                replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)

    def test_equal_length_content_change_fails_hash_check(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen_manifest_fixture(root)
            path = root / "data/legislation/bill_milestones.ndjson"
            before = path.read_bytes()
            after = before.replace(b'"fixture_row": 2', b'"fixture_row": 9')
            self.assertEqual(len(before), len(after))
            self.assertNotEqual(before, after)
            path.write_bytes(after)
            with self.assertRaises(ValueError):
                replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)

    def test_missing_required_manifest_entry_refuses(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = frozen_manifest_fixture(root)
            del manifest["artifacts"]["bill_impact.ndjson"]
            write_object(root / "data/legislation/effectiveness_universe_manifest.json", manifest)
            with self.assertRaises(ValueError):
                replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)

    def test_missing_initial_hash_refuses(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            frozen_manifest_fixture(root)
            initial = actual_initial_hashes(root)
            del initial[str((root / "data/legislation/accepted_signals.ndjson").resolve())]
            with self.assertRaises(ValueError):
                replay.validate_frozen_manifest(root, initial, CUTOFF)

    def test_stale_or_missing_manifest_cutoff_refuses(self):
        for cutoff in ("2023-12-31", None):
            with self.subTest(cutoff=cutoff), TemporaryDirectory() as tmp:
                root = Path(tmp)
                manifest = frozen_manifest_fixture(root)
                if cutoff is None:
                    del manifest["as_of"]
                else:
                    manifest["as_of"] = cutoff
                write_object(root / "data/legislation/effectiveness_universe_manifest.json", manifest)
                with self.assertRaises(ValueError):
                    replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)

    def test_only_fixed_artifact_names_are_followed(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp) / "term"
            manifest = frozen_manifest_fixture(root)
            for name in ("../../outside-canary.ndjson", "C:/arbitrary/secret.ndjson",
                         "bill_media_evidence.ndjson"):
                manifest["artifacts"][name] = {"bytes": 123456, "sha256": "0" * 64}
            write_object(root / "data/legislation/effectiveness_universe_manifest.json", manifest)
            # None of these extra paths exists. Following them would fail or
            # consult a source outside the five declared scoring inputs.
            result = replay.validate_frozen_manifest(root, actual_initial_hashes(root), CUTOFF)
            self.assertIs(result["passed"], True)
            self.assertEqual(result["checked_artifacts"], 5)


class CompactAdapterTests(unittest.TestCase):
    def test_full_chamber_universe_and_impact_weights_survive_compaction(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            bills, roles, signals, roster, impacts, comparison, summary = replay.compact_term(root, 118, CUTOFF)
            self.assertEqual({row["measure_id"] for row in bills}, {MID, UNSELECTED, NO_ROLE, GLOBAL})
            self.assertEqual({row["measure_id"]: row["weight"] for row in impacts},
                             {MID: 5, UNSELECTED: 10, NO_ROLE: 1, GLOBAL: 5})
            selected_bill = next(row for row in bills if row["measure_id"] == MID)
            self.assertEqual(selected_bill["as_of"], CUTOFF)
            self.assertIs(selected_bill["milestones"]["AIC"]["reached"], False)
            self.assertEqual(len(roster), 3)

    def test_only_accepted_global_or_member_scoped_roles_are_retained(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            bills, roles, signals, roster, impacts, comparison, summary = replay.compact_term(root, 118, CUTOFF)
            self.assertEqual({(row["measure_id"], row["bioguide_id"]) for row in roles},
                             {(MID, BIO), (GLOBAL, "B000002"), (GLOBAL, "C000003")})
            self.assertEqual(summary["source_role_rows"], 5)
            self.assertEqual(summary["retained_selected_role_rows"], 3)
            self.assertIn(NO_ROLE, {s["measure_id"] for s in signals})
            self.assertFalse(any(r["measure_id"] == NO_ROLE for r in roles))

    def test_letter_coverage_is_reported_without_inventing_signatures(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            bills, roles, signals, roster, impacts, comparison, summary = replay.compact_term(root, 118, CUTOFF)
            self.assertEqual(summary["letter_documents"], 1)
            self.assertEqual(summary["letter_rows_not_merged"], 2)
            self.assertEqual(summary["letter_verification"], {"unverified_signature_dates": 1})
            self.assertFalse(any(":letter:" in row["measure_id"] for row in roles + bills))

    def test_requested_cutoff_cannot_exceed_frozen_evidence_vintage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            with self.assertRaises(ValueError):
                replay.compact_term(root, 118, "2025-01-01")

    def test_unselected_bill_vintage_still_matters_for_chamber_denominator(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = term_fixture(root)
            next(row for row in rows if row["measure_id"] == UNSELECTED)["as_of"] = "2023-01-11"
            write_rows(root / "data/legislation/bill_milestones.ndjson", rows)
            with self.assertRaises(ValueError):
                replay.compact_term(root, 118, CUTOFF)

    def test_comparison_congress_mismatch_refuses_replay(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            write_object(root / "data/engine/legislative_effectiveness_comparison_v1.json",
                         {"congress": 119, "as_of": CUTOFF, "members": {}})
            with self.assertRaises(ValueError):
                replay.compact_term(root, 118, CUTOFF)


class ReservedNumberTests(unittest.TestCase):
    @staticmethod
    def reserved_source(number=2):
        row = bill("119:hr:" + str(number))
        row.update(congress=119, introduced_date="2025-01-03", as_of="2026-09-06",
                   title="Reserved for the Speaker.", actions=[])
        return row

    def test_only_named_119_reserved_numbers_match_without_mutating_source(self):
        for number in (2, 3, 5, 8, 10):
            with self.subTest(number=number):
                source = self.reserved_source(number)
                original = deepcopy(source)
                reason = replay.reserved_number_exclusion(source, set())
                self.assertIsInstance(reason, str)
                self.assertTrue(reason)
                self.assertEqual(source, original)

    def test_ordinary_unknown_action_bill_is_not_excluded(self):
        source = self.reserved_source(11)
        source["title"] = "A substantive bill with incomplete action coverage"
        self.assertIsNone(replay.reserved_number_exclusion(source, set()))

    def test_reserved_exception_requires_all_exact_conditions(self):
        changes = [
            {"measure_id": "118:hr:2", "congress": 118},
            {"measure_id": "119:hr:4"},
            {"measure_id": "119:s:2", "chamber": "Senate", "measure_type": "s"},
            {"title": "Reserved for the Speaker"},
            {"title": "reserved for the speaker."},
            {"title": "Real policy legislation"},
            {"actions": [{"date": "2025-01-03", "text": "Introduced"}]},
            {"actions": None},
        ]
        for change in changes:
            with self.subTest(change=change):
                source = self.reserved_source()
                source.update(change)
                self.assertIsNone(replay.reserved_number_exclusion(source, set()))
        source = self.reserved_source()
        del source["actions"]
        self.assertIsNone(replay.reserved_number_exclusion(source, set()))

    def test_accepted_reserved_scope_refuses_instead_of_silently_disappearing(self):
        source = self.reserved_source()
        with self.assertRaises(ValueError):
            replay.reserved_number_exclusion(source, {source["measure_id"]})


class BoardAdapterTests(unittest.TestCase):
    def assert_withheld(self, board):
        self.assertFalse(board["candidate_tiers_available"])
        self.assertIsNone(board["summary"]["rank_changes"])
        self.assertIsNone(board["summary"]["tier_changes"])
        for row in board["members"]:
            self.assertIsNone(row["candidate_rank"])
            self.assertIsNone(row["candidate_tier"])

    def test_ranking_uses_normalized_scores_and_preserves_raw_diagnostics(self):
        board, apply = make_board()
        self.assertEqual(apply.call_args.args[1], ["Higher percentile", "Higher raw", "No historical record"])
        self.assertTrue(board["candidate_tiers_available"])
        row = next(r for r in board["members"] if r["bioguide_id"] == "B000002")
        self.assertEqual((row["efficiency_score"], row["efficiency_raw"]), (.8, .5))
        self.assertEqual((row["substance_score"], row["substance_raw"]), (.3, 10))
        self.assertEqual((row["volume_score"], row["volume_raw"]), (.2, 2))
        self.assertEqual(row["candidate_rank"], 1)

    def test_substance_precedes_volume_when_primacy_and_efficiency_tie(self):
        metrics, comparison, base = board_fixture()
        a, b = metrics["members"]["A000001|house"], metrics["members"]["B000002|senate"]
        a.update(efficiency_score=.6, substance_score=.3, volume_score=1., useful_volume=10000)
        b.update(efficiency_score=.6, substance_score=.8, volume_score=.1, useful_volume=1)
        board, apply = make_board(metrics, comparison, base)
        self.assertEqual(apply.call_args.args[1][:2], ["Higher percentile", "Higher raw"])
        self.assertTrue(board["candidate_tiers_available"])

    def test_volume_uses_normalized_score_after_all_higher_scores_tie(self):
        metrics, comparison, base = board_fixture()
        a, b = metrics["members"]["A000001|house"], metrics["members"]["B000002|senate"]
        a.update(efficiency_score=.6, substance_score=.6, volume_score=.2, volume_raw=999, useful_volume=999)
        b.update(efficiency_score=.6, substance_score=.6, volume_score=.8, volume_raw=1, useful_volume=1)
        board, apply = make_board(metrics, comparison, base)
        self.assertEqual(apply.call_args.args[1][:2], ["Higher percentile", "Higher raw"])

    def test_missing_historical_term_does_not_fabricate_any_metric(self):
        board, _ = make_board()
        row = next(r for r in board["members"] if r["bioguide_id"] == "C000003")
        for field in ("efficiency_raw", "efficiency_score", "substance_raw", "substance_score",
                      "volume_raw", "volume_score"):
            self.assertIsNone(row[field], field)
        self.assertEqual(row["useful_volume"], 0)
        self.assertEqual(row["coverage"], {"historical_member_term_not_covered": 1})

    def test_summary_counts_each_observed_dimension_and_distinct_measures(self):
        board, _ = make_board()
        summary = board["summary"]
        self.assertEqual(summary["members"], 3)
        for axis in ("efficiency", "substance", "volume"):
            self.assertEqual(summary[axis + "_observed"], 2)
            self.assertEqual(summary[axis + "_unknown"], 1)
        self.assertEqual(summary["useful_measures"], 22)

    def test_failed_baseline_withholds_candidate_tiers_but_retains_analytical_order(self):
        board, _ = make_board(passed=False)
        self.assert_withheld(board)
        self.assertFalse(board["gates"]["baseline_reproduced"])
        self.assertTrue(all(row["strict_rank"] is not None for row in board["members"]))

    def test_identity_mismatch_withholds_all_candidate_assignments(self):
        metrics, comparison, base = board_fixture()
        comparison["members"]["Higher raw"]["bioguide"] = "WRONG01"
        board, _ = make_board(metrics, comparison, base)
        self.assert_withheld(board)
        self.assertFalse(board["gates"]["identity_parity"])

    def test_missing_comparison_member_withholds_all_candidate_assignments(self):
        metrics, comparison, base = board_fixture()
        del comparison["members"]["Higher raw"]
        board, _ = make_board(metrics, comparison, base)
        self.assert_withheld(board)
        self.assertFalse(board["gates"]["identity_parity"])

    def test_invalid_normalized_metric_cannot_publish_a_candidate(self):
        for axis in ("efficiency", "substance", "volume"):
            for value in (math.nan, math.inf, -math.inf, -.1, 1.1, True):
                with self.subTest(axis=axis, value=value):
                    metrics, comparison, base = board_fixture()
                    metrics["members"]["A000001|house"][axis + "_score"] = value
                    try:
                        board, _ = make_board(metrics, comparison, base)
                    except ValueError:
                        continue  # A pre-publication schema refusal is also safe.
                    self.assert_withheld(board)
                    self.assertFalse(board["gates"]["valid_normalized_metrics"])

    def test_nonfinite_raw_diagnostic_cannot_publish_a_candidate(self):
        for axis in ("efficiency", "substance", "volume"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(axis=axis, value=value):
                    metrics, comparison, base = board_fixture()
                    metrics["members"]["A000001|house"][axis + "_raw"] = value
                    try:
                        board, _ = make_board(metrics, comparison, base)
                    except ValueError:
                        continue
                    self.assert_withheld(board)

    def test_copied_tier_policy_violation_withholds_candidate(self):
        def violation(helper, order, baseline):
            mapping, conduct, _, policy = fake_policy(helper, order, baseline)
            return mapping, conduct, [{"rule": "synthetic_conduct_ceiling"}], policy
        board, _ = make_board(policy=violation)
        self.assert_withheld(board)
        self.assertFalse(board["gates"]["final_tier_constraints"])


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts, self.tags, self.attributes = [], [], []
        self.current_script = None

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend(attrs)
        if tag == "script":
            self.current_script = {"attrs": dict(attrs), "text": ""}
            self.scripts.append(self.current_script)

    def handle_endtag(self, tag):
        if tag == "script":
            self.current_script = None

    def handle_data(self, data):
        if self.current_script is not None:
            self.current_script["text"] += data


class HtmlSafetyTests(unittest.TestCase):
    def test_member_text_cannot_escape_json_or_create_executable_markup(self):
        malicious = "</script><script>alert('owned')</script><img src=x onerror=alert(1)>\u2028\u2029"
        board = {"default_congress": 118, "baseline": {"errors": [malicious]},
                 "terms": {"118": {"members": [{"name": malicious,
                                                 "coverage": {"detail": malicious}}]}}}
        source = replay.review_html(board)
        parser = DocumentParser()
        parser.feed(source)
        self.assertEqual(len(parser.scripts), 2)
        self.assertNotIn("img", parser.tags)
        self.assertFalse(any(name.lower().startswith("on") for name, _ in parser.attributes))
        payloads = [script["text"] for script in parser.scripts
                    if script["attrs"].get("type") == "application/json"]
        self.assertEqual(len(payloads), 1)
        self.assertEqual(json.loads(payloads[0]), board)
        self.assertNotIn(malicious, source)
        executable = next(script["text"] for script in parser.scripts
                          if script["attrs"].get("type") != "application/json")
        self.assertNotIn("alert('owned')", executable)
        self.assertNotIn("innerHTML", executable)
        self.assertIn("textContent", executable)


if __name__ == "__main__":
    unittest.main()
