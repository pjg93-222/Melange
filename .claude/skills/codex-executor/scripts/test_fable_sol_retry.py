from __future__ import annotations

import unittest

from fable_sol_retry import (
    FableResult,
    IncompleteReviewError,
    RetryLimitError,
    ReviewFlag,
    RewriteRequest,
    SolResult,
    StalledRewriteError,
    run_until_clear,
    run_until_clear_sync,
)


class QueueFable:
    def __init__(self, results: list[FableResult]) -> None:
        self.results = list(results)
        self.prompts: list[str] = []

    async def run(self, prompt: str, *, attempt: int) -> FableResult:
        self.prompts.append(prompt)
        return self.results.pop(0)


class NumberedSol:
    def __init__(self) -> None:
        self.requests: list[RewriteRequest] = []

    async def rewrite(self, request: RewriteRequest) -> SolResult:
        self.requests.append(request)
        return SolResult(
            revised_prompt=f"{request.current_prompt}\nrevision={len(self.requests)}"
        )


class FixedSol:
    def __init__(self, prompt: str) -> None:
        self.prompt = prompt

    async def rewrite(self, request: RewriteRequest) -> SolResult:
        return SolResult(revised_prompt=self.prompt)


class SyncQueueFable:
    def __init__(self, results: list[FableResult]) -> None:
        self.results = list(results)
        self.prompts: list[str] = []

    def run(self, prompt: str, *, attempt: int) -> FableResult:
        self.prompts.append(prompt)
        return self.results.pop(0)


class SyncNumberedSol:
    def __init__(self) -> None:
        self.requests: list[RewriteRequest] = []

    def rewrite(self, request: RewriteRequest) -> SolResult:
        self.requests.append(request)
        return SolResult(
            revised_prompt=f"{request.current_prompt}\nrevision={len(self.requests)}"
        )


class RetryWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_clear_result_returns_without_sol(self) -> None:
        fable = QueueFable([FableResult("ok", "fable-default")])
        sol = NumberedSol()

        result = await run_until_clear("prompt", fable=fable, sol=sol)

        self.assertEqual(result.output, "ok")
        self.assertEqual(result.sol_rewrites, 0)
        self.assertEqual(len(result.attempts), 1)

    async def test_opus_backend_routes_through_sol(self) -> None:
        fable = QueueFable(
            [
                FableResult("retry", "claude-opus-4"),
                FableResult("ok", "fable-default"),
            ]
        )
        sol = NumberedSol()

        result = await run_until_clear("prompt", fable=fable, sol=sol)

        self.assertEqual(result.output, "ok")
        self.assertEqual(result.sol_rewrites, 1)
        self.assertIn("switched to", sol.requests[0].retry_reasons[0])

    async def test_flags_keep_the_loop_running(self) -> None:
        flag = ReviewFlag("NEEDS_REVISION", "Revise this prompt.")
        fable = QueueFable(
            [
                FableResult("one", "fable-default", (flag,)),
                FableResult("two", "fable-default", (flag,)),
                FableResult("three", "fable-default"),
            ]
        )
        sol = NumberedSol()

        result = await run_until_clear(
            "prompt",
            fable=fable,
            sol=sol,
            max_attempts=3,
        )

        self.assertEqual(result.output, "three")
        self.assertEqual(result.sol_rewrites, 2)

    async def test_incomplete_review_fails_closed(self) -> None:
        fable = QueueFable(
            [FableResult("unknown", "fable-default", review_completed=False)]
        )

        with self.assertRaises(IncompleteReviewError):
            await run_until_clear("prompt", fable=fable, sol=NumberedSol())

    async def test_retry_limit_preserves_history(self) -> None:
        flag = ReviewFlag("STILL_FLAGGED", "Not clear.")
        fable = QueueFable(
            [
                FableResult("one", "fable-default", (flag,)),
                FableResult("two", "fable-default", (flag,)),
            ]
        )

        with self.assertRaises(RetryLimitError) as caught:
            await run_until_clear(
                "prompt",
                fable=fable,
                sol=NumberedSol(),
                max_attempts=2,
            )

        self.assertEqual(len(caught.exception.attempts), 2)

    async def test_unchanged_rewrite_is_rejected(self) -> None:
        flag = ReviewFlag("FLAG", "Issue.")
        fable = QueueFable([FableResult("one", "fable-default", (flag,))])

        with self.assertRaises(StalledRewriteError):
            await run_until_clear(
                "prompt",
                fable=fable,
                sol=FixedSol("prompt"),
            )


class SyncRetryWorkflowTests(unittest.TestCase):
    def test_sync_opus_backend_routes_through_sol(self) -> None:
        fable = SyncQueueFable(
            [
                FableResult("retry", "claude-opus-4"),
                FableResult("ok", "fable-default"),
            ]
        )
        sol = SyncNumberedSol()

        result = run_until_clear_sync("prompt", fable=fable, sol=sol)

        self.assertEqual(result.output, "ok")
        self.assertEqual(result.sol_rewrites, 1)
        self.assertEqual(len(result.attempts), 2)

    def test_sync_flags_keep_the_loop_running(self) -> None:
        flag = ReviewFlag("NEEDS_REVISION", "Revise this prompt.")
        fable = SyncQueueFable(
            [
                FableResult("retry", "fable-default", (flag,)),
                FableResult("ok", "fable-default"),
            ]
        )

        result = run_until_clear_sync(
            "prompt",
            fable=fable,
            sol=SyncNumberedSol(),
        )

        self.assertEqual(result.output, "ok")
        self.assertEqual(result.sol_rewrites, 1)


if __name__ == "__main__":
    unittest.main()
