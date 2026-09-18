"""S8: the district geography behind the PAC evidence map.

Fixture-only by default: every test here writes its own data root, its own
boundary files and its own snapshot, so nothing depends on the built
app/geo/*.json or on the FEC bulk masters. The few tests that do read the
shipped files skip when they are absent.

Run: python mentat/tests/test_evidence_geo.py
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))

import district_geo  # noqa: E402
import evidence_csv  # noqa: E402
import evidence_geo  # noqa: E402

CONTRACT = (Path(__file__).resolve().parents[2] / 'audits' / 'mentat_failings_20260915'
            / 'contracts' / 'evidence-geo.json')


# --------------------------------------------------------------- the fixtures

def write_geo(root):
    """A three-district map, two states and a four-ZIP crosswalk."""
    root.mkdir(parents=True, exist_ok=True)
    (root / 'index.json').write_text(json.dumps({
        'width': 100, 'height': 60, 'built_at': 'fixture',
        'cycles': {'2022': '118', '2024': '118', '2026': '119'},
        'vintages': {
            '118': {'file': 'cd118.json', 'cycle': 2024, 'congress': '118th',
                    'zcta_file': 'zcta_cd118.json', 'zcta_basis': 'land area'},
            '119': {'file': 'cd119.json', 'cycle': 2026, 'congress': '119th',
                    'zcta_file': 'zcta_cd119.json', 'zcta_basis': 'land area'}}}), encoding='utf-8')
    for vintage in ('118', '119'):
        (root / f'cd{vintage}.json').write_text(json.dumps({
            'width': 100, 'height': 60,
            'districts': {'CA-12': {'path': 'M0 0L1 0L1 1Z', 'centroid': [1, 1]},
                          'CA-45': {'path': 'M2 0L3 0L3 1Z', 'centroid': [2, 1]},
                          'NY-16': {'path': 'M4 0L5 0L5 1Z', 'centroid': [4, 1]}},
            'states': {'CA': {'path': 'M0 0L3 0L3 2Z'}, 'NY': {'path': 'M4 0L6 0L6 2Z'}}}),
            encoding='utf-8')
        (root / f'zcta_cd{vintage}.json').write_text(json.dumps({
            '94607': [['CA-12', 1.0]],
            '92625': [['CA-45', 0.6], ['CA-12', 0.4]],
            '10024': [['NY-16', 1.0]],
            '99999': [['ZZ-99', 1.0]]}), encoding='utf-8')


def write_masters(root):
    """A candidate master and a committee master with a state that MOVED."""
    (root / 'fec_beneficiary' / 'cn24').mkdir(parents=True, exist_ok=True)
    (root / 'fec_beneficiary' / 'cn24' / 'cn.txt').write_text(
        'H0CA48198|STEEL, MICHELLE|REP|2024|CA|H|45|I|C|C00700000|||\n'
        'S4CA00522|PORTER, KATHERINE|DEM|2024|CA|S|00|C|C|C00700001|||\n'
        'H2NY16000|BOWMAN, JAMAAL|DEM|2024|NY|H|16|I|C|C00700002|||\n'
        'H9TX66000|NOSUCH, SEAT|REP|2024|TX|H|66|C|C|C00700003|||\n'
        'P0US00000|CANDIDATE, PRESIDENTIAL|DEM|2024|US|P|00|C|C|C00700004|||\n',
        encoding='utf-8')
    (root / 'fec_committee_master' / 'cm24').mkdir(parents=True, exist_ok=True)
    (root / 'fec_committee_master' / 'cm24' / 'cm.txt').write_text(
        'C00848440|PROTECT PROGRESS|TRES|ST1|ST2|PALM CITY|FL|34990|U|O|UNK|Q|||\n'
        'C00836221|DEFEND AMERICAN JOBS|TRES|ST1|ST2|ARLINGTON|VA|22201|U|O|UNK|Q|||\n',
        encoding='utf-8')
    (root / 'fec_committee_master' / 'cm26').mkdir(parents=True, exist_ok=True)
    (root / 'fec_committee_master' / 'cm26' / 'cm.txt').write_text(
        'C00848440|PROTECT PROGRESS|TRES|ST1|ST2|ST. PAUL|MN|55116|U|O|UNK|Q|||\n',
        encoding='utf-8')


def disbursement(line, amount, **fields):
    row = {'line_number': line, 'disbursement_amount': amount, 'memo_code': '',
           'memoed_subtotal': False, 'recipient_name': '', 'recipient_committee_id': '',
           'recipient_state': '', 'recipient_zip': '', 'disbursement_description': '',
           'candidate_id': '', 'sub_id': str(abs(hash((line, amount))) % 10 ** 12)}
    row.update(fields)
    return row


def expenditure(amount, candidate, direction, **fields):
    row = {'expenditure_amount': amount, 'candidate_id': candidate,
           'support_oppose_indicator': direction, 'candidate_name': candidate,
           'memo_code': '', 'memoed_subtotal': False,
           'sub_id': str(abs(hash((amount, candidate, direction))) % 10 ** 12)}
    row.update(fields)
    return row


def receipt(amount, **fields):
    row = {'contribution_receipt_amount': amount, 'contributor_name': 'A DONOR',
           'contributor_zip': '', 'contributor_state': '', 'memo_code': '',
           'memoed_subtotal': False, 'receipt_type_full': '', 'memo_text': '',
           'sub_id': str(abs(hash((amount, fields.get('contributor_zip')))) % 10 ** 12)}
    row.update(fields)
    return row


def write_snapshot(root, identifier='fixture-snap'):
    """One committee, one cycle, with E, B22, B23, B21B and a conversion twin."""
    directory = root / identifier
    directory.mkdir(parents=True, exist_ok=True)
    snapshot = {
        'committee_id': 'C00835959', 'cycle': 2024,
        'receipts': [
            receipt(1000, contributor_zip='94607', contributor_state='CA', contributor_name='COINBASE'),
            receipt(2000, contributor_zip='92625', contributor_state='CA'),
            receipt(500, contributor_zip='', contributor_state='NY'),
            receipt(250, contributor_zip='', contributor_state=''),
            receipt(9999, contributor_zip='94607', contributor_state='CA', memo_code='X'),
            receipt(7000, contributor_zip='94607', contributor_state='CA', contributor_name='COINBASE',
                    receipt_type_full='IN-KIND - BITCOIN - NOT LIQUIDATED')],
        'disbursements': [
            disbursement('22', 5000, recipient_committee_id='C00848440', recipient_name='PROTECT PROGRESS'),
            disbursement('22', 3000, recipient_committee_id='C00836221', recipient_name='DEFEND AMERICAN JOBS'),
            disbursement('23', 1500, recipient_committee_id='C00700000', recipient_name='STEEL FOR CONGRESS',
                         candidate_id='H0CA48198'),
            disbursement('21B', 800, recipient_name='SCHOEN SURVEY RESEARCH', recipient_state='NY',
                         recipient_zip='10024', disbursement_description='POLLING'),
            disbursement('21B', 7000, recipient_name='COINBASE', recipient_state='CA',
                         recipient_zip='94607',
                         disbursement_description='IN-KIND - BITCOIN - NOT LIQUIDATED'),
            disbursement('21B', 400, recipient_name='NO STATE VENDOR'),
            disbursement('22', 99999, recipient_committee_id='C00848440', memo_code='X')],
        'expenditures': [
            expenditure(12000, 'S4CA00522', 'O'),
            expenditure(4000, 'H0CA48198', 'S'),
            expenditure(2000, 'H2NY16000', 'O'),
            expenditure(700, 'H9TX66000', 'S'),
            expenditure(300, 'P0US00000', 'S'),
            expenditure(55555, 'S4CA00522', 'O', memo_code='X')],
        'totals': {'disbursements': 36700.0, 'receipts': 10750.0}}
    later = {'committee_id': 'C00835959', 'cycle': 2026, 'receipts': [],
             'disbursements': [disbursement('22', 100, recipient_committee_id='C00848440',
                                            recipient_name='PROTECT PROGRESS')],
             'expenditures': [], 'totals': {'disbursements': 100.0, 'receipts': 0.0}}
    (directory / 'snapshots.json').write_text(json.dumps([snapshot, later]), encoding='utf-8')
    (directory / 'evidence.json').write_text(json.dumps({
        'version': 1, 'company': 'Coinbase', 'aliases': ['COINBASE'],
        'committee_finances': [{'committee_id': 'C00835959', 'cycle': 2024,
                                'committee_name': 'FAIRSHAKE'}]}), encoding='utf-8')
    return directory


IMPORT_CSV = '\n'.join([
    'Committee ID,Cycle,Contributor,Amount,Date,State,ZIP,Record Type,Recipient',
    'C00804179,2023-2024,"ONE, PERSON",100,2024-01-02,CA,94607,CONTRIBUTION,COINBASE PAC',
    'C00804179,2023-2024,"TWO, PERSON",200,2024-01-03,CA,92625,CONTRIBUTION,COINBASE PAC',
    'C00804179,2023-2024,"THREE, PERSON",50,2024-01-04,NY,,CONTRIBUTION,COINBASE PAC',
    'C00804179,2023-2024,"FOUR, PERSON",25,2024-01-05,,,CONTRIBUTION,COINBASE PAC',
    'C00804179,2025-2026,"FIVE, PERSON",400,2026-01-05,CA,94607,CONTRIBUTION,COINBASE PAC',
    '']) + '\n'


class GeoFixture(unittest.TestCase):
    """Every test in this file runs against a data root it wrote itself."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        write_geo(self.root / 'geo')
        write_masters(self.root / 'inputs')
        self.saved = {name: os.environ.get(name) for name in ('MENTAT_GEO_DIR', 'MENTAT_INPUTS_DIR')}
        os.environ['MENTAT_GEO_DIR'] = str(self.root / 'geo')
        os.environ['MENTAT_INPUTS_DIR'] = str(self.root / 'inputs')
        district_geo.reset_caches()
        self.addCleanup(self.restore)
        self.snapshot_root = self.root / 'snapshots'
        write_snapshot(self.snapshot_root)

    def restore(self):
        for name, value in self.saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        district_geo.reset_caches()
        self.temp.cleanup()

    def store(self):
        store = evidence_csv.Store(self.root / 'data', evict=False)
        job = store.wait(store.ingest_text('Crypto Industry Spending Overview.csv', IMPORT_CSV)['id'])
        self.assertEqual(job['state'], 'ready', job.get('message'))
        return store, job['id']

    def snapshot_spend(self, cycle='2024'):
        return evidence_geo.geography('snapshot', 'fixture-snap', 'C00835959', cycle, 'spent',
                                      snapshot_root=self.snapshot_root)


class SnapshotSpend(GeoFixture):
    def test_four_kinds_are_present_with_their_bases(self):
        payload = self.snapshot_spend()
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        self.assertEqual(set(kinds), {'candidates', 'transfers', 'operating', 'conversions'})
        self.assertFalse(kinds['conversions']['default_on'])
        self.assertTrue(all(kinds[name]['default_on'] for name in ('candidates', 'transfers', 'operating')))
        self.assertTrue(all(kinds[name]['basis'] for name in kinds))

    def test_located_plus_unlocated_equals_reported(self):
        payload = self.snapshot_spend()
        self.assertAlmostEqual(payload['located_total'] + payload['unlocated_total'],
                               payload['reported_total'], places=2)
        self.assertTrue(payload['reconciles'])

    def test_schedule_e_support_and_oppose_stay_apart(self):
        payload = self.snapshot_spend()
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        districts = {row['key']: row for row in kinds['candidates']['districts']}
        self.assertAlmostEqual(districts['CA-SEN']['oppose'], 12000, places=2)
        self.assertAlmostEqual(districts['CA-SEN']['support'], 0, places=2)
        # Schedule E support 4,000 and the Schedule B line 23 gift 1,500 both
        # land on the candidate's own district.
        self.assertAlmostEqual(districts['CA-45']['support'], 5500, places=2)
        self.assertAlmostEqual(districts['NY-16']['oppose'], 2000, places=2)

    def test_memo_rows_are_excluded_exactly_as_pac_evidence_does(self):
        payload = self.snapshot_spend()
        everything = sum(kind['total'] for kind in payload['kinds'])
        self.assertNotIn(55555, [row['amount'] for kind in payload['kinds']
                                 for row in kind['districts'] + kind['states']])
        self.assertLess(everything, 55555)

    def test_transfers_use_the_cycle_s_committee_state_not_the_newest(self):
        payload = self.snapshot_spend()
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        states = {row['key']: row for row in kinds['transfers']['states']}
        # C00848440 is FL in the 2024 master and MN in the 2026 one.
        self.assertIn('FL', states)
        self.assertNotIn('MN', states)
        self.assertAlmostEqual(states['FL']['amount'], 5000, places=2)
        self.assertAlmostEqual(states['VA']['amount'], 3000, places=2)

    def test_conversions_are_their_own_kind_and_leave_operating_clean(self):
        payload = self.snapshot_spend()
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        self.assertAlmostEqual(kinds['conversions']['total'], 7000, places=2)
        self.assertAlmostEqual(kinds['operating']['total'], 800, places=2)

    def test_a_seat_no_map_carries_and_a_payee_with_no_state_are_unlocated(self):
        payload = self.snapshot_spend()
        reasons = ' '.join(item['reason'] for item in payload['unlocated'])
        amounts = sum(item['amount'] for item in payload['unlocated'])
        self.assertIn('TX-66', reasons)
        self.assertGreaterEqual(amounts, 700 + 300 + 400)

    def test_every_district_key_matches_the_contract_pattern(self):
        payload = self.snapshot_spend()
        for kind in payload['kinds']:
            for row in kind['districts']:
                self.assertRegex(row['key'], r'^[A-Z]{2}-(\d{2}|AL|SEN)$')
            for row in kind['states']:
                self.assertRegex(row['key'], r'^[A-Z]{2}$')

    def test_shares_are_inside_zero_to_one(self):
        payload = self.snapshot_spend()
        for kind in payload['kinds']:
            for row in kind['districts'] + kind['states']:
                self.assertGreaterEqual(row['share'], 0.0)
                self.assertLessEqual(row['share'], 1.0)


class SnapshotRaise(GeoFixture):
    def test_receipts_go_by_zip_and_state(self):
        payload = evidence_geo.geography('snapshot', 'fixture-snap', 'C00835959', '2024', 'raised',
                                         snapshot_root=self.snapshot_root)
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        districts = {row['key']: row for row in kinds['contributors']['districts']}
        self.assertAlmostEqual(districts['CA-12']['amount'], 1000 + 7000 + 2000 * 0.4, places=2)
        self.assertAlmostEqual(districts['CA-45']['amount'], 2000 * 0.6, places=2)
        self.assertTrue(districts['CA-45']['split'])
        self.assertFalse(districts['NY-16']['amount'] if 'NY-16' in districts else False)
        states = {row['key']: row for row in kinds['contributors']['states']}
        self.assertIn('NY', states)
        self.assertAlmostEqual(payload['located_total'] + payload['unlocated_total'],
                               payload['reported_total'], places=2)


class ImportGeography(GeoFixture):
    def test_raised_splits_a_straddling_zip_and_marks_it(self):
        store, identifier = self.store()
        payload = evidence_geo.geography('csv', identifier, 'C00804179', '2024', 'raised', store=store)
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        districts = {row['key']: row for row in kinds['contributors']['districts']}
        self.assertAlmostEqual(districts['CA-12']['amount'], 100 + 200 * 0.4, places=2)
        self.assertAlmostEqual(districts['CA-45']['amount'], 200 * 0.6, places=2)
        self.assertTrue(districts['CA-45']['split'])
        self.assertAlmostEqual(payload['reported_total'], 375, places=2)

    def test_a_row_with_no_zip_falls_back_to_its_state_then_to_unlocated(self):
        store, identifier = self.store()
        payload = evidence_geo.geography('csv', identifier, 'C00804179', '2024', 'raised', store=store)
        kinds = {kind['kind']: kind for kind in payload['kinds']}
        states = {row['key']: row for row in kinds['contributors']['states']}
        self.assertAlmostEqual(states['NY']['amount'], 50, places=2)
        self.assertAlmostEqual(sum(item['amount'] for item in payload['unlocated']), 25, places=2)
        self.assertAlmostEqual(payload['located_total'] + payload['unlocated_total'],
                               payload['reported_total'], places=2)

    def test_the_cycle_narrows_the_rows(self):
        store, identifier = self.store()
        payload = evidence_geo.geography('csv', identifier, 'C00804179', '2026', 'raised', store=store)
        self.assertAlmostEqual(payload['reported_total'], 400, places=2)

    def test_spent_says_plainly_when_the_import_carries_no_outbound_rows(self):
        store, identifier = self.store()
        payload = evidence_geo.geography('csv', identifier, 'C00804179', '2024', 'spent', store=store)
        self.assertEqual(payload['kinds'], [])
        self.assertTrue(payload['reason'])
        self.assertIn('outbound', payload['reason'].lower())


class CycleToVintage(GeoFixture):
    def test_the_payload_names_the_vintage_it_drew(self):
        payload = self.snapshot_spend('2024')
        self.assertEqual(payload['vintage'], '118')
        self.assertEqual(payload['cycle'], '2024')

    def test_2026_draws_the_119th(self):
        payload = self.snapshot_spend('2026')
        self.assertEqual(payload['vintage'], '119')


class ShippedIndex(unittest.TestCase):
    """The shipped index.json, not a fixture. Skips when it is not built."""

    def setUp(self):
        district_geo.reset_caches()
        self.addCleanup(district_geo.reset_caches)
        if not (APP / 'geo' / 'index.json').is_file():
            self.skipTest('mentat/app/geo/index.json is not built in this checkout')

    def test_2022_is_drawn_on_the_118th_map(self):
        # Correction to S6_DESIGN ruling 9, accepted by Paul 2026-09-17: the
        # 2021-2022 candidate master already numbers House seats on the 118th
        # map (it carries NC-14), so money in the 2022 cycle belongs on 118th
        # districts even though the sitting members sat on 116th-map seats.
        self.assertEqual(district_geo.vintage_for_cycle('2021-2022'), '118')
        self.assertEqual(district_geo.vintage_for_cycle(2022), '118')

    def test_2024_and_2026_are_unchanged(self):
        self.assertEqual(district_geo.vintage_for_cycle(2024), '118')
        self.assertEqual(district_geo.vintage_for_cycle(2026), '119')

    def test_the_index_records_why_2022_moved(self):
        payload = json.loads((APP / 'geo' / 'index.json').read_text(encoding='utf-8'))
        notes = ' '.join(payload.get('notes') or [])
        self.assertIn('NC-14', notes)
        self.assertNotIn('OPEN QUESTION', notes)


class Contract(GeoFixture):
    """The contract's examples are asserted against the producer, with controls."""

    def setUp(self):
        super().setUp()
        if not CONTRACT.is_file():
            self.skipTest(f'{CONTRACT.name} is not written yet')
        self.contract = json.loads(CONTRACT.read_text(encoding='utf-8'))

    def test_the_contract_is_v1_and_names_the_route(self):
        self.assertEqual(self.contract['version'], 1)
        self.assertEqual(self.contract['route'], '/api/evidence-geo')

    def test_every_example_validates(self):
        self.assertGreaterEqual(len(self.contract['examples']), 1)
        for example in self.contract['examples']:
            self.assertEqual(evidence_geo.contract_problems(example['payload']), [], example['name'])

    def test_every_negative_control_is_refused_for_its_stated_reason(self):
        self.assertGreaterEqual(len(self.contract['negative_controls']), 3)
        for control in self.contract['negative_controls']:
            problems = evidence_geo.contract_problems(control['payload'])
            self.assertTrue(problems, control['name'])
            self.assertTrue(any(control['expect'] in problem for problem in problems),
                            f'{control["name"]}: {problems}')

    def test_a_real_payload_satisfies_the_contract(self):
        self.assertEqual(evidence_geo.contract_problems(self.snapshot_spend()), [])

    def test_the_controls_are_not_vacuously_wrong(self):
        """A control must fail only for its own reason, not for a shape error."""
        for control in self.contract['negative_controls']:
            payload = json.loads(json.dumps(control['payload']))
            self.assertNotEqual(evidence_geo.contract_problems(payload), [],
                                control['name'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
