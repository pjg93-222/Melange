#!/usr/bin/env python3
"""Consolidate staffer-network acquisition slices and emit residual work queues.

The script is deliberately offline.  It accelerates normalization,
deduplication, completeness auditing, and scheduling without increasing
request pressure on any external source.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from fec.staffer_network.employment_history import audit_history_completeness
from fec.staffer_network.schema_validation import validate_instance


SLICE_RE = re.compile(r"slice_(\d+_\d+)")
RECEIPT_SCHEMA_PATH = (
    REPOSITORY_ROOT
    / "fec"
    / "staffer_network"
    / "schemas"
    / "working_history_corpus_receipt.schema.json"
)
RECEIPT_SCHEMA_ID = "staffer-network-working-history-corpus-receipt-v2"
RESERVED_PERSON_IDS = frozenset({"unresolved"})


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


def read_rows(path: Path) -> list[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[dict[str, Any]] = []
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def write_gzip(path: Path, rows: Iterable[dict[str, Any]], *, key) -> int:
    ordered = sorted(rows, key=key)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in ordered:
                stream.write(canonical_bytes(row))
    return len(ordered)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_bytes(value))


def slice_tag(path: Path) -> str | None:
    match = SLICE_RE.search(path.name)
    return match.group(1) if match else None


def input_inventory(root: Path) -> list[Path]:
    enrichment = sorted(root.glob("legistorm_lda_profile_enrichment_*_slice_*.ndjson"))
    enriched_slices = {tag for path in enrichment if (tag := slice_tag(path))}
    fanout = [
        path
        for path in sorted(root.glob("legistorm_lda_profile_fanout_*_slice_*.ndjson"))
        if slice_tag(path) not in enriched_slices
    ]
    return enrichment + fanout


def classify_person_id(row: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return a trimmed identity or a fail-closed rejection reason.

    ``UNRESOLVED`` is a reserved sentinel, never a person identifier.  Both
    supported ID locations are considered so conflicting IDs cannot be silently
    assigned to either person.
    """

    raw_values: list[Any] = [row.get("lda_source_person_id")]
    identity = row.get("person_identity")
    if isinstance(identity, dict):
        raw_values.append(identity.get("lda_source_person_id"))

    candidates: list[str] = []
    saw_reserved = False
    for raw_value in raw_values:
        if not isinstance(raw_value, str):
            continue
        value = raw_value.strip()
        if not value:
            continue
        if value.casefold() in RESERVED_PERSON_IDS:
            saw_reserved = True
            continue
        candidates.append(value)

    distinct_candidates = sorted(set(candidates))
    if len(distinct_candidates) > 1:
        return None, "CONFLICTING_PERSON_IDS"
    if distinct_candidates:
        return distinct_candidates[0], None
    if saw_reserved:
        return None, "RESERVED_UNRESOLVED_PERSON_ID"
    return None, "MISSING_OR_BLANK_PERSON_ID"


def person_id(row: dict[str, Any]) -> str | None:
    return classify_person_id(row)[0]


def episodes(row: dict[str, Any]) -> list[dict[str, Any]]:
    value = row.get("employment_episodes")
    if value is None:
        value = row.get("employment_history", [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def education(row: dict[str, Any]) -> list[dict[str, Any]]:
    value = row.get("education")
    if value is None:
        value = row.get("education_history", [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def normalized_sources(value: Any) -> list[str]:
    if isinstance(value, str) and value:
        return [value]
    if isinstance(value, list):
        return sorted({item for item in value if isinstance(item, str) and item})
    return []


def episode_signature(row: dict[str, Any]) -> str:
    fields = (
        row.get("employer", row.get("raw_employer")),
        row.get("title", row.get("raw_title")),
        row.get("raw_dates"),
        row.get("raw_start"),
        row.get("raw_end"),
        row.get("start_date", row.get("start_earliest")),
        row.get("end_date", row.get("end_earliest")),
    )
    return hashlib.sha256(canonical_bytes(fields)).hexdigest()


def education_signature(row: dict[str, Any]) -> str:
    fields = (
        row.get("institution"),
        row.get("degree"),
        row.get("field", row.get("field_of_study")),
        row.get("years"),
        row.get("class_year", row.get("class_year_lead")),
        row.get("start_date", row.get("start_earliest")),
        row.get("end_date", row.get("end_earliest")),
    )
    return hashlib.sha256(canonical_bytes(fields)).hexdigest()


def merge_evidence(items: Iterable[dict[str, Any]], *, signature) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        key = signature(item)
        if key not in merged:
            merged[key] = dict(item)
            continue
        existing = merged[key]
        sources = set(normalized_sources(existing.get("source_urls")))
        sources.update(normalized_sources(existing.get("source_url")))
        sources.update(normalized_sources(item.get("source_urls")))
        sources.update(normalized_sources(item.get("source_url")))
        if sources:
            existing["source_urls"] = sorted(sources)
            existing.pop("source_url", None)
    return [merged[key] for key in sorted(merged)]


def row_score(row: dict[str, Any]) -> tuple[int, int, int, int]:
    complete = str(
        row.get("history_completeness", row.get("completion_status", ""))
    ).lower() in {"complete", "complete_history"}
    resolved = row.get("legistorm_person_id") is not None
    return (int(complete), len(episodes(row)), int(resolved), len(education(row)))


def _consolidate_identified(
    rows: list[tuple[Path, dict[str, Any]]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[tuple[Path, dict[str, Any]]]] = defaultdict(list)
    for path, row in rows:
        pid = person_id(row)
        if pid:
            grouped[pid].append((path, row))

    output: list[dict[str, Any]] = []
    for pid, source_rows in sorted(grouped.items()):
        base_path, base = max(source_rows, key=lambda item: row_score(item[1]))
        all_episodes = merge_evidence(
            (episode for _, row in source_rows for episode in episodes(row)),
            signature=episode_signature,
        )
        all_education = merge_evidence(
            (item for _, row in source_rows for item in education(row)),
            signature=education_signature,
        )
        source_urls = sorted({
            url
            for _, row in source_rows
            for url in normalized_sources(row.get("source_urls"))
        })
        linkedin_urls = [url for url in source_urls if "linkedin.com/" in url.lower()]
        gap_values: set[str] = set()
        legacy_gap_invalid = False
        for _, row in source_rows:
            for key in ("history_gaps", "unresolved_history_gaps", "known_gaps"):
                if key not in row:
                    continue
                value = row[key]
                if not isinstance(value, list):
                    legacy_gap_invalid = True
                    continue
                gap_values.update(str(gap) for gap in value)
        gaps = sorted(gap_values)
        typed_gap_values: set[str] = set()
        typed_gap_invalid = False
        for _, row in source_rows:
            source_attestation = row.get("history_completeness_attestation")
            if source_attestation is None:
                continue
            if not isinstance(source_attestation, dict):
                typed_gap_invalid = True
                continue
            source_has_gap_field = False
            for key in ("unresolved_employment_gaps", "unresolved_gaps"):
                if key not in source_attestation:
                    continue
                source_has_gap_field = True
                value = source_attestation[key]
                if not isinstance(value, list):
                    typed_gap_invalid = True
                    continue
                # Preserve even blank-looking entries. A nonempty source gap
                # list must remain nonempty so the core audit fails closed.
                typed_gap_values.update(str(gap) for gap in value)
            if not source_has_gap_field:
                typed_gap_invalid = True
        attestation = base.get("history_completeness_attestation")
        if isinstance(attestation, dict):
            attestation = dict(attestation)
            if typed_gap_invalid or legacy_gap_invalid:
                # Preserve a fail-closed non-list value so the core audit emits
                # UNRESOLVED_EMPLOYMENT_GAPS_INVALID.
                attestation["unresolved_employment_gaps"] = {
                    "invalid_source_attestation_gap_field": True
                }
            else:
                attestation["unresolved_employment_gaps"] = sorted(
                    typed_gap_values | set(gaps)
                )
        consolidated = {
            "schema_id": "staffer-network-working-history-profile-v1",
            "lda_source_person_id": pid,
            "display_name": base.get("display_name"),
            "legistorm_person_ids": sorted({
                value
                for _, row in source_rows
                if (value := row.get("legistorm_person_id")) is not None
            }, key=str),
            "employment_episodes": all_episodes,
            "education": all_education,
            "source_urls": source_urls,
            "linkedin_source_urls": linkedin_urls,
            "linkedin_evidence_status": (
                "RAW_CANDIDATE_ONLY" if linkedin_urls else "NONE"
            ),
            "verification_status": "DEFERRED_UNTIL_COLLECTION_COMPLETE",
            "history_gaps": gaps,
            "history_completeness_attestation": attestation,
            "source_artifacts": sorted({str(path) for path, _ in source_rows}),
            "source_row_count": len(source_rows),
            "preferred_source_artifact": str(base_path),
            "canonical_identity_decision": "NOT_ADJUDICATED",
        }
        audit = audit_history_completeness(consolidated)
        consolidated["completeness_audit"] = audit
        consolidated["history_completeness"] = (
            "complete_history"
            if audit["employment_status"] == "COMPLETE"
            else ("partial_history" if all_episodes or all_education else "unresolved")
        )
        consolidated["employment_completeness"] = audit["employment_status"]
        consolidated["education_completeness"] = audit["education_status"]
        output.append(consolidated)
    return output


def consolidate_with_accounting(
    rows: list[tuple[Path, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Consolidate valid identities and account for every supplied input row."""

    identified_rows: list[tuple[Path, dict[str, Any]]] = []
    unidentified_rows: list[dict[str, Any]] = []
    identity_counts: Counter[str] = Counter()
    rejection_counts: Counter[str] = Counter()
    source_ordinals: Counter[str] = Counter()

    for input_row_ordinal, (path, row) in enumerate(rows, start=1):
        source_artifact = str(path)
        source_ordinals[source_artifact] += 1
        pid, rejection_reason = classify_person_id(row)
        if pid is not None:
            identity_counts[pid] += 1
            identified_rows.append((path, row))
            continue

        reason = rejection_reason or "UNCLASSIFIED_PERSON_ID_FAILURE"
        rejection_counts[reason] += 1
        unidentified_rows.append({
            "schema_id": "staffer-network-unidentified-history-input-row-v1",
            "input_row_ordinal": input_row_ordinal,
            "source_artifact": source_artifact,
            "source_row_ordinal": source_ordinals[source_artifact],
            "source_row_sha256": hashlib.sha256(canonical_bytes(row)).hexdigest(),
            "rejection_reason": reason,
        })

    profiles = _consolidate_identified(identified_rows)
    consumed_identified_rows = sum(
        int(profile["source_row_count"]) for profile in profiles
    )
    accounted_input_rows = consumed_identified_rows + len(unidentified_rows)
    duplicate_identity_counts = {
        pid: count for pid, count in sorted(identity_counts.items()) if count > 1
    }
    profile_ids = [profile["lda_source_person_id"] for profile in profiles]
    output_duplicate_person_ids = len(profile_ids) - len(set(profile_ids))
    accounting = {
        "input_rows": len(rows),
        "identified_input_rows": len(identified_rows),
        "unidentified_input_rows": len(unidentified_rows),
        "dropped_input_rows": len(unidentified_rows),
        "consumed_identified_input_rows": consumed_identified_rows,
        "accounted_input_rows": accounted_input_rows,
        "duplicate_identified_input_rows": sum(
            count - 1 for count in duplicate_identity_counts.values()
        ),
        "duplicate_identified_person_ids": len(duplicate_identity_counts),
        "output_duplicate_person_ids": output_duplicate_person_ids,
        "classification_row_conservation_ok": (
            len(rows) == len(identified_rows) + len(unidentified_rows)
        ),
        "identified_row_conservation_ok": (
            len(identified_rows) == consumed_identified_rows
        ),
        "input_row_conservation_ok": len(rows) == accounted_input_rows,
        "output_person_ids_unique": output_duplicate_person_ids == 0,
        "unidentified_reason_counts": dict(sorted(rejection_counts.items())),
    }
    return profiles, unidentified_rows, accounting


def consolidate(rows: list[tuple[Path, dict[str, Any]]]) -> list[dict[str, Any]]:
    """Backward-compatible profile-only consolidation entry point."""

    return consolidate_with_accounting(rows)[0]


def consolidation_status(
    profiles: list[dict[str, Any]], row_accounting: dict[str, Any], *, unseen_people: int = 0
) -> tuple[str, list[str]]:
    """Derive the receipt status from completeness and conservation evidence."""

    incomplete_reasons: list[str] = []
    if row_accounting["input_rows"] == 0:
        incomplete_reasons.append("INPUT_ROWS_EMPTY")
    if unseen_people:
        incomplete_reasons.append("QUEUE_PEOPLE_UNSEEN")
    if any(row["employment_completeness"] != "COMPLETE" for row in profiles):
        incomplete_reasons.append("IDENTIFIED_EMPLOYMENT_NOT_COMPLETE")
    if row_accounting["unidentified_input_rows"]:
        incomplete_reasons.append("UNIDENTIFIED_INPUT_ROWS")
    if row_accounting["duplicate_identified_input_rows"]:
        incomplete_reasons.append("DUPLICATE_IDENTIFIED_PERSON_IDS")
    if not row_accounting["classification_row_conservation_ok"]:
        incomplete_reasons.append("CLASSIFICATION_ROW_CONSERVATION_FAILURE")
    if not row_accounting["identified_row_conservation_ok"]:
        incomplete_reasons.append("IDENTIFIED_ROW_CONSERVATION_FAILURE")
    if not row_accounting["input_row_conservation_ok"]:
        incomplete_reasons.append("INPUT_ROW_CONSERVATION_FAILURE")
    if not row_accounting["output_person_ids_unique"]:
        incomplete_reasons.append("OUTPUT_DUPLICATE_PERSON_IDS")
    return ("INCOMPLETE" if incomplete_reasons else "PASS", incomplete_reasons)


def validate_receipt(receipt: dict[str, Any]) -> None:
    """Validate both the committed schema and cross-field conservation rules."""

    schema = json.loads(RECEIPT_SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_instance(receipt, schema)
    accounting = receipt["row_accounting"]
    checks = {
        "input_row_count matches row accounting": (
            receipt["input_row_count"] == accounting["input_rows"]
        ),
        "classified rows conserve input": (
            accounting["input_rows"]
            == accounting["identified_input_rows"]
            + accounting["unidentified_input_rows"]
        ),
        "dropped rows equal unidentified rows": (
            accounting["dropped_input_rows"]
            == accounting["unidentified_input_rows"]
        ),
        "accounted rows equal consumed plus dropped": (
            accounting["accounted_input_rows"]
            == accounting["consumed_identified_input_rows"]
            + accounting["dropped_input_rows"]
        ),
        "all input rows are accounted": (
            accounting["input_rows"] == accounting["accounted_input_rows"]
        ),
        "all identified rows are consumed": (
            accounting["identified_input_rows"]
            == accounting["consumed_identified_input_rows"]
        ),
        "unidentified reasons conserve unidentified rows": (
            sum(accounting["unidentified_reason_counts"].values())
            == accounting["unidentified_input_rows"]
        ),
        "duplicate person ids are bounded by duplicate rows": (
            accounting["duplicate_identified_person_ids"]
            <= accounting["duplicate_identified_input_rows"]
            and (
                accounting["duplicate_identified_input_rows"] == 0
            ) == (
                accounting["duplicate_identified_person_ids"] == 0
            )
        ),
        "duplicate rows bridge consumed rows to processed people": (
            accounting["duplicate_identified_input_rows"]
            == accounting["consumed_identified_input_rows"]
            - receipt["processed_people"]
        ),
        "output duplicate count matches uniqueness flag": (
            accounting["output_person_ids_unique"]
            == (accounting["output_duplicate_person_ids"] == 0)
        ),
        "profile status counts equal processed people": (
            receipt["processed_people"]
            == receipt["complete_people"]
            + receipt["partial_people"]
            + receipt["unresolved_people"]
        ),
        "residual rows equal incomplete processed people": (
            receipt["residual_incomplete_rows"]
            == receipt["processed_people"] - receipt["complete_people"]
        ),
        "verification queue covers every processed person": (
            receipt["identity_verification_queue_rows"]
            == receipt["processed_people"]
        ),
        "queue rows equal processed plus unseen people": (
            receipt["queue_rows"]
            == receipt["processed_people"] + receipt["unseen_people"]
        ),
        "input artifact count matches manifest": (
            receipt["input_artifact_count"] == len(receipt["input_artifacts"])
        ),
        "file inventory matches worker count": (
            len(receipt["files"]) == 5 + receipt["python_worker_count"]
        ),
    }
    failures = [name for name, passed in checks.items() if not passed]
    if failures:
        raise ValueError("receipt semantic validation failed: " + "; ".join(failures))

    expected_reasons: list[str] = []
    if accounting["input_rows"] == 0:
        expected_reasons.append("INPUT_ROWS_EMPTY")
    if receipt["unseen_people"]:
        expected_reasons.append("QUEUE_PEOPLE_UNSEEN")
    if receipt["complete_people"] != receipt["processed_people"]:
        expected_reasons.append("IDENTIFIED_EMPLOYMENT_NOT_COMPLETE")
    if accounting["unidentified_input_rows"]:
        expected_reasons.append("UNIDENTIFIED_INPUT_ROWS")
    if accounting["duplicate_identified_input_rows"]:
        expected_reasons.append("DUPLICATE_IDENTIFIED_PERSON_IDS")
    if not accounting["classification_row_conservation_ok"]:
        expected_reasons.append("CLASSIFICATION_ROW_CONSERVATION_FAILURE")
    if not accounting["identified_row_conservation_ok"]:
        expected_reasons.append("IDENTIFIED_ROW_CONSERVATION_FAILURE")
    if not accounting["input_row_conservation_ok"]:
        expected_reasons.append("INPUT_ROW_CONSERVATION_FAILURE")
    if not accounting["output_person_ids_unique"]:
        expected_reasons.append("OUTPUT_DUPLICATE_PERSON_IDS")
    expected_status = "INCOMPLETE" if expected_reasons else "PASS"
    if receipt["incomplete_reasons"] != expected_reasons:
        raise ValueError("receipt incomplete reasons do not match receipt evidence")
    if receipt["status"] != expected_status:
        raise ValueError("receipt status does not match receipt evidence")


def residual_row(
    queue_row: dict[str, Any], rank: int, profile: dict[str, Any] | None
) -> dict[str, Any]:
    if profile is None:
        status = "UNSEEN"
        failure_codes = ["NO_ACQUISITION_RECORD"]
        employment_count = education_count = 0
        acquisition_priority = 2
    else:
        audit = profile["completeness_audit"]
        status = profile["history_completeness"].upper()
        failure_codes = audit["failure_codes"]
        employment_count = len(profile["employment_episodes"])
        education_count = len(profile["education"])
        acquisition_priority = (
            0 if status in {"PARTIAL_HISTORY", "UNRESOLVED"} else 1
        )
    return {
        "schema_id": "staffer-network-employment-residual-candidate-v1",
        "lookup_rank": rank,
        "lda_source_person_id": queue_row["lda_source_person_id"],
        "display_name": queue_row["display_name"],
        "original_priority": queue_row.get("priority"),
        "acquisition_priority": acquisition_priority,
        "working_history_status": status,
        "employment_episode_count": employment_count,
        "education_episode_count": education_count,
        "failure_codes": failure_codes,
        "search_queries": queue_row.get("search_queries", []),
        "covered_position_values": queue_row.get("covered_position_values", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fanout-root",
        default="audits/staffer_network/legistorm_fanout",
    )
    parser.add_argument(
        "--queue",
        default=(
            "C:/Users/pgoff/AppData/Local/Melange/staffer_network/"
            "employment-lookup/generation-20260831T050000Z/"
            "employment_lookup_queue.ndjson.gz"
        ),
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    fanout_root = Path(args.fanout_root)
    queue_path = Path(args.queue)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    inputs = input_inventory(fanout_root)
    if not inputs:
        raise SystemExit(f"no acquisition artifacts found in {fanout_root}")
    with ThreadPoolExecutor(max_workers=min(args.workers, len(inputs))) as executor:
        loaded = list(executor.map(read_rows, inputs))
    sourced_rows = [
        (path, row)
        for path, rows in zip(inputs, loaded, strict=True)
        for row in rows
    ]
    profiles, unidentified_input_rows, row_accounting = (
        consolidate_with_accounting(sourced_rows)
    )
    by_person = {row["lda_source_person_id"]: row for row in profiles}

    queue = read_rows(queue_path)
    residual: list[dict[str, Any]] = []
    unseen: list[dict[str, Any]] = []
    for rank, row in enumerate(queue, start=1):
        profile = by_person.get(person_id(row))
        candidate = residual_row(row, rank, profile)
        if profile is None:
            unseen.append(candidate)
        elif profile["history_completeness"] != "complete_history":
            residual.append(candidate)

    verification_queue = [
        {
            "schema_id": "staffer-network-identity-verification-candidate-v1",
            "lda_source_person_id": profile["lda_source_person_id"],
            "display_name": profile.get("display_name"),
            "verification_status": "DEFERRED_UNTIL_COLLECTION_COMPLETE",
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "legistorm_person_ids": profile["legistorm_person_ids"],
            "linkedin_source_urls": profile["linkedin_source_urls"],
            "source_urls": profile["source_urls"],
            "candidate_employers": sorted({
                str(item.get("employer", item.get("raw_employer"))).strip()
                for item in profile["employment_episodes"]
                if item.get("employer", item.get("raw_employer")) not in (None, "")
            }),
            "candidate_titles": sorted({
                str(item.get("title", item.get("raw_title"))).strip()
                for item in profile["employment_episodes"]
                if item.get("title", item.get("raw_title")) not in (None, "")
            }),
            "candidate_education_institutions": sorted({
                str(item.get("institution")).strip()
                for item in profile["education"]
                if item.get("institution") not in (None, "")
            }),
        }
        for profile in profiles
    ]

    corpus_path = output_root / "working_history_corpus.ndjson.gz"
    residual_path = output_root / "residual_incomplete_queue.ndjson.gz"
    unseen_path = output_root / "unseen_queue.ndjson.gz"
    verification_path = output_root / "identity_verification_queue.ndjson.gz"
    unidentified_path = output_root / "unidentified_input_rows.ndjson.gz"
    write_gzip(corpus_path, profiles, key=lambda row: row["lda_source_person_id"])
    write_gzip(
        residual_path,
        residual,
        key=lambda row: (row["acquisition_priority"], row["lookup_rank"]),
    )
    write_gzip(unseen_path, unseen, key=lambda row: row["lookup_rank"])
    write_gzip(
        verification_path,
        verification_queue,
        key=lambda row: row["lda_source_person_id"],
    )
    write_gzip(
        unidentified_path,
        unidentified_input_rows,
        key=lambda row: (
            row["source_artifact"],
            row["source_row_ordinal"],
            row["input_row_ordinal"],
        ),
    )
    worker_paths: list[Path] = []
    for worker_index in range(args.workers):
        path = output_root / f"unseen_worker_{worker_index + 1:02d}_of_{args.workers:02d}.ndjson.gz"
        shard = unseen[worker_index::args.workers]
        write_gzip(path, shard, key=lambda row: row["lookup_rank"])
        worker_paths.append(path)

    status_counts = Counter(row["history_completeness"] for row in profiles)
    receipt_status, incomplete_reasons = consolidation_status(
        profiles, row_accounting, unseen_people=len(unseen)
    )
    receipt = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": receipt_status,
        "incomplete_reasons": incomplete_reasons,
        "queue_sha256": sha256_file(queue_path),
        "queue_rows": len(queue),
        "input_artifact_count": len(inputs),
        "input_row_count": len(sourced_rows),
        "row_accounting": row_accounting,
        "processed_people": len(profiles),
        "unseen_people": len(unseen),
        "complete_people": status_counts["complete_history"],
        "partial_people": status_counts["partial_history"],
        "unresolved_people": status_counts["unresolved"],
        "employment_episode_count": sum(len(row["employment_episodes"]) for row in profiles),
        "education_episode_count": sum(len(row["education"]) for row in profiles),
        "residual_incomplete_rows": len(residual),
        "python_worker_count": args.workers,
        "identity_verification_deferred": True,
        "identity_verification_queue_rows": len(verification_queue),
        "linkedin_candidate_people": sum(bool(row["linkedin_source_urls"]) for row in profiles),
        "files": [
            {
                "role": role,
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for role, path in (
                ("working_history_corpus", corpus_path),
                ("residual_incomplete_queue", residual_path),
                ("unseen_queue", unseen_path),
                ("identity_verification_queue", verification_path),
                ("unidentified_input_rows", unidentified_path),
            )
        ] + [
            {
                "role": f"unseen_worker_{index + 1:02d}",
                "path": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for index, path in enumerate(worker_paths)
        ],
        "input_artifacts": [
            {"path": str(path), "sha256": sha256_file(path)} for path in inputs
        ],
        "canonical_identity_promotions": 0,
    }
    validate_receipt(receipt)
    write_json(output_root / "working_history_corpus_receipt.json", receipt)
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
