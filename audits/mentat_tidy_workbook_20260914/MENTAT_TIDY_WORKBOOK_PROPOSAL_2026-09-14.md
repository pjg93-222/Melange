# Mentat: a Tableau-shaped companion workbook per industry

Proposal, 2026-09-14/15. Prepared for Paul. Companion files in the same folder: `STAGING_CONTRACT.md`
(the column-level schema both lanes built against), `Credit Union Industry Spending Data (MOCK).xlsx`
(built from the real Credit Union export by the real draft writer), `patches/` (unapplied drafts with
`APPLY_ORDER.md`), `A_RECEIPT.md` / `B_RECEIPT.md` (build receipts), `VERIFY_A.md` / `VERIFY_B.md`
(independent verification).

## 1. Summary

- The Overview workbook stays exactly as it is. Its Node builder, the Excel-COM finalizer, the
  structured-reference formulas and the Master Overview grid are untouched.
- Each industry gains a second file, `<Industry> Industry Spending Data.xlsx`, written from the same
  export run and pinned to the same source database. It is static values only, one table per sheet,
  header on row 1, tall not wide, typed columns, no derived percentages, no merged cells, no total rows.
- The Chart Studio already opens the new file through its worksheet mode with no code change; three
  small console edits make it catalogue the file under its industry, prove the lineage, and keep the
  per-cycle split sheets non-summable. Tableau Desktop reads it directly, including a wildcard union for
  the split sheets.
- Every scraped FEC field survives: the `Contributions` sheet carries the full receipt line (source id,
  transaction ids, filing form, line number, memo text, committee type and designation, receipt role,
  conduit and memo flags, amendment and duplicate flags, source URL), and individual PACs, candidates and
  people are first-class rows in `Committees`, `Committee Sponsors`, `Candidates` and `Contributor Facts`.
- The generator change is additive: one new R module, one new Python writer, a short hook in the
  exporter, a `--staging` option in the enrichment step, and an orchestrator step. Nothing that exists
  today changes shape.

## 2. What is wrong with the current output (measured)

Measured on `Credit Union Industry Spending Overview.xlsx` (26 sheets, 15.1 MB, built 2026-07-28) and
the Sept-2026 builder that produced the Banking workbook.

| Problem | Where | Tableau rule it breaks |
|---|---|---|
| Three merged banner rows plus a blank spacer above every header; header on row 5 (row 6 on Master Overview, row 4 on the cycle sheets) | every sheet (`crypto_workbook_builder.mjs:618-649`) | headers in the first row |
| `Master Overview` is 83 columns (88 in the current builder): 14 five-column blocks pivot recipient channel and contributor tier into column groups; three cycle tables are stacked on one sheet with merged band rows, `Industry Total` and `Average` rows | `Master Overview` (`:1185-1460`) | tall not wide; no totals in the data; one table per sheet |
| Four contributor tiers pivoted into columns | `Company List` K-N, `Recipient List` U-X | tall not wide |
| Overlapping grains in one table (`View` = Industry and Company; `Scope` = Total Giving and its parts) | `Recipient List`, `Spending Overview`, `Beneficiary Summary` | one observation per row |
| Polymorphic rows: a `Section` column changes the meaning of every other column, half of them blank per section | three `Summary` sheets and ten company `View` sheets (`:2444-2560`) | one field per column |
| Dates stored as ISO text; `0` used as a null sentinel in text columns | `Downstream Activity` N/O, `Beneficiary Bridge` O/P; `Recipient List` H/K/L | one data type per column |
| `;`-joined multi-value cells | `Employee List` (Cities / States, ZIPs, Titles), `PAC & Candidate Map` (Candidate ID(s), Office(s)), `Beneficiary Summary` (Source Committees, Directions) | one value per cell |
| Derived measures shipped as data (`% of Industry`, ranks, `$ Change`, `Net Democratic %`) | most summary sheets | let the tool aggregate |
| About 347,600 formulas; values exist only as Excel's cached results | all sheets (finalizer) | static, machine-readable values |
| The console reader hard-codes the shape: it drops `View`/`Scope`/`Section` overlap rows and pins header row 5 | `app/report_insights.py:244-281`, `app/graph_data.py:70,122-131` | - |

The same lint that passes the mock with zero findings reports 89 findings on the published Overview
(50 table-ref, 26 merged-cells, 8 multi-value, 3 bare cycle-label sheet names, 1 aggregate-rows, 1
table-count).

The Studio's own field-granularity trouble (ZIP, Super PAC, employer) traces to the same cause: the
Overview is aggregated, and for Banking the payload exceeds the compact-mode threshold so the cycle
sheets are stripped to twelve columns before the console ever sees them.

## 3. The Data workbook

### 3.1 Rules (every sheet)

1. Header on row 1, data from row 2. No banner, subtitle or source rows, no spacer rows, no merged
   cells, no footer notes, no `Total` / `Average` / `Other (n folded)` rows.
2. One grain per sheet and one Excel Table (ListObject) spanning it, named `tbl_<sheet>`, frozen at row 2
   with its own autofilter. Sheet names are never a bare cycle label.
3. Tall: election cycle, contributor tier, recipient category and recipient party are row values.
4. One measure per column, named for the console's summability rules: `Amount` (reported) and
   `Analysis Amount` (0 when excluded) at receipt grain; `Giving`, `Gift Count`, `Distinct Contributors`,
   `Distinct Recipients` at aggregate grains. No `%`, rank or change columns.
5. One type per column: money as numbers, counts as integers, dates as real Excel dates, flags as real
   booleans, identifiers (source id, committee id, candidate id, ZIP, district, line number) as text.
6. No `;`-joined values. Many-to-many relationships become bridge sheets; set-valued attributes become
   `Has ...` boolean columns. Prose columns (`Ownership Status`, `Memo Text`, reasons, URLs) are exempt.
   No `0`-as-null; missing is blank.
7. Every row has a unique key and carries the join keys (`Election Cycle`, `Company`, `Committee ID`,
   `Candidate ID`, `Person Key`).
8. The workbook verifies itself at build time. A `Data Quality` sheet records checks whose expectations
   come from sources other than the sheets themselves: accepted-row amounts and row counts recomputed by
   SQL straight from `mentat.db`, the exporter's expected cycle totals, and the Overview's Excel-computed
   totals from the finalizer receipt. A failed check aborts the build before anything is published.
9. Provenance lives in an `About` sheet whose `Lineage` cell holds the literal
   `Source DB SHA-256: <hash>` that the console already scans for, plus the Overview's SHA-256, the payload
   SHA-256, versions, cycles, row counts per sheet and the list of columns that are blank for the industry.
10. The console's worksheet reader refuses sheets above 50,000 rows. Any sheet above the threshold
    (`MENTAT_DATA_SPLIT_ROWS`, default 50,000) is written as per-cycle sheets with an identical schema,
    which Tableau unions with a wildcard. For Credit Union that splits `Downstream Activity`,
    `Transfer Paths` and `Allocation Estimates`; `Transfer Paths` stays above the cap even per cycle (see
    open item 6). Banking `Contributions` (about 602,000 accepted rows) is a Tableau-only sheet; the Studio
    keeps its aggregate sheets and the SQLite-backed verified source for receipt-level questions.
11. Grain: `Contributions` holds the accepted rows in supported cycles, the same universe as the
    Overview's cycle sheets and the source guard, including rows excluded from analysis (memo, conduit and
    duplicate legs carry `Include in Analysis` = FALSE with the reason). Rejected and review matcher rows
    stay in the database and the cross-reference, as today.
12. Every sheet part carries an explicit `<dimension>` element. Without it openpyxl's read-only loader,
    which the console uses on every request, walks the whole sheet to find its size: 418 seconds per open
    on the 33 MB mock, 0.03 seconds with it. This is a general rule for any write-only workbook producer.

### 3.2 Sheets

| Sheet | One row per | Measures | Notes |
|---|---|---|---|
| About | key | - | provenance and row counts |
| Contributions | accepted FEC receipt line, all cycles | Amount, Analysis Amount | 56 columns; every raw_export field, real dates, ZIP5 plus raw ZIP, FEC labels for committee type and designation |
| Giving Facts | cycle x company x contributor tier x recipient category x recipient party | Giving, Gift Count, Distinct Contributors, Distinct Recipients | replaces Master Overview, Spending Overview, Company List |
| Recipient Facts | cycle x company x committee x contributor tier | Giving, Gift Count, Distinct Contributors, First / Last Gift Date | replaces Recipient List and Recipient Detail; committee attributes denormalised |
| Contributor Facts | cycle x company x person x recipient party | Giving, Gift Count | replaces Employee List; modal city / state / ZIP / employer / occupation, distinct-address count |
| Location Facts | cycle x company x state x city x ZIP | Giving, Gift Count, Distinct Contributors | replaces Contributor Detail |
| Committees | committee x cycle | - | replaces PAC & Candidate Map; single-valued attributes only |
| Committee Sponsors | committee x candidate x relationship | - | replaces the `Candidate ID(s)` cell; FEC candidate-committee links plus leadership-PAC roster mappings |
| Candidates | candidate | - | name, party, office, state, district, incumbency, principal committee |
| Downstream Activity | as today | as today | real dates; key includes the payee name (see ruling D2) |
| Beneficiary Bridge | company path row | as today | industry-view duplicates dropped; relationship and direction sets become `Has ...` flags |
| Transfer Paths, Funding Cohorts, Allocation Estimates, Allocation Coverage, Source Freshness, Classification Review, State Destinations, Recipient Locations, Accounting Basis | as today | as today | full rows (the Overview truncates audit tables to 10,000) |
| Data Quality | check | Passed | R guards, enrichment checks, writer reconciliation |

The complete column list, types, header vocabulary, derivations and example rows are in
`STAGING_CONTRACT.md`. Sheets dropped as derivable (they remain in the Overview): Master Overview,
Spending Overview, the cycle Summary sheets, the company View sheets, Company List, Employee List,
Recipient List, Beneficiary Summary, PAC & Candidate Map, Employee Rank Facts, Recipient Detail,
Contributor Detail.

### 3.3 Why a companion file rather than restructuring the Overview

Restructuring in place would rewrite the 2,700-line Node builder, the whole-column formulas in the
Excel-COM finalizer (`finalize_crypto_excel.ps1:274-499`), the worksheet-count gates in the orchestrator
(`build_industry_report.ps1:715,821`), the Graph reader's header-row pins (`graph_data.py:70,187`), the
cycle-totals guard (`contribution_workbook_guard.py:33-55`), the console's banner-literal lineage scan and
its `View`/`Scope`/`Section` logic, plus their tests. The companion file is additive and can be rolled
back by deleting two files.

## 4. Code changes (all paths under `C:\Users\pgoff\Mentat\mentat\`)

The pipeline today: `export_crypto_spending_data.R` builds the frames and writes a JSON payload;
`enrich_downstream.py` adds the transfer and allocation tables; `prepare_workbook_payload.py` projects the
raw rows down to 24 fields when the payload is large; `crypto_workbook_builder.mjs` writes the Overview;
`finalize_crypto_excel.ps1` injects formulas through Excel; `build_industry_report.ps1` orchestrates,
gates and publishes.

| Patch | File | Change | Lines |
|---|---|---|---|
| P1 | `R/tidy_stage.R` (new) | Builds every contract table with data.table from the frames the exporter already holds and writes them with `DBI::dbWriteTable` into `tidy-<hash>.sqlite` (pending file, then rename, one transaction). Adds `mentat_guard_tidy_reconciliation` (fails on a cycle-total mismatch or a duplicated row key), shaped like `mentat_guard_detail_reconciliation` (`R/export_guards.R:471-515`). | +1299 |
| P2 | `tools/export_crypto_spending_data.R` | Sources the module; registers the guard; between `export_phase("payload_assembled")` and `write_payload_json` builds the frames and writes the store to a path given as a new sixth positional argument. Without the argument the exporter behaves exactly as today and says it skipped staging. | +109 / -3 |
| P3 | `R/fec_beneficiary.R` | `fec_build_committee_map` also exposes its tall `mappings` frame (as an attribute, so the JSON payload is byte-identical) for `Committee Sponsors`. | +15 |
| P4 | `tools/enrich_downstream.py` | `--staging <sqlite>` inserts the seven Python-side tables and its quality checks. No-op without the option; refuses a store with no `contributions` table; idempotent. | +176 |
| P5 | `tools/build_industry_report.ps1` | Sixth Rscript argument; pending store integrity-checked (`PRAGMA integrity_check`) and moved like the payload; `stage_sha256` in the export manifest and required on cache hits; `enrich_downstream.py --staging`; the finalizer's stdout receipt persisted to `<stage>\formula_receipt.json`; the writer runs after `sourceGuard check` and before any publish, is gated by `Assert-WorkbookPackage` against its own receipt, and the Data book is published right after the Overview and before `sourceGuard accept`; `data_workbook_sha256` in the workbook manifest; writer and R module in the fingerprint inputs; result object extended. | +159 / -2 |
| P6a | `app/server.py` | Catalogue `... Industry Spending Data.xlsx` under its industry with `kind = data` (today it appears as an industry called "X Industry Spending Data" but is already chartable). | +11 / -2 |
| P6b | `app/contribution_data.py` | Attach the sibling Data book to the verified source's provenance with `data_workbook_sha256` and `data_lineage_matches`; the Data book can never become a verified dataset. | +22 |
| P6c | `app/report_insights.py` | The sheet-level non-summable list matches the base name of a per-cycle split sheet (`Transfer Paths 2021-2022` stays non-summable; a bare cycle label is left alone so `graph_data.py` is unaffected). Confirmed against the unpatched reader: the split sheet was summable. | +9 |
| P8 | `tools/build_tidy_workbook.py` (new) | The writer: openpyxl write-only streaming, one sheet per table, header row 1, tables, formats, booleans, real dates, per-cycle split, `About`, `Data Quality` with checks W1-W11, explicit `<dimension>` per sheet, receipt JSON, exit 2 on any failed check. | +1076 |
| P7 / P8b | tests | `tests/test_tidy_stage.R` (51 checks, two negative controls), `tests/test_tidy_workbook.py` (11 tests), additions to `tests/test_report_insights.py`, `tests/test_report_directory_console.py`, `tests/test_contribution_data.py`, `tests/Test-MentatWorkbookBuilderGuards.ps1` (publish-order assertions with a negative control). | +740 |

Why an R-side staging store instead of extending the JSON payload: the payload is already 1.4 GB for
Banking and is projected down to 24 raw fields before the Node builder runs. Writing the tidy frames
straight from R memory into SQLite keeps every field for every industry regardless of compact mode, and
lets the Python writer compute and check the aggregates with SQL.

### 4.1 Console impact

- Worksheet mode reads the Data book today: the header detector already prefers a unique text row 1,
  real date cells are typed `date`, boolean cells are typed `category` (never a measure), `Giving`,
  `Amount` and `Analysis Amount` are currency measures, `Distinct ...` columns are not summable, and the
  `Source ID` column switches `Contributions` to the FEC-observation grain with its usual note. All of
  this was measured with the console's own reader on the mock, not inferred.
- The `View` / `Scope` / `Section` overlap logic never fires: the Data book has no overlapping rows, so
  the row count the reader sees equals the row count written.
- Identifier columns (`Committee ID`, `Candidate ID`, `Source ID`, `Contributor ZIP`, `District`,
  `... Code`) are hidden by default in the Studio and revealed with "Show identifier fields"; `Person Key`
  and `Recipient Key` are visible dimensions.
- Follow-ups for a later call, not in this lane: a "% of total" quick table calculation in
  `chart-math.js` (the Data book ships no percentages by design); pointing the verified source's receipt
  reader (`contribution_data.py:388-412`) at the Data book's `Contributions` sheet; adding `keys?` to the
  identifier regex at `chart-math.js:183`.

## 5. Rollout

1. Apply the patches in the order given in `patches/APPLY_ORDER.md` (backups beside each file as
   `<file>.bak-20260914-tidy`). Every patch was generated against the live working tree, not HEAD, and
   `git apply --check` passes for all of them individually and together.
2. Run the offline tests listed in `APPLY_ORDER.md` (R staging contract, R parse checks, the four Python
   suites, the PowerShell guard test).
3. Smallest live dry run: set `$env:MENTAT_REPORT_DIRECTORY = <scratch>` (the scratch folder must
   already exist), then `build_industry_report.ps1 -Industry Crypto -DatabasePath <db> -OutputDirectory <scratch>`
   (both files land in a scratch folder; nothing is published; the first run after applying re-exports
   because the cache now demands a staging store).
   **`-OutputDirectory <scratch>` on its own does NOT work** - `Resolve-MentatReportDirectory`
   (`tools\report_directory.psm1`) throws `"OutputDirectory conflicts with the authoritative report
   directory"` whenever it differs from `config\report-directory.json`
   (`C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files`). `MENTAT_REPORT_DIRECTORY` is the
   module's own documented escape hatch and is what makes the run isolated. Do NOT "fix" the throw by
   dropping the flag: that publishes into `Mentat Complete Files`. `-DatabasePath` has no default and
   throws if omitted. **A scratch run still advances the accepted-source pointer**: `sourceGuard accept`
   (`build_industry_report.ps1:996`) writes
   `mentat\state\accepted-report-sources\<industry>\<cycles>\current.json`, which is not under the
   output directory - back that file up before the run and restore it afterwards.
   (Verified 2026-09-15 by reading the code; see `DRYRUN_RECEIPT.md`.)
4. First real publish: an industry whose export is current. The Data book lands beside the Overview;
   the console lists it under the industry; Tableau opens it directly.
5. Banking: rebuilt only after the receipt-evidence ruleset question from 2026-09-12 is settled; the
   Data path does not change that gate.

Rollback: delete the new files, restore the `.bak-20260914-tidy` copies, delete any published
`... Industry Spending Data.xlsx` and the `tidy-*.sqlite` stores in the cache. The Overview is never
modified by any of this.

## 6. Verification performed in this lane

**Mock.** `Credit Union Industry Spending Data (MOCK).xlsx`: 22 sheets, 469,226 data rows, 33.3 MB,
built in 367 s by the real draft writer from the current Credit Union export cache (payload of
2026-09-08; 28,960 accepted receipts). SHA-256 `f7349527e8bc063eea07ca071b39ea861fdf75ae3c17c461c8ce7cdf988ca7f6`.

**Writer checks, all on the final file:** 97 rows, 0 failing, 0 skipped. W1-W4: every fact sheet's
`Giving` equals the `Contributions` analysis sum per cycle. W5: equals the exporter's expected cycle
totals. W6: equals the Overview's Excel-computed cycle totals read from the workbook manifest's formula
receipt. W7: 30 cycle x company rows of reported amount and row count recomputed by SQL over the pinned
382 MB `credit_union.db`, every one equal to the cent and to the row. The three cycle totals are
$246,812.93, $563,762.16 and $242,809.53.

**Negative control.** One receipt in a copy of the staging store moved by +$1.00: the writer exits 2,
writes no workbook, leaves no pending file, and six independent checks fire (W1-W6). W7 correctly stays
green because it measures reported amounts and row counts, not the analysis amount, which shows the
checks are independent rather than restatements of each other. The refusal path also fired unplanned on
the first real build (three genuine data problems, now rulings D2 and D3).

**Tableau lint.** Zero findings on the mock; 89 on the published Overview under the same rules.

**Console reader.** `report_insights.worksheet_data` on the mock: header row 1 on every sheet checked,
no cap refusal, `Date` typed `date`, the six flag columns typed `category`, `Giving` / `Amount` /
`Analysis Amount` typed `number` with unit `currency`, `Distinct Contributors` not summable, `Giving`
summable, `Contributions` on the FEC-observation grain, zero auto-filtered rows.
`contribution_data._workbook_source` returns the database hash from the `About` sheet.

**Tests.** Writer unit tests 11/11. R staging contract 56 checks passing, run twice with identical
output, including negative controls for a corrupted fact table, a duplicated row key, and the old
six-column `Downstream Activity` key (which the fixture proves produces a false duplicate). Python suites
70 tests OK in a scratch overlay (51 pre-existing, 8 from the console patches, 11 from the writer); the
new tests fail against the unpatched app. PowerShell post-images parse with zero errors; the guard test
throws against the pristine builder. All fifteen patches pass `git apply --check` individually and
together against the live working tree. Two guard defects were found and fixed on the way: the R
duplicate-key guard had not been checking `downstream_activity` at all, and a key column missing from a
frame used to be silently dropped from the check instead of failing it.

**Independent verification.** Lane B's patch set: 10/10 checks PASS (hash anchoring, apply-check of all
patches together, no scratchpad leaks in shipped code, scope, R and Python re-runs, PowerShell parse,
contract conformance read from the R source, publish ordering, live tree untouched). Lane A's mock:
see `VERIFY_A.md` (verdict recorded in section 8).

**Live dry run on a scratch copy (2026-09-15, after Paul applied the patches).** The real chain could not
run on any production database because the uncommitted receipt-evidence gate refuses every industry
with an unresolved receipt row (on the hydrated 2026-09-10 databases: Credit Union 4 rows, Crypto 80).
On Paul's ruling a copy of the hydrated Credit Union database had those 4 rows removed ($3,012.57, so
nothing built from it is a valid artifact), and the chain ran by hand into a scratch stage: exporter
with the new sixth argument (269 s, 9 of 9 export guards including `tidy_reconciliation` on 67,165
in-scope rows), enrichment with `--staging` (3.9 s), and the writer (150 s): exit 0, 90 checks passed,
0 failed, 1 informational skip (no Overview, because `@oai/artifact-tool` is not resolvable outside the
orchestrator), 30 of 30 cycle x company rows matching the database to the cent, lint clean, console
reader clean, lineage hash equal to the scratch database. The first attempt had refused on two false
positives in the multi-value check (a Receipt Type value and the committee name `MADISON PAC; THE`);
Paul ruled the check into an include-list of categorical columns, which is now the rule in the writer,
the lint and the tests. The orchestrator step itself remains covered by its parse and guard tests only:
two of its assumptions were corrected on the way (`-OutputDirectory` conflicts with the authoritative
directory, so `MENTAT_REPORT_DIRECTORY` is the isolation lever, and `sourceGuard accept` advances the
accepted-source pointer even for a scratch run).

**Performance defect found and fixed.** The first build had no `<dimension>` element in its sheet parts;
the console's read-only loader then took 418 s per workbook open. The writer now pins the dimension;
the final file opens in 0.03 s. This is rule 12 above.

## 7. Rulings made in this lane, and open items for Paul

Rulings made (recorded in the contract): D1 year columns use number format `0`; D2 the
`Downstream Activity` key includes the payee name (`candidate`), because the exporter carries name
variants under one candidate id and the six-column key collided in 92 groups on real data; D3 prose
columns are exempt from the multi-value rule; D4 the receipt is written on failure too (`ok: false`);
D5 an empty staging table is treated as absent and listed in `About`.

Open for Paul:

1. Cache-hit builds re-run the writer every time (the safe default). Alternative: skip when the
   workbook manifest's `data_workbook_sha256` matches, at the cost of republishing an unverified file.
2. Sixth positional Rscript argument (as drafted) versus an environment variable `MENTAT_TIDY_STAGE`.
3. The Data book appears in the report picker under its industry with `kind = data` (two entries per
   industry). Alternative: hide it from the picker.
4. `Funding Cohorts` ships the contract's nine columns; the enrichment step also produces
   `funding_source_type` and `funding_direction`, which look chartable. Add them?
5. `Recipient Locations` keeps the first row per cycle x committee when the exporter's destination fields
   disagree. Confirm that grain.
6. `Transfer Paths` exceeds the console's 50,000-row cap even per cycle (68,039 / 123,789 / 63,379 for
   Credit Union). Options: accept it as Tableau-only, add a second split key, or cap it like the Overview's
   audit tables (10,000 rows).
7. The three console follow-ups in section 4.1.
8. `Beneficiary Bridge` flag headers are rebuilt from snake_case, so the token `Contribution / Other`
   becomes `Has Contribution Other Activity`. If the exact punctuation matters, the store should carry the
   token vocabulary explicitly.

## 8. Results appendix

### 8.1 Mock sheets and rows

| Sheet | Rows | Sheet | Rows |
|---|---:|---|---:|
| About | 38 | Beneficiary Bridge | 5,044 |
| Contributions | 28,960 | Transfer Paths 2021-2022 | 68,039 |
| Giving Facts | 374 | Transfer Paths 2023-2024 | 123,789 |
| Recipient Facts | 708 | Transfer Paths 2025-2026 | 63,379 |
| Contributor Facts | 3,922 | Allocation Estimates 2021-2022 | 26,490 |
| Location Facts | 2,223 | Allocation Estimates 2023-2024 | 32,150 |
| Committees | 358 | Allocation Estimates 2025-2026 | 11,499 |
| Committee Sponsors | 205 | Allocation Coverage | 170 |
| Candidates | 2,836 | Source Freshness | 15 |
| Downstream Activity 2021-2022 | 35,239 | Data Quality | 110 |
| Downstream Activity 2023-2024 | 38,523 | | |
| Downstream Activity 2025-2026 | 25,155 | | |

Absent in the mock because the cached payload has no key for them: `Funding Cohorts`,
`Classification Review` (present but empty), `State Destinations`, `Recipient Locations`,
`Accounting Basis`. In production they come from the enrichment step and the R frames.

### 8.2 Data Quality sheet (110 rows, 0 failing)

| Check | Source | Rows |
|---|---|---:|
| giving_facts_vs_contributions, recipient_facts_vs_contributions, contributor_facts_vs_contributions, location_facts_vs_contributions | writer | 3 each |
| expected_cycle_totals, overview_cycle_totals | writer | 3 each |
| database_amount_and_rows (cycle x company vs SQL over the source DB) | writer | 30 |
| unique_keys, no_multivalue_cells | writer | 14 each |
| header_vocabulary | writer | 20 |
| lineage_literal | writer | 1 |
| roster_coverage, category_agreement, allocation_conservation, direction_integrity, date_sanity (2), cell_coverage, collection_completeness, zero_provenance, transfer_source_2022/2024/2026, category_population | r_guard | 13 |

One carried R guard (`category_population`, severity warn) shows `Passed = FALSE`; the writer blocks only
on severity fail, and a failing warning must stay visible.

### 8.3 Columns blank in the mock (19), and why

The cached Credit Union payload predates the wide `raw_export` projection, so `Transaction ID`,
`Back Reference Transaction ID`, `Company Match Reason`, `Matched Alias`, `Funding Source Type`,
`Receipt Role`, `Receipt Type`, `Filing Form`, `Line Number`, `Memo Text`, `Source URL`,
`Recipient State` and `Represented State` are blank on `Contributions`; `Duplicate Of Source ID` and
`Duplicate Reason` are NULL for every accepted Credit Union row; `Committees` lacks `Party Affiliation`
and `Committee State` (no committee-master key in the payload); `Downstream Activity` lacks
`Transfer Records`; `Beneficiary Bridge` lacks `Source Recipient Category`. All nineteen are populated by
the production path, where the R module writes the store from the full frames. `About` lists them.

### 8.4 Independent verification of the mock

`VERIFY_A.md`: overall PASS, ten checks. A1 identity (sha256 and sheet order match the receipt);
A2 writer unit tests 11/11; A3 lint 0 findings on the final mock and 89 on the Overview; A4 structural
spot-checks (headers, freeze panes, sheet names) on the final file; A5 SQLite reconciliation:
`SUM(analysis_amount)` equals `SUM(giving)` on every fact table for every cycle, 28,960 receipts;
A6 console reader proof taken from the 22:21 build (the final file differs from it only by the
`<dimension>` elements, as A1 and A3 confirm on the final file); A7 negative control; A8 Tableau review
(no mixed types, no aggregate rows, no bare cycle sheet names); A9 no hard-coded scratchpad or session
paths in the writer; A10 receipt consistency. Two notes: the Lane A receipt's narrative sections still
quote the earlier build's hash in two places (the receipt JSON is authoritative), and `Transfer Paths`
exceeds the console cap even per cycle (open item 6).
