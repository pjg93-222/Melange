#!/usr/bin/env python3
"""Acquire historical official House SOD PDFs and inventory pre-web reports.

Adapters are deliberately separated:

* 2009Q3-2015Q4: official house.gov single-volume PDFs and layout text.
* 1996Q1-2008Q4: official GovInfo Serial Set session indexes.  These are
  bibliographic evidence only unless a separately verified official digital
  report URL is present; catalog metadata is never represented as payroll data.

All network access is sequential through one shared pacer.  Completed files are
reused without cache clearing.  No payee identity is adjudicated or merged.
"""

from __future__ import annotations

import argparse
from collections import Counter
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable
import urllib.parse

import fitz
from pypdf import PdfReader

import acquire_house_sod_payroll as base


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "house_sod_payroll_20260831"
INVENTORY_SCHEMA_ID = "staffer-network-house-sod-historical-inventory-v1"
PDF_CANDIDATE_SCHEMA_ID = "staffer-network-house-sod-pdf-payroll-candidate-v1"
PDF_RECEIPT_SCHEMA_ID = "staffer-network-house-sod-pdf-payroll-receipt-v1"


def session_for_year(year: int) -> tuple[int, int]:
    return (year - 1789) // 2 + 1, 1 if year % 2 else 2


def session_index_specs() -> list[dict[str, Any]]:
    # 111-1 is included because publication of late-2008 Serial Set volumes can
    # lag into the following congressional session.
    specs = []
    for congress in range(104, 112):
        for session in (1, 2):
            if (congress, session) < (104, 2) or (congress, session) > (111, 1):
                continue
            specs.append(
                {
                    "congress": congress,
                    "session": session,
                    "url": f"https://www.govinfo.gov/media/{congress}-{session}se.pdf",
                }
            )
    return specs


def generic_download(
    key: str,
    url: str,
    final_path: Path,
    pacer: base.SharedPacer,
    max_attempts: int,
    expected_magic: bytes,
) -> tuple[str, int, str]:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    part_path = final_path.with_name(final_path.name + ".part")
    if final_path.exists():
        return base.sha256_file(final_path), final_path.stat().st_size, "REUSED_COMPLETE_CACHE"
    for attempt in range(1, max_attempts + 1):
        partial_size = part_path.stat().st_size if part_path.exists() else 0
        headers = {"Range": f"bytes={partial_size}-"} if partial_size else {}
        try:
            with base.request_url(url, pacer, headers=headers, timeout=180) as response:
                status = getattr(response, "status", response.getcode())
                append = bool(partial_size and status == 206)
                declared = response.headers.get("Content-Length")
                received = 0
                with part_path.open("ab" if append else "wb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        output.write(chunk)
            # http.client.HTTPResponse.read(amt) deliberately does NOT raise
            # IncompleteRead, so a body that stops early exits the loop as an
            # ordinary success. The magic check below only proves the FIRST bytes;
            # a truncated PDF still starts with %PDF and would be promoted and then
            # reported REUSED_COMPLETE_CACHE forever.
            if declared is not None and str(declared).strip().isdigit():
                if received != int(str(declared).strip()):
                    raise RuntimeError(
                        f"{key}: truncated body: {received} of "
                        f"{int(str(declared).strip())} declared bytes"
                    )
            with part_path.open("rb") as probe:
                if probe.read(len(expected_magic)) != expected_magic:
                    raise RuntimeError(f"{key}: source body failed magic validation")
            os.replace(part_path, final_path)
            return base.sha256_file(final_path), final_path.stat().st_size, "DOWNLOADED"
        except Exception as error:
            if attempt >= max_attempts:
                raise RuntimeError(f"{key}: download failed after {max_attempts} attempts: {error}") from error
            time.sleep(5.0 * attempt)
    raise AssertionError("unreachable")


def pdf_text(path: Path, layout: bool = False) -> tuple[str, int]:
    reader = PdfReader(path)
    pages = []
    for page in reader.pages:
        if layout:
            try:
                text = page.extract_text(extraction_mode="layout") or ""
            except TypeError:
                text = page.extract_text() or ""
        else:
            text = page.extract_text() or ""
        pages.append(text)
    return "\n\f\n".join(pages), len(reader.pages)


def infer_title_period(title: str) -> str | None:
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", title)
    if not year_match:
        return None
    year = int(year_match.group(1))
    upper = title.upper()
    if "JAN" in upper or "MARCH" in upper:
        quarter = 1
    elif "APRIL" in upper or "JUNE" in upper:
        quarter = 2
    elif "JULY" in upper or "SEPT" in upper:
        quarter = 3
    elif "OCT" in upper or "DEC" in upper:
        quarter = 4
    else:
        return None
    return f"{year}Q{quarter}"


def parse_serial_index(text: str, source: dict[str, Any]) -> list[dict[str, Any]]:
    text = text.replace("\ufffd", "-")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    entries = []
    current: tuple[str, str] | None = None
    for index, line in enumerate(lines):
        match = re.match(r"^(\d{5}[A-Z]?).*?House Document No\.\s*(\d+)\b", line, re.I)
        if match:
            current = (match.group(1), match.group(2))
            block = " ".join(lines[index : index + 4])
            if "Statement of Disbursements" not in block and "Statement of Disbursments" not in block:
                continue
            period = infer_title_period(block)
            if period is None:
                continue
            part_match = re.search(r"\bpt\.\s*(\d+)\b", block, re.I)
            entries.append(
                {
                    "house_document_number": current[1],
                    "index_congress": source["congress"],
                    "index_session": source["session"],
                    "index_url": source["url"],
                    "part": int(part_match.group(1)) if part_match else None,
                    "period": period,
                    "serial_set_number": current[0],
                    "title_evidence": block,
                }
            )
    return entries


def parse_house_archive_pdfs(archive_bytes: bytes) -> list[dict[str, Any]]:
    parser = base.AnchorCollector()
    parser.feed(archive_bytes.decode("utf-8", errors="replace"))
    entries = []
    for href, label in parser.anchors:
        if not urllib.parse.urlparse(href).path.lower().endswith(".pdf"):
            continue
        inferred = base.infer_period(href, label)
        if inferred is None or not (2009 <= inferred[0] <= 2015):
            continue
        year, quarter = inferred
        period = f"{year}Q{quarter}"
        start, end = base.quarter_bounds(year, quarter)
        entries.append(
            {
                "period": period,
                "period_end": end,
                "period_start": start,
                "pdf_url": urllib.parse.urljoin(base.ARCHIVE_URL, href),
                "source_status": "OFFICIAL_HOUSE_PDF_AVAILABLE",
            }
        )
    by_period = {entry["period"]: entry for entry in entries}
    return [by_period[key] for key in sorted(by_period)]


def build_historical_inventory(args: argparse.Namespace, pacer: base.SharedPacer) -> tuple[dict[str, Any], Path]:
    inventory_path = args.output_dir / "house_sod_historical_url_inventory.json"
    if inventory_path.exists() and not args.refresh_inventory:
        return json.loads(inventory_path.read_text(encoding="utf-8")), inventory_path

    archive_bytes = base.fetch_bytes(base.ARCHIVE_URL, pacer)
    house_pdfs = parse_house_archive_pdfs(archive_bytes)
    index_dir = args.output_dir / "raw_govinfo_serial_indexes"
    index_receipts = []
    catalog_entries = []
    for spec in session_index_specs():
        key = f"{spec['congress']}-{spec['session']}"
        path = index_dir / f"{key}se.pdf"
        digest, byte_count, state = generic_download(
            key, spec["url"], path, pacer, args.max_attempts, b"%PDF"
        )
        text, page_count = pdf_text(path)
        source = {**spec, "bytes": byte_count, "pages": page_count, "sha256": digest}
        index_receipts.append(source)
        catalog_entries.extend(parse_serial_index(text, source))
        print(base.compact_json({"bytes": byte_count, "download_state": state, "source": key}), flush=True)

    catalog_by_period: dict[str, list[dict[str, Any]]] = {}
    for entry in catalog_entries:
        if "1996Q1" <= entry["period"] <= "2008Q4":
            catalog_by_period.setdefault(entry["period"], []).append(entry)

    historical_quarters = []
    for year in range(1996, 2009):
        for quarter in range(1, 5):
            period = f"{year}Q{quarter}"
            start, end = base.quarter_bounds(year, quarter)
            evidence = sorted(
                catalog_by_period.get(period, []),
                key=lambda row: (row["part"] or 0, row["serial_set_number"]),
            )
            historical_quarters.append(
                {
                    "catalog_evidence": evidence,
                    "digital_report_url": None,
                    "period": period,
                    "period_end": end,
                    "period_start": start,
                    "payroll_extraction_status": (
                        "GAP_FULL_REPORT_NOT_AVAILABLE_IN_VERIFIED_OFFICIAL_DIGITAL_FORM"
                        if evidence
                        else "GAP_NO_OFFICIAL_CATALOG_ENTRY_LOCATED"
                    ),
                    "source_status": (
                        "OFFICIAL_GOVINFO_SERIAL_SET_CATALOG_METADATA_ONLY"
                        if evidence
                        else "OFFICIAL_SOURCE_NOT_LOCATED"
                    ),
                }
            )

    inventory = {
        "archive": {
            "bytes": len(archive_bytes),
            "sha256": base.sha256_bytes(archive_bytes),
            "url": base.ARCHIVE_URL,
        },
        "coverage": {
            "house_pdf_period_count": len(house_pdfs),
            "house_pdf_periods": [row["period"] for row in house_pdfs],
            "pre_web_catalog_period_count": sum(bool(row["catalog_evidence"]) for row in historical_quarters),
            "pre_web_full_report_digital_period_count": 0,
            "pre_web_gap_periods": [row["period"] for row in historical_quarters],
        },
        "govinfo_serial_set_index_sources": index_receipts,
        "house_pdf_periods": house_pdfs,
        "pre_web_periods": historical_quarters,
        "schema_id": INVENTORY_SCHEMA_ID,
    }
    base.write_json_atomic(inventory_path, inventory)
    return inventory, inventory_path


def visual_rows(page: fitz.Page) -> list[dict[str, Any]]:
    transformed = []
    for word in page.get_text("words", sort=False):
        rectangle = fitz.Rect(word[:4]) * page.rotation_matrix
        transformed.append((rectangle.x0, rectangle.y0, word[4]))
    groups: list[list[Any]] = []
    for word in sorted(transformed, key=lambda value: (value[1], value[0])):
        if not groups or abs(word[1] - groups[-1][0]) > 1.2:
            groups.append([word[1], [word]])
        else:
            groups[-1][1].append(word)
    return [
        {
            "row_y_milli": int(round(y * 1000)),
            "words": [[int(round(word[0] * 1000)), word[2]] for word in sorted(words, key=lambda value: value[0])],
        }
        for y, words in groups
    ]


def extract_layout_text_worker(task: tuple[str, str, str]) -> dict[str, Any]:
    period, pdf_path_text, text_path_text = task
    pdf_path = Path(pdf_path_text)
    text_path = Path(text_path_text)
    if text_path.exists():
        return {
            "period": period,
            "text_bytes": text_path.stat().st_size,
            "text_sha256": base.sha256_file(text_path),
            "text_state": "REUSED_COMPLETE_CACHE",
        }
    temporary = text_path.with_name(text_path.name + ".part")
    text_path.parent.mkdir(parents=True, exist_ok=True)
    page_count = 0
    row_count = 0
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            with fitz.open(pdf_path) as document:
                page_count = len(document)
                for page_number, page in enumerate(document, start=1):
                    for row in visual_rows(page):
                        row_count += 1
                        record = {"page_number": page_number, **row}
                        gz.write((base.compact_json(record) + "\n").encode("utf-8"))
    os.replace(temporary, text_path)
    return {
        "pages": page_count,
        "period": period,
        "visual_text_rows": row_count,
        "text_bytes": text_path.stat().st_size,
        "text_sha256": base.sha256_file(text_path),
        "text_state": "EXTRACTED",
    }


def acquire_pdf_sources(
    entries: list[dict[str, Any]],
    args: argparse.Namespace,
    pacer: base.SharedPacer,
) -> list[dict[str, Any]]:
    pdf_dir = args.output_dir / "raw_historical_house_pdf"
    text_dir = args.output_dir / "historical_house_pdf_text"
    receipts = []
    for entry in entries:
        period = entry["period"]
        path = pdf_dir / f"{period.lower()}_singlevolume.pdf"
        digest, byte_count, state = generic_download(
            period, entry["pdf_url"], path, pacer, args.max_attempts, b"%PDF"
        )
        receipts.append(
            {
                **entry,
                "bytes": byte_count,
                "pdf_path": str(path),
                "pdf_sha256": digest,
                "runtime_download_state": state,
                "text_path": str(text_dir / f"{period.lower()}_visual_rows.ndjson.gz"),
            }
        )
        print(base.compact_json({"bytes": byte_count, "download_state": state, "period": period}), flush=True)

    tasks = [(row["period"], row["pdf_path"], row["text_path"]) for row in receipts]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as executor:
        extracted = list(executor.map(extract_layout_text_worker, tasks))
    text_by_period = {row["period"]: row for row in extracted}
    for receipt in receipts:
        receipt.update(text_by_period[receipt["period"]])
    return receipts


DATE_TOKEN_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
AMOUNT_TOKEN_RE = re.compile(r"^-?\(?[\d,]+(?:\.\d{2})?\)?$")
DOT_LEADER_RE = re.compile(r"^[.·�-]{4,}$")


def row_text(words: list[list[Any]], minimum_x: int = 0, maximum_x: int = 10**9) -> str:
    return " ".join(
        value for x, value in words if minimum_x <= x < maximum_x and not DOT_LEADER_RE.fullmatch(value)
    ).strip()


def header_columns(words: list[list[Any]]) -> dict[str, int] | None:
    positions = {value.upper(): x for x, value in words}
    if not {"PAYEE", "SERVICE", "DESCRIPTION"}.issubset(positions):
        return None
    amount_positions = [x for x, value in words if value.upper() in {"YTD", "QUARTERLY"}]
    return {
        "payee": positions["PAYEE"],
        "service": positions["SERVICE"],
        "description": positions["DESCRIPTION"],
        "amount": min(amount_positions) if amount_positions else positions["DESCRIPTION"] + 160000,
    }


def detect_office(words: list[list[Any]], columns: dict[str, int]) -> str | None:
    office_floor = max(0, columns["payee"] - 70000)
    office_words = [[x, value] for x, value in words if office_floor <= x < columns["amount"]]
    year_index = next(
        (index for index, (_, value) in enumerate(office_words) if re.fullmatch(r"20\d{2}", value)),
        None,
    )
    if year_index is None:
        return None
    candidate = row_text(office_words[year_index:])
    upper = candidate.upper()
    if "STATEMENT OF DISBURSEMENTS" in upper or "TOTALS:" in upper or len(candidate.split()) < 2:
        return None
    return candidate


def parse_visual_period(
    source: dict[str, Any],
    writer: io.TextIOBase,
) -> dict[str, Any]:
    text_path = Path(source["text_path"])
    columns: dict[str, int] | None = None
    office: str | None = None
    in_personnel = False
    counts = Counter()
    page_numbers = set()
    with gzip.open(text_path, "rt", encoding="utf-8") as rows:
        for raw in rows:
            row = json.loads(raw)
            words = row["words"]
            page_number = row["page_number"]
            page_numbers.add(page_number)
            counts["visual_text_rows"] += 1
            detected_columns = header_columns(words)
            if detected_columns:
                columns = detected_columns
                counts["table_header_rows"] += 1
                continue
            if columns is None:
                continue
            detected_office = detect_office(words, columns)
            if detected_office:
                office = detected_office
                in_personnel = False
                counts["office_heading_rows"] += 1
                continue

            # Section labels and their totals are not confined to the payee/
            # description columns.  In the historical PDFs, the words
            # ``PERSONNEL COMPENSATION TOTALS`` can begin in the description
            # column and ``TOTALS`` can fall beyond the YTD boundary.  Using
            # the bounded detail-row slice therefore missed the terminator and
            # incorrectly carried personnel state into TRAVEL and later
            # expenditure sections.  Section-state detection must inspect the
            # complete visual row; payee/title extraction below remains
            # column-bounded.
            upper = row_text(words).upper().replace("�", "-")
            amount_tokens = [value for x, value in words if x >= columns["amount"] - 10000 and AMOUNT_TOKEN_RE.fullmatch(value)]
            if "PERSONNEL COMPENSATION" in upper:
                if "TOTALS:" in upper:
                    in_personnel = False
                    counts["personnel_total_rows"] += 1
                elif not amount_tokens:
                    in_personnel = True
                    counts["personnel_detail_heading_rows"] += 1
                else:
                    counts["personnel_summary_heading_rows"] += 1
                continue
            if not in_personnel:
                continue

            payee = row_text(words, columns["payee"] - 20000, columns["service"])
            date_tokens = [
                value
                for x, value in words
                if columns["service"] - 5000 <= x < columns["description"] and DATE_TOKEN_RE.fullmatch(value)
            ]
            title = row_text(words, columns["description"] - 5000, columns["amount"])
            if len(date_tokens) < 2 or not re.search(r"[A-Za-z]", payee) or not re.search(r"[A-Za-z]", title) or not amount_tokens:
                if payee or title or date_tokens or amount_tokens:
                    counts["rejected_personnel_section_rows"] += 1
                continue

            start_raw, end_raw = date_tokens[0], date_tokens[1]
            start_iso, start_status = base.candidate_iso_date(start_raw)
            end_iso, end_status = base.candidate_iso_date(end_raw)
            candidate_seed = (
                f"{source['pdf_sha256']}\0{page_number}\0{row['row_y_milli']}\0{payee}\0{title}"
            ).encode("utf-8")
            candidate = {
                "amount_raw": amount_tokens[-1],
                "candidate_id": "house-sod-pdf-payroll:" + hashlib.sha256(candidate_seed).hexdigest(),
                "candidate_status": "UNVERIFIED_OFFICIAL_PDF_TABLE_ROW",
                "canonical_employing_office_id": None,
                "canonical_employment_episode_id": None,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_person_id": None,
                "canonical_service_end_date": None,
                "canonical_service_start_date": None,
                "employing_office_raw": office,
                "payee_raw": payee,
                "period": source["period"],
                "period_end": source["period_end"],
                "period_start": source["period_start"],
                "schema_id": PDF_CANDIDATE_SCHEMA_ID,
                "service_end_date_candidate_iso": end_iso,
                "service_end_date_parse_status": end_status,
                "service_end_date_raw": end_raw,
                "service_start_date_candidate_iso": start_iso,
                "service_start_date_parse_status": start_status,
                "service_start_date_raw": start_raw,
                "source_pdf_page_number": page_number,
                "source_pdf_row_y_milli": row["row_y_milli"],
                "source_pdf_sha256": source["pdf_sha256"],
                "source_url": source["pdf_url"],
                "title_description_raw": title,
                "ytd_amount_raw": amount_tokens[-2] if len(amount_tokens) >= 2 else None,
            }
            writer.write(base.compact_json(candidate) + "\n")
            counts["payroll_candidate_rows"] += 1
            counts["missing_office_rows"] += int(office is None)
            counts["unparsed_service_date_fields"] += int(start_iso is None) + int(end_iso is None)
    return {"pages_observed": len(page_numbers), **dict(sorted(counts.items()))}


def write_pdf_candidates(
    mode: str,
    sources: list[dict[str, Any]],
    output_dir: Path,
    inventory_path: Path,
    minimum_request_interval: float,
    workers: int,
) -> dict[str, Any]:
    stem = "house_sod_payroll_pdf_sample" if mode == "sample" else "house_sod_payroll_pdf"
    output_path = output_dir / f"{stem}_candidates.ndjson.gz"
    receipt_path = output_dir / f"{stem}_receipt.json"
    temporary = output_path.with_name(output_path.name + ".part")
    period_receipts = []
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            with io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as writer:
                for source in sources:
                    stats = parse_visual_period(source, writer)
                    period_receipts.append(
                        {
                            "bytes": source["bytes"],
                            "pages": source.get("pages"),
                            "pdf_sha256": source["pdf_sha256"],
                            "pdf_url": source["pdf_url"],
                            "period": source["period"],
                            "text_bytes": source["text_bytes"],
                            "text_sha256": source["text_sha256"],
                            **stats,
                        }
                    )
    os.replace(temporary, output_path)
    candidate_rows = sum(row.get("payroll_candidate_rows", 0) for row in period_receipts)
    receipt = {
        "acquisition_policy": {
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "canonical_merges_performed": 0,
            "completed_source_cache_policy": "IMMUTABLE_REUSE; NO CACHE CLEARING",
            "download_concurrency": 1,
            "layout_text_workers": workers,
            "minimum_request_interval_seconds": minimum_request_interval,
            "source_scope": "OFFICIAL_HOUSE_GOV_PDF_ONLY",
        },
        "counts": {
            "missing_office_rows": sum(row.get("missing_office_rows", 0) for row in period_receipts),
            "payroll_candidate_rows": candidate_rows,
            "rejected_personnel_section_rows": sum(
                row.get("rejected_personnel_section_rows", 0) for row in period_receipts
            ),
            "source_periods": len(period_receipts),
            "unparsed_service_date_fields": sum(
                row.get("unparsed_service_date_fields", 0) for row in period_receipts
            ),
        },
        "historical_inventory": {
            "path": inventory_path.name,
            "sha256": base.sha256_file(inventory_path),
        },
        "mode": mode.upper(),
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": candidate_rows,
            "sha256": base.sha256_file(output_path),
        },
        "periods": period_receipts,
        "risk_notes": [
            "Candidates are coordinate-reconstructed official PDF table rows, not canonical identities or employment episodes.",
            "Service dates are payment coverage dates and are not promoted to complete employment tenure.",
            "The parser requires a personnel-compensation section, payee text, two service dates, title text, and an amount; malformed or multi-line rows can be under-recalled.",
            "PDF text can contain replacement characters or truncated House abbreviations; raw extracted strings are retained without name or title correction.",
            "Repeated payees and overlapping service periods are retained without cross-row or cross-quarter merging.",
        ],
        "schema_id": PDF_RECEIPT_SCHEMA_ID,
        "status": "PASS" if candidate_rows else "FAIL_NO_CANDIDATES",
        "validation": {
            "canonical_employment_episode_promotions": 0,
            "canonical_identity_promotions": 0,
            "canonical_office_promotions": 0,
            "canonical_service_date_promotions": 0,
            "period_order_preserved": True,
        },
    }
    base.write_json_atomic(receipt_path, receipt)
    return {"receipt": receipt, "receipt_path": str(receipt_path), "receipt_sha256": base.sha256_file(receipt_path)}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inventory", "sample", "pdf-full"), default="inventory")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-request-interval", type=float, default=2.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--refresh-inventory", action="store_true")
    args = parser.parse_args(argv)
    if args.minimum_request_interval < 1.0:
        parser.error("--minimum-request-interval must be at least 1 second")
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    pacer = base.SharedPacer(args.minimum_request_interval)
    inventory, inventory_path = build_historical_inventory(args, pacer)
    if args.mode == "inventory":
        print(
            base.compact_json(
                {
                    "coverage": inventory["coverage"],
                    "inventory_path": str(inventory_path),
                    "inventory_sha256": base.sha256_file(inventory_path),
                }
            )
        )
        return 0
    pdf_entries = inventory["house_pdf_periods"]
    if args.mode == "sample":
        pdf_entries = [pdf_entries[0], pdf_entries[-1]]
    receipts = acquire_pdf_sources(pdf_entries, args, pacer)
    result = write_pdf_candidates(
        args.mode,
        receipts,
        args.output_dir,
        inventory_path,
        args.minimum_request_interval,
        args.workers,
    )
    print(base.compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
