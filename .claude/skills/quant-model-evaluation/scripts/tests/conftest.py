# -*- coding: utf-8 -*-
"""Shared pytest plumbing for the quant-model-evaluation script tests (build spec section 6.6).

API that every test file may rely on:

  SCRIPTS
      Path of the ``scripts/`` folder. It is put on ``sys.path``, so tests can ``import _common``
      or ``import <script>`` directly.
  run_script(name, *args, tmp_path=None, timeout=120, env=None)   (fixture)
      Runs ``scripts/<name>`` in a subprocess as
      ``[sys.executable, SCRIPTS/name, *args, "--no-glassbox", "--out", str(tmp_path)]`` and returns the
      ``subprocess.CompletedProcess`` (stdout/stderr captured as text). ``tmp_path`` defaults to the
      test's own ``tmp_path``; passing it as the last positional argument also works. A name without a
      suffix gets ``.py``; a name ending in ``.R`` runs under Rscript (the test is skipped when Rscript
      cannot be found). ``env`` adds variables to the child environment.
  latest_report(out_dir) -> dict
      Loads the newest ``*/report.json`` under ``out_dir`` (fails the test when there is none).
  latest_run_dir(out_dir) -> pathlib.Path
      The run folder that holds that report (for extra artifacts such as ``references.csv``).
  find_rscript() -> str | None
      ``QME_RSCRIPT`` if it names a file, then ``Rscript`` on PATH, then the newest
      ``C:\\Program Files\\R\\R-*\\bin\\Rscript.exe``.
  sha256(path) -> str
      Hex digest of a file, for the inputs-unchanged checks.

Marker: ``@pytest.mark.live`` marks tests that reach the network; they are skipped unless the
environment variable ``QME_LIVE=1`` is set. No other test may touch the network.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

SCRIPTS = pathlib.Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
# Keep __pycache__ folders out of the skill tree for modules imported after this point.
sys.dont_write_bytecode = True


def pytest_configure(config):
    config.addinivalue_line("markers", "live: reaches the network; skipped unless QME_LIVE=1")


def pytest_collection_modifyitems(config, items):
    if os.environ.get("QME_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="live network test; set QME_LIVE=1 to run it")
    for item in items:
        if item.get_closest_marker("live") is not None:
            item.add_marker(skip)


def _r_version(exe: pathlib.Path) -> tuple[int, ...]:
    m = re.match(r"R-(\d+)\.(\d+)\.(\d+)", exe.parents[1].name)
    return tuple(int(x) for x in m.groups()) if m else (0, 0, 0)


def find_rscript() -> str | None:
    env = os.environ.get("QME_RSCRIPT")
    if env and pathlib.Path(env).is_file():
        return env
    hit = shutil.which("Rscript")
    if hit:
        return hit
    found = sorted(pathlib.Path(r"C:\Program Files\R").glob("R-*/bin/Rscript.exe"), key=_r_version)
    return str(found[-1]) if found else None


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def latest_run_dir(out_dir) -> pathlib.Path:
    reports = sorted(pathlib.Path(out_dir).glob("*/report.json"), key=lambda p: p.stat().st_mtime)
    assert reports, f"no */report.json under {out_dir}"
    return reports[-1].parent


def latest_report(out_dir) -> dict:
    return json.loads((latest_run_dir(out_dir) / "report.json").read_text(encoding="utf-8"))


@pytest.fixture
def run_script(tmp_path):
    default_out = tmp_path

    def _run(name, *args, tmp_path=None, timeout=120, env=None):
        args = list(args)
        # Tolerate run_script(name, *args, tmp_path) with the test's tmp_path passed positionally,
        # unless it is the value of a preceding --option.
        if (tmp_path is None and args and isinstance(args[-1], pathlib.Path) and args[-1] == default_out
                and not (len(args) >= 2 and str(args[-2]).startswith("--"))):
            tmp_path = args.pop()
        out = pathlib.Path(tmp_path) if tmp_path is not None else default_out
        script = SCRIPTS / name
        if not script.suffix and (SCRIPTS / f"{name}.py").is_file():
            script = SCRIPTS / f"{name}.py"
        if script.suffix.lower() == ".r":
            rscript = find_rscript()
            if rscript is None:
                pytest.skip("Rscript not found (set QME_RSCRIPT)")
            cmd = [rscript, str(script)]
        else:
            cmd = [sys.executable, str(script)]
        child_env = dict(os.environ, QME_GLASSBOX="0", PYTHONDONTWRITEBYTECODE="1")
        if env:
            child_env.update({k: str(v) for k, v in env.items()})
        return subprocess.run(cmd + [str(a) for a in args] + ["--no-glassbox", "--out", str(out)],
                              capture_output=True, text=True, errors="replace", timeout=timeout,
                              env=child_env)

    return _run
