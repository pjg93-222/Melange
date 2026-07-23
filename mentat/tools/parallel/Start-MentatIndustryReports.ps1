<#
.SYNOPSIS
Launch one visible collection-and-report console per Mentat industry.

.DESCRIPTION
The launcher creates a run directory containing immutable worker specifications,
live state files, per-industry result receipts, transcripts, process logs, and
wall-clock summaries. All industry consoles are created immediately. A named
semaphore limits active report builds while a separate named mutex is supplied
to the report generator for Excel COM serialization.

The launcher never stops a run merely because it exceeds 45 minutes. It records
the performance-gate result after every worker has completed.

.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-MentatIndustryReports.ps1 `
  -GeneratorPath ..\generate_industry_report.ps1 `
  -NoCache
#>
[CmdletBinding()]
param(
  [string[]]$Industries = @(
    'Crypto',
    'Credit Union',
    'Community Banks',
    'Property & Casualty Insurance',
    'Credit Arms',
    'Telecom'
  ),
  [ValidateRange(1, 32)]
  [int]$MaxParallel = 3,
  [string]$GeneratorPath = '',
  [string]$MentatPath = '',
  [string]$RScriptPath = 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe',
  [string]$RLibraryPath = 'C:\Users\pgoff\AppData\Local\R\win-library\4.6',
  [string]$DatabasePath = '',
  [string]$OutputDirectory = '',
  [string]$RunRoot = '',
  [switch]$SkipCollection,
  [switch]$NoCache,
  [switch]$SkipMonitorConsole,
  [switch]$ForceStartProcess,
  [ValidateRange(0, 1440)]
  [int]$MaxWaitMinutes = 0
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

$parallelRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$toolsRoot = Split-Path -Parent $parallelRoot
$projectRoot = Split-Path -Parent $toolsRoot
$workspaceRoot = Split-Path -Parent $projectRoot
$workerPath = Join-Path $parallelRoot 'Invoke-MentatIndustryWorker.ps1'
$monitorPath = Join-Path $parallelRoot 'Watch-MentatIndustryProcesses.ps1'
$powerShellPath = (Get-Command powershell.exe -ErrorAction Stop).Source

function Resolve-FullPath {
  param([string]$Path, [string]$BasePath)
  if ([string]::IsNullOrWhiteSpace($Path)) { return '' }
  if ([IO.Path]::IsPathRooted($Path)) { return [IO.Path]::GetFullPath($Path) }
  return [IO.Path]::GetFullPath((Join-Path $BasePath $Path))
}

function ConvertTo-Slug {
  param([string]$Value)
  $slug = [Text.RegularExpressions.Regex]::Replace(
    $Value.ToLowerInvariant(),
    '[^a-z0-9]+',
    '-'
  ).Trim('-')
  if ([string]::IsNullOrWhiteSpace($slug)) {
    throw "Industry name cannot be converted to a safe slug: $Value"
  }
  return $slug
}

function ConvertTo-EncodedInvocation {
  param(
    [Parameter(Mandatory = $true)][string]$ScriptPath,
    [Parameter(Mandatory = $true)][string]$ParameterName,
    [Parameter(Mandatory = $true)][string]$ParameterValue
  )
  $safeScript = $ScriptPath.Replace("'", "''")
  $safeValue = $ParameterValue.Replace("'", "''")
  $command = "& '$safeScript' -$ParameterName '$safeValue'"
  return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
}

function Write-AtomicJson {
  param(
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)]$Value
  )
  $directory = Split-Path -Parent $Path
  [IO.Directory]::CreateDirectory($directory) | Out-Null
  $temporary = Join-Path $directory (
    '.{0}.{1}.{2}.tmp' -f
      [IO.Path]::GetFileName($Path),
      $PID,
      [Guid]::NewGuid().ToString('N')
  )
  $encoding = New-Object Text.UTF8Encoding($false)
  [IO.File]::WriteAllText(
    $temporary,
    ($Value | ConvertTo-Json -Depth 12),
    $encoding
  )
  if (Test-Path -LiteralPath $Path) {
    [IO.File]::Replace($temporary, $Path, $null, $true)
  } else {
    [IO.File]::Move($temporary, $Path)
  }
}

function Start-VisiblePowerShell {
  param(
    [Parameter(Mandatory = $true)][string]$EncodedCommand,
    [Parameter(Mandatory = $true)][string]$WindowTitle
  )
  $terminal = Get-Command wt.exe -ErrorAction SilentlyContinue
  if (-not $ForceStartProcess -and $null -ne $terminal) {
    $arguments = @(
      '-w', 'new',
      'new-tab',
      '--title', $WindowTitle,
      'powershell.exe',
      '-NoLogo',
      '-NoProfile',
      '-NoExit',
      '-ExecutionPolicy', 'Bypass',
      '-EncodedCommand', $EncodedCommand
    )
    return Start-Process -FilePath $terminal.Source -ArgumentList $arguments `
      -WindowStyle Normal -PassThru
  }

  $arguments = @(
    '-NoLogo',
    '-NoProfile',
    '-NoExit',
    '-ExecutionPolicy', 'Bypass',
    '-EncodedCommand', $EncodedCommand
  )
  return Start-Process -FilePath $powerShellPath -ArgumentList $arguments `
    -WindowStyle Normal -PassThru
}

if (-not $GeneratorPath) {
  $GeneratorPath = Join-Path $toolsRoot 'generate_industry_report.ps1'
}
if (-not $MentatPath) {
  $MentatPath = Join-Path $projectRoot 'mentat.R'
}
if (-not $OutputDirectory) {
  $OutputDirectory = Join-Path $workspaceRoot 'reports'
}
if (-not $RunRoot) {
  $RunRoot = Join-Path $projectRoot '.cache\industry-report-runs'
}

$GeneratorPath = Resolve-FullPath $GeneratorPath $parallelRoot
$MentatPath = Resolve-FullPath $MentatPath $projectRoot
$RScriptPath = Resolve-FullPath $RScriptPath $workspaceRoot
$RLibraryPath = Resolve-FullPath $RLibraryPath $workspaceRoot
$OutputDirectory = Resolve-FullPath $OutputDirectory $workspaceRoot
$RunRoot = Resolve-FullPath $RunRoot $projectRoot
if ($DatabasePath) {
  $DatabasePath = Resolve-FullPath $DatabasePath $workspaceRoot
}

foreach ($requiredPath in @(
  $workerPath, $monitorPath, $GeneratorPath, $MentatPath, $RScriptPath
)) {
  if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
    throw "Required parallel-report script is missing: $requiredPath"
  }
}
if ($DatabasePath -and -not (Test-Path -LiteralPath $DatabasePath -PathType Leaf)) {
  throw "Database file is missing: $DatabasePath"
}
if (-not $SkipCollection -and $DatabasePath) {
  throw '-DatabasePath is report-only. Omit it for from-scratch collection or add -SkipCollection.'
}
if (-not $SkipCollection -and -not (Test-Path -LiteralPath $RLibraryPath -PathType Container)) {
  throw "R package library is missing: $RLibraryPath"
}
$generatorCommand = Get-Command -Name $GeneratorPath -ErrorAction Stop
foreach ($requiredParameter in @('Industry', 'OutputDirectory')) {
  if (-not $generatorCommand.Parameters.ContainsKey($requiredParameter)) {
    throw (
      "Report generator must declare -$requiredParameter before parallel " +
      "workers can be launched: $GeneratorPath"
    )
  }
}
if (-not $generatorCommand.Parameters.ContainsKey('ExcelMutexName')) {
  Write-Warning (
    'Generator does not declare -ExcelMutexName. Workers will safely ' +
    'serialize whole generator invocations instead of only Excel COM.'
  )
}

$cleanIndustries = @(
  $Industries |
    ForEach-Object { if ($null -ne $_) { $_.Trim() } } |
    Where-Object { -not [string]::IsNullOrWhiteSpace($_) } |
    Select-Object -Unique
)
if (-not $cleanIndustries.Count) { throw 'At least one industry is required.' }
$slugs = @($cleanIndustries | ForEach-Object { ConvertTo-Slug $_ })
if (@($slugs | Select-Object -Unique).Count -ne $slugs.Count) {
  throw 'Industry names collide after safe-slug conversion.'
}

[IO.Directory]::CreateDirectory($OutputDirectory) | Out-Null
[IO.Directory]::CreateDirectory($RunRoot) | Out-Null
$runId = '{0}-{1}' -f (Get-Date -Format 'yyyyMMddTHHmmss'), $PID
$runDirectory = Join-Path $RunRoot $runId
$specDirectory = Join-Path $runDirectory 'specs'
$stateDirectory = Join-Path $runDirectory 'state'
$resultDirectory = Join-Path $runDirectory 'results'
$logDirectory = Join-Path $runDirectory 'logs'
$dataDirectory = Join-Path $runDirectory 'data'
foreach ($directory in @(
  $runDirectory, $specDirectory, $stateDirectory, $resultDirectory,
  $logDirectory, $dataDirectory
)) {
  [IO.Directory]::CreateDirectory($directory) | Out-Null
}

$slotName = 'Local\MentatIndustrySlots_{0}' -f (
  [Text.RegularExpressions.Regex]::Replace($runId, '[^A-Za-z0-9_]', '_')
)
$excelMutexName = 'Local\MentatExcelComFinalizer'
$slotSemaphore = New-Object Threading.Semaphore(
  $MaxParallel,
  $MaxParallel,
  $slotName
)
$excelMutex = New-Object Threading.Mutex($false, $excelMutexName)

$gitCommit = ''
try {
  $gitCommit = (& git -C $workspaceRoot rev-parse HEAD 2>$null | Select-Object -First 1)
} catch {
  $gitCommit = ''
}
$generatorHash = (Get-FileHash -LiteralPath $GeneratorPath -Algorithm SHA256).Hash
$startedAt = [DateTimeOffset]::Now
$wallWatch = [Diagnostics.Stopwatch]::StartNew()

$specs = New-Object Collections.Generic.List[object]
for ($index = 0; $index -lt $cleanIndustries.Count; $index++) {
  $industry = $cleanIndustries[$index]
  $slug = $slugs[$index]
  $specPath = Join-Path $specDirectory "$slug.json"
  $industryDataRoot = Join-Path $dataDirectory $slug
  $industryDatabase = if ($SkipCollection) {
    $DatabasePath
  } else {
    Join-Path $industryDataRoot 'mentat.db'
  }
  $spec = [ordered]@{
    run_id = $runId
    industry = $industry
    slug = $slug
    generator_path = $GeneratorPath
    mentat_path = $MentatPath
    rscript_path = $RScriptPath
    r_library_path = $RLibraryPath
    collect_from_scratch = (-not [bool]$SkipCollection)
    data_root = $industryDataRoot
    database_path = $industryDatabase
    output_directory = $OutputDirectory
    expected_workbook_path = Join-Path $OutputDirectory (
      "$industry Industry Spending Overview.xlsx"
    )
    run_directory = $runDirectory
    state_path = Join-Path $stateDirectory "$slug.state.json"
    result_path = Join-Path $resultDirectory "$slug.result.json"
    process_log_path = Join-Path $logDirectory "$slug.process.log"
    transcript_path = Join-Path $logDirectory "$slug.transcript.txt"
    slot_semaphore_name = $slotName
    excel_mutex_name = $excelMutexName
    no_cache = [bool]$NoCache
    requested_at = $startedAt.ToString('o')
  }
  Write-AtomicJson $specPath $spec
  $specs.Add([pscustomobject]@{
    industry = $industry
    slug = $slug
    spec_path = $specPath
    state_path = $spec.state_path
    result_path = $spec.result_path
  })
}

$manifestPath = Join-Path $runDirectory 'manifest.json'
$summaryJsonPath = Join-Path $runDirectory 'summary.json'
$summaryCsvPath = Join-Path $runDirectory 'summary.csv'
Write-AtomicJson $manifestPath ([ordered]@{
  run_id = $runId
  started_at = $startedAt.ToString('o')
  launcher_pid = $PID
  git_commit = [string]$gitCommit
  generator_path = $GeneratorPath
  generator_sha256 = $generatorHash
  mentat_path = $MentatPath
  rscript_path = $RScriptPath
  collect_from_scratch = (-not [bool]$SkipCollection)
  database_path = $DatabasePath
  output_directory = $OutputDirectory
  max_parallel = $MaxParallel
  no_cache = [bool]$NoCache
  slot_semaphore_name = $slotName
  excel_mutex_name = $excelMutexName
  industries = $cleanIndustries
  summary_json_path = $summaryJsonPath
  summary_csv_path = $summaryCsvPath
})

Write-Host ''
Write-Host 'MENTAT PARALLEL INDUSTRY REPORT RUN' -ForegroundColor Cyan
Write-Host "Run ID:       $runId"
Write-Host "Industries:   $($cleanIndustries -join ', ')"
Write-Host "Max parallel: $MaxParallel"
Write-Host "Run folder:   $runDirectory"
Write-Host ''

$launches = New-Object Collections.Generic.List[object]
try {
  foreach ($spec in $specs) {
    $encoded = ConvertTo-EncodedInvocation `
      -ScriptPath $workerPath `
      -ParameterName 'SpecPath' `
      -ParameterValue $spec.spec_path
    $process = Start-VisiblePowerShell `
      -EncodedCommand $encoded `
      -WindowTitle "Mentat-$($spec.slug)"
    $launches.Add([pscustomobject]@{
      industry = $spec.industry
      shell_pid = $process.Id
      started_at = [DateTimeOffset]::Now.ToString('o')
    })
    Write-Host ("Launched {0} (shell PID {1})" -f $spec.industry, $process.Id)
  }

  if (-not $SkipMonitorConsole) {
    $encodedMonitor = ConvertTo-EncodedInvocation `
      -ScriptPath $monitorPath `
      -ParameterName 'RunDirectory' `
      -ParameterValue $runDirectory
    $monitorProcess = Start-VisiblePowerShell `
      -EncodedCommand $encodedMonitor `
      -WindowTitle "Mentat-Monitor-$runId"
    Write-Host "Launched process monitor (shell PID $($monitorProcess.Id))."
  }

  $lastProgress = [DateTimeOffset]::MinValue
  $timedOut = $false
  while ($true) {
    $completed = @(
      $specs | Where-Object { Test-Path -LiteralPath $_.result_path -PathType Leaf }
    ).Count
    if ($completed -eq $specs.Count) { break }
    if (
      $MaxWaitMinutes -gt 0 -and
      $wallWatch.Elapsed.TotalMinutes -ge $MaxWaitMinutes
    ) {
      $timedOut = $true
      break
    }
    if (([DateTimeOffset]::Now - $lastProgress).TotalSeconds -ge 15) {
      Write-Host (
        '[{0}] {1}/{2} industries complete; elapsed {3:n1} min' -f
          (Get-Date -Format 'HH:mm:ss'),
          $completed,
          $specs.Count,
          $wallWatch.Elapsed.TotalMinutes
      )
      $lastProgress = [DateTimeOffset]::Now
    }
    Start-Sleep -Seconds 2
  }

  $wallWatch.Stop()
  $finishedAt = [DateTimeOffset]::Now
  $results = New-Object Collections.Generic.List[object]
  foreach ($spec in $specs) {
    if (Test-Path -LiteralPath $spec.result_path -PathType Leaf) {
      try {
        $results.Add(
          (Get-Content -LiteralPath $spec.result_path -Raw | ConvertFrom-Json)
        )
        continue
      } catch {
        $readError = $_.Exception.Message
      }
    } else {
      $readError = 'Worker result was not available before launcher timeout.'
    }
    $results.Add([pscustomobject]@{
      run_id = $runId
      industry = $spec.industry
      slug = $spec.slug
      status = 'launcher_incomplete'
      exit_code = 125
      error = $readError
      total_elapsed_seconds = $null
      collection_elapsed_seconds = $null
      generator_elapsed_seconds = $null
      slot_wait_seconds = $null
      over_45_minutes = $null
      output_workbook = ''
      process_log = ''
      transcript = ''
    })
  }

  $failed = @($results | Where-Object { $_.status -ne 'succeeded' })
  $summary = [ordered]@{
    run_id = $runId
    started_at = $startedAt.ToString('o')
    finished_at = $finishedAt.ToString('o')
    wall_clock_seconds = [math]::Round($wallWatch.Elapsed.TotalSeconds, 3)
    wall_clock_minutes = [math]::Round($wallWatch.Elapsed.TotalMinutes, 3)
    under_45_minutes = ($wallWatch.Elapsed.TotalMinutes -lt 45)
    timed_out = $timedOut
    max_parallel = $MaxParallel
    industry_count = $specs.Count
    succeeded = $results.Count - $failed.Count
    failed = $failed.Count
    launches = $launches
    results = $results
  }
  Write-AtomicJson $summaryJsonPath $summary
  $results |
    Select-Object run_id, industry, status, exit_code, started_at, finished_at,
      slot_wait_seconds, generator_elapsed_seconds, total_elapsed_seconds,
      collection_elapsed_seconds,
      over_45_minutes, output_workbook, workbook_sha256, process_log,
      transcript, error |
    Export-Csv -LiteralPath "$summaryCsvPath.pending-$PID" `
      -NoTypeInformation -Encoding UTF8
  $pendingSummaryCsv = "$summaryCsvPath.pending-$PID"
  if (Test-Path -LiteralPath $summaryCsvPath) {
    [IO.File]::Replace($pendingSummaryCsv, $summaryCsvPath, $null, $true)
  } else {
    [IO.File]::Move($pendingSummaryCsv, $summaryCsvPath)
  }

  Write-Host ''
  Write-Host 'RUN COMPLETE' -ForegroundColor Cyan
  Write-Host ("Succeeded: {0}/{1}" -f ($results.Count - $failed.Count), $results.Count)
  Write-Host ("Wall clock: {0:n2} minutes" -f $wallWatch.Elapsed.TotalMinutes)
  if ($wallWatch.Elapsed.TotalMinutes -ge 45) {
    Write-Warning (
      'The run exceeded the 45-minute performance target. ' +
      'All completed outputs and timings were preserved for optimization.'
    )
  }
  if ($failed.Count) {
    Write-Warning "$($failed.Count) industry worker(s) reported failure."
  }
  Write-Host "Summary JSON: $summaryJsonPath"
  Write-Host "Summary CSV:  $summaryCsvPath"
} finally {
  if ($null -ne $slotSemaphore) { $slotSemaphore.Dispose() }
  if ($null -ne $excelMutex) { $excelMutex.Dispose() }
}
