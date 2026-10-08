#!/usr/bin/env python3
"""Last untested official route: the govinfo SERIALSET collection.

The 2009-2010 payroll documents are bound Serial Set volumes (S.Doc 111-2 =
serials 15212-15213, S.Doc 111-8 = 15216-15217, H.Doc 111-26 = 15246-15248,
H.Doc 111-56 = 15260-15262).  govinfo's robots.txt advertises
SERIALSET_sitemap_index.xml, so if GPO's Serial Set digitisation reaches the
111th Congress these documents are reachable there even though they are absent
from CDOC.  This settles the question rather than assuming.

GET only, sequential, paced.
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
SCHEMA_ID = "staffer-network-corpus-backfill-2009-serialset-route-v1"
INDEX_URL = "https://www.govinfo.gov/sitemap/SERIALSET_sitemap_index.xml"
USER_AGENT = (
    "MelangeSystemsPayrollBackfill/1.0 "
    "(official-public-data research; sequential paced GET only)"
)
TARGET_SERIALS = {
    "15212": "S.Doc 111-2 pt.1 (Senate report 2008-10-01..2009-03-31)",
    "15213": "S.Doc 111-2 pt.2",
    "15216": "S.Doc 111-8 pt.1 (Senate report 2009-04-01..2009-09-30)",
    "15217": "S.Doc 111-8 pt.2",
    "15246": "H.Doc 111-26 pt.1 (House SOD 2009Q1)",
    "15247": "H.Doc 111-26 pt.2",
    "15248": "H.Doc 111-26 pt.3",
    "15260": "H.Doc 111-56 pt.1 (House SOD 2009Q2)",
    "15261": "H.Doc 111-56 pt.2",
    "15262": "H.Doc 111-56 pt.3",
}


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
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                         encoding="utf-8")
    os.replace(temporary, path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


def get(url: str, pacer: HostPacer, accept: str, receipts: list[dict[str, Any]],
        timeout: int = 120) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc
    pacer.wait(host)
    started = time.monotonic()
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    record: dict[str, Any] = {"url": url, "fetched_utc": utc_now(), "host": host,
                              "http_status": None, "bytes": 0, "sha256": None, "error": None}
    body = b""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            body = response.read()
            record["http_status"] = response.status
    except urllib.error.HTTPError as exc:
        record["http_status"] = exc.code
        record["error"] = f"HTTPError {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    record["bytes"] = len(body)
    record["duration_ms"] = int((time.monotonic() - started) * 1000)
    if body:
        record["sha256"] = sha256_bytes(body)
    receipts.append(dict(record))
    print(f"  {record['http_status']} {record['bytes']}B {url} {record['error'] or ''}", flush=True)
    record["body"] = body
    return record


def run(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    pacer = HostPacer(args.minimum_interval_seconds)

    record = get(INDEX_URL, pacer, "application/xml,text/xml,*/*;q=0.1", receipts)
    body = record["body"] or b""
    if not body:
        write_json_atomic(output_dir / "serialset_route.json",
                          {"schema_id": SCHEMA_ID, "outcome": "INDEX_FETCH_FAILED",
                           "request_receipts": receipts})
        return 1
    write_bytes_atomic(raw_dir / "SERIALSET_sitemap_index.xml", body)
    text = body.decode("utf-8", errors="replace")
    children = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", text)
    years = sorted({m.group(1) for c in children for m in [re.search(r"_(\d{4})_", c)] if m})
    print(f"SERIALSET sitemaps: {len(children)}; years {years[:5]}..{years[-5:] if years else []}")

    # Only walk year sitemaps that could plausibly carry 111th-Congress volumes.
    plausible = [c for c in children if any(y in c for y in ("2009", "2010", "2011", "2012"))]
    print(f"plausible year sitemaps: {plausible}")
    serial_hits: dict[str, list[str]] = {}
    walked: list[dict[str, Any]] = []
    for url in plausible:
        name = Path(urllib.parse.urlparse(url).path).name
        local = raw_dir / name
        if local.exists():
            payload = local.read_bytes()
        else:
            child = get(url, pacer, "application/xml,text/xml,*/*;q=0.1", receipts)
            payload = child["body"] or b""
            if not payload:
                walked.append({"url": url, "outcome": "FETCH_FAILED"})
                continue
            write_bytes_atomic(local, payload)
        child_text = payload.decode("utf-8", errors="replace")
        locs = re.findall(r"<loc>\s*([^<]+?)\s*</loc>", child_text)
        for serial in TARGET_SERIALS:
            matched = [loc for loc in locs if serial in loc]
            if matched:
                serial_hits.setdefault(serial, []).extend(matched)
        walked.append({"url": url, "name": name, "loc_count": len(locs),
                       "bytes": len(payload), "sha256": sha256_bytes(payload),
                       "sample_loc": locs[0] if locs else None})

    outcome = "SERIALS_FOUND" if serial_hits else "NO_TARGET_SERIALS_IN_SERIALSET"
    write_json_atomic(output_dir / "serialset_route.json", {
        "schema_id": SCHEMA_ID, "generated_utc": utc_now(), "index_url": INDEX_URL,
        "index_sha256": sha256_bytes(body), "index_child_count": len(children),
        "index_children": children, "index_years": years,
        "walked_sitemaps": walked, "target_serials": TARGET_SERIALS,
        "serial_hits": serial_hits, "outcome": outcome,
        "request_receipts": receipts,
    })
    print(f"OUTCOME {outcome}; hits={list(serial_hits)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.2)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
