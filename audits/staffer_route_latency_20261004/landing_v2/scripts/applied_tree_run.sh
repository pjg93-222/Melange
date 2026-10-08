#!/bin/bash
# "LIVE after the apply", as a scratch tree: a clean export of the base 3248a6a02 (fec/ only, autocrlf off), the 13 edited files replaced by
# LIVE's exact pre-image bytes (landing_v2\pre_images), the patch applied with the shipped apply_landing.py --apply, then every staffer suite.
set -u
SP="/c/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad"
SPW=$(cygpath -m "$SP")
W="$SP/uuid_merge"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
DEST="$W/applied_tree"
LOG="$W/logs/applied_tree_run.log"
mkdir -p "$DEST"
{
  cd /c/Users/pgoff/Melange-wt/route-jobs
  git -c core.autocrlf=false archive 3248a6a02 fec | tar -x -C "$DEST"
  echo "exported 3248a6a02 fec ($(find "$DEST" -type f | wc -l) files)"
  cd "$SP/landing_v2/pre_images" && find . -type f | while read -r f; do cp "$f" "$DEST/${f#./}"; done
  echo "replaced $(find "$SP/landing_v2/pre_images" -type f | wc -l) files by LIVE pre-image bytes"
  PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python "$SPW/landing_v2/scripts/apply_landing.py" --root "$(cygpath -m "$DEST")" --apply
  echo "apply rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "$LIVE/fec/surfaces/$f" "$DEST/fec/surfaces/$f"
  done
  echo "data files copied"
  cd "$W"
  python run_suites.py "$(cygpath -m "$DEST")" "$W/applied_tree_run.json"
  echo "SUITES rc=$?"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    rm -f "$DEST/fec/surfaces/$f"
  done
  echo "data files deleted"
  echo "DONE"
} > "$LOG" 2>&1
