<#
.SYNOPSIS
  Probe congress.gov reachability on an interval and emit the result to the
  shared GLASS BOX stream.

.DESCRIPTION
  On 2026-07-27 congress.gov began serving Cloudflare managed-challenge pages to
  this host for every request, including from a real headful browser. That is a
  site-side block, not a collector defect, so the only correct response is to
  stop collecting and wait for the window to close.

  This probe issues ONE lightweight request per interval -- deliberately gentle,
  since hammering a block extends it -- and reports whether the response is real
  content or a challenge page. It never attempts to solve or bypass a challenge.

  Read-only. It collects nothing and writes no harvest artifacts.
#>
param(
    [string]$EventsDirectory = "C:\Users\pgoff\.claude\glassbox\events",
    [string]$ProbeUrl = "https://www.congress.gov/bill/117th-congress/house-bill/3664/text",
    [int]$IntervalSeconds = 300,
    [int]$MaxHours = 12,
    [string]$Lane = "codex"
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $EventsDirectory)) { New-Item -ItemType Directory $EventsDirectory -Force | Out-Null }

$runId = 'congress-reachability-{0}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')
$deadline = (Get-Date).AddHours($MaxHours)
$probe = 0
$clearAt = $null

function Write-GlassboxEvent {
    param([hashtable]$Payload, [string]$Tag)
    $name = ('evt-{0}-reach-{1}-{2}.json' -f `
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID, $Tag) -replace '[^A-Za-z0-9._-]+', '-'
    $tmp = Join-Path $EventsDirectory ($name + '.tmp')
    ($Payload | ConvertTo-Json -Depth 6) | Out-File -FilePath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination (Join-Path $EventsDirectory $name) -Force
}

while ((Get-Date) -lt $deadline) {
    $probe++
    $status = 0
    $bytes = 0
    $challenged = $true
    $err = ''
    try {
        $r = Invoke-WebRequest -Uri $ProbeUrl -UseBasicParsing -TimeoutSec 45 `
             -Headers @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' }
        $status = [int]$r.StatusCode
        $bytes = $r.RawContentLength
        $body = [string]$r.Content
        # A real bill-text page carries the typed main-surface marker and is
        # hundreds of KB; a challenge page is ~6 KB and names the CF platform.
        $challenged = ($body -match 'challenge-platform|cf_chl|Just a moment|Performing security verification') -or ($body.Length -lt 50000)
    } catch {
        $err = $_.Exception.Message
        if ($_.Exception.Response) { $status = [int]$_.Exception.Response.StatusCode }
    }

    $reachable = (-not $challenged) -and $status -eq 200
    if ($reachable -and -not $clearAt) { $clearAt = (Get-Date).ToUniversalTime().ToString('u') }

    Write-GlassboxEvent -Tag 'probe' -Payload @{
        schema_version = 1
        timestamp_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
        lane           = $Lane
        source         = 'congress-reachability-probe'
        run_id         = $runId
        kind           = 'probe.progress'
        status         = if ($reachable) { 'completed' } else { 'blocked' }
        stage          = 'cloudflare-block-watch'
        summary        = if ($reachable) { "congress.gov REACHABLE (http $status, $bytes bytes)" }
                         else { "congress.gov BLOCKED by Cloudflare challenge (http $status, $bytes bytes)" }
        detail         = if ($err) { "probe error: $err" }
                         else { "Probe #$probe every ${IntervalSeconds}s. One request per interval; no bypass attempted. Collection stays stopped until this clears." }
        current        = $probe
        total          = 0
        http_status    = $status
        challenged     = $challenged
        cleared_at_utc = $clearAt
    }

    if ($reachable) { break }
    Start-Sleep -Seconds $IntervalSeconds
}
