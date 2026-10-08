from __future__ import annotations

import a8_match_house_sod_1997q1_to_lda as builder
import a8_verify_house_sod_1997q1_lda_matches as verifier
import match_lda_house_payroll as a4_reference


def test_a8_normalization_is_exactly_the_a4_reference_grammar() -> None:
    lda_values = [
        "Gordon A. Holzberg Jr.",
        "José M. Muñoz III",
        "MARY ANN O'BRIEN",
    ]
    house_values = [
        "HOLZBERG, GORDON A JR",
        "MUÑOZ JOSÉ M III",
        "O'BRIEN MARY ANN",
    ]
    for value in lda_values:
        assert builder.normalized_tokens(value) == a4_reference.tokens(value)
        assert builder.lda_name(value) == a4_reference.queue_name(value)
    for value in house_values:
        assert builder.normalized_tokens(value) == a4_reference.tokens(value)
        assert builder.house_payee_name(value) == a4_reference.payroll_name(value)
    middle_pairs = [((), ()), (("A",), ()), (("ALAN",), ("A",)), (("A",), ("B",))]
    for left, right in middle_pairs:
        assert builder.middle_compatible(left, right) == a4_reference.middle_compatible(
            left, right
        )


def test_conservative_name_grammar_matches_a4_behavior() -> None:
    assert builder.lda_name("Gordon A. Holzberg Jr.") == (
        "GORDON",
        "HOLZBERG",
        ("A",),
    )
    assert builder.house_payee_name("HOLZBERG, GORDON A JR") == (
        "GORDON",
        "HOLZBERG",
        ("A",),
    )
    assert builder.house_payee_name("DE LA CRUZ, ANA") == (
        "LA",
        "DE",
        ("CRUZ", "ANA"),
    )


def test_middle_compatibility_is_conservative_and_classified() -> None:
    assert builder.middle_compatible((), ())
    assert builder.middle_compatible(("ALAN",), ())
    assert builder.middle_compatible(("ALAN",), ("A",))
    assert not builder.middle_compatible(("ALAN",), ("B",))
    assert builder.candidate_class((), ()) == "EXACT_NORMALIZED_FULL_NAME"
    assert (
        builder.candidate_class(("ALAN",), ())
        == "EXACT_FIRST_LAST_MIDDLE_UNSPECIFIED"
    )
    assert (
        builder.candidate_class(("ALAN",), ("A",))
        == "EXACT_FIRST_LAST_MIDDLE_INITIAL_COMPATIBLE"
    )


def test_independent_verifier_name_logic_agrees_on_boundary_cases() -> None:
    cases = [
        ("GORDON HOLZBERG", "HOLZBERG, GORDON", True),
        ("GORDON A HOLZBERG", "HOLZBERG, GORDON", True),
        ("GORDON ALAN HOLZBERG", "HOLZBERG, GORDON A", True),
        ("GORDON ALAN HOLZBERG", "HOLZBERG, GORDON B", False),
    ]
    for lda_raw, house_raw, expected in cases:
        lda_parsed = verifier.parse_lda(lda_raw)
        house_parsed = verifier.parse_house(house_raw)
        assert lda_parsed is not None and house_parsed is not None
        assert lda_parsed[:2] == house_parsed[:2]
        assert verifier.compatible(lda_parsed[2], house_parsed[2]) is expected


def test_compact_candidate_retains_ambiguity_and_zero_promotion() -> None:
    source = {
        "book_id": "vfE2RJJsCaAC",
        "candidate_id": "house-row:1",
        "employing_office_raw": "HON. EXAMPLE",
        "part": 2,
        "payee_raw": "HOLZBERG, GORDON",
        "period": "1997Q1",
        "period_end": "1997-03-31",
        "period_start": "1997-01-01",
        "service_end_date_candidate_iso": "1997-03-31",
        "service_end_date_raw": "03/31/97",
        "service_start_date_candidate_iso": "1997-01-03",
        "service_start_date_raw": "01/03/97",
        "source_pdf_page_number": 10,
        "source_pdf_row_y_milli": 100,
        "source_pdf_sha256": "a" * 64,
        "source_title": "Statement of Disbursements",
        "source_url": "https://example.test/source.pdf",
        "title_description_raw": "COUNSEL",
    }
    person = {
        "display_name": "GORDON A HOLZBERG",
        "lda_source_person_id": "lda:lobbyist:147664",
        "priority_bucket": "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION",
        "priority_queue_ordinal": 10,
        "sealed_queue_ordinal": 20,
    }
    row = builder.compact_candidate(source, person, ("A",), (), 2, 2)
    assert row["ambiguity_status"] == "MULTIPLE_LDA_CANDIDATES_REVIEW_REQUIRED"
    assert row["compatible_lda_candidate_count"] == 2
    assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
    assert row["canonical_person_id"] is None
    assert row["canonical_employment_fact"] is False
    assert row["canonical_employment_episode_id"] is None
    assert row["interval_continuity_asserted"] is False
    assert row["service_date_scope"] == "OBSERVED_ROW_BOUNDS_WITHIN_1997Q1_REPORT_ONLY"
