import unittest
import numpy as np
from fec.research.member_personal_relationships.personality_context import (
    bipartisan_propensity,pair_similarity,interaction_features,moderation,OUT,MODELS,read_json,digest,ROOT)
from fec.research.member_personal_relationships.regression import metrics
from fec.research.member_personal_relationships.freeze_v5 import verify_lock


class MechanismTests(unittest.TestCase):
    def test_same_direction_of_traits_does_not_imply_identical_profiles(self):
        traits={'a':dict(E=.5,A=-.3,O=0.),'b':dict(E=2.3,A=-1.7,O=.1)}
        self.assertLess(pair_similarity('a','b',traits),.5)
        self.assertEqual(pair_similarity('a','a',traits),1.)

    def test_missing_traits_and_unknown_bipartisanship_remain_missing(self):
        self.assertIsNone(pair_similarity('a','b',{'a':dict(E=1,A=1,O=1),'b':dict(E=1,A=None,O=1)}))
        self.assertIsNone(interaction_features(.5,1,1,None)['S_D_B'])
        self.assertEqual(interaction_features(.5,1,1,None)['S_D'],.5)

    def fixture(self):
        ids=['a','partner','same','cross']
        members={k:{'party':p} for k,p in zip(ids,['Republican','Democrat','Republican','Democrat'])}
        w=dict(direct=np.zeros((4,4)),direct_opportunities=np.zeros((4,4)))
        w['direct'][0]=[0,99,10,10];w['direct_opportunities'][0]=[0,100,100,100]
        return ids,members,w

    def test_focal_partner_cannot_change_bipartisan_predictor(self):
        ids,members,w=self.fixture();before=bipartisan_propensity(0,1,ids,members,w)
        w['direct'][0,1]=0;w['direct_opportunities'][0,1]=9000
        self.assertEqual(before,bipartisan_propensity(0,1,ids,members,w))
        self.assertEqual(before['value'],.5)

    def test_bipartisanship_adjusts_for_bill_opportunities(self):
        ids,members,w=self.fixture();w['direct_opportunities'][0,3]=1000
        result=bipartisan_propensity(0,1,ids,members,w)
        self.assertLess(result['value'],.15)
        self.assertEqual(result['raw_cross_signature_share'],.5)

    def test_no_work_is_not_moderation_and_independents_are_not_recoded(self):
        ids,members,w=self.fixture();w['direct'][:]=0
        self.assertIsNone(bipartisan_propensity(0,1,ids,members,w)['value'])
        members['a']['party']='Independent'
        self.assertEqual(bipartisan_propensity(0,1,ids,members,w)['reason'],'independent_or_other_party_not_recoded')

    def test_three_way_interpretation_includes_lower_order_term(self):
        beta={'S_D':-2,'S_D_B':3}
        self.assertAlmostEqual(moderation(beta,'D',.2),-1.4)
        self.assertAlmostEqual(moderation(beta,'D',.8),.4)
        self.assertEqual(moderation({'S_P':-1},'P',.5),-1)


@unittest.skipUnless((OUT/'run_receipt.json').exists(),'run mechanism exploration first')
class MechanismOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=read_json(OUT/'cases.json');cls.results=read_json(OUT/'model_results.json')

    def test_no_new_test_members_or_modified_sources(self):
        verify_lock();receipt=read_json(OUT/'run_receipt.json')
        self.assertFalse(receipt['test_outcomes_used'])
        for p,h in receipt['inputs'].items():self.assertEqual(digest(ROOT/p),h,p)
        self.assertEqual(len(self.cases),29)
        assignment=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
        self.assertTrue(all(assignment[a]['split']=='development' for c in self.cases for a in c['pair']))

    def test_all_declared_models_and_metrics_are_reported(self):
        self.assertEqual(set(self.results),set(MODELS))
        for r in self.results.values():
            p=r['predictions'];self.assertEqual(metrics([x['y'] for x in p],[x['p'] for x in p]),r['metrics'])

    def test_outer_labels_and_ranking_exclude_every_held_endpoint(self):
        for r in self.results.values():
            for i,p in enumerate(r['predictions']):
                for j in p['train_cases']:
                    self.assertFalse(set(self.cases[i]['pair'])&set(self.cases[j]['pair']))
                    self.assertFalse(set(self.cases[i]['families'])&set(self.cases[j]['families']))
        for result in read_json(OUT/'same_fit_auc.json').values():
            self.assertEqual(result['comparisons'],180)
            for r in result['rows']:
                for i in [r['positive'],r['negative']]:
                    for j in r['train_cases']:
                        self.assertFalse(set(self.cases[i]['pair'])&set(self.cases[j]['pair']))
                        self.assertFalse(set(self.cases[i]['families'])&set(self.cases[j]['families']))

    def test_sensitivity_really_removes_motivating_members(self):
        for r in read_json(OUT/'without_mace_crockett.json').values():
            self.assertEqual(r['metrics']['n'],28)
            self.assertTrue(all(not {'M000194','C001130'}&set(p['pair']) for p in r['predictions']))


if __name__=='__main__':unittest.main()
