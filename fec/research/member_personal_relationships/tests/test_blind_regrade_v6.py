# -*- coding: utf-8 -*-
"""Tests for the P1-12 blind re-grade kit. No network, no live grading: these
exercise --build-kit's packet/prompt construction and the --ingest agreement
arithmetic against small synthetic fixtures, never the real 73-record file."""
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fec.research.member_personal_relationships import blind_grading as bg
from fec.research.member_personal_relationships import blind_regrade_v6 as brv

FAKE_RUBRIC = ("FAKE RUBRIC MARKER TEXT.\n"
              "Section 12: the rationale is <= 120 words and describes the cited text.\n")


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def record(rid, actor="A000001", target="B000002", names=("Alice Adams", "Bob Baker"),
          evidence_ids=("ev-1",), chamber="House", date="2021-03-04", venue="CREC",
          extra=None):
    row = {
        "id": rid, "actor": actor, "target": target, "pair": sorted([actor, target]),
        "date": date, "episode_id": "ep-%s" % rid, "evidence_ids": list(evidence_ids),
        "affinity": 3, "friction": None, "affinity_range": [2, 4], "friction_range": None,
        "neutral_evidence": False, "families": ["fam-%s" % rid],
        "source_urls": ["https://example.com/ORIGINAL_URL_MARKER"],
        "rationale": "ORIGINAL_RATIONALE_MARKER should never reach a prompt.",
        "names": list(names), "chamber": chamber, "venue": venue, "purpose": "context_preserved",
        "confidence": "provisional_single_reviewer", "display": "partially_assessed",
        "coverage_tiers": ["high", "high"],
    }
    if extra:
        row.update(extra)
    return row


def evidence(eid, actor="A000001", target="B000002", event_date="2021-03-04", source="CREC",
            attribution="direct_speaker", text=None, extra=None):
    row = {
        "evidence_id": eid, "actor": actor, "target": target, "actor_name": "Alice Adams",
        "target_name": "Bob Baker", "event_date": event_date, "source": source,
        "source_locator": "CREC-p1", "attribution": attribution,
        "text": text or ("Verbatim floor remark for %s." % eid),
        "reason": "REASON_MARKER_%s" % eid, "review_status": "assistant_reviewed",
        "category": "CATEGORY_MARKER_%s" % eid, "sign": "positive",
    }
    if extra:
        row.update(extra)
    return row


def write_ndjson_rows(path, rows):
    bg.write_ndjson(path, rows)
    return path


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

class SchemaTests(unittest.TestCase):
    def test_required_keys_and_additional_properties_false(self):
        schema = brv.record_grade_schema()
        expected = {"affinity", "friction", "affinity_range", "friction_range",
                   "neutral_evidence", "closeness_trust_evidence", "ritual_courtesy_only",
                   "cited_evidence_ids", "rationale"}
        self.assertEqual(set(schema["properties"]), expected)
        self.assertEqual(set(schema["required"]), expected)
        self.assertFalse(schema["additionalProperties"])

    def _valid(self):
        return {"affinity": "2", "friction": "unassessable", "affinity_range": ["1", "3"],
               "friction_range": None, "neutral_evidence": False,
               "closeness_trust_evidence": ["disclosure"], "ritual_courtesy_only": False,
               "cited_evidence_ids": ["ev-1"], "rationale": "Short and fine."}

    def test_valid_response_has_no_errors(self):
        self.assertEqual(brv.validate_record_grade(self._valid()), [])

    def test_missing_key_is_an_error(self):
        obj = self._valid()
        del obj["rationale"]
        self.assertTrue(brv.validate_record_grade(obj))

    def test_additional_key_is_an_error(self):
        obj = self._valid()
        obj["extra_field"] = "nope"
        self.assertTrue(brv.validate_record_grade(obj))

    def test_bad_enum_value_is_an_error(self):
        obj = self._valid()
        obj["affinity"] = "5"
        self.assertTrue(brv.validate_record_grade(obj))

    def test_range_of_wrong_length_is_an_error(self):
        obj = self._valid()
        obj["affinity_range"] = ["1", "2", "3"]
        self.assertTrue(brv.validate_record_grade(obj))

    def test_rationale_over_120_words_is_an_error(self):
        obj = self._valid()
        obj["rationale"] = " ".join(["word"] * 121)
        self.assertTrue(brv.validate_record_grade(obj))

    def test_rationale_of_exactly_120_words_is_fine(self):
        obj = self._valid()
        obj["rationale"] = " ".join(["word"] * 120)
        self.assertEqual(brv.validate_record_grade(obj), [])


# ---------------------------------------------------------------------------
# --build-kit: strip check, pass-B reversal, exclusion on unresolved evidence
# ---------------------------------------------------------------------------

class KitBuildTests(unittest.TestCase):
    def _build(self, records, evidence_rows, rubric_text=FAKE_RUBRIC, secondary_paths=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        records_path = write_ndjson_rows(root / "annotations.ndjson", records)
        evidence_path = write_ndjson_rows(root / "reviewed_events.ndjson", evidence_rows)
        out_dir = root / "out"
        original_secondary = brv.SECONDARY_EVIDENCE_FILES
        brv.SECONDARY_EVIDENCE_FILES = secondary_paths
        try:
            result = brv.build_kit(out_dir, records_path, evidence_path, rubric_text,
                                   log=lambda *_a: None)
        finally:
            brv.SECONDARY_EVIDENCE_FILES = original_secondary
        return result, out_dir

    def test_three_synthetic_records_strip_and_pass_b_reversed(self):
        records = [
            record("rec-1", evidence_ids=("ev-1", "ev-2", "ev-3")),
            record("rec-2", actor="C000003", target="D000004",
                   names=("Cara Cole", "Dan Diaz"), evidence_ids=("ev-4",)),
            record("rec-3", actor="E000005", target="F000006",
                   names=("Eve Ellis", "Fay Frost"), evidence_ids=("ev-5",)),
        ]
        evidence_rows = [
            evidence("ev-1", text="First excerpt text."),
            evidence("ev-2", text="Second excerpt text."),
            evidence("ev-3", text="Third excerpt text."),
            evidence("ev-4", actor="C000003", target="D000004", text="Fourth excerpt."),
            evidence("ev-5", actor="E000005", target="F000006", text="Fifth excerpt."),
        ]
        result, out_dir = self._build(records, evidence_rows)

        self.assertEqual(result["meta"]["records_total"], 3)
        self.assertEqual(result["meta"]["records_included"], 3)
        self.assertEqual(result["meta"]["records_excluded"], 0)
        self.assertEqual(result["meta"]["items_total"], 6)  # 3 records x 2 passes
        self.assertTrue(result["sweep"]["ok"], result["sweep"]["hits"])

        prompts_root = Path(result["kit_dir"]) / "prompts"
        all_text = []
        for md in prompts_root.rglob("*.md"):
            all_text.append(md.read_text(encoding="utf-8"))
        joined = "\n".join(all_text)

        # STRIP check: none of the stripped v6/evidence field VALUES appear anywhere.
        for leak in ("ORIGINAL_RATIONALE_MARKER", "ORIGINAL_URL_MARKER",
                    "REASON_MARKER_ev-1", "CATEGORY_MARKER_ev-1"):
            self.assertNotIn(leak, joined)
        # And the forbidden KEY NAMES themselves (outside the rubric block).
        sweep = brv.forbidden_word_sweep(prompts_root, FAKE_RUBRIC)
        self.assertTrue(sweep["ok"], sweep["hits"])

        # Pass B reversed: rec-1 has 3 evidence ids; pass A keeps ev-1,ev-2,ev-3
        # order, pass B must show exactly the reverse.
        stem = brv.safe_stem("rec-1")
        text_a = (prompts_root / "A" / ("%s.md" % stem)).read_text(encoding="utf-8")
        text_b = (prompts_root / "B" / ("%s.md" % stem)).read_text(encoding="utf-8")
        order_a = [line.split("]")[0][1:] for line in text_a.splitlines()
                  if line.startswith("[ev-")]
        order_b = [line.split("]")[0][1:] for line in text_b.splitlines()
                  if line.startswith("[ev-")]
        self.assertEqual(order_a, ["ev-1", "ev-2", "ev-3"])
        self.assertEqual(order_b, list(reversed(order_a)))

        index = json.loads((Path(result["index_path"])).read_text(encoding="utf-8"))
        self.assertEqual(len(index["items"]), 6)
        batches = json.loads((Path(result["batches_path"])).read_text(encoding="utf-8"))
        # 3 items per pass, batch_max 19 -> exactly one batch per pass.
        self.assertEqual(batches["meta"]["batch_count"], 2)
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["evidence_missing_in_repo"], [])

    def test_record_excluded_when_evidence_id_missing_everywhere(self):
        records = [record("rec-ok", evidence_ids=("ev-1",)),
                  record("rec-bad", actor="C000003", target="D000004",
                         names=("Cara Cole", "Dan Diaz"), evidence_ids=("ev-ghost",))]
        evidence_rows = [evidence("ev-1")]
        result, out_dir = self._build(records, evidence_rows)

        self.assertEqual(result["meta"]["records_included"], 1)
        self.assertEqual(result["meta"]["records_excluded"], 1)
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["evidence_missing_in_repo"]), 1)
        entry = manifest["evidence_missing_in_repo"][0]
        self.assertEqual(entry["record_id"], "rec-bad")
        self.assertEqual(entry["evidence_ids"], ["ev-ghost"])
        self.assertEqual(entry["unresolved_evidence_ids"][0]["status"],
                         "not_found_anywhere_searched")
        # never a placeholder packet for the excluded record
        stem = brv.safe_stem("rec-bad")
        self.assertFalse((Path(result["kit_dir"]) / "prompts" / "A" / ("%s.md" % stem)).exists())

    def test_record_excluded_when_evidence_resolves_only_as_paraphrase(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        secondary_path = Path(tmp.name) / "graded_events.ndjson"
        write_ndjson_rows(secondary_path, [
            {"id": "ev-paraphrase-only", "note": "PRIOR REVIEWER PARAPHRASE, not a quotation."}])
        records = [record("rec-paraphrased", evidence_ids=("ev-paraphrase-only",))]
        result, out_dir = self._build(records, evidence_rows=[],
                                      secondary_paths=(secondary_path,))
        self.assertEqual(result["meta"]["records_excluded"], 1)
        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        entry = manifest["evidence_missing_in_repo"][0]["unresolved_evidence_ids"][0]
        self.assertEqual(entry["status"], "found_only_as_paraphrase_elsewhere")
        self.assertEqual(entry["resolved_in_file"], str(secondary_path))
        self.assertIn("PRIOR REVIEWER PARAPHRASE", entry["paraphrase_not_used_as_evidence"])
        # the paraphrase text must never appear in any written prompt
        for md in (Path(result["kit_dir"]) / "prompts").rglob("*.md"):
            self.assertNotIn("PRIOR REVIEWER PARAPHRASE", md.read_text(encoding="utf-8"))

    def test_partial_resolution_still_excludes_the_whole_record(self):
        # One resolvable + one unresolvable evidence_id -> excluded outright,
        # never shown with a silently-shrunk evidence set.
        records = [record("rec-partial", evidence_ids=("ev-1", "ev-ghost"))]
        result, out_dir = self._build(records, evidence_rows=[evidence("ev-1")])
        self.assertEqual(result["meta"]["records_excluded"], 1)
        self.assertEqual(result["meta"]["items_total"], 0)


# ---------------------------------------------------------------------------
# agreement arithmetic (hand-computed)
# ---------------------------------------------------------------------------

class QwkTests(unittest.TestCase):
    def test_perfect_agreement_is_one(self):
        kappa, note = brv.qwk_or_null([(0, 0), (1, 1), (4, 4)])
        self.assertEqual(kappa, 1.0)
        self.assertIsNone(note)

    def test_hand_computed_case(self):
        # a=[2,1], b=[2,3]: derivation in the module's test docstring below.
        # num = w(2,2)*1 + w(1,3)*1 = 0 + 4/16 = 0.25
        # den = [w(1,2)+w(1,3)+w(2,2)+w(2,3)] / n = [1/16+4/16+0+1/16]/2 = 0.1875
        # kappa = 1 - 0.25/0.1875 = -1/3
        kappa, note = brv.qwk_or_null([(2, 2), (1, 3)])
        self.assertIsNone(note)
        self.assertAlmostEqual(kappa, -1.0 / 3.0, places=9)

    def test_zero_variance_one_rater_returns_null(self):
        kappa, note = brv.qwk_or_null([(1, 1), (1, 2), (1, 0)])  # rater A always 1
        self.assertIsNone(kappa)
        self.assertIn("zero variance", note)

    def test_zero_variance_both_raters_returns_null(self):
        kappa, note = brv.qwk_or_null([(2, 2), (2, 2), (2, 2)])
        self.assertIsNone(kappa)
        self.assertIn("zero variance", note)

    def test_empty_returns_null(self):
        kappa, note = brv.qwk_or_null([])
        self.assertIsNone(kappa)
        self.assertIn("n=0", note)


class AxisAgreementTests(unittest.TestCase):
    def test_hand_computed_rates_and_missing_bookkeeping(self):
        record_ids = ["r1", "r2", "r3", "r4", "r5", "r6"]
        pass_a = {"r1": {"affinity": "2"}, "r2": {"affinity": "unassessable"},
                 "r3": {"affinity": "1"}, "r4": {"affinity": "3"}}
        pass_b = {"r1": {"affinity": "2"}, "r2": {"affinity": "unassessable"},
                 "r3": {"affinity": "3"}, "r5": {"affinity": "0"}}
        block = brv.axis_agreement(pass_a, pass_b, record_ids, "affinity")

        self.assertEqual(block["n_total"], 6)
        self.assertEqual(sorted(block["missing"]), ["r4", "r5", "r6"])
        # present on both sides: r1, r2, r3 -> n=3
        self.assertEqual(block["assessability_agreement"]["n"], 3)
        self.assertEqual(block["assessability_agreement"]["agree"], 3)
        self.assertEqual(block["assessability_agreement"]["rate"], 1.0)
        # both numerically assessed (excludes r2, unassessable): r1, r3 -> n=2
        self.assertEqual(block["both_assessed_n"], 2)
        self.assertEqual(block["exact_agreement"], bg._rate(1, 2))     # r1 exact, r3 (1 vs 3) not
        self.assertEqual(block["within_1_agreement"], bg._rate(1, 2))  # r1 within1, r3 |1-3|=2 not
        # r1=(2,2), r3=(1,3) -> same hand-computed case as QwkTests.test_hand_computed_case
        self.assertAlmostEqual(block["quadratic_weighted_kappa"], -1.0 / 3.0, places=9)

    def test_all_missing_gives_null_rates_not_zero(self):
        block = brv.axis_agreement({}, {}, ["r1", "r2"], "affinity")
        self.assertEqual(block["missing"], ["r1", "r2"])
        self.assertIsNone(block["assessability_agreement"]["rate"])
        self.assertIsNone(block["exact_agreement"]["rate"])


# ---------------------------------------------------------------------------
# --ingest: missing response is a failure, never imputed
# ---------------------------------------------------------------------------

class IngestTests(unittest.TestCase):
    def test_missing_response_is_a_failure_and_excluded_from_by_pass(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        schema = brv.record_grade_schema()
        present_path = root / "present.json"
        missing_path = root / "missing.json"
        valid_grade = {"affinity": "2", "friction": "unassessable", "affinity_range": ["1", "3"],
                      "friction_range": None, "neutral_evidence": False,
                      "closeness_trust_evidence": [], "ritual_courtesy_only": False,
                      "cited_evidence_ids": ["ev-1"], "rationale": "fine"}
        present_path.write_text(json.dumps(valid_grade), encoding="utf-8")
        # missing_path is deliberately never written.
        items = [
            {"item_id": "rec-present", "pass": "A", "response_path": str(present_path)},
            {"item_id": "rec-missing", "pass": "A", "response_path": str(missing_path)},
        ]
        by_pass, failures = brv.read_responses(items, schema)

        self.assertIn("rec-present", by_pass["A"])
        self.assertNotIn("rec-missing", by_pass["A"])
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["item_id"], "rec-missing")
        self.assertEqual(failures[0]["reason"], "missing_response")

    def test_invalid_json_is_a_failure(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        bad_path = Path(tmp.name) / "bad.json"
        bad_path.write_text("{not json", encoding="utf-8")
        by_pass, failures = brv.read_responses(
            [{"item_id": "rec-bad", "pass": "B", "response_path": str(bad_path)}],
            brv.record_grade_schema())
        self.assertEqual(by_pass["B"], {})
        self.assertEqual(failures[0]["reason"].startswith("invalid_json"), True)

    # -- 20260911 v6 regrade ingest mismatch: batch regrade_retext__B__0001's
    # response writer sanitised item_id by replacing only ':' and left the
    # "#retext" suffix's literal '#' untouched, where response_path (built
    # from safe_stem) folds '#' to '_' same as ':'. read_responses must
    # tolerate that specific, item-derived alternate filename without ever
    # guessing between two different records.

    def _valid_grade(self, **overrides):
        grade = {"affinity": "2", "friction": "unassessable", "affinity_range": ["1", "3"],
                "friction_range": None, "neutral_evidence": False,
                "closeness_trust_evidence": [], "ritual_courtesy_only": False,
                "cited_evidence_ids": ["ev-1"], "rationale": "fine"}
        grade.update(overrides)
        return grade

    def test_grader_hash_preserved_filename_is_tolerated(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        item_id = "v6:anchor-foo-0#retext"
        recorded_path = root / (brv.safe_stem(item_id) + ".json")  # "..._retext.json"
        actual_path = root / (item_id.replace(":", "_") + ".json")  # "...#retext.json"
        self.assertNotEqual(str(recorded_path), str(actual_path))
        grade = self._valid_grade(rationale="from the hash-preserved file")
        actual_path.write_text(json.dumps(grade), encoding="utf-8")
        # recorded_path (what response_path says) is deliberately never
        # written -- only the grader's alternate-named file exists.
        by_pass, failures = brv.read_responses(
            [{"item_id": item_id, "pass": "B", "response_path": str(recorded_path)}],
            brv.record_grade_schema())
        self.assertEqual(failures, [])
        self.assertEqual(by_pass["B"][item_id], grade)

    def test_alt_filename_never_borrows_another_items_own_response_path(self):
        # Guard: an alternate candidate is skipped when it equals some OTHER
        # item's own recorded response_path -- using it anyway would swap a
        # different record's grade in instead of correctly reporting this
        # one missing.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        x_id = "v6:x-0#retext"
        x_recorded = root / (brv.safe_stem(x_id) + ".json")
        # Contrived so X's alternate candidate IS Y's own recorded path.
        y_recorded = root / (x_id.replace(":", "_") + ".json")
        y_grade = self._valid_grade(rationale="this belongs to v6:y, not x")
        y_recorded.write_text(json.dumps(y_grade), encoding="utf-8")
        # x_recorded is deliberately never written.
        items = [{"item_id": x_id, "pass": "B", "response_path": str(x_recorded)},
                {"item_id": "v6:y", "pass": "B", "response_path": str(y_recorded)}]
        by_pass, failures = brv.read_responses(items, brv.record_grade_schema())
        self.assertNotIn(x_id, by_pass["B"])
        self.assertEqual(by_pass["B"]["v6:y"], y_grade)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0], {"item_id": x_id, "pass": "B",
                                       "reason": "missing_response", "path": str(x_recorded)})

    def test_retext_supersession_survives_the_graders_hash_preserved_filename(self):
        # End-to-end shape of the production bug: read_responses feeding
        # apply_supersession, exactly as run_ingest composes them. Before
        # the fix, pass B produced a `no_text_packet` failure for the OLD
        # id even though a valid graded response existed on disk under the
        # grader's alternate filename.
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        old_id, new_id = "v6:anchor-foo-0", "v6:anchor-foo-0#retext"
        (root / "A").mkdir()
        (root / "B").mkdir()
        grade_a = self._valid_grade(rationale="pass A")
        grade_b = self._valid_grade(rationale="pass B")
        a_recorded = root / "A" / (brv.safe_stem(new_id) + ".json")
        b_recorded = root / "B" / (brv.safe_stem(new_id) + ".json")
        a_recorded.write_text(json.dumps(grade_a), encoding="utf-8")  # pass A: canonical name
        b_actual = b_recorded.with_name(new_id.replace(":", "_") + ".json")
        b_actual.write_text(json.dumps(grade_b), encoding="utf-8")  # pass B: '#' preserved

        items = [{"item_id": new_id, "pass": "A", "response_path": str(a_recorded)},
                {"item_id": new_id, "pass": "B", "response_path": str(b_recorded)}]
        by_pass, failures = brv.read_responses(items, brv.record_grade_schema())
        eff_by_pass, eff_failures = brv.apply_supersession(
            by_pass, failures, {"A": {old_id: new_id}, "B": {old_id: new_id}})

        self.assertEqual(eff_failures, [])
        self.assertEqual(eff_by_pass["A"][old_id], grade_a)
        self.assertEqual(eff_by_pass["B"][old_id], grade_b)


# ---------------------------------------------------------------------------
# --build-kit-supplement: locator parsing (pure functions, no I/O)
# ---------------------------------------------------------------------------

class LocatorParsingTests(unittest.TestCase):
    def test_parses_canonical_sqlite_locator(self):
        parsed = brv.parse_sqlite_locator("sqlite:social_media.db#speeches/rowid=19040")
        self.assertEqual(parsed, {"db": "social_media.db", "table": "speeches", "rowid": 19040})

    def test_rejects_non_sqlite_scheme(self):
        self.assertIsNone(brv.parse_sqlite_locator("pdf:foo.pages.json#pages=1,2"))

    def test_rejects_missing_rowid(self):
        self.assertIsNone(brv.parse_sqlite_locator("sqlite:social_media.db#speeches/rowid="))

    def test_rejects_non_numeric_rowid(self):
        self.assertIsNone(brv.parse_sqlite_locator("sqlite:social_media.db#speeches/rowid=abc"))

    def test_rejects_non_string_input(self):
        self.assertIsNone(brv.parse_sqlite_locator(None))
        self.assertIsNone(
            brv.parse_sqlite_locator({"sqlite": "sqlite:social_media.db#speeches/rowid=1"}))

    def test_rejects_trailing_garbage(self):
        self.assertIsNone(
            brv.parse_sqlite_locator("sqlite:social_media.db#speeches/rowid=19040 extra"))


class ResolveRowidTests(unittest.TestCase):
    def test_prefers_explicit_source_locator(self):
        locator_row = {"source_locator": {"sqlite": "sqlite:social_media.db#speeches/rowid=42"}}
        self.assertEqual(brv.resolve_rowid("review_42", locator_row), 42)

    def test_falls_back_to_review_id_convention_with_no_secondary_row(self):
        self.assertEqual(brv.resolve_rowid("review_65329", None), 65329)
        self.assertEqual(brv.resolve_rowid("new_review_44692", None), 44692)

    def test_falls_back_to_bare_source_row_token(self):
        # v6:cotton_welch_20231017's own evidence_id: never written to any
        # secondary ndjson, but it plainly names its own source_rowid.
        self.assertEqual(
            brv.resolve_rowid("source_row_153803_and_original_S5030_S5031", None), 153803)

    def test_no_match_returns_none(self):
        self.assertIsNone(brv.resolve_rowid("comer_frost_order_control", None))

    def test_locator_row_present_but_no_sqlite_key_still_falls_back(self):
        locator_row = {"source_locator": {"pdf_pages": [1, 2]}}
        self.assertEqual(brv.resolve_rowid("review_9", locator_row), 9)


# ---------------------------------------------------------------------------
# --build-kit-supplement: recover_one against a fake sqlite db / fake pages
# ---------------------------------------------------------------------------

def make_fake_speeches_db(path, rows):
    """rows: iterable of (rowid, member, date, source, chamber, package, text)."""
    con = sqlite3.connect(str(path))
    con.execute("CREATE TABLE speeches(member TEXT, date TEXT, source TEXT, chamber TEXT, "
               "package TEXT, nwords INTEGER, text TEXT)")
    for rowid, member, date, source, chamber, package, text in rows:
        con.execute("INSERT INTO speeches(rowid, member, date, source, chamber, package, "
                   "nwords, text) VALUES (?,?,?,?,?,?,?,?)",
                   (rowid, member, date, source, chamber, package, len(text.split()), text))
    con.commit()
    con.close()


class RecoverOneTests(unittest.TestCase):
    def test_sqlite_recovery_shapes_a_packet_evidence_row(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(999, "Alice Adams", "2022-01-02", "CREC", "house",
                                        "CREC-2022-01-02", "Verbatim floor remark text.")])
        locator_row = {"source_locator": {"sqlite": "sqlite:social_media.db#speeches/rowid=999"},
                      "date": "2022-01-02"}
        row, why, bookkeeping = brv.recover_one("review_999", locator_row, db_path=db_path)
        self.assertIsNone(why)
        self.assertEqual(row, {"evidence_id": "review_999", "event_date": "2022-01-02",
                              "source": "CREC", "attribution": "direct_speaker",
                              "text": "Verbatim floor remark text."})
        self.assertEqual(bookkeeping["locator"], "sqlite:social_media.db#speeches/rowid=999")
        self.assertEqual(bookkeeping["chars"], len("Verbatim floor remark text."))

    def test_sqlite_missing_rowid_is_reported_not_raised(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "fake_social_media.db"
        make_fake_speeches_db(db_path, [])
        row, why, bookkeeping = brv.recover_one("review_1", None, db_path=db_path)
        self.assertIsNone(row)
        self.assertIsNone(bookkeeping)
        self.assertIn("absent from speeches", why)

    def test_pdf_pages_recovery_joins_pages_in_order(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        sources_dir = Path(tmp.name)
        pages = [{"pdf_page": 1, "text": "Page one."}, {"pdf_page": 2, "text": "Page two."}]
        (sources_dir / "fake_hearing.pages.json").write_text(json.dumps(pages), encoding="utf-8")
        locator_row = {"source_locator": {"pdf_pages": [1, 2]}, "source_family": "fake_hearing",
                      "date": "2024-01-01"}
        attribution_row = {"attribution": "direct_reply_sequence"}
        row, why, bookkeeping = brv.recover_one("some_hearing_id", locator_row, attribution_row,
                                                sources_dir=sources_dir)
        self.assertIsNone(why)
        self.assertEqual(row["text"], "[PDF PAGE 1]\nPage one.\n\n[PDF PAGE 2]\nPage two.")
        self.assertEqual(row["source"], brv.HEARING_SOURCE_TAG)
        self.assertEqual(row["attribution"], "direct_reply_sequence")
        self.assertIn("pages=1,2", bookkeeping["locator"])

    def test_pdf_pages_missing_page_is_reported_not_raised(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        sources_dir = Path(tmp.name)
        (sources_dir / "fake_hearing.pages.json").write_text(
            json.dumps([{"pdf_page": 1, "text": "Page one."}]), encoding="utf-8")
        locator_row = {"source_locator": {"pdf_pages": [1, 2]}, "source_family": "fake_hearing"}
        row, why, bookkeeping = brv.recover_one("x", locator_row, sources_dir=sources_dir)
        self.assertIsNone(row)
        self.assertIsNone(bookkeeping)
        self.assertIn("not present in", why)

    def test_no_locator_at_all_is_reported_not_raised(self):
        row, why, bookkeeping = brv.recover_one("totally_unplaceable_id", None)
        self.assertIsNone(row)
        self.assertIsNone(bookkeeping)
        self.assertIn("no sqlite rowid or pdf_pages locator", why)


# ---------------------------------------------------------------------------
# --build-kit-supplement: additive kit-building on a synthetic fake kit
# ---------------------------------------------------------------------------

class BuildKitSupplementSyntheticTests(unittest.TestCase):
    def _seed_kit(self, root, existing_records, evidence_rows):
        """A real --build-kit run (so index/batches/manifest have the exact
        shape build_kit_supplement expects to extend)."""
        records_path = write_ndjson_rows(root / "annotations.ndjson", existing_records)
        evidence_path = write_ndjson_rows(root / "reviewed_events.ndjson", evidence_rows)
        out_dir = root / "out"
        result = brv.build_kit(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                              log=lambda *_a: None)
        return records_path, evidence_path, out_dir, result

    def test_recovers_a_sqlite_record_and_appends_additively(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        kept = record("rec-kept", evidence_ids=("ev-kept",))
        missing = record("rec-missing", actor="C000003", target="D000004",
                         names=("Cara Cole", "Dan Diaz"), evidence_ids=("review_999",))
        records_path, evidence_path, out_dir, build_result = self._seed_kit(
            root, [kept, missing], [evidence("ev-kept")])
        self.assertEqual(build_result["meta"]["records_included"], 1)
        self.assertEqual(build_result["meta"]["records_excluded"], 1)

        before_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        before_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))
        kept_prompt_a = (Path(build_result["kit_dir"]) / "prompts" / "A"
                        / (brv.safe_stem("rec-kept") + ".md"))
        before_bytes = kept_prompt_a.read_bytes()

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(999, "Cara Cole", "2022-05-06", "CREC", "house",
                                        "CREC-2022-05-06", "Verbatim recovered remark.")])
        locator_path = write_ndjson_rows(root / "exchange_context.ndjson", [
            {"id": "review_999", "date": "2022-05-06",
            "source_locator": {"sqlite": "sqlite:social_media.db#speeches/rowid=999"}}])

        result = brv.build_kit_supplement(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                          log=lambda *_a: None, locator_path=locator_path,
                                          attribution_path=root / "no_such_file.ndjson",
                                          db_path=db_path, sources_dir=root)

        self.assertEqual(result["recovered_records"], 1)
        self.assertEqual(result["still_missing"], [])
        self.assertEqual(result["new_items"], 2)  # rec-missing x passes A/B
        self.assertEqual(sorted(result["new_batches"]), ["regrade__A__0002", "regrade__B__0002"])
        self.assertTrue(result["sweep"]["ok"], result["sweep"]["hits"])

        # Existing entry/file completely untouched.
        self.assertEqual(kept_prompt_a.read_bytes(), before_bytes)
        after_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:len(before_index["items"])], before_index["items"])
        self.assertEqual(len(after_index["items"]), len(before_index["items"]) + 2)
        after_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])
        self.assertEqual(after_batches["meta"]["batch_count"], len(before_batches["batches"]) + 2)

        # New prompt carries the recovered VERBATIM text.
        new_stem = brv.safe_stem("rec-missing")
        new_prompt = (Path(result["kit_dir"]) / "prompts" / "A"
                     / (new_stem + ".md")).read_text(encoding="utf-8")
        self.assertIn("Verbatim recovered remark.", new_prompt)

        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(len(manifest["recovered"]), 1)
        self.assertEqual(manifest["recovered"][0]["record_id"], "rec-missing")
        self.assertEqual(manifest["recovered"][0]["locator"],
                         "sqlite:social_media.db#speeches/rowid=999")
        self.assertEqual(manifest["still_missing"], [])
        # Original manifest keys (written by build_kit) untouched.
        self.assertEqual(manifest["records_total"], 2)
        self.assertEqual(manifest["records_excluded"], 1)

    def test_unrecoverable_record_stays_excluded_and_is_logged(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        missing = record("rec-ghost", evidence_ids=("ev-nowhere",))
        records_path, evidence_path, out_dir, build_result = self._seed_kit(root, [missing], [])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [])
        result = brv.build_kit_supplement(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                          log=lambda *_a: None,
                                          locator_path=root / "no_locator.ndjson",
                                          attribution_path=root / "no_attribution.ndjson",
                                          db_path=db_path, sources_dir=root)
        self.assertEqual(result["recovered_records"], 0)
        self.assertEqual(len(result["still_missing"]), 1)
        self.assertEqual(result["still_missing"][0]["record_id"], "rec-ghost")
        self.assertEqual(result["new_items"], 0)
        self.assertEqual(result["new_batches"], [])
        stem = brv.safe_stem("rec-ghost")
        self.assertFalse((Path(result["kit_dir"]) / "prompts" / "A" / (stem + ".md")).exists())


# ---------------------------------------------------------------------------
# --build-kit-supplement: additive behaviour against a COPY of the REAL,
# currently-being-graded kit. Never touches outputs/.../grading_kit itself
# (four other agents read/write under it right now) -- copies it into a
# temp dir first and runs entirely there. Reads (social_media.db, the
# hearing PDFs' *.pages.json, exchange_context.ndjson, annotations.ndjson)
# are the real, read-only repo files.
# ---------------------------------------------------------------------------

class BuildKitSupplementRealKitTests(unittest.TestCase):
    def setUp(self):
        self.real_kit_dir = brv.DEFAULT_OUT / "grading_kit"
        if not self.real_kit_dir.exists():
            self.skipTest("no real grading_kit at %s" % self.real_kit_dir)

    def test_first_84_entries_and_their_real_files_are_byte_identical(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = Path(tmp.name) / "out"
        shutil.copytree(self.real_kit_dir, out_dir / "grading_kit")

        before_index = json.loads((out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        before_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        before_manifest = json.loads(
            (out_dir / "grading_kit" / "manifest.json").read_text(encoding="utf-8"))
        n_before = len(before_index["items"])
        # prompt_path is an ABSOLUTE path baked in when --build-kit originally
        # ran, so these point at the REAL live kit, not this temp copy.
        # Hashing them proves the real files four other agents are grading
        # right now are never opened for writing by this run.
        before_hashes = {it["prompt_path"]: bg.sha256_file(it["prompt_path"])
                         for it in before_index["items"]}
        rubric_text = brv.RUBRIC_PATH.read_text(encoding="utf-8")

        if "recovered" in before_manifest:
            # The real, one-time --build-kit-supplement run already landed on
            # the live kit (this test's own job): every one of the 31 stems
            # is already in this copy's index.json, so re-running MUST be
            # refused outright rather than silently double-writing. This
            # keeps the test meaningful (a regression guard against ever
            # double-applying the supplement) instead of failing forever
            # once the one-time recovery is done.
            with self.assertRaises(brv.RegradeKitError):
                brv.build_kit_supplement(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                         rubric_text, log=lambda *_a: None)
            return

        result = brv.build_kit_supplement(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                          rubric_text, log=lambda *_a: None)

        after_index = json.loads((out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        after_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        after_manifest = json.loads(
            (out_dir / "grading_kit" / "manifest.json").read_text(encoding="utf-8"))

        self.assertEqual(after_index["items"][:n_before], before_index["items"])
        self.assertGreater(len(after_index["items"]), n_before)
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])
        for prompt_path, digest in before_hashes.items():
            self.assertEqual(bg.sha256_file(prompt_path), digest, prompt_path)
        for key in ("records_total", "records_included_in_kit", "records_excluded",
                   "evidence_missing_in_repo"):
            self.assertEqual(after_manifest[key], before_manifest[key])
        self.assertIn("recovered", after_manifest)
        self.assertIn("still_missing", after_manifest)
        still_missing_records = {m["record_id"] for m in after_manifest["still_missing"]}
        self.assertEqual(len(after_manifest["recovered"]) + len(still_missing_records), 31)
        print("\n[real-kit additive-behaviour check] recovered=%d still_missing=%d new_items=%d "
             "new_batches=%s sweep_ok=%s"
             % (result["recovered_records"], len(still_missing_records), result["new_items"],
                result["new_batches"], result["sweep"]["ok"]))


# ---------------------------------------------------------------------------
# --build-kit-retext: local-speech recovery for "(no text)" evidence rows.
# ---------------------------------------------------------------------------

class ClassifySourceUrlsTests(unittest.TestCase):
    def test_cnn_transcript_url(self):
        url = "https://transcripts.cnn.com/show/x/date/2020-01-01/segment/01"
        self.assertEqual(brv.classify_source_urls([url]),
                         {"strategy": "interview_url", "package": url})

    def test_crec_pdf_url_with_chamber_suffix(self):
        result = brv.classify_source_urls(
            ["https://www.govinfo.gov/content/pkg/CREC-2021-11-17/pdf/CREC-2021-11-17-house.pdf"])
        self.assertEqual(result, {"strategy": "crec_date", "package": "CREC-2021-11-17",
                                  "chamber": "house"})

    def test_crec_pdf_url_without_chamber_suffix(self):
        result = brv.classify_source_urls(
            ["https://www.govinfo.gov/content/pkg/CREC-2021-11-17/pdf/CREC-2021-11-17.pdf"])
        self.assertEqual(result, {"strategy": "crec_date", "package": "CREC-2021-11-17",
                                  "chamber": None})

    def test_unrecognized_domain_and_empty_input_return_none(self):
        self.assertIsNone(brv.classify_source_urls(["https://www.example.senate.gov/news/x"]))
        self.assertIsNone(brv.classify_source_urls(["https://www.c-span.org/program/washington-journal/x"]))
        self.assertIsNone(brv.classify_source_urls([]))
        self.assertIsNone(brv.classify_source_urls(None))

    def test_first_recognized_url_wins_when_several_are_listed(self):
        result = brv.classify_source_urls(["https://www.example.com/article",
                                           "https://transcripts.cnn.com/show/x/date/2020-01-01/segment/01"])
        self.assertEqual(result["strategy"], "interview_url")


class SurnameOfTests(unittest.TestCase):
    def test_last_whitespace_token(self):
        self.assertEqual(brv.surname_of("Alexandria Ocasio-Cortez"), "Ocasio-Cortez")
        self.assertEqual(brv.surname_of("James Comer"), "Comer")

    def test_empty_or_missing_name(self):
        self.assertEqual(brv.surname_of(""), "")
        self.assertEqual(brv.surname_of(None), "")


class TrimEvidenceTextTests(unittest.TestCase):
    """Mechanical evidence-text builder (task step 2): sentence is this
    source's "paragraph" unit (see trim_evidence_text's docstring -- every
    `speeches.text` row is one continuous run with no blank-line breaks)."""

    def test_short_text_with_no_surname_mention_is_kept_whole_and_unmarked(self):
        text = "You will not do that. I am not a child."
        built, trimmed = brv.trim_evidence_text(text, ["Mace", "Crockett"])
        self.assertEqual(built, text)
        self.assertFalse(trimmed)

    def test_keeps_one_sentence_of_context_on_each_side_and_marks_trimmed(self):
        text = ("Sentence one is filler. Sentence two is also filler. "
               "Sentence three mentions Warren directly. Sentence four is filler too. "
               "Sentence five is filler as well.")
        built, trimmed = brv.trim_evidence_text(text, ["Warren"])
        self.assertTrue(trimmed)
        self.assertIn("Sentence three mentions Warren directly.", built)
        self.assertIn("Sentence two is also filler.", built)
        self.assertIn("Sentence four is filler too.", built)
        self.assertNotIn("Sentence one is filler.", built)
        self.assertNotIn("Sentence five is filler as well.", built)
        self.assertTrue(built.endswith(brv.RETEXT_TRIM_MARKER))

    def test_mention_past_the_char_cap_in_raw_order_is_still_captured(self):
        """Regression guard: a naive head-truncation-at-6000-chars would drop
        this mention entirely (it sits past the cap in the RAW text) --
        exactly the failure mode this task's own investigation found and
        rejected for roy_massie_20240925 (rowid 171173: "Massie" first
        appears at raw offset 7488 of an 8108-char speech)."""
        filler = "This sentence says nothing about anyone in particular. " * 150
        text = filler + "Only now do we finally mention Massie by name. " + filler
        self.assertGreater(len(text), 6000)
        built, trimmed = brv.trim_evidence_text(text, ["Massie"], max_chars=6000)
        self.assertIn("Only now do we finally mention Massie by name.", built)
        self.assertTrue(trimmed)

    def test_caps_at_max_chars_when_the_kept_window_is_still_oversized(self):
        text = "Warren appears in this sentence again and again. " * 300
        built, trimmed = brv.trim_evidence_text(text, ["Warren"], max_chars=500)
        self.assertTrue(trimmed)
        self.assertLessEqual(len(built) - len("\n\n" + brv.RETEXT_TRIM_MARKER), 500)

    def test_empty_text_returns_empty_untrimmed(self):
        self.assertEqual(brv.trim_evidence_text("", ["Warren"]), ("", False))
        self.assertEqual(brv.trim_evidence_text(None, ["Warren"]), ("", False))

    def test_never_introduces_reviewer_vocabulary(self):
        text = "Plain evidence sentence naming Grassley, nothing more."
        built, _ = brv.trim_evidence_text(text, ["Grassley"])
        for marker in ("REASON_MARKER", "CATEGORY_MARKER", "neutral_evidence", "affinity_range"):
            self.assertNotIn(marker, built)


class MatchLocalSpeechTests(unittest.TestCase):
    def _db(self, rows):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        db_path = Path(tmp.name) / "fake_social_media.db"
        make_fake_speeches_db(db_path, rows)
        return db_path

    def test_single_member_match_is_recovered_without_needing_a_surname_hit(self):
        url = "https://transcripts.cnn.com/show/xx/date/2022-01-01/segment/01"
        db_path = self._db([(1, "Alice Adams", "2022-01-01", "INTERVIEW", "xx", url,
                            "A short soundbite that never names the other person.")])
        result = brv.match_local_speech("ev-1", [url], "Alice Adams", "Baker", db_path=db_path)
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["rowid"], 1)
        self.assertEqual(result["rule"], "interview_url_package")

    def test_multiple_member_matches_narrowed_by_surname_to_exactly_one(self):
        url = "https://transcripts.cnn.com/show/xx/date/2022-01-01/segment/01"
        db_path = self._db([(1, "Alice Adams", "2022-01-01", "INTERVIEW", "xx", url, "Off-topic remark."),
                            (2, "Alice Adams", "2022-01-01", "INTERVIEW", "xx", url,
                             "On topic: Bob Baker is a friend.")])
        result = brv.match_local_speech("ev-1", [url], "Alice Adams", "Baker", db_path=db_path)
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["rowid"], 2)
        self.assertEqual(result["rule"], "interview_url_package+surname")

    def test_multiple_surname_hits_stay_ambiguous_with_the_narrowed_count(self):
        """The reported ambiguity count must be the surname-narrowed count,
        not the raw member-match count -- this is exactly what this task's
        own investigation found for cole_mcgovern_20190515 (6 raw Cole
        speeches that day, only 2 mentioning McGovern -> "ambiguous (2)",
        not "(6)") and mcgovern_cole_20200423 (17 raw, 3 mentioning Cole)."""
        pkg = "CREC-2022-01-01"
        url = "https://www.govinfo.gov/content/pkg/CREC-2022-01-01/pdf/CREC-2022-01-01-house.pdf"
        db_path = self._db([(1, "Alice Adams", "2022-01-01", "CREC", "house", pkg, "Mentions Baker once."),
                            (2, "Alice Adams", "2022-01-01", "CREC", "house", pkg, "Mentions Baker twice."),
                            (3, "Alice Adams", "2022-01-01", "CREC", "house", pkg, "Never mentions him.")])
        result = brv.match_local_speech("ev-1", [url], "Alice Adams", "Baker", db_path=db_path)
        self.assertEqual(result["status"], "ambiguous")
        self.assertEqual(result["candidate_count"], 2)

    def test_no_matching_member_row_is_missing(self):
        url = "https://transcripts.cnn.com/show/xx/date/2022-01-01/segment/01"
        db_path = self._db([(1, "Someone Else", "2022-01-01", "INTERVIEW", "xx", url, "text")])
        result = brv.match_local_speech("ev-1", [url], "Alice Adams", "Baker", db_path=db_path)
        self.assertEqual(result["status"], "missing")

    def test_unrecognized_source_url_is_missing_without_touching_the_db(self):
        # A nonexistent db_path would raise if this ever tried to query it;
        # classify_source_urls returning None must short-circuit first.
        result = brv.match_local_speech("ev-1", ["https://example.com/not-a-transcript"],
                                        "Alice Adams", "Baker",
                                        db_path=Path("Z:/does/not/exist.db"))
        self.assertEqual(result["status"], "missing")
        self.assertIn("no local copy", result["reason"])

    def test_explicit_content_mismatch_override_is_honoured(self):
        """A single syntactic candidate is not automatically accepted: this
        task's own investigation found `speeches` rowid 67697 -- the only
        Ocasio-Cortez row anywhere on this exact URL -- to be about Rep.
        Greene, not Fetterman, and rejected it explicitly rather than on
        syntax alone (RETEXT_REJECTED_MATCHES)."""
        url = "https://transcripts.cnn.com/show/sotu/date/2024-05-19/segment/01"
        db_path = self._db([(67697, "Alexandria Ocasio-Cortez", "2024-05-19", "INTERVIEW", "sotu", url,
                            "Unrelated remark about someone else entirely.")])
        result = brv.match_local_speech("anchor-aoc_fetterman_20240517-0", [url],
                                        "Alexandria Ocasio-Cortez", "Fetterman", db_path=db_path)
        self.assertEqual(result["status"], "missing")
        self.assertIn("content mismatch", result["reason"])


class ApplySupersessionTests(unittest.TestCase):
    def test_replacement_response_present_is_used_under_the_old_id(self):
        by_pass = {"A": {"old-1#retext": {"affinity": "3", "friction": "0"}},
                  "B": {"old-1#retext": {"affinity": "2", "friction": "1"}}}
        failures = [{"item_id": "old-1", "pass": "A", "reason": "missing_response"},
                   {"item_id": "old-1", "pass": "B", "reason": "missing_response"}]
        superseded = {"A": {"old-1": "old-1#retext"}, "B": {"old-1": "old-1#retext"}}
        eff_by_pass, eff_failures = brv.apply_supersession(by_pass, failures, superseded)
        self.assertEqual(eff_by_pass["A"]["old-1"], {"affinity": "3", "friction": "0"})
        self.assertEqual(eff_by_pass["B"]["old-1"], {"affinity": "2", "friction": "1"})
        self.assertNotIn("old-1#retext", eff_by_pass["A"])
        self.assertNotIn("old-1#retext", eff_by_pass["B"])
        self.assertEqual(eff_failures, [])

    def test_replacement_missing_becomes_a_single_no_text_packet_failure(self):
        by_pass = {"A": {}, "B": {}}
        failures = [{"item_id": "old-1", "pass": "A", "reason": "missing_response"},
                   {"item_id": "old-1#retext", "pass": "A", "reason": "missing_response"}]
        superseded = {"A": {"old-1": "old-1#retext"}, "B": {}}
        eff_by_pass, eff_failures = brv.apply_supersession(by_pass, failures, superseded)
        self.assertNotIn("old-1", eff_by_pass["A"])
        self.assertEqual(len(eff_failures), 1)
        self.assertEqual(eff_failures[0]["item_id"], "old-1")
        self.assertEqual(eff_failures[0]["reason"], "no_text_packet")

    def test_invalid_replacement_response_also_falls_back_to_no_text_packet(self):
        # A replacement whose response fails schema validation never lands in
        # by_pass (read_responses only populates by_pass with VALID
        # responses) -- it must still be reported, never silently dropped.
        by_pass = {"A": {}, "B": {}}
        failures = [{"item_id": "old-1#retext", "pass": "A", "reason": "schema_invalid"}]
        superseded = {"A": {"old-1": "old-1#retext"}, "B": {}}
        eff_by_pass, eff_failures = brv.apply_supersession(by_pass, failures, superseded)
        self.assertEqual(len(eff_failures), 1)
        self.assertEqual(eff_failures[0]["reason"], "no_text_packet")

    def test_non_superseded_items_pass_through_unchanged(self):
        by_pass = {"A": {"other-1": {"affinity": "1"}}, "B": {}}
        failures = [{"item_id": "other-2", "pass": "B", "reason": "missing_response"}]
        eff_by_pass, eff_failures = brv.apply_supersession(by_pass, failures, {})
        self.assertEqual(eff_by_pass, by_pass)
        self.assertEqual(eff_failures, failures)

    def test_empty_or_none_superseded_is_a_no_op(self):
        by_pass = {"A": {"x": {"affinity": "1"}}, "B": {}}
        failures = [{"item_id": "y", "pass": "A", "reason": "missing_response"}]
        for empty in ({}, None):
            eff_by_pass, eff_failures = brv.apply_supersession(by_pass, failures, empty)
            self.assertEqual(eff_by_pass, by_pass)
            self.assertEqual(eff_failures, failures)


class BuildKitRetextSyntheticTests(unittest.TestCase):
    def _seed_kit(self, root, existing_records, evidence_rows):
        records_path = write_ndjson_rows(root / "annotations.ndjson", existing_records)
        evidence_path = write_ndjson_rows(root / "reviewed_events.ndjson", evidence_rows)
        out_dir = root / "out"
        result = brv.build_kit(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                              log=lambda *_a: None)
        return records_path, evidence_path, out_dir, result

    def test_recovers_a_no_text_row_and_appends_additively(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        url = "https://transcripts.cnn.com/show/xx/date/2022-05-06/segment/03"
        rec = record("rec-notext", names=("Alice Adams", "Bob Baker"), evidence_ids=("ev-seen",))
        ev_no_text = evidence("ev-seen", extra={"text": None, "source_urls": [url]})
        records_path, evidence_path, out_dir, build_result = self._seed_kit(root, [rec], [ev_no_text])

        # Sanity: the seeded kit really does render "(no text)" for this row.
        prompt_a_path = (Path(build_result["kit_dir"]) / "prompts" / "A"
                        / (brv.safe_stem("rec-notext") + ".md"))
        before_bytes = prompt_a_path.read_text(encoding="utf-8")
        self.assertIn("(no text)", before_bytes)

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(555, "Alice Adams", "2022-05-06", "INTERVIEW", "xx", url,
                                        "It was good working with Bob Baker on this.")])

        before_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        before_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))

        result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                      log=lambda *_a: None, db_path=db_path,
                                      locator_path=root / "no_locator.ndjson",
                                      attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 1)
        self.assertEqual(result["new_items"], 2)
        self.assertEqual(sorted(result["new_batches"]),
                         ["regrade_retext__A__0001", "regrade_retext__B__0001"])
        self.assertTrue(result["sweep"]["ok"], result["sweep"]["hits"])

        # Existing entry/file completely untouched (additivity, byte-checked).
        self.assertEqual(prompt_a_path.read_text(encoding="utf-8"), before_bytes)
        after_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:len(before_index["items"])], before_index["items"])
        self.assertEqual(len(after_index["items"]), len(before_index["items"]) + 2)
        after_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])

        new_id = "rec-notext" + brv.RETEXT_ITEM_SUFFIX
        new_prompt = (Path(result["kit_dir"]) / "prompts" / "A"
                     / (brv.safe_stem(new_id) + ".md")).read_text(encoding="utf-8")
        self.assertIn("It was good working with Bob Baker on this.", new_prompt)
        self.assertNotIn("(no text)", new_prompt)
        self.assertNotIn("ORIGINAL_RATIONALE_MARKER", new_prompt)

        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["superseded"]["A"]["rec-notext"], new_id)
        self.assertEqual(manifest["superseded"]["B"]["rec-notext"], new_id)
        recovered_rows = [r for r in manifest["retext"]["rows"] if r["status"] == "recovered"]
        self.assertEqual(len(recovered_rows), 1)
        self.assertEqual(recovered_rows[0]["rowid"], 555)

    def test_ambiguous_or_unrecognized_rows_are_logged_but_not_retexted(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        rec_ambiguous = record("rec-ambiguous", actor="C000003", target="D000004",
                              names=("Carla Cole", "Dana Diaz"), evidence_ids=("ev-ambig",))
        rec_no_strategy = record("rec-nostrategy", actor="E000005", target="F000006",
                                names=("Erin Ellis", "Finn Ford"), evidence_ids=("ev-nostrat",))
        pkg = "CREC-2022-02-02"
        crec_url = "https://www.govinfo.gov/content/pkg/CREC-2022-02-02/pdf/CREC-2022-02-02-house.pdf"
        ev_ambiguous = evidence("ev-ambig", extra={"text": None, "source_urls": [crec_url]})
        ev_no_strategy = evidence("ev-nostrat",
                                  extra={"text": None, "source_urls": ["https://example.senate.gov/news"]})
        records_path, evidence_path, out_dir, _build = self._seed_kit(
            root, [rec_ambiguous, rec_no_strategy], [ev_ambiguous, ev_no_strategy])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [
            (1, "Carla Cole", "2022-02-02", "CREC", "house", pkg, "Mentions Diaz here."),
            (2, "Carla Cole", "2022-02-02", "CREC", "house", pkg, "Mentions Diaz again."),
        ])

        result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                      log=lambda *_a: None, db_path=db_path,
                                      locator_path=root / "no_locator.ndjson",
                                      attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 0)
        self.assertEqual(result["new_items"], 0)
        self.assertEqual(result["new_batches"], [])
        rows_by_record = {r["record_id"]: r for r in result["retext"]["rows"]}
        self.assertEqual(rows_by_record["rec-ambiguous"]["status"], "ambiguous")
        self.assertEqual(rows_by_record["rec-ambiguous"]["reason"], "ambiguous local candidates (2)")
        self.assertEqual(rows_by_record["rec-nostrategy"]["status"], "missing")
        self.assertIn("no local copy", rows_by_record["rec-nostrategy"]["reason"])


# ---------------------------------------------------------------------------
# --build-kit-retext: additive behaviour against a COPY of the real,
# currently-being-graded kit -- same discipline as
# BuildKitSupplementRealKitTests (never touches outputs/.../grading_kit
# itself; copies it into a temp dir first).
# ---------------------------------------------------------------------------

class BuildKitRetextRealKitTests(unittest.TestCase):
    def setUp(self):
        self.real_kit_dir = brv.DEFAULT_OUT / "grading_kit"
        if not self.real_kit_dir.exists():
            self.skipTest("no real grading_kit at %s" % self.real_kit_dir)

    def test_existing_entries_and_real_files_untouched_by_a_second_run(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = Path(tmp.name) / "out"
        shutil.copytree(self.real_kit_dir, out_dir / "grading_kit")

        before_index = json.loads((out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        before_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        before_manifest = json.loads(
            (out_dir / "grading_kit" / "manifest.json").read_text(encoding="utf-8"))
        n_before = len(before_index["items"])
        # prompt_path is an ABSOLUTE path baked in when the kit was originally
        # built, so these point at the REAL live kit, not this temp copy --
        # hashing them proves the real files graders are working from right
        # now are never opened for writing by this run.
        before_hashes = {it["prompt_path"]: bg.sha256_file(it["prompt_path"])
                         for it in before_index["items"]}
        rubric_text = brv.RUBRIC_PATH.read_text(encoding="utf-8")

        if "retext" in before_manifest:
            # This task's own one-time --build-kit-retext run already landed
            # on the live kit: every recoverable stem is already in this
            # copy's index.json, so re-running MUST be refused outright
            # rather than silently double-writing -- same regression guard
            # BuildKitSupplementRealKitTests already applies to
            # --build-kit-supplement.
            with self.assertRaises(brv.RegradeKitError):
                brv.build_kit_retext(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                     rubric_text, log=lambda *_a: None)
            return

        result = brv.build_kit_retext(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                      rubric_text, log=lambda *_a: None)
        after_index = json.loads((out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        after_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))

        self.assertEqual(after_index["items"][:n_before], before_index["items"])
        self.assertGreater(len(after_index["items"]), n_before)
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])
        for prompt_path, digest in before_hashes.items():
            self.assertEqual(bg.sha256_file(prompt_path), digest, prompt_path)
        print("\n[real-kit retext additive-behaviour check] records_retexted=%d new_items=%d "
             "new_batches=%s sweep_ok=%s"
             % (result["records_retexted"], result["new_items"], result["new_batches"],
                result["sweep"]["ok"]))


# ---------------------------------------------------------------------------
# --build-kit-retext-fetched
# ---------------------------------------------------------------------------

class SplitIntoParagraphsTests(unittest.TestCase):
    def test_splits_on_blank_lines_and_strips(self):
        text = "Para one line.\n\nPara two, two sentences. Still two.\n\n\nPara three."
        self.assertEqual(brv.split_into_paragraphs(text),
                         ["Para one line.", "Para two, two sentences. Still two.", "Para three."])

    def test_empty_or_missing_text(self):
        self.assertEqual(brv.split_into_paragraphs(""), [])
        self.assertEqual(brv.split_into_paragraphs(None), [])

    def test_single_paragraph_no_blank_line_is_kept_whole(self):
        text = "One sentence. Another sentence. A third."
        self.assertEqual(brv.split_into_paragraphs(text), [text])


class TrimEvidenceTextParagraphSplitterTests(unittest.TestCase):
    """Task step 2: the SAME trim_evidence_text rule (window/cap/marker),
    parameterised onto split_into_paragraphs/"\\n\\n" instead of the
    sentence default -- fetched web-page text (unlike `speeches.text`) has
    real blank-line paragraph breaks, the shape every fixture under
    fetched_sources/ actually has."""

    def test_keeps_whole_paragraph_even_when_the_hit_is_one_sentence_of_several(self):
        # Two filler paragraphs on each side of the hit: the +/-1 WINDOW must
        # keep only the immediately-adjacent filler, proving the unit being
        # windowed is the paragraph, not the sentence within it (unlike the
        # 3-paragraph case, this leaves something outside the window to cut).
        text = ("Far filler paragraph one, nothing relevant here at all.\n\n"
               "Near filler paragraph, directly before the hit.\n\n"
               "Opening line of the hit paragraph. Warren is named in the middle. "
               "A closing line with no name in it.\n\n"
               "Near filler paragraph, directly after the hit.\n\n"
               "Far filler paragraph two, also nothing relevant.")
        built, trimmed = brv.trim_evidence_text(text, ["Warren"],
                                                splitter=brv.split_into_paragraphs, joiner="\n\n")
        self.assertTrue(trimmed)
        self.assertIn("Opening line of the hit paragraph. Warren is named in the middle. "
                     "A closing line with no name in it.", built)
        self.assertIn("Near filler paragraph, directly before the hit.", built)
        self.assertIn("Near filler paragraph, directly after the hit.", built)
        self.assertNotIn("Far filler paragraph one", built)
        self.assertNotIn("Far filler paragraph two", built)

    def test_paragraphs_are_joined_with_blank_lines_not_spaces(self):
        text = "Alpha names Warren here.\n\nBravo also names Warren here."
        built, _trimmed = brv.trim_evidence_text(text, ["Warren"],
                                                  splitter=brv.split_into_paragraphs, joiner="\n\n")
        self.assertIn("Alpha names Warren here.\n\nBravo also names Warren here.", built)

    def test_default_splitter_and_joiner_are_unchanged_sentence_behaviour(self):
        # Regression guard: adding splitter/joiner params must not alter any
        # existing call site's behaviour -- every one calls this positionally
        # with just text/surnames, or with max_chars= only.
        text = ("Sentence one is filler. Sentence two is also filler. "
               "Sentence three mentions Warren directly. Sentence four is filler too.")
        built, trimmed = brv.trim_evidence_text(text, ["Warren"])
        self.assertTrue(trimmed)
        self.assertIn("Sentence three mentions Warren directly.", built)
        self.assertNotIn("\n\nSentence two", built)  # space-joined, not "\n\n"-joined


class ClassifyFetchedEntryTests(unittest.TestCase):
    def test_ok_true_and_plain_ok_status_is_usable(self):
        self.assertEqual(brv.classify_fetched_entry({"ok": True, "status_or_error": "ok"}),
                         "usable")

    def test_ok_true_but_summary_only_status_is_summary_only_not_usable(self):
        entry = {"ok": True, "status_or_error": "ok_summary_only: condensed by WebFetch"}
        self.assertEqual(brv.classify_fetched_entry(entry), "summary_only")

    def test_ok_false_excluded_pdf_prefix(self):
        entry = {"ok": False, "status_or_error": "excluded_pdf: is a PDF"}
        self.assertEqual(brv.classify_fetched_entry(entry), "excluded_pdf")

    def test_ok_false_failed_prefix(self):
        entry = {"ok": False, "status_or_error": "failed_blocked: HTTP 403"}
        self.assertEqual(brv.classify_fetched_entry(entry), "failed")

    def test_unrecognised_status_is_unknown(self):
        entry = {"ok": False, "status_or_error": "something_else"}
        self.assertEqual(brv.classify_fetched_entry(entry), "unknown")


def write_fetched_sources(kit_dir, entries, texts=None):
    """Seeds a synthetic grading_kit/fetched_sources/ directory: `entries`
    becomes index.json's own "entries" list (url/sha256/ok/status_or_error/
    evidence_ids/record_ids, exactly the fetch step's own shape); `texts`
    is {sha256: text} for entries that also get a saved <sha256>.txt (a
    real fetch step saves one for every "ok" entry, summary-only included
    -- a failed or excluded_pdf entry never gets one)."""
    fs_dir = Path(kit_dir) / "fetched_sources"
    fs_dir.mkdir(parents=True, exist_ok=True)
    for sha, text in (texts or {}).items():
        (fs_dir / ("%s.txt" % sha)).write_text(text, encoding="utf-8", newline="\n")
    bg.write_json(fs_dir / "index.json",
                 {"generated_at_utc": bg.utc_now(), "total_urls": len(entries),
                  "counts": {}, "entries": entries})
    return fs_dir


class MatchFetchedSourceTests(unittest.TestCase):
    def test_usable_entry_reads_the_saved_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kit_dir = Path(tmp.name) / "grading_kit"
        url = "https://example.com/article"
        write_fetched_sources(kit_dir, [{"url": url, "sha256": "abc123", "ok": True,
                                        "status_or_error": "ok", "evidence_ids": ["ev-1"],
                                        "record_ids": ["rec-1"]}],
                              {"abc123": "Paragraph text naming Warren."})
        fetched_by_url = brv.load_fetched_sources_index(kit_dir)
        result = brv.match_fetched_source([url], fetched_by_url, kit_dir)
        self.assertEqual(result["status"], "recovered")
        self.assertEqual(result["sha256"], "abc123")
        self.assertEqual(result["text"], "Paragraph text naming Warren.")

    def test_summary_only_entry_is_rejected_despite_having_saved_text(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kit_dir = Path(tmp.name) / "grading_kit"
        url = "https://transcripts.cnn.com/show/x/date/2020-01-01/segment/01"
        write_fetched_sources(kit_dir, [{"url": url, "sha256": "def456", "ok": True,
                                        "status_or_error": "ok_summary_only: condensed",
                                        "evidence_ids": [], "record_ids": []}],
                              {"def456": "A condensed summary, not a transcript."})
        fetched_by_url = brv.load_fetched_sources_index(kit_dir)
        result = brv.match_fetched_source([url], fetched_by_url, kit_dir)
        self.assertEqual(result["status"], "missing")
        self.assertIn("summary-only", result["reason"])

    def test_failed_entry_is_missing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kit_dir = Path(tmp.name) / "grading_kit"
        url = "https://www.c-span.org/program/x"
        write_fetched_sources(kit_dir, [{"url": url, "sha256": "ff00", "ok": False,
                                        "status_or_error": "failed_paywall: HTTP 402",
                                        "evidence_ids": [], "record_ids": []}])
        fetched_by_url = brv.load_fetched_sources_index(kit_dir)
        result = brv.match_fetched_source([url], fetched_by_url, kit_dir)
        self.assertEqual(result["status"], "missing")
        self.assertIn("fetch failed", result["reason"])

    def test_excluded_pdf_entry_is_missing(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        kit_dir = Path(tmp.name) / "grading_kit"
        url = "https://docs.house.gov/meetings/x.pdf"
        write_fetched_sources(kit_dir, [{"url": url, "sha256": "aa11", "ok": False,
                                        "status_or_error": "excluded_pdf: is a PDF",
                                        "evidence_ids": [], "record_ids": []}])
        fetched_by_url = brv.load_fetched_sources_index(kit_dir)
        result = brv.match_fetched_source([url], fetched_by_url, kit_dir)
        self.assertEqual(result["status"], "missing")
        self.assertIn("PDF", result["reason"])

    def test_url_absent_from_the_index_is_missing_without_touching_disk(self):
        result = brv.match_fetched_source(["https://example.com/never-fetched"], {},
                                          Path("Z:/does/not/exist"))
        self.assertEqual(result["status"], "missing")
        self.assertIn("no fetched-source entry", result["reason"])

    def test_no_source_urls_is_missing(self):
        result = brv.match_fetched_source(None, {}, Path("."))
        self.assertEqual(result["status"], "missing")


class BuildKitRetextFetchedSyntheticTests(unittest.TestCase):
    def _seed_kit(self, root, records, evidence_rows):
        records_path = write_ndjson_rows(root / "annotations.ndjson", records)
        evidence_path = write_ndjson_rows(root / "reviewed_events.ndjson", evidence_rows)
        out_dir = root / "out"
        result = brv.build_kit(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                              log=lambda *_a: None)
        return records_path, evidence_path, out_dir, result

    def test_recovers_from_a_fetched_page_continues_batch_numbering_and_skips_local_hits(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        # rec-local: retextable straight from a local speeches row (same shape
        # as BuildKitRetextSyntheticTests) -- this seeds a REAL
        # "regrade_retext__*__0001" batch pair for the fetched pass to
        # continue numbering from, exactly like the live kit.
        local_url = "https://transcripts.cnn.com/show/xx/date/2022-05-06/segment/03"
        rec_local = record("rec-local", names=("Alice Adams", "Bob Baker"),
                          evidence_ids=("ev-local",))
        ev_local = evidence("ev-local", extra={"text": None, "source_urls": [local_url]})

        # rec-fetched: NOT locally matchable (an ordinary news URL -- no local
        # speeches row could ever exist for it), but has a usable fetched page.
        fetched_url = "https://abcnews.example.com/story?id=1"
        rec_fetched = record("rec-fetched", actor="C000003", target="D000004",
                            names=("Carla Cole", "Dana Diaz"), evidence_ids=("ev-fetched",))
        ev_fetched = evidence("ev-fetched", extra={"text": None, "source_urls": [fetched_url]})

        records_path, evidence_path, out_dir, build_result = self._seed_kit(
            root, [rec_local, rec_fetched], [ev_local, ev_fetched])
        kit_dir = Path(build_result["kit_dir"])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(555, "Alice Adams", "2022-05-06", "INTERVIEW", "xx",
                                        local_url, "It was good working with Bob Baker on this.")])

        local_result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                            log=lambda *_a: None, db_path=db_path,
                                            locator_path=root / "no_locator.ndjson",
                                            attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(local_result["records_retexted"], 1)
        self.assertEqual(sorted(local_result["new_batches"]),
                         ["regrade_retext__A__0001", "regrade_retext__B__0001"])

        write_fetched_sources(
            kit_dir,
            [{"url": fetched_url, "sha256": "fe7c4ed", "ok": True, "status_or_error": "ok",
              "evidence_ids": ["ev-fetched"], "record_ids": ["rec-fetched"]}],
            {"fe7c4ed": (
                "Completely unrelated filler paragraph number one, far from the point.\n\n"
                "A second filler paragraph directly before the mention, still unrelated.\n\n"
                "Carla Cole said working with Dana Diaz on the bill was a pleasure.\n\n"
                "A filler paragraph directly after the mention, still unrelated.\n\n"
                "Completely unrelated filler paragraph number two, far from the point.")})

        before_index = json.loads(Path(local_result["index_path"]).read_text(encoding="utf-8"))
        before_batches = json.loads(Path(local_result["batches_path"]).read_text(encoding="utf-8"))
        local_prompt_path = (kit_dir / "prompts" / "A"
                            / (brv.safe_stem("rec-local" + brv.RETEXT_ITEM_SUFFIX) + ".md"))
        before_local_prompt = local_prompt_path.read_text(encoding="utf-8")

        result = brv.build_kit_retext_fetched(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                              log=lambda *_a: None, db_path=db_path,
                                              locator_path=root / "no_locator.ndjson",
                                              attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 1)
        self.assertEqual(result["new_items"], 2)
        self.assertEqual(sorted(result["new_batches"]),
                         ["regrade_retext__A__0002", "regrade_retext__B__0002"])
        self.assertTrue(result["sweep"]["ok"], result["sweep"]["hits"])

        # Additivity: the local pass's own batch/prompt/index footprint is
        # untouched (byte-checked for the prompt file).
        self.assertEqual(local_prompt_path.read_text(encoding="utf-8"), before_local_prompt)
        after_index = json.loads(Path(local_result["index_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:len(before_index["items"])], before_index["items"])
        self.assertEqual(len(after_index["items"]), len(before_index["items"]) + 2)
        after_batches = json.loads(Path(local_result["batches_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])

        new_id = "rec-fetched" + brv.RETEXT_ITEM_SUFFIX
        new_prompt = (kit_dir / "prompts" / "A" / (brv.safe_stem(new_id) + ".md")).read_text(
            encoding="utf-8")
        self.assertIn("Carla Cole said working with Dana Diaz on the bill was a pleasure.",
                     new_prompt)
        self.assertIn("A second filler paragraph directly before the mention", new_prompt)
        self.assertIn("A filler paragraph directly after the mention", new_prompt)
        self.assertNotIn("filler paragraph number one", new_prompt)
        self.assertNotIn("filler paragraph number two", new_prompt)
        self.assertNotIn("(no text)", new_prompt)
        self.assertNotIn("ORIGINAL_RATIONALE_MARKER", new_prompt)

        manifest = json.loads(Path(local_result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["superseded"]["A"]["rec-local"],
                         "rec-local" + brv.RETEXT_ITEM_SUFFIX)
        self.assertEqual(manifest["superseded"]["A"]["rec-fetched"], new_id)
        self.assertEqual(manifest["superseded"]["B"]["rec-fetched"], new_id)
        self.assertEqual(manifest["retext"]["records_checked"], 2)
        self.assertEqual(manifest["retext"]["records_retexted"], 2)

        # The local pass's own "missing" row for ev-fetched (it tried and
        # failed too, over a URL classify_source_urls never recognises)
        # stays on the record SIDE BY SIDE with this run's "recovered" row
        # -- neither ever overwrites the other.
        ev_fetched_rows = [r for r in manifest["retext"]["rows"] if r["evidence_id"] == "ev-fetched"]
        self.assertEqual(len(ev_fetched_rows), 2)
        self.assertEqual({r["status"] for r in ev_fetched_rows}, {"missing", "recovered"})
        recovered_row = next(r for r in ev_fetched_rows if r["status"] == "recovered")
        self.assertEqual(recovered_row["source_url"], fetched_url)
        self.assertEqual(recovered_row["sha256"], "fe7c4ed")
        self.assertTrue(recovered_row["trimmed"])

        # The OLD local-pass row for rec-local/ev-local is untouched.
        old_row = next(r for r in manifest["retext"]["rows"] if r["evidence_id"] == "ev-local")
        self.assertEqual(old_row["status"], "recovered")
        self.assertEqual(old_row["rowid"], 555)

    def test_summary_only_failed_pdf_and_unattempted_rows_are_logged_missing_not_retexted(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        rec_summary = record("rec-summary", actor="C000003", target="D000004",
                            names=("Carla Cole", "Dana Diaz"), evidence_ids=("ev-summary",))
        rec_failed = record("rec-failed", actor="E000005", target="F000006",
                           names=("Erin Ellis", "Finn Ford"), evidence_ids=("ev-failed",))
        rec_pdf = record("rec-pdf", actor="G000007", target="H000008",
                        names=("Gina Grant", "Hal Hunt"), evidence_ids=("ev-pdf",))
        rec_unattempted = record("rec-unattempted", actor="I000009", target="J000010",
                                names=("Ivy Irwin", "Jack Judd"), evidence_ids=("ev-unattempted",))
        url_summary = "https://transcripts.cnn.com/show/x/date/2020-01-01/segment/01"
        url_failed = "https://www.c-span.org/program/x"
        url_pdf = "https://docs.house.gov/meetings/x.pdf"
        url_unattempted = "https://example.senate.gov/news/never-fetched"
        ev_summary = evidence("ev-summary", extra={"text": None, "source_urls": [url_summary]})
        ev_failed = evidence("ev-failed", extra={"text": None, "source_urls": [url_failed]})
        ev_pdf = evidence("ev-pdf", extra={"text": None, "source_urls": [url_pdf]})
        ev_unattempted = evidence("ev-unattempted",
                                  extra={"text": None, "source_urls": [url_unattempted]})

        records_path, evidence_path, out_dir, build_result = self._seed_kit(
            root, [rec_summary, rec_failed, rec_pdf, rec_unattempted],
            [ev_summary, ev_failed, ev_pdf, ev_unattempted])
        kit_dir = Path(build_result["kit_dir"])

        write_fetched_sources(
            kit_dir,
            [{"url": url_summary, "sha256": "s1", "ok": True,
              "status_or_error": "ok_summary_only: condensed", "evidence_ids": ["ev-summary"],
              "record_ids": ["rec-summary"]},
             {"url": url_failed, "sha256": "f1", "ok": False,
              "status_or_error": "failed_blocked: HTTP 403", "evidence_ids": ["ev-failed"],
              "record_ids": ["rec-failed"]},
             {"url": url_pdf, "sha256": "p1", "ok": False,
              "status_or_error": "excluded_pdf: is a PDF", "evidence_ids": ["ev-pdf"],
              "record_ids": ["rec-pdf"]}],
            {"s1": "A condensed summary paragraph, not a transcript."})
        # url_unattempted deliberately has NO entry at all in the index.

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [])

        result = brv.build_kit_retext_fetched(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                              log=lambda *_a: None, db_path=db_path,
                                              locator_path=root / "no_locator.ndjson",
                                              attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 0)
        self.assertEqual(result["new_items"], 0)
        self.assertEqual(result["new_batches"], [])
        rows_by_record = {r["record_id"]: r for r in result["rows_this_run"]}
        self.assertEqual(rows_by_record["rec-summary"]["status"], "missing")
        self.assertIn("summary-only", rows_by_record["rec-summary"]["reason"])
        self.assertEqual(rows_by_record["rec-failed"]["status"], "missing")
        self.assertIn("fetch failed", rows_by_record["rec-failed"]["reason"])
        self.assertEqual(rows_by_record["rec-pdf"]["status"], "missing")
        self.assertIn("PDF", rows_by_record["rec-pdf"]["reason"])
        self.assertEqual(rows_by_record["rec-unattempted"]["status"], "missing")
        self.assertIn("no fetched-source entry", rows_by_record["rec-unattempted"]["reason"])

    def test_record_already_superseded_locally_is_never_reprocessed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        url = "https://transcripts.cnn.com/show/xx/date/2022-05-06/segment/03"
        rec = record("rec-notext", names=("Alice Adams", "Bob Baker"), evidence_ids=("ev-seen",))
        ev_no_text = evidence("ev-seen", extra={"text": None, "source_urls": [url]})
        records_path, evidence_path, out_dir, build_result = self._seed_kit(root, [rec],
                                                                            [ev_no_text])
        kit_dir = Path(build_result["kit_dir"])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(555, "Alice Adams", "2022-05-06", "INTERVIEW", "xx", url,
                                        "It was good working with Bob Baker on this.")])
        local_result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                            log=lambda *_a: None, db_path=db_path,
                                            locator_path=root / "no_locator.ndjson",
                                            attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(local_result["records_retexted"], 1)

        # Even though the SAME url is also "available" as a perfectly usable
        # fetched page, the record is already superseded locally, so it must
        # never be touched, retexted a second time, or double-counted.
        write_fetched_sources(
            kit_dir, [{"url": url, "sha256": "trap1", "ok": True, "status_or_error": "ok",
                      "evidence_ids": ["ev-seen"], "record_ids": ["rec-notext"]}],
            {"trap1": "This would also mention Bob Baker if it were ever read."})

        before_manifest = json.loads(
            Path(local_result["manifest_path"]).read_text(encoding="utf-8"))

        result = brv.build_kit_retext_fetched(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                              log=lambda *_a: None, db_path=db_path,
                                              locator_path=root / "no_locator.ndjson",
                                              attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(result["records_retexted"], 0)
        self.assertEqual(result["new_items"], 0)
        self.assertEqual(result["new_batches"], [])
        after_manifest = json.loads(
            Path(local_result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_manifest["superseded"], before_manifest["superseded"])
        self.assertEqual(after_manifest["retext"]["rows"], before_manifest["retext"]["rows"])


# ---------------------------------------------------------------------------
# --build-kit-retext-fetched: additive behaviour against a COPY of the real,
# currently-being-graded kit -- same discipline as BuildKitRetextRealKitTests.
# ---------------------------------------------------------------------------

class BuildKitRetextFetchedRealKitTests(unittest.TestCase):
    def setUp(self):
        self.real_kit_dir = brv.DEFAULT_OUT / "grading_kit"
        if not self.real_kit_dir.exists():
            self.skipTest("no real grading_kit at %s" % self.real_kit_dir)

    def test_existing_entries_and_real_files_untouched_and_idempotent_on_rerun(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = Path(tmp.name) / "out"
        shutil.copytree(self.real_kit_dir, out_dir / "grading_kit")

        before_index = json.loads(
            (out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        before_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        n_before = len(before_index["items"])
        # prompt_path is an ABSOLUTE path baked in when the kit was originally
        # built, so these point at the REAL live kit, not this temp copy --
        # hashing them proves the real files graders are working from right
        # now are never opened for writing by this run.
        before_hashes = {it["prompt_path"]: bg.sha256_file(it["prompt_path"])
                         for it in before_index["items"]}
        rubric_text = brv.RUBRIC_PATH.read_text(encoding="utf-8")

        result = brv.build_kit_retext_fetched(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                              rubric_text, log=lambda *_a: None)

        after_index = json.loads(
            (out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        after_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:n_before], before_index["items"])
        self.assertEqual(len(after_index["items"]), n_before + result["new_items"])
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])
        for prompt_path, digest in before_hashes.items():
            self.assertEqual(bg.sha256_file(prompt_path), digest, prompt_path)
        # The sweep is run and its result surfaced -- deliberately NOT
        # asserted clean here: forbidden_word_sweep's own docstring says it
        # reports a hit inside a verbatim evidence quote exactly like any
        # other hit, honestly, never exempting excerpts (unlike blind_
        # grading's assert_blind). Real fetched news/press-release text is
        # uncontrolled prose that can legitimately contain an ordinary word
        # ("party", "sign") that collides with this kit's forbidden-key
        # list; that is a reportable fact about the source text, not a
        # defect in this function. See BuildKitRetextRealKitTests above,
        # which likewise never asserts sweep-cleanliness against real kit
        # content.
        self.assertIn("hits", result["sweep"])
        if not result["sweep"]["ok"]:
            print("\n[real-kit retext-fetched sweep] HITS FOUND (reported, not asserted clean -- "
                 "see forbidden_word_sweep's docstring): %s"
                 % [(h["file"], h["words"]) for h in result["sweep"]["hits"]])

        # Re-running against the kit THIS run just updated must be a clean
        # no-op: every record it retexted is now in manifest["superseded"],
        # so the skip-filter alone prevents any collision or double-write --
        # unlike build_kit_retext's own local pass, which raises on a second
        # run (see BuildKitRetextRealKitTests above).
        second = brv.build_kit_retext_fetched(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                              rubric_text, log=lambda *_a: None)
        self.assertEqual(second["records_retexted"], 0)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(second["new_batches"], [])

        print("\n[real-kit retext-fetched additive-behaviour check] records_retexted=%d "
             "new_items=%d new_batches=%s sweep_ok=%s"
             % (result["records_retexted"], result["new_items"], result["new_batches"],
                result["sweep"]["ok"]))


# ---------------------------------------------------------------------------
# --build-kit-retext-pdf
# ---------------------------------------------------------------------------

def write_pdf_sources(kit_dir, entries, pages=None):
    """Seeds a synthetic grading_kit/fetched_sources/pdf/ directory:
    `entries` becomes pdf/index.json's own "entries" list (url/sha256/
    evidence_ids/record_ids/pages, the real fetch step's own shape);
    `pages` is {sha256: [{"page": int, "text": str}, ...]} for the
    matching <sha256>.pages.json sidecar."""
    pdf_dir = Path(kit_dir) / "fetched_sources" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    for sha, page_rows in (pages or {}).items():
        bg.write_json(pdf_dir / ("%s.pages.json" % sha), page_rows)
    bg.write_json(pdf_dir / "index.json",
                 {"generated_at_utc": bg.utc_now(), "total_urls": len(entries),
                  "ok_count": len(entries), "failed_count": 0, "entries": entries})
    return pdf_dir


def _window_ranges(windows):
    return [(w["start"], w["end"]) for w in windows]


class PdfCooccurrenceWindowTests(unittest.TestCase):
    """Task step 2: co-occurrence window selection on synthetic pages."""

    def test_same_paragraph_cooccurrence_is_one_window_with_context(self):
        units = [
            (1, "Far filler paragraph one, nothing relevant here at all."),
            (1, "Near filler paragraph, directly before the hit."),
            (1, "Mr. COLE and Mr. MCGOVERN spoke together on the floor today."),
            (1, "Near filler paragraph, directly after the hit."),
            (1, "Far filler paragraph two, also nothing relevant."),
        ]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(1, 3)])
        self.assertEqual(windows[0]["density"], 1)

    def test_adjacent_paragraph_cooccurrence_counts_as_one_window(self):
        units = [
            (1, "Filler before."),
            (1, "Mr. COLE reserved the balance of his time."),
            (1, "Mr. MCGOVERN thanked the gentleman for yielding."),
            (1, "Filler after."),
        ]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(0, 3)])
        # An adjacent-PAIR hit never contributes to density -- neither unit
        # in the pair names both surnames by itself.
        self.assertEqual(windows[0]["density"], 0)

    def test_case_insensitive_matching(self):
        # The record's own stored name-casing ("Cole") must still match a
        # PDF speaker attribution rendered in full capitals ("COLE") -- the
        # empirically-verified CREC convention this function exists for
        # (see build_kit_retext_pdf's module section header).
        units = [(9, "Mr. COLE and Mr. MCGOVERN discussed the rule.")]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(0, 0)])
        self.assertEqual(windows[0]["density"], 1)

    def test_two_separate_windows_are_counted_and_kept_independently(self):
        units = [
            (1, "Nothing relevant here."),
            (2, "Mr. COLE and Mr. MCGOVERN spoke first."),
            (3, "Middle filler paragraph one, unrelated to either."),
            (4, "Middle filler paragraph two, also unrelated."),
            (5, "Middle filler paragraph three, still unrelated."),
            (6, "Later, Mr. COLE and Mr. MCGOVERN spoke again."),
            (7, "Trailing filler."),
        ]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(0, 2), (4, 6)])
        self.assertEqual([w["density"] for w in windows], [1, 1])

    def test_higher_density_window_from_two_close_hits(self):
        units = [
            (1, "Nothing before."),
            (2, "Mr. COLE and Mr. MCGOVERN spoke first."),
            (3, "A short connecting line."),
            (4, "Mr. COLE and Mr. MCGOVERN spoke again immediately."),
            (5, "Filler after."),
        ]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(0, 4)])  # the two hits' contexts touch, merge
        self.assertEqual(windows[0]["density"], 2)

    def test_touching_expanded_windows_merge_into_one(self):
        # Two hits close enough that their own +/-1 context paragraphs meet
        # must count as ONE window, not two.
        units = [
            (1, "Mr. COLE and Mr. MCGOVERN spoke."),
            (1, "One paragraph of shared context."),
            (1, "Mr. MCGOVERN and Mr. COLE spoke again."),
        ]
        windows = brv.pdf_cooccurrence_windows(units, "Cole", "McGovern")
        self.assertEqual(_window_ranges(windows), [(0, 2)])
        self.assertEqual(windows[0]["density"], 2)

    def test_no_cooccurrence_returns_empty(self):
        units = [(1, "Mr. COLE spoke alone."), (1, "Ms. LEE spoke separately.")]
        self.assertEqual(brv.pdf_cooccurrence_windows(units, "Cole", "McGovern"), [])

    def test_empty_surname_returns_empty(self):
        units = [(1, "Mr. COLE and Mr. MCGOVERN spoke.")]
        self.assertEqual(brv.pdf_cooccurrence_windows(units, "", "McGovern"), [])
        self.assertEqual(brv.pdf_cooccurrence_windows(units, "Cole", ""), [])


class PdfActorSurnameFallbackTests(unittest.TestCase):
    def test_keeps_every_actor_only_paragraph_with_no_added_context(self):
        units = [
            (1, "Filler before, no name at all."),
            (1, "Mr. JEFFRIES took the floor to respond."),
            (1, "Filler after, no name at all."),
            (2, "Later, Mr. JEFFRIES returned to the point."),
        ]
        kept = brv.pdf_actor_surname_fallback(units, "Jeffries")
        self.assertEqual(kept, [1, 3])

    def test_case_insensitive(self):
        units = [(1, "Mr. JEFFRIES spoke.")]
        self.assertEqual(brv.pdf_actor_surname_fallback(units, "Jeffries"), [0])

    def test_empty_surname_or_no_match_returns_empty(self):
        units = [(1, "Nothing relevant.")]
        self.assertEqual(brv.pdf_actor_surname_fallback(units, ""), [])
        self.assertEqual(brv.pdf_actor_surname_fallback(units, "Jeffries"), [])


class BuildPdfEvidenceTextTests(unittest.TestCase):
    """Task step 2: the fallback path (fewer than 2 co-occurrence windows),
    and the density-ranked budget fill (coordinator follow-up: an early,
    thin window must never starve a later, denser one)."""

    def test_uses_cooccurrence_when_two_or_more_windows_exist(self):
        pages = [
            {"page": 1, "text": ("Filler paragraph one.\n\n"
                                 "Mr. COLE and Mr. MCGOVERN met first.\n\n"
                                 "Middle filler A.")},
            {"page": 2, "text": ("Middle filler B.\n\nMiddle filler C.\n\n"
                                 "Mr. COLE and Mr. MCGOVERN met again.\n\n"
                                 "Trailing filler.")},
        ]
        text, _trimmed, pages_used, used_fallback, rank_rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern")
        self.assertFalse(used_fallback)
        self.assertEqual(rank_rule, brv.RANK_RULE_DESCRIPTION)
        self.assertIn("Mr. COLE and Mr. MCGOVERN met first.", text)
        self.assertIn("Mr. COLE and Mr. MCGOVERN met again.", text)
        self.assertNotIn("Middle filler B.", text)
        self.assertEqual(pages_used, [1, 2])

    def test_falls_back_when_fewer_than_two_windows(self):
        # Exactly ONE co-occurrence window exists here -- per task
        # instruction that is still "fewer than 2", so the fallback
        # (actor-surname-only, no added context) is used instead, even
        # though a genuine co-occurrence hit exists. Ranking does not apply
        # to the fallback path, so rank_rule is None.
        pages = [{"page": 5, "text": ("Filler.\n\nMr. COMER and Mr. JEFFRIES clashed once.\n\n"
                                      "Unrelated filler.\n\nMr. JEFFRIES spoke again alone.")}]
        text, _trimmed, pages_used, used_fallback, rank_rule = brv.build_pdf_evidence_text(
            pages, "Jeffries", "Comer")
        self.assertTrue(used_fallback)
        self.assertIsNone(rank_rule)
        self.assertIn("Mr. COMER and Mr. JEFFRIES clashed once.", text)
        self.assertIn("Mr. JEFFRIES spoke again alone.", text)
        self.assertNotIn("Unrelated filler.", text)
        self.assertEqual(pages_used, [5])

    def test_records_page_numbers_actually_used(self):
        pages = [
            {"page": 10, "text": "Nothing before."},
            {"page": 11, "text": "Cole and McGovern spoke here first."},
            {"page": 12, "text": "Unrelated filler A."},
            {"page": 13, "text": "Unrelated filler B."},
            {"page": 14, "text": "Unrelated filler C."},
            {"page": 15, "text": "Cole and McGovern spoke here again, a second time."},
            {"page": 16, "text": "Nothing after."},
        ]
        _text, _trimmed, pages_used, used_fallback, _rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern")
        self.assertFalse(used_fallback)
        self.assertEqual(pages_used, [10, 11, 12, 14, 15, 16])

    def test_caps_at_max_chars_and_marks_trimmed(self):
        long_hit = "Mr. COLE and Mr. MCGOVERN spoke. " + ("Padding word. " * 500)
        pages = [{"page": 1, "text": long_hit}]
        text, trimmed, _pages_used, _fb, _rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern", max_chars=100)
        self.assertTrue(trimmed)
        self.assertTrue(text.endswith(brv.RETEXT_TRIM_MARKER))
        self.assertLessEqual(len(text) - len("\n\n" + brv.RETEXT_TRIM_MARKER), 100)

    def test_neither_rule_matches_anything_returns_empty(self):
        pages = [{"page": 1, "text": "Nobody relevant is mentioned here at all."}]
        text, trimmed, pages_used, _fb, rank_rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern")
        self.assertEqual(text, "")
        self.assertFalse(trimmed)
        self.assertEqual(pages_used, [])
        self.assertIsNone(rank_rule)

    def test_higher_density_window_wins_over_earlier_lower_density_window(self):
        # Window A (pages 1-3, density 1) comes FIRST in document order but
        # is the weaker signal; window B (pages 5-9, density 2) comes later
        # but is denser. A budget that can hold only one of the two whole
        # windows must keep B, not A -- the coordinator's fix for the
        # mcgovern_cole colloquy being starved by an earlier, thinner hit.
        pages = [
            {"page": 1, "text": "Nothing before."},
            {"page": 2, "text": "Mr. COLE and Mr. MCGOVERN spoke briefly."},
            {"page": 3, "text": "Unrelated filler A."},
            {"page": 4, "text": "Unrelated filler B."},
            {"page": 5, "text": "Unrelated filler C."},
            {"page": 6, "text": "Mr. COLE and Mr. MCGOVERN met again."},
            {"page": 7, "text": "A short connecting line."},
            {"page": 8, "text": "Mr. COLE and Mr. MCGOVERN spoke a third time."},
            {"page": 9, "text": "Filler after."},
        ]
        text, _trimmed, pages_used, used_fallback, rank_rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern", max_chars=160)
        self.assertFalse(used_fallback)
        self.assertEqual(rank_rule, brv.RANK_RULE_DESCRIPTION)
        self.assertIn("Mr. COLE and Mr. MCGOVERN met again.", text)
        self.assertIn("Mr. COLE and Mr. MCGOVERN spoke a third time.", text)
        self.assertNotIn("spoke briefly", text)
        self.assertEqual(pages_used[0], 5)

    def test_selected_windows_are_rendered_back_in_document_order(self):
        # Same fixture as above, but with room for BOTH windows: selection
        # is by rank, but the final text must still read in document order.
        pages = [
            {"page": 1, "text": "Nothing before."},
            {"page": 2, "text": "Mr. COLE and Mr. MCGOVERN spoke briefly."},
            {"page": 3, "text": "Unrelated filler A."},
            {"page": 4, "text": "Unrelated filler B."},
            {"page": 5, "text": "Unrelated filler C."},
            {"page": 6, "text": "Mr. COLE and Mr. MCGOVERN met again."},
            {"page": 7, "text": "A short connecting line."},
            {"page": 8, "text": "Mr. COLE and Mr. MCGOVERN spoke a third time."},
            {"page": 9, "text": "Filler after."},
        ]
        text, _trimmed, pages_used, used_fallback, _rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern")  # default max_chars=6000, both windows fit easily
        self.assertFalse(used_fallback)
        self.assertLess(text.index("spoke briefly"), text.index("met again"))
        self.assertEqual(pages_used, [1, 2, 3, 5, 6, 7, 8, 9])

    def test_top_ranked_window_bigger_than_the_whole_budget_is_truncated_not_dropped(self):
        # Regression for the real v6:anchor-mcgovern_cole_20200423-0 case:
        # skip-if-it-doesn't-fit-whole landed on an early, low-density
        # window while the actual density-2 Cole/McGovern exchange (bigger
        # than the whole budget by itself) was dropped outright. The
        # highest-ranked (density 2) window here is deliberately bigger
        # than max_chars alone; it must still be the one included
        # (truncated), never abandoned for the smaller, earlier,
        # density-1 window on page 1.
        dense_hit = "Mr. COLE and Mr. MCGOVERN discussed the matter directly. "
        pages = [
            {"page": 1, "text": "Mr. COLE and Mr. MCGOVERN spoke briefly."},  # density-1 window
            {"page": 2, "text": "Filler A."},
            {"page": 3, "text": "Filler B."},
            {"page": 4, "text": "Filler C."},          # context paragraph for the dense window
            {"page": 5, "text": dense_hit * 20},        # density contributor, ~1.2k chars alone
            {"page": 6, "text": dense_hit * 20},        # adjacent density contributor, merges in
        ]
        text, trimmed, pages_used, used_fallback, rank_rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern", max_chars=1500)
        self.assertFalse(used_fallback)
        self.assertEqual(rank_rule, brv.RANK_RULE_DESCRIPTION)
        self.assertTrue(trimmed)
        self.assertIn("Mr. COLE and Mr. MCGOVERN discussed the matter directly.", text)
        self.assertNotIn("spoke briefly", text)  # the smaller, earlier window is dropped, not kept
        self.assertEqual(pages_used, [4, 5])
        self.assertLessEqual(len(text), 1500 + len("\n\n" + brv.RETEXT_TRIM_MARKER))

    def test_smaller_lower_ranked_window_fills_space_a_bigger_one_left_unused(self):
        # Window B (density 2, larger) is tried first and fits; window A
        # (density 1, smaller) is tried next and STILL fits in what's left
        # -- a lower-ranked window is never skipped just because a
        # higher-ranked one already claimed some of the budget.
        pages = [
            {"page": 1, "text": "Mr. COLE and Mr. MCGOVERN spoke briefly."},
            {"page": 2, "text": "Unrelated filler A."},
            {"page": 3, "text": "Unrelated filler B."},
            {"page": 4, "text": "Unrelated filler C."},
            {"page": 5, "text": "Mr. COLE and Mr. MCGOVERN met again."},
            {"page": 6, "text": "A short connecting line."},
            {"page": 7, "text": "Mr. COLE and Mr. MCGOVERN spoke a third time."},
        ]
        text, _trimmed, _pages_used, used_fallback, _rule = brv.build_pdf_evidence_text(
            pages, "Cole", "McGovern", max_chars=6000)
        self.assertFalse(used_fallback)
        self.assertIn("spoke briefly", text)
        self.assertIn("met again", text)


class BuildKitRetextPdfSyntheticTests(unittest.TestCase):
    def _seed_kit(self, root, records, evidence_rows):
        records_path = write_ndjson_rows(root / "annotations.ndjson", records)
        evidence_path = write_ndjson_rows(root / "reviewed_events.ndjson", evidence_rows)
        out_dir = root / "out"
        result = brv.build_kit(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                              log=lambda *_a: None)
        return records_path, evidence_path, out_dir, result

    def test_recovers_via_cooccurrence_and_appends_additively(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        pdf_url = "https://www.govinfo.gov/content/pkg/CREC-2022-06-07/pdf/CREC-2022-06-07-house.pdf"
        rec = record("rec-pdf", names=("Carla Cole", "Dana Diaz"), evidence_ids=("ev-pdf",))
        ev_pdf = evidence("ev-pdf", extra={"text": None, "source_urls": [pdf_url]})
        records_path, evidence_path, out_dir, build_result = self._seed_kit(root, [rec], [ev_pdf])
        kit_dir = Path(build_result["kit_dir"])

        prompt_a_path = kit_dir / "prompts" / "A" / (brv.safe_stem("rec-pdf") + ".md")
        before_bytes = prompt_a_path.read_text(encoding="utf-8")
        self.assertIn("(no text)", before_bytes)

        write_pdf_sources(
            kit_dir,
            [{"url": pdf_url, "sha256": "pdfsha1", "evidence_ids": ["ev-pdf"],
              "record_ids": ["rec-pdf"], "ok": True, "pages": 2}],
            {"pdfsha1": [
                {"page": 1, "text": ("Filler paragraph one.\n\n"
                                     "Carla Cole and Dana Diaz met first.\n\nMiddle filler A.")},
                {"page": 2, "text": ("Middle filler B.\n\nMiddle filler C.\n\n"
                                     "Carla Cole and Dana Diaz met again.\n\nTrailing filler.")},
            ]})

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [])
        before_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        before_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))

        result = brv.build_kit_retext_pdf(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                          log=lambda *_a: None, db_path=db_path,
                                          locator_path=root / "no_locator.ndjson",
                                          attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 1)
        self.assertEqual(result["new_items"], 2)
        self.assertEqual(sorted(result["new_batches"]),
                         ["regrade_retext__A__0001", "regrade_retext__B__0001"])
        self.assertTrue(result["sweep"]["ok"], result["sweep"]["hits"])

        # Additivity: the original item/file untouched, byte-checked.
        self.assertEqual(prompt_a_path.read_text(encoding="utf-8"), before_bytes)
        after_index = json.loads(Path(build_result["index_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:len(before_index["items"])], before_index["items"])
        self.assertEqual(len(after_index["items"]), len(before_index["items"]) + 2)
        after_batches = json.loads(Path(build_result["batches_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])

        new_id = "rec-pdf" + brv.RETEXT_ITEM_SUFFIX
        new_prompt = (kit_dir / "prompts" / "A" / (brv.safe_stem(new_id) + ".md")).read_text(
            encoding="utf-8")
        self.assertIn("Carla Cole and Dana Diaz met first.", new_prompt)
        self.assertIn("Carla Cole and Dana Diaz met again.", new_prompt)
        self.assertNotIn("Middle filler B.", new_prompt)
        self.assertNotIn("(no text)", new_prompt)
        self.assertNotIn("ORIGINAL_RATIONALE_MARKER", new_prompt)

        manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(manifest["superseded"]["A"]["rec-pdf"], new_id)
        self.assertEqual(manifest["superseded"]["B"]["rec-pdf"], new_id)
        recovered_row = next(r for r in manifest["retext"]["rows"] if r["status"] == "recovered")
        self.assertEqual(recovered_row["source"], "pdf")
        self.assertEqual(recovered_row["sha256"], "pdfsha1")
        self.assertEqual(recovered_row["pages"], [1, 2])
        self.assertFalse(recovered_row["used_fallback"])
        self.assertEqual(recovered_row["rank_rule"], brv.RANK_RULE_DESCRIPTION)

    def test_record_already_superseded_by_local_pass_is_never_reprocessed(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        local_url = "https://transcripts.cnn.com/show/xx/date/2022-05-06/segment/03"
        rec = record("rec-notext", names=("Alice Adams", "Bob Baker"), evidence_ids=("ev-seen",))
        ev_no_text = evidence("ev-seen", extra={"text": None, "source_urls": [local_url]})
        records_path, evidence_path, out_dir, build_result = self._seed_kit(root, [rec],
                                                                            [ev_no_text])
        kit_dir = Path(build_result["kit_dir"])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(555, "Alice Adams", "2022-05-06", "INTERVIEW", "xx",
                                        local_url, "It was good working with Bob Baker on this.")])
        local_result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                            log=lambda *_a: None, db_path=db_path,
                                            locator_path=root / "no_locator.ndjson",
                                            attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(local_result["records_retexted"], 1)

        # A PDF is also "available" for the exact same evidence_id, but the
        # record is already superseded locally, so it must never be touched.
        write_pdf_sources(
            kit_dir, [{"url": local_url, "sha256": "trap1", "evidence_ids": ["ev-seen"],
                      "record_ids": ["rec-notext"], "ok": True, "pages": 1}],
            {"trap1": [{"page": 1, "text": "This would also mention Bob Baker and Alice Adams."}]})

        before_manifest = json.loads(
            Path(local_result["manifest_path"]).read_text(encoding="utf-8"))
        result = brv.build_kit_retext_pdf(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                          log=lambda *_a: None, db_path=db_path,
                                          locator_path=root / "no_locator.ndjson",
                                          attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(result["records_retexted"], 0)
        self.assertEqual(result["new_items"], 0)
        self.assertEqual(result["new_batches"], [])
        after_manifest = json.loads(
            Path(local_result["manifest_path"]).read_text(encoding="utf-8"))
        self.assertEqual(after_manifest["superseded"], before_manifest["superseded"])

    def test_pdf_available_recorded_for_untouched_pdf_cited_records_only(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)

        # rec-target: gets a NEW packet this run (a genuine 2-window hit).
        target_url = "https://www.govinfo.gov/content/pkg/CREC-2022-06-07/pdf/CREC-2022-06-07-house.pdf"
        rec_target = record("rec-target", names=("Carla Cole", "Dana Diaz"),
                           evidence_ids=("ev-target",))
        ev_target = evidence("ev-target", extra={"text": None, "source_urls": [target_url]})

        # rec-sibling: shares rec-target's SAME PDF (same sha) but is left on
        # its own already-recovered (non-PDF) replacement text -- must get NO
        # pdf_available note, since that PDF was "touched" this run via its
        # sibling row.
        sibling_url = "https://transcripts.cnn.com/show/yy/date/2022-01-01/segment/02"
        rec_sibling = record("rec-sibling", actor="E000005", target="F000006",
                            names=("Erin Ellis", "Finn Ford"), evidence_ids=("ev-sibling",))
        ev_sibling = evidence("ev-sibling", extra={"text": None, "source_urls": [sibling_url]})

        # rec-other: PDF-cited, untouched this run, and its PDF text never
        # names its actor's surname either -- stays "missing" and gets
        # exactly one pdf_available note.
        other_url = "https://www.govinfo.gov/content/pkg/CREC-2022-08-01/pdf/CREC-2022-08-01-house.pdf"
        rec_other = record("rec-other", actor="G000007", target="H000008",
                          names=("Gina Grant", "Hal Hunt"), evidence_ids=("ev-other",))
        ev_other = evidence("ev-other", extra={"text": None, "source_urls": [other_url]})

        records_path, evidence_path, out_dir, build_result = self._seed_kit(
            root, [rec_target, rec_sibling, rec_other], [ev_target, ev_sibling, ev_other])
        kit_dir = Path(build_result["kit_dir"])

        db_path = root / "fake_social_media.db"
        make_fake_speeches_db(db_path, [(9001, "Erin Ellis", "2022-01-01", "INTERVIEW", "yy",
                                        sibling_url,
                                        "Erin Ellis said Finn Ford was a good partner.")])
        local_result = brv.build_kit_retext(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                            log=lambda *_a: None, db_path=db_path,
                                            locator_path=root / "no_locator.ndjson",
                                            attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(local_result["records_retexted"], 1)  # rec-sibling only

        write_pdf_sources(
            kit_dir,
            [{"url": target_url, "sha256": "shaTARGET",
              "evidence_ids": ["ev-target", "ev-sibling"],
              "record_ids": ["rec-target", "rec-sibling"], "ok": True, "pages": 2},
             {"url": other_url, "sha256": "shaOTHER", "evidence_ids": ["ev-other"],
              "record_ids": ["rec-other"], "ok": True, "pages": 5}],
            {"shaTARGET": [
                {"page": 1, "text": "Filler.\n\nCarla Cole and Dana Diaz met first.\n\nMiddle A."},
                {"page": 2, "text": ("Middle B.\n\nMiddle C.\n\n"
                                     "Carla Cole and Dana Diaz met again.\n\nEnd.")}],
             "shaOTHER": [{"page": 1, "text": "Nobody relevant is named on this page at all."}]})

        result = brv.build_kit_retext_pdf(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                          log=lambda *_a: None, db_path=db_path,
                                          locator_path=root / "no_locator.ndjson",
                                          attribution_path=root / "no_attribution.ndjson")

        self.assertEqual(result["records_retexted"], 1)  # rec-target only
        pdf_available_ids = {e["record_id"] for e in result["pdf_available"]}
        self.assertEqual(pdf_available_ids, {"rec-other"})
        other_entry = next(e for e in result["pdf_available"] if e["record_id"] == "rec-other")
        self.assertEqual(other_entry["sha256"], "shaOTHER")
        self.assertEqual(other_entry["pages"], 5)

        # Idempotent: a second run adds no duplicate pdf_available entries
        # and retexts nothing further.
        result2 = brv.build_kit_retext_pdf(out_dir, records_path, evidence_path, FAKE_RUBRIC,
                                           log=lambda *_a: None, db_path=db_path,
                                           locator_path=root / "no_locator.ndjson",
                                           attribution_path=root / "no_attribution.ndjson")
        self.assertEqual(result2["records_retexted"], 0)
        self.assertEqual({e["record_id"] for e in result2["pdf_available"]}, {"rec-other"})


# ---------------------------------------------------------------------------
# --build-kit-retext-pdf: additive behaviour against a COPY of the real,
# currently-being-graded kit -- same discipline as
# BuildKitRetextFetchedRealKitTests.
# ---------------------------------------------------------------------------

class BuildKitRetextPdfRealKitTests(unittest.TestCase):
    def setUp(self):
        self.real_kit_dir = brv.DEFAULT_OUT / "grading_kit"
        if not self.real_kit_dir.exists():
            self.skipTest("no real grading_kit at %s" % self.real_kit_dir)

    def test_existing_entries_and_real_files_untouched_and_idempotent_on_rerun(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        out_dir = Path(tmp.name) / "out"
        shutil.copytree(self.real_kit_dir, out_dir / "grading_kit")

        before_index = json.loads(
            (out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        before_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        n_before = len(before_index["items"])
        # prompt_path is an ABSOLUTE path baked in when the kit was originally
        # built, so these point at the REAL live kit, not this temp copy --
        # hashing them proves the real files graders are working from right
        # now are never opened for writing by this run.
        before_hashes = {it["prompt_path"]: bg.sha256_file(it["prompt_path"])
                         for it in before_index["items"]}
        rubric_text = brv.RUBRIC_PATH.read_text(encoding="utf-8")

        result = brv.build_kit_retext_pdf(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                          rubric_text, log=lambda *_a: None)

        after_index = json.loads(
            (out_dir / "grading_kit" / "index.json").read_text(encoding="utf-8"))
        after_batches = json.loads(
            (out_dir / "grading_kit" / "batches.json").read_text(encoding="utf-8"))
        self.assertEqual(after_index["items"][:n_before], before_index["items"])
        self.assertEqual(len(after_index["items"]), n_before + result["new_items"])
        self.assertEqual(after_batches["batches"][:len(before_batches["batches"])],
                         before_batches["batches"])
        for prompt_path, digest in before_hashes.items():
            self.assertEqual(bg.sha256_file(prompt_path), digest, prompt_path)

        second = brv.build_kit_retext_pdf(out_dir, brv.DEFAULT_RECORDS, brv.DEFAULT_EVIDENCE,
                                          rubric_text, log=lambda *_a: None)
        self.assertEqual(second["records_retexted"], 0)
        self.assertEqual(second["new_items"], 0)
        self.assertEqual(second["new_batches"], [])
        self.assertEqual(second["pdf_available"], result["pdf_available"])

        print("\n[real-kit retext-pdf additive-behaviour check] records_retexted=%d new_items=%d "
             "new_batches=%s pdf_available=%d sweep_ok=%s"
             % (result["records_retexted"], result["new_items"], result["new_batches"],
                len(result["pdf_available"]), result["sweep"]["ok"]))
        for row in result["rows_this_run"]:
            if row["status"] == "recovered":
                print("  recovered %s / %s: pages=%s chars=%d trimmed=%s used_fallback=%s"
                     % (row["record_id"], row["evidence_id"], row["pages"], row["chars"],
                        row["trimmed"], row["used_fallback"]))
        for b in after_batches["batches"]:
            if b["batch_id"] in result["new_batches"]:
                print("  batch %s: %d items" % (b["batch_id"], b["item_count"]))
        for e in result["pdf_available"]:
            print("  pdf_available: %s (evidence_id=%s sha256=%s pages=%s)"
                 % (e["record_id"], e["evidence_id"], e["sha256"], e["pages"]))
        if not result["sweep"]["ok"]:
            print("  sweep HITS: %s" % [(h["file"], h["words"]) for h in result["sweep"]["hits"]])


# ---------------------------------------------------------------------------
# classify_final_packets / _retext_source_class: coordinator follow-up --
# a PDF-retexted record must be classed "retext_pdf_page" in the --ingest
# evidence-class report, not misread as "retext_fetched_web" by the batch-id
# sniffing this replaces.
# ---------------------------------------------------------------------------

class RetextSourceClassTests(unittest.TestCase):
    def test_local_speechdb_row_shape(self):
        row = {"status": "recovered", "rule": "crec_date_member", "rowid": 5968, "chars": 10}
        self.assertEqual(brv._retext_source_class(row), "retext_local_speechdb")

    def test_pdf_row_shape(self):
        row = {"status": "recovered", "source": "pdf", "sha256": "abc", "pages": [1],
              "chars": 10}
        self.assertEqual(brv._retext_source_class(row), "retext_pdf_page")

    def test_fetched_web_row_shape(self):
        row = {"status": "recovered", "source_url": "https://example.com/x", "sha256": "abc",
              "chars": 10}
        self.assertEqual(brv._retext_source_class(row), "retext_fetched_web")

    def test_unrecognised_shape_returns_none(self):
        self.assertIsNone(brv._retext_source_class({"status": "recovered", "chars": 10}))


class ClassifyFinalPacketsTests(unittest.TestCase):
    def _write_kit(self, root, manifest_extra):
        kit_dir = root / "grading_kit"
        kit_dir.mkdir(parents=True, exist_ok=True)
        manifest = {"evidence_missing_in_repo": [], "superseded": {"A": {}, "B": {}},
                   "retext": {"records_checked": 0, "records_retexted": 0, "rows": []}}
        manifest.update(manifest_extra)
        bg.write_json(kit_dir / "manifest.json", manifest)
        bg.write_json(kit_dir / "batches.json", {"meta": {}, "batches": []})
        return kit_dir

    def test_distinguishes_all_three_retext_sources_by_row_shape(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        kit_dir = self._write_kit(root, {
            "superseded": {"A": {"rec-local": "rec-local#retext", "rec-pdf": "rec-pdf#retext",
                                 "rec-web": "rec-web#retext"},
                          "B": {}},
            "retext": {"records_checked": 3, "records_retexted": 3, "rows": [
                {"record_id": "rec-local", "evidence_id": "ev-local", "status": "recovered",
                 "rule": "crec_date_member", "rowid": 1, "chars": 5},
                {"record_id": "rec-pdf", "evidence_id": "ev-pdf", "status": "recovered",
                 "source": "pdf", "sha256": "s1", "pages": [1], "chars": 5},
                {"record_id": "rec-web", "evidence_id": "ev-web", "status": "recovered",
                 "source_url": "https://example.com/x", "sha256": "s2", "chars": 5},
            ]}})
        classes = brv.classify_final_packets(kit_dir, ["rec-local", "rec-pdf", "rec-web"])
        self.assertEqual(classes, {"rec-local": "retext_local_speechdb",
                                   "rec-pdf": "retext_pdf_page",
                                   "rec-web": "retext_fetched_web"})

    def test_never_superseded_but_checked_is_no_text_available(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        kit_dir = self._write_kit(root, {"retext": {"records_checked": 1, "records_retexted": 0,
                                                    "rows": [{"record_id": "rec-missing",
                                                             "evidence_id": "ev-x",
                                                             "status": "missing",
                                                             "reason": "no local copy"}]}})
        classes = brv.classify_final_packets(kit_dir, ["rec-missing"])
        self.assertEqual(classes, {"rec-missing": "no_text_available"})

    def test_supplement_and_verbatim_classes(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        kit_dir = self._write_kit(root, {"evidence_missing_in_repo": [
            {"record_id": "rec-supplement", "evidence_ids": [], "source_urls": [],
             "unresolved_evidence_ids": []}]})
        classes = brv.classify_final_packets(kit_dir, ["rec-supplement", "rec-plain"])
        self.assertEqual(classes, {"rec-supplement": "supplement_recovered",
                                   "rec-plain": "verbatim_reviewed_events"})

    def test_pdf_class_is_covered_by_evidence_class_rows(self):
        rows, unclassified = brv.evidence_class_rows(
            {"rec-pdf": "retext_pdf_page"}, ["rec-pdf"], {}, {})
        self.assertEqual(unclassified, [])
        pdf_row = next(r for r in rows if r["class"] == "retext_pdf_page")
        self.assertEqual(pdf_row["n_records"], 1)


if __name__ == "__main__":
    unittest.main()
