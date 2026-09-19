"""Local-only startup probes; no report scans, collectors, credentials or API calls."""
import argparse
import base64
import json
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / 'mentat'
PS = 'powershell.exe'


def powershell(code):
    result = subprocess.run([PS, '-NoLogo', '-NoProfile', '-NonInteractive',
        '-ExecutionPolicy', 'Bypass', '-EncodedCommand', base64.b64encode(code.encode('utf-16le')).decode()],
        capture_output=True, text=True, timeout=30, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr + result.stdout)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    report = {'label': args.label, 'scope': 'local synthetic process/probe timings; no collection or API calls'}
    for name, source in {
        'python_full_import': "import sys; assert sys.version_info >= (3,11); import openpyxl",
        'python_package_presence': "import sys,importlib.util; assert sys.version_info >= (3,11); assert importlib.util.find_spec('openpyxl') is not None",
    }.items():
        elapsed = []
        for _ in range(5):
            started = time.perf_counter()
            subprocess.run([sys.executable, '-c', source], check=True, capture_output=True, timeout=15)
            elapsed.append(time.perf_counter() - started)
        report[name] = {'samples_seconds': elapsed, 'median_seconds': statistics.median(elapsed)}
    with socket.socket() as reserve:
        reserve.bind(('127.0.0.1', 0))
        port = reserve.getsockname()[1]
    report['closed_port'] = powershell(f"""
$watch=[Diagnostics.Stopwatch]::StartNew()
try {{ $null=Invoke-RestMethod 'http://127.0.0.1:{port}/api/health' -TimeoutSec 2 }} catch {{}}
$http=$watch.Elapsed.TotalSeconds
$watch.Restart()
$probe=New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback,{port})
try {{$probe.Start()}} finally {{$probe.Stop()}}
[pscustomobject]@{{http_seconds=$http;bind_seconds=$watch.Elapsed.TotalSeconds}}|ConvertTo-Json -Compress
""")
    path = PROJECT / 'tools/parallel/Start-MentatResilientIndustryReports.ps1'
    with tempfile.TemporaryDirectory(prefix='Mentat process timing ') as temporary:
        literal = str(path).replace("'", "''")
        directory = temporary.replace("'", "''")
        report['managed_process'] = powershell(f"""
$ErrorActionPreference='Stop'
$text=Get-Content -LiteralPath '{literal}' -Raw
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseInput($text,[ref]$tokens,[ref]$errors)
foreach($name in @('Start-ManagedPowerShell','Wait-ManagedProcess')) {{
  $definition=@($ast.FindAll({{param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq $name}},$true))
  . ([scriptblock]::Create($definition[0].Extent.Text))
}}
$managedProcessNullExitCode=-9999
$powerShellPath=(Get-Command powershell.exe).Source
$wallWatch=[Diagnostics.Stopwatch]::StartNew()
function Update-GeneratorJobs {{}}
function Write-RunStatus {{param($Stage,$Industry,$Live)}}
function Write-RunLog {{param($Message)}}
$state=[pscustomobject]@{{industry='Synthetic'}}
$results=@(foreach($i in 1..3) {{
  $process=Start-ManagedPowerShell -Command 'Start-Sleep -Milliseconds 100; exit 37' -StdoutPath '{directory}/out'+$i -StderrPath '{directory}/err'+$i
  $watch=[Diagnostics.Stopwatch]::StartNew()
  $code=Wait-ManagedProcess $process 'test' $state
  [pscustomobject]@{{seconds=$watch.Elapsed.TotalSeconds;exit_code=$code}}
}})
$results|ConvertTo-Json -Compress
""".replace("-StdoutPath '" + directory + "/out'+$i", "-StdoutPath ('" + directory + "/out'+$i)").replace("-StderrPath '" + directory + "/err'+$i", "-StderrPath ('" + directory + "/err'+$i)"))
    output = Path(__file__).with_name(args.label + '.json')
    output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
