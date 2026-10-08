#!/usr/bin/env python3
"""Validate and deterministically consolidate structured discovery shards."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    input_root = Path(args.input_root)
    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    shards = sorted(input_root.glob("batch*.ndjson"))
    seen: set[str] = set()
    shard_receipts: list[dict[str, Any]] = []
    for shard in shards:
        shard_count = 0
        with shard.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                source_id = row["lda_source_person_id"]
                if source_id in seen:
                    raise ValueError(f"duplicate lda_source_person_id: {source_id}")
                seen.add(source_id)
                for key in ("display_name", "education"):
                    if key not in row:
                        raise ValueError(f"{shard}:{line_number} missing {key}")
                employment = row.get("employment", row.get("employment_episodes"))
                if employment is None:
                    raise ValueError(f"{shard}:{line_number} missing employment facts")
                row["employment"] = employment
                if not isinstance(row["employment"], list) or not isinstance(row["education"], list):
                    raise ValueError(f"{shard}:{line_number} facts must be lists")
                for flag in ("canonical_identity_promoted", "canonical_employment_promoted"):
                    if row.get(flag, False) is not False:
                        raise ValueError(f"{shard}:{line_number} illegal promotion: {flag}")
                    row[flag] = False
                if row.get("complete_lifetime_employment_asserted", False) is not False:
                    raise ValueError(f"{shard}:{line_number} illegal lifetime assertion")
                row["complete_lifetime_employment_asserted"] = False
                row.setdefault("schema_id", "staffer-network-rapid-structured-profile-evidence-v1")
                row["source_shard"] = str(shard)
                rows.append(row)
                shard_count += 1
        shard_receipts.append({
            "path": str(shard),
            "rows": shard_count,
            "bytes": shard.stat().st_size,
            "sha256": digest(shard),
        })

    rows.sort(key=lambda row: row["lda_source_person_id"])
    ledger = output_root / "rapid_structured_profile_evidence.ndjson"
    ledger.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    receipt = {
        "schema_id": "staffer-network-rapid-structured-profile-evidence-receipt-v1",
        "status": "PASS",
        "shard_count": len(shards),
        "person_count": len(rows),
        "employment_episode_count": sum(len(row["employment"]) for row in rows),
        "education_episode_count": sum(len(row["education"]) for row in rows),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "shards": shard_receipts,
        "output": {
            "path": ledger.name,
            "bytes": ledger.stat().st_size,
            "sha256": digest(ledger),
        },
    }
    receipt_path = output_root / "rapid_structured_profile_evidence_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
