# -*- coding: utf-8 -*-
"""Tests for scripts/calibration_report.py (build spec section 6.4).

Known answers: a hand-computable discrete forecast (Brier 0.17 = 0 - 0.08 + 0.25, AUC 0.82, AP 0.78, slope 1,
intercept 0); overconfident scores (true recalibration slope 0.5); the balanced-class-weight trap (intercept
-log 9, repaired by the prior-shift correction); scores worse than the base rate. Negative control:
well-calibrated scores. Usage errors exit 2. The run folder holds every output and the input is unchanged.
Fixtures are generated in code with fixed seeds; the three subprocess runs go through conftest's run_script,
the other scenarios call the same entry point (run_main) in-process to stay inside the time budget.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

try:
    from conftest import SCRIPTS, latest_report, latest_run_dir, sha256
except ImportError:  # conftest.py (agent S1) absent: minimal fallback with the same API (spec 6.6)
    SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(SCRIPTS))

    def latest_run_dir(out_dir):
        reports = sorted(pathlib.Path(out_dir).glob("*/report.json"), key=lambda p: p.stat().st_mtime)
        assert reports, f"no */report.json under {out_dir}"
        return reports[-1].parent

    def latest_report(out_dir):
        return json.loads((latest_run_dir(out_dir) / "report.json").read_text(encoding="utf-8"))

    def sha256(path):
        return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

    @pytest.fixture
    def run_script(tmp_path):
        def _run(name, *args, tmp_path=tmp_path, timeout=120, env=None):
            cmd = [sys.executable, str(SCRIPTS / name), *map(str, args), "--no-glassbox", "--out", str(tmp_path)]
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return _run

import calibration_report as cr  # noqa: E402  (scripts/ is on sys.path)
from _common import UsageError  # noqa: E402

SCRIPT = "calibration_report.py"


def checks(report: dict) -> dict:
    return {c["id"]: c for c in report["checks"]}


def write(df: pd.DataFrame, path: pathlib.Path) -> pathlib.Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def run_inprocess(out: pathlib.Path, *argv) -> tuple[int, dict | None]:
    code = cr.run_main(cr.SCRIPT, cr.main, cr.build_parser(),
                       argv=[*map(str, argv), "--no-glassbox", "--quiet", "--out", str(out)])
    return code, (latest_report(out) if code != 2 else None)


def calibrated(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.05, 0.95, n)
    return p, (rng.random(n) < p).astype(int)


def discrete_fixture() -> tuple[np.ndarray, np.ndarray]:
    """Five forecast levels, 20 rows each; the observed rate equals the forecast in every level."""
    rows = []
    for level, ones in ((0.1, 2), (0.3, 6), (0.5, 10), (0.7, 14), (0.9, 18)):
        rows += [(level, 1.0)] * ones + [(level, 0.0)] * (20 - ones)
    p, y = (np.array(v, dtype=float) for v in zip(*rows))
    return p, y


# ---- known answers computed by hand ----
def test_known_answer_discrete_forecasts():
    """Brier = 17.0/100 = 0.17; reliability 0; resolution 0.2*(0.4^2+0.2^2+0+0.2^2+0.4^2) = 0.08; uncertainty
    0.25; AUC = 2050/2500 = 0.82 (count of positive-above-negative pairs, ties half); AP = 0.36*0.9 +
    0.28*0.8 + 0.20*0.7 + 0.12*0.6 + 0.04*0.5 = 0.78; the recalibration fit solves at a = 0, b = 1 because
    the observed rate equals the forecast at every level."""
    p, y = discrete_fixture()
    idx, edges = cr.assign_bins(p, 10, "uniform")
    nb = len(edges) - 1
    assert sorted(set(idx.tolist())) == [1, 3, 5, 7, 9]  # one level per bin
    mur = cr.murphy(y, p, idx, nb)
    assert mur["brier"] == pytest.approx(0.17, abs=1e-12)
    assert mur["reliability"] == pytest.approx(0.0, abs=1e-12)
    assert mur["resolution"] == pytest.approx(0.08, abs=1e-12)
    assert mur["uncertainty"] == pytest.approx(0.25, abs=1e-12)
    assert mur["within_bin"] == pytest.approx(0.0, abs=1e-12)
    assert cr.ece_mce(y, p, idx, nb) == pytest.approx((0.0, 0.0), abs=1e-12)
    assert cr.auc_delong(y, p)[0] == pytest.approx(0.82, abs=1e-12)
    assert cr.average_precision(y, p) == pytest.approx(0.78, abs=1e-12)
    cal = cr.glm_calibration(y, cr.logit(p, 1e-6), 0.05)
    assert cal["slope"] == pytest.approx(1.0, abs=1e-6)
    assert cal["intercept"] == pytest.approx(0.0, abs=1e-6)


def test_known_answer_ece_weights_unequal_bins(tmp_path):
    """Bins of 10/30/60 rows at p = 0.2/0.5/0.8 with observed rates 0.4/0.5/0.7 (gaps 0.2/0/0.1).
    ECE = (10*0.2 + 30*0 + 60*0.1)/100 = 0.08; the unweighted mean of the gaps would be 0.10. MCE 0.2.
    Reliability (10*0.2^2 + 60*0.1^2)/100 = 0.01; resolution (10*0.21^2 + 30*0.11^2 + 60*0.09^2)/100 = 0.0129;
    uncertainty 0.61*0.39 = 0.2379; Brier = 0.01 - 0.0129 + 0.2379 = 0.235 (direct count: 23.5/100)."""
    spec = ((0.2, 10, 4), (0.5, 30, 15), (0.8, 60, 42))  # (forecast, rows, events)
    p = np.concatenate([np.full(n, level) for level, n, _ in spec])
    y = np.concatenate([np.r_[np.ones(k), np.zeros(n - k)] for _, n, k in spec])
    idx, edges = cr.assign_bins(p, 10, "uniform")
    nb = len(edges) - 1
    assert sorted(set(idx.tolist())) == [2, 5, 8]
    assert cr.ece_mce(y, p, idx, nb) == pytest.approx((0.08, 0.2), abs=1e-12)
    mur = cr.murphy(y, p, idx, nb)
    assert [mur[k] for k in ("brier", "reliability", "resolution", "uncertainty", "within_bin")] == pytest.approx(
        [0.235, 0.01, 0.0129, 0.2379, 0.0], abs=1e-12)
    frame = pd.DataFrame({"y": y.astype(int), "p": p})
    code, rep = run_inprocess(tmp_path / "out", "--data", write(frame, tmp_path / "in" / "bins.csv"), "--y", "y",
                              "--p", "p", "--strategy", "uniform")
    assert checks(rep)["CAL-04"]["value"] == pytest.approx(0.08, abs=1e-9)  # the reported number, not only the helper
    assert rep["data"]["mce"] == pytest.approx(0.2, abs=1e-12)


def test_second_computation_paths_agree():
    """AUC, its DeLong SE and AP against brute-force pair counts; the slope against a hand Newton-Raphson."""
    rng = np.random.default_rng(11)
    p = np.round(rng.uniform(0.02, 0.98, 400), 2)  # rounding creates ties
    y = (rng.random(400) < p).astype(float)
    pos, neg = p[y == 1], p[y == 0]
    psi = (pos[:, None] > neg[None, :]) + 0.5 * (pos[:, None] == neg[None, :])
    auc, se = cr.auc_delong(y, p)
    assert auc == pytest.approx(psi.mean(), abs=1e-12)
    delong = math.sqrt(psi.mean(axis=1).var(ddof=1) / len(pos) + psi.mean(axis=0).var(ddof=1) / len(neg))
    assert se == pytest.approx(delong, rel=1e-10)
    # AP = mean over positives of precision at that positive's score (ties share the threshold)
    ap = np.mean([(pos >= s).sum() / (p >= s).sum() for s in pos])
    assert cr.average_precision(y, p) == pytest.approx(ap, abs=1e-12)
    x = cr.logit(p, 1e-6)
    design, beta = np.column_stack([np.ones_like(x), x]), np.zeros(2)
    for _ in range(30):
        mu = 1 / (1 + np.exp(-design @ beta))
        beta += np.linalg.solve(design.T @ (design * (mu * (1 - mu))[:, None]), design.T @ (y - mu))
    assert cr.glm_calibration(y, x, 0.05)["slope"] == pytest.approx(beta[1], rel=1e-6)


def test_prior_shift_formula():
    """Moving from prior 0.5 to 0.1 shifts every logit by -log 9 and maps p = 0.5 to 0.1; the map inverts."""
    p = np.array([0.01, 0.2, 0.5, 0.8, 0.99])
    shifted = cr.prior_shift(p, 0.5, 0.1)
    assert cr.logit(shifted, 1e-12) - cr.logit(p, 1e-12) == pytest.approx(np.full(5, -math.log(9)), abs=1e-9)
    assert shifted[2] == pytest.approx(0.1)
    assert cr.prior_shift(shifted, 0.1, 0.5) == pytest.approx(p, abs=1e-12)


def test_known_answer_class_weight_trap(run_script, tmp_path):
    """Scores from a model fitted with balanced class weights (training prior 0.5) on a ~10% outcome:
    logit(p) = logit(p_true) + log 9. Calibration intercept ~ -log 9 = -2.197 (WOUNDED); the correction
    restores it to ~0; the raw scores lose to the base rate on Brier (KILLED); the slope stays ~1."""
    rng = np.random.default_rng(21)
    lt = rng.normal(-2.6, 1.2, 5000)
    y = (rng.random(5000) < 1 / (1 + np.exp(-lt))).astype(int)
    data = write(pd.DataFrame({"y": y, "p": 1 / (1 + np.exp(-(lt + math.log(9))))}), tmp_path / "in" / "w.csv")
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--data", data, "--y", "y", "--p", "p", "--prior-train", "0.5",
                      "--prior-target", "0.1", tmp_path=out)
    assert proc.returncode == 1, proc.stderr + proc.stdout
    rep = latest_report(out)
    c = checks(rep)
    assert c["CAL-02"]["verdict"] == "WOUNDED"
    assert c["CAL-02"]["value"] == pytest.approx(-math.log(9), abs=0.15)
    assert c["CAL-01"]["verdict"] == "KILLED"
    assert c["CAL-03"]["verdict"] == "SURVIVES"
    assert c["CAL-07"]["verdict"] == "WOUNDED" and "use p' as the probability" in c["CAL-07"]["detail"]
    after = rep["data"]["prior_shift"]["after"]
    assert abs(after["intercept"]) < 0.15 and after["ece"] < 0.03
    assert after["brier"] < rep["data"]["brier_base_rate"] < rep["data"]["brier"]


def test_known_answer_overconfident_scores_flag_the_slope(tmp_path):
    p, y = calibrated(4000, seed=8)
    over = 1 / (1 + np.exp(-2 * cr.logit(p, 1e-9)))  # logit doubled: the true recalibration slope is 0.5
    code, rep = run_inprocess(tmp_path / "out", "--data", write(pd.DataFrame({"y": y, "p": over}),
                                                                tmp_path / "in" / "o.csv"), "--y", "y", "--p", "p")
    c = checks(rep)
    assert code == 1
    assert c["CAL-03"]["verdict"] == "WOUNDED" and c["CAL-03"]["value"] == pytest.approx(0.5, abs=0.05)
    assert "overconfident" in c["CAL-03"]["detail"]
    assert c["CAL-04"]["verdict"] == "WOUNDED"
    assert c["CAL-05"]["verdict"] == "SURVIVES"  # ranking is untouched by a monotone distortion


def test_known_answer_worse_than_base_rate_is_killed(tmp_path):
    rng = np.random.default_rng(9)
    frame = pd.DataFrame({"y": (rng.random(3000) < 0.5).astype(int), "p": rng.uniform(0, 1, 3000)})
    code, rep = run_inprocess(tmp_path / "out", "--data", write(frame, tmp_path / "in" / "u.csv"), "--y", "y", "--p", "p")
    c = checks(rep)
    assert code == 1
    assert c["CAL-01"]["verdict"] == "KILLED"  # E[(p - y)^2] = 1/3 > 1/4 for uniform noise
    assert rep["data"]["brier"] == pytest.approx(1 / 3, abs=0.02)
    assert c["CAL-05"]["verdict"] in ("KILLED", "WOUNDED")


def test_miscalibration_in_one_group_is_localised(tmp_path):
    p, y = calibrated(4000, seed=12)
    g = np.where(np.arange(4000) < 2000, "A", "B")
    shifted = np.where(g == "B", 1 / (1 + np.exp(-(cr.logit(p, 1e-9) + 1.0))), p)  # group B over-predicts by 1 logit
    frame = pd.DataFrame({"y": y, "p": shifted, "g": g})
    code, rep = run_inprocess(tmp_path / "out", "--data", write(frame, tmp_path / "in" / "g.csv"),
                              "--y", "y", "--p", "p", "--group", "g")
    groups = {r["group"]: r for r in rep["data"]["groups"]}
    assert code == 1 and checks(rep)["CAL-06"]["verdict"] == "WOUNDED"
    assert groups["A"]["status"] == "ok" and groups["B"]["status"] == "off"
    assert groups["B"]["intercept"] == pytest.approx(-1.0, abs=0.2)


# ---- negative control and the run-folder contract ----
def test_negative_control_and_run_folder_contract(run_script, tmp_path):
    p, y = calibrated(4000, seed=5)
    data = write(pd.DataFrame({"y": y, "p": p, "g": np.where(np.arange(4000) % 2, "A", "B")}),
                 tmp_path / "in" / "preds.csv")
    before = sha256(data)
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--data", data, "--y", "y", "--p", "p", "--group", "g", tmp_path=out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rep = latest_report(out)
    assert {c["verdict"] for c in rep["checks"]} == {"SURVIVES"}
    assert {c["id"] for c in rep["checks"]} == {"CAL-01", "CAL-02", "CAL-03", "CAL-04", "CAL-05", "CAL-06"}
    assert 0.8 <= rep["data"]["calibration"]["slope"] <= 1.2 and rep["data"]["ece"] < 0.05
    run = latest_run_dir(out)
    assert list(out.iterdir()) == [run]
    assert {f.name for f in run.iterdir()} == {"report.json", "report.md", "reliability.csv", "groups.csv"}
    assert sha256(data) == before and [f.name for f in data.parent.iterdir()] == ["preds.csv"]
    assert rep["provenance"]["inputs"][0]["sha256"] == before


# ---- usage errors ----
def test_usage_error_exits_2_without_traceback(run_script, tmp_path):
    data = write(pd.DataFrame({"y": [0, 1] * 10, "p": np.linspace(0.1, 0.9, 20)}), tmp_path / "in" / "d.csv")
    proc = run_script(SCRIPT, "--data", data, "--y", "no_such_column", "--p", "p", tmp_path=tmp_path / "out")
    assert proc.returncode == 2
    assert "usage error" in proc.stderr and "Traceback" not in proc.stderr


@pytest.mark.parametrize("frame, extra", [
    (pd.DataFrame({"y": [0, 1] * 10, "p": np.linspace(0.1, 1.4, 20)}), []),                 # p outside [0, 1]
    (pd.DataFrame({"y": [1] * 20, "p": np.linspace(0.1, 0.9, 20)}), []),                    # a single outcome
    (pd.DataFrame({"y": [0, 2] * 10, "p": np.linspace(0.1, 0.9, 20)}), []),                 # outcome not 0/1
    (pd.DataFrame({"y": [0, 1] * 10, "p": np.linspace(0.1, 0.9, 20)}), ["--prior-train", "0.5"]),  # prior pair
    (pd.DataFrame({"y": [0, 1] * 10, "p": ["a"] * 20}), []),                                 # p not numeric
    (pd.DataFrame({"y": [0, 1] * 10, "p": [0.5] * 19 + [np.inf]}), []),                      # p infinite (CR-13)
])
def test_bad_inputs_are_usage_errors(tmp_path, frame, extra):
    code, _ = run_inprocess(tmp_path / "out", "--data", write(frame, tmp_path / "in" / "d.csv"),
                            "--y", "y", "--p", "p", *extra)
    assert code == 2


def test_argument_errors_exit_2():
    for argv in (["--data", "x.csv", "--y", "y"], ["--data", "x.csv", "--y", "y", "--p", "p", "--strategy", "bogus"]):
        with pytest.raises(SystemExit) as exc:
            cr.build_parser().parse_args(argv)
        assert exc.value.code == 2


def test_outcome_parsing():
    assert cr.to_binary(pd.Series(["Yes", "no", None, "TRUE"]), "--y").tolist()[:2] == [1.0, 0.0]
    with pytest.raises(UsageError):
        cr.to_binary(pd.Series(["yes", "maybe"]), "--y")
    assert np.isnan(cr.to_binary(pd.Series([1.0, None]), "--y")[1])
