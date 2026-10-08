from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

import a7_build_machine_local_source_inventory as a7


class A7NormalizationTests(unittest.TestCase):
    def test_person_name_reorders_fec_comma_form_exactly(self) -> None:
        self.assertEqual(
            a7.normalize_person_name("HOLZBERG, GORDON E."),
            a7.normalize_person_name("Gordon E Holzberg"),
        )

    def test_person_name_does_not_drop_middle_name(self) -> None:
        self.assertNotEqual(
            a7.normalize_person_name("HOLZBERG, GORDON"),
            a7.normalize_person_name("GORDON E HOLZBERG"),
        )

    def test_org_normalization_is_punctuation_only_not_suffix_fuzzy(self) -> None:
        self.assertEqual(a7.normalize_org("A.T.&T"), "A T AND T")
        self.assertNotEqual(a7.normalize_org("EXAMPLE LLC"), a7.normalize_org("EXAMPLE"))

    def test_fec_date_is_bounded_to_held_source_window(self) -> None:
        self.assertEqual(a7.valid_fec_date("2024-02-29T12:00:00"), "2024-02-29")
        self.assertIsNone(a7.valid_fec_date("2020-12-31"))
        self.assertIsNone(a7.valid_fec_date("not-a-date"))

    def test_report_period_bounds_are_not_called_employment_bounds(self) -> None:
        self.assertEqual(a7.report_period_bounds(2025, "mid_year"), ("2025-01-01", "2025-07-01"))
        self.assertEqual(a7.report_period_bounds(2025, "year_end"), ("2025-07-01", "2026-01-01"))

    def test_deterministic_gzip_has_identical_bytes(self) -> None:
        rows = [{"z": 1, "a": "x"}, {"a": "y", "z": 2}]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left = root / "left.gz"
            right = root / "right.gz"
            self.assertEqual(a7.write_deterministic_gzip(left, rows), 2)
            self.assertEqual(a7.write_deterministic_gzip(right, rows), 2)
            self.assertEqual(left.read_bytes(), right.read_bytes())
            with gzip.open(left, "rt", encoding="utf-8") as stream:
                observed = [json.loads(line) for line in stream]
            self.assertEqual(observed, rows)


if __name__ == "__main__":
    unittest.main()
