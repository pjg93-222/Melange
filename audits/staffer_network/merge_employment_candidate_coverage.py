from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


SCHEMA_ID = "staffer-network-employment-candidate-coverage-v1"
RECEIPT_SCHEMA_ID = "staffer-network-employment-candidate-coverage-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-employment-candidate-integration-manifest-v1"
EXPECTED_PUBLIC_VALIDATION_SCHEMA = "staffer-network-public-employment-lane-validation-receipt-v1"
SAFE_IDENTITY_DECISIONS = {
    "",
    "NOT_ADJUDICATED",
    "REVIEW_REQUIRED",
    "REVIEW_REQUIRED_NOT_ADJUDICATED",
    "UNVERIFIED_CANDIDATE",
}
PROMOTED_ID_SUFFIXES = (
    "canonical_person_id",
    "canonical_employment_episode_id",
    "canonical_employment_fact_id",
    "canonical_fact_id",
)
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LANE_NAME = re.compile(r"^[a-z][a-z0-9_-]*$")


class GateFailure(RuntimeError):
    """Raised when an input violates a non-negotiable integration gate."""


def compact_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure(f"cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise GateFailure(f"JSON object required: {path}")
    return value


def iter_ndjson(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    try:
        with opener(path, "rt", encoding="utf-8", newline="") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                try:
                    value = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise GateFailure(f"invalid NDJSON at {path}:{line_number}: {exc}") from exc
                if not isinstance(value, dict):
                    raise GateFailure(f"NDJSON object required at {path}:{line_number}")
                yield value
    except OSError as exc:
        raise GateFailure(f"cannot read NDJSON {path}: {exc}") from exc


def _is_nonzero(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, str):
        return value.strip().upper() not in SAFE_IDENTITY_DECISIONS
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return bool(value)


def assert_no_canonical_promotion(value: Any, context: str, trail: tuple[str, ...] = ()) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            key_lower = key.lower()
            child_trail = (*trail, key)
            dotted = ".".join(child_trail)
            if key_lower.endswith(PROMOTED_ID_SUFFIXES) and child not in (None, "", False, 0):
                raise GateFailure(f"canonical ID promotion at {context}:{dotted}")
            if "canonical" in key_lower:
                if key_lower.startswith("zero_canonical_"):
                    if child is not True:
                        raise GateFailure(f"zero-canonical assertion failed at {context}:{dotted}")
                elif key_lower.endswith("identity_decision"):
                    if str(child or "").strip().upper() not in SAFE_IDENTITY_DECISIONS:
                        raise GateFailure(f"adjudicated canonical identity at {context}:{dotted}")
                elif any(token in key_lower for token in ("promot", "canonicalized")):
                    if _is_nonzero(child):
                        raise GateFailure(f"canonical promotion at {context}:{dotted}")
                elif key_lower.endswith(("employment_fact", "identity_fact")) and _is_nonzero(child):
                    raise GateFailure(f"canonical fact promotion at {context}:{dotted}")
            if "complete_lifetime_employment_assert" in key_lower and _is_nonzero(child):
                raise GateFailure(f"complete lifetime history assertion at {context}:{dotted}")
            assert_no_canonical_promotion(child, context, child_trail)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_no_canonical_promotion(child, context, (*trail, str(index)))


def require_pass(receipt: Mapping[str, Any], context: str) -> None:
    if str(receipt.get("status", "")).upper() != "PASS":
        raise GateFailure(f"{context} status is not PASS")
    assert_no_canonical_promotion(receipt, context)


def receipt_output_hash(receipt: Mapping[str, Any], context: str) -> str:
    output = receipt.get("output")
    if not isinstance(output, Mapping):
        raise GateFailure(f"{context} has no output object")
    expected = str(output.get("sha256", "")).lower()
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        raise GateFailure(f"{context} has no valid output.sha256")
    return expected


def require_payload_hash(path: Path, receipt: Mapping[str, Any], context: str) -> str:
    expected = receipt_output_hash(receipt, context)
    actual = sha256_file(path)
    if actual != expected:
        raise GateFailure(f"payload hash mismatch for {context}: expected {expected}, got {actual}")
    return actual


def resolve_path(manifest_path: Path, raw_path: Any, field: str) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise GateFailure(f"manifest path required: {field}")
    path = Path(raw_path)
    if not path.is_absolute():
        path = manifest_path.parent / path
    try:
        path = path.resolve(strict=True)
    except OSError as exc:
        raise GateFailure(f"manifest path does not exist ({field}): {path}") from exc
    return path


def validate_public_binding(
    ledger_path: Path,
    receipt_path: Path,
    validation_path: Path,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    receipt = read_json(receipt_path)
    validation = read_json(validation_path)
    require_pass(receipt, "public receipt")
    require_pass(validation, "public validation receipt")
    if validation.get("schema_id") != EXPECTED_PUBLIC_VALIDATION_SCHEMA:
        raise GateFailure("unexpected public validation schema")
    gates = validation.get("gates")
    required_gates = (
        "education_nonblocking",
        "queue_candidate_only",
        "queue_scope_25340_conserved",
        "token_negative_structured_artifact_scan",
    )
    if not isinstance(gates, Mapping) or not all(gates.get(name) is True for name in required_gates):
        raise GateFailure("public validation receipt is missing a required PASS gate")
    controls = validation.get("adjudication_controls")
    if not isinstance(controls, Mapping):
        raise GateFailure("public validation receipt has no adjudication controls")
    if str(controls.get("identity_status", "")).upper() != "REVIEW_REQUIRED":
        raise GateFailure("public validation identity status is not REVIEW_REQUIRED")
    ledger_hash = require_payload_hash(ledger_path, receipt, "public receipt")
    validation_hash = str(
        (validation.get("artifact_hashes") or {}).get("full_acquisition_queue", "")
    ).lower()
    if validation_hash != ledger_hash:
        raise GateFailure("public validation does not bind the supplied queue payload hash")

    receipt_hash = sha256_file(receipt_path)
    queue_comparison = next(
        (
            item
            for item in validation.get("comparisons", [])
            if isinstance(item, Mapping) and item.get("name") == "public_employment_acquisition_queue"
        ),
        None,
    )
    if not isinstance(queue_comparison, Mapping):
        raise GateFailure("public validation has no acquisition-queue twin comparison")
    manifests = (
        queue_comparison.get("primary_manifest"),
        queue_comparison.get("twin_manifest"),
    )
    allowed_receipt_hashes = {
        str(manifest.get("public_employment_acquisition_queue_receipt.json", "")).lower()
        for manifest in manifests
        if isinstance(manifest, Mapping)
    }
    if receipt_hash not in allowed_receipt_hashes:
        raise GateFailure("public validation does not bind the supplied public receipt hash")
    if queue_comparison.get("per_file_sha256_equal") is not True:
        raise GateFailure("public queue twin comparison is not byte-equal")
    return receipt, validation, ledger_hash


def _valid_date(value: Any) -> str | None:
    if isinstance(value, str) and ISO_DATE.fullmatch(value):
        return value
    return None


def extract_intervals(row: Mapping[str, Any]) -> list[tuple[str | None, str | None, str]]:
    intervals: list[tuple[str | None, str | None, str]] = []
    direct_pairs = (
        ("service_start_date_candidate", "service_end_date_candidate", "SERVICE_DATE_CANDIDATE"),
        ("service_start_date_candidate_iso", "service_end_date_candidate_iso", "SERVICE_DATE_CANDIDATE"),
        ("period_start", "period_end", "REPORT_PERIOD_OBSERVATION"),
        ("start_date", "end_date", "DATE_CANDIDATE"),
        ("start", "end", "INTERVAL_OBSERVATION"),
    )
    for start_key, end_key, basis in direct_pairs:
        start = _valid_date(row.get(start_key))
        end = _valid_date(row.get(end_key))
        if start or end:
            intervals.append((start, end, basis))
    observed = row.get("observed_report_intervals")
    if isinstance(observed, list):
        for item in observed:
            if not isinstance(item, Mapping):
                continue
            start = _valid_date(item.get("start"))
            end = _valid_date(item.get("end"))
            if start or end:
                intervals.append((start, end, str(item.get("basis") or "REPORT_PERIOD_OBSERVATION")))
    unique = sorted(set(intervals), key=lambda item: (item[0] or "", item[1] or "", item[2]))
    return unique


def candidate_id(row: Mapping[str, Any]) -> str:
    for field in (
        "match_candidate_id",
        "candidate_match_id",
        "candidate_id",
        "employment_candidate_id",
    ):
        value = row.get(field)
        if isinstance(value, str) and value:
            return value
    return "row-sha256:" + hashlib.sha256(compact_json(row)).hexdigest()


def _public_source_counts(row: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    counts = row.get("candidate_counts")
    if not isinstance(counts, Mapping):
        raise GateFailure("public row candidate_counts must be an object")

    def integer(name: str) -> int:
        value = counts.get(name, 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise GateFailure(f"invalid public candidate count: {name}")
        return value

    external_count = integer("repaired_public_external_employment") + integer(
        "legacy_public_external_employment"
    )
    external_dated = integer("repaired_public_external_employment_dated") + integer(
        "legacy_public_external_employment_dated"
    )
    external_bounded = integer("repaired_public_external_employment_bounded") + integer(
        "legacy_public_external_employment_bounded"
    )
    specifications = {
        "public_external": (external_count, external_dated, external_bounded),
        "littlesis_position": (
            integer("littlesis_position"),
            integer("littlesis_position_dated"),
            integer("littlesis_position_bounded"),
        ),
        "politico_role": (integer("politico_role_observation_time_only"), 0, 0),
        "base_house_payroll": (integer("base_house_payroll_match_groups"), 0, 0),
        "base_senate_payroll": (integer("base_senate_payroll_match_groups"), 0, 0),
        "lda_covered_position": (integer("base_lda_covered_position_claims"), 0, 0),
        "lda_registrant_association": (integer("base_registrant_association_episodes"), 0, 0),
    }
    return {
        name: {
            "bounded_candidate_count": bounded,
            "candidate_count": count,
            "dated_candidate_count": dated,
            "has_bounded_candidate": bounded > 0,
            "has_candidate": count > 0,
            "has_dated_candidate": dated > 0,
        }
        for name, (count, dated, bounded) in specifications.items()
    }


def load_public_scope(
    ledger_path: Path,
    expected_scope_size: int,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    people: dict[str, dict[str, Any]] = {}
    ordered_ids: list[str] = []
    for line_number, row in enumerate(iter_ndjson(ledger_path), start=1):
        assert_no_canonical_promotion(row, f"public queue row {line_number}")
        lda_id = row.get("lda_source_person_id")
        if not isinstance(lda_id, str) or not lda_id.startswith("lda:lobbyist:"):
            raise GateFailure(f"invalid LDA source ID at public queue row {line_number}")
        if lda_id in people:
            raise GateFailure(f"duplicate public-scope LDA source ID: {lda_id}")
        if str(row.get("identity_status", "")).upper() != "REVIEW_REQUIRED":
            raise GateFailure(f"public queue row is not REVIEW_REQUIRED: {lda_id}")
        if row.get("secondary_nonblocking") != "EDUCATION":
            raise GateFailure(f"education is not explicitly nonblocking for {lda_id}")
        people[lda_id] = row
        ordered_ids.append(lda_id)
    if len(people) != expected_scope_size:
        raise GateFailure(
            f"public-scope conservation failed: expected {expected_scope_size}, got {len(people)}"
        )
    ordered_ids.sort(
        key=lambda lda_id: (
            int(people[lda_id].get("sealed_queue_ordinal", 2**63 - 1)),
            lda_id,
        )
    )
    return people, ordered_ids


def aggregate_lane(
    lane_name: str,
    ledger_path: Path,
    receipt_path: Path,
    verification_path: Path | None,
    public_ids: set[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    receipt = read_json(receipt_path)
    require_pass(receipt, f"{lane_name} receipt")
    payload_hash = require_payload_hash(ledger_path, receipt, f"{lane_name} receipt")
    verification_hash: str | None = None
    if verification_path is not None:
        verification = read_json(verification_path)
        require_pass(verification, f"{lane_name} verification")
        verification_hash = sha256_file(verification_path)
        binding_keys = {
            "candidate_payload_sha256",
            "match_candidate_sha256",
            "primary_payload_sha256",
            "twin_payload_sha256",
        }
        bound_payload_hashes: set[str] = set()

        def collect_bindings(value: Any) -> None:
            if isinstance(value, Mapping):
                for key, child in value.items():
                    if str(key).lower() in binding_keys and isinstance(child, str):
                        bound_payload_hashes.add(child.lower())
                    collect_bindings(child)
            elif isinstance(value, list):
                for child in value:
                    collect_bindings(child)

        collect_bindings(verification)
        if payload_hash not in bound_payload_hashes:
            raise GateFailure(f"{lane_name} verification does not bind the supplied candidate payload")

    state: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "candidate_ids": [],
            "intervals": [],
            "titles": set(),
            "offices": set(),
        }
    )
    row_count = 0
    for line_number, row in enumerate(iter_ndjson(ledger_path), start=1):
        row_count += 1
        assert_no_canonical_promotion(row, f"{lane_name} row {line_number}")
        lda_id = row.get("lda_source_person_id")
        if not isinstance(lda_id, str) or lda_id not in public_ids:
            raise GateFailure(f"{lane_name} row has an out-of-scope LDA source ID: {lda_id!r}")
        entry = state[lda_id]
        entry["candidate_ids"].append(candidate_id(row))
        entry["intervals"].extend(extract_intervals(row))
        for field in ("title_candidate", "title_description_raw"):
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                entry["titles"].add(value.strip())
        for field in ("employing_office_candidate", "employing_office_raw"):
            value = row.get(field)
            if isinstance(value, str) and value.strip():
                entry["offices"].add(value.strip())

    output_meta = receipt.get("output")
    declared_rows = output_meta.get("rows") if isinstance(output_meta, Mapping) else None
    if declared_rows is None:
        declared_rows = receipt.get("match_candidate_rows")
    if declared_rows is not None and declared_rows != row_count:
        raise GateFailure(
            f"{lane_name} receipt row count mismatch: expected {declared_rows}, got {row_count}"
        )

    result: dict[str, dict[str, Any]] = {}
    for lda_id, entry in state.items():
        candidate_ids = sorted(entry["candidate_ids"])
        if len(candidate_ids) != len(set(candidate_ids)):
            raise GateFailure(f"{lane_name} contains duplicate candidate IDs for {lda_id}")
        intervals = sorted(
            set(entry["intervals"]),
            key=lambda item: (item[0] or "", item[1] or "", item[2]),
        )
        dated_candidates = sum(1 for start, end, _ in intervals if start or end)
        bounded_candidates = sum(1 for start, end, _ in intervals if start and end)
        starts = [start for start, _, _ in intervals if start]
        ends = [end for _, end, _ in intervals if end]
        result[lda_id] = {
            "bounded_interval_count": bounded_candidates,
            "candidate_count": len(candidate_ids),
            "candidate_id_digest": hashlib.sha256(compact_json(candidate_ids)).hexdigest(),
            "dated_interval_count": dated_candidates,
            "distinct_employing_office_count": len(entry["offices"]),
            "distinct_title_count": len(entry["titles"]),
            "earliest_interval_start": min(starts) if starts else None,
            "has_bounded_candidate": bounded_candidates > 0,
            "has_candidate": bool(candidate_ids),
            "has_dated_candidate": dated_candidates > 0,
            "interval_digest": hashlib.sha256(compact_json(intervals)).hexdigest(),
            "interval_observation_count": len(intervals),
            "latest_interval_end": max(ends) if ends else None,
        }
    return result, {
        "ledger": str(ledger_path),
        "ledger_bytes": ledger_path.stat().st_size,
        "ledger_rows": row_count,
        "ledger_sha256": payload_hash,
        "receipt": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "verification": str(verification_path) if verification_path else None,
        "verification_sha256": verification_hash,
    }


def _public_coverage_flags(row: Mapping[str, Any]) -> tuple[bool, bool, bool]:
    flags = row.get("evidence_flags")
    if not isinstance(flags, Mapping):
        raise GateFailure("public row evidence_flags must be an object")
    return (
        flags.get("has_any_employment_candidate") is True,
        flags.get("has_any_dated_employment_candidate") is True,
        flags.get("has_any_bounded_employment_candidate") is True,
    )


def build_row(
    public_row: Mapping[str, Any],
    lane_results: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, Any]:
    lda_id = str(public_row["lda_source_person_id"])
    source_coverage = _public_source_counts(public_row)
    any_public, dated_public, bounded_public = _public_coverage_flags(public_row)
    any_candidate = any_public
    any_dated = dated_public
    any_bounded = bounded_public
    lane_any_candidate = False
    lane_any_dated = False
    lane_any_bounded = False

    for lane_name in sorted(lane_results):
        lane_value = lane_results[lane_name].get(lda_id)
        if lane_value is None:
            source_coverage[lane_name] = {
                "bounded_interval_count": 0,
                "candidate_count": 0,
                "candidate_id_digest": hashlib.sha256(compact_json([])).hexdigest(),
                "dated_interval_count": 0,
                "distinct_employing_office_count": 0,
                "distinct_title_count": 0,
                "earliest_interval_start": None,
                "has_bounded_candidate": False,
                "has_candidate": False,
                "has_dated_candidate": False,
                "interval_digest": hashlib.sha256(compact_json([])).hexdigest(),
                "interval_observation_count": 0,
                "latest_interval_end": None,
            }
            continue
        source_coverage[lane_name] = dict(lane_value)
        any_candidate = any_candidate or lane_value["has_candidate"] is True
        any_dated = any_dated or lane_value["has_dated_candidate"] is True
        any_bounded = any_bounded or lane_value["has_bounded_candidate"] is True
        lane_any_candidate = lane_any_candidate or lane_value["has_candidate"] is True
        lane_any_dated = lane_any_dated or lane_value["has_dated_candidate"] is True
        lane_any_bounded = lane_any_bounded or lane_value["has_bounded_candidate"] is True

    gaps = set(public_row.get("critical_path_gap_codes") or [])
    # The validated public queue is authoritative for its own gap semantics. In
    # particular, a dated LDA filing association is not necessarily a former
    # position. Only newly supplied employment lanes can close an existing
    # public-queue candidate gap here.
    if lane_any_candidate:
        gaps.discard("FORMER_POSITION_CANDIDATE_MISSING")
    if lane_any_dated:
        gaps.discard("DATED_FORMER_POSITION_CANDIDATE_MISSING")
    if lane_any_bounded:
        gaps.discard("BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING")
    gaps.update(
        {
            "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
            "EMPLOYMENT_GAPS_NOT_ADJUDICATED",
            "HILL_HISTORY_NOT_EXHAUSTIVE",
            "IDENTITY_NOT_ADJUDICATED",
            "PRIVATE_SECTOR_HISTORY_NOT_EXHAUSTIVE",
        }
    )
    for lane_name in sorted(lane_results):
        if not source_coverage[lane_name]["has_candidate"]:
            gaps.add(f"{lane_name.upper()}_CANDIDATE_MISSING")

    row = {
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "complete_lifetime_employment_asserted": False,
        "coverage_flags": {
            "has_any_bounded_employment_candidate": any_bounded,
            "has_any_dated_employment_candidate": any_dated,
            "has_any_employment_candidate": any_candidate,
        },
        "critical_path_gap_codes": sorted(gaps),
        "display_name": public_row.get("display_name"),
        "education": {
            "blocking": False,
            "diagnostic_gap_codes": sorted(public_row.get("secondary_enrichment_gap_codes") or []),
        },
        "identity_status": "REVIEW_REQUIRED",
        "lda_source_person_id": lda_id,
        "review_disposition": "REVIEW_REQUIRED",
        "schema_id": SCHEMA_ID,
        "sealed_queue_ordinal": public_row.get("sealed_queue_ordinal"),
        "source_candidate_coverage": source_coverage,
    }
    assert_no_canonical_promotion(row, f"integrated output row {lda_id}")
    return row


def write_deterministic_gzip(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp_path = Path(raw_temp)
    try:
        with temp_path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                    for row in rows:
                        text.write(compact_json(row).decode("utf-8"))
                        text.write("\n")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_json_atomic(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_temp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp_path = Path(raw_temp)
    try:
        temp_path.write_bytes(compact_json(value) + b"\n")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def run(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(manifest_path)
    if manifest.get("schema_id") != MANIFEST_SCHEMA_ID:
        raise GateFailure("unexpected integration manifest schema")
    expected_scope_size = manifest.get("expected_scope_size", 25340)
    if not isinstance(expected_scope_size, int) or isinstance(expected_scope_size, bool) or expected_scope_size < 1:
        raise GateFailure("expected_scope_size must be a positive integer")

    public_spec = manifest.get("public_queue")
    if not isinstance(public_spec, Mapping):
        raise GateFailure("manifest public_queue object is required")
    public_ledger = resolve_path(manifest_path, public_spec.get("ledger"), "public_queue.ledger")
    public_receipt = resolve_path(manifest_path, public_spec.get("receipt"), "public_queue.receipt")
    public_validation = resolve_path(
        manifest_path, public_spec.get("validation"), "public_queue.validation"
    )
    receipt, validation, public_hash = validate_public_binding(
        public_ledger, public_receipt, public_validation
    )
    people, ordered_ids = load_public_scope(public_ledger, expected_scope_size)
    if receipt.get("unique_lda_source_person_ids") != expected_scope_size:
        raise GateFailure("public receipt unique-ID count does not match the expected scope")
    if receipt.get("output_rows") != expected_scope_size:
        raise GateFailure("public receipt output-row count does not match the expected scope")

    lane_results: dict[str, dict[str, dict[str, Any]]] = {}
    lane_inputs: dict[str, dict[str, Any]] = {}
    lane_specs = manifest.get("candidate_lanes", [])
    if not isinstance(lane_specs, list):
        raise GateFailure("candidate_lanes must be a list")
    for index, lane_spec in enumerate(lane_specs):
        if not isinstance(lane_spec, Mapping):
            raise GateFailure(f"candidate_lanes[{index}] must be an object")
        lane_name = str(lane_spec.get("name", ""))
        if not LANE_NAME.fullmatch(lane_name):
            raise GateFailure(f"invalid candidate lane name: {lane_name!r}")
        if lane_name in lane_results:
            raise GateFailure(f"duplicate candidate lane name: {lane_name}")
        ledger_path = resolve_path(manifest_path, lane_spec.get("ledger"), f"{lane_name}.ledger")
        receipt_path = resolve_path(manifest_path, lane_spec.get("receipt"), f"{lane_name}.receipt")
        verification_raw = lane_spec.get("verification")
        verification_path = (
            resolve_path(manifest_path, verification_raw, f"{lane_name}.verification")
            if verification_raw
            else None
        )
        lane_result, lane_input = aggregate_lane(
            lane_name,
            ledger_path,
            receipt_path,
            verification_path,
            set(people),
        )
        lane_results[lane_name] = lane_result
        lane_inputs[lane_name] = lane_input

    output_rows = [build_row(people[lda_id], lane_results) for lda_id in ordered_ids]
    if len(output_rows) != expected_scope_size:
        raise GateFailure("output scope loss detected before write")
    if len({row["lda_source_person_id"] for row in output_rows}) != expected_scope_size:
        raise GateFailure("output scope duplication detected before write")
    if any(row["identity_status"] != "REVIEW_REQUIRED" for row in output_rows):
        raise GateFailure("non-review output status detected before write")

    output_dir = output_dir.resolve()
    output_path = output_dir / "employment_candidate_coverage_25340.ndjson.gz"
    receipt_path = output_dir / "employment_candidate_coverage_receipt.json"
    write_deterministic_gzip(output_path, output_rows)
    output_hash = sha256_file(output_path)
    gap_counts: Counter[str] = Counter()
    lane_people_counts: Counter[str] = Counter()
    bounded_people = dated_people = candidate_people = 0
    for row in output_rows:
        gap_counts.update(row["critical_path_gap_codes"])
        flags = row["coverage_flags"]
        candidate_people += int(flags["has_any_employment_candidate"])
        dated_people += int(flags["has_any_dated_employment_candidate"])
        bounded_people += int(flags["has_any_bounded_employment_candidate"])
        for lane_name in lane_results:
            lane_people_counts[lane_name] += int(
                row["source_candidate_coverage"][lane_name]["has_candidate"]
            )

    integrated_receipt = {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "coverage_counts": {
            "people_with_any_bounded_employment_candidate": bounded_people,
            "people_with_any_dated_employment_candidate": dated_people,
            "people_with_any_employment_candidate": candidate_people,
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["sealed_queue_ordinal", "lda_source_person_id"],
        },
        "education_blocking": False,
        "expected_scope_size": expected_scope_size,
        "gap_counts": dict(sorted(gap_counts.items())),
        "inputs": {
            "candidate_lanes": dict(sorted(lane_inputs.items())),
            "manifest": str(manifest_path),
            "manifest_sha256": sha256_file(manifest_path),
            "public_ledger": str(public_ledger),
            "public_ledger_sha256": public_hash,
            "public_receipt": str(public_receipt),
            "public_receipt_sha256": sha256_file(public_receipt),
            "public_validation": str(public_validation),
            "public_validation_sha256": sha256_file(public_validation),
        },
        "lane_people_with_candidates": dict(sorted(lane_people_counts.items())),
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": len(output_rows),
            "sha256": output_hash,
            "unique_lda_source_person_ids": len(
                {row["lda_source_person_id"] for row in output_rows}
            ),
        },
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS",
    }
    assert_no_canonical_promotion(integrated_receipt, "integrated receipt")
    write_json_atomic(receipt_path, integrated_receipt)
    return integrated_receipt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge validated employment candidates into one REVIEW_REQUIRED row per LDA ID."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        receipt = run(args.manifest, args.output_dir)
    except GateFailure as exc:
        raise SystemExit(f"GATE_FAILURE: {exc}") from exc
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
