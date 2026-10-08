#!/bin/bash
# "LIVE after landing_v2 and the follow-up", as a scratch tree: a clean export of the base 3248a6a02 (fec/ only, autocrlf off), the 13 files landing_v2 edits replaced by
# LIVE's exact pre-image bytes, LIVE's own staffer-live.js, landing_v2 applied with its shipped apply_landing.py --apply, then the follow-up with its shipped
# apply_landing.py --apply, then every staffer suite (one process per file, peak memory sampled). Never touches LIVE (read-only copies) or any repository.
#   usage: applied_tree_run.sh <work dir>     (the work dir must not hold applied_tree yet; delete it by hand to repeat)
set -u
SP="/c/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad"
W="$1"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
V2="$SP/landing_v2"
V3="$SP/landing_v3_ids"
DEST="$W/applied_tree"
LOG="$W/logs/applied_tree_run.log"
if [ -e "$DEST" ]; then echo "refusing: $DEST exists"; exit 1; fi
mkdir -p "$DEST"
{
  cd /c/Users/pgoff/Melange-wt/route-search
  git -c core.autocrlf=false archive 3248a6a02 fec | tar -x -C "$DEST"
  echo "exported 3248a6a02 fec ($(find "$DEST" -type f | wc -l) files)"
  cd "$V2/pre_images" && find . -type f | while read -r f; do cp "$f" "$DEST/${f#./}"; done
  echo "replaced $(find "$V2/pre_images" -type f | wc -l) files by LIVE pre-image bytes (landing_v2)"
  cp "$LIVE/fec/surfaces/staffer_live/staffer-live.js" "$DEST/fec/surfaces/staffer_live/staffer-live.js"
  echo "staffer-live.js: LIVE's own bytes"
  PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python "$V2/scripts/apply_landing.py" --root "$(cygpath -m "$DEST")" --apply
  echo "landing_v2 apply rc=$?"
  PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python "$V3/scripts/apply_landing.py" --root "$(cygpath -m "$DEST")" --apply
  echo "landing_v3_ids apply rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "$LIVE/fec/surfaces/$f" "$DEST/fec/surfaces/$f"
  done
  echo "data files copied"
  cd "$W"
  PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python run_with_peak.py "$(cygpath -m "$W")" "$(cygpath -m "$W")/logs/applied_tree_suites.log" -- python run_suites.py "$(cygpath -m "$DEST")" "$(cygpath -m "$W")/applied_tree_run.json"
  echo "SUITES rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    rm -f "$DEST/fec/surfaces/$f"
  done
  echo "data files deleted"
  echo "DONE"
} > "$LOG" 2>&1
