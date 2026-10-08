#!/usr/bin/env python3
"""Join LDA review candidates to normalized Politico Pro directory role text.

The directory supplies an observation-time role assertion, not a full dated
employment episode.  All rows remain review-required candidate evidence.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_IDENTITY_CANDIDATES = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
    "lda-identity-candidates/generation-20260830T231700Z/"
    "lda_identity_candidates.ndjson.gz"
)
DEFAULT_POLITICO_ROOT = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
    "politico/normalized-20260829T230000-0400"
)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_records(path: Path) -> Iterable[dict[str, Any]]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    else:
        with path.open("rt", encoding="utf-8") as stream:
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--identity-candidates", type=Path, default=DEFAULT_IDENTITY_CANDIDATES)
    parser.add_argument("--politico-root", type=Path, default=DEFAULT_POLITICO_ROOT)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    persons_path = args.politico_root / "persons.ndjson"
    roles_path = args.politico_root / "role_assertions.ndjson"
    for path in (args.identity_candidates, persons_path, roles_path):
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)

    candidates_by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in read_records(args.identity_candidates):
        if candidate.get("matched_source_system_id") == "politico-pro-staffer-directory":
            candidates_by_person[candidate["matched_source_entity_id"]].append(candidate)
    persons = {row["source_person_id"]: row for row in read_records(persons_path)}

    output_rows = []
    targets_with_roles = set()
    lda_ids_with_roles = set()
    for role in read_records(roles_path):
        source_person_id = role["source_person_id"]
        candidates = candidates_by_person.get(source_person_id)
        if not candidates:
            continue
        targets_with_roles.add(source_person_id)
        for candidate in candidates:
            seed = (candidate["candidate_id"] + "\x1f" + role["assertion_id"]).encode("utf-8")
            lda_ids_with_roles.add(candidate["lda_source_person_id"])
            output_rows.append(
                {
                    "schema_id": "staffer-network-politico-employment-candidate-v1",
                    "observation_id": "politico-employment-candidate:" + hashlib.sha256(seed).hexdigest(),
                    "lda_source_person_id": candidate["lda_source_person_id"],
                    "lda_display_name": candidate["lda_display_name"],
                    "politico_source_person_id": source_person_id,
                    "politico_display_name": (persons.get(source_person_id) or {}).get("display_name"),
                    "role_text_raw": role.get("role_text"),
                    "observed_at": role.get("observed_at"),
                    "date_basis": "DIRECTORY_OBSERVATION_TIME_ONLY",
                    "identity_candidate_id": candidate["candidate_id"],
                    "identity_match_method": candidate["method_version"],
                    "lda_name_collision_max": candidate.get("lda_name_collision_max"),
                    "target_name_collision_max": candidate.get("target_name_collision_max"),
                    "target_cross_source_multiplicity_max": candidate.get("target_cross_source_multiplicity_max"),
                    "identity_status": "REVIEW_REQUIRED",
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "canonical_employment_fact": False,
                    "complete_history_asserted": False,
                }
            )

    output_rows.sort(
        key=lambda row: (
            row["lda_source_person_id"],
            row["politico_source_person_id"],
            row["observation_id"],
        )
    )
    output_path = args.output_root / "politico_lda_employment_candidates.ndjson.gz"
    output_count = write_gzip(output_path, output_rows)
    candidate_lda_ids = {
        candidate["lda_source_person_id"]
        for candidates in candidates_by_person.values()
        for candidate in candidates
    }
    receipt = {
        "schema_id": "staffer-network-politico-employment-candidate-receipt-v1",
        "status": "PASS",
        "identity_candidate_edges": sum(len(values) for values in candidates_by_person.values()),
        "unique_lda_source_ids_with_identity_candidate": len(candidate_lda_ids),
        "unique_politico_person_targets": len(candidates_by_person),
        "unique_politico_targets_with_role": len(targets_with_roles),
        "unique_lda_source_ids_with_role_candidate": len(lda_ids_with_roles),
        "output_candidate_observations": output_count,
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_history_assertions": 0,
        "inputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in (args.identity_candidates, persons_path, roles_path)
        ],
        "output": {
            "path": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "risk_notes": [
            "Normalized-name equality is an unadjudicated identity candidate.",
            "Politico directory observation time does not establish a role start or end date.",
            "Role text is preserved raw and is not parsed into a canonical employer or title here.",
            "The local source is enabled for restricted internal analysis; this artifact grants no redistribution right.",
        ],
    }
    receipt_path = args.output_root / "politico_lda_employment_candidate_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
