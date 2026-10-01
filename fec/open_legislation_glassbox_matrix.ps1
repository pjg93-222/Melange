param(
    [string]$RunDirectory = "audits\legfix5\identifier_probe_fast_20260726",
    [int]$RefreshMilliseconds = 750,
    [int]$PageArtifactsPerTick = 2,
    [int]$QueryArtifactsPerTick = 6,
    [int]$FailureArtifactsPerTick = 6
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[System.Windows.Forms.Application]::EnableVisualStyles()

$Workspace = Split-Path -Parent $PSScriptRoot
if ([System.IO.Path]::IsPathRooted($RunDirectory)) {
    $RunPath = [System.IO.Path]::GetFullPath($RunDirectory)
}
else {
    $RunPath = [System.IO.Path]::GetFullPath((Join-Path $Workspace $RunDirectory))
}
$ProgressPath = Join-Path $RunPath "progress.json"
$QueryPath = Join-Path $RunPath "queries"
$PagePath = Join-Path $RunPath "raw\pages"
$FailurePath = Join-Path $RunPath "failure_receipts"
$CollectorCommand = (
    "node fec\collect\collect_congress_identifier_fast.mjs --workers 6 " +
    "--endpoint http://127.0.0.1:9222 --resume"
)

function Read-JsonSafe {
    param([string]$Path)
    try {
        return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 |
            ConvertFrom-Json
    }
    catch {
        return $null
    }
}

function Format-Seconds {
    param($Seconds)
    if ($null -eq $Seconds) { return "--" }
    $value = [Math]::Max(0, [int][Math]::Ceiling([double]$Seconds))
    if ($value -lt 60) { return "${value}s" }
    if ($value -lt 3600) { return "$([Math]::Ceiling($value / 60))m" }
    return "$([Math]::Floor($value / 3600))h $([Math]::Ceiling(($value % 3600) / 60))m"
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "GLASS BOX - LEGISLATION HARVEST MATRIX"
$form.BackColor = [System.Drawing.Color]::FromArgb(15, 18, 24)
$form.ForeColor = [System.Drawing.Color]::Gainsboro
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(1540, 940)
$form.MinimumSize = New-Object System.Drawing.Size(1100, 700)
$form.Font = New-Object System.Drawing.Font("Consolas", 9)

$split = New-Object System.Windows.Forms.SplitContainer
$split.Dock = "Fill"
$split.Orientation = "Horizontal"
$split.SplitterDistance = 270
$split.IsSplitterFixed = $false
$split.BackColor = [System.Drawing.Color]::FromArgb(42, 48, 58)
$form.Controls.Add($split)

$overhead = $split.Panel1
$overhead.BackColor = [System.Drawing.Color]::FromArgb(15, 18, 24)
$feedPanel = $split.Panel2
$feedPanel.BackColor = [System.Drawing.Color]::FromArgb(10, 12, 17)

$title = New-Object System.Windows.Forms.Label
$title.Text = "OVERHEAD / CONGRESS.GOV IDENTIFIER HARVEST"
$title.ForeColor = [System.Drawing.Color]::White
$title.Font = New-Object System.Drawing.Font("Consolas", 14, [System.Drawing.FontStyle]::Bold)
$title.Location = New-Object System.Drawing.Point(15, 12)
$title.AutoSize = $true
$overhead.Controls.Add($title)

$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Text = "Starting matrix observer..."
$statusLabel.ForeColor = [System.Drawing.Color]::Cyan
$statusLabel.Font = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Bold)
$statusLabel.Location = New-Object System.Drawing.Point(16, 45)
$statusLabel.Size = New-Object System.Drawing.Size(1480, 25)
$overhead.Controls.Add($statusLabel)

$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Minimum = 0
$progressBar.Maximum = 210
$progressBar.Value = 0
$progressBar.Style = "Continuous"
$progressBar.Location = New-Object System.Drawing.Point(18, 74)
$progressBar.Size = New-Object System.Drawing.Size(1480, 24)
$progressBar.Anchor = "Top,Left,Right"
$overhead.Controls.Add($progressBar)

$commandLabel = New-Object System.Windows.Forms.Label
$commandLabel.Text = "COMMAND  $CollectorCommand"
$commandLabel.ForeColor = [System.Drawing.Color]::LightGray
$commandLabel.Location = New-Object System.Drawing.Point(18, 105)
$commandLabel.Size = New-Object System.Drawing.Size(1480, 19)
$commandLabel.Anchor = "Top,Left,Right"
$overhead.Controls.Add($commandLabel)

$privacyLabel = New-Object System.Windows.Forms.Label
$privacyLabel.Text = "TRANSPORT  visible Chrome CDP :9222 | 6 workers | no retry waits | cookie values never displayed"
$privacyLabel.ForeColor = [System.Drawing.Color]::DarkGray
$privacyLabel.Location = New-Object System.Drawing.Point(18, 127)
$privacyLabel.Size = New-Object System.Drawing.Size(1480, 19)
$privacyLabel.Anchor = "Top,Left,Right"
$overhead.Controls.Add($privacyLabel)

$workerGrid = New-Object System.Windows.Forms.DataGridView
$workerGrid.Location = New-Object System.Drawing.Point(18, 152)
$workerGrid.Size = New-Object System.Drawing.Size(1480, 105)
$workerGrid.Anchor = "Top,Bottom,Left,Right"
$workerGrid.BackgroundColor = [System.Drawing.Color]::FromArgb(20, 24, 31)
$workerGrid.BorderStyle = "FixedSingle"
$workerGrid.EnableHeadersVisualStyles = $false
$workerGrid.ColumnHeadersDefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(38, 45, 56)
$workerGrid.ColumnHeadersDefaultCellStyle.ForeColor = [System.Drawing.Color]::White
$workerGrid.DefaultCellStyle.BackColor = [System.Drawing.Color]::FromArgb(20, 24, 31)
$workerGrid.DefaultCellStyle.ForeColor = [System.Drawing.Color]::Gainsboro
$workerGrid.DefaultCellStyle.SelectionBackColor = [System.Drawing.Color]::FromArgb(20, 24, 31)
$workerGrid.DefaultCellStyle.SelectionForeColor = [System.Drawing.Color]::Gainsboro
$workerGrid.RowHeadersVisible = $false
$workerGrid.AllowUserToAddRows = $false
$workerGrid.AllowUserToDeleteRows = $false
$workerGrid.AllowUserToResizeRows = $false
$workerGrid.ReadOnly = $true
$workerGrid.AutoSizeColumnsMode = "Fill"
[void]$workerGrid.Columns.Add("worker", "WORKER")
[void]$workerGrid.Columns.Add("state", "STATE")
[void]$workerGrid.Columns.Add("query", "CURRENT INPUT / QUERY ID")
$workerGrid.Columns[0].FillWeight = 12
$workerGrid.Columns[1].FillWeight = 16
$workerGrid.Columns[2].FillWeight = 72
$overhead.Controls.Add($workerGrid)

$feedTitle = New-Object System.Windows.Forms.Label
$feedTitle.Text = "LIVE FEED / COMMANDS + INPUTS + OUTPUTS + RECORDS"
$feedTitle.ForeColor = [System.Drawing.Color]::White
$feedTitle.Font = New-Object System.Drawing.Font("Consolas", 11, [System.Drawing.FontStyle]::Bold)
$feedTitle.Location = New-Object System.Drawing.Point(10, 7)
$feedTitle.AutoSize = $true
$feedPanel.Controls.Add($feedTitle)

$feed = New-Object System.Windows.Forms.RichTextBox
$feed.Location = New-Object System.Drawing.Point(10, 31)
$feed.Size = New-Object System.Drawing.Size(1500, 600)
$feed.Anchor = "Top,Bottom,Left,Right"
$feed.BackColor = [System.Drawing.Color]::FromArgb(8, 10, 14)
$feed.ForeColor = [System.Drawing.Color]::Gainsboro
$feed.BorderStyle = "FixedSingle"
$feed.ReadOnly = $true
$feed.WordWrap = $false
$feed.DetectUrls = $false
$feed.Font = New-Object System.Drawing.Font("Consolas", 9)
$feedPanel.Controls.Add($feed)

function Add-Feed {
    param(
        [string]$Text,
        [System.Drawing.Color]$Color = [System.Drawing.Color]::Gainsboro
    )
    if (-not $Text) { return }
    $feed.SelectionStart = $feed.TextLength
    $feed.SelectionLength = 0
    $feed.SelectionColor = $Color
    $feed.AppendText($Text)
    if (-not $Text.EndsWith("`r`n")) {
        $feed.AppendText("`r`n")
    }
    $feed.SelectionColor = $feed.ForeColor
    $feed.SelectionStart = $feed.TextLength
    $feed.ScrollToCaret()
}

function Add-PageArtifact {
    param(
        [object]$Page,
        [string]$File
    )
    $stamp = Get-Date -Format "HH:mm:ss.fff"
    $range = $Page.result_range
    $rangeText = "$($range.start)-$($range.end) of $($range.total)"
    Add-Feed (
        "`r`n[$stamp] OUTPUT PAGE  query=$($Page.query_id)  page=$($Page.page_number)  " +
        "range=$rangeText  transport=$($Page.result_transport)"
    ) ([System.Drawing.Color]::LimeGreen)
    Add-Feed ("  COMMAND  GET " + [string]$Page.requested_url) ([System.Drawing.Color]::DeepSkyBlue)
    Add-Feed ("  INPUT    " + [string]$Page.advanced_search_query) ([System.Drawing.Color]::Khaki)
    Add-Feed ("  RESOLVED " + [string]$Page.loaded_url) ([System.Drawing.Color]::DarkGray)
    $transport = $Page.transport_provenance
    if ($null -ne $transport) {
        Add-Feed (
            "  RESPONSE sha256=$($transport.response_body_sha256) " +
            "bytes=$($transport.response_body_byte_length) attempts=$($transport.http_attempt_count)"
        ) ([System.Drawing.Color]::DarkGray)
    }
    Add-Feed ("  ARTIFACT " + $File) ([System.Drawing.Color]::DarkGray)
    foreach ($record in @($Page.records)) {
        $titleText = ([string]$record.title -replace "\s+", " ").Trim()
        $sponsorText = ([string]$record.sponsor -replace "\s+", " ").Trim()
        Add-Feed (
            "    RECORD $($record.canonical_key) | $($record.display_number) | " +
            "$titleText | sponsor=$sponsorText | date=$($record.initial_action_date_iso)"
        ) ([System.Drawing.Color]::Gainsboro)
        Add-Feed ("           " + [string]$record.result_url) ([System.Drawing.Color]::DimGray)
    }
}

function Add-QueryArtifact {
    param(
        [object]$Query,
        [string]$File
    )
    $stamp = Get-Date -Format "HH:mm:ss.fff"
    Add-Feed (
        "`r`n[$stamp] QUERY COMPLETE  id=$($Query.query_id)  results=$($Query.result_total)  " +
        "pages=$($Query.page_count)  transport=$($Query.result_transport)"
    ) ([System.Drawing.Color]::Cyan)
    Add-Feed ("  INPUT  " + [string]$Query.advanced_search_query) ([System.Drawing.Color]::Khaki)
    Add-Feed (
        "  OUTPUT unique=$($Query.unique_record_count) records_sha256=$($Query.records_sha256)"
    ) ([System.Drawing.Color]::LightGreen)
    Add-Feed ("  ARTIFACT " + $File) ([System.Drawing.Color]::DarkGray)
}

function Add-FailureArtifact {
    param(
        [object]$Failure,
        [string]$File
    )
    $stamp = Get-Date -Format "HH:mm:ss.fff"
    Add-Feed (
        "`r`n[$stamp] QUARANTINED  query=$($Failure.query_id)  worker=$($Failure.worker)  " +
        "type=$($Failure.name)"
    ) ([System.Drawing.Color]::OrangeRed)
    Add-Feed ("  ERROR    " + [string]$Failure.message) ([System.Drawing.Color]::Orange)
    Add-Feed ("  INPUT    " + [string]$Failure.requested_url) ([System.Drawing.Color]::Khaki)
    if ($null -ne $Failure.transport) {
        try {
            $transportText = $Failure.transport | ConvertTo-Json -Depth 10 -Compress
            Add-Feed ("  OUTPUT   " + $transportText) ([System.Drawing.Color]::DarkGray)
        }
        catch { }
    }
    Add-Feed ("  RECEIPT  " + $File) ([System.Drawing.Color]::DarkGray)
}

$seenPages = @{}
$seenQueries = @{}
$seenFailures = @{}
$lastProgressSignature = ""
$initialBannerWritten = $false

function Refresh-Matrix {
    if (-not $initialBannerWritten) {
        Add-Feed ("GLASS BOX MATRIX ATTACHED  " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss")) ([System.Drawing.Color]::White)
        Add-Feed ("COMMAND  " + $CollectorCommand) ([System.Drawing.Color]::DeepSkyBlue)
        Add-Feed ("RUN PATH " + $RunPath) ([System.Drawing.Color]::DarkGray)
        Add-Feed "Replaying preserved artifacts, then following all new accepted page/query evidence live." ([System.Drawing.Color]::DarkGray)
        $script:initialBannerWritten = $true
    }

    $progress = Read-JsonSafe $ProgressPath
    if ($null -ne $progress) {
        $completed = [Math]::Max(0, [Math]::Min(210, [int]$progress.completed_queries))
        $progressBar.Value = $completed
        $percent = [Math]::Floor(($completed / 210.0) * 100)
        $eta = Format-Seconds $progress.eta_seconds
        $statusLabel.Text = (
            "$completed/210 ($percent%) | pages=$($progress.accepted_pages) | " +
            "workers=$($progress.active_workers) | $($progress.queries_per_minute) q/min | " +
            "failures=$($progress.failure_count) | ETA $eta | $([string]$progress.status).ToUpperInvariant()"
        )
        if ([int]$progress.failure_count -gt 0) {
            $statusLabel.ForeColor = [System.Drawing.Color]::OrangeRed
        }
        elseif ([string]$progress.status -eq "complete") {
            $statusLabel.ForeColor = [System.Drawing.Color]::LimeGreen
        }
        else {
            $statusLabel.ForeColor = [System.Drawing.Color]::Cyan
        }

        $workerGrid.Rows.Clear()
        $activeByWorker = @{}
        foreach ($active in @($progress.active_worker_ids)) {
            $activeByWorker[[int]$active.worker] = [string]$active.query_id
        }
        for ($worker = 1; $worker -le 6; $worker += 1) {
            $state = if ($activeByWorker.ContainsKey($worker)) { "FETCH/PARSE" } else { "IDLE" }
            $queryId = if ($activeByWorker.ContainsKey($worker)) { $activeByWorker[$worker] } else { "" }
            [void]$workerGrid.Rows.Add($worker, $state, $queryId)
        }

        $signature = (
            "$($progress.status):${completed}:$($progress.accepted_pages):" +
            "$($progress.active_workers):$($progress.failure_count)"
        )
        if ($signature -ne $lastProgressSignature) {
            Add-Feed (
                "[$(Get-Date -Format 'HH:mm:ss.fff')] PROGRESS $($statusLabel.Text)"
            ) ([System.Drawing.Color]::MediumTurquoise)
            $script:lastProgressSignature = $signature
        }
    }

    if (Test-Path -LiteralPath $PagePath) {
        $newPages = @(
            Get-ChildItem -LiteralPath $PagePath -Recurse -Filter "page_*.json" -File -ErrorAction SilentlyContinue |
                Where-Object { -not $seenPages.ContainsKey($_.FullName) } |
                Sort-Object LastWriteTimeUtc, FullName |
                Select-Object -First $PageArtifactsPerTick
        )
        foreach ($file in $newPages) {
            $page = Read-JsonSafe $file.FullName
            if ($null -eq $page) { continue }
            Add-PageArtifact -Page $page -File $file.FullName
            $seenPages[$file.FullName] = $true
        }
    }

    if (Test-Path -LiteralPath $QueryPath) {
        $newQueries = @(
            Get-ChildItem -LiteralPath $QueryPath -Filter "*.json" -File -ErrorAction SilentlyContinue |
                Where-Object { -not $seenQueries.ContainsKey($_.FullName) } |
                Sort-Object LastWriteTimeUtc, FullName |
                Select-Object -First $QueryArtifactsPerTick
        )
        foreach ($file in $newQueries) {
            $query = Read-JsonSafe $file.FullName
            if ($null -eq $query) { continue }
            Add-QueryArtifact -Query $query -File $file.FullName
            $seenQueries[$file.FullName] = $true
        }
    }

    if (Test-Path -LiteralPath $FailurePath) {
        $newFailures = @(
            Get-ChildItem -LiteralPath $FailurePath -Filter "*.json" -File -ErrorAction SilentlyContinue |
                Where-Object { -not $seenFailures.ContainsKey($_.FullName) } |
                Sort-Object LastWriteTimeUtc, FullName |
                Select-Object -First $FailureArtifactsPerTick
        )
        foreach ($file in $newFailures) {
            $failure = Read-JsonSafe $file.FullName
            if ($null -eq $failure) { continue }
            Add-FailureArtifact -Failure $failure -File $file.FullName
            $seenFailures[$file.FullName] = $true
        }
    }
}

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = [Math]::Max(250, [Math]::Min(5000, $RefreshMilliseconds))
$timer.Add_Tick({
    try {
        Refresh-Matrix
    }
    catch {
        Add-Feed (
            "[$(Get-Date -Format 'HH:mm:ss.fff')] MATRIX ERROR $($_.Exception.Message)"
        ) ([System.Drawing.Color]::OrangeRed)
    }
})

$form.Add_Shown({
    Refresh-Matrix
    $timer.Start()
})
$form.Add_FormClosed({
    $timer.Stop()
    $timer.Dispose()
})

[void]$form.ShowDialog()
