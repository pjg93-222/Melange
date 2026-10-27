import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import directory_zip
import native_extract_directory as native


@unittest.skipUnless(os.name=='nt','Windows file-sharing locks')
class HeldInputTests(unittest.TestCase):
    def test_held_input_denies_writes_and_replacement_but_releases_afterward(self):
        with tempfile.TemporaryDirectory(prefix='native-extract-lock-') as folder:
            root=Path(folder).resolve();file=root/'input.bin';file.write_bytes(b'original')
            with native.held_read(file) as stream:
                self.assertEqual(stream.read(),b'original')
                with self.assertRaises(PermissionError): file.write_bytes(b'changed')
                with self.assertRaises(PermissionError): file.rename(root/'renamed.bin')
            file.write_bytes(b'changed')


@unittest.skipUnless(os.name=='nt' and os.environ.get('NATIVE_EXTRACT_7ZA'),'Set reviewed NATIVE_EXTRACT_7ZA')
class NativeExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='native-extract-fixture-');self.root=Path(self.temp.name).resolve()
        self.source=self.root/'source'
        for name,data in {'Melange.exe':b'MZ fixture','resources/app.asar':b'ASAR fixture','resources/runtime/melange/nested/café.txt':b'Unicode runtime file'}.items():
            file=self.source/name;file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(data)
        self.archive=self.root/'package.zip';self.descriptor=directory_zip.build(self.source,self.archive,'melange','1.0.20')
        self.client=Path(__file__).resolve().parents[1]/'client'
        self.tool=Path(os.environ['NATIVE_EXTRACT_7ZA']).resolve();self.tool_hash=hashlib.sha256(self.tool.read_bytes()).hexdigest()

    def tearDown(self): self.temp.cleanup()

    def extract(self,destination,descriptor=None,tool_hash=None):
        return native.extract(self.client,self.archive,destination,descriptor or self.descriptor,self.tool,tool_hash or self.tool_hash)

    def test_real_locked_native_extraction_passes_existing_full_verifier(self):
        destination=self.root/'program';inventory=self.extract(destination)
        for row in inventory['files']: self.assertEqual((destination/row['path']).read_bytes(),(self.source/row['path']).read_bytes())
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(),self.descriptor['sha256'])

    def test_refuses_existing_tree_bad_hash_and_changed_tool(self):
        existing=self.root/'existing';existing.mkdir();(existing/'sentinel').write_bytes(b'preserve')
        with self.assertRaisesRegex(ValueError,'already exists'): self.extract(existing)
        self.assertEqual((existing/'sentinel').read_bytes(),b'preserve')
        target=self.root/'not-created'
        with self.assertRaisesRegex(ValueError,'hash changed'): self.extract(target,{**self.descriptor,'sha256':'0'*64})
        self.assertFalse(target.exists())
        with self.assertRaisesRegex(ValueError,'extractor changed'): self.extract(target,tool_hash='0'*64)
        self.assertFalse(target.exists())

    def test_extra_native_output_fails_existing_exact_inventory_check(self):
        original=native.subprocess.run;destination=self.root/'program'
        def run(command,*args,**kwargs):
            result=original(command,*args,**kwargs)
            if command[0]==str(self.tool): (destination/'extra.dll').write_bytes(b'unlisted')
            return result
        with patch.object(native.subprocess,'run',run),self.assertRaisesRegex(ValueError,'unexpected installed file'):
            self.extract(destination)
        self.assertTrue((destination/'extra.dll').exists())


if __name__=='__main__': unittest.main()
