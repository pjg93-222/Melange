"""Run behavior/corpus checks and verify a deterministic rebuild of the pilot."""
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from .data import ROOT,digest,read_json,write_json


def main():
    out=ROOT/"outputs/member_personal_relationships/20260910_pilot"
    before=read_json(out/"manifest.json")["artifact_sha256"]
    result=subprocess.run([sys.executable,"-m","fec.research.member_personal_relationships.run"],
                          cwd=ROOT,capture_output=True,text=True,encoding="utf-8")
    (out/"rebuild_log.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
    if result.returncode:
        raise RuntimeError(result.stderr)
    after=read_json(out/"manifest.json")["artifact_sha256"]
    same=before==after
    stream=io.StringIO()
    suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/"tests"))
    test=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/"TEST_RESULTS.txt").write_text(stream.getvalue(),encoding="utf-8")
    receipt=dict(tests_run=test.testsRun,failures=len(test.failures),errors=len(test.errors),skipped=len(test.skipped),
                 all_passed=test.wasSuccessful(),deterministic_rebuild=same,
                 artifacts_compared=len(before),before_sha256=before,after_sha256=after,
                 predictive_accuracy_tested=False,calibration_tested=False,
                 test_first_history=[
                     "Initial 19 behavioral contracts were executed before core.py existed: expected ModuleNotFoundError, then all 19 passed.",
                     "Four additional service/baseline contracts were added before work.py existed: expected ModuleNotFoundError, then all 23 passed.",
                     "Seven corpus integration checks added after empirical run; software verification is separate from friendship accuracy."],
                 production_unchanged=read_json(out/"manifest.json")["production_unchanged"])
    write_json(out/"verification_receipt.json",receipt)
    print(json.dumps({k:v for k,v in receipt.items() if not k.endswith("sha256")},indent=2))
    if not test.wasSuccessful() or not same:
        raise SystemExit(1)


if __name__=="__main__":
    main()
