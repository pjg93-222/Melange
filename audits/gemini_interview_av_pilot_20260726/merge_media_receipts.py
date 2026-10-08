#!/usr/bin/env python3
"""Merge retry rows into a media receipt document by pilot ID."""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", type=Path, required=True)
    parser.add_argument("--updates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base = json.loads(args.base.read_text(encoding="utf-8"))
    updates = json.loads(args.updates.read_text(encoding="utf-8"))
    rows = {row["pilot_id"]: row for row in base["items"]}
    rows.update({row["pilot_id"]: row for row in updates["items"]})
    document = {
        **base,
        "schema": "gemini-interview-av-media-receipts-v2",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "merge_sources": [args.base.name, args.updates.name],
        "items": [rows[pilot_id] for pilot_id in sorted(rows)],
    }
    args.output.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    failed = [
        row["pilot_id"]
        for row in document["items"]
        if row["status"] == "failed"
    ]
    print(
        json.dumps(
            {
                "items": len(document["items"]),
                "failed": failed,
                "output": str(args.output.resolve()),
            },
            indent=2,
        )
    )
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
