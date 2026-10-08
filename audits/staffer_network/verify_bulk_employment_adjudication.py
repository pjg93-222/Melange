#!/usr/bin/env python3
"""Independently verify twin bulk employment-adjudication generations."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterator

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT / "fec") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "fec"))
from staffer_network.schema_validation import validate_instance, validate_schema_definition


PAYLOADS = (
    "candidate_adjudication_decisions.ndjson.gz",
    "provisional_employment_episodes.ndjson.gz",
    "employment_adjudication_person_summary_25340.ndjson.gz",
    "covered_position_parser_gold_sample_100.ndjson.gz",
    "identity_rule_gold_sample_200.ndjson.gz",
)
SCHEMA_DIRECTORY = PROJECT_ROOT / "fec" / "staffer_network" / "schemas"
SCHEMA_FILES = {
    "staffer-network-employment-candidate-adjudication-v2": "employment_candidate_adjudication_v2.schema.json",
    "staffer-network-provisional-employment-episode-v2": "provisional_employment_episode_v2.schema.json",
    "staffer-network-employment-adjudication-person-summary-v1": "employment_adjudication_person_summary.schema.json",
    "staffer-network-employment-adjudication-gold-sample-v2": "employment_adjudication_gold_sample_v2.schema.json",
    "staffer-network-employment-adjudication-receipt-v2": "employment_adjudication_receipt_v2.schema.json",
}
OPEN_GATES = {
    "COVERED_POSITION_PARSER_PRECISION_GOLD_100_REQUIRED",
    "IDENTITY_PRECISION_RECALL_GOLD_200_REQUIRED",
    "CONTAINER_ADJUDICATION_REQUIRED",
    "SENATE_TEMPORAL_OBSERVATION_AUDIT_REQUIRED",
    "FABLE_OPUS_5_ADVERSARIAL_PASS_REQUIRED",
}
IDENTITY_STRATA = {
    ("house_payroll_corroborated", "PROVISIONALLY_ACCEPTED"): 60,
    ("senate_payroll_corroborated", "PROVISIONALLY_ACCEPTED"): 30,
    ("structured_public_profile_episode", "PROVISIONALLY_ACCEPTED"): 10,
    ("house_payroll_corroborated", "REVIEW_REQUIRED"): 60,
    ("senate_payroll_corroborated", "REVIEW_REQUIRED"): 30,
    ("structured_public_profile_episode", "REVIEW_REQUIRED"): 10,
}
VERIFICATION_SCHEMA_ID = (
    "staffer-network-employment-adjudication-independent-verification-v3"
)
VERIFICATION_SCHEMA_PATH = (
    SCHEMA_DIRECTORY / "employment_adjudication_verification_receipt_v3.schema.json"
)
VERIFIER_METHOD_VERSION = "bulk-employment-adjudication-independent-verifier-v4"
TOKEN_PATTERN = re.compile(
    rb"(?i)(?:[\"'])?(?:password|passwd|api[_-]?key|access[_-]?token|secret)"
    rb"(?:[\"'])?\s*[:=]\s*[\"'][^\"']+[\"']"
)
WORD = re.compile(r"[a-z0-9]+")
STOP = {
    "a", "an", "and", "at", "for", "from", "in", "of", "on", "the", "to",
    "u", "s", "us", "office", "staff", "sen", "senator", "rep",
    "representative", "committee",
}


class VerificationError(RuntimeError):
    pass


def compact(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def digest(value: Any) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def tokens(value: Any) -> set[str]:
    return {
        token for token in WORD.findall(str(value or "").lower())
        if len(token) > 1 and token not in STOP
    }


def similarity(left: Any, right: Any) -> float:
    left_tokens, right_tokens = tokens(left), tokens(right)
    return (
        len(left_tokens & right_tokens) / len(left_tokens | right_tokens)
        if left_tokens and right_tokens else 0.0
    )


def decision_core(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: row[key]
        for key in (
            "lane", "candidate_id", "lda_source_person_id", "display_name",
            "decision", "reviewer_kind", "reviewer_id", "rationale_codes",
            "evidence_digest", "source_urls", "proposed_episode_id",
            "method_version",
        )
    }


def scan_plaintext(path: Path) -> int:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rb") as stream:
            return sum(len(TOKEN_PATTERN.findall(line)) for line in stream)
    with path.open("rb") as stream:
        return sum(len(TOKEN_PATTERN.findall(line)) for line in stream)


def rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationError(f"object required at {path}:{line_number}")
            yield value


def verify(primary: Path, twin: Path, output_root: Path) -> dict[str, Any]:
    schemas = {
        schema_id: json.loads((SCHEMA_DIRECTORY / filename).read_text(encoding="utf-8"))
        for schema_id, filename in SCHEMA_FILES.items()
    }
    for schema in schemas.values():
        validate_schema_definition(schema)
    verification_schema = json.loads(VERIFICATION_SCHEMA_PATH.read_text(encoding="utf-8"))
    validate_schema_definition(verification_schema)
    primary_receipt_path = (primary / "employment_adjudication_receipt.json").resolve(strict=True)
    twin_receipt_path = (twin / "employment_adjudication_receipt.json").resolve(strict=True)
    primary_receipt = json.loads(primary_receipt_path.read_text(encoding="utf-8"))
    twin_receipt = json.loads(twin_receipt_path.read_text(encoding="utf-8"))
    validate_instance(
        primary_receipt,
        schemas["staffer-network-employment-adjudication-receipt-v2"],
        _schema_checked=True,
    )
    validate_instance(
        twin_receipt,
        schemas["staffer-network-employment-adjudication-receipt-v2"],
        _schema_checked=True,
    )
    primary_implementation = primary_receipt["implementation"]
    twin_implementation = twin_receipt["implementation"]
    generator_path = Path(primary_implementation["generator_path"])
    assertions: dict[str, bool] = {
        "receipt_bytes_equal": primary_receipt_path.read_bytes() == twin_receipt_path.read_bytes(),
        "receipt_status_generation_valid_review_open": primary_receipt.get("status")
        == twin_receipt.get("status") == "GENERATION_VALID_REVIEW_OPEN",
        "sealed_scope_exact": primary_receipt.get("sealed_scope_people") == 25340,
        "canonical_promotions_zero": primary_receipt.get("canonical_employment_promotions") == 0,
        "lifetime_assertions_zero": primary_receipt.get("complete_lifetime_employment_assertions") == 0,
        "primary_temporal_eligible_zero": primary_receipt.get("primary_temporal_eligible_episodes") == 0,
        "required_review_gates_open": set(primary_receipt.get("open_gates") or [])
        == OPEN_GATES,
        "gate_states_exact": primary_receipt.get("gate_states")
        == {code: "OPEN" for code in sorted(OPEN_GATES)},
        "generator_implementation_receipts_equal": primary_implementation
        == twin_implementation,
        "generator_implementation_hash_bound": generator_path.is_file()
        and primary_implementation.get("generator_sha256") == sha256(generator_path),
    }
    for name in PAYLOADS:
        left, right = primary / name, twin / name
        assertions[f"payload_bytes_equal:{name}"] = left.read_bytes() == right.read_bytes()
        assertions[f"payload_hash_equal:{name}"] = sha256(left) == sha256(right)

    receipt_files = {entry["path"]: entry for entry in primary_receipt.get("files") or []}
    assertions["receipt_lists_all_payloads"] = set(receipt_files) == set(PAYLOADS)
    for name in PAYLOADS:
        entry = receipt_files.get(name) or {}
        assertions[f"receipt_binds_hash:{name}"] = entry.get("sha256") == sha256(primary / name)
        assertions[f"receipt_binds_bytes:{name}"] = entry.get("bytes") == (primary / name).stat().st_size
        assertions[f"receipt_binds_schema:{name}"] = (
            entry.get("schema_id") in schemas
            and entry.get("schema_sha256")
            == sha256(SCHEMA_DIRECTORY / SCHEMA_FILES[entry["schema_id"]])
        )

    receipt_schemas = {
        entry.get("schema_id"): entry for entry in primary_receipt.get("schemas") or []
    }
    assertions["all_output_schemas_registered_and_bound"] = set(receipt_schemas) == set(schemas)
    for schema_id, filename in SCHEMA_FILES.items():
        entry = receipt_schemas.get(schema_id) or {}
        path = SCHEMA_DIRECTORY / filename
        assertions[f"schema_hash_bound:{schema_id}"] = (
            entry.get("path") == str(path)
            and entry.get("sha256") == sha256(path)
        )

    input_hashes_ok = True
    for entry in (primary_receipt.get("inputs") or {}).values():
        path = Path(entry["path"])
        input_hashes_ok &= path.is_file() and entry.get("bytes") == path.stat().st_size
        input_hashes_ok &= path.is_file() and entry.get("sha256") == sha256(path)
    assertions["input_hashes_bound"] = input_hashes_ok

    house_source_rows = {
        str(row["candidate_match_id"]): row
        for row in rows(Path(primary_receipt["inputs"]["house_payroll"]["path"]))
    }
    senate_source_rows = {
        str(row["match_candidate_id"]): row
        for row in rows(Path(primary_receipt["inputs"]["senate_payroll"]["path"]))
    }
    house_people_by_payroll: defaultdict[str, set[str]] = defaultdict(set)
    for row in house_source_rows.values():
        house_people_by_payroll[str(row.get("payroll_candidate_id"))].add(
            str(row.get("lda_source_person_id"))
        )

    decisions_path = primary / "candidate_adjudication_decisions.ndjson.gz"
    decisions: dict[str, dict[str, Any]] = {}
    candidate_keys: set[tuple[str, str]] = set()
    status_counts: Counter[str] = Counter()
    lane_counts: defaultdict[str, Counter[str]] = defaultdict(Counter)
    decision_failures: Counter[str] = Counter()
    for row in rows(decisions_path):
        try:
            validate_instance(
                row,
                schemas["staffer-network-employment-candidate-adjudication-v2"],
                _schema_checked=True,
            )
        except Exception:
            decision_failures["schema_validation"] += 1
        decision_id = str(row.get("decision_id") or "")
        if not decision_id or decision_id in decisions:
            decision_failures["duplicate_or_blank_decision_id"] += 1
        decisions[decision_id] = row
        candidate_key = (str(row.get("lane") or ""), str(row.get("candidate_id") or ""))
        if candidate_key in candidate_keys:
            decision_failures["duplicate_lane_candidate"] += 1
        candidate_keys.add(candidate_key)
        try:
            payload_sha256 = digest(decision_core(row))
        except KeyError:
            payload_sha256 = ""
        if row.get("decision_payload_sha256") != payload_sha256:
            decision_failures["decision_payload_digest"] += 1
        if row.get("decision_id") != "adjudication:decision:" + payload_sha256:
            decision_failures["decision_id_content_binding"] += 1
        status_counts[str(row.get("decision"))] += 1
        lane_counts[str(row.get("lane"))][str(row.get("decision"))] += 1
        if row.get("canonical_eligible") is not False:
            decision_failures["canonical_eligible"] += 1
        if row.get("canonical_employment_promoted") is not False:
            decision_failures["canonical_promotion"] += 1
        if row.get("complete_lifetime_employment_asserted") is not False:
            decision_failures["lifetime_assertion"] += 1
    assertions["decision_rows_exact"] = len(decisions) == primary_receipt.get("decision_rows")
    assertions["decision_status_counts_exact"] = dict(sorted(status_counts.items())) == primary_receipt.get(
        "decision_status_counts"
    )
    assertions["lane_status_counts_exact"] = {
        lane: dict(sorted(counts.items())) for lane, counts in sorted(lane_counts.items())
    } == primary_receipt.get("lane_status_counts")
    assertions["all_decisions_closed_to_canonical"] = not decision_failures

    episodes_path = primary / "provisional_employment_episodes.ndjson.gz"
    episodes: dict[str, dict[str, Any]] = {}
    episode_failures: Counter[str] = Counter()
    provisional_lane_counts: Counter[str] = Counter()
    temporal_semantics_counts: Counter[str] = Counter()
    for row in rows(episodes_path):
        try:
            validate_instance(
                row,
                schemas["staffer-network-provisional-employment-episode-v2"],
                _schema_checked=True,
            )
        except Exception:
            episode_failures["schema_validation"] += 1
        episode_id = str(row.get("episode_id") or "")
        if not episode_id or episode_id in episodes:
            episode_failures["duplicate_or_blank_episode_id"] += 1
        episodes[episode_id] = row
        provisional_lane_counts.update(row.get("evidence_lanes") or [])
        temporal_semantics_counts[str(row.get("temporal_semantics") or "")] += 1
        linked_candidate_ids: set[str] = set()
        for linked_decision_id in row.get("decision_ids") or []:
            decision = decisions.get(str(linked_decision_id))
            if (
                decision is None
                or decision.get("decision") != "PROVISIONALLY_ACCEPTED"
                or decision.get("proposed_episode_id") != episode_id
                or decision.get("lda_source_person_id") != row.get("lda_source_person_id")
                or decision.get("lane") not in (row.get("evidence_lanes") or [])
            ):
                episode_failures["decision_episode_reciprocity"] += 1
            else:
                linked_candidate_ids.add(str(decision["candidate_id"]))
        if set(row.get("source_candidate_ids") or []) != linked_candidate_ids:
            episode_failures["source_candidate_decision_set"] += 1
        if row.get("canonical_eligible") is not False:
            episode_failures["canonical_eligible"] += 1
        if row.get("temporal_weight_eligible") is not False:
            episode_failures["temporal_weight_eligible"] += 1
        if row.get("container_status") != "LITERAL_REVIEW_REQUIRED":
            episode_failures["container_gate"] += 1
        try:
            start_earliest = date.fromisoformat(str(row["valid_start_earliest"]))
            start_latest = date.fromisoformat(str(row["valid_start_latest"]))
            end_earliest = date.fromisoformat(str(row["valid_end_earliest"]))
            end_latest = date.fromisoformat(str(row["valid_end_latest"]))
            source_as_of = date.fromisoformat(str(row["source_as_of"]))
        except (KeyError, TypeError, ValueError):
            episode_failures["interval_parse"] += 1
        else:
            if not (
                start_earliest <= start_latest
                and end_earliest <= end_latest
                and start_earliest < end_latest
            ):
                episode_failures["interval_quartet_order"] += 1
            if end_latest > source_as_of + timedelta(days=1):
                episode_failures["interval_exceeds_source_as_of"] += 1
        support_ids = sorted(set(row.get("support_candidate_ids") or []))
        if row.get("support_digest") != digest(support_ids):
            episode_failures["support_digest"] += 1
        if not set(row.get("source_candidate_ids") or []) <= set(support_ids):
            episode_failures["source_support_subset"] += 1
        semantics = row.get("temporal_semantics")
        observed = row.get("observation_intervals") or []
        if semantics == "OBSERVATION_ONLY":
            if len(observed) != 1:
                episode_failures["observation_component_count"] += 1
            for interval in observed:
                try:
                    observed_start = date.fromisoformat(str(interval["start"]))
                    observed_end = date.fromisoformat(str(interval["end_exclusive"]))
                except (KeyError, TypeError, ValueError):
                    episode_failures["observation_interval_parse"] += 1
                    continue
                if observed_start >= observed_end:
                    episode_failures["observation_interval_order"] += 1
                if interval.get("basis") == "COMPLEX_QUALIFIER_REVIEW_REQUIRED":
                    episode_failures["review_marked_observation_promoted"] += 1
                if (
                    interval.get("start") != row.get("valid_start_earliest")
                    or interval.get("end_exclusive") != row.get("valid_end_latest")
                ):
                    episode_failures["observation_envelope_mismatch"] += 1
            lane = (row.get("evidence_lanes") or [None])[0]
            for candidate_id in row.get("source_candidate_ids") or []:
                if lane == "house_payroll_corroborated":
                    source = house_source_rows.get(str(candidate_id))
                    try:
                        expected_start = str(source["service_start_date_candidate_iso"])
                        expected_end = (
                            date.fromisoformat(str(source["service_end_date_candidate_iso"]))
                            + timedelta(days=1)
                        ).isoformat()
                    except (KeyError, TypeError, ValueError):
                        episode_failures["house_source_resolution"] += 1
                        continue
                    if observed != [{
                        "basis": "OFFICIAL_SERVICE_RANGE",
                        "start": expected_start,
                        "end_exclusive": expected_end,
                    }]:
                        episode_failures["house_source_interval_transform"] += 1
                    if (
                        str(source.get("employing_office_raw"))
                        not in (row.get("raw_employer_variants") or [])
                        or str(source.get("title_description_raw"))
                        not in (row.get("raw_title_variants") or [])
                    ):
                        episode_failures["house_source_literal_binding"] += 1
                elif lane == "senate_payroll_corroborated":
                    source = senate_source_rows.get(str(candidate_id))
                    intervals = source.get("observed_report_intervals") if source else None
                    if not isinstance(intervals, list) or len(intervals) != 1:
                        episode_failures["senate_source_resolution"] += 1
                        continue
                    source_interval = intervals[0]
                    try:
                        expected_end = (
                            date.fromisoformat(str(source_interval["end"]))
                            + timedelta(days=1)
                        ).isoformat()
                    except (KeyError, TypeError, ValueError):
                        episode_failures["senate_source_resolution"] += 1
                        continue
                    expected = [{
                        "basis": str(source_interval.get("basis") or "UNKNOWN"),
                        "start": str(source_interval.get("start")),
                        "end_exclusive": expected_end,
                    }]
                    if observed != expected:
                        episode_failures["senate_source_interval_transform"] += 1
                    if source_interval.get("basis") == "COMPLEX_QUALIFIER_REVIEW_REQUIRED":
                        episode_failures["senate_review_basis_source"] += 1
                    if (
                        str(source.get("employing_office_candidate"))
                        not in (row.get("raw_employer_variants") or [])
                        or str(source.get("title_candidate"))
                        not in (row.get("raw_title_variants") or [])
                    ):
                        episode_failures["senate_source_literal_binding"] += 1
        elif observed:
            episode_failures["asserted_episode_has_observation_ranges"] += 1
        core = {
            "lane": (row.get("evidence_lanes") or [None])[0],
            "person": row.get("lda_source_person_id"),
            "employer": str(row.get("employer_candidate") or "").casefold(),
            "title": str(row.get("title_candidate") or "").casefold(),
            "bounds": {
                key: row.get(key)
                for key in (
                    "valid_start_earliest", "valid_start_latest",
                    "valid_end_earliest", "valid_end_latest", "start_precision",
                    "end_precision", "asserted_current",
                )
            },
            "temporal_semantics": row.get("temporal_semantics"),
            "identity_status": row.get("identity_status"),
            "container_status": row.get("container_status"),
        }
        if episode_id != "provisional:employment-episode:" + digest(core):
            episode_failures["episode_id_content_binding"] += 1
        if not row.get("promotion_blockers"):
            episode_failures["promotion_blockers_missing"] += 1
    assertions["provisional_episode_rows_exact"] = len(episodes) == primary_receipt.get(
        "provisional_episode_rows"
    )
    assertions["provisional_lane_counts_exact"] = dict(sorted(provisional_lane_counts.items())) == primary_receipt.get("provisional_episode_lane_counts")
    assertions["temporal_semantics_counts_exact"] = dict(sorted(temporal_semantics_counts.items())) == primary_receipt.get("temporal_semantics_counts")
    proposed_decisions = sum(
        row.get("decision") == "PROVISIONALLY_ACCEPTED" for row in decisions.values()
    )
    assertions["support_decision_conservation"] = proposed_decisions == primary_receipt.get("provisional_support_decision_rows")
    assertions["dedup_conservation"] = (
        proposed_decisions - len(episodes)
        == primary_receipt.get("exact_fact_duplicate_rows_collapsed")
    )
    assertions["all_provisional_episodes_blocked"] = not episode_failures

    summary_path = primary / "employment_adjudication_person_summary_25340.ndjson.gz"
    person_ids: set[str] = set()
    summary_failures: Counter[str] = Counter()
    sealed_queue_path = Path(primary_receipt["inputs"]["sealed_queue"]["path"])
    sealed_queue_rows = list(rows(sealed_queue_path))
    queue_records = {
        str(row["lda_source_person_id"]): row for row in sealed_queue_rows
    }
    queue_order = {
        str(row["lda_source_person_id"]): row.get("sealed_queue_ordinal")
        for row in sealed_queue_rows
    }
    decision_counts_by_person: defaultdict[str, Counter[str]] = defaultdict(Counter)
    decision_ids_by_person: defaultdict[str, list[str]] = defaultdict(list)
    for decision in decisions.values():
        person_id = str(decision["lda_source_person_id"])
        decision_counts_by_person[person_id][
            f"{decision['lane']}:{decision['decision']}"
        ] += 1
        decision_ids_by_person[person_id].append(decision["decision_id"])
    episode_ids_by_person: defaultdict[str, list[str]] = defaultdict(list)
    for episode in episodes.values():
        episode_ids_by_person[str(episode["lda_source_person_id"])].append(
            episode["episode_id"]
        )
    for ordinal, row in enumerate(rows(summary_path), start=1):
        try:
            validate_instance(
                row,
                schemas["staffer-network-employment-adjudication-person-summary-v1"],
                _schema_checked=True,
            )
        except Exception:
            summary_failures["schema_validation"] += 1
        person_id = str(row.get("lda_source_person_id") or "")
        if not person_id or person_id in person_ids:
            summary_failures["duplicate_or_blank_person"] += 1
        person_ids.add(person_id)
        if row.get("sealed_queue_ordinal") != ordinal or queue_order.get(person_id) != ordinal:
            summary_failures["queue_order"] += 1
        if row.get("display_name") != queue_records.get(person_id, {}).get("display_name"):
            summary_failures["queue_display_name"] += 1
        if row.get("source_native_identity_status") != "ACCEPTED":
            summary_failures["source_native_identity"] += 1
        if row.get("cross_source_identity_merge_performed") is not False:
            summary_failures["cross_source_merge"] += 1
        if row.get("canonical_employment_promoted_count") != 0:
            summary_failures["canonical_promotion"] += 1
        if row.get("primary_temporal_eligible_episode_count") != 0:
            summary_failures["primary_temporal_eligibility"] += 1
        if row.get("complete_lifetime_employment_asserted") is not False:
            summary_failures["lifetime_assertion"] += 1
        expected_counts = dict(sorted(decision_counts_by_person[person_id].items()))
        expected_episode_count = len(episode_ids_by_person[person_id])
        expected_state = (
            "PROVISIONAL_EPISODES_PENDING_REVIEW" if expected_episode_count
            else "CANDIDATES_REVIEW_REQUIRED" if expected_counts
            else "NO_CANDIDATES"
        )
        if row.get("decision_counts") != expected_counts:
            summary_failures["decision_counts"] += 1
        if row.get("provisional_episode_count") != expected_episode_count:
            summary_failures["episode_count"] += 1
        if row.get("adjudication_state") != expected_state:
            summary_failures["adjudication_state"] += 1
        if row.get("open_gate_codes") != primary_receipt.get("open_gates"):
            summary_failures["open_gate_codes"] += 1
        if row.get("decision_digest") != digest(sorted(decision_ids_by_person[person_id])):
            summary_failures["decision_digest"] += 1
        if row.get("episode_digest") != digest(sorted(episode_ids_by_person[person_id])):
            summary_failures["episode_digest"] += 1
    assertions["person_scope_exact"] = (
        person_ids == set(queue_order)
        and len(sealed_queue_rows) == len(queue_order) == 25340
    )
    decision_people = {
        str(row.get("lda_source_person_id") or "") for row in decisions.values()
    }
    episode_people = {
        str(row.get("lda_source_person_id") or "") for row in episodes.values()
    }
    assertions["all_decision_and_episode_people_in_sealed_queue"] = (
        decision_people <= set(queue_order) and episode_people <= set(queue_order)
    )
    accepted_decision_ids = {
        decision_id for decision_id, row in decisions.items()
        if row.get("decision") == "PROVISIONALLY_ACCEPTED"
    }
    linked_episode_decision_ids = {
        str(decision_id)
        for row in episodes.values()
        for decision_id in row.get("decision_ids") or []
    }
    assertions["accepted_decision_episode_set_equality"] = (
        accepted_decision_ids == linked_episode_decision_ids
    )
    assertions["all_person_summaries_valid"] = not summary_failures

    covered_sample = list(rows(primary / "covered_position_parser_gold_sample_100.ndjson.gz"))
    identity_sample = list(rows(primary / "identity_rule_gold_sample_200.ndjson.gz"))
    assertions["covered_gold_sample_exact"] = len(covered_sample) == 100
    assertions["identity_gold_sample_exact"] = len(identity_sample) == 200
    sample_failures: Counter[str] = Counter()
    sample_ids: set[str] = set()
    sample_strata: Counter[tuple[str, str]] = Counter()
    for row in covered_sample + identity_sample:
        try:
            validate_instance(
                row,
                schemas["staffer-network-employment-adjudication-gold-sample-v2"],
                _schema_checked=True,
            )
        except Exception:
            sample_failures["schema_validation"] += 1
        sample_id = str(row.get("sample_id") or "")
        if not sample_id or sample_id in sample_ids:
            sample_failures["duplicate_or_blank_sample_id"] += 1
        sample_ids.add(sample_id)
        sample_core = {
            key: value for key, value in row.items()
            if key not in {"sample_id", "candidate_evidence", "proposed_episode"}
        }
        if sample_id != "adjudication:gold-sample:" + digest(sample_core):
            sample_failures["sample_id_content_binding"] += 1
        if row.get("candidate_evidence_sha256") != digest(
            row.get("candidate_evidence")
        ):
            sample_failures["candidate_evidence_payload_digest"] += 1
        expected_episode_sha256 = (
            digest(row.get("proposed_episode"))
            if row.get("proposed_episode") is not None else None
        )
        if row.get("proposed_episode_sha256") != expected_episode_sha256:
            sample_failures["proposed_episode_payload_digest"] += 1
        decision = decisions.get(str(row.get("decision_id") or ""))
        if (
            decision is None
            or decision.get("candidate_id") != row.get("candidate_id")
            or decision.get("lane") != row.get("lane")
            or decision.get("lda_source_person_id") != row.get("lda_source_person_id")
            or decision.get("decision") != row.get("proposed_decision")
            or decision.get("evidence_digest") != row.get("evidence_digest")
            or decision.get("decision_payload_sha256")
            != row.get("decision_payload_sha256")
        ):
            sample_failures["decision_sample_reciprocity"] += 1
        proposed = episodes.get(str(decision.get("proposed_episode_id") or "")) if decision else None
        if row.get("proposed_episode") != proposed:
            sample_failures["proposed_episode_materialization"] += 1
        if row.get("sample_kind") == "IDENTITY_RULE":
            sample_strata[(str(row.get("lane")), str(row.get("proposed_decision")))] += 1
            if row.get("proposed_decision") == "PROVISIONALLY_ACCEPTED":
                evidence = row.get("candidate_evidence") or {}
                if row.get("lane") in {
                    "house_payroll_corroborated", "senate_payroll_corroborated"
                } and not evidence.get("corroboration"):
                    sample_failures["accepted_identity_corroboration_missing"] += 1
                if row.get("lane") in {
                    "house_payroll_corroborated", "senate_payroll_corroborated"
                } and evidence.get("corroboration"):
                    corroboration = evidence["corroboration"]
                    source = evidence.get("source_candidate") or {}
                    claim = corroboration.get("lda_claim") or {}
                    roles = [
                        str(item.get("text") or "")
                        for item in claim.get("role_title_mentions") or []
                        if item.get("confidence") == "HIGH"
                        and not item.get("generic_title_risk")
                    ]
                    organizations = [
                        str(item.get("text") or "")
                        for item in claim.get("office_employer_mentions") or []
                        if item.get("confidence") == "HIGH"
                    ]
                    if row.get("lane") == "house_payroll_corroborated":
                        title_value = source.get("title_description_raw")
                        organization_value = source.get("employing_office_raw")
                        expected_cardinality = len(house_people_by_payroll[
                            str(source.get("payroll_candidate_id"))
                        ])
                        reported_cardinality = evidence.get(
                            "queue_candidate_count_for_payroll_name"
                        )
                    else:
                        title_value = source.get("title_candidate")
                        organization_value = source.get("employing_office_candidate")
                        expected_cardinality = source.get("queue_candidate_count_for_name")
                        reported_cardinality = evidence.get("queue_candidate_count_for_name")
                    title_score = max(
                        (similarity(title_value, value) for value in roles), default=0.0
                    )
                    organization_score = max(
                        (similarity(organization_value, value) for value in organizations),
                        default=0.0,
                    )
                    if (
                        corroboration.get("title_similarity") != title_score
                        or corroboration.get("organization_similarity")
                        != organization_score
                        or corroboration.get("title_threshold") != 0.34
                        or corroboration.get("organization_threshold") != 0.20
                        or reported_cardinality != expected_cardinality
                        or evidence.get("unique_payroll_to_lda_name_candidate")
                        is not (expected_cardinality == 1)
                    ):
                        sample_failures["accepted_identity_corroboration_reproduction"] += 1
        evidence = row.get("candidate_evidence") or {}
        if row.get("lane") in {
            "house_payroll_corroborated", "senate_payroll_corroborated"
        }:
            evidence_source = evidence.get("source_candidate")
        elif row.get("lane") == "structured_public_profile_episode":
            evidence_source = evidence.get("episode")
        else:
            evidence_source = evidence
        if not isinstance(evidence_source, dict) or digest(evidence_source) != row.get(
            "evidence_digest"
        ):
            sample_failures["candidate_evidence_digest"] += 1
    assertions["gold_samples_immutable_unlabeled_units"] = all(
        not ({"gold_label", "gold_reviewer_id", "gold_rationale"} & set(row))
        for row in covered_sample + identity_sample
    )
    assertions["identity_gold_strata_exact"] = dict(sample_strata) == IDENTITY_STRATA
    assertions["gold_samples_valid"] = not sample_failures

    scanned = [primary_receipt_path, twin_receipt_path]
    scanned.extend(primary / name for name in PAYLOADS)
    scanned.extend(twin / name for name in PAYLOADS)
    token_matches = sum(scan_plaintext(path) for path in scanned)
    assertions["token_negative_artifact_scan"] = token_matches == 0
    failures = sorted(name for name, passed in assertions.items() if not passed)
    result = {
        "schema_id": VERIFICATION_SCHEMA_ID,
        "method_version": VERIFIER_METHOD_VERSION,
        "implementation": {
            "verifier_path": str(Path(__file__).resolve()),
            "verifier_sha256": sha256(Path(__file__).resolve()),
            "verified_generator_sha256": primary_implementation["generator_sha256"],
            "python_version": sys.version.split()[0],
        },
        "verification_schema_sha256": sha256(VERIFICATION_SCHEMA_PATH),
        "status": "PASS" if not failures else "FAIL",
        "assertions": dict(sorted(assertions.items())),
        "failures": failures,
        "decision_failure_counts": dict(sorted(decision_failures.items())),
        "episode_failure_counts": dict(sorted(episode_failures.items())),
        "summary_failure_counts": dict(sorted(summary_failures.items())),
        "sample_failure_counts": dict(sorted(sample_failures.items())),
        "token_negative_scan_matches": token_matches,
        "primary_receipt_sha256": sha256(primary_receipt_path),
        "twin_receipt_sha256": sha256(twin_receipt_path),
    }
    if result["status"] == "PASS" and (
        result["failures"]
        or any(value is not True for value in result["assertions"].values())
        or any(
            result[key]
            for key in (
                "decision_failure_counts", "episode_failure_counts",
                "summary_failure_counts", "sample_failure_counts",
            )
        )
        or result["token_negative_scan_matches"] != 0
    ):
        raise VerificationError("PASS receipt is internally inconsistent")
    validate_instance(result, verification_schema, _schema_checked=True)
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "employment_adjudication_verification_receipt.json").write_bytes(compact(result))
    if failures:
        raise VerificationError("verification failed: " + ", ".join(failures))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--twin", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.primary.resolve(), args.twin.resolve(), args.output_root.resolve())
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
