#!/usr/bin/env python3
"""Deterministically reassemble a Senate candidate archive from sealed per-report caches."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_gzip(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_gzip(path: Path, rows: list[dict[str, Any]]) -> None:
    temporary = path.with_name(path.name + ".part")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as stream:
            for row in rows:
                stream.write((compact_json(row) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def run(archive: Path, output_root: Path, parser_version: str) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"Output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    inventory = json.loads((archive / "senate_report_archive_inventory.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    cache_bindings = []
    for report in inventory["periods"]:
        package = report["package_id"]
        candidate_path = archive / "parsed" / f"{package}.candidates.ndjson.gz"
        receipt_path = archive / "parsed" / f"{package}.receipt.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("parser_version") != parser_version:
            raise RuntimeError(f"Unexpected parser version for {package}: {receipt.get('parser_version')}")
        report_rows = read_gzip(candidate_path)
        if len(report_rows) != receipt["candidate_count"]:
            raise RuntimeError(f"Cache count mismatch for {package}")
        rows.extend(report_rows)
        cache_bindings.append({
            "candidate_cache_sha256": sha256_file(candidate_path),
            "candidate_count": len(report_rows),
            "package_id": package,
            "receipt_sha256": sha256_file(receipt_path),
        })
    rows.sort(key=lambda row: (
        row["report_period_start"], row["report_package_id"], row["page_number"],
        row["row_ordinal_on_page"], row["candidate_id"],
    ))
    ids = [row["candidate_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate candidate IDs in reassembled archive")
    output_path = output_root / "senate_payroll_candidates_2011_2026.ndjson.gz"
    write_gzip(output_path, rows)
    receipt = {
        "cache_bindings": cache_bindings,
        "candidate_count": len(rows),
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "sha256": sha256_file(output_path),
        },
        "parser_version": parser_version,
        "report_count": len(cache_bindings),
        "schema_id": "staffer-network-senate-payroll-cache-assembly-receipt-v1",
        "status": "PASS",
    }
    receipt_path = output_root / "senate_payroll_cache_assembly_receipt.json"
    receipt_path.write_text(compact_json(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact_json(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--parser-version", default="senate-payroll-parser-v4")
    args = parser.parse_args()
    run(args.archive, args.output_root, args.parser_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
