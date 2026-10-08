#!/usr/bin/env python3
"""Inventory employment-related fields in every local Senate LDA raw page.

This is a read-only schema audit.  It does not use the raw pages as a second
canonical corpus; it proves which keys the locally sealed source payloads
actually expose and binds the result to per-file hashes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_RAW_ROOT = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\raw\lda"
)
DEFAULT_OUTPUT_ROOT = Path(
    "audits/staffer_network/lda_raw_covered_position_schema_audit_20260831"
)
RECEIPT = "lda_raw_covered_position_schema_audit_receipt.json"
RELEVANT_TOKENS = (
    "position",
    "employ",
    "title",
    "start",
    "end",
    "date",
    "current",
    "government",
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def is_relevant(key: str) -> bool:
    lowered = key.casefold()
    return any(token in lowered for token in RELEVANT_TOKENS)


def signature(keys: Any) -> str:
    return "|".join(sorted(str(key) for key in keys))


def scan_file(raw_root: Path, path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    value = json.loads(payload)
    if not isinstance(value, dict) or not isinstance(value.get("results"), list):
        raise ValueError("raw page lacks results array")
    counts: Counter[str] = Counter()
    item_signatures: Counter[str] = Counter()
    identity_signatures: Counter[str] = Counter()
    item_keys: Counter[str] = Counter()
    identity_keys: Counter[str] = Counter()
    relevant_item_keys: Counter[str] = Counter()
    relevant_identity_keys: Counter[str] = Counter()
    relevant_filing_keys: Counter[str] = Counter()
    relevant_activity_keys: Counter[str] = Counter()
    covered_value_types: Counter[str] = Counter()
    counts["filings"] = len(value["results"])
    for filing in value["results"]:
        if not isinstance(filing, dict):
            raise ValueError("filing row is not an object")
        for key in filing:
            if is_relevant(key):
                relevant_filing_keys[key] += 1
        activities = filing.get("lobbying_activities") or []
        counts["activities"] += len(activities)
        for activity in activities:
            if not isinstance(activity, dict):
                raise ValueError("activity row is not an object")
            for key in activity:
                if is_relevant(key):
                    relevant_activity_keys[key] += 1
            lobbyist_items = activity.get("lobbyists") or []
            counts["lobbyist_items"] += len(lobbyist_items)
            for item in lobbyist_items:
                if not isinstance(item, dict):
                    raise ValueError("lobbyist item is not an object")
                item_signatures[signature(item)] += 1
                for key in item:
                    item_keys[key] += 1
                    if is_relevant(key):
                        relevant_item_keys[key] += 1
                covered = item.get("covered_position")
                covered_value_types[type(covered).__name__] += 1
                identity = item.get("lobbyist")
                if not isinstance(identity, dict):
                    raise ValueError("lobbyist identity subobject is not an object")
                identity_signatures[signature(identity)] += 1
                for key in identity:
                    identity_keys[key] += 1
                    if is_relevant(key):
                        relevant_identity_keys[key] += 1
    return {
        "bytes": len(payload),
        "counts": dict(counts),
        "covered_value_types": dict(covered_value_types),
        "generation": path.relative_to(raw_root).parts[0],
        "identity_keys": dict(identity_keys),
        "identity_signatures": dict(identity_signatures),
        "item_keys": dict(item_keys),
        "item_signatures": dict(item_signatures),
        "path": path.relative_to(raw_root).as_posix(),
        "relevant_activity_keys": dict(relevant_activity_keys),
        "relevant_filing_keys": dict(relevant_filing_keys),
        "relevant_identity_keys": dict(relevant_identity_keys),
        "relevant_item_keys": dict(relevant_item_keys),
        "sha256": digest,
    }


def merge_counter(target: Counter[str], values: dict[str, int]) -> None:
    target.update(values)


def build(args: argparse.Namespace) -> dict[str, Any]:
    raw_root = args.raw_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    paths = sorted(raw_root.rglob("page_*.json"), key=lambda path: path.as_posix())
    if not paths:
        raise ValueError("no local raw page files found")

    totals: Counter[str] = Counter()
    item_signatures: Counter[str] = Counter()
    identity_signatures: Counter[str] = Counter()
    item_keys: Counter[str] = Counter()
    identity_keys: Counter[str] = Counter()
    relevant_item_keys: Counter[str] = Counter()
    relevant_identity_keys: Counter[str] = Counter()
    relevant_filing_keys: Counter[str] = Counter()
    relevant_activity_keys: Counter[str] = Counter()
    covered_value_types: Counter[str] = Counter()
    generation_files: Counter[str] = Counter()
    generation_bytes: Counter[str] = Counter()
    generation_digest_streams: dict[str, hashlib._Hash] = defaultdict(hashlib.sha256)
    inventory_digest = hashlib.sha256()
    errors: list[dict[str, str]] = []

    def safe(path: Path) -> dict[str, Any]:
        try:
            return scan_file(raw_root, path)
        except Exception as exc:  # fail-closed while retaining exact path/error
            return {
                "error": f"{type(exc).__name__}: {exc}",
                "path": path.relative_to(raw_root).as_posix(),
            }

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for result in executor.map(safe, paths):
            if "error" in result:
                errors.append({"path": result["path"], "error": result["error"]})
                continue
            generation = result["generation"]
            generation_files[generation] += 1
            generation_bytes[generation] += result["bytes"]
            binding = f"{result['path']}\0{result['sha256']}\n".encode("utf-8")
            inventory_digest.update(binding)
            generation_digest_streams[generation].update(binding)
            totals["page_files"] += 1
            totals["bytes"] += result["bytes"]
            merge_counter(totals, result["counts"])
            merge_counter(item_signatures, result["item_signatures"])
            merge_counter(identity_signatures, result["identity_signatures"])
            merge_counter(item_keys, result["item_keys"])
            merge_counter(identity_keys, result["identity_keys"])
            merge_counter(relevant_item_keys, result["relevant_item_keys"])
            merge_counter(relevant_identity_keys, result["relevant_identity_keys"])
            merge_counter(relevant_filing_keys, result["relevant_filing_keys"])
            merge_counter(relevant_activity_keys, result["relevant_activity_keys"])
            merge_counter(covered_value_types, result["covered_value_types"])

    generations = []
    for name in sorted(generation_files):
        generations.append(
            {
                "bytes": generation_bytes[name],
                "inventory_binding_sha256": generation_digest_streams[name].hexdigest(),
                "name": name,
                "page_files": generation_files[name],
            }
        )
    checks = {
        "all_discovered_raw_pages_parsed": totals["page_files"] == len(paths),
        "covered_position_present_at_lobbyist_activity_item": relevant_item_keys.get("covered_position", 0) > 0,
        "lobbyist_identity_has_no_employment_relevant_keys": len(relevant_identity_keys) == 0,
        "parse_errors_zero": len(errors) == 0,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    receipt = {
        "checks": checks,
        "conclusion": {
            "employment_source_shape": "filing.lobbying_activities[].lobbyists[].covered_position",
            "separately_structured_current_field": False,
            "separately_structured_employer_or_office_field": False,
            "separately_structured_employment_end_field": False,
            "separately_structured_employment_start_field": False,
            "separately_structured_title_field": False,
            "source_value_type": "free-text string or null",
        },
        "covered_position_value_type_counts": dict(sorted(covered_value_types.items())),
        "errors": errors,
        "generations": generations,
        "inventory_binding_sha256": inventory_digest.hexdigest(),
        "lobbyist_identity_key_counts": dict(sorted(identity_keys.items())),
        "lobbyist_identity_key_signatures": dict(sorted(identity_signatures.items())),
        "lobbyist_item_key_counts": dict(sorted(item_keys.items())),
        "lobbyist_item_key_signatures": dict(sorted(item_signatures.items())),
        "relevant_activity_key_counts": dict(sorted(relevant_activity_keys.items())),
        "relevant_filing_key_counts": dict(sorted(relevant_filing_keys.items())),
        "relevant_lobbyist_identity_key_counts": dict(sorted(relevant_identity_keys.items())),
        "relevant_lobbyist_item_key_counts": dict(sorted(relevant_item_keys.items())),
        "schema_id": "staffer-network-lda-raw-covered-position-schema-audit-v1",
        "status": status,
        "totals": dict(sorted(totals.items())),
        "workers": args.workers,
    }
    receipt_path = output_root / RECEIPT
    receipt_path.write_bytes(canonical_bytes(receipt))
    if status != "PASS":
        raise RuntimeError(f"raw schema audit failed: {checks}; errors={len(errors)}")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=8)
    return parser.parse_args()


if __name__ == "__main__":
    print(json.dumps(build(parse_args()), ensure_ascii=False, sort_keys=True))
