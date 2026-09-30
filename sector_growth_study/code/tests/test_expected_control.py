"""Expected control 2023-2026 (Paul's ruling of 2026-09-25): the 02 fill sheet, IEM first, and the precedence of a
future `expected_control_markets` sheet for 2023-2026 (synthetic workbooks only)."""
import math
import tempfile
import unittest
from pathlib import Path

import pandas as pd

import synth_workbooks
from sgs import load, panel
from sgs.load import LoadError


def markets_frame():
    """Daily Polymarket/Kalshi-style rows. House: p_dem_control; Senate: p_rep_control only (1 - p used).
    2024 House has one row after election day (before_election_day = 0, excluded). 2025 House has a row dated in 2026
    (flag: measured after the year). 2021 rows fall outside the fill years and must be ignored. No 2026 rows."""
    rows = []

    def add(date, year, ch, market, p_dem=None, p_rep=None, before=1, status="observed"):
        rows.append({"date": date, "calendar_year": year, "chamber": ch, "market": market, "p_dem_control": p_dem,
                     "p_rep_control": p_rep, "before_election_day": before, "status": status})

    add("2023-03-01", 2023, "House", "kalshi", p_dem=0.40)
    add("2023-03-01", 2023, "House", "polymarket", p_dem=0.44)
    add("2023-09-01", 2023, "House", "kalshi", p_dem=0.48)
    add("2024-06-01", 2024, "House", "kalshi", p_dem=0.50)
    add("2024-11-10", 2024, "House", "kalshi", p_dem=0.99, before=0)  # after election day: excluded
    add("2025-05-01", 2025, "House", "kalshi", p_dem=0.70)
    add("2026-01-15", 2025, "House", "kalshi", p_dem=0.80)  # dated after the calendar year
    add("2023-03-01", 2023, "Senate", "kalshi", p_rep=0.70)
    add("2023-06-01", 2023, "Senate", "polymarket", p_rep=0.60)
    add("2024-06-01", 2024, "Senate", "kalshi", p_rep=0.75, status="missing")  # unusable status: excluded
    add("2021-06-01", 2021, "House", "kalshi", p_dem=0.01)  # IEM year: ignored
    return pd.DataFrame(rows)


def panel_for(folder, **kw):
    data = synth_workbooks.build(folder, **kw)
    wbs = load.load_all(data)
    return panel.build_sector_year(wbs), wbs


def at(sy, year, col):
    v = sy.loc[(sy["study_sector"] == "commercial_banks") & (sy["year"] == year), col]
    assert len(v) == 1
    return v.iloc[0]


class TestExpectedControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        cls.iem_only, _ = panel_for(base / "iem", iem_last_year=2022)
        cls.filled, cls.wbs_filled = panel_for(base / "fill", iem_last_year=2022,
                                               expected_control=synth_workbooks.expected_control_sheet())
        cls.iem_full, _ = panel_for(base / "iemfull", expected_control=synth_workbooks.expected_control_sheet())
        cls.mk, _ = panel_for(base / "mk", iem_last_year=2022, expected_control=synth_workbooks.expected_control_sheet(),
                              markets=markets_frame())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_without_the_fill_sheet_2023_2025_stay_missing(self):
        for y in (2023, 2024, 2025):
            self.assertTrue(math.isnan(at(self.iem_only, y, "exp_dem_house")))
            self.assertEqual(at(self.iem_only, y, "exp_dem_house_status"), "missing")
            self.assertIsNone(at(self.iem_only, y, "exp_dem_house_method"))
        self.assertEqual(at(self.iem_only, 2022, "exp_dem_house_method"), "iem_annual_mean")

    def test_fill_sheet_supplies_2023_2026_with_method_and_flag(self):
        sy = self.filled
        self.assertEqual((at(sy, 2023, "exp_dem_house"), at(sy, 2023, "exp_dem_senate")), (1.0, 0.0))
        self.assertEqual(at(sy, 2023, "exp_dem_house_method"), "forecaster_final_call_binary")
        self.assertEqual(at(sy, 2023, "exp_dem_house_flag"), "measured Nov 2024, after the year")
        self.assertIsNone(at(sy, 2024, "exp_dem_house_flag"))
        self.assertAlmostEqual(at(sy, 2025, "exp_dem_house"), 0.9144)
        self.assertEqual(at(sy, 2025, "exp_dem_senate_method"), "market_snapshot")
        self.assertEqual(at(sy, 2025, "exp_dem_senate_flag"), "measured Sep 2026, after the year")
        self.assertEqual(at(sy, 2023, "exp_dem_house_status"), "observed")
        self.assertIn("expected_control_2023_2026", at(sy, 2023, "exp_dem_house_source"))
        # exp_shift uses the filled value
        self.assertAlmostEqual(at(sy, 2023, "exp_shift_house"), 1.0 - at(sy, 2023, "cur_dem_house"))

    def test_iem_rows_unchanged_by_the_fill(self):
        a = self.iem_only[self.iem_only["year"] <= 2022]
        b = self.filled[self.filled["year"] <= 2022]
        for c in ("exp_dem_house", "exp_dem_senate", "exp_dem_house_status", "exp_dem_house_method"):
            self.assertTrue(a[c].equals(b[c]), c)

    def test_iem_value_wins_over_the_fill_sheet_where_present(self):
        sy = self.iem_full  # synthetic IEM observed in every year
        v = at(sy, 2023, "exp_dem_house")
        self.assertNotEqual(v, 1.0)
        self.assertEqual(at(sy, 2023, "exp_dem_house_method"), "iem_annual_mean")

    def test_markets_sheet_takes_precedence_for_2023_2026(self):
        sy = self.mk
        self.assertAlmostEqual(at(sy, 2023, "exp_dem_house"), (0.40 + 0.44 + 0.48) / 3)
        self.assertEqual(at(sy, 2023, "exp_dem_house_method"), "market_daily_mean")
        self.assertAlmostEqual(at(sy, 2024, "exp_dem_house"), 0.50)  # the post-election row is excluded
        self.assertAlmostEqual(at(sy, 2023, "exp_dem_senate"), 1 - (0.70 + 0.60) / 2)  # from p_rep_control
        self.assertAlmostEqual(at(sy, 2025, "exp_dem_house"), 0.75)
        self.assertEqual(at(sy, 2025, "exp_dem_house_flag"), "measured Jan 2026, after the year")
        self.assertIsNone(at(sy, 2023, "exp_dem_house_flag"))
        # no usable market row: the fill sheet still supplies the year x chamber
        self.assertEqual(at(sy, 2024, "exp_dem_senate"), 0.0)
        self.assertEqual(at(sy, 2024, "exp_dem_senate_method"), "forecaster_final_call_binary")
        self.assertAlmostEqual(at(sy, 2026, "exp_dem_house"), 0.9144)
        self.assertEqual(at(sy, 2026, "exp_dem_house_method"), "market_snapshot")
        # market rows outside 2023-2026 never replace IEM
        self.assertEqual(at(sy, 2021, "exp_dem_house"), at(self.iem_only, 2021, "exp_dem_house"))
        self.assertEqual(at(sy, 2021, "exp_dem_house_method"), "iem_annual_mean")

    def test_flags_reach_the_tier_table(self):
        syt = panel.build_sector_year_tier(self.wbs_filled, self.filled)
        v = syt.loc[(syt["study_sector"] == "commercial_banks") & (syt["year"] == 2023), "exp_dem_house_flag"]
        self.assertEqual(set(v), {"measured Nov 2024, after the year"})

    def test_optional_sheets_validated_when_present(self):
        with tempfile.TemporaryDirectory() as d:
            bad = markets_frame().drop(columns=["market"])
            data = synth_workbooks.build(Path(d), iem_last_year=2022, markets=bad)
            with self.assertRaises(LoadError) as cm:
                load.load_all(data)
            self.assertIn("[expected_control_markets] column market", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
