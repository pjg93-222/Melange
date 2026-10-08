#!/usr/bin/env python3
"""Build a deterministic one-row-per-LDA-ID employment/education coverage ledger.

The ledger is a coverage and gap accounting artifact.  It combines candidate
evidence counts without adjudicating an identity, promoting an employment fact,
or claiming a complete lifetime history.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_QUEUE = Path(
    "C:/Users/pgoff/AppData/Local/Melange/staffer_network/"
    "employment-lookup/generation-20260831T050000Z/"
    "employment_lookup_queue.ndjson.gz"
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
    if not path.exists():
        return
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


def dated_episode(episode: dict[str, Any]) -> bool:
    keys = (
        "start_date",
        "end_date",
        "start_year",
        "end_year",
        "raw_start_date",
        "raw_end_date",
        "date_start",
        "date_end",
    )
    return any(episode.get(key) not in (None, "", []) for key in keys)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument(
        "--lda-people",
        type=Path,
        default=Path("audits/staffer_network/lda_employment_materialization_20260831_v2/lda_employment_people.ndjson.gz"),
    )
    parser.add_argument(
        "--registrant-people",
        type=Path,
        default=Path("audits/staffer_network/lda_registrant_employment_20260831/lda_registrant_employment_people.ndjson.gz"),
    )
    parser.add_argument(
        "--house-matches",
        type=Path,
        default=Path("audits/staffer_network/lda_house_payroll_matches_2016_2026/lda_house_payroll_match_candidates.ndjson.gz"),
    )
    parser.add_argument(
        "--senate-matches",
        type=Path,
        default=Path("audits/staffer_network/lda_senate_payroll_matches_2025_2026/lda_senate_payroll_match_candidates.ndjson.gz"),
    )
    parser.add_argument(
        "--working-history",
        type=Path,
        default=Path("audits/staffer_network/working_history_corpus_20260831T180000Z_8workers/working_history_corpus.ndjson.gz"),
    )
    parser.add_argument(
        "--public-ledger",
        type=Path,
        default=Path("audits/staffer_network/linkedin_public_evidence_20260831_39rows/linkedin_public_evidence_ledger_20260831.ndjson"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    output_root = args.output_root
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    input_paths = [
        args.queue,
        args.lda_people,
        args.registrant_people,
        args.house_matches,
        args.senate_matches,
        args.working_history,
        args.public_ledger,
    ]
    missing_inputs = [str(path) for path in input_paths if not path.exists()]
    if missing_inputs:
        raise SystemExit("missing inputs: " + ", ".join(missing_inputs))

    queue = list(read_records(args.queue))
    queue_ids = [row["lda_source_person_id"] for row in queue]
    if len(queue_ids) != len(set(queue_ids)):
        raise SystemExit("queue contains duplicate lda_source_person_id values")
    universe = set(queue_ids)

    lda_people = {row["lda_source_person_id"]: row for row in read_records(args.lda_people)}
    registrant_people = {
        row["lda_source_person_id"]: row for row in read_records(args.registrant_people)
    }
    house_by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_records(args.house_matches):
        house_by_id[row["lda_source_person_id"]].append(row)
    senate_by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_records(args.senate_matches):
        senate_by_id[row["lda_source_person_id"]].append(row)
    working_by_id = {
        row["lda_source_person_id"]: row for row in read_records(args.working_history)
    }
    public_by_id = {
        row["lda_source_person_id"]: row for row in read_records(args.public_ledger)
    }

    auxiliary_sets = {
        "lda_people": set(lda_people),
        "registrant_people": set(registrant_people),
        "house_matches": set(house_by_id),
        "senate_matches": set(senate_by_id),
        "working_history": set(working_by_id),
        "public_ledger": set(public_by_id),
    }
    outside_universe = {
        name: sorted(values - universe) for name, values in auxiliary_sets.items() if values - universe
    }
    if outside_universe:
        raise SystemExit("auxiliary IDs outside queue universe: " + json.dumps(outside_universe, sort_keys=True))
    if set(lda_people) != universe:
        raise SystemExit("LDA employment people do not exactly cover queue universe")
    if set(registrant_people) != universe:
        raise SystemExit("registrant people do not exactly cover queue universe")

    rows = []
    outcome_counts: Counter[str] = Counter()
    gap_counts: Counter[str] = Counter()
    for queue_row in sorted(queue, key=lambda row: row["lda_source_person_id"]):
        person_id = queue_row["lda_source_person_id"]
        lda = lda_people[person_id]
        registrant = registrant_people[person_id]
        house = house_by_id.get(person_id, [])
        senate = senate_by_id.get(person_id, [])
        working = working_by_id.get(person_id)
        public = public_by_id.get(person_id)

        working_employment = (working or {}).get("employment_episodes") or []
        working_education = (working or {}).get("education") or []
        public_facts = (public or {}).get("candidate_facts") or []
        public_employment = [fact for fact in public_facts if fact.get("fact_type") == "EMPLOYMENT"]
        public_education = [fact for fact in public_facts if fact.get("fact_type") == "EDUCATION"]

        lda_substantive = int(lda.get("substantive_position_claim_count") or 0)
        lda_explicit_year = bool(lda.get("has_explicit_year_token"))
        registrant_count = int(registrant.get("employment_episode_count") or 0)
        house_support_rows = sum(int(row.get("payroll_row_support_count") or 0) for row in house)
        senate_support_rows = sum(int(row.get("payroll_row_support_count") or 0) for row in senate)
        working_dated = sum(dated_episode(episode) for episode in working_employment)
        public_employment_dated = sum(dated_episode(fact) for fact in public_employment)
        public_education_dated = sum(dated_episode(fact) for fact in public_education)

        has_former_position_candidate = bool(lda_substantive or house or senate or working_employment or public_employment)
        has_dated_employment_candidate = bool(
            lda_explicit_year
            or house
            or senate
            or working_dated
            or public_employment_dated
            or registrant.get("has_dated_employment_evidence")
        )
        has_education_candidate = bool(working_education or public_education)

        if house or senate:
            outcome = "OFFICIAL_PAYROLL_AND_OTHER_PARTIAL_EVIDENCE"
        elif working_employment or public_employment:
            outcome = "PUBLIC_HISTORY_AND_OTHER_PARTIAL_EVIDENCE"
        elif lda_substantive:
            outcome = "LDA_COVERED_POSITION_AND_REGISTRANT_ASSOCIATION_ONLY"
        else:
            outcome = "LDA_REGISTRANT_ASSOCIATION_ONLY"
        outcome_counts[outcome] += 1

        gaps = [
            "IDENTITY_NOT_ADJUDICATED",
            "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
            "PRIVATE_SECTOR_HISTORY_NOT_EXHAUSTIVE",
            "HILL_HISTORY_NOT_EXHAUSTIVE",
        ]
        if not has_dated_employment_candidate:
            gaps.append("DATED_EMPLOYMENT_EVIDENCE_MISSING")
        if not has_education_candidate:
            gaps.append("EDUCATION_EVIDENCE_MISSING")
        if not house:
            gaps.append("HOUSE_PAYROLL_MATCH_MISSING_IN_CURRENT_WINDOW")
        if not senate:
            gaps.append("SENATE_PAYROLL_MATCH_MISSING_IN_CURRENT_WINDOW")
        for gap in gaps:
            gap_counts[gap] += 1

        critical_path_gaps = sorted(gap for gap in gaps if gap != "EDUCATION_EVIDENCE_MISSING")
        secondary_enrichment_gaps = (
            ["EDUCATION_EVIDENCE_MISSING"] if "EDUCATION_EVIDENCE_MISSING" in gaps else []
        )
        row = {
            "schema_id": "staffer-network-lda-history-coverage-ledger-v1",
            "lda_source_person_id": person_id,
            "display_name": queue_row["display_name"],
            "queue_priority": queue_row["priority"],
            "coverage_outcome": outcome,
            "coverage_is_explicit": True,
            "identity_status": "NOT_ADJUDICATED",
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "complete_lifetime_employment_asserted": False,
            "complete_education_history_asserted": False,
            "completion_priority": {
                "binding_primary": "COMPLETE_EMPLOYMENT_CHRONOLOGY",
                "secondary_enrichment": "EDUCATION",
            },
            "evidence_counts": {
                "lda_substantive_covered_position_claims": lda_substantive,
                "lda_claims_with_explicit_year_token": int(lda_explicit_year),
                "lda_registrant_association_episodes": registrant_count,
                "house_payroll_match_groups": len(house),
                "house_payroll_support_rows": house_support_rows,
                "senate_payroll_match_groups": len(senate),
                "senate_payroll_support_rows": senate_support_rows,
                "working_history_employment_episodes": len(working_employment),
                "working_history_education_episodes": len(working_education),
                "public_ledger_employment_facts": len(public_employment),
                "public_ledger_education_facts": len(public_education),
            },
            "evidence_flags": {
                "has_former_position_candidate": has_former_position_candidate,
                "has_dated_employment_candidate": has_dated_employment_candidate,
                "has_education_candidate": has_education_candidate,
                "has_house_payroll_candidate": bool(house),
                "has_senate_payroll_candidate": bool(senate),
                "has_public_or_working_history_candidate": bool(working or public),
                "has_registrant_association_candidate": bool(registrant_count),
            },
            "current_gap_codes": sorted(gaps),
            "critical_path_gap_codes": critical_path_gaps,
            "secondary_enrichment_gap_codes": secondary_enrichment_gaps,
            "source_windows": {
                "lda_filings": "2021-2026_SEALED_SOURCE_WINDOW",
                "house_payroll": "2016Q1-2026Q1_CURRENTLY_MATCHED",
                "senate_payroll": "2025-10-01_TO_2026-03-31_CURRENTLY_MATCHED",
                "public_history": "EXISTING_PARTIAL_CORPUS",
            },
        }
        rows.append(row)

    output_path = output_root / "lda_history_coverage_ledger.ndjson.gz"
    output_count = write_gzip(output_path, rows)
    if output_count != len(queue):
        raise SystemExit("output row conservation failed")

    receipt = {
        "schema_id": "staffer-network-lda-history-coverage-receipt-v1",
        "status": "PASS",
        "scope": "ALL_LDA_SOURCE_IDENTITIES_IN_SEALED_EMPLOYMENT_LOOKUP_QUEUE",
        "queue_rows": len(queue),
        "unique_lda_source_person_ids": len(universe),
        "output_rows": output_count,
        "coverage_conservation": output_count == len(queue) == len(universe),
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "gap_counts": dict(sorted(gap_counts.items())),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_history_assertions": 0,
        "completion_policy": {
            "binding_primary": "COMPLETE_EMPLOYMENT_CHRONOLOGY_WITH_EMPLOYER_OR_OFFICE_TITLE_AND_BOUNDED_DATES",
            "secondary_nonblocking": "EDUCATION",
        },
        "inputs": [
            {
                "path": str(path),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in input_paths
        ],
        "output": {
            "path": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "risk_notes": [
            "The 25,340 rows are LDA source identities, not a deduplicated human count.",
            "Registrant filing association is not asserted as continuous employment.",
            "Exact-name payroll joins and public-history rows remain unadjudicated candidates.",
            "Explicit coverage means every source ID has an outcome and gap accounting, not that every history is complete.",
            "The ledger must be rebuilt against new immutable House, Senate, or public evidence generations.",
        ],
    }
    receipt_path = output_root / "lda_history_coverage_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
