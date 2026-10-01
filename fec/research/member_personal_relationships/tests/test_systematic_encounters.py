"""Synthetic-only tests for the systematic encounter census.

No live corpus, no live roster, no frozen sample is read here. Every fixture is
built in a temporary directory so the tests can never touch, or depend on, the
sealed held-out split.
"""
import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from fec.research.member_personal_relationships.history_speech import (
    clean, name_matcher, nearest_cues)
from fec.research.member_personal_relationships.systematic_encounters import (
    CALIBRATION_PER_STRATUM, PACKET_CAP, Reservoir, TextMap, TITLES, build_matcher,
    census, cues_by_mention, report_text, resolve_match, Roster)


def term(start, end, chamber, state, party='Republican'):
    return dict(start=start, end=end, chamber=chamber, state=state, party=party)


LONG = ('2019-01-03', '2027-01-03')


def roster_fixture():
    """Two Smiths (ambiguous), a one-seat state, a two-senator state, two CA seats."""
    return {
        'S1': dict(bioguide='S1', name='John Smith', terms=[term(*LONG, 'House', 'CA')]),
        'S2': dict(bioguide='S2', name='Jane Smith', terms=[term(*LONG, 'Senate', 'TX')]),
        'A1': dict(bioguide='A1', name='Alice Alpha', terms=[term(*LONG, 'House', 'WY')]),
        'D1': dict(bioguide='D1', name='Dave Delta', terms=[term(*LONG, 'House', 'CA')]),
        'B1': dict(bioguide='B1', name='Bob Beta',
                   terms=[term('2013-01-03', '2019-01-03', 'Senate', 'VT'),
                          term(*LONG, 'Senate', 'VT')]),
        'C1': dict(bioguide='C1', name='Carol Gamma', terms=[term('2021-01-03', '2027-01-03', 'Senate', 'VT')]),
        'E1': dict(bioguide='E1', name='Eve Epsilon', terms=[term(*LONG, 'House', 'TX')]),
        # Montana holds two House seats in the panel, so a day that shows only one
        # of them is an incomplete delegation, not a one-seat state.
        'F1': dict(bioguide='F1', name='Frank Foxtrot', terms=[term(*LONG, 'House', 'MT')]),
        'G1': dict(bioguide='G1', name='Grace Golf', terms=[term('2025-01-03', '2027-01-03', 'House', 'MT')]),
        # Nevada holds only one of its two Senate seats in the panel.
        'H1': dict(bioguide='H1', name='Harry Hotel', terms=[term(*LONG, 'Senate', 'NV')]),
        # First name equal to somebody else's ambiguous surname: the real-corpus
        # shape of Scott Peters, Kim Schrier, Joyce Beatty and Kelly Morrison.
        'K1': dict(bioguide='K1', name='Smith Kilo', terms=[term(*LONG, 'House', 'OH')]),
        # First name equal to somebody else's UNAMBIGUOUS surname: the real-corpus
        # shape of Jack Reed, Paul Gosar, James Risch, Young Kim, Warren Davidson
        # and Neal Dunn, each of whom history_speech mis-attributes.
        'L1': dict(bioguide='L1', name='Alpha Lima', terms=[term(*LONG, 'House', 'IA')]),
    }


def write_corpus(path, rows):
    connection = sqlite3.connect(str(path))
    connection.execute('CREATE TABLE speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,'
                       'package TEXT,nwords INTEGER,text TEXT)')
    connection.executemany('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)',
                           [(r['member'], r['date'], r['source'], r.get('chamber', ''),
                             r.get('package', 'PKG'), len(r['text'].split()), r['text']) for r in rows])
    connection.commit()
    connection.close()


def pair_row(pair_id, pair, names, split='development', stratum='X', weight=1.0):
    return dict(pair_id=pair_id, pair=list(pair), names=list(names), split=split,
                stratum=stratum, design_weight=weight, coverage_tiers=['high', 'high'])


def run(rows, pairs=(), members=None, **kwargs):
    members = members or roster_fixture()
    tmp = tempfile.TemporaryDirectory()
    base = Path(tmp.name)
    write_corpus(base / 'corpus.db', rows)
    manifest = census(base / 'corpus.db', members, list(pairs), base / 'out',
                      progress=lambda *a, **k: None, **kwargs)
    out = base / 'out'
    read = lambda n: [json.loads(s) for s in (out / n).read_text(encoding='utf-8').splitlines() if s.strip()]
    bundle = dict(manifest=manifest, dir=out, keep=tmp,
                  mentions=read('systematic_encounters.ndjson'),
                  encounters=read('encounter_counts.ndjson'),
                  baseline=read('speaker_baseline.ndjson'),
                  calibration=read('calibration_sample.ndjson'),
                  hidden=read('calibration_sample_hidden_cues.ndjson'),
                  packets=read('development_pair_packets.ndjson'))
    return bundle


class MatcherFormTests(unittest.TestCase):
    def test_titles_match_history_speech(self):
        """TITLES is pinned to the list history_speech actually uses."""
        one = {'Z1': dict(bioguide='Z1', name='Jane Zzyzx', terms=[term(*LONG, 'House', 'CA')])}
        variants, _ = name_matcher(one)
        prefixes = sorted(v[:-len(' zzyzx')] for v in variants if v != 'jane zzyzx')
        self.assertEqual(prefixes, sorted(TITLES))

    def test_existing_forms_are_preserved_not_replaced(self):
        members = roster_fixture()
        base, _ = name_matcher(members)
        spec, pattern = build_matcher(members)
        for variant, bio in base.items():
            self.assertIn(variant, spec)
            form, kind, payload = spec[variant]
            self.assertEqual(kind, 'fixed')
            self.assertEqual(payload, bio)
            self.assertTrue(pattern.fullmatch(variant), variant)
        self.assertEqual(spec['alice alpha'][0], 'full_name')
        self.assertEqual(spec['mr alpha'][0], 'titled_surname')
        # history_speech never admits a bare surname; neither do we.
        self.assertNotIn('alpha', spec)

    def test_no_base_identification_is_lost_to_a_new_form(self):
        """Every form history_speech could identify must still identify the same member.

        The new two-word ambiguous forms start earlier in the string than a full
        name whose first token is that surname, and finditer takes the earliest
        start, so without titled full names 'Senator Scott Peters' would be
        attributed to a Scott. This walks every base variant, bare and titled,
        in isolation. A base identification is legitimately overridden only when a
        longer, more specific name actually follows it in the text; that case is
        pinned separately by test_a_titled_surname_yields_to_the_full_name.
        """
        members = roster_fixture()
        base, base_pattern = name_matcher(members)
        spec, pattern = build_matcher(members)
        roster = Roster(members)
        from collections import Counter
        for variant, bio in sorted(base.items()):
            for prefix in [''] + [t + ' ' for t in TITLES]:
                text = 'aaa ' + prefix + variant + ' bbb'
                found = []
                for match in pattern.finditer(text):
                    form, kind, payload = spec[match.group()]
                    target, _res = resolve_match(form, kind, payload, actor='ZZZ',
                                                 day='2024-05-01', row_chamber=None, normal=text,
                                                 start=match.start(), end=match.end(),
                                                 roster=roster, drops=Counter())
                    found.append(target)
                self.assertIn(bio, found, (prefix + variant, found))

    def test_a_first_name_that_is_an_ambiguous_surname_still_resolves(self):
        members = roster_fixture()
        spec, pattern = build_matcher(members)
        roster = Roster(members)
        from collections import Counter
        for text, expected in [('congressman smith kilo spoke', 'K1'),
                               ('smith kilo spoke', 'K1'),
                               ('senator smith kilo spoke', 'K1'),
                               ('congressman smith spoke', 'S1')]:
            drops = Counter()
            found = []
            for match in pattern.finditer(text):
                form, kind, payload = spec[match.group()]
                target, _res = resolve_match(form, kind, payload, actor='ZZZ', day='2024-05-01',
                                             row_chamber=None, normal=text, start=match.start(),
                                             end=match.end(), roster=roster, drops=drops)
                found.append(target)
            self.assertEqual(found, [expected], text)

    def test_a_titled_surname_yields_to_the_full_name_that_contains_it(self):
        """"Senator Jack Reed" is Jack Reed, not the member whose surname is Jack.

        history_speech resolves the two-word prefix and attributes the turn to the
        surname holder. This census keeps the base forms but adds the titled full
        name, so the longer and more specific identification wins. Measured on the
        live corpus this corrects 126 (turn, target) units across 77 directed
        pairs in the existing pair_rhetoric baseline.
        """
        members = roster_fixture()
        base, base_pattern = name_matcher(members)
        spec, pattern = build_matcher(members)
        roster = Roster(members)
        from collections import Counter
        text = 'i thank congressman alpha lima for the bill'
        wrong = [base[m.group()] for m in base_pattern.finditer(text)]
        self.assertEqual(wrong, ['A1'])                      # the defect being corrected
        right = []
        for match in pattern.finditer(text):
            form, kind, payload = spec[match.group()]
            target, _res = resolve_match(form, kind, payload, actor='ZZZ', day='2024-05-01',
                                         row_chamber=None, normal=text, start=match.start(),
                                         end=match.end(), roster=roster, drops=Counter())
            right.append(target)
        self.assertEqual(right, ['L1'])

    def test_ambiguous_titled_surnames_are_added_as_context_forms(self):
        spec, _ = build_matcher(roster_fixture())
        form, kind, payload = spec['mr smith']
        self.assertEqual((form, kind), ('titled_surname', 'ambiguous_surname'))
        self.assertEqual(payload[0], 'smith')
        self.assertEqual(set(payload[1]), {'S1', 'S2'})


class ResolutionTests(unittest.TestCase):
    def setUp(self):
        self.members = roster_fixture()
        self.roster = Roster(self.members)
        self.spec, self.pattern = build_matcher(self.members)

    def resolve(self, text, actor='A1', day='2024-05-01', row_chamber=None):
        normal = clean(text)
        out = []
        from collections import Counter
        drops = Counter()
        for match in self.pattern.finditer(normal):
            form, kind, payload = self.spec[match.group()]
            target, resolution = resolve_match(form, kind, payload, actor=actor, day=day,
                                               row_chamber=row_chamber, normal=normal,
                                               start=match.start(), end=match.end(),
                                               roster=self.roster, drops=drops)
            out.append((match.group(), target, resolution))
        return out, drops

    def test_ambiguous_surname_resolved_by_row_chamber(self):
        found, drops = self.resolve('I thank Mr. Smith for the amendment.', row_chamber='House')
        self.assertEqual(found, [('mr smith', 'S1', 'chamber')])
        self.assertFalse(drops)
        found, _ = self.resolve('I thank Mr. Smith for the amendment.', row_chamber='Senate')
        self.assertEqual(found, [('mr smith', 'S2', 'chamber')])

    def test_a_chamber_naming_title_outranks_the_proceedings_chamber(self):
        """'Senator Smith' in a House proceeding is still a senator."""
        found, drops = self.resolve('I thank Senator Smith for the bill.', row_chamber='House')
        self.assertEqual(found, [('senator smith', 'S2', 'chamber')])
        self.assertFalse(drops)
        found, drops = self.resolve('I thank Congressman Smith for the bill.', row_chamber='Senate')
        self.assertEqual(found, [('congressman smith', 'S1', 'chamber')])
        self.assertFalse(drops)

    def test_a_title_naming_an_unoccupied_chamber_is_a_conflict_not_a_fallback(self):
        """Only one Alpha exists and she is in the House; 'Senator Alpha' must drop."""
        members = dict(roster_fixture())
        members['A2'] = dict(bioguide='A2', name='Adam Alpha',
                             terms=[term(*LONG, 'House', 'ND')])       # makes 'alpha' ambiguous
        self.members, self.roster = members, Roster(members)
        self.spec, self.pattern = build_matcher(members)
        found, drops = self.resolve('I thank Senator Alpha for the bill.', actor='D1')
        self.assertEqual(found[0][1], None)
        self.assertEqual(drops['ambiguous_surname_chamber_conflict'], 1)

    def test_ambiguous_surname_dropped_without_context(self):
        found, drops = self.resolve('I thank Mr. Smith for the amendment.', row_chamber=None)
        self.assertEqual(found, [('mr smith', None, None)])
        self.assertEqual(drops['ambiguous_surname_dropped'], 1)
        self.assertEqual(drops['ambiguous_surname_no_disambiguating_context'], 1)

    def test_ambiguous_surname_resolved_by_following_state_cue(self):
        found, drops = self.resolve('I thank Mr. Smith of Texas for the amendment.')
        self.assertEqual(found, [('mr smith', 'S2', 'state_cue')])
        self.assertFalse(drops)

    def test_state_cue_before_the_match_does_not_resolve_it(self):
        found, _ = self.resolve('The Texas delegation and Mr. Smith agree.')
        self.assertEqual(found[-1][1], None)

    def test_single_district_state_reference_resolves(self):
        found, drops = self.resolve('I yield to the gentlewoman from Wyoming.', actor='D1')
        self.assertEqual(found, [('the gentlewoman from wyoming', 'A1', 'single_district')])
        self.assertFalse(drops)

    def test_multi_member_state_reference_needs_a_following_surname(self):
        found, drops = self.resolve('I yield to the gentleman from California.', actor='A1')
        self.assertEqual(found[0][1], None)
        self.assertEqual(drops['house_state_not_unique'], 1)
        found, drops = self.resolve('I yield to the gentleman from California, Mr. Delta.', actor='A1')
        self.assertEqual(found[0], ('the gentleman from california', 'D1', 'unique'))
        self.assertFalse(drops)

    def test_two_senator_state_resolves_only_with_seniority_or_speaker_exclusion(self):
        plain, drops = self.resolve('I agree with the Senator from Vermont.', actor='A1')
        self.assertEqual(plain[0][1], None)
        self.assertEqual(drops['senator_state_not_unique'], 1)

        senior, drops = self.resolve('I agree with the senior Senator from Vermont.', actor='A1')
        self.assertEqual(senior[0], ('the senior senator from vermont', 'B1', 'seniority'))
        self.assertFalse(drops)

        junior, drops = self.resolve('I agree with the junior Senator from Vermont.', actor='A1')
        self.assertEqual(junior[0], ('the junior senator from vermont', 'C1', 'seniority'))
        self.assertFalse(drops)

        excluded, drops = self.resolve('I agree with the Senator from Vermont.', actor='B1')
        self.assertEqual(excluded[0], ('the senator from vermont', 'C1', 'unique'))
        self.assertFalse(drops)

    def test_my_colleague_follows_the_speakers_chamber(self):
        senate, _ = self.resolve('my colleague from Vermont said so.', actor='B1')
        self.assertEqual(senate[0], ('my colleague from vermont', 'C1', 'unique'))
        house, drops = self.resolve('my colleague from California said so.', actor='S1')
        self.assertEqual(house[0], ('my colleague from california', 'D1', 'unique'))
        self.assertFalse(drops)

    def test_a_member_not_serving_that_day_is_not_a_candidate(self):
        found, drops = self.resolve('I agree with the junior Senator from Vermont.',
                                    actor='A1', day='2020-05-01')
        self.assertEqual(found[0][1], None)
        self.assertEqual(drops['senator_state_delegation_not_two'], 1)

    def test_an_incomplete_senate_delegation_never_resolves(self):
        """One roster senator for a two-seat state is a panel artefact, not a fact."""
        for text in ('the Senator from Nevada', 'the senior Senator from Nevada',
                     'the junior Senator from Nevada'):
            found, drops = self.resolve('I agree with ' + text + '.', actor='A1')
            self.assertEqual(found[0][1], None, text)
            self.assertEqual(drops['senator_state_delegation_not_two'], 1)
            drops.clear()

    def test_an_incomplete_house_delegation_never_resolves_on_size_alone(self):
        alone, drops = self.resolve('I yield to the gentleman from Montana.',
                                    actor='A1', day='2024-05-01')
        self.assertEqual(alone[0][1], None)
        self.assertEqual(drops['house_state_roster_delegation_incomplete'], 1)
        named, drops = self.resolve('I yield to the gentleman from Montana, Mr. Foxtrot.',
                                    actor='A1', day='2024-05-01')
        self.assertEqual(named[0], ('the gentleman from montana', 'F1', 'unique'))
        self.assertFalse(drops)
        both, drops = self.resolve('I yield to the gentleman from Montana.',
                                   actor='A1', day='2026-05-01')
        self.assertEqual(both[0][1], None)
        self.assertEqual(drops['house_state_not_unique'], 1)


class SelfMentionTests(unittest.TestCase):
    def test_self_mentions_are_excluded_and_counted(self):
        rows = [dict(member='John Smith', date='2024-05-01', source='CREC', chamber='house',
                     text='John Smith rises. Mr. Smith also thanks Alice Alpha today.')]
        bundle = run(rows)
        targets = {m['target'] for m in bundle['mentions']}
        self.assertEqual(targets, {'A1'})
        self.assertEqual(bundle['manifest']['rows']['self_mention_excluded'], 2)


class CueAttributionTests(unittest.TestCase):
    def test_turn_level_output_matches_history_speech_nearest_cues(self):
        members = roster_fixture()
        variants, pattern = name_matcher(members)
        texts = [
            'I thank my good friend Bob Beta for the work, and Alice Alpha spoke too.',
            'Alice Alpha and Bob Beta were both here; my dear friend deserves the credit.',
            'Bob Beta is a liar, and Alice Alpha knows it.',
            'Nothing here names anybody at all.',
            'Eve Epsilon has a friendship with Dave Delta and my best friend Bob Beta.',
        ]
        for text in texts:
            normal = clean(text)
            mentions = [(m.start(), m.end(), variants[m.group()])
                        for m in pattern.finditer(normal) if variants[m.group()] != 'A1']
            flags = cues_by_mention(normal, mentions)
            mine = {}
            for (_s, _e, target), flag in zip(mentions, flags):
                mine.setdefault(target, set()).update(flag & {'warm', 'hostile'})
            mine = {k: v for k, v in mine.items() if v}
            _targets, hits = nearest_cues(text, 'A1', variants, pattern)
            self.assertEqual(mine, {k: v for k, v in hits.items() if v}, text)

    def test_a_cue_equidistant_between_two_targets_is_not_attributed(self):
        # 'my good friend' sits at 11..25; the nearer mention wins.
        near = cues_by_mention('aaaaaaaaaa my good friend cc ' + 'd' * 40 + ' bbbb',
                               [(0, 10, 'X'), (70, 74, 'Y')])
        self.assertEqual([{'warm'}, set()], near)
        # Here it is one character from each, so neither target is nearest alone.
        even = cues_by_mention('aaaaaaaaaa my good friend bbbb', [(0, 10, 'X'), (26, 30, 'Y')])
        self.assertEqual([set(), set()], even)

    def test_a_cue_beyond_160_characters_is_not_attributed(self):
        filler = 'z' * 200
        text = 'my good friend ' + filler + ' bbbb'
        self.assertEqual([set()], cues_by_mention(text, [(len(text) - 4, len(text), 'Y')]))


class TextMapTests(unittest.TestCase):
    def check(self, text, token):
        tm = TextMap(text)
        self.assertEqual(tm.cleaned, clean(text))
        at = tm.cleaned.index(token)
        start = tm.clean_to_orig(at)
        end = tm.clean_to_orig(at + len(token), end=True)
        self.assertEqual(clean(text[start:end]), token, (text, start, end))

    def test_ascii_offsets_round_trip(self):
        self.check('Mr.  Smith, hello there', 'mr smith')

    def test_non_ascii_offsets_round_trip(self):
        self.check('Señor Mr. Smith spoke', 'mr smith')          # one char folds to one
        self.check('a—b Mr. Smith spoke', 'mr smith')            # one char folds to none
        self.check('ﬁrst Mr. Smith spoke', 'mr smith')           # one char folds to two
        self.check('½ of Mr. Smith’s time', 'mr smith')

    def test_every_token_maps_back_on_random_text(self):
        rng = random.Random(7)
        alphabet = list('abcdefgh IJKL.,;-—éñﬁ½’  ')
        for _ in range(200):
            text = ''.join(rng.choice(alphabet) for _ in range(rng.randrange(1, 120)))
            tm = TextMap(text)
            self.assertEqual(tm.cleaned, clean(text))
            if not tm.mapped:
                continue
            at = 0
            for token in tm.cleaned.split(' '):
                if token:
                    start = tm.clean_to_orig(at)
                    end = tm.clean_to_orig(at + len(token), end=True)
                    self.assertEqual(clean(text[start:end]), token, (repr(text), token))
                at += len(token) + 1


class ReservoirTests(unittest.TestCase):
    def test_selection_depends_only_on_arrival_order_and_seed(self):
        plain, tagged = Reservoir(5, 'seed'), Reservoir(5, 'seed')
        for i in range(500):
            plain.offer(i)
            tagged.offer(('cue' if i % 3 == 0 else 'plain', i))
        self.assertEqual([x[1] for x in tagged.items], plain.items)

    def test_same_seed_same_draw(self):
        a, b = Reservoir(7, 'k'), Reservoir(7, 'k')
        for i in range(300):
            a.offer(i)
            b.offer(i)
        self.assertEqual(a.items, b.items)
        self.assertNotEqual(Reservoir(7, 'other').__class__, None)


class CalibrationTests(unittest.TestCase):
    def corpus(self, n=240, cue_every=3):
        rows = []
        for i in range(n):
            warm = 'my good friend ' if i % cue_every == 0 else ''
            rows.append(dict(member='Dave Delta', date='2024-%02d-%02d' % (i // 28 + 1, i % 28 + 1),
                             source='CREC', chamber='house', package='P%d' % i,
                             text=f'Turn {i}: I yield to {warm}Bob Beta on this matter.'))
        return rows

    def test_draw_is_cue_blind_and_deterministic(self):
        rows = self.corpus()
        first = run(rows)
        second = run(rows)
        self.assertEqual([r['mention_id'] for r in first['calibration']],
                         [r['mention_id'] for r in second['calibration']])
        self.assertEqual(len(first['calibration']), CALIBRATION_PER_STRATUM)
        population = [m for m in first['mentions']]
        rate = sum(m['cue_warm'] for m in population) / len(population)
        self.assertAlmostEqual(rate, 1 / 3, places=2)
        hidden = {h['mention_id']: h for h in first['hidden']}
        drawn = sum(hidden[r['mention_id']]['cue_warm'] for r in first['calibration'])
        drawn_rate = drawn / len(first['calibration'])
        self.assertGreater(drawn_rate, 0.10)
        self.assertLess(drawn_rate, 0.60)

    def test_cue_flags_are_not_in_the_review_file(self):
        first = run(self.corpus(n=60))
        for row in first['calibration']:
            self.assertNotIn('cue_warm', row)
            self.assertNotIn('cue_hostile', row)
            self.assertNotIn('cue_personal', row)
            self.assertEqual(row['review_status'], 'unreviewed')
            self.assertEqual(row['sampling_basis'], 'systematic_encounter_random_sample')
            self.assertIsNone(row['substantive_warmth'])
            self.assertIsNone(row['speech_purpose'])
        self.assertEqual({h['mention_id'] for h in first['hidden']},
                         {r['mention_id'] for r in first['calibration']})

    def test_strata_are_speaker_chamber_by_source(self):
        rows = self.corpus(n=10) + [
            dict(member='Bob Beta', date='2024-03-01', source='CREC', chamber='senate',
                 text='I yield to Dave Delta.'),
            dict(member='Bob Beta', date='2024-03-02', source='CHRG', chamber='senate',
                 text='I ask Dave Delta about this.'),
            dict(member='Dave Delta', date='2024-03-03', source='INTERVIEW', chamber='a-slug',
                 text='I spoke with Bob Beta last night.')]
        bundle = run(rows)
        strata = bundle['manifest']['calibration']['strata']
        self.assertEqual(strata['House|CREC']['frame'], 10)
        self.assertEqual(strata['Senate|CREC']['frame'], 1)
        self.assertEqual(strata['Senate|CHRG']['frame'], 1)
        self.assertEqual(strata['House|INTERVIEW']['frame'], 1)
        self.assertEqual(strata['House|CHRG']['frame'], 0)
        self.assertEqual(strata['Senate|INTERVIEW']['frame'], 0)
        self.assertEqual(sorted(strata), ['House|CHRG', 'House|CREC', 'House|INTERVIEW',
                                          'Senate|CHRG', 'Senate|CREC', 'Senate|INTERVIEW'])


class PacketTests(unittest.TestCase):
    def corpus(self, plain=60, cued=5):
        rows = []
        for i in range(plain):
            rows.append(dict(member='Dave Delta', date='2024-%02d-%02d' % (i // 28 + 1, i % 28 + 1),
                             source='CREC', chamber='house', package='P%d' % i,
                             text=f'Turn {i}: I yield to Bob Beta on this matter.'))
        for i in range(cued):
            rows.append(dict(member='Dave Delta', date='2025-01-%02d' % (i + 1), source='CREC',
                             chamber='house', package='W%d' % i,
                             text=f'Turn W{i}: my good friend Bob Beta deserves the credit.'))
        rows.append(dict(member='Bob Beta', date='2024-06-01', source='CREC', chamber='senate',
                         text='I thank Dave Delta for the work.'))
        return rows

    def pairs(self):
        return [pair_row('D1__B1', ('D1', 'B1'), ('Dave Delta', 'Bob Beta'))]

    def test_packet_cap_keeps_every_cue_flagged_row_first(self):
        bundle = run(self.corpus(), self.pairs())
        packet = bundle['packets'][0]
        direction = packet['directions']['D1->B1']
        self.assertEqual(len(direction['mentions']), PACKET_CAP)
        flagged = {m['mention_id'] for m in bundle['mentions']
                   if m['actor'] == 'D1' and m['target'] == 'B1'
                   and (m['cue_warm'] or m['cue_hostile'] or m['cue_personal'])}
        self.assertEqual(len(flagged), 5)
        chosen = [m['mention_id'] for m in direction['mentions']]
        self.assertTrue(flagged.issubset(set(chosen)))
        self.assertEqual(set(chosen[:5]), flagged)          # cue-flagged rows come first
        self.assertEqual(direction['hidden_cue_counts']['cue_flagged_mentions_available'], 5)
        self.assertEqual(direction['mention_total'], 65)

    def test_packet_mention_rows_carry_no_cue_information(self):
        bundle = run(self.corpus(), self.pairs())
        for packet in bundle['packets']:
            for direction in packet['directions'].values():
                self.assertIn('hidden_cue_counts', direction)
                # Nothing outside hidden_cue_counts may betray a cue hit, including
                # a frame size whose complement would give the flagged count away.
                self.assertEqual(set(direction) - {'hidden_cue_counts'},
                                 {'actor', 'target', 'mention_total', 'mention_by_source', 'mentions'})
                for row in direction['mentions']:
                    self.assertEqual(set(row), {'mention_id', 'date', 'source', 'package', 'context_650'})

    def test_packets_carry_no_work_or_model_fields(self):
        bundle = run(self.corpus(), self.pairs())
        text = (bundle['dir'] / 'development_pair_packets.ndjson').read_text(encoding='utf-8')
        for banned in ('cosponsor', 'affinity', 'antagonism', 'friction', 'propensity',
                       'jaccard', 'nominate', 'probability', 'score'):
            self.assertNotIn(banned, text.lower())

    def test_hearing_coappearances_are_reported(self):
        rows = self.corpus() + [
            dict(member='Dave Delta', date='2025-03-01', source='CHRG', chamber='house',
                 package='CHRG-1', text='I ask the witness about the bill.'),
            dict(member='Bob Beta', date='2025-03-01', source='CHRG', chamber='senate',
                 package='CHRG-1', text='I also ask the witness about the bill.')]
        bundle = run(rows, self.pairs())
        shared = bundle['packets'][0]['hearing_coappearances']
        self.assertEqual(shared['count'], 1)
        self.assertEqual(shared['packages'], [dict(package='CHRG-1', date='2025-03-01')])

    def test_heldout_pairs_are_rejected_and_never_packeted(self):
        held = pair_row('S1__E1', ('S1', 'E1'), ('John Smith', 'Eve Epsilon'), split='heldout')
        with self.assertRaises(ValueError):
            run(self.corpus(), self.pairs() + [held])
        bundle = run(self.corpus(), [p for p in self.pairs() + [held] if p['split'] == 'development'])
        text = (bundle['dir'] / 'development_pair_packets.ndjson').read_text(encoding='utf-8')
        self.assertNotIn('S1__E1', text)
        self.assertNotIn('heldout', text)
        self.assertEqual({p['split'] for p in bundle['packets']}, {'development'})

    def test_zero_mention_directions_are_counted_not_imputed(self):
        rows = [dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                     text='I yield to Bob Beta.')]
        bundle = run(rows, self.pairs())
        packets = bundle['manifest']['packets']
        self.assertEqual(packets['pairs_with_zero_mentions_in_at_least_one_direction'], 1)
        self.assertEqual(packets['pairs_with_zero_mentions_in_both_directions'], 0)
        reverse = bundle['packets'][0]['directions']['B1->D1']
        self.assertEqual(reverse['mention_total'], 0)
        self.assertEqual(reverse['mentions'], [])


class AggregateTests(unittest.TestCase):
    def test_denominator_arithmetic_is_reproducible_from_the_two_files(self):
        rows = [
            dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                 text='my good friend Bob Beta and also Alice Alpha are here.'),
            dict(member='Dave Delta', date='2024-05-02', source='CREC', chamber='house',
                 text='Alice Alpha spoke at length about the measure today.'),
            dict(member='Dave Delta', date='2024-05-03', source='CREC', chamber='house',
                 text='Nothing in this turn names a colleague at all.')]
        bundle = run(rows)
        baseline = {(r['actor'], r['source']): r for r in bundle['baseline']}[('D1', 'CREC')]
        counts = {(r['actor'], r['target'], r['source']): r for r in bundle['encounters']}
        self.assertEqual(baseline['total_turns'], 3)
        self.assertEqual(baseline['colleague_mention_turns'], 2)
        self.assertEqual(baseline['distinct_targets'], 2)
        self.assertEqual(baseline['target_mention_turn_sum'], 3)
        target = counts[('D1', 'B1', 'CREC')]
        other_n = baseline['target_mention_turn_sum'] - target['mention_turns']
        other_positive = baseline['target_warm_turn_sum'] - target['warm_turns']
        self.assertEqual((target['mention_turns'], target['warm_turns']), (1, 1))
        self.assertEqual((other_n, other_positive), (2, 0))
        from fec.research.member_personal_relationships.relative_expression import relative_contrast
        out = relative_contrast(target['mention_turns'], target['warm_turns'], other_n, other_positive)
        self.assertIsNotNone(out['contrast'])

    def test_duplicate_turns_and_mixed_voice_tails_follow_history_speech(self):
        duplicate = 'I yield to Bob Beta on this matter.'
        rows = [dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house', text=duplicate),
                dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house', text=duplicate),
                dict(member='Dave Delta', date='2024-05-02', source='INTERVIEW', chamber='slug',
                     text='I like Bob Beta. SOME OTHER HOST: and Alice Alpha is here too.')]
        bundle = run(rows)
        audit = bundle['manifest']['rows']
        self.assertEqual(audit['duplicate_turns_removed'], 1)
        self.assertEqual(audit['mixed_voice_tails_trimmed'], 1)
        self.assertEqual({m['target'] for m in bundle['mentions']}, {'B1'})

    def test_unresolved_speaker_rows_are_counted_not_attributed(self):
        rows = [dict(member='Someone Unlisted', date='2024-05-01', source='CREC', chamber='house',
                     text='I yield to Bob Beta.'),
                dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house', text='')]
        bundle = run(rows)
        audit = bundle['manifest']['rows']
        self.assertEqual(audit['unresolved_speaker_rows'], 1)
        self.assertEqual(audit['empty_text_rows'], 1)
        self.assertEqual(audit.get('source_rows', 0), 0)
        self.assertEqual(bundle['mentions'], [])
        self.assertEqual(bundle['manifest']['unresolved_speaker_names']['top'],
                         [dict(member='Someone Unlisted', rows=1)])


class OutputContractTests(unittest.TestCase):
    def test_mention_rows_expose_the_fields_the_expression_gate_needs(self):
        rows = [dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                     package='P1', text='my good friend Bob Beta spoke.')]
        bundle = run(rows)
        row = bundle['mentions'][0]
        for field in ('actor', 'target', 'date', 'venue', 'source', 'episode_id', 'source_family',
                      'cue_warm', 'cue_hostile', 'cue_personal', 'mention_id', 'window_240',
                      'window_650_sha256', 'turn_sha256', 'match_form', 'resolution',
                      'char_start', 'char_end', 'source_rowid'):
            self.assertIn(field, row)
        self.assertEqual(row['episode_id'], 'CREC:P1:2024-05-01')
        self.assertEqual(row['venue'], row['source'])
        self.assertTrue(row['cue_warm'])

    def test_window_policy_selected_keeps_windows_only_where_needed(self):
        rows = [dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                     text='I yield to Bob Beta.'),
                dict(member='Dave Delta', date='2024-05-02', source='CREC', chamber='house',
                     text='my good friend Bob Beta spoke.')]
        bundle = run(rows, window_policy='selected')
        windows = {m['date']: m['window_240'] for m in bundle['mentions']}
        self.assertIsNone(windows['2024-05-01'])
        self.assertIsNotNone(windows['2024-05-02'])
        self.assertIn('cue-flagged', bundle['manifest']['window_policy'])

    def test_report_names_a_denominator_and_carries_the_status_banner(self):
        bundle = run([dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                           text='I yield to Bob Beta.')])
        text = report_text(bundle['manifest'], [('systematic_encounters.ndjson', 1, 'ab')])
        self.assertTrue(text.startswith('**STATUS: EXPLORATORY.**'))
        self.assertIn('Share of mention rows', text)
        self.assertIn('Mention rows in frame', text)
        for causal in (' causes ', ' caused ', ' because of ', ' leads to ', ' drives '):
            self.assertNotIn(causal, text.lower())

    def test_mention_ids_are_stable_across_runs(self):
        rows = [dict(member='Dave Delta', date='2024-05-01', source='CREC', chamber='house',
                     text='my good friend Bob Beta spoke and Alice Alpha listened.')]
        first, second = run(rows), run(rows)
        self.assertEqual([m['mention_id'] for m in first['mentions']],
                         [m['mention_id'] for m in second['mentions']])
        self.assertEqual(len({m['mention_id'] for m in first['mentions']}), len(first['mentions']))


if __name__ == '__main__':
    unittest.main()
