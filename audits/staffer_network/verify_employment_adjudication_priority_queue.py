from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA_ID = "staffer-network-employment-acquisition-adjudication-priority-independent-verification-v1"
TOKEN_PATTERN = re.compile(
    rb"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[\"'][^\"']+[\"']"
)


class VerificationFailure(RuntimeError):
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
        raise VerificationFailure(f"object required: {path}")
    return value


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationFailure(f"object required at {path}:{line_number}")
            yield value


def expected_bucket(input_row: Mapping[str, Any]) -> tuple[int, str]:
    gaps = set(input_row.get("critical_path_gap_codes") or [])
    flags = input_row.get("coverage_flags") or {}
    if "FORMER_POSITION_CANDIDATE_MISSING" in gaps or flags.get(
        "has_any_employment_candidate"
    ) is not True:
        return 0, "P0_NO_EMPLOYMENT_CANDIDATE"
    if "DATED_FORMER_POSITION_CANDIDATE_MISSING" in gaps:
        return 1, "P1_DATED_FORMER_POSITION_MISSING"
    if "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING" in gaps or flags.get(
        "has_any_bounded_employment_candidate"
    ) is not True:
        return 2, "P2_BOUNDED_INTERVAL_MISSING"
    return 3, "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION"


def verify(primary_dir: Path, twin_dir: Path, output_dir: Path) -> dict[str, Any]:
    payload_name = "employment_acquisition_adjudication_priority_queue_25340.ndjson.gz"
    receipt_name = "employment_acquisition_adjudication_priority_queue_receipt.json"
    primary_payload = (primary_dir / payload_name).resolve(strict=True)
    twin_payload = (twin_dir / payload_name).resolve(strict=True)
    primary_receipt_path = (primary_dir / receipt_name).resolve(strict=True)
    twin_receipt_path = (twin_dir / receipt_name).resolve(strict=True)
    primary_receipt = read_json(primary_receipt_path)
    twin_receipt = read_json(twin_receipt_path)
    input_ledger = Path(primary_receipt["input"]["integration_ledger"]).resolve(strict=True)
    input_rows = {str(row["lda_source_person_id"]): row for row in rows(input_ledger)}

    assertions: dict[str, bool] = {
        "payload_bytes_equal": primary_payload.read_bytes() == twin_payload.read_bytes(),
        "receipt_bytes_equal": primary_receipt_path.read_bytes() == twin_receipt_path.read_bytes(),
        "payload_hash_equal": sha(primary_payload) == sha(twin_payload),
        "receipt_hash_equal": sha(primary_receipt_path) == sha(twin_receipt_path),
        "receipts_pass": primary_receipt.get("status") == twin_receipt.get("status") == "PASS",
        "receipt_binds_payload": (primary_receipt.get("output") or {}).get("sha256")
        == sha(primary_payload),
        "input_hash_bound": primary_receipt["input"].get("integration_ledger_sha256")
        == sha(input_ledger),
        "network_acquisition_not_performed": primary_receipt.get("network_acquisition_performed")
        is False,
        "receipt_zero_promotions": primary_receipt.get("canonical_identity_promotions") == 0
        and primary_receipt.get("canonical_employment_promotions") == 0
        and primary_receipt.get("complete_lifetime_employment_assertions") == 0,
    }

    output_ids: set[str] = set()
    row_failures: Counter[str] = Counter()
    bucket_counts: Counter[str] = Counter()
    overlap_counts: Counter[str] = Counter()
    provider_counts: Counter[str] = Counter()
    previous_sort_key: tuple[Any, ...] | None = None
    row_count = 0
    for output_row in rows(primary_payload):
        row_count += 1
        lda_id = str(output_row.get("lda_source_person_id", ""))
        if lda_id in output_ids:
            row_failures["duplicate_id"] += 1
        output_ids.add(lda_id)
        source = input_rows.get(lda_id)
        if source is None:
            row_failures["out_of_scope_id"] += 1
            continue
        rank, bucket = expected_bucket(source)
        if output_row.get("priority_rank") != rank or output_row.get("priority_bucket") != bucket:
            row_failures["priority_bucket"] += 1
        if output_row.get("priority_queue_ordinal") != row_count:
            row_failures["queue_ordinal"] += 1
        sort_key = tuple(output_row.get("sort_key") or [])
        if previous_sort_key is not None and sort_key < previous_sort_key:
            row_failures["sort_order"] += 1
        previous_sort_key = sort_key
        if output_row.get("explicit_gap_codes") != sorted(
            set(source.get("critical_path_gap_codes") or [])
        ):
            row_failures["gap_preservation"] += 1
        if output_row.get("provider_evidence") != source.get("source_candidate_coverage"):
            row_failures["provider_evidence_preservation"] += 1
        active_expected = sorted(
            name
            for name, coverage in (source.get("source_candidate_coverage") or {}).items()
            if isinstance(coverage, Mapping) and coverage.get("has_candidate") is True
        )
        if output_row.get("active_evidence_providers") != active_expected:
            row_failures["active_provider_set"] += 1
        pointers = output_row.get("provider_evidence_pointers") or {}
        if sorted(pointers) != active_expected:
            row_failures["provider_pointer_set"] += 1
        for provider in active_expected:
            pointer = pointers.get(provider) or {}
            if pointer.get("lda_source_person_id") != lda_id or pointer.get("provider") != provider:
                row_failures["provider_pointer_identity"] += 1
        if output_row.get("adjudication_status") != "REVIEW_REQUIRED":
            row_failures["review_status"] += 1
        if (output_row.get("education") or {}).get("blocking") is not False:
            row_failures["education_blocking"] += 1
        if any(
            output_row.get(key) not in (False, 0, None, "")
            for key in (
                "canonical_employment_promoted",
                "canonical_identity_promoted",
                "complete_lifetime_employment_asserted",
            )
        ):
            row_failures["canonical_promotion"] += 1
        bucket_counts[bucket] += 1
        overlap_counts[str(output_row.get("provider_overlap_bucket"))] += 1
        provider_counts[str(output_row.get("employment_provider_count"))] += 1

    expected_scope = int(primary_receipt.get("output", {}).get("rows", 0))
    assertions.update(
        {
            "exact_scope": row_count == len(output_ids) == len(input_rows) == expected_scope == 25340,
            "scope_ids_exact": output_ids == set(input_rows),
            "all_rows_valid": not row_failures,
            "bucket_counts_exact": dict(sorted(bucket_counts.items()))
            == dict(primary_receipt.get("bucket_counts") or {}),
            "overlap_counts_exact": dict(sorted(overlap_counts.items()))
            == dict(primary_receipt.get("provider_overlap_counts") or {}),
            "provider_distribution_exact": dict(sorted(provider_counts.items()))
            == dict(primary_receipt.get("provider_count_distribution") or {}),
        }
    )
    scanned = (primary_payload, twin_payload, primary_receipt_path, twin_receipt_path)
    token_matches = sum(len(TOKEN_PATTERN.findall(path.read_bytes())) for path in scanned)
    assertions["token_negative_structured_artifact_scan"] = token_matches == 0
    failures = sorted(name for name, passed in assertions.items() if not passed)
    result = {
        "assertions": dict(sorted(assertions.items())),
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "failures": failures,
        "hashes": {
            "primary_payload_sha256": sha(primary_payload),
            "primary_receipt_sha256": sha(primary_receipt_path),
            "twin_payload_sha256": sha(twin_payload),
            "twin_receipt_sha256": sha(twin_receipt_path),
        },
        "provider_count_distribution": dict(sorted(provider_counts.items())),
        "provider_overlap_counts": dict(sorted(overlap_counts.items())),
        "row_failure_counts": dict(sorted(row_failures.items())),
        "schema_id": SCHEMA_ID,
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {"matches": token_matches, "scanned_files": len(scanned)},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "verification_receipt.json").write_bytes(compact(result) + b"\n")
    if failures:
        raise VerificationFailure("verification failed: " + ", ".join(failures))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-dir", required=True, type=Path)
    parser.add_argument("--twin-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.primary_dir, args.twin_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
