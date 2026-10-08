#!/usr/bin/env python3
"""Materialize all indexed 2011-present Senate payroll reports deterministically.

Network acquisition is strictly sequential through one pacer.  Only PDF parsing
of already-local official inputs is parallelized.  Output rows remain unverified,
non-canonical employment candidates.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import json
import os
from pathlib import Path
import shutil
from typing import Any

from build_official_senate_payroll_lane import (
    ARCHIVE_URL,
    MANIFEST_SCHEMA_ID,
    PARSER_VERSION,
    SharedPacer,
    artifact_description,
    build_inventory,
    compact_json,
    extract_candidates,
    load_source_bytes,
    sha256_bytes,
    sha256_file,
    write_bytes_atomic,
    write_json_atomic,
)


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "official_senate_payroll_2011_2026_full_8workers"
FULL_RECEIPT_SCHEMA_ID = "staffer-network-official-senate-payroll-full-archive-receipt-v1"
FULL_MANIFEST_SCHEMA_ID = "staffer-network-official-senate-payroll-full-archive-manifest-v1"


def read_gzip_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def extract_job(job: tuple[str, dict[str, Any], str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path, report, cache_dir_raw = job
    cache_dir = Path(cache_dir_raw)
    candidate_cache = cache_dir / f"{report['package_id']}.candidates.ndjson.gz"
    receipt_cache = cache_dir / f"{report['package_id']}.receipt.json"
    if candidate_cache.exists() and receipt_cache.exists():
        cached_stats = json.loads(receipt_cache.read_text(encoding="utf-8"))
        if cached_stats.get("parser_version") == PARSER_VERSION:
            return read_gzip_rows(candidate_cache), cached_stats
    rows, stats = extract_candidates(Path(path), report)
    cache_dir.mkdir(parents=True, exist_ok=True)
    write_gzip_ndjson_atomic(candidate_cache, rows)
    write_json_atomic(receipt_cache, stats)
    return rows, stats


def write_gzip_ndjson_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as stream:
            for row in rows:
                stream.write((compact_json(row) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def acquire_pdfs(
    reports: list[dict[str, Any]],
    output_dir: Path,
    seed_raw_dir: Path | None,
    pacer: SharedPacer,
) -> list[Path]:
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for index, report in enumerate(reports, start=1):
        destination = raw_dir / f"{report['package_id']}.pdf"
        seed = seed_raw_dir / destination.name if seed_raw_dir else None
        if destination.exists():
            pass
        elif seed is not None and seed.exists():
            temporary = destination.with_name(destination.name + ".part")
            shutil.copyfile(seed, temporary)
            os.replace(temporary, destination)
        else:
            value = pacer.get(report["full_pdf_url"], "application/pdf,*/*;q=0.1")
            write_bytes_atomic(destination, value)
        if destination.stat().st_size < 1024 or destination.read_bytes()[:4] != b"%PDF":
            raise RuntimeError(f"Not a valid PDF: {destination}")
        print(f"ACQUIRED {index}/{len(reports)} {report['package_id']} {destination.stat().st_size}", flush=True)
        paths.append(destination)
    return paths


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pacer = SharedPacer(args.minimum_interval_seconds)
    index_bytes = load_source_bytes(args.source_index, args.archive_url, pacer, "text/html,*/*;q=0.1")
    index_path = args.output_dir / "raw" / "senate_report_archive_index.html"
    write_bytes_atomic(index_path, index_bytes)
    inventory = build_inventory(index_bytes)
    inventory_path = args.output_dir / "senate_report_archive_inventory.json"
    write_json_atomic(inventory_path, inventory)
    reports = inventory["periods"]
    pdf_paths = acquire_pdfs(reports, args.output_dir, args.seed_raw_dir, pacer)

    parsed_cache_dir = args.output_dir / "parsed"
    if args.seed_parsed_dir:
        parsed_cache_dir.mkdir(parents=True, exist_ok=True)
        for report in reports:
            for suffix in (".candidates.ndjson.gz", ".receipt.json"):
                source = args.seed_parsed_dir / f"{report['package_id']}{suffix}"
                destination = parsed_cache_dir / source.name
                if source.exists() and not destination.exists():
                    temporary = destination.with_name(destination.name + ".part")
                    shutil.copyfile(source, temporary)
                    os.replace(temporary, destination)
    jobs = [(str(path), report, str(parsed_cache_dir)) for path, report in zip(pdf_paths, reports)]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        extracted = list(pool.map(extract_job, jobs))

    combined: list[dict[str, Any]] = []
    report_receipts: list[dict[str, Any]] = []
    total_pages = 0
    total_candidate_pages = 0
    parse_status_counts: dict[str, int] = {}
    interval_basis_counts: dict[str, int] = {}
    qualifier_row_count = 0
    unresolved_qualifier_row_count = 0
    invalid_or_reversed_qualifier_row_count = 0
    offices: set[str] = set()
    for report, path, (rows, stats) in zip(reports, pdf_paths, extracted):
        combined.extend(rows)
        total_pages += stats["page_count"]
        total_candidate_pages += stats["pages_with_candidates"]
        offices.update(row["office_raw"] for row in rows)
        for status, count in stats["parse_status_counts"].items():
            parse_status_counts[status] = parse_status_counts.get(status, 0) + count
        for basis, count in stats["interval_basis_counts"].items():
            interval_basis_counts[basis] = interval_basis_counts.get(basis, 0) + count
        qualifier_row_count += stats["qualifier_row_count"]
        unresolved_qualifier_row_count += stats["unresolved_qualifier_row_count"]
        invalid_or_reversed_qualifier_row_count += stats["invalid_or_reversed_qualifier_row_count"]
        report_receipts.append({
            "candidate_count": stats["candidate_count"],
            "office_count": stats["office_count"],
            "package_id": report["package_id"],
            "page_count": stats["page_count"],
            "pages_with_candidates": stats["pages_with_candidates"],
            "parse_status_counts": stats["parse_status_counts"],
            "interval_basis_counts": stats["interval_basis_counts"],
            "qualifier_row_count": stats["qualifier_row_count"],
            "unresolved_qualifier_row_count": stats["unresolved_qualifier_row_count"],
            "invalid_or_reversed_qualifier_row_count": stats["invalid_or_reversed_qualifier_row_count"],
            "parser_version": stats["parser_version"],
            "pdf_bytes": path.stat().st_size,
            "pdf_sha256": sha256_file(path),
            "pdf_url": report["full_pdf_url"],
            "period_end": report["period_end"],
            "period_start": report["period_start"],
        })
    combined.sort(key=lambda row: (
        row["report_period_start"], row["report_package_id"], row["page_number"],
        row["row_ordinal_on_page"], row["candidate_id"],
    ))
    ids = [row["candidate_id"] for row in combined]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate candidate IDs in combined Senate archive")

    candidate_path = args.output_dir / "senate_payroll_candidates_2011_2026.ndjson.gz"
    write_gzip_ndjson_atomic(candidate_path, combined)
    report_receipts_path = args.output_dir / "senate_report_extraction_receipts.ndjson"
    write_bytes_atomic(
        report_receipts_path,
        "".join(compact_json(row) + "\n" for row in report_receipts).encode("utf-8"),
    )
    receipt = {
        "archive_coverage": inventory["coverage"],
        "archive_reports_extracted": len(report_receipts),
        "archive_reports_remaining": 0,
        "candidate_file": artifact_description(candidate_path),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_history_assertions": 0,
        "extraction": {
            "candidate_count": len(combined),
            "office_count": len(offices),
            "page_count": total_pages,
            "pages_with_candidates": total_candidate_pages,
            "interval_basis_counts": dict(sorted(interval_basis_counts.items())),
            "qualifier_row_count": qualifier_row_count,
            "unresolved_qualifier_row_count": unresolved_qualifier_row_count,
            "invalid_or_reversed_qualifier_row_count": invalid_or_reversed_qualifier_row_count,
            "parse_status_counts": dict(sorted(parse_status_counts.items())),
        },
        "index_source": {
            "bytes": len(index_bytes),
            "sha256": sha256_bytes(index_bytes),
            "url": args.archive_url,
        },
        "inventory_file": artifact_description(inventory_path),
        "offline_pdf_workers": args.workers,
        "parser_version": PARSER_VERSION,
        "report_extraction_receipts_file": artifact_description(report_receipts_path),
        "schema_id": FULL_RECEIPT_SCHEMA_ID,
        "sequencing_rule": "COLLECT_FIRST_IDENTITY_ADJUDICATION_LATER",
    }
    receipt_path = args.output_dir / "senate_payroll_full_archive_receipt.json"
    write_json_atomic(receipt_path, receipt)
    manifest = {
        "artifacts": {
            "archive_index": artifact_description(index_path),
            "candidate_rows": artifact_description(candidate_path),
            "inventory": artifact_description(inventory_path),
            "report_extraction_receipts": artifact_description(report_receipts_path),
            "receipt": artifact_description(receipt_path),
        },
        "pdfs": [artifact_description(path) for path in pdf_paths],
        "schema_id": FULL_MANIFEST_SCHEMA_ID,
    }
    write_json_atomic(args.output_dir / "manifest.json", manifest)
    print(compact_json(receipt))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-url", default=ARCHIVE_URL)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed-raw-dir", type=Path)
    parser.add_argument("--seed-parsed-dir", type=Path)
    parser.add_argument("--source-index", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if not 1 <= args.workers <= 8:
        parser.error("--workers must be between 1 and 8")
    return args


if __name__ == "__main__":
    run(parse_args())
