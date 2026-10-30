import hashlib
import json
import unittest

import module_workspace_render as ui


class RendererGuards(unittest.TestCase):
    def context(self):
        return {'schemaVersion': 1, 'appId': 'melange', 'contractId': 'melange.workspace.v1',
                'sourceDigest': 'a' * 64, 'releaseTag': 'module-data-2026-10-30',
                'roles': {role: {'sha256': 'b' * 64, 'bytes': 100} for role in ui.MAIN_ROLES | {'member-profiles', 'industry-pages'}}}

    def test_script_boundaries_and_html_context_are_escaped(self):
        hostile = {'value': '</script><script>UNTRUSTED</script>&\u2028\u2029'}
        encoded = ui.script_json(hostile)
        self.assertNotIn('</script>', encoded)
        self.assertNotIn('<script>', encoded)
        self.assertEqual(json.loads(encoded), hostile)

    def test_provenance_is_closed_and_contains_no_owner_or_path_fields(self):
        context = self.context()
        self.assertEqual(ui.provenance_context(context), context)
        for change in ({'schemaVersion': True}, {'profile': 'private path'}, {'sourceDigest': 'bad'}):
            with self.assertRaises(ui.WorkspaceRenderDataError):
                ui.provenance_context({**context, **change})

    def test_data_trees_reject_executable_types_prototype_fields_and_nonfinite_numbers(self):
        for value in ({'__proto__': {}}, {'x': float('nan')}, {'x': object()}, {'constructor': 'bad'}):
            with self.assertRaises(ui.WorkspaceRenderDataError):
                ui.safe_tree(value)

    def test_exact_positional_roster_binds_base_and_lazy_role_hashes(self):
        context = self.context()
        members = {'members': [{'name': 'Alpha', 'state': 'AA', 'district': '1', 'sna_idx': 0}]}
        roster = [['Alpha', 'AA', '1', 0]]
        merge = {'fields': ['name', 'state', 'district', 'sna_idx'], 'members': 1, 'membersHeavy': 1,
                 'orderedRoster': roster, 'orderedRosterSha256': hashlib.sha256(ui.canonical(roster)).hexdigest(),
                 'membersSha256': 'b' * 64, 'memberProfilesSha256': 'b' * 64}
        loader = ui.profile_loader(members, context, {'memberProfileMerge': merge})
        self.assertIn(ui.PROFILES_PATH, loader)
        self.assertNotIn('members_heavy":[', loader)
        with self.assertRaises(ui.WorkspaceRenderDataError):
            ui.profile_loader(members, context, {'memberProfileMerge': {**merge, 'membersHeavy': 2}})

    def test_compiled_template_changes_fail_instead_of_tolerant_replacement(self):
        with self.assertRaises(RuntimeError):
            ui.replace_once('missing', '__MARKER__', 'value')
        with self.assertRaises(RuntimeError):
            ui.replace_once('__MARKER____MARKER__', '__MARKER__', 'value')


if __name__ == '__main__':
    unittest.main()
