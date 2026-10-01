param(
    [string]$Progress = "audits\legfix5\identifier_probe_fast_20260726\progress.json",
    [int]$PollSeconds = 2,
    [int]$TimeoutHours = 12,
    [string]$RunId = "legislation-idprobe-20260726-fast",
    [ValidateSet("claude", "codex", "grok", "gemini", "system")]
    [string]$Lane = "codex"
)

$ErrorActionPreference = "Stop"
$Workspace = Split-Path -Parent $PSScriptRoot
$PowerShell = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$Emit = "C:\Users\pgoff\.claude\glassbox\emit.ps1"
Set-Location -LiteralPath $Workspace

function Get-WorkspacePath {
    param([string]$Value)
    if ([System.IO.Path]::IsPathRooted($Value)) {
        return [System.IO.Path]::GetFullPath($Value)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $Workspace $Value))
}

function Format-Duration {
    param($Seconds)
    if ($null -eq $Seconds) {
        return "--"
    }
    $value = [Math]::Max(0, [int][Math]::Ceiling([double]$Seconds))
    if ($value -lt 60) {
        return "${value}s"
    }
    if ($value -lt 3600) {
        return "$([Math]::Ceiling($value / 60))m"
    }
    return "$([Math]::Floor($value / 3600))h $([Math]::Ceiling(($value % 3600) / 60))m"
}

function Format-ProgressBar {
    param(
        [int]$Completed,
        [int]$Total,
        [int]$Width = 30
    )
    $safeTotal = [Math]::Max(1, $Total)
    $ratio = [Math]::Min(
        1.0,
        [Math]::Max(0.0, ([double]$Completed / [double]$safeTotal))
    )
    $filled = [Math]::Min($Width, [Math]::Floor($ratio * $Width))
    $empty = $Width - $filled
    $bar = "[" + ("#" * $filled) + ("-" * $empty) + "]"
    $percent = [Math]::Floor($ratio * 100)
    return "$bar $Completed/$Total ($percent%)"
}

function Send-GlassboxEvent {
    param(
        [string]$Kind,
        [string]$Status,
        [string]$Summary,
        [string]$Detail = ""
    )
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Emit,
        "-Lane", $Lane,
        "-Kind", $Kind,
        "-Status", $Status,
        "-Summary", $Summary,
        "-RunId", $RunId,
        "-Stage", "fast-collector",
        "-Source", "codex-legislation-fast-observer",
        "-Cwd", $Workspace,
        "-Quiet"
    )
    if ($Detail) {
        $arguments += @("-Detail", $Detail)
    }
    & $PowerShell @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Glassbox event emission failed: $Kind"
    }
}

if (-not (Test-Path -LiteralPath $Emit)) {
    throw "Glassbox emitter is unavailable: $Emit"
}
if ($PollSeconds -lt 1 -or $PollSeconds -gt 30) {
    throw "PollSeconds must be between 1 and 30"
}
if ($TimeoutHours -lt 1 -or $TimeoutHours -gt 24) {
    throw "TimeoutHours must be between 1 and 24"
}

$progressPath = Get-WorkspacePath $Progress
$deadline = [DateTimeOffset]::UtcNow.AddHours($TimeoutHours)
$lastSignature = ""
$missingReported = $false

while ([DateTimeOffset]::UtcNow -lt $deadline) {
    if (-not (Test-Path -LiteralPath $progressPath)) {
        if (-not $missingReported) {
            Send-GlassboxEvent `
                -Kind "collector.starting" -Status "running" `
                -Summary "[########----------------------] 55/210 (26%) | starting 6 workers" `
                -Detail "The strict fast collector is starting; 55 accepted queries are preserved."
            $missingReported = $true
        }
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    try {
        $item = Get-Content -LiteralPath $progressPath -Raw |
            ConvertFrom-Json
    }
    catch {
        Start-Sleep -Seconds $PollSeconds
        continue
    }

    $completed = [int]$item.completed_queries
    $total = [int]$item.total_queries
    $workers = [int]$item.active_workers
    $failures = [int]$item.failure_count
    $rate = if ($null -eq $item.queries_per_minute) {
        0.0
    }
    else {
        [double]$item.queries_per_minute
    }
    $status = [string]$item.status
    $eta = Format-Duration $item.eta_seconds
    $bar = Format-ProgressBar -Completed $completed -Total $total
    $summary = "$bar | $workers workers | $($rate.ToString('0.0')) q/min | ETA $eta"
    $signature = "$status`:$completed`:$total`:$workers`:$failures`:$([Math]::Round($rate, 1))`:$eta"

    if ($signature -ne $lastSignature) {
        $eventStatus = if ($status -eq "complete") {
            "completed"
        }
        elseif ($status -eq "failed") {
            "failed"
        }
        else {
            "running"
        }
        $kind = if ($status -eq "complete") {
            "collector.completed"
        }
        elseif ($status -eq "failed") {
            "collector.failed"
        }
        else {
            "collector.progress"
        }
        Send-GlassboxEvent `
            -Kind $kind -Status $eventStatus -Summary $summary `
            -Detail "Failures: $failures. Updated: $($item.updated_utc). Cookie values are never emitted."
        $lastSignature = $signature
    }

    if ($status -eq "complete") {
        exit 0
    }
    if ($status -eq "failed") {
        exit 1
    }
    Start-Sleep -Seconds $PollSeconds
}

Send-GlassboxEvent `
    -Kind "observer.timeout" -Status "failed" `
    -Summary "Fast collector progress observer reached its bounded timeout"
exit 2
