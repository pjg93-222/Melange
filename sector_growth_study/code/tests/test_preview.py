"""PREVIEW tests C1-PV..C3-PV and H1-PV (Paul, 2026-09-25): fixed window 2021-2025, labels, the NOT IDENTIFIED rule
for the full core specification, wild cluster bootstrap enumeration, and H1-PV over every Mentat industry."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

import synth_workbooks
from helpers import sector_year_panel
from sgs import config, gates, registry, run_all
from sgs.sample import build_design, build_sample

PV = [t for t in registry.REGISTRY if t.label == "PREVIEW"]


class TestPreviewRegistry(unittest.TestCase):
    def test_ten_preview_tests(self):
        self.assertEqual([t.id for t in PV], ["C1-PV-reduced", "C1-PV-yearFE", "C1-PV-core", "C2-PV-reduced",
                                              "C2-PV-yearFE", "C2-PV-core", "C3-PV-reduced", "C3-PV-yearFE",
                                              "C3-PV-core", "H1-PV"])
        for t in PV:
            self.assertEqual((t.gate, t.flag, t.dv), ("preview", "PREVIEW - below the 6-year minimum",
                                                      "contributions_real_m"))
        by = registry.BY_ID
        self.assertEqual((by["C1-PV-reduced"].controls, by["C1-PV-reduced"].fe), (("pres_year", "midterm_year"), ("sector",)))
        self.assertEqual((by["C2-PV-yearFE"].controls, by["C2-PV-yearFE"].fe), ((), ("sector", "year")))
        self.assertEqual(by["C3-PV-core"].controls, registry.C_CONTROLS)
        self.assertTrue(by["C3-PV-core"].saturation_check)
        self.assertEqual((by["H1-PV"].table, by["H1-PV"].focal), ("industry_year", ("pres_year", "midterm_year")))
        self.assertEqual(config.PREVIEW_WINDOW, (2021, 2025))


class TestSaturation(unittest.TestCase):
    def test_five_year_level_parameters_on_five_years_are_not_identified(self):
        df = sector_year_panel(n_sectors=4, years=range(2021, 2026))
        tables = {"sector_year": df}
        core = registry.BY_ID["C1-PV-core"]
        d = gates.decide(core, tables)
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertTrue(d.reason.startswith("preview 2021-2025"))
        self.assertIn("NOT IDENTIFIED: 5 year-level parameters (common level of the sector baselines, pres_year, "
                      "midterm_year, exp_dem_house, exp_dem_senate) on 5 distinct years", d.reason)
        # the rank check alone would pass: the saturation rule is what blocks it
        smp = build_sample(tables, core, (2021, 2025))
        self.assertEqual(gates.year_level_check(build_design(smp.df, core)), (True, ""))
        red = registry.BY_ID["C1-PV-reduced"]
        self.assertEqual(gates.decide(red, tables).status, gates.ESTIMABLE)
        ok, why = gates.saturation_check(build_design(build_sample(tables, red, (2021, 2025)).df, red))
        self.assertTrue(ok, why)

    def test_fixed_window_ignores_the_window_arguments(self):
        df = sector_year_panel(n_sectors=3, years=range(2014, 2026))
        d = gates.decide(registry.BY_ID["C1-PV-reduced"], {"sector_year": df}, default_window=(2016, 2025),
                         fallback_search=(2008, 2025))
        self.assertEqual((d.status, d.window, d.window_kind, len(d.attempts)), (gates.ESTIMABLE, (2021, 2025), "preview", 1))

    def test_four_years_are_not_enough(self):
        df = sector_year_panel(n_sectors=3, years=range(2014, 2026))
        df.loc[df["year"] == 2021, "contributions_status"] = "missing"
        d = gates.decide(registry.BY_ID["C1-PV-reduced"], {"sector_year": df})
        self.assertEqual(d.status, gates.NOT_ESTIMABLE)
        self.assertIn("4 distinct years (2022-2025) < 5 required", d.reason)


class TestPreviewEndToEnd(unittest.TestCase):
    """Synthetic inputs shaped like the real ones: contributions 2021-2025 only, IEM blank after 2022 and the fill
    sheet for 2023-2026, community_banks as a non-study Mentat industry."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        base = Path(cls.tmp.name)
        data = synth_workbooks.build(base / "data", contrib_years=range(2021, 2026), extra_units=("community_banks",),
                                     iem_last_year=2022, expected_control=synth_workbooks.expected_control_sheet())
        cls.out = run_all.run(data_dir=data, results_dir=base / "results", B=9999, run_id="analysis-test-pv",
                              only=["C1-PV", "H1-PV", "C1"], log=lambda *a: None)
        cls.rows = {r["test_id"]: r for r in cls.out["est_rows"]}
        cls.coefs = [c for c in cls.out["coef_rows"] if c["test_id"] in {t.id for t in PV}]

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_reduced_and_year_fe_estimable_on_2021_2025(self):
        for tid in ("C1-PV-reduced", "C1-PV-yearFE"):
            r = self.rows[tid]
            self.assertEqual((r["status"], r["label"], r["window_used"], r["window_kind"], r["n_years"]),
                             ("ESTIMABLE", "PREVIEW", "2021-2025", "preview", 5), tid)
            c = [c for c in self.coefs if c["test_id"] == tid][0]
            self.assertLess(abs(c["estimate"] - 0.3), 0.1, tid)
            self.assertEqual(c["resid_df"], r["resid_df"])
        self.assertEqual(self.rows["C1"]["status"], "NOT ESTIMABLE")  # the CORE test keeps its 6-year gate

    def test_core_spec_reported_not_identified(self):
        r = self.rows["C1-PV-core"]
        self.assertEqual(r["status"], "NOT ESTIMABLE")
        self.assertTrue(r["reason_short"].startswith("preview 2021-2025: NOT IDENTIFIED: 5 year-level parameters on 5 "
                                                     "distinct years"), r["reason_short"])
        self.assertIn("2023 forecaster_final_call_binary (measured Nov 2024, after the year)", r["input_flags"])
        self.assertFalse([c for c in self.coefs if c["test_id"] == "C1-PV-core"])

    def test_every_preview_output_is_labeled(self):
        self.assertTrue(self.coefs)
        for c in self.coefs:
            self.assertIn("PREVIEW - below the 6-year minimum", c["flag"])
        for tid in [t.id for t in PV if t.id in self.rows]:
            self.assertEqual(self.rows[tid]["flag"], "PREVIEW - below the 6-year minimum")
        md = Path(self.out["report"]).read_text(encoding="utf-8")
        self.assertIn("### C1-PV-reduced (PREVIEW - below the 6-year minimum): ESTIMABLE", md)
        self.assertIn("### C1-PV-core (PREVIEW - below the 6-year minimum): NOT ESTIMABLE", md)
        emd = Path(self.out["estimability"]).read_text(encoding="utf-8")
        self.assertIn("| H1-PV | PREVIEW - below the 6-year minimum | ESTIMABLE | 2021-2025 |", emd)

    def test_bootstrap_enumerates_all_draws_when_small(self):
        c = [c for c in self.coefs if c["test_id"] == "C1-PV-reduced"][0]
        G = self.rows["C1-PV-reduced"]["n_sectors"]
        self.assertEqual(G, 5)
        self.assertEqual((c["boot_draws"], c["boot_enumerated"]), (6 ** G, True))
        self.assertGreaterEqual(c["boot_p"], 2 / 6 ** G)

    def test_h1_pv_covers_every_mentat_industry_and_matches_ols(self):
        r = self.rows["H1-PV"]
        self.assertEqual(r["status"], "ESTIMABLE")
        self.assertIn("community_banks", r["sectors"])
        self.assertEqual((r["n_sectors"], r["n"]), (6, 30))
        self.assertEqual(r["cluster_by"], "Mentat industry")
        df = self.out["decisions"]["H1-PV"].chosen.sample.df
        units = sorted(df["study_sector"].unique())
        X = np.column_stack([df["pres_year"], df["midterm_year"]] + [(df["study_sector"] == u).astype(float) for u in units])
        b = np.linalg.lstsq(X, df["y"].to_numpy(float), rcond=None)[0]
        got = {c["coefficient"]: c for c in self.coefs if c["test_id"] == "H1-PV"}
        self.assertAlmostEqual(got["pres_year"]["estimate"], b[0], places=9)
        self.assertAlmostEqual(got["midterm_year"]["estimate"], b[1], places=9)
        self.assertLess(abs(b[0] - 1.0), 1.0)
        self.assertTrue(got["pres_year"]["stratification"].startswith("STRATIFIED"))
        iy = self.out["tables"]["industry_year"]
        self.assertFalse(iy.loc[iy["study_sector"] == "community_banks", "is_study_sector"].any())


if __name__ == "__main__":
    unittest.main()
