import csv
import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from bs4 import BeautifulSoup

p=Path(__file__).with_name('collect_opensecrets.py')
spec=importlib.util.spec_from_file_location('collector',p)
c=importlib.util.module_from_spec(spec); spec.loader.exec_module(c)

class CollectorTests(unittest.TestCase):
    def test_money_preserves_missing_zero_negative(self):
        self.assertIsNone(c.money('N/A'))
        self.assertEqual(c.money('$0'),0)
        self.assertEqual(c.money('-$2,900'),-2900)
        self.assertEqual(c.money('($2,900)'),-2900)
        self.assertEqual(c.money('44.27%'),44.27)
        with self.assertRaises(ValueError): c.money('not disclosed')

    def test_cycle_fallback_rejected(self):
        soup=BeautifulSoup('<select name="cycle"><option selected>All</option><option>2024</option></select>','html.parser')
        self.assertFalse(c.Collector.period_ok(None,soup,2026))
        soup=BeautifulSoup('<select name="cycle"><option selected>2024</option></select>','html.parser')
        self.assertTrue(c.Collector.period_ok(None,soup,2024))
        self.assertFalse(c.Collector.period_ok(None,soup,2026))

    def test_generic_redirect_rejected(self):
        soup=BeautifulSoup('<title>Industries - OpenSecrets</title>','html.parser')
        self.assertFalse(c.Collector.industry_ok(None,soup,c.SCOPES[0]))

    def test_real_nominal_source(self):
        import hashlib
        url='https://www.opensecrets.org/elections-overview/cost-of-election?infl=N'
        path=p.parent/'probe_cache'/(hashlib.sha256(url.encode()).hexdigest()[:16]+'.html')
        soup=BeautifulSoup(path.read_text(encoding='utf-8'),'html.parser')
        checkbox=soup.select_one('input[name=infl]')
        self.assertEqual(checkbox['value'],'N')
        self.assertFalse(checkbox.has_attr('checked'))
        rr=c.rows(soup.select_one('table'))
        row=next(r for r in rr if r[0]=='2008*')
        self.assertEqual(c.money(row[1]),5285680883)

def winerr(code):
    exc=PermissionError(13,'Access is denied'); exc.winerror=code
    return exc

class FlakyReplace:
    """Fails the first `failures` calls with `error`, then delegates to os.replace."""
    def __init__(self,failures,error):
        self.failures,self.error,self.calls=failures,error,0
    def __call__(self,src,dst):
        self.calls+=1
        if self.calls<=self.failures: raise self.error
        os.replace(src,dst)

class AtomicReplaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.dir=Path(self.tmp.name)
        self.sleeps=[]
    def tearDown(self): self.tmp.cleanup()
    def read_csv(self):
        with open(self.dir/'t.csv',encoding='utf-8-sig',newline='') as handle: return list(csv.DictReader(handle))

    @unittest.skipUnless(os.name=='nt','real Windows sharing violation')
    def test_real_reader_lock_released_midway(self):
        import threading
        dst=self.dir/'t.csv'; dst.write_text('a\nold\n',encoding='utf-8')
        reader=open(dst,'rb')
        threading.Timer(0.5,reader.close).start()
        c.put_csv(dst,['a'],[{'a':'new'}])
        self.assertEqual(self.read_csv(),[{'a':'new'}])

    @unittest.skipUnless(os.name=='nt','real Windows sharing violation')
    def test_real_reader_lock_persistent_fails(self):
        dst=self.dir/'t.csv'; dst.write_text('a\nold\n',encoding='utf-8')
        with open(dst,'rb'):
            with self.assertRaises(PermissionError): c.put_csv(dst,['a'],[{'a':'new'}],attempts=3,base_delay=0.01,max_delay=0.02)
        self.assertEqual(self.read_csv(),[{'a':'old'}])

    def test_success_after_transient_winerror(self):
        for code in (5,32,33):
            dst=self.dir/f'a{code}.csv'; dst.write_text('old',encoding='utf-8')
            src=self.dir/f'a{code}.csv.tmp'; src.write_text('new',encoding='utf-8')
            flaky=FlakyReplace(3,winerr(code))
            c.replace_with_retry(src,dst,sleep=self.sleeps.append,replace=flaky)
            self.assertEqual(flaky.calls,4)
            self.assertEqual(dst.read_text(encoding='utf-8'),'new')
            self.assertFalse(src.exists())
        self.assertTrue(self.sleeps and max(self.sleeps)<=2.0)

    def test_persistent_error_fails_bounded_and_keeps_destination(self):
        dst=self.dir/'b.csv'; dst.write_text('old',encoding='utf-8')
        src=self.dir/'b.csv.tmp'; src.write_text('new',encoding='utf-8')
        flaky=FlakyReplace(10**6,winerr(5))
        with self.assertRaises(PermissionError):
            c.replace_with_retry(src,dst,attempts=5,sleep=self.sleeps.append,replace=flaky)
        self.assertEqual(flaky.calls,5)
        self.assertEqual(len(self.sleeps),4)
        self.assertEqual(dst.read_text(encoding='utf-8'),'old')

    def test_non_transient_errors_not_retried(self):
        for error in (winerr(2),PermissionError(13,'no winerror'),FileNotFoundError(2,'gone'),OSError(5,'io')):
            flaky=FlakyReplace(10**6,error); self.sleeps.clear()
            with self.assertRaises(type(error)):
                c.replace_with_retry(self.dir/'x',self.dir/'y',sleep=self.sleeps.append,replace=flaky)
            self.assertEqual(flaky.calls,1); self.assertEqual(self.sleeps,[])

    def test_put_csv_and_json_retry_and_stay_atomic(self):
        flaky=FlakyReplace(2,winerr(5))
        orig=c.replace_with_retry
        c.replace_with_retry=lambda s,d,**kw: orig(s,d,sleep=self.sleeps.append,replace=flaky,**kw)
        try:
            c.put_csv(self.dir/'t.csv',['a','b'],[{'a':1,'b':'x'}])
            self.assertEqual(flaky.calls,3)
            self.assertEqual(self.read_csv(),[{'a':'1','b':'x'}])
            flaky.calls=0; flaky.failures=2
            c.put_json(self.dir/'t.json',{'k':1})
            self.assertEqual(json.loads((self.dir/'t.json').read_text(encoding='utf-8')),{'k':1})
            flaky.calls=0; flaky.failures=10**6
            with self.assertRaises(PermissionError): c.put_csv(self.dir/'t.csv',['a','b'],[{'a':2,'b':'y'}])
            self.assertEqual(self.read_csv()[0]['a'],'1')
        finally: c.replace_with_retry=orig

class CandidatePartyTests(unittest.TestCase):
    def test_codes(self):
        self.assertEqual(c.candidate_party('Smith, Jane (D-CA)'),'D')
        self.assertEqual(c.candidate_party('Smith, John (R-TX)'),'R')
        self.assertEqual(c.candidate_party('Walker, January (3-UT)'),'3')
        self.assertEqual(c.candidate_party('Obama, Barack (D)'),'D')
        self.assertEqual(c.candidate_party('No Party Shown'),'')
        self.assertEqual(c.candidate_party('Name (Jr.) Smith'),'')

def stub_collector(html,url):
    col=object.__new__(c.Collector)
    col.data={k:[] for k in c.SCHEMAS}
    meta={k:'' for k in c.COMMON}; meta.update(source_url=url,capture_date='2026-10-01',capture_utc='2026-10-01T00:00:00+00:00',status='observed')
    col.fetch=lambda path,family='public':(BeautifulSoup(html,'html.parser'),meta)
    return col

class ReconciliationTests(unittest.TestCase):
    def test_citigroup_preserved_and_flagged(self):
        row={'total_usd':4112319,'candidates_parties_usd':4112319,'outside_groups_usd':9000}
        out=c.contributor_reconciliation(row)
        self.assertEqual(out['reconciliation_delta_usd'],-9000)
        self.assertEqual(out['source_reconciliation_status'],'published_columns_not_additive_review')
        self.assertIn('not assumed',out['source_reconciliation_notes'])
        self.assertEqual(row,{'total_usd':4112319,'candidates_parties_usd':4112319,'outside_groups_usd':9000})

    def test_consistent_and_uncheckable(self):
        self.assertEqual(c.contributor_reconciliation({'total_usd':10,'candidates_parties_usd':4,'outside_groups_usd':6})['source_reconciliation_status'],'published_columns_consistent')
        out=c.contributor_reconciliation({'total_usd':10,'candidates_parties_usd':10})
        self.assertIsNone(out['reconciliation_delta_usd']); self.assertEqual(out['source_reconciliation_status'],'not_checkable')

    def test_real_2008_f03_raw_capture(self):
        raw=p.parent/'raw'/'1380c9d0b13d34b4b4d5512aefe43e715310b119d24f06d6ae79d7abba4bf5f7.html'
        if not raw.exists(): self.skipTest('raw capture absent')
        col=stub_collector(raw.read_text(encoding='utf-8'),'https://www.opensecrets.org/industries/contrib?ind=F03&cycle=2008')
        col.contributors(c.SCOPES[0],2008)
        cit=next(r for r in col.data['top_contributors'] if r['organisation']=='Citigroup Inc')
        self.assertEqual((cit['total_usd'],cit['candidates_parties_usd'],cit['outside_groups_usd']),(4112319,4112319,9000))
        self.assertEqual(cit['reconciliation_delta_usd'],-9000)
        self.assertEqual(cit['source_reconciliation_status'],'published_columns_not_additive_review')

SPLIT_PAGE='<title>{t} Industry Profile</title><select name="cycle"><option selected>2024</option></select><table><tr><th>Rank</th><th>Contributor</th><th>Grand Total</th>{extra_h}</tr><tr><td>1</td><td>Org</td><td>$5</td>{extra_d}</tr></table>'

class SplitCoverageTests(unittest.TestCase):
    def gaps(self,html):
        col=stub_collector(html,'u'); col.contributors(c.SCOPES[0],2024)
        return [g for g in col.data['coverage'] if g['field']=='pac_usd;individual_usd'],col
    def test_gap_reported_when_rows_lack_split(self):
        g,col=self.gaps(SPLIT_PAGE.format(t='Commercial Banks',extra_h='',extra_d=''))
        self.assertEqual(len(g),1); self.assertEqual(col.data['top_contributors'][0]['pac_individual_split_status'],'not_published_on_contributor_page')
    def test_no_gap_when_rows_have_split(self):
        g,col=self.gaps(SPLIT_PAGE.format(t='Commercial Banks',extra_h='<th>PACs</th><th>Individuals</th>',extra_d='<td>$2</td><td>$3</td>'))
        self.assertEqual(g,[]); self.assertEqual(col.data['top_contributors'][0]['pac_individual_split_status'],'observed')

class SchemaTests(unittest.TestCase):
    def test_no_duplicate_fields(self):
        for name,fields in c.SCHEMAS.items(): self.assertEqual(len(fields),len(set(fields)),name)
    def test_reconciliation_fields_in_top_contributors(self):
        for f in ('reconciliation_delta_usd','source_reconciliation_status','source_reconciliation_notes'): self.assertIn(f,c.SCHEMAS['top_contributors'])

if __name__=='__main__': unittest.main()
