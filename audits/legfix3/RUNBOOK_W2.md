# W2 Claude execution runbook

Run every command below from the worktree in one PowerShell session. The comparison script
reads the live data root but creates both build roots and its report under this worktree.
It never sets `MONEYBALL_ROOT` to live.

## 1. Pin paths and establish the live read-only hash fence

```powershell
Set-Location 'C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-legfix3'
$Worktree = (Get-Location).Path
$Live = 'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
$Scratch = Join-Path $Worktree 'audits\legfix3\scratch_w2_20260725'
$Delta = Join-Path $Worktree 'audits\legfix3\archive_wiring_delta_20260725.json'

if (Test-Path -LiteralPath $Scratch) { throw "ABORT: preserve existing scratch root: $Scratch" }
if (Test-Path -LiteralPath $Delta) { throw "ABORT: preserve existing delta report: $Delta" }

$Archive = Get-ChildItem -LiteralPath $Live -Filter 'congress_bills_archive_*.xlsx' |
    Sort-Object Name | Select-Object -Last 1 -ExpandProperty FullName
if (-not $Archive) { throw 'ABORT: no live archive workbook' }
$Watched = @(
    (Join-Path $Live 'bill_directions.csv'),
    (Join-Path $Live 'bill_overrides.csv'),
    (Join-Path $Live 'congestion.json'),
    $Archive
)
$Manual = Join-Path $Live 'manual_bill_evidence.csv'
if (Test-Path -LiteralPath $Manual) { $Watched += $Manual }
$Before = $Watched | ForEach-Object {
    "$_|$((Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash)"
}
```

Expected: no output. Abort if the current directory is not the pinned worktree, either
scratch/output path already exists, a watched live input is missing, or the selected archive
is not `congress_bills_archive_20260624_115822.xlsx`.

## 2. Validate fixed data artifacts and the reversal copy

```powershell
$Registry = Import-Csv -LiteralPath '.\bill_directions.csv'
$Overrides = Import-Csv -LiteralPath '.\bill_overrides.csv'
$Ledger = Get-Content -LiteralPath '.\audits\legfix3\wiring_report.json' -Raw |
    ConvertFrom-Json
$BackupHash = (Get-FileHash -LiteralPath `
    '.\backups\bill_directions.PRE-LEGFIX3.csv' -Algorithm SHA256).Hash.ToLowerInvariant()

if ($Registry.Count -ne 126) { throw "ABORT: registry rows = $($Registry.Count), expected 126" }
if (($Registry[0].PSObject.Properties.Name -join ',') -ne 'Bill,Congress,Category,Direction,Note') {
    throw 'ABORT: registry schema mismatch'
}
if (@($Registry | Where-Object Direction -eq '1').Count -ne 107) { throw 'ABORT: +1 count mismatch' }
if (@($Registry | Where-Object Direction -eq '-1').Count -ne 12) { throw 'ABORT: -1 count mismatch' }
if (@($Registry | Where-Object Direction -eq '0').Count -ne 7) { throw 'ABORT: 0 count mismatch' }
if (@($Registry | Where-Object { -not $_.Congress }).Count -ne 14) { throw 'ABORT: inert count mismatch' }
if ($Overrides.Count -ne 8) { throw "ABORT: override rows = $($Overrides.Count), expected 8" }
if ($Ledger.precedence_decisions.Count -ne 47) { throw 'ABORT: precedence ledger mismatch' }
if ($Ledger.quarantines.Count -ne 7) { throw 'ABORT: quarantine ledger mismatch' }
if ($Ledger.inert_rows.Count -ne 14) { throw 'ABORT: inert ledger mismatch' }
if ($Ledger.skips.malformed_directions.bills.Count -ne 159) { throw 'ABORT: malformed skip ledger mismatch' }
if ($BackupHash -ne 'b7a1e0f8d331feda30727a9bd247c22e698d10f051d38b4414a7b5a374a3007e') {
    throw 'ABORT: fixed legacy backup is not the verbatim live 60-row file'
}
```

Expected: no output. Every mismatch is an abort; do not run either builder after a mismatch.

## 3. Compile without importing the write-on-import builder

```powershell
python -c "import pathlib; files=['fec/build_archive_legislative.py','fec/bill_coverage_audit.py','fec/tests/test_bill_collision_guards.py','audits/legfix3/compare_archive_wiring.py']; [compile(pathlib.Path(p).read_text(encoding='utf-8'),p,'exec') for p in files]; print('syntax: 4 files clean')"
if ($LASTEXITCODE -ne 0) { throw 'ABORT: syntax check failed' }
```

Expected: `syntax: 4 files clean`. This command deliberately does not import
`build_archive_legislative.py`, because importing it executes a build.

## 4. Run the focused suite, then the registered suite

```powershell
python -W error .\fec\tests\test_bill_collision_guards.py
if ($LASTEXITCODE -ne 0) { throw 'ABORT: focused collision/wiring suite failed' }

python .\fec\tests\run_tests.py
if ($LASTEXITCODE -ne 0) { throw 'ABORT: registered test runner failed' }
```

Predicted focused terminator: `test_bill_collision_guards: 28 passed, 0 failed`.
The registered runner must report `test_bill_collision_guards suite clean`; the suite name
is registered exactly once. The focused cases cover exact Congress lookup, blank fallback,
H.R.59/H.J.Res.59 type separation, keep-earlier conflicts, fail-closed quarantine,
`LEGDIR_V1` fixed-path legacy parity, and C14 Congress awareness.

Abort on any failure, traceback, warning promoted to failure, or unexpected write outside the
worktree.

## 5. Run the old-vs-new builds in fresh scratch roots

```powershell
python .\audits\legfix3\compare_archive_wiring.py `
    --live-root "$Live" `
    --scratch-root "$Scratch" `
    --output "$Delta"
if ($LASTEXITCODE -ne 0) { throw 'ABORT: scratch comparison failed' }
```

The script creates:

- `audits\legfix3\scratch_w2_20260725\baseline`, with the fixed backup selected by
  `LEGDIR_V1=1` and the live five-row baseline overrides;
- `audits\legfix3\scratch_w2_20260725\new`, with the 126-row typed registry and the new
  eight-row overrides;
- `audits\legfix3\archive_wiring_delta_20260725.json`.

Predicted console shape:

```text
baseline root: <worktree>\audits\legfix3\scratch_w2_20260725\baseline
new root: <worktree>\audits\legfix3\scratch_w2_20260725\new
changed cells: <computed integer>
bills newly direction-covered: <computed integer>
sign flips: <computed integer>
new registry exclusions: <computed integer>
report: <worktree>\audits\legfix3\archive_wiring_delta_20260725.json
```

The numeric runtime deltas are intentionally not predicted as observed results in the
edit-only lane. The report must be nonempty if the authorized reroutes or rank-moving
directions affect selected archive events. An empty report is a review stop, not automatic
acceptance.

## 6. Validate delta attribution and prove live remained untouched

```powershell
$Result = Get-Content -LiteralPath $Delta -Raw | ConvertFrom-Json
if ($Result.schema -ne 'legfix3-archive-wiring-delta-v1') { throw 'ABORT: delta schema mismatch' }
if ($Result.summary.changed_cells -ne $Result.cells.Count) { throw 'ABORT: changed-cell count mismatch' }
$Unattributed = @($Result.cells | Where-Object { $_.responsible.Count -eq 0 })
if ($Unattributed.Count) { throw "ABORT: $($Unattributed.Count) changed cells lack bill attribution" }
$Result.summary | ConvertTo-Json -Depth 8

$After = $Watched | ForEach-Object {
    "$_|$((Get-FileHash -LiteralPath $_ -Algorithm SHA256).Hash)"
}
$LiveDiff = @(Compare-Object -ReferenceObject $Before -DifferenceObject $After)
if ($LiveDiff.Count) {
    $LiveDiff | Format-Table -AutoSize
    throw 'ABORT: a watched live input changed'
}
'live hash fence: unchanged'
```

Expected final line: `live hash fence: unchanged`. Review every entry under `cells`; each
must include member, category, old value, new value, delta, and at least one responsible
bill with old/new mechanism. Review the summary lists for newly direction-covered bills,
sign flips, and new registry exclusions before merge.

## Global abort conditions

Stop without copying any scratch result to live if any command fails; any live hash changes;
the backup hash differs; counts differ from 126/47/7/14/159; a changed cell is unattributed;
the builder selects any archive other than the pinned workbook; `MONEYBALL_ROOT` points
outside either scratch build root; or a title quarantine appears in `bill_directions.csv`.
Do not repair or delete a failed scratch root in this run—preserve it and report the exact
failure.
