"""OLS recovery, HC1 / CR1 errors, and the fast wild-cluster-restricted algebra against brute force."""
import unittest

import numpy as np

from helpers import L_CONTROLS, TRUE, sector_year_panel, spec
from sgs import estimate, gates
from sgs.sample import build_design, build_sample


def _design(df, sp, window=(2016, 2025)):
    smp = build_sample({"sector_year": df}, sp, window)
    return smp, build_design(smp.df, sp)


class TestRecovery(unittest.TestCase):
    def test_known_coefficients_recovered_exactly_without_noise(self):
        df = sector_year_panel(n_sectors=6, noise=0.0)
        sp = spec(controls=L_CONTROLS)
        _, d = _design(df, sp)
        fit = estimate.ols(d)
        for k in ("growth_previous_year_pct",) + L_CONTROLS:
            self.assertAlmostEqual(fit.coef(k), TRUE[k], places=8, msg=k)
        for i, s in enumerate(d.cluster_labels):  # sector baselines a_i = 5 + 3 i
            self.assertAlmostEqual(fit.coef(f"FE:{s}"), 5.0 + 3.0 * i, places=8)

    def test_known_coefficients_recovered_with_noise(self):
        df = sector_year_panel(n_sectors=6, noise=0.05, seed=11)
        sp = spec(controls=L_CONTROLS)
        _, d = _design(df, sp)
        fit = estimate.ols(d)
        self.assertLess(abs(fit.coef("growth_previous_year_pct") - 0.8), 0.02)
        self.assertLess(abs(fit.coef("pres_year") - 1.5), 0.1)

    def test_hc1_and_cr1_match_statsmodels(self):
        try:
            import statsmodels.api as sm
        except ImportError:
            self.skipTest("statsmodels not importable")
        df = sector_year_panel(n_sectors=5, noise=0.5, seed=3)
        _, d = _design(df, spec())
        fit = estimate.ols(d)
        m = sm.OLS(d.y, d.X)
        hc1 = m.fit(cov_type="HC1").bse
        cl = m.fit(cov_type="cluster", cov_kwds={"groups": d.clusters}).bse
        np.testing.assert_allclose(fit.se_hc1, hc1, rtol=1e-8)
        np.testing.assert_allclose(fit.se_cr1, cl, rtol=1e-8)


def brute_force_tstars(d, fit, k, b0, V):
    """Explicit restricted wild cluster bootstrap: build y*, refit, CR1 t* for every draw."""
    X, y, cl = d.X, d.y, d.clusters
    n, p = X.shape
    G = fit.G
    Xmk = np.delete(X, k, axis=1)
    yr = y - b0 * X[:, k]
    g = np.linalg.lstsq(Xmk, yr, rcond=None)[0]
    u_r = yr - Xmk @ g
    fitted = y - u_r
    A = np.linalg.inv(X.T @ X)
    c = G / (G - 1) * (n - 1) / (n - p)
    out = []
    for v in V:
        ys = fitted + u_r * v[cl]
        bs = A @ X.T @ ys
        us = ys - X @ bs
        S = np.zeros((G, p))
        np.add.at(S, cl, X * us[:, None])
        se = np.sqrt(c * (A @ S.T @ S @ A)[k, k])
        out.append((bs[k] - b0) / se)
    return np.array(out)


class TestWildClusterAlgebra(unittest.TestCase):
    def setUp(self):
        df = sector_year_panel(n_sectors=4, noise=1.0, seed=5, years=range(2016, 2026))
        self.smp, self.d = _design(df, spec())
        self.fit = estimate.ols(self.d)
        self.k = self.fit.names.index("growth_previous_year_pct")

    def test_fast_equals_brute_force(self):
        w = estimate.WCR(self.d, self.fit, self.k, 9999, estimate.seed_for(1, "t"))
        self.assertTrue(w.enumerated)
        self.assertEqual(w.draws, 6 ** 4)
        import itertools
        V = np.array(list(itertools.product(estimate.WEBB, repeat=4)))
        for b0 in (0.0, 0.3, -2.0, self.fit.coef("growth_previous_year_pct")):
            np.testing.assert_allclose(w.tstar(b0), brute_force_tstars(self.d, self.fit, self.k, b0, V),
                                       rtol=1e-7, atol=1e-9)

    def test_se_is_cr1(self):
        w = estimate.WCR(self.d, self.fit, self.k, 9999, estimate.seed_for(1, "t"))
        self.assertAlmostEqual(w.se, float(self.fit.se_cr1[self.k]), places=10)

    def test_identity_draw_reproduces_t_and_bounds_p(self):
        w = estimate.WCR(self.d, self.fit, self.k, 9999, estimate.seed_for(1, "t"))
        ones = int(np.where((np.array(list(__import__("itertools").product(estimate.WEBB, repeat=4))) == 1.0).all(1))[0][0])
        for b0 in (0.0, 1.7, -5.0):
            self.assertAlmostEqual(w.tstar(b0)[ones], w.tstat(b0), places=8)
            self.assertGreaterEqual(w.pvalue(b0), 2 / 6 ** 4 - 1e-12)

    def test_ci_is_test_inversion(self):
        w = estimate.WCR(self.d, self.fit, self.k, 9999, estimate.seed_for(1, "t"))
        lo, hi = w.ci(0.05)
        self.assertLess(lo, w.bk)
        self.assertGreater(hi, w.bk)
        eps = 1e-4 * w.se
        self.assertGreaterEqual(w.pvalue(lo + eps), 0.05)
        self.assertLess(w.pvalue(lo - eps), 0.05)
        self.assertGreaterEqual(w.pvalue(hi - eps), 0.05)
        self.assertLess(w.pvalue(hi + eps), 0.05)

    def test_two_clusters_give_unbounded_interval(self):
        df = sector_year_panel(n_sectors=2, noise=1.0, seed=9, years=range(2016, 2026))
        _, d = _design(df, spec(controls=("pres_year",)))
        fit = estimate.ols(d)
        row = estimate.boot_coefficient(d, fit, "growth_previous_year_pct", 9999, estimate.seed_for(1, "x"))
        self.assertEqual(row["boot_draws"], 36)
        self.assertGreaterEqual(row["boot_p"], 2 / 36 - 1e-12)
        self.assertTrue(np.isinf(row["ci_low"]) and np.isinf(row["ci_high"]))


if __name__ == "__main__":
    unittest.main()
