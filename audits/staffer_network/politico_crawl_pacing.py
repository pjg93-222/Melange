"""One aggregate navigation admission clock for the Politico crawler.

Share a single instance across every worker and every explicit navigation,
including directory initialization and recovery. This limits starts, not the
browser's automatic asset requests or the duration of a hydrated profile load.
"""

from __future__ import annotations

import asyncio
import math
import numbers
import time
from collections.abc import Awaitable, Callable


class AdmissionStopped(RuntimeError):
    """The caller stopped this crawl before a navigation was admitted."""


class AsyncRequestPacer:
    """Serialize admissions without reserved slots or catch-up bursts.

    ``rate_getter`` is consulted again after every wait, so a rate backoff that
    happens while a worker sleeps extends that worker's spacing. Cancellation
    never advances the admission clock. The optional clock and sleep callables
    allow deterministic tests without wall-clock delays.
    """

    def __init__(
        self,
        rate_getter: Callable[[], float],
        *,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        self._rate_getter = rate_getter
        self._clock = clock if clock is not None else time.monotonic
        self._sleep = sleep if sleep is not None else asyncio.sleep
        self._lock = asyncio.Lock()
        self.last_admitted_time: float | None = None
        self.admissions = 0

    def _interval(self) -> float:
        rate = self._rate_getter()
        if (
            isinstance(rate, bool)
            or not isinstance(rate, numbers.Real)
            or not math.isfinite(rate)
            or rate <= 0
            or rate > 250
        ):
            raise ValueError("navigation rate must be finite, positive and at most 250 per minute")
        return 60.0 / rate

    @staticmethod
    def _check_stopped(stop_event: asyncio.Event | None) -> None:
        if stop_event is not None and stop_event.is_set():
            raise AdmissionStopped("crawl navigation admissions stopped")

    async def wait_turn(self, stop_event: asyncio.Event | None = None) -> float:
        """Wait for, record, and return this navigation's actual admission time."""
        self._check_stopped(stop_event)
        async with self._lock:
            while True:
                self._check_stopped(stop_event)
                interval = self._interval()
                now = self._clock()
                remaining = (
                    0.0
                    if self.last_admitted_time is None
                    else self.last_admitted_time + interval - now
                )
                if remaining <= 0:
                    # No await separates the final stop check from admission.
                    self._check_stopped(stop_event)
                    self.last_admitted_time = now
                    self.admissions += 1
                    return now
                await self._sleep(remaining)
