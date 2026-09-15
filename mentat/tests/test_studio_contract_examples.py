"""The worked example payloads in mentat/app/studio-contract-examples.json, sent to a
real Console over HTTP.

The two defects this suite exists to stop were both invisible to the per-endpoint unit
tests, because each side was tested against its own idea of the payload. Here the one
file the browser is written against is the one file the server is asked to accept, so a
client that starts sending something else fails here rather than on a reader's screen.

Nothing real is touched: the report directory is a temporary empty folder patched in for
the duration of construction only, and the data root is a temporary directory.
"""
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

APP = Path(__file__).resolve().parents[1] / "app"
EXAMPLES = json.loads((APP / "studio-contract-examples.json").read_text(encoding="utf-8"))

spec = importlib.util.spec_from_file_location("studio_contract_server", APP / "server.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class StudioContractExampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.data_root = Path(cls.temp.name) / 'data'
        cls.report_root = Path(cls.temp.name) / 'reports'
        cls.data_root.mkdir()
        cls.report_root.mkdir()
        with patch.object(app, 'report_directory', return_value=cls.report_root):
            cls.console = app.Console(str(cls.data_root), read_only=True)
        cls.console.read_only = False
        cls.server = app.ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
        cls.server.app = cls.console
        cls.console.port = cls.server.server_port
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.console.read_only = False

    def post(self, path, payload):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        headers = {'Host': '127.0.0.1:{}'.format(self.server.server_port),
                   'X-Mentat-Token': self.console.token, 'Content-Type': 'application/json'}
        try:
            connection.request('POST', path, body=json.dumps(payload).encode(), headers=headers)
            response = connection.getresponse()
            content = response.read()
            return response.status, json.loads(content) if content else None
        finally:
            connection.close()

    def get(self, path):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=10)
        try:
            connection.request('GET', path, headers={'Host': '127.0.0.1:{}'.format(self.server.server_port)})
            response = connection.getresponse()
            content = response.read()
            return response.status, json.loads(content) if content else None
        finally:
            connection.close()

    # ------------------------------------------------------------------ saved views

    def test_the_example_saved_view_is_accepted_exactly_as_written(self):
        status, body = self.post('/api/studio/views', EXAMPLES['views_save'])
        self.assertEqual(status, 200, body)
        stored = json.loads((self.console.root / 'studio' / 'views' / (body['id'] + '.json'))
                            .read_text(encoding='utf-8'))
        self.assertEqual(stored['source'], EXAMPLES['views_save']['source'])
        self.assertEqual(stored['sourceKey'], EXAMPLES['views_save']['sourceKey'])

        status, listed = self.get('/api/studio/views')
        self.assertEqual(status, 200)
        view = next(entry for entry in listed['views'] if entry['id'] == body['id'])
        # The picker prints a caption; it can only do that if the object carried one.
        # A saved view's caption is the dataset's, while an exported chart's is the
        # workbook's, so the fixture keeps the two apart and so does this.
        self.assertIsInstance(view['source'], dict)
        self.assertEqual(view['source']['label'], EXAMPLES['expected']['view_source_caption'])
        self.assertEqual(view['source']['reportName'], EXAMPLES['expected']['source_caption'])
        self.assertEqual(view['source']['sha256'], EXAMPLES['expected']['workbook_sha256'])

    def test_a_view_recovered_from_the_old_browser_store_is_accepted_too(self):
        """The migration path carries nothing but a caption, because the old
        browser-local store recorded nothing else - but it still has to travel as an
        object, or every recovered view is refused and the reader is told nothing."""
        payload = dict(EXAMPLES['views_save'])
        payload['name'] = 'Recovered - Crypto - 2 sheets'
        payload['source'] = EXAMPLES['producer']['view_recovered']['expected_source']
        status, body = self.post('/api/studio/views', payload)
        self.assertEqual(status, 200, body)
        stored = json.loads((self.console.root / 'studio' / 'views' / (body['id'] + '.json'))
                            .read_text(encoding='utf-8'))
        self.assertEqual(stored['source'],
                         EXAMPLES['producer']['view_recovered']['expected_source'])

    def test_a_saved_view_whose_source_is_a_caption_is_refused_with_the_reason(self):
        """The original defect: the browser sent viewSourceLabel(), a string, and every
        Save view answered 400 with no clue on screen about which field was wrong."""
        payload = dict(EXAMPLES['views_save'])
        payload['source'] = EXAMPLES['expected']['source_caption']
        status, body = self.post('/api/studio/views', payload)
        self.assertEqual(status, 400)
        self.assertIn('source', body['error'].lower())

    # --------------------------------------------------------------------- briefing

    def test_the_example_briefing_item_keeps_its_provenance_object(self):
        status, body = self.post('/api/studio/briefing/add', EXAMPLES['briefing_add'])
        self.assertEqual(status, 200, body)
        index = json.loads((self.console.root / 'studio' / 'briefing' / 'index.json')
                           .read_text(encoding='utf-8'))
        item = next(entry for entry in index['items'] if entry['id'] == body['id'])
        self.assertEqual(item['provenance'], EXAMPLES['briefing_add']['provenance'])
        self.assertEqual(item['source'], EXAMPLES['briefing_add']['source'])
        self.assertEqual(item['provenance']['sha'], EXAMPLES['expected']['workbook_sha256'])
        # The short scope chip travels with the item. Every export prints it before
        # it falls back to the full provenance scope, so a tray that loses it here
        # prints the digest string where a reader expects one line.
        self.assertEqual(item['chip'], EXAMPLES['briefing_add']['chip'])

    def test_a_briefing_item_sent_with_a_string_provenance_loses_it_entirely(self):
        """Why the browser must send objects: the server replaces anything that is not
        an object with an empty one, so a digest sent as a string never reaches a slide."""
        payload = dict(EXAMPLES['briefing_add'])
        payload['provenance'] = EXAMPLES['expected']['workbook_sha256']
        payload['source'] = EXAMPLES['expected']['source_caption']
        status, body = self.post('/api/studio/briefing/add', payload)
        self.assertEqual(status, 200, body)
        index = json.loads((self.console.root / 'studio' / 'briefing' / 'index.json')
                           .read_text(encoding='utf-8'))
        item = next(entry for entry in index['items'] if entry['id'] == body['id'])
        self.assertEqual(item['provenance'], {})
        self.assertEqual(item['source'], {})


if __name__ == '__main__':
    unittest.main()
