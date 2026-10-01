import json
import tempfile
import unittest
from pathlib import Path
import numpy as np
from fec.research.member_personal_relationships.history_work import (
    read_history, full_work, service_overlap, percentile, network_proximity)
from fec.research.member_personal_relationships.history_speech import name_matcher,nearest_cues
from fec.research.member_personal_relationships.run_history import assess,compatibility,personality_expression


def person(start='2019-01-03',chamber='House'):
    return dict(terms=[dict(start=start,end='2027-01-03',chamber=chamber)])


def bill(key, sponsor, joins, introduced='2019-01-03', title='Same title'):
    return dict(key=key, congress=116, type='hr', number=int(key.split(':')[-1]),
        introduced=introduced,chamber='House',sponsor=sponsor,
        cosponsors=[dict(member=a,date=d,original=False,withdrawn=None) for a,d in joins],
        titles=[dict(text=title,kind='Official Title as Introduced')],policy_area='Health',updated='2020-12-01')


class FullHistoryTests(unittest.TestCase):
    def prepare(self,rows,members):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bills.jsonl';p.write_text('\n'.join(json.dumps(r) for r in rows),encoding='utf-8')
            return read_history(p,members,'2026-09-10')

    def test_late_joins_reintroductions_and_canonical_dedup(self):
        b=bill('116:hr:1','s',[('a','2019-05-01')]); c=bill('116:hr:2','s',[('a','2019-06-01')])
        bs,a=self.prepare([b,b,c],{'a':person()})
        self.assertEqual(len(bs),2);self.assertEqual(a['joins_after_day_30'],2)
        self.assertEqual(a['duplicate_bill_records'],1)

    def test_member_can_join_bill_introduced_before_taking_seat(self):
        bs,_=self.prepare([bill('116:hr:1','s',[('a','2019-08-01')])],{'a':person('2019-07-01')})
        self.assertIn('a',bs[0]['joins'])
        self.assertTrue(service_overlap(person('2019-07-01'),'2019-01-03','2021-01-03','House'))

    def test_wrong_chamber_is_no_opportunity(self):
        self.assertFalse(service_overlap(person(chamber='Senate'),'2019-01-03','2021-01-03','House'))

    def test_service_end_is_exclusive(self):
        p=dict(terms=[dict(start='2019-01-03',end='2020-01-01',chamber='House')])
        self.assertFalse(service_overlap(p,'2020-01-01','2021-01-03','House'))

    def test_shared_cosponsorship_is_distinct_from_direct_support(self):
        members={a:person() for a in ['a','b','s']}
        bs,_=self.prepare([bill('116:hr:1','s',[('a','2019-02-01'),('b','2019-03-01')])],members)
        ids,w,_,_=full_work(members,bs,progress=lambda *a,**k:None)
        a,b,s=map(ids.index,['a','b','s'])
        self.assertEqual(w['shared'][a,b],1);self.assertEqual(w['direct'][a,b],0)
        self.assertEqual(w['direct'][a,s],1);self.assertEqual(w['shared_propensity'][a,b],1)
        self.assertEqual(w['shared'][a,s],0)

    def test_withdrawals_are_separate_from_initial_join(self):
        members={a:person() for a in ['a','b','s']}
        row=bill('116:hr:1','s',[('a','2019-02-01'),('b','2019-02-01')])
        row['cosponsors'][0]['withdrawn']='2019-03-01'
        bs,_=self.prepare([row],members);ids,w,_,_=full_work(members,bs,progress=lambda *a,**k:None)
        a,b,s=map(ids.index,['a','b','s'])
        self.assertEqual(w['shared'][a,b],1);self.assertEqual(w['shared_active'][a,b],0)
        self.assertEqual(w['withdrawn_direct'][a,s],1)

    def test_bill_after_cutoff_is_excluded(self):
        row=bill('116:hr:1','s',[],introduced='2026-09-11')
        bs,_=self.prepare([row],{'a':person()});self.assertEqual(bs,[])

    def test_small_match_groups_stay_missing(self):
        self.assertIsNone(percentile(1,[0,0,0,0]))
        self.assertEqual(percentile(1,[0,0,1,2,2]),.5)

    def test_direct_link_does_not_create_common_neighbor(self):
        a=np.array([[np.nan,1,0],[1,np.nan,0],[0,0,np.nan]],float)
        raw,_=network_proximity({'weighted_jaccard':a},{})
        self.assertTrue(np.isnan(raw[0,1]))

    def test_common_words_are_not_member_identities(self):
        variants,pattern=name_matcher({'a':{'name':'James Justice'},'b':{'name':'Todd Young'}})
        targets,_=nearest_cues('My friend is a strong young advocate for justice.','c',variants,pattern)
        self.assertEqual(targets,set())

    def test_qualified_member_name_survives_punctuation(self):
        variants,pattern=name_matcher({'a':{'name':'Tom Cole'},'b':{'name':'Steve Cohen'}})
        targets,cues=nearest_cues('Mr. Cole is my oldest friend.','c',variants,pattern)
        self.assertEqual(targets,{'a'});self.assertEqual(cues['a'],{'warm'})

    def test_personality_similarity_is_positive_compatibility(self):
        high=compatibility(dict(E=0,A=0,O=0),dict(E=0,A=0,O=0))
        low=compatibility(dict(E=0,A=0,O=0),dict(E=3,A=3,O=3))
        self.assertEqual(high['EAO_similarity'],1)
        self.assertGreater(low['EAO_similarity'],0)

    def test_rare_warmth_and_lower_EA_increase_distinctiveness(self):
        traits={'a':dict(E=-1,A=-1)}
        r=personality_expression('a',traits,{'a':dict(E=.1,A=.1)},[dict(turns=100,warm_turns=1)])
        s=personality_expression('a',traits,{'a':dict(E=.9,A=.9)},[dict(turns=100,warm_turns=1)])
        frequent=personality_expression('a',traits,{'a':dict(E=.1,A=.1)},[dict(turns=100,warm_turns=50)])
        self.assertGreater(r['reviewed_warmth_distinctiveness_multiplier'],s['reviewed_warmth_distinctiveness_multiplier'])
        self.assertGreater(r['reviewed_warmth_distinctiveness_multiplier'],frequent['reviewed_warmth_distinctiveness_multiplier'])

    def test_no_work_or_trait_mismatch_cannot_create_dislike(self):
        row=dict(work_flag=False,compatibility_support=False,network_percentile=0)
        result=assess(row,[],dict(reviewed_warmth_distinctiveness_multiplier=2))
        self.assertEqual(result['dislike'],'unknown');self.assertEqual(result['friendship'],'unknown')

    def test_contextual_warmth_combines_with_work_and_compatibility(self):
        row=dict(work_flag=True,compatibility_support=True,network_percentile=None)
        event=dict(sign='positive',evidence_level='contextual_warmth',source_family='x',event_date='2025-01-01',evidence_id='x')
        result=assess(row,[event],dict(reviewed_warmth_distinctiveness_multiplier=1))
        self.assertEqual(result['friendship'],'inferred_personal_affinity')

    def test_strong_work_does_not_erase_documented_hostility(self):
        row=dict(work_flag=True,compatibility_support=True,network_percentile=1)
        event=dict(sign='negative',dislike_inference=True,source_family='x',event_date='2025-01-01',evidence_id='x')
        result=assess(row,[event],dict(reviewed_warmth_distinctiveness_multiplier=1))
        self.assertEqual(result['hostility'],'documented_public_antagonism')
        self.assertEqual(result['dislike'],'inferred_personal_dislike_at_event')

    def test_single_cordial_phrase_does_not_promote_by_itself(self):
        row=dict(work_flag=False,compatibility_support=False,network_percentile=None)
        event=dict(sign='positive',evidence_level='contextual_warmth',source_family='x',event_date='2025-01-01',evidence_id='x')
        result=assess(row,[event],dict(reviewed_warmth_distinctiveness_multiplier=1))
        self.assertEqual(result['friendship'],'unknown')


if __name__=='__main__':unittest.main()
