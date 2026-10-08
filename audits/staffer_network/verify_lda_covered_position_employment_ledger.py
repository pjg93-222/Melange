#!/usr/bin/env python3
"""Independently verify the sealed LDA covered-position review ledgers.

This verifier does not import the builder.  It binds the primary and clean
twin generations byte-for-byte, recounts all source and output rows, checks
the source-to-output joins, enforces the filing URL template, and fails closed
on canonical-promotion, complete-history, or credential-token leakage.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import zip_longest
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable, Iterator, Mapping


EXPECTED_PERSON_ROWS = 25_340
EXPECTED_SOURCE_FILES: dict[str, dict[str, Any]] = {
    "source_native_lobbyists": {
        "name": "lda_lobbyist_assertions.ndjson.gz",
        "bytes": 1_928_569,
        "sha256": "80ac82346c435bb8f1231d9f3425d759ca9a8ae063db879ec104244f9fcd282e",
    },
    "source_native_covered_position_occurrences": {
        "name": "lda_covered_position_assertions.ndjson.gz",
        "bytes": 58_789_826,
        "sha256": "81841c810269bf967cb3edc10664dbbad5aa17261089eaa67e4f288c2fcda625",
    },
    "materialized_person_universe": {
        "name": "lda_employment_people.ndjson.gz",
        "bytes": 1_652_798,
        "sha256": "49fbdc1e03f8cac931b56b265222a594583774857b650b0b987b471bf01e3908",
    },
    "materialized_source_fragments": {
        "name": "lda_employment_claims.ndjson.gz",
        "bytes": 2_769_809,
        "sha256": "39fb98a5ef2fe68b990356e84ce38f5d61b900f2f691d66156c84c48e84e9311",
    },
    "exact_span_candidate_mentions": {
        "name": "lda_employment_claim_mentions.ndjson.gz",
        "bytes": 3_910_651,
        "sha256": "d131b963027d73a760a542b4f82143165d816ab18aa36eaf57f74a21680cbd59",
    },
}
ARTIFACTS = (
    "lda_covered_position_occurrences.ndjson.gz",
    "lda_covered_position_episode_candidates.ndjson.gz",
    "lda_covered_position_people_coverage.ndjson.gz",
    "lda_covered_position_employment_ledger_receipt.json",
)
FILING_URL_TEMPLATE = (
    "https://lda.senate.gov/filings/public/filing/{filing_uuid}/print/"
)
LEGILIST_EXAMPLE_URL = (
    "https://legilist.com/lda/contributions/lobbyist/147664/gordon-holzberg/"
)
TOKEN_PATTERN = re.compile(
    rb'''(?i)["']?(?:password|passwd|api[_-]?key|access[_-]?token|secret)["']?'''
    rb'''\s*:\s*["'][^"']+["']'''
)


class VerificationFailure(RuntimeError):
    pass


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


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise VerificationFailure(f"JSON object required: {path}")
    return value


def rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationFailure(f"object required at {path}:{line_number}")
            yield value


def row_list(path: Path) -> list[dict[str, Any]]:
    return list(rows(path))


def pairwise(
    left: Iterable[dict[str, Any]], right: Iterable[dict[str, Any]]
) -> Iterator[tuple[int, dict[str, Any], dict[str, Any]]]:
    sentinel = object()
    for ordinal, pair in enumerate(zip_longest(left, right, fillvalue=sentinel), 1):
        lhs, rhs = pair
        if lhs is sentinel or rhs is sentinel:
            raise VerificationFailure(f"row streams differ in length at ordinal {ordinal}")
        yield ordinal, lhs, rhs  # type: ignore[misc]


def filing_url(filing_uuid: str) -> str:
    return FILING_URL_TEMPLATE.format(filing_uuid=filing_uuid)


def legilist_numeric_id(url: str) -> str:
    match = re.search(r"/lda/contributions/lobbyist/(\d+)(?:/|$)", url)
    if match is None:
        raise VerificationFailure(f"LegiList lobbyist numeric ID absent: {url}")
    return match.group(1)


def promotion_or_completeness_violations(
    row: Mapping[str, Any], context: str
) -> list[str]:
    failures: list[str] = []
    checks = {
        "canonical_employment_fact": False,
        "canonical_employment_promotions": 0,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "complete_employment_history_asserted": False,
    }
    for key, expected in checks.items():
        if key in row and row[key] != expected:
            failures.append(f"{context}:{key}={row[key]!r}")
    for key, value in row.items():
        lowered = str(key).casefold()
        if lowered.startswith("canonical_") and key not in checks:
            if value not in (False, 0, None, "", "NOT_ADJUDICATED"):
                failures.append(f"{context}:{key}={value!r}")
        if key not in checks and "complete" in lowered and "history" in lowered:
            if value not in (False, 0, None, ""):
                failures.append(f"{context}:{key}={value!r}")
    return failures


def token_matches(path: Path) -> int:
    matches = 0
    if path.suffix.casefold() == ".gz":
        with gzip.open(path, "rb") as stream:
            for line in stream:
                matches += len(TOKEN_PATTERN.findall(line))
    else:
        matches = len(TOKEN_PATTERN.findall(path.read_bytes()))
    return matches


def source_paths(
    source_root: Path, materialized_root: Path, normalized_root: Path
) -> dict[str, Path]:
    return {
        "source_native_lobbyists": source_root / "lda_lobbyist_assertions.ndjson.gz",
        "source_native_covered_position_occurrences": source_root
        / "lda_covered_position_assertions.ndjson.gz",
        "materialized_person_universe": materialized_root
        / "lda_employment_people.ndjson.gz",
        "materialized_source_fragments": materialized_root
        / "lda_employment_claims.ndjson.gz",
        "exact_span_candidate_mentions": normalized_root
        / "lda_employment_claim_mentions.ndjson.gz",
    }


def verify(
    *,
    primary_dir: Path,
    twin_dir: Path,
    output_dir: Path,
    source_root: Path,
    materialized_root: Path,
    normalized_root: Path,
    schema_audit_receipt: Path | None = None,
) -> dict[str, Any]:
    primary_dir = primary_dir.resolve(strict=True)
    twin_dir = twin_dir.resolve(strict=True)
    sources = {
        role: path.resolve(strict=True)
        for role, path in source_paths(
            source_root.resolve(strict=True),
            materialized_root.resolve(strict=True),
            normalized_root.resolve(strict=True),
        ).items()
    }
    primary = {name: (primary_dir / name).resolve(strict=True) for name in ARTIFACTS}
    twin = {name: (twin_dir / name).resolve(strict=True) for name in ARTIFACTS}
    primary_receipt = read_json(primary[ARTIFACTS[-1]])
    twin_receipt = read_json(twin[ARTIFACTS[-1]])

    assertions: dict[str, bool] = {}
    failures: list[str] = []
    artifact_hashes: dict[str, dict[str, Any]] = {}
    for name in ARTIFACTS:
        primary_hash = sha256_file(primary[name])
        twin_hash = sha256_file(twin[name])
        byte_equal = primary[name].read_bytes() == twin[name].read_bytes()
        artifact_hashes[name] = {
            "bytes": primary[name].stat().st_size,
            "primary_sha256": primary_hash,
            "twin_sha256": twin_hash,
        }
        assertions[f"primary_twin_bytes_equal:{name}"] = byte_equal
        assertions[f"primary_twin_sha256_equal:{name}"] = primary_hash == twin_hash

    assertions["primary_receipt_pass"] = primary_receipt.get("status") == "PASS"
    assertions["twin_receipt_pass"] = twin_receipt.get("status") == "PASS"
    assertions["primary_twin_receipts_equal"] = primary_receipt == twin_receipt
    assertions["receipt_filing_url_template_exact"] = all(
        receipt.get("provenance", {}).get("official_filing_url_template")
        == FILING_URL_TEMPLATE
        for receipt in (primary_receipt, twin_receipt)
    )

    source_hashes: dict[str, dict[str, Any]] = {}
    receipt_sources = {
        str(item.get("role")): item for item in primary_receipt.get("source_inputs", [])
    }
    twin_receipt_sources = {
        str(item.get("role")): item for item in twin_receipt.get("source_inputs", [])
    }
    for role, expected in EXPECTED_SOURCE_FILES.items():
        path = sources[role]
        actual = {
            "bytes": path.stat().st_size,
            "path": str(path),
            "sha256": sha256_file(path),
        }
        source_hashes[role] = actual
        assertions[f"exact_source_hash:{role}"] = actual["sha256"] == expected["sha256"]
        assertions[f"exact_source_bytes:{role}"] = actual["bytes"] == expected["bytes"]
        assertions[f"primary_receipt_binds_source:{role}"] = (
            receipt_sources.get(role, {}).get("path") == expected["name"]
            and receipt_sources.get(role, {}).get("bytes") == actual["bytes"]
            and receipt_sources.get(role, {}).get("sha256") == actual["sha256"]
        )
        assertions[f"twin_receipt_binds_source:{role}"] = (
            twin_receipt_sources.get(role, {}).get("path") == expected["name"]
            and twin_receipt_sources.get(role, {}).get("bytes") == actual["bytes"]
            and twin_receipt_sources.get(role, {}).get("sha256") == actual["sha256"]
        )

    source_people = row_list(sources["source_native_lobbyists"])
    source_person_ids = [str(row["source_person_id"]) for row in source_people]
    source_person_id_set = set(source_person_ids)
    materialized_people = row_list(sources["materialized_person_universe"])
    materialized_person_ids = [str(row["lda_source_person_id"]) for row in materialized_people]
    materialized_person_id_set = set(materialized_person_ids)

    counts: Counter[str] = Counter()
    counts["source_person_rows"] = len(source_people)
    counts["source_person_unique_ids"] = len(source_person_id_set)
    counts["materialized_person_rows"] = len(materialized_people)
    counts["materialized_person_unique_ids"] = len(materialized_person_id_set)
    assertions["source_person_rows_exact_25340"] = len(source_people) == EXPECTED_PERSON_ROWS
    assertions["source_person_ids_unique"] = len(source_person_id_set) == len(source_people)
    assertions["materialized_person_universe_exact"] = (
        materialized_person_id_set == source_person_id_set
        and len(materialized_people) == EXPECTED_PERSON_ROWS
        and len(materialized_person_id_set) == EXPECTED_PERSON_ROWS
    )

    people_out = primary["lda_covered_position_people_coverage.ndjson.gz"]
    output_person_ids: list[str] = []
    promotion_failures: list[str] = []
    people_source_numeric: dict[str, list[dict[str, Any]]] = {}
    for ordinal, (source_row, output_row) in enumerate(
        zip_longest(source_people, rows(people_out), fillvalue=None), 1
    ):
        if source_row is None or output_row is None:
            failures.append(f"person stream length mismatch at ordinal {ordinal}")
            break
        source_id = str(source_row["source_person_id"])
        output_person_ids.append(str(output_row.get("lda_source_person_id", "")))
        counts["output_person_rows"] += 1
        if output_row.get("lda_source_person_id") != source_id:
            counts["person_order_or_id_mismatches"] += 1
        if output_row.get("source_numeric_id") != source_row.get("source_numeric_id"):
            counts["person_numeric_id_mismatches"] += 1
        if output_row.get("display_name") != source_row.get("display_name"):
            counts["person_display_name_mismatches"] += 1
        promotion_failures.extend(
            promotion_or_completeness_violations(output_row, f"people:{ordinal}")
        )
        numeric = str(source_row.get("source_numeric_id", ""))
        people_source_numeric.setdefault(numeric, []).append(source_row)
    output_person_id_set = set(output_person_ids)
    counts["output_person_unique_ids"] = len(output_person_id_set)
    assertions["output_person_rows_exact_25340"] = (
        counts["output_person_rows"] == EXPECTED_PERSON_ROWS
    )
    assertions["output_person_universe_exact"] = (
        output_person_id_set == source_person_id_set
        and len(output_person_ids) == EXPECTED_PERSON_ROWS
        and len(output_person_id_set) == EXPECTED_PERSON_ROWS
        and counts["person_order_or_id_mismatches"] == 0
        and counts["person_numeric_id_mismatches"] == 0
        and counts["person_display_name_mismatches"] == 0
    )

    occurrence_source = sources["source_native_covered_position_occurrences"]
    occurrence_out = primary["lda_covered_position_occurrences.ndjson.gz"]
    occurrence_fields = (
        "assertion_id",
        "covered_position",
        "dt_posted",
        "filing_uuid",
        "source_activity_id",
        "source_person_id",
        "source_system_id",
        "support_digest",
    )
    source_occurrence_ids: set[str] = set()
    output_occurrence_ids: set[str] = set()
    for ordinal, source_row, output_row in pairwise(rows(occurrence_source), rows(occurrence_out)):
        counts["source_occurrence_rows"] += 1
        counts["output_occurrence_rows"] += 1
        source_occurrence_ids.add(str(source_row.get("assertion_id", "")))
        output_occurrence_ids.add(str(output_row.get("assertion_id", "")))
        if any(source_row.get(field) != output_row.get(field) for field in occurrence_fields):
            counts["occurrence_projection_mismatches"] += 1
        if output_row.get("filing_url") != filing_url(str(source_row.get("filing_uuid", ""))):
            counts["filing_url_mismatches"] += 1
        else:
            counts["filing_url_template_bindings"] += 1
        promotion_failures.extend(
            promotion_or_completeness_violations(output_row, f"occurrence:{ordinal}")
        )
    counts["source_occurrence_unique_ids"] = len(source_occurrence_ids)
    counts["output_occurrence_unique_ids"] = len(output_occurrence_ids)
    assertions["occurrence_source_row_conservation"] = (
        counts["source_occurrence_rows"] == counts["output_occurrence_rows"]
        and counts["occurrence_projection_mismatches"] == 0
        and source_occurrence_ids == output_occurrence_ids
        and len(source_occurrence_ids) == counts["source_occurrence_rows"]
        and len(output_occurrence_ids) == counts["output_occurrence_rows"]
    )
    assertions["all_occurrence_filing_urls_bound"] = (
        counts["filing_url_mismatches"] == 0
        and counts["filing_url_template_bindings"] == counts["source_occurrence_rows"]
    )

    mentions = row_list(sources["exact_span_candidate_mentions"])
    mentions_by_id = {str(row["claim_id"]): row for row in mentions}
    counts["mention_rows"] = len(mentions)
    counts["mention_unique_claim_ids"] = len(mentions_by_id)
    claims_source = sources["materialized_source_fragments"]
    candidates_out = primary["lda_covered_position_episode_candidates.ndjson.gz"]
    claim_ids: set[str] = set()
    candidate_ids: set[str] = set()
    for ordinal, claim, candidate in pairwise(rows(claims_source), rows(candidates_out)):
        counts["source_claim_rows"] += 1
        counts["episode_candidate_rows"] += 1
        claim_id = str(claim.get("claim_id", ""))
        claim_ids.add(claim_id)
        candidate_ids.add(str(candidate.get("claim_id", "")))
        mention = mentions_by_id.get(claim_id)
        if (
            candidate.get("claim_id") != claim.get("claim_id")
            or candidate.get("lda_source_person_id") != claim.get("lda_source_person_id")
            or candidate.get("raw_covered_position_literal")
            != claim.get("raw_covered_position_literal")
            or candidate.get("claim_text") != claim.get("claim_text")
        ):
            counts["claim_candidate_projection_mismatches"] += 1
        if mention is None or any(
            candidate.get(field) != mention.get(field)
            for field in (
                "role_title_mentions",
                "office_employer_mentions",
                "date_range_mentions",
            )
        ):
            counts["candidate_mention_projection_mismatches"] += 1
        promotion_failures.extend(
            promotion_or_completeness_violations(candidate, f"candidate:{ordinal}")
        )
    counts["source_claim_unique_ids"] = len(claim_ids)
    counts["episode_candidate_unique_ids"] = len(candidate_ids)
    assertions["claim_episode_candidate_conservation"] = (
        counts["source_claim_rows"] == counts["episode_candidate_rows"]
        and counts["source_claim_rows"] == counts["mention_rows"]
        and claim_ids == candidate_ids == set(mentions_by_id)
        and len(claim_ids) == counts["source_claim_rows"]
        and len(candidate_ids) == counts["episode_candidate_rows"]
        and len(mentions_by_id) == counts["mention_rows"]
        and counts["claim_candidate_projection_mismatches"] == 0
        and counts["candidate_mention_projection_mismatches"] == 0
    )

    counts["promotion_or_completeness_violations"] = len(promotion_failures)
    assertions["canonical_promotions_and_complete_history_claims_zero"] = (
        not promotion_failures
        and all(
            receipt.get("invariant_checks", {}).get(name) is True
            for receipt in (primary_receipt, twin_receipt)
            for name in (
                "canonical_employment_promotions_zero",
                "canonical_identity_promotions_zero",
                "complete_history_assertions_zero",
            )
        )
    )

    declared_primary_files = {
        str(item.get("path")): item for item in primary_receipt.get("files", [])
    }
    declared_twin_files = {
        str(item.get("path")): item for item in twin_receipt.get("files", [])
    }
    for name in ARTIFACTS[:-1]:
        actual = artifact_hashes[name]
        assertions[f"primary_receipt_binds_output:{name}"] = (
            declared_primary_files.get(name, {}).get("bytes") == actual["bytes"]
            and declared_primary_files.get(name, {}).get("sha256")
            == actual["primary_sha256"]
        )
        assertions[f"twin_receipt_binds_output:{name}"] = (
            declared_twin_files.get(name, {}).get("bytes") == twin[name].stat().st_size
            and declared_twin_files.get(name, {}).get("sha256") == actual["twin_sha256"]
        )

    token_match_counts: dict[str, int] = {}
    for label, paths_by_name in (("primary", primary), ("twin", twin)):
        for name, path in paths_by_name.items():
            token_match_counts[f"{label}/{name}"] = token_matches(path)
    counts["credential_token_matches"] = sum(token_match_counts.values())
    assertions["token_negative_scan"] = counts["credential_token_matches"] == 0

    numeric_id = legilist_numeric_id(LEGILIST_EXAMPLE_URL)
    legilist_matches = people_source_numeric.get(numeric_id, [])
    legilist = {
        "bulk_crawl_performed": False,
        "equivalence_basis": (
            "LegiList URL numeric path segment equals the exact Senate LDA "
            "source_numeric_id; no name-only identity resolution is asserted."
        ),
        "legilist_numeric_id": numeric_id,
        "legilist_url": LEGILIST_EXAMPLE_URL,
        "local_source_matches": [
            {
                "display_name": row.get("display_name"),
                "source_numeric_id": row.get("source_numeric_id"),
                "source_person_id": row.get("source_person_id"),
            }
            for row in legilist_matches
        ],
        "published_crawl_delay_seconds": 10,
    }
    assertions["legilist_numeric_id_exact_local_equivalence"] = (
        len(legilist_matches) == 1
        and str(legilist_matches[0].get("source_numeric_id")) == numeric_id
    )

    schema_audit: dict[str, Any] | None = None
    if schema_audit_receipt is not None:
        schema_audit_path = schema_audit_receipt.resolve(strict=True)
        schema_audit = read_json(schema_audit_path)
        conclusion = schema_audit.get("conclusion", {})
        assertions["raw_schema_audit_pass"] = (
            schema_audit.get("status") == "PASS"
            and not schema_audit.get("errors")
            and schema_audit.get("checks", {}).get("all_discovered_raw_pages_parsed") is True
            and conclusion.get("employment_source_shape")
            == "filing.lobbying_activities[].lobbyists[].covered_position"
            and all(
                conclusion.get(key) is False
                for key in (
                    "separately_structured_current_field",
                    "separately_structured_employer_or_office_field",
                    "separately_structured_employment_end_field",
                    "separately_structured_employment_start_field",
                    "separately_structured_title_field",
                )
            )
        )
        schema_audit = {
            "inventory_binding_sha256": schema_audit.get("inventory_binding_sha256"),
            "receipt_path": str(schema_audit_path),
            "receipt_sha256": sha256_file(schema_audit_path),
            "status": schema_audit.get("status"),
            "totals": schema_audit.get("totals"),
        }

    for name, passed in assertions.items():
        if not passed:
            failures.append(name)
    result = {
        "artifact_hashes": artifact_hashes,
        "assertions": dict(sorted(assertions.items())),
        "counts": dict(sorted(counts.items())),
        "failures": sorted(set(failures)),
        "legilist_id_equivalence": legilist,
        "promotion_or_completeness_failure_samples": promotion_failures[:10],
        "schema_audit": schema_audit,
        "schema_id": "staffer-network-lda-covered-position-employment-ledger-independent-verification-v1",
        "source_hashes": source_hashes,
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {
            "match_counts": dict(sorted(token_match_counts.items())),
            "scanned_files": len(token_match_counts),
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "verification_receipt.json"
    output_path.write_bytes(canonical_bytes(result))
    if failures:
        raise VerificationFailure("verification failed: " + ", ".join(sorted(set(failures))))
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--primary-dir",
        type=Path,
        default=Path("audits/staffer_network/lda_covered_position_employment_ledger_20260831"),
    )
    parser.add_argument(
        "--twin-dir",
        type=Path,
        default=Path(
            "audits/staffer_network/lda_covered_position_employment_ledger_20260831_verify"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(
            "audits/staffer_network/lda_covered_position_employment_ledger_verification_20260831"
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path(
            r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\normalized\lda-source-native\generation-20260830T231200Z"
        ),
    )
    parser.add_argument(
        "--materialized-root",
        type=Path,
        default=Path("audits/staffer_network/lda_employment_materialization_20260831_v2"),
    )
    parser.add_argument(
        "--normalized-root",
        type=Path,
        default=Path("audits/staffer_network/lda_employment_claim_normalization_20260831_v2"),
    )
    parser.add_argument(
        "--schema-audit-receipt",
        type=Path,
        default=Path(
            "audits/staffer_network/lda_raw_covered_position_schema_audit_20260831_verify/"
            "lda_raw_covered_position_schema_audit_receipt.json"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify(
        primary_dir=args.primary_dir,
        twin_dir=args.twin_dir,
        output_dir=args.output_dir,
        source_root=args.source_root,
        materialized_root=args.materialized_root,
        normalized_root=args.normalized_root,
        schema_audit_receipt=args.schema_audit_receipt,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
