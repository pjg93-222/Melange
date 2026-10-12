"""Hosted, read-only, Access-gated Mentat console (Lane M).

Default mode must be what it always was: a 127.0.0.1 bind, the loopback Host and Origin allowlists, the
per-process session token, no new routes, no new headers. Enforced mode (Cloudflare Access) must be read-only,
must refuse everything that exports, downloads, uploads or reads a path, and must never hand out the console's
own token. MENTAT_STATE_WRITE_ROOT must move every cache the console writes; receipt paths written on Windows
must resolve on Linux.

Nothing here touches the real data root, the real state folder or a real port: servers listen on 127.0.0.1:0
over stand-in consoles in temp dirs, and the start-up tests run server.py on an OS-chosen port with every
path in a temp dir. RSA keys are generated at run time with `cryptography` and signed in memory; only the
public JWKS is written (to a temp dir). The enforced-mode tests skip without `cryptography`.
"""
import base64
import contextlib
import hashlib
import http.client
import inspect
import io
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False

from test_contribution_http import app

import contribution_data
import contribution_source_guard
import evidence_csv
import receipt_path as receipt_paths
import source_memo

gate = app.access_gate
needs_crypto = unittest.skipUnless(HAVE_CRYPTO, 'cryptography is not installed')

AUD = 'mentat-test-aud'
ISS = 'https://example-team.cloudflareaccess.com'
HOST = 'mentat.example.test'
EMAIL = 'analyst@example.test'
REAL_TOKEN = 'real-console-token-never-shown'
ANALYTICAL = {'/api/contributions/query', '/api/contributions/records', '/api/contributions/geography',
              '/api/insights/query', '/api/insights/records', '/api/forecast/project'}
SERVER_PY = Path(app.__file__).resolve()
# deploy/access-gate: fec/access_gate.py. The three apps carry byte-identical copies; change one, recopy, update this.
GATE_SHA256 = 'dc7ef05085044601884ce037f21c1b44d774e7dffba3a0276a3ea5423227e58d'


def b64u(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode('ascii')


class Idp:
    """A throw-away Access: one RSA key, its JWKS file in `directory`, and a way to sign tokens."""

    def __init__(self, directory):
        self.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        numbers = self.key.public_key().public_numbers()
        big = lambda n: n.to_bytes((n.bit_length() + 7) // 8, 'big')
        self.jwks = Path(directory) / 'certs.json'
        self.jwks.write_text(json.dumps({'keys': [{'kty': 'RSA', 'kid': 'kid-a', 'use': 'sig', 'alg': 'RS256',
                                                   'n': b64u(big(numbers.n)), 'e': b64u(big(numbers.e))}]}))

    def token(self, **over):
        now = int(time.time())
        claims = {'aud': [AUD], 'iss': ISS, 'exp': now + 3600, 'nbf': now - 10, 'email': EMAIL, **over}
        encode = lambda value: b64u(json.dumps(value).encode())
        signing = encode({'alg': 'RS256', 'kid': 'kid-a', 'typ': 'JWT'}) + '.' + encode(claims)
        signature = self.key.sign(signing.encode('ascii'), padding.PKCS1v15(), hashes.SHA256())
        return signing + '.' + b64u(signature)

    def env(self, **over):
        return {'ACCESS_ENFORCE': '1', 'ALLOWED_HOSTS': HOST, 'ACCESS_AUD': AUD, 'ACCESS_ISSUER': ISS,
                'ACCESS_JWKS_FILE': str(self.jwks), **over}


class Served:
    """A Handler class on 127.0.0.1:0 in a thread, over a stand-in console."""

    def __init__(self, handler, console):
        self.server = app.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.server.app = console
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.stderr = ''

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def request(self, path, *, method='GET', data=None, headers=None, raw=None):
        """(status, headers, body); body is parsed JSON, or bytes. self.stderr is what the server wrote."""
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        sent = {'Host': f'127.0.0.1:{self.port}'}
        if method == 'POST':
            sent['Content-Type'] = 'application/json'
        sent.update(headers or {})
        captured = io.StringIO()
        try:
            with contextlib.redirect_stderr(captured):
                connection.request(method, path, body=body, headers=sent)
                response = connection.getresponse()
                content = response.read()
            parsed = json.loads(content) if response.getheader('Content-Type', '').startswith('application/json') else content
            return response.status, dict(response.getheaders()), parsed
        finally:
            connection.close()
            self.stderr = captured.getvalue()


def free_port():
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


class AccessGateCopy(unittest.TestCase):
    def test_the_copy_is_the_canonical_gate_byte_for_byte(self):
        self.assertEqual(hashlib.sha256(Path(gate.__file__).read_bytes()).hexdigest(), GATE_SHA256)


class ServerPaths(unittest.TestCase):
    def test_absolute_paths_are_omitted_and_the_rest_is_kept(self):
        body = {'a': 1, 'b': 'C:\\x\\y', 'c': 'c:/x', 'd': '\\\\host\\share', 'e': '/srv/x', 'f': 'relative/x',
                'g': ['/srv/y', 'ok', {'h': '/z', 'i': 2}], 'j': {'k': 'D:\\q'}}
        self.assertEqual(app.without_server_paths(body), {'a': 1, 'f': 'relative/x', 'g': ['ok', {'i': 2}], 'j': {}})


class DefaultModeIsUnchanged(unittest.TestCase):
    """No Access environment: every local contract holds, and nothing hosted leaks in."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.console = SimpleNamespace(
            token='local-token', read_only=False, report_directory=Path(cls.temp.name),
            configured_root=cls.temp.name, root=Path(cls.temp.name),
            evidence_files=Mock(return_value={'files': []}),
            import_evidence_path=Mock(return_value={'id': 'job', 'state': 'reading'}),
            restart=Mock(return_value={'restarting': True}))

        class Listed(app.Handler):
            # ALLOWED_HOSTS is set but nothing is enforced: it must add no host and no origin.
            access_cfg = gate.AccessConfig(allowed_hosts=gate.LOOPBACK | {HOST})

        cls.plain, cls.listed = Served(app.Handler, cls.console), Served(Listed, cls.console)

    @classmethod
    def tearDownClass(cls):
        cls.plain.close()
        cls.listed.close()
        cls.temp.cleanup()

    def setUp(self):
        self.console.read_only = False
        for method in (self.console.evidence_files, self.console.import_evidence_path, self.console.restart):
            method.reset_mock()

    def post(self, served, path, data=None, **headers):
        return served.request(path, method='POST', data={} if data is None else data,
                              headers={'X-Mentat-Token': self.console.token, **headers})

    def test_nothing_is_enforced_and_the_bind_is_loopback(self):
        self.assertFalse(app.Handler.access_cfg.enforced)
        self.assertEqual(app.Handler.access_cfg.bind_host, '127.0.0.1')
        self.assertFalse(gate.AccessConfig.from_env({}).enforced)

        class Spy:
            request_queue_size = 0

            def __init__(self, address, handler, bind_and_activate=True):
                Spy.address = address

            server_bind = server_activate = server_close = lambda self: None

        with patch.object(app, 'ThreadingHTTPServer', Spy):
            app.console_server(8123)
            self.assertEqual(Spy.address, ('127.0.0.1', 8123))
            app.console_server(8123, host='10.0.0.5')
            self.assertEqual(Spy.address, ('10.0.0.5', 8123))

    def test_host_must_be_loopback_with_this_port(self):
        for served in (self.plain, self.listed):
            status, _, body = served.request('/api/session?light=1', headers={'Host': 'elsewhere.invalid'})
            self.assertEqual((status, body), (403, {'error': 'Local access only.'}))
            status, _, _ = served.request('/api/session?light=1', headers={'Host': '127.0.0.1:1'})
            self.assertEqual(status, 403)
        status, _, body = self.listed.request('/api/session?light=1', headers={'Host': HOST})
        self.assertEqual((status, body), (403, {'error': 'Local access only.'}), 'ALLOWED_HOSTS alone adds nothing')
        status, _, body = self.plain.request('/api/session?light=1')
        self.assertEqual((status, body['token'], body['read_only']), (200, 'local-token', False))
        status, _, body = self.plain.request('/api/session?light=1', headers={'Host': f'localhost:{self.plain.port}'})
        self.assertEqual(status, 200)

    def test_origin_must_be_loopback(self):
        with patch('giving_forecast.project', return_value={'ok': True}) as project:
            for served, origin in ((self.plain, 'https://elsewhere.invalid'), (self.listed, f'https://{HOST}'),
                                   (self.listed, f'http://{HOST}')):
                status, _, body = self.post(served, '/api/forecast/project', Origin=origin)
                self.assertEqual((status, body), (403, {'error': 'Local access only.'}), origin)
            project.assert_not_called()
            for origin in (f'http://127.0.0.1:{self.plain.port}', f'http://localhost:{self.plain.port}'):
                status, _, body = self.post(self.plain, '/api/forecast/project', Origin=origin)
                self.assertEqual((status, body), (200, {'ok': True}), origin)
            self.assertEqual(self.post(self.plain, '/api/forecast/project')[0], 200, 'no Origin header is still fine')

    def test_token_flow_is_intact(self):
        status, headers, body = self.plain.request('/api/session?light=1')
        self.assertEqual((status, body['token']), (200, 'local-token'))
        self.assertEqual(headers['Cache-Control'], 'no-store')
        with patch('giving_forecast.project', return_value={'ok': True}):
            self.assertEqual(self.post(self.plain, '/api/forecast/project')[0], 200)
            status, _, body = self.plain.request('/api/forecast/project', method='POST', data={},
                                                 headers={'X-Mentat-Token': 'hosted-read-only'})
            self.assertEqual((status, body), (403, {'error': 'Refresh the app before continuing.'}))
            status, _, _ = self.plain.request('/api/forecast/project', method='POST', data={})
            self.assertEqual(status, 403)

    def test_no_hosted_routes_headers_or_log_lines(self):
        for route in ('/healthz', '/version'):
            status, _, body = self.plain.request(route)
            self.assertEqual((status, body), (404, {'error': 'Not found.'}), route)
        status, headers, _ = self.plain.request('/app.js')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Cache-Control'], 'private, no-cache')
        for name in ('Referrer-Policy', 'X-Frame-Options', 'Cross-Origin-Resource-Policy'):
            self.assertNotIn(name, headers)
        self.assertEqual(self.plain.stderr, '', 'a local console logs nothing')

    def test_other_verbs_and_the_local_answers_are_what_they_were(self):
        for method in ('PUT', 'DELETE', 'HEAD', 'OPTIONS'):
            self.assertEqual(self.plain.request('/api/runs', method=method)[0], 501, method)
        status, _, body = self.plain.request('/api/health')
        self.assertEqual(status, 200)
        self.assertEqual((body['project'], body['report_directory'], body['resolved_data_root']),
                         (str(app.PROJECT), self.temp.name, str(Path(self.temp.name))))
        status, _, body = self.plain.request('/api/session?light=1')
        self.assertEqual(body['report_directory'], self.temp.name)

    def test_local_donor_rows_are_not_gated(self):
        with patch.object(app.contribution_workbook_guard, 'verify_sources', return_value=[]), \
                patch.object(app.contribution_query, 'records', return_value={'rows': [{'source_id': 'a'}]}):
            status, _, body = self.post(self.plain, '/api/contributions/records', {'dataset': 'Example'})
        self.assertEqual((status, body['rows']), (200, [{'source_id': 'a'}]))

    def test_local_read_only_allowlist_is_what_it_was(self):
        self.console.read_only = True
        status, _, body = self.post(self.plain, '/api/evidence-files', {'path': '.'})
        self.assertEqual((status, body), (200, {'files': []}))
        status, _, body = self.post(self.plain, '/api/evidence-csv', {'path': 'C:/somewhere/file.csv'})
        self.assertEqual((status, body['state']), (200, 'reading'))
        status, _, body = self.post(self.plain, '/api/restart')
        self.assertEqual(status, 403)
        self.assertIn('read-only while the original console', body['error'])
        self.console.restart.assert_not_called()


@needs_crypto
class HostedMode(unittest.TestCase):
    """Access enforced on a loopback bind (ACCESS_ENFORCE=1), as the container will run it."""

    MUTATORS = ('upload', 'create_roster', 'collect_evidence', 'launch', 'resume', 'acknowledge_quality',
                'archive_run', 'stop', 'set_workers', 'publish_pocket', 'add_to_briefing', 'remove_from_briefing',
                'order_briefing', 'save_view', 'delete_view', 'restart', 'import_evidence_path',
                'import_evidence_csv', 'evidence_files', 'start_evidence_geocode')

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.idp = Idp(cls.temp.name)
        cls.mutators = {name: Mock() for name in cls.MUTATORS}
        cls.console = SimpleNamespace(
            token=REAL_TOKEN, read_only=True, report_directory=Path(cls.temp.name),
            configured_root=cls.temp.name, root=Path(cls.temp.name),
            summary=Mock(return_value={'runs': []}), report_path=Mock(), evidence_store=Mock(), **cls.mutators)
        config = gate.AccessConfig.from_env(cls.idp.env())

        class Hosted(app.Handler):
            access_cfg = config

        cls.served = Served(Hosted, cls.console)

    @classmethod
    def tearDownClass(cls):
        cls.served.close()
        cls.temp.cleanup()

    def get(self, path, *, token=True, host=HOST, **headers):
        sent = {'Host': host, **headers}
        if token:
            sent['Cf-Access-Jwt-Assertion'] = self.idp.token() if token is True else token
        return self.served.request(path, headers=sent)

    def post(self, path, data=None, *, marker='hosted-read-only', host=HOST, jwt=True, **headers):
        sent = {'Host': host, **headers}
        if marker is not None:
            sent['X-Mentat-Token'] = marker
        if jwt:
            sent['Cf-Access-Jwt-Assertion'] = self.idp.token()
        return self.served.request(path, method='POST', data={} if data is None else data, headers=sent)

    def setUp(self):
        for method in (*self.mutators.values(), self.console.report_path, self.console.summary,
                       self.console.evidence_store):
            method.reset_mock()

    def assert_untouched(self):
        for name, method in self.mutators.items():
            self.assertFalse(method.called, name)
        self.assertFalse(self.console.report_path.called)
        self.assertEqual(self.console.evidence_store.mock_calls, [])

    def test_the_config_is_the_environments(self):
        config = gate.AccessConfig.from_env(self.idp.env())
        self.assertTrue(config.enforced)
        self.assertEqual(config.bind_host, '127.0.0.1')
        self.assertEqual(config.allowed_hosts, gate.LOOPBACK | {HOST})

    def test_no_valid_jwt_gets_nothing(self):
        for route in ('/', '/api/session?light=1', '/app.js', '/api/runs', '/api/report?id=a&index=0'):
            status, headers, body = self.get(route, token=False)
            self.assertEqual((status, body), (403, b'forbidden\n'), route)
        for name, bad in (('wrong audience', self.idp.token(aud=['someone-else'])),
                          ('expired', self.idp.token(exp=int(time.time()) - 3600)),
                          ('no identity', self.idp.token(email=None)),
                          ('garbage', 'not.a.jwt')):
            self.assertEqual(self.get('/api/session?light=1', token=bad)[0], 403, name)
        status, _, _ = self.post('/api/forecast/project', jwt=False)
        self.assertEqual(status, 403)
        self.assert_untouched()

    def test_wrong_host_is_refused_even_with_a_valid_jwt(self):
        self.assertEqual(self.get('/api/session?light=1', host='evil.example')[0], 403)
        self.assertEqual(self.post('/api/forecast/project', host='evil.example')[0], 403)

    def test_a_read_only_get_is_served_with_security_headers(self):
        status, headers, body = self.get('/api/session?light=1')
        self.assertEqual((status, body['read_only']), (200, True))
        status, headers, _ = self.get('/app.js')
        self.assertEqual(status, 200)
        self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertEqual(headers['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertEqual(headers['Cache-Control'], 'private, no-cache', 'the route keeps its own caching rule')
        # one copy of each header, not the route's and the gate's
        raw = http.client.HTTPConnection('127.0.0.1', self.served.port)
        with contextlib.redirect_stderr(io.StringIO()):
            raw.request('GET', '/app.js', headers={'Host': HOST, 'Cf-Access-Jwt-Assertion': self.idp.token()})
            response = raw.getresponse()
            response.read()
        names = [name.lower() for name, _ in response.getheaders()]
        raw.close()
        for name in ('x-content-type-options', 'cache-control', 'referrer-policy', 'x-frame-options'):
            self.assertEqual(names.count(name), 1, name)

    def test_the_consoles_token_is_never_handed_out(self):
        for route in ('/api/session?light=1', '/api/session', '/api/contributions/session'):
            status, headers, body = self.get(route)
            self.assertEqual(status, 200, route)
            self.assertEqual(body['token'], 'hosted-read-only', route)
            self.assertNotIn(REAL_TOKEN, json.dumps(body))
        self.assertNotIn(REAL_TOKEN, self.served.stderr)

    def test_a_post_needs_the_marker_and_an_allowed_origin(self):
        with patch('giving_forecast.project', return_value={'ok': True}) as project:
            self.assertEqual(self.post('/api/forecast/project'), (200, unittest.mock.ANY, {'ok': True}))
            for name, kwargs in (('no marker', {'marker': None}), ('the console token', {'marker': REAL_TOKEN}),
                                 ('a guess', {'marker': 'x'}),
                                 ('a foreign origin', {'Origin': 'https://elsewhere.invalid'}),
                                 ('http origin', {'Origin': f'http://{HOST}'})):
                status, _, _ = self.post('/api/forecast/project', **kwargs)
                self.assertEqual(status, 403, name)
            self.assertEqual(project.call_count, 1)
            self.assertEqual(self.post('/api/forecast/project', Origin=f'https://{HOST}')[0], 200)
            self.assertEqual(self.post('/api/forecast/project', Origin=f'https://{HOST.upper()}')[0], 200)

    def test_every_post_route_but_the_analytical_reads_is_refused(self):
        literals = set(re.findall(r"""['"](/api/[a-z0-9/-]+)['"]""", inspect.getsource(app.Handler.do_POST)))
        refused = sorted(literals - ANALYTICAL)
        for needed in ('/api/evidence-csv', '/api/evidence-files', '/api/export/pdf', '/api/upload', '/api/restart',
                       '/api/stop', '/api/keys', '/api/start', '/api/evidence-geocode', '/api/studio/views'):
            self.assertIn(needed, refused)
        bodies = {'/api/evidence-csv': {'path': 'C:/Windows/win.ini'}, '/api/evidence-files': {'path': 'C:/'},
                  '/api/upload': {'filename': 'x.xlsx', 'content': 'AAAA'}}
        for route in refused:
            with self.subTest(route=route):
                status, _, body = self.post(route, bodies.get(route))
                self.assertEqual(status, 403, body)
        # the raw CSV upload form of /api/evidence-csv, and a path with a query string
        self.assertEqual(self.served.request('/api/evidence-csv', method='POST', raw=b'a,b\n1,2\n', headers={
            'Host': HOST, 'X-Mentat-Token': 'hosted-read-only', 'Content-Type': 'text/csv',
            'X-Evidence-Name': 'x.csv', 'Cf-Access-Jwt-Assertion': self.idp.token()})[0], 403)
        self.assertEqual(self.post('/api/evidence-csv?x=1', {'path': 'C:/'})[0], 403)
        self.assert_untouched()

    def test_every_verb_is_gated_not_only_get_and_post(self):
        token = self.idp.token()
        for method in ('HEAD', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'TRACE'):
            with self.subTest(method=method):
                status, _, _ = self.served.request('/api/runs', method=method, headers={'Host': HOST})
                self.assertEqual(status, 403, 'refused by the gate, not left to http.server as 501')
                # past the gate nothing handles it
                status, _, _ = self.served.request('/api/runs', method=method, headers={
                    'Host': HOST, 'Cf-Access-Jwt-Assertion': token})
                self.assertEqual(status, 501)
        self.assert_untouched()
        for name in ('do_GET', 'do_POST'):
            self.assertNotIn('access_check', inspect.getsource(getattr(app.Handler, name)), name)
        self.assertIs(app.Handler.parse_request, gate.AccessMixin.parse_request)

    def records(self, route, email=EMAIL):
        return self.served.request(route, method='POST', data={'dataset': 'Example'}, headers={
            'Host': HOST, 'X-Mentat-Token': 'hosted-read-only', 'Cf-Access-Jwt-Assertion': self.idp.token(email=email)})

    def test_donor_rows_are_refused_unless_the_email_is_listed(self):
        with patch.object(app.contribution_workbook_guard, 'verify_sources', return_value=[]), \
                patch.object(app.contribution_query, 'records', return_value={'rows': [{'source_id': 'a'}]}) as contribution, \
                patch.object(app.contribution_query, 'query', return_value={'rows': []}) as aggregate, \
                patch('analysis_data.records', return_value={'rows': [{'source_id': 'b'}]}) as insights, \
                patch.dict(os.environ):
            os.environ.pop('MENTAT_DONOR_ROW_EMAILS', None)
            readers = {'/api/contributions/records': contribution, '/api/insights/records': insights}
            for route, reader in readers.items():          # default: nobody
                status, _, body = self.records(route)
                self.assertEqual((status, body), (403, {'error': app.HOSTED_DONOR_ROWS_REFUSED}), route)
                reader.assert_not_called()
            os.environ['MENTAT_DONOR_ROW_EMAILS'] = ' Someone@Example.test , ' + EMAIL.upper()   # case and spaces
            for route, reader in readers.items():
                status, _, body = self.records(route)
                self.assertEqual((status, len(body['rows'])), (200, 1), route)
                self.assertEqual(reader.call_count, 1)
                status, _, body = self.records(route, email='stranger@example.test')
                self.assertEqual((status, body), (403, {'error': app.HOSTED_DONOR_ROWS_REFUSED}), route)
                self.assertEqual(reader.call_count, 1)
            self.assertEqual(self.records('/api/contributions/query', email='stranger@example.test')[0], 200,
                             'only the two records routes carry donor rows')
            aggregate.assert_called_once()
            os.environ['MENTAT_DONOR_ROW_EMAILS'] = ''
            self.assertEqual(self.records('/api/contributions/records')[0], 403)
        self.assert_untouched()

    def test_health_and_session_carry_no_server_paths(self):
        windows = 'C:\\Users\\pgoff\\Mentat\\mentat\\.cache\\x\\mentat.db'
        summary = {'runs': [], 'collection_directory': self.temp.name, 'report_directory': self.temp.name,
                   'coverage': [{'industry': 'Banking', 'receipt': windows, 'database': '/srv/mentat/db.sqlite'}],
                   'read_only': True}

        def strings(value):
            if isinstance(value, dict):
                value = list(value.values())
            for item in value if isinstance(value, list) else [value]:
                if isinstance(item, (dict, list)):
                    yield from strings(item)
                elif isinstance(item, str):
                    yield item

        with patch.object(self.console, 'summary', Mock(return_value=summary)):
            for route in ('/api/health', '/api/session?light=1', '/api/session', '/api/runs'):
                status, _, body = self.get(route)
                self.assertEqual(status, 200, route)
                self.assertEqual([s for s in strings(body) if app._SERVER_PATH.match(s)], [], route)
                for key in ('project', 'data_root', 'resolved_data_root', 'report_directory', 'collection_directory'):
                    self.assertNotIn(key, body, route)
        status, _, health = self.get('/api/health')
        self.assertEqual((health['application'], health['read_only']), ('MENTAT', True))
        self.assertIn('code_sha256', health)
        with patch.object(self.console, 'summary', Mock(return_value=summary)):
            status, _, session = self.get('/api/session')
        self.assertEqual(session['coverage'], [{'industry': 'Banking'}])
        self.assertEqual(session['token'], 'hosted-read-only')

    def test_the_workbook_download_is_refused(self):
        status, _, body = self.get('/api/report?id=run&index=0')
        self.assertEqual((status, body), (403, {'error': app.HOSTED_REFUSED}))
        self.assert_untouched()

    def test_healthz_and_version(self):
        # no token, no proxy headers, loopback peer: this is the container's own health check
        status, _, body = self.served.request('/healthz', headers={'Host': f'127.0.0.1:{self.served.port}'})
        self.assertEqual((status, body), (200, {'status': 'ok'}))
        status, _, body = self.served.request('/version', headers={'Host': 'localhost'})
        self.assertEqual((status, body['app']), (200, 'mentat-console'))
        self.assertEqual(set(body), {'app', 'git_sha', 'build_time', 'snapshot_id'})
        # the same request seen through the tunnel (Cf- headers), a foreign Host, or on any other route
        self.assertEqual(self.served.request('/healthz', headers={'Host': HOST, 'Cf-Ray': '1'})[0], 403)
        self.assertEqual(self.served.request('/healthz', headers={'Host': 'evil.example'})[0], 403)
        self.assertEqual(self.served.request('/api/runs', headers={'Host': f'127.0.0.1:{self.served.port}'})[0], 403)
        self.assertEqual(self.get('/healthz')[0], 200)

    def test_one_audit_line_per_request_without_query_or_address(self):
        self.get('/api/session?light=1&secret=abc')
        line = json.loads(self.served.stderr.strip().splitlines()[-1])
        self.assertEqual({k: line[k] for k in ('app', 'user', 'method', 'route', 'status')},
                         {'app': 'mentat-console', 'user': EMAIL, 'method': 'GET', 'route': '/api/session', 'status': 200})
        self.assertNotIn('secret', self.served.stderr)
        self.assertNotIn('127.0.0.1', self.served.stderr)
        self.get('/api/runs', token=False)
        denied = json.loads(self.served.stderr.strip().splitlines()[-1])
        self.assertEqual((denied['user'], denied['status'], denied['reason']), ('-', 403, 'no token'))


class StateWriteRoot(unittest.TestCase):
    """MENTAT_STATE_WRITE_ROOT: the caches the console writes move; the inputs stay put."""

    PAIRS = (('contribution_query_store', 'ROOT'), ('analysis_history', 'ROOT'),
             ('contribution_source_guard', 'CACHE_ROOT'), ('analysis_data', 'ROOT'), ('response_cache', 'ROOT'),
             ('analysis_data', 'HINTS_PATH'), ('access_stats', 'PATH'), ('contribution_geo', 'CACHE'),
             ('glassbox_emit', 'EVENTS_DIR'),
             ('contribution_data', '_materialize'), ('contribution_data', 'CACHE_ROOT'),
             ('contribution_source_guard', 'ACCEPTED_ROOT'))

    def setUp(self):
        import importlib
        import drawer_sidecars
        import prewarm
        self.prewarm, self.drawer = prewarm, drawer_sidecars
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'write-root'
        self.shipped = Path(self.temp.name) / 'shipped-state'
        modules = {name: importlib.import_module(name) for name, _ in self.PAIRS}
        self.before = {pair: getattr(modules[pair[0]], pair[1]) for pair in self.PAIRS}
        self.modules = modules
        previous = drawer_sidecars.configure()
        project_state = Path(app.PROJECT) / 'state'
        self.state_listing = sorted(str(p) for p in project_state.rglob('*')) if project_state.exists() else []

        def restore():
            for (name, attribute), value in self.before.items():
                setattr(modules[name], attribute, value)
            drawer_sidecars.configure(**previous)
            contribution_data._jobs.pop('tok', None)
            self.temp.cleanup()

        self.addCleanup(restore)
        (self.shipped / 'contribution-source-proofs').mkdir(parents=True)
        (self.shipped / 'contribution-source-proofs' / 'a.json').write_text('{"proof": 1}')
        (self.shipped / 'geography' / 'census-v1').mkdir(parents=True)
        (self.shipped / 'geography' / 'census-v1' / 'b.json').write_text('{"census": 1}')

    def redirect(self):
        with patch.object(self.prewarm, 'DEFAULT_STATE_ROOT', self.shipped):
            return app.redirect_state_writes(self.root)

    def test_writers_move_and_inputs_stay(self):
        self.assertEqual(self.redirect(), self.root.resolve())
        root = self.root.resolve()
        for (name, attribute), original in self.before.items():
            now = getattr(self.modules[name], attribute)
            if attribute in ('CACHE_ROOT', 'ACCEPTED_ROOT') and (name, attribute) in self.prewarm.READ_ONLY_STATE:
                self.assertEqual(now, original, f'{name}.{attribute} is a shipped input')
            elif attribute != '_materialize':
                self.assertTrue(Path(now).is_relative_to(root), f'{name}.{attribute} -> {now}')
        self.assertEqual(self.modules['contribution_source_guard'].CACHE_ROOT, root / 'contribution-source-proofs')
        self.assertEqual(self.modules['response_cache'].ROOT, root / 'response-cache')
        self.assertTrue(self.drawer.state_root().is_relative_to(root))
        self.assertFalse(self.drawer._settings['emit'])

    def test_what_the_console_writes_lands_under_the_root_and_nothing_under_state(self):
        self.redirect()
        store = self.modules['contribution_query_store']
        store._atomic(store.ROOT / 'responses' / 'x.json', b'1')
        self.assertTrue((self.root / 'contribution-query-cache' / 'responses' / 'x.json').is_file())
        geo = self.modules['contribution_geo']
        self.assertEqual(geo._cached('k', lambda: {'a': 1})['data'], {'a': 1})
        self.assertEqual(len(list((self.root / 'geography' / 'census-v1').glob('*.json'))) , 2, 'seeded file + new one')
        self.drawer._write(self.drawer.state_root() / 'native' / 's.bin', {'k': 1}, b'body')
        self.assertTrue((self.root / 'drawer-sidecars' / 'native' / 's.bin').is_file())
        project_state = Path(app.PROJECT) / 'state'
        after = sorted(str(p) for p in project_state.rglob('*')) if project_state.exists() else []
        self.assertEqual(after, self.state_listing)

    def test_the_shipped_caches_are_seeded_once_and_not_touched(self):
        self.redirect()
        self.assertEqual((self.root / 'contribution-source-proofs' / 'a.json').read_text(), '{"proof": 1}')
        self.assertEqual((self.root / 'geography' / 'census-v1' / 'b.json').read_text(), '{"census": 1}')
        (self.root / 'contribution-source-proofs' / 'a.json').write_text('changed here')
        self.redirect()
        self.assertEqual((self.root / 'contribution-source-proofs' / 'a.json').read_text(), 'changed here')
        self.assertEqual((self.shipped / 'contribution-source-proofs' / 'a.json').read_text(), '{"proof": 1}')

    def test_a_missing_index_is_refused_not_built(self):
        self.redirect()
        built = Path(self.temp.name) / 'index.sqlite'
        contribution_data._materialize({'database': 'x'}, 'tok', built)
        job = contribution_data._jobs['tok']
        self.assertEqual((job['status'], job['message']), ('error', self.prewarm.INDEX_REFUSED))
        self.assertFalse(built.exists())


class ReceiptPaths(unittest.TestCase):
    """Receipts and accepted-source pointers hold Windows paths; Linux must still find the files."""

    def as_linux(self, text):
        with patch.object(receipt_paths, 'os', SimpleNamespace(name='posix')):
            return receipt_paths.receipt_path(text)

    def relative_to_project(self, text):
        return self.as_linux(text).relative_to(receipt_paths.PROJECT).as_posix()

    def test_a_windows_path_is_rebased_onto_this_checkout(self):
        for text, expected in (
                ('C:/Users/pgoff/Mentat/mentat/.cache/report-repairs/banking-20260910/data/mentat.db',
                 '.cache/report-repairs/banking-20260910/data/mentat.db'),
                ('C:\\Users\\pgoff\\Mentat\\mentat\\state\\accepted-report-sources\\credit_union\\2022-2024-2026\\x.db',
                 'state/accepted-report-sources/credit_union/2022-2024-2026/x.db'),
                ('c:\\users\\PGOFF\\MENTAT\\MENTAT\\.cache\\y.db', '.cache/y.db')):
            self.assertEqual(self.relative_to_project(text), expected)
        outside = self.as_linux('C:/Users/pgoff/Mentat/tmp/production-all/runs/x/data/mentat.db')
        self.assertEqual(outside.relative_to(receipt_paths.PROJECT.parent).as_posix(), 'tmp/production-all/runs/x/data/mentat.db')

    def test_everything_else_is_left_alone(self):
        for text in ('/srv/mentat/.cache/x.db', 'relative/x.db', 'D:/elsewhere/x.db', ''):
            self.assertEqual(self.as_linux(text), Path(text), text)

    def test_windows_keeps_the_path_it_was_given(self):
        if os.name != 'nt':
            self.skipTest('Windows only')
        self.assertEqual(receipt_paths.receipt_path('C:/Users/pgoff/Mentat/mentat/.cache/x'), Path('C:/Users/pgoff/Mentat/mentat/.cache/x'))

    def test_the_readers_use_it(self):
        for module in (contribution_data, contribution_source_guard, source_memo):
            self.assertIs(module.receipt_path, receipt_paths.receipt_path, module.__name__)
        # contribution_data._sources and source_memo._discover are too heavy to drive here: guard the call sites.
        for function, needles in ((contribution_data._sources, ("receipt_path(metadata['database_path'])",
                                                                "receipt_path(hydration['output'])")),
                                  (source_memo._discover, ("receipt_path(data._payload_metadata(payload)['database_path'])",
                                                           "receipt_path(hydration['output'])"))):
            source = inspect.getsource(function)
            for needle in needles:
                self.assertIn(needle, source, function.__name__)

    def test_verify_finds_the_snapshot_a_windows_pointer_names(self):
        guard = contribution_source_guard
        pointer = {'snapshot': 'C:\\Users\\pgoff\\Mentat\\mentat\\state\\accepted-report-sources\\x\\2022-2024-2026\\s.db'}
        source = {'hydration_manifest': 'h', 'industry': 'X', 'database': 'recovered.db', 'database_sha256': 'a',
                  'original_database_sha256': 'b'}
        fake_stamp = lambda path: guard.LOADED_ALGORITHM_STAMP if path == guard.__file__ else (str(path), 1, 1, 1)
        with patch.object(guard, '_stamp', side_effect=fake_stamp), patch.object(guard, '_read', return_value=pointer), \
                patch.object(guard, '_quiescent'), patch.object(guard, '_verify_cached', return_value='proof') as verified, \
                patch.object(receipt_paths, 'os', SimpleNamespace(name='posix')):
            self.assertEqual(guard.verify(source), 'proof')
        expected = (guard.ACCEPTED_ROOT / 'x' / '2022-2024-2026' / 's.db').resolve()
        self.assertEqual(Path(verified.call_args.args[2][0]), expected)

    def test_an_accepted_pointer_written_on_windows_matches_its_snapshot_on_linux(self):
        guard = contribution_source_guard
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            database = temp / 'recovered.db'
            database.write_bytes(b'db')
            pointer = temp / 'current.json'
            pointer.write_text(json.dumps({
                'status': 'verified', 'industry': 'X', 'cycles': list(guard.CYCLES), 'database_sha256': 'original',
                'snapshot': 'C:\\Users\\pgoff\\Mentat\\mentat\\state\\accepted-report-sources\\x\\2022-2024-2026\\s.db'}))
            snapshot = guard.ACCEPTED_ROOT / 'x' / '2022-2024-2026' / 's.db'
            stamp = lambda path: (str(path.resolve()), 1, 1, 1)
            arguments = (stamp(database), stamp(pointer), stamp(snapshot), 'not-its-hash', 'original', 'X', 'algorithm',
                         str(temp))
            # The pointer names the snapshot, so verification moves on to the next check (the database's hash).
            with patch.object(receipt_paths, 'os', SimpleNamespace(name='posix')):
                with self.assertRaisesRegex(ValueError, 'recovered database changed'):
                    guard._verify_cached.__wrapped__(*arguments)
            # Named some other snapshot, it is refused at the pointer.
            pointer.write_text(pointer.read_text().replace('\\\\s.db', '\\\\other.db'))
            with patch.object(receipt_paths, 'os', SimpleNamespace(name='posix')):
                with self.assertRaisesRegex(ValueError, 'does not match the original published source scope'):
                    guard._verify_cached.__wrapped__(*arguments)

    def test_a_stored_windows_source_path_still_names_its_industry(self):
        record = {'name': 'upload.csv', 'catalog': {'row_count': 0, 'committees': []},
                  'source_path': 'C:\\Users\\pgoff\\Downloads\\Banking Industry Spending Overview.xlsx'}
        self.assertEqual(evidence_csv.stored_catalog(record)['industry'], 'Banking')


class KeyStoreImport(unittest.TestCase):
    def test_wintypes_is_not_needed_to_import_the_key_store(self):
        tools = Path(app.PROJECT) / 'tools'
        code = ('import sys; sys.path.insert(0, %r); import fec_key_store; '
                'sys.exit(1 if "ctypes.wintypes" in sys.modules else 0)' % str(tools))
        done = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)

    @unittest.skipUnless(os.name == 'nt', 'DPAPI is Windows only')
    def test_the_dpapi_round_trip_still_works(self):
        sys.path.insert(0, str(Path(app.PROJECT) / 'tools'))
        import fec_key_store
        self.assertEqual(fec_key_store.crypt(fec_key_store.crypt(b'not-a-key'), decrypt=True), b'not-a-key')


class HostedStartup(unittest.TestCase):
    """server.py main(), run for real on an OS-chosen port with every path in a temp dir."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.reports = Path(self.temp.name) / 'reports'
        self.reports.mkdir()
        self.port = free_port()

    def command(self, *extra):
        return [sys.executable, '-B', str(SERVER_PY), '--port', str(self.port), '--data-root',
                str(Path(self.temp.name) / 'data'), *extra]

    def environment(self, **over):
        env = {k: v for k, v in os.environ.items()
               if not k.startswith(('ACCESS_', 'MENTAT_')) and k not in ('BIND_HOST', 'ALLOWED_HOSTS', 'GIT_SHA')}
        env.update(MENTAT_REPORT_DIRECTORY=str(self.reports), PYTHONDONTWRITEBYTECODE='1',
                   GLASSBOX_EVENTS_DIR=str(Path(self.temp.name) / 'glassbox'))
        env.update(over)
        return env

    def run_to_exit(self, env, *extra):
        return subprocess.run(self.command(*extra), env=env, capture_output=True, text=True, timeout=120)

    def test_a_non_loopback_bind_without_the_access_environment_does_not_start(self):
        done = self.run_to_exit(self.environment(BIND_HOST='0.0.0.0'), '--read-only')
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn('ACCESS_AUD', done.stderr)

    def test_an_enforced_console_must_be_read_only(self):
        env = self.environment(ACCESS_ENFORCE='1', ACCESS_AUD=AUD, ACCESS_ISSUER=ISS,
                               ACCESS_JWKS_FILE=str(Path(self.temp.name) / 'certs.json'))
        done = self.run_to_exit(env)
        self.assertEqual(done.returncode, 2, done.stderr)
        self.assertIn('--read-only', done.stderr)
        self.assertNotIn('Mentat app', done.stdout)

    @needs_crypto
    def test_a_hosted_console_serves_only_behind_access(self):
        idp = Idp(self.temp.name)
        env = self.environment(**idp.env(MENTAT_STATE_WRITE_ROOT=str(Path(self.temp.name) / 'state-write'),
                                         GIT_SHA='abc1234'))
        process = subprocess.Popen(self.command('--read-only'), env=env, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True)
        try:
            def call(path, headers):
                connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=10)
                try:
                    connection.request('GET', path, headers=headers)
                    response = connection.getresponse()
                    return response.status, response.read()
                finally:
                    connection.close()

            deadline = time.time() + 120
            while True:
                self.assertIsNone(process.poll(), 'the console exited during start-up')
                try:
                    if call('/healthz', {'Host': f'127.0.0.1:{self.port}'})[0] == 200:
                        break
                except OSError:
                    pass
                self.assertLess(time.time(), deadline, 'the console did not come up')
                time.sleep(.25)
            self.assertEqual(call('/api/session?light=1', {'Host': HOST})[0], 403)
            status, body = call('/api/session?light=1', {'Host': HOST, 'Cf-Access-Jwt-Assertion': idp.token()})
            self.assertEqual((status, json.loads(body)['token'], json.loads(body)['read_only']), (200, 'hosted-read-only', True))
            status, body = call('/version', {'Host': f'127.0.0.1:{self.port}'})
            self.assertEqual((status, json.loads(body)['git_sha']), (200, 'abc1234'))
        finally:
            process.terminate()
            try:
                out, err = process.communicate(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                out, err = process.communicate()
        self.assertIn('hosted, read-only', out)
        self.assertNotIn('MENTAT_STATE_WRITE_ROOT', err)
        lines = [json.loads(line) for line in err.splitlines() if line.startswith('{')]
        self.assertTrue(any(line['route'] == '/api/session' and line['status'] == 200 and line['user'] == EMAIL
                            for line in lines), err)
        self.assertTrue(any(line.get('reason') == 'no token' for line in lines), err)


if __name__ == '__main__':
    unittest.main()
