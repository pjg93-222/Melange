"""Network-free regression tests for the shared-page crawler scheduler."""

import asyncio
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from audits.staffer_network import politico_profile_crawl_playwright as crawl
from audits.staffer_network.politico_crawl_pacing import AdmissionStopped, AsyncRequestPacer


class PipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.pages = [object(), object(), object()]
        self.batch = [{"profile_uuid": f"test-{index}", "sequence": index} for index in range(25)]
        self.rate = crawl.RateState()
        self.pacer = AsyncRequestPacer(lambda: self.rate.rpm)

    @staticmethod
    def success(expected):
        return crawl.FetchResult(expected=expected, ok=True, retryable=False,
                                 row={"profile_uuid": expected["profile_uuid"]},
                                 elapsed_ms=1000, started=True)

    async def test_three_page_isolation_and_source_order_for_twenty_five_jobs(self):
        active = set()
        high_water = 0
        completed = []
        all_three_started = asyncio.Event()
        second_completed = asyncio.Event()

        async def fake_fetch(page, expected, rpm, ordinal, pacer, stop_event):
            nonlocal high_water
            self.assertNotIn(page, active, "a page must never serve two jobs at once")
            active.add(page)
            high_water = max(high_water, len(active))
            if len(active) == 3:
                all_three_started.set()
            try:
                await all_three_started.wait()
                if expected["sequence"] == 0:
                    await second_completed.wait()
                await asyncio.sleep(0)
                completed.append(expected["sequence"])
                if expected["sequence"] == 1:
                    second_completed.set()
                return self.success(expected)
            finally:
                active.remove(page)

        with patch.object(crawl, "bounded_fetch", side_effect=fake_fetch):
            results = await asyncio.wait_for(
                crawl.fetch_wave(self.pages, self.batch, self.rate, self.pacer, 12_000), timeout=2
            )
        self.assertEqual(high_water, 3)
        self.assertFalse(active)
        self.assertNotEqual(completed, list(range(25)), "fixture must finish out of source order")
        self.assertEqual([item.expected for item in results], self.batch)
        self.assertTrue(all(item.ok and item.started for item in results))
        self.assertEqual(self.rate.total_clean_batches, 25)
        self.assertEqual(self.rate.rpm, 120)

    async def test_failure_stops_queued_jobs_and_returns_every_uuid(self):
        called = []
        all_three_started = asyncio.Event()

        async def fake_fetch(page, expected, rpm, ordinal, pacer, stop_event):
            called.append(expected["sequence"])
            if len(called) == 3:
                all_three_started.set()
            await all_three_started.wait()
            if expected["sequence"] == 0:
                return crawl.FetchResult(expected=expected, error="RATE_LIMIT_429_DETECTED",
                                         elapsed_ms=100, started=True)
            await stop_event.wait()
            return self.success(expected)

        with patch.object(crawl, "bounded_fetch", side_effect=fake_fetch):
            results = await asyncio.wait_for(
                crawl.fetch_wave(self.pages, self.batch, self.rate, self.pacer, 12_000), timeout=2
            )
        self.assertEqual(called, [0, 1, 2])
        self.assertEqual([item.expected for item in results], self.batch)
        self.assertEqual(sum(item.started for item in results), 3)
        self.assertEqual(sum(item.ok for item in results), 2)
        self.assertTrue(all(not item.started and item.retryable for item in results[3:]))
        self.assertTrue(all(item.error == "ADMISSION_STOPPED" for item in results[3:]))
        self.assertEqual(self.rate.backoff_count, 1)

    async def test_exception_stops_cancels_and_drains_siblings(self):
        called = []
        active = set()
        cancelled = set()
        all_three_started = asyncio.Event()
        never = asyncio.Event()

        async def fake_fetch(page, expected, rpm, ordinal, pacer, stop_event):
            sequence = expected["sequence"]
            called.append(sequence)
            active.add(sequence)
            if len(active) == 3:
                all_three_started.set()
            try:
                await all_three_started.wait()
                if sequence == 0:
                    raise RuntimeError("scheduler fixture failure")
                await never.wait()
            except asyncio.CancelledError:
                cancelled.add(sequence)
                raise
            finally:
                active.remove(sequence)

        with patch.object(crawl, "bounded_fetch", side_effect=fake_fetch):
            with self.assertRaisesRegex(RuntimeError, "scheduler fixture failure"):
                await asyncio.wait_for(
                    crawl.fetch_wave(self.pages, self.batch, self.rate, self.pacer, 12_000), timeout=2
                )
            await asyncio.sleep(0)
        self.assertEqual(called, [0, 1, 2], "queued jobs must not start after an exception")
        self.assertFalse(active, "all child jobs must be drained before the wave raises")
        self.assertEqual(cancelled, {1, 2})

    def api400(self):
        return crawl.FetchResult(expected=self.batch[0], error="PROFILE_DATA_API_HTTP_400",
                                 halt=True, started=True, elapsed_ms=10)

    async def test_directory_recovery_admission_stopped_preserves_started(self):
        with patch.object(crawl, "fetch_profile", return_value=self.api400()) as fetch:
            with patch.object(crawl, "initialize_directory", side_effect=AdmissionStopped("stopped")):
                result = await crawl.bounded_fetch(self.pages[0], self.batch[0], 60, 0, self.pacer)
        self.assertEqual(fetch.await_count, 1)
        self.assertFalse(result.ok)
        self.assertTrue(result.started)
        self.assertTrue(result.retryable)

    async def test_retry_navigation_refused_preserves_first_attempt(self):
        stopped = crawl.FetchResult(expected=self.batch[0], error="ADMISSION_STOPPED", started=False)
        with patch.object(crawl, "fetch_profile", side_effect=[self.api400(), stopped]) as fetch:
            with patch.object(crawl, "initialize_directory", return_value=None):
                result = await crawl.bounded_fetch(self.pages[0], self.batch[0], 60, 0, self.pacer)
        self.assertEqual(fetch.await_count, 2)
        self.assertFalse(result.ok)
        self.assertTrue(result.started)
        self.assertTrue(result.retryable)

    async def test_retry_navigation_raises_stopped_preserves_first_attempt(self):
        with patch.object(crawl, "fetch_profile", side_effect=[self.api400(), AdmissionStopped("stopped")]):
            with patch.object(crawl, "initialize_directory", return_value=None):
                result = await crawl.bounded_fetch(self.pages[0], self.batch[0], 60, 0, self.pacer)
        self.assertFalse(result.ok)
        self.assertTrue(result.started)
        self.assertTrue(result.retryable)


class DirectoryInitializationTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def page(*, flags=None, status=200):
        return SimpleNamespace(
            url=crawl.DIRECTORY_URL,
            goto=AsyncMock(return_value=SimpleNamespace(status=status)),
            wait_for_function=AsyncMock(),
            evaluate=AsyncMock(return_value={"flags": flags or {}}),
        )

    async def test_transient_readiness_failure_retries_once_and_succeeds(self):
        page = self.page()
        page.wait_for_function.side_effect = [TimeoutError("directory not ready"), None]
        pacer = SimpleNamespace(wait_turn=AsyncMock())
        await crawl.initialize_directory(page, pacer)
        self.assertEqual(page.goto.await_count, 2)
        self.assertEqual(page.wait_for_function.await_count, 2)
        self.assertEqual(page.evaluate.await_count, 1)
        self.assertEqual(pacer.wait_turn.await_count, 2)
        self.assertTrue(all(call.args == (crawl.DIRECTORY_URL,) for call in page.goto.await_args_list))

    async def test_auth_challenge_and_throttle_readiness_failures_never_retry(self):
        for flag in ("authentication_required", "challenge", "throttled"):
            with self.subTest(flag=flag):
                page = self.page(flags={flag: True})
                page.wait_for_function.side_effect = TimeoutError("directory not ready")
                pacer = SimpleNamespace(wait_turn=AsyncMock())
                with self.assertRaisesRegex(RuntimeError, "DIRECTORY_AUTHENTICATION_CHALLENGE_OR_THROTTLE"):
                    await crawl.initialize_directory(page, pacer)
                self.assertEqual(page.goto.await_count, 1)
                self.assertEqual(page.wait_for_function.await_count, 1)
                self.assertEqual(pacer.wait_turn.await_count, 1)

    async def test_persistent_readiness_failure_is_limited_to_two_navigations(self):
        page = self.page()
        page.wait_for_function.side_effect = TimeoutError("directory still not ready")
        pacer = SimpleNamespace(wait_turn=AsyncMock())
        with self.assertRaisesRegex(TimeoutError, "directory still not ready"):
            await crawl.initialize_directory(page, pacer)
        self.assertEqual(page.goto.await_count, 2)
        self.assertEqual(page.wait_for_function.await_count, 2)
        self.assertEqual(page.evaluate.await_count, 2)
        self.assertEqual(pacer.wait_turn.await_count, 2)

    async def test_http_auth_or_throttle_fails_without_readiness_wait_or_retry(self):
        for status in (401, 403, 429):
            with self.subTest(status=status):
                page = self.page(status=status)
                with self.assertRaisesRegex(RuntimeError, f"DIRECTORY_HTTP_{status}"):
                    await crawl.initialize_directory(page)
                self.assertEqual(page.goto.await_count, 1)
                page.wait_for_function.assert_not_awaited()
                page.evaluate.assert_not_awaited()

    async def test_login_path_redirect_stops_before_readiness_wait(self):
        page = self.page()
        page.url = "https://directory.politicopro.com/login"
        with self.assertRaisesRegex(RuntimeError, "DIRECTORY_AUTHENTICATION_REDIRECT"):
            await crawl.initialize_directory(page)
        self.assertEqual(page.goto.await_count, 1)
        page.wait_for_function.assert_not_awaited()
        page.evaluate.assert_not_awaited()

    async def test_root_login_hostname_stops_before_readiness_wait(self):
        page = self.page()
        page.url = "https://login.politicopro.com/"
        with self.assertRaisesRegex(RuntimeError, "DIRECTORY_AUTHENTICATION_REDIRECT"):
            await crawl.initialize_directory(page)
        self.assertEqual(page.goto.await_count, 1)
        page.wait_for_function.assert_not_awaited()
        page.evaluate.assert_not_awaited()

    async def test_delayed_root_login_redirect_never_retries(self):
        page = self.page()

        async def redirect_during_readiness(*args, **kwargs):
            page.url = "https://login.politicopro.com/"
            raise TimeoutError("redirected during directory readiness")

        page.wait_for_function.side_effect = redirect_during_readiness
        with self.assertRaisesRegex(RuntimeError, "DIRECTORY_AUTHENTICATION_CHALLENGE_OR_THROTTLE"):
            await crawl.initialize_directory(page)
        self.assertEqual(page.goto.await_count, 1)
        self.assertEqual(page.wait_for_function.await_count, 1)
        self.assertEqual(page.evaluate.await_count, 1)


if __name__ == "__main__":
    unittest.main()
