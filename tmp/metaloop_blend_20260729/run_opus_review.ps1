$ErrorActionPreference = 'Stop'
$promptPath = Join-Path $PSScriptRoot 'opus_review_prompt_compact.md'
$reviewPrompt = Get-Content -Raw -LiteralPath $promptPath
& 'C:\Users\pgoff\AppData\Roaming\npm\claude.cmd' `
    -p $reviewPrompt `
    --model opus `
    --effort max `
    --tools "" `
    --no-session-persistence
exit $LASTEXITCODE
