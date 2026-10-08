"""Fixed UUID shards must never overlap page ownership or lose queued jobs."""
import asyncio
import unittest
from unittest.mock import patch
from audits.staffer_network import politico_profile_crawl_playwright as crawl


class WindowSchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def test_inflight_cap_preserves_all_eight_shards(self):
        pages = [object() for _ in range(8)]
        batch = [{"profile_uuid": str(i)} for i in range(32)]
        active = 0
        peak = 0
        async def fetch(page, expected, *args):
            nonlocal active, peak
            self.assertIs(page, pages[int(expected["profile_uuid"]) % 8])
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.001)
            active -= 1
            return crawl.FetchResult(expected=expected, ok=True, started=True)
        rate = crawl.RateState()
        with patch.object(crawl, "shard_for_uuid", side_effect=lambda uuid, count: int(uuid) % count):
            with patch.object(crawl, "bounded_fetch", side_effect=fetch):
                results = await crawl.fetch_wave(pages, batch, rate,
                    crawl.AsyncRequestPacer(lambda: rate.rpm), 12000,
                    shard_by_uuid=True, max_inflight=2)
        self.assertEqual(peak, 2)
        self.assertEqual([r.expected for r in results], batch)
        self.assertTrue(all(r.ok for r in results))

    async def test_fixed_shards_preserve_source_order_and_exclusive_windows(self):
        pages = [object() for _ in range(8)]
        batch = [{"profile_uuid": str(i)} for i in range(64)]
        active = set()
        async def fetch(page, expected, *args):
            index = int(expected["profile_uuid"]) % 8
            self.assertIs(page, pages[index])
            self.assertNotIn(index, active)
            active.add(index)
            await asyncio.sleep(0)
            active.remove(index)
            return crawl.FetchResult(expected=expected, ok=True, retryable=False,
                                     started=True, row={"profile_uuid": expected["profile_uuid"]})
        rate = crawl.RateState()
        with patch.object(crawl, "shard_for_uuid", side_effect=lambda uuid, count: int(uuid) % count):
            with patch.object(crawl, "bounded_fetch", side_effect=fetch):
                results = await asyncio.wait_for(crawl.fetch_wave(
                    pages, batch, rate, crawl.AsyncRequestPacer(lambda: rate.rpm), 12000,
                    shard_by_uuid=True), 2)
        self.assertEqual([result.expected for result in results], batch)
        self.assertEqual([result.worker_index for result in results], [i % 8 for i in range(64)])
        self.assertTrue(all(result.ok for result in results))
        self.assertFalse(active)

    async def test_one_shard_failure_keeps_unscheduled_uuids_retryable(self):
        batch = [{"profile_uuid": str(i)} for i in range(25)]
        calls = []
        async def fetch(page, expected, *args):
            calls.append(expected["profile_uuid"])
            return crawl.FetchResult(expected=expected, started=True, error="RATE_LIMIT_429_DETECTED")
        rate = crawl.RateState()
        with patch.object(crawl, "shard_for_uuid", return_value=0):
            with patch.object(crawl, "bounded_fetch", side_effect=fetch):
                results = await asyncio.wait_for(crawl.fetch_wave(
                    [object() for _ in range(8)], batch, rate,
                    crawl.AsyncRequestPacer(lambda: rate.rpm), 12000, shard_by_uuid=True), 2)
        self.assertEqual(calls, ["0"])
        self.assertEqual([result.expected for result in results], batch)
        self.assertEqual(sum(result.started for result in results), 1)
        self.assertTrue(all(result.retryable for result in results))


if __name__ == "__main__":
    unittest.main()
