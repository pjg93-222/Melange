"""Tests for scripts/global_sensitivity.py (BUILD_SPEC 6.4): the Ishigami known answer end to end (design ->
test computes the function -> analysis), Morris elementary effects of a linear model, the OAT non-monotone
detector with its negative control, the SALib second computation path (skipped without SALib), design-layout
validation, usage errors and run-folder hygiene. The script itself never runs a model; the tests play the user."""
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

# In-process import (collection time) for the generator unit tests: heavy imports made after the subprocess
# tests have run are several times slower on this Windows machine.
sys.dont_write_bytecode = True  # keep __pycache__ out of the skill folder
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import global_sensitivity as gs  # noqa: E402
from _common import UsageError  # noqa: E402

S = "global_sensitivity.py"
PI = math.pi


def _check(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


def _ok(r, *codes):
    """Assert the exit code, showing the child's output when it is unexpected."""
    assert r.returncode in codes, f"exit {r.returncode}\nSTDERR:\n{r.stderr[-2000:]}\nSTDOUT:\n{r.stdout[-1000:]}"
    return r


def _json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _csv(path, header, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(",".join(f"{v:.17g}" if isinstance(v, float) else str(v) for v in row) for row in rows)
    path.write_text(",".join(header) + "\n" + body + "\n", encoding="utf-8")
    return path


def _design_csv(path, names, X):
    return _csv(path, ["run_id"] + names, [[i] + [float(v) for v in row] for i, row in enumerate(X)])


def test_design_generators_and_layout_validator_in_process():
    rng = np.random.default_rng(1)
    d, r, p = 3, 6, 4
    delta = p / (2 * (p - 1))
    U = gs.design_morris(d, r, p, rng)
    traj = U.reshape(r, d + 1, d)
    step = np.diff(traj, axis=1)                       # (r, d, d)
    moved = np.abs(step) > 1e-12
    assert (moved.sum(axis=2) == 1).all() and (moved.sum(axis=1) == 1).all()   # one factor per step, each once
    assert np.allclose(np.abs(step[moved]), delta) and U.min() >= 0 and U.max() <= 1
    gs.check_structure(U, "morris", d)
    V = gs.design_sobol(d, 8, rng)
    Z = V.reshape(8, d + 2, d)
    for i in range(d):                                 # AB_i = A with column i from B
        assert np.array_equal(np.delete(Z[:, 1 + i], i, axis=1), np.delete(Z[:, 0], i, axis=1))
        assert np.array_equal(Z[:, 1 + i, i], Z[:, d + 1, i])
    gs.check_structure(V, "sobol", d)
    with pytest.raises(UsageError):
        gs.check_structure(V[rng.permutation(len(V))], "sobol", d)


def test_ishigami_sobol_known_answer_end_to_end(run_script, tmp_path):
    # Ishigami f = sin x1 + a sin^2 x2 + b x3^4 sin x1, x_i ~ U(-pi, pi), a = 7, b = 0.1. Analytic:
    # V = a^2/8 + b pi^4/5 + b^2 pi^8/18 + 1/2 = 13.8446; V1 = (1 + b pi^4/5)^2 / 2 = 4.3459; V2 = a^2/8 = 6.125;
    # V13 = b^2 pi^8 (1/18 - 1/50) = 3.3737 -> S1 = (0.3139, 0.4424, 0), ST = (0.5576, 0.4424, 0.2437).
    # x4 is a dummy the function ignores (negative control: S1 = ST = 0, never flagged).
    names = ["x1", "x2", "x3", "x4"]
    problem = _json(tmp_path / "in" / "problem.json",
                    {"names": names, "bounds": [[-PI, PI]] * 3 + [[0.0, 1.0]],
                     "status": ["arbitrary", "fitted", "literature", "arbitrary"]})
    before = hashlib.sha256(problem.read_bytes()).hexdigest()
    _ok(run_script(S, "--problem", problem, "--method", "sobol", "--design-only", "--N", "2048",
                   tmp_path=tmp_path / "design"), 0)
    # design mode has a real check (a run with no checks would exit 3): the design regenerates byte-identically
    assert _check(latest_report(tmp_path / "design"), "GSA-DESIGN")["verdict"] == "SURVIVES"
    run = next((tmp_path / "design").iterdir())
    assert {p.name for p in run.iterdir()} == {"design.csv", "design_meta.json", "report.json", "report.md"}
    D = np.genfromtxt(run / "design.csv", delimiter=",", names=True)
    assert len(D) == 2048 * (4 + 2) and list(D.dtype.names) == ["run_id"] + names
    assert D["x4"].min() >= 0 and D["x4"].max() <= 1 and np.abs(D["x1"]).max() <= PI
    y = np.sin(D["x1"]) + 7 * np.sin(D["x2"]) ** 2 + 0.1 * D["x3"] ** 4 * np.sin(D["x1"])
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"], zip(D["run_id"].astype(int), y.tolist()))
    _ok(run_script(S, "--problem", problem, "--method", "sobol", "--design", run / "design.csv",
                   "--outputs", outputs, tmp_path=tmp_path / "analysis"), 1)  # arbitrary/literature with ST > 0.1
    rep = latest_report(tmp_path / "analysis")
    ind = rep["data"]["indices"]
    assert np.allclose(ind["S1"], [0.3139, 0.4424, 0.0, 0.0], atol=0.05)
    assert np.allclose(ind["ST"], [0.5576, 0.4424, 0.2437, 0.0], atol=0.05)
    verdicts = [_check(rep, f"GSA-P0{i}")["verdict"] for i in range(1, 5)]
    assert verdicts == ["WOUNDED", "SURVIVES", "WOUNDED", "SURVIVES"]
    assert _check(rep, "GSA-PREC")["verdict"] == "SURVIVES" and _check(rep, "GSA-CONSIST")["verdict"] == "SURVIVES"
    if rep["data"]["engine"].startswith("SALib"):   # second path present: point estimates must agree
        assert _check(rep, "GSA-PATH")["verdict"] == "SURVIVES"
    assert hashlib.sha256(problem.read_bytes()).hexdigest() == before
    assert len(list((tmp_path / "analysis").iterdir())) == 1


def test_morris_linear_known_answer(run_script, tmp_path):
    # y = 2*x1 + 0.5*x2 + 0*x3 with x1 in [0, 10], x2, x3 in [0, 1]. Elementary effects are taken per unit of the
    # [0, 1]-scaled factor, so EE = (20, 0.5, 0) on every step: mu* = mu = (20, 0.5, 0), sigma = 0.
    # No status given: x1 is influential -> UNVERIFIED-HERE (never a pass); x2, x3 are below threshold.
    names, lo, hi = ["x1", "x2", "x3"], np.array([0.0, 0, 0]), np.array([10.0, 1, 1])
    problem = _json(tmp_path / "in" / "problem.json", {"names": names, "bounds": [[0, 10], [0, 1], [0, 1]]})
    X = lo + gs.design_morris(3, 10, 4, np.random.default_rng(5)) * (hi - lo)
    design = _design_csv(tmp_path / "in" / "design.csv", names, X)
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"],
                   [(i, float(2 * x[0] + 0.5 * x[1])) for i, x in enumerate(X)])
    _ok(run_script(S, "--problem", problem, "--method", "morris", "--design", design, "--outputs", outputs,
                   tmp_path=tmp_path / "out"), 3)
    rep = latest_report(tmp_path / "out")
    ind = rep["data"]["indices"]
    assert np.allclose(ind["mu_star"], [20, 0.5, 0], atol=1e-9) and np.allclose(ind["mu"], [20, 0.5, 0], atol=1e-9)
    assert np.allclose(ind["sigma"], 0, atol=1e-9)
    assert [_check(rep, f"GSA-P0{i}")["verdict"] for i in (1, 2, 3)] == ["UNVERIFIED-HERE", "SURVIVES", "SURVIVES"]


def test_oat_nonmonotone_planted_and_monotone_negative_control(run_script, tmp_path):
    # y = x1^2 + 2*x2, x1 in [-1, 1], x2 in [0, 1], nominal = midpoints (0, 0.5). x1: y(-1) = y(1) = 2 but
    # y(nominal) = 1, so its swing is 0 although it matters: the non-monotone detector must flag x1. x2 is
    # monotone (y 1 -> 0 and 2) and must not be flagged.
    names = ["x1", "x2"]
    problem = _json(tmp_path / "in" / "problem.json",
                    {"parameters": [{"name": "x1", "bounds": [-1, 1], "status": "arbitrary"},
                                    {"name": "x2", "bounds": [0, 1], "status": "fitted"}]})
    X = np.array([[0, 0.5], [-1, 0.5], [1, 0.5], [0, 0.0], [0, 1.0]])   # nominal, x1 low/high, x2 low/high
    design = _design_csv(tmp_path / "in" / "design.csv", names, X)
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"],
                   [(i, float(x[0] ** 2 + 2 * x[1])) for i, x in enumerate(X)])
    _ok(run_script(S, "--problem", problem, "--method", "oat", "--design", design, "--outputs", outputs,
                   tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    mono = _check(rep, "GSA-MONO")
    assert mono["verdict"] == "WOUNDED" and "x1" in mono["detail"] and "x2" not in mono["detail"]
    assert rep["data"]["indices"]["swing"] == pytest.approx([0.0, 2.0])
    assert rep["data"]["indices"]["non_monotone"] == [True, False]


def test_salib_second_path_agrees(run_script, tmp_path):
    pytest.importorskip("SALib")
    # y = x1 + 2*x2 on U(0, 1)^2: S1 = ST = (0.2, 0.8). SALib must be the engine and agree with numpy.
    names = ["x1", "x2"]
    problem = _json(tmp_path / "in" / "problem.json", {"names": names, "bounds": [[0, 1], [0, 1]]})
    X = gs.design_sobol(2, 256, np.random.default_rng(3))
    design = _design_csv(tmp_path / "in" / "design.csv", names, X)
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"],
                   [(i, float(x[0] + 2 * x[1])) for i, x in enumerate(X)])
    _ok(run_script(S, "--problem", problem, "--method", "sobol", "--design", design, "--outputs", outputs,
                   tmp_path=tmp_path / "out"), 1, 3)  # influential, no status given (-> 3) unless N = 256 is imprecise
    rep = latest_report(tmp_path / "out")
    assert rep["data"]["engine"].startswith("SALib")
    assert _check(rep, "GSA-PATH")["verdict"] == "SURVIVES" and rep["data"]["salib_numpy_max_diff"] < 1e-9
    assert np.allclose(rep["data"]["indices"]["ST"], [0.2, 0.8], atol=0.05)


def test_zero_sobol_variance_is_unverified_not_a_pass(run_script, tmp_path):
    # CR-22: outputs that vary only on the AB_1 rows leave var(f_A, f_B) = 0, so every Sobol' index is 0/0.
    # Before the fix every parameter said SURVIVES; now nothing can be attributed: GSA-VAR UNVERIFIED-HERE.
    names = ["a", "b"]
    problem = _json(tmp_path / "in" / "problem.json",
                    {"names": names, "bounds": [[0, 1], [0, 1]], "status": ["ratified", "fitted"]})
    X = gs.design_sobol(2, 16, np.random.default_rng(6))
    design = _design_csv(tmp_path / "in" / "design.csv", names, X)
    y = [1.0 if i % 4 == 1 else 0.0 for i in range(len(X))]  # block rows: A, AB_1, AB_2, B
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"], list(enumerate(y)))
    _ok(run_script(S, "--problem", problem, "--method", "sobol", "--design", design, "--outputs", outputs,
                   tmp_path=tmp_path / "out"), 3)
    rep = latest_report(tmp_path / "out")
    assert [(c["id"], c["verdict"]) for c in rep["checks"]] == [("GSA-VAR", "UNVERIFIED-HERE")]


def test_usage_error_reordered_design_rows(run_script, tmp_path):
    # A design whose rows were shuffled can no longer be split into A, AB_i, B blocks: refuse (exit 2).
    names = ["x1", "x2"]
    problem = _json(tmp_path / "in" / "problem.json", {"names": names, "bounds": [[0, 1], [0, 1]]})
    X = gs.design_sobol(2, 16, np.random.default_rng(4))
    X = X[np.random.default_rng(5).permutation(len(X))]
    design = _design_csv(tmp_path / "in" / "design.csv", names, X)
    outputs = _csv(tmp_path / "in" / "outputs.csv", ["run_id", "y"], [(i, float(x.sum())) for i, x in enumerate(X)])
    r = _ok(run_script(S, "--problem", problem, "--method", "sobol", "--design", design, "--outputs", outputs,
                       tmp_path=tmp_path / "out"), 2)
    assert "Saltelli block order" in r.stderr and "Traceback" not in r.stderr
    assert not list((tmp_path / "out").glob("*/report.json"))
