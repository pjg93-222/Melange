"""Route regression with the shipped native graph reader, not replacement math.

Set MENTAT_TEST_RUNTIME to a packaged runtime containing bootstrap and sources.
"""
import ast
import hashlib
import importlib.util
import os
import re
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

if not os.environ.get('MENTAT_TEST_RUNTIME'):
    raise unittest.SkipTest('Set MENTAT_TEST_RUNTIME to an assembled Mentat runtime to exercise its native readers.')
RUNTIME = Path(os.environ['MENTAT_TEST_RUNTIME'])
sys.path[:0] = [str(RUNTIME / 'bootstrap'), str(RUNTIME / 'sources/mentat/app'),
               str(RUNTIME / 'sources/mentat/tools')]
spec = importlib.util.spec_from_file_location('candidate_workspace_mentat',
    os.environ.get('MENTAT_TEST_BINDING', str(Path(__file__).with_name('workspace_mentat.py'))))
candidate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(candidate)
import graph_data
import comparison_data
import snapshot_registry
from report_insights import stamp, report_freshness, worksheet_data
from module_application_contracts import DataIntakeBlocked
from openpyxl import Workbook

policy_names = {'donor_rows_allowed', 'names_person_subject', 'without_person_subjects'}
policy_tree = ast.parse((RUNTIME / 'sources/mentat/app/server.py').read_text(encoding='utf-8'))
policy = {'os': os, 're': re}
exec(compile(ast.Module(body=[node for node in policy_tree.body
    if isinstance(node, ast.FunctionDef) and node.name in policy_names], type_ignores=[]),
    '<native-comparison-policy>', 'exec'), policy)


class Handler:
    command = 'GET'
    headers = {}
    access_cfg = SimpleNamespace(enforced=False)
    def __init__(self, server, path):
        self.server, self.path, self.result, self.status = server, path, None, None
    def valid_host(self):
        return True
    def send(self, result, status=200, **options):
        self.result, self.status = result, status


class WorkspaceGraphRoutes(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'Banking Industry Spending Overview.xlsx'
        book = Workbook()
        sheet = book.active
        sheet.title = '2023-2024'
        for _ in range(3):
            sheet.append([''])
        sheet.append(['company', 'employee_tier', 'amount', 'include_in_analysis',
                      'recipient_category', 'fact_type', 'recipient_key', 'recipient', 'person_key', 'contributor'])
        sheet.append(['Test Bank', 'Employee', 125, 'yes', 'Company PAC', 'Master', '', ''])
        sheet.append(['Test Bank', 'Employee', 125, 'yes', 'Company PAC', 'Recipient', 'C00000001', 'Test PAC'])
        sheet.append(['Test Bank', 'Employee', 125, 'yes', 'Company PAC', 'Employee', '', '', 'test-person', 'Test Person'])
        book.save(self.path)
        book.close()
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        binding = candidate.MentatBinding.__new__(candidate.MentatBinding)
        binding.server = object()
        binding.console = SimpleNamespace(report_directory=Path(self.temp.name) / 'empty-local-reports')
        binding.module = SimpleNamespace(graph_schema=graph_data.graph_schema, stamp=stamp,
                                         graph_view=graph_data.graph_view, report_freshness=report_freshness,
                                         worksheet_data=worksheet_data,
                                         comparison_subjects=comparison_data.subjects,
                                         comparison_flows=comparison_data.flows)
        for name in policy_names:
            setattr(binding.module, name, policy[name])
        binding.module.HOSTED_PERSON_LEVEL_REFUSED = 'Person-level fields are not available to this account on the hosted console.'
        binding.books = {'banking': self.path}
        binding.analysis = SimpleNamespace(facts={'banking': {'receipt': {'projectedWorkbookSha256': self.digest}}})
        binding.sources = [{'id': 'Banking', 'industry': 'Banking', 'workbook': self.path,
                            'workbook_sha256': self.digest, 'available': True}]
        binding.programs = {'snapshot_registry': snapshot_registry}
        binding.prepared = SimpleNamespace(binding={'sourceDigest': 'a' * 64})
        binding.verify = lambda: True  # installation/signature checks are outside this route unit test
        self.binding = binding

    def request(self, route, **params):
        handler = Handler(self.binding.server, route + '?' + urlencode(params))
        self.assertTrue(self.binding.handle_request(handler), 'workspace route fell through to empty local console')
        return handler

    def test_native_graph_and_catalog_work_with_empty_local_reports(self):
        catalog = self.request('/api/graph-catalog', id='published-reports')
        self.assertEqual(catalog.status, 200)
        self.assertEqual(catalog.result['industries'][0]['name'], 'Banking')
        reports = self.request('/api/reports', id='published-reports')
        self.assertEqual(catalog.result['industries'][0]['indices'], [reports.result['reports'][0]['index']])
        expected = graph_data.graph_view([self.path], {'mode': 'direct'})
        graph = self.request('/api/graph', id='published-reports', industry='Banking', mode='direct')
        self.assertEqual(graph.status, 200)
        for field in ('totals', 'options', 'companies', 'levels', 'categories', 'organizations'):
            self.assertEqual(graph.result[field], expected[field])
        self.assertEqual(graph.result['totals']['giving'], 125)
        self.assertEqual(graph.result['reports'][0]['name'], 'Banking Industry Spending Overview.xlsx')
        self.assertEqual(graph.result['reports'][0]['sha256'], self.digest)
        self.assertEqual(graph.result['reports'][0]['build_stamp'],
                         snapshot_registry.build_stamp(self.digest, None, None, None))
        self.assertEqual(graph.result['reports'][0]['freshness'], report_freshness(self.path))
        self.assertFalse(self.binding.console.report_directory.exists())

    def test_slug_and_filters_use_existing_native_graph(self):
        graph = self.request('/api/graph', id='published-reports', industry='banking', company='Test Bank', latest='1')
        self.assertEqual(graph.status, 200)
        self.assertEqual(graph.result['industry'], 'Banking')
        self.assertEqual(graph.result['filters']['cycle'], '2024')
        self.assertEqual(graph.result['totals']['giving'], 125)

    def test_bad_selector_is_rejected_without_local_fallback(self):
        for params in ({'id': 'elsewhere', 'industry': 'Banking'},
                       {'id': 'published-reports', 'industry': '../banking.xlsx'},
                       {'id': 'published-reports', 'industry': 'Banking', 'company': 'Unknown'}):
            with self.subTest(params=params):
                self.assertEqual(self.request('/api/graph', **params).status, 400)
        self.assertEqual(self.request('/api/graph-catalog', id='elsewhere').status, 400)

    def test_signed_workbook_digest_mismatch_remains_blocked(self):
        self.binding.analysis.facts['banking']['receipt']['projectedWorkbookSha256'] = '0' * 64
        with self.assertRaises(DataIntakeBlocked):
            self.request('/api/graph', id='published-reports', industry='Banking')

    def test_unrelated_routes_still_belong_to_native_console(self):
        handler = Handler(self.binding.server, '/api/runs')
        self.assertFalse(self.binding.handle_request(handler))

    def test_report_data_uses_native_stamp_and_ui_selectors(self):
        reports = self.request('/api/reports', id='published-reports')
        index = reports.result['reports'][0]['index']
        listed = self.request('/api/report-data', id='published-reports', index=index)
        self.assertEqual(listed.status, 200)
        self.assertEqual(listed.result['sheets'], ['2023-2024'])
        self.assertEqual(listed.result['sha256'], self.digest)
        selected = self.request('/api/report-data', id='published-reports', index=index,
                                sheet='2023-2024', header=4)
        self.assertEqual(selected.status, 200)
        self.assertEqual(selected.result, worksheet_data(stamp(self.path), '2023-2024', 4))
        self.assertEqual(self.request('/api/report-data', id='published-reports', index=index,
                                     sheet='not-a-sheet', header=4).status, 400)

    def test_advanced_comparison_uses_native_subjects_and_flows(self):
        for route, engine in (('/api/comparison', comparison_data.subjects),
                              ('/api/comparison-flows', comparison_data.flows)):
            with self.subTest(route=route):
                expected = engine([self.path], 'Banking')
                actual = self.request(route, id='published-reports', industry='banking')
                self.assertEqual(actual.status, 200)
                for key, value in expected.items():
                    self.assertEqual(actual.result[key], value)
                self.assertEqual(actual.result['workspace_source_digest'], 'a' * 64)
                self.assertEqual(actual.result['reports'][0]['sha256'], self.digest)
                self.assertFalse(self.binding.console.report_directory.exists())

    def test_advanced_comparison_rejects_unknown_selectors_and_changed_workbooks(self):
        for route in ('/api/comparison', '/api/comparison-flows'):
            with self.subTest(route=route):
                self.assertEqual(self.request(route, id='other', industry='Banking').status, 400)
                self.assertEqual(self.request(route, id='published-reports', industry='../Banking').status, 400)
                self.binding.analysis.facts['banking']['receipt']['projectedWorkbookSha256'] = '0' * 64
                with self.assertRaises(DataIntakeBlocked):
                    self.request(route, id='published-reports', industry='Banking')
                self.binding.analysis.facts['banking']['receipt']['projectedWorkbookSha256'] = self.digest

    def test_advanced_comparison_preserves_native_hosted_person_policy(self):
        self.assertTrue(any(row['kind'] == 'Person' for row in comparison_data.subjects([self.path], 'Banking')['subjects']))
        with patch.dict(os.environ, {'MENTAT_DONOR_ROW_EMAILS': ''}):
            handler = Handler(self.binding.server, '/api/comparison?id=published-reports&industry=Banking')
            handler.access_cfg = SimpleNamespace(enforced=True)
            handler.access_user = 'viewer@example.test'
            self.assertTrue(self.binding.handle_request(handler))
            self.assertEqual(handler.status, 200)
            self.assertFalse(any(row['kind'] == 'Person' for row in handler.result['subjects']))
            handler.path += '&kind=Person'
            self.assertTrue(self.binding.handle_request(handler))
            self.assertEqual(handler.status, 403)


if __name__ == '__main__':
    unittest.main()
