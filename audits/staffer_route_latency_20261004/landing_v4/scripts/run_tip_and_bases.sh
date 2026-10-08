#!/bin/bash
# Fix round of landing_v4: every staffer suite (run_suites.py: one process per file, peak memory sampled) and the extra tests that mention staffer_live (run_extra.py), on
#   1. a clean `git archive` export of the new tip (argument 1) of claude/staffer-route-v4-20261003,
#   2. a clean `git archive` export of 5d4a9bd0a (the tip before this fix round), the baseline the round is measured against, and
#   3. a clean `git archive` export of f23a40aee (the state LIVE runs now),
# each plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (deleted afterwards). Sequential on purpose: some suites are timing-sensitive.
# Read-only on LIVE; no repository is written (git archive only reads).
#   usage: run_tip_and_bases.sh <tip commit> <work dir>      (the work dir must not hold tip_v4, base_5d4a9bd0a or base_f23a40aee yet)
set -u
TIP="$1"
W="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="C:/Users/pgoff/Melange-wt/route-core"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
mkdir -p "$W/logs"
echo "start $(date +%H:%M:%S) tip $TIP"
bash "$HERE/export_and_run.sh" "$TIP" tip_v4 "$WT" "$W"
echo "tip export finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/export_and_run.sh" 5d4a9bd0a4445553823502aab60567ec3daa20af base_5d4a9bd0a "$WT" "$W"
echo "5d4a9bd0a export finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/export_and_run.sh" f23a40aee4c749bae9db132599a853a52c81d9bf base_f23a40aee "$WT" "$W"
echo "f23a40aee export finished rc=$? $(date +%H:%M:%S)"
echo "ALL DONE"
