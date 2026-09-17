#!/usr/bin/env bash
# Drives the read-only gate census across every industry. Small databases
# first so failures surface early; Banking third because it is the
# cross-check against the 2,070-row receipt-review CSV.
set -u

export PATH="/c/Program Files/R/R-4.6.0/bin/x64:$PATH"
export MENTAT_INPUT_DIR="C:/Users/pgoff/Mentat/mentat/inputs"
unset MENTAT_CYCLE_FILTER

OUT="C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-xref-spreadsheet-review-3f1ff0/53c11c19-7e9e-4d2f-882c-36f194e8428b/scratchpad/gate_census"
REPAIR="C:/Users/pgoff/Mentat/mentat/.cache/receipt-metadata-repair-20260910"
BANKDB="C:/Users/pgoff/Mentat/mentat/.cache/report-repairs/banking-20260910/data/mentat.db"

cd "C:/Users/pgoff/Mentat/mentat" || exit 1

run() {
  slug="$1"; label="$2"; db="$3"
  echo "########## $slug  ($(date +%H:%M:%S))"
  Rscript "$OUT/gate_census.R" "$db" "$label" "$slug" "$OUT" 2>&1
  echo "########## $slug exit=$? ($(date +%H:%M:%S))"
  echo
}

run community_banks             "Community Banks"               "$REPAIR/community_banks/mentat.db"
run credit_union                "Credit Union"                  "$REPAIR/credit_union/mentat.db"
run banking                     "Banking"                       "$BANKDB"
run fintech                     "Fintech"                       "$REPAIR/fintech/mentat.db"
run property_casualty_insurance "Property & Casualty Insurance" "$REPAIR/property_casualty_insurance/mentat.db"
run credit_arms                 "Credit Arms"                   "$REPAIR/credit_arms/mentat.db"
run telecom                     "Telecom"                       "$REPAIR/telecom/mentat.db"

echo "ALL DONE $(date +%H:%M:%S)"
