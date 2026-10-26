# -*- coding: utf-8 -*-
"""Lane SEL: deterministic network/archive source selection (no mtime).  Offline, tmp dirs only."""
import json, os, sys, tempfile, unittest
from pathlib import Path

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
import source_select as S  # noqa: E402

NET = 'congress_cosponsor_network_'
BASE_OLD, BASE_NEW = NET + '20260625_184604.xlsx', NET + '20260625_205554.xlsx'
AUG_OLD, AUG_NEW = NET + 'AUG20261011.xlsx', NET + 'AUG20261022.xlsx'
ARCH_OLD, ARCH_NEW = 'congress_bills_archive_20260624_115822.xlsx', 'congress_bills_archive_20260825_115305.xlsx'


def mk(d, names, mtime=1_000_000_000):
    out = []
    for n in names:
        p = Path(d) / n
        p.write_bytes(b'x')
        os.utime(p, (mtime, mtime))   # all mtimes tied
        out.append(str(p))
    return out


class SourceSelect(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory(); self.d = self._t.name
        self.addCleanup(self._t.cleanup)

    def test_mtime_tie_and_touched_older_file_do_not_matter(self):
        fs = mk(self.d, [BASE_OLD, BASE_NEW, AUG_OLD, AUG_NEW])
        before = S.select_network(fs, 'prefer'), S.select_network(fs, 'exclude'), S.select_network(fs, 'any')
        for old in (BASE_OLD, AUG_OLD):
            os.utime(Path(self.d) / old, (2_000_000_000, 2_000_000_000))   # touch an older file
        after = S.select_network(fs, 'prefer'), S.select_network(fs, 'exclude'), S.select_network(fs, 'any')
        self.assertEqual(before, after)
        self.assertEqual([os.path.basename(x) for x in after], [AUG_NEW, BASE_NEW, AUG_NEW])

    def test_filename_timestamp_ordering(self):
        fs = mk(self.d, [ARCH_NEW, ARCH_OLD, 'congress_bills_archive_20260825_090000.xlsx'])
        self.assertEqual(os.path.basename(S.select_archive(fs)), ARCH_NEW)
        # HHMMSS decides within a date; a no-timestamp name sorts lowest
        fs2 = mk(self.d, ['congress_bills_archive_current.xlsx'])
        self.assertEqual(os.path.basename(S.select_archive(fs + fs2)), ARCH_NEW)

    def test_tie_break_is_full_filename(self):
        fs = [str(Path(self.d) / n) for n in ('congress_bills_archive_20260101_000000_a.xlsx', 'congress_bills_archive_20260101_000000_b.xlsx')]
        self.assertTrue(S.select_archive(fs).endswith('_b.xlsx'))

    def test_aug_modes_match_old_intent(self):
        only_base = mk(self.d, [BASE_OLD, BASE_NEW])
        self.assertEqual(os.path.basename(S.select_network(only_base, 'prefer')), BASE_NEW)  # base only when no AUG
        with self.assertRaises(FileNotFoundError):
            S.select_network(mk(self.d, [AUG_NEW]), 'exclude')
        fs = mk(self.d, [AUG_NEW])
        self.assertEqual(os.path.basename(S.select_network(only_base + fs, 'prefer')), AUG_NEW)   # AUG beats a base
        self.assertEqual(os.path.basename(S.select_network(only_base + fs, 'exclude')), BASE_NEW)
        with self.assertRaises(FileNotFoundError):
            S.select_network([], 'prefer')

    def test_pin_overrides_and_fails_closed(self):
        fs = mk(self.d, [BASE_OLD, BASE_NEW, AUG_OLD, AUG_NEW, ARCH_OLD, ARCH_NEW])
        pins = Path(self.d) / 'data' / 'engine'; pins.mkdir(parents=True)
        (pins / 'source_pins.json').write_text(json.dumps({
            'congress_cosponsor_network': AUG_OLD, 'congress_cosponsor_network:base': BASE_OLD,
            'congress_bills_archive': ARCH_OLD}))
        nets = [f for f in fs if NET in f]; arcs = [f for f in fs if 'archive' in f]
        self.assertEqual(os.path.basename(S.select_network(nets, 'prefer', root=self.d)), AUG_OLD)
        self.assertEqual(os.path.basename(S.select_network(nets, 'any', root=self.d)), AUG_OLD)
        self.assertEqual(os.path.basename(S.select_network(nets, 'exclude', root=self.d)), BASE_OLD)
        self.assertEqual(os.path.basename(S.select_archive(arcs, root=self.d)), ARCH_OLD)
        (pins / 'source_pins.json').write_text(json.dumps({'congress_bills_archive': 'gone.xlsx'}))
        with self.assertRaises(FileNotFoundError):
            S.select_archive(arcs, root=self.d)

    def test_migrated_readers_call_helper(self):
        readers = ['moneyball_core.py', 'network/press_hcoi.py', 'network/press_engagement_layer.py',
                   'stance/stance_dynamics.py', 'members/persona_homophily_validate.py',
                   'surfaces/build_dashboard_bundle.py', 'network/build_multilayer_network.py',
                   'audit/audit_full.py', 'tools/identity_collision_census.py',
                   'legislation/vote_by_category.py', 'members/coop_v2_candidate.py',
                   'members/behavior_panel.py', 'members/behavioral_dispositions.py',
                   'legislation/build_archive_legislative.py', 'legislation/bill_coverage_audit.py',
                   'legislation/build_vote_category.py', 'legislation/bill_audit_console.py']
        for r in readers:
            src = (FEC / r).read_text(encoding='utf-8')
            self.assertIn('source_select', src, r)
            for line in src.splitlines():
                if ('congress_cosponsor_network_*' in line or 'congress_bills_archive_*' in line) and 'getmtime' in line:
                    self.fail('%s still selects by mtime: %s' % (r, line.strip()))
                if 'select_' in line and 'source_select' in line and ('congress_cosponsor_network_*' in line or 'congress_bills_archive_*' in line):
                    self.assertIn('root=', line, '%s helper call is not pin-aware: %s' % (r, line.strip()))

    def test_same_date_aug_beats_base_in_any(self):
        base_same = NET + '20261022_235959.xlsx'            # base stamped later the same day than the AUG
        fs = mk(self.d, [AUG_NEW, base_same, BASE_NEW])
        self.assertEqual(os.path.basename(S.select_network(fs, 'any')), AUG_NEW)
        fs = mk(self.d, [NET + 'AUG20261022_093000.xlsx', base_same])
        self.assertEqual(os.path.basename(S.select_network(fs, 'any')), NET + 'AUG20261022_093000.xlsx')
        nxt = mk(self.d, [NET + '20261023_000001.xlsx'])     # a later-DATE base still wins
        self.assertEqual(os.path.basename(S.select_network(fs + nxt, 'any')), os.path.basename(nxt[0]))
        self.assertEqual(os.path.basename(S.select_network(fs, 'exclude')), os.path.basename(base_same))

    def test_new_aug_timestamp_orders_against_old_aug_date(self):
        old, early, late = NET + 'AUG20261022.xlsx', NET + 'AUG20261022_090000.xlsx', NET + 'AUG20261022_170000.xlsx'
        nextday_old = NET + 'AUG20261023.xlsx'
        for fs, want in (([old, early], early), ([early, late, old], late), ([late, nextday_old], nextday_old)):
            self.assertEqual(os.path.basename(S.select_network(mk(self.d, fs), 'prefer')), want)

    def test_pin_beats_same_date_ordering(self):
        fs = mk(self.d, [AUG_NEW, NET + '20261022_235959.xlsx'])
        pins = Path(self.d) / 'data' / 'engine'; pins.mkdir(parents=True)
        (pins / 'source_pins.json').write_text(json.dumps({'congress_cosponsor_network': NET + '20261022_235959.xlsx'}))
        self.assertEqual(os.path.basename(S.select_network(fs, 'any', root=self.d)), NET + '20261022_235959.xlsx')


if __name__ == '__main__':
    unittest.main()
