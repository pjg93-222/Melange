from __future__ import annotations

from audits.staffer_network.build_politico_payroll_direct_links import (
    BuildError,
    committee_signature,
    display_name_key,
    explicit_side,
    member_bioguides_from_roles,
    roster_markers,
    validate_profile_crawl,
)
import pytest
from types import SimpleNamespace


def test_name_key_handles_hyphenated_names_without_guessing_middle() -> None:
    assert display_name_key("Yaa-Sin Abdul-Qawiy") == ("yaa", "qawiy")


def test_committee_vocabulary_normalizes_known_source_differences() -> None:
    assert committee_signature("Fiscal Year 2025 Committee on Appropriations") == "APPROPRIATIONS"
    assert committee_signature("House Appropriations Committee Defense Subcommittee") == "APPROPRIATIONS"
    assert committee_signature("House Oversight and Government Reform Committee") == "OVERSIGHT AND ACCOUNTABILITY"
    assert committee_signature("Transportation-Infrastructure") == "TRANSPORTATION INFRASTRUCTURE"


def test_member_role_requires_exact_roster_display() -> None:
    roster = [
        {"member": "Alma Adams", "bioguide": "A000370", "chamber": "House"},
        {"member": "Emilia Sykes", "bioguide": "S001223", "chamber": "House"},
    ]
    roles = ["Legislative Assistant for Rep. Alma AdamsDemocraticNC-12"]
    assert member_bioguides_from_roles(roles, roster_markers(roster)) == [
        ("A000370", roles[0])
    ]


def test_explicit_side_is_source_label_only_and_four_valued() -> None:
    assert explicit_side("Majority Staff") == "MAJ"
    assert explicit_side("Minority Staff") == "MIN"
    assert explicit_side("Bipartisan Staff") == "BIPARTISAN"
    assert explicit_side("Democratic") is None


def test_terminal_profile_gate_rejects_partial_clean_crawl() -> None:
    profiles = {"one": {"profile_uuid": "one"}}
    verification = {
        "status": "PASS",
        "verification_failure_count": 0,
        "counts": {"profile_rows": 1, "unique_profiles_collected": 1},
        "coverage": {"all_profiles": {"completed": 1, "expected": 2, "unresolved": 1}},
        "crawl_state": {
            "queue_total": 2,
            "total_succeeded": 1,
            "total_failed": 0,
            "remaining": 1,
            "halted": False,
        },
    }
    with pytest.raises(BuildError, match="full profile crawl required"):
        validate_profile_crawl(profiles, verification, require_complete=True)


def test_bridge_build_refuses_a_nonempty_output_directory(tmp_path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "sentinel.txt").write_text("preserve me", encoding="utf-8")
    with pytest.raises(BuildError, match="output directory is not empty"):
        from audits.staffer_network.build_politico_payroll_direct_links import run

        run(SimpleNamespace(output=str(occupied)))
    assert (occupied / "sentinel.txt").read_text(encoding="utf-8") == "preserve me"
