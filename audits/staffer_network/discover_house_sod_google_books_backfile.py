#!/usr/bin/env python3
"""Discover public Google Books scans for the pre-web House SOD backfile.

This is a metadata/discovery stage only.  It reads public Google Play Books
search pages without authentication, preserves the response bytes, and maps
only titles whose period and part are explicit.  It does not promote any
identity or employment fact.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request


SCHEMA_ID = "staffer-network-house-sod-preweb-google-books-discovery-v1"
SEARCH_URL = "https://play.google.com/store/search"
BOOK_RE = re.compile(
    r'\[\["(?P<id>[A-Za-z0-9_-]{12})",9\],'
    r'\[null,3,\[\d+,\d+\],.*?\[0,0,0,255\]\],null,'
    r'"(?P<title>(?:\\.|[^"\\])*)"',
    re.DOTALL,
)
PERIOD_RE = re.compile(
    r"\bfrom\s+"
    r"(?P<start_month>January|April|July|October)\s+1,\s+(?P<start_year>\d{4})\s+"
    r"to\s+(?P<end_month>March|June|September|December)\s+"
    r"(?:30|31),\s+(?P<end_year>\d{4}),\s+Part\s+(?P<part>\d+)\b",
    re.IGNORECASE,
)
QUARTER_BY_MONTH = {"january": 1, "april": 2, "july": 3, "october": 4}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def download_search(query: str, path: Path, minimum_interval: float, state: dict[str, float]) -> str:
    if path.exists() and path.stat().st_size:
        return "REUSED_COMPLETE_CACHE"
    delay = minimum_interval - (time.monotonic() - state["last_request"])
    if delay > 0:
        time.sleep(delay)
    url = SEARCH_URL + "?" + urllib.parse.urlencode({"q": query, "c": "books"})
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; MelangeResearch/1.0)"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    state["last_request"] = time.monotonic()
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)
    return "DOWNLOADED_PUBLIC_UNAUTHENTICATED"


def parse_books(payload: str, search_key: str) -> list[dict[str, object]]:
    rows = []
    seen = set()
    for match in BOOK_RE.finditer(payload):
        book_id = match.group("id")
        title = json.loads('"' + match.group("title") + '"')
        if book_id in seen or "Statement of Disbursements of the House" not in title:
            continue
        seen.add(book_id)
        period_match = PERIOD_RE.search(title)
        period = None
        part = None
        if period_match and period_match.group("start_year") == period_match.group("end_year"):
            year = int(period_match.group("start_year"))
            quarter = QUARTER_BY_MONTH[period_match.group("start_month").lower()]
            period = f"{year}Q{quarter}"
            part = int(period_match.group("part"))
        rows.append(
            {
                "book_id": book_id,
                "download_url_template": (
                    f"https://books.google.com/books/download?id={book_id}&output=pdf"
                ),
                "metadata_url": f"https://play.google.com/store/books/details?id={book_id}",
                "part": part,
                "period": period,
                "title": title,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-request-interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.minimum_request_interval < 1.0:
        parser.error("minimum request interval must be at least one second")
    output_dir = args.output_dir.resolve()
    cache_dir = output_dir / "raw_google_play_search"
    cache_dir.mkdir(parents=True, exist_ok=True)

    state = {"last_request": -10_000.0}
    search_receipts = []
    candidates_by_id: dict[str, dict[str, object]] = {}
    expected_periods = [f"{year}Q{quarter}" for year in range(1996, 2009) for quarter in range(1, 5)]
    quarter_dates = {
        1: ("January 1", "March 31"),
        2: ("April 1", "June 30"),
        3: ("July 1", "September 30"),
        4: ("October 1", "December 31"),
    }
    for period in expected_periods:
        year = int(period[:4])
        quarter = int(period[-1])
        start_date, end_date = quarter_dates[quarter]
        query = (
            f'"Statement of Disbursements of the House" '
            f'"{start_date}, {year}" "{end_date}, {year}"'
        )
        path = cache_dir / f"statement_of_disbursements_{period.lower()}.html"
        download_state = download_search(query, path, args.minimum_request_interval, state)
        parsed = parse_books(path.read_text(encoding="utf-8"), period)
        for row in parsed:
            existing = candidates_by_id.setdefault(row["book_id"], row)
            if existing != row:
                raise RuntimeError(f"conflicting metadata for Google Books id {row['book_id']}")
        search_receipts.append(
            {
                "bytes": path.stat().st_size,
                "download_state": download_state,
                "parsed_statement_book_candidates": len(parsed),
                "path": str(path.relative_to(output_dir)),
                "search_key": period,
                "sha256": sha256_file(path),
            }
        )

    candidates = sorted(
        candidates_by_id.values(),
        key=lambda row: (
            row["period"] is None,
            row["period"] or "",
            row["part"] or 0,
            row["book_id"],
        ),
    )
    target_candidates = [
        row
        for row in candidates
        if row["period"] is not None and "1996Q1" <= row["period"] <= "2008Q4"
    ]
    by_period: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in target_candidates:
        by_period[str(row["period"])].append(row)
    missing_periods = [period for period in expected_periods if period not in by_period]

    result = {
        "counts": {
            "all_unique_statement_book_candidates": len(candidates),
            "expected_periods": len(expected_periods),
            "missing_periods": len(missing_periods),
            "search_pages": len(search_receipts),
            "target_book_candidates": len(target_candidates),
            "target_periods_with_candidates": len(by_period),
        },
        "expected_periods": expected_periods,
        "missing_periods": missing_periods,
        "schema_id": SCHEMA_ID,
        "search_receipts": search_receipts,
        "status": "PASS_DISCOVERY_COMPLETE" if not missing_periods else "PARTIAL_DISCOVERY",
        "target_candidates": target_candidates,
        "validation": {
            "authentication_used": False,
            "cache_clearing_used": False,
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "minimum_request_interval_seconds": args.minimum_request_interval,
        },
    }
    output_path = output_dir / "google_books_backfile_discovery.json"
    output_path.write_bytes(canonical_bytes(result))
    print(json.dumps({**result["counts"], "output_sha256": sha256_file(output_path), "status": result["status"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
