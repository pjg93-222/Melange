# -*- coding: utf-8 -*-
"""Tests for scripts/leakage_audit.py (build spec section 6.4).

Known answer: a split with planted leaks whose counts are fixed by construction (3 copied rows, 4 shared
entities of which one only after restoring leading zeros, 3 shared groups, 4 test rows inside the training
period and the 90-day embargo, 1 target proxy, 6 late availability stamps, 1 column whose missingness jumps
from 0% to 57%). Negative control: the same split without the plants. Usage errors exit 2. The run folder
holds every output and the inputs are unchanged. Fixtures are generated in code with fixed seeds.
"""
from __future__ import annotations

import argparse
import hashlib
import json
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

import leakage_audit as la  # noqa: E402  (scripts/ is on sys.path)
from _common import UsageError  # noqa: E402

SCRIPT = "leakage_audit.py"
FLAGS = ("--id", "id", "--group", "district", "--time", "date", "--embargo", "90D", "--target", "y",
         "--available-at", "avail")


def checks(report: dict) -> dict:
    return {c["id"]: c for c in report["checks"]}


def run_inprocess(out: pathlib.Path, *argv) -> tuple[int, dict | None]:
    code = la.run_main(la.SCRIPT, la.main, la.build_parser(),
                       argv=[*map(str, argv), "--no-glassbox", "--quiet", "--out", str(out)])
    return code, (latest_report(out) if code != 2 else None)


def make_split(rng, n: int, start: str, id0: int, district) -> pd.DataFrame:
    t = pd.Timestamp(start) + pd.to_timedelta(np.arange(n), unit="D")
    x1 = rng.normal(size=n)
    return pd.DataFrame({"id": [f"{i:05d}" for i in range(id0, id0 + n)], "district": [district(i) for i in range(n)],
                         "date": t.strftime("%Y-%m-%d"), "x1": x1, "party": rng.choice(["D", "R", "I"], size=n),
                         "noise": rng.normal(size=n), "y": (rng.random(n) < 1 / (1 + np.exp(-0.8 * x1))).astype(int),
                         "avail": t.strftime("%Y-%m-%d")})


def clean_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Train 2020-01-01..2020-07-18, test from 2021-01-01 (167-day gap); disjoint ids and districts."""
    rng = np.random.default_rng(7)
    return (make_split(rng, 200, "2020-01-01", 0, lambda i: f"d{i % 30:02d}"),
            make_split(rng, 100, "2021-01-01", 1000, lambda i: f"t{i % 15:02d}"))


def planted_split() -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = clean_split()
    rng = np.random.default_rng(99)
    train["leak"] = train["y"] * 10 + rng.normal(scale=0.01, size=len(train))  # the target in disguise
    test["leak"] = test["y"] * 10 + rng.normal(scale=0.01, size=len(test))
    test.loc[5, "id"] = "7"                        # train has '00007': one overlap once leading zeros return
    test.loc[6, "date"] = "2020-03-01"             # inside the training period (its avail stays in 2021)
    test.loc[:59, "noise"] = np.nan                # missingness 0% in train -> 57% in test after the copies
    test.loc[10:14, "avail"] = "2030-01-01"        # five rows whose features arrive after prediction time
    test.iloc[0:3] = train.iloc[10:13].to_numpy()  # three exact copies of training rows (ids, districts, dates)
    return train, test


def write_pair(folder: pathlib.Path, train: pd.DataFrame, test: pd.DataFrame) -> tuple[pathlib.Path, pathlib.Path]:
    folder.mkdir(parents=True, exist_ok=True)
    train.to_csv(folder / "train.csv", index=False)
    test.to_csv(folder / "test.csv", index=False)
    return folder / "train.csv", folder / "test.csv"


# ---- known answer (planted leaks), through the CLI ----
def test_known_answer_planted_leaks(run_script, tmp_path):
    tr, te = write_pair(tmp_path / "in", *planted_split())
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--train", tr, "--test", te, *FLAGS, tmp_path=out)
    assert proc.returncode == 1, proc.stderr + proc.stdout
    rep = latest_report(out)
    c = checks(rep)
    expected = {"LEAK-01": 3, "LEAK-02": 4, "LEAK-03": 3, "LEAK-04": 4, "LEAK-05": 4, "LEAK-07": 6, "LEAK-08": 1}
    assert {k: c[k]["value"] for k in expected} == expected
    assert {k: c[k]["verdict"] for k in c} == {k: "WOUNDED" for k in [*expected, "LEAK-06"]}  # all <= 5% of rows
    assert "1 match only after trimming" in c["LEAK-02"]["detail"]
    flagged = [r["feature"] for r in rep["data"]["feature_screen"]["rows"] if r["flagged"]]
    assert flagged == ["leak"]
    assert [r["column"] for r in rep["data"]["missingness"]["flagged"]] == ["noise"]
    pairs = pd.read_csv(latest_run_dir(out) / "duplicate_rows.csv")
    assert pairs.to_dict("list") == {"test_row_index": [0, 1, 2], "train_row_index": [10, 11, 12]}


def test_share_rule_escalates_to_killed(tmp_path):
    """Twenty copied rows are 20% of the test split, above --kill-share 0.05: KILLED, not WOUNDED."""
    train, test = clean_split()
    test.iloc[0:20] = train.iloc[0:20].to_numpy()
    tr, te = write_pair(tmp_path / "in", train, test)
    code, rep = run_inprocess(tmp_path / "out", "--train", tr, "--test", te, "--id", "id")
    c = checks(rep)
    assert code == 1 and c["LEAK-01"]["verdict"] == "KILLED" and c["LEAK-01"]["value"] == 20
    assert c["LEAK-02"]["verdict"] == "KILLED"


# ---- negative control and the run-folder contract ----
def test_negative_control_and_run_folder_contract(run_script, tmp_path):
    tr, te = write_pair(tmp_path / "in", *clean_split())
    before = {p.name: sha256(p) for p in (tr, te)}
    out = tmp_path / "out"
    proc = run_script(SCRIPT, "--train", tr, "--test", te, *FLAGS, tmp_path=out)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    rep = latest_report(out)
    assert {c["id"] for c in rep["checks"]} == {f"LEAK-0{i}" for i in range(1, 9)}
    assert {c["verdict"] for c in rep["checks"]} == {"SURVIVES"}
    run = latest_run_dir(out)
    assert list(out.iterdir()) == [run]
    assert {f.name for f in run.iterdir()} == {"report.json", "report.md", "feature_screen.csv", "missingness.csv"}
    assert {p.name: sha256(p) for p in (tr, te)} == before
    assert sorted(f.name for f in tr.parent.iterdir()) == ["test.csv", "train.csv"]


# ---- usage errors ----
def test_usage_error_exits_2(run_script, tmp_path):
    tr, te = write_pair(tmp_path / "in", *clean_split())
    proc = run_script(SCRIPT, "--train", tr, "--test", te, "--time", "date", "--embargo", "20X",
                      tmp_path=tmp_path / "out")
    assert proc.returncode == 2
    assert "usage error" in proc.stderr and "Traceback" not in proc.stderr


@pytest.mark.parametrize("extra", [["--embargo", "90D"],             # embargo without --time
                                   ["--id", "nope"],                  # column missing
                                   ["--time", "party"],               # not dates
                                   ["--target", "y", "--features", "x1,ghost"]])
def test_bad_arguments_are_usage_errors(tmp_path, extra):
    tr, te = write_pair(tmp_path / "in", *clean_split())
    assert run_inprocess(tmp_path / "out", "--train", tr, "--test", te, *extra)[0] == 2


# ---- units ----
def test_parse_embargo_units():
    assert la.parse_embargo("20D", False)[0] == pd.Timedelta(days=20)
    assert pd.Timestamp("2020-02-29") + la.parse_embargo("1Y", False)[0] == pd.Timestamp("2021-02-28")
    assert la.parse_embargo("6M", False)[0] == pd.DateOffset(months=6)
    assert la.parse_embargo("90min", False)[0] == pd.Timedelta(minutes=90)
    assert la.parse_embargo("5", True)[0] == 5.0
    for text, numeric in (("abc", False), ("20", False), ("20D", True), ("1.5Y", False), ("3X", False)):
        with pytest.raises(UsageError):
            la.parse_embargo(text, numeric)


def test_row_hash_normalizes_numbers_text_and_column_order():
    a = pd.DataFrame({"x": [1, 2, -0.0, np.nan], "s": [" a", "b", "c", None]})
    b = pd.DataFrame({"s": ["a", "b ", "c", None], "x": [1.0, 2.0, 0.0, np.nan]})
    ha, hb = la.row_hashes(a, b, ["x", "s"])
    assert (ha == hb).all() and len(set(ha.tolist())) == 4
    text = pd.DataFrame({"x": ["1", "2.0", "0", None], "s": ["a", "b", "c", None]})  # numbers stored as text
    ht, ha2 = la.row_hashes(text, a, ["s", "x"])
    assert (ht == ha2).all()
    assert list(la.norm_keys(pd.Series(["007", "7", "7.0", " 07 "]))) == ["7"] * 4


def test_screen_flags_proxies_but_not_high_cardinality_codes():
    rng = np.random.default_rng(3)
    n = 600

    def frame(prefix):
        y = (rng.random(n) < 0.4).astype(int)
        return pd.DataFrame({"y": y, "proxy": y * 3.0 + rng.normal(scale=0.01, size=n), "noise": rng.normal(size=n),
                             "row_code": [f"{prefix}{i}" for i in range(n)],             # unique per row
                             "outcome_date": np.where(y == 1, "2024-01-01", None)})      # exists only for positives
    tr, te = frame("r"), frame("s")
    kind, ytr, yte, _ = la.target_vectors(tr["y"], te["y"])
    ns = argparse.Namespace(folds=5, leak_threshold=0.98)
    rows = {r["feature"]: r for r in la.screen_features(tr, te, ["proxy", "noise", "row_code", "outcome_date"],
                                                           kind, ytr, yte, ns, rng)}
    assert kind == "binary"
    assert rows["proxy"]["flagged"] and rows["proxy"]["train"] == pytest.approx(1.0)
    assert rows["outcome_date"]["flagged"] and rows["outcome_date"]["train_missing"] == pytest.approx(1.0)
    assert not rows["noise"]["flagged"] and not rows["row_code"]["flagged"]
    assert rows["row_code"]["train"] == pytest.approx(0.5)  # out-of-fold encoding cannot memorise row ids


def test_screen_numeric_target_uses_r2():
    rng = np.random.default_rng(4)
    t = rng.normal(size=500)
    tr = pd.DataFrame({"t": t, "cube": t ** 3, "half": 0.5 * t + rng.normal(size=500)})
    kind, ytr, _, _ = la.target_vectors(tr["t"], None)
    rows = {r["feature"]: r for r in la.screen_features(tr, tr, ["cube", "half"], kind, ytr, None,
                                                           argparse.Namespace(folds=5, leak_threshold=0.98), rng)}
    assert kind == "numeric"
    assert rows["cube"]["flagged"] and rows["cube"]["train"] == pytest.approx(1.0)  # Spearman rho^2 = 1
    assert not rows["half"]["flagged"]


def test_screen_with_nothing_scorable_is_unverified(tmp_path):
    """CR-02: all-missing and constant features cannot be scored, so LEAK-06 must not say SURVIVES."""
    rng = np.random.default_rng(5)

    def frame(n):
        return pd.DataFrame({"t": rng.normal(size=n), "empty": np.nan, "const": 1.0, "flag": rng.integers(0, 2, n)})
    tr, te = write_pair(tmp_path / "in", frame(60), frame(30))
    code, rep = run_inprocess(tmp_path / "o1", "--train", tr, "--test", te, "--target", "t", "--features", "empty,const")
    c = checks(rep)["LEAK-06"]
    assert code == 3 and c["verdict"] == "UNVERIFIED-HERE" and c["value"] is None
    assert "empty (all missing)" in c["detail"] and "const (constant)" in c["detail"]
    code, rep = run_inprocess(tmp_path / "o2", "--train", tr, "--test", te, "--target", "flag", "--features", "const")
    assert code == 3 and checks(rep)["LEAK-06"]["verdict"] == "UNVERIFIED-HERE"  # binary target, constant feature
    code, rep = run_inprocess(tmp_path / "o3", "--train", tr, "--test", te, "--target", "t", "--features", "const,flag")
    c = checks(rep)["LEAK-06"]
    assert c["verdict"] == "SURVIVES" and "unscorable (1): const (constant)" in c["detail"]


def test_numeric_time_with_plain_number_embargo(tmp_path):
    train = pd.DataFrame({"t": np.arange(0, 100), "x": np.arange(100) % 7})
    test = pd.DataFrame({"t": np.arange(103, 150), "x": np.arange(47) % 7})
    tr, te = write_pair(tmp_path / "in", train, test)
    code, rep = run_inprocess(tmp_path / "out", "--train", tr, "--test", te, "--time", "t", "--embargo", "5")
    c = checks(rep)
    assert c["LEAK-04"]["verdict"] == "SURVIVES"
    assert c["LEAK-05"]["verdict"] == "WOUNDED" and c["LEAK-05"]["value"] == 1  # t = 103 < 99 + 5
    assert code == 1
