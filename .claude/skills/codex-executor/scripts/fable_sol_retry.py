"""Bounded orchestration for a Fable -> Sol -> Fable retry workflow.

The module is deliberately SDK-agnostic. Implement ``FableClient`` and
``SolClient`` with the APIs used by your application, then pass the clients to
``run_until_clear``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, Protocol, Sequence


@dataclass(frozen=True)
class ReviewFlag:
    """A structured issue returned by Fable's review step."""

    code: str
    message: str
    severity: str = "warning"


@dataclass(frozen=True)
class FableResult:
    """The result of one Fable attempt."""

    output: str
    reasoning_backend: str
    flags: tuple[ReviewFlag, ...] = ()
    review_completed: bool = True


@dataclass(frozen=True)
class RewriteRequest:
    """Context supplied to Sol when another attempt is needed."""

    original_prompt: str
    current_prompt: str
    previous_output: str
    flags: tuple[ReviewFlag, ...]
    retry_reasons: tuple[str, ...]
    attempt: int


@dataclass(frozen=True)
class SolResult:
    """A revised prompt produced by Sol."""

    revised_prompt: str
    notes: str = ""


@dataclass(frozen=True)
class AttemptRecord:
    """Audit information for a single Fable attempt."""

    attempt: int
    prompt: str
    output: str
    reasoning_backend: str
    flags: tuple[ReviewFlag, ...]
    retry_reasons: tuple[str, ...]
    accepted: bool


@dataclass(frozen=True)
class OrchestrationResult:
    """A cleared output together with the complete attempt history."""

    output: str
    accepted_prompt: str
    attempts: tuple[AttemptRecord, ...]
    sol_rewrites: int


class FableClient(Protocol):
    """Adapter contract for the service that attempts and reviews the prompt."""

    async def run(self, prompt: str, *, attempt: int) -> FableResult:
        ...


class SolClient(Protocol):
    """Adapter contract for the service that revises a rejected prompt."""

    async def rewrite(self, request: RewriteRequest) -> SolResult:
        ...


class SyncFableClient(Protocol):
    """Synchronous adapter contract for Fable."""

    def run(self, prompt: str, *, attempt: int) -> FableResult:
        ...


class SyncSolClient(Protocol):
    """Synchronous adapter contract for Sol."""

    def rewrite(self, request: RewriteRequest) -> SolResult:
        ...


class OrchestrationError(RuntimeError):
    """Base class for workflow failures."""


class IncompleteReviewError(OrchestrationError):
    """Fable returned without completing its review."""


class RetryLimitError(OrchestrationError):
    """The workflow did not clear within the configured attempt limit."""

    def __init__(self, message: str, attempts: Sequence[AttemptRecord]) -> None:
        super().__init__(message)
        self.attempts = tuple(attempts)


class StalledRewriteError(OrchestrationError):
    """Sol returned an empty, unchanged, or previously attempted prompt."""


OpusDetector = Callable[[str], bool]
EventHandler = Callable[[str, object], Awaitable[None] | None]
SyncEventHandler = Callable[[str, object], None]


def default_opus_detector(reasoning_backend: str) -> bool:
    """Match common backend identifiers such as ``claude-opus-4``."""

    return "opus" in reasoning_backend.casefold()


async def _emit(
    handler: EventHandler | None,
    event: str,
    payload: object,
) -> None:
    if handler is None:
        return

    pending = handler(event, payload)
    if pending is not None:
        await pending


async def run_until_clear(
    prompt: str,
    *,
    fable: FableClient,
    sol: SolClient,
    max_attempts: int = 5,
    opus_detector: OpusDetector = default_opus_detector,
    on_event: EventHandler | None = None,
) -> OrchestrationResult:
    """Run Fable and route retries through Sol until the result is clear.

    A retry is required when:

    * Fable reports that its reasoning backend is Opus; or
    * Fable returns one or more structured review flags.

    Missing review data never counts as a clear result. The workflow also has a
    hard attempt limit and rejects rewrite cycles.
    """

    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    original_prompt = prompt
    current_prompt = prompt
    seen_prompts = {prompt}
    attempts: list[AttemptRecord] = []
    sol_rewrites = 0

    for attempt_number in range(1, max_attempts + 1):
        await _emit(
            on_event,
            "fable_attempt_started",
            {"attempt": attempt_number, "prompt": current_prompt},
        )
        fable_result = await fable.run(current_prompt, attempt=attempt_number)

        if not fable_result.review_completed:
            raise IncompleteReviewError(
                f"Fable review was incomplete on attempt {attempt_number}"
            )

        retry_reasons: list[str] = []
        if opus_detector(fable_result.reasoning_backend):
            retry_reasons.append(
                f"reasoning backend switched to {fable_result.reasoning_backend}"
            )
        retry_reasons.extend(f"review flag: {flag.code}" for flag in fable_result.flags)

        accepted = not retry_reasons
        record = AttemptRecord(
            attempt=attempt_number,
            prompt=current_prompt,
            output=fable_result.output,
            reasoning_backend=fable_result.reasoning_backend,
            flags=fable_result.flags,
            retry_reasons=tuple(retry_reasons),
            accepted=accepted,
        )
        attempts.append(record)
        await _emit(on_event, "fable_attempt_finished", record)

        if accepted:
            return OrchestrationResult(
                output=fable_result.output,
                accepted_prompt=current_prompt,
                attempts=tuple(attempts),
                sol_rewrites=sol_rewrites,
            )

        if attempt_number == max_attempts:
            raise RetryLimitError(
                f"No clear Fable result after {max_attempts} attempts",
                attempts,
            )

        rewrite_request = RewriteRequest(
            original_prompt=original_prompt,
            current_prompt=current_prompt,
            previous_output=fable_result.output,
            flags=fable_result.flags,
            retry_reasons=tuple(retry_reasons),
            attempt=attempt_number,
        )
        await _emit(on_event, "sol_rewrite_started", rewrite_request)
        sol_result = await sol.rewrite(rewrite_request)
        sol_rewrites += 1

        revised_prompt = sol_result.revised_prompt.strip()
        if not revised_prompt:
            raise StalledRewriteError(
                f"Sol returned an empty prompt after attempt {attempt_number}"
            )
        if revised_prompt == current_prompt:
            raise StalledRewriteError(
                f"Sol did not change the prompt after attempt {attempt_number}"
            )
        if revised_prompt in seen_prompts:
            raise StalledRewriteError(
                f"Sol recreated an earlier prompt after attempt {attempt_number}"
            )

        seen_prompts.add(revised_prompt)
        current_prompt = revised_prompt
        await _emit(on_event, "sol_rewrite_finished", sol_result)

    raise AssertionError("unreachable")


def run_until_clear_sync(
    prompt: str,
    *,
    fable: SyncFableClient,
    sol: SyncSolClient,
    max_attempts: int = 5,
    opus_detector: OpusDetector = default_opus_detector,
    on_event: SyncEventHandler | None = None,
) -> OrchestrationResult:
    """Synchronous version of :func:`run_until_clear`.

    This path calls ordinary blocking client methods and does not create or
    depend on an asyncio event loop.
    """

    if not prompt.strip():
        raise ValueError("prompt must not be empty")
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    original_prompt = prompt
    current_prompt = prompt
    seen_prompts = {prompt}
    attempts: list[AttemptRecord] = []
    sol_rewrites = 0

    def emit(event: str, payload: object) -> None:
        if on_event is not None:
            on_event(event, payload)

    for attempt_number in range(1, max_attempts + 1):
        emit(
            "fable_attempt_started",
            {"attempt": attempt_number, "prompt": current_prompt},
        )
        fable_result = fable.run(current_prompt, attempt=attempt_number)

        if not fable_result.review_completed:
            raise IncompleteReviewError(
                f"Fable review was incomplete on attempt {attempt_number}"
            )

        retry_reasons: list[str] = []
        if opus_detector(fable_result.reasoning_backend):
            retry_reasons.append(
                f"reasoning backend switched to {fable_result.reasoning_backend}"
            )
        retry_reasons.extend(f"review flag: {flag.code}" for flag in fable_result.flags)

        accepted = not retry_reasons
        record = AttemptRecord(
            attempt=attempt_number,
            prompt=current_prompt,
            output=fable_result.output,
            reasoning_backend=fable_result.reasoning_backend,
            flags=fable_result.flags,
            retry_reasons=tuple(retry_reasons),
            accepted=accepted,
        )
        attempts.append(record)
        emit("fable_attempt_finished", record)

        if accepted:
            return OrchestrationResult(
                output=fable_result.output,
                accepted_prompt=current_prompt,
                attempts=tuple(attempts),
                sol_rewrites=sol_rewrites,
            )

        if attempt_number == max_attempts:
            raise RetryLimitError(
                f"No clear Fable result after {max_attempts} attempts",
                attempts,
            )

        rewrite_request = RewriteRequest(
            original_prompt=original_prompt,
            current_prompt=current_prompt,
            previous_output=fable_result.output,
            flags=fable_result.flags,
            retry_reasons=tuple(retry_reasons),
            attempt=attempt_number,
        )
        emit("sol_rewrite_started", rewrite_request)
        sol_result = sol.rewrite(rewrite_request)
        sol_rewrites += 1

        revised_prompt = sol_result.revised_prompt.strip()
        if not revised_prompt:
            raise StalledRewriteError(
                f"Sol returned an empty prompt after attempt {attempt_number}"
            )
        if revised_prompt == current_prompt:
            raise StalledRewriteError(
                f"Sol did not change the prompt after attempt {attempt_number}"
            )
        if revised_prompt in seen_prompts:
            raise StalledRewriteError(
                f"Sol recreated an earlier prompt after attempt {attempt_number}"
            )

        seen_prompts.add(revised_prompt)
        current_prompt = revised_prompt
        emit("sol_rewrite_finished", sol_result)

    raise AssertionError("unreachable")
