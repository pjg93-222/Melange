# Lane B progress

Started 2026-09-14. Scratchpad root S = `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-excel-tableau-format-8ac097\aad4d8be-16e5-435f-9bdb-3eb4c731eb44\scratchpad\tidy`

## Step log

- [x] Created `S\laneB\{patches,new,post,overlay}`.
- [x] Read `S\STAGING_CONTRACT.md` (343 lines; tables 2.1-2.13, writer behaviour 3, example rows 4).
- [x] Read plan `C:\Users\pgoff\.claude\plans\system-reminder-you-are-operating-greedy-truffle.md` (Writer architecture items 1,2,4,5,6 = Lane B).
- [x] Confirmed `C:\Users\pgoff\Mentat` on branch `codex/mentat-crypto`, working tree DIRTY. Anchoring all patches on WORKING FILES.
- [x] Read live files:
  - `tools/export_crypto_spending_data.R` (956 lines). args 1-41 (2..5 positional); module sourcing 43-50; raw_export projection 497-551; `mentat_add_destinations` 656; `workbook_raw_export` 657-659; guard list 722-774 (`mentat_run_export_guards(list(...), context = MENTAT_INDUSTRY)` closes 774-776); `payload <- list(` 780; `export_phase("payload_assembled", ...)` 887; `write_payload_json <- function` 889; `dir.create(dirname(output_path)...)` 940; `write_payload_json(payload, output_path)` 941.
  - `R/export_guards.R`: `mentat_guard_result` 37-46; `mentat_guard_detail_reconciliation` 471-515; `mentat_run_export_guards` 520-548.
  - `R/report.R`: label maps 1747-1773, `mentat_fec_code_label` 1775-1780; ZIP5 rule 1885-1886; `uniqueN`/`fec_min_text` 1968-1970.
  - `R/fec_beneficiary.R`: `fec_mode_text` 15-24 (modal, alphabetical tie-break - REUSED); `fec_join_unique` 26-32 (separator `"; "`); `candidate_master` 236-268; `candidate_committee_links` 270-304; `fec_build_committee_map` 522-629 (`mappings` 553-563, returns `result` 628); beneficiary bridge columns from 111-190 + 690-735.
  - `R/state_destinations.R`: `mentat_destination_fields` (6 fields, 2 are `; `-joined evidence).
  - `R/paths.R`: `atomic_replace` 170-200 (backup/rename/restore).
  - `R/schema.R` 1203-1209, `R/ingest.R` 1363-1369: `dbWithTransaction` + `dbAppendTable`.
  - `tools/enrich_downstream.py` (142 lines): `enrich()` 11-102, `main()` 105-142.
  - `tools/build_industry_report.ps1` (925 lines): params 11-34; `Write-AtomicText` 221-225; `Assert-WorkbookPackage` 227+; `$sourceGuard` 335; `$stageDirectory` 362; `$dataInputPaths` 380-406; cache-hit 412-427; Rscript 433-434; enrich 436; `Move-Item $pendingData` 452; manifest 457-466; `$stageWorkbook` 572; `$workbookFingerprintInputs` 586-593; lock 625-688; cache-hit workbook 691-727; node 795; finalizer receipt captured to `$formulaReceiptObject` 816-820 (STDOUT JSON, NOT a file); gates 821-823; workbook manifest 830-837; `sourceGuard check` 853-854; Overview publish 859-860; `sourceGuard accept` 862; result object 895-925.
  - `tools/finalize_crypto_excel.ps1:741` - the finalizer receipt object carries `cycle_totals` (and `expected_worksheet_count`). It is emitted on STDOUT; there is no receipt FILE today. DEVIATION recorded: P5 writes `$formulaReceiptObject` to `<stage>\formula_receipt.json` via the existing `Write-AtomicText` and passes THAT path to `--overview-receipt`.
  - `app/server.py` 1377-1400 (`published_reports`, industry regex 1396), `report_catalog` 1406+.
  - `app/contribution_data.py` `_workbook_source` 152-167, `_sources` 174-220 (glob 182, item 186-187), `_provenance` 230-237.
  - `app/report_insights.py`: `MAX_ROWS` 18; `header_row` 66-73 (max distinct text cells, earliest row wins ties); `cell_value` 204-211 (datetime -> isoformat); `numeric` 214-228 (returns None for bool); `profile_columns` 231-241 (`is_id` regex, type rule); `worksheet_accounting` 244-281 (summable regexes 277-280).
  - tests: `test_report_insights.py` (240 lines), `test_report_directory_console.py` (125), `test_contribution_data.py` (228), `Test-MentatWorkbookBuilderGuards.ps1` (80), `test_spending_detail_frames.R` (Rscript pattern).
  - `tests/test_downstream_enrichment.py` EXISTS.
- [ ] Draft P1 R/tidy_stage.R

## Session 2 (21:51 EDT resume)

- [x] Built `S\laneB\rtest\` (scratchpad-only R test root): read-only copies of live `R/paths.R`, `R/ingest.R`, `R/report.R`, `R/fec_beneficiary.R`, `R/export_guards.R` + the P1 post-image `R/tidy_stage.R` + `tests/test_tidy_stage.R`. Sourced whole files (no extraction needed: none of them touch the DB or the network at load time - same list `tests/test_spending_detail_frames.R` already uses, plus `ingest.R` for `trim_text` and the module under test).
- [x] P1 runtime fixes found by the test:
  1. `trim_text` lives in `R/ingest.R:425`, not report.R - added `ingest.R` to the test's source list (the exporter already sources it, so the module needs no change).
  2. `data.table(key = ..., value = ...)`: `key` is a RESERVED argument of `data.table()`, so the metadata frame's `key` column was swallowed as the table key -> `setkeyv` error. Fixed to `data.table::as.data.table(list(key = ..., value = ...))`.
- [x] `Rscript tests/test_tidy_stage.R` -> 51 checks, ALL PASS, exit 0. Run TWICE; `diff` of the two outputs is empty (deterministic), including the byte-identical-store check.
- [x] Recorded live `git hash-object` for all 10 modification targets (see B_RECEIPT.md).
- [ ] P2 exporter hook
- [x] P2 exporter hook drafted (6th positional arg, `tidy_stage.R` in the module list, frames built before the guard block, guard added as a NULL-able entry in the existing `list(...)`, store written between :887 and the `write_payload_json` call). `Rscript -e parse()` OK.
- [x] P3 `fec_beneficiary.R`: `data.table::setattr(result, "mentat_committee_mappings", mappings)` + `fec_committee_map_mappings()` accessor. Parse OK. Verified `jsonlite::toJSON` ignores the attribute (payload byte-identical) and `nrow`/`names` are unchanged.
- [x] P4 `enrich_downstream.py --staging`: seven tables under contract 2.12 names with explicit SQLite types + enrichment rows in `data_quality`; refuses a store that does not exist or lacks `contributions`. `py_compile` OK.
- [x] P5 `build_industry_report.ps1`: `$stagePath`, `$dataInputPaths` += `R\tidy_stage.R`, cache hit requires `stage_sha256`, 6th Rscript arg, `--staging`, PRAGMA integrity_check + receipt-count probe, Move-Item, manifest `stage_sha256`/`stage_bytes`, `$workbookFingerprintInputs` += the writer (Test-Path guarded), writer invoked after `sourceGuard check`, `Assert-WorkbookPackage` against the writer's OWN receipt, Data book published after the Overview and before `sourceGuard accept`, `data_workbook_sha256` in the workbook manifest, result-object fields. ParseFile -> 0 errors.
- [x] P6a/P6b console patches drafted. `py_compile` OK.
- [x] P7 tests drafted: `test_tidy_stage.R` (new), 2 cases in `test_report_insights.py`, 1 in `test_report_directory_console.py`, a new `CompanionDataWorkbookTests` class (4 cases) in `test_contribution_data.py`, 8 fragment + 4 ordering assertions in `Test-MentatWorkbookBuilderGuards.ps1`.
- [x] Python overlay `S\laneB\overlay\mentat\`: read-only copies of live `app/*.py`, `tools/*.py`, `tests/*.py` + fixtures those tests need (`config/`, `inputs/*.json|*.csv`, `R/*.R`, empty `inputs/fec_beneficiary` and `inputs/fec_committee_master`). NO node_modules, NO .cache. Post-images applied.
- [x] `python -m unittest tests.test_report_insights tests.test_report_directory_console tests.test_contribution_data tests.test_downstream_enrichment` -> **Ran 58 tests, OK**. No suite skipped. Baseline control: pristine tests against the patched app -> **Ran 51 tests, OK** (no regression). New tests alone -> 7/7 ok. NEGATIVE CONTROL: new tests against unpatched app -> FAILED (failures=1, errors=3) of 5.
- [x] `py_compile` OK on all 6 changed .py files. Python 3.12.14, openpyxl 3.1.5.
- [x] PowerShell: ParseFile on both .ps1 post-images -> 0 errors. `Test-MentatWorkbookBuilderGuards.ps1` (post-image) run against the post-image builder -> PASS; against the PRISTINE builder -> throws on the first missing fragment (`stage_sha256`). `build_industry_report.ps1` was NOT executed.
- [x] End-to-end R -> Python handoff: R wrote a real store, `enrich_downstream.stage()` appended the seven tables; all 20 tables coexist, R's 8 receipt rows survive, `data_quality` holds `r_guard`=2 + `enrichment`=2, re-run is idempotent, missing store refused.
- [x] 12 patches generated (`S\laneB\make_patches.sh`; live-vs-post `git diff --no-index --unified=3`, paths rewritten to repo-root relative, `#` header with target + live `git hash-object`).
- [x] `git -C C:\Users\pgoff\Mentat apply --check` -> **OK for all 12 individually AND all 12 together** (read-only).
- [x] Wrote `S\laneB\APPLY_ORDER.md` and `S\laneB\B_RECEIPT.md`.
- [x] LANE B COMPLETE.

## Addendum 2026-09-15

- [x] A1 amendment D2: added `MENTAT_TIDY_TABLE_KEYS` to P1 (keys now declared once, beside the specs); `downstream_activity` keyed on cycle_label/source_committee_id/candidate_id/**candidate**/activity_type/support_oppose/transaction_type and now CHECKED by the guard (it was absent from the key list before); a MISSING key column now FAILS instead of silently shortening the key.
- [x] A1 P7a: downstream fixture is now two rows for one candidate_id under two name spellings; 5 new checks incl. the negative control that the OLD six-column key finds exactly 1 false duplicate on the same frame.
- [x] `Rscript tests/test_tidy_stage.R` -> **56 PASS, 0 FAIL, exit 0**. Run twice; `diff` empty (IDENTICAL OUTPUT ACROSS TWO RUNS).
- [x] A2 P6c `app/report_insights.py` (live hash `31a2410092564b520254c43053b8e0610bc50bb7`, 337 -> 346 lines): strip a trailing ` \d{4}-\d{4}` before the sheet-level non-summable comparison, so per-cycle split sheets keep it. `or sheet_name` fallback keeps a BARE cycle label unstripped.
- [x] A2 P7b: new `test_per_cycle_split_sheets_keep_their_sheet_level_summability`. NEGATIVE CONTROL against pristine report_insights.py -> `AssertionError: True is not false` (F4 was real).
- [x] A3 P8: `S\laneA\build_tidy_workbook.py` copied BYTE-FOR-BYTE (md5 7b9d64dea1048b2140a49a8825c76621 on both sides) -> `mentat/tools/build_tidy_workbook.py`, 1076 lines. No logic touched.
- [x] A3 P8b: `S\laneA\test_tidy_workbook.py` -> `mentat/tests/test_tidy_workbook.py`, 313 lines. ONLY the import block changed (`import sys` + `sys.path.insert(0, .../"tools")`, per tests/test_downstream_enrichment.py:6-7); the stale "Future repo path" docstring line dropped. `diff` of everything below the import block is EMPTY.
- [x] `python -m unittest tests.test_tidy_workbook` -> **Ran 11 tests, OK** (the `FAIL giving_facts_vs_contributions` line is the writer's own negative control printing inside a passing test).
- [x] `py_compile` OK on report_insights.py, build_tidy_workbook.py, test_tidy_workbook.py, test_report_insights.py.
- [x] Full overlay run: `python -m unittest tests.test_report_insights tests.test_report_directory_console tests.test_contribution_data tests.test_downstream_enrichment tests.test_tidy_workbook` -> **Ran 70 tests, OK** (51 pre-existing + 8 Lane B + 11 Lane A).
- [x] `Test-MentatWorkbookBuilderGuards.ps1` re-run (P5/P7e unchanged) -> PASS.
- [x] Regenerated all patches. **15 patches**: `git apply --check` OK individually AND all fifteen together (read-only in C:\Users\pgoff\Mentat).
- [x] `APPLY_ORDER.md` updated: P8 now applies BEFORE P5 (absent-writer warning can never fire); backups list gains `app\report_insights.py`; rollback removes 4 new files; post-apply command adds `tests.test_tidy_workbook`; expected tails updated to 56 checks / 70 tests.
- [x] `B_RECEIPT.md` section "Addendum 2026-09-15" written; open question 5.1 updated to note the writer is always present with P8 applied.
- [x] NOT DONE (coordinator's file): `S\STAGING_CONTRACT.md:234` still states the six-column downstream key. P1/P7a implement the amended key; the contract text needs the coordinator's edit.
- [x] ADDENDUM COMPLETE.
