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

    python fec/tests/run_focused_tests.py fec/tests/legislation/test_run_reversible_legislation_culling.py
"""

from __future__ import annotations

import argparse
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tempfile
import traceback
import types
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS_ROOT = REPO_ROOT / "fec" / "tests"


def _discover_tests() -> dict[str, Path]:
    """Map each recursively discovered test basename to its unique path."""
    paths: dict[str, Path] = {}
    for path in sorted(TESTS_ROOT.rglob("test_*.py")):
        name = path.stem
        if name in paths:
            raise RuntimeError(
                f"duplicate test basename {name!r}: {paths[name]} and {path}"
            )
        paths[name] = path
    return paths


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


class _Mark:
    """Minimal ``pytest.mark`` supporting ``parametrize`` and inert marks."""

    @staticmethod
    def parametrize(argnames, argvalues, **_kwargs):
        if isinstance(argnames, str):
            names = [part.strip() for part in argnames.split(",") if part.strip()]
        else:
            names = list(argnames)

        def decorate(function):
            cases = list(getattr(function, "_parametrize", []))
            cases.append((names, list(argvalues)))
            function._parametrize = cases
            return function

        return decorate

    def __getattr__(self, _name):
        def mark(*args, **_kwargs):
            if len(args) == 1 and callable(args[0]):
                return args[0]

            def decorate(function):
                return function

            return decorate

        return mark


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
    shim.mark = _Mark()  # type: ignore[attr-defined]
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


def _cases(function: Callable[..., Any]) -> list[dict[str, Any]]:
    """Expand stacked ``parametrize`` decorators into concrete kwarg sets."""

    stack = getattr(function, "_parametrize", None)
    if not stack:
        return [{}]
    combined: list[dict[str, Any]] = [{}]
    for names, values in stack:
        expanded: list[dict[str, Any]] = []
        for base in combined:
            for value in values:
                row = tuple(value) if len(names) > 1 else (value,)
                expanded.append({**base, **dict(zip(names, row))})
        combined = expanded
    return combined


def _call(function: Callable[..., Any], kwargs: dict[str, Any]) -> None:
    names = function.__code__.co_varnames[: function.__code__.co_argcount]
    if "tmp_path" in names and "tmp_path" not in kwargs:
        directory = Path(tempfile.mkdtemp(prefix="focused-"))
        try:
            function(directory, **kwargs)
        finally:
            shutil.rmtree(directory, ignore_errors=True)
    else:
        function(**kwargs)


def _run_unittest(module: types.ModuleType) -> tuple[int, int, list[str]]:
    import unittest

    suite = unittest.TestLoader().loadTestsFromModule(module)
    count = suite.countTestCases()
    if count == 0:
        return 0, 0, []
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    for line in stream.getvalue().splitlines():
        if " ... ok" in line:
            print(f"  ok   {line.split(' ... ')[0].strip()}")
        elif " ... FAIL" in line or " ... ERROR" in line:
            print(f"  FAIL {line.split(' ... ')[0].strip()}")
    failures = [
        f"{test}\n{trace}" for test, trace in result.failures + result.errors
    ]
    passed = count - len(failures) - len(result.skipped)
    return passed, count - len(result.skipped), failures


def run_module(path: Path) -> tuple[int, int, list[str]]:
    module = _load_module(path)
    if any(
        isinstance(getattr(module, name, None), type)
        and issubclass(getattr(module, name), _unittest_case())
        for name in dir(module)
    ):
        return _run_unittest(module)

    tests = sorted(name for name in dir(module) if name.startswith("test_"))
    passed = 0
    total = 0
    failures: list[str] = []
    for name in tests:
        function = getattr(module, name)
        if not callable(function):
            continue
        for kwargs in _cases(function):
            total += 1
            label = name if not kwargs else f"{name}{tuple(kwargs.values())}"
            try:
                _call(function, kwargs)
            except sys.modules["pytest"].Skipped as error:  # type: ignore[attr-defined]
                total -= 1
                print(f"  SKIP {label}: {error}")
                continue
            except BaseException:
                failures.append(
                    f"{path.name}::{label}\n{traceback.format_exc()}"
                )
                print(f"  FAIL {label}")
                continue
            passed += 1
            print(f"  ok   {label}")
    return passed, total, failures


def _unittest_case() -> type:
    import unittest

    return unittest.TestCase


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
    # 2026-08-04 Phase 1: domain subdirectories are discovered recursively;
    # this index is the single source of path truth for moved focused suites.
    test_paths = _discover_tests()

    total_passed = 0
    total_tests = 0
    all_failures: list[str] = []
    for raw in args.modules:
        path = Path(raw)
        if not path.is_absolute():
            path = (REPO_ROOT / raw).resolve()
        if not path.is_file():
            name = Path(raw).stem
            if name not in test_paths:
                raise FileNotFoundError(f"focused test module not found: {raw}")
            path = test_paths[name]
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
