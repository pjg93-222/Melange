"""LobbyView tests L1-LV..L3-LV (Paul's option (a)): registry entries, fallback gating, DESCRIPTIVE output."""
import math
import unittest

import numpy as np

from helpers import sector_year_panel
from sgs import estimate, gates, registry
from sgs.registry import L_CONTROLS

NOTE = "2 sectors: wild cluster bootstrap cannot reach p < 0.056; inference not available"


def lv_panel(noise=0.02, seed=4):
    """Two LobbyView sectors 2006-2025: the LobbyView amount observed 2006-2023 (2024 partial, 2025 absent) and
    expected control blank 2023-2025, as in the real inputs. LV = 20 + 5 i + 0.5 * prior growth + controls."""
    beta = {"growth_previous_year_pct": 0.5, "pres_year": 1.0, "midterm_year": -0.3, "exp_dem_house": 0.8,
            "exp_dem_senate": -0.6, "cur_dem_house": 0.2, "cur_dem_senate": -0.1}
    df = sector_year_panel(n_sectors=2, years=range(2006, 2026), noise=noise, seed=seed, beta=beta,
                           dv="lobby_amount_undiff_real_m")
    df["lobby_undiff_status"] = "observed"
    df.loc[df["year"] == 2024, "lobby_undiff_status"] = "partial"
    df.loc[df["year"] == 2025, "lobby_amount_undiff_real_m"] = np.nan
    df.loc[df["year"] == 2025, "lobby_undiff_status"] = "missing"
    for c in ("exp_dem_house", "exp_dem_senate"):
        df.loc[df["year"] >= 2023, c] = np.nan
        df.loc[df["year"] >= 2023, c + "_status"] = "missing"
    return df


class TestRegistry(unittest.TestCase):
    def test_three_descriptive_lobbyview_tests(self):
        lv = [t for t in registry.REGISTRY if t.family == "L-LV"]
        self.assertEqual([t.id for t in lv], ["L1-LV", "L2-LV", "L3-LV"])
        for t, g in zip(lv, ("growth_previous_year_pct", "growth_same_year_pct", "predicted_growth_pct")):
            self.assertEqual((t.label, t.dv, t.focal, t.controls, t.fe, t.inference),
                             ("DESCRIPTIVE", "lobby_amount_undiff_real_m", (g,), L_CONTROLS, ("sector",), "none"))
            self.assertIn(NOTE, t.note)

    def test_lda_l_tests_unchanged_and_never_mixed(self):
        l_lda = [t for t in registry.REGISTRY if t.family == "L"]
        self.assertEqual(len(l_lda), 6)
        self.assertEqual({t.dv for t in l_lda}, {"lobby_income_real_m", "lobby_expenses_real_m"})
        self.assertTrue(all(t.label == "CORE" and t.inference == "wcr" for t in l_lda))
        # no test mixes the LobbyView measure with an LDA measure, and no derived/robustness test reuses LV
        self.assertFalse([t for t in registry.REGISTRY if t.base in ("L1-LV", "L2-LV", "L3-LV")])


class TestLobbyViewPath(unittest.TestCase):
    def setUp(self):
        self.df = lv_panel()
        self.spec = registry.BY_ID["L1-LV"]

    def test_gated_through_the_fallback_window(self):
        d = gates.decide(self.spec, {"sector_year": self.df})  # config defaults: 2020-2025, search 2008-2025
        self.assertEqual((d.status, d.window, d.window_kind), (gates.ESTIMABLE, (2013, 2022), "fallback"))
        self.assertFalse(d.attempts[0].ok)
        self.assertEqual(d.chosen.sectors, ["commercial_banks", "credit_unions"])
        self.assertIn("complete-case years in 2008-2025: 2008-2022", d.fallback_search)

    def test_descriptive_output_no_inference(self):
        d = gates.decide(self.spec, {"sector_year": self.df})
        res = estimate.estimate(self.spec, d.chosen, B=999)
        self.assertEqual(len(res.coefs), 1)
        c = res.coefs[0]
        self.assertEqual(c["coefficient"], "growth_previous_year_pct")
        self.assertLess(abs(c["estimate"] - 0.5), 0.05)
        self.assertTrue(math.isfinite(c["hc1_se"]) and c["hc1_se"] > 0)
        for k in ("boot_p", "ci_low", "ci_high", "cr1_se"):
            self.assertTrue(math.isnan(c[k]), k)
        self.assertEqual(c["boot_draws"], 0)
        self.assertEqual(c["boot_note"], NOTE)
        self.assertTrue(c["inference"].startswith("none (DESCRIPTIVE)"))
        self.assertTrue(c["stratification"].startswith(("STRATIFIED", "UNSTRATIFIED")))
        self.assertEqual(estimate.descriptive_note(2), NOTE)


if __name__ == "__main__":
    unittest.main()
