#!/usr/bin/env python3
"""Probe govinfo content endpoints for the 2009-2011 payroll backfill targets.

The CDOC sitemap enumeration proved insufficient as NEGATIVE evidence: the
Report of the Secretary of the Senate packages that are demonstrably on govinfo
and already on disk (GPO-CDOC-112sdoc4/7/10) are absent from every CDOC year
sitemap, while their neighbours (CDOC-112sdoc1/3/5/6/11/12) are present.  The
payroll documents therefore live under the `GPO-CDOC-` prefix and are excluded
from the sitemap, so package existence must be settled by a direct content
probe.

Each probe is a single GET carrying `Range: bytes=0-8191`, so a hit costs 8 KB
rather than 15 MB while still proving the body is a real PDF (%PDF magic) and
reporting the document's true length from Content-Range.  A 404/403 is recorded
as the outcome; nothing is retried past the configured attempt budget and no
challenge is ever bypassed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "corpus_backfill_2009_raw"
SCHEMA_ID = "staffer-network-corpus-backfill-2009-endpoint-probe-v1"
USER_AGENT = (
    "MelangeSystemsPayrollBackfill/1.0 "
    "(official-public-data research; sequential paced GET only)"
)

# (label, chamber, period_start, period_end, doc_stub, part_suffixes)
TARGETS = [
    ("senate_2008-10", "senate", "2008-10-01", "2009-03-31", "111sdoc2", ("1", "2")),
    ("senate_2009-04", "senate", "2009-04-01", "2009-09-30", "111sdoc8", ("1", "2")),
    ("senate_2009-10", "senate", "2009-10-01", "2010-03-31", "111sdoc12", ("1", "2")),
    ("senate_2010-04", "senate", "2010-04-01", "2010-09-30", "111sdoc17", ("1", "2")),
    ("house_2009Q1", "house", "2009-01-01", "2009-03-31", "111hdoc26", ("1", "2", "3")),
    ("house_2009Q2", "house", "2009-04-01", "2009-06-30", "111hdoc56", ("1", "2", "3")),
    # Positive control: known-present package, already on disk from the shipped lane.
    ("CONTROL_senate_2011-04", "senate", "2011-04-01", "2011-09-30", "112sdoc4", ("1", "2")),
    # Negative control: a stub that should not exist in either prefix.
    ("CONTROL_absent", "senate", None, None, "111sdoc9999", ()),
]
PREFIXES = ("GPO-CDOC-", "CDOC-")


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


CHALLENGE_MARKERS = (b"captcha", b"unusual traffic", b"are you a robot",
                     b"cf-browser-verification", b"just a moment")


def probe(url: str, pacer: HostPacer, receipts: list[dict[str, Any]],
          timeout: int = 120) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc
    pacer.wait(host)
    started = time.monotonic()
    headers = {"User-Agent": USER_AGENT, "Accept": "application/pdf,*/*;q=0.1",
               "Range": "bytes=0-8191"}
    record: dict[str, Any] = {
        "url": url, "fetched_utc": utc_now(), "host": host, "http_status": None,
        "bytes": 0, "sha256_prefix8k": None, "content_type": None,
        "content_range": None, "content_length": None, "error": None,
        "is_pdf": False, "challenge_suspected": False,
    }
    body = b""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            body = response.read()
            record["http_status"] = response.status
            record["content_type"] = response.headers.get("Content-Type", "")
            record["content_range"] = response.headers.get("Content-Range")
            record["content_length"] = response.headers.get("Content-Length")
    except urllib.error.HTTPError as exc:
        record["http_status"] = exc.code
        record["error"] = f"HTTPError {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["bytes"] = len(body)
    record["duration_ms"] = int((time.monotonic() - started) * 1000)
    if body:
        record["sha256_prefix8k"] = sha256_bytes(body)
        record["is_pdf"] = body[:4] == b"%PDF"
        low = body[:4096].lower()
        record["challenge_suspected"] = any(m in low for m in CHALLENGE_MARKERS)
    if record["content_range"]:
        tail = record["content_range"].rsplit("/", 1)[-1]
        record["full_bytes"] = int(tail) if tail.isdigit() else None
    receipts.append(dict(record))
    print(f"  {record['http_status']} pdf={record['is_pdf']} "
          f"full={record.get('full_bytes')} {url}", flush=True)
    return record


def content_url(prefix: str, stub: str, suffix: str | None) -> str:
    pkg = f"{prefix}{stub}"
    leaf = pkg if suffix is None else f"{pkg}-{suffix}"
    return f"https://www.govinfo.gov/content/pkg/{pkg}/pdf/{leaf}.pdf"


def run(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    pacer = HostPacer(args.minimum_interval_seconds)
    results: list[dict[str, Any]] = []

    for label, chamber, period_start, period_end, stub, parts in TARGETS:
        print(f"[{label}] {stub}")
        entry: dict[str, Any] = {
            "label": label, "chamber": chamber, "period_start": period_start,
            "period_end": period_end, "doc_stub": stub, "resolved_prefix": None,
            "full_report": None, "parts": [], "outcome": "NOT_FOUND",
        }
        for prefix in PREFIXES:
            record = probe(content_url(prefix, stub, None), pacer, receipts)
            if record["is_pdf"]:
                entry["resolved_prefix"] = prefix
                entry["full_report"] = {
                    "url": record["url"], "full_bytes": record.get("full_bytes"),
                    "http_status": record["http_status"],
                }
                entry["outcome"] = "FULL_REPORT_AVAILABLE"
                break
            if record["challenge_suspected"]:
                entry["outcome"] = "CHALLENGE_ENCOUNTERED"
                break
        if entry["outcome"] == "CHALLENGE_ENCOUNTERED":
            results.append(entry)
            continue
        prefixes_for_parts = (entry["resolved_prefix"],) if entry["resolved_prefix"] else PREFIXES
        for prefix in prefixes_for_parts:
            part_hits = []
            for suffix in parts:
                record = probe(content_url(prefix, stub, suffix), pacer, receipts)
                if record["is_pdf"]:
                    part_hits.append({"suffix": suffix, "url": record["url"],
                                      "full_bytes": record.get("full_bytes")})
                elif record["challenge_suspected"]:
                    entry["outcome"] = "CHALLENGE_ENCOUNTERED"
                    break
            if part_hits:
                entry["resolved_prefix"] = entry["resolved_prefix"] or prefix
                entry["parts"] = part_hits
                if entry["outcome"] != "FULL_REPORT_AVAILABLE":
                    entry["outcome"] = "PARTS_ONLY_AVAILABLE"
                break
        results.append(entry)

    payload = {
        "schema_id": SCHEMA_ID,
        "generated_utc": utc_now(),
        "minimum_interval_seconds": args.minimum_interval_seconds,
        "targets": results,
        "request_receipts": receipts,
    }
    write_json_atomic(output_dir / "govinfo_endpoint_probe.json", payload)
    print("\nSUMMARY")
    for entry in results:
        parts = ",".join(p["suffix"] for p in entry["parts"]) or "-"
        print(f"  {entry['label']:24s} {entry['doc_stub']:14s} {entry['outcome']:26s} "
              f"prefix={entry['resolved_prefix']} parts={parts}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.2)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
