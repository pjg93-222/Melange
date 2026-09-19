# Lane A progress

- [2026-09-14T23:09:07Z] laneA dirs created; contract + plan read.
- [recon] Live files read: report_insights.py (header_row/numeric/profile_columns/worksheet_accounting/worksheet_data/MAX_ROWS=50000),
  contribution_data.py (_payload_rows streaming, _workbook_source literal scan), tools/report_source_guard.py
  (NOTE: it is tools/, NOT app/ as the brief said) source_facts + cycle_of(y)=y+y%2 + cents,
  export_crypto_spending_data.R raw_export/workbook_raw_export/payload, R/report.R label maps (16+6) + zip5 rule,
  split_telecom_workbook.py Table+TableStyleInfo+number_format pattern.
- [recon] CU cache IS readable. Payload = .cache/industry-report/credit_union/industry_data-f9e956354525acb0.json (225,773,786 B),
  manifest-f9e956354525acb0.json, stage-all_cycles/{finalizer_data.json, Credit Union Industry Spending Overview.xlsx (20.5MB),
  downstream_activity.usv (98,917 rows), beneficiary_bridge.usv (6,929 rows)}. Payload top-level keys: metadata, cycles, companies,
  raw_rows(=workbook_raw_export, 28,960), cycle_exceptions, committee_master_sources, beneficiary_sources, employees, committee_map,
  transfer_edges, candidate_committee_links, candidate_master, downstream_activity, beneficiary_bridge, beneficiary_summary,
  transfer_paths, allocation_estimates, allocation_coverage, attribution_summary, source_freshness, classification_review(EMPTY),
  quality_checks. ABSENT: funding_cohorts, state_destinations, recipient_locations, accounting_basis, recipient_detail, contributor_detail.
  Source DB EXISTS: .cache/repair-20260908-databases/credit_union.db (382,787,584 B) -> W7 can run.
  expected_cycle_totals = {2021-2022: 246812.930000002, 2023-2024: 563762.159999999, 2025-2026: 242809.53};
  workbook manifest formula_receipt.cycle_totals = identical -> W5 and W6 both live.
- [recon] Cached payload raw_rows carries only 34 of the contract's 56 contribution columns (the Sept-8 cache predates the
  wide raw_export projection). Committee type/designation recoverable from committee_map. Full blank list in A_RECEIPT.md.
- [step 1] build_tidy_workbook.py written (writer, contract section 3). 11/11 unit tests pass (test_tidy_workbook.py, step 5 written early
  and used as the writer smoke test).
- [step 2] payload_to_stage.py written and RUN (8m36s, streams the 225MB payload once per key). Store =
  laneA/stage/tidy-cu.sqlite, 91,414,528 B, sha256 cdbf11baa58fb6f0...
  Rows: contributions 28,960 | committees 358 | committee_sponsors 205 | candidates 2,836 | downstream_activity 98,917 |
  beneficiary_bridge 5,044 (Company view of 6,929) | giving_facts 374 | recipient_facts 708 | contributor_facts 3,922 |
  location_facts 2,223 | transfer_paths 255,207 | allocation_estimates 70,139 | allocation_coverage 170 | source_freshness 15 |
  classification_review 0 (empty) | data_quality 13.
  Bridge flag vocabulary (8): Contribution / Other, Contribution to nonaffiliated committee, Coordinated party expenditure,
  In-kind contribution to registered filer, Independent expenditure - oppose, Independent expenditure - support, Oppose, Support.
  Store analysis totals per cycle = 246812.93 / 563762.16 / 242809.53 == payload expected_cycle_totals EXACTLY.
  FINDING: transfer_paths per cycle = 68,039 / 123,789 / 63,379 - every per-cycle chunk still exceeds the console's 50,000 cap.
  allocation_estimates per cycle = 26,490 / 32,150 / 11,499 (fits). Recorded, not silently truncated.
- [step 3] MOCK BUILT. out/Credit Union Industry Spending Data (MOCK).xlsx, 33,307,701 B, 22 sheets, 469,226 data rows, 197.18s,
  sha256 2c7fc5b4360178d917c796a1b935f45a2e6968ef7347cb1875994f38fc63e7c3. Writer exit 0; ALL 97 writer check rows passed
  (W1-W4 3 each, W5 3, W6 3, W7 30 cycle x company rows recomputed from the 382MB source DB, W8 14, W9 14, W10 20, W11 1).
  Split sheets: Downstream Activity / Transfer Paths / Allocation Estimates, 3 cycles each.
  Absent tables: funding_cohorts, classification_review (empty), state_destinations, recipient_locations, accounting_basis.
  Blank columns: 19 (15 Contributions, 2 Committees, Downstream Activity/Transfer Records, Beneficiary Bridge/Source Recipient Category).
  FIRST run exited 2 with 3 real failures (Ownership Status ';' x2, Downstream Activity key collisions) -> two documented
  deviations, see A_RECEIPT.md D2/D3. The refuse-to-publish path is therefore proven on real data, not only in the unit test.
- [step 4a] tidy_lint.py written; mock PASSES with ZERO findings (7m15s over 469k rows). Two lint bugs found and fixed while
  proving it: the workbook r:id namespace is officeDocument, not package (tables and merges were invisible), and int/float
  must collapse to one "number" kind (XLSX has a single numeric type; openpyxl reads 25.0 back as int 25).
- [step 4b] NEGATIVE CONTROL SATISFIED: tidy_lint.py on the published July Overview
  (C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files\Credit Union Industry Spending Overview.xlsx, 15,113,389 B)
  = 89 findings, exit 0 under --expect fail. Breakdown: table-ref x50, merged-cells x26, multivalue x8, sheet-name x3
  (the three bare cycle-label sheets), aggregate-rows x1, table-count x1. Full output in laneA_overview_lint.txt.
  Mock = 0 findings. Same lint, same rules, opposite verdicts.
- [step 6 in flight] reader_check.py running against the live app modules; it is slow and memory-hungry
  (python.exe at 6.5 GB RSS) because report_insights.worksheet_data reopens the 33MB workbook per sheet and
  lru_caches six full sheet payloads. Measuring, will report.
- [step 8 draft] A_RECEIPT.md written with sections 1-5 and 8-11 complete; sections 6 (reader proof) and 7 (negative control)
  pending their runs.
- [note] The 6.5 GB python.exe seen earlier is NOT mine: PID 12580 is Paul's staffer_live_server.py on port 8841
  (started 16:38). Checked its command line before touching anything; nothing of Paul's was killed. My first reader_check
  run was simply buffering all output to the end; it is now instrumented to stream one line per sheet and to clear
  report_insights' 6-entry lru_cache between sheets.
- [step 6 timing caveat] The first measured sheet (About, 38 rows) took 212 s inside worksheet_data. That measurement is
  CONTENDED: the negative-control writer was concurrently reading 4.5 GB from the 382 MB source DB and Paul's
  staffer_live_server (PID 12580, port 8841) holds 6.5 GB. A clean single-sheet re-measure will be taken once both
  background jobs finish; no performance claim will be published from the contended run.
- [receipt] A_RECEIPT.md gained findings F4 (per-cycle split sheet names defeat report_insights.py:272's exact-name
  non-summable list) and F5 (W10 header_vocabulary covers the 20 data sheets, not About/Data Quality; tidy_lint covers all 22).
- [waiting] reader_check.py (PID 27880) and negative_control.py (child build_tidy_workbook PID 20168) both alive and
  progressing under disk contention: reader 125 s CPU / 100 MB read; writer 102 s CPU / 4,662 MB read / 241 MB written
  (past the W7 DB scan, now writing the pending workbook it will delete). 4.8 GB RAM free, so not paging.
- [step 7] WRITER NEGATIVE CONTROL PASSED. Corrupted source_id 1121420220265208294 (2021-2022, Navy Federal CU)
  analysis_amount 12.5 -> 13.5 in a COPY of the store. Writer exit 2, no xlsx produced, no .pending-* left,
  receipt ok=false sha256=null, and SIX independent checks fired: W1 W2 W3 W4 W5 W6 (all "246,812.93 vs 246,813.93").
  W7's 30 rows stayed green - correct, because the corruption moved analysis_amount and W7 recomputes reported amount
  and row counts from the source DB. Output in negative_control.txt. Corrupted copy deleted.
- [steps 1-8 COMPLETE 2026-09-15 02:5x] ROOT CAUSE FOUND AND FIXED: our sheets carried no <dimension> element, so openpyxl's
  read-only loader (ReadOnlyWorksheet._get_size -> WorkSheetParser.parse_dimensions, which iterparses to the END event of
  <sheetData> when no dimension exists) XML-parsed all 469,226 rows on EVERY load_workbook - profiled at 418.16s and
  18,652,063 element steps, paid per console request. New writer function pin_dimensions() injects a true
  <dimension ref="A1:..."/> into all 22 sheet parts after save. Measured on the FINAL file: load_workbook(read_only) 0.03s
  (was 418s); Contributions max_row/max_column 28961/56 taken straight from the dimension.
  A first injection attempt (23:53) used "\"" in a re.sub replacement -> invalid XML; the unit tests caught it
  (ExpatError, 6 errors) and it was replaced. 11/11 tests pass on the final writer source.
  FINAL MOCK: out\Credit Union Industry Spending Data (MOCK).xlsx, 33,308,280 B, 23:59,
  sha256 f7349527e8bc063eea07ca071b39ea861fdf75ae3c17c461c8ce7cdf988ca7f6, 22 sheets, 469,226 rows, 367.49s,
  97 writer check rows, 0 failing, 0 skipped. Receipt json beside it.
  Delta vs the 22:21 build (2c7fc5b4...): the <dimension> elements and the re-zip ONLY - identical sheet list, row counts,
  check rows, blank columns, absent tables, splits; +506 bytes.
  A_RECEIPT.md finalized: section 2 is an explicit per-check "which build was this measured on" table. lint (0 findings),
  reader_check (5/22 sheets, all assertions passed) and the negative control were measured on the 22:21 build / pre-fix
  writer and are flagged as needing re-run on the final file; the verifier is doing exactly that.
