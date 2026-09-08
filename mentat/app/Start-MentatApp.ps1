[CmdletBinding()]
param(
  [ValidateRange(1024,65526)][int]$Port = 8802,
  [string]$PythonPath = '',
  [string]$KeysFile = '',
  [string]$RScriptPath = '',
  [switch]$NoBrowser,
  [switch]$AppWindow,
  [string]$DataRoot = '',
  [string]$ErrorLog = ''
)
$ErrorActionPreference = 'Stop'
trap {
  if ($ErrorLog) { [IO.File]::WriteAllText($ErrorLog, $_.Exception.Message) }
  Write-Error $_ -ErrorAction Continue
  exit 1
}
$localDataSetting = Join-Path $PSScriptRoot 'desktop\local-appdata.path'
if (Test-Path -LiteralPath $localDataSetting) {
  $savedLocalData = (Get-Content -LiteralPath $localDataSetting -Raw).Trim()
  if ([IO.Path]::IsPathRooted($savedLocalData) -and (Test-Path -LiteralPath $savedLocalData)) {
    $env:LOCALAPPDATA = $savedLocalData
  }
}
$projectPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
if (-not $DataRoot) { $DataRoot = Join-Path $env:LOCALAPPDATA 'Mentat\console' }
$DataRoot = [IO.Path]::GetFullPath($DataRoot)
$hash = [Security.Cryptography.SHA256]::Create()
$identity = [BitConverter]::ToString($hash.ComputeHash([Text.Encoding]::UTF8.GetBytes($projectPath + $DataRoot))).Replace('-', '')
$hash.Dispose()
$mutex = New-Object Threading.Mutex($false, ('Local\MENTAT-Startup-' + $identity))
$ownsMutex = $false
try {
  try { $ownsMutex = $mutex.WaitOne(45000) } catch [Threading.AbandonedMutexException] { $ownsMutex = $true }
  if (-not $ownsMutex) { throw 'Another MENTAT launch is still starting. Please try again shortly.' }
  $available = $false
  $portReceipt = Join-Path $DataRoot ("desktop-$identity.port")
  $ports = @($Port..($Port + 9))
  if (Test-Path -LiteralPath $portReceipt) {
    $savedPort = 0
    if ([int]::TryParse((Get-Content -LiteralPath $portReceipt -Raw).Trim(), [ref]$savedPort) -and $savedPort -in $ports) {
      $ports = @($savedPort) + @($ports | Where-Object { $_ -ne $savedPort })
    }
  }
  $freePort = $false
  foreach ($candidate in $ports) {
    $url = "http://127.0.0.1:$candidate"
    try {
      $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 2
      if ($health.application -eq 'MENTAT' -and $health.project -eq $projectPath -and $health.data_root -eq $DataRoot) {
        $available = $true; $Port = $candidate; break
      }
    } catch { }
    $probe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
    try { $probe.Start(); $Port = $candidate; $freePort = $true; break } catch { } finally { $probe.Stop() }
  }
  if (-not $available -and -not $freePort) { throw 'No local MENTAT port is available. Close an unused local app and try again.' }
  if (-not $available) {
if (-not $PythonPath) {
  $PythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (-not (Test-Path -LiteralPath $PythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw 'Python 3.11 or newer is required. Install Python, then run: python -m pip install openpyxl' }
    $PythonPath = $pythonCommand.Source
  }
}
& $PythonPath -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'; import openpyxl" 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'MENTAT requires Python 3.11 or newer with openpyxl. Run: python -m pip install openpyxl' }
$arguments = @((Join-Path $PSScriptRoot 'server.py'), '--port', [string]$Port, '--data-root', $DataRoot)
if ($KeysFile) { $arguments += @('--keys-file', $KeysFile) }
if ($RScriptPath) { $arguments += @('--rscript', $RScriptPath) }
$url = "http://127.0.0.1:$Port"
  $logDirectory = $DataRoot
  [IO.Directory]::CreateDirectory($logDirectory) | Out-Null
  $quotedArguments = ($arguments | ForEach-Object {
    '"' + $_.Replace('"', '\"') + '"'
  }) -join ' '
  $process = Start-Process -FilePath $PythonPath -ArgumentList $quotedArguments `
    -WindowStyle Hidden -PassThru `
    -RedirectStandardOutput (Join-Path $logDirectory "server-$Port.stdout.log") `
    -RedirectStandardError (Join-Path $logDirectory "server-$Port.stderr.log")
  for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 300
    if ($process.HasExited) { throw "MENTAT could not start. See $logDirectory\server-$Port.stderr.log." }
    try {
      $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 1
      if ($health.application -eq 'MENTAT' -and $health.project -eq $projectPath -and $health.data_root -eq $DataRoot) { $available = $true; break }
    } catch { }
  }
  if (-not $available) { throw 'Mentat app has not responded yet. Check its local server log.' }
}
[IO.Directory]::CreateDirectory($DataRoot) | Out-Null
[IO.File]::WriteAllText($portReceipt, [string]$Port)
} finally {
  if ($ownsMutex) { $mutex.ReleaseMutex() }
  $mutex.Dispose()
}
if (-not $NoBrowser) {
  if ($AppWindow) {
    $browserCandidates = @(
      "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
      "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
      "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe",
      "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
      "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe")
    $browserPath = $browserCandidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
    if (-not $browserPath) { throw 'Install Microsoft Edge or Google Chrome to use the MENTAT app window.' }
    $profilePath = Join-Path $env:LOCALAPPDATA 'Mentat\browser'
    Start-Process -FilePath $browserPath -ArgumentList @("--app=$url", ('--user-data-dir="' + $profilePath + '"'), '--no-first-run', '--no-default-browser-check')
  } else { Start-Process $url }
}
Write-Host "Mentat app: $url"
