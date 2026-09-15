/* F1 step 2 - Start-MentatApp.ps1: hash the same app/*.py set the server does,
   and replace an idle stale server on its own port instead of opening a new
   one. Busy, read-only and foreign servers are never touched. File is pure LF. */
'use strict';

const treeHash = `$projectPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
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
$codeTreeHash = Get-MentatCodeTreeHash $PSScriptRoot`;

const identityTests = `function Test-MentatServerIdentity($health) {
  return ($health.application -eq 'MENTAT' -and $health.project -eq $projectPath -and
    $health.data_root -eq $DataRoot -and $health.report_directory -eq $reportDirectory)
}
function Test-CurrentMentatServer($health) {
  return ((Test-MentatServerIdentity $health) -and
    $health.code_sha256 -eq $codeTreeHash -and $health.read_only -eq $false)
}
function Test-ReplaceableMentatServer($health) {
  # Never stop a busy server, a read-only preview, or a server that does not
  # state in its own health block that it is idle. A server too old to answer
  # with busy and code_sha256 keeps its port and gets a printed notice instead.
  if (-not (Test-MentatServerIdentity $health)) { return $false }
  $fields = @($health.PSObject.Properties.Name)
  foreach ($field in @('busy', 'code_sha256', 'pid', 'read_only')) {
    if ($fields -notcontains $field) { return $false }
  }
  if ($health.read_only -ne $false) { return $false }
  if ($health.busy -ne $false) { return $false }
  if ($health.code_sha256 -eq $codeTreeHash) { return $false }
  try { return ([int]$health.pid -gt 0) } catch { return $false }
}`;

const portLoop = `  $freePort = $false
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
    if (-not $reclaimed) { $Port = $freeCandidate }`;

module.exports = {
  root: 'C:\\Users\\pgoff\\Mentat\\mentat\\app',
  eol: 'lf',
  files: [{
    path: 'Start-MentatApp.ps1',
    eol: 'lf',
    edits: [
      {find: `$projectPath = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$serverHasher = [Security.Cryptography.SHA256]::Create()
try {
  $serverCodeHash = [BitConverter]::ToString($serverHasher.ComputeHash(
    [IO.File]::ReadAllBytes((Join-Path $PSScriptRoot 'server.py')))).Replace('-', '').ToLowerInvariant()
} finally { $serverHasher.Dispose() }`,
       replace: treeHash},
      {find: `function Test-CurrentMentatServer($health) {
  return ($health.application -eq 'MENTAT' -and $health.project -eq $projectPath -and
    $health.data_root -eq $DataRoot -and $health.report_directory -eq $reportDirectory -and
    $health.server_code_sha256 -eq $serverCodeHash -and $health.read_only -eq $false)
}`,
       replace: identityTests},
      {find: `  $freePort = $false
  foreach ($candidate in $ports) {
    $url = "http://127.0.0.1:$candidate"
    $probe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
    try { $probe.Start(); $Port = $candidate; $freePort = $true; break } catch { } finally { $probe.Stop() }
    if (-not (Test-MentatPortListening $candidate)) { continue }
    try {
      $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 2
      if (Test-CurrentMentatServer $health) {
        $available = $true; $Port = $candidate; break
      }
    } catch { }
  }
  if (-not $available -and -not $freePort) { throw 'No local MENTAT port is available. Close an unused local app and try again.' }
  if (-not $available) {`,
       replace: portLoop}
    ]
  }]
};
