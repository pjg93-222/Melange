"""Generated stage-phase integrity fixtures; no real rows or application boot."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from module_data_snapshot import KINDS, Snapshot, parse
from module_public_input_installers import validate_public_snapshot


class PublicProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.root=self.base/'snapshot';self.source=self.base/'program'
        self.root.mkdir();self.source.mkdir();self.kind='mentat.public-fec-tables.v1'
        self.docs={};self.raw={}
        for role,(name,_limit) in KINDS[self.kind][1].items():
            if role=='mentat.fec.provenance':continue
            raw=b'NOT A VALID FEC ROW\n';self.raw[role]=raw
            self.docs[role]={'memberBytes':len(raw),'memberSha256':hashlib.sha256(raw).hexdigest()}
        self.raw['mentat.fec.provenance']=json.dumps(self.docs).encode()
        def receipt(raw):
            value=parse(raw)
            if type(value) is not dict or set(value)!=set(self.docs):raise ValueError('Generated receipt schema')
            return value,value
        self.module=SimpleNamespace(_receipt=receipt)
        self.write()

    def write(self):
        files={};objects=[]
        for role,(name,_limit) in KINDS[self.kind][1].items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(self.raw[role])
            sha=hashlib.sha256(self.raw[role]).hexdigest();files[role]=str(path)
            objects.append({'role':role,'bytes':len(self.raw[role]),'sha256':sha,
                'segments':[{'asset':f'part-{len(objects)}.bin','bytes':len(self.raw[role]),'sha256':sha}]})
        self.snapshot=Snapshot({'appId':'mentat','kind':self.kind,'sourceRoot':str(self.source),
            'snapshotRoot':str(self.root),'files':files,'objects':objects})

    def probe(self,**kwargs):
        with patch('module_public_input_installers._program_module',return_value=self.module),\
             patch('module_public_input_installers.prepare_public_component',side_effect=AssertionError('Full reader entered')):
            return validate_public_snapshot(self.snapshot,**kwargs)

    def test_stage_probe_hashes_closed_tree_and_receipt_without_parsing_rows_or_constructing_reader(self):
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.root.rglob('*') if p.is_file()}
        self.probe()
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before})

    def test_receipt_binding_drift_is_refused_even_with_fresh_snapshot_hashes(self):
        self.docs[next(iter(self.docs))]['memberSha256']='0'*64
        self.raw['mentat.fec.provenance']=json.dumps(self.docs).encode();self.write()
        with self.assertRaises(ValueError):self.probe()

    def test_duplicate_or_unknown_receipt_metadata_is_refused(self):
        for raw in (b'{"x":1,"x":2}',b'{"extra":1}'):
            self.raw['mentat.fec.provenance']=raw;self.write()
            with self.assertRaises(ValueError):self.probe()

    def test_changed_same_length_bytes_after_snapshot_are_refused(self):
        path=self.snapshot.files[next(iter(self.docs))];before=path.stat();raw=path.read_bytes()
        path.write_bytes(b'X'+raw[1:]);os.utime(path,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaises(ValueError):self.probe()

    def test_foreign_file_or_extra_directory_is_refused_without_deletion(self):
        foreign=self.root/'foreign';foreign.mkdir();marker=foreign/'keep';marker.write_bytes(b'keep')
        with self.assertRaises(ValueError):self.probe()
        self.assertEqual(marker.read_bytes(),b'keep')

    def test_hardlink_is_refused_and_foreign_link_is_preserved(self):
        path=self.snapshot.files[next(iter(self.docs))];foreign=self.base/'foreign';os.link(path,foreign)
        with self.assertRaises(ValueError):self.probe()
        self.assertEqual(foreign.read_bytes(),path.read_bytes())

    def test_cancel_before_import_or_between_objects_never_constructs_consumer(self):
        with patch('module_public_input_installers._program_module',side_effect=AssertionError('Import entered')):
            with self.assertRaises(ValueError):validate_public_snapshot(self.snapshot,is_cancelled=lambda:True)
        calls=0
        def cancelled():
            nonlocal calls
            calls+=1;return calls>=3
        with self.assertRaises(ValueError):self.probe(is_cancelled=cancelled)
        self.assertEqual(calls,3)

    def test_mutation_during_metadata_validation_is_refused(self):
        original=self.module._receipt
        def changed(raw):
            result=original(raw);self.snapshot.files[next(iter(self.docs))].write_bytes(b'changed');return result
        self.module._receipt=changed
        with self.assertRaises(ValueError):self.probe()


if __name__=='__main__':unittest.main()
