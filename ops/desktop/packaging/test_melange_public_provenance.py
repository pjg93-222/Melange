"""Fabricated government documents only; never opens the original data tree."""
from dataclasses import replace
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

import melange_public_provenance as public


def encoded(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def fixture(root):
    documents, receipts, inputs, rows = [], [], [], {}
    for role, family in public.ROLE_FAMILIES.items():
        document_id = role + '-document'
        raw = ('FABRICATED ' + document_id).encode()
        document_path = document_id + '.pdf'
        (root / document_path).write_bytes(raw)
        url = 'https://www.' + ('house.gov' if family == 'house' else 'senate.gov') + '/synthetic/' + document_path
        documents.append(public.DocumentSpec(document_id, family, document_path, len(raw), digest(raw), url))
        if family == 'house':
            row = {'source_url': url, 'source_sha256': digest(raw), 'source_row_index': 0,
                   'payee_raw': 'Fabricated Employee', 'office_raw': 'Fabricated Office',
                   'title_raw': 'Fabricated Position', 'amount_raw': '123.45',
                   'report_period_start': '2024-01-01', 'report_period_end': '2024-03-31',
                   'service_start_raw': None, 'service_end_raw': None}
        else:
            row = {'source_pdf_url': url, 'source_pdf_sha256': digest(raw), 'page_number': 1,
                   'row_ordinal_on_page': 0, 'payee_name_raw': 'Fabricated Employee',
                   'office_raw': 'Fabricated Office', 'title_raw': 'Fabricated Position',
                   'amount_paid_raw': '123.45', 'report_period_start': '2024-01-01',
                   'report_period_end': '2024-03-31'}
        rows[role] = row
        payload = gzip.compress(encoded(row) + b'\n', mtime=0)
        input_path = role + '.ndjson.gz'
        (root / input_path).write_bytes(payload)
        receipt_id = role + '-receipt'
        producer = digest(b'fabricated reviewed producer')
        receipt = {'schemaVersion': 1, 'receiptId': receipt_id, 'family': family,
                   'producerSha256': producer,
                   'dependencies': [{'id': document_id, 'bytes': len(raw), 'sha256': digest(raw)}],
                   'outputs': [{'role': role, 'bytes': len(payload), 'sha256': digest(payload)}],
                   'canonicalPromotions': {'identity': 0, 'employment': 0, 'office': 0, 'date': 0}}
        receipt_raw = encoded(receipt)
        receipt_path = receipt_id + '.json'
        (root / receipt_path).write_bytes(receipt_raw)
        receipts.append(public.ReceiptSpec(receipt_id, family, receipt_path, len(receipt_raw),
                                          digest(receipt_raw), producer, (document_id,), (role,)))
        inputs.append(public.InputSpec(role, input_path, len(payload), digest(payload), 1, receipt_id))
    return public.ReviewedPlan(tuple(documents), tuple(receipts), tuple(inputs)), rows


def change_receipt(root, plan, index, mutate):
    spec = plan.receipts[index]
    value = json.loads((root / spec.relative).read_bytes())
    mutate(value)
    raw = encoded(value)
    (root / spec.relative).write_bytes(raw)
    specs = list(plan.receipts)
    specs[index] = replace(spec, bytes=len(raw), sha256=digest(raw))
    return replace(plan, receipts=tuple(specs))


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.plan, self.rows = fixture(self.root)

    def tearDown(self):
        self.temporary.cleanup()

    def assert_rejected(self, plan=None):
        with self.assertRaises((ValueError, OSError)):
            with public.validated_inputs(self.root, self.plan if plan is None else plan):
                pass

    def test_exact_three_families_and_closed_documents_validate_read_only(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        with public.validated_inputs(self.root, self.plan) as value:
            self.assertEqual(set(value.inputs), set(public.ROLE_FAMILIES))
            self.assertEqual(len(value.manifest_digest), 64)
            value.ensure_current()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()})
        self.assertEqual(dict(public.PRODUCTION_PUBLIC_INPUT_PLANS), {})

    def test_plan_is_not_loaded_from_a_downloaded_approval_flag(self):
        self.assert_rejected({'approved': True, 'inputs': self.plan.inputs})
        with self.assertRaises((AttributeError, TypeError)):
            self.plan.inputs = ()

    def test_missing_duplicate_foreign_or_extra_input_role_refused(self):
        first = self.plan.inputs[0]
        for inputs in (self.plan.inputs[:-1], self.plan.inputs + (first,),
                       (replace(first, role='private-profile'),) + self.plan.inputs[1:]):
            self.assert_rejected(replace(self.plan, inputs=inputs))

    def test_paths_and_shared_paths_refused_before_open(self):
        first = self.plan.documents[0]
        for relative in ('../secret', '/secret', 'C:/secret', 'a\\secret', 'a/../secret', './secret'):
            self.assert_rejected(replace(self.plan, documents=(replace(first, relative=relative),) + self.plan.documents[1:]))
        first_input = self.plan.inputs[0]
        self.assert_rejected(replace(self.plan, inputs=(replace(first_input, relative=first.relative),) + self.plan.inputs[1:]))

    def test_only_exact_official_https_inventory_urls_allowed(self):
        first = self.plan.documents[0]
        for url in ('http://www.house.gov/a', 'https://house.gov.evil.invalid/a', 'https://user@house.gov/a',
                    'https://house.gov:443/a', 'https://house.gov/a?private=1', 'https://house.gov/a#x',
                    'https://house.gov/%2e%2e/a', 'https://house.gov/a%5cb', 'https://senate.gov/a'):
            with self.subTest(url=url):
                self.assert_rejected(replace(self.plan, documents=(replace(first, url=url),) + self.plan.documents[1:]))

    def test_every_dependency_and_document_must_be_reachable(self):
        first = self.plan.receipts[0]
        self.assert_rejected(replace(self.plan, receipts=(replace(first, dependencies=('unreviewed',)),) + self.plan.receipts[1:]))
        self.assert_rejected(replace(self.plan, receipts=(replace(first, dependencies=(first.receipt_id,)),) + self.plan.receipts[1:]))
        extra = replace(self.plan.documents[0], document_id='unused-document', relative='unused.pdf')
        (self.root / extra.relative).write_bytes((self.root / self.plan.documents[0].relative).read_bytes())
        self.assert_rejected(replace(self.plan, documents=self.plan.documents + (extra,)))

    def test_receipt_unknown_dependency_output_producer_and_promotions_refused(self):
        mutations = [lambda v: v.update(private='not admitted'),
                     lambda v: v['dependencies'][0].update(id='foreign'),
                     lambda v: v['outputs'][0].update(role='private-profile'),
                     lambda v: v.update(producerSha256='0' * 64),
                     lambda v: v['canonicalPromotions'].update(identity=1),
                     lambda v: v['canonicalPromotions'].update(date=False)]
        original = self.plan
        for mutate in mutations:
            self.plan, _ = fixture(self.root)
            self.assert_rejected(change_receipt(self.root, self.plan, 0, mutate))
        self.plan = original

    def test_pinned_document_input_receipt_hash_or_size_mismatch_refused(self):
        for spec in (self.plan.documents[0], self.plan.inputs[0], self.plan.receipts[0]):
            path = self.root / spec.relative
            before = path.read_bytes()
            path.write_bytes(before + b'x')
            self.assert_rejected()
            path.write_bytes(before)

    def test_duplicate_prototype_nonfinite_depth_string_and_utf8_limits(self):
        for raw in (b'{"a":1,"a":2}', b'{"__proto__":{}}', b'{"a":NaN}', b'{"a":1e999}',
                    b'[' * 40 + b'0' + b']' * 40, b'"' + b'x' * (public.MAX_STRING + 1) + b'"',
                    b'\xef\xbb\xbf{}', b'"\xff"', b'{} trailing'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                public.strict_json(raw)

    def test_symlink_or_hardlinked_input_never_admitted(self):
        spec = self.plan.documents[0]
        path, saved = self.root / spec.relative, self.root / 'saved.pdf'
        path.rename(saved)
        os.link(saved, path)
        self.assert_rejected()
        path.unlink()
        try:
            path.symlink_to(saved)
        except OSError:
            saved.rename(path)
        else:
            self.assert_rejected()

    def test_retained_handle_and_path_replacement_detected(self):
        spec = self.plan.documents[0]
        path = self.root / spec.relative
        with public.validated_inputs(self.root, self.plan) as value:
            original = path.read_bytes()
            path.write_bytes(original + b'x')
            with self.assertRaises(ValueError):
                value.ensure_current()

    def test_coverage_remains_component_only_and_no_global_authority_added(self):
        with public.validated_inputs(self.root, self.plan) as value:
            self.assertEqual(value.coverage, {'closedGovernmentInputs': True, 'fullApplication': False})
        with self.assertRaises(ValueError):
            value.ensure_current()


if __name__ == '__main__':
    unittest.main()
