"""Deterministic projection of fabricated observations, with hostile boundaries."""
from dataclasses import replace
import gzip
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import melange_public_provenance as public
import melange_public_payroll_projection as projection
from test_melange_public_provenance import fixture, encoded, digest, change_receipt


class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / 'inputs'
        self.root.mkdir()
        self.output = Path(self.temporary.name) / 'output'
        self.output.mkdir()
        self.plan, self.rows = fixture(self.root)
        self.destination = self.output / 'projected.ndjson'

    def tearDown(self):
        self.temporary.cleanup()

    def rewrite_input(self, role, raw, rows=1):
        index = next(i for i, v in enumerate(self.plan.inputs) if v.role == role)
        spec = self.plan.inputs[index]
        payload = gzip.compress(raw, mtime=0)
        (self.root / spec.relative).write_bytes(payload)
        inputs = list(self.plan.inputs)
        inputs[index] = replace(spec, bytes=len(payload), sha256=digest(payload), records=rows)
        self.plan = replace(self.plan, inputs=tuple(inputs))
        ridx = next(i for i, v in enumerate(self.plan.receipts) if v.receipt_id == spec.receipt_id)
        self.plan = change_receipt(self.root, self.plan, ridx,
            lambda v: v['outputs'][0].update(bytes=len(payload), sha256=digest(payload)))

    def run_projection(self):
        with public.validated_inputs(self.root, self.plan) as value:
            return projection.project_observations(value, self.destination)

    def assert_failure_preserves_inputs(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        with self.assertRaises((ValueError, OSError)):
            self.run_projection()
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()})
        self.assertFalse(self.destination.exists())
        self.assertEqual(list(self.output.iterdir()), [])

    def test_three_roles_emit_only_source_native_whitelist_and_receipt(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir()}
        receipt = self.run_projection()
        records = [json.loads(line) for line in self.destination.read_bytes().splitlines()]
        self.assertEqual(len(records), 3)
        self.assertEqual(len({row['recordId'] for row in records}), 3)
        self.assertEqual([row['sourceRole'] for row in records], list(public.ROLE_FAMILIES))
        self.assertEqual(set(records[0]), {'schemaVersion', 'recordId', 'sourceRole', 'source', 'printed', 'review'})
        self.assertEqual(records[0]['printed']['payee'], 'Fabricated Employee')
        self.assertTrue(all(row['review']['status'] == 'SOURCE_OBSERVATION_ONLY' for row in records))
        self.assertEqual(receipt['output']['sha256'], digest(self.destination.read_bytes()))
        self.assertEqual(receipt['output']['records'], 3)
        self.assertFalse(receipt['coverage']['fullApplication'])
        self.assertEqual(receipt['canonicalPromotions'], {'identity': 0, 'employment': 0, 'office': 0, 'date': 0})
        self.assertNotIn(str(self.root), json.dumps(receipt))
        self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in self.root.iterdir() if p.name in before})

    def test_same_source_bytes_produce_identical_output_and_receipt(self):
        first = self.run_projection()
        raw = self.destination.read_bytes()
        self.destination = self.output / 'second.ndjson'
        second = self.run_projection()
        self.assertEqual(self.destination.read_bytes(), raw)
        self.assertEqual(first, second)

    def test_unreviewed_or_closed_capability_refused(self):
        with self.assertRaises(ValueError):
            projection.project_observations({'approved': True}, self.destination)
        with public.validated_inputs(self.root, self.plan) as value:
            pass
        with self.assertRaises(ValueError):
            projection.project_observations(value, self.destination)
        self.assertFalse(self.destination.exists())

    def test_existing_output_or_symlink_is_never_replaced(self):
        self.destination.write_bytes(b'foreign user state')
        before = self.destination.stat()
        with self.assertRaises((ValueError, OSError)):
            self.run_projection()
        self.assertEqual(self.destination.read_bytes(), b'foreign user state')
        self.assertEqual(self.destination.stat().st_mtime_ns, before.st_mtime_ns)
        self.destination.unlink()
        target = self.output / 'unrelated'
        target.write_bytes(b'preserve')
        try:
            self.destination.symlink_to(target)
        except OSError:
            return
        with self.assertRaises((ValueError, OSError)):
            self.run_projection()
        self.assertEqual(target.read_bytes(), b'preserve')

    def test_hidden_private_field_and_wrong_inventory_document_fail(self):
        role = 'house-observations'
        for field, value in [('user_notes', 'never exported'), ('quorum_staff_id', 'private'),
                             ('source_url', 'https://www.house.gov/unreviewed.pdf'),
                             ('source_sha256', '0' * 64)]:
            row = {**self.rows[role], field: value}
            self.rewrite_input(role, encoded(row) + b'\n')
            self.assert_failure_preserves_inputs()

    def test_source_promotion_flags_and_canonical_ids_cannot_enter_projection(self):
        role = 'house-observations'
        for field, value in [('canonical_identity_promoted', True), ('canonical_eligible', True),
                             ('canonical_employment_promoted', 1), ('canonical_person_id', 'private-merged-id')]:
            self.rewrite_input(role, encoded({**self.rows[role], field: value}) + b'\n')
            self.assert_failure_preserves_inputs()

    def test_output_inside_original_input_tree_is_refused_without_touching_it(self):
        self.destination = self.root / 'new-output.ndjson'
        self.assert_failure_preserves_inputs()
        self.destination = self.output / '..' / 'inputs' / 'new-output.ndjson'
        self.assert_failure_preserves_inputs()

    def test_duplicate_source_native_locator_never_silently_deduplicates(self):
        raw = encoded(self.rows['house-observations']) + b'\n'
        self.rewrite_input('house-observations', raw * 2, rows=2)
        self.assert_failure_preserves_inputs()

    def test_record_count_and_blank_line_conservation(self):
        role = 'house-observations'
        raw = encoded(self.rows[role]) + b'\n'
        self.rewrite_input(role, raw, rows=2)
        self.assert_failure_preserves_inputs()
        self.rewrite_input(role, raw + b'\n')
        self.assert_failure_preserves_inputs()

    def test_wrong_types_nonfinite_proto_duplicate_or_invalid_utf8_fail(self):
        role = 'house-observations'
        row = self.rows[role]
        for raw in (encoded({**row, 'source_row_index': True}),
                    encoded({**row, 'payee_raw': {'unexpected': 'object'}}),
                    encoded(row)[:-1] + b',"source_row_index":1}\n',
                    encoded(row)[:-1] + b',"__proto__":{}}\n', b'\xff\n'):
            self.rewrite_input(role, raw if raw.endswith(b'\n') else raw + b'\n')
            self.assert_failure_preserves_inputs()

    def test_text_html_stays_inert_json_and_dates_are_never_inferred(self):
        role = 'house-observations'
        row = {**self.rows[role], 'payee_raw': '<img src=x onerror=evil()>',
               'service_start_raw': 'printed uncertain date', 'service_end_raw': None}
        self.rewrite_input(role, encoded(row) + b'\n')
        self.run_projection()
        value = json.loads(self.destination.read_bytes().splitlines()[0])
        self.assertEqual(value['printed']['payee'], row['payee_raw'])
        self.assertEqual(value['printed']['serviceStart'], 'printed uncertain date')
        self.assertIsNone(value['printed']['serviceEnd'])
        self.assertNotIn('canonical_person_id', value)

    def test_output_budget_and_expanded_line_budget_fail_atomically(self):
        with patch.object(projection, 'MAX_OUTPUT_BYTES', 1):
            self.assert_failure_preserves_inputs()
        with patch.object(projection, 'MAX_LINE_BYTES', 20):
            self.assert_failure_preserves_inputs()

    def test_validation_and_source_change_before_publish_leave_no_output(self):
        original = public.ValidatedInputs.ensure_current
        calls = [0]
        def changed(value):
            calls[0] += 1
            if calls[0] == 2:
                path = self.root / self.plan.documents[0].relative
                path.write_bytes(path.read_bytes() + b'changed')
            return original(value)
        with patch.object(public.ValidatedInputs, 'ensure_current', changed):
            with self.assertRaises(ValueError):
                self.run_projection()
        self.assertFalse(self.destination.exists())
        self.assertFalse(any(p.name.startswith('.melange-public-') for p in self.output.iterdir()))

    def test_foreign_file_created_at_publish_is_preserved(self):
        link = os.link
        def raced(source, destination, *args, **kwargs):
            Path(destination).write_bytes(b'foreign late file')
            return link(source, destination, *args, **kwargs)
        with patch.object(projection.os, 'link', raced):
            with self.assertRaises((ValueError, OSError)):
                self.run_projection()
        self.assertEqual(self.destination.read_bytes(), b'foreign late file')
        self.assertFalse(any(p.name.startswith('.melange-public-') for p in self.output.iterdir()))

    def test_replaced_foreign_stage_is_preserved_and_never_published(self):
        original = projection._program_fingerprint
        calls = [0]
        foreign = [None]
        def replaced():
            calls[0] += 1
            if calls[0] == 2:
                stage = next(self.output.glob('.melange-public-*.tmp'))
                stage.unlink()
                stage.write_bytes(b'foreign replacement')
                foreign[0] = stage
            return original()
        with patch.object(projection, '_program_fingerprint', replaced):
            with self.assertRaises((ValueError, OSError)):
                self.run_projection()
        self.assertFalse(self.destination.exists())
        self.assertEqual(foreign[0].read_bytes(), b'foreign replacement')

    def test_hardlinked_stage_is_preserved_and_never_published(self):
        original = projection._program_fingerprint
        calls = [0]
        stage_path = [None]
        def linked():
            calls[0] += 1
            if calls[0] == 2:
                stage = next(self.output.glob('.melange-public-*.tmp'))
                os.link(stage, self.output / 'foreign-link')
                stage_path[0] = stage
            return original()
        with patch.object(projection, '_program_fingerprint', linked):
            with self.assertRaises((ValueError, OSError)):
                self.run_projection()
        self.assertFalse(self.destination.exists())
        self.assertTrue(stage_path[0].is_file())
        self.assertEqual(stage_path[0].stat().st_nlink, 2)

    def test_in_place_stage_modification_is_not_published(self):
        original = projection._program_fingerprint
        calls = [0]
        def changed():
            calls[0] += 1
            if calls[0] == 2:
                stage = next(self.output.glob('.melange-public-*.tmp'))
                before = stage.stat()
                stage.write_bytes(b'x' * before.st_size)
                os.utime(stage, ns=(before.st_atime_ns, before.st_mtime_ns))
            return original()
        with patch.object(projection, '_program_fingerprint', changed):
            with self.assertRaises((ValueError, OSError)):
                self.run_projection()
        self.assertFalse(self.destination.exists())

    def test_edit_before_first_stage_stamp_cannot_become_a_trusted_baseline(self):
        original = public._path_stamp
        changed = [False]
        def first_stamp(path):
            if Path(path).name.startswith('.melange-public-') and not changed[0]:
                changed[0] = True
                before = Path(path).stat()
                Path(path).write_bytes(b'x' * before.st_size)
                os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
            return original(path)
        with patch.object(public, '_path_stamp', first_stamp):
            self.assert_failure_preserves_inputs()
        self.assertTrue(changed[0], 'The regression must reach the pre-stamp publication window')

    def test_invalid_gzip_fails_without_a_published_output(self):
        spec = self.plan.inputs[0]
        payload = b'not a gzip stream'
        (self.root / spec.relative).write_bytes(payload)
        inputs = list(self.plan.inputs)
        inputs[0] = replace(spec, bytes=len(payload), sha256=digest(payload))
        self.plan = replace(self.plan, inputs=tuple(inputs))
        self.plan = change_receipt(self.root, self.plan, 0,
            lambda v: v['outputs'][0].update(bytes=len(payload), sha256=digest(payload)))
        self.assert_failure_preserves_inputs()


if __name__ == '__main__':
    unittest.main()
