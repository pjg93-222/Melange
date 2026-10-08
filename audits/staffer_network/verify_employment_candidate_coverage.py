from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA_ID = "staffer-network-employment-candidate-coverage-independent-verification-v1"
EXPECTED_ROWS = 25340
HEX64 = re.compile(r"^[0-9a-f]{64}$")
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


def resolve(manifest_path: Path, raw: Any) -> Path:
    path = Path(str(raw))
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve(strict=True)


def assert_zero_promotions(row: Mapping[str, Any], context: str) -> None:
    for key, value in row.items():
        lowered = str(key).lower()
        if lowered in {
            "canonical_employment_promoted",
            "canonical_identity_promoted",
            "canonical_employment_fact",
            "canonical_identity_fact",
            "complete_lifetime_employment_asserted",
        } and value not in (False, 0, None, ""):
            raise VerificationFailure(f"promotion field set in {context}: {key}")
        if lowered.endswith(
            (
                "canonical_person_id",
                "canonical_employment_episode_id",
                "canonical_employment_fact_id",
                "canonical_fact_id",
            )
        ) and value not in (False, 0, None, ""):
            raise VerificationFailure(f"canonical ID set in {context}: {key}")


def candidate_sets(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for lane in manifest.get("candidate_lanes", []):
        name = str(lane["name"])
        ledger = resolve(manifest_path, lane["ledger"])
        result[name] = {str(row["lda_source_person_id"]) for row in rows(ledger)}
    return result


def verify(manifest_path: Path, primary_dir: Path, twin_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(manifest_path)
    primary_payload = (primary_dir / "employment_candidate_coverage_25340.ndjson.gz").resolve(
        strict=True
    )
    twin_payload = (twin_dir / "employment_candidate_coverage_25340.ndjson.gz").resolve(strict=True)
    primary_receipt_path = (primary_dir / "employment_candidate_coverage_receipt.json").resolve(
        strict=True
    )
    twin_receipt_path = (twin_dir / "employment_candidate_coverage_receipt.json").resolve(strict=True)
    primary_receipt = read_json(primary_receipt_path)
    twin_receipt = read_json(twin_receipt_path)

    assertions: dict[str, bool] = {
        "payload_bytes_equal": primary_payload.read_bytes() == twin_payload.read_bytes(),
        "payload_sha256_equal": sha(primary_payload) == sha(twin_payload),
        "receipt_bytes_equal": primary_receipt_path.read_bytes() == twin_receipt_path.read_bytes(),
        "receipt_sha256_equal": sha(primary_receipt_path) == sha(twin_receipt_path),
        "primary_receipt_pass": primary_receipt.get("status") == "PASS",
        "twin_receipt_pass": twin_receipt.get("status") == "PASS",
        "receipt_binds_primary_payload": (
            (primary_receipt.get("output") or {}).get("sha256") == sha(primary_payload)
        ),
        "receipt_binds_twin_payload": (
            (twin_receipt.get("output") or {}).get("sha256") == sha(twin_payload)
        ),
        "receipt_zero_canonical_promotions": all(
            receipt.get("canonical_employment_promotions") == 0
            and receipt.get("canonical_identity_promotions") == 0
            and receipt.get("complete_lifetime_employment_assertions") == 0
            for receipt in (primary_receipt, twin_receipt)
        ),
    }

    public_spec = manifest["public_queue"]
    public_path = resolve(manifest_path, public_spec["ledger"])
    public_rows = list(rows(public_path))
    public_ids = {str(row["lda_source_person_id"]) for row in public_rows}
    public_any = {
        str(row["lda_source_person_id"])
        for row in public_rows
        if (row.get("evidence_flags") or {}).get("has_any_employment_candidate") is True
    }
    lane_sets = candidate_sets(manifest_path, manifest)
    candidate_counts_by_id: dict[str, Counter[str]] = defaultdict(Counter)
    for lane_name, lane in [(str(item["name"]), item) for item in manifest.get("candidate_lanes", [])]:
        for candidate in rows(resolve(manifest_path, lane["ledger"])):
            candidate_counts_by_id[str(candidate["lda_source_person_id"])][lane_name] += 1

    output_ids: set[str] = set()
    gap_counts: Counter[str] = Counter()
    combination_counts: Counter[str] = Counter()
    row_count = 0
    duplicate_ids = 0
    row_failures: Counter[str] = Counter()
    required_gaps = {
        "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
        "EMPLOYMENT_GAPS_NOT_ADJUDICATED",
        "HILL_HISTORY_NOT_EXHAUSTIVE",
        "IDENTITY_NOT_ADJUDICATED",
        "PRIVATE_SECTOR_HISTORY_NOT_EXHAUSTIVE",
    }
    for row in rows(primary_payload):
        row_count += 1
        lda_id = str(row.get("lda_source_person_id", ""))
        if lda_id in output_ids:
            duplicate_ids += 1
        output_ids.add(lda_id)
        try:
            assert_zero_promotions(row, lda_id)
        except VerificationFailure:
            row_failures["canonical_promotion"] += 1
        if row.get("identity_status") != "REVIEW_REQUIRED":
            row_failures["identity_status"] += 1
        if row.get("review_disposition") != "REVIEW_REQUIRED":
            row_failures["review_disposition"] += 1
        if (row.get("education") or {}).get("blocking") is not False:
            row_failures["education_blocking"] += 1
        gaps = set(row.get("critical_path_gap_codes") or [])
        if not required_gaps.issubset(gaps):
            row_failures["mandatory_gap_missing"] += 1
        gap_counts.update(gaps)
        coverage = row.get("source_candidate_coverage") or {}
        for lane_name in lane_sets:
            actual = int((coverage.get(lane_name) or {}).get("candidate_count", -1))
            expected = candidate_counts_by_id[lda_id][lane_name]
            if actual != expected:
                row_failures[f"{lane_name}_candidate_count"] += 1
            missing_code = f"{lane_name.upper()}_CANDIDATE_MISSING"
            if (expected == 0) != (missing_code in gaps):
                row_failures[f"{lane_name}_missing_gap"] += 1
        labels = []
        if lda_id in public_any:
            labels.append("PUBLIC")
        labels.extend(name.upper() for name in sorted(lane_sets) if lda_id in lane_sets[name])
        combination_counts["+".join(labels) if labels else "NO_CANDIDATE"] += 1

    assertions.update(
        {
            "exact_row_count": row_count == EXPECTED_ROWS,
            "unique_output_ids": len(output_ids) == EXPECTED_ROWS and duplicate_ids == 0,
            "public_scope_exact": output_ids == public_ids and len(public_ids) == EXPECTED_ROWS,
            "all_rows_review_required": not row_failures,
            "education_nonblocking": row_failures["education_blocking"] == 0,
            "gap_counts_match_receipt": dict(sorted(gap_counts.items()))
            == dict((primary_receipt.get("gap_counts") or {})),
            "lane_people_counts_match_receipt": {
                name: len(ids) for name, ids in sorted(lane_sets.items())
            }
            == dict(primary_receipt.get("lane_people_with_candidates") or {}),
        }
    )

    scanned_paths = (
        primary_payload,
        twin_payload,
        primary_receipt_path,
        twin_receipt_path,
    )
    token_matches = sum(len(TOKEN_PATTERN.findall(path.read_bytes())) for path in scanned_paths)
    assertions["token_negative_structured_artifact_scan"] = token_matches == 0
    failures = sorted(name for name, passed in assertions.items() if not passed)

    lane_overlap_counts: dict[str, int] = {}
    lane_names = sorted(lane_sets)
    for left_index, left in enumerate(lane_names):
        lane_overlap_counts[f"PUBLIC&{left.upper()}"] = len(public_any & lane_sets[left])
        lane_overlap_counts[f"PUBLIC_ONLY_RELATIVE_TO_{left.upper()}"] = len(public_any - lane_sets[left])
        lane_overlap_counts[f"{left.upper()}_NEW_TO_PUBLIC"] = len(lane_sets[left] - public_any)
        for right in lane_names[left_index + 1 :]:
            lane_overlap_counts[f"{left.upper()}&{right.upper()}"] = len(
                lane_sets[left] & lane_sets[right]
            )
            lane_overlap_counts[f"PUBLIC&{left.upper()}&{right.upper()}"] = len(
                public_any & lane_sets[left] & lane_sets[right]
            )

    verification = {
        "assertions": dict(sorted(assertions.items())),
        "candidate_combination_counts": dict(sorted(combination_counts.items())),
        "counts": {
            "duplicate_output_ids": duplicate_ids,
            "output_rows": row_count,
            "public_candidate_people": len(public_any),
            "public_scope_people": len(public_ids),
            "row_failure_counts": dict(sorted(row_failures.items())),
            "unique_output_ids": len(output_ids),
        },
        "failures": failures,
        "gap_counts": dict(sorted(gap_counts.items())),
        "hashes": {
            "manifest_sha256": sha(manifest_path),
            "primary_payload_sha256": sha(primary_payload),
            "primary_receipt_sha256": sha(primary_receipt_path),
            "twin_payload_sha256": sha(twin_payload),
            "twin_receipt_sha256": sha(twin_receipt_path),
        },
        "lane_overlap_counts": dict(sorted(lane_overlap_counts.items())),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "schema_id": SCHEMA_ID,
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {"matches": token_matches, "scanned_files": len(scanned_paths)},
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "verification_receipt.json"
    output_path.write_bytes(compact(verification) + b"\n")
    if failures:
        raise VerificationFailure("verification failed: " + ", ".join(failures))
    return verification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--primary-dir", required=True, type=Path)
    parser.add_argument("--twin-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.manifest, args.primary_dir, args.twin_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
