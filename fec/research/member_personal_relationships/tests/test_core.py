"""Behavioral contracts written before the relationship prototype implementation."""
import unittest

from fec.research.member_personal_relationships.core import (
    accepted_events, collapse_episodes, eligible_join, graph_features,
    personality_features, relationship_summary, residual_support,
)


def event(sign="positive", **changes):
    row = dict(actor="a", target="b", sign=sign, category="personal_warmth",
               event_date="2026-01-01", published_date="2026-01-02",
               episode_id="e1", source_family="s1", review_status="assistant_reviewed",
               attribution="direct_speaker", naturalness="unknown", evidence_id="one")
    row.update(changes)
    return row


class EvidenceTests(unittest.TestCase):
    def test_policy_and_courtesy_are_not_personal_seeds(self):
        rows = [event(category="policy"), event(category="courtesy"),
                event(category="professional_respect")]
        self.assertEqual(accepted_events(rows, "2026-09-10"), [])

    def test_missing_and_future_dates_are_not_current_evidence(self):
        rows = [event(event_date=None), event(event_date="2027-01-01"),
                event(published_date="2027-01-01"), event(event_date="garbage")]
        self.assertEqual(accepted_events(rows, "2026-09-10"), [])

    def test_machine_candidates_and_ambiguous_attribution_are_not_seeds(self):
        self.assertEqual(accepted_events([
            event(review_status="candidate"), event(attribution="unresolved"),
            event(actor="b"), event(sign="neutral")], "2026-09-10"), [])

    def test_copied_and_repeated_anecdotes_count_once(self):
        rows = [event(), event(evidence_id="copy", source_family="s2"),
                event(evidence_id="rerun", episode_id="e2"),
                event(evidence_id="independent", episode_id="e3", source_family="s3")]
        self.assertEqual(len(collapse_episodes(rows)), 2)

    def test_dedup_preserves_disagreement_and_direction(self):
        rows = [event(), event(sign="negative"), event(actor="b", target="a")]
        self.assertEqual(len(collapse_episodes(rows)), 3)

    def test_absence_is_unknown_and_scores_are_not_probabilities(self):
        result = relationship_summary("a", "b", [], {})
        self.assertEqual(result["affinity"], "unknown")
        self.assertEqual(result["antagonism"], "unknown")
        self.assertIsNone(result["affinity_probability"])
        self.assertIsNone(result["antagonism_probability"])

    def test_context_alone_never_earns_personal_score(self):
        x = relationship_summary("a", "b", [], dict(same_party=1, same_state=1,
                                                    nominate_distance=0, leadership=1))
        y = relationship_summary("a", "b", [], dict(same_party=0, same_state=0,
                                                    nominate_distance=2, leadership=0))
        self.assertEqual(x, y)

    def test_both_signs_and_reciprocity_are_separate(self):
        rows = [event(), event(sign="negative", category="personal_hostility")]
        result = relationship_summary("a", "b", rows, {})
        self.assertEqual(result["affinity"], "documented_provisional")
        self.assertEqual(result["antagonism"], "documented_provisional")
        self.assertEqual(result["evidence_status"], "contested_or_mixed")
        self.assertFalse(result["mutual_friendship"])
        reverse = relationship_summary("b", "a", rows, {})
        self.assertEqual(reverse["affinity"], "unknown")

    def test_indirect_signals_can_nominate_a_candidate_without_claiming_validation(self):
        result = relationship_summary("a", "b", [], dict(
            personality_similarity_eao=0.9, positive_resource_allocation=0.5,
            work_residual_rate=0.2, work_opportunities=20))
        self.assertGreater(result["affinity_candidate_score"], 0)
        self.assertEqual(result["affinity"], "indirect_candidate")
        self.assertEqual(result["model_status"], "exploratory_unfitted")
        self.assertIsNone(result["affinity_probability"])


class PersonalityTests(unittest.TestCase):
    def test_eao_similarity_changes_candidate_score(self):
        high = personality_features(dict(E=1, A=1, O=1), dict(E=1, A=1, O=1))
        low = personality_features(dict(E=1, A=1, O=1), dict(E=-1, A=-1, O=-1))
        self.assertGreater(high["personality_similarity_eao"], low["personality_similarity_eao"])
        self.assertGreater(relationship_summary("a", "b", [], high)["affinity_candidate_score"],
                           relationship_summary("a", "b", [], low)["affinity_candidate_score"])

    def test_missing_traits_are_missing_not_zero(self):
        result = personality_features(dict(E=None, A=None, O=None), dict(E=0, A=0, O=0))
        self.assertIsNone(result["personality_similarity_eao"])
        self.assertEqual(result["personality_traits_observed"], 0)

    def test_conscientiousness_and_neuroticism_do_not_imply_dislike(self):
        result = personality_features(dict(C=-2, N=-2), dict(C=2, N=2))
        self.assertIsNone(result["personality_similarity_eao"])
        out = relationship_summary("a", "b", [], result)
        self.assertEqual(out["antagonism"], "unknown")


class NetworkTests(unittest.TestCase):
    def test_holdout_removes_both_directions_before_all_features(self):
        edges = [event(), event(actor="b", target="a"),
                 event(actor="a", target="c"), event(actor="c", target="b")]
        masked = graph_features(edges, "a", "b", holdout_pair=True)
        explicit = graph_features(edges[2:], "a", "b", holdout_pair=False)
        self.assertEqual(masked, explicit)
        self.assertEqual(masked["positive_shortest_path"], 2)

    def test_shared_enemy_is_feature_not_friendship_rule(self):
        edges = [event(actor="a", target="c", sign="negative", category="personal_hostility"),
                 event(actor="b", target="c", sign="negative", category="personal_hostility")]
        features = graph_features(edges, "a", "b")
        self.assertEqual(features["signed_motifs"]["out_out_--"], 1)
        result = relationship_summary("a", "b", [], features)
        self.assertEqual(result["affinity"], "unknown")
        self.assertEqual(result["antagonism"], "unknown")

    def test_personal_graph_rejects_group_coattendance_and_unreviewed_edges(self):
        edges = [event(actor="a", target="c", category="coattendance"),
                 event(actor="c", target="b", review_status="candidate")]
        self.assertIsNone(graph_features(edges, "a", "b")["positive_shortest_path"])

    def test_hub_overlap_is_downweighted(self):
        base = [event(actor="a", target="c"), event(actor="b", target="c")]
        hub = base + [event(actor=f"x{i}", target="c") for i in range(10)]
        self.assertGreater(graph_features(base, "a", "b")["positive_resource_allocation"],
                           graph_features(hub, "a", "b")["positive_resource_allocation"])


class WorkTests(unittest.TestCase):
    def test_thirty_day_boundary_and_right_censoring(self):
        self.assertEqual(eligible_join("2026-01-01", "2026-01-31", "2026-02-01"), 1)
        self.assertEqual(eligible_join("2026-01-01", "2026-02-01", "2026-02-01"), 0)
        self.assertIsNone(eligible_join("2026-01-01", None, "2026-01-20"))
        self.assertEqual(eligible_join("2026-01-01", None, "2026-02-01"), 0)

    def test_residual_does_not_reward_raw_volume_or_create_hostility(self):
        a = residual_support(9, [0.9] * 10)
        b = residual_support(5, [0.1] * 10)
        self.assertAlmostEqual(a["work_residual_rate"], 0)
        self.assertGreater(b["work_residual_rate"], a["work_residual_rate"])
        low = residual_support(0, [0.9] * 10)
        self.assertEqual(relationship_summary("a", "b", [], low)["antagonism"], "unknown")

    def test_no_opportunity_is_not_negative_observation(self):
        result = residual_support(0, [])
        self.assertIsNone(result["work_residual_rate"])
        self.assertEqual(result["work_opportunities"], 0)


if __name__ == "__main__":
    unittest.main()
