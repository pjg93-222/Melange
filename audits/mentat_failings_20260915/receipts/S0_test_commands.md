# S0 receipt — per-suite test commands, proven 2026-09-15

Working directory for **every** command below: `C:\Users\pgoff\Mentat\mentat`
(not the repo root). Verified, not assumed — both directories were tried.

Interpreters: `python` 3.12.10, `node` v24.18.0, R 4.6.0.
**`Rscript` is NOT on PATH** — the full path is required.
**`pwsh` is NOT installed** — use `powershell.exe` (Windows PowerShell 5.1).
Pester 3.4.0 is installed but the `Test-Mentat*.ps1` files are plain scripts,
not Pester suites.

---

## 1. Python — `python -m unittest tests.<module> -v`

```
cd C:\Users\pgoff\Mentat\mentat
python -m unittest tests.test_validate_industry_coverage -v
```

```
test_complete_company_cycle_grid_passes (tests.test_validate_industry_coverage.CoverageGateTests.test_complete_company_cycle_grid_passes) ... ok
test_incomplete_unit_and_canary_failure_fail (tests.test_validate_industry_coverage.CoverageGateTests.test_incomplete_unit_and_canary_failure_fail) ... ok
test_missing_cycle_fails_closed_even_with_success_receipt (tests.test_validate_industry_coverage.CoverageGateTests.test_missing_cycle_fails_closed_even_with_success_receipt) ... ok
test_out_of_scope_fact_row_fails (tests.test_validate_industry_coverage.CoverageGateTests.test_out_of_scope_fact_row_fails) ... ok
test_receipt_counts_must_match_roster_grid (tests.test_validate_industry_coverage.CoverageGateTests.test_receipt_counts_must_match_roster_grid) ... ok
test_roster_validation_discovers_industries_and_exclusion_coverage (tests.test_validate_industry_coverage.CoverageGateTests.test_roster_validation_discovers_industries_and_exclusion_coverage) ... ok
test_window_fetch_checkpoints_require_reconciled_stored_parent (tests.test_validate_industry_coverage.CoverageGateTests.test_window_fetch_checkpoints_require_reconciled_stored_parent) ... ok

Ran 7 tests in 1.570s
OK
```

Exit code 0.

Direct execution also works:

```
cd C:\Users\pgoff\Mentat\mentat
python tests\test_validate_industry_coverage.py
```

```
.......
----------------------------------------------------------------------
Ran 7 tests in 2.190s
OK
```

Exit code 0.

## 2. Node — `node tests\<file>.cjs`

```
cd C:\Users\pgoff\Mentat\mentat
node tests\test_chart_math.cjs
```

Tail of output:

```
ℹ tests 20
ℹ suites 0
ℹ pass 20
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 229.9238
```

Exit code 0.

## 3. R — full Rscript path required

```
& "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" --version
```

```
Rscript (R) version 4.6.0 (2026-04-24)
```

```
cd C:\Users\pgoff\Mentat\mentat
& "C:/Program Files/R/R-4.6.0/bin/Rscript.exe" tests\test_fec_api.R
```

Tail of output:

```
unservable_decomposed_query: BINANCEUS cycle 2024 per_page 10 -> retrying from page 1 at per_page 5
unservable_decomposed_query: BINANCEUS cycle 2024 per_page 5 -> retrying from page 1 at per_page 1
test_fec_api: PASS
```

Exit code 0.

## 4. PowerShell — plain script, not Pester

```
cd C:\Users\pgoff\Mentat\mentat
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tests\Test-MentatWorkbookBuilderGuards.ps1
```

```
Test-MentatWorkbookBuilderGuards: PASS
```

Exit code 0.

---

## Sweeps

**PowerShell sweep — RUN, 5/5 PASS:** `Test-MentatFundingLabels`,
`Test-MentatLastGoodGuard`, `Test-MentatNodeHeapPlan`,
`Test-MentatReportDirectory`, `Test-MentatWorkbookBuilderGuards`.

**Node sweep — RUN, 27/31 PASS, 4 FAIL.** These four were already red before
this lane changed anything:

| Test | Line | Failure |
| --- | --- | --- |
| `test_console_browser.cjs` | 188 | `Expected 'false' === 'true'` |
| `test_contribution_export_browser.cjs` | 102 | expected `/exportable viewport/`, got `Nothing to export.` |
| `test_cross_reference_view.cjs` | 75 | regex mismatch on "unresolved company attribution" |
| `test_studio_briefing_tray_browser.cjs` | 121, 155 | expected `2026-09-16.html/pptx`, got `2026-09-15...` |

The last is a **date-boundary flake and a genuine test bug** — it fails whenever
a run straddles local midnight.

**Python and R sweeps — NOT RUN** (slow). No baseline exists; the first session
to run one records it in HANDOFF.md.

---

## Test census (non-recursive, `.bak-*` excluded)

`mentat\tests\`: **137 files total, 116 real tests, 21 `.bak-*` backups.**
By extension: **57 `.py`, 31 `.cjs`, 23 `.R`, 5 `.ps1`.** One subdirectory,
`__pycache__`. A separate `mentat\app\tests\` holds 14 files, 4 real `.js`.

## Fixture convention: none exists across languages

`graph_fixture.py` is shared by three Python suites —
`console_browser_fixture.py:11`, `test_comparison_data.py:10`,
`test_graph_data.py:18`. Other Python cross-imports: `test_merge_company_shards`
into `test_api_company_cycle_fanout.py:21` and `test_worker_sharing.py:19`;
`test_contribution_data` into `test_contribution_query_store.py:18` and
`test_contribution_semantics.py:13`.

**No `.json` fixture files exist in `mentat\tests\`, and no `.cjs` file imports
any `.json`** — the `.cjs` suites build their data inline. The convention in
`contracts/README.md` is therefore new to this repo, not a description of
existing practice.
