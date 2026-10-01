<#
.SYNOPSIS
  Keep overall_progress.json current so the GLASS BOX bar shows live corpus
  coverage. Does nothing else.

.DESCRIPTION
  The collector's own progress.json counts only the FILTERED remaining queue, so
  a viewer bound to it reports a much smaller percentage than real coverage.
  overall_progress.json carries collected/18557 instead, and the Glass Box codex
  view reads it first.

  That file used to be written by the clearance supervisor. Running two
  supervisors at once caused duplicate collector launches and immutable-receipt
  collisions, so the supervisor is not always running. This does the one job the
  bar depends on and nothing more: it never starts, stops, or touches the
  collector, and it never writes to congress.gov.

  Read-only apart from overall_progress.json and its Glass Box event mirror.
#>
param(
    [string]$Workspace = "C:\Users\pgoff\OneDrive\Desktop\Melange Systems",
    [string]$Generation = "audits\legfix5\congress_advanced_pages_20260725\text_relevance_httr_full_20260727z",
    [string]$EventsDirectory = "C:\Users\pgoff\.claude\glassbox\events",
    [int]$CorpusTotal = 18557,
    [int]$IntervalSeconds = 20,
    [int]$MaxHours = 24,
    [string]$Lane = "codex"
)

$ErrorActionPreference = 'Stop'
$gen = Join-Path $Workspace $Generation
$receipts = Join-Path $gen 'receipts'
$overall = Join-Path $gen 'overall_progress.json'
$runId = 'congress-fulltext-overall'
if (-not (Test-Path $EventsDirectory)) { New-Item -ItemType Directory $EventsDirectory -Force | Out-Null }

# Only one updater should run; a second would just duplicate events.
$mutex = New-Object System.Threading.Mutex($false, 'Global\MelangeOverallProgressUpdater')
if (-not $mutex.WaitOne(0)) {
    Write-Host 'Another overall-progress updater is already running; exiting.'
    return
}

$deadline = (Get-Date).AddHours($MaxHours)
$previous = -1
try {
    while ((Get-Date) -lt $deadline) {
        $count = 0
        if (Test-Path $receipts) {
            $count = @(Get-ChildItem $receipts -Recurse -File -Filter 'receipt.json' -ErrorAction SilentlyContinue).Count
        }
        # Bills that exist but have no published text (BillStatus text_versions = [])
        # can never yield a receipt, so they are accounted for here rather than
        # left as a permanent shortfall against the corpus total.
        $accountedNoText = 0
        $noTextPath = Join-Path $gen 'accounted_no_text.json'
        if (Test-Path $noTextPath) {
            try { $accountedNoText = @((Get-Content $noTextPath -Raw | ConvertFrom-Json).keys).Count } catch { }
        }
        $count = $count + $accountedNoText
        $pct = if ($CorpusTotal -gt 0) { [math]::Round(100.0 * $count / $CorpusTotal, 1) } else { 0 }
        $collectorAlive = (@(Get-Process Rterm -ErrorAction SilentlyContinue)).Count -gt 0
        $status = if ($count -ge $CorpusTotal) { 'completed' } elseif ($collectorAlive) { 'running' } else { 'blocked' }

        $payload = [ordered]@{
            schema_version = 1
            updated_at = (Get-Date).ToUniversalTime().ToString('yyyy-MM-dd HH:mm:ss') + ' UTC'
            lane = $Lane
            source = 'congress-full-text'
            run_id = $runId
            kind = 'collector.progress'
            status = $status
            stage = 'collecting'
            current = $count
            total = $CorpusTotal
            summary = ('{0} / {1} pages ({2}%)' -f $count, $CorpusTotal, $pct)
            detail = if ($collectorAlive) { 'Congress.gov official full text; collector running.' }
                     else { 'Congress.gov official full text; collector not running.' }
            output_directory = $gen
        }

        try {
            ($payload | ConvertTo-Json -Depth 6) | Out-File -FilePath ($overall + '.tmp') -Encoding utf8
            Move-Item -LiteralPath ($overall + '.tmp') -Destination $overall -Force
        } catch { }

        # Mirror to the shared stream only when the number actually moves, so the
        # feed does not fill with identical heartbeats.
        if ($count -ne $previous) {
            $previous = $count
            $name = ('evt-{0}-overall-{1}-progress.json' -f `
                (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssfff'), $PID) -replace '[^A-Za-z0-9._-]+','-'
            try {
                ($payload | ConvertTo-Json -Depth 6) | Out-File -FilePath (Join-Path $EventsDirectory ($name + '.tmp')) -Encoding utf8
                Move-Item -LiteralPath (Join-Path $EventsDirectory ($name + '.tmp')) -Destination (Join-Path $EventsDirectory $name) -Force
            } catch { }
        }

        Start-Sleep -Seconds $IntervalSeconds
    }
} finally {
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}
