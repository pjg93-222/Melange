"""Two extra proofs:

  A) the pinned-config runtime layer actually resolves (runtime_source == "config"),
     and env still wins over it;
  B) the audit_full sentinel_ledger_freshness block, lifted verbatim out of the
     patched audit_full.py and exercised against synthetic receipts -- including
     the negative controls (stale skip, sha mismatch, unknown status).
"""
import ast
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
from pathlib import Path

SCRATCH = Path(__file__).resolve().parent
PATCHED_FEC = SCRATCH / "patched" / "fec"
LIVE = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")

os.environ["MONEYBALL_ROOT"] = str(LIVE)
sys.path.insert(0, str(LIVE / "fec"))
sys.path.insert(0, str(PATCHED_FEC))


def load_sync():
    path = PATCHED_FEC / "legislation" / "sync_sentinel_bill_ledger.py"
    spec = importlib.util.spec_from_file_location("sentinel_sync_extra", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


print("=" * 72)
print("A) runtime resolution order with a REAL pinned config")
print("=" * 72)
module = load_sync()
with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    # A believable pinned runtime: a real file where node goes, a real modules dir.
    pinned = tmp / "pinned"
    (pinned / "bin").mkdir(parents=True)
    (pinned / "node_modules").mkdir()
    node = pinned / "bin" / ("node.exe" if os.name == "nt" else "node")
    node.write_bytes(b"")
    config = tmp / "artifact_tool_runtime.json"
    config.write_text(json.dumps({
        "schema": "artifact-tool-runtime-v1",
        "node": str(node),
        "node_modules": str(pinned / "node_modules"),
    }), encoding="utf-8")

    saved = {k: os.environ.get(k) for k in ("ARTIFACT_TOOL_NODE", "ARTIFACT_TOOL_NODE_MODULES")}
    saved_root = module.CODEX_RUNTIME_ROOT
    try:
        module.CODEX_RUNTIME_ROOT = tmp / "no-codex-cache"
        for key in saved:
            os.environ.pop(key, None)
        resolved = module.runtime(config)
        print("no env, config present     -> %r" % (resolved,))
        assert resolved is not None and resolved[0] == "config", resolved
        assert resolved[1] == str(node) and resolved[2] == str(pinned / "node_modules")

        # env wins, and a half-set env borrows the config's partner value.
        other = tmp / "envnode"
        (other / "bin").mkdir(parents=True)
        (other / "node_modules").mkdir()
        env_node = other / "bin" / ("node.exe" if os.name == "nt" else "node")
        env_node.write_bytes(b"")
        os.environ["ARTIFACT_TOOL_NODE"] = str(env_node)
        resolved = module.runtime(config)
        print("ARTIFACT_TOOL_NODE only    -> %r" % (resolved,))
        assert resolved[0] == "env" and resolved[1] == str(env_node)
        assert resolved[2] == str(pinned / "node_modules"), "half-set env must borrow the config partner"

        # A broken env override must fall THROUGH to the config, not fail.
        os.environ["ARTIFACT_TOOL_NODE"] = str(tmp / "gone" / "node.exe")
        resolved = module.runtime(config)
        print("broken env, config present -> %r" % (resolved,))
        assert resolved[0] == "config", resolved

        # Nothing anywhere -> None (the skip signal).
        os.environ["ARTIFACT_TOOL_NODE_MODULES"] = str(tmp / "gone" / "node_modules")
        resolved = module.runtime(tmp / "no-such-config.json")
        print("nothing resolvable         -> %r" % (resolved,))
        assert resolved is None
    finally:
        module.CODEX_RUNTIME_ROOT = saved_root
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
print("A) OK")
print()

print("=" * 72)
print("B) audit_full sentinel_ledger_freshness, lifted verbatim and exercised")
print("=" * 72)
source = (PATCHED_FEC / "audit" / "audit_full.py").read_text(encoding="utf-8")
start = source.index("# Sentinel bill-ledger freshness (2026-09-04)")
end = source.index("# 2026-07-04 nomological fix guard", start)
block = source[start:end]
print("lifted %d lines of the check block" % block.count("\n"))
compiled = compile(block, "<sentinel_ledger_freshness>", "exec")


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_case(label, receipt, ledger_bytes=b"ledger", ledger_age_days=0.0, write_receipt=True,
             write_ledger=True):
    results = []

    def ck(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "data" / "engine").mkdir(parents=True)
        ledger = root / "Sentinel Bill Ledger.xlsx"
        if write_ledger:
            ledger.write_bytes(ledger_bytes)
            stamp = time.time() - ledger_age_days * 86400.0
            os.utime(ledger, (stamp, stamp))
        if write_receipt:
            if isinstance(receipt, dict) and receipt.get("__bind_sha__"):
                receipt = dict(receipt)
                receipt.pop("__bind_sha__")
                receipt["live_ledger_workbook"] = dict(receipt.get("live_ledger_workbook") or {})
                receipt["live_ledger_workbook"]["sha256"] = _file_sha256(ledger)
            (root / "data" / "engine" / "sentinel_bill_workbook_receipt.json").write_text(
                json.dumps(receipt), encoding="utf-8")
        namespace = {"B": str(root), "os": os, "json": json, "ck": ck,
                     "_file_sha256": _file_sha256}
        exec(compiled, namespace)
    name, passed, detail = results[0]
    print("  %-46s %-4s  %s :: %s" % (label, "PASS" if passed else "FAIL", name, detail))
    return passed


cases = [
    ("receipt absent (feature never run)",
     run_case("receipt absent", {}, write_receipt=False), True),
    ("skip, ledger 3 days old",
     run_case("skip / 3d", {"schema": "sentinel-bill-workbook-receipt-v1",
                            "status": "SKIPPED_RUNTIME_ABSENT"}, ledger_age_days=3.0), True),
    ("skip, ledger 20.9 days old (inside window)",
     run_case("skip / 20.9d", {"status": "SKIPPED_RUNTIME_ABSENT"}, ledger_age_days=20.9), True),
    ("skip, ledger 22 days old (NEGATIVE CONTROL)",
     run_case("skip / 22d", {"status": "SKIPPED_RUNTIME_ABSENT"}, ledger_age_days=22.0), False),
    ("skip, ledger missing (NEGATIVE CONTROL)",
     run_case("skip / no ledger", {"status": "SKIPPED_RUNTIME_ABSENT"}, write_ledger=False), False),
    ("PASS bound to the installed bytes",
     run_case("PASS / bound", {"status": "PASS", "live_ledger_workbook": {}, "__bind_sha__": True}), True),
    ("PASS but sha mismatch (NEGATIVE CONTROL)",
     run_case("PASS / drifted", {"status": "PASS",
                                 "live_ledger_workbook": {"sha256": "0" * 64}}), False),
    ("PASS --no-install, fresh ledger",
     run_case("PASS / no-install fresh", {"status": "PASS", "live_ledger_workbook": None},
              ledger_age_days=2.0), True),
    ("PASS --no-install, 30-day ledger (NEGATIVE CONTROL)",
     run_case("PASS / no-install stale", {"status": "PASS", "live_ledger_workbook": None},
              ledger_age_days=30.0), False),
    ("unknown status (NEGATIVE CONTROL)",
     run_case("status WEIRD", {"status": "WEIRD"}), False),
    ("unreadable receipt (NEGATIVE CONTROL)",
     run_case("receipt list not object", [], ), False),
]
print()
bad = [(label, got, want) for label, got, want in cases if got != want]
for label, got, want in cases:
    print("  %-46s expected %-4s got %-4s  %s" % (label, "PASS" if want else "FAIL",
                                                  "PASS" if got else "FAIL",
                                                  "ok" if got == want else "<<< MISMATCH"))
print()
print("B) %s" % ("OK - every case, including 6 negative controls, behaved as specified"
                 if not bad else "MISMATCHES: %s" % bad))
raise SystemExit(0 if not bad else 1)
