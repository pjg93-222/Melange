<#
.SYNOPSIS
  Emit OneDrive content-store restoration progress into the shared GLASS BOX
  stream so the rehydration is observable rather than inferred.

.DESCRIPTION
  After the 2026-07-27 reset OneDrive re-materialised the large content stores
  (GovInfo object store, Congress.gov accepted HTML). That work is invisible to
  the dashboard because OneDrive emits nothing. This watcher counts the stores
  on an interval and writes progress records to the shared events directory the
  Glass Box viewer polls.

  Read-only with respect to the stores. It only counts files and writes events.
#>
param(
    [string]$EventsDirectory = "C:\Users\pgoff\.claude\glassbox\events",
    [string]$Workspace = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [int]$IntervalSeconds = 20,
    [int]$MaxMinutes = 120,
    [string]$Lane = "claude"
)

$ErrorActionPreference = 'Stop'

$targets = @(
    @{ Id = 'govinfo_objects'
       Label = 'GovInfo official XML object store'
       Path = Join-Path $Workspace 'audits\legfix5\govinfo_bill_xml_versions\objects'
       Total = 18406 },
    @{ Id = 'congress_accepted_html'
       Label = 'Congress.gov accepted full-text HTML (2026-07-26 stage)'
       Path = Join-Path $Workspace 'audits\legfix5\congress_advanced_pages_20260725\text_relevance_httr_full_stage_20260726\accepted_html'
       Total = 2886 }
)

if (-not (Test-Path $EventsDirectory)) {
    New-Item -ItemType Directory $EventsDirectory -Force | Out-Null
}

function Write-GlassboxEvent {
    param([hashtable]$Payload, [string]$Tag)
    $name = 'evt-{0}-restore-{1}-{2}.json' -f `
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID, $Tag
    $safe = $name -replace '[^A-Za-z0-9._-]+', '-'
    $tmp = Join-Path $EventsDirectory ($safe + '.tmp')
    $final = Join-Path $EventsDirectory $safe
    ($Payload | ConvertTo-Json -Depth 6) | Out-File -FilePath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination $final -Force
}

$runId = 'onedrive-restore-{0}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')
$deadline = (Get-Date).AddMinutes($MaxMinutes)
$previous = @{}

while ((Get-Date) -lt $deadline) {
    $allDone = $true
    foreach ($t in $targets) {
        $count = 0
        if (Test-Path $t.Path) {
            $count = (Get-ChildItem $t.Path -Recurse -File -Force -ErrorAction SilentlyContinue).Count
        }
        $prior = if ($previous.ContainsKey($t.Id)) { $previous[$t.Id] } else { $count }
        $delta = $count - $prior
        $previous[$t.Id] = $count
        $done = $count -ge $t.Total
        if (-not $done) { $allDone = $false }

        Write-GlassboxEvent -Tag $t.Id -Payload @{
            schema_version = 1
            timestamp_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
            lane           = $Lane
            source         = 'onedrive-content-restore'
            run_id         = $runId
            kind           = 'restore.progress'
            status         = if ($done) { 'completed' } else { 'running' }
            stage          = $t.Id
            summary        = ('{0}/{1} {2}' -f $count, $t.Total, $t.Label)
            detail         = ('Rehydrating from OneDrive; +{0} files since last sample ({1}s interval). Read-only observer.' -f $delta, $IntervalSeconds)
            current        = $count
            total          = $t.Total
            rate           = if ($IntervalSeconds -gt 0) { [math]::Round($delta * 60 / $IntervalSeconds, 1) } else { 0 }
            output_directory = $t.Path
        }
    }

    if ($allDone) {
        Write-GlassboxEvent -Tag 'summary' -Payload @{
            schema_version = 1
            timestamp_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
            lane           = $Lane
            source         = 'onedrive-content-restore'
            run_id         = $runId
            kind           = 'restore.progress'
            status         = 'completed'
            stage          = 'all-stores'
            summary        = 'All watched content stores reached their expected file counts'
            detail         = 'GovInfo object store and Congress.gov accepted HTML are fully rehydrated.'
            current        = 1
            total          = 1
        }
        break
    }

    Start-Sleep -Seconds $IntervalSeconds
}
