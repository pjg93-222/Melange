#!/usr/bin/env python3
"""Build a deterministic, anchor-rich Google profile-search manifest.

The manifest is acquisition input only.  It does not fetch Google, LinkedIn,
or any other site, and it never promotes identity or employment facts.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
QUEUE = ROOT / "audits/staffer_network/public_employment_acquisition_queue_20260901_v3c_b/public_employment_acquisition_queue_25340.ndjson.gz"
COVERED = ROOT / "audits/staffer_network/lda_covered_position_employment_ledger_20260831/lda_covered_position_episode_candidates.ndjson.gz"
REGISTRANTS = ROOT / "audits/staffer_network/lda_registrant_employment_20260831/lda_registrant_employment_episodes.ndjson.gz"
HOUSE = ROOT / "audits/staffer_network/lda_house_payroll_matches_2016_2026/lda_house_payroll_match_candidates.ndjson.gz"
SENATE = ROOT / "audits/staffer_network/lda_senate_payroll_matches_2011_2026_v1/lda_senate_payroll_match_candidates.ndjson.gz"
LITTLESIS = ROOT / "audits/staffer_network/littlesis_lda_history_candidates_20260831/littlesis_lda_history_candidates.ndjson.gz"
ALREADY_CAPTURED = ROOT / "audits/staffer_network/linkedin_authenticated_evidence_20260901/linkedin_authenticated_evidence.ndjson"
AUTHENTICATED_RECEIPT = ROOT / "audits/staffer_network/linkedin_authenticated_evidence_20260901/linkedin_authenticated_evidence_receipt.json"


def read_ndjson(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                row = json.loads(line)
                if isinstance(row, dict):
                    yield row


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def title_name(value: str) -> str:
    return " ".join(part if len(part) <= 2 and part.isupper() else part.capitalize() for part in value.split())


def add_anchor(index: dict[str, list[dict[str, Any]]], person_id: str, anchor: dict[str, Any]) -> None:
    signature = json.dumps(anchor, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if all(json.dumps(existing, ensure_ascii=False, sort_keys=True, separators=(",", ":")) != signature for existing in index[person_id]):
        index[person_id].append(anchor)


def load_anchors() -> dict[str, list[dict[str, Any]]]:
    anchors: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_ndjson(COVERED):
        add_anchor(anchors, row["lda_source_person_id"], {
            "source": "lda_covered_position",
            "score": 50,
            "text": row.get("raw_covered_position_literal") or row.get("claim_text"),
        })
    for row in read_ndjson(HOUSE):
        add_anchor(anchors, row["lda_source_person_id"], {
            "source": "house_payroll",
            "score": 45,
            "text": " | ".join(filter(None, [row.get("employing_office_candidate"), row.get("title_candidate"), row.get("service_start_date_candidate"), row.get("service_end_date_candidate")])),
        })
    for row in read_ndjson(SENATE):
        intervals = row.get("observed_report_intervals") or []
        dates = "; ".join(f"{item.get('start')} to {item.get('end')}" for item in intervals[:2])
        add_anchor(anchors, row["lda_source_person_id"], {
            "source": "senate_payroll",
            "score": 45,
            "text": " | ".join(filter(None, [row.get("employing_office_candidate"), row.get("title_candidate"), dates])),
        })
    for row in read_ndjson(LITTLESIS):
        label = " | ".join(filter(None, [row.get("container_display_name"), row.get("title_or_degree_raw"), row.get("raw_start_date"), row.get("raw_end_date")]))
        add_anchor(anchors, row["lda_source_person_id"], {
            "source": f"littlesis_{str(row.get('fact_type', '')).lower()}",
            "score": 30,
            "text": label,
        })
    for row in read_ndjson(REGISTRANTS):
        add_anchor(anchors, row["lda_source_person_id"], {
            "source": "lda_registrant_association",
            "score": 20,
            "text": " | ".join(filter(None, [row.get("employer_name"), str(row.get("start_year") or ""), str(row.get("end_year") or "")])),
        })
    for values in anchors.values():
        values.sort(key=lambda item: (-item["score"], item["source"], item["text"] or ""))
    return anchors


def already_captured_ids() -> set[str]:
    ids = (
        {row["lda_source_person_id"] for row in read_ndjson(ALREADY_CAPTURED)}
        if ALREADY_CAPTURED.exists()
        else set()
    )
    if AUTHENTICATED_RECEIPT.exists():
        receipt = json.loads(AUTHENTICATED_RECEIPT.read_text(encoding="utf-8"))
        ids.update(
            item["lda_source_person_id"]
            for item in receipt.get("unresolved_linkedin_searches", [])
            if item.get("status") == "NO_IDENTITY_MATCH_AFTER_TARGETED_SEARCH"
        )
    return ids


def search_anchor_text(anchor: dict[str, Any]) -> str:
    text = " ".join(str(anchor.get("text") or "").split())
    return text[:180]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--max-persons", type=int, default=200)
    parser.add_argument(
        "--selection-offset",
        type=int,
        default=0,
        help="Skip this many deterministic eligible identities before selecting the batch.",
    )
    args = parser.parse_args()
    if args.max_persons < 1:
        raise SystemExit("--max-persons must be positive")
    if args.selection_offset < 0:
        raise SystemExit("--selection-offset must be nonnegative")

    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    anchors = load_anchors()
    captured = already_captured_ids()
    candidates: list[dict[str, Any]] = []
    for row in read_ndjson(QUEUE):
        person_id = row["lda_source_person_id"]
        if person_id in captured or person_id not in anchors:
            continue
        flags = row.get("evidence_flags") or {}
        counts = row.get("candidate_counts") or {}
        has_anchor = bool(
            flags.get("has_any_employment_candidate")
            or flags.get("has_education_candidate")
            or counts.get("base_house_payroll_match_groups")
            or counts.get("base_senate_payroll_match_groups")
            or counts.get("base_lda_covered_position_claims")
            or counts.get("littlesis_position")
        )
        if not has_anchor:
            continue
        best = anchors[person_id][0]
        candidates.append({
            "queue_ordinal": row.get("sealed_queue_ordinal", 10**9),
            "person_id": person_id,
            "display_name": row["display_name"],
            "priority": row.get("acquisition_priority"),
            "best_anchor_score": best["score"],
        })

    candidates.sort(key=lambda item: (-item["best_anchor_score"], item["queue_ordinal"], item["person_id"]))
    selection_end = args.selection_offset + args.max_persons
    selected = candidates[args.selection_offset : selection_end]
    rows: list[dict[str, Any]] = []
    for ordinal, candidate in enumerate(selected, start=1):
        person_id = candidate["person_id"]
        name = title_name(candidate["display_name"])
        person_anchors = anchors[person_id][:6]
        anchor = search_anchor_text(person_anchors[0])
        quoted_name = f'"{name}"'
        quoted_anchor = f'"{anchor}"' if anchor else ""
        queries = [
            f"site:linkedin.com/in {quoted_name} {quoted_anchor}".strip(),
            f"{quoted_name} {quoted_anchor} employment experience".strip(),
            f"{quoted_name} {quoted_anchor} biography LegiStorm".strip(),
        ]
        rows.append({
            "schema_id": "staffer-network-google-profile-search-target-v1",
            "search_ordinal": ordinal,
            "lda_source_person_id": person_id,
            "display_name": candidate["display_name"],
            "acquisition_priority": candidate["priority"],
            "identity_status": "REVIEW_REQUIRED",
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "anchors": person_anchors,
            "queries": queries,
        })

    manifest_path = output_root / "google_profile_search_manifest.ndjson.gz"
    with manifest_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write(canonical_bytes(row))
    receipt = {
        "schema_id": "staffer-network-google-profile-search-manifest-receipt-v1",
        "status": "PASS",
        "row_count": len(rows),
        "query_count": sum(len(row["queries"]) for row in rows),
        "selection_rule": "incomplete queue rows with existing employment, education, payroll, or covered-position anchors; strongest anchors first",
        "selection_offset": args.selection_offset,
        "eligible_candidate_count": len(candidates),
        "already_captured_excluded": len(captured),
        "network_requests": 0,
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "output": {
            "path": manifest_path.name,
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
        },
    }
    receipt_path = output_root / "google_profile_search_manifest_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
