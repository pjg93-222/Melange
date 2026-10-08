"""Regression tests for accepting complete profiles, never rendered shells."""
import unittest
from unittest.mock import patch
from audits.staffer_network import politico_profile_crawl_playwright as crawl


class Page:
    def __init__(self, snapshots, status=200):
        self.snapshots = snapshots
        self.index = 0
        self.status = status
        self.url = ''
        self.listeners = {}

    def on(self, event, callback):
        self.listeners[event] = callback

    def remove_listener(self, event, callback):
        self.listeners.pop(event, None)

    async def wait_for_function(self, *args, **kwargs):
        return True

    async def bring_to_front(self):
        return None

    async def goto(self, url, **kwargs):
        self.url = url
        if self.status == 200 and 'response' in self.listeners:
            profile_id = url.rsplit('/', 1)[-1]
            self.listeners['response'](type('Response', (), {'url': 'https://directory.politicopro.com/proxy/lava/api/v1/person/' + profile_id, 'status': 200})())
        return type('Response', (), {'status': self.status})()

    async def evaluate(self, script):
        result = self.snapshots[min(self.index, len(self.snapshots) - 1)]
        self.index += 1
        return result

class AcceptanceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.expected = {'profile_uuid': 'test-id', 'name': 'Test Person'}
        self.shell = {
            'profile_names': ['Test Person'], 'headings': ['Employment History'],
            'header_positions': ['Legislative Assistant for Test Member'],
            'employment_history': [], 'flags': {'document_loaded': True},
        }
        self.complete = {
            **self.shell,
            'employment_history': [{'employer': 'Test Member', 'date_text': '(2020 - Present)', 'title': 'Legislative Assistant'}],
        }

    async def test_shell_never_becomes_success(self):
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(Page([self.shell]), self.expected, 60, 0)
        self.assertFalse(result.ok)
        self.assertIsNone(result.row)
        self.assertTrue(result.retryable)

    async def test_delayed_history_is_awaited(self):
        page = Page([self.shell, self.shell, self.complete])
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(page, self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(page.index, 5)
        self.assertEqual(len(result.row['employment_history']), 1)

    async def test_partial_history_item_is_rejected(self):
        snapshot = {**self.complete, 'employment_history': [{'employer': 'Test Member', 'title': '', 'date_text': ''}]}
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(Page([snapshot]), self.expected, 60, 0)
        self.assertFalse(result.ok)

    async def test_404_has_no_profile_collections(self):
        unavailable = {'profile_names': [], 'flags': {'document_loaded': True}}
        result = await crawl.fetch_profile(Page([unavailable], 404), self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertIsNone(result.row['verified_name'])
        for field in ('current_header_positions', 'explicit_side_labels', 'profile_issue_areas', 'employment_history', 'education'):
            self.assertEqual(result.row[field], [])

    async def test_auth_halts(self):
        result = await crawl.fetch_profile(Page([self.complete], 401), self.expected, 60, 0)
        self.assertTrue(result.halt)
        self.assertFalse(result.ok)

    async def test_legitimately_missing_dates_and_degree_are_preserved(self):
        snapshot = {
            **self.complete,
            'employment_history': [{'employer': 'Test Member', 'title': 'Assistant', 'date_text': ''}],
            'education': [{'institution': 'Test University', 'date_text': '', 'degree': ''}],
        }
        result = await crawl.fetch_profile(Page([snapshot]), self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(result.row['education'][0]['institution'], 'Test University')
        self.assertEqual(result.row['employment_history'][0]['title'], 'Assistant')

    async def test_worker_timeout_is_retryable(self):
        with patch.object(crawl, 'fetch_profile', side_effect=TimeoutError):
            result = await crawl.bounded_fetch(Page([self.complete]), self.expected, 60, 0)
        self.assertFalse(result.ok)
        self.assertTrue(result.retryable)
        self.assertEqual(result.error, 'PROFILE_WORKER_TIMEOUT')

    async def test_soft404_never_overrides_profile_content(self):
        snapshot = {**self.complete, 'flags': {'document_loaded': True, 'unavailable_404': True}}
        result = await crawl.fetch_profile(Page([snapshot]), self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(result.row['identity_status'], 'UUID_AND_NAME_MATCH')
        self.assertTrue(result.row['employment_history'])

    async def test_wrong_uuid_redirect_halts(self):
        class RedirectedPage(Page):
            async def goto(self, url, **kwargs):
                response = await super().goto(url, **kwargs)
                self.url = crawl.PROFILE_BASE_URL + 'wrong-id'
                return response
        result = await crawl.fetch_profile(RedirectedPage([self.complete]), self.expected, 60, 0)
        self.assertTrue(result.halt)
        self.assertFalse(result.ok)
        self.assertTrue(result.error.startswith('PROFILE_FINAL_URL_MISMATCH'))

    async def test_later_history_and_side_labels_are_preserved(self):
        later = {**self.complete, 'employment_history': self.complete['employment_history'] + [{'employer': 'Earlier Member', 'title': 'Intern', 'date_text': ''}], 'explicit_side_labels': ['Majority Staff']}
        page = Page([self.complete, self.complete, later, later, later])
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(page, self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(len(result.row['employment_history']), 2)
        self.assertEqual(result.row['explicit_side_labels'], ['Majority Staff'])

    async def test_busy_profile_is_not_accepted(self):
        snapshot = {**self.complete, 'flags': {'document_loaded': True, 'busy': True}}
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(Page([snapshot]), self.expected, 60, 0)
        self.assertFalse(result.ok)

    async def test_data_api_400_halts_despite_visible_soft404(self):
        class ApiErrorPage(Page):
            async def evaluate(self, script):
                self.listeners['response'](type('Response', (), {'url': 'https://directory.politicopro.com/proxy/lava/api/v1/person/test-id', 'status': 400})())
                return await super().evaluate(script)
        page = ApiErrorPage([{'profile_names': [], 'flags': {'document_loaded': True, 'unavailable_404': True}}])
        result = await crawl.fetch_profile(page, self.expected, 60, 0)
        self.assertTrue(result.halt)
        self.assertFalse(result.ok)
        self.assertEqual(result.error, 'PROFILE_DATA_API_HTTP_400')

    async def test_soft404_without_person_api_evidence_is_not_accepted(self):
        page = Page([{'profile_names': [], 'flags': {'document_loaded': True, 'unavailable_404': True}}])
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(page, self.expected, 60, 0)
        self.assertFalse(result.ok)

    async def test_api400_recovers_once_through_normal_directory(self):
        class RecoverablePage(Page):
            profile_attempts = 0
            directory_visits = 0
            async def goto(self, url, **kwargs):
                response = await super().goto(url, **kwargs)
                if url == crawl.DIRECTORY_URL:
                    self.directory_visits += 1
                else:
                    self.profile_attempts += 1
                    if self.profile_attempts == 1:
                        self.listeners['response'](type('Response', (), {'url': 'https://directory.politicopro.com/proxy/lava/api/v1/person/test-id', 'status': 400})())
                return response
        page = RecoverablePage([self.complete])
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.bounded_fetch(page, self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(page.directory_visits, 1)
        self.assertEqual(page.profile_attempts, 2)

    async def test_authoritative_api404_does_not_wait_for_failed_request_body(self):
        class MissingPage(Page):
            async def goto(self, url, **kwargs):
                response = await super().goto(url, **kwargs)
                api_url = 'https://directory.politicopro.com/proxy/lava/api/v1/person/test-id'
                self.listeners['request'](type('Request', (), {'url': api_url, 'resource_type': 'xhr'})())
                self.listeners['response'](type('Response', (), {'url': api_url, 'status': 404})())
                return response
        page = MissingPage([{'profile_names': [], 'flags': {'document_loaded': True, 'unavailable_404': True}}])
        with patch.object(crawl.asyncio, 'sleep', return_value=None):
            result = await crawl.fetch_profile(page, self.expected, 60, 0)
        self.assertTrue(result.ok)
        self.assertEqual(result.row['profile_api_status'], 404)
        self.assertEqual(result.row['employment_history'], [])

    async def test_throttling_is_retryable(self):
        result = await crawl.fetch_profile(Page([self.complete], 429), self.expected, 60, 0)
        self.assertTrue(result.retryable)
        self.assertFalse(result.ok)


if __name__ == '__main__':
    unittest.main()
