#!/usr/bin/env python3
"""Dependency-free runner for the legfix5 focused test modules.

The workstation has no ``pytest`` installed and installing one mid-audit would
change the environment under test.  This runner injects a minimal ``pytest``
shim providing only the surface the focused suites actually use
(``pytest.raises``, ``pytest.fail``, ``pytest.skip``, and the ``tmp_path``
fixture), then executes every ``test_*`` function in the requested modules.

It is a test harness only: it imports and runs test modules, and never touches
discovery evidence, ledgers, the main corpus, or promotion artifacts.

Usage::

    python fec/tests/run_focused_tests.py fec/tests/test_run_reversible_legislation_culling.py
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import types
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]


class _Raises:
    def __init__(self, expected: type[BaseException] | tuple, match: str | None):
        self.expected = expected
        self.match = match
        self.value: BaseException | None = None

    def __enter__(self) -> "_Raises":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            raise AssertionError(f"DID NOT RAISE {self.expected}")
        if not issubclass(exc_type, self.expected):
            return False
        if self.match is not None and self.match not in str(exc):
            raise AssertionError(
                f"pattern {self.match!r} not found in {str(exc)!r}"
            )
        self.value = exc
        return True


def _install_pytest_shim() -> None:
    if "pytest" in sys.modules:
        return
    shim = types.ModuleType("pytest")

    def raises(expected, match: str | None = None):
        return _Raises(expected, match)

    class _Skipped(Exception):
        pass

    def fail(reason: str = "") -> None:
        raise AssertionError(reason)

    def skip(reason: str = "") -> None:
        raise _Skipped(reason)

    shim.raises = raises  # type: ignore[attr-defined]
    shim.fail = fail  # type: ignore[attr-defined]
    shim.skip = skip  # type: ignore[attr-defined]
    shim.Skipped = _Skipped  # type: ignore[attr-defined]
    sys.modules["pytest"] = shim


def _load_module(path: Path) -> types.ModuleType:
    name = f"_focused_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _call(function: Callable[..., Any]) -> None:
    names = function.__code__.co_varnames[: function.__code__.co_argcount]
    if "tmp_path" in names:
        directory = Path(tempfile.mkdtemp(prefix="focused-"))
        try:
            function(directory)
        finally:
            shutil.rmtree(directory, ignore_errors=True)
    else:
        function()


def run_module(path: Path) -> tuple[int, int, list[str]]:
    module = _load_module(path)
    tests = sorted(
        name for name in dir(module) if name.startswith("test_")
    )
    passed = 0
    failures: list[str] = []
    for name in tests:
        function = getattr(module, name)
        if not callable(function):
            continue
        try:
            _call(function)
        except sys.modules["pytest"].Skipped as error:  # type: ignore[attr-defined]
            print(f"  SKIP {name}: {error}")
            continue
        except BaseException:
            failures.append(f"{path.name}::{name}\n{traceback.format_exc()}")
            print(f"  FAIL {name}")
            continue
        passed += 1
        print(f"  ok   {name}")
    return passed, len(tests), failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("modules", nargs="+")
    args = parser.parse_args(argv)

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
    fec_dir = REPO_ROOT / "fec"
    if str(fec_dir) not in sys.path:
        sys.path.insert(0, str(fec_dir))
    _install_pytest_shim()

    total_passed = 0
    total_tests = 0
    all_failures: list[str] = []
    for raw in args.modules:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / raw).resolve()
        print(f"== {path.name} ==")
        passed, count, failures = run_module(path)
        total_passed += passed
        total_tests += count
        all_failures.extend(failures)

    print()
    for failure in all_failures:
        print(failure)
    print(f"{total_passed}/{total_tests} passed")
    return 0 if total_passed == total_tests else 1


if __name__ == "__main__":
    raise SystemExit(main())
