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
| `audits/mentat_failings_20260915/**` | S0 | committed by Paul | S0 writes nothing outside this directory |
| `mentat/R/fec_api.R` | S1 | not started | retry, page checkpoints, API SELECT list |
| `mentat/R/collect.R` | S1 | not started | scrape checkpoints, resume, industry SQL |
| `mentat/R/fec_page.R` | S1 | not started | chromote browser fallback |
| `mentat/tools/api_company_cycle_fanout.py` | S1 | not started | key cap, lane cap, recovery pool |
| `mentat/tools/collect_api_lane.R` | S1 | not started | assigns `MENTAT_INDUSTRY` |
| `mentat/R/schema.R` | S2 | committed by Paul | `corporate_giving`, migrations |
| `mentat/tools/export_raw_contribution_warehouse.py` | S2 | committed by Paul | PRAGMA-driven export |
| `mentat/tools/export_crypto_spending_data.R` | S2 | committed by Paul | workbook column list |
| `mentat/R/tidy_stage.R` | S2 | committed by Paul | tidy contributions spec; content-clean at HEAD before S2, whole diff is S2's |
| `mentat/R/report.R` | S2 | committed by Paul | two SELECT lines only (`spending_raw_report_rows` :2029, :2048); file otherwise unowned |
| `mentat/tools/build_tidy_workbook.py` | S2 | committed by Paul | `CONTRIBUTIONS` registry: Street 1 / Street 2 on the companion Data workbook |
| `mentat/tools/backfill_contributor_street.py` | S2 | committed by Paul | NEW: rebuild street from archived FEC response bodies, no network |
| `mentat/tests/test_raw_contribution_columns.py` | S2 | committed by Paul | NEW: Python producers vs the contract; hosts `assert_block_adjacent` |
| `mentat/tests/test_raw_contribution_columns.R` | S2 | committed by Paul | NEW: checks (a)-(h) across collect.R, fec_api.R, tidy_stage.R, report.R |
| `mentat/tests/test_raw_contribution_columns.cjs` | S2 | committed by Paul | NEW: workbook sheet writer vs the contract |
| `mentat/tests/test_backfill_contributor_street.py` | S2 | committed by Paul | NEW: backfill precedence, idempotence, un-migrated refusal |
| `mentat/tests/test_export_raw_contribution_warehouse.py` | S2 | committed by Paul | EDITED: fixture SCHEMA in migrated shape + block assertions |
| `mentat/app/evidence_csv.py` | S3 | not started | `MAX_BYTES`, `MAX_COLUMNS` |
| `mentat/app/evidence-csv.js` | S3 | not started | client size mirror, status line |
| `mentat/tools/pac_evidence.py` | S3 | not started | collector, `ThreadPoolExecutor(3)` |
| `mentat/tools/fec_key_store.py` | S3 | not started | see DEFECT-KEYSTORE in PACKET.md |
| `mentat/app/contribution_data.py` | S4 | committed by Paul (8377b5e77) | `DIMENSIONS`, detail row cap |
| `mentat/app/chart-studio.js` | S4 | committed by Paul (8377b5e77) | API base, view routing |
| `mentat/app/chart-studio-core.js` | S4 | committed by Paul (8377b5e77) | `STUDIO_GROUP_LIMIT = 60` |
| `mentat/app/snapshot_registry.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/app/industry_scope.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/app/cross_reference_data.py` | S4 | committed by Paul (8377b5e77) | CLAIMED 2026-09-16, previously unowned: `?industry=` selects a run, so `latest_cross_reference` was refactored into a shared `_run_view` and a new `cross_reference_for_industry` |
| `mentat/app/contribution_semantics.py` | S4 | committed by Paul (8377b5e77) | CLAIMED 2026-09-16, previously unowned: one line, `catalog(directory, sources=None)`, so a request can reuse the report-folder scan it already paid for |
| `mentat/app/chart-studio-contributions.js` | S4 | committed by Paul (8377b5e77) | one-line: industry in the query body |
| `mentat/tools/crypto_workbook_builder.mjs` | S4 | committed by Paul (8377b5e77) | buildContributorDetail widening, S2 decision 7 |
| `mentat/R/report.R` | S4 | committed by Paul (8377b5e77) | contributor_keys only, S2 decision 7 |
| `mentat/tests/test_snapshot_registry.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/tests/test_industry_routes.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/tests/test_studio_views_industry.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/tests/test_contribution_dimensions_order.py` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/tests/test_studio_industry_browser.cjs` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/tests/test_contributor_detail_header.cjs` | S4 | committed by Paul (8377b5e77) | NEW |
| `mentat/app/index.html` | S5 | committed by Paul (a7e09ed8c) | tabs (unchanged), graph-mode select; one `<script src="/scope.js">` before app.js |
| `mentat/app/app.js` | S5 | committed by Paul (a7e09ed8c) | hash routing, localStorage; comment only - `showView` is unchanged |
| `mentat/app/graph.js` | S5 | committed by Paul (a7e09ed8c) | `clear()` untouched; reads and writes the URL scope, ruling A(ii) visibility |
| `mentat/app/scope.js` | S5 | committed by Paul (a7e09ed8c) | NEW: the URL scope module (`read`/`write`/`parse`/`serialize`/`href`/`subscribe`) |
| `mentat/app/cross-reference.js` | S5 | committed by Paul (a7e09ed8c) | CLAIMED 2026-09-17, previously unowned: industry-scoped fetch + `selected_by` in the status line |
| `mentat/app/chart-studio.js` | S5 | committed by Paul (a7e09ed8c) | S5 hunks only: URL scope (dataset preselection, carried pills, `saved=`). S4's row above stands - S4's work is committed at `8377b5e77` and S5's hunks sit on top of it; this is a hand-off, not a second live claim |
| `mentat/app/tests/scope.test.js` | S5 | committed by Paul (a7e09ed8c) | NEW: the url_scope contract from both ends |
| `mentat/tests/test_navigation_scope_browser.cjs` | S5 | committed by Paul (a7e09ed8c) | NEW: real-client pass, 13 steps |
| `audits/mentat_failings_20260915/contracts/url_scope.json` | S5 | committed by Paul (a7e09ed8c) | NEW: v1, the URL vocabulary S6 inherits |
| `mentat/app/graph_data.py` | S5 | untouched by S5 | ruling B (2026-09-17): NOT edited. Carries another lane's uncommitted hunks (`singleflight_cache`) and navigation needs none of it; the two Downstream failure texts stay |
| `mentat/R/fec_beneficiary.R` | S5 | untouched by S5 | ruling B (2026-09-17): NOT edited. Carries another lane's uncommitted hunks (PAS2 parser v4) |
| `mentat/app/server.py` | S4 | committed by Paul (8377b5e77, then a565216bf) | S4 hunks built and receipted. **S5 added exactly one line** (`'/scope.js': ('scope.js', 'text/javascript')` in `STATIC_ASSETS`; grep `'/scope.js'` rather than a line number - it landed at `:71` and a later session's lazy-import hunk had already moved it to `:97`) because that dict is an allow-list and an unlisted path answers 404 - a new client script cannot be served without it. That line is **already committed**: Paul's `a565216bf` (S3d latency, 2026-09-17 00:49) swept it in six minutes after S5 wrote it. The S5 patch carries no `server.py` hunk |
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

**Status:** committed by Paul (11654f911, 2026-09-16)

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

**Status:** committed by Paul (2026-09-16, whole-file; see Patches note)

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

Committed 2026-09-16 as whole files at Paul's ruling after a three-way merge
showed collect.R, fec_api.R and export_crypto_spending_data.R cannot be
separated from the contributor-id / evidence-archive lane's uncommitted hunks
(S2's column lists carry contributor_id, which exists only in that lane's
hunks). The commit therefore also carries that lane's hunks in schema.R,
collect.R, fec_api.R, report.R, export_crypto_spending_data.R and
crypto_workbook_builder.mjs. patches/S2_street_columns*.patch remain the
hunk-isolated record of S2's own changes.

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

Answered by the production dry run (2026-09-16,
receipts/S2_backfill_dryrun_production.md, 41 database copies, production files
untouched): the backfill fills 100% of the ten 2026-09-15 Credit Unions
run-lane databases (14,265 rows) and 32,581 of 783,808 contributions in
banking-20260910, but the report-input sets
mentat/.cache/receipt-metadata-repair-20260910/<industry>/mentat.db (7
industries) and mentat/.cache/repair-20260908-databases (8) carry no
fec_response_archive and empty checkpoints, so 0 of roughly 4.0 million rows
can be filled there. S1's re-collect is therefore required for street on the
report inputs. Note also that init_schema() on those older databases carries
other lanes' pending migrations along with street (contributor_id,
query_contract, the four evidence tables, and on the 2026-09-08 set the
filing-form columns); six audit fixtures under
outputs/mentat-full-audit-2026-09-13/ refuse init_schema() because their
hand-built contributions table lacks two_year_transaction_period.

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

**Status:** BUILT, receipts ready, UNCOMMITTED (2026-09-16). This slot is S0's stub; the full S3 record — files, contracts, before/after tallies, real-client pass, measurements, open items and the S6 pane state model — is the section of the same title appended at the END of this file.

**Files owned:** `mentat/app/evidence_csv.py`, `mentat/app/evidence-csv.js`, `mentat/tools/pac_evidence.py`, the four evidence hunks in `mentat/app/server.py` (CONTENDED; before/after diffs receipted).

**Patches:** `patches/S3_pac_evidence_fixes.patch` plus three PROPOSED patches for unowned files (`S3_PROPOSED_PATCHES.md`).

**Contract decisions:** `contracts/evidence-csv-import.json`, `contracts/evidence-job-status.json`.

**Open questions:** see the appended section, "Open for Paul".

**Handoff notes for later sessions:** see the appended section, "Pane state model for S6".

---

## S4 — Cross-industry addressing (Area E)

**Status:** committed by Paul (2026-09-16 evening, `8377b5e77`, 35 files, +8,351/-127, staged from patches/S4_cross_industry_contract.patch via `git apply --cached`; console 8806 verified current on code 5f7da2d1… / assets 30772a98…). Prior status for the record: BUILT, receipts ready, UNCOMMITTED (2026-09-16 evening); Paul commits from
`patches/S4_cross_industry_contract.patch`.
Patch regenerated against HEAD 21c9cab6d (S3b committed after pass B); 499891 bytes, 35 files.

**Files owned:** see table, all now BUILT/uncommitted. `server.py` is CONTENDED and S5
waits on Paul's commit. Claimed by S4 during the build, each previously unowned and each
recorded in the table when claimed: `mentat/app/snapshot_registry.py` (NEW),
`mentat/app/industry_scope.py` (NEW), `mentat/app/cross_reference_data.py` (the
`?industry=` run selector), `mentat/app/contribution_semantics.py` (one line, a
`sources=None` pass-through), `mentat/app/chart-studio-contributions.js`,
`mentat/tools/crypto_workbook_builder.mjs`, `mentat/R/report.R` (contributor grain only).
New tests: `tests/test_snapshot_registry.py`, `tests/test_industry_routes.py`,
`tests/test_studio_views_industry.py`, `tests/test_contribution_dimensions_order.py`,
`tests/test_contributor_detail_header.cjs`, `tests/test_studio_industry_browser.cjs`.

**Patches:** `patches/S4_cross_industry_contract.patch` — every tracked S4 file as
`git diff HEAD`, then each new file as a `/dev/null` hunk, so the whole lane applies from
one file. `server.py` was clean at HEAD before S4 (S3 committed its own hunks at
303409192 and 91fe7402a), so the whole `server.py` diff in this patch is S4's.

**Receipts:** `receipts/S4_phase2-5_server.txt` (registry, scope, routes, the five
python-review findings, close-out pass A, pass C), `receipts/S4_phase4_client.txt`
(the five typescript-review findings and the real-client browser pass),
`receipts/S4_phase6_contributor_detail.txt`, `receipts/S4_acceptance_real_snapshots.txt`.

**Contract decisions:** three contracts, written before any code:
`contracts/snapshot_registry.json` **v2**, `contracts/contributions_api.json` **v2**,
`contracts/studio_api.json` **v1**; `contracts/raw_contribution_columns.json` is **v2**
with no deferred surface. Every correction, and why:

1. **Underscore slug.** The console has one slug rule, `contribution_data._slug`:
   `re.sub(r'[^a-z0-9]+','_',label.lower()).strip('_')`. It uses UNDERSCORES and it names
   the `.cache/industry-report/<slug>/` directory. Every `"credit-union"` slug and
   `/credit-union/` path in the contracts and in S4_DESIGN.md §2 became `credit_union`.
   No second slug rule was invented. The collector slug `credit-unions` stays in a
   negative control: it is the value that must be rejected.
2. **Error body.** `server.py` emits exactly `{"error": str(error)}` (`do_GET :1853`,
   `do_POST :1974`). Example 15 lost its `known` key.
3. **Example 14 rewritten.** It carried `"pending_phase_5": true` and a `"..."`
   placeholder, written before phase 5 decided. It now shows what the route answers.
4. **`"token": "<hex>"` → `"<token>"`** — the session token is `secrets.token_urlsafe`,
   not hex.
5. **`schema_version` 2 → 3** in the six catalog/query/records examples, matching
   `contribution_data.VERSION = 3` after the phase-6 lane's bump.
6. **A fourth registry example, Telecom**, showing the unreadable-workbook shape:
   `available: false`, `message: "Report workbook is unreadable."`, `workbook.sha256`
   and `build_stamp` null. A stamp built from the three remaining fields would be the
   SAME string for every unreadable book, so none is invented.
7. **Parser relaxation, `chart-studio-core.js:1007`.** Adding example 6 turned the JS
   consumer red — `"Telecom is missing a valid build_stamp."` — which is a live
   client/server disagreement of the DE-021 kind that the example exposed. Fixed per
   `contracts/README.md`'s own procedure ("Change the code until both are green and the
   negative control still fails"): `build_stamp` may be null only when `available` is
   false. Made during a docs-only pass, flagged in the receipt, and **the coordinator
   ruled it STANDS**.

**Design premise correction (measured, not assumed):** there never was a console-global
industry to remove. `main()` takes `--port`, `--data-root`, `--keys-file`, `--rscript`,
`--read-only` and nothing else, and one process already served every published snapshot.
And **the dataset id IS the industry label**: `contribution_data.py` sets
`industry = workbook.name.removesuffix(' Industry Spending Overview.xlsx')` and then
`{'id': industry, 'industry': industry, 'label': industry, ...}`. S4's job was therefore
not to add a selector but to make the one that existed explicit, uniform,
registry-backed and echoed.

**Measurements:**

- `snapshot_registry.registry()` on the real published folder (8 books + one Excel lock
  file): **3.15 s cold, 73 ms warm**. `_workbook_source` is `lru_cache`d; the warm cost is
  the per-snapshot manifest and payload-header reads `_sources()` already did on every
  catalog and query request before S4. Deliberately NOT memoized: a rebuilt workbook has
  to change its `build_stamp` immediately, which is the whole point of the stamp.
- Contributor grain, Banking: **783,808 rows, 95,331 distinct contributor-grain rows, no
  street columns present yet, row-count delta 0** (phase 6 receipt).
- Tests: nine-suite python **118 OK (skipped 1)**; `node --test "app/tests/**/*.test.js"`
  **118/118**; `tests/test_studio_industry_browser.cjs` **10/10 steps, exit 0**;
  R `test_spending_detail_frames` **PASS** (8 cells → 9, folded 5 → 6);
  `test_raw_contribution_columns` **PASS** in both languages; `test_fec_api` **PASS**.
  The one skip is contract example 13 (`/api/graph`), marked
  `skipTest('acceptance run: needs a real workbook')`.

**Acceptance:** `receipts/S4_acceptance_real_snapshots.txt` — **10 of 13 steps PASS** on a
scratch console against the real published folder. Rerun complete
(`receipts/S4_acceptance_rerun.txt`): Banking and Credit Union queries ready with distinct
dataset/industry/build_stamp matching `GET /api/snapshots`; industry/dataset disagreement
→ 400 exact message; records ready 5 rows; two-industry saved view round-trips sheets +
`source.industry`, list `industries` == [Banking, Credit Union], on-disk JSON captured;
briefing add echoes `source.industry`; health stamps identical across three fresh processes
(code `5f7da2d1…`, assets `30772a98…`). Cost: `VERSION` 3 invalidated the analytics
caches; Banking's 707 MB index took ~38 min behind the single global build lock
(`_build_gate`); Banking and Credit Union caches are now built in the real state dir, the
other six materialize on first query.

**Read that rerun as three passes, not one.** Pass 1 (21:40–22:21) recorded
`FAIL query_ready_Banking: did not reach ready within 1500s; last status=preparing` and
skipped its cross-industry comparisons. The Banking readiness, the differ checks and the
400 above are **pass 3's** (22:30:56), taken after the 707 MB cache finished at 22:19:21;
the saved-view and briefing round-trips are pass 1's. The rerun also records `git_sha`
drift — pass 1 saw 91fe7402a, pass 3 saw 21c9cab6d — with `code_sha256` and
`assets_sha256` identical across both, so the intervening commit touched no server code
or asset.

**The verifier sweep receipt now exists** (`receipts/S4_verifier_sweep.txt`) and carries a
dated **Post-sweep diagnosis**: of the two node tests it called NEW RED, **neither is
S4's**. `test_studio_data_source_browser.cjs` passes alone twice (45.8 s, 63.0 s) against
byte-identical inputs — a load-induced flake. `test_evidence_csv_browser.cjs` fails alone
twice, deterministically, at step 14, because commit 21c9cab6d retired `M_UTF8` in favour
of `M_BINARY` (`mentat/app/evidence_csv.py:187-191`) without updating that test's
expectation (`mentat/tests/test_evidence_csv_browser.cjs:499`) — S3b's to close, not
S4's. That sweep's own "HEAD commit: 91fe7402a (VERIFIED)" line is FALSE: 21c9cab6d had
been HEAD for 8m20s when it ran. S4's own suites were re-run during the diagnosis and are
unmoved: `node --test "app/tests/**/*.test.js"` **118/118**,
`tests/test_studio_industry_browser.cjs` **10/10 steps, exit 0**.

**Non-owned test edits, for their owners to nod at.** Each was forced by a contract
change, and each keeps the test's own intent:

- `mentat/tests/test_contribution_http.py` — the session body assertion (now carries
  `industry` + `industries[]`), the geography-catalog assertion, and
  `catalog.assert_called_once_with(report_root)` → `call_count` + `args[0]`, because the
  route now threads its one folder scan into the producer.
- `mentat/tests/test_console_delivery.py` (untracked at HEAD) — one assertion: the
  geography catalogue body now carries `industry`.

**Foreign observations, recorded because they are not S4's to fix:**

- S3's commit 91fe7402a carried S4's HANDOFF hunks whole-file. No S4 code went in with it.
- `contracts/evidence-csv-import.json` shows working-tree drift that S4 did not make.
- A `~$Credit Union Industry Spending Overview.xlsx` Excel lock file was present in the
  published folder while S4 measured, which means **the workbook was open in Excel**.
  `_sources()` listed it as a ninth snapshot whose slug collided with the real Credit
  Union's. The phantom is skipped now (`contribution_data.py:184-186`, phase-6 lane);
  `snapshot_registry.find()` also resolves a label outright and prefers an available
  snapshot on a slug, so addressing stays deterministic if one ever appears again.

**Known limits, stated rather than hidden:**

- **No UI writes `sheet.sources[]`.** `selectContributionDataset` rewrites every sheet's
  `source`, and `sourceKey` is one per view. The two-industry model is proven at the
  contract, API and server round-trip level and in the browser by two saved
  single-industry views — not by a picker. The picker is S5's.
- **POST `query`/`records` still scan the report folder twice**: once to resolve the
  scope, once inside `contribution_query` → `contribution_data._source()`. Closing it
  means changing the readers' signature, which the contract pins as a producer and both
  suites patch.
- **`graph_catalog` names come from every `.xlsx`**, a wider set than the registry's
  Overview books, so an unknown graph industry deliberately falls through to the existing
  "Choose an industry with completed reports." rather than the registry refusal. Refusing
  it would remove views those routes serve today.
- `Console.report_path('published-reports', i)` calls `published_reports()` once per
  index — an N+1 older than S4, left alone.

**Open for Paul:**

1. Commit from the patch.
2. Restart the consoles (below): they predate every S4 edit.
3. Do the three non-owned test-file edits need their owners' nod, or does the contract
   change carry them?
4. Memoize the registry later, or keep paying 73 ms for a stamp that can never be stale?

---

### HANDOFF NOTES FOR S5 — the parameter names, verbatim

- **`industry`** — the published label exactly as the registry lists it (`Credit Union`,
  `Property & Casualty Insurance`), URL-encoded on GET, a JSON string on POST bodies. The
  server also accepts the label's slug (`contribution_data._slug`, underscores:
  `credit_union`, `property_casualty_insurance`) and **always echoes the label**.
- **`dataset`** — the legacy selector on `/api/contributions/query|records`, the same
  value as `industry`. Kept so every existing caller keeps working. Both present and
  disagreeing is a 400.
- **`id=published-reports`** — the graph and comparison routes' fixed run identifier.
- **`build_stamp`** — 64 hex, echoed on every industry-scoped response;
  `sha256("\n".join([workbook_sha256, companion or "", database or "", payload or ""]))`.
  Null only on an entry whose workbook could not be read.
- **`GET /api/snapshots`** — the registry envelope; `?industry=` filters it to one entry.
- **`GET /api/cross-reference?industry=<label>`** — `industry` is the ONLY query key this
  view accepts; every other key still raises "The cross-reference view accepts no path or
  run parameters." The response carries `selected_by`: `"pointer"` on the latest path,
  `"industry"` when a label chose the run, and `report_sha256` is always the digest of the
  bytes that call read, never a pointer's claim.
- **Saved views** — `source.industry`, `sheets[].source.industry`, and
  `sheets[].sources[] = [{industry, dataset, label}]`. `GET /api/studio/views` list items
  carry `industries[]`, the distinct labels in first-seen order. Membership in the
  registry is deliberately NOT validated at save or load: a saved view must reload after
  its snapshot is retired, and the client reports it at open time.

Error bodies, verbatim — one key, `error`, and nothing else:

```json
{"error": "Choose a registered industry: Banking, Credit Union."}
{"error": "The industry and dataset in this request disagree."}
{"error": "Every series source in a saved view needs an industry."}
{"error": "A saved view carries its industry inside its data source."}
{"error": "The cross-reference view accepts no path or run parameters."}
```

The registered labels in the first one are sorted, joined with a comma and a space, and
end in one period.

---

### RESTART, for Paul

The running consoles predate every S4 edit, so none of this is live until they restart.
S0 recorded 8802, 8806 (the Mentat console) and 8808 up. Per port, from any directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\mentat\app\Start-MentatApp.ps1 -Port 8806
```

`-DataRoot` is optional and was left off deliberately: `Start-MentatApp.ps1:111` already
defaults it to `Join-Path $env:LOCALAPPDATA 'Mentat\console'`, which on this machine is
`C:\Users\pgoff\AppData\Local\Mentat\console`. Passing it explicitly needs PowerShell's
own syntax — `-DataRoot "$env:LOCALAPPDATA\Mentat\console"`, not the cmd.exe `%VAR%`
form, which PowerShell does not expand. The launcher's real parameters are `-Port`
(default 8802), `-PythonPath`, `-KeysFile`, `-RScriptPath`, `-NoBrowser`, `-AppWindow`,
`-DataRoot`, `-ErrorLog`.

**D-029 applies: the launcher replaces only an IDLE stale console.**
`Start-MentatApp.ps1:98` returns false unless `$health.busy -eq $false`, so a console
mid-collection keeps its port and its old build. Check `/api/health` before assuming a
restart took.

Expected build identity after the restart, computed from this working tree
(`python -c "import server; print(server.CODE_TREE_SHA256, server.ASSET_TREE_SHA256)"`
run in `mentat/app`):

```
code_sha256   5f7da2d17ee9a94d24c9916bfecee82726639ebe9ad7161ef94ea3631f5fb28f
assets_sha256 30772a98f1c9d7d1fd37f1c3ca81223ad823ef15cc175da48ce84591463728b8
```

A restarted console must report that pair in `/api/health` as `code_sha256` and
`assets_sha256`, with `on_disk_code_sha256_now` and `on_disk_assets_sha256_now` equal to
them. If they differ, the tree moved after this was written — recompute rather than
trusting these two lines.

---

## S5 — Navigation and linking (Area D)

**Status:** committed by Paul (2026-09-17, `a7e09ed8c`, 14 files, +2,506/-16, staged from patches/S5_url_scope.patch via `git apply --cached` with the HANDOFF hunk excluded because 522e3ad31 had already carried this section whole-file; console 8806 verified current on assets 9350a964… / code ba9d6c22… and serving /scope.js). Prior status for the record: BUILT, receipts ready, UNCOMMITTED (2026-09-17); Paul commits from
`patches/S5_url_scope.patch`. Design accepted by Paul with three rulings (below);
phases 1-3 built, Fable-reviewed, three review findings fixed, sweep run.
Patch cut against HEAD `a565216bf`.

**`git add -f` is required for part of this patch.** The repo-root `.gitignore`
ignores `*.json` (`:6`), `*.txt` (`:21`) and `*.html` (`:20`), so
`contracts/url_scope.json`, `receipts/S5_phase1-3.txt` and
`receipts/S5_verifier_sweep.txt` are ignored files. They land the way S4's did -
`git apply --cached` from the patch, or `git add -f` - not through a plain
`git add`. The `.md` and `.js` files are unaffected (`!*.md` at `:32`).

**Files owned:** see table, all now BUILT/uncommitted.

- `mentat/app/index.html` — one `<script src="/scope.js" defer>` before `app.js` (`:7`). Tab strip unchanged; `#graph-candidate-controls` keeps its `hidden`.
- `mentat/app/app.js` — comment only (`:42-45`). `showView` is byte-identical in behaviour.
- `mentat/app/graph.js` — reads the permalink, writes the scope back, ruling A(ii) visibility. `clear()` untouched.
- `mentat/app/chart-studio.js` — S5 hunks on top of S4's committed work (`8377b5e77`): dataset preselection, carried pills, `saved=`, the deferred industry follow.
- `mentat/app/cross-reference.js` — CLAIMED 2026-09-17, previously unowned: industry-scoped fetch and the run line.
- `mentat/app/scope.js` — NEW, the module the vocabulary lives in.
- `mentat/app/tests/scope.test.js` — NEW, the contract from both ends.
- `mentat/tests/test_navigation_scope_browser.cjs` — NEW, the real-client pass.
- `audits/mentat_failings_20260915/contracts/url_scope.json` — NEW, v1.
- `mentat/app/graph_data.py`, `mentat/R/fec_beneficiary.R` — **NOT TOUCHED** (ruling B). Both still carry another lane's uncommitted hunks (`singleflight_cache`; PAS2 parser v4). Their two Downstream failure texts stay as they are.

**Patches:** `patches/S5_url_scope.patch` — `git diff HEAD` for the eight tracked
files, then each new file as a `/dev/null` hunk, so the whole lane applies from one
file. It contains **no `server.py`, `graph_data.py` or `fec_beneficiary.R` hunk**;
verified by `git apply --stat` and `git apply --check --reverse` (exit 0).

**Rulings, verbatim (Paul, 2026-09-17):**

- **A(ii)** — "show the Graph 'Candidate view' select as soon as a report is chosen
  and make `mode=activity` linkable, no new tab".
- **B** — "leave `mentat/app/graph_data.py` and `mentat/R/fec_beneficiary.R`
  untouched (they carry another lane's uncommitted hunks)".
- **C** — "keep `history.replaceState` (never `pushState`)".

**Contract decisions:** `contracts/url_scope.json` **v1**, written before any code.
**The hash names the tab; the query string carries the scope.** A fragment-only
`history.replaceState('#graph')` resolves against the current URL and keeps its
query, so `showView` needs no change and a tab switch cannot lose a permalink.
Nothing new is stored in `localStorage` or `sessionStorage`: the URL is the state,
so a permalink, a reload and a tab switch are one operation.

| key | value rule | writer | reader |
| --- | --- | --- | --- |
| `industry` | the published label exactly as the registry lists it (`Credit Union`, `Property & Casualty Insurance`); never the slug | Graph industry select; Chart Studio dataset picker and "Open in Chart Studio" | Graph, Chart Studio, Cross-reference |
| `company` | company name as the Graph select spells it | Graph; "Open in Chart Studio" | Graph; Chart Studio as a carried pill |
| `cycle` | election-cycle END year, four digits, as Graph spells it (`2024`) | Graph; "Open in Chart Studio" | Graph; Chart Studio via `core.carriedFilterValue('cycle', v)` → `2023-2024` |
| `mode` | `direct` \| `activity` \| `estimates`; `direct` is the default and is removed | Graph | Graph |
| `direction` | a `#graph-direction` value; `Support` is the default and is removed | Graph | Graph |
| `tier` | a `#graph-tier` value; empty means all levels and is removed | Graph | Graph |
| `funding` | a `#graph-funding` value; `all` is the default and is removed | Graph | Graph |
| `category` | the recipient-type drill-down id | Graph | Graph |
| `recipient` | the organization drill-down id | Graph | Graph |
| `saved` | 32 lowercase hex, the shape `save_view()` mints and `get_view()` demands | Chart Studio, on a successful save or open | Chart Studio |
| `studioPane` | PRE-EXISTING, `B`\|`C`\|`D`; S5 never writes it and never removes it | the reader / pane frames | `chart-studio.js:17` |

**Reserved for S6, written by nobody in S5:** `evidence`, `id`, `committee`,
`offset`, `limit`. `write()` preserves them untouched, in place, exactly as it
preserves `studioPane`.

Six decisions worth naming:

1. **Values are `encodeURIComponent`'d, not `URLSearchParams.toString()`'d.** The
   latter spells a space as `+`; `Property & Casualty Insurance` has to survive a
   copied permalink, so the contract pins `Property%20%26%20Casualty%20Insurance`.
2. **`write()` refuses what `read()` would reject.** A value that fails validation
   removes its key rather than being written, so the URL can never carry something
   `read()` drops. Every negative control is asserted in both directions.
3. **`saved` is `[a-f0-9]{32}`**, the same rule `server.py get_view()` enforces, so
   a saved-view permalink never fires a request the console answers 400 for. A view
   that lives only in this tab (`viewsMemory`, id `memory-...`) is never written: it
   is not addressable, and writing it would silently remove a real id.
4. **Defaults are absent from the URL, not spelled out in it** (`mode=direct`,
   `direction=Support`, `funding=all`, every empty select), so a URL names only
   what the reader actually chose.
5. **Unknown keys are preserved in place**, keeping their order; new keys append.
   The contract's `write` example is exactly that case.
6. **`replaceState` only (ruling C).** Tab switches created no history entries
   before S5 and create none now; `pushState` appears nowhere.

**Measurements:**

- Node: `node --test "app/tests/**/*.test.js"` **151/151** (121 before S5; the 30
  new tests are `app/tests/scope.test.js`, which loads the contract from disk).
- Real-client: `node tests/test_navigation_scope_browser.cjs` **13/13 steps,
  exit 0**, against the real `python app/server.py` on a free port with a throwaway
  `--data-root`. `/api/studio/views` is deliberately not stubbed, so the saved view
  in step 8 really reaches disk and is read back off it.
- Baseline browser tests, all green after the fixes: `test_console_browser.cjs`,
  `test_app_lazy_startup_browser.cjs` **3/3**, `test_graph_lazy_tables_browser.cjs`
  **1/1**, `test_studio_industry_browser.cjs` **10/10 steps**.
- Sweep: `receipts/S5_verifier_sweep.txt` — **9/10 browser suites**, node 151/151,
  python **55 ran, OK (1 skipped)**, `url_scope.json` valid. Its one red was
  `test_console_browser.cjs`, which is **not an S5 defect and is now fixed**: see
  "Non-owned edits" below. (Two corrections to that receipt for the record: it
  reports the branch as `claude/multi-industry-snapshot-support-7c95a9`, but this
  repo is on `codex/mentat-crypto`; and its failure detail truncates before the
  assertion, so the line number in it came from a later run, not from the sweep.)
- Build stamp, `python -c "import server; print(server.CODE_TREE_SHA256,
  server.ASSET_TREE_SHA256)"` in `mentat/app`: code `491a0d4680824a3e561ad9e0ddbff264c42ee58bf3d1e2480d12fba117a66087`,
  assets `9350a96481e14c24e0058e24fe12d0907e7f2d754e9b35ef6caefd2d7600773c`.

**Fable review (2026-09-17), three findings, all fixed.** Each fix was made only
after its new browser step had been written and RUN against the pre-fix bytes, so
none rests on an argument alone; the pre-fix assertions are verbatim in
`receipts/S5_phase1-3.txt`.

1. **HIGH, `graph.js:125`, step 11.** `refresh(initial)` sent `&latest=1`
   unconditionally, and `graph_view()` replaces the requested cycle with
   `max(years)` whenever it is present (`graph_data.py:317-318`), so the URL said
   2022 while the view showed 2024. Now `initial && !query.get('cycle')`. S5's own
   step 1 could not see this: the fixture's newest cycle is the one that permalink
   asks for, so the `/api/graph` stub now mirrors that server rule and the hole
   cannot reopen. Pre-fix: `'2024' !== '2022'`.
2. **HIGH, `chart-studio.js:60, :142, :154, :417-421, :2006-2013`, step 12.**
   `saved=<id>` outlived the sheets it described: edit the opened view, reload, and
   `openSavedFromUrl()` re-opened the saved view while `persist()` wrote it over the
   edited sheets — **a data loss that did not exist before S5 put the id in the
   URL**. The first change to the working sheets after an open or a save now clears
   the id, at `commit()` (45 edit paths) and at `step()` (undo/redo mutates sheets
   and calls `persist()` without going through `commit()`), and deliberately NOT at
   `persist()`, which also runs on load paths and would have destroyed the
   permalink before `openSavedFromUrl()` read it. An open fences its own `commit`
   with `holdingSavedId`. Both directions are pinned by the step. Pre-fix:
   `saved= leaving the URL after the first edit never happened`.
3. **MEDIUM, `cross-reference.js:150-160`, step 13.** An industry-scoped ask that
   found nothing still said "Latest run", naming the one run it was not showing.
   Now "No cross-reference run for <label>". Both branches are pinned: step 5 the
   found run, step 13 the empty one. Pre-fix: `got "Latest run · Saved evidence
   refreshed."`.

**User-visible changes, for Paul:**

- **Cross-reference follows the URL's industry.** It is no longer "the latest saved
  run" unconditionally: once the URL names an industry — and Graph always puts one
  there — it shows the newest run for that industry, or that industry's empty
  state. The status line says which of the three it is looking at: "Newest run for
  Banking · …", "No cross-reference run for Banking · …", or "Latest run · …".
  No silent fallback to the bare route was added; that would make the line lie.
- **The Candidate view select is visible once a report is chosen**, wherever the
  candidate panel is showing, instead of only on the Candidates analysis tab. The
  note at `index.html:107` ("Direct contributions only") is now shown only while it
  is true, because the select above it can make it untrue on the overview tab.

**Known limits, stated rather than hidden:**

a. **Chart Studio never writes `company`/`cycle` back.** Removing a carried pill
   does not remove the key from the URL, so `loadContributions(refresh)` re-carries
   it. Idempotent — the pill returns exactly as it was, nothing lost or duplicated
   — but a removed pill can reappear on a source refresh. Graph owns those two keys
   today; **S6 may want to give Chart Studio ownership of them.**
b. **`scope.js merge()` re-encodes unknown keys' values** with
   `encodeURIComponent`, so a `+` meaning a space in another session's key is
   normalised to `%20`. The same value either way under `URLSearchParams`
   decoding; harmless, named here so nobody reads it as data loss.
c. **A first load that names no cycle still sends `latest=1`** and lands on the
   newest cycle while the URL names no cycle at all. That is the contract's own
   rule ("a URL names only what the reader chose") and it is unchanged from before
   S5, but a link copied in that state means "newest", not "2024".
d. **No cross-tab sync.** `subscribe` listens to `popstate` and this document's
   `mentat:scope`; a second browser tab is a different document and no `storage`
   event is used, so two tabs do not follow each other.
e. **The S0 known-red for `test_console_browser.cjs` was a race, and it is closed
   here** — see the second non-owned edit below.

**Non-owned test edits, for their owner to nod at.** Both are in
`mentat/tests/test_console_browser.cjs`, both forced, neither cosmetic:

1. `:50` — `page.route('**/api/cross-reference', …)` gained a second registration
   for the query form, the idiom that file already uses for `/api/evidence` at
   `:48-49`. Forced by the contract: the test clicks `#split-view` while Evidence is
   current (`:163`), which activates Graph; Graph now writes its industry into the
   query, so Cross-reference asks S4's industry-scoped route and the bare glob
   stopped matching. Measured, not assumed — a probe on the same fixture with no
   industry in the URL still requests the bare route and still renders "Observed
   original giving".
2. `:196` — a `waitForFunction` was inserted before the run-group assertion. That
   attribute is set by `renderRunLibrary()` (`app.js:217-227`), which runs only
   after `mentat:view` → `poll()` → `refreshRuns()` →
   `fetch('/api/runs?include_archived=1')` (`app.js:252`) comes back, and no wait
   sat between the `#tab-collection` click at `:195` and the read. **It is a race,
   not an S5 defect**: measured on byte-identical trees as pass, pass, **FAIL**
   (`'false' !== 'true'` at `:196:12`), plus the sweep's red under load; S5 adds no
   request on that path. The wait uses the file's own idiom (`:162`, `:173`) and the
   assertion is unchanged. After it: two consecutive runs, exit 0 and exit 0.

**Foreign facts, recorded because they are not S5's to fix:**

- **HEAD moved under this lane mid-build.** `server.py` was clean when S5 checked
  it, carried five foreign hunks by 00:29:56 (S3d's HTTP/1.1 and `read_json_cached`
  work), gained S5's one `STATIC_ASSETS` line at 00:43:04, and at **00:49:02 Paul
  committed `a565216bf`**, which carries all six. So **S3d's commit shipped S5's
  `/scope.js` line** under a message that does not mention it, `server.py` is clean
  again, and the S5 patch carries no `server.py` hunk. Every S5 measurement was
  taken against exactly those bytes.
- `mentat/app/graph_data.py`, `report_insights.py`, `style.css`, `graph.css` and
  `desktop/Launcher.cs` are modified-uncommitted by other lanes right now. S5
  touched none of them, and the build stamp above therefore describes a tree that
  includes those foreign edits — it will not reproduce from a clean checkout of
  HEAD plus this patch alone.

**Open for Paul:**

1. Commit from `patches/S5_url_scope.patch` (`git apply --cached`, as S4's went in;
   the ignored `.json`/`.txt` files need that or `git add -f`).
2. Restart the consoles: `scope.js` is a **new static asset**, so the assets stamp
   changes and a console that predates it serves an `index.html` whose
   `<script src="/scope.js">` would 404 on the old process. Expected identity after
   the restart is the pair above.
3. Cross-reference industry scoping (under "User-visible changes") — intended, but
   it changes what that tab shows after a Graph visit.
4. The two non-owned `test_console_browser.cjs` edits: does the contract change
   carry them, or do they need their owner's nod?

---

### HANDOFF NOTES FOR S6 — the URL vocabulary, verbatim

**The rule.** The hash names the tab (`app.js showView`, `#loading`,
`#collection`, `#graph`, `#chart-studio`, `#cross-reference`, `#evidence`). The
query string carries the scope. A fragment-only `replaceState` keeps the query, so
the two never fight. `pushState` is used nowhere and ruling C says keep it that way.

**Every key** is in the table above, with its value rule, its writer and its
reader. **Ownership, which is the part that matters for a second pane:**

- **Graph owns** `company`, `cycle`, `mode`, `direction`, `tier`, `funding`,
  `category`, `recipient`. It writes all eight from one place, `writeScope(query)`
  in `graph.js`, mirroring the `/api/graph` request it just made.
- **Chart Studio owns** `industry` **on pick** (inside `selectContributionDataset`,
  so all four call sites are covered) and `saved`. Graph also writes `industry`,
  from its own select — last writer wins, and both spell it the same way because
  the contract pins the published label.
- **S6 owns** `evidence`, `id`, `committee`, `offset`, `limit`. S5 writes none of
  them and `write()` preserves them in place.

**The module**, `mentat/app/scope.js`, browser global `MentatScope`, CommonJS in
node (UMD like `chart-studio-core.js`):

```js
read(search = location.search)  // -> {industry?, company?, ..., invalid: [{key, value, reason}]}
write(partial, {location, history, dispatch, target} = defaults)  // -> the new scope
parse(search)                   // the pure read
serialize(scope)                // the pure write, keys in KEYS order
href(view, scope, base = location)   // "/?<query>#<view>"
subscribe(fn, target = window)  // popstate + mentat:scope; returns an unsubscribe
KEYS, MODES, RESERVED           // the vocabulary as data
```

`read()` never throws: a value it refuses is dropped from the scope and reported in
`invalid[]`, because a bad permalink must still open its tab. `write()` merges into
the live query - an empty, null or undefined value removes its key, unknown keys
are preserved in place, existing keys keep their order, new keys append - then
calls `history.replaceState` and dispatches **`mentat:scope`** (a `CustomEvent`
whose `detail` is the new scope) **only when the URL actually changed**. A no-op
write dispatches nothing, which is why `showView` does not call `write({})`.

**Extending it to a two-pane URL.** S3's pane model (this file, the "Pane state
model for S6" section around lines 1173-1188) already commits the evidence pane to
`?evidence=csv&id=…&committee=…&cycle=…&offset=…`, and those keys are the reserved
list above. Two things to keep when you build it:

- A second pane's keys should be **prefixed, not duplicated** (`paneB.cycle`, the
  shape S5_DESIGN.md §2 anticipated), because `cycle` already belongs to Graph and
  a bare second copy would make "whose cycle is this?" unanswerable. `write()`
  preserves any prefixed key untouched today, so the prefix costs nothing now.
- Add the new keys to `contracts/url_scope.json`, bump its `version`, and re-run
  both suites. `app/tests/scope.test.js` reads the contract from disk, so new
  examples and negative controls are picked up without touching the test.

**Restart requirement.** `scope.js` is a new entry in `STATIC_ASSETS`
(`server.py`, grep `'/scope.js'`), so `ASSET_TREE_SHA256` changes and a console that
predates it serves an `index.html` referring to a script it will 404. Restart
before judging anything in the browser:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\pgoff\Mentat\mentat\app\Start-MentatApp.ps1 -Port 8806
```

D-029 applies: the launcher replaces only an IDLE stale console, so check
`/api/health` before assuming a restart took.

---

## S6 — Surface (dashboard / dataviz)

**Status:** not started

**Files owned:** to be claimed. S6 must not claim a file still held by an
in-progress session.

**Patches:** —

**Contract decisions:** —

**Open questions:** —

**Handoff notes for later sessions:** —








---

## S3 — PAC evidence ingestion (Area C)

**Session:** Fable, worktree evidence-csv-fetch-streaming-8bedff, 2026-09-16 (15:30–22:00 ET).
**Status:** BUILT, receipts ready, UNCOMMITTED. Paul applies. One verification still
open at write time (browser step 5, see "Tests" below).

**Precondition record.** S0's status was "receipts ready" and the packet directory was
untracked when S3 booted; on Paul's "commit it, then go" the packet was committed as
`11654f911` (44 files, `git add -f` because the root `.gitignore` eats `*.json`/`*.txt`).
S2's own commit `d78cf0b8f` landed on the branch between that and S3's first edit; it
touched no `mentat/app/` file. S3's four source files were clean at both hashes.
`git diff -- mentat/app/server.py` before S3's edit: empty (receipt
`S3_server_py_diff_before.txt`); after: exactly four hunks, +73/−27, at `@@ -884`
(collect_evidence messages), `@@ -1274` (Console evidence methods), `@@ -1729` (GET
route), `@@ -1851` (streaming POST branch) — `S3_server_py_diff_after.txt`.

**What S0's Area C actually said, and what S3 did about it.** No fetch failure
reproduced. Finding 1 (imports live in one process's dict and vanish on same-port
restart, launcher stale-stop or port hop, leaving "This CSV import is unavailable in the
current app session") and Finding 2 (JSON POST of the whole file parsed synchronously on
the request thread, 3.7–15.5 s for 4.95 MB, peak 11.8×, retained 7.8× forever) are both
closed by one mechanism: an on-disk import store under the console data root, which every
launcher-started console shares.

**Files changed (S3-owned):**
- `mentat/app/evidence_csv.py` (245 → ~830 lines): constants `MAX_BYTES = 50_000_000`,
  `MAX_COLUMNS = 200` (kept), `MAX_ROWS = 500_000`, `CHUNK_BYTES`, `KEEP_IMPORTS = 10`,
  `KEEP_BYTES = 250_000_000`, `PAGE_LIMIT = 1000`; `limits()`, `page_args()`,
  `decode_name()`; `Upload` (chunked write, byte gate applied before the crossing chunk,
  incremental UTF-8 decode, running sha256, abort-on-refuse so the handle never blocks a
  delete); `Store(data_root, evict=True)` with `begin_upload / job / wait / sources /
  catalog / select / ingest_text`; ingest runs in one background thread per console,
  streams `csv.reader` over the file, checks `MAX_ROWS` before normalising each row,
  writes rows to `rows.sqlite` in 1,000-row batches as `csv_rows(row_number, line_num,
  committee_id, cycle, status, channel, amount, cells JSON)` plus a Decimal-exact
  `totals` table; `select()` rebuilds only the requested page through the pure `rebuild()`
  → `normalize()` path. Import id = `csv-` + sha256(bytes)[:32] (same file, same id on
  every console). Legacy `parse/catalog/select/normalize` remain importable and run over
  the same reader. The ceiling comment justifies 50 MB on measured disk figures only
  (ingest seconds are NOT certifiable on this host, see Measurements).
- `mentat/app/server.py`: the four hunks above. Streaming branch sits inside `do_POST`'s
  `try:` before the 7 MB generic gate; `Content-Length > MAX_BYTES` is refused without
  reading the body; short read → `M_SHORT`; legacy JSON `{name,text}` still accepted
  (synchronous, returns the old CATALOG shape). GET: `?job=` polling, `limits` in the
  listing, `page_args()` instead of bare `int()` (DEFECT-INT-LEAK closed).
  `collect_evidence` failure message now `Collection failed: <last log line>. Full log:
  <path>` and `Could not start the evidence collector: <OSError>`. `csv_imports` is gone;
  `evidence_store` is a lazy accessor passing `evict=not read_only`.
- `mentat/app/evidence-csv.js` (69 → 163 lines): raw-body `fetch` with the File as body
  (no `file.text()`), pre-flight from the server's `limits` (no size literal in the file),
  `?job=` polling at 500 ms with a progress line, a JS-built `#evidence-csv-source`
  picker listing previous imports, every failure path writing file-or-URL plus reason to
  `#evidence-csv-status`, new provenance sentence.
- `mentat/tools/pac_evidence.py`: `Client.page` reports `FEC evidence request failed:
  <reason>; URL <url>` for HTTPError, URLError, timeouts and non-JSON bodies; retries
  transient classes with the existing backoff; cache-integrity message names the path.

**Contracts (DE-021):** `contracts/evidence-csv-import.json` (LIMITS, JOB reading/ready/
failed, listing, SELECT) and `contracts/evidence-job-status.json` (collector job states),
asserted against the real producers in `test_evidence_csv_stream.py::
test_contract_examples_against_producers` with six negative controls that fail the
helper. Both JSON files are gitignored: commit with `git add -f`.

**Tests (fail before, pass after):**
- `tests/test_evidence_csv_stream.py` (18 tests): pristine HEAD `11654f911` → 1 failure +
  18 errors (`no attribute 'Store'`), receipt `S3_before_python.txt`; live tree → 18/18,
  `S3_after_python.txt`.
- `tests/test_pac_evidence_errors.py` (7): 5/7 red before, 7/7 after
  (`S3_pac_evidence_errors_before/after.txt`).
- `tests/test_evidence_csv_browser.cjs` (Playwright, spawns `app/server.py` on a free port
  with a temp data root; never 8802/8806/8808): pristine HEAD → red at step 4 (old client
  never emits the new status), `S3_before_browser.txt`. Live tree, run under host load
  with a second verifier active → steps 1–4 pass, step 5 (6 MB import) timed out at 60 s
  twice without the status text being captured (`S3_after_browser_run1_contended.txt`).
  Diagnosis on a quiet host was IN FLIGHT when this section was written: either host load
  (this box had 1.6 GB of 31.5 GB free; identical 6 MB ingests measured 0.82–34.66 s) or a
  client defect in `evidence-csv.js`. Whichever it is, `S3_after_browser.txt` is the
  receipt; treat the client rewrite as UNPROVEN until that file shows the run green.
- Pre-existing suites: `tests.test_pac_evidence` 10/10 (unchanged); `tests.test_evidence_csv`
  (UNTRACKED, unowned) 10/10 → 9/10: the failing test pins "no files written" and "a
  restart forgets", i.e. the defect S3 removed. Proposed fix in `patches/
  S3_proposed_test_evidence_csv_pin.patch` (proven 10/10 on a temp copy).
  `tests/test_console_browser.cjs` (tracked, modified by another lane, already red at :188
  per S0) now also fails at :87 on the old "no larger than 5 MB" assertion; proposed fix
  `S3_proposed_test_console_browser_limit.patch`. `index.html:343` still says "up to 5 MB"
  (visible only until the first GET returns); proposed fix
  `S3_proposed_index_html_limit_text.patch`. All three apply with `git apply --check`
  exit 0; none applied (files outside S3's ownership).
- DEFECT-KEYSTORE (1,975 tracebacks, log dated 09-11) was ALREADY CLOSED at HEAD: the
  once-per-response catch in `summary()` landed 2026-09-13 in `2906980d1`, the POST
  handler 09-08 in `4f6a6f564`. S3 pins it with `test_keystore_failure_reported_once`
  rather than re-fixing it.

**Real-client pass (criterion 7, DE-021):** `S3_real_client_pass.txt`. Writable console on
port 8943, temp data root: streaming import, `?job=` progression 0 → 14,977 rows, limits,
100-row page with `has_more`, `?offset=abc` → exactly `Choose a valid CSV row page
(1–1,000 rows).`, unknown id → M_GONE, `Content-Length: 60000000` → M_BYTES, short read →
`The upload ended early: 54 of 5,000 bytes arrived.`, legacy JSON import, no-token 403,
and ONE real `POST /api/evidence-collect` (Coinbase, C00835959, cycle 2026) → completed
in ~10 s, wrote `mentat/.cache/pac-evidence/snapshot-2eb1b6d618fa4595b4ddbe8043753ede/`
(collection.log, collection.json, evidence.json 16 KB, snapshots.json 1.5 MB, 10 source-
cache files; 13 receipt legs, 11 transfers, 3 candidate activities, IE totals reconcile).
Two deviations in that receipt, stated plainly: its generated file was 390 KB, not 6 MB,
and it deferred the restart-on-another-port step. Both are covered by
`S3_smoke_server.txt` FINAL RUN (6,000,146-byte streaming POST; restart on 8902 with the
same data root lists both imports and serves their rows).

**Measurements (receipt `S3_smoke_server.txt`, three dated sections; the FINAL RUN is
the shipped code):** streaming POST returns in 0.078 s for 6,000,146 B (the request thread
only copies bytes; S0 measured 3.7–15.5 s for 4.95 MB); oversize refused in 0.015 s
without reading; `rows.sqlite` 9,498,624 B for a 6,000,146 B source = 1.58× (was 5.06×
before the cells-only payload); 100-row page 15–16 ms (46–47 ms at offset 7,000); disk per
50 MB import ≈ 129 MB; behind `KEEP_BYTES` 250 MB ≈ 645 MB total. Ingest seconds were
NOT certified: nine identical 6 MB ingests spanned 0.82–34.66 s with 1.6 GB RAM free, so
the ceiling is justified on disk and on the request-thread cost only.

**Contract deviations shipped (accepted):** local `atomic_json` in `evidence_csv.py`
(server.py defines its own; `tools/` is not on `sys.path` at import); `decode_name()` in
the module instead of a server.py import edit; `Upload.write` aborts before raising;
table named `csv_rows`; `catalog/select` on a still-reading import raise `M_BUSY`; a
failed ingest deletes `source.csv`/`rows.sqlite` and keeps `import.json` for the message;
the every-1,000-rows progress write uses one attempt inside `try/except OSError` so an
open handle can neither slow nor fail an import.

**Unchanged by ruling (PACKET S3 criterion 8):** `SO_REUSEADDR`, the snapshot store
location (`PROJECT/.cache/pac-evidence`, still keyed on the repo path), the startup
`save_keys` call.

**Open for Paul:**
1. Apply `patches/S3_pac_evidence_fixes.patch` (145,242 B, 9 files, +2562/−97, proven
   `git apply --check` exit 0 on `d78cf0b8f` in a throwaway worktree, then compiled) — or
   commit the live files directly; contracts and receipts need `git add -f`. If S's
   browser diagnosis edited `evidence-csv.js` or the `.cjs` after 21:30 UTC, regenerate
   the patch first (`git diff` on the four tracked files + `git diff --no-index` on the
   five new ones).
2. The three proposed patches for unowned files (above).
3. `MAX_ROWS` 50,000 → 500,000 and `KEEP_BYTES` 250 MB (~645 MB on disk) — S3's calls,
   reversible by editing two constants.
4. Read-only previews write imports into the shared data root but never evict; a
   preview can still see and select the main console's imports (by design of the shared
   store; say if that is unwanted).
5. Consoles 8806 (and any 8802/8808 relaunch) predate every server.py edit and must be
   restarted to serve the new routes; the F1 launcher restarts an idle stale console.

**Pane state model for S6 (two-pane comparison; NOT built here):** the evidence CSV pane's
whole state is `{source: 'csv', id: 'csv-<32hex>', committee, cycle, offset, limit}`; the
snapshot pane's is `{source: 'snapshot', id: '<snapshot dir name>', cycle, committee,
mode: 'saved' | 'graph'}`. What S3 leaves for S6: (a) ids are content-addressed, so the
same file gives the same id on every console and data root — a second pane on another
port can address an import by id without a file input; (b) `GET /api/evidence-csv` lists
the ready imports with their catalogs, so a pane can populate from the id alone;
(c) `evidence-csv.js` keeps `source`/`offset` closure-private today — S6 must expose
`getState()/setState(state)` on the module and round-trip the state through the URL query
(`?evidence=csv&id=…&committee=…&cycle=…&offset=…`) so two panes can be driven and
compared; (d) the status line contract (file-or-URL plus reason, never blank) must hold
per pane, so each pane needs its own `#evidence-csv-status` element or a keyed status
map; (e) `limits` are per server, identical across consoles on the same build.

**Next:** Paul restarts the consoles, applies or commits, rules on items 2–4; S6 builds the
pane state model after the cross-industry contract exists.

---

### S3 addendum — cap raised to 500 MB, follow-up patches applied (2026-09-16 evening)

The S3 section above (both the stub at line ~727 and the full write-up at the end of
this file) says "BUILT, receipts ready, UNCOMMITTED." That predates commit `303409192`,
which landed S3 on this branch; this addendum is a second, separate pass on top of that
commit.

**Paul's ruling:** "Apply all, and the cap should be way past 5 or even 50."

**Constants changed, in `mentat/app/evidence_csv.py`:**
- `MAX_BYTES`: `50_000_000` → `500_000_000`. The request thread only ever copies
  `CHUNK_BYTES` (64 KiB) at a time before handing off, so a larger ceiling costs the
  request thread no more time per chunk; ingest itself runs off-thread with progress
  reported to the page as rows and bytes are read. Ingest seconds are still NOT
  certifiable on this host (an identical 6 MB ingest measured 0.82–34.66 s across runs
  under memory pressure — S0's Finding 2 environment, not a property of the code), so the
  honest expectation at 500 MB is minutes, not seconds.
- `MAX_ROWS`: `500_000` → `5_000_000`. Rows live in `rows.sqlite`, not memory; the cap
  only bounds ingest time and page offsets, and scales with `MAX_BYTES`: at roughly
  100 bytes/row, 500 MB is about 5,000,000 rows.
- `KEEP_BYTES`: `250_000_000` → `1_000_000_000`. This is an eviction budget of source
  bytes only; `KEEP_IMPORTS` stays `10`.

**Disk arithmetic (unchanged measurement, rescaled):** the design measured here stores
only cells and recomputes `normalize()` per page, at 1.58× the source in `rows.sqlite`,
so one import costs source + 1.58× source ≈ 2.6× the source in all. At the 500 MB
ceiling that is about 1.3 GB of disk for one import; behind `KEEP_BYTES` = 1 GB of kept
sources, the sqlite databases behind them add roughly another 1.58 GB, about 2.6 GB kept
on disk worst case. The generic 7 MB JSON body gate in `server.py`'s `do_POST`
(`Content-Length > 7_000_000`) is unchanged and still bounds the legacy in-request JSON
import path only; the streamed CSV path answers to `MAX_BYTES`.

**Three proposed patches applied, in this order (all were `git apply --check` clean
before applying):**
1. `patches/S3_proposed_index_html_limit_text.patch` — `index.html`'s
   `#evidence-csv-status` resting text no longer states a size number; the console
   states the size limit when a file is chosen, from the server's published `limits`.
2. `patches/S3_proposed_test_evidence_csv_pin.patch` — `mentat/tests/test_evidence_csv.py`
   is now git-tracked (added by this commit); the renamed test
   `test_csv_http_is_authenticated_and_available_in_read_only_mode` pins that an import's
   on-disk record exists and that a restart remembers it, replacing the old
   "memory only / a restart forgets" assertions that pinned the pre-S3 defect.
3. `patches/S3_proposed_test_console_browser_limit.patch` — `mentat/tests/test_console_browser.cjs`
   lines ~86–87 now assert the server-published limit instead of the old "no larger than
   5 MB" literal. This lane then re-edited that same assertion a second time, past what
   the patch itself did, to the 500 MB cap: the oversize input is now a
   500,000,001-byte SPARSE temp file (open + `ftruncateSync`, no real write) passed to
   `setInputFiles` by path, not a `Buffer.alloc(...)`, so the case stays fast at the new
   ceiling; regex now `too-large.csv (500.0 MB): Choose a CSV no larger than 500 MB.`.
   This file already carried unrelated, uncommitted hunks from another lane (navigation,
   coverage-panel and keyboard-nav checks) before S3 touched it; those hunks are untouched
   by this addendum and are included in the receipt patch only because the file as a
   whole changed.

**Also updated for the new cap (not from the proposed-patches packet):**
- `contracts/evidence-csv-import.json`: the `limits` example now reads `max_bytes:
  500000000`, `max_rows: 5000000`, and the matching `_message` strings.
- `mentat/tests/test_evidence_csv_stream.py`: `test_oversize_rejected_while_streaming`
  now narrows `evidence_csv.MAX_BYTES` to `2_000_000` for its own duration (restored in
  `finally`) instead of writing 500 MB per run, and asserts the live
  `csv_data.bytes_message()` (`'Choose a CSV no larger than 2 MB.'`);
  `test_http_streaming_roundtrip`'s oversize `Content-Length` case now asserts the live
  `csv_data.bytes_message()` instead of a hardcoded 50 MB string.
- `mentat/tests/test_evidence_csv_browser.cjs`: the `big.csv` pre-flight fixture is now a
  500,000,001-byte sparse file (open + `ftruncateSync`, no 500 MB write); the expected
  status regex is `big.csv (500.0 MB): Choose a CSV no larger than 500 MB.`. The sparse
  file worked on the first try in this lane's runs — Playwright's `setInputFiles` by path
  read only `file.size` and issued no request, so the documented Buffer fallback was not
  needed.

**Tallies (full output in `receipts/S3_cap500_after.txt`):**
- `python -m py_compile` on `evidence_csv.py`, `server.py`, `test_evidence_csv_stream.py`,
  `test_evidence_csv.py`: exit 0.
- `node --check` on `evidence-csv.js`, `test_evidence_csv_browser.cjs`,
  `test_console_browser.cjs`: exit 0.
- Leftover-literal grep over `evidence_csv.py`, `evidence-csv.js`, `index.html`,
  `server.py`: 4 hits, all expected and unrelated to the evidence-CSV path —
  `evidence_csv.py:78` is the new `MAX_ROWS = 5_000_000` itself; `index.html:39` and
  `server.py:594-595` are the separate roster-file upload's own "up to 5 MB" / `5_000_000`
  gate (a different feature, out of S3's scope, untouched).
- `tests.test_evidence_csv_stream`: 18/18 OK.
- `tests.test_evidence_csv`: 10/10 OK (this suite is now tracked; the pin patch's
  renamed test is included and passes).
- `tests.test_pac_evidence` + `tests.test_pac_evidence_errors`: 17/17 OK (10 + 7).
- `node tests/test_evidence_csv_browser.cjs`: 19/19 steps PASS, exit 0 — including step 9
  (the sparse `big.csv` rejected client-side at the new 500 MB cap, zero uploads issued).
- `node tests/test_console_browser.cjs`: the receipted run passed end-to-end
  ("Browser checks passed…"), exit 0, including the :87 assertion this lane rewrote for
  the 500 MB cap. Note for the next session: a separate, non-receipted run earlier the
  same evening failed at a different, unrelated assertion (`[data-run-group=history]`
  `aria-pressed`, around line 195, inside the other lane's in-progress run-group UI work)
  — :87 had already passed in that run too before the unrelated failure. This looks like
  the flakiness this file's own comments already describe elsewhere in the repo, not a
  regression from this addendum; it was not investigated further here because it is
  outside S3's ownership.

**Receipts:** `receipts/S3_cap500_after.txt` (commands, HEAD, UTC date, exit codes, full
output for every command above). **Patch:** `patches/S3_cap_500MB_and_followups.patch`
(`git diff --no-color` of the six tracked files this addendum changed, plus
`git diff --no-index` for the newly-tracked `mentat/tests/test_evidence_csv.py`;
`git apply --check -R` from the repo root: exit 0).

---

### S3b addendum — any file type, any path (2026-09-16 night)

**Paul's report after the S3 commits:** "still failing to fetch. It cannot look at files other than CSV files … should be able to look anywhere in a computer." Root cause was the file type, not the transport: `index.html:343` carried `accept=".csv,text/csv"`, the server refused any name not ending `.csv` before reading a byte, and non-UTF-8 text was refused. Paul: "Go, do all, get this done."

**Built (this commit):** a reader layer in `evidence_csv.py` feeding the unchanged S3 ingest: delimited text `.csv/.tsv/.txt` (delimiter sniffed among `, ; tab |`, with a steady-count override when the Sniffer is wrong; encoding by BOM, then strict UTF-8, then Windows-1252 with a catalog warning; NUL → refusal), `.xlsx/.xlsm` via openpyxl read-only (first sheet by default, `sheet` selectable, `sheets` listed, cells to text), `.json` openFEC exports (whole-file parse, capped `MAX_JSON_BYTES = 25_000_000`), FEC bulk `.zip`/pipe `.txt` with no header row (types indiv/itcont/itpas2/pas2/itoth/oth/cm/cn/ccl/oppexp; headers from a given header file, else `mentat/inputs/**/<type>_header_file.csv`, else a bundled table; zip member size gated before extraction). Anything else: `This file type (.pdf) is not supported. Choose CSV, TSV, TXT, XLSX, JSON or an FEC bulk ZIP.` Path import `POST /api/evidence-csv {"path","sheet","header_path"}` copies the file into the store and ingests off-thread; directory browser `POST /api/evidence-files {"path"}` (roots, shortcuts, entries dirs-first, 2,000 cap; token-checked, POST-only because `do_GET` has no token check). Client: picker without `accept`, path box, header-file box, "Read this file", "Browse…" panel, worksheet picker. Import ids unchanged for CSV (`sha256(bytes)`), `sha256(bytes + NUL + sheet)` for a named sheet. JOB/CATALOG gain `format, source_kind, source_path, sheet, sheets, encoding, delimiter, header_source`; S3-era records are back-filled on read.

**Evidence:** `tests/test_evidence_readers.py` 38/38 (red on 91fe7402a: no `import_path`/`browse`), stream 18/18, legacy 10/10, collector 7/7; `receipts/S3b_smoke_server.txt` 53/53 + 19/19 on scratch ports (2-sheet workbook, tsv, pipe txt, Windows-1252, json, a real-shaped `itcont.txt` inside `indiv26.zip`, `.pdf` refusal, path import, missing/folder refusals, browse of roots and `C:\Windows\System32\config` → permission denied). `receipts/S3b_server_py_diff_before.txt` shows server.py already carried the S4 lane's 128 uncommitted lines; this commit staged ONLY the four evidence hunks (+40/−2) via a context-anchored patch proven against a throwaway index.

**Open for Paul:** (1) FEC bulk rows import but stay `unsupported` because `normalize()` does not read `TRANSACTION_TP`; the code-to-channel mapping is a data rule — proposal in `receipts/S3b_bulk_channel_proposal.md`. (2) `browse`/path import read anything this Windows user can read; local-only by Host/Origin/token, never to be moved to GET. (3) Restart the consoles to serve the new picker and routes.

**Follows in the next commit:** the extended browser test (`test_evidence_csv_browser.cjs` steps 20+: xlsx/tsv/json/1252/bulk/pdf/path/browse) with its red-before and green-after receipts, and `receipts/S3b_real_client_pass.txt` (real workbook from `mentat/inputs` by path, Downloads browsed in Chrome, restart on another port).


### S3c addendum — Paul's workbook reads; UI put back; code review (2026-09-16 late night, Fable directly)

**Paul after restarting on 21c9cab6d:** "the UI should not have changed" and "it says it is reading 0 rows". Then: "do it as fable" — no agents from that point; the remaining work in this section was done by Fable in the main session.

**Cause of the 0-rows import (from his console's own record, `%LOCALAPPDATA%\Mentat\console\evidence-csv\csv-a6591d…\import.json`):** `Credit Union Industry Spending Overview.xlsx` (15,113,389 B) was uploaded at 22:35:11 and refused 2.2 s later with `The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.` The workbook has 26 sheets; sheet 1 "Master Overview" starts with a title row, so the S3b reader's header was `['credit_union_master_overview']`. The data lives in `2021-2022`, `2023-2024`, `2025-2026`, `Cycle Exceptions` (identical 35-column header on row 4: Committee ID, Recipient Key `FEC:C…`, Amount, Date, Cycle, Record Type `CONTRIBUTION`, Contributor, Recipient …), with aggregate sheets beside them (`Downstream Activity`: Source Committee ID + Net Included Amount + Support / Oppose).

**Fixed (committed by the commit this section rides in):**
- `evidence_csv.py` workbook reader: `header_row()` = first row within 50 whose keyed cells name a committee column, else the first row with ≥ 3 filled cells, else the first non-empty row (delimited text unchanged); `sheet_grade()` ranks every sheet (3 = committee + amount + date, 2 = committee + net_included_amount, 1 = committee only); the best sheet wins (ties by row count, then workbook order) and every sheet with the identical keyed header is read after it as one table; `sheets_read` recorded on the JOB/CATALOG with the warning `Read N worksheets with the same columns: …`; a workbook with no qualifying sheet fails with `No worksheet in this workbook has a Committee ID column. Sheets: …`; `sheets` is written onto the record before anything can fail. Naming a `sheet` still reads only that sheet.
- `TYPES` gains `'contribution': 'receipt'` (Mentat's own Record Type label), `NAME_FIELDS` gains `recipient`, the counterparty fields gain `contributor`. FEC bulk `TRANSACTION_TP` mapping is still Paul's (proposal in `receipts/S3b_bulk_channel_proposal.md`).
- Warnings: `select()` now returns the stored catalog's warnings (the Windows-1252 and combined-sheets notes reach the page); the legacy `catalog(document)` carries the document's warnings.
- Zip members are read through `BoundedBytes` so a lying zip header cannot stream past `MAX_BYTES`; the streaming route refuses a non-numeric `Content-Length` with a sentence instead of Python text.
- UI: `index.html` line 343 is the 91fe7402a block again with only `accept=".csv,text/csv"` removed (label "Choose CSV" unchanged); no path box, no browse panel, no sheet picker. `evidence-csv.js` keeps the any-type upload and is guarded so the removed controls' absence is a no-op; the path route and `/api/evidence-files` stay server-side, unused by the page. Progress reads `Reading <name> · opening the workbook…` while a workbook is being opened.

**Measured on Paul's real workbook** (`import_path`, temp store, this host under load): request returned in 0.06 s; ready in 130.7 s; `sheet` `2021-2022`, `sheets_read` the four cycle sheets; 27,632 rows, 27,430 supported, 202 unsupported; 264 committees with names; cycles 2026/2024/2022/2020; `C00007880` in 2024: 232 rows, Receipts $9,064.59; first row dated 2024-12-31 with the recipient's name.

**Tests:** `tests/test_evidence_readers.py::MentatWorkbookSelection` (3 cases: cycle sheets chosen and totalled as receipts; explicit aggregate sheet; workbook with no committee column names its sheets — red before, green after); `test_xlsx_first_sheet_default` now expects the 2-sheet fixture read as one 3-row table; JOB/CATALOG key sets and both contract fixtures gain `sheets_read`. Tallies after: readers 41, legacy 10, collector 7, stream 18. Browser `.cjs` cut to picker-only steps (2-sheet workbook as one table, tsv, json, Windows-1252 warning, FEC bulk zip, `.pdf` refusal, a Mentat-shaped workbook with title rows and two cycle sheets, and an assertion that none of the S3b path/browse/sheet controls exist); result in `receipts/S3c_after_browser.txt`.

**Code review** (Paul's `/ecc:code-review`, Fable): `receipts/S3c_code_review.md` — REQUEST CHANGES at review time (three HIGH items = the three fixes above, now landed), no CRITICAL; the trust boundary of the path/browse routes holds (POST-only, Host + Origin + constant-time token; `do_GET` has no token check). Deferred LOW/MEDIUM items are listed there (resolved `source_path`, the `it is not a folder` wording, a future split of the reader layer into its own module).

**Process note for the record:** the Opus architect dispatched for this fix ran 26 minutes without writing a byte and was stopped; the Haiku scout was stopped on Paul's order. Verify agents' claims against the tree before relying on them (T2's "33 passed" did not survive a fresh run).


### S3d addendum — startup and workbook latency (2026-09-17 early, Fable directly)

**Paul:** "The app startup itself is incredibly slowed and needs a dramatic reduction in latency"; "The pace at which the system reads the spending overview is incredibly slowed and needs to be speeded up"; split view means several PACs side by side (S6); "These should also be graphable". Then "Go, and yes" (yes = python-calamine into the launcher's Python).

**Startup, measured on his console 8806 before:** page load 10.8 s; the 30 static files took 5.2 s because the handler spoke HTTP/1.0 with Nagle on (one connection per file, two-segment responses hitting Windows' delayed-ACK stall); `/api/runs?include_archived=1` 3.1 s because every run's status file was re-parsed on each call; `/api/session` 3.2 s; process cold start 4.7 s (3.1 s imports, 1.0 s of it openpyxl via report_insights — untouched, another lane's uncommitted file). **After** (scratch console from the patched server on his real data root): page load 1.2 s / 1.5 s; static files 0.7 s; `/api/runs` 0.56 s then 0.3 s; `/api/session` 0.6 s. Changes in `server.py`: `Handler.protocol_version = 'HTTP/1.1'`, `disable_nagle_algorithm = True`; `read_json_cached()` keyed by (path, size, mtime_ns) used by `runs()` (three call sites). Every response already carries Content-Length and every early refusal drains the body, so keep-alive is safe; the streaming refusal sets `close_connection`.

**Workbook read:** before 16.1 s (openpyxl + lxml, launcher Python; 130 s under load). Profile: 21 of 30 s openpyxl XML parsing, normalisation 28 µs/row when the host is quiet. `python-calamine` 0.8.2 (Rust) converts the four cycle sheets in 1.17 s and surveys 50 rows of the largest sheet in 0.00 s. Installed into the launcher's Python; `evidence_csv.workbook_reader` now dispatches to `calamine_reader` (50-row survey of every sheet, full conversion only of the chosen table, one sheet at a time) with `openpyxl_reader` as the fallback; the record carries `engine`. Same results from both engines (27,632 rows, 264 committees, C00007880/2024 = 232 rows, $9,064.59). Measured after: 8.7 s on the best run; 15 to 28 s while other sessions thrashed the host; expected 3 to 5 s on a quiet host. Threads do not help calamine (GIL held; shared handle raises "Already borrowed"); a process pool was not added because normalisation is under a second when the host is quiet.

**Records:** `receipts/S3d_latency.txt` (all numbers), `receipts/S3d_after_browser.txt` (30/30). Tests: readers/legacy/collector 58 OK under both Pythons (calamine and fallback), stream 18 OK on HTTP/1.1, browser 30/30.

**For S6 (pane state model, added to the S3 section's list):** split view = two or more PACs side by side, from the same import or different imports (each pane = `{source, id, committee, cycle, offset, limit}`); and the imported rows should be graphable: register a ready import as a Chart Studio data source with committee, cycle, channel, amount, date and counterparty as fields, so the studio's existing engine charts them without a new renderer. Neither is built here.

**Paul's next step:** restart 8806 (and 8802) to get the fast handler and the calamine reader; the first restart is the real startup measurement on a quiet console.


### S3e addendum — launcher and server cold start (2026-09-17 ~02:30 ET, Fable directly)

**Paul:** "I need start-up latency to be dramatically reduced, work on optimizing all of this."

**Measured (receipt `receipts/S3e_startup.txt`):** the launcher took 10.0 s to its ready line on a scratch port; a second Python process spawned only to check for openpyxl cost 5.5 s on this loaded host (a bare interpreter start was 2.8 s), ten bind probes 1.4 s, PowerShell's `Invoke-RestMethod` 1.1 s on its first call (`Invoke-WebRequest` 15.7 s), and the server's own cold start 4.7 s because three top-level imports (report_insights, graph_data, comparison_data) pulled openpyxl and numpy before any request needed them.

**Changed:** `server.py` imports those three modules lazily through wrappers that keep the same attribute names (tests patch them by name), and runs `git rev-parse` on the first health call instead of at import. `Start-MentatApp.ps1` checks for openpyxl with a `Test-Path` of `Lib\site-packages\openpyxl` beside the interpreter (process check kept as fallback), takes one TCP listener census instead of a bind probe per port, calls health through a proxy-free `HttpWebRequest` with millisecond timeouts, and starts the Edge app window without extensions, sync, background networking or component updates.

**After:** server process to ready line 0.48 s (was 4.66 s); `import server` 0.16 s with openpyxl, numpy and pandas absent until a workbook route runs (0.39 s once, on first use); launcher end-to-end to ready line 4.6 s with a full server start (was 10.0 s). Together with S3d: page load 1.2 s (was 10.8 s).

**Verified:** 55 tests across `test_report_directory_console`, `test_desktop_launcher` (drives the real script) and `test_evidence_readers`; stream 18. The launcher script parses under PowerShell 5.1.

**Paul's next step:** run the launcher again (not only restart the console): the launcher file itself changed.
