"""Tests for scripts/mutation_check.py (BUILD_SPEC 6.4): a real check kills every mutant (SURVIVES), a vacuous
check kills none (KILLED), a clamped check misses the non-monotone mutations (WOUNDED), CSV blind spots and
value-equivalent mutants, custom specs with expected survivors, a failing baseline (UNVERIFIED-HERE), the
process-tree kill on timeout, shell-script refusal, usage errors, the --help warning and run-folder hygiene.
The fixture checkers are small stdlib scripts under fixtures/mutation_check/."""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

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

S = "mutation_check.py"
FIX = pathlib.Path(__file__).resolve().parent / "fixtures" / "mutation_check"
SERIES, TABLE = FIX / "series.json", FIX / "table.csv"


def _cmd(checker, *extra):
    """The check command; the lone '--' ends it (the shared helper appends --no-glassbox --out after it)."""
    return ["--cmd", sys.executable, str(FIX / checker), "{input}", *extra, "--"]


def _check(rep, cid):
    return next(c for c in rep["checks"] if c["id"] == cid)


def _ok(r, *codes):
    """Assert the exit code, showing the child's output when it is unexpected."""
    assert r.returncode in codes, f"exit {r.returncode}\nSTDERR:\n{r.stderr[-2000:]}\nSTDOUT:\n{r.stdout[-1000:]}"
    return r


def _sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def _alive(pid):
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        code = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(handle, ctypes.byref(code))
        k32.CloseHandle(handle)
        return bool(ok) and code.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def test_real_check_kills_every_mutant_and_run_dir_hygiene(run_script, tmp_path):
    before, fixtures_before = _sha(SERIES), sorted(p.name for p in FIX.iterdir())
    _ok(run_script(S, "--input", SERIES, *_cmd("check_series.py"), tmp_path=tmp_path), 0)
    rep = latest_report(tmp_path)
    kill = _check(rep, "MUT-KILL")
    assert kill["verdict"] == "SURVIVES" and kill["value"] == "5/5"
    assert _check(rep, "MUT-BASE")["verdict"] == "SURVIVES" and rep["data"]["baseline_copy_byte_identical"]
    assert [row["op"] for row in rep["data"]["runs"]] == ["baseline", "identity", "reverse", "swap_adjacent",
                                                         "scale", "zero", "delete_key"]
    # nothing outside the run folder; the input and the fixture folder are untouched; the copies are always named
    # input<ext> (never the user's file name, CR-04) and each run keeps its own stdout/stderr files
    assert _sha(SERIES) == before and sorted(p.name for p in FIX.iterdir()) == fixtures_before
    runs = list(tmp_path.iterdir())
    assert len(runs) == 1 and runs[0].name.startswith("mutation_check-")
    assert {p.name for p in runs[0].iterdir()} == {"report.json", "report.md", "mutants.csv", "mutants"}
    base = runs[0] / "mutants" / "000_baseline"
    assert {p.name for p in base.iterdir()} == {"input.json", "stdout.txt", "stderr.txt"}
    assert (base / "input.json").read_bytes() == SERIES.read_bytes()
    assert all(r_["file"].endswith("input.json") for r_ in rep["data"]["runs"])


def test_vacuous_check_is_killed(run_script, tmp_path):
    _ok(run_script(S, "--input", SERIES, *_cmd("check_vacuous.py"), tmp_path=tmp_path), 1)
    kill = _check(latest_report(tmp_path), "MUT-KILL")
    assert kill["verdict"] == "KILLED" and kill["value"] == "0/5" and "vacuous" in kill["detail"]


def test_clamped_check_misses_non_monotone_mutations(run_script, tmp_path):
    # The running-max bug hides reversal and local swaps; range-breaking mutants are still caught.
    _ok(run_script(S, "--input", SERIES, *_cmd("check_clamped.py"), tmp_path=tmp_path), 1)
    rep = latest_report(tmp_path)
    assert _check(rep, "MUT-KILL")["verdict"] == "WOUNDED"
    assert rep["data"]["blind_spots"] == ["reverse /values", "swap_adjacent /values"]
    status = {row["op"]: row["status"] for row in rep["data"]["runs"]}
    assert status["scale"] == status["zero"] == status["delete_key"] == "KILLED"


def test_csv_blind_spots_and_equivalent_mutants(run_script, tmp_path):
    # check_table.py validates x, y and the row count but ignores id: every id mutation survives (blind spots),
    # every x / y / row mutation is killed. Sorting an already sorted column changes nothing: EQUIVALENT, not run.
    _ok(run_script(S, "--input", TABLE, *_cmd("check_table.py"), tmp_path=tmp_path), 1)
    rep = latest_report(tmp_path)
    assert _check(rep, "MUT-KILL")["verdict"] == "WOUNDED"
    assert all(spot.endswith(" id") for spot in rep["data"]["blind_spots"]) and len(rep["data"]["blind_spots"]) == 4
    rows = rep["data"]["runs"][2:]
    assert {r_["target"] for r_ in rows if r_["status"] == "EQUIVALENT"} == {"id", "x", "y"}
    assert all(r_["status"] == "KILLED" for r_ in rows if r_["target"] in ("x", "y", "(rows)", "id<->x", "x<->y")
               and r_["status"] != "EQUIVALENT")


def test_custom_spec_expected_survivor_and_provenance_pins(run_script, tmp_path):
    # flip_sign of id survives by design (the check ignores id): declared with --expect-survive it is listed as
    # EXPECTED-SURVIVOR and left out of the verdict, so the three counted mutants decide it (SURVIVES).
    # The spec and the check script decide the verdict, so both are pinned by sha256 in the provenance (CR-19).
    spec = tmp_path / "in" / "spec.json"
    spec.parent.mkdir(parents=True)
    spec.write_text(json.dumps([{"op": "flip_sign", "column": "x"}, {"op": "swap", "columns": ["x", "y"]},
                                {"op": "drop_rows", "frac": 0.2}, {"op": "flip_sign", "column": "id"}]),
                    encoding="utf-8")
    _ok(run_script(S, "--input", TABLE, "--mutations", spec, "--expect-survive", "flip_sign:id",
                   *_cmd("check_table.py"), tmp_path=tmp_path / "out"), 0)
    rep = latest_report(tmp_path / "out")
    assert _check(rep, "MUT-KILL")["value"] == "3/3" and _check(rep, "MUT-KILL")["verdict"] == "SURVIVES"
    assert rep["data"]["expected_survivors"] == ["flip_sign:id"]
    assert {r_["status"] for r_ in rep["data"]["runs"] if r_["target"] == "id"} == {"EXPECTED-SURVIVOR"}
    pinned = {i["sha256"] for i in rep["provenance"]["inputs"]}
    assert {_sha(TABLE), _sha(spec), _sha(FIX / "check_table.py")} <= pinned


def test_bom_csv_and_value_equivalent_mutants(run_script, tmp_path):
    # A UTF-8 BOM must not stick to the first header name (CR-20): the spec can name column "a". flip_sign on a
    # column of zeros writes "-0", which differs as text but not as a value: EQUIVALENT, not run (CR-21).
    data = tmp_path / "in" / "bom.csv"
    data.parent.mkdir(parents=True)
    data.write_bytes("﻿a,z\n1,0\n2,0\n3,0\n".encode("utf-8"))
    spec = tmp_path / "in" / "spec.json"
    spec.write_text(json.dumps([{"op": "flip_sign", "column": "z"}, {"op": "flip_sign", "column": "a"}]),
                    encoding="utf-8")
    _ok(run_script(S, "--input", data, "--mutations", spec, *_cmd("check_vacuous.py"), tmp_path=tmp_path / "out"), 1)
    rep = latest_report(tmp_path / "out")
    status = {r_["target"]: r_["status"] for r_ in rep["data"]["runs"][2:]}
    assert status == {"z": "EQUIVALENT", "a": "SURVIVED"}
    assert rep["data"]["equivalent"] == ["flip_sign:z"] and rep["data"]["baseline_copy_byte_identical"]


def test_timeout_kills_the_whole_process_tree(run_script, tmp_path):
    # The check leaves a sleeping grandchild behind and never exits. With --timeout 3 the run must end within the
    # timeout + 5 s, and neither process may survive it (CR-03).
    pidfile = tmp_path / "grandchild.pid"
    t0 = time.perf_counter()
    _ok(run_script(S, "--input", SERIES, "--timeout", "3", *_cmd("check_spawns_sleeper.py", str(pidfile)),
                   tmp_path=tmp_path / "out"), 3)
    wall = time.perf_counter() - t0
    rep = latest_report(tmp_path / "out")
    base = rep["data"]["runs"][0]
    assert base["status"] == "TIMEOUT" and base["seconds"] <= 3 + 5
    assert _check(rep, "MUT-BASE")["verdict"] == "UNVERIFIED-HERE"
    assert wall < 3 + 5 + 10, f"run took {wall:.1f} s"  # + interpreter start-up on a loaded machine
    assert pidfile.exists(), "the check never started its grandchild"
    gpid, deadline = int(pidfile.read_text()), time.monotonic() + 5
    while _alive(gpid) and time.monotonic() < deadline:  # termination completes asynchronously on Windows;
        time.sleep(0.1)                                   # a 30 s sleeper can only be gone this early if killed
    assert not _alive(gpid), "the grandchild outlived the timeout"


@pytest.mark.parametrize("prog", ["check.bat", "powershell"])
def test_shell_script_commands_refused(run_script, tmp_path, prog):
    # .bat/.cmd run through cmd.exe, which re-parses arguments; refused unless --allow-shell-script (CR-04).
    r = _ok(run_script(S, "--input", SERIES, "--cmd", prog, "{input}", "--", tmp_path=tmp_path), 2)
    assert "--allow-shell-script" in r.stderr and "Traceback" not in r.stderr
    assert not list(tmp_path.glob("*/report.json"))


@pytest.mark.skipif(os.name != "nt", reason="cmd.exe behaviour is Windows-only")
def test_allowed_shell_script_gets_safe_copy_names(run_script, tmp_path):
    # An input file name carrying cmd.exe metacharacters never reaches the shell: the copies are input.json.
    evil = tmp_path / "in" / "x&ver&.json"
    evil.parent.mkdir(parents=True)
    evil.write_bytes(SERIES.read_bytes())
    bat = tmp_path / "in" / "check.bat"
    if len(str(bat)) >= 250:  # cmd.exe cannot start a batch file whose path exceeds MAX_PATH (WinError 206)
        pytest.skip(f"batch path is {len(str(bat))} characters, too long for cmd.exe; use a shorter --basetemp")
    bat.write_text(f'@"{sys.executable}" "{FIX / "check_series.py"}" %1\r\n', encoding="ascii")
    r = _ok(run_script(S, "--input", evil, "--allow-shell-script", "--cmd", str(bat), "{input}", "--",
                       tmp_path=tmp_path / "out"), 0)
    assert "WARNING: --allow-shell-script" in r.stderr
    rep = latest_report(tmp_path / "out")
    assert _check(rep, "MUT-KILL")["verdict"] == "SURVIVES" and rep["data"]["shell_script_allowed"]
    assert not any("not recognized" in r_["tail"] for r_ in rep["data"]["runs"])


def test_failing_baseline_is_unverified_not_a_pass(run_script, tmp_path):
    # A JSON checker pointed at a CSV fails on the unmodified input: nothing can be concluded (exit 3).
    _ok(run_script(S, "--input", TABLE, *_cmd("check_series.py"), tmp_path=tmp_path), 3)
    rep = latest_report(tmp_path)
    assert [c["id"] for c in rep["checks"]] == ["MUT-BASE"] and rep["checks"][0]["verdict"] == "UNVERIFIED-HERE"


@pytest.mark.parametrize("args", [["--cmd", sys.executable, str(FIX / "check_series.py"), "--"],  # no {input}
                                  ["--cmd", "qme-no-such-command-xyz", "{input}", "--"],         # cannot start
                                  [],                                                             # no --cmd
                                  ["--expect-survive", "no_such_op"] + _cmd("check_series.py")])  # unknown name
def test_usage_errors_exit_2(run_script, tmp_path, args):
    r = _ok(run_script(S, "--input", SERIES, *args, tmp_path=tmp_path), 2)
    assert "usage error" in r.stderr and "Traceback" not in r.stderr
    assert not list(tmp_path.glob("*/report.json"))


def test_help_warns_that_the_command_is_executed(run_script, tmp_path):
    r = _ok(run_script(S, "--help", tmp_path=tmp_path), 0)
    assert "EXECUTES THE COMMAND" in r.stdout and "import == execution" in r.stdout
    assert "--allow-shell-script" in r.stdout and "--expect-survive" in r.stdout
