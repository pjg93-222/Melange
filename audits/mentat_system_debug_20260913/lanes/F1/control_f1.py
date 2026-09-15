"""Local HTTP contracts for contribution analytics with stubbed source services.

Does not instantiate Console, index data, read real reports, run collectors, or
fetch geography. All service calls are replaced with explicit in-memory stubs.
"""
import http.client
import importlib.util
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import importlib.machinery
APP = Path(r"C:\Users\pgoff\Mentat\mentat\app")
spec = importlib.util.spec_from_loader("control_f1_server",
    importlib.machinery.SourceFileLoader("control_f1_server", str(APP / "server.py.bak-20260914-F1")))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class ContributionHTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.report_root = Path(cls.temp.name)
        cls.console = SimpleNamespace(token="contribution-test-token", read_only=True, report_directory=cls.report_root)
        cls.server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        cls.server.app = cls.console
        cls.worker = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join(timeout=5)
        cls.temp.cleanup()

    def setUp(self):
        self.console.read_only = True
        guard = patch.object(app.contribution_workbook_guard, 'verify_sources', return_value=[])
        self.guard = guard.start()
        self.addCleanup(guard.stop)
        self.patches = [patch.object(app.contribution_data, "catalog", return_value={"datasets": [{"id": "Banking", "available": True}]}),
                        patch.object(app.contribution_query, "query", return_value={"rows": [{"zip5": "02134", "amount": 12300}], "totals": {"amount": 12300}}),
                        patch.object(app.contribution_query, "records", return_value={"rows": [{"source_id": "fixture-1", "zip5": "02134"}]}),
                        patch.object(app.contribution_geo, "geo_catalog", return_value={"congresses": ["119", "120"]}),
                        patch.object(app.contribution_geo, "geography", return_value={"points": [{"zip5": "02134"}], "layers": {}, "coverage": {}})]
        self.catalog, self.query, self.records, self.geo_catalog, self.geo = [p.start() for p in self.patches]
        for p in self.patches: self.addCleanup(p.stop)

    def request(self, path, *, method="GET", data=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=8)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        default_headers = {"Host": f"127.0.0.1:{self.server.server_port}"}
        if method == "POST": default_headers.update({"X-Mentat-Token": self.console.token, "Content-Type": "application/json"})
        default_headers.update(headers or {})
        try:
            connection.request(method, path, body=body, headers=default_headers)
            response = connection.getresponse()
            content = response.read()
            parsed = json.loads(content) if response.getheader("Content-Type") == "application/json" else content
            return response.status, dict(response.getheaders()), parsed
        finally:
            connection.close()

    def test_local_session_returns_token_and_read_only_state(self):
        status, headers, body = self.request("/api/contributions/session")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"token": self.console.token, "read_only": True})
        self.assertEqual(headers["Cache-Control"], "no-store")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
        self.query.assert_not_called()

    def test_catalog_routes_use_configured_report_directory(self):
        status, _, body = self.request("/api/contributions/catalog?directory=C:/arbitrary")
        self.assertEqual(status, 200)
        self.assertEqual(body["datasets"][0]["id"], "Banking")
        self.catalog.assert_called_once_with(self.report_root)
        self.guard.assert_called_once_with(self.report_root, strict=False)
        status, _, body = self.request("/api/contributions/geography/catalog")
        self.assertEqual((status, body["congresses"]), (200, ["119", "120"]))
        self.geo_catalog.assert_called_once_with()

    def test_workbook_mismatch_disables_only_its_dataset_and_blocks_queries(self):
        self.catalog.return_value = {'datasets': [{'id':'Banking','available':True}, {'id':'Crypto','available':True}]}
        self.guard.return_value = [{'dataset':'Banking','matched':False,'error':'Published total changed.'}]
        status, _, body = self.request('/api/contributions/catalog')
        self.assertEqual(status,200)
        self.assertFalse(body['datasets'][0]['available'])
        self.assertTrue(body['datasets'][1]['available'])
        self.guard.side_effect = ValueError('Published total changed.')
        status, _, body = self.request('/api/contributions/query',method='POST',data={'dataset':'Banking'})
        self.assertEqual(status,400)
        self.assertIn('Published total changed',body['error'])
        self.query.assert_not_called()

    def test_query_is_bound_to_the_workbook_version_that_passed_the_guard(self):
        self.guard.return_value = [{'dataset':'Banking','matched':True,'workbook_sha256':'checked-version'}]
        self.query.return_value = {'status':'ready','rows':[],'provenance':{'workbook_sha256':'changed-version'}}
        status, _, body = self.request('/api/contributions/query',method='POST',data={'dataset':'Banking'})
        self.assertEqual(status,400)
        self.assertIn('source changed',body['error'])

    def test_same_workbook_cannot_switch_database_after_verification(self):
        self.guard.return_value = [{'dataset':'Banking','matched':True,'workbook_sha256':'book',
                                    'database_sha256':'checked-db'}]
        self.query.return_value = {'status':'ready','rows':[],
                                   'provenance':{'workbook_sha256':'book','database_sha256':'changed-db'}}
        status, _, body = self.request('/api/contributions/query',method='POST',data={'dataset':'Banking'})
        self.assertEqual(status,400)
        self.assertIn('source changed',body['error'])

    def test_preparation_response_keeps_verified_source_identity(self):
        self.guard.return_value = [{'dataset':'Banking','matched':True,'workbook_sha256':'book',
                                    'database_sha256':'db','source_financial_universe_verified':True,
                                    'source_proof_token':'proof'}]
        self.query.return_value = {'status':'preparing','retry_after_ms':1500,
                                   'provenance':{'workbook_sha256':'book','database_sha256':'db'}}
        status, _, body = self.request('/api/contributions/query',method='POST',data={'dataset':'Banking'})
        self.assertEqual(status,200)
        self.assertEqual(body['status'],'preparing')
        self.assertEqual(body['provenance']['source_proof_token'],'proof')
        self.assertTrue(body['provenance']['source_financial_universe_verified'])

    def test_read_only_mode_allows_only_analytical_post_routes(self):
        request = {"dataset": "Banking", "basis": "original_observed", "dimensions": ["zip5"], "measures": ["amount"]}
        status, _, body = self.request("/api/contributions/query", method="POST", data=request)
        self.assertEqual(status, 200)
        self.assertEqual(body["totals"]["amount"], 12300)
        self.query.assert_called_once_with(self.report_root, request)
        status, _, _ = self.request("/api/contributions/records", method="POST", data=request)
        self.assertEqual(status, 200)
        self.records.assert_called_once_with(self.report_root, request)
        geometry = {"zips": ["02134"], "layers": ["states", "districts", "zip_areas"], "congress": "119", "bbox": [-72, 41, -70, 43]}
        status, _, _ = self.request("/api/contributions/geography", method="POST", data=geometry)
        self.assertEqual(status, 200)
        self.geo.assert_called_once_with(geometry)
        for path in ("/api/upload", "/api/start", "/api/keys", "/api/evidence-collect", "/api/run-archive"):
            with self.subTest(path=path):
                status, _, body = self.request(path, method="POST", data={})
                self.assertEqual(status, 403)
                self.assertIn("read-only", body["error"])

    def test_missing_or_wrong_tokens_never_invoke_analytics(self):
        for token in ("", "wrong-token"):
            for route in ("query", "records", "geography"):
                with self.subTest(token=token, route=route):
                    status, _, _ = self.request("/api/contributions/" + route, method="POST", data={}, headers={"X-Mentat-Token": token})
                    self.assertEqual(status, 403)
        self.query.assert_not_called(); self.records.assert_not_called(); self.geo.assert_not_called()

    def test_bad_hosts_and_foreign_origins_are_rejected(self):
        for host in ("evil.example", "127.0.0.1:1", "localhost.evil.example:" + str(self.server.server_port)):
            with self.subTest(host=host):
                self.assertEqual(self.request("/api/contributions/session", headers={"Host": host})[0], 403)
                self.assertEqual(self.request("/api/contributions/query", method="POST", data={}, headers={"Host": host})[0], 403)
        for origin in ("null", "https://evil.example", "http://127.0.0.1:1", f"https://localhost:{self.server.server_port}"):
            with self.subTest(origin=origin):
                self.assertEqual(self.request("/api/contributions/query", method="POST", data={}, headers={"Origin": origin})[0], 403)
        self.query.assert_not_called()

    def test_both_local_origins_can_query(self):
        for host in ("127.0.0.1", "localhost"):
            status, _, _ = self.request("/api/contributions/query", method="POST", data={}, headers={"Host": f"{host}:{self.server.server_port}", "Origin": f"http://{host}:{self.server.server_port}"})
            self.assertEqual(status, 200)
        self.assertEqual(self.query.call_count, 2)

    def test_invalid_json_shape_length_and_unknown_routes_fail(self):
        for raw in (b"[]", b"null", b"false", b"{broken", b""):
            with self.subTest(raw=raw):
                self.assertEqual(self.request("/api/contributions/query", method="POST", raw=raw)[0], 400)
        status, _, _ = self.request("/api/contributions/query", method="POST", raw=b"{}", headers={"Content-Length": "7000001"})
        self.assertEqual(status, 400)
        self.assertEqual(self.request("/api/contributions/query")[0], 404)
        self.assertEqual(self.request("/api/contributions/unknown")[0], 404)
        self.query.assert_not_called()

    def test_service_validation_failure_is_useful_json(self):
        for error in (ValueError("Invalid dimension"), RuntimeError("Source fingerprint changed"), OSError("Source unavailable")):
            with self.subTest(error=error):
                self.query.side_effect = error
                status, _, body = self.request("/api/contributions/query", method="POST", data={})
                self.assertEqual(status, 400)
                self.assertEqual(body["error"], str(error))
        self.geo.side_effect = app.contribution_geo.GeographyError("Congress must be 119 or 120.")
        status, _, body = self.request("/api/contributions/geography", method="POST", data={"congress": "121"})
        self.assertEqual((status, body["error"]), (400, "Congress must be 119 or 120."))

    def test_assets_are_same_origin_and_accessible_in_read_only_mode(self):
        for route, mime in (("/contribution-studio", "text/html; charset=utf-8"), ("/contribution-studio.js", "text/javascript"),
                            ("/contribution-studio.css", "text/css"), ("/contribution-map.js", "text/javascript"),
                            ("/contribution-plot.js", "text/javascript"), ("/chart-export.js", "text/javascript")):
            with self.subTest(route=route):
                status, headers, body = self.request(route)
                self.assertEqual(status, 200)
                self.assertEqual(headers["Content-Type"], mime)
                self.assertGreater(len(body), 50)
                self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(self.request("/../server.py")[0], 404)


if __name__ == "__main__": unittest.main()
