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

Write-Host 'Test-MentatWorkbookBuilderGuards: PASS'
