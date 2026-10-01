"""Contracts for the fitted, anchor-supervised extension (written first)."""
import unittest
import numpy as np
from fec.research.member_personal_relationships.anchored_model import (
    Logistic, ResidualRanker, anchor_cases, fold_mask, rank_fraction,
)


def e(a, b, sign, family, **kw):
    return dict(actor=a, target=b, sign=sign, source_family=family,
                episode_id=family, event_date="2025-01-01", published_date="2025-01-01",
                category="personal_warmth" if sign=="positive" else "personal_hostility",
                attribution="direct_speaker", review_status="assistant_reviewed", **kw)


class AnchorContracts(unittest.TestCase):
    def test_mixed_signs_do_not_become_a_false_binary_gold_label(self):
        rows=[e("a","b","positive","one"),e("a","b","negative","two")]
        self.assertEqual(anchor_cases(rows,"2026-09-10"), [])

    def test_reciprocal_rows_share_one_holdout_unit(self):
        rows=[e("a","b","positive","one"),e("b","a","positive","two")]
        cases=anchor_cases(rows,"2026-09-10")
        self.assertEqual(len(cases),1)
        self.assertEqual(set(map(tuple,cases[0]["directions"])),{("a","b"),("b","a")})

    def test_unreviewed_unknown_and_future_do_not_become_training_labels(self):
        r=e("a","b","positive","one");r['review_status']='unreviewed'
        s=e("a","c","negative","two");s['published_date']='2027-01-01'
        self.assertEqual(anchor_cases([r,s],"2026-09-10"),[])

    def test_source_family_is_removed_globally_before_graph_construction(self):
        rows=[e("a","b","positive","one"),e("b","a","positive","two"),
              e("a","c","positive","one"),e("d","e","negative","three")]
        cases=anchor_cases(rows,"2026-09-10")
        held=next(c for c in cases if c['pair']==['a','b'])
        graph,train=fold_mask(rows,cases,held)
        self.assertEqual([(r['actor'],r['target']) for r in graph],[('d','e')])
        self.assertEqual([c['pair'] for c in train],[['d','e']])

    def test_family_connected_cases_are_excluded_transitively(self):
        rows=[e('a','b','positive','one'),e('a','c','positive','one'),
              e('a','c','positive','two'),e('c','d','positive','two'),
              e('x','y','negative','three')]
        cases=anchor_cases(rows,'2026-09-10')
        _,train=fold_mask(rows,cases,cases[0])
        self.assertEqual([c['pair'] for c in train],[['x','y']])

    def test_fit_learns_a_signal_instead_of_returning_fixed_weights(self):
        x=np.array([[-3.],[-2.],[-1.],[1.],[2.],[3.]])
        m=Logistic().fit(x,[0,0,0,1,1,1])
        self.assertGreater(m.predict([[2.]])[0],m.predict([[-2.]])[0])
        self.assertGreater(m.coefficients_[0],0)

    def test_test_rows_cannot_change_scaler_or_missing_value_imputer(self):
        m=Logistic().fit([[0,None],[2,4],[1,2],[3,None]],[0,1,0,1])
        before=m.mean_.copy();weights=m.coefficients_.copy()
        m.predict([[100000,-100000]])
        np.testing.assert_equal(before,m.mean_)
        np.testing.assert_equal(weights,m.coefficients_)

    def test_unknown_is_not_accepted_as_a_negative_gold_label(self):
        with self.assertRaises(ValueError): Logistic().fit([[0],[1]],[0,None])

    def test_context_alone_cannot_produce_a_residual_friendship_bonus(self):
        c=np.array([[0.],[0.],[1.],[1.]])
        m=ResidualRanker().fit(c,np.zeros((4,2)),[0,0,1,1])
        np.testing.assert_allclose(m.score([[0],[1]],[[0,0],[0,0]]),[0,0],atol=1e-12)

    def test_residual_ranker_learns_signal_orthogonal_to_context(self):
        c=np.array([[0],[0],[1],[1],[0],[1]])
        x=np.array([[-2],[2],[-2],[2],[-1],[1]])
        m=ResidualRanker().fit(c,x,[0,1,0,1,0,1])
        self.assertGreater(m.score([[0]],[[2]])[0],m.score([[0]],[[-2]])[0])

    def test_tied_retrieval_scores_do_not_count_as_perfect_recovery(self):
        rank,pct=rank_fraction(0,[0,0,0,0])
        self.assertEqual(rank,3)
        self.assertEqual(pct,.5)

    def test_unseen_motif_cannot_claim_support_from_positive_training_anchors(self):
        m=ResidualRanker().fit([[0],[0],[1],[1]],[[0,0],[0,1],[0,0],[1,0]],[1,0,1,0])
        np.testing.assert_equal(m.anchor_supported_,[False,False])

    def test_zeroing_an_unused_channel_has_no_fitted_contribution(self):
        m=ResidualRanker().fit([[0],[0],[1],[1]],[[-2,0],[2,0],[-2,0],[2,0]],[0,1,0,1])
        np.testing.assert_allclose(m.contribution([[0]],[[2,5]],[1]),[0])


if __name__=='__main__': unittest.main()
