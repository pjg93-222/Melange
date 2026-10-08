#!/usr/bin/env python3
"""Enumerate govinfo CDOC packages for 2009-2011 from the public sitemaps.

robots.txt on www.govinfo.gov advertises
https://www.govinfo.gov/sitemap/CDOC_sitemap_index.xml and disallows none of
/sitemap/, /content/ or /metadata/.  Walking the index gives an authoritative
list of every Congressional Document package govinfo holds per year, which
settles - without guessing identifiers - whether the Report of the Secretary of
the Senate and the House Statement of Disbursements for the missing periods are
published online at all.

GET only, sequential, paced per host.  Nothing bypassed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "corpus_backfill_2009_raw"
SCHEMA_ID = "staffer-network-corpus-backfill-2009-cdoc-sitemap-v1"
INDEX_URL = "https://www.govinfo.gov/sitemap/CDOC_sitemap_index.xml"
USER_AGENT = (
    "MelangeSystemsPayrollBackfill/1.0 "
    "(official-public-data research; sequential paced GET only)"
)
TARGET_YEARS = ("2008", "2009", "2010", "2011", "2012")
PKG_RE = re.compile(r"GPO-CDOC-(\d+)(sdoc|hdoc)(\d+)", re.IGNORECASE)


class HostPacer:
    def __init__(self, interval_seconds: float) -> None:
        self.interval_seconds = interval_seconds
        self._last: dict[str, float] = {}

    def wait(self, host: str) -> None:
        previous = self._last.get(host)
        if previous is not None:
            remaining = self.interval_seconds - (time.monotonic() - previous)
            if remaining > 0:
                time.sleep(remaining)
        self._last[host] = time.monotonic()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def fetch(url: str, pacer: HostPacer, accept: str, receipts: list[dict[str, Any]],
          extra_headers: dict[str, str] | None = None, timeout: int = 180) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc
    pacer.wait(host)
    started = time.monotonic()
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if extra_headers:
        headers.update(extra_headers)
    record: dict[str, Any] = {
        "url": url, "fetched_utc": utc_now(), "host": host, "http_status": None,
        "bytes": 0, "sha256": None, "content_type": None, "error": None,
        "request_headers": {k: v for k, v in headers.items() if k != "User-Agent"},
    }
    body = b""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            body = response.read()
            record["http_status"] = response.status
            record["content_type"] = response.headers.get("Content-Type", "")
            record["content_length_header"] = response.headers.get("Content-Length")
            record["content_range_header"] = response.headers.get("Content-Range")
    except urllib.error.HTTPError as exc:
        record["http_status"] = exc.code
        record["error"] = f"HTTPError {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["bytes"] = len(body)
    record["duration_ms"] = int((time.monotonic() - started) * 1000)
    if body:
        record["sha256"] = sha256_bytes(body)
        record["magic"] = body[:8].hex()
    receipts.append(dict(record))
    print(f"GET {url} -> {record['http_status']} {record['bytes']}B {record['error'] or ''}", flush=True)
    record["body"] = body
    return record


def maybe_gunzip(body: bytes) -> bytes:
    if body[:2] == b"\x1f\x8b":
        return gzip.decompress(body)
    return body


def run(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    pacer = HostPacer(args.minimum_interval_seconds)

    index_path = raw_dir / "CDOC_sitemap_index.xml"
    if index_path.exists():
        index_body = index_path.read_bytes()
        print(f"REUSED {index_path}")
    else:
        record = fetch(INDEX_URL, pacer, "application/xml,text/xml,*/*;q=0.1", receipts)
        index_body = maybe_gunzip(record["body"])
        if not index_body:
            write_json_atomic(output_dir / "cdoc_sitemap_discovery.json",
                              {"schema_id": SCHEMA_ID, "error": "index fetch failed",
                               "request_receipts": receipts})
            return 1
        write_bytes_atomic(index_path, index_body)

    index_text = index_body.decode("utf-8", errors="replace")
    child_urls = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", index_text)
    print(f"INDEX children: {len(child_urls)}")
    targets = [u for u in child_urls if any(y in u for y in TARGET_YEARS)]
    print(f"TARGET year sitemaps: {targets}")

    packages: dict[str, dict[str, Any]] = {}
    year_stats: list[dict[str, Any]] = []
    for url in targets:
        name = Path(urllib.parse.urlparse(url).path).name
        local = raw_dir / name
        if local.exists():
            body = local.read_bytes()
            print(f"REUSED {local}")
        else:
            record = fetch(url, pacer, "application/xml,text/xml,*/*;q=0.1", receipts)
            body = maybe_gunzip(record["body"])
            if not body:
                year_stats.append({"url": url, "outcome": "FETCH_FAILED"})
                continue
            write_bytes_atomic(local, body)
        text = body.decode("utf-8", errors="replace")
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", text)
        count = 0
        for loc in locs:
            match = PKG_RE.search(loc)
            if not match:
                continue
            pkg = f"GPO-CDOC-{match.group(1)}{match.group(2).lower()}{match.group(3)}"
            count += 1
            packages.setdefault(pkg, {
                "package_id": pkg,
                "congress": int(match.group(1)),
                "doc_type": match.group(2).lower(),
                "doc_number": int(match.group(3)),
                "sitemap": name,
                "detail_url": loc,
            })
        year_stats.append({"url": url, "name": name, "loc_count": len(locs),
                           "cdoc_package_count": count,
                           "sha256": sha256_bytes(body), "bytes": len(body)})

    by_congress: dict[int, list[str]] = {}
    for pkg, row in packages.items():
        by_congress.setdefault(row["congress"], []).append(pkg)
    summary = {
        congress: {
            "count": len(pkgs),
            "sdoc_numbers": sorted(packages[p]["doc_number"] for p in pkgs
                                   if packages[p]["doc_type"] == "sdoc"),
            "hdoc_numbers": sorted(packages[p]["doc_number"] for p in pkgs
                                   if packages[p]["doc_type"] == "hdoc"),
        }
        for congress, pkgs in sorted(by_congress.items())
    }

    wanted = ["GPO-CDOC-111sdoc2", "GPO-CDOC-111sdoc8", "GPO-CDOC-111hdoc26",
              "GPO-CDOC-111hdoc56", "GPO-CDOC-112sdoc4"]
    presence = {pkg: pkg in packages for pkg in wanted}
    print("WANTED PRESENCE:", json.dumps(presence))
    print("CONGRESS SUMMARY:", json.dumps({str(k): v["count"] for k, v in summary.items()}))

    write_json_atomic(output_dir / "cdoc_sitemap_discovery.json", {
        "schema_id": SCHEMA_ID,
        "generated_utc": utc_now(),
        "index_url": INDEX_URL,
        "index_sha256": sha256_bytes(index_body),
        "index_child_count": len(child_urls),
        "index_children": child_urls,
        "target_sitemaps": year_stats,
        "package_count": len(packages),
        "packages": sorted(packages.values(), key=lambda r: (r["congress"], r["doc_type"], r["doc_number"])),
        "congress_summary": {str(k): v for k, v in summary.items()},
        "wanted_presence": presence,
        "request_receipts": receipts,
    })
    print(f"WROTE {output_dir / 'cdoc_sitemap_discovery.json'}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.2)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
