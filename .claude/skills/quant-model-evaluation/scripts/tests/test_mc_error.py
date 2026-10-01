"""Tests for scripts/mc_error.py (BUILD_SPEC 6.4): MCSE ~ sigma/sqrt(n) for iid replications, ESS of a planted
AR(1) series, the common-random-numbers credit in paired comparisons, top-K stability with a separated and a
null ranking, long-format input, usage errors, and run-folder hygiene."""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import subprocess
import sys

import numpy as np
import pytest

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

S = "mc_error.py"
SMALL = pathlib.Path(__file__).resolve().parent / "fixtures" / "mc_error" / "reps_small.csv"

# In-process imports for the helper second-path test happen here, at collection time: on this Windows machine
# heavy imports made after the subprocess tests have run are several times slower.
sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import mc_error  # noqa: E402
from scipy.stats import chi2, kendalltau  # noqa: E402


def _check(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


def _ok(r, *codes):
    """Assert the exit code, showing the child's output when it is unexpected."""
    assert r.returncode in codes, f"exit {r.returncode}\nSTDERR:\n{r.stderr[-2000:]}\nSTDOUT:\n{r.stdout[-1000:]}"
    return r


def _write(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(",".join(v if isinstance(v, str) else f"{v:.17g}" for v in row) for row in rows)
    path.write_text(",".join(header) + "\n" + body + "\n", encoding="utf-8")
    return path


def test_mcse_known_answers_planted_autocorrelation_and_crn_gap(run_script, tmp_path):
    # iid N(0, 2^2), n = 400: MCSE = sigma/sqrt(n) = 0.1, and a 0.05 target needs (2/0.05)^2 = 1600 replications.
    # Planted: AR(1), phi = 0.9, started in its stationary law: ESS/n = (1-phi)/(1+phi) = 0.053 (ESS ~ 21) and
    # MCSE = 1/(1-phi)/sqrt(n) = 0.5; the independence check must flag it and must NOT flag the iid column.
    # Common random numbers: A = X + 0.1 + e1, B = X + e2, X ~ N(0, 5^2) shared, e ~ N(0, 0.05^2): paired MCSE =
    # sd(e1 - e2)/sqrt(n) = 0.0707/20 = 0.0035 (z ~ 28) while the unpaired MCSE would be ~0.35.
    rng = np.random.default_rng(2)
    n = 400
    iid = rng.normal(0, 2, n)
    ar = np.empty(n)
    ar[0] = rng.normal(0, 1 / math.sqrt(1 - 0.81))
    for t in range(1, n):
        ar[t] = 0.9 * ar[t - 1] + rng.normal()
    x = rng.normal(0, 5, n)
    a, b = x + 0.1 + rng.normal(0, 0.05, n), x + rng.normal(0, 0.05, n)
    data = _write(tmp_path / "in" / "reps.csv", ["iid", "ar", "a", "b"], zip(iid, ar, a, b))
    _ok(run_script(S, "--data", data, "--target-se", "0.05", "--compare", "a,b", tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    m = rep["data"]["metrics"]
    assert m["iid"]["mcse_iid"] == pytest.approx(2 / math.sqrt(n), rel=0.10)
    assert m["iid"]["mcse_rule"] == "iid" and m["iid"]["mcse"] == m["iid"]["mcse_iid"]
    assert m["iid"]["mcse_batch"] == pytest.approx(2 / math.sqrt(n), rel=0.40)
    assert 1250 <= m["iid"]["reps_needed"] <= 2000   # 400 * s^2 = 1600 x (s/sigma)^2, s within ~12% of sigma
    assert m["ar"]["ess"] < 60 and 0.25 < m["ar"]["mcse_ess"] < 1.0 and m["ar"]["mcse_rule"] == "ESS-adjusted"
    assert m["ar"]["mcse_ess"] > 3 * m["ar"]["mcse_iid"]
    indep = _check(rep, "MC-INDEP")
    assert indep["verdict"] == "WOUNDED" and "ar (" in indep["detail"] and "iid" not in indep["detail"]
    assert _check(rep, "MC-DEGENERATE")["verdict"] == "SURVIVES"   # negative control: every column varies
    comp = rep["data"]["compare"]
    assert comp["mcse_paired"] == pytest.approx(0.05 * math.sqrt(2) / math.sqrt(n), rel=0.25)
    assert comp["mcse_unpaired"] > 50 * comp["mcse_paired"] and comp["gap"] == pytest.approx(0.1, abs=0.02)
    assert _check(rep, "MC-GAP")["verdict"] == "SURVIVES"
    # Ljung-Box statistic of the iid column recomputed by direct lag sums (second path for the FFT version)
    yc, lags = iid - iid.mean(), min(10, n // 5)
    rho = [np.sum(yc[:n - k] * yc[k:]) / np.sum(yc * yc) for k in range(1, lags + 1)]
    q_direct = n * (n + 2) * sum(r_ * r_ / (n - k) for k, r_ in enumerate(rho, start=1))
    assert m["iid"]["ljung_box_q"] == pytest.approx(q_direct, rel=1e-9)


def test_long_format_and_unresolved_gap_negative_control(run_script, tmp_path):
    # Long input (rep, metric, value). C is a permutation of B: identical mean, so the gap is exactly 0 and the
    # comparison must NOT be called resolved. Means must come through the pivot unchanged.
    rng = np.random.default_rng(6)
    n = 60
    b = rng.normal(3, 1, n)
    c = rng.permutation(b)
    rows = [(str(i), name, v) for i in range(n) for name, v in (("b", b[i]), ("c", c[i]))]
    data = _write(tmp_path / "in" / "long.csv", ["rep", "metric", "value"], rows)
    _ok(run_script(S, "--data", data, "--rep", "rep", "--metric", "metric", "--value", "value", "--compare", "b,c",
                   tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    assert rep["data"]["metrics"]["b"]["mean"] == pytest.approx(b.mean(), abs=1e-12)
    gap = _check(rep, "MC-GAP")
    assert gap["verdict"] == "WOUNDED" and abs(rep["data"]["compare"]["z"]) < 1e-6


def _topk_rows(rng, scores_fn, reps=60, entities=12):
    return [(str(r), f"u{e:02d}", scores_fn(e)) for r in range(reps) for e in range(entities)]


def test_topk_separated_ranking_survives(run_script, tmp_path):
    # Entity means 10, 9, ..., -1 with noise sd 0.1: every resample picks the same top 3; boundary gap 1.0 >> MCSE.
    rng = np.random.default_rng(8)
    data = _write(tmp_path / "in" / "sep.csv", ["rep", "unit", "score"],
                  _topk_rows(rng, lambda e: 10 - e + rng.normal(0, 0.1)))
    _ok(run_script(S, "--data", data, "--rep", "rep", "--entity", "unit", "--score", "score", "--topk", "3",
                   tmp_path=tmp_path / "out"), 0)
    rep = latest_report(tmp_path / "out")
    topk = rep["data"]["topk"]
    assert topk["top"] == ["u00", "u01", "u02"] and topk["p_same"] == 1.0 and topk["tau_median"] > 0.99
    assert _check(rep, "MC-TOPK")["verdict"] == "SURVIVES"


def test_topk_null_ranking_is_killed(run_script, tmp_path):
    # Every entity has the same score distribution: the top-3 set is decided by the seed, not by the model.
    rng = np.random.default_rng(9)
    data = _write(tmp_path / "in" / "null.csv", ["rep", "unit", "score"], _topk_rows(rng, lambda e: rng.normal()))
    _ok(run_script(S, "--data", data, "--rep", "rep", "--entity", "unit", "--score", "score", "--topk", "3",
                   tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    assert rep["data"]["topk"]["p_same"] < 0.5 and _check(rep, "MC-TOPK")["verdict"] == "KILLED"


def test_helpers_match_independent_computations():
    # Kendall tau-b per resample is scipy.stats.kendalltau (CR-25: O(E log E) memory); a constant resample row
    # gives NaN, not an error. Ljung-Box (FFT autocovariance + incomplete-gamma tail) is checked against direct
    # lag sums + scipy.stats.chi2.sf (a second computation path).
    rng = np.random.default_rng(12)
    x = np.r_[rng.normal(size=15), [0.5, 0.5]]           # includes a tie
    rows = np.vstack([x + rng.normal(0, s, x.size) for s in (0.1, 1.0, 5.0)] + [np.ones(x.size)])
    rows[0, 3] = rows[0, 4]                               # a tie in one row too
    taus = mc_error.kendall_taus(x, rows)
    assert np.allclose(taus[:3], [kendalltau(x, r)[0] for r in rows[:3]], atol=1e-12) and np.isnan(taus[3])
    y = rng.normal(size=120)
    n, yc, lags = y.size, y - y.mean(), 6
    rho = [np.sum(yc[:n - k] * yc[k:]) / np.sum(yc * yc) for k in range(1, lags + 1)]
    q_direct = n * (n + 2) * sum(r * r / (n - k) for k, r in enumerate(rho, start=1))
    q, p = mc_error.ljung_box(y, lags)
    assert q == pytest.approx(q_direct, rel=1e-9) and p == pytest.approx(chi2.sf(q_direct, lags), rel=1e-9)


@pytest.mark.parametrize("extra", [["--compare", "loss,nope"], ["--rep", "rep", "--entity", "nope", "--score", "loss",
                                                                 "--topk", "1"]])
def test_usage_errors_exit_2(run_script, tmp_path, extra):
    r = _ok(run_script(S, "--data", SMALL, *extra, tmp_path=tmp_path), 2)
    assert "usage error" in r.stderr and "Traceback" not in r.stderr
    assert not list(tmp_path.glob("*/report.json"))


def test_infinite_value_is_a_usage_error(run_script, tmp_path):
    # CR-12: +inf used to pass the numeric check and crash later with a traceback.
    data = _write(tmp_path / "in" / "inf.csv", ["rep", "loss"], [(str(i), float(i)) for i in range(29)] + [("29", "inf")])
    r = _ok(run_script(S, "--data", data, "--rep", "rep", tmp_path=tmp_path / "out"), 2)
    assert "infinite" in r.stderr and "Traceback" not in r.stderr


def test_identical_replications_never_pass(run_script, tmp_path):
    # CR-01: 50 identical replications (the seed never reached the model) must not get a clean bill: MC-DEGENERATE
    # is WOUNDED and every precision / independence / drift check is UNVERIFIED-HERE; nothing SURVIVES.
    data = _write(tmp_path / "in" / "flat.csv", ["rep", "loss", "gain"], [(str(i), 3.25, 1.5) for i in range(50)])
    _ok(run_script(S, "--data", data, "--rep", "rep", tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    verdicts = {c["id"]: c["verdict"] for c in rep["checks"]}
    assert verdicts.pop("MC-DEGENERATE") == "WOUNDED"
    assert set(verdicts) == {"MC-PREC-01", "MC-PREC-02", "MC-INDEP", "MC-DRIFT"}
    assert set(verdicts.values()) == {"UNVERIFIED-HERE"}
    assert "seed/randomness never reached it" in _check(rep, "MC-DEGENERATE")["detail"]


def test_identical_topk_scores_never_pass(run_script, tmp_path):
    # CR-01 for the top-K decision: constant entity scores make P(same set) = 1 trivially; not evidence.
    rows = [(str(r), f"u{e:02d}", float(10 - e)) for r in range(30) for e in range(8)]
    data = _write(tmp_path / "in" / "flat_topk.csv", ["rep", "unit", "score"], rows)
    _ok(run_script(S, "--data", data, "--rep", "rep", "--entity", "unit", "--score", "score", "--topk", "3",
                   tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    assert _check(rep, "MC-TOPK")["verdict"] == "UNVERIFIED-HERE"
    assert _check(rep, "MC-DEGENERATE")["verdict"] == "WOUNDED"
    assert "SURVIVES" not in {c["verdict"] for c in rep["checks"]}


def test_run_dir_only_inputs_unchanged_and_too_few_reps_unverified(run_script, tmp_path):
    # 8 replications < --min-reps 10: precision cannot be judged -> UNVERIFIED-HERE, never a pass (exit 3).
    before = hashlib.sha256(SMALL.read_bytes()).hexdigest()
    _ok(run_script(S, "--data", SMALL, "--rep", "rep", tmp_path=tmp_path), 3)
    assert hashlib.sha256(SMALL.read_bytes()).hexdigest() == before
    runs = list(tmp_path.iterdir())
    assert len(runs) == 1 and runs[0].name.startswith("mc_error-")
    assert {p.name for p in runs[0].iterdir()} == {"report.json", "report.md", "metrics.csv"}
    rep = latest_report(tmp_path)
    verdicts = {c["id"]: c["verdict"] for c in rep["checks"]}
    assert verdicts.pop("MC-DEGENERATE") == "SURVIVES" and set(verdicts.values()) == {"UNVERIFIED-HERE"}
    assert rep["data"]["metrics"]["loss"]["mean"] == pytest.approx(10.0625)
