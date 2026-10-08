#!/usr/bin/env python3
"""Tests for the declaration-directed employment tier builder and verifier.

Unit tests cover the three defect guards against synthetic declarations, the
name-alias repair, period normalisation, canonical NDJSON determinism and the
non-empty-output-directory refusal.  Generation-level tests run only when the
primary generation exists on disk and check the tier's structural refusals:
no promotion anywhere, no FIRST_INITIAL row outside the non-evidential file,
no resolved payroll person on an ambiguous candidate, and the committed schema
accepting every emitted row.
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import sys

import pytest

HERE = Path(__file__).resolve().parent
REPOSITORY_ROOT = HERE.parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import build_declaration_directed_tier as builder  # noqa: E402
import verify_declaration_directed_tier as verifier  # noqa: E402

from fec.staffer_network.schema_validation import validate_instance  # noqa: E402

GENERATION = HERE / "declaration_directed_tier_20260903_v1_primary"
TWIN = HERE / "declaration_directed_tier_20260903_v1_twin"
SCHEMA_PATH = (
    REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"
    / "declaration_directed_employment_link.schema.json"
)


# ---------------------------------------------------------------------------
# guard 1: cross-clause attachment
# ---------------------------------------------------------------------------


def _target(values, mentions, years=None):
    return {
        "covered_position_values": list(values),
        "declared_office_mentions": list(mentions),
        "covered_position_year_tokens": list(years or []),
    }


def _member_mention(text, office_key, title=None):
    return {
        "kind": "MEMBER", "text": text, "title": title,
        "office_keys": [office_key], "chamber_hint": "house",
    }


def _committee_mention(alias, text, office_key):
    return {
        "kind": "COMMITTEE", "alias_hit": alias, "text": text,
        "office_keys": [office_key], "chamber": "house",
    }


def test_cross_clause_guard_passes_a_legislative_clause():
    target = _target(
        ["Senior Advisor, USDA; Counsel to Senator Jeff Merkley"],
        [_member_mention("Jeff Merkley", "SENATOR JEFF MERKLEY", "SENATOR")],
    )
    graded = builder.attachment_evidence(target, "SENATOR JEFF MERKLEY")
    assert graded["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
    assert graded["cross_clause_basis"] == "CONTIGUOUS"


def test_cross_clause_guard_fires_when_the_only_clause_is_executive():
    """The committee alias lands in a clause that names an executive employer."""
    target = _target(
        ["Senior Adviser for Fair and Competitive Markets, USDA Agriculture unit"],
        [_committee_mention(
            "AGRICULTURE",
            "Senior Adviser for Fair and Competitive Markets, USDA Agriculture unit",
            "COMMITTEE:AGRICULTURE",
        )],
    )
    graded = builder.attachment_evidence(target, "COMMITTEE:AGRICULTURE")
    assert graded["cross_clause_status"] == (
        "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
    )


def test_cross_clause_guard_is_fail_closed_when_the_anchor_is_absent():
    target = _target(
        ["Policy Director, a trade association"],
        [_member_mention("Frank Wolf", "HON:W000672", "REP")],
    )
    graded = builder.attachment_evidence(target, "HON:W000672")
    assert graded["cross_clause_status"] == "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE"


def test_ampersand_and_stopwords_do_not_break_anchor_location():
    """"Science, Space & Technology" must locate the alias "SCIENCE SPACE AND
    TECHNOLOGY"; without the normalisation a real match would be demoted."""
    value = "Professional Staff, House Committee on Science, Space & Technology"
    target = _target(
        [value],
        [_committee_mention("SCIENCE SPACE AND TECHNOLOGY", value,
                            "COMMITTEE:COMM ON SCIENCE SPACE AND TECH")],
    )
    graded = builder.attachment_evidence(
        target, "COMMITTEE:COMM ON SCIENCE SPACE AND TECH"
    )
    assert graded["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"


def test_ordered_subsequence_recovers_a_mention_with_an_interrupted_span():
    value = "Sr. Legislative Assistant, Rep. Shelley Moore Capito (R-WV) Jan. 2006"
    target = _target(
        [value],
        [_member_mention("Shelley Moore Capito Jan.", "HON:C001047", "REP")],
    )
    graded = builder.attachment_evidence(target, "HON:C001047")
    assert graded["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
    assert graded["cross_clause_basis"] == "ORDERED_SUBSEQUENCE"


def test_a_neighbouring_clause_does_not_rescue_the_attachment():
    """A legislative cue in a DIFFERENT clause must not count."""
    target = _target(
        ["Legislative Director, Rep. Someone Else; Senior Adviser, USDA Agriculture"],
        [_committee_mention(
            "AGRICULTURE",
            "Legislative Director, Rep. Someone Else; Senior Adviser, USDA Agriculture",
            "COMMITTEE:AGRICULTURE",
        )],
    )
    graded = builder.attachment_evidence(target, "COMMITTEE:AGRICULTURE")
    assert graded["cross_clause_status"] == (
        "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
    )


# ---------------------------------------------------------------------------
# guard 2: disclaimer
# ---------------------------------------------------------------------------


def test_disclaimer_guard_fires_when_every_supporting_clause_is_a_disclaimer():
    target = _target(
        ["*No lobby activity or contact made to US Senator John Cornyn's Office"],
        [_member_mention("John Cornyn", "SENATOR JOHN CORNYN", "SENATOR")],
    )
    graded = builder.attachment_evidence(target, "SENATOR JOHN CORNYN")
    assert graded["disclaimer_status"] == "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"


def test_disclaimer_guard_spares_a_filer_who_also_declared_the_position():
    target = _target(
        [
            "*No lobby activity or contact made to US Senator John Cornyn's Office",
            "Legislative Correspondent/Staff Assistant, Senator John Cornyn",
        ],
        [_member_mention("John Cornyn", "SENATOR JOHN CORNYN", "SENATOR")],
    )
    graded = builder.attachment_evidence(target, "SENATOR JOHN CORNYN")
    assert graded["disclaimer_status"] == "SOME_SUPPORTING_CLAUSES_ARE_DISCLAIMERS"


def test_disclaimer_detector_finds_a_disclaimer_anywhere_in_a_declaration():
    target = _target(
        ["*No lobby activity or contact made to Congressman Clay Higgins Office"],
        [],
    )
    assert builder.declaration_has_disclaimer_clause(target) is True


def test_year_token_caveat_flags_a_year_that_only_a_disclaimer_supplies():
    target = _target(
        [
            "Professional Staff, House Committee on Science",
            "*No lobby activity or contact made to Senator John Cornyn's Office "
            "thru 1/3/2023",
        ],
        [],
        years=["2023"],
    )
    assert builder.year_tokens_only_in_disclaimer_clauses(target) is True


def test_year_token_caveat_is_off_when_a_real_clause_carries_the_year():
    target = _target(
        ["Legislative Assistant, Rep. Frank Wolf, 2013", "*No lobby activity 2013"],
        [],
        years=["2013"],
    )
    assert builder.year_tokens_only_in_disclaimer_clauses(target) is False


# ---------------------------------------------------------------------------
# guard 3: middle-initial alias stripping
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def alias_rule():
    path = (
        REPOSITORY_ROOT / "data" / "staffer_network" / "reference"
        / "first_name_nicknames_v1.json"
    )
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    return builder.NameAliasRule(entries)


def test_inlined_go_by_name_is_not_a_middle_initial(alias_rule):
    repaired = builder.middle_initial_repair("ms KATHERINE KATIE MEYER", alias_rule)
    assert repaired["raw"] == "K"
    assert repaired["repaired"] == ""
    assert repaired["stripped"] == ["KATIE"]


def test_courtesy_title_and_suffix_are_stripped(alias_rule):
    repaired = builder.middle_initial_repair("mr CHARLES CHES GARRISON iv", alias_rule)
    assert repaired["middles"] == ["CHES"]


def test_a_real_middle_name_survives_the_alias_strip(alias_rule):
    repaired = builder.middle_initial_repair("ms ANJALI HELENA TADAVARTHY", alias_rule)
    assert repaired["repaired"] == "H"
    assert repaired["stripped"] == []


def test_maiden_surname_in_the_middle_slot_is_not_treated_as_an_alias(alias_rule):
    """The prescribed fix does not reach maiden surnames; that is measured, not hidden."""
    repaired = builder.middle_initial_repair("MEGAN SUSSMAN HERBER", alias_rule)
    assert repaired["repaired"] == "S"
    assert repaired["stripped"] == []


def test_alias_rule_matches_the_verifier_implementation(alias_rule):
    path = (
        REPOSITORY_ROOT / "data" / "staffer_network" / "reference"
        / "first_name_nicknames_v1.json"
    )
    entries = json.loads(path.read_text(encoding="utf-8"))["entries"]
    other = verifier.Aliases(entries)
    for name in (
        "ms KATHERINE KATIE MEYER", "mrs JACQUELINE JACKY USYK",
        "ZACHARY ZACH LAVEN", "MAIA HUNT ESTES", "PATRICIA (\"TRISH\") REILLY",
        "mr THOMAS TOMMY S ANDREWS",
    ):
        left = builder.middle_initial_repair(name, alias_rule)
        right = verifier.middle_initials(name, other)
        assert left["repaired"] == right["repaired"], name
        assert left["stripped"] == right["stripped"], name


# ---------------------------------------------------------------------------
# period normalisation
# ---------------------------------------------------------------------------


def test_house_member_period_uses_the_service_span():
    hit = {
        "payroll_service_start_min": "2012-08-06",
        "payroll_service_end_max": "2014-11-30",
        "payroll_quarters": ["2012Q3", "2014Q4"],
    }
    periods = builder.payroll_periods_for(hit, "house_member")
    assert periods == [{"start": "2012-08-06", "end": "2014-11-30",
                        "basis": "HOUSE_SOD_SERVICE_SPAN"}]


def test_house_member_period_falls_back_to_the_quarter_envelope():
    periods = builder.payroll_periods_for(
        {"payroll_quarters": ["2010Q2", "2009Q3"]}, "house_member"
    )
    assert periods == [{"start": "2009-07-01", "end": "2010-06-30",
                        "basis": "HOUSE_SOD_QUARTER_ENVELOPE"}]


def test_senate_periods_carry_the_report_period_basis():
    hit = {"payroll_periods": [{"start": "2011-04-01", "end": "2011-09-30"}]}
    periods = builder.payroll_periods_for(hit, "senate_all")
    assert periods == [{"start": "2011-04-01", "end": "2011-09-30",
                        "basis": "SENATE_REPORT_PERIOD"}]


def test_out_of_order_period_is_flagged_not_silently_accepted():
    flags = builder.check_periods(
        [{"start": "2014-01-01", "end": "2012-01-01", "basis": "SENATE_REPORT_PERIOD"}]
    )
    assert flags == ["PERIOD_BOUNDS_OUT_OF_ORDER"]


def test_builder_and_verifier_agree_on_periods():
    hit = {
        "payroll_spans": [
            {"service_start_min": "2011-01-03", "service_end_max": "2012-02-10"},
            {"service_start_min": "2009-07-01", "service_end_max": "2010-06-30"},
        ]
    }
    assert builder.payroll_periods_for(hit, "house_nonmember") == verifier.periods_of(
        hit, "house_nonmember"
    )


# ---------------------------------------------------------------------------
# io discipline
# ---------------------------------------------------------------------------


def test_canonical_ndjson_is_byte_stable(tmp_path):
    rows = [{"b": 2, "a": 1}, {"a": 3, "b": 4}]
    first = tmp_path / "one.ndjson.gz"
    second = tmp_path / "two.ndjson.gz"
    builder.write_ndjson(first, rows)
    builder.write_ndjson(second, rows)
    assert first.read_bytes() == second.read_bytes()
    with gzip.open(first, "rt", encoding="utf-8") as stream:
        assert stream.readline() == '{"a":1,"b":2}\n'


def test_prepare_output_refuses_a_non_empty_generation(tmp_path):
    output = tmp_path / "generation"
    output.mkdir()
    (output / "already_here.txt").write_text("x", encoding="utf-8")
    with pytest.raises(builder.BuildError):
        builder.prepare_output(output)


def test_prepare_output_accepts_a_fresh_path(tmp_path):
    staging = builder.prepare_output(tmp_path / "generation")
    assert staging.is_dir()


# ---------------------------------------------------------------------------
# generation-level structural refusals
# ---------------------------------------------------------------------------


def _load(name):
    path = GENERATION / name
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


needs_generation = pytest.mark.skipif(
    not (GENERATION / "declaration_directed_tier_receipt.json").is_file(),
    reason="primary generation not built",
)


@needs_generation
def test_every_emitted_row_validates_against_the_committed_schema():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    for name in (
        "declaration_directed_employment_links.ndjson.gz",
        "declaration_directed_candidates.ndjson.gz",
        "declaration_directed_non_evidential.ndjson.gz",
    ):
        for row in _load(name):
            validate_instance(row, schema)


@needs_generation
def test_nothing_is_promoted_anywhere():
    for name in (
        "declaration_directed_employment_links.ndjson.gz",
        "declaration_directed_candidates.ndjson.gz",
        "declaration_directed_non_evidential.ndjson.gz",
    ):
        for row in _load(name):
            assert row["canonical_eligible"] is False
            assert row["canonical_employment_promoted"] is False
            assert row["canonical_identity_promoted"] is False
            assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
            assert row["review_status"] == "REVIEW_REQUIRED"


@needs_generation
def test_receipt_pins_both_promotion_counters_to_zero():
    receipt = json.loads(
        (GENERATION / "declaration_directed_tier_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    assert receipt["canonical_identity_promotions"] == 0
    assert receipt["canonical_employment_promotions"] == 0
    assert receipt["status"] == "PASS"
    assert receipt["failures"] == []


@needs_generation
def test_first_initial_never_reaches_a_link_or_candidate_file():
    for name in (
        "declaration_directed_employment_links.ndjson.gz",
        "declaration_directed_candidates.ndjson.gz",
    ):
        assert all(row["match_class"] != "FIRST_INITIAL" for row in _load(name))
    non_evidential = _load("declaration_directed_non_evidential.ndjson.gz")
    assert non_evidential
    assert all(row["match_class"] == "FIRST_INITIAL" for row in non_evidential)
    assert all(
        row["evidence_tier"] == "NON_EVIDENTIAL_HIT_ONLY" for row in non_evidential
    )


@needs_generation
def test_first_initial_exclusion_carries_its_measured_error_rate():
    receipt = json.loads(
        (GENERATION / "declaration_directed_tier_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    excluded = receipt["exclusions"]["FIRST_INITIAL"]
    assert excluded["never_a_link_tier"] is True
    assert excluded["control_false_positive_rate_pct_point"] == pytest.approx(6.977,
                                                                              abs=0.01)
    assert excluded["control_false_positive_rate_pct_upper95"] == pytest.approx(
        20.38, abs=0.05
    )


@needs_generation
def test_d1_status_false_positive_rate_is_a_first_class_receipt_field():
    receipt = json.loads(
        (GENERATION / "declaration_directed_tier_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    rates = receipt["measured_error_rates"]
    assert rates["d1_status_false_positive_rate_point_pct"] == pytest.approx(0.235,
                                                                             abs=0.001)
    assert rates["d1_status_false_positive_rate_upper95_pct"] == pytest.approx(
        0.849, abs=0.001
    )
    assert rates["d1_status_fpr_control_d1"] == 2
    assert rates["d1_status_fpr_searches_per_arm"] == 2783


@needs_generation
def test_every_link_is_unique_in_its_declared_office():
    links = _load("declaration_directed_employment_links.ndjson.gz")
    assert links
    for row in links:
        assert row["in_office_tie_size"] == 1
        assert row["evidence_tier"] == "D1_DECLARED_OFFICE_EXACT_UNIQUE"
        assert row["match_class"] in {"EXACT_TRIPLE", "EXACT_PAIR"}
        assert row["resolved_payroll_person_key"]
        assert row["guard_cross_clause_attachment_status"] == (
            "CLAUSE_CARRIES_LEGISLATIVE_CUE"
        )


@needs_generation
def test_ambiguous_candidates_are_never_resolved():
    ambiguous = [
        row for row in _load("declaration_directed_candidates.ndjson.gz")
        if row["evidence_tier"] in {"D2_CANDIDATE", "D3M_CANDIDATE"}
    ]
    assert ambiguous
    for row in ambiguous:
        assert row["resolved_payroll_person_key"] is None
        assert row["in_office_tie_size"] >= 2
        # the whole contending set, never one arbitrary member of it
        assert len(row["candidate_payroll_person_keys"]) >= row["in_office_tie_size"]


@needs_generation
def test_d3_candidates_carry_the_strengthened_flag():
    d3 = [
        row for row in _load("declaration_directed_candidates.ndjson.gz")
        if row["evidence_tier"] == "D3_CANDIDATE"
    ]
    assert len(d3) == 183
    assert sum(1 for row in d3 if row["d3_strengthened"]) == 38
    assert all(row["match_class"] in {"NICKNAME", "VARIANT"} for row in d3)


@needs_generation
@pytest.mark.skipif(
    not (TWIN / "declaration_directed_employment_links.ndjson.gz").is_file(),
    reason="twin generation not built",
)
def test_primary_and_twin_are_byte_identical():
    for name in (
        "declaration_directed_employment_links.ndjson.gz",
        "declaration_directed_candidates.ndjson.gz",
        "declaration_directed_non_evidential.ndjson.gz",
    ):
        assert (GENERATION / name).read_bytes() == (TWIN / name).read_bytes(), name
