"""A computed two-panel pass never promotes a trait above its owner-ratified evidence status."""
import unittest
from pathlib import Path

from fec.members.ratified_trait_status import RATIFIED_STATUS, published_status

EXTERNAL = 'ACTIVE_EXTERNAL_GOLD_ANCHORED'
ONE_PANEL = 'ACTIVE_ONE_PANEL_ASSOCIATION_SUPPORTED'
WITHHELD = 'WITHHELD_FAILED_GATES'
FEC = Path(__file__).resolve().parents[2]


class RatifiedTraitStatusTests(unittest.TestCase):
    def test_computed_promotion_is_capped_at_the_ratified_level(self):
        self.assertEqual(RATIFIED_STATUS['O'], ONE_PANEL)
        self.assertEqual(published_status('O', EXTERNAL), ONE_PANEL)

    def test_ratified_external_and_any_demotion_publish_as_computed(self):
        self.assertEqual(published_status('E', EXTERNAL), EXTERNAL)
        self.assertEqual(published_status('E', ONE_PANEL), ONE_PANEL)
        self.assertEqual(published_status('O', WITHHELD), WITHHELD)

    def test_producer_publishes_capped_status_and_records_computed_status(self):
        source = (FEC / 'members' / 'b5_gold_multitrait_validate.py').read_text(encoding='utf-8')
        self.assertIn('"status": published_status(trait, status),', source)
        self.assertIn('"computed_status": status,', source)

    def test_audit_expects_the_same_map(self):
        source = (FEC / 'audit' / 'audit_full.py').read_text(encoding='utf-8')
        self.assertIn('from members.ratified_trait_status import RATIFIED_STATUS as _expected_status', source)


if __name__ == '__main__':
    unittest.main()
