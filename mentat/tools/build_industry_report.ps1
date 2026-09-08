<#
.SYNOPSIS
Build an audited Mentat industry spending workbook in one command.

.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\generate_industry_report.ps1 `
  -Industry Fintech -DatabasePath C:\path\to\mentat.db `
  -OutputDirectory C:\path\to\reports
#>
[CmdletBinding()]
param(
  [string]$Industry = 'Crypto',
  [string]$DatabasePath = '',
  [string]$OutputDirectory = '',
  [string]$CommitteeMasterDirectory = '',
  [string]$BeneficiaryDirectory = '',
  [string]$RScriptPath = 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe',
  [string]$NodePath = '',
  [string]$NodeModulesPath = '',
  [string]$PythonPath = '',
  [ValidateRange(0,32768)]
  [int]$NodeHeapMb = 0,
  [ValidateRange(1,45)]
  [double]$PerformanceBudgetMinutes = 15,
  [string]$WorkbookLockPath = '',
  [string]$ExcelMutexName = 'Global\MentatIndustryExcelFinalize',
  [ValidateSet('','2021-2022','2023-2024','2025-2026')]
  [string]$CycleLabel = '',
  [switch]$NoCache,
  [switch]$RenderPreviews
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot
$heapPlanner = Join-Path $scriptRoot 'node_heap_plan.psm1'
if (-not (Test-Path -LiteralPath $heapPlanner -PathType Leaf)) {
  throw "Node heap planner is missing: $heapPlanner"
}
Import-Module $heapPlanner -Force
$templateContract = 'mentat-industry-overview-v1'
$Industry = $Industry.Trim()
if (-not $PythonPath) { $PythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' }
if (-not $Industry) { throw 'Industry cannot be empty.' }

$reportBaseName = if ($CycleLabel) {
  "${Industry} Industry Spending Overview ${CycleLabel}"
} else {
  "${Industry} Industry Spending Overview"
}
$industryToken = ($Industry -replace '[^A-Za-z0-9]+','_').Trim('_').ToLowerInvariant()
if (-not $industryToken) { throw "Industry cannot be converted to a safe cache token: $Industry" }
if (-not $WorkbookLockPath) {
  $WorkbookLockPath = Join-Path $projectRoot '.cache\industry-report\workbook-builder.lock'
}

if (-not $DatabasePath) {
  $dataRoot = if ($env:MENTAT_DATA_ROOT) { $env:MENTAT_DATA_ROOT } else { Join-Path $env:LOCALAPPDATA 'Mentat' }
  $DatabasePath = Join-Path $dataRoot 'mentat.db'
}
if (-not $OutputDirectory) {
  $workspaceRoot = Split-Path -Parent $projectRoot
  $OutputDirectory = Join-Path $workspaceRoot 'reports'
}
$sourceRoot = Join-Path $projectRoot 'inputs'
if ($env:MENTAT_FEC_SOURCE_ROOT) { $sourceRoot = $env:MENTAT_FEC_SOURCE_ROOT }
elseif (Test-Path -LiteralPath (Join-Path $sourceRoot 'active_fec_sources.json')) {
  $sourceRoot = (Get-Content -Raw -LiteralPath (Join-Path $sourceRoot 'active_fec_sources.json') | ConvertFrom-Json).path
}
if (-not $CommitteeMasterDirectory) { $CommitteeMasterDirectory = Join-Path $sourceRoot 'fec_committee_master' }
if (-not $BeneficiaryDirectory) { $BeneficiaryDirectory = Join-Path $sourceRoot 'fec_beneficiary' }
# Pin the inputs directory for the R side. mentat_input_dir() otherwise walks up
# from the working directory, which resolves wrongly (and fatally) whenever this
# script is invoked from outside the project - a git worktree, a scheduled task,
# another drive. The report path needs inputs\ only for the trade-association
# committee-ID overrides, so an unpinned cwd silently emptied that category.
$env:MENTAT_INPUT_DIR = Join-Path $projectRoot 'inputs'
if (-not $NodePath -and $env:MENTAT_NODE_PATH) {
  $NodePath = $env:MENTAT_NODE_PATH
}
if (-not $NodePath) {
  $nodeCommand = Get-Command node -CommandType Application `
    -ErrorAction SilentlyContinue |
    Select-Object -First 1
  if ($null -ne $nodeCommand) {
    $NodePath = $nodeCommand.Source
  }
}
if (-not $NodePath) {
  $cachedNode = Join-Path $env:USERPROFILE (
    '.cache\codex-runtimes\codex-primary-runtime\dependencies\' +
    'node\bin\node.exe'
  )
  if (Test-Path -LiteralPath $cachedNode -PathType Leaf) {
    $NodePath = $cachedNode
  }
}
if (-not $NodePath) {
  throw (
    'Node.js runtime was not found. Pass -NodePath, set MENTAT_NODE_PATH, ' +
    'or install Node.js with node on PATH.'
  )
}
$NodePath = [IO.Path]::GetFullPath($NodePath)
if (-not (Test-Path -LiteralPath $NodePath -PathType Leaf)) {
  throw (
    "Node.js runtime is missing at '$NodePath'. Pass -NodePath, set " +
    'MENTAT_NODE_PATH, or install Node.js with node on PATH.'
  )
}
if (-not $NodeModulesPath -and $env:MENTAT_NODE_MODULES) {
  $NodeModulesPath = $env:MENTAT_NODE_MODULES
}
if (-not $NodeModulesPath) {
  $moduleCandidates = New-Object Collections.Generic.List[string]
  $moduleCandidates.Add((Join-Path $projectRoot 'node_modules'))
  if ($env:NODE_PATH) {
    foreach ($candidate in (
      $env:NODE_PATH -split [regex]::Escape([string][IO.Path]::PathSeparator)
    )) {
      if (-not [string]::IsNullOrWhiteSpace($candidate)) {
        $moduleCandidates.Add($candidate)
      }
    }
  }
  foreach ($candidate in $moduleCandidates) {
    if (Test-Path -LiteralPath (
      Join-Path $candidate '@oai\artifact-tool'
    ) -PathType Container) {
      $NodeModulesPath = $candidate
      break
    }
  }
}
if (-not $NodeModulesPath) {
  $cachedNodeModules = Join-Path $env:USERPROFILE (
    '.cache\codex-runtimes\codex-primary-runtime\dependencies\' +
    'node\node_modules'
  )
  if (Test-Path -LiteralPath (
    Join-Path $cachedNodeModules '@oai\artifact-tool'
  ) -PathType Container) {
    $NodeModulesPath = $cachedNodeModules
  }
}
if (-not $NodeModulesPath) {
  throw (
    'The @oai/artifact-tool Node module was not found. Pass ' +
    '-NodeModulesPath, set MENTAT_NODE_MODULES, or install ' +
    '@oai/artifact-tool in the project node_modules directory.'
  )
}
$NodeModulesPath = [IO.Path]::GetFullPath($NodeModulesPath)
if (-not (Test-Path -LiteralPath (
  Join-Path $NodeModulesPath '@oai\artifact-tool'
) -PathType Container)) {
  throw (
    "@oai/artifact-tool is missing under '$NodeModulesPath'. Pass " +
    '-NodeModulesPath, set MENTAT_NODE_MODULES, or install ' +
    '@oai/artifact-tool in that node_modules directory.'
  )
}

$DatabasePath = [IO.Path]::GetFullPath($DatabasePath)
$OutputDirectory = [IO.Path]::GetFullPath($OutputDirectory)
$CommitteeMasterDirectory = [IO.Path]::GetFullPath($CommitteeMasterDirectory)
$BeneficiaryDirectory = [IO.Path]::GetFullPath($BeneficiaryDirectory)
$WorkbookLockPath = [IO.Path]::GetFullPath($WorkbookLockPath)
$exporter = Join-Path $scriptRoot 'export_crypto_spending_data.R'
$builder = Join-Path $scriptRoot 'crypto_workbook_builder.mjs'
$cycleFilterScript = Join-Path $scriptRoot 'filter_industry_cycle_data.mjs'
$finalizer = Join-Path $scriptRoot 'finalize_crypto_excel.ps1'
$beneficiaryModule = Join-Path $projectRoot 'R\fec_beneficiary.R'
$committeeFiles = @(
  (Join-Path $CommitteeMasterDirectory 'cm22\cm.txt'),
  (Join-Path $CommitteeMasterDirectory 'cm24\cm.txt'),
  (Join-Path $CommitteeMasterDirectory 'cm26\cm.txt')
)
$beneficiaryFiles = @(
  (Join-Path $BeneficiaryDirectory 'cn22\cn.txt'),(Join-Path $BeneficiaryDirectory 'cn24\cn.txt'),(Join-Path $BeneficiaryDirectory 'cn26\cn.txt'),
  (Join-Path $BeneficiaryDirectory 'ccl22\ccl.txt'),(Join-Path $BeneficiaryDirectory 'ccl24\ccl.txt'),(Join-Path $BeneficiaryDirectory 'ccl26\ccl.txt'),
  (Join-Path $BeneficiaryDirectory 'leadership2022.csv'),(Join-Path $BeneficiaryDirectory 'leadership2024.csv'),(Join-Path $BeneficiaryDirectory 'leadership2026.csv'),
  (Join-Path $BeneficiaryDirectory 'pas222\itpas2.txt'),(Join-Path $BeneficiaryDirectory 'pas224\itpas2.txt'),(Join-Path $BeneficiaryDirectory 'pas226\itpas2.txt')
)
foreach ($requiredPath in @($DatabasePath,$RScriptPath,$NodePath,$NodeModulesPath,$exporter,$builder,$cycleFilterScript,$finalizer,$beneficiaryModule,$heapPlanner) + $committeeFiles + $beneficiaryFiles) {
  if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required report input or runtime is missing: $requiredPath" }
}

function Test-JsonFile([string]$Path) {
  $validationScript = "const fs=require('node:fs');JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
  $priorErrorAction = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    if ((Get-Item -LiteralPath $Path).Length -ge 480MB) {
      & $PythonPath '-c' 'import json,sys; json.load(open(sys.argv[1],encoding="utf-8-sig"))' $Path 2>$null | Out-Null
    } else {
      & $NodePath '--max-old-space-size=8192' '-e' $validationScript $Path 2>$null | Out-Null
    }
    $valid = $LASTEXITCODE -eq 0
  } finally {
    $ErrorActionPreference = $priorErrorAction
  }
  $valid
}

function Get-CombinedFingerprint([string[]]$Paths, [string]$Salt = '') {
  $lines = @("salt|$Salt") + @(foreach ($path in $Paths) {
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    "$($item.Name)|$($item.Length)|$hash"
  })
  $sha = [Security.Cryptography.SHA256]::Create()
  try {
    $bytes = [Text.Encoding]::UTF8.GetBytes(($lines -join "`n"))
    ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()
  } finally { $sha.Dispose() }
}

function Write-AtomicText([string]$Path, [string]$Text) {
  $temporary = "$Path.pending-$PID"
  [IO.File]::WriteAllText($temporary, $Text, [Text.UTF8Encoding]::new($false))
  Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Assert-WorkbookPackage([string]$Path, [int]$ExpectedWorksheetCount) {
  Add-Type -AssemblyName System.IO.Compression.FileSystem
  $archive = [IO.Compression.ZipFile]::OpenRead($Path)
  try {
    $names = @($archive.Entries | ForEach-Object { $_.FullName })
    if ('[Content_Types].xml' -notin $names -or 'xl/workbook.xml' -notin $names) {
      throw 'Workbook ZIP package is missing required Open XML parts.'
    }
    $worksheetCount = @($names | Where-Object { $_ -match '^xl/worksheets/sheet\d+\.xml$' }).Count
    if ($worksheetCount -ne $ExpectedWorksheetCount) { throw "Workbook contains $worksheetCount worksheets; expected $ExpectedWorksheetCount." }

    $tableIds = [Collections.Generic.HashSet[int]]::new()
    $tableNames = [Collections.Generic.HashSet[string]]::new(
      [StringComparer]::OrdinalIgnoreCase
    )
    foreach ($entry in @($archive.Entries | Where-Object {
      $_.FullName -match '^xl/tables/table\d+\.xml$'
    })) {
      $reader = [IO.StreamReader]::new($entry.Open())
      try { [xml]$tableXml = $reader.ReadToEnd() } finally { $reader.Dispose() }
      $table = $tableXml.DocumentElement
      $tableId = [int]$table.GetAttribute('id')
      $tableName = $table.GetAttribute('displayName')
      $tableRef = $table.GetAttribute('ref')
      if (-not $tableIds.Add($tableId)) {
        throw "Workbook has duplicate Excel table id $tableId."
      }
      if (-not $tableName -or -not $tableNames.Add($tableName)) {
        throw "Workbook has a blank or duplicate Excel table name '$tableName'."
      }
      if ($tableRef -notmatch '^[A-Z]+(\d+):[A-Z]+(\d+)$') {
        throw "Excel table '$tableName' has invalid range '$tableRef'."
      }
      if ([int]$Matches[2] -le [int]$Matches[1]) {
        throw "Excel table '$tableName' has no data row."
      }
      $namespace = [Xml.XmlNamespaceManager]::new($tableXml.NameTable)
      $namespace.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
      $columns = @($tableXml.SelectNodes('/m:table/m:tableColumns/m:tableColumn', $namespace))
      $declaredCount = [int]$tableXml.SelectSingleNode(
        '/m:table/m:tableColumns',
        $namespace
      ).GetAttribute('count')
      if ($columns.Count -ne $declaredCount) {
        throw "Excel table '$tableName' has a table-column count mismatch."
      }
      $columnNames = [Collections.Generic.HashSet[string]]::new(
        [StringComparer]::OrdinalIgnoreCase
      )
      for ($index = 0; $index -lt $columns.Count; $index++) {
        $columnId = [int]$columns[$index].GetAttribute('id')
        $columnName = $columns[$index].GetAttribute('name')
        if ($columnId -ne $index + 1) {
          throw "Excel table '$tableName' has non-sequential column ids."
        }
        if (-not $columnName -or -not $columnNames.Add($columnName)) {
          throw "Excel table '$tableName' has a blank or duplicate column name '$columnName'."
        }
      }
    }

    foreach ($entry in @($archive.Entries | Where-Object {
      $_.FullName -match '^xl/worksheets/sheet\d+\.xml$'
    })) {
      $reader = [IO.StreamReader]::new($entry.Open())
      try { [xml]$sheetXml = $reader.ReadToEnd() } finally { $reader.Dispose() }
      $namespace = [Xml.XmlNamespaceManager]::new($sheetXml.NameTable)
      $namespace.AddNamespace('m', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')
      $hasSheetFilter = $null -ne $sheetXml.SelectSingleNode(
        '/m:worksheet/m:autoFilter',
        $namespace
      )
      $hasTables = $null -ne $sheetXml.SelectSingleNode(
        '/m:worksheet/m:tableParts',
        $namespace
      )
      if ($hasSheetFilter -and $hasTables) {
        throw "Worksheet part '$($entry.FullName)' has an overlapping worksheet AutoFilter and Excel table."
      }
    }
  } finally { $archive.Dispose() }
}

function Get-QuiescentDatabaseSha256([string]$Path) {
  $walPath = "$Path-wal"
  foreach ($phase in @('before', 'after')) {
    if (
      (Test-Path -LiteralPath $walPath -PathType Leaf) -and
      (Get-Item -LiteralPath $walPath).Length -gt 0
    ) {
      throw (
        "Source database has a nonempty WAL sidecar $phase fingerprinting " +
        "and is not a quiescent snapshot: $walPath. Stop writers and " +
        "checkpoint SQLite, or build from a private snapshot."
      )
    }
    if ($phase -eq 'before') {
      $hash = (
        Get-FileHash -LiteralPath $Path -Algorithm SHA256
      ).Hash.ToLowerInvariant()
    }
  }
  $hash
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$cacheRoot = Join-Path $projectRoot ('.cache\industry-report\' + $industryToken)
$databaseHash = Get-QuiescentDatabaseSha256 $DatabasePath
$databaseToken = $databaseHash.Substring(0, 16)
# A per-cycle build exports only that cycle, so it needs its own payload and
# manifest - sharing one industry_data.json across three -CycleLabel runs would
# make each run a cache hit on the previous cycle's data.
$cycleToken = if ($CycleLabel) { '-' + ($CycleLabel -replace '[^0-9]', '') } else { '' }
$cacheVariantToken = if ($CycleLabel) {
  $CycleLabel -replace '[^0-9]+','_'
} else {
  'all_cycles'
}
$stageDirectory = Join-Path $cacheRoot ("stage-" + $cacheVariantToken)
New-Item -ItemType Directory -Path $cacheRoot,$stageDirectory -Force | Out-Null
$dataPath = Join-Path $cacheRoot (
  "industry_data$cycleToken-$databaseToken.json"
)
$manifestPath = Join-Path $cacheRoot (
  "manifest$cycleToken-$databaseToken.json"
)
# Set BEFORE the export, not just around the workbook step: the exporter reads it
# to narrow the payload, which is what keeps a large industry under V8's
# 536,870,888-byte JSON string limit. Telecom's full payload is 591,338,574 and
# cannot be parsed by the validator or the builder at all.
$env:MENTAT_CYCLE_FILTER = $CycleLabel
# Every file whose contents can change export output must be fingerprinted, or a
# code fix silently republishes the pre-fix artifact as a cache hit. This list
# previously held only the exporter and fec_beneficiary.R, so edits to report.R
# (recipient classification), identity_components.R (person grouping) or the
# trade-association override CSV did not invalidate the cache.
$dataInputPaths = @(
  $DatabasePath,
  $exporter,
  $beneficiaryModule,
  $MyInvocation.MyCommand.Path,
  (Join-Path $projectRoot 'R\report.R'),
  (Join-Path $projectRoot 'R\identity_components.R'),
  (Join-Path $projectRoot 'R\ingest.R'),
  (Join-Path $projectRoot 'R\collect.R'),
  (Join-Path $projectRoot 'R\paths.R'),
  (Join-Path $projectRoot 'R\schema.R'),
  (Join-Path $projectRoot 'R\reconcile.R'),
  # export_guards.R gates publication rather than mutating the payload, so on a
  # cache hit the export never runs and a newly added or tightened guard is
  # silently skipped. Fingerprinting it forces the re-run that lets it fire.
  (Join-Path $projectRoot 'R\export_guards.R'),
  (Join-Path $projectRoot 'R\fec_transfer_graph.R'),
  (Join-Path $projectRoot 'tools\fec_transfer_graph.py'),
  (Join-Path $projectRoot 'tools\enrich_downstream.py'),
  (Join-Path $projectRoot 'tools\crypto_workbook_builder.mjs'),
  (Join-Path $projectRoot 'tools\finalize_crypto_excel.ps1'),
  (Join-Path $projectRoot 'inputs\trade_committee_overrides.csv')
) + $committeeFiles + $beneficiaryFiles + @(Get-ChildItem -LiteralPath $BeneficiaryDirectory -Recurse -File | Where-Object { $_.Name -in @('transfer-current.json','transfer-info.json','transfer-edges.csv') } | ForEach-Object FullName) + @(Get-ChildItem -LiteralPath $sourceRoot -Recurse -Filter 'source-receipt.json' | ForEach-Object FullName)
$dataInputPaths = $dataInputPaths | Where-Object { $_ -and (Test-Path -LiteralPath $_) }
$inputFingerprint = Get-CombinedFingerprint $dataInputPaths (
  "industry=$Industry|cycle=$CycleLabel"
)
$cacheHit = $false
if (-not $NoCache -and (Test-Path -LiteralPath $dataPath) -and (Test-Path -LiteralPath $manifestPath)) {
  try {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $actualDataHash = (
      Get-FileHash -LiteralPath $dataPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    $cacheHit = (
      [string]$manifest.input_fingerprint -eq $inputFingerprint -and
      [string]$manifest.database_sha256 -eq $databaseHash -and
      [string]$manifest.cycle_label -eq $CycleLabel -and
      [string]$manifest.data_sha256 -eq $actualDataHash -and
      [long]$manifest.data_bytes -eq (Get-Item -LiteralPath $dataPath).Length
    )
    if ($cacheHit) { $cacheHit = Test-JsonFile $dataPath }
  } catch { $cacheHit = $false }
}

$overallWatch = [Diagnostics.Stopwatch]::StartNew()
$exportSeconds = 0.0
if (-not $cacheHit) {
  $exportWatch = [Diagnostics.Stopwatch]::StartNew()
  $pendingData = "$dataPath.pending-$PID"
  & $RScriptPath $exporter $DatabasePath $pendingData $CommitteeMasterDirectory $BeneficiaryDirectory $Industry
  if ($LASTEXITCODE -ne 0) { throw "$Industry data export failed with exit code $LASTEXITCODE" }
  & $PythonPath (Join-Path $projectRoot 'tools\enrich_downstream.py') $pendingData $BeneficiaryDirectory
  if ($LASTEXITCODE -ne 0) { throw 'Transfer allocation and coverage enrichment failed.' }
  if (-not (Test-JsonFile $pendingData)) {
    throw "$Industry data export did not produce valid JSON."
  }
  $databaseHashAfterExport = Get-QuiescentDatabaseSha256 $DatabasePath
  if ($databaseHashAfterExport -ne $databaseHash) {
    throw (
      "Source database changed during the $Industry export; refusing to " +
      "publish data under a stale database fingerprint."
    )
  }
  $afterFingerprint = Get-CombinedFingerprint $dataInputPaths ("industry=$Industry|cycle=$CycleLabel")
  if ($afterFingerprint -ne $inputFingerprint) {
    throw 'Report code or source inputs changed during export; refusing to publish mixed inputs.'
  }
  Move-Item -LiteralPath $pendingData -Destination $dataPath -Force
  $dataItem = Get-Item -LiteralPath $dataPath
  $dataHash = (
    Get-FileHash -LiteralPath $dataPath -Algorithm SHA256
  ).Hash.ToLowerInvariant()
  Write-AtomicText $manifestPath ([pscustomobject]@{
    schema_version = 2
    input_fingerprint = $inputFingerprint
    database_sha256 = $databaseHash
    cycle_label = $CycleLabel
    data_sha256 = $dataHash
    data_bytes = [long]$dataItem.Length
    guard_receipt = 'embedded:metadata.export_guards'
    generated_at = [DateTimeOffset]::Now.ToString('o')
  } | ConvertTo-Json)
  $exportWatch.Stop(); $exportSeconds = $exportWatch.Elapsed.TotalSeconds
}

$buildDataPath = $dataPath
if ($CycleLabel) {
  $cycleToken = $CycleLabel -replace '[^0-9]+','_'
  $cycleDataPath = Join-Path $cacheRoot (
    "industry_data_cycle_${cycleToken}-$databaseToken.json"
  )
  $cycleManifestPath = Join-Path $cacheRoot (
    "industry_data_cycle_${cycleToken}-$databaseToken.manifest.json"
  )
  $sourceDataHash = (
    Get-FileHash -LiteralPath $dataPath -Algorithm SHA256
  ).Hash.ToLowerInvariant()
  $filterScriptHash = (
    Get-FileHash -LiteralPath $cycleFilterScript -Algorithm SHA256
  ).Hash.ToLowerInvariant()
  $cycleCacheHit = $false
  if (
    -not $NoCache -and
    (Test-Path -LiteralPath $cycleDataPath -PathType Leaf) -and
    (Test-Path -LiteralPath $cycleManifestPath -PathType Leaf)
  ) {
    try {
      $cycleManifest = Get-Content -Raw -LiteralPath (
        $cycleManifestPath
      ) | ConvertFrom-Json
      $actualCycleHash = (
        Get-FileHash -LiteralPath $cycleDataPath -Algorithm SHA256
      ).Hash.ToLowerInvariant()
      $cycleCacheHit = (
        [string]$cycleManifest.source_data_sha256 -eq $sourceDataHash -and
        [string]$cycleManifest.filter_script_sha256 -eq $filterScriptHash -and
        [string]$cycleManifest.cycle_label -eq $CycleLabel -and
        [string]$cycleManifest.output_sha256 -eq $actualCycleHash -and
        (Test-JsonFile $cycleDataPath)
      )
    } catch { $cycleCacheHit = $false }
  }
  if (
    -not $cycleCacheHit
  ) {
    $pendingCycleData = "$cycleDataPath.pending-$PID"
    & $NodePath '--max-old-space-size=4096' $cycleFilterScript $dataPath $pendingCycleData $CycleLabel
    if ($LASTEXITCODE -ne 0) {
      throw "Cycle cache build failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-JsonFile $pendingCycleData)) {
      throw "Cycle cache builder produced invalid JSON: $pendingCycleData"
    }
    Move-Item -LiteralPath $pendingCycleData -Destination $cycleDataPath -Force
    $cycleOutputHash = (
      Get-FileHash -LiteralPath $cycleDataPath -Algorithm SHA256
    ).Hash.ToLowerInvariant()
    Write-AtomicText $cycleManifestPath ([pscustomobject]@{
      schema_version = 1
      source_data_sha256 = $sourceDataHash
      filter_script_sha256 = $filterScriptHash
      cycle_label = $CycleLabel
      output_sha256 = $cycleOutputHash
      generated_at = [DateTimeOffset]::Now.ToString('o')
    } | ConvertTo-Json)
  } else {
    Write-Host "Cycle cache hit: $cycleDataPath"
  }
  if (-not (Test-JsonFile $cycleDataPath)) {
    throw "Cycle cache is not valid JSON: $cycleDataPath"
  }
  $buildDataPath = $cycleDataPath
}

$priorDefer = $env:MENTAT_DEFER_FORMULAS
$priorModules = $env:MENTAT_NODE_MODULES
$priorRender = $env:MENTAT_RENDER_PREVIEWS
$priorIndustry = $env:MENTAT_INDUSTRY
$priorCompactRaw = $env:MENTAT_COMPACT_RAW
$priorFormulaFacts = $env:MENTAT_FORMULA_FACTS
$priorCycleFilter = $env:MENTAT_CYCLE_FILTER
$largePayloadThresholdBytes = 120MB
$compactRawMode = if (
  $priorCompactRaw -in @('0', '1')
) {
  $priorCompactRaw
} elseif (
  (Get-Item -LiteralPath $dataPath).Length -ge
    $largePayloadThresholdBytes
) {
  '1'
} else {
  '0'
}
$formulaFactsMode = if (
  $priorFormulaFacts -in @('0', '1')
) {
  $priorFormulaFacts
} elseif (
  (Get-Item -LiteralPath $dataPath).Length -ge
    $largePayloadThresholdBytes
) {
  '1'
} else {
  '0'
}

$stageWorkbook = Join-Path $stageDirectory "${reportBaseName}.xlsx"
if ((Get-Item -LiteralPath $buildDataPath).Length -ge 256MB -and $compactRawMode -eq '1' -and $formulaFactsMode -eq '1') {
  $workbookDataPath = Join-Path $cacheRoot ("workbook_data${cycleToken}-$databaseToken.json")
  & $PythonPath (Join-Path $projectRoot 'tools\prepare_workbook_payload.py') $buildDataPath $workbookDataPath
  if ($LASTEXITCODE -ne 0) { throw 'Large workbook payload preparation failed.' }
  $buildDataPath = $workbookDataPath
}
$finalizerDataPath = Join-Path $stageDirectory 'finalizer_data.json'
$workbookCacheManifestPath = Join-Path $cacheRoot (
  "workbook_manifest_${cacheVariantToken}.json"
)
$artifactToolModule = Join-Path $NodeModulesPath (
  '@oai\artifact-tool\dist\artifact_tool.mjs'
)
$workbookFingerprintInputs = @(
  $buildDataPath,
  $builder,
  $finalizer,
  (Join-Path $projectRoot 'tools\prepare_workbook_payload.py'),
  $MyInvocation.MyCommand.Path
)
if (Test-Path -LiteralPath $artifactToolModule -PathType Leaf) {
  $workbookFingerprintInputs += $artifactToolModule
}
$workbookFingerprintSalt = (
  (
    'template={0}|industry={1}|cycle={2}|compact_raw={3}|' +
    'formula_facts={4}|render_previews={5}|source_db={6}'
  ) -f
      $templateContract,
      $Industry,
      $CycleLabel,
      $compactRawMode,
      $formulaFactsMode,
      [int][bool]$RenderPreviews,
      $databaseHash
)
$workbookFingerprint = Get-CombinedFingerprint `
  -Paths $workbookFingerprintInputs `
  -Salt $workbookFingerprintSalt
$workbookCacheHit = $false
$formulaReceiptObject = $null
$expectedWorksheetCount = 0
$buildWatch = New-Object Diagnostics.Stopwatch
$formulaWatch = New-Object Diagnostics.Stopwatch
$finalizeWatch = New-Object Diagnostics.Stopwatch
$workbookLockOwned = $false
$workbookLockStream = $null
$workbookLockToken = [Guid]::NewGuid().ToString('N')
New-Item -ItemType Directory -Path (
  Split-Path -Parent $WorkbookLockPath
) -Force | Out-Null
Write-Host "Waiting for workbook build slot: $WorkbookLockPath"
while (-not $workbookLockOwned) {
  try {
    $workbookLockStream = [IO.File]::Open(
      $WorkbookLockPath,
      [IO.FileMode]::CreateNew,
      [IO.FileAccess]::Write,
      [IO.FileShare]::None
    )
    try {
      $lockText = (
        "pid=$PID`r`ntoken=$workbookLockToken`r`n" +
        "created=$([DateTimeOffset]::Now.ToString('o'))`r`n"
      )
      $lockBytes = [Text.Encoding]::UTF8.GetBytes($lockText)
      $workbookLockStream.Write($lockBytes, 0, $lockBytes.Length)
      $workbookLockStream.Flush()
      $workbookLockOwned = $true
    } catch {
      $workbookLockStream.Dispose()
      $workbookLockStream = $null
      throw
    }
  } catch [IO.IOException] {
    if (
      (Test-Path -LiteralPath $WorkbookLockPath) -and
      (Get-Item -LiteralPath $WorkbookLockPath).LastWriteTimeUtc -lt
      [DateTime]::UtcNow.AddMinutes(-90)
    ) {
      $observedLock = ''
      try {
        $observedLock = Get-Content -Raw -LiteralPath $WorkbookLockPath
      } catch { $observedLock = '' }
      $ownerPid = 0
      if ($observedLock -match '(?m)^pid=(\d+)\s*$') {
        $ownerPid = [int]$Matches[1]
      }
      $ownerAlive = $false
      if ($ownerPid -gt 0) {
        $ownerAlive = $null -ne (
          Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
        )
      }
      if (-not $ownerAlive -and $observedLock) {
        $confirmedLock = ''
        try {
          $confirmedLock = Get-Content -Raw -LiteralPath $WorkbookLockPath
        } catch { $confirmedLock = '' }
        if ($confirmedLock -eq $observedLock) {
          try {
            Write-Warning "Reclaiming abandoned workbook build lock: $WorkbookLockPath"
            Remove-Item -LiteralPath $WorkbookLockPath -Force -ErrorAction Stop
            continue
          } catch {
            # A contender acquired and opened the lease after our confirmation.
            # Its FileShare.None handle is the authority; wait rather than steal.
          }
        }
      }
    }
    Start-Sleep -Seconds 1
  }
}
Write-Host "Workbook build slot acquired: $WorkbookLockPath"

try {
  if (
    -not $NoCache -and
    (Test-Path -LiteralPath $stageWorkbook -PathType Leaf) -and
    (Test-Path -LiteralPath $workbookCacheManifestPath -PathType Leaf)
  ) {
    $finalizeWatch.Start()
    try {
      $workbookManifest = Get-Content -Raw -LiteralPath (
        $workbookCacheManifestPath
      ) | ConvertFrom-Json
      $cachedWorkbookSha256 = (
        Get-FileHash -LiteralPath $stageWorkbook -Algorithm SHA256
      ).Hash.ToLowerInvariant()
      $workbookCacheHit = (
        [string]$workbookManifest.workbook_fingerprint -eq
          $workbookFingerprint -and
        [string]$workbookManifest.workbook_sha256 -eq
          $cachedWorkbookSha256
      )
      if ($workbookCacheHit) {
        $expectedWorksheetCount = [int](
          $workbookManifest.expected_worksheet_count
        )
        $formulaReceiptObject = $workbookManifest.formula_receipt
        if ($expectedWorksheetCount -lt 16 -or $null -eq $formulaReceiptObject) {
          $workbookCacheHit = $false
        } else {
          Assert-WorkbookPackage $stageWorkbook $expectedWorksheetCount
        }
      }
    } catch {
      $workbookCacheHit = $false
      $formulaReceiptObject = $null
      $expectedWorksheetCount = 0
    } finally {
      $finalizeWatch.Stop()
    }
  }

  if (-not $workbookCacheHit) {
    try {
    if ($NodeHeapMb -eq 0) {
      # Measure immediately before Node starts, after any arbitrarily long lock
      # wait. Cache hits never need a heap plan at all.
      $detectedPhysicalMb = 0
      try {
        Add-Type -AssemblyName Microsoft.VisualBasic -ErrorAction Stop
        $computerInfo = [Microsoft.VisualBasic.Devices.ComputerInfo]::new()
        $detectedPhysicalMb = [int][math]::Floor(
          [double]$computerInfo.TotalPhysicalMemory / 1MB
        )
      } catch { $detectedPhysicalMb = 0 }
      $availableMb = 0
      try {
        $osInfo = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
        # FreePhysicalMemory is in KB.
        $availableMb = [int][math]::Floor(
          [double]$osInfo.FreePhysicalMemory / 1KB
        )
      } catch { $availableMb = 0 }
      $heapPlan = Get-MentatNodeHeapPlan `
        -TotalPhysicalMb $detectedPhysicalMb `
        -AvailableMb $availableMb
      Write-Host (
        'Node heap sizing: total={0}MB available={1}MB safe_cap={2}MB status={3}' -f
          $detectedPhysicalMb,
          $availableMb,
          $heapPlan.safe_cap_mb,
          $heapPlan.reason
      )
      if (-not $heapPlan.ready) {
        throw (
          'Automatic Node heap sizing cannot safely provide the 8,192 MB ' +
          "minimum (total=$detectedPhysicalMb MB; available=$availableMb MB; " +
          "safe cap=$($heapPlan.safe_cap_mb) MB). Wait for collection/build " +
          'processes to release memory, or pass -NodeHeapMb explicitly only ' +
          'after verifying that capacity is available.'
        )
      }
      $NodeHeapMb = [int]$heapPlan.heap_mb
    }
    Write-Host (
      'Workbook RAM plan: node_heap_mb={0} performance_budget_minutes={1:n2}' -f
        $NodeHeapMb,
        $PerformanceBudgetMinutes
    )
    $env:MENTAT_INDUSTRY = $Industry
    $env:MENTAT_DEFER_FORMULAS = '1'
    $env:MENTAT_NODE_MODULES = $NodeModulesPath
    $env:MENTAT_RENDER_PREVIEWS = if ($RenderPreviews) { '1' } else { '0' }
    # artifact-tool uses an in-memory managed workbook. Preserve every accepted
    # row but omit audit-only raw columns from large Excel payloads; the complete
    # audit trail remains in the source database and export JSON.
    $env:MENTAT_COMPACT_RAW = $compactRawMode
    $env:MENTAT_FORMULA_FACTS = $formulaFactsMode
    $env:MENTAT_CYCLE_FILTER = $CycleLabel
    $buildWatch.Start()
    & $NodePath "--max-old-space-size=$NodeHeapMb" $builder $buildDataPath $stageDirectory $databaseHash
    if ($LASTEXITCODE -ne 0) { throw "Workbook build failed with exit code $LASTEXITCODE" }
    $buildWatch.Stop()
    } finally {
      $env:MENTAT_DEFER_FORMULAS = $priorDefer
      $env:MENTAT_NODE_MODULES = $priorModules
      $env:MENTAT_RENDER_PREVIEWS = $priorRender
      $env:MENTAT_INDUSTRY = $priorIndustry
      $env:MENTAT_COMPACT_RAW = $priorCompactRaw
      $env:MENTAT_FORMULA_FACTS = $priorFormulaFacts
      $env:MENTAT_CYCLE_FILTER = $priorCycleFilter
    }

    if (-not (Test-Path -LiteralPath $stageWorkbook)) { throw "Workbook builder did not create $stageWorkbook" }
    if (-not (Test-Path -LiteralPath $finalizerDataPath)) {
      throw "Workbook builder did not create $finalizerDataPath"
    }
    if (-not (Test-JsonFile $finalizerDataPath)) {
      throw "Workbook builder created invalid finalizer data."
    }
    $formulaWatch.Start()
    $formulaReceipt = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $finalizer -WorkbookPath $stageWorkbook -JsonPath $finalizerDataPath -ExcelMutexName $ExcelMutexName
    if ($LASTEXITCODE -ne 0) { throw "Excel formula finalization failed with exit code $LASTEXITCODE" }
    $formulaWatch.Stop()
    $formulaReceiptObject = (($formulaReceipt -join "`n") | ConvertFrom-Json)
    $expectedWorksheetCount = [int]$formulaReceiptObject.expected_worksheet_count
    if ($expectedWorksheetCount -lt 16) {
      throw "Excel formula finalizer returned an invalid worksheet count."
    }
    $finalizeWatch.Start()
    try {
      Assert-WorkbookPackage $stageWorkbook $expectedWorksheetCount
      $workbookSha256 = (
        Get-FileHash -LiteralPath $stageWorkbook -Algorithm SHA256
      ).Hash.ToLowerInvariant()
      Write-AtomicText $workbookCacheManifestPath ([pscustomobject]@{
        workbook_fingerprint = $workbookFingerprint
        workbook_sha256 = $workbookSha256
        template_contract = $templateContract
        expected_worksheet_count = $expectedWorksheetCount
        generated_at = [DateTimeOffset]::Now.ToString('o')
        formula_receipt = $formulaReceiptObject
      } | ConvertTo-Json -Depth 10)
    } finally {
      $finalizeWatch.Stop()
    }
  } else {
    Write-Host (
      'Workbook cache hit: verified package and SHA-256; skipping Node build ' +
      'and Excel formula finalization.'
    )
  }

  $targetWorkbook = Join-Path $OutputDirectory "${reportBaseName}.xlsx"
  $pendingWorkbook = "$targetWorkbook.pending-$PID"
  $finalizeWatch.Start()
  try {
    # Publish companions on cache hits too, binding every CSV to the validated
    # workbook and exact payload. A bundle reader can reject partial updates.
    & $PythonPath (Join-Path $projectRoot 'tools\enrich_downstream.py') $buildDataPath $BeneficiaryDirectory --audit-only --workbook $stageWorkbook --audit-directory (Join-Path $OutputDirectory ($reportBaseName + '.audit'))
    if ($LASTEXITCODE -ne 0) { throw 'Audit companion publication failed.' }
    Copy-Item -LiteralPath $stageWorkbook -Destination $pendingWorkbook -Force
    Move-Item -LiteralPath $pendingWorkbook -Destination $targetWorkbook -Force
  } finally {
    $finalizeWatch.Stop()
  }
} finally {
  if ($null -ne $workbookLockStream) {
    $workbookLockStream.Dispose()
    $workbookLockStream = $null
  }
  if ($workbookLockOwned -and (Test-Path -LiteralPath $WorkbookLockPath)) {
    $currentLock = ''
    try {
      $currentLock = Get-Content -Raw -LiteralPath $WorkbookLockPath
    } catch { $currentLock = '' }
    if ($currentLock -match (
      '(?m)^token=' + [regex]::Escape($workbookLockToken) + '\s*$'
    )) {
      Remove-Item -LiteralPath $WorkbookLockPath -Force
    } else {
      Write-Warning (
        'Workbook lock ownership changed; refusing to remove another ' +
        "process lease: $WorkbookLockPath"
      )
    }
  }
}
$overallWatch.Stop()
$under45Minutes = $overallWatch.Elapsed.TotalMinutes -lt 45
$underPerformanceBudget = (
  $overallWatch.Elapsed.TotalMinutes -lt $PerformanceBudgetMinutes
)

[pscustomobject]@{
  industry = $Industry
  workbook = $targetWorkbook
  bytes = (Get-Item -LiteralPath $targetWorkbook).Length
  database_sha256 = $databaseHash
  data_sha256 = (
    Get-FileHash -LiteralPath $dataPath -Algorithm SHA256
  ).Hash.ToLowerInvariant()
  data_manifest = $manifestPath
  export_guard_receipt = 'embedded:metadata.export_guards'
  template_contract = $templateContract
  cache_hit = $cacheHit
  data_cache_hit = $cacheHit
  workbook_cache_hit = $workbookCacheHit
  export_seconds = [math]::Round($exportSeconds,3)
  build_seconds = [math]::Round($buildWatch.Elapsed.TotalSeconds,3)
  formula_seconds = [math]::Round($formulaWatch.Elapsed.TotalSeconds,3)
  finalize_seconds = [math]::Round($finalizeWatch.Elapsed.TotalSeconds,3)
  total_seconds = [math]::Round($overallWatch.Elapsed.TotalSeconds,3)
  node_heap_mb = $NodeHeapMb
  runtimes = [ordered]@{
    node_path = $NodePath
    node_modules_path = $NodeModulesPath
    rscript_path = [IO.Path]::GetFullPath($RScriptPath)
  }
  performance_budget_minutes = $PerformanceBudgetMinutes
  performance_budget_pass = $underPerformanceBudget
  under_15_minutes = $overallWatch.Elapsed.TotalMinutes -lt 15
  under_45_minutes = $under45Minutes
  formula_receipt = $formulaReceiptObject
} | ConvertTo-Json -Depth 5
