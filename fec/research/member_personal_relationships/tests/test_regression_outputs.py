import unittest
import numpy as np
from fec.research.member_personal_relationships.regression import (
    OUT, ROOT, read_json, digest, metrics, build_cases, matrices, MODELS, Fitter)
from fec.research.member_personal_relationships.run_history import read_rows


@unittest.skipUnless((OUT/'run_receipt.json').exists(),'run regression first')
class RegressionOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases=read_json(OUT/'cases.json');cls.results=read_json(OUT/'model_results.json')

    def test_primary_labels_do_not_include_weak_or_inferred(self):
        events=read_rows(OUT.parent/'20260910_full_history/reviewed_events.ndjson')
        expected=build_cases(events)
        self.assertEqual([c['pair'] for c in self.cases],[c['pair'] for c in expected])
        self.assertEqual((len(self.cases),sum(c['y'] for c in self.cases)),(29,20))

    def test_every_outer_fold_respects_sources_and_members(self):
        for name,models in self.results.items():
            for mode,result in models.items():
                for i,p in enumerate(result['predictions']):
                    held=self.cases[i]
                    self.assertNotIn(i,p['train_cases'])
                    for j in p['train_cases']:
                        train=self.cases[j]
                        self.assertFalse(set(held['families'])&set(train['families']))
                        if mode=='members':self.assertFalse(set(held['pair'])&set(train['pair']))

    def test_metrics_recompute_from_all_heldout_predictions(self):
        for models in self.results.values():
            for result in models.values():
                p=[r['p'] for r in result['predictions']]
                self.assertTrue(all(0<v<1 for v in p))
                self.assertEqual(metrics([c['y'] for c in self.cases],p),result['metrics'])

    def test_inputs_and_executed_code_unchanged(self):
        receipt=read_json(OUT/'run_receipt.json')
        for path,h in receipt['inputs'].items():self.assertEqual(digest(ROOT/path),h,path)
        self.assertEqual(digest(ROOT/'fec/research/member_personal_relationships/regression.py'),receipt['code_sha256'])

    def test_saved_fit_reproduces_coefficients(self):
        rows={(r['actor'],r['target']):r for r in read_json(OUT/'features.json')['composite']}
        fit=read_json(OUT/'coefficients.json');x=matrices(self.cases,MODELS['combined'],rows)
        model=Fitter(self.cases,x).fit(list(range(len(self.cases))),fit['model']['penalty'])
        np.testing.assert_allclose(model.beta_,fit['model']['beta'],atol=1e-10)
        self.assertLess(model.gradient_norm_,1e-7)

    @unittest.skipUnless((OUT/'same_fit_auc.json').exists(),'run ranking diagnostic first')
    def test_same_fit_comparison_purges_both_held_cases(self):
        for model,result in read_json(OUT/'same_fit_auc.json').items():
            self.assertEqual(result['comparisons'],180)
            for r in result['rows']:
                endpoints={a for i in [r['positive'],r['negative']] for a in self.cases[i]['pair']}
                families={f for i in [r['positive'],r['negative']] for f in self.cases[i]['families']}
                for j in r['train_cases']:
                    self.assertFalse(endpoints&set(self.cases[j]['pair']))
                    self.assertFalse(families&set(self.cases[j]['families']))

    @unittest.skipUnless((OUT/'expanded_controls_receipt.json').exists(),'run expanded-control check first')
    def test_expanded_models_and_rankings_use_same_cases_without_leakage(self):
        results=read_json(OUT/'expanded_controls_results.json')
        rankings=read_json(OUT/'expanded_controls_same_fit_auc.json')
        for name,models in results.items():
            for mode,result in models.items():
                self.assertEqual(len(result['predictions']),len(self.cases))
                p=[r['p'] for r in result['predictions']]
                self.assertEqual(metrics([c['y'] for c in self.cases],p),result['metrics'])
                for i,r in enumerate(result['predictions']):
                    for j in r['train_cases']:
                        self.assertFalse(set(self.cases[i]['families'])&set(self.cases[j]['families']))
                        if mode=='members':self.assertFalse(set(self.cases[i]['pair'])&set(self.cases[j]['pair']))
            self.assertEqual(rankings[name]['comparisons'],180)
            self.assertAlmostEqual(rankings[name]['auc'],np.mean([r['concordance'] for r in rankings[name]['rows']]))
            for r in rankings[name]['rows']:
                held=[self.cases[r['positive']],self.cases[r['negative']]]
                for j in r['train_cases']:
                    for c in held:
                        self.assertFalse(set(c['pair'])&set(self.cases[j]['pair']))
                        self.assertFalse(set(c['families'])&set(self.cases[j]['families']))


if __name__=='__main__':unittest.main()
