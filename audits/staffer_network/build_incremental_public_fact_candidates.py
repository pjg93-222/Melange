#!/usr/bin/env python3
"""Convert incremental page captures into person-linked review-only fact spans."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from public_history_scraper import nested_urls, normalized_url, read_ndjson


def compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def seed_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern in (
        "legistorm_lda_profile_enrichment_*_slice_*.ndjson",
        "legistorm_lda_profile_fanout_*_slice_*.ndjson",
        "public_lda_profile_fanout_*_slice_*.ndjson",
    ):
        for path in sorted(root.glob(pattern)):
            rows.extend(read_ndjson(path))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-root", action="append", required=True)
    parser.add_argument("--capture-ledger", required=True)
    parser.add_argument("--capture-repair-ledger", action="append", default=[])
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    output_root = Path(args.output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    if any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")

    person: dict[str, dict[str, Any]] = {}
    url_people: defaultdict[str, set[str]] = defaultdict(set)
    for raw_root in args.seed_root:
        for seed in seed_rows(Path(raw_root)):
            source_id = seed["lda_source_person_id"]
            person.setdefault(source_id, {
                "lda_source_person_id": source_id,
                "display_name": seed["display_name"],
            })
            for raw_url in nested_urls(seed):
                url = normalized_url(raw_url)
                if url:
                    url_people[url].add(source_id)

    captures = {
        row["url"]: row for row in read_ndjson(Path(args.capture_ledger))
    }
    for raw_repair in args.capture_repair_ledger:
        for repair in read_ndjson(Path(raw_repair)):
            url = repair["url"]
            if url in captures:
                captures[url] = {**captures[url], **repair}
    spans: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for url in sorted(url_people):
        capture = captures.get(url)
        if not capture or capture.get("status") != "CAPTURED":
            continue
        hints = capture.get("hints", {})
        employment_lines = list(dict.fromkeys(hints.get("employment_lines", [])))
        education_lines = list(dict.fromkeys(hints.get("education_lines", [])))
        if not employment_lines and not education_lines and not hints.get("date_ranges"):
            continue
        span = {
            "evidence_status": "UNSTRUCTURED_REVIEW_REQUIRED",
            "canonical_eligible": False,
            "source_url": url,
            "final_url": capture.get("final_url"),
            "source_title": capture.get("title"),
            "content_sha256": capture.get("content_sha256"),
            "text_sha256": capture.get("text_sha256"),
            "text_path": capture.get("text_path"),
            "date_ranges": hints.get("date_ranges", []),
            "year_tokens": hints.get("year_tokens", []),
            "employment_lines": employment_lines,
            "education_lines": education_lines,
        }
        for source_id in sorted(url_people[url]):
            spans[source_id].append(span)

    rows: list[dict[str, Any]] = []
    for source_id in sorted(person):
        candidate_spans = sorted(
            spans.get(source_id, []), key=lambda item: (item["source_url"], item.get("text_sha256") or "")
        )
        rows.append({
            "schema_id": "staffer-network-incremental-public-fact-candidates-v1",
            **person[source_id],
            "identity_status": "REVIEW_REQUIRED",
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "complete_lifetime_employment_asserted": False,
            "captured_candidate_source_count": len(candidate_spans),
            "candidate_span_count": len(candidate_spans),
            "employment_line_count": sum(len(span["employment_lines"]) for span in candidate_spans),
            "education_line_count": sum(len(span["education_lines"]) for span in candidate_spans),
            "candidate_spans": candidate_spans,
        })

    ledger = output_root / "incremental_public_fact_candidates.ndjson"
    ledger.write_text("".join(compact(row) + "\n" for row in rows), encoding="utf-8", newline="\n")
    receipt = {
        "schema_id": "staffer-network-incremental-public-fact-candidates-receipt-v1",
        "status": "PASS",
        "person_count": len(rows),
        "persons_with_candidate_spans": sum(row["candidate_span_count"] > 0 for row in rows),
        "candidate_span_count": sum(row["candidate_span_count"] for row in rows),
        "employment_line_count": sum(row["employment_line_count"] for row in rows),
        "education_line_count": sum(row["education_line_count"] for row in rows),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "output": {
            "path": ledger.name,
            "bytes": ledger.stat().st_size,
            "sha256": sha256(ledger),
        },
    }
    receipt_path = output_root / "incremental_public_fact_candidates_receipt.json"
    receipt_path.write_text(compact(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact(receipt))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
