"""Schema-2 (Mentat-anchored) Giving Forecast calculator, asserted against the shared contract fixtures and ADDENDUM section F.

The bundle and the anchor snapshot come from mentat/forecast/contracts (the same example files the R writer and the anchor builder are
asserted against, brain DE-021). The anchors example is real builder output for banks and credit unions, so the numbers below are the
section F numbers of the phase-2 design, reproduced by the console's own calculator."""
import copy
from datetime import date
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'app'))
sys.path.insert(0, str(ROOT / 'forecast' / 'contracts'))
import contract  # noqa: E402
import giving_forecast as gf  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / 'fixtures' / 'giving_forecast_v2_render.json'
BANKS, CUS = 'commercial_banks', 'credit_unions'


class Today(date):
    @classmethod
    def today(cls):
        return cls(2026, 9, 30)


class World:
    """Bundle + anchors installed from the contract examples (optionally mutated) into a temp folder, with the published-workbook check patched."""

    def __init__(self, tmp, bundle=None, anchors=None, published=None):
        self.dir = Path(tmp)
        self.bundle = bundle or contract.example('models')
        self.anchors = anchors or contract.example('anchors')
        (self.dir / 'models.json').write_text(json.dumps(self.bundle))
        (self.dir / 'anchors.json').write_text(json.dumps(self.anchors))
        shas = {i['mentat']['workbook']: i['mentat'].get('workbook_sha256') for i in self.anchors['industries'].values()}
        self.published = published if published is not None else shas
        self.patches = [patch.dict(os.environ, {'MENTAT_GIVING_MODELS': str(self.dir / 'models.json'), 'MENTAT_GIVING_ANCHORS': str(self.dir / 'anchors.json')}),
                        patch.object(gf, 'date', Today), patch.object(gf, '_published_workbook_sha256', lambda name: self.published.get(name))]

    def __enter__(self):
        gf._load.cache_clear()
        gf._load_anchors.cache_clear()
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self.patches):
            p.stop()
        gf._load.cache_clear()
        gf._load_anchors.cache_clear()


def scenario(sector=BANKS, growth='mean', scores=None, dg=(0, 0, 0), as_of='2026-09-30', control=(1, 1)):
    """The owner scenario of ADDENDUM section F: 2026 growth = the industry's mean growth; the Polymarket January-June 2026 scores."""
    b = contract.example('models')
    industry = b['industries'][sector]
    outlook = b['saved_outlook']['control']
    scores = scores or {'House': outlook['House']['value'], 'Senate': outlook['Senate']['value']}
    changes = {'2026': dg[0], '2027': dg[1], '2028': dg[2]}
    request = dict(industry=sector, as_of=as_of, horizons={})
    for cycle in (2026, 2028):
        g = industry['growth_mean'] if growth == 'mean' else growth
        request['horizons'][str(cycle)] = dict(growth_pct=g, current_control={'House': control[0], 'Senate': control[1]}, control_scores=dict(scores),
                                               annual_forecast_changes=changes)
    return request


def run(request, **world):
    with tempfile.TemporaryDirectory() as tmp, World(tmp, **world):
        return gf.project(request)


def near(test, actual, expected, places=0):
    test.assertAlmostEqual(actual, expected, places=places, msg=f'{actual} != {expected}')


class SectionFTests(unittest.TestCase):
    """ADDENDUM F.2 (PAC), F.3 (share) and F.4 (lobbying), banks and credit unions."""

    @classmethod
    def setUpClass(cls):
        cls.out = {}
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            for sector in (BANKS, CUS):
                cls.out[sector] = gf.project(scenario(sector))
                cls.out[sector + ':eq'] = gf.project(scenario(sector, scores={'House': 19.03485027624309, 'Senate': 56.39529613}))
                cls.out[sector + ':lob'] = {dg: gf.project(scenario(sector, dg=(dg, 0, 0))) for dg in (-1, 0, 1)}

    def measure(self, sector, mid, horizon=0):
        return next(m for m in self.out[sector]['horizons'][horizon]['pac']['measures'] if m['id'] == mid)

    # --- F.2 ---------------------------------------------------------------------------------------------------------------------
    def test_pac_relative_change_and_intervals_use_each_industrys_own_slope(self):
        expected = {BANKS: (13.207, (-16.679, 53.814), (-38.076, 106.961)), CUS: (12.593, (-12.864, 45.488), (-23.381, 65.459))}
        for sector, (change, coef, pred) in expected.items():
            pac = self.out[sector]['horizons'][0]['pac']
            with self.subTest(sector=sector):
                self.assertEqual(pac['slope']['label'], 'industry-specific slope')
                near(self, pac['change_pct'], change, 2)
                near(self, pac['coefficient_interval_pct'][0], coef[0], 2)
                near(self, pac['coefficient_interval_pct'][1], coef[1], 2)
                near(self, pac['prediction_interval_pct'][0], pred[0], 2)
                near(self, pac['prediction_interval_pct'][1], pred[1], 2)

    def test_pac_table_reproduces_section_f2_to_the_dollar(self):
        # (anchor nominal, anchor 2025 USD, projection, coef low, coef high, pred low, pred high, observed, remainder)
        table = {
            (BANKS, 'pac_to_candidates'): (5692500, 5926312, 6709026, 4937854, 9115504, 3669835, 12265136, 4673000, 2036026),
            (BANKS, 'general_giving'): (26107204, 27179525, 30769242, 22646213, 41805943, 16830766, 56250931, 11566805, 19202438),
            (CUS, 'pac_to_candidates'): (80800, 84119, 94712, 73298, 122382, 64451, 139182, 54500, 40212),
            (CUS, 'general_giving'): (779088, 811088, 913231, 706752, 1180033, 621446, 1342017, 272141, 641090),
        }
        for (sector, mid), expected in table.items():
            m = self.measure(sector, mid)
            actual = (m['anchor_cycle_nominal'], m['anchor_cycle_real_2025'], m['projected_cycle_real_2025'], m['cycle_coefficient_low'], m['cycle_coefficient_high'],
                      m['cycle_prediction_low'], m['cycle_prediction_high'], m['observed']['amount_nominal'], m['projected_remaining'])
            with self.subTest(sector=sector, measure=mid):
                for a, e in zip(actual, expected):
                    self.assertLessEqual(abs(round(a) - e), 1, f'{a} vs {e} in {actual}')
                self.assertEqual(m['remainder_status'], 'ready')

    def test_the_two_pac_measures_are_side_by_side_never_summed(self):
        pac = self.out[BANKS]['horizons'][0]['pac']
        self.assertEqual([m['id'] for m in pac['measures']], ['pac_to_candidates', 'general_giving'])
        self.assertNotIn('total', pac)
        self.assertNotEqual(pac['measures'][0]['projected_cycle_real_2025'], pac['measures'][1]['projected_cycle_real_2025'])

    def test_remainder_starts_the_day_after_the_coverage_end(self):
        self.assertEqual(self.out[BANKS]['horizons'][0]['starts'], '2026-07-01')
        self.assertEqual(self.out[CUS]['horizons'][0]['starts'], '2026-06-01')           # credit unions are cut back to 2026-05-31
        self.assertEqual(self.measure(CUS, 'general_giving')['observed']['through'], '2026-05-31')
        self.assertEqual(self.out[BANKS]['anchors']['coverage_end'], '2026-06-30')

    def test_cpi_is_missing_for_2026_so_observed_amounts_are_face_value_and_say_so(self):
        self.assertTrue(self.measure(BANKS, 'general_giving')['observed']['face_value'])
        self.assertTrue(self.out[BANKS]['anchors']['face_value_current_cycle'])
        self.assertAlmostEqual(self.out[BANKS]['anchors']['cpi_multiplier'], 1.0410737386804656, places=12)

    def test_credit_union_pac_channel_carries_the_single_pac_thin_base_flag(self):
        self.assertIn('single_pac_thin_base', self.measure(CUS, 'pac_to_candidates')['flags'])
        self.assertNotIn('single_pac_thin_base', self.measure(BANKS, 'pac_to_candidates')['flags'])

    def test_next_cycle_is_chained_on_the_anchor_with_widened_prediction_variance(self):
        for sector in (BANKS, CUS):
            pac0, pac1 = (self.out[sector]['horizons'][i]['pac'] for i in (0, 1))
            with self.subTest(sector=sector):
                self.assertEqual((pac0['steps'], pac0['chained']), (1, False))
                self.assertEqual((pac1['steps'], pac1['chained']), (2, True))
                self.assertEqual(pac1['anchor_cycle'], 2024)
                self.assertNotIn('projected_remaining', pac1['measures'][0])            # no observed amounts for the next cycle
                # same growth, so the same point; the prediction interval is wider by the second step's residual variance
                near(self, pac1['change_pct'], pac0['change_pct'], 9)
                w0 = pac0['prediction_interval_pct'][1] - pac0['prediction_interval_pct'][0]
                w1 = pac1['prediction_interval_pct'][1] - pac1['prediction_interval_pct'][0]
                self.assertGreater(w1, w0)
                self.assertEqual(pac1['coefficient_interval_pct'], pac0['coefficient_interval_pct'])

    # --- F.3 ---------------------------------------------------------------------------------------------------------------------
    def chamber(self, key, chamber, horizon=0):
        return self.out[key]['horizons'][horizon]['shares'][chamber]

    def basis(self, key, chamber, bid):
        return next(b for b in self.chamber(key, chamber)['bases'] if b['id'] == bid)

    def test_share_pp_change_on_polymarket_to_polymarket_inputs(self):
        # Polymarket-only sensitivity column of F.3, the owner's primary: pp change [coefficient 95%]
        expected = {(BANKS, 'House'): (-0.939, -3.004, 1.126), (CUS, 'House'): (-1.251, -3.147, 0.645),
                    (BANKS, 'Senate'): (11.632, 2.965, 20.300), (CUS, 'Senate'): (10.251, 2.370, 18.131)}
        for (sector, chamber), (change, low, high) in expected.items():
            s = self.chamber(sector, chamber)
            b = self.basis(sector, chamber, 'employee_candidate')
            with self.subTest(sector=sector, chamber=chamber):
                near(self, s['change_pp'], change, 2)
                near(self, 100 * (b['cycle_coefficient_low'] - b['anchor_share']), low, 2)
                near(self, 100 * (b['cycle_coefficient_high'] - b['anchor_share']), high, 2)

    def test_share_pp_change_on_the_equal_weight_sensitivity_matches_the_f3_table(self):
        expected = {(BANKS, 'House'): (-0.892, -2.949, 1.165), (CUS, 'House'): (-1.204, -3.090, 0.681),
                    (BANKS, 'Senate'): (11.343, 2.723, 19.963), (CUS, 'Senate'): (9.961, 2.131, 17.791)}
        for (sector, chamber), (change, low, high) in expected.items():
            s = self.chamber(sector + ':eq', chamber)
            b = self.basis(sector + ':eq', chamber, 'employee_candidate')
            with self.subTest(sector=sector, chamber=chamber):
                near(self, s['change_pp'], change, 2)
                near(self, 100 * (b['cycle_coefficient_low'] - b['anchor_share']), low, 2)
                near(self, 100 * (b['cycle_coefficient_high'] - b['anchor_share']), high, 2)

    def test_share_anchors_on_both_bases_side_by_side_match_f3(self):
        # (employee anchor -> projected, PAC anchor -> projected) on the equal-weight inputs of the F.3 table
        expected = {(BANKS, 'House'): ((0.3435, 0.3345), (0.5436, 0.5347)), (BANKS, 'Senate'): ((0.5144, 0.6278), (0.6450, 0.7584)),
                    (CUS, 'House'): ((0.4407, 0.4286), (0.4063, 0.3943)), (CUS, 'Senate'): ((0.0868, 0.1864), (0.0000, 0.0996))}
        for (sector, chamber), (employee, pac) in expected.items():
            for bid, (anchor, projected) in zip(('employee_candidate', 'pac_candidate'), (employee, pac)):
                b = self.basis(sector + ':eq', chamber, bid)
                with self.subTest(sector=sector, chamber=chamber, basis=bid):
                    near(self, b['anchor_share'], anchor, 4)
                    near(self, b['projected_cycle_R_share'], projected, 4)
        self.assertEqual([b['id'] for b in self.chamber(BANKS, 'House')['bases']], ['employee_candidate', 'pac_candidate'])

    def test_thin_base_is_flagged_per_basis_and_chamber_below_100k(self):
        thin = {(CUS, 'House', 'employee_candidate'): True, (CUS, 'House', 'pac_candidate'): True, (CUS, 'Senate', 'employee_candidate'): False,
                (CUS, 'Senate', 'pac_candidate'): True, (BANKS, 'House', 'employee_candidate'): False, (BANKS, 'Senate', 'pac_candidate'): False}
        for (sector, chamber, bid), expected in thin.items():
            b = self.basis(sector, chamber, bid)
            with self.subTest(sector=sector, chamber=chamber, basis=bid):
                self.assertIs(b['thin_base'], expected)
                self.assertEqual('thin_base' in b['flags'], expected)
        self.assertAlmostEqual(self.basis(CUS, 'House', 'employee_candidate')['anchor_total_nominal'], 55123.94, places=2)
        self.assertAlmostEqual(self.basis(CUS, 'Senate', 'pac_candidate')['anchor_total_nominal'], 5000.0, places=2)

    def test_the_2024_house_window_is_flagged_131_of_182_days(self):
        house, senate = self.chamber(BANKS, 'House')['anchor_input'], self.chamber(BANKS, 'Senate')['anchor_input']
        self.assertEqual((house['days'], house['expected_days'], house['partial_window'], house['market']), (131, 182, True, 'polymarket'))
        self.assertEqual(house['first_day'], '2024-02-21')
        self.assertEqual((senate['days'], senate['expected_days'], senate['partial_window']), (182, 182, False))

    def test_combined_reference_remainder_reproduces_f3(self):
        # F.3 (equal-weight inputs): projected two-party total, observed D / R, remaining D / R, remaining R share
        expected = {(BANKS, 'House'): (7978102, 2637920, 2241699, 1546004, 1552479, 0.5010), (BANKS, 'Senate'): (2827597, 754284, 1082965, 166944, 823404, 0.8314),
                    (CUS, 'Senate'): (232183, 12048, 4500, 177372, 38264, 0.1774)}
        for (sector, chamber), (total, od, orr, rd, rr, share) in expected.items():
            c = self.chamber(sector + ':eq', chamber)['combined_reference']
            with self.subTest(sector=sector, chamber=chamber):
                self.assertEqual(c['remainder_status'], 'ready')
                for actual, e in ((c['projected_total_real_2025'], total), (c['observed']['D'], od), (c['observed']['R'], orr),
                                  (c['projected_remaining_D_real_2025'], rd), (c['projected_remaining_R_real_2025'], rr)):
                    self.assertLessEqual(abs(round(actual) - e), 1, f'{actual} vs {e}')
                near(self, c['projected_remaining_R_share'], share, 4)
        cu_house = self.chamber(CUS + ':eq', 'House')['combined_reference']
        self.assertEqual(cu_house['remainder_status'], 'budget_inconsistent')           # observed R already exceeds the projected R total; not clipped
        self.assertLess(cu_house['projected_remaining_R_real_2025'], 0)
        self.assertLessEqual(abs(round(cu_house['projected_total_real_2025']) - 153466), 1)

    def test_each_basis_carries_its_own_remainder(self):
        for sector in (BANKS, CUS):
            for chamber in ('House', 'Senate'):
                for b in self.chamber(sector, chamber)['bases']:
                    with self.subTest(sector=sector, chamber=chamber, basis=b['id']):
                        self.assertIn(b['remainder_status'], ('ready', 'budget_inconsistent'))
                        self.assertIn('projected_total_real_2025', b)
                        self.assertEqual(b['observed']['through'], '2026-06-30' if sector == BANKS else '2026-05-31')
        ready = self.basis(BANKS, 'Senate', 'employee_candidate')
        self.assertEqual(ready['remainder_status'], 'ready')
        self.assertAlmostEqual(ready['projected_remaining_R_share'], ready['projected_remaining_R_real_2025'] / (ready['projected_remaining_R_real_2025'] + ready['projected_remaining_D_real_2025']))

    # --- F.4 ---------------------------------------------------------------------------------------------------------------------
    def lobby(self, sector, dg=0, year=2026):
        rows = self.out[sector + ':lob'][dg]['horizons'][0]['lobbying']['rows']
        return {s['id']: s for s in next(r for r in rows if r['year'] == year)['series']}

    def test_lobbying_table_reproduces_section_f4(self):
        # (2025 level, dg=-1, dg=0, dg=+1, prediction low/high at dg=0, observed Q1+Q2, Q3+Q4 remainder at dg=0)
        table = {(BANKS, 'income_total'): (23824000, 24018902, 23824000, 23630679, 17523803, 32389257, 13367000, 10457000),
                 (BANKS, 'expenses_total'): (65696931, 66234392, 65696931, 65163831, 48323544, 89316437, 38975000, 26721931),
                 (CUS, 'income_total'): (2054500, 2071308, 2054500, 2037829, 1511193, 2793138, 1311000, 743500),
                 (CUS, 'expenses_total'): (6233000, 6283992, 6233000, 6182422, 4584699, 8473902, 3424000, 2809000)}
        for (sector, sid), (level, m1, p0, p1, plow, phigh, observed, remainder) in table.items():
            with self.subTest(sector=sector, series=sid):
                lo, mid, hi = self.lobby(sector, -1)[sid], self.lobby(sector, 0)[sid], self.lobby(sector, 1)[sid]
                for actual, e in ((lo['base_level'], level), (lo['projected'], m1), (mid['projected'], p0), (hi['projected'], p1),
                                  (mid['prediction_low'], plow), (mid['prediction_high'], phigh), (mid['observed']['amount_nominal'], observed), (mid['projected_remaining'], remainder)):
                    self.assertLessEqual(abs(round(actual) - e), 1, f'{actual} vs {e}')

    def test_lobbying_coefficient_interval_at_dg_minus_one_matches_the_log_refit(self):
        s = self.lobby(BANKS, -1)['income_total']
        self.assertLessEqual(abs(round(s['coefficient_low']) - 23844485), 1)
        self.assertLessEqual(abs(round(s['coefficient_high']) - 24194595), 1)
        self.assertLessEqual(abs(round(s['prediction_low']) - 17665651), 1)
        self.assertLessEqual(abs(round(s['prediction_high']) - 32657027), 1)

    def test_both_lda_series_are_side_by_side_and_never_summed(self):
        block = self.out[BANKS + ':lob'][0]['horizons'][0]['lobbying']
        row = block['rows'][0]
        self.assertEqual([s['id'] for s in row['series']], ['income_total', 'expenses_total'])
        self.assertEqual(block['sector'], 'bank')
        self.assertNotIn('total', row)
        self.assertEqual(block['base_year'], 2025)
        near(self, row['change_pct'], 0, 9)

    def test_lobbying_uses_the_log_refit_with_its_ordinary_p(self):
        block = self.out[BANKS + ':lob'][-1]['horizons'][0]['lobbying']
        self.assertAlmostEqual(block['ordinary_p'], 0.029125763521828413, places=12)
        self.assertEqual(block['slope']['label'], 'pooled slope')
        self.assertAlmostEqual(block['rows'][0]['change_pct'], 100 * math.expm1(-0.00814763405915353 * -1), places=6)


class ContractAndRefusalTests(unittest.TestCase):
    def test_a_stale_snapshot_is_refused_with_anchor_stale(self):
        with tempfile.TemporaryDirectory() as tmp:
            anchors = contract.example('anchors')
            shas = {i['mentat']['workbook']: i['mentat']['workbook_sha256'] for i in anchors['industries'].values()}
            shas['Banking Industry Spending Overview.xlsx'] = 'f' * 64                # the workbook was republished
            with World(tmp, published=shas):
                out = gf.project(scenario(BANKS))
                self.assertEqual(out['status'], 'anchor_stale')
                self.assertEqual(out['horizons'], [])
                self.assertIn('Rebuild the anchors', out['reason'])
                self.assertEqual(gf.project(scenario(CUS))['status'], 'ready')          # one industry's republish does not block another
                catalog = gf.catalog('2026-09-30')
                self.assertEqual(catalog['anchors']['industries'][BANKS]['status'], 'anchor_stale')
                self.assertEqual(catalog['anchors']['industries'][CUS]['status'], 'ready')

    def test_an_unreadable_published_workbook_is_refused_not_trusted(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp, published={}):
            self.assertEqual(gf.project(scenario(BANKS))['status'], 'anchor_unavailable')

    def test_a_missing_or_invalid_snapshot_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp) as w:
            (w.dir / 'anchors.json').unlink()
            gf._load_anchors.cache_clear()
            out = gf.project(scenario(BANKS))
            self.assertEqual(out['status'], 'anchor_unavailable')
            self.assertIn('build_giving_anchors', out['reason'])
            self.assertEqual(gf.catalog('2026-09-30')['anchors']['status'], 'anchor_unavailable')
            (w.dir / 'anchors.json').write_text(json.dumps(contract.apply_mutation(contract.example('anchors'), {'op': 'delete', 'path': ['cpi']})))
            gf._load_anchors.cache_clear()
            self.assertEqual(gf.project(scenario(BANKS))['status'], 'anchor_unavailable')

    def test_every_anchor_negative_control_makes_the_console_refuse(self):
        for control in (c for c in contract.negative_controls() if c['target'] == 'anchors'):
            path = ['commercial_banks' if step == '<industry>' else step for step in control['path']]
            mutated = contract.apply_mutation(contract.example('anchors'), {**control, 'path': path})
            if control['op'] == 'set' and isinstance(control.get('value'), dict) and '$nonfinite' in control['value']:
                continue                                                                 # JSON on disk cannot carry NaN; the validator rejects it in memory
            with self.subTest(control=control['id']), tempfile.TemporaryDirectory() as tmp, World(tmp, anchors=mutated):
                self.assertEqual(gf.project(scenario(BANKS))['status'], 'anchor_unavailable')

    def test_an_invalid_bundle_is_refused_by_the_loader(self):
        for control in (c for c in contract.negative_controls() if c['target'] == 'models'):
            if isinstance(control.get('value'), dict) and '$nonfinite' in control['value'] or control['path'] == ['schema_version']:
                continue                                   # NaN cannot be written to JSON; schema_version 1 is a legitimate v1 package to the loader
            mutated = contract.apply_mutation(contract.example('models'), control)
            with self.subTest(control=control['id']), tempfile.TemporaryDirectory() as tmp:
                with World(tmp, bundle=mutated), self.assertRaises(ValueError):
                    gf.models()

    def test_a_bundle_whose_anchor_contract_the_console_does_not_implement_is_refused(self):
        bundle = contract.example('models')
        bundle['anchor_contract']['pac']['measures'][0]['id'] = 'general_giving'
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle), self.assertRaises(ValueError):
            gf.models()

    def test_seats_are_not_a_selectable_signal_and_slopes_are_not_selectable(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            with self.assertRaisesRegex(ValueError, 'evidence only'):
                gf.project(scenario(BANKS) | {'signal': 'seats'})
            with self.assertRaisesRegex(ValueError, 'not selectable'):
                gf.project(scenario(BANKS) | {'industry_slopes': True})
            self.assertEqual(gf.project(scenario(BANKS) | {'signal': 'control', 'industry_slopes': False})['status'], 'ready')
            catalog = gf.catalog('2026-09-30')
            self.assertEqual(set(catalog['share_models']), {'control_House', 'control_Senate'})
            self.assertTrue(all(m['calculator'] is False for m in catalog['evidence_models'].values()))
            self.assertIn('seats_House', catalog['evidence_models'])

    def test_auto_has_no_mentat_data_so_it_is_not_offered_but_stays_in_estimation(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            catalog = gf.catalog('2026-09-30')
            self.assertNotIn('auto_light_duty_manufacturing', [i['id'] for i in catalog['industries']])
            self.assertEqual([n['id'] for n in catalog['not_offered']], ['auto_light_duty_manufacturing'])
            self.assertIn('auto_light_duty_manufacturing', catalog['pac_model']['slopes'])            # still in the estimation
            with self.assertRaises(ValueError):
                gf.project(scenario('auto_light_duty_manufacturing'))

    def test_community_banks_are_separate_and_not_a_forecast_industry(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp) as w:
            self.assertEqual(w.anchors['industries']['community_banks']['forecast_industry'], None)
            with self.assertRaises(ValueError):
                gf.project({'industry': 'community_banks', 'as_of': '2026-09-30'})
            banks = gf.project(scenario(BANKS))['anchors']
            self.assertEqual(banks['dataset'], 'Banking')
            self.assertNotEqual(w.anchors['industries']['community_banks']['general_giving']['cycles']['2024'], w.anchors['industries'][BANKS]['general_giving']['cycles']['2024'])

    def test_property_casualty_lobbying_is_hidden_and_flagged_and_its_other_models_withheld(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            out = gf.project(scenario('property_casualty'))
            self.assertEqual(out['status'], 'ready')
            h = out['horizons'][0]
            self.assertEqual(h['lobbying']['status'], 'unavailable')
            self.assertIn('No Melange-LDA sector', h['lobbying']['reason'])
            self.assertEqual(h['lobbying']['rows'], [])
            self.assertEqual(h['pac']['status'], 'withheld')
            self.assertIn('F3400', h['pac']['reason'])
            self.assertEqual(h['shares']['House']['status'], 'withheld')

    def test_v2_outputs_are_strict_json_and_the_request_is_not_mutated(self):
        request = scenario(BANKS)
        before = copy.deepcopy(request)
        out = run(request)
        self.assertEqual(request, before)
        json.dumps(out, allow_nan=False)
        self.assertEqual(out['inputs'], request)
        self.assertEqual(len(out['model_sha256']), 64)

    def test_non_finite_and_invalid_numbers_are_rejected(self):
        for bad in (float('nan'), float('inf'), True, {}, 501, 10 ** 400):
            r = scenario(BANKS)
            r['horizons']['2026']['growth_pct'] = bad
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as tmp, World(tmp), self.assertRaises(ValueError):
                gf.project(r)

    def test_dates_are_validated_like_v1(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            for extra in ({'as_of': '2026-10-01'}, {'as_of': '2026-09-26'}, {'as_of': 'bad'}, {'assumption_date': '2026-10-01'}):
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    gf.project(scenario(BANKS) | extra)

    def test_inputs_left_blank_are_unknown_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            out = gf.project({'industry': BANKS, 'as_of': '2026-09-30'})
            h = out['horizons'][0]
            self.assertEqual(h['pac']['status'], 'needs_inputs')
            self.assertEqual(h['shares']['House']['status'], 'needs_inputs')
            self.assertEqual(h['lobbying']['rows'][0]['status'], 'needs_inputs')
            self.assertEqual([r['cycle'] for r in out['horizons']], [2026, 2028])

    def test_an_earlier_as_of_date_uses_the_latest_observed_cut_on_or_before_it(self):
        bundle = contract.example('models')
        bundle['built_on'] = '2025-01-01'                # the vintage guard would otherwise refuse an as-of date before the model package existed
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            out = gf.project(scenario(BANKS, as_of='2026-03-31'))
            g = next(m for m in out['horizons'][0]['pac']['measures'] if m['id'] == 'general_giving')
            self.assertEqual(g['observed']['through'], '2026-03-31')
            self.assertAlmostEqual(g['observed']['amount_nominal'], 9416929.24, places=2)
            self.assertEqual(out['horizons'][0]['starts'], '2026-04-01')
            self.assertEqual(g['remainder_starts'], '2026-04-01')
            # as-of in the middle of a month: the previous month-end
            mid = gf.project(scenario(BANKS, as_of='2026-04-20'))
            self.assertEqual(next(m for m in mid['horizons'][0]['pac']['measures'] if m['id'] == 'general_giving')['observed']['through'], '2026-03-31')

    def test_an_as_of_date_before_the_first_observed_month_end_has_no_remainder(self):
        bundle = contract.example('models')
        bundle['built_on'] = '2025-01-01'
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            out = gf.project(scenario(BANKS, as_of='2025-01-15'))
            g = next(m for m in out['horizons'][0]['pac']['measures'] if m['id'] == 'general_giving')
            self.assertEqual(g['remainder_status'], 'no_observed')
            self.assertNotIn('projected_remaining', g)

    def test_observed_above_the_projection_is_a_conflict_not_a_zero_forecast(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            out = gf.project(scenario(BANKS, growth=400))          # extreme growth: a strongly negative log change shrinks the projection below the observed
            g = next(m for m in out['horizons'][0]['pac']['measures'] if m['id'] == 'general_giving')
            self.assertEqual(g['remainder_status'], 'baseline_exceeded')
            self.assertIsNone(g['projected_remaining'])
            self.assertGreater(g['excess_observed'], 0)
            self.assertTrue(out['horizons'][0]['pac']['extrapolation'])

    def test_share_outside_zero_one_is_flagged_and_never_clipped(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            out = gf.project(scenario(CUS, scores={'House': 100, 'Senate': 100}))
            senate = out['horizons'][0]['shares']['Senate']
            pac = next(b for b in senate['bases'] if b['id'] == 'pac_candidate')       # anchor share 0.0000 on a $5,000 base: the negative effect takes it below zero
            self.assertEqual(pac['status'], 'outside_share_range')
            self.assertLess(pac['raw_projected_cycle_R_share'], 0)
            self.assertNotIn('projected_cycle_R_share', pac)
            self.assertTrue(pac['interval_outside_share_range'])
            self.assertIn('thin_base', pac['flags'])

    def test_offset_application_with_the_pooled_slope_equals_the_pooled_application(self):
        bundle = contract.example('models')
        m = bundle['share_models']['control_House']
        j = m['terms'].index('Forecast')
        keep = [i for i in range(len(m['terms'])) if i != j]
        m['application'] = 'offset'
        m['offset'] = {'terms': [m['terms'][i] for i in keep], 'beta': [m['beta'][i] for i in keep], 'covariance': [[m['covariance'][a][c] for c in keep] for a in keep]}
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            offset = gf.project(scenario(BANKS))['horizons'][0]['shares']['House']
        pooled = run(scenario(BANKS))['horizons'][0]['shares']['House']
        self.assertAlmostEqual(offset['change_pp'], pooled['change_pp'], places=9)
        self.assertAlmostEqual(offset['political_change_pp'], pooled['political_change_pp'], places=9)

    def test_an_industry_specific_focal_slope_changes_only_the_political_term(self):
        bundle = contract.example('models')
        m = bundle['share_models']['control_House']
        j = m['terms'].index('Forecast')
        keep = [i for i in range(len(m['terms'])) if i != j]
        m['application'] = 'offset'
        m['offset'] = {'terms': [m['terms'][i] for i in keep], 'beta': [m['beta'][i] for i in keep], 'covariance': [[m['covariance'][a][c] for c in keep] for a in keep]}
        m['slopes'][BANKS]['applied'].update(rule='R1', beta=m['beta'][j] * 2)
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            doubled = gf.project(scenario(BANKS))['horizons'][0]['shares']['House']
        base = run(scenario(BANKS))['horizons'][0]['shares']['House']
        self.assertEqual(doubled['slope_label'], 'industry-specific slope')
        self.assertAlmostEqual(doubled['political_change_pp'], 2 * base['political_change_pp'], places=9)
        self.assertNotAlmostEqual(doubled['change_pp'], base['change_pp'], places=3)

    def test_the_slope_rule_the_bundle_records_is_the_one_applied(self):
        bundle = contract.example('models')
        row = bundle['pac_model']['slopes'][BANKS]
        row['applied'].update(rule='R0', beta=-0.168, se=0.035, df=11, critical_95=2.2, ordinary_p=0.0006)
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            pac = gf.project(scenario(BANKS))['horizons'][0]['pac']
        self.assertEqual(pac['slope']['label'], 'pooled slope')
        self.assertEqual(pac['slope']['beta'], -0.168)
        self.assertEqual(pac['ordinary_p'], 0.0006)

    def test_chained_lobbying_needs_every_intermediate_year(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            r = scenario(BANKS)
            r['horizons']['2026']['annual_forecast_changes'] = {'2027': 1, '2028': 1}
            r['horizons']['2028']['annual_forecast_changes'] = {'2027': 1, '2028': 1}
            out = gf.project(r)
            rows = out['horizons'][1]['lobbying']['rows']
            self.assertEqual([x['year'] for x in rows], [2027, 2028])
            self.assertEqual(rows[0]['status'], 'needs_inputs')
            self.assertIn('2026', rows[0]['reason'])
            r['horizons']['2028']['annual_forecast_changes'] = {'2026': 1, '2027': 1, '2028': 1}
            rows = gf.project(r)['horizons'][1]['lobbying']['rows']
            self.assertEqual([(x['steps'], x['chained'], x['cumulative_change_pp']) for x in rows], [(2, True, 2), (3, True, 3)])
            near(self, rows[1]['change_pct'], 100 * math.expm1(-0.00814763405915353 * 3), 6)

    def test_lobbying_remainder_needs_the_as_of_date_to_reach_the_ldas_last_quarter(self):
        bundle = contract.example('models')
        bundle['built_on'] = '2025-01-01'
        with tempfile.TemporaryDirectory() as tmp, World(tmp, bundle=bundle):
            out = gf.project(scenario(BANKS, as_of='2026-06-01'))
            s = out['horizons'][0]['lobbying']['rows'][0]['series'][0]
            self.assertEqual(s['remainder_status'], 'no_observed')
            self.assertNotIn('projected_remaining', s)

    def test_catalog_reads_the_bundle_not_hard_coded_text(self):
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            catalog = gf.catalog('2026-09-30')
            self.assertEqual(catalog['schema_version'], 2)
            self.assertEqual(catalog['pac_model']['n'], 21)
            self.assertEqual(catalog['lobby_model']['n'], 71)
            self.assertEqual({i['id'] for i in catalog['industries']}, {BANKS, CUS, 'property_casualty'})
            self.assertEqual(catalog['anchors']['industries'][BANKS]['coverage_end'], '2026-06-30')
            self.assertIn('prediction', catalog['interval_labels']['prediction'])
            json.dumps(catalog, allow_nan=False)


class UnusualButValidAnchorTests(unittest.TestCase):
    """Schema-valid snapshots with missing pieces answer with a status or a reason, never a crash and never a zero."""

    def with_anchors(self, edit):
        anchors = contract.example('anchors')
        edit(anchors['industries'][BANKS])
        self.assertEqual(contract.validate_kind(anchors, 'anchors') or contract.check_anchor_invariants(anchors), [])     # the variant is a legal snapshot
        with tempfile.TemporaryDirectory() as tmp, World(tmp, anchors=anchors):
            out = gf.project(scenario(BANKS))
            json.dumps(out, allow_nan=False)
            return out['horizons'][0]

    def test_a_missing_anchor_cycle_of_candidate_receipts_makes_the_share_bases_unavailable(self):
        def edit(i):
            i['candidate_receipts']['cycles'].pop('2024')
            i['candidate_receipts']['thin_base'].pop('2024')
        h = self.with_anchors(edit)
        basis = next(b for b in h['shares']['House']['bases'] if b['id'] == 'employee_candidate')
        self.assertEqual(basis['status'], 'unavailable')
        self.assertIn('anchor cycle', basis['reason'])
        self.assertEqual(next(b for b in h['shares']['House']['bases'] if b['id'] == 'pac_candidate')['status'], 'ready')
        self.assertIsNone(h['shares']['House']['combined_reference'])

    def test_an_unavailable_pac_block_leaves_general_giving_and_the_employee_basis(self):
        def edit(i):
            i['pac_to_candidates'].update(status='unavailable', reason='roster not resolved', committee_count=0, single_pac=False, committees=[], inputs=[],
                                          cycles={}, file_through={}, observed=[], thin_base={})
            i['status']['pac_to_candidates'] = 'unavailable'
        h = self.with_anchors(edit)
        measures = {m['id']: m for m in h['pac']['measures']}
        self.assertEqual(measures['pac_to_candidates']['status'], 'unavailable')
        self.assertEqual(measures['pac_to_candidates']['reason'], 'roster not resolved')
        self.assertEqual(measures['general_giving']['status'], 'ready')
        bases = {b['id']: b for b in h['shares']['Senate']['bases']}
        self.assertEqual(bases['pac_candidate']['status'], 'unavailable')
        self.assertIn(bases['employee_candidate']['remainder_status'], ('ready', 'budget_inconsistent'))

    def test_a_partial_year_absent_from_the_lda_means_no_observed_quarters_and_no_remainder(self):
        def edit(i):
            for s in i['lda']['series'].values():
                s['partial'] = None
        s = self.with_anchors(edit)['lobbying']['rows'][0]['series'][0]
        self.assertNotIn('observed', s)
        self.assertNotIn('projected_remaining', s)
        self.assertGreater(s['projected'], 0)

    def test_a_two_party_base_of_zero_has_no_share_to_carry_over(self):
        def edit(i):
            for chamber in ('House', 'Senate'):
                i['candidate_receipts']['cycles']['2024'][chamber].update(D=0.0, R=0.0, other=0.0)
            i['candidate_receipts']['thin_base']['2024'] = {'House': True, 'Senate': True}
        h = self.with_anchors(edit)
        basis = next(b for b in h['shares']['House']['bases'] if b['id'] == 'employee_candidate')
        self.assertEqual(basis['status'], 'unavailable')

    def test_the_last_day_of_the_cycle_has_no_remainder_window(self):
        class YearEnd(date):
            @classmethod
            def today(cls):
                return cls(2026, 12, 31)
        with tempfile.TemporaryDirectory() as tmp, World(tmp), patch.object(gf, 'date', YearEnd):
            out = gf.project(scenario(BANKS, as_of='2026-12-31'))
        h = out['horizons'][0]
        self.assertIsNone(h['starts'])
        self.assertEqual(h['pac']['measures'][0]['remainder_status'], 'cycle_closed')
        self.assertEqual(h['shares']['House']['bases'][0]['remainder_status'], 'cycle_closed')
        self.assertEqual(h['lobbying']['rows'][0]['series'][0]['remainder_status'], 'ready')       # Melange LDA's Q3 + Q4 are not filed yet: that remainder stands


class RenderFixtureTests(unittest.TestCase):
    """The golden payload the browser harness (test_giving_forecast_v2.cjs) renders: pinned to the calculator so the two cannot drift."""

    @staticmethod
    def payload():
        runs = {}
        with tempfile.TemporaryDirectory() as tmp, World(tmp):
            catalog = gf.catalog('2026-09-30')
            for name, request in (('banks', scenario(BANKS)), ('credit_unions', scenario(CUS)), ('banks_equal_weight', scenario(BANKS, scores={'House': 19.03485027624309, 'Senate': 56.39529613})),
                                  ('banks_blank', {'industry': BANKS, 'as_of': '2026-09-30'}), ('property_casualty', scenario('property_casualty'))):
                runs[name] = gf.project(request)
        stale = contract.example('anchors')
        shas = {i['mentat']['workbook']: i['mentat']['workbook_sha256'] for i in stale['industries'].values()}
        shas['Banking Industry Spending Overview.xlsx'] = 'e' * 64
        with tempfile.TemporaryDirectory() as tmp, World(tmp, published=shas):
            runs['banks_stale'] = gf.project(scenario(BANKS))
        return {'catalog': catalog, 'runs': runs}

    def test_the_render_payload_is_the_calculators_current_output(self):
        payload = json.loads(json.dumps(self.payload()))
        if os.environ.get('UPDATE_GIVING_FORECAST_GOLDEN'):
            GOLDEN.parent.mkdir(exist_ok=True)
            GOLDEN.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n', encoding='utf-8', newline='\n')
        self.assertEqual(payload, json.loads(GOLDEN.read_text(encoding='utf-8')),
                         'giving_forecast_v2_render.json is stale; regenerate it with UPDATE_GIVING_FORECAST_GOLDEN=1')


if __name__ == '__main__':
    unittest.main()
