"""Modern renderer boundaries and existing advanced-engine route contracts."""
import hashlib
import json
import unittest

from module_workspace_clean_assets import ASSETS, ASSET_PROVENANCE
from module_workspace_clean_ui import CleanWorkspace, PREFIX, shell


class CleanRoutes(unittest.TestCase):
    def fixture(self):
        workspace = object.__new__(CleanWorkspace)
        workspace.main = {'members': {'members': [{'name': 'One', 'score': 7}]}}
        workspace.documents = {'index.html': '<h1>Modern shell</h1>',
                               'advanced-desk.html': '<h1>Analytical engine</h1>'}
        workspace.values = {'catalog': {'members': [{'name': 'One'}]}}
        workspace.heavy = None
        workspace.heavy_loader = lambda: {'members_heavy': [{'psy': {'brief_v3': {'name': 'One'}}}], 'bill_lobbying': {}}
        return workspace

    def test_native_root_and_advanced_engine_remain_distinct(self):
        workspace = self.fixture()
        self.assertEqual(workspace.response('/')[1], b'<h1>Modern shell</h1>')
        self.assertEqual(workspace.response(PREFIX + 'advanced-desk.html')[1], b'<h1>Analytical engine</h1>')

    def test_paths_cannot_escape_capsule_or_fall_back_to_old_disk_assets(self):
        workspace = self.fixture()
        for name in ('../secret.py', '%2e%2e/secret.py', '..\\secret.py', 'people-source.html',
                     'old-generated.html', 'data/member--1.json', 'data/member-1.json', 'data/member-00.json'):
            with self.subTest(name=name):
                self.assertEqual(workspace.response(PREFIX + name)[0], 404)
        self.assertIsNone(workspace.response('/outside-capsule.js'))

    def test_member_lookup_merges_same_positional_signed_rows(self):
        workspace = self.fixture()
        status, raw, content_type = workspace.response(PREFIX + 'data/member-0.json')
        value = json.loads(raw)
        self.assertEqual(status, 200)
        self.assertEqual(value['name'], 'One')
        self.assertEqual(value['score'], 7)
        self.assertEqual(value['psy']['brief_v3']['name'], 'One')
        self.assertTrue(content_type.startswith('application/json'))
        workspace.heavy = None
        workspace.heavy_loader = lambda: {'members_heavy': []}
        with self.assertRaises(ValueError):
            workspace.response(PREFIX + 'data/member-0.json')

    def test_capsule_bytes_match_independent_committed_source_digest_map(self):
        self.assertEqual(set(ASSETS), set(ASSET_PROVENANCE))
        for name, content in ASSETS.items():
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), ASSET_PROVENANCE[name]['sha256'])

    def test_freshness_distinguishes_analytical_and_brief_delivery_dates(self):
        context = {'roles': {'member-profiles': {'sha256': 'a' * 64, 'bytes': 100}},
                   'sourceDigest': 'b' * 64, 'releaseTag': 'module-data-2026-10-31-workspace-v1'}
        page = shell(context, 535, 'October 22, 2026')
        self.assertIn('Analytical baseline: ', page)
        self.assertIn('October 22, 2026', page)
        self.assertIn('delivered in signed workspace published ', page)
        self.assertIn('Evidence windows appear on individual briefs.', page)
        self.assertNotIn('__ANALYTIC__', page)
        self.assertNotIn('__EXPECTED__', page)


if __name__ == '__main__':
    unittest.main()
