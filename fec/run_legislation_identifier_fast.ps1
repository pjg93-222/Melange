param(
    [string]$Plan = "audits\legfix5\identifier_probe_parallel_20260726\shard_plan.json",
    [string]$Out = "audits\legfix5\identifier_probe_fast_20260726",
    [string]$Endpoint = "http://127.0.0.1:9222",
    [ValidateRange(1, 6)]
    [int]$Workers = 6
)

$ErrorActionPreference = "Stop"
$workspace = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $workspace
$env:NODE_PATH = "C:\Users\pgoff\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\node_modules"

& node "fec\collect\collect_congress_identifier_fast.mjs" `
    --plan $Plan `
    --out $Out `
    --endpoint $Endpoint `
    --workers $Workers `
    --resume

if ($LASTEXITCODE -ne 0) {
    throw "Strict identifier fast collector failed with exit code $LASTEXITCODE"
}
