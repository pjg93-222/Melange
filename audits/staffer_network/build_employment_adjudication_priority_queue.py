from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


MANIFEST_SCHEMA = "staffer-network-employment-priority-queue-manifest-v1"
ROW_SCHEMA = "staffer-network-employment-acquisition-adjudication-priority-v1"
RECEIPT_SCHEMA = "staffer-network-employment-acquisition-adjudication-priority-receipt-v1"
CONTEXT_ONLY_PROVIDERS = {"lda_registrant_association"}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class GateFailure(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateFailure(f"object required: {path}")
    return value


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise GateFailure(f"object required at {path}:{line_number}")
            yield value


def resolve(manifest_path: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise GateFailure(f"path required: {label}")
    path = Path(raw)
    if not path.is_absolute():
        path = manifest_path.parent / path
    try:
        return path.resolve(strict=True)
    except OSError as exc:
        raise GateFailure(f"path does not exist ({label}): {path}") from exc


def assert_unpromoted(value: Mapping[str, Any], context: str) -> None:
    for key, child in value.items():
        lowered = str(key).lower()
        if lowered in {
            "canonical_employment_promoted",
            "canonical_identity_promoted",
            "canonical_employment_fact",
            "canonical_identity_fact",
            "complete_lifetime_employment_asserted",
        } and child not in (False, 0, None, ""):
            raise GateFailure(f"promotion field set at {context}:{key}")
        if lowered.endswith(
            (
                "canonical_person_id",
                "canonical_employment_episode_id",
                "canonical_employment_fact_id",
                "canonical_fact_id",
            )
        ) and child not in (False, 0, None, ""):
            raise GateFailure(f"canonical ID set at {context}:{key}")


def validate_input(
    ledger: Path,
    receipt_path: Path,
    verification_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = read_json(receipt_path)
    verification = read_json(verification_path)
    if receipt.get("status") != "PASS":
        raise GateFailure("integration receipt is not PASS")
    if verification.get("status") != "PASS":
        raise GateFailure("integration independent verification is not PASS")
    assert_unpromoted(receipt, "integration receipt")
    expected_payload = str((receipt.get("output") or {}).get("sha256", "")).lower()
    actual_payload = sha(ledger)
    if not HEX64.fullmatch(expected_payload) or expected_payload != actual_payload:
        raise GateFailure("integration payload hash mismatch")
    hashes = verification.get("hashes") or {}
    if actual_payload not in {
        str(hashes.get("primary_payload_sha256", "")).lower(),
        str(hashes.get("twin_payload_sha256", "")).lower(),
    }:
        raise GateFailure("independent verification does not bind the integration payload")
    receipt_hash = sha(receipt_path)
    if receipt_hash not in {
        str(hashes.get("primary_receipt_sha256", "")).lower(),
        str(hashes.get("twin_receipt_sha256", "")).lower(),
    }:
        raise GateFailure("independent verification does not bind the integration receipt")
    return receipt, verification


def priority_bucket(row: Mapping[str, Any]) -> tuple[int, str, str]:
    gaps = set(row.get("critical_path_gap_codes") or [])
    flags = row.get("coverage_flags") or {}
    if "FORMER_POSITION_CANDIDATE_MISSING" in gaps or flags.get(
        "has_any_employment_candidate"
    ) is not True:
        return (
            0,
            "P0_NO_EMPLOYMENT_CANDIDATE",
            "Acquire a dated employer-or-office and title from an official payroll, employer biography, or archived profile; retain as REVIEW_REQUIRED.",
        )
    if "DATED_FORMER_POSITION_CANDIDATE_MISSING" in gaps:
        return (
            1,
            "P1_DATED_FORMER_POSITION_MISSING",
            "Resolve dates for the known employer-or-office and title; use bounded source observations and do not infer continuity.",
        )
    if "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING" in gaps or flags.get(
        "has_any_bounded_employment_candidate"
    ) is not True:
        return (
            2,
            "P2_BOUNDED_INTERVAL_MISSING",
            "Acquire start and end bounds for each dated position, preserving uncertainty and report-period-only observations.",
        )
    return (
        3,
        "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION",
        "Adjudicate identity with independent anchors, reconcile provider overlaps, then enumerate unresolved chronology gaps without canonical promotion.",
    )


def provider_paths(receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    inputs = receipt.get("inputs") or {}
    public_pointer = {
        "source_ledger": inputs.get("public_ledger"),
        "source_ledger_sha256": inputs.get("public_ledger_sha256"),
    }
    pointers = {
        name: dict(public_pointer)
        for name in (
            "base_house_payroll",
            "base_senate_payroll",
            "lda_covered_position",
            "lda_registrant_association",
            "littlesis_position",
            "politico_role",
            "public_external",
        )
    }
    for name, lane in sorted((inputs.get("candidate_lanes") or {}).items()):
        pointers[name] = {
            "source_ledger": lane.get("ledger"),
            "source_ledger_sha256": lane.get("ledger_sha256"),
            "source_receipt": lane.get("receipt"),
            "source_receipt_sha256": lane.get("receipt_sha256"),
            "source_verification": lane.get("verification"),
            "source_verification_sha256": lane.get("verification_sha256"),
        }
    return pointers


def build_queue_row(
    row: Mapping[str, Any],
    pointers: Mapping[str, Mapping[str, Any]],
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    assert_unpromoted(row, str(row.get("lda_source_person_id")))
    if row.get("identity_status") != "REVIEW_REQUIRED":
        raise GateFailure("input identity status is not REVIEW_REQUIRED")
    if (row.get("education") or {}).get("blocking") is not False:
        raise GateFailure("education is not nonblocking")
    gaps = sorted(set(row.get("critical_path_gap_codes") or []))
    if "IDENTITY_NOT_ADJUDICATED" not in gaps:
        raise GateFailure("identity-unadjudicated gap is missing")
    source_coverage = row.get("source_candidate_coverage")
    if not isinstance(source_coverage, Mapping):
        raise GateFailure("source candidate coverage object is missing")

    active: list[str] = []
    employment: list[str] = []
    context: list[str] = []
    evidence_pointers: dict[str, dict[str, Any]] = {}
    for provider_name, coverage in sorted(source_coverage.items()):
        if not isinstance(coverage, Mapping) or coverage.get("has_candidate") is not True:
            continue
        active.append(provider_name)
        if provider_name in CONTEXT_ONLY_PROVIDERS:
            context.append(provider_name)
        else:
            employment.append(provider_name)
        pointer = dict(pointers.get(provider_name) or {})
        pointer.update(
            {
                "candidate_count": coverage.get("candidate_count", 0),
                "candidate_id_digest": coverage.get("candidate_id_digest"),
                "interval_digest": coverage.get("interval_digest"),
                "lda_source_person_id": row.get("lda_source_person_id"),
                "provider": provider_name,
            }
        )
        evidence_pointers[provider_name] = pointer

    if len(employment) == 0:
        overlap = "NO_EMPLOYMENT_PROVIDER"
    elif len(employment) == 1:
        overlap = "SINGLE_EMPLOYMENT_PROVIDER"
    else:
        overlap = "MULTI_EMPLOYMENT_PROVIDER_OVERLAP"
    rank, bucket, action = priority_bucket(row)
    provider_gap_rank = len(employment)
    sort_key = (
        rank,
        provider_gap_rank,
        len(active),
        int(row.get("sealed_queue_ordinal", 2**63 - 1)),
        str(row.get("lda_source_person_id")),
    )
    output = {
        "active_evidence_providers": active,
        "adjudication_status": "REVIEW_REQUIRED",
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "complete_lifetime_employment_asserted": False,
        "context_provider_count": len(context),
        "coverage_flags": dict(row.get("coverage_flags") or {}),
        "display_name": row.get("display_name"),
        "education": dict(row.get("education") or {}),
        "employment_provider_count": len(employment),
        "explicit_gap_codes": gaps,
        "lda_source_person_id": row.get("lda_source_person_id"),
        "priority_bucket": bucket,
        "priority_rank": rank,
        "provider_evidence": dict(source_coverage),
        "provider_evidence_pointers": evidence_pointers,
        "provider_overlap_bucket": overlap,
        "recommended_next_action": action,
        "schema_id": ROW_SCHEMA,
        "sealed_queue_ordinal": row.get("sealed_queue_ordinal"),
        "sort_key": list(sort_key),
    }
    return sort_key, output


def write_gzip(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                    for row in rows:
                        text.write(compact(row).decode() + "\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def run(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(manifest_path)
    if manifest.get("schema_id") != MANIFEST_SCHEMA:
        raise GateFailure("unexpected manifest schema")
    input_spec = manifest.get("integration") or {}
    ledger = resolve(manifest_path, input_spec.get("ledger"), "integration.ledger")
    receipt_path = resolve(manifest_path, input_spec.get("receipt"), "integration.receipt")
    verification_path = resolve(
        manifest_path, input_spec.get("verification"), "integration.verification"
    )
    expected_scope = manifest.get("expected_scope_size", 25340)
    if not isinstance(expected_scope, int) or isinstance(expected_scope, bool) or expected_scope < 1:
        raise GateFailure("expected_scope_size must be a positive integer")
    receipt, verification = validate_input(ledger, receipt_path, verification_path)
    pointers = provider_paths(receipt)

    source_ids: set[str] = set()
    queued: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    for row in iter_rows(ledger):
        lda_id = str(row.get("lda_source_person_id", ""))
        if lda_id in source_ids:
            raise GateFailure(f"duplicate input LDA source ID: {lda_id}")
        source_ids.add(lda_id)
        queued.append(build_queue_row(row, pointers))
    if len(source_ids) != expected_scope:
        raise GateFailure(f"scope loss: expected {expected_scope}, got {len(source_ids)}")
    queued.sort(key=lambda item: item[0])
    output_rows: list[dict[str, Any]] = []
    for ordinal, (_, row) in enumerate(queued, start=1):
        row["priority_queue_ordinal"] = ordinal
        output_rows.append(row)
    if len({row["lda_source_person_id"] for row in output_rows}) != expected_scope:
        raise GateFailure("output scope duplication")

    output_dir = output_dir.resolve()
    output_path = output_dir / "employment_acquisition_adjudication_priority_queue_25340.ndjson.gz"
    receipt_output = output_dir / "employment_acquisition_adjudication_priority_queue_receipt.json"
    write_gzip(output_path, output_rows)
    bucket_counts = Counter(row["priority_bucket"] for row in output_rows)
    action_counts = Counter(row["recommended_next_action"] for row in output_rows)
    overlap_counts = Counter(row["provider_overlap_bucket"] for row in output_rows)
    provider_count_distribution = Counter(
        str(row["employment_provider_count"]) for row in output_rows
    )
    result = {
        "action_counts": dict(sorted(action_counts.items())),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": [
                "priority_rank",
                "employment_provider_count",
                "active_provider_count",
                "sealed_queue_ordinal",
                "lda_source_person_id",
            ],
        },
        "education_blocking": False,
        "input": {
            "integration_ledger": str(ledger),
            "integration_ledger_sha256": sha(ledger),
            "integration_receipt": str(receipt_path),
            "integration_receipt_sha256": sha(receipt_path),
            "integration_verification": str(verification_path),
            "integration_verification_sha256": sha(verification_path),
            "manifest": str(manifest_path),
            "manifest_sha256": sha(manifest_path),
        },
        "network_acquisition_performed": False,
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": len(output_rows),
            "sha256": sha(output_path),
            "unique_lda_source_person_ids": len(source_ids),
        },
        "provider_count_distribution": dict(sorted(provider_count_distribution.items())),
        "provider_overlap_counts": dict(sorted(overlap_counts.items())),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "schema_id": RECEIPT_SCHEMA,
        "status": "PASS",
    }
    receipt_output.parent.mkdir(parents=True, exist_ok=True)
    receipt_output.write_bytes(compact(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.manifest, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
