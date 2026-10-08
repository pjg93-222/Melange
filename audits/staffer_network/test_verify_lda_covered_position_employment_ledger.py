from __future__ import annotations

import verify_lda_covered_position_employment_ledger as verifier


def test_filing_url_template_is_exact_and_uuid_bound() -> None:
    filing_uuid = "0be1026f-81e2-457e-8acb-4c1d2a2147bc"
    assert verifier.filing_url(filing_uuid) == (
        "https://lda.senate.gov/filings/public/filing/"
        "0be1026f-81e2-457e-8acb-4c1d2a2147bc/print/"
    )


def test_exact_source_hash_contract_is_fully_pinned() -> None:
    assert set(verifier.EXPECTED_SOURCE_FILES) == {
        "source_native_lobbyists",
        "source_native_covered_position_occurrences",
        "materialized_person_universe",
        "materialized_source_fragments",
        "exact_span_candidate_mentions",
    }
    assert all(
        len(spec["sha256"]) == 64 and spec["bytes"] > 0
        for spec in verifier.EXPECTED_SOURCE_FILES.values()
    )


def test_promotion_and_completeness_scan_fails_closed() -> None:
    safe = {
        "canonical_employment_fact": False,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "complete_employment_history_asserted": False,
    }
    assert verifier.promotion_or_completeness_violations(safe, "safe") == []
    unsafe = dict(safe)
    unsafe["canonical_employment_fact"] = True
    unsafe["complete_employment_history_asserted"] = True
    failures = verifier.promotion_or_completeness_violations(unsafe, "unsafe")
    assert len(failures) == 2


def test_token_scan_detects_credentials_without_matching_secretary() -> None:
    assert verifier.TOKEN_PATTERN.search(b'{"api_key":"do-not-commit"}') is not None
    assert verifier.TOKEN_PATTERN.search(b'{"title":"Secretary of the Senate"}') is None


def test_legilist_numeric_id_is_path_bound_not_name_bound() -> None:
    assert verifier.legilist_numeric_id(verifier.LEGILIST_EXAMPLE_URL) == "147664"
    assert verifier.legilist_numeric_id(
        "https://legilist.com/lda/contributions/lobbyist/147664/different-slug/"
    ) == "147664"
