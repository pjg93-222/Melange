$ErrorActionPreference = 'Stop'
$promptPath = Join-Path $PSScriptRoot 'opus_followup.md'
$reviewPrompt = Get-Content -Raw -LiteralPath $promptPath
& 'C:\Users\pgoff\AppData\Roaming\npm\claude.cmd' `
    -p $reviewPrompt `
    --model opus `
    --effort max `
    --tools "" `
    --no-session-persistence
exit $LASTEXITCODE
