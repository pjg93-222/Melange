from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import pytest

import build_employment_adjudication_priority_queue as builder


def compact(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_rows(path: Path, rows: list[dict]) -> None:
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def row(lda_id: str, ordinal: int, bucket: int) -> dict:
    gaps = [
        "COMPLETE_LIFETIME_EMPLOYMENT_NOT_ATTESTED",
        "EMPLOYMENT_GAPS_NOT_ADJUDICATED",
        "HILL_HISTORY_NOT_EXHAUSTIVE",
        "IDENTITY_NOT_ADJUDICATED",
        "PRIVATE_SECTOR_HISTORY_NOT_EXHAUSTIVE",
    ]
    flags = {
        "has_any_bounded_employment_candidate": bucket == 3,
        "has_any_dated_employment_candidate": bucket >= 2,
        "has_any_employment_candidate": bucket >= 1,
    }
    if bucket == 0:
        gaps += [
            "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING",
            "DATED_FORMER_POSITION_CANDIDATE_MISSING",
            "FORMER_POSITION_CANDIDATE_MISSING",
        ]
    elif bucket == 1:
        gaps += [
            "BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING",
            "DATED_FORMER_POSITION_CANDIDATE_MISSING",
        ]
    elif bucket == 2:
        gaps += ["BOUNDED_EMPLOYMENT_INTERVAL_CANDIDATE_MISSING"]
    return {
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "complete_lifetime_employment_asserted": False,
        "coverage_flags": flags,
        "critical_path_gap_codes": gaps,
        "display_name": lda_id,
        "education": {"blocking": False, "diagnostic_gap_codes": []},
        "identity_status": "REVIEW_REQUIRED",
        "lda_source_person_id": lda_id,
        "sealed_queue_ordinal": ordinal,
        "source_candidate_coverage": {
            "public_external": {
                "candidate_count": int(bucket >= 1),
                "has_candidate": bucket >= 1,
            },
            "lda_registrant_association": {"candidate_count": 1, "has_candidate": True},
        },
    }


def fixture(tmp_path: Path, source_rows: list[dict]) -> tuple[Path, dict[str, Path]]:
    ledger = tmp_path / "integration.ndjson.gz"
    receipt = tmp_path / "integration_receipt.json"
    verification = tmp_path / "integration_verification.json"
    manifest = tmp_path / "manifest.json"
    write_rows(ledger, source_rows)
    receipt.write_bytes(
        compact(
            {
                "canonical_employment_promotions": 0,
                "canonical_identity_promotions": 0,
                "output": {"sha256": sha(ledger)},
                "status": "PASS",
            }
        )
    )
    verification.write_bytes(
        compact(
            {
                "hashes": {
                    "primary_payload_sha256": sha(ledger),
                    "primary_receipt_sha256": sha(receipt),
                },
                "status": "PASS",
            }
        )
    )
    manifest.write_bytes(
        compact(
            {
                "expected_scope_size": len(source_rows),
                "integration": {
                    "ledger": ledger.name,
                    "receipt": receipt.name,
                    "verification": verification.name,
                },
                "schema_id": builder.MANIFEST_SCHEMA,
            }
        )
    )
    return manifest, {"ledger": ledger, "manifest": manifest, "receipt": receipt, "verification": verification}


def test_priority_order_and_determinism(tmp_path: Path) -> None:
    manifest, _ = fixture(
        tmp_path,
        [row("lda:lobbyist:4", 4, 3), row("lda:lobbyist:2", 2, 1), row("lda:lobbyist:1", 1, 0), row("lda:lobbyist:3", 3, 2)],
    )
    first = builder.run(manifest, tmp_path / "a")
    second = builder.run(manifest, tmp_path / "b")
    assert first["bucket_counts"] == {
        "P0_NO_EMPLOYMENT_CANDIDATE": 1,
        "P1_DATED_FORMER_POSITION_MISSING": 1,
        "P2_BOUNDED_INTERVAL_MISSING": 1,
        "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION": 1,
    }
    assert first["output"]["sha256"] == second["output"]["sha256"]
    with gzip.open(
        tmp_path / "a" / "employment_acquisition_adjudication_priority_queue_25340.ndjson.gz",
        "rt",
        encoding="utf-8",
    ) as stream:
        output = [json.loads(line) for line in stream]
    assert [item["priority_rank"] for item in output] == [0, 1, 2, 3]
    assert all(item["adjudication_status"] == "REVIEW_REQUIRED" for item in output)
    assert all(item["education"]["blocking"] is False for item in output)


def test_explicit_gaps_and_provider_pointer_are_preserved(tmp_path: Path) -> None:
    source = row("lda:lobbyist:1", 1, 1)
    manifest, _ = fixture(tmp_path, [source])
    builder.run(manifest, tmp_path / "out")
    with gzip.open(
        tmp_path / "out" / "employment_acquisition_adjudication_priority_queue_25340.ndjson.gz",
        "rt",
        encoding="utf-8",
    ) as stream:
        output = json.loads(next(stream))
    assert output["explicit_gap_codes"] == sorted(source["critical_path_gap_codes"])
    assert output["provider_evidence_pointers"]["public_external"]["lda_source_person_id"] == "lda:lobbyist:1"
    assert output["context_provider_count"] == 1
    assert output["employment_provider_count"] == 1


def test_scope_loss_and_duplication_fail(tmp_path: Path) -> None:
    manifest, paths = fixture(tmp_path, [row("lda:lobbyist:1", 1, 0)])
    value = json.loads(paths["manifest"].read_text())
    value["expected_scope_size"] = 2
    paths["manifest"].write_bytes(compact(value))
    with pytest.raises(builder.GateFailure, match="scope loss"):
        builder.run(manifest, tmp_path / "loss")

    duplicate_dir = tmp_path / "duplicate"
    duplicate_dir.mkdir()
    manifest, _ = fixture(
        duplicate_dir,
        [row("lda:lobbyist:1", 1, 0), row("lda:lobbyist:1", 2, 0)],
    )
    with pytest.raises(builder.GateFailure, match="duplicate input"):
        builder.run(manifest, duplicate_dir / "out")


def test_nonpass_hash_drift_and_promotion_fail(tmp_path: Path) -> None:
    nonpass_dir = tmp_path / "nonpass"
    nonpass_dir.mkdir()
    manifest, paths = fixture(nonpass_dir, [row("lda:lobbyist:1", 1, 0)])
    receipt = json.loads(paths["receipt"].read_text())
    receipt["status"] = "FAIL"
    paths["receipt"].write_bytes(compact(receipt))
    with pytest.raises(builder.GateFailure, match="receipt is not PASS"):
        builder.run(manifest, nonpass_dir / "out")

    drift_dir = tmp_path / "drift"
    drift_dir.mkdir()
    manifest, paths = fixture(drift_dir, [row("lda:lobbyist:1", 1, 0)])
    paths["ledger"].write_bytes(paths["ledger"].read_bytes() + b"tamper")
    with pytest.raises(builder.GateFailure, match="payload hash mismatch"):
        builder.run(manifest, drift_dir / "out")

    promoted_dir = tmp_path / "promoted"
    promoted_dir.mkdir()
    promoted = row("lda:lobbyist:1", 1, 0)
    promoted["canonical_identity_promoted"] = True
    manifest, _ = fixture(promoted_dir, [promoted])
    with pytest.raises(builder.GateFailure, match="promotion field set"):
        builder.run(manifest, promoted_dir / "out")
