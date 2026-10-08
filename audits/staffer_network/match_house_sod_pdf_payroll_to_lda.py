#!/usr/bin/env python3
"""Produce non-canonical LDA name-match candidates from House PDF payroll rows."""

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
from typing import Any, Iterable

import acquire_house_sod_payroll as base


ROOT = Path(__file__).resolve().parent
DEFAULT_PAYROLL = ROOT / "house_sod_payroll_20260831" / "house_sod_payroll_pdf_candidates.ndjson.gz"
DEFAULT_PEOPLE = ROOT / "lda_employment_materialization_20260831" / "lda_employment_people.ndjson.gz"
DEFAULT_OUTPUT_DIR = ROOT / "house_sod_pdf_lda_name_matches_20260831"
SCHEMA_ID = "staffer-network-house-sod-pdf-lda-name-match-candidate-v2"
RECEIPT_SCHEMA_ID = "staffer-network-house-sod-pdf-lda-name-match-receipt-v2"
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
TRAILING_DATE_RE = re.compile(r"(?:\s+\d{1,2}/\d{1,2}/\d{2,4})+$")


def tokens(value: str) -> tuple[str, ...]:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_value = "".join(character for character in decomposed if not unicodedata.combining(character))
    return tuple(re.findall(r"[A-Z0-9]+", ascii_value.upper()))


def last_name_index(values: tuple[str, ...]) -> int:
    index = len(values) - 1
    while index > 0 and values[index] in SUFFIXES:
        index -= 1
    return index


def first_last(values: tuple[str, ...]) -> tuple[str, str] | None:
    if len(values) < 2:
        return None
    last_index = last_name_index(values)
    if last_index <= 0 or len(values[0]) < 2 or len(values[last_index]) < 2:
        return None
    return values[0], values[last_index]


def payee_signature(raw: str) -> tuple[tuple[str, ...] | None, str, bool]:
    stripped = TRAILING_DATE_RE.sub("", raw.strip())
    trailing_date_removed = stripped != raw.strip()
    if "," in stripped:
        family_raw, given_raw = stripped.split(",", 1)
        family_tokens = list(tokens(family_raw))
        suffix_tokens = []
        while family_tokens and family_tokens[-1] in SUFFIXES:
            suffix_tokens.insert(0, family_tokens.pop())
        signature = (*tokens(given_raw), *family_tokens, *suffix_tokens)
        method = "HOUSE_LAST_COMMA_GIVEN_EXACT_NORMALIZATION"
    else:
        signature = tokens(stripped)
        method = "HOUSE_DISPLAY_ORDER_EXACT_NORMALIZATION"
    if len(signature) < 2 or signature in {("DO",), ("D", "O")}:
        return None, "UNUSABLE_PAYEE_NAME_SHAPE", trailing_date_removed
    return tuple(signature), method, trailing_date_removed


def load_people(path: Path) -> tuple[list[dict[str, Any]], dict[tuple[str, ...], list[dict[str, Any]]], dict[tuple[str, str], list[dict[str, Any]]]]:
    people = []
    full_index: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    first_last_index: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    with gzip.open(path, "rt", encoding="utf-8") as source:
        for line in source:
            person = json.loads(line)
            signature = tokens(person["display_name"])
            people.append(person)
            full_index[signature].append(person)
            key = first_last(signature)
            if key:
                first_last_index[key].append(person)
    for values in full_index.values():
        values.sort(key=lambda row: (row["queue_rank"], row["lda_source_person_id"]))
    for values in first_last_index.values():
        values.sort(key=lambda row: (row["queue_rank"], row["lda_source_person_id"]))
    return people, full_index, first_last_index


def compact_candidate(
    payroll: dict[str, Any],
    person: dict[str, Any],
    method: str,
    signature: tuple[str, ...],
    ambiguous: bool,
    trailing_date_removed: bool,
    temporal_relationship: str,
    temporal_review_flags: list[str],
) -> dict[str, Any]:
    seed = (
        f"{payroll['candidate_id']}\0{person['lda_source_person_id']}\0{method}"
    ).encode("utf-8")
    return {
        "canonical_employment_episode_id": None,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_person_id": None,
        "candidate_match_id": "house-sod-pdf-lda-match:" + hashlib.sha256(seed).hexdigest(),
        "corroboration_status": "UNVERIFIED_NAME_ONLY_CANDIDATE",
        "employing_office_raw": payroll["employing_office_raw"],
        "identity_verification_status": "UNVERIFIED_CANDIDATE",
        "lda_display_name": person["display_name"],
        "lda_queue_rank": person["queue_rank"],
        "lda_source_person_id": person["lda_source_person_id"],
        "match_method": method,
        "match_review_flags": [
            *(["NORMALIZED_FULL_NAME_MAP_HAS_MULTIPLE_LDA_PEOPLE"] if ambiguous else []),
            *(["TRAILING_DATE_TOKEN_REMOVED_FROM_PAYEE_FOR_NAME_MATCH"] if trailing_date_removed else []),
            *temporal_review_flags,
            "NAME_MATCH_ONLY_NO_IDENTITY_ADJUDICATION",
        ],
        "normalized_name_signature": list(signature),
        "payroll_amount_raw": payroll["amount_raw"],
        "payroll_candidate_id": payroll["candidate_id"],
        "payroll_payee_raw": payroll["payee_raw"],
        "period": payroll["period"],
        "period_end": payroll["period_end"],
        "period_start": payroll["period_start"],
        "schema_id": SCHEMA_ID,
        "service_end_date_candidate_iso": payroll["service_end_date_candidate_iso"],
        "service_end_date_raw": payroll["service_end_date_raw"],
        "service_start_date_candidate_iso": payroll["service_start_date_candidate_iso"],
        "service_start_date_raw": payroll["service_start_date_raw"],
        "service_date_report_period_relationship": temporal_relationship,
        "source_pdf_page_number": payroll["source_pdf_page_number"],
        "source_pdf_row_y_milli": payroll["source_pdf_row_y_milli"],
        "source_pdf_sha256": payroll["source_pdf_sha256"],
        "source_url": payroll["source_url"],
        "title_description_raw": payroll["title_description_raw"],
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    people, full_index, first_last_index = load_people(args.people)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "house_sod_pdf_lda_name_match_candidates.ndjson.gz"
    receipt_path = args.output_dir / "house_sod_pdf_lda_name_match_receipt.json"
    temporary = output_path.with_name(output_path.name + ".part")
    counts = Counter()
    matched_lda_ids = set()
    matched_payroll_ids = set()
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as writer:
                with gzip.open(args.payroll, "rt", encoding="utf-8") as payroll_rows:
                    for line in payroll_rows:
                        payroll = json.loads(line)
                        counts["payroll_input_rows"] += 1
                        start = payroll.get("service_start_date_candidate_iso")
                        end = payroll.get("service_end_date_candidate_iso")
                        period_start = payroll["period_start"]
                        period_end = payroll["period_end"]
                        if start is None or end is None:
                            counts["unparsed_service_range_rows_not_emitted"] += 1
                            continue
                        if start > end:
                            counts["reversed_service_range_rows_not_emitted"] += 1
                            continue
                        if start > period_end or end > period_end:
                            counts["future_service_range_rows_not_emitted"] += 1
                            continue
                        temporal_review_flags = []
                        if end < period_start:
                            temporal_relationship = "ENTIRE_SERVICE_RANGE_BEFORE_REPORT_PERIOD"
                            temporal_review_flags.append("SERVICE_RANGE_ENDS_BEFORE_REPORT_PERIOD_REVIEW_REQUIRED")
                        elif start < period_start:
                            temporal_relationship = "SERVICE_RANGE_BEGINS_BEFORE_REPORT_PERIOD"
                        else:
                            temporal_relationship = "SERVICE_RANGE_WITHIN_REPORT_PERIOD"
                        if start < period_start:
                            temporal_review_flags.append("SERVICE_RANGE_BEGINS_BEFORE_REPORT_PERIOD_REVIEW_REQUIRED")
                            counts["pre_report_service_range_rows_retained_with_review_flag"] += 1
                        signature, payee_method, trailing_date_removed = payee_signature(payroll["payee_raw"])
                        if signature is None:
                            counts["unusable_payee_name_shape_rows"] += 1
                            continue
                        matches = full_index.get(signature, [])
                        method = "EXACT_NORMALIZED_FULL_NAME"
                        if not matches:
                            key = first_last(signature)
                            possible = first_last_index.get(key, []) if key else []
                            if len(possible) == 1:
                                matches = possible
                                method = "UNIQUE_LDA_FIRST_LAST_NAME"
                            elif len(possible) > 1:
                                counts["ambiguous_first_last_rows_not_emitted"] += 1
                                continue
                        if not matches:
                            counts["no_lda_name_candidate_rows"] += 1
                            continue
                        ambiguous = len(matches) > 1
                        matched_payroll_ids.add(payroll["candidate_id"])
                        counts["matched_payroll_rows"] += 1
                        counts[f"matched_payroll_rows_{method.lower()}"] += 1
                        counts[f"payee_parse_{payee_method.lower()}"] += 1
                        counts["matched_rows_with_trailing_date_removed"] += int(trailing_date_removed)
                        for person in matches:
                            matched_lda_ids.add(person["lda_source_person_id"])
                            candidate = compact_candidate(
                                payroll,
                                person,
                                method,
                                signature,
                                ambiguous,
                                trailing_date_removed,
                                temporal_relationship,
                                temporal_review_flags,
                            )
                            writer.write(base.compact_json(candidate) + "\n")
                            counts["match_candidate_rows"] += 1
                            counts["ambiguous_full_name_match_candidate_rows"] += int(ambiguous)
    os.replace(temporary, output_path)
    receipt = {
        "counts": {
            **dict(sorted(counts.items())),
            "distinct_matched_lda_people": len(matched_lda_ids),
            "distinct_matched_payroll_candidates": len(matched_payroll_ids),
            "lda_input_people": len(people),
            "lda_normalized_full_name_collision_keys": sum(len(value) > 1 for value in full_index.values()),
            "lda_normalized_first_last_collision_keys": sum(len(value) > 1 for value in first_last_index.values()),
        },
        "inputs": {
            "lda_people": {
                "bytes": args.people.stat().st_size,
                "path": str(args.people),
                "sha256": base.sha256_file(args.people),
            },
            "payroll_candidates": {
                "bytes": args.payroll.stat().st_size,
                "path": str(args.payroll),
                "sha256": base.sha256_file(args.payroll),
            },
        },
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": counts["match_candidate_rows"],
            "sha256": base.sha256_file(output_path),
        },
        "risk_notes": [
            "All outputs are unverified name-only candidates; no match is a canonical identity or employment episode.",
            "Exact full-name normalization can still join different people who share the same name; collisions are retained and flagged.",
            "Unique-in-this-LDA-roster first/last matching is a recall aid, not proof of identity, and omits ambiguous first/last keys.",
            "House PDF payees can contain ditto marks, dates, OCR replacement characters, vendors, or accounting text; unusable shapes remain counted and unmatched.",
            "Service dates remain payment-coverage candidates and are not promoted to complete employment tenure.",
            "Official House service ranges can predate the report accounting period (for example retroactive or other compensation); every retained pre-period range is explicitly review-flagged.",
            "Reversed service ranges and ranges extending after the report period are fail-closed and not emitted.",
        ],
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS",
        "validation": {
            "canonical_employment_episode_promotions": 0,
            "canonical_identity_promotions": 0,
            "canonical_service_date_promotions": 0,
            "payroll_input_order_preserved": True,
        },
    }
    base.write_json_atomic(receipt_path, receipt)
    return {"receipt": receipt, "receipt_path": str(receipt_path), "receipt_sha256": base.sha256_file(receipt_path)}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payroll", type=Path, default=DEFAULT_PAYROLL)
    parser.add_argument("--people", type=Path, default=DEFAULT_PEOPLE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args(argv)
    args.payroll = args.payroll.resolve()
    args.people = args.people.resolve()
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    print(base.compact_json(run(args)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
