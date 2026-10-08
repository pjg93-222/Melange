#!/usr/bin/env python3
"""Merge verified local media receipts into the final Fable pilot manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE / "pilot_manifest_30_fable_media_ready.json"
RECEIPTS = HERE / "media_receipts_fable.json"
OUTPUT = HERE / "pilot_manifest_30_fable_final.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--receipts", type=Path, default=RECEIPTS)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--expected-count", type=int, default=30)
    args = parser.parse_args()
    source = args.source.resolve()
    receipt_path = args.receipts.resolve()
    output = args.output.resolve()
    manifest = json.loads(source.read_text(encoding="utf-8"))
    receipt_document = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipts = {row["pilot_id"]: row for row in receipt_document["items"]}
    items = []
    for item in manifest["items"]:
        receipt = receipts.get(item["pilot_id"])
        if not receipt or receipt["status"] not in {"existing", "downloaded"}:
            raise ValueError(f"{item['pilot_id']}: missing verified media receipt")
        items.append(
            {
                **item,
                "media_status": (
                    "LOCAL_VERIFIED_AV_TEMPORALLY_TRIMMED"
                    if receipt.get("temporal_selection")
                    == "hls-segment-trim-v2"
                    else "LOCAL_VERIFIED_AV"
                ),
                "duration_sec": receipt.get(
                    "duration_sec",
                    item["duration_sec"],
                ),
                "target_end_sec_in_clip": min(
                    item["target_end_sec_in_clip"],
                    receipt.get("duration_sec", item["duration_sec"]),
                ),
                "local_media_path": receipt["path"],
                "media_bytes": receipt["bytes"],
                "media_sha256": receipt["sha256"],
                **{
                    key: receipt[key]
                    for key in (
                        "temporal_selection",
                        "rendition_url",
                        "requested_start_sec",
                        "source_segment_start_sec",
                        "local_seek_sec",
                        "requested_duration_sec",
                        "output_duration_sec",
                        "selected_segment_count",
                        "selected_segment_coverage_sec",
                        "selected_segment_bytes",
                    )
                    if key in receipt
                },
            }
        )
    if len(items) != args.expected_count:
        raise ValueError(
            f"final manifest must contain {args.expected_count} items"
        )
    temporally_trimmed = all(
        row.get("temporal_selection") == "hls-segment-trim-v2"
        for row in items
    )
    manifest.update(
        {
            "schema": (
                "gemini-flash-interview-av-fable-final-manifest-v2"
                if temporally_trimmed
                else "gemini-flash-interview-av-fable-final-manifest-v1"
            ),
            "status": (
                "FROZEN_LOCAL_AV_TEMPORALLY_TRIMMED_NOT_SCORED"
                if temporally_trimmed
                else "FROZEN_LOCAL_AV_READY_NOT_SCORED"
            ),
            "media_receipt_source": receipt_path.name,
            "items": items,
        }
    )
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "items": len(items),
                "total_bytes": sum(row["media_bytes"] for row in items),
                "all_sha256_present": all(row["media_sha256"] for row in items),
                "temporally_trimmed": temporally_trimmed,
                "output": str(output),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
