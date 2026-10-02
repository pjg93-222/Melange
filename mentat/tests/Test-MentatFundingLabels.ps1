$ErrorActionPreference = 'Stop'
$path = Join-Path (Split-Path $PSScriptRoot -Parent) 'tools\finalize_crypto_excel.ps1'
$errors = $null
$ast = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$null, [ref]$errors)
if ($errors.Count) { throw $errors[0].Message }
# Load only pure formula helpers. This test never starts Excel or edits a book.
foreach ($name in @('Category-Label','Scope-Expression','Master-Expression')) {
  $definition = $ast.FindAll({ param($node)
    $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name
  }, $true)
  if ($definition.Count -ne 1) { throw "Missing helper $name" }
  Invoke-Expression $definition[0].Extent.Text
}
$formulaFacts = $true
$scope = Scope-Expression 'Cycle2024' 'D'
if (-not $scope.Contains('IF([@Scope]="Company PAC receipts","Company PAC",[@Scope])')) {
  throw 'Displayed PAC receipt scope must map to the canonical source category.'
}
$script:captured = @{}
function Set-TableColumnFormula($Table, [string]$ColumnName, [string]$Formula) {
  $script:captured[$ColumnName] = $Formula
}
$categoryLoop = $ast.FindAll({ param($node)
  $node -is [Management.Automation.Language.ForEachStatementAst] -and
  $node.Variable.VariablePath.UserPath -eq 'category' -and
  $node.Body.Extent.Text.Contains('Set-TableColumnFormula')
}, $true)
if ($categoryLoop.Count -ne 1) { throw 'Expected one master category formula loop.' }
$masterCategories = @('Company PAC','Other PAC')
$sourceTableName = 'Cycle2024'
$table = $null
Invoke-Expression $categoryLoop[0].Extent.Text
foreach ($label in @('Company PAC receipts','Other PAC')) {
  foreach ($suffix in @('',' %',' D',' R',' R %')) {
    if (-not $captured.ContainsKey($label + $suffix)) { throw "Missing formula for $label$suffix" }
  }
}
if ($captured.ContainsKey('Company PAC')) { throw 'Formula writer used the obsolete display header.' }
if (-not $captured['Company PAC receipts'].Contains('[Recipient Category],"Company PAC"')) {
  throw 'Receipt display wording leaked into the source SUMIFS criterion.'
}
if (-not $captured['Company PAC receipts R %'].Contains('[@[Company PAC receipts D]]')) {
  throw 'PAC partisan formulas must reference the renamed columns.'
}
Write-Host 'Test-MentatFundingLabels: PASS'
