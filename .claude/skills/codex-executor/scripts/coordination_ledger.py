"""SQLite event ledger for executor coordination and retry runs."""

from __future__ import annotations

import codecs
from contextlib import closing
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any

from coordination_contract import DecisionVerdict


_EPISODE_SCHEMA_VERSION = 3
_DISPATCH_PROVENANCE_FIELDS = ("model", "effort", "tier")
_ATTRIBUTED_EVENT_TYPES = ("node_blocked", "node_failed", "node_rework")
_ATTRIBUTION_VALUES = ("spec-misread", "coordination", "verification", "infra")
_RECEIPT_EPOCH = "2026-08-11T00:00:00+00:00"
_RECEIPT_FINGERPRINTS_LEDGER_COMPUTED = (
    "receipt_fingerprints_ledger_computed"
)
_UTF8_FILE_FINGERPRINT_CHUNK_SIZE = 64 * 1024
_RECEIPT_BLOCK_RE = re.compile(
    r"^[ \t]*(?:(?:#{1,6}|[*_]{1,3})[ \t]*)*"
    r"RECEIPT(?=$|[^A-Za-z0-9])",
    re.MULTILINE,
)
_RECEIPT_ENUMERATED_ITEM_RE = re.compile(
    r"^[ \t]*(?:(?:[-+*]|[1-9][0-9]*[.)])[ \t]+)?"
    r"(?:[*_]{1,3}[ \t]*)*(?P<source>CON|INV)-"
    r"(?P<ordinal>[1-9][0-9]*):",
    re.MULTILINE,
)
# These values are the Fable-Sol retry lifecycle emitted through the
# handler used by fable_sol_retry.py, fable_sol_cli.py, and fec/b5_narratives.py.
# Generic coordination lifecycle events are intentionally excluded because a
# genuine Codex run can also emit them; over-flagging is the safe direction. A
# new producer emitting a new non-dispatch literal must be added here
# deliberately.
_NON_DISPATCH_RUN_EVENT_TYPES = frozenset(
    {
        "fable_attempt_started",
        "fable_attempt_finished",
        "sol_rewrite_started",
        "sol_rewrite_finished",
    }
)
_UNPARSEABLE_TIMESTAMP_SENTINEL = datetime.min.replace(tzinfo=timezone.utc)
_CONTENT_KEYS = {
    "claim",
    "command_or_operation",
    "evidence",
    "evidence_observed",
    "expected",
    "message",
    "note",
    "notes",
    "prompt",
    "output",
    "original_prompt",
    "current_prompt",
    "previous_output",
    "revised_prompt",
    "receipt",
    "reversal",
    "spec",
    "value",
}
_SECRET_SEGMENTS = {
    "apikey",
    "auth",
    "authorization",
    "bearer",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "passwd",
    "password",
    "secret",
    "secrets",
    "token",
    "tokens",
}
_SECRET_PAIRS = {
    ("access", "key"),
    ("api", "key"),
    ("private", "key"),
    ("session", "key"),
}


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    normalized = re.sub(
        r"(\.\d{6})\d+(?=(?:[+-]\d{2}:\d{2})?$)",
        r"\1",
        normalized,
    )
    try:
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (OverflowError, ValueError):
        return None


def _stored_timestamp_key(value: str) -> tuple[int, datetime, str]:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return (1, _UNPARSEABLE_TIMESTAMP_SENTINEL, value)
    return (0, parsed, value)


def _run_first_seen_key(
    item: dict[str, object],
) -> tuple[int, tuple[int, datetime, str], str]:
    first_seen = item["first_seen"]
    if isinstance(first_seen, str):
        timestamp_key = _stored_timestamp_key(first_seen)
        missing = 0
    else:
        timestamp_key = (
            1,
            _UNPARSEABLE_TIMESTAMP_SENTINEL,
            "",
        )
        missing = 1
    return (missing, timestamp_key, str(item["run_id"]))


def _duration_seconds(start: object, completed: object) -> float | None:
    started_at = _parse_timestamp(start)
    completed_at = _parse_timestamp(completed)
    if started_at is None or completed_at is None:
        return None
    duration = (completed_at - started_at).total_seconds()
    if duration < 0:
        return None
    return round(duration, 3)


def _numeric_token(value: object) -> int | float | None:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value
    return None


def _extract_tokens(payload: object) -> int | float | None:
    if not isinstance(payload, dict):
        return None
    tokens = _numeric_token(payload.get("tokens"))
    if tokens is not None:
        return tokens
    prompt_tokens = _numeric_token(payload.get("prompt_tokens"))
    completion_tokens = _numeric_token(payload.get("completion_tokens"))
    if prompt_tokens is not None and completion_tokens is not None:
        try:
            total = prompt_tokens + completion_tokens
        except OverflowError:
            return None
        return _numeric_token(total)
    return _numeric_token(payload.get("token_count"))


def _load_glassbox_events(
    glassbox_dir: str | Path,
) -> list[dict[str, object]]:
    events = []
    directory = Path(glassbox_dir)
    for path in sorted(directory.glob("*.json"), key=lambda item: item.name):
        try:
            event = json.loads(path.read_text(encoding="utf-8"))
        except (
            json.JSONDecodeError,
            RecursionError,
            TypeError,
            UnicodeDecodeError,
        ):
            continue
        if not isinstance(event, dict):
            continue
        schema_version = event.get("schema_version")
        if (
            not isinstance(schema_version, int)
            or isinstance(schema_version, bool)
            or schema_version != 1
            or "run_id" not in event
        ):
            continue
        events.append(event)
    return events


def _glassbox_event_key(
    event: dict[str, object],
) -> tuple[datetime, str]:
    timestamp = _parse_timestamp(event.get("timestamp_utc"))
    if timestamp is None:
        timestamp = _UNPARSEABLE_TIMESTAMP_SENTINEL
    return (timestamp, str(event.get("id", "")))


def _pair_glassbox_events(
    events: list[dict[str, object]],
) -> list[dict[str, object]]:
    prefixes = {"dispatch", "stage", "agent", "reconcile"}
    started_events = []
    completed_events = []
    for event in events:
        kind = event.get("kind")
        if not isinstance(kind, str):
            continue
        parts = kind.split(".")
        if len(parts) != 2 or parts[0] not in prefixes:
            continue
        timestamp = _parse_timestamp(event.get("timestamp_utc"))
        if timestamp is None:
            continue
        candidate = {
            "event": event,
            "prefix": parts[0],
            "timestamp": timestamp,
            "id": str(event.get("id", "")),
            "matched": False,
        }
        if parts[1] == "started":
            started_events.append(candidate)
        elif parts[1] == "completed":
            completed_events.append(candidate)

    def candidate_key(item: dict[str, object]) -> tuple[datetime, str]:
        return (item["timestamp"], str(item["id"]))  # type: ignore[return-value]

    started_events.sort(key=candidate_key)
    completed_events.sort(key=candidate_key)
    matched_candidates = []

    def match(
        started: dict[str, object], completed: dict[str, object]
    ) -> None:
        started["matched"] = True
        completed["matched"] = True
        started_event = started["event"]
        completed_event = completed["event"]
        if not isinstance(started_event, dict) or not isinstance(
            completed_event, dict
        ):
            return
        duration = _duration_seconds(
            started_event.get("timestamp_utc"),
            completed_event.get("timestamp_utc"),
        )
        if duration is None:
            return
        matched_candidates.append(
            {
                "prefix": started["prefix"],
                "started": started_event,
                "started_timestamp": started["timestamp"],
                "started_id": started["id"],
                "duration": duration,
            }
        )

    for started in started_events:
        started_event = started["event"]
        if not isinstance(started_event, dict):
            continue
        correlation_id = started_event.get("correlation_id")
        if not isinstance(correlation_id, str) or not correlation_id:
            continue
        for completed in completed_events:
            if completed["matched"] or completed["prefix"] != started["prefix"]:
                continue
            completed_event = completed["event"]
            if (
                isinstance(completed_event, dict)
                and completed_event.get("correlation_id") == correlation_id
            ):
                match(started, completed)
                break

    for started in started_events:
        if started["matched"]:
            continue
        started_event = started["event"]
        if not isinstance(started_event, dict):
            continue
        for completed in completed_events:
            if completed["matched"] or completed["prefix"] != started["prefix"]:
                continue
            completed_event = completed["event"]
            if (
                isinstance(completed_event, dict)
                and completed_event.get("stage") == started_event.get("stage")
            ):
                match(started, completed)
                break

    matched_candidates.sort(
        key=lambda item: (
            item["started_timestamp"],
            str(item["started_id"]),
        )
    )
    return matched_candidates


def _content_fingerprint(value: object) -> dict[str, object]:
    encoded = str(value).encode("utf-8")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "utf8_bytes": len(encoded),
    }


def _utf8_file_fingerprint(
    path: str | Path,
    *,
    field: str,
    text_chunks: list[str] | None = None,
) -> dict[str, object]:
    digest = hashlib.sha256()
    decoder = codecs.getincrementaldecoder("utf-8")()
    utf8_bytes = 0
    try:
        with Path(path).open("rb") as source:
            while chunk := source.read(_UTF8_FILE_FINGERPRINT_CHUNK_SIZE):
                digest.update(chunk)
                utf8_bytes += len(chunk)
                decoded = decoder.decode(chunk)
                if text_chunks is not None:
                    text_chunks.append(decoded)
            decoded = decoder.decode(b"", final=True)
            if text_chunks is not None:
                text_chunks.append(decoded)
    except UnicodeDecodeError as exc:
        raise ValueError(f"{field} file must contain UTF-8 text") from exc
    return {
        "sha256": digest.hexdigest(),
        "utf8_bytes": utf8_bytes,
    }


def _receipt_structure(
    receipt_text: str, *, invariants_pinned: int
) -> dict[str, object]:
    block_match = _RECEIPT_BLOCK_RE.search(receipt_text)
    block_text = receipt_text[block_match.start() :] if block_match else ""
    enumerated_items = list(_RECEIPT_ENUMERATED_ITEM_RE.finditer(block_text))
    covered_invariants = {
        int(item.group("ordinal"))
        for item in enumerated_items
        if item.group("source") == "INV"
    }
    invariants_missing = [
        ordinal
        for ordinal in range(1, invariants_pinned + 1)
        if ordinal not in covered_invariants
    ]
    has_block = block_match is not None
    return {
        "checked": True,
        "has_block": has_block,
        "enumerated_items": len(enumerated_items),
        "invariants_pinned": invariants_pinned,
        "invariants_missing": invariants_missing,
        "pass": (
            has_block
            and bool(enumerated_items)
            and not invariants_missing
        ),
    }


def _receipt_structure_error(structure: dict[str, object]) -> str:
    failures = []
    if structure["has_block"] is False:
        failures.append("has_block: missing RECEIPT block")
    if structure["enumerated_items"] == 0:
        failures.append("enumerated_items: none found in RECEIPT block")
    invariants_missing = structure["invariants_missing"]
    if invariants_missing:
        missing_tags = ", ".join(
            f"INV-{ordinal}" for ordinal in invariants_missing
        )
        failures.append(f"invariants_covered: missing {missing_tags}")
    return "receipt structure check failed: " + "; ".join(failures)


def _secret_named_value(key: str, value: object) -> bool:
    segments = tuple(
        segment
        for segment in re.split(r"[^A-Za-z0-9]+", key.casefold())
        if segment
    )
    secret_name = any(
        segment in _SECRET_SEGMENTS for segment in segments
    ) or any(
        pair in _SECRET_PAIRS
        for pair in zip(segments, segments[1:])
    )
    scalar_allowed = value is None or type(value) in {int, float, bool}
    return secret_name and not scalar_allowed


def _jsonable(value: object, *, key: str | None = None) -> object:
    normalized_key = (key or "").casefold()
    if normalized_key in _CONTENT_KEYS:
        return _content_fingerprint(value)
    if _secret_named_value(normalized_key, value):
        return {"redacted": True}
    if is_dataclass(value):
        return _jsonable(asdict(value))
    if isinstance(value, dict):
        return {
            str(item_key): _jsonable(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


class CoordinationLedger:
    """Append-only structured ledger with transactional recurrence counts."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._initialized = False

    def _connect(self, *, read_only: bool = False) -> sqlite3.Connection:
        if read_only:
            if not self.path.is_file():
                raise ValueError(f"ledger database not found: {self.path}")
            database_uri = Path(self.path).resolve().as_uri() + "?mode=ro"
            connection = sqlite3.connect(
                database_uri,
                timeout=30,
                uri=True,
            )
        else:
            connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()
        self._initialized = True

    def _initialize(self) -> None:
        with closing(self._connect()) as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                schema_table_exists = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'coordination_schema'
                    """
                ).fetchone()
                stored_version: int | None = None
                if schema_table_exists is not None:
                    version_row = connection.execute(
                        """
                        SELECT version FROM coordination_schema
                        WHERE name = 'episode_events'
                        """
                    ).fetchone()
                    if version_row is not None:
                        stored_version = int(version_row["version"])
                episode_table_exists = connection.execute(
                    """
                    SELECT 1 FROM sqlite_master
                    WHERE type = 'table'
                      AND name = 'coordination_episode_events'
                    """
                ).fetchone()
                effective_version = stored_version
                if effective_version is None and episode_table_exists is not None:
                    effective_version = 2
                if (
                    effective_version is not None
                    and effective_version < _EPISODE_SCHEMA_VERSION
                ):
                    raise ValueError(
                        f"{self.path}: ledger schema v{effective_version} "
                        "is older than this runtime's "
                        f"v{_EPISODE_SCHEMA_VERSION}"
                    )
                if (
                    effective_version is not None
                    and effective_version > _EPISODE_SCHEMA_VERSION
                ):
                    raise ValueError(
                        f"{self.path}: ledger schema v{effective_version} "
                        "is newer than this runtime's "
                        f"v{_EPISODE_SCHEMA_VERSION}"
                    )
                initialize_schema_version = (
                    stored_version is None
                    and episode_table_exists is None
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coordination_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        run_id TEXT NOT NULL,
                        task_slug TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        trigger_key TEXT NOT NULL,
                        verdict TEXT,
                        occurrence INTEGER NOT NULL CHECK (occurrence >= 1),
                        payload_json TEXT NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_coordination_trigger
                        ON coordination_events(trigger_key, id)
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_coordination_run
                        ON coordination_events(run_id, id)
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coordination_schema (
                        name TEXT PRIMARY KEY,
                        version INTEGER NOT NULL
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS coordination_episode_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL,
                        sequence INTEGER NOT NULL CHECK (sequence >= 1),
                        event_kind TEXT NOT NULL,
                        subject TEXT NOT NULL,
                        trigger_key TEXT NOT NULL,
                        payload_json TEXT NOT NULL,
                        payload_sha256 TEXT NOT NULL,
                        UNIQUE(run_id, sequence),
                        UNIQUE(
                            run_id, event_kind, subject, trigger_key,
                            payload_sha256
                        )
                    )
                    """
                )
                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_episode_run
                        ON coordination_episode_events(run_id, sequence)
                    """
                )
                if initialize_schema_version:
                    connection.execute(
                        """
                        INSERT INTO coordination_schema(name, version)
                        VALUES ('episode_events', ?)
                        """,
                        (_EPISODE_SCHEMA_VERSION,),
                    )

    def record(
        self,
        *,
        run_id: str,
        task_slug: str,
        event_type: str,
        trigger_key: str,
        payload: object,
        verdict: str | None = None,
        spec_file: str | Path | None = None,
        receipt_file: str | Path | None = None,
    ) -> int:
        file_arguments = {
            "spec": spec_file,
            "receipt": receipt_file,
        }
        if isinstance(payload, dict):
            for field, path in file_arguments.items():
                if path is not None and field in payload:
                    raise ValueError(
                        f"payload field conflict: {field} supplied by both "
                        f"--{field}-file and payload"
                    )
        receipt_text_chunks: list[str] | None = (
            [] if receipt_file is not None else None
        )
        file_fingerprints = {}
        for field, path in file_arguments.items():
            if path is not None:
                file_fingerprints[field] = _utf8_file_fingerprint(
                    path,
                    field=field,
                    text_chunks=(
                        receipt_text_chunks if field == "receipt" else None
                    ),
                )
        receipt_text = (
            "".join(receipt_text_chunks)
            if receipt_text_chunks is not None
            else None
        )
        self._ensure_initialized()
        required = {
            "run_id": run_id,
            "task_slug": task_slug,
            "event_type": event_type,
            "trigger_key": trigger_key,
        }
        for label, value in required.items():
            if not value.strip():
                raise ValueError(f"{label} must not be empty")
        sanitized = _jsonable(payload)
        if file_fingerprints:
            if not isinstance(sanitized, dict):
                raise ValueError(
                    "payload must be an object when fingerprint files are supplied"
                )
            sanitized.update(file_fingerprints)
        if event_type == "dispatch":
            missing = [
                field
                for field in _DISPATCH_PROVENANCE_FIELDS
                if (
                    not isinstance(sanitized, dict)
                    or not isinstance(sanitized.get(field), str)
                    or not sanitized[field].strip()
                )
            ]
            if missing:
                raise ValueError(
                    "dispatch payload fields must be non-empty strings: "
                    + ", ".join(missing)
                )
            if sanitized["effort"] != "xhigh":
                raise ValueError('dispatch payload effort must equal exactly "xhigh"')
            if sanitized["tier"] != "priority":
                raise ValueError('dispatch payload tier must equal exactly "priority"')
        if event_type == "signoff":
            try:
                DecisionVerdict(verdict)
            except (TypeError, ValueError) as exc:
                choices = ", ".join(item.value for item in DecisionVerdict)
                raise ValueError(
                    f"signoff verdict must be one of: {choices}"
                ) from exc
        if event_type == "invariants":
            invariants = (
                sanitized.get("invariants")
                if isinstance(sanitized, dict)
                else None
            )
            if (
                not isinstance(invariants, list)
                or not invariants
                or any(
                    not isinstance(item, str) or not item
                    for item in invariants
                )
            ):
                raise ValueError(
                    "invariants record requires a non-empty list of "
                    "non-empty strings"
                )
        if event_type == "receipt":
            if not isinstance(sanitized, dict):
                raise ValueError(
                    "receipt record requires non-empty string "
                    "dispatch_trigger_key"
                )
            dispatch_trigger_key = sanitized.get("dispatch_trigger_key")
            if (
                not isinstance(dispatch_trigger_key, str)
                or not dispatch_trigger_key.strip()
            ):
                raise ValueError(
                    "receipt record requires non-empty string "
                    "dispatch_trigger_key"
                )
            sanitized[_RECEIPT_FINGERPRINTS_LEDGER_COMPUTED] = (
                set(file_fingerprints) == {"spec", "receipt"}
            )
            content_fields = ("spec", "receipt")
            valid_fingerprints = (
                isinstance(sanitized, dict)
                and all(field in sanitized for field in content_fields)
                and all(
                    isinstance(sanitized[field], dict)
                    and set(sanitized[field]) == {"sha256", "utf8_bytes"}
                    and isinstance(sanitized[field]["sha256"], str)
                    and re.fullmatch(
                        r"[0-9a-f]{64}", sanitized[field]["sha256"]
                    )
                    is not None
                    and type(sanitized[field]["utf8_bytes"]) is int
                    and sanitized[field]["utf8_bytes"] > 0
                    for field in content_fields
                )
            )
            if (
                not valid_fingerprints
                or not isinstance(sanitized, dict)
                or "verified" not in sanitized
                or type(sanitized["verified"]) is not bool
            ):
                raise ValueError(
                    "receipt record requires spec, receipt, verified"
                )
        if event_type == "fact":
            valid_raw_provenance = (
                isinstance(payload, dict)
                and isinstance(payload.get("provenance"), str)
            )
            claim = (
                sanitized.get("claim")
                if isinstance(sanitized, dict)
                else None
            )
            provenance = (
                sanitized.get("provenance")
                if isinstance(sanitized, dict)
                else None
            )
            valid_claim = (
                isinstance(claim, dict)
                and set(claim) == {"sha256", "utf8_bytes"}
                and isinstance(claim["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", claim["sha256"])
                is not None
                and type(claim["utf8_bytes"]) is int
                and claim["utf8_bytes"] > 0
            )
            valid_provenance = (
                isinstance(provenance, str) and bool(provenance.strip())
            )
            if (
                not valid_raw_provenance
                or not valid_claim
                or not valid_provenance
            ):
                raise ValueError(
                    "fact record requires claim and provenance: "
                    f"{trigger_key}"
                )
        if event_type in _ATTRIBUTED_EVENT_TYPES:
            missing = [
                field
                for field in ("attribution",)
                if not isinstance(sanitized, dict) or field not in sanitized
            ]
            if missing:
                raise ValueError(
                    "attribution tag required: " + ", ".join(missing)
                )
            if (
                not isinstance(sanitized["attribution"], str)
                or sanitized["attribution"] not in _ATTRIBUTION_VALUES
            ):
                choices = ", ".join(_ATTRIBUTION_VALUES)
                raise ValueError(
                    f"attribution tag required; must be one of: {choices}"
                )
        encoded = json.dumps(sanitized, ensure_ascii=False, sort_keys=True)
        created_at = datetime.now(timezone.utc).isoformat()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                if event_type == "receipt" and receipt_text is not None:
                    invariants_row = connection.execute(
                        """
                        SELECT payload_json
                        FROM coordination_events
                        WHERE run_id = ? AND event_type = 'invariants'
                        ORDER BY id DESC
                        LIMIT 1
                        """,
                        (run_id,),
                    ).fetchone()
                    invariants_pinned = 0
                    if invariants_row is not None:
                        try:
                            invariants_payload = json.loads(
                                invariants_row["payload_json"]
                            )
                        except (
                            json.JSONDecodeError,
                            RecursionError,
                            TypeError,
                            UnicodeDecodeError,
                        ):
                            invariants_payload = None
                        invariants = (
                            invariants_payload.get("invariants")
                            if isinstance(invariants_payload, dict)
                            else None
                        )
                        if isinstance(invariants, list):
                            invariants_pinned = len(invariants)
                    structure = _receipt_structure(
                        receipt_text,
                        invariants_pinned=invariants_pinned,
                    )
                    sanitized["structure"] = structure
                    if sanitized["verified"] is True and not structure["pass"]:
                        raise ValueError(_receipt_structure_error(structure))
                    encoded = json.dumps(
                        sanitized,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                occurrence = int(
                    connection.execute(
                        """
                        SELECT COUNT(*) + 1
                        FROM coordination_events
                        WHERE trigger_key = ?
                        """,
                        (trigger_key,),
                    ).fetchone()[0]
                )
                connection.execute(
                    """
                    INSERT INTO coordination_events (
                        created_at, run_id, task_slug, event_type, trigger_key,
                        verdict, occurrence, payload_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        run_id,
                        task_slug,
                        event_type,
                        trigger_key,
                        verdict,
                        occurrence,
                        encoded,
                    ),
                )
        return occurrence

    def list_events(self, *, run_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM coordination_events"
        parameters: tuple[object, ...] = ()
        if run_id is not None:
            query += " WHERE run_id = ?"
            parameters = (run_id,)
        query += " ORDER BY id"
        with closing(self._connect(read_only=True)) as connection:
            rows = connection.execute(query, parameters).fetchall()
        events = []
        for row in rows:
            event = dict(row)
            event["payload"] = json.loads(event.pop("payload_json"))
            events.append(event)
        return events

    def repeated_triggers(self, *, minimum: int = 2) -> list[dict[str, Any]]:
        if minimum < 2:
            raise ValueError("minimum must be at least 2")
        with closing(self._connect(read_only=True)) as connection:
            rows = connection.execute(
                """
                SELECT trigger_key, COUNT(*) AS occurrences, MAX(created_at) AS last_seen
                FROM coordination_events
                WHERE trigger_key NOT LIKE 'info:%'
                GROUP BY trigger_key
                HAVING COUNT(*) >= ?
                ORDER BY occurrences DESC, trigger_key
                """,
                (minimum,),
            ).fetchall()
        return [dict(row) for row in rows]

    def audit(
        self, glassbox_dir: str | Path | None = None
    ) -> dict[str, object]:
        with closing(self._connect(read_only=True)) as connection:
            event_rows = connection.execute(
                """
                SELECT id, created_at, run_id, task_slug, event_type,
                       trigger_key, verdict, payload_json
                FROM coordination_events
                ORDER BY id
                """
            ).fetchall()
            episode_rows = connection.execute(
                """
                SELECT run_id
                FROM coordination_episode_events
                ORDER BY run_id, sequence
                """
            ).fetchall()

        glassbox_events = (
            _load_glassbox_events(glassbox_dir)
            if glassbox_dir is not None
            else None
        )
        event_count_by_run: dict[str, int] = {}
        first_seen_by_run: dict[str, str] = {}
        task_slug_by_run: dict[str, str] = {}
        event_types_by_run: dict[str, set[str]] = {}
        events_by_run: dict[str, list[sqlite3.Row]] = {}
        tokens_by_event_id: dict[int, int | float | None] = {}
        dispatch_runs: set[str] = set()
        dispatch_missing_provenance = []
        signoffs_missing_verdict = []
        attributed_events_missing_tag = []
        dispatches_missing_receipt = []
        facts_missing_provenance = []
        runs_missing_invariants = []
        receipt_fingerprints_caller_supplied = []
        receipts_verified_without_structure_check = []
        valid_receipt_ids: set[int] = set()
        receipt_dispatch_trigger_keys: dict[int, str] = {}
        valid_verdicts = {item.value for item in DecisionVerdict}

        for row in event_rows:
            run_id = str(row["run_id"])
            event_count_by_run[run_id] = event_count_by_run.get(run_id, 0) + 1
            events_by_run.setdefault(run_id, []).append(row)
            created_at = str(row["created_at"])
            if (
                run_id not in first_seen_by_run
                or _stored_timestamp_key(created_at)
                < _stored_timestamp_key(first_seen_by_run[run_id])
            ):
                first_seen_by_run[run_id] = created_at
            task_slug_by_run[run_id] = str(row["task_slug"])
            event_types_by_run.setdefault(run_id, set()).add(
                str(row["event_type"])
            )

            try:
                payload = json.loads(row["payload_json"])
            except (
                json.JSONDecodeError,
                RecursionError,
                TypeError,
                UnicodeDecodeError,
            ):
                payload = None
                payload_unparseable = True
            else:
                payload_unparseable = False
            tokens_by_event_id[int(row["id"])] = (
                None if payload_unparseable else _extract_tokens(payload)
            )

            if row["event_type"] == "dispatch":
                dispatch_runs.add(run_id)
                if payload_unparseable:
                    missing = ["<unparseable-payload>"]
                else:
                    missing = [
                        field
                        for field in _DISPATCH_PROVENANCE_FIELDS
                        if (
                            not isinstance(payload, dict)
                            or not isinstance(payload.get(field), str)
                            or not payload[field].strip()
                            or (field == "effort" and payload[field] != "xhigh")
                            or (field == "tier" and payload[field] != "priority")
                        )
                    ]
                if missing:
                    dispatch_missing_provenance.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "created_at": created_at,
                            "missing": missing,
                        }
                    )

            if row["event_type"] == "signoff":
                verdict = row["verdict"]
                valid_verdict = (
                    isinstance(verdict, str)
                    and bool(verdict.strip())
                    and verdict in valid_verdicts
                )
                if not valid_verdict:
                    verdict_display = (
                        verdict
                        if verdict is None or isinstance(verdict, str)
                        else str(verdict)
                    )
                    signoffs_missing_verdict.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "created_at": created_at,
                            "verdict": verdict_display,
                        }
                    )

            if row["event_type"] == "receipt":
                receipt_dispatch_trigger_key = (
                    payload.get("dispatch_trigger_key")
                    if isinstance(payload, dict)
                    else None
                )
                if (
                    isinstance(receipt_dispatch_trigger_key, str)
                    and receipt_dispatch_trigger_key.strip()
                ):
                    receipt_dispatch_trigger_keys[int(row["id"])] = (
                        receipt_dispatch_trigger_key
                    )
                fingerprints_ledger_computed = (
                    not payload_unparseable
                    and isinstance(payload, dict)
                    and payload.get(
                        _RECEIPT_FINGERPRINTS_LEDGER_COMPUTED
                    )
                    is True
                )
                if not fingerprints_ledger_computed:
                    receipt_fingerprints_caller_supplied.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "trigger_key": str(row["trigger_key"]),
                        }
                    )
                structure = (
                    payload.get("structure")
                    if isinstance(payload, dict)
                    else None
                )
                structure_checked = (
                    isinstance(structure, dict)
                    and structure.get("checked") is True
                )
                if (
                    isinstance(payload, dict)
                    and payload.get("verified") is True
                    and not structure_checked
                ):
                    receipts_verified_without_structure_check.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "trigger_key": str(row["trigger_key"]),
                        }
                    )
                content_fields = ("spec", "receipt")
                valid_fingerprints = (
                    not payload_unparseable
                    and isinstance(payload, dict)
                    and all(field in payload for field in content_fields)
                    and all(
                        isinstance(payload[field], dict)
                        and set(payload[field]) == {"sha256", "utf8_bytes"}
                        and isinstance(payload[field]["sha256"], str)
                        and re.fullmatch(
                            r"[0-9a-f]{64}", payload[field]["sha256"]
                        )
                        is not None
                        and type(payload[field]["utf8_bytes"]) is int
                        and payload[field]["utf8_bytes"] > 0
                        for field in content_fields
                    )
                )
                if (
                    valid_fingerprints
                    and "verified" in payload
                    and type(payload["verified"]) is bool
                ):
                    valid_receipt_ids.add(int(row["id"]))

            if row["event_type"] in _ATTRIBUTED_EVENT_TYPES:
                if payload_unparseable:
                    attribution = "<unparseable-payload>"
                    valid_attribution = False
                elif not isinstance(payload, dict) or "attribution" not in payload:
                    attribution = "<missing>"
                    valid_attribution = False
                else:
                    attribution = payload["attribution"]
                    valid_attribution = (
                        isinstance(attribution, str)
                        and attribution in _ATTRIBUTION_VALUES
                    )
                if not valid_attribution:
                    attributed_events_missing_tag.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "event_type": str(row["event_type"]),
                            "attribution": attribution,
                        }
                    )

            if row["event_type"] == "fact":
                claim = (
                    payload.get("claim")
                    if isinstance(payload, dict)
                    else None
                )
                provenance = (
                    payload.get("provenance")
                    if isinstance(payload, dict)
                    else None
                )
                valid_claim = (
                    not payload_unparseable
                    and isinstance(claim, dict)
                    and set(claim) == {"sha256", "utf8_bytes"}
                    and isinstance(claim["sha256"], str)
                    and re.fullmatch(r"[0-9a-f]{64}", claim["sha256"])
                    is not None
                    and type(claim["utf8_bytes"]) is int
                    and claim["utf8_bytes"] > 0
                )
                valid_provenance = (
                    not payload_unparseable
                    and isinstance(provenance, str)
                    and bool(provenance.strip())
                )
                if not valid_claim or not valid_provenance:
                    facts_missing_provenance.append(
                        {
                            "id": int(row["id"]),
                            "run_id": run_id,
                            "task_slug": str(row["task_slug"]),
                            "trigger_key": str(row["trigger_key"]),
                        }
                    )

        receipt_epoch = _parse_timestamp(_RECEIPT_EPOCH)
        assert receipt_epoch is not None
        for run_id, run_events in events_by_run.items():
            dispatches = [
                row for row in run_events if row["event_type"] == "dispatch"
            ]
            dispatch_count = sum(
                1
                for row in dispatches
                if (
                    (dispatch_time := _parse_timestamp(str(row["created_at"])))
                    is not None
                    and dispatch_time >= receipt_epoch
                )
            )
            if (
                dispatch_count >= 2
                and "invariants" not in event_types_by_run[run_id]
            ):
                runs_missing_invariants.append(
                    {
                        "run_id": run_id,
                        "task_slug": task_slug_by_run[run_id],
                        "dispatch_count": dispatch_count,
                    }
                )
            receipt_times = [
                _parse_timestamp(str(row["created_at"]))
                for row in run_events
                if (
                    row["event_type"] == "receipt"
                    and int(row["id"]) in valid_receipt_ids
                )
            ]
            run_uses_trigger_keys = any(
                row["event_type"] == "receipt"
                and int(row["id"]) in receipt_dispatch_trigger_keys
                for row in run_events
            )
            valid_receipt_trigger_keys = {
                receipt_dispatch_trigger_keys[int(row["id"])]
                for row in run_events
                if (
                    row["event_type"] == "receipt"
                    and int(row["id"]) in valid_receipt_ids
                    and int(row["id"]) in receipt_dispatch_trigger_keys
                )
            }
            for index, dispatch in enumerate(dispatches):
                dispatch_time = _parse_timestamp(str(dispatch["created_at"]))
                if dispatch_time is None:
                    dispatches_missing_receipt.append(
                        {
                            "id": int(dispatch["id"]),
                            "run_id": run_id,
                            "task_slug": str(dispatch["task_slug"]),
                            "trigger_key": str(dispatch["trigger_key"]),
                        }
                    )
                    continue
                if dispatch_time < receipt_epoch:
                    continue
                next_dispatch_time = (
                    _parse_timestamp(str(dispatches[index + 1]["created_at"]))
                    if index + 1 < len(dispatches)
                    else None
                )
                if run_uses_trigger_keys:
                    has_receipt = (
                        str(dispatch["trigger_key"])
                        in valid_receipt_trigger_keys
                    )
                else:
                    has_receipt = any(
                        receipt_time is not None
                        and receipt_time > dispatch_time
                        and (
                            index + 1 == len(dispatches)
                            or (
                                next_dispatch_time is not None
                                and receipt_time < next_dispatch_time
                            )
                        )
                        for receipt_time in receipt_times
                    )
                if not has_receipt:
                    dispatches_missing_receipt.append(
                        {
                            "id": int(dispatch["id"]),
                            "run_id": run_id,
                            "task_slug": str(dispatch["task_slug"]),
                            "trigger_key": str(dispatch["trigger_key"]),
                        }
                    )

        episode_runs = {str(row["run_id"]) for row in episode_rows}
        universe = set(event_count_by_run) | episode_runs
        exempt_runs = {
            run_id
            for run_id, event_types in event_types_by_run.items()
            if event_types
            and event_types.issubset(_NON_DISPATCH_RUN_EVENT_TYPES)
        }
        coordinator_bookkeeping_runs = {
            run_id
            for run_id, event_types in event_types_by_run.items()
            if event_types
            and event_types.issubset({"invariants", "receipt"})
        }
        exempt_runs |= coordinator_bookkeeping_runs
        runs_missing_dispatch = [
            {
                "run_id": run_id,
                "task_slug": task_slug_by_run.get(run_id),
                "first_seen": first_seen_by_run.get(run_id),
                "event_count": event_count_by_run.get(run_id, 0),
            }
            for run_id in universe
            if run_id not in dispatch_runs and run_id not in exempt_runs
        ]
        runs_missing_dispatch.sort(key=_run_first_seen_key)
        runs_exempt_non_dispatch = [
            {
                "run_id": run_id,
                "task_slug": task_slug_by_run.get(run_id),
                "event_types": sorted(event_types_by_run[run_id]),
            }
            for run_id in sorted(exempt_runs)
        ]
        dispatch_missing_provenance.sort(key=lambda item: item["id"])
        signoffs_missing_verdict.sort(key=lambda item: item["id"])
        attributed_events_missing_tag.sort(key=lambda item: item["id"])
        dispatches_missing_receipt.sort(key=lambda item: item["id"])
        facts_missing_provenance.sort(key=lambda item: item["id"])
        receipt_fingerprints_caller_supplied.sort(
            key=lambda item: item["id"]
        )
        receipts_verified_without_structure_check.sort(
            key=lambda item: item["id"]
        )
        runs_missing_invariants.sort(key=lambda item: item["run_id"])
        runs_with_no_episode_events = [
            {
                "run_id": run_id,
                "task_slug": task_slug_by_run.get(run_id),
            }
            for run_id in sorted(universe - episode_runs)
        ]

        glassbox_events_by_run: dict[str, list[dict[str, object]]] = {}
        if glassbox_events is not None:
            for event in glassbox_events:
                event_run_id = event.get("run_id")
                if isinstance(event_run_id, str):
                    glassbox_events_by_run.setdefault(event_run_id, []).append(
                        event
                    )

        run_metrics = []
        for run_id, run_events in events_by_run.items():
            first_event = run_events[0]
            last_event = run_events[-1]
            run_glassbox_events = glassbox_events_by_run.get(run_id, [])
            glassbox_pairs = (
                _pair_glassbox_events(run_glassbox_events)
                if glassbox_events is not None
                else []
            )
            dispatch_pairs = [
                pair
                for pair in glassbox_pairs
                if pair["prefix"] == "dispatch"
            ]

            nodes = []
            dispatch_index = 0
            untimed_nodes = 0
            for event_index, row in enumerate(run_events):
                if row["event_type"] != "dispatch":
                    continue
                ledger_next_event_seconds = None
                if event_index + 1 < len(run_events):
                    ledger_next_event_seconds = _duration_seconds(
                        row["created_at"],
                        run_events[event_index + 1]["created_at"],
                    )
                glassbox_pair_seconds = None
                if dispatch_index < len(dispatch_pairs):
                    pair_duration = dispatch_pairs[dispatch_index]["duration"]
                    if isinstance(pair_duration, float):
                        glassbox_pair_seconds = pair_duration
                if (
                    ledger_next_event_seconds is None
                    and glassbox_pair_seconds is None
                ):
                    untimed_nodes += 1
                nodes.append(
                    {
                        "trigger_key": str(row["trigger_key"]),
                        "created_at": str(row["created_at"]),
                        "ledger_next_event_seconds": (
                            ledger_next_event_seconds
                        ),
                        "glassbox_pair_seconds": glassbox_pair_seconds,
                        "tokens": tokens_by_event_id[int(row["id"])],
                    }
                )
                dispatch_index += 1

            token_values = [
                tokens_by_event_id[int(row["id"])]
                for row in run_events
                if tokens_by_event_id[int(row["id"])] is not None
            ]
            run_metric = {
                "run_id": run_id,
                "task_slug": task_slug_by_run[run_id],
                "event_count": len(run_events),
                "first_event_utc": str(first_event["created_at"]),
                "last_event_utc": str(last_event["created_at"]),
                "ledger_wall_seconds": _duration_seconds(
                    first_event["created_at"], last_event["created_at"]
                ),
                "closed": str(last_event["event_type"])
                in {"signoff", "lane_complete"},
                "nodes": nodes,
                "tokens_total": (
                    sum(token_values) if token_values else None
                ),
                "untimed_nodes": untimed_nodes,
            }

            if glassbox_events is not None:
                run_started = sorted(
                    (
                        event
                        for event in run_glassbox_events
                        if event.get("kind") == "run.started"
                        and _parse_timestamp(event.get("timestamp_utc"))
                        is not None
                    ),
                    key=_glassbox_event_key,
                )
                run_completed = sorted(
                    (
                        event
                        for event in run_glassbox_events
                        if event.get("kind") == "run.completed"
                        and _parse_timestamp(event.get("timestamp_utc"))
                        is not None
                    ),
                    key=_glassbox_event_key,
                )
                glassbox_run_seconds = None
                if run_started and run_completed:
                    glassbox_run_seconds = _duration_seconds(
                        run_started[0].get("timestamp_utc"),
                        run_completed[-1].get("timestamp_utc"),
                    )

                serial_durations = []
                parallel_durations = []
                for pair in glassbox_pairs:
                    started_event = pair["started"]
                    if not isinstance(started_event, dict):
                        continue
                    lane = started_event.get("lane")
                    prefix = pair["prefix"]
                    duration = pair["duration"]
                    if not isinstance(duration, float):
                        continue
                    if lane == "codex" or prefix == "dispatch":
                        serial_durations.append(duration)
                    elif (
                        lane in {"claude", "gemini", "grok"}
                        and prefix in {"agent", "stage"}
                        and lane != "codex"
                    ):
                        parallel_durations.append(duration)

                run_metric.update(
                    {
                        "glassbox_run_seconds": glassbox_run_seconds,
                        "serial_spine_seconds": round(
                            sum(serial_durations, 0.0), 3
                        ),
                        "parallel_side_seconds": round(
                            sum(parallel_durations, 0.0), 3
                        ),
                        "glassbox_events_matched": len(
                            run_glassbox_events
                        ),
                    }
                )
            run_metrics.append(run_metric)

        run_metrics.sort(
            key=lambda item: _run_first_seen_key(
                {
                    "run_id": item["run_id"],
                    "first_seen": first_seen_by_run[str(item["run_id"])],
                }
            )
        )
        totals = {
            "events": len(event_rows),
            "runs": len(universe),
            "episode_events": len(episode_rows),
            "runs_missing_dispatch": len(runs_missing_dispatch),
            "runs_exempt_non_dispatch": len(runs_exempt_non_dispatch),
            "dispatch_missing_provenance": len(
                dispatch_missing_provenance
            ),
            "signoffs_missing_verdict": len(signoffs_missing_verdict),
            "attributed_events_missing_tag": len(
                attributed_events_missing_tag
            ),
            "dispatches_missing_receipt": len(dispatches_missing_receipt),
            "facts_missing_provenance": len(facts_missing_provenance),
            "receipt_fingerprints_caller_supplied": len(
                receipt_fingerprints_caller_supplied
            ),
            "receipts_verified_without_structure_check": len(
                receipts_verified_without_structure_check
            ),
            "runs_missing_invariants": len(runs_missing_invariants),
            "runs_with_no_episode_events": len(
                runs_with_no_episode_events
            ),
        }
        totals["findings"] = (
            totals["runs_missing_dispatch"]
            + totals["dispatch_missing_provenance"]
            + totals["signoffs_missing_verdict"]
            + totals["attributed_events_missing_tag"]
            + totals["dispatches_missing_receipt"]
            + totals["facts_missing_provenance"]
        )
        return {
            "runs_missing_dispatch": runs_missing_dispatch,
            "runs_exempt_non_dispatch": runs_exempt_non_dispatch,
            "dispatch_missing_provenance": dispatch_missing_provenance,
            "signoffs_missing_verdict": signoffs_missing_verdict,
            "attributed_events_missing_tag": attributed_events_missing_tag,
            "dispatches_missing_receipt": dispatches_missing_receipt,
            "facts_missing_provenance": facts_missing_provenance,
            "receipt_fingerprints_caller_supplied": (
                receipt_fingerprints_caller_supplied
            ),
            "receipts_verified_without_structure_check": (
                receipts_verified_without_structure_check
            ),
            "runs_missing_invariants": runs_missing_invariants,
            "episode_events_total": len(episode_rows),
            "runs_with_no_episode_events": runs_with_no_episode_events,
            "totals": totals,
            "run_metrics": run_metrics,
        }

    def record_episode_event(
        self,
        *,
        run_id: str,
        event_kind: str,
        subject: str,
        trigger_key: str,
        payload: object,
    ) -> int:
        self._ensure_initialized()
        for label, value in {
            "run_id": run_id,
            "event_kind": event_kind,
            "subject": subject,
            "trigger_key": trigger_key,
        }.items():
            if not value.strip():
                raise ValueError(f"{label} must not be empty")
        normalized = _jsonable(payload)
        encoded = json.dumps(
            normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        with closing(self._connect()) as connection:
            with connection:
                connection.execute("BEGIN IMMEDIATE")
                existing = connection.execute(
                    """
                    SELECT sequence FROM coordination_episode_events
                    WHERE run_id = ? AND event_kind = ? AND subject = ?
                      AND trigger_key = ? AND payload_sha256 = ?
                    """,
                    (run_id, event_kind, subject, trigger_key, digest),
                ).fetchone()
                if existing is not None:
                    return int(existing["sequence"])
                sequence = int(
                    connection.execute(
                        """
                        SELECT COALESCE(MAX(sequence), 0) + 1
                        FROM coordination_episode_events WHERE run_id = ?
                        """,
                        (run_id,),
                    ).fetchone()[0]
                )
                connection.execute(
                    """
                    INSERT INTO coordination_episode_events(
                        run_id, sequence, event_kind, subject, trigger_key,
                        payload_json, payload_sha256
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        sequence,
                        event_kind,
                        subject,
                        trigger_key,
                        encoded,
                        digest,
                    ),
                )
        return sequence

    def episode(self, *, run_id: str) -> list[dict[str, Any]]:
        with closing(self._connect(read_only=True)) as connection:
            rows = connection.execute(
                """
                SELECT run_id, sequence, event_kind, subject, trigger_key,
                       payload_sha256, payload_json
                FROM coordination_episode_events
                WHERE run_id = ? ORDER BY sequence
                """,
                (run_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

    def amendment_candidates(
        self,
        *,
        minimum: int = 2,
    ) -> list[dict[str, Any]]:
        if minimum < 2:
            raise ValueError("minimum must be at least 2")
        with closing(self._connect(read_only=True)) as connection:
            rows = connection.execute(
                """
                SELECT trigger_key, COUNT(*) AS occurrence_count,
                       MIN(sequence) AS first_sequence,
                       MAX(sequence) AS last_sequence
                FROM coordination_episode_events
                WHERE event_kind = 'TRIGGER_OCCURRENCE'
                  AND trigger_key NOT LIKE 'info:%'
                GROUP BY trigger_key
                HAVING COUNT(*) >= ?
                ORDER BY first_sequence, trigger_key
                """,
                (minimum,),
            ).fetchall()
        return [
            {
                "candidate_id": hashlib.sha256(
                    str(row["trigger_key"]).encode("utf-8")
                ).hexdigest(),
                "status": "CANDIDATE",
                **dict(row),
            }
            for row in rows
        ]


class LedgerEventHandler:
    """Controller event callback that records stable duplicate keys."""

    def __init__(
        self,
        ledger: CoordinationLedger,
        *,
        run_id: str,
        task_slug: str,
    ) -> None:
        self.ledger = ledger
        self.run_id = run_id
        self.task_slug = task_slug

    def __call__(self, event: str, payload: object) -> None:
        trigger_key = "info:" + event
        if event == "fable_attempt_finished":
            reasons = tuple(getattr(payload, "retry_reasons", ()) or ())
            trigger_key = (
                "info:fable_clear"
                if not reasons
                else "fable_retry:" + "|".join(sorted(reasons))
            )
        self.ledger.record(
            run_id=self.run_id,
            task_slug=self.task_slug,
            event_type=event,
            trigger_key=trigger_key,
            payload=payload,
        )
