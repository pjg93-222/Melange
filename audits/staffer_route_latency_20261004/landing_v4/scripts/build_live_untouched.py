r"""Write proof/live_untouched.txt: the three read-only fingerprints of LIVE (live_fingerprint.py: before any work, midway, after the last proof) and the state of the 8841 sidecar.

usage: python build_live_untouched.py <landing_v4 dir> <landing_v4_work dir> <sidecar note file>
The sidecar note is a text file with the lines to print under the sidecar heading (the PID, its start time, its command line), taken read-only from the process table.
"""
import os
import sys

NEW, WORK, NOTE = sys.argv[1], sys.argv[2], sys.argv[3]


def clean(path, lines=3):
    """The first `lines` lines of a fingerprint file (HEAD, status digest, file digest); a file taken with --list carries one more line per file, which is not repeated here."""
    with open(path, encoding='utf-8-sig') as handle:
        return '\n'.join(handle.read().strip().splitlines()[:lines])


out = [r"# LIVE (C:\Users\pgoff\OneDrive\Desktop\Melange Systems) fingerprinted read-only by scripts\live_fingerprint.py: git HEAD, the sha256 of the full 'git status --porcelain=v1 -uall' text, and the sha256 of",
       "# 'relative path|size|mtime_ns' over every file under fec/surfaces, fec/tests/surfaces and fec/tools (__pycache__ excluded). Taken on 2026-10-03 for the re-cut after the fix round: before any work of the round (22:56); midway (after the three suite",
       "# runs, the git-history runs, the three-in-a-row runs and --ties, before the last proofs); and after the last proof. (The first cut's three fingerprints, taken at 20:00, 21:09 and 21:16, are the same three lines.)",
       "# Identical three times means nothing in those trees was written, touched or re-saved by the integration, the cut, the proofs, the suite runs or the dry runs, and git status did not move anywhere in LIVE.",
       "# (The count was 883 files and 59,844 status lines before landing_v3_ids was applied at 16:24:42 and is 885 and 59,847 since: its two new files and its one newly modified tracked file.)",
       "",
       "## before", clean(os.path.join(WORK, "live_fingerprint_before.txt")), "",
       "## midway", clean(os.path.join(WORK, "live_fingerprint_midway.txt")), "",
       "## after", clean(os.path.join(WORK, "live_fingerprint_after.txt")), "",
       "## the sidecar on 127.0.0.1:8841 (not touched: no script of this work connects to it, and the tests that start servers listen on ephemeral ports)",
       clean(NOTE), "",
       "## no bytecode or other file was written into LIVE's fec tree: `find fec -type f -newermt \"2026-10-03 17:00:00\"` lists nothing (the last write there is landing_v3_ids at 16:24:42),",
       "## and LIVE's fec/tools/__pycache__/live_patch.cpython-312.pyc is still the one of 2026-09-19."]
with open(os.path.join(NEW, "proof", "live_untouched.txt"), "w", encoding="utf-8", newline="\n") as handle:
    handle.write("\n".join(out) + "\n")
print("wrote live_untouched.txt")
