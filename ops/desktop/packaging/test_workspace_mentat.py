"""Portable security boundaries; actual accounting-data parity is a separate gate."""
import hashlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from module_application_contracts import DataIntakeBlocked, ModuleInputError, ProgramFile
import workspace_mentat as workspace


class MentatWorkspaceGuards(unittest.TestCase):
    def test_signed_receipt_parser_rejects_duplicate_prototype_nonfinite_and_oversize(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            for raw in (b'{"a":1,"a":2}', b'{"__proto__":{}}', b'{"value":NaN}', b'['*80+b']'*80):
                path.write_bytes(raw)
                with self.assertRaises(DataIntakeBlocked): workspace.read_json(path)
            path.write_bytes(b'{"value":1}')
            with self.assertRaises(DataIntakeBlocked): workspace.read_json(path, maximum=2)

    def test_direct_fact_path_keeps_actual_fact_and_actual_receipt_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            data, receipt = Path(directory)/'index.sqlite', Path(directory)/'receipt.json'
            data.write_bytes(b'actual fact fixture')
            receipt.write_bytes(b'actual receipt fixture')
            alias = workspace._FactPath(data, receipt)
            self.assertEqual(Path(alias).read_bytes(), b'actual fact fixture')
            self.assertEqual(alias.with_suffix('.json').read_bytes(), b'actual receipt fixture')
            with self.assertRaises(ModuleInputError): alias.with_suffix('.py')

    def test_exact_program_bytes_and_late_imports_stay_isolated_from_original_modules(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root/'mentat/app'
            app.mkdir(parents=True)
            tools = root/'mentat/tools'
            tools.mkdir()
            (tools/'cross_reference_engine.py').write_bytes(b'# program-only fixture\n')
            programs = {'contribution_data': b"VALUE='native fixture'\ndef read(): return VALUE\n",
                        'analysis_data': b'def read():\n import contribution_data\n return contribution_data.read()\n'}
            files = []
            for name, raw in programs.items():
                (app/(name+'.py')).write_bytes(raw)
                files.append(ProgramFile('source', 'mentat/app/'+name+'.py', len(raw), hashlib.sha256(raw).hexdigest()))
            fixture = SimpleNamespace(source_file=lambda relative: root/relative)
            original = SimpleNamespace(read=lambda: 'original private module')
            with patch.object(workspace, '_MODULES', tuple(programs)), patch.dict(sys.modules, {'contribution_data': original}):
                isolated = workspace.isolated_programs(fixture, program_files=tuple(files))
                self.assertIs(sys.modules['contribution_data'], original)
                self.assertEqual(isolated['analysis_data'].read(), 'native fixture')
                (app/'contribution_data.py').write_bytes(b"raise RuntimeError('unverified code executed')\n")
                with self.assertRaises(ModuleInputError): workspace.isolated_programs(fixture, program_files=tuple(files))
                self.assertIs(sys.modules['contribution_data'], original)


if __name__ == '__main__': unittest.main()
