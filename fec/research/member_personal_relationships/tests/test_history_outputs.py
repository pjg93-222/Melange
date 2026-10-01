import unittest
import numpy as np
from fec.research.member_personal_relationships.prepare_history import OUT
from fec.research.member_personal_relationships.run_history import load_all,read_rows
from fec.research.member_personal_relationships.data import read_json,ROOT,digest


@unittest.skipUnless((OUT/'results.json').exists(),'Full-history build required')
class HistoryOutputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.members,cls.traits,cls.ids,cls.w=load_all()
        cls.rows=read_rows(OUT/'relationships.ndjson')
        cls.events={e['evidence_id']:e for e in read_rows(OUT/'reviewed_events.ndjson')}

    def test_full_roster_panel(self):
        self.assertEqual(len(self.ids),532)
        self.assertEqual(self.w['shared'].shape,(532,532))
        manifest=read_json(OUT/'work_manifest.json')
        self.assertEqual(manifest['audit']['included_bills'],61085)
        self.assertEqual(manifest['ordered_pairs'],282492)

    def test_source_inputs_unchanged(self):
        for path,h in read_json(OUT/'work_manifest.json')['source_sha256'].items():
            self.assertEqual(digest(ROOT/path),h,path)

    def test_numerators_do_not_exceed_opportunities(self):
        w=self.w
        for num,den in [('direct','direct_opportunities'),('shared','shared_opportunities'),('shared','union')]:
            good=np.isfinite(w[num])&np.isfinite(w[den])
            self.assertTrue(np.all(w[num][good]<=w[den][good]+1e-5),(num,den))
        good=np.isfinite(w['shared'])
        self.assertTrue(np.all(w['shared_active'][good]<=w['shared'][good]))
        self.assertTrue(np.all(w['original_shared'][good]<=w['shared'][good]))

    def test_shared_symmetry_and_congress_reconciliation(self):
        w=self.w
        for k in ['shared','shared_active','weighted_jaccard','network_proximity']:
            np.testing.assert_allclose(w[k],w[k].T,atol=2e-5,equal_nan=True)
        expected=sum(w[f'c{c}_shared'] for c in range(116,120))
        np.fill_diagonal(expected,np.nan)
        np.testing.assert_equal(expected,w['shared'])

    def test_probabilities_not_fabricated_and_no_unreviewed_signs(self):
        for r in self.rows:
            self.assertIsNone(r['probability'])
            if r['hostility']!='unknown':
                self.assertTrue(any(self.events[k]['sign']=='negative' for k in r['evidence_ids']))
            if r['friendship'] in ['documented_personal_friendship','inferred_personal_affinity']:
                self.assertTrue(any(self.events[k]['sign']=='positive' for k in r['evidence_ids']))

    def test_speaker_baselines_have_valid_denominators(self):
        for r in read_rows(OUT/'speaker_usage.ndjson'):
            self.assertLessEqual(r.get('warm_turns',0),r['turns'])
            self.assertLessEqual(r.get('hostile_turns',0),r['turns'])
        for r in read_rows(OUT/'pair_rhetoric.ndjson'):
            self.assertLessEqual(r.get('warm_turns',0),r['mention_turns'])
            self.assertLessEqual(r.get('hostile_turns',0),r['mention_turns'])

    def test_dossier_independent_recounts_complete(self):
        receipt=read_json(OUT/'dossier_receipt.json')
        pairs={tuple(sorted((e['actor'],e['target']))) for e in self.events.values()}
        self.assertEqual(receipt['pairs'],len(pairs))
        self.assertTrue(receipt['independent_pair_recounts_passed'])
        for a,b in pairs:self.assertTrue((OUT/'pairs'/f'{a}__{b}.md').exists())


if __name__=='__main__':unittest.main()
