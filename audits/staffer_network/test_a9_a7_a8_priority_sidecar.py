from __future__ import annotations

import hashlib
import json

import a9_build_a7_a8_priority_sidecar as subject
import a9_verify_a7_a8_priority_sidecar as verifier


def test_a7_fec_point_observation_never_changes_any_bucket() -> None:
    for bucket, rank in subject.BUCKET_RANK.items():
        revised_rank, revised_bucket, reason, _ = subject.revised_priority(
            bucket, True, False
        )
        assert revised_rank == rank
        assert revised_bucket == bucket
        assert reason == "A7_FEC_POINT_CONTEXT_ONLY_NO_BUCKET_CHANGE"


def test_a8_bounded_house_candidate_routes_p0_p1_p2_to_p3() -> None:
    for bucket in (
        "P0_NO_EMPLOYMENT_CANDIDATE",
        "P1_DATED_FORMER_POSITION_MISSING",
        "P2_BOUNDED_INTERVAL_MISSING",
    ):
        rank, revised, reason, _ = subject.revised_priority(bucket, False, True)
        assert rank == 3
        assert revised == subject.P3
        assert reason.startswith("A8_DATED_BOUNDED_FORMER_HOUSE_CANDIDATE")


def test_a8_keeps_existing_p3_in_p3() -> None:
    rank, revised, reason, _ = subject.revised_priority(subject.P3, False, True)
    assert (rank, revised) == (3, subject.P3)
    assert reason == "A8_CANDIDATE_ADDED_BASELINE_ALREADY_P3"


def test_evidence_combination_is_exact_and_ld203_free() -> None:
    assert subject.evidence_combination(False, False) == "NO_A7_FEC_OR_A8_CANDIDATE"
    assert subject.evidence_combination(True, False) == "A7_FEC_POINT_ONLY"
    assert subject.evidence_combination(False, True) == "A8_HOUSE_1997Q1_ONLY"
    assert (
        subject.evidence_combination(True, True)
        == "A7_FEC_POINT+A8_HOUSE_1997Q1"
    )
    for left in (False, True):
        for right in (False, True):
            assert "LD203" not in subject.evidence_combination(left, right)


def test_candidate_digest_is_sorted_unique_and_deterministic() -> None:
    expected = hashlib.sha256(
        json.dumps(["a", "b"], sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert subject.digest_values(["b", "a", "b"]) == expected


def test_sidecar_row_preserves_baseline_and_zero_promotion() -> None:
    baseline = {
        "coverage_flags": {"has_any_employment_candidate": False},
        "display_name": "EXAMPLE PERSON",
        "employment_provider_count": 0,
        "explicit_gap_codes": ["FORMER_POSITION_CANDIDATE_MISSING"],
        "lda_source_person_id": "lda:lobbyist:1",
        "priority_bucket": "P0_NO_EMPLOYMENT_CANDIDATE",
        "priority_queue_ordinal": 10,
        "priority_rank": 0,
        "provider_overlap_bucket": "NO_EMPLOYMENT_PROVIDER",
        "recommended_next_action": "baseline action",
        "sealed_queue_ordinal": 20,
    }
    fec = {
        "candidate_count": 1,
        "candidate_id_digest": "a" * 64,
        "distinct_employer_count": 1,
        "distinct_occupation_count": 1,
        "distinct_registrant_anchor_count": 1,
        "first_observation_date": "2025-01-01",
        "last_observation_date": "2025-01-01",
    }
    house = {
        "ambiguity_status_counts": {"SINGLE_LDA_CANDIDATE_NOT_IDENTITY_PROOF": 1},
        "candidate_class_counts": {"EXACT_NORMALIZED_FULL_NAME": 1},
        "candidate_count": 1,
        "candidate_id_digest": "b" * 64,
        "distinct_employing_office_count": 1,
        "distinct_source_personnel_row_count": 1,
        "distinct_title_count": 1,
        "earliest_service_start": "1997-01-03",
        "latest_service_end": "1997-03-31",
        "source_candidate_id_digest": "c" * 64,
    }
    _, row = subject.build_row(baseline, fec, house, "run-test")
    assert row["baseline_a5b"]["priority_bucket"] == baseline["priority_bucket"]
    assert row["revised_priority"]["priority_bucket"] == subject.P3
    assert row["a7_fec_employer_point_observations"]["gap_clearances"] == []
    assert row["a7_fec_employer_point_observations"]["employment_interval_asserted"] is False
    assert row["a7_fec_employer_point_observations"]["former_position_asserted"] is False
    assert row["a8_house_1997q1_candidates"]["identity_adjudicated"] is False
    assert row["adjudication_status"] == "REVIEW_REQUIRED"
    assert row["canonical_identity_promoted"] is False
    assert row["canonical_employment_promoted"] is False
    assert row["complete_lifetime_employment_asserted"] is False


def test_independent_verifier_agrees_on_all_priority_cases() -> None:
    for bucket in subject.BUCKET_RANK:
        for has_fec in (False, True):
            for has_house in (False, True):
                assert subject.revised_priority(
                    bucket, has_fec, has_house
                ) == verifier.expected_priority(bucket, has_fec, has_house)


def test_token_pattern_detects_secret_assignments_only() -> None:
    assert verifier.TOKEN_PATTERN.search(b'"api_key":"do-not-emit"')
    assert verifier.TOKEN_PATTERN.search(b"password='do-not-emit'")
    assert not verifier.TOKEN_PATTERN.search(b'"candidate_id_digest":"abc"')
    assert not verifier.TOKEN_PATTERN.search(b'"review_only":true')
