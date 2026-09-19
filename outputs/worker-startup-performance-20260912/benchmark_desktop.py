"""Compare the immediately preceding launcher algorithm to the revised one.

Only synthetic local health servers are launched. The old algorithm is restored
in a temporary fixture by reversing this task's exact launcher edits.
"""
import hashlib
import json
from pathlib import Path
import socket
import statistics
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'mentat/tests'))
from test_startup_performance import LAUNCHER, fixture_project, launch_fixture, stop_fixture


def replace_once(text, current, previous):
    assert text.count(current) == 1, current
    return text.replace(current, previous, 1)


after = LAUNCHER.read_text()
before = after
start = before.index('function Test-MentatPortListening(')
end = before.index("if (-not $DataRoot)", start)
before = before[:start] + before[end:]
probe = '''    $probe = New-Object Net.Sockets.TcpListener([Net.IPAddress]::Loopback, $candidate)
    try { $probe.Start(); $Port = $candidate; $freePort = $true; break } catch { } finally { $probe.Stop() }
'''
before = replace_once(before, probe + "    if (-not (Test-MentatPortListening $candidate)) { continue }\n", '')
before = replace_once(before, "    } catch { }\n  }\n  if (-not $available", "    } catch { }\n" + probe + "  }\n  if (-not $available")
before = replace_once(before, '''# The server imports openpyxl itself. Check availability here without loading
# the entire package in a disposable process before loading it again.
& $PythonPath -c "import sys, importlib.util; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'; assert importlib.util.find_spec('openpyxl') is not None, 'openpyxl is required'" 2>&1 | Out-Null''',
'''& $PythonPath -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11 or newer is required'; import openpyxl" 2>&1 | Out-Null''')
before = replace_once(before, '''  $null = $process.Handle
  $startupWatch = [Diagnostics.Stopwatch]::StartNew()
  while ($startupWatch.Elapsed.TotalSeconds -lt 30) {
    if ($process.HasExited) { throw "MENTAT could not start. See $logDirectory\\server-$Port.stderr.log." }
    if (Test-MentatPortListening $Port) {
      try {
        $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 1
        if (Test-CurrentMentatServer $health) { $available = $true; break }
      } catch { }
    }
    Start-Sleep -Milliseconds 100''', '''  for ($attempt = 0; $attempt -lt 30; $attempt++) {
    Start-Sleep -Milliseconds 300
    if ($process.HasExited) { throw "MENTAT could not start. See $logDirectory\\server-$Port.stderr.log." }
    try {
      $health = Invoke-RestMethod "$url/api/health" -TimeoutSec 1
      if (Test-CurrentMentatServer $health) { $available = $true; break }
    } catch { }''')

evidence = {'scope': 'Synthetic localhost health server imports openpyxl; no collection, real reports or network APIs.'}
for label, source in (('before', before), ('after', after)):
    samples = []
    for _ in range(3):
        with tempfile.TemporaryDirectory(prefix='Mentat desktop timing ') as directory:
            root = fixture_project(directory, source)
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1', 0))
                port = reserve.getsockname()[1]
            result = None
            try:
                result = launch_fixture(root, port)
                again = launch_fixture(root, port)
                assert result['pid'] == again['pid']
                samples.append({'cold_seconds': result['seconds'], 'reuse_seconds': again['seconds']})
            finally:
                stop_fixture(result)
    evidence[label] = {'launcher_sha256': hashlib.sha256(source.encode()).hexdigest(), 'samples': samples,
        'median_cold_seconds': statistics.median(row['cold_seconds'] for row in samples),
        'median_reuse_seconds': statistics.median(row['reuse_seconds'] for row in samples)}
    print(label, json.dumps(evidence[label]), flush=True)
Path(__file__).with_name('desktop-before-after.json').write_text(json.dumps(evidence, indent=2) + '\n', encoding='utf-8')
