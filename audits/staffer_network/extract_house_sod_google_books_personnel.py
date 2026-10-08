#!/usr/bin/env python3
"""Extract conservative personnel-row candidates from acquired Google Books PDFs.

Only PDF captures already sealed by the acquisition audit are read.  The Google
Books scan text is physically rotated, so coordinates are transformed to a
logical landscape table before section-bounded parsing.  Output rows remain
unadjudicated candidates and never become canonical identity or employment data.
"""

from __future__ import annotations

import argparse
from collections import Counter
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

import fitz


SCHEMA_ID = "staffer-network-house-sod-google-books-personnel-candidate-v1"
RECEIPT_SCHEMA_ID = "staffer-network-house-sod-google-books-personnel-receipt-v1"
DATE_RE = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
AMOUNT_RE = re.compile(r"^-?\(?[\d,]+\.\d{2}\)?$")
DOT_RE = re.compile(r"^[.·�-]{2,}$")


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


def parse_candidate_date(raw: str) -> str | None:
    for fmt in ("%m/%d/%y", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def period_bounds(period: str) -> tuple[str, str]:
    year = int(period[:4])
    quarter = int(period[-1])
    start_month = 1 + (quarter - 1) * 3
    start = dt.date(year, start_month, 1)
    following = dt.date(year + 1, 1, 1) if quarter == 4 else dt.date(year, start_month + 3, 1)
    return start.isoformat(), (following - dt.timedelta(days=1)).isoformat()


def normalize_token(value: str) -> str:
    return "PAYEE" if value.upper().lstrip(".") == "PAYEE" else value


def logical_rows_from_words(
    page_height: float,
    words: Iterable[tuple[float, float, float, float, str]],
    merge_tolerance: float = 2.1,
) -> list[dict[str, Any]]:
    """Rotate vertical OCR coordinates and merge split baselines deterministically."""
    transformed = [
        (float(word[0]), float(page_height - word[3]), normalize_token(str(word[4])), source_index)
        for source_index, word in enumerate(words)
    ]
    groups: list[list[Any]] = []
    for logical_y, logical_x, value, source_index in sorted(transformed, key=lambda row: (row[0], row[1], row[3])):
        if not groups or logical_y - groups[-1][1] > merge_tolerance:
            groups.append([logical_y, logical_y, [(logical_x, value, source_index)]])
        else:
            groups[-1][1] = max(groups[-1][1], logical_y)
            groups[-1][2].append((logical_x, value, source_index))
    return [
        {
            "logical_y_milli": int(round(group[0] * 1000)),
            # Google OCR stream order preserves word order inside cells more
            # faithfully than nearly identical bounding boxes do.  Coordinates
            # remain attached for column filtering.
            "tokens": [
                [int(round(x * 1000)), value]
                for x, value, _ in sorted(group[2], key=lambda row: row[2])
            ],
        }
        for group in groups
    ]


def cleaned_values(tokens: list[list[Any]]) -> list[str]:
    return [value for _, value in tokens if value and not DOT_RE.fullmatch(value)]


def header_columns(tokens: list[list[Any]]) -> dict[str, int] | None:
    positions: dict[str, list[int]] = {}
    for x, value in tokens:
        positions.setdefault(value.upper(), []).append(x)
    if not {"PAYEE", "SERVICE", "DESCRIPTION"}.issubset(positions):
        return None
    amounts = positions.get("YTD", []) + positions.get("QUARTERLY", [])
    if not amounts:
        return None
    return {
        "amount": min(amounts),
        "description": min(positions["DESCRIPTION"]),
        "payee": min(positions["PAYEE"]),
        "service": min(positions["SERVICE"]),
    }


def parse_candidate_row(
    tokens: list[list[Any]],
    columns: dict[str, int],
) -> dict[str, str] | None:
    payee_limit = columns["service"] - 15000
    amount_floor = columns["amount"] - 20000
    payee_tokens = cleaned_values([[x, value] for x, value in tokens if columns["payee"] - 40000 <= x < payee_limit])
    middle_tokens = cleaned_values([[x, value] for x, value in tokens if payee_limit <= x < amount_floor])
    amount_tokens = [value for x, value in tokens if x >= amount_floor and AMOUNT_RE.fullmatch(value)]
    date_indexes = [index for index, value in enumerate(middle_tokens) if DATE_RE.fullmatch(value)]
    if len(date_indexes) < 2 or not amount_tokens:
        return None
    first_date_index, second_date_index = date_indexes[0], date_indexes[1]
    # Google OCR sometimes gives every word in the service/description cells
    # an almost identical bounding box, so coordinate sorting can place a title
    # word just before the dates.  The personnel grammar contains exactly two
    # dates; retain every non-date token in the bounded middle region as raw
    # title evidence rather than silently truncating it.
    title_tokens = [value for value in middle_tokens if not DATE_RE.fullmatch(value)]
    payee = " ".join(payee_tokens).strip()
    title = " ".join(title_tokens).strip()
    if not re.search(r"[A-Za-z]", payee) or not re.search(r"[A-Za-z]", title):
        return None
    return {
        "amount_raw": amount_tokens[-1],
        "payee_raw": payee,
        "service_end_date_raw": middle_tokens[second_date_index],
        "service_start_date_raw": middle_tokens[first_date_index],
        "title_description_raw": title,
    }


def parse_pdf_capture(capture: dict[str, Any], pdf_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    period = capture["period"]
    period_start, period_end = period_bounds(period)
    candidates: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    columns: dict[str, int] | None = None
    office: str | None = None
    in_personnel = False
    with fitz.open(pdf_path) as document:
        counts["pages"] = len(document)
        for page_number, page in enumerate(document, start=1):
            raw_words = page.get_text("words", sort=False)
            counts["ocr_words"] += len(raw_words)
            rows = logical_rows_from_words(page.rect.height, raw_words)
            counts["logical_rows"] += len(rows)
            for row in rows:
                tokens = row["tokens"]
                values = cleaned_values(tokens)
                upper = " ".join(values).upper().replace("�", "-")
                detected_columns = header_columns(tokens)
                if detected_columns is not None:
                    columns = detected_columns
                    in_personnel = False
                    counts["table_header_rows"] += 1
                    continue
                if columns is None:
                    continue
                if (
                    str(period[:4]) in values
                    and any(value.upper().lstrip(".") in {"HON", "HON."} for value in values)
                    and not any(DATE_RE.fullmatch(value) for value in values)
                ):
                    office = " ".join(values)
                    in_personnel = False
                    counts["office_heading_rows"] += 1
                    continue
                amount_tokens = [value for x, value in tokens if x >= columns["amount"] - 20000 and AMOUNT_RE.fullmatch(value)]
                if "PERSONNEL COMPENSATION" in upper:
                    if "TOTALS" in upper:
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
                parsed = parse_candidate_row(tokens, columns)
                if parsed is None:
                    if values:
                        counts["rejected_personnel_rows"] += 1
                    continue
                start_iso = parse_candidate_date(parsed["service_start_date_raw"])
                end_iso = parse_candidate_date(parsed["service_end_date_raw"])
                temporal_status = "WITHIN_REPORT_QUARTER"
                if start_iso is None or end_iso is None:
                    temporal_status = "UNPARSED_SERVICE_DATE"
                elif start_iso > end_iso:
                    temporal_status = "SERVICE_DATE_ORDER_INVALID"
                elif start_iso < period_start or end_iso > period_end:
                    temporal_status = "OUTSIDE_REPORT_QUARTER"
                if temporal_status != "WITHIN_REPORT_QUARTER":
                    counts[f"rejected_{temporal_status.lower()}"] += 1
                    continue
                seed = "\0".join(
                    [
                        capture["body_sha256"],
                        str(page_number),
                        str(row["logical_y_milli"]),
                        parsed["payee_raw"],
                        parsed["service_start_date_raw"],
                        parsed["service_end_date_raw"],
                        parsed["title_description_raw"],
                        parsed["amount_raw"],
                    ]
                ).encode("utf-8")
                candidate = {
                    "amount_raw": parsed["amount_raw"],
                    "book_id": capture["book_id"],
                    "candidate_id": "house-sod-google-books-personnel:" + hashlib.sha256(seed).hexdigest(),
                    "candidate_status": "UNVERIFIED_PUBLIC_SCAN_PERSONNEL_ROW",
                    "canonical_employing_office_id": None,
                    "canonical_employment_episode_id": None,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "canonical_person_id": None,
                    "canonical_service_end_date": None,
                    "canonical_service_start_date": None,
                    "employing_office_raw": office,
                    "part": capture["part"],
                    "payee_raw": parsed["payee_raw"],
                    "period": period,
                    "period_end": period_end,
                    "period_start": period_start,
                    "schema_id": SCHEMA_ID,
                    "service_end_date_candidate_iso": end_iso,
                    "service_end_date_raw": parsed["service_end_date_raw"],
                    "service_start_date_candidate_iso": start_iso,
                    "service_start_date_raw": parsed["service_start_date_raw"],
                    "source_pdf_page_number": page_number,
                    "source_pdf_row_y_milli": row["logical_y_milli"],
                    "source_pdf_sha256": capture["body_sha256"],
                    "source_title": capture["title"],
                    "source_url": capture["download_url_template"],
                    "temporal_validation": temporal_status,
                    "title_description_raw": parsed["title_description_raw"],
                }
                candidates.append(candidate)
                counts["candidate_rows"] += 1
                counts["missing_office_rows"] += int(office is None)
    candidates.sort(key=lambda row: (row["period"], row["part"], row["source_pdf_page_number"], row["source_pdf_row_y_milli"], row["candidate_id"]))
    return candidates, dict(sorted(counts.items()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest_path = args.acquisition_manifest.resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    usable = [
        capture
        for capture in manifest["captures"]
        if capture.get("pdf_magic_verified")
        and capture.get("pdf_inspection", {}).get("personnel_text_extractable")
    ]
    if not usable:
        raise RuntimeError("acquisition manifest contains no personnel-text-extractable PDF")
    all_candidates = []
    source_receipts = []
    for capture in sorted(usable, key=lambda row: (row["period"], row["part"], row["book_id"])):
        pdf_path = manifest_path.parent / capture["body_path"]
        if sha256_file(pdf_path) != capture["body_sha256"]:
            raise RuntimeError(f"sealed PDF hash mismatch: {capture['book_id']}")
        candidates, counts = parse_pdf_capture(capture, pdf_path)
        all_candidates.extend(candidates)
        source_receipts.append(
            {
                "book_id": capture["book_id"],
                "part": capture["part"],
                "pdf_bytes": pdf_path.stat().st_size,
                "pdf_sha256": capture["body_sha256"],
                "period": capture["period"],
                "source_counts": counts,
                "title": capture["title"],
            }
        )
    all_candidates.sort(key=lambda row: (row["period"], row["part"], row["source_pdf_page_number"], row["source_pdf_row_y_milli"], row["candidate_id"]))
    ledger_path = args.output_dir / "house_sod_google_books_personnel_candidates.ndjson.gz"
    temporary = ledger_path.with_name(ledger_path.name + ".part")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as gz:
            for row in all_candidates:
                gz.write((compact_json(row) + "\n").encode("utf-8"))
    os.replace(temporary, ledger_path)
    receipt = {
        "acquisition_manifest": {
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
        "counts": {
            "candidate_rows": len(all_candidates),
            "source_books": len(source_receipts),
            "source_periods": len({row["period"] for row in source_receipts}),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["period", "part", "source_pdf_page_number", "source_pdf_row_y_milli", "candidate_id"],
        },
        "output": {
            "bytes": ledger_path.stat().st_size,
            "path": ledger_path.name,
            "rows": len(all_candidates),
            "sha256": sha256_file(ledger_path),
        },
        "implementation": {
            "script_path": Path(__file__).name,
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "risk_notes": [
            "Rows come from Google Books OCR of a public House document scan, not an official House-hosted PDF.",
            "Only rows with two parseable service dates wholly inside the reported quarter are emitted.",
            "OCR names, offices, titles, and amounts are raw candidate strings and may contain recognition errors.",
            "No cross-row identity merge or employment-tenure inference is performed.",
        ],
        "schema_id": RECEIPT_SCHEMA_ID,
        "sources": source_receipts,
        "status": "PASS" if all_candidates else "FAIL_NO_CANDIDATES",
        "validation": {
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "canonical_office_promotions": 0,
            "canonical_service_date_promotions": 0,
        },
    }
    receipt_path = args.output_dir / "house_sod_google_books_personnel_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(compact_json({"candidate_rows": len(all_candidates), "ledger_sha256": sha256_file(ledger_path), "receipt_sha256": sha256_file(receipt_path), "status": receipt["status"]}))
    return 0 if all_candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
