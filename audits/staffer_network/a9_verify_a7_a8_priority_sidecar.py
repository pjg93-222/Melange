#!/usr/bin/env python3
"""Independently verify the A9 A7/A8 immutable priority sidecar."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator, Mapping


SCHEMA_ID = "staffer-network-a9-a7-a8-priority-sidecar-independent-verification-v1"
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
TOKEN_PATTERN = re.compile(
    rb"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret)[\"']?\s*[:=]\s*[\"'][^\"']+[\"']"
)


class VerificationFailure(RuntimeError):
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


def load_json(path: Path) -> dict[str, Any]:
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


def resolve(repo_root: Path, entry: Mapping[str, Any]) -> Path:
    path = Path(str(entry["path"]))
    return (path if path.is_absolute() else repo_root / path).resolve()


def independent_fec_summary(path: Path) -> tuple[dict[str, dict[str, Any]], int, int]:
    grouped: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "ids": [],
            "dates": [],
            "employers": set(),
            "occupations": set(),
            "registrants": set(),
        }
    )
    failures = 0
    count = 0
    ids: set[str] = set()
    for row in rows(path):
        count += 1
        candidate_id = str(row.get("candidate_id") or "")
        if not candidate_id or candidate_id in ids:
            failures += 1
        ids.add(candidate_id)
        if not (
            row.get("schema_id")
            == "staffer-network-a7-fec-employment-observation-candidate-v1"
            and row.get("candidate_kind")
            == "FEC_REPORTED_EMPLOYER_OCCUPATION_POINT_OBSERVATION"
            and row.get("identity_anchor_count") == 3
            and row.get("identity_status") == "REVIEW_REQUIRED"
            and row.get("review_disposition") == "REVIEW_REQUIRED"
            and row.get("employment_interval_asserted") is False
            and row.get("canonical_identity_promoted") is False
            and row.get("canonical_employment_promoted") is False
            and row.get("complete_history_asserted") is False
        ):
            failures += 1
        lda_id = str(row.get("lda_source_person_id") or "")
        item = grouped[lda_id]
        item["ids"].append(candidate_id)
        item["dates"].append(str(row.get("observation_date") or ""))
        item["employers"].add(str(row.get("source_employer_key") or ""))
        occupation = str(row.get("raw_occupation") or "").strip()
        if occupation:
            item["occupations"].add(occupation)
        for anchor in row.get("lda_registrant_anchors") or []:
            registrant = str(anchor.get("lda_registrant_id") or "")
            if registrant:
                item["registrants"].add(registrant)
    summaries = {
        lda_id: {
            "candidate_count": len(value["ids"]),
            "candidate_id_digest": digest_values(value["ids"]),
            "distinct_employer_count": len(value["employers"]),
            "distinct_occupation_count": len(value["occupations"]),
            "distinct_registrant_anchor_count": len(value["registrants"]),
            "first_observation_date": min(value["dates"]),
            "last_observation_date": max(value["dates"]),
        }
        for lda_id, value in grouped.items()
    }
    return summaries, count, failures


def independent_house_summary(path: Path) -> tuple[dict[str, dict[str, Any]], int, int]:
    grouped: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "ambiguities": Counter(),
            "classes": Counter(),
            "ends": [],
            "ids": [],
            "offices": set(),
            "source_ids": set(),
            "starts": [],
            "titles": set(),
        }
    )
    failures = 0
    count = 0
    ids: set[str] = set()
    for row in rows(path):
        count += 1
        candidate_id = str(row.get("candidate_match_id") or "")
        start = row.get("service_start_date_candidate_iso")
        end = row.get("service_end_date_candidate_iso")
        if not candidate_id or candidate_id in ids:
            failures += 1
        ids.add(candidate_id)
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
            failures += 1
        lda_id = str(row.get("lda_source_person_id") or "")
        item = grouped[lda_id]
        item["ids"].append(candidate_id)
        item["source_ids"].add(str(row.get("source_candidate_id") or ""))
        item["starts"].append(start)
        item["ends"].append(end)
        item["offices"].add(str(row.get("employing_office_raw") or ""))
        item["titles"].add(str(row.get("title_description_raw") or ""))
        item["classes"][str(row.get("candidate_class") or "")] += 1
        item["ambiguities"][str(row.get("ambiguity_status") or "")] += 1
    summaries = {
        lda_id: {
            "ambiguity_status_counts": dict(sorted(value["ambiguities"].items())),
            "candidate_class_counts": dict(sorted(value["classes"].items())),
            "candidate_count": len(value["ids"]),
            "candidate_id_digest": digest_values(value["ids"]),
            "distinct_employing_office_count": len(value["offices"]),
            "distinct_source_personnel_row_count": len(value["source_ids"]),
            "distinct_title_count": len(value["titles"]),
            "earliest_service_start": min(value["starts"]),
            "latest_service_end": max(value["ends"]),
            "source_candidate_id_digest": digest_values(value["source_ids"]),
        }
        for lda_id, value in grouped.items()
    }
    return summaries, count, failures


def expected_fec(value: Mapping[str, Any] | None) -> dict[str, Any]:
    result = {
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
    if value:
        result.update(value)
        result["has_candidate"] = True
    return result


def expected_house(value: Mapping[str, Any] | None) -> dict[str, Any]:
    result = {
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
    if value:
        result.update(value)
        result.update(
            {
                "bounded_candidate_for_scheduling": True,
                "dated_candidate_for_scheduling": True,
                "former_position_candidate_for_scheduling": True,
                "has_candidate": True,
                "period": "1997Q1",
            }
        )
    return result


def expected_combination(has_fec: bool, has_house: bool) -> str:
    if has_fec and has_house:
        return "A7_FEC_POINT+A8_HOUSE_1997Q1"
    if has_fec:
        return "A7_FEC_POINT_ONLY"
    if has_house:
        return "A8_HOUSE_1997Q1_ONLY"
    return "NO_A7_FEC_OR_A8_CANDIDATE"


def expected_priority(
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


def token_matches_in_json_lines(path: Path) -> tuple[int, int]:
    matches = 0
    documents = 0
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    documents += 1
                    matches += len(TOKEN_PATTERN.findall(line.encode("utf-8")))
    else:
        documents = 1
        matches = len(TOKEN_PATTERN.findall(path.read_bytes()))
    return matches, documents


def verify(args: argparse.Namespace) -> dict[str, Any]:
    manifest = load_json(args.manifest)
    repo_root = args.repo_root.resolve()
    payload_name = "a9_a7_a8_priority_sidecar_25340.ndjson.gz"
    receipt_name = "a9_a7_a8_priority_sidecar_receipt.json"
    primary_payload = (args.primary / payload_name).resolve(strict=True)
    twin_payload = (args.twin / payload_name).resolve(strict=True)
    primary_receipt_path = (args.primary / receipt_name).resolve(strict=True)
    twin_receipt_path = (args.twin / receipt_name).resolve(strict=True)
    primary_receipt = load_json(primary_receipt_path)
    twin_receipt = load_json(twin_receipt_path)
    assertions: dict[str, bool] = {
        "manifest_schema_valid": manifest.get("schema_id") == MANIFEST_SCHEMA,
        "stage_id_exact": manifest.get("stage_id") == STAGE_ID,
        "payload_bytes_equal": primary_payload.read_bytes() == twin_payload.read_bytes(),
        "payload_hash_equal": sha(primary_payload) == sha(twin_payload),
        "receipt_bytes_equal": primary_receipt_path.read_bytes()
        == twin_receipt_path.read_bytes(),
        "receipt_hash_equal": sha(primary_receipt_path) == sha(twin_receipt_path),
        "receipt_schema_valid": primary_receipt.get("schema_id") == RECEIPT_SCHEMA,
        "receipts_pass": primary_receipt.get("status")
        == twin_receipt.get("status")
        == "PASS",
        "receipt_binds_payload": primary_receipt.get("output", {}).get("sha256")
        == sha(primary_payload),
        "receipt_binds_manifest": primary_receipt.get("manifest", {}).get("sha256")
        == sha(args.manifest),
        "gzip_mtime_zero": primary_payload.read_bytes()[4:8] == b"\x00\x00\x00\x00",
    }

    input_paths: dict[str, Path] = {}
    input_binding_failures = 0
    for label, entry in manifest.get("inputs", {}).items():
        path = resolve(repo_root, entry)
        input_paths[label] = path
        receipt_entry = primary_receipt.get("input_bindings", {}).get(label, {})
        if not (
            path.is_file()
            and path.stat().st_size == entry.get("bytes") == receipt_entry.get("bytes")
            and sha(path) == entry.get("sha256") == receipt_entry.get("sha256")
            and receipt_entry.get("path") == entry.get("path")
        ):
            input_binding_failures += 1
    assertions["all_manifest_inputs_hash_bound"] = input_binding_failures == 0
    assertions["ld203_candidate_ledger_not_an_input"] = all(
        "ld203" not in label.lower() for label in manifest.get("inputs", {})
    )

    baseline_rows = list(rows(input_paths["a5b_priority_ledger"]))
    baseline = {str(row["lda_source_person_id"]): row for row in baseline_rows}
    fec, fec_row_count, fec_source_failures = independent_fec_summary(
        input_paths["a7_fec_employer_observations"]
    )
    house, house_row_count, house_source_failures = independent_house_summary(
        input_paths["a8_house_match_candidates"]
    )
    expected = manifest["expected"]
    assertions.update(
        {
            "baseline_scope_exact": len(baseline_rows)
            == len(baseline)
            == expected["a5b_people"]
            == 25340,
            "a7_fec_source_semantics_valid": fec_source_failures == 0,
            "a7_fec_counts_exact": fec_row_count == expected["a7_fec_candidate_rows"]
            and len(fec) == expected["a7_fec_people"],
            "a8_source_semantics_valid": house_source_failures == 0,
            "a8_counts_exact": house_row_count == expected["a8_candidate_rows"]
            and len(house) == expected["a8_people"],
            "provider_person_overlap_exact": len(set(fec) & set(house)) == 0,
            "all_candidate_people_in_baseline": set(fec) | set(house) <= set(baseline),
        }
    )

    output_rows = list(rows(primary_payload))
    row_failures: Counter[str] = Counter()
    output_ids: set[str] = set()
    previous_sort_key: tuple[Any, ...] | None = None
    revised_buckets: Counter[str] = Counter()
    transitions: Counter[str] = Counter()
    combinations: Counter[str] = Counter()
    baseline_by_evidence: defaultdict[str, Counter[str]] = defaultdict(Counter)
    changed_people = 0
    a7_people_with_changed_row = 0
    a8_already_p3 = 0
    payload_ld203_mentions = 0

    for ordinal, row in enumerate(output_rows, start=1):
        lda_id = str(row.get("lda_source_person_id") or "")
        if lda_id in output_ids:
            row_failures["DUPLICATE_ID"] += 1
        output_ids.add(lda_id)
        source = baseline.get(lda_id)
        if source is None:
            row_failures["OUT_OF_SCOPE_ID"] += 1
            continue
        fec_source = fec.get(lda_id)
        house_source = house.get(lda_id)
        has_fec = fec_source is not None
        has_house = house_source is not None
        baseline_bucket = str(source["priority_bucket"])
        baseline_rank = int(source["priority_rank"])
        revised_rank, revised_bucket, reason, action = expected_priority(
            baseline_bucket, has_fec, has_house
        )
        combination = expected_combination(has_fec, has_house)
        expected_baseline = {
            "coverage_flags": dict(source.get("coverage_flags") or {}),
            "employment_provider_count": source.get("employment_provider_count"),
            "explicit_gap_codes": list(source.get("explicit_gap_codes") or []),
            "priority_bucket": baseline_bucket,
            "priority_queue_ordinal": source["priority_queue_ordinal"],
            "priority_rank": baseline_rank,
            "provider_overlap_bucket": source.get("provider_overlap_bucket"),
            "recommended_next_action": source.get("recommended_next_action"),
        }
        expected_sort_key = (
            revised_rank,
            baseline_rank,
            int(source["priority_queue_ordinal"]),
            int(source["sealed_queue_ordinal"]),
            lda_id,
        )
        expected_revised = {
            "bucket_changed": revised_bucket != baseline_bucket,
            "priority_bucket": revised_bucket,
            "priority_queue_ordinal": ordinal,
            "priority_rank": revised_rank,
            "reason_code": reason,
            "recommended_next_action": action,
            "transition": f"{baseline_bucket}->{revised_bucket}",
        }
        checks = {
            "SCHEMA": row.get("schema_id") == ROW_SCHEMA,
            "STAGE_RUN": row.get("stage_id") == STAGE_ID
            and row.get("run_id") == manifest.get("run_id"),
            "DISPLAY_AND_SEAL": row.get("display_name") == source.get("display_name")
            and row.get("sealed_queue_ordinal") == source.get("sealed_queue_ordinal"),
            "BASELINE_SNAPSHOT": row.get("baseline_a5b") == expected_baseline,
            "FEC_SUMMARY": row.get("a7_fec_employer_point_observations")
            == expected_fec(fec_source),
            "HOUSE_SUMMARY": row.get("a8_house_1997q1_candidates")
            == expected_house(house_source),
            "COMBINATION": row.get("evidence_combination") == combination,
            "REVISED_PRIORITY": row.get("revised_priority") == expected_revised,
            "SORT_KEY": tuple(row.get("sort_key") or []) == expected_sort_key,
            "ZERO_PROMOTION": row.get("adjudication_status") == "REVIEW_REQUIRED"
            and row.get("canonical_identity_promoted") is False
            and row.get("canonical_employment_promoted") is False
            and row.get("complete_lifetime_employment_asserted") is False,
        }
        for label, passed in checks.items():
            if not passed:
                row_failures[label] += 1
        if previous_sort_key is not None and expected_sort_key < previous_sort_key:
            row_failures["SORT_ORDER"] += 1
        previous_sort_key = expected_sort_key
        payload_ld203_mentions += int(b"ld203" in compact(row).lower())
        revised_buckets[revised_bucket] += 1
        transition = f"{baseline_bucket}->{revised_bucket}"
        transitions[transition] += 1
        combinations[combination] += 1
        baseline_by_evidence[baseline_bucket][combination] += 1
        changed = revised_bucket != baseline_bucket
        changed_people += int(changed)
        a7_people_with_changed_row += int(has_fec and changed)
        a8_already_p3 += int(has_house and baseline_bucket == P3)

    expected_baseline_by_evidence = {
        bucket: dict(sorted(value.items()))
        for bucket, value in sorted(baseline_by_evidence.items())
    }
    expected_counts = {
        "a7_fec_candidate_rows": fec_row_count,
        "a7_fec_people": len(fec),
        "a7_fec_people_with_bucket_change": a7_people_with_changed_row,
        "a8_candidate_rows": house_row_count,
        "a8_people": len(house),
        "a8_people_already_p3": a8_already_p3,
        "a8_people_causing_bucket_change": changed_people,
        "output_people": len(output_rows),
        "provider_person_overlap": len(set(fec) & set(house)),
        "unchanged_bucket_people": len(output_rows) - changed_people,
    }
    assertions.update(
        {
            "exact_25340_id_scope": len(output_rows)
            == len(output_ids)
            == len(baseline)
            == 25340,
            "output_ids_equal_baseline": output_ids == set(baseline),
            "all_rows_independently_reconstructed": not row_failures,
            "payload_has_zero_ld203_mentions": payload_ld203_mentions == 0,
            "receipt_counts_exact": primary_receipt.get("counts") == expected_counts,
            "receipt_revised_buckets_exact": primary_receipt.get(
                "revised_bucket_counts"
            )
            == dict(sorted(revised_buckets.items())),
            "receipt_transitions_exact": primary_receipt.get("transition_counts")
            == dict(sorted(transitions.items())),
            "receipt_combinations_exact": primary_receipt.get(
                "evidence_combination_counts"
            )
            == dict(sorted(combinations.items())),
            "receipt_baseline_evidence_cross_tab_exact": primary_receipt.get(
                "baseline_bucket_by_evidence_combination"
            )
            == expected_baseline_by_evidence,
            "fec_never_changes_bucket": all(
                expected_priority(str(baseline[lda_id]["priority_bucket"]), True, False)[1]
                == baseline[lda_id]["priority_bucket"]
                for lda_id in fec
            ),
            "receipt_policy_is_conservative": primary_receipt.get("policy", {}).get(
                "a7_fec_bucket_effect"
            )
            == "NONE_POINT_OBSERVATION_IS_NOT_A_FORMER_POSITION_OR_BOUNDED_INTERVAL"
            and primary_receipt.get("policy", {}).get(
                "a7_ld203_affiliation_as_employment"
            )
            == "PROHIBITED_AND_NOT_CONSUMED",
            "receipt_zero_promotions": primary_receipt.get(
                "canonical_identity_promotions"
            )
            == 0
            and primary_receipt.get("canonical_employment_promotions") == 0
            and primary_receipt.get("complete_lifetime_employment_assertions") == 0,
        }
    )

    token_matches = 0
    token_documents = 0
    for path in (
        primary_payload,
        twin_payload,
        primary_receipt_path,
        twin_receipt_path,
        args.manifest,
    ):
        matches, documents = token_matches_in_json_lines(path)
        token_matches += matches
        token_documents += documents
    assertions["token_negative_structured_artifact_scan"] = token_matches == 0
    failures = sorted(label for label, passed in assertions.items() if not passed)
    result = {
        "assertions": dict(sorted(assertions.items())),
        "baseline_bucket_by_evidence_combination": expected_baseline_by_evidence,
        "counts": {
            **expected_counts,
            "fec_source_semantic_failures": fec_source_failures,
            "house_source_semantic_failures": house_source_failures,
            "input_binding_failures": input_binding_failures,
            "payload_ld203_mentions": payload_ld203_mentions,
            "row_failure_count": sum(row_failures.values()),
        },
        "evidence_combination_counts": dict(sorted(combinations.items())),
        "failure_codes": failures,
        "hashes": {
            "manifest_sha256": sha(args.manifest),
            "primary_payload_sha256": sha(primary_payload),
            "primary_receipt_sha256": sha(primary_receipt_path),
            "twin_payload_sha256": sha(twin_payload),
            "twin_receipt_sha256": sha(twin_receipt_path),
            "verifier_implementation_sha256": sha(Path(__file__).resolve()),
        },
        "policy": {
            "a7_fec_bucket_effect": "NONE_POINT_OBSERVATION_CONTEXT_ONLY",
            "a7_ld203_consumed_as_employment": False,
            "a8_bucket_effect": "P0_P1_P2_TO_P3_IDENTITY_AND_CHRONOLOGY_REVIEW",
            "review_only": True,
            "zero_promotions": True,
        },
        "revised_bucket_counts": dict(sorted(revised_buckets.items())),
        "row_failure_counts": dict(sorted(row_failures.items())),
        "schema_id": SCHEMA_ID,
        "stage_id": STAGE_ID,
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {
            "matches": token_matches,
            "structured_documents_scanned": token_documents,
        },
        "transition_counts": dict(sorted(transitions.items())),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_line(result))
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--twin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    args.manifest = args.manifest.resolve()
    args.primary = args.primary.resolve()
    args.twin = args.twin.resolve()
    args.output = args.output.resolve()
    return args


def main(argv: Iterable[str] | None = None) -> int:
    result = verify(parse_args(argv))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
