# Mentat collection and orchestration audit — 2026-09-13

The current working tree has one confirmed collection correctness defect: a timeout fallback can certify a different population from the exact count already observed. Two shipped R tests also need maintenance. This audit made no production code or source-data changes and made no FEC requests.

## Confirmed finding

**P1 — Timeout fallback drops the previously observed exact count and can certify an incomplete or changed population.**

At [R/fec_api.R:1073](C:/Users/pgoff/Mentat/mentat/R/fec_api.R:1073), a parent query that becomes unservable is replaced with date-window results by calling `fec_api_combine_date_windows(state, child_result)` without the parent's already observed count. The helper defaults `expected_count` to `NULL` at [line 952](C:/Users/pgoff/Mentat/mentat/R/fec_api.R:952), so the row-count comparison at line 958 is skipped. It replaces the old expected count with the union size at line 967 and sets `coverage_verified=TRUE` at line 970.

The offline [reproduction](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/reproduce_window_count_drift.R) supplies a parent page with an exact count of three and one observed ID, then two mocked 504 responses. Its 26 disjoint date windows return two unique IDs, including the previously observed ID. The actual collector returns:

```text
Original exact count=3; window union=2; complete=TRUE; coverage_verified=TRUE; requests=29
```

These were 29 calls to an in-process mock transport, not network requests. The [log](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/reproduce_window_count_drift.R.log) records the result. This is not proof that a historical production report lost a particular receipt. It proves a path that can certify a population inconsistent with its own preserved source count. Even if the difference is a legitimate live FEC update, the methodology requires unstable populations to remain unverified; the normal pagination path explicitly rejects them. Recovery should retain and compare the prior count/evidence or start an explicitly new snapshot, and needs a regression case for timeout after successful pages.

## Test results

- **Shipped R suites: 19 passed, 2 failed, 21 total.** Results: [r-verified-results.json](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/r-verified-results.json). Passing suites cover API pagination/fanout, evidence preservation, attribution recheck, receipt rules, identity components, ingestion, reconciliation, report generation/vectorization, report directory, export guards and transfer evidence. The report test checked 6,035 Stats formulas and cross-sheet references; the identity test includes 1,000 randomized comparisons.
- **PowerShell suites: 5 passed, 0 failed.** Funding labels, last-good publication guard, Node heap planning, report-directory enforcement and workbook-builder guards passed. Results are the `.ps1` entries in [all-results.json](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/all-results.json); that file's R entries are the initial sandbox attempt, not the authoritative R rerun.
- **Requested Python/R integration reruns: 17 passed, 0 failed.** `test_api_request_pool.py`: 4 tests; `test_transfer_graph.py`: 13 tests. These are reruns of the parent audit's tests, not 17 additional unique tests.
- **Static parsing: 48 R files and 24 PowerShell files passed with zero syntax failures.** Backups and cached runtimes were excluded. See [r-parse-results.log](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/r-parse-results.log) and [powershell-parse-results.json](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/powershell-parse-results.json).

## Shipped test failures and supplemental checks

**P2 — Two stale test cases prevent their intended behavior from being checked by the shipped suite.** These are test-maintenance failures, not evidence that SQLite locking or correct date-window unions are broken.

1. [test_request_windows.R:17](C:/Users/pgoff/Mentat/mentat/tests/test_request_windows.R:17) builds API fixtures without `pagination.is_count_exact=TRUE`, which production now requires. It stops immediately with `FEC API requires an exact nonnegative pagination.count: sample`, before window coverage and resume assertions execute. Its negative-case assertion at [line 25](C:/Users/pgoff/Mentat/mentat/tests/test_request_windows.R:25) also expects `coverage differs`, while the current error says `Date-window coverage is partial or overlapping`.
2. [test_sqlite_lane_locking.R:86](C:/Users/pgoff/Mentat/mentat/tests/test_sqlite_lane_locking.R:86) searches for the removed literal `startup_jitter_seconds <- (lane_index - 1L) * 0.25`. The current lane code delegates to `lane_startup_delay(lane_number)` at [collect_api_lane.R:283](C:/Users/pgoff/Mentat/mentat/tools/collect_api_lane.R:283), so the structural assertion stops the test before its real two-process SQLite lock exercise.

Fixture-only copies saved under this audit directory correct those outdated assumptions and point to the original production modules. Both supplemental copies pass: date-window completeness, overlap/shortfall rejection and resume; and the real SQLite lock test, which waited 1.330 seconds for the competing writer. These **do not change the shipped suite result of 19/21**. Files: [supplemental_request_windows.R](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/supplemental_request_windows.R), [supplemental_sqlite_lane_locking.R](C:/Users/pgoff/Mentat/outputs/mentat-full-audit-2026-09-13/collection/supplemental_sqlite_lane_locking.R), and their `.log` companions.

## Scope and limitations

The audit reviewed the current dirty working files, not only committed HEAD. Review concentrated on `R/collect.R`, `R/schema.R`, `R/fec_api.R`, identity components, API lanes, fanout/work-sharing, query/coverage validation, shared request budgets and PowerShell orchestration. `mentat/AGENTS.md`, README and METHODOLOGY governed scope; fec/Moneyball was excluded. No production workbook, database, checkpoint, accepted-source baseline or API key store was rewritten.

All synthetic databases, reports, temporary files, supplemental scripts and logs were isolated beneath this audit directory. Initial execution could not read the installed R package library through the sandbox and therefore reported missing packages. The approved rerun accessed that library successfully; those initial failures are environmental and are superseded by the results above. Locale warnings persisted but did not prevent passing suites. Process enumeration found no running R/Rscript collector at the start; command-line inspection through Win32_Process was denied, so process information was limited to Get-Process IDs and paths.

Passing synthetic tests does not establish historical attribution accuracy, completeness of every FEC filing, or unique end-to-end giving. Those are separately documented methodology requirements. The audit did not contact FEC, independently adjudicate historical receipts, or determine the dollar exposure of the confirmed timeout path.
