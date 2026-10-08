#!/usr/bin/env python3
"""Validate deterministic twins and fail-closed controls for the public lane."""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


ROOT = Path("audits/staffer_network")
PUBLIC_A = ROOT / "public_evidence_generation_20260901T003500Z_g1371_pdf109_v3_pymupdf1282_processsafe_a"
PUBLIC_B = ROOT / "public_evidence_generation_20260901T003500Z_g1371_pdf109_v3_pymupdf1282_processsafe_b"
LITTLESIS_A = ROOT / "littlesis_lda_history_candidates_20260831"
LITTLESIS_B = ROOT / "littlesis_lda_history_candidates_20260831_verify"
POLITICO_A = ROOT / "politico_lda_employment_candidates_20260831"
POLITICO_B = ROOT / "politico_lda_employment_candidates_20260831_verify"
QUEUE_A = ROOT / "public_employment_acquisition_queue_20260901_v3c_a"
QUEUE_B = ROOT / "public_employment_acquisition_queue_20260901_v3c_b"
OUTPUT = ROOT / "public_employment_lane_validation_20260901_v1"


def compact(value: Any) -> bytes:
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


def directory_manifest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)).replace("\\", "/"): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def compare(name: str, primary: Path, twin: Path) -> dict[str, Any]:
    first = directory_manifest(primary)
    second = directory_manifest(twin)
    differences = [
        key
        for key in sorted(set(first) | set(second))
        if first.get(key) != second.get(key)
    ]
    return {
        "name": name,
        "primary": str(primary),
        "twin": str(twin),
        "primary_file_count": len(first),
        "twin_file_count": len(second),
        "relative_file_names_equal": set(first) == set(second),
        "per_file_sha256_equal": first == second,
        "difference_count": len(differences),
        "differences": differences,
        "primary_manifest": first,
    }


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_stream(path: Path) -> Iterable[str]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield line


def token_scan(paths: list[Path]) -> dict[str, Any]:
    pattern = re.compile(
        r"(?i)(?:password|passwd|authorization|cookie|api[_-]?key|client[_-]?secret)\s*[:=]"
    )
    matches = 0
    scanned_bytes = 0
    for path in paths:
        scanned_bytes += path.stat().st_size
        for line in text_stream(path):
            matches += len(pattern.findall(line))
    return {
        "structured_artifact_count": len(paths),
        "compressed_or_plain_bytes_scanned": scanned_bytes,
        "credential_assignment_pattern_matches": matches,
        "status": "PASS" if matches == 0 else "FAIL",
    }


def main() -> int:
    comparisons = [
        compare("public_process_isolated_generation", PUBLIC_A, PUBLIC_B),
        compare("littlesis_candidate_materialization", LITTLESIS_A, LITTLESIS_B),
        compare("politico_candidate_materialization", POLITICO_A, POLITICO_B),
        compare("public_employment_acquisition_queue", QUEUE_A, QUEUE_B),
    ]

    public = read_json(PUBLIC_A / "generation_receipt.json")
    littlesis = read_json(LITTLESIS_A / "littlesis_lda_history_candidate_receipt.json")
    politico = read_json(POLITICO_A / "politico_lda_employment_candidate_receipt.json")
    queue = read_json(QUEUE_A / "public_employment_acquisition_queue_receipt.json")

    gates = {
        "all_directory_twins_byte_equal": all(
            item["per_file_sha256_equal"] and item["relative_file_names_equal"]
            for item in comparisons
        ),
        "public_parser_version_pinned_1_28_2": public["pdf_repair"]["extraction_engine_version"] == "1.28.2",
        "public_pdf_process_isolation_pass": public["pdf_repair"].get("thread_safe_extraction_gate") == "PASS",
        "public_scope_1371_conserved": public["working_corpus"]["row_count"] == 1371,
        "public_employment_present_for_all_1371": public["working_corpus"]["rows_with_employment_facts"] == 1371,
        "public_pdf_sources_conserved": public["pdf_repair"]["source_capture_count"] == 109,
        "littlesis_candidate_only": littlesis["canonical_identity_promotions"] == 0
        and littlesis["canonical_history_fact_promotions"] == 0,
        "politico_candidate_only": politico["canonical_identity_promotions"] == 0
        and politico["canonical_employment_promotions"] == 0,
        "queue_scope_25340_conserved": queue["coverage_conservation"]
        and queue["output_rows"] == 25340
        and queue["unique_lda_source_person_ids"] == 25340,
        "queue_candidate_only": queue["canonical_identity_promotions"] == 0
        and queue["canonical_employment_promotions"] == 0
        and queue["complete_lifetime_employment_assertions"] == 0,
        "education_nonblocking": queue["secondary_nonblocking"] == "EDUCATION",
    }

    scan_paths = [
        PUBLIC_A / "public_evidence_ledger_1371.ndjson",
        PUBLIC_A / "generation_receipt.json",
        LITTLESIS_A / "littlesis_lda_history_candidates.ndjson.gz",
        LITTLESIS_A / "littlesis_lda_history_candidate_receipt.json",
        POLITICO_A / "politico_lda_employment_candidates.ndjson.gz",
        POLITICO_A / "politico_lda_employment_candidate_receipt.json",
        QUEUE_A / "public_employment_acquisition_queue_25340.ndjson.gz",
        QUEUE_A / "public_employment_acquisition_queue_receipt.json",
    ]
    token_negative_scan = token_scan(scan_paths)
    gates["token_negative_structured_artifact_scan"] = token_negative_scan["status"] == "PASS"

    status = "PASS" if all(gates.values()) else "FAIL"
    receipt = {
        "schema_id": "staffer-network-public-employment-lane-validation-receipt-v1",
        "status": status,
        "binding_objective": "COMPLETE_EMPLOYMENT_CHRONOLOGY",
        "secondary_nonblocking": "EDUCATION",
        "comparisons": comparisons,
        "gates": gates,
        "token_negative_scan": token_negative_scan,
        "adjudication_controls": {
            "identity_status": "REVIEW_REQUIRED",
            "canonical_identity_promotions": 0,
            "canonical_employment_promotions": 0,
            "complete_lifetime_employment_assertions": 0,
        },
        "key_counts": {
            "public_rows": public["working_corpus"]["row_count"],
            "public_employment_facts": public["working_corpus"]["employment_fact_count"],
            "public_external_employment_unique_ids": queue["new_candidate_coverage"]["repaired_public_external_employment_unique_ids"],
            "littlesis_position_unique_ids": queue["new_candidate_coverage"]["littlesis_position_unique_ids"],
            "littlesis_dated_position_unique_ids": littlesis["unique_lda_source_ids_with_dated_position_candidate"],
            "politico_role_unique_ids": queue["new_candidate_coverage"]["politico_role_unique_ids"],
            "unique_ids_with_any_new_public_employment_candidate": queue["new_candidate_coverage"]["unique_ids_with_any_new_public_employment_candidate"],
            "full_queue_rows": queue["output_rows"],
        },
        "queue_priority_counts": queue["priority_counts"],
        "queue_evidence_outcome_counts": queue["evidence_outcome_counts"],
        "queue_gap_counts": queue["gap_counts"],
        "artifact_hashes": {
            "public_ledger_ndjson": sha256_file(PUBLIC_A / "public_evidence_ledger_1371.ndjson"),
            "public_pdf_manifest": sha256_file(PUBLIC_A / "pdf_text_extractions_109.ndjson"),
            "public_receipt": sha256_file(PUBLIC_A / "generation_receipt.json"),
            "littlesis_candidates": sha256_file(LITTLESIS_A / "littlesis_lda_history_candidates.ndjson.gz"),
            "politico_candidates": sha256_file(POLITICO_A / "politico_lda_employment_candidates.ndjson.gz"),
            "full_acquisition_queue": sha256_file(QUEUE_A / "public_employment_acquisition_queue_25340.ndjson.gz"),
        },
        "known_nonterminal_gaps": [
            "The 1,371-row repaired public generation is PARTIAL and does not attest complete lifetime histories.",
            "20,624 source IDs still lack a public/third-party employment candidate.",
            "18,693 source IDs still lack a dated former-position candidate.",
            "20,964 source IDs still lack a bounded employment interval candidate.",
            "All 25,340 identities and employment chronologies still require adjudication.",
        ],
    }
    OUTPUT.mkdir(parents=True, exist_ok=False)
    output_path = OUTPUT / "validation_receipt.json"
    output_path.write_bytes(compact(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
