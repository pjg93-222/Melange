#!/usr/bin/env python3
"""Seal source-native LDA covered-position evidence as review-only ledgers.

The Senate LDA API exposes a single free-text ``covered_position`` value on
each lobbyist/activity occurrence.  This program conserves every occurrence,
joins the previously materialized source fragments and exact-span mentions,
and emits person-level coverage for the complete source-ID universe.  It does
not infer an employer, title, employment interval, current status, identity
resolution, or complete career history.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, field
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


DEFAULT_SOURCE = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z"
)
DEFAULT_MATERIALIZED = Path(
    "audits/staffer_network/lda_employment_materialization_20260831_v2"
)
DEFAULT_NORMALIZED = Path(
    "audits/staffer_network/lda_employment_claim_normalization_20260831_v2"
)
DEFAULT_OUTPUT = Path(
    "audits/staffer_network/lda_covered_position_employment_ledger_20260831"
)

OCCURRENCES = "lda_covered_position_occurrences.ndjson.gz"
CANDIDATES = "lda_covered_position_episode_candidates.ndjson.gz"
PEOPLE = "lda_covered_position_people_coverage.ndjson.gz"
RECEIPT = "lda_covered_position_employment_ledger_receipt.json"


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: Path, role: str) -> dict[str, Any]:
    return {
        "path": path.name,
        "role": role,
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def read_ndjson_gz(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: expected object")
            yield value


class DeterministicGzipWriter:
    def __init__(self, path: Path) -> None:
        self._raw = path.open("wb")
        self._gzip = gzip.GzipFile(
            filename="", mode="wb", fileobj=self._raw, compresslevel=9, mtime=0
        )

    def write(self, value: dict[str, Any]) -> None:
        self._gzip.write(canonical_bytes(value))

    def __enter__(self) -> "DeterministicGzipWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._gzip.close()
        self._raw.close()


def evidence_key(source_person_id: str, literal: str) -> str:
    digest = hashlib.sha256(
        canonical_bytes([source_person_id, literal])
    ).hexdigest()
    return f"lda:covered-position-evidence:{digest}"


def official_filing_url(filing_uuid: str) -> str:
    return f"https://lda.senate.gov/filings/public/filing/{filing_uuid}/print/"


@dataclass
class LiteralSupport:
    assertion_count: int = 0
    filing_uuids: set[str] = field(default_factory=set)
    first_dt_posted: str | None = None
    last_dt_posted: str | None = None

    def add(self, filing_uuid: str, dt_posted: str) -> None:
        self.assertion_count += 1
        self.filing_uuids.add(filing_uuid)
        if self.first_dt_posted is None or dt_posted < self.first_dt_posted:
            self.first_dt_posted = dt_posted
        if self.last_dt_posted is None or dt_posted > self.last_dt_posted:
            self.last_dt_posted = dt_posted


@dataclass
class PersonSupport:
    assertion_count: int = 0
    filing_uuids: set[str] = field(default_factory=set)
    literals: set[str] = field(default_factory=set)
    first_dt_posted: str | None = None
    last_dt_posted: str | None = None

    def add(self, literal: str, filing_uuid: str, dt_posted: str) -> None:
        self.assertion_count += 1
        self.filing_uuids.add(filing_uuid)
        self.literals.add(literal)
        if self.first_dt_posted is None or dt_posted < self.first_dt_posted:
            self.first_dt_posted = dt_posted
        if self.last_dt_posted is None or dt_posted > self.last_dt_posted:
            self.last_dt_posted = dt_posted


def build(args: argparse.Namespace) -> dict[str, Any]:
    source_root = args.source_root.resolve()
    materialized_root = args.materialized_root.resolve()
    normalized_root = args.normalized_root.resolve()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    source_people_path = source_root / "lda_lobbyist_assertions.ndjson.gz"
    source_occurrence_path = source_root / "lda_covered_position_assertions.ndjson.gz"
    materialized_people_path = materialized_root / "lda_employment_people.ndjson.gz"
    claims_path = materialized_root / "lda_employment_claims.ndjson.gz"
    mentions_path = normalized_root / "lda_employment_claim_mentions.ndjson.gz"

    source_people = list(read_ndjson_gz(source_people_path))
    source_people_by_id = {row["source_person_id"]: row for row in source_people}
    if len(source_people_by_id) != len(source_people):
        raise ValueError("duplicate source person IDs")

    materialized_people = list(read_ndjson_gz(materialized_people_path))
    materialized_people_by_id = {row["lda_source_person_id"]: row for row in materialized_people}
    if set(materialized_people_by_id) != set(source_people_by_id):
        raise ValueError("materialized person universe differs from source-native universe")

    claims = list(read_ndjson_gz(claims_path))
    claims_by_id = {row["claim_id"]: row for row in claims}
    if len(claims_by_id) != len(claims):
        raise ValueError("duplicate claim IDs")

    mentions = list(read_ndjson_gz(mentions_path))
    mentions_by_id = {row["claim_id"]: row for row in mentions}
    if len(mentions_by_id) != len(mentions):
        raise ValueError("duplicate mention claim IDs")
    if set(mentions_by_id) != set(claims_by_id):
        raise ValueError("mention/claim ID sets differ")

    literal_support: dict[tuple[str, str], LiteralSupport] = defaultdict(LiteralSupport)
    person_support: dict[str, PersonSupport] = defaultdict(PersonSupport)
    occurrence_ids: set[str] = set()
    occurrence_count = 0
    duplicate_occurrence_ids = 0
    occurrence_out = output_root / OCCURRENCES

    with DeterministicGzipWriter(occurrence_out) as writer:
        for row in read_ndjson_gz(source_occurrence_path):
            source_person_id = row["source_person_id"]
            if source_person_id not in source_people_by_id:
                raise ValueError(f"occurrence references unknown person {source_person_id}")
            assertion_id = row["assertion_id"]
            if assertion_id in occurrence_ids:
                duplicate_occurrence_ids += 1
            occurrence_ids.add(assertion_id)
            literal = row["covered_position"]
            filing_uuid = row["filing_uuid"]
            dt_posted = row["dt_posted"]
            literal_support[(source_person_id, literal)].add(filing_uuid, dt_posted)
            person_support[source_person_id].add(literal, filing_uuid, dt_posted)
            occurrence_count += 1
            writer.write(
                {
                    "assertion_id": assertion_id,
                    "canonical_employment_fact": False,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "complete_employment_history_asserted": False,
                    "covered_position": literal,
                    "dt_posted": dt_posted,
                    "employment_field_availability": {
                        "current": "NOT_SEPARATELY_REPORTED",
                        "employer_or_office": "NOT_SEPARATELY_REPORTED",
                        "end_date": "NOT_SEPARATELY_REPORTED",
                        "start_date": "NOT_SEPARATELY_REPORTED",
                        "title": "NOT_SEPARATELY_REPORTED",
                    },
                    "filing_dt_interpretation": "SOURCE_FILING_OBSERVATION_DATE_NOT_EMPLOYMENT_DATE",
                    "filing_uuid": filing_uuid,
                    "filing_url": official_filing_url(filing_uuid),
                    "government_term_hits": row.get("government_term_hits", []),
                    "review_status": "REVIEW_REQUIRED",
                    "schema_id": "staffer-network-lda-covered-position-occurrence-v1",
                    "source_activity_id": row["source_activity_id"],
                    "source_person_id": source_person_id,
                    "source_system_id": row["source_system_id"],
                    "support_digest": row["support_digest"],
                }
            )

    join_misses: list[str] = []
    candidate_out = output_root / CANDIDATES
    candidate_counts: Counter[str] = Counter()
    person_candidate_counts: Counter[str] = Counter()
    person_role_rows: Counter[str] = Counter()
    person_entity_rows: Counter[str] = Counter()
    person_date_rows: Counter[str] = Counter()
    with DeterministicGzipWriter(candidate_out) as writer:
        for claim in claims:
            claim_id = claim["claim_id"]
            person_id = claim["lda_source_person_id"]
            literal = claim["raw_covered_position_literal"]
            support = literal_support.get((person_id, literal))
            if support is None:
                join_misses.append(claim_id)
                continue
            mention = mentions_by_id[claim_id]
            roles = mention["role_title_mentions"]
            entities = mention["office_employer_mentions"]
            dates = mention["date_range_mentions"]
            candidate_counts["rows"] += 1
            candidate_counts["role_mentions"] += len(roles)
            candidate_counts["office_employer_mentions"] += len(entities)
            candidate_counts["date_range_mentions"] += len(dates)
            candidate_counts["explicit_no_position_rows"] += int(claim["explicit_no_position"])
            candidate_counts["substantive_rows"] += int(not claim["explicit_no_position"])
            person_candidate_counts[person_id] += 1
            person_role_rows[person_id] += int(bool(roles))
            person_entity_rows[person_id] += int(bool(entities))
            person_date_rows[person_id] += int(bool(dates))
            writer.write(
                {
                    "canonical_employment_fact": False,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "claim_id": claim_id,
                    "claim_text": claim["claim_text"],
                    "complete_employment_history_asserted": False,
                    "date_range_mentions": dates,
                    "employment_episode_boundary_status": "NOT_ADJUDICATED",
                    "evidence_class": claim["evidence_class"],
                    "explicit_no_position": claim["explicit_no_position"],
                    "fragment_ordinal": claim["fragment_ordinal"],
                    "identity_status": claim["identity_status"],
                    "lda_source_person_id": person_id,
                    "office_employer_mentions": entities,
                    "raw_covered_position_literal": literal,
                    "review_required": True,
                    "role_title_mentions": roles,
                    "schema_id": "staffer-network-lda-covered-position-episode-candidate-v1",
                    "source_current_status": None,
                    "source_current_text_present": any(
                        item.get("open_ended_text", False) for item in dates
                    ),
                    "source_employment_end_date": None,
                    "source_employment_start_date": None,
                    "source_evidence_key": evidence_key(person_id, literal),
                    "source_filing_support": {
                        "assertion_count": support.assertion_count,
                        "first_dt_posted": support.first_dt_posted,
                        "last_dt_posted": support.last_dt_posted,
                        "occurrence_ledger": OCCURRENCES,
                        "unique_filing_count": len(support.filing_uuids),
                    },
                    "source_year_ranges_in_fragment": claim["year_ranges"],
                    "source_year_tokens_in_fragment": claim["year_tokens"],
                    "structured_employer_or_office": None,
                    "structured_title": None,
                }
            )

    if join_misses:
        raise ValueError(f"{len(join_misses)} claims lack exact person/literal occurrence support")

    people_out = output_root / PEOPLE
    people_counts: Counter[str] = Counter()
    with DeterministicGzipWriter(people_out) as writer:
        for source_person in source_people:
            person_id = source_person["source_person_id"]
            materialized = materialized_people_by_id[person_id]
            support = person_support.get(person_id, PersonSupport())
            response_class = materialized["covered_position_response_class"]
            if not support.assertion_count:
                gap_status = "NO_NONBLANK_COVERED_POSITION_ASSERTION"
            elif materialized["has_substantive_covered_position_claim"]:
                gap_status = "SOURCE_PROSE_PRESENT_EPISODE_BOUNDARIES_NOT_ADJUDICATED"
            else:
                gap_status = "EXPLICIT_NO_POSITION_RESPONSE_ONLY"
            people_counts[response_class] += 1
            people_counts[gap_status] += 1
            writer.write(
                {
                    "canonical_employment_promotions": 0,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "complete_employment_history_asserted": False,
                    "covered_position_assertion_count": support.assertion_count,
                    "covered_position_response_class": response_class,
                    "date_range_candidate_rows": person_date_rows[person_id],
                    "display_name": source_person["display_name"],
                    "education_status": "NOT_REPORTED_IN_LDA_COVERED_POSITION_FIELD",
                    "employment_coverage_gap_status": gap_status,
                    "episode_candidate_count": person_candidate_counts[person_id],
                    "first_covered_position_filing_dt_posted": support.first_dt_posted,
                    "lda_source_person_id": person_id,
                    "last_covered_position_filing_dt_posted": support.last_dt_posted,
                    "office_employer_candidate_rows": person_entity_rows[person_id],
                    "review_required": True,
                    "role_title_candidate_rows": person_role_rows[person_id],
                    "schema_id": "staffer-network-lda-covered-position-person-coverage-v1",
                    "source_numeric_id": source_person["source_numeric_id"],
                    "unique_covered_position_literal_count": len(support.literals),
                    "unique_covered_position_filing_count": len(support.filing_uuids),
                }
            )

    output_records = [
        file_record(occurrence_out, "source_occurrence_ledger"),
        file_record(candidate_out, "review_only_episode_candidate_ledger"),
        file_record(people_out, "complete_source_person_coverage_ledger"),
    ]
    invariant_checks = {
        "all_claims_exact_person_literal_joined": len(join_misses) == 0,
        "canonical_employment_promotions_zero": True,
        "canonical_identity_promotions_zero": True,
        "complete_history_assertions_zero": True,
        "duplicate_occurrence_assertion_ids_zero": duplicate_occurrence_ids == 0,
        "episode_candidate_count_equals_claim_count": candidate_counts["rows"] == len(claims),
        "occurrence_count_equals_source_rows": occurrence_count == len(occurrence_ids),
        "person_universe_exactly_conserved": len(source_people) == 25340,
    }
    status = "PASS" if all(invariant_checks.values()) else "FAIL"
    receipt = {
        "candidate_counts": dict(sorted(candidate_counts.items())),
        "determinism": "Canonical sorted-key JSON, stable source order, gzip mtime=0 and blank embedded filename.",
        "field_availability": {
            "covered_position": "SOURCE_NATIVE_FREE_TEXT",
            "current": "ONLY_IF_EXPLICITLY_PRESENT_IN_FREE_TEXT; NOT_STRUCTURED OR INFERRED",
            "employer_or_office": "EMBEDDED_IN_FREE_TEXT; EXACT-SPAN CANDIDATES ONLY",
            "employment_end": "ONLY_IF EXPLICITLY PRESENT IN FREE TEXT; NOT STRUCTURED OR INFERRED",
            "employment_start": "ONLY_IF EXPLICITLY PRESENT IN FREE TEXT; NOT STRUCTURED OR INFERRED",
            "filing_dt_posted": "SOURCE FILING OBSERVATION DATE; NOT AN EMPLOYMENT DATE",
            "title": "EMBEDDED IN FREE TEXT; EXACT-SPAN CANDIDATES ONLY",
        },
        "files": output_records,
        "invariant_checks": invariant_checks,
        "literal_evidence_keys": len(literal_support),
        "occurrence_assertion_rows": occurrence_count,
        "people_count_by_response_or_gap_status": dict(sorted(people_counts.items())),
        "person_rows": len(source_people),
        "policy": {
            "canonical_promotion": "PROHIBITED",
            "complete_history_claim": "PROHIBITED",
            "employment_episode_linkage": "REVIEW_REQUIRED",
            "identity_scope": "EXACT LDA SOURCE PERSON ID ONLY",
            "name_overlap_identity_resolution": "PROHIBITED",
        },
        "provenance": {
            "official_filing_url_template": "https://lda.senate.gov/filings/public/filing/{filing_uuid}/print/",
            "source_system_id": "senate-lda-api",
        },
        "risk_notes": [
            "The LDA source field is disclosure prose, not a structured complete employment history.",
            "A filing date bounds observation of the disclosure, not the start or end of employment.",
            "Role, employer/office, and date mentions are exact-span candidates and are not linked into episodes.",
            "No source silence is interpreted as no prior covered position or as a complete history.",
        ],
        "schema_id": "staffer-network-lda-covered-position-employment-ledger-receipt-v1",
        "source_inputs": [
            file_record(source_people_path, "source_native_lobbyists"),
            file_record(source_occurrence_path, "source_native_covered_position_occurrences"),
            file_record(materialized_people_path, "materialized_person_universe"),
            file_record(claims_path, "materialized_source_fragments"),
            file_record(mentions_path, "exact_span_candidate_mentions"),
        ],
        "status": status,
    }
    receipt_path = output_root / RECEIPT
    receipt_path.write_bytes(canonical_bytes(receipt))
    if status != "PASS":
        raise RuntimeError(f"ledger invariants failed: {invariant_checks}")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--materialized-root", type=Path, default=DEFAULT_MATERIALIZED)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    result = build(parse_args())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
