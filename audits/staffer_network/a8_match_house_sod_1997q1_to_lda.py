#!/usr/bin/env python3
"""Build A8 review-only 1997Q1 House SOD/LDA name-match candidates.

This stage deliberately reuses the conservative name grammar in
``match_lda_house_payroll.py``: LDA names are display-order, House payees are
surname-first, suffixes are ignored, and two stated middle names must share an
initial.  Every compatible LDA person is retained.  A name match is never an
identity adjudication or a canonical employment fact.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Mapping


SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-candidate-v1"
RECEIPT_SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-a8-house-sod-1997q1-lda-match-manifest-v1"
TOKEN_RE = re.compile(r"[A-Z0-9]+")
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
EXPECTED_BUCKETS = (
    "P0_NO_EMPLOYMENT_CANDIDATE",
    "P1_DATED_FORMER_POSITION_MISSING",
    "P2_BOUNDED_INTERVAL_MISSING",
    "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION",
)


class GateFailure(RuntimeError):
    """Raised when a frozen A8 input or zero-promotion invariant fails."""


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


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def normalized_tokens(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    values = TOKEN_RE.findall(normalized.upper())
    while values and values[-1] in SUFFIXES:
        values.pop()
    return tuple(values)


def lda_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = normalized_tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def house_payee_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = normalized_tokens(value)
    if len(values) < 2:
        return None
    # House SOD OCR payees use SURNAME GIVEN [MIDDLE/SUFFIX].  Deliberately do
    # not attempt compound-surname repair: this is the fail-closed A4 grammar.
    surname, given = values[0], values[1]
    middle = tuple(item for item in values[2:] if item not in SUFFIXES)
    return given, surname, middle


def middle_compatible(lda_middle: tuple[str, ...], house_middle: tuple[str, ...]) -> bool:
    if not lda_middle or not house_middle:
        return True
    return lda_middle[0][0] == house_middle[0][0]


def candidate_class(
    lda_middle: tuple[str, ...], house_middle: tuple[str, ...]
) -> str:
    if lda_middle == house_middle:
        return "EXACT_NORMALIZED_FULL_NAME"
    if lda_middle and house_middle:
        return "EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE"
    return "EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED"


def resolve_path(repo_root: Path, entry: Mapping[str, Any]) -> Path:
    value = Path(str(entry["path"]))
    return value if value.is_absolute() else repo_root / value


def bind_file(repo_root: Path, label: str, entry: Mapping[str, Any]) -> Path:
    path = resolve_path(repo_root, entry).resolve()
    if not path.is_file():
        raise GateFailure(f"{label} is missing: {path}")
    observed_bytes = path.stat().st_size
    observed_hash = sha256_file(path)
    if observed_bytes != entry.get("bytes") or observed_hash != entry.get("sha256"):
        raise GateFailure(
            f"{label} seal mismatch: bytes={observed_bytes}, sha256={observed_hash}"
        )
    return path


def validate_frozen_inputs(
    manifest: Mapping[str, Any], repo_root: Path
) -> dict[str, Path]:
    if manifest.get("schema_id") != MANIFEST_SCHEMA_ID:
        raise GateFailure("unexpected A8 manifest schema")
    inputs = manifest.get("inputs", {})
    required = (
        "source_pdf",
        "source_personnel_ledger",
        "source_extraction_receipt",
        "source_independent_verifier",
        "a5b_priority_ledger",
        "a5b_priority_receipt",
        "a5b_independent_verifier",
        "matching_reference_implementation",
    )
    paths = {label: bind_file(repo_root, label, inputs[label]) for label in required}

    extraction = read_json(paths["source_extraction_receipt"])
    source_verifier = read_json(paths["source_independent_verifier"])
    a5b_receipt = read_json(paths["a5b_priority_receipt"])
    a5b_verifier = read_json(paths["a5b_independent_verifier"])
    source_ledger_hash = inputs["source_personnel_ledger"]["sha256"]
    source_pdf_hash = inputs["source_pdf"]["sha256"]
    a5b_ledger_hash = inputs["a5b_priority_ledger"]["sha256"]

    checks = {
        "source_extraction_pass": extraction.get("status") == "PASS",
        "source_extraction_row_count": extraction.get("counts", {}).get("candidate_rows")
        == manifest.get("expected", {}).get("source_personnel_rows"),
        "source_extraction_binds_ledger": extraction.get("output", {}).get("sha256")
        == source_ledger_hash,
        "source_extraction_binds_pdf": bool(extraction.get("sources"))
        and extraction["sources"][0].get("pdf_sha256") == source_pdf_hash,
        "source_verifier_audit_pass": source_verifier.get("audit_status") == "PASS",
        "source_verifier_binds_ledger": source_verifier.get("candidate_twins", {}).get(
            "ledger_sha256"
        )
        == source_ledger_hash,
        "source_verifier_confirms_twin": source_verifier.get("candidate_twins", {}).get(
            "twin_byte_identical"
        )
        is True,
        "source_verifier_confirms_rows": source_verifier.get("candidate_twins", {}).get(
            "candidate_rows"
        )
        == manifest.get("expected", {}).get("source_personnel_rows"),
        "a5b_receipt_pass": a5b_receipt.get("status") == "PASS",
        "a5b_receipt_binds_ledger": a5b_receipt.get("output", {}).get("sha256")
        == a5b_ledger_hash,
        "a5b_receipt_confirms_scope": a5b_receipt.get("output", {}).get("rows")
        == manifest.get("expected", {}).get("a5b_people"),
        "a5b_verifier_pass": a5b_verifier.get("status") == "PASS",
        "a5b_verifier_binds_ledger": a5b_verifier.get("hashes", {}).get(
            "primary_payload_sha256"
        )
        == a5b_ledger_hash,
    }
    failures = sorted(label for label, passed in checks.items() if not passed)
    if failures:
        raise GateFailure("frozen input semantic checks failed: " + ", ".join(failures))
    return paths


def load_a5b_people(
    path: Path, expected_people: int, expected_bucket_counts: Mapping[str, int]
) -> tuple[
    list[dict[str, Any]],
    dict[tuple[str, str], list[tuple[dict[str, Any], tuple[str, ...]]]],
    Counter[str],
]:
    people: list[dict[str, Any]] = []
    by_first_last: defaultdict[
        tuple[str, str], list[tuple[dict[str, Any], tuple[str, ...]]]
    ] = defaultdict(list)
    seen_ids: set[str] = set()
    bucket_counts: Counter[str] = Counter()
    for row in read_gzip(path):
        lda_id = row.get("lda_source_person_id")
        if not lda_id or lda_id in seen_ids:
            raise GateFailure(f"A5b contains a missing or duplicate LDA ID: {lda_id!r}")
        seen_ids.add(lda_id)
        if not (
            row.get("schema_id")
            == "staffer-network-employment-acquisition-adjudication-priority-v1"
            and row.get("adjudication_status") == "REVIEW_REQUIRED"
            and row.get("canonical_identity_promoted") is False
            and row.get("canonical_employment_promoted") is False
        ):
            raise GateFailure(f"A5b zero-promotion invariant failed for {lda_id}")
        bucket = row.get("priority_bucket")
        if bucket not in EXPECTED_BUCKETS:
            raise GateFailure(f"unexpected A5b bucket for {lda_id}: {bucket!r}")
        bucket_counts[bucket] += 1
        people.append(row)
        parsed = lda_name(row.get("display_name") or "")
        if parsed:
            given, surname, middle = parsed
            by_first_last[(given, surname)].append((row, middle))
    if len(people) != expected_people:
        raise GateFailure(f"A5b scope mismatch: {len(people)} != {expected_people}")
    if dict(sorted(bucket_counts.items())) != dict(sorted(expected_bucket_counts.items())):
        raise GateFailure("A5b bucket counts do not match the frozen manifest")
    for candidates in by_first_last.values():
        candidates.sort(
            key=lambda item: (
                item[0]["sealed_queue_ordinal"],
                item[0]["lda_source_person_id"],
            )
        )
    return people, dict(by_first_last), bucket_counts


def compact_candidate(
    source: Mapping[str, Any],
    person: Mapping[str, Any],
    lda_middle: tuple[str, ...],
    house_middle: tuple[str, ...],
    compatible_count: int,
    compatible_display_count: int,
) -> dict[str, Any]:
    match_class = candidate_class(lda_middle, house_middle)
    seed = (
        f"{source['candidate_id']}\0{person['lda_source_person_id']}\0{match_class}"
    ).encode("utf-8")
    ambiguous = compatible_count > 1
    review_flags = [
        "OCR_PUBLIC_SCAN_REVIEW_REQUIRED",
        "NAME_MATCH_ONLY_NO_IDENTITY_ADJUDICATION",
        "REPORT_PERIOD_ONLY_NO_CONTINUITY_INFERENCE",
    ]
    if ambiguous:
        review_flags.append("MULTIPLE_COMPATIBLE_LDA_PEOPLE")
    if match_class == "EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED":
        review_flags.append("MIDDLE_NAME_UNSPECIFIED_ON_ONE_SIDE")
    elif match_class == "EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE":
        review_flags.append("MIDDLE_NAME_INITIAL_COMPATIBILITY_ONLY")
    return {
        "a5b_priority_bucket_snapshot": person["priority_bucket"],
        "a5b_priority_queue_ordinal_snapshot": person["priority_queue_ordinal"],
        "a5b_sealed_queue_ordinal": person["sealed_queue_ordinal"],
        "ambiguity_status": (
            "MULTIPLE_LDA_CANDIDATES_REVIEW_REQUIRED"
            if ambiguous
            else "SINGLE_LDA_CANDIDATE_NOT_IDENTITY_PROOF"
        ),
        "canonical_employment_fact": False,
        "canonical_employment_episode_id": None,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_person_id": None,
        "candidate_class": match_class,
        "candidate_match_id": "a8-house-sod-1997q1-lda-match:"
        + hashlib.sha256(seed).hexdigest(),
        "candidate_status": "REVIEW_REQUIRED_NAME_ONLY_CANDIDATE",
        "compatible_lda_candidate_count": compatible_count,
        "compatible_lda_display_name_count": compatible_display_count,
        "display_name": person["display_name"],
        "employing_office_raw": source["employing_office_raw"],
        "interval_continuity_asserted": False,
        "lda_source_person_id": person["lda_source_person_id"],
        "match_method": "EXACT_FIRST_LAST_MIDDLE_COMPATIBLE",
        "match_review_flags": review_flags,
        "normalized_house_middle_tokens": list(house_middle),
        "normalized_lda_middle_tokens": list(lda_middle),
        "part": source["part"],
        "payee_raw": source["payee_raw"],
        "period": source["period"],
        "period_end": source["period_end"],
        "period_start": source["period_start"],
        "schema_id": SCHEMA_ID,
        "service_date_scope": "OBSERVED_ROW_BOUNDS_WITHIN_1997Q1_REPORT_ONLY",
        "service_end_date_candidate_iso": source["service_end_date_candidate_iso"],
        "service_end_date_raw": source["service_end_date_raw"],
        "service_start_date_candidate_iso": source[
            "service_start_date_candidate_iso"
        ],
        "service_start_date_raw": source["service_start_date_raw"],
        "source_book_id": source["book_id"],
        "source_candidate_id": source["candidate_id"],
        "source_pdf_page_number": source["source_pdf_page_number"],
        "source_pdf_row_y_milli": source["source_pdf_row_y_milli"],
        "source_pdf_sha256": source["source_pdf_sha256"],
        "source_title": source["source_title"],
        "source_url": source["source_url"],
        "title_description_raw": source["title_description_raw"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve()
    manifest = read_json(manifest_path)
    paths = validate_frozen_inputs(manifest, repo_root)
    expected = manifest["expected"]
    people, people_index, observed_bucket_counts = load_a5b_people(
        paths["a5b_priority_ledger"],
        expected["a5b_people"],
        expected["a5b_bucket_counts"],
    )

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise GateFailure(f"output directory is nonempty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "a8_house_sod_1997q1_lda_match_candidates.ndjson.gz"
    receipt_path = args.output_dir / "a8_house_sod_1997q1_lda_match_receipt.json"
    temporary = output_path.with_name(output_path.name + ".part")

    counts: Counter[str] = Counter()
    class_counts: Counter[str] = Counter()
    bucket_candidate_rows: Counter[str] = Counter()
    bucket_people: defaultdict[str, set[str]] = defaultdict(set)
    matched_people: set[str] = set()
    ambiguous_people: set[str] = set()
    single_people: set[str] = set()
    matched_source_ids: set[str] = set()
    matched_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    ambiguous_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    single_keys: set[tuple[str, str, tuple[str, ...]]] = set()
    source_ids: set[str] = set()
    previous_source_sort_key: tuple[Any, ...] | None = None

    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            with io.TextIOWrapper(zipped, encoding="utf-8", newline="\n") as writer:
                for source in read_gzip(paths["source_personnel_ledger"]):
                    counts["source_personnel_rows"] += 1
                    source_id = source.get("candidate_id")
                    if not source_id or source_id in source_ids:
                        raise GateFailure(
                            f"source contains missing or duplicate candidate ID: {source_id!r}"
                        )
                    source_ids.add(source_id)
                    source_sort_key = (
                        source.get("period"),
                        source.get("part"),
                        source.get("source_pdf_page_number"),
                        source.get("source_pdf_row_y_milli"),
                        source_id,
                    )
                    if previous_source_sort_key is not None and source_sort_key < previous_source_sort_key:
                        raise GateFailure("source personnel ledger is not in declared deterministic order")
                    previous_source_sort_key = source_sort_key
                    start = source.get("service_start_date_candidate_iso")
                    end = source.get("service_end_date_candidate_iso")
                    if not (
                        source.get("schema_id")
                        == "staffer-network-house-sod-google-books-personnel-candidate-v1"
                        and source.get("period") == "1997Q1"
                        and source.get("part") == 2
                        and source.get("source_pdf_sha256")
                        == manifest["inputs"]["source_pdf"]["sha256"]
                        and source.get("canonical_identity_decision") == "NOT_ADJUDICATED"
                        and source.get("canonical_person_id") is None
                        and source.get("canonical_employment_episode_id") is None
                        and source.get("canonical_employing_office_id") is None
                        and source.get("canonical_service_start_date") is None
                        and source.get("canonical_service_end_date") is None
                        and source.get("period_start") == "1997-01-01"
                        and source.get("period_end") == "1997-03-31"
                        and start is not None
                        and end is not None
                        and "1997-01-01" <= start <= end <= "1997-03-31"
                    ):
                        raise GateFailure(f"source row invariant failed: {source_id}")

                    parsed = house_payee_name(source.get("payee_raw") or "")
                    if parsed is None:
                        counts["unusable_house_payee_rows"] += 1
                        continue
                    given, surname, house_middle = parsed
                    compatible = [
                        (person, lda_middle)
                        for person, lda_middle in people_index.get((given, surname), [])
                        if middle_compatible(lda_middle, house_middle)
                    ]
                    if not compatible:
                        counts["parseable_source_rows_without_lda_candidate"] += 1
                        continue

                    matched_source_ids.add(source_id)
                    key = (given, surname, house_middle)
                    matched_keys.add(key)
                    compatible_display_count = len(
                        {person["display_name"] for person, _ in compatible}
                    )
                    ambiguous = len(compatible) > 1
                    if ambiguous:
                        counts["ambiguous_source_rows"] += 1
                        ambiguous_keys.add(key)
                    else:
                        counts["single_candidate_source_rows"] += 1
                        single_keys.add(key)
                    for person, lda_middle in compatible:
                        row = compact_candidate(
                            source,
                            person,
                            lda_middle,
                            house_middle,
                            len(compatible),
                            compatible_display_count,
                        )
                        writer.write(canonical_bytes(row).decode("utf-8"))
                        counts["match_candidate_rows"] += 1
                        counts["ambiguous_match_candidate_rows"] += int(ambiguous)
                        counts["single_match_candidate_rows"] += int(not ambiguous)
                        class_counts[row["candidate_class"]] += 1
                        bucket = person["priority_bucket"]
                        bucket_candidate_rows[bucket] += 1
                        lda_id = person["lda_source_person_id"]
                        bucket_people[bucket].add(lda_id)
                        matched_people.add(lda_id)
                        (ambiguous_people if ambiguous else single_people).add(lda_id)
    os.replace(temporary, output_path)

    if counts["source_personnel_rows"] != expected["source_personnel_rows"]:
        raise GateFailure("source row count changed after the frozen-input check")
    if ambiguous_people & single_people:
        raise GateFailure("a person appeared in both ambiguity classes")
    source_rows_without_match = (
        counts["unusable_house_payee_rows"]
        + counts["parseable_source_rows_without_lda_candidate"]
    )
    bucket_people_counts = {
        bucket: len(bucket_people[bucket]) for bucket in EXPECTED_BUCKETS
    }
    bucket_row_counts = {
        bucket: bucket_candidate_rows[bucket] for bucket in EXPECTED_BUCKETS
    }
    receipt = {
        "ambiguity_counts": {
            "ambiguous_match_candidate_rows": counts[
                "ambiguous_match_candidate_rows"
            ],
            "ambiguous_matched_lda_people": len(ambiguous_people),
            "ambiguous_normalized_house_name_keys": len(ambiguous_keys),
            "ambiguous_source_personnel_rows": counts["ambiguous_source_rows"],
            "single_match_candidate_rows": counts["single_match_candidate_rows"],
            "single_matched_lda_people": len(single_people),
            "single_normalized_house_name_keys": len(single_keys),
            "single_source_personnel_rows": counts["single_candidate_source_rows"],
        },
        "candidate_class_counts": dict(sorted(class_counts.items())),
        "counts": {
            "a5b_input_people": len(people),
            "a5b_unmatched_people": len(people) - len(matched_people),
            "distinct_matched_lda_people": len(matched_people),
            "distinct_matched_source_personnel_rows": len(matched_source_ids),
            "matched_normalized_house_name_keys": len(matched_keys),
            "match_candidate_rows": counts["match_candidate_rows"],
            "parseable_source_rows_without_lda_candidate": counts[
                "parseable_source_rows_without_lda_candidate"
            ],
            "source_personnel_rows": counts["source_personnel_rows"],
            "source_personnel_rows_without_match": source_rows_without_match,
            "unusable_house_payee_rows": counts["unusable_house_payee_rows"],
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "source_order_required": [
                "period",
                "part",
                "source_pdf_page_number",
                "source_pdf_row_y_milli",
                "candidate_id",
            ],
            "within_source_row_order": [
                "a5b_sealed_queue_ordinal",
                "lda_source_person_id",
            ],
        },
        "gain_counts_by_final_a5b_bucket": {
            bucket: {
                "dated_1997q1_candidate_people": bucket_people_counts[bucket],
                "bounded_1997q1_candidate_people": bucket_people_counts[bucket],
                "match_candidate_rows": bucket_row_counts[bucket],
            }
            for bucket in EXPECTED_BUCKETS
        },
        "input_bindings": {
            label: {
                "bytes": manifest["inputs"][label]["bytes"],
                "path": manifest["inputs"][label]["path"],
                "sha256": manifest["inputs"][label]["sha256"],
            }
            for label in sorted(manifest["inputs"])
        },
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "manifest": {
            "bytes": manifest_path.stat().st_size,
            "path": str(manifest_path),
            "sha256": sha256_file(manifest_path),
        },
        "observed_final_a5b_bucket_counts": {
            bucket: observed_bucket_counts[bucket] for bucket in EXPECTED_BUCKETS
        },
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": counts["match_candidate_rows"],
            "sha256": sha256_file(output_path),
        },
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "risk_notes": [
            "Exact normalized name compatibility is discovery evidence and never a canonical identity decision.",
            "The source is Google Books OCR of a public House scan, not an official House-hosted PDF; names, offices, titles, dates, and amounts may contain OCR errors.",
            "Surname-first parsing intentionally preserves the conservative A4 grammar and does not repair compound-surname or OCR edge cases.",
            "Every compatible same-name LDA person is retained and multiplicity is explicit; a single compatible roster candidate is still not identity proof.",
            "Service dates are bounded observations inside the 1997Q1 report only; no continuity, tenure outside the report, or complete employment history is asserted.",
            "A8 is additive and does not overwrite or promote any A4/A5b record.",
        ],
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS",
        "validation": {
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "complete_lifetime_employment_assertions": 0,
            "source_pdf_hash_bound": True,
            "source_ledger_hash_bound": True,
            "source_receipt_hash_bound": True,
            "source_verifier_hash_bound": True,
            "a5b_ledger_hash_bound": True,
            "a5b_receipt_hash_bound": True,
            "a5b_verifier_hash_bound": True,
        },
    }
    receipt_path.write_bytes(canonical_bytes(receipt))
    return {
        "receipt": receipt,
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    args.manifest = args.manifest.resolve()
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
