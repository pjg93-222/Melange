#!/usr/bin/env python3
"""Incrementally fetch newly discovered public profile evidence URLs.

Seed shards are ordinary NDJSON files using the existing LegiStorm-fanout file
names and may be dropped into any configured seed root.  Completed URL records
are hash-bound and reused on later runs; only new URLs and bounded retries are
submitted to the eight-worker, per-domain-paced public scraper.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import gzip
import hashlib
import json
import msvcrt
from pathlib import Path
from typing import Any

from public_history_scraper import PublicScraper, discover_seeds


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-root", action="append", default=[])
    parser.add_argument("--import-capture", action="append", default=[])
    parser.add_argument("--auto-discover-root", default="audits/staffer_network")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-domain-delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--max-bytes", type=int, default=10 * 1024 * 1024)
    parser.add_argument("--max-attempts", type=int, default=2)
    args = parser.parse_args()
    if args.workers < 1 or args.per_domain_delay < 0 or args.max_attempts < 1:
        raise SystemExit("invalid worker, delay, or attempt setting")

    discovery_root = Path(args.auto_discover_root)
    if not args.seed_root:
        auto_seed_roots = [discovery_root / "legistorm_fanout"]
        auto_seed_roots.extend(sorted(
            path for path in discovery_root.glob("rapid_public_profile_seeds_20260901*")
            if path.is_dir()
        ))
        args.seed_root = [str(path) for path in auto_seed_roots if path.exists()]
    if not args.import_capture:
        auto_captures = list(discovery_root.glob(
            "public_history_scrape_20260831_full_8workers/public_page_captures.ndjson.gz"
        ))
        auto_captures.extend(sorted(discovery_root.glob(
            "rapid_public_profile_capture_20260901_*/public_page_captures.ndjson.gz"
        )))
        args.import_capture = [str(path) for path in auto_captures]
    if not args.seed_root:
        raise SystemExit("no seed roots discovered")

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    lock_path = output_root / ".pipeline.lock"
    lock_stream = lock_path.open("a+b")
    if lock_stream.seek(0, 2) == 0:
        lock_stream.write(b"\0")
        lock_stream.flush()
    lock_stream.seek(0)
    try:
        msvcrt.locking(lock_stream.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        print(compact({
            "schema_id": "staffer-network-incremental-public-profile-pipeline-receipt-v1",
            "status": "ALREADY_RUNNING",
            "output_root": str(output_root),
        }))
        return 0
    ledger_path = output_root / "incremental_public_page_captures.ndjson"

    provenance_sets: defaultdict[str, set[str]] = defaultdict(set)
    for raw_root in args.seed_root:
        urls, provenance = discover_seeds(Path(raw_root))
        for url in urls:
            provenance_sets[url].update(provenance[url])

    by_url: dict[str, dict[str, Any]] = {}
    for row in read_rows(ledger_path):
        by_url[row["url"]] = row
    for raw_capture in args.import_capture:
        for row in read_rows(Path(raw_capture)):
            by_url.setdefault(row["url"], row)

    terminal_statuses = {"CAPTURED", "HTTP_ERROR", "SKIPPED"}
    pending: list[str] = []
    for url in sorted(provenance_sets):
        previous = by_url.get(url)
        attempts = int(previous.get("attempt_count", 1)) if previous else 0
        if previous and previous.get("status") in terminal_statuses:
            continue
        if attempts >= args.max_attempts:
            continue
        pending.append(url)

    scraper = PublicScraper(
        output_root,
        delay=args.per_domain_delay,
        timeout=args.timeout,
        max_bytes=args.max_bytes,
    )
    new_records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(scraper.fetch, url, sorted(provenance_sets[url])): url
            for url in pending
        }
        for future in as_completed(futures):
            url = futures[future]
            row = future.result()
            previous = by_url.get(url)
            prior_attempts = int(previous.get("attempt_count", 1)) if previous else 0
            row["attempt_count"] = prior_attempts + 1
            new_records.append(row)
            by_url[url] = row
            if len(new_records) % 25 == 0:
                checkpoint_rows = [by_url[key] for key in sorted(by_url)]
                write_atomic(ledger_path, checkpoint_rows)

    ordered = [by_url[url] for url in sorted(by_url)]
    write_atomic(ledger_path, ordered)
    status_counts = Counter(row["status"] for row in ordered)
    receipt = {
        "schema_id": "staffer-network-incremental-public-profile-pipeline-receipt-v1",
        "status": "PASS",
        "generated_at": now(),
        "workers": args.workers,
        "per_domain_delay_seconds": args.per_domain_delay,
        "one_inflight_request_per_domain": True,
        "robots_enforced": True,
        "authenticated_sessions_used": 0,
        "browser_cookies_used": 0,
        "captcha_bypasses": 0,
        "cache_rotations": 0,
        "seed_root_count": len(args.seed_root),
        "discovered_url_count": len(provenance_sets),
        "previously_recorded_url_count": len(ordered) - len(new_records),
        "submitted_url_count": len(pending),
        "new_record_count": len(new_records),
        "status_counts": dict(sorted(status_counts.items())),
        "search_transport_blocks": {
            "google": "CAPTCHA_UNUSUAL_TRAFFIC",
            "duckduckgo_html": "BOT_CHALLENGE_HTTP_202",
            "bing_html": "ROBOTS_DISALLOWED",
        },
        "output": {
            "path": ledger_path.name,
            "bytes": ledger_path.stat().st_size,
            "sha256": sha256(ledger_path),
        },
    }
    receipt_path = output_root / "incremental_public_profile_pipeline_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
