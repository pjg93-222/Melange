import base64
import contextlib
import datetime
import hashlib
import http.server
import json
import io
import os
from pathlib import Path
import sys
import threading
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import scrape_client

BODY = b'{ "results": [{"amount": 123456789012345.123456}], "pagination": {"count": 1} }\n'


class ScrapeClientTests(unittest.TestCase):
    def setUp(self):
        self.requests=[]; self.status=200; self.corrupt=False
        owner=self
        class Handler(http.server.BaseHTTPRequestHandler):
            def log_message(self,*_): pass
            def do_POST(self):
                owner.requests.append((self.headers, json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
                self.send_response(owner.status);self.send_header('Content-Type','application/json')
                if owner.status==429:self.send_header('Retry-After','17')
                self.end_headers()
                raw={'status':200,'headers':{'content-type':'application/json'},'bodyBase64':base64.b64encode(BODY).decode(),'bytes':len(BODY),'sha256':hashlib.sha256(BODY).hexdigest(),'originalResponseBytes':True}
                if owner.corrupt:raw['sha256']='0'*64
                self.wfile.write(json.dumps({'schemaVersion':1,'provider':'fec','raw':raw}).encode())
        self.server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
        worker=threading.Thread(target=self.server.serve_forever,daemon=True);worker.start()
        self.addCleanup(self.server.server_close);self.addCleanup(worker.join,3);self.addCleanup(self.server.shutdown)
        self.env=patch.dict(os.environ,{'MELANGE_SCRAPE_BROKER_URL':f'http://127.0.0.1:{self.server.server_port}/query','MELANGE_SCRAPE_BROKER_TOKEN':'a'*43})
        self.env.start();self.addCleanup(self.env.stop)

    def test_exact_original_decimal_body_and_repeat_query_survive(self):
        content,status,headers=scrape_client.fetch_raw_url('https://api.open.fec.gov/v1/schedules/schedule_a/?committee_id=C00000001&committee_id=C00000002')
        self.assertEqual((content,status,headers),(BODY,200,{'content-type':'application/json'}))
        self.assertEqual(self.requests[0][1]['query']['committee_id'],['C00000001','C00000002'])
        self.assertEqual(self.requests[0][0]['Authorization'],'Bearer '+'a'*43)

    def test_refuses_corruption_arbitrary_origins_and_credentials(self):
        for url in ('https://evil.invalid/v1/schedules/schedule_a/','https://api.open.fec.gov/v1/schedules/schedule_a/?api_key=secret','http://api.open.fec.gov/v1/schedules/schedule_a/'):
            with self.assertRaises(scrape_client.ScrapeBrokerError):scrape_client.fetch_raw_url(url)
        self.assertEqual(self.requests,[])
        self.corrupt=True
        with self.assertRaises(scrape_client.ScrapeBrokerError):scrape_client.fetch_raw_url('https://api.open.fec.gov/v1/candidates/')

    def test_quota_failure_keeps_retry_and_cannot_fall_back(self):
        self.status=429
        with self.assertRaises(scrape_client.ScrapeBrokerError) as caught:scrape_client.fetch_raw_url('https://api.open.fec.gov/v1/candidates/')
        self.assertEqual((caught.exception.status,caught.exception.retry_after),(429,17));self.assertEqual(len(self.requests),1)

    def test_partial_configuration_is_an_error(self):
        self.assertIsNone(scrape_client.configuration({}))
        for env in ({'MELANGE_SCRAPE_BROKER_TOKEN':'a'*43},{'MELANGE_SCRAPE_BROKER_URL':'http://evil.invalid/query','MELANGE_SCRAPE_BROKER_TOKEN':'a'*43}):
            with self.assertRaises(scrape_client.ScrapeBrokerError):scrape_client.configuration(env)

    def test_congress_collector_uses_original_bytes_and_never_direct_key(self):
        from legislation.collect_official_rollcall_events import HttpFetcher
        source='https://api.congress.gov/v3/bill/119/hr/1/actions?format=json'
        with patch('scrape_client.fetch_raw_url',return_value=(BODY,200,{'content-type':'application/json'})) as fetch,patch('urllib.request.urlopen',side_effect=AssertionError('direct request')):
            response=HttpFetcher('unused-local-key').fetch(source)
        self.assertEqual(response['content'],BODY);fetch.assert_called_once_with(source)

    def test_fec_refresh_skips_key_file_and_caches_exact_original_bytes(self):
        from collect import refresh_fec_money as collector
        body=b'{ "results": [], "pagination": {"count":0,"pages":0} }\n'
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('fec/attic/full_congestion.py','fec/legislators.csv','data/engine/congestion.json'):
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('[]')
            with patch.object(collector,'committee_policy',return_value={'C00000001':'cu'}),patch.object(collector,'candidate_map',return_value={}),patch('scrape_client.fetch_raw_url',return_value=(body,200,{})) as fetch,patch('urllib.request.urlopen',side_effect=AssertionError('direct request')),contextlib.redirect_stdout(io.StringIO()):
                status=collector.main(['--root',str(root),'--no-install','--key-file',str(root/'never-read-key.json')])
            self.assertEqual(status,1) # Empty evidence must keep the last good generation.
            self.assertEqual(fetch.call_count,1)
            pages=list((root/'data/money/fec_page_cache').glob('*.json'))
            originals=[file for file in pages if not file.name.endswith('.receipt.json')]
            self.assertEqual(len(originals),1);self.assertEqual(originals[0].read_bytes(),body)
            self.assertFalse((root/'data/money/fec_refresh_current.json').exists())

    def test_broker_5xx_raises_and_collectors_never_take_the_direct_key_path(self):
        self.status=503
        with self.assertRaises(scrape_client.ScrapeBrokerError) as caught:scrape_client.fetch_raw_url('https://api.open.fec.gov/v1/candidates/')
        self.assertEqual(caught.exception.status,503)
        from legislation.collect_official_rollcall_events import HttpFetcher
        source='https://api.congress.gov/v3/bill/119/hr/1/actions?format=json'
        with patch('urllib.request.urlopen',side_effect=AssertionError('direct request')) as direct:
            with self.assertRaises(scrape_client.ScrapeBrokerError):HttpFetcher('TEST-KEY-0000').fetch(source)
            # an upstream error status passed through the broker is raised too, never retried directly
            with patch('scrape_client.fetch_raw_url',return_value=(b'{}',500,{})):
                with self.assertRaises(scrape_client.ScrapeBrokerError):HttpFetcher('TEST-KEY-0000').fetch(source)
        direct.assert_not_called()
        from collect import refresh_fec_money as collector
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for name in ('fec/attic/full_congestion.py','fec/legislators.csv','data/engine/congestion.json'):
                file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('[]')
            with patch.object(collector,'committee_policy',return_value={'C00000001':'cu'}),patch.object(collector,'candidate_map',return_value={}),\
                 patch('scrape_client.fetch_raw_url',side_effect=scrape_client.ScrapeBrokerError(503)) as fetch,\
                 patch('urllib.request.urlopen',side_effect=AssertionError('direct request')) as direct,\
                 patch.dict(os.environ,{'FEC_API_KEY':'TEST-KEY-0000'}):
                status=collector.main(['--root',str(root),'--no-install','--key-file',str(root/'never-read-key.json')])
            self.assertNotEqual(status,0)
            self.assertGreaterEqual(fetch.call_count,1);direct.assert_not_called()
            self.assertFalse((root/'data/money/fec_refresh_current.json').exists())


    def test_fec_refresh_honors_a_capped_broker_retry_after_and_never_falls_back(self):
        from collect import refresh_fec_money as collector
        body=b'{ "results": [], "pagination": {"count":0,"pages":0} }\n'
        for side_effect,sleeps,calls in (
                ([scrape_client.ScrapeBrokerError(429,7),(body,200,{})],[7],2),          # broker quota, then success
                ([(b'{}',503,{'retry-after':'5'}),(body,200,{})],[5],2),                # upstream 503 passed through
                ([(b'{}',503,{'retry-after':'Fri, 23 Oct 2026 12:00:05 GMT'}),(body,200,{})],[5],2),  # upstream 503 with a future HTTP-date
                ([(b'{}',503,{'retry-after':'soon, maybe'})],[],1),                      # unparsable: no wait
                ([(b'{}',503,{'retry-after':'9'*310})],[],1),                           # decimal too large for a float: unusable, no wait
                ([scrape_client.ScrapeBrokerError(429,301)],[],1),                       # above the cap: no wait
                ([scrape_client.ScrapeBrokerError(429)],[],1),                           # no Retry-After: no wait
                ([scrape_client.ScrapeBrokerError(429,1)]*6,[1]*5,6)):                   # six attempts at most
            with self.subTest(sleeps=sleeps,calls=calls),tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)
                for name in ('fec/attic/full_congestion.py','fec/legislators.csv','data/engine/congestion.json'):
                    file=root/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_text('[]')
                with patch.object(collector,'committee_policy',return_value={'C00000001':'cu'}),patch.object(collector,'candidate_map',return_value={}),\
                     patch('scrape_client.fetch_raw_url',side_effect=side_effect) as fetch,patch.object(collector.time,'sleep') as sleep,patch.object(scrape_client,'_now',return_value=datetime.datetime(2026,10,23,12,0,0,tzinfo=datetime.timezone.utc)),\
                     patch('urllib.request.urlopen',side_effect=AssertionError('direct request')) as direct,contextlib.redirect_stdout(io.StringIO()):
                    collector.main(['--root',str(root),'--no-install','--key-file',str(root/'never-read-key.json')])
                self.assertEqual(fetch.call_count,calls);self.assertEqual([c.args[0] for c in sleep.call_args_list],sleeps);direct.assert_not_called()
                cached=[f for f in (root/'data/money/fec_page_cache').glob('*.json') if not f.name.endswith('.receipt.json')]
                self.assertEqual(len(cached),1 if calls==2 else 0)


if __name__=='__main__':unittest.main()
