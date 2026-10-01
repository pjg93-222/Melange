import unittest
from fec.research.member_personal_relationships.relationship_spectrum import (
    summarize,context_grade,ANCHOR_GRADES,OUT,read_rows,read_json,digest,ROOT)


def event(id='e',episode='one',actor='a',target='b',affinity=None,tension=None):
    return dict(id=id,episode_id=episode,actor=actor,target=target,date='2025-01-01',
        affinity_grade=affinity,tension_grade=tension)


class SpectrumTests(unittest.TestCase):
    def test_warmth_and_tension_coexist_without_cancellation(self):
        r=summarize([event(affinity=3),event('f','two',tension=3)])
        self.assertEqual(r['affinity']['evidence_grade'],3)
        self.assertEqual(r['tension']['evidence_grade'],3)
        self.assertTrue(r['mixed_evidence']);self.assertIsNone(r['net_friend_vs_enemy_score'])

    def test_courtesy_does_not_create_closeness_or_dislike(self):
        r=context_grade(dict(id='new_review_44692'))
        self.assertIsNone(r[0]);self.assertIsNone(r[1]);self.assertIn('senate_floor_courtesy',r[2])
        self.assertIsNone(ANCHOR_GRADES['history-durbin_grassley_20211202-0'][0])
        self.assertEqual(context_grade(dict(id='new_review_60458'))[0],2)

    def test_duplicate_source_and_reverse_reply_do_not_create_repeat_episodes(self):
        r=summarize([event(affinity=3),event('duplicate',affinity=3),event('reply',actor='b',target='a',affinity=3)])
        self.assertEqual(r['affinity']['evidence_grade'],3)
        self.assertEqual(r['affinity']['independent_support_episodes'],1)
        self.assertEqual(len(r['affinity']['directions']),2)

    def test_no_invented_reciprocity_or_opposite_channel(self):
        r=summarize([event(tension=2)])
        self.assertIsNone(r['affinity']['evidence_grade'])
        self.assertEqual(r['tension']['directions'],[['a','b']])
        self.assertFalse(r['mixed_evidence'])

    def test_unknown_is_not_neutral_and_repetition_requires_qualifying_evidence(self):
        self.assertIsNone(summarize([event()])['affinity']['evidence_grade'])
        r=summarize([event(affinity=2),event('f','two',affinity=2)])
        self.assertEqual(r['affinity']['evidence_grade'],2)
        r=summarize([event(affinity=3),event('f','two',affinity=3)])
        self.assertEqual(r['affinity']['evidence_grade'],4)


class SpectrumOutputTests(unittest.TestCase):
    def test_record_hashes_no_probabilities_and_courtesy_application(self):
        receipt=read_json(OUT/'spectrum_receipt.json')
        for p,h in receipt['inputs'].items():self.assertEqual(digest(ROOT/p),h,p)
        self.assertFalse(receipt['regression_probabilities_used'])
        self.assertIsNone(receipt['graded_prediction_accuracy'])
        profiles=read_rows(OUT/'relationship_spectrum.ndjson')
        self.assertEqual(len(profiles),receipt['dyad_profiles'])
        ds=next(p for p in profiles if set(p['pair'])=={'D000563','S001184'})
        self.assertIsNone(ds['affinity']['evidence_grade'])
        self.assertEqual(ds['original_work']['shared_bills'],9)
        self.assertTrue(all(p['net_friend_vs_enemy_score'] is None for p in profiles))

    def test_all_context_evidence_is_development_and_never_predicts_itself(self):
        assignment=read_json(ROOT/'outputs/member_personal_relationships/20260910_frozen_v5/member_assignment.json')
        for e in read_rows(OUT/'exchange_context.ndjson'):
            self.assertFalse(e['used_in_regression'])
            self.assertEqual(assignment[e['actor']]['split'],'development')
            self.assertEqual(assignment[e['target']]['split'],'development')
        for r in read_rows(OUT/'graded_events.ndjson'):
            self.assertEqual(assignment[r['actor']]['split'],'development')
            self.assertEqual(assignment[r['target']]['split'],'development')

    def test_legacy_and_official_hearing_are_one_episode(self):
        profiles=read_rows(OUT/'relationship_spectrum.ndjson')
        mc=next(p for p in profiles if set(p['pair'])=={'M000194','C001130'})
        self.assertEqual(mc['tension']['independent_support_episodes'],1)
        self.assertEqual(mc['tension']['evidence_grade'],3)


if __name__=='__main__':unittest.main()
