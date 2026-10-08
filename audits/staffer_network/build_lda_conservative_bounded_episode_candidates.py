from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


MANIFEST_SCHEMA = "staffer-network-lda-conservative-bounded-episode-manifest-v1"
CANDIDATE_SCHEMA = "staffer-network-lda-conservative-bounded-episode-candidate-v1"
BLOCKER_SCHEMA = "staffer-network-lda-conservative-bounded-episode-blocker-v1"
RECEIPT_SCHEMA = "staffer-network-lda-conservative-bounded-episode-receipt-v1"
DISQUALIFYING_NORMALIZATION_FLAGS = {
    "AMBIGUOUS_ROLE_ABBREVIATION",
    "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
    "PUNCTUATION_ONLY_CLAIM_TEXT",
    "REFERENCE_TO_PRIOR_FILING_NOT_EMPLOYMENT_FACT",
    "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
}
TWO_DIGIT_YEAR = re.compile(r"(?:^|\D)(?:'\d{2}|\d{1,2}/\d{2})(?:\D|$)")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class GateFailure(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


@lru_cache(maxsize=None)
def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateFailure(f"object required: {path}")
    return value


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise GateFailure(f"object required at {path}:{line_number}")
            yield value


def resolve(manifest_path: Path, raw: Any, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise GateFailure(f"path required: {label}")
    path = Path(raw)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve(strict=True)


def receipt_file_hash(receipt: Mapping[str, Any], role: str) -> str:
    for item in receipt.get("files", []):
        if isinstance(item, Mapping) and item.get("role") == role:
            return str(item.get("sha256", "")).lower()
    raise GateFailure(f"materialization receipt has no {role} file binding")


def require_sealed_hash(path: Path, raw: Any, label: str) -> None:
    expected = str(raw or "").lower()
    if not HEX64.fullmatch(expected):
        raise GateFailure(f"sealed SHA-256 required: {label}")
    actual = sha(path)
    if actual != expected:
        raise GateFailure(f"sealed SHA-256 mismatch for {label}: expected {expected}, got {actual}")


def validate_inputs(manifest_path: Path, manifest: Mapping[str, Any]) -> dict[str, Path]:
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
    sealed_hashes = {
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
    for role, path in sorted(paths.items()):
        require_sealed_hash(path, sealed_hashes.get(role), role)
    primary_receipt = read_json(paths["normalization_primary_receipt"])
    twin_receipt = read_json(paths["normalization_twin_receipt"])
    materialization_receipt = read_json(paths["materialization_receipt"])
    if primary_receipt.get("status") != "PASS" or twin_receipt.get("status") != "PASS":
        raise GateFailure("normalization primary/twin receipt is not PASS")
    if materialization_receipt.get("status") != "PASS":
        raise GateFailure("materialization receipt is not PASS")
    if paths["normalization_primary"].read_bytes() != paths["normalization_twin"].read_bytes():
        raise GateFailure("normalization primary/twin payloads are not byte equal")
    if paths["normalization_primary_receipt"].read_bytes() != paths[
        "normalization_twin_receipt"
    ].read_bytes():
        raise GateFailure("normalization primary/twin receipts are not byte equal")
    normalization_hash = sha(paths["normalization_primary"])
    if str((primary_receipt.get("output") or {}).get("sha256", "")).lower() != normalization_hash:
        raise GateFailure("normalization receipt payload hash mismatch")
    if receipt_file_hash(materialization_receipt, "people") != sha(paths["people"]):
        raise GateFailure("materialization people hash mismatch")
    validation = primary_receipt.get("validation") or {}
    if validation.get("exact_span_round_trip") != "PASS":
        raise GateFailure("normalization receipt exact-span gate is not PASS")
    if any(
        validation.get(field) != 0
        for field in (
            "canonical_date_range_promotions",
            "canonical_employment_promotions",
            "canonical_identity_promotions",
            "canonical_office_employer_promotions",
            "canonical_role_title_promotions",
            "complete_history_assertions",
        )
    ):
        raise GateFailure("normalization receipt contains a promotion")
    return paths


def load_a5b_gap_people(
    manifest: Mapping[str, Any], paths: Mapping[str, Path], person_ids: set[str]
) -> set[str]:
    a5b = manifest.get("a5b_final_gaps") or {}
    gap_code = str(a5b.get("gap_code", ""))
    if not gap_code:
        raise GateFailure("a5b_final_gaps.gap_code is required")
    expected_scope_size = manifest.get("expected_scope_size")
    expected_gap_people = a5b.get("expected_bounded_interval_gap_people")
    if not (
        isinstance(expected_scope_size, int)
        and not isinstance(expected_scope_size, bool)
        and expected_scope_size > 0
    ):
        raise GateFailure("positive expected_scope_size is required")
    if not (
        isinstance(expected_gap_people, int)
        and not isinstance(expected_gap_people, bool)
        and expected_gap_people >= 0
    ):
        raise GateFailure("nonnegative expected A5b bounded-gap count is required")

    receipt = read_json(paths["a5b_receipt"])
    verification = read_json(paths["a5b_verification"])
    if receipt.get("status") != "PASS" or verification.get("status") != "PASS":
        raise GateFailure("A5b receipt/verification is not PASS")
    if str((receipt.get("output") or {}).get("sha256", "")).lower() != sha(paths["a5b_ledger"]):
        raise GateFailure("A5b receipt does not bind the final gap ledger")
    if (receipt.get("gap_counts") or {}).get(gap_code) != expected_gap_people:
        raise GateFailure("A5b receipt bounded-gap count does not match the manifest seal")
    if (verification.get("gap_counts") or {}).get(gap_code) != expected_gap_people:
        raise GateFailure("A5b verification bounded-gap count does not match the manifest seal")

    seen: set[str] = set()
    gap_people: set[str] = set()
    row_count = 0
    for row in rows(paths["a5b_ledger"]):
        row_count += 1
        lda_id = str(row.get("lda_source_person_id", ""))
        if not lda_id or lda_id in seen:
            raise GateFailure(f"A5b ledger has missing/duplicate source ID: {lda_id}")
        seen.add(lda_id)
        if gap_code in set(row.get("critical_path_gap_codes") or []):
            gap_people.add(lda_id)
    if row_count != expected_scope_size or seen != person_ids:
        raise GateFailure("A5b ledger does not exactly conserve the sealed person scope")
    if len(gap_people) != expected_gap_people:
        raise GateFailure(
            f"A5b ledger bounded-gap count mismatch: {len(gap_people)} != {expected_gap_people}"
        )
    return gap_people


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


def rejection_reasons(row: Mapping[str, Any]) -> list[str]:
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
    claim_text = str(row.get("claim_text", ""))
    for name, mention in (("ROLE", role), ("OFFICE", office), ("DATE", date)):
        if not round_trip(claim_text, mention):
            reasons.add(f"{name}_SPAN_ROUND_TRIP_FAILED")
    spans = sorted(
        (mention.get("span_start"), mention.get("span_end"))
        for mention in (role, office, date)
        if isinstance(mention.get("span_start"), int) and isinstance(mention.get("span_end"), int)
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


def source_pointer(
    row: Mapping[str, Any],
    person: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    return {
        "claim_id": row.get("claim_id"),
        "lda_source_person_id": row.get("lda_source_person_id"),
        "normalization_ledger": str(paths["normalization_primary"]),
        "normalization_ledger_sha256": sha(paths["normalization_primary"]),
        "source_claim_row_ordinal": row.get("source_claim_row_ordinal"),
        "source_filing_years": person.get("filing_years", []),
        "source_person_candidate_id": person.get("candidate_id"),
    }


def candidate_row(
    row: Mapping[str, Any], person: Mapping[str, Any], paths: Mapping[str, Path]
) -> dict[str, Any]:
    role = row["role_title_mentions"][0]
    office = row["office_employer_mentions"][0]
    date = row["date_range_mentions"][0]
    identifier = "lda-bounded-episode-candidate:" + hashlib.sha256(
        compact(
            [
                row.get("claim_id"),
                role.get("span_start"),
                role.get("span_end"),
                office.get("span_start"),
                office.get("span_end"),
                date.get("span_start"),
                date.get("span_end"),
            ]
        )
    ).hexdigest()
    return {
        "bounded_episode_candidate_id": identifier,
        "candidate_status": "REVIEW_REQUIRED",
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "claim_text": row.get("claim_text"),
        "complete_lifetime_employment_asserted": False,
        "date_literal": date.get("text"),
        "date_range_mention": date,
        "end_year_candidate": date.get("explicit_end_year"),
        "identity_status": "NOT_ADJUDICATED",
        "interval_continuity_asserted": False,
        "lda_source_person_id": row.get("lda_source_person_id"),
        "office_employer_mention": office,
        "raw_covered_position_literal": row.get("raw_covered_position_literal"),
        "role_title_mention": role,
        "schema_id": CANDIDATE_SCHEMA,
        "source_pointer": source_pointer(row, person, paths),
        "start_year_candidate": date.get("explicit_start_year"),
        "year_precision_only": True,
    }


def blocker_row(
    row: Mapping[str, Any], person: Mapping[str, Any], paths: Mapping[str, Path], reasons: list[str]
) -> dict[str, Any]:
    return {
        "blocker_status": "REVIEW_REQUIRED_NO_EPISODE_EMITTED",
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "claim_text": row.get("claim_text"),
        "complete_lifetime_employment_asserted": False,
        "date_range_mention": row["date_range_mentions"][0],
        "lda_source_person_id": row.get("lda_source_person_id"),
        "office_employer_mention": row["office_employer_mentions"][0],
        "raw_covered_position_literal": row.get("raw_covered_position_literal"),
        "rejection_reasons": reasons,
        "role_title_mention": row["role_title_mentions"][0],
        "schema_id": BLOCKER_SCHEMA,
        "source_pointer": source_pointer(row, person, paths),
    }


def write_gzip(path: Path, values: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temp = Path(name)
    try:
        with temp.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                    for value in values:
                        text.write(compact(value).decode() + "\n")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def run(manifest_path: Path, output_dir: Path) -> dict[str, Any]:
    manifest_path = manifest_path.resolve(strict=True)
    manifest = read_json(manifest_path)
    if manifest.get("schema_id") != MANIFEST_SCHEMA:
        raise GateFailure("unexpected manifest schema")
    expected_scope_size = manifest.get("expected_scope_size")
    if not (
        isinstance(expected_scope_size, int)
        and not isinstance(expected_scope_size, bool)
        and expected_scope_size > 0
    ):
        raise GateFailure("positive expected_scope_size is required")
    paths = validate_inputs(manifest_path, manifest)
    people: dict[str, dict[str, Any]] = {}
    for person in rows(paths["people"]):
        lda_id = str(person.get("lda_source_person_id", ""))
        if lda_id in people:
            raise GateFailure(f"duplicate person source ID: {lda_id}")
        people[lda_id] = person
    if len(people) != expected_scope_size:
        raise GateFailure(f"people scope is not {expected_scope_size:,}: {len(people)}")
    a5b_gap_people = load_a5b_gap_people(manifest, paths, set(people))

    candidates: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    funnel: Counter[str] = Counter()
    claim_ids: set[str] = set()
    for row in rows(paths["normalization_primary"]):
        funnel["input_claim_rows"] += 1
        claim_id = str(row.get("claim_id", ""))
        if claim_id in claim_ids:
            raise GateFailure(f"duplicate normalized claim ID: {claim_id}")
        claim_ids.add(claim_id)
        lda_id = str(row.get("lda_source_person_id", ""))
        if lda_id not in people:
            raise GateFailure(f"normalized claim has out-of-scope person: {lda_id}")
        exact_cardinality = (
            len(row.get("role_title_mentions") or []) == 1
            and len(row.get("office_employer_mentions") or []) == 1
            and len(row.get("date_range_mentions") or []) == 1
        )
        if not exact_cardinality:
            continue
        funnel["exact_one_role_one_office_one_date_range"] += 1
        reasons = rejection_reasons(row)
        if reasons:
            blockers.append(blocker_row(row, people[lda_id], paths, reasons))
            reason_counts.update(reasons)
        else:
            candidates.append(candidate_row(row, people[lda_id], paths))

    candidates.sort(key=lambda row: (row["source_pointer"]["source_claim_row_ordinal"], row["bounded_episode_candidate_id"]))
    blockers.sort(key=lambda row: (row["source_pointer"]["source_claim_row_ordinal"], row["source_pointer"]["claim_id"]))
    output_dir = output_dir.resolve()
    candidate_path = output_dir / "lda_conservative_bounded_episode_candidates.ndjson.gz"
    blocker_path = output_dir / "lda_conservative_bounded_episode_blockers.ndjson.gz"
    receipt_path = output_dir / "lda_conservative_bounded_episode_receipt.json"
    write_gzip(candidate_path, candidates)
    write_gzip(blocker_path, blockers)
    candidate_people = {row["lda_source_person_id"] for row in candidates}
    a5b_gap_people_gaining_candidate = candidate_people & a5b_gap_people
    risk_notes = [
        "Two-digit years are never century-expanded.",
        "Year ranges are never converted to day-level bounds.",
        "Continuity is never inferred.",
    ]
    if not candidates:
        risk_notes.append(
            "Every exact-cardinality row retains a boundary, linkage, ambiguity, date, or span blocker, so no episode candidate is emitted."
        )
    result = {
        "blocker_counts": dict(sorted(reason_counts.items())),
        "candidate_rows": len(candidates),
        "candidates": {
            "bytes": candidate_path.stat().st_size,
            "path": candidate_path.name,
            "sha256": sha(candidate_path),
        },
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["source_claim_row_ordinal", "candidate_or_claim_id"],
        },
        "filter_funnel": dict(sorted(funnel.items())),
        "gap_impact": {
            "a5b_bounded_interval_gap_people": len(a5b_gap_people),
            "a5b_gap_people_gaining_review_required_bounded_candidate": len(
                a5b_gap_people_gaining_candidate
            ),
            "a5b_gap_people_remaining_without_a6_candidate": len(
                a5b_gap_people - candidate_people
            ),
            "canonical_bounded_interval_gap_closures": 0,
            "candidate_people_outside_a5b_bounded_gap": len(candidate_people - a5b_gap_people),
        },
        "near_candidate_blocker_rows": len(blockers),
        "near_candidate_blockers": {
            "bytes": blocker_path.stat().st_size,
            "path": blocker_path.name,
            "sha256": sha(blocker_path),
        },
        "network_acquisition_performed": False,
        "people_with_candidate": len(candidate_people),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "risk_notes": risk_notes,
        "schema_id": RECEIPT_SCHEMA,
        "source": {
            key: {"bytes": path.stat().st_size, "path": str(path), "sha256": sha(path)}
            for key, path in sorted(paths.items())
        },
        "status": "BLOCKED_SAFE_LINKAGE_NOT_ESTABLISHED" if not candidates else "PASS",
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_bytes(compact(result) + b"\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = run(args.manifest, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
