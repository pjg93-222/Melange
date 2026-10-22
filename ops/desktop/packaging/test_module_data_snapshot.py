import copy
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from module_data_snapshot import Snapshot,parse,validate_snapshot,main,regular
from module_data_test_helpers import graph_fixture

class BoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.f=graph_fixture(self.temp.name)
    def test_missing_unknown_or_duplicate_role_is_refused(self):
        for change in ('missing','unknown','duplicate'):
            request=copy.deepcopy(self.f.request)
            if change=='missing':request['objects'].pop()
            elif change=='unknown':request['objects'][0]['role']='accounts'
            else:request['objects'][0]['role']=request['objects'][1]['role']
            with self.assertRaises(ValueError):Snapshot(request)
    def test_changed_same_length_bytes_fail_even_with_preserved_mtime(self):
        p=self.f.path('edges');before=p.stat();raw=p.read_bytes();p.write_bytes(bytes([raw[0]^1])+raw[1:]);os.utime(p,ns=(before.st_atime_ns,before.st_mtime_ns))
        with self.assertRaises(ValueError):Snapshot(self.f.request)
    def test_source_code_may_not_be_taken_from_the_data_snapshot(self):
        request={**self.f.request,'sourceRoot':str(self.f.root)}
        with self.assertRaises(ValueError):Snapshot(request)
    def test_supplied_role_path_must_be_exact_compiled_location(self):
        self.f.request['files']['edges']=str(Path(self.temp.name)/'outside.bin')
        with self.assertRaises(ValueError):Snapshot(self.f.request)
    def test_duplicate_or_nonfinite_metadata_is_refused(self):
        for value in (b'{"role":1,"role":2}',b'{"x":NaN}',b'{"x":[1e9999]}',b'{"x":-1e9999}',b'{"__proto__":{}}',b'{} trailing'):
            with self.assertRaises((ValueError,json.JSONDecodeError)):parse(value)
    def test_payload_bytes_must_use_the_real_readers_strict_utf8(self):
        for raw in ('{"fixture":0}'.encode('utf-16'),b'\xef\xbb\xbf{}',b'{"x":"\xff"}'):
            with self.assertRaises(ValueError):parse(raw)
    def test_windows_reparse_attribute_is_refused(self):
        original=Path.lstat;target=self.f.path('edges')
        def info(path,*args,**kwargs):
            result=original(path,*args,**kwargs)
            if path==target:
                class Reparse:
                    st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT
                    st_mode=result.st_mode
                return Reparse()
            return result
        with patch.object(Path,'lstat',info):
            with self.assertRaises(ValueError):regular(target)
    def test_node_and_python_compiled_roles_agree(self):
        from module_data_snapshot import KINDS
        client=Path(__file__).resolve().parents[1]/'client/module-data-adapters.cjs'
        output=subprocess.run(['node','-e','const m=require(process.argv[1]);process.stdout.write(JSON.stringify({...m.ROLE_MAPS,...m.PUBLIC_ROLES}))',str(client)],capture_output=True,check=True,timeout=20)
        actual=json.loads(output.stdout)
        expected={kind:{role:{'path':value[0],'maxBytes':value[1]} for role,value in roles.items()} for kind,(_app,roles) in KINDS.items()}
        self.assertEqual(actual,expected)

if __name__=='__main__':unittest.main()
