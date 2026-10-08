#!/usr/bin/env python3
"""Confirm that the 2009-2010 payroll packages are absent, not mis-addressed.

The endpoint probe returned HTTP 200 with a non-PDF body (the govinfo Angular
shell) for every 2009-2010 target, matching the NEGATIVE control
(GPO-CDOC-111sdoc9999) exactly and differing from the POSITIVE control
(GPO-CDOC-112sdoc4, 206 + %PDF + 14,630,781 bytes).  That already implicates
absence, but two alternative explanations remain and are tested here:

1. Leaf-naming artifact - the legacy `CDOC-` packages might not expose a
   `<pkg>.pdf` leaf at all.  Tested by probing NEIGHBOUR packages that the CDOC
   sitemap positively lists (CDOC-111hdoc25, CDOC-111hdoc27, CDOC-111sdoc7).
   If those neighbours return %PDF at the identical URL shape, the shape is
   right and the target's absence is real.
2. Chamber-site publication - the House Clerk / house.gov archive might list the
   2009Q1-Q2 statements even though govinfo does not.  Tested by re-fetching the
   live Statement of Disbursements archive index and enumerating its periods.

GET only, sequential, paced.  No bypasses.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html.parser
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
SCHEMA_ID = "staffer-network-corpus-backfill-2009-absence-confirmation-v1"
USER_AGENT = (
    "MelangeSystemsPayrollBackfill/1.0 "
    "(official-public-data research; sequential paced GET only)"
)
HOUSE_ARCHIVE_URL = (
    "https://www.house.gov/the-house-explained/open-government/"
    "statement-of-disbursements/archive"
)
HOUSE_SOD_URL = (
    "https://www.house.gov/the-house-explained/open-government/statement-of-disbursements"
)
SENATE_ARCHIVE_URL = "https://www.senate.gov/legislative/common/generic/report_secsen.htm"

# Packages the CDOC sitemap positively lists, immediately adjacent to the
# targets.  These calibrate the URL shape.
NEIGHBOUR_CONTROLS = [
    ("CDOC-111hdoc25", "neighbour of the 2009Q1 House SOD (hdoc26)"),
    ("CDOC-111hdoc27", "neighbour of the 2009Q1 House SOD (hdoc26)"),
    ("CDOC-111sdoc7", "neighbour of the 2009-04 Senate report (sdoc8)"),
    ("CDOC-111sdoc10", "neighbour of the 2009-04 Senate report (sdoc8)"),
]
TARGETS_RECHECK = [
    ("CDOC-111hdoc26", "House SOD 2009Q1"),
    ("CDOC-111sdoc8", "Senate report 2009-04"),
]
YEAR_QUARTER_RE = re.compile(r"(19|20)\d{2}\s*Q[1-4]", re.IGNORECASE)


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


class AnchorCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a" or self._href is not None:
            return
        values = dict(attrs)
        if values.get("href"):
            self._href = values["href"]
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


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


CHALLENGE_MARKERS = (b"captcha", b"unusual traffic", b"are you a robot",
                     b"cf-browser-verification", b"just a moment")


def get(url: str, pacer: HostPacer, accept: str, receipts: list[dict[str, Any]],
        range_header: str | None = None, timeout: int = 120) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc
    pacer.wait(host)
    started = time.monotonic()
    headers = {"User-Agent": USER_AGENT, "Accept": accept}
    if range_header:
        headers["Range"] = range_header
    record: dict[str, Any] = {
        "url": url, "fetched_utc": utc_now(), "host": host, "http_status": None,
        "bytes": 0, "sha256": None, "content_type": None, "content_range": None,
        "full_bytes": None, "error": None, "is_pdf": False,
        "challenge_suspected": False,
    }
    body = b""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=timeout) as response:
            body = response.read()
            record["http_status"] = response.status
            record["content_type"] = response.headers.get("Content-Type", "")
            record["content_range"] = response.headers.get("Content-Range")
    except urllib.error.HTTPError as exc:
        record["http_status"] = exc.code
        record["error"] = f"HTTPError {exc.code} {exc.reason}"
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    record["bytes"] = len(body)
    record["duration_ms"] = int((time.monotonic() - started) * 1000)
    if body:
        record["sha256"] = sha256_bytes(body)
        record["is_pdf"] = body[:4] == b"%PDF"
        record["challenge_suspected"] = any(m in body[:4096].lower() for m in CHALLENGE_MARKERS)
    if record["content_range"]:
        tail = record["content_range"].rsplit("/", 1)[-1]
        record["full_bytes"] = int(tail) if tail.isdigit() else None
    receipts.append({k: v for k, v in record.items()})
    print(f"  {record['http_status']} pdf={record['is_pdf']} bytes={record['bytes']} "
          f"full={record['full_bytes']} {url}", flush=True)
    record["body"] = body
    return record


def run(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    pacer = HostPacer(args.minimum_interval_seconds)

    print("URL-SHAPE CALIBRATION (sitemap-listed neighbours)")
    shape: list[dict[str, Any]] = []
    for pkg, note in NEIGHBOUR_CONTROLS + TARGETS_RECHECK:
        url = f"https://www.govinfo.gov/content/pkg/{pkg}/pdf/{pkg}.pdf"
        record = get(url, pacer, "application/pdf,*/*;q=0.1", receipts, "bytes=0-8191")
        shape.append({
            "package_id": pkg, "note": note, "url": url,
            "http_status": record["http_status"], "is_pdf": record["is_pdf"],
            "full_bytes": record["full_bytes"], "bytes": record["bytes"],
            "sha256_prefix8k": record["sha256"],
            "challenge_suspected": record["challenge_suspected"],
            "role": "SITEMAP_LISTED_NEIGHBOUR" if (pkg, note) in NEIGHBOUR_CONTROLS else "TARGET",
        })

    print("CHAMBER-SITE PUBLICATION CHECK")
    chamber: dict[str, Any] = {}
    for name, url in (("house_sod_archive", HOUSE_ARCHIVE_URL),
                      ("house_sod_current", HOUSE_SOD_URL),
                      ("senate_secsen_index", SENATE_ARCHIVE_URL)):
        record = get(url, pacer, "text/html,*/*;q=0.1", receipts)
        body = record["body"] or b""
        if body:
            write_bytes_atomic(raw_dir / f"{name}.html", body)
        parser = AnchorCollector()
        parser.feed(body.decode("utf-8", errors="replace"))
        pdf_anchors = [(h, t) for h, t in parser.anchors
                       if urllib.parse.urlparse(h).path.lower().endswith((".pdf", ".csv", ".zip"))]
        periods = sorted({m.group(0).upper().replace(" ", "")
                          for h, t in parser.anchors
                          for m in [YEAR_QUARTER_RE.search(f"{h} {t}")] if m})
        chamber[name] = {
            "url": url, "http_status": record["http_status"], "bytes": record["bytes"],
            "sha256": record["sha256"], "challenge_suspected": record["challenge_suspected"],
            "anchor_count": len(parser.anchors), "document_anchor_count": len(pdf_anchors),
            "detected_periods": periods,
            "earliest_detected_period": periods[0] if periods else None,
            "mentions_2009q1": any("2009Q1" in p for p in periods),
            "mentions_2009q2": any("2009Q2" in p for p in periods),
        }
        print(f"  {name}: {len(periods)} periods, earliest={periods[0] if periods else None}")

    verdict = {
        "url_shape_valid": all(row["is_pdf"] for row in shape
                               if row["role"] == "SITEMAP_LISTED_NEIGHBOUR"),
        "targets_absent": all(not row["is_pdf"] for row in shape if row["role"] == "TARGET"),
        "any_challenge": any(row["challenge_suspected"] for row in shape)
        or any(v["challenge_suspected"] for v in chamber.values()),
    }
    write_json_atomic(output_dir / "absence_confirmation.json", {
        "schema_id": SCHEMA_ID, "generated_utc": utc_now(),
        "url_shape_calibration": shape, "chamber_sites": chamber,
        "verdict": verdict, "request_receipts": receipts,
    })
    print("\nVERDICT", json.dumps(verdict))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.2)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
