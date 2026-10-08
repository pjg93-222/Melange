#!/bin/bash
# test_staffer_identity_api.py failed in two of the suite runs of the fix round (the f23a40aee baseline and the applied tree) and passed in the other two: this runs it N times in each of the four trees and
# counts, to show that it is an intermittent failure of the test's own HTTP client on this host (WinError 10053 reading the answer to a rejected POST) and not something a tree causes.
# The 4 gitignored data files are copied read-only from LIVE for the runs and deleted afterwards.   usage: flake_identity_api.sh <work dir> [runs, default 20]
set -u
W="$1"
N="${2:-20}"
LIVE="/c/Users/pgoff/OneDrive/Desktop/Melange Systems"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8 PYTHONUTF8=1
for name in base_f23a40aee base_5d4a9bd0a tip_v4 applied_tree; do
  tree="$W/$name"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "$LIVE/fec/surfaces/$f" "$tree/fec/surfaces/$f"
  done
  pass=0; fail=0; names=""
  for i in $(seq 1 "$N"); do
    out=$(cd "$tree" && python -m pytest fec/tests/surfaces/test_staffer_identity_api.py -q -p no:cacheprovider --no-header --tb=line 2>&1)
    if echo "$out" | grep -q " failed"; then
      fail=$((fail+1))
      names="$names | $(echo "$out" | grep -E '^(FAILED|SUBFAILED)' | sed 's/.*:://' | cut -c1-110 | head -2 | tr '\n' ' ')"
    else
      pass=$((pass+1))
    fi
  done
  echo "$name: $N runs, $pass passed, $fail failed $names"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    rm -f "$tree/fec/surfaces/$f"
  done
done
