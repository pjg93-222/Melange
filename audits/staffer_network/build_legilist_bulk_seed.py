#!/usr/bin/env python3
"""Convert a bulk identity manifest into deterministic public LegiList URLs."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    manifest = Path(args.manifest).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    with gzip.open(manifest, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            source = json.loads(line)
            source_id = source["lda_source_person_id"]
            numeric_id = source_id.rsplit(":", 1)[-1]
            url = f"https://legilist.com/lda/contributions/lobbyist/{numeric_id}/{slug(source['display_name'])}/"
            rows.append({
                "schema_id": "staffer-network-public-lda-profile-fanout-v1",
                "lda_source_person_id": source_id,
                "display_name": source["display_name"],
                "acquisition_priority": source.get("acquisition_priority"),
                "source_urls": [url],
                "profile_urls": [url],
                "legilist_profile_url": url,
                "identity_status": "REVIEW_REQUIRED",
                "canonical_identity_promoted": False,
                "canonical_employment_promoted": False,
                "complete_lifetime_employment_asserted": False,
            })

    rows.sort(key=lambda row: row["lda_source_person_id"])
    output = output_root / "public_lda_profile_fanout_20260901_slice_2000.ndjson"
    output.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    receipt = {
        "schema_id": "staffer-network-legilist-bulk-seed-receipt-v1",
        "status": "PASS",
        "manifest": {"path": str(manifest), "sha256": sha256(manifest)},
        "person_count": len(rows),
        "url_count": len(rows),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "output": {"path": output.name, "bytes": output.stat().st_size, "sha256": sha256(output)},
    }
    receipt_path = output_root / "legilist_bulk_seed_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
