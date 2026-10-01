param(
    [int]$ShardMaxAttempts = 8,
    [int]$ShardRetryDelaySeconds = 300,
    [int]$PipelineMaxAttempts = 240,
    [int]$PipelineRetryDelaySeconds = 300
)

$ErrorActionPreference = "Stop"
$Workspace = Split-Path -Parent $PSScriptRoot
$PowerShell = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
$ShardRunner = Join-Path $PSScriptRoot "run_legislation_identifier_probe_shards.ps1"
$Pipeline = Join-Path $PSScriptRoot "run_legislation_coverage_pipeline.ps1"
$Log = Join-Path $Workspace "audits\legfix5\parallel_identifier_then_pipeline.log"

Set-Location -LiteralPath $Workspace

& $PowerShell -NoProfile -ExecutionPolicy Bypass -File $ShardRunner `
    -MaxAttempts $ShardMaxAttempts `
    -RetryDelaySeconds $ShardRetryDelaySeconds *>> $Log
$shardExit = $LASTEXITCODE
if ($shardExit -ne 0) {
    throw "Parallel identifier harvest/consolidation failed: exit=$shardExit"
}

& $PowerShell -NoProfile -ExecutionPolicy Bypass -File $Pipeline `
    -MaxAttempts $PipelineMaxAttempts `
    -RetryDelaySeconds $PipelineRetryDelaySeconds *>> $Log
exit $LASTEXITCODE
