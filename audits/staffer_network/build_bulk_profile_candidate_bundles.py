#!/usr/bin/env python3
"""Partition all person-linked evidence into deterministic 200-person review bundles."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from public_history_scraper import read_ndjson


TOKEN = re.compile(r"[A-Za-z][A-Za-z'-]+")
STOP = {"the", "and", "for", "with", "from", "jr", "sr", "ii", "iii", "iv"}


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clean_line(value: str) -> str | None:
    line = " ".join(value.split())
    if not line or len(line) > 2000:
        return None
    if sum(character == "\ufffd" for character in line) > max(1, len(line) // 100):
        return None
    printable = sum(character.isprintable() or character.isspace() for character in line)
    if printable / len(line) < 0.95 or sum(character.isalpha() for character in line) < 3:
        return None
    return line


def name_tokens(name: str) -> set[str]:
    return {token.lower() for token in TOKEN.findall(name) if len(token) > 1 and token.lower() not in STOP}


def evidence_lines(row: dict[str, Any], kind: str) -> tuple[list[dict[str, Any]], int]:
    key = f"{kind}_lines"
    person_tokens = name_tokens(row["display_name"])
    output: list[dict[str, Any]] = []
    rejected = 0
    seen: set[tuple[str, str]] = set()
    for span in row.get("candidate_spans", []):
        url = span["source_url"]
        for raw in span.get(key, []):
            line = clean_line(str(raw))
            if line is None:
                rejected += 1
                continue
            identity_match = bool(person_tokens & name_tokens(line))
            dedupe = (url, line)
            if dedupe in seen:
                continue
            seen.add(dedupe)
            output.append({
                "kind": kind.upper(),
                "line": line,
                "line_sha256": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                "identity_token_match": identity_match,
                "source_url": url,
                "source_domain": urlsplit(url).hostname,
                "source_title": span.get("source_title"),
                "content_sha256": span.get("content_sha256"),
                "text_sha256": span.get("text_sha256"),
                "date_ranges": span.get("date_ranges", []),
                "year_tokens": span.get("year_tokens", []),
                "canonical_eligible": False,
            })
    output.sort(key=lambda item: (item["source_url"], item["line_sha256"]))
    return output, rejected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fact-ledger", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--batch-size", type=int, default=200)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("batch-size must be positive")

    fact_ledger = Path(args.fact_ledger).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")

    bundles: list[dict[str, Any]] = []
    rejected_lines = 0
    coverage = Counter()
    for row in read_ndjson(fact_ledger):
        employment, rejected_employment = evidence_lines(row, "employment")
        education, rejected_education = evidence_lines(row, "education")
        rejected_lines += rejected_employment + rejected_education
        dated = sum(bool(item["date_ranges"] or item["year_tokens"]) for item in employment)
        matched = sum(item["identity_token_match"] for item in employment)
        if dated and matched:
            state = "DATED_IDENTITY_MATCHED_CANDIDATES"
        elif dated:
            state = "DATED_CANDIDATES_REVIEW_REQUIRED"
        elif employment:
            state = "UNDATED_EMPLOYMENT_CANDIDATES"
        else:
            state = "NO_EMPLOYMENT_CANDIDATES"
        coverage[state] += 1
        bundles.append({
            "schema_id": "staffer-network-bulk-profile-candidate-bundle-v1",
            "lda_source_person_id": row["lda_source_person_id"],
            "display_name": row["display_name"],
            "coverage_state": state,
            "identity_status": "REVIEW_REQUIRED",
            "captured_candidate_source_count": row.get("captured_candidate_source_count", 0),
            "employment_candidate_count": len(employment),
            "dated_employment_candidate_count": dated,
            "identity_matched_employment_candidate_count": matched,
            "education_candidate_count": len(education),
            "employment_candidates": employment,
            "education_candidates": education,
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "complete_lifetime_employment_asserted": False,
        })

    bundles.sort(key=lambda item: item["lda_source_person_id"])
    shards = []
    for offset in range(0, len(bundles), args.batch_size):
        shard_rows = bundles[offset:offset + args.batch_size]
        shard = output_root / f"bulk_profile_candidate_bundles_{offset // args.batch_size + 1:04d}.ndjson"
        shard.write_text("".join(compact(row) + "\n" for row in shard_rows), encoding="utf-8", newline="\n")
        shards.append({"path": shard.name, "rows": len(shard_rows), "bytes": shard.stat().st_size, "sha256": sha256(shard)})

    receipt = {
        "schema_id": "staffer-network-bulk-profile-candidate-bundles-receipt-v1",
        "status": "PASS",
        "fact_ledger": {"path": str(fact_ledger), "sha256": sha256(fact_ledger)},
        "batch_size": args.batch_size,
        "person_count": len(bundles),
        "shard_count": len(shards),
        "coverage_states": dict(sorted(coverage.items())),
        "employment_candidate_count": sum(row["employment_candidate_count"] for row in bundles),
        "dated_employment_candidate_count": sum(row["dated_employment_candidate_count"] for row in bundles),
        "identity_matched_employment_candidate_count": sum(row["identity_matched_employment_candidate_count"] for row in bundles),
        "education_candidate_count": sum(row["education_candidate_count"] for row in bundles),
        "rejected_low_quality_line_count": rejected_lines,
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "shards": shards,
    }
    receipt_path = output_root / "bulk_profile_candidate_bundles_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
