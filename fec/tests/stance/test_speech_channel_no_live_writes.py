# -*- coding: utf-8 -*-
"""Regression guard: test_speech_channel's CSV-emission test must not write into the data root it runs against.

Until 2026-10-20 that test called speech_stance_stack.main(), which rewrote the stance joblib + .sha256 sidecar, the
accuracy report, speech_stance_final.csv and its receipt under the kernel's MONEYBALL_ROOT (the live tree).  This copies
the inputs into a scratch root, runs that one test the way the kernel does (pytest subprocess, MONEYBALL_ROOT=<scratch>)
and fails if anything in the scratch root moved.

Standalone: python fec/tests/stance/test_speech_channel_no_live_writes.py
"""
from __future__ import annotations
import hashlib, os, shutil, subprocess, sys, tempfile, unittest
from pathlib import Path

FEC = Path(__file__).resolve().parents[2]
ROOT = FEC.parent
DATA_ROOT = Path(os.environ.get("MONEYBALL_ROOT", ROOT))


def state(root: Path) -> dict:
    """(mtime_ns, sha256) of the speech inputs and outputs, the dead-letter ledger and every file under data/stance; None marks an absent file."""
    files = [root / "speeches_cu.csv", root / "speeches_cu.receipt.json",
             root / "speech_stance_final.csv", root / "speech_stance_final.receipt.json",
             root / "data" / "engine" / "dead_letter" / "gold_labels.jsonl"]
    files += [p for p in (root / "data" / "stance").rglob("*") if p.is_file()]
    return {p.relative_to(root).as_posix():
            (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) if p.exists() else None
            for p in files}


class SpeechChannelNoLiveWrites(unittest.TestCase):

    def test_csv_emission_test_leaves_its_data_root_untouched(self):
        if not (DATA_ROOT / "speeches_cu.csv").exists():
            self.skipTest("speeches_cu.csv absent in this tree")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("speeches_cu.csv", "speeches_cu.receipt.json",
                         "speech_stance_final.csv", "speech_stance_final.receipt.json",
                         "data/engine/dead_letter/gold_labels.jsonl"):
                if (DATA_ROOT / name).exists():
                    destination = root / name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(DATA_ROOT / name, destination)
            (root / "data" / "stance").mkdir(parents=True)
            for path in (DATA_ROOT / "data" / "stance").iterdir():   # top-level files only: the model's inputs + joblib/sidecar/report
                if path.is_file():
                    shutil.copy2(path, root / "data" / "stance" / path.name)
            before = state(root)
            proc = subprocess.run(
                [sys.executable, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                 str(Path(__file__).with_name("test_speech_channel.py")), "-k", "test_main_emits_wellformed_csv"],
                cwd=str(ROOT), env=dict(os.environ, MONEYBALL_ROOT=str(root), COMPET_MULT="0"),
                capture_output=True, text=True, timeout=600)
            self.assertEqual(proc.returncode, 0, (proc.stdout + proc.stderr)[-3000:])
            self.assertIn("1 passed", proc.stdout, "inner test did not run (skipped?)")   # a skip also exits 0
            self.assertEqual(state(root), before, "the CSV-emission test wrote into its MONEYBALL_ROOT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
