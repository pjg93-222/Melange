#!/usr/bin/env python3
"""Discovery for the 2009-2011 payroll corpus backfill.

Locates, but does not yet mass-download, the official source documents for the
periods missing from the two shipped payroll corpora:

* Senate Report of the Secretary of the Senate - periods starting 2008-10,
  2009-04, 2009-10, 2010-04 and 2010-10 (the shipped archive opens 2011-04-01).
* House Statement of Disbursements - 2009Q1 and 2009Q2 (the shipped ledger
  opens 2009Q3).

Method: the GPO Serial Set preliminary session-volume schedules
(https://www.govinfo.gov/media/<congress>-<session>se.pdf) name every Senate and
House Document printed in a session, including the document NUMBER.  That number
maps directly onto a govinfo CDOC package identifier
(GPO-CDOC-<congress><sdoc|hdoc><number>), whose existence and PDF endpoints are
then probed via the static metadata endpoint.

Every request is GET, sequential, and paced at >= the configured interval per
host.  Nothing is bypassed: a non-200 or a non-PDF/non-XML body is recorded as
the outcome and the route stops.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "corpus_backfill_2009_raw"
DISCOVERY_SCHEMA_ID = "staffer-network-corpus-backfill-2009-discovery-v1"
USER_AGENT = (
    "MelangeSystemsPayrollBackfill/1.0 "
    "(official-public-data research; sequential paced GET only)"
)

# Serial Set session schedules that cover the target periods.  104-2..111-1 are
# already on disk from the shipped historical acquirer; these are the two that
# are not.
SESSION_INDEX_SPECS = [
    {"congress": 111, "session": 2, "url": "https://www.govinfo.gov/media/111-2se.pdf"},
    {"congress": 112, "session": 1, "url": "https://www.govinfo.gov/media/112-1se.pdf"},
]

LOCAL_SESSION_INDEX_DIR = (
    Path(__file__).resolve().parent
    / "house_sod_payroll_20260831"
    / "raw_govinfo_serial_indexes"
)

# Document entries already resolved from the ON-DISK 111-1 session schedule.
SEED_DOCUMENTS = [
    {
        "chamber": "senate",
        "congress": 111,
        "doc_type": "sdoc",
        "doc_number": 2,
        "period_start": "2008-10-01",
        "period_end": "2009-03-31",
        "title_evidence": "Senate Document No. 2 Report of Secretary of Senate, Oct. 1, 2008-March 31, 2009",
        "evidence_source": "local 111-1se.pdf",
    },
    {
        "chamber": "senate",
        "congress": 111,
        "doc_type": "sdoc",
        "doc_number": 8,
        "period_start": "2009-04-01",
        "period_end": "2009-09-30",
        "title_evidence": "Senate Document No. 8 Report of Secretary of Senate, April 1-Sept. 30, 2009",
        "evidence_source": "local 111-1se.pdf",
    },
    {
        "chamber": "house",
        "congress": 111,
        "doc_type": "hdoc",
        "doc_number": 26,
        "period_start": "2009-01-01",
        "period_end": "2009-03-31",
        "title_evidence": "House Document No. 26 Statement of Disbursements of House, Jan. 1-March 31, 2009 (pts. 1-3)",
        "evidence_source": "local 111-1se.pdf",
    },
    {
        "chamber": "house",
        "congress": 111,
        "doc_type": "hdoc",
        "doc_number": 56,
        "period_start": "2009-04-01",
        "period_end": "2009-06-30",
        "title_evidence": "House Document No. 56 Statement of Disbursements of House, April 1-June 30, 2009 (pts. 1-3)",
        "evidence_source": "local 111-1se.pdf",
    },
]

SENATE_ENTRY_RE = re.compile(
    r"Senate Document No\.\s*(\d+)\s+Report of Secretary of Senate,\s*"
    r"([A-Za-z]+\.?\s*\d+),?\s*(\d{4})?\s*[–—\-â€“]+\s*"
    r"([A-Za-z]+\.?\s*\d+),?\s*(\d{4})",
    re.IGNORECASE,
)
HOUSE_ENTRY_RE = re.compile(
    r"House Document No\.\s*(\d+)\s+Statement of Disbursements of House,\s*"
    r"([A-Za-z]+\.?\s*\d+)\s*[–—\-â€“]+\s*"
    r"([A-Za-z]+\.?\s*\d+),?\s*(\d{4})",
    re.IGNORECASE,
)


class HostPacer:
    """Sequential pacer: at least `interval` seconds between requests to one host."""

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
        json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def write_bytes_atomic(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


CHALLENGE_MARKERS = (
    b"captcha",
    b"unusual traffic",
    b"are you a robot",
    b"cf-browser-verification",
    b"Just a moment...",
)


def classify_body(body: bytes, content_type: str) -> str:
    head = body[:4096].lower()
    for marker in CHALLENGE_MARKERS:
        if marker.lower() in head:
            return "CHALLENGE_SUSPECTED"
    if body[:4] == b"%PDF":
        return "PDF"
    stripped = body.lstrip()[:5].lower()
    if stripped.startswith(b"<?xml") or stripped.startswith(b"<mods"):
        return "XML"
    if stripped.startswith(b"<html") or stripped.startswith(b"<!doc"):
        return "HTML"
    if "json" in content_type.lower():
        return "JSON"
    return "OTHER"


def fetch(
    url: str, pacer: HostPacer, accept: str, receipts: list[dict[str, Any]], timeout: int = 180
) -> dict[str, Any]:
    host = urllib.parse.urlparse(url).netloc
    pacer.wait(host)
    started = time.monotonic()
    record: dict[str, Any] = {
        "url": url,
        "fetched_utc": utc_now(),
        "host": host,
        "http_status": None,
        "bytes": 0,
        "sha256": None,
        "content_type": None,
        "body_class": None,
        "error": None,
        "body": None,
    }
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
            record["http_status"] = response.status
            record["content_type"] = response.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        record["http_status"] = exc.code
        record["error"] = f"HTTPError {exc.code} {exc.reason}"
        body = b""
    except Exception as exc:  # noqa: BLE001 - route outcome is the datum
        record["error"] = f"{type(exc).__name__}: {exc}"
        body = b""
    record["bytes"] = len(body)
    record["duration_ms"] = int((time.monotonic() - started) * 1000)
    if body:
        record["sha256"] = sha256_bytes(body)
        record["body_class"] = classify_body(body, record["content_type"] or "")
    receipt = {key: value for key, value in record.items() if key != "body"}
    receipts.append(receipt)
    print(
        f"GET {url} -> {record['http_status']} {record['bytes']}B {record['body_class']} "
        f"{record['error'] or ''}",
        flush=True,
    )
    record["body"] = body
    return record


def parse_session_schedule(text: str, congress: int, session: int, source_url: str) -> list[dict[str, Any]]:
    flat = " ".join(text.split())
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for match in SENATE_ENTRY_RE.finditer(flat):
        number = int(match.group(1))
        if ("sdoc", number) in seen:
            continue
        seen.add(("sdoc", number))
        rows.append(
            {
                "chamber": "senate",
                "congress": congress,
                "session": session,
                "doc_type": "sdoc",
                "doc_number": number,
                "title_evidence": flat[match.start() : match.end()],
                "evidence_source": source_url,
            }
        )
    for match in HOUSE_ENTRY_RE.finditer(flat):
        number = int(match.group(1))
        if ("hdoc", number) in seen:
            continue
        seen.add(("hdoc", number))
        rows.append(
            {
                "chamber": "house",
                "congress": congress,
                "session": session,
                "doc_type": "hdoc",
                "doc_number": number,
                "title_evidence": flat[match.start() : match.end()],
                "evidence_source": source_url,
            }
        )
    return rows


def pdf_text(path: Path) -> str:
    import fitz

    document = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in document)
    finally:
        document.close()


def package_id(congress: int, doc_type: str, number: int) -> str:
    return f"GPO-CDOC-{congress}{doc_type}{number}"


def mods_url(pkg: str) -> str:
    return f"https://www.govinfo.gov/metadata/pkg/{pkg}/mods.xml"


def content_pdf_url(pkg: str, suffix: str | None = None) -> str:
    leaf = pkg if suffix is None else f"{pkg}-{suffix}"
    return f"https://www.govinfo.gov/content/pkg/{pkg}/pdf/{leaf}.pdf"


def summarize_mods(body: bytes) -> dict[str, Any]:
    out: dict[str, Any] = {"title": None, "granules": [], "parse_error": None}
    try:
        root = ET.fromstring(body)
    except ET.ParseError as exc:
        out["parse_error"] = str(exc)
        return out
    namespace = {"m": "http://www.loc.gov/mods/v3"}
    titles = root.findall(".//m:titleInfo/m:title", namespace)
    if titles:
        out["title"] = (titles[0].text or "").strip()
    granule_ids: list[str] = []
    for related in root.findall(".//m:relatedItem", namespace):
        for identifier in related.findall("./m:identifier", namespace):
            if identifier.get("type") == "preferred citation":
                continue
            value = (identifier.text or "").strip()
            if value.startswith("GPO-CDOC-") and value not in granule_ids:
                granule_ids.append(value)
    out["granules"] = granule_ids
    return out


def run(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    receipts: list[dict[str, Any]] = []
    pacer = HostPacer(args.minimum_interval_seconds)

    # --- robots.txt for every host we intend to touch -------------------------
    robots: dict[str, Any] = {}
    for host in ("www.govinfo.gov", "www.house.gov", "www.senate.gov"):
        url = f"https://{host}/robots.txt"
        record = fetch(url, pacer, "text/plain,*/*;q=0.1", receipts)
        if record["body"]:
            write_bytes_atomic(raw_dir / f"robots_{host}.txt", record["body"])
        robots[host] = {
            "http_status": record["http_status"],
            "bytes": record["bytes"],
            "sha256": record["sha256"],
            "text": (record["body"] or b"").decode("utf-8", errors="replace")[:4000],
        }

    # --- Serial Set session schedules not already on disk --------------------
    documents: list[dict[str, Any]] = [dict(row) for row in SEED_DOCUMENTS]
    schedule_records: list[dict[str, Any]] = []
    for spec in SESSION_INDEX_SPECS:
        name = Path(urllib.parse.urlparse(spec["url"]).path).name
        local = LOCAL_SESSION_INDEX_DIR / name
        destination = raw_dir / name
        if destination.exists():
            body_class = "PDF" if destination.read_bytes()[:4] == b"%PDF" else "OTHER"
            entry = {
                "url": spec["url"],
                "path": str(destination),
                "bytes": destination.stat().st_size,
                "sha256": sha256_bytes(destination.read_bytes()),
                "body_class": body_class,
                "http_status": None,
                "source": "REUSED_LOCAL_CACHE",
            }
        elif local.exists():
            payload = local.read_bytes()
            write_bytes_atomic(destination, payload)
            entry = {
                "url": spec["url"],
                "path": str(destination),
                "bytes": len(payload),
                "sha256": sha256_bytes(payload),
                "body_class": classify_body(payload, ""),
                "http_status": None,
                "source": "REUSED_SHIPPED_ACQUIRER_CACHE",
            }
        else:
            record = fetch(spec["url"], pacer, "application/pdf,*/*;q=0.1", receipts)
            if record["body_class"] != "PDF":
                schedule_records.append(
                    {
                        "congress": spec["congress"],
                        "session": spec["session"],
                        "url": spec["url"],
                        "outcome": "NOT_A_PDF",
                        "http_status": record["http_status"],
                        "body_class": record["body_class"],
                        "error": record["error"],
                    }
                )
                continue
            write_bytes_atomic(destination, record["body"])
            entry = {
                "url": spec["url"],
                "path": str(destination),
                "bytes": record["bytes"],
                "sha256": record["sha256"],
                "body_class": record["body_class"],
                "http_status": record["http_status"],
                "source": "FETCHED",
            }
        text = pdf_text(destination)
        rows = parse_session_schedule(text, spec["congress"], spec["session"], spec["url"])
        entry.update(
            {
                "congress": spec["congress"],
                "session": spec["session"],
                "outcome": "PARSED",
                "entry_count": len(rows),
            }
        )
        schedule_records.append(entry)
        documents.extend(rows)

    # --- probe govinfo CDOC packages ----------------------------------------
    probes: list[dict[str, Any]] = []
    for document in documents:
        pkg = package_id(document["congress"], document["doc_type"], document["doc_number"])
        mods_path = raw_dir / f"{pkg}.mods.xml"
        if mods_path.exists():
            body = mods_path.read_bytes()
            status, body_class, source = None, classify_body(body, ""), "REUSED_LOCAL_CACHE"
            sha = sha256_bytes(body)
        else:
            record = fetch(mods_url(pkg), pacer, "application/xml,text/xml,*/*;q=0.1", receipts)
            body = record["body"] or b""
            status, body_class, source = record["http_status"], record["body_class"], "FETCHED"
            sha = record["sha256"]
            if body_class == "XML":
                write_bytes_atomic(mods_path, body)
        probe: dict[str, Any] = {
            "package_id": pkg,
            "mods_url": mods_url(pkg),
            "http_status": status,
            "body_class": body_class,
            "bytes": len(body),
            "sha256": sha,
            "source": source,
            "document": document,
            "exists": body_class == "XML",
        }
        if body_class == "XML":
            probe.update(summarize_mods(body))
        probes.append(probe)

    payload = {
        "schema_id": DISCOVERY_SCHEMA_ID,
        "generated_utc": utc_now(),
        "minimum_interval_seconds": args.minimum_interval_seconds,
        "robots": robots,
        "session_schedules": schedule_records,
        "seed_documents": SEED_DOCUMENTS,
        "documents": documents,
        "package_probes": probes,
        "request_receipts": receipts,
    }
    write_json_atomic(output_dir / "backfill_2009_discovery.json", payload)
    print(f"WROTE {output_dir / 'backfill_2009_discovery.json'}")
    found = [probe["package_id"] for probe in probes if probe["exists"]]
    print(f"PACKAGES_FOUND {len(found)}/{len(probes)}: {found}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.2)
    return run(parser.parse_args())


if __name__ == "__main__":
    sys.exit(main())
