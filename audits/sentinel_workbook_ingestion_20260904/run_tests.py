"""Run the PATCHED sentinel test module against the PATCHED sync script.

sys.path puts patched/fec FIRST and LIVE fec second, so every patched module wins
and everything else (paths, bill_rules, legislation.*, members.*) resolves to the
LIVE tree read-only.  MONEYBALL_ROOT points at LIVE so paths.ROOT is the real root.
Nothing here writes into LIVE.

The test module was authored pytest-style (tmp_path/monkeypatch).  Rather than skip
those, this runner supplies the two fixtures itself and drives everything through
unittest.FunctionTestCase, so the whole file runs with no pytest installed.
"""
import importlib.util
import inspect
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
PATCHED_FEC = SCRATCH / "patched" / "fec"
LIVE = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")

os.environ["MONEYBALL_ROOT"] = str(LIVE)
for entry in (str(LIVE / "fec"), str(PATCHED_FEC)):
    while entry in sys.path:
        sys.path.remove(entry)
sys.path.insert(0, str(LIVE / "fec"))
sys.path.insert(0, str(PATCHED_FEC))

TEST_PATH = PATCHED_FEC / "tests" / "legislation" / "test_sentinel_bill_workbook_sync.py"


class MonkeyPatch:
    """The 3 pytest monkeypatch methods this test file uses, with an undo stack."""

    def __init__(self):
        self._undo = []

    def setattr(self, target, name, value):
        had = hasattr(target, name)
        old = getattr(target, name, None)
        self._undo.append((target, name, old, had))
        setattr(target, name, value)

    def setenv(self, name, value):
        had = name in os.environ
        old = os.environ.get(name)
        self._undo.append((os.environ, name, old, had))
        os.environ[name] = str(value)

    def delenv(self, name, raising=True):
        had = name in os.environ
        old = os.environ.get(name)
        self._undo.append((os.environ, name, old, had))
        if had:
            del os.environ[name]
        elif raising:
            raise KeyError(name)

    def undo(self):
        while self._undo:
            target, name, old, had = self._undo.pop()
            if isinstance(target, type(os.environ)):
                if had:
                    target[name] = old
                else:
                    target.pop(name, None)
            elif had:
                setattr(target, name, old)
            else:
                try:
                    delattr(target, name)
                except AttributeError:
                    pass


def load_test_module():
    spec = importlib.util.spec_from_file_location("patched_sentinel_tests", TEST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def wrap(function):
    parameters = list(inspect.signature(function).parameters)

    def run():
        kwargs = {}
        temp = None
        patcher = None
        try:
            if "tmp_path" in parameters:
                temp = tempfile.mkdtemp(prefix="sentinel_test_")
                kwargs["tmp_path"] = Path(temp)
            if "monkeypatch" in parameters:
                patcher = MonkeyPatch()
                kwargs["monkeypatch"] = patcher
            function(**kwargs)
        finally:
            if patcher is not None:
                patcher.undo()
            if temp is not None:
                shutil.rmtree(temp, ignore_errors=True)

    return run


def main():
    module = load_test_module()
    names = sorted(name for name in dir(module)
                   if name.startswith("test_") and callable(getattr(module, name)))
    body = {}
    for name in names:
        body[name] = (lambda runner: (lambda self: runner()))(wrap(getattr(module, name)))
    case_class = type("SentinelBillWorkbookSyncTests", (unittest.TestCase,), body)
    suite = unittest.TestLoader().loadTestsFromTestCase(case_class)
    print("collected %d tests from %s" % (suite.countTestCases(), TEST_PATH))
    for name in names:
        print("   " + name)
    print()
    result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
