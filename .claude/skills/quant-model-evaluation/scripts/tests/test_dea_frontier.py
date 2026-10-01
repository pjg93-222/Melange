"""Tests for scripts/dea_frontier.py (BUILD_SPEC 6.4): hand-solved known answers, an independent dual-LP
computation path, a planted outlier and its negative control, the Simar-Wilson bootstrap on a planted-truth
DGP, usage errors, and run-folder hygiene."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import numpy as np
import pytest
from scipy.optimize import linprog

try:  # shared helpers from scripts/tests/conftest.py (BUILD_SPEC 6.6)
    from conftest import SCRIPTS, latest_report
except ImportError:  # conftest.py not written yet: minimal local fallback with the same API
    SCRIPTS = pathlib.Path(__file__).resolve().parents[1]

    def latest_report(tmp_path):
        found = sorted(pathlib.Path(tmp_path).glob("*/report.json"), key=lambda p: p.stat().st_mtime)
        assert found, f"no report.json under {tmp_path}"
        return json.loads(found[-1].read_text(encoding="utf-8"))

    @pytest.fixture
    def run_script():
        def _run(name, *args, tmp_path):
            return subprocess.run([sys.executable, str(SCRIPTS / name), *[str(a) for a in args],
                                   "--no-glassbox", "--out", str(tmp_path)],
                                  capture_output=True, text=True, timeout=120)
        return _run

S = "dea_frontier.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "dea_frontier"
ONE, TWO = FIX / "one_input.csv", FIX / "two_input.csv"

# In-process import (collection time) for the SW98 and failure-path tests: heavy imports made after the
# subprocess tests have run are several times slower on this Windows machine.
sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import dea_frontier as dea  # noqa: E402


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _scores(rep):
    return {row["id"]: row for row in rep["data"]["scores"]}


def _check(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


def _ok(r, *codes):
    """Assert the exit code, showing the child's output when it is unexpected."""
    assert r.returncode in codes, f"exit {r.returncode}\nSTDERR:\n{r.stderr[-2000:]}\nSTDOUT:\n{r.stdout[-1000:]}"
    return r


def _write_csv(path, header, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [",".join(header)] + [",".join(f"{v:.17g}" for v in row) for row in zip(*cols)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _dual_scores(X, Y, vrs):
    """Second computation path: the multiplier (dual) form, max u'y0 (+ u0 under VRS) s.t. v'x0 = 1,
    u'y_j - v'x_j (+ u0) <= 0, u, v >= 0, u0 free (Charnes, Cooper & Rhodes 1978; Banker, Charnes & Cooper
    1984). By LP duality its optimum equals the envelopment score the script reports (input orientation)."""
    n, m = X.shape
    s = Y.shape[1]
    out = []
    for o in range(n):
        c = np.r_[-Y[o], np.zeros(m), [-1.0] if vrs else []]
        a_ub = np.c_[Y, -X, np.ones((n, 1))] if vrs else np.c_[Y, -X]
        a_eq = np.r_[np.zeros(s), X[o], [0.0] if vrs else []][None, :]
        bounds = [(0, None)] * (s + m) + ([(None, None)] if vrs else [])
        res = linprog(c, A_ub=a_ub, b_ub=np.zeros(n), A_eq=a_eq, b_eq=[1.0], bounds=bounds, method="highs")
        assert res.status == 0
        out.append(-res.fun)
    return np.array(out)


def test_known_answer_one_input_vrs_crs_scale_super(run_script, tmp_path):
    # one_input.csv (x, y): A(2,2) B(4,6) C(6,6) D(8,7) E(5,3).
    # CRS: theta = (y/x) / max(y/x); ratios 1, 1.5, 1, 0.875, 0.6 -> 2/3, 1, 2/3, 7/12, 0.4.
    # VRS frontier A-B-D: A, B, D score 1 (only D reaches y = 7); C gets y = 6 from B at x = 4 -> 4/6;
    # E gets y = 3 from 0.75A + 0.25B at x = 2.5 -> 0.5. SE = CRS/VRS. NIRS (sum lam <= 1) reaches A and E by
    # scaling B down -> increasing returns there; D keeps its VRS score -> decreasing; B and C have SE = 1.
    # VRS super-efficiency: without A the cheapest way to y >= 2 is B (x = 4) -> 2.0; without B it is C
    # (x = 6) -> 1.5; without D nothing reaches y = 7 -> infeasible.
    _ok(run_script(S, "--data", ONE, "--inputs", "x", "--outputs", "y", "--id", "unit", "--rts", "vrs", "--super",
                   tmp_path=tmp_path), 1)  # DEA-DIM is WOUNDED: n = 5 < max(1*1, 3*(1+1)) = 6
    rep = latest_report(tmp_path)
    sc = _scores(rep)
    vrs = {"A": 1, "B": 1, "C": 2 / 3, "D": 1, "E": 0.5}
    crs = {"A": 2 / 3, "B": 1, "C": 2 / 3, "D": 7 / 12, "E": 0.4}
    for u in vrs:
        assert sc[u]["eff"] == pytest.approx(vrs[u], abs=1e-6)
        assert sc[u]["eff_crs"] == pytest.approx(crs[u], abs=1e-6)
        assert sc[u]["scale_eff"] == pytest.approx(crs[u] / vrs[u], abs=1e-6)
    assert {u: sc[u]["rts_region"] for u in sc} == {"A": "increasing", "B": "constant", "C": "constant",
                                                     "D": "decreasing", "E": "increasing"}
    assert sc["E"]["peers"] == "A:0.75;B:0.25" and sc["C"]["peers"] == "B:1"
    assert sc["A"]["super_eff"] == pytest.approx(2.0, abs=1e-6)
    assert sc["B"]["super_eff"] == pytest.approx(1.5, abs=1e-6)
    assert sc["D"]["super_eff"] is None and sc["D"]["super_status"] == "infeasible"
    assert _check(rep, "DEA-DIM")["verdict"] == "WOUNDED"
    # D (infeasible = most extreme) is dropped first; it is nobody's peer, so nobody moves: negative control
    assert _check(rep, "DEA-INFLUENCE")["verdict"] == "SURVIVES"
    assert rep["data"]["influence"]["removed"] == ["D"]


def test_known_answer_two_inputs_weak_efficiency_and_super(run_script, tmp_path):
    # two_input.csv, y = 1 for all: A(2,4) B(4,2) C(4,4) D(6,1) E(3,6) F(5,3) G(8,1). Isoquant A-B-D, then flat
    # from D. C: ray (1,1) meets A-B at (3,3) -> 0.75 with A .5 + B .5; E: ray (1,2) meets A -> 2/3;
    # F: ray (5,3) meets A-B at (3.75,2.25) -> 0.75 with A .125 + B .875; G: radial score 1 but it uses 2 more
    # of x1 than D -> weakly efficient. Super-efficiency: A -> E lies on its ray at 1.5x -> 1.5;
    # B -> segment A-D at (4.4,2.2) -> 1.1; D -> segment B-G at (7.2,1.2) -> 1.2; G -> D still covers it -> 1.0.
    _ok(run_script(S, "--data", TWO, "--inputs", "x1,x2", "--outputs", "y", "--id", "unit", "--rts", "crs",
                   "--super", tmp_path=tmp_path), 1)  # n = 7 < 9: DEA-DIM WOUNDED
    sc = _scores(latest_report(tmp_path))
    for u, v in {"A": 1, "B": 1, "C": 0.75, "D": 1, "E": 2 / 3, "F": 0.75, "G": 1}.items():
        assert sc[u]["eff"] == pytest.approx(v, abs=1e-6)
    assert sc["G"]["weakly_efficient"] is True and sc["G"]["slack_x1"] == pytest.approx(2.0, abs=1e-6)
    assert not any(sc[u]["weakly_efficient"] for u in "ABCDEF")
    assert sc["C"]["peers"] in ("A:0.5;B:0.5", "B:0.5;A:0.5") and sc["F"]["peers"] == "B:0.875;A:0.125"
    for u, v in {"A": 1.5, "B": 1.1, "D": 1.2, "G": 1.0, "C": 0.75}.items():
        assert sc[u]["super_eff"] == pytest.approx(v, abs=1e-6)


def test_dual_lp_second_path_and_dimensionality_negative_control(run_script, tmp_path):
    # Random 2-input / 2-output data, n = 40 >= max(2*2, 3*(2+2)) = 12: the dimensionality check must NOT fire,
    # and every CRS and VRS score must equal the optimum of the independently solved multiplier (dual) LP.
    rng = np.random.default_rng(3)
    cols = [rng.uniform(1, 10, 40) for _ in range(4)]
    data = _write_csv(tmp_path / "in" / "random.csv", ["x1", "x2", "y1", "y2"], cols)
    _ok(run_script(S, "--data", data, "--inputs", "x1,x2", "--outputs", "y1,y2", "--rts", "crs",
                   tmp_path=tmp_path / "out"), 0)
    rep = latest_report(tmp_path / "out")
    assert _check(rep, "DEA-DIM")["verdict"] == "SURVIVES"
    rows = rep["data"]["scores"]
    X, Y = np.c_[cols[0], cols[1]], np.c_[cols[2], cols[3]]
    assert np.allclose([row["eff_crs"] for row in rows], _dual_scores(X, Y, vrs=False), atol=1e-6)
    assert np.allclose([row["eff_vrs"] for row in rows], _dual_scores(X, Y, vrs=True), atol=1e-6)


def test_planted_outlier_wounds_influence_check(run_script, tmp_path):
    # 30 units with y/x in [0.5, 0.8] and one planted unit at y/x = 2. Under CRS every score is (y/x)/2; without
    # the outlier it is (y/x)/max(y/x) -- every remaining unit moves by far more than 0.05.
    rng = np.random.default_rng(11)
    x = np.r_[rng.uniform(1, 10, 30), 5.0]
    y = np.r_[x[:30] * rng.uniform(0.5, 0.8, 30), 10.0]
    data = _write_csv(tmp_path / "in" / "outlier.csv", ["x", "y"], [x, y])
    _ok(run_script(S, "--data", data, "--inputs", "x", "--outputs", "y", "--rts", "crs", "--super",
                   tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    chk = _check(rep, "DEA-INFLUENCE")
    assert chk["verdict"] == "WOUNDED" and chk["value"] >= 0.9
    assert rep["data"]["influence"]["removed"] == ["row31"]


def test_bootstrap_planted_truth(run_script, tmp_path):
    # DGP with known truth: CRS Cobb-Douglas isoquant sqrt(x1*x2) = y, true input efficiency th (half-normal).
    # DEA overstates efficiency (its frontier lies inside the true one). The SW98 pseudo-frontier lies inside the
    # DEA frontier, so every bootstrap bias estimate is >= 0 and every interval ends at or below the DEA score.
    rng = np.random.default_rng(7)
    n = 25
    y = rng.uniform(1, 5, n)
    w = rng.uniform(0.2, 1.37, n)
    xf = np.c_[np.cos(w), np.sin(w)] * (y / np.sqrt(np.cos(w) * np.sin(w)))[:, None]
    th = np.clip(1 - np.abs(rng.normal(0, 0.2, n)), 0.4, 1.0)
    X = xf / th[:, None]
    data = _write_csv(tmp_path / "in" / "dgp.csv", ["x1", "x2", "y"], [X[:, 0], X[:, 1], y])
    _ok(run_script(S, "--data", data, "--inputs", "x1,x2", "--outputs", "y", "--rts", "crs", "--bootstrap", "60",
                   tmp_path=tmp_path / "out"), 0, 1)
    rep = latest_report(tmp_path / "out")
    rows = rep["data"]["scores"]
    eff, bc = np.array([r["eff"] for r in rows]), np.array([r["eff_bc"] for r in rows])
    bias = np.array([r["bias"] for r in rows])
    lo, hi = np.array([r["ci_low"] for r in rows]), np.array([r["ci_high"] for r in rows])
    assert eff.mean() > th.mean()                       # DEA is biased upward
    assert (bias >= -1e-9).all() and (hi <= eff + 1e-9).all() and (lo < hi).all()
    assert abs(bc.mean() - th.mean()) < abs(eff.mean() - th.mean())  # correction moves toward the truth
    true_bias = eff.mean() - th.mean()
    assert true_bias / 3 < bias.mean() < 3 * true_bias
    assert _check(rep, "DEA-BOOT-CI")["verdict"] in ("SURVIVES", "WOUNDED")
    assert rep["data"]["bootstrap"]["h"] > 0


@pytest.mark.parametrize("case", ["missing_column", "negative_value"])
def test_usage_errors_exit_2(run_script, tmp_path, case):
    data, cols = ONE, ["--inputs", "x", "--outputs", "nope"]
    if case == "negative_value":
        data = _write_csv(tmp_path / "in" / "neg.csv", ["x", "y"], [[2.0, -1.0, 3.0], [1.0, 2.0, 3.0]])
        cols = ["--inputs", "x", "--outputs", "y"]
    r = _ok(run_script(S, "--data", data, *cols, tmp_path=tmp_path / "out"), 2)
    assert "usage error" in r.stderr and "Traceback" not in r.stderr
    assert not list((tmp_path / "out").glob("*/report.json"))


def test_output_orientation_known_answer_run_dir_and_determinism(run_script, tmp_path):
    # Output VRS frontier A(2,2)-B(4,6)-D(8,7): at x = 6 (C) it gives y = 6.5 -> 1/phi = 6/6.5 = 12/13; at x = 5 (E)
    # it gives y = 6.25 -> 3/6.25 = 0.48. CRS scores do not depend on orientation (D: 7/12).
    # The same run, done twice with one --seed, checks run-folder hygiene and bootstrap determinism.
    before, fixtures_before = _sha(ONE), sorted(p.name for p in FIX.iterdir())
    args = ["--data", ONE, "--inputs", "x", "--outputs", "y", "--id", "unit", "--orientation", "output",
            "--super", "--bootstrap", "20"]
    for _ in range(2):
        _ok(run_script(S, *args, tmp_path=tmp_path), 0, 1)
    sc = _scores(latest_report(tmp_path))
    for u, v in {"A": 1, "B": 1, "C": 12 / 13, "D": 1, "E": 0.48}.items():
        assert sc[u]["eff"] == pytest.approx(v, abs=1e-6)
    assert sc["D"]["eff_crs"] == pytest.approx(7 / 12, abs=1e-6)
    assert _sha(ONE) == before and sorted(p.name for p in FIX.iterdir()) == fixtures_before
    runs = sorted(tmp_path.iterdir())
    assert len(runs) == 2 and all(p.is_dir() and p.name.startswith("dea_frontier-") for p in runs)
    for run in runs:
        assert {p.name for p in run.iterdir()} == {"report.json", "report.md", "scores.csv"}
        assert "Second-stage warning" in (run / "report.md").read_text(encoding="utf-8")
    assert (runs[0] / "scores.csv").read_bytes() == (runs[1] / "scores.csv").read_bytes()


def _crs_data(n=25, seed=7):
    """1-input / 1-output CRS data with efficiencies spread over (0.4, 1] (eff = ratio / max ratio)."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(1, 10, n)
    y = x * np.r_[1.0, rng.uniform(0.4, 1.0, n - 1)]
    X, Y = x[:, None], y[:, None]
    sc, _, st = dea.envelopment(X, Y, X, Y, "crs", "input")
    assert (st == 0).all()
    return X, Y, dea.farrell(sc, "input")


def test_sw98_draws_are_reflected_and_variance_corrected(monkeypatch):
    # Pins the two SW98 ingredients the property tests cannot see (CR-07). Every replication's draws come from
    # the reflected set R = {eff, 2 - eff}, so before folding they centre on 1; the variance correction keeps
    # their variance at var(R) instead of var(R) + h^2. A wide bandwidth h = 0.4 makes h^2 larger than var(R),
    # so dropping the reflection (mean ~ mean(eff) ~ 0.7) or the correction (variance ~ 2.3 var(R)) fails here.
    X, Y, eff = _crs_data()
    calls, orig = [], dea._sw98_draw

    def record(refl, var_r, h, n, rng, floor):
        smooth, star = orig(refl, var_r, h, n, rng, floor)
        calls.append((np.array(refl), smooth, star))
        return smooth, star

    monkeypatch.setattr(dea, "_sw98_draw", record)
    h = 0.4
    out = dea.sw98_bootstrap(X, Y, eff, "crs", "input", 150, 0.05, np.random.default_rng(3), h, 1e-6)
    assert out is not None and len(calls) == 150
    var_r = np.var(np.r_[eff, 2.0 - eff], ddof=1)
    assert var_r + h * h > 2 * var_r                  # the test has power: the uncorrected variance is 2x+ larger
    for refl, _, _ in calls[:3]:                      # resampling pool = the reflected set, symmetric about 1
        assert refl.size == 2 * eff.size and np.allclose(np.sort(refl), np.sort(2.0 - refl))
    smooth = np.concatenate([c[1] for c in calls])
    star = np.concatenate([c[2] for c in calls])
    assert abs(smooth.mean() - 1.0) < 0.02            # 3750 pre-fold draws, SE about 0.006
    assert 0.85 < smooth.var() / var_r < 1.15         # variance-corrected
    fold = np.where(smooth <= 1.0, smooth, 2.0 - smooth)
    assert (star <= 1.0 + 1e-12).all() and np.allclose(star[fold > 1e-3], fold[fold > 1e-3])


def _run_in_process(tmp_path, *args):
    return dea.run_main(dea.SCRIPT, dea.main, dea.build_parser(),
                        [*map(str, args), "--no-glassbox", "--quiet", "--out", str(tmp_path)])


def test_failed_influence_lp_stops_the_run(monkeypatch, tmp_path):
    # CR-32: if re-scoring the remaining units fails, the run must stop (exit 2) instead of counting NaN moves as
    # "unchanged". Planted by making the reduced-set LPs (4 of the 5 units in one_input.csv) report status 2.
    orig = dea.envelopment

    def broken(Xr, Yr, X0, Y0, rts, orient, exclude=None):
        score, lam, status = orig(Xr, Yr, X0, Y0, rts, orient, exclude)
        if X0.shape[0] == 4 and exclude is None:
            return np.full_like(score, np.nan), lam, np.full_like(status, 2)
        return score, lam, status

    monkeypatch.setattr(dea, "envelopment", broken)
    assert _run_in_process(tmp_path, "--data", ONE, "--inputs", "x", "--outputs", "y", "--super") == 2
    assert not list(tmp_path.glob("*/report.json"))


def test_failed_bootstrap_lps_make_the_interval_check_unverified(monkeypatch, tmp_path):
    # CR-32: intervals built on an incomplete resample are not judged. Planted: the first bootstrap replication's
    # LPs (reference set = pseudo-data, so Xr is not X0) fail.
    orig, state = dea.envelopment, {"failed": False}

    def flaky(Xr, Yr, X0, Y0, rts, orient, exclude=None):
        score, lam, status = orig(Xr, Yr, X0, Y0, rts, orient, exclude)
        if Xr is not X0 and not state["failed"]:
            state["failed"] = True
            return np.full_like(score, np.nan), lam, np.full_like(status, 4)
        return score, lam, status

    monkeypatch.setattr(dea, "envelopment", flaky)
    assert _run_in_process(tmp_path, "--data", ONE, "--inputs", "x", "--outputs", "y", "--bootstrap", "20") in (1, 3)
    chk = _check(latest_report(tmp_path), "DEA-BOOT-CI")
    assert chk["verdict"] == "UNVERIFIED-HERE" and "failed" in chk["detail"]


def test_help_states_bootstrap_guidance_and_variant():
    text = dea.build_parser().format_help()
    assert ">= 1000 (1999 recommended)" in text and "--bootstrap 1999" in text        # D-41
    assert "Benchmarking::dea.boot" in text and "reflected about 1" in text           # CR-31
    assert "--slack-tol" in text                                                      # CR-23
