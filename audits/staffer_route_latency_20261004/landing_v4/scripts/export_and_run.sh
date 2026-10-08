#!/bin/bash
# usage: export_and_run.sh <rev> <name> <worktree> <work dir>
#   Exports <rev>'s fec/ from <worktree>'s repository with autocrlf off (a clean tree, no .git), adds the 4 gitignored data files copied read-only from LIVE fec/surfaces/,
#   runs every staffer suite once (run_suites.py: one process per file) under run_with_peak.py (peak resident memory of the process tree), then the extra tests that mention
#   staffer_live (run_extra.py), and deletes the data files again. Never touches LIVE (read-only copies) or any repository. The work dir must not hold <name> yet.
#   Used for the v4 tip and for f23a40aee by run_tip_and_base.sh: export_and_run.sh <sha> tip_v4 C:/Users/pgoff/Melange-wt/route-core <work dir>
set -u
REV="$1"; NAME="$2"; WT="$3"; W="$4"
HERE="$(cd "$(dirname "$0")" && pwd)"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
DEST="$W/$NAME"
if [ -e "$DEST" ]; then echo "refusing: $DEST exists"; exit 1; fi
mkdir -p "$DEST" "$W/logs"
cd "$WT"
git -c core.autocrlf=false archive "$REV" fec | tar -x -C "$DEST"
echo "exported $REV fec -> $DEST ($(find "$DEST" -type f | wc -l) files)"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  cp "$LIVE/fec/surfaces/$f" "$DEST/fec/surfaces/$f"
done
echo "data files copied"
cd "$HERE"
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python run_with_peak.py "$W" "$W/logs/${NAME}_suites.log" -- python "$HERE/run_suites.py" "$DEST" "$W/${NAME}_run.json"
echo "SUITES rc=$?"
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python "$HERE/run_extra.py" "$DEST" "$W/${NAME}_extra.json" > "$W/logs/${NAME}_extra.log" 2>&1
echo "EXTRA rc=$?"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  rm -f "$DEST/fec/surfaces/$f"
done
echo "data files deleted"
