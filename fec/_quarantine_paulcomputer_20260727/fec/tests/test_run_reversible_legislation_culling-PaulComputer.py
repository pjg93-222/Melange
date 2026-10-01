from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from fec.legislation_culling_integration_contract import (
    EVIDENCE_SCHEMA,
    MEMBERSHIP_SCHEMA as INPUT_MEMBERSHIP_SCHEMA,
)
from fec.run_reversible_legislation_culling import (
    ReversibleCullingError,
    append_restoration,
    build_generation,
)


SHA = "a" * 64
URL = "https://www.congress.gov/bill/117th-congress/house-bill/1"
TEXT_URL = URL + "/text"
EVENT_TIME = "2026-07-27T03:00:00Z"


def evidence(
    key: str = "117:hr:1",
    *,
    query_ids: tuple[str, ...] = ("q1", "q2"),
) -> dict:
    return {
        "schema": EVIDENCE_SCHEMA,
        "canonical_key": key,
        "candidate_preserved": True,
        "discovery": {
            "path": "candidate.ndjson",
            "sha256": SHA,
            "record_sha256": SHA,
        },
        "membership_query_ids": list(query_ids),
        "official_evidence": {
            "title": {
                "status": "available",
                "source_url": URL,
                "text_sha256": SHA,
            },
            "summary": {
                "status": "available",
                "source_url": URL + "/summary",
                "text_sha256": SHA,
            },
            "full_text": {
                "status": "accepted",
                "expected_url": TEXT_URL,
                "final_url": TEXT_URL,
                "body_sha256": SHA,
                "archive_reverified": True,
                "decompressed_body_sha256": SHA,
                "marker_bounded_text_sha256": SHA,
                "extraction_receipt_sha256": SHA,
                "cookie_values_persisted": False,
                "version_inventory": {
                    "expected_version_count": 1,
                    "reviewed_version_count": 1,
                    "all_versions_reviewed": True,
                },
                "validation": {
                    "status_200": True,
                    "exact_url": True,
                    "html_content_type": True,
                    "not_challenge": True,
                    "expected_main_marker": True,
                },
            },
        },
        "category_evidence": [
            {
                "category_id": f"category_{index:02d}",
                "title_reviewed": True,
                "summary_status_reviewed": True,
                "full_text_reviewed": True,
                "absence_is_neutral": True,
                "evidence_sha256": SHA,
            }
            for index in range(19)
        ],
        "keyword_review": {
            "ruleset_sha256": SHA,
            "title_reviewed": True,
            "summary_reviewed": True,
            "full_text_reviewed": True,
            "absence_is_neutral": True,
        },
        "stage": {
            "status": "available",
            "value": "introduced",
            "actions_sha256": SHA,
        },
        "relationships": {
            "status": "complete",
            "role_provenance_complete": True,
            "sponsor_count": 1,
            "original_cosponsor_count": 1,
            "cosponsor_count": 2,
            "edges_sha256": SHA,
        },
    }


def decision(
    query_id: str,
    disposition: str,
    *,
    key: str = "117:hr:1",
) -> dict:
    return {
        "schema": INPUT_MEMBERSHIP_SCHEMA,
        "canonical_key": key,
        "query_id": query_id,
        "disposition": disposition,
        "adjudication_state": "human_ratified",
        "automated_final_decision": False,
        "reviewer_confidence": "high",
        "reason": "Official title, summary, and every text version reviewed.",
        "reason_code": "official_evidence_reviewed",
        "reviewer": "reviewer",
        "reviewed_at": "2026-07-26T22:00:00-05:00",
        "decision_evidence_sha256": SHA,
        "evidence_sources_checked": [
            "official_title",
            "official_crs_summary",
            "official_full_text",
        ],
        "absence_used_as_exclusion_evidence": False,
        "full_text_rule_out_complete": True,
    }


def write_ndjson(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def setup_inputs(
    tmp_path: Path,
    *,
    evidence_rows: list[dict] | None = None,
    membership_rows: list[dict] | None = None,
    decision_rows: list[dict] | None = None,
) -> tuple[Path, Path, Path, Path]:
    evidence_path = tmp_path / "evidence.ndjson"
    memberships_path = tmp_path / "memberships.ndjson"
    decisions_path = tmp_path / "decisions.ndjson"
    root = tmp_path / "out"
    write_ndjson(
        evidence_path,
        evidence_rows if evidence_rows is not None else [evidence()],
    )
    write_ndjson(
        memberships_path,
        membership_rows
        if membership_rows is not None
        else [
            {"canonical_key": "117:hr:1", "query_id": "q1"},
            {"canonical_key": "117:hr:1", "query_id": "q2"},
        ],
    )
    write_ndjson(
        decisions_path,
        decision_rows
        if decision_rows is not None
        else [
            decision("q1", "exclude_false_positive"),
            decision("q2", "exclude_false_positive"),
        ],
    )
    return evidence_path, memberships_path, decisions_path, root


def run(tmp_path: Path, **overrides):
    evidence_path, memberships_path, decisions_path, root = setup_inputs(
        tmp_path,
        **overrides,
    )
    result = build_generation(
        evidence_path=evidence_path,
        memberships_path=memberships_path,
        decisions_path=decisions_path,
        root=root,
        event_time=EVENT_TIME,
    )
    return result, evidence_path, memberships_path, decisions_path, root


def read_generation_rows(result: dict, name: str) -> list[dict]:
    path = Path(result["receipt"]["outputs"][name]["path"])
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def test_every_explicit_exclusion_creates_reversible_global_junk(tmp_path):
    result, evidence_path, memberships_path, decisions_path, root = run(tmp_path)
    receipt = result["receipt"]
    assert receipt["counts"]["membership_partition"] == {
        "flagged": 0,
        "junk": 2,
        "keep": 0,
    }
    assert receipt["counts"]["candidate_partition"] == {
        "flagged": 0,
        "junk": 1,
        "keep": 0,
    }
    assert receipt["ledgers"]["new_junk_exclusions_appended"] == 1
    assert len((root / "junk_exclusions.ndjson").read_text().splitlines()) == 1
    assert (root / "restorations.ndjson").read_bytes() == b""
    candidates = read_generation_rows(result, "candidate_partition.ndjson")
    assert candidates[0]["all_memberships_explicitly_excluded"] is True
    assert candidates[0]["candidate_deletion_performed"] is False
    assert receipt["safety"]["main_corpus_write_performed"] is False
    assert evidence_path.exists()
    assert memberships_path.exists()
    assert decisions_path.exists()


def test_one_keep_vetoes_global_junk(tmp_path):
    result, *_ = run(
        tmp_path,
        decision_rows=[
            decision("q1", "include"),
            decision("q2", "exclude_false_positive"),
        ],
    )
    assert result["receipt"]["counts"]["candidate_partition"] == {
        "flagged": 0,
        "junk": 0,
        "keep": 1,
    }
    assert result["receipt"]["ledgers"]["new_junk_exclusions_appended"] == 0


def test_missing_or_incomplete_evidence_is_always_flagged(tmp_path):
    incomplete = evidence()
    incomplete["official_evidence"]["full_text"]["status"] = "missing"
    result, *_ = run(
        tmp_path,
        evidence_rows=[incomplete],
    )
    memberships = read_generation_rows(result, "membership_partition.ndjson")
    assert {row["disposition"] for row in memberships} == {"flagged"}
    assert all(
        "decision_not_finalizable_against_official_evidence"
        in row["flag_reasons"]
        for row in memberships
    )
    assert all(row["missing_evidence_can_produce_junk"] is False for row in memberships)
    assert result["receipt"]["counts"]["candidate_partition"]["flagged"] == 1
    assert result["receipt"]["counts"]["candidate_partition"]["junk"] == 0


def test_missing_candidate_evidence_is_flagged_not_fatal(tmp_path):
    result, *_ = run(tmp_path, evidence_rows=[])
    memberships = read_generation_rows(result, "membership_partition.ndjson")
    assert all(row["disposition"] == "flagged" for row in memberships)
    assert all(
        "missing_candidate_evidence" in row["flag_reasons"]
        for row in memberships
    )
    assert result["receipt"]["ledgers"]["new_junk_exclusions_appended"] == 0


def test_legacy_edge_vetoes_global_junk(tmp_path):
    evidence_path, memberships_path, decisions_path, root = setup_inputs(tmp_path)
    legacy_path = tmp_path / "legacy.ndjson"
    write_ndjson(
        legacy_path,
        [{"canonical_key": "117:hr:1", "source": "preserved_snapshot"}],
    )
    result = build_generation(
        evidence_path=evidence_path,
        memberships_path=memberships_path,
        decisions_path=decisions_path,
        legacy_edges_path=legacy_path,
        root=root,
        event_time=EVENT_TIME,
    )
    candidates = read_generation_rows(result, "candidate_partition.ndjson")
    assert candidates[0]["disposition"] == "flagged"
    assert candidates[0]["legacy_edge_present"] is True
    assert result["receipt"]["ledgers"]["new_junk_exclusions_appended"] == 0


def test_restoration_is_append_only_and_vetoes_future_junk(tmp_path):
    first, evidence_path, memberships_path, decisions_path, root = run(tmp_path)
    restoration = append_restoration(
        root=root,
        canonical_key="117:hr:1",
        reason="User restored this candidate for another review.",
        restored_by="User",
        restored_at="2026-07-27T03:05:00Z",
    )
    assert restoration["candidate_restored_edge_active"] is True
    assert len((root / "junk_exclusions.ndjson").read_text().splitlines()) == 1
    assert len((root / "restorations.ndjson").read_text().splitlines()) == 1

    second = build_generation(
        evidence_path=evidence_path,
        memberships_path=memberships_path,
        decisions_path=decisions_path,
        root=root,
        event_time="2026-07-27T03:10:00Z",
    )
    candidates = read_generation_rows(second, "candidate_partition.ndjson")
    assert candidates[0]["disposition"] == "flagged"
    assert candidates[0]["restored_edge_present"] is True
    assert second["receipt"]["ledgers"]["new_junk_exclusions_appended"] == 0
    assert first["generation_id"] != second["generation_id"]


def test_rerun_is_idempotent_and_does_not_duplicate_junk(tmp_path):
    first, evidence_path, memberships_path, decisions_path, root = run(tmp_path)
    second = build_generation(
        evidence_path=evidence_path,
        memberships_path=memberships_path,
        decisions_path=decisions_path,
        root=root,
        event_time="2026-07-27T04:00:00Z",
    )
    assert first["generation_id"] == second["generation_id"]
    assert second["receipt"]["ledgers"]["new_junk_exclusions_appended"] == 0
    assert len((root / "junk_exclusions.ndjson").read_text().splitlines()) == 1


def test_source_inputs_remain_byte_identical(tmp_path):
    evidence_path, memberships_path, decisions_path, root = setup_inputs(tmp_path)
    before = {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (evidence_path, memberships_path, decisions_path)
    }
    build_generation(
        evidence_path=evidence_path,
        memberships_path=memberships_path,
        decisions_path=decisions_path,
        root=root,
        event_time=EVENT_TIME,
    )
    assert {
        path: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in before
    } == before


def test_duplicate_decision_fails_closed(tmp_path):
    evidence_path, memberships_path, decisions_path, root = setup_inputs(
        tmp_path,
        decision_rows=[
            decision("q1", "include"),
            decision("q1", "exclude_false_positive"),
        ],
    )
    with pytest.raises(ReversibleCullingError, match="duplicate membership decision"):
        build_generation(
            evidence_path=evidence_path,
            memberships_path=memberships_path,
            decisions_path=decisions_path,
            root=root,
            event_time=EVENT_TIME,
        )


def test_tampered_append_only_ledger_fails_closed(tmp_path):
    _, evidence_path, memberships_path, decisions_path, root = run(tmp_path)
    ledger = root / "junk_exclusions.ndjson"
    body = ledger.read_text(encoding="utf-8")
    ledger.write_text(body.replace('"restorable":true', '"restorable":false'))
    with pytest.raises(ReversibleCullingError, match="content hash drift"):
        build_generation(
            evidence_path=evidence_path,
            memberships_path=memberships_path,
            decisions_path=decisions_path,
            root=root,
            event_time=EVENT_TIME,
        )


def test_flagged_review_csv_is_user_editable_and_authority_remains_ndjson(tmp_path):
    result, *_ = run(tmp_path, evidence_rows=[])
    csv_path = Path(result["receipt"]["outputs"]["flagged_memberships.csv"]["path"])
    ndjson_path = Path(
        result["receipt"]["outputs"]["flagged_memberships.ndjson"]["path"]
    )
    header = csv_path.read_text(encoding="utf-8-sig").splitlines()[0]
    assert "review_decision" in header
    assert "review_reason" in header
    assert len(ndjson_path.read_text().splitlines()) == 2
    assert result["receipt"]["xlsx_status"]["created"] is False