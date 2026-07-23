[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$Industry,
  [string]$DatabasePath = '',
  [string]$OutputDirectory = '',
  [string]$CommitteeMasterDirectory = '',
  [string]$BeneficiaryDirectory = '',
  [string]$RScriptPath = '',
  [string]$NodePath = '',
  [string]$NodeModulesPath = '',
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
$generator = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) 'generate_crypto_report.ps1'
$arguments = @{
  Industry = $Industry
  ExcelMutexName = $ExcelMutexName
}
if ($DatabasePath) { $arguments.DatabasePath = $DatabasePath }
if ($OutputDirectory) { $arguments.OutputDirectory = $OutputDirectory }
if ($CommitteeMasterDirectory) { $arguments.CommitteeMasterDirectory = $CommitteeMasterDirectory }
if ($BeneficiaryDirectory) { $arguments.BeneficiaryDirectory = $BeneficiaryDirectory }
if ($RScriptPath) { $arguments.RScriptPath = $RScriptPath }
if ($NodePath) { $arguments.NodePath = $NodePath }
if ($NodeModulesPath) { $arguments.NodeModulesPath = $NodeModulesPath }
$arguments.NodeHeapMb = $NodeHeapMb
$arguments.PerformanceBudgetMinutes = $PerformanceBudgetMinutes
if ($WorkbookLockPath) { $arguments.WorkbookLockPath = $WorkbookLockPath }
if ($CycleLabel) { $arguments.CycleLabel = $CycleLabel }
if ($NoCache) { $arguments.NoCache = $true }
if ($RenderPreviews) { $arguments.RenderPreviews = $true }

& $generator @arguments
if ($LASTEXITCODE -ne 0) {
  exit $LASTEXITCODE
}
