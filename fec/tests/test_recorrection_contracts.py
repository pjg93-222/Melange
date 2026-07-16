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
    def test_opponent_cutoff_default_is_minus_1_2(self):
        # Paul-directed 2026-07-15: raise OVERALL_OPPONENT_CUTOFF from -1.60 to -1.20.
        txt = source("moneyball_core.py")
        m = re.search(r"OVERALL_OPPONENT_CUTOFF\s*=\s*float\(os\.environ\.get\('OVERALL_OPPONENT_CUTOFF','([^']+)'\)\)", txt)
        self.assertIsNotNone(m, "OVERALL_OPPONENT_CUTOFF env-default line not found")
        self.assertEqual(float(m.group(1)), -1.20)

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
