"""Leave-one-out loops and the tier-interaction coding (Employee reference), on synthetic data."""
import dataclasses
import unittest

import numpy as np
import pandas as pd

from helpers import SECTORS, national, sector_year_panel, spec
from sgs import config, estimate, gates
from sgs.sample import build_design, build_sample


class TestLeaveOneOut(unittest.TestCase):
    def setUp(self):
        self.df = sector_year_panel(n_sectors=5, years=range(2016, 2026), noise=0.3, seed=31)

    def _direct(self, sub, sp):
        d = build_design(sub.assign(y=sub["contributions_real_m"]), dataclasses.replace(sp, variant="level"))
        return estimate.ols(d).coef("growth_previous_year_pct")

    def test_leave_one_sector_out(self):
        sp = spec(id="R-LOSO-X", variant="loso")
        d = gates.decide(sp, {"sector_year": self.df}, (2016, 2025), None)
        self.assertEqual(d.status, gates.ESTIMABLE)
        res = estimate.estimate(sp, d.chosen, B=999)
        self.assertEqual([r["left_out"] for r in res.subfits], list(SECTORS[:5]))
        for r in res.subfits:
            self.assertEqual(r["status"], "estimated")
            sub = self.df[self.df["study_sector"] != r["left_out"]]
            self.assertAlmostEqual(r["estimate"], self._direct(sub, sp), places=10)
            self.assertEqual(r["n_sectors"], 4)

    def test_leave_one_year_out_flags_the_minimum(self):
        df = self.df[self.df["year"] >= 2020]
        sp = spec(id="R-LOYO-X", variant="loyo", controls=("pres_year", "midterm_year"))
        d = gates.decide(sp, {"sector_year": df}, (2020, 2025), None)
        self.assertEqual(d.status, gates.ESTIMABLE)
        res = estimate.estimate(sp, d.chosen, B=999)
        self.assertEqual([r["left_out"] for r in res.subfits], [str(y) for y in range(2020, 2026)])
        for r in res.subfits:
            self.assertEqual(r["n_years"], 5)
            self.assertIn("diagnostic: 5 years < the 6-year minimum", r["flag"])
            if r["status"] == "estimated":
                sub = df[df["year"] != int(r["left_out"])]
                self.assertAlmostEqual(r["estimate"], self._direct(sub, sp), places=10)
        # dropping the single midterm year removes midterm_year's variation: that sub-fit is not identified
        mid = [r for r in res.subfits if r["left_out"] == "2022"][0]
        self.assertEqual(mid["status"], "not estimable")
        self.assertIn("midterm_year", mid["reason"])


def tier_panel(n_sectors=4, years=range(2016, 2026), seed=3, slopes=None):
    slopes = slopes or {"Employee": 1.0, "Chief": 3.0, "Middle Management": 2.0, "Corporate": 5.0}
    rng = np.random.default_rng(seed)
    nat = national(years, seed)
    rows = []
    for i, s in enumerate(SECTORS[:n_sectors]):
        for _, r in nat.iterrows():
            x = rng.normal(2, 3)
            for j, t in enumerate(config.TIERS):
                y = 1.0 + i + 0.5 * j + slopes[t] * x + 1.2 * r["pres_year"] - 0.4 * r["exp_dem_house"]
                rows.append({"study_sector": s, "year": int(r["year"]), "tier": t, "partial_year": False,
                             "growth_previous_year_pct": x, "contributions_real_m": y,
                             "pres_year": r["pres_year"], "midterm_year": r["midterm_year"],
                             "exp_dem_house": r["exp_dem_house"], "exp_dem_senate": r["exp_dem_senate"],
                             "contributions_status": "observed", "growth_prev_status": "observed",
                             "controls_status": "observed", "exp_dem_house_status": "observed",
                             "exp_dem_senate_status": "observed"})
    return pd.DataFrame(rows)


class TestTierModel(unittest.TestCase):
    def test_employee_is_the_reference_tier(self):
        x = "growth_previous_year_pct"
        sp = spec(id="T1", table="sector_year_tier", focal=(x, f"{x}:Chief", f"{x}:Middle Management"),
                  fe=("sector_x_tier",), variant="tier", tiers=config.TIER_MODEL_TIERS,
                  interactions=((x, "Chief"), (x, "Middle Management")))
        tab = {"sector_year_tier": tier_panel()}
        smp = build_sample(tab, sp, (2016, 2025))
        self.assertEqual(set(smp.df["tier"]), {"Chief", "Middle Management", "Employee"})  # Corporate separate
        d = build_design(smp.df, sp)
        self.assertIn(x, d.names)
        self.assertIn(f"{x}:Chief", d.names)
        self.assertIn(f"{x}:Middle Management", d.names)
        self.assertNotIn(f"{x}:Employee", d.names)
        self.assertEqual(len([n for n in d.names if n.startswith("FE:")]), 4 * 3)  # sector x tier baselines
        fit = estimate.ols(d)
        self.assertAlmostEqual(fit.coef(x), 1.0, places=8)  # Employee slope
        self.assertAlmostEqual(fit.coef(f"{x}:Chief"), 2.0, places=8)  # 3 - 1
        self.assertAlmostEqual(fit.coef(f"{x}:Middle Management"), 1.0, places=8)  # 2 - 1
        dec = gates.decide(sp, tab, (2016, 2025), None)
        self.assertEqual(dec.status, gates.ESTIMABLE)
        res = estimate.estimate(sp, dec.chosen, B=999)
        self.assertEqual([c["coefficient"] for c in res.coefs], list(sp.focal))

    def test_corporate_fitted_separately(self):
        x = "growth_previous_year_pct"
        sp = spec(id="T1-corporate", table="sector_year_tier", tiers=(config.CORPORATE_TIER,))
        smp = build_sample({"sector_year_tier": tier_panel()}, sp, (2016, 2025))
        self.assertEqual(set(smp.df["tier"]), {"Corporate"})
        fit = estimate.ols(build_design(smp.df, sp))
        self.assertAlmostEqual(fit.coef(x), 5.0, places=8)


if __name__ == "__main__":
    unittest.main()
