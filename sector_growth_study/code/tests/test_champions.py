"""H5 (champions, 05): slope recovery with and without champion fixed effects, the member-cycle gate, and NOT BUILT
when 05 is missing, being rewritten, or lacks expected columns. Synthetic data only."""
import dataclasses
import tempfile
import unittest
from pathlib import Path

import numpy as np

import synth_workbooks as sw
from sgs import champions, config, gates, registry

POOLED, WITHIN = registry.BY_ID["H5-pooled"], registry.BY_ID["H5-within"]


def data_from(frame):
    return champions.ChampionsData(ok=True, frame=frame, source={}, documented=set(frame.columns))


class TestRecovery(unittest.TestCase):
    def test_pooled_and_within_recover_the_slope_without_member_effects(self):
        cd = data_from(sw.champions_frame(slope=5000.0, member_corr=0.0, noise=0.0))
        for spec in (POOLED, WITHIN):
            d = champions.decide_h5(spec, cd)
            self.assertEqual(d.status, gates.ESTIMABLE, d.reason)
            res = champions.estimate_h5(spec, d, B=999)
            self.assertAlmostEqual(res.coefs[0]["estimate"], 5000.0, places=5, msg=spec.id)
            self.assertEqual(d.sample.cycles, [2022, 2024, 2026])  # 2020 money missing

    def test_within_recovers_the_slope_when_member_effects_track_toughness(self):
        cd = data_from(sw.champions_frame(slope=5000.0, member_corr=1.0, noise=0.0, seed=8))
        dw = champions.decide_h5(WITHIN, cd)
        self.assertEqual(dw.status, gates.ESTIMABLE, dw.reason)
        bw = champions.estimate_h5(WITHIN, dw, B=999).coefs[0]["estimate"]
        self.assertAlmostEqual(bw, 5000.0, places=5)
        dp = champions.decide_h5(POOLED, cd)
        bp = champions.estimate_h5(POOLED, dp, B=999).coefs[0]["estimate"]
        self.assertGreater(abs(bp - 5000.0), 500.0)  # pooled OLS is biased by the correlated member effects
        # seniority grows one-for-one with the cycle: absorbed by champion + cycle FE and named as dropped
        self.assertIn("seniority_years", dw.info["dropped_controls"])
        self.assertIn("chamber=Senate", dw.info["dropped_controls"])
        self.assertEqual(dw.design.nested_fe, len(dw.sample.champions))
        self.assertGreater(dw.identifying_champions, 0)

    def test_noisy_recovery_inference_and_strata(self):
        cd = data_from(sw.champions_frame(n_members=60, slope=5000.0, noise=2000.0, seed=11))
        d = champions.decide_h5(POOLED, cd)
        res = champions.estimate_h5(POOLED, d, B=999)
        c = res.coefs[0]
        self.assertLess(abs(c["estimate"] - 5000.0), 1000.0)
        self.assertTrue(c["ci_low"] < 5000.0 < c["ci_high"])
        self.assertLess(c["boot_p"], 0.05)
        self.assertEqual(c["boot_draws"], 999)  # 6**60 > B: random draws
        self.assertTrue(c["stratification"].startswith("STRATIFIED"))
        self.assertEqual(sorted({s["board"] for s in res.strata}), ["bank", "credit_union", "crypto"])
        self.assertIn("employee channel only", c["flag"])

    def test_sample_rules(self):
        frame = sw.champions_frame()
        cd = data_from(frame)
        d = champions.decide_h5(POOLED, cd)
        df = d.sample.df
        self.assertTrue((df["up_for_election"] == 1).all())
        self.assertFalse((df["lost_primary"] == 1).any())
        self.assertIn("lost_primary = 1 (lost renomination; such rows enter only the primary models)",
                      d.sample.exclusions)
        # the primary models keep lost-renomination rows
        sp = registry.BY_ID["H5-primary_contested"]
        smp = champions.build_h5_sample(cd, sp, "direct_giving_real_2025_usd", "", "")
        self.assertTrue(any("lost-renomination rows kept" in n for n in smp.notes))
        # log1p and extensive-margin variants
        dl = champions.decide_h5(registry.BY_ID["H5-pooled-log1p"], cd)
        self.assertTrue(np.allclose(dl.sample.df["y"], np.log1p(dl.sample.df["direct_giving_real_2025_usd"])))
        da = champions.decide_h5(registry.BY_ID["H5-pooled-any"], cd)
        self.assertTrue(set(da.sample.df["y"].unique()) <= {0.0, 1.0})


class TestGate(unittest.TestCase):
    def test_excluding_2026_leaves_two_cycles(self):
        d = champions.decide_h5(registry.BY_ID["H5-pooled-no2026"], data_from(sw.champions_frame()))
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("2 cycles (2022, 2024) < 3 required", d.reason)

    def test_too_few_member_cycles(self):
        d = champions.decide_h5(POOLED, data_from(sw.champions_frame(n_members=8, boards=("bank",))))
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("member-cycles < 30 required", d.reason)

    def test_zero_variance_focal(self):
        f = sw.champions_frame()
        f.loc[f["toughness_general"].notna(), "toughness_general"] = 1.0
        d = champions.decide_h5(POOLED, data_from(f))
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("toughness_general: zero variance", d.reason)

    def test_within_needs_within_champion_variation(self):
        f = sw.champions_frame()
        has = f["toughness_general"].notna()
        f.loc[has, "toughness_general"] = (f.loc[has, "bioguide"].str[1:].astype(int) % 4).astype(float)
        self.assertEqual(champions.decide_h5(POOLED, data_from(f)).status, gates.ESTIMABLE)
        d = champions.decide_h5(WITHIN, data_from(f))
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("zero within-champion variance", d.reason)

    def test_secondary_regressor_blocked_by_cycles(self):
        d = champions.decide_h5(registry.BY_ID["H5-primary_contested"], data_from(sw.champions_frame()))
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("1 cycles (2022) < 3 required", d.reason)
        self.assertIn("primary_contested usable in cycles 2020, 2022", d.reason)


class TestLoadingAndNotBuilt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name) / "data"
        self.data.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_05_is_not_built(self):
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("05_industry_champions.xlsx not found", cd.reason)
        d = champions.decide_h5(POOLED, cd)
        self.assertEqual(d.status, gates.NOT_BUILT)
        self.assertTrue(d.reason.startswith("NotBuilt: "))

    def test_missing_receipt_is_not_built(self):
        sw.write_champions(self.data, sw.champions_frame(), write_receipt=False)
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("build_receipt_05.json not found", cd.reason)

    def test_fresh_receipt_means_being_rewritten(self):
        sw.write_champions(self.data, sw.champions_frame(), age_minutes=2.0)
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("min ago (< 10 min): 05 is being rewritten", cd.reason)
        self.assertEqual(champions.decide_h5(WITHIN, cd).status, gates.NOT_BUILT)

    def test_bytes_differing_from_the_receipt(self):
        sw.write_champions(self.data, sw.champions_frame(), receipt_sha="0" * 64)
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("differs from the receipt", cd.reason)

    def test_missing_expected_column(self):
        sw.write_champions(self.data, sw.champions_frame().drop(columns=["toughness_general"]))
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("expected columns missing from 05_industry_champions.xlsx [data]: toughness_general", cd.reason)

    def test_no_dependent_variable_column(self):
        sw.write_champions(self.data, sw.champions_frame().drop(columns=["direct_giving_real_2025_usd"]))
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("industry_money_primary_real_2025_usd or direct_giving_real_2025_usd", cd.reason)

    def test_loaded_and_dv_choice(self):
        sw.write_champions(self.data, sw.champions_frame())
        cd = champions.load_champions(self.data)
        self.assertTrue(cd.ok, cd.reason)
        self.assertEqual(len(cd.source["sha256"]), 64)
        col, label, flag, _ = champions.resolve_dv(cd, "industry_money_primary")
        self.assertEqual((col, flag), ("direct_giving_real_2025_usd", "employee channel only"))
        self.assertIn("employee channel only", label)
        trade = champions.decide_h5(registry.BY_ID["H5-pooled-trade"], cd)
        self.assertEqual(trade.status, gates.NOT_BUILT)
        self.assertIn("industry_money_with_trade_real_2025_usd", trade.reason)

    def test_primary_money_column_preferred_when_present(self):
        sw.write_champions(self.data, sw.champions_frame(primary_dv=True, trade=True))
        cd = champions.load_champions(self.data)
        col, _, flag, _ = champions.resolve_dv(cd, "industry_money_primary")
        self.assertEqual((col, flag), ("industry_money_primary_real_2025_usd", ""))
        d = champions.decide_h5(registry.BY_ID["H5-pooled-trade"], cd)
        self.assertEqual((d.status, d.dv_col), (gates.ESTIMABLE, "industry_money_with_trade_real_2025_usd"))

    def test_formula_cell_is_not_built(self):
        f = sw.champions_frame()
        f["name"] = f["name"].astype(object)
        f.loc[0, "name"] = "=A1"
        sw.write_champions(self.data, f)
        cd = champions.load_champions(self.data)
        self.assertFalse(cd.ok)
        self.assertIn("value starts with '='", cd.reason)


if __name__ == "__main__":
    unittest.main()
