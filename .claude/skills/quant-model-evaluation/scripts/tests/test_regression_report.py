# -*- coding: utf-8 -*-
"""Tests for scripts/regression_report.R (build spec 6.2 / 6.4). Skipped when Rscript cannot be found.

Every dataset is synthetic and generated here with a fixed seed. QME_R_HAND_ONLY=1 forces the base-R path so
the hand-built formulas are tested even on machines where sandwich/lmtest are installed.
"""
from __future__ import annotations

import pathlib
import re
import subprocess

import numpy as np
import pandas as pd
import pytest
import statsmodels.api as sm

from conftest import find_rscript, latest_report, sha256

pytestmark = pytest.mark.skipif(find_rscript() is None, reason="Rscript not found (set QME_RSCRIPT)")
R = "regression_report.R"
HAND = {"QME_R_HAND_ONLY": "1"}
VERDICTS = ("SURVIVES", "WOUNDED", "KILLED", "UNVERIFIED-HERE")


def _panel(G, per, seed):
    """y = 1 + 2 x1 - 0.5 x2 + cluster effect + noise, G clusters of `per` rows."""
    rng = np.random.default_rng(seed)
    g = np.repeat(np.arange(G), per)
    n = G * per
    x1 = rng.normal(size=n) + 0.3 * rng.normal(size=G)[g]
    x2 = rng.normal(size=n)
    y = 1.0 + 2.0 * x1 - 0.5 * x2 + 0.5 * rng.normal(size=G)[g] + rng.normal(size=n)
    return pd.DataFrame({"y": y, "x1": x1, "x2": x2, "g": [f"c{i:02d}" for i in g], "t": np.tile(np.arange(per), G),
                         "sector": np.array(list("abcd"))[g % 4]})


def _violations(seed=4):
    """Three planted violations, G = 60: curvature (0.8 u^2), noise scaled by exp(0.7 x2), and a Simpson reversal
    (sectors differ, so the pooled slope of y on x1 is about +1.08 while the slope inside every sector is -1)."""
    rng = np.random.default_rng(seed)
    s = np.repeat(np.arange(4), 90)
    u, x2 = rng.normal(size=s.size), rng.normal(size=s.size)
    y = 3.0 * s - u + 0.8 * u ** 2 + rng.normal(size=s.size) * np.exp(0.7 * x2)
    return pd.DataFrame({"y": y, "x1": 2.0 * s + u, "x2": x2, "g": rng.integers(0, 60, s.size),
                         "sector": np.array(list("abcd"))[s]})


def _series(n=200, seed=6):
    """One time series with AR(1) errors (rho 0.5): y = 1 + 0.8 x1 - 0.3 x2 + e."""
    rng = np.random.default_rng(seed)
    e = np.zeros(n)
    for i in range(1, n):
        e[i] = 0.5 * e[i - 1] + rng.normal()
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    return pd.DataFrame({"y": 1 + 0.8 * x1 - 0.3 * x2 + e, "x1": x1, "x2": x2, "t": np.arange(n)})


def _one_row_dummy(seed=9):
    """y = 1 + 2 x1 + e; d1 marks data row 17 only and has no true effect (leverage 1: the fit passes through it)."""
    rng = np.random.default_rng(seed)
    n = 200
    frame = pd.DataFrame({"x1": rng.normal(size=n), "g": rng.integers(0, 50, n)})
    frame["d1"] = 0
    frame.loc[16, "d1"] = 1
    frame["y"] = 1 + 2 * frame["x1"] + rng.normal(size=n)
    return frame


@pytest.fixture(scope="module")
def data(tmp_path_factory):
    d = tmp_path_factory.mktemp("regression_data")
    frames = {"clean": _panel(50, 12, 1), "few": _panel(8, 30, 2), "violations": _violations(), "series": _series(),
              "lev1": _one_row_dummy()}
    out = {name: d / f"{name}.csv" for name in frames}
    for name, frame in frames.items():
        frame.to_csv(out[name], index=False)
    out["brute"] = d / "brute_wcr.R"
    out["brute"].write_text(BRUTE_R, encoding="utf-8")
    return out


def _check(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


@pytest.mark.parametrize("env", [HAND, None], ids=["hand-built", "packages-if-installed"])
def test_contract_order_and_cr1_matches_statsmodels(run_script, tmp_path, data, env):
    """Known answer + negative control + run-dir contract on a clean clustered panel (G = 50)."""
    before = sha256(data["clean"])
    res = run_script(R, "--data", data["clean"], "--formula", "y ~ x1 + x2", "--cluster", "g", "--time", "t",
                     "--strata", "sector", env=env)
    assert res.returncode == 0, res.stdout + res.stderr          # negative control: nothing may be flagged
    out = res.stdout
    assert out.lstrip().startswith("Call:\nlm(formula = y ~ x1 + x2, data = dat)\n")   # the verbatim summary print
    assert "\nCoefficients:\n" in out and "Residual standard error:" in out and "Signif. codes:" in out
    pos = [out.index(s) for s in ("Call:", "=== Inference block:", "=== Diagnostics ===", "\nTrend: ")]
    assert pos == sorted(pos)
    assert re.search(r"^=== Inference block: CR1 \(G = 50, no bootstrap\) ===$", out, re.M)
    assert len(re.findall(r"^Trend: ", out, re.M)) == 1
    assert re.search(r"^Trend: x1 is positive .*same sign in 4 of 4 strata", out, re.M)

    rep = latest_report(tmp_path)
    frame = pd.read_csv(data["clean"])
    ref = sm.OLS(frame["y"], sm.add_constant(frame[["x1", "x2"]])).fit(
        cov_type="cluster", cov_kwds={"groups": pd.factorize(frame["g"])[0]})
    se = np.array([r["se"] for r in rep["data"]["inference"]])
    np.testing.assert_allclose(se, ref.bse.to_numpy(), rtol=1e-6)            # same (G/(G-1))(N-1)/(N-K) factor
    est = np.array([r["estimate"] for r in rep["data"]["inference"]])
    assert np.all(np.abs(est - np.array([1.0, 2.0, -0.5])) < 4 * se)       # planted coefficients recovered
    path = rep["data"]["vcov"]["covariance_path"]
    if env:
        assert path == "hand-built" and "hand-built CR1 (QME_R_HAND_ONLY=1)" in out
    if path == "sandwich":
        assert _check(rep, "LM-PARITY")["verdict"] == "SURVIVES"
    assert rep["counts"] == {v: sum(c["verdict"] == v for c in rep["checks"]) for v in VERDICTS}
    assert all(c["id"].startswith("LM-") for c in rep["checks"])             # REG- is the regulatory prefix
    runs = list(tmp_path.iterdir())
    assert len(runs) == 1 and {p.name for p in runs[0].iterdir()} == {"report.json", "report.md"}
    assert sha256(data["clean"]) == before == rep["provenance"]["inputs"][0]["sha256"]
    home = str(pathlib.Path.home())                                           # provenance never carries the home path
    text = (runs[0] / "report.json").read_text(encoding="utf-8").lower()
    assert home.lower().replace("\\", "\\\\") not in text and home.lower().replace("\\", "/") not in text
    if str(data["clean"]).lower().startswith(home.lower()):
        assert rep["provenance"]["inputs"][0]["path"].startswith("~")


def test_hc1_matches_statsmodels_and_unclustered_rows_are_unverified(run_script, tmp_path, data):
    res = run_script(R, "--data", data["clean"], "--formula", "y ~ x1 + x2", env=HAND)
    assert res.returncode == 3, res.stderr
    assert re.search(r"^=== Inference block: HC1 \(G = none, no bootstrap\) ===$", res.stdout, re.M)
    rep = latest_report(tmp_path)
    frame = pd.read_csv(data["clean"])
    ref = sm.OLS(frame["y"], sm.add_constant(frame[["x1", "x2"]])).fit(cov_type="HC1")
    np.testing.assert_allclose([r["se"] for r in rep["data"]["inference"]], ref.bse.to_numpy(), rtol=1e-6)
    assert _check(rep, "LM-UNITS")["verdict"] == "UNVERIFIED-HERE"


BRUTE_R = r"""
a <- commandArgs(trailingOnly = TRUE); d <- read.csv(a[1]); B <- as.integer(a[2]); b0s <- as.numeric(a[-(1:2)])
g <- as.integer(factor(as.character(d$g))); G <- max(g); N <- nrow(d)
vals <- if (G <= 11) c(-sqrt(1.5), -1, -sqrt(0.5), sqrt(0.5), 1, sqrt(1.5)) else c(-1, 1)
set.seed(20260930 + 1); V <- matrix(sample(vals, G * B, replace = TRUE), G, B)
X <- cbind(1, d$x1, d$x2); K <- 3; j <- 3
se_j <- function(u) { XtXi <- solve(crossprod(X)); S <- rowsum(X * u, g)
  sqrt(((G / (G - 1)) * ((N - 1) / (N - K)) * XtXi %*% crossprod(S) %*% XtXi)[j, j]) }
f <- lm.fit(X, d$y); bh <- f$coefficients[j]; sh <- se_j(f$residuals)
for (b0 in b0s) { r <- lm.fit(X[, -j], d$y - b0 * X[, j]); yt <- d$y - r$residuals
  ts <- vapply(seq_len(B), function(k) { fk <- lm.fit(X, yt + r$residuals * V[g, k])
    (fk$coefficients[j] - b0) / se_j(fk$residuals) }, 0)
  to <- abs((bh - b0) / sh); cat(sprintf("%.10f\n", mean(abs(ts) >= to - 1e-10 * max(1, to)))) }
"""


def test_few_clusters_webb_bootstrap_matches_brute_force_refits(run_script, tmp_path, data):
    """Planted few-cluster problem (G = 8): Webb weights, DESCRIPTIVE label, WOUNDED units check; the closed-form
    wild cluster restricted bootstrap must equal a brute-force refit-every-draw version with the same draws."""
    res = run_script(R, "--data", data["few"], "--formula", "y ~ x1 + x2", "--cluster", "g", "--B", "199", env=HAND)
    assert res.returncode == 1, res.stderr
    out = res.stdout
    assert re.search(r"^=== Inference block: CR1 \(G = 8, wild cluster restricted bootstrap, Webb six-point weights, "
                     r"B = 199\) ===$", out, re.M)
    assert "Inference is DESCRIPTIVE: G = 8 < 10." in out
    rep = latest_report(tmp_path)
    assert _check(rep, "LM-UNITS")["verdict"] == "WOUNDED"
    x1, x2 = rep["data"]["inference"][1], rep["data"]["inference"][2]
    assert x1["boot_p"] < 0.05 and x1["boot_ci_low"] < 2.0 < x1["boot_ci_high"]
    lo, hi = x2["boot_ci_low"], x2["boot_ci_high"]
    eps = 1e-6 * (hi - lo)
    brute = subprocess.run([find_rscript(), str(data["brute"]), str(data["few"]), "199",
                            *map(str, (0.0, lo - eps, lo + eps, hi - eps, hi + eps))],
                           capture_output=True, text=True, timeout=120)
    p0, p_out_lo, p_in_lo, p_in_hi, p_out_hi = map(float, brute.stdout.split())
    assert p0 == pytest.approx(x2["boot_p"], abs=1e-12)
    assert p_out_lo < 0.05 <= p_in_lo and p_out_hi < 0.05 <= p_in_hi     # CI = where the bootstrap p crosses 0.05


def test_planted_curvature_heteroskedasticity_and_strata_reversal_are_flagged(run_script, tmp_path, data):
    res = run_script(R, "--data", data["violations"], "--formula", "y ~ x1 + x2", "--cluster", "g",
                     "--strata", "sector", env=HAND)
    assert res.returncode == 1, res.stderr
    rep = latest_report(tmp_path)
    assert _check(rep, "LM-RESET")["verdict"] == "WOUNDED"
    assert _check(rep, "LM-BP")["verdict"] == "WOUNDED"
    assert _check(rep, "LM-UNITS")["verdict"] == "SURVIVES"
    strata = _check(rep, "LM-STRATA")
    assert strata["verdict"] == "KILLED" and strata["value"] == 0
    assert rep["data"]["inference"][1]["estimate"] > 0 and all(s["estimate"] < 0 for s in rep["data"]["strata"])
    assert re.search(r"^Trend: x1 is positive .*same sign in 0 of 4 strata", res.stdout, re.M)


def test_planted_one_row_dummy_is_flagged_not_trusted(run_script, tmp_path, data):
    """Review CR-05: a one-row dummy has leverage 1, its residual is 0, and HC/CR SEs for it come out tiny (spurious
    p ~ 1e-7 with no true effect). The run must say so: LM-LEVERAGE WOUNDED naming d1, Cook's NaN row named, exit 1."""
    res = run_script(R, "--data", data["lev1"], "--formula", "y ~ x1 + d1", "--cluster", "g", env=HAND)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "Leverage-1 rows (data rows 17) are fitted exactly: robust SEs for d1 are unreliable" in res.stdout
    rep = latest_report(tmp_path)
    lev = _check(rep, "LM-LEVERAGE")
    assert lev["verdict"] == "WOUNDED" and lev["detail"].startswith(
        "robust SEs are unreliable for coefficients identified by single rows (e.g. one-row dummies): d1 (data rows 17)")
    cook = _check(rep, "LM-COOK")
    assert cook["verdict"] == "WOUNDED" and "undefined (leverage 1) at data rows 17" in cook["detail"]
    assert rep["data"]["diagnostics"]["leverage"]["terms"] == ["d1"]


def test_uncomputable_diagnostics_are_recorded_unverified(run_script, tmp_path, data):
    """Review CR-26: an intercept-only model has no RESET (constant fitted values) and no Breusch-Pagan regressor;
    both must appear as UNVERIFIED-HERE with the reason, never silently absent."""
    res = run_script(R, "--data", data["clean"], "--formula", "y ~ 1", "--cluster", "g", env=HAND)
    assert res.returncode == 3, res.stdout + res.stderr
    rep = latest_report(tmp_path)
    for cid in ("LM-RESET", "LM-BP"):
        c = _check(rep, cid)
        assert c["verdict"] == "UNVERIFIED-HERE" and c["detail"].startswith("not computable:")
    assert "Collinearity and VIF: not applicable" in res.stdout


def test_two_way_clusters_match_statsmodels_and_label_the_one_way_bootstrap(run_script, tmp_path, data):
    """CGM two-way CR1 against statsmodels; the bootstrap runs by the smaller dimension and the Trend line says it is
    one-way (review CR-33)."""
    res = run_script(R, "--data", data["clean"], "--formula", "y ~ x1 + x2", "--cluster", "g", "--cluster2", "t",
                     "--B", "199", env=HAND)
    assert res.returncode == 1, res.stdout + res.stderr                        # G = 12 in the smaller dimension
    assert re.search(r"^=== Inference block: CR1 two-way \(G = 50 x 12, wild cluster restricted bootstrap by t, "
                     r"Rademacher weights, B = 199\) ===$", res.stdout, re.M)
    assert re.search(r"^Trend: .*wild-bootstrap \(one-way by t\) p", res.stdout, re.M)
    frame = pd.read_csv(data["clean"])
    groups = np.column_stack([pd.factorize(frame["g"])[0], frame["t"].to_numpy()])
    ref = sm.OLS(frame["y"], sm.add_constant(frame[["x1", "x2"]])).fit(cov_type="cluster", cov_kwds={"groups": groups})
    np.testing.assert_allclose([r["se"] for r in latest_report(tmp_path)["data"]["inference"]], ref.bse.to_numpy(),
                               rtol=1e-6)


def test_newey_west_matches_statsmodels_hac_and_states_its_assumption(run_script, tmp_path, data):
    res = run_script(R, "--data", data["series"], "--formula", "y ~ x1 + x2", "--vcov", "NW", "--time", "t",
                     "--nw-lag", "4", env=HAND)
    assert res.returncode == 3, res.stdout + res.stderr
    assert re.search(r"^=== Inference block: NW \(G = none, no bootstrap\) ===$", res.stdout, re.M)
    rep = latest_report(tmp_path)
    frame = pd.read_csv(data["series"])
    ref = sm.OLS(frame["y"], sm.add_constant(frame[["x1", "x2"]])).fit(
        cov_type="HAC", cov_kwds={"maxlags": 4, "use_correction": False})           # Bartlett, no df adjustment
    np.testing.assert_allclose([r["se"] for r in rep["data"]["inference"]], ref.bse.to_numpy(), rtol=1e-6)
    units = _check(rep, "LM-UNITS")
    assert units["verdict"] == "UNVERIFIED-HERE"
    assert units["detail"] == ("one time series; Newey-West (lag 4) allows serial correlation up to lag 4; "
                               "stationarity is assumed. See core-statistics.md for the ADF/KPSS checks.")
    assert _check(rep, "LM-SERIAL")["verdict"] == "SURVIVES"                      # AR(1) errors, covered by NW


def test_cr2_without_sandwich_is_unverified_and_falls_back_to_cr1(run_script, tmp_path, data):
    res = run_script(R, "--data", data["clean"], "--formula", "y ~ x1 + x2", "--cluster", "g", "--vcov", "CR2", env=HAND)
    assert res.returncode == 3, res.stderr
    assert re.search(r"^=== Inference block: CR1 \(G = 50, no bootstrap\) ===$", res.stdout, re.M)
    cr2 = _check(latest_report(tmp_path), "LM-CR2")
    assert cr2["verdict"] == "UNVERIFIED-HERE" and "CR2 needs sandwich" in cr2["detail"]


@pytest.mark.parametrize("case", ["cr1-without-cluster", "unknown-column", "formula-runs-code"])
def test_usage_errors_exit_2_before_any_output(run_script, tmp_path, data, case):
    args = {"cr1-without-cluster": ["--data", data["clean"], "--formula", "y ~ x1", "--vcov", "CR1"],
            "unknown-column": ["--data", data["clean"], "--formula", "y ~ x1 + nope"],
            "formula-runs-code": ["--data", data["clean"], "--formula", "y ~ x1 + I(system('echo pwned'))"]}[case]
    res = run_script(R, *args)
    assert res.returncode == 2
    assert res.stdout == "" and "usage error" in res.stderr
    if case == "formula-runs-code":
        assert "outside the allowed list: system" in res.stderr
    assert not any(tmp_path.iterdir())                                       # nothing written on a usage error


@pytest.mark.parametrize("shape", ["({code})", "{{{code}; y ~ x1}}"], ids=["paren", "brace"])
def test_formula_text_is_never_evaluated(run_script, tmp_path, data, shape):
    """stats:::formula.character eval()s a top-level ( or { call; the script must only parse the text.
    Each payload would create a sentinel file if it ran."""
    sentinel = tmp_path / "pwned"
    formula = shape.format(code=f"file.create('{sentinel.as_posix()}')")
    res = run_script(R, "--data", data["clean"], "--formula", formula)
    assert res.returncode == 2, res.stdout + res.stderr
    assert res.stdout == "" and "two-sided formula" in res.stderr
    assert not sentinel.exists() and not any(tmp_path.iterdir())
