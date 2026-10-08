#!/usr/bin/env python3
"""Rebuild House historical personnel candidates from sealed layout-text caches.

This runner performs no network requests.  It exists so parser corrections can
produce a new, immutable derived generation without overwriting the original
official-PDF cache or any earlier candidate generation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil

import acquire_house_sod_historical as historical


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    source_dir = args.source_dir.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SystemExit(f"output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    source_receipt_path = source_dir / "house_sod_payroll_pdf_receipt.json"
    source_inventory_path = source_dir / "house_sod_historical_url_inventory.json"
    source_receipt = json.loads(source_receipt_path.read_text(encoding="utf-8"))
    inventory = json.loads(source_inventory_path.read_text(encoding="utf-8"))
    source_periods = {row["period"]: row for row in source_receipt["periods"]}

    sources = []
    for inventory_row in inventory["house_pdf_periods"]:
        period = inventory_row["period"]
        source = source_periods[period]
        text_path = source_dir / "historical_house_pdf_text" / f"{period.lower()}_visual_rows.ndjson.gz"
        if historical.base.sha256_file(text_path) != source["text_sha256"]:
            raise SystemExit(f"layout-text cache hash mismatch: {period}")
        sources.append(
            {
                "bytes": source["bytes"],
                "pages": source.get("pages"),
                "pdf_sha256": source["pdf_sha256"],
                "pdf_url": source["pdf_url"],
                "period": period,
                "period_end": inventory_row["period_end"],
                "period_start": inventory_row["period_start"],
                "text_bytes": source["text_bytes"],
                "text_path": str(text_path),
                "text_sha256": source["text_sha256"],
            }
        )

    inventory_path = output_dir / source_inventory_path.name
    shutil.copyfile(source_inventory_path, inventory_path)
    result = historical.write_pdf_candidates(
        "full",
        sources,
        output_dir,
        inventory_path,
        minimum_request_interval=0.0,
        workers=1,
    )
    result["cache_rebuild"] = {
        "network_requests": 0,
        "source_generation": str(source_dir),
        "source_inventory_sha256": historical.base.sha256_file(source_inventory_path),
        "source_receipt_sha256": historical.base.sha256_file(source_receipt_path),
    }
    print(historical.base.compact_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
