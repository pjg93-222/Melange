#requires -Version 5.1
<#
.SYNOPSIS
    Reverts a Sentinel-finish apply using the manifest it produced.

.DESCRIPTION
    Windows PowerShell 5.1 compatible (no &&, no ??, no ternary).
    For each entry in the manifest:
      - refuse (per-file) if the live file's CURRENT SHA256 does not match the
        manifest's recorded "NewSha" -- that means someone edited the file
        after the apply, and blindly restoring the backup would silently
        discard that edit.
      - otherwise, copy the backup file back over the live file and verify
        the live file's SHA256 now equals the backup's SHA256.

    No partial silent damage: files that fail the current-sha check are
    skipped and reported, not force-restored. Use -Force to override that
    per-file refusal if you have confirmed the post-apply edit should be
    discarded.

.PARAMETER ManifestPath
    Path to the sentinel_finish_apply_<stamp>.json manifest written by
    apply_sentinel_finish.ps1.

.PARAMETER Force
    Restore a file even if its current live SHA256 does not match the
    manifest's NewSha (i.e. it was edited after the apply). Off by default.

.PARAMETER WhatIf
    Reports what would be restored without writing anything.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$ManifestPath,

    [switch]$Force,

    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'

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

if (-not (Test-Path -LiteralPath $ManifestPath)) {
    Write-Host "ERROR: manifest not found: $ManifestPath" -ForegroundColor Red
    exit 1
}

Write-Section "Sentinel finish revert -- Manifest=$ManifestPath WhatIf=$($WhatIf.IsPresent) Force=$($Force.IsPresent)"

$manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json

Write-Host "Manifest timestamp : $($manifest.Timestamp)"
Write-Host "LiveRoot            : $($manifest.LiveRoot)"
Write-Host "PatchRoot           : $($manifest.PatchRoot)"
Write-Host "Files in manifest   : $($manifest.Files.Count)"

$refused = @()
$toRestore = @()

Write-Section "Checking current live state against manifest NewSha"

foreach ($entry in $manifest.Files) {
    $livePath = $entry.LivePath
    $backupPath = $entry.BackupPath
    $expectedNewSha = $entry.NewSha

    if (-not (Test-Path -LiteralPath $backupPath)) {
        $refused += [PSCustomObject]@{
            File   = $entry.File
            Reason = "backup missing: $backupPath"
        }
        Write-Host ("{0,-62} [REFUSED: backup missing]" -f $entry.File) -ForegroundColor Red
        continue
    }

    $currentSha = Get-FileSha256 -Path $livePath

    if ($currentSha -ne $expectedNewSha) {
        if ($Force) {
            Write-Host ("{0,-62} current={1} expected={2} [DRIFT - FORCED]" -f $entry.File, $currentSha, $expectedNewSha) -ForegroundColor Yellow
            $toRestore += $entry
        } else {
            $refused += [PSCustomObject]@{
                File   = $entry.File
                Reason = "live file changed since apply (current=$currentSha expected=$expectedNewSha); edited after apply, refusing without -Force"
            }
            Write-Host ("{0,-62} current={1} expected={2} [REFUSED: post-apply edit detected]" -f $entry.File, $currentSha, $expectedNewSha) -ForegroundColor Red
        }
        continue
    }

    Write-Host ("{0,-62} current={1} [OK, matches manifest]" -f $entry.File, $currentSha)
    $toRestore += $entry
}

if ($refused.Count -gt 0) {
    Write-Host ""
    Write-Host "The following file(s) will NOT be restored (use -Force to override after confirming with Paul):" -ForegroundColor Red
    $refused | Format-Table -AutoSize | Out-String | Write-Host
}

if ($toRestore.Count -eq 0) {
    Write-Host ""
    Write-Host "Nothing to restore. Exiting." -ForegroundColor Yellow
    exit 0
}

if ($WhatIf) {
    Write-Section "WhatIf: the following would be restored (nothing written)"
    foreach ($entry in $toRestore) {
        Write-Host ("WOULD RESTORE: {0}" -f $entry.BackupPath)
        Write-Host ("           TO: {0}" -f $entry.LivePath)
    }
    Write-Host ""
    Write-Host "WhatIf complete. No files were written." -ForegroundColor Green
    exit 0
}

Write-Section "Restoring backups"

$restoreFailures = @()
foreach ($entry in $toRestore) {
    Copy-Item -LiteralPath $entry.BackupPath -Destination $entry.LivePath -Force
    $restoredSha = Get-FileSha256 -Path $entry.LivePath
    $backupSha = Get-FileSha256 -Path $entry.BackupPath
    $ok = ($restoredSha -eq $backupSha)
    $status = 'OK'
    if (-not $ok) { $status = 'MISMATCH' }
    Write-Host ("{0,-62} restored={1}  backup={2}  [{3}]" -f $entry.File, $restoredSha, $backupSha, $status)
    if (-not $ok) {
        $restoreFailures += $entry.File
    }
}

if ($restoreFailures.Count -gt 0) {
    Write-Host ""
    Write-Host "ERROR: restore verification FAILED for: $($restoreFailures -join ', ')" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Revert complete. $($toRestore.Count) file(s) restored, $($refused.Count) refused." -ForegroundColor Green
