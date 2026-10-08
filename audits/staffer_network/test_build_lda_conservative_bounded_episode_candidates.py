from __future__ import annotations

from pathlib import Path

import pytest

import build_lda_conservative_bounded_episode_candidates as builder
import verify_lda_conservative_bounded_episode_candidates as verifier


def mention(text: str, literal: str) -> dict:
    start = text.index(literal)
    return {"span_start": start, "span_end": start + len(literal), "text": literal}


def safe_row() -> dict:
    text = "Counsel, Senate Finance Committee, 2001-2004"
    role = mention(text, "Counsel")
    role.update({"ambiguous_abbreviation": False, "generic_title_risk": False})
    office = mention(text, "Senate Finance Committee")
    date = mention(text, "2001-2004")
    date.update(
        {
            "explicit_end_year": 2004,
            "explicit_start_year": 2001,
            "open_ended_text": False,
            "pattern_id": "DATE_EXPLICIT_YEAR_RANGE",
            "review_flags": [],
        }
    )
    return {
        "claim_text": text,
        "date_range_mentions": [date],
        "normalization_review_flags": [],
        "office_employer_mentions": [office],
        "role_title_mentions": [role],
    }


def test_exact_safe_mentions_are_eligible() -> None:
    assert builder.rejection_reasons(safe_row()) == []


def test_boundary_and_date_linkage_flags_fail_closed() -> None:
    row = safe_row()
    row["normalization_review_flags"] = [
        "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
        "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
    ]
    assert builder.rejection_reasons(row) == [
        "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
        "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
    ]


@pytest.mark.parametrize(
    "flag",
    [
        "AMBIGUOUS_ROLE_ABBREVIATION",
        "PUNCTUATION_ONLY_CLAIM_TEXT",
        "REFERENCE_TO_PRIOR_FILING_NOT_EMPLOYMENT_FACT",
    ],
)
def test_ambiguity_reference_and_punctuation_flags_fail_closed(flag: str) -> None:
    row = safe_row()
    row["normalization_review_flags"] = [flag]
    assert flag in builder.rejection_reasons(row)


def test_role_and_date_mention_review_signals_fail_closed() -> None:
    row = safe_row()
    row["role_title_mentions"][0]["ambiguous_abbreviation"] = True
    row["role_title_mentions"][0]["generic_title_risk"] = True
    row["date_range_mentions"][0]["review_flags"] = ["REVIEW_DATE"]
    reasons = builder.rejection_reasons(row)
    assert "AMBIGUOUS_ROLE_ABBREVIATION" in reasons
    assert "GENERIC_ROLE_TITLE_RISK" in reasons
    assert "DATE_MENTION_REVIEW_FLAG_PRESENT" in reasons


def test_two_digit_year_is_never_expanded() -> None:
    row = safe_row()
    date = row["date_range_mentions"][0]
    date["text"] = "'01-'04"
    date["span_start"] = row["claim_text"].index("2001-2004")
    date["span_end"] = date["span_start"] + len(date["text"])
    date["explicit_start_year"] = None
    date["explicit_end_year"] = None
    date["pattern_id"] = "DATE_APOSTROPHE_YEAR_RANGE"
    reasons = builder.rejection_reasons(row)
    assert "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED" in reasons
    assert "DATE_RANGE_NOT_CLOSED_WITH_EXPLICIT_YEARS" in reasons


def test_span_round_trip_and_cardinality_fail_closed() -> None:
    row = safe_row()
    row["role_title_mentions"][0]["span_end"] += 1
    assert "ROLE_SPAN_ROUND_TRIP_FAILED" in builder.rejection_reasons(row)
    row = safe_row()
    row["office_employer_mentions"].append(dict(row["office_employer_mentions"][0]))
    assert builder.rejection_reasons(row) == ["OFFICE_EMPLOYER_MENTION_COUNT_NOT_ONE"]


def test_independent_verifier_agrees_on_gate_examples() -> None:
    examples = [safe_row()]
    boundary = safe_row()
    boundary["normalization_review_flags"] = ["ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED"]
    examples.append(boundary)
    ambiguous = safe_row()
    ambiguous["role_title_mentions"][0]["ambiguous_abbreviation"] = True
    examples.append(ambiguous)
    for row in examples:
        assert verifier.independent_rejection_reasons(row) == builder.rejection_reasons(row)


def test_sealed_hash_gate_accepts_exact_hash_and_rejects_drift(tmp_path: Path) -> None:
    source = tmp_path / "sealed.bin"
    source.write_bytes(b"sealed-input")
    expected = builder.sha(source)
    builder.require_sealed_hash(source, expected, "test")
    source.write_bytes(b"drifted-input")
    builder.sha.cache_clear()
    with pytest.raises(builder.GateFailure, match="sealed SHA-256 mismatch"):
        builder.require_sealed_hash(source, expected, "test")
