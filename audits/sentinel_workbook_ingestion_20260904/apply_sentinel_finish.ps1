#requires -Version 5.1
<#
.SYNOPSIS
    Applies the 7-file Sentinel workbook ingestion patch set to the LIVE tree.

.DESCRIPTION
    Windows PowerShell 5.1 compatible (no &&, no ??, no ternary).
    Preflight (all before any write):
      (a) refuse if any python.exe process has -LiveRoot in its command line
      (b) refuse if the two named workbooks are open in Excel (exclusive-open probe)
      (c) refuse (no partial applies) if any live file's SHA256 has drifted from
          the recorded "orig" copy under -PatchRoot\orig\<file>

    Apply (only if preflight passes and -WhatIf is not set):
      - back up each live file to LiveRoot\backups\<basename>.PRE-SENTINEL-FINISH-<stamp>.<ext>
      - copy PatchRoot\patched\<file> over LiveRoot\<file>
      - verify post-copy SHA256 of each live file matches the patched source
      - run `python -m py_compile` on each touched .py file (from LiveRoot)
      - write a JSON manifest to LiveRoot\backups\sentinel_finish_apply_<stamp>.json

.PARAMETER LiveRoot
    Root of the live Melange Systems tree.

.PARAMETER PatchRoot
    Root containing orig\ and patched\ mirrors of the changed files. Defaults to
    the directory this script lives in.

.PARAMETER WhatIf
    Runs the full preflight and prints exactly what would be copied. Writes nothing.
#>
[CmdletBinding()]
param(
    [string]$LiveRoot = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [string]$PatchRoot = '',
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

# NOTE: $PSScriptRoot is not reliably populated yet when used directly as a
# param() default value in Windows PowerShell 5.1 (it depends on invocation
# form -- confirmed empty under `powershell -File ... -WhatIf`). Resolve it
# here in the body instead, once the script is actually running.
if ([string]::IsNullOrEmpty($PatchRoot)) {
    if ($PSScriptRoot) {
        $PatchRoot = $PSScriptRoot
    } elseif ($MyInvocation.MyCommand.Path) {
        $PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
    } else {
        throw "Could not resolve -PatchRoot: pass it explicitly."
    }
}

# ---------------------------------------------------------------------------
# File list: the 7 changed files, as repo-relative paths (relative to LiveRoot
# and to PatchRoot\orig / PatchRoot\patched alike).
# ---------------------------------------------------------------------------
$FileList = @(
    'fec\audit\audit_full.py',
    'fec\legislation\build_archive_legislative.py',
    'fec\legislation\sync_sentinel_bill_ledger.py',
    'fec\moneyball_core.py',
    'fec\run_pipeline.py',
    'fec\tests\legislation\test_sentinel_bill_workbook_sync.py',
    'fec\weekly_refresh.py'
)

function Write-Section {
    param([string]$Text)
    Write-Host ""
    Write-Host "=== $Text ===" -ForegroundColor Cyan
}

function Get-FileSha256 {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    $hash = Get-FileHash -LiteralPath $Path -Algorithm SHA256
    return $hash.Hash
}

Write-Section "Sentinel finish apply -- LiveRoot=$LiveRoot PatchRoot=$PatchRoot WhatIf=$($WhatIf.IsPresent)"

# ---------------------------------------------------------------------------
# Preflight (a): refuse if any python.exe process is running whose command
# line references LiveRoot (Paul's live-jobs law).
# ---------------------------------------------------------------------------
Write-Section "Preflight (a): checking for running python.exe processes touching LiveRoot"

$liveJobHits = @()
try {
    $pyProcs = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction Stop
} catch {
    Write-Host "WARNING: could not enumerate python.exe processes via CIM: $($_.Exception.Message)" -ForegroundColor Yellow
    $pyProcs = @()
}

foreach ($proc in $pyProcs) {
    $cmdLine = $proc.CommandLine
    if ($null -eq $cmdLine) { $cmdLine = '' }
    if ($cmdLine.ToLowerInvariant().Contains($LiveRoot.ToLowerInvariant())) {
        $liveJobHits += [PSCustomObject]@{
            PID         = $proc.ProcessId
            CommandLine = $cmdLine
        }
    }
}

if ($liveJobHits.Count -gt 0) {
    Write-Host "REFUSED: found $($liveJobHits.Count) python.exe process(es) referencing LiveRoot:" -ForegroundColor Red
    $liveJobHits | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host "Apply refused. No files were touched." -ForegroundColor Red
    exit 1
}
Write-Host "OK: no python.exe process references LiveRoot."

# ---------------------------------------------------------------------------
# Preflight (b): refuse if the two named workbooks are open in Excel.
# Tested by attempting an exclusive-write open; never modifies the file.
# ---------------------------------------------------------------------------
Write-Section "Preflight (b): checking workbook exclusive-open availability"

$workbooks = @(
    (Join-Path $LiveRoot 'Moneyball Main Version - Blended.xlsx'),
    (Join-Path $LiveRoot 'Sentinel Bill Ledger.xlsx')
)

$lockedWorkbooks = @()
foreach ($wb in $workbooks) {
    if (-not (Test-Path -LiteralPath $wb)) {
        Write-Host "SKIP (not found): $wb" -ForegroundColor Yellow
        continue
    }
    $fs = $null
    try {
        $fs = [System.IO.File]::Open($wb, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        Write-Host "OK (not locked): $wb"
    } catch {
        $lockedWorkbooks += $wb
        Write-Host "LOCKED: $wb -- $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        if ($null -ne $fs) { $fs.Dispose() }
    }
}

if ($lockedWorkbooks.Count -gt 0) {
    Write-Host "REFUSED: $($lockedWorkbooks.Count) workbook(s) appear open elsewhere (e.g. Excel):" -ForegroundColor Red
    $lockedWorkbooks | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    Write-Host "Apply refused. No files were touched." -ForegroundColor Red
    exit 1
}
Write-Host "OK: neither workbook is open for exclusive access elsewhere."

# ---------------------------------------------------------------------------
# Preflight (c): compare live file SHA256 against the recorded "orig" copy.
# ANY drift refuses the WHOLE apply (no partial applies).
# ---------------------------------------------------------------------------
Write-Section "Preflight (c): comparing live files against recorded orig snapshots"

$driftRows = @()
$missingRows = @()
foreach ($rel in $FileList) {
    $livePath = Join-Path $LiveRoot $rel
    $origPath = Join-Path (Join-Path $PatchRoot 'orig') $rel

    if (-not (Test-Path -LiteralPath $livePath)) {
        $missingRows += [PSCustomObject]@{ File = $rel; Problem = "live file missing: $livePath" }
        continue
    }
    if (-not (Test-Path -LiteralPath $origPath)) {
        $missingRows += [PSCustomObject]@{ File = $rel; Problem = "orig snapshot missing: $origPath" }
        continue
    }

    $liveSha = Get-FileSha256 -Path $livePath
    $origSha = Get-FileSha256 -Path $origPath

    $status = 'MATCH'
    if ($liveSha -ne $origSha) {
        $status = 'DRIFTED'
        $driftRows += [PSCustomObject]@{
            File    = $rel
            LiveSha = $liveSha
            OrigSha = $origSha
            Status  = $status
        }
    }

    Write-Host ("{0,-62} live={1}  orig={2}  [{3}]" -f $rel, $liveSha, $origSha, $status)
}

if ($missingRows.Count -gt 0) {
    Write-Host ""
    Write-Host "REFUSED: missing file(s) prevent a safe comparison:" -ForegroundColor Red
    $missingRows | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host "Apply refused. No files were touched." -ForegroundColor Red
    exit 1
}

if ($driftRows.Count -gt 0) {
    Write-Host ""
    Write-Host "REFUSED: $($driftRows.Count) file(s) have drifted from the recorded orig snapshot:" -ForegroundColor Red
    $driftRows | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host "Apply refused (no partial applies). No files were touched." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "OK: all $($FileList.Count) live files match their recorded orig snapshot." -ForegroundColor Green

# ---------------------------------------------------------------------------
# -WhatIf: report what would happen, write nothing.
# ---------------------------------------------------------------------------
if ($WhatIf) {
    Write-Section "WhatIf: the following would be copied (nothing written)"
    $stampPreview = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
    foreach ($rel in $FileList) {
        $livePath = Join-Path $LiveRoot $rel
        $patchedPath = Join-Path (Join-Path $PatchRoot 'patched') $rel
        $base = [System.IO.Path]::GetFileNameWithoutExtension($rel)
        $ext = [System.IO.Path]::GetExtension($rel)
        $backupName = "$base.PRE-SENTINEL-FINISH-$stampPreview$ext"
        Write-Host ("WOULD BACK UP : {0}" -f $livePath)
        Write-Host ("           TO : {0}" -f (Join-Path (Join-Path $LiveRoot 'backups') $backupName))
        Write-Host ("WOULD COPY    : {0}" -f $patchedPath)
        Write-Host ("           TO : {0}" -f $livePath)
        Write-Host ""
    }
    Write-Host "WhatIf complete. Preflight passed; no files were written." -ForegroundColor Green
    exit 0
}

# ---------------------------------------------------------------------------
# Apply.
# ---------------------------------------------------------------------------
Write-Section "Applying patch set"

$backupsDir = Join-Path $LiveRoot 'backups'
if (-not (Test-Path -LiteralPath $backupsDir)) {
    New-Item -ItemType Directory -Path $backupsDir -Force | Out-Null
}

$stamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$manifestEntries = @()

foreach ($rel in $FileList) {
    $livePath = Join-Path $LiveRoot $rel
    $patchedPath = Join-Path (Join-Path $PatchRoot 'patched') $rel

    if (-not (Test-Path -LiteralPath $patchedPath)) {
        throw "Patched source missing, aborting mid-apply: $patchedPath"
    }

    $base = [System.IO.Path]::GetFileNameWithoutExtension($rel)
    $ext = [System.IO.Path]::GetExtension($rel)
    $backupName = "$base.PRE-SENTINEL-FINISH-$stamp$ext"
    $backupPath = Join-Path $backupsDir $backupName

    Copy-Item -LiteralPath $livePath -Destination $backupPath -Force
    Write-Host "BACKED UP  : $livePath -> $backupPath"

    Copy-Item -LiteralPath $patchedPath -Destination $livePath -Force
    Write-Host "COPIED     : $patchedPath -> $livePath"

    $manifestEntries += [PSCustomObject]@{
        File       = $rel
        LivePath   = $livePath
        BackupPath = $backupPath
        PatchedSrc = $patchedPath
    }
}

# ---------------------------------------------------------------------------
# Post-copy verification: live file SHA256 must equal patched source SHA256.
# ---------------------------------------------------------------------------
Write-Section "Post-copy verification"

$verifyFailures = @()
foreach ($entry in $manifestEntries) {
    $liveSha = Get-FileSha256 -Path $entry.LivePath
    $patchedSha = Get-FileSha256 -Path $entry.PatchedSrc
    $ok = ($liveSha -eq $patchedSha)
    if (-not $ok) {
        $verifyFailures += $entry.File
    }
    $entry | Add-Member -NotePropertyName NewSha -NotePropertyValue $liveSha
    $status = 'MATCH'
    if (-not $ok) { $status = 'MISMATCH' }
    Write-Host ("{0,-62} new={1}  patched={2}  [{3}]" -f $entry.File, $liveSha, $patchedSha, $status)
}

if ($verifyFailures.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: post-copy verification FAILED for: $($verifyFailures -join ', ')" -ForegroundColor Red
    Write-Host "Live files are in an inconsistent state. Use the backups in $backupsDir to restore manually." -ForegroundColor Red
    exit 1
}
Write-Host ""
Write-Host "OK: all live files verified against patched source." -ForegroundColor Green

# ---------------------------------------------------------------------------
# py_compile check on each .py touched, run from LiveRoot.
# ---------------------------------------------------------------------------
Write-Section "python -m py_compile on touched .py files"

$compileResults = @()
foreach ($entry in $manifestEntries) {
    if ($entry.File -notlike '*.py') { continue }
    Push-Location $LiveRoot
    try {
        $compileOut = & python -m py_compile $entry.File 2>&1
        $compileExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $status = 'OK'
    if ($compileExit -ne 0) { $status = 'FAILED' }
    $compileResults += [PSCustomObject]@{
        File     = $entry.File
        ExitCode = $compileExit
        Status   = $status
    }
    Write-Host ("py_compile {0,-58} [{1}]" -f $entry.File, $status)
    if ($compileExit -ne 0) {
        Write-Host $compileOut -ForegroundColor Red
    }
}

$compileFailures = $compileResults | Where-Object { $_.Status -eq 'FAILED' }
if ($compileFailures.Count -gt 0) {
    Write-Host ""
    Write-Host "WARNING: $($compileFailures.Count) file(s) failed py_compile. Files are already applied; backups are in $backupsDir." -ForegroundColor Yellow
}

# ---------------------------------------------------------------------------
# Manifest.
# ---------------------------------------------------------------------------
Write-Section "Manifest"

$manifestForPrint = $manifestEntries | Select-Object File, BackupPath, NewSha
$manifestForPrint | Format-Table -AutoSize | Out-String | Write-Host

$manifestObject = [PSCustomObject]@{
    Timestamp      = $stamp
    LiveRoot       = $LiveRoot
    PatchRoot      = $PatchRoot
    Files          = $manifestEntries | Select-Object File, LivePath, BackupPath, PatchedSrc, NewSha
    CompileResults = $compileResults
}

$manifestPath = Join-Path $backupsDir "sentinel_finish_apply_$stamp.json"
$manifestObject | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $manifestPath -Encoding utf8

Write-Host "Manifest written to: $manifestPath" -ForegroundColor Green
Write-Host ""
Write-Host "Apply complete." -ForegroundColor Green
