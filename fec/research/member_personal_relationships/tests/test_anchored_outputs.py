"""Adversarial checks on the fitted pilot and its published claims."""
import unittest
from fec.research.member_personal_relationships.data import ROOT,read_json,digest
from fec.research.member_personal_relationships.run import read_lines
from fec.research.member_personal_relationships.anchored_model import fold_mask

OUT=ROOT/'outputs/member_personal_relationships/20260910_anchored'


@unittest.skipUnless((OUT/'results.json').exists(),'Build the anchored pilot first')
class FittedOutputContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events=read_lines(OUT/'anchor_events.ndjson')
        cls.cases=read_json(OUT/'anchor_cases.json')
        cls.rows=read_lines(OUT/'relationships.ndjson')
        cls.results=read_json(OUT/'results.json')

    def test_heldout_sources_and_both_directions_are_absent(self):
        for held in self.cases:
            graph,train=fold_mask(self.events,self.cases,held)
            self.assertTrue(all(sorted([e['actor'],e['target']])!=held['pair'] for e in graph))
            self.assertTrue(all(not set(held['families'])&set(c['families']) for c in train))

    def test_unknown_pairs_not_assumed_enemy_and_no_fake_probability(self):
        for r in self.rows:
            self.assertIsNone(r['affinity_probability'])
            self.assertIsNone(r['antagonism_probability'])
            if r['antagonism_status']=='inferred_antagonism_candidate':
                self.assertTrue(r['antagonism_observed_supported_network'])
                self.assertGreater(r['antagonism_network_contribution'],0)

    def test_empty_work_cannot_create_a_personal_dislike(self):
        for r in self.rows:
            if not r['negative_episodes'] and not r['antagonism_observed_supported_network']:
                self.assertEqual(r['antagonism_status'],'unresolved')

    def test_source_copies_do_not_become_independent_friendship_events(self):
        own=[e for e in self.events if e['actor_name']=='Katie Britt' and e['target_name']=='John Fetterman']
        self.assertEqual(len(own),2)  # 2024 speech plus 2026 NBC episode, not three website pages
        self.assertEqual(len({e['source_family'] for e in own}),2)

    def test_graph_has_no_unreviewed_mining_hits_or_predicted_edges(self):
        self.assertTrue(all(e['review_status']=='assistant_reviewed' for e in self.events))
        self.assertFalse(any(e['evidence_id'].startswith('db-') for e in self.events))
        self.assertEqual(len(self.events),self.results['reviewed_evidence_rows'])

    def test_case_predictions_count_pairs_not_reciprocal_edges(self):
        predictions=read_lines(OUT/'heldout_sign_predictions.ndjson')
        self.assertEqual(len(predictions),len(self.cases))
        self.assertEqual(len({tuple(r['pair']) for r in predictions}),len(self.cases))

    def test_current_inputs_unchanged(self):
        m=read_json(OUT/'manifest.json')
        for path,sha in m['inputs'].items(): self.assertEqual(digest(ROOT/path),sha,path)


if __name__=='__main__': unittest.main()
