from datetime import date

import pytest

from audits.staffer_network.adjudicate_bulk_employment_candidates import (
    AdjudicationError,
    OFFICIAL_HOSTS,
    bounds_within_cutoff,
    clean_covered_candidate,
    clean_role_and_employer,
    consolidate_episodes,
    date_atom_bounds,
    exact_legilist_source_binding,
    raw_line_disposition,
    year_bounds,
)
from audits.staffer_network.verify_bulk_employment_adjudication import TOKEN_PATTERN


def _candidate(line: str, *, person_id: str = "100039") -> dict:
    return {
        "line": line,
        "source_url": (
            f"https://legilist.com/lda/contributions/lobbyist/{person_id}/joo-jin-ong/"
        ),
        "source_title": "Joo-Jin Ong - Federal Lobbyist | LegiList",
    }


def test_exact_legilist_binding_requires_numeric_id_and_ordered_name() -> None:
    candidate = _candidate("Senior staff member")
    assert exact_legilist_source_binding(
        candidate, "lda:lobbyist:100039", "JOO-JIN ONG"
    )
    assert not exact_legilist_source_binding(
        candidate, "lda:lobbyist:999", "JOO-JIN ONG"
    )
    reversed_title = {**candidate, "source_title": "Ong, Joo-Jin"}
    assert not exact_legilist_source_binding(
        reversed_title, "lda:lobbyist:100039", "JOO-JIN ONG"
    )


def test_legilist_disclosed_position_is_reviewed_not_rejected_or_dated() -> None:
    status, reasons = raw_line_disposition(
        _candidate("Senior Professional Staff Member, House Foreign Affairs, 2010-2014"),
        "lda:lobbyist:100039",
        "JOO-JIN ONG",
    )
    assert status == "REVIEW_REQUIRED"
    assert "EXACT_LEGILIST_SOURCE_PAGE_BINDING" in reasons
    assert "PAGE_YEARS_MUST_NOT_BE_USED_AS_EMPLOYMENT_DATES" in reasons


def test_navigation_and_contribution_header_are_rejected_before_source_binding() -> None:
    for line in (
        "Recipient / Honoree Legislator Payee / Committee Date Amount",
        "Bills Search by number, title, sponsor, chamber, or status Legislators",
    ):
        status, reasons = raw_line_disposition(
            _candidate(line), "lda:lobbyist:100039", "JOO-JIN ONG"
        )
        assert status == "REJECTED"
        assert reasons == ["KNOWN_NAVIGATION_GATE_OR_PLACEHOLDER_LINE"]


def test_page_level_dates_are_never_inputs_to_raw_line_disposition() -> None:
    candidate = {
        **_candidate("Generic position-free text"),
        "date_ranges": ["2021-2026"],
        "year_tokens": ["2021", "2026"],
    }
    status, reasons = raw_line_disposition(
        candidate, "lda:lobbyist:100039", "JOO-JIN ONG"
    )
    assert status == "REVIEW_REQUIRED"
    assert all("DATED" not in reason for reason in reasons)


def test_year_bounds_are_uncertain_and_half_open() -> None:
    assert year_bounds(2010, 2014) == {
        "valid_start_earliest": "2010-01-01",
        "valid_start_latest": "2010-12-31",
        "valid_end_earliest": "2014-01-02",
        "valid_end_latest": "2015-01-01",
        "start_precision": "year",
        "end_precision": "year",
        "asserted_current": False,
    }
    with pytest.raises(AdjudicationError):
        year_bounds(2015, 2014)


def test_current_end_is_censored_at_as_of() -> None:
    assert date_atom_bounds("present", "end", date(2026, 9, 1)) == (
        "2026-09-02",
        "2026-09-02",
        "day",
        True,
    )


def test_clean_covered_candidate_requires_one_role_container_and_closed_range() -> None:
    row = {
        "date_range_mentions": [{
            "explicit_start_year": 2010,
            "explicit_end_year": 2014,
            "open_ended_text": False,
            "review_flags": [],
        }],
        "role_title_mentions": [{
            "text": "Senior Professional Staff Member",
            "confidence": "HIGH",
            "generic_title_risk": False,
            "ambiguous_abbreviation": False,
        }],
        "office_employer_mentions": [
            {
                "text": "Committee on Foreign Affairs",
                "confidence": "HIGH",
                "entity_class": "COMMITTEE_CANDIDATE",
            },
            {
                "text": "U.S. House of Representatives",
                "confidence": "HIGH",
                "entity_class": "GOVERNMENT_BODY_CANDIDATE",
            },
        ],
    }
    bounds, title, employer = clean_covered_candidate(row)
    assert title == "Senior Professional Staff Member"
    assert employer == "Committee on Foreign Affairs"
    assert bounds["valid_end_latest"] == "2015-01-01"
    row["role_title_mentions"].append({
        "text": "Counsel",
        "confidence": "HIGH",
        "generic_title_risk": False,
        "ambiguous_abbreviation": False,
    })
    assert clean_covered_candidate(row) is None


def test_cutoff_rejects_future_uncertainty_window() -> None:
    assert not bounds_within_cutoff(year_bounds(2025, 2026), date(2026, 9, 1))
    assert bounds_within_cutoff(year_bounds(2024, 2025), date(2026, 9, 1))


def test_truncated_title_and_narrative_employer_are_quarantined() -> None:
    assert not clean_role_and_employer("CHIEF COUNSEL AND", "Senator Example")
    assert not clean_role_and_employer(
        "Legislative Director", "Office of the Republican Secretary. He"
    )
    assert clean_role_and_employer("Legislative Director", "Senator Example")


def test_legistorm_is_commercial_not_official_evidence() -> None:
    assert "legistorm.com" not in OFFICIAL_HOSTS
    assert "www.legistorm.com" not in OFFICIAL_HOSTS


def test_exact_episode_duplicates_union_support_without_double_counting() -> None:
    base = {
        "schema_id": "staffer-network-provisional-employment-episode-v2",
        "episode_id": "provisional:employment-episode:" + "a" * 64,
        "evidence_lanes": ["lda_covered_position_parse"],
        "decision_ids": ["adjudication:decision:" + "b" * 64],
        "lda_source_person_id": "lda:lobbyist:1",
        "display_name": "Example Person",
        "raw_employer": "Example Office",
        "raw_title": "Counsel",
        "raw_employer_variants": ["Example Office"],
        "raw_title_variants": ["Counsel"],
        "employer_candidate": "Example Office",
        "title_candidate": "Counsel",
        "valid_start_earliest": "2020-01-01",
        "valid_start_latest": "2020-12-31",
        "valid_end_earliest": "2021-01-02",
        "valid_end_latest": "2022-01-01",
        "start_precision": "year",
        "end_precision": "year",
        "asserted_current": False,
        "source_as_of": "2026-09-01",
        "source_urls": [],
        "source_candidate_ids": ["claim:1"],
        "support_candidate_ids": ["claim:1"],
        "support_digest": "unused",
        "identity_status": "SOURCE_NATIVE_ACCEPTED",
        "container_status": "LITERAL_REVIEW_REQUIRED",
        "episode_status": "PROVISIONAL",
        "temporal_semantics": "ASSERTED_EPISODE",
        "observation_intervals": [],
        "promotion_blockers": ["REVIEW"],
        "temporal_weight_eligible": False,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "complete_lifetime_employment_asserted": False,
    }
    second = {
        **base,
        "decision_ids": ["adjudication:decision:" + "c" * 64],
        "source_candidate_ids": ["claim:2"],
        "support_candidate_ids": ["claim:2"],
    }
    merged = consolidate_episodes([base, second])
    assert len(merged) == 1
    assert merged[0]["source_candidate_ids"] == ["claim:1", "claim:2"]
    assert len(merged[0]["decision_ids"]) == 2


@pytest.mark.parametrize(
    "payload",
    [
        b'{"password":"hunter2"}',
        b'{"api_key": "abc"}',
        b'{"access-token":"abc"}',
        b"secret='abc'",
    ],
)
def test_token_scan_detects_quoted_json_and_assignment_credentials(payload: bytes) -> None:
    assert TOKEN_PATTERN.search(payload)


def test_parenthesized_other_compensation_is_removed_from_title_candidate() -> None:
    from audits.staffer_network.adjudicate_bulk_employment_candidates import (
        normalize_title_candidate,
    )

    assert normalize_title_candidate("LEGISLATIVE ASSISTANT (OTHER COMPENSATION)") == (
        "LEGISLATIVE ASSISTANT"
    )
