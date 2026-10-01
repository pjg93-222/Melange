# -*- coding: utf-8 -*-
"""Tests for scripts/backtest_eval.py (build spec 6.3 / 6.4 / 6.5).

The exit-code and run-folder contract is tested through the conftest subprocess helper; further behaviour runs
in-process through _common.run_main (same code path, no interpreter start-up) to keep the file under 20 s.
All data are synthetic: the fixture is hand-solved, the rest is generated here with fixed seeds.
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import backtest_eval as bt
from _common import UsageError
from conftest import SCRIPTS, latest_report, latest_run_dir, sha256

TINY = SCRIPTS / "tests" / "fixtures" / "backtest_eval" / "tiny_known_answer.csv"


def _inproc(out, *args):
    code = bt.run_main(bt.SCRIPT, bt.main, bt.build_parser(),
                       argv=[*map(str, args), "--no-glassbox", "--quiet", "--out", str(out)])
    return code, (latest_report(out) if code != 2 else None)


def _verdicts(rep):
    return {c["id"]: c["verdict"] for c in rep["checks"]}


def _series(T, seed, group=None):
    """y_t = 0.5 y_{t-1} + 2 x_t + e_t. f_good uses the true dynamics; f_noise is naive plus noise; f_ar is the
    nested AR-only model; intervals: +-1.645 sd around f_good (nominal 90%) and +-0.5 sd (planted too narrow)."""
    r = np.random.default_rng(seed)
    x = r.normal(size=T)
    y = np.zeros(T)
    for t in range(1, T):
        y[t] = 0.5 * y[t - 1] + 2.0 * x[t] + r.normal()
    lag = np.r_[np.nan, y[:-1]]
    good = 0.5 * lag + 2.0 * x
    d = pd.DataFrame({"t": np.arange(T), "y": y, "f_good": good, "f_noise": lag + r.normal(scale=2.0, size=T),
                      "f_ar": 0.5 * lag, "f_ar_noise": 0.5 * lag + r.normal(scale=1.0, size=T),
                      "lo": good - 1.645, "hi": good + 1.645, "lo_n": good - 0.5, "hi_n": good + 0.5})
    d.loc[:9, d.columns[2:]] = np.nan                                          # first 10 rows: history only
    if group is not None:
        d.insert(0, "g", group)
    return d


# --------------------------------------------------------------------------- subprocess contract tests
def test_known_answer_hand_solved_fixture_and_run_folder(run_script, tmp_path):
    """Fixture solved by hand: naive errors 2,-1,2,-1,... (SSE 24, MAE 14/9), model errors +-0.5 (SSE 2.25).
    OOS R^2 = 1 - 2.25/24 = 0.90625. d = 3.75 (5x) and 0.75 (4x): mean 21.75/9, gamma0 = 20/9,
    DM = mean / sqrt(gamma0 / 9); HLN factor sqrt((9 + 1 - 2)/9) = sqrt(8/9); one-sided p from t(8).
    Direction: 9/9 hits vs majority baseline 5/9; Wilson 90% lower bound 0.76887. Negative control: exit 0."""
    before = sha256(TINY)
    res = run_script("backtest_eval", "--data", TINY, "--actual", "y", "--forecast", "f", "--time", "t")
    assert res.returncode == 0, res.stdout + res.stderr
    rep = latest_report(tmp_path)
    m = rep["data"]["models"]["f"]
    dm = (21.75 / 9) / math.sqrt((20 / 9) / 9) * math.sqrt(8 / 9)
    assert m["oos_r2"] == pytest.approx(0.90625, abs=1e-12)
    assert m["test"]["stat"] == pytest.approx(dm, rel=1e-12)
    assert m["test"]["p_one"] == pytest.approx(stats.t.sf(dm, 8), rel=1e-9)
    assert m["MAE"] == pytest.approx(0.5) and m["n_periods"] == 9 and m["windows_won"] == 4
    assert m["direction"]["hits"] == 9 and m["direction"]["baseline"] == pytest.approx(5 / 9)
    assert m["direction"]["wilson"][0] == pytest.approx(0.768866, abs=1e-5)
    run = latest_run_dir(tmp_path)
    bench = pd.read_csv(run / "metrics.csv").iloc[0]
    assert bench["MAE"] == pytest.approx(14 / 9) and bench["RMSE"] == pytest.approx(math.sqrt(24 / 9))
    assert [p.name for p in tmp_path.iterdir()] == [run.name]
    assert {p.name for p in run.iterdir()} == {"report.json", "report.md", "metrics.csv"}
    assert sha256(TINY) == before == rep["provenance"]["inputs"][0]["sha256"]


def test_too_few_periods_is_unverified(run_script, tmp_path):
    res = run_script("backtest_eval", "--data", TINY, "--actual", "y", "--forecast", "f", "--time", "t",
                     "--min-n", "10")
    assert res.returncode == 3, res.stderr
    assert set(_verdicts(latest_report(tmp_path)).values()) == {"UNVERIFIED-HERE"}


def test_usage_error_missing_column_exits_2(run_script, tmp_path):
    res = run_script("backtest_eval", "--data", TINY, "--actual", "y", "--forecast", "nope", "--time", "t")
    assert res.returncode == 2 and "nope" in res.stderr


# --------------------------------------------------------------------------- in-process behaviour
def _reject_constant(token):
    raise ValueError(f"non-standard JSON token {token}")


def test_identical_forecast_gives_zero_statistic_and_is_killed(tmp_path):
    code, rep = _inproc(tmp_path, "--data", TINY, "--actual", "y", "--forecast", "f_same", "--time", "t")
    t = rep["data"]["models"]["f_same"]["test"]
    assert code == 1 and t["stat"] == 0.0 and t["p_one"] == 0.5 and "identically zero" in t["note"]
    assert _verdicts(rep)["BT-ACC-f_same"] == "KILLED"
    # the power numbers are undefined here; report.json must still be strict JSON (null, not NaN/Infinity)
    text = (latest_run_dir(tmp_path) / "report.json").read_text(encoding="utf-8")
    assert json.loads(text, parse_constant=_reject_constant)["data"]["models"]["f_same"]["n_eff"] is None


def test_strictly_better_model_survives_and_noise_model_is_killed(tmp_path):
    data = tmp_path / "series.csv"
    _series(120, 1).to_csv(data, index=False)
    code, rep = _inproc(tmp_path / "out", "--data", data, "--actual", "y", "--forecast", "f_good",
                        "--forecast", "f_noise", "--time", "t", "--direction", "none")
    v = _verdicts(rep)
    assert code == 1 and v["BT-ACC-f_good"] == "SURVIVES" and v["BT-ACC-f_noise"] == "KILLED"
    assert rep["data"]["models"]["f_good"]["test"]["p_one"] < 1e-4
    assert rep["data"]["models"]["f_good"]["mde_skill"] > 0


def test_nested_clark_west_detects_real_signal_not_added_noise(tmp_path):
    data = tmp_path / "series.csv"
    _series(150, 2).to_csv(data, index=False)
    code, rep = _inproc(tmp_path / "out", "--data", data, "--actual", "y", "--forecast", "f_good",
                        "--forecast", "f_ar_noise", "--time", "t", "--benchmark", "col:f_ar", "--nested",
                        "--direction", "none")
    good, noise = rep["data"]["models"]["f_good"], rep["data"]["models"]["f_ar_noise"]
    assert good["test"]["kind"] == "Clark-West" and good["test"]["p_one"] < 1e-4
    assert noise["test"]["p_one"] > 0.05 and _verdicts(rep)["BT-ACC-f_ar_noise"] != "SURVIVES"


def test_panel_pools_periods_and_reports_groups(tmp_path):
    data = tmp_path / "panel.csv"
    pd.concat([_series(40, 10 + k, f"s{k}") for k in range(5)]).to_csv(data, index=False)
    code, rep = _inproc(tmp_path / "out", "--data", data, "--actual", "y", "--forecast", "f_good", "--time", "t",
                        "--group", "g")
    assert rep["data"]["n_periods"] == 30 and rep["data"]["n_rows"] == 150
    assert _verdicts(rep)["BT-GRP-f_good"] == "SURVIVES" and code == 0


def test_interval_coverage_planted_too_narrow_is_killed(tmp_path):
    data = tmp_path / "series.csv"
    _series(120, 1).to_csv(data, index=False)
    code, rep = _inproc(tmp_path / "ok", "--data", data, "--actual", "y", "--forecast", "f_good", "--time", "t",
                        "--lower", "lo", "--upper", "hi", "--level", "0.9")
    assert _verdicts(rep)["BT-COVER"] == "SURVIVES"
    code, rep = _inproc(tmp_path / "narrow", "--data", data, "--actual", "y", "--forecast", "f_good", "--time", "t",
                        "--lower", "lo_n", "--upper", "hi_n", "--level", "0.9")
    assert code == 1 and _verdicts(rep)["BT-COVER"] == "KILLED" and rep["data"]["intervals"]["picp"] < 0.6


def test_infinite_values_are_usage_errors(tmp_path):
    """Review CR-11: +-inf used to pass the numeric check and end as KILLED with a NaN statistic."""
    frame = pd.read_csv(TINY)
    frame.loc[4, "f"] = np.inf
    data = tmp_path / "inf.csv"
    frame.to_csv(data, index=False)
    code, _ = _inproc(tmp_path / "out", "--data", data, "--actual", "y", "--forecast", "f", "--time", "t")
    assert code == 2


def test_mixed_date_formats_parse_and_text_time_needs_a_flag(tmp_path):
    """Review CR-29: one odd date format used to drop the whole column to text order. Mixed formats now parse
    (same answer as the numeric fixture); genuine text is refused unless --allow-text-time is given."""
    frame = pd.read_csv(TINY)
    frame["t"] = ["2020-01-15", "2020-02-15", "03/15/2020", "2020-04-15", "05/15/2020", "2020-06-15", "2020-07-15",
                  "08/15/2020", "2020-09-15", "2020-10-15"]
    mixed = tmp_path / "mixed.csv"
    frame.to_csv(mixed, index=False)
    code, rep = _inproc(tmp_path / "a", "--data", mixed, "--actual", "y", "--forecast", "f", "--time", "t")
    assert code == 0 and rep["data"]["notes"][0] == "time order: date"
    assert rep["data"]["models"]["f"]["oos_r2"] == pytest.approx(0.90625, abs=1e-12)
    frame["t"] = [f"p{k:02d}" for k in range(10)]
    text = tmp_path / "text.csv"
    frame.to_csv(text, index=False)
    code, _ = _inproc(tmp_path / "b", "--data", text, "--actual", "y", "--forecast", "f", "--time", "t")
    assert code == 2
    code, rep = _inproc(tmp_path / "c", "--data", text, "--actual", "y", "--forecast", "f", "--time", "t",
                        "--allow-text-time")
    assert code == 0 and rep["data"]["notes"][0].startswith("time order: text")


def test_duplicate_time_is_a_usage_error(tmp_path):
    data = tmp_path / "dup.csv"
    pd.concat([_series(20, 3, "a"), _series(20, 4, "b")]).to_csv(data, index=False)
    code, _ = _inproc(tmp_path / "out", "--data", data, "--actual", "y", "--forecast", "f_good", "--time", "t")
    assert code == 2


# --------------------------------------------------------------------------- formulas against hand values
def test_dm_hln_h2_matches_textbook_formula():
    d = np.random.default_rng(0).normal(0.3, 1.0, 40)
    n, h = 40, 2
    dc = d - d.mean()
    g0, g1 = dc @ dc / n, dc[1:] @ dc[:-1] / n
    dm = d.mean() / math.sqrt((g0 + 2 * g1) / n) * math.sqrt((n + 1 - 2 * h + h * (h - 1) / n) / n)
    res = bt.compare(d, h, "DM-HLN")
    assert res["stat"] == pytest.approx(dm, rel=1e-12)
    assert res["p_one"] == pytest.approx(stats.t.sf(dm, n - 1), rel=1e-10)


def test_constant_advantage_is_exact_not_estimated():
    res = bt.compare(np.full(12, 0.5), 1, "DM-HLN")
    assert math.isinf(res["stat"]) and res["p_one"] == 0.0 and "zero variance" in res["note"]


def test_wilson_kupiec_christoffersen_hand_values():
    lo, hi = bt.wilson(8, 10, 0.95)                      # textbook: 0.4902 to 0.9433
    assert (lo, hi) == (pytest.approx(0.49016, abs=1e-4), pytest.approx(0.94331, abs=1e-4))
    lr, p = bt.kupiec(20, 100, 0.1)                     # -2[80 ln .9 + 20 ln .1 - 80 ln .8 - 20 ln .2]
    exp = -2 * (80 * math.log(0.9) + 20 * math.log(0.1) - 80 * math.log(0.8) - 20 * math.log(0.2))
    assert lr == pytest.approx(exp, rel=1e-12) and exp == pytest.approx(8.8806, abs=1e-3)
    assert p == pytest.approx(stats.chi2.sf(exp, 1), rel=1e-12)
    lr_c, p_c, n = bt.christoffersen([np.array([0, 1] * 10, dtype=bool)])   # n01 = 10, n10 = 9, pi = 10/19
    assert (n[0, 1], n[1, 0], n[0, 0], n[1, 1]) == (10, 9, 0, 0)
    assert lr_c == pytest.approx(-2 * (9 * math.log(9 / 19) + 10 * math.log(10 / 19)), rel=1e-12)


def test_option_validation_raises_usage_errors():
    args = bt.build_parser().parse_args(["--data", "x", "--actual", "y", "--forecast", "f", "--time", "t",
                                         "--nested", "--loss", "mae"])
    with pytest.raises(UsageError):
        bt._validate(args)
    frame = pd.DataFrame({"_g": ["a"] * 3, "y": [1.0, 2.0, 3.0]})
    args = bt.build_parser().parse_args(["--data", "x", "--actual", "y", "--forecast", "f", "--time", "t",
                                         "--benchmark", "seasonal:x"])
    with pytest.raises(UsageError):
        bt.make_benchmark(frame, args)
