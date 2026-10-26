"""Actual source shapes with entirely fabricated documents and records."""
from dataclasses import replace
import copy
import csv
import gzip
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import melange_public_provenance as p
import melange_public_payroll_normalize as n
import melange_public_payroll_projection as projection
from test_melange_public_provenance import digest, encoded


def actual_fixture(root, mutate=None, *, csv_header=None, extra_csv_row=False):
    """Small complete five-receipt/two-auxiliary original-source closure."""
    def write(name, raw):
        (root / name).write_bytes(raw)
        return len(raw), digest(raw)
    rendered = io.StringIO(newline='')
    writer = csv.writer(rendered)
    writer.writerow(n.CSV_12 if csv_header is None else csv_header)
    csv_row = ['Fabricated Office', '', 'PERSONNEL COMPENSATION', 'DETAIL', '', '', '',
               'Fabricated CSV Payee', '01/01/24', '03/31/24', 'Fabricated CSV Title', '12.34']
    writer.writerow(csv_row)
    if extra_csv_row:
        writer.writerow(csv_row)
    docs = [p.DocumentSpec('house-csv', 'house', 'house.csv', *write('house.csv', rendered.getvalue().encode()),
                           'https://www.house.gov/synthetic/house.csv', 'csv'),
        p.DocumentSpec('house-pdf', 'house', 'house.pdf', *write('house.pdf', b'FABRICATED HOUSE PDF'),
                           'https://www.house.gov/synthetic/house.pdf', 'pdf', 10),
        p.DocumentSpec('senate-pdf', 'senate', 'senate.pdf', *write('senate.pdf', b'FABRICATED SENATE PDF'),
                           'https://www.govinfo.gov/content/pkg/GPO-CDOC-118sdoc2/pdf/GPO-CDOC-118sdoc2.pdf', 'pdf', 10)]
    csv_doc, pdf_doc, senate_doc = docs
    common = {'report_period_start': '2024-01-01', 'report_period_end': '2024-03-31'}
    pdf = {'candidate_id': 'fabricated-pdf-row', 'source_url': pdf_doc.url, 'source_pdf_sha256': pdf_doc.sha256,
        'source_pdf_page_number': 2, 'source_pdf_row_y_milli': 12345, 'period_start': common['report_period_start'],
        'period_end': common['report_period_end'], 'employing_office_raw': 'Fabricated PDF Office',
        'payee_raw': 'Fabricated Reconstructed Payee', 'payee_source_slice_raw': 'DO.',
        'payee_reconstruction_method': 'DITTO_FROM_PRIOR_PERSONNEL_ROW_SAME_OFFICE',
        'title_description_raw': 'Fabricated PDF Title', 'amount_raw': '10.00', 'amount_source_token_raw': '$10.00',
        'service_start_date_raw': '01/01/24', 'service_end_date_raw': '03/31/24',
        'service_start_date_candidate_iso': '2024-01-01', 'service_end_date_candidate_iso': '2024-03-31'}
    house_pdf = {**common, 'source_form': 'house_gov_single_volume_pdf', 'source_url': pdf_doc.url,
        'source_sha256': '', 'source_row_index': 1,
        'source_locator': {k: pdf[k] for k in ('source_pdf_page_number', 'source_pdf_row_y_milli', 'source_pdf_sha256', 'candidate_id')},
        'office_raw': pdf['employing_office_raw'], 'payee_raw': pdf['payee_raw'],
        'title_raw': pdf['title_description_raw'], 'amount_raw': pdf['amount_raw'],
        'service_start_raw': '2024-01-01', 'service_end_raw': '2024-03-31'}
    house_csv = {**common, 'source_form': 'detail_csv', 'source_url': csv_doc.url, 'source_sha256': csv_doc.sha256,
        'source_row_index': 1, 'source_locator': None, 'office_raw': 'Fabricated Office',
        'payee_raw': 'Fabricated CSV Payee', 'title_raw': 'Fabricated CSV Title', 'amount_raw': '12.34',
        'service_start_raw': '01/01/24', 'service_end_raw': '03/31/24'}
    personal = {**common, 'source_pdf_url': senate_doc.url, 'source_pdf_sha256': senate_doc.sha256,
        'page_number': 2, 'row_ordinal_on_page': 1, 'candidate_id': 'fabricated-personal-1',
        'office_raw': 'Fabricated Senate Office', 'payee_name_raw': 'Fabricated First Payee',
        'title_raw': 'Fabricated Title', 'title_candidate': 'Fabricated Title', 'amount_paid_raw': '20.00',
        'identity_status': 'UNVERIFIED_CANDIDATE', 'employment_claim_status': 'UNVERIFIED_CANDIDATE',
        'parse_status': 'HEURISTIC_SPLIT'}
    before = {**personal, 'candidate_id': 'fabricated-personal-2', 'row_ordinal_on_page': 2,
              'payee_name_raw': 'Fabricated Original Boundary', 'title_raw': 'Fabricated Original Title'}
    repaired = {**before, 'payee_name_raw': 'Fabricated Repaired Payee', 'title_raw': 'Fabricated Repaired Title',
        'title_candidate': 'Fabricated Repaired Title', 'boundary_repair_status': n.REPAIR_STATUS,
        'pre_boundary_repair_payee_name_raw': before['payee_name_raw'], 'pre_boundary_repair_title_raw': before['title_raw']}
    excluded = {**personal, 'candidate_id': 'fabricated-excluded', 'row_ordinal_on_page': 3}
    committee = {**personal, 'candidate_id': 'fabricated-committee', 'parse_status': 'COLUMN_COORDINATE_SPLIT',
        'parser_version': 'senate-committee-payroll-parser-v2', 'office_attribution_basis': 'PAGE_HEADER'}
    rows = {'house-pdf-candidates': [pdf], 'senate-personal-unfiltered': [excluded, personal, before],
            'house-observations': [house_pdf, house_csv], 'senate-personal-candidates': [personal, repaired],
            'senate-committee-candidates': [committee]}
    rows = {role: [copy.deepcopy(row) for row in values] for role, values in rows.items()}
    if mutate:
        mutate(rows)
    specs = {}
    for role in ('house-pdf-candidates', 'senate-personal-unfiltered', *p.ROLE_FAMILIES):
        if role == 'house-observations':
            for row in rows[role]:
                if row.get('source_form') == 'house_gov_single_volume_pdf' and row['source_sha256'] == '':
                    row['source_sha256'] = specs['house-pdf-candidates'].sha256
        name = role + '.ndjson.gz'
        specs[role] = p.InputSpec(role, name, *write(name, gzip.compress(b''.join(encoded(r) + b'\n' for r in rows[role]), mtime=0)),
                                  len(rows[role]), role + '-receipt')
    evidence = []
    def ev(key, family, kind, value, ndjson=False):
        name = key + ('.ndjson' if ndjson else '.json')
        raw = b''.join(encoded(v) + b'\n' for v in value) if ndjson else encoded(value)
        spec = p.EvidenceSpec(key, family, name, *write(name, raw), kind)
        evidence.append(spec)
        return spec
    cache = ev('house-text', 'house', 'source-text-cache', {'fabricated': True})
    csv_inventory = ev('house-csv-inventory', 'house', 'source-inventory',
        {'schema_id': 'staffer-network-house-sod-url-inventory-v1', 'periods': [{**{'period_start': common['report_period_start'],
        'period_end': common['report_period_end']}, 'detail_csv_url': csv_doc.url}]})
    pdf_inventory = ev('house-pdf-inventory', 'house', 'source-inventory',
        {'schema_id': 'staffer-network-house-sod-historical-inventory-v1', 'house_pdf_periods': [{
        'period_start': common['report_period_start'], 'period_end': common['report_period_end'], 'pdf_url': pdf_doc.url}]})
    senate_inventory = ev('senate-inventory', 'senate', 'source-inventory',
        {'schema_id': 'staffer-network-official-senate-report-inventory-v1', 'periods': [{
        'period_start': common['report_period_start'], 'period_end': common['report_period_end'], 'full_pdf_url': senate_doc.url}]})
    package = {'package_id': 'GPO-CDOC-118sdoc2', 'pdf_bytes': senate_doc.bytes, 'pdf_sha256': senate_doc.sha256,
               'page_count': 10, 'pdf_url': senate_doc.url,
               'period_start': common['report_period_start'], 'period_end': common['report_period_end']}
    personal_packages = ev('senate-personal-packages', 'senate', 'source-extraction-receipts',
        [{**package, 'parser_version': 'senate-payroll-parser-v4', 'candidate_count': 3}], True)
    committee_packages = ev('senate-committee-packages', 'senate', 'source-extraction-receipts',
        [{**package, 'parser_version': 'senate-committee-payroll-parser-v2', 'accepted_row_count': 1}], True)
    current_code = ev('current-house-mapper', 'house', 'current-mapping-source', {'fabricatedCurrentCode': True})
    def binding(spec, rows=False):
        result = {'bytes': spec.bytes, 'sha256': spec.sha256, 'path': 'IGNORED PRIVATE ORIGINAL PATH'}
        if rows:
            result['rows'] = spec.records
        return result
    zero = {'canonical_identity_promotions': 0, 'canonical_employment_promotions': 0,
            'canonical_office_promotions': 0, 'canonical_service_date_promotions': 0}
    schema = {'house-ledger-v1': 'staffer-network-house-personnel-ledger-receipt-v1',
        'house-pdf-v1': 'staffer-network-house-sod-complete-reparse-receipt-v1',
        'senate-scope-v1': 'staffer-network-senate-payroll-employment-scope-receipt-v1',
        'senate-full-v1': 'staffer-network-official-senate-payroll-full-archive-receipt-v1',
        'senate-committee-v1': 'staffer-network-senate-committee-payroll-receipt-v1'}
    raw_receipts = {
        'house-ledger-v1': {'status': 'PASS', 'invariants': zero, 'outputs': [binding(specs['house-observations'], True)],
            'totals': {'observations': 2}, 'inputs': {'csv_files': [{**binding(csv_doc), 'source_url': csv_doc.url}],
                'pdf_era': binding(specs['house-pdf-candidates']), 'url_inventory': binding(csv_inventory)}},
        'house-pdf-v1': {**zero, 'status': 'PASS', 'failures': [], 'files': [binding(specs['house-pdf-candidates'], True)],
            'counts': {'payroll_candidate_rows': 1}, 'periods': [{'pdf_sha256': pdf_doc.sha256, 'text_sha256': cache.sha256}],
            'source_inventory': binding(pdf_inventory)},
        'senate-scope-v1': {**zero, 'status': 'PASS', 'complete_history_assertions': 0,
            'filter_version': 'senate-payroll-employment-scope-filter-v1',
            'accepted_candidates': binding(specs['senate-personal-candidates']),
            'source': binding(specs['senate-personal-unfiltered']), 'accepted_candidate_count': 2,
            'input_candidate_count': 3, 'rejected_candidate_count': 1},
        'senate-full-v1': {**zero, 'complete_history_assertions': 0, 'parser_version': 'senate-payroll-parser-v4',
            'archive_reports_remaining': 0, 'candidate_file': binding(specs['senate-personal-unfiltered']),
            'extraction': {'candidate_count': 3}, 'inventory_file': binding(senate_inventory),
            'report_extraction_receipts_file': binding(personal_packages)},
        'senate-committee-v1': {**zero, 'status': 'PASS', 'complete_history_assertions': 0, 'date_promotions': 0,
            'parser_version': 'senate-committee-payroll-parser-v2', 'accepted_candidates': binding(specs['senate-committee-candidates']),
            'accepted_row_count': 1, 'inventory_source': binding(senate_inventory), 'package_receipts': binding(committee_packages)}}
    dependencies = {'house-ledger-v1': ('house-csv', 'house-pdf-candidates-receipt', csv_inventory.evidence_id, current_code.evidence_id),
        'house-pdf-v1': ('house-pdf', cache.evidence_id, pdf_inventory.evidence_id),
        'senate-scope-v1': ('senate-personal-unfiltered-receipt',),
        'senate-full-v1': ('senate-pdf', senate_inventory.evidence_id, personal_packages.evidence_id),
        'senate-committee-v1': ('senate-pdf', senate_inventory.evidence_id, committee_packages.evidence_id)}
    receipts = []
    for kind, (family, role) in p.SOURCE_RECEIPTS.items():
        value = {**raw_receipts[kind], 'schema_id': schema[kind]}
        spec = specs[role]
        name = spec.receipt_id + '.json'
        receipts.append(p.ReceiptSpec(spec.receipt_id, family, name, *write(name, encoded(value)), None,
                                      dependencies[kind], (role,), kind))
    plan = p.ReviewedPlan(tuple(docs), tuple(receipts), tuple(specs[k] for k in p.ROLE_FAMILIES),
                          tuple(specs[k] for k in p.AUXILIARY_FAMILIES), tuple(evidence))
    return plan, rows


class ActualShapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve() / 'originals'
        self.root.mkdir()
        self.destination = Path(self.tmp.name).resolve() / 'projection.ndjson'
        self.plan, self.rows = actual_fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def project(self):
        with p.validated_inputs(self.root, self.plan) as verified:
            return projection.project_observations(verified, self.destination)

    def refused(self):
        before = {v.name: (v.read_bytes(), v.stat().st_mtime_ns) for v in self.root.iterdir()}
        with self.assertRaises((ValueError, OSError, csv.Error)):
            self.project()
        self.assertFalse(self.destination.exists())
        self.assertEqual(before, {v.name: (v.read_bytes(), v.stat().st_mtime_ns) for v in self.root.iterdir()})

    def test_actual_shapes_preserve_literal_tokens_repairs_and_zero_promotions(self):
        receipt = self.project()
        rows = [json.loads(v) for v in self.destination.read_bytes().splitlines()]
        self.assertEqual(len(rows), 5)
        pdf, csv_row, plain, repaired, committee = rows
        self.assertEqual(pdf['literalTokens']['serviceStart'], '01/01/24')
        self.assertNotEqual(pdf['literalTokens']['serviceStart'], '2024-01-01')
        self.assertEqual(pdf['literalTokens']['payee'], 'DO.')
        self.assertEqual(pdf['extractionStatus']['method'], 'DITTO_FROM_PRIOR_PERSONNEL_ROW_SAME_OFFICE')
        self.assertEqual(pdf['source']['sha256'], self.plan.documents[1].sha256)
        self.assertEqual(repaired['originalBeforeRepair']['payee'], 'Fabricated Original Boundary')
        self.assertEqual(repaired['sourceExtracted']['payee'], 'Fabricated Repaired Payee')
        self.assertIsNone(plain['literalTokens'])
        self.assertIsNone(committee['literalTokens'])
        self.assertEqual(csv_row['extractionStatus']['literalEquivalence'], 'VERIFIED_RAW_CSV_FIELDS')
        self.assertEqual(receipt['normalizationCounts'], {'houseCsvFieldEquivalentRows': 1, 'housePdfCandidateJoins': 1,
            'senateAcceptedSubsequence': 2, 'senateRawRecords': 3, 'senateExcludedRecords': 1, 'senateAcceptedRepairs': 1})
        public = encoded(receipt)
        self.assertNotIn(b'PRIVATE ORIGINAL PATH', public)
        self.assertNotIn(b'Fabricated Repaired Payee', public)
        self.assertTrue(all(v['producerSha256'] is None and v['historicalProducerProof'] == 'GENERATION_CODE_UNAVAILABLE'
                            for v in receipt['sourceManifest']['receipts']))
        self.assertEqual(dict(p.PRODUCTION_PUBLIC_INPUT_PLANS), {})
        self.assertFalse(receipt['coverage']['fullApplication'])

    def test_govinfo_exact_full_package_only(self):
        valid = self.plan.documents[2]
        for url in ('https://govinfo.gov/content/pkg/GPO-CDOC-118sdoc2/pdf/GPO-CDOC-118sdoc2.pdf',
            valid.url.replace('/pdf/', '/html/'), valid.url.replace('pdf/GPO-CDOC-118sdoc2', 'pdf/GPO-CDOC-118sdoc3'),
            valid.url.replace('.pdf', '-pt1.pdf'), valid.url + '?x=1', valid.url.replace('www.govinfo.gov', 'www.govinfo.gov.evil.invalid')):
            with self.subTest(url=url), self.assertRaises(ValueError):
                p._official_url(url, 'senate')
        p._official_url(valid.url, 'senate')

    def test_missing_wrong_or_private_auxiliary_closure_fails(self):
        self.plan = replace(self.plan, auxiliaries=())
        self.refused()
        self.plan, _ = actual_fixture(self.root)
        first = self.plan.auxiliaries[0]
        self.plan = replace(self.plan, auxiliaries=(replace(first, role='private-graph'), self.plan.auxiliaries[1]))
        self.refused()

    def test_house_pdf_intermediate_digest_ordinal_locator_and_fields_cannot_drift(self):
        mutations = [lambda r: r['house-observations'][0].update(source_row_index=2),
            lambda r: r['house-observations'][0].update(source_sha256='0' * 64),
            lambda r: r['house-observations'][0]['source_locator'].update(source_pdf_row_y_milli=1),
            lambda r: r['house-observations'][0].update(payee_raw='Fabricated unauthorized repair'),
            lambda r: r['house-pdf-candidates'][0].update(payee_reconstruction_method='PRIVATE_PERSON_MERGE')]
        for mutate in mutations:
            self.plan, _ = actual_fixture(self.root, mutate)
            self.refused()

    def test_senate_subsequence_and_pre_repair_conservation_fail_closed(self):
        mutations = [lambda r: r['senate-personal-candidates'].reverse(),
            lambda r: r['senate-personal-candidates'][1].update(pre_boundary_repair_title_raw='Wrong original'),
            lambda r: r['senate-personal-candidates'][0].update(amount_paid_raw='999.00'),
            lambda r: r['senate-personal-candidates'][1].update(boundary_repair_status='PRIVATE_IDENTITY_REPAIR'),
            lambda r: r['senate-personal-unfiltered'].append(copy.deepcopy(r['senate-personal-unfiltered'][0]))]
        for mutate in mutations:
            self.plan, _ = actual_fixture(self.root, mutate)
            self.refused()

    def test_house_csv_six_fields_checked_against_original_column_values(self):
        for key in ('office_raw', 'payee_raw', 'title_raw', 'amount_raw', 'service_start_raw', 'service_end_raw'):
            self.plan, _ = actual_fixture(self.root, lambda r: r['house-observations'][1].update({key: 'Changed'}))
            self.refused()

    def test_unknown_csv_schema_and_unused_admitted_rows_rejected(self):
        self.plan, _ = actual_fixture(self.root, csv_header=('unknown', 'header'))
        self.refused()
        self.plan, _ = actual_fixture(self.root, extra_csv_row=True)
        self.refused()

    def test_csv_record_ordinals_width_repair_and_two_fixed_headers(self):
        for header in (n.CSV_12, n.CSV_18):
            rendered = io.StringIO(newline='')
            writer = csv.writer(rendered)
            writer.writerow((*header, ''))
            original = {k: '' for k in header}
            original.update({'ORGANIZATION': ' Fabricated Office ', 'SORT SEQUENCE': 'detail',
                'SORT SUBTOTAL DESCRIPTION': 'Personnel Compensation', 'VENDOR NAME': 'Fabricated',
                'DESCRIPTION': 'Title', 'AMOUNT': '1.00'})
            values = [original[k] for k in header]
            writer.writerow(['MALFORMED WIDTH'])
            nonadmitted = list(values)
            nonadmitted[header.index('SORT SEQUENCE')] = 'SUBTOTAL'
            writer.writerow(nonadmitted + [''])
            writer.writerow(values + [''])
            index = header.index('VENDOR NAME')
            writer.writerow(values[:index + 1] + ['Comma'] + values[index + 1:])
            raw = rendered.getvalue().encode()
            document = replace(self.plan.documents[0], bytes=len(raw), sha256=digest(raw))
            verified = SimpleNamespace(document_stream=lambda _: io.BytesIO(raw))
            rows = list(n.csv_records(verified, document))
            self.assertEqual([ordinal for ordinal, _ in rows], [3, 4])
            self.assertEqual(rows[0][1]['ORGANIZATION'], 'Fabricated Office')
            self.assertEqual(rows[1][1]['VENDOR NAME'], 'Fabricated, Comma')

    def test_original_receipt_adapter_rechecks_schema_output_and_zero_counters(self):
        for mutate in (lambda v: v.update(schema_id='unreviewed-receipt'),
                       lambda v: v['invariants'].update(canonical_identity_promotions=1),
                       lambda v: v['outputs'][0].update(sha256='0' * 64)):
            self.plan, _ = actual_fixture(self.root)
            receipt = self.plan.receipts[0]
            raw = json.loads((self.root / receipt.relative).read_bytes())
            mutate(raw)
            encoded_raw = encoded(raw)
            (self.root / receipt.relative).write_bytes(encoded_raw)
            self.plan = replace(self.plan, receipts=(replace(receipt, bytes=len(encoded_raw), sha256=digest(encoded_raw)),)
                                + self.plan.receipts[1:])
            self.refused()

    def test_changed_original_auxiliary_is_detected_without_mutating_it(self):
        spec = self.plan.auxiliaries[0]
        path = self.root / spec.relative
        with p.validated_inputs(self.root, self.plan) as verified:
            path.write_bytes(path.read_bytes() + b'CHANGED')
            before = path.read_bytes(), path.stat().st_mtime_ns
            with self.assertRaises(ValueError):
                projection.project_observations(verified, self.destination)
            self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
        self.assertFalse(self.destination.exists())

    def test_original_receipt_does_not_invent_a_historical_code_hash(self):
        first = self.plan.receipts[0]
        self.plan = replace(self.plan, receipts=(replace(first, producer_sha256='0' * 64),) + self.plan.receipts[1:])
        self.refused()

    def test_inventory_period_and_package_page_limit_are_enforced(self):
        self.plan, _ = actual_fixture(self.root,
            lambda r: r['senate-personal-candidates'][0].update(page_number=11))
        self.refused()
        self.plan, _ = actual_fixture(self.root,
            lambda r: r['house-observations'][1].update(report_period_start='2020-01-01'))
        self.refused()

    def test_auxiliary_expansion_and_unknown_source_keys_refused(self):
        with patch.object(n, 'MAX_ROLE_EXPANDED_BYTES', 1):
            self.refused()
        self.plan, _ = actual_fixture(self.root, lambda r: r['house-pdf-candidates'][0].update(private_notes='Never export'))
        self.refused()


if __name__ == '__main__':
    unittest.main()
