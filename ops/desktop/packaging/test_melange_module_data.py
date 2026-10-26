"""Real installed-reader code over synthetic, fully bound immutable snapshots."""
import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from module_data_snapshot import validate_snapshot, LimitedGzip
from module_data_test_helpers import graph_fixture,payroll_fixture,repin_payroll
from melange_module_data import bounded_rows,configure_readers

class GraphTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.f=graph_fixture(self.temp.name)
    def test_real_graph_reader_accepts_closed_aliases_without_original_paths(self):
        result=validate_snapshot(self.f.request)
        self.assertEqual(result['coverage'],{'completeKind':True,'fullApplication':False})
    def test_scoped_graph_factory_ignores_original_state_paths(self):
        original=Path(self.temp.name)/'original-state';original.mkdir();sentinel=original/'assertions.json';sentinel.write_bytes(b'unchanged')
        bound=configure_readers(self.f.request)
        self.assertIs(bound['graph_factory'](original),bound['graph'])
        self.assertEqual(sentinel.read_bytes(),b'unchanged')
        self.assertFalse(bound['coverage']['fullApplication'])
    def test_signed_metadata_cannot_omit_generation_role_or_inject_path(self):
        for change in ('omit','path'):
            receipt=json.loads(self.f.path('graph-receipt').read_bytes())
            if change=='omit':receipt['files'].pop()
            else:receipt['files'][0]['path']='../../accounts.sqlite3'
            self.f.write('graph-receipt',receipt)
            with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_twin_receipt_must_bind_actual_generation_bytes(self):
        verification=json.loads(self.f.path('graph-verification').read_bytes())
        verification['twin_byte_identity'][0]['primary_sha256']='f'*64
        self.f.write('graph-verification',verification)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_reader_failure_is_not_reported_as_complete_kind(self):
        self.f.write('node-scores',b'not-json\n',True)
        receipt=json.loads(self.f.path('graph-receipt').read_bytes())
        for spec in receipt['files']:
            if spec['role']=='staffer_social_node_scores':spec.update(sha256=self.f.spec('node-scores')['sha256'],bytes=self.f.spec('node-scores')['bytes'])
        self.f.write('graph-receipt',receipt)
        v=json.loads(self.f.path('graph-verification').read_bytes());row=v['twin_byte_identity'][0]
        row['primary_sha256']=row['twin_sha256']=self.f.spec('graph-receipt')['sha256'];self.f.write('graph-verification',v)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_many_tiny_rows_are_bounded_before_reader_indexes_grow(self):
        path=Path(self.temp.name)/'many.bin';path.write_bytes(gzip.compress(b'{}\n'*3))
        with self.assertRaises(ValueError):list(bounded_rows(path,max_records=2))

class PayrollTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.f=payroll_fixture(self.temp.name)
    def test_real_payroll_reader_uses_all_five_compiled_sources(self):
        self.assertTrue(validate_snapshot(self.f.request)['validated'])
    def test_scoped_payroll_loader_cannot_follow_original_or_caller_config(self):
        bound=configure_readers(self.f.request)
        self.assertEqual(bound['payroll_loader']('/never-read-original',config_path='/outside/accounts.sqlite3')['counts'],{'episodes':0})
        self.assertFalse(bound['coverage']['fullApplication'])
    def test_missing_or_extra_source_binding_rejects_even_with_rebound_hashes(self):
        bundle=json.loads(gzip.decompress(self.f.path('evidence').read_bytes()))
        for bindings in (bundle['sources'][:-1],bundle['sources']+[{'path':'/outside/accounts.sqlite3','sha256':'0'*64}]):
            changed={**bundle,'sources':bindings};repin_payroll(self.f,changed)
            with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_absolute_reference_never_becomes_unconfined_io(self):
        bundle=json.loads(gzip.decompress(self.f.path('evidence').read_bytes()))
        bundle['sources'][0]['path']='/outside/../../accounts.sqlite3';repin_payroll(self.f,bundle)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_source_bytes_must_match_evidence_binding_not_just_manifest(self):
        self.f.write('hill-spans',b'changed fixture source')
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_fixed_format_gzip_has_a_decompressed_byte_limit(self):
        path=Path(self.temp.name)/'bounded.bin';path.write_bytes(gzip.compress(b'x'*65))
        with LimitedGzip(path,64) as stream:
            with self.assertRaises(ValueError):stream.read()
    def test_numeric_overflow_cannot_pass_an_otherwise_bound_reader_bundle(self):
        raw=gzip.decompress(self.f.path('evidence').read_bytes()).replace(b'"episodes":0',b'"episodes":1e9999')
        self.f.write('evidence',raw,True)
        self.f.write('config',{'path':__import__('melange_module_data').PAYROLL_EVIDENCE,'sha256':self.f.spec('evidence')['sha256']})
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_utf16_cannot_pass_a_reader_that_requires_utf8(self):
        raw=gzip.decompress(self.f.path('evidence').read_bytes()).decode('utf-8').encode('utf-16')
        self.f.write('evidence',raw,True)
        self.f.write('config',{'path':__import__('melange_module_data').PAYROLL_EVIDENCE,'sha256':self.f.spec('evidence')['sha256']})
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)

if __name__=='__main__':unittest.main()
