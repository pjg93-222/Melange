import unittest
from fec.research.member_personal_relationships.freeze_v5 import OUT,HERE,read_json,digest,verify_lock
from fec.research.member_personal_relationships.run_history import read_rows


@unittest.skipUnless((OUT/'preparation_results.json').exists(),'prepare review artifacts first')
class PreparationOutputs(unittest.TestCase):
    def test_source_review_does_not_change_frozen_sample(self):
        self.assertEqual(verify_lock()['freeze_id'],read_json(OUT/'preparation_results.json')['freeze_id'])
        original=OUT.parent/'20260910_frozen_v5_partial_serialization/sampled_pairs.ndjson'
        if original.exists():
            self.assertEqual(digest(original),digest(OUT/'sampled_pairs.ndjson'))

    def test_review_receipts_reproduce_sources_and_decisions(self):
        retrieval=read_json(OUT/'development_retrieval_receipt.json')
        self.assertEqual(digest(OUT/'development_review_packets.ndjson'),retrieval['packets_sha256'])
        receipt=read_json(OUT/'preparation_receipt.json')
        self.assertEqual(digest(HERE/'v5_development_reviews.json'),receipt['decisions_sha256'])
        for name,h in receipt['derived_outputs'].items():
            self.assertEqual(digest(OUT/name),h,name)

    def test_distinct_broadcasts_cannot_double_one_friendship_episode(self):
        events=read_rows(OUT/'development_new_events.ndjson')
        self.assertEqual(len(events),1)
        event=events[0]
        self.assertEqual(event['independent_episode_count'],1)
        self.assertEqual(sorted(event['source_rowids']),[215949,215969])
        self.assertEqual(event['actor_name'],'Jamie Raskin')
        self.assertEqual(event['target_name'],'Tom Cole')
        self.assertIsNone(event['private_friendship_probability'])

    def test_compound_surname_mismatch_is_quarantined(self):
        q=read_rows(OUT/'identity_quarantine.ndjson')
        self.assertEqual(len(q),1)
        self.assertFalse(q[0]['target_verified'])
        self.assertEqual(q[0]['correct_target_name'],'Catherine Cortez Masto')
        self.assertNotEqual(q[0]['correct_target_id'],q[0]['target'])
        self.assertEqual(q[0]['affinity'],'unknown')
        self.assertFalse(q[0]['strict_signed_tie_eligible'])

    def test_quoted_insult_and_other_persons_story_cannot_label_focal_pair(self):
        rows={r['source_rowid']:r for r in read_rows(OUT/'development_reviewed_interactions.ndjson')}
        self.assertFalse(rows[238844]['personal_hostility'])
        for i in [17304,33706]:
            self.assertFalse(rows[i]['substantive_warmth'])
            self.assertEqual(rows[i]['affinity'],'unknown')
        for i in [215949,215969]:
            self.assertEqual(rows[i]['venue'],'COMMITTEE')

    def test_unobserved_baseline_cannot_produce_personality_multiplier(self):
        rows=read_rows(OUT/'development_expression_availability.ndjson')
        self.assertTrue(all(r['warmth']['contrast'] is None for r in rows))
        self.assertTrue(all(r['probability_of_sincerity'] is None for r in rows))
        self.assertFalse(any(r['actor_name']=='Jamie Raskin' for r in
            read_rows(OUT/'development_reviewed_interactions.ndjson') if r['actor'] in {x['actor'] for x in rows}))

    def test_preparation_is_not_reported_as_300_labeled_relationships(self):
        r=read_json(OUT/'preparation_results.json')
        self.assertEqual(r['sampled_pairs'],300)
        self.assertEqual(r['probability_sample_labels_reviewed'],0)
        self.assertEqual(r['models_refitted'],0)
        self.assertFalse(r['test_results_opened'])
        self.assertIsNone(r['new_accuracy'])


if __name__=='__main__':unittest.main()
