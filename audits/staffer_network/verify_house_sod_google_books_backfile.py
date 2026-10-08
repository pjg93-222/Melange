#!/usr/bin/env python3
"""Independently verify House Google Books discovery, capture, and candidate twins."""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path
import re
import urllib.parse
from typing import Any


SCHEMA_ID = "staffer-network-house-sod-google-books-verification-v1"
TITLE_RE = re.compile(
    r"^Statement of Disbursements of the House: As Compiled by the Chief "
    r"Administrative Officer from (?P<start>January|April|July|October) 1, "
    r"(?P<year>\d{4}) to (?P<end>March|June|September|December) (?:30|31), "
    r"(?P=year), Part (?P<part>\d+)$"
)
QUARTER = {"January": 1, "April": 2, "July": 3, "October": 4}
END_MONTH = {1: "March", 2: "June", 3: "September", 4: "December"}
CAPTCHA_MARKER = b"To continue with your download, please type the characters you see below"


def compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_bytes(value: object) -> bytes:
    return (compact_json(value) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_periods() -> list[str]:
    return [f"{year}Q{quarter}" for year in range(1996, 2009) for quarter in range(1, 5)]


def title_period_part(title: str) -> tuple[str, int]:
    match = TITLE_RE.fullmatch(title)
    if match is None:
        raise AssertionError(f"invalid candidate title: {title!r}")
    quarter = QUARTER[match.group("start")]
    assert match.group("end") == END_MONTH[quarter]
    return f"{match.group('year')}Q{quarter}", int(match.group("part"))


def verify_discovery(path: Path) -> dict[str, Any]:
    value = load_json(path)
    expected = expected_periods()
    assert len(expected) == 52 and len(set(expected)) == 52
    assert value["expected_periods"] == expected
    receipt_hashes = []
    for receipt in value["search_receipts"]:
        source = path.parent / receipt["path"]
        assert source.stat().st_size == receipt["bytes"]
        digest = sha256_file(source)
        assert digest == receipt["sha256"]
        receipt_hashes.append({"bytes": receipt["bytes"], "path": receipt["path"], "sha256": digest})
    ids = set()
    covered = set()
    candidate_hashes = []
    for candidate in value["target_candidates"]:
        assert re.fullmatch(r"[A-Za-z0-9_-]{12}", candidate["book_id"])
        assert candidate["book_id"] not in ids
        ids.add(candidate["book_id"])
        period, part = title_period_part(candidate["title"])
        assert period == candidate["period"] and part == candidate["part"]
        assert urllib.parse.parse_qs(urllib.parse.urlparse(candidate["download_url_template"]).query)["id"] == [candidate["book_id"]]
        assert urllib.parse.parse_qs(urllib.parse.urlparse(candidate["metadata_url"]).query)["id"] == [candidate["book_id"]]
        covered.add(period)
        candidate_hashes.append(
            {
                "book_id": candidate["book_id"],
                "candidate_sha256": hashlib.sha256(canonical_bytes(candidate)).hexdigest(),
                "part": part,
                "period": period,
                "title": candidate["title"],
            }
        )
    missing = [period for period in expected if period not in covered]
    assert len(ids) == 23
    assert len(covered) == 12
    assert len(missing) == 40
    assert sorted(covered) == sorted(set(expected) - set(missing))
    assert value["missing_periods"] == missing
    assert value["counts"]["expected_periods"] == 52
    assert value["counts"]["target_book_candidates"] == 23
    assert value["counts"]["target_periods_with_candidates"] == 12
    assert value["counts"]["missing_periods"] == 40
    return {
        "bytes": path.stat().st_size,
        "candidate_hashes": sorted(candidate_hashes, key=lambda row: (row["period"], row["part"], row["book_id"])),
        "candidate_ids": sorted(ids),
        "covered_periods": sorted(covered),
        "missing_periods": missing,
        "path": str(path),
        "search_receipts": receipt_hashes,
        "sha256": sha256_file(path),
    }


def verify_acquisition(path: Path, authorized_ids: set[str]) -> dict[str, Any]:
    value = load_json(path)
    assert value["status"] == "BLOCKED_ACQUISITION_INCOMPLETE"
    assert value["acquisition_policy"] == {
        "authentication_used": False,
        "cache_clearing_used": False,
        "candidate_scope": "GENERATION2_EXACT_23_ONLY",
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "direct_download_attempts_per_candidate": 1,
        "minimum_request_interval_seconds": 2.0,
        "redirect_hops_manually_paced": True,
        "request_concurrency": 1,
    }
    captures = value["captures"]
    assert len(captures) == 23
    assert {row["book_id"] for row in captures} == authorized_ids
    assert len({row["body_path"] for row in captures}) == 23
    assert all((row.get("minimum_observed_inter_request_seconds") or 0) >= 2.0 for row in captures)
    body_checks = []
    pdf_count = 0
    captcha_count = 0
    for capture in captures:
        body_path = path.parent / capture["body_path"]
        body = body_path.read_bytes()
        magic = body.startswith(b"%PDF-")
        assert len(body) == capture["body_bytes"]
        assert hashlib.sha256(body).hexdigest() == capture["body_sha256"]
        assert magic == capture["pdf_magic_verified"]
        if magic:
            pdf_count += 1
            assert capture["content_type"].lower().startswith("application/pdf")
            assert capture["response_diagnostic"] == "DIRECT_PDF"
            assert capture["pdf_inspection"]["document_opened"]
            assert capture["pdf_inspection"]["pages"] == 1555
            assert capture["pdf_inspection"]["extracted_text_characters"] > 4_000_000
            assert capture["pdf_inspection"]["front_matter_title_verified"]
            assert capture["pdf_inspection"]["front_matter_period_verified"]
            assert capture["pdf_inspection"]["front_matter_part_verified"]
            assert capture["pdf_inspection"]["personnel_text_extractable"]
        else:
            assert capture["content_type"].lower().startswith("text/html")
            assert CAPTCHA_MARKER in body
            assert capture["response_diagnostic"] == "GOOGLE_BOOKS_CAPTCHA_REQUIRED"
            captcha_count += 1
        body_checks.append(
            {
                "body_bytes": len(body),
                "body_sha256": capture["body_sha256"],
                "book_id": capture["book_id"],
                "content_type": capture["content_type"],
                "pdf_magic_verified": magic,
                "response_diagnostic": capture["response_diagnostic"],
            }
        )
    assert pdf_count == 1 and captcha_count == 22
    assert value["counts"] == {
        "authorized_candidates": 23,
        "captcha_html_responses": 22,
        "covered_periods": 12,
        "direct_pdf_responses": 1,
        "expected_periods": 52,
        "missing_periods": 40,
        "personnel_text_extractable_pdfs": 1,
    }
    assert value["validation"]["canonical_promotions"] == 0
    assert value["validation"]["exact_52_quarter_accounting"]
    assert value["validation"]["zero_scope_expansion"]
    return {
        "body_checks": sorted(body_checks, key=lambda row: row["book_id"]),
        "bytes": path.stat().st_size,
        "captcha_html_responses": captcha_count,
        "direct_pdf_responses": pdf_count,
        "minimum_observed_inter_request_seconds": min(row["minimum_observed_inter_request_seconds"] for row in captures),
        "path": str(path),
        "sha256": sha256_file(path),
        "total_http_requests_including_redirect_hops": sum(row["request_count"] for row in captures),
    }


def expected_candidate_id(row: dict[str, Any]) -> str:
    seed = "\0".join(
        [
            row["source_pdf_sha256"],
            str(row["source_pdf_page_number"]),
            str(row["source_pdf_row_y_milli"]),
            row["payee_raw"],
            row["service_start_date_raw"],
            row["service_end_date_raw"],
            row["title_description_raw"],
            row["amount_raw"],
        ]
    ).encode("utf-8")
    return "house-sod-google-books-personnel:" + hashlib.sha256(seed).hexdigest()


def read_candidate_generation(directory: Path) -> tuple[bytes, bytes, dict[str, Any], list[dict[str, Any]]]:
    ledger_path = directory / "house_sod_google_books_personnel_candidates.ndjson.gz"
    receipt_path = directory / "house_sod_google_books_personnel_receipt.json"
    ledger_bytes = ledger_path.read_bytes()
    receipt_bytes = receipt_path.read_bytes()
    receipt = json.loads(receipt_bytes)
    with gzip.open(ledger_path, "rt", encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    assert receipt["status"] == "PASS"
    assert receipt["output"] == {
        "bytes": len(ledger_bytes),
        "path": ledger_path.name,
        "rows": len(rows),
        "sha256": hashlib.sha256(ledger_bytes).hexdigest(),
    }
    assert receipt["validation"] == {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "canonical_office_promotions": 0,
        "canonical_service_date_promotions": 0,
    }
    return ledger_bytes, receipt_bytes, receipt, rows


def verify_candidate_twins(first: Path, second: Path) -> dict[str, Any]:
    ledger_a, receipt_a, parsed_receipt, rows = read_candidate_generation(first)
    ledger_b, receipt_b, _, rows_b = read_candidate_generation(second)
    assert ledger_a == ledger_b
    assert receipt_a == receipt_b
    assert rows == rows_b
    assert len(rows) == 4939
    ids = set()
    prior_key = None
    for row in rows:
        assert row["candidate_id"] == expected_candidate_id(row)
        assert row["candidate_id"] not in ids
        ids.add(row["candidate_id"])
        assert row["schema_id"] == "staffer-network-house-sod-google-books-personnel-candidate-v1"
        assert row["candidate_status"] == "UNVERIFIED_PUBLIC_SCAN_PERSONNEL_ROW"
        assert row["book_id"] == "vfE2RJJsCaAC"
        assert row["period"] == "1997Q1" and row["part"] == 2
        assert row["period_start"] == "1997-01-01" and row["period_end"] == "1997-03-31"
        start = dt.date.fromisoformat(row["service_start_date_candidate_iso"])
        end = dt.date.fromisoformat(row["service_end_date_candidate_iso"])
        assert dt.date(1997, 1, 1) <= start <= end <= dt.date(1997, 3, 31)
        assert row["temporal_validation"] == "WITHIN_REPORT_QUARTER"
        assert re.search(r"[A-Za-z]", row["payee_raw"])
        assert re.search(r"[A-Za-z]", row["title_description_raw"])
        assert re.fullmatch(r"-?\(?[\d,]+\.\d{2}\)?", row["amount_raw"])
        for field in (
            "canonical_employing_office_id",
            "canonical_employment_episode_id",
            "canonical_person_id",
            "canonical_service_end_date",
            "canonical_service_start_date",
        ):
            assert row[field] is None
        assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
        key = (row["period"], row["part"], row["source_pdf_page_number"], row["source_pdf_row_y_milli"], row["candidate_id"])
        assert prior_key is None or key >= prior_key
        prior_key = key
    return {
        "candidate_rows": len(rows),
        "ledger_bytes": len(ledger_a),
        "ledger_sha256": hashlib.sha256(ledger_a).hexdigest(),
        "receipt_bytes": len(receipt_a),
        "receipt_sha256": hashlib.sha256(receipt_a).hexdigest(),
        "source_book_id": parsed_receipt["sources"][0]["book_id"],
        "source_period": parsed_receipt["sources"][0]["period"],
        "twin_byte_identical": True,
        "unique_candidate_ids": len(ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation1-discovery", type=Path, required=True)
    parser.add_argument("--generation2-discovery", type=Path, required=True)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--candidate-generation1", type=Path, required=True)
    parser.add_argument("--candidate-generation2", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    discovery1 = verify_discovery(args.generation1_discovery.resolve())
    discovery2 = verify_discovery(args.generation2_discovery.resolve())
    common = set(discovery1["candidate_ids"]) & set(discovery2["candidate_ids"])
    only1 = sorted(set(discovery1["candidate_ids"]) - set(discovery2["candidate_ids"]))
    only2 = sorted(set(discovery2["candidate_ids"]) - set(discovery1["candidate_ids"]))
    assert len(common) == 22
    assert only1 == ["OPokXmFXyeAC"]
    assert only2 == ["vfE2RJJsCaAC"]
    assert discovery1["covered_periods"] == discovery2["covered_periods"]
    assert discovery1["missing_periods"] == discovery2["missing_periods"]
    acquisition = verify_acquisition(args.acquisition_manifest.resolve(), set(discovery2["candidate_ids"]))
    twins = verify_candidate_twins(args.candidate_generation1.resolve(), args.candidate_generation2.resolve())
    result = {
        "acquisition": acquisition,
        "acquisition_state": "BLOCKED",
        "audit_status": "PASS",
        "blockers": [
            "22_OF_23_AUTHORIZED_GOOGLE_BOOKS_DOWNLOAD_RESPONSES_REQUIRE_CAPTCHA",
            "40_OF_52_TARGET_QUARTERS_HAVE_NO_DISCOVERED_CANDIDATE",
            "ONLY_1997Q1_PART2_WAS_DIRECTLY_ACQUIRED_AND_EXTRACTABLE",
        ],
        "candidate_twins": twins,
        "canonical_promotions": 0,
        "discovery_comparison": {
            "common_candidate_ids": sorted(common),
            "common_candidate_ids_count": len(common),
            "generation1_only_candidate_ids": only1,
            "generation2_only_candidate_ids": only2,
        },
        "discovery_generation1": discovery1,
        "discovery_generation2": discovery2,
        "exact_accounting": {
            "covered_periods": discovery2["covered_periods"],
            "covered_periods_count": 12,
            "expected_periods_count": 52,
            "missing_periods": discovery2["missing_periods"],
            "missing_periods_count": 40,
        },
        "implementation": {
            "acquisition_script_sha256": sha256_file(Path(__file__).with_name("audit_house_sod_google_books_backfile.py")),
            "extraction_script_sha256": sha256_file(Path(__file__).with_name("extract_house_sod_google_books_personnel.py")),
            "test_script_sha256": sha256_file(Path(__file__).with_name("test_extract_house_sod_google_books_personnel.py")),
            "verifier_script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "schema_id": SCHEMA_ID,
        "scope": {
            "authorized_candidate_ids": 23,
            "candidate_source_books": 1,
            "candidate_source_periods": 1,
            "canonical_promotions": 0,
            "network_requests_added_by_verification": 0,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_bytes(result))
    print(compact_json({"acquisition_state": "BLOCKED", "audit_status": "PASS", "candidate_rows": twins["candidate_rows"], "output": str(args.output), "output_sha256": sha256_file(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
