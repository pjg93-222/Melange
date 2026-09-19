# Lane A receipt - tidy workbook writer, mock, lint, tests, reader proof

Scratchpad root `S` =
`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-excel-tableau-format-8ac097\aad4d8be-16e5-435f-9bdb-3eb4c731eb44\scratchpad\tidy`.
Everything below lives under `S\laneA\`. Nothing was written under `C:\Users\pgoff\Mentat`
or into `Mentat Complete Files`; no console port was touched; no git command was run.
Paul's running servers (PID 12580 `staffer_live_server.py` :8841, PID 20820 Mentat
console :8806) were identified by command line and left alone.

## 0. THE FINAL ARTIFACT

| | |
|---|---|
| file | `S\laneA\out\Credit Union Industry Spending Data (MOCK).xlsx` |
| written | 2026-09-14 23:59 |
| bytes | 33,308,280 |
| **sha256** | **`f7349527e8bc063eea07ca071b39ea861fdf75ae3c17c461c8ce7cdf988ca7f6`** |
| receipt | `S\laneA\out\Credit Union Industry Spending Data (MOCK).xlsx.receipt.json` (25,303 B) |
| contents | 22 worksheets, 469,226 data rows, writer exit 0, 97 writer check rows, 0 failing, 0 skipped |
| build time | 367.49 s |

An earlier build of the same data, sha256
`2c7fc5b4360178d917c796a1b935f45a2e6968ef7347cb1875994f38fc63e7c3` (33,307,774 B,
22:21), also exists in the run log. **Some evidence below was measured on that earlier
build**; section 2 says exactly which, and section 1 says exactly what differs.

## 1. What the 23:59 rebuild changed, and why

### The defect
`app/report_insights.worksheet_data` opens the workbook with
`openpyxl.load_workbook(read_only=True, data_only=True)` on **every** call - once per
console request. openpyxl's read-only loader constructs a `ReadOnlyWorksheet` per sheet,
whose `__init__` calls `_get_size()` -> `WorkSheetParser.parse_dimensions()`
(`openpyxl/worksheet/_read_only.py`:35,46 and `openpyxl/worksheet/_reader.py`:172):

```python
def parse_dimensions(self):
    it = iterparse(self.source)
    for _event, element in it:
        if element.tag == DIMENSION_TAG:  return dim.boundaries
        elif element.tag == DATA_TAG:     break          # <- END event of <sheetData>
        element.clear()
```

`iterparse` yields **end** events, so when a sheet part carries no `<dimension>` element
the `DATA_TAG` break is only reached after `</sheetData>` - i.e. after the parser has
walked every cell of the sheet. openpyxl's **write-only** writer emits no `<dimension>`,
so the 22:21 build had none, and every workbook open re-parsed all 469,226 rows.

Measured, uncontended, with `cProfile` on the 22:21 build:

```
ZipFile open + namelist   0.00s (74 entries)
read_manifest/strings/workbook/properties/custom/theme/stylesheet   0.00s each
read_worksheets         418.16s
   22 x ReadOnlyWorksheet.__init__ -> _get_size -> parse_dimensions   418.08s
   18,652,063 ElementTree iterator steps, 304s inside pyexpat Parse
```

That cost is paid per console request, which is why the reader sweep in section 6 was
taking 200-700 s **per sheet** while iterating the rows themselves took 0.0 s.

### The fix
`build_tidy_workbook.pin_dimensions()` (new) rewrites the saved archive once, inserting a
true `<dimension ref="A1:<lastcol><lastrow>"/>` after `</sheetPr>` in each of the 22
sheet parts, then `os.replace`s it into position. Sizes come from the writer's own row
counts, so no scan is needed.

Measured on the FINAL 23:59 file:

```
openpyxl.load_workbook(read_only=True, data_only=True)   0.03s      (was 418s)
book["Contributions"].max_row / .max_column              28961 / 56  (from the dimension)
```

### What else differs between the 22:21 build and the 23:59 build
**Nothing but the `<dimension>` elements and the resulting re-zip.** No cell value,
header, table definition, number format, `About` row or `Data Quality` row changed. The
two receipts agree on every field except `sha256` and `seconds`: same 22 sheets, same
per-sheet row counts, same 97 check rows all passing, same 19 blank columns, same 5
absent tables, same 3 split groups, same 3 oversize sheets. The file grew by 506 bytes
(33,307,774 -> 33,308,280).

### A failed intermediate build, caught by the tests
A first attempt at the injection (23:53, 451.07 s) used a regex replacement string
containing `\"`, which is not an escape in `re.sub`, so it emitted
`ref=\"A1:B39\"` and produced **invalid XML**. `test_tidy_workbook` failed with
`ExpatError: not well-formed (invalid token): line 1, column 173` on 6 tests and that
build was replaced. The published 23:59 file is from the corrected function
(`lambda match: match.group(1) + element`), and 11/11 tests pass against it.

## 2. Which check ran on which build - read this before quoting any number

| check | ran against | verdict | re-run needed on the final file? |
|---|---|---|---|
| Writer checks W1-W11 (97 rows) | **FINAL 23:59 build** (`f7349527...`) - they are in its own receipt | 97 rows, **0 failing, 0 skipped** | no |
| `openpyxl.load_workbook` timing 0.03 s, dimension-derived size | **FINAL 23:59 build** | pass | no |
| `test_tidy_workbook` 11/11 | **FINAL writer source** (`build_tidy_workbook.py` sha `7afee68c...`), i.e. the code that produced the 23:59 file | OK | no |
| `tidy_lint.py` on the mock | **22:21 build** (`2c7fc5b4...`) | 0 findings | **yes** - the 23:59 file differs by the `<dimension>` elements only, but the lint has not been run on it |
| `tidy_lint.py --expect fail` on the published July Overview | the Overview itself, independent of our builds | 89 findings, control satisfied | no |
| `reader_check.py` (live `report_insights`) | **22:21 build**, 5 of 22 sheets before it was stopped | 5/5 sheets passed every assertion | **yes** - and it is now cheap to do, because of the fix in section 1 |
| `contribution_data._workbook_source` lineage literal | **22:21 build** | returned the correct DB sha256 | **yes** (expected identical; the `About` sheet is byte-identical apart from the dimension element) |
| Writer negative control | writer source as of 23:14 (**before** `pin_dimensions`), against a corrupted copy of the staging store | exit 2, nothing published, 6 checks fired | no - it exercises the refusal path, which the dimension change does not touch |

Nothing in this receipt claims a lint or reader result for the 23:59 file. The independent
verifier now re-running lint / reader_check / negative control on the final mock is the
right way to close the three "yes" rows above.

## 3. What was built

| file | bytes | lines | sha256 |
|---|---|---|---|
| `S\laneA\build_tidy_workbook.py` | 50,681 | 1,076 | `7afee68cc4577e2687165735dd2753971e3e053235358686ee61455a3f8caf75` |
| `S\laneA\payload_to_stage.py` | 42,248 | 818 | `46f73f765dbac0c249d18e7662bb8746b2f4ebb88b06c633cc568d39f4123a1e` |
| `S\laneA\tidy_lint.py` | 12,215 | 250 | `95af617498f03b04dc46ae8f9aaf44dd5135a4fe56c45618db13f7567a3e883a` |
| `S\laneA\test_tidy_workbook.py` | 16,864 | 313 | `6ffb54325dbc2d5e92c46f06e4d812cdb20a38d8f0851bde3a7919c1a135f64f` |
| `S\laneA\reader_check.py` | 7,572 | 163 | `5ab6c55032778e43bdb0ab55e46c05c09d6af2adf496a95e48f7fccdde760129` |
| `S\laneA\negative_control.py` | 3,479 | 78 | `102a3087e2e4c42d5fde77fc7beddff39d674b821de9a37ad2e07d5d1778ffd9` |
| `S\laneA\inspect_cache.py` (recon) | 4,283 | - | `d0dc267aa2fff0f39476a1b86cbdd0821e30276988b341de7007cc7708d33c54` |
| `S\laneA\inspect_shapes.py` (recon) | 1,523 | - | `1163819ac93ea9fe455bac38068ba293f564c0f2bad2f7ac69489df1731ddbfa` |

Other artifacts: `S\laneA\stage\tidy-cu.sqlite` (91,414,528 B, sha256
`cdbf11baa58fb6f0cf79b1f54c180aff2cdefbb9eced510437682281e2e9ff17`),
`S\laneA\laneA_overview_lint.txt`, `S\laneA\reader_check.stdout.txt`,
`S\laneA\negative_control.txt`, and
`S\laneA\out\NEGATIVE CONTROL (should not exist).xlsx.receipt.json` - the receipt of a
build that was correctly refused; there is deliberately no `.xlsx` beside it.

Future repo paths: `build_tidy_workbook.py` -> `mentat/tools/build_tidy_workbook.py`;
`test_tidy_workbook.py` -> `mentat/tests/test_tidy_workbook.py`. `payload_to_stage.py` is
**mock-only** and is replaced in production by Lane B's `R/tidy_stage.R`.

## 4. Exact commands to reproduce

Run from `S\laneA`.

```
python payload_to_stage.py
  # -> stage\tidy-cu.sqlite  (8 m 36 s; streams the 225 MB payload once per array)

python build_tidy_workbook.py ^
  --staging "stage/tidy-cu.sqlite" ^
  --out "out/Credit Union Industry Spending Data (MOCK).xlsx" ^
  --database "C:\Users\pgoff\Mentat\mentat\.cache\repair-20260908-databases\credit_union.db" ^
  --database-sha256 f9e956354525acb069cae220eb8d1538c479eea1bf23df1b3154adee8f416686 ^
  --payload "C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union\industry_data-f9e956354525acb0.json" ^
  --overview "C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union\stage-all_cycles\Credit Union Industry Spending Overview.xlsx" ^
  --overview-receipt "C:\Users\pgoff\Mentat\mentat\.cache\industry-report\credit_union\workbook_manifest_all_cycles.json"
  # -> the mock + its .receipt.json  (367 s)

python -m unittest test_tidy_workbook -v
python tidy_lint.py "out/Credit Union Industry Spending Data (MOCK).xlsx"
python tidy_lint.py "C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files\Credit Union Industry Spending Overview.xlsx" --expect fail
python reader_check.py
python negative_control.py
```

`--overview-receipt` is `workbook_manifest_all_cycles.json`, not a file named "finalizer
receipt": the Overview's Excel-computed `cycle_totals` live at
`formula_receipt.cycle_totals` inside that manifest.
`stage-all_cycles\finalizer_data.json` carries `expected_cycle_totals` (the R-side
expectation), **not** the Excel-computed totals, so it is not an independent source for
W6. W6 therefore ran live rather than being skipped.

## 5. The mock, sheet by sheet (FINAL 23:59 receipt)

22 worksheets, 469,226 data rows.

| sheet | rows | | sheet | rows |
|---|---:|---|---|---:|
| About | 38 | | Beneficiary Bridge | 5,044 |
| Contributions | 28,960 | | Transfer Paths 2021-2022 | 68,039 |
| Giving Facts | 374 | | Transfer Paths 2023-2024 | 123,789 |
| Recipient Facts | 708 | | Transfer Paths 2025-2026 | 63,379 |
| Contributor Facts | 3,922 | | Allocation Estimates 2021-2022 | 26,490 |
| Location Facts | 2,223 | | Allocation Estimates 2023-2024 | 32,150 |
| Committees | 358 | | Allocation Estimates 2025-2026 | 11,499 |
| Committee Sponsors | 205 | | Allocation Coverage | 170 |
| Candidates | 2,836 | | Source Freshness | 15 |
| Downstream Activity 2021-2022 | 35,239 | | Data Quality | 110 |
| Downstream Activity 2023-2024 | 38,523 | | | |
| Downstream Activity 2025-2026 | 25,155 | | | |

Split groups (3 tables x 3 cycles): Downstream Activity, Transfer Paths, Allocation
Estimates. Oversize sheets (still above the console's 50,000-row cap after the split):
`Transfer Paths 2021-2022`, `Transfer Paths 2023-2024`, `Transfer Paths 2025-2026` - see
finding F1.

### Absent tables (skipped and listed in `About`)
`funding_cohorts`, `classification_review (empty)`, `state_destinations`,
`recipient_locations`, `accounting_basis`.

### Data Quality sheet: 110 rows, 0 failing
13 rows carried from the export's own guards (`source = r_guard`) plus 97 written by the
writer (`source = writer`).

| check | source | rows | failed | skipped |
|---|---|---:|---:|---:|
| W1 `giving_facts_vs_contributions` | writer | 3 | 0 | 0 |
| W2 `recipient_facts_vs_contributions` | writer | 3 | 0 | 0 |
| W3 `contributor_facts_vs_contributions` | writer | 3 | 0 | 0 |
| W4 `location_facts_vs_contributions` | writer | 3 | 0 | 0 |
| W5 `expected_cycle_totals` | writer | 3 | 0 | 0 |
| W6 `overview_cycle_totals` | writer | 3 | 0 | 0 |
| W7 `database_amount_and_rows` | writer | 30 | 0 | 0 |
| W8 `unique_keys` | writer | 14 | 0 | 0 |
| W9 `no_multivalue_cells` | writer | 14 | 0 | 0 |
| W10 `header_vocabulary` | writer | 20 | 0 | 0 |
| W11 `lineage_literal` | writer | 1 | 0 | 0 |
| `roster_coverage`, `category_agreement`, `allocation_conservation`, `direction_integrity`, `date_sanity:downstream_activity`, `date_sanity:downstream_last_activity`, `cell_coverage`, `collection_completeness`, `zero_provenance`, `transfer_source_2022/2024/2026`, `category_population` | r_guard | 13 | 0 at fail severity | - |

Nothing was skipped. Sample rows:

```
expected_cycle_totals  2021-2022: Contributions analysis 246,812.93 vs expected 246,812.93
expected_cycle_totals  2023-2024: Contributions analysis 563,762.16 vs expected 563,762.16
expected_cycle_totals  2025-2026: Contributions analysis 242,809.53 vs expected 242,809.53
overview_cycle_totals  2021-2022: Contributions analysis 246,812.93 vs Overview 246,812.93
overview_cycle_totals  2023-2024: Contributions analysis 563,762.16 vs Overview 563,762.16
overview_cycle_totals  2025-2026: Contributions analysis 242,809.53 vs Overview 242,809.53
database_amount_and_rows 2021-2022 Alliant Credit Union:        workbook 1,559.20 / 91 rows    vs source DB 1,559.20 / 91 rows
database_amount_and_rows 2021-2022 America First Credit Union:  workbook 7,125.50 / 65 rows    vs source DB 7,125.50 / 65 rows
database_amount_and_rows 2021-2022 Boeing Employees Credit Union: workbook 41,610.20 / 1,383 rows vs source DB 41,610.20 / 1,383 rows
   ... 30 cycle x company rows, every one equal to the cent and to the row.
```

W7 is a full independent recomputation over the pinned 382,787,584-byte
`credit_union.db`, mirroring `tools/report_source_guard.source_facts` (`contributions`
and `corporate_giving`, `WHERE industry = ?`, `cycle_of(date) = year + year % 2`) plus
the acceptance filter that defines the workbook universe, mapping canonical company names
through the DB's own `company_display_names`. `--database-sha256` was verified against
the file before the query ran.

One r_guard row (`category_population`, severity `warn`) is carried through with
`Passed = FALSE`. That is correct: the writer blocks only on severity `fail`, and a
failing warn row must remain visible in the published sheet.

## 6. Live console-reader proof (`reader_check.py`)

**Measured on the 22:21 build, 5 of 22 sheets.** The sweep was stopped deliberately once
the per-sheet cost was traced to the missing `<dimension>` (section 1); finishing it
would have taken ~3 hours, and the fix makes a full re-run cheap. Output:
`S\laneA\reader_check.stdout.txt`.

```
workbook: ...\out\Credit Union Industry Spending Data (MOCK).xlsx
bytes: 33,307,774
sha256 (reader): 2c7fc5b4360178d917c796a1b935f45a2e6968ef7347cb1875994f38fc63e7c3
sheets: 22

sheet                            hdr     rows  cols  safe_to_sum grain                     note/status
About                              1       38     2  True        worksheet row             ok in 212s
Contributions                      1   28,960    56  True        FEC source observation    ok in 344s
Giving Facts                       1      374    10  True        worksheet row             ok in 460s
Recipient Facts                    1      708    29  True        worksheet row             ok in 490s
Contributor Facts                  1    3,922    16  True        worksheet row             ok in 716s
```

Every assertion passed on all five sheets (the harness appends to a FAILURES list and
prints "ok" per sheet only when that sheet added nothing to it):

* `header_row == 1` on every sheet - the reader's `header_row()` heuristic picks row 1,
  with no `header=` override;
* no `MAX_ROWS` refusal on any of the five;
* `Date` typed `date`; `Include in Analysis`, `Memo Leg`, `Conduit Leg`,
  `Superseded Amendment`, `Duplicate Filing Version`, `Duplicate Memo` typed `category`
  (real booleans, which `numeric()` maps to None, so they can never be charted as
  measures); `Giving`, `Amount`, `Analysis Amount` typed `number` with `unit == 'currency'`;
* `Distinct Contributors` carries `accounting.safe_to_sum = False`; `Giving` carries no
  non-summable override and `Giving Facts` is sheet-level `safe_to_sum = True`;
* `Contributions` carries the `Source ID` grain: `accounting.grain == 'FEC source
  observation'`, the note names Analysis Amount, and raw `Amount` is marked
  `safe_to_sum = False`;
* **zero auto-filtered rows** on every sheet: `accounting.row_role_column is None` and
  the note never contains "overlapping summary rows were excluded". The reader drops
  rows on sheets carrying `View` / `Scope` / `Section` headers; the tidy schema has none,
  so `row_count` equals the written row count exactly (28,960 / 374 / 708 / 3,922).

Separately, and also on the 22:21 build:

```
contribution_data._workbook_source(...) -> f9e956354525acb069cae220eb8d1538c479eea1bf23df1b3154adee8f416686   (0.0s)
matches the manifest's database_sha256: True
```

so the `About` sheet's single text run `Source DB SHA-256: <64 hex>` is found by the
console's own scanner on the first sheet part it reads.

**Not yet covered by a reader run:** the 17 remaining sheets, including every split sheet
(needed to confirm finding F4), `Beneficiary Bridge`, `Data Quality`, and the expected
`MAX_ROWS` refusal on the three `Transfer Paths` sheets.

## 7. Writer negative control on the real store

`python negative_control.py` -> `S\laneA\negative_control.txt`. A copy of the 91 MB
staging store had exactly one receipt corrupted:

```
corrupted source_id 1121420220265208294 (2021-2022, Navy Federal Credit Union):
analysis_amount 12.5 -> 13.5
```

Result:

```
writer exit code: 2
output workbook exists: False
pending files left behind: []
receipt ok=False sha256=None
failing Data Quality rows: 6
  giving_facts_vs_contributions      2021-2022: Giving Facts 246,812.93 vs Contributions analysis 246,813.93
  recipient_facts_vs_contributions   2021-2022: Recipient Facts 246,812.93 vs Contributions analysis 246,813.93
  contributor_facts_vs_contributions 2021-2022: Contributor Facts 246,812.93 vs ... (person rows) 246,813.93
  location_facts_vs_contributions    2021-2022: Location Facts 246,812.93 vs Contributions analysis 246,813.93
  expected_cycle_totals              2021-2022: Contributions analysis 246,813.93 vs expected 246,812.93
  overview_cycle_totals              2021-2022: Contributions analysis 246,813.93 vs Overview 246,812.93
W7 database_amount_and_rows rows still passing: 30
```

A one-dollar edit to one row out of 28,960 is caught by **six independent checks** and
nothing is published. W7's 30 rows correctly stay green: the corruption moved
`analysis_amount`, while W7 recomputes the reported `amount` and the row count from the
source database - the checks measure different quantities rather than restating each
other. The pristine store and the published mock were untouched; the corrupted copy was
deleted afterwards.

The refusal path was also exercised for real, unplanned, on the first full build: it
exited 2 on three genuine data problems (section 8, D2 and D3) before any of them had
been diagnosed. The guard is not only tested, it has already done its job.

## 8. Tableau lint

| workbook | findings | exit |
|---|---:|---|
| `Credit Union Industry Spending Data (MOCK).xlsx` **(22:21 build)** | **0** | 0 (PASS) |
| `Mentat Complete Files\Credit Union Industry Spending Overview.xlsx` (15,113,389 B, 33 sheets) | **89** | 0 under `--expect fail` (control satisfied) |

Overview breakdown: `table-ref` x50, `merged-cells` x26, `multivalue` x8, `sheet-name` x3
(the bare cycle-label sheets `2021-2022`, `2023-2024`, `2025-2026` - exactly the
`app/graph_data.py`:148,187 hazard), `aggregate-rows` x1 (`Master Overview` Total/Average
rows), `table-count` x1 (`Master Overview` carries three ListObjects). Full output:
`S\laneA\laneA_overview_lint.txt`.

Two bugs in the lint itself were found and fixed while proving it:

* `workbook.xml` carries `r:id` in the **officeDocument** relationships namespace, not
  the package one. With the wrong namespace every sheet resolved to no part, so tables
  and merged cells were invisible and the mock falsely reported "0 Excel Tables" on every
  sheet. (Caught because the mock's ZIP demonstrably contains 22 correct
  `xl/tables/tableN.xml` parts with correct refs and `tableColumns`.)
* `int` and `float` must collapse to one `number` kind: XLSX has a single numeric type
  and openpyxl reads `25.0` back as `int 25`, so an int/float mix in a money column is a
  serialisation artefact, not two types in one column. `bool` stays separate, which is
  what the console reader's `numeric()` distinguishes.

## 9. Unit tests

`python -m unittest test_tidy_workbook -v` -> **11 tests, OK**, against the final writer
source. The fixture store is built from the contract's own section-4 example rows, so a
drift between `STAGING_CONTRACT.md` and the writer fails here first.

Covered: sheet set and order; header row 1 with unique non-empty text headers; freeze
`A2`; no merged cells; exactly one ListObject per sheet whose ref starts at A1, ends at
the real last cell, and whose `tableColumns` equal the header row; booleans stored as
`bool`; dates stored as datetimes with format `yyyy-mm-dd`; `Source ID` /
`Contributor ZIP` / `Line Number` stored as `str`; NULL -> empty cell; `--split-rows 1`
forcing `Contributions 2021-2022` / `2023-2024` with table `tbl_contributions_2022` and
no bare cycle sheet name; W1-W4 passing on consistent data; all eleven W-checks present;
skipped checks stating their reason; the corrupted `giving_facts` row producing exit 2,
no output file, no leftover `.pending-*`, `ok: false` and a failing
`giving_facts_vs_contributions` row in the receipt; the `About` lineage literal; blank
columns detected both when absent and when all-NULL; absent tables listed in `About`;
receipt shape.

## 10. Deviations from the contract, with reasons

**D1 - year columns use number format `0`, not `#,##0`.** The contract fixes three
formats. `Cycle End Year` and `FEC Filing Cycle` are integer-typed by the contract, and
`#,##0` renders 2022 as `2,022`. The writer applies `0` to headers ending in `Year` or
`Cycle`. No value changes, and `report_insights.profile_columns` classifies these columns
as `category` either way because its `is_id` regex matches `year`/`cycle`.

**D2 - `Downstream Activity` key extended by `candidate`.** The contract's key
`(cycle_label, source_committee_id, candidate_id, activity_type, support_oppose,
transaction_type)` is **not unique on real Credit Union data**: 98,917 rows collapse to
98,719 distinct keys, in 92 colliding groups. Every colliding row has a **non-NULL**
`candidate_id` (0 rows have a NULL one); the rows differ only in the payee name - `USPS`,
`CANVA`, `TMA DIRECT`, `48 HOUR PRINT`, `SENATE CONSERVATIVES FUND`, several UNITE HERE
locals - i.e. FEC `pas2` vendor rows sharing one linked candidate id, with different
dates, row counts and amounts. Adding `candidate` yields exactly 98,917 distinct keys.
This changes only the uniqueness and sort key; no column was added, removed or renamed.
**Coordinator ruling wanted:** amend the contract's stated key, or accept that
`downstream_activity` has no unique key and drop W8 for that table.

**D3 - `Ownership Status` added to the `;` exemption list.** Its values are
`committee_map` prose, e.g. `Organization/committee; no individual ownership link in FEC
files` - a sentence, not a packed set. Without the exemption W9 fails on 378
`Recipient Facts` and 147 `Committees` rows and nothing publishes. The list is duplicated
verbatim in `tidy_lint.py` so the two agree. The writer ships with these prose
exemptions: Memo Text, Source URL, Representative Path, Transfer Records, Unresolved
Reasons, Detail, Inclusion Reason, Duplicate Reason, Company Match Reason, Traversal
Status, Accounting Note, Rule, Ownership Status. `Inclusion Reason` is on the list because
the exporter itself builds `paste0("Memo duplicate: ", duplicate_reason, "; retained
source ", duplicate_of_sub_id)` (`tools/export_crypto_spending_data.R` ~:470).
**Measured fact:** after those exemptions, `ownership_status` is the ONLY `;`-bearing
column left anywhere in the staging store - the tall design removes every other packed
multi-value.

**D4 - the receipt is written on failure too.** The contract says "remove the pending file
and exit 2" and "Writes `<out>.receipt.json`". The writer always writes the receipt, with
`ok: false` and `sha256: null` on a failure, so the refusal is auditable. The workbook
itself is still removed.

**D5 - a present-but-empty staging table is treated as absent.** `classification_review`
exists in this cache with 0 rows. An Excel ListObject needs at least one data row, so the
writer skips the sheet and lists the table in `About` as `classification_review (empty)`
rather than emitting a one-row phantom table.

**D6 - file length.** `build_tidy_workbook.py` is 1,076 lines, not "under ~700". Lines
70-362 (~292 lines) are the declarative column-header registry that contract section 2
requires to live in the script, and `pin_dimensions` + `sheet_parts` add ~50; executable
logic is ~700 lines.

**D7 - `report_source_guard.py` is in `tools/`, not `app/`.** The brief cited
`C:\Users\pgoff\Mentat\mentat\app\report_source_guard.py`; that file does not exist. The
live one is `C:\Users\pgoff\Mentat\mentat\tools\report_source_guard.py` (`source_facts`
:116-131, `cycle_of` :59-64). W7 mirrors the `tools/` copy.

**D8 - contract example label text differs from `R/report.R`.** The contract's section-4
example gives committee type `O` the label `Super PAC (independent expenditure-only)`;
`R/report.R`:1747-1780 defines `O = "Independent expenditure-only (Super PAC)"`. The shim
copies **`report.R`** verbatim, per the brief. The R constant is also named
`MENTAT_FEC_COMMITTEE_DESIGNATION_LABELS`, not the contract's
`MENTAT_FEC_DESIGNATION_LABELS`.

**D9 - the writer post-processes its own output.** `pin_dimensions` rewrites the saved
archive once before `os.replace`. The contract's "pending file then `os.replace`" rule is
preserved (the rewrite happens on the pending file, via its own `.dim-<pid>` temporary).
Rationale in section 1; without it the artifact is unusable in the console.

## 11. Findings for the coordinator

**F1 - `Transfer Paths` exceeds the console cap even after a per-cycle split.** 255,207
rows -> 68,039 / 123,789 / 63,379 per cycle. All three exceed
`report_insights.MAX_ROWS` (50,000), so `worksheet_data` refuses them outright - it
raises rather than truncating. The writer wrote them anyway (the contract says to split
by cycle and says nothing about a second level) and listed them in the receipt under
`oversize_sheets`. Same class of problem as Banking `Contributions`. Options: a secondary
split key, a row cap for audit tables (the Node Overview builder truncates non-complete
audit tables to 10,000, `crypto_workbook_builder.mjs`:2257), or accepting that Transfer
Paths is Tableau-only. `Allocation Estimates` per cycle (26,490 / 32,150 / 11,499) fits.

**F2 - the writer builds the whole workbook before it can refuse it.** Checks are computed
first (so the Data Quality sheet can carry them), the pending file is written, then a
failure deletes it. On this dataset a refusal still costs the full write. That is what the
contract prescribes; a fail-fast variant needs a contract change.

**F3 - the shim re-streams the 225 MB payload once per array (14 passes, 8 m 36 s).**
Irrelevant in production, where `R/tidy_stage.R` writes the store from frames in memory.

**F4 - the per-cycle split silently drops the console's sheet-level non-summable flag.**
`app/report_insights.py`:272 pins non-summability by EXACT sheet name:
`if sheet_name in ('Beneficiary Bridge', 'Beneficiary Summary', 'Transfer Paths',
'Funding Cohorts', 'Allocation Estimates')`. A split sheet is called
`Transfer Paths 2021-2022` / `Allocation Estimates 2023-2024`, which does not match, so
`accounting.safe_to_sum` returns **True** for sheets that repeat funding across
association paths - the exact thing that list exists to prevent. One-line console fix
(strip a trailing ` \d{4}-\d{4}` before the membership test), belonging in the same patch
set as the `server.py` suffix regex. **Predicted from the code, not yet observed**: the
reader sweep stopped before reaching a split sheet, so this is the first thing the
re-run should confirm. The inverse is fine and is confirmed: our sheet names are never a
bare cycle label, so `app/graph_data.py`:148,187
(`re.fullmatch(r'\d{4}[-–]\d{4}')`, header row 4) correctly ignores every sheet of the
Data book.

**F5 - W10 scope.** The writer's `header_vocabulary` rows cover the 20 data sheets, not
`About` and `Data Quality`, whose headers are compile-time constants (`ABOUT`,
`DATA_QUALITY`). The property was still proven for the 22:21 build: `tidy_lint.py`
applies its own header-uniqueness rule to all 22 sheets and returned 0 findings. A
one-line extension (pass those two registries into `structural_checks`) closes the gap in
the writer itself; it was deliberately not made after the mock was built, so the shipped
script and the shipped artifact match.

**F6 - the missing `<dimension>` is a general Mentat problem, not just ours.** Any
openpyxl `write_only=True` producer in this repo has the same defect, and the console pays
it on every request. `tools/split_telecom_workbook.py` uses the normal (non-write-only)
writer, which does emit a dimension, so it is unaffected; the July Overview is written by
the Node/Excel-COM chain and also carries dimensions. Worth a note in the proposal so the
next write-only writer does not reintroduce it.

## 12. Known limits of the MOCK (not of the writer)

* The Sept-8 cached payload's `raw_rows` is the pre-widening projection: 34 of the
  contract's 56 contribution columns.
* `funding_cohorts`, `state_destinations`, `recipient_locations` and `accounting_basis`
  have no key in this payload, so those four sheets do not exist in the mock. In
  production they come from `tools/enrich_downstream.py` and the R frames.
* `classification_review` is present but empty in this cache.
* `Committee Sponsors` is `candidate_committee_links` only; the leadership-PAC `mappings`
  frame is not in the payload (the design notes that `fec_build_committee_map` must also
  return it), so `link_source` is always `FEC ccl`.
* `Recipient Facts` sponsor columns are populated only where `sponsor_count = 1`; with
  205 sponsor links over 358 committee-cycles most rows are legitimately blank.
* `Beneficiary Bridge` flag headers are rebuilt from snake_case, so the token
  `Contribution / Other` becomes `Has Contribution Other Activity` - the slash is lost.
  The eight observed tokens are: Contribution / Other, Contribution to nonaffiliated
  committee, Coordinated party expenditure, In-kind contribution to registered filer,
  Independent expenditure - oppose, Independent expenditure - support, Oppose, Support.
  If the exact punctuation matters, the production store should carry the token
  vocabulary explicitly.

## 13. Columns blank in the mock, and why

`About` -> `Blank columns` lists 19. A header counts as blank when the store lacks the
column **or** the column is NULL in every row.

| column | why |
|---|---|
| Contributions / Transaction ID | not in the cached payload's `raw_rows` projection |
| Contributions / Back Reference Transaction ID | same |
| Contributions / Company Match Reason | same |
| Contributions / Matched Alias | same |
| Contributions / Funding Source Type | same (needs `entity_type`, dropped by the projection) |
| Contributions / Receipt Role | same |
| Contributions / Receipt Type | same |
| Contributions / Filing Form | same |
| Contributions / Line Number | same |
| Contributions / Memo Text | same |
| Contributions / Duplicate Of Source ID | column present in the store, NULL for every accepted CU row |
| Contributions / Duplicate Reason | same |
| Contributions / Recipient State | `mentat_add_destinations` output has no payload key here |
| Contributions / Represented State | same |
| Contributions / Source URL | `pdf_url` not in the projection |
| Committees / Party Affiliation | needs `fec_committee_master`, which has no payload key |
| Committees / Committee State | same |
| Downstream Activity / Transfer Records | no payload key in this cache |
| Beneficiary Bridge / Source Recipient Category | not carried on the bridge frame |

Everything else in the contract's registry is populated, including `Committee Type` /
`Committee Designation` and their codes on Contributions, Recipient Facts and Committees,
which the shim recovers by joining `committee_map` on `(cycle, committee_id)` and
labelling with the 16 + 6 maps copied verbatim from `R/report.R`:1747-1780.
