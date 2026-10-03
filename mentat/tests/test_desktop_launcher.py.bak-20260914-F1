"""Windows launcher integration: occupied port, concurrent start, and reuse."""
import concurrent.futures
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import unittest
import hashlib
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen


def stop_verified_server(health, directory):
    if health and Path(health['data_root']) == Path(directory):
        # Stop-Process directly opens the verified fixture PID; taskkill's
        # process enumeration can fail in a restricted Windows test host.
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                        f"Stop-Process -Id {int(health['pid'])} -Force -ErrorAction Stop"],
                       env=os.environ.copy(), capture_output=True, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


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
                self.assertEqual(health['server_code_sha256'], hashlib.sha256((script.parent/'server.py').read_bytes()).hexdigest())
                self.assertFalse(health['read_only'])
                with urlopen(urls[0] + '/coverage-view.js', timeout=5) as response:
                    self.assertIn(b'root.MentatCoverage = api', response.read())
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
                stop_verified_server(health, directory)

    def test_old_and_read_only_servers_are_not_reused_from_another_working_directory(self):
        script=Path(__file__).resolve().parents[1]/'app/Start-MentatApp.ps1'
        project=script.parent.parent
        report_directory=json.loads((project/'config/report-directory.json').read_text())['directory']
        current_hash=hashlib.sha256((script.parent/'server.py').read_bytes()).hexdigest()
        for version in ({}, {'server_code_sha256':'old-build','read_only':False},
                        {'server_code_sha256':current_hash,'read_only':True}):
            with self.subTest(version=version), tempfile.TemporaryDirectory(prefix='MENTAT old server ') as directory:
                old_health=dict(application='MENTAT',project=str(project),data_root=directory,
                    resolved_data_root=directory,report_directory=report_directory,**version)
                class OldServer(BaseHTTPRequestHandler):
                    def log_message(self,*args):pass
                    def do_GET(self):
                        body=json.dumps(old_health).encode() if self.path=='/api/health' else b'not found'
                        self.send_response(200 if self.path=='/api/health' else 404)
                        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)))
                        self.end_headers();self.wfile.write(body)
                server=ThreadingHTTPServer(('127.0.0.1',0),OldServer)
                worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
                health=None
                try:
                    with tempfile.TemporaryFile(mode='w+',encoding='utf-8') as output:
                        result=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(script),
                            '-NoBrowser','-Port',str(server.server_port),'-DataRoot',directory],
                            cwd=directory,stdout=output,stderr=output,timeout=70)
                        output.seek(0);text=output.read()
                    self.assertEqual(result.returncode,0,text)
                    url=text.strip().splitlines()[-1].split('Mentat app: ')[-1]
                    self.assertNotEqual(url,f'http://127.0.0.1:{server.server_port}')
                    with urlopen(url+'/api/health',timeout=5) as response:health=json.load(response)
                    self.assertEqual(health['server_code_sha256'],current_hash)
                    self.assertEqual(Path(health['data_root']),Path(directory))
                    self.assertFalse(health['read_only'])
                    with urlopen(url+'/coverage-view.js',timeout=5) as response:self.assertEqual(response.status,200)
                    with urlopen(f'http://127.0.0.1:{server.server_port}/api/health',timeout=5) as response:
                        self.assertEqual(json.load(response),old_health,'An older server may still own running work')
                finally:
                    stop_verified_server(health, directory)
                    server.shutdown();server.server_close();worker.join()


if __name__ == '__main__':
    unittest.main()
