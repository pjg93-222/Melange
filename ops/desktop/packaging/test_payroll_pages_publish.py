import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import melange_public_provenance as p
import melange_public_payroll_projection as projection
from test_melange_public_payroll_normalize import actual_fixture
from payroll_pages_publish import build
from demand_publish import sealed_inventory


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        originals = self.root / 'originals'; originals.mkdir()
        inputs = self.root / 'input'; inputs.mkdir()
        self.data = inputs / 'observations.ndjson'
        plan, _ = actual_fixture(originals)
        with p.validated_inputs(originals, plan) as verified:
            receipt = projection.project_observations(verified, self.data)
        self.receipt = inputs / 'receipt.json'; self.receipt.write_bytes(p.canonical(receipt))
        self.tag = 'module-data-2026-10-22-pages-2'

    def test_all_rows_conserved_and_closed_publication(self):
        output = self.root / 'out'
        index = build(self.data, self.receipt, output, release_tag=self.tag, generation=2, page_bytes=8192)
        original = self.data.read_bytes()
        combined = b''.join((output / c['asset']).read_bytes() for c in index['chunks'])
        self.assertEqual(combined, original)
        self.assertEqual(index['receiptSha256'], hashlib.sha256(self.receipt.read_bytes()).hexdigest())
        _, assets, _ = sealed_inventory(output, 'pjg93-222/Melange', self.tag)
        self.assertEqual(len(assets), len(index['chunks']) + 3)
        starts = {}
        for part in index['chunks']:
            role = part['selectors']['sourceRole']
            self.assertEqual(part['selectors']['start'], starts.get(role, 0))
            starts[role] = starts.get(role, 0) + part['selectors']['count']
        self.assertEqual(starts, index['recordCounts'])

    def test_changed_projection_cannot_seal_or_publish(self):
        self.data.write_bytes(self.data.read_bytes() + b'{}\n')
        output = self.root / 'bad'
        with self.assertRaises(ValueError):
            build(self.data, self.receipt, output, release_tag=self.tag, generation=2)
        self.assertFalse((output / 'publication.json').exists())

    def test_existing_output_preserved(self):
        output = self.root / 'kept'; output.mkdir(); (output/'keep').write_text('keep')
        with self.assertRaises(ValueError):
            build(self.data, self.receipt, output, release_tag=self.tag, generation=2)
        self.assertEqual((output/'keep').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
