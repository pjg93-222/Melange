"""Concrete adapters for the bounded Fable -> Sol retry controller.

The process adapters exchange one JSON object on stdin/stdout and never invoke
a shell.  The Codex adapter uses ``codex exec`` in a read-only, ephemeral
session with a schema-constrained final response.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Mapping, Sequence

from fable_sol_retry import FableResult, ReviewFlag, RewriteRequest, SolResult


class AdapterError(RuntimeError):
    """A configured service adapter failed or returned an invalid response."""


def command_from_json(value: str, *, label: str) -> tuple[str, ...]:
    """Parse a JSON argv array without accepting shell command strings."""

    try:
        command = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON array of argv strings") from exc
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or not part for part in command)
    ):
        raise ValueError(f"{label} must be a non-empty JSON array of argv strings")
    return tuple(command)


def _run_json_process(
    command: Sequence[str],
    request: Mapping[str, Any],
    *,
    timeout_seconds: float,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            list(command),
            input=json.dumps(request, ensure_ascii=False),
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_seconds,
            check=False,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AdapterError(f"adapter process failed: {exc}") from exc

    if completed.returncode:
        detail = completed.stderr.strip()[-2000:]
        raise AdapterError(
            f"adapter exited with code {completed.returncode}"
            + (f": {detail}" if detail else "")
        )
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AdapterError("adapter stdout was not one JSON object") from exc
    if not isinstance(response, dict):
        raise AdapterError("adapter response must be a JSON object")
    return response


def _parse_flags(value: object) -> tuple[ReviewFlag, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AdapterError("flags must be a JSON array")
    flags: list[ReviewFlag] = []
    for item in value:
        if not isinstance(item, dict):
            raise AdapterError("each flag must be a JSON object")
        code = item.get("code")
        message = item.get("message")
        severity = item.get("severity", "warning")
        if not isinstance(code, str) or not code.strip():
            raise AdapterError("each flag needs a non-empty code")
        if not isinstance(message, str) or not message.strip():
            raise AdapterError("each flag needs a non-empty message")
        if not isinstance(severity, str) or not severity.strip():
            raise AdapterError("flag severity must be a non-empty string")
        flags.append(ReviewFlag(code.strip(), message.strip(), severity.strip()))
    return tuple(flags)


def _fable_result(response: Mapping[str, Any]) -> FableResult:
    output = response.get("output")
    backend = response.get("reasoning_backend")
    completed = response.get("review_completed")
    if not isinstance(output, str):
        raise AdapterError("Fable response needs a string output")
    if not isinstance(backend, str) or not backend.strip():
        raise AdapterError("Fable response needs a reasoning_backend")
    if not isinstance(completed, bool):
        raise AdapterError("Fable response needs a boolean review_completed")
    return FableResult(
        output=output,
        reasoning_backend=backend.strip(),
        flags=_parse_flags(response.get("flags")),
        review_completed=completed,
    )


def _sol_result(response: Mapping[str, Any]) -> SolResult:
    revised = response.get("revised_prompt")
    notes = response.get("notes", "")
    if not isinstance(revised, str):
        raise AdapterError("Sol response needs a string revised_prompt")
    if not isinstance(notes, str):
        raise AdapterError("Sol response notes must be a string")
    return SolResult(revised_prompt=revised, notes=notes)


def rewrite_request_dict(request: RewriteRequest) -> dict[str, Any]:
    return {
        "action": "rewrite",
        "original_prompt": request.original_prompt,
        "current_prompt": request.current_prompt,
        "previous_output": request.previous_output,
        "flags": [
            {
                "code": flag.code,
                "message": flag.message,
                "severity": flag.severity,
            }
            for flag in request.flags
        ],
        "retry_reasons": list(request.retry_reasons),
        "attempt": request.attempt,
    }


class JsonProcessFableClient:
    """Call an explicitly configured Fable process through the JSON contract."""

    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 300) -> None:
        if not command:
            raise ValueError("command must not be empty")
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds

    def run(self, prompt: str, *, attempt: int) -> FableResult:
        response = _run_json_process(
            self.command,
            {"action": "review", "prompt": prompt, "attempt": attempt},
            timeout_seconds=self.timeout_seconds,
        )
        return _fable_result(response)

    async def run_async(self, prompt: str, *, attempt: int) -> FableResult:
        return await asyncio.to_thread(self.run, prompt, attempt=attempt)


class JsonProcessSolClient:
    """Call an explicitly configured Sol process through the JSON contract."""

    def __init__(self, command: Sequence[str], *, timeout_seconds: float = 600) -> None:
        if not command:
            raise ValueError("command must not be empty")
        self.command = tuple(command)
        self.timeout_seconds = timeout_seconds

    def rewrite(self, request: RewriteRequest) -> SolResult:
        response = _run_json_process(
            self.command,
            rewrite_request_dict(request),
            timeout_seconds=self.timeout_seconds,
        )
        return _sol_result(response)

    async def rewrite_async(self, request: RewriteRequest) -> SolResult:
        return await asyncio.to_thread(self.rewrite, request)


def resolve_codex_executable(explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            raise AdapterError(f"Codex executable does not exist: {path}")
        return str(path)

    discovered = shutil.which("codex")
    if discovered:
        return discovered

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates = list(
            (Path(local_app_data) / "OpenAI" / "Codex" / "bin").glob(
                "*/codex.exe"
            )
        )
        if candidates:
            return str(max(candidates, key=lambda path: path.stat().st_mtime))
    raise AdapterError("could not locate codex; pass --codex-executable")


class CodexExecSolClient:
    """Use the installed Codex CLI as the concrete Sol rewrite service."""

    _SCHEMA = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["revised_prompt", "notes"],
        "properties": {
            "revised_prompt": {"type": "string", "minLength": 1},
            "notes": {"type": "string"},
        },
    }

    def __init__(
        self,
        *,
        executable: str | None = None,
        working_directory: str | os.PathLike[str] | None = None,
        model: str = "gpt-5.6-sol",
        reasoning_effort: str = "xhigh",
        service_tier: str = "priority",
        timeout_seconds: float = 900,
    ) -> None:
        self.executable = resolve_codex_executable(executable)
        self.working_directory = str(
            Path(working_directory or os.getcwd()).resolve()
        )
        self.model = model
        self.reasoning_effort = reasoning_effort
        self.service_tier = service_tier
        self.timeout_seconds = timeout_seconds

    def rewrite(self, request: RewriteRequest) -> SolResult:
        instructions = (
            "Revise the current prompt so a fresh Fable attempt can satisfy the "
            "original objective and all existing constraints. Resolve the listed "
            "issues substantively; do not disguise trigger words or weaken scope, "
            "safety requirements, acceptance criteria, or higher-priority "
            "instructions. Return only the schema-conforming JSON object."
        )
        payload = rewrite_request_dict(request)
        with tempfile.TemporaryDirectory(prefix="fable-sol-") as temp_dir:
            temp = Path(temp_dir)
            schema_path = temp / "response.schema.json"
            output_path = temp / "response.json"
            schema_path.write_text(
                json.dumps(self._SCHEMA, ensure_ascii=False),
                encoding="utf-8",
            )
            command = [
                self.executable,
                "exec",
                "--model",
                self.model,
                "--config",
                f'model_reasoning_effort="{self.reasoning_effort}"',
                "--config",
                f'service_tier="{self.service_tier}"',
                "--sandbox",
                "read-only",
                "--ephemeral",
                "--output-schema",
                str(schema_path),
                "--output-last-message",
                str(output_path),
                "--cd",
                self.working_directory,
                "--skip-git-repo-check",
                "-",
            ]
            try:
                completed = subprocess.run(
                    command,
                    input=instructions
                    + "\n\nREWRITE REQUEST JSON:\n"
                    + json.dumps(payload, ensure_ascii=False),
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=self.timeout_seconds,
                    check=False,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise AdapterError(f"Sol execution failed: {exc}") from exc
            if completed.returncode:
                detail = completed.stderr.strip()[-3000:]
                raise AdapterError(
                    f"Sol exited with code {completed.returncode}"
                    + (f": {detail}" if detail else "")
                )
            if not output_path.is_file():
                raise AdapterError("Sol did not produce its final response file")
            try:
                response = json.loads(output_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise AdapterError("Sol final response was not valid JSON") from exc
        if not isinstance(response, dict):
            raise AdapterError("Sol final response must be a JSON object")
        return _sol_result(response)

    async def rewrite_async(self, request: RewriteRequest) -> SolResult:
        return await asyncio.to_thread(self.rewrite, request)


class AnthropicFableClient:
    """Use the Anthropic SDK as an explicitly paid Fable review adapter."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-fable-5",
        max_tokens: int = 4000,
    ) -> None:
        if not api_key.strip():
            raise ValueError("api_key must not be empty")
        try:
            import anthropic
        except ImportError as exc:
            raise AdapterError("the anthropic package is not installed") from exc
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def run(self, prompt: str, *, attempt: int) -> FableResult:
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=(
                    "Complete the supplied prompt, then review the result. Return "
                    "one JSON object with output (string), reasoning_backend (the "
                    "actual backend identifier), review_completed (boolean), and "
                    "flags (array of {code,message,severity}). Use an empty flags "
                    "array only when the result fully meets the prompt. Do not "
                    "wrap the JSON in markdown."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": f"Attempt {attempt}\n\n{prompt}",
                    }
                ],
            )
        except Exception as exc:
            raise AdapterError(f"Fable API request failed: {exc}") from exc
        text = "".join(
            block.text
            for block in message.content
            if getattr(block, "type", "") == "text"
        ).strip()
        try:
            response = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AdapterError("Fable returned a non-JSON review") from exc
        if not isinstance(response, dict):
            raise AdapterError("Fable review must be a JSON object")
        response["reasoning_backend"] = str(
            getattr(message, "model", response.get("reasoning_backend", self.model))
        )
        return _fable_result(response)

    async def run_async(self, prompt: str, *, attempt: int) -> FableResult:
        return await asyncio.to_thread(self.run, prompt, attempt=attempt)
