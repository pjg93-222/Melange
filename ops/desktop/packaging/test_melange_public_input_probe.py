"""Actual Melange pure metadata validator with entirely fabricated observations."""
import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import melange_public_provenance as p
import melange_public_payroll_projection as projection
from module_data_snapshot import Snapshot
from module_public_input_installers import validate_public_snapshot, prepare_public_component
from test_melange_public_payroll_normalize import actual_fixture

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from fec.surfaces import melange_public_data as public


class ActualMelangeProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name).resolve();self.original=self.base/'generated-originals';self.original.mkdir()
        self.source=self.base/'program';self.source.mkdir();self.root=self.base/'snapshot';self.root.mkdir()
        (self.root/'public-data').mkdir();self.data=self.root/'public-data/observations.ndjson'
        plan,_=actual_fixture(self.original)
        with p.validated_inputs(self.original,plan) as inputs:self.receipt=projection.project_observations(inputs,self.data)

    def snapshot(self):
        (self.root/'public-data/receipt.json').write_bytes(p.canonical(self.receipt)+b'\n')
        files={};objects=[]
        for role,name in (('observations','observations.ndjson'),('receipt','receipt.json')):
            path=self.root/'public-data'/name;raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest();files[role]=str(path)
            objects.append({'role':role,'bytes':len(raw),'sha256':sha,
                'segments':[{'asset':role+'.bin','bytes':len(raw),'sha256':sha}]})
        return Snapshot({'appId':'melange','kind':public.KIND,'sourceRoot':str(self.source),
            'snapshotRoot':str(self.root),'files':files,'objects':objects})

    def test_actual_typed_receipt_passes_without_full_catalogue(self):
        snapshot=self.snapshot()
        with patch('module_public_input_installers._program_module',return_value=public),\
             patch.object(public,'prepare_public_data',side_effect=AssertionError('Full reader entered')):
            validate_public_snapshot(snapshot)

    def test_row_validation_remains_required_only_in_actual_full_preparation(self):
        raw=b'NOT VALID NDJSON\n';self.data.write_bytes(raw)
        self.receipt['output'].update(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        snapshot=self.snapshot()
        with patch('module_public_input_installers._program_module',return_value=public):
            validate_public_snapshot(snapshot)
            with self.assertRaises(ValueError):
                prepare_public_component(snapshot,source={'appId':'melange','manifestSha256':'0'*64})

    def test_receipt_unknown_fields_promotions_urls_and_hash_bindings_refuse(self):
        original=copy.deepcopy(self.receipt)
        for mutate in (lambda r:r.update(localPath='C:/private'),
            lambda r:r['canonicalPromotions'].update(identity=False),
            lambda r:r['sourceManifest']['documents'][0].update(url='https://untrusted.invalid/a'),
            lambda r:r['output'].update(sha256='0'*64),lambda r:r.update(programFingerprint='0'*64),
            lambda r:r['coverage'].update(fullApplication=True)):
            self.receipt=copy.deepcopy(original);mutate(self.receipt);snapshot=self.snapshot()
            with self.subTest(mutate=mutate),patch('module_public_input_installers._program_module',return_value=public):
                with self.assertRaises(ValueError):validate_public_snapshot(snapshot)


if __name__=='__main__':unittest.main()
