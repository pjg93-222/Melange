"""Regression coverage for stable Senate identities and safe correction outputs."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import sys; sys.path.insert(0, str(Path(__file__).resolve().parents[3]))  # repo root: run_tests runs this as plain `python <path>`
from fec.members.b5_gold_identity import map_gold, map_gold_with_receipt, roster_records
from fec.members.b5_gold_identity_registry import APPENDIX_PDF_SHA256, SOURCE_NAME_TO_BIOGUIDE
from fec.members import b5_external_gold_validate as external


def gold(*names):
    return {
        "schema": "big5-senate-expert-gold-v1", "status": "FROZEN_EXTERNAL_GOLD",
        "source": {"pdf_sha256": APPENDIX_PDF_SHA256},
        "records": [{"panel": "senate_insiders", "source_name": name,
                     "ratings_n": 2, "O": 4.0} for name in names],
    }


def member(name, bioguide, chamber="Senate"):
    return {"member": name, "bioguide": bioguide, "chamber": chamber}


class StableGoldIdentityTests(unittest.TestCase):
    def test_menendez_son_never_inherits_fathers_ratings(self):
        panels, unmatched, receipt = map_gold_with_receipt(
            gold("Menendez, Robert"), [member("Robert Menendez", "M001226", "House")])
        self.assertEqual({}, panels["senate_insiders"])
        self.assertEqual(["Menendez, Robert"], unmatched)
        self.assertEqual("M000639", receipt["excluded"][0]["bioguide"])
        self.assertEqual("not_on_current_roster", receipt["excluded"][0]["reason"])

    def test_same_name_and_chamber_cannot_override_stable_id(self):
        panels, _ = map_gold(gold("Menendez, Robert"), [member("Robert Menendez", "M001226")])
        self.assertEqual({}, panels["senate_insiders"])

    def test_real_identity_can_have_a_new_display_name(self):
        panels, unmatched = map_gold(
            gold("Sanders, Bernard"), [member("Bernie Sanders", "S000033")])
        self.assertEqual([], unmatched)
        self.assertEqual("S000033", panels["senate_insiders"]["Bernie Sanders"]["bioguide"])

    def test_historic_senator_must_still_be_current_senator(self):
        panels, _, receipt = map_gold_with_receipt(
            gold("Menendez, Robert"), [member("Bob Menendez", "M000639", "House")])
        self.assertEqual({}, panels["senate_insiders"])
        self.assertEqual("not_current_senator", receipt["excluded"][0]["reason"])

    def test_name_only_roster_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "name-only"):
            map_gold(gold("Cantwell, Maria"), ["Maria Cantwell"])

    def test_missing_identity_or_chamber_fails_closed(self):
        for row in [{"member": "Maria Cantwell", "chamber": "Senate"},
                    {"member": "Maria Cantwell", "bioguide": "C000127"}]:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "incomplete"):
                roster_records([row])

    def test_duplicate_current_id_or_name_fails_closed(self):
        for rows in [[member("Maria Cantwell", "C000127"), member("Maria C.", "C000127")],
                     [member("Maria Cantwell", "C000127"), member("Maria Cantwell", "C000128")]]:
            with self.subTest(rows=rows), self.assertRaisesRegex(ValueError, "duplicate"):
                roster_records(rows)

    def test_unknown_historic_identity_is_excluded_even_when_name_matches(self):
        panels, _, receipt = map_gold_with_receipt(
            gold("Example, Senator"), [member("Senator Example", "E000001")])
        self.assertEqual({}, panels["senate_insiders"])
        self.assertEqual("unregistered_historic_identity", receipt["excluded"][0]["reason"])

    def test_changed_appendix_requires_reviewed_registry(self):
        data = gold("Cantwell, Maria")
        data["source"]["pdf_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "not the source pinned"):
            map_gold(data, [member("Maria Cantwell", "C000127")])

    def test_gold_identity_conflict_is_not_silently_overwritten(self):
        data = gold("Menendez, Robert")
        data["records"][0]["bioguide"] = "M001226"
        with self.assertRaisesRegex(ValueError, "disagrees"):
            map_gold(data, [member("Robert Menendez", "M001226", "House")])

    def test_aliases_cannot_double_count_one_identity_in_one_panel(self):
        with self.assertRaisesRegex(ValueError, "duplicate gold panel identity"):
            map_gold(gold("Bond, Christopher", "Bond, Christopher S."),
                     [member("Kit Bond", "B000611")])

    def test_matching_preserves_source_values_and_does_not_mutate_inputs(self):
        data = gold("Cantwell, Maria")
        before = copy.deepcopy(data)
        panels, _, receipt = map_gold_with_receipt(
            data, {"members": [member("Maria Cantwell", "C000127")]})
        self.assertEqual(before, data)
        self.assertEqual(4.0, panels["senate_insiders"]["Maria Cantwell"]["O"])
        self.assertEqual(2, panels["senate_insiders"]["Maria Cantwell"]["ratings_n"])
        self.assertEqual(64, len(receipt["registry_sha256"]))


class ExternalCorrectionOutputTests(unittest.TestCase):
    def test_correction_writes_only_explicit_output_and_filters_departed_inputs(self):
        source_names = ["Cantwell, Maria", "Collins, Susan M.", "Warren, Elizabeth",
                        "Murkowski, Lisa", "Baldwin, Tammy", "Klobuchar, Amy"]
        current = [member("Senator %s" % i, SOURCE_NAME_TO_BIOGUIDE[name])
                   for i, name in enumerate(source_names)]
        data = gold()
        data["records"] = [
            {"panel": panel, "source_name": name, "ratings_n": 2,
             **{trait: float(i + 1) for trait in external.TRAITS}}
            for panel in ("senate_insiders", "academic_experts")
            for i, name in enumerate(source_names)
        ]
        blue = {row["member"]: {"E": i + 1} for i, row in enumerate(current)}
        pink = {row["member"]: {"n_chunks": 2, "raw_z": {"E": i + 1}}
                for i, row in enumerate(current)}
        blue["Departed person"] = {"E": 100000}
        pink["Departed person"] = {"n_chunks": 2, "raw_z": {"E": 100000}}
        documents = {external.GOLD: data, external.BLUE: {"traits": blue},
                     external.PINK: {"traits": pink}, external.ROSTER: {"members": current},
                     external.DISPOSITIONS: {"members": {}}, external.STYLE: {"members": {}}}
        with tempfile.TemporaryDirectory() as tmp:
            writes = []

            def write(doc, path, indent):
                writes.append(Path(path))
                Path(path).write_text(json.dumps(doc), encoding="utf-8")

            with patch.object(external, "load", side_effect=documents.__getitem__), \
                    patch.object(external, "sha256_file", return_value="test-hash"), \
                    patch.object(external, "one_sided_permutation_p", return_value=(1.0, .001)), \
                    patch.object(external, "dump_atomic", side_effect=write):
                validation, _ = external.validate(out_dir=tmp)
            self.assertEqual(6, validation["coverage"]["e_members"])
            self.assertTrue(all(path.parent == Path(tmp) for path in writes))
            self.assertEqual(2, len(writes))
            self.assertIn(external.ROSTER, validation["inputs_sha256"])
            self.assertEqual(6, validation["identity_audit"]["matched_panel_n"]["senate_insiders"])


if __name__ == "__main__":
    unittest.main()
