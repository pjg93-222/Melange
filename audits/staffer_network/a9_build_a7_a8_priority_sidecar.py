#!/usr/bin/env python3
"""Build the immutable A9 A7/A8 review-priority sidecar.

The sidecar joins the sealed A5b 25,340-person priority baseline to A7 FEC
employer point observations and A8 1997Q1 House payroll name-match candidates.
A7 LD-203 affiliation rows are intentionally not consumed.  FEC point
observations add context but clear no former-position or interval gap.  A8
rows are dated and bounded former-House-position candidates for scheduling,
but remain unadjudicated name matches and therefore route to P3 review.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Iterator, Mapping


MANIFEST_SCHEMA = "staffer-network-a9-a7-a8-priority-sidecar-manifest-v1"
ROW_SCHEMA = "staffer-network-a9-a7-a8-priority-sidecar-row-v1"
RECEIPT_SCHEMA = "staffer-network-a9-a7-a8-priority-sidecar-receipt-v1"
STAGE_ID = "A9-a7-a8-priority-sidecar-integration"
BUCKET_RANK = {
    "P0_NO_EMPLOYMENT_CANDIDATE": 0,
    "P1_DATED_FORMER_POSITION_MISSING": 1,
    "P2_BOUNDED_INTERVAL_MISSING": 2,
    "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION": 3,
}
P3 = "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION"


class GateFailure(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_line(value: Any) -> bytes:
    return compact(value) + b"\n"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_values(values: Iterable[str]) -> str:
    return hashlib.sha256(compact(sorted(set(values)))).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise GateFailure(f"JSON object required: {path}")
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


def resolve(repo_root: Path, entry: Mapping[str, Any]) -> Path:
    path = Path(str(entry["path"]))
    return (path if path.is_absolute() else repo_root / path).resolve()


def bind_inputs(
    manifest: Mapping[str, Any], repo_root: Path
) -> dict[str, Path]:
    if manifest.get("schema_id") != MANIFEST_SCHEMA:
        raise GateFailure("unexpected A9 manifest schema")
    if manifest.get("stage_id") != STAGE_ID:
        raise GateFailure("unexpected A9 stage ID")
    required = {
        "a5b_independent_verification",
        "a5b_priority_ledger",
        "a5b_priority_receipt",
        "a7_build_receipt",
        "a7_fec_employer_observations",
        "a7_independent_verification",
        "a8_house_match_candidates",
        "a8_independent_verification",
        "a8_match_receipt",
    }
    inputs = manifest.get("inputs") or {}
    if set(inputs) != required:
        raise GateFailure("manifest input set is not exact")
    bound: dict[str, Path] = {}
    for label in sorted(required):
        entry = inputs[label]
        path = resolve(repo_root, entry)
        if not path.is_file():
            raise GateFailure(f"input missing: {label}: {path}")
        if path.stat().st_size != entry.get("bytes") or sha(path) != entry.get("sha256"):
            raise GateFailure(f"input seal mismatch: {label}")
        bound[label] = path
    return bound


def validate_receipts(
    manifest: Mapping[str, Any], paths: Mapping[str, Path]
) -> None:
    expected = manifest["expected"]
    a5_receipt = read_json(paths["a5b_priority_receipt"])
    a5_verify = read_json(paths["a5b_independent_verification"])
    a7_receipt = read_json(paths["a7_build_receipt"])
    a7_verify = read_json(paths["a7_independent_verification"])
    a8_receipt = read_json(paths["a8_match_receipt"])
    a8_verify = read_json(paths["a8_independent_verification"])
    checks = {
        "a5_pass": a5_receipt.get("status") == a5_verify.get("status") == "PASS",
        "a5_ledger_bound": a5_receipt.get("output", {}).get("sha256")
        == a5_verify.get("hashes", {}).get("primary_payload_sha256")
        == manifest["inputs"]["a5b_priority_ledger"]["sha256"],
        "a5_receipt_bound": a5_verify.get("hashes", {}).get("primary_receipt_sha256")
        == manifest["inputs"]["a5b_priority_receipt"]["sha256"],
        "a5_scope": a5_receipt.get("output", {}).get("rows")
        == expected["a5b_people"],
        "a7_pass": a7_receipt.get("status") == a7_verify.get("status") == "PASS",
        "a7_fec_ledger_bound": a7_receipt.get("outputs", {})
        .get("fec_candidates", {})
        .get("sha256")
        == manifest["inputs"]["a7_fec_employer_observations"]["sha256"],
        "a7_fec_rows": a7_receipt.get("fec", {}).get("candidates_emitted")
        == a7_verify.get("fec_candidates")
        == expected["a7_fec_candidate_rows"],
        "a7_fec_people": a7_receipt.get("fec", {}).get("people_with_candidates")
        == a7_verify.get("fec_people")
        == expected["a7_fec_people"],
        "a7_fec_twin_verified": a7_verify.get("twin_byte_equal", {}).get(
            "fec_candidates"
        )
        is True,
        "a8_pass": a8_receipt.get("status") == a8_verify.get("status") == "PASS",
        "a8_ledger_bound": a8_receipt.get("output", {}).get("sha256")
        == a8_verify.get("hashes", {}).get("primary_payload_sha256")
        == manifest["inputs"]["a8_house_match_candidates"]["sha256"],
        "a8_receipt_bound": a8_verify.get("hashes", {}).get("primary_receipt_sha256")
        == manifest["inputs"]["a8_match_receipt"]["sha256"],
        "a8_rows": a8_receipt.get("counts", {}).get("match_candidate_rows")
        == a8_verify.get("counts", {}).get("match_candidate_rows")
        == expected["a8_candidate_rows"],
        "a8_people": a8_receipt.get("counts", {}).get(
            "distinct_matched_lda_people"
        )
        == a8_verify.get("counts", {}).get("distinct_matched_lda_people")
        == expected["a8_people"],
        "a8_twin_verified": a8_verify.get("assertions", {}).get(
            "payload_bytes_equal"
        )
        is True,
        "all_receipts_zero_promotion": all(
            receipt.get("canonical_identity_promotions", 0) == 0
            and receipt.get("canonical_employment_promotions", 0) == 0
            for receipt in (a5_receipt, a7_receipt)
        )
        and a8_receipt.get("validation", {}).get("canonical_identity_promotions")
        == 0
        and a8_receipt.get("validation", {}).get("canonical_employment_promotions")
        == 0,
    }
    failures = sorted(name for name, passed in checks.items() if not passed)
    if failures:
        raise GateFailure("receipt validation failed: " + ", ".join(failures))


def load_a5b(
    path: Path, expected_people: int, expected_buckets: Mapping[str, int]
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    ordered: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    bucket_counts: Counter[str] = Counter()
    queue_ordinals: set[int] = set()
    for row in rows(path):
        lda_id = str(row.get("lda_source_person_id") or "")
        if not lda_id or lda_id in by_id:
            raise GateFailure(f"missing/duplicate A5b person ID: {lda_id!r}")
        bucket = row.get("priority_bucket")
        if bucket not in BUCKET_RANK or row.get("priority_rank") != BUCKET_RANK[bucket]:
            raise GateFailure(f"invalid A5b priority for {lda_id}")
        queue_ordinal = row.get("priority_queue_ordinal")
        if not isinstance(queue_ordinal, int) or queue_ordinal in queue_ordinals:
            raise GateFailure(f"invalid/duplicate A5b queue ordinal for {lda_id}")
        queue_ordinals.add(queue_ordinal)
        if not (
            row.get("adjudication_status") == "REVIEW_REQUIRED"
            and row.get("canonical_identity_promoted") is False
            and row.get("canonical_employment_promoted") is False
            and row.get("complete_lifetime_employment_asserted") is False
        ):
            raise GateFailure(f"A5b zero-promotion invariant failed for {lda_id}")
        by_id[lda_id] = row
        ordered.append(row)
        bucket_counts[bucket] += 1
    if len(by_id) != expected_people or queue_ordinals != set(range(1, expected_people + 1)):
        raise GateFailure("A5b does not conserve its exact queue scope")
    if dict(sorted(bucket_counts.items())) != dict(sorted(expected_buckets.items())):
        raise GateFailure("A5b bucket counts differ from manifest")
    return ordered, by_id


def load_a7_fec(
    path: Path, scope: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], int]:
    working: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "candidate_ids": [],
            "dates": [],
            "employers": set(),
            "occupations": set(),
            "registrants": set(),
        }
    )
    seen_ids: set[str] = set()
    row_count = 0
    for row in rows(path):
        row_count += 1
        candidate_id = str(row.get("candidate_id") or "")
        lda_id = str(row.get("lda_source_person_id") or "")
        date = row.get("observation_date")
        if not candidate_id or candidate_id in seen_ids:
            raise GateFailure("A7 FEC candidate ID missing/duplicate")
        seen_ids.add(candidate_id)
        if lda_id not in scope:
            raise GateFailure(f"A7 FEC person is outside A5b: {lda_id}")
        if not (
            row.get("schema_id")
            == "staffer-network-a7-fec-employment-observation-candidate-v1"
            and row.get("candidate_kind")
            == "FEC_REPORTED_EMPLOYER_OCCUPATION_POINT_OBSERVATION"
            and row.get("review_disposition") == "REVIEW_REQUIRED"
            and row.get("identity_status") == "REVIEW_REQUIRED"
            and row.get("identity_anchor_count") == 3
            and row.get("canonical_identity_promoted") is False
            and row.get("canonical_employment_promoted") is False
            and row.get("complete_history_asserted") is False
            and row.get("employment_interval_asserted") is False
            and isinstance(date, str)
        ):
            raise GateFailure(f"invalid A7 FEC point observation: {candidate_id}")
        entry = working[lda_id]
        entry["candidate_ids"].append(candidate_id)
        entry["dates"].append(date)
        entry["employers"].add(str(row.get("source_employer_key") or ""))
        occupation = str(row.get("raw_occupation") or "").strip()
        if occupation:
            entry["occupations"].add(occupation)
        for anchor in row.get("lda_registrant_anchors") or []:
            registrant_id = str(anchor.get("lda_registrant_id") or "")
            if registrant_id:
                entry["registrants"].add(registrant_id)
    result: dict[str, dict[str, Any]] = {}
    for lda_id, value in working.items():
        result[lda_id] = {
            "candidate_count": len(value["candidate_ids"]),
            "candidate_id_digest": digest_values(value["candidate_ids"]),
            "distinct_employer_count": len(value["employers"]),
            "distinct_occupation_count": len(value["occupations"]),
            "distinct_registrant_anchor_count": len(value["registrants"]),
            "first_observation_date": min(value["dates"]),
            "last_observation_date": max(value["dates"]),
        }
    return result, row_count


def load_a8_house(
    path: Path, scope: Mapping[str, Any]
) -> tuple[dict[str, dict[str, Any]], int]:
    working: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "candidate_ids": [],
            "source_ids": set(),
            "starts": [],
            "ends": [],
            "offices": set(),
            "titles": set(),
            "classes": Counter(),
            "ambiguities": Counter(),
        }
    )
    seen_ids: set[str] = set()
    row_count = 0
    for row in rows(path):
        row_count += 1
        candidate_id = str(row.get("candidate_match_id") or "")
        lda_id = str(row.get("lda_source_person_id") or "")
        start = row.get("service_start_date_candidate_iso")
        end = row.get("service_end_date_candidate_iso")
        if not candidate_id or candidate_id in seen_ids:
            raise GateFailure("A8 candidate ID missing/duplicate")
        seen_ids.add(candidate_id)
        if lda_id not in scope:
            raise GateFailure(f"A8 person is outside A5b: {lda_id}")
        if not (
            row.get("schema_id")
            == "staffer-network-a8-house-sod-1997q1-lda-match-candidate-v1"
            and row.get("candidate_status")
            == "REVIEW_REQUIRED_NAME_ONLY_CANDIDATE"
            and row.get("canonical_identity_decision") == "NOT_ADJUDICATED"
            and row.get("canonical_person_id") is None
            and row.get("canonical_employment_fact") is False
            and row.get("canonical_employment_episode_id") is None
            and row.get("interval_continuity_asserted") is False
            and row.get("period") == "1997Q1"
            and "1997-01-01" <= start <= end <= "1997-03-31"
        ):
            raise GateFailure(f"invalid A8 review candidate: {candidate_id}")
        entry = working[lda_id]
        entry["candidate_ids"].append(candidate_id)
        entry["source_ids"].add(str(row.get("source_candidate_id") or ""))
        entry["starts"].append(start)
        entry["ends"].append(end)
        entry["offices"].add(str(row.get("employing_office_raw") or ""))
        entry["titles"].add(str(row.get("title_description_raw") or ""))
        entry["classes"][str(row.get("candidate_class") or "")] += 1
        entry["ambiguities"][str(row.get("ambiguity_status") or "")] += 1
    result: dict[str, dict[str, Any]] = {}
    for lda_id, value in working.items():
        result[lda_id] = {
            "ambiguity_status_counts": dict(sorted(value["ambiguities"].items())),
            "candidate_class_counts": dict(sorted(value["classes"].items())),
            "candidate_count": len(value["candidate_ids"]),
            "candidate_id_digest": digest_values(value["candidate_ids"]),
            "distinct_employing_office_count": len(value["offices"]),
            "distinct_source_personnel_row_count": len(value["source_ids"]),
            "distinct_title_count": len(value["titles"]),
            "earliest_service_start": min(value["starts"]),
            "latest_service_end": max(value["ends"]),
            "source_candidate_id_digest": digest_values(value["source_ids"]),
        }
    return result, row_count


def evidence_combination(has_fec: bool, has_house: bool) -> str:
    if has_fec and has_house:
        return "A7_FEC_POINT+A8_HOUSE_1997Q1"
    if has_fec:
        return "A7_FEC_POINT_ONLY"
    if has_house:
        return "A8_HOUSE_1997Q1_ONLY"
    return "NO_A7_FEC_OR_A8_CANDIDATE"


def revised_priority(
    baseline_bucket: str, has_fec: bool, has_house: bool
) -> tuple[int, str, str, str]:
    baseline_rank = BUCKET_RANK[baseline_bucket]
    if has_house and baseline_rank < 3:
        return (
            3,
            P3,
            "A8_DATED_BOUNDED_FORMER_HOUSE_CANDIDATE_REQUIRES_IDENTITY_AND_CHRONOLOGY_REVIEW",
            "Adjudicate the 1997Q1 House name match with independent identity anchors, then reconcile chronology; retain all evidence as review-only.",
        )
    if has_house:
        return (
            baseline_rank,
            baseline_bucket,
            "A8_CANDIDATE_ADDED_BASELINE_ALREADY_P3",
            "Adjudicate the 1997Q1 House name match with independent identity anchors and reconcile it with existing chronology.",
        )
    if has_fec:
        return (
            baseline_rank,
            baseline_bucket,
            "A7_FEC_POINT_CONTEXT_ONLY_NO_BUCKET_CHANGE",
            "Preserve the baseline action; review the FEC employer point observation as context only because it proves neither a former position nor interval bounds.",
        )
    return (
        baseline_rank,
        baseline_bucket,
        "NO_NEW_A7_FEC_OR_A8_SCHEDULING_EVIDENCE",
        "Preserve the sealed A5b recommended action.",
    )


def build_row(
    baseline: Mapping[str, Any],
    fec: Mapping[str, Any] | None,
    house: Mapping[str, Any] | None,
    run_id: str,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    lda_id = str(baseline["lda_source_person_id"])
    baseline_bucket = str(baseline["priority_bucket"])
    baseline_rank = int(baseline["priority_rank"])
    has_fec = fec is not None
    has_house = house is not None
    revised_rank, revised_bucket, reason, next_action = revised_priority(
        baseline_bucket, has_fec, has_house
    )
    fec_summary = {
        "candidate_count": 0,
        "candidate_id_digest": digest_values([]),
        "distinct_employer_count": 0,
        "distinct_occupation_count": 0,
        "distinct_registrant_anchor_count": 0,
        "employment_interval_asserted": False,
        "first_observation_date": None,
        "former_position_asserted": False,
        "gap_clearances": [],
        "has_candidate": False,
        "last_observation_date": None,
        "scheduling_effect": "CONTEXT_ONLY_NO_PRIORITY_BUCKET_CHANGE",
    }
    if fec:
        fec_summary.update(fec)
        fec_summary["has_candidate"] = True
    house_summary = {
        "ambiguity_status_counts": {},
        "bounded_candidate_for_scheduling": False,
        "candidate_class_counts": {},
        "candidate_count": 0,
        "candidate_id_digest": digest_values([]),
        "dated_candidate_for_scheduling": False,
        "distinct_employing_office_count": 0,
        "distinct_source_personnel_row_count": 0,
        "distinct_title_count": 0,
        "earliest_service_start": None,
        "former_position_candidate_for_scheduling": False,
        "has_candidate": False,
        "identity_adjudicated": False,
        "latest_service_end": None,
        "period": None,
        "source_candidate_id_digest": digest_values([]),
    }
    if house:
        house_summary.update(house)
        house_summary.update(
            {
                "bounded_candidate_for_scheduling": True,
                "dated_candidate_for_scheduling": True,
                "former_position_candidate_for_scheduling": True,
                "has_candidate": True,
                "period": "1997Q1",
            }
        )
    sort_key = (
        revised_rank,
        baseline_rank,
        int(baseline["priority_queue_ordinal"]),
        int(baseline["sealed_queue_ordinal"]),
        lda_id,
    )
    row = {
        "a7_fec_employer_point_observations": fec_summary,
        "a8_house_1997q1_candidates": house_summary,
        "adjudication_status": "REVIEW_REQUIRED",
        "baseline_a5b": {
            "coverage_flags": dict(baseline.get("coverage_flags") or {}),
            "employment_provider_count": baseline.get("employment_provider_count"),
            "explicit_gap_codes": list(baseline.get("explicit_gap_codes") or []),
            "priority_bucket": baseline_bucket,
            "priority_queue_ordinal": baseline["priority_queue_ordinal"],
            "priority_rank": baseline_rank,
            "provider_overlap_bucket": baseline.get("provider_overlap_bucket"),
            "recommended_next_action": baseline.get("recommended_next_action"),
        },
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "complete_lifetime_employment_asserted": False,
        "display_name": baseline.get("display_name"),
        "evidence_combination": evidence_combination(has_fec, has_house),
        "lda_source_person_id": lda_id,
        "revised_priority": {
            "bucket_changed": revised_bucket != baseline_bucket,
            "priority_bucket": revised_bucket,
            "priority_rank": revised_rank,
            "reason_code": reason,
            "recommended_next_action": next_action,
            "transition": f"{baseline_bucket}->{revised_bucket}",
        },
        "run_id": run_id,
        "schema_id": ROW_SCHEMA,
        "sealed_queue_ordinal": baseline["sealed_queue_ordinal"],
        "sort_key": list(sort_key),
        "stage_id": STAGE_ID,
    }
    return sort_key, row


def write_gzip(path: Path, values: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(fd)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="\n") as text:
                    for value in values:
                        text.write(compact(value).decode("utf-8") + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def run(args: argparse.Namespace) -> dict[str, Any]:
    manifest_path = args.manifest.resolve()
    manifest = read_json(manifest_path)
    paths = bind_inputs(manifest, args.repo_root.resolve())
    validate_receipts(manifest, paths)
    expected = manifest["expected"]
    baseline_rows, baseline_by_id = load_a5b(
        paths["a5b_priority_ledger"],
        expected["a5b_people"],
        expected["a5b_bucket_counts"],
    )
    fec_by_id, fec_row_count = load_a7_fec(
        paths["a7_fec_employer_observations"], baseline_by_id
    )
    house_by_id, house_row_count = load_a8_house(
        paths["a8_house_match_candidates"], baseline_by_id
    )
    if fec_row_count != expected["a7_fec_candidate_rows"] or len(fec_by_id) != expected[
        "a7_fec_people"
    ]:
        raise GateFailure("A7 FEC observed counts differ from manifest")
    if house_row_count != expected["a8_candidate_rows"] or len(house_by_id) != expected[
        "a8_people"
    ]:
        raise GateFailure("A8 observed counts differ from manifest")

    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise GateFailure(f"output directory is nonempty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    queued = [
        build_row(
            baseline,
            fec_by_id.get(str(baseline["lda_source_person_id"])),
            house_by_id.get(str(baseline["lda_source_person_id"])),
            str(manifest["run_id"]),
        )
        for baseline in baseline_rows
    ]
    queued.sort(key=lambda item: item[0])
    output_rows: list[dict[str, Any]] = []
    for ordinal, (_, row) in enumerate(queued, start=1):
        row["revised_priority"]["priority_queue_ordinal"] = ordinal
        output_rows.append(row)

    output_path = args.output_dir / "a9_a7_a8_priority_sidecar_25340.ndjson.gz"
    receipt_path = args.output_dir / "a9_a7_a8_priority_sidecar_receipt.json"
    write_gzip(output_path, output_rows)

    revised_buckets: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    combinations: Counter[str] = Counter()
    baseline_by_evidence: defaultdict[str, Counter[str]] = defaultdict(Counter)
    changed_people = 0
    for row in output_rows:
        revised = row["revised_priority"]
        baseline_bucket = row["baseline_a5b"]["priority_bucket"]
        combination = row["evidence_combination"]
        revised_buckets[revised["priority_bucket"]] += 1
        transitions[revised["transition"]] += 1
        combinations[combination] += 1
        baseline_by_evidence[baseline_bucket][combination] += 1
        changed_people += int(revised["bucket_changed"])

    input_bindings = {
        label: {
            "bytes": manifest["inputs"][label]["bytes"],
            "path": manifest["inputs"][label]["path"],
            "sha256": manifest["inputs"][label]["sha256"],
        }
        for label in sorted(manifest["inputs"])
    }
    result = {
        "baseline_bucket_by_evidence_combination": {
            bucket: dict(sorted(counts.items()))
            for bucket, counts in sorted(baseline_by_evidence.items())
        },
        "baseline_bucket_counts": dict(sorted(expected["a5b_bucket_counts"].items())),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "counts": {
            "a7_fec_candidate_rows": fec_row_count,
            "a7_fec_people": len(fec_by_id),
            "a7_fec_people_with_bucket_change": sum(
                lda_id in house_by_id for lda_id in fec_by_id
            ),
            "a8_candidate_rows": house_row_count,
            "a8_people": len(house_by_id),
            "a8_people_already_p3": sum(
                baseline_by_id[lda_id]["priority_bucket"] == P3 for lda_id in house_by_id
            ),
            "a8_people_causing_bucket_change": changed_people,
            "output_people": len(output_rows),
            "provider_person_overlap": len(set(fec_by_id) & set(house_by_id)),
            "unchanged_bucket_people": len(output_rows) - changed_people,
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": [
                "revised_priority_rank",
                "baseline_priority_rank",
                "baseline_priority_queue_ordinal",
                "sealed_queue_ordinal",
                "lda_source_person_id",
            ],
        },
        "evidence_combination_counts": dict(sorted(combinations.items())),
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha(Path(__file__).resolve()),
        },
        "input_bindings": input_bindings,
        "manifest": {
            "bytes": manifest_path.stat().st_size,
            "path": str(manifest_path),
            "sha256": sha(manifest_path),
        },
        "output": {
            "bytes": output_path.stat().st_size,
            "path": output_path.name,
            "rows": len(output_rows),
            "sha256": sha(output_path),
            "unique_lda_source_person_ids": len(
                {row["lda_source_person_id"] for row in output_rows}
            ),
        },
        "policy": {
            "a7_fec_bucket_effect": "NONE_POINT_OBSERVATION_IS_NOT_A_FORMER_POSITION_OR_BOUNDED_INTERVAL",
            "a7_ld203_affiliation_as_employment": "PROHIBITED_AND_NOT_CONSUMED",
            "a8_bucket_effect": "P0_P1_P2_TO_P3_FOR_IDENTITY_AND_CHRONOLOGY_REVIEW",
            "immutable_baseline": True,
            "review_only": True,
        },
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "revised_bucket_counts": dict(sorted(revised_buckets.items())),
        "schema_id": RECEIPT_SCHEMA,
        "stage_id": STAGE_ID,
        "status": "PASS",
        "transition_counts": dict(sorted(transitions.items())),
    }
    receipt_path.write_bytes(canonical_line(result))
    return {
        "receipt": result,
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha(receipt_path),
    }


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    args.output_dir = args.output_dir.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
