#!/usr/bin/env python3
"""Convert structured discovery shards into a deterministic scraper seed shard."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from public_history_scraper import nested_urls, normalized_url


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    input_root = Path(args.input_root)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    people: dict[str, dict[str, Any]] = {}
    for shard in sorted(input_root.glob("batch*.ndjson")):
        with shard.open("r", encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                value = json.loads(line)
                source_id = value["lda_source_person_id"]
                row = people.setdefault(source_id, {
                    "schema_id": "staffer-network-structured-discovery-scraper-seed-v1",
                    "lda_source_person_id": source_id,
                    "display_name": value["display_name"],
                    "source_urls": set(),
                })
                for raw_url in nested_urls(value):
                    url = normalized_url(raw_url)
                    if url:
                        row["source_urls"].add(url)

    rows = []
    for source_id in sorted(people):
        row = people[source_id]
        row["source_urls"] = sorted(row["source_urls"])
        rows.append(row)
    output.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    receipt = {
        "schema_id": "staffer-network-structured-discovery-scraper-seed-receipt-v1",
        "status": "PASS",
        "person_count": len(rows),
        "url_count": sum(len(row["source_urls"]) for row in rows),
        "unique_url_count": len({url for row in rows for url in row["source_urls"]}),
        "output": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256(output),
        },
    }
    receipt_path = output.with_suffix(".receipt.json")
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
