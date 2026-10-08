# -*- coding: utf-8 -*-
"""Kernel tests for the primacy tier + graduated conduct ladder. Add to fec/tests/run_tests.py.

Contract: primacy re-scores the DISPLAY tier only; the ladder only ever pushes a member DOWN; both fail open on a missing artifact and fail loud on a malformed one.
"""
import importlib, importlib.util, json, os, sys, tempfile, unittest
import primacy_factors as PF


def _load_consumer():
    """Resolve the consumer wherever it currently lives, so this suite runs both
    BEFORE integration (against `tier_util_primacy.patch.py`, the drop-in spec) and
    AFTER (against `fec/tier_util.py`, once the patch has been folded in)."""
    for name in ('tier_util', 'tier_util_primacy'):
        try:
            mod = importlib.import_module(name)
            if hasattr(mod, 'apply_conduct_ladder'):
                return mod
        except ImportError:
            pass
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'tier_util_primacy.patch.py')
    if not os.path.exists(path):
        raise ImportError('no consumer found: expected tier_util.apply_conduct_ladder, '
                          'tier_util_primacy, or tier_util_primacy.patch.py next to this file')
    spec = importlib.util.spec_from_file_location('tier_util_primacy', path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['tier_util_primacy'] = mod
    spec.loader.exec_module(mod)
    return mod


TU = _load_consumer()
load_primacy_factors = TU.load_primacy_factors
load_open_breaches   = TU.load_open_breaches
primacy_scores       = TU.primacy_scores
tier_ceiling         = TU.tier_ceiling
apply_conduct_ladder = TU.apply_conduct_ladder
CONDUCT_LADDER       = TU.CONDUCT_LADDER
BUCKETS              = getattr(TU, 'BUCKETS', (12, 24, 48))   # SIZES, matching tier_util L18


def bundle(*members):
    return {'members': list(members)}


def mem(name, *acts):
    return {'name': name, 'bills': [{'bill': b, 'congress': c, 'role': r} for b, c, r in acts]}


def tags(**kw):
    return {k: {'class': v} for k, v in kw.items()}


class ActWeights(unittest.TestCase):
    def test_weight_table_is_the_ratified_one(self):
        self.assertEqual(PF.ACT_W['cu_primary'], 1.0)
        self.assertEqual(PF.ACT_W['shared'], 0.5)
        self.assertEqual(PF.ACT_W['oppose'], -1.0)
        self.assertEqual(PF.ACT_W['offtopic'], 0.0)
        for k in ('bank_primary', 'crypto_primary', 'fintech'):
            self.assertEqual(PF.ACT_W[k], 0.15)

    def test_oppose_is_the_only_negative(self):
        self.assertEqual([k for k, v in PF.ACT_W.items() if v < 0], ['oppose'])

    def test_letters_use_the_letter_weight_not_their_class(self):
        t = {'LTR-119-X|119': {'class': 'shared'}}
        self.assertEqual(PF.act_weight(t['LTR-119-X|119'], 'LTR-119-X|119'), PF.LETTER_W)

    def test_unknown_class_raises(self):
        with self.assertRaises(ValueError):
            PF.act_weight({'class': 'nonsense'}, 'H.R.1|119')


class Factor(unittest.TestCase):
    def test_pure_cu_author_scores_one(self):
        m, _ = PF.compute(bundle(mem('A', ('H.R.1', '119', 'sponsor'))),
                          tags(**{'H.R.1|119': 'cu_primary'}))
        self.assertAlmostEqual(m['A']['factor_raw'], 1.0)

    def test_oppose_drags_the_factor_below_shared(self):
        t = {'H.R.1|119': {'class': 'cu_primary'}, 'H.R.2|119': {'class': 'oppose'}}
        m, _ = PF.compute(bundle(mem('A', ('H.R.1', '119', 'sponsor'), ('H.R.2', '119', 'sponsor'))), t)
        self.assertAlmostEqual(m['A']['factor_raw'], 0.0)

    def test_role_weights_are_applied(self):
        t = {'H.R.1|119': {'class': 'cu_primary'}, 'H.R.2|119': {'class': 'offtopic'}}
        m, _ = PF.compute(bundle(mem('A', ('H.R.1', '119', 'sponsor'), ('H.R.2', '119', 'cosponsor'))), t)
        self.assertAlmostEqual(m['A']['factor_raw'], 1.0 / 1.25)

    def test_shrink_pulls_thin_files_toward_baseline(self):
        t = {'H.R.1|119': {'class': 'cu_primary'}, 'H.R.2|119': {'class': 'shared'}}
        b = bundle(mem('Thin', ('H.R.1', '119', 'cosponsor')),
                   *[mem('Bulk%d' % i, *[('H.R.2', '119', 'sponsor')] * 20) for i in range(6)])
        m, base = PF.compute(b, t)
        self.assertEqual(m['Thin']['factor_raw'], 1.0)
        self.assertLess(m['Thin']['factor_shrunk'], m['Thin']['factor_raw'])
        self.assertGreater(m['Thin']['factor_shrunk'], base)

    def test_shrink_containment_always(self):
        t = {'H.R.1|119': {'class': 'cu_primary'}, 'H.R.2|119': {'class': 'oppose'}}
        m, base = PF.compute(bundle(mem('A', ('H.R.1', '119', 'sponsor')),
                                    mem('B', ('H.R.2', '119', 'sponsor'))), t)
        for v in m.values():
            self.assertTrue(min(v['factor_raw'], base) - 1e-9 <= v['factor_shrunk']
                            <= max(v['factor_raw'], base) + 1e-9)

    def test_member_with_no_acts_is_neutral(self):
        m, base = PF.compute(bundle(mem('Empty'), mem('A', ('H.R.1', '119', 'sponsor'))),
                             tags(**{'H.R.1|119': 'shared'}))
        self.assertEqual(m['Empty']['agenda_credit'], 0)
        self.assertAlmostEqual(m['Empty']['factor_shrunk'], base)   # lambda 0 -> exactly baseline

    def test_untagged_act_raises_rather_than_scoring_zero(self):
        with self.assertRaises(KeyError):
            PF.compute(bundle(mem('A', ('H.R.9', '119', 'sponsor'))), tags(**{'H.R.1|119': 'shared'}))

    def test_deterministic(self):
        t = tags(**{'H.R.1|119': 'cu_primary', 'H.R.2|119': 'shared'})
        b = bundle(mem('A', ('H.R.1', '119', 'sponsor')), mem('B', ('H.R.2', '119', 'original')))
        self.assertEqual(PF.compute(b, t), PF.compute(b, t))


class GateAndScoring(unittest.TestCase):
    def test_score_is_leg_times_factor(self):
        s = primacy_scores({'A': {'leg': 0.8}}, {'A': 0.5})
        self.assertAlmostEqual(s['A'], 0.4)

    def test_member_missing_from_factors_is_neutral_not_zero(self):
        s = primacy_scores({'A': {'leg': 0.8}}, {})
        self.assertAlmostEqual(s['A'], 0.8)

    def test_missing_artifacts_fail_open(self):
        self.assertEqual(load_primacy_factors('/nonexistent-root'), {})
        self.assertEqual(load_open_breaches('/nonexistent-root'), {})

    def test_malformed_primacy_artifact_raises(self):
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, 'primacy_factors.json'), 'w').write('{not json')
            with self.assertRaises(ValueError):
                load_primacy_factors(td)

    def test_effective_severity_sums_severity_times_leverage(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'grievance_ledger.ndjson'), 'w') as fh:
                for r in (
                    {'member': 'Andy Barr', 'severity': 3, 'leverage_mult': 1.75,
                     'status': 'open', 'event_id': 'MS-2026-002'},
                    {'member': 'Andy Barr', 'severity': 2, 'leverage_mult': 1.0,
                     'status': 'open', 'event_id': 'MS-2026-003'},
                    {'member': 'Cured', 'severity': 3, 'leverage_mult': 2.0,
                     'status': 'cured', 'event_id': 'X'},
                    {'member': 'NoMult', 'severity': 2, 'status': 'open', 'event_id': 'Y'},
                ):
                    fh.write(json.dumps(r) + '\n')
            b = load_open_breaches(td)
            self.assertAlmostEqual(b['Andy Barr']['effective_severity'], 7.25)
            self.assertNotIn('Cured', b)                     # cured events do not count
            self.assertAlmostEqual(b['NoMult']['effective_severity'], 2.0)   # missing mult -> 1.0

    def test_severity2_events_are_no_longer_free(self):
        """The 2026-07-28 draft consumed only severity>=3; sev-2 cost nothing."""
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, 'grievance_ledger.ndjson'), 'w') as fh:
                for i in range(2):
                    fh.write(json.dumps({'member': 'M', 'severity': 2, 'leverage_mult': 1.0,
                                         'status': 'open', 'event_id': 'E%d' % i}) + '\n')
            self.assertEqual(tier_ceiling(load_open_breaches(td)['M']['effective_severity']), 2)


class ConductLadder(unittest.TestCase):
    def test_buckets_are_sizes_not_cutoffs(self):
        """tier_util.BUCKETS is (12, 24, 48) SIZES. Passing cutoffs would put Tier 2 at slot 37."""
        order = ['M%02d' % i for i in range(90)]
        breaches = {'M01': {'effective_severity': 3.0, 'events': [('E', 3, 1.0)]}}
        final, _ = apply_conduct_ladder(order, breaches, (12, 24, 48))
        self.assertEqual(final.index('M01'), 12)        # first slot of Tier 2, from SIZES

    def test_ladder_thresholds(self):
        self.assertEqual(tier_ceiling(0.0), 1)
        self.assertEqual(tier_ceiling(2.99), 1)
        self.assertEqual(tier_ceiling(3.0), 2)
        self.assertEqual(tier_ceiling(5.99), 2)
        self.assertEqual(tier_ceiling(6.0), 3)
        self.assertEqual(tier_ceiling(8.99), 3)
        self.assertEqual(tier_ceiling(9.0), 0)

    def test_ladder_is_monotone(self):
        prev = 1
        for e in [x / 4.0 for x in range(0, 60)]:
            c = tier_ceiling(e)
            rank = {1: 0, 2: 1, 3: 2, 0: 3}
            self.assertGreaterEqual(rank[c], rank[prev])
            prev = c

    def test_ceiling_is_a_floor_on_slot_not_a_fixed_demotion(self):
        """A capped member re-enters at their OWN score position, not one tier down."""
        order = ['M%02d' % i for i in range(90)]
        breaches = {'M80': {'effective_severity': 6.0, 'events': [('E', 3, 2.0)]}}
        final, detail = apply_conduct_ladder(order, breaches, (12, 24, 48))
        self.assertEqual(detail['M80']['tier_ceiling'], 3)
        self.assertEqual(final.index('M80'), 80)        # already below slot 36: does not move

    def test_capped_member_lands_at_head_of_permitted_tier(self):
        order = ['M%02d' % i for i in range(90)]
        breaches = {'M01': {'effective_severity': 7.25, 'events': [('E', 3, 1.75)]}}
        final, _ = apply_conduct_ladder(order, breaches, (12, 24, 48))
        self.assertEqual(final.index('M01'), 36)        # first slot of Tier 3

    def test_ladder_never_promotes_and_preserves_the_roster(self):
        order = ['M%02d' % i for i in range(90)]
        breaches = {'M01': {'effective_severity': 7.25, 'events': [('E', 3, 1.75)]},
                    'M05': {'effective_severity': 3.0, 'events': [('E', 3, 1.0)]}}
        final, _ = apply_conduct_ladder(order, breaches, (12, 24, 48))
        self.assertEqual(sorted(final), sorted(order))              # permutation, nothing dropped
        for m in order:
            self.assertGreaterEqual(final.index(m), 0)
        self.assertGreaterEqual(final.index('M01'), order.index('M01'))   # only ever down
        self.assertGreaterEqual(final.index('M05'), order.index('M05'))
        for m in order:                                             # uncapped members only rise
            if m not in breaches:
                self.assertLessEqual(final.index(m), order.index(m))

    def test_untier_rung_removes_a_member_from_the_board(self):
        """eff >= 9 is `untiered`: the member is pushed past the last tiered slot."""
        order = ['M%02d' % i for i in range(90)]
        breaches = {'M73': {'effective_severity': 10.0, 'events': [('A', 3, 2.0), ('B', 2, 2.0)]}}
        final, detail = apply_conduct_ladder(order, breaches, (12, 24, 48))
        self.assertEqual(detail['M73']['tier_ceiling'], 0)
        self.assertGreaterEqual(final.index('M73'), 84)      # past the last Tier-3 slot
        self.assertEqual(final[:73], ['M%02d' % i for i in range(73)] )   # nobody above is disturbed

    def test_live_ledger_reproduces_the_two_known_cases(self):
        """Regression lock on the ledger of record. Update deliberately, never incidentally."""
        here = os.path.dirname(os.path.abspath(__file__))
        if not os.path.exists(os.path.join(here, 'grievance_ledger.ndjson')):
            self.skipTest('ledger not colocated')
        b = load_open_breaches(here)
        self.assertAlmostEqual(b['Andy Barr']['effective_severity'], 7.25)
        self.assertAlmostEqual(b['French Hill']['effective_severity'], 10.00)
        self.assertEqual(tier_ceiling(b['Andy Barr']['effective_severity']), 3)
        self.assertEqual(tier_ceiling(b['French Hill']['effective_severity']), 0)

    def test_ladder_counts_events_so_completeness_matters(self):
        """DOCUMENTED LIMITATION, asserted so nobody is surprised by it.

        Effective severity is a SUM over logged events, so a member with one logged
        event scores lower than an equally culpable member with two — the ladder
        measures the ledger, not the world. The mitigation is a completeness audit
        (for every logged vehicle, sweep every member with leverage over it), not a
        code change. This test exists to keep that property explicit."""
        one_bad_event  = {'effective_severity': 3 * 2.00, 'events': [('X', 3, 2.0)]}
        two_lesser     = {'effective_severity': 3 * 1.75 + 2 * 1.0, 'events': [('Y', 3, 1.75), ('Z', 2, 1.0)]}
        self.assertLess(one_bad_event['effective_severity'], two_lesser['effective_severity'])

    def test_empty_ledger_is_the_identity(self):
        order = ['A', 'B', 'C']
        final, detail = apply_conduct_ladder(order, {}, (12, 24, 48))
        self.assertEqual(final, order)
        self.assertEqual(detail, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
