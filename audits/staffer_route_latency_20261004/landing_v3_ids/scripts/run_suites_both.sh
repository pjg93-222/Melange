#!/bin/bash
# 1. the applied tree (LIVE-as-it-was + landing_v2 + the re-cut follow-up, each by its own apply_landing.py --apply) and every staffer suite on it;
# 2. the clean git-archive export of the new tip f23a40aee (the baseline) and every staffer suite on it, then the extra tests that mention staffer_live.
# Sequential on purpose: some suites are timing-sensitive. Read-only on LIVE (copies of 4 gitignored data files, deleted afterwards), no repository is written.
SP="/c/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad"
W="$SP/ids_followup2/suites_work"
NEW="$SP/landing_v3_ids"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
echo "start $(date +%H:%M:%S)"
bash "$NEW/scripts/applied_tree_run.sh" "$W"
echo "applied tree finished rc=$? $(date +%H:%M:%S)"
bash "$NEW/scripts/export_and_run.sh" f23a40aee4c749bae9db132599a853a52c81d9bf tip_f23a40aee "C:/Users/pgoff/Melange-wt/route-search" "$W"
echo "tip export finished rc=$? $(date +%H:%M:%S)"
echo "ALL DONE"
