"""Contracts for universe pair scoring (member-relationships review items P1-5, 6, 8, 11).

Every test here builds its own synthetic panel in a temporary directory, or drives a
pure function directly. None of them reads a real lane artefact except the four small
frozen files the module needs to know the held-out seal is wired to the real deny
list, and none of them reads a held-out label of any kind.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

from fec.research.member_personal_relationships import pair_scoring as ps
from fec.research.member_personal_relationships.chamber_work import temporal_features


# ------------------------------------------------------------------- fixtures

W115 = ('2017-01-03', '2019-01-03')
W116 = ('2019-01-03', '2021-01-03')
W117 = ('2021-01-03', '2023-01-03')
REFERENCE = '2023-01-02'
HOUSE = ['H%02d' % i for i in range(1, 7)]
SENATE = ['S%02d' % i for i in range(1, 4)]


def person(bioguide, chamber, state, party, d1, include_115=False, late=None):
    start = late or W116[0]
    terms = [dict(start=start, end=W116[1], chamber=chamber, state=state, party=party),
             dict(start=W117[0], end=W117[1], chamber=chamber, state=state, party=party)]
    if include_115:
        terms.insert(0, dict(start=W115[0], end=W115[1], chamber=chamber, state=state,
                             party=party))
    return dict(bioguide=bioguide, name='Member ' + bioguide, terms=terms, chamber=chamber,
                state=state, party=party, d1=d1, d2=0.1, leader=False, leadership_role=None)


def make_members(orphan=False):
    """Six House members, three Senators. H06 arrives late; S03 has no ideology score."""
    members = {}
    for i, who in enumerate(HOUSE):
        members[who] = person(who, 'House', ['CA', 'TX', 'NY'][i % 3],
                              ['Democrat', 'Republican'][i % 2], round(-0.5 + 0.2 * i, 3),
                              include_115=(i < 3), late=('2019-09-01' if who == 'H06' else None))
    for i, who in enumerate(SENATE):
        members[who] = person(who, 'Senate', ['CA', 'TX', 'NY'][i % 3],
                              ['Democrat', 'Republican'][i % 2], round(0.1 * i, 3),
                              include_115=(i == 0))
    if orphan:
        members['S03']['d1'] = None
        members['S03']['d2'] = None
    return members


def bill(key, congress, chamber, sponsor, introduced, originals):
    end = {115: W115[1], 116: W116[1], 117: W117[1]}[congress]
    joins = {a: introduced for a in originals}
    return dict(key=key, congress=congress, chamber=chamber, sponsor=sponsor,
                introduced=introduced, end=end, title=key, area='Health' if congress % 2 else 'Tax',
                joins=joins, withdrawals={}, original=sorted(originals), size=len(joins) + 1,
                updated=None, url='https://example.invalid/' + key)


def directed_residual_row(signer, sponsor, n, big_n, expected, congress=116, state='measured'):
    """One row of the producer's directed pair_work_residuals.ndjson shape.

    ``residual`` and ``shrunken_rate_ratio`` are filled in with per-row values a real
    producer would carry, exactly so a test that misused them instead of the pooled
    figure would be caught: ``load_residuals_directed`` must recompute, never read them.
    """
    return dict(signer=signer, sponsor=sponsor, congress=congress,
               original_cosponsorships=n, eligible_opportunities=big_n, expected=expected,
               residual=round(n - expected, 6), pearson_residual=0.0,
               shrunken_rate_ratio=round((n + 0.5) / (expected + 0.5), 6), state=state)


def make_bills():
    """A small panel: the 115th exists so --congress-range has something to include."""
    rows = []
    for step, day in enumerate(('2017-03-01', '2017-06-01')):
        rows.append(bill('h115-%d' % step, 115, 'House', HOUSE[step], day,
                         [HOUSE[(step + 1) % 3], HOUSE[(step + 2) % 3]]))
    for step, day in enumerate(('2019-03-01', '2019-06-01', '2019-09-15', '2020-02-01')):
        rows.append(bill('h116-%d' % step, 116, 'House', HOUSE[step % 5], day,
                         [HOUSE[(step + 1) % 5], HOUSE[(step + 2) % 5], HOUSE[5]]))
    for step, day in enumerate(('2021-03-01', '2021-09-01', '2022-05-01')):
        rows.append(bill('h117-%d' % step, 117, 'House', HOUSE[step % 6], day,
                         [HOUSE[(step + 3) % 6], HOUSE[(step + 4) % 6]]))
    for step, day in enumerate(('2019-04-01', '2021-04-01')):
        rows.append(bill('s%d-%d' % (116 + step, step), 116 + step, 'Senate', SENATE[step], day,
                         [SENATE[(step + 1) % 3]]))
    return rows


def annotation(index, actor, target, date, chamber, affinity, friction, family):
    return dict(id='v6:test-%d' % index, actor=actor, target=target, pair=[actor, target],
                date=date, chamber=chamber, affinity=affinity, friction=friction,
                families=[family], names=['Member ' + actor, 'Member ' + target],
                episode_id=family, evidence_ids=[family + '-0'], neutral_evidence=False,
                affinity_range=None, friction_range=None, display='graded_relationship',
                coverage_tiers=['high', 'high'], venue='CREC')


def make_annotations():
    """Twelve dated records over eight dyads, graded across the whole 0..4 range."""
    plan = [(HOUSE[0], HOUSE[1], 'House', 3, 0), (HOUSE[0], HOUSE[2], 'House', 2, 1),
            (HOUSE[1], HOUSE[2], 'House', 4, 0), (HOUSE[2], HOUSE[3], 'House', 1, 2),
            (HOUSE[3], HOUSE[4], 'House', 0, 3), (HOUSE[4], HOUSE[5], 'House', 2, 1),
            (SENATE[0], SENATE[1], 'Senate', 3, 0), (SENATE[1], SENATE[2], 'Senate', 1, 4),
            (HOUSE[0], SENATE[0], 'cross_chamber', 2, 2), (HOUSE[1], HOUSE[3], 'House', 3, 1),
            (HOUSE[2], HOUSE[4], 'House', 0, 2), (HOUSE[0], HOUSE[3], 'House', 4, 0)]
    return [annotation(i, a, b, '2022-06-0%d' % (1 + i % 9), chamber, affinity, friction,
                       'family-%d' % i)
            for i, (a, b, chamber, affinity, friction) in enumerate(plan)]


def make_features(members, bills, annotations):
    """The v6 feature rows, built by the lane's own dated work builder."""
    rows, _ = temporal_features(members, bills, annotations, progress=lambda *a, **k: None)
    out = {}
    for record in annotations:
        feature = dict(rows[record['id']])
        a, b = record['actor'], record['target']
        ta = ps.term_on(members[a], record['date'])
        tb = ps.term_on(members[b], record['date'])
        feature['id'] = record['id']
        feature['same_party'] = float(ta['party'] == tb['party'])
        feature['same_state'] = float(ta['state'] == tb['state'])
        for role, who in (('actor', a), ('target', b)):
            feature[role + '_dw1'] = members[who].get('d1')
            feature[role + '_dw2'] = members[who].get('d2')
            feature[role + '_log_interview_words'] = float(np.log1p(1000 + 7 * len(who)))
        d1a, d1b = members[a].get('d1'), members[b].get('d1')
        feature['dw1_distance'] = (abs(d1a - d1b) if d1a is not None and d1b is not None else None)
        out[record['id']] = feature
    return out


def expression_rows(members, available_pairs):
    """One pooled row plus three venue rows for each directed pair given evidence."""
    rows = []
    for (actor, target), (warm, hostile, n) in sorted(available_pairs.items()):
        status = 'available' if n else 'insufficient_systematic_exposure'
        for source in ('CHRG', 'CREC', 'INTERVIEW', 'pooled'):
            rows.append(dict(actor=actor, target=target, actor_name=actor, target_name=target,
                             source=source, row_kind='pooled' if source == 'pooled'
                             else 'venue_matched', n=n, warm=1, hostile=0, personal=0,
                             status=status, speaker_total_turns=10 * n,
                             speaker_distinct_targets=3, speaker_target_mention_turns=n,
                             warm_contrast=dict(contrast=warm), hostile_contrast=dict(
                                 contrast=hostile)))
    return rows


def encounter_rows(available_pairs):
    out = []
    for (actor, target), (_, _, n) in sorted(available_pairs.items()):
        for venue in ('CREC', 'CHRG'):
            out.append(dict(actor=actor, target=target, source=venue, venue=venue,
                            mention_turns=n if venue == 'CREC' else 0))
    return out


def label_row(pair_id, pair, cells, status='two_blind_model_passes_merged'):
    def cell(value, rule):
        return dict(value=value, merge_rule=rule, adjudication_needed=False,
                    adjudication_reason=None)
    directions = {}
    for direction in ('a_to_b', 'b_to_a'):
        directions[direction] = {axis: cell(*cells[direction][axis]) for axis in ps.AXES}
    return dict(pair_id=pair_id, pair=list(pair), names=['Member ' + p for p in pair],
                label_status=status, graded_via='test', split='development',
                directions=directions)


def write_ndjson(path, rows):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('w', encoding='utf-8', newline='\n') as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding='utf-8')


def nominate_csv(path, rows):
    header = ('congress,chamber,icpsr,state_icpsr,district_code,state_abbrev,party_code,occupancy,'
              'last_means,bioname,bioguide_id,born,died,nominate_dim1,nominate_dim2,'
              'nominate_log_likelihood,nominate_geo_mean_probability,nominate_number_of_votes,'
              'nominate_number_of_errors,conditional,nokken_poole_dim1,nokken_poole_dim2')
    lines = [header]
    for congress, chamber, bioguide, dim1, dim2, votes in rows:
        lines.append('%d,%s,1,1,1,CA,100,0,,Name,%s,1950,,%s,%s,,,%d,,,,'
                     % (congress, chamber, bioguide, dim1, dim2, votes))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text('\n'.join(lines) + '\n', encoding='utf-8')


class Lane:
    """A whole synthetic lane on disk, with pair_scoring pointed at it."""

    def __init__(self, root, orphan=False, heldout=('H05__S02',), speech=None, labels=None,
                 with_115=True):
        self.root = Path(root)
        self.members = make_members(orphan=orphan)
        self.bills = make_bills() if with_115 else [b for b in make_bills()
                                                    if b['congress'] != 115]
        self.annotations = make_annotations()
        self.features = make_features(self.members, [b for b in self.bills
                                                     if b['congress'] != 115], self.annotations)
        self.speech = speech if speech is not None else {
            (HOUSE[0], HOUSE[1]): (0.8, -0.2, 4), (HOUSE[1], HOUSE[0]): (0.5, -0.1, 3),
            (HOUSE[0], HOUSE[2]): (0.3, 0.1, 2), (HOUSE[2], HOUSE[0]): (0.2, 0.4, 2),
            (HOUSE[1], HOUSE[2]): (0.9, -0.3, 5), (HOUSE[2], HOUSE[1]): (0.7, -0.2, 4),
            (HOUSE[2], HOUSE[3]): (0.1, 0.6, 3), (HOUSE[3], HOUSE[2]): (0.0, 0.5, 3),
            (HOUSE[3], HOUSE[4]): (-0.4, 0.9, 4), (HOUSE[4], HOUSE[3]): (-0.3, 0.8, 3),
            (HOUSE[4], HOUSE[5]): (0.4, 0.0, 2), (HOUSE[5], HOUSE[4]): (0.3, 0.1, 2),
            (SENATE[0], SENATE[1]): (0.6, -0.1, 3), (SENATE[1], SENATE[0]): (0.5, 0.0, 3),
            (SENATE[1], SENATE[2]): (-0.2, 0.7, 3), (SENATE[2], SENATE[1]): (-0.1, 0.6, 2),
            (HOUSE[0], SENATE[0]): (0.2, 0.2, 2), (SENATE[0], HOUSE[0]): (0.1, 0.3, 2),
            (HOUSE[1], HOUSE[3]): (0.5, 0.2, 3), (HOUSE[3], HOUSE[1]): (0.4, 0.3, 2),
            (HOUSE[2], HOUSE[4]): (-0.1, 0.4, 2), (HOUSE[4], HOUSE[2]): (0.0, 0.3, 2),
            (HOUSE[0], HOUSE[3]): (0.9, -0.4, 5), (HOUSE[3], HOUSE[0]): (0.8, -0.3, 4),
            (HOUSE[5], HOUSE[0]): (0.1, 0.1, 0)}
        self.heldout = list(heldout)
        self.labels = labels if labels is not None else self.default_labels()
        self.write()

    def default_labels(self):
        return [
            label_row('H01__H02', ('H01', 'H02'),
                      dict(a_to_b=dict(affinity=(2, 'exact'), friction=(0, 'exact')),
                           b_to_a=dict(affinity=(2, 'exact'), friction=(0, 'exact')))),
            label_row('H02__H03', ('H02', 'H03'),
                      dict(a_to_b=dict(affinity=(1, 'exact'), friction=(1, 'min_of_adjacent')),
                           b_to_a=dict(affinity=(0, 'exact'), friction=(0, 'exact')))),
            label_row('H03__H04', ('H03', 'H04'),
                      dict(a_to_b=dict(affinity=('unassessable', 'both_unassessable'),
                                       friction=('unassessable', 'both_unassessable')),
                           b_to_a=dict(affinity=('unassessable', 'both_unassessable'),
                                       friction=('unassessable', 'both_unassessable'))),
                      status='no_evidence_deterministic'),
        ]

    def write(self):
        write_json(self.root / 'outputs/member_personal_relationships/20260910_full_history/'
                              'members.json', self.members)
        write_ndjson(self.root / 'outputs/member_personal_relationships/20260910_full_history/'
                                'bills.ndjson', self.bills)
        write_json(self.root / 'outputs/member_personal_relationships/20260910_frozen_v5/'
                              'member_assignment.json',
                   {who: dict(coverage_tier='high', interview_words=1000 + 7 * len(who),
                              split='development') for who in self.members})
        sample = []
        for pair_id in self.heldout:
            a, b = pair_id.split('__')
            sample.append(dict(pair_id=pair_id, pair=[a, b], split='heldout', affinity=None,
                               antagonism=None, names=['Member ' + a, 'Member ' + b]))
        sample.append(dict(pair_id='H01__H02', pair=['H01', 'H02'], split='development',
                           affinity=None, antagonism=None, names=['Member H01', 'Member H02']))
        write_ndjson(self.root / 'outputs/member_personal_relationships/20260910_frozen_v5/'
                                'sampled_pairs.ndjson', sample)
        write_ndjson(self.root / 'outputs/member_personal_relationships/'
                                '20260910_chamber_degrees_v6/annotations.ndjson', self.annotations)
        write_json(self.root / 'outputs/member_personal_relationships/'
                              '20260910_chamber_degrees_v6/features.json', self.features)
        regrade = []
        for index, record in enumerate(self.annotations):
            regrade.append(dict(id=record['id'],
                                affinity=str(record['affinity']) if index % 3 else 'unassessable',
                                friction=str(record['friction']) if index % 2 else 'unassessable',
                                affinity_range=None, friction_range=None, rationale='test',
                                cited_evidence_ids=[], closeness_trust_evidence=[],
                                neutral_evidence=False, ritual_courtesy_only=False))
        write_ndjson(self.root / 'outputs/member_personal_relationships/20260911_v6_regrade/'
                                'pass_A.ndjson', regrade)
        second = [dict(row, affinity=row['affinity'] if index % 2 else 'unassessable')
                  for index, row in enumerate(regrade)]
        write_ndjson(self.root / 'outputs/member_personal_relationships/20260911_v6_regrade/'
                                'pass_B.ndjson', second)
        write_json(self.root / 'outputs/member_personal_relationships/20260910_regression/'
                              'cases.json', [])
        write_ndjson(self.root / 'outputs/member_personal_relationships/'
                                '20260910_probability_sample_labels/labels_v1.ndjson', self.labels)
        write_ndjson(self.root / 'outputs/member_personal_relationships/'
                                '20260910_expression_contrasts/expression_contrasts.ndjson',
                     expression_rows(self.members, self.speech))
        write_ndjson(self.root / 'outputs/member_personal_relationships/'
                                '20260910_systematic_encounters/encounter_counts.ndjson',
                     encounter_rows(self.speech))
        nominate_csv(self.root / 'votes/HSall_members.csv',
                     [(116, 'House', who, 0.9, 0.2, 500) for who in HOUSE[:4]]
                     + [(117, 'House', who, -0.9, -0.2, 500) for who in HOUSE[:4]]
                     + [(117, 'Senate', SENATE[0], 0.4, 0.1, 400)])

    def residual_file(self, missing=()):
        path = self.root / 'work_residuals.ndjson'
        ids = sorted(self.members)
        rows = []
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                pair_id = '%s__%s' % (a, b)
                if pair_id in set(missing):
                    continue
                rows.append(dict(pair_id=pair_id, members=[a, b],
                                 original_cosponsorships=(i % 3),
                                 eligible_opportunities=10 + i, expected=1.5,
                                 residual=round(-0.5 + 0.1 * i, 3),
                                 shrunken_rate_ratio=round(0.5 + 0.05 * i, 3), state='measured'))
        write_ndjson(path, rows)
        return path

    def residual_file_directed(self, rows):
        """The producer's directed, per-(signer, sponsor, congress) shape. Callers build
        their own rows so each test controls exactly which directions are covered."""
        path = self.root / 'work_residuals_directed.ndjson'
        write_ndjson(path, rows)
        return path

    def full_directed_rows(self, overrides=None, exclude=()):
        """Directed rows covering both directions of every member pair, the same full
        coverage `residual_file` gives the undirected flag. A build fits its work-channel
        specs on the 12-record annotated panel, so leaving most of that panel's dyads
        without any directed row starves the fit rather than exercising this option; this
        is the fixture a test reaches for once it needs `estimate...prediction_state`
        rather than only the pooling or the receipt. `overrides` replaces one (signer,
        sponsor) direction's (n, N, expected); `exclude` drops a direction's row entirely.
        """
        overrides = overrides or {}
        exclude = set(exclude)
        ids = sorted(self.members)
        rows = []
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                for step, (signer, sponsor) in enumerate(((a, b), (b, a))):
                    if (signer, sponsor) in exclude:
                        continue
                    n, big_n, expected = overrides.get((signer, sponsor),
                                                        ((i + step) % 3, 10 + i, 1.5))
                    rows.append(directed_residual_row(signer, sponsor, n=n, big_n=big_n,
                                                       expected=expected))
        return rows


class LaneCase(unittest.TestCase):
    """Base class: redirect every module path at a synthetic lane, and clean up."""

    orphan = False
    heldout = ('H05__S02',)
    with_115 = True

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix='pair-scoring-')
        cls.saved = {name: getattr(ps, name) for name in
                     ('ROOT', 'OUTPUTS', 'HISTORY', 'FROZEN', 'V6', 'REGRADE', 'CONTRASTS',
                      'CENSUS', 'SAMPLE_LABELS', 'REGRESSION', 'BENCH', 'OUT')}
        root = Path(cls.tmp)
        cls.lane = Lane(root, orphan=cls.orphan, heldout=cls.heldout, with_115=cls.with_115)
        outputs = root / 'outputs/member_personal_relationships'
        ps.ROOT = root
        ps.OUTPUTS = outputs
        ps.HISTORY = outputs / '20260910_full_history'
        ps.FROZEN = outputs / '20260910_frozen_v5'
        ps.V6 = outputs / '20260910_chamber_degrees_v6'
        ps.REGRADE = outputs / '20260911_v6_regrade'
        ps.CONTRASTS = outputs / '20260910_expression_contrasts'
        ps.CENSUS = outputs / '20260910_systematic_encounters'
        ps.SAMPLE_LABELS = outputs / '20260910_probability_sample_labels'
        ps.REGRESSION = outputs / '20260910_regression'
        ps.BENCH = outputs / '20260910_benchmark_contract'
        ps.OUT = outputs / '20260911_pair_scores'

    @classmethod
    def tearDownClass(cls):
        for name, value in cls.saved.items():
            setattr(ps, name, value)
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def load(self, **kwargs):
        kwargs.setdefault('reference_date', REFERENCE)
        kwargs.setdefault('congress_range', (116, 117))
        return ps.load_inputs(progress=lambda *a, **k: None, **kwargs)

    def run_build(self, out_name, inputs=None, bootstrap=8, seed=7, compare=()):
        inputs = inputs or self.load()
        out = Path(self.tmp) / out_name
        receipt = ps.build(out, inputs, bootstrap=bootstrap, seed=seed, compare=compare,
                           progress=lambda *a, **k: None)
        return out, receipt

    def pair_rows(self, out):
        return {row['pair_id']: row
                for row in ps.read_rows(Path(out) / 'pair_scores.ndjson')}


# ------------------------------------------------------------------ the tests


class StateAssignment(LaneCase):
    """P1-5: four explicit states, one per missing channel, never the word `unknown`."""

    def test_work_states_cover_the_universe_with_no_unknown(self):
        out, receipt = self.run_build('states')
        counts = receipt['label_states']['work_state_counts']
        self.assertEqual(set(counts), set(ps.WORK_STATES))
        self.assertEqual(sum(counts.values()), receipt['universe']['pairs'])
        self.assertGreater(counts[ps.WORK_AVAILABLE], 0)
        self.assertGreater(counts[ps.WORK_CROSS_CHAMBER], 0)
        self.assertNotIn('unknown', json.dumps(counts))

    def test_cross_chamber_pairs_state_not_measured_and_are_not_scored(self):
        out, _ = self.run_build('states_cross')
        row = self.pair_rows(out)['H01__S01']
        self.assertEqual(row['work_state'], ps.WORK_CROSS_CHAMBER)
        for axis in ps.AXES:
            cell = row['estimate']['joint'][axis]['a_to_b']
            self.assertIsNone(cell['expected_grade'])
            self.assertEqual(cell['prediction_state'],
                             'not_scored:' + ps.WORK_CROSS_CHAMBER)
        self.assertIsNone(row['evidence_availability']['work']['co_service_years'])
        self.assertEqual(row['evidence_availability']['work']['co_service_years_state'],
                         ps.WORK_CROSS_CHAMBER)

    def test_no_mentions_is_a_state_not_a_zero_contrast(self):
        """H01 -> H06 has no census row at all; H06 -> H01 has one with n = 0."""
        out, _ = self.run_build('states_speech')
        rows = self.pair_rows(out)
        silent = rows['H01__H06']
        self.assertEqual(silent['speech_state']['a_to_b'], ps.SPEECH_NO_MENTIONS)
        self.assertEqual(silent['speech_state']['b_to_a'], ps.SPEECH_INSUFFICIENT)
        for direction, state in (('a_to_b', ps.SPEECH_NO_MENTIONS),
                                 ('b_to_a', ps.SPEECH_INSUFFICIENT)):
            cell = silent['estimate']['speech_only']['affinity'][direction]
            self.assertEqual(cell['prediction_state'], 'not_scored:' + state)
            self.assertIsNone(cell['expected_grade'])
        self.assertIsNone(silent['evidence_availability']['speech']['a_to_b']['warm_contrast'])
        self.assertEqual(silent['evidence_availability']['speech']['a_to_b']
                         ['mention_turns_by_venue'], {v: 0 for v in ps.VENUES})
        loud = rows['H01__H02']
        self.assertEqual(loud['speech_state']['a_to_b'], ps.SPEECH_AVAILABLE)
        self.assertEqual(loud['estimate']['speech_only']['affinity']['a_to_b']
                         ['prediction_state'], ps.SCORED)

    def test_insufficient_exposure_is_its_own_state(self):
        inputs = self.load()
        # H06 -> H01 carries a row with n = 0, which the census marks insufficient.
        state = ps.speech_state_of(inputs['pooled'][('H06', 'H01')])
        self.assertEqual(state, ps.SPEECH_INSUFFICIENT)
        self.assertEqual(ps.speech_state_of(None), ps.SPEECH_NO_MENTIONS)

    def test_no_history_before_date_when_the_panel_starts_after_the_reference(self):
        inputs = self.load(reference_date='2019-03-02', congress_range=(116, 117))
        states = [ps.work_state_of(inputs['work_rows'][k]) for k in sorted(inputs['work_rows'])]
        self.assertIn(ps.WORK_NO_HISTORY, states)

    def test_no_dated_membership_is_reported_not_defaulted(self):
        self.assertEqual(ps.work_state_of(None), ps.WORK_NO_MEMBERSHIP)
        self.assertEqual(ps.work_state_of(dict(chamber=None)), ps.WORK_NO_MEMBERSHIP)
        with self.assertRaises(ValueError):
            ps.work_state_of(dict(chamber='House', work_status='something_new'))

    def test_a_pair_with_an_unresolved_chamber_is_stated_not_crashed_into(self):
        """OrdinalDegrees refuses a None chamber, so such a row must never reach it.

        At a reference date inside the 115th only the four members carrying a 115th term
        have a resolvable chamber, so the universe holds both kinds of row at once. H04
        has no 115th term while H01 does, and H01 -> H04 still carries speech evidence:
        that is exactly the combination that would otherwise reach predict_proba with a
        None chamber and raise there.
        """
        inputs = self.load(reference_date='2018-06-01', congress_range=(116, 117))
        out, receipt = self.run_build('unresolved', inputs=inputs, bootstrap=4)
        total = receipt['universe']['directed_rows']
        unresolved = receipt['fits']['joint']['unresolved_chamber_rows']
        self.assertGreater(unresolved, 0)
        self.assertLess(unresolved, total, 'a mixed universe is what this guards')
        counts = receipt['label_states']['prediction_state_counts']
        for spec in ps.SPEC_ORDER:
            for axis in ps.AXES:
                block = counts[spec][axis]
                self.assertEqual(sum(block['counts'].values()), block['denominator'])
                self.assertGreaterEqual(
                    block['counts'].get('not_scored:' + ps.WORK_NO_MEMBERSHIP, 0), 1)
        rows = self.pair_rows(out)
        mixed = rows['H01__H04']
        self.assertEqual(mixed['work_state'], ps.WORK_NO_MEMBERSHIP)
        self.assertEqual(mixed['speech_state']['a_to_b'], ps.SPEECH_AVAILABLE)
        for spec in ps.SPEC_ORDER:
            self.assertEqual(mixed['estimate'][spec]['affinity']['a_to_b']['prediction_state'],
                             'not_scored:' + ps.WORK_NO_MEMBERSHIP)

    def test_label_state_is_not_assessed_rather_than_unknown(self):
        out, receipt = self.run_build('states_label')
        counts = receipt['label_states']['label_state_counts']
        self.assertEqual(set(counts), set(ps.LABEL_STATES))
        self.assertGreater(counts[ps.LABEL_NOT_ASSESSED], 0)
        text = (Path(out) / 'label_states_summary.json').read_text(encoding='utf-8')
        self.assertNotIn('"unknown"', text)


class VisibilityBoundary(LaneCase):
    """Ruling 7: visibility leaves the estimate and becomes evidence availability."""

    def test_visibility_is_absent_from_every_estimate_feature_vector(self):
        for spec in ps.SPEC_ORDER:
            for residuals in (False, True):
                names = ps.spec_features(spec, residuals)
                for column in ps.VISIBILITY_OUT_OF_ESTIMATE:
                    self.assertNotIn(column, names, '%s leaked into %s' % (column, spec))
                self.assertFalse([n for n in names if 'interview' in n or 'visibility' in n])

    def test_visibility_is_present_in_evidence_availability(self):
        out, receipt = self.run_build('visibility')
        row = self.pair_rows(out)['H01__H02']
        block = row['evidence_availability']['visibility']
        self.assertEqual(sorted(block), ['a_interview_words', 'a_log_interview_words',
                                         'b_interview_words', 'b_log_interview_words'])
        self.assertIsNotNone(block['a_log_interview_words'])
        self.assertNotIn('visibility', json.dumps(row['estimate']))

    def test_the_v6_context_list_is_reproduced_minus_exactly_the_two_columns(self):
        from fec.research.member_personal_relationships.run_chamber_degrees import CONTEXT, WORK
        self.assertEqual(ps.ESTIMATE_CONTEXT + ps.ESTIMATE_WORK,
                         [n for n in CONTEXT if n not in ps.VISIBILITY_OUT_OF_ESTIMATE]
                         + list(WORK))
        self.assertEqual(len(ps.SPECS['joint']['features']), len(CONTEXT) + len(WORK) - 2)

    def test_evidence_availability_carries_the_denominators_and_the_window(self):
        out, receipt = self.run_build('evidence')
        row = self.pair_rows(out)['H01__H02']
        evidence = row['evidence_availability']
        self.assertEqual(evidence['window']['reference_date'], REFERENCE)
        self.assertEqual(evidence['window']['congress_range'], [116, 117])
        self.assertEqual(evidence['window']['timing'], 'strict_before_reference_date')
        work = evidence['work']
        self.assertIsNotNone(work['eligible_target_sponsored_bills']['a_to_b'])
        self.assertIsNotNone(work['shared_eligible_bills'])
        self.assertIsNotNone(work['co_service_years'])
        speech = evidence['speech']['a_to_b']
        self.assertEqual(sorted(speech['mention_turns_by_venue']), list(ps.VENUES))
        self.assertEqual(sorted(evidence['coverage_tier']), ['a', 'b'])
        for key in ('window.timing', 'work.shared_eligible_bills',
                    'confidence.bootstrap_standard_error'):
            self.assertIn(key, receipt['definitions'])


class SharedEligible(LaneCase):
    """The recomputed shared-eligible denominator must reproduce the builder exactly."""

    def test_opportunity_counts_are_reproduced_from_the_recomputed_matrix(self):
        inputs = self.load()
        audit = inputs['eligible_audit']
        self.assertGreater(audit['checked_counts'], 0)
        self.assertEqual(audit['mismatches'], 0)

    def test_shared_eligible_matches_a_hand_count_for_one_pair(self):
        inputs = self.load()
        bills = [b for b in inputs['bills'] if b['chamber'] == 'House'
                 and b['introduced'] < REFERENCE]
        expected = 0
        for b in bills:
            eligible = []
            for who in ('H01', 'H02'):
                term = ps.term_on(inputs['members'][who], b['introduced'])
                eligible.append(bool(term) and term['chamber'] == 'House' and b['sponsor'] != who)
            expected += int(all(eligible))
        self.assertEqual(inputs['shared_eligible']['H01__H02'], expected)

    def test_a_disagreement_raises_rather_than_warning(self):
        inputs = self.load()
        corrupted = {k: dict(v) for k, v in inputs['work_rows'].items()}
        key = next(k for k, v in corrupted.items()
                   if v.get('opportunities_a_to_b') is not None)
        corrupted[key]['opportunities_a_to_b'] += 7
        with self.assertRaises(ValueError):
            ps.coeligible_counts(inputs['members'], inputs['bills'], REFERENCE, corrupted,
                                 progress=lambda *a, **k: None)

    def test_single_term_intervals_reject_an_overlap(self):
        clean = dict(terms=[dict(start='2019-01-03', end='2021-01-03', chamber='House')])
        self.assertEqual(ps.single_term_intervals(clean),
                         [('2019-01-03', '2021-01-03', 'House')])
        overlapping = dict(terms=[dict(start='2019-01-03', end='2021-01-03', chamber='House'),
                                  dict(start='2020-01-03', end='2022-01-03', chamber='Senate')])
        covered = [row for row in ps.single_term_intervals(overlapping)]
        self.assertNotIn(('2020-01-03', '2021-01-03'), [(r[0], r[1]) for r in covered])
        for low, high, _ in covered:
            self.assertIsNotNone(ps.term_on(overlapping, low))


class HeldOutSeal(LaneCase):
    """The 120 sealed dyads are scored and then refused from every reported figure."""

    # Neither sealed dyad carries a lane label, exactly as the frozen split guarantees:
    # a sealed pair that also held a degree record would make the build raise, which
    # test_the_assertion_raises_on_a_leak checks directly.
    heldout = ('H02__H05', 'H06__S03')

    def test_heldout_pairs_are_scored_and_flagged(self):
        out, receipt = self.run_build('heldout')
        rows = self.pair_rows(out)
        self.assertTrue(rows['H02__H05']['heldout'])
        self.assertFalse(rows['H01__H02']['heldout'])
        self.assertEqual(receipt['heldout']['in_universe'], 2)
        self.assertEqual(rows['H02__H05']['estimate']['joint']['affinity']['a_to_b']
                         ['prediction_state'], ps.SCORED)
        self.assertEqual(rows['H02__H05']['label']['state'], ps.LABEL_NOT_ASSESSED)

    def test_no_heldout_id_reaches_the_validation_table_or_the_report(self):
        out, receipt = self.run_build('heldout_seal')
        denied = set(self.heldout)
        text = (Path(out) / 'validation_predictions.ndjson').read_text(encoding='utf-8')
        for pair_id in denied:
            self.assertNotIn(pair_id, text)
        receipt = dict(receipt, artefacts=[], glassbox_run_id='x', runtime_seconds=0.0)
        report = ps.report_text(receipt)
        for pair_id in denied:
            self.assertNotIn(pair_id, report)
        self.assertEqual(ps.assert_text_free_of_heldout(report, frozenset(denied), 'REPORT.md'),
                         len(denied))

    def test_the_assertion_raises_on_a_leak(self):
        with self.assertRaises(ValueError):
            ps.assert_no_heldout(['A__B', 'H02__H04'], frozenset({'H02__H04'}), 'table')
        with self.assertRaises(ValueError):
            ps.assert_text_free_of_heldout('a line naming H02__H04', frozenset({'H02__H04'}),
                                           'REPORT.md')
        self.assertEqual(ps.assert_no_heldout(['A__B'], frozenset({'H02__H04'}), 'table'), 1)

    def test_a_sealed_dyad_that_also_held_a_label_stops_the_build(self):
        """The seal is an assertion, not a filter: a labelled sealed dyad must raise."""
        inputs = self.load()
        leaked = frozenset(set(inputs['denied']) | {'H02__H04'})
        with self.assertRaises(ValueError):
            ps.build(Path(self.tmp) / 'heldout_leak', dict(inputs, denied=leaked), bootstrap=2,
                     seed=1, progress=lambda *a, **k: None)

    def test_a_heldout_label_is_refused_rather_than_read(self):
        path = Path(self.tmp) / 'leaky_sample.ndjson'
        write_ndjson(path, [dict(pair_id='H02__H04', split='heldout', affinity=3,
                                 antagonism=None)])
        with self.assertRaises(ValueError):
            ps.load_sample(path)

    def test_the_real_frozen_deny_list_is_the_one_the_module_reads(self):
        """A guard on the wiring: the real file still holds 120 unlabelled sealed rows."""
        real = (self.saved['OUTPUTS'] / '20260910_frozen_v5/sampled_pairs.ndjson')
        if not real.is_file():
            self.skipTest('frozen v5 sample not present')
        development, denied = ps.load_sample(real)
        self.assertEqual(len(denied), 120)
        self.assertEqual(len(development), 180)


class BootstrapConfidence(LaneCase):
    """P1-6: confidence is a bootstrap standard error, never the model probability."""

    def test_standard_error_shape_and_determinism_under_a_fixed_seed(self):
        inputs = self.load()
        rows = ps.training_rows(inputs, False)
        names = ps.spec_features('joint', False)
        index = ps.fittable(rows, 'affinity', 'joint')
        x = ps.design_matrix(rows, index, names)
        chambers = [rows[i]['chamber'] for i in index]
        first, audit = ps.bootstrap_fits(rows, index, names, 'affinity', True, 12, 4242)
        second, _ = ps.bootstrap_fits(rows, index, names, 'affinity', True, 12, 4242)
        other, _ = ps.bootstrap_fits(rows, index, names, 'affinity', True, 12, 99)
        self.assertEqual(audit['requested'], 12)
        self.assertEqual(audit['resample_unit'], 'evidence_family_component')
        se_a = ps.bootstrap_standard_error(first, x, chambers)
        se_b = ps.bootstrap_standard_error(second, x, chambers)
        se_c = ps.bootstrap_standard_error(other, x, chambers)
        self.assertEqual(se_a.shape, (len(index),))
        np.testing.assert_array_equal(se_a, se_b)
        self.assertTrue(np.all(np.isfinite(se_a)))
        self.assertFalse(np.array_equal(se_a, se_c))

    def test_chunking_does_not_change_the_standard_error(self):
        inputs = self.load()
        rows = ps.training_rows(inputs, False)
        names = ps.spec_features('joint', False)
        index = ps.fittable(rows, 'affinity', 'joint')
        x = ps.design_matrix(rows, index, names)
        chambers = [rows[i]['chamber'] for i in index]
        models, _ = ps.bootstrap_fits(rows, index, names, 'affinity', True, 10, 11)
        whole = ps.bootstrap_standard_error(models, x, chambers, chunk=10 ** 6)
        pieces = ps.bootstrap_standard_error(models, x, chambers, chunk=2)
        np.testing.assert_allclose(whole, pieces, rtol=0, atol=1e-12)

    def test_too_few_refits_gives_a_missing_standard_error_not_a_zero(self):
        inputs = self.load()
        rows = ps.training_rows(inputs, False)
        names = ps.spec_features('joint', False)
        index = ps.fittable(rows, 'affinity', 'joint')
        x = ps.design_matrix(rows, index, names)
        chambers = [rows[i]['chamber'] for i in index]
        se = ps.bootstrap_standard_error([], x, chambers)
        self.assertTrue(np.all(np.isnan(se)))

    def test_confidence_is_not_the_model_probability(self):
        out, _ = self.run_build('confidence')
        row = self.pair_rows(out)['H01__H02']
        cell = row['estimate']['joint']['affinity']['a_to_b']
        se = row['confidence']['joint']['affinity']['a_to_b']['bootstrap_standard_error']
        self.assertIsNotNone(se)
        self.assertEqual(len(cell['probability_by_grade']), 5)
        self.assertNotIn(se, cell['probability_by_grade'])
        self.assertAlmostEqual(sum(cell['probability_by_grade']), 1.0, places=4)


class ResidualSubstitution(LaneCase):
    """P1-7 flag: the raw bill-rate work columns are swapped for baseline residuals."""

    def test_the_switch_replaces_the_raw_columns_and_records_it(self):
        path = self.lane.residual_file()
        inputs = self.load(work_residuals=path)
        out, receipt = self.run_build('residuals', inputs=inputs)
        names = receipt['fits']['joint']['features']
        for column in ps.RAW_WORK_COLUMNS:
            self.assertNotIn(column, names)
        for column in ps.RESIDUAL_FEATURES:
            self.assertIn(column, names)
        self.assertIn('co_service_years', names)
        self.assertTrue(receipt['work_residuals']['active'])
        self.assertEqual(receipt['work_residuals']['substituted_columns'], ps.RESIDUAL_FEATURES)
        self.assertEqual(receipt['work_residuals']['audit']['directed'], False)
        row = self.pair_rows(out)['H01__H02']
        block = row['evidence_availability']['work']['residual_substitution']
        self.assertTrue(block['active'])
        self.assertIsNotNone(block['eligible_opportunities'])

    def test_default_run_keeps_the_raw_columns(self):
        out, receipt = self.run_build('raw')
        names = receipt['fits']['joint']['features']
        for column in ps.RAW_WORK_COLUMNS:
            self.assertIn(column, names)
        for column in ps.RESIDUAL_FEATURES:
            self.assertNotIn(column, names)
        self.assertFalse(receipt['work_residuals']['active'])
        self.assertNotIn('residual_substitution',
                         self.pair_rows(out)['H01__H02']['evidence_availability']['work'])

    def test_a_pair_with_no_residual_row_gets_its_own_state_not_a_zero(self):
        path = self.lane.residual_file(missing=('H01__H02',))
        inputs = self.load(work_residuals=path)
        out, receipt = self.run_build('residuals_missing', inputs=inputs)
        row = self.pair_rows(out)['H01__H02']
        self.assertEqual(row['work_state'], ps.WORK_NO_RESIDUAL)
        self.assertEqual(row['estimate']['joint']['affinity']['a_to_b']['prediction_state'],
                         'not_scored:' + ps.WORK_NO_RESIDUAL)
        self.assertGreater(receipt['label_states']['work_state_counts'][ps.WORK_NO_RESIDUAL], 0)

    def test_a_residual_file_with_the_wrong_schema_raises(self):
        path = Path(self.tmp) / 'bad_residuals.ndjson'
        write_ndjson(path, [dict(pair_id='H01__H02', rate_ratio_shrunk=1.0, residual=0.0)])
        with self.assertRaises(ValueError):
            ps.load_residuals(path)


class DirectedResidualSubstitution(LaneCase):
    """--work-residuals-directed: pooled per (signer, sponsor) direction, never per pair.

    H01 -> H02 is both the P1-7 fixture's own pair and training record v6:test-0's own
    (actor, target), so every test below reuses it rather than introducing a second
    synthetic dyad.
    """

    def test_pooling_sums_across_congresses_and_recomputes_from_scratch(self):
        rows = [directed_residual_row('H01', 'H02', n=2, big_n=10, expected=1.0, congress=116),
                directed_residual_row('H01', 'H02', n=3, big_n=8, expected=0.5, congress=117)]
        path = Path(self.tmp) / 'directed_pool_only.ndjson'
        write_ndjson(path, rows)
        pooled, audit = ps.load_residuals_directed(path)
        entry = pooled[('H01', 'H02')]
        self.assertEqual(entry['counts']['original_cosponsorships'], 5)
        self.assertEqual(entry['counts']['eligible_opportunities'], 18)
        self.assertAlmostEqual(entry['counts']['expected'], 1.5)
        self.assertAlmostEqual(entry['counts']['residual'], 3.5)
        self.assertAlmostEqual(entry['work_residual'], 3.5)
        self.assertAlmostEqual(entry['work_rate_ratio_shrunk'], (5 + 0.5) / (1.5 + 0.5))
        self.assertNotIn(('H02', 'H01'), pooled)
        self.assertEqual(audit['rows_read'], 2)
        self.assertEqual(audit['directions'], 1)
        self.assertTrue(audit['directed'])

    def test_the_two_directions_of_one_pair_pool_separately(self):
        rows = [directed_residual_row('H01', 'H02', n=5, big_n=10, expected=2.0),
                directed_residual_row('H02', 'H01', n=1, big_n=10, expected=2.0)]
        path = self.lane.residual_file_directed(rows)
        pooled, audit = ps.load_residuals_directed(path)
        self.assertEqual(audit['directions'], 2)
        self.assertNotEqual(pooled[('H01', 'H02')]['work_residual'],
                            pooled[('H02', 'H01')]['work_residual'])
        self.assertNotEqual(pooled[('H01', 'H02')]['work_rate_ratio_shrunk'],
                            pooled[('H02', 'H01')]['work_rate_ratio_shrunk'])

    def test_per_direction_substitution_differs_in_a_full_build(self):
        # Full coverage everywhere except the pair under test, so the joint/affinity fit
        # still has enough of the 12-record annotated panel to fit at all; H01 -> H02 and
        # H02 -> H01 are overridden to different counts to make the two directions differ.
        rows = self.lane.full_directed_rows(
            overrides={('H01', 'H02'): (5, 10, 2.0), ('H02', 'H01'): (1, 10, 2.0)})
        path = self.lane.residual_file_directed(rows)
        inputs = self.load(work_residuals_directed=path)
        out, receipt = self.run_build('residuals_directed_asymmetric', inputs=inputs)
        self.assertTrue(receipt['work_residuals']['active'])
        self.assertTrue(receipt['work_residuals']['directed'])
        row = self.pair_rows(out)['H01__H02']
        block = row['evidence_availability']['work']['residual_substitution']
        self.assertTrue(block['active'])
        self.assertTrue(block['directed'])
        self.assertFalse(block['undirected'])
        self.assertEqual(block['a_to_b']['original_cosponsorships'], 5)
        self.assertEqual(block['b_to_a']['original_cosponsorships'], 1)
        self.assertNotEqual(block['a_to_b']['rate_ratio_shrunk'],
                            block['b_to_a']['rate_ratio_shrunk'])
        for direction in ('a_to_b', 'b_to_a'):
            cell = row['estimate']['joint']['affinity'][direction]
            self.assertEqual(cell['prediction_state'], ps.SCORED)

    def test_a_direction_with_no_row_becomes_no_baseline_row_not_the_pair(self):
        # Full coverage everywhere except H02 -> H01, which is dropped entirely, so the
        # fit still stands on the rest of the panel and the gap is isolated to one row.
        rows = self.lane.full_directed_rows(overrides={('H01', 'H02'): (5, 10, 2.0)},
                                            exclude={('H02', 'H01')})
        path = self.lane.residual_file_directed(rows)
        inputs = self.load(work_residuals_directed=path)
        out, receipt = self.run_build('residuals_directed_missing', inputs=inputs)
        row = self.pair_rows(out)['H01__H02']
        self.assertEqual(row['estimate']['joint']['affinity']['a_to_b']['prediction_state'],
                         ps.SCORED)
        self.assertEqual(row['estimate']['joint']['affinity']['b_to_a']['prediction_state'],
                         'not_scored:' + ps.WORK_NO_BASELINE_ROW)
        block = row['evidence_availability']['work']['residual_substitution']
        self.assertIsNotNone(block['a_to_b']['original_cosponsorships'])
        self.assertIsNone(block['b_to_a']['original_cosponsorships'])
        source = receipt['work_residuals']['directed_source']
        self.assertGreaterEqual(source['directions_missing'], 1)
        self.assertGreaterEqual(source['directions_covered'], 1)

    def test_training_rows_use_the_records_own_direction_not_the_pair(self):
        """Data only for the reverse direction must not satisfy record v6:test-0's own
        (H01 -> H02): an undirected, pair-keyed lookup would wrongly find it."""
        rows = [directed_residual_row('H02', 'H01', n=5, big_n=10, expected=2.0)]
        path = self.lane.residual_file_directed(rows)
        inputs = self.load(work_residuals_directed=path)
        record = {r['id']: r for r in ps.training_rows(inputs, True)}['v6:test-0']
        self.assertEqual((record['actor'], record['target']), ('H01', 'H02'))
        self.assertEqual(record['work_state'], ps.WORK_NO_BASELINE_ROW)

    def test_receipt_records_directed_source_path_hash_and_coverage(self):
        rows = [directed_residual_row('H01', 'H02', n=5, big_n=10, expected=2.0)]
        path = self.lane.residual_file_directed(rows)
        inputs = self.load(work_residuals_directed=path)
        out, receipt = self.run_build('residuals_directed_receipt', inputs=inputs)
        wr = receipt['work_residuals']
        self.assertTrue(wr['directed'])
        self.assertIsNone(wr['path'])
        self.assertIsNone(wr['audit'])
        source = wr['directed_source']
        self.assertEqual(source['path'], ps.relative(path))
        self.assertEqual(len(source['sha256']), 64)
        self.assertEqual(source['rows_pooled'], 1)
        self.assertEqual(source['directions_produced'], 1)
        self.assertGreaterEqual(source['directions_covered'], 1)
        self.assertGreaterEqual(source['directions_missing'], 1)

    def test_both_residual_flags_together_are_refused(self):
        undirected_path = self.lane.residual_file()
        directed_path = self.lane.residual_file_directed(
            [directed_residual_row('H01', 'H02', n=1, big_n=5, expected=0.5)])
        with self.assertRaises(ValueError):
            self.load(work_residuals=undirected_path, work_residuals_directed=directed_path)

    def test_a_directed_residual_file_with_the_wrong_schema_raises(self):
        path = Path(self.tmp) / 'bad_residuals_directed.ndjson'
        write_ndjson(path, [dict(signer='H01', sponsor='H02', original_cosponsorships=1)])
        with self.assertRaises(ValueError):
            ps.load_residuals_directed(path)

    def test_a_directed_residual_row_not_measured_raises(self):
        path = Path(self.tmp) / 'unfitted_directed.ndjson'
        write_ndjson(path, [directed_residual_row('H01', 'H02', n=1, big_n=5, expected=0.5,
                                                  state='not_fitted_too_few_pairs')])
        with self.assertRaises(ValueError):
            ps.load_residuals_directed(path)


class CongressRangeFlag(LaneCase):
    """--bills and --congress-range read a wider panel without history_work's fixed filter."""

    def test_the_range_selects_the_bills_and_is_recorded(self):
        wide = self.load(congress_range=(115, 117))
        narrow = self.load(congress_range=(116, 117))
        self.assertGreater(wide['bill_audit']['included_bills'],
                           narrow['bill_audit']['included_bills'])
        self.assertIn(115, wide['bill_audit']['bills_by_congress'])
        self.assertNotIn(115, narrow['bill_audit']['bills_by_congress'])
        self.assertEqual(narrow['bill_audit']['excluded_outside_range'],
                         wide['bill_audit']['included_bills']
                         - narrow['bill_audit']['included_bills']
                         + wide['bill_audit']['excluded_outside_range'])
        self.assertEqual(wide['panel_start'], '2017-01-03')
        self.assertEqual(narrow['panel_start'], '2019-01-03')

    def test_the_training_rows_move_onto_the_same_panel_as_the_universe(self):
        narrow = self.load(congress_range=(116, 117))
        wide = self.load(congress_range=(115, 117))
        narrow_rows = {r['id']: r for r in ps.training_rows(narrow, False)}
        wide_rows = {r['id']: r for r in ps.training_rows(wide, False)}
        moved = [rid for rid, row in wide_rows.items()
                 if row['features']['log_shared_bills']
                 != narrow_rows[rid]['features']['log_shared_bills']]
        self.assertTrue(moved, 'the wider panel left every training work column unchanged')
        self.assertEqual(narrow['training_work_audit']['records'], len(narrow['annotations']))
        self.assertGreater(wide['training_work_audit']['cells_beyond_tolerance'], 0)
        self.assertEqual(narrow['training_work_audit']['cells_beyond_tolerance'], 0)

    def test_a_mismatch_on_the_frozen_default_panel_stops_the_run(self):
        inputs = self.load()
        broken = {k: dict(v) for k, v in inputs['v6_features'].items()}
        first = sorted(broken)[0]
        broken[first]['log_shared_bills'] = (broken[first].get('log_shared_bills') or 0) + 5.0
        with self.assertRaises(ValueError):
            ps.training_work_panel(inputs['members'], inputs['bills'], inputs['annotations'],
                                   broken, True, progress=lambda *a, **k: None)
        rows, audit = ps.training_work_panel(inputs['members'], inputs['bills'],
                                             inputs['annotations'], broken, False,
                                             progress=lambda *a, **k: None)
        self.assertGreater(audit['cells_beyond_tolerance'], 0)
        self.assertFalse(audit['reproduces_frozen_v6_features'])

    def test_a_float32_sized_wobble_is_tolerated_but_a_real_move_is_not(self):
        inputs = self.load()
        noisy = {k: dict(v) for k, v in inputs['v6_features'].items()}
        first = sorted(noisy)[0]
        base = noisy[first]['log_shared_bills']
        noisy[first]['log_shared_bills'] = base + 1e-9
        _, audit = ps.training_work_panel(inputs['members'], inputs['bills'],
                                          inputs['annotations'], noisy, True,
                                          progress=lambda *a, **k: None)
        self.assertEqual(audit['cells_beyond_tolerance'], 0)
        self.assertEqual(audit['cells_within_float32_tolerance'], 1)
        # The gap that justifies the tolerance survives the receipt's float rounding.
        self.assertEqual(float(audit['max_absolute_difference']), 1e-9)
        self.assertFalse(audit['max_absolute_difference_exceeds_tolerance'])
        noisy[first]['log_shared_bills'] = base + 0.5
        with self.assertRaises(ValueError):
            ps.training_work_panel(inputs['members'], inputs['bills'], inputs['annotations'],
                                   noisy, True, progress=lambda *a, **k: None)

    def test_the_rebuild_reproduces_the_stored_features_on_the_same_panel(self):
        inputs = self.load()
        rows, audit = ps.training_work_panel(inputs['members'], inputs['bills'],
                                             inputs['annotations'], inputs['v6_features'], True,
                                             progress=lambda *a, **k: None)
        self.assertEqual(audit['cells_beyond_tolerance'], 0)
        self.assertEqual(audit['cells_compared'],
                         len(inputs['annotations']) * len(ps.BUILDER_COLUMNS))
        self.assertTrue(audit['reproduces_frozen_v6_features'])
        self.assertEqual(sorted(rows), sorted(r['id'] for r in inputs['annotations']))

    def test_a_wider_range_can_only_add_eligible_bills(self):
        wide = self.load(congress_range=(115, 117))
        narrow = self.load(congress_range=(116, 117))
        for key, value in narrow['shared_eligible'].items():
            self.assertGreaterEqual(wide['shared_eligible'].get(key, 0), value)

    def test_the_flag_parser_rejects_a_backwards_range(self):
        self.assertEqual(ps.parse_congress_range('115-119'), (115, 119))
        self.assertEqual(ps.parse_congress_range('118'), (118, 118))
        with self.assertRaises(Exception):
            ps.parse_congress_range('119-115')


class NominateFlag(LaneCase):
    """--nominate-file substitutes per-congress ideology in training and universe alike."""

    def test_per_congress_values_replace_the_static_ones_in_both_places(self):
        path = Path(self.tmp) / 'votes/HSall_members.csv'
        plain = self.load()
        swapped = self.load(nominate_path=path)
        static_rows = ps.training_rows(plain, False)
        moved_rows = ps.training_rows(swapped, False)
        by_id = {r['id']: r for r in static_rows}
        changed = [r['id'] for r in moved_rows
                   if r['features']['actor_dw1'] != by_id[r['id']]['features']['actor_dw1']]
        self.assertTrue(changed, 'no training row picked up a per-congress score')
        out, receipt = self.run_build('nominate', inputs=swapped)
        self.assertEqual(receipt['nominate']['replaced_columns'], list(ps.NOMINATE_COLUMNS))
        self.assertIn('per_congress', receipt['nominate']['rank_counts'])
        row = self.pair_rows(out)['H01__H02']
        self.assertEqual(row['evidence_availability']['nominate']['a'], 'per_congress')

    def test_a_member_with_no_score_anywhere_stays_missing(self):
        resolve = ps.nominate_resolver(Path(self.tmp) / 'votes/HSall_members.csv', (116, 117),
                                       self.lane.members)
        hit = resolve('H01', '2021-06-01')
        self.assertEqual(hit['rank'], 2)
        self.assertAlmostEqual(hit['dw1'], -0.9)
        fallback = resolve('H06', '2021-06-01')
        self.assertEqual(fallback['rank'], 1)
        self.assertEqual(fallback['dw1'], self.lane.members['H06']['d1'])
        orphan = dict(self.lane.members)
        orphan['H06'] = dict(orphan['H06'], d1=None, d2=None)
        resolve_two = ps.nominate_resolver(Path(self.tmp) / 'votes/HSall_members.csv', (116, 117),
                                           orphan)
        missing = resolve_two('H06', '2021-06-01')
        self.assertEqual(missing['rank'], 0)
        self.assertIsNone(missing['dw1'])

    def test_the_default_run_uses_the_static_members_json_values(self):
        out, receipt = self.run_build('nominate_off')
        self.assertIsNone(receipt['nominate']['path'])
        self.assertEqual(receipt['nominate']['replaced_columns'], [])
        self.assertNotIn('nominate', self.pair_rows(out)['H01__H02']['evidence_availability'])


class ValidationTables(LaneCase):
    """P1-5: held-out predictions live in their own table, with denominators."""

    def test_the_degree_table_reports_both_label_sets_separately(self):
        out, receipt = self.run_build('validation')
        sources = {entry['label_source'] for entry in receipt['degree_records']['summaries']}
        self.assertEqual(sources, {'original', 'blind_passes_agree'})
        for entry in receipt['degree_records']['summaries']:
            self.assertEqual(entry['records'], entry['scored'] + entry['not_scored'])
            if entry['scored']:
                self.assertEqual(entry['denominator'], entry['scored'])
        blind = receipt['degree_records']['blind_agreement']
        for axis in ps.AXES:
            self.assertLessEqual(blind['agreed'][axis], blind['both_assessed'][axis])

    def test_the_graded_sample_table_uses_only_cells_both_passes_agreed_on(self):
        out, receipt = self.run_build('graded')
        summary = receipt['graded_sample']['summary']
        # Four affinity cells carry merge_rule "exact"; the fifth is min_of_adjacent
        # and is counted as a sensitivity cell instead of entering the table.
        self.assertEqual(summary['affinity']['agreed_cells'], 4)
        self.assertEqual(summary['friction']['agreed_cells'], 3)
        self.assertEqual(summary['affinity']['sensitivity_cells_min_of_adjacent'], 0)
        for axis in ps.AXES:
            block = summary[axis]
            self.assertEqual(block['graded_cells'],
                             block['agreed_cells'] + block['sensitivity_cells_min_of_adjacent']
                             + block['adjudication_pending_cells'])
        self.assertEqual(summary['friction']['sensitivity_cells_min_of_adjacent'], 1)
        self.assertEqual(receipt['graded_sample']['no_evidence_rows'], 1)
        for axis in ps.AXES:
            auc = summary[axis]['joint']['presence_vs_ordinary_auc']
            self.assertIn(auc['state'], ('reported', 'n_too_small', 'no_scored_cells'))
            self.assertEqual(auc['comparisons'], auc['positive'] * auc['negative'])

    def test_an_auc_below_the_class_floor_prints_its_counts_instead_of_a_number(self):
        small = ps.presence_auc([1.0, 2.0, 3.0], [True, True, False])
        self.assertIsNone(small['auc'])
        self.assertEqual(small['state'], 'n_too_small')
        self.assertEqual((small['positive'], small['negative']), (2, 1))
        big = ps.presence_auc([3.0] * 5 + [1.0] * 5, [True] * 5 + [False] * 5)
        self.assertEqual(big['auc'], 1.0)
        self.assertEqual(big['comparisons'], 25)

    def test_validation_rows_carry_their_table_and_state(self):
        out, _ = self.run_build('validation_rows')
        rows = list(ps.read_rows(Path(out) / 'validation_predictions.ndjson'))
        tables = {row['table'] for row in rows}
        self.assertEqual(tables, {'degree_records', 'graded_development_pairs'})
        for row in rows:
            self.assertTrue(row['prediction_state'] == ps.SCORED
                            or row['prediction_state'].startswith('not_scored:'))

    def test_two_axes_are_reported_side_by_side_and_never_combined(self):
        out, _ = self.run_build('axes')
        row = self.pair_rows(out)['H01__H02']
        for spec in ps.SPEC_ORDER:
            self.assertEqual(sorted(row['estimate'][spec]), sorted(ps.AXES))
        flat = json.dumps(row['estimate'])
        for word in ('signed', 'combined_score', 'net_affinity'):
            self.assertNotIn(word, flat)


class Determinism(LaneCase):
    """A small synthetic universe end to end, byte for byte, twice."""

    def test_two_runs_of_the_same_build_are_byte_identical(self):
        first, receipt_a = self.run_build('determinism_a', bootstrap=10, seed=31)
        second, receipt_b = self.run_build('determinism_b', bootstrap=10, seed=31)
        for name in ps.ARTEFACTS:
            left = (Path(first) / name).read_bytes()
            right = (Path(second) / name).read_bytes()
            self.assertEqual(left, right, '%s differs between two runs at one seed' % name)
        for key in ('fits', 'label_states', 'degree_records', 'graded_sample'):
            self.assertEqual(json.dumps(receipt_a[key], sort_keys=True),
                             json.dumps(receipt_b[key], sort_keys=True))

    def test_the_report_is_stable_once_the_volatile_fields_are_fixed(self):
        first, receipt_a = self.run_build('determinism_report_a', bootstrap=6, seed=5)
        second, receipt_b = self.run_build('determinism_report_b', bootstrap=6, seed=5)
        frozen = dict(artefacts=[], glassbox_run_id='fixed', runtime_seconds=0.0)
        self.assertEqual(ps.report_text(dict(receipt_a, **frozen)),
                         ps.report_text(dict(receipt_b, **frozen)))

    def test_a_different_seed_moves_the_standard_errors_but_not_the_estimate(self):
        first, _ = self.run_build('seed_a', bootstrap=10, seed=1)
        second, _ = self.run_build('seed_b', bootstrap=10, seed=2)
        left = self.pair_rows(first)['H01__H02']
        right = self.pair_rows(second)['H01__H02']
        self.assertEqual(left['estimate']['joint']['affinity']['a_to_b']['expected_grade'],
                         right['estimate']['joint']['affinity']['a_to_b']['expected_grade'])
        self.assertNotEqual(left['confidence']['joint']['affinity']['a_to_b'],
                            right['confidence']['joint']['affinity']['a_to_b'])


class NoImputationAcrossAChannel(LaneCase):
    """P1-11: a missing channel is availability, never a mean-imputed feature row."""

    def test_a_row_without_the_channel_never_enters_that_channel_fit(self):
        inputs = self.load()
        rows = ps.training_rows(inputs, False)
        for spec in ('joint', 'work_only'):
            for index in ps.fittable(rows, 'affinity', spec):
                self.assertEqual(rows[index]['work_state'], ps.WORK_AVAILABLE)
        for index in ps.fittable(rows, 'affinity', 'speech_only'):
            self.assertEqual(rows[index]['speech_state'], ps.SPEECH_AVAILABLE)

    def test_a_cross_chamber_training_row_is_excluded_from_the_work_fit(self):
        inputs = self.load()
        rows = ps.training_rows(inputs, False)
        cross = [i for i, r in enumerate(rows) if r['chamber'] == 'cross_chamber']
        self.assertTrue(cross)
        self.assertFalse(set(cross) & set(ps.fittable(rows, 'affinity', 'joint')))

    def test_the_partial_estimates_are_labelled_partial_in_every_row(self):
        out, _ = self.run_build('partial')
        row = self.pair_rows(out)['H01__H02']
        self.assertNotIn('partial', row['estimate']['joint']['affinity']['a_to_b'])
        for spec in ('work_only', 'speech_only'):
            cell = row['estimate'][spec]['affinity']['a_to_b']
            self.assertTrue(cell['partial'])
            self.assertEqual(cell['partial_channel'], ps.SPECS[spec]['channel'])

    def test_an_unscored_cell_carries_no_expected_grade_at_all(self):
        out, receipt = self.run_build('unscored')
        for row in ps.read_rows(Path(out) / 'pair_scores.ndjson'):
            for spec in ps.SPEC_ORDER:
                for axis in ps.AXES:
                    for cell in row['estimate'][spec][axis].values():
                        if cell['prediction_state'] != ps.SCORED:
                            self.assertIsNone(cell['expected_grade'])
                            self.assertNotIn('probability_by_grade', cell)


class ComparisonAcrossRuns(LaneCase):
    """--compare lines sibling runs up without merging them."""

    def test_a_sibling_receipt_becomes_one_comparison_row(self):
        out, receipt = self.run_build('compare_base')
        ps.write_json(Path(out) / 'run_receipt.json',
                      ps.clean(dict(receipt, artefacts=[], glassbox_run_id='x',
                                    runtime_seconds=0.0)))
        second, with_compare = self.run_build('compare_main', compare=[str(out)])
        runs = with_compare['comparison']['runs']
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['run'], 'compare_base')
        self.assertEqual(runs[0]['congress_range'], '116-117')
        self.assertEqual(runs[0]['work_columns'], 'raw')
        self.assertEqual(runs[0]['pairs'], with_compare['universe']['pairs'])
        self.assertEqual(runs[0]['affinity_rows'],
                         with_compare['fits']['joint']['axes']['affinity']['labelled_rows'])
        self.assertEqual(runs[0]['training_cells_beyond_tolerance'], 0)
        text = ps.report_text(dict(with_compare, artefacts=[], glassbox_run_id='x',
                                   runtime_seconds=0.0))
        self.assertIn('Comparison across runs', text)
        self.assertIn('compare_base', text)

    def test_a_missing_sibling_raises_rather_than_printing_an_empty_row(self):
        with self.assertRaises(FileNotFoundError):
            ps.comparison_table([str(Path(self.tmp) / 'no_such_run')])

    def test_no_comparison_flag_prints_the_absence(self):
        out, receipt = self.run_build('compare_absent')
        text = ps.report_text(dict(receipt, artefacts=[], glassbox_run_id='x',
                                   runtime_seconds=0.0))
        self.assertIn('No sibling run was supplied', text)


class ReportDiscipline(LaneCase):
    """The report says STATUS, prints denominators, and claims nothing causal."""

    def test_the_report_carries_status_denominators_and_no_causal_verb(self):
        out, receipt = self.run_build('report')
        text = ps.report_text(dict(receipt, artefacts=[], glassbox_run_id='x',
                                   runtime_seconds=1.0))
        self.assertIn('**STATUS: EXPLORATORY.**', text)
        self.assertIn('Design choices pending Paul', text)
        self.assertIn('Limitations carried by every figure above', text)
        self.assertIn('denominator', text)
        lowered = text.lower()
        for verb in (' causes ', ' caused ', ' leads to ', ' drives ', ' because of the model',
                     ' proves ', ' impact of '):
            self.assertNotIn(verb, lowered, 'causal verb %r in REPORT.md' % verb)

    def test_every_state_reaches_the_report_with_its_denominator(self):
        out, receipt = self.run_build('report_states')
        text = ps.report_text(dict(receipt, artefacts=[], glassbox_run_id='x',
                                   runtime_seconds=1.0))
        for state in ps.WORK_STATES:
            self.assertIn('`%s`' % state, text)
        for state in ps.SPEECH_STATES:
            self.assertIn('`%s`' % state, text)
        self.assertIn('`%s`' % ps.LABEL_NOT_ASSESSED, text)

    def test_the_receipt_names_its_inputs_by_hash(self):
        out, receipt = self.run_build('report_receipt')
        self.assertIn('members.json', receipt['inputs'])
        for entry in receipt['inputs'].values():
            self.assertEqual(len(entry['sha256']), 64)
            self.assertGreater(entry['bytes'], 0)
        self.assertEqual(receipt['status'], 'EXPLORATORY')


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
