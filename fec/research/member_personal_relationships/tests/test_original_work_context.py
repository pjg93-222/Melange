import unittest
import numpy as np
from fec.research.member_personal_relationships.original_work_context import (
    original_panel,replace_work_rows,specific_traits,OUT,MODELS,read_json,ROOT,digest)
from fec.research.member_personal_relationships.history_work import full_work,network_proximity
from fec.research.member_personal_relationships.regression import metrics
from fec.research.member_personal_relationships.freeze_v5 import verify_lock


class OriginalWorkTests(unittest.TestCase):
    def fixture(self):
        members={k:dict(terms=[dict(chamber='House',start='2025-01-03',end='2027-01-03')]) for k in 'abcd'}
        members['d']['terms'][0]['start']='2025-03-01'
        bill=dict(key='119:hr:1',congress=119,chamber='House',sponsor='a',introduced='2025-02-01',
            end='2027-01-03',area='Test',joins={'b':'2025-02-01','c':'2025-02-01','d':'2025-03-02'},
            original=['b'],withdrawals={'b':'2025-03-01'},size=3)
        return members,bill

    def compute(self,members,bills):
        panel,audit,excluded=original_panel(bills,members)
        ids,w,_,_=full_work(members,panel,progress=lambda *a,**k:None)
        w['network_proximity']=network_proximity(w,{})[0]
        return panel,ids,w,audit,excluded

    def test_flag_not_same_day_or_later_signature_controls_numerator(self):
        members,bill=self.fixture();panel,ids,w,audit,_=self.compute(members,[bill])
        self.assertEqual(panel[0]['joins'],{'b':'2025-02-01'})
        self.assertEqual(w['direct'][1,0],1)
        self.assertEqual(w['direct'][2,0],0)
        self.assertEqual(w['direct'][3,0],0)

    def test_late_entrant_has_no_introduction_opportunity(self):
        members,bill=self.fixture();_,ids,w,_,_=self.compute(members,[bill])
        self.assertEqual(w['direct_opportunities'][1,0],1)
        self.assertEqual(w['direct_opportunities'][3,0],0)
        self.assertTrue(np.isnan(w['direct_rate'][3,0]))

    def test_withdrawal_preserves_original_support_and_records_separately(self):
        members,bill=self.fixture();_,_,w,_,_=self.compute(members,[bill])
        self.assertEqual(w['direct'][1,0],1)
        self.assertEqual(w['withdrawn_direct'][1,0],1)

    def test_original_coalition_size_includes_nonroster_members(self):
        members,bill=self.fixture();bill['original']=['b','c','former'];bill['joins']['former']='2025-02-01'
        panel,_,w,_,_=self.compute(members,[bill])
        self.assertEqual(panel[0]['size'],3)
        self.assertEqual(w['weighted_shared'][1,2],.5)
        self.assertEqual(w['shared'][1,2],1)
        self.assertEqual(w['weighted_jaccard'][1,2],1)

    def test_no_original_bills_still_count_as_opportunities(self):
        members,bill=self.fixture();bill['original']=[]
        _,_,w,_,_=self.compute(members,[bill])
        self.assertEqual(w['direct_opportunities'][1,0],1)
        self.assertEqual(w['direct_rate'][1,0],0)

    def test_source_ineligible_original_is_disclosed(self):
        members,bill=self.fixture();bill['original'].append('d')
        _,_,_,_,excluded=self.compute(members,[bill])
        self.assertEqual(excluded,[dict(bill='119:hr:1',member='d',reason='not_eligible_at_introduction')])

    def test_every_work_channel_is_replaced_without_changing_other_controls(self):
        members,bill=self.fixture();_,ids,w,_,_=self.compute(members,[bill])
        row=replace_work_rows({('b','c'):dict(same_party=1,actor_A=-.7,direct_propensity=99)},ids,w)[('b','c')]
        self.assertEqual(row['direct_propensity'],w['direct_rate'][1,2]) if np.isfinite(w['direct_rate'][1,2]) else self.assertTrue(np.isnan(row['direct_propensity']))
        self.assertEqual(row['log_shared_bills'],0)
        self.assertEqual(row['actor_A'],-.7)
        self.assertEqual(row['same_party'],1)
        self.assertIn('issue_similarity',row);self.assertIn('network_proximity',row)

    def test_traits_missing_not_imputed_before_training(self):
        t={'a':dict(A=None,E=0,O=0),'b':dict(A=1,E=0,O=0)}
        row=specific_traits('a','b',t,.5)
        self.assertIsNone(row['joint_low_A']);self.assertIsNone(row['similarity_A_D'])
        self.assertEqual(row['joint_high_E'],.25)
        self.assertEqual(row['joint_high_E_D'],.125)


@unittest.skipUnless((OUT/'run_receipt.json').exists(),'run original work analysis first')
class OriginalWorkOutputTests(unittest.TestCase):
    def test_sources_and_frozen_test_unchanged(self):
        verify_lock();r=read_json(OUT/'run_receipt.json')
        for p,h in r['inputs'].items():self.assertEqual(digest(ROOT/p),h,p)
        self.assertFalse(r['test_outcomes_used'])
        self.assertTrue(read_json(OUT/'work_audit.json')['counts']['shared_original_reconciles_to_previous'])

    def test_complete_models_and_recomputed_metrics(self):
        results=read_json(OUT/'model_results.json');self.assertEqual(set(results),set(MODELS))
        for r in results.values():
            rows=r['predictions'];self.assertEqual(len(rows),29)
            self.assertEqual(metrics([v['y'] for v in rows],[v['p'] for v in rows]),r['metrics'])
        for r in read_json(OUT/'same_fit_auc.json').values():self.assertEqual(r['comparisons'],180)

    def test_outer_exclusions_and_development_only(self):
        cases=read_json(OUT/'cases.json')
        assignment=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
        self.assertTrue(all(assignment[a]['split']=='development' for c in cases for a in c['pair']))
        for r in read_json(OUT/'model_results.json').values():
            for i,p in enumerate(r['predictions']):
                for j in p['train_cases']:
                    self.assertFalse(set(cases[i]['pair'])&set(cases[j]['pair']))
                    self.assertFalse(set(cases[i]['families'])&set(cases[j]['families']))
        for r in read_json(OUT/'without_mace_crockett.json').values():
            self.assertEqual(r['metrics']['n'],28)
            self.assertTrue(all(not {'M000194','C001130'}&set(p['pair']) for p in r['predictions']))


if __name__=='__main__':unittest.main()
