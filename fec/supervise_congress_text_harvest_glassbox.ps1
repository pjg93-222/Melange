<#
.SYNOPSIS
  Supervise the long-running congress.gov official-text harvest and emit every
  observation to the shared GLASS BOX stream.

.DESCRIPTION
  The harvest (fec\harvest_congress_text_httr.R) replays cookies from a headful
  Chrome on 127.0.0.1:9222. Cloudflare periodically re-issues a managed
  challenge, which invalidates cf_clearance; the collector's own circuit breaker
  then re-reads the browser cookie jar. That recovery only works if the BROWSER
  itself still holds a valid clearance, so this supervisor keeps the browser
  warm by driving it to a normal bill-text page when the lane stalls.

  Driving the browser to a normal URL and letting Cloudflare's own JavaScript
  run is ordinary browsing. This script NEVER attempts to solve, bypass, or
  automate past a challenge. If the browser itself stays challenged, the
  correct and only action is to wait, which is what this script does.

  Safety properties:
    * Never deletes or overwrites harvest evidence (receipts, accepted_html,
      quarantine, failure_attempts, batches). Read-only against the out dir
      except for its own state file.
    * Refuses to launch a second collector while one is alive -- concurrent
      writers would trip the immutable-receipt collision guard.
    * Refuses to launch once manifest.json exists (the run is terminal).
    * Relaunches use the SAME command with --resume, and write to a NEW log
      file per attempt so no prior log is truncated.
#>
param(
    [string]$Workspace        = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [string]$OutRelative      = "audits\legfix5\congress_advanced_pages_20260725\text_relevance_httr_full_20260727z",
    [string]$RecordsRelative  = "audits\legfix5\congress_advanced_pages_20260725\congress_advanced_records.ndjson",
    [string]$PriorReceipts    = "audits\legfix5\congress_advanced_pages_20260725\text_relevance_httr_full_stage_20260726\receipts",
    [string]$LogBase          = "audits\legfix5\congress_advanced_pages_20260725\full_harvest_20260727z",
    [string]$EventsDirectory  = "C:\Users\pgoff\.claude\glassbox\events",
    [string]$RRuntime         = "C:\Program Files\R\R-4.6.0\bin\x64\Rterm.exe",
    [string]$ChromeExe        = "C:\Program Files\Google\Chrome\Application\chrome.exe",
    [string]$ChromeProfile    = "C:\Users\pgoff\.melange\chrome-harvest",
    [string]$WarmUrl          = "https://www.congress.gov/bill/117th-congress/house-bill/3664/text",
    [int]$Port                = 9222,
    [int]$IntervalSeconds     = 60,
    [int]$StallSeconds        = 600,
    [int]$RemintCooldownSec   = 900,
    [int]$MaxRelaunches       = 40,
    [int]$MaxHours            = 12,
    [int]$Workers             = 6,
    [string]$Lane             = "codex"
)

$ErrorActionPreference = 'Continue'

$outDir       = Join-Path $Workspace $OutRelative
$progressPath = Join-Path $outDir 'progress.json'
$manifestPath = Join-Path $outDir 'manifest.json'
$statePath    = Join-Path $outDir 'supervisor_state.json'
$total        = 18557

if (-not (Test-Path $EventsDirectory)) { New-Item -ItemType Directory $EventsDirectory -Force | Out-Null }

$runId    = 'congress-text-supervisor-{0}' -f (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmss')
$deadline = (Get-Date).AddHours($MaxHours)
$cycle    = 0

# Tally survives supervisor restarts.
$state = @{ relaunches = 0; reminted = 0; blocks_seen = 0; browser_challenged = 0 }
if (Test-Path $statePath) {
    try {
        $prior = Get-Content $statePath -Raw | ConvertFrom-Json
        foreach ($k in @('relaunches','reminted','blocks_seen','browser_challenged')) {
            if ($null -ne $prior.$k) { $state[$k] = [int]$prior.$k }
        }
    } catch { }
}

function Save-State {
    try { ($state | ConvertTo-Json -Depth 4) | Out-File -FilePath $statePath -Encoding utf8 } catch { }
}

function Write-GlassboxEvent {
    param([hashtable]$Payload, [string]$Tag)
    $name = ('evt-{0}-supervisor-{1}-{2}.json' -f `
        (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID, $Tag) -replace '[^A-Za-z0-9._-]+', '-'
    $tmp = Join-Path $EventsDirectory ($name + '.tmp')
    try {
        ($Payload | ConvertTo-Json -Depth 6) | Out-File -FilePath $tmp -Encoding utf8
        Move-Item -LiteralPath $tmp -Destination (Join-Path $EventsDirectory $name) -Force
    } catch { }
}

function Emit {
    param([string]$Tag, [string]$Status, [string]$Stage, [string]$Summary, [string]$Detail,
          [int]$Current = 0, [hashtable]$Extra)
    $payload = @{
        schema_version = 1
        timestamp_utc  = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
        lane           = $Lane
        source         = 'congress-text-harvest-supervisor'
        run_id         = $runId
        kind           = 'supervisor.progress'
        status         = $Status
        stage          = $Stage
        summary        = $Summary
        detail         = $Detail
        current        = $Current
        total          = $total
        cycle          = $cycle
        relaunches     = $state.relaunches
        clearance_remints = $state.reminted
        blocks_seen    = $state.blocks_seen
    }
    if ($Extra) { foreach ($k in $Extra.Keys) { $payload[$k] = $Extra[$k] } }
    Write-GlassboxEvent -Payload $payload -Tag $Tag
}

function Get-CollectorProcess {
    # Match on the script name, not just the image name: another R job must not
    # be mistaken for this collector (and vice versa).
    try {
        Get-CimInstance Win32_Process -Filter "Name='Rterm.exe'" -ErrorAction Stop |
            Where-Object { $_.CommandLine -match 'harvest_congress_text_httr\.R' } |
            Select-Object -First 1
    } catch { $null }
}

function Test-DebuggerUp {
    try {
        $v = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/version" -TimeoutSec 10
        return [bool]$v.Browser
    } catch { return $false }
}

function Start-HarvestChrome {
    Start-Process -FilePath $ChromeExe -ArgumentList @(
        "--remote-debugging-port=$Port",
        "--user-data-dir=$ChromeProfile",
        "--no-first-run",
        "--no-default-browser-check",
        $WarmUrl
    ) | Out-Null
    Start-Sleep -Seconds 25
}

function Invoke-BrowserWarm {
    <#
      Open the bill-text page in the harvest browser and let it load. Cloudflare
      runs its own JS; if a challenge is present the browser clears it the way a
      human visit would. Nothing here inspects or answers a challenge.
      Returns: 'clear', 'challenged', or 'unreachable'.
    #>
    if (-not (Test-DebuggerUp)) { return 'unreachable' }
    $tabId = $null
    # Verified live 2026-07-27: Chrome 150 accepts the raw (unescaped) URL as the
    # query string. The percent-encoded form is NOT accepted, so do not "fix" this.
    try {
        $tab = Invoke-RestMethod -Method Put -Uri "http://127.0.0.1:$Port/json/new?$WarmUrl" -TimeoutSec 30
        $tabId = $tab.id
    } catch { return 'unreachable' }
    # Give Cloudflare's own JS time to run and settle.
    Start-Sleep -Seconds 30
    $title = ''
    try {
        $list = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/list" -TimeoutSec 15
        $me = $list | Where-Object { $_.id -eq $tabId } | Select-Object -First 1
        if ($me) { $title = [string]$me.title }
    } catch { }
    if ($tabId) { try { Invoke-RestMethod -Uri "http://127.0.0.1:$Port/json/close/$tabId" -TimeoutSec 15 | Out-Null } catch { } }
    if ($title -match 'Congress\.gov') { return 'clear' }
    if ($title -match 'Just a moment|Attention Required|moment') { return 'challenged' }
    if ([string]::IsNullOrWhiteSpace($title)) { return 'challenged' }
    return 'challenged'
}

function Start-Collector {
    if (Test-Path $manifestPath) { return 'terminal' }
    if (Get-CollectorProcess)   { return 'already-running' }
    if ($state.relaunches -ge $MaxRelaunches) { return 'cap-reached' }
    if (-not (Test-DebuggerUp)) {
        Start-HarvestChrome
        if (-not (Test-DebuggerUp)) { return 'no-browser' }
    }
    $attempt = $state.relaunches + 1
    $log = Join-Path $Workspace ("{0}.r{1}.log" -f $LogBase, $attempt)
    $err = "$log.err"
    $argList = @(
        '--no-echo', '--no-restore', '--file=fec\harvest_congress_text_httr.R', '--args',
        '--records', $RecordsRelative,
        '--out', $OutRelative,
        '--prior_receipts', $PriorReceipts,
        '--limit', '0', '--workers', "$Workers", '--attempts', '6',
        '--min_delay', '2', '--max_delay', '300',
        '--host', '127.0.0.1', '--port', "$Port", '--resume'
    )
    try {
        Start-Process -FilePath $RRuntime -ArgumentList $argList -WorkingDirectory $Workspace `
            -RedirectStandardOutput $log -RedirectStandardError $err -WindowStyle Hidden | Out-Null
    } catch {
        Emit -Tag 'relaunch-failed' -Status 'failed' -Stage 'relaunch' `
             -Summary 'Collector relaunch threw' -Detail $_.Exception.Message
        return 'launch-error'
    }
    $state.relaunches = $attempt
    Save-State
    Start-Sleep -Seconds 20
    if (Get-CollectorProcess) { return 'launched' }
    return 'launch-died'
}

Emit -Tag 'start' -Status 'running' -Stage 'supervise' `
     -Summary 'Harvest supervisor armed' `
     -Detail ("Watching {0} every {1}s; stall threshold {2}s; relaunch cap {3}." -f $OutRelative, $IntervalSeconds, $StallSeconds, $MaxRelaunches)

$lastCurrent = -1
$lastAdvance = Get-Date
$lastRemint  = (Get-Date).AddSeconds(-$RemintCooldownSec)

while ((Get-Date) -lt $deadline) {
    $cycle++

    $prog = $null
    try { $prog = Get-Content $progressPath -Raw -ErrorAction Stop | ConvertFrom-Json } catch { }
    $current  = 0
    $pstatus  = 'unknown'
    $pdetail  = ''
    $rate     = 0
    $failures = 0
    if ($prog) {
        if ($null -ne $prog.current)       { $current  = [int]$prog.current }
        if ($null -ne $prog.status)        { $pstatus  = [string]$prog.status }
        if ($null -ne $prog.detail)        { $pdetail  = [string]$prog.detail }
        if ($null -ne $prog.rate)          { $rate     = [double]$prog.rate }
        if ($null -ne $prog.failure_count) { $failures = [int]$prog.failure_count }
    }

    $proc  = Get-CollectorProcess
    $alive = [bool]$proc

    if ($current -gt $lastCurrent) { $lastCurrent = $current; $lastAdvance = Get-Date }
    $stalledFor = [int]((Get-Date) - $lastAdvance).TotalSeconds

    if ($pdetail -match 'Full-batch block detected') {
        $state.blocks_seen++
        Save-State
        Emit -Tag 'block' -Status 'blocked' -Stage 'cloudflare-block' -Current $current `
             -Summary ("Cloudflare full-batch block at {0}/{1}" -f $current, $total) `
             -Detail ("Collector circuit breaker fired; cooling down and re-minting clearance from the live browser. detail={0}" -f $pdetail) `
             -Extra @{ failure_count = $failures }
    }

    # Terminal: the collector wrote its manifest.
    if (Test-Path $manifestPath) {
        $mf = $null
        try { $mf = Get-Content $manifestPath -Raw | ConvertFrom-Json } catch { }
        $acct = 0; $skip = 'unknown'
        if ($mf) {
            if ($null -ne $mf.accounted_record_count)     { $acct = [int]$mf.accounted_record_count }
            if ($null -ne $mf.failures_silently_skipped)  { $skip = [string]$mf.failures_silently_skipped }
        }
        Emit -Tag 'terminal' -Status 'completed' -Stage 'manifest-written' -Current $current `
             -Summary ("Harvest terminal: manifest written, accounted={0}/{1}" -f $acct, $total) `
             -Detail ("status={0} failures_silently_skipped={1} relaunches={2} remints={3} blocks={4}" -f `
                      $(if ($mf) { $mf.status } else { 'unreadable' }), $skip, $state.relaunches, $state.reminted, $state.blocks_seen)
        break
    }

    if (-not $alive) {
        # Process gone with no manifest -> it died. Warm the browser first so the
        # fresh process finds a valid cf_clearance at startup (it hard-stops
        # without one), then relaunch with --resume.
        $warm = Invoke-BrowserWarm
        if ($warm -eq 'clear') { $state.reminted++; Save-State }
        if ($warm -eq 'challenged') { $state.browser_challenged++; Save-State }

        if ($warm -ne 'clear') {
            Emit -Tag 'wait-browser' -Status 'blocked' -Stage 'await-clearance' -Current $current `
                 -Summary 'Collector down and browser not clear; waiting rather than hammering' `
                 -Detail ("Browser state={0}. Not relaunching: the collector aborts at startup without cf_clearance. Re-testing next cycle." -f $warm)
            Start-Sleep -Seconds ([Math]::Max($IntervalSeconds, 300))
            continue
        }

        $res = Start-Collector
        Emit -Tag 'relaunch' -Status $(if ($res -eq 'launched') { 'running' } else { 'needs-review' }) `
             -Stage 'relaunch' -Current $current `
             -Summary ("Collector was down; relaunch result={0}" -f $res) `
             -Detail ("Same command with --resume; already-collected pages are skipped without a request. relaunch #{0} of cap {1}." -f $state.relaunches, $MaxRelaunches)
        if ($res -eq 'cap-reached' -or $res -eq 'terminal') { break }
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    # Alive but not advancing for a long stretch -> keep the browser's clearance
    # fresh so the collector's next breaker re-mint finds a usable token.
    if ($stalledFor -ge $StallSeconds -and ((Get-Date) - $lastRemint).TotalSeconds -ge $RemintCooldownSec) {
        $lastRemint = Get-Date
        $warm = Invoke-BrowserWarm
        if ($warm -eq 'clear') { $state.reminted++ } else { $state.browser_challenged++ }
        Save-State
        Emit -Tag 'warm' -Status $(if ($warm -eq 'clear') { 'running' } else { 'blocked' }) `
             -Stage 'browser-warm' -Current $current `
             -Summary ("Lane stalled {0}s at {1}/{2}; browser warm result={3}" -f $stalledFor, $current, $total, $warm) `
             -Detail 'Opened the bill-text page in the harvest browser and let Cloudflare JS settle. No challenge was solved, bypassed, or automated.'
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }

    Emit -Tag 'heartbeat' -Status 'running' -Stage 'native-chrome-cookie-replay-httr' -Current $current `
         -Summary ("{0}/{1} official pages ({2:N1}/min)" -f $current, $total, $rate) `
         -Detail ("pid={0} stalled_for={1}s failures={2} progress_status={3} :: {4}" -f `
                  $proc.ProcessId, $stalledFor, $failures, $pstatus, $pdetail) `
         -Extra @{ failure_count = $failures; records_per_minute = $rate; collector_pid = $proc.ProcessId }

    Start-Sleep -Seconds $IntervalSeconds
}

Emit -Tag 'stop' -Status 'completed' -Stage 'supervise' -Current $lastCurrent `
     -Summary 'Harvest supervisor exiting' `
     -Detail ("cycles={0} relaunches={1} remints={2} blocks={3} browser_challenged={4}" -f `
              $cycle, $state.relaunches, $state.reminted, $state.blocks_seen, $state.browser_challenged)
Save-State
