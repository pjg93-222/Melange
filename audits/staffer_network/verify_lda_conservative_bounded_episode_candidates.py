from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterator, Mapping


SCHEMA_ID = "staffer-network-lda-conservative-bounded-episode-independent-verification-v1"
CANDIDATE_SCHEMA = "staffer-network-lda-conservative-bounded-episode-candidate-v1"
BLOCKER_SCHEMA = "staffer-network-lda-conservative-bounded-episode-blocker-v1"
MANIFEST_SCHEMA = "staffer-network-lda-conservative-bounded-episode-manifest-v1"
DISQUALIFYING_NORMALIZATION_FLAGS = {
    "AMBIGUOUS_ROLE_ABBREVIATION",
    "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
    "PUNCTUATION_ONLY_CLAIM_TEXT",
    "REFERENCE_TO_PRIOR_FILING_NOT_EMPLOYMENT_FACT",
    "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
}
TWO_DIGIT_YEAR = re.compile(r"(?:^|\D)(?:'\d{2}|\d{1,2}/\d{2})(?:\D|$)")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
TOKEN_PATTERN = re.compile(
    rb"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[\"'][^\"']+[\"']"
)
PROMOTION_KEYS = {
    "canonical_date_range_promotions",
    "canonical_employment_promoted",
    "canonical_employment_promotions",
    "canonical_identity_promoted",
    "canonical_identity_promotions",
    "canonical_office_employer_promotions",
    "canonical_role_title_promotions",
    "complete_employment_history_asserted",
    "complete_history_assertions",
    "complete_lifetime_employment_asserted",
    "complete_lifetime_employment_assertions",
}


class VerificationFailure(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationFailure(f"object required: {path}")
    return value


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationFailure(f"object required at {path}:{line_number}")
            yield value


def resolve(manifest_path: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise VerificationFailure(f"path required: {label}")
    path = Path(raw)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve(strict=True)


def round_trip(text: str, mention: Mapping[str, Any]) -> bool:
    start = mention.get("span_start")
    end = mention.get("span_end")
    literal = mention.get("text")
    return (
        isinstance(start, int)
        and not isinstance(start, bool)
        and isinstance(end, int)
        and not isinstance(end, bool)
        and 0 <= start < end <= len(text)
        and text[start:end] == literal
    )


def independent_rejection_reasons(row: Mapping[str, Any]) -> list[str]:
    roles = row.get("role_title_mentions") or []
    offices = row.get("office_employer_mentions") or []
    dates = row.get("date_range_mentions") or []
    reasons: set[str] = set()
    if len(roles) != 1:
        reasons.add("ROLE_TITLE_MENTION_COUNT_NOT_ONE")
    if len(offices) != 1:
        reasons.add("OFFICE_EMPLOYER_MENTION_COUNT_NOT_ONE")
    if len(dates) != 1:
        reasons.add("DATE_RANGE_MENTION_COUNT_NOT_ONE")
    if reasons:
        return sorted(reasons)

    role, office, date = roles[0], offices[0], dates[0]
    text = str(row.get("claim_text", ""))
    for label, mention in (("ROLE", role), ("OFFICE", office), ("DATE", date)):
        if not round_trip(text, mention):
            reasons.add(f"{label}_SPAN_ROUND_TRIP_FAILED")
    spans = sorted(
        (mention.get("span_start"), mention.get("span_end"))
        for mention in (role, office, date)
        if isinstance(mention.get("span_start"), int)
        and not isinstance(mention.get("span_start"), bool)
        and isinstance(mention.get("span_end"), int)
        and not isinstance(mention.get("span_end"), bool)
    )
    if any(left[1] > right[0] for left, right in zip(spans, spans[1:])):
        reasons.add("MENTION_SPANS_OVERLAP")
    if role.get("ambiguous_abbreviation") is True:
        reasons.add("AMBIGUOUS_ROLE_ABBREVIATION")
    if role.get("generic_title_risk") is True:
        reasons.add("GENERIC_ROLE_TITLE_RISK")
    if date.get("review_flags"):
        reasons.add("DATE_MENTION_REVIEW_FLAG_PRESENT")
    flags = set(row.get("normalization_review_flags") or [])
    reasons.update(flags & DISQUALIFYING_NORMALIZATION_FLAGS)
    start_year = date.get("explicit_start_year")
    end_year = date.get("explicit_end_year")
    if date.get("open_ended_text") is True or not (
        isinstance(start_year, int)
        and not isinstance(start_year, bool)
        and isinstance(end_year, int)
        and not isinstance(end_year, bool)
    ):
        reasons.add("DATE_RANGE_NOT_CLOSED_WITH_EXPLICIT_YEARS")
    else:
        if not (1000 <= start_year <= 9999 and 1000 <= end_year <= 9999):
            reasons.add("DATE_YEAR_NOT_FOUR_DIGIT")
        if start_year > end_year:
            reasons.add("DATE_RANGE_REVERSED")
    if date.get("pattern_id") == "DATE_APOSTROPHE_YEAR_RANGE" or TWO_DIGIT_YEAR.search(
        str(date.get("text", ""))
    ):
        reasons.add("TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED")
    return sorted(reasons)


def expected_candidate_id(source: Mapping[str, Any]) -> str:
    role = source["role_title_mentions"][0]
    office = source["office_employer_mentions"][0]
    date = source["date_range_mentions"][0]
    return "lda-bounded-episode-candidate:" + hashlib.sha256(
        compact(
            [
                source.get("claim_id"),
                role.get("span_start"),
                role.get("span_end"),
                office.get("span_start"),
                office.get("span_end"),
                date.get("span_start"),
                date.get("span_end"),
            ]
        )
    ).hexdigest()


def promotion_failures(value: Any, context: str, failures: Counter[str]) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered in PROMOTION_KEYS and nested not in (False, 0, None, ""):
                failures[f"promotion:{context}:{key}"] += 1
            if lowered.endswith(
                (
                    "canonical_person_id",
                    "canonical_employment_episode_id",
                    "canonical_employment_fact_id",
                    "canonical_fact_id",
                )
            ) and nested not in (False, 0, None, ""):
                failures[f"canonical_id:{context}:{key}"] += 1
            promotion_failures(nested, context, failures)
    elif isinstance(value, list):
        for nested in value:
            promotion_failures(nested, context, failures)


def logical_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rb") as stream:
            return stream.read()
    return path.read_bytes()


def verify(manifest_path: Path, primary_dir: Path, twin_dir: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(manifest_path)
    if manifest.get("schema_id") != MANIFEST_SCHEMA:
        raise VerificationFailure("unexpected manifest schema")
    normalization = manifest.get("normalization") or {}
    materialization = manifest.get("materialization") or {}
    a5b = manifest.get("a5b_final_gaps") or {}
    paths = {
        "normalization_primary": resolve(
            manifest_path, normalization.get("primary_ledger"), "normalization.primary_ledger"
        ),
        "normalization_primary_receipt": resolve(
            manifest_path, normalization.get("primary_receipt"), "normalization.primary_receipt"
        ),
        "normalization_twin": resolve(
            manifest_path, normalization.get("twin_ledger"), "normalization.twin_ledger"
        ),
        "normalization_twin_receipt": resolve(
            manifest_path, normalization.get("twin_receipt"), "normalization.twin_receipt"
        ),
        "people": resolve(manifest_path, materialization.get("people"), "materialization.people"),
        "materialization_receipt": resolve(
            manifest_path, materialization.get("receipt"), "materialization.receipt"
        ),
        "a5b_ledger": resolve(manifest_path, a5b.get("ledger"), "a5b_final_gaps.ledger"),
        "a5b_receipt": resolve(manifest_path, a5b.get("receipt"), "a5b_final_gaps.receipt"),
        "a5b_verification": resolve(
            manifest_path, a5b.get("verification"), "a5b_final_gaps.verification"
        ),
    }
    sealed = {
        "normalization_primary": normalization.get("primary_ledger_sha256"),
        "normalization_primary_receipt": normalization.get("primary_receipt_sha256"),
        "normalization_twin": normalization.get("twin_ledger_sha256"),
        "normalization_twin_receipt": normalization.get("twin_receipt_sha256"),
        "people": materialization.get("people_sha256"),
        "materialization_receipt": materialization.get("receipt_sha256"),
        "a5b_ledger": a5b.get("ledger_sha256"),
        "a5b_receipt": a5b.get("receipt_sha256"),
        "a5b_verification": a5b.get("verification_sha256"),
    }

    assertions: dict[str, bool] = {}
    input_hashes: dict[str, dict[str, Any]] = {}
    for role, path in sorted(paths.items()):
        actual = sha(path)
        expected = str(sealed.get(role) or "").lower()
        input_hashes[role] = {"bytes": path.stat().st_size, "sha256": actual}
        assertions[f"sealed_input_hash:{role}"] = bool(HEX64.fullmatch(expected)) and actual == expected
    assertions["normalization_payload_twins_byte_equal"] = (
        paths["normalization_primary"].read_bytes() == paths["normalization_twin"].read_bytes()
    )
    assertions["normalization_receipt_twins_byte_equal"] = (
        paths["normalization_primary_receipt"].read_bytes()
        == paths["normalization_twin_receipt"].read_bytes()
    )
    normalization_receipt = read_json(paths["normalization_primary_receipt"])
    materialization_receipt = read_json(paths["materialization_receipt"])
    a5b_receipt = read_json(paths["a5b_receipt"])
    a5b_verification = read_json(paths["a5b_verification"])
    assertions["sealed_upstream_receipts_pass"] = all(
        receipt.get("status") == "PASS"
        for receipt in (normalization_receipt, materialization_receipt, a5b_receipt, a5b_verification)
    )
    assertions["normalization_receipt_binds_payload"] = (
        str((normalization_receipt.get("output") or {}).get("sha256", "")).lower()
        == sha(paths["normalization_primary"])
    )
    assertions["a5b_receipt_binds_ledger"] = (
        str((a5b_receipt.get("output") or {}).get("sha256", "")).lower()
        == sha(paths["a5b_ledger"])
    )

    expected_scope = manifest.get("expected_scope_size")
    people: dict[str, dict[str, Any]] = {}
    source_failures: Counter[str] = Counter()
    for person in rows(paths["people"]):
        lda_id = str(person.get("lda_source_person_id", ""))
        if not lda_id:
            source_failures["blank_person_id"] += 1
        if lda_id in people:
            source_failures["duplicate_person_id"] += 1
        people[lda_id] = person
        promotion_failures(person, "person", source_failures)
    assertions["person_scope_exact"] = (
        isinstance(expected_scope, int)
        and not isinstance(expected_scope, bool)
        and len(people) == expected_scope
    )

    gap_code = str(a5b.get("gap_code", ""))
    expected_gap_people = a5b.get("expected_bounded_interval_gap_people")
    a5b_ids: set[str] = set()
    a5b_gap_ids: set[str] = set()
    for row in rows(paths["a5b_ledger"]):
        lda_id = str(row.get("lda_source_person_id", ""))
        if not lda_id:
            source_failures["blank_a5b_id"] += 1
        if lda_id in a5b_ids:
            source_failures["duplicate_a5b_id"] += 1
        a5b_ids.add(lda_id)
        if gap_code in set(row.get("critical_path_gap_codes") or []):
            a5b_gap_ids.add(lda_id)
        promotion_failures(row, "a5b", source_failures)
    assertions["a5b_scope_matches_people"] = a5b_ids == set(people)
    assertions["a5b_bounded_gap_count_exact"] = (
        isinstance(expected_gap_people, int)
        and not isinstance(expected_gap_people, bool)
        and len(a5b_gap_ids) == expected_gap_people
        and (a5b_receipt.get("gap_counts") or {}).get(gap_code) == expected_gap_people
        and (a5b_verification.get("gap_counts") or {}).get(gap_code) == expected_gap_people
    )

    source_by_claim: dict[str, dict[str, Any]] = {}
    eligible_claims: set[str] = set()
    blocked_claims: dict[str, list[str]] = {}
    exact_cardinality_count = 0
    input_claim_rows = 0
    for source in rows(paths["normalization_primary"]):
        input_claim_rows += 1
        claim_id = str(source.get("claim_id", ""))
        if not claim_id:
            source_failures["blank_claim_id"] += 1
        if claim_id in source_by_claim:
            source_failures["duplicate_claim_id"] += 1
        source_by_claim[claim_id] = source
        if str(source.get("lda_source_person_id", "")) not in people:
            source_failures["claim_person_link_missing"] += 1
        promotion_failures(source, "normalization", source_failures)
        exact = (
            len(source.get("role_title_mentions") or []) == 1
            and len(source.get("office_employer_mentions") or []) == 1
            and len(source.get("date_range_mentions") or []) == 1
        )
        if exact:
            exact_cardinality_count += 1
            reasons = independent_rejection_reasons(source)
            if reasons:
                blocked_claims[claim_id] = reasons
            else:
                eligible_claims.add(claim_id)
    assertions["source_claim_person_linkage_complete"] = not source_failures
    assertions["normalization_claim_count_exact"] = (
        input_claim_rows == normalization_receipt.get("output_claim_rows") == len(source_by_claim)
    )

    output_files: dict[str, Path] = {}
    for prefix, directory in (("primary", primary_dir), ("twin", twin_dir)):
        output_files[f"{prefix}_candidates"] = (
            directory / "lda_conservative_bounded_episode_candidates.ndjson.gz"
        ).resolve(strict=True)
        output_files[f"{prefix}_blockers"] = (
            directory / "lda_conservative_bounded_episode_blockers.ndjson.gz"
        ).resolve(strict=True)
        output_files[f"{prefix}_receipt"] = (
            directory / "lda_conservative_bounded_episode_receipt.json"
        ).resolve(strict=True)
    for artifact in ("candidates", "blockers", "receipt"):
        primary = output_files[f"primary_{artifact}"]
        twin = output_files[f"twin_{artifact}"]
        assertions[f"{artifact}_twins_byte_equal"] = primary.read_bytes() == twin.read_bytes()
        assertions[f"{artifact}_twins_sha256_equal"] = sha(primary) == sha(twin)

    primary_receipt = read_json(output_files["primary_receipt"])
    twin_receipt = read_json(output_files["twin_receipt"])
    output_failures: Counter[str] = Counter()
    promotion_failures(primary_receipt, "a6_receipt", output_failures)
    assertions["receipt_binds_candidate_payload"] = (
        str((primary_receipt.get("candidates") or {}).get("sha256", "")).lower()
        == sha(output_files["primary_candidates"])
    )
    assertions["receipt_binds_blocker_payload"] = (
        str((primary_receipt.get("near_candidate_blockers") or {}).get("sha256", "")).lower()
        == sha(output_files["primary_blockers"])
    )
    assertions["receipt_zero_promotions"] = all(
        primary_receipt.get(key) == 0
        for key in (
            "canonical_employment_promotions",
            "canonical_identity_promotions",
            "complete_lifetime_employment_assertions",
        )
    )

    candidate_claims: set[str] = set()
    candidate_ids: set[str] = set()
    candidate_people: set[str] = set()
    candidate_rows = 0
    for candidate in rows(output_files["primary_candidates"]):
        candidate_rows += 1
        promotion_failures(candidate, "candidate", output_failures)
        candidate_id = str(candidate.get("bounded_episode_candidate_id", ""))
        if not candidate_id or candidate_id in candidate_ids:
            output_failures["candidate_id_missing_or_duplicate"] += 1
        candidate_ids.add(candidate_id)
        pointer = candidate.get("source_pointer") or {}
        claim_id = str(pointer.get("claim_id", ""))
        if claim_id in candidate_claims:
            output_failures["candidate_claim_duplicate"] += 1
        candidate_claims.add(claim_id)
        source = source_by_claim.get(claim_id)
        if source is None:
            output_failures["candidate_source_claim_missing"] += 1
            continue
        lda_id = str(candidate.get("lda_source_person_id", ""))
        person = people.get(lda_id)
        if person is None:
            output_failures["candidate_person_missing"] += 1
            continue
        candidate_people.add(lda_id)
        roles = source.get("role_title_mentions") or []
        offices = source.get("office_employer_mentions") or []
        dates = source.get("date_range_mentions") or []
        if not (len(roles) == len(offices) == len(dates) == 1):
            output_failures["candidate_source_cardinality"] += 1
            continue
        source_reasons = independent_rejection_reasons(source)
        if source_reasons:
            output_failures["candidate_source_disqualified"] += 1
        source_flags = set(source.get("normalization_review_flags") or [])
        if (
            source_flags & DISQUALIFYING_NORMALIZATION_FLAGS
            or roles[0].get("ambiguous_abbreviation") is True
            or roles[0].get("generic_title_risk") is True
            or dates[0].get("review_flags")
        ):
            output_failures["candidate_ambiguity_reference_punctuation_or_boundary_flag"] += 1
        if candidate.get("schema_id") != CANDIDATE_SCHEMA:
            output_failures["candidate_schema"] += 1
        if candidate.get("candidate_status") != "REVIEW_REQUIRED":
            output_failures["candidate_status"] += 1
        if candidate.get("claim_text") != source.get("claim_text"):
            output_failures["candidate_claim_text"] += 1
        if candidate.get("raw_covered_position_literal") != source.get("raw_covered_position_literal"):
            output_failures["candidate_raw_literal"] += 1
        if candidate.get("role_title_mention") != roles[0]:
            output_failures["candidate_role_mention"] += 1
        if candidate.get("office_employer_mention") != offices[0]:
            output_failures["candidate_office_mention"] += 1
        if candidate.get("date_range_mention") != dates[0]:
            output_failures["candidate_date_mention"] += 1
        if not all(round_trip(str(source.get("claim_text", "")), item) for item in (roles[0], offices[0], dates[0])):
            output_failures["candidate_exact_source_span"] += 1
        if candidate_id != expected_candidate_id(source):
            output_failures["candidate_id_derivation"] += 1
        if not (
            lda_id == source.get("lda_source_person_id") == pointer.get("lda_source_person_id")
            and pointer.get("source_claim_row_ordinal") == source.get("source_claim_row_ordinal")
            and pointer.get("source_person_candidate_id") == person.get("candidate_id")
            and pointer.get("source_filing_years") == person.get("filing_years", [])
            and pointer.get("normalization_ledger") == str(paths["normalization_primary"])
            and pointer.get("normalization_ledger_sha256") == sha(paths["normalization_primary"])
        ):
            output_failures["candidate_source_claim_person_linkage"] += 1
        date = dates[0]
        start_year = date.get("explicit_start_year")
        end_year = date.get("explicit_end_year")
        if not (
            date.get("open_ended_text") is False
            and isinstance(start_year, int)
            and not isinstance(start_year, bool)
            and isinstance(end_year, int)
            and not isinstance(end_year, bool)
            and 1000 <= start_year <= end_year <= 9999
            and date.get("pattern_id") != "DATE_APOSTROPHE_YEAR_RANGE"
            and not TWO_DIGIT_YEAR.search(str(date.get("text", "")))
        ):
            output_failures["candidate_explicit_closed_date_range"] += 1
        if not (
            candidate.get("date_literal") == date.get("text")
            and candidate.get("start_year_candidate") == date.get("explicit_start_year")
            and candidate.get("end_year_candidate") == date.get("explicit_end_year")
            and candidate.get("year_precision_only") is True
            and candidate.get("interval_continuity_asserted") is False
            and candidate.get("identity_status") == "NOT_ADJUDICATED"
        ):
            output_failures["candidate_explicit_date_or_policy"] += 1

    blocker_claims: set[str] = set()
    blocker_rows = 0
    blocker_reason_counts: Counter[str] = Counter()
    for blocker in rows(output_files["primary_blockers"]):
        blocker_rows += 1
        promotion_failures(blocker, "blocker", output_failures)
        pointer = blocker.get("source_pointer") or {}
        claim_id = str(pointer.get("claim_id", ""))
        if claim_id in blocker_claims:
            output_failures["blocker_claim_duplicate"] += 1
        blocker_claims.add(claim_id)
        source = source_by_claim.get(claim_id)
        if source is None:
            output_failures["blocker_source_claim_missing"] += 1
            continue
        lda_id = str(blocker.get("lda_source_person_id", ""))
        person = people.get(lda_id)
        if person is None:
            output_failures["blocker_person_missing"] += 1
            continue
        expected_reasons = independent_rejection_reasons(source)
        actual_reasons = blocker.get("rejection_reasons") or []
        blocker_reason_counts.update(actual_reasons)
        if blocker.get("schema_id") != BLOCKER_SCHEMA:
            output_failures["blocker_schema"] += 1
        if not expected_reasons or actual_reasons != expected_reasons:
            output_failures["blocker_reasons"] += 1
        if not (
            blocker.get("claim_text") == source.get("claim_text")
            and blocker.get("raw_covered_position_literal") == source.get("raw_covered_position_literal")
            and blocker.get("role_title_mention") == source["role_title_mentions"][0]
            and blocker.get("office_employer_mention") == source["office_employer_mentions"][0]
            and blocker.get("date_range_mention") == source["date_range_mentions"][0]
        ):
            output_failures["blocker_source_mentions"] += 1
        if not (
            lda_id == source.get("lda_source_person_id") == pointer.get("lda_source_person_id")
            and pointer.get("source_claim_row_ordinal") == source.get("source_claim_row_ordinal")
            and pointer.get("source_person_candidate_id") == person.get("candidate_id")
            and pointer.get("source_filing_years") == person.get("filing_years", [])
            and pointer.get("normalization_ledger") == str(paths["normalization_primary"])
            and pointer.get("normalization_ledger_sha256") == sha(paths["normalization_primary"])
        ):
            output_failures["blocker_source_claim_person_linkage"] += 1

    assertions["candidate_set_exactly_matches_independent_gate"] = candidate_claims == eligible_claims
    assertions["blocker_set_exactly_matches_independent_gate"] = blocker_claims == set(blocked_claims)
    assertions["all_emitted_candidates_pass_row_checks"] = not output_failures
    assertions["emitted_candidates_exactly_one_title_office_and_date"] = (
        output_failures["candidate_source_cardinality"] == 0
    )
    assertions["emitted_candidates_have_explicit_closed_date_range"] = (
        output_failures["candidate_explicit_closed_date_range"] == 0
    )
    assertions["emitted_candidates_have_exact_source_spans"] = (
        output_failures["candidate_exact_source_span"] == 0
    )
    assertions["emitted_candidates_have_no_ambiguity_reference_punctuation_or_boundary_flags"] = (
        output_failures["candidate_ambiguity_reference_punctuation_or_boundary_flag"] == 0
    )
    assertions["emitted_candidates_have_exact_source_claim_person_linkage"] = (
        output_failures["candidate_source_claim_person_linkage"] == 0
        and output_failures["candidate_source_claim_missing"] == 0
        and output_failures["candidate_person_missing"] == 0
    )
    assertions["emitted_candidates_have_zero_promotions"] = not any(
        key.startswith(("promotion:candidate:", "canonical_id:candidate:"))
        for key in output_failures
    )
    assertions["candidate_and_blocker_partition_exact_cardinality_rows"] = (
        candidate_rows + blocker_rows == exact_cardinality_count
        and not (candidate_claims & blocker_claims)
    )
    assertions["receipt_counts_match_payloads"] = (
        primary_receipt.get("candidate_rows") == candidate_rows
        and primary_receipt.get("people_with_candidate") == len(candidate_people)
        and primary_receipt.get("near_candidate_blocker_rows") == blocker_rows
        and primary_receipt.get("filter_funnel")
        == {
            "exact_one_role_one_office_one_date_range": exact_cardinality_count,
            "input_claim_rows": input_claim_rows,
        }
        and primary_receipt.get("blocker_counts") == dict(sorted(blocker_reason_counts.items()))
    )
    a5b_gaining = candidate_people & a5b_gap_ids
    assertions["a5b_gap_impact_exact"] = primary_receipt.get("gap_impact") == {
        "a5b_bounded_interval_gap_people": len(a5b_gap_ids),
        "a5b_gap_people_gaining_review_required_bounded_candidate": len(a5b_gaining),
        "a5b_gap_people_remaining_without_a6_candidate": len(a5b_gap_ids - candidate_people),
        "canonical_bounded_interval_gap_closures": 0,
        "candidate_people_outside_a5b_bounded_gap": len(candidate_people - a5b_gap_ids),
    }
    expected_status = "BLOCKED_SAFE_LINKAGE_NOT_ESTABLISHED" if candidate_rows == 0 else "PASS"
    assertions["zero_candidate_outcome_reported_honestly"] = (
        primary_receipt.get("status") == twin_receipt.get("status") == expected_status
    )

    scanned_paths = tuple(output_files.values())
    token_matches = sum(len(TOKEN_PATTERN.findall(logical_bytes(path))) for path in scanned_paths)
    assertions["token_negative_structured_artifact_scan"] = token_matches == 0

    failures = sorted(name for name, passed in assertions.items() if not passed)
    verification = {
        "assertions": dict(sorted(assertions.items())),
        "counts": {
            "a5b_bounded_interval_gap_people": len(a5b_gap_ids),
            "a5b_gap_people_gaining_review_required_bounded_candidate": len(a5b_gaining),
            "candidate_people": len(candidate_people),
            "candidate_rows": candidate_rows,
            "exact_cardinality_source_rows": exact_cardinality_count,
            "input_claim_rows": input_claim_rows,
            "near_candidate_blocker_rows": blocker_rows,
            "source_people": len(people),
        },
        "failures": failures,
        "hashes": {
            "manifest_sha256": sha(manifest_path),
            "primary_blockers_sha256": sha(output_files["primary_blockers"]),
            "primary_candidates_sha256": sha(output_files["primary_candidates"]),
            "primary_receipt_sha256": sha(output_files["primary_receipt"]),
            "twin_blockers_sha256": sha(output_files["twin_blockers"]),
            "twin_candidates_sha256": sha(output_files["twin_candidates"]),
            "twin_receipt_sha256": sha(output_files["twin_receipt"]),
        },
        "input_hashes": input_hashes,
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "row_failure_counts": dict(sorted(output_failures.items())),
        "schema_id": SCHEMA_ID,
        "source_failure_counts": dict(sorted(source_failures.items())),
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {
            "matches": token_matches,
            "scan_mode": "DECOMPRESSED_LOGICAL_BYTES_FOR_GZIP",
            "scanned_files": len(scanned_paths),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "verification_receipt.json"
    output_path.write_bytes(compact(verification) + b"\n")
    if failures:
        raise VerificationFailure("verification failed: " + ", ".join(failures))
    return verification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--primary-dir", required=True, type=Path)
    parser.add_argument("--twin-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.manifest, args.primary_dir, args.twin_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
