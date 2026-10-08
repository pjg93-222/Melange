#!/usr/bin/env python3
"""Verify deterministic, non-canonical House SOD/LDA match candidates.

The verifier compares independent matcher generations byte-for-byte and checks
candidate invariants against the separately produced House payroll receipt and
historical source inventory.  It never adjudicates an identity.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA_ID = "staffer-network-house-sod-pdf-lda-name-match-verification-v2"
CANDIDATE_SCHEMA_ID = "staffer-network-house-sod-pdf-lda-name-match-candidate-v2"
MATCH_RECEIPT_SCHEMA_ID = "staffer-network-house-sod-pdf-lda-name-match-receipt-v2"
GAP_STATUS = "GAP_FULL_REPORT_NOT_AVAILABLE_IN_VERIFIED_OFFICIAL_DIGITAL_FORM"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def expected_periods(first_year: int, first_quarter: int, last_year: int, last_quarter: int) -> list[str]:
    periods = []
    year, quarter = first_year, first_quarter
    while (year, quarter) <= (last_year, last_quarter):
        periods.append(f"{year}Q{quarter}")
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1
    return periods


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def payroll_output(receipt: dict[str, Any]) -> dict[str, Any]:
    """Return the candidate payload descriptor from either payroll receipt version."""
    if "output" in receipt:
        return receipt["output"]
    for row in receipt.get("files", []):
        if row.get("path") == "house_sod_payroll_pdf_candidates.ndjson.gz":
            return row
    raise KeyError("payroll candidate output is not declared in the receipt")


def verify(args: argparse.Namespace) -> dict[str, Any]:
    primary_payload = args.primary / "house_sod_pdf_lda_name_match_candidates.ndjson.gz"
    twin_payload = args.twin / "house_sod_pdf_lda_name_match_candidates.ndjson.gz"
    primary_receipt_path = args.primary / "house_sod_pdf_lda_name_match_receipt.json"
    twin_receipt_path = args.twin / "house_sod_pdf_lda_name_match_receipt.json"

    primary_receipt = load_json(primary_receipt_path)
    twin_receipt = load_json(twin_receipt_path)
    payroll_receipt = load_json(args.payroll_receipt)
    inventory = load_json(args.historical_inventory)
    payroll_output_row = payroll_output(payroll_receipt)
    payroll_payload = args.payroll_receipt.parent / payroll_output_row["path"]

    expected_web_periods = expected_periods(2009, 3, 2015, 4)
    expected_gap_periods = expected_periods(1996, 1, 2008, 4)
    source_periods = payroll_receipt.get("selected_periods") or [
        row["period"] for row in payroll_receipt["periods"]
    ]
    inventory_web_periods = inventory["coverage"]["house_pdf_periods"]
    inventory_gap_periods = inventory["coverage"]["pre_web_gap_periods"]

    assertions: dict[str, bool] = {
        "candidate_payload_bytes_equal": primary_payload.read_bytes() == twin_payload.read_bytes(),
        "candidate_payload_sha256_equal": sha256_file(primary_payload) == sha256_file(twin_payload),
        # Independent runs bind their own absolute input path, so compare the
        # deterministic substantive results rather than raw receipt bytes.
        "match_receipt_substantive_results_equal": (
            primary_receipt.get("schema_id") == twin_receipt.get("schema_id")
            and primary_receipt.get("status") == twin_receipt.get("status")
            and primary_receipt.get("counts") == twin_receipt.get("counts")
            and primary_receipt.get("output") == twin_receipt.get("output")
            and primary_receipt.get("validation") == twin_receipt.get("validation")
        ),
        "match_receipt_schema_valid": primary_receipt.get("schema_id") == MATCH_RECEIPT_SCHEMA_ID,
        "match_receipt_status_pass": primary_receipt.get("status") == "PASS",
        "payroll_source_payload_hash_bound": (
            primary_receipt["inputs"]["payroll_candidates"]["sha256"]
            == payroll_output_row["sha256"]
            == sha256_file(payroll_payload)
        ),
        "payroll_source_row_count_bound": (
            primary_receipt["counts"]["payroll_input_rows"]
            == payroll_output_row["rows"]
        ),
        "source_periods_exact_2009q3_through_2015q4": source_periods == expected_web_periods,
        "inventory_web_periods_exact_2009q3_through_2015q4": inventory_web_periods == expected_web_periods,
        "inventory_gap_periods_exact_1996q1_through_2008q4": inventory_gap_periods == expected_gap_periods,
        "inventory_gap_count_is_52": len(inventory_gap_periods) == 52,
        "inventory_has_no_verified_pre_web_full_reports": (
            inventory["coverage"]["pre_web_full_report_digital_period_count"] == 0
        ),
        "historical_inventory_hash_bound": (
            sha256_file(args.historical_inventory)
            == (payroll_receipt.get("source_inventory") or payroll_receipt["historical_inventory"])["sha256"]
        ),
    }

    counts = Counter()
    candidate_ids: set[str] = set()
    payroll_ids: set[str] = set()
    lda_ids: set[str] = set()
    matched_periods: set[str] = set()
    canonical_violation_rows = 0
    temporal_violation_rows = 0
    source_binding_violation_rows = 0
    schema_violation_rows = 0
    duplicate_candidate_id_rows = 0

    period_source_hash = {row["period"]: row["pdf_sha256"] for row in payroll_receipt["periods"]}
    period_source_url = {
        row["period"]: row["pdf_url"] for row in inventory["house_pdf_periods"]
    }

    source_temporal_counts = Counter()
    with gzip.open(payroll_payload, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            start = row.get("service_start_date_candidate_iso")
            end = row.get("service_end_date_candidate_iso")
            period_start = row["period_start"]
            period_end = row["period_end"]
            if start is None or end is None:
                source_temporal_counts["unparsed"] += 1
            elif start > end:
                source_temporal_counts["reversed"] += 1
            elif start > period_end or end > period_end:
                source_temporal_counts["future"] += 1
            elif start < period_start:
                source_temporal_counts["pre_report"] += 1
            else:
                source_temporal_counts["within_report"] += 1

    with gzip.open(primary_payload, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            counts["candidate_rows"] += 1
            candidate_id = row.get("candidate_match_id")
            if candidate_id in candidate_ids:
                duplicate_candidate_id_rows += 1
            candidate_ids.add(candidate_id)
            payroll_ids.add(row.get("payroll_candidate_id"))
            lda_ids.add(row.get("lda_source_person_id"))
            period = row.get("period")
            matched_periods.add(period)

            if row.get("schema_id") != CANDIDATE_SCHEMA_ID:
                schema_violation_rows += 1
            if not (
                row.get("canonical_identity_decision") == "NOT_ADJUDICATED"
                and row.get("canonical_person_id") is None
                and row.get("canonical_employment_episode_id") is None
                and row.get("identity_verification_status") == "UNVERIFIED_CANDIDATE"
                and row.get("corroboration_status") == "UNVERIFIED_NAME_ONLY_CANDIDATE"
            ):
                canonical_violation_rows += 1

            start = row.get("service_start_date_candidate_iso")
            end = row.get("service_end_date_candidate_iso")
            period_start = row.get("period_start")
            period_end = row.get("period_end")
            review_flags = set(row.get("match_review_flags", []))
            if end < period_start:
                expected_relationship = "ENTIRE_SERVICE_RANGE_BEFORE_REPORT_PERIOD"
                expected_temporal_flags = {
                    "SERVICE_RANGE_BEGINS_BEFORE_REPORT_PERIOD_REVIEW_REQUIRED",
                    "SERVICE_RANGE_ENDS_BEFORE_REPORT_PERIOD_REVIEW_REQUIRED",
                }
            elif start < period_start:
                expected_relationship = "SERVICE_RANGE_BEGINS_BEFORE_REPORT_PERIOD"
                expected_temporal_flags = {
                    "SERVICE_RANGE_BEGINS_BEFORE_REPORT_PERIOD_REVIEW_REQUIRED"
                }
            else:
                expected_relationship = "SERVICE_RANGE_WITHIN_REPORT_PERIOD"
                expected_temporal_flags = set()
            observed_temporal_flags = {
                flag for flag in review_flags if flag.startswith("SERVICE_RANGE_")
            }
            if not (
                period in expected_web_periods
                and period_start <= period_end
                and start is not None
                and end is not None
                and start <= end <= period_end
                and row.get("service_date_report_period_relationship") == expected_relationship
                and observed_temporal_flags == expected_temporal_flags
            ):
                temporal_violation_rows += 1

            if not (
                row.get("source_pdf_sha256") == period_source_hash.get(period)
                and row.get("source_url") == period_source_url.get(period)
            ):
                source_binding_violation_rows += 1

    gap_rows = inventory.get("pre_web_periods", [])
    assertions.update(
        {
            "candidate_row_count_matches_receipt": (
                counts["candidate_rows"] == primary_receipt["output"]["rows"]
            ),
            "candidate_payload_hash_matches_receipt": (
                sha256_file(primary_payload) == primary_receipt["output"]["sha256"]
            ),
            "distinct_payroll_count_matches_receipt": (
                len(payroll_ids) == primary_receipt["counts"]["distinct_matched_payroll_candidates"]
            ),
            "distinct_lda_count_matches_receipt": (
                len(lda_ids) == primary_receipt["counts"]["distinct_matched_lda_people"]
            ),
            "all_26_web_periods_have_candidates": sorted(matched_periods) == expected_web_periods,
            "candidate_ids_unique": duplicate_candidate_id_rows == 0,
            "candidate_schemas_valid": schema_violation_rows == 0,
            "zero_canonical_promotion_violations": canonical_violation_rows == 0,
            "zero_temporal_bound_violations": temporal_violation_rows == 0,
            "source_reversed_ranges_fail_closed": (
                primary_receipt["counts"].get("reversed_service_range_rows_not_emitted", 0)
                == source_temporal_counts["reversed"]
            ),
            "source_future_ranges_fail_closed": (
                primary_receipt["counts"].get("future_service_range_rows_not_emitted", 0)
                == source_temporal_counts["future"]
            ),
            "source_pre_report_ranges_explicitly_dispositioned": (
                primary_receipt["counts"].get(
                    "pre_report_service_range_rows_retained_with_review_flag", 0
                )
                == source_temporal_counts["pre_report"]
            ),
            "zero_source_binding_violations": source_binding_violation_rows == 0,
            "all_pre_web_inventory_rows_are_explicit_gaps": (
                len(gap_rows) == 52
                and [row["period"] for row in gap_rows] == expected_gap_periods
                and all(row.get("digital_report_url") is None for row in gap_rows)
                and all(row.get("payroll_extraction_status") == GAP_STATUS for row in gap_rows)
            ),
        }
    )

    failures = sorted(name for name, passed in assertions.items() if not passed)
    result = {
        "assertions": dict(sorted(assertions.items())),
        "counts": {
            "candidate_rows": counts["candidate_rows"],
            "distinct_candidate_ids": len(candidate_ids),
            "distinct_matched_lda_people": len(lda_ids),
            "distinct_matched_payroll_candidates": len(payroll_ids),
            "duplicate_candidate_id_rows": duplicate_candidate_id_rows,
            "matched_web_periods": len(matched_periods),
            "pre_web_evidence_gap_periods": len(inventory_gap_periods),
            "schema_violation_rows": schema_violation_rows,
            "canonical_promotion_violation_rows": canonical_violation_rows,
            "source_binding_violation_rows": source_binding_violation_rows,
            "temporal_bound_violation_rows": temporal_violation_rows,
            "source_future_service_range_rows": source_temporal_counts["future"],
            "source_pre_report_service_range_rows": source_temporal_counts["pre_report"],
            "source_reversed_service_range_rows": source_temporal_counts["reversed"],
            "source_within_report_service_range_rows": source_temporal_counts["within_report"],
        },
        "failure_codes": failures,
        "gaps": {
            "period_end": "2008Q4",
            "period_start": "1996Q1",
            "periods": inventory_gap_periods,
            "reason": GAP_STATUS,
            "verified_full_report_digital_periods": 0,
        },
        "inputs": {
            "historical_inventory_sha256": sha256_file(args.historical_inventory),
            "payroll_receipt_sha256": sha256_file(args.payroll_receipt),
            "primary_payload_sha256": sha256_file(primary_payload),
            "primary_receipt_sha256": sha256_file(primary_receipt_path),
            "twin_payload_sha256": sha256_file(twin_payload),
            "twin_receipt_sha256": sha256_file(twin_receipt_path),
        },
        "promotion_policy": {
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "candidate_disposition": "REVIEW_REQUIRED_NOT_ADJUDICATED",
        },
        "schema_id": SCHEMA_ID,
        "status": "PASS" if not failures else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--twin", type=Path, required=True)
    parser.add_argument("--payroll-receipt", type=Path, required=True)
    parser.add_argument("--historical-inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.primary = args.primary.resolve()
    args.twin = args.twin.resolve()
    args.payroll_receipt = args.payroll_receipt.resolve()
    args.historical_inventory = args.historical_inventory.resolve()
    args.output = args.output.resolve()
    result = verify(args)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
