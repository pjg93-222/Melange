from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import build_a6_prose_release as builder
import verify_a6_prose_release as verifier


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------
NICKNAME_TABLE_PATH = (
    Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
    / "data"
    / "staffer_network"
    / "reference"
    / "first_name_nicknames_v1.json"
)


def mention(text: str, literal: str, **extra: object) -> dict:
    start = text.index(literal)
    out = {"span_start": start, "span_end": start + len(literal), "text": literal}
    out.update(extra)
    return out


def near_candidate_row(
    *,
    claim_text: str = "Legislative Assistant to Rep. Frank R. Wolf (2013-2014)",
    role_text: str = "Legislative Assistant",
    office_text: str = "Rep. Frank R. Wolf",
    date_text: str = "2013-2014",
    entity_class: str = "MEMBER_OFFICE_CANDIDATE",
    explicit_start_year: int | None = 2013,
    explicit_end_year: int | None = 2014,
    rejection_reasons: list[str] | None = None,
) -> dict:
    """A realistic upstream near-candidate row modelled on
    ``staffer-network-lda-conservative-bounded-episode-blocker-v1``.  Spans are
    derived from ``claim_text`` by construction, so R1 is true by default.
    The two universal blockers are present by default, matching the real
    corpus (every one of the 3,090 rows carries both), which is what pins
    that they do NOT exclude a row (this is the whole point of the lane)."""

    role = mention(
        claim_text,
        role_text,
        pattern_id="ROLE_TITLE_SIMPLE",
        generic_title_risk=False,
        ambiguous_abbreviation=False,
    )
    office = mention(
        claim_text, office_text, entity_class=entity_class, pattern_id="OFFICE_MEMBER_TITLE"
    )
    date_mention = mention(
        claim_text,
        date_text,
        explicit_start_year=explicit_start_year,
        explicit_end_year=explicit_end_year,
        review_flags=[],
        pattern_id="DATE_EXPLICIT_YEAR_RANGE",
    )
    return {
        "claim_text": claim_text,
        "role_title_mention": role,
        "office_employer_mention": office,
        "date_range_mention": date_mention,
        "rejection_reasons": (
            list(rejection_reasons)
            if rejection_reasons is not None
            else [
                "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
                "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
            ]
        ),
        "lda_source_person_id": "lda:lobbyist:100741",
        "source_pointer": {
            "claim_id": "lda:claim:100741:7",
            "source_claim_row_ordinal": 7,
            "source_filing_years": [2013, 2014],
        },
    }


def roster_candidate(
    first: str,
    last: str,
    *,
    nickname: str | None = None,
    official_full: str | None = None,
    terms: list[dict] | None = None,
    min_year: int = 2000,
    max_year: int = 2026,
    bioguide: str = "X000001",
) -> dict:
    """Matches the shape ``builder.load_roster`` emits: bioguide, first, last,
    last_tokens, nickname, official_full, min_year, max_year, terms."""

    return {
        "bioguide": bioguide,
        "first": first,
        "last": last,
        "last_tokens": builder.name_tokens(last),
        "nickname": nickname,
        "official_full": official_full,
        "min_year": min_year,
        "max_year": max_year,
        "terms": terms or [],
    }


# ---------------------------------------------------------------------------
# 1-2: the release rule and the universal blockers
# ---------------------------------------------------------------------------
def test_a_clean_row_is_released() -> None:
    released, excluded, _ = builder.classify_rows([near_candidate_row()])
    assert len(released) == 1
    assert excluded == []


def test_the_two_universal_blockers_do_not_exclude_a_row() -> None:
    row = near_candidate_row(
        rejection_reasons=[
            "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
            "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
        ]
    )
    released, excluded, _ = builder.classify_rows([row])
    assert len(released) == 1
    assert excluded == []


# ---------------------------------------------------------------------------
# 3: R4 excluding blockers
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("flag", builder.EXCLUDING_BLOCKERS)
def test_each_excluding_blocker_alone_excludes_the_row(flag: str) -> None:
    row = near_candidate_row(rejection_reasons=[flag])
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == [f"R4_{flag}"]


# ---------------------------------------------------------------------------
# 4-6: R1 same-string binding
# ---------------------------------------------------------------------------
def test_a_shifted_mention_span_fails_r1() -> None:
    row = near_candidate_row()
    row["role_title_mention"]["span_start"] += 1
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R1_SAME_STRING_BINDING_NOT_ESTABLISHED"]


def test_a_mention_span_outside_claim_text_bounds_fails_r1() -> None:
    row = near_candidate_row()
    text = row["role_title_mention"]["text"]
    row["role_title_mention"]["span_start"] = len(row["claim_text"])
    row["role_title_mention"]["span_end"] = len(row["claim_text"]) + len(text)
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R1_SAME_STRING_BINDING_NOT_ESTABLISHED"]


def test_a_missing_role_mention_text_fails_r1() -> None:
    row = near_candidate_row()
    row["role_title_mention"]["text"] = None
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R1_SAME_STRING_BINDING_NOT_ESTABLISHED"]


# ---------------------------------------------------------------------------
# 7: R2 entity class
# ---------------------------------------------------------------------------
def test_organization_candidate_entity_class_fails_r2() -> None:
    row = near_candidate_row(entity_class="ORGANIZATION_CANDIDATE")
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R2_OFFICE_NOT_MEMBER_OFFICE_OR_COMMITTEE"]


@pytest.mark.parametrize("entity_class", sorted(builder.RELEASABLE_ENTITY_CLASSES))
def test_member_office_and_committee_entity_classes_pass_r2(entity_class: str) -> None:
    row = near_candidate_row(entity_class=entity_class)
    released, excluded, _ = builder.classify_rows([row])
    assert len(released) == 1
    assert excluded == []


# ---------------------------------------------------------------------------
# 8-9: R3 explicit years and R5 year order
# ---------------------------------------------------------------------------
def test_a_null_explicit_end_year_fails_r3() -> None:
    row = near_candidate_row(explicit_end_year=None)
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R3_YEARS_NOT_BOTH_EXPLICIT"]


def test_start_year_after_end_year_fails_r5() -> None:
    row = near_candidate_row(explicit_start_year=2014, explicit_end_year=2013)
    released, excluded, _ = builder.classify_rows([row])
    assert released == []
    assert excluded[0]["exclusion_reasons"] == ["R5_START_YEAR_AFTER_END_YEAR"]


# ---------------------------------------------------------------------------
# 10: the trio agreement test
# ---------------------------------------------------------------------------
def test_the_verifier_agrees_with_the_builder_on_every_failure_mode() -> None:
    rows = [
        near_candidate_row(),
        near_candidate_row(rejection_reasons=["AMBIGUOUS_ROLE_ABBREVIATION"]),
        near_candidate_row(entity_class="ORGANIZATION_CANDIDATE"),
        near_candidate_row(explicit_end_year=None),
        near_candidate_row(explicit_start_year=2014, explicit_end_year=2013),
    ]
    shifted = near_candidate_row()
    shifted["role_title_mention"]["span_start"] += 1
    rows.append(shifted)

    for row in rows:
        released, excluded, _ = builder.classify_rows([row])
        builder_reasons = excluded[0]["exclusion_reasons"] if excluded else []
        assert verifier.independent_release_decision(row) == builder_reasons


# ---------------------------------------------------------------------------
# 11: nickname table
# ---------------------------------------------------------------------------
def test_the_nickname_table_drops_multi_formal_short_forms() -> None:
    table, stats = builder.load_nickname_table(NICKNAME_TABLE_PATH)
    for forms in table.values():
        assert len(set(forms)) == 1
    assert stats["entries_dropped_multi_formal"] > 0
    assert "jay" not in table


# ---------------------------------------------------------------------------
# 12-13: name splitting
# ---------------------------------------------------------------------------
def test_split_display_name_handles_first_last() -> None:
    assert builder.split_display_name("JOHN SMITH") == ("JOHN", "SMITH")


def test_split_display_name_handles_first_middle_last() -> None:
    assert builder.split_display_name("JOHN QUINCY SMITH") == ("JOHN", "SMITH")


def test_split_display_name_drops_a_trailing_suffix() -> None:
    assert builder.split_display_name("JOHN SMITH JR") == ("JOHN", "SMITH")


def test_split_display_name_keeps_a_hyphenated_name_as_one_token() -> None:
    # person_name_tokens() splits on WHITESPACE only and strips punctuation
    # INSIDE each token, which is exactly how the House payroll person_key is
    # built ('Aalim-Johnson' -> 'AALIMJOHNSON').  Splitting on the hyphen made
    # every hyphenated filer unmatchable: measured 10 of 10 such name-checkable
    # rows landed in NAME_ABSENT_FROM_DECLARED_OFFICE.
    assert builder.split_display_name("JOO-JIN ONG") == ("JOOJIN", "ONG")
    assert builder.split_display_name("KAIF AALIM-JOHNSON") == ("KAIF", "AALIMJOHNSON")
    assert builder.split_display_name("SHANNON O'HARE") == ("SHANNON", "OHARE")


def test_split_display_name_strips_a_leading_honorific() -> None:
    # 4,603 of the 25,340 LDA people carry a leading honorific in their
    # self-entered display name.  Reading 'mr' as the given name made the
    # payroll binding impossible: measured 190 of 190 honorific-prefixed
    # name-checkable rows landed in NAME_ABSENT_FROM_DECLARED_OFFICE.
    assert builder.split_display_name("mr JAKE OKEN-BERG") == ("JAKE", "OKENBERG")
    assert builder.split_display_name("ms ANGELA B BUCKINGHAM-MELTON") == (
        "ANGELA",
        "BUCKINGHAMMELTON",
    )
    assert builder.split_display_name("mr ANTHONY J. LEMMA iii") == ("ANTHONY", "LEMMA")
    assert builder.split_display_name("mr SMITH") == (None, None)


def test_split_payroll_comma_name_keeps_a_hyphenated_given_as_one_token() -> None:
    assert builder.split_payroll_comma_name("ONG, JOO-JIN") == ("JOOJIN", "ONG")
    assert builder.split_payroll_comma_name("AALIM-JOHNSON, KAIF") == (
        "KAIF",
        "AALIMJOHNSON",
    )


def test_split_display_name_returns_none_none_for_a_single_token() -> None:
    assert builder.split_display_name("MADONNA") == (None, None)


def test_split_payroll_comma_name_splits_last_comma_first() -> None:
    assert builder.split_payroll_comma_name("CZERWINSKI, JOHN") == ("JOHN", "CZERWINSKI")


# ---------------------------------------------------------------------------
# 14: payee name matching
# ---------------------------------------------------------------------------
def test_payee_name_matches_is_strict_on_a_different_given_name() -> None:
    entry = {"surname": "SMITH", "given": "ROBERT"}
    assert builder.payee_name_matches("JOHN", "SMITH", entry, {}) is None


def test_payee_name_matches_returns_exact_for_an_exact_match() -> None:
    entry = {"surname": "SMITH", "given": "JOHN"}
    assert builder.payee_name_matches("JOHN", "SMITH", entry, {}) == "EXACT_SURNAME_AND_GIVEN"


# ---------------------------------------------------------------------------
# 15-16: interval and quarter arithmetic
# ---------------------------------------------------------------------------
def test_touching_by_one_day_ranges_overlap() -> None:
    assert builder.intervals_overlap(
        date(2020, 1, 1), date(2020, 1, 10), date(2020, 1, 10), date(2020, 1, 20)
    )


def test_adjacent_non_touching_ranges_do_not_overlap() -> None:
    assert not builder.intervals_overlap(
        date(2020, 1, 1), date(2020, 1, 9), date(2020, 1, 10), date(2020, 1, 20)
    )


def test_a_reversed_range_never_overlaps() -> None:
    assert not builder.intervals_overlap(
        date(2020, 1, 10), date(2020, 1, 1), date(2020, 1, 1), date(2020, 1, 20)
    )


def test_quarter_bounds_of_q1_and_q4() -> None:
    assert builder.quarter_bounds("2013Q1") == (date(2013, 1, 1), date(2013, 3, 31))
    assert builder.quarter_bounds("2013Q4") == (date(2013, 10, 1), date(2013, 12, 31))


def test_quarter_bounds_returns_none_for_a_bad_string() -> None:
    assert builder.quarter_bounds("not-a-quarter") is None


# ---------------------------------------------------------------------------
# 17: refuse_non_empty
# ---------------------------------------------------------------------------
def test_refuse_non_empty_raises_on_a_directory_containing_a_file(tmp_path: Path) -> None:
    (tmp_path / "existing.txt").write_text("x")
    with pytest.raises(builder.GateFailure, match="output directory is nonempty"):
        builder.refuse_non_empty(tmp_path)


def test_refuse_non_empty_does_not_raise_on_an_empty_or_absent_directory(
    tmp_path: Path,
) -> None:
    builder.refuse_non_empty(tmp_path / "does-not-exist-yet")
    empty = tmp_path / "empty"
    empty.mkdir()
    builder.refuse_non_empty(empty)


# ---------------------------------------------------------------------------
# 18: write_ndjson_gz determinism
# ---------------------------------------------------------------------------
def test_write_ndjson_gz_is_byte_deterministic_across_two_tmp_paths(tmp_path: Path) -> None:
    rows = [{"b": 2, "a": 1}, {"a": 3, "b": 4}]
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"
    result_a = builder.write_ndjson_gz(out_a / "rows.ndjson.gz", rows)
    result_b = builder.write_ndjson_gz(out_b / "rows.ndjson.gz", rows)
    assert (out_a / "rows.ndjson.gz").read_bytes() == (out_b / "rows.ndjson.gz").read_bytes()
    assert result_a["sha256"] == result_b["sha256"]
    assert result_a["uncompressed_sha256"] == result_b["uncompressed_sha256"]


# ---------------------------------------------------------------------------
# 19: senate_office_matches_member
# ---------------------------------------------------------------------------
def test_senate_office_matches_member_on_a_multi_token_surname() -> None:
    candidate = roster_candidate("Catherine", "Cortez Masto")
    assert builder.senate_office_matches_member(
        "SENATOR CATHERINE CORTEZ MASTO", candidate, {}
    )


def test_senate_office_matches_member_rejects_a_surname_match_with_the_wrong_first_name() -> (
    None
):
    candidate = roster_candidate("Catherine", "Cortez Masto")
    assert not builder.senate_office_matches_member(
        "SENATOR JANE CORTEZ MASTO", candidate, {}
    )


def test_senate_office_matches_member_refuses_to_guess_through_ocr_damage() -> None:
    candidate = roster_candidate("Rand", "Paul")
    assert not builder.senate_office_matches_member("SENATOR RANDP AUL", candidate, {})


# ---------------------------------------------------------------------------
# 20: cross_check_episode
# ---------------------------------------------------------------------------
def test_cross_check_episode_reports_member_unresolved_when_bioguide_is_none() -> None:
    result = builder.cross_check_episode(
        bioguide=None,
        filer_given="JOHN",
        filer_surname="SMITH",
        start_year=2013,
        end_year=2014,
        chambers=["house"],
        house_index={},
        house_present=set(),
        senate_index={},
        table={},
    )
    assert result["status"] == "NOT_CHECKED_MEMBER_UNRESOLVED"


def test_cross_check_episode_reports_office_out_of_corpus_window_before_2009() -> None:
    result = builder.cross_check_episode(
        bioguide="W000001",
        filer_given="JOHN",
        filer_surname="SMITH",
        start_year=2001,
        end_year=2002,
        chambers=["house"],
        house_index={},
        house_present=set(),
        senate_index={},
        table={},
    )
    assert result["status"] == "OFFICE_OUT_OF_CORPUS_WINDOW"
