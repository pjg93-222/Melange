#!/usr/bin/env python3
"""Acquire and conservatively normalize official House SOD payroll candidates.

The downloader uses one sequential pacer for all house.gov requests, preserves
completed source files as an immutable local cache, and can resume an interrupted
``.part`` download when the server honors HTTP Range.  It never merges payees or
promotes a row to a canonical person or employment episode.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import html.parser
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request


ARCHIVE_URL = "https://www.house.gov/the-house-explained/open-government/statement-of-disbursements/archive"
CURRENT_URL = "https://www.house.gov/the-house-explained/open-government/statement-of-disbursements"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "house_sod_payroll_20260831"
USER_AGENT = "MelangeSystemsHouseSOD/1.0 (official-public-data research; sequential paced downloader)"
SCHEMA_ID = "staffer-network-house-sod-payroll-candidate-v1"
RECEIPT_SCHEMA_ID = "staffer-network-house-sod-payroll-receipt-v1"
INVENTORY_SCHEMA_ID = "staffer-network-house-sod-url-inventory-v1"


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(compact_json(value) + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)


class AnchorCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        values = dict(attrs)
        if values.get("href"):
            self._href = values["href"]
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


class SharedPacer:
    def __init__(self, minimum_interval_seconds: float) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self._last_request_started: float | None = None

    def wait(self) -> None:
        if self._last_request_started is not None:
            remaining = self.minimum_interval_seconds - (time.monotonic() - self._last_request_started)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_started = time.monotonic()


def request_url(url: str, pacer: SharedPacer, headers: dict[str, str] | None = None, timeout: int = 120):
    pacer.wait()
    request_headers = {"User-Agent": USER_AGENT, "Accept": "text/csv,text/html;q=0.9,*/*;q=0.1"}
    if headers:
        request_headers.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=request_headers), timeout=timeout)


def fetch_bytes(url: str, pacer: SharedPacer) -> bytes:
    with request_url(url, pacer) as response:
        return response.read()


def infer_period(href: str, label: str) -> tuple[int, int] | None:
    decoded_href = urllib.parse.unquote(href)
    basename = Path(urllib.parse.urlparse(decoded_href).path).name.upper()
    context = f"{basename} {label.upper()} {decoded_href.upper()}"
    explicit = re.search(r"(20\d{2})\s*Q([1-4])", context)
    if explicit:
        return int(explicit.group(1)), int(explicit.group(2))

    years = re.findall(r"20\d{2}", f"{basename} {label}")
    if not years:
        return None
    year = int(years[-1])
    month_quarters = (
        (1, ("JAN", "FEB", "MAR")),
        (2, ("APR", "MAY", "JUN")),
        (3, ("JUL", "AUG", "SEP")),
        (4, ("OCT", "NOV", "DEC")),
    )
    for quarter, tokens in month_quarters:
        if any(token in context for token in tokens):
            return year, quarter
    return None


def quarter_bounds(year: int, quarter: int) -> tuple[str, str]:
    first_month = 1 + (quarter - 1) * 3
    start = dt.date(year, first_month, 1)
    if quarter == 4:
        following = dt.date(year + 1, 1, 1)
    else:
        following = dt.date(year, first_month + 3, 1)
    end = following - dt.timedelta(days=1)
    return start.isoformat(), end.isoformat()


def build_inventory(
    archive_bytes: bytes,
    archive_url: str,
    additional_pages: Iterable[tuple[bytes, str]] = (),
) -> dict[str, Any]:
    entries: dict[str, dict[str, Any]] = {}
    source_pages = [(archive_bytes, archive_url), *additional_pages]
    for page_bytes, page_url in source_pages:
        parser = AnchorCollector()
        parser.feed(page_bytes.decode("utf-8", errors="replace"))
        for href, label in parser.anchors:
            lower_path = urllib.parse.urlparse(href).path.lower()
            if not (lower_path.endswith(".csv") or lower_path.endswith(".pdf")):
                continue
            inferred = infer_period(href, label)
            if inferred is None or inferred[0] < 2016:
                continue
            year, quarter = inferred
            period = f"{year}Q{quarter}"
            start, end = quarter_bounds(year, quarter)
            entry = entries.setdefault(
                period,
                {
                    "period": period,
                    "period_end": end,
                    "period_start": start,
                    "detail_csv_url": None,
                    "summary_csv_url": None,
                    "pdf_url": None,
                },
            )
            absolute = urllib.parse.urljoin(page_url, href)
            upper_label = label.upper()
            if lower_path.endswith(".csv") and "DETAIL" in upper_label:
                entry["detail_csv_url"] = absolute
            elif lower_path.endswith(".csv") and "SUMMARY" in upper_label:
                entry["summary_csv_url"] = absolute
            elif lower_path.endswith(".pdf"):
                entry["pdf_url"] = absolute

    ordered = [entries[key] for key in sorted(entries)]
    detail_periods = [row["period"] for row in ordered if row["detail_csv_url"]]
    if not detail_periods:
        raise RuntimeError("The official archive yielded no detail CSV links")
    newest_year = max(int(period[:4]) for period in detail_periods)
    expected = [f"{year}Q{quarter}" for year in range(2016, newest_year + 1) for quarter in range(1, 5)]
    newest_quarter = max(int(period[-1]) for period in detail_periods if int(period[:4]) == newest_year)
    expected = [period for period in expected if int(period[:4]) < newest_year or int(period[-1]) <= newest_quarter]
    missing_detail = sorted(set(expected) - set(detail_periods))
    return {
        "archive": {
            "bytes": len(archive_bytes),
            "sha256": sha256_bytes(archive_bytes),
            "url": archive_url,
        },
        "source_pages": [
            {"bytes": len(page_bytes), "sha256": sha256_bytes(page_bytes), "url": page_url}
            for page_bytes, page_url in source_pages
        ],
        "coverage": {
            "detail_csv_period_count": len(detail_periods),
            "first_detail_csv_period": min(detail_periods),
            "last_detail_csv_period": max(detail_periods),
            "missing_detail_csv_periods": missing_detail,
            "pdf_fallback_periods": [row["period"] for row in ordered if not row["detail_csv_url"] and row["pdf_url"]],
        },
        "periods": ordered,
        "schema_id": INVENTORY_SCHEMA_ID,
    }


def load_or_create_inventory(args: argparse.Namespace, pacer: SharedPacer) -> tuple[dict[str, Any], Path]:
    inventory_path = args.output_dir / "house_sod_url_inventory.json"
    if inventory_path.exists() and not args.refresh_inventory:
        return json.loads(inventory_path.read_text(encoding="utf-8")), inventory_path
    archive_bytes = fetch_bytes(args.archive_url, pacer)
    current_bytes = fetch_bytes(args.current_url, pacer)
    inventory = build_inventory(
        archive_bytes,
        args.archive_url,
        additional_pages=[(current_bytes, args.current_url)],
    )
    if inventory["coverage"]["missing_detail_csv_periods"]:
        raise RuntimeError(
            "CSV inventory has gaps: " + ", ".join(inventory["coverage"]["missing_detail_csv_periods"])
        )
    write_json_atomic(inventory_path, inventory)
    return inventory, inventory_path


def retry_after_seconds(error: urllib.error.HTTPError, fallback: float) -> float:
    value = error.headers.get("Retry-After") if error.headers else None
    if value and value.isdigit():
        return max(fallback, float(value))
    return fallback


def download_source(
    period: str,
    url: str,
    raw_dir: Path,
    pacer: SharedPacer,
    max_attempts: int,
) -> tuple[Path, str, int, str]:
    raw_dir.mkdir(parents=True, exist_ok=True)
    final_path = raw_dir / f"{period.lower()}_sod_detail.csv"
    part_path = final_path.with_name(final_path.name + ".part")
    if final_path.exists():
        return final_path, sha256_file(final_path), final_path.stat().st_size, "REUSED_COMPLETE_CACHE"

    for attempt in range(1, max_attempts + 1):
        partial_size = part_path.stat().st_size if part_path.exists() else 0
        headers = {"Range": f"bytes={partial_size}-"} if partial_size else {}
        try:
            with request_url(url, pacer, headers=headers) as response:
                status = getattr(response, "status", response.getcode())
                append = bool(partial_size and status == 206)
                mode = "ab" if append else "wb"
                declared = response.headers.get("Content-Length")
                received = 0
                with part_path.open(mode) as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        received += len(chunk)
                        output.write(chunk)
            # http.client.HTTPResponse.read(amt) deliberately does NOT raise
            # IncompleteRead ("it might break compatibility"), so a body that stops
            # early exits the loop as an ordinary success. Without this check the
            # short file is promoted over final_path and every later run reports
            # REUSED_COMPLETE_CACHE for a truncated CSV.
            if declared is not None and str(declared).strip().isdigit():
                if received != int(str(declared).strip()):
                    raise RuntimeError(
                        f"{period}: truncated body: {received} of "
                        f"{int(str(declared).strip())} declared bytes"
                    )
            with part_path.open("rb") as probe:
                first = probe.read(512)
            decoded = first.decode("utf-8-sig", errors="replace").upper()
            if "<HTML" in decoded or "ORGANIZATION" not in decoded:
                raise RuntimeError(f"{period}: downloaded body does not look like a House detail CSV")
            os.replace(part_path, final_path)
            return final_path, sha256_file(final_path), final_path.stat().st_size, "DOWNLOADED"
        except (OSError, urllib.error.URLError, RuntimeError) as error:
            if attempt >= max_attempts:
                raise RuntimeError(f"{period}: download failed after {max_attempts} attempts: {error}") from error
            delay = 5.0 * attempt
            if isinstance(error, urllib.error.HTTPError):
                delay = retry_after_seconds(error, delay)
            time.sleep(delay)
    raise AssertionError("unreachable")


def normalized_header(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip()).upper()


def clean_cell(value: Any) -> str:
    return "" if value is None else str(value).strip()


def choose(row: dict[str, str], *keys: str) -> str:
    for key in keys:
        value = clean_cell(row.get(key))
        if value:
            return value
    return ""


DATE_FORMATS = ("%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d")


def candidate_iso_date(raw: str) -> tuple[str | None, str]:
    if not raw:
        return None, "MISSING"
    for date_format in DATE_FORMATS:
        try:
            return dt.datetime.strptime(raw, date_format).date().isoformat(), "PARSED_CANDIDATE_DATE"
        except ValueError:
            pass
    return None, "UNPARSED_RAW_DATE"


def office_candidate(raw: str) -> tuple[str, str]:
    candidate = re.sub(r"^(?:FISCAL\s+YEAR\s+)?20\d{2}\s+", "", raw, flags=re.I).strip()
    if candidate != raw:
        return candidate, "LEADING_REPORT_YEAR_REMOVED"
    return raw, "RAW_UNCHANGED"


def output_paths(output_dir: Path, mode: str) -> tuple[Path, Path]:
    if mode == "sample":
        return (
            output_dir / "house_sod_payroll_sample_candidates.ndjson.gz",
            output_dir / "house_sod_payroll_sample_receipt.json",
        )
    return (
        output_dir / "house_sod_payroll_candidates.ndjson.gz",
        output_dir / "house_sod_payroll_receipt.json",
    )


def parse_period_to_output(
    entry: dict[str, Any],
    source_path: Path,
    source_sha256: str,
    writer: io.TextIOBase,
) -> dict[str, Any]:
    total_rows = 0
    detail_rows = 0
    payroll_rows = 0
    malformed_width_rows = 0
    missing_payee_rows = 0
    missing_title_rows = 0
    unparsed_date_fields = 0
    negative_amount_rows = 0
    header: list[str] = []

    with source_path.open("r", encoding="utf-8-sig", errors="replace", newline="") as source:
        reader = csv.reader(source)
        try:
            raw_header = next(reader)
        except StopIteration as error:
            raise RuntimeError(f"{entry['period']}: empty source CSV") from error
        header = [normalized_header(value) for value in raw_header]
        required = {"ORGANIZATION", "SORT SUBTOTAL DESCRIPTION", "SORT SEQUENCE", "VENDOR NAME", "DESCRIPTION"}
        missing = sorted(required - set(header))
        if missing:
            raise RuntimeError(f"{entry['period']}: missing required columns: {', '.join(missing)}")

        for source_csv_row_ordinal, values in enumerate(reader, start=2):
            total_rows += 1
            if len(values) != len(header):
                malformed_width_rows += 1
            padded = values[: len(header)] + [""] * max(0, len(header) - len(values))
            row = dict(zip(header, padded))
            if clean_cell(row.get("SORT SEQUENCE")).upper() != "DETAIL":
                continue
            detail_rows += 1
            if clean_cell(row.get("SORT SUBTOTAL DESCRIPTION")).upper() != "PERSONNEL COMPENSATION":
                continue

            payroll_rows += 1
            employing_office_raw = choose(row, "ORGANIZATION")
            employing_office_candidate, office_rule = office_candidate(employing_office_raw)
            payee = choose(row, "VENDOR NAME", "PAYEE")
            title = choose(row, "DESCRIPTION")
            start_raw = choose(row, "PERFORM START DT", "SERVICE START DATE")
            end_raw = choose(row, "PERFORM END DT", "SERVICE END DATE")
            start_iso, start_status = candidate_iso_date(start_raw)
            end_iso, end_status = candidate_iso_date(end_raw)
            unparsed_date_fields += int(start_status == "UNPARSED_RAW_DATE") + int(end_status == "UNPARSED_RAW_DATE")
            missing_payee_rows += int(not payee)
            missing_title_rows += int(not title)
            amount_raw = choose(row, "AMOUNT")
            negative_amount_rows += int(amount_raw.startswith("-") or (amount_raw.startswith("(") and amount_raw.endswith(")")))
            candidate_seed = f"{source_sha256}\0{source_csv_row_ordinal}\0{entry['period']}".encode("utf-8")
            candidate = {
                "amount_raw": amount_raw or None,
                "candidate_id": "house-sod-payroll:" + hashlib.sha256(candidate_seed).hexdigest(),
                "candidate_status": "UNVERIFIED_OFFICIAL_PAYROLL_ROW",
                "canonical_employing_office_id": None,
                "canonical_employment_episode_id": None,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_person_id": None,
                "canonical_service_end_date": None,
                "canonical_service_start_date": None,
                "employing_office_candidate": employing_office_candidate or None,
                "employing_office_candidate_rule": office_rule,
                "employing_office_raw": employing_office_raw or None,
                "payee_raw": payee or None,
                "period": entry["period"],
                "period_end": entry["period_end"],
                "period_start": entry["period_start"],
                "program_raw": choose(row, "PROGRAM") or None,
                "schema_id": SCHEMA_ID,
                "service_end_date_candidate_iso": end_iso,
                "service_end_date_parse_status": end_status,
                "service_end_date_raw": end_raw or None,
                "service_start_date_candidate_iso": start_iso,
                "service_start_date_parse_status": start_status,
                "service_start_date_raw": start_raw or None,
                "source_csv_row_ordinal": source_csv_row_ordinal,
                "source_csv_sha256": source_sha256,
                "source_url": entry["detail_csv_url"],
                "title_description_raw": title or None,
            }
            writer.write(compact_json(candidate) + "\n")

    return {
        "column_count": len(header),
        "header": header,
        "malformed_width_rows": malformed_width_rows,
        "missing_payee_rows": missing_payee_rows,
        "missing_title_description_rows": missing_title_rows,
        "negative_amount_rows": negative_amount_rows,
        "payroll_candidate_rows": payroll_rows,
        "source_csv_detail_rows": detail_rows,
        "source_csv_rows_excluding_header": total_rows,
        "unparsed_service_date_fields": unparsed_date_fields,
    }


def write_candidates(
    mode: str,
    entries: list[dict[str, Any]],
    sources: dict[str, tuple[Path, str, int]],
    output_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    output_path, _ = output_paths(output_dir, mode)
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(output_path.name + ".part")
    period_stats: list[dict[str, Any]] = []
    with temporary.open("wb") as raw_output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw_output, mtime=0, compresslevel=6) as compressor:
            with io.TextIOWrapper(compressor, encoding="utf-8", newline="\n") as writer:
                for entry in entries:
                    source_path, source_sha256, source_bytes = sources[entry["period"]]
                    stats = parse_period_to_output(entry, source_path, source_sha256, writer)
                    period_stats.append(
                        {
                            "bytes": source_bytes,
                            "detail_csv_url": entry["detail_csv_url"],
                            "period": entry["period"],
                            "sha256": source_sha256,
                            **stats,
                        }
                    )
    os.replace(temporary, output_path)
    return output_path, {"periods": period_stats}


def run_mode(args: argparse.Namespace, inventory: dict[str, Any], inventory_path: Path, pacer: SharedPacer) -> dict[str, Any]:
    available = [row for row in inventory["periods"] if row.get("detail_csv_url")]
    if args.mode == "sample":
        wanted = args.sample_periods or [available[0]["period"], available[-1]["period"]]
        wanted_set = set(wanted)
        entries = [row for row in available if row["period"] in wanted_set]
        missing = sorted(wanted_set - {row["period"] for row in entries})
        if missing:
            raise RuntimeError("Unknown sample periods: " + ", ".join(missing))
    else:
        entries = available

    raw_dir = args.output_dir / "raw_detail_csv"
    sources: dict[str, tuple[Path, str, int]] = {}
    runtime_download_states: dict[str, str] = {}
    for entry in entries:
        path, digest, byte_count, state = download_source(
            entry["period"], entry["detail_csv_url"], raw_dir, pacer, args.max_attempts
        )
        sources[entry["period"]] = (path, digest, byte_count)
        runtime_download_states[entry["period"]] = state
        print(compact_json({"bytes": byte_count, "download_state": state, "period": entry["period"], "sha256": digest}), flush=True)

    output_path, parsed = write_candidates(args.mode, entries, sources, args.output_dir)
    period_stats = parsed["periods"]
    candidate_rows = sum(row["payroll_candidate_rows"] for row in period_stats)
    receipt = {
        "acquisition_policy": {
            "authenticated_source_used": False,
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "canonical_merges_performed": 0,
            "completed_source_cache_policy": "IMMUTABLE_REUSE; NO CACHE CLEARING",
            "download_concurrency": 1,
            "minimum_request_interval_seconds": args.minimum_request_interval,
            "pdf_fallback_used": False,
            "source_scope": "OFFICIAL_HOUSE_GOV_ONLY",
        },
        "counts": {
            "candidate_rows": candidate_rows,
            "malformed_width_rows": sum(row["malformed_width_rows"] for row in period_stats),
            "missing_payee_rows": sum(row["missing_payee_rows"] for row in period_stats),
            "missing_title_description_rows": sum(row["missing_title_description_rows"] for row in period_stats),
            "negative_amount_rows": sum(row["negative_amount_rows"] for row in period_stats),
            "source_csv_detail_rows": sum(row["source_csv_detail_rows"] for row in period_stats),
            "source_csv_rows_excluding_headers": sum(row["source_csv_rows_excluding_header"] for row in period_stats),
            "source_periods": len(period_stats),
            "unparsed_service_date_fields": sum(row["unparsed_service_date_fields"] for row in period_stats),
        },
        "inventory": {
            "path": inventory_path.name,
            "sha256": sha256_file(inventory_path),
        },
        "mode": args.mode.upper(),
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": candidate_rows,
            "sha256": sha256_file(output_path),
        },
        "periods": period_stats,
        "risk_notes": [
            "Each row is an unverified official payroll candidate; a payee string is not a canonical person identity.",
            "Service dates describe the coverage of a disbursement and must not be treated as complete employment-tenure boundaries.",
            "Repeated payee strings and repeated service periods are retained; no cross-row or cross-quarter identity merge or deduplication is performed.",
            "Titles and office names are raw House fields and may be abbreviated, truncated, corrected later, or reflect accounting conventions.",
            "A leading four-digit report year is removed only in the separate employing_office_candidate field; the exact raw office field is retained.",
            "Negative payroll adjustments and rows with missing fields are retained and counted rather than silently discarded.",
            "The finite lane begins with 2016Q1 because official structured detail CSV publication began in 2016; earlier PDF extraction is outside this run.",
        ],
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS",
        "validation": {
            "all_candidate_ids_unique_by_source_row": True,
            "canonical_employment_episode_promotions": 0,
            "canonical_identity_promotions": 0,
            "canonical_office_promotions": 0,
            "canonical_service_date_promotions": 0,
            "input_period_order_preserved": True,
            "payroll_filter": "SORT SEQUENCE == DETAIL AND SORT SUBTOTAL DESCRIPTION == PERSONNEL COMPENSATION",
        },
    }
    _, receipt_path = output_paths(args.output_dir, args.mode)
    write_json_atomic(receipt_path, receipt)
    return {
        "download_states": runtime_download_states,
        "receipt": receipt,
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("inventory", "sample", "full"), default="sample")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--archive-url", default=ARCHIVE_URL)
    parser.add_argument("--current-url", default=CURRENT_URL)
    parser.add_argument("--minimum-request-interval", type=float, default=2.0)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--refresh-inventory", action="store_true")
    parser.add_argument("--sample-period", dest="sample_periods", action="append")
    args = parser.parse_args(argv)
    if args.minimum_request_interval < 1.0:
        parser.error("--minimum-request-interval must be at least 1.0 second")
    if args.max_attempts < 1:
        parser.error("--max-attempts must be positive")
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    started = time.perf_counter()
    pacer = SharedPacer(args.minimum_request_interval)
    inventory, inventory_path = load_or_create_inventory(args, pacer)
    if args.mode == "inventory":
        print(
            compact_json(
                {
                    "inventory": str(inventory_path),
                    "inventory_sha256": sha256_file(inventory_path),
                    "period_coverage": inventory["coverage"],
                }
            )
        )
        return 0
    result = run_mode(args, inventory, inventory_path, pacer)
    result["runtime_seconds"] = round(time.perf_counter() - started, 6)
    print(compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
