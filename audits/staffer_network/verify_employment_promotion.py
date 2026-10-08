"""Independent checks for the employment promotion and affiliation artifacts."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterator

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fec.staffer_network.publication import _validate_record_semantics
from fec.staffer_network.schema_validation import validate_instance
from fec.staffer_network.source_manifest import canonical_json_bytes, sha256_file


EPISODE_SCHEMA = json.loads(
    (ROOT / "fec/staffer_network/schemas/employment_episode.schema.json").read_text(encoding="utf-8")
)


def rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for ordinal, line in enumerate(handle, start=1):
            if not line.strip():
                raise AssertionError(f"blank NDJSON line: {path.name}:{ordinal}")
            yield json.loads(line)


def support_digest(values: list[str]) -> str:
    return hashlib.sha256("\0".join(sorted(set(values))).encode("utf-8")).hexdigest()


def verify(primary: Path, twin: Path, output: Path) -> dict[str, Any]:
    first = json.loads((primary / "employment_promotion_receipt.json").read_text(encoding="utf-8"))
    second = json.loads((twin / "employment_promotion_receipt.json").read_text(encoding="utf-8"))
    assertions: dict[str, bool] = {}
    assertions["receipts_equal"] = first == second
    assertions["quarantine_disabled"] = first.get("quarantine_enabled") is False
    assertions["removed_gates_exact"] = set(first.get("removed_gates") or []) == {
        "IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED",
        "SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED",
        "FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED",
    }
    assertions["retained_gates_exact"] = set(first.get("retained_gates") or []) == {
        "COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED",
        "CONTAINER_ADJUDICATION_REQUIRED",
    }
    for entry in first["files"]:
        name = entry["path"]
        left, right = primary / name, twin / name
        assertions[f"primary_hash:{name}"] = sha256_file(left) == entry["sha256"]
        assertions[f"twin_hash:{name}"] = sha256_file(right) == entry["sha256"]
        assertions[f"byte_twin:{name}"] = left.read_bytes() == right.read_bytes()

    episodes = list(rows(primary / "canonical_employment_episodes.ndjson.gz"))
    episode_ids = [row["episode_id"] for row in episodes]
    assertions["episode_count"] = len(episodes) == first["counts"]["canonical_employment_episodes"]
    assertions["episode_ids_unique"] = len(episode_ids) == len(set(episode_ids))
    for row in episodes:
        validate_instance(row, EPISODE_SCHEMA)
        _validate_record_semantics(row, row["schema_id"])
    assertions["all_episodes_canonical_active_accepted"] = all(
        row["episode_status"] == "ACTIVE"
        and row["identity_status"] == "ACCEPTED"
        and row["container_status"] == "ACCEPTED"
        for row in episodes
    )

    decisions = list(rows(primary / "employment_promotion_decisions.ndjson.gz"))
    decision_ids = [row["decision_id"] for row in decisions]
    assertions["decision_count"] = len(decisions) == first["counts"]["promotion_decisions"]
    assertions["decision_ids_unique"] = len(decision_ids) == len(set(decision_ids))
    assertions["decisions_reference_canonical_episode"] = all(
        row["episode_id"] in set(episode_ids) for row in decisions
    )

    memberships = list(rows(primary / "service_affiliation_memberships.ndjson.gz"))
    groups = list(rows(primary / "service_affiliation_groups.ndjson.gz"))
    edges = list(rows(primary / "shared_affiliation_edges.ndjson.gz"))
    assertions["membership_count"] = len(memberships) == first["counts"]["affiliation_memberships"]
    assertions["group_count"] = len(groups) == first["counts"]["affiliation_groups"]
    assertions["edge_count"] = len(edges) == first["counts"]["shared_affiliation_edges"]
    assertions["edge_ids_unique"] = len(edges) == len({row["edge_id"] for row in edges})
    assertions["edge_no_self_loops"] = all(row["subject_id"] != row["object_id"] for row in edges)
    assertions["edge_weights_exact"] = all(
        math.isclose(
            row["edge_weight"], 1.0 - math.exp(-row["overlap_days"] / first["tau_days"]),
            rel_tol=0.0, abs_tol=1e-15,
        )
        for row in edges
    )
    assertions["edge_support_digests"] = all(
        row["support_digest"] == support_digest(row["support_ids"]) for row in edges
    )

    stephanie = [row for row in episodes if row["resolved_person_id"] == "lda:lobbyist:147663"]
    stephanie_education = [
        row for row in rows(primary / "canonical_education_records.ndjson.gz")
        if row["person_id"] == "lda:lobbyist:147663"
    ]
    stephanie_support = {
        support for row in stephanie for support in row["support_observation_ids"]
    }
    assertions["stephanie_five_profile_jobs"] = sum(
        any(item.startswith("authenticated-profile-fact:") for item in row["support_observation_ids"])
        for row in stephanie
    ) == 5
    assertions["stephanie_one_education"] = len(stephanie_education) == 1
    assertions["stephanie_seven_senate_intervals"] = sum(
        any(item.startswith("senate-interval:") for item in row["support_observation_ids"])
        for row in stephanie
    ) == 7
    assertions["stephanie_lda_literal_retained"] = (
        "lda:employment-claim:v2:2147dbcd5e1cef2bd393ace0dc3f0c4f2278fc5778f8ea556c5d6d8f05a84561"
        in stephanie_support
    )
    assertions["stephanie_registrant_container"] = any(
        row["normalized_container_id"] == "lda:registrant:11322" for row in stephanie
    )

    failures = sorted(name for name, passed in assertions.items() if not passed)
    receipt = {
        "schema_id": "staffer-network-employment-promotion-verification-v1",
        "status": "PASS" if not failures else "FAIL",
        "assertions": assertions,
        "failures": failures,
        "counts": first["counts"],
        "canonical_people": first["canonical_people"],
        "primary_receipt_sha256": sha256_file(primary / "employment_promotion_receipt.json"),
        "twin_receipt_sha256": sha256_file(twin / "employment_promotion_receipt.json"),
        "gate_disposition_counts": dict(Counter(
            row["container_gate"] for row in decisions
        )),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_json_bytes(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--twin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    receipt = verify(args.primary, args.twin, args.output)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
