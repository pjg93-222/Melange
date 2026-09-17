# Commit plan for Paul (2026-09-17, Mentat tree C:\Users\pgoff\Mentat, branch codex/mentat-crypto)

Nothing in this lane was staged or committed. HEAD stayed at `3fdfeae8f` (S3f) throughout. A peer session (S3 evidence lane) is committing to the same tree; stage by explicit path only, never `git add -A`.

## 1. Dwarfed cross-reference (Paul's ruling: outliers and refunds only, no totals)

Files (9 modified, 5 new). Backups `<file>.bak-20260917-xref` sit beside each modified file; delete them after the commit.

```
git add mentat/tools/cross_reference_digest.py mentat/tools/run_cross_reference.py \
        mentat/app/cross_reference_data.py mentat/app/cross-reference.js \
        mentat/tests/test_cross_reference_data.py mentat/tests/test_cross_reference_digest.py \
        mentat/tests/test_cross_reference_view.cjs \
        mentat/tests/test_navigation_scope_browser.cjs mentat/tests/test_console_browser.cjs \
        mentat/tests/test_studio_wording.cjs
git commit -m "Dwarf the cross-reference tab to clear refunds and obvious outliers; publish no totals"
```

Notes: the three browser/wording tests lost one assertion each that named the old wording (`Observed original giving`); `test_cross_reference_data.py` / `test_cross_reference_view.cjs` were untracked before this lane and are now tracked with the new expectations. `mentat/README.md` still describes the old dashboard (tracked and dirty by another lane; not touched). Evidence: `audits/mentat_xref_workbook_review_20260917/receipts/XREF_DWARF_RECEIPT.md`; live route check `receipts/xref_live_check.py` (Banking: 641 unmatched negative adjustments, 4,778 non-giving reclassifications of $76,500,263.92, 24 large receipts; Fintech: 56 / 100 / 5; no total-like key in any response). The two existing runs carry a new `digest.json` (state, not code). Thresholds `MENTAT_XREF_LARGE_RECEIPT_CENTS` (default $1,000,000) and `MENTAT_XREF_LARGE_INDIVIDUAL_CENTS` (default $100,000) await Paul's ratification.

## 2. Worksheet-mode guards in Chart Studio

Files (3 modified, 1 new). Backups `<file>.bak-20260917-wsg`.

```
git add mentat/app/chart-studio-core.js mentat/app/chart-studio.js \
        mentat/app/tests/chart-studio-core.test.js mentat/tests/test_studio_worksheet_guard_browser.cjs
git commit -m "Open polymorphic Overview sheets on the partition the report totals; caption committee-activity sheets; list the Data workbook first"
```

Evidence: `receipts/WORKSHEET_GUARD_RECEIPT.md`; core suite 163/163, wording 10/10, browser guard test 3/3 on a read-only 8834 instance against the real Banking workbook.

## 3. Tidy lane's deferred patches P5 / P6c / P7b (rebased onto HEAD)

Only P5 can be committed now. The working-tree `build_industry_report.ps1` carries another lane's hunks on top of P5, so the packet patch no longer applies to HEAD; the HEAD-anchored version `audits/mentat_xref_workbook_review_20260917/tidy_rebase/P5-rebased.patch` passes `git apply --check --cached` and a PowerShell parse (0 errors).

```
git apply --cached audits/mentat_xref_workbook_review_20260917/tidy_rebase/P5-rebased.patch
git commit -m "Wire the companion Data workbook into the report build"
```

This stages only the tidy hunks of the .ps1; the other lane's hunks stay in the working tree. P6c (`report_insights.py`) edits inside `def worksheet_accounting()`, which exists only in the other lane's UNCOMMITTED file and is absent from HEAD; P7b (`test_report_insights.py`) sits in that lane's test region. Both stay applied in the working tree and are committed after that lane commits, from the tidy packet as they are. P2 (exporter hook) and P8 (writer) are already in HEAD, so P5 alone is enough for a rebuild to produce the companion Data workbook.

## 4. Street-column tolerance in the exporter (unblocks every rebuild)

`audits/mentat_xref_workbook_review_20260917/gate_census/report_R_street_tolerant.patch` (proven: `git apply --check` clean, Crypto census identical through the real loader, real street values preserved on a database that has the columns). Apply on Paul's go:

```
git apply audits/mentat_xref_workbook_review_20260917/gate_census/report_R_street_tolerant.patch
git add mentat/R/report.R
git commit -m "Export from snapshots that predate the street columns; absent means blank, not a failed export"
```

## 5. After the commits

- Restart console 8806 through the launcher (assets changed; the F1 stamp will show a reload banner until then).
- Rule on the receipt table (`RECEIPT_RULING_TABLE_2026-09-17.md`); extend `mentat/inputs/fec_receipt_rules.json` accordingly (gitignored; Paul's file).
- Rebuild order once the gate passes: Credit Union (4 refusals), Community Banks (11), Credit Arms (17), P&C (53), Crypto (80 but $187.5M and the R2/R3 rulings), Fintech (94), Telecom (96), Banking (593; and the 50,000-row worksheet-cap check on its companion).
