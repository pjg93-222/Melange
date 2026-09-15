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
function Get-MentatCodeTreeHash([string]$Folder) {
  # Must match server.py tree_sha256(code_files()): every *.py beside server.py,
  # sorted by ordinal name, folded in as name + NUL + SHA-256 bytes + NUL.
  $names = [string[]]@(Get-ChildItem -LiteralPath $Folder -File |
    Where-Object { [IO.Path]::GetExtension($_.Name) -eq '.py' } | ForEach-Object { $_.Name })
  [Array]::Sort($names, [StringComparer]::Ordinal)
  $stream = New-Object IO.MemoryStream
  $fileHasher = [Security.Cryptography.SHA256]::Create()
  try {
    foreach ($name in $names) {
      $label = [Text.Encoding]::UTF8.GetBytes($name)
      $stream.Write($label, 0, $label.Length)
      $stream.WriteByte(0)
      $digest = $fileHasher.ComputeHash([IO.File]::ReadAllBytes((Join-Path $Folder $name)))
      $stream.Write($digest, 0, $digest.Length)
      $stream.WriteByte(0)
    }
  } finally { $fileHasher.Dispose() }
  $treeHasher = [Security.Cryptography.SHA256]::Create()
  try {
    return [BitConverter]::ToString($treeHasher.ComputeHash($stream.ToArray())).Replace('-', '').ToLowerInvariant()
  } finally { $treeHasher.Dispose(); $stream.Dispose() }
}
$codeTreeHash = Get-MentatCodeTreeHash $PSScriptRoot
$reportDirectory = $env:MENTAT_REPORT_DIRECTORY
if (-not $reportDirectory) {
  $reportConfiguration = Get-Content -Raw -LiteralPath (Join-Path $projectPath 'config\report-directory.json') | ConvertFrom-Json
  if ($reportConfiguration.schema_version -ne 1) { throw 'Unsupported report-directory configuration.' }
  $reportDirectory = [string]$reportConfiguration.directory
}
if (-not [IO.Path]::IsPathRooted($reportDirectory) -or -not (Test-Path -LiteralPath $reportDirectory -PathType Container)) {
  throw 'The authoritative report folder is unavailable. No alternate folder will be used.'
}
$reportDirectory = (Resolve-Path -LiteralPath $reportDirectory).ProviderPath
$env:MENTAT_REPORT_DIRECTORY = $reportDirectory
function Test-MentatServerIdentity($health) {
  return ($health.application -eq 'MENTAT' -and $health.project -eq $projectPath -and
    $health.data_root -eq $DataRoot -and $health.report_directory -eq $reportDirectory)
}
function Test-MentatBuildCurrent($health) {
  # A process latches its build identity at import time (server.py's
  # CODE_TREE_SHA256 / ASSET_TREE_SHA256 module constants), while
  # on_disk_*_now is recomputed fresh from disk on every health call no
  # matter how old the process is - so this same pair of comparisons is
  # accurate whichever process answers it. Current means BOTH pairs still
  # agree: an interface-only edit (JS/CSS, no *.py change) leaves
  # code_sha256 fresh but assets_sha256 stale, and that must count as stale
  # too, or a reload can never clear the banner because the frozen fields
  # never change without a restart. This mirrors the same two-pair
  # comparison server.py's own /api/restart handler already makes.
  $fields = @($health.PSObject.Properties.Name)
  foreach ($field in @('code_sha256', 'on_disk_code_sha256_now', 'assets_sha256', 'on_disk_assets_sha256_now')) {
    if ($fields -notcontains $field) { return $false }
  }
  return ($health.code_sha256 -eq $health.on_disk_code_sha256_now -and
    $health.assets_sha256 -eq $health.on_disk_assets_sha256_now)
}
function Test-CurrentMentatServer($health) {
  return ((Test-MentatServerIdentity $health) -and
    (Test-MentatBuildCurrent $health) -and $health.read_only -eq $false)
}
function Test-ReplaceableMentatServer($health) {
  # Never stop a busy server, a read-only preview, or a server that does not
  # state in its own health block that it is idle. A server too old to answer
  # with busy and the build-identity fields keeps its port and gets a
  # printed notice instead.
  if (-not (Test-MentatServerIdentity $health)) { return $false }
  $fields = @($health.PSObject.Properties.Name)
  foreach ($field in @('busy', 'code_sha256', 'on_disk_code_sha256_now', 'assets_sha256', 'on_disk_assets_sha256_now', 'pid', 'read_only')) {
    if ($fields -notcontains $field) { return $false }
  }
  if ($health.read_only -ne $false) { return $false }
  if ($health.busy -ne $false) { return $false }
  if (Test-MentatBuildCurrent $health) { return $false }
  try { return ([int]$health.pid -gt 0) } catch { return $false }
}
function Test-MentatPortListening([int]$Candidate) {
  # Windows HTTP connection retries can consume seconds on an unused port.
  # Only ask for health after a bounded loopback TCP connection succeeds.
  $client = New-Object Net.Sockets.TcpClient
  try {
    $connection = $client.ConnectAsync('127.0.0.1', $Candidate)
    return ($connection.Wait(150) -and $client.Connected)
  } catch { return $false } finally { $client.Dispose() }
}
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
  $freeCandidate = 0
  $stalePort = 0
  $staleHealth = $null
  $reclaimed = $false
  foreach ($candidate in $ports) {
    $url = "http://127.0.0.1:$candidate"
    $probe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
    $isFree = $false
    try { $probe.Start(); $isFree = $true } catch { } finally { $probe.Stop() }
    if ($isFree) {
      if (-not $freePort) { $freePort = $true; $freeCandidate = $candidate }
      continue
    }
    if (-not (Test-MentatPortListening $candidate)) { continue }
    try {
      $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 2
      if (Test-CurrentMentatServer $health) {
        $available = $true; $Port = $candidate; break
      }
      if (-not $staleHealth -and (Test-ReplaceableMentatServer $health)) {
        $stalePort = $candidate; $staleHealth = $health
      }
    } catch { }
  }
  if (-not $available -and $staleHealth) {
    # An idle console of this identity running older code gives its own port
    # back, so the window a user already has open stays the current one.
    $stalePid = 0
    try { $stalePid = [int]$staleHealth.pid } catch { $stalePid = 0 }
    $owner = $null
    if ($stalePid -gt 0) {
      try { $owner = Get-CimInstance Win32_Process -Filter "ProcessId = $stalePid" -ErrorAction Stop } catch { $owner = $null }
    }
    if ($owner -and $owner.CommandLine -and $owner.CommandLine.Contains('server.py')) {
      Write-Host ("Stopping stale MENTAT server pid " + $stalePid + " on port " + $stalePort)
      try { Stop-Process -Id $stalePid -Force -ErrorAction Stop }
      catch { Write-Host ("Could not stop pid " + $stalePid + ": " + $_.Exception.Message) }
      $stopWatch = [Diagnostics.Stopwatch]::StartNew()
      while ($stopWatch.Elapsed.TotalSeconds -lt 5 -and (Test-MentatPortListening $stalePort)) { Start-Sleep -Milliseconds 100 }
      if (Test-MentatPortListening $stalePort) {
        Write-Host ("Port " + $stalePort + " is still in use; opening another local port.")
      } else { $Port = $stalePort; $freePort = $true; $reclaimed = $true }
    } else {
      Write-Host ("Leaving the server on port " + $stalePort + " alone; no matching server.py process owns it.")
    }
  }
  if (-not $available -and -not $freePort) { throw 'No local MENTAT port is available. Close an unused local app and try again.' }
  if (-not $available) {
    if (-not $reclaimed) { $Port = $freeCandidate }
if (-not $PythonPath) {
  $PythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (-not (Test-Path -LiteralPath $PythonPath)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw 'Python 3.11 or newer is required. Install Python, then run: python -m pip install openpyxl' }
    $PythonPath = $pythonCommand.Source
  }
}
# The server imports openpyxl itself. Check availability here without loading
# the entire package in a disposable process before loading it again.
& $PythonPath -c "import sys, importlib.util; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'; assert importlib.util.find_spec('openpyxl') is not None, 'openpyxl is required'" 2>&1 | Out-Null
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
    -WindowStyle Hidden -PassThru -WorkingDirectory $reportDirectory `
    -RedirectStandardOutput (Join-Path $logDirectory "server-$Port.stdout.log") `
    -RedirectStandardError (Join-Path $logDirectory "server-$Port.stderr.log")
  $null = $process.Handle
  $startupWatch = [Diagnostics.Stopwatch]::StartNew()
  while ($startupWatch.Elapsed.TotalSeconds -lt 30) {
    if ($process.HasExited) { throw "MENTAT could not start. See $logDirectory\server-$Port.stderr.log." }
    if (Test-MentatPortListening $Port) {
      try {
        $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 1
        if (Test-CurrentMentatServer $health) { $available = $true; break }
      } catch { }
    }
    Start-Sleep -Milliseconds 100
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
