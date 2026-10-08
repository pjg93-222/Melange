#!/usr/bin/env python3
"""Inventory non-temporal employment evidence across staffer-network ledgers.

This audit deliberately ignores education and every employment date/duration field.
It does not equate field completeness with an exhaustive lifetime history.  Instead,
it reports four separate concepts:

* source-profile role/employer completeness: a structured source profile has at
  least one employment assertion and every profile assertion has an employer and
  role, without requiring education, dates, chronology, or lifetime attestation;
* field completeness on collected assertions: every collected employment assertion
  has both an employer/office and a role/title, without promoting candidate facts;
* canonical field completeness: every promoted episode has a normalized container
  and a title; and
* strict LDA representation completeness: every substantive LDA covered-position
  claim is bound into the support set of a promoted canonical episode.
"""

from __future__ import annotations

from collections import defaultdict
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


SCHEMA_ID = "staffer-network-profile-evidence-inventory-v3"
RECEIPT_SCHEMA_ID = "staffer-network-profile-evidence-inventory-receipt-v3"


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def text_present(value: Any) -> bool:
    return bool(str(value or "").strip())


def working_assertions(profile: Mapping[str, Any]) -> Iterator[tuple[bool, bool]]:
    for episode in profile.get("employment_episodes") or []:
        yield (
            text_present(episode.get("employer", episode.get("raw_employer"))),
            text_present(episode.get("title", episode.get("raw_title"))),
        )


def rapid_assertions(profile: Mapping[str, Any]) -> Iterator[tuple[bool, bool]]:
    episodes = profile.get("employment_episodes") or profile.get("employment") or []
    for episode in episodes:
        yield (
            text_present(episode.get("employer", episode.get("employer_raw"))),
            text_present(episode.get("title", episode.get("title_raw"))),
        )


def authenticated_assertions(profile: Mapping[str, Any]) -> Iterator[tuple[bool, bool]]:
    for fact in profile.get("candidate_facts") or []:
        if fact.get("fact_type") == "EMPLOYMENT":
            yield (text_present(fact.get("employer_raw")), text_present(fact.get("title_raw")))


def content_status(assertions: Iterable[tuple[bool, bool]]) -> tuple[str, int, int, int]:
    values = list(assertions)
    missing_employer = sum(not employer for employer, _ in values)
    missing_title = sum(not title for _, title in values)
    if not values:
        status = "NO_SUBSTANTIVE_EMPLOYMENT_EVIDENCE"
    elif missing_employer or missing_title:
        status = "FIELD_INCOMPLETE_ON_COLLECTED_ASSERTIONS"
    else:
        status = "FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS"
    return status, len(values), missing_employer, missing_title


def source_profile_status(
    assertions: Iterable[tuple[bool, bool]],
) -> tuple[str, int, int, int]:
    """Classify only structured profile assertions, independent of other lanes."""
    values = list(assertions)
    missing_employer = sum(not employer for employer, _ in values)
    missing_title = sum(not title for _, title in values)
    if not values:
        status = "NO_STRUCTURED_SOURCE_PROFILE_EMPLOYMENT"
    elif missing_employer or missing_title:
        status = "SOURCE_PROFILE_ROLE_EMPLOYER_INCOMPLETE"
    else:
        status = "SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE"
    return status, len(values), missing_employer, missing_title


def lda_representation_status(
    claim_ids: Iterable[str], support_ids: set[str], explicit_no_count: int
) -> tuple[str, int]:
    claims = list(claim_ids)
    represented = sum(claim_id in support_ids for claim_id in claims)
    if claims and represented == len(claims):
        return "ALL_SUBSTANTIVE_LDA_CLAIMS_REPRESENTED", represented
    if claims:
        return "SUBSTANTIVE_LDA_CLAIMS_NOT_FULLY_REPRESENTED", represented
    if explicit_no_count:
        return "EXPLICIT_NO_POSITION_DISPOSITION", 0
    return "NO_SUBSTANTIVE_EMPLOYMENT_EVIDENCE", 0


def employment_evidence_state(
    *, has_canonical: bool, noncanonical_candidate_count: int,
    covered_has_employer: bool, covered_has_role: bool,
) -> str:
    if has_canonical:
        return "CANONICAL_DATED_EMPLOYMENT_PRESENT"
    if noncanonical_candidate_count or covered_has_employer:
        return "REVIEW_REQUIRED_EMPLOYMENT_CANDIDATE_ONLY"
    if covered_has_role:
        return "DIRECT_ROLE_OR_POSITION_TEXT_ONLY"
    return "NONE"


def audit(
    *,
    people_path: Path,
    covered_positions_path: Path,
    canonical_episodes_path: Path,
    affiliation_memberships_path: Path,
    registrant_associations_path: Path,
    working_profiles_path: Path,
    rapid_profiles_path: Path,
    authenticated_profiles_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise ValueError(f"output directory is not empty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    input_paths = {
        "people": people_path,
        "covered_positions": covered_positions_path,
        "canonical_episodes": canonical_episodes_path,
        "affiliation_memberships": affiliation_memberships_path,
        "registrant_associations": registrant_associations_path,
        "working_profiles": working_profiles_path,
        "rapid_profiles": rapid_profiles_path,
        "authenticated_profiles": authenticated_profiles_path,
    }
    for label, path in input_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"missing {label}: {path}")

    people = list(rows(people_path))
    if len(people) != 25_340:
        raise ValueError(f"expected sealed 25,340-person scope, got {len(people)}")
    person_ids = [str(row["lda_source_person_id"]) for row in people]
    if len(set(person_ids)) != len(person_ids):
        raise ValueError("people ledger contains duplicate LDA source person IDs")
    scope = set(person_ids)

    assertions: defaultdict[str, list[tuple[bool, bool, str]]] = defaultdict(list)
    covered_claims: defaultdict[str, list[str]] = defaultdict(list)
    explicit_no_counts: defaultdict[str, int] = defaultdict(int)
    canonical_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    working_counts: defaultdict[str, int] = defaultdict(int)
    rapid_counts: defaultdict[str, int] = defaultdict(int)
    authenticated_counts: defaultdict[str, int] = defaultdict(int)
    registrant_counts: defaultdict[str, int] = defaultdict(int)

    for row in rows(covered_positions_path):
        person_id = str(row["lda_source_person_id"])
        if person_id not in scope:
            raise ValueError(f"covered-position person outside sealed scope: {person_id}")
        if row.get("explicit_no_position"):
            explicit_no_counts[person_id] += 1
            continue
        if not text_present(row.get("claim_text")):
            continue
        claim_id = str(row["claim_id"])
        covered_claims[person_id].append(claim_id)
        assertions[person_id].append(
            (
                bool(row.get("office_employer_mentions")),
                bool(row.get("role_title_mentions")),
                "lda_covered_position",
            )
        )

    canonical_support_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows(canonical_episodes_path):
        person_id = str(row["resolved_person_id"])
        if person_id not in scope:
            raise ValueError(f"canonical person outside sealed scope: {person_id}")
        canonical_rows[person_id].append(row)
        assertions[person_id].append(
            (
                text_present(row.get("normalized_container_id")),
                text_present(row.get("title")),
                "canonical_episode",
            )
        )
        canonical_support_ids[person_id].update(
            str(value) for value in row.get("support_observation_ids") or []
        )

    for row in rows(working_profiles_path):
        person_id = str(row["lda_source_person_id"])
        if person_id not in scope:
            raise ValueError(f"working-profile person outside sealed scope: {person_id}")
        for employer, title in working_assertions(row):
            assertions[person_id].append((employer, title, "working_profile"))
            working_counts[person_id] += 1

    for row in rows(rapid_profiles_path):
        person_id = str(row["lda_source_person_id"])
        if person_id not in scope:
            raise ValueError(f"rapid-profile person outside sealed scope: {person_id}")
        for employer, title in rapid_assertions(row):
            assertions[person_id].append((employer, title, "rapid_structured_profile"))
            rapid_counts[person_id] += 1

    for row in rows(authenticated_profiles_path):
        person_id = str(row["lda_source_person_id"])
        if person_id not in scope:
            raise ValueError(f"authenticated-profile person outside sealed scope: {person_id}")
        for employer, title in authenticated_assertions(row):
            assertions[person_id].append((employer, title, "authenticated_profile"))
            authenticated_counts[person_id] += 1

    registrant_episode_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows(registrant_associations_path):
        person_id = str(row["lda_source_person_id"])
        if person_id not in scope:
            raise ValueError(f"registrant person outside sealed scope: {person_id}")
        registrant_counts[person_id] += 1
        registrant_episode_ids[person_id].add(str(row["episode_id"]))

    membership_support_ids: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows(affiliation_memberships_path):
        person_id = str(row["person_id"])
        if person_id not in scope:
            raise ValueError(f"affiliation-member person outside sealed scope: {person_id}")
        membership_support_ids[person_id].update(
            str(value) for value in row.get("support_ids") or []
        )
    represented_registrants = {
        (person_id, episode_id)
        for person_id, episode_ids in registrant_episode_ids.items()
        for episode_id in episode_ids
        if episode_id in membership_support_ids[person_id]
    }

    audit_rows: list[dict[str, Any]] = []
    for person in people:
        person_id = str(person["lda_source_person_id"])
        person_assertions = assertions.get(person_id, [])
        status, assertion_count, missing_employer, missing_title = content_status(
            (employer, title) for employer, title, _ in person_assertions
        )
        profile_status, profile_assertion_count, profile_missing_employer, profile_missing_title = (
            source_profile_status(
                (employer, title)
                for employer, title, source in person_assertions
                if source in {
                    "working_profile",
                    "rapid_structured_profile",
                    "authenticated_profile",
                }
            )
        )
        canon = canonical_rows.get(person_id, [])
        canonical_status, _, _, _ = content_status(
            (
                text_present(row.get("normalized_container_id")),
                text_present(row.get("title")),
            )
            for row in canon
        )
        claim_ids = covered_claims.get(person_id, [])
        lda_status, represented_claim_count = lda_representation_status(
            claim_ids,
            canonical_support_ids[person_id],
            explicit_no_counts.get(person_id, 0),
        )
        source_counts = defaultdict(int)
        for _, _, source in person_assertions:
            source_counts[source] += 1
        noncanonical_candidate_count = (
            working_counts.get(person_id, 0)
            + rapid_counts.get(person_id, 0)
            + authenticated_counts.get(person_id, 0)
        )
        covered_has_employer = any(
            employer and source == "lda_covered_position"
            for employer, _, source in person_assertions
        )
        covered_has_role = any(
            title and source == "lda_covered_position"
            for _, title, source in person_assertions
        )
        evidence_state = employment_evidence_state(
            has_canonical=bool(canon),
            noncanonical_candidate_count=noncanonical_candidate_count,
            covered_has_employer=covered_has_employer,
            covered_has_role=covered_has_role,
        )
        represented_person_registrants = sum(
            (person_id, episode_id) in represented_registrants
            for episode_id in registrant_episode_ids.get(person_id, set())
        )
        if represented_person_registrants:
            affiliation_evidence_state = "CANONICAL_AFFILIATION_PRESENT"
        elif registrant_counts.get(person_id, 0):
            affiliation_evidence_state = "REVIEW_REQUIRED_AFFILIATION_CANDIDATE_ONLY"
        else:
            affiliation_evidence_state = "NONE"
        acquisition_state = (
            "PARTIAL" if assertion_count or explicit_no_counts.get(person_id, 0)
            else "UNQUERIED_OR_UNKNOWN"
        )
        audit_rows.append(
            {
                "schema_id": SCHEMA_ID,
                "sealed_queue_ordinal": int(person.get("queue_rank") or 0),
                "lda_source_person_id": person_id,
                "display_name": person.get("display_name"),
                "education_and_dates_ignored": True,
                "source_profile_status": profile_status,
                "source_profile_employment_assertion_count": profile_assertion_count,
                "source_profile_missing_employer_count": profile_missing_employer,
                "source_profile_missing_title_count": profile_missing_title,
                "field_coverage_status": status,
                "collected_assertion_count": assertion_count,
                "collected_missing_employer_count": missing_employer,
                "collected_missing_title_count": missing_title,
                "source_assertion_counts": dict(sorted(source_counts.items())),
                "canonical_content_status": canonical_status,
                "canonical_episode_count": len(canon),
                "employment_evidence_state": evidence_state,
                "affiliation_evidence_state": affiliation_evidence_state,
                "acquisition_state": acquisition_state,
                "lifetime_history_state": "NOT_ATTESTED",
                "substantive_lda_claim_count": len(claim_ids),
                "canonical_supported_lda_claim_count": represented_claim_count,
                "lda_representation_status": lda_status,
                "explicit_no_position_claim_count": explicit_no_counts.get(person_id, 0),
                "working_profile_episode_count": working_counts.get(person_id, 0),
                "rapid_profile_episode_count": rapid_counts.get(person_id, 0),
                "authenticated_profile_episode_count": authenticated_counts.get(person_id, 0),
                "registrant_association_count": registrant_counts.get(person_id, 0),
                "represented_registrant_association_count": represented_person_registrants,
            }
        )

    audit_rows.sort(key=lambda row: (row["sealed_queue_ordinal"], row["lda_source_person_id"]))
    output_path = output_root / "profile_evidence_inventory_25340.ndjson.gz"
    with output_path.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            for row in audit_rows:
                compressed.write(canonical_json_bytes(row))

    collected_complete = sum(
        row["field_coverage_status"] == "FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS"
        for row in audit_rows
    )
    source_profile_complete = sum(
        row["source_profile_status"] == "SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE"
        for row in audit_rows
    )
    canonical_complete = sum(
        row["canonical_content_status"] == "FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS"
        for row in audit_rows
    )
    strict_complete = sum(
        row["lda_representation_status"] == "ALL_SUBSTANTIVE_LDA_CLAIMS_REPRESENTED"
        for row in audit_rows
    )
    explicit_dispositions = sum(
        row["lda_representation_status"] == "EXPLICIT_NO_POSITION_DISPOSITION"
        for row in audit_rows
    )
    substantive_claims = sum(row["substantive_lda_claim_count"] for row in audit_rows)
    supported_claims = sum(row["canonical_supported_lda_claim_count"] for row in audit_rows)
    receipt = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS",
        "pass_meaning": (
            "Scope, row conservation, exact person-bound support joins, input/output hashes, "
            "and deterministic serialization passed. PASS does not assert evidence completeness."
        ),
        "scope_people": len(audit_rows),
        "definitions": {
            "source_profile_role_employer_complete": (
                "At least one employment assertion exists in a structured working-history, "
                "rapid structured-profile, or authenticated-profile record, and every such "
                "profile assertion has an employer and role/title. Education, dates, duration, "
                "chronology, canonical promotion, and lifetime-exhaustiveness attestation are "
                "ignored. Multiple source ledgers are deduplicated at the exact LDA person-ID "
                "level for the people count."
            ),
            "field_complete_on_collected_assertions": (
                "At least one collected employment assertion and every collected assertion has "
                "an employer/office and role/title; education, dates, duration, chronology, and "
                "lifetime-exhaustiveness attestation are ignored. Candidate rows are inventoried "
                "but are not promoted by this audit."
            ),
            "canonical_content_complete": (
                "At least one canonical episode and every canonical episode has a normalized "
                "container and title; education and all temporal fields are ignored."
            ),
            "strict_lda_representation_complete": (
                "At least one substantive LDA covered-position claim and every such claim ID is "
                "present in canonical episode support for the same exact LDA person ID."
            ),
        },
        "implementation": {
            "path": str(Path(__file__).resolve()),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "counts": {
            "people_with_structured_source_profile_employment": sum(
                row["source_profile_employment_assertion_count"] > 0 for row in audit_rows
            ),
            "source_profile_role_employer_complete_people": source_profile_complete,
            "source_profile_role_employer_incomplete_people": sum(
                row["source_profile_status"] == "SOURCE_PROFILE_ROLE_EMPLOYER_INCOMPLETE"
                for row in audit_rows
            ),
            "collected_people_with_substantive_employment_evidence": sum(
                row["collected_assertion_count"] > 0 for row in audit_rows
            ),
            "field_complete_on_collected_assertions_people": collected_complete,
            "field_incomplete_on_collected_assertions_people": sum(
                row["field_coverage_status"] == "FIELD_INCOMPLETE_ON_COLLECTED_ASSERTIONS"
                for row in audit_rows
            ),
            "canonical_content_complete_people": canonical_complete,
            "strict_lda_representation_complete_people": strict_complete,
            "explicit_no_position_disposition_people": explicit_dispositions,
            "lda_source_disposition_closed_including_explicit_no_position": (
                strict_complete + explicit_dispositions
            ),
            "substantive_lda_claims": substantive_claims,
            "canonical_supported_lda_claims": supported_claims,
            "unrepresented_substantive_lda_claims": substantive_claims - supported_claims,
            "lifetime_history_attested_complete_people": 0,
            "registrant_association_rows": sum(map(len, registrant_episode_ids.values())),
            "represented_registrant_association_rows": len(represented_registrants),
        },
        "inputs": {
            label: {
                "path": str(path.resolve()),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for label, path in sorted(input_paths.items())
        },
        "output": {
            "path": output_path.name,
            "rows": len(audit_rows),
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["sealed_queue_ordinal", "lda_source_person_id"],
        },
    }
    receipt_path = output_root / "profile_evidence_inventory_receipt.json"
    receipt_path.write_bytes(canonical_json_bytes(receipt))
    return receipt


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--people", type=Path, required=True)
    result.add_argument("--covered-positions", type=Path, required=True)
    result.add_argument("--canonical-episodes", type=Path, required=True)
    result.add_argument("--affiliation-memberships", type=Path, required=True)
    result.add_argument("--registrant-associations", type=Path, required=True)
    result.add_argument("--working-profiles", type=Path, required=True)
    result.add_argument("--rapid-profiles", type=Path, required=True)
    result.add_argument("--authenticated-profiles", type=Path, required=True)
    result.add_argument("--output-root", type=Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    receipt = audit(
        people_path=args.people,
        covered_positions_path=args.covered_positions,
        canonical_episodes_path=args.canonical_episodes,
        affiliation_memberships_path=args.affiliation_memberships,
        registrant_associations_path=args.registrant_associations,
        working_profiles_path=args.working_profiles,
        rapid_profiles_path=args.rapid_profiles,
        authenticated_profiles_path=args.authenticated_profiles,
        output_root=args.output_root,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
