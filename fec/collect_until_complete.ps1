<#
.SYNOPSIS
  Drive the full-text collection to completion, retrying throttled failures
  automatically until nothing is left. Emits to the Glass Box.

.DESCRIPTION
  The collector finishes its queue and exits, leaving any HTTP 403/429 records
  quarantined. Nothing looped back on them, so the last handful of pages needed
  a human to notice and relaunch -- which is exactly the wrong place to need a
  human.

  This loops: rebuild the outstanding-records list, re-mint clearance if the
  browser lost it, relaunch, repeat. Pacing gets gentler as the queue shrinks,
  because the tail is almost always throttling rather than a bad page, and a
  small queue hammered fast just re-earns the block.

  Stops when the queue is empty, when a round makes no progress repeatedly, or
  on a wall-clock cap. Never deletes evidence; never bypasses a challenge -- if
  the browser stays challenged it waits.
#>
param(
    [string]$Workspace = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [string]$Generation = "audits\legfix5\congress_advanced_pages_20260725\text_relevance_httr_full_20260727z",
    [string]$Records = "audits\legfix5\congress_advanced_pages_20260725\congress_advanced_records.ndjson",
    [string]$RRuntime = "C:\Program Files\R\R-4.6.0\bin\x64\Rterm.exe",
    [string]$Python = "C:\Users\pgoff\AppData\Local\Programs\Python\Python312\python.exe",
    [string]$ChromeExe = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$ChromeProfile = "C:\Users\pgoff\.melange\chrome-harvest",
    [string]$EventsDirectory = "C:\Users\pgoff\.claude\glassbox\events",
    [int]$Port = 9222,
    [int]$CorpusTotal = 18557,
    [int]$MaxRounds = 40,
    [int]$MaxHours = 8,
    [int]$StallRoundsBeforeCooldown = 3,
    [int]$CooldownMinutes = 15,
    [string]$Lane = "codex"
)

$ErrorActionPreference = 'Stop'
$gen = Join-Path $Workspace $Generation
$receiptsDir = Join-Path $gen 'receipts'
$remaining = Join-Path $gen 'records_remaining.ndjson'
$runId = 'collect-until-complete-{0}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')
if (-not (Test-Path $EventsDirectory)) { New-Item -ItemType Directory $EventsDirectory -Force | Out-Null }

$mutex = New-Object System.Threading.Mutex($false, 'Global\MelangeCollectUntilComplete')
if (-not $mutex.WaitOne(0)) { Write-Host 'Another completion driver is running; exiting.'; return }

function Emit {
    param([string]$Status, [string]$Stage, [string]$Summary, [string]$Detail, [int]$Current)
    $payload = [ordered]@{
        schema_version = 1
        timestamp_utc = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
        lane = $Lane; source = 'congress-fulltext-completion'; run_id = $runId
        kind = 'collector.progress'; status = $Status; stage = $Stage
        summary = $Summary; detail = $Detail; current = $Current; total = $CorpusTotal
    }
    $n = ('evt-{0}-complete-{1}-{2}.json' -f `
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID, $Stage) -replace '[^A-Za-z0-9._-]+','-'
    try {
        ($payload | ConvertTo-Json -Depth 6) | Out-File -FilePath (Join-Path $EventsDirectory ($n + '.tmp')) -Encoding utf8
        Move-Item -LiteralPath (Join-Path $EventsDirectory ($n + '.tmp')) -Destination (Join-Path $EventsDirectory $n) -Force
    } catch { }
}

function Receipts { @(Get-ChildItem $receiptsDir -Recurse -File -Filter 'receipt.json' -ErrorAction SilentlyContinue).Count }

function Test-Port {
    try { $c = New-Object System.Net.Sockets.TcpClient; $ok = $c.ConnectAsync('127.0.0.1', $Port).Wait(3000); $c.Close(); return $ok }
    catch { return $false }
}

# Clearance is re-minted by letting the browser's own challenge complete. No
# challenge is solved or bypassed; if it stays challenged this waits.
$remintScript = Join-Path $env:TEMP ("cuc_remint_{0}.R" -f $PID)
$remintCode = @'
suppressPackageStartupMessages({ library(chromote) })
a <- commandArgs(trailingOnly = TRUE); port <- as.integer(a[[1]])
set_default_chromote_object(Chromote$new(browser = ChromeRemote$new(host="127.0.0.1", port=port)))
s <- ChromoteSession$new(); s$default_timeout <- 180
try({ s$Page$navigate("https://www.congress.gov/bill/117th-congress/house-bill/3664/text")
      s$Page$loadEventFired(wait_ = TRUE) }, silent = TRUE)
deadline <- Sys.time() + 90; ok <- FALSE
repeat {
  Sys.sleep(6)
  m <- tryCatch(s$Runtime$evaluate("document.body && document.body.innerText.indexOf('Shown Here:') >= 0")$result$value,
                error = function(e) FALSE)
  if (isTRUE(m)) { ok <- TRUE; break }
  if (Sys.time() > deadline) break
}
try(s$close(), silent = TRUE)
cat("REMINT_OK:", ok, "\n")
'@
# WITHOUT a BOM: Out-File -Encoding utf8 on PS 5.1 emits one and Rterm cannot parse it.
[System.IO.File]::WriteAllText($remintScript, $remintCode, (New-Object System.Text.UTF8Encoding($false)))

function Ensure-Browser {
    if (Test-Port) { return $true }
    Start-Process $ChromeExe -ArgumentList @(
        "--remote-debugging-port=$Port", "--user-data-dir=$ChromeProfile",
        '--no-first-run', '--no-default-browser-check',
        'https://www.congress.gov/bill/117th-congress/house-bill/3664/text') | Out-Null
    for ($i = 0; $i -lt 20; $i++) { Start-Sleep -Seconds 3; if (Test-Port) { return $true } }
    return $false
}

function Outstanding {
    & $Python (Join-Path $Workspace 'fec\legislation\build_remaining_records.py') `
        --records (Join-Path $Workspace $Records) --out-dir $gen --emit $remaining 2>&1 | Out-Null
    if (-not (Test-Path $remaining)) { return 0 }
    return @(Get-Content $remaining -ErrorAction SilentlyContinue | Where-Object { $_.Trim() }).Count
}

Emit -Status 'running' -Stage 'start' -Summary ("Completion driver armed at {0}/{1}" -f (Receipts), $CorpusTotal) `
     -Detail 'Retries throttled failures automatically until the queue is empty.' -Current (Receipts)

$deadline = (Get-Date).AddHours($MaxHours)
$stall = 0
for ($round = 1; $round -le $MaxRounds -and (Get-Date) -lt $deadline; $round++) {
    $left = Outstanding
    if ($left -le 0) {
        Emit -Status 'completed' -Stage 'complete' -Summary ("Collection COMPLETE at {0}/{1}" -f (Receipts), $CorpusTotal) `
             -Detail 'No outstanding records remain.' -Current (Receipts)
        break
    }

    if (-not (Ensure-Browser)) {
        Emit -Status 'blocked' -Stage 'no-browser' -Summary 'Chrome unavailable; waiting' -Detail '' -Current (Receipts)
        Start-Sleep -Seconds 120; continue
    }
    $remint = (& $RRuntime --no-echo --no-restore --file="$remintScript" --args $Port 2>&1 | Out-String)
    if ($remint -notmatch 'REMINT_OK:\s*TRUE') {
        Emit -Status 'blocked' -Stage 'challenged' `
             -Summary ("Site challenged; {0} record(s) outstanding, waiting {1} min" -f $left, $CooldownMinutes) `
             -Detail 'No bypass attempted.' -Current (Receipts)
        Start-Sleep -Seconds ($CooldownMinutes * 60); continue
    }

    # Small tail => almost certainly throttling, so go gentle rather than fast.
    $workers = if ($left -le 25) { 2 } elseif ($left -le 200) { 3 } else { 6 }
    $delay   = if ($left -le 25) { 5 } elseif ($left -le 200) { 3 } else { 1 }

    $before = Receipts
    $lock = Join-Path $gen '.collector-lock'
    if ((@(Get-Process Rterm -ErrorAction SilentlyContinue)).Count -eq 0 -and (Test-Path $lock)) {
        Remove-Item -LiteralPath $lock -Recurse -Force -ErrorAction SilentlyContinue
    }
    $log = Join-Path $gen ('completion_round{0:d2}.log' -f $round)
    $args = @('--no-echo','--no-restore','--file=fec\harvest_congress_text_httr.R','--args',
              '--records', $remaining, '--out', $Generation,
              '--limit','0','--workers',"$workers",'--delay',"$delay",
              '--host','127.0.0.1','--port',"$Port",'--resume')
    $proc = Start-Process $RRuntime -ArgumentList $args -WorkingDirectory $Workspace -PassThru `
        -RedirectStandardOutput $log -RedirectStandardError ($log + '.err')
    $proc.WaitForExit()

    $after = Receipts
    $gained = $after - $before
    Emit -Status 'running' -Stage 'round' `
         -Summary ("Round {0}: +{1} collected, {2} were outstanding, now {3}/{4}" -f $round, $gained, $left, $after, $CorpusTotal) `
         -Detail ("workers={0} delay={1}s" -f $workers, $delay) -Current $after

    if ($gained -le 0) {
        $stall++
        if ($stall -ge $StallRoundsBeforeCooldown) {
            Emit -Status 'blocked' -Stage 'cooldown' `
                 -Summary ("{0} rounds with no progress; cooling down {1} min" -f $stall, $CooldownMinutes) `
                 -Detail 'A rate-limit penalty expires on idleness; retrying through it sustains it.' -Current $after
            Start-Sleep -Seconds ($CooldownMinutes * 60)
            $stall = 0
        }
    } else { $stall = 0 }
}

$final = Receipts
Emit -Status $(if ($final -ge $CorpusTotal) { 'completed' } else { 'needs-review' }) -Stage 'exit' `
     -Summary ("Completion driver exiting at {0}/{1}" -f $final, $CorpusTotal) `
     -Detail 'Any still-outstanding record retains an explicit failure artifact.' -Current $final
Remove-Item -LiteralPath $remintScript -Force -ErrorAction SilentlyContinue
$mutex.ReleaseMutex(); $mutex.Dispose()
