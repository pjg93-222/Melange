param(
    [string]$Plan = "audits\legfix5\identifier_probe_parallel_20260726\shard_plan.json",
    [int]$WorkflowPid = 0,
    [int]$PollSeconds = 10,
    [int]$TimeoutHours = 12,
    [string]$RunId = "legislation-idprobe-20260726",
    [switch]$RunAlreadyStarted,
    [switch]$SkipInitialQueueEvents,
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

function Send-GlassboxEvent {
    param(
        [string]$Kind,
        [string]$Status,
        [string]$Stage,
        [string]$Summary,
        [string]$Detail = "",
        [hashtable]$Metadata = @{}
    )
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $Emit,
        "-Lane", $Lane,
        "-Kind", $Kind,
        "-Status", $Status,
        "-Summary", $Summary,
        "-RunId", $RunId,
        "-Stage", $Stage,
        "-Source", "codex-legislation-observer",
        "-Cwd", $Workspace,
        "-Quiet"
    )
    if ($Detail) {
        $arguments += @("-Detail", $Detail)
    }
    & $PowerShell @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Glassbox event emission failed: $Kind/$Stage"
    }
}

function Get-LatestPartialManifest {
    param([string]$OutputDirectory)
    if (-not (Test-Path -LiteralPath $OutputDirectory)) {
        return $null
    }
    $partial = @(
        Get-ChildItem -LiteralPath $OutputDirectory `
            -Filter "manifest.partial.*.json" -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTimeUtc -Descending
    )
    if ($partial.Count -eq 0) {
        return $null
    }
    try {
        return Get-Content -LiteralPath $partial[0].FullName -Raw |
            ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Get-CollectorPid {
    param([string]$OutputDirectory)
    $lockPath = Join-Path $OutputDirectory "collector.lock.json"
    if (-not (Test-Path -LiteralPath $lockPath)) {
        return 0
    }
    try {
        $lock = Get-Content -LiteralPath $lockPath -Raw | ConvertFrom-Json
        $pidValue = [int]$lock.pid
        if ($null -ne (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
            return $pidValue
        }
    }
    catch {
        return 0
    }
    return 0
}

if (-not (Test-Path -LiteralPath $Emit)) {
    throw "Glassbox emitter is unavailable: $Emit"
}
if ($PollSeconds -lt 2 -or $PollSeconds -gt 60) {
    throw "PollSeconds must be between 2 and 60"
}
if ($TimeoutHours -lt 1 -or $TimeoutHours -gt 24) {
    throw "TimeoutHours must be between 1 and 24"
}

$planPath = Get-WorkspacePath $Plan
$document = Get-Content -LiteralPath $planPath -Raw | ConvertFrom-Json
if (
    $document.schema -ne "acu-legislation-identifier-shard-plan-v1" -or
    $document.partition.registry_query_count -ne 210 -or
    $document.partition.disjoint -ne $true -or
    $document.partition.complete -ne $true
) {
    throw "Refusing to observe an unverified shard plan"
}

$deadline = [DateTimeOffset]::UtcNow.AddHours($TimeoutHours)
$lastState = @{}
$cooldownNotBefore = $null
if ($document.global_cooldown.next_retry_not_before) {
    $cooldownNotBefore = [DateTimeOffset]::Parse(
        $document.global_cooldown.next_retry_not_before
    )
}

if (-not $RunAlreadyStarted) {
    Send-GlassboxEvent `
        -Kind "run.started" -Status "running" -Stage "fleet" `
        -Summary "Congress.gov identifier collector fleet" `
        -Detail "Three disjoint headless shards; exact 210-query consolidation."
}

foreach ($shard in $document.shards) {
    $stage = [string]$shard.shard_id
    $lastState[$stage] = ""
    if (-not $SkipInitialQueueEvents) {
        Send-GlassboxEvent `
            -Kind "collector.queued" -Status "queued" -Stage $stage `
            -Summary "$stage queued: 0/$(@($shard.query_ids).Count) queries" `
            -Detail "Headless browser; isolated profile and output; 4500ms per-shard request delay." `
            -Metadata @{
                expected_queries = @($shard.query_ids).Count
                headless = $true
                delay_ms = [int]$shard.delay_ms
                output_dir = [string]$shard.output_dir
                profile_dir = [string]$shard.profile_dir
            }
    }
}

while ([DateTimeOffset]::UtcNow -lt $deadline) {
    if (
        $null -ne $cooldownNotBefore -and
        [DateTimeOffset]::UtcNow -lt $cooldownNotBefore
    ) {
        $remaining = [Math]::Ceiling(
            ($cooldownNotBefore - [DateTimeOffset]::UtcNow).TotalSeconds
        )
        $bucket = [Math]::Floor($remaining / 60)
        $signature = "waiting:$bucket"
        if ($lastState["cooldown"] -ne $signature) {
            $lastState["cooldown"] = $signature
            Send-GlassboxEvent `
                -Kind "collector.cooldown" -Status "waiting" -Stage "cooldown" `
                -Summary "Fail-closed cooldown: ${remaining}s remain" `
                -Detail "No Congress.gov request before $($cooldownNotBefore.ToString('o'))."
        }
        Start-Sleep -Seconds $PollSeconds
        continue
    }
    if ($lastState["cooldown"] -ne "completed") {
        $lastState["cooldown"] = "completed"
        Send-GlassboxEvent `
            -Kind "collector.cooldown.completed" -Status "completed" `
            -Stage "cooldown" -Summary "Cooldown honored; shard launch enabled"
    }

    $completeShards = 0
    $activePids = @()
    foreach ($shard in $document.shards) {
        $stage = [string]$shard.shard_id
        $out = Get-WorkspacePath ([string]$shard.output_dir)
        $expected = @($shard.query_ids).Count
        $manifestPath = Join-Path $out "manifest.json"
        $manifest = $null
        if (Test-Path -LiteralPath $manifestPath) {
            try {
                $manifest = Get-Content -LiteralPath $manifestPath -Raw |
                    ConvertFrom-Json
            }
            catch {
                $manifest = $null
            }
        }
        $partial = Get-LatestPartialManifest $out
        $done = 0
        if ($null -ne $manifest) {
            $done = @($manifest.queries).Count
        }
        elseif ($null -ne $partial) {
            $done = @($partial.queries).Count
        }
        $collectorPid = Get-CollectorPid $out
        if ($collectorPid -gt 0) {
            $activePids += $collectorPid
        }

        if (
            $null -ne $manifest -and
            $manifest.status -eq "complete" -and
            $done -eq $expected
        ) {
            $completeShards += 1
            $signature = "complete:$done"
            if ($lastState[$stage] -ne $signature) {
                $lastState[$stage] = $signature
                Send-GlassboxEvent `
                    -Kind "collector.completed" -Status "completed" -Stage $stage `
                    -Summary "$stage complete: $done/$expected queries" `
                    -Detail "Shard manifest is complete; consolidation remains fail-closed." `
                    -Metadata @{
                        completed_queries = $done
                        expected_queries = $expected
                        output_dir = [string]$shard.output_dir
                    }
            }
            continue
        }

        if ($collectorPid -gt 0) {
            $signature = "running:$collectorPid`:$done"
            if ($lastState[$stage] -ne $signature) {
                $lastState[$stage] = $signature
                Send-GlassboxEvent `
                    -Kind "collector.progress" -Status "running" -Stage $stage `
                    -Summary "$stage PID ${collectorPid}: $done/$expected queries" `
                    -Detail "Headless Chromium is active with an isolated profile and output directory." `
                    -Metadata @{
                        pid = $collectorPid
                        completed_queries = $done
                        expected_queries = $expected
                        headless = $true
                        output_dir = [string]$shard.output_dir
                    }
            }
        }
        elseif ($done -gt 0) {
            $signature = "waiting:$done"
            if ($lastState[$stage] -ne $signature) {
                $lastState[$stage] = $signature
                Send-GlassboxEvent `
                    -Kind "collector.waiting" -Status "waiting" -Stage $stage `
                    -Summary "$stage paused/retrying: $done/$expected queries" `
                    -Detail "No live shard PID; preserved artifacts remain available for resume."
            }
        }
    }

    if ($completeShards -eq @($document.shards).Count) {
        $consolidatedDirectory = Get-WorkspacePath (
            [string]$document.consolidated_output
        )
        $consolidatedManifest = Join-Path $consolidatedDirectory "manifest.json"
        if (Test-Path -LiteralPath $consolidatedManifest) {
            try {
                $combined = Get-Content -LiteralPath $consolidatedManifest -Raw |
                    ConvertFrom-Json
                $combinedCount = @($combined.selected_query_ids).Count
                if (
                    $combined.status -eq "complete" -and
                    $combinedCount -eq 210
                ) {
                    Send-GlassboxEvent `
                        -Kind "run.completed" -Status "completed" -Stage "consolidate" `
                        -Summary "Identifier fleet consolidated: 210/210 queries" `
                        -Detail "All source artifacts preserved; exact registry reconciliation passed." `
                        -Metadata @{
                            query_count = 210
                            output_dir = [string]$document.consolidated_output
                        }
                    exit 0
                }
            }
            catch {
                # The consolidator may still be replacing the manifest atomically.
            }
        }
        $signature = "running:$completeShards"
        if ($lastState["consolidate"] -ne $signature) {
            $lastState["consolidate"] = $signature
            Send-GlassboxEvent `
                -Kind "collector.consolidating" -Status "running" `
                -Stage "consolidate" `
                -Summary "All shards complete; validating exact 210-query union"
        }
    }

    if ($WorkflowPid -gt 0) {
        $workflow = Get-Process -Id $WorkflowPid -ErrorAction SilentlyContinue
        if ($null -eq $workflow -and $activePids.Count -eq 0) {
            Send-GlassboxEvent `
                -Kind "run.failed" -Status "failed" -Stage "fleet" `
                -Summary "Collector workflow exited before exact consolidation" `
                -Detail "Observer found no live workflow or shard PID; preserved artifacts were not removed."
            exit 1
        }
    }

    Start-Sleep -Seconds $PollSeconds
}

Send-GlassboxEvent `
    -Kind "run.blocked" -Status "blocked" -Stage "observer" `
    -Summary "Collector observer reached its bounded timeout" `
    -Detail "The observer stopped after $TimeoutHours hours; the collector workflow was not terminated."
exit 2
