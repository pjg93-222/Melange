"""A computed two-panel pass never promotes a trait above its owner-ratified evidence status."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @unittest.skipUnless((FEC.parent / 'source_data' / 'big5' / 'frozen_accepted_spec.json').exists(),
                         'frozen Big Five spec is local-only (source_data is not exported)')
    def test_producer_publishes_the_ratified_status_for_every_trait(self):
        # D-364 frozen correction: the producer publishes the frozen spec's accepted status; routine builds never promote.
        sys.path.insert(0, str(FEC))
        from members import b5_gold_multitrait_validate as model
        spec, _ = model.frozen_spec()
        roster = [{'member': 'Member %d' % i, 'bioguide': 'X%06d' % i, 'chamber': 'Senate'} for i in range(1, 7)]
        channels = {t: {c: {r['member']: float(i) for i, r in enumerate(roster)} for c in a['selected_weights']}
                    for t, a in spec['traits'].items()}
        with patch.object(model, 'load', return_value={'members': roster}), \
             patch.object(model, 'raw_channels', return_value=channels), \
             patch.object(model, 'input_hashes', return_value={'input': 'unchanged'}):
            doc = model.build()
        published = {t: row['status'] for t, row in doc['traits'].items()}
        self.assertEqual(RATIFIED_STATUS, published)
        for trait, status in published.items():
            self.assertEqual(published_status(trait, status), status, trait)

    def test_audit_expects_the_same_map(self):
        source = (FEC / 'audit' / 'audit_full.py').read_text(encoding='utf-8')
        self.assertIn('from members.ratified_trait_status import RATIFIED_STATUS as _expected_status', source)


if __name__ == '__main__':
    unittest.main()
