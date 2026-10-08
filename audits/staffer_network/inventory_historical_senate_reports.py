#!/usr/bin/env python3
"""Inventory the pre-online Senate report bridge and specify extraction adapters.

The official Senate index begins with the period 2011-04-01..2011-09-30.
This inventory therefore evaluates the contiguous bridge from 1995-10-01
(the report ending in calendar 1996) through 2011-03-31 against GovInfo's
Congressional Documents/GPO search.  Missing online renditions stay explicit;
the script never treats an expected printed report as an acquired source.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
import urllib.request


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "official_senate_reports_1996_2010_inventory"
SEARCH_ENDPOINT = "https://api.govinfo.gov/search"
SEARCH_QUERY = 'collection:(CDOC) AND title:("Report of the Secretary of the Senate")'
INVENTORY_SCHEMA_ID = "staffer-network-historical-senate-report-inventory-v1"
ADAPTER_SCHEMA_ID = "staffer-network-historical-senate-report-adapter-spec-v1"
RECEIPT_SCHEMA_ID = "staffer-network-historical-senate-report-inventory-receipt-v1"
PERIOD_RE = re.compile(
    r"(?:FROM\s+)?"
    r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+"
    r"(\d{1,2}),?\s+(19\d{2}|20\d{2})\s+(?:TO|THROUGH|-)\s+"
    r"(JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+"
    r"(\d{1,2}),?\s+(19\d{2}|20\d{2})",
    re.IGNORECASE,
)
PUBLIC_INDEXED_GPO_CATALOG_LEADS = [
    {
        "google_books_id": "0gdKnQEACAAJ",
        "period_end": "2010-03-31",
        "period_start": "2009-10-01",
        "publisher": "U.S. Government Printing Office",
        "senate_document": "111-12",
        "title": "Report of the Secretary of the Senate from October 1, 2009 to March 31, 2010",
        "url": "https://books.google.com/books?id=0gdKnQEACAAJ",
    },
    {
        "google_books_id": "OyqMAQAACAAJ",
        "period_end": "2004-09-30",
        "period_start": "2004-04-01",
        "publisher": "U.S. Government Printing Office",
        "senate_document": "108-18",
        "title": "Report of the Secretary of the Senate from April 1, 2004 to September 30, 2004",
        "url": "https://books.google.com/books?id=OyqMAQAACAAJ",
    },
    {
        "google_books_id": "74ok0gEACAAJ",
        "period_end": "1998-03-31",
        "period_start": "1997-10-01",
        "publisher": "U.S. Government Printing Office",
        "senate_document": "105-21",
        "title": "Report of the Secretary of the Senate from October 1, 1997 to March 31, 1998",
        "url": "https://books.google.com/books?id=74ok0gEACAAJ",
    },
]
UNMAPPED_PUBLIC_INDEXED_GPO_CATALOG_LEADS = [
    {
        "google_books_id": "thuQxwEACAAJ",
        "publisher_or_date": "2009",
        "senate_document": "110-11 Part I",
        "url": "https://books.google.com/books?id=thuQxwEACAAJ",
    },
    {
        "google_books_id": "166qxwEACAAJ",
        "publisher_or_date": "2009",
        "senate_document": "110-11 Part II",
        "url": "https://books.google.com/books?id=166qxwEACAAJ",
    },
    {
        "google_books_id": "FIgjywAACAAJ",
        "publisher_or_date": "U.S. Government Printing Office, 1996",
        "senate_document": "104-16 (period not stated in indexed title)",
        "url": "https://books.google.com/books?id=FIgjywAACAAJ",
    },
]


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: Any) -> None:
    write_bytes_atomic(path, (compact_json(value) + "\n").encode("utf-8"))


def artifact(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "path": path.name, "sha256": sha256_file(path)}


def expected_periods() -> list[dict[str, Any]]:
    current = dt.date(1995, 10, 1)
    final = dt.date(2010, 10, 1)
    rows: list[dict[str, Any]] = []
    while current <= final:
        if current.month == 10:
            end = dt.date(current.year + 1, 3, 31)
            next_start = dt.date(current.year + 1, 4, 1)
        else:
            end = dt.date(current.year, 9, 30)
            next_start = dt.date(current.year, 10, 1)
        rows.append({
            "calendar_year_label": end.year if current.month == 10 else current.year,
            "period_end": end.isoformat(),
            "period_start": current.isoformat(),
        })
        current = next_start
    return rows


def fetch_search_response(api_key: str, minimum_interval_seconds: float) -> tuple[bytes, bytes]:
    body = compact_json({
        "offsetMark": "*",
        "pageSize": "1000",
        "query": SEARCH_QUERY,
        "sorts": [{"field": "publishdate", "sortOrder": "ASC"}],
    }).encode("utf-8")
    if minimum_interval_seconds > 0:
        time.sleep(minimum_interval_seconds)
    request = urllib.request.Request(
        SEARCH_ENDPOINT,
        data=body,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "MelangeSystemsHistoricalSenate/1.0",
            "X-Api-Key": api_key,
        },
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return body, response.read()


def parse_title_period(title: str) -> tuple[str, str] | None:
    match = PERIOD_RE.search(title)
    if match is None:
        return None
    start = dt.datetime.strptime(
        f"{match.group(1)} {match.group(2)} {match.group(3)}", "%B %d %Y"
    ).date()
    end = dt.datetime.strptime(
        f"{match.group(4)} {match.group(5)} {match.group(6)}", "%B %d %Y"
    ).date()
    return start.isoformat(), end.isoformat()


def normalize_matches(search: dict[str, Any]) -> tuple[dict[tuple[str, str], list[dict[str, Any]]], list[dict[str, Any]]]:
    by_period: dict[tuple[str, str], list[dict[str, Any]]] = {}
    unmapped: list[dict[str, Any]] = []
    seen: set[tuple[str, str | None]] = set()
    for result in search.get("results") or []:
        title = result.get("title") or ""
        if "REPORT OF THE SECRETARY OF THE SENATE" not in title.upper():
            continue
        key = (result.get("packageId") or "", result.get("granuleId"))
        if key in seen:
            continue
        seen.add(key)
        download = result.get("download") or {}
        row = {
            "collection_code": result.get("collectionCode"),
            "date_issued": result.get("dateIssued"),
            "details_url": (
                "https://www.govinfo.gov/app/details/" + key[0]
                + (("/" + key[1]) if key[1] else "")
            ),
            "granule_id": key[1],
            "package_id": key[0],
            "pdf_api_url": download.get("pdfLink"),
            "text_api_url": download.get("txtLink"),
            "title": title,
        }
        bounds = parse_title_period(title)
        if bounds is None:
            unmapped.append(row)
        else:
            by_period.setdefault(bounds, []).append(row)
    for rows in by_period.values():
        rows.sort(key=lambda row: (row["package_id"], row.get("granule_id") or ""))
    unmapped.sort(key=lambda row: (row["package_id"], row.get("granule_id") or ""))
    return by_period, unmapped


def adapter_spec() -> dict[str, Any]:
    return {
        "accepted_inputs": [
            {
                "adapter": "GOVINFO_CDOC_TEXT",
                "priority": 1,
                "requirements": ["official package/granule metadata", "period stated in title or cover", "text rendition"],
            },
            {
                "adapter": "GOVINFO_OR_GPO_PDF_TEXT_LAYER",
                "priority": 2,
                "requirements": ["official PDF", "SHA-256 fixity", "minimum text-density probe passes"],
            },
            {
                "adapter": "GPO_SCAN_OCR",
                "priority": 3,
                "requirements": ["official/catalog-bound scan", "page images", "OCR engine/version receipt"],
            },
            {
                "adapter": "CATALOG_LEAD_ONLY",
                "priority": 4,
                "requirements": ["bibliographic record without downloadable official rendition"],
            },
        ],
        "date_rules": {
            "default_interval": "report period only",
            "row_qualifiers": ["FROM MON. DD", "TO MON. DD", "FROM MON. DD TO MON. DD", "TO MON. DD AND FROM MON. DD"],
            "split_interval_rule": "TO-then-FROM produces two observations; never bridge the intervening gap",
        },
        "extraction_stages": [
            "Bind catalog/package URL, local bytes, SHA-256, and report-period dates.",
            "Probe page count, rotation, embedded-text density, and representative payroll pages.",
            "Use direct text extraction when the text layer passes; otherwise render pages and OCR with versioned settings.",
            "Locate office/account headers before interpreting comma-form payee rows ending in a currency amount.",
            "Preserve raw line, raw payee/title split, page, office, amount, and date qualifiers.",
            "Emit UNSPLIT_REVIEW_REQUIRED for ambiguous OCR or name/title boundaries.",
        ],
        "identity_and_promotion_gates": {
            "canonical_employment_decision": "NOT_ADJUDICATED",
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "completeness_status": "PARTIAL",
            "date_promotion_eligible": False,
            "identity_status": "UNVERIFIED_CANDIDATE",
        },
        "quality_receipts": [
            "input URL/bytes/SHA-256", "page count and pages parsed", "embedded-text versus OCR route",
            "candidate/office/parse-status counts", "unique deterministic IDs", "byte-identical exact-input rerun",
        ],
        "schema_id": ADAPTER_SCHEMA_ID,
    }


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    if args.source_response:
        response_bytes = args.source_response.read_bytes()
        body = compact_json({
            "offsetMark": "*", "pageSize": "1000", "query": SEARCH_QUERY,
            "sorts": [{"field": "publishdate", "sortOrder": "ASC"}],
        }).encode("utf-8")
    else:
        body, response_bytes = fetch_search_response(args.api_key, args.minimum_interval_seconds)
    response_path = raw_dir / "govinfo_search_response.json"
    write_bytes_atomic(response_path, response_bytes)
    search = json.loads(response_bytes)
    matches, unmapped = normalize_matches(search)

    periods: list[dict[str, Any]] = []
    leads_by_period = {
        (row["period_start"], row["period_end"]): [row]
        for row in PUBLIC_INDEXED_GPO_CATALOG_LEADS
    }
    for expected in expected_periods():
        key = (expected["period_start"], expected["period_end"])
        sources = matches.get(key, [])
        online = [row for row in sources if row.get("pdf_api_url") or row.get("text_api_url")]
        catalog_leads = leads_by_period.get(key, [])
        periods.append({
            **expected,
            "catalog_leads": catalog_leads,
            "coverage_status": (
                "OFFICIAL_ONLINE_SOURCE_LOCATED" if online
                else "PUBLIC_INDEXED_GPO_CATALOG_LEAD_ONLY" if catalog_leads
                else "UNRESOLVED_OFFICIAL_ONLINE_SOURCE"
            ),
            "govinfo_matches": sources,
            "senate_online_archive_listed": False,
        })
    resolved = [row for row in periods if row["coverage_status"] == "OFFICIAL_ONLINE_SOURCE_LOCATED"]
    gaps = [
        {
            "period_end": row["period_end"],
            "period_start": row["period_start"],
            "reason": "No official online PDF/text rendition located in the frozen Senate/GovInfo inventory.",
        }
        for row in periods if row["coverage_status"] != "OFFICIAL_ONLINE_SOURCE_LOCATED"
    ]
    inventory = {
        "coverage": {
            "first_period_start": periods[0]["period_start"],
            "last_period_end": periods[-1]["period_end"],
            "official_online_periods_located": len(resolved),
            "public_indexed_gpo_catalog_lead_periods": sum(bool(row["catalog_leads"]) for row in periods),
            "residual_gap_count": len(gaps),
            "target_period_count": len(periods),
        },
        "discovery_scope": {
            "govinfo_collection": "Congressional Documents (including GPO-CDOC renditions)",
            "query": SEARCH_QUERY,
            "senate_modern_archive_boundary": "2011-04-01",
        },
        "periods": periods,
        "public_indexed_gpo_catalog_leads": PUBLIC_INDEXED_GPO_CATALOG_LEADS,
        "residual_gaps": gaps,
        "schema_id": INVENTORY_SCHEMA_ID,
        "unmapped_public_indexed_gpo_catalog_leads": UNMAPPED_PUBLIC_INDEXED_GPO_CATALOG_LEADS,
        "unmapped_report_search_results": unmapped,
    }
    inventory_path = args.output_dir / "historical_senate_report_inventory.json"
    adapter_path = args.output_dir / "historical_pdf_text_adapter_spec.json"
    write_json_atomic(inventory_path, inventory)
    write_json_atomic(adapter_path, adapter_spec())
    receipt = {
        "adapter_spec": artifact(adapter_path),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_history_assertions": 0,
        "coverage": inventory["coverage"],
        "govinfo_response": {
            "bytes": len(response_bytes),
            "result_count": search.get("count"),
            "sha256": sha256_bytes(response_bytes),
        },
        "inventory": artifact(inventory_path),
        "request": {
            "body_sha256": sha256_bytes(body),
            "endpoint": SEARCH_ENDPOINT,
            "query": SEARCH_QUERY,
        },
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS_WITH_EXPLICIT_GAPS" if gaps else "PASS",
    }
    receipt_path = args.output_dir / "historical_senate_report_inventory_receipt.json"
    write_json_atomic(receipt_path, receipt)
    manifest = {
        "artifacts": {
            "adapter_spec": artifact(adapter_path),
            "govinfo_search_response": artifact(response_path),
            "inventory": artifact(inventory_path),
            "receipt": artifact(receipt_path),
        },
        "schema_id": "staffer-network-historical-senate-report-inventory-manifest-v1",
    }
    write_json_atomic(args.output_dir / "manifest.json", manifest)
    print(compact_json(receipt))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default="DEMO_KEY")
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--source-response", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
