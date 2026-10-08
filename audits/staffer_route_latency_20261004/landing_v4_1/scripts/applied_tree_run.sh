#!/bin/bash
# "LIVE after landing_v2, landing_v3_ids, landing_v4 and v4.1", as a scratch tree: a clean export of LIVE's HEAD 3366a7840 (fec/ only, autocrlf off; that commit holds the three earlier landings as LF blobs), LIVE's CURRENT bytes for every file the three earlier landings
# touched (build_applied_tree.py: read-only copies, each checked against its post-image hash), v4.1 applied with its shipped apply_landing.py --apply, then every staffer suite (one process per file, peak
# memory sampled) and the extra tests that mention staffer_live. Never touches LIVE (read-only copies) or any repository.
#   usage: applied_tree_run.sh <work dir>     (the work dir must not hold applied_tree yet; delete it by hand to repeat)
set -u
W="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
LANDING="$(dirname "$HERE")"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
WT="C:/Users/pgoff/Melange-wt/route-core"
DEST="$W/applied_tree"
LOG="$W/logs/applied_tree_run.log"
if [ -e "$DEST" ]; then echo "refusing: $DEST exists"; exit 1; fi
mkdir -p "$DEST" "$W/logs"
export PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1
{
  cd "$WT"
  git -c core.autocrlf=false archive 3366a7840f90a204d496070da11354245d18f741 fec | tar -x -C "$DEST"
  echo "exported 3366a7840 fec ($(find "$DEST" -type f | wc -l) files)"
  python "$HERE/build_applied_tree.py" "$(cygpath -m "$DEST")"
  echo "overlay rc=$?"
  python "$HERE/apply_landing.py" --root "$(cygpath -m "$DEST")" --apply
  echo "landing_v4_1 apply rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "$LIVE/fec/surfaces/$f" "$DEST/fec/surfaces/$f"
  done
  echo "data files copied"
  cd "$HERE"
  python run_with_peak.py "$(cygpath -m "$W")" "$(cygpath -m "$W")/logs/applied_tree_suites.log" -- python "$HERE/run_suites.py" "$(cygpath -m "$DEST")" "$(cygpath -m "$W")/applied_tree_run.json"
  echo "SUITES rc=$?"
  python "$HERE/run_extra.py" "$(cygpath -m "$DEST")" "$(cygpath -m "$W")/applied_tree_extra.json" > "$(cygpath -m "$W")/logs/applied_tree_extra.log" 2>&1
  echo "EXTRA rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    rm -f "$DEST/fec/surfaces/$f"
  done
  echo "data files deleted"
  echo "DONE"
} > "$LOG" 2>&1
