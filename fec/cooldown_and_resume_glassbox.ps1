<#
.SYNOPSIS
  Hold the congress.gov lane at ZERO traffic until the Cloudflare block window
  expires, then restart the collection pipeline. Emits to the Glass Box.

.DESCRIPTION
  When congress.gov issues a managed challenge to this host, every request --
  including the collector's backed-off 300s batches -- is refused AND keeps the
  penalty alive. Backing off harder inside the collector does not help, because
  the collector is still generating load.

  This watcher takes the opposite approach: stop the collector completely, send
  no HTTP requests at all, and probe only occasionally by driving the real
  browser (which is ordinary browsing, not a bypass). When the browser is served
  genuine content again, it restarts the pipeline.

  It never attempts to solve or circumvent a challenge. If the block persists it
  simply keeps waiting.
#>
param(
    [string]$Workspace = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [string]$EventsDirectory = "C:\Users\pgoff\.claude\glassbox\events",
    [string]$RRuntime = "C:\Program Files\R\R-4.6.0\bin\x64\Rterm.exe",
    [int]$InitialCooldownMinutes = 20,
    [int]$ProbeIntervalMinutes = 15,
    [int]$MaxWaitHours = 8,
    [string]$Lane = "codex"
)

$ErrorActionPreference = 'Stop'
if (-not (Test-Path $EventsDirectory)) { New-Item -ItemType Directory $EventsDirectory -Force | Out-Null }
$runId = 'congress-cooldown-{0}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')

function Write-GlassboxEvent {
    param([hashtable]$Payload, [string]$Tag)
    $name = ('evt-{0}-cooldown-{1}-{2}.json' -f `
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID, $Tag) -replace '[^A-Za-z0-9._-]+','-'
    $tmp = Join-Path $EventsDirectory ($name + '.tmp')
    ($Payload | ConvertTo-Json -Depth 6) | Out-File -FilePath $tmp -Encoding utf8
    Move-Item -LiteralPath $tmp -Destination (Join-Path $EventsDirectory $name) -Force
}

function Emit {
    param([string]$Status, [string]$Stage, [string]$Summary, [string]$Detail, [int]$Current, [int]$Total)
    Write-GlassboxEvent -Tag $Stage -Payload @{
        schema_version = 1
        timestamp_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
        lane = $Lane; source = 'congress-cooldown-resume'; run_id = $runId
        kind = 'cooldown.progress'; status = $Status; stage = $Stage
        summary = $Summary; detail = $Detail; current = $Current; total = $Total
    }
}

# --- 1. Silence the lane completely -----------------------------------------
$stopped = @()
foreach ($p in (Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" -ErrorAction SilentlyContinue)) {
    if (([string]$p.CommandLine).Contains('run_congress_fulltext_pipeline') -or
        ([string]$p.CommandLine).Contains('supervise_congress_text_harvest')) {
        try { Stop-Process -Id $p.ProcessId -Force -ErrorAction Stop; $stopped += "pipeline:$($p.ProcessId)" } catch {}
    }
}
foreach ($r in (Get-Process Rterm -ErrorAction SilentlyContinue)) {
    try { Stop-Process -Id $r.Id -Force -ErrorAction Stop; $stopped += "collector:$($r.Id)" } catch {}
}
Start-Sleep -Seconds 5
Emit -Status 'running' -Stage 'silenced' `
     -Summary ("Lane silenced: stopped " + $stopped.Count + " process(es); zero requests to congress.gov") `
     -Detail ("Stopped: " + ($stopped -join ', ') + ". A Cloudflare penalty window expires on idleness; continuing to send backed-off batches sustains it.") `
     -Current 0 -Total 1

# --- 2. Cooldown, then probe via the browser only ---------------------------
$probeScript = Join-Path $env:TEMP ("cooldown_probe_{0}.R" -f $PID)
@'
suppressPackageStartupMessages({ library(chromote) })
set_default_chromote_object(Chromote$new(browser = ChromeRemote$new(host = "127.0.0.1", port = 9222L)))
s <- ChromoteSession$new(); s$default_timeout <- 120
try({ s$Page$navigate("https://www.congress.gov/bill/117th-congress/house-bill/3664/text")
      s$Page$loadEventFired(wait_ = TRUE) }, silent = TRUE)
Sys.sleep(8)
title <- s$Runtime$evaluate("document.title")$result$value
marker <- s$Runtime$evaluate("document.body && document.body.innerText.indexOf('Shown Here:') >= 0")$result$value
try(s$close(), silent = TRUE)
cat("TITLE:", title, "\n"); cat("MARKER:", isTRUE(marker), "\n")
'@ | Out-File -FilePath $probeScript -Encoding utf8

Emit -Status 'running' -Stage 'cooldown' `
     -Summary ("Cooling down {0} minutes before first probe" -f $InitialCooldownMinutes) `
     -Detail 'No HTTP requests are issued during cooldown. Only the browser is used to probe, at long intervals.' `
     -Current 0 -Total 1
Start-Sleep -Seconds ($InitialCooldownMinutes * 60)

$deadline = (Get-Date).AddHours($MaxWaitHours)
$probe = 0
$clear = $false
while ((Get-Date) -lt $deadline) {
    $probe++
    $out = & $RRuntime --no-echo --no-restore --file="$probeScript" 2>&1
    $text = ($out | Out-String)
    $marker = $text -match 'MARKER:\s*TRUE'
    $challenged = $text -match 'Just a moment|Performing security'
    if ($marker -and -not $challenged) { $clear = $true }

    Emit -Status $(if ($clear) { 'completed' } else { 'blocked' }) -Stage 'probe' `
         -Summary $(if ($clear) { "congress.gov serving content again after probe $probe" }
                    else { "still blocked (probe $probe); waiting $ProbeIntervalMinutes more minutes" }) `
         -Detail 'Browser-driven probe only; no bypass attempted. Collection stays stopped until content is served.' `
         -Current $probe -Total 0
    if ($clear) { break }
    Start-Sleep -Seconds ($ProbeIntervalMinutes * 60)
}

# --- 3. Resume ---------------------------------------------------------------
if ($clear) {
    $pipeline = Join-Path $Workspace 'fec\run_congress_fulltext_pipeline.ps1'
    Start-Process powershell.exe -ArgumentList @(
        '-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File',("`"$pipeline`""),'-NoViewer'
    ) -WorkingDirectory $Workspace | Out-Null
    Emit -Status 'completed' -Stage 'resumed' `
         -Summary 'Block cleared; collection pipeline restarted' `
         -Detail 'Resume re-fetches nothing already collected.' -Current 1 -Total 1
} else {
    Emit -Status 'blocked' -Stage 'gave-up' `
         -Summary ("Still blocked after {0} hours; collection remains stopped" -f $MaxWaitHours) `
         -Detail 'Deliberately not resuming into a block. Needs a human decision.' -Current 0 -Total 1
}
Remove-Item -LiteralPath $probeScript -Force -ErrorAction SilentlyContinue
