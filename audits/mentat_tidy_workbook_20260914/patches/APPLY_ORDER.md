# Lane B apply order

All paths are relative to the repo root `C:\Users\pgoff\Mentat` (the package lives under `mentat\`).
Every patch was generated against the LIVE working-tree file on branch `codex/mentat-crypto`
(dirty tree) and `git apply --check`s clean, individually and all twelve together.

**Updated 2026-09-15 (addendum):** 15 patches now, not 12 - `P6c-report_insights-split`,
`P8-build_tidy_workbook-new` and `P8b-test_tidy_workbook-new` were added, and P1/P7a were
regenerated for contract amendment D2. See `B_RECEIPT.md` section "Addendum 2026-09-15".

Patches live in
`C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-mentat-excel-tableau-format-8ac097\aad4d8be-16e5-435f-9bdb-3eb4c731eb44\scratchpad\tidy\laneB\patches\`
(referred to below as `$P`).

## 0. Back up first

The four new files (`R\tidy_stage.R`, `tools\build_tidy_workbook.py`,
`tests\test_tidy_stage.R`, `tests\test_tidy_workbook.py`) need no backup.
Take a `.bak-20260914-tidy` copy of every file a patch MODIFIES:

```powershell
$M = 'C:\Users\pgoff\Mentat\mentat'
foreach ($rel in @(
  'tools\export_crypto_spending_data.R',
  'R\fec_beneficiary.R',
  'tools\enrich_downstream.py',
  'tools\build_industry_report.ps1',
  'app\server.py',
  'app\contribution_data.py',
  'app\report_insights.py',
  'tests\test_report_insights.py',
  'tests\test_report_directory_console.py',
  'tests\test_contribution_data.py',
  'tests\Test-MentatWorkbookBuilderGuards.ps1'
)) { Copy-Item -LiteralPath (Join-Path $M $rel) -Destination (Join-Path $M "$rel.bak-20260914-tidy") -Force }
```

## 1. Apply, in this order

Dependency order. **P8 (Lane A's writer) goes in BEFORE P5**, so the orchestrator's
absent-writer warning never fires: by the time P5 turns staging on, the writer is on disk.

| # | Patch | Target | Why here |
|---|---|---|---|
| 1 | `P1-tidy_stage-new.patch` | `mentat/R/tidy_stage.R` (new) | Everything else calls into it. |
| 2 | `P3-fec_beneficiary-mappings.patch` | `mentat/R/fec_beneficiary.R` | The exporter calls `fec_committee_map_mappings()`; it must exist first. |
| 3 | `P2-exporter-hook.patch` | `mentat/tools/export_crypto_spending_data.R` | Sources P1, calls P3. Harmless until something passes a 6th argument. |
| 4 | `P4-enrich-staging.patch` | `mentat/tools/enrich_downstream.py` | No-op without `--staging`. |
| 5 | `P8-build_tidy_workbook-new.patch` | `mentat/tools/build_tidy_workbook.py` (new) | Lane A's writer. Must exist before P5 runs it. Inert on its own. |
| 6 | `P5-build_industry_report.patch` | `mentat/tools/build_industry_report.ps1` | First patch that actually turns staging ON. Apply only after 1-5. |
| 7 | `P6a-server-catalog.patch` | `mentat/app/server.py` | Console-only; independent of 1-6. |
| 8 | `P6b-contribution_data.patch` | `mentat/app/contribution_data.py` | Console-only; independent of 1-6. |
| 9 | `P6c-report_insights-split.patch` | `mentat/app/report_insights.py` | Console-only. Sheet-level non-summable list must match per-cycle split sheets. |
| 10 | `P7a-test_tidy_stage-new.patch` | `mentat/tests/test_tidy_stage.R` (new) | Tests P1. |
| 11 | `P8b-test_tidy_workbook-new.patch` | `mentat/tests/test_tidy_workbook.py` (new) | Tests P8. Will FAIL until P8 is applied. |
| 12 | `P7b-test_report_insights.patch` | `mentat/tests/test_report_insights.py` | One case tests P6c; will FAIL until P6c is applied. |
| 13 | `P7c-test_report_directory_console.patch` | `mentat/tests/test_report_directory_console.py` | Tests P6a. |
| 14 | `P7d-test_contribution_data.patch` | `mentat/tests/test_contribution_data.py` | Tests P6b. |
| 15 | `P7e-Test-MentatWorkbookBuilderGuards.patch` | `mentat/tests/Test-MentatWorkbookBuilderGuards.ps1` | Tests P5. Will FAIL until P5 is applied. |

```powershell
cd C:\Users\pgoff\Mentat
$P = '<patches dir>'
foreach ($name in @(
  'P1-tidy_stage-new','P3-fec_beneficiary-mappings','P2-exporter-hook',
  'P4-enrich-staging','P8-build_tidy_workbook-new','P5-build_industry_report',
  'P6a-server-catalog','P6b-contribution_data','P6c-report_insights-split',
  'P7a-test_tidy_stage-new','P8b-test_tidy_workbook-new','P7b-test_report_insights',
  'P7c-test_report_directory_console','P7d-test_contribution_data',
  'P7e-Test-MentatWorkbookBuilderGuards'
)) {
  git apply --check (Join-Path $P "$name.patch")
  if ($LASTEXITCODE -ne 0) { throw "refused: $name" }
  git apply (Join-Path $P "$name.patch")
  if ($LASTEXITCODE -ne 0) { throw "failed: $name" }
  Write-Host "applied $name"
}
```

## 2. Run after applying

```powershell
$M = 'C:\Users\pgoff\Mentat\mentat'
$PY = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$env:R_LIBS_USER = 'C:/Users/pgoff/AppData/Local/R/win-library/4.6'

# 2a. R staging contract (51 checks; deterministic, safe to run twice)
& 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe' (Join-Path $M 'tests\test_tidy_stage.R')

# 2b. R parse checks on the two changed R files
foreach ($f in @('R\tidy_stage.R','R\fec_beneficiary.R','tools\export_crypto_spending_data.R')) {
  & 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe' -e "invisible(parse(file='$(($M + '\' + $f) -replace '\\','/')'))"
}

# 2c. Python suites
Push-Location $M
& $PY -m unittest tests.test_report_insights tests.test_report_directory_console tests.test_contribution_data tests.test_downstream_enrichment tests.test_tidy_workbook
Pop-Location

# 2d. PowerShell builder guards (parses build_industry_report.ps1, does not run it)
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $M 'tests\Test-MentatWorkbookBuilderGuards.ps1')
```

Expected: `test_tidy_stage: PASS` (56 checks); `Ran 70 tests ... OK` (51 pre-existing +
Lane B's 8 new Python tests + Lane A's 11 writer tests; the 51 pre-existing ones also pass
against the patched app on their own); `Test-MentatWorkbookBuilderGuards: PASS`.
`tests.test_tidy_workbook` prints `Wrote ... (8 sheets, 67 rows, 0.1s)` lines and one
`FAIL giving_facts_vs_contributions: ...` line - that FAIL is the writer's own negative
control being exercised inside a passing test, not a failing test.

## 3. Smallest live dry run

Crypto is the smallest industry and the branch's default. Point it at a scratch output
folder so nothing lands in `Mentat Complete Files` (the console globs that folder).

> **CORRECTED 2026-09-15.** The recipe below previously passed `-OutputDirectory $scratch` alone.
> **That throws and never runs.** `build_industry_report.ps1:64` calls
> `Resolve-MentatReportDirectory` (`tools\report_directory.psm1`), which reads
> `$env:MENTAT_REPORT_DIRECTORY` or falls back to `config\report-directory.json`
> (`C:/Users/pgoff/OneDrive/Desktop/Mentat Complete Files`) and then throws
> `"OutputDirectory conflicts with the authoritative report directory: ... Remove the old override,
> or set MENTAT_REPORT_DIRECTORY explicitly for an isolated run."` whenever `-OutputDirectory`
> differs from it. **`MENTAT_REPORT_DIRECTORY` is the isolation lever**, not `-OutputDirectory`.
> Do NOT "fix" the throw by dropping the flag - that publishes straight into `Mentat Complete Files`.
> The scratch directory must ALREADY EXIST, or the function throws
> `'The configured report directory is unavailable'`.
>
> **`-DatabasePath` has no default**: `build_industry_report.ps1:60-62` throws
> `'Pass -DatabasePath explicitly. Report sources are never selected from an ambient default database.'`
>
> **A scratch-output run STILL advances the accepted-source pointer.**
> `build_industry_report.ps1:996` runs `sourceGuard accept` unconditionally once both books are on
> disk, and `accept()` (`report_source_guard.py:327-336`) writes
> `mentat\state\accepted-report-sources\<industry>\<cycles>\current.json` - which is NOT under the
> output directory. **Back that one file up before the run and restore it afterwards** (see below).
> `report_source_guard.py prepare` additionally writes `<uuid>.baseline.db`, `<uuid>.db` and
> `<uuid>.source-changes.jsonl` into the same state directory, and a receipt under
> `state\accepted-report-sources\runs\`, at ps1:350 - near the START of the run.

```powershell
$scratch = Join-Path $env:TEMP 'mentat-tidy-dryrun'
New-Item -ItemType Directory -Path $scratch -Force | Out-Null   # must exist BEFORE the call

# Back up the accepted-source pointer first - the run WILL advance it.
$state   = 'C:\Users\pgoff\Mentat\mentat\state\accepted-report-sources\crypto\2022-2024-2026'
$pointer = Join-Path $state 'current.json'
Copy-Item -LiteralPath $pointer -Destination (Join-Path $scratch 'current.json.before') -Force
(Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash    # record this

$env:MENTAT_REPORT_DIRECTORY = $scratch                        # <-- the isolation lever
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File C:\Users\pgoff\Mentat\mentat\tools\build_industry_report.ps1 `
  -Industry Crypto -DatabasePath <db> -OutputDirectory $scratch

# Restore the pointer byte-for-byte, and remove what `prepare` left behind.
Copy-Item -LiteralPath (Join-Path $scratch 'current.json.before') -Destination $pointer -Force
(Get-FileHash -LiteralPath $pointer -Algorithm SHA256).Hash    # must equal the recorded value
Get-ChildItem $state -File | Where-Object { $_.LastWriteTime -gt $runStart -and $_.Name -ne 'current.json' } |
  Remove-Item -Force
```

Force the export to actually run (a cache hit now also demands a matching staging store,
so the FIRST run after applying will re-export by design). What to look for in the output:

- `tidy staging frames built in N.NNs` and `tidy staging store: ...` from the exporter.
- `Tidy staging: {"allocation_coverage": ..., ...}` from `enrich_downstream.py`.
- `[PASS] tidy_reconciliation` in the EXPORT GUARDS block.
- `<scratch>\Crypto Industry Spending Data.xlsx` exists beside
  `Crypto Industry Spending Overview.xlsx`, with a `.receipt.json` next to the staged copy,
  and `.cache\industry-report\crypto\manifest-*.json` carries `stage_sha256`.
- You should NOT see `Tidy data workbook writer is not installed`. That warning only fires
  when `tools\build_tidy_workbook.py` is missing; applying P8 before P5 (as ordered above)
  guarantees it is present. If you do see it, P8 was skipped.

## 4. Rollback

```powershell
$M = 'C:\Users\pgoff\Mentat\mentat'
foreach ($new in @('R\tidy_stage.R','tools\build_tidy_workbook.py',
                   'tests\test_tidy_stage.R','tests\test_tidy_workbook.py')) {
  Remove-Item -LiteralPath (Join-Path $M $new) -Force -ErrorAction SilentlyContinue
}
foreach ($rel in @(
  'tools\export_crypto_spending_data.R','R\fec_beneficiary.R','tools\enrich_downstream.py',
  'tools\build_industry_report.ps1','app\server.py','app\contribution_data.py',
  'app\report_insights.py','tests\test_report_insights.py',
  'tests\test_report_directory_console.py',
  'tests\test_contribution_data.py','tests\Test-MentatWorkbookBuilderGuards.ps1'
)) {
  $backup = Join-Path $M "$rel.bak-20260914-tidy"
  if (Test-Path -LiteralPath $backup) { Move-Item -LiteralPath $backup -Destination (Join-Path $M $rel) -Force }
}
```

Also delete any staging stores the dry run left behind, so a later build does not
cache-hit on them: `Remove-Item C:\Users\pgoff\Mentat\mentat\.cache\industry-report\*\tidy-*.sqlite`.
Nothing published is affected by rollback: the Overview workbook, its payload, its
manifest and the accepted-source baseline are all written by unchanged code paths.

`git apply -R <patch>` also works for every one of the fifteen, but the `.bak` restore is
safer on a dirty tree where other lanes may have touched the same files since.

## Status, 2026-09-18 (recorded when this packet was committed)

All fifteen patches are applied in `C:\Users\pgoff\Mentat` and all fifteen are committed on
`codex/mentat-crypto`. Do not re-apply any of them.

| Patch | Landed in |
|---|---|
| P1, P3, P4, P6b, P7a, P7c, P7d, P7e, P8, P8b | `bd5dc8ea1` |
| P2 | `d78cf0b8f` (carried by the contributor street-column commit) |
| P5 | `937ea01f5` |
| P6a | `a4b3c8e2e` (carried by the Ride 1 findings commit) |
| P6c, P7b | `825ac3b12` (the worksheet-accounting commit, which owns the rest of both files) |

`R/tidy_stage.R` and `tools/build_tidy_workbook.py` have since gained the contributor street
columns (`d78cf0b8f`), so their committed blobs differ from the P1 and P8 post-images by those
lines. The `.bak-20260914-tidy` rollback route above no longer exists (those backups were deleted
on 2026-09-15); roll a patch back by reverting the commit that carries it.
