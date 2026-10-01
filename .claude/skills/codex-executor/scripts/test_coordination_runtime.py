from __future__ import annotations

from contextlib import closing, redirect_stderr, redirect_stdout
from datetime import datetime
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from coordination_contract import (
    CapabilityHandshake,
    ContractError,
    CoordinationStateMachine,
    CorrectionReport,
    DecisionRequest,
    ExecutionContract,
    LaneState,
    Readiness,
    ReportKind,
    validate_verdict,
)
from coordination_cli import main as coordination_main
from coordination_ledger import (
    _NON_DISPATCH_RUN_EVENT_TYPES,
    _utf8_file_fingerprint,
    CoordinationLedger,
    LedgerEventHandler,
)
from fable_sol_adapters import (
    AdapterError,
    JsonProcessFableClient,
    JsonProcessSolClient,
    command_from_json,
)
from fable_sol_retry import AttemptRecord, ReviewFlag, RewriteRequest


class AdapterTests(unittest.TestCase):
    def test_command_parser_requires_an_argv_array(self) -> None:
        self.assertEqual(
            command_from_json('["tool","--flag"]', label="test"),
            ("tool", "--flag"),
        )
        for invalid in ("tool --flag", '"tool"', "[]", '[""]'):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                command_from_json(invalid, label="test")

    def test_process_fable_contract(self) -> None:
        program = (
            "import json,sys;"
            "r=json.load(sys.stdin);"
            "json.dump({'output':r['prompt'],'reasoning_backend':'fable',"
            "'review_completed':True,'flags':[]},sys.stdout)"
        )
        client = JsonProcessFableClient((sys.executable, "-c", program))
        result = client.run("hello", attempt=1)
        self.assertEqual(result.output, "hello")
        self.assertTrue(result.review_completed)

    def test_process_sol_contract(self) -> None:
        program = (
            "import json,sys;"
            "r=json.load(sys.stdin);"
            "json.dump({'revised_prompt':r['current_prompt']+' revised',"
            "'notes':'fixed'},sys.stdout)"
        )
        client = JsonProcessSolClient((sys.executable, "-c", program))
        result = client.rewrite(
            RewriteRequest(
                original_prompt="hello",
                current_prompt="hello",
                previous_output="no",
                flags=(ReviewFlag("X", "issue"),),
                retry_reasons=("review flag: X",),
                attempt=1,
            )
        )
        self.assertEqual(result.revised_prompt, "hello revised")

    def test_process_response_rejects_missing_review_marker(self) -> None:
        program = (
            "import json,sys;json.load(sys.stdin);"
            "json.dump({'output':'x','reasoning_backend':'fable','flags':[]},sys.stdout)"
        )
        with self.assertRaises(AdapterError):
            JsonProcessFableClient((sys.executable, "-c", program)).run(
                "hello", attempt=1
            )


class CliTests(unittest.TestCase):
    def test_dc07_cli_rejects_non_object_evidence_items_cleanly(self) -> None:
        valid_prediction = {
            "prediction_id": "pred-1",
            "step_id": "step-1",
            "subject": "service.status",
            "expected": "ready",
            "comparison": "equals",
            "tolerance": {},
            "deadline_sequence": 2,
            "allow_self_generated": False,
            "minimum_evidence_confidence": 0.5,
            "max_observation_age_seconds": None,
            "allow_bounded_drift_continue": False,
        }
        valid_observation = {
            "observation_id": "obs-1",
            "run_id": "run-1",
            "sequence": 1,
            "observed_at": "2026-07-24T12:00:00Z",
            "source": "service",
            "kind": "response",
            "subject": "service.status",
            "value": "ready",
            "confidence": 1.0,
            "evidence_class": "independent",
            "caused_by_action_id": "none",
            "retry_attempt_id": None,
            "content_sha256": None,
        }
        cases = (
            ("prediction", [1], [valid_observation]),
            ("observation", [valid_prediction], [1]),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            for label, predictions, observations in cases:
                with self.subTest(label=label):
                    path = Path(temp_dir) / f"{label}.json"
                    path.write_text(
                        json.dumps(
                            {
                                "predictions": predictions,
                                "observations": observations,
                                "run_id": "run-1",
                                "cutoff_sequence": 2,
                            }
                        ),
                        encoding="utf-8",
                    )
                    stderr = StringIO()
                    with redirect_stderr(stderr):
                        exit_code = coordination_main(["reconcile", str(path)])
                    error_text = stderr.getvalue()
                    self.assertEqual(exit_code, 1)
                    self.assertNotIn("Traceback", error_text)
                    error = json.loads(error_text)
                    self.assertIs(error["valid"], False)
                    self.assertEqual(
                        error["error"],
                        f"{label} must be an object",
                    )

    def test_dc14_cli_rejects_null_recorded_hash_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "replay.json"
            path.write_text(
                json.dumps(
                    {
                        "predictions": [],
                        "observations": [],
                        "run_id": "run-1",
                        "cutoff_sequence": 2,
                        "recorded_reconciliation_sha256": None,
                    }
                ),
                encoding="utf-8",
            )
            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = coordination_main(["replay", str(path)])
            error_text = stderr.getvalue()
            self.assertEqual(exit_code, 1)
            self.assertNotIn("Traceback", error_text)
            error = json.loads(error_text)
            self.assertIs(error["valid"], False)
            self.assertEqual(
                error["error"],
                "recorded_reconciliation_sha256 must be a string when provided",
            )

    def test_invariants_cli_prints_latest_and_errors_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run-pinned",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants:old",
                payload={"invariants": ["old invariant"]},
            )
            latest = ["stdlib only", "deterministic output"]
            ledger.record(
                run_id="run-pinned",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants:latest",
                payload={"invariants": latest},
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    [
                        "invariants",
                        str(ledger_path),
                        "--run-id",
                        "run-pinned",
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(
                stdout.getvalue(),
                "- stdlib only\n- deterministic output\n",
            )

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = coordination_main(
                    [
                        "invariants",
                        str(ledger_path),
                        "--run-id",
                        "run-missing",
                    ]
                )
            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            error = json.loads(stderr.getvalue())
            self.assertIs(error["valid"], False)
            self.assertIn("run-missing", error["error"])


class LedgerTests(unittest.TestCase):
    def _initialized_empty_ledger(self, path: Path) -> CoordinationLedger:
        ledger = CoordinationLedger(path)
        ledger.record(
            run_id="fixture",
            task_slug="fixture",
            event_type="configured",
            trigger_key="fixture",
            payload={},
        )
        with closing(sqlite3.connect(path)) as connection:
            with connection:
                connection.execute("DELETE FROM coordination_events")
                connection.execute(
                    "DELETE FROM sqlite_sequence WHERE name = 'coordination_events'"
                )
        return ledger

    def test_records_and_detects_repeated_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            first = ledger.record(
                run_id="one",
                task_slug="task",
                event_type="pause",
                trigger_key="tool-missing",
                payload={"tool": "x"},
            )
            second = ledger.record(
                run_id="two",
                task_slug="task",
                event_type="pause",
                trigger_key="tool-missing",
                payload={"tool": "x"},
            )
            self.assertEqual((first, second), (1, 2))
            self.assertEqual(
                ledger.repeated_triggers()[0]["trigger_key"], "tool-missing"
            )

    def test_controller_handler_uses_retry_reason_as_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            handler = LedgerEventHandler(ledger, run_id="run", task_slug="task")
            handler(
                "fable_attempt_finished",
                AttemptRecord(
                    attempt=1,
                    prompt="p",
                    output="o",
                    reasoning_backend="fable",
                    flags=(ReviewFlag("FORMAT", "missing"),),
                    retry_reasons=("review flag: FORMAT",),
                    accepted=False,
                ),
            )
            events = ledger.list_events(run_id="run")
            self.assertEqual(
                events[0]["trigger_key"], "fable_retry:review flag: FORMAT"
            )
            self.assertEqual(events[0]["payload"]["attempt"], 1)
            self.assertNotEqual(events[0]["payload"]["prompt"], "p")
            self.assertIn("sha256", events[0]["payload"]["prompt"])
            self.assertNotEqual(events[0]["payload"]["output"], "o")

    def test_informational_events_do_not_count_as_recurring_defects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for run_id in ("one", "two"):
                ledger.record(
                    run_id=run_id,
                    task_slug="task",
                    event_type="clear",
                    trigger_key="info:fable_clear",
                    payload={"output": "private"},
                )
            self.assertEqual(ledger.repeated_triggers(), [])

    def test_secret_named_payload_fields_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="one",
                task_slug="task",
                event_type="configured",
                trigger_key="configured",
                payload={"api_key": "do-not-store", "token_count": 2},
            )
            payload = ledger.list_events()[0]["payload"]
            self.assertEqual(payload["api_key"], {"redacted": True})
            self.assertEqual(payload["token_count"], 2)

    def test_dispatch_requires_complete_provenance_without_writing(self) -> None:
        invalid_payloads = (
            {"effort": "xhigh", "tier": "priority"},
            {"model": "gpt-5.6-sol", "tier": "priority"},
            {"model": "gpt-5.6-sol", "effort": "xhigh"},
            {"model": None, "effort": "xhigh", "tier": "priority"},
            {"model": "gpt-5.6-sol", "effort": " ", "tier": "priority"},
            {"model": "gpt-5.6-sol", "effort": "xhigh", "tier": 1},
            ["not", "a", "dict"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for payload in invalid_payloads:
                with self.subTest(payload=payload), self.assertRaisesRegex(
                    ValueError,
                    "dispatch payload fields must be non-empty strings",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="dispatch",
                        trigger_key="dispatch",
                        payload=payload,
                    )
                self.assertEqual(ledger.list_events(), [])

    def test_dispatch_requires_pinned_effort_and_tier_without_writing(self) -> None:
        invalid_values = (
            ("effort", "high", 'effort must equal exactly "xhigh"'),
            ("effort", "medium", 'effort must equal exactly "xhigh"'),
            ("effort", "Xhigh", 'effort must equal exactly "xhigh"'),
            ("effort", " xhigh", 'effort must equal exactly "xhigh"'),
            ("tier", "standard", 'tier must equal exactly "priority"'),
            ("tier", "flex", 'tier must equal exactly "priority"'),
            ("tier", "Priority", 'tier must equal exactly "priority"'),
            ("tier", " priority", 'tier must equal exactly "priority"'),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for field, value, message in invalid_values:
                payload = {
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "tier": "priority",
                }
                payload[field] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(
                    ValueError,
                    message,
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="dispatch",
                        trigger_key="dispatch",
                        payload=payload,
                    )
                self.assertEqual(ledger.list_events(), [])

    def test_dispatch_rejects_sanitized_alias_key_effort_downgrade(self) -> None:
        class K:
            def __str__(self) -> str:
                return "effort"

        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            with self.assertRaisesRegex(
                ValueError,
                'effort must equal exactly "xhigh"',
            ):
                ledger.record(
                    run_id="run",
                    task_slug="task",
                    event_type="dispatch",
                    trigger_key="dispatch",
                    payload={
                        "model": "gpt-5.6-sol",
                        "effort": "xhigh",
                        "tier": "priority",
                        K(): "high",
                    },
                )
            self.assertEqual(ledger.list_events(), [])

    def test_dispatch_provenance_round_trips_exact_values(self) -> None:
        payload = {
            "model": "gpt-5.6-sol",
            "effort": "xhigh",
            "tier": "priority",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="dispatch",
                trigger_key="dispatch",
                payload=payload,
            )
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            )
            self.assertEqual(ledger.list_events()[0]["payload"], payload)

    def test_receipt_records_fingerprints_and_strict_verified_bool(self) -> None:
        spec = "approved specification"
        receipt = "verification receipt"
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": spec,
                    "receipt": receipt,
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            )

            events = ledger.list_events()
            self.assertEqual(len(events), 1)
            stored = events[0]["payload"]
            self.assertEqual(
                set(stored["spec"]),
                {"sha256", "utf8_bytes"},
            )
            self.assertEqual(stored["spec"]["utf8_bytes"], len(spec.encode("utf-8")))
            self.assertRegex(stored["spec"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                stored["spec"]["sha256"],
                hashlib.sha256(spec.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(
                set(stored["receipt"]),
                {"sha256", "utf8_bytes"},
            )
            self.assertEqual(
                stored["receipt"]["utf8_bytes"],
                len(receipt.encode("utf-8")),
            )
            self.assertRegex(stored["receipt"]["sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(
                stored["receipt"]["sha256"],
                hashlib.sha256(receipt.encode("utf-8")).hexdigest(),
            )
            self.assertIs(stored["verified"], True)

    def test_receipt_rejections_write_nothing(self) -> None:
        invalid_payloads = (
            (
                "missing spec",
                {
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            ),
            (
                "missing receipt",
                {
                    "spec": "spec",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            ),
            (
                "missing verified",
                {
                    "spec": "spec",
                    "receipt": "receipt",
                    "dispatch_trigger_key": "dispatch",
                },
            ),
            (
                "empty spec",
                {
                    "spec": "",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            ),
            (
                "integer verified",
                {
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": 1,
                    "dispatch_trigger_key": "dispatch",
                },
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for label, payload in invalid_payloads:
                with self.subTest(label=label), self.assertRaisesRegex(
                    ValueError,
                    "receipt record requires spec, receipt, verified",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="receipt",
                        trigger_key="receipt",
                        payload=payload,
                    )
                self.assertEqual(ledger.list_events(), [])

    def test_cli_receipt_files_compute_fingerprints_without_storing_text(
        self,
    ) -> None:
        spec_text = "true dispatch text with caf\u00e9"
        receipt_text = "true reply text with jalape\u00f1o"
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger_path = directory / "events.sqlite3"
            spec_path = directory / "A.txt"
            receipt_path = directory / "B.txt"
            spec_path.write_text(spec_text, encoding="utf-8")
            receipt_path.write_text(receipt_text, encoding="utf-8")
            payload = json.dumps(
                {
                    "verified": False,
                    "dispatch_trigger_key": "probe-a",
                }
            )

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = coordination_main(
                    [
                        "record",
                        str(ledger_path),
                        "--run-id",
                        "run-file-fingerprints",
                        "--task-slug",
                        "task",
                        "--event-type",
                        "receipt",
                        "--trigger-key",
                        "receipt:file-fingerprints",
                        "--spec-file",
                        str(spec_path),
                        "--receipt-file",
                        str(receipt_path),
                        "--payload",
                        payload,
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertEqual(
                json.loads(stdout.getvalue()),
                {"recorded": True, "occurrence": 1},
            )
            spec_bytes = spec_path.read_bytes()
            receipt_bytes = receipt_path.read_bytes()
            independent = {
                "spec": {
                    "sha256": hashlib.sha256(spec_bytes).hexdigest(),
                    "utf8_bytes": len(spec_bytes),
                },
                "receipt": {
                    "sha256": hashlib.sha256(receipt_bytes).hexdigest(),
                    "utf8_bytes": len(receipt_bytes),
                },
            }
            with closing(sqlite3.connect(ledger_path)) as connection:
                raw_payload = connection.execute(
                    "SELECT payload_json FROM coordination_events"
                ).fetchone()[0]
            stored = json.loads(raw_payload)
            self.assertEqual(stored["spec"], independent["spec"])
            self.assertEqual(stored["receipt"], independent["receipt"])
            self.assertIs(
                stored["receipt_fingerprints_ledger_computed"],
                True,
            )
            for source_text in (spec_text, receipt_text):
                self.assertNotIn(source_text, raw_payload)
                self.assertNotIn(source_text, stdout.getvalue())
                self.assertNotIn(source_text, stderr.getvalue())

    def test_utf8_file_fingerprint_accepts_split_multibyte_character(
        self,
    ) -> None:
        chunk_size = 4
        encoded = b"abc" + "\u00e9".encode("utf-8") + b"longer"
        self.assertEqual(
            encoded[chunk_size - 1 : chunk_size + 1],
            "\u00e9".encode("utf-8"),
        )
        self.assertGreater(len(encoded), chunk_size)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "split.txt"
            path.write_bytes(encoded)
            with patch(
                "coordination_ledger._UTF8_FILE_FINGERPRINT_CHUNK_SIZE",
                chunk_size,
            ):
                fingerprint = _utf8_file_fingerprint(path, field="spec")

        self.assertEqual(
            fingerprint,
            {
                "sha256": hashlib.sha256(encoded).hexdigest(),
                "utf8_bytes": len(encoded),
            },
        )

    def test_invalid_utf8_file_rejects_before_insert_with_exact_message(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            path = directory / "invalid.txt"
            path.write_bytes(b"valid prefix\xff")
            ledger_path = directory / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)

            with self.assertRaises(ValueError) as raised:
                ledger.record(
                    run_id="run-invalid-utf8",
                    task_slug="task",
                    event_type="configured",
                    trigger_key="configured:invalid-utf8",
                    payload={},
                    spec_file=path,
                )

            self.assertEqual(
                str(raised.exception),
                "spec file must contain UTF-8 text",
            )
            # No database file is a stronger zero-side-effect guarantee than
            # an empty event list.
            self.assertFalse(ledger_path.exists())

            ledger.record(
                run_id="run-existing-ledger",
                task_slug="task",
                event_type="configured",
                trigger_key="configured:existing",
                payload={},
            )
            before = ledger.list_events()
            self.assertEqual(len(before), 1)

            with self.assertRaises(ValueError) as existing_raised:
                ledger.record(
                    run_id="run-invalid-utf8",
                    task_slug="task",
                    event_type="configured",
                    trigger_key="configured:invalid-utf8-existing",
                    payload={},
                    spec_file=path,
                )

            self.assertEqual(
                str(existing_raised.exception),
                "spec file must contain UTF-8 text",
            )
            self.assertEqual(ledger.list_events(), before)

    def test_cli_receipt_file_conflict_names_field_and_writes_nothing(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger_path = directory / "events.sqlite3"
            receipt_path = directory / "B.txt"
            receipt_path.write_text("true reply", encoding="utf-8")
            self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                before = connection.execute(
                    "SELECT COUNT(*) FROM coordination_events"
                ).fetchone()[0]
            payload = json.dumps(
                {
                    "verified": False,
                    "dispatch_trigger_key": "probe-a",
                    "receipt": {
                        "sha256": "a" * 64,
                        "utf8_bytes": 1,
                    },
                }
            )

            stderr = StringIO()
            with redirect_stderr(stderr):
                exit_code = coordination_main(
                    [
                        "record",
                        str(ledger_path),
                        "--run-id",
                        "run-conflict",
                        "--task-slug",
                        "task",
                        "--event-type",
                        "receipt",
                        "--trigger-key",
                        "receipt:conflict",
                        "--receipt-file",
                        str(receipt_path),
                        "--payload",
                        payload,
                    ]
                )

            self.assertEqual(exit_code, 1)
            error = json.loads(stderr.getvalue())["error"]
            self.assertIn("conflict", error)
            self.assertIn("receipt", error)
            with closing(sqlite3.connect(ledger_path)) as connection:
                after = connection.execute(
                    "SELECT COUNT(*) FROM coordination_events"
                ).fetchone()[0]
            self.assertEqual((before, after), (0, 0))

    def test_caller_supplied_receipt_fingerprints_are_informational_only(
        self,
    ) -> None:
        fingerprint = {"sha256": "a" * 64, "utf8_bytes": 1}
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger_path = directory / "events.sqlite3"
            spec_path = directory / "A.txt"
            receipt_path = directory / "B.txt"
            spec_path.write_text("dispatch", encoding="utf-8")
            receipt_path.write_text("reply", encoding="utf-8")
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run-ledger-computed",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:ledger-computed",
                payload={
                    "verified": False,
                    "dispatch_trigger_key": "dispatch:ledger-computed",
                },
                spec_file=spec_path,
                receipt_file=receipt_path,
            )
            ledger.record(
                run_id="run-caller-supplied",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:caller-supplied",
                payload={
                    "spec": fingerprint,
                    "receipt": fingerprint,
                    "verified": False,
                    "dispatch_trigger_key": "dispatch:caller-supplied",
                },
            )

            report = ledger.audit()
            self.assertEqual(
                report["receipt_fingerprints_caller_supplied"],
                [
                    {
                        "id": 2,
                        "run_id": "run-caller-supplied",
                        "task_slug": "task",
                        "trigger_key": "receipt:caller-supplied",
                    }
                ],
            )
            self.assertEqual(
                report["totals"]["receipt_fingerprints_caller_supplied"],
                1,
            )
            self.assertEqual(report["totals"]["findings"], 0)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), report)

    def test_receipt_structure_accepts_latest_pinned_invariants(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger = CoordinationLedger(directory / "events.sqlite3")
            ledger.record(
                run_id="run-structured",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants:old",
                payload={"invariants": ["old invariant"]},
            )
            ledger.record(
                run_id="run-structured",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants:latest",
                payload={"invariants": ["one", "two", "three", "four"]},
            )
            spec_path = directory / "dispatch.txt"
            receipt_path = directory / "receipt.txt"
            spec_path.write_text("dispatch", encoding="utf-8")
            receipt_path.write_text(
                "## **RECEIPT**\n"
                "OBJECTIVE: implement the contract\n"
                "ENUMERATION:\n"
                "- **CON-1:** preserve the contract\n"
                "- **INV-1:** one\n"
                "- **INV-2:** two\n"
                "- **INV-3:** three\n"
                "- **INV-4:** four\n",
                encoding="utf-8",
            )

            before = len(ledger.list_events(run_id="run-structured"))
            occurrence = ledger.record(
                run_id="run-structured",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:structured",
                payload={
                    "verified": True,
                    "dispatch_trigger_key": "dispatch:structured",
                },
                spec_file=spec_path,
                receipt_file=receipt_path,
            )
            events = ledger.list_events(run_id="run-structured")

            self.assertEqual(occurrence, 1)
            self.assertEqual((before, len(events)), (2, 3))
            self.assertEqual(
                events[-1]["payload"]["structure"],
                {
                    "checked": True,
                    "has_block": True,
                    "enumerated_items": 5,
                    "invariants_pinned": 4,
                    "invariants_missing": [],
                    "pass": True,
                },
            )
            self.assertEqual(
                ledger.audit()["receipts_verified_without_structure_check"],
                [],
            )

    def test_missing_receipt_block_rejects_true_but_records_false(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger = CoordinationLedger(directory / "events.sqlite3")
            ledger.record(
                run_id="run-no-block",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants:no-block",
                payload={"invariants": ["one"]},
            )
            spec_path = directory / "dispatch.txt"
            receipt_path = directory / "receipt.txt"
            spec_path.write_text("dispatch", encoding="utf-8")
            receipt_path.write_text(
                "An ordinary executor reply with no labeled block.",
                encoding="utf-8",
            )
            payload = {
                "verified": True,
                "dispatch_trigger_key": "dispatch:no-block",
            }

            before = len(ledger.list_events())
            with self.assertRaises(ValueError) as raised:
                ledger.record(
                    run_id="run-no-block",
                    task_slug="task",
                    event_type="receipt",
                    trigger_key="receipt:no-block",
                    payload=payload,
                    spec_file=spec_path,
                    receipt_file=receipt_path,
                )
            after_rejection = len(ledger.list_events())

            self.assertEqual((before, after_rejection), (1, 1))
            self.assertIn("has_block: missing RECEIPT block", str(raised.exception))

            payload["verified"] = False
            ledger.record(
                run_id="run-no-block",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:no-block",
                payload=payload,
                spec_file=spec_path,
                receipt_file=receipt_path,
            )
            events = ledger.list_events()
            self.assertEqual((after_rejection, len(events)), (1, 2))
            self.assertEqual(
                events[-1]["payload"]["structure"],
                {
                    "checked": True,
                    "has_block": False,
                    "enumerated_items": 0,
                    "invariants_pinned": 1,
                    "invariants_missing": [1],
                    "pass": False,
                },
            )

    def test_missing_invariant_ordinal_rejects_true_but_records_false(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger = CoordinationLedger(directory / "events.sqlite3")
            ledger.record(
                run_id="run-missing-invariant",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["one", "two", "three", "four"]},
            )
            spec_path = directory / "dispatch.txt"
            receipt_path = directory / "receipt.txt"
            spec_path.write_text("dispatch", encoding="utf-8")
            receipt_path.write_text(
                "RECEIPT\n"
                "- INV-1: one\n"
                "- INV-2: two\n"
                "- INV-3: three\n",
                encoding="utf-8",
            )
            payload = {
                "verified": True,
                "dispatch_trigger_key": "dispatch:missing-invariant",
            }

            before = len(ledger.list_events())
            with self.assertRaises(ValueError) as raised:
                ledger.record(
                    run_id="run-missing-invariant",
                    task_slug="task",
                    event_type="receipt",
                    trigger_key="receipt:missing-invariant",
                    payload=payload,
                    spec_file=spec_path,
                    receipt_file=receipt_path,
                )
            after_rejection = len(ledger.list_events())
            error = str(raised.exception)
            self.assertEqual((before, after_rejection), (1, 1))
            self.assertIn("invariants_covered", error)
            self.assertIn("INV-4", error)

            payload["verified"] = False
            ledger.record(
                run_id="run-missing-invariant",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:missing-invariant",
                payload=payload,
                spec_file=spec_path,
                receipt_file=receipt_path,
            )
            events = ledger.list_events()
            self.assertEqual((after_rejection, len(events)), (1, 2))
            self.assertEqual(
                events[-1]["payload"]["structure"],
                {
                    "checked": True,
                    "has_block": True,
                    "enumerated_items": 3,
                    "invariants_pinned": 4,
                    "invariants_missing": [4],
                    "pass": False,
                },
            )

    def test_receipt_without_pinned_invariants_passes_vacuously(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            ledger = CoordinationLedger(directory / "events.sqlite3")
            spec_path = directory / "dispatch.txt"
            receipt_path = directory / "receipt.txt"
            spec_path.write_text("dispatch", encoding="utf-8")
            receipt_path.write_text(
                "# RECEIPT\n- CON-47: one mechanically enumerated item\n",
                encoding="utf-8",
            )

            ledger.record(
                run_id="run-no-invariants",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:no-invariants",
                payload={
                    "verified": True,
                    "dispatch_trigger_key": "dispatch:no-invariants",
                },
                spec_file=spec_path,
                receipt_file=receipt_path,
            )

            structure = ledger.list_events()[0]["payload"]["structure"]
            self.assertEqual(
                structure,
                {
                    "checked": True,
                    "has_block": True,
                    "enumerated_items": 1,
                    "invariants_pinned": 0,
                    "invariants_missing": [],
                    "pass": True,
                },
            )

    def test_verified_receipt_without_file_is_informational_only(self) -> None:
        fingerprint = {"sha256": "a" * 64, "utf8_bytes": 1}
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run-unchecked-receipt",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt:unchecked",
                payload={
                    "spec": fingerprint,
                    "receipt": fingerprint,
                    "verified": True,
                    "dispatch_trigger_key": "dispatch:unchecked",
                },
            )

            report = ledger.audit()
            self.assertEqual(
                report["receipts_verified_without_structure_check"],
                [
                    {
                        "id": 1,
                        "run_id": "run-unchecked-receipt",
                        "task_slug": "task",
                        "trigger_key": "receipt:unchecked",
                    }
                ],
            )
            self.assertEqual(
                report["totals"]["receipts_verified_without_structure_check"],
                1,
            )
            self.assertEqual(report["totals"]["findings"], 0)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), report)

    def test_audit_copy_preserves_existing_rows_and_missing_receipts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            source_path = directory / "live.sqlite3"
            copy_path = directory / "scratch.sqlite3"
            source = CoordinationLedger(source_path)
            source.record(
                run_id="run-copy-safety",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["one"]},
            )
            source.record(
                run_id="run-copy-safety",
                task_slug="task",
                event_type="dispatch",
                trigger_key="dispatch:copy-safety",
                payload={
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "tier": "priority",
                },
            )
            source_report = source.audit()
            source_before = source_path.read_bytes()
            copy_path.write_bytes(source_before)

            copy_report = CoordinationLedger(copy_path).audit()
            source_after = source_path.read_bytes()

            self.assertEqual(source_after, source_before)
            self.assertEqual(
                copy_report["totals"]["events"],
                source_report["totals"]["events"],
            )
            self.assertEqual(
                copy_report["dispatches_missing_receipt"],
                source_report["dispatches_missing_receipt"],
            )
            self.assertEqual(len(copy_report["dispatches_missing_receipt"]), 1)

    def test_receipt_requires_dispatch_trigger_key_without_writing(
        self,
    ) -> None:
        invalid_values = (
            ("missing", None, False),
            ("empty", "", True),
            ("non-string", 7, True),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._initialized_empty_ledger(
                Path(temp_dir) / "events.sqlite3"
            )
            for label, value, include_field in invalid_values:
                payload = {
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": False,
                }
                if include_field:
                    payload["dispatch_trigger_key"] = value
                before = len(ledger.list_events())
                with self.subTest(label=label), self.assertRaisesRegex(
                    ValueError,
                    "dispatch_trigger_key",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="receipt",
                        trigger_key=f"receipt:{label}",
                        payload=payload,
                    )
                after = len(ledger.list_events())
                self.assertEqual((before, after), (0, 0))

    def test_fact_records_claim_fingerprint_and_verbatim_provenance(self) -> None:
        claim = "reconciled result"
        provenance = "coordination:event:17"
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="fact",
                trigger_key="fact:valid",
                payload={"claim": claim, "provenance": provenance},
            )

            events = ledger.list_events()
            self.assertEqual(len(events), 1)
            stored = events[0]["payload"]
            self.assertEqual(
                set(stored["claim"]),
                {"sha256", "utf8_bytes"},
            )
            self.assertEqual(
                stored["claim"]["utf8_bytes"],
                len(claim.encode("utf-8")),
            )
            self.assertEqual(
                stored["claim"]["sha256"],
                hashlib.sha256(claim.encode("utf-8")).hexdigest(),
            )
            self.assertEqual(stored["provenance"], provenance)

    def test_fact_rejections_name_trigger_and_write_nothing(self) -> None:
        invalid_payloads = (
            (
                "fact:missing-claim",
                {"provenance": "coordination:event:17"},
            ),
            (
                "fact:empty-claim",
                {"claim": "", "provenance": "coordination:event:17"},
            ),
            ("fact:missing-provenance", {"claim": "claim"}),
            (
                "fact:empty-provenance",
                {"claim": "claim", "provenance": ""},
            ),
            (
                "fact:integer-provenance",
                {"claim": "claim", "provenance": 7},
            ),
            (
                "fact:bytes-provenance",
                {"claim": "claim", "provenance": b"source"},
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for trigger_key, payload in invalid_payloads:
                with self.subTest(trigger_key=trigger_key):
                    with self.assertRaises(ValueError) as raised:
                        ledger.record(
                            run_id="run",
                            task_slug="task",
                            event_type="fact",
                            trigger_key=trigger_key,
                            payload=payload,
                        )
                    message = str(raised.exception)
                    self.assertIn(
                        "fact record requires claim and provenance",
                        message,
                    )
                    self.assertIn(trigger_key, message)
                    self.assertEqual(ledger.list_events(), [])

    def test_receipt_and_fact_reject_malformed_sha256_without_writing(
        self,
    ) -> None:
        invalid_hashes = (
            ("63 chars", "a" * 63),
            ("uppercase", "A" * 64),
            ("non-hex", "g" * 64),
        )
        valid_fingerprint = {"sha256": "b" * 64, "utf8_bytes": 1}
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for label, invalid_hash in invalid_hashes:
                invalid_fingerprint = {
                    "sha256": invalid_hash,
                    "utf8_bytes": 1,
                }
                receipt_payload = {
                    "spec": invalid_fingerprint,
                    "receipt": valid_fingerprint,
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                }
                with self.subTest(path="receipt", value=label), patch(
                    "coordination_ledger._jsonable",
                    return_value=receipt_payload,
                ), self.assertRaisesRegex(
                    ValueError,
                    "receipt record requires spec, receipt, verified",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="receipt",
                        trigger_key="receipt",
                        payload={},
                    )
                self.assertEqual(ledger.list_events(), [])

                fact_payload = {
                    "claim": invalid_fingerprint,
                    "provenance": "coordination:event:17",
                }
                with self.subTest(path="fact", value=label), patch(
                    "coordination_ledger._jsonable",
                    return_value=fact_payload,
                ), self.assertRaisesRegex(
                    ValueError,
                    "fact record requires claim and provenance",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="fact",
                        trigger_key="fact",
                        payload={"provenance": "coordination:event:17"},
                    )
                self.assertEqual(ledger.list_events(), [])

    def test_audit_flags_raw_malformed_receipt_and_fact_sha256(self) -> None:
        invalid_hashes = (
            ("short", "a" * 63),
            ("uppercase", "A" * 64),
            ("nonhex", "g" * 64),
        )
        dispatch_payload = json.dumps(
            {
                "model": "gpt-5.6-sol",
                "effort": "xhigh",
                "tier": "priority",
            }
        )
        valid_fingerprint = {"sha256": "b" * 64, "utf8_bytes": 1}
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            rows = []
            for index, (label, invalid_hash) in enumerate(invalid_hashes):
                run_id = f"run-{label}"
                hour = index + 1
                invalid_fingerprint = {
                    "sha256": invalid_hash,
                    "utf8_bytes": 1,
                }
                rows.extend(
                    (
                        (
                            f"2026-08-11T{hour:02d}:00:00+00:00",
                            run_id,
                            "task",
                            "dispatch",
                            f"dispatch:{label}",
                            None,
                            1,
                            dispatch_payload,
                        ),
                        (
                            f"2026-08-11T{hour:02d}:00:01+00:00",
                            run_id,
                            "task",
                            "receipt",
                            f"receipt:{label}",
                            None,
                            1,
                            json.dumps(
                                {
                                    "spec": invalid_fingerprint,
                                    "receipt": valid_fingerprint,
                                    "verified": True,
                                }
                            ),
                        ),
                        (
                            f"2026-08-11T{hour:02d}:00:02+00:00",
                            run_id,
                            "task",
                            "fact",
                            f"fact:{label}",
                            None,
                            1,
                            json.dumps(
                                {
                                    "claim": invalid_fingerprint,
                                    "provenance": "coordination:event:17",
                                }
                            ),
                        ),
                    )
                )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            report = ledger.audit()
            self.assertEqual(
                [
                    item["trigger_key"]
                    for item in report["dispatches_missing_receipt"]
                ],
                ["dispatch:short", "dispatch:uppercase", "dispatch:nonhex"],
            )
            self.assertEqual(
                [
                    item["trigger_key"]
                    for item in report["facts_missing_provenance"]
                ],
                ["fact:short", "fact:uppercase", "fact:nonhex"],
            )
            self.assertEqual(report["totals"]["findings"], 6)

    def test_fact_rejects_and_audit_flags_whitespace_only_provenance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            with self.assertRaisesRegex(
                ValueError,
                "fact record requires claim and provenance",
            ):
                ledger.record(
                    run_id="run",
                    task_slug="task",
                    event_type="fact",
                    trigger_key="fact:whitespace",
                    payload={"claim": "claim", "provenance": "   "},
                )
            self.assertEqual(ledger.list_events(), [])

            claim = {
                "sha256": hashlib.sha256(b"claim").hexdigest(),
                "utf8_bytes": len(b"claim"),
            }
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                "2026-08-10T01:00:00+00:00",
                                "run",
                                "task",
                                "dispatch",
                                "dispatch",
                                None,
                                1,
                                json.dumps(
                                    {
                                        "model": "gpt-5.6-sol",
                                        "effort": "xhigh",
                                        "tier": "priority",
                                    }
                                ),
                            ),
                            (
                                "2026-08-10T01:00:01+00:00",
                                "run",
                                "task",
                                "fact",
                                "fact:whitespace",
                                None,
                                1,
                                json.dumps(
                                    {"claim": claim, "provenance": "   "}
                                ),
                            ),
                        ),
                    )

            report = ledger.audit()
            self.assertEqual(
                report["facts_missing_provenance"],
                [
                    {
                        "id": 2,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:whitespace",
                    }
                ],
            )
            self.assertEqual(report["totals"]["findings"], 1)

    def test_invariants_round_trip_bytes_and_rejections_write_nothing(self) -> None:
        invalid_payloads = (
            ("empty list", {"invariants": []}),
            ("empty string", {"invariants": [""]}),
            ("non-list", {"invariants": "not-a-list"}),
            ("missing key", {}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for label, payload in invalid_payloads:
                with self.subTest(label=label), self.assertRaisesRegex(
                    ValueError,
                    (
                        "invariants record requires a non-empty list of "
                        "non-empty strings"
                    ),
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="invariants",
                        trigger_key="invariants",
                        payload=payload,
                    )
                self.assertEqual(ledger.list_events(), [])

            invariants = ["stdlib only", "café invariance"]
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": invariants},
            )
            stored = ledger.list_events()[0]["payload"]["invariants"]
            self.assertEqual(stored, invariants)
            self.assertEqual(
                [item.encode("utf-8") for item in stored],
                [item.encode("utf-8") for item in invariants],
            )
            with closing(sqlite3.connect(ledger.path)) as connection:
                raw_payload = connection.execute(
                    """
                    SELECT payload_json
                    FROM coordination_events
                    WHERE event_type = 'invariants'
                    """
                ).fetchone()[0]
            self.assertIn("café invariance", raw_payload)

    def test_audit_gates_missing_receipts_by_epoch_and_window(self) -> None:
        dispatch_payload = json.dumps(
            {
                "model": "gpt-5.6-sol",
                "effort": "xhigh",
                "tier": "priority",
            }
        )
        receipt_payload = json.dumps(
            {
                "spec": {"sha256": "a" * 64, "utf8_bytes": 1},
                "receipt": {"sha256": "b" * 64, "utf8_bytes": 1},
                "verified": True,
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                "2026-08-11T00:00:00+00:00",
                                "run-post",
                                "task-post",
                                "dispatch",
                                "dispatch:post",
                                None,
                                1,
                                dispatch_payload,
                            ),
                            (
                                "2026-08-10T23:59:59+00:00",
                                "run-pre",
                                "task-pre",
                                "dispatch",
                                "dispatch:pre",
                                None,
                                1,
                                dispatch_payload,
                            ),
                        ),
                    )

            missing_report = ledger.audit()
            self.assertEqual(
                missing_report["dispatches_missing_receipt"],
                [
                    {
                        "id": 1,
                        "run_id": "run-post",
                        "task_slug": "task-post",
                        "trigger_key": "dispatch:post",
                    }
                ],
            )
            self.assertEqual(
                missing_report["totals"]["dispatches_missing_receipt"],
                1,
            )
            self.assertEqual(missing_report["totals"]["findings"], 1)

            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "2026-08-11T00:00:01+00:00",
                            "run-post",
                            "task-post",
                            "receipt",
                            "receipt:post",
                            None,
                            1,
                            receipt_payload,
                        ),
                    )

            covered_report = ledger.audit()
            self.assertEqual(covered_report["dispatches_missing_receipt"], [])
            self.assertEqual(
                covered_report["totals"]["dispatches_missing_receipt"],
                0,
            )
            self.assertEqual(covered_report["totals"]["findings"], 0)

            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                "2026-08-11T01:00:00+00:00",
                                "run-bounded",
                                "task-bounded",
                                "dispatch",
                                "dispatch:bounded:first",
                                None,
                                1,
                                dispatch_payload,
                            ),
                            (
                                "2026-08-11T01:00:02+00:00",
                                "run-bounded",
                                "task-bounded",
                                "dispatch",
                                "dispatch:bounded:second",
                                None,
                                1,
                                dispatch_payload,
                            ),
                            (
                                "2026-08-11T01:00:03+00:00",
                                "run-bounded",
                                "task-bounded",
                                "receipt",
                                "receipt:bounded",
                                None,
                                1,
                                receipt_payload,
                            ),
                            (
                                "not-a-timestamp",
                                "run-unparseable",
                                "task-unparseable",
                                "dispatch",
                                "dispatch:unparseable",
                                None,
                                1,
                                dispatch_payload,
                            ),
                        ),
                    )

            bounded_report = ledger.audit()
            self.assertEqual(
                bounded_report["dispatches_missing_receipt"],
                [
                    {
                        "id": 4,
                        "run_id": "run-bounded",
                        "task_slug": "task-bounded",
                        "trigger_key": "dispatch:bounded:first",
                    },
                    {
                        "id": 7,
                        "run_id": "run-unparseable",
                        "task_slug": "task-unparseable",
                        "trigger_key": "dispatch:unparseable",
                    },
                ],
            )
            self.assertEqual(
                bounded_report["totals"]["dispatches_missing_receipt"],
                2,
            )
            self.assertEqual(bounded_report["totals"]["findings"], 2)

    def test_audit_pairs_keyed_receipt_to_first_dispatch_after_second(
        self,
    ) -> None:
        dispatch_payload = {
            "model": "gpt-5.6-sol",
            "effort": "xhigh",
            "tier": "priority",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            recorded_times = (
                datetime.fromisoformat("2026-08-11T03:00:00+00:00"),
                datetime.fromisoformat(
                    "2026-08-11T03:00:00.100000+00:00"
                ),
                datetime.fromisoformat(
                    "2026-08-11T03:00:00.200000+00:00"
                ),
            )
            with patch("coordination_ledger.datetime") as ledger_datetime:
                ledger_datetime.now.side_effect = recorded_times
                ledger.record(
                    run_id="run-p33-keyed",
                    task_slug="task",
                    event_type="dispatch",
                    trigger_key="p33-probe-a:first",
                    payload=dispatch_payload,
                )
                ledger.record(
                    run_id="run-p33-keyed",
                    task_slug="task",
                    event_type="dispatch",
                    trigger_key="p33-probe-a:second",
                    payload=dispatch_payload,
                )
                ledger.record(
                    run_id="run-p33-keyed",
                    task_slug="task",
                    event_type="receipt",
                    trigger_key="receipt:p33-probe-a:first",
                    payload={
                        "spec": "dispatch",
                        "receipt": "reply",
                        "verified": False,
                        "dispatch_trigger_key": "p33-probe-a:first",
                    },
                )

            events = ledger.list_events()
            first_dispatch_at = datetime.fromisoformat(events[0]["created_at"])
            second_dispatch_at = datetime.fromisoformat(events[1]["created_at"])
            receipt_at = datetime.fromisoformat(events[2]["created_at"])
            self.assertLess(
                (second_dispatch_at - first_dispatch_at).total_seconds(),
                1,
            )
            self.assertGreater(receipt_at, second_dispatch_at)
            self.assertEqual(
                ledger.audit()["dispatches_missing_receipt"],
                [
                    {
                        "id": 2,
                        "run_id": "run-p33-keyed",
                        "task_slug": "task",
                        "trigger_key": "p33-probe-a:second",
                    }
                ],
            )

    def test_audit_any_keyed_receipt_selects_key_mode_when_invalid(
        self,
    ) -> None:
        fingerprint = {"sha256": "a" * 64, "utf8_bytes": 1}
        rows = (
            (
                "2026-08-11T04:00:00+00:00",
                "run-any-keyed-receipt",
                "task",
                "dispatch",
                "dispatch:any-keyed-receipt",
                None,
                1,
                json.dumps(
                    {
                        "model": "gpt-5.6-sol",
                        "effort": "xhigh",
                        "tier": "priority",
                    }
                ),
            ),
            (
                "2026-08-11T04:00:00.100000+00:00",
                "run-any-keyed-receipt",
                "task",
                "receipt",
                "receipt:invalid-keyed",
                None,
                1,
                json.dumps(
                    {
                        "spec": fingerprint,
                        "receipt": fingerprint,
                        "dispatch_trigger_key": (
                            "dispatch:any-keyed-receipt"
                        ),
                    }
                ),
            ),
            (
                "2026-08-11T04:00:00.200000+00:00",
                "run-any-keyed-receipt",
                "task",
                "receipt",
                "receipt:valid-keyless",
                None,
                1,
                json.dumps(
                    {
                        "spec": fingerprint,
                        "receipt": fingerprint,
                        "verified": False,
                    }
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            # Filtering run_uses_trigger_keys by valid_receipt_ids would use
            # the time window and let the valid keyless receipt match instead.
            self.assertEqual(
                ledger.audit()["dispatches_missing_receipt"],
                [
                    {
                        "id": 1,
                        "run_id": "run-any-keyed-receipt",
                        "task_slug": "task",
                        "trigger_key": "dispatch:any-keyed-receipt",
                    }
                ],
            )

    def test_audit_legacy_unkeyed_runs_keep_time_window_fallback(
        self,
    ) -> None:
        dispatch_payload = json.dumps(
            {
                "model": "gpt-5.6-sol",
                "effort": "xhigh",
                "tier": "priority",
            }
        )
        receipt_payload = json.dumps(
            {
                "spec": {"sha256": "a" * 64, "utf8_bytes": 1},
                "receipt": {"sha256": "b" * 64, "utf8_bytes": 1},
                "verified": False,
            }
        )
        rows = (
            (
                "2026-08-11T01:00:00+00:00",
                "run-legacy-covered",
                "task",
                "dispatch",
                "legacy-covered",
                None,
                1,
                dispatch_payload,
            ),
            (
                "2026-08-11T01:00:00.500000+00:00",
                "run-legacy-covered",
                "task",
                "receipt",
                "receipt:legacy-covered",
                None,
                1,
                receipt_payload,
            ),
            (
                "2026-08-11T02:00:00+00:00",
                "run-p33-legacy",
                "task",
                "dispatch",
                "p33-probe-a",
                None,
                1,
                dispatch_payload,
            ),
            (
                "2026-08-11T02:00:00.100000+00:00",
                "run-p33-legacy",
                "task",
                "dispatch",
                "p33-probe-b",
                None,
                1,
                dispatch_payload,
            ),
            (
                "2026-08-11T02:00:00.200000+00:00",
                "run-p33-legacy",
                "task",
                "receipt",
                "receipt:p33-probe-b",
                None,
                1,
                receipt_payload,
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            self.assertEqual(
                [
                    item["trigger_key"]
                    for item in ledger.audit()["dispatches_missing_receipt"]
                ],
                ["p33-probe-a"],
            )

    def test_audit_flags_directly_inserted_unpinned_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "2026-08-09T12:00:00+00:00",
                            "run",
                            "task",
                            "dispatch",
                            "dispatch",
                            None,
                            1,
                            json.dumps(
                                {
                                    "model": "gpt-5.6-sol",
                                    "effort": "high",
                                    "tier": "priority",
                                }
                            ),
                        ),
                    )

            report = ledger.audit()
            self.assertEqual(
                report["dispatch_missing_provenance"],
                [
                    {
                        "id": 1,
                        "run_id": "run",
                        "task_slug": "task",
                        "created_at": "2026-08-09T12:00:00+00:00",
                        "missing": ["effort"],
                    }
                ],
            )
            self.assertEqual(report["totals"]["dispatch_missing_provenance"], 1)
            self.assertEqual(report["totals"]["findings"], 1)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(stdout.getvalue())["totals"]["findings"], 1)

    def test_audit_flags_directly_inserted_invalid_facts(self) -> None:
        claim = "raw claim"
        claim_fingerprint = {
            "sha256": hashlib.sha256(claim.encode("utf-8")).hexdigest(),
            "utf8_bytes": len(claim.encode("utf-8")),
        }
        rows = (
            (
                "2026-08-10T09:00:00+00:00",
                "run",
                "task",
                "dispatch",
                "dispatch",
                None,
                1,
                json.dumps(
                    {
                        "model": "gpt-5.6-sol",
                        "effort": "xhigh",
                        "tier": "priority",
                    }
                ),
            ),
            (
                "2026-08-10T10:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:missing-provenance",
                None,
                1,
                json.dumps({"claim": claim_fingerprint}),
            ),
            (
                "2026-08-10T11:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:missing-claim",
                None,
                1,
                json.dumps({"provenance": "coordination:event:17"}),
            ),
            (
                "2026-08-10T12:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:unparseable",
                None,
                1,
                "not-json",
            ),
            (
                "2026-08-10T13:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:valid",
                None,
                1,
                json.dumps(
                    {
                        "claim": claim_fingerprint,
                        "provenance": "coordination:event:17",
                    }
                ),
            ),
            (
                "2026-08-10T14:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:wrong-claim-keys",
                None,
                1,
                json.dumps(
                    {
                        "claim": {**claim_fingerprint, "extra": True},
                        "provenance": "coordination:event:17",
                    }
                ),
            ),
            (
                "2026-08-10T15:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:boolean-utf8-bytes",
                None,
                1,
                json.dumps(
                    {
                        "claim": {
                            "sha256": claim_fingerprint["sha256"],
                            "utf8_bytes": True,
                        },
                        "provenance": "coordination:event:17",
                    }
                ),
            ),
            (
                "2026-08-10T16:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:empty-provenance",
                None,
                1,
                json.dumps(
                    {"claim": claim_fingerprint, "provenance": ""}
                ),
            ),
            (
                "2026-08-10T17:00:00+00:00",
                "run",
                "task",
                "fact",
                "fact:numeric-provenance",
                None,
                1,
                json.dumps(
                    {"claim": claim_fingerprint, "provenance": 7}
                ),
            ),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            report = ledger.audit()
            self.assertEqual(
                report["facts_missing_provenance"],
                [
                    {
                        "id": 2,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:missing-provenance",
                    },
                    {
                        "id": 3,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:missing-claim",
                    },
                    {
                        "id": 4,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:unparseable",
                    },
                    {
                        "id": 6,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:wrong-claim-keys",
                    },
                    {
                        "id": 7,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:boolean-utf8-bytes",
                    },
                    {
                        "id": 8,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:empty-provenance",
                    },
                    {
                        "id": 9,
                        "run_id": "run",
                        "task_slug": "task",
                        "trigger_key": "fact:numeric-provenance",
                    },
                ],
            )
            self.assertNotIn(
                "fact:valid",
                {
                    item["trigger_key"]
                    for item in report["facts_missing_provenance"]
                },
            )
            self.assertEqual(report["totals"]["facts_missing_provenance"], 7)
            self.assertEqual(report["totals"]["findings"], 7)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(stdout.getvalue()), report)

    def test_audit_missing_path_errors_without_creating_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "missing.sqlite3"
            expected = f"ledger database not found: {ledger_path.resolve()}"
            with self.assertRaises(ValueError) as raised:
                CoordinationLedger(ledger_path).audit()
            self.assertEqual(str(raised.exception), expected)
            self.assertFalse(ledger_path.exists())

            stdout = StringIO()
            stderr = StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = coordination_main(["audit", str(ledger_path)])
            self.assertEqual(exit_code, 1)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(
                json.loads(stderr.getvalue()),
                {"valid": False, "error": expected},
            )
            self.assertFalse(ledger_path.exists())

    def test_audit_existing_database_uses_read_only_connection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="configured",
                trigger_key="configured",
                payload={},
            )
            with patch(
                "coordination_ledger.sqlite3.connect",
                wraps=sqlite3.connect,
            ) as connect:
                report = ledger.audit()
            connect.assert_called_once_with(
                ledger.path.resolve().as_uri() + "?mode=ro",
                timeout=30,
                uri=True,
            )
            self.assertEqual(report["totals"]["events"], 1)

    def test_audit_percent_path_uses_encoded_read_only_uri(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "literal%20segment" / "events.sqlite3"
            decoded_path = Path(temp_dir) / "literal segment" / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="configured",
                trigger_key="configured",
                payload={},
            )
            expected_uri = ledger.path.resolve().as_uri() + "?mode=ro"
            self.assertIn("%2520", expected_uri)
            with patch(
                "coordination_ledger.sqlite3.connect",
                wraps=sqlite3.connect,
            ) as connect:
                report = ledger.audit()
            connect.assert_called_once_with(
                expected_uri,
                timeout=30,
                uri=True,
            )
            self.assertEqual(report["totals"]["events"], 1)
            self.assertTrue(ledger_path.exists())
            self.assertFalse(decoded_path.exists())

    def test_audit_clean_database_adds_empty_fact_keys_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._initialized_empty_ledger(
                Path(temp_dir) / "events.sqlite3"
            )
            self.assertEqual(
                ledger.audit(),
                {
                    "runs_missing_dispatch": [],
                    "runs_exempt_non_dispatch": [],
                    "dispatch_missing_provenance": [],
                    "signoffs_missing_verdict": [],
                    "attributed_events_missing_tag": [],
                    "dispatches_missing_receipt": [],
                    "facts_missing_provenance": [],
                    "receipt_fingerprints_caller_supplied": [],
                    "receipts_verified_without_structure_check": [],
                    "runs_missing_invariants": [],
                    "episode_events_total": 0,
                    "runs_with_no_episode_events": [],
                    "totals": {
                        "events": 0,
                        "runs": 0,
                        "episode_events": 0,
                        "runs_missing_dispatch": 0,
                        "runs_exempt_non_dispatch": 0,
                        "dispatch_missing_provenance": 0,
                        "signoffs_missing_verdict": 0,
                        "attributed_events_missing_tag": 0,
                        "dispatches_missing_receipt": 0,
                        "facts_missing_provenance": 0,
                        "receipt_fingerprints_caller_supplied": 0,
                        "receipts_verified_without_structure_check": 0,
                        "runs_missing_invariants": 0,
                        "runs_with_no_episode_events": 0,
                        "findings": 0,
                    },
                    "run_metrics": [],
                },
            )

    def test_audit_reports_runs_missing_invariants_without_findings(self) -> None:
        dispatch_payload = json.dumps(
            {
                "model": "gpt-5.6-sol",
                "effort": "xhigh",
                "tier": "priority",
            }
        )
        receipt_payload = json.dumps(
            {
                "spec": {"sha256": "a" * 64, "utf8_bytes": 1},
                "receipt": {"sha256": "b" * 64, "utf8_bytes": 1},
                "verified": True,
            }
        )
        rows = []

        def add_covered_run(
            run_id: str,
            hour: int,
            *,
            include_invariants: bool = False,
        ) -> None:
            rows.extend(
                (
                    (
                        f"2026-08-11T{hour:02d}:00:00+00:00",
                        run_id,
                        "task",
                        "dispatch",
                        f"dispatch:{run_id}:one",
                        None,
                        1,
                        dispatch_payload,
                    ),
                    (
                        f"2026-08-11T{hour:02d}:00:01+00:00",
                        run_id,
                        "task",
                        "receipt",
                        f"receipt:{run_id}:one",
                        None,
                        1,
                        receipt_payload,
                    ),
                    (
                        f"2026-08-11T{hour:02d}:00:02+00:00",
                        run_id,
                        "task",
                        "dispatch",
                        f"dispatch:{run_id}:two",
                        None,
                        1,
                        dispatch_payload,
                    ),
                    (
                        f"2026-08-11T{hour:02d}:00:03+00:00",
                        run_id,
                        "task",
                        "receipt",
                        f"receipt:{run_id}:two",
                        None,
                        1,
                        receipt_payload,
                    ),
                )
            )
            if include_invariants:
                rows.append(
                    (
                        f"2026-08-11T{hour:02d}:00:04+00:00",
                        run_id,
                        "task",
                        "invariants",
                        f"invariants:{run_id}",
                        None,
                        1,
                        json.dumps({"invariants": ["pinned"]}),
                    )
                )

        add_covered_run("run-b-missing", 1)
        add_covered_run("run-a-missing", 2)
        add_covered_run("run-with-invariants", 3, include_invariants=True)
        rows.extend(
            (
                (
                    "2026-08-10T01:00:00+00:00",
                    "run-pre-epoch",
                    "task",
                    "dispatch",
                    "dispatch:pre:one",
                    None,
                    1,
                    dispatch_payload,
                ),
                (
                    "2026-08-10T02:00:00+00:00",
                    "run-pre-epoch",
                    "task",
                    "dispatch",
                    "dispatch:pre:two",
                    None,
                    1,
                    dispatch_payload,
                ),
                (
                    "2026-08-11T04:00:00+00:00",
                    "run-one-dispatch",
                    "task",
                    "dispatch",
                    "dispatch:one",
                    None,
                    1,
                    dispatch_payload,
                ),
                (
                    "2026-08-11T04:00:01+00:00",
                    "run-one-dispatch",
                    "task",
                    "receipt",
                    "receipt:one",
                    None,
                    1,
                    receipt_payload,
                ),
            )
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            report = ledger.audit()
            self.assertEqual(
                report["runs_missing_invariants"],
                [
                    {
                        "run_id": "run-a-missing",
                        "task_slug": "task",
                        "dispatch_count": 2,
                    },
                    {
                        "run_id": "run-b-missing",
                        "task_slug": "task",
                        "dispatch_count": 2,
                    },
                ],
            )
            self.assertEqual(report["totals"]["runs_missing_invariants"], 2)
            self.assertEqual(report["totals"]["findings"], 0)

    def test_attributed_node_events_accept_exact_attribution_values(self) -> None:
        cases = (
            ("node_blocked", "spec-misread"),
            ("node_failed", "coordination"),
            ("node_rework", "verification"),
            ("node_failed", "infra"),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for index, (event_type, attribution) in enumerate(cases):
                ledger.record(
                    run_id="run",
                    task_slug="task",
                    event_type=event_type,
                    trigger_key=f"{event_type}:{index}",
                    payload={"attribution": attribution},
                )

            self.assertEqual(
                [
                    (event["event_type"], event["payload"]["attribution"])
                    for event in ledger.list_events()
                ],
                list(cases),
            )
            report = ledger.audit()
            self.assertEqual(report["attributed_events_missing_tag"], [])
            self.assertEqual(
                report["totals"]["attributed_events_missing_tag"], 0
            )

    def test_attributed_node_events_reject_invalid_tags_without_writing(
        self,
    ) -> None:
        class K:
            def __str__(self) -> str:
                return "attribution"

        invalid_cases = (
            ("node_blocked", None),
            ("node_failed", {}),
            ("node_rework", {"attribution": "Spec-misread"}),
            ("node_failed", {"attribution": " spec-misread"}),
            ("node_failed", {"attribution": "SPEC-MISREAD"}),
            ("node_failed", {"attribution": "other"}),
            ("node_failed", {"attribution": True}),
            ("node_failed", {"attribution": None}),
            ("node_failed", {"attribution": 1}),
            ("node_failed", {"attribution": "infra", K(): True}),
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for event_type, payload in invalid_cases:
                with self.subTest(
                    event_type=event_type,
                    payload=payload,
                ), self.assertRaisesRegex(
                    ValueError,
                    "attribution tag required",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type=event_type,
                        trigger_key=event_type,
                        payload=payload,
                    )
                self.assertEqual(ledger.list_events(), [])

    def test_audit_flags_directly_inserted_invalid_attribution_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="dispatch",
                trigger_key="dispatch",
                payload={
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "tier": "priority",
                },
            )
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            )
            rows = (
                (
                    "2026-08-10T12:00:00+00:00",
                    "run",
                    "task",
                    "node_failed",
                    "node_failed",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-08-10T13:00:00+00:00",
                    "run",
                    "task",
                    "node_blocked",
                    "node_blocked",
                    None,
                    1,
                    "not-json",
                ),
                (
                    "2026-08-10T14:00:00+00:00",
                    "run",
                    "task",
                    "node_rework",
                    "node_rework",
                    None,
                    1,
                    json.dumps({"attribution": "Spec-misread"}),
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            report = ledger.audit()
            self.assertEqual(
                report["attributed_events_missing_tag"],
                [
                    {
                        "id": 3,
                        "run_id": "run",
                        "task_slug": "task",
                        "event_type": "node_failed",
                        "attribution": "<missing>",
                    },
                    {
                        "id": 4,
                        "run_id": "run",
                        "task_slug": "task",
                        "event_type": "node_blocked",
                        "attribution": "<unparseable-payload>",
                    },
                    {
                        "id": 5,
                        "run_id": "run",
                        "task_slug": "task",
                        "event_type": "node_rework",
                        "attribution": "Spec-misread",
                    },
                ],
            )
            self.assertEqual(
                report["totals"]["attributed_events_missing_tag"], 3
            )
            self.assertEqual(report["totals"]["findings"], 3)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(stdout.getvalue())["totals"]["findings"], 3)

    def test_signoff_requires_decision_verdict_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for verdict in (None, "", " ", "CONFIRM"):
                with self.subTest(verdict=verdict), self.assertRaisesRegex(
                    ValueError,
                    "signoff verdict must be one of",
                ):
                    ledger.record(
                        run_id="run",
                        task_slug="task",
                        event_type="signoff",
                        trigger_key="signoff",
                        payload={},
                        verdict=verdict,
                    )
                self.assertEqual(ledger.list_events(), [])

            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="signoff",
                trigger_key="signoff",
                payload={},
                verdict="CONTINUE",
            )
            self.assertEqual(ledger.list_events()[0]["verdict"], "CONTINUE")

    def test_other_event_types_still_accept_arbitrary_payloads(self) -> None:
        event_types = (
            "report",
            "verification",
            "deviation",
            "lane_complete",
            "spec_defect",
            "dispatch_completed",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            for event_type in event_types:
                ledger.record(
                    run_id="run",
                    task_slug="task",
                    event_type=event_type,
                    trigger_key=f"info:{event_type}",
                    payload=["arbitrary", None, 1],
                )
            self.assertEqual(len(ledger.list_events()), len(event_types))

    def test_non_dispatch_event_type_allowlist_is_exact(self) -> None:
        self.assertEqual(
            _NON_DISPATCH_RUN_EVENT_TYPES,
            frozenset(
                {
                    "fable_attempt_started",
                    "fable_attempt_finished",
                    "sol_rewrite_started",
                    "sol_rewrite_finished",
                }
            ),
        )

    def test_invariants_only_run_is_coordinator_bookkeeping_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="invariants-only",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["pinned"]},
            )

            report = ledger.audit()
            self.assertEqual(
                report["runs_exempt_non_dispatch"],
                [
                    {
                        "run_id": "invariants-only",
                        "task_slug": "task",
                        "event_types": ["invariants"],
                    }
                ],
            )
            self.assertEqual(report["runs_missing_dispatch"], [])
            self.assertEqual(report["runs_missing_invariants"], [])

    def test_receipt_only_run_is_coordinator_bookkeeping_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="receipt-only",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch:receipt-only",
                },
            )

            report = ledger.audit()
            self.assertEqual(
                report["runs_exempt_non_dispatch"],
                [
                    {
                        "run_id": "receipt-only",
                        "task_slug": "task",
                        "event_types": ["receipt"],
                    }
                ],
            )
            self.assertEqual(report["runs_missing_dispatch"], [])

    def test_invariants_with_dispatch_is_not_bookkeeping_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="invariants-dispatch",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["pinned"]},
            )
            with closing(sqlite3.connect(ledger.path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "2026-08-10T01:00:00+00:00",
                            "invariants-dispatch",
                            "task",
                            "dispatch",
                            "dispatch",
                            None,
                            1,
                            json.dumps(
                                {
                                    "model": "gpt-5.6-sol",
                                    "effort": "high",
                                    "tier": "priority",
                                }
                            ),
                        ),
                    )

            report = ledger.audit()
            self.assertEqual(report["runs_exempt_non_dispatch"], [])
            self.assertEqual(report["runs_missing_dispatch"], [])
            self.assertEqual(
                report["dispatch_missing_provenance"][0]["missing"],
                ["effort"],
            )

    def test_invariants_receipt_dispatch_run_is_not_bookkeeping_exempt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="invariants-receipt-dispatch",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["pinned"]},
            )
            ledger.record(
                run_id="invariants-receipt-dispatch",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            )
            with closing(sqlite3.connect(ledger.path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "2026-08-10T01:00:00+00:00",
                            "invariants-receipt-dispatch",
                            "task",
                            "dispatch",
                            "dispatch",
                            None,
                            1,
                            json.dumps(
                                {
                                    "model": "gpt-5.6-sol",
                                    "effort": "high",
                                    "tier": "priority",
                                }
                            ),
                        ),
                    )

            self.assertEqual(
                {event["event_type"] for event in ledger.list_events()},
                {"invariants", "receipt", "dispatch"},
            )
            report = ledger.audit()
            self.assertEqual(report["runs_exempt_non_dispatch"], [])
            self.assertEqual(report["runs_missing_dispatch"], [])
            self.assertEqual(
                report["dispatch_missing_provenance"][0]["missing"],
                ["effort"],
            )

    def test_invariants_with_other_event_is_not_bookkeeping_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="invariants-report",
                task_slug="task",
                event_type="invariants",
                trigger_key="invariants",
                payload={"invariants": ["pinned"]},
            )
            ledger.record(
                run_id="invariants-report",
                task_slug="task",
                event_type="report",
                trigger_key="report",
                payload={},
            )

            report = ledger.audit()
            self.assertEqual(report["runs_exempt_non_dispatch"], [])
            self.assertEqual(
                [item["run_id"] for item in report["runs_missing_dispatch"]],
                ["invariants-report"],
            )

    def test_every_non_dispatch_event_type_is_exempt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            expected = {}
            for index, event_type in enumerate(
                sorted(_NON_DISPATCH_RUN_EVENT_TYPES)
            ):
                run_id = f"exempt-{index}"
                expected[run_id] = [event_type]
                ledger.record(
                    run_id=run_id,
                    task_slug="task",
                    event_type=event_type,
                    trigger_key=f"info:{event_type}:{index}",
                    payload={},
                )

            report = ledger.audit()
            self.assertEqual(
                {
                    item["run_id"]: item["event_types"]
                    for item in report["runs_exempt_non_dispatch"]
                },
                expected,
            )
            self.assertEqual(report["runs_missing_dispatch"], [])

    def test_mixing_any_non_dispatch_event_type_with_report_is_flagged(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            expected_run_ids = []
            for index, event_type in enumerate(
                sorted(_NON_DISPATCH_RUN_EVENT_TYPES)
            ):
                run_id = f"mixed-{index}"
                expected_run_ids.append(run_id)
                ledger.record(
                    run_id=run_id,
                    task_slug="task",
                    event_type=event_type,
                    trigger_key=f"info:{event_type}:{index}",
                    payload={},
                )
                ledger.record(
                    run_id=run_id,
                    task_slug="task",
                    event_type="report",
                    trigger_key=f"report:{index}",
                    payload={},
                )

            report = ledger.audit()
            self.assertEqual(report["runs_exempt_non_dispatch"], [])
            self.assertEqual(
                sorted(
                    item["run_id"]
                    for item in report["runs_missing_dispatch"]
                ),
                expected_run_ids,
            )

    def test_pause_only_run_is_missing_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="paused",
                task_slug="task",
                event_type="pause",
                trigger_key="pause",
                payload={},
            )
            report = ledger.audit()
            self.assertEqual(report["runs_exempt_non_dispatch"], [])
            self.assertEqual(
                [item["run_id"] for item in report["runs_missing_dispatch"]],
                ["paused"],
            )

    def test_audit_reports_legacy_findings_and_strict_exit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            rows = (
                (
                    "2026-07-25T01:00:00+00:00",
                    "run-a",
                    "task-a",
                    "dispatch",
                    "dispatch:a",
                    None,
                    1,
                    json.dumps(
                        {
                            "model": "gpt-5.6-sol",
                            "effort": "xhigh",
                            "tier": "priority",
                        }
                    ),
                ),
                (
                    "2026-07-25T02:00:00+00:00",
                    "run-a",
                    "task-a",
                    "signoff",
                    "signoff:a",
                    "CONTINUE",
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T03:00:00+00:00",
                    "run-b",
                    "task-b-old",
                    "report",
                    "report:b",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T04:00:00+00:00",
                    "run-b",
                    "task-b-new",
                    "signoff",
                    "signoff:b",
                    "CONFIRM",
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T05:00:00+00:00",
                    "run-c",
                    "task-c",
                    "dispatch",
                    "dispatch:c",
                    None,
                    1,
                    '{"effort": null, "model": "gpt-5.6-sol"}',
                ),
                (
                    "2026-07-25T06:00:00+00:00",
                    "run-d",
                    "task-d",
                    "dispatch",
                    "dispatch:d",
                    None,
                    1,
                    "{",
                ),
                (
                    "2026-07-25T07:00:00+00:00",
                    "run-d",
                    "task-d",
                    "signoff",
                    "signoff:d",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T08:00:00+00:00",
                    "run-d",
                    "task-d",
                    "signoff",
                    "signoff:d-blob",
                    sqlite3.Binary(b"\xffbad"),
                    1,
                    "{}",
                ),
            ) + tuple(
                (
                    f"2026-07-25T{index:02d}:00:00+00:00",
                    "run-fable",
                    "task-fable",
                    event_type,
                    f"info:{event_type}",
                    None,
                    1,
                    "{}",
                )
                for index, event_type in enumerate(
                    sorted(_NON_DISPATCH_RUN_EVENT_TYPES),
                    start=9,
                )
            ) + (
                (
                    "2026-07-25T13:00:00+00:00",
                    "run-mixed",
                    "task-mixed",
                    "fable_attempt_started",
                    "info:fable_attempt_started",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T14:00:00+00:00",
                    "run-mixed",
                    "task-mixed",
                    "report",
                    "report:mixed",
                    None,
                    1,
                    "{}",
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
            for run_id in ("run-a", "run-c", "run-e"):
                ledger.record_episode_event(
                    run_id=run_id,
                    event_kind="OBSERVATION",
                    subject="service",
                    trigger_key=f"info:{run_id}",
                    payload={},
                )

            report = ledger.audit()
            self.assertEqual(
                set(report),
                {
                    "runs_missing_dispatch",
                    "runs_exempt_non_dispatch",
                    "dispatch_missing_provenance",
                    "signoffs_missing_verdict",
                    "attributed_events_missing_tag",
                    "dispatches_missing_receipt",
                    "facts_missing_provenance",
                    "receipt_fingerprints_caller_supplied",
                    "receipts_verified_without_structure_check",
                    "runs_missing_invariants",
                    "episode_events_total",
                    "runs_with_no_episode_events",
                    "totals",
                    "run_metrics",
                },
            )
            self.assertEqual(
                report["runs_missing_dispatch"],
                [
                    {
                        "run_id": "run-b",
                        "task_slug": "task-b-new",
                        "first_seen": "2026-07-25T03:00:00+00:00",
                        "event_count": 2,
                    },
                    {
                        "run_id": "run-mixed",
                        "task_slug": "task-mixed",
                        "first_seen": "2026-07-25T13:00:00+00:00",
                        "event_count": 2,
                    },
                    {
                        "run_id": "run-e",
                        "task_slug": None,
                        "first_seen": None,
                        "event_count": 0,
                    },
                ],
            )
            self.assertEqual(
                report["runs_exempt_non_dispatch"],
                [
                    {
                        "run_id": "run-fable",
                        "task_slug": "task-fable",
                        "event_types": sorted(
                            _NON_DISPATCH_RUN_EVENT_TYPES
                        ),
                    }
                ],
            )
            self.assertEqual(
                report["dispatch_missing_provenance"],
                [
                    {
                        "id": 5,
                        "run_id": "run-c",
                        "task_slug": "task-c",
                        "created_at": "2026-07-25T05:00:00+00:00",
                        "missing": ["effort", "tier"],
                    },
                    {
                        "id": 6,
                        "run_id": "run-d",
                        "task_slug": "task-d",
                        "created_at": "2026-07-25T06:00:00+00:00",
                        "missing": ["<unparseable-payload>"],
                    },
                ],
            )
            self.assertEqual(
                report["signoffs_missing_verdict"],
                [
                    {
                        "id": 4,
                        "run_id": "run-b",
                        "task_slug": "task-b-new",
                        "created_at": "2026-07-25T04:00:00+00:00",
                        "verdict": "CONFIRM",
                    },
                    {
                        "id": 7,
                        "run_id": "run-d",
                        "task_slug": "task-d",
                        "created_at": "2026-07-25T07:00:00+00:00",
                        "verdict": None,
                    },
                    {
                        "id": 8,
                        "run_id": "run-d",
                        "task_slug": "task-d",
                        "created_at": "2026-07-25T08:00:00+00:00",
                        "verdict": "b'\\xffbad'",
                    },
                ],
            )
            self.assertEqual(report["episode_events_total"], 3)
            self.assertEqual(
                report["runs_with_no_episode_events"],
                [
                    {"run_id": "run-b", "task_slug": "task-b-new"},
                    {"run_id": "run-d", "task_slug": "task-d"},
                    {"run_id": "run-fable", "task_slug": "task-fable"},
                    {"run_id": "run-mixed", "task_slug": "task-mixed"},
                ],
            )
            self.assertEqual(
                report["totals"],
                {
                    "events": 14,
                    "runs": 7,
                    "episode_events": 3,
                    "runs_missing_dispatch": 3,
                    "runs_exempt_non_dispatch": 1,
                    "dispatch_missing_provenance": 2,
                    "signoffs_missing_verdict": 3,
                    "attributed_events_missing_tag": 0,
                    "dispatches_missing_receipt": 0,
                    "facts_missing_provenance": 0,
                    "receipt_fingerprints_caller_supplied": 0,
                    "receipts_verified_without_structure_check": 0,
                    "runs_missing_invariants": 0,
                    "runs_with_no_episode_events": 4,
                    "findings": 8,
                },
            )
            self.assertEqual(
                report["totals"]["findings"],
                report["totals"]["runs_missing_dispatch"]
                + report["totals"]["dispatch_missing_provenance"]
                + report["totals"]["signoffs_missing_verdict"]
                + report["totals"]["attributed_events_missing_tag"]
                + report["totals"]["dispatches_missing_receipt"]
                + report["totals"]["facts_missing_provenance"],
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(["audit", str(ledger_path)])
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), report)

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(ledger_path), "--strict"]
                )
            self.assertEqual(exit_code, 1)
            self.assertEqual(json.loads(stdout.getvalue()), report)

            clean_path = Path(temp_dir) / "clean.sqlite3"
            self._initialized_empty_ledger(clean_path)
            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    ["audit", str(clean_path), "--strict"]
                )
            self.assertEqual(exit_code, 0)
            clean_report = json.loads(stdout.getvalue())
            self.assertEqual(clean_report["totals"]["findings"], 0)
            self.assertIn("run_metrics", clean_report)

    def test_audit_reports_additive_per_run_and_node_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            dispatch_payload = {
                "model": "gpt-5.6-sol",
                "effort": "xhigh",
                "tier": "priority",
            }
            rows = (
                (
                    "2026-08-10T02:00:00+00:00",
                    "run-b",
                    "task-b",
                    "dispatch",
                    "dispatch:b",
                    None,
                    1,
                    json.dumps(
                        {
                            **dispatch_payload,
                            "tokens": 1234,
                            "prompt_tokens": 100,
                            "completion_tokens": 100,
                        }
                    ),
                ),
                (
                    "2026-08-10T01:00:00+00:00",
                    "run-a",
                    "task-a",
                    "dispatch",
                    "dispatch:a",
                    None,
                    1,
                    json.dumps(dispatch_payload),
                ),
                (
                    "2026-08-10T02:30:00+00:00",
                    "run-b",
                    "task-b",
                    "report",
                    "report:b",
                    None,
                    1,
                    json.dumps(
                        {"prompt_tokens": 2, "completion_tokens": 3}
                    ),
                ),
                (
                    "2026-08-10T03:00:00+00:00",
                    "run-b",
                    "task-b",
                    "signoff",
                    "signoff:b",
                    "CONTINUE",
                    1,
                    json.dumps({"token_count": 6}),
                ),
                (
                    "2026-08-10T01:00:00.500000+00:00",
                    "run-a",
                    "task-a",
                    "report",
                    "report:a",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-08-10T04:00:00+00:00",
                    "run-c",
                    "task-c",
                    "dispatch",
                    "dispatch:c",
                    None,
                    1,
                    json.dumps(dispatch_payload),
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )
            ledger.record_episode_event(
                run_id="episode-only",
                event_kind="OBSERVATION",
                subject="service",
                trigger_key="info:episode-only",
                payload={},
            )

            with patch("coordination_ledger._load_glassbox_events") as load:
                report = ledger.audit()
            load.assert_not_called()
            self.assertEqual(
                set(report) - {"run_metrics"},
                {
                    "runs_missing_dispatch",
                    "runs_exempt_non_dispatch",
                    "dispatch_missing_provenance",
                    "signoffs_missing_verdict",
                    "attributed_events_missing_tag",
                    "dispatches_missing_receipt",
                    "facts_missing_provenance",
                    "receipt_fingerprints_caller_supplied",
                    "receipts_verified_without_structure_check",
                    "runs_missing_invariants",
                    "episode_events_total",
                    "runs_with_no_episode_events",
                    "totals",
                },
            )
            self.assertEqual(
                report["run_metrics"],
                [
                    {
                        "run_id": "run-a",
                        "task_slug": "task-a",
                        "event_count": 2,
                        "first_event_utc": "2026-08-10T01:00:00+00:00",
                        "last_event_utc": (
                            "2026-08-10T01:00:00.500000+00:00"
                        ),
                        "ledger_wall_seconds": 0.5,
                        "closed": False,
                        "nodes": [
                            {
                                "trigger_key": "dispatch:a",
                                "created_at": (
                                    "2026-08-10T01:00:00+00:00"
                                ),
                                "ledger_next_event_seconds": 0.5,
                                "glassbox_pair_seconds": None,
                                "tokens": None,
                            }
                        ],
                        "tokens_total": None,
                        "untimed_nodes": 0,
                    },
                    {
                        "run_id": "run-b",
                        "task_slug": "task-b",
                        "event_count": 3,
                        "first_event_utc": "2026-08-10T02:00:00+00:00",
                        "last_event_utc": "2026-08-10T03:00:00+00:00",
                        "ledger_wall_seconds": 3600.0,
                        "closed": True,
                        "nodes": [
                            {
                                "trigger_key": "dispatch:b",
                                "created_at": (
                                    "2026-08-10T02:00:00+00:00"
                                ),
                                "ledger_next_event_seconds": 1800.0,
                                "glassbox_pair_seconds": None,
                                "tokens": 1234,
                            }
                        ],
                        "tokens_total": 1245,
                        "untimed_nodes": 0,
                    },
                    {
                        "run_id": "run-c",
                        "task_slug": "task-c",
                        "event_count": 1,
                        "first_event_utc": "2026-08-10T04:00:00+00:00",
                        "last_event_utc": "2026-08-10T04:00:00+00:00",
                        "ledger_wall_seconds": 0.0,
                        "closed": False,
                        "nodes": [
                            {
                                "trigger_key": "dispatch:c",
                                "created_at": (
                                    "2026-08-10T04:00:00+00:00"
                                ),
                                "ledger_next_event_seconds": None,
                                "glassbox_pair_seconds": None,
                                "tokens": None,
                            }
                        ],
                        "tokens_total": None,
                        "untimed_nodes": 1,
                    },
                ],
            )
            self.assertNotIn(
                "episode-only",
                [item["run_id"] for item in report["run_metrics"]],
            )
            self.assertEqual(
                json.dumps(report, ensure_ascii=False),
                json.dumps(ledger.audit(), ensure_ascii=False),
            )

    def test_audit_treats_nonfinite_tokens_as_null(self) -> None:
        dispatch_payload = {
            "model": "gpt-5.6-sol",
            "effort": "xhigh",
            "tier": "priority",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                "2026-08-10T01:00:00+00:00",
                                "run-inf",
                                "task",
                                "dispatch",
                                "dispatch:inf",
                                None,
                                1,
                                json.dumps(
                                    {**dispatch_payload, "tokens": float("inf")}
                                ),
                            ),
                            (
                                "2026-08-10T02:00:00+00:00",
                                "run-nan",
                                "task",
                                "dispatch",
                                "dispatch:nan",
                                None,
                                1,
                                json.dumps(
                                    {**dispatch_payload, "tokens": float("nan")}
                                ),
                            ),
                        ),
                    )

            metrics = {
                item["run_id"]: item for item in ledger.audit()["run_metrics"]
            }
            for run_id in ("run-inf", "run-nan"):
                with self.subTest(run_id=run_id):
                    self.assertIsNone(metrics[run_id]["nodes"][0]["tokens"])
                    self.assertIsNone(metrics[run_id]["tokens_total"])

    def test_audit_rejects_nonfinite_and_overflowing_token_sums(self) -> None:
        dispatch_payload = {
            "model": "gpt-5.6-sol",
            "effort": "xhigh",
            "tier": "priority",
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            (
                                "2026-08-10T01:00:00+00:00",
                                "run-sum-inf",
                                "task",
                                "dispatch",
                                "dispatch:sum-inf",
                                None,
                                1,
                                json.dumps(
                                    {
                                        **dispatch_payload,
                                        "prompt_tokens": sys.float_info.max,
                                        "completion_tokens": sys.float_info.max,
                                    }
                                ),
                            ),
                            (
                                "2026-08-10T02:00:00+00:00",
                                "run-sum-overflow",
                                "task",
                                "dispatch",
                                "dispatch:sum-overflow",
                                None,
                                1,
                                json.dumps(
                                    {
                                        **dispatch_payload,
                                        "prompt_tokens": 10**1000,
                                        "completion_tokens": 1.0,
                                    }
                                ),
                            ),
                        ),
                    )

            metrics = {
                item["run_id"]: item for item in ledger.audit()["run_metrics"]
            }
            for run_id in ("run-sum-inf", "run-sum-overflow"):
                with self.subTest(run_id=run_id):
                    self.assertIsNone(metrics[run_id]["nodes"][0]["tokens"])
                    self.assertIsNone(metrics[run_id]["tokens_total"])

    def test_audit_metrics_follow_ledger_id_timing_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            self._initialized_empty_ledger(ledger_path)
            rows = (
                (
                    "2026-08-10T02:00:00+00:00",
                    "run-negative",
                    "task",
                    "dispatch",
                    "dispatch:negative",
                    None,
                    1,
                    json.dumps(
                        {
                            "model": "gpt-5.6-sol",
                            "effort": "xhigh",
                            "tier": "priority",
                        }
                    ),
                ),
                (
                    "2026-08-10T01:00:00+00:00",
                    "run-negative",
                    "task",
                    "lane_complete",
                    "complete:negative",
                    None,
                    1,
                    "{}",
                ),
                (
                    "not-a-timestamp",
                    "run-invalid",
                    "task",
                    "report",
                    "report:invalid",
                    None,
                    1,
                    "{}",
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            metrics = CoordinationLedger(ledger_path).audit()["run_metrics"]
            by_run = {item["run_id"]: item for item in metrics}
            self.assertEqual(
                by_run["run-negative"]["first_event_utc"],
                "2026-08-10T02:00:00+00:00",
            )
            self.assertEqual(
                by_run["run-negative"]["last_event_utc"],
                "2026-08-10T01:00:00+00:00",
            )
            self.assertIsNone(
                by_run["run-negative"]["ledger_wall_seconds"]
            )
            self.assertTrue(by_run["run-negative"]["closed"])
            self.assertIsNone(
                by_run["run-negative"]["nodes"][0][
                    "ledger_next_event_seconds"
                ]
            )
            self.assertEqual(by_run["run-negative"]["untimed_nodes"], 1)
            self.assertIsNone(
                by_run["run-invalid"]["ledger_wall_seconds"]
            )

    def test_audit_uses_glassbox_pairing_and_cli_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = root / "events.sqlite3"
            glassbox_dir = root / "glassbox"
            glassbox_dir.mkdir()
            self._initialized_empty_ledger(ledger_path)
            dispatch_payload = json.dumps(
                {
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "tier": "priority",
                }
            )
            rows = (
                (
                    "2026-08-10T20:00:00+00:00",
                    "run-glassbox",
                    "task",
                    "dispatch",
                    "dispatch:one",
                    None,
                    1,
                    dispatch_payload,
                ),
                (
                    "2026-08-10T20:00:05+00:00",
                    "run-glassbox",
                    "task",
                    "report",
                    "report:one",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-08-10T20:00:06+00:00",
                    "run-glassbox",
                    "task",
                    "dispatch",
                    "dispatch:two",
                    None,
                    1,
                    dispatch_payload,
                ),
                (
                    "2026-08-10T20:00:00+00:00",
                    "run-no-complete",
                    "task",
                    "report",
                    "report:no-complete",
                    None,
                    1,
                    "{}",
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            def write_event(name: str, **values: object) -> None:
                event = {
                    "schema_version": 1,
                    "id": name,
                    "timestamp_utc": "2026-08-10T20:00:00Z",
                    "run_id": "run-glassbox",
                    "correlation_id": "",
                    "lane": "codex",
                    "kind": "run.started",
                    "status": "ok",
                    "stage": "run",
                }
                event.update(values)
                (glassbox_dir / f"{name}.json").write_text(
                    json.dumps(event), encoding="utf-8"
                )

            write_event(
                "01-run-start",
                id="run-start-a",
                timestamp_utc="2026-08-10T20:00:00.0000000Z",
            )
            write_event(
                "02-run-start",
                id="run-start-b",
                timestamp_utc="2026-08-10T20:00:05Z",
            )
            write_event(
                "03-run-completed",
                id="run-end-a",
                timestamp_utc="2026-08-10T20:01:00Z",
                kind="run.completed",
            )
            write_event(
                "04-run-completed",
                id="run-end-b",
                timestamp_utc="2026-08-10T20:02:00.1234567Z",
                kind="run.completed",
            )
            write_event(
                "05-dispatch-start",
                id="dispatch-start-a",
                timestamp_utc="2026-08-10T20:00:10Z",
                correlation_id="dispatch-a",
                lane="claude",
                kind="dispatch.started",
                stage="dispatch-a",
            )
            write_event(
                "06-dispatch-completed",
                id="dispatch-end-a",
                timestamp_utc="2026-08-10T20:00:12Z",
                correlation_id="dispatch-a",
                lane="claude",
                kind="dispatch.completed",
                stage="different-stage",
            )
            write_event(
                "07-dispatch-start",
                id="dispatch-start-b",
                timestamp_utc="2026-08-10T20:00:20Z",
                kind="dispatch.started",
                stage="dispatch-b",
            )
            write_event(
                "08-dispatch-completed",
                id="dispatch-end-b",
                timestamp_utc="2026-08-10T20:00:23Z",
                kind="dispatch.completed",
                stage="dispatch-b",
            )
            write_event(
                "08c-dispatch-start",
                id="dispatch-start-unallocated",
                timestamp_utc="2026-08-10T20:00:25Z",
                correlation_id="dispatch-unallocated",
                kind="dispatch.started",
                stage="dispatch-unallocated",
            )
            write_event(
                "08d-dispatch-completed",
                id="dispatch-end-unallocated",
                timestamp_utc="2026-08-10T20:00:29Z",
                correlation_id="dispatch-unallocated",
                kind="dispatch.completed",
                stage="dispatch-unallocated",
            )
            write_event(
                "09-stage-start",
                id="stage-start",
                timestamp_utc="2026-08-10T20:00:30Z",
                correlation_id="stage-a",
                kind="stage.started",
                stage="spine",
            )
            write_event(
                "10-stage-completed",
                id="stage-end",
                timestamp_utc="2026-08-10T20:00:40Z",
                correlation_id="stage-a",
                kind="stage.completed",
                stage="spine",
            )
            write_event(
                "11-agent-start",
                id="agent-start",
                timestamp_utc="2026-08-10T20:00:50Z",
                lane="claude",
                kind="agent.started",
                stage="side",
            )
            write_event(
                "12-agent-completed",
                id="agent-end",
                timestamp_utc="2026-08-10T20:01:10Z",
                lane="claude",
                kind="agent.completed",
                stage="side",
            )
            write_event(
                "13-unmatched",
                id="stage-unmatched",
                timestamp_utc="2026-08-10T20:01:20Z",
                lane="gemini",
                kind="stage.started",
                stage="unmatched",
            )
            write_event(
                "14-invalid-time",
                id="run-end-invalid",
                timestamp_utc="invalid",
                kind="run.completed",
            )
            write_event(
                "15-no-complete",
                id="no-complete-start",
                run_id="run-no-complete",
            )
            write_event(
                "16-other-run",
                id="other-run-start",
                run_id="other-run",
            )
            write_event("17-wrong-schema", schema_version=2)
            missing_run = {
                "schema_version": 1,
                "id": "missing-run",
                "timestamp_utc": "2026-08-10T20:00:00Z",
                "correlation_id": "",
                "lane": "codex",
                "kind": "run.started",
                "status": "ok",
                "stage": "run",
            }
            (glassbox_dir / "18-missing-run.json").write_text(
                json.dumps(missing_run), encoding="utf-8"
            )
            (glassbox_dir / "19-invalid.json").write_text(
                "{", encoding="utf-8"
            )

            report = CoordinationLedger(ledger_path).audit(
                glassbox_dir=glassbox_dir
            )
            by_run = {
                item["run_id"]: item for item in report["run_metrics"]
            }
            metric = by_run["run-glassbox"]
            self.assertEqual(metric["glassbox_run_seconds"], 120.123)
            self.assertEqual(metric["serial_spine_seconds"], 19.0)
            self.assertEqual(metric["parallel_side_seconds"], 20.0)
            self.assertEqual(metric["glassbox_events_matched"], 16)
            self.assertEqual(
                [node["ledger_next_event_seconds"] for node in metric["nodes"]],
                [5.0, None],
            )
            self.assertEqual(
                [node["glassbox_pair_seconds"] for node in metric["nodes"]],
                [2.0, 3.0],
            )
            self.assertEqual(metric["untimed_nodes"], 0)
            self.assertIsNone(
                by_run["run-no-complete"]["glassbox_run_seconds"]
            )

            stdout = StringIO()
            with redirect_stdout(stdout):
                exit_code = coordination_main(
                    [
                        "audit",
                        str(ledger_path),
                        "--glassbox-dir",
                        str(glassbox_dir),
                    ]
                )
            self.assertEqual(exit_code, 0)
            self.assertEqual(json.loads(stdout.getvalue()), report)

    def test_audit_handles_timezone_normalization_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            self._initialized_empty_ledger(ledger_path)
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.execute(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            "0001-01-01T00:00:00+01:00",
                            "run-overflow",
                            "task",
                            "report",
                            "report:overflow",
                            None,
                            1,
                            "{}",
                        ),
                    )

            report = CoordinationLedger(ledger_path).audit()
            metric = report["run_metrics"][0]
            self.assertEqual(metric["run_id"], "run-overflow")
            self.assertIsNone(metric["ledger_wall_seconds"])

    def test_audit_rejects_boolean_glassbox_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            glassbox_dir = root / "glassbox"
            glassbox_dir.mkdir()
            ledger = CoordinationLedger(root / "events.sqlite3")
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="report",
                trigger_key="report",
                payload={},
            )
            valid_event = {
                "schema_version": 1,
                "id": "valid",
                "timestamp_utc": "2026-08-10T20:00:00Z",
                "run_id": "run",
                "correlation_id": "",
                "lane": "codex",
                "kind": "run.started",
                "status": "ok",
                "stage": "run",
            }
            boolean_schema_event = {
                **valid_event,
                "schema_version": True,
                "id": "boolean-schema",
            }
            (glassbox_dir / "valid.json").write_text(
                json.dumps(valid_event), encoding="utf-8"
            )
            (glassbox_dir / "boolean-schema.json").write_text(
                json.dumps(boolean_schema_event), encoding="utf-8"
            )

            metric = ledger.audit(glassbox_dir=glassbox_dir)["run_metrics"][0]
            self.assertEqual(metric["glassbox_events_matched"], 1)

    def test_audit_empty_ledger_has_no_run_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = self._initialized_empty_ledger(
                Path(temp_dir) / "events.sqlite3"
            )
            self.assertEqual(ledger.audit()["run_metrics"], [])

    def test_audit_orders_first_seen_by_parsed_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "events.sqlite3"
            self._initialized_empty_ledger(ledger_path)
            rows = (
                (
                    "2026-07-25T03:00:00+02:00",
                    "run-a",
                    "task-a",
                    "report",
                    "report:a-1",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T01:30:00+00:00",
                    "run-a",
                    "task-a",
                    "report",
                    "report:a-2",
                    None,
                    1,
                    "{}",
                ),
                (
                    "2026-07-25T01:15:00+00:00",
                    "run-b",
                    "task-b",
                    "report",
                    "report:b",
                    None,
                    1,
                    "{}",
                ),
                (
                    "z-invalid",
                    "run-c",
                    "task-c",
                    "report",
                    "report:c-1",
                    None,
                    1,
                    "{}",
                ),
                (
                    "a-invalid",
                    "run-c",
                    "task-c",
                    "report",
                    "report:c-2",
                    None,
                    1,
                    "{}",
                ),
            )
            with closing(sqlite3.connect(ledger_path)) as connection:
                with connection:
                    connection.executemany(
                        """
                        INSERT INTO coordination_events(
                            created_at, run_id, task_slug, event_type,
                            trigger_key, verdict, occurrence, payload_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        rows,
                    )

            findings = CoordinationLedger(ledger_path).audit()[
                "runs_missing_dispatch"
            ]
            self.assertEqual(
                [item["run_id"] for item in findings[:2]],
                ["run-a", "run-b"],
            )
            self.assertEqual(
                findings[0]["first_seen"],
                "2026-07-25T03:00:00+02:00",
            )
            run_c = next(
                item for item in findings if item["run_id"] == "run-c"
            )
            self.assertEqual(run_c["first_seen"], "a-invalid")

    def test_mixed_timestamp_order_is_stable_across_insertion_order(
        self,
    ) -> None:
        rows = (
            (
                "a-invalid",
                "run-a",
                "task-a",
                "report",
                "report:a-invalid",
                None,
                1,
                "{}",
            ),
            (
                "2026-07-25T02:00:00+00:00",
                "run-a",
                "task-a",
                "report",
                "report:a-valid",
                None,
                1,
                "{}",
            ),
            (
                "2026-07-25T01:00:00+00:00",
                "run-b",
                "task-b",
                "report",
                "report:b-valid",
                None,
                1,
                "{}",
            ),
            (
                "b-invalid",
                "run-c",
                "task-c",
                "report",
                "report:c-invalid",
                None,
                1,
                "{}",
            ),
        )

        def audit_rows(
            ordered_rows: tuple[tuple[object, ...], ...],
        ) -> list[tuple[object, object]]:
            with tempfile.TemporaryDirectory() as temp_dir:
                ledger_path = Path(temp_dir) / "events.sqlite3"
                self._initialized_empty_ledger(ledger_path)
                with closing(sqlite3.connect(ledger_path)) as connection:
                    with connection:
                        connection.executemany(
                            """
                            INSERT INTO coordination_events(
                                created_at, run_id, task_slug, event_type,
                                trigger_key, verdict, occurrence, payload_json
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            ordered_rows,
                        )
                findings = CoordinationLedger(ledger_path).audit()[
                    "runs_missing_dispatch"
                ]
                return [
                    (item["run_id"], item["first_seen"])
                    for item in findings
                ]

        expected = [
            ("run-b", "2026-07-25T01:00:00+00:00"),
            ("run-a", "2026-07-25T02:00:00+00:00"),
            ("run-c", "b-invalid"),
        ]
        self.assertEqual(audit_rows(rows), expected)
        self.assertEqual(audit_rows(tuple(reversed(rows))), expected)

    def test_audit_treats_recursive_json_as_unparseable(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="dispatch",
                trigger_key="dispatch",
                payload={
                    "model": "gpt-5.6-sol",
                    "effort": "xhigh",
                    "tier": "priority",
                },
            )
            ledger.record(
                run_id="run",
                task_slug="task",
                event_type="receipt",
                trigger_key="receipt",
                payload={
                    "spec": "spec",
                    "receipt": "receipt",
                    "verified": True,
                    "dispatch_trigger_key": "dispatch",
                },
            )
            with patch(
                "coordination_ledger.json.loads",
                side_effect=RecursionError,
            ):
                report = ledger.audit()
            self.assertEqual(
                report["dispatch_missing_provenance"][0]["missing"],
                ["<unparseable-payload>"],
            )

    def test_record_episode_event_initializes_fresh_database(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger_path = Path(temp_dir) / "fresh" / "events.sqlite3"
            ledger = CoordinationLedger(ledger_path)
            self.assertFalse(ledger_path.exists())

            sequence = ledger.record_episode_event(
                run_id="run",
                event_kind="OBSERVATION",
                subject="service",
                trigger_key="trigger",
                payload={"marker": "first"},
            )

            self.assertEqual(sequence, 1)
            self.assertTrue(ledger_path.exists())
            episode = ledger.episode(run_id="run")
            self.assertEqual(len(episode), 1)
            self.assertEqual(episode[0]["sequence"], 1)
            self.assertEqual(episode[0]["payload"], {"marker": "first"})

    def test_dc08_episode_subject_dedupe_and_version_guard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ledger_path = root / "events.sqlite3"
            ledger = self._initialized_empty_ledger(ledger_path)
            reopened = CoordinationLedger(ledger_path)
            self.assertEqual(reopened.episode(run_id="run"), [])
            first = ledger.record_episode_event(
                run_id="run",
                event_kind="OBSERVATION",
                subject="service-a",
                trigger_key="same",
                payload={"marker": "same"},
            )
            second = ledger.record_episode_event(
                run_id="run",
                event_kind="OBSERVATION",
                subject="service-b",
                trigger_key="same",
                payload={"marker": "same"},
            )
            duplicate = ledger.record_episode_event(
                run_id="run",
                event_kind="OBSERVATION",
                subject="service-a",
                trigger_key="same",
                payload={"marker": "same"},
            )
            self.assertEqual((first, second, duplicate), (1, 2, 1))

            def existing_episode_database(
                path: Path,
                version: int | None,
                *,
                create_episode_table: bool = True,
            ) -> None:
                with closing(sqlite3.connect(path)) as connection:
                    with connection:
                        connection.execute(
                            """
                            CREATE TABLE coordination_schema (
                                name TEXT PRIMARY KEY,
                                version INTEGER NOT NULL
                            )
                            """
                        )
                        if version is not None:
                            connection.execute(
                                """
                                INSERT INTO coordination_schema(name, version)
                                VALUES ('episode_events', ?)
                                """,
                                (version,),
                            )
                        if create_episode_table:
                            connection.execute(
                                """
                                CREATE TABLE coordination_episode_events (
                                    id INTEGER PRIMARY KEY
                                )
                                """
                            )

            for name, version in (("older.sqlite3", 2), ("missing.sqlite3", None)):
                with self.subTest(name=name):
                    path = root / name
                    existing_episode_database(path, version)
                    with self.assertRaises(ValueError) as raised:
                        CoordinationLedger(path).record_episode_event(
                            run_id="run",
                            event_kind="OBSERVATION",
                            subject="service",
                            trigger_key="trigger",
                            payload={},
                        )
                    message = str(raised.exception)
                    self.assertIn(str(path.resolve()), message)
                    self.assertIn("schema v2", message)
                    self.assertIn("runtime's v3", message)

            newer = root / "newer.sqlite3"
            existing_episode_database(newer, 4)
            with self.assertRaises(ValueError) as raised:
                CoordinationLedger(newer).record_episode_event(
                    run_id="run",
                    event_kind="OBSERVATION",
                    subject="service",
                    trigger_key="trigger",
                    payload={},
                )
            message = str(raised.exception)
            self.assertIn(str(newer.resolve()), message)
            self.assertIn(
                "ledger schema v4 is newer than this runtime's v3",
                message,
            )

            newer_without_table = root / "newer-without-table.sqlite3"
            existing_episode_database(
                newer_without_table,
                4,
                create_episode_table=False,
            )
            with self.assertRaises(ValueError) as raised:
                CoordinationLedger(newer_without_table).record_episode_event(
                    run_id="run",
                    event_kind="OBSERVATION",
                    subject="service",
                    trigger_key="trigger",
                    payload={},
                )
            self.assertIn(
                "ledger schema v4 is newer than this runtime's v3",
                str(raised.exception),
            )
            with closing(sqlite3.connect(newer_without_table)) as connection:
                stored_version = connection.execute(
                    """
                    SELECT version FROM coordination_schema
                    WHERE name = 'episode_events'
                    """
                ).fetchone()[0]
                episode_table = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'coordination_episode_events'
                    """
                ).fetchone()
            self.assertEqual(stored_version, 4)
            self.assertIsNone(episode_table)

    def test_dc09_secret_key_segments_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            ledger = CoordinationLedger(Path(temp_dir) / "events.sqlite3")
            ledger.record(
                run_id="one",
                task_slug="task",
                event_type="configured",
                trigger_key="configured",
                payload={
                    "auth_token": "private",
                    "Bearer_Token": "private",
                    "openai_api_key": "private",
                    "client_secret": "private",
                    "aws_secret_access_key": "private",
                    "session_cookie": "private",
                    "password": b"private",
                    "credentials": ["private"],
                    "api_key": ("private",),
                    "private_key": {"value": "private"},
                    "token_set": {"private"},
                    "token_count": 2,
                    "prompt_tokens": 100,
                    "auth_enabled": False,
                    "secret": None,
                    "rank_authority": "reviewer",
                    "trigger_key": "retry:flag",
                },
            )
            payload = ledger.list_events()[0]["payload"]
            for key in (
                "auth_token",
                "Bearer_Token",
                "openai_api_key",
                "client_secret",
                "aws_secret_access_key",
                "session_cookie",
                "password",
                "credentials",
                "api_key",
                "private_key",
                "token_set",
            ):
                with self.subTest(key=key):
                    self.assertEqual(payload[key], {"redacted": True})
            self.assertEqual(payload["token_count"], 2)
            self.assertEqual(payload["prompt_tokens"], 100)
            self.assertIs(payload["auth_enabled"], False)
            self.assertIsNone(payload["secret"])
            self.assertEqual(payload["rank_authority"], "reviewer")
            self.assertEqual(payload["trigger_key"], "retry:flag")


class ContractTests(unittest.TestCase):
    def test_complete_contract_is_valid(self) -> None:
        contract = ExecutionContract.from_mapping(
            {
                "objective": "Implement it",
                "constraints": ["No new dependencies"],
                "acceptance_criteria": ["Tests pass"],
                "impact_envelope": {
                    "files": ["a.py"],
                    "processes": ["python -m unittest"],
                },
                "confirmation_conditions": ["Return before merge"],
            }
        )
        self.assertEqual(contract.objective, "Implement it")

    def test_contract_rejects_empty_envelope(self) -> None:
        with self.assertRaises(ContractError):
            ExecutionContract.from_mapping(
                {
                    "objective": "Implement it",
                    "constraints": ["Safe"],
                    "acceptance_criteria": ["Done"],
                    "impact_envelope": {"files": [], "processes": []},
                    "confirmation_conditions": ["Review"],
                }
            )

    def test_contract_rejects_string_where_array_is_required(self) -> None:
        with self.assertRaises(ContractError):
            ExecutionContract.from_mapping(
                {
                    "objective": "Implement it",
                    "constraints": "Safe",
                    "acceptance_criteria": ["Done"],
                    "impact_envelope": {"files": ["a.py"], "processes": []},
                    "confirmation_conditions": ["Review"],
                }
            )

    def test_dc11_direct_tuple_fields_reject_non_sequences(self) -> None:
        contract_values = {
            "objective": "Implement it",
            "constraints": ("Safe",),
            "acceptance_criteria": ("Done",),
            "impact_files": ("a.py",),
            "impact_processes": (),
            "confirmation_conditions": ("Review",),
        }
        invalid_contract_fields = (
            ("constraints", "Safe"),
            ("acceptance_criteria", b"Done"),
            ("impact_files", {"a.py": True}),
            ("impact_processes", "python"),
            ("confirmation_conditions", {"review": "required"}),
        )
        for field, invalid in invalid_contract_fields:
            with self.subTest(dataclass="ExecutionContract", field=field):
                values = dict(contract_values)
                values[field] = invalid
                with self.assertRaises(ContractError):
                    ExecutionContract(**values)

        handshake_values = {
            "tools_verified": ("git",),
            "permissions_verified": ("workspace",),
            "files_verified": ("a.py",),
            "reversal_options": ("manual patch reversal",),
        }
        with self.assertRaises(ContractError):
            CapabilityHandshake(
                readiness=Readiness.READY,
                tools_verified={"git": True},
                permissions_verified=handshake_values["permissions_verified"],
                files_verified=handshake_values["files_verified"],
                reversal_options=handshake_values["reversal_options"],
            )
        with self.assertRaises(ContractError):
            CapabilityHandshake(
                readiness=Readiness.READY_WITH_LIMITS,
                limits="network unavailable",
                **handshake_values,
            )

        with self.assertRaises(ContractError):
            CorrectionReport(
                trigger="risk",
                evidence_observed="evidence",
                immediate_risk="damage",
                action_taken="stopped process",
                affected_state=b"process",
                proportionality="small",
                reversal="restart",
                current_safe_state="safe",
                recommended_next_step="review",
                confirmation_requested="CONFIRM",
            )

        with self.assertRaises(ContractError):
            DecisionRequest(
                intended_result="one",
                actual_result="two",
                evidence="exit 1",
                current_state="paused",
                options="retry",
                risks=("may fail",),
                recommended_option="retry",
                reversal_procedure="discard worktree",
                decision_required="choose",
            )

    def test_dc12_missing_handshake_limits_defaults_empty(self) -> None:
        common = {
            "readiness": "READY",
            "tools_verified": ["git"],
            "permissions_verified": ["workspace"],
            "files_verified": ["a.py"],
            "reversal_options": ["manual patch reversal"],
        }
        handshake = CapabilityHandshake.from_mapping(common)
        self.assertEqual(handshake.limits, ())

        invalid_limits = dict(common)
        invalid_limits["readiness"] = "READY_WITH_LIMITS"
        invalid_limits["limits"] = "network unavailable"
        with self.assertRaises(ContractError):
            CapabilityHandshake.from_mapping(invalid_limits)

        ready_with_limits = dict(common)
        ready_with_limits["limits"] = ["network unavailable"]
        with self.assertRaises(ContractError):
            CapabilityHandshake.from_mapping(ready_with_limits)

        missing_required_limits = dict(common)
        missing_required_limits["readiness"] = "READY_WITH_LIMITS"
        with self.assertRaises(ContractError):
            CapabilityHandshake.from_mapping(missing_required_limits)

    def test_handshake_state_specific_fields(self) -> None:
        common = {
            "tools_verified": ("git",),
            "permissions_verified": ("workspace",),
            "files_verified": ("a.py",),
            "reversal_options": ("discard worktree",),
        }
        CapabilityHandshake(readiness=Readiness.READY, **common)
        CapabilityHandshake(
            readiness=Readiness.READY_WITH_LIMITS,
            limits=("network unavailable",),
            **common,
        )
        with self.assertRaises(ContractError):
            CapabilityHandshake(
                readiness=Readiness.READY_WITH_LIMITS,
                **common,
            )
        with self.assertRaises(ContractError):
            CapabilityHandshake(readiness=Readiness.BLOCKED, **common)
        with self.assertRaises(ContractError):
            CapabilityHandshake.from_mapping(
                {
                    "readiness": "READY",
                    "tools_verified": "git",
                    "permissions_verified": ["workspace"],
                    "files_verified": ["a.py"],
                    "reversal_options": ["discard worktree"],
                    "limits": [],
                }
            )

    def test_verdict_vocabularies_do_not_mix(self) -> None:
        self.assertEqual(
            validate_verdict(ReportKind.CORRECTION, "CONFIRM"), "CONFIRM"
        )
        with self.assertRaises(ValueError):
            validate_verdict(ReportKind.DECISION, "CONFIRM")

    def test_reports_validate_required_fields(self) -> None:
        CorrectionReport.from_mapping(
            {
                "trigger": "runaway process",
                "evidence_observed": "output grew continuously",
                "immediate_risk": "disk exhaustion",
                "action_taken": "stopped process 123",
                "affected_state": ["process 123"],
                "proportionality": "stopping only",
                "reversal": "restart from the top",
                "current_safe_state": "process stopped",
                "recommended_next_step": "inspect logs",
                "confirmation_requested": "CONFIRM or MODIFY",
            }
        )
        with self.assertRaises(ContractError):
            CorrectionReport.from_mapping(
                {
                    "trigger": "risk",
                    "evidence_observed": "evidence",
                    "immediate_risk": "damage",
                    "action_taken": "none",
                    "affected_state": ["process"],
                    "proportionality": "small",
                    "reversal": "restart",
                    "current_safe_state": "safe",
                    "recommended_next_step": "review",
                    "confirmation_requested": "CONFIRM",
                }
            )
        DecisionRequest.from_mapping(
            {
                "intended_result": "one",
                "actual_result": "two",
                "evidence": "exit 1",
                "current_state": "paused",
                "options": ["retry", "stop"],
                "risks": ["may fail", "incomplete"],
                "recommended_option": "stop",
                "reversal_procedure": "discard worktree",
                "decision_required": "choose",
            }
        )

    def test_state_machine_rejects_skipped_review(self) -> None:
        machine = CoordinationStateMachine()
        machine.transition(LaneState.READY)
        machine.transition(LaneState.EXECUTING)
        with self.assertRaises(ContractError):
            machine.transition(LaneState.COMPLETE)
        machine.transition(LaneState.REVIEW)
        machine.transition(LaneState.COMPLETE)
        self.assertEqual(machine.state, LaneState.COMPLETE)


def _repo_root() -> Path | None:
    root = Path(__file__).resolve().parents[4]
    if (root / "fec" / "members" / "b5_narratives.py").is_file() and (
        root / ".claude" / "skills" / "codex-executor" / "SKILL.md"
    ).is_file():
        return root
    return None


class IntegrationSourceTests(unittest.TestCase):
    def test_narrative_route_has_no_direct_opus_fallback(self) -> None:
        repo = _repo_root()
        if repo is None:
            self.skipTest("repo layout not present for this copy of the suite")
        source = (repo / "fec" / "members" / "b5_narratives.py").read_text(encoding="utf-8")
        self.assertIn("'claude-fable-5'", source)
        self.assertIn("run_until_clear_sync", source)
        self.assertNotIn("FALLBACK_MODEL", source)
        self.assertNotIn("opus-fallback", source)

    def test_dispatch_protocol_uses_neutral_vocabulary(self) -> None:
        repo = _repo_root()
        if repo is None:
            self.skipTest("repo layout not present for this copy of the suite")
        skill = (
            repo / ".claude" / "skills" / "codex-executor" / "SKILL.md"
        ).read_text(encoding="utf-8")
        excluded = re.compile(
            r"\b(brain|body|biology|biological|reflex|reflexes|nervous|"
            r"spinal|efferent|afferent|motor|sensory)\b",
            re.IGNORECASE,
        )
        self.assertIsNone(excluded.search(skill))


if __name__ == "__main__":
    unittest.main()
