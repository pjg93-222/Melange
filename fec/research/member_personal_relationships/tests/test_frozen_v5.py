import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import numpy as np
from fec.research.member_personal_relationships.freeze_v5 import (
    OUT, INPUT, ROOT, balanced_allocation, coverage_roster, split_members,
    draw_sample, personality_audit, verify_lock, stable_hash, read_json, digest,feature_communication)
from fec.research.member_personal_relationships.run_history import read_rows
from fec.research.member_personal_relationships.relative_expression import (
    relative_contrast, reviewed_expression, expression_features, leadership_tension)


def interaction(actor='a',target='b',episode='e1',**kw):
    return dict(actor=actor,target=target,episode_id=episode,date='2025-01-01',
                venue='CREC',source_family=episode,review_status='context_reviewed',
                speaker_verified=True,target_verified=True,quoted_only=False,
                content_status='resolved',substantive_warmth=True,personal_hostility=False)|kw


class ExpressionTests(unittest.TestCase):
    def test_sparse_target_evidence_is_shrunk_toward_speaker_baseline(self):
        sparse=relative_contrast(1,1,20,2)
        repeated=relative_contrast(10,10,20,2)
        self.assertGreater(sparse['contrast'],0)
        self.assertGreater(repeated['contrast'],sparse['contrast'])
        self.assertLess(sparse['target_rate'],1)

    def test_zero_target_or_comparison_opportunity_is_missing(self):
        self.assertIsNone(relative_contrast(0,0,10,2)['contrast'])
        self.assertIsNone(relative_contrast(1,1,0,0)['contrast'])

    def test_bad_counts_cannot_create_rates(self):
        for args in [(1,2,4,1),(1,1,0,1),(-1,0,1,0)]:
            with self.assertRaises(ValueError):relative_contrast(*args)

    def test_raw_cues_and_unresolved_targets_never_enter_baseline(self):
        rows=[interaction(),interaction(target='c',episode='e2'),
              interaction(episode='e3',review_status='unreviewed_retrieval_only'),
              interaction(episode='e4',target_verified=False),
              interaction(episode='e5',content_status='ambiguous')]
        out=reviewed_expression(rows,{})
        self.assertEqual(sum(r['counts']['n'] for r in out),2)

    def test_source_episode_and_date_purges_apply_to_other_target_baseline(self):
        rows=[interaction(),interaction(target='c',episode='e2'),
              interaction(target='d',episode='e3',source_family='outcome'),
              interaction(target='c',episode='e4',date='2026-01-01')]
        result=reviewed_expression(rows,{},excluded_episodes={'e2'},
                                  excluded_families={'outcome'},before='2026-01-01')
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['other_counts']['n'],0)
        self.assertIsNone(result[0]['warmth']['contrast'])

    def test_same_episode_repetition_does_not_increase_support(self):
        rows=[interaction(),interaction(),interaction(quoted_only=True),
              interaction(target='c',episode='e2',substantive_warmth=False)]
        r=reviewed_expression(rows,{'a':{'E':-1,'A':.5}})[0]
        self.assertEqual(r['counts']['n'],1)
        self.assertGreater(r['warmth']['contrast'],0)
        self.assertLess(r['warmth_x_E'],0)
        self.assertIsNone(r['reciprocal_warmth'])

    def test_ritual_can_be_reviewed_opportunity_without_substantive_warmth(self):
        rows=[interaction(substantive_warmth=False),interaction(target='c',episode='e2')]
        r=reviewed_expression(rows,{})[0]
        self.assertEqual(r['counts'],dict(n=1,warmth=0,hostility=0))

    def test_friendship_and_personal_hostility_can_coexist(self):
        rows=[interaction(personal_hostility=True),interaction(target='c',episode='e2',substantive_warmth=False)]
        r=reviewed_expression(rows,{})[0]
        self.assertEqual(r['counts']['warmth'],1)
        self.assertEqual(r['counts']['hostility'],1)

    def test_reciprocity_requires_actual_reverse_direction_and_baselines(self):
        rows=[interaction(),interaction(target='c',episode='e2',substantive_warmth=False),
              interaction(actor='b',target='a',episode='e3'),
              interaction(actor='b',target='c',episode='e4',substantive_warmth=False)]
        output=reviewed_expression(rows,{})
        self.assertGreater(next(r for r in output if r['target']=='b')['reciprocal_warmth'],0)

    def test_venue_missingness_is_not_zero_and_interactions_need_traits(self):
        out=reviewed_expression([interaction(),interaction(target='c',episode='e2',venue='INTERVIEW')],{})
        row=expression_features(out)[('a','b')]
        self.assertIsNone(row['relative_warmth'])
        self.assertIsNone(row['warmth_x_E'])
        self.assertEqual(row['relative_warmth_venue_n'],0)

    def test_leadership_explanation_requires_independent_inputs(self):
        self.assertIsNone(leadership_tension(True,None,1))
        self.assertEqual(leadership_tension(True,1,1),1.)
        self.assertEqual(leadership_tension(False,None,None),0.)
        self.assertEqual(leadership_tension(True,0,1),0.)


class SamplingTests(unittest.TestCase):
    def test_null_exposure_for_quiet_members_is_preserved_as_missing(self):
        source={'quiet':dict(raw_text={'interview_words':None},public_exposure=None)}
        result=feature_communication(source)
        self.assertEqual(result['quiet']['public_exposure'],{})
        self.assertIsNone(result['quiet']['raw_text']['interview_words'])
        self.assertIsNone(source['quiet']['public_exposure'])

    def test_capacity_and_total_preserved(self):
        self.assertEqual(balanced_allocation(8,{'a':1,'b':8,'c':8}),{'a':1,'b':4,'c':3})
        with self.assertRaises(ValueError):balanced_allocation(4,{'a':3})

    def test_missing_coverage_is_a_sampling_priority_not_an_observed_zero(self):
        members={str(i):dict(name=str(i),chamber='House',party='D',state='X') for i in range(4)}
        comm={str(i):dict(raw_text=dict(interview_words=v)) for i,v in enumerate([None,10,100,1000])}
        roster,_=coverage_roster(members,comm)
        self.assertEqual(roster['0']['coverage_tier'],'unrecorded')
        self.assertEqual(roster['0']['coverage_bucket'],'L')
        self.assertIsNone(roster['0']['interview_words'])

    def test_previous_members_never_enter_heldout_and_split_reproduces(self):
        roster={str(i):dict(coverage_bucket='L',chamber='House',party='D') for i in range(20)}
        first=split_members(roster,set(['0','1']),np.random.default_rng(42))
        second=split_members(json.loads(json.dumps(roster)),set(['0','1']),np.random.default_rng(42))
        self.assertEqual(first,second)
        self.assertEqual(first['0']['split'],'development')
        self.assertEqual(first['1']['split'],'development')
        self.assertEqual(sum(r['split']=='heldout' for r in first.values()),5)

    def test_changed_manifest_cannot_verify(self):
        with TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'x.json').write_text('{}',encoding='utf-8')
            lock=dict(inputs={},outputs={'x.json':digest(path/'x.json')})
            lock['freeze_id']=stable_hash(lock)
            (path/'freeze_manifest.json').write_text(json.dumps(lock),encoding='utf-8')
            verify_lock(path)
            (path/'x.json').write_text('{"changed":true}',encoding='utf-8')
            with self.assertRaises(ValueError):verify_lock(path)


@unittest.skipUnless((OUT/'freeze_manifest.json').exists(),'freeze sample first')
class FrozenOutputs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample=read_rows(OUT/'sampled_pairs.ndjson')
        cls.members=read_json(OUT/'member_assignment.json')
        cls.spec=read_json(OUT/'analysis_spec.json')

    def test_frozen_contract_hashes_verify(self):
        self.assertEqual(verify_lock()['version'],5)

    def test_draw_reproduces_exactly_without_outcome_inputs(self):
        from fec.research.member_personal_relationships.freeze_v5 import prior_evidence
        source=read_json(INPUT/'members.json')
        excluded,known,_=prior_evidence(source)
        roster=json.loads(json.dumps(self.members));rng=np.random.default_rng(20260910)
        split_members(roster,known,rng)
        result,_,_=draw_sample(roster,excluded,rng)
        self.assertEqual(result,self.sample)

    def test_sample_sizes_unique_pairs_and_half_low_endpoint_slots(self):
        self.assertEqual(len(self.sample),300)
        self.assertEqual(len({r['pair_id'] for r in self.sample}),300)
        self.assertEqual(sum(r['split']=='heldout' for r in self.sample),120)
        endpoints=[a for r in self.sample for a in r['pair']]
        self.assertEqual(sum(self.members[a]['coverage_bucket']=='L' for a in endpoints),300)

    def test_heldout_members_do_not_cross_into_any_development_arm(self):
        test={a for r in self.sample if r['split']=='heldout' for a in r['pair']}
        dev={a for r in self.sample if r['split']=='development' for a in r['pair']}
        dev.update(a for r in read_rows(OUT/'development_discovery_queue.ndjson') for a in r['pair'])
        dev.update(a for a,r in self.members.items() if r['prior_reviewed_member'])
        self.assertFalse(test&dev)

    def test_old_anchors_never_get_redrawn_as_fresh_labels(self):
        old={tuple(p) for p in self.spec['excluded_reviewed_pairs']}
        self.assertFalse(old&{tuple(r['pair']) for r in self.sample})
        self.assertTrue(all(r['affinity'] is None and r['antagonism'] is None for r in self.sample))

    def test_design_weights_recover_conditional_frame_cell_counts(self):
        for cell in read_json(OUT/'sampling_frame.json'):
            rows=[r for r in self.sample if r['split']==cell['split'] and r['stratum']==cell['stratum']]
            self.assertEqual(len(rows),cell['sample_n'])
            if rows:
                self.assertAlmostEqual(sum(r['design_weight'] for r in rows),cell['frame_n'])
                for r in rows:self.assertAlmostEqual(r['conditional_inclusion_probability']*r['design_weight'],1.)

    def test_traits_retain_true_support_levels_and_missingness(self):
        audit=read_json(OUT/'personality_gate_audit.json')['traits']
        self.assertTrue(all(r['retain_current_measure'] for r in audit.values()))
        self.assertEqual({t for t,r in audit.items() if r['two_panel_discriminant_support']},{'E','A'})
        self.assertLess(audit['A']['current_roster_observed'],audit['A']['current_roster_n'])
        self.assertTrue(all(not r['exact_relationship_source_purge_verified'] for r in audit.values()))

    def test_no_missing_expression_or_leadership_evidence_is_invented(self):
        rows=read_rows(OUT/'frozen_features.ndjson')
        self.assertTrue(all(r['relative_warmth'] is None for r in rows))
        self.assertTrue(all(r['leadership_tension'] is None for r in rows if r['same_party']))
        self.assertTrue(all(r['ideology_similarity'] is None or 0<r['ideology_similarity']<=1 for r in rows))

    def test_freeze_does_not_claim_new_regression_results(self):
        state=read_json(OUT/'readiness.json')
        self.assertEqual(state['models_fitted'],0)
        self.assertIsNone(state['regression_accuracy'])
        self.assertFalse(state['test_outcomes_opened'])


if __name__=='__main__':unittest.main()
