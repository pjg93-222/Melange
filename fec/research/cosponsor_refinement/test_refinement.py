"""Boundary tests for added evidence, graph semantics and shortlist selection."""
import datetime as dt
import unittest

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from member_network import centrality, exposure, NAMES
from verify_predecessors import body_tokens, compare
from build_extra_features import demographic_lookup, RELEASE_2022
from external_context import union_days, filing_available_day, staff_graph
from public_review import classify
from prospective import apply_outcomes, score
from influence_coverage import marginal_coverage, from_dates


class EvidenceTests(unittest.TestCase):
    def test_introduced_body_excludes_sponsor_metadata(self):
        def xml(name):
            return f'<bill bill-stage="Introduced-in-House"><form><sponsor>{name}</sponsor></form><legis-body><text>Require the bank to report 25 dollars.</text></legis-body></bill>'
        self.assertEqual(body_tokens(xml('Alice')),body_tokens(xml('Bob')))

    def test_later_version_rejected(self):
        with self.assertRaises(ValueError):body_tokens('<bill bill-stage="Enrolled"><legis-body>text</legis-body></bill>')

    def test_legal_numbers_preserved(self):
        a=['word']*50+['25'];b=['word']*50+['250']
        self.assertFalse(compare(a,b)['exact'])

    def test_tiny_text_not_verified(self):
        self.assertFalse(compare(['hello'],['hello'])['close'])

    def test_components_and_isolates(self):
        a=np.array([[0,1,0,0,0],[1,0,0,0,0],[0,0,0,2,0],[0,0,2,0,0],[0,0,0,0,0]],dtype=float)
        g=centrality(a)
        np.testing.assert_allclose(g['eigenvector'],[.5,.5,.5,.5,0])
        self.assertEqual(g['pagerank'][-1],0)
        self.assertEqual(g['isolate'][-1],1)

    def test_marginal_coverage_has_diminishing_returns(self):
        a=np.array([[0,1,0],[1,0,.5],[0,.5,0]],dtype=float)
        empty=marginal_coverage(a,[False,False,False])
        small=marginal_coverage(a,[True,False,False])
        large=marginal_coverage(a,[True,True,False])
        self.assertTrue((empty>=small).all());self.assertTrue((small>=large).all())
        self.assertTrue((large>=0).all());self.assertEqual(small[0],0)
        self.assertEqual(large[1],0)

    def test_marginal_coverage_excludes_future_and_same_day(self):
        a=np.array([[0,1],[1,0]],dtype=float)
        empty=from_dates(a,['A','B'],{},10)
        np.testing.assert_allclose(empty,from_dates(a,['A','B'],{'B':10},10))
        np.testing.assert_allclose(empty,from_dates(a,['A','B'],{'B':11},10))
        self.assertEqual(from_dates(a,['A','B'],{'B':9},10)[1],0)

    def test_post_forecast_peer_action_excluded(self):
        a=np.array([[0,1],[1,0]],dtype=float)
        g=dict(ids=['A','B'],index={'A':0,'B':1},adjacency=a,**centrality(a))
        future=exposure(g,{'B':20},10,'B',{'A':'D','B':'R'})
        same=exposure(g,{'B':10},10,'B',{'A':'D','B':'R'})
        past=exposure(g,{'B':9},10,'B',{'A':'D','B':'R'})
        j=NAMES.index('network_active_weight_share')
        self.assertEqual(future[0,j],0);self.assertEqual(same[0,j],0);self.assertEqual(past[0,j],1)

    def test_shared_staff_interval_union(self):
        self.assertEqual(union_days([(0,20),(10,30),(15,25),(40,50)]),40)

    def test_lobbying_uses_later_public_date(self):
        self.assertEqual(filing_available_day('2022-04-01','2022-04-15T00:00:00'),dt.date(2022,4,15).toordinal())

    def test_future_staff_history_excluded(self):
        row=dict(member_bioguide_id='A',start_latest='2021-02-01',end_earliest='2022-01-01',identity_status='ACCEPTED',container_status='ACCEPTED',resolved_person_id='P')
        a,p,c=staff_graph([row],117,['A']);self.assertEqual(c[0],0)

    def test_118_district_release_guard(self):
        r={'values':dict(population=100,median_age=40,median_household_income=50000,below_poverty=10,poverty_universe=100,renter_housing=20,occupied_housing=100)}
        data={(2022,'50000US0101'):r}
        before=demographic_lookup(data,118,RELEASE_2022-1,'AL',1,False)
        after=demographic_lookup(data,118,RELEASE_2022,'AL',1,False)
        self.assertEqual(before[-1],1);self.assertEqual(after[-1],0)

    def test_nc_boundary_guard(self):
        r={'values':dict(population=100,median_age=40,median_household_income=50000,below_poverty=10,poverty_universe=100,renter_housing=20,occupied_housing=100)}
        self.assertEqual(demographic_lookup({(2019,'50000US3701'):r},117,dt.date(2021,2,1).toordinal(),'NC',1,False)[-1],1)

    def test_intent_and_existing_sponsorship_distinguished(self):
        self.assertEqual(classify('I will cosponsor H.R. 123.','social','Smith'),'stated_future_intent')
        self.assertEqual(classify('I am a proud cosponsor of H.R. 123.','social','Smith'),'self_reported_existing_sponsorship')
        self.assertIsNone(classify('I want to know if you support H.R. 123.','hearing','Smith'))

    def test_prospective_scoring_refuses_immature_outcomes(self):
        from unittest.mock import patch
        with patch('prospective.read_json',return_value={'earliest_scoring_date':'2999-01-01'}):
            with self.assertRaisesRegex(RuntimeError,'pending'):score(None,None)

    def test_prospective_keeps_issued_ranks_and_censors_departures(self):
        frame=pd.DataFrame({'bill':['B']*3,'member':['A','C','D'],'model_rank':[1,2,9]})
        manifest={'forecast_date':'2026-09-05','outcome_start':'2026-09-06','outcome_end':'2026-10-05'}
        review={'complete_departure_review':True,'reviewed_through':'2026-10-05',
                'sources':['official source'],'last_serving_dates':{'C':'2026-09-20'}}
        result=apply_outcomes(frame,{'B':{'A':'2026-09-04','C':'2026-09-10','D':'2026-09-15'}},manifest,{'A','D'},review)
        self.assertTrue(result.late_reported_prior_signature.iloc[0])
        self.assertTrue(result.service_censored.iloc[1])
        self.assertEqual(result.model_rank.tolist(),[1,2,9])
        self.assertEqual(result.event.tolist(),[False,True,True])

    def test_prospective_departure_review_required(self):
        frame=pd.DataFrame({'bill':['B'],'member':['A']})
        manifest={'outcome_end':'2026-10-05'}
        with self.assertRaisesRegex(ValueError,'complete'):
            apply_outcomes(frame,{},manifest,{}, {})
        review={'complete_departure_review':True,'reviewed_through':'2026-10-05','sources':['official source']}
        with self.assertRaisesRegex(ValueError,'Unresolved'):
            apply_outcomes(frame,{},manifest,{},review)


if __name__=='__main__':
    with threadpool_limits(limits=1):unittest.main(verbosity=2)
