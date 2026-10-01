import unittest
import numpy as np
from fec.research.member_personal_relationships.regression import (
    RidgeLogit, build_cases, training_indices, metrics, nested_cv, coefficient_names)


def event(a,b,sign='positive',family='f',level='personal_statement'):
    return dict(actor=a,target=b,sign=sign,source_family=family,event_date='2020-01-01',
                evidence_level=level,review_status='assistant_reviewed',evidence_id=a+b+family)


class RegressionTests(unittest.TestCase):
    def test_contextual_unknown_and_conflicted_not_gold(self):
        events=[event('a','b'),event('b','a'),event('b','c',level='contextual_warmth'),
                event('c','d','unknown'),event('d','e'),event('d','e','negative','g')]
        cases=build_cases(events)
        self.assertEqual(len(cases),1)
        self.assertEqual(len(cases[0]['directions']),2)

    def test_weak_source_still_purged(self):
        cases=build_cases([event('a','b',family='f'),event('a','b',family='g',level='contextual_warmth'),
                           event('c','d',family='g'),event('d','e','negative','h')])
        self.assertEqual(training_indices(cases,0,'family'),[2])

    def test_transitive_sources_and_members(self):
        cases=build_cases([event('a','b',family='f'),event('c','d',family='f'),event('c','d',family='g'),
                           event('e','f','negative','g'),event('a','h','negative','h'),event('i','j','negative','i')])
        self.assertEqual(training_indices(cases,0,'family'),[1,4])
        self.assertEqual(training_indices(cases,0,'members'),[4])

    def test_imputation_is_training_only(self):
        m=RidgeLogit(.1).fit([[0,None],[2,None]],[0,1])
        np.testing.assert_allclose(m.mean_,[1,0])
        before=m.mean_.copy();m.predict([[100000,15]])
        np.testing.assert_array_equal(before,m.mean_)
        self.assertEqual(len(coefficient_names(['x','y'])),4)

    def test_recipient_weight_does_not_double_pair(self):
        a=RidgeLogit(.1).fit([[0],[1],[3]],[0,0,1],[1,1,1])
        b=RidgeLogit(.1).fit([[0],[0],[1],[3]],[0,0,0,1],[.5,.5,1,1])
        np.testing.assert_allclose(a.predict([[2]]),b.predict([[2]]),atol=1e-8)

    def test_signal_and_complete_separation_converge(self):
        x=np.arange(-10,11,dtype=float)[:,None];y=(x[:,0]>0).astype(float)
        m=RidgeLogit(.03).fit(x,y)
        self.assertLess(m.gradient_norm_,1e-7)
        self.assertGreater(metrics(y,m.predict(x))['auc'],.99)
        self.assertTrue(np.isfinite(m.beta_).all())

    def test_unknown_never_negative(self):
        with self.assertRaises(ValueError):RidgeLogit().fit([[0],[1]],[0,2])
        with self.assertRaises(ValueError):RidgeLogit().fit([[0],[1]],[1,1])

    def test_nested_folds_never_include_held_members(self):
        events=[event(str(i),str(i+20),'positive' if i%2 else 'negative',str(i)) for i in range(8)]
        cases=build_cases(events);x=[np.array([[i]],float) for i in range(8)]
        result=nested_cv(cases,x,'members',penalties=(.1,1.))
        self.assertEqual(result['metrics']['n'],8)
        for i,row in enumerate(result['predictions']):
            self.assertNotIn(i,row['train_cases'])
            for j in row['train_cases']:
                self.assertFalse(set(cases[i]['pair']) & set(cases[j]['pair']))

    def test_metrics_do_not_equate_accuracy_with_auc(self):
        m=metrics([0,0,1,1],[.6,.7,.8,.9])
        self.assertEqual(m['accuracy'],.5);self.assertEqual(m['auc'],1.)


if __name__=='__main__':unittest.main()
