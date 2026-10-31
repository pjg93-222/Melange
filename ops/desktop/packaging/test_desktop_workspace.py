import contextlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import tempfile
import threading
from types import SimpleNamespace
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from desktop_backend import guarded_handler, TOKEN_HEADER
from desktop_workspace import DesktopWorkspace, WORKSPACE_PATH, empty_dashboard
from melange_bootstrap import initialize_workspace


class WorkspaceTests(unittest.TestCase):
    def test_only_exact_program_template_is_empty_and_every_input_is_preserved(self):
        with tempfile.TemporaryDirectory(prefix='Jos\u00e9 workspace ') as temporary:
            root = Path(temporary)
            initialize_workspace(root)
            original = (root / 'Moneyball.html').read_bytes()
            self.assertTrue(empty_dashboard(root))
            (root / 'notes.txt').write_bytes(b'private local notes')
            page, policy = DesktopWorkspace('melange', root).page(SimpleNamespace(public_data=None))
            self.assertIn(b'Application workspace not connected', page)
            self.assertIn(b'Not available yet', page)
            self.assertEqual((root / 'Moneyball.html').read_bytes(), original)
            self.assertEqual((root / 'notes.txt').read_bytes(), b'private local notes')
            self.assertNotIn(temporary.encode(), page)
            self.assertIn("default-src 'none'", policy)
            nonce = re.search(rb'<script nonce="([\w-]+)">', page).group(1).decode()
            self.assertIn("script-src 'nonce-" + nonce + "'", policy)
            (root / 'Moneyball.html').write_bytes(original + b'<!-- user revision -->')
            self.assertFalse(empty_dashboard(root))
            self.assertFalse(DesktopWorkspace('melange', root).replaces_empty_root())

    def test_reader_unavailability_and_partial_coverage_never_claim_full_application(self):
        class Reader:
            def __init__(self, value):
                self.value = value
            def catalogue(self):
                if isinstance(self.value, Exception):
                    raise self.value
                return self.value
        with tempfile.TemporaryDirectory() as temporary:
            for app in ('melange', 'mentat'):
                workspace = DesktopWorkspace(app, temporary)
                available = ({'available': True, 'kind': 'mentat.public-fec-tables.v1'} if app == 'mentat'
                             else {'status': 'available', 'coverage': {'fullApplication': False}})
                for catalogue, ready in ((available, True),
                                         ({'status': 'available', 'coverage': {'fullApplication': True}}, False),
                                         ({'status': 'available'}, False),
                                         (ValueError('private C:/data/secret/path'), False)):
                    container = SimpleNamespace(public_data=Reader(catalogue))
                    server = SimpleNamespace(app=container) if app == 'mentat' else container
                    page, _ = workspace.page(server)
                    self.assertEqual(b'Ready to browse' in page, ready)
                    self.assertIn(b'do not replace the complete analysis workspace', page)
                    self.assertNotIn(b'secret/path', page)
                    self.assertNotIn(b'synced', page)
                    self.assertNotIn(b'fully operational', page)

    @contextlib.contextmanager
    def server(self, app, root):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'existing application route')
            def log_message(self, *args):
                pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), guarded_handler(
            Handler, 'x' * 32, app, workspace=DesktopWorkspace(app, root)))
        server.app = SimpleNamespace(public_data=None)
        server.public_data = None
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            yield 'http://127.0.0.1:' + str(server.server_port)
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_trusted_workspace_route_requires_token_for_every_verb_and_accepts_no_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            initialize_workspace(root)
            before = (root / 'Moneyball.html').read_bytes()
            with self.server('melange', root) as origin:
                for verb in ('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS'):
                    with self.assertRaises(HTTPError) as error:
                        urlopen(Request(origin + WORKSPACE_PATH, method=verb))
                    self.assertEqual(error.exception.code, 403)
                headers = {TOKEN_HEADER: 'x' * 32}
                with urlopen(Request(origin + WORKSPACE_PATH + '?dataRoot=C:/untrusted', headers=headers)) as response:
                    body = response.read()
                    self.assertIn(b'openWorkspaceSettings()', body)
                    self.assertNotIn(b'C:/untrusted', body)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    self.assertEqual(response.headers['Referrer-Policy'], 'no-referrer')
                    self.assertIn("frame-ancestors 'none'", response.headers['Content-Security-Policy'])
                with self.assertRaises(HTTPError) as error:
                    urlopen(Request(origin + WORKSPACE_PATH, headers=headers, method='POST'))
                self.assertEqual(error.exception.code, 405)
                self.assertEqual(urlopen(Request(origin + '/', headers=headers)).read(), b'existing application route')
                (root / 'Moneyball.html').write_bytes(b'user-owned dashboard')
                self.assertEqual(urlopen(Request(origin + '/', headers=headers)).read(), b'existing application route')
            self.assertEqual((root / 'Moneyball.html').read_bytes(), b'user-owned dashboard')
            self.assertNotEqual(before, b'user-owned dashboard')

    def test_mentat_console_is_retained_and_model_selections_do_not_claim_verified_inputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            models = root / 'app-data'
            models.mkdir()
            for name in ('giving-models-current.json', 'pac-giving-current.json'):
                (models / name).write_text('{}', encoding='utf-8')
            with self.server('mentat', root) as origin:
                headers = {TOKEN_HEADER: 'x' * 32}
                self.assertEqual(urlopen(Request(origin + '/', headers=headers)).read(), b'existing application route')
                page = urlopen(Request(origin + WORKSPACE_PATH, headers=headers)).read()
                self.assertIn(b'Local model selections found', page)
                self.assertIn(b'Inputs are verified when opened', page)
                self.assertIn(b'anchors, and report workbooks', page)
                self.assertNotIn(b'Ready to browse', page)


if __name__ == '__main__':
    unittest.main()
