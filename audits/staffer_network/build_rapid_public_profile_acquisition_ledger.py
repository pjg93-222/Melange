#!/usr/bin/env python3
"""Join rapid public-profile seed rows to rate-safe page captures."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", required=True)
    parser.add_argument("--captures", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    seed_path = Path(args.seeds)
    capture_path = Path(args.captures)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    captures = {row["url"]: row for row in read_ndjson(capture_path)}
    rows: list[dict[str, Any]] = []
    for seed in read_ndjson(seed_path):
        source_records = []
        for url in sorted(set(seed.get("source_urls", []))):
            captured = captures.get(url)
            if captured is None:
                source_records.append({"url": url, "status": "NOT_CAPTURED"})
                continue
            source_records.append({
                "url": url,
                "status": captured["status"],
                "http_status": captured.get("http_status"),
                "final_url": captured.get("final_url"),
                "content_sha256": captured.get("content_sha256"),
                "text_sha256": captured.get("text_sha256"),
                "text_path": captured.get("text_path"),
                "title": captured.get("title"),
                "hints": captured.get("hints", {}),
                "skip_reason": captured.get("skip_reason"),
                "error": captured.get("error"),
            })
        rows.append({
            "schema_id": "staffer-network-rapid-public-profile-acquisition-v1",
            "lda_source_person_id": seed["lda_source_person_id"],
            "display_name": seed["display_name"],
            "identity_status": "REVIEW_REQUIRED",
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "complete_lifetime_employment_asserted": False,
            "source_count": len(source_records),
            "captured_source_count": sum(item["status"] == "CAPTURED" for item in source_records),
            "source_records": source_records,
        })

    rows.sort(key=lambda row: row["lda_source_person_id"])
    ledger = output_root / "rapid_public_profile_acquisition.ndjson"
    ledger.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    source_statuses = Counter(
        source["status"] for row in rows for source in row["source_records"]
    )
    receipt = {
        "schema_id": "staffer-network-rapid-public-profile-acquisition-receipt-v1",
        "status": "PASS",
        "person_count": len(rows),
        "source_count": sum(row["source_count"] for row in rows),
        "captured_source_count": sum(row["captured_source_count"] for row in rows),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "source_status_counts": dict(sorted(source_statuses.items())),
        "output": {
            "path": ledger.name,
            "bytes": ledger.stat().st_size,
            "sha256": sha256(ledger),
        },
    }
    receipt_path = output_root / "rapid_public_profile_acquisition_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
