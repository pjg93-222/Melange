#!/usr/bin/env python3
"""Build a deterministic, reversible legislation culling proposal.

This program is intentionally independent of Codex and any model runtime.  It
reads immutable discovery/evidence inputs, classifies every membership at the
natural key ``(canonical_key, query_id)``, and writes only to a dedicated audit
root.  It never edits discovery records, the main corpus, scoring inputs, or
promotion artifacts.

Candidate-wide junk is a derived, reversible state.  A candidate is eligible
only when every membership is a finalizable explicit exclusion and no keep,
flagged, legacy, or restored edge exists.  Missing or incomplete evidence is
always flagged and can never produce junk.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable, Mapping

try:
    from legislation_culling_integration_contract import (
        CullingContractError,
        membership_is_finalizable,
        validate_candidate_evidence,
    )
except ImportError:  # pragma: no cover - package import path
    from fec.legislation_culling_integration_contract import (
        CullingContractError,
        membership_is_finalizable,
        validate_candidate_evidence,
    )


TOOL_NAME = "run_reversible_legislation_culling.py"
TOOL_VERSION = "1.0.0"
MEMBERSHIP_SCHEMA = "acu-legislation-reversible-membership-disposition-v1"
CANDIDATE_SCHEMA = "acu-legislation-reversible-candidate-partition-v1"
JUNK_SCHEMA = "acu-legislation-derived-junk-exclusion-v1"
RESTORATION_SCHEMA = "acu-legislation-derived-junk-restoration-v1"
GENERATION_SCHEMA = "acu-legislation-reversible-culling-generation-v1"
RECEIPT_SCHEMA = "acu-legislation-reversible-culling-receipt-v1"
ZERO_SHA256 = "0" * 64
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_KEY_RE = re.compile(
    r"^(?:116|117|118|119):"
    r"(?:hr|hres|hjres|hconres|hamdt|s|sres|sjres|sconres|samdt):"
    r"[1-9]\d*$"
)

JUNK_LEDGER = "junk_exclusions.ndjson"
RESTORATION_LEDGER = "restorations.ndjson"


class ReversibleCullingError(ValueError):
    """Raised when the culling proposal cannot be proven safe."""


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def value_sha256(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
        "+00:00", "Z"
    )


def validate_timestamp(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReversibleCullingError(
            f"{field} must be an ISO-8601 UTC timestamp ending in Z"
        )
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ReversibleCullingError(f"{field} is invalid") from exc
    return value


def require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReversibleCullingError(f"{field} must be a non-empty string")
    return value.strip()


def require_canonical_key(value: Any, field: str = "canonical_key") -> str:
    key = require_text(value, field)
    if not CANONICAL_KEY_RE.fullmatch(key):
        raise ReversibleCullingError(f"{field} is invalid: {key!r}")
    return key


def require_query_id(value: Any, field: str = "query_id") -> str:
    query_id = require_text(value, field)
    if any(character.isspace() for character in query_id):
        raise ReversibleCullingError(f"{field} may not contain whitespace")
    return query_id


def file_receipt(path: Path) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ReversibleCullingError(f"required input is missing: {resolved}")
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": sha256_file(resolved),
    }


def optional_file_receipt(path: Path | None) -> dict[str, Any] | None:
    return file_receipt(path) if path is not None else None


def read_ndjson(
    path: Path,
    *,
    label: str,
) -> list[tuple[dict[str, Any], str]]:
    rows: list[tuple[dict[str, Any], str]] = []
    with path.open("rb") as stream:
        for line_number, raw_with_newline in enumerate(stream, 1):
            if not raw_with_newline.strip():
                continue
            raw = raw_with_newline.rstrip(b"\r\n")
            try:
                value = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReversibleCullingError(
                    f"{label}:{line_number}: invalid JSON"
                ) from exc
            if not isinstance(value, dict):
                raise ReversibleCullingError(
                    f"{label}:{line_number}: row must be an object"
                )
            rows.append((value, sha256_bytes(raw)))
    return rows


def _record_content_sha256(row: Mapping[str, Any]) -> str:
    core = dict(row)
    core.pop("record_content_sha256", None)
    return value_sha256(core)


def _seal_record(row: Mapping[str, Any]) -> dict[str, Any]:
    sealed = dict(row)
    sealed["record_content_sha256"] = _record_content_sha256(sealed)
    return sealed


def _write_new(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError as exc:
        raise ReversibleCullingError(
            f"refusing to overwrite immutable artifact: {path}"
        ) from exc


def _atomic_initialize_empty(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    try:
        os.close(descriptor)
        try:
            os.link(temporary, path)
        except FileExistsError:
            pass
    finally:
        temporary.unlink(missing_ok=True)


class ExclusiveLock:
    def __init__(self, root: Path):
        self.path = root / ".reversible-culling.lock"
        self.descriptor: int | None = None

    def __enter__(self) -> "ExclusiveLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.descriptor = os.open(
                self.path,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError as exc:
            raise ReversibleCullingError(
                f"another culling writer owns {self.path}; inspect it first"
            ) from exc
        os.write(self.descriptor, f"{os.getpid()}\n".encode("ascii"))
        os.fsync(self.descriptor)
        return self

    def __exit__(self, *_: Any) -> None:
        if self.descriptor is not None:
            os.close(self.descriptor)
        self.path.unlink(missing_ok=True)


def initialize_ledgers(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    junk = root / JUNK_LEDGER
    restorations = root / RESTORATION_LEDGER
    if junk.exists() != restorations.exists():
        raise ReversibleCullingError(
            "partial ledger initialization detected; refusing to repair silently"
        )
    if not junk.exists():
        _atomic_initialize_empty(junk)
        _atomic_initialize_empty(restorations)


def _validate_ledger(
    path: Path,
    expected_schema: str,
) -> tuple[list[dict[str, Any]], list[bytes]]:
    rows: list[dict[str, Any]] = []
    raw_lines: list[bytes] = []
    previous = ZERO_SHA256
    with path.open("rb") as stream:
        for line_number, raw_with_newline in enumerate(stream, 1):
            if not raw_with_newline.endswith(b"\n"):
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: unterminated ledger record"
                )
            raw = raw_with_newline[:-1]
            if raw.endswith(b"\r"):
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: noncanonical CRLF"
                )
            try:
                row = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: invalid JSON"
                ) from exc
            if (
                not isinstance(row, dict)
                or canonical_json_bytes(row) != raw
                or row.get("schema") != expected_schema
            ):
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: schema or canonical JSON drift"
                )
            if row.get("previous_record_sha256") != previous:
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: hash chain is broken"
                )
            if row.get("record_content_sha256") != _record_content_sha256(row):
                raise ReversibleCullingError(
                    f"{path.name}:{line_number}: content hash drift"
                )
            previous = sha256_bytes(raw)
            rows.append(row)
            raw_lines.append(raw_with_newline)
    return rows, raw_lines


def _append_ledger_record(
    path: Path,
    rows: list[dict[str, Any]],
    raw_lines: list[bytes],
    core: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    previous = (
        sha256_bytes(raw_lines[-1][:-1]) if raw_lines else ZERO_SHA256
    )
    record = _seal_record({**core, "previous_record_sha256": previous})
    raw = canonical_json_bytes(record)
    with path.open("ab") as stream:
        stream.write(raw + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    rows.append(record)
    raw_lines.append(raw + b"\n")
    return record, sha256_bytes(raw)


def _ledger_receipt(path: Path, raw_lines: list[bytes]) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "record_count": len(raw_lines),
        "tail_record_sha256": (
            sha256_bytes(raw_lines[-1][:-1]) if raw_lines else ZERO_SHA256
        ),
    }


def _load_ledger_state(root: Path) -> dict[str, Any]:
    exclusions, exclusion_lines = _validate_ledger(
        root / JUNK_LEDGER,
        JUNK_SCHEMA,
    )
    restorations, restoration_lines = _validate_ledger(
        root / RESTORATION_LEDGER,
        RESTORATION_SCHEMA,
    )
    exclusion_by_candidate: dict[str, tuple[dict[str, Any], str]] = {}
    exclusion_by_id: dict[str, tuple[dict[str, Any], str]] = {}
    for row, raw_line in zip(exclusions, exclusion_lines):
        key = require_canonical_key(row.get("canonical_key"))
        exclusion_id = require_text(row.get("exclusion_id"), "exclusion_id")
        line_sha = sha256_bytes(raw_line[:-1])
        if key in exclusion_by_candidate:
            raise ReversibleCullingError(
                f"multiple derived junk exclusions for {key}"
            )
        if exclusion_id in exclusion_by_id:
            raise ReversibleCullingError(
                f"duplicate exclusion_id: {exclusion_id}"
            )
        membership_keys = row.get("membership_keys")
        if (
            not isinstance(membership_keys, list)
            or not membership_keys
            or membership_keys != sorted(set(membership_keys))
        ):
            raise ReversibleCullingError(
                f"{key}: exclusion membership_keys are not a unique sorted list"
            )
        exclusion_by_candidate[key] = (row, line_sha)
        exclusion_by_id[exclusion_id] = (row, line_sha)

    restored_candidates: set[str] = set()
    restored_targets: set[str] = set()
    for row in restorations:
        key = require_canonical_key(row.get("canonical_key"))
        target_id = require_text(row.get("target_exclusion_id"), "target_exclusion_id")
        target = exclusion_by_id.get(target_id)
        if target is None:
            raise ReversibleCullingError(
                f"restoration targets unknown exclusion: {target_id}"
            )
        target_row, target_sha = target
        if target_row["canonical_key"] != key:
            raise ReversibleCullingError(
                f"restoration candidate/target mismatch for {key}"
            )
        if row.get("target_exclusion_record_sha256") != target_sha:
            raise ReversibleCullingError(
                f"restoration target hash drift for {key}"
            )
        if target_id in restored_targets or key in restored_candidates:
            raise ReversibleCullingError(
                f"duplicate restoration edge for {key}"
            )
        restored_targets.add(target_id)
        restored_candidates.add(key)

    active_exclusions = {
        key: value
        for key, value in exclusion_by_candidate.items()
        if value[0]["exclusion_id"] not in restored_targets
    }
    return {
        "exclusions": exclusions,
        "exclusion_lines": exclusion_lines,
        "restorations": restorations,
        "restoration_lines": restoration_lines,
        "exclusion_by_candidate": exclusion_by_candidate,
        "exclusion_by_id": exclusion_by_id,
        "restored_candidates": restored_candidates,
        "active_exclusions": active_exclusions,
    }


def _index_evidence(
    rows: Iterable[tuple[dict[str, Any], str]],
) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    values: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    for row, line_sha in rows:
        key = require_canonical_key(row.get("canonical_key"))
        if key in values:
            raise ReversibleCullingError(f"duplicate candidate evidence: {key}")
        values[key] = row
        hashes[key] = line_sha
    return values, hashes


def _index_memberships(
    rows: Iterable[tuple[dict[str, Any], str]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], str]]:
    values: dict[tuple[str, str], dict[str, Any]] = {}
    hashes: dict[tuple[str, str], str] = {}
    for row, line_sha in rows:
        natural_key = (
            require_canonical_key(row.get("canonical_key")),
            require_query_id(row.get("query_id")),
        )
        if natural_key in values:
            raise ReversibleCullingError(
                f"duplicate discovery membership: {natural_key}"
            )
        values[natural_key] = row
        hashes[natural_key] = line_sha
    if not values:
        raise ReversibleCullingError("membership universe is empty")
    return values, hashes


def _index_decisions(
    rows: Iterable[tuple[dict[str, Any], str]],
    membership_keys: set[tuple[str, str]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[tuple[str, str], str]]:
    values: dict[tuple[str, str], dict[str, Any]] = {}
    hashes: dict[tuple[str, str], str] = {}
    for row, line_sha in rows:
        natural_key = (
            require_canonical_key(row.get("canonical_key")),
            require_query_id(row.get("query_id")),
        )
        if natural_key not in membership_keys:
            raise ReversibleCullingError(
                f"decision is outside the discovery universe: {natural_key}"
            )
        if natural_key in values:
            raise ReversibleCullingError(
                f"duplicate membership decision: {natural_key}"
            )
        values[natural_key] = row
        hashes[natural_key] = line_sha
    return values, hashes


def _load_legacy_keys(
    path: Path | None,
    candidate_keys: set[str],
) -> tuple[set[str], dict[str, list[str]]]:
    if path is None:
        return set(), {}
    result: set[str] = set()
    hashes: dict[str, list[str]] = {}
    for row, line_sha in read_ndjson(path, label="legacy_edges"):
        key = require_canonical_key(
            row.get("canonical_key") or row.get("candidate_id")
        )
        if key not in candidate_keys:
            raise ReversibleCullingError(
                f"legacy edge is outside the discovery universe: {key}"
            )
        result.add(key)
        hashes.setdefault(key, []).append(line_sha)
    for values in hashes.values():
        values.sort()
    return result, hashes


def _classify_memberships(
    evidence: Mapping[str, dict[str, Any]],
    evidence_hashes: Mapping[str, str],
    memberships: Mapping[tuple[str, str], dict[str, Any]],
    membership_hashes: Mapping[tuple[str, str], str],
    decisions: Mapping[tuple[str, str], dict[str, Any]],
    decision_hashes: Mapping[tuple[str, str], str],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    evidence_validation: dict[str, tuple[bool, str | None]] = {}
    for key, candidate_evidence in evidence.items():
        try:
            validate_candidate_evidence(candidate_evidence)
            evidence_validation[key] = (True, None)
        except (CullingContractError, TypeError, ValueError) as exc:
            evidence_validation[key] = (False, str(exc))

    for natural_key in sorted(memberships):
        key, query_id = natural_key
        candidate_evidence = evidence.get(key)
        decision = decisions.get(natural_key)
        reasons: list[str] = []
        if candidate_evidence is None:
            reasons.append("missing_candidate_evidence")
        elif not evidence_validation[key][0]:
            reasons.append("invalid_or_incomplete_candidate_evidence")
        if decision is None:
            reasons.append("missing_membership_decision")

        finalizable = bool(
            candidate_evidence is not None
            and decision is not None
            and membership_is_finalizable(decision, candidate_evidence)
        )
        if decision is not None and not finalizable:
            reasons.append("decision_not_finalizable_against_official_evidence")

        if finalizable and decision.get("disposition") == "include":
            disposition = "keep"
        elif (
            finalizable
            and decision.get("disposition") == "exclude_false_positive"
        ):
            disposition = "junk"
        else:
            disposition = "flagged"
        if disposition == "flagged" and not reasons:
            reasons.append("unresolved_membership")

        output.append(
            {
                "schema": MEMBERSHIP_SCHEMA,
                "canonical_key": key,
                "query_id": query_id,
                "disposition": disposition,
                "flag_reasons": sorted(set(reasons)),
                "source_membership_sha256": membership_hashes[natural_key],
                "candidate_evidence_sha256": evidence_hashes.get(key),
                "decision_sha256": decision_hashes.get(natural_key),
                "decision_disposition": (
                    decision.get("disposition") if decision is not None else None
                ),
                "finalizable": finalizable,
                "missing_evidence_can_produce_junk": False,
                "source_candidate_mutated": False,
            }
        )
    return output


def _candidate_rows(
    membership_rows: list[dict[str, Any]],
    *,
    legacy_keys: set[str],
    legacy_hashes: Mapping[str, list[str]],
    ledger_state: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[str]]:
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in membership_rows:
        by_candidate.setdefault(row["canonical_key"], []).append(row)

    rows: list[dict[str, Any]] = []
    eligible_for_new_junk: list[str] = []
    restored_candidates = set(ledger_state["restored_candidates"])
    active_exclusions = ledger_state["active_exclusions"]
    for key in sorted(by_candidate):
        members = sorted(by_candidate[key], key=lambda item: item["query_id"])
        counts = {
            disposition: sum(
                item["disposition"] == disposition for item in members
            )
            for disposition in ("keep", "junk", "flagged")
        }
        legacy_veto = key in legacy_keys
        restored_veto = key in restored_candidates
        active_exclusion = active_exclusions.get(key)
        all_explicitly_excluded = bool(
            members and counts["junk"] == len(members)
        )
        conflict = bool(
            active_exclusion is not None and not all_explicitly_excluded
        )

        reasons: list[str] = []
        if counts["keep"]:
            disposition = "keep"
            reasons.append("one_or_more_memberships_kept")
        elif counts["flagged"]:
            disposition = "flagged"
            reasons.append("one_or_more_memberships_flagged")
        elif legacy_veto:
            disposition = "flagged"
            reasons.append("legacy_edge_vetoes_global_junk")
        elif restored_veto:
            disposition = "flagged"
            reasons.append("restored_edge_vetoes_global_junk")
        elif all_explicitly_excluded:
            disposition = "junk"
            reasons.append("every_membership_explicitly_excluded")
            if active_exclusion is None:
                eligible_for_new_junk.append(key)
        else:
            disposition = "flagged"
            reasons.append("candidate_partition_not_closed")
        if conflict:
            disposition = "flagged"
            reasons.append("active_junk_ledger_conflicts_with_current_memberships")

        rows.append(
            {
                "schema": CANDIDATE_SCHEMA,
                "canonical_key": key,
                "disposition": disposition,
                "membership_count": len(members),
                "membership_counts": counts,
                "membership_keys": [
                    f"{item['canonical_key']}|{item['query_id']}"
                    for item in members
                ],
                "all_memberships_explicitly_excluded": all_explicitly_excluded,
                "legacy_edge_present": legacy_veto,
                "legacy_edge_sha256s": legacy_hashes.get(key, []),
                "restored_edge_present": restored_veto,
                "active_junk_exclusion_present": active_exclusion is not None,
                "partition_reasons": sorted(set(reasons)),
                "candidate_deletion_performed": False,
                "main_corpus_write_authorized": False,
            }
        )
    return rows, eligible_for_new_junk


def _append_new_junk_exclusions(
    root: Path,
    candidate_rows: list[dict[str, Any]],
    eligible: list[str],
    membership_rows: list[dict[str, Any]],
    *,
    event_time: str,
) -> int:
    if not eligible:
        return 0
    validate_timestamp(event_time, "event_time")
    candidate_by_key = {
        row["canonical_key"]: row for row in candidate_rows
    }
    membership_by_candidate: dict[str, list[dict[str, Any]]] = {}
    for row in membership_rows:
        membership_by_candidate.setdefault(row["canonical_key"], []).append(row)

    state = _load_ledger_state(root)
    appended = 0
    for key in sorted(eligible):
        if key in state["exclusion_by_candidate"]:
            continue
        members = sorted(
            membership_by_candidate[key],
            key=lambda item: item["query_id"],
        )
        if not members or any(item["disposition"] != "junk" for item in members):
            raise ReversibleCullingError(
                f"{key}: refusing derived junk append without all memberships junk"
            )
        membership_keys = [
            f"{key}|{item['query_id']}" for item in members
        ]
        binding = [
            {
                "membership_key": f"{key}|{item['query_id']}",
                "source_membership_sha256": item["source_membership_sha256"],
                "candidate_evidence_sha256": item["candidate_evidence_sha256"],
                "decision_sha256": item["decision_sha256"],
            }
            for item in members
        ]
        exclusion_id = "junk-" + value_sha256(
            {
                "canonical_key": key,
                "membership_bindings": binding,
                "tool_version": TOOL_VERSION,
            }
        )[:32]
        _append_ledger_record(
            root / JUNK_LEDGER,
            state["exclusions"],
            state["exclusion_lines"],
            {
                "schema": JUNK_SCHEMA,
                "exclusion_id": exclusion_id,
                "canonical_key": key,
                "recorded_at": event_time,
                "derived_by": {
                    "tool": TOOL_NAME,
                    "version": TOOL_VERSION,
                    "rule": "all-memberships-explicitly-excluded-no-veto-v1",
                },
                "membership_keys": membership_keys,
                "membership_bindings": binding,
                "candidate_partition_sha256": value_sha256(candidate_by_key[key]),
                "restorable": True,
                "source_candidate_mutated": False,
                "main_corpus_write_authorized": False,
            },
        )
        appended += 1
    _load_ledger_state(root)
    return appended


def _ndjson_body(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(canonical_json_bytes(row) + b"\n" for row in rows)


def _flagged_csv_body(rows: list[dict[str, Any]]) -> bytes:
    fields = [
        "canonical_key",
        "query_id",
        "flag_reasons",
        "decision_disposition",
        "candidate_evidence_sha256",
        "decision_sha256",
        "review_decision",
        "review_reason",
        "reviewer",
    ]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "canonical_key": row["canonical_key"],
                "query_id": row["query_id"],
                "flag_reasons": ";".join(row["flag_reasons"]),
                "decision_disposition": row["decision_disposition"] or "",
                "candidate_evidence_sha256": (
                    row["candidate_evidence_sha256"] or ""
                ),
                "decision_sha256": row["decision_sha256"] or "",
                "review_decision": "",
                "review_reason": "",
                "reviewer": "",
            }
        )
    return b"\xef\xbb\xbf" + stream.getvalue().encode("utf-8")


def _ensure_inputs_unchanged(
    before: Mapping[str, dict[str, Any] | None],
) -> None:
    for name, original in before.items():
        if original is None:
            continue
        current = file_receipt(Path(original["path"]))
        if (
            current["bytes"] != original["bytes"]
            or current["sha256"] != original["sha256"]
        ):
            raise ReversibleCullingError(
                f"immutable input changed during culling: {name}"
            )


def build_generation(
    *,
    evidence_path: Path,
    memberships_path: Path,
    decisions_path: Path,
    root: Path,
    legacy_edges_path: Path | None = None,
    event_time: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    inputs = {
        "candidate_evidence": file_receipt(evidence_path),
        "discovery_memberships": file_receipt(memberships_path),
        "membership_decisions": file_receipt(decisions_path),
        "legacy_edges": optional_file_receipt(legacy_edges_path),
    }
    for name, receipt in inputs.items():
        if receipt is None:
            continue
        input_path = Path(receipt["path"])
        try:
            input_path.relative_to(root)
        except ValueError:
            continue
        raise ReversibleCullingError(
            f"{name} is inside the output root; inputs must remain immutable"
        )

    with ExclusiveLock(root):
        initialize_ledgers(root)
        ledger_state = _load_ledger_state(root)
        evidence, evidence_hashes = _index_evidence(
            read_ndjson(evidence_path, label="candidate_evidence")
        )
        memberships, membership_hashes = _index_memberships(
            read_ndjson(memberships_path, label="discovery_memberships")
        )
        candidate_keys = {key for key, _ in memberships}
        extra_evidence = set(evidence) - candidate_keys
        if extra_evidence:
            raise ReversibleCullingError(
                "candidate evidence is outside the discovery membership universe: "
                + ", ".join(sorted(extra_evidence)[:10])
            )
        decisions, decision_hashes = _index_decisions(
            read_ndjson(decisions_path, label="membership_decisions"),
            set(memberships),
        )
        legacy_keys, legacy_hashes = _load_legacy_keys(
            legacy_edges_path,
            candidate_keys,
        )
        membership_rows = _classify_memberships(
            evidence,
            evidence_hashes,
            memberships,
            membership_hashes,
            decisions,
            decision_hashes,
        )
        candidate_rows, eligible = _candidate_rows(
            membership_rows,
            legacy_keys=legacy_keys,
            legacy_hashes=legacy_hashes,
            ledger_state=ledger_state,
        )
        appended_count = _append_new_junk_exclusions(
            root,
            candidate_rows,
            eligible,
            membership_rows,
            event_time=event_time or utc_now(),
        )
        ledger_state = _load_ledger_state(root)
        candidate_rows, _ = _candidate_rows(
            membership_rows,
            legacy_keys=legacy_keys,
            legacy_hashes=legacy_hashes,
            ledger_state=ledger_state,
        )

        membership_counts = {
            disposition: sum(
                row["disposition"] == disposition for row in membership_rows
            )
            for disposition in ("keep", "junk", "flagged")
        }
        candidate_counts = {
            disposition: sum(
                row["disposition"] == disposition for row in candidate_rows
            )
            for disposition in ("keep", "junk", "flagged")
        }
        if sum(membership_counts.values()) != len(membership_rows):
            raise ReversibleCullingError("membership partition is not exact")
        if sum(candidate_counts.values()) != len(candidate_rows):
            raise ReversibleCullingError("candidate partition is not exact")

        flagged_rows = [
            row for row in membership_rows if row["disposition"] == "flagged"
        ]
        junk_receipt = _ledger_receipt(
            root / JUNK_LEDGER,
            ledger_state["exclusion_lines"],
        )
        restoration_receipt = _ledger_receipt(
            root / RESTORATION_LEDGER,
            ledger_state["restoration_lines"],
        )
        generation_basis = {
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "inputs": inputs,
            "junk_ledger": junk_receipt,
            "restoration_ledger": restoration_receipt,
            "membership_rows_sha256": value_sha256(membership_rows),
            "candidate_rows_sha256": value_sha256(candidate_rows),
        }
        generation_id = value_sha256(generation_basis)
        generation_root = root / "generations" / generation_id
        bodies = {
            "membership_partition.ndjson": _ndjson_body(membership_rows),
            "candidate_partition.ndjson": _ndjson_body(candidate_rows),
            "flagged_memberships.ndjson": _ndjson_body(flagged_rows),
            "flagged_memberships.csv": _flagged_csv_body(flagged_rows),
        }
        output_receipts = {
            name: {
                "path": str((generation_root / name).resolve()),
                "bytes": len(body),
                "sha256": sha256_bytes(body),
                "record_count": (
                    len(flagged_rows)
                    if name.startswith("flagged_memberships")
                    else (
                        len(membership_rows)
                        if name.startswith("membership_partition")
                        else len(candidate_rows)
                    )
                ),
            }
            for name, body in bodies.items()
        }
        receipt_core = {
            "schema": RECEIPT_SCHEMA,
            "status": "PASS_REVERSIBLE_CULLING_PROPOSAL",
            "generation_id": generation_id,
            "tool": {"name": TOOL_NAME, "version": TOOL_VERSION},
            "inputs": inputs,
            "ledgers": {
                "junk_exclusions": junk_receipt,
                "restorations": restoration_receipt,
                "new_junk_exclusions_appended": appended_count,
            },
            "counts": {
                "candidate_count": len(candidate_rows),
                "membership_count": len(membership_rows),
                "candidate_partition": candidate_counts,
                "membership_partition": membership_counts,
                "legacy_candidate_veto_count": len(legacy_keys),
                "restored_candidate_veto_count": len(
                    ledger_state["restored_candidates"]
                ),
            },
            "outputs": output_receipts,
            "gates": {
                "membership_partition_exact": True,
                "candidate_partition_exact": True,
                "missing_evidence_flagged_never_junk": True,
                "candidate_junk_requires_every_membership_excluded": True,
                "keep_flagged_legacy_restored_edges_veto_global_junk": True,
                "junk_and_restoration_ledgers_append_only": True,
                "source_candidates_immutable": True,
                "integration_authorized": False,
            },
            "safety": {
                "candidate_deletion_performed": False,
                "source_candidate_write_performed": False,
                "scoring_performed": False,
                "sync_or_promotion_performed": False,
                "main_corpus_write_performed": False,
            },
            "xlsx_status": {
                "created": False,
                "reason": (
                    "artifact-tool workspace dependency loader unavailable; "
                    "reviewable UTF-8 CSV and authoritative NDJSON emitted"
                ),
            },
        }
        receipt = _seal_record(receipt_core)
        manifest = {
            "schema": GENERATION_SCHEMA,
            "generation_id": generation_id,
            "receipt": receipt,
            "generation_basis": generation_basis,
        }
        manifest_body = canonical_json_bytes(manifest) + b"\n"

        if generation_root.exists():
            manifest_path = generation_root / "manifest.json"
            if (
                not manifest_path.is_file()
                or manifest_path.read_bytes() != manifest_body
            ):
                raise ReversibleCullingError(
                    f"immutable generation collision: {generation_root}"
                )
            for name, body in bodies.items():
                if (generation_root / name).read_bytes() != body:
                    raise ReversibleCullingError(
                        f"immutable generation artifact drift: {name}"
                    )
        else:
            generation_root.mkdir(parents=True, exist_ok=False)
            for name, body in bodies.items():
                _write_new(generation_root / name, body)
            _write_new(generation_root / "manifest.json", manifest_body)
        _ensure_inputs_unchanged(inputs)
        return manifest


def append_restoration(
    *,
    root: Path,
    canonical_key: str,
    reason: str,
    restored_by: str,
    restored_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    key = require_canonical_key(canonical_key)
    reason = require_text(reason, "reason")
    restored_by = require_text(restored_by, "restored_by")
    timestamp = validate_timestamp(restored_at or utc_now(), "restored_at")
    with ExclusiveLock(root):
        initialize_ledgers(root)
        state = _load_ledger_state(root)
        target = state["active_exclusions"].get(key)
        if target is None:
            if key in state["restored_candidates"]:
                raise ReversibleCullingError(f"{key} is already restored")
            raise ReversibleCullingError(
                f"{key} has no active derived junk exclusion"
            )
        target_row, target_sha = target
        restoration_id = "restore-" + value_sha256(
            {
                "canonical_key": key,
                "target_exclusion_record_sha256": target_sha,
                "reason": reason,
                "restored_by": restored_by,
                "restored_at": timestamp,
            }
        )[:32]
        record, record_sha = _append_ledger_record(
            root / RESTORATION_LEDGER,
            state["restorations"],
            state["restoration_lines"],
            {
                "schema": RESTORATION_SCHEMA,
                "restoration_id": restoration_id,
                "canonical_key": key,
                "target_exclusion_id": target_row["exclusion_id"],
                "target_exclusion_record_sha256": target_sha,
                "reason": reason,
                "restored_by": restored_by,
                "restored_at": timestamp,
                "source_candidate_mutated": False,
                "main_corpus_write_authorized": False,
            },
        )
        verified = _load_ledger_state(root)
        receipt = _seal_record(
            {
                "schema": "acu-legislation-restoration-receipt-v1",
                "restoration_id": restoration_id,
                "canonical_key": key,
                "restoration_record_sha256": record_sha,
                "restoration_record": record,
                "ledgers": {
                    "junk_exclusions": _ledger_receipt(
                        root / JUNK_LEDGER,
                        verified["exclusion_lines"],
                    ),
                    "restorations": _ledger_receipt(
                        root / RESTORATION_LEDGER,
                        verified["restoration_lines"],
                    ),
                },
                "candidate_restored_edge_active": (
                    key in verified["restored_candidates"]
                ),
                "candidate_deletion_performed": False,
                "main_corpus_write_performed": False,
            }
        )
        receipt_path = (
            root / "restoration_receipts" / f"{restoration_id}.json"
        )
        _write_new(receipt_path, canonical_json_bytes(receipt) + b"\n")
        return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run")
    run.add_argument("--evidence", type=Path, required=True)
    run.add_argument("--memberships", type=Path, required=True)
    run.add_argument("--decisions", type=Path, required=True)
    run.add_argument("--legacy-edges", type=Path)
    run.add_argument("--root", type=Path, required=True)
    run.add_argument("--event-time")

    restore = commands.add_parser("restore")
    restore.add_argument("--root", type=Path, required=True)
    restore.add_argument("--canonical-key", required=True)
    restore.add_argument("--reason", required=True)
    restore.add_argument("--restored-by", required=True)
    restore.add_argument("--restored-at")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "run":
            result = build_generation(
                evidence_path=args.evidence.resolve(),
                memberships_path=args.memberships.resolve(),
                decisions_path=args.decisions.resolve(),
                legacy_edges_path=(
                    args.legacy_edges.resolve() if args.legacy_edges else None
                ),
                root=args.root,
                event_time=args.event_time,
            )
        else:
            result = append_restoration(
                root=args.root,
                canonical_key=args.canonical_key,
                reason=args.reason,
                restored_by=args.restored_by,
                restored_at=args.restored_at,
            )
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (
        ReversibleCullingError,
        CullingContractError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        print(f"FAIL CLOSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())