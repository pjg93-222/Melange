[CmdletBinding()]
param(
  [int]$Port = 8802,
  [string]$PythonPath = '',
  [string]$KeysFile = '',
  [string]$RScriptPath = '',
  [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
if (-not $PythonPath) {
  $PythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (-not (Test-Path -LiteralPath $PythonPath)) {
    $PythonPath = (Get-Command python -ErrorAction Stop).Source
  }
}
$arguments = @((Join-Path $PSScriptRoot 'server.py'), '--port', [string]$Port)
if ($KeysFile) { $arguments += @('--keys-file', $KeysFile) }
if ($RScriptPath) { $arguments += @('--rscript', $RScriptPath) }
$url = "http://127.0.0.1:$Port"
$available = $false
try {
  $session = Invoke-RestMethod "$url/api/session" -TimeoutSec 2
  $available = [bool]$session.token
} catch { }
if (-not $available) {
  $logDirectory = Join-Path $env:LOCALAPPDATA 'Mentat\console'
  [IO.Directory]::CreateDirectory($logDirectory) | Out-Null
  $quotedArguments = ($arguments | ForEach-Object {
    '"' + $_.Replace('"', '\"') + '"'
  }) -join ' '
  $process = Start-Process -FilePath $PythonPath -ArgumentList $quotedArguments `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logDirectory 'server.stdout.log') `
    -RedirectStandardError (Join-Path $logDirectory 'server.stderr.log')
  for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 300
    if ($process.HasExited) { throw 'Mentat app could not start. See %LOCALAPPDATA%\Mentat\console\server.stderr.log.' }
    try {
      $session = Invoke-RestMethod "$url/api/session" -TimeoutSec 1
      if ($session.token) { $available = $true; break }
    } catch { }
  }
  if (-not $available) { throw 'Mentat app has not responded yet. Check its local server log.' }
}
if (-not $NoBrowser) { Start-Process $url }
Write-Host "Mentat app: $url"
