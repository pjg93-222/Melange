#!/bin/bash
# The four test files the v4.1 round changed (and the one it adds is not in the v4 tree), as they were at 79ef9f1b7 (the v4 tip), run against the new tip's code: every test that fails is a test
# whose expectation the round changed on purpose, and every other test must pass. A copy of the clean tip export, the old test files laid over it (git show with autocrlf off), the 4 data files
# copied read-only from LIVE (deleted afterwards), GIT_DIR at the shared object store (read-only) so the tests that read a base commit run instead of skipping.
#   usage: old_tests_on_new_code.sh <work dir>      (holds tip_v41 from export_and_run.sh; must not hold old_tests_on_tip yet)
set -u
W="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="C:/Users/pgoff/Melange-wt/route-core"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
LIVE_GIT="C:/Users/pgoff/OneDrive/Desktop/Melange Systems/.git"
DEST="$W/old_tests_on_tip"
if [ -e "$DEST" ]; then echo "refusing: $DEST exists"; exit 1; fi
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
mkdir -p "$DEST"
cp -r "$W/tip_v41/fec" "$DEST/"
cd "$WT"
for f in fec/tests/surfaces/test_staffer_left_out_staff.cjs fec/tests/surfaces/test_staffer_office_covered_staff.py fec/tests/surfaces/test_staffer_prewarm.py fec/tests/surfaces/test_staffer_unreachable_hint.py; do
  git -c core.autocrlf=false show "79ef9f1b7440bcee21c7f7c677a93263d9fcc04a:$f" > "$DEST/$f"
done
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  cp "$LIVE/fec/surfaces/$f" "$DEST/fec/surfaces/$f"
done
cd "$HERE"
GIT_DIR="$LIVE_GIT" GIT_OPTIONAL_LOCKS=0 python run_suites.py "$(cygpath -m "$DEST")" "$W/old_tests_on_tip_run.json" --only test_staffer_left_out_staff \
  --only test_staffer_office_covered_staff --only test_staffer_prewarm --only test_staffer_unreachable_hint > "$W/logs/old_tests_on_tip.log" 2>&1
echo "old tests on the new code rc=$?"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  rm -f "$DEST/fec/surfaces/$f"
done
echo "data files deleted"
