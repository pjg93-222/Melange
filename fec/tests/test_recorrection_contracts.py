# -*- coding: utf-8 -*-
"""TDD contracts for the 2026-07-15 re-correction gated fixes (Paul-directed).
Kept dependency-light (source-text + kernel-import assertions) so they run in a clean runtime."""
from __future__ import annotations
import os, re, sys, unittest
from pathlib import Path
FEC = Path(__file__).resolve().parents[1]
ROOT = FEC.parent
sys.path.insert(0, str(FEC))
def source(name: str) -> str:
    return (FEC / name).read_text(encoding="utf-8-sig")


class DialContracts(unittest.TestCase):
    def test_overall_scale_shifted_and_ladder_monotonic(self):
        # Paul-directed 2026-07-15: SHIFT THE WHOLE OVERALL SCALE UP so the bottom rungs populate.
        # Contract: (1) Opponent cutoff = -1.10; (2) the band ladder is STRICTLY DESCENDING (a monotonic
        # ladder) so no tier is unreachable -- the bug where cutoff -1.20 sat ABOVE Skeptic -1.50 and
        # collapsed the Highly Skeptical band must never recur.
        import importlib
        MC = importlib.import_module("moneyball_core")
        self.assertEqual(MC.OVERALL_OPPONENT_CUTOFF, -1.10)
        cuts = [c for c, _ in MC.OVERALL_BANDS]
        self.assertEqual(cuts, sorted(cuts, reverse=True), "OVERALL_BANDS cutoffs must strictly descend")
        self.assertEqual(len(cuts), len(set(cuts)), "OVERALL_BANDS cutoffs must be distinct")
        # Highly Skeptical floor (== opponent cutoff) must sit BELOW the Skeptic floor
        skeptic = dict((t, c) for c, t in MC.OVERALL_BANDS)['Skeptic']
        self.assertLess(MC.OVERALL_OPPONENT_CUTOFF, skeptic)

    def test_cu_tax_status_is_defensive(self):
        # Paul-directed 2026-07-15: CU Tax Status is a defend-type fight -> DEFENSIVE weighting.
        txt = source("per_category_stance.py")
        m = re.search(r"DEFENSIVE\s*=\s*\{([^}]*)\}", txt)
        self.assertIsNotNone(m, "DEFENSIVE set literal not found")
        self.assertIn("CU Tax Status", m.group(1))


class StackContracts(unittest.TestCase):
    def test_tweet_classical_read_uses_classifier_class_order(self):
        # 3rd-pass S2: sklearn predict_proba columns are alphabetical (neutral,oppose,support,unrelated),
        # NOT CL order (support,oppose,neutral,unrelated); indexing pr's argmax into CL swaps neutral<->support
        # in classical_read + the tier weight. Must index the classifier's OWN classes_.
        txt = source("tweet_stance_stack.py")
        self.assertNotIn("clab = CL[int(np.argmax(pr))]", txt)
        self.assertIn("clab = pc.classes_[int(np.argmax(pr))]", txt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
