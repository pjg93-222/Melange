"""Synthetic-only tests for the mechanical expression-contrast consumer.

No live census, no live roster, no frozen sample is read here. Every fixture is
built in a temporary directory, so these tests can never touch, or depend on, the
sealed held-out split.
"""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from fec.research.member_personal_relationships.expression_contrasts import (
    AVAILABLE, CLASSIFIER, INSUFFICIENT, LEADERBOARD_MIN_N, POOLED, SAMPLING_BASIS,
    SOURCES, VARIANT_UNDEFINED, assert_no_heldout, build, calibration_for,
    contrast_arguments, exposure_status, load_calibration, load_sample,
    mann_whitney_auc, median_iqr, pair_id_of, pooled_baseline, pooled_counts,
    turn_level_arguments, turn_level_block)
from fec.research.member_personal_relationships.relative_expression import relative_contrast


def term(start, end, chamber):
    return dict(start=start, end=end, chamber=chamber, state='CA', party='Democrat')


MEMBERS = {
    'A1': dict(bioguide='A1', name='Ann Alpha', chamber='House',
               terms=[term('2019-01-03', '2027-01-03', 'House')]),
    'B1': dict(bioguide='B1', name='Bob Beta', chamber='House',
               terms=[term('2019-01-03', '2027-01-03', 'House')]),
    'C1': dict(bioguide='C1', name='Cal Gamma', chamber='Senate',
               terms=[term('2019-01-03', '2027-01-03', 'Senate')]),
    'D1': dict(bioguide='D1', name='Dee Delta', chamber='Senate',
               terms=[term('2019-01-03', '2027-01-03', 'Senate')]),
}


def count(actor, target, source, mention, warm, hostile, personal=0,
          first='2021-01-05', last='2021-06-06'):
    return dict(actor=actor, target=target, source=source, venue=source,
                actor_name=MEMBERS[actor]['name'], target_name=MEMBERS[target]['name'],
                mention_turns=mention, warm_turns=warm, hostile_turns=hostile,
                personal_turns=personal, first_date=first, last_date=last,
                forms=dict(titled_surname=mention))


def baseline(actor, source, *, total, colleague, distinct, mention_sum, warm_sum,
             hostile_sum, warm_turns, hostile_turns, personal_sum=0, personal_turns=0):
    return dict(actor=actor, source=source, venue=source, actor_name=MEMBERS[actor]['name'],
                total_turns=total, colleague_mention_turns=colleague, distinct_targets=distinct,
                target_mention_turn_sum=mention_sum, target_warm_turn_sum=warm_sum,
                target_hostile_turn_sum=hostile_sum, target_personal_turn_sum=personal_sum,
                warm_turns=warm_turns, hostile_turns=hostile_turns, personal_turns=personal_turns)


# A1 names B1 four times on the floor (three warm) and C1 six times (one warm, two
# hostile), so a leave-one-target-out baseline for B1 is exactly C1's six turns.
# A1's turn-level warm_turns is deliberately larger than colleague_mention_turns,
# which is what makes the turn-level reading undefined.
COUNTS = [
    count('A1', 'B1', 'CREC', 4, 3, 0),
    count('A1', 'C1', 'CREC', 6, 1, 2),
    count('A1', 'B1', 'INTERVIEW', 2, 2, 0, first='2022-02-02', last='2022-02-02'),
    count('C1', 'D1', 'CREC', 1, 0, 0),
]
BASELINES = [
    baseline('A1', 'CREC', total=50, colleague=8, distinct=2, mention_sum=10, warm_sum=4,
             hostile_sum=2, warm_turns=9, hostile_turns=2),
    baseline('A1', 'INTERVIEW', total=5, colleague=2, distinct=1, mention_sum=2, warm_sum=2,
             hostile_sum=0, warm_turns=2, hostile_turns=0),
    baseline('C1', 'CREC', total=3, colleague=1, distinct=1, mention_sum=1, warm_sum=0,
             hostile_sum=0, warm_turns=0, hostile_turns=0),
]
CASES = [
    dict(pair=['A1', 'B1'], sign='positive', y=1, directions=[['A1', 'B1']],
         families=['f1'], first='2021-01-05', last='2021-06-06', evidence_ids=['e1'],
         episodes=['f1'], names=['Ann Alpha', 'Bob Beta']),
    dict(pair=['A1', 'C1'], sign='negative', y=0, directions=[['A1', 'C1'], ['C1', 'A1']],
         families=['f2'], first='2021-02-02', last='2021-02-02', evidence_ids=['e2'],
         episodes=['f2'], names=['Ann Alpha', 'Cal Gamma']),
]
SAMPLE = [
    dict(pair=['A1', 'B1'], pair_id='A1__B1', names=['Ann Alpha', 'Bob Beta'],
         split='development', stratum='LH|same|House+House', design_weight=12.5),
    dict(pair=['C1', 'D1'], pair_id='C1__D1', names=['Cal Gamma', 'Dee Delta'],
         split='heldout', stratum='LH|same|Senate+Senate', design_weight=99.9,
         affinity=1, antagonism=0),
]
CALIBRATION = {
    'House|CREC': dict(warm_precision=.62, warm_recall=.41, hostile_precision=.30,
                       hostile_recall=.22, reviewed=40),
    'House|INTERVIEW': dict(warm_precision=.55, warm_recall=.38, hostile_precision=.25,
                            hostile_recall=.19, reviewed=40),
    'House|CHRG': dict(warm_precision=.70, warm_recall=.44, hostile_precision=.33,
                       hostile_recall=.28, reviewed=40),
    'Senate|CREC': dict(warm_precision=.71, warm_recall=.50, hostile_precision=.40,
                        hostile_recall=.31, reviewed=40),
    'Senate|INTERVIEW': dict(warm_precision=.60, warm_recall=.45, hostile_precision=.35,
                             hostile_recall=.29, reviewed=40),
    'Senate|CHRG': dict(warm_precision=.66, warm_recall=.47, hostile_precision=.38,
                        hostile_recall=.30, reviewed=40),
}


def write_ndjson(path, rows):
    path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows),
                    encoding='utf-8', newline='\n')


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def fixture(root, *, counts=None, baselines=None, cases=None, sample=None, pin=True):
    """Lay out a synthetic census plus its three consumer inputs."""
    root = Path(root)
    census = root / 'census'
    census.mkdir(parents=True, exist_ok=True)
    write_ndjson(census / 'encounter_counts.ndjson', COUNTS if counts is None else counts)
    write_ndjson(census / 'speaker_baseline.ndjson', BASELINES if baselines is None else baselines)
    artefacts = [dict(name=n, bytes=(census / n).stat().st_size,
                      sha256=sha256_file(census / n) if pin else '0' * 64)
                 for n in ('encounter_counts.ndjson', 'speaker_baseline.ndjson')]
    write_json(census / 'manifest.json', dict(status='EXPLORATORY', artefacts=artefacts,
                                              denominator_contract=dict(n='mention_turns')))
    write_json(root / 'cases.json', CASES if cases is None else cases)
    write_ndjson(root / 'sampled_pairs.ndjson', SAMPLE if sample is None else sample)
    write_json(root / 'members.json', MEMBERS)
    return dict(census_dir=census, cases_path=root / 'cases.json',
                sample_path=root / 'sampled_pairs.ndjson', members_path=root / 'members.json')


def run_build(root, out_name='out', **overrides):
    paths = fixture(root, **{k: v for k, v in overrides.items()
                             if k in ('counts', 'baselines', 'cases', 'sample', 'pin')})
    out = Path(root) / out_name
    receipt = build(out, calibration_path=overrides.get('calibration_path'),
                    progress=lambda *a, **k: None, **paths)
    rows = [json.loads(line) for line in
            (out / 'expression_contrasts.ndjson').read_text(encoding='utf-8').splitlines()]
    return receipt, rows, out


def indexed(rows):
    return {(r['actor'], r['target'], r['source']): r for r in rows}


class ArgumentMapping(unittest.TestCase):
    def test_other_n_excludes_the_focal_target(self):
        count_row = dict(mention_turns=4, warm_turns=3, hostile_turns=0)
        base = BASELINES[0]
        self.assertEqual(contrast_arguments(count_row, base, 'warm'), (4, 3, 6, 1))
        self.assertEqual(contrast_arguments(count_row, base, 'hostile'), (4, 0, 6, 2))
        # The excluded remainder is exactly the other target's own counts.
        other = COUNTS[1]
        self.assertEqual(contrast_arguments(count_row, base, 'warm')[2], other['mention_turns'])
        self.assertEqual(contrast_arguments(count_row, base, 'warm')[3], other['warm_turns'])
        self.assertEqual(contrast_arguments(count_row, base, 'hostile')[3], other['hostile_turns'])

    def test_rejects_an_unknown_channel(self):
        with self.assertRaises(ValueError):
            contrast_arguments(COUNTS[0], BASELINES[0], 'personal')

    def test_row_contrast_is_relative_contrast_of_those_arguments(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            row = indexed(rows)[('A1', 'B1', 'CREC')]
            self.assertEqual(row['warm_contrast'], relative_contrast(4, 3, 6, 1))
            self.assertEqual(row['hostile_contrast'], relative_contrast(4, 0, 6, 2))
            self.assertEqual(row['other_n'], 6)
            self.assertEqual(row['other_warm'], 1)
            self.assertEqual(row['other_hostile'], 2)
            self.assertLess(row['warm_contrast']['baseline_rate'], row['warm_contrast']['target_rate'])

    def test_turn_level_variant_is_undefined_when_positives_exceed_opportunities(self):
        # A1 CREC: colleague_mention_turns 8, warm_turns 9 -> other_warm 6 > other_n 4.
        self.assertEqual(turn_level_arguments(COUNTS[0], BASELINES[0], 'warm'), (4, 3, 4, 6))
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            row = indexed(rows)[('A1', 'B1', 'CREC')]
            self.assertEqual(row['turn_level_variant']['status'], VARIANT_UNDEFINED)
            self.assertIsNone(row['turn_level_variant']['warm_contrast'])
            # The contracted mapping on the same row stays defined.
            self.assertEqual(row['status'], AVAILABLE)
            self.assertIsNotNone(row['warm_contrast']['contrast'])

    def test_turn_level_variant_statuses_across_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            row = indexed(rows)[('A1', 'C1', 'CREC')]
            # other_n = 8-6 = 2, other_warm = 9-1 = 8 -> still undefined for warm,
            # but hostile (2-2=0 positives) is fine, so the block reports the worst case.
            self.assertEqual(row['turn_level_variant']['status'], VARIANT_UNDEFINED)
            interview = indexed(rows)[('A1', 'B1', 'INTERVIEW')]
            # other_n = 2-2 = 0 -> no comparison at all, not an undefined one.
            self.assertEqual(interview['turn_level_variant']['status'], INSUFFICIENT)


class TurnLevelVariantGuard(unittest.TestCase):
    """relative_contrast rejects positives>opportunities BEFORE its zero-denominator return."""

    def block(self, mention, warm, colleague, speaker_warm):
        return turn_level_block(
            dict(mention_turns=mention, warm_turns=warm, hostile_turns=0),
            dict(colleague_mention_turns=colleague, warm_turns=speaker_warm, hostile_turns=0))

    def test_zero_opportunities_with_leftover_positives_is_undefined_not_insufficient(self):
        # other_n = 2-2 = 0 while other_warm = 3-2 = 1: relative_contrast would raise.
        block = self.block(2, 2, 2, 3)
        self.assertEqual(block['status'], VARIANT_UNDEFINED)
        self.assertIsNone(block['warm_contrast'])
        self.assertEqual(block['other_n'], 0)
        self.assertEqual(block['other_warm'], 1)

    def test_zero_opportunities_with_no_leftover_positives_is_merely_insufficient(self):
        block = self.block(2, 2, 2, 2)
        self.assertEqual(block['status'], INSUFFICIENT)
        self.assertIsNone(block['warm_contrast'])

    def test_a_well_formed_variant_is_available(self):
        block = self.block(2, 1, 6, 2)
        self.assertEqual(block['status'], AVAILABLE)
        self.assertIsNotNone(block['warm_contrast'])
        self.assertEqual(block['other_n'], 4)
        self.assertEqual(block['other_warm'], 1)

    def test_per_channel_status_is_reported_separately_from_the_block_status(self):
        # warm is undefined (3-2=1 > 0) while hostile has nothing left over.
        block = self.block(2, 2, 2, 3)
        self.assertEqual(block['warm_status'], VARIANT_UNDEFINED)
        self.assertEqual(block['hostile_status'], INSUFFICIENT)
        self.assertEqual(block['status'], VARIANT_UNDEFINED)

    def test_census_row_undefined_counts_use_the_census_denominator(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, rows, _ = run_build(tmp)
            block = receipt['diagnostics']['turn_level_variant_undefined_on_census_rows']
            census_rows = [r for r in rows if r['source'] != POOLED and r['n'] >= 1]
            self.assertEqual(block['census_rows'], len(census_rows))
            self.assertEqual(block['census_rows'], len(COUNTS))
            self.assertEqual(block['warm'], sum(
                1 for r in census_rows
                if r['turn_level_variant']['warm_status'] == VARIANT_UNDEFINED))
            self.assertEqual(block['hostile'], sum(
                1 for r in census_rows
                if r['turn_level_variant']['hostile_status'] == VARIANT_UNDEFINED))

    def test_the_whole_live_shaped_fixture_builds_without_raising(self):
        # Same shape as the row that broke the first live run.
        baselines = [baseline('A1', 'CREC', total=50, colleague=8, distinct=2, mention_sum=10,
                              warm_sum=4, hostile_sum=2, warm_turns=9, hostile_turns=2),
                     baseline('A1', 'INTERVIEW', total=5, colleague=2, distinct=1, mention_sum=2,
                              warm_sum=2, hostile_sum=0, warm_turns=3, hostile_turns=1),
                     baseline('C1', 'CREC', total=3, colleague=1, distinct=1, mention_sum=1,
                              warm_sum=0, hostile_sum=0, warm_turns=2, hostile_turns=0)]
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp, baselines=baselines)
            index = indexed(rows)
            self.assertEqual(index[('A1', 'B1', 'INTERVIEW')]['turn_level_variant']['status'],
                             VARIANT_UNDEFINED)
            self.assertEqual(index[('C1', 'D1', 'CREC')]['turn_level_variant']['status'],
                             VARIANT_UNDEFINED)
            # The contracted mapping is unaffected by the variant's undefined rows.
            self.assertEqual(index[('A1', 'B1', 'CREC')]['status'], AVAILABLE)


class StatusRule(unittest.TestCase):
    def test_exposure_status_boundaries(self):
        self.assertEqual(exposure_status(1, 1), AVAILABLE)
        self.assertEqual(exposure_status(0, 5), INSUFFICIENT)
        self.assertEqual(exposure_status(5, 0), INSUFFICIENT)
        self.assertEqual(exposure_status(0, 0), INSUFFICIENT)

    def test_status_value_is_distinct_from_the_reviewed_gate(self):
        self.assertEqual(INSUFFICIENT, 'insufficient_systematic_exposure')
        self.assertNotEqual(INSUFFICIENT, 'insufficient_systematic_reviewed_exposure')

    def test_rows_take_the_status_rule(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            index = indexed(rows)
            self.assertEqual(index[('A1', 'B1', 'CREC')]['status'], AVAILABLE)
            # C1 named only D1, so there is no other target to compare against.
            self.assertEqual(index[('C1', 'D1', 'CREC')]['status'], INSUFFICIENT)
            self.assertEqual(index[('C1', 'D1', 'CREC')]['other_n'], 0)
            self.assertIsNone(index[('C1', 'D1', 'CREC')]['warm_contrast']['contrast'])
            # A source the pair never appears in is emitted, with n = 0.
            self.assertEqual(index[('A1', 'B1', 'CHRG')]['n'], 0)
            self.assertEqual(index[('A1', 'B1', 'CHRG')]['status'], INSUFFICIENT)

    def test_every_directed_pair_gets_every_source_plus_pooled(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, rows, _ = run_build(tmp)
            self.assertEqual(receipt['directed_pairs'], 3)
            self.assertEqual(len(rows), 3 * (len(SOURCES) + 1))
            for pair in (('A1', 'B1'), ('A1', 'C1'), ('C1', 'D1')):
                got = sorted(r['source'] for r in rows
                             if (r['actor'], r['target']) == pair)
                self.assertEqual(got, sorted(list(SOURCES) + [POOLED]))

    def test_every_row_carries_the_provenance_stamps(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, rows, _ = run_build(tmp)
            manifest_sha = receipt['inputs']['manifest.json']['sha256']
            for row in rows:
                self.assertEqual(row['sampling_basis'], SAMPLING_BASIS)
                self.assertEqual(row['classifier'], CLASSIFIER)
                self.assertEqual(row['census_manifest_sha256'], manifest_sha)
                self.assertIsNone(row['calibration'])

    def test_stale_census_manifest_pins_are_recorded_not_hidden(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, _, _ = run_build(tmp, pin=False)
            block = receipt['inputs']['encounter_counts.ndjson']
            self.assertFalse(block['matches_census_manifest'])
            self.assertNotEqual(block['sha256'], block['manifest_sha256'])


class Pooling(unittest.TestCase):
    def test_pooled_counts_sum_and_take_the_date_envelope(self):
        pooled = pooled_counts([COUNTS[0], COUNTS[2]])
        self.assertEqual(pooled['mention_turns'], 6)
        self.assertEqual(pooled['warm_turns'], 5)
        self.assertEqual(pooled['first_date'], '2021-01-05')
        self.assertEqual(pooled['last_date'], '2022-02-02')

    def test_pooled_baseline_sums_every_source_the_speaker_appears_in(self):
        pooled = pooled_baseline([BASELINES[0], BASELINES[1]])
        self.assertEqual(pooled['target_mention_turn_sum'], 12)
        self.assertEqual(pooled['target_warm_turn_sum'], 6)
        self.assertEqual(pooled['total_turns'], 55)

    def test_pooled_row_equals_the_sum_of_the_source_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            index = indexed(rows)
            pooled = index[('A1', 'B1', POOLED)]
            per_source = [index[('A1', 'B1', s)] for s in SOURCES]
            for field in ('n', 'warm', 'hostile', 'personal'):
                self.assertEqual(pooled[field], sum(r[field] for r in per_source), field)
            self.assertEqual(pooled['n'], 6)
            self.assertEqual(pooled['warm'], 5)
            self.assertEqual(pooled['other_n'], 6)
            self.assertEqual(pooled['other_warm'], 1)
            self.assertEqual(pooled['warm_contrast'], relative_contrast(6, 5, 6, 1))
            self.assertEqual(pooled['row_kind'], POOLED)
            self.assertEqual(pooled['first_date'], '2021-01-05')
            self.assertEqual(pooled['last_date'], '2022-02-02')


class HeldOutSeal(unittest.TestCase):
    def test_load_sample_keeps_development_rows_and_only_ids_from_the_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = fixture(tmp)
            development, denied = load_sample(paths['sample_path'])
            self.assertEqual([r['pair_id'] for r in development], ['A1__B1'])
            self.assertEqual(denied, frozenset({'C1__D1'}))

    def test_assert_no_heldout_raises_on_a_sealed_dyad(self):
        rows = [dict(actor='D1', target='C1'), dict(actor='A1', target='B1')]
        with self.assertRaises(ValueError) as caught:
            assert_no_heldout(rows, frozenset({'C1__D1'}), 'unit_test_view')
        self.assertIn('C1__D1', str(caught.exception))
        self.assertIn('unit_test_view', str(caught.exception))
        self.assertEqual(assert_no_heldout(rows, frozenset({'X__Y'}), 'unit_test_view'), 2)

    def test_pair_id_is_direction_free(self):
        self.assertEqual(pair_id_of('C1', 'D1'), pair_id_of('D1', 'C1'))

    def test_build_refuses_a_benchmark_dyad_that_is_sealed(self):
        poisoned = CASES + [dict(pair=['C1', 'D1'], sign='positive', y=1,
                                 directions=[['C1', 'D1']], families=['f3'],
                                 first='2021-03-03', last='2021-03-03', evidence_ids=['e3'],
                                 episodes=['f3'], names=['Cal Gamma', 'Dee Delta'])]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as caught:
                run_build(tmp, cases=poisoned)
            self.assertIn('C1__D1', str(caught.exception))
            self.assertIn('sign_benchmark_contrasts', str(caught.exception))

    def test_views_carry_their_own_keys_and_both_directions(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, out = run_build(tmp)
            dev = [json.loads(l) for l in
                   (out / 'development_pair_contrasts.ndjson').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(dev), 2 * (len(SOURCES) + 1))
            self.assertEqual({(r['actor'], r['target']) for r in dev}, {('A1', 'B1'), ('B1', 'A1')})
            self.assertTrue(all(r['design_weight'] == 12.5 and r['split'] == 'development'
                                for r in dev))
            bench = [json.loads(l) for l in
                     (out / 'sign_benchmark_contrasts.ndjson').read_text(encoding='utf-8').splitlines()]
            self.assertEqual(len(bench), 2 * 2 * (len(SOURCES) + 1))
            self.assertEqual({r['sign'] for r in bench}, {'positive', 'negative'})
            self.assertEqual({(r['actor'], r['target']) for r in bench},
                             {('A1', 'B1'), ('B1', 'A1'), ('A1', 'C1'), ('C1', 'A1')})
            self.assertNotIn('C1__D1', {r['dyad_pair_id'] for r in bench})


class Calibration(unittest.TestCase):
    def test_matches_stratum_by_speaker_chamber_and_source_and_records_the_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'cue_precision_recall.json'
            write_json(path, CALIBRATION)
            receipt, rows, _ = run_build(tmp, calibration_path=path)
            self.assertEqual(receipt['calibration']['sha256'], sha256_file(path))
            self.assertEqual(receipt['calibration']['strata'], sorted(CALIBRATION))
            index = indexed(rows)
            self.assertEqual(index[('A1', 'B1', 'CREC')]['calibration'], CALIBRATION['House|CREC'])
            self.assertEqual(index[('A1', 'B1', 'INTERVIEW')]['calibration'],
                             CALIBRATION['House|INTERVIEW'])
            # C1 is a senator, so the same source resolves to a different stratum.
            self.assertEqual(index[('C1', 'D1', 'CREC')]['calibration'], CALIBRATION['Senate|CREC'])
            # Pooled rows carry every stratum that contributed a mention.
            self.assertEqual(index[('A1', 'B1', POOLED)]['calibration'],
                             {'House|CREC': CALIBRATION['House|CREC'],
                              'House|INTERVIEW': CALIBRATION['House|INTERVIEW']})
            self.assertEqual(index[('C1', 'D1', POOLED)]['calibration'],
                             {'Senate|CREC': CALIBRATION['Senate|CREC']})
            for row in rows:
                self.assertEqual(row['classifier'], CLASSIFIER)

    def test_absent_calibration_leaves_every_row_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, rows, _ = run_build(tmp)
            self.assertIsNone(receipt['calibration']['sha256'])
            self.assertIsNone(receipt['calibration']['strata'])
            self.assertTrue(all(r['calibration'] is None for r in rows))

    def test_accepts_both_the_bare_and_the_wrapped_receipt_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            bare = Path(tmp) / 'bare.json'
            wrapped = Path(tmp) / 'wrapped.json'
            write_json(bare, CALIBRATION)
            write_json(wrapped, dict(status='EXPLORATORY', strata=CALIBRATION, reviewed=240))
            self.assertEqual(load_calibration(bare)[0], load_calibration(wrapped)[0])
            self.assertNotEqual(load_calibration(bare)[1], load_calibration(wrapped)[1])
            broken = Path(tmp) / 'broken.json'
            write_json(broken, dict(precision=.5, recall=.5))
            with self.assertRaises(ValueError):
                load_calibration(broken)

    def test_no_match_leaves_the_field_null(self):
        self.assertIsNone(calibration_for(CALIBRATION, None, 'CREC'))
        self.assertIsNone(calibration_for(None, 'House', 'CREC'))
        self.assertIsNone(calibration_for(CALIBRATION, 'House', POOLED, ()))
        self.assertIsNone(calibration_for({'House|CREC': {}}, 'Senate', 'CREC'))


class AucHelper(unittest.TestCase):
    def test_hand_built_case_with_one_tie(self):
        # 3>0,3>1 | 2>0,2>1 | 1>0, 1==1 -> 5 wins, 1 tie, 6 comparisons.
        result = mann_whitney_auc([3, 2, 1], [0, 1])
        self.assertEqual(result['n_pos'], 3)
        self.assertEqual(result['n_neg'], 2)
        self.assertEqual(result['comparisons'], 6)
        self.assertEqual(result['wins'], 5)
        self.assertEqual(result['ties'], 1)
        self.assertAlmostEqual(result['auc'], 5.5 / 6)

    def test_perfect_and_inverted_separation(self):
        self.assertEqual(mann_whitney_auc([5, 6], [1, 2])['auc'], 1.0)
        self.assertEqual(mann_whitney_auc([1, 2], [5, 6])['auc'], 0.0)
        self.assertEqual(mann_whitney_auc([1, 1], [1, 1])['auc'], 0.5)

    def test_missing_values_are_dropped_and_an_empty_side_yields_none(self):
        result = mann_whitney_auc([3, None, 1], [0])
        self.assertEqual(result['n_pos'], 2)
        self.assertEqual(result['auc'], 1.0)
        empty = mann_whitney_auc([], [1, 2])
        self.assertIsNone(empty['auc'])
        self.assertEqual(empty['comparisons'], 0)

    def test_median_iqr_on_a_known_sample(self):
        block = median_iqr([1, 2, 3, 4])
        self.assertEqual(block['n'], 4)
        self.assertAlmostEqual(block['median'], 2.5)
        self.assertAlmostEqual(block['q1'], 1.75)
        self.assertAlmostEqual(block['q3'], 3.25)
        self.assertAlmostEqual(block['iqr'], 1.5)
        self.assertIsNone(median_iqr([])['median'])


class Diagnostics(unittest.TestCase):
    def test_coverage_and_leaderboards_respect_denominators_and_the_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, _, out = run_build(tmp)
            d = receipt['diagnostics']
            self.assertEqual(d['status'], 'EXPLORATORY')
            bench = d['coverage']['sign_benchmark']
            self.assertEqual(bench[POOLED]['dyads'], 2)
            self.assertEqual(bench[POOLED]['available_in_at_least_one_direction'], 2)
            self.assertEqual(bench['CHRG']['available_in_at_least_one_direction'], 0)
            dev = d['coverage']['development_sample']
            self.assertEqual(dev[POOLED]['dyads'], 1)
            board = d['leaderboards']
            self.assertEqual(board['minimum_n'], LEADERBOARD_MIN_N)
            # C1->D1 has n = 1 and is sealed; neither table may show it.
            self.assertNotIn('C1', {r['actor'] for r in board['top_warm']})
            self.assertTrue(all(r['n'] >= LEADERBOARD_MIN_N for r in board['top_warm']))
            self.assertEqual(board['heldout_directed_pairs_excluded'], 0)
            self.assertEqual(json.loads((out / 'diagnostics.json').read_text(encoding='utf-8')), d)

    def test_an_eligible_sealed_dyad_is_excluded_from_the_leaderboards_and_counted(self):
        counts = COUNTS[:3] + [count('C1', 'D1', 'CREC', 5, 4, 0),
                               count('C1', 'A1', 'CREC', 4, 0, 0)]
        baselines = BASELINES[:2] + [
            baseline('C1', 'CREC', total=20, colleague=7, distinct=2, mention_sum=9,
                     warm_sum=4, hostile_sum=0, warm_turns=4, hostile_turns=0)]
        with tempfile.TemporaryDirectory() as tmp:
            receipt, rows, _ = run_build(tmp, counts=counts, baselines=baselines)
            sealed = indexed(rows)[('C1', 'D1', POOLED)]
            self.assertEqual(sealed['status'], AVAILABLE)
            self.assertGreaterEqual(sealed['n'], LEADERBOARD_MIN_N)
            board = receipt['diagnostics']['leaderboards']
            self.assertEqual(board['heldout_directed_pairs_excluded'], 1)
            self.assertEqual(receipt['diagnostics']['heldout_dyads_in_census_rows'], 1)
            for table in ('top_warm', 'top_hostile'):
                self.assertNotIn(('C1', 'D1'), {(r['actor'], r['target']) for r in board[table]})

    def test_separation_block_reports_its_own_denominators(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, _, _ = run_build(tmp)
            sep = receipt['diagnostics']['sign_separation']
            self.assertEqual(sep['dyads_total'], 2)
            self.assertEqual(sep['dyads_scored'] + sep['dropped_no_available_contrast'], 2)
            self.assertEqual(sep['warm_contrast']['n_pos'], 1)
            self.assertEqual(sep['warm_contrast']['n_neg'], 1)
            self.assertIn('sign-among-documented-ties', sep['interpretation'])
            for sign in ('positive', 'negative'):
                block = sep['group_sizes'][sign]
                self.assertEqual(block['documented'], 1)
                self.assertEqual(block['scored'], 1)
                self.assertEqual(block['dropped'], [])

    def test_a_one_sided_drop_is_named_not_just_counted(self):
        # A1 never names D1, so the extra documented-positive dyad cannot be scored.
        cases = CASES + [dict(pair=['A1', 'D1'], sign='positive', y=1,
                              directions=[['A1', 'D1']], families=['f4'], first='2021-04-04',
                              last='2021-04-04', evidence_ids=['e4'], episodes=['f4'],
                              names=['Ann Alpha', 'Dee Delta'])]
        with tempfile.TemporaryDirectory() as tmp:
            receipt, _, _ = run_build(tmp, cases=cases)
            sep = receipt['diagnostics']['sign_separation']
            self.assertEqual(sep['dropped_no_available_contrast'], 1)
            self.assertEqual(sep['group_sizes']['positive']['documented'], 2)
            self.assertEqual(sep['group_sizes']['positive']['scored'], 1)
            self.assertEqual(sep['group_sizes']['positive']['dropped'], ['A1__D1'])
            self.assertEqual(sep['group_sizes']['negative']['dropped'], [])

    def test_baseline_warm_rate_is_keyed_by_chamber_and_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt, _, _ = run_build(tmp)
            strata = receipt['diagnostics']['baseline_warm_rate']['strata']
            self.assertIn('House|CREC', strata)
            self.assertIn('Senate|CREC', strata)
            self.assertEqual(strata['House|CREC']['n'], 1)
            # A1 CREC: (4 + 0.5) / (10 + 1)
            self.assertAlmostEqual(strata['House|CREC']['median'], 4.5 / 11)
            self.assertAlmostEqual(strata['Senate|CREC']['median'], .5 / 2)


class Determinism(unittest.TestCase):
    def test_two_runs_produce_identical_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = fixture(tmp)
            digests = []
            for name in ('run_a', 'run_b'):
                out = Path(tmp) / name
                build(out, progress=lambda *a, **k: None, **paths)
                digests.append({f: sha256_file(out / f) for f in (
                    'expression_contrasts.ndjson', 'sign_benchmark_contrasts.ndjson',
                    'development_pair_contrasts.ndjson', 'diagnostics.json')})
            self.assertEqual(digests[0], digests[1])
            self.assertEqual(len(set(digests[0].values())), 4)

    def test_rows_are_emitted_in_a_stable_sorted_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, rows, _ = run_build(tmp)
            keys = [(r['actor'], r['target']) for r in rows]
            grouped = [k for i, k in enumerate(keys) if i == 0 or keys[i - 1] != k]
            self.assertEqual(grouped, sorted(set(keys)))
            self.assertEqual(grouped, [('A1', 'B1'), ('A1', 'C1'), ('C1', 'D1')])
            self.assertEqual([r['source'] for r in rows[:4]], list(SOURCES) + [POOLED])


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
