"""Local deterministic tests for aggregate crawler navigation pacing."""

import asyncio
import unittest

from audits.staffer_network.politico_crawl_pacing import AdmissionStopped, AsyncRequestPacer


class Clock:
    def __init__(self):
        self.now = 0.0
        self.waits = []
        self.after_sleep = None

    def __call__(self):
        return self.now

    async def sleep(self, delay):
        self.waits.append(delay)
        await asyncio.sleep(0)
        self.now += delay
        if self.after_sleep is not None:
            self.after_sleep()


class PacerTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_admissions_are_half_second_apart(self):
        clock = Clock()
        pacer = AsyncRequestPacer(lambda: 150, clock=clock, sleep=clock.sleep)
        starts = await asyncio.gather(*(pacer.wait_turn() for _ in range(6)))
        self.assertEqual([round(value, 12) for value in starts], [0.0, 0.4, 0.8, 1.2, 1.6, 2.0])
        self.assertEqual(pacer.admissions, 6)

    async def test_backoff_during_wait_extends_spacing(self):
        clock = Clock()
        rate = [120]
        pacer = AsyncRequestPacer(lambda: rate[0], clock=clock, sleep=clock.sleep)
        await pacer.wait_turn()
        clock.after_sleep = lambda: rate.__setitem__(0, 60)
        self.assertEqual(await pacer.wait_turn(), 1.0)
        self.assertEqual(clock.waits, [0.5, 0.5])

    async def test_idle_time_does_not_accumulate_burst_tokens(self):
        clock = Clock()
        pacer = AsyncRequestPacer(lambda: 120, clock=clock, sleep=clock.sleep)
        await pacer.wait_turn()
        clock.now = 30.0
        starts = await asyncio.gather(*(pacer.wait_turn() for _ in range(3)))
        self.assertEqual(starts, [30.0, 30.5, 31.0])

    async def test_cancellation_does_not_record_admission(self):
        clock = Clock()
        waiting = asyncio.Event()
        never = asyncio.Event()

        async def blocked_sleep(delay):
            waiting.set()
            await never.wait()

        pacer = AsyncRequestPacer(lambda: 120, clock=clock, sleep=blocked_sleep)
        await pacer.wait_turn()
        task = asyncio.create_task(pacer.wait_turn())
        await waiting.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(pacer.admissions, 1)
        self.assertEqual(pacer.last_admitted_time, 0.0)
        clock.now = 0.5
        self.assertEqual(await pacer.wait_turn(), 0.5)

    async def test_stopped_before_wait_does_not_admit(self):
        stop = asyncio.Event()
        stop.set()
        pacer = AsyncRequestPacer(lambda: 120)
        with self.assertRaises(AdmissionStopped):
            await pacer.wait_turn(stop)
        self.assertEqual(pacer.admissions, 0)

    async def test_stopped_during_wait_does_not_admit(self):
        clock = Clock()
        stop = asyncio.Event()
        pacer = AsyncRequestPacer(lambda: 120, clock=clock, sleep=clock.sleep)
        await pacer.wait_turn(stop)
        clock.after_sleep = stop.set
        with self.assertRaises(AdmissionStopped):
            await pacer.wait_turn(stop)
        self.assertEqual(pacer.admissions, 1)

    async def test_invalid_rate_is_rejected_without_admission(self):
        for rate in (251, 0, -1, float("inf"), float("nan"), True, "120", None):
            with self.subTest(rate=rate):
                pacer = AsyncRequestPacer(lambda: rate)
                with self.assertRaises(ValueError):
                    await pacer.wait_turn()
                self.assertEqual(pacer.admissions, 0)


if __name__ == "__main__":
    unittest.main()
