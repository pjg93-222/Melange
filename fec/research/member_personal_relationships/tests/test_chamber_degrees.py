import unittest
import numpy as np
from fec.research.member_personal_relationships.ordinal_degrees import (
    ordinal_objective, OrdinalDegrees, training_indices, reviewed_display, weighted_metrics)
from fec.research.member_personal_relationships.chamber_work import temporal_features, chamber_at, term_on
from fec.research.member_personal_relationships.chamber_expression import matched_expression


class OrdinalTests(unittest.TestCase):
    def test_gradient_all_grades(self):
        rng = np.random.default_rng(41)
        z = rng.normal(size=(15, 6)); y = np.arange(15) % 5
        w = rng.uniform(.2, 2, 15); reg = np.linspace(.2, 1, 6)
        p = np.r_[rng.normal(0,.4,6), -1.2, .1, -.3, .5]
        f, g = ordinal_objective(p,z,y,w,reg)
        numeric=[]
        for j in range(len(p)):
            d=np.zeros_like(p);d[j]=1e-5
            numeric.append((ordinal_objective(p+d,z,y,w,reg)[0]-ordinal_objective(p-d,z,y,w,reg)[0])/2e-5)
        np.testing.assert_allclose(g,numeric,rtol=1e-5,atol=1e-7)

    def test_predictive_distribution_and_signal(self):
        rng=np.random.default_rng(321)
        x=rng.normal(size=(220,1)); y=np.digitize(x[:,0]+rng.logistic(0,.3,len(x)),[-1,-.25,.25,1])
        model=OrdinalDegrees(.03,True).fit(x,y,['House']*110+['Senate']*110)
        p=model.predict_proba(np.array([[-2],[0],[2]]),['House']*3)
        np.testing.assert_allclose(p.sum(1),1,atol=1e-12)
        self.assertTrue((p>=0).all());self.assertTrue((np.diff(model.theta_)>0).all())
        self.assertTrue(np.all(np.diff(p@np.arange(5))>0))
        self.assertLess(model.gradient_norm_,2e-6)

    def test_unknown_is_not_zero(self):
        with self.assertRaises(ValueError):
            OrdinalDegrees().fit([[1],[2]],[None,2],['House']*2)
        self.assertEqual(reviewed_display(None,None),'unknown')
        self.assertEqual(reviewed_display(0,0),'graded_relationship')
        self.assertEqual(reviewed_display(0,0,True),'supported_neutral')
        self.assertEqual(reviewed_display(4,4),'mixed')
        self.assertEqual(reviewed_display(4,None),'partially_assessed')

    def test_only_training_data_used_for_scaling(self):
        m=OrdinalDegrees().fit([[1,np.nan],[3,2],[5,4]],[1,2,3],['House']*3)
        before=m.mean_.copy()
        p=m.predict_proba([[100000, np.nan]],['Senate'])
        np.testing.assert_array_equal(before,m.mean_)
        np.testing.assert_allclose(m.mean_,[3,3])
        self.assertTrue(np.isfinite(p).all())

    def test_missing_grade_regularized_but_disclosed(self):
        m=OrdinalDegrees().fit(np.empty((4,0)),[2,2,3,3],['Senate']*4)
        self.assertEqual(m.observed_grades_,[2,3])
        self.assertTrue((m.predict_proba(np.empty((1,0)),['Senate'])>0).all())

    def test_replication_with_equivalent_weights(self):
        x=np.array([[0],[1],[2]]);y=[1,2,3];c=['House']*3
        a=OrdinalDegrees().fit(x,y,c)
        b=OrdinalDegrees().fit(np.repeat(x,2,axis=0),np.repeat(y,2),c*2,np.ones(6)/2)
        np.testing.assert_allclose(a.predict_proba(x,c),b.predict_proba(x,c),atol=2e-6)

    def test_extreme_etas_stay_finite(self):
        z=np.array([[-1000.],[1000.],[1000.],[-1000.],[0.]])
        f,g=ordinal_objective(np.array([1.,-1.,0.,0.,0.]),z,np.arange(5),np.ones(5),np.ones(1))
        self.assertTrue(np.isfinite(f));self.assertTrue(np.isfinite(g).all())

    def test_member_and_transitive_source_exclusion(self):
        rows=[dict(pair=['a','b'],families=['f1']),dict(pair=['a','c'],families=['f2']),
              dict(pair=['d','e'],families=['f2','f3']),dict(pair=['f','g'],families=['f3']),
              dict(pair=['h','i'],families=['f4'])]
        self.assertEqual(training_indices(rows,0),[4])

    def test_correct_ordinal_score(self):
        p=np.eye(5)[[0,4]]
        m=weighted_metrics([0,4],p,[1,1])
        self.assertEqual(m['ranked_probability_score'],0)
        self.assertEqual(m['mean_absolute_grade_error'],0)


def member(terms):
    return dict(terms=[dict(start=s,end=e,chamber=c,party=p,state='AA') for s,e,c,p in terms])


class DatedWorkTests(unittest.TestCase):
    def setUp(self):
        self.members={
          'a':member([('2019-01-03','2021-01-03','House','Democrat'),('2021-01-03','2027-01-03','Senate','Democrat')]),
          'b':member([('2019-01-03','2027-01-03','House','Republican')]),
          's':member([('2019-01-03','2027-01-03','House','Democrat')]),
          'z':member([('2019-01-03','2027-01-03','Senate','Republican')])}

    def test_chamber_transition_and_boundary(self):
        self.assertEqual(chamber_at(self.members,'a','b','2020-01-01'),'House')
        self.assertEqual(chamber_at(self.members,'a','b','2021-01-03'),'cross_chamber')
        self.assertEqual(term_on(self.members['a'],'2021-01-03')['chamber'],'Senate')

    def test_original_only_strict_time_no_title_collapse(self):
        def bill(key,day,original,joins):
            return dict(key=key,chamber='House',sponsor='s',introduced=day,original=original,
                        joins=joins,withdrawals={'a':'2020-04-01'},area='Test',title='Same title')
        bills=[bill('1','2020-01-01',['a','b'],{'a':'2020-01-01','b':'2020-01-01'}),
               bill('2','2020-01-02',['a'],{'a':'2020-01-02','b':'2020-01-04'}),
               bill('3','2020-01-03',['a','b'],{'a':'2020-01-03','b':'2020-01-03'})]
        queries=[dict(id='old',actor='a',target='b',date='2018-12-01'),
                 dict(id='now',actor='a',target='b',date='2020-01-03'),
                 dict(id='later',actor='a',target='b',date='2020-02-01'),
                 dict(id='cross',actor='a',target='b',date='2022-01-01')]
        out,audit=temporal_features(self.members,bills,queries,lambda *a,**k:None)
        self.assertIsNone(out['old']['shared_original_bills'])
        self.assertEqual(out['now']['shared_original_bills'],1)
        self.assertEqual(out['later']['shared_original_bills'],2)
        self.assertAlmostEqual(out['now']['weighted_shared_jaccard'],.5)
        self.assertIsNone(out['cross']['shared_original_bills'])
        self.assertEqual(out['cross']['work_status'],'cross_chamber_structurally_unavailable')
        self.assertIsNone(out['now']['direct_propensity']) # b has introduced no bills

    def test_expression_requires_source_independence_and_comparable_exposure(self):
        def encounter(target,episode,warmth):
            return dict(actor='a',target=target,date='2020-01-01',venue='CREC',speech_purpose='ordinary',
                episode_id=episode,source_family=episode,review_status='context_reviewed',
                sampling_basis='systematic_encounter_review',speaker_verified=True,target_verified=True,
                quoted_only=False,content_status='resolved',substantive_warmth=warmth,personal_hostility=False)
        assessment=dict(id='x',actor='a',target='b',date='2020-02-01',venue='CREC',purpose='ordinary',families=['outcome'])
        exposures=[encounter('b','prior',True),encounter('s','other',False),encounter('b','outcome',True)]
        traits={'a':{'E':0.,'A':-1.}}
        result=matched_expression(exposures,[assessment],self.members,traits)[0]
        self.assertEqual(result['target_encounters'],1)
        self.assertEqual(result['other_encounters'],1)
        self.assertGreater(result['warmth']['contrast'],0)
        self.assertEqual(result['warmth_x_E'],0.)
        self.assertLess(result['warmth_x_A'],0.) # signed covariate, not a sincerity boost
        for r in exposures:r['sampling_basis']='cue_enriched'
        result=matched_expression(exposures,[assessment],self.members,traits)[0]
        self.assertIsNone(result['warmth']['contrast'])
        exposures[0]['sampling_basis']='systematic_encounter_review'
        exposures[1]['sampling_basis']='systematic_encounter_review'
        exposures[1]['speech_purpose']='tribute'
        result=matched_expression(exposures,[assessment],self.members,traits)[0]
        self.assertIsNone(result['warmth']['contrast'])


if __name__=='__main__':
    unittest.main()
