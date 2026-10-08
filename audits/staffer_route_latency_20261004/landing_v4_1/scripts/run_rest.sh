#!/bin/bash
# The rest of the v4.1 suite proof, one step after the other (some suites are timing-sensitive), after run_tip_and_base.sh has finished (logs/driver.log ends with ALL DONE):
#   1. the applied tree: clean 3366a7840 (LIVE HEAD) + LIVE's current bytes for every file the earlier landings touched + v4.1 by its own apply script, and every staffer suite on it (applied_tree_run.sh);
#   2. the tests that skip in a clean export for want of git history (they read a base commit with `git show`), on the clean tip export and on the applied tree, with GIT_DIR pointed at the
#      shared object store so `git -C <export> show <sha>:<path>` works without a .git in the export (read-only: git show writes nothing);
#   3. the new and changed tests three times in a row, in the worktree itself (git available) and in the clean tip export;
#   4. `python -m fec.surfaces.test_staffer_closeness_bidirectional --ties` (violations 0), on the clean tip export and on the applied tree.
#   usage: run_rest.sh <suites work dir>        (the first driver's log in <work dir>/logs/driver.log must end with ALL DONE)
set -u
W="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
WT="C:/Users/pgoff/Melange-wt/route-core"
LIVE_GIT="C:/Users/pgoff/OneDrive/Desktop/Melange Systems/.git"
export PYTHONDONTWRITEBYTECODE=1 PYTHONIOENCODING=utf-8
until grep -q "ALL DONE" "$W/logs/driver.log" 2>/dev/null; do sleep 5; done
echo "start $(date +%H:%M:%S)"
bash "$HERE/applied_tree_run.sh" "$W"
echo "applied tree finished rc=$? $(date +%H:%M:%S)"
GITSUBSET=(--only test_staffer_office_covered_staff --only test_staffer_unreachable_hint --only test_staffer_inventory_worker_codes --only test_staffer_inventory_worker_committee_names
           --only test_staffer_left_out_staff --only test_staffer_live_query_committee_names --only test_staffer_live_query_ids --only test_staffer_prewarm --only test_staffer_request_work_index)
for name in tip_v41 applied_tree; do
  cp_dir="$W/$name"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    cp "/c/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/surfaces/$f" "$cp_dir/fec/surfaces/$f"
  done
  GIT_DIR="$LIVE_GIT" GIT_OPTIONAL_LOCKS=0 python "$HERE/run_suites.py" "$(cygpath -m "$cp_dir")" "$W/gitsubset_${name}_run.json" "${GITSUBSET[@]}" > "$W/logs/gitsubset_${name}.log" 2>&1
  echo "git-history subset on $name rc=$? $(tail -1 "$W/logs/gitsubset_${name}.log")"
  for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
    rm -f "$cp_dir/fec/surfaces/$f"
  done
done
bash "$HERE/run_new_tests_3x.sh" "$WT" worktree "$W"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  cp "/c/Users/pgoff/OneDrive/Desktop/Melange Systems/fec/surfaces/$f" "$W/tip_v41/fec/surfaces/$f"
done
bash "$HERE/run_new_tests_3x.sh" "$(cygpath -m "$W/tip_v41")" export "$W"
for f in staffer_identity_reference_seeds.json staffer_named_filing_evidence.json staffer_payroll_inventory_exceptions.json staffer_user_assertions.json; do
  rm -f "$W/tip_v41/fec/surfaces/$f"
done
for name in tip_v41 applied_tree; do
  started=$(date +%s)
  (cd "$W/$name" && python -m fec.surfaces.test_staffer_closeness_bidirectional --ties > "$W/logs/ties_${name}.log" 2>&1)
  echo "--ties on $name rc=$? in $(( $(date +%s) - started )) s: $(tr '\n' '|' < "$W/logs/ties_${name}.log" | cut -c1-400)"
done
echo "REST DONE $(date +%H:%M:%S)"
