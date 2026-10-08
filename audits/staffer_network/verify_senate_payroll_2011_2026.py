#!/usr/bin/env python3
"""Independently verify Senate archive, scope-filter twin, and LDA-match twin."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def expected_periods() -> list[tuple[str, str]]:
    start = dt.date(2011, 4, 1)
    values = []
    while start <= dt.date(2025, 10, 1):
        if start.month == 4:
            end = dt.date(start.year, 9, 30)
            next_start = dt.date(start.year, 10, 1)
        else:
            end = dt.date(start.year + 1, 3, 31)
            next_start = dt.date(start.year + 1, 4, 1)
        values.append((start.isoformat(), end.isoformat()))
        start = next_start
    return values


def artifact_ok(root: Path, value: dict[str, Any]) -> bool:
    path = root / value["path"]
    return path.stat().st_size == value["bytes"] and sha256_file(path) == value["sha256"]


def verify(args: argparse.Namespace) -> dict[str, Any]:
    failures: list[str] = []
    parser_receipt = read_json(args.archive / "senate_payroll_full_archive_receipt.json")
    inventory = read_json(args.archive / "senate_report_archive_inventory.json")
    raw_path = args.archive / "senate_payroll_candidates_2011_2026.ndjson.gz"
    raw_twin_receipt = read_json(args.raw_twin / "senate_payroll_cache_assembly_receipt.json")
    raw_twin_path = args.raw_twin / raw_twin_receipt["output"]["path"]
    if parser_receipt.get("parser_version") != "senate-payroll-parser-v4":
        failures.append("PARSER_VERSION_NOT_V4")
    if parser_receipt.get("archive_reports_extracted") != 30:
        failures.append("ARCHIVE_REPORT_COUNT_NOT_30")
    if parser_receipt.get("archive_reports_remaining") != 0:
        failures.append("ARCHIVE_REPORTS_REMAIN")
    if not artifact_ok(args.archive, parser_receipt["candidate_file"]):
        failures.append("RAW_CANDIDATE_ARTIFACT_HASH_OR_SIZE_MISMATCH")
    if not artifact_ok(args.raw_twin, raw_twin_receipt["output"]):
        failures.append("RAW_TWIN_ARTIFACT_HASH_OR_SIZE_MISMATCH")
    if raw_path.read_bytes() != raw_twin_path.read_bytes():
        failures.append("RAW_ARCHIVE_TWIN_NOT_BYTE_IDENTICAL")
    inventory_periods = [(row["period_start"], row["period_end"]) for row in inventory["periods"]]
    if inventory_periods != expected_periods():
        failures.append("INVENTORY_PERIOD_SEQUENCE_MISMATCH")

    report_receipts = [
        json.loads(line)
        for line in (args.archive / "senate_report_extraction_receipts.ndjson").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(report_receipts) != 30 or len({row["package_id"] for row in report_receipts}) != 30:
        failures.append("REPORT_RECEIPT_CARDINALITY_MISMATCH")
    if any(row.get("parser_version") != "senate-payroll-parser-v4" for row in report_receipts):
        failures.append("REPORT_RECEIPT_VERSION_MISMATCH")
    for row in report_receipts:
        pdf = args.archive / "raw" / f"{row['package_id']}.pdf"
        if not pdf.exists() or pdf.stat().st_size != row["pdf_bytes"] or sha256_file(pdf) != row["pdf_sha256"]:
            failures.append(f"PDF_BINDING_MISMATCH:{row['package_id']}")

    raw_ids: set[str] = set()
    raw_count = 0
    for row in read_gzip(raw_path):
        raw_count += 1
        candidate_id = row["candidate_id"]
        if candidate_id in raw_ids:
            failures.append("RAW_DUPLICATE_CANDIDATE_ID")
            break
        raw_ids.add(candidate_id)
        if row.get("canonical_identity_decision") != "NOT_ADJUDICATED":
            failures.append("RAW_IDENTITY_GATE_WEAKENED")
            break
        if row.get("canonical_employment_decision") != "NOT_ADJUDICATED":
            failures.append("RAW_EMPLOYMENT_GATE_WEAKENED")
            break
        if row.get("date_promotion_eligible") is not False:
            failures.append("RAW_DATE_PROMOTION_GATE_WEAKENED")
            break
    if raw_count != parser_receipt["extraction"]["candidate_count"]:
        failures.append("RAW_COUNT_MISMATCH")

    filter_receipt_names = "senate_payroll_employment_scope_receipt.json"
    primary_filter_receipt = read_json(args.filter_primary / filter_receipt_names)
    twin_filter_receipt = read_json(args.filter_twin / filter_receipt_names)
    if primary_filter_receipt != twin_filter_receipt:
        failures.append("FILTER_RECEIPTS_DIFFER")
    for root, receipt in ((args.filter_primary, primary_filter_receipt), (args.filter_twin, twin_filter_receipt)):
        if receipt.get("status") != "PASS":
            failures.append("FILTER_RECEIPT_NOT_PASS")
        if not artifact_ok(root, receipt["accepted_candidates"]):
            failures.append("FILTER_ACCEPTED_ARTIFACT_MISMATCH")
        if not artifact_ok(root, receipt["rejections"]):
            failures.append("FILTER_REJECTION_ARTIFACT_MISMATCH")
    primary_accepted = args.filter_primary / primary_filter_receipt["accepted_candidates"]["path"]
    twin_accepted = args.filter_twin / twin_filter_receipt["accepted_candidates"]["path"]
    primary_rejected = args.filter_primary / primary_filter_receipt["rejections"]["path"]
    twin_rejected = args.filter_twin / twin_filter_receipt["rejections"]["path"]
    if primary_accepted.read_bytes() != twin_accepted.read_bytes():
        failures.append("FILTER_ACCEPTED_TWIN_NOT_BYTE_IDENTICAL")
    if primary_rejected.read_bytes() != twin_rejected.read_bytes():
        failures.append("FILTER_REJECTION_TWIN_NOT_BYTE_IDENTICAL")

    accepted_ids: set[str] = set()
    accepted_count = 0
    for row in read_gzip(primary_accepted):
        accepted_count += 1
        candidate_id = row["candidate_id"]
        if candidate_id in accepted_ids:
            failures.append("ACCEPTED_DUPLICATE_CANDIDATE_ID")
            break
        accepted_ids.add(candidate_id)
        if row.get("canonical_identity_decision") != "NOT_ADJUDICATED":
            failures.append("ACCEPTED_IDENTITY_GATE_WEAKENED")
            break
        if row.get("canonical_employment_decision") != "NOT_ADJUDICATED":
            failures.append("ACCEPTED_EMPLOYMENT_GATE_WEAKENED")
            break
        period_start, period_end = row["report_period_start"], row["report_period_end"]
        for interval in row.get("date_intervals") or []:
            if not period_start <= interval["start"] <= interval["end"] <= period_end:
                failures.append("ACCEPTED_INVALID_OR_OUT_OF_PERIOD_INTERVAL")
                break
    rejected_ids = {row["candidate_id"] for row in read_gzip(primary_rejected)}
    if accepted_ids & rejected_ids:
        failures.append("ACCEPTED_REJECTED_ID_OVERLAP")
    if accepted_ids | rejected_ids != raw_ids:
        failures.append("FILTER_GLOBAL_CONSERVATION_FAILED")
    if accepted_count != primary_filter_receipt["accepted_candidate_count"]:
        failures.append("FILTER_ACCEPTED_COUNT_MISMATCH")
    if len(rejected_ids) != primary_filter_receipt["rejected_candidate_count"]:
        failures.append("FILTER_REJECTED_COUNT_MISMATCH")

    matcher_receipt_name = "lda_senate_payroll_match_receipt.json"
    match_primary_receipt = read_json(args.match_primary / matcher_receipt_name)
    match_twin_receipt = read_json(args.match_twin / matcher_receipt_name)
    if match_primary_receipt != match_twin_receipt:
        failures.append("MATCH_RECEIPTS_DIFFER")
    match_primary_path = args.match_primary / match_primary_receipt["output"]["path"]
    match_twin_path = args.match_twin / match_twin_receipt["output"]["path"]
    if match_primary_path.read_bytes() != match_twin_path.read_bytes():
        failures.append("MATCH_TWIN_NOT_BYTE_IDENTICAL")
    if not artifact_ok(args.match_primary, match_primary_receipt["output"]):
        failures.append("MATCH_ARTIFACT_MISMATCH")
    match_count = 0
    matched_people: set[str] = set()
    match_ids: set[str] = set()
    for row in read_gzip(match_primary_path):
        match_count += 1
        if row["match_candidate_id"] in match_ids:
            failures.append("MATCH_DUPLICATE_ID")
            break
        match_ids.add(row["match_candidate_id"])
        matched_people.add(row["lda_source_person_id"])
        if row.get("candidate_status") != "REVIEW_REQUIRED":
            failures.append("MATCH_REVIEW_GATE_WEAKENED")
            break
        if row.get("canonical_identity_decision") != "NOT_ADJUDICATED":
            failures.append("MATCH_IDENTITY_GATE_WEAKENED")
            break
        if row.get("canonical_employment_fact") is not False:
            failures.append("MATCH_EMPLOYMENT_PROMOTION_DETECTED")
            break
        if row.get("interval_continuity_asserted") is not False:
            failures.append("MATCH_CONTINUITY_ASSERTED")
            break
        for interval in row.get("observed_report_intervals") or []:
            if not "2011-04-01" <= interval["start"] <= interval["end"] <= "2026-03-31":
                failures.append("MATCH_INTERVAL_OUT_OF_ARCHIVE_BOUNDS")
                break
    if match_count != match_primary_receipt["match_candidate_rows"]:
        failures.append("MATCH_COUNT_MISMATCH")
    if len(matched_people) != match_primary_receipt["matched_lda_source_people"]:
        failures.append("MATCHED_PEOPLE_COUNT_MISMATCH")
    if match_primary_receipt.get("queue_rows") != 25340:
        failures.append("LDA_QUEUE_COUNT_NOT_25340")

    return {
        "accepted_candidate_count": accepted_count,
        "archive_candidate_count": raw_count,
        "archive_period_count": len(inventory_periods),
        "archive_window": [inventory_periods[0][0], inventory_periods[-1][1]],
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "failures": failures,
        "filter_accepted_sha256": sha256_file(primary_accepted),
        "filter_rejected_sha256": sha256_file(primary_rejected),
        "global_conservation": len(accepted_ids | rejected_ids) == len(raw_ids),
        "match_candidate_count": match_count,
        "match_candidate_sha256": sha256_file(match_primary_path),
        "matched_lda_source_people": len(matched_people),
        "rejected_candidate_count": len(rejected_ids),
        "schema_id": "staffer-network-senate-payroll-independent-verification-receipt-v1",
        "status": "PASS" if not failures else "FAIL",
        "twin_byte_equality": {
            "accepted": primary_accepted.read_bytes() == twin_accepted.read_bytes(),
            "matches": match_primary_path.read_bytes() == match_twin_path.read_bytes(),
            "raw_archive": raw_path.read_bytes() == raw_twin_path.read_bytes(),
            "rejections": primary_rejected.read_bytes() == twin_rejected.read_bytes(),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--filter-primary", type=Path, required=True)
    parser.add_argument("--filter-twin", type=Path, required=True)
    parser.add_argument("--match-primary", type=Path, required=True)
    parser.add_argument("--match-twin", type=Path, required=True)
    parser.add_argument("--raw-twin", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    receipt = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
