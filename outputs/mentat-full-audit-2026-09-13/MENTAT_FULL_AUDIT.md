# Mentat full system audit

September 12, 2026, Eastern time. Evidence directory uses the UTC date September 13.

**The audit is not clean. Two high-priority defects affect collection completeness and process termination. Six further reproduced defects affect report safeguards, reconciliation, concurrent launches and chart behavior. The shipped regression suite also has stale tests.**

This is an audit of the current working files, including uncommitted work. Production code, accepted baselines, source databases, published workbooks and running services were not changed. Reproductions used isolated fixtures. No FEC collection or report publication was performed.

## Confirmed defects

### 1. P1 — Timeout recovery can certify an incomplete collection

[R/fec_api.R:1073](C:/Users/pgoff/Mentat/mentat/R/fec_api.R:1073) invokes date-window recovery without passing the exact population count already observed from the parent query. The helper's count check is optional, so its smaller recovered count replaces the earlier count and receives `coverage_verified=TRUE`.

**Reproduction:** the original query reports exactly three records, supplies one record, then times out. All recovery windows complete and retain that observed record, but their combined population contains only two records. The result is nevertheless `complete=TRUE, coverage_verified=TRUE`.

This can label a changing or incomplete source population as complete. It violates the same stable-count rule enforced in the normal pagination path. The audit has not measured historical dollar exposure from this defect.

**Repair:** carry the observed exact count into recovery and reject inconsistent totals; preserve the failed query evidence for a fresh collection. [Reproduction log](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/reproduce_window_count_drift.R.log).

### 2. P1 — Force-stop can terminate an unrelated process through a stale PID

[app/server.py:543](C:/Users/pgoff/Mentat/mentat/app/server.py:543) falls back to the PID saved in an upload manifest, then calls `taskkill /PID … /T /F` without verifying the run is active or that the PID still identifies its original process.

**Reproduction:** a completed fixture run with no in-memory process handle and saved PID `123456` is accepted for force-stop and produces a kill command for that PID and its process tree. The kill call was mocked; no process was terminated.

After a console restart or worker exit, Windows can reuse the stored PID. A stale run can therefore target unrelated work. Confirmation that the user wants to stop a collection does not establish the identity of the process being killed.

**Repair:** reject terminal runs; persist and validate process creation identity and ownership before termination. Prefer the retained process handle when it exists. [Observed command](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/console-reproductions.json).

### 3. P2 — The publication guard accepts the wrong donor, recipient and date

[tools/report_source_guard.py:207](C:/Users/pgoff/Mentat/mentat/tools/report_source_guard.py:207) compares payload source ID, amount and cycle with the source snapshot. It omits the donor name, committee ID and receipt date, although those fields are stored as source financial facts. They are also absent from the decision comparison.

**Reproduction:** after accepting a $100 fixture receipt, a second payload changes its donor, committee and date while preserving ID, amount and cycle. Both check and acceptance return `verified`, with zero changed decisions and zero dollar delta.

A join or payload-generation regression can misattribute giving while passing the final publication check. This is a missing safeguard, not evidence that these changes occurred in the eight current workbooks.

**Repair:** compare every financial identity field at the payload boundary and record any permitted changes explicitly. [Reconciliation reproductions](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/reconciliation/reproduction-results.json).

### 4. P2 — Expanding cycle scope bypasses an earlier accepted baseline

[tools/report_source_guard.py:105](C:/Users/pgoff/Mentat/mentat/tools/report_source_guard.py:105) and [tools/run_cross_reference.py:38](C:/Users/pgoff/Mentat/mentat/tools/run_cross_reference.py:38) can inherit a broader baseline for a narrower request, but do not preserve an earlier narrow baseline when the requested scope expands.

**Reproduction:** accept a 2024 source containing $100. Prepare an all-cycle report against a source containing only a 2026 $25 receipt. The accepted 2024 receipt disappears, but the comparison reports no missing source and final acceptance succeeds.

The inspected historical pointers all cover the full cycle set, so current loss through this path was not demonstrated.

**Repair:** compare protected facts for every overlapping accepted cycle and retain concurrency tokens for each baseline used. [Detailed finding](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/reconciliation/findings.md).

### 5. P2 — Conflicting memo flags can silently remove a contribution

[tools/run_cross_reference.py:140](C:/Users/pgoff/Mentat/mentat/tools/run_cross_reference.py:140) treats an explicit blank memo flag as missing when combining observations of the same source ID. A second observation with `memo_code='X'` replaces it without a recorded conflict. The evidence store elsewhere correctly distinguishes an explicit blank from X.

**Reproduction:** a $100 child receipt has two observations, one blank and one X, and an explicit reference to a $100 parent. The combined record has no conflict, the child is excluded as a duplicate, and the review queue is empty.

**Repair:** distinguish absent metadata from explicitly blank memo flags and preserve contradictory observations for resolution. The audit checked all 32 same-ID overlap groups in the latest Banking ledger; none contains this particular conflict. [Reproduction and live-scope evidence](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/reconciliation/findings.md).

### 6. P2 — Separate consoles can accept the same collection launch

[app/server.py:389](C:/Users/pgoff/Mentat/mentat/app/server.py:389) protects launch checks with an instance-local thread lock. Separate consoles sharing the same state directory can both read `ready`, pass the active-run check, and begin preparation before either sees the other's state change.

**Reproduction:** two console objects sharing one fixture run both return `starting`; preparation is invoked twice. No collector was launched. The downstream workbook lock does not prevent duplicate runtime preparation or competing writes to the shared launch log and PID manifest.

The live snapshot found four writable consoles sharing the same state directory, making the prerequisite configuration relevant here.

**Repair:** use a cross-process claim or lock covering the ready-to-preparing transition and shared runtime preparation. [Reproduction](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/console-reproductions.json).

### 7. P2 — Standalone record inspection can disagree with its chart

[app/contribution-studio.js:231](C:/Users/pgoff/Mentat/mentat/app/contribution-studio.js:231) displays record inspection results without checking that their source provenance matches the chart already displayed.

**Reproduction:** the chart retains a $100 result from the earlier source while inspection accepts a $900 result from changed workbook/database/index provenance without an error. The main Chart Studio has a provenance check for this situation; the standalone Contribution Studio does not.

**Repair:** compare the chart and inspection source identifiers and require a refresh when they differ. [UI reproduction](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/frontend/stale-inspection.json).

### 8. P2 — Three contribution time-analysis modes crash

[app/chart-studio.js:303](C:/Users/pgoff/Mentat/mentat/app/chart-studio.js:303) constructs contribution-mode data without `row_numbers`. The shared [chart-math.js:36](C:/Users/pgoff/Mentat/mentat/app/chart-math.js:36) filter unconditionally indexes that missing field.

**Reproduction:** valid nonempty time data fails in Year-over-year %, Period change and Same-phase forecast, each with `Cannot read properties of undefined (reading '0')`. A browser fixture with eight closed years shows the error and an empty chart. Basic period totals bypass this path and work.

**Repair:** provide the shared data contract or make the transformation handle contribution rows explicitly; exercise each selectable transform through the contribution-mode adapter. [Browser and helper evidence](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/frontend/period-analysis.json).

## Regression maintenance and runtime observations

Two shipped R suites fail before reaching their intended later checks. `test_request_windows.R` supplies a response without the exact `pagination.count` now required by the implementation. `test_sqlite_lane_locking.R` expects the obsolete startup-jitter expression. Output-directory copies with corrected fixtures/expectations passed, including a real SQLite lock wait. Those supplemental results do not turn the unchanged shipped tests green.

The broad console browser test expects five navigation tabs and fails because Chart Studio is now the sixth tab. Its later assertions do not execute in that original run. Supplemental copies also encounter an obsolete legacy-chart-dialog expectation; neither passed, and neither is counted as current-product validation. The separate current Chart Studio and chart-builder tests passed.

The health snapshot found older server code loaded on ports **8802, 8803 and 8808**, alongside current code on **8804** and the read-only **8813** console. All five identify this Mentat project and the authoritative report directory. This is version drift between running services and the reviewed files. Consolidate verified idle older instances after the process-identity and launch controls are addressed. [Runtime evidence](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/runtime-health.json).

## Checks that passed

| Area | Result |
|---|---|
| Python | 500 test cases passed after rerunning two R-dependent cases with installed-package access and adapting one standalone test function to unittest. No production test was edited. |
| JavaScript unit tests | 139 tests passed across ten files. |
| Browser tests | 12 of 13 reported tests passed across all 11 shipped browser files; the original broad console test failed on stale navigation expectations. No shipped browser test timed out or was skipped. |
| R | 19 of 21 shipped suites passed; the two stale failures remain reported above. Both supplemental corrected fixtures passed. |
| PowerShell | All five shipped guard suites passed. |
| Syntax | Python parsing was clean; 48 R, 24 PowerShell and 20 app JavaScript files passed parser checks. |
| Active company roster | All seven configured industries, 70 companies and 327 aliases passed structural readiness. This does not establish exhaustive real-world alias coverage. |
| Published workbooks | All eight passed source lineage and headline cycle-total checks. All 219 worksheets were streamed: 1,033,424 worksheet rows and 3,864,656 formula cells; zero stored Excel error cells and zero literal broken `#REF!` formulas. |
| Accepted source snapshots | All seven existing accepted snapshots passed fingerprints and SQLite quick checks, covering 1,776,120 protected facts. |
| Source databases | All eight pinned source/recovery databases passed SQLite quick checks, had no missing source IDs in their scoped contribution tables, and remained unchanged during checking. |
| Latest reconciliation ledger | Banking run `20260913T025223-09b3c7578492`: report/pointer hash and full 3.60 GB ledger hash matched; SQLite quick check and all ten independently recomputed count/amount checks passed. |

The workbook scan found 9,024 formulas without a nonempty cached value. Blank-returning formulas can legitimately have that representation. This was not counted as corruption. The audit did not recalculate the workbooks in Excel or certify each formula's economic meaning.

The latest ledger contains 849,431 physical observations and 849,399 decisions. Its arithmetic reconciles, but it explicitly retains **132,890 unresolved records**, unproven collection coverage and no accepted Banking baseline. Its reported gross unresolved exposure is not a measured error, a unique-dollar total or an amount to add to giving. None of the integrity checks establishes complete unique original giving.

Seven of the eight published workbooks are dated July; Banking is dated September 10. New code and recovered metadata do not retroactively repair those published reports. Banking and Community Banks remain distinct scopes throughout this audit.

## Scope and limits

The scan covered Mentat's R collection and classification pipeline; Python orchestration, evidence storage, reconciliation, source guards and analytical queries; browser views and chart inspection; PowerShell launch/export guards; configured inputs; accepted snapshots; the latest ledger; published workbooks; and local service identities. The separate `fec/` Moneyball influence-model pipeline, historical backup trees and archived experiments were outside the Mentat subsystem audit.

All 222 fingerprinted source/configuration/test files remained unchanged during the scan, as did the eight workbooks. Source database physical checks and detailed test receipts are retained alongside this report. Audit scripts and fixture outputs are the only authored files.

This was an offline audit. It did not recollect FEC records, run a new production export, perform online dependency-advisory scanning, independently validate all ownership/filing/route evidence, or establish that historical amounts are correct. Confirmed control defects are separated from observed live data errors and declared accounting limitations.

**Recommended order:** fix false collection certification and unsafe PID termination first; repair publication identity and scope protection; align memo-conflict treatment; then add the cross-process launch claim and correct chart inspection/transforms. Restore the stale regression tests and replay the isolated counterexamples before any fresh collection or report publication.

## Evidence

- [Scan summary](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/scan-summary.json)
- [Consolidated validation results](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/final-validation.json)
- [Collection audit](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/collection-audit.md)
- [Reconciliation audit](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/reconciliation/findings.md)
- [Frontend audit](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/frontend/AUDIT.md)
- [Python test receipts](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/python-results.json)
- [Workbook scan](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/workbook-scan.json)
- [Workbook/source checks](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/source-checks.json)
- [Source database checks](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/source-database-checks.json)
- [Live ledger checks](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/reconciliation/live-ledger-check.json)
