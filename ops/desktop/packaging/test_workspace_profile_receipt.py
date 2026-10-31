import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from module_application_contracts import DataIntakeBlocked
from workspace_melange import MelangeBinding


def content_digest(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()


class ProfileReceipt(unittest.TestCase):
    def fixture(self, root):
        rows = [{'profile_uuid': str(index), 'name': 'Person ' + str(index)} for index in range(32)]
        lines = [(json.dumps(row) + '\n').encode() for row in rows]
        raw = b''.join(lines)
        specs, offset = {}, 0
        for row, line in zip(rows, lines):
            specs[row['profile_uuid']] = {
                'byteStart': offset, 'byteEnd': offset + len(line),
                'projectedRawRowSha256': hashlib.sha256(line).hexdigest(),
                'projectedContentSha256': content_digest(row),
            }
            offset += len(line)
        receipt = {'schemaVersion': 1, 'records': len(rows), 'profiles': specs,
                   'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                   'parent': {'receipt': {'generated_at': '2026-10-30T00:00:00Z'}}}
        receipt_file, records_file = root / 'receipt.json', root / 'records.ndjson'
        receipt_bytes = json.dumps(receipt).encode()
        receipt_file.write_bytes(receipt_bytes)
        records_file.write_bytes(raw)
        profile = SimpleNamespace(content_digest=content_digest, eligible=lambda row: True, summary=lambda: {})
        binding = MelangeBinding.__new__(MelangeBinding)
        binding._profile = profile
        binding.analytics = SimpleNamespace(verify=lambda: True, content=SimpleNamespace(data={
            'lease': SimpleNamespace(paths={'profiles/receipt.json': receipt_file,
                                           'profiles/records.ndjson': records_file}),
            'profileReceipt': receipt, 'profileCheckpoint': {'checkpoint': {}},
        }))
        return binding, profile, rows, receipt, receipt_file, records_file, receipt_bytes

    def test_receipt_is_read_once_and_all_row_contracts_keep_its_exact_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, profile, rows, receipt, receipt_file, _, receipt_bytes = self.fixture(Path(directory))
            reads = []
            original_read = Path.read_bytes

            def counted_read(path):
                if path == receipt_file:
                    reads.append(path)
                return original_read(path)

            with patch.object(Path, 'read_bytes', counted_read):
                binding._bind_profiles()
            self.assertEqual(len(reads), 1)
            expected = hashlib.sha256(receipt_bytes).hexdigest()
            self.assertEqual(profile.rows, rows)
            self.assertEqual(profile.accepted_receipt_digest, expected)
            self.assertEqual(profile.accepted_prefix_sha256, receipt['sha256'])
            self.assertEqual(profile.line_end_offsets[-1], receipt['bytes'])
            self.assertEqual(len(profile.profile_contracts), len(rows))
            for row in rows:
                contract = profile.profile_contracts[row['profile_uuid']]
                self.assertEqual(contract['receipt_sha256'], expected)
                self.assertEqual(contract['profile_content_sha256'], content_digest(row))
                self.assertEqual(contract['raw_line_sha256'], receipt['profiles'][row['profile_uuid']]['projectedRawRowSha256'])

    def test_modified_profile_row_is_still_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, _, _, _, _, records_file, _ = self.fixture(Path(directory))
            records_file.write_bytes(records_file.read_bytes().replace(b'Person 0', b'Person X'))
            with self.assertRaises(DataIntakeBlocked):
                binding._bind_profiles()


if __name__ == '__main__':
    unittest.main()
