"""Integration checks on actual pilot outputs; not relationship-accuracy tests."""
import unittest
from fec.research.member_personal_relationships.core import graph_features
from fec.research.member_personal_relationships.data import ROOT,digest,read_json
from fec.research.member_personal_relationships.run import read_lines

OUT=ROOT/"outputs/member_personal_relationships/20260910_pilot"


@unittest.skipUnless((OUT/"manifest.json").exists(),"Run the pilot before corpus integration checks")
class PilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=read_json(OUT/"manifest.json")
        cls.events=read_lines(OUT/"events.ndjson")
        cls.features=read_lines(OUT/"pair_features.ndjson")
        cls.relations=read_lines(OUT/"relationships.ndjson")

    def test_sources_and_production_still_match_frozen_hashes(self):
        for p,h in self.manifest["source_sha256"].items():
            self.assertEqual(digest(ROOT/p),h,p)
        for p,h in self.manifest["production_sha256"].items():
            self.assertEqual(digest(ROOT/p),h,p)

    def test_output_artifacts_match_receipt(self):
        for p,h in self.manifest["artifact_sha256"].items():
            self.assertEqual(digest(OUT/p),h,p)

    def test_160_unique_pairs_both_directions_no_self_edges(self):
        pairs={(r["actor"],r["target"]) for r in self.relations}
        self.assertEqual(len(pairs),320)
        self.assertTrue(all(a!=b and (b,a) in pairs for a,b in pairs))

    def test_wrong_al_green_and_carter_do_not_become_personal_ties(self):
        bad={"b49dc581f52f26f20923","db31d4c1a0c36d8b441b"}
        for r in self.relations:
            self.assertFalse(bad & set(r["evidence_ids"]))

    def test_no_unreviewed_rows_or_fake_probabilities(self):
        reviewed={e["evidence_id"] for e in self.events if e["category"]=="personal_warmth"}
        for r in self.relations:
            self.assertTrue(set(r["evidence_ids"])<=reviewed)
            self.assertIsNone(r["affinity_probability"])
            self.assertIsNone(r["antagonism_probability"])
            self.assertEqual(r["model_status"],"exploratory_unfitted")

    def test_current_seeds_are_not_their_own_network_predictors(self):
        for e in self.events:
            if e["category"]!="personal_warmth": continue
            f=graph_features(self.events,e["actor"],e["target"],as_of=self.manifest["as_of"])
            self.assertIsNone(f["positive_shortest_path"])

    def test_work_counts_are_bounded_and_baselines_explain_expected_counts(self):
        for f in self.features:
            self.assertLessEqual(f["work_observed"],f["work_opportunities"])
            self.assertLessEqual(f["work_opportunities"],f["work_total_opportunities"])
            self.assertGreaterEqual(f["work_expected"],0)
            self.assertLessEqual(f["work_expected"],f["work_opportunities"])
            expected=sum(a["opportunities"]*a["expected_rate"] for a in f["work_areas"] if a["expected_rate"] is not None)
            self.assertAlmostEqual(f["work_expected"],expected,places=5)


if __name__=="__main__":
    unittest.main()
