"""Wild cluster restricted bootstrap: seeded reproducibility and the null p-value distribution (G = 6)."""
import os
import unittest

import numpy as np

from helpers import sector_year_panel, spec
from sgs import config, estimate
from sgs.sample import build_design, build_sample


def _fit(n_sectors, seed, beta=None, noise=1.0, years=range(2016, 2026)):
    df = sector_year_panel(n_sectors=n_sectors, noise=noise, seed=seed, beta=beta, years=years)
    sp = spec(controls=("pres_year", "midterm_year"))
    smp = build_sample({"sector_year": df}, sp, (years[0], years[-1]))
    d = build_design(smp.df, sp)
    return d, estimate.ols(d)


class TestReproducible(unittest.TestCase):
    def test_same_seed_same_result_random_draws(self):
        d, fit = _fit(7, seed=21)  # 6**7 > 9,999: random draws
        a = estimate.boot_coefficient(d, fit, "growth_previous_year_pct", config.BOOT_B, estimate.seed_for(42, "T", "g"))
        b = estimate.boot_coefficient(d, fit, "growth_previous_year_pct", config.BOOT_B, estimate.seed_for(42, "T", "g"))
        self.assertFalse(a["boot_enumerated"])
        self.assertEqual(a["boot_draws"], config.BOOT_B)
        for key in ("boot_p", "ci_low", "ci_high"):
            self.assertEqual(a[key], b[key])
        c = estimate.boot_coefficient(d, fit, "growth_previous_year_pct", config.BOOT_B, estimate.seed_for(43, "T", "g"))
        self.assertNotEqual((a["ci_low"], a["ci_high"]), (c["ci_low"], c["ci_high"]))

    def test_enumeration_when_small(self):
        d, fit = _fit(5, seed=22)
        r = estimate.boot_coefficient(d, fit, "growth_previous_year_pct", config.BOOT_B, estimate.seed_for(1, "x"))
        self.assertTrue(r["boot_enumerated"])
        self.assertEqual(r["boot_draws"], 6 ** 5)

    def test_null_pvalues_roughly_uniform_g6(self):
        reps = int(os.environ.get("SGS_NULL_REPS", "200"))
        beta0 = {"growth_previous_year_pct": 0.0, "pres_year": 1.0, "midterm_year": -0.5}
        ps = []
        for r in range(reps):
            d, fit = _fit(6, seed=1000 + r, beta=beta0, noise=1.0)
            k = fit.names.index("growth_previous_year_pct")
            w = estimate.WCR(d, fit, k, config.BOOT_B, estimate.seed_for(config.SEED, "null", str(r)))
            ps.append(w.pvalue(0.0))
        ps = np.array(ps)
        rate5 = float(np.mean(ps < 0.05))
        rate10 = float(np.mean(ps < 0.10))
        grid = np.linspace(0, 1, 201)
        ks = float(np.max(np.abs(np.searchsorted(np.sort(ps), grid, side="right") / len(ps) - grid)))
        deciles = np.histogram(ps, bins=np.linspace(0, 1, 11))[0].tolist()
        print(f"\nNULL_SIMULATION G=6 reps={reps} B={config.BOOT_B}: rejection rate at 5% = {rate5:.3f}, "
              f"at 10% = {rate10:.3f}; KS distance to uniform = {ks:.3f}; decile counts = {deciles}")
        self.assertLessEqual(rate5, 0.10)
        self.assertGreaterEqual(rate5, 0.005)
        self.assertLess(ks, 0.15)


if __name__ == "__main__":
    unittest.main()
