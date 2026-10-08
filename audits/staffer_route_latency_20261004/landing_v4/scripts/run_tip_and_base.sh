#!/bin/bash
# Task 4 of the v4 integration: every staffer suite (run_suites.py: one process per file, peak memory sampled) and the extra tests that mention staffer_live (run_extra.py), on
#   1. a clean `git archive` export of the final tip (argument 1) of claude/staffer-route-v4-20261003, and
#   2. a clean `git archive` export of f23a40aee (the state LIVE runs now), the baseline,
# each plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (deleted afterwards). Sequential on purpose: some suites are timing-sensitive.
# Read-only on LIVE; no repository is written (git archive only reads).
#   usage: run_tip_and_base.sh <tip commit> <work dir>      (the work dir must not hold tip_v4 or base_f23a40aee yet)
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
bash "$HERE/export_and_run.sh" f23a40aee4c749bae9db132599a853a52c81d9bf base_f23a40aee "$WT" "$W"
echo "baseline export finished rc=$? $(date +%H:%M:%S)"
echo "ALL DONE"
