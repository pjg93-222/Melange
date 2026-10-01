# -*- coding: utf-8 -*-
"""Tests for scripts/confounding_sensitivity.py (build spec 6.3 / 6.4 / 6.5).

Known answers: the E-value worked example (RR 3.9 -> 7.26, CI limit 1.8 -> 3.0; VanderWeele & Ding 2017), the RV
formula of spec 6.5, the published Darfur robustness values (Cinelli & Hazlett 2020: partial R^2 2.19%, RV 13.88%,
RV_alpha 7.63%), benchmark bounds recomputed with the R package sensemakr 0.1.6, and a hand-solved Oster case.
"""
from __future__ import annotations

import csv
import math

import pytest

import confounding_sensitivity as cs
from conftest import SCRIPTS, latest_report, latest_run_dir, sha256

TABLE = SCRIPTS / "tests" / "fixtures" / "confounding_sensitivity" / "scenarios.csv"
EST, SE, DOF = 0.097315819285, 0.0232565378098, 783            # Darfur: 'directlyharmed' coefficient
R2DXJ, R2YXJ = 0.00908106519033, 0.109033915428                  # benchmark covariate 'female'
# sensemakr 0.1.6: sensemakr(model, treatment = "directlyharmed", benchmark_covariates = "female", kd = 1:3)$bounds
SENSEMAKR_BOUNDS = [(1, 0.00916428667505, 0.124640923036, 0.0752202712144, 0.0218733277438, 3.43890386025),
                    (2, 0.0183285733501, 0.2493240642, 0.0529151723845, 0.020350062078, 2.60024623914),
                    (3, 0.0274928600251, 0.374050471038, 0.0303960234642, 0.0186700648171, 1.62806202131)]


def _inproc(out, *args):
    code = cs.run_main(cs.SCRIPT, cs.main, cs.build_parser(),
                       argv=[*map(str, args), "--no-glassbox", "--quiet", "--out", str(out)])
    return code, (latest_report(out) if code != 2 else None)


def _verdicts(rep):
    return {c["id"]: c["verdict"] for c in rep["checks"]}


# --------------------------------------------------------------------------- closed forms
def test_evalue_worked_example():
    assert cs.evalue_rr(3.9) == pytest.approx(3.9 + math.sqrt(3.9 * 2.9), rel=1e-15)
    assert round(cs.evalue_rr(3.9), 2) == 7.26
    assert cs.evalue_rr(1.8) == pytest.approx(3.0, abs=1e-12)                  # 1.8 + sqrt(1.8 * 0.8)
    assert cs.evalue_rr(1 / 3.9) == pytest.approx(cs.evalue_rr(3.9), rel=1e-12)  # protective: use 1/RR
    assert cs.evalue_rr(1.0) == 1.0


def test_ratio_conversions():
    assert cs.to_rr("odds_ratio", 4.0, rare=False) == pytest.approx(2.0)       # common outcome: sqrt(OR)
    assert cs.to_rr("odds_ratio", 4.0, rare=True) == 4.0
    assert cs.to_rr("hr", 1.0, rare=False) == pytest.approx(1.0)
    hr = 2.0
    assert cs.to_rr("hr", hr, rare=False) == pytest.approx((1 - 0.5 ** math.sqrt(hr)) / (1 - 0.5 ** math.sqrt(1 / hr)))


def test_robustness_values_spec_formula_and_published_darfur():
    t = EST / SE
    r2yd, rv, rva = cs.robustness_values(t, DOF, 1.0, 0.05)
    f = abs(t) / math.sqrt(DOF)
    assert rv == pytest.approx(0.5 * (math.sqrt(f ** 4 + 4 * f ** 2) - f ** 2), rel=1e-14)   # spec 6.5
    assert (round(100 * r2yd, 2), round(100 * rv, 2), round(100 * rva, 2)) == (2.19, 13.88, 7.63)
    assert (r2yd, rv, rva) == (pytest.approx(0.0218730933411, rel=1e-9), pytest.approx(0.138776353894, rel=1e-9),
                               pytest.approx(0.0762579655449, rel=1e-9))


# sensemakr 0.1.6 on random draws and one extreme case: (t, df, q, alpha, partial R^2, RV_q [alpha = 1], RV_q,alpha).
SENSEMAKR_RV = [
    (-8.17592009577485, 1736.0, 0.392886187229306, 0.0671699235448614, 0.0370778655913895, 0.0741808192796038,
     0.0325769736240349),
    (-3.93430871148532, 78.0, 0.692735022678971, 0.142612078969833, 0.16558607422099, 0.264631113118099,
     0.13035763116644),
    (1.68360547095969, 27.0, 0.848075094493106, 0.181521451410372, 0.0950082884024583, 0.239612866881641,
     0.0055291023109267),
    (3.09489388992531, 246.0, 1.3090396179352, 0.109815102573484, 0.0374772257047208, 0.227088839010476,
     0.144112869628787),
    (1e10, 100.0, 1.0, 0.05, 1.0, 1.0, 1.0),
]


@pytest.mark.parametrize("t, dof, q, alpha, r2, rv, rva", SENSEMAKR_RV)
def test_robustness_values_match_sensemakr(t, dof, q, alpha, r2, rv, rva):
    got = cs.robustness_values(t, dof, q, alpha)
    assert got == (pytest.approx(r2, rel=1e-12), pytest.approx(rv, rel=1e-12), pytest.approx(rva, rel=1e-12))


def test_rv_is_stable_at_huge_t(tmp_path):
    """Review CR-09: the textbook form 0.5(sqrt(f^4 + 4f^2) - f^2) cancels to 0 for f >~ 3e8, which flagged the most
    robust estimates as fragile. At f = |t|/sqrt(df) = 1e9 sensemakr gives 1."""
    r2yd, rv, rva = cs.robustness_values(1e10, 100.0, 1.0, 0.05)          # f = 1e10 / sqrt(100) = 1e9
    assert (r2yd, rv, rva) == (pytest.approx(1.0, abs=1e-12), pytest.approx(1.0, abs=1e-12),
                               pytest.approx(1.0, abs=1e-12))
    assert cs.rv_from_f(1e9) == pytest.approx(1.0, abs=1e-15) and cs.rv_from_f(0.0) == 0.0
    code, rep = _inproc(tmp_path, "--mode", "sensemakr", "--estimate", "1", "--se", "1e-10", "--dof", "100")
    assert code == 0 and _verdicts(rep) == {"CS-RV": "SURVIVES"}
    assert rep["checks"][0]["value"] == pytest.approx(1.0, abs=1e-12)


def test_bench_criterion_lists_only_evaluated_multiples(tmp_path):
    """Review CR-10: kd 2 and 3 are impossible for a benchmark with partial R^2 0.4 with the treatment."""
    code, rep = _inproc(tmp_path, "--mode", "sensemakr", "--estimate", "5", "--se", "0.1", "--dof", "500",
                        "--r2dz-bench", "0.4", "--r2yz-bench", "0.001")
    bench = next(c for c in rep["checks"] if c["id"] == "CS-BENCH")
    assert bench["criterion"].startswith("sign kept for kd in 1;")
    assert "kd 2,3 impossible given the benchmark's partial R^2, not evaluated" in bench["criterion"]


@pytest.mark.parametrize("kd, r2dz, r2yz, adj, adj_se, adj_t", SENSEMAKR_BOUNDS)
def test_benchmark_bounds_match_sensemakr(kd, r2dz, r2yz, adj, adj_se, adj_t):
    b_r2dz, b_r2yz, capped = cs.bench_bound(R2DXJ, R2YXJ, kd, kd)
    assert (b_r2dz, b_r2yz, capped) == (pytest.approx(r2dz, rel=1e-9), pytest.approx(r2yz, rel=1e-9), False)
    out = cs.adjusted(EST, SE, DOF, b_r2dz, b_r2yz)
    assert (out["estimate"], out["se"], out["t"]) == (pytest.approx(adj, rel=1e-9), pytest.approx(adj_se, rel=1e-9),
                                                      pytest.approx(adj_t, rel=1e-9))


def test_impossible_benchmark_multiple_is_rejected():
    assert cs.bench_bound(0.6, 0.1, 2.0, 2.0) is None                          # implied R2dz = 2 * 0.6 / 0.4 >= 1


def test_oster_hand_solved():
    # delta = b (R - R0) / ((b0 - b)(Rmax - R)) = 0.6 * 0.2 / (0.4 * 0.09) = 10/3;
    # beta* = b - (b0 - b)(Rmax - R)/(R - R0) = 0.6 - 0.4 * 0.09 / 0.2 = 0.42
    delta, beta_star = cs.oster_delta(1.0, 0.10, 0.6, 0.30, 0.39)
    assert delta == pytest.approx(10 / 3, rel=1e-12) and beta_star == pytest.approx(0.42, rel=1e-12)
    assert cs.oster_delta(1.0, 0.1, 1.0, 0.3, 0.39) == (math.inf, 1.0)          # coefficient did not move


# --------------------------------------------------------------------------- subprocess contract tests
def test_table_mode_run_folder_and_inputs_unchanged(run_script, tmp_path):
    """Negative control: three robust scenarios (one per mode) must not be flagged."""
    before = sha256(TABLE)
    res = run_script("confounding_sensitivity", "--table", TABLE)
    assert res.returncode == 0, res.stdout + res.stderr
    rep = latest_report(tmp_path)
    assert _verdicts(rep) == {"CS-RV[darfur]": "SURVIVES", "CS-BENCH[darfur]": "SURVIVES",
                              "CS-EVALUE[evalue-book]": "SURVIVES", "CS-OSTER[oster-hand]": "SURVIVES"}
    ev = next(s for s in rep["data"]["scenarios"] if s["mode"] == "evalue")["results"]
    assert ev["evalue"] == pytest.approx(7.263, abs=5e-4) and ev["evalue_ci"] == pytest.approx(3.0, abs=1e-12)
    run = latest_run_dir(tmp_path)
    with open(run / "results.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert [r["label"] for r in rows] == ["darfur", "evalue-book", "oster-hand"]
    assert [p.name for p in tmp_path.iterdir()] == [run.name]
    assert {p.name for p in run.iterdir()} == {"report.json", "report.md", "results.csv"}
    assert sha256(TABLE) == before == rep["provenance"]["inputs"][0]["sha256"]
    assert "note" in (run / "report.md").read_text(encoding="utf-8")            # unknown column reported, not used


def test_planted_fragility_is_wounded_and_benchmark_flip_is_killed(run_script, tmp_path):
    # t = 0.8 on 300 df: RV ~ 0.045 < 0.05; a confounder as strong as the benchmark (partial R^2 0.05 both
    # ways) implies |bias| ~ 0.99 se > |estimate| = 0.8 se, so the sign flips at kd = 1.
    res = run_script("confounding_sensitivity", "--mode", "sensemakr", "--estimate", "0.08", "--se", "0.1",
                     "--dof", "300", "--r2dz-bench", "0.05", "--r2yz-bench", "0.05")
    assert res.returncode == 1, res.stderr
    rep = latest_report(tmp_path)
    assert _verdicts(rep) == {"CS-RV": "WOUNDED", "CS-BENCH": "KILLED"}
    assert next(c for c in rep["checks"] if c["id"] == "CS-BENCH")["value"] == 1.0


@pytest.mark.parametrize("args", [
    ["--mode", "sensemakr", "--estimate", "1", "--dof", "50"],                    # --se missing
    ["--mode", "evalue", "--rr", "2", "--or", "3"],                               # two effect measures
])
def test_usage_errors_exit_2(run_script, tmp_path, args):
    res = run_script("confounding_sensitivity", *args)
    assert res.returncode == 2 and "usage error" in res.stderr


# --------------------------------------------------------------------------- in-process behaviour
def test_evalue_ci_crossing_null_and_smd_conversion(tmp_path):
    code, rep = _inproc(tmp_path / "a", "--mode", "evalue", "--rr", "1.5", "--lo", "0.9", "--hi", "2.5")
    assert code == 1 and rep["data"]["scenarios"][0]["results"]["evalue_ci"] == 1.0
    code, rep = _inproc(tmp_path / "b", "--mode", "evalue", "--smd", "0.5", "--se", "0.1", "--e-min", "1.5")
    res = rep["data"]["scenarios"][0]["results"]
    assert res["rr"] == pytest.approx(math.exp(0.455)) and res["rr_lo"] == pytest.approx(math.exp(0.455 - 0.178))
    assert code == 0


def test_oster_fragile_and_undefined(tmp_path):
    code, rep = _inproc(tmp_path / "a", "--mode", "oster", "--beta-short", "1.0", "--r2-short", "0.1",
                        "--beta-long", "0.2", "--r2-long", "0.3")                  # Rmax = 0.39 -> delta = 0.139
    assert code == 1 and _verdicts(rep) == {"CS-OSTER": "WOUNDED"}
    code, rep = _inproc(tmp_path / "b", "--mode", "oster", "--beta-short", "1.0", "--r2-short", "0.3",
                        "--beta-long", "0.5", "--r2-long", "0.3")
    assert code == 3 and _verdicts(rep) == {"CS-OSTER": "UNVERIFIED-HERE"}
    code, _ = _inproc(tmp_path / "c", "--mode", "oster", "--beta-short", "1.0", "--r2-short", "0.1",
                      "--beta-long", "0.5", "--r2-long", "0.3", "--rmax", "0.2")    # Rmax below R^2: usage error
    assert code == 2
