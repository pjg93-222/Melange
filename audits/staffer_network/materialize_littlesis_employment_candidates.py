#!/usr/bin/env python3
"""Materialize LittleSis employment/education rows for LDA identity candidates.

The normalized-name crosswalk is a review queue, not an identity decision.  This
adapter therefore emits source-bound candidate observations only and retains all
name multiplicity/collision signals needed for later adjudication.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_CANDIDATES = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
    "lda-identity-candidates/generation-20260830T231700Z/"
    "lda_identity_candidates.ndjson.gz"
)
DEFAULT_ENTITIES = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
    "source-native-corpus/generation-20260830T150500Z-e/"
    "littlesis_entities.ndjson.gz"
)
DEFAULT_RELATIONSHIPS = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
    "source-native-corpus/generation-20260830T150500Z-e/"
    "littlesis_relationship_assertions.ndjson.gz"
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gzip(path: Path, values: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6) as stream:
            for value in values:
                stream.write(canonical_bytes(value))
                count += 1
    return count


def has_date(value: str | None) -> bool:
    return bool(value and value not in {"0000-00-00", "0", "00"})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-candidates", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--entities", type=Path, default=DEFAULT_ENTITIES)
    parser.add_argument("--relationships", type=Path, default=DEFAULT_RELATIONSHIPS)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    for path in (args.identity_candidates, args.entities, args.relationships):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)

    candidate_by_target: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    littlesis_candidate_edges = 0
    for candidate in read_gzip(args.identity_candidates):
        if candidate.get("matched_source_system_id") != "littlesis":
            continue
        candidate_by_target[candidate["matched_source_entity_id"]].append(candidate)
        littlesis_candidate_edges += 1

    # Only retain names for candidate people and relationship objects that are
    # actually used.  The full entity file is still hashed and conserved by its
    # upstream receipt; this adapter does not rewrite it.
    entity_names: dict[str, str] = {}
    entity_types: dict[str, list[str]] = {}
    for entity in read_gzip(args.entities):
        entity_id = entity["source_entity_id"]
        entity_names[entity_id] = entity.get("display_name") or entity.get("name") or ""
        entity_types[entity_id] = entity.get("source_types") or entity.get("types") or []

    observations: list[dict[str, Any]] = []
    source_relationship_counts: Counter[str] = Counter()
    relationship_count_by_lda: Counter[str] = Counter()
    position_count_by_lda: Counter[str] = Counter()
    dated_position_count_by_lda: Counter[str] = Counter()
    education_count_by_lda: Counter[str] = Counter()
    source_relationships_scanned = 0
    matched_source_relationships = 0
    for relationship in read_gzip(args.relationships):
        source_relationships_scanned += 1
        category = relationship.get("category_name")
        if category not in {"Position", "Education"}:
            continue
        target_id = relationship.get("subject_source_entity_id")
        candidates = candidate_by_target.get(target_id)
        if not candidates:
            continue
        matched_source_relationships += 1
        source_relationship_counts[category] += 1
        object_id = relationship.get("object_source_entity_id")
        for candidate in candidates:
            lda_id = candidate["lda_source_person_id"]
            seed = (
                candidate["candidate_id"]
                + "\x1f"
                + relationship["source_relationship_id"]
            ).encode("utf-8")
            observation = {
                "schema_id": "staffer-network-littlesis-history-candidate-v1",
                "observation_id": "littlesis-history-candidate:" + hashlib.sha256(seed).hexdigest(),
                "fact_type": "EMPLOYMENT" if category == "Position" else "EDUCATION",
                "lda_source_person_id": lda_id,
                "lda_display_name": candidate["lda_display_name"],
                "littlesis_person_source_entity_id": target_id,
                "littlesis_person_display_name": entity_names.get(target_id) or candidate.get("matched_display_name"),
                "container_source_entity_id": object_id,
                "container_display_name": entity_names.get(object_id),
                "container_source_types": entity_types.get(object_id, []),
                "title_or_degree_raw": relationship.get("description2") or relationship.get("description1"),
                "description_raw": relationship.get("description"),
                "raw_start_date": relationship.get("raw_start_date"),
                "raw_end_date": relationship.get("raw_end_date"),
                "precision_bucket": relationship.get("precision_bucket"),
                "source_is_current": relationship.get("source_is_current"),
                "position_attributes": relationship.get("source_category_attributes") if category == "Position" else None,
                "source_relationship_id": relationship["source_relationship_id"],
                "source_url": relationship.get("source_url"),
                "source_updated_at": relationship.get("source_updated_at"),
                "identity_candidate_id": candidate["candidate_id"],
                "identity_match_method": candidate["method_version"],
                "lda_name_collision_max": candidate.get("lda_name_collision_max"),
                "target_name_collision_max": candidate.get("target_name_collision_max"),
                "target_cross_source_multiplicity_max": candidate.get("target_cross_source_multiplicity_max"),
                "identity_status": "REVIEW_REQUIRED",
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_history_fact": False,
                "complete_history_asserted": False,
            }
            observations.append(observation)
            relationship_count_by_lda[lda_id] += 1
            if category == "Position":
                position_count_by_lda[lda_id] += 1
                if has_date(relationship.get("raw_start_date")) or has_date(relationship.get("raw_end_date")):
                    dated_position_count_by_lda[lda_id] += 1
            else:
                education_count_by_lda[lda_id] += 1

    observations.sort(
        key=lambda row: (
            row["lda_source_person_id"],
            row["fact_type"],
            row["littlesis_person_source_entity_id"],
            row["source_relationship_id"],
        )
    )
    output_path = args.output_root / "littlesis_lda_history_candidates.ndjson.gz"
    output_count = write_gzip(output_path, observations)

    candidate_lda_ids = {
        candidate["lda_source_person_id"]
        for candidates in candidate_by_target.values()
        for candidate in candidates
    }
    receipt = {
        "schema_id": "staffer-network-littlesis-history-candidate-receipt-v1",
        "status": "PASS",
        "completion_priority": {
            "binding_primary": "EMPLOYMENT",
            "secondary_nonblocking": "EDUCATION",
        },
        "littlesis_identity_candidate_edges": littlesis_candidate_edges,
        "unique_lda_source_ids_with_littlesis_identity_candidate": len(candidate_lda_ids),
        "unique_littlesis_person_targets": len(candidate_by_target),
        "source_relationships_scanned": source_relationships_scanned,
        "matched_source_relationships": matched_source_relationships,
        "matched_source_relationship_counts": dict(sorted(source_relationship_counts.items())),
        "output_candidate_observations": output_count,
        "unique_lda_source_ids_with_any_history_candidate": len(relationship_count_by_lda),
        "unique_lda_source_ids_with_position_candidate": len(position_count_by_lda),
        "unique_lda_source_ids_with_dated_position_candidate": len(dated_position_count_by_lda),
        "unique_lda_source_ids_with_education_candidate": len(education_count_by_lda),
        "candidate_targets_without_position_observation": len(candidate_lda_ids - set(position_count_by_lda)),
        "canonical_identity_promotions": 0,
        "canonical_history_fact_promotions": 0,
        "complete_history_assertions": 0,
        "inputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (args.identity_candidates, args.entities, args.relationships)
        ],
        "output": {
            "path": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "risk_notes": [
            "Normalized-name equality is discovery evidence only and can represent collisions or aliases.",
            "Every observation inherits a REVIEW_REQUIRED identity candidate and is not canonical.",
            "LittleSis source dates and current flags are preserved as assertions, not adjudicated tenure.",
            "Multiple LDA source IDs or LittleSis targets are retained rather than silently collapsed.",
        ],
    }
    receipt_path = args.output_root / "littlesis_lda_history_candidate_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
