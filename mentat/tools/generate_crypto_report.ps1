<#
.SYNOPSIS
Build the audited Crypto Industry Spending Overview workbook in one command.

.EXAMPLE
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\generate_crypto_report.ps1 `
  -DatabasePath C:\path\to\mentat.db -OutputDirectory C:\path\to\reports
#>
[CmdletBinding()]
param(
  [string]$DatabasePath = '',
  [string]$OutputDirectory = '',
  [string]$CommitteeMasterDirectory = '',
  [string]$BeneficiaryDirectory = '',
  [string]$RScriptPath = 'C:\Program Files\R\R-4.6.0\bin\Rscript.exe',
  [string]$NodePath = '',
  [string]$NodeModulesPath = '',
  [switch]$NoCache,
  [switch]$RenderPreviews
)

$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptRoot

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
$exporter = Join-Path $scriptRoot 'export_crypto_spending_data.R'
$builder = Join-Path $scriptRoot 'crypto_workbook_builder.mjs'
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
foreach ($requiredPath in @($DatabasePath,$RScriptPath,$NodePath,$NodeModulesPath,$exporter,$builder,$finalizer,$beneficiaryModule) + $committeeFiles + $beneficiaryFiles) {
  if (-not (Test-Path -LiteralPath $requiredPath)) { throw "Required report input or runtime is missing: $requiredPath" }
}

function Get-CombinedFingerprint([string[]]$Paths) {
  $lines = foreach ($path in $Paths) {
    $item = Get-Item -LiteralPath $path
    $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant()
    "$($item.Name)|$($item.Length)|$hash"
  }
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
  } finally { $archive.Dispose() }
}

New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
$cacheRoot = Join-Path $projectRoot '.cache\crypto-report'
$stageDirectory = Join-Path $cacheRoot 'stage'
New-Item -ItemType Directory -Path $cacheRoot,$stageDirectory -Force | Out-Null
$dataPath = Join-Path $cacheRoot 'crypto_data.json'
$manifestPath = Join-Path $cacheRoot 'manifest.json'
$databaseHash = (Get-FileHash -LiteralPath $DatabasePath -Algorithm SHA256).Hash.ToLowerInvariant()
$inputFingerprint = Get-CombinedFingerprint (@($DatabasePath,$exporter,$builder,$finalizer,$beneficiaryModule) + $committeeFiles + $beneficiaryFiles)
$cacheHit = $false
if (-not $NoCache -and (Test-Path -LiteralPath $dataPath) -and (Test-Path -LiteralPath $manifestPath)) {
  try {
    $manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
    $cacheHit = [string]$manifest.input_fingerprint -eq $inputFingerprint
    if ($cacheHit) { [void](Get-Content -Raw -LiteralPath $dataPath | ConvertFrom-Json) }
  } catch { $cacheHit = $false }
}

$overallWatch = [Diagnostics.Stopwatch]::StartNew()
$exportSeconds = 0.0
if (-not $cacheHit) {
  $exportWatch = [Diagnostics.Stopwatch]::StartNew()
  $pendingData = "$dataPath.pending-$PID"
  & $RScriptPath $exporter $DatabasePath $pendingData $CommitteeMasterDirectory $BeneficiaryDirectory
  if ($LASTEXITCODE -ne 0) { throw "Crypto data export failed with exit code $LASTEXITCODE" }
  [void](Get-Content -Raw -LiteralPath $pendingData | ConvertFrom-Json)
  Move-Item -LiteralPath $pendingData -Destination $dataPath -Force
  Write-AtomicText $manifestPath ([pscustomobject]@{
    input_fingerprint = $inputFingerprint
    database_sha256 = $databaseHash
    generated_at = [DateTimeOffset]::Now.ToString('o')
  } | ConvertTo-Json)
  $exportWatch.Stop(); $exportSeconds = $exportWatch.Elapsed.TotalSeconds
}

$priorDefer = $env:MENTAT_DEFER_FORMULAS
$priorModules = $env:MENTAT_NODE_MODULES
$priorRender = $env:MENTAT_RENDER_PREVIEWS
try {
  $env:MENTAT_DEFER_FORMULAS = '1'
  $env:MENTAT_NODE_MODULES = $NodeModulesPath
  $env:MENTAT_RENDER_PREVIEWS = if ($RenderPreviews) { '1' } else { '0' }
  $buildWatch = [Diagnostics.Stopwatch]::StartNew()
  & $NodePath '--max-old-space-size=8192' $builder $dataPath $stageDirectory $databaseHash
  if ($LASTEXITCODE -ne 0) { throw "Workbook build failed with exit code $LASTEXITCODE" }
  $buildWatch.Stop()
} finally {
  $env:MENTAT_DEFER_FORMULAS = $priorDefer
  $env:MENTAT_NODE_MODULES = $priorModules
  $env:MENTAT_RENDER_PREVIEWS = $priorRender
}

$stageWorkbook = Join-Path $stageDirectory 'Crypto Industry Spending Overview.xlsx'
if (-not (Test-Path -LiteralPath $stageWorkbook)) { throw "Workbook builder did not create $stageWorkbook" }
$formulaWatch = [Diagnostics.Stopwatch]::StartNew()
$formulaReceipt = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $finalizer -WorkbookPath $stageWorkbook -JsonPath $dataPath
if ($LASTEXITCODE -ne 0) { throw "Excel formula finalization failed with exit code $LASTEXITCODE" }
$formulaWatch.Stop()
$payload = Get-Content -Raw -LiteralPath $dataPath | ConvertFrom-Json
$expectedWorksheetCount = 16 + @($payload.companies).Count
Assert-WorkbookPackage $stageWorkbook $expectedWorksheetCount

$targetWorkbook = Join-Path $OutputDirectory 'Crypto Industry Spending Overview.xlsx'
$pendingWorkbook = "$targetWorkbook.pending-$PID"
Copy-Item -LiteralPath $stageWorkbook -Destination $pendingWorkbook -Force
Move-Item -LiteralPath $pendingWorkbook -Destination $targetWorkbook -Force
$overallWatch.Stop()
if ($overallWatch.Elapsed.TotalMinutes -ge 45) {
  throw "Performance gate failed: report generation took $([math]::Round($overallWatch.Elapsed.TotalMinutes,2)) minutes."
}

[pscustomobject]@{
  workbook = $targetWorkbook
  bytes = (Get-Item -LiteralPath $targetWorkbook).Length
  database_sha256 = $databaseHash
  cache_hit = $cacheHit
  export_seconds = [math]::Round($exportSeconds,3)
  build_seconds = [math]::Round($buildWatch.Elapsed.TotalSeconds,3)
  formula_seconds = [math]::Round($formulaWatch.Elapsed.TotalSeconds,3)
  total_seconds = [math]::Round($overallWatch.Elapsed.TotalSeconds,3)
  under_45_minutes = $true
  formula_receipt = (($formulaReceipt -join "`n") | ConvertFrom-Json)
} | ConvertTo-Json -Depth 5
