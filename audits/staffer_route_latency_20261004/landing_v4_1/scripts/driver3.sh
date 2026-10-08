#!/bin/bash
# The third driver of the v4.1 proof: waits for run_rest.sh (logs/driver_rest.log ends with REST DONE), then runs the old tests on the new code, the gc and rebuild evidence, and the mutation checks, one after the other.
#   usage: driver3.sh <suites work dir>
set -u
W="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
LANDING="$(dirname "$HERE")"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
until grep -q "REST DONE" "$W/logs/driver_rest.log" 2>/dev/null; do sleep 5; done
echo "driver3 start $(date +%H:%M:%S)"
bash "$HERE/old_tests_on_new_code.sh" "$W" > "$W/logs/driver_old_tests.log" 2>&1
echo "old tests on new code finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/evidence.sh" "$W" "$W/evidence" > "$W/logs/driver_evidence.log" 2>&1
echo "evidence finished rc=$? $(date +%H:%M:%S)"
MUT="$W/mutation_tree"
if [ ! -e "$MUT" ]; then
  mkdir -p "$MUT" && cp -r "$W/tip_v41/fec" "$MUT/"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "$LIVE/fec/surfaces/$f" "$MUT/fec/surfaces/$f"
  done
fi
python "$HERE/mutations.py" "$(cygpath -m "$MUT")" > "$W/mutations.log" 2>&1
echo "mutations finished rc=$? $(date +%H:%M:%S): $(tail -1 "$W/mutations.log")"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  rm -f "$MUT/fec/surfaces/$f"
done
echo "DRIVER3 DONE"
