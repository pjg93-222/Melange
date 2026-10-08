#!/bin/bash
# v4.1: every staffer suite (run_suites.py: one process per file, peak memory sampled) and the extra tests that mention staffer_live (run_extra.py), on
#   1. a clean `git archive` export of the v4.1 tip (argument 1), claude/staffer-route-v4-1-20261004, and
#   2. a clean `git archive` export of 79ef9f1b7440bcee21c7f7c677a93263d9fcc04a, the v4 tip that LIVE runs now (the baseline),
# each plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (deleted afterwards). Sequential on purpose: some suites are timing-sensitive.
#   usage: run_tip_and_base.sh <tip commit> <work dir>      (the work dir must not hold tip_v41 or base_v4 yet)
set -u
TIP="$1"
W="$2"
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="C:/Users/pgoff/Melange-wt/route-core"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
mkdir -p "$W/logs"
echo "start $(date +%H:%M:%S) tip $TIP"
bash "$HERE/export_and_run.sh" "$TIP" tip_v41 "$WT" "$W"
echo "tip export finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/export_and_run.sh" 79ef9f1b7440bcee21c7f7c677a93263d9fcc04a base_v4 "$WT" "$W"
echo "v4 export finished rc=$? $(date +%H:%M:%S)"
echo "ALL DONE"
