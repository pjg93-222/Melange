#!/usr/bin/env python3
"""Build an employment-first acquisition queue for every sealed LDA source ID.

This queue layers the repaired public corpus plus LittleSis and Politico role
candidates over the existing full-universe coverage ledger.  It is deliberately
candidate-only: normalized-name edges remain review work and no identity or
employment fact is promoted to canonical state.
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
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_records(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=6
        ) as stream:
            for row in rows:
                stream.write(canonical_bytes(row))
                count += 1
    return count


def stated(value: Any) -> bool:
    return value not in (None, "", [], {}, "0000-00-00", "0", "00")


def public_fact_is_dated(fact: dict[str, Any]) -> bool:
    if any(stated(fact.get(key)) for key in ("raw_start_date", "raw_end_date", "raw_dates")):
        return True
    return fact.get("date_granularity") not in (
        None,
        "",
        "DATE_NOT_STATED",
        "YEAR_NOT_STATED",
        "RAW_DATE_UNCLASSIFIED",
        "UNPARSED_NARRATIVE",
    )


def public_fact_is_bounded(fact: dict[str, Any]) -> bool:
    if stated(fact.get("raw_start_date")) and stated(fact.get("raw_end_date")):
        return True
    return stated(fact.get("raw_dates")) and fact.get("date_granularity") in {
        "MULTIPLE_PUBLIC_PAYMENT_PERIODS",
        "PUBLIC_PAYMENT_PERIOD",
        "PUBLIC_PAYMENT_PERIOD_WITH_REPORTED_BREAKS",
        "YEAR_EVIDENCE_WINDOW",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument(
        "--base-coverage",
        type=Path,
        default=Path(
            "audits/staffer_network/"
            "lda_history_coverage_20260831_checkpoint2_employment_priority/"
            "lda_history_coverage_ledger.ndjson.gz"
        ),
    )
    parser.add_argument(
        "--public-ledger",
        type=Path,
        default=Path(
            "audits/staffer_network/"
            "public_evidence_generation_20260831T235930Z_g1371_pdf109_v1/"
            "public_evidence_ledger_1371.ndjson"
        ),
    )
    parser.add_argument(
        "--legacy-public-ledger",
        type=Path,
        default=Path(
            "audits/staffer_network/linkedin_public_evidence_20260831_39rows/"
            "linkedin_public_evidence_ledger_20260831.ndjson"
        ),
    )
    parser.add_argument(
        "--littlesis",
        type=Path,
        default=Path(
            "audits/staffer_network/littlesis_lda_history_candidates_20260831/"
            "littlesis_lda_history_candidates.ndjson.gz"
        ),
    )
    parser.add_argument(
        "--politico",
        type=Path,
        default=Path(
            "audits/staffer_network/politico_lda_employment_candidates_20260831/"
            "politico_lda_employment_candidates.ndjson.gz"
        ),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()

    inputs = [
        args.queue,
        args.base_coverage,
        args.public_ledger,
        args.legacy_public_ledger,
        args.littlesis,
        args.politico,
    ]
    for path in inputs:
        if not path.exists():
            raise SystemExit(f"missing input: {path}")
    if args.output_root.exists() and any(args.output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {args.output_root}")
    args.output_root.mkdir(parents=True, exist_ok=True)

    queue_rows = list(read_records(args.queue))
    queue_ids = [row["lda_source_person_id"] for row in queue_rows]
    universe = set(queue_ids)
    if len(queue_ids) != len(universe):
        raise SystemExit("sealed queue has duplicate lda_source_person_id values")
    queue_ordinal = {person_id: index + 1 for index, person_id in enumerate(queue_ids)}
    queue_by_id = {row["lda_source_person_id"]: row for row in queue_rows}

    base_by_id = {
        row["lda_source_person_id"]: row for row in read_records(args.base_coverage)
    }
    if set(base_by_id) != universe:
        raise SystemExit("base coverage does not exactly conserve the sealed queue")

    public_by_id: dict[str, dict[str, Any]] = {}
    for row in read_records(args.public_ledger):
        person_id = row["lda_source_person_id"]
        if person_id in public_by_id:
            raise SystemExit(f"duplicate public row: {person_id}")
        public_by_id[person_id] = row

    legacy_public_by_id: dict[str, dict[str, Any]] = {}
    for row in read_records(args.legacy_public_ledger):
        person_id = row["lda_source_person_id"]
        if person_id in legacy_public_by_id:
            raise SystemExit(f"duplicate legacy public row: {person_id}")
        legacy_public_by_id[person_id] = row

    littlesis_by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_records(args.littlesis):
        littlesis_by_id[row["lda_source_person_id"]].append(row)

    politico_by_id: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_records(args.politico):
        politico_by_id[row["lda_source_person_id"]].append(row)

    auxiliary = {
        "public": set(public_by_id),
        "legacy_public": set(legacy_public_by_id),
        "littlesis": set(littlesis_by_id),
        "politico": set(politico_by_id),
    }
    outside = {name: sorted(ids - universe) for name, ids in auxiliary.items() if ids - universe}
    if outside:
        raise SystemExit("candidate IDs outside sealed queue: " + json.dumps(outside, sort_keys=True))

    rows: list[dict[str, Any]] = []
    gap_counts: Counter[str] = Counter()
    priority_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    evidence_outcome_counts: Counter[str] = Counter()
    candidate_source_combination_counts: Counter[str] = Counter()

    for person_id in sorted(universe):
        queue_row = queue_by_id[person_id]
        base = base_by_id[person_id]
        public = public_by_id.get(person_id)
        legacy_public = legacy_public_by_id.get(person_id)
        littlesis_rows = littlesis_by_id.get(person_id, [])
        politico_rows = politico_by_id.get(person_id, [])

        public_facts = (public or {}).get("candidate_facts") or []
        public_employment = [fact for fact in public_facts if fact.get("fact_type") == "EMPLOYMENT"]
        public_external_employment = [
            fact
            for fact in public_employment
            if fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
        ]
        public_education = [fact for fact in public_facts if fact.get("fact_type") == "EDUCATION"]
        legacy_public_facts = (legacy_public or {}).get("candidate_facts") or []
        legacy_public_employment = [
            fact for fact in legacy_public_facts if fact.get("fact_type") == "EMPLOYMENT"
        ]
        legacy_public_external_employment = [
            fact
            for fact in legacy_public_employment
            if fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
        ]
        legacy_public_education = [
            fact for fact in legacy_public_facts if fact.get("fact_type") == "EDUCATION"
        ]
        littlesis_positions = [row for row in littlesis_rows if row.get("fact_type") == "EMPLOYMENT"]
        littlesis_education = [row for row in littlesis_rows if row.get("fact_type") == "EDUCATION"]

        public_dated = sum(public_fact_is_dated(fact) for fact in public_external_employment)
        public_bounded = sum(public_fact_is_bounded(fact) for fact in public_external_employment)
        legacy_public_dated = sum(
            public_fact_is_dated(fact) for fact in legacy_public_external_employment
        )
        legacy_public_bounded = sum(
            public_fact_is_bounded(fact) for fact in legacy_public_external_employment
        )
        littlesis_dated = sum(
            stated(row.get("raw_start_date")) or stated(row.get("raw_end_date"))
            for row in littlesis_positions
        )
        littlesis_bounded = sum(
            stated(row.get("raw_start_date")) and stated(row.get("raw_end_date"))
            for row in littlesis_positions
        )

        base_counts = base["evidence_counts"]
        base_flags = base["evidence_flags"]
        payroll_bounded = (
            int(base_counts.get("house_payroll_match_groups") or 0)
            + int(base_counts.get("senate_payroll_match_groups") or 0)
        )
        has_any_employment_candidate = bool(
            base_flags.get("has_former_position_candidate")
            or public_external_employment
            or legacy_public_external_employment
            or littlesis_positions
            or politico_rows
        )
        has_any_dated_candidate = bool(
            base_flags.get("has_dated_employment_candidate")
            or public_dated
            or legacy_public_dated
            or littlesis_dated
        )
        has_dated_former_position_candidate = bool(
            has_any_employment_candidate
            and (
                payroll_bounded
                or int(base_counts.get("lda_claims_with_explicit_year_token") or 0)
                or public_dated
                or legacy_public_dated
                or littlesis_dated
            )
        )
        has_any_bounded_candidate = bool(
            payroll_bounded
            or public_bounded
            or legacy_public_bounded
            or littlesis_bounded
        )
        has_public_third_party_candidate = bool(
            public_external_employment
            or legacy_public_external_employment
            or littlesis_positions
            or politico_rows
        )
        has_education_candidate = bool(
            base_flags.get("has_education_candidate")
            or public_education
            or legacy_public_education
            or littlesis_education
        )

        gaps = [
            "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
            "EMPLOYMENT_GAPS_NOT_ADJUDICATED",
            "HILL_HISTORY_NOT_EXHAUSTIVE",
            "IDENTITY_NOT_ADJUDICATED",
            "PRIVATE_SECTOR_HISTORY_NOT_EXHAUSTIVE",
        ]
        if not has_any_employment_candidate:
            gaps.append("FORMER_POSITION_CANDIDATE_MISSING")
        if not has_dated_former_position_candidate:
            gaps.append("DATED_FORMER_POSITION_CANDIDATE_MISSING")
        if not has_any_bounded_candidate:
            gaps.append("BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING")
        if not has_public_third_party_candidate:
            gaps.append("PUBLIC_THIRD_PARTY_EMPLOYMENT_CANDIDATE_MISSING")
        if public or legacy_public or littlesis_positions or politico_rows:
            gaps.append("NAME_MATCH_REQUIRES_IDENTITY_ADJUDICATION")
        gaps = sorted(set(gaps))
        for gap in gaps:
            gap_counts[gap] += 1

        if not has_any_employment_candidate:
            priority = "P0_ACQUIRE_FORMER_POSITION"
            route = "OFFICIAL_OR_EMPLOYER_BIO_AND_ARCHIVE_SEARCH"
        elif not has_dated_former_position_candidate:
            priority = "P0_ACQUIRE_DATED_EMPLOYMENT"
            route = "OFFICIAL_OR_EMPLOYER_BIO_AND_ARCHIVE_SEARCH"
        elif not has_any_bounded_candidate:
            priority = "P1_ACQUIRE_BOUNDED_EMPLOYMENT_INTERVALS"
            route = "DATED_PAYROLL_OR_PROFILE_TIMELINE_SEARCH"
        else:
            priority = "P2_ADJUDICATE_AND_FILL_CHRONOLOGY_GAPS"
            route = "IDENTITY_ADJUDICATION_THEN_GAP_DIRECTED_SEARCH"
        priority_counts[priority] += 1
        route_counts[route] += 1

        source_labels = []
        if public_external_employment:
            source_labels.append("PUBLIC_REPAIRED_CORPUS")
        if legacy_public_external_employment:
            source_labels.append("PUBLIC_CHECKPOINT_39")
        if littlesis_positions:
            source_labels.append("LITTLESIS_POSITION_CANDIDATE")
        if politico_rows:
            source_labels.append("POLITICO_ROLE_CANDIDATE")
        combination = "+".join(source_labels) if source_labels else "NO_NEW_PUBLIC_CANDIDATE"
        candidate_source_combination_counts[combination] += 1

        if not has_any_employment_candidate:
            outcome = "NO_FORMER_POSITION_CANDIDATE"
        elif has_any_bounded_candidate:
            outcome = "HAS_BOUNDED_EMPLOYMENT_CANDIDATE_NOT_ADJUDICATED"
        elif has_dated_former_position_candidate:
            outcome = "HAS_DATED_EMPLOYMENT_CANDIDATE_NOT_BOUNDED"
        else:
            outcome = "HAS_UNDATED_EMPLOYMENT_CANDIDATE"
        evidence_outcome_counts[outcome] += 1

        row = {
            "schema_id": "staffer-network-public-employment-acquisition-queue-v2",
            "lda_source_person_id": person_id,
            "display_name": queue_row["display_name"],
            "sealed_queue_ordinal": queue_ordinal[person_id],
            "sealed_queue_priority": queue_row.get("priority"),
            "binding_objective": "COMPLETE_EMPLOYMENT_CHRONOLOGY_WITH_EMPLOYER_OR_OFFICE_TITLE_AND_BOUNDED_DATES",
            "secondary_nonblocking": "EDUCATION",
            "identity_status": "REVIEW_REQUIRED",
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "complete_lifetime_employment_asserted": False,
            "acquisition_priority": priority,
            "next_acquisition_route": route,
            "evidence_outcome": outcome,
            "new_public_candidate_sources": source_labels,
            "candidate_counts": {
                "repaired_public_employment_all_including_lda_context": len(public_employment),
                "repaired_public_external_employment": len(public_external_employment),
                "repaired_public_external_employment_dated": public_dated,
                "repaired_public_external_employment_bounded": public_bounded,
                "legacy_public_external_employment": len(legacy_public_external_employment),
                "legacy_public_external_employment_dated": legacy_public_dated,
                "legacy_public_external_employment_bounded": legacy_public_bounded,
                "littlesis_position": len(littlesis_positions),
                "littlesis_position_dated": littlesis_dated,
                "littlesis_position_bounded": littlesis_bounded,
                "politico_role_observation_time_only": len(politico_rows),
                "base_house_payroll_match_groups": int(base_counts.get("house_payroll_match_groups") or 0),
                "base_senate_payroll_match_groups": int(base_counts.get("senate_payroll_match_groups") or 0),
                "base_lda_covered_position_claims": int(base_counts.get("lda_substantive_covered_position_claims") or 0),
                "base_registrant_association_episodes": int(base_counts.get("lda_registrant_association_episodes") or 0),
            },
            "evidence_flags": {
                "has_any_employment_candidate": has_any_employment_candidate,
                "has_any_dated_employment_candidate": has_any_dated_candidate,
                "has_dated_former_position_candidate": has_dated_former_position_candidate,
                "has_any_bounded_employment_candidate": has_any_bounded_candidate,
                "has_public_third_party_employment_candidate": has_public_third_party_candidate,
                "has_education_candidate": has_education_candidate,
            },
            "critical_path_gap_codes": gaps,
            "secondary_enrichment_gap_codes": (
                [] if has_education_candidate else ["EDUCATION_EVIDENCE_MISSING_NONBLOCKING"]
            ),
            "source_candidate_ids": {
                "public_generation_id": (public or {}).get("generation_id"),
                "legacy_public_generation_id": (legacy_public or {}).get("generation_id"),
                "littlesis_identity_candidate_ids": sorted(
                    {row["identity_candidate_id"] for row in littlesis_rows}
                ),
                "politico_identity_candidate_ids": sorted(
                    {row["identity_candidate_id"] for row in politico_rows}
                ),
            },
        }
        rows.append(row)

    rows.sort(
        key=lambda row: (
            {"P0_ACQUIRE_FORMER_POSITION": 0, "P0_ACQUIRE_DATED_EMPLOYMENT": 1, "P1_ACQUIRE_BOUNDED_EMPLOYMENT_INTERVALS": 2, "P2_ADJUDICATE_AND_FILL_CHRONOLOGY_GAPS": 3}[row["acquisition_priority"]],
            row["sealed_queue_ordinal"],
            row["lda_source_person_id"],
        )
    )

    output_path = args.output_root / "public_employment_acquisition_queue_25340.ndjson.gz"
    output_count = write_gzip(output_path, rows)
    if output_count != len(universe) or output_count != 25340:
        raise SystemExit(f"queue conservation failed: {output_count} vs {len(universe)}")

    receipt = {
        "schema_id": "staffer-network-public-employment-acquisition-queue-receipt-v2",
        "status": "PASS",
        "scope": "ALL_25340_SEALED_LDA_SOURCE_IDENTITIES",
        "binding_objective": "COMPLETE_EMPLOYMENT_CHRONOLOGY_WITH_EMPLOYER_OR_OFFICE_TITLE_AND_BOUNDED_DATES",
        "secondary_nonblocking": "EDUCATION",
        "input_rows": len(queue_rows),
        "unique_lda_source_person_ids": len(universe),
        "output_rows": output_count,
        "coverage_conservation": output_count == len(queue_rows) == len(universe) == 25340,
        "priority_counts": dict(sorted(priority_counts.items())),
        "next_route_counts": dict(sorted(route_counts.items())),
        "evidence_outcome_counts": dict(sorted(evidence_outcome_counts.items())),
        "candidate_source_combination_counts": dict(sorted(candidate_source_combination_counts.items())),
        "gap_counts": dict(sorted(gap_counts.items())),
        "new_candidate_coverage": {
            "repaired_public_unique_ids": len(public_by_id),
            "repaired_public_external_employment_unique_ids": len(
                {
                    person_id
                    for person_id, value in public_by_id.items()
                    if any(
                        fact.get("fact_type") == "EMPLOYMENT"
                        and fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
                        for fact in (value.get("candidate_facts") or [])
                    )
                }
            ),
            "legacy_public_unique_ids": len(legacy_public_by_id),
            "legacy_public_external_employment_unique_ids": len(
                {
                    person_id
                    for person_id, value in legacy_public_by_id.items()
                    if any(
                        fact.get("fact_type") == "EMPLOYMENT"
                        and fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
                        for fact in (value.get("candidate_facts") or [])
                    )
                }
            ),
            "littlesis_any_history_unique_ids": len(littlesis_by_id),
            "littlesis_position_unique_ids": len(
                {
                    row["lda_source_person_id"]
                    for values in littlesis_by_id.values()
                    for row in values
                    if row.get("fact_type") == "EMPLOYMENT"
                }
            ),
            "politico_role_unique_ids": len(politico_by_id),
            "unique_ids_with_any_new_public_employment_candidate": len(
                {
                    person_id
                    for person_id, value in public_by_id.items()
                    if any(
                        fact.get("fact_type") == "EMPLOYMENT"
                        and fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
                        for fact in (value.get("candidate_facts") or [])
                    )
                }
                | {
                    person_id
                    for person_id, value in legacy_public_by_id.items()
                    if any(
                        fact.get("fact_type") == "EMPLOYMENT"
                        and fact.get("evidence_type") != "LDA_QUEUE_CONTEXT"
                        for fact in (value.get("candidate_facts") or [])
                    )
                }
                | {
                    person_id
                    for person_id, values in littlesis_by_id.items()
                    if any(row.get("fact_type") == "EMPLOYMENT" for row in values)
                }
                | set(politico_by_id)
            ),
        },
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "inputs": [
            {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in inputs
        ],
        "output": {
            "path": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["acquisition_priority", "sealed_queue_ordinal", "lda_source_person_id"],
            "twin_verification": "PENDING_EXTERNAL_BYTE_COMPARISON",
        },
        "risk_notes": [
            "Every LittleSis and Politico join remains a REVIEW_REQUIRED normalized-name candidate.",
            "Repaired public facts remain UNVERIFIED_CANDIDATE facts and are not canonical.",
            "A bounded candidate interval does not establish a complete lifetime chronology.",
            "Registrant filing association is not treated as continuous employment.",
            "Education is retained as a nonblocking diagnostic only.",
        ],
    }
    receipt_path = args.output_root / "public_employment_acquisition_queue_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
