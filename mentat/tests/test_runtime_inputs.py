"""Selected-cycle snapshots retain evidence and remain private to the run."""
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT / 'tools'))
from runtime_inputs import copy_fec_sources


class RuntimeInputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / 'source'
        self.required = {}
        for cycle in (2022, 2024, 2026):
            suffix = str(cycle)[2:]
            paths = [f'fec_committee_master/cm{suffix}/cm.txt']
            paths += [f'fec_beneficiary/{prefix}{suffix}/{name}' for prefix, name in
                      [('cn', 'cn.txt'), ('ccl', 'ccl.txt'), ('pas2', 'itpas2.txt'), ('oth', 'itoth.txt')]]
            paths += [f'fec_beneficiary/leadership{cycle}.csv',
                      f'fec_beneficiary/oth{suffix}/source-receipt.json',
                      f'fec_beneficiary/oth{suffix}/transfer-current.json',
                      f'fec_beneficiary/oth{suffix}/published/transfer-edges.csv']
            self.required[cycle] = paths
        for relative in sum(self.required.values(), []) + ['fec_beneficiary/shared.json',
                                                          'fec_beneficiary/cache/scratch',
                                                          'fec_beneficiary/oth26/lookup.sqlite']:
            path = self.source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(relative, encoding='utf-8')

    def test_every_cycle_selection_preserves_evidence_and_copy_isolation(self):
        for count in (1, 2, 3):
            for cycles in itertools.combinations(self.required, count):
                with self.subTest(cycles=cycles):
                    destination = self.root / '-'.join(map(str, cycles))
                    copy_fec_sources(self.source, destination, cycles)
                    for cycle, paths in self.required.items():
                        for relative in paths:
                            target = destination / relative
                            self.assertEqual(target.exists(), cycle in cycles, relative)
                            if cycle in cycles:
                                self.assertEqual(target.read_bytes(), (self.source / relative).read_bytes())
                    self.assertTrue((destination / 'fec_beneficiary/shared.json').is_file())
                    self.assertFalse((destination / 'fec_beneficiary/cache').exists())
                    self.assertFalse((destination / 'fec_beneficiary/oth26/lookup.sqlite').exists())
                    relative = self.required[cycles[0]][0]
                    (destination / relative).write_text('private edit')
                    self.assertEqual((self.source / relative).read_text(), relative)

    def test_invalid_selection_fails_before_copying(self):
        for cycles in ([], [2028], [2026, 2028]):
            with self.assertRaises(ValueError):
                copy_fec_sources(self.source, self.root / 'invalid', cycles)
            self.assertFalse((self.root / 'invalid').exists())

    @unittest.skipUnless(os.name == 'nt', 'PowerShell report build contract')
    def test_report_required_inputs_match_each_selected_snapshot(self):
        builder = (PROJECT / 'tools/build_industry_report.ps1').read_text(encoding='utf-8-sig')
        block = builder[builder.index('$inputCycles ='):builder.index('foreach ($requiredPath')]
        script = self.root / 'check-inputs.ps1'
        script.write_text("param([string]$Snapshot)\n$ErrorActionPreference = 'Stop'\n"
                          "$CommitteeMasterDirectory = Join-Path $Snapshot 'fec_committee_master'\n"
                          "$BeneficiaryDirectory = Join-Path $Snapshot 'fec_beneficiary'\n"
                          "$results = @(foreach ($CycleLabel in @('2021-2022','2023-2024','2025-2026','')) {\n"
                          + block + "\n[pscustomobject]@{label=$CycleLabel; files=@($committeeFiles)+@($beneficiaryFiles)}\n})\n"
                          "$results | ConvertTo-Json -Depth 4\n", encoding='utf-8')
        process = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(script), '-Snapshot', str(self.source)],
                                 capture_output=True, text=True, timeout=30)
        self.assertEqual(process.returncode, 0, process.stderr)
        for row in json.loads(process.stdout):
            cycles = [int(row['label'][-4:])] if row['label'] else [2022, 2024, 2026]
            self.assertEqual(len(row['files']), 5 * len(cycles))
            destination = self.root / ('build-' + (row['label'] or 'all'))
            copy_fec_sources(self.source, destination, cycles)
            for name in row['files']:
                relative = Path(name).relative_to(self.source)
                self.assertTrue((destination / relative).is_file(), name)


if __name__ == '__main__':
    unittest.main()
