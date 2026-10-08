#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the Part A tiered corroboration sidecar.

Synthetic fixtures only.  No live ledger is read: the end-to-end tests build a
complete miniature input tree under pytest's tmp_path, run the builder against
it, and then run the independent verifier over the resulting primary/twin pair.
"""

from __future__ import annotations

from datetime import date
import gzip
import importlib.util
import json
from pathlib import Path
import contextlib
import shutil
import sys

import pytest


LANE_DIR = Path(__file__).resolve().parent
REPO_ROOT = LANE_DIR.parents[1]
SCHEMA_DIR = REPO_ROOT / "fec" / "staffer_network" / "schemas"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
    validate_schema_definition,
)


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, LANE_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load("build_tiered_corroboration_sidecar")
verifier = _load("verify_tiered_corroboration_sidecar")

SCHEMA_FILES = {
    "record": "tiered_person_office_record.schema.json",
    "summary": "tiered_person_summary.schema.json",
    "episode": "filer_asserted_year_episode.schema.json",
    "registrant": "registrant_side_record.schema.json",
    "receipt": "tiered_corroboration_receipt.schema.json",
}


def schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / SCHEMA_FILES[name]).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
def test_all_five_schemas_are_valid_under_the_lane_validator():
    for name in SCHEMA_FILES:
        validate_schema_definition(schema(name))


def test_schema_ids_are_the_declared_strings():
    expected = {
        "record": "staffer-network-tiered-person-office-record-v1",
        "summary": "staffer-network-tiered-person-summary-v1",
        "episode": "staffer-network-filer-asserted-year-episode-v1",
        "registrant": "staffer-network-registrant-side-record-v1",
        "receipt": "staffer-network-tiered-corroboration-receipt-v1",
    }
    for name, schema_id in expected.items():
        document = schema(name)
        assert document["$id"] == schema_id
        assert document["properties"]["schema_id"]["const"] == schema_id


def test_every_schema_closes_additional_properties_and_pins_promotion():
    for name in SCHEMA_FILES:
        document = schema(name)
        assert document["additionalProperties"] is False
    for name in ("record", "summary", "episode", "registrant"):
        properties = schema(name)["properties"]
        assert properties["canonical_employment_promoted"] == {"const": False}
        assert properties["canonical_eligible"] == {"const": False}
        assert properties["review_status"] == {"const": "REVIEW_REQUIRED"}
    receipt_properties = schema("receipt")["properties"]
    assert receipt_properties["canonical_employment_promotions"] == {"const": 0}
    assert receipt_properties["canonical_identity_promotions"] == {"const": 0}
    assert receipt_properties["promotion_policy"] == {
        "const": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
    }


def test_schema_rejects_a_promoted_row():
    document = schema("record")
    with pytest.raises(SchemaValidationError):
        validate_instance(
            {"canonical_employment_promoted": True},
            {
                "type": "object",
                "properties": {
                    "canonical_employment_promoted": document["properties"][
                        "canonical_employment_promoted"
                    ]
                },
            },
        )


# ---------------------------------------------------------------------------
# Prong rules: office corroboration
# ---------------------------------------------------------------------------
def test_em_dash_con_row_continuation_artifact_is_stripped():
    raw = "2009 OFFICE OF THE SPEAKER—Con."
    assert builder.normalize_office(raw) == "OFFICE OF THE SPEAKER"
    assert verifier.house_normalize_office(raw) == "OFFICE OF THE SPEAKER"


def test_right_single_quotation_mark_is_normalized_to_an_apostrophe():
    raw = "VETERANS’ AFFAIRS"
    assert builder.normalize_office(raw) == "VETERANS' AFFAIRS"
    assert builder.normalize_office(raw) in builder.COMMITTEE_KEYWORDS


def test_middle_initial_punctuation_variants_share_one_office_group():
    assert (
        builder.office_group_key("2011 HON. STENY H HOYER")
        == builder.office_group_key("HON. STENY H. HOYER")
        == "HON:HOYER"
    )


def test_house_member_surname_prong_positive_and_negative():
    blob = "chief of staff to rep. hoyer, u.s. house of representatives".casefold()
    ok, method, form = builder.check_office_corroboration_house("HON. STENY H. HOYER", blob)
    assert (ok, method, form) == (True, "MEMBER_SURNAME_MATCH", "HOYER")
    ok, method, _ = builder.check_office_corroboration_house("HON. NANCY PELOSI", blob)
    assert (ok, method) == (False, "MEMBER_SURNAME_NOT_FOUND")


def test_house_committee_keyword_prong_positive_and_negative():
    blob = "professional staff member, committee on ways and means".casefold()
    ok, method, phrase = builder.check_office_corroboration_house(
        "COMMITTEE ON WAYS AND MEANS", blob
    )
    assert (ok, method, phrase) == (True, "COMMITTEE_KEYWORD_MATCH", "ways and means")
    ok, method, _ = builder.check_office_corroboration_house(
        "COMMITTEE ON AGRICULTURE", blob
    )
    assert (ok, method) == (False, "COMMITTEE_KEYWORD_NOT_FOUND")


def test_unmapped_house_office_family_can_never_corroborate():
    ok, method, _ = builder.check_office_corroboration_house(
        "TASK FORCE", "task force".casefold()
    )
    assert (ok, method) == (False, "COMMITTEE_FAMILY_UNMAPPED")


def test_office_corroboration_requires_a_whole_word():
    blob = "aide to rep. hoyerson".casefold()
    ok, _, _ = builder.check_office_corroboration_house("HON. STENY H. HOYER", blob)
    assert ok is False


def test_senate_office_token_rule_covers_every_documented_branch():
    assert builder.office_token_senate("SENATOR A. MITCHELL MCCONNELL, JR.") == "MCCONNELL"
    assert builder.office_token_senate("INTERN COMPENSATION - COLLINS") == "COLLINS"
    assert builder.office_token_senate("COMMITTEE ON APPROPRIATIONS") == "APPROPRIATIONS"
    assert builder.office_token_senate("APPROPRIATIONS") == "APPROPRIATIONS"
    # administrative payroll buckets yield no token and can never satisfy L3
    assert builder.office_token_senate("SGT @ ARMS - CAPITOL DIVISION") is None
    assert builder.office_token_senate("CONSULTANTS") is None


def test_senate_container_kinds():
    assert builder.container_kind_senate("SENATOR JONI ERNST") == "member_office"
    assert builder.container_kind_senate("APPROPRIATIONS") == "committee"
    assert builder.container_kind_senate("MAJORITY LEADER (D)") == "leadership"
    assert builder.container_kind_senate("CONSULTANTS") == "admin"
    assert builder.container_kind_senate("") == "unresolved"


def test_house_container_kinds():
    assert builder.container_kind_house("HON. STENY H. HOYER") == "member_office"
    assert builder.container_kind_house("COMMITTEE ON RULES") == "committee"
    assert builder.container_kind_house("OFFICE OF THE SPEAKER") == "leadership"
    assert builder.container_kind_house("CLERK OF THE HOUSE") == "admin"
    assert builder.container_kind_house("19TH DISTRICT OF FLORIDA") == "unresolved"


# ---------------------------------------------------------------------------
# Prong rules: name uniqueness
# ---------------------------------------------------------------------------
def test_h1_name_uniqueness_reconstruction_positive_and_negative():
    index = {
        ("JOSEPH", "ONEK"): [("lda:lobbyist:1", (), "JOSEPH ONEK")],
        ("JANE", "SMITH"): [
            ("lda:lobbyist:2", (), "JANE SMITH"),
            ("lda:lobbyist:3", (), "JANE A SMITH"),
        ],
    }
    assert builder.h1_name_uniqueness("ONEK,JOSEPH", index) == (1, 1)
    assert builder.h1_name_uniqueness("SMITH,JANE", index) == (2, 2)
    assert builder.h1_name_uniqueness("NOBODY,NEVER", index) == (None, None)


def test_middle_initial_compatibility_gates_the_candidate_pool():
    index = {("JANE", "SMITH"): [("lda:lobbyist:2", ("ANNE",), "JANE ANNE SMITH")]}
    assert builder.h1_name_uniqueness("SMITH,JANE A", index) == (1, 1)
    assert builder.h1_name_uniqueness("SMITH,JANE B", index) == (None, None)


def test_generational_suffixes_are_dropped_from_name_tokens():
    assert builder.name_tokens("SMITH,JOHN JR") == ("SMITH", "JOHN")


# ---------------------------------------------------------------------------
# Prong rules: chronology
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "max_end_year,expected",
    [(2021, "CONSISTENT"), (2022, "CONSISTENT"), (2023, "INCONSISTENT")],
)
def test_chronology_threshold_boundary_is_first_filing_year_plus_one(
    max_end_year, expected
):
    lane = {
        "p": {
            "rows": [{"name_ok": True, "office_ok": True, "end_year": max_end_year}],
            "offices": {},
        }
    }
    queue = {"p": {"filing_years": [2021, 2022], "covered_blob_casefolded": ""}}
    assert builder.house_lane_tiers(lane, queue)["p"]["chronology"] == expected


def test_chronology_is_unknown_without_filing_years_or_an_end_year():
    lane = {"p": {"rows": [{"name_ok": True, "office_ok": True, "end_year": None}], "offices": {}}}
    queue = {"p": {"filing_years": [2021], "covered_blob_casefolded": ""}}
    assert builder.house_lane_tiers(lane, queue)["p"]["chronology"] == "UNKNOWN"
    lane2 = {"p": {"rows": [{"name_ok": True, "office_ok": True, "end_year": 2015}], "offices": {}}}
    queue2 = {"p": {"filing_years": [], "covered_blob_casefolded": ""}}
    assert builder.house_lane_tiers(lane2, queue2)["p"]["chronology"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# Prong rules: split / contiguity
# ---------------------------------------------------------------------------
def test_senate_split_rule_requires_the_day_after_the_previous_period_end():
    from datetime import date

    clean = [
        (date(2021, 4, 1), date(2021, 9, 30)),
        (date(2021, 10, 1), date(2022, 3, 31)),
    ]
    gapped = [
        (date(2021, 4, 1), date(2021, 9, 30)),
        (date(2022, 4, 1), date(2022, 9, 30)),
    ]
    assert builder.periods_contiguous(clean) is True
    assert builder.periods_contiguous(gapped) is False


def test_house_contiguity_with_a_missing_quarter():
    assert builder.quarters_contiguous([(2017, 1), (2017, 2), (2017, 3)]) is True
    assert builder.quarters_contiguous([(2017, 1), (2017, 2), (2017, 4)]) is False
    assert builder.quarters_contiguous([(2017, 4), (2018, 1)]) is True


def test_duplicate_periods_do_not_create_extra_runs():
    from datetime import date

    intervals = [
        (date(2021, 4, 1), date(2021, 9, 30)),
        (date(2021, 4, 1), date(2021, 9, 30)),
        (date(2021, 10, 1), date(2022, 3, 31)),
    ]
    assert len(builder.merge_runs(intervals)) == 1


def test_envelope_widens_by_exactly_one_reporting_period():
    from datetime import date

    assert builder.quarter_bounds((2017, 1)) == (date(2017, 1, 1), date(2017, 3, 31))
    previous = builder.ordinal_to_quarter(builder.quarter_ordinal((2017, 1)) - 1)
    assert previous == (2016, 4)
    assert builder.quarter_bounds(previous)[0] == date(2016, 10, 1)
    window = builder.senate_window(date(2022, 11, 15))
    assert window == (date(2022, 10, 1), date(2023, 3, 31))
    assert builder.senate_previous_window(window) == (date(2022, 4, 1), date(2022, 9, 30))
    assert builder.senate_next_window(window) == (date(2023, 4, 1), date(2023, 9, 30))


# ---------------------------------------------------------------------------
# Strict-bioguide resolution (INV-6) and the nickname table
# ---------------------------------------------------------------------------
NICKNAME_TABLE = {"joe": ("joseph",), "bill": ("william",)}
ROSTER = {
    "SMITH": [
        {
            "bioguide": "S000001",
            "first": "Joseph",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "sen", "start": date(1995, 1, 3), "end": date(2015, 1, 3)}],
        },
        {
            "bioguide": "S000002",
            "first": "Maria",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "rep", "start": date(1999, 1, 6), "end": date(2003, 1, 3)}],
        },
    ],
    "HOYER": [
        {
            "bioguide": "H000874",
            "first": "Steny",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "rep", "start": date(1981, 5, 19), "end": date(2027, 1, 3)}],
        }
    ],
    "NELSON": [
        {
            "bioguide": "N000032",
            "first": "William",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "sen", "start": date(2001, 1, 3), "end": date(2019, 1, 3)}],
        },
        {
            "bioguide": "N000100",
            "first": "Bill",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "rep", "start": date(1847, 12, 6), "end": date(1851, 3, 3)}],
        },
    ],
}

# Helper so the many pure-name-matching assertions below (unaffected by the
# INV-6 term-window extension) don't have to repeat chamber=None,
# window_start=None, window_end=None: passing no window means the hard
# constraint does not apply, matching v1 behavior exactly.
def _resolve(module, first, surname, roster=ROSTER, nickname_table=NICKNAME_TABLE, **window):
    kwargs = {"chamber": None, "window_start": None, "window_end": None}
    kwargs.update(window)
    fn = module.resolve_member_bioguide if hasattr(module, "resolve_member_bioguide") else module.resolve_bioguide
    return fn(first, surname, roster, nickname_table, **kwargs)


def test_nickname_table_resolves_joe_to_joseph():
    assert builder.nickname_expansions("Joe", NICKNAME_TABLE) == {"joe", "joseph"}
    assert _resolve(builder, "JOE", "SMITH") == (
        "S000001",
        "STRICT_ROSTER_SURNAME_AND_FIRST_NAME",
    )


def test_unique_surname_resolves_without_a_first_name():
    assert _resolve(builder, None, "HOYER") == (
        "H000874",
        "STRICT_ROSTER_UNIQUE_SURNAME_NO_FIRST_NAME_IN_OFFICE_STRING",
    )


def test_strict_bioguide_refuses_every_ambiguous_or_fuzzy_case():
    assert _resolve(builder, None, "SMITH") == (
        None,
        "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME",
    )
    assert _resolve(builder, "BILL", "NELSON") == (
        None,
        "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE",
    )
    assert _resolve(builder, "XAVIER", "SMITH") == (
        None,
        "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER",
    )
    assert _resolve(builder, "JOE", "NOTAMEMBER") == (
        None,
        "UNRESOLVED_SURNAME_NOT_IN_ROSTER",
    )
    # a prefix is not a match: "Jos" must not resolve to "Joseph"
    assert _resolve(builder, "JOS", "SMITH")[0] is None


def test_verifier_resolution_agrees_with_the_builder():
    for first, surname in (
        ("JOE", "SMITH"),
        (None, "HOYER"),
        (None, "SMITH"),
        ("BILL", "NELSON"),
        ("XAVIER", "SMITH"),
    ):
        assert _resolve(builder, first, surname) == _resolve(verifier, first, surname)


# ---------------------------------------------------------------------------
# INV-6 extension (generation v2, 2026-09-02): nickname-field/official_full
# resolution forms and the term-window hard constraint.
# ---------------------------------------------------------------------------
NELSON_TERM_ROSTER = {
    "NELSON": [
        {
            "bioguide": "N000032",
            "first": "Bill",
            "nickname": None,
            "official_full": "Bill Nelson",
            "terms": [
                {"type": "rep", "start": date(1979, 1, 15), "end": date(1991, 1, 3)},
                {"type": "sen", "start": date(2001, 1, 3), "end": date(2019, 1, 3)},
            ],
        },
        {
            "bioguide": "N000045",
            "first": "William",
            "nickname": None,
            "official_full": None,
            "terms": [
                {"type": "rep", "start": date(1847, 12, 6), "end": date(1851, 3, 3)},
            ],
        },
    ]
}


def test_bill_nelson_resolves_via_term_window_disambiguation():
    """Both roster Nelsons fold to the same bill/william name class (one is
    literally 'Bill', the other 'William', and the nickname table equates
    them), so plain first-name matching is ambiguous.  Only N000032 has a
    Senate term overlapping the 2013 observation -- that is what resolves
    'SENATOR BILL NELSON' to N000032 rather than leaving it unresolved.
    """
    kwargs = dict(
        first="BILL",
        surname="NELSON",
        roster=NELSON_TERM_ROSTER,
        nickname_table=NICKNAME_TABLE,
        chamber="senate",
        window_start=date(2013, 3, 1),
        window_end=date(2013, 6, 30),
    )
    expected = ("N000032", "STRICT_ROSTER_SURNAME_FIRST_NAME_AND_TERM_WINDOW")
    assert builder.resolve_member_bioguide(**kwargs) == expected
    assert verifier.resolve_bioguide(**kwargs) == expected


def test_term_window_mismatch_when_no_nelson_term_covers_the_observation():
    kwargs = dict(
        first="BILL",
        surname="NELSON",
        roster=NELSON_TERM_ROSTER,
        nickname_table=NICKNAME_TABLE,
        chamber="senate",
        window_start=date(1900, 1, 1),
        window_end=date(1900, 6, 30),
    )
    expected = (None, "TERM_WINDOW_MISMATCH")
    assert builder.resolve_member_bioguide(**kwargs) == expected
    assert verifier.resolve_bioguide(**kwargs) == expected


def test_term_window_mismatch_on_a_single_unambiguous_name_match():
    """Surname and first name match exactly one roster candidate, but the
    record's observation window predates every term on file -- this is a
    named unresolved reason, not a resolved bioguide.
    """
    kwargs = dict(
        first="STENY",
        surname="HOYER",
        roster=ROSTER,
        nickname_table=NICKNAME_TABLE,
        chamber="house",
        window_start=date(1970, 1, 1),
        window_end=date(1970, 3, 31),
    )
    expected = (None, "TERM_WINDOW_MISMATCH")
    assert builder.resolve_member_bioguide(**kwargs) == expected
    assert verifier.resolve_bioguide(**kwargs) == expected


NICKNAME_ONLY_ROSTER = {
    "JONES": [
        {
            "bioguide": "J999999",
            "first": "Robert",
            "nickname": None,
            "official_full": None,
            "terms": [{"type": "sen", "start": date(2001, 1, 3), "end": date(2007, 1, 3)}],
        }
    ]
}


def test_nickname_only_resolution_bob_to_robert():
    """'Bob' only resolves to roster first name 'Robert' because the
    nickname table maps it there -- remove the table entry and the same
    surname+first-name+term-window inputs go unresolved.
    """
    kwargs = dict(
        first="BOB",
        surname="JONES",
        roster=NICKNAME_ONLY_ROSTER,
        chamber="senate",
        window_start=date(2003, 1, 1),
        window_end=date(2003, 6, 30),
    )
    with_table = builder.resolve_member_bioguide(nickname_table={"bob": ("robert",)}, **kwargs)
    assert with_table == ("J999999", "STRICT_ROSTER_SURNAME_AND_FIRST_NAME")
    assert verifier.resolve_bioguide(nickname_table={"bob": ("robert",)}, **kwargs) == with_table

    without_table = builder.resolve_member_bioguide(nickname_table={}, **kwargs)
    assert without_table == (None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER")
    assert verifier.resolve_bioguide(nickname_table={}, **kwargs) == without_table


# ---------------------------------------------------------------------------
# A6 flag exclusion
# ---------------------------------------------------------------------------
def test_a6_excluded_flags_are_exactly_the_four_named_flags():
    assert set(builder.A6_EXCLUDED_FLAGS) == {
        "AMBIGUOUS_ROLE_ABBREVIATION",
        "DATE_RANGE_REVERSED",
        "MENTION_SPANS_OVERLAP",
        "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED",
    }
    assert set(builder.A6_EXCLUDED_FLAGS) == set(verifier.A6_EXCLUDED_FLAGS)


def _a6_row(person, claim, entity_class, start, end, reasons):
    return {
        "lda_source_person_id": person,
        "office_employer_mention": {"entity_class": entity_class, "text": "U.S. Senator Joe Smith"},
        "date_range_mention": {"explicit_start_year": start, "explicit_end_year": end},
        "role_title_mention": {"text": "Regional Director"},
        "rejection_reasons": [
            "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
            "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
            *reasons,
        ],
        "source_pointer": {"claim_id": claim},
    }


def test_a6_release_rule_excludes_flagged_rows(tmp_path):
    rows = [
        _a6_row("lda:lobbyist:1", "c1", "MEMBER_OFFICE_CANDIDATE", 2001, 2002, []),
        _a6_row("lda:lobbyist:1", "c2", "COMMITTEE_CANDIDATE", 2003, 2004, []),
        _a6_row(
            "lda:lobbyist:1", "c3", "MEMBER_OFFICE_CANDIDATE", 2005, 2006,
            ["AMBIGUOUS_ROLE_ABBREVIATION"],
        ),
        _a6_row(
            "lda:lobbyist:1", "c4", "MEMBER_OFFICE_CANDIDATE", 2007, 2008,
            ["DATE_RANGE_REVERSED"],
        ),
        _a6_row(
            "lda:lobbyist:1", "c5", "MEMBER_OFFICE_CANDIDATE", 2009, 2010,
            ["MENTION_SPANS_OVERLAP"],
        ),
        _a6_row(
            "lda:lobbyist:1", "c6", "MEMBER_OFFICE_CANDIDATE", 2011, 2012,
            ["TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED"],
        ),
        # not resolvable / not both years -> never counted as a release candidate
        _a6_row("lda:lobbyist:1", "c7", "ORGANIZATION_CANDIDATE", 2013, 2014, []),
        _a6_row("lda:lobbyist:1", "c8", "MEMBER_OFFICE_CANDIDATE", 2015, None, []),
    ]
    path = tmp_path / "a6.ndjson.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")
    episodes, stats = builder.build_filer_episodes(path, ROSTER, NICKNAME_TABLE, {}, "v")
    assert stats["near_candidate_rows"] == 8
    assert stats["resolvable_entity_and_both_years"] == 6
    assert stats["excluded_by_flags"] == 4
    assert [row["claim_id"] for row in episodes] == ["c1", "c2"]
    assert all(row["excluded_flags"] == [] for row in episodes)
    assert all(row["precision"] == "year" for row in episodes)
    assert all(row["single_author"] is True for row in episodes)
    assert episodes[0]["member_bioguide"] == "S000001"
    assert episodes[1]["member_bioguide"] is None
    assert episodes[1]["member_resolution_method"] == "NOT_A_MEMBER_OFFICE"
    for row in episodes:
        validate_instance(row, schema("episode"))


def test_a6_payroll_corroboration_uses_a_whole_word_surname_match(tmp_path):
    rows = [_a6_row("lda:lobbyist:1", "c1", "MEMBER_OFFICE_CANDIDATE", 2001, 2002, [])]
    path = tmp_path / "a6.ndjson.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        stream.write(json.dumps(rows[0]) + "\n")
    hit, _ = builder.build_filer_episodes(
        path, ROSTER, NICKNAME_TABLE, {"lda:lobbyist:1": {"SENATOR JOE SMITH"}}, "v"
    )
    assert hit[0]["corroborated_by_payroll"] is True
    assert hit[0]["corroborating_payroll_office_examples"] == ["SENATOR JOE SMITH"]
    miss, _ = builder.build_filer_episodes(
        path, ROSTER, NICKNAME_TABLE, {"lda:lobbyist:1": {"SENATOR SMITHSON"}}, "v"
    )
    assert miss[0]["corroborated_by_payroll"] is False


# ---------------------------------------------------------------------------
# Language law and the anti-promotion tripwire
# ---------------------------------------------------------------------------
def test_language_law_flags_an_authored_value_but_exempts_a_quoted_office():
    quoted = [{"office_key": "OFFICE OF CONGRESSIONAL ACCESSIBILITY SERVICES"}]
    hits, verbatim = verifier.language_law_scan(quoted)
    assert hits == []
    assert verbatim == {"office_key|access": 1}
    authored = [{"tier_rationale": "office access was inferred"}]
    hits, _ = verifier.language_law_scan(authored)
    assert hits


def test_language_law_flags_a_banned_field_name():
    hits, _ = verifier.language_law_scan([{"predicted_tier": "L4"}])
    assert any("field_name" in hit for hit in hits)


def test_builder_and_verifier_agree_on_the_verbatim_exemption_list():
    assert builder.verbatim_field_names() == set(verifier.VERBATIM_LEAF_NAMES)


def test_anti_promotion_tripwire_negative_control():
    clean = {
        "review_status": "REVIEW_REQUIRED",
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
    }
    assert verifier.assert_unpromoted([clean]) == []
    promoted = dict(clean, canonical_employment_promoted=True)
    assert verifier.assert_unpromoted([promoted])
    eligible = dict(clean, canonical_eligible=True)
    assert verifier.assert_unpromoted([eligible])
    accepted = dict(clean, review_status="ACCEPTED")
    assert verifier.assert_unpromoted([accepted])


# ---------------------------------------------------------------------------
# End-to-end over a synthetic input tree
# ---------------------------------------------------------------------------
QUEUE = [
    ("lda:lobbyist:1", "STENY STAFFER", ["Chief of Staff to Rep. Hoyer, 2009-2012."], [2021, 2022]),
    ("lda:lobbyist:2", "GAPPY QUARTERS", ["Legislative Assistant to Rep. Hoyer."], [2021]),
    ("lda:lobbyist:3", "WAYS MEANS", ["Professional Staff, Committee on Ways and Means."], [2021]),
    ("lda:lobbyist:4", "SPLIT CLEAN", ["Counsel to Senator Smith."], [2021]),
    ("lda:lobbyist:5", "SPLIT GAPPED", ["Counsel to Senator Smith."], [2021]),
    ("lda:lobbyist:6", "LATE LEAVER", ["Aide to Rep. Hoyer."], [2021]),
    ("lda:lobbyist:7", "JANE SMITH", ["Aide to Rep. Hoyer."], [2021]),
    ("lda:lobbyist:8", "JANE SMITH", ["No covered positions."], [2021]),
    ("lda:lobbyist:9", "MULTI SOURCE", ["Counsel to Senator Smith."], [2021]),
    ("lda:lobbyist:10", "NO PAYROLL", ["None."], [2021]),
]

H1_ROWS = [
    # person 1: two punctuation variants of one member office, adjacent quarters
    ("lda:lobbyist:1", "STAFFER,STENY", "2009 HON. STENY H HOYER—Con.", "2009Q3", "2009-09-30", "CHIEF OF STAFF"),
    ("lda:lobbyist:1", "STAFFER,STENY", "2009 HON. STENY H. HOYER", "2009Q4", "2009-12-31", "CHIEF OF STAFF"),
    # persons 7 and 8 share a display name: the reconstruction must see two candidates
    ("lda:lobbyist:7", "SMITH,JANE", "2010 HON. STENY H. HOYER", "2010Q1", "2010-03-31", "AIDE"),
]
H2_ROWS = [
    # person 2: 2017Q1, 2017Q2 then a gap then 2017Q4
    ("lda:lobbyist:2", "GAPPY QUARTERS", "HON. STENY H. HOYER", ["2017Q1", "2017Q2", "2017Q4"], "2017-12-31", "LEGISLATIVE ASSISTANT", 1, 1),
    ("lda:lobbyist:3", "WAYS MEANS", "COMMITTEE ON WAYS AND MEANS", ["2018Q1"], "2018-03-31", "PROFESSIONAL STAFF", 1, 1),
    # person 6 leaves two years after the first filing year -> INCONSISTENT
    ("lda:lobbyist:6", "LATE LEAVER", "HON. STENY H. HOYER", ["2023Q1"], "2023-03-31", "AIDE", 1, 1),
]
SENATE_ROWS = [
    ("lda:lobbyist:4", "SENATOR JOE SMITH", [("2021-04-01", "2021-09-30"), ("2021-10-01", "2022-03-31")], "COUNSEL", 1),
    ("lda:lobbyist:5", "SENATOR JOE SMITH", [("2021-04-01", "2021-09-30"), ("2022-04-01", "2022-09-30")], "COUNSEL", 1),
    ("lda:lobbyist:9", "SENATOR JOE SMITH", [("2021-04-01", "2021-09-30")], "COUNSEL", 1),
]


def _write_gz(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


def _write_ndjson(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")


@pytest.fixture(scope="module")
def synthetic_tree(tmp_path_factory):
    root = tmp_path_factory.mktemp("synthetic")
    live = root / "live"
    appdata = root / "appdata"
    lane = live / "audits" / "staffer_network"

    _write_gz(
        appdata / "employment-lookup" / "generation-20260831T050000Z" / "employment_lookup_queue.ndjson.gz",
        [
            {
                "lda_source_person_id": person,
                "display_name": name,
                "covered_position_values": values,
                "filing_years": years,
            }
            for person, name, values, years in QUEUE
        ],
    )
    _write_gz(
        lane
        / "house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
        / "house_sod_pdf_lda_name_match_candidates.ndjson.gz",
        [
            {
                "candidate_match_id": f"h1-{index}",
                "lda_source_person_id": person,
                "payroll_payee_raw": payee,
                "employing_office_raw": office,
                "period": period,
                "period_start": period[:4] + "-01-01",
                "period_end": end,
                "service_start_date_candidate_iso": period[:4] + "-01-01",
                "service_end_date_candidate_iso": end,
                "title_description_raw": title,
            }
            for index, (person, payee, office, period, end, title) in enumerate(H1_ROWS)
        ],
    )
    _write_gz(
        lane / "lda_house_payroll_matches_2016_2026" / "lda_house_payroll_match_candidates.ndjson.gz",
        [
            {
                "match_candidate_id": f"h2-{index}",
                "lda_source_person_id": person,
                "display_name": name,
                "employing_office_candidate": office,
                "supported_quarters": quarters,
                "service_start_date_candidate": quarters[0][:4] + "-01-01",
                "service_end_date_candidate": end,
                "title_candidate": title,
                "queue_candidate_count_for_name": candidates,
                "queue_display_name_count_for_name": displays,
            }
            for index, (person, name, office, quarters, end, title, candidates, displays) in enumerate(
                H2_ROWS
            )
        ],
    )
    _write_gz(
        lane / "lda_senate_payroll_matches_2011_2026_v1" / "lda_senate_payroll_match_candidates.ndjson.gz",
        [
            {
                "match_candidate_id": f"s-{index}",
                "lda_source_person_id": person,
                "employing_office_candidate": office,
                "observed_report_intervals": [
                    {"basis": "REPORT_PERIOD_ONLY", "start": start, "end": end}
                    for start, end in intervals
                ],
                "title_candidate": title,
                "queue_candidate_count_for_name": candidates,
                "queue_display_name_count_for_name": 1,
            }
            for index, (person, office, intervals, title, candidates) in enumerate(SENATE_ROWS)
        ],
    )
    _write_gz(
        lane
        / "employment_adjudication_generation_20260901_v3_primary"
        / "candidate_adjudication_decisions.ndjson.gz",
        [
            {
                "lane": "legilist_source_binding",
                "decision": "ACCEPTED_SOURCE_BINDING",
                "lda_source_person_id": "lda:lobbyist:1",
            },
            {
                "lane": "lda_registrant_association",
                "decision": "REVIEW_REQUIRED",
                "lda_source_person_id": "lda:lobbyist:2",
            },
        ],
    )
    _write_gz(
        lane / "politico_lda_employment_candidates_20260831" / "politico_lda_employment_candidates.ndjson.gz",
        [
            {
                "lda_source_person_id": "lda:lobbyist:9",
                "role_text_raw": "Counsel for Sen. Joe Smith, Republican",
            }
        ],
    )
    _write_gz(
        lane
        / "a7_machine_local_source_inventory_20260901_primary"
        / "a7_ld203_affiliation_candidates.ndjson.gz",
        [
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "filing_year": 2021,
                "lda_registrant_name": "ACME ADVOCACY",
            },
            {
                "lda_source_person_id": "lda:lobbyist:1",
                "filing_year": 2024,
                "lda_registrant_name": "ACME ADVOCACY",
            },
        ],
    )
    _write_gz(
        lane
        / "a7_machine_local_source_inventory_20260901_primary"
        / "a7_fec_employment_observation_candidates.ndjson.gz",
        [
            {
                "lda_source_person_id": "lda:lobbyist:3",
                "observation_date": "2021-05-01",
                "raw_employer": "Acme Advocacy",
            }
        ],
    )
    _write_gz(
        lane / "lda_registrant_employment_20260831" / "lda_registrant_employment_episodes.ndjson.gz",
        [
            {
                "lda_source_person_id": person,
                "registrant_source_org_id": "lda:registrant:1",
                "employer_name": "ACME ADVOCACY",
                "filing_years": [2021, 2022],
                "start_year": 2021,
                "end_year": 2022,
            }
            for person, _, _, _ in QUEUE
        ],
    )
    _write_gz(
        lane / "littlesis_lda_history_candidates_20260831" / "littlesis_lda_history_candidates.ndjson.gz",
        [
            {
                "lda_source_person_id": "lda:lobbyist:4",
                "fact_type": "EMPLOYMENT",
                "container_display_name": "Acme Advocacy",
                "raw_start_date": "2021-01-01",
                "raw_end_date": "2022-12-31",
            }
        ],
    )
    _write_gz(
        lane
        / "lda_conservative_bounded_episode_candidates_20260901_b"
        / "lda_conservative_bounded_episode_blockers.ndjson.gz",
        [
            _a6_row("lda:lobbyist:1", "c1", "MEMBER_OFFICE_CANDIDATE", 2001, 2002, []),
            _a6_row(
                "lda:lobbyist:2", "c2", "MEMBER_OFFICE_CANDIDATE", 2003, 2004,
                ["AMBIGUOUS_ROLE_ABBREVIATION"],
            ),
        ],
    )
    _write_gz(
        lane / "working_history_corpus_20260831T180000Z_8workers" / "working_history_corpus.ndjson.gz",
        [
            {
                "lda_source_person_id": "lda:lobbyist:9",
                "employment_episodes": [
                    {
                        "employer": "Office of Senator Smith",
                        "raw_start_date": "2021-04-01",
                        "raw_end_date": "2021-09-30",
                    }
                ],
            }
        ],
    )
    _write_ndjson(
        lane / "rapid_structured_profile_evidence_20260901_current" / "rapid_structured_profile_evidence.ndjson",
        [{"lda_source_person_id": "lda:lobbyist:4", "employment": []}],
    )
    _write_ndjson(
        lane / "linkedin_authenticated_evidence_20260901" / "linkedin_authenticated_evidence.ndjson",
        [{"lda_source_person_id": "lda:lobbyist:4", "candidate_facts": []}],
    )
    _write_gz(
        lane / "a9_a7_a8_priority_sidecar_20260901_primary" / "a9_a7_a8_priority_sidecar_25340.ndjson.gz",
        [
            {
                "lda_source_person_id": person,
                "sealed_queue_ordinal": index + 1,
                "revised_priority": {"priority_bucket": "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION"},
            }
            for index, (person, _, _, _) in enumerate(QUEUE)
        ],
    )
    roster_dir = (
        live
        / "data"
        / "staffer_network"
        / "reference"
        / "congress-legislators"
        / "750c0608efb6ef1fc3257ba72c99af3771d35088"
    )
    roster_dir.mkdir(parents=True, exist_ok=True)
    (roster_dir / "legislators-current.yaml").write_text(
        "- id:\n    bioguide: H000874\n  name:\n    first: Steny\n    last: Hoyer\n"
        "  terms:\n    - type: rep\n      start: '1981-05-19'\n      end: '2027-01-03'\n",
        encoding="utf-8",
    )
    (roster_dir / "legislators-historical.yaml").write_text(
        "- id:\n    bioguide: S000001\n  name:\n    first: Joseph\n    last: Smith\n"
        "  terms:\n    - type: rep\n      start: '1995-01-03'\n      end: '2015-01-03'\n",
        encoding="utf-8",
    )
    reference_dir = live / "data" / "staffer_network" / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    (reference_dir / "first_name_nicknames_v1.json").write_text(
        json.dumps(
            {
                "schema_id": "staffer-network-first-name-nickname-table-v1",
                "provenance": "synthetic fixture table",
                "entries": {
                    "bill": ["william"],
                    "joe": ["joseph"],
                    "mitch": ["mitchell"],
                    "steny": ["steny"],
                },
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return root


@pytest.fixture(scope="module")
def synthetic_generation(synthetic_tree, tmp_path_factory, monkeypatch_module):
    outputs = tmp_path_factory.mktemp("generation")
    primary, twin = outputs / "gen_primary", outputs / "gen_twin"
    monkeypatch_module.setattr(builder, "SEALED_QUEUE_ROWS", len(QUEUE))
    monkeypatch_module.setattr(verifier, "SEALED_QUEUE_ROWS", len(QUEUE))
    monkeypatch_module.setattr(
        builder,
        "INV5_EXPECTED",
        (("payroll_union", "people", 8), ("a6_near_candidates", "rows", 2)),
    )
    monkeypatch_module.setattr(
        verifier,
        "INV5_EXPECTED",
        {("payroll_union", "people"): 8, ("a6_near_candidates", "rows"): 2},
    )
    common = [
        "--live-root", str(synthetic_tree / "live"),
        "--appdata-root", str(synthetic_tree / "appdata"),
        "--run-id", "synthetic",
    ]
    for directory in (primary, twin):
        builder.run(builder.parse_args(["--output-root", str(directory), *common]))
    return primary, twin


@pytest.fixture(scope="module")
def monkeypatch_module():
    from _pytest.monkeypatch import MonkeyPatch

    patch = MonkeyPatch()
    yield patch
    patch.undo()


def test_synthetic_build_is_deterministic_and_twin_identical(synthetic_generation):
    primary, twin = synthetic_generation
    for name in (
        "tiered_person_office_records.ndjson.gz",
        "tiered_person_summary_25340.ndjson.gz",
        "filer_asserted_year_episodes.ndjson.gz",
        "registrant_side_records.ndjson.gz",
        "tiered_corroboration_receipt.json",
    ):
        assert (primary / name).read_bytes() == (twin / name).read_bytes()
    payload = (primary / "tiered_person_office_records.ndjson.gz").read_bytes()
    assert payload[4:8] == b"\x00\x00\x00\x00"


def _rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def test_synthetic_rows_validate_against_the_committed_schemas(synthetic_generation):
    primary, _ = synthetic_generation
    for filename, key in (
        ("tiered_person_office_records.ndjson.gz", "record"),
        ("tiered_person_summary_25340.ndjson.gz", "summary"),
        ("filer_asserted_year_episodes.ndjson.gz", "episode"),
        ("registrant_side_records.ndjson.gz", "registrant"),
    ):
        document = schema(key)
        for row in _rows(primary / filename):
            validate_instance(row, document)
    receipt = json.loads(
        (primary / "tiered_corroboration_receipt.json").read_text(encoding="utf-8")
    )
    validate_instance(receipt, schema("receipt"))


def test_synthetic_tiers_and_spans_follow_the_prong_rules(synthetic_generation):
    primary, _ = synthetic_generation
    records = _rows(primary / "tiered_person_office_records.ndjson.gz")
    by_person = {}
    for row in records:
        by_person.setdefault(row["lda_source_person_id"], []).append(row)

    # person 1: both punctuation variants collapse into one office group and one run
    person1 = by_person["lda:lobbyist:1"]
    assert len(person1) == 1
    assert person1[0]["office_key"] == "HON:HOYER"
    assert person1[0]["periods_observed"] == 2
    assert person1[0]["contiguous"] is True
    assert person1[0]["member_bioguide"] == "H000874"
    assert person1[0]["core"] == {"start_latest": "2009-07-01", "end_earliest": "2009-12-31"}
    assert person1[0]["envelope"] == {"start_earliest": "2009-04-01", "end_latest": "2010-03-31"}
    assert sorted(len(row["office_raw_examples"]) for row in person1) == [2]

    # person 2: a missing quarter splits the office into two runs
    person2 = sorted(by_person["lda:lobbyist:2"], key=lambda row: row["run_index"])
    assert [row["run_index"] for row in person2] == [1, 2]
    assert all(row["run_count"] == 2 for row in person2)
    assert all(row["contiguous"] is False for row in person2)
    assert [row["periods_observed"] for row in person2] == [2, 1]

    # person 3: committee keyword corroboration
    assert by_person["lda:lobbyist:3"][0]["prong"]["office_corroborated"] is True
    assert by_person["lda:lobbyist:3"][0]["container_kind"] == "committee"

    # persons 4 and 5: the Senate split prong
    assert by_person["lda:lobbyist:4"][0]["prong"]["split_clean"] is True
    assert by_person["lda:lobbyist:5"][0]["prong"]["split_clean"] is False

    # person 6: chronology inconsistent stops the ladder at L3
    assert by_person["lda:lobbyist:6"][0]["prong"]["chronology"] == "INCONSISTENT"
    assert by_person["lda:lobbyist:6"][0]["tier"] == "L3"

    # person 7: the shared display name breaks name uniqueness
    assert by_person["lda:lobbyist:7"][0]["prong"]["name_unique"] is False
    assert by_person["lda:lobbyist:7"][0]["tier"] == "L1"
    assert by_person["lda:lobbyist:7"][0]["identity_status"] == "NAME_MATCH_ONLY"

    # person 9: a profile employer and a Politico role both name the office -> L5
    person9 = by_person["lda:lobbyist:9"][0]
    assert person9["prong"]["multi_source"] == ["politico", "profile"]
    assert person9["tier"] == "L5"
    assert person9["prong_evidence"]["multi_source"]["legilist_names_office"] is False

    # every row is review-only
    assert all(row["review_status"] == "REVIEW_REQUIRED" for row in records)
    assert all(row["canonical_employment_promoted"] is False for row in records)


def test_tier_fields_do_not_depend_on_member_resolution(
    synthetic_generation, synthetic_tree, tmp_path_factory, monkeypatch
):
    """Tier assignment (person_tier_letter / house_lane_tiers /
    senate_lane_tiers) never reads member_bioguide or member_resolution_method
    -- see the generation-v2 design note at build_tiered_corroboration_sidecar.py
    around line 739.  Prove it empirically rather than trust the comment: force
    every roster lookup to miss (so every previously-resolved row's
    member_bioguide goes to null and its method flips to an UNRESOLVED_* /
    NOT_A_MEMBER_OFFICE reason) and assert every tier-bearing field on both the
    per-record ladder output and the person-level summary -- tier, prong,
    periods_observed, contiguous, run_index/run_count, core/envelope, and
    max_tier -- is byte-for-byte unchanged.
    """
    baseline_primary, _ = synthetic_generation
    baseline_records = _rows(baseline_primary / "tiered_person_office_records.ndjson.gz")
    baseline_summary = _rows(baseline_primary / "tiered_person_summary_25340.ndjson.gz")

    # Sanity: the baseline actually resolved somebody (person 1 / Hoyer), or
    # this test would be vacuously true.
    assert any(row["member_bioguide"] for row in baseline_records)

    monkeypatch.setattr(builder, "load_roster", lambda directory: {})
    output_dir = tmp_path_factory.mktemp("broken_roster_generation") / "gen"
    builder.run(
        builder.parse_args(
            [
                "--output-root", str(output_dir),
                "--live-root", str(synthetic_tree / "live"),
                "--appdata-root", str(synthetic_tree / "appdata"),
            ]
        )
    )
    broken_records = _rows(output_dir / "tiered_person_office_records.ndjson.gz")
    broken_summary = _rows(output_dir / "tiered_person_summary_25340.ndjson.gz")

    # The empty roster really did break every resolution -- otherwise the
    # comparison below would be trivially unaffected either way.
    assert all(row["member_bioguide"] is None for row in broken_records)
    assert any(
        baseline["member_resolution_method"] != broken["member_resolution_method"]
        for baseline, broken in zip(baseline_records, broken_records)
    )

    resolution_fields = {"member_bioguide", "member_resolution_method"}

    def strip(rows):
        return [
            {key: value for key, value in row.items() if key not in resolution_fields}
            for row in rows
        ]

    assert strip(baseline_records) == strip(broken_records)
    assert baseline_summary == broken_summary


def test_synthetic_summary_conserves_the_queue(synthetic_generation):
    primary, _ = synthetic_generation
    summary = _rows(primary / "tiered_person_summary_25340.ndjson.gz")
    assert len(summary) == len(QUEUE)
    assert {row["lda_source_person_id"] for row in summary} == {q[0] for q in QUEUE}
    by_person = {row["lda_source_person_id"]: row for row in summary}
    assert by_person["lda:lobbyist:10"]["max_tier"] == "L0"
    assert by_person["lda:lobbyist:10"]["prong_failure_codes"] == ["NO_PAYROLL_OBSERVATION"]
    assert by_person["lda:lobbyist:9"]["max_tier"] == "L5"
    assert "SPLIT_NOT_CLEAN" in by_person["lda:lobbyist:5"]["prong_failure_codes"]
    assert "CHRONOLOGY_INCONSISTENT" in by_person["lda:lobbyist:6"]["prong_failure_codes"]
    assert "NAME_COLLISION_IN_QUEUE" in by_person["lda:lobbyist:7"]["prong_failure_codes"]
    assert by_person["lda:lobbyist:1"]["filer_asserted_year_episode_count"] == 1
    assert by_person["lda:lobbyist:2"]["filer_asserted_year_episode_count"] == 0


def test_synthetic_registrant_side_tiers(synthetic_generation):
    primary, _ = synthetic_generation
    rows = {
        row["lda_source_person_id"]: row
        for row in _rows(primary / "registrant_side_records.ndjson.gz")
    }
    assert len(rows) == len(QUEUE)
    assert rows["lda:lobbyist:1"]["ld203"]["same_year_name_equal"] is True
    assert rows["lda:lobbyist:1"]["ld203"]["extends_later_years"] == 2
    assert rows["lda:lobbyist:1"]["registrant_side_tier"] == "R1"
    assert rows["lda:lobbyist:3"]["fec"]["same_year_name_equal"] is True
    assert rows["lda:lobbyist:4"]["registrant_side_tier"] == "R2"
    assert rows["lda:lobbyist:10"]["hill_registrant_order"] == "NO_HILL_OBSERVATION"
    assert rows["lda:lobbyist:1"]["hill_registrant_order"] == "ORDERED"


def test_verifier_passes_on_the_synthetic_generation(synthetic_generation, tmp_path):
    primary, twin = synthetic_generation
    output = tmp_path / "verification" / "tiered_corroboration_verification_receipt.json"
    result = verifier.verify(
        verifier.parse_args(
            ["--primary", str(primary), "--twin", str(twin), "--output", str(output)]
        )
    )
    assert result["status"] == "PASS", result["failures"]
    assert result["counts"]["row_mismatches_records"] == 0
    assert output.is_file()


def test_verifier_fails_when_a_row_claims_a_promotion(synthetic_generation, tmp_path):
    """Tripwire negative control: a single promoted row must fail the verifier."""

    primary, twin = synthetic_generation
    poisoned = tmp_path / "poisoned_primary"
    poisoned.mkdir()
    for path in primary.iterdir():
        poisoned.joinpath(path.name).write_bytes(path.read_bytes())
    name = "tiered_person_office_records.ndjson.gz"
    rows = _rows(poisoned / name)
    rows[0]["canonical_employment_promoted"] = True
    with gzip.open(poisoned / name, "wt", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    output = tmp_path / "verification_poisoned" / "receipt.json"
    result = verifier.verify(
        verifier.parse_args(
            ["--primary", str(poisoned), "--twin", str(twin), "--output", str(output)]
        )
    )
    assert result["status"] == "FAIL"
    assert result["assertions"]["anti_promotion_tripwire_clean"] is False
    assert any(
        "canonical_employment_promoted" in entry
        for entry in result["detail"]["anti_promotion_tripwire"]
    )


def test_builder_refuses_a_nonempty_output_directory(synthetic_tree, tmp_path):
    directory = tmp_path / "occupied"
    directory.mkdir()
    (directory / "already_here.txt").write_text("x", encoding="utf-8")
    with pytest.raises(builder.GateFailure):
        builder.run(
            builder.parse_args(
                [
                    "--output-root", str(directory),
                    "--live-root", str(synthetic_tree / "live"),
                    "--appdata-root", str(synthetic_tree / "appdata"),
                ]
            )
        )


def test_builder_refuses_a_queue_that_is_not_the_sealed_scope(
    synthetic_tree, tmp_path, monkeypatch
):
    monkeypatch.setattr(builder, "SEALED_QUEUE_ROWS", 25340)
    with pytest.raises(builder.GateFailure) as error:
        builder.run(
            builder.parse_args(
                [
                    "--output-root", str(tmp_path / "scope"),
                    "--live-root", str(synthetic_tree / "live"),
                    "--appdata-root", str(synthetic_tree / "appdata"),
                ]
            )
        )
    assert "sealed queue" in str(error.value)


# ---------------------------------------------------------------------------
# v3 SPINE LINK
# ---------------------------------------------------------------------------
# Synthetic only.  A miniature spine, a miniature v2 generation and miniature
# lane inputs are built under tmp_path and the --spine-link stage is run over
# them, so the four cases the rule has to get right are exercised end to end:
# one LINKED, one AMBIGUOUS same-office same-name pair, one NOT_FOUND, and one
# record that links only through its person's legacy v6 key.
#
# The INV-5 gate CANNOT pass on a fixture -- the ladder constants are the real
# 25,340-person figures -- so the end-to-end test asserts that
# INV5_LADDER_REPRODUCTION_MISMATCH is the ONLY failure.  That is a negative
# control for the gate, not a hole in it: a build whose numbers moved fails.

from fec.staffer_network import name_standard as _standard  # noqa: E402

# Captured at import, before any test can monkeypatch it.  An earlier test in
# this file swaps INV5_EXPECTED for a two-row fixture set at module scope, and
# a link generation built while that patch is live would carry a two-row INV-5
# block -- which would make the 34-row assertion below pass or fail on test
# ORDER rather than on behaviour.
REAL_INV5_EXPECTED = tuple(builder.INV5_EXPECTED)

SPINE_SCHEMA_FILES = {
    "record_v2": "tiered_person_office_record_v2.schema.json",
    "summary_v2": "tiered_person_summary_v2.schema.json",
    "link_receipt": "tiered_corroboration_spine_link_receipt.schema.json",
    "link_verification": "tiered_corroboration_spine_link_verification.schema.json",
}


def spine_schema(name: str) -> dict:
    return json.loads(
        (SCHEMA_DIR / SPINE_SCHEMA_FILES[name]).read_text(encoding="utf-8")
    )


def _name_key(raw: str, source: str) -> str:
    return _standard.name_key(_standard.parse_name(raw, source))


def _person_id(seed: str) -> str:
    import hashlib

    return "hill:person:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _v2_record(person, chamber, lane, office_key, office_raws, window, tier="L2"):
    return {
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "chamber": chamber,
        "container_kind": "committee",
        "contiguous": True,
        "core": {"end_earliest": window[1], "start_latest": window[0]},
        "envelope": {"end_latest": window[1], "start_earliest": window[0]},
        "identity_status": "NAME_MATCH_ONLY",
        "lda_source_person_id": person,
        "member_bioguide": None,
        "member_resolution_method": "NOT_A_MEMBER_OFFICE",
        "office_key": office_key,
        "office_raw_examples": list(office_raws),
        "period_kind": "quarter" if chamber == "house" else "half_year",
        "periods_observed": 1,
        "precision": "report_period",
        "prong": {
            "chronology": "CONSISTENT",
            "multi_source": [],
            "name_unique": True,
            "office_corroborated": False,
            "split_clean": None if chamber == "house" else True,
        },
        "prong_evidence": {
            "chronology": {
                "first_filing_year": 2021,
                "max_observed_end_year": 2017,
                "office_chronology_consistent": True,
                "office_max_observed_end_year": 2017,
                "threshold_year": 2022,
            },
            "multi_source": {
                "legilist_names_office": False,
                "legilist_person_binding": False,
                "politico_matched_token": None,
                "profile_matched_employer": None,
            },
            "name_uniqueness": {
                "method": "LEDGER_FIELDS",
                "queue_candidate_count_for_name": 1,
                "queue_display_name_count_for_name": 1,
            },
            "office_match": {
                "matched_token": None,
                "method": "COMMITTEE_KEYWORD_NOT_FOUND",
                "office_normalized": office_key,
            },
            "payroll_support_digest": "0" * 64,
            "split": {
                "office_period_count": 1,
                "office_run_count": 1,
                "person_offices_all_contiguous": None if chamber == "house" else True,
            },
        },
        "review_status": "REVIEW_REQUIRED",
        "rule_version": "tiered-corroboration-v2",
        "run_count": 1,
        "run_index": 1,
        "schema_id": "staffer-network-tiered-person-office-record-v1",
        "source_lane": lane,
        "tier": tier,
        "title_examples": ["COUNSEL"],
    }


def _v2_summary(person, ordinal, chamber):
    return {
        "a9_bucket": "P3_IDENTITY_AND_CHRONOLOGY_ADJUDICATION",
        "a9_sealed_queue_ordinal": ordinal,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "filer_asserted_year_episode_count": 0,
        "lda_source_person_id": person,
        "max_tier": "L2",
        "person_office_record_count": 1,
        "prong_failure_codes": [],
        "registrant_side_tier": "R1",
        "review_status": "REVIEW_REQUIRED",
        "rule_version": "tiered-corroboration-v2",
        "schema_id": "staffer-network-tiered-person-summary-v1",
        "senate_split_clean": True if chamber == "senate" else None,
        "tier_by_chamber": {
            "house": "L2" if chamber == "house" else "L0",
            "senate": "L2" if chamber == "senate" else "L0",
        },
        "tier_by_lane": {
            builder.LANE_H1: "L0",
            builder.LANE_H2: "L2" if chamber == "house" else "L0",
            builder.LANE_SENATE: "L2" if chamber == "senate" else "L0",
        },
    }


@pytest.fixture(scope="module")
def spine_link_tree(tmp_path_factory):
    """A miniature live tree carrying every input the link stage binds."""

    root = tmp_path_factory.mktemp("spine_link")
    lane_root = root / "audits" / "staffer_network"
    v2 = lane_root / "sidecar_v2_primary"
    v2_verify = lane_root / "sidecar_v2_verification"
    spine = lane_root / "spine_primary"
    spine_verify = lane_root / "spine_verification"
    ledger = lane_root / "ledger_primary"
    roster_dir = root / "data" / "staffer_network" / "reference" / "roster"
    for directory in (v2, v2_verify, spine, spine_verify, ledger, roster_dir):
        directory.mkdir(parents=True, exist_ok=True)

    # --- the four cases ----------------------------------------------------
    # 1 LINKED         house committee, one spine person, windows overlap
    # 2 AMBIGUOUS      same office, same last|first, two spine persons whose
    #                  middle initials are both compatible with a record that
    #                  carries none
    # 3 NOT_FOUND      a name that is in no bucket for that office
    # 4 LEGACY         links only through the person's recorded key_v6
    office_committee = "COMMITTEE ON RULES"
    office_senate = "OFFICE OF SENATOR ALPHA"
    linked_key = _name_key("MARY C JONES", "display")
    ambiguous_key = _name_key("JOHN SMITH", "display")
    legacy_key = _name_key("ORLA QUINN", "display")

    p_linked = _person_id("linked")
    p_amb_a = _person_id("ambiguous-a")
    p_amb_b = _person_id("ambiguous-b")
    p_legacy = _person_id("legacy")
    # The legacy person's CURRENT key is deliberately not the key the record
    # produces; only the id map carries the key the record will compute.
    legacy_v7_key = legacy_key.split("|")[0] + "zz|" + legacy_key.split("|", 1)[1]

    spine_rows = [
        {"spine_person_id": p_linked, "name_key": linked_key,
         "payee_key": {"first": "mary", "first_class": linked_key.split("|")[1],
                       "last": "jones", "middle_initial": "c", "suffix": None}},
        {"spine_person_id": p_amb_a, "name_key": ambiguous_key.rsplit("|", 1)[0] + "|a",
         "payee_key": {"first": "john", "first_class": ambiguous_key.split("|")[1],
                       "last": "smith", "middle_initial": "a", "suffix": None}},
        {"spine_person_id": p_amb_b, "name_key": ambiguous_key.rsplit("|", 1)[0] + "|b",
         "payee_key": {"first": "john", "first_class": ambiguous_key.split("|")[1],
                       "last": "smith", "middle_initial": "b", "suffix": None}},
        {"spine_person_id": p_legacy, "name_key": legacy_v7_key,
         "payee_key": {"first": "orla", "first_class": legacy_key.split("|")[1],
                       "last": legacy_v7_key.split("|")[0], "middle_initial": None,
                       "suffix": None}},
    ]
    _write_gz(spine / "hill_person_spine.ndjson.gz", spine_rows)
    _write_gz(
        spine / "spine_id_map_v6_to_v7.ndjson.gz",
        [
            {"legacy_person_id": _person_id("legacy-v6"), "person_id": p_legacy,
             "key_v6": legacy_key, "key_v7": legacy_v7_key, "reason": "ascii_punct",
             "causes": ["ascii_punct"]},
            {"legacy_person_id": p_linked, "person_id": p_linked,
             "key_v6": linked_key, "key_v7": linked_key, "reason": "unchanged",
             "causes": []},
        ],
    )
    _write_gz(
        spine / "hill_person_office_spans.ndjson.gz",
        [
            {"spine_person_id": p_linked, "chamber": "house",
             "office_key": office_committee, "first_period": "2017Q1",
             "last_period": "2017Q4",
             "envelope": {"start_earliest": "2017-01-01", "end_latest": "2017-12-31"}},
            {"spine_person_id": p_amb_a, "chamber": "house",
             "office_key": office_committee, "first_period": "2017Q1",
             "last_period": "2017Q4",
             "envelope": {"start_earliest": "2017-01-01", "end_latest": "2017-12-31"}},
            {"spine_person_id": p_amb_b, "chamber": "house",
             "office_key": office_committee, "first_period": "2017Q1",
             "last_period": "2017Q4",
             "envelope": {"start_earliest": "2017-01-01", "end_latest": "2017-12-31"}},
            {"spine_person_id": p_legacy, "chamber": "senate",
             "office_key": office_senate, "first_period": "2019H1",
             "last_period": "2019H2",
             "envelope": {"start_earliest": "2019-01-01", "end_latest": "2019-12-31"}},
        ],
    )
    (spine / "hill_personnel_spine_receipt.json").write_text(
        json.dumps({"status": "PASS", "generated_at": "2026-09-07T06:00:00Z",
                    "rule_version": "hill-personnel-spine-v2", "run_id": "fixture"}),
        encoding="utf-8",
    )
    (spine_verify / "hill_personnel_spine_verification_receipt.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )

    # --- lane inputs -------------------------------------------------------
    h2_dir = lane_root / "lda_house_payroll_matches_2016_2026"
    senate_dir = lane_root / "lda_senate_payroll_matches_2011_2026_v1"
    h1_dir = (
        lane_root
        / "house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
    )
    _write_gz(
        h1_dir / "house_sod_pdf_lda_name_match_candidates.ndjson.gz",
        [{"lda_source_person_id": "lda:lobbyist:900",
          "employing_office_raw": office_committee, "payroll_payee_raw": "NOBODY,NAMED",
          "period": "2017Q1"}],
    )
    _write_gz(
        h2_dir / "lda_house_payroll_match_candidates.ndjson.gz",
        [
            {"lda_source_person_id": "lda:lobbyist:901", "display_name": "MARY C JONES",
             "employing_office_candidate": office_committee},
            {"lda_source_person_id": "lda:lobbyist:902", "display_name": "JOHN SMITH",
             "employing_office_candidate": office_committee},
        ],
    )
    _write_gz(
        senate_dir / "lda_senate_payroll_match_candidates.ndjson.gz",
        [{"lda_source_person_id": "lda:lobbyist:903", "display_name": "ORLA QUINN",
          "employing_office_candidate": office_senate}],
    )

    # --- the v2 generation the stage carries forward -----------------------
    records = [
        _v2_record("lda:lobbyist:900", "house", builder.LANE_H1, office_committee,
                   [office_committee], ("2017-01-01", "2017-12-31")),
        _v2_record("lda:lobbyist:901", "house", builder.LANE_H2, office_committee,
                   [office_committee], ("2017-01-01", "2017-12-31")),
        _v2_record("lda:lobbyist:902", "house", builder.LANE_H2, office_committee,
                   [office_committee], ("2017-01-01", "2017-12-31")),
        _v2_record("lda:lobbyist:903", "senate", builder.LANE_SENATE, office_senate,
                   [office_senate], ("2019-01-01", "2019-12-31")),
    ]
    summaries = [
        _v2_summary("lda:lobbyist:900", 1, "house"),
        _v2_summary("lda:lobbyist:901", 2, "house"),
        _v2_summary("lda:lobbyist:902", 3, "house"),
        _v2_summary("lda:lobbyist:903", 4, "senate"),
    ]
    _write_gz(v2 / builder.RECORD_FILE, records)
    _write_gz(v2 / builder.SUMMARY_FILE, summaries)
    _write_gz(v2 / builder.EPISODE_FILE, [])
    _write_gz(v2 / builder.REGISTRANT_FILE, [])
    a6_dir = lane_root / "lda_conservative_bounded_episode_candidates_20260901_b"
    _write_gz(a6_dir / "lda_conservative_bounded_episode_blockers.ndjson.gz", [])
    (v2 / builder.RECEIPT_FILE).write_text(
        json.dumps(
            {
                "status": "PASS",
                "rule_version": "tiered-corroboration-v2",
                "inputs": {},
                "inv5_reproduction": {"all_match": True, "rows": []},
            }
        ),
        encoding="utf-8",
    )
    (v2_verify / "tiered_corroboration_verification_receipt.json").write_text(
        json.dumps({"status": "PASS"}), encoding="utf-8"
    )

    # --- ledger, roster, nickname table ------------------------------------
    _write_gz(ledger / "house_personnel_observations.ndjson.gz", [])
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        (roster_dir / filename).write_text("[]\n", encoding="utf-8")
    (roster_dir / "nicknames.json").write_text(json.dumps({}), encoding="utf-8")

    return {
        "root": root,
        "v2": v2,
        "v2_verify": v2_verify / "tiered_corroboration_verification_receipt.json",
        "spine": spine,
        "spine_verify": spine_verify / "hill_personnel_spine_verification_receipt.json",
        "ledger": ledger,
        "roster": roster_dir,
        "nicknames": roster_dir / "nicknames.json",
        "ids": {
            "linked": p_linked,
            "ambiguous": (p_amb_a, p_amb_b),
            "legacy": p_legacy,
        },
        "keys": {"linked": linked_key, "legacy": legacy_key},
        "offices": {"committee": office_committee, "senate": office_senate},
    }


@contextlib.contextmanager
def real_inv5_expected():
    """Run the link stage against the REAL ladder constants regardless of what
    an earlier test left patched on the builder module."""

    patched = builder.INV5_EXPECTED
    builder.INV5_EXPECTED = REAL_INV5_EXPECTED
    try:
        yield
    finally:
        builder.INV5_EXPECTED = patched


def _spine_link_args(tree, output_root):
    return builder.parse_args(
        [
            "--spine-link",
            "--output-root", str(output_root),
            "--live-root", str(tree["root"]),
            "--v2-root", str(tree["v2"]),
            "--v2-verification-receipt", str(tree["v2_verify"]),
            "--spine-root", str(tree["spine"]),
            "--spine-verification-receipt", str(tree["spine_verify"]),
            "--house-ledger-root", str(tree["ledger"]),
            "--roster-root", str(tree["roster"]),
            "--nickname-table", str(tree["nicknames"]),
            "--run-id", "fixture",
            "--generated-at", "2026-09-07T00:00:00Z",
        ]
    )


@pytest.fixture(scope="module")
def spine_link_generation(spine_link_tree, tmp_path_factory):
    out = tmp_path_factory.mktemp("spine_link_out")
    primary = out / "primary"
    with real_inv5_expected():
        result = builder.run_spine_link(_spine_link_args(spine_link_tree, primary))
    return primary, result["receipt"]


def test_spine_link_covers_linked_ambiguous_not_found_and_the_legacy_key(
    spine_link_generation, spine_link_tree
):
    primary, receipt = spine_link_generation
    rows = {row["lda_source_person_id"]: row for row in _rows(primary / builder.RECORD_FILE)}

    # 1 LINKED
    linked = rows["lda:lobbyist:901"]
    assert linked["spine_link_status"] == "LINKED"
    assert linked["spine_link_reason"] == "UNIQUE_SPINE_PERSON"
    assert linked["spine_person_id"] == spine_link_tree["ids"]["linked"]
    basis = linked["spine_link_basis"]
    assert basis["office_key"] == spine_link_tree["offices"]["committee"]
    assert basis["name_key"] == spine_link_tree["keys"]["linked"]
    assert basis["name_key_equality"] == "EXACT"
    assert basis["key_generation"] in {"v7", "both"}
    assert basis["window"]["test"] == "APPLIED"
    assert basis["span_ids"] == [f"{spine_link_tree['ids']['linked']}#0"]

    # 2 AMBIGUOUS -- same office, same last|first, two spine persons
    ambiguous = rows["lda:lobbyist:902"]
    assert ambiguous["spine_link_status"] == "AMBIGUOUS"
    assert ambiguous["spine_link_reason"] == "MULTIPLE_SPINE_PERSONS"
    assert ambiguous["spine_link_candidate_count"] == 2
    assert ambiguous["spine_person_id"] is None
    assert ambiguous["spine_link_basis"] is None

    # 3 NOT_FOUND
    missing = rows["lda:lobbyist:900"]
    assert missing["spine_link_status"] == "NOT_FOUND"
    assert missing["spine_link_reason"] == "NAME_ABSENT_IN_OFFICE"
    assert missing["spine_person_id"] is None

    # 4 the legacy v6 key
    legacy = rows["lda:lobbyist:903"]
    assert legacy["spine_link_status"] == "LINKED"
    assert legacy["spine_person_id"] == spine_link_tree["ids"]["legacy"]
    assert legacy["spine_link_basis"]["key_generation"] == "v6_legacy"
    assert legacy["spine_link_basis"]["name_key"] == spine_link_tree["keys"]["legacy"]

    assert receipt["counts"]["link_status"] == {
        "LINKED": 2, "AMBIGUOUS": 1, "NOT_FOUND": 1
    }
    assert receipt["counts"]["persons_with_at_least_one_link"] == 2


def test_spine_link_summaries_carry_only_linked_ids(spine_link_generation):
    primary, _ = spine_link_generation
    rows = {row["lda_source_person_id"]: row for row in _rows(primary / builder.SUMMARY_FILE)}
    assert rows["lda:lobbyist:901"]["spine_link_summary"] == {
        "ambiguous": 0, "linked_records": 1, "not_found": 0
    }
    assert len(rows["lda:lobbyist:901"]["spine_person_ids"]) == 1
    assert rows["lda:lobbyist:902"]["spine_person_ids"] == []
    assert rows["lda:lobbyist:902"]["spine_link_summary"]["ambiguous"] == 1
    assert rows["lda:lobbyist:900"]["spine_person_ids"] == []


def test_spine_link_carries_every_v2_field_byte_identically(
    spine_link_generation, spine_link_tree
):
    primary, receipt = spine_link_generation
    old = {row["lda_source_person_id"]: row for row in _rows(spine_link_tree["v2"] / builder.RECORD_FILE)}
    new = {row["lda_source_person_id"]: row for row in _rows(primary / builder.RECORD_FILE)}
    assert set(old) == set(new)
    for person, before in old.items():
        after = new[person]
        for key in before:
            if key == "schema_id":
                continue
            assert builder.compact(after[key]) == builder.compact(before[key]), key
        assert after["rule_version"] == "tiered-corroboration-v2"
        assert after["schema_id"] == builder.SPINE_LINK_RECORD_SCHEMA
    assert receipt["conservation"]["v2_record_fields_byte_identical"] is True
    assert receipt["conservation"]["v2_summary_fields_byte_identical"] is True
    assert receipt["link_rule"]["tiers_recomputed"] is False


def test_spine_link_never_lets_an_unlinked_row_carry_an_id(spine_link_generation):
    primary, receipt = spine_link_generation
    for row in _rows(primary / builder.RECORD_FILE):
        if row["spine_link_status"] != "LINKED":
            assert row["spine_person_id"] is None
            assert row["spine_link_basis"] is None
        else:
            assert row["spine_person_id"]
            assert row["spine_link_basis"]
    assert receipt["conservation"]["unlinked_records_carrying_a_spine_id"] == 0
    assert receipt["conservation"]["linked_records_without_a_spine_id"] == 0
    assert receipt["canonical_identity_promotions"] == 0
    assert receipt["canonical_employment_promotions"] == 0
    assert receipt["canonical_promotions_zero"] is True


def test_spine_link_rows_validate_against_the_committed_v2_schemas(
    spine_link_generation,
):
    primary, _ = spine_link_generation
    record_schema = spine_schema("record_v2")
    summary_schema = spine_schema("summary_v2")
    validate_schema_definition(record_schema)
    validate_schema_definition(summary_schema)
    for row in _rows(primary / builder.RECORD_FILE):
        validate_instance(row, record_schema)
    for row in _rows(primary / builder.SUMMARY_FILE):
        validate_instance(row, summary_schema)


def test_v2_schema_rejects_an_unlinked_row_that_carries_an_id(spine_link_generation):
    primary, _ = spine_link_generation
    document = spine_schema("record_v2")
    linked = next(
        row for row in _rows(primary / builder.RECORD_FILE)
        if row["spine_link_status"] == "LINKED"
    )
    forged = dict(linked)
    forged["spine_link_status"] = "AMBIGUOUS"
    forged["spine_link_reason"] = "MULTIPLE_SPINE_PERSONS"
    with pytest.raises(SchemaValidationError):
        validate_instance(forged, document)


def test_spine_link_scope_gates_fire_on_a_fixture_and_nothing_else_does(
    spine_link_generation,
):
    """Negative control for the two SCOPE gates, and only those two.

    A fixture is four people, not the sealed 25,340, and the ladder constants
    are the real figures -- so the sealed-queue gate and the INV-5 gate MUST
    both fire here.  If either stopped firing it would mean the gate had gone
    decorative.  Every other gate must still pass on the same generation, which
    is what makes this a control rather than a blanket allowance."""

    _, receipt = spine_link_generation
    assert receipt["failures"] == [
        "INV5_LADDER_REPRODUCTION_MISMATCH",
        "SUMMARY_COUNT_NOT_SEALED_QUEUE",
    ]
    assert receipt["status"] == "FAIL"
    assert receipt["inv5_reproduction"]["all_match"] is False
    assert len(receipt["inv5_reproduction"]["rows"]) == len(REAL_INV5_EXPECTED) == 34
    assert receipt["conservation"]["person_office_records"] == 4
    assert receipt["conservation"]["link_histogram_sums_to_records"] is True
    assert receipt["language_law"]["authored_hits"] == 0


def test_spine_link_is_deterministic_and_twin_identical(
    spine_link_tree, tmp_path_factory
):
    out = tmp_path_factory.mktemp("spine_link_twin")
    primary, twin = out / "primary", out / "twin"
    with real_inv5_expected():
        builder.run_spine_link(_spine_link_args(spine_link_tree, primary))
        args = _spine_link_args(spine_link_tree, twin)
        args.generated_at = "2026-09-07T01:01:01Z"
        args.run_id = "fixture-twin"
        builder.run_spine_link(args)
    for name in (
        builder.RECORD_FILE, builder.SUMMARY_FILE,
        builder.EPISODE_FILE, builder.REGISTRANT_FILE,
    ):
        assert (primary / name).read_bytes() == (twin / name).read_bytes()
    volatile = {"generated_at", "run_id"}
    left = json.loads((primary / builder.RECEIPT_FILE).read_text(encoding="utf-8"))
    right = json.loads((twin / builder.RECEIPT_FILE).read_text(encoding="utf-8"))
    assert {k: v for k, v in left.items() if k not in volatile} == {
        k: v for k, v in right.items() if k not in volatile
    }
    assert left["generated_at"] != right["generated_at"]


def test_spine_link_refuses_a_non_empty_output_root(spine_link_tree, tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "already-here.txt").write_text("x", encoding="utf-8")
    with real_inv5_expected(), pytest.raises(builder.GateFailure) as error:
        builder.run_spine_link(_spine_link_args(spine_link_tree, occupied))
    assert "INV-2" in str(error.value)


def test_window_overlap_rule(spine_link_generation):
    overlap = builder.windows_overlap
    assert overlap(("2017-01-01", "2017-12-31"), ("2017-12-31", "2018-06-30")) == (
        True, "APPLIED"
    )
    assert overlap(("2017-01-01", "2017-12-31"), ("2018-01-01", "2018-06-30")) == (
        False, "APPLIED"
    )
    # An envelope nobody observed cannot DISPROVE overlap.
    assert overlap((None, None), ("2018-01-01", "2018-06-30")) == (True, "NOT_APPLICABLE")


def test_sidecar_office_key_matches_the_record_rule():
    assert builder.sidecar_office_key("house", "2010 HON. STENY H. HOYER") == "HON:HOYER"
    assert builder.sidecar_office_key("house", "COMMITTEE ON RULES") == "COMMITTEE ON RULES"
    assert builder.sidecar_office_key("senate", "  office of   senator alpha ") == (
        "OFFICE OF SENATOR ALPHA"
    )


def test_builder_and_verifier_agree_on_the_lane_payee_map():
    assert builder.SPINE_LINK_LANE_PAYEE == verifier.SPINE_LINK_LANE_FIELDS


def test_builder_and_verifier_agree_on_the_stage_id():
    assert builder.SPINE_LINK_STAGE_ID == verifier.SPINE_LINK_STAGE_ID


def test_spine_link_verifier_rederives_the_fixture_link(
    spine_link_tree, tmp_path_factory
):
    out = tmp_path_factory.mktemp("spine_link_verify")
    primary, twin = out / "primary", out / "twin"
    with real_inv5_expected():
        for directory in (primary, twin):
            builder.run_spine_link(_spine_link_args(spine_link_tree, directory))
    result = verifier.verify_spine_link(
        verifier.parse_args(
            [
                "--spine-link",
                "--primary", str(primary),
                "--twin", str(twin),
                "--output", str(out / "verification.json"),
            ]
        )
    )
    assertions = result["assertions"]
    assert assertions["every_link_status_independently_rederived"] is True
    assert assertions["every_spine_id_independently_rederived"] is True
    assert assertions["every_link_basis_independently_rederived"] is True
    assert assertions["every_summary_link_independently_rederived"] is True
    assert assertions["v2_record_fields_byte_identical"] is True
    assert assertions["v2_summary_fields_byte_identical"] is True
    assert assertions["primary_twin_payload_byte_identical"] is True
    assert assertions["no_unlinked_record_carries_a_spine_id"] is True
    assert assertions["every_emitted_spine_id_exists_in_the_spine"] is True
    assert result["counts"]["rederived_link_status"] == {
        "LINKED": 2, "AMBIGUOUS": 1, "NOT_FOUND": 1
    }
    # The fixture cannot satisfy the real ladder constants, so the verifier's
    # own INV-5 gate must fire here too.
    assert assertions["inv5_ladder_reproduction_exact_against_v2_and_the_constant"] is (
        False
    )


def test_spine_link_verifier_catches_a_forged_link(spine_link_tree, tmp_path_factory):
    """Negative control: move one record's id to the wrong spine person and the
    independent re-derivation must refuse it."""

    out = tmp_path_factory.mktemp("spine_link_forged")
    primary, twin = out / "primary", out / "twin"
    with real_inv5_expected():
        for directory in (primary, twin):
            builder.run_spine_link(_spine_link_args(spine_link_tree, directory))
    rows = _rows(primary / builder.RECORD_FILE)
    for row in rows:
        if row["spine_link_status"] == "LINKED":
            row["spine_person_id"] = spine_link_tree["ids"]["ambiguous"][0]
            break
    builder.write_ndjson_gz(primary / builder.RECORD_FILE, rows)
    result = verifier.verify_spine_link(
        verifier.parse_args(
            [
                "--spine-link",
                "--primary", str(primary),
                "--twin", str(twin),
                "--output", str(out / "verification.json"),
            ]
        )
    )
    assert result["assertions"]["every_spine_id_independently_rederived"] is False
    assert "SPINE_ID_NOT_REDERIVED" in result["failures"]
    assert result["status"] == "FAIL"
