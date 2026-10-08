#!/usr/bin/env python3
"""Tests for the declaration-widened recovery tier builder and verifier.

Unit tests exercise the cross-clause guard against synthetic declarations that
reproduce ADJUDICATION.md defect 4, the year-strengthener tables, the Senate
person-key derivation, period normalisation, canonical NDJSON determinism and
the non-empty-output-directory refusal.  Generation-level tests run only when the
primary generation exists on disk, and check the tier's structural refusals:
E1 ranks below D1 and says so on every row, nothing is promoted anywhere, no
flagged-provenance office reaches a link file, the held rows are held, and the
builder and the independent verifier agree wherever they compute the same thing.
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

import build_declaration_widened_tier as builder  # noqa: E402
import verify_declaration_widened_tier as verifier  # noqa: E402

from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
)

GENERATION = HERE / "declaration_widened_tier_20260903_v1_primary"
TWIN = HERE / "declaration_widened_tier_20260903_v1_twin"
VERIFICATION = HERE / "declaration_widened_tier_20260903_v1_verification"
SCHEMA_PATH = (
    REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"
    / "declaration_widened_employment_link.schema.json"
)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _target(values, mentions):
    return {"covered_position_values": list(values),
            "declared_office_mentions": list(mentions)}


def _member(text, office_key):
    return {"kind": "MEMBER", "text": text, "office_keys": [office_key]}


def _committee(alias, text, office_key):
    return {"kind": "COMMITTEE", "alias_hit": alias, "text": text,
            "office_keys": [office_key]}


# ---------------------------------------------------------------------------
# the cross-clause guard
# ---------------------------------------------------------------------------


def test_guard_passes_when_the_anchor_sits_in_a_legislative_clause():
    target = _target(
        ["Legislative Assistant, Representative Larry Bucshon"],
        [_member("Larry Bucshon", "HON:B001275")],
    )
    result = builder.attachment_evidence(target, "HON:B001275")
    assert result["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
    assert result["cross_clause_basis"] == "CONTIGUOUS"


def test_guard_fires_on_the_defect_4_shape():
    """An office alias matching a clause that carries no legislative cue."""
    target = _target(
        ["Senior Adviser for Fair and Competitive Markets, USDA; "
         "Counsel to Commissioner Kara Stein, Securities and Exchange Commission"],
        [_member("Fair Competitive Markets", "SENATOR SOMEBODY")],
    )
    result = builder.attachment_evidence(target, "SENATOR SOMEBODY")
    assert result["cross_clause_status"] == "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"


def test_guard_is_fail_closed_when_the_anchor_is_nowhere_in_the_declaration():
    target = _target(["Chief of Staff, Governor of Oregon"],
                     [_member("Jeff Merkley", "SENATOR JEFF MERKLEY")])
    result = builder.attachment_evidence(target, "SENATOR JEFF MERKLEY")
    assert result["cross_clause_status"] == "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE"
    assert result["cross_clause_basis"] == "NONE"


def test_a_neighbouring_legislative_clause_does_not_rescue_the_attachment():
    """The cue must be in the SAME clause as the anchor, not merely nearby."""
    target = _target(
        ["Analyst, Acme Widgets Incorporated; Legislative Aide, Rep. Someone Else"],
        [_member("Acme Widgets Incorporated", "COMMITTEE:X")],
    )
    result = builder.attachment_evidence(target, "COMMITTEE:X")
    assert result["cross_clause_status"] == "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"


def test_a_second_declared_value_can_carry_the_attachment():
    """The Andrew Green case: value one is executive, value three names the member."""
    target = _target(
        ["Senior Adviser for Fair and Competitive Markets, USDA",
         "Senior Advisor, USDA; Counsel to Senator Jeff Merkley"],
        [_member("Jeff Merkley", "SENATOR JEFF MERKLEY")],
    )
    result = builder.attachment_evidence(target, "SENATOR JEFF MERKLEY")
    assert result["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"


def test_committee_anchor_is_the_alias_not_the_whole_value():
    """The unanchored behaviour being repaired: the mention text is the WHOLE value."""
    target = _target(
        ["Analyst, Acme Widgets; Staff, House Committee on Agriculture"],
        [_committee("COMMITTEE ON AGRICULTURE",
                    "Analyst, Acme Widgets; Staff, House Committee on Agriculture",
                    "COMMITTEE:AGRICULTURE")],
    )
    anchors = builder.declared_anchors(target, "COMMITTEE:AGRICULTURE")
    assert anchors == [("COMMITTEE", "COMMITTEE ON AGRICULTURE")]
    result = builder.attachment_evidence(target, "COMMITTEE:AGRICULTURE")
    assert result["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
    assert all("Acme" not in clause["clause"] for clause in result["supporting"])


def test_ampersand_and_stopwords_do_not_break_anchor_location():
    target = _target(
        ["Staff Director, House Committee on Science, Space & Technology"],
        [_committee("COMMITTEE ON SCIENCE SPACE AND TECHNOLOGY",
                    "whole value", "COMMITTEE:SST")],
    )
    result = builder.attachment_evidence(target, "COMMITTEE:SST")
    assert result["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"


def test_ordered_subsequence_recovers_an_interrupted_span():
    target = _target(
        ["Legislative Aide, Rep. Shelley Moore (R-WV) Capito"],
        [_member("Shelley Moore Capito", "HON:C001047")],
    )
    result = builder.attachment_evidence(target, "HON:C001047")
    assert result["cross_clause_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
    assert result["cross_clause_basis"] == "ORDERED_SUBSEQUENCE"


def test_builder_and_verifier_grade_attachments_identically():
    cases = [
        _target(["Legislative Assistant, Representative Larry Bucshon"],
                [_member("Larry Bucshon", "HON:B001275")]),
        _target(["Analyst, Acme Widgets; Aide, Rep. Someone Else"],
                [_member("Acme Widgets", "COMMITTEE:X")]),
        _target(["Chief of Staff, Governor of Oregon"],
                [_member("Jeff Merkley", "SENATOR JEFF MERKLEY")]),
        _target(["Staff Director, House Committee on Science, Space & Technology"],
                [_committee("COMMITTEE ON SCIENCE SPACE AND TECHNOLOGY",
                            "whole", "COMMITTEE:SST")]),
    ]
    keys = ["HON:B001275", "COMMITTEE:X", "SENATOR JEFF MERKLEY", "COMMITTEE:SST"]
    for target, key in zip(cases, keys):
        left = builder.attachment_evidence(target, key)
        right = verifier.grade_attachment(target, key)
        assert left["cross_clause_status"] == right["status"]
        assert left["cross_clause_basis"] == right["basis"]
        assert left["disclaimer_status"] == right["disclaimer"]


def test_the_guard_is_powered_on_a_synthetic_population():
    """A guard that cannot reject anything is not a guard."""
    targets = {
        "p1": _target(["Legislative Assistant, Representative Larry Bucshon"],
                      [_member("Larry Bucshon", "HON:B001275")]),
        "p2": _target(["Aide, Senator Bill Cassidy"],
                      [_member("Bill Cassidy", "SENATOR BILL CASSIDY")]),
    }
    power = builder.guard_power(targets, [("p1", "HON:B001275"),
                                          ("p2", "SENATOR BILL CASSIDY")])
    foreign = power["foreign_office_key_substitution"]
    assert foreign["trials"] > 0
    assert foreign["rejected"] == foreign["trials"]


# ---------------------------------------------------------------------------
# year strengthener
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "declared,payroll,expected",
    [
        ([2012, 2013], [2012, 2014], "OVERLAP"),
        ([2011, 2016], [2013], "RANGE_OVERLAP"),
        ([], [2012], "NONE"),
        ([2012], [], "NO_PAYROLL_YEARS"),
        ([2001, 2002], [2015, 2016], "NO_OVERLAP"),
    ],
)
def test_year_overlap_classification(declared, payroll, expected):
    assert builder.year_overlap(declared, payroll) == expected
    assert verifier.overlap_of(declared, payroll) == expected


def test_an_untestable_year_is_never_reported_as_corroboration():
    assert builder.E1_YEAR["NONE"] == "E1_YEAR_UNTESTABLE"
    assert builder.E1_YEAR["NO_PAYROLL_YEARS"] == "E1_YEAR_UNTESTABLE"
    assert builder.E1_YEAR["NO_OVERLAP"] == "E1_YEAR_CONTRADICTED"
    assert builder.E1_YEAR == verifier.E1_YEAR
    assert builder.D1_YEAR == verifier.D1_YEAR


# ---------------------------------------------------------------------------
# person keys and periods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("SMITH, JANE A", "SMITH|JANE|A"),
        ("O'BRIEN, PATRICK", "OBRIEN|PATRICK|"),
        ("LUCAS, JEFFREY K.", "LUCAS|JEFFREY|K"),
        ("NO COMMA HERE", None),
    ],
)
def test_senate_person_key_derivation(raw, expected):
    assert builder.senate_person_key(raw) == expected
    assert verifier.senate_triple(raw) == expected


def test_the_two_senate_key_shapes_reduce_to_one():
    long_form = "senate|SENATOR JOHN F. REED|CURRAN|DANIEL|P"
    assert builder.normalise_person_key("senate_all", long_form) == "CURRAN|DANIEL|P"
    assert verifier.canonical_person_key("senate_all", long_form) == "CURRAN|DANIEL|P"
    assert builder.normalise_person_key("house_member", "SOD:LUCAS|JEFFREY|K") == (
        "SOD:LUCAS|JEFFREY|K")


def test_house_member_period_prefers_the_service_span():
    entry = {"titles": {"AIDE"}, "quarters": {"2012Q1", "2012Q2"}, "raw": set(),
             "service_starts": {"2012-01-05"}, "service_ends": {"2012-06-30"},
             "spans": set(), "periods": set(), "years": set(),
             "container_kinds": set(), "bioguides": set(), "rows": 2}
    view = builder.payroll_view("house_member", entry)
    assert view["periods"] == [
        {"start": "2012-01-05", "end": "2012-06-30", "basis": "HOUSE_SOD_SERVICE_SPAN"}]
    assert view["years"] == [2012]


def test_house_member_period_falls_back_to_the_quarter_envelope():
    entry = {"titles": set(), "quarters": {"2012Q1", "2013Q4"}, "raw": set(),
             "service_starts": set(), "service_ends": set(), "spans": set(),
             "periods": set(), "years": set(), "container_kinds": set(),
             "bioguides": set(), "rows": 1}
    view = builder.payroll_view("house_member", entry)
    assert view["periods"] == [
        {"start": "2012-01-01", "end": "2013-12-31",
         "basis": "HOUSE_SOD_QUARTER_ENVELOPE"}]


def test_senate_periods_carry_the_report_period_basis():
    entry = {"titles": set(), "quarters": set(), "raw": set(), "service_starts": set(),
             "service_ends": set(), "spans": set(),
             "periods": {("2019-04-01", "2019-09-30")}, "years": {2019},
             "container_kinds": set(), "bioguides": set(), "rows": 1}
    view = builder.payroll_view("senate_all", entry)
    assert view["periods"] == [
        {"start": "2019-04-01", "end": "2019-09-30", "basis": "SENATE_REPORT_PERIOD"}]


def test_out_of_order_period_is_flagged_not_silently_accepted():
    flags = builder.check_periods(
        [{"start": "2015-01-01", "end": "2014-01-01", "basis": "SENATE_REPORT_PERIOD"}])
    assert flags == ["PERIOD_BOUNDS_OUT_OF_ORDER"]
    assert verifier.period_flags(
        [{"start": "2015-01-01", "end": "2014-01-01",
          "basis": "SENATE_REPORT_PERIOD"}]) == flags


def test_builder_and_verifier_agree_on_payroll_views():
    entry = {"titles": {"AIDE"}, "quarters": {"2012Q1"}, "raw": {"LUCAS,JEFFREY K"},
             "service_starts": {"2012-01-05"}, "service_ends": {"2012-03-31"},
             "spans": set(), "periods": set(), "years": set(),
             "container_kinds": {"member"}, "bioguides": {"B001275"}, "rows": 3}
    left = builder.payroll_view("house_member", entry)
    right = verifier.payroll_fields("house_member", {
        "titles": entry["titles"], "quarters": entry["quarters"], "raw": entry["raw"],
        "starts": entry["service_starts"], "ends": entry["service_ends"],
        "spans": set(), "periods": set(), "years": set(),
        "containers": entry["container_kinds"], "bioguides": entry["bioguides"],
        "rows": entry["rows"]})
    assert left["periods"] == right["periods"]
    assert left["titles"] == right["titles"]
    assert left["years"] == right["years"]
    assert left["container_kind"] == right["container"]


# ---------------------------------------------------------------------------
# determinism and immutability
# ---------------------------------------------------------------------------


def test_canonical_ndjson_is_byte_stable(tmp_path):
    rows = [{"b": 2, "a": 1}, {"a": 3, "b": 4}]
    left, right = tmp_path / "left.ndjson.gz", tmp_path / "right.ndjson.gz"
    builder.write_ndjson(left, rows)
    builder.write_ndjson(right, [dict(reversed(list(row.items()))) for row in rows])
    assert left.read_bytes() == right.read_bytes()
    with gzip.open(left, "rt", encoding="utf-8") as stream:
        assert stream.readline() == '{"a":1,"b":2}\n'


def test_prepare_output_refuses_a_non_empty_generation(tmp_path):
    existing = tmp_path / "generation"
    existing.mkdir()
    (existing / "rows.ndjson.gz").write_bytes(b"x")
    with pytest.raises(builder.BuildError):
        builder.prepare_output(existing)
    with pytest.raises(verifier.VerifyError):
        verifier.prepare_output(existing)


def test_prepare_output_accepts_a_fresh_path(tmp_path):
    staging = builder.prepare_output(tmp_path / "fresh")
    assert staging.is_dir()
    assert staging.name.startswith(".fresh.tmp-")


def test_office_provenance_refuses_an_undeclared_office():
    target = {"lda_source_person_id": "p1", "candidate_office_keys_house": ["HON:A"],
              "candidate_office_keys_senate": [],
              "flagged_candidate_office_keys_house": ["HON:B"],
              "flagged_candidate_office_keys_senate": []}
    assert builder.office_provenance_of(target, "HON:A") == "RESOLVED"
    assert builder.office_provenance_of(target, "HON:B") == "FLAGGED"
    with pytest.raises(builder.BuildError):
        builder.office_provenance_of(target, "HON:C")


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def row_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def test_schema_forbids_a_widened_row_that_claims_to_equal_d1(row_schema):
    generation = list(_rows(GENERATION / builder.WIDENED_FILENAME)) if (
        GENERATION / builder.WIDENED_FILENAME).is_file() else []
    if not generation:
        pytest.skip("generation not present")
    row = dict(generation[0])
    row["tier_rank_relative_to_d1"] = "EQUAL"
    with pytest.raises(SchemaValidationError):
        validate_instance(row, row_schema)


def test_schema_forbids_a_promoted_row(row_schema):
    files = [GENERATION / builder.WIDENED_FILENAME]
    if not files[0].is_file():
        pytest.skip("generation not present")
    row = dict(next(iter(_rows(files[0]))))
    row["canonical_employment_promoted"] = True
    with pytest.raises(SchemaValidationError):
        validate_instance(row, row_schema)


def test_schema_forbids_a_linked_row_that_failed_the_guard(row_schema):
    path = GENERATION / builder.WIDENED_FILENAME
    if not path.is_file():
        pytest.skip("generation not present")
    row = dict(next(iter(_rows(path))))
    row["guard_cross_clause_attachment_status"] = "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE"
    with pytest.raises(SchemaValidationError):
        validate_instance(row, row_schema)


# ---------------------------------------------------------------------------
# generation-level
# ---------------------------------------------------------------------------


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


needs_generation = pytest.mark.skipif(
    not (GENERATION / builder.RECEIPT_FILENAME).is_file(),
    reason="primary generation is not present",
)


@pytest.fixture(scope="module")
def generation():
    receipt_path = GENERATION / builder.RECEIPT_FILENAME
    if not receipt_path.is_file():
        pytest.skip("primary generation is not present")
    return {
        "receipt": json.loads(receipt_path.read_text(encoding="utf-8")),
        "widened": list(_rows(GENERATION / builder.WIDENED_FILENAME)),
        "recovered": list(_rows(GENERATION / builder.RECOVERED_FILENAME)),
        "held": list(_rows(GENERATION / builder.HELD_FILENAME)),
    }


@needs_generation
def test_every_emitted_row_validates_against_the_committed_schema(generation, row_schema):
    for key in ("widened", "recovered", "held"):
        for row in generation[key]:
            validate_instance(row, row_schema)


@needs_generation
def test_the_widened_tier_says_on_every_row_that_it_ranks_below_d1(generation):
    assert generation["widened"]
    for row in generation["widened"]:
        assert row["evidence_tier"] == builder.E1_TIER
        assert row["tier_rank_relative_to_d1"] == "BELOW"
        assert row["evidence_tier_family"] == "LINK_BELOW_D1"
        assert row["match_class"] == "WIDENED_GIVEN_SURNAME_EXACT"


@needs_generation
def test_every_widened_row_carries_its_firing_rule_and_that_rules_control_numbers(
        generation):
    for row in generation["widened"]:
        assert row["widening_rule"] in builder.SAFE_RULES
        assert row["widening_rule_control_unique_target_scope_rows"] == 0
        assert row["widening_rule_declared_unique_target_scope_rows"] > 0
        assert row["widening_rule_status_fpr_point_pct"] == 0.0
        assert row["widening_rule_status_fpr_upper95_pct"] > 0


@needs_generation
def test_nothing_is_promoted_anywhere(generation):
    for key in ("widened", "recovered", "held"):
        for row in generation[key]:
            assert row["canonical_eligible"] is False
            assert row["canonical_employment_promoted"] is False
            assert row["canonical_identity_promoted"] is False
            assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
            assert row["review_status"] == "REVIEW_REQUIRED"
    assert generation["receipt"]["canonical_identity_promotions"] == 0
    assert generation["receipt"]["canonical_employment_promotions"] == 0


@needs_generation
def test_no_link_sits_on_a_flagged_office_and_every_held_flag_row_does(generation):
    for row in generation["widened"] + generation["recovered"]:
        assert row["office_provenance"] == "RESOLVED"
    for row in generation["held"]:
        if row["hold_reason"] == builder.HOLD_FLAGGED:
            assert row["office_provenance"] == "FLAGGED"
            assert row["evidence_tier_family"] == "HELD"


@needs_generation
def test_the_held_rows_are_visible_but_never_linked(generation):
    linked = {row["lda_source_person_id"]
              for row in generation["widened"] + generation["recovered"]}
    for row in generation["held"]:
        assert row["lda_source_person_id"] not in linked
        assert row["hold_reason"] is not None
        assert row["tier_rank_relative_to_d1"] == "NOT_RANKED"
        assert row["resolved_payroll_person_key"]


@needs_generation
def test_every_link_is_unique_inside_its_declared_office(generation):
    for row in generation["widened"] + generation["recovered"]:
        assert row["in_office_tie_size"] == 1
        assert row["in_office_tie_size_basis"]


@needs_generation
def test_every_linked_row_passed_the_cross_clause_guard(generation):
    for row in generation["widened"] + generation["recovered"]:
        assert row["guard_cross_clause_attachment_status"] == (
            "CLAUSE_CARRIES_LEGISLATIVE_CUE")
        assert row["declared_office_supporting_clauses"]


@needs_generation
def test_the_cross_clause_audit_covers_every_row_it_built(generation):
    guard = generation["receipt"]["guards"]["cross_clause_attachment"]
    total = len(generation["widened"]) + len(generation["recovered"]) + len(
        generation["held"])
    assert guard["rows_audited"] == total
    assert sum(guard["status_counts"].values()) == total


@needs_generation
def test_the_guard_reports_its_own_power(generation):
    power = generation["receipt"]["guards"]["cross_clause_attachment"]["power"]
    foreign = power["foreign_office_key_substitution"]
    assert foreign["trials"] > 0
    assert foreign["rejected"] == foreign["trials"]


@needs_generation
def test_the_control_evidence_is_a_first_class_receipt_field(generation):
    control = generation["receipt"]["control_evidence"]
    pooled = control["pooled_four_rules"]
    assert pooled["declared_unique_targets"] == 72
    assert pooled["control_unique_targets"] == 0
    assert pooled["status_false_positive_rate_point_pct"] == 0.0
    assert control["searches_per_arm"] == 2783
    for name in builder.SAFE_RULES:
        assert control["per_rule"][name]["control_unique_target_scope_rows"] == 0


@needs_generation
def test_the_zero_is_reported_next_to_the_positive_control(generation):
    """A zero false-positive count means nothing without a fired positive control."""
    control = generation["receipt"]["control_evidence"]
    positive = control["positive_control"]
    assert positive["rule"] == builder.POSITIVE_CONTROL_RULE
    assert positive["control_unique_target_scope_rows"] > 0
    assert positive["status_false_positive_rate_point_pct"] > 50
    assert positive["never_used_to_recover_anything"] is True
    capability = control["control_arm_capability"]
    assert capability["control_office_pairs_with_a_strict_same_surname_person"] > 0


@needs_generation
def test_the_positive_control_rule_never_produced_a_row(generation):
    for row in generation["widened"]:
        assert row["widening_rule"] != builder.POSITIVE_CONTROL_RULE


@needs_generation
def test_the_compound_surname_refusal_is_recorded_with_its_forgone_yield(generation):
    refusal = generation["receipt"]["declared_refusals"]["S1_COMPOUND_SURNAME_RULE"]
    assert refusal["implemented"] is False
    assert refusal["forgone_yield_targets_ruled"] == builder.S1_FORGONE_YIELD_RULED
    assert refusal["reason"]
    assert refusal["reproducible_bracket"]


@needs_generation
def test_the_flagged_provenance_refusal_is_recorded(generation):
    refusal = generation["receipt"]["declared_refusals"]["A3_FLAGGED_OFFICE_PROVENANCE"]
    assert refusal["implemented_as_links"] is False
    assert refusal["rows_held"] == sum(
        1 for row in generation["held"]
        if row["hold_reason"] == builder.HOLD_FLAGGED)


@needs_generation
def test_a_multi_office_winner_declares_its_competitors(generation):
    for row in generation["widened"]:
        assert row["winner_selected_among_multiple_offices"] == bool(
            row["competing_office_hits"])
        for competitor in row["competing_office_hits"]:
            assert (competitor["office_key"], competitor["payroll_person_key"]) != (
                row["office_key"], row["resolved_payroll_person_key"])


@needs_generation
def test_the_receipt_hash_binds_every_input(generation):
    inputs = generation["receipt"]["inputs"]
    assert inputs
    for entry in inputs:
        assert len(entry["sha256"]) == 64
        assert entry["bytes"] > 0
    names = {entry["name"] for entry in inputs}
    for required in ("e3_recovered", "a3_rows", "control_newrules",
                     "control_newrules_per_target", "targets", "adjudication",
                     "house_personnel_observations", "row_schema"):
        assert required in names


@needs_generation
def test_the_receipt_reports_no_failures(generation):
    assert generation["receipt"]["failures"] == []
    assert generation["receipt"]["status"] == "PASS"


@pytest.mark.skipif(
    not (TWIN / builder.RECEIPT_FILENAME).is_file()
    or not (GENERATION / builder.RECEIPT_FILENAME).is_file(),
    reason="primary or twin generation is not present",
)
def test_primary_and_twin_are_byte_identical():
    for filename in (builder.WIDENED_FILENAME, builder.RECOVERED_FILENAME,
                     builder.HELD_FILENAME):
        assert (GENERATION / filename).read_bytes() == (TWIN / filename).read_bytes()


@pytest.mark.skipif(
    not (VERIFICATION / verifier.VERIFICATION_FILENAME).is_file(),
    reason="verification is not present",
)
def test_the_independent_verification_passed():
    payload = json.loads(
        (VERIFICATION / verifier.VERIFICATION_FILENAME).read_text(encoding="utf-8"))
    assert payload["failures"] == []
    assert payload["status"] == "PASS"
    assert all(check["status"] == "PASS" for check in payload["checks"])
