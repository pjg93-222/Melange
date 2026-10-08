# Cosponsorship forecast refresh: build record for A and B

Date: 2026-09-04. Lane: `claude/bill-lobbying-regression-d38c1e`, worktree `employment-tenure-adjudication-e27de8`. Paul's instruction: "Build A and B", following the design in `audits/COSPONSOR_FORECAST_SELF_UPDATE_2026-09-04.md`. The build is complete and verified in the worktree. Nothing has been applied to the live tree; an anchor-based apply script with a sandbox rehearsal is ready and waits for Paul's word.

## 1. What was built

Both steps ship behind environment dials whose default reproduces today's production behaviour, per the change-control rule that a new default must equal the empty-env state. With both dials unset, every new step still runs and writes a receipt marked `SKIPPED_DIAL_OFF`, and nothing else changes.

A. `fec/legislation/refresh_billstatus_bulk.py` (new, 391 lines). Dial `BILLSTATUS_BULK_REFRESH`. When set to 1 it downloads the eight GovInfo BILLSTATUS bulk archives for the live Congress (`https://www.govinfo.gov/bulkdata/BILLSTATUS/119/<type>/BILLSTATUS-119-<type>.zip`) to temp files inside the target directory, verifies each with `testzip()` and an at-least-one-XML rule, and only after all eight pass promotes them onto the production names. Any failure deletes the temps and leaves every existing zip untouched. HTTPS only, hostname pinned to `www.govinfo.gov`, no redirects, HTTP 200 only, streamed to disk with a hard byte ceiling. It writes `data/engine/billstatus_bulk_refresh_receipt.json` and a sidecar `BILLSTATUS-119.receipt.json` beside the zips, each listing per-archive sha256, previous sha256, and a changed flag. Wired into `fec/weekly_refresh.py` as `step('GovInfo BILLSTATUS bulk refresh', ...)` with `hard=False` and a 3600 s timeout, immediately after the Congress.gov bill repository step, and deliberately not added to the deferred-failure list that blocks dashboard publication.

B. `fec/lobbying/refresh_cosponsor_forecast.py` (new, 469 lines). Dial `COSPONSOR_FORECAST_REFRESH`. When set to 1 it loads the production report, re-hashes every path in `provenance.every_input_sha256` (353 entries today, compared case-insensitively), and scans the report's BILLSTATUS directories for any zip the report does not list. Report missing, any hash moved, any path missing, any unlisted zip, or `--force` means run; otherwise it writes `SKIPPED_UNCHANGED`. A run executes the forecaster by subprocess with `--same-chamber-only` into a staging directory under the output directory, then promotes report and scores with the previous pair kept as `.previous` until both replacements succeed. A failed run leaves production untouched. The gate itself costs about 6.5 seconds; a real run costs about 16 minutes. Receipt at `data/engine/cosponsor_forecast_refresh_receipt.json`, log under `data/engine/`. Wired into `fec/run_pipeline.py` immediately before `bill_lobbying_sidecar.py`; the chain stays network-free.

Audit check `cosponsor_forecast_freshness` in `fec/audit/audit_full.py`, printed under a new `[FCST]` heading before `[SYS]`. It calls the same `compare_inputs` function the chain gate uses, so the two cannot disagree. It passes when the report exists, every recorded input hash matches disk, and no unlisted zip exists; it fails otherwise, and it fails when the report is absent. Against live production today it passes: 353 inputs, 0 changed, 0 missing, 0 unlisted.

Tests: `fec/tests/lobbying/test_cosponsor_forecast_refresh.py` (24 tests, all on temp directories with a fake fetcher and a fake runner, no network, no live paths), registered in `run_tests.py`, whose loader walks `fec/tests` recursively. The suite proved non-vacuous during the build: it caught a leaked temp file for an archive that failed verification, which was then fixed.

Modified files, insert-only: `fec/run_pipeline.py` (+8), `fec/weekly_refresh.py` (+9), `fec/audit/audit_full.py` (+22), `fec/tests/run_tests.py` (+4). No existing test or check was weakened. No constants changed. The forecaster and the sidecar were not touched.

## 2. Verification

Independent verifier report: `<scratch>\build_ab\VERIFY_REPORT.md`, 11 of 11 items pass.

| Check | Result |
|---|---|
| Import safety of both new modules | pass |
| Dials unset write only the skip receipt | pass |
| Chain entry position and basename resolution | pass |
| Weekly step wiring, `hard=False`, not deferred | pass |
| Audit check convention and shared comparison | pass |
| Hash-gate decision rule and promotion order | pass |
| Bulk fetch security properties vs the original fetcher | pass, none dropped |
| New test module | 24 passed, 0 failed |
| `py_compile` on all 7 touched files | clean |
| Diff review against pre-edit copies | only the specified hunks |
| Audit check against live production data | pass (353 inputs, 0 changed) |

The full kernel suite, the chain, and `audit_full` were not run in the worktree, whose data plane is empty; those gates run in the live tree after apply, per the protocol below.

## 3. Apply path

The live tree's `run_pipeline.py` and `weekly_refresh.py` carry Codex's uncommitted sentinel hunks, and its `weekly_refresh.py` is LF while the other files are CRLF. The build therefore reaches the live tree by anchor insertion, never by file copy. Script: `<scratch>\build_ab\apply_ab.py`, with `APPLY_README.md` and the rehearsal transcript `APPLY_SANDBOX_RUN.md`.

Preconditions the script enforces: no running chain, weekly refresh, audit, or kernel-test process; each anchor line resolves exactly once in the live file; a hunk already in place is reported and skipped; each live file compiles before and after a simulated insertion. On apply it backs up each modified file with sha256s in a manifest, writes atomically preserving each file's own line ending, compiles everything it touched, and restores all of it on any failure. `--revert <manifest>` restores byte-identically and refuses if a file drifted since the apply. The sandbox rehearsal ran what-if, apply, a second apply (all seven reported already applied, shas unchanged), and revert (byte-identical restore). The what-if against the real live tree reports `PLAN STATUS: READY` with every anchor resolving exactly once.

Commands, run from the scratch build directory:

```powershell
python apply_ab.py --what-if
python apply_ab.py --apply
```

Post-apply verification in the live tree, in order: `fec\tests\run_tests.py`, `fec\run_pipeline.py` (both dials unset, so the new step writes a skip receipt), the rank delta check (expected 0 of 533), `fec\audit\audit_full.py` (expect the count to grow by one with `[FCST]` passing).

Enable, once the sentinel finish patch set is applied and the scheduler is re-enabled: set `BILLSTATUS_BULK_REFRESH=1` and `COSPONSOR_FORECAST_REFRESH=1` together. Enabling A without B makes the audit go red on the next weekly pull, which is the intended signal but not a useful state. Rollback is unsetting the two dials; nothing needs deleting.

## 4. Open items for Paul

1. Apply now, or hold. One word.
2. The audit check fails on an absent report. That is correct for the live tree, where the report exists; on a data-isolated box it shows one failure. Keep, or switch to skip-on-absent.
3. Publication of the eight archives is eight sequential atomic replaces after full verification. A crash between two of them leaves a partly refreshed directory, reported in the receipt with the types promoted. A directory-level swap would close the window but changes the paths other consumers read. Accept as is, or ask for the swap.
4. When to flip the two dials.

## 5. Evidence

Scratch root: `C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-employment-tenure-adjudication-e27de8\27337674-dfbb-4dce-8acd-ad49411e9dfb\scratchpad\build_ab\`

- `BUILD_RECORD.md`: conventions found with file:line, diffs, compile and test output, decisions.
- `VERIFY_REPORT.md`: independent verification, 11 items.
- `apply_ab.py`, `hunks\*.hunk.txt`, `APPLY_README.md`, `APPLY_SANDBOX_RUN.md`, `sandbox\`, `live_backup_sandbox_test\`.
- Worktree files: the three new modules and four modified files listed in section 1, uncommitted.

## 6. Brain update draft (STATE.md, Active workstream)

BILL-LOBBYING REGRESSION LANE (2026-09-04, later): A (weekly BILLSTATUS bulk refresh, dial `BILLSTATUS_BULK_REFRESH`) and B (hash-gated forecaster chain step before the sidecar, dial `COSPONSOR_FORECAST_REFRESH`, audit check `cosponsor_forecast_freshness`, 24 tests) are BUILT and verified in the worktree, both default-inert, UNAPPLIED. Anchor-based apply script rehearsed in a sandbox; what-if against live is READY. Record: `audits/COSPONSOR_FORECAST_REFRESH_BUILD_2026-09-04.md`. Apply, the two open design items, and the dial flip are Paul's.
