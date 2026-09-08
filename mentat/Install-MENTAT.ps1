[CmdletBinding()]
param([switch]$NoLaunch)
$ErrorActionPreference = 'Stop'
$desktopApp = Join-Path $PSScriptRoot 'app\desktop'
$pythonPath = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { $pythonPath = (Get-Command python -ErrorAction Stop).Source }
$effectiveLocalData = & $pythonPath -c "import os; from pathlib import Path; print((Path(os.environ['LOCALAPPDATA']) / 'Mentat').resolve().parent)"
if ($LASTEXITCODE -ne 0) { throw 'Python could not resolve the local MENTAT data directory.' }
[IO.File]::WriteAllText((Join-Path $desktopApp 'local-appdata.path'), $effectiveLocalData.Trim())
& (Join-Path $desktopApp 'Build-Desktop.ps1')
$target = Join-Path $desktopApp 'MENTAT.exe'
$shell = New-Object -ComObject WScript.Shell
foreach ($folder in @([Environment]::GetFolderPath('Desktop'), [Environment]::GetFolderPath('Programs'))) {
  $shortcut = $shell.CreateShortcut((Join-Path $folder 'MENTAT.lnk'))
  $shortcut.TargetPath = $target
  $shortcut.WorkingDirectory = $PSScriptRoot
  $shortcut.IconLocation = (Join-Path $desktopApp 'MENTAT.ico') + ',0'
  $shortcut.Description = 'MENTAT - local political-finance console'
  $shortcut.Save()
}
Write-Host 'MENTAT is ready in your Desktop and Start menu.'
if (-not $NoLaunch) { Start-Process -FilePath $target }
