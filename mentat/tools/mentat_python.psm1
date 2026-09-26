# The one place a Mentat launcher chooses its Python interpreter.
#
# Order:
#   1. an explicit path the caller was given (-PythonPath, or MENTAT_PYTHON_PATH where
#      the caller already honours it);
#   2. Mentat's own venv, %LOCALAPPDATA%\Mentat\venv, when its python.exe exists and the
#      base Python named in its pyvenv.cfg is still installed;
#   3. the Codex app's runtime Python. The Codex app resets that environment: on
#      2026-09-25 a reset removed jinja2, geopy and geopandas, and "/" fell back to the
#      golden index.html;
#   4. python on PATH.
# The venv is built from mentat\requirements-console.txt.
#
# Nothing here prints. Each caller reports the choice where its own output is read, so
# a script whose stdout is parsed (a -PlanOnly plan) stays clean.

function Get-MentatVenvPath {
  $localData = $env:LOCALAPPDATA
  if ([string]::IsNullOrWhiteSpace($localData)) {
    $localData = [Environment]::GetFolderPath('LocalApplicationData')
  }
  return (Join-Path $localData 'Mentat\venv')
}

function Get-MentatVenvState([string]$VenvPath) {
  # A venv's Scripts\python.exe is a small launcher that starts the base interpreter
  # named by `home` in pyvenv.cfg. If that base is gone the venv cannot start at all.
  if (-not (Test-Path -LiteralPath (Join-Path $VenvPath 'Scripts\python.exe') -PathType Leaf)) { return 'missing' }
  $config = Join-Path $VenvPath 'pyvenv.cfg'
  if (-not (Test-Path -LiteralPath $config -PathType Leaf)) { return 'pyvenv.cfg is missing' }
  $homeLines = @(Get-Content -LiteralPath $config | Where-Object { $_ -match '^\s*home\s*=' })
  if ($homeLines.Count -eq 0) { return 'pyvenv.cfg names no base Python' }
  $baseFolder = ($homeLines[0] -split '=', 2)[1].Trim()
  if (-not (Test-Path -LiteralPath (Join-Path $baseFolder 'python.exe') -PathType Leaf)) {
    return ('its base Python is gone from ' + $baseFolder)
  }
  return 'ok'
}

function Resolve-MentatPython {
  # Returns @{ Path; Source ('explicit' | 'venv' | 'codex-runtime' | 'PATH'); Venv; Warning },
  # or $null when no interpreter exists at all (the caller throws its own message).
  # Warning is set whenever the choice fell back past the venv.
  [CmdletBinding()]
  param([string]$ExplicitPath = '')
  $venv = Get-MentatVenvPath
  $venvPython = Join-Path $venv 'Scripts\python.exe'
  if (-not [string]::IsNullOrWhiteSpace($ExplicitPath)) {
    return [pscustomobject]@{ Path = $ExplicitPath; Source = 'explicit'; Venv = $venv; Warning = $null }
  }
  $state = Get-MentatVenvState $venv
  if ($state -eq 'ok') {
    return [pscustomobject]@{ Path = $venvPython; Source = 'venv'; Venv = $venv; Warning = $null }
  }
  $requirements = Join-Path (Split-Path -Parent $PSScriptRoot) 'requirements-console.txt'
  $reason = if ($state -eq 'missing') { "Mentat's venv was not found at $venv" } else { "Mentat's venv at $venv cannot start: $state" }
  $advice = 'To restore it: python -m venv "' + $venv + '" (Python 3.12), then "' + $venvPython +
    '" -m pip install --only-binary=:all: -r "' + $requirements + '".'
  $codex = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
  if (Test-Path -LiteralPath $codex -PathType Leaf) {
    return [pscustomobject]@{ Path = $codex; Source = 'codex-runtime'; Venv = $venv
      Warning = ($reason + '; using the Codex app runtime Python, which the Codex app resets (packages installed there can disappear). ' + $advice) }
  }
  $onPath = @(Get-Command python -CommandType Application -ErrorAction SilentlyContinue)
  if ($onPath.Count -gt 0) {
    return [pscustomobject]@{ Path = $onPath[0].Source; Source = 'PATH'; Venv = $venv
      Warning = ($reason + ' and the Codex app runtime Python is absent; using python on PATH. ' + $advice) }
  }
  return $null
}

Export-ModuleMember -Function Resolve-MentatPython, Get-MentatVenvPath
