"""Modern renderer boundaries and existing advanced-engine route contracts."""
import hashlib
import json
import unittest

from module_workspace_clean_assets import ASSETS, ASSET_PROVENANCE
from module_workspace_clean_ui import CleanWorkspace, PREFIX, shell, catalog


class CleanRoutes(unittest.TestCase):
    def catalog_fixture(self):
        base = {'members': [{'name': 'One', 'honors': {'member_id': 'B000001'}},
                            {'name': 'Two', 'honors': {'member_id': 'C000002'}}],
                'cats': [], 'source_updates': {}}
        heavy = {'members_heavy': [
            {'bio': {'bioguide': 'C000002', 'state': 'BB'}, 'staffdir': None},
            {'bio': {'bioguide': 'B000001', 'state': 'AA', 'url': 'https://example.invalid'},
             'staffdir': [{'n': 'Fixture staff', 't': 'Fixture role', 'id': 'fixture'}],
             'articles': [{'date': '2026-10-02'}, {'date': '2026-10-01'}], 'bills': [{}, {}]}]}
        return base, heavy

    def fixture(self):
        workspace = object.__new__(CleanWorkspace)
        workspace.main = {'members': {'members': [{'name': 'One', 'score': 7, 'honors': {'member_id': 'B000001'}}]}}
        workspace.documents = {'index.html': '<h1>Modern shell</h1>',
                               'advanced-desk.html': '<h1>Analytical engine</h1>'}
        workspace.values = {'catalog': {'members': [{'name': 'One'}]}}
        workspace.heavy = None
        workspace.heavy_loader = lambda: {'members_heavy': [{'bio': {'bioguide': 'B000001'}, 'psy': {'brief_v3': {'name': 'One'}}}], 'bill_lobbying': {}}
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

    def test_member_lookup_merges_verified_identity_and_rejects_wrong_roster(self):
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

    def test_catalog_joins_by_bioguide_identity_preserving_light_order_and_real_missing_values(self):
        base, heavy = self.catalog_fixture()
        rows = catalog(base, heavy)['members']
        self.assertEqual([row['name'] for row in rows], ['One', 'Two'])
        self.assertEqual([row['bio']['bioguide'] for row in rows], ['B000001', 'C000002'])
        self.assertEqual(rows[0]['bio']['state'], 'AA')
        self.assertEqual(rows[0]['staffdir'][0]['n'], 'Fixture staff')
        self.assertEqual((rows[0]['articleCount'], rows[0]['billCount'], rows[0]['latest']), (2, 2, '2026-10-02'))
        self.assertIsNone(rows[1]['staffdir'])
        self.assertIsNone(rows[1]['billCount'])
        self.assertIsNone(rows[1]['articleCount'])
        self.assertIsNone(rows[1]['latest'])

    def test_catalog_refuses_duplicate_missing_and_mismatched_light_or_heavy_ids(self):
        for mutation in (
                lambda b, h: b['members'][1]['honors'].update(member_id='B000001'),
                lambda b, h: h['members_heavy'][0]['bio'].update(bioguide='B000001'),
                lambda b, h: h['members_heavy'][0]['bio'].update(bioguide='C999999'),
                lambda b, h: b['members'][0].update(honors=None),
                lambda b, h: h['members_heavy'][0].pop('bio'),
                lambda b, h: h['members_heavy'].pop()):
            base, heavy = self.catalog_fixture()
            mutation(base, heavy)
            with self.assertRaises(ValueError):
                catalog(base, heavy)

    def test_unchanged_signed_positional_profile_stream_must_match_bound_identity_order(self):
        base, heavy = self.catalog_fixture()
        workspace = self.fixture()
        workspace.main = {'members': base}
        workspace.heavy_loader = lambda: heavy
        with self.assertRaisesRegex(ValueError, 'profile order'):
            workspace.response(PREFIX + 'data/member-0.json')

    def test_capsule_bytes_match_independent_committed_source_digest_map(self):
        self.assertEqual(set(ASSETS), set(ASSET_PROVENANCE))
        for name, content in ASSETS.items():
            self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), ASSET_PROVENANCE[name]['sha256'])

    def test_people_font_import_cannot_block_scripts_and_other_css_bytes_are_unchanged(self):
        workspace = self.fixture()
        declaration = '@import url("https://use.typekit.net/ayd3qhz.css");'
        self.assertEqual(ASSETS['staffer-live.css'].count(declaration), 1)
        status, raw, content_type = workspace.response(PREFIX + 'staffer-live.css')
        self.assertEqual(status, 200)
        self.assertEqual(raw, ASSETS['staffer-live.css'].replace(declaration, '', 1).encode())
        self.assertNotIn(b'@import', raw)
        self.assertTrue(content_type.startswith('text/css'))
        self.assertIn('https://use.typekit.net/ayd3qhz.css', ASSETS['mlk-boot.js'])
        self.assertIn('FONT_WAIT = 1500', ASSETS['mlk-boot.js'])
        self.assertEqual(workspace.response(PREFIX + 'app.css')[1], ASSETS['app.css'].encode())

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
