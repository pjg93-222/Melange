#!/bin/bash
# The new and changed staffer tests of the v4 tip (every test file the three branches add, and every one this integration edits), three runs in a row, one process per file
# (run_suites.py --only ...: pytest per Python file, a file pytest collects no tests from run as a script, `node --test` per .cjs file).
#   usage: run_new_tests_3x.sh <root> <label> <work dir>
# <root> is a tree that holds the tip: the worktree itself (git is available there, so the tests that read a base commit from git run instead of skipping) or a clean `git archive` export.
# Run with the worktree as <root>, PYTHONDONTWRITEBYTECODE keeps it clean. Never touches LIVE or any repository.
set -u
ROOT="$1"
LABEL="$2"
W="$3"
HERE="$(cd "$(dirname "$0")" && pwd)"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
mkdir -p "$W/logs"
ONLY=(--only test_staffer_office_covered_staff --only test_staffer_unreachable_hint --only test_staffer_route_jobs --only test_staffer_contact_group
      --only test_staffer_payroll_people --only test_staffer_prewarm --only test_staffer_row_equality --only test_staffer_closeness_bidirectional
      --only test_staffer_left_out_staff --only test_staffer_route_models --only test_staffer_inventory_worker_committee_names
      --only test_staffer_live_query_committee_names --only test_staffer_inventory_worker_codes --only test_staffer_live_query_ids)
for i in 1 2 3; do
  python "$HERE/run_suites.py" "$ROOT" "$W/new_${LABEL}_run$i.json" "${ONLY[@]}" > "$W/logs/new_${LABEL}_run$i.log" 2>&1
  echo "$LABEL run $i rc=$? $(tail -1 "$W/logs/new_${LABEL}_run$i.log")"
done
