<#
.SYNOPSIS
Build the audited Crypto Industry Spending Overview workbook in one command.

.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\generate_crypto_report.ps1 `
  -DatabasePath C:\path\to\mentat.db -OutputDirectory C:\path\to\reports
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
  [ValidateRange(4096,32768)]
  [int]$NodeHeapMb = 16384,
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
$Industry = $Industry.Trim()
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
if (-not $CommitteeMasterDirectory) { $CommitteeMasterDirectory = Join-Path $projectRoot 'inputs\fec_committee_master' }
if (-not $BeneficiaryDirectory) { $BeneficiaryDirectory = Join-Path $projectRoot 'inputs\fec_beneficiary' }
if (-not $NodePath) {
  $bundledNode = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
  $NodePath = if (Test-Path -LiteralPath $bundledNode) { $bundledNode } else { (Get-Command node -ErrorAction Stop).Source }
}
if (-not $NodeModulesPath) {
  $NodeModulesPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules'
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
foreach ($requiredPath in @($DatabasePath,$RScriptPath,$NodePath,$NodeModulesPath,$exporter,$builder,$cycleFilterScript,$finalizer,$beneficiaryModule) + $committeeFiles + $beneficiaryFiles) {
  if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required report input or runtime is missing: $requiredPath" }
}

function Test-JsonFile([string]$Path) {
  $validationScript = "const fs=require('node:fs');JSON.parse(fs.readFileSync(process.argv[1],'utf8'));"
  $priorErrorAction = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    & $NodePath '--max-old-space-size=8192' '-e' $validationScript $Path 2>$null | Out-Null
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

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$cacheRoot = Join-Path $projectRoot ('.cache\industry-report\' + $industryToken)
$stageDirectory = Join-Path $cacheRoot 'stage'
New-Item -ItemType Directory -Path $cacheRoot,$stageDirectory -Force | Out-Null
$dataPath = Join-Path $cacheRoot 'industry_data.json'
$manifestPath = Join-Path $cacheRoot 'manifest.json'
$databaseHash = (Get-FileHash -LiteralPath $DatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()
$dataInputPaths = @(
  $DatabasePath,
  $exporter,
  $beneficiaryModule
) + $committeeFiles + $beneficiaryFiles
$inputFingerprint = Get-CombinedFingerprint $dataInputPaths $Industry
$cacheHit = $false
if (-not $NoCache -and (Test-Path -LiteralPath $dataPath) -and (Test-Path -LiteralPath $manifestPath)) {
  try {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $cacheHit = [string]$manifest.input_fingerprint -eq $inputFingerprint
    if (
      -not $cacheHit -and
      [string]$manifest.database_sha256 -eq $databaseHash
    ) {
      $latestInputWrite = (
        $dataInputPaths |
          ForEach-Object { (Get-Item -LiteralPath $_).LastWriteTimeUtc } |
          Measure-Object -Maximum
      ).Maximum
      $cacheHit = (Get-Item -LiteralPath $dataPath).LastWriteTimeUtc -ge
        $latestInputWrite
      if ($cacheHit) {
        Write-Host 'Reusing fresh export after report-builder-only changes.'
      }
    }
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
  if (-not (Test-JsonFile $pendingData)) {
    throw "$Industry data export did not produce valid JSON."
  }
  Move-Item -LiteralPath $pendingData -Destination $dataPath -Force
  Write-AtomicText $manifestPath ([pscustomobject]@{
    input_fingerprint = $inputFingerprint
    database_sha256 = $databaseHash
    generated_at = [DateTimeOffset]::Now.ToString('o')
  } | ConvertTo-Json)
  $exportWatch.Stop(); $exportSeconds = $exportWatch.Elapsed.TotalSeconds
}

$buildDataPath = $dataPath
if ($CycleLabel) {
  $cycleToken = $CycleLabel -replace '[^0-9]+','_'
  $cycleDataPath = Join-Path $cacheRoot "industry_data_cycle_${cycleToken}.json"
  if (
    -not (Test-Path -LiteralPath $cycleDataPath) -or
    (Get-Item -LiteralPath $cycleDataPath).LastWriteTimeUtc -lt
      (Get-Item -LiteralPath $dataPath).LastWriteTimeUtc
  ) {
    & $NodePath '--max-old-space-size=4096' $cycleFilterScript $dataPath $cycleDataPath $CycleLabel
    if ($LASTEXITCODE -ne 0) {
      throw "Cycle cache build failed with exit code $LASTEXITCODE"
    }
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
$workbookLockOwned = $false
try {
  New-Item -ItemType Directory -Path (
    Split-Path -Parent $WorkbookLockPath
  ) -Force | Out-Null
  Write-Host "Waiting for workbook build slot: $WorkbookLockPath"
  while (-not $workbookLockOwned) {
    try {
      $lockStream = [IO.File]::Open(
        $WorkbookLockPath,
        [IO.FileMode]::CreateNew,
        [IO.FileAccess]::Write,
        [IO.FileShare]::None
      )
      $workbookLockOwned = $true
      try {
        $lockText = "pid=$PID`r`ncreated=$([DateTimeOffset]::Now.ToString('o'))`r`n"
        $lockBytes = [Text.Encoding]::UTF8.GetBytes($lockText)
        $lockStream.Write($lockBytes, 0, $lockBytes.Length)
      } finally {
        $lockStream.Dispose()
      }
    } catch [IO.IOException] {
      if (
        (Test-Path -LiteralPath $WorkbookLockPath) -and
        (Get-Item -LiteralPath $WorkbookLockPath).LastWriteTimeUtc -lt
        [DateTime]::UtcNow.AddMinutes(-90)
      ) {
        Write-Warning "Removing stale workbook build lock: $WorkbookLockPath"
        Remove-Item -LiteralPath $WorkbookLockPath -Force -ErrorAction SilentlyContinue
        continue
      }
      Start-Sleep -Seconds 1
    }
  }
  Write-Host "Workbook build slot acquired: $WorkbookLockPath"
  $env:MENTAT_INDUSTRY = $Industry
  $env:MENTAT_DEFER_FORMULAS = '1'
  $env:MENTAT_NODE_MODULES = $NodeModulesPath
  $env:MENTAT_RENDER_PREVIEWS = if ($RenderPreviews) { '1' } else { '0' }
  # artifact-tool uses an in-memory managed workbook. Preserve every accepted
  # row but omit audit-only raw columns from large Excel payloads; the complete
  # audit trail remains in the source database and export JSON.
  $env:MENTAT_COMPACT_RAW = if (
    $priorCompactRaw -in @('0', '1')
  ) {
    $priorCompactRaw
  } elseif ((Get-Item -LiteralPath $dataPath).Length -ge 150MB) {
    '1'
  } else {
    '0'
  }
  $env:MENTAT_FORMULA_FACTS = if (
    $priorFormulaFacts -in @('0', '1')
  ) {
    $priorFormulaFacts
  } elseif ((Get-Item -LiteralPath $dataPath).Length -ge 150MB) {
    '1'
  } else {
    '0'
  }
  $env:MENTAT_CYCLE_FILTER = $CycleLabel
  $buildWatch = [Diagnostics.Stopwatch]::StartNew()
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
  if ($workbookLockOwned -and (Test-Path -LiteralPath $WorkbookLockPath)) {
    Remove-Item -LiteralPath $WorkbookLockPath -Force
  }
}

$stageWorkbook = Join-Path $stageDirectory "${reportBaseName}.xlsx"
if (-not (Test-Path -LiteralPath $stageWorkbook)) { throw "Workbook builder did not create $stageWorkbook" }
$finalizerDataPath = Join-Path $stageDirectory 'finalizer_data.json'
if (-not (Test-Path -LiteralPath $finalizerDataPath)) {
  throw "Workbook builder did not create $finalizerDataPath"
}
if (-not (Test-JsonFile $finalizerDataPath)) {
  throw "Workbook builder created invalid finalizer data."
}
$formulaWatch = [Diagnostics.Stopwatch]::StartNew()
$formulaReceipt = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $finalizer -WorkbookPath $stageWorkbook -JsonPath $finalizerDataPath -ExcelMutexName $ExcelMutexName
if ($LASTEXITCODE -ne 0) { throw "Excel formula finalization failed with exit code $LASTEXITCODE" }
$formulaWatch.Stop()
$formulaReceiptObject = (($formulaReceipt -join "`n") | ConvertFrom-Json)
$expectedWorksheetCount = [int]$formulaReceiptObject.expected_worksheet_count
if ($expectedWorksheetCount -lt 16) {
  throw "Excel formula finalizer returned an invalid worksheet count."
}
Assert-WorkbookPackage $stageWorkbook $expectedWorksheetCount

$targetWorkbook = Join-Path $OutputDirectory "${reportBaseName}.xlsx"
$pendingWorkbook = "$targetWorkbook.pending-$PID"
Copy-Item -LiteralPath $stageWorkbook -Destination $pendingWorkbook -Force
Move-Item -LiteralPath $pendingWorkbook -Destination $targetWorkbook -Force
$overallWatch.Stop()
$under45Minutes = $overallWatch.Elapsed.TotalMinutes -lt 45

[pscustomobject]@{
  industry = $Industry
  workbook = $targetWorkbook
  bytes = (Get-Item -LiteralPath $targetWorkbook).Length
  database_sha256 = $databaseHash
  cache_hit = $cacheHit
  export_seconds = [math]::Round($exportSeconds,3)
  build_seconds = [math]::Round($buildWatch.Elapsed.TotalSeconds,3)
  formula_seconds = [math]::Round($formulaWatch.Elapsed.TotalSeconds,3)
  total_seconds = [math]::Round($overallWatch.Elapsed.TotalSeconds,3)
  under_45_minutes = $under45Minutes
  formula_receipt = $formulaReceiptObject
} | ConvertTo-Json -Depth 5
