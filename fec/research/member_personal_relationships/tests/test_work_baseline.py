"""Contracts for the original-cosponsorship expected-rate baseline (P1 item 7).

Every test here runs on a synthetic panel written into a temporary directory. None
of them reads the real lane artefacts, and none of them reads a held-out label.
"""
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from fec.research.member_personal_relationships import work_baseline as wb
from fec.research.member_personal_relationships.chamber_work import temporal_features


# ------------------------------------------------------------------- fixtures

HOUSE = ['H%02d' % i for i in range(1, 13)]
SENATE = ['S%02d' % i for i in range(1, 4)]
W115 = ('2017-01-03', '2019-01-03')
W116 = ('2019-01-03', '2021-01-03')
W117 = ('2021-01-03', '2023-01-03')
WINDOWS = {115: W115, 116: W116, 117: W117}
LATE_ARRIVAL = '2019-09-01'


def person(bioguide, chamber, state, party, d1, start='2019-01-03', include_115=False):
    terms = [dict(start=start, end=W116[1], chamber=chamber, state=state, party=party),
             dict(start=W117[0], end=W117[1], chamber=chamber, state=state, party=party)]
    if include_115:
        terms.insert(0, dict(start=W115[0], end=W115[1], chamber=chamber, state=state, party=party))
    return dict(bioguide=bioguide, name=bioguide, terms=terms, chamber=chamber, state=state,
                party=party, d1=d1, d2=0.0, leader=False, leadership_role=None)


def make_members(include_115=False):
    members = {}
    for index, bioguide in enumerate(HOUSE):
        members[bioguide] = person(bioguide, 'House', ['CA', 'TX', 'NY'][index % 3],
                                   'Democrat' if index % 2 == 0 else 'Republican',
                                   None if bioguide == 'H12' else round(-0.6 + 0.1 * index, 3),
                                   include_115=include_115 and bioguide != 'H11')
    # H11 arrives mid-congress: its earlier opportunities never existed.
    members['H11']['terms'][0]['start'] = LATE_ARRIVAL
    for index, bioguide in enumerate(SENATE):
        members[bioguide] = person(bioguide, 'Senate', ['CA', 'TX', 'NY'][index % 3],
                                   'Democrat' if index % 2 == 0 else 'Republican', 0.1 * index,
                                   include_115=include_115)
    return members


def bill(key, congress, chamber, sponsor, introduced, originals, later=()):
    joins = {a: introduced for a in originals}
    joins.update({a: later_day for a, later_day in later})
    return dict(key=key, congress=congress, chamber=chamber, sponsor=sponsor, introduced=introduced,
                end=WINDOWS[congress][1], title=key, area='Health',
                joins=joins, withdrawals={}, original=sorted(originals), size=len(joins),
                updated=introduced, url='https://example.invalid/' + key)


def make_bills(seed=11, congresses=(116, 117)):
    generator = np.random.default_rng(seed)
    rows = []
    for congress in congresses:
        window = WINDOWS[congress]
        day_zero = np.datetime64(window[0])
        for number in range(60):
            # H03 sponsors nothing, so every pair that points at it is no_eligible_bills.
            sponsor = HOUSE[(number % (len(HOUSE) - 1)) + (1 if number % (len(HOUSE) - 1) >= 2 else 0)]
            if sponsor == 'H03':
                sponsor = 'H04'
            day = str(day_zero + np.timedelta64(int(30 + number * 8), 'D'))
            eligible = [a for a in HOUSE if a != sponsor
                        and (a != 'H11' or congress == 117 or day >= LATE_ARRIVAL)]
            picked = generator.random(len(eligible)) < 0.12
            originals = [a for a, take in zip(eligible, picked) if take]
            rows.append(bill('%d:hr:%d' % (congress, number), congress, 'House', sponsor, day, originals))
        for number in range(24):
            sponsor = SENATE[number % len(SENATE)]
            day = str(day_zero + np.timedelta64(int(20 + number * 20), 'D'))
            eligible = [a for a in SENATE if a != sponsor]
            picked = generator.random(len(eligible)) < 0.4
            rows.append(bill('%d:s:%d' % (congress, number), congress, 'Senate', sponsor, day,
                             [a for a, take in zip(eligible, picked) if take]))
    return rows


def make_cases():
    """Four documented dyads: two positive, two negative, one of them cross-chamber."""
    def case(a, b, sign):
        return dict(pair=[a, b], sign=sign, y=1 if sign == 'positive' else 0,
                    directions=[[a, b]], families=['fixture'], first='2019-06-01', last='2019-06-01',
                    evidence_ids=['fixture'], episodes=['fixture'], names=[a, b])
    return [case('H01', 'H02', 'positive'), case('H04', 'H05', 'positive'),
            case('H06', 'H07', 'negative'), case('H08', 'S01', 'negative')]


def sample_rows(heldout_pairs, development_pairs):
    rows = [dict(pair=list(pair), pair_id=wb.pair_id_of(*pair), split='heldout', stratum='fixture')
            for pair in heldout_pairs]
    rows += [dict(pair=list(pair), pair_id=wb.pair_id_of(*pair), split='development', stratum='fixture')
             for pair in development_pairs]
    return rows


def affinity(value, merge_rule):
    return dict(value=value, merge_rule=merge_rule, pass_a=value, pass_b=value)


def label_row(pair, status, a_to_b, b_to_a, split='development'):
    return dict(pair=list(pair), pair_id=wb.pair_id_of(*pair), split=split, label_status=status,
                directions=dict(a_to_b=dict(affinity=a_to_b), b_to_a=dict(affinity=b_to_a)))


def make_labels():
    merged = 'two_blind_model_passes_merged'
    return [
        label_row(('H01', 'H02'), merged, affinity(2, 'exact'), affinity('unassessable', 'both_unassessable')),
        label_row(('H04', 'H05'), merged, affinity(1, 'exact'), affinity(1, 'exact')),
        label_row(('H06', 'H07'), merged, affinity(0, 'exact'), affinity('unassessable', 'both_unassessable')),
        label_row(('H02', 'H09'), merged, affinity(1, 'min_of_adjacent'), affinity(None, None)),
        label_row(('H05', 'H10'), merged, affinity('unassessable', 'both_unassessable'),
                  affinity('unassessable', 'both_unassessable')),
        label_row(('H07', 'H09'), 'no_evidence_deterministic', affinity(None, 'no_evidence'),
                  affinity(None, 'no_evidence')),
    ]


NOMINATE_HEADER = ['congress', 'chamber', 'icpsr', 'bioname', 'bioguide_id', 'nominate_dim1',
                   'nominate_dim2', 'nominate_number_of_votes']


def nominate_rows(congresses=('116', '117')):
    """Per-congress scores for most members, with the gaps the fallback has to cover.

    H11 has no row in either congress and falls back to its static score; H12 has
    neither, so its distances are imputed; H02 carries two 116 rows, as VoteView
    records a party switch inside a congress.
    """
    rows = [['116', 'President', '99912', 'A PRESIDENT', '', '0.4', '0.1', '100']]
    for congress in congresses:
        for index, bioguide in enumerate(HOUSE):
            if bioguide in ('H11', 'H12'):
                continue
            offset = 0.02 if congress == '117' else 0.0
            rows.append([congress, 'House', str(100 + index), bioguide.lower(), bioguide,
                         '%.3f' % (-0.55 + 0.1 * index + offset), '0.0', '500'])
        for index, bioguide in enumerate(SENATE):
            rows.append([congress, 'Senate', str(200 + index), bioguide.lower(), bioguide,
                         '%.3f' % (0.11 * index), '0.0', '400'])
    # The losing half of the party switch: fewer votes, so it must not be the one kept.
    rows.append(['116', 'House', '999', 'h02 second spell', 'H02', '0.999', '0.0', '12'])
    rows.append(['115', 'House', '101', 'out of window', 'H01', '0.9', '0.0', '500'])
    rows.append(['116', 'House', '998', 'no bioguide', '', '0.5', '0.0', '300'])
    rows.append(['117', 'Senate', '997', 'no score', 'S09', '', '0.0', '50'])
    return rows


def write_panel(directory, *, cases=None, sample=None, labels=None, bills=None, members=None,
                nominate=None):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    paths = dict(members_path=directory / 'members.json', bills_path=directory / 'bills.ndjson',
                 cases_path=directory / 'cases.json', sample_path=directory / 'sampled_pairs.ndjson',
                 labels_path=directory / 'labels_v1.ndjson',
                 nominate_path=directory / 'HSall_members.csv')
    lines = [','.join(NOMINATE_HEADER)]
    lines += [','.join(row) for row in (nominate if nominate is not None else nominate_rows())]
    paths['nominate_path'].write_text('\n'.join(lines) + '\n', encoding='utf-8')
    paths['members_path'].write_text(json.dumps(members or make_members()), encoding='utf-8')
    paths['bills_path'].write_text(
        ''.join(json.dumps(b) + '\n' for b in (bills if bills is not None else make_bills())),
        encoding='utf-8')
    paths['cases_path'].write_text(json.dumps(cases if cases is not None else make_cases()), encoding='utf-8')
    rows = sample if sample is not None else sample_rows([('H01', 'H03')], [('H04', 'H05')])
    paths['sample_path'].write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    paths['labels_path'].write_text(
        ''.join(json.dumps(r) + '\n' for r in (labels if labels is not None else make_labels())),
        encoding='utf-8')
    return {k: str(v) for k, v in paths.items()}


def run_build(out_dir, panel, **kwargs):
    options = dict(bootstrap=6, auc_draws=25, congresses=(116, 117), cutoff='2026-09-10',
                   progress=lambda *a, **k: None)
    options.update(kwargs)
    return wb.build(out_dir, **panel, **options)


def read_ndjson(path):
    return [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]


# ------------------------------------------------------------------ the solver

class SolverContracts(unittest.TestCase):
    def test_irls_recovers_known_coefficients(self):
        generator = np.random.default_rng(20260911)
        rows = 40000
        X = np.column_stack([generator.normal(size=rows),
                             generator.binomial(1, 0.5, rows).astype(float),
                             generator.uniform(0, 2, rows)])
        truth = np.array([0.8, -0.5, 0.25])
        intercept = -3.0
        probability = 1 / (1 + np.exp(-(intercept + X @ truth)))
        trials = generator.integers(5, 60, rows).astype(float)
        y = generator.binomial(trials.astype(int), probability).astype(float)
        result = wb.fit_binomial(X, y, trials)
        self.assertTrue(result['converged'])
        self.assertLess(abs(result['intercept'] - intercept), 0.05)
        for estimated, actual in zip(result['coefficients'], truth):
            self.assertLess(abs(estimated - actual), 0.05)

    def test_convergence_is_reported_not_assumed(self):
        generator = np.random.default_rng(3)
        X = generator.normal(size=(500, 2))
        trials = np.full(500, 10.0)
        y = generator.binomial(10, 0.2, 500).astype(float)
        result = wb.fit_binomial(X, y, trials)
        for key in ('converged', 'iterations', 'max_step', 'max_gradient', 'status'):
            self.assertIn(key, result)
        self.assertGreaterEqual(result['iterations'], 1)
        self.assertLess(result['max_gradient'], wb.GRADIENT_TOL)

    def test_a_column_without_variation_is_dropped_not_silently_fitted(self):
        generator = np.random.default_rng(5)
        X = np.column_stack([generator.normal(size=800), np.ones(800)])
        trials = np.full(800, 12.0)
        y = generator.binomial(12, 0.3, 800).astype(float)
        result = wb.fit_binomial(X, y, trials)
        self.assertIsNotNone(result['coefficients'][0])
        self.assertIsNone(result['coefficients'][1])
        self.assertEqual(result['kept_columns'], [0])

    def test_the_expectation_never_exceeds_the_exposure(self):
        generator = np.random.default_rng(9)
        X = generator.normal(size=(2000, 2)) * 8.0
        trials = generator.integers(1, 5, 2000).astype(float)
        y = trials.copy()
        result = wb.fit_binomial(X, y, trials)
        self.assertTrue(bool(np.all(result['fitted'] <= trials + 1e-9)))

    def test_pair_groups_keep_both_directions_of_a_pair_together(self):
        signer = np.array([0, 1, 0, 2])
        sponsor = np.array([1, 0, 2, 0])
        groups = wb.pair_groups(signer, sponsor)
        self.assertEqual(groups.shape, (2, 2))
        recovered = {frozenset(row.tolist()) for row in groups}
        self.assertEqual(recovered, {frozenset({0, 1}), frozenset({2, 3})})


# ---------------------------------------------------------- counting contracts

class CountingContracts(unittest.TestCase):
    def test_cell_counts_reproduce_the_lane_chamber_work_builder(self):
        """The baseline must count with the lane's own definition, not a new one."""
        members = make_members()
        bills = [b for b in make_bills(congresses=(116,)) if b['chamber'] == 'House']
        member_ids = sorted(a for a, p in members.items()
                            if wb.service_overlap(p, W116[0], W116[1], 'House'))
        counts = wb.cell_counts(member_ids, members, bills, 'House')
        index = {a: i for i, a in enumerate(member_ids)}
        assessments = [dict(id='%s->%s' % (a, b), actor=a, target=b, date='2021-01-04')
                       for a, b in (('H01', 'H02'), ('H05', 'H04'), ('H11', 'H06'), ('H02', 'H09'))]
        lane, _ = temporal_features(members, bills, assessments, progress=lambda *a, **k: None)
        for row in assessments:
            reference = lane[row['id']]
            i, j = index[row['actor']], index[row['target']]
            self.assertEqual(int(counts['direct'][i, j]), reference['original_a_to_b'])
            self.assertEqual(int(counts['opportunities'][i, j]), reference['opportunities_a_to_b'])
            self.assertEqual(int(counts['direct'][j, i]), reference['original_b_to_a'])
            self.assertEqual(int(counts['opportunities'][j, i]), reference['opportunities_b_to_a'])

    def test_a_mid_congress_arrival_is_not_charged_for_earlier_bills(self):
        """Exposure is pair-specific: opportunities that never existed are not denominators."""
        members = make_members()
        bills = [b for b in make_bills(congresses=(116,)) if b['chamber'] == 'House']
        member_ids = sorted(a for a, p in members.items()
                            if wb.service_overlap(p, W116[0], W116[1], 'House'))
        counts = wb.cell_counts(member_ids, members, bills, 'House')
        index = {a: i for i, a in enumerate(member_ids)}
        def serving(who, day):
            return any(t['chamber'] == 'House' and t['start'] <= day < t['end']
                       for t in members[who]['terms'])

        def eligible(who):
            return sum(1 for b in bills if serving(who, b['introduced']) and b['sponsor'] != who)

        for who in ('H01', 'H11'):
            self.assertEqual(int(counts['exposures'][index[who]]), eligible(who))
        self.assertGreater(counts['exposures'][index['H11']], 0)
        self.assertLess(counts['exposures'][index['H11']], counts['exposures'][index['H01']])
        self.assertTrue(all(b['introduced'] >= LATE_ARRIVAL for b in bills
                            if 'H11' in b['original']))

    def test_a_sponsor_is_never_eligible_for_its_own_bill(self):
        members = make_members()
        bills = [b for b in make_bills(congresses=(116,)) if b['chamber'] == 'House']
        member_ids = sorted(a for a, p in members.items()
                            if wb.service_overlap(p, W116[0], W116[1], 'House'))
        counts = wb.cell_counts(member_ids, members, bills, 'House')
        self.assertTrue(bool(np.all(np.diag(counts['opportunities']) == 0)))
        self.assertTrue(bool(np.all(np.diag(counts['direct']) == 0)))

    def test_leave_pair_out_propensity_excludes_the_focal_sponsor(self):
        members = make_members()
        member_ids = ['H01', 'H02', 'H03']
        counts = dict(direct=np.array([[0., 3., 1.], [0., 0., 0.], [0., 0., 0.]]),
                      opportunities=np.array([[0., 10., 4.], [0., 0., 0.], [0., 0., 0.]]),
                      signatures=np.array([4., 0., 0.]), exposures=np.array([14., 0., 0.]),
                      sponsor_bills=np.array([0., 10., 4.]), days_cached=1)
        design = wb.cell_design(member_ids, members, counts, 'House', *W116)
        # Signer H01 against sponsor H02: 4 - 3 = 1 signature over 14 - 10 = 4 opportunities.
        self.assertAlmostEqual(design['propensity_rate'][0, 1], 0.25)
        self.assertAlmostEqual(design['columns']['signer_propensity_logit'][0, 1],
                               float(np.log(1.5 / 3.5)))
        # Against sponsor H03: 4 - 1 = 3 signatures over 14 - 4 = 10 opportunities.
        self.assertAlmostEqual(design['propensity_rate'][0, 2], 0.3)
        self.assertAlmostEqual(design['columns']['signer_propensity_logit'][0, 2],
                               float(np.log(3.5 / 7.5)))

    def test_propensity_is_neutral_when_no_other_sponsor_offered_an_opportunity(self):
        members = make_members()
        member_ids = ['H01', 'H02']
        counts = dict(direct=np.array([[0., 2.], [0., 0.]]), opportunities=np.array([[0., 5.], [0., 0.]]),
                      signatures=np.array([2., 0.]), exposures=np.array([5., 0.]),
                      sponsor_bills=np.array([0., 5.]), days_cached=1)
        design = wb.cell_design(member_ids, members, counts, 'House', *W116)
        self.assertEqual(design['columns']['signer_propensity_logit'][0, 1], 0.0)
        self.assertTrue(np.isnan(design['propensity_rate'][0, 1]))

    def test_a_missing_nominate_score_is_imputed_and_flagged(self):
        members = make_members()
        member_ids = ['H01', 'H02', 'H12']
        size = len(member_ids)
        counts = dict(direct=np.zeros((size, size)), opportunities=np.ones((size, size)),
                      signatures=np.zeros(size), exposures=np.ones(size),
                      sponsor_bills=np.ones(size), days_cached=1)
        design = wb.cell_design(member_ids, members, counts, 'House', *W116)
        flags = design['columns']['nominate_distance_imputed']
        self.assertEqual(flags[0, 1], 0.0)
        self.assertEqual(flags[0, 2], 1.0)
        self.assertEqual(design['imputed_pairs'], 4)
        expected = abs(members['H01']['d1'] - members['H02']['d1'])
        self.assertAlmostEqual(design['nominate_fill'], expected)
        self.assertAlmostEqual(design['columns']['nominate_distance'][0, 2], expected)

    def test_per_congress_nominate_is_read_per_congress_and_chamber(self):
        with tempfile.TemporaryDirectory() as directory:
            panel = write_panel(Path(directory) / 'inputs')
            scores, audit = wb.load_nominate(panel['nominate_path'], (116, 117))
            self.assertEqual(audit['congresses'], [116, 117])
            self.assertEqual(audit['blank_bioguide'], 1)
            self.assertEqual(audit['blank_scores'], 1)
            self.assertEqual(audit['duplicate_member_congress_rows'], 1)
            # The President row is out of scope before the bioguide check, by chamber.
            self.assertEqual(audit['rows_in_window'], audit['usable_rows'] + 2)
            self.assertNotIn((115, 'House', 'H01'), scores)
            self.assertAlmostEqual(scores[(116, 'House', 'H01')], -0.55)
            self.assertAlmostEqual(scores[(117, 'House', 'H01')], -0.53)
            # The party-switch spell with fewer recorded votes must not win.
            self.assertAlmostEqual(scores[(116, 'House', 'H02')], -0.45)
            self.assertNotIn((116, 'House', 'H11'), scores)

    def test_the_static_score_is_the_fallback_and_the_gap_is_flagged(self):
        with tempfile.TemporaryDirectory() as directory:
            panel = write_panel(Path(directory) / 'inputs')
            members = make_members()
            scores, _ = wb.load_nominate(panel['nominate_path'], (116, 117))
            resolved = wb.cell_nominate(['H01', 'H11', 'H12'], members, scores, 116, 'House')
            self.assertEqual(resolved['H01']['rank'], 2)
            self.assertAlmostEqual(resolved['H01']['value'], -0.55)
            self.assertEqual(resolved['H11']['rank'], 1)
            self.assertAlmostEqual(resolved['H11']['value'], members['H11']['d1'])
            self.assertEqual(resolved['H12']['rank'], 0)
            self.assertIsNone(resolved['H12']['value'])
            counts = dict(direct=np.zeros((3, 3)), opportunities=np.ones((3, 3)),
                          signatures=np.zeros(3), exposures=np.ones(3),
                          sponsor_bills=np.ones(3), days_cached=1)
            design = wb.cell_design(['H01', 'H11', 'H12'], members, counts, 'House', *W116,
                                    nominate=resolved)
            self.assertEqual(design['nominate_members'],
                             {'per_congress': 1, 'static_hs119_fallback': 1,
                              'missing_imputed_at_cell_mean': 1})
            self.assertEqual(design['nominate_pairs']['per_congress'], 0)
            self.assertEqual(design['nominate_pairs']['static_hs119_fallback'], 2)
            self.assertEqual(design['nominate_pairs']['missing_imputed_at_cell_mean'], 4)
            self.assertAlmostEqual(design['columns']['nominate_distance'][0, 1],
                                   abs(-0.55 - members['H11']['d1']))

    def test_congress_window_clamps_at_the_read_cutoff(self):
        self.assertEqual(wb.congress_window(116, '2026-09-10'), ('2019-01-03', '2021-01-03'))
        self.assertEqual(wb.congress_window(119, '2026-09-10'), ('2025-01-03', '2026-09-11'))
        self.assertEqual(wb.congress_window(119, '2025-06-30'), ('2025-01-03', '2025-07-01'))


# ------------------------------------------------------ residual arithmetic

class BillPanelContracts(unittest.TestCase):
    def test_the_congress_range_flag_parses_every_accepted_form(self):
        self.assertEqual(wb.parse_congress_range('116-119'), (116, 117, 118, 119))
        self.assertEqual(wb.parse_congress_range('115-119'), (115, 116, 117, 118, 119))
        self.assertEqual(wb.parse_congress_range('118'), (118,))
        self.assertEqual(wb.parse_congress_range('117,115'), (115, 117))
        self.assertEqual(wb.parse_congress_range((119, 118)), (118, 119))
        with self.assertRaises(ValueError):
            wb.parse_congress_range('119-116')

    def test_the_reader_applies_no_congress_filter(self):
        """history_work.read_history() drops anything outside 116-119; this reader must not."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bills.ndjson'
            rows = make_bills(congresses=(115, 116))
            path.write_text(''.join(json.dumps(b) + '\n' for b in rows), encoding='utf-8')
            read, census = wb.read_bills(path)
            self.assertEqual(len(read), len(rows))
            self.assertEqual(sorted(census), [115, 116])
            self.assertEqual(census[115], sum(1 for b in rows if b['congress'] == 115))
            # The filtering loader is never even imported, so it cannot be reached by accident.
            self.assertFalse(hasattr(wb, 'read_history'))

    def test_a_missing_or_empty_panel_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                wb.read_bills(Path(directory) / 'absent.ndjson')
            empty = Path(directory) / 'empty.ndjson'
            empty.write_text('', encoding='utf-8')
            with self.assertRaises(ValueError):
                wb.read_bills(empty)

    def test_a_requested_congress_with_no_bills_stops_the_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            with self.assertRaises(ValueError) as caught:
                run_build(root / 'out', panel, congresses='115-117')
            self.assertIn('115', str(caught.exception))

    def test_a_wider_range_reaches_the_earlier_congress(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs', members=make_members(include_115=True),
                                bills=make_bills(congresses=(115, 116, 117)),
                                nominate=nominate_rows(congresses=('115', '116', '117')))
            narrow = run_build(root / 'narrow', panel, congresses='116-117')
            wide = run_build(root / 'wide', panel, congresses='115-117')
            self.assertEqual(narrow['coverage']['congresses'], [116, 117])
            self.assertEqual(wide['coverage']['congresses'], [115, 116, 117])
            self.assertEqual(wide['coverage']['congress_range'], '115-117')
            self.assertGreater(wide['totals']['measured'], narrow['totals']['measured'])
            rows = read_ndjson(root / 'wide' / 'pair_work_residuals.ndjson')
            self.assertTrue(any(row['congress'] == 115 for row in rows))
            self.assertTrue(any(row['window'].startswith(W115[0]) for row in rows))
            self.assertFalse(any(row['congress'] == 115
                                 for row in read_ndjson(root / 'narrow' / 'pair_work_residuals.ndjson')))
            # The 115th must not quietly change the shared congresses.
            for name in ('116', '117'):
                self.assertIn(name, json.dumps(wide['coverage']['bills_by_congress_in_source']))


class ResidualContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        cls.panel = write_panel(root / 'inputs')
        cls.out = root / 'out'
        cls.receipt = run_build(cls.out, cls.panel)
        cls.rows = read_ndjson(cls.out / 'pair_work_residuals.ndjson')
        cls.pooled = read_ndjson(cls.out / 'pair_work_pooled.ndjson')
        cls.fits = json.loads((cls.out / 'baseline_fits.json').read_text(encoding='utf-8'))
        cls.validation = json.loads((cls.out / 'validation.json').read_text(encoding='utf-8'))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def test_residual_shrinkage_and_pearson_arithmetic(self):
        self.assertTrue(self.rows)
        for row in self.rows:
            n, exposure, expected = (row['original_cosponsorships'], row['eligible_opportunities'],
                                     row['expected'])
            self.assertGreater(exposure, 0)
            self.assertLessEqual(expected, exposure + 1e-9)
            self.assertAlmostEqual(row['residual'], n - expected, places=5)
            self.assertAlmostEqual(row['shrunken_rate_ratio'], (n + 0.5) / (expected + 0.5), places=5)
            self.assertAlmostEqual(row['variance'], expected * (1 - expected / exposure), places=5)
            if row['variance'] > 0:
                self.assertAlmostEqual(row['pearson_residual'],
                                       (n - expected) / (row['variance'] ** 0.5), places=4)
            self.assertEqual(row['shrinkage'], 0.5)

    def test_every_row_records_where_its_ideology_score_came_from(self):
        sources = {row['nominate_source'] for row in self.rows}
        self.assertEqual(sources, set(wb.NOMINATE_SOURCES.values()))
        for row in self.rows:
            if row['nominate_source'] == 'missing_imputed_at_cell_mean':
                self.assertTrue(row['nominate_distance_imputed'])
            else:
                self.assertFalse(row['nominate_distance_imputed'])
        cells = [c for c in self.fits['cells'] if c.get('fit_status') == 'fitted']
        for cell in cells:
            self.assertEqual(sum(cell['nominate_pairs'].values()), cell['directed_pairs_in_cell'])
            self.assertEqual(sum(cell['nominate_members'].values()), cell['serving_members'])
        self.assertEqual(self.fits['nominate']['duplicate_member_congress_rows'], 1)
        self.assertIn('nominate_per_congress', self.fits['totals'])

    def test_every_row_carries_its_window_and_its_denominator(self):
        for row in self.rows:
            self.assertRegex(row['window'], r'^\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}$')
            self.assertIn('eligible_opportunities', row)
            self.assertIn('sponsor_bills_in_window', row)
            self.assertEqual(row['state'], 'measured')
        for row in self.pooled:
            self.assertIn('eligible_opportunities', row)
            self.assertTrue(row['congresses'])
            for slot in row['by_congress'].values():
                self.assertRegex(slot['window'], r'^\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2}$')

    def test_pooled_rows_sum_both_directions_and_every_congress(self):
        totals = {}
        for row in self.rows:
            entry = totals.setdefault(row['pair_id'], dict(n=0, N=0, expected=0.0, congresses=set()))
            entry['n'] += row['original_cosponsorships']
            entry['N'] += row['eligible_opportunities']
            entry['expected'] += row['expected']
            entry['congresses'].add(row['congress'])
        self.assertEqual(len(totals), len(self.pooled))
        for row in self.pooled:
            entry = totals[row['pair_id']]
            self.assertEqual(row['original_cosponsorships'], entry['n'])
            self.assertEqual(row['eligible_opportunities'], entry['N'])
            self.assertAlmostEqual(row['expected'], entry['expected'], places=4)
            self.assertEqual(row['congresses'], sorted(entry['congresses']))
            self.assertAlmostEqual(row['shrunken_rate_ratio'],
                                   (entry['n'] + 0.5) / (entry['expected'] + 0.5), places=4)

    def test_a_sponsor_with_no_bills_is_no_eligible_bills_not_a_zero_score(self):
        self.assertFalse(any(row['sponsor'] == 'H03' for row in self.rows))
        self.assertGreater(self.receipt['totals']['no_eligible_bills'], 0)
        self.assertEqual(self.receipt['totals']['directed_pairs'],
                         self.receipt['totals']['measured'] + self.receipt['totals']['no_eligible_bills'])
        self.assertIn('no_eligible_bills', self.fits['state_vocabulary'])

    def test_cross_chamber_pairs_are_absent_by_construction(self):
        for row in self.rows:
            self.assertEqual(row['signer'][0], row['sponsor'][0])
        self.assertFalse(any(set(row['members']) == {'H08', 'S01'} for row in self.pooled))
        state = [r['state'] for r in self.validation['sign_benchmark']['rows']
                 if r['pair_id'] == wb.pair_id_of('H08', 'S01')]
        self.assertEqual(state, ['cross_chamber_not_measured'])

    def test_the_fit_record_reports_convergence_and_the_omitted_committee_term(self):
        fitted = [c for c in self.fits['cells'] if c.get('fit_status') == 'fitted']
        self.assertTrue(fitted)
        for cell in fitted:
            self.assertIn('converged', cell)
            self.assertIn('iterations', cell)
            self.assertEqual(cell['bootstrap']['draws_requested'], 6)
            self.assertEqual([c['name'] for c in cell['columns']], ['intercept'] + wb.COVARIATES)
        self.assertEqual(self.fits['shared_committee']['status'], 'omitted')
        self.assertTrue(self.fits['shared_committee']['paths_searched'])
        self.assertNotIn('shared_committee', self.fits['covariates'])


# ---------------------------------------------------------- held-out discipline

class HeldOutContracts(unittest.TestCase):
    def test_assert_no_heldout_raises_instead_of_filtering(self):
        with self.assertRaises(ValueError):
            wb.assert_no_heldout(['A__B', 'C__D'], frozenset({'C__D'}), 'fixture')
        self.assertEqual(wb.assert_no_heldout(['A__B'], frozenset({'C__D'}), 'fixture'), 1)

    def test_the_deny_list_reads_nothing_but_the_pair_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'sampled_pairs.ndjson'
            path.write_text(''.join(json.dumps(r) + '\n' for r in sample_rows(
                [('H01', 'H03'), ('H02', 'H06')], [('H04', 'H05')])), encoding='utf-8')
            denied, development = wb.load_deny_list(path)
            self.assertEqual(denied, {'H01__H03', 'H02__H06'})
            self.assertEqual(development, 1)

    def test_held_out_pairs_are_scored_in_the_pair_table_but_never_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            receipt = run_build(root / 'out', panel)
            pooled = read_ndjson(root / 'out' / 'pair_work_pooled.ndjson')
            sealed = wb.pair_id_of('H01', 'H03')
            self.assertIn(sealed, {row['pair_id'] for row in pooled})
            self.assertEqual(receipt['held_out_dyads_denied'], 1)
            validation = receipt['validation']
            for table in (validation['sign_benchmark']['rows'],
                          validation['development_graded']['rows']):
                self.assertNotIn(sealed, {row['pair_id'] for row in table})

    def test_a_held_out_dyad_in_a_validation_input_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = make_cases()
            cases[0]['pair'] = ['H01', 'H03']
            panel = write_panel(root / 'inputs', cases=cases)
            with self.assertRaises(ValueError):
                run_build(root / 'out', panel)

    def test_a_held_out_dyad_in_the_graded_rows_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            labels = make_labels()
            labels[0] = label_row(('H01', 'H03'), 'two_blind_model_passes_merged',
                                  affinity(1, 'exact'), affinity(1, 'exact'))
            panel = write_panel(root / 'inputs', labels=labels)
            with self.assertRaises(ValueError):
                run_build(root / 'out', panel)

    def test_the_report_names_no_held_out_dyad(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            out = root / 'out'
            receipt = run_build(out, panel)
            receipt['cells'] = json.loads((out / 'baseline_fits.json').read_text(encoding='utf-8'))['cells']
            receipt['glassbox_run_id'] = 'fixture-run'
            receipt['runtime_seconds'] = 0.0
            receipt['artefacts'] = [dict(name=name, bytes=1, sha256='0' * 64) for name in wb.ARTEFACTS]
            text = wb.report_text(receipt)
            self.assertTrue(text.startswith('# Expected-rate baseline'))
            self.assertIn('STATUS: EXPLORATORY', text.splitlines()[2])
            self.assertNotIn(wb.pair_id_of('H01', 'H03'), text)
            self.assertIn('Design choices pending Paul', text)
            self.assertIn('Per-congress NOMINATE, with a static fallback', text)
            self.assertIn('shared_committee omitted', text)
            # Every reported count must be over the denominator it names.
            totals = receipt['totals']
            self.assertEqual(totals['directed_pairs'],
                             totals['measured'] + totals['no_eligible_bills'])
            self.assertEqual(sum(v for k, v in totals.items() if k.startswith('nominate_')),
                             totals['directed_pairs'])
            self.assertIn('of the %s directed pairs in the cells' % f"{totals['directed_pairs']:,}", text)
            self.assertIn('%s carry a per-congress NOMINATE' % f"{totals['nominate_per_congress']:,}", text)


# ------------------------------------------------------------------ diagnostics

class DiagnosticContracts(unittest.TestCase):
    def test_auc_counts_every_comparison_and_halves_ties(self):
        # 3>1, 3>2, 2>1 are three wins; 2 against 2 is a tie worth a half.
        value, comparisons, wins = wb.auc_from_scores([3.0, 2.0], [1.0, 2.0])
        self.assertEqual(comparisons, 4)
        self.assertEqual(wins, 3.5)
        self.assertAlmostEqual(value, 0.875)
        self.assertEqual(wb.auc_from_scores([], [1.0])[1], 0)

    def test_the_auc_interval_is_bounded_and_deterministic(self):
        positive = [3.0, 2.5, 2.0, 1.5]
        negative = [1.0, 0.5, 2.2]
        first = wb.auc_bootstrap_interval(positive, negative, 200, 5)
        second = wb.auc_bootstrap_interval(positive, negative, 200, 5)
        self.assertEqual(first, second)
        self.assertLessEqual(first[0], first[1])
        self.assertGreaterEqual(first[0], 0.0)
        self.assertLessEqual(first[1], 1.0)

    def test_spearman_matches_a_hand_computation(self):
        self.assertAlmostEqual(wb.spearman([1, 2, 3, 4], [1, 2, 3, 4]), 1.0)
        self.assertAlmostEqual(wb.spearman([1, 2, 3, 4], [4, 3, 2, 1]), -1.0)
        self.assertAlmostEqual(wb.spearman([1, 2, 3, 4], [1, 3, 2, 4]), 0.8)
        self.assertIsNone(wb.spearman([1, 1, 1], [1, 2, 3]))
        self.assertIsNone(wb.spearman([1, 2], [2, 1]))

    def test_average_ranks_share_a_tie(self):
        self.assertEqual(list(wb.average_ranks([5.0, 5.0, 9.0])), [1.5, 1.5, 3.0])

    def test_both_unmeasurable_denominators_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            receipt = run_build(root / 'out', panel)
            benchmark = receipt['validation']['sign_benchmark']
            self.assertEqual(benchmark['dyads'], benchmark['measurable'] + benchmark['unmeasurable'])
            for block in benchmark['scores'].values():
                self.assertEqual(block['mean_imputed']['dyads'], benchmark['dyads'])
                self.assertEqual(block['dropped']['dyads'], benchmark['measurable'])
                for values in block.values():
                    self.assertEqual(values['comparisons'], values['positive'] * values['negative'])

    def test_the_graded_subset_takes_only_rows_both_passes_agreed_on(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            receipt = run_build(root / 'out', panel)
            graded = receipt['validation']['development_graded']
            self.assertEqual(graded['two_pass_merged_rows'], 5)
            self.assertEqual(graded['with_agreed_assessable_affinity'], 3)
            degrees = {row['pair_id']: row['degree'] for row in graded['rows']}
            self.assertEqual(degrees[wb.pair_id_of('H01', 'H02')], 2)
            self.assertEqual(degrees[wb.pair_id_of('H06', 'H07')], 0)
            self.assertIsNone(degrees[wb.pair_id_of('H02', 'H09')])
            self.assertIsNone(degrees[wb.pair_id_of('H05', 'H10')])
            self.assertNotIn(wb.pair_id_of('H07', 'H09'), degrees)


# ----------------------------------------------------------------- determinism

class DeterminismContracts(unittest.TestCase):
    def test_two_runs_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            first, second = root / 'first', root / 'second'
            run_build(first, panel)
            run_build(second, panel)
            for name in wb.ARTEFACTS:
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes(),
                                 '%s differed between two runs' % name)

    def test_the_receipt_pins_every_input_by_sha256(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            panel = write_panel(root / 'inputs')
            receipt = run_build(root / 'out', panel)
            self.assertEqual(sorted(receipt['inputs']),
                             ['HSall_members.csv', 'bills.ndjson', 'cases.json', 'labels_v1.ndjson',
                              'members.json', 'sampled_pairs.ndjson'])
            for value in receipt['inputs'].values():
                self.assertRegex(value['sha256'], r'^[0-9a-f]{64}$')
            self.assertEqual(receipt['status'], 'EXPLORATORY')
            self.assertFalse(receipt['held_out_split_touched'])
            self.assertTrue(receipt['pending_decisions'])
            # Wall time lives in the receipt, never in a byte-compared data artefact.
            self.assertEqual(sorted(receipt['cell_wall_seconds']),
                             ['116|House', '116|Senate', '117|House', '117|Senate'])
            fits = json.loads((root / 'out' / 'baseline_fits.json').read_text(encoding='utf-8'))
            self.assertNotIn('wall_seconds', json.dumps(fits))


if __name__ == '__main__':
    unittest.main()
