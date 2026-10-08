from audit_profile_content_completeness import (
    content_status,
    employment_evidence_state,
    lda_representation_status,
    source_profile_status,
)


def test_content_status_requires_substantive_evidence() -> None:
    assert content_status([]) == (
        "NO_SUBSTANTIVE_EMPLOYMENT_EVIDENCE",
        0,
        0,
        0,
    )


def test_content_status_ignores_dates_but_requires_employer_and_title() -> None:
    assert content_status([(True, True), (True, True)]) == (
        "FIELD_COMPLETE_ON_COLLECTED_ASSERTIONS",
        2,
        0,
        0,
    )


def test_source_profile_status_is_distinct_from_lifetime_attestation() -> None:
    assert source_profile_status([(True, True), (True, True)]) == (
        "SOURCE_PROFILE_ROLE_EMPLOYER_COMPLETE",
        2,
        0,
        0,
    )
    assert source_profile_status([]) == (
        "NO_STRUCTURED_SOURCE_PROFILE_EMPLOYMENT",
        0,
        0,
        0,
    )


def test_source_profile_status_requires_role_and_employer_on_every_assertion() -> None:
    assert source_profile_status([(True, True), (True, False)]) == (
        "SOURCE_PROFILE_ROLE_EMPLOYER_INCOMPLETE",
        2,
        0,
        1,
    )


def test_explicit_no_position_is_a_disposition_not_complete_employment() -> None:
    assert lda_representation_status([], set(), 1) == (
        "EXPLICIT_NO_POSITION_DISPOSITION",
        0,
    )


def test_claim_support_must_be_in_the_same_person_support_set() -> None:
    claim = "lda:employment-claim:v2:person-a"
    assert lda_representation_status([claim], {"lda:employment-claim:v2:person-b"}, 0) == (
        "SUBSTANTIVE_LDA_CLAIMS_NOT_FULLY_REPRESENTED",
        0,
    )


def test_silence_and_role_text_do_not_create_canonical_employment() -> None:
    assert employment_evidence_state(
        has_canonical=False,
        noncanonical_candidate_count=0,
        covered_has_employer=False,
        covered_has_role=False,
    ) == "NONE"
    assert employment_evidence_state(
        has_canonical=False,
        noncanonical_candidate_count=0,
        covered_has_employer=False,
        covered_has_role=True,
    ) == "DIRECT_ROLE_OR_POSITION_TEXT_ONLY"
    assert content_status([(False, True), (True, False)]) == (
        "FIELD_INCOMPLETE_ON_COLLECTED_ASSERTIONS",
        2,
        1,
        1,
    )
