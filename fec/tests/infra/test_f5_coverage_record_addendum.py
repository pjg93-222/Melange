"""Pin the FC-2 / D-151 F5 COVERAGE RECORD addendum so the hold terms cannot drift silently."""
import unittest
from pathlib import Path

ADDENDUM = Path(__file__).resolve().parents[3] / "audits" / "small_tooling_20261020" / "F5_COVERAGE_RECORD_ADDENDUM_20261026.md"


class F5CoverageRecordAddendum(unittest.TestCase):
    def test_terms(self):
        text = ADDENDUM.read_text(encoding="utf-8")
        for needle in (
            "VOID-FOR-COVERAGE", "72 eligible members", "150", "UNSPENT",
            "VOID-FOR-CONSTRUCT-CHANGE", "2027-01-15", "468", "f5-coverage-recount",
            "2027-01-20", "refuse to open `seed_prob` or `pressure_mult`",
            "reproduce the 09-30 count of 72",
        ):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
