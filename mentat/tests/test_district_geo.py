"""district_geo against written fixtures, then against the shipped geography.

Two halves. The first builds a tiny data root in a temp directory - a
three-district vintage, a ZIP crosswalk, an eight-line candidate master, a
two-line committee master - and checks the resolution rules, including every
missing-file path. It needs nothing built and always runs.

The second reads the real files under mentat/app/geo and skips when they are
absent, because they are built by mentat/tools/build_district_geo.py from
Census downloads and a fresh checkout has not run it. Run:

    python mentat/tools/build_district_geo.py
    python mentat/tests/test_district_geo.py
"""
import json
import math
import os
import sys
import tempfile
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'app'
sys.path.insert(0, str(APP))
import district_geo  # noqa: E402

GEO = APP / 'geo'
KEY_PATTERN = r'^[A-Z]{2}-(\d{2}|AL|SEN)$'

# Three districts, the same shape the builder writes: DC as one at-large
# square, and two CA districts side by side.
FAKE_VINTAGE = {
    'vintage': '119', 'source': 'fixture', 'fetched_at': '2026-09-17T00:00:00+00:00',
    'cycle': 2026, 'width': 975, 'height': 610,
    'projection': {'kind': 'albers conic equal area, one conic per region',
                   'regions': {'lower48': {'parallels': [29.5, 45.5], 'meridian': -96.0,
                                           'origin': 37.5, 'scale': 1000.0,
                                           'translate': [480.0, 300.0], 'statefp': None}}},
    'districts': {
        'DC-AL': {'geoid': '1198', 'name': 'Delegate District (at Large)',
                  'path': 'M760 210 L780 210 780 225 760 225 Z',
                  'bbox': [760.0, 210.0, 780.0, 225.0], 'centroid': [770.0, 217.5],
                  'region': 'lower48'},
        'CA-12': {'geoid': '0612', 'name': 'Congressional District 12',
                  'path': 'M100 200 L130 200 130 230 100 230 Z',
                  'bbox': [100.0, 200.0, 130.0, 230.0], 'centroid': [115.0, 215.0],
                  'region': 'lower48'},
        'CA-13': {'geoid': '0613', 'name': 'Congressional District 13',
                  'path': 'M130 200 L160 200 160 230 130 230 Z',
                  'bbox': [130.0, 200.0, 160.0, 230.0], 'centroid': [145.0, 215.0],
                  'region': 'lower48'}},
    'states': {'CA': {'name': 'California', 'statefp': '06',
                      'path': 'M100 200 L160 200 160 230 100 230 Z',
                      'bbox': [100.0, 200.0, 160.0, 230.0], 'region': 'lower48'}},
    'undrawn': {'GU-AL': {'stusps': 'GU', 'name': 'Guam', 'statefp': '66',
                          'reason': 'no boundary in the 20m cartographic files'}},
    'unplaced': [], 'skipped': [], 'build': {'min_step_px': 0.5, 'decimals': 1}}

FAKE_CROSSWALK = {'94607': [['CA-12', 1.0]],
                  '95111': [['CA-13', 0.72], ['CA-12', 0.28]],
                  '20008': [['DC-AL', 1.0]],
                  '96910': [['GU-AL', 1.0]]}

# CAND_ID|NAME|PTY|ELECTION_YR|OFFICE_ST|OFFICE|OFFICE_DISTRICT|ICI|STATUS|PCC
FAKE_CN = '\n'.join([
    'H0CA12345|HOUSE, HOPE|DEM|2026|CA|H|12|I|C|C00000001',
    'H2AK00011|ATLARGE, ANNA|REP|2026|AK|H|00|C|C|C00000002',
    'S6CA00022|SENATE, SAM|DEM|2026|CA|S|00|I|C|C00000003',
    'P80000333|PRESIDENT, PAT|REP|2026|US|P|00|C|C|C00000004',
    'H4TX00044|OUTOFRANGE, OLLIE|REP|2026|TX|H|66|C|C|C00000005',
    'H8CA12346|MOVED, MORGAN|DEM|2024|CA|H|15|C|C|C00000006',
    'H0MP00055|DELEGATE, DANA|IND|2026|MP|H|01|I|C|C00000007',
    'H0AK00066|BLANK, BRETT|REP|2026|AK|H||C|C|C00000008',
]) + '\n'
FAKE_CM = '\n'.join([
    'C00000001|HOPE FOR CONGRESS|T, T|1 MAIN||OAKLAND|CA|94607|A|H|DEM|Q||HOPE|H0CA12345',
    'C00099999|DEFEND AMERICAN JOBS|T, T|2 OAK||ARLINGTON|VA|22201|U|O|UNK|M||X|',
]) + '\n'


def write_root(tmp, vintage=True, crosswalk=True, candidates=True, committees=True,
               index_cycles=None):
    """A data root with exactly the pieces asked for, so absence is testable."""
    root = Path(tmp)
    geo, inputs = root / 'geo', root / 'inputs'
    geo.mkdir(parents=True, exist_ok=True)
    cycles = {'2026': '119', '2024': '118', '2022': '116'} if index_cycles is None \
        else index_cycles
    vintages = {'119': {'file': 'cd119.json', 'cycle': 2026, 'districts': 3,
                        'zcta_file': 'zcta_cd119.json' if crosswalk else None,
                        'zcta_source': 'fixture',
                        'zcta_basis': 'land area (AREALAND_PART)'},
                '118': {'file': 'cd118.json', 'cycle': 2024, 'districts': 0,
                        'zcta_file': 'zcta_cd118.json', 'zcta_basis': 'land area'},
                '116': {'file': 'cd116.json', 'cycle': 2022, 'districts': 0,
                        'zcta_file': None}}
    (geo / 'index.json').write_text(json.dumps({'width': 975, 'height': 610,
                                                'cycles': cycles, 'vintages': vintages}),
                                    encoding='utf-8')
    if vintage:
        (geo / 'cd119.json').write_text(json.dumps(FAKE_VINTAGE), encoding='utf-8')
    if crosswalk:
        (geo / 'zcta_cd119.json').write_text(json.dumps(FAKE_CROSSWALK), encoding='utf-8')
    if candidates:
        (inputs / 'fec_beneficiary' / 'cn26').mkdir(parents=True, exist_ok=True)
        (inputs / 'fec_beneficiary' / 'cn26' / 'cn.txt').write_text(FAKE_CN, encoding='utf-8')
    if committees:
        (inputs / 'fec_committee_master' / 'cm26').mkdir(parents=True, exist_ok=True)
        (inputs / 'fec_committee_master' / 'cm26' / 'cm.txt').write_text(FAKE_CM,
                                                                        encoding='utf-8')
    inputs.mkdir(parents=True, exist_ok=True)
    return geo, inputs


class FixtureTests(unittest.TestCase):
    """Every rule, against a data root this test wrote."""

    def setUp(self):
        self.previous = {name: os.environ.get(name)
                         for name in ('MENTAT_GEO_DIR', 'MENTAT_INPUTS_DIR')}
        district_geo.reset_caches()

    def tearDown(self):
        for name, value in self.previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        district_geo.reset_caches()

    def point(self, **kwargs):
        tmp = tempfile.mkdtemp()
        geo, inputs = write_root(tmp, **kwargs)
        os.environ['MENTAT_GEO_DIR'] = str(geo)
        os.environ['MENTAT_INPUTS_DIR'] = str(inputs)
        district_geo.reset_caches()
        return geo, inputs

    def test_cycle_resolves_to_the_vintage_the_index_names(self):
        self.point()
        self.assertEqual(district_geo.vintage_for_cycle(2026), '119')
        self.assertEqual(district_geo.vintage_for_cycle('2023-2024'), '118')
        self.assertEqual(district_geo.vintage_for_cycle('2021–2022'), '116')
        self.assertEqual(district_geo.vintage_for_cycle(2023), '118')
        self.assertEqual(district_geo.load_vintage(2026)['vintage'], '119')
        self.assertEqual(sorted(district_geo.load_vintage('2025-2026')['districts']),
                         ['CA-12', 'CA-13', 'DC-AL'])
        self.assertIsNone(district_geo.vintage_for_cycle(2018))
        self.assertIn('2018', district_geo.last_problem)
        self.assertIsNone(district_geo.vintage_for_cycle('all cycles'))
        self.assertIn('not a cycle', district_geo.last_problem)

    def test_a_cycle_whose_vintage_file_is_missing_reports_it(self):
        self.point(vintage=False)
        self.assertIsNone(district_geo.load_vintage(2026))
        self.assertIn('cd119.json', district_geo.last_problem)
        self.assertFalse(district_geo.district_exists('CA-12', 2026))

    def test_zip_lookup_returns_shares_largest_first(self):
        self.point()
        self.assertEqual(district_geo.district_for_zip('94607', 2026), [('CA-12', 1.0)])
        self.assertEqual(district_geo.district_for_zip('95111-1234', 2026),
                         [('CA-13', 0.72), ('CA-12', 0.28)])
        self.assertEqual(sum(share for _, share in
                             district_geo.district_for_zip('95111', 2026)), 1.0)
        self.assertEqual(district_geo.district_for_zip('20008', '2025-2026'), [('DC-AL', 1.0)])
        self.assertEqual(district_geo.zip_basis(2026)['vintage'], '119')
        self.assertIn('land area', district_geo.zip_basis(2026)['basis'])

    def test_zip_lookup_refuses_rather_than_guess(self):
        self.point()
        self.assertEqual(district_geo.district_for_zip('1234', 2026), [])
        self.assertIn('five-digit', district_geo.last_problem)
        self.assertEqual(district_geo.district_for_zip(None, 2026), [])
        self.assertEqual(district_geo.district_for_zip('99999', 2026), [])
        self.assertIn('99999', district_geo.last_problem)
        # the 116th map has no crosswalk at all: nothing is substituted
        self.assertEqual(district_geo.district_for_zip('94607', 2022), [])
        self.assertIn('crosswalk', district_geo.last_problem)
        self.assertIsNone(district_geo.zip_basis(2022))

    def test_zip_lookup_with_no_crosswalk_file_reports_it(self):
        self.point(crosswalk=False)
        self.assertEqual(district_geo.district_for_zip('94607', 2026), [])
        self.assertIn('crosswalk', district_geo.last_problem)

    def test_candidate_lookup_covers_house_senate_president_and_at_large(self):
        self.point()
        self.assertEqual(district_geo.district_for_candidate('H0CA12345', 2026), 'CA-12')
        self.assertEqual(district_geo.district_for_candidate('H2AK00011', 2026), 'AK-AL')
        self.assertEqual(district_geo.district_for_candidate('S6CA00022', 2026), 'CA-SEN')
        self.assertEqual(district_geo.district_for_candidate('P80000333', 2026), 'US-PRES')
        self.assertEqual(district_geo.district_for_candidate('h0ca12345 ', '2025-2026'), 'CA-12')
        self.assertEqual(district_geo.district_for_candidate('H0CA12345'), 'CA-12')

    def test_a_delegate_seat_reads_at_large_whichever_code_the_master_used(self):
        self.point()
        # The FEC writes the Marianas delegate as district 01, the Census as
        # CD..FP 98; both mean the one seat the islands have.
        self.assertEqual(district_geo.district_for_candidate('H0MP00055', 2026), 'MP-AL')
        # A blank district is a gap in the master, not an at-large seat.
        self.assertIsNone(district_geo.district_for_candidate('H0AK00066', 2026))
        self.assertIn('no FEC candidate master', district_geo.last_problem)

    def test_candidate_district_the_map_has_no_seat_for_is_reported_not_dropped(self):
        self.point()
        self.assertEqual(district_geo.district_for_candidate('H4TX00044', 2026), 'TX-66')
        self.assertFalse(district_geo.district_exists('TX-66', 2026))
        self.assertTrue(district_geo.district_exists('CA-12', 2026))
        self.assertTrue(district_geo.district_exists('GU-AL', 2026))   # a seat, undrawn
        self.assertFalse(district_geo.district_exists('CA-SEN', 2026))

    def test_candidate_lookup_falls_back_to_another_cycle_and_says_so(self):
        geo, inputs = self.point()
        (inputs / 'fec_beneficiary' / 'cn24').mkdir(parents=True, exist_ok=True)
        (inputs / 'fec_beneficiary' / 'cn24' / 'cn.txt').write_text(
            'H9CA99999|OLD, OLIVER|DEM|2024|CA|H|09|C|C|C00000009\n', encoding='utf-8')
        district_geo.reset_caches()
        self.assertEqual(district_geo.district_for_candidate('H9CA99999', 2026), 'CA-09')
        self.assertIn('2024', district_geo.last_problem)
        self.assertEqual(district_geo.district_for_candidate('H8CA12346', 2026), 'CA-15')

    def test_candidate_lookup_refuses_unknown_input_and_missing_files(self):
        self.point()
        self.assertIsNone(district_geo.district_for_candidate('nonsense', 2026))
        self.assertIn('not an FEC candidate id', district_geo.last_problem)
        self.assertIsNone(district_geo.district_for_candidate(None, 2026))
        self.assertIsNone(district_geo.district_for_candidate('H9ZZ00000', 2026))
        self.assertIn('no FEC candidate master', district_geo.last_problem)
        self.point(candidates=False)
        self.assertIsNone(district_geo.district_for_candidate('H0CA12345', 2026))
        self.assertIn('not available', district_geo.last_problem)

    def test_committee_state_comes_from_the_committee_master(self):
        self.point()
        self.assertEqual(district_geo.committee_state('C00099999'), 'VA')
        self.assertEqual(district_geo.committee_state('c00000001'), 'CA')
        self.assertIsNone(district_geo.committee_state('C00000002'))
        self.assertIn('no FEC committee master', district_geo.last_problem)
        self.assertIsNone(district_geo.committee_state('not-an-id'))
        self.assertIn('not an FEC committee id', district_geo.last_problem)
        self.point(committees=False)
        self.assertIsNone(district_geo.committee_state('C00099999'))
        self.assertIn('not available', district_geo.last_problem)

    def test_nothing_raises_when_the_whole_data_root_is_empty(self):
        tmp = tempfile.mkdtemp()
        os.environ['MENTAT_GEO_DIR'] = str(Path(tmp) / 'geo')
        os.environ['MENTAT_INPUTS_DIR'] = str(Path(tmp) / 'inputs')
        district_geo.reset_caches()
        self.assertIsNone(district_geo.load_vintage(2026))
        self.assertIn('index', district_geo.last_problem)
        self.assertEqual(district_geo.district_for_zip('94607', 2026), [])
        self.assertIsNone(district_geo.district_for_candidate('H0CA12345', 2026))
        self.assertIsNone(district_geo.committee_state('C00099999'))
        self.assertIsNone(district_geo.index())

    def test_a_corrupt_index_is_a_problem_not_a_crash(self):
        geo, _ = self.point()
        (geo / 'index.json').write_text('{not json', encoding='utf-8')
        district_geo.reset_caches()
        self.assertIsNone(district_geo.load_vintage(2026))
        self.assertIn('not valid JSON', district_geo.last_problem)


def albers(longitude, latitude, region):
    """The projection the vintage file documents, implemented from its numbers."""
    first, second = (math.radians(value) for value in region['parallels'])
    n = (math.sin(first) + math.sin(second)) / 2
    c = math.cos(first) ** 2 + 2 * n * math.sin(first)
    rho = math.sqrt(max(c - 2 * n * math.sin(math.radians(latitude)), 0.0)) / n
    rho0 = math.sqrt(max(c - 2 * n * math.sin(math.radians(region['origin'])), 0.0)) / n
    theta = n * (math.radians(longitude) - math.radians(region['meridian']))
    x, y = rho * math.sin(theta), rho0 - rho * math.cos(theta)
    return (region['translate'][0] + region['scale'] * x,
            region['translate'][1] - region['scale'] * y)


@unittest.skipUnless((GEO / 'cd119.json').is_file(),
                     'run mentat/tools/build_district_geo.py first')
class BuiltGeographyTests(unittest.TestCase):
    """The shipped files, read the way the page will read them."""

    @classmethod
    def setUpClass(cls):
        cls.vintage = json.loads((GEO / 'cd119.json').read_text(encoding='utf-8'))

    def setUp(self):
        for name in ('MENTAT_GEO_DIR', 'MENTAT_INPUTS_DIR'):
            os.environ.pop(name, None)
        district_geo.reset_caches()

    def test_the_shipped_index_draws_2022_on_the_118th_map(self):
        # S8, Paul 2026-09-17, correcting ruling 9: the map answers where the
        # MONEY went and cn22 already numbers House seats on the 118th map (it
        # carries NC-14), so cycle 2022 draws the 118th. The 116th paths stay
        # shipped for anyone reading where the members SAT; no cycle uses them.
        self.assertEqual(district_geo.vintage_for_cycle(2022), '118')
        self.assertEqual(district_geo.vintage_for_cycle('2021-2022'), '118')
        self.assertEqual(district_geo.vintage_for_cycle(2024), '118')
        self.assertEqual(district_geo.vintage_for_cycle(2026), '119')
        self.assertTrue((GEO / 'cd116.json').is_file(),
                        'the 116th map stays shipped even though no cycle points at it')

    def test_every_district_key_matches_the_agreed_shape(self):
        import re
        bad = [key for key in self.vintage['districts'] if not re.match(KEY_PATTERN, key)]
        self.assertEqual(bad, [])

    def test_california_has_fifty_two_house_districts_on_the_119th_map(self):
        keys = [key for key in self.vintage['districts'] if key.startswith('CA-')]
        self.assertEqual(len(keys), 52)
        self.assertEqual(len(self.vintage['districts']), 437)      # 435 + DC + PR
        self.assertIn('DC-AL', self.vintage['districts'])

    def test_washington_dc_projects_inside_the_dc_district(self):
        region = self.vintage['projection']['regions']['lower48']
        x, y = albers(-77.0369, 38.9072, region)
        x0, y0, x1, y1 = self.vintage['districts']['DC-AL']['bbox']
        self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1,
                        f'DC projects to ({x:.1f}, {y:.1f}), outside {[x0, y0, x1, y1]}')
        self.assertTrue(0 <= x <= self.vintage['width']
                        and 0 <= y <= self.vintage['height'])

    def test_every_centroid_sits_inside_its_own_bbox(self):
        for key, district in self.vintage['districts'].items():
            x, y = district['centroid']
            x0, y0, x1, y1 = district['bbox']
            self.assertTrue(x0 <= x <= x1 and y0 <= y <= y1, key)

    @unittest.skipUnless((GEO / 'zcta_cd119.json').is_file(), 'no crosswalk built')
    def test_the_real_crosswalk_places_two_known_zips(self):
        self.assertEqual(district_geo.district_for_zip('94607', 2026)[0][0], 'CA-12')
        self.assertEqual(district_geo.district_for_zip('20008', 2026), [('DC-AL', 1.0)])
        for zip5 in ('94607', '20008'):
            parts = district_geo.district_for_zip(zip5, 2026)
            self.assertAlmostEqual(sum(share for _, share in parts), 1.0, places=9)

    @unittest.skipUnless((Path(__file__).resolve().parents[1] / 'inputs'
                          / 'fec_beneficiary' / 'cn26' / 'cn.txt').is_file(),
                         'no FEC candidate master in this checkout')
    def test_the_real_candidate_master_answers_and_flags_seats_that_do_not_exist(self):
        key = district_geo.district_for_candidate('H0AL01055', 2026)   # Carl, AL-01
        self.assertEqual(key, 'AL-01')
        self.assertTrue(district_geo.district_exists(key, 2026))
        self.assertIsNone(district_geo.district_for_candidate('H0ZZ99999', 2026))


if __name__ == '__main__':
    unittest.main(verbosity=2)
