"""Candidate campaign spending (FEC Schedule B): the source adapter, the classifier, the money rules and the route.

Every figure is worked by hand. Scenario rows come from Andy Barr's 2023-24 committee (ANDY BARR FOR CONGRESS,
INC.) as Paul named them: WinRed CC TRANSACTION FEES, The Stanton Group FUNDRAISING CONSULTING, Payroll Solutions
PAYROLL TAXES / SEE MEMOS, American Express SEE MEMOS, Delta TRAVEL EXPENSE, Accurate Word PRINTING, Professional Data
Services COMPLIANCE CONSULTING, Republican Party of Fayette County EVENT SPONSOR and a VOID of -$1,500, refunds to
donors, and IN-KIND: FOOD, BEVERAGE & EVENT SPACE.

The source is the crawler's reader (tools/committee_activity_reader.py, not in this checkout); every test feeds the
adapter results in the reader's exact shape through MENTAT_CANDIDATE_SPENDING_FIXTURE or by calling combine() directly.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'app'))
sys.path.insert(0, str(HERE / 'tools'))
import candidate_spending as cs  # noqa: E402

FIXTURES = HERE / 'tests' / 'fixtures' / 'candidate_spending'
CRAWLER = FIXTURES / 'crawler'
CRAWLER_FIXTURE = CRAWLER / 'read_campaign_spending_fixture.json'      # copied unchanged from the crawler lane (see the README beside it)
CRAWLER_SCHEMA = CRAWLER / 'read_campaign_spending_fixture.schema.json'
CRAWLER_SHA256 = {CRAWLER_FIXTURE.name: 'c6a51fe6018691372f2cc427d0a37523003f22263fc91202990fc3eae49523f7',
                  CRAWLER_SCHEMA.name: 'def754dc60bd42a0323cf0ab56699db5fe76e52345854ef958caf6a8e969cc05'}
BARR = 'BARR, GARLAND ANDY'
COMMITTEE = 'C00467571'


def row(name, text, amount, tid='', line='17', purpose='OTHER', memo=None, back=None, entity='ORG', committee=None, date='2024-03-01', sub=None):
    key = abs(hash((name, text, amount, date)))
    return {'committee_id': COMMITTEE, 'transaction_id': tid or f'T{key % 10**8}', 'sub_id': sub or tid or f'S{key % 10**8}',
            'disbursement_date': date, 'disbursement_amount': amount, 'disbursement_description': text,
            'disbursement_purpose_category': purpose, 'memo_code': memo, 'memo_text': None,
            'back_reference_transaction_id': back, 'entity_type': entity, 'recipient_committee_id': committee,
            'line_number': line, 'recipient_name': name, 'recipient_state': 'KY',
            'image_number': '202501319748746337', 'pdf_url': 'https://docquery.fec.gov/cgi-bin/fecimg/?202501319748746337'}


def totals(disbursements, committee=COMMITTEE, cycle=2024, loans=0.0, transfers=0.0, end='2024-12-31T00:00:00'):
    return {'committee_id': committee, 'cycle': cycle, 'disbursements': disbursements, 'loan_repayments': loans,
            'transfers_to_other_authorized_committee': transfers, 'coverage_end_date': end}


def committee(rows, disbursements='sum', committee_id=COMMITTEE, status='complete', name='ANDY BARR FOR CONGRESS, INC.', **extra):
    if disbursements == 'sum':
        disbursements = sum(r['disbursement_amount'] for r in rows if r['memo_code'] != 'X')
    return {'committee_id': committee_id, 'committee_name': name, 'cycle': 2024, 'coverage_status': status,
            'endpoint_status': {'B': 'complete', 'totals': 'complete'} if status == 'complete' else {'B': 'pending', 'totals': 'pending'},
            'retrieved_at': {'B_latest': '2026-10-15T12:00:00Z', 'totals': '2026-10-15T12:01:00Z'},
            'totals': [] if disbursements is None else [totals(disbursements, committee_id, **extra)], 'rows': rows,
            'row_occurrences': len(rows), 'disclosure_boundaries': 0}


def result(*committees, candidate='H0KY06104'):
    ids = [item['committee_id'] for item in committees]
    return {'query': {'cycle': 2024, 'candidate_id': candidate, 'committee_id': None}, 'snapshot': {'batch': 3, 'sha256': 'ab' * 32},
            'mapping': {'candidate_id': candidate, 'source': 'bulk_ccl', 'vintage_or_retrieved_at': '2026-07-22', 'committee_ids': ids},
            'committees': list(committees)}


def campaign(rows, **kwargs):
    return cs.combine(result(committee(rows, **kwargs)), 2024)


def numbers(rows, hint=BARR, detail=False, **kwargs):
    return cs.breakdown(campaign(rows, **kwargs), hint, detail=detail)


def amounts(body):
    return {item['key']: item['amount'] for item in body['categories']}


class Classifier(unittest.TestCase):
    TABLE = [
        # (payee, description, expected, extra row fields)
        ('WINRED TECHNICAL SERVICES, LLC', 'CC TRANSACTION FEES', 'fundraising_fees', {}),
        ('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 'consulting', {}),
        ('PAYROLL SOLUTIONS', 'PAYROLL TAXES / SEE MEMOS', 'payroll', {}),
        ('PAYROLL SOLUTIONS', 'PAYROLL EXPENSE', 'payroll', {}),
        ('AMERICAN EXPRESS', 'SEE MEMOS', 'other', {}),
        ('DELTA AIRLINES', 'TRAVEL EXPENSE', 'travel', {}),
        ('ACCURATE WORD LLC', 'PRINTING', 'printing_mail', {}),
        ('PROFESSIONAL DATA SERVICES', 'COMPLIANCE CONSULTING', 'legal_compliance', {}),     # not consulting
        ('REPUBLICAN PARTY OF FAYETTE COUNTY', 'EVENT SPONSOR', 'contributions_transfers', {}),  # not events
        ('NRCC', 'CONTRIBUTION', 'contributions_transfers', {}),
        ('BOUCHER, DAWN D', 'REFUND', 'refunds', {'line': '20A', 'entity': 'IND'}),
        ('LOTT, CHESTER TRENT JR.', 'IN-KIND:FOOD, BEVERAGE, & EVENT SPACE', 'events', {}),
        ('LOTT, CHESTER TRENT JR.', 'IN-KIND: FOOD, BEVERAGE & EVENT SPACE', 'events', {}),
        ('LEXINGTON MINI STORAGE', 'RENT', 'office', {}),
        ('AMERICAN TRUST', 'BANK FEE', 'office', {}),                       # a bank fee is not a processing fee
        ('UPONE INSIGHTS', 'POLLING EXPENSE', 'polling_data', {}),
        ('SOMETHING ELSE STRATEGIES, LLC', 'MEDIA PRODUCTION', 'advertising', {}),
        ('SEYMOUR & PERRY, LLC', 'TAX PREPARATION EXPENSE', 'legal_compliance', {'purpose': 'MATERIALS'}),
        ('LILLY & COMPANY', 'GRAPHIC DESIGN', 'advertising', {}),
        ('BARR, GARLAND ANDY', 'CHILD CARE REIMBURSEMENT', 'personal_reimb', {'entity': 'IND'}),
        ('BARR, GARLAND ANDY', 'TRAVEL EXPENSE REIMBURSEMENT', 'personal_reimb', {'entity': 'IND'}),
        ('ANDY BARR VICTORY COMMITTEE', 'TRANSFER', 'contributions_transfers', {'committee': 'C00123456'}),
        ('ACTBLUE', 'ACTBLUE PROCESSING FEES', 'fundraising_fees', {'committee': 'C00401224'}),   # a fee before the committee signal
        ('ARISTOTLE INTERNATIONAL', 'DATABASE SERVICES', 'polling_data', {}),
        ('THE MAIL HAUS', 'POSTAGE', 'printing_mail', {}),
        ('WHATEVER LLC', 'MYSTERY ITEM', 'other', {}),
        ('WHATEVER LLC', 'MYSTERY ITEM', 'travel', {'purpose': 'TRAVEL'}),     # FEC's purpose category is the fallback
        ('WHATEVER LLC', '', 'other', {}),
    ]

    def test_paul_rows_and_the_ordering_rules(self):
        for payee, description, expected, extra in self.TABLE:
            with self.subTest(payee=payee, description=description):
                self.assertEqual(cs.classify(row(payee, description, 100, **extra), BARR), expected)

    def test_a_campaign_paying_itself_is_a_transfer_not_a_reimbursement(self):
        self.assertEqual(cs.classify(row('ANDY BARR FOR CONGRESS', 'REIMBURSEMENT', 10, committee='C00467571'), BARR), 'contributions_transfers')

    def test_without_the_candidates_name_the_committees_stands_in(self):
        self.assertEqual(cs.candidate_hint('ANDY BARR FOR CONGRESS, INC. + ANDY BARR VICTORY'), 'ANDY BARR')
        body = numbers([row('BARR, GARLAND ANDY', 'CHILD CARE REIMBURSEMENT', 120.0, entity='IND')], hint=None)
        self.assertEqual(amounts(body), {'personal_reimb': 120.0})

    def test_the_table_is_deterministic(self):
        sample = row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 5)
        self.assertEqual({cs.classify(sample, BARR) for _ in range(5)}, {'consulting'})


class MemoParents(unittest.TestCase):
    def rows(self, child_total):
        parent = row('PAYROLL SOLUTIONS', 'SEE MEMOS', 1000.00, tid='P1')
        kids = [row('WITT, CONNIE', 'PAYROLL EXPENSE', 600.00, tid='K1', memo='X', back='P1', entity='IND'),
                row('PAYROLL SOLUTIONS', 'PAYROLL TAXES', child_total - 600.00, tid='K2', memo='X', back='P1')]
        return [parent, *kids, row('DELTA AIRLINES', 'TRAVEL EXPENSE', 50.00)]

    def test_children_that_sum_to_the_parent_are_classified_and_the_parent_is_not_counted_twice(self):
        body = numbers(self.rows(1000.00))
        self.assertEqual(amounts(body), {'payroll': 1000.0, 'travel': 50.0})
        self.assertEqual(body['total_itemized'], 1050.0)            # the parent once, never parent plus children
        self.assertEqual(body['memo_handling'], {'parents': 1, 'resolved': 1, 'unresolved': 0, 'children_used': 2,
                                                  'unresolved_amount': 0.0, 'memo_rows': 2, 'memo_rows_not_counted': 0})

    def test_within_a_dollar_resolves_and_the_difference_stays_in_the_total(self):
        body = numbers(self.rows(999.20))                           # $0.80 short: within $1.00
        self.assertEqual(body['memo_handling']['resolved'], 1)
        self.assertEqual(body['total_itemized'], 1050.0)
        self.assertAlmostEqual(sum(amounts(body).values()), 1050.0, places=2)   # categories still add up to the parent

    def test_more_than_a_dollar_off_stays_one_unitemized_parent_in_other(self):
        body = numbers(self.rows(998.50))                           # $1.50 short
        self.assertEqual(amounts(body), {'other': 1000.0, 'travel': 50.0})
        self.assertEqual(body['memo_handling']['unresolved'], 1)
        self.assertEqual(body['memo_handling']['unresolved_amount'], 1000.0)
        self.assertEqual(body['memo_handling']['memo_rows_not_counted'], 2)
        self.assertEqual(body['other_top_descriptions'][0]['description'], cs.UNITEMIZED_PARENT)
        self.assertEqual(body['total_itemized'], 1050.0)

    def test_memo_rows_alone_are_never_totals(self):
        orphan = row('SOMEONE', 'TRAVEL EXPENSE', 77.00, memo='X', back='NOPE')
        body = numbers([orphan, row('DELTA AIRLINES', 'TRAVEL EXPENSE', 50.00)])
        self.assertEqual(body['total_itemized'], 50.0)

    def test_a_parent_that_is_not_a_see_memos_row_keeps_its_own_words(self):
        parent = row('U.S. DEPARTMENT OF THE TREASURY', 'DISGORGED FUNDS', 100.0, tid='D1')
        kid = row('DONOR, ONE', 'REFUND', 100.0, tid='D2', memo='X', back='D1')
        body = numbers([parent, kid])
        self.assertEqual(amounts(body), {'other': 100.0})
        self.assertEqual(body['memo_handling']['parents'], 0)


class Netting(unittest.TestCase):
    def test_a_void_nets_inside_the_category_of_the_row_it_undoes(self):
        rows = [row('REPUBLICAN PARTY OF FAYETTE COUNTY', 'EVENT SPONSOR', 1500.00, date='2024-02-01'),
                row('REPUBLICAN PARTY OF FAYETTE COUNTY', 'VOID OF PREVIOUS - REISSUED FOR CORRECTED AMOUNT', -1500.00, date='2024-03-01'),
                row('REPUBLICAN PARTY OF FAYETTE COUNTY', 'EVENT SPONSOR', 2500.00, date='2024-03-02')]
        body = numbers(rows)
        self.assertEqual(amounts(body), {'contributions_transfers': 2500.0})
        self.assertEqual(body['categories'][0]['payments'], 2)           # the void is not a payment
        self.assertEqual(body['total_itemized'], 2500.0)

    def test_a_void_with_no_original_in_the_data_falls_back_to_its_own_words(self):
        rows = [row('ELECTORAL STRATEGIES INC.', 'VOID OF PREVIOUS CK 10442 LOST', -2146.91),
                row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 5000.00)]
        self.assertEqual(numbers(rows)['total_itemized'], 2853.09)

    def test_a_category_that_nets_to_zero_or_less_is_dropped_and_listed(self):
        rows = [row('DELTA AIRLINES', 'TRAVEL EXPENSE', 300.00),
                row('DELTA AIRLINES', 'TRAVEL EXPENSE REFUNDED', -300.00),
                row('DELTA AIRLINES', 'TRAVEL EXPENSE', -50.00),
                row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 1000.00)]
        body = numbers(rows)
        self.assertEqual(amounts(body), {'consulting': 1000.0})
        self.assertEqual(body['dropped_negative'], [{'key': 'travel', 'label': 'Travel', 'amount': -50.0, 'payments': 1}])
        self.assertEqual(body['categories'][0]['share'], 1.0)           # shares are over what the ring draws
        self.assertEqual(body['total_itemized'], 950.0)                  # the net of everything itemized


class Coverage(unittest.TestCase):
    def test_coverage_is_itemized_over_reported_and_never_scaled_up(self):
        rows = [row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 600.00), row('DELTA AIRLINES', 'TRAVEL EXPENSE', 200.00)]
        body = numbers(rows, disbursements=1000.00)
        self.assertEqual((body['total_itemized'], body['reported_total'], body['coverage']), (800.0, 1000.0, 0.8))
        self.assertEqual(sum(item['amount'] for item in body['categories']), 800.0)    # nothing was scaled to 1,000
        self.assertFalse(body['coverage_unknown'])

    def test_loan_repayments_and_transfers_to_authorized_committees_leave_both_sides(self):
        rows = [row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 600.00),
                row('ANDY BARR VICTORY COMMITTEE', 'TRANSFER', 300.00, line='18', committee='C00123456'),
                row('BARR, GARLAND ANDY', 'LOAN REPAYMENT', 100.00, line='19A', entity='IND')]
        body = numbers(rows, disbursements=1500.00, loans=100.00, transfers=300.00)
        self.assertEqual((body['total_itemized'], body['reported_total'], body['coverage']), (600.0, 1100.0, 0.5455))
        self.assertEqual(body['excluded']['transfers_to_authorized'], {'itemized': 300.0, 'reported': 300.0})
        self.assertEqual(body['excluded']['loan_repayments'], {'itemized': 100.0, 'reported': 100.0})
        self.assertEqual(amounts(body), {'consulting': 600.0})

    def test_no_totals_means_unknown_coverage_not_a_made_up_one(self):
        body = numbers([row('DELTA AIRLINES', 'TRAVEL EXPENSE', 5.00)], disbursements=None, status='partial')
        self.assertIsNone(body['coverage'])
        self.assertIsNone(body['reported_total'])
        self.assertTrue(body['coverage_unknown'])
        self.assertEqual(body['coverage_status'], 'partial')
        self.assertEqual(body['total_itemized'], 5.0)

    def test_totals_are_the_object_for_the_cycle_and_the_latest_when_there_are_several(self):
        item = committee([row('DELTA AIRLINES', 'TRAVEL EXPENSE', 10.0)])
        item['totals'] = [totals(999.0, cycle=2022), totals(100.0, end='2024-06-30T00:00:00'), totals(250.0, end='2024-12-31T00:00:00')]
        self.assertEqual(cs.combine(result(item), 2024)['totals']['disbursements'], 25000)       # cents
        item['totals'] = [totals(999.0, cycle=2022)]
        self.assertIsNone(cs.combine(result(item), 2024)['totals'])


class Source(unittest.TestCase):
    def test_rows_are_deduplicated_by_sub_id_before_anything_else_and_the_count_is_kept(self):
        first = row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 600.00, sub='S1')
        rows = [first, dict(first), row('DELTA AIRLINES', 'TRAVEL EXPENSE', 200.00, sub='S2')]
        body = numbers(rows, disbursements=800.00)
        self.assertEqual(body['total_itemized'], 800.0)
        self.assertEqual((body['source']['row_occurrences'], body['source']['duplicate_rows_dropped'], body['source']['rows']), (3, 1, 2))
        self.assertEqual(body['coverage'], 1.0)

    def test_two_committees_are_combined_and_transfers_between_them_are_counted_once_and_reported(self):
        a = committee([row('PEAK', 'FUNDRAISING CONSULTING', 1000.00, sub='A1'),
                       row('ZED FOR CONGRESS II', 'TRANSFER', 400.00, line='18', committee='C90000102', sub='A2')],
                      disbursements=1400.00, committee_id='C90000101', name='ZED FOR CONGRESS', transfers=400.00)
        b = committee([row('KENTUCKY TV', 'TV ADS', 300.00, sub='B1'),
                       row('ZED FOR CONGRESS', 'REIMBURSEMENT', 50.00, line='21', committee='C90000101', sub='B2')],
                      disbursements=350.00, committee_id='C90000102', name='ZED FOR CONGRESS II')
        body = cs.breakdown(cs.combine(result(a, b), 2024), 'ZED, ZACHARY')
        self.assertEqual(amounts(body), {'consulting': 1000.0, 'advertising': 300.0})
        self.assertEqual(body['own_transfers'], {'amount': 450.0, 'rows': 2})
        self.assertEqual(body['committee_name'], 'ZED FOR CONGRESS + ZED FOR CONGRESS II')
        self.assertEqual(body['committee_ids'], ['C90000101', 'C90000102'])
        self.assertEqual((body['total_itemized'], body['reported_total'], body['coverage']), (1300.0, 1350.0, 0.963))
        self.assertEqual(body['coverage_status'], 'complete')

    def test_complete_needs_every_committee_complete(self):
        a = committee([row('PEAK', 'FUNDRAISING CONSULTING', 1000.00, sub='A1')], committee_id='C90000101', name='ZED FOR CONGRESS')
        b = committee([], disbursements=None, committee_id='C90000102', name='ZED FOR CONGRESS II', status='partial')
        both = cs.combine(result(a, b), 2024)
        self.assertEqual(both['coverage_status'], 'partial')
        self.assertIsNone(both['totals'])                       # one committee's totals are missing: the sum is unknown
        self.assertIn('ZED FOR CONGRESS II: partial (Schedule B pending, totals pending)', both['reasons'])
        only = cs.combine(result(a), 2024)
        self.assertEqual(only['coverage_status'], 'complete')

    def test_pending_not_seeded_and_unmapped_never_imply_zero(self):
        for status, words in (('pending', 'Spending not collected for 2023–24'), ('not_seeded', 'Spending not collected for 2023–24'),
                              ('mapping_unknown', 'Campaign committee not identified for 2023–24')):
            with self.subTest(status=status):
                made = cs.combine(result(committee([], disbursements=None, status=status)), 2024)
                self.assertEqual(made['message'], words)
                self.assertNotEqual(made['status'], 'ok')
        self.assertEqual(cs.combine({'committees': []}, 2024)['status'], 'mapping_unknown')

    def test_a_partial_campaign_is_drawn_with_its_reason(self):
        item = committee([row('PEAK', 'FUNDRAISING CONSULTING', 1000.00)], disbursements=None, status='partial')
        body = cs.breakdown(cs.combine(result(item), 2024), BARR)
        self.assertEqual((body['status'], body['coverage_status'], body['coverage']), ('ok', 'partial', None))
        self.assertEqual(body['coverage_reasons'], ['ANDY BARR FOR CONGRESS, INC.: partial (Schedule B pending, totals pending)'])

    def test_without_the_reader_the_answer_is_source_unavailable_not_a_crash(self):
        with patch.dict(os.environ, {cs.FIXTURE_ENV: ''}), patch.dict(sys.modules, {cs.READER: None}):
            body, status = cs.respond({'candidate': ['H0KY06104'], 'cycle': ['2024']})
        self.assertEqual((status, body['status'], body['error']), (503, 'source_unavailable', 'Spending source not installed'))

    def test_the_reader_is_called_with_its_documented_keywords(self):
        calls = []

        class Reader:
            @staticmethod
            def read_campaign_spending(**kwargs):
                calls.append(kwargs)
                return result(committee([row('DELTA AIRLINES', 'TRAVEL EXPENSE', 5.0)]))
        with patch.dict(os.environ, {cs.FIXTURE_ENV: ''}), patch.dict(sys.modules, {cs.READER: Reader}):
            cs.load_campaign_spending('H0KY06104', 2024)
            cs.load_campaign_spending('C00467571', 2024)
        self.assertEqual(calls, [{'cycle': 2024, 'candidate_id': 'H0KY06104', 'committee_id': None},
                                 {'cycle': 2024, 'candidate_id': None, 'committee_id': 'C00467571'}])

    def test_the_crawlers_contract_fixture_is_the_copy_it_was_given(self):
        import hashlib
        for name, digest in CRAWLER_SHA256.items():
            self.assertEqual(hashlib.sha256((CRAWLER / name).read_bytes()).hexdigest(), digest, name)

    def test_every_fixture_here_validates_against_the_crawlers_schema(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is not installed')
        schema = json.loads(CRAWLER_SCHEMA.read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.validate(json.loads(CRAWLER_FIXTURE.read_text(encoding='utf-8')), schema)            # the container
        one = jsonschema.Draft202012Validator({'$ref': '#/$defs/Result', '$defs': schema['$defs']})
        for path in sorted(FIXTURES.glob('*-20*.json')):
            with self.subTest(fixture=path.name):
                one.validate(json.loads(path.read_text(encoding='utf-8')))

    def test_the_crawlers_fixture_goes_through_the_adapter_unchanged_and_each_state_reads_right(self):
        value = json.loads(CRAWLER_FIXTURE.read_text(encoding='utf-8'))
        # coverage_status -> what the UI is told (candidate_spending.combine + breakdown)
        expected = {'complete': 'ok', 'partial': 'ok', 'not_seeded': 'not_collected', 'pending': 'not_collected', 'mapping_unknown': 'mapping_unknown'}
        self.assertEqual({item['name'] for item in value['examples']}, set(expected))
        words = {'not_collected': 'Spending not collected for 2023–24', 'mapping_unknown': 'Campaign committee not identified for 2023–24'}
        for item in value['examples']:
            call = item['call']
            who = call.get('candidate_id') or call['committee_id']
            with self.subTest(example=item['name']), patch.dict(os.environ, {cs.FIXTURE_ENV: str(CRAWLER_FIXTURE)}):
                made = cs.load_campaign_spending(who, call['cycle'])
                self.assertEqual(made['status'], expected[item['name']])
                if made['status'] != 'ok':
                    self.assertEqual(made['message'], words[made['status']])
                    if call.get('candidate_id'):
                        body, status = cs.respond({'candidate': [who], 'cycle': [str(call['cycle'])]})
                        self.assertEqual((status, body['error']), (404, words[made['status']]))
                    continue
                shown = cs.breakdown(made, detail=True)
                self.assertEqual(shown['coverage_status'], item['name'])
                rows = [row for committee in item['result']['committees'] for row in committee['rows']]
                self.assertEqual(shown['source']['row_occurrences'], len(rows))
                self.assertEqual(shown['source']['rows'] + shown['source']['duplicate_rows_dropped'] + shown['own_transfers']['rows'], len(rows))
                self.assertEqual(shown['committee_name'], item['result']['committees'][0]['committee_name'])
                if item['name'] == 'complete':
                    self.assertFalse(shown['coverage_unknown'])
                    self.assertEqual(shown['coverage_reasons'], [])
                    self.assertIsNotNone(shown['reported_total'])
                else:                                                          # partial: drawn, never read as zero or as complete
                    self.assertTrue(shown['coverage_unknown'])
                    self.assertIsNone(shown['reported_total'])
                    self.assertIn('partial (Schedule B pending, totals unsupported)', shown['coverage_reasons'][0])


class Detail(unittest.TestCase):
    def test_top_payees_use_non_memo_rows_and_resolved_memo_children(self):
        parent = row('AMERICAN EXPRESS', 'SEE MEMOS', 700.00, tid='A1')
        kids = [row('DELTA AIRLINES', 'TRAVEL EXPENSE', 400.00, tid='A2', memo='X', back='A1'),
                row('MARRIOTT', 'TRAVEL EXPENSE', 300.00, tid='A3', memo='X', back='A1')]
        plain = [row('DELTA AIRLINES', 'TRAVEL EXPENSE', 250.00), row('GOLD SHIELD TRANSPORTATION', 'TRANSPORTATION', 500.00),
                 row('UNION CARD', 'SEE MEMOS', 90.00, tid='U1'),
                 row('HERTZ', 'TRAVEL EXPENSE', 20.00, tid='U2', memo='X', back='U1')]           # does not sum: parent stays Other
        body = numbers([parent, *kids, *plain], detail=True)
        self.assertEqual(body['payees']['travel'], [
            {'payee': 'DELTA AIRLINES', 'amount': 650.0, 'payments': 2},      # a card memo child plus a direct payment
            {'payee': 'GOLD SHIELD TRANSPORTATION', 'amount': 500.0, 'payments': 1},
            {'payee': 'MARRIOTT', 'amount': 300.0, 'payments': 1}])
        self.assertEqual([p['payee'] for p in body['payees']['other']], ['UNION CARD'])
        self.assertNotIn('AMERICAN EXPRESS', [p['payee'] for p in body['payees']['travel']])    # the parent is not also counted
        self.assertEqual(body['payments']['travel']['total'], 4)
        self.assertEqual(sum(item['amount'] for item in body['payments']['travel']['rows']), 1450.0)
        self.assertTrue(all(item['url'].startswith('https://docquery.fec.gov/') for item in body['payments']['travel']['rows']))

    def test_top_five_only_and_the_first_hundred_payments_with_the_count_of_the_rest(self):
        rows = [row(f'VENDOR {n}', 'TRAVEL EXPENSE', 10.0 + n, date=f'2024-01-{n % 28 + 1:02d}', sub=f'V{n}') for n in range(150)]
        body = numbers(rows, detail=True)
        self.assertEqual(len(body['payees']['travel']), 5)
        self.assertEqual(body['payees']['travel'][0]['payee'], 'VENDOR 149')
        self.assertEqual((len(body['payments']['travel']['rows']), body['payments']['travel']['total']), (100, 150))

    def test_a_payment_without_a_pdf_url_links_by_its_image_number(self):
        item = row('DELTA AIRLINES', 'TRAVEL EXPENSE', 10.0)
        item['pdf_url'] = None
        body = numbers([item], detail=True)
        self.assertEqual(body['payments']['travel']['rows'][0]['url'], 'https://docquery.fec.gov/cgi-bin/fecimg/?202501319748746337')


class Route(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        patcher = patch.dict(os.environ, {cs.FIXTURE_ENV: self.directory.name})
        patcher.start()
        self.addCleanup(patcher.stop)

    def save(self, candidate, rows=None, cycle=2024, status='complete', committee_id=None, **kwargs):
        rows = rows or [row('THE STANTON GROUP, LLC', 'FUNDRAISING CONSULTING', 600.00, sub=f'{candidate}1'),
                        row('DELTA AIRLINES', 'TRAVEL EXPENSE', 400.00, sub=f'{candidate}2')]
        item = committee(rows, committee_id=committee_id or 'C0' + candidate[-8:], status=status, **kwargs)
        (Path(self.directory.name) / f'{candidate}-{cycle}.json').write_text(json.dumps(result(item, candidate=candidate)), encoding='utf-8')

    def ask(self, **query):
        return cs.respond({key: [value] for key, value in query.items()})

    def test_not_collected_is_a_404_with_a_json_body_and_never_a_fetch(self):
        body, status = self.ask(candidate='H0KY06104', cycle='2024')
        self.assertEqual(status, 404)
        self.assertEqual(body['status'], 'mapping_unknown')                 # nothing in the source for it
        self.save('H0KY06104', [], status='pending', disbursements=None)
        body, status = self.ask(candidate='H0KY06104', cycle='2024')
        self.assertEqual((status, body['status'], body['error']), (404, 'not_collected', 'Spending not collected for 2023–24'))
        json.dumps(body)

    def test_a_collected_campaign_is_served_by_id_or_by_node_key(self):
        self.save('H0KY06104', committee_id=COMMITTEE)
        for key in ('H0KY06104', 'candidate:H0KY06104:support'):
            body, status = self.ask(candidate=key, cycle='2024')
            self.assertEqual(status, 200)
            self.assertEqual((body['committee_id'], body['committee_name'], body['cycle']), ('C00467571', 'ANDY BARR FOR CONGRESS, INC.', 2024))
            self.assertEqual((body['total_itemized'], body['reported_total'], body['coverage']), (1000.0, 1000.0, 1.0))
            self.assertEqual([(c['key'], c['amount'], c['share'], c['payments']) for c in body['categories']],
                             [('consulting', 600.0, 0.6, 1), ('travel', 400.0, 0.4, 1)])
            self.assertNotIn('payees', body)                         # the hover card stays light
        self.assertIn('payees', self.ask(candidate='H0KY06104', cycle='2024', detail='1')[0])

    def test_the_name_the_chart_sends_finds_the_candidates_own_reimbursements(self):
        self.save('H0KY06104', [row('BARR, GARLAND ANDY', 'CHILD CARE REIMBURSEMENT', 50.0, entity='IND', sub='R1'), row('DELTA AIRLINES', 'TRAVEL EXPENSE', 50.0, sub='R2')])
        with_name = self.ask(candidate='H0KY06104', cycle='2024', name='BARR, GARLAND ANDY')[0]
        self.assertIn('personal_reimb', amounts(with_name))

    def test_bad_requests_are_refused_not_guessed(self):
        for query in ({'candidate': 'nope', 'cycle': '2024'}, {'candidate': 'H0KY06104', 'cycle': '2023'}, {'candidate': 'H0KY06104'}):
            with self.assertRaises(ValueError):
                cs.respond({key: [value] for key, value in query.items()})

    def test_the_comparison_needs_five_complete_peers_of_the_same_office_and_cycle_among_those_offered(self):
        self.save('H0KY06104', committee_id=COMMITTEE)
        names = ['H0XX00000', 'H0XX00001', 'H0XX00002', 'H0XX00003']
        for number, candidate in enumerate(names):
            self.save(candidate, [row('X', 'TRAVEL EXPENSE', 10.0, sub=f'P{number}')])

        def peers(*offered):
            return self.ask(candidate='H0KY06104', cycle='2024', detail='1', peers=','.join(offered))[0]['peers']
        found = peers(*names)
        self.assertEqual((found['n'], found['too_few'], found['note']), (4, True, 'Too few collected campaigns to compare'))
        self.assertNotIn('shares', found)
        self.save('S0XX00009', [row('X', 'TRAVEL EXPENSE', 10.0)], committee_id='C00000099')          # a Senate campaign is no House peer
        self.assertEqual(peers(*names, 'S0XX00009', 'H0KY06104')['n'], 4)                                # nor is the campaign itself
        self.save('H0XX00004', [row('X', 'FUNDRAISING CONSULTING', 30.0, sub='P4'), row('X', 'TRAVEL EXPENSE', 10.0, sub='P5')])
        self.save('H0XX00005', [row('X', 'TRAVEL EXPENSE', 10.0, sub='P6')], status='partial', disbursements=None)   # partial: never a peer
        found = peers(*names, 'H0XX00004', 'H0XX00005')
        self.assertEqual((found['n'], found['too_few']), (5, False))
        self.assertEqual(found['label'], 'Median of 5 collected House campaigns, 2023–24')
        self.assertAlmostEqual(sum(found['shares'].values()), 1.0, places=5)
        self.assertEqual(found['shares']['travel'], 1.0)            # the median share of four all-travel campaigns and one 25% one
        self.assertEqual(self.ask(candidate='H0KY06104', cycle='2024', detail='1')[0]['peers']['n'], 0)   # none offered: none read

    def test_the_committed_fixtures_answer_through_the_route(self):
        with patch.dict(os.environ, {cs.FIXTURE_ENV: str(FIXTURES)}):
            barr, status = self.ask(candidate='H0KY06104', cycle='2024')
            self.assertEqual((status, barr['coverage_status'], barr['coverage'], barr['reported_total']), (200, 'partial', None, None))
            self.assertTrue(barr['coverage_unknown'])
            synthetic, _ = self.ask(candidate='H8ZZ00001', cycle='2024', name='ZED, ZACHARY', detail='1')
            self.assertEqual((synthetic['total_itemized'], synthetic['reported_total'], synthetic['coverage']), (71770.0, 153000.0, 0.4691))
            self.assertEqual(synthetic['own_transfers'], {'amount': 6000.0, 'rows': 2})
            self.assertEqual(synthetic['source']['duplicate_rows_dropped'], 1)
            self.assertEqual(synthetic['dropped_negative'][0]['key'], 'travel')
            self.assertEqual(synthetic['memo_handling']['resolved'], 1)
            self.assertEqual(synthetic['memo_handling']['unresolved'], 1)
            self.assertIn('personal_reimb', amounts(synthetic))
            self.assertEqual(self.ask(candidate='H0KY06104', cycle='2022')[1], 404)


if __name__ == '__main__':
    unittest.main()
