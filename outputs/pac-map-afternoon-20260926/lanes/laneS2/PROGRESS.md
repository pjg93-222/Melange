# Lane S2 - Data workbook split-sheet names (lane-s2-20260926)

Status: DONE, uncommitted (no git writes; the lead commits). Repo C:\Users\pgoff\Mentat,
branch codex/mentat-crypto, HEAD fadd2c751. Paul approved S1 = Yes.

## Where the split happens
- mentat/tools/build_tidy_workbook.py `plan_sheets()`: a table with more rows than
  `--split-rows` (default MENTAT_DATA_SPLIT_ROWS or 50,000) and a `cycle_label` column becomes
  one sheet per cycle. Old name `f"{sheet.name} {label}"`; `open_sheet()` refused names over 31.
- build_industry_report.ps1 only runs the writer and checks the receipt's worksheet count;
  it never reads sheet names. R (tidy_stage.R / export) writes the staging store only.

## Name map (old -> new; table ids unchanged, `tbl_<snake>_<year>`)
Rule: `<Sheet> <yyyy-yyyy>` -> `<split base> <election year>` (the cycle's even year).
Every registry sheet (all 23 can split; dynamic tables take whatever columns the store has):
| table | old part (chars) | new part (chars) |
|---|---|---|
| contributions | Contributions 2021-2022 (23) | Contributions 2022 (18) |
| giving_facts | Giving Facts 2021-2022 (22) | Giving Facts 2022 (17) |
| recipient_facts | Recipient Facts 2021-2022 (25) | Recipient Facts 2022 (20) |
| contributor_facts | Contributor Facts 2021-2022 (27) | Contributor Facts 2022 (22) |
| location_facts | Location Facts 2021-2022 (24) | Location Facts 2022 (19) |
| committees | Committees 2021-2022 (20) | Committees 2022 (15) |
| committee_sponsors | Committee Sponsors 2021-2022 (28) | Committee Sponsors 2022 (23) |
| candidates | Candidates 2021-2022 (20) | Candidates 2022 (15) |
| downstream_activity | Downstream Activity 2021-2022 (29) | Downstream Activity 2022 (24) |
| beneficiary_bridge | Beneficiary Bridge 2021-2022 (28) | Beneficiary Bridge 2022 (23) |
| beneficiary_activity | **Network Candidate Activity 2021-2022 (36, crashed)** | **Network Candidates 2022 (23)** |
| transfer_paths | Transfer Paths 2021-2022 (24) | Transfer Paths 2022 (19) |
| funding_cohorts | Funding Cohorts 2021-2022 (25) | Funding Cohorts 2022 (20) |
| allocation_estimates | Allocation Estimates 2021-2022 (30) | Allocation Estimates 2022 (25) |
| allocation_coverage | Allocation Coverage 2021-2022 (29) | Allocation Coverage 2022 (24) |
| source_freshness | Source Freshness 2021-2022 (26) | Source Freshness 2022 (21) |
| downstream_reach | Downstream Reach 2021-2022 (26) | Downstream Reach 2022 (21) |
| downstream_measurement_ledger | Downstream Measurement 2021-2022 (32, latent) | Downstream Measurement 2022 (27) |
| downstream_sources | Downstream Sources 2021-2022 (28) | Downstream Sources 2022 (23) |
| classification_review | Classification Review 2021-2022 (31, at limit) | Classification Review 2022 (26) |
| state_destinations | State Destinations 2021-2022 (28) | State Destinations 2022 (23) |
| recipient_locations | Recipient Locations 2021-2022 (29) | Recipient Locations 2022 (24) |
| accounting_basis | Accounting Basis 2021-2022 (26) | Accounting Basis 2022 (21) |
Unsplit names are unchanged. "Downstream Measurement" would also have broken 31, but its staged
table has no cycle_label today (enrich_downstream.STAGING_TABLES), so it never split.
Off-cycle labels (round 2): a label that is not an FEC two-year cycle keeps its own text, as
before (the exporter's sprintf writes `NA-NA` for a receipt with no date - verified in Rscript -
so `Contributions NA-NA` still publishes). A NULL label is refused at plan time; the old writer
also failed on it (planned the part, wrote 0 rows, raised).

## Files changed (sha256 original -> final; backups in laneS2\backups)
- mentat/tools/build_tidy_workbook.py 05b73666 -> 1d79f024: `Sheet.split_base`, `election_year`,
  `split_sheet_name`, `sheet_name_problems`, `EXCEL_FORBIDDEN_SHEET_CHARACTERS`; plan_sheets names
  parts with split_sheet_name and validates every name (31 chars, []:*?/\, apostrophes, History,
  case-insensitive duplicates) before a row is written; open_sheet also refuses forbidden
  characters; docstring records the S1 rule; WRITER_VERSION 1.0.0 -> 1.1.0.
- mentat/app/report_insights.py e44e55bc -> ea4abf65: `split_sheet_base()` (strips ` yyyy` or
  ` yyyy-yyyy`, maps `Network Candidates` back to `Network Candidate Activity`, leaves a bare
  cycle label alone); used by worksheet_accounting and untraced_sheet_notes.
- mentat/app/chart-studio-core.js 31a2aff1 -> d20469fb: `splitSheetBase()` (exported); the
  committee-activity caption / grand-total refusal now applies to split parts under both names.
- tests: test_tidy_workbook.py 079b4aa9 -> f6602e2f; test_report_insights.py 2a46083c -> f93a46a2;
  test_worksheet_not_traced.py 2ed04a19 -> 6862c936; app/tests/chart-studio-core.test.js
  221f88f4 -> 026dbcfe.
Every write: sha checked at cut and immediately before os.replace, atomic, line-wise, untouched
lines byte-identical, new lines take the majority terminator (LF for the pure-LF test file),
no non-ASCII bytes introduced. git diff shows only the intended hunks (no EOL churn).

## Pinned expectation changed on purpose
test_tidy_workbook.WriterTest.test_split_forces_per_cycle_sheets: before `Contributions 2021-2022`
/ `Contributions 2023-2024`; after `Contributions 2022` / `Contributions 2024`. Reason: Paul's S1
rename. All other assertions kept; added: old name absent, receipt split_sheets list pinned.

## Readers (census)
Updated: report_insights.worksheet_accounting + untraced_sheet_notes (were ` yyyy-yyyy` only);
chart-studio-core committeeActivitySheet (was exact-name only - split parts of Downstream
Activity / Beneficiary Bridge / Transfer Paths never got the caption or the total refusal).
Checked, no change needed: graph_data (reads Overview books only: graph_schema needs bare cycle
sheets, which a Data book has none of; has_transfer_paths, report_quality are Overview);
server.report_quality/inspect_report (Overview, header row 5); contribution_data/source_memo
(lineage literal, filename only); evidence_csv (no name parsing); chart-studio.js/charts.js
`preferred` default-sheet lists (exact names; same result for old and new split names);
saved views (restore chart sheets, not worksheet names); build_industry_report.ps1 (count only);
audit_collection_outputs.py / verify_repaired_reports.py (Overview, header 5); R (no reader).
Docs: no living doc (README.md, METHODOLOGY.md, app/README.md) describes the split name.
audits/mentat_tidy_workbook_20260914/STAGING_CONTRACT.md section 3 still says
`<Sheet> <cycle_label>`; it is a dated packet, left as written; the writer docstring records
the change.

## Tests
Before: tidy 17 OK, not-traced 5 OK, report_insights 18 OK, chart-studio-core 105/105.
After round 2: tidy 22 OK, not-traced 6 OK, report_insights 20 OK, raw_contribution_columns 7 OK,
transfer_paths_contract 13 OK. After round 1 (suites that do not import the writer):
report_receipts_streamed 9 OK, graph_not_traced 14 OK, graph_data 25 OK, chart-studio-core
106/106, all node unit tests 620/620, worksheet-guard browser test 3/3.
Negative controls: pristine modules -> all 9 new/changed test units fail (incl. the original
crash "Sheet name 'Network Candidate Activity 2021-2022' exceeds 31 characters."); pristine
chart-studio-core -> exactly the new JS test fails. End to end (e2e_all_sheets.py): 22 of 23
tables split (the fixture's candidates table has no cycle_label) into 61 parts, all valid; the
console reads all 61 by new name, and 55 renamed to the old spelling, with the right summability.
R testthat: not run - no R file changed and no R code reads these names.

## Open for the lead / Paul
1. Lane J2 may edit build_tidy_workbook.py: its sha is now 1d79f024; re-read before writing.
2. Network Candidate Activity is not in any sheet-level non-summable or committee-activity list
   (unsplit or split). Unchanged here; flag for J2 (money rules) if it should be.
3. A NULL cycle_label in a table that splits fails the build (before and after S2).
4. Published books keep the old names until the later rebuild lane runs; readers accept both.

## Brain drafts (for Paul to apply)
DECISIONS.md - D-0XX - Data workbook per-cycle sheets are named `<base> <election year>`
Date: 2026-09-26 / Status: ACTIVE - uncommitted on codex/mentat-crypto (lane S2), awaiting the
lead's commit and a workbook rebuild.
Decision: A Data-workbook sheet over MENTAT_DATA_SPLIT_ROWS splits into one sheet per cycle named
`<base> <election year>` (2021-2022 -> 2022); Network Candidate Activity splits under
`Network Candidates`; a non-cycle label keeps its own text; table ids stay `tbl_<snake>_<year>`.
Readers accept the new and the old `<name> <yyyy-yyyy>` spelling. The writer validates every
name before writing.
Context: Paul's review page, S1 = Yes. `Network Candidate Activity 2021-2022` (36 chars)
crashed every all-cycles build that split that sheet.
Reversal condition: Paul rules another spelling, or a consumer outside the console is found that
parses the `yyyy-yyyy` suffix and cannot be changed.
DEADENDS.md - DE-0XX - Naming a split sheet `<Sheet> <cycle_label>`: the ` yyyy-yyyy` suffix is 10
characters, so any base over 21 passes Excel's 31-character limit (Network Candidate Activity
2021-2022 = 36; Downstream Measurement 2021-2022 = 32). Would reconsider if: never; name parts
by election year.
