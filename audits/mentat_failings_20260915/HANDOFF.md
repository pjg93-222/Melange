# HANDOFF — MENTAT FAILINGS LANE (2026-09-15)

The ledger for sessions S0–S6. Coordination in this lane happens **only through
this file**. No session may rely on another session's memory or on anything said
in a chat transcript.

Read this file before any edit. Write your section before you stop.

---

## Lane facts (verified by S0, 2026-09-15)

| Fact | Value | How verified |
| --- | --- | --- |
| Repo | `C:\Users\pgoff\Mentat` | — |
| Branch | `codex/mentat-crypto` | `git rev-parse --abbrev-ref HEAD` |
| HEAD | `bd5dc8ea18a1641f3e08116f0d666fa98ba8750f` | `git rev-parse HEAD` |
| Ahead of `main` | 24 commits | `git rev-list --count main..HEAD` |
| Behind `main` | 465 commits | `git rev-list --count HEAD..main` |
| Working tree | 58 tracked-modified, 201 untracked | `git status --porcelain` |
| Console data root | `C:\Users\pgoff\AppData\Local\Mentat\console\f897a21e05a24d1e9246b0bf972145e0\runs\` | `server.py` arg default |
| Published workbooks | `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files` (8 industries) | directory listing |

**CORRECTION to the lane brief:** the brief states HEAD is `1b8499147`. It is
not; HEAD is `bd5dc8ea1`. Branch, ahead-count and dirty-file counts all match the
brief. Every line number in the brief is therefore suspect — **re-grep before
editing**, and record the live line number you found in your section.

**A COLLECTION WAS LIVE WHEN S0 STARTED; IT HAS SINCE ENDED** (19 of 30 tasks succeeded, 11 failed on HTTP_403; see PACKET.md Area A). **The port rules below still stand:** three of Paul's consoles are up (8802 pid 41244, 8806 pid 12500, 8808 pid 1612), and `server.py:1944` inherits `SO_REUSEADDR`, which on Windows lets a second bind on a listening port silently share its traffic (PACKET.md, DEFECT-SO-REUSEADDR). Run `20260915T152258-18548` (credit-unions, 10 worker
lanes) started 2026-09-15 15:22:58 under the data root above. Brain decision
D-029 permits the launcher to restart a stale console on the same port **only
when idle**, and its reversal condition is *"a restart is observed killing an
in-flight collection job."* Whenever any console is up: do not call
`POST /api/restart` on any port, do not bind 8802, do not kill a process you did
not start, and point any scratch console at a throwaway `--data-root`.

---

## Ledger protocol

1. Read `PACKET.md` (S0's diagnosis) before anything else. If it is missing and
   you are not S0, stop and tell Paul.
2. Before editing, confirm every file you will touch is **unowned**, or owned by
   a session whose Status is `committed by Paul`. If a file is owned by an
   in-progress session, **stop and tell Paul which session holds it**.
3. Contracts go in `contracts/*.json` as example payloads **before** any code
   changes. Both suites import the same file. See `contracts/README.md`. A prose
   description is never a contract (brain DE-021).
4. End each phase with a patch: `git diff -- <files you own>` written to
   `patches/S<n>_<slug>.patch`, with test output saved beside it in `receipts/`.
   Paul commits from the patch. **You never commit, merge, push, stash, or
   switch branches.**
5. Before stopping: append your section below, run `/ecc:save-session` with tag
   `mentat-failings-S<n>`, and draft one STATE.md line for the brain in your
   final message.
6. Present designs and WAIT for Paul's go before editing. Verify, never infer
   completion. Never poll-supervise a long job (DE-019). State what you left
   undone.

---

## Test commands (PROVEN by S0, 2026-09-15 — output in `receipts/S0_test_commands.md`)

There is **no single test runner**. Four independent runners. **Every command
below runs with the working directory `C:\Users\pgoff\Mentat\mentat`** — not the
repo root. This was verified, not assumed.

| Kind | Command | Proven on | Result |
| --- | --- | --- | --- |
| Python | `python -m unittest tests.test_validate_industry_coverage -v` | `test_validate_industry_coverage` | 7 tests, OK, exit 0 |
| Python (alt) | `python tests\test_validate_industry_coverage.py` | same | 7 tests, OK, exit 0 |
| Node | `node tests\test_chart_math.cjs` | `test_chart_math.cjs` | 20 pass / 0 fail, exit 0 |
| R | `& "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" tests\test_fec_api.R` | `test_fec_api.R` | `test_fec_api: PASS`, exit 0 |
| PowerShell | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests\Test-MentatWorkbookBuilderGuards.ps1` | same | PASS, exit 0 |

`Rscript` is **not on PATH**. The full path `C:/Program Files/R/R-4.6.0/bin/Rscript.exe`
is required (R 4.6.0). `pwsh` is **not installed**; use `powershell.exe`
(Windows PowerShell 5.1). Pester 3.4.0 is installed but the `Test-Mentat*.ps1`
files are plain scripts, not Pester suites — run them directly as above.

### Sweep commands

Python (slow, do not run casually):

```
cd C:\Users\pgoff\Mentat\mentat
python -m unittest discover -s tests -p "test_*.py" -v
```

Node:

```
cd C:\Users\pgoff\Mentat\mentat
Get-ChildItem tests -Filter "*.cjs" | ForEach-Object {
  & node $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "FAILED: $($_.Name)" }
}
```

R (slow):

```
cd C:\Users\pgoff\Mentat\mentat
Get-ChildItem tests -Filter "*.R" | ForEach-Object {
  & "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "FAILED: $($_.Name)" }
}
```

PowerShell — **full sweep run by S0: 5/5 PASS** (`Test-MentatFundingLabels`,
`Test-MentatLastGoodGuard`, `Test-MentatNodeHeapPlan`, `Test-MentatReportDirectory`,
`Test-MentatWorkbookBuilderGuards`):

```
cd C:\Users\pgoff\Mentat\mentat
Get-ChildItem tests -Filter "Test-*.ps1" | ForEach-Object {
  & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $_.FullName
  if ($LASTEXITCODE -ne 0) { throw "FAILED: $($_.Name)" }
}
```

The Node sweep includes browser tests and is long-running; S0 did not run it to
completion. The Python and R sweeps were not run.

### Test census (S0, non-recursive, `.bak-*` excluded)

`mentat\tests\` holds **137 files**, of which **116 are real tests** and 21 are
`.bak-*` backups. By extension: **57 `.py`, 31 `.cjs`, 23 `.R`, 5 `.ps1`.** The
only subdirectory is `__pycache__`. A separate `mentat\app\tests\` holds 14
files, 4 of them real `.js` tests.

### KNOWN-RED BASELINE — measured by S0 BEFORE this lane changed anything

Do not take credit or blame for these. Record any change to this list.

**Node sweep: 27 of 31 pass, 4 fail.**

| Failing test | Line | Failure |
| --- | --- | --- |
| `test_console_browser.cjs` | 188 | `Expected 'false' === 'true'` |
| `test_contribution_export_browser.cjs` | 102 | expected `/exportable viewport/`, got `Nothing to export.` |
| `test_cross_reference_view.cjs` | 75 | regex mismatch on "unresolved company attribution" |
| `test_studio_briefing_tray_browser.cjs` | 121, 155 | expected `2026-09-16.html/pptx`, got `2026-09-15...` |

The last one is a **date-boundary flake and a genuine test bug**: it fails
whenever a run straddles local midnight. It will pass or fail depending on the
hour, so treat it as unreliable rather than as a signal.

**PowerShell sweep: 5 of 5 pass.**

**Python and R sweeps were NOT run by S0** — they are slow and have no baseline.
The first session to run one records the result here.
### No cross-language fixture convention exists yet

`graph_fixture.py` is shared by three Python suites (`console_browser_fixture.py:11`,
`test_comparison_data.py:10`, `test_graph_data.py:18`). **No `.json` fixture
files exist in `mentat\tests\`, and no `.cjs` file imports any `.json`** — the
`.cjs` suites build their data inline. The convention in `contracts/README.md`
is therefore new to this repo, not a description of existing practice. The first
session to write a contract also establishes the loaders.

---

## Files-owned table

Ownership is claimed by updating this table AND your section's Status. A file
with two claimants is a **conflict**: stop and ask Paul, do not negotiate around
it in code.

| File | Owner | Status | Notes |
| --- | --- | --- | --- |
| `audits/mentat_failings_20260915/**` | S0 | receipts ready | S0 writes nothing outside this directory |
| `mentat/R/fec_api.R` | S1 | not started | retry, page checkpoints, API SELECT list |
| `mentat/R/collect.R` | S1 | not started | scrape checkpoints, resume, industry SQL |
| `mentat/R/fec_page.R` | S1 | not started | chromote browser fallback |
| `mentat/tools/api_company_cycle_fanout.py` | S1 | not started | key cap, lane cap, recovery pool |
| `mentat/tools/collect_api_lane.R` | S1 | not started | assigns `MENTAT_INDUSTRY` |
| `mentat/R/schema.R` | S2 | receipts ready | `corporate_giving`, migrations |
| `mentat/tools/export_raw_contribution_warehouse.py` | S2 | receipts ready | PRAGMA-driven export |
| `mentat/tools/export_crypto_spending_data.R` | S2 | receipts ready | workbook column list |
| `mentat/R/tidy_stage.R` | S2 | receipts ready | tidy contributions spec; content-clean at HEAD before S2, whole diff is S2's |
| `mentat/R/report.R` | S2 | receipts ready | two SELECT lines only (`spending_raw_report_rows` :2029, :2048); file otherwise unowned |
| `mentat/tools/build_tidy_workbook.py` | S2 | receipts ready | `CONTRIBUTIONS` registry: Street 1 / Street 2 on the companion Data workbook |
| `mentat/tools/backfill_contributor_street.py` | S2 | receipts ready | NEW: rebuild street from archived FEC response bodies, no network |
| `mentat/tests/test_raw_contribution_columns.py` | S2 | receipts ready | NEW: Python producers vs the contract; hosts `assert_block_adjacent` |
| `mentat/tests/test_raw_contribution_columns.R` | S2 | receipts ready | NEW: checks (a)-(h) across collect.R, fec_api.R, tidy_stage.R, report.R |
| `mentat/tests/test_raw_contribution_columns.cjs` | S2 | receipts ready | NEW: workbook sheet writer vs the contract |
| `mentat/tests/test_backfill_contributor_street.py` | S2 | receipts ready | NEW: backfill precedence, idempotence, un-migrated refusal |
| `mentat/tests/test_export_raw_contribution_warehouse.py` | S2 | receipts ready | EDITED: fixture SCHEMA in migrated shape + block assertions |
| `mentat/app/evidence_csv.py` | S3 | not started | `MAX_BYTES`, `MAX_COLUMNS` |
| `mentat/app/evidence-csv.js` | S3 | not started | client size mirror, status line |
| `mentat/tools/pac_evidence.py` | S3 | not started | collector, `ThreadPoolExecutor(3)` |
| `mentat/tools/fec_key_store.py` | S3 | not started | see DEFECT-KEYSTORE in PACKET.md |
| `mentat/app/contribution_data.py` | S4 | not started | `DIMENSIONS`, detail row cap |
| `mentat/app/chart-studio.js` | S4 | not started | API base, view routing |
| `mentat/app/chart-studio-core.js` | S4 | not started | `STUDIO_GROUP_LIMIT = 60` |
| `mentat/app/index.html` | S5 | not started | tabs, graph-mode select |
| `mentat/app/app.js` | S5 | not started | hash routing, localStorage |
| `mentat/app/graph.js` | S5 | not started | `clear()`, scope handoff |
| `mentat/app/graph_data.py` | S5 | not started | Downstream Activity worksheet |
| `mentat/R/fec_beneficiary.R` | S5 | not started | produces Downstream Activity |
| `mentat/app/server.py` | **CONTENDED** | **blocked** | see below |
| `mentat/tests/**` | shared | — | each session owns only the test files it adds |

**WORKING-TREE HAZARD (verified 2026-09-16):** `fec_api.R`, `collect.R`, `schema.R`, `report.R`, `tidy_stage.R`, `prepare_workbook_payload.py`, `build_industry_report.ps1` and `finalize_crypto_excel.ps1` are all **modified-uncommitted by other lanes** right now. `git diff -- <file>` on any of them captures foreign hunks. Every S1/S2 patch must be separated hunk by hunk and the receipt must say which hunks are the session's own — the same rule as `server.py`. `build_tidy_workbook.py` was tracked and clean at HEAD `bd5dc8ea1`; S2 has since modified it (one registry edit) and it is now ` M` — that hunk is S2's alone.

### CONTENDED: `mentat/app/server.py`

Four claims on one file. Paul rules before any of S3/S4/S5 edits it.

1. **S3** needs the evidence routes (`/api/evidence-csv`, `/api/evidence`,
   `/api/evidence-job`, `POST /api/evidence-collect`, `collect_evidence`).
2. **S4** needs the studio/contributions routes and the 512 KB gate.
3. **S5** may need routing if deep links become server-visible.
4. **Another lane already holds it.** The tidy-workbook lane has uncommitted
   edits to `server.py` in this same working tree (revert with
   `git apply -R P6a` per that lane's notes). Those edits are **not** part of
   this lane and must not be swept into a FAILINGS patch.

Consequence for patches: `git diff -- mentat/app/server.py` in this tree will
capture the other lane's uncommitted work as well as yours. Any session
patching `server.py` must diff **hunk by hunk** and state in its receipt which
hunks are its own. Do not hand Paul a patch you have not separated.

---

## S0 — Diagnosis (read-only)

**Status:** receipts ready

**Files owned:** `audits/mentat_failings_20260915/**` only. S0 made no edit
anywhere else in the tree.

**Patches:** none. S0 is read-only; its output is `PACKET.md`, this file,
`contracts/README.md`, and three receipts: `receipts/S0_test_commands.md`
(proven runner commands, sweep tallies, census), `receipts/S0_area_b_workbooks.md`
(all eight workbook layouts, payload record keys), and
`receipts/S0_area_c_measure.py` (the 5 MB / 20 MB parse harness).

**Glassbox:** `stage.started` emitted for `S0-diagnosis`
(`evt-20260916T0427333987508Z-580f6402f8`, run `mentat-failings-20260915`);
`stage.completed` `evt-20260916T0442463120603Z-0c40bd919b` emitted at close, after the packet was verified.

**Verification of this packet:** 24 of 24 sampled `file:line` citations
confirmed against the live tree by an independent verifier (0 off-by-N,
0 not-found), including both negative claims.

**Contract decisions:** established the fixture convention in
`contracts/README.md`, derived from brain DE-021. Wrote no contract files —
S0 has no API shape to define. Confirmed no cross-language fixture convention
previously existed in this repo.

**Open questions:** the three for Paul are stated at the end of `PACKET.md`.

**Handoff notes for later sessions:**
- Re-grep every line number. The brief's HEAD is wrong, so its line numbers are
  from a different commit.
- The working tree is dirty from other lanes. Your patch must contain only your
  files, and for `server.py` only your hunks.
- A collection is live. Respect D-029 and the port rules above.
- All four test runners work only from `C:\Users\pgoff\Mentat\mentat`.
- **Cross-console hazards S0 found (any session starting a scratch console):**
  `console_state_lock` is a file lock on `<data-root>\collection-control.lock`
  shared by every console on the same data root (`server.py:258-287`, 10 s
  deadline); the PAC-evidence store is keyed on `PROJECT`, not `--data-root`,
  so a throwaway data root does NOT isolate that tab (`server.py:867-869`); and
  a writable instance launched with any `FEC_API_KEY*` set rewrites the shared
  `fec-keys.dpapi` at startup (`server.py:520-522`). Launch scratch consoles by
  invoking `server.py --port <n> --data-root <throwaway>` directly, with no
  `FEC_API_KEY*` in the environment, and never through the launcher.
- **Area C did not reproduce a fetch failure.** Both fetch paths return 200 on a
  writable scratch instance and on all three of Paul''s consoles. S3 is gated on
  Paul stating the literal symptom text (PACKET.md Q2).
- **Lane-01 in the evidence run holds 228 `corporate_giving` rows with
  `contributor_employer` and `contributor_occupation` as empty strings on every
  row** (not NULL — `''`), while City/State/ZIP are 100% populated and every
  other populated lane is at 92-100% on employer/occupation. Cause not
  established. S2 explains it before trusting any employer-keyed join.
- **"10 lanes" means ten lane directories, three concurrent processes.** The
  run's `status.json` reports `effective_api_lanes: 3`, `fanout_max_parallel: 3`;
  `lane_count = min(len(keys), len(companies))` = 10 directories.
- **Street IS delivered by openFEC and IS retained in `api_page_checkpoints`
  payloads** — each stored page holds the full 81-key schedule_a record incl.
  `contributor_street_1` with real values (verified in lanes 02/03/04/09 of the
  evidence run). `collect.R:1266-1270` maps city/state/zip/employer/occupation
  and drops street. Checkpoints survive only for INCOMPLETE units
  (`fec_api.R:695-698` clears a decomposed unit's pages on completion; observed: every lane with stored rows holds 0 checkpoint rows), so street for already-stored rows is gone:
  S2 = two schema columns + two collect.R lines + a re-collect. No API change.
- **Four workbooks lack address columns because they lack contribution ROWS.**
  Banking, Telecom (12-col) and Credit Arms, P&C (18-col) cycle sheets are an
  aggregate "Formula Facts" layout (row-1 title `<cycle> <Industry> Formula Fa…`,
  `Gift Count` column, one Wells Fargo row = 44,721 gifts). Crypto, Community
  Banks, Credit Union, Fintech get the 35-column per-contribution layout with
  City/State/ZIP/Employer/Occupation at header row 4. Verified by dumping rows
  1-10 of every plain cycle sheet in all eight published workbooks.
- **Hint for Q1:** the report directory holds an Excel lock file
  `~$Credit Union Industry Spending Overview.xlsx` (2026-09-14 17:21) — the
  workbook most recently open on Paul's desk is one that HAS the five fields.
- **DEFECT-RESCUE-CAP fired during the evidence run:** `bulk_rescue_overflow.csv`
  (192 B, 2026-09-15 15:40:34) was written into the OneDrive report directory
  `C:\Users\pgoff\OneDrive\Desktop\Mentat Complete Files`, not the run directory.
- **The 403 quota hypothesis is refuted** (all 22 keys at 42-46 of 1000). Do not
  revive it without new evidence. The 403 body is discarded at `fec_api.R:521`;
  making it observable is S1''s first deliverable.

---

## S1 — Collection resilience (Area A)

**Status:** not started

**Files owned:** see table.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —

---

## S2 — Address fields and schema (Area B)

**Status:** `receipts ready`. S2 never commits. Everything described below is in
the live working tree and in two patch files; Paul applies and commits.

### Files owned or touched

Owned by S2 and changed:

- `mentat/R/schema.R` - `contributor_street_1` / `contributor_street_2` TEXT
  appended LAST in the `contributions` (:138), `bulk_candidates` (:283) and
  `corporate_giving` (:51) CREATE TABLEs; the same two entries appended at the
  END of `corporate_migrations` (:474); and a new `dbListFields` + `setdiff`
  ALTER loop for `contributions` and `bulk_candidates` (:486-497) placed AFTER
  the corporate migration loop, so a freshly created database and a migrated one
  end up with identical PRAGMA order.
- `mentat/tools/export_raw_contribution_warehouse.py` - new
  `CONTRACT_ADDRESS_BLOCK` (:95) and `contract_column_order()` (:106-129), used
  by `export_table()` and by the manifest builder; the partition manifest gains
  `manifest["tables"][t]["missing_contract_columns"]`. A later pass (T0 below)
  added `missing_columns_by_table()` / `warn_missing_contract_columns()` and
  wired the gap into the export receipt and stderr on BOTH receipt paths.
- `mentat/tools/export_crypto_spending_data.R` - the `raw_export` projection
  now reads employer, occupation, street_1, street_2, city, state, zipcode
  (52 columns), with a defensive NA fill of the two street columns before the
  copy so an un-migrated source cannot abort the export.
- `mentat/tools/crypto_workbook_builder.mjs` - `rawHeaders` 35 -> 37
  (Employer, Occupation, Street 1, Street 2, City, State, ZIP), the raw row
  projection reordered to match, and eight column-letter sites shifted
  (Z->AB, AB->AD, AI->AK, AD:AH->AF:AJ, AC->AE, plus widths).
- `mentat/tools/build_tidy_workbook.py` - the `CONTRIBUTIONS` registry gains
  `("street_1", "Street 1", "T")` and `("street_2", "Street 2", "T")` between
  the occupation and city entries, so the companion
  `<Industry> Industry Spending Data.xlsx` Contributions sheet carries the
  block. This file was clean at HEAD `bd5dc8ea1`; S2 is its only editor.
- `mentat/R/tidy_stage.R` - `MENTAT_TIDY_TABLE_SPECS$contributions` gains
  `street_1`, `street_2` after `occupation` (58 fields) and
  `mentat_tidy_contributions` projects them. **Correction to the WORKING-TREE
  HAZARD note above:** this file was CONTENT-CLEAN at HEAD `bd5dc8ea1` when S2
  snapshotted it, so its whole current diff is S2's. See "Working-tree
  provenance" below for the evidence.

New files written by S2:

- `mentat/tools/backfill_contributor_street.py` - recovers street for rows
  collected before the columns existed, from evidence Mentat already stores:
  `fec_response_archive` first, then `api_page_checkpoints`, first-seen wins per
  `sub_id`. Dry run is the default; `--apply` writes. It refuses an un-migrated
  table by name and tells the operator to run `init_schema()`. It opens no
  collector, no console and no network.
- `mentat/tests/test_raw_contribution_columns.py` - asserts the Python
  producers (raw warehouse header on fresh / migrated / un-migrated databases,
  the receipt's gap key, the formula-facts projection exclusion, and the
  tidy-workbook sheet registry) against the contract, plus a negative control
  that must fail. It also hosts `assert_block_adjacent`, which the sibling
  suites import.
- `mentat/tests/test_raw_contribution_columns.R` - checks (a)-(h): `collect.R`
  `contribution_columns()`, `collect.R` `corporate_columns`, `fec_api.R`
  `fec_api_corporate_records()`, the `tidy_stage.R` spec, the
  `export_crypto_spending_data.R` projection, a real `init_schema()` migration
  of an old database, the negative control, and the two `report.R` SELECTs.
- `mentat/tests/test_raw_contribution_columns.cjs` - asserts the workbook sheet
  writer (`rawHeaders` and the row projection) against the contract.
- `mentat/tests/test_backfill_contributor_street.py` - the backfill tool:
  precedence, first-seen-wins, conflict counting, idempotence, and the
  un-migrated refusal.
- `audits/mentat_failings_20260915/contracts/raw_contribution_columns.json` -
  the contract itself; all three suites import it.

Touched but NOT owned by S2:

- `mentat/R/report.R` - two lines only, the two SELECT lists in
  `spending_raw_report_rows()` (:2029 and :2048), which now carry
  `contributor_street_1, contributor_street_2`. The file is unowned in the table
  and carries other lanes' uncommitted hunks; S2's are those two lines.
- `mentat/tests/test_export_raw_contribution_warehouse.py` - an existing S2-area
  suite. Its fixture SCHEMA now carries the block in migrated shape, and it
  gained a full-block assertion and a `contract_column_order()` check.
- `mentat/R/collect.R` and `mentat/R/fec_api.R` - **S1's files.** S2 made the
  minimum change that lets street reach the database at collection time and put
  it in a SEPARATE patch so Paul can route it. In `collect.R`:
  `contribution_columns()`, the `corporate_columns` local inside
  `checkpoint_corporate_page`, and the browser-lane corporate projection (~:3203)
  were reordered to employer, occupation, street_1, street_2, city, state, zip;
  `flatten_fec_rows` maps `page_text("contributor_street_1")` /
  `("contributor_street_2")` and emits a one-per-call `cat()` canary when
  tabular rows carry neither street key. In `fec_api.R`, the
  `fec_api_corporate_records` `.()` projection carries the block.

### Patches

`patches/S2_street_columns.patch` (108,867 bytes, 14 files) carries `schema.R`,
`tidy_stage.R`, `report.R`, `export_raw_contribution_warehouse.py`,
`export_crypto_spending_data.R`, `crypto_workbook_builder.mjs`,
`build_tidy_workbook.py`, `test_export_raw_contribution_warehouse.py`, and the
six new files (the backfill tool, the four test files, the contract JSON).

`patches/S2_street_columns_collect.patch` (4,707 bytes, 2 files) carries
`collect.R` and `fec_api.R` on their own, because S1 owns them.

Both patches are diffs against pre-edit snapshots of each file taken before S2
touched it, NOT `git diff` against the index. They therefore apply on top of the
**working tree as it stood on 2026-09-16**, in which other lanes already hold
uncommitted hunks in six of the ten files S2 modified: `schema.R`, `collect.R`,
`fec_api.R`, `report.R`, `export_crypto_spending_data.R` and
`crypto_workbook_builder.mjs`. Those foreign hunks appear only as unchanged
context lines; no patch contains a `+` or `-` line that is not S2's.

Both patches were verified two independent ways, recorded in
`receipts/S2_patch_check.txt`:

1. `git -c core.autocrlf=false apply --check --reverse <patch>` against the live
   Mentat tree succeeds for both (exit 0). A patch reverse-applies only if its
   post-image is byte-for-byte the live tree, so this proves the patches are a
   faithful record of what is in the working tree. It is read-only; nothing was
   staged, committed or reverted in `C:\Users\pgoff\Mentat`.
2. The pre-edit tree was rebuilt from the snapshots in a scratch directory
   (10 modified files restored, the 6 new files absent), `git init`ed there
   (that scratch directory is NOT the Mentat repo), and both patches applied
   with `git apply`. All 16 resulting files are SHA256-identical to the live
   files. `build_tidy_workbook.py` is `i/lf w/crlf`, so this is also the proof
   that no CRLF/LF corruption crept into the patches.

Both patches were re-cut and both checks re-run AFTER T0 landed. An earlier pair
of patch files from before that point is gone; do not use any copy of them.

#### Working-tree provenance (verified, not assumed)

Each before/ snapshot was byte-compared against `git cat-file -p HEAD:<path>`,
comparing after CRLF normalisation because several of these files are `i/lf
w/crlf`. Four of the ten were CONTENT-CLEAN at HEAD `bd5dc8ea1`, so their entire
current diff is S2's: `mentat/R/tidy_stage.R`,
`mentat/tools/export_raw_contribution_warehouse.py`,
`mentat/tools/build_tidy_workbook.py` and
`mentat/tests/test_export_raw_contribution_warehouse.py`. The other six carry
another lane's work as context. This also reconciles the working-tree counts:
the session started at 58 ` M` + 202 `??` and S2 leaves 62 ` M` + 207 `??` -
+4 for exactly those four files, +5 for the five new files under `mentat/`.
The packet directory is a single collapsed `?? audits/mentat_failings_20260915/`
entry, so `patches/` and `receipts/` add no further lines. **`tidy_stage.R` is
listed in S0's WORKING-TREE HAZARD paragraph as modified by another lane; on
this evidence it was not.**

### Contract decisions

1. **Column-order rule.** On every listed surface the mandated columns appear in
   this exact order and immediately adjacent: occupation, street_1, street_2,
   city, state, zip. `employer` immediately precedes `occupation` on every
   surface. That employer-before-occupation convention already existed; S2 kept
   it rather than inventing a new order, and wrote it into the contract so it
   stops being folklore.
2. **Raw warehouse headers follow PRAGMA order with the block relocated
   (option B).** The exporter reads `PRAGMA table_info`, then emits the block
   contiguous at the position of its first member found in PRAGMA order
   (`contributor_city` today), members in block order, and leaves every other
   column in its relative PRAGMA order. The physical column order of
   `contributions` is NOT changed to match the header; CREATE TABLE order stays
   as it is. The alternative, basing the header on `collect.R`
   `contribution_columns()`, was rejected: that function orders columns 27-38
   differently from the live CREATE TABLE, so it produced a header that did not
   match what the exporter's own `PRAGMA table_info` call emits.
3. **Street is physically LAST in every table, and last in
   `corporate_migrations`.** A fresh database gets street at the end of the
   CREATE TABLE; a migrated one gets it at the end via ALTER TABLE, which can
   only append. Keeping both at the end is what makes fresh and migrated
   databases share one PRAGMA order. This matters because
   `merge_company_shards.py` `ensure_schema_compatible` compares PRAGMA order
   between shards. That probe was run and ACCEPTED the new schema. A separate,
   PRE-EXISTING PRAGMA-order mismatch on `contributor_id` remains for legacy
   databases; it is not S2's and S2 did not change it.
4. **An un-migrated database still exports, and the gap is reported at receipt
   level (T0).** `status` stays `"succeeded"`:
   `tools/parallel/Start-MentatResilientIndustryReports.ps1` keys its exit-code
   contract on that field, and the rows written ARE a complete record of what
   the database actually holds, so a schema gap must not become a pipeline
   outage. Instead the exporter now emits, when and only when something is
   missing, a top-level receipt key
   `missing_contract_columns` = `{table: [names]}` listing just the affected
   tables, plus one stderr line per table:
   `warning: <table> lacks contract columns <names>; run init_schema() from
   mentat/R/schema.R before treating this export as complete`.
   The key is OMITTED entirely on a complete schema, so a migrated database's
   receipt keeps exactly the shape it had before. **Both receipt paths are
   covered.** The reuse ("fast") path builds its own receipt and never computes
   a placement, so it would have silently dropped both signals on every rerun -
   the case an operator hits most often; it now recomputes the gap from the
   schema the stored manifest already carries and gives the same answer. Proved
   in `receipts/S2_green_python_phase3a.txt`: 12 tests OK, plus a probe that
   exports twice and checks the gap is reported on the full path AND the reuse
   path, with a negative control showing a complete schema produces no key and
   no warning on either path (14/14).
5. **The compact Contributions sheet and the formula-facts projection exclude
   street by design.** `compactRawHeaders` drops all geography, and
   `prepare_workbook_payload.py` `RAW_FIELDS` excludes geography, employer,
   occupation and street. Both are asserted as `must_not_contain` lists so a
   later well-meaning edit that "adds the missing address columns" fails a test
   instead of silently changing those surfaces.
6. **`bulk_candidates` carries the two columns for uniformity, but FEC bulk
   files have no street field, so they stay NULL.** The columns exist so that
   every contribution-shaped table has one schema; they are not evidence of
   coverage. Do not read a NULL there as a collection failure.
7. **The Contributor Detail sheet and the Chart Studio DIMENSIONS are DEFERRED
   to S4**, and both are marked `"status": "deferred to S4"` in the contract.
   The required change, with line numbers re-verified against the live tree on
   2026-09-16:
   - `mentat/app/contribution_data.py` `DIMENSIONS` (:48-58) gains
     `'street_1':'Contributor street 1'` and `'street_2':'Contributor street 2'`
     between `'occupation'` and `'city'`, in the required order employer,
     occupation, street_1, street_2, city, state, zip5. **Note for S4:** that is
     not a pure insertion. The live dict order is ... `state`, `city`,
     `employer`, `occupation` ... with `zip5` back at position 6, so reaching
     the required order means REORDERING existing keys. `DIMENSIONS` order is
     load-bearing: it drives the dimension list at :240 and a CREATE TABLE
     column list at :309. The record builder at :343-348 must read
     `raw['contributor_street_1']` and `raw['contributor_street_2']` alongside
     the existing `contributor_employer` / `contributor_occupation` reads
     (:348).
   - `mentat/tools/crypto_workbook_builder.mjs` `buildContributorDetail` -
     **the contract cites :2199-2245; the live function starts at :2205.** The
     header becomes Cycle, Company, Employer, Occupation, Street 1, Street 2,
     City, State, ZIP, Total Giving, Gift Count, Contributors, Rows Folded, with
     values from `row.street_1` / `row.street_2`, and the A5:K table widens to
     A5:M. The full site list, all verified live: headers :2207-2210, the row
     projection `.map` :2222-2234, the `row[10]` folded index :2235, the
     `titleBlock(..., "K")` width argument :2236-2243, `A5:K` at BOTH :2245 and
     :2246, the currency range `H6:H` :2249, the count range `I6:K` :2250, the
     11-entry `widths` array :2251, and the `B6:G` wrap-text range :2256.
   - `mentat/R/report.R` `contributor_keys` (:1828-1831) is today
     cycle, cycle_label, company, state, city, zip5, employer, occupation.
     Whether street joins that aggregate grain is S4's and Paul's call, not a
     mechanical edit: adding it changes what one Contributor Detail row means
     and how rows fold. The contract surface `contributor_detail_sheet` is
     marked deferred precisely so nobody treats this as done.
8. **`report.R` `spending_raw_report_rows` was edited by S2 although the file is
   unowned.** Two lines, the two SELECT lists at :2029 and :2048. Without them
   the columns exist in the database but never reach the report rows, so the
   whole chain would have been dead. Recorded here so the file's eventual owner
   knows.

### What the data receipts show (Phase 3b, on real lane databases)

These were produced against scratch COPIES of collected lane databases, never
the originals. Index: `receipts/S2_receipts_index.md`.

- **The migration is byte-exact.** `receipts/S2_migration_lane08.md` and
  `receipts/S2_migration_lane09.md` report MATCH on both lanes: running
  `init_schema()` over a collected database added the two street columns, LAST,
  and changed nothing else.
- **The warehouse headers agree with the contract on real data.**
  `receipts/S2_export_header_lane08.md`: headers EQUAL on the migrated copy,
  and the un-migrated copy omits the two columns and flags them.
- **The backfill works on real evidence.** `receipts/S2_backfill_lane08.md`:
  lane-08 updated 3,132 `corporate_giving` rows and 1,674 `contributions` rows
  from `fec_response_archive`; a second `--apply` updated 0 rows (idempotent);
  the refusal on an un-migrated database was verified; lane-01 matched 228 of
  228.
- **Coverage after backfill.** `receipts/S2_nonnull_rates.md`: `street_1` is
  100% populated; `street_2` is 1.12% and 3.47% (it is genuinely absent from
  most filings, not dropped). Before the migration the column was ABSENT
  everywhere - so the rates are a floor established by this work, not a
  regression from something better.
- **DEFECT-EMPLOYER-ZERO, as counts.** `receipts/S2_employer_zero_lane01.md`:
  lane-01's 228 `corporate_giving` rows are entity_type ORG 174, PAC 37, COM 17
  and IND 0, and the archived API responses carry null employer/occupation for
  all 228. The stored `''` therefore agrees with the source. That is a count,
  not a claim about why the API returns null for those entity types, and S0's
  note asking S2 to "explain it before trusting any employer-keyed join" should
  be read as answered only to that extent: the zeros are not a Mentat
  transcription fault.

### Open questions for Paul

1. **Apply the patches?** Nothing is committed. `S2_street_columns.patch` is the
   Area B work; `S2_street_columns_collect.patch` touches S1's two files and may
   want to wait for S1.
2. **Which production databases get the backfill?** Run
   `python tools/backfill_contributor_street.py <db>` (dry run) first, then
   `--apply`. Lane-08 and lane-01 are proven (above). The hydrated
   `.cache\receipt-metadata-repair-20260910\<industry>\mentat.db` inputs were
   NOT tested; treat them as unknown until a dry run says otherwise. Two
   operational notes: the tool takes `BEGIN IMMEDIATE` with a 60 s busy timeout,
   so run it when no collection is live or it will abort cleanly rather than
   half-write; and a committed run is atomic but NOT undoable - take your own
   copy first if you want a way back.
3. **Is S1's re-collect still wanted for street?** S0's note said street for
   already-stored rows was gone and S2 needed a re-collect. That is now only
   half true: for every row whose response body is archived, the backfill
   restores street without re-fetching - 3,132 + 1,674 rows on lane-08 alone. A
   re-collect is still needed only for rows with no archived body.
4. **A leaked test console.** PID 45068 was listening on port 62160 from the
   Python baseline sweep. It runs from `%TEMP%`, is harmless, and can be killed
   at will. It is not on 8802 and not one of Paul's consoles.
5. **Gitignore finding (this is the one that can silently break the lane).**
   `audits/mentat_failings_20260915/contracts/raw_contribution_columns.json` IS
   gitignored by `.gitignore:6` (`*.json`), and EVERY `receipts/*.txt` file is
   gitignored by `.gitignore:21` (`*.txt`). Verified with
   `git check-ignore -q <path>` per path, in `receipts/S2_contract_integrity.txt`.
   The `.md` packet files are NOT ignored, because `.gitignore:31` (`!*.md`)
   re-includes them, which is why the packet directory still shows as `??` in
   `git status`. Note that `git check-ignore -v` reports negated matches too and
   still exits 0, so only the `-q` exit code is an ignore verdict. This matters
   because all three new test suites read the contract JSON at import time: a
   plain `git add` would land tests that cannot find their contract. Paul's
   call - `git add -f` the contract file, or add a negation line next to the
   existing `!formal_visibility_roles.json` / `!tier_overrides.json` entries.

### Handoff notes for later sessions

**S1 (collection).** Two things.

- `fec_page.R`'s bulk CSV export branch (the `data.table::fread` at :565-571,
  whose completion is validated on `sub_id` only, at :579-588) has NOT been
  checked for the street columns. Verify that the downloaded export actually
  carries `contributor_street_1` / `contributor_street_2`; the row-count and
  `sub_id` checks there would not notice their absence.
- `page_raw` (`collect.R`:1084-1094) silently defaults an absent key to `""`,
  which is exactly how street went missing without a single error. The new
  canary in `flatten_fec_rows` prints one line per page when tabular rows carry
  neither street key. Watch `process.log` for it on the next run, and **do not
  remove the canary** - it is the only signal that distinguishes "the filer left
  street blank" from "we stopped asking for it".

**S4 (cross-industry addressing).** Decision (7) above is your work order, with
live line numbers. Additionally: **no test asserts the Contributor Detail header
today.** Add one that imports `contracts/raw_contribution_columns.json` and
checks `surfaces.contributor_detail_sheet.required_headers`, and flip that
surface's `status` off `"deferred to S4"` in the same change.

**Tidy workbook lane / whoever owns `build_tidy_workbook.py`.** Its
`CONTRIBUTIONS` registry gained `Street 1` and `Street 2` (T1 of this session).
Nothing else in that file changed. The writer's `select()` emits
`NULL AS "<column>"` for a registry column the store lacks, so an older tidy
store still builds; the two columns simply come out empty. An empty street
column is reported in the About sheet's "Blank columns" row and in the receipt
JSON, which is informational - `blank_columns()` is not a severity-`fail` check,
so a store with no street data still publishes.

**Whoever owns `merge_company_shards.py`.** Its `ensure_schema_compatible` probe
ACCEPTED the new schema, but while running it S2 observed a pre-existing PRAGMA
order mismatch on `contributor_id` for legacy databases. That predates this lane
and S2 left it alone.

**Anyone reading the raw warehouse CSVs.** The header ORDER changed for
already-migrated databases: employer and occupation now precede city/state/ZIP.
Every file still carries a header row and the partition manifest still records
`columns`, so a name-based reader is unaffected. The only in-repo consumer,
`tools/parallel/Start-MentatResilientIndustryReports.ps1`, just checks that the
manifest exists and records its path (:1560, :1589) - it never reads columns. A
reader OUTSIDE this repo that indexes by position rather than by name would
break, and S2 cannot enumerate those from here.

### Tests added, and how to run them

All four run with the working directory `C:\Users\pgoff\Mentat\mentat`.

```
python -m unittest tests.test_raw_contribution_columns -v
python -m unittest tests.test_backfill_contributor_street -v
& "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" tests\test_raw_contribution_columns.R
node tests\test_raw_contribution_columns.cjs
```

The edited suite is `python -m unittest tests.test_export_raw_contribution_warehouse -v`
(5 tests). The two new Python suites add 7 and 8 tests respectively, which is
exactly the 587 -> 602 change in the repo's discovered Python test count.
Receipts for every red/green step are in `receipts/S2_*.txt`; the final
four-runner sweep is `receipts/S2_final_sweep.txt`.
---

## S3 — PAC evidence ingestion (Area C)

**Status:** not started

**Files owned:** see table. `server.py` is CONTENDED.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —

---

## S4 — Cross-industry addressing (Area E)

**Status:** not started

**Files owned:** see table. `server.py` is CONTENDED.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —

---

## S5 — Navigation and linking (Area D)

**Status:** not started

**Files owned:** see table. `server.py` is CONTENDED.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —

---

## S6 — Surface (dashboard / dataviz)

**Status:** not started

**Files owned:** to be claimed. S6 must not claim a file still held by an
in-progress session.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —







