"""Estimability gates (Paul's rule) and the primary-then-flexible-fallback window logic, on synthetic panels."""
import unittest

import numpy as np

from helpers import L_CONTROLS, sector_year_panel, spec
from sgs import gates

SEARCH = (2008, 2025)


def tables(df):
    return {"sector_year": df}


class TestGates(unittest.TestCase):
    def test_passes_with_six_years_and_enough_sectors(self):
        df = sector_year_panel(n_sectors=4, years=range(2020, 2026))
        d = gates.decide(spec(), tables(df), (2020, 2025), None)
        self.assertEqual(d.status, gates.ESTIMABLE)
        self.assertEqual(d.window, (2020, 2025))

    def test_rejects_fewer_than_six_years(self):
        df = sector_year_panel(n_sectors=4, years=range(2020, 2026))
        df.loc[df["year"] == 2020, "contributions_real_m"] = np.nan  # 5 usable years
        d = gates.decide(spec(), tables(df), (2020, 2025), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("5 distinct years (2021-2025) < 6 required", d.reason)
        self.assertIn("contributions_real_m: no usable value for any sector in 2020", d.reason)

    def test_rejects_rank_deficient_national_design(self):
        # six national regressors + the common level = 7 year-level parameters on 6 distinct years
        df = sector_year_panel(n_sectors=4, years=range(2020, 2026))
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("year-level design not identified: 7 year-level parameters", d.reason)
        self.assertIn("on 6 distinct years", d.reason)

    def test_rejects_collinear_national_regressors_and_names_them(self):
        df = sector_year_panel(n_sectors=4, years=range(2016, 2026))
        df["exp_dem_senate"] = df["exp_dem_house"]
        d = gates.decide(spec(), tables(df), (2016, 2025), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("not identified: exp_dem_senate", d.reason)

    def test_rejects_fewer_than_two_sectors(self):
        df = sector_year_panel(n_sectors=3, years=range(2020, 2026))
        df.loc[df["study_sector"] != df["study_sector"].iloc[0], "growth_previous_year_pct"] = np.nan
        d = gates.decide(spec(), tables(df), (2020, 2025), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("1 sector(s)", d.reason)

    def test_rejects_residual_df_below_three(self):
        df = sector_year_panel(n_sectors=2, years=range(2020, 2026))
        s2 = df["study_sector"].unique()[1]
        df.loc[(df["study_sector"] == s2) & (df["year"] > 2020), "contributions_real_m"] = np.nan  # n = 7, p = 7
        d = gates.decide(spec(), tables(df), (2020, 2025), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("residual df 0 < 3", d.reason)

    def test_partial_year_never_enters(self):
        df = sector_year_panel(n_sectors=3, years=range(2021, 2027))
        df.loc[df["year"] == 2026, "partial_year"] = True
        d = gates.decide(spec(), tables(df), (2021, 2026), None)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("5 distinct years (2021-2025)", d.reason)
        df.loc[df["year"] == 2021, "contributions_status"] = "partial"  # a partial status is never usable either
        d = gates.decide(spec(), tables(df), (2021, 2026), None)
        self.assertIn("4 distinct years (2022-2025)", d.reason)


class TestFallback(unittest.TestCase):
    """Fallback = most recent run of >= 10 consecutive complete-case years within 2008-2025, its most recent 10."""

    def test_default_window_used_when_it_passes(self):
        df = sector_year_panel(n_sectors=4, years=range(2014, 2026))
        d = gates.decide(spec(), tables(df), (2020, 2025), SEARCH)
        self.assertEqual((d.status, d.window, d.window_kind, len(d.attempts)), (gates.ESTIMABLE, (2020, 2025), "default", 1))
        self.assertEqual(d.fallback_search, "")

    def test_fallback_used_when_default_fails(self):
        df = sector_year_panel(n_sectors=4, years=range(2014, 2026))
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual(d.status, gates.ESTIMABLE)
        self.assertEqual((d.window, d.window_kind, len(d.attempts)), ((2016, 2025), "fallback", 2))
        self.assertFalse(d.attempts[0].ok)
        self.assertEqual(d.chosen.years, list(range(2016, 2026)))
        self.assertIn("complete-case years in 2008-2025: 2014-2025", d.fallback_search)
        self.assertIn("window used: its most recent 10 years, 2016-2025", d.fallback_search)

    def test_most_recent_ten_years_of_a_longer_run(self):
        # the ruling's LobbyView example: complete 2008-2022 -> window 2013-2022
        df = sector_year_panel(n_sectors=3, years=range(2006, 2026))
        df.loc[df["year"] > 2022, "exp_dem_house"] = np.nan
        df.loc[df["year"] > 2022, "exp_dem_house_status"] = "missing"
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual((d.status, d.window, d.window_kind), (gates.ESTIMABLE, (2013, 2022), "fallback"))
        self.assertIn("complete-case years in 2008-2025: 2008-2022", d.fallback_search)
        self.assertIn("most recent run of >= 10: 2008-2022", d.fallback_search)
        self.assertEqual(d.chosen.years, list(range(2013, 2023)))

    def test_whole_run_switch(self):
        df = sector_year_panel(n_sectors=3, years=range(2006, 2026))
        df.loc[df["year"] > 2022, "exp_dem_house"] = np.nan
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH, whole_run=True)
        self.assertEqual((d.status, d.window), (gates.ESTIMABLE, (2008, 2022)))
        self.assertEqual(len(d.chosen.years), 15)

    def test_most_recent_qualifying_run_is_used_not_the_latest_short_run(self):
        # complete 2008-2019 (12 years), gap 2020, complete 2021-2025 (5 years): the 5-year run does not qualify
        df = sector_year_panel(n_sectors=3, years=range(2006, 2026))
        df.loc[df["year"] == 2020, "contributions_real_m"] = np.nan
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual((d.status, d.window), (gates.ESTIMABLE, (2010, 2019)))
        self.assertIn("2008-2019 (12 years), 2021-2025 (5 years)", d.fallback_search)

    def test_no_run_of_ten_consecutive_years(self):
        # 9 + 4 complete years, never 10 consecutive: NOT ESTIMABLE even with 13 distinct years
        df = sector_year_panel(n_sectors=4, years=range(2008, 2026))
        df.loc[df["year"].isin([2017, 2021]), "contributions_real_m"] = np.nan
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertEqual(len(d.attempts), 2)
        self.assertTrue(d.attempts[1].is_search)
        self.assertIn("no run of >= 10 consecutive calendar years", d.reason)
        self.assertIn("2008-2016 (9 years), 2018-2020 (3 years), 2022-2025 (4 years)", d.reason)
        self.assertIn("fallback search 2008-2025", d.attempts[1].compact())

    def test_search_span_limits_the_run(self):
        # complete 2000-2019 but the search starts in 2008 and the run ends in 2019
        df = sector_year_panel(n_sectors=3, years=range(2000, 2020))
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual((d.status, d.window), (gates.ESTIMABLE, (2010, 2019)))
        self.assertIn("complete-case years in 2008-2025: 2008-2019", d.fallback_search)

    def test_fallback_needs_ten_consecutive_years(self):
        df = sector_year_panel(n_sectors=4, years=range(2018, 2026))  # 8 years available
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), SEARCH)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertEqual(len(d.attempts), 2)
        self.assertIn("complete-case years in 2008-2025: 2018-2025", d.reason)
        self.assertIn("no run of >= 10 consecutive calendar years", d.reason)
        self.assertIn("default 2020-2025", d.reason)

    def test_fallback_can_be_disabled(self):
        df = sector_year_panel(n_sectors=4, years=range(2014, 2026))
        d = gates.decide(spec(controls=L_CONTROLS), tables(df), (2020, 2025), None)
        self.assertEqual((d.status, len(d.attempts)), (gates.NOT_ESTIMABLE, 1))

    def test_year_runs(self):
        self.assertEqual(gates.year_runs([2012, 2008, 2009, 2010, 2014]), [[2008, 2009, 2010], [2012], [2014]])
        self.assertEqual(gates.year_runs([]), [])


if __name__ == "__main__":
    unittest.main()
