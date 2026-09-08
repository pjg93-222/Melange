"""Windows launcher integration: occupied port, concurrent start, and reuse."""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
from urllib.request import urlopen


@unittest.skipUnless(os.name == 'nt', 'Windows desktop launcher')
class DesktopLauncherTests(unittest.TestCase):
    def test_conflict_concurrent_start_and_reuse(self):
        script = Path(__file__).resolve().parents[1] / 'app/Start-MentatApp.ps1'
        with tempfile.TemporaryDirectory(prefix='MENTAT desktop ') as directory, socket.socket() as occupied:
            occupied.bind(('127.0.0.1', 0))
            # Bound without listening: the port is unavailable without accepting HTTP.
            base = occupied.getsockname()[1]
            command = ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                       '-File', str(script), '-NoBrowser', '-Port', str(base),
                       '-DataRoot', directory]
            health = None
            def launch():
                # Detached Windows children can inherit pipe handles. Disk-backed
                # diagnostics let the launcher finish independently of its server.
                with tempfile.TemporaryFile(mode='w+', encoding='utf-8') as output:
                    result = subprocess.run(command, stdout=output, stderr=output, timeout=70)
                    output.seek(0)
                    return result.returncode, output.read()
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda _: launch(), range(2)))
                for code, output in results:
                    self.assertEqual(code, 0, output)
                urls = [output.strip().splitlines()[-1].split('Mentat app: ')[-1] for _, output in results]
                self.assertEqual(urls[0], urls[1], 'Concurrent launches must reuse one server')
                self.assertNotEqual(urls[0], f'http://127.0.0.1:{base}')
                with urlopen(urls[0] + '/api/health', timeout=5) as response:
                    health = json.load(response)
                self.assertEqual(health['application'], 'MENTAT')
                self.assertEqual(Path(health['project']), script.parent.parent)
                self.assertEqual(Path(health['data_root']), Path(directory))
                # Freeing the original port must not change this app's origin.
                occupied.close()
                code, output = launch()
                self.assertEqual(code, 0, output)
                with urlopen(urls[0] + '/api/health', timeout=5) as response:
                    self.assertEqual(json.load(response)['pid'], health['pid'])
                with urlopen(urls[0] + '/mentat-icon.svg', timeout=5) as response:
                    self.assertIn(b'#342649', response.read())
            finally:
                # Only terminate the isolated server whose identity/root we verified.
                if health and Path(health['data_root']) == Path(directory):
                    subprocess.run(['taskkill', '/PID', str(health['pid']), '/F'],
                                   capture_output=True, check=True)


if __name__ == '__main__':
    unittest.main()
