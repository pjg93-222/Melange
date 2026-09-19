"""Synthetic adapter and output-safety tests; no production helper imports."""
from copy import deepcopy
from html.parser import HTMLParser
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import pev
import replay_pev as replay
from test_pev import BIO, MID, bill, person, role, signal


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def write_object(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def term_fixture(root):
    evidence = root / "data/legislation"
    missing_role, global_measure = "118:hr:102", "118:hr:103"
    unselected, letter = "118:hr:101", "118:letter:LTR-X"
    write_rows(evidence / "bill_milestones.ndjson", [
        bill(), bill(unselected),
        bill(missing_role, events={"AIC": "2023-03-01"}), bill(global_measure)])
    write_rows(evidence / "member_measure_roles.ndjson", [
        role(), role(bio="B000002"), role(unselected),
        role(global_measure, bio="B000002")])
    write_rows(evidence / "accepted_signals.ndjson", [
        signal(), signal(unselected, accepted=False), signal(missing_role),
        signal(global_measure, bio=None), signal(letter)])
    write_rows(evidence / "member_population.ndjson", [person(), person("B000002")])
    write_rows(evidence / "congressional_letter_coverage.ndjson", [{
        "measure_id": letter, "verification_status": "unverified_signature_dates",
        "accepted_rows": [{"member": BIO}, {"member": "B000002"}]}])
    write_object(evidence / "accepted_evidence_coverage.json", {"fixture": "accepted scope"})
    write_object(evidence / "population_receipt.json", {"fixture": "dated roster"})
    write_object(root / "data/engine/legislative_effectiveness_comparison_v1.json", {
        "congress": 118, "as_of": "2024-12-31", "members": {}})


def board_fixture(passed=True):
    rows = {
        "Higher raw lower": {"member": "Higher raw lower", "bioguide": "A000001",
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
    metrics = {"congress": 118, "as_of": "2024-12-31", "policy": {"fixture": True},
               "members": {
                   "A000001|house": {"efficiency_raw": .95, "efficiency_score": .9,
                                     "efficiency_percentile": .2, "efficiency_peer_count": 6,
                                     "eligible_attempts": 20, "successes": 19,
                                     "useful_volume": 20, "efficiency_status": "observed_matched_horizon"},
                   "B000002|senate": {"efficiency_raw": .5, "efficiency_score": .1,
                                      "efficiency_percentile": .8, "efficiency_peer_count": 6,
                                      "eligible_attempts": 2, "successes": 1,
                                      "useful_volume": 2, "efficiency_status": "observed_matched_horizon"},
               }}
    return metrics, comparison, base


def fake_policy(helper, order, baseline):
    return ({name: {"rank": index + 1, "tier": 1} for index, name in enumerate(order)},
            {}, [], {"fixture_policy": True})


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
            output = root / "generation"
            staging = root / "generation.building"
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


class CompactAdapterTests(unittest.TestCase):
    def test_compaction_preserves_snapshot_and_observed_failures(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            bills, roles, signals, roster, comparison, summary = replay.compact_term(
                root, 118, "2024-12-31")
            b = next(row for row in bills if row["measure_id"] == MID)
            self.assertEqual(b["as_of"], "2024-12-31")
            self.assertIs(b["milestones"]["AIC"]["reached"], False)
            # The adapter must not retain only successful bills or signatories.
            metric = pev.compute_metrics(bills, roles, signals, roster,
                                         congress=118, as_of="2024-12-31")
            self.assertEqual(metric["members"][BIO + "|house"]["eligible_attempts"], 1)
            self.assertEqual(metric["members"][BIO + "|house"]["successes"], 0)

    def test_compaction_filters_scopes_and_counts_letters_without_fabricating_roles(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            bills, roles, signals, roster, comparison, summary = replay.compact_term(
                root, 118, "2024-12-31")
            self.assertEqual({row["measure_id"] for row in bills},
                             {MID, "118:hr:102", "118:hr:103"})
            self.assertEqual({(row["measure_id"], row["bioguide_id"]) for row in roles},
                             {(MID, BIO), ("118:hr:103", "B000002")})
            self.assertEqual(summary["letter_documents"], 1)
            self.assertEqual(summary["letter_rows_not_merged"], 2)
            self.assertEqual(summary["source_role_rows"], 4)
            self.assertEqual(summary["retained_selected_role_rows"], 2)
            self.assertFalse(any(":letter:" in row["measure_id"] for row in roles + bills))

    def test_requested_cutoff_cannot_exceed_frozen_selected_bill_vintage(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            term_fixture(root)
            with self.assertRaises(ValueError):
                replay.compact_term(root, 118, "2025-01-01")


class BoardAdapterTests(unittest.TestCase):
    def make_board(self, passed=True):
        metrics, comparison, base = board_fixture(passed)
        with patch.object(replay, "apply_policy", side_effect=fake_policy) as apply:
            board = replay.term_board(pev, metrics, comparison, base,
                                      SimpleNamespace(), Path("synthetic-not-opened"))
        return board, apply

    def test_ranking_uses_percentile_and_retains_raw_wilson_separately(self):
        board, apply = self.make_board()
        self.assertEqual(apply.call_args.args[1],
                         ["Higher percentile", "Higher raw lower", "No historical record"])
        self.assertTrue(board["candidate_tiers_available"])
        row = next(r for r in board["members"] if r["bioguide_id"] == "B000002")
        self.assertEqual((row["efficiency_score"], row["efficiency_percentile"]), (.8, .8))
        self.assertEqual(row["efficiency_lower"], .1)
        self.assertEqual(row["candidate_rank"], 1)

    def test_missing_historical_term_does_not_fabricate_successful_efficiency(self):
        board, _ = self.make_board()
        row = next(r for r in board["members"] if r["bioguide_id"] == "C000003")
        self.assertIsNone(row["efficiency_score"])
        self.assertIsNone(row["efficiency_lower"])
        self.assertIsNone(row["efficiency_raw"])
        self.assertEqual((row["eligible_attempts"], row["successes"], row["useful_volume"]),
                         (0, 0, 0))
        self.assertEqual(row["efficiency_status"], "historical_member_term_not_covered")
        self.assertEqual(row["coverage"], {"historical_member_term_not_covered": 1})

    def test_failed_baseline_withholds_candidate_tiers_and_ranks(self):
        board, _ = self.make_board(passed=False)
        self.assertFalse(board["candidate_tiers_available"])
        self.assertFalse(board["gates"]["baseline_reproduced"])
        self.assertIsNone(board["summary"]["rank_changes"])
        self.assertIsNone(board["summary"]["tier_changes"])
        for row in board["members"]:
            self.assertIsNone(row["candidate_rank"])
            self.assertIsNone(row["candidate_tier"])
            self.assertIsNotNone(row["strict_rank"], "Analytical order must remain labeled separately")


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.tags = []
        self.attributes = []
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
        self.assertIn("td.textContent=value", executable)


if __name__ == "__main__":
    unittest.main()
