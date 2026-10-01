"""Command-line entry point for the bounded Fable -> Sol retry workflow."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid

from coordination_ledger import CoordinationLedger, LedgerEventHandler
from fable_sol_adapters import (
    AdapterError,
    AnthropicFableClient,
    CodexExecSolClient,
    JsonProcessFableClient,
    JsonProcessSolClient,
    command_from_json,
)
from fable_sol_retry import (
    OrchestrationError,
    RetryLimitError,
    run_until_clear_sync,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run Fable review attempts, routing every flag or Opus selection "
            "through Sol before trying Fable again."
        )
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--prompt", help="prompt text")
    source.add_argument("--prompt-file", type=Path, help="UTF-8 prompt file")

    fable = parser.add_mutually_exclusive_group()
    fable.add_argument(
        "--fable-command-json",
        help=(
            "JSON argv array for a process that reads/writes the documented "
            "Fable JSON contract; FABLE_REVIEW_COMMAND_JSON is also accepted"
        ),
    )
    fable.add_argument(
        "--fable-api-key-file",
        type=Path,
        help="key file for the explicitly paid Anthropic Fable adapter",
    )
    parser.add_argument(
        "--allow-paid-api",
        action="store_true",
        help="required with --fable-api-key-file",
    )
    parser.add_argument("--fable-model", default="claude-fable-5")
    parser.add_argument(
        "--sol-command-json",
        help=(
            "optional JSON argv array for Sol; otherwise the installed Codex "
            "CLI runs gpt-5.6-sol"
        ),
    )
    parser.add_argument("--codex-executable")
    parser.add_argument("--workdir", type=Path, default=Path.cwd())
    parser.add_argument("--max-attempts", type=int, default=5)
    parser.add_argument("--timeout-seconds", type=float, default=900)
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--task-slug", default="fable-sol-review")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path.home()
        / ".claude"
        / "state"
        / "codex-executor-ledger.sqlite3",
    )
    return parser


def _prompt(args: argparse.Namespace) -> str:
    if args.prompt is not None:
        return args.prompt
    return args.prompt_file.read_text(encoding="utf-8")


def _fable_client(args: argparse.Namespace):
    command_value = args.fable_command_json or os.environ.get(
        "FABLE_REVIEW_COMMAND_JSON"
    )
    if command_value:
        return JsonProcessFableClient(
            command_from_json(command_value, label="Fable command"),
            timeout_seconds=args.timeout_seconds,
        )
    if args.fable_api_key_file is None:
        raise ValueError(
            "configure --fable-command-json, FABLE_REVIEW_COMMAND_JSON, "
            "or --fable-api-key-file"
        )
    if not args.allow_paid_api:
        raise ValueError("--fable-api-key-file requires --allow-paid-api")
    return AnthropicFableClient(
        api_key=args.fable_api_key_file.read_text(encoding="utf-8").strip(),
        model=args.fable_model,
    )


def _sol_client(args: argparse.Namespace):
    command_value = args.sol_command_json or os.environ.get("SOL_REWRITE_COMMAND_JSON")
    if command_value:
        return JsonProcessSolClient(
            command_from_json(command_value, label="Sol command"),
            timeout_seconds=args.timeout_seconds,
        )
    return CodexExecSolClient(
        executable=args.codex_executable,
        working_directory=args.workdir,
        timeout_seconds=args.timeout_seconds,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_id = args.run_id or str(uuid.uuid4())
    try:
        ledger = CoordinationLedger(args.ledger)
        result = run_until_clear_sync(
            _prompt(args),
            fable=_fable_client(args),
            sol=_sol_client(args),
            max_attempts=args.max_attempts,
            on_event=LedgerEventHandler(
                ledger,
                run_id=run_id,
                task_slug=args.task_slug,
            ),
        )
    except RetryLimitError as exc:
        print(
            json.dumps(
                {
                    "status": "retry_limit",
                    "run_id": run_id,
                    "error": str(exc),
                    "attempts": [asdict(item) for item in exc.attempts],
                },
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 2
    except (
        OSError,
        ValueError,
        sqlite3.Error,
        OrchestrationError,
        AdapterError,
    ) as exc:
        print(
            json.dumps(
                {"status": "error", "run_id": run_id, "error": str(exc)},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "status": "accepted",
                "run_id": run_id,
                **asdict(result),
                "repeated_triggers": ledger.repeated_triggers(),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
