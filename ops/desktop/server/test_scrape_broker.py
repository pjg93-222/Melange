import concurrent.futures
import base64
import hashlib
import http.client
import http.server
import json
from pathlib import Path
import ssl
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from scrape_broker import BrokerError, Limits, ScrapeBroker, UpstreamResponse, checked_request, from_environment, upstream, _NoRedirect
from desktop_admin import BoundedServer, handler_for
from test_access_store import AccessStoreTests

QUERY = {'schemaVersion': 1, 'provider': 'fec', 'path': 'schedules/schedule_a',
         'query': {'committee_id': ['C00000001'], 'per_page': 10}}
KEY = 'synthetic-server-only-key-0123456789'

def source(value): return UpstreamResponse(json.dumps(value).encode(), headers={'content-type':'application/json'})
def decoded(value): return json.loads(base64.b64decode(value['raw']['bodyBase64']))


class BrokerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve(); self.now = 1800000000
        self.grant = {'app': 'melange', 'principal_id': str(uuid.uuid4()), 'revoked': 0}
        self.calls = []

    def broker(self, **options):
        def fetch(provider, url, key):
            self.calls.append((provider, url, key)); return source({'results': [1], 'pagination': {'count': 1}})
        return ScrapeBroker(self.root, keys={'fec': KEY, 'congress': KEY},
            clock=lambda: self.now, fetch=options.pop('fetch', fetch), **options)

    def test_only_fixed_government_endpoints_and_bounded_parameters(self):
        broker = self.broker()
        broker.execute(self.grant, QUERY)
        self.assertTrue(self.calls[0][1].startswith('https://api.open.fec.gov/v1/schedules/schedule_a/?'))
        self.assertNotIn(KEY, self.calls[0][1])
        for change in ({'path': 'https://evil.invalid/x'}, {'path': '../private'}, {'path': 'bill/%2fprivate'},
                       {'path': 'bill\\private'}, {'provider': 'arbitrary'}, {'query': {'api_key': KEY}},
                       {'query': {'Authorization': KEY}}, {'query': {'headers': '{}'}},
                       {'query': {'per_page': 101}}, {'headers': {'X-Api-Key': 'user-key'}}):
            with self.subTest(change=change), self.assertRaises(BrokerError):
                broker.execute(self.grant, {**QUERY, **change})
        self.assertEqual(len(self.calls), 1)
        provider, url = checked_request({'schemaVersion': 1, 'provider': 'congress',
            'path': 'bill/119/hr/1/actions', 'query': {'limit': 250}})
        self.assertEqual(provider, 'congress'); self.assertIn('format=json', url)
        with self.assertRaises(BrokerError): _NoRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.invalid')

    def test_quota_survives_recreation_and_counts_failed_attempts(self):
        limits = Limits(per_principal_hour=1, global_hour=3)
        def fail(*_): raise RuntimeError(KEY)
        with self.assertRaisesRegex(BrokerError, 'upstream_unavailable'):
            self.broker(limits=limits, fetch=fail).execute(self.grant, QUERY)
        with self.assertRaises(BrokerError) as caught:
            self.broker(limits=limits).execute(self.grant, QUERY)
        self.assertEqual((caught.exception.status, caught.exception.retry_after), (429, 3600))
        self.now += 3600
        self.assertEqual(decoded(self.broker(limits=limits).execute(self.grant, QUERY))['results'], [1])

    def test_global_budget_spans_providers_and_users(self):
        broker = self.broker(limits=Limits(per_principal_hour=10, global_hour=1))
        broker.execute(self.grant, QUERY)
        other = {**self.grant, 'principal_id': str(uuid.uuid4()), 'app': 'mentat'}
        with self.assertRaises(BrokerError) as caught:
            broker.execute(other, {'schemaVersion': 1, 'provider': 'congress', 'path': 'bill', 'query': {}})
        self.assertEqual(caught.exception.code, 'scrape_quota_exceeded')

    def test_persistent_concurrency_leases_and_release_on_finish(self):
        started, finish = threading.Event(), threading.Event()
        def fetch(*_):
            started.set(); self.assertTrue(finish.wait(4)); return source({'ok': True})
        limits = Limits(global_concurrent=1)
        one, two = self.broker(limits=limits, fetch=fetch), self.broker(limits=limits)
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            pending = pool.submit(one.execute, self.grant, QUERY)
            self.assertTrue(started.wait(3))
            try:
                with self.assertRaises(BrokerError) as caught: two.execute(self.grant, QUERY)
                self.assertEqual(caught.exception.code, 'scrape_concurrency_exceeded')
            finally: finish.set()
            self.assertEqual(decoded(pending.result()), {'ok': True})
        self.assertEqual(decoded(two.execute(self.grant, QUERY))['results'], [1])

    def test_upstream_429_cooldown_survives_restart(self):
        def limited(*_): raise BrokerError(429, 'upstream_rate_limited', 17)
        with self.assertRaises(BrokerError): self.broker(fetch=limited).execute(self.grant, QUERY)
        with self.assertRaises(BrokerError) as caught: self.broker().execute(self.grant, QUERY)
        self.assertEqual(caught.exception.retry_after, 17); self.assertEqual(self.calls, [])
        self.now += 17
        self.broker().execute(self.grant, QUERY); self.assertEqual(len(self.calls), 1)

    def test_keys_never_reach_success_response_exception_or_quota_database(self):
        def echo(*_): return source({'api_key': KEY, KEY: 'value', 'url': 'https://api.example/?api_key=' + KEY})
        broker = self.broker(fetch=echo)
        with self.assertRaises(BrokerError) as caught: broker.execute(self.grant, QUERY)
        self.assertNotIn(KEY, str(caught.exception))
        self.assertNotIn(KEY.encode(), broker.db.read_bytes())
        def fail(*_): raise ValueError('request headers leaked? ' + KEY)
        with self.assertRaises(BrokerError) as caught: self.broker(fetch=fail).execute(self.grant, QUERY)
        self.assertNotIn(KEY, str(caught.exception))

    def test_original_number_lexemes_and_whitespace_survive_without_secret_reflections(self):
        body = b'{ "results": [{"amount": 123456789012345.123456, "tiny":1e-99}] }\n'
        result = self.broker(fetch=lambda *_: UpstreamResponse(body, 200, {'Content-Type':'application/json','X-Secret':KEY})).execute(self.grant, QUERY)
        self.assertEqual(base64.b64decode(result['raw']['bodyBase64']), body)
        self.assertEqual(result['raw']['sha256'], hashlib.sha256(body).hexdigest())
        self.assertEqual(result['raw']['headers'], {'content-type':'application/json'})
        for value in (KEY, ''.join('%%%02x'%ord(char) for char in KEY)):
            with self.assertRaisesRegex(BrokerError, 'upstream_response_refused'):
                self.broker(fetch=lambda *_: source({'url':value})).execute(self.grant, QUERY)

    def test_disabled_configuration_performs_no_io_and_invalid_scopes_refuse(self):
        self.assertIsNone(from_environment(self.root / 'absent', {}))
        self.assertFalse((self.root / 'absent').exists())
        for grant in ({}, {**self.grant, 'revoked': 1}, {**self.grant, 'app': 'terrier'}):
            with self.assertRaises(BrokerError): self.broker().execute(grant, QUERY)
        with self.assertRaises(ValueError): from_environment(self.root, {'MELANGE_SCRAPE_BROKER_ENABLED': '1'})


class BrokerHTTPTests(unittest.TestCase):
    request, approval, activated, payload = (AccessStoreTests.request, AccessStoreTests.approval,
                                           AccessStoreTests.activated, AccessStoreTests.payload)

    def setUp(self):
        AccessStoreTests.setUp(self)
        self.calls = []
        def fetch(*args): self.calls.append(args); return source({'results': [1]})
        self.broker = ScrapeBroker(self.publisher.root, keys={'fec': KEY}, fetch=fetch)
        self.server = BoundedServer(('127.0.0.1', 0),
            handler_for(self.publisher, scrape_broker=self.broker), self.publisher.tls_context())
        self.addCleanup(self.server.server_close)
        worker = threading.Thread(target=self.server.serve_forever, daemon=True); worker.start()
        self.addCleanup(worker.join, 3); self.addCleanup(self.server.shutdown)

    def call(self, token=None, query=QUERY, extra=None):
        conn = http.client.HTTPSConnection('127.0.0.1', self.server.server_port,
            context=ssl._create_unverified_context(), timeout=3)
        try:
            headers = {'Content-Type': 'application/json', **(extra or {})}
            if token: headers['Authorization'] = 'Bearer ' + token
            conn.request('POST', '/v1/scrape/query', json.dumps(query), headers)
            result = conn.getresponse()
            return result.status, json.loads(result.read()), result.getheader('Retry-After')
        finally: conn.close()

    def test_approved_native_caller_works_anonymous_browser_and_revoked_callers_do_not(self):
        self.assertEqual(self.call()[0], 403)
        _, activation = self.activated('melange'); token = activation['accessToken']
        self.assertEqual(self.call(token, extra={'Origin': 'https://evil.invalid'})[0], 403)
        self.assertEqual(self.call(token)[0], 200); self.assertEqual(len(self.calls), 1)
        self.store.revoke(self.payload(activation['grant'])['grantId'])
        self.assertEqual(self.call(token)[0], 403); self.assertEqual(len(self.calls), 1)

    def test_retry_after_is_preserved_and_no_key_crosses_http(self):
        _, activation = self.activated('mentat')
        def limited(*_): raise BrokerError(429, 'upstream_rate_limited', 19)
        self.broker.fetch = limited
        status, data, retry = self.call(activation['accessToken'])
        self.assertEqual((status, retry), (429, '19')); self.assertNotIn(KEY, json.dumps(data))

    def test_default_disabled_keeps_ordinary_access_routes_available(self):
        with patch.dict('os.environ', {'MELANGE_SCRAPE_BROKER_ENABLED': '0'}):
            self.server.RequestHandlerClass = handler_for(self.publisher)
        _, activation = self.activated('mentat')
        self.assertEqual(self.call(activation['accessToken'])[:2], (503, {'error': 'scrape_service_disabled'}))
        self.assertEqual(self.calls, [])


class UpstreamTransportTests(unittest.TestCase):
    def test_exact_source_bytes_status_headers_and_absolute_drip_deadline(self):
        import urllib.request
        body=b'{ "amount": 123456789012345.123456 }\n';mode=['ok'];seen=[]
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_):pass
            def do_GET(self):
                seen.append(self.headers.get('X-Api-Key'))
                status={'ok':200,'missing':404,'limited':429,'drip':200}[mode[0]]
                self.send_response(status);self.send_header('Content-Type','application/json')
                if mode[0]=='limited':self.send_header('Retry-After','13')
                self.end_headers()
                if mode[0]=='drip':
                    try:
                        for _ in range(100):self.wfile.write(b' ');self.wfile.flush();time.sleep(.02)
                    except OSError:pass
                else:self.wfile.write(body)
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        self.addCleanup(server.server_close);self.addCleanup(worker.join,3);self.addCleanup(server.shutdown)
        native_opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        class LocalOpener:
            def open(self,request,timeout):
                return native_opener.open(urllib.request.Request('http://127.0.0.1:'+str(server.server_port)+'/',headers=dict(request.header_items())),timeout=timeout)
        with patch('scrape_broker.urllib.request.build_opener',return_value=LocalOpener()):
            result=upstream('fec','https://api.open.fec.gov/v1/candidates/',KEY)
            self.assertEqual((result.body,result.status),(body,200));self.assertEqual(seen,[KEY])
            mode[0]='missing';self.assertEqual(upstream('fec','https://api.open.fec.gov/v1/candidates/',KEY).status,404)
            mode[0]='limited'
            with self.assertRaises(BrokerError) as caught:upstream('fec','https://api.open.fec.gov/v1/candidates/',KEY)
            self.assertEqual((caught.exception.status,caught.exception.retry_after),(429,13))
            mode[0]='drip';native_timer=threading.Timer;started=time.monotonic()
            with patch('scrape_broker.threading.Timer',side_effect=lambda _seconds,fn:native_timer(.08,fn)):
                with self.assertRaises(BrokerError):upstream('fec','https://api.open.fec.gov/v1/candidates/',KEY)
            self.assertLess(time.monotonic()-started,1)


if __name__ == '__main__': unittest.main()
