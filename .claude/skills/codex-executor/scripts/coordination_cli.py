"""Validate coordination payloads and query the structured event ledger."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys

from coordination_contract import (
    CapabilityHandshake,
    ContractError,
    CoordinationStateMachine,
    CorrectionReport,
    DecisionRequest,
    ExecutionContract,
    LaneState,
    ReportKind,
    validate_verdict,
)
from coordination_ledger import CoordinationLedger
from dynamic_coordination import (
    DynamicCoordinationError,
    Observation,
    Prediction,
    parse_timestamp,
    reconcile,
    replay_report,
)


def _load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ContractError("input must be a JSON object")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    contract = subparsers.add_parser("validate-contract")
    contract.add_argument("path", type=Path)

    handshake = subparsers.add_parser("validate-handshake")
    handshake.add_argument("path", type=Path)

    correction = subparsers.add_parser("validate-correction")
    correction.add_argument("path", type=Path)

    decision = subparsers.add_parser("validate-decision")
    decision.add_argument("path", type=Path)

    verdict = subparsers.add_parser("validate-verdict")
    verdict.add_argument("report_kind", choices=["CORRECTION_REPORT", "DECISION_REQUEST"])
    verdict.add_argument("verdict")

    transition = subparsers.add_parser("validate-transition")
    transition.add_argument("current", choices=[state.value for state in LaneState])
    transition.add_argument("target", choices=[state.value for state in LaneState])

    observation = subparsers.add_parser("validate-observation")
    observation.add_argument("path", type=Path)

    prediction = subparsers.add_parser("validate-prediction")
    prediction.add_argument("path", type=Path)

    reconcile_command = subparsers.add_parser("reconcile")
    reconcile_command.add_argument("path", type=Path)

    replay = subparsers.add_parser("replay")
    replay.add_argument("path", type=Path)

    record = subparsers.add_parser("record")
    record.add_argument("ledger", type=Path)
    record.add_argument("--run-id", required=True)
    record.add_argument("--task-slug", required=True)
    record.add_argument("--event-type", required=True)
    record.add_argument("--trigger-key", required=True)
    record.add_argument("--verdict")
    record.add_argument("--payload", default="{}")
    record.add_argument("--spec-file", type=Path)
    record.add_argument("--receipt-file", type=Path)

    repeats = subparsers.add_parser("repeats")
    repeats.add_argument("ledger", type=Path)
    repeats.add_argument("--minimum", type=int, default=2)

    audit = subparsers.add_parser("audit")
    audit.add_argument("ledger", type=Path)
    audit.add_argument("--glassbox-dir", type=Path, default=None)
    audit.add_argument("--strict", action="store_true")

    invariants = subparsers.add_parser("invariants")
    invariants.add_argument("ledger", type=Path)
    invariants.add_argument("--run-id", required=True)

    record_episode = subparsers.add_parser("record-episode")
    record_episode.add_argument("ledger", type=Path)
    record_episode.add_argument("--run-id", required=True)
    record_episode.add_argument("--event-kind", required=True)
    record_episode.add_argument("--subject", required=True)
    record_episode.add_argument("--trigger-key", required=True)
    record_episode.add_argument("--payload", default="{}")

    episode = subparsers.add_parser("episode")
    episode.add_argument("ledger", type=Path)
    episode.add_argument("--run-id", required=True)

    candidates = subparsers.add_parser("candidates")
    candidates.add_argument("ledger", type=Path)
    candidates.add_argument("--minimum", type=int, default=2)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    exit_code = 0
    try:
        if args.command == "validate-contract":
            ExecutionContract.from_mapping(_load(args.path))
            output: object = {"valid": True, "kind": "contract"}
        elif args.command == "validate-handshake":
            CapabilityHandshake.from_mapping(_load(args.path))
            output = {"valid": True, "kind": "handshake"}
        elif args.command == "validate-correction":
            CorrectionReport.from_mapping(_load(args.path))
            output = {"valid": True, "kind": "correction"}
        elif args.command == "validate-decision":
            DecisionRequest.from_mapping(_load(args.path))
            output = {"valid": True, "kind": "decision"}
        elif args.command == "validate-verdict":
            report_kind = ReportKind(args.report_kind)
            output = {
                "valid": True,
                "kind": "verdict",
                "verdict": validate_verdict(report_kind, args.verdict),
            }
        elif args.command == "validate-transition":
            current = LaneState(args.current)
            machine = CoordinationStateMachine(state=current, history=[current])
            machine.transition(LaneState(args.target))
            output = {
                "valid": True,
                "kind": "transition",
                "state": machine.state.value,
            }
        elif args.command == "validate-observation":
            Observation.from_mapping(_load(args.path))
            output = {"valid": True, "kind": "observation"}
        elif args.command == "validate-prediction":
            Prediction.from_mapping(_load(args.path))
            output = {"valid": True, "kind": "prediction"}
        elif args.command in {"reconcile", "replay"}:
            value = _load(args.path)
            predictions = value.get("predictions")
            observations = value.get("observations")
            if not isinstance(predictions, list) or not isinstance(
                observations, list
            ):
                raise DynamicCoordinationError(
                    "predictions and observations must be arrays"
                )
            options = {
                "run_id": str(value.get("run_id", "")),
                "cutoff_sequence": int(value.get("cutoff_sequence", 0)),
                "consecutive_divergences": int(
                    value.get("consecutive_divergences", 0)
                ),
                "rebase_after": int(value.get("rebase_after", 3)),
                "evaluated_at": value.get("evaluated_at"),
            }
            if args.command == "replay":
                recorded_hash: str | None = None
                if "recorded_reconciliation_sha256" in value:
                    supplied_hash = value["recorded_reconciliation_sha256"]
                    if not isinstance(supplied_hash, str):
                        raise DynamicCoordinationError(
                            "recorded_reconciliation_sha256 must be a string "
                            "when provided"
                        )
                    recorded_hash = supplied_hash
                output = replay_report(
                    predictions,
                    observations,
                    **options,
                    recorded_reconciliation_sha256=recorded_hash,
                )
            else:
                evaluated_at = options.pop("evaluated_at")
                result = reconcile(
                    [Prediction.from_mapping(item) for item in predictions],
                    [Observation.from_mapping(item) for item in observations],
                    **options,
                    evaluated_at=(
                        None
                        if evaluated_at is None
                        else parse_timestamp(evaluated_at, "evaluated_at")
                    ),
                )
                output = {
                    "aggregate_result": result.aggregate_result.value,
                    "evaluated_at_sequence": result.evaluated_at_sequence,
                    "reconciliation_sha256": result.reconciliation_sha256,
                    "prediction_results": [
                        {
                            "prediction_id": item.prediction_id,
                            "observation_id": item.observation_id,
                            "result": item.result.value,
                            "reason_code": item.reason_code.value,
                            "terminal": item.terminal,
                            "continuation_permitted": item.continuation_permitted,
                        }
                        for item in result.prediction_results
                    ],
                }
        elif args.command == "record":
            payload = json.loads(args.payload)
            occurrence = CoordinationLedger(args.ledger).record(
                run_id=args.run_id,
                task_slug=args.task_slug,
                event_type=args.event_type,
                trigger_key=args.trigger_key,
                payload=payload,
                verdict=args.verdict,
                spec_file=args.spec_file,
                receipt_file=args.receipt_file,
            )
            output = {"recorded": True, "occurrence": occurrence}
        elif args.command == "record-episode":
            sequence = CoordinationLedger(args.ledger).record_episode_event(
                run_id=args.run_id,
                event_kind=args.event_kind,
                subject=args.subject,
                trigger_key=args.trigger_key,
                payload=json.loads(args.payload),
            )
            output = {"recorded": True, "sequence": sequence}
        elif args.command == "episode":
            output = CoordinationLedger(args.ledger).episode(run_id=args.run_id)
        elif args.command == "invariants":
            events = CoordinationLedger(args.ledger).list_events(
                run_id=args.run_id
            )
            latest = next(
                (
                    event
                    for event in reversed(events)
                    if event["event_type"] == "invariants"
                ),
                None,
            )
            if latest is None:
                raise ValueError(
                    f"run {args.run_id!r} has no invariants event"
                )
            payload = latest["payload"]
            invariants = (
                payload.get("invariants")
                if isinstance(payload, dict)
                else None
            )
            if (
                not isinstance(invariants, list)
                or any(not isinstance(item, str) for item in invariants)
            ):
                raise ValueError(
                    f"run {args.run_id!r} has corrupt invariants event payload"
                )
            for invariant in invariants:
                print(f"- {invariant}")
            return 0
        elif args.command == "candidates":
            output = CoordinationLedger(args.ledger).amendment_candidates(
                minimum=args.minimum
            )
        elif args.command == "audit":
            output = CoordinationLedger(args.ledger).audit(
                glassbox_dir=args.glassbox_dir
            )
            if args.strict and output["totals"]["findings"]:
                exit_code = 1
        else:
            output = CoordinationLedger(args.ledger).repeated_triggers(
                minimum=args.minimum
            )
    except (
        ContractError,
        DynamicCoordinationError,
        OSError,
        ValueError,
        sqlite3.Error,
        json.JSONDecodeError,
    ) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(output, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
