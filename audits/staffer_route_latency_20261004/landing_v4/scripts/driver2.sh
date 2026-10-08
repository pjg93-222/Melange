#!/bin/bash
# The second driver of the fix round: waits for run_tip_and_bases.sh (logs/driver.log ends with ALL DONE), then runs run_rest.sh (applied tree, git-history subset, the changed tests three times,
# --ties), the changed test files as they were at 5d4a9bd0a against the new code (old_tests_on_new_code.sh) and the memory runs (run_memory.sh), one after the other.
#   usage: driver2.sh <work dir>
set -u
W="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
until grep -q "ALL DONE" "$W/logs/driver.log" 2>/dev/null; do sleep 5; done
echo "driver2 start $(date +%H:%M:%S)"
bash "$HERE/run_rest.sh" "$W" > "$W/logs/driver_rest.log" 2>&1
echo "run_rest finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/old_tests_on_new_code.sh" "$W" > "$W/logs/driver_old_tests.log" 2>&1
echo "old tests on new code finished rc=$? $(date +%H:%M:%S)"
bash "$HERE/run_memory.sh" "$W" > "$W/logs/driver_memory.log" 2>&1
echo "memory runs finished rc=$? $(date +%H:%M:%S)"
echo "DRIVER2 DONE"
