#!/usr/bin/env python3
"""Independently verify A8 House 1997Q1/LDA review candidates.

The verifier does not import the A8 builder.  It independently recreates the
conservative name-compatible source/person pairs, checks their order and every
source/person binding, verifies ambiguity and A5b bucket counts, and enforces
zero canonical promotion.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Mapping


SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-independent-verification-v1"
CANDIDATE_SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-candidate-v1"
RECEIPT_SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-manifest-v1"
TOKEN_RE = re.compile(r"[A-Z0-9]+")
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
BUCKETS = (
    "P0_NO_EMPLOYMENT_CANDIDATE",
    "P1_DATED_FORMER_POSITION_MISSING",
    "P2_BOUNDED_INTERVAL_MISSING",
    "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION",
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def tokens(value: str) -> tuple[str, ...]:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    values = re.findall(r"[A-Z0-9]+", ascii_value.upper())
    while values and values[-1] in SUFFIXES:
        values.pop()
    return tuple(values)


def parse_lda(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def parse_house(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = tokens(value)
    if len(values) < 2:
        return None
    return values[1], values[0], tuple(value for value in values[2:] if value not in SUFFIXES)


def compatible(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    return not left or not right or left[0][0] == right[0][0]


def classify(left: tuple[str, ...], right: tuple[str, ...]) -> str:
    if left == right:
        return "EXACT_NORMALIZED_FULL_NAME"
    if left and right:
        return "EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE"
    return "EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED"


def resolved(repo_root: Path, entry: Mapping[str, Any]) -> Path:
    path = Path(str(entry["path"]))
    return (path if path.is_absolute() else repo_root / path).resolve()


def source_fields_equal(row: Mapping[str, Any], source: Mapping[str, Any]) -> bool:
    pairs = {
        "employing_office_raw": "employing_office_raw",
        "part": "part",
        "payee_raw": "payee_raw",
        "period": "period",
        "period_end": "period_end",
        "period_start": "period_start",
        "service_end_date_candidate_iso": "service_end_date_candidate_iso",
        "service_end_date_raw": "service_end_date_raw",
        "service_start_date_candidate_iso": "service_start_date_candidate_iso",
        "service_start_date_raw": "service_start_date_raw",
        "source_book_id": "book_id",
        "source_candidate_id": "candidate_id",
        "source_pdf_page_number": "source_pdf_page_number",
        "source_pdf_row_y_milli": "source_pdf_row_y_milli",
        "source_pdf_sha256": "source_pdf_sha256",
        "source_title": "source_title",
        "source_url": "source_url",
        "title_description_raw": "title_description_raw",
    }
    return all(row.get(output) == source.get(original) for output, original in pairs.items())


def verify(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    manifest = load_json(args.manifest)
    primary_payload = args.primary / "a8_house_sod_1997q1_lda_match_candidates.ndjson.gz"
    twin_payload = args.twin / "a8_house_sod_1997q1_lda_match_candidates.ndjson.gz"
    primary_receipt_path = args.primary / "a8_house_sod_1997q1_lda_match_receipt.json"
    twin_receipt_path = args.twin / "a8_house_sod_1997q1_lda_match_receipt.json"
    primary_receipt = load_json(primary_receipt_path)
    twin_receipt = load_json(twin_receipt_path)

    assertions: dict[str, bool] = {
        "manifest_schema_valid": manifest.get("schema_id") == MANIFEST_SCHEMA_ID,
        "primary_payload_exists": primary_payload.is_file(),
        "twin_payload_exists": twin_payload.is_file(),
        "primary_receipt_schema_valid": primary_receipt.get("schema_id")
        == RECEIPT_SCHEMA_ID,
        "primary_receipt_pass": primary_receipt.get("status") == "PASS",
        "twin_receipt_pass": twin_receipt.get("status") == "PASS",
        "payload_bytes_equal": primary_payload.read_bytes() == twin_payload.read_bytes(),
        "payload_sha256_equal": sha256_file(primary_payload) == sha256_file(twin_payload),
        "receipt_bytes_equal": primary_receipt_path.read_bytes()
        == twin_receipt_path.read_bytes(),
        "receipt_sha256_equal": sha256_file(primary_receipt_path)
        == sha256_file(twin_receipt_path),
        "gzip_header_mtime_zero": primary_payload.read_bytes()[4:8] == b"\x00\x00\x00\x00",
        "receipt_binds_primary_payload": primary_receipt.get("output", {}).get("sha256")
        == sha256_file(primary_payload),
        "receipt_binds_manifest": primary_receipt.get("manifest", {}).get("sha256")
        == sha256_file(args.manifest),
    }

    input_paths: dict[str, Path] = {}
    input_binding_failures = 0
    for label, entry in manifest.get("inputs", {}).items():
        path = resolved(repo_root, entry)
        input_paths[label] = path
        receipt_entry = primary_receipt.get("input_bindings", {}).get(label, {})
        if not (
            path.is_file()
            and path.stat().st_size == entry.get("bytes") == receipt_entry.get("bytes")
            and sha256_file(path) == entry.get("sha256") == receipt_entry.get("sha256")
            and receipt_entry.get("path") == entry.get("path")
        ):
            input_binding_failures += 1
    assertions["all_manifest_inputs_hash_bound"] = input_binding_failures == 0

    source_rows = list(read_gzip(input_paths["source_personnel_ledger"]))
    a5b_rows = list(read_gzip(input_paths["a5b_priority_ledger"]))
    source_by_id = {row["candidate_id"]: row for row in source_rows}
    person_by_id = {row["lda_source_person_id"]: row for row in a5b_rows}
    assertions.update(
        {
            "source_scope_exact": len(source_rows)
            == len(source_by_id)
            == manifest["expected"]["source_personnel_rows"],
            "a5b_scope_exact": len(a5b_rows)
            == len(person_by_id)
            == manifest["expected"]["a5b_people"],
            "a5b_hash_unchanged_after_generation": sha256_file(
                input_paths["a5b_priority_ledger"]
            )
            == manifest["inputs"]["a5b_priority_ledger"]["sha256"],
            "source_hash_unchanged_after_generation": sha256_file(
                input_paths["source_personnel_ledger"]
            )
            == manifest["inputs"]["source_personnel_ledger"]["sha256"],
        }
    )

    index: defaultdict[
        tuple[str, str], list[tuple[dict[str, Any], tuple[str, ...]]]
    ] = defaultdict(list)
    bucket_scope_counts: Counter[str] = Counter()
    a5b_zero_promotion_violations = 0
    for person in a5b_rows:
        bucket_scope_counts[person.get("priority_bucket")] += 1
        if not (
            person.get("adjudication_status") == "REVIEW_REQUIRED"
            and person.get("canonical_identity_promoted") is False
            and person.get("canonical_employment_promoted") is False
        ):
            a5b_zero_promotion_violations += 1
        parsed = parse_lda(person.get("display_name") or "")
        if parsed:
            first, last, middle = parsed
            index[(first, last)].append((person, middle))
    for values in index.values():
        values.sort(
            key=lambda item: (
                item[0]["sealed_queue_ordinal"],
                item[0]["lda_source_person_id"],
            )
        )

    expected_pairs: list[
        tuple[dict[str, Any], dict[str, Any], tuple[str, ...], tuple[str, ...], int, int]
    ] = []
    expected_source_status: Counter[str] = Counter()
    expected_keys: dict[tuple[str, str, tuple[str, ...]], str] = {}
    for source in source_rows:
        parsed = parse_house(source.get("payee_raw") or "")
        if parsed is None:
            expected_source_status["UNUSABLE"] += 1
            continue
        first, last, house_middle = parsed
        matches = [
            (person, lda_middle)
            for person, lda_middle in index.get((first, last), [])
            if compatible(lda_middle, house_middle)
        ]
        if not matches:
            expected_source_status["NO_LDA_CANDIDATE"] += 1
            continue
        status = "AMBIGUOUS" if len(matches) > 1 else "SINGLE"
        expected_source_status[status] += 1
        expected_keys[(first, last, house_middle)] = status
        display_count = len({person["display_name"] for person, _ in matches})
        for person, lda_middle in matches:
            expected_pairs.append(
                (
                    source,
                    person,
                    lda_middle,
                    house_middle,
                    len(matches),
                    display_count,
                )
            )

    output_rows = list(read_gzip(primary_payload))
    row_failure_counts: Counter[str] = Counter()
    observed_candidate_ids: set[str] = set()
    observed_people: set[str] = set()
    observed_ambiguous_people: set[str] = set()
    observed_single_people: set[str] = set()
    observed_class_counts: Counter[str] = Counter()
    observed_bucket_rows: Counter[str] = Counter()
    observed_bucket_people: defaultdict[str, set[str]] = defaultdict(set)

    if len(output_rows) != len(expected_pairs):
        row_failure_counts["ROW_COUNT_MISMATCH"] += abs(len(output_rows) - len(expected_pairs)) or 1
    for index_number, (row, expected_pair) in enumerate(
        zip(output_rows, expected_pairs, strict=False)
    ):
        source, person, lda_middle, house_middle, match_count, display_count = expected_pair
        match_class = classify(lda_middle, house_middle)
        ambiguous = match_count > 1
        seed = (
            f"{source['candidate_id']}\0{person['lda_source_person_id']}\0{match_class}"
        ).encode("utf-8")
        expected_id = "a8-house-sod-1997q1-lda-match:" + hashlib.sha256(seed).hexdigest()
        expected_flags = [
            "OCR_PUBLIC_SCAN_REVIEW_REQUIRED",
            "NAME_MATCH_ONLY_NO_IDENTITY_ADJUDICATION",
            "REPORT_PERIOD_ONLY_NO_CONTINUITY_INFERENCE",
        ]
        if ambiguous:
            expected_flags.append("MULTIPLE_COMPATIBLE_LDA_PEOPLE")
        if match_class == "EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED":
            expected_flags.append("MIDDLE_NAME_UNSPECIFIED_ON_ONE_SIDE")
        elif match_class == "EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE":
            expected_flags.append("MIDDLE_NAME_INITIAL_COMPATIBILITY_ONLY")

        checks = {
            "SCHEMA": row.get("schema_id") == CANDIDATE_SCHEMA_ID,
            "PAIR_ORDER": (
                row.get("source_candidate_id"), row.get("lda_source_person_id")
            )
            == (source["candidate_id"], person["lda_source_person_id"]),
            "CANDIDATE_ID": row.get("candidate_match_id") == expected_id,
            "SOURCE_BINDING": source_fields_equal(row, source),
            "PERSON_BINDING": (
                row.get("display_name") == person["display_name"]
                and row.get("a5b_priority_bucket_snapshot")
                == person["priority_bucket"]
                and row.get("a5b_priority_queue_ordinal_snapshot")
                == person["priority_queue_ordinal"]
                and row.get("a5b_sealed_queue_ordinal")
                == person["sealed_queue_ordinal"]
            ),
            "CLASS": row.get("candidate_class") == match_class,
            "NORMALIZED_MIDDLE": (
                row.get("normalized_lda_middle_tokens") == list(lda_middle)
                and row.get("normalized_house_middle_tokens") == list(house_middle)
            ),
            "AMBIGUITY": (
                row.get("compatible_lda_candidate_count") == match_count
                and row.get("compatible_lda_display_name_count") == display_count
                and row.get("ambiguity_status")
                == (
                    "MULTIPLE_LDA_CANDIDATES_REVIEW_REQUIRED"
                    if ambiguous
                    else "SINGLE_LDA_CANDIDATE_NOT_IDENTITY_PROOF"
                )
            ),
            "FLAGS": row.get("match_review_flags") == expected_flags,
            "ZERO_PROMOTION": (
                row.get("canonical_identity_decision") == "NOT_ADJUDICATED"
                and row.get("canonical_person_id") is None
                and row.get("canonical_employment_fact") is False
                and row.get("canonical_employment_episode_id") is None
                and row.get("interval_continuity_asserted") is False
                and row.get("candidate_status")
                == "REVIEW_REQUIRED_NAME_ONLY_CANDIDATE"
            ),
            "TEMPORAL_SCOPE": (
                row.get("period") == "1997Q1"
                and row.get("period_start") == "1997-01-01"
                and row.get("period_end") == "1997-03-31"
                and "1997-01-01"
                <= row.get("service_start_date_candidate_iso")
                <= row.get("service_end_date_candidate_iso")
                <= "1997-03-31"
                and row.get("service_date_scope")
                == "OBSERVED_ROW_BOUNDS_WITHIN_1997Q1_REPORT_ONLY"
            ),
            "MATCH_METHOD": row.get("match_method")
            == "EXACT_FIRST_LAST_MIDDLE_COMPATIBLE",
        }
        for label, passed in checks.items():
            if not passed:
                row_failure_counts[label] += 1
        candidate_id = row.get("candidate_match_id")
        if candidate_id in observed_candidate_ids:
            row_failure_counts["DUPLICATE_CANDIDATE_ID"] += 1
        observed_candidate_ids.add(candidate_id)
        lda_id = row.get("lda_source_person_id")
        bucket = row.get("a5b_priority_bucket_snapshot")
        observed_people.add(lda_id)
        observed_bucket_rows[bucket] += 1
        observed_bucket_people[bucket].add(lda_id)
        observed_class_counts[row.get("candidate_class")] += 1
        (observed_ambiguous_people if ambiguous else observed_single_people).add(lda_id)

    expected_bucket_people = {
        bucket: len(observed_bucket_people[bucket]) for bucket in BUCKETS
    }
    expected_bucket_rows = {bucket: observed_bucket_rows[bucket] for bucket in BUCKETS}
    expected_gain = {
        bucket: {
            "bounded_1997q1_candidate_people": expected_bucket_people[bucket],
            "dated_1997q1_candidate_people": expected_bucket_people[bucket],
            "match_candidate_rows": expected_bucket_rows[bucket],
        }
        for bucket in BUCKETS
    }
    expected_ambiguity = {
        "ambiguous_match_candidate_rows": sum(
            1 for row in output_rows if row.get("compatible_lda_candidate_count", 0) > 1
        ),
        "ambiguous_matched_lda_people": len(observed_ambiguous_people),
        "ambiguous_normalized_house_name_keys": sum(
            value == "AMBIGUOUS" for value in expected_keys.values()
        ),
        "ambiguous_source_personnel_rows": expected_source_status["AMBIGUOUS"],
        "single_match_candidate_rows": sum(
            1 for row in output_rows if row.get("compatible_lda_candidate_count") == 1
        ),
        "single_matched_lda_people": len(observed_single_people),
        "single_normalized_house_name_keys": sum(
            value == "SINGLE" for value in expected_keys.values()
        ),
        "single_source_personnel_rows": expected_source_status["SINGLE"],
    }
    receipt_counts = primary_receipt.get("counts", {})
    expected_counts = {
        "a5b_input_people": len(a5b_rows),
        "a5b_unmatched_people": len(a5b_rows) - len(observed_people),
        "distinct_matched_lda_people": len(observed_people),
        "distinct_matched_source_personnel_rows": expected_source_status["AMBIGUOUS"]
        + expected_source_status["SINGLE"],
        "matched_normalized_house_name_keys": len(expected_keys),
        "match_candidate_rows": len(expected_pairs),
        "parseable_source_rows_without_lda_candidate": expected_source_status[
            "NO_LDA_CANDIDATE"
        ],
        "source_personnel_rows": len(source_rows),
        "source_personnel_rows_without_match": expected_source_status["UNUSABLE"]
        + expected_source_status["NO_LDA_CANDIDATE"],
        "unusable_house_payee_rows": expected_source_status["UNUSABLE"],
    }
    assertions.update(
        {
            "expected_candidate_sequence_exact": not row_failure_counts,
            "candidate_ids_unique": len(observed_candidate_ids) == len(output_rows),
            "receipt_counts_exact": receipt_counts == expected_counts,
            "receipt_candidate_class_counts_exact": primary_receipt.get(
                "candidate_class_counts"
            )
            == dict(sorted(observed_class_counts.items())),
            "receipt_ambiguity_counts_exact": primary_receipt.get("ambiguity_counts")
            == expected_ambiguity,
            "receipt_a5b_gain_counts_exact": primary_receipt.get(
                "gain_counts_by_final_a5b_bucket"
            )
            == expected_gain,
            "a5b_bucket_scope_counts_exact": {
                bucket: bucket_scope_counts[bucket] for bucket in BUCKETS
            }
            == manifest["expected"]["a5b_bucket_counts"],
            "a5b_zero_promotion_input": a5b_zero_promotion_violations == 0,
            "zero_people_in_both_ambiguity_classes": not (
                observed_ambiguous_people & observed_single_people
            ),
            "receipt_zero_promotions": primary_receipt.get("validation", {}).get(
                "canonical_identity_promotions"
            )
            == 0
            and primary_receipt.get("validation", {}).get(
                "canonical_employment_promotions"
            )
            == 0
            and primary_receipt.get("validation", {}).get(
                "complete_lifetime_employment_assertions"
            )
            == 0,
        }
    )

    failures = sorted(label for label, passed in assertions.items() if not passed)
    result = {
        "ambiguity_counts": expected_ambiguity,
        "assertions": dict(sorted(assertions.items())),
        "candidate_class_counts": dict(sorted(observed_class_counts.items())),
        "counts": {
            **expected_counts,
            "input_binding_failures": input_binding_failures,
            "row_failure_count": sum(row_failure_counts.values()),
        },
        "failure_codes": failures,
        "gain_counts_by_final_a5b_bucket": expected_gain,
        "hashes": {
            "manifest_sha256": sha256_file(args.manifest),
            "primary_payload_sha256": sha256_file(primary_payload),
            "primary_receipt_sha256": sha256_file(primary_receipt_path),
            "twin_payload_sha256": sha256_file(twin_payload),
            "twin_receipt_sha256": sha256_file(twin_receipt_path),
            "verifier_implementation_sha256": sha256_file(Path(__file__).resolve()),
        },
        "promotion_policy": {
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "candidate_disposition": "REVIEW_REQUIRED_NOT_ADJUDICATED",
            "interval_scope": "1997Q1_REPORT_OBSERVATION_ONLY",
        },
        "row_failure_counts": dict(sorted(row_failure_counts.items())),
        "schema_id": SCHEMA_ID,
        "status": "PASS" if not failures else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--twin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    args.manifest = args.manifest.resolve()
    args.primary = args.primary.resolve()
    args.twin = args.twin.resolve()
    args.output = args.output.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    result = verify(parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
