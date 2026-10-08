from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

import merge_employment_candidate_coverage as merger


def _compact(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_rows(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def _public_row(lda_id: str, ordinal: int) -> dict:
    return {
        "candidate_counts": {
            "base_house_payroll_match_groups": 0,
            "base_lda_covered_position_claims": 0,
            "base_registrant_association_episodes": 1,
            "base_senate_payroll_match_groups": 0,
            "legacy_public_external_employment": 0,
            "legacy_public_external_employment_bounded": 0,
            "legacy_public_external_employment_dated": 0,
            "littlesis_position": 0,
            "littlesis_position_bounded": 0,
            "littlesis_position_dated": 0,
            "politico_role_observation_time_only": 0,
            "repaired_public_external_employment": 0,
            "repaired_public_external_employment_bounded": 0,
            "repaired_public_external_employment_dated": 0,
        },
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "complete_lifetime_employment_asserted": False,
        "critical_path_gap_codes": [
            "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING",
            "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
            "DATED_FORMER_POSITION_CANDIDATE_MISSING",
            "FORMER_POSITION_CANDIDATE_MISSING",
            "IDENTITY_NOT_ADJUDICATED",
        ],
        "display_name": f"PERSON {ordinal}",
        "evidence_flags": {
            "has_any_bounded_employment_candidate": False,
            "has_any_dated_employment_candidate": False,
            "has_any_employment_candidate": False,
        },
        "identity_status": "REVIEW_REQUIRED",
        "lda_source_person_id": lda_id,
        "sealed_queue_ordinal": ordinal,
        "secondary_enrichment_gap_codes": ["EDUCATION_EVIDENCE_MISSING_NONBLOCKING"],
        "secondary_nonblocking": "EDUCATION",
    }


def _fixture(tmp_path: Path, rows: list[dict] | None = None) -> tuple[Path, dict[str, Path]]:
    rows = rows or [_public_row("lda:lobbyist:1", 1), _public_row("lda:lobbyist:2", 2)]
    queue = tmp_path / "queue.ndjson.gz"
    receipt = tmp_path / "public_receipt.json"
    validation = tmp_path / "validation.json"
    manifest = tmp_path / "manifest.json"
    _write_rows(queue, rows)
    receipt_value = {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "output": {"sha256": _sha(queue)},
        "output_rows": len(rows),
        "status": "PASS",
        "unique_lda_source_person_ids": len({row["lda_source_person_id"] for row in rows}),
    }
    receipt.write_bytes(_compact(receipt_value))
    validation_value = {
        "adjudication_controls": {
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "complete_lifetime_employment_assertions": 0,
            "identity_status": "REVIEW_REQUIRED",
        },
        "artifact_hashes": {"full_acquisition_queue": _sha(queue)},
        "comparisons": [
            {
                "name": "public_employment_acquisition_queue",
                "per_file_sha256_equal": True,
                "primary_manifest": {
                    "public_employment_acquisition_queue_receipt.json": _sha(receipt)
                },
            }
        ],
        "gates": {
            "education_nonblocking": True,
            "queue_candidate_only": True,
            "queue_scope_25340_conserved": True,
            "token_negative_structured_artifact_scan": True,
        },
        "schema_id": merger.EXPECTED_PUBLIC_VALIDATION_SCHEMA,
        "status": "PASS",
    }
    validation.write_bytes(_compact(validation_value))
    manifest_value = {
        "candidate_lanes": [],
        "expected_scope_size": len(rows),
        "public_queue": {
            "ledger": queue.name,
            "receipt": receipt.name,
            "validation": validation.name,
        },
        "schema_id": merger.MANIFEST_SCHEMA_ID,
    }
    manifest.write_bytes(_compact(manifest_value))
    return manifest, {
        "manifest": manifest,
        "queue": queue,
        "receipt": receipt,
        "validation": validation,
    }


def _rewrite_public_binding(paths: dict[str, Path]) -> None:
    receipt = json.loads(paths["receipt"].read_text())
    receipt["output"]["sha256"] = _sha(paths["queue"])
    paths["receipt"].write_bytes(_compact(receipt))
    validation = json.loads(paths["validation"].read_text())
    validation["artifact_hashes"]["full_acquisition_queue"] = _sha(paths["queue"])
    validation["comparisons"][0]["primary_manifest"][
        "public_employment_acquisition_queue_receipt.json"
    ] = _sha(paths["receipt"])
    paths["validation"].write_bytes(_compact(validation))


def test_public_only_is_deterministic_one_row_per_id_and_education_nonblocking(
    tmp_path: Path,
) -> None:
    manifest, _ = _fixture(tmp_path)
    receipt_a = merger.run(manifest, tmp_path / "out-a")
    receipt_b = merger.run(manifest, tmp_path / "out-b")
    assert receipt_a["output"]["rows"] == 2
    assert receipt_a["output"]["unique_lda_source_person_ids"] == 2
    assert receipt_a["education_blocking"] is False
    assert receipt_a["canonical_identity_promotions"] == 0
    assert receipt_a["output"]["sha256"] == receipt_b["output"]["sha256"]
    assert (tmp_path / "out-a" / "employment_candidate_coverage_25340.ndjson.gz").read_bytes() == (
        tmp_path / "out-b" / "employment_candidate_coverage_25340.ndjson.gz"
    ).read_bytes()


def test_optional_lane_adds_bounded_dated_candidate_without_promotion(tmp_path: Path) -> None:
    manifest, paths = _fixture(tmp_path)
    lane = tmp_path / "house.ndjson.gz"
    lane_receipt = tmp_path / "house_receipt.json"
    _write_rows(
        lane,
        [
            {
                "canonical_employment_fact": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "employing_office_candidate": "TEST OFFICE",
                "lda_source_person_id": "lda:lobbyist:1",
                "match_candidate_id": "candidate:1",
                "service_end_date_candidate": "2001-12-31",
                "service_start_date_candidate": "2001-01-01",
                "title_candidate": "COUNSEL",
            }
        ],
    )
    lane_receipt.write_bytes(
        _compact(
            {
                "canonical_employment_promotions": 0,
                "canonical_identity_promotions": 0,
                "output": {"sha256": _sha(lane)},
                "status": "PASS",
            }
        )
    )
    manifest_value = json.loads(paths["manifest"].read_text())
    manifest_value["candidate_lanes"] = [
        {"ledger": lane.name, "name": "house_final", "receipt": lane_receipt.name}
    ]
    paths["manifest"].write_bytes(_compact(manifest_value))
    receipt = merger.run(manifest, tmp_path / "out")
    assert receipt["lane_people_with_candidates"] == {"house_final": 1}
    with gzip.open(
        tmp_path / "out" / "employment_candidate_coverage_25340.ndjson.gz",
        "rt",
        encoding="utf-8",
    ) as stream:
        rows = [json.loads(line) for line in stream]
    first = rows[0]
    assert first["coverage_flags"]["has_any_bounded_employment_candidate"] is True
    assert first["identity_status"] == "REVIEW_REQUIRED"
    assert "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING" not in first["critical_path_gap_codes"]
    assert first["source_candidate_coverage"]["house_final"]["candidate_count"] == 1


@pytest.mark.parametrize("status_target", ["public", "lane"])
def test_non_pass_receipt_fails(tmp_path: Path, status_target: str) -> None:
    manifest, paths = _fixture(tmp_path)
    if status_target == "public":
        receipt = json.loads(paths["receipt"].read_text())
        receipt["status"] = "FAIL"
        paths["receipt"].write_bytes(_compact(receipt))
        validation = json.loads(paths["validation"].read_text())
        validation["comparisons"][0]["primary_manifest"][
            "public_employment_acquisition_queue_receipt.json"
        ] = _sha(paths["receipt"])
        paths["validation"].write_bytes(_compact(validation))
    else:
        lane = tmp_path / "lane.ndjson.gz"
        lane_receipt = tmp_path / "lane_receipt.json"
        _write_rows(lane, [])
        lane_receipt.write_bytes(_compact({"output": {"sha256": _sha(lane)}, "status": "FAIL"}))
        value = json.loads(paths["manifest"].read_text())
        value["candidate_lanes"] = [
            {"ledger": lane.name, "name": "house_final", "receipt": lane_receipt.name}
        ]
        paths["manifest"].write_bytes(_compact(value))
    with pytest.raises(merger.GateFailure, match="status is not PASS"):
        merger.run(manifest, tmp_path / "out")


def test_scope_duplication_and_loss_fail(tmp_path: Path) -> None:
    duplicate = [_public_row("lda:lobbyist:1", 1), _public_row("lda:lobbyist:1", 2)]
    manifest, _ = _fixture(tmp_path, duplicate)
    with pytest.raises(merger.GateFailure, match="duplicate public-scope"):
        merger.run(manifest, tmp_path / "out")


def test_scope_loss_fails(tmp_path: Path) -> None:
    manifest, paths = _fixture(tmp_path)
    value = json.loads(paths["manifest"].read_text())
    value["expected_scope_size"] = 3
    paths["manifest"].write_bytes(_compact(value))
    with pytest.raises(merger.GateFailure, match="public-scope conservation failed"):
        merger.run(manifest, tmp_path / "out")


def test_payload_hash_mismatch_fails(tmp_path: Path) -> None:
    manifest, paths = _fixture(tmp_path)
    rows = [_public_row("lda:lobbyist:1", 1), _public_row("lda:lobbyist:2", 2)]
    rows[0]["display_name"] = "TAMPERED"
    _write_rows(paths["queue"], rows)
    with pytest.raises(merger.GateFailure, match="payload hash mismatch"):
        merger.run(manifest, tmp_path / "out")


def test_canonical_promotion_in_candidate_row_fails(tmp_path: Path) -> None:
    manifest, paths = _fixture(tmp_path)
    lane = tmp_path / "lane.ndjson.gz"
    lane_receipt = tmp_path / "lane_receipt.json"
    _write_rows(
        lane,
        [
            {
                "canonical_employment_fact": True,
                "lda_source_person_id": "lda:lobbyist:1",
                "match_candidate_id": "candidate:promoted",
            }
        ],
    )
    lane_receipt.write_bytes(
        _compact(
            {
                "canonical_employment_promotions": 0,
                "canonical_identity_promotions": 0,
                "output": {"sha256": _sha(lane)},
                "status": "PASS",
            }
        )
    )
    value = json.loads(paths["manifest"].read_text())
    value["candidate_lanes"] = [
        {"ledger": lane.name, "name": "senate_final", "receipt": lane_receipt.name}
    ]
    paths["manifest"].write_bytes(_compact(value))
    with pytest.raises(merger.GateFailure, match="canonical fact promotion"):
        merger.run(manifest, tmp_path / "out")


def test_true_zero_canonical_verification_assertion_is_safe() -> None:
    merger.assert_no_canonical_promotion(
        {"assertions": {"zero_canonical_promotion_violations": True}},
        "verification",
    )
    with pytest.raises(merger.GateFailure, match="zero-canonical assertion failed"):
        merger.assert_no_canonical_promotion(
            {"assertions": {"zero_canonical_promotion_violations": False}},
            "verification",
        )


def test_senate_observed_report_interval_is_bounded_but_not_continuous() -> None:
    intervals = merger.extract_intervals(
        {
            "interval_continuity_asserted": False,
            "observed_report_intervals": [
                {"basis": "REPORT_PERIOD_ONLY", "end": "2023-03-31", "start": "2022-10-01"}
            ],
        }
    )
    assert intervals == [("2022-10-01", "2023-03-31", "REPORT_PERIOD_ONLY")]


def test_verification_must_bind_candidate_payload(tmp_path: Path) -> None:
    manifest, paths = _fixture(tmp_path)
    lane = tmp_path / "lane.ndjson.gz"
    lane_receipt = tmp_path / "lane_receipt.json"
    verification = tmp_path / "verification.json"
    _write_rows(lane, [])
    lane_receipt.write_bytes(
        _compact({"output": {"rows": 0, "sha256": _sha(lane)}, "status": "PASS"})
    )
    verification.write_bytes(
        _compact({"match_candidate_sha256": "0" * 64, "status": "PASS"})
    )
    value = json.loads(paths["manifest"].read_text())
    value["candidate_lanes"] = [
        {
            "ledger": lane.name,
            "name": "senate_final",
            "receipt": lane_receipt.name,
            "verification": verification.name,
        }
    ]
    paths["manifest"].write_bytes(_compact(value))
    with pytest.raises(merger.GateFailure, match="verification does not bind"):
        merger.run(manifest, tmp_path / "out")
