$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$builderPath = Join-Path $projectRoot 'tools\crypto_workbook_builder.mjs'
$builderText = Get-Content -Raw -LiteralPath $builderPath

$requiredFragments = @(
  'function emptyRawTablePlaceholder(headers, sheetName, exceptionSheet)',
  '["Source ID", "NO_SOURCE_ROWS"]',
  '["Fact ID", "NO_SOURCE_ROWS"]',
  '["Include in Analysis", "No"]',
  'exceptionSheet ? "Outside requested cycles" : "OK"',
  ': [emptyRawTablePlaceholder(headers, sheetName, exceptionSheet)]',
  '4 + tableData.length'
)

foreach ($fragment in $requiredFragments) {
  if (-not $builderText.Contains($fragment)) {
    throw "Workbook builder is missing the empty-table guard fragment: $fragment"
  }
}

if ($builderText.Contains('4 + data.length')) {
  throw 'Workbook tables must be sized from guarded tableData, not raw data.'
}

$buildPath = Join-Path $projectRoot 'tools\build_industry_report.ps1'
$finalizerPath = Join-Path $projectRoot 'tools\finalize_crypto_excel.ps1'
$parseErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
  $buildPath,
  [ref]$null,
  [ref]$parseErrors
)
if ($parseErrors.Count) {
  throw "build_industry_report.ps1 has parse errors: $($parseErrors[0].Message)"
}
$parseErrors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile(
  $finalizerPath,
  [ref]$null,
  [ref]$parseErrors
)
if ($parseErrors.Count) {
  throw "finalize_crypto_excel.ps1 has parse errors: $($parseErrors[0].Message)"
}

$buildText = Get-Content -Raw -LiteralPath $buildPath
$finalizerText = Get-Content -Raw -LiteralPath $finalizerPath
foreach ($fragment in @(
  'data_sha256',
  'cycle_label',
  'source_data_sha256',
  'nonempty WAL sidecar',
  'Get-QuiescentDatabaseSha256',
  'databaseHashAfterExport',
  'changed during the $Industry export',
  'token=$workbookLockToken'
)) {
  if (-not $buildText.Contains($fragment)) {
    throw "Report builder is missing cache/lease guard fragment: $fragment"
  }
}
if ($buildText.Contains('Reusing fresh export after report-builder-only changes.')) {
  throw 'Content-fingerprint mismatches must never fall back to mtimes.'
}
if ($finalizerText.Contains('$compactJson')) {
  throw 'Finalizer must honor the explicit JsonPath without sibling override.'
}
$targetMove = $buildText.LastIndexOf(
  'Move-Item -LiteralPath $pendingWorkbook -Destination $targetWorkbook -Force'
)
$ownedRelease = $buildText.LastIndexOf(
  'Remove-Item -LiteralPath $WorkbookLockPath -Force'
)
if ($targetMove -lt 0 -or $ownedRelease -le $targetMove) {
  throw 'Workbook lease must be released only after atomic target publication.'
}

# Companion Data workbook publication order.
#
# The console globs the published folder and pairs the two books by name, and
# `sourceGuard accept` advances the accepted source baseline for the NEXT run.
# If acceptance ran between the two publications, a failure in the Data copy
# would leave the baseline advanced past an Overview whose companion never
# landed, and the following build would treat the half-published pair as the
# accepted state. The Data book therefore goes out after the Overview and
# before acceptance, under the same copy-then-atomic-move.
foreach ($fragment in @(
  'stage_sha256',
  '$pendingStage = "$stagePath.pending-$PID"',
  '--staging $pendingStage',
  'PRAGMA integrity_check',
  'Move-Item -LiteralPath $pendingStage -Destination $stagePath -Force',
  '--overview-receipt $overviewReceiptPath',
  'Assert-WorkbookPackage $stageDataWorkbook $dataWorksheetCount',
  'data_workbook_sha256 = $dataWorkbookSha256'
)) {
  if (-not $buildText.Contains($fragment)) {
    throw "Report builder is missing a tidy data-workbook fragment: $fragment"
  }
}

$dataMove = $buildText.LastIndexOf(
  'Move-Item -LiteralPath $pendingDataWorkbook -Destination $targetDataWorkbook -Force'
)
$sourceAccept = $buildText.LastIndexOf(
  '& $PythonPath $sourceGuard accept --receipt $sourceGuardReceipt'
)
if ($dataMove -lt 0) {
  throw 'The companion Data workbook must be published by an atomic move.'
}
if ($dataMove -le $targetMove) {
  throw 'The companion Data workbook must be published after the Overview.'
}
if ($sourceAccept -lt 0 -or $sourceAccept -le $dataMove) {
  throw 'Accepted-source advance must follow BOTH workbook publications.'
}
if ($ownedRelease -le $dataMove) {
  throw 'Workbook lease must be released only after both books are published.'
}

$writerCall = $buildText.IndexOf('& $PythonPath $tidyWriter --staging $stagePath')
$overviewCopy = $buildText.LastIndexOf(
  'Copy-Item -LiteralPath $stageWorkbook -Destination $pendingWorkbook -Force'
)
if ($writerCall -lt 0 -or $overviewCopy -lt 0 -or $writerCall -ge $overviewCopy) {
  throw 'The tidy writer must run before anything is copied into the output folder.'
}
if ($buildText.Contains('Assert-WorkbookPackage $stageDataWorkbook $expectedWorksheetCount')) {
  throw 'The Data book must be checked against its OWN receipt, not the Overview count.'
}

Write-Host 'Test-MentatWorkbookBuilderGuards: PASS'
