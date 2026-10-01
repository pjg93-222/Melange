"""Synthetic-fixture tests for the benchmark contract. No live lane data is read, except the
skip-gated live-reproduction check in DefaultBillsFlagsReproduceTheFrozenRunTests below, which
only runs where the frozen benchmark has already been built."""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

from fec.research.member_personal_relationships.benchmark_contract import (
    ALL_HISTORY_CUTOFF, BILLS_FILE, CONTRACT, CONTRACT_SHA256, COVERAGE_START, DEFAULT_CONGRESS_RANGE, FLOOR,
    INPUT_PINS, OUT, PANEL_FILE, R0, R0_NOVIS, ROOT, ROW_ORDER, SEED, VISIBILITY, WORK_BENCH,
    apply_signature_policy, bootstrap_auc, bootstrap_draws, build_assessments, build_run_contract,
    build_work_rows, chamber_strata, congress_start_date, consumed_input_pins, contract_digest,
    derive_coverage_start, distinct_permutations, interval, parse_congress_range, permuted_cases,
    read_bills_in_range, report_text, run_bill_universe, stratum_shape)
from fec.research.member_personal_relationships.chamber_work import WORK_FIELDS


def member(chamber, start='2019-01-03', end='2027-01-03', party='Democrat', state='XX'):
    return dict(name=chamber + start, chamber=chamber, party=party, state=state,
                terms=[dict(start=start, end=end, chamber=chamber, party=party, state=state)])


def bill(key, chamber, introduced, sponsor, joins, area='Health', congress=116):
    return dict(key=key, chamber=chamber, introduced=introduced, sponsor=sponsor, area=area,
                joins={a: introduced for a in joins}, withdrawals={}, original=sorted(joins),
                size=len(joins), congress=congress, end='2027-01-03', title=key, updated=None, url='')


def quiet(*args, **kwargs):
    return None


class SignaturePolicyTests(unittest.TestCase):
    def test_all_policy_makes_original_equal_the_valid_signers(self):
        panel = [bill('h1', 'House', '2020-01-01', 'S', ['A', 'B']),
                 bill('h2', 'House', '2020-02-01', 'S', ['A', 'B', 'C'])]
        panel[0]['original'] = ['A']
        panel[1]['original'] = []
        converted = apply_signature_policy(panel, 'all')
        for before, after in zip(panel, converted):
            self.assertEqual(after['original'], sorted(before['joins']))
            self.assertTrue(set(after['original']).issubset(set(after['joins'])))
        self.assertEqual([b['original'] for b in panel], [['A'], []], 'the source panel must not be mutated')
        self.assertIs(apply_signature_policy(panel, 'original'), panel)
        with self.assertRaises(ValueError):
            apply_signature_policy(panel, 'some_other_policy')


class CongressRangeParsingTests(unittest.TestCase):
    def test_parses_a_valid_inclusive_range(self):
        self.assertEqual(parse_congress_range('115-119'), (115, 119))
        self.assertEqual(parse_congress_range('116-116'), (116, 116))

    def test_default_matches_the_frozen_contract_range(self):
        self.assertEqual(DEFAULT_CONGRESS_RANGE, (116, 119))

    def test_rejects_malformed_or_backwards_values(self):
        for bad in ('abc-119', '115', '115-119-120', '', '119-115', '0-119', '115-9999', '115-', '-119'):
            with self.assertRaises(argparse.ArgumentTypeError, msg=bad):
                parse_congress_range(bad)


class BillsRangeLoaderTests(unittest.TestCase):
    """Synthetic ndjson fixture in the schema history_work.read_history() produces; no live file read."""

    def fixture(self, tmp):
        rows = [bill('115:hr:1', 'House', '2017-01-05', 'S', ['A', 'B'], congress=115),
                bill('116:hr:1', 'House', '2019-01-05', 'S', ['A', 'B'], congress=116),
                bill('119:hr:1', 'House', '2025-01-05', 'S', ['A', 'B'], congress=119),
                bill('120:hr:1', 'House', '2027-01-05', 'S', ['A', 'B'], congress=120)]
        path = Path(tmp) / 'bills.ndjson'
        with path.open('w', encoding='utf-8') as f:
            for row in rows:
                f.write(json.dumps(row) + '\n')
        return path

    def test_default_range_keeps_only_116_through_119(self):
        with tempfile.TemporaryDirectory() as tmp:
            bills, audit = read_bills_in_range(self.fixture(tmp), DEFAULT_CONGRESS_RANGE)
        self.assertEqual(sorted(b['key'] for b in bills), ['116:hr:1', '119:hr:1'])
        self.assertEqual(audit['source_records'], 4)
        self.assertEqual(audit['included_bills'], 2)
        self.assertEqual(audit['bills_by_congress'], {116: 1, 119: 1})

    def test_extended_range_keeps_the_115th_congress(self):
        with tempfile.TemporaryDirectory() as tmp:
            bills, audit = read_bills_in_range(self.fixture(tmp), (115, 119))
        self.assertEqual(sorted(b['key'] for b in bills), ['115:hr:1', '116:hr:1', '119:hr:1'])
        self.assertEqual(audit['included_bills'], 3)
        self.assertIn(115, audit['bills_by_congress'])

    def test_a_single_congress_range_is_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            bills, _ = read_bills_in_range(self.fixture(tmp), (120, 120))
        self.assertEqual([b['key'] for b in bills], ['120:hr:1'])

    def test_an_empty_file_yields_no_bills(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / 'empty.ndjson'
            empty.write_text('', encoding='utf-8')
            bills, audit = read_bills_in_range(empty, DEFAULT_CONGRESS_RANGE)
        self.assertEqual(bills, [])
        self.assertEqual(audit['source_records'], 0)
        self.assertIsNone(audit['earliest_introduced'])

    def test_the_audit_reports_the_earliest_introduction_inside_the_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = self.fixture(tmp)
            _, wide = read_bills_in_range(path, (115, 119))
            _, narrow = read_bills_in_range(path, DEFAULT_CONGRESS_RANGE)
        self.assertEqual(wide['earliest_introduced'], '2017-01-05')
        self.assertEqual(narrow['earliest_introduced'], '2019-01-05',
                         'the earliest date must come from the kept rows, not the whole file')


def audit_for(bills_by_congress, congress_range, source_records=None, earliest_introduced=None):
    """The slice of read_bills_in_range()'s audit the coverage and contract builders read."""
    included = sum(bills_by_congress.values())
    return dict(bills_by_congress=dict(bills_by_congress), congress_range=list(congress_range),
                source_records=included if source_records is None else source_records,
                included_bills=included, earliest_introduced=earliest_introduced)


FROZEN_AUDIT = audit_for({116: 14148, 117: 15066, 118: 16213, 119: 15658}, (116, 119),
                         earliest_introduced='2019-01-03')
EXTENDED_AUDIT = audit_for({115: 11199, 116: 14148, 117: 15066, 118: 16213, 119: 15658}, (115, 119),
                           earliest_introduced='2017-01-03')


class CoverageStartDerivationTests(unittest.TestCase):
    """D1: the S1 threshold and the coverage notes follow the panel a run loads, not a fixed constant."""

    def test_a_congress_starts_on_january_3_of_its_first_year(self):
        self.assertEqual(congress_start_date(115), '2017-01-03')
        self.assertEqual(congress_start_date(116), '2019-01-03')
        self.assertEqual(congress_start_date(117), '2021-01-03')
        self.assertEqual(congress_start_date(119), '2025-01-03')

    def test_the_default_range_still_derives_the_frozen_coverage_start(self):
        coverage = derive_coverage_start(FROZEN_AUDIT, DEFAULT_CONGRESS_RANGE)
        self.assertEqual(coverage['coverage_start'], '2019-01-03')
        self.assertEqual(coverage['coverage_start'], COVERAGE_START,
                         'the default flags must reproduce the frozen panel start exactly')
        self.assertEqual(coverage['earliest_congress'], 116)
        self.assertEqual(coverage['congresses_in_panel'], [116, 117, 118, 119])
        self.assertTrue(coverage['agrees_with_earliest_introduced'])

    def test_the_115_119_range_derives_the_115th_congress_start(self):
        coverage = derive_coverage_start(EXTENDED_AUDIT, (115, 119))
        self.assertEqual(coverage['coverage_start'], '2017-01-03')
        self.assertNotEqual(coverage['coverage_start'], COVERAGE_START)
        self.assertEqual(coverage['earliest_congress'], 115)
        self.assertEqual(coverage['requested_congress_range'], [115, 119])
        self.assertEqual(coverage['earliest_introduced_in_panel'], '2017-01-03')
        self.assertTrue(coverage['agrees_with_earliest_introduced'])
        self.assertEqual(coverage['frozen_v1_1_coverage_start'], COVERAGE_START)

    def test_the_derivation_is_recorded_not_assumed(self):
        coverage = derive_coverage_start(EXTENDED_AUDIT, (115, 119))
        self.assertEqual(coverage['rule'], 'first day of the earliest congress in the loaded bill panel')
        self.assertEqual(coverage['basis'], 'earliest congress present in the loaded panel')
        self.assertIn('1789 + 2*(115 - 1)', coverage['formula'])
        self.assertTrue(coverage['formula'].endswith('2017-01-03'))

    def test_the_panel_not_the_requested_bound_sets_the_start(self):
        """A 115-119 request against a panel holding no 115th-congress bill starts at the 116th."""
        coverage = derive_coverage_start(FROZEN_AUDIT, (115, 119))
        self.assertEqual(coverage['coverage_start'], '2019-01-03')
        self.assertEqual(coverage['requested_range_start_date'], '2017-01-03')
        self.assertEqual(coverage['basis'], 'earliest congress present in the loaded panel')

    def test_an_empty_panel_falls_back_to_the_requested_start_and_says_so(self):
        coverage = derive_coverage_start(audit_for({}, (115, 119)), (115, 119))
        self.assertEqual(coverage['coverage_start'], '2017-01-03')
        self.assertEqual(coverage['congresses_in_panel'], [])
        self.assertIn('loaded panel is empty', coverage['basis'])
        self.assertFalse(coverage['agrees_with_earliest_introduced'])

    def test_the_s1_rule_selects_by_the_derived_start(self):
        """The rule main() applies: first documented event strictly before the panel coverage start."""
        # The six earliest first-event dates in the pinned 29-dyad label file, plus the next one after
        # them, so the counts here are the counts the live S1 row reports.
        firsts = ['2015-07-24', '2016-06-29', '2016-09-12', '2017-12-04', '2017-12-04', '2018-12-21',
                  '2019-01-30']
        frozen = derive_coverage_start(FROZEN_AUDIT, DEFAULT_CONGRESS_RANGE)['coverage_start']
        extended = derive_coverage_start(EXTENDED_AUDIT, (115, 119))['coverage_start']
        self.assertEqual(sum(1 for f in firsts if f < frozen), 6)
        self.assertEqual(sum(1 for f in firsts if f < extended), 3)


class RunContractPanelBlockTests(unittest.TestCase):
    """D2: contract.json's panel block is built from the run's bills instead of a static 116-119 block."""

    def frozen_block(self):
        return run_bill_universe(ROOT / PANEL_FILE, INPUT_PINS[PANEL_FILE], FROZEN_AUDIT,
                                 derive_coverage_start(FROZEN_AUDIT, DEFAULT_CONGRESS_RANGE))

    def extended_block(self):
        panel = 'outputs/member_personal_relationships/20260911_full_history_115_119/bills.ndjson'
        sha = '41db16930ec5bc6aedd235cb15bac262634da1018f25a4c4543428f57e031845'
        return panel, sha, run_bill_universe(ROOT / panel, sha, EXTENDED_AUDIT,
                                             derive_coverage_start(EXTENDED_AUDIT, (115, 119)))

    def test_the_default_panel_rebuilds_the_frozen_block_field_for_field(self):
        self.assertEqual(self.frozen_block(), CONTRACT['bill_universe'])
        self.assertEqual(list(self.frozen_block()), list(CONTRACT['bill_universe']))

    def test_the_default_run_contract_is_v1_1_and_keeps_the_frozen_digest(self):
        contract = build_run_contract(self.frozen_block(), COVERAGE_START)
        self.assertEqual(contract['contract_version'], '1.1')
        self.assertEqual(contract_digest(contract), CONTRACT_SHA256)
        self.assertEqual(contract, CONTRACT)
        self.assertEqual(list(contract), list(CONTRACT), 'contract.json key order must not move')

    def test_the_115_119_panel_block_describes_the_panel_the_run_read(self):
        panel, sha, block = self.extended_block()
        self.assertEqual(block['serialized_panel'], panel)
        self.assertEqual(block['serialized_panel_sha256'], sha)
        self.assertEqual(block['source'], panel)
        self.assertEqual(block['source_sha256'], sha)
        self.assertEqual(block['source_records'], 72284)
        self.assertEqual(block['panel_records'], 72284)
        self.assertEqual(block['congresses'], [115, 116, 117, 118, 119])
        self.assertEqual(block['coverage_start'], '2017-01-03')
        self.assertIn('congresses 115-119', block['loader'])
        self.assertIn('run_history.read_rows()', block['loader'])
        self.assertNotIn(INPUT_PINS[PANEL_FILE], json.dumps(block),
                         'the 116-119 panel sha must not survive into a 115-119 panel block')
        self.assertNotEqual(block['source'], BILLS_FILE)

    def test_the_115_119_run_contract_is_v1_2_with_its_own_digest(self):
        _, _, block = self.extended_block()
        contract = build_run_contract(block, '2017-01-03')
        self.assertEqual(contract['contract_version'], '1.2')
        self.assertNotEqual(contract_digest(contract), CONTRACT_SHA256)
        self.assertEqual(contract['bill_universe'], block)
        self.assertEqual(contract['rows']['S1']['drop'],
                         'dyads whose first documented event predates the bill panel coverage start 2017-01-03')
        self.assertEqual(list(contract), list(CONTRACT))

    def test_building_a_run_contract_never_mutates_the_frozen_one(self):
        _, _, block = self.extended_block()
        before = json.dumps(CONTRACT, sort_keys=True, ensure_ascii=False)
        build_run_contract(block, '2017-01-03')
        self.assertEqual(json.dumps(CONTRACT, sort_keys=True, ensure_ascii=False), before)
        self.assertEqual(contract_digest(), CONTRACT_SHA256)
        self.assertEqual(CONTRACT['bill_universe']['coverage_start'], COVERAGE_START)
        self.assertTrue(CONTRACT['rows']['S1']['drop'].endswith(COVERAGE_START))


class ConsumedInputPinTests(unittest.TestCase):
    """The receipt's primary pin table must name the bill panel the run opened."""

    def test_the_default_run_records_the_frozen_pin_table_unchanged(self):
        consumed = consumed_input_pins(dict(INPUT_PINS), ROOT / PANEL_FILE, INPUT_PINS[PANEL_FILE])
        self.assertEqual(consumed, dict(INPUT_PINS))
        self.assertEqual(list(consumed), list(INPUT_PINS), 'the pin order must not move on a default run')

    def test_a_non_default_bills_run_records_the_file_it_consumed(self):
        panel = 'outputs/member_personal_relationships/20260911_full_history_115_119/bills.ndjson'
        sha = '41db16930ec5bc6aedd235cb15bac262634da1018f25a4c4543428f57e031845'
        consumed = consumed_input_pins(dict(INPUT_PINS), ROOT / panel, sha)
        self.assertEqual(consumed[panel], sha)
        self.assertNotIn(PANEL_FILE, consumed,
                         'the 116-119 panel was not read by this run and must not sit in the primary table')
        self.assertNotIn(INPUT_PINS[PANEL_FILE], consumed.values())
        for name, pinned in INPUT_PINS.items():
            if name != PANEL_FILE:
                self.assertEqual(consumed[name], pinned, name)
        self.assertEqual(len(consumed), len(INPUT_PINS))


class TimingPolicyTests(unittest.TestCase):
    cases = [dict(pair=['A', 'B'], first='2020-03-04', directions=[['A', 'B'], ['B', 'A']], y=1),
             dict(pair=['A', 'C'], first='2021-07-08', directions=[['A', 'C']], y=0)]

    def test_strict_before_carries_the_first_documented_event_date(self):
        rows = build_assessments(self.cases, 'strict_before')
        self.assertEqual([r['date'] for r in rows], ['2020-03-04', '2020-03-04', '2021-07-08'])
        self.assertEqual([(r['actor'], r['target']) for r in rows], [('A', 'B'), ('B', 'A'), ('A', 'C')])
        self.assertEqual(len({r['id'] for r in rows}), 3)

    def test_all_history_carries_the_single_declared_cutoff(self):
        rows = build_assessments(self.cases, 'all_history')
        self.assertEqual({r['date'] for r in rows}, {ALL_HISTORY_CUTOFF})
        self.assertEqual(ALL_HISTORY_CUTOFF, '2026-09-11')

    def test_unknown_timing_is_refused(self):
        with self.assertRaises(ValueError):
            build_assessments(self.cases, 'whenever')


class SpecificationTests(unittest.TestCase):
    def test_novis_removes_exactly_the_visibility_features(self):
        self.assertEqual(len(VISIBILITY), 4)
        self.assertFalse(set(R0_NOVIS) & set(VISIBILITY))
        self.assertEqual(R0, R0_NOVIS + VISIBILITY)
        self.assertEqual(len(R0) - len(R0_NOVIS), 4)
        self.assertEqual(len(set(R0)), len(R0))

    def test_the_floor_carries_no_work_feature(self):
        self.assertFalse(set(FLOOR) & set(WORK_BENCH))
        self.assertFalse(set(FLOOR) & set(WORK_FIELDS))
        for name in FLOOR:
            self.assertNotIn('shared', name)
            self.assertNotIn('propensity', name)
            self.assertNotIn('proximity', name)
            self.assertNotIn('jaccard', name)
        self.assertTrue(set(VISIBILITY).issubset(set(FLOOR)))
        self.assertEqual(len(set(FLOOR)), len(FLOOR))


class PermutationTests(unittest.TestCase):
    def cases(self):
        rows = []
        for i, (layer, y) in enumerate([('House', 1), ('House', 1), ('House', 0), ('House', 0),
                                        ('Senate', 1), ('Senate', 1), ('Senate', 1), ('Senate', 0),
                                        ('cross_chamber', 0), ('cross_chamber', 0)]):
            rows.append(dict(pair=[f'a{i}', f'b{i}'], directions=[[f'a{i}', f'b{i}']], y=y,
                             sign='positive' if y else 'negative', families=[f'f{i}'], layer=layer))
        work = {(c['directions'][0][0], c['directions'][0][1]): dict(chamber=c['layer']) for c in rows}
        return rows, work

    def test_strata_come_from_the_dated_chamber_layer(self):
        cases, work = self.cases()
        strata = chamber_strata(cases, work)
        self.assertEqual(sorted(strata), ['House', 'Senate', 'cross_chamber'])
        self.assertEqual(stratum_shape(cases, strata)['cross_chamber'],
                         dict(dyads=2, positive=0, negative=2))
        self.assertEqual(distinct_permutations(cases, strata), 6 * 4 * 1)

    def test_permutation_preserves_each_stratum_positive_count(self):
        cases, work = self.cases()
        strata = chamber_strata(cases, work)
        before = stratum_shape(cases, strata)
        rng = np.random.default_rng(SEED)
        seen = set()
        for _ in range(60):
            permuted = permuted_cases(cases, strata, rng)
            self.assertEqual(stratum_shape(permuted, strata), before)
            self.assertEqual(sum(c['y'] for c in permuted), sum(c['y'] for c in cases))
            for original, new in zip(cases, permuted):
                self.assertEqual(original['pair'], new['pair'])
                self.assertEqual(original['families'], new['families'])
                self.assertEqual(original['directions'], new['directions'])
                self.assertEqual(new['sign'], 'positive' if new['y'] else 'negative')
            seen.add(tuple(c['y'] for c in permuted))
        self.assertEqual([c['y'] for c in cases], [1, 1, 0, 0, 1, 1, 1, 0, 0, 0],
                         'the source cases must not be mutated')
        self.assertGreater(len(seen), 1)
        self.assertLessEqual(len(seen), distinct_permutations(cases, strata))


class BootstrapTests(unittest.TestCase):
    def grid(self):
        rng = np.random.default_rng(7)
        return (rng.random((20, 9)) < .85).astype(float)

    def test_interval_brackets_the_point_estimate_and_is_seed_deterministic(self):
        grid = self.grid()
        point = float(grid.mean())
        draws = bootstrap_draws(20, 9, 500, SEED)
        values = bootstrap_auc(grid, draws)
        band = interval(values)
        self.assertLessEqual(band['low'], point)
        self.assertGreaterEqual(band['high'], point)
        self.assertEqual(len(values), 500)
        again = bootstrap_auc(grid, bootstrap_draws(20, 9, 500, SEED))
        np.testing.assert_array_equal(values, again)
        other = bootstrap_auc(grid, bootstrap_draws(20, 9, 500, SEED + 1))
        self.assertFalse(np.array_equal(values, other))

    def test_draw_shapes_follow_the_two_sample_dyad_design(self):
        i, j = bootstrap_draws(20, 9, 11, SEED)
        self.assertEqual(i.shape, (11, 20))
        self.assertEqual(j.shape, (11, 9))
        self.assertTrue((i < 20).all() and (j < 9).all())


class MissingWorkTests(unittest.TestCase):
    def panel(self):
        members = {'H1': member('House'), 'H2': member('House'), 'H3': member('House'),
                   'S1': member('Senate'), 'SP': member('Senate'), 'HP': member('House')}
        bills = [bill('h1', 'House', '2019-02-01', 'HP', ['H1', 'H2']),
                 bill('h2', 'House', '2019-03-01', 'HP', ['H1', 'H2', 'H3']),
                 bill('s1', 'Senate', '2019-02-01', 'SP', ['S1'])]
        return members, bills

    def test_cross_chamber_and_pre_coverage_dyads_are_missing_not_zero(self):
        members, bills = self.panel()
        cases = [dict(pair=['H1', 'S1'], first='2020-01-01', directions=[['H1', 'S1']], y=1),
                 dict(pair=['H1', 'H3'], first='2019-01-10', directions=[['H1', 'H3']], y=1),
                 dict(pair=['H1', 'H2'], first='2020-01-01', directions=[['H1', 'H2']], y=0)]
        rows, audit = build_work_rows(members, bills, cases, 'original', 'strict_before', quiet)
        cross = rows[('H1', 'S1')]
        self.assertEqual(cross['chamber'], 'cross_chamber')
        self.assertEqual(cross['work_status'], 'cross_chamber_structurally_unavailable')
        for name in WORK_FIELDS:
            self.assertIsNone(cross[name], name)
        self.assertIsNone(cross['bipartisan_pair'])
        self.assertIsNone(cross['opportunities_a_to_b'])
        self.assertIsNone(cross['opportunities_b_to_a'])
        self.assertIsNone(cross['co_service_years'],
                          'a structurally unavailable layer must not report zero co-service')
        self.assertEqual(audit['signature_policy'], 'original')
        self.assertEqual(audit['timing_policy'], 'strict_before')

    def test_a_dyad_with_no_prior_bill_has_no_work_number_at_all(self):
        members, bills = self.panel()
        cases = [dict(pair=['H1', 'H2'], first='2019-01-10', directions=[['H1', 'H2']], y=1)]
        rows, _ = build_work_rows(members, bills, cases, 'original', 'strict_before', quiet)
        row = rows[('H1', 'H2')]
        self.assertEqual(row['chamber'], 'House')
        self.assertEqual(row['work_status'], 'no_prior_covered_work')
        for name in WORK_FIELDS:
            self.assertIsNone(row[name], name)
        self.assertIsNone(row['shared_original_bills'])
        self.assertIsNone(row['opportunities_a_to_b'])
        self.assertIsNone(row['bipartisan_pair'])

    def test_a_dyad_with_prior_bills_does_get_numbers(self):
        members, bills = self.panel()
        cases = [dict(pair=['H1', 'H2'], first='2020-01-01', directions=[['H1', 'H2']], y=1)]
        rows, _ = build_work_rows(members, bills, cases, 'original', 'strict_before', quiet)
        row = rows[('H1', 'H2')]
        self.assertEqual(row['work_status'], 'prior_original_work_available')
        self.assertEqual(row['shared_original_bills'], 2)
        self.assertIsNotNone(row['opportunities_a_to_b'])
        self.assertIsNotNone(row['co_service_years'])

    def test_two_cases_cannot_share_one_direction_row(self):
        members, bills = self.panel()
        cases = [dict(pair=['H1', 'H2'], first='2020-01-01', directions=[['H1', 'H2']], y=1),
                 dict(pair=['H1', 'H2'], first='2020-06-01', directions=[['H1', 'H2']], y=0)]
        with self.assertRaises(ValueError):
            build_work_rows(members, bills, cases, 'original', 'strict_before', quiet)

    def test_the_all_policy_adds_signers_the_original_policy_omits(self):
        members, bills = self.panel()
        bills[0]['original'] = ['H1']
        bills[1]['original'] = ['H1']
        cases = [dict(pair=['H1', 'H2'], first='2020-01-01', directions=[['H1', 'H2']], y=1)]
        original, _ = build_work_rows(members, bills, cases, 'original', 'strict_before', quiet)
        every, _ = build_work_rows(members, bills, cases, 'all', 'strict_before', quiet)
        self.assertEqual(original[('H1', 'H2')]['shared_original_bills'], 0)
        self.assertEqual(every[('H1', 'H2')]['shared_original_bills'], 2)


class ContractFreezeTests(unittest.TestCase):
    def test_the_contract_dict_matches_its_frozen_digest(self):
        self.assertEqual(len(CONTRACT_SHA256), 64)
        self.assertEqual(contract_digest(), CONTRACT_SHA256)
        payload = json.dumps(CONTRACT, sort_keys=True, ensure_ascii=False)
        self.assertNotIn('None', payload[:1])
        self.assertEqual(CONTRACT['status'], 'EXPLORATORY')
        self.assertIs(CONTRACT['labels']['held_out_split_touched'], False)
        self.assertEqual(CONTRACT['labels']['dyads'], 29)
        self.assertEqual(CONTRACT['rows']['C1'],
                         dict(role='canonical', spec='R0_novis', signatures='original', timing='strict_before'))

    def test_a_changed_contract_changes_the_digest(self):
        altered = json.loads(json.dumps(CONTRACT))
        altered['rows']['C1']['timing'] = 'all_history'
        self.assertNotEqual(contract_digest(altered), CONTRACT_SHA256)

    @unittest.skipUnless((OUT / 'contract.json').exists(), 'run the benchmark first')
    def test_the_written_contract_records_the_same_digest(self):
        written = json.loads((OUT / 'contract.json').read_text(encoding='utf-8'))
        self.assertEqual(written['contract_sha256'], CONTRACT_SHA256)
        self.assertEqual(written['status'], 'EXPLORATORY')


class ReportProseNoBillDerivedWorkValueTests(unittest.TestCase):
    """The nuisance-floor paragraph in REPORT.md names how many C1 dyads have no bill-derived work
    value. S2b is C1 with exactly those dyads dropped (see the S2b 'added row' note), so the count
    must be read off the run's own C1/S2b dyad totals, not hard-coded to the frozen 116-119 value
    of eight."""

    def _report(self, total_dyads, no_bill_derived_work_dyads):
        def row(dyads, ci=False):
            r = dict(spec_label='R0_novis', features=3, feature_names=['a', 'b', 'c'], signatures='original',
                     timing='strict_before', dyads=dyads, positive=dyads // 2, negative=dyads - dyads // 2,
                     comparisons=10, expected_comparisons=10, auc=0.75, unique_fits=1, wall_seconds=0.1,
                     note='synthetic row',
                     coverage=dict(direction_rows=dyads, missing_cells_by_feature={},
                                  dyads_with_no_observed_work_feature=[]))
            if ci:
                r['ci'] = dict(low=0.60, median=0.75, high=0.85, mean=0.75, sd=0.05)
            return r

        results = {name: row(total_dyads) for name in ROW_ORDER}
        results['C1']['ci'] = dict(low=0.60, median=0.75, high=0.85, mean=0.75, sd=0.05)
        results['F1']['ci'] = dict(low=0.55, median=0.70, high=0.80, mean=0.70, sd=0.05)
        results['S2b'] = row(total_dyads - no_bill_derived_work_dyads, ci=True)
        results['F1b'] = row(total_dyads - no_bill_derived_work_dyads, ci=True)
        cases = ([dict(y=1) for _ in range(total_dyads // 2)] +
                 [dict(y=0) for _ in range(total_dyads - total_dyads // 2)])
        null = dict(permutations_completed=0, reason='synthetic fixture, no permutations run')
        measurable = dict(rows=['S2b', 'F1b'], dyads=total_dyads - no_bill_derived_work_dyads, comparisons=10,
                          point=0.05, low=-0.05, high=0.15, fraction_above_zero=0.7, replicates=200,
                          caveat='synthetic caveat')
        return report_text(results, null, 'deadbeef', cases, {}, 1, ['synthetic note'], measurable)

    def test_five_dyads_with_no_bill_derived_work_value_renders_as_a_numeral(self):
        text = self._report(total_dyads=20, no_bill_derived_work_dyads=5)
        self.assertIn('and 5 with no bill-derived work value', text)
        self.assertNotIn('eight', text)

    def test_eight_dyads_with_no_bill_derived_work_value_renders_as_a_numeral(self):
        text = self._report(total_dyads=20, no_bill_derived_work_dyads=8)
        self.assertIn('and 8 with no bill-derived work value', text)
        self.assertNotIn('eight', text)


class DefaultBillsFlagsReproduceTheFrozenRunTests(unittest.TestCase):
    """Touches live lane data via a fast (--permutations 0) rerun; skips cleanly where the frozen
    benchmark has not been built."""

    @unittest.skipUnless((OUT / 'results.json').exists(), 'run the benchmark first')
    @unittest.skipUnless(os.environ.get('RUN_SLOW_CONTRACT_TESTS') == '1',
                         'rebuilds the whole benchmark (about 3 minutes uncontended, far longer under load); '
                         'opt in with RUN_SLOW_CONTRACT_TESTS=1')
    def test_default_bills_and_range_reproduce_the_frozen_rows(self):
        old = json.loads((OUT / 'results.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as tmp:
            completed = subprocess.run(
                [sys.executable, '-m', 'fec.research.member_personal_relationships.benchmark_contract',
                 '--permutations', '0', '--output-dir', tmp],
                cwd=str(ROOT), env=dict(os.environ, PYTHONPATH=str(ROOT)),
                capture_output=True, text=True, timeout=2400)
            self.assertEqual(completed.returncode, 0, completed.stdout[-4000:] + completed.stderr[-4000:])
            fresh = json.loads((Path(tmp) / 'results.json').read_text(encoding='utf-8'))
        for name in ROW_ORDER:
            self.assertEqual(fresh['rows'][name]['auc'], old['rows'][name]['auc'], name)
            self.assertEqual(fresh['rows'][name]['comparisons'], old['rows'][name]['comparisons'], name)
        self.assertEqual(fresh['reference_reproduced'], old['reference_reproduced'])


if __name__ == '__main__':
    unittest.main()
