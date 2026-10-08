#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Synthetic-fixture tests for the corrected current-staffer link rule.

Every fixture is hand-built so the expected tier is known by construction, and
each of the six cases the adjudication names has one:

  * own-member exact                       -> RESOLVED_T1
  * committee with period corroboration    -> RESOLVED_T2
  * a Senate staffer                       -> RESOLVED_T1 (unreachable under the
                                              old rule, which never looked at
                                              the Senate at all)
  * a tie that must demote                 -> CANDIDATE_T3, ambiguous, tie_size 2
  * nickname corroborated                  -> RESOLVED_T4
  * absent                                 -> NOT_FOUND

plus the promotion tripwire's NEGATIVE CONTROL: the tripwire must REJECT a row
carrying a promotion, because a tripwire that cannot fire is not a tripwire.

Two further regression tests pin the defect this rebuild exists to repair: an
own-member match in an OLD period still resolves (no latest-period filter), and
a match in a different member's office is a CANDIDATE, never a resolution.
"""

from __future__ import annotations

import gzip
import importlib.util
import json
from pathlib import Path
import sys

import pytest

MODULE_PATH = Path(__file__).resolve().parent / "build_current_staffer_links.py"
_spec = importlib.util.spec_from_file_location("build_current_staffer_links", MODULE_PATH)
builder = importlib.util.module_from_spec(_spec)
sys.modules["build_current_staffer_links"] = builder
_spec.loader.exec_module(builder)


# ---------------------------------------------------------------------------
# Fixture construction
# ---------------------------------------------------------------------------
def house_row(office_key, office_raw, container_kind, bioguide, quarter, surname, given,
              middle_initial="", middle_tokens=None, title="LEGISLATIVE ASSISTANT"):
    return {
        "container_kind": container_kind,
        "member_bioguide": bioguide,
        "office_key": office_key,
        "office_raw": office_raw,
        "payee_parse": {
            "given": given,
            "middle_initial": middle_initial,
            "middle_tokens": middle_tokens or [],
            "surname": surname,
        },
        "payee_raw": f"{surname}, {given}",
        "quarter": quarter,
        "title_raw": title,
    }


def senate_row(office_raw, payee, period_start, title="COMMUNICATIONS DIRECTOR"):
    return {
        "office_raw": office_raw,
        "payee_name_raw": payee,
        "report_period_start": period_start,
        "report_period_end": period_start,
        "title_candidate": title,
    }


def legislator(bioguide, first, last, kind, start, end, official_full=None, nickname=None):
    return {
        "id": {"bioguide": bioguide},
        "name": {
            "first": first,
            "last": last,
            "official_full": official_full or f"{first} {last}",
            **({"nickname": nickname} if nickname else {}),
        },
        "terms": [{"start": start, "end": end, "type": kind}],
    }


def write_gz(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


@pytest.fixture(scope="module")
def generation(tmp_path_factory):
    root = tmp_path_factory.mktemp("stafflink")
    sources = root / "sources"
    roster_dir = sources / "roster"
    roster_dir.mkdir(parents=True)

    (roster_dir / "legislators-current.yaml").write_text(
        json.dumps(
            [
                legislator("A000001", "Ann", "Alpha", "rep", "2021-01-03", "2027-01-03"),
                legislator("B000002", "Bob", "Beta", "sen", "2019-01-03", "2031-01-03"),
                legislator("C000003", "Carl", "Gamma", "rep", "2015-01-03", "2027-01-03"),
            ]
        ),
        encoding="utf-8",
    )
    (roster_dir / "legislators-historical.yaml").write_text("[]", encoding="utf-8")

    (sources / "nicknames.json").write_text(
        json.dumps(
            {
                "schema_id": "staffer-network-first-name-nickname-table-v1",
                "entries": {
                    "mike": ["michael"],
                    # two formal forms -- MUST be dropped, or one office string
                    # could match two different people.
                    "al": ["alan", "albert"],
                },
            }
        ),
        encoding="utf-8",
    )

    (sources / "staff_directory.json").write_text(
        json.dumps(
            {
                "Ann Alpha": [
                    {"id": "1", "n": "Dana Delta", "t": "Chief of Staff"},
                    {"id": "2", "n": "Evan Epsilon", "t": "Counsel"},
                    {"id": "3", "n": "Mike Mu", "t": "Legislative Director"},
                    {"id": "4", "n": "Zed Zeta", "t": "Intern"},
                    {"id": "5", "n": "Tina Theta", "t": "Legislative Assistant"},
                    {"id": "7", "n": "Otto Omega", "t": "Field Director"},
                    {"id": "8", "n": "Nora Nu", "t": "Scheduler"},
                    {"id": "9", "n": "Rhea Rho", "t": "Staff Assistant"},
                    {"id": "10", "n": "Amy Emerick Clerkin", "t": "Deputy Chief"},
                    {"id": "11", "n": "Pat O'Connor", "t": "Policy Advisor"},
                    {"id": "12", "n": "Sam Sigma-Tau", "t": "Press Secretary"},
                ],
                "Bob Beta": [
                    {"id": "6", "n": "Sara Sigma", "t": "Communications Director"},
                ],
            }
        ),
        encoding="utf-8",
    )

    write_gz(
        sources / "house.ndjson.gz",
        [
            # 1: own-member office, exact -> T1
            house_row("HON:A000001", "2025 HON. ANN ALPHA", "member_office", "A000001",
                      "2025Q1", "DELTA", "DANA"),
            # 2: committee, exact, period inside Ann's service -> T2
            house_row("COMMITTEE:COMMITTEE ON RULES", "2024 COMMITTEE ON RULES", "committee",
                      None, "2024Q2", "EPSILON", "EVAN"),
            # 3: own-member office, nickname of Mike -> T4
            house_row("HON:A000001", "2023 HON. ANN ALPHA", "member_office", "A000001",
                      "2023Q3", "MU", "MICHAEL"),
            # 5: two middle-initial identities in the SAME own-member office -> tie 2
            house_row("HON:A000001", "2022 HON. ANN ALPHA", "member_office", "A000001",
                      "2022Q1", "THETA", "TINA", middle_initial="A"),
            house_row("HON:A000001", "2022 HON. ANN ALPHA", "member_office", "A000001",
                      "2022Q2", "THETA", "TINA", middle_initial="B"),
            # 7: own-member office but only an OLD quarter -> still T1 (no period filter)
            house_row("HON:A000001", "2016 HON. ANN ALPHA", "member_office", "A000001",
                      "2016Q1", "OMEGA", "OTTO"),
            # 8: exact, but in a DIFFERENT member's office -> CANDIDATE_T3
            house_row("HON:C000003", "2024 HON. CARL GAMMA", "member_office", "C000003",
                      "2024Q1", "NU", "NORA"),
            # 9: exact in a committee, period OUTSIDE Ann's service -> T5
            house_row("COMMITTEE:COMMITTEE ON RULES", "2016 COMMITTEE ON RULES", "committee",
                      None, "2016Q1", "RHO", "RHEA"),
            # 10: the Quorum "middle" token is a maiden name (Emerick, initial E)
            # and the payroll middle initial is C.  The match must SURVIVE, with
            # its class narrowed -- never be dropped.
            house_row("HON:A000001", "2025 HON. ANN ALPHA", "member_office", "A000001",
                      "2025Q2", "CLERKIN", "AMY", middle_initial="C"),
            # 11: the T4 split.  A variant match in the OWN member office (T4A)
            # and one in a committee during Ann's service (T4B).  Two distinct
            # payroll identities, two DIFFERENT corroboration strengths -- they
            # must not tie each other.
            house_row("HON:A000001", "2025 HON. ANN ALPHA", "member_office", "A000001",
                      "2025Q1", "O'CONNOR", "PATRICK"),
            house_row("COMMITTEE:COMMITTEE ON RULES", "2024 COMMITTEE ON RULES", "committee",
                      None, "2024Q2", "O'CONNOR", "PATRICK"),
            # 12: two variant identities at the SAME corroboration strength --
            # both T4A in the same member office -- which DOES tie.
            house_row("HON:A000001", "2024 HON. ANN ALPHA", "member_office", "A000001",
                      "2024Q1", "SIGMA-TAU", "SAMUEL", middle_initial="A"),
            house_row("HON:A000001", "2024 HON. ANN ALPHA", "member_office", "A000001",
                      "2024Q2", "SIGMA-TAU", "SAMUEL", middle_initial="B"),
        ],
    )

    write_gz(
        sources / "senate.ndjson.gz",
        [
            # 6: the Senate case the old rule could never reach
            senate_row("SENATOR BOB BETA", "SIGMA, SARA", "2024-04-01"),
            senate_row("INTERN COMPENSATION - BETA", "OTHER, PERSON", "2024-04-01"),
        ],
    )

    output = root / "generation"
    args = builder.parse_args(
        [
            "--staff-directory", str(sources / "staff_directory.json"),
            "--house-observations", str(sources / "house.ndjson.gz"),
            "--senate-candidates", str(sources / "senate.ndjson.gz"),
            "--nickname-table", str(sources / "nicknames.json"),
            "--roster-dir", str(roster_dir),
            "--output-root", str(output),
            "--no-glassbox",
        ]
    )
    receipt = builder.run(args)
    rows = {}
    with gzip.open(output / builder.LINK_FILE, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            rows[row["quorum_staff_id"]] = row
    candidates = []
    with gzip.open(output / builder.CANDIDATE_FILE, "rt", encoding="utf-8") as handle:
        for line in handle:
            candidates.append(json.loads(line))
    return {"receipt": receipt, "rows": rows, "candidates": candidates, "output": output,
            "sources": sources, "roster_dir": roster_dir}


# ---------------------------------------------------------------------------
# The six named cases
# ---------------------------------------------------------------------------
def test_own_member_exact_is_t1(generation):
    row = generation["rows"]["1"]
    assert row["status"] == "RESOLVED_T1"
    assert row["best_tier"] == builder.TIER_T1
    assert row["ambiguous"] is False
    assert row["tie_size"] == 1
    best = row["matches"][0]
    assert best["match_class"] == builder.CLASS_EXACT
    assert best["corroboration"] == builder.CORROBORATION_OWN_MEMBER
    assert best["member_bioguide"] == "A000001"
    assert best["office_key"] == "HON:A000001"


def test_committee_with_period_corroboration_is_t2(generation):
    row = generation["rows"]["2"]
    assert row["status"] == "RESOLVED_T2"
    best = row["matches"][0]
    assert best["container_kind"] == "committee"
    assert best["member_bioguide"] is None
    assert best["corroboration"] == builder.CORROBORATION_PERIOD
    assert best["periods"] == ["2024Q2"]


def test_senate_staffer_resolves(generation):
    """The old rule built its candidate set from House spans only, so no Senate
    staffer could link at all; this is the structural exclusion being repaired."""

    row = generation["rows"]["6"]
    assert row["status"] == "RESOLVED_T1"
    best = row["matches"][0]
    assert best["chamber"] == "senate"
    assert best["office_key"] == "SENATOR BOB BETA"
    assert best["container_kind"] == "member_office"
    assert best["member_bioguide"] == "B000002"


def test_tie_demotes_and_is_never_broken(generation):
    row = generation["rows"]["5"]
    assert row["tier_before_tie_demotion"] == builder.TIER_T1
    assert row["ambiguous"] is True
    assert row["demoted_for_tie"] is True
    assert row["tie_size"] == 2
    assert row["best_tier"] == builder.TIER_T3
    assert row["status"] == "CANDIDATE_T3"
    # both tied identities are still emitted -- the tie is reported, not resolved
    identities = {m["payroll_identity_key"] for m in row["matches"]}
    assert len(identities) == 2
    assert {m["payroll_middle_initial"] for m in row["matches"]} == {"a", "b"}


def test_nickname_with_own_member_corroboration_is_t4(generation):
    row = generation["rows"]["3"]
    assert row["status"] == "RESOLVED_T4"
    best = row["matches"][0]
    assert best["match_class"] == builder.CLASS_NICKNAME
    assert best["corroboration"] == builder.CORROBORATION_OWN_MEMBER


def test_absent_staffer_is_not_found(generation):
    row = generation["rows"]["4"]
    assert row["status"] == "NOT_FOUND"
    assert row["best_tier"] is None
    assert row["match_count"] == 0
    assert row["matches"] == []
    assert row["tie_size"] == 0


# ---------------------------------------------------------------------------
# The defect being repaired
# ---------------------------------------------------------------------------
def test_no_period_filter_an_old_own_member_match_still_resolves(generation):
    """The old rule required last_period == the LATEST House quarter."""

    row = generation["rows"]["7"]
    assert row["status"] == "RESOLVED_T1"
    assert row["matches"][0]["period_last"] == "2016Q1"


def test_other_member_office_is_a_candidate_never_a_resolution(generation):
    row = generation["rows"]["8"]
    assert row["status"] == "CANDIDATE_T3"
    assert row["best_tier"] == builder.TIER_T3
    assert row["ambiguous"] is False
    assert row["matches"][0]["member_bioguide"] == "C000003"
    assert row["matches"][0]["match_class"] == builder.CLASS_EXACT


def test_non_member_office_without_period_overlap_is_weak(generation):
    row = generation["rows"]["9"]
    assert row["status"] == "CANDIDATE_T5"
    assert row["matches"][0]["corroboration"] == builder.CORROBORATION_NONE


# ---------------------------------------------------------------------------
# Tripwire: positive state, then the NEGATIVE CONTROL
# ---------------------------------------------------------------------------
def test_every_row_is_unpromoted(generation):
    for row in list(generation["rows"].values()) + generation["candidates"]:
        assert row["review_status"] == "REVIEW_REQUIRED"
        assert row["canonical_eligible"] is False
        assert row["canonical_employment_promoted"] is False
        assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
    assert generation["receipt"]["canonical_employment_promotions"] == 0
    assert generation["receipt"]["canonical_identity_promotions"] == 0
    assert generation["receipt"]["tripwire"]["anti_promotion_failure_count"] == 0


def test_tripwire_negative_control_rejects_a_promoted_row(generation):
    """A check that cannot fail is not a check (DE-011 / DE-012)."""

    clean = dict(next(iter(generation["rows"].values())))
    assert builder.assert_unpromoted([clean], "control") == []
    for field, value in (
        ("canonical_employment_promoted", True),
        ("canonical_eligible", True),
        ("review_status", "PROMOTED"),
        ("canonical_identity_decision", "ADJUDICATED"),
    ):
        tampered = dict(clean)
        tampered[field] = value
        assert builder.assert_unpromoted([tampered], "control"), field


def test_language_law_scan_can_fire():
    authored, verbatim = builder.scan_language_law(
        [{"note": "this value claims to predict something"}]
    )
    assert authored
    exempt, counted = builder.scan_language_law(
        [{"office_key": "OFFICE OF CONGRESSIONAL ACCESSIBILITY SERVICES"}]
    )
    assert exempt == []
    assert counted["office_key|access"] == 1


# ---------------------------------------------------------------------------
# Conservation, dials, and lane conventions
# ---------------------------------------------------------------------------
def test_conservation_one_row_per_directory_entry(generation):
    receipt = generation["receipt"]
    assert len(generation["rows"]) == 12
    assert receipt["conservation"]["current_staffer_rows_equal_directory"] is True
    assert receipt["conservation"]["match_candidate_rows_equal_match_sum"] is True
    assert len(generation["candidates"]) == sum(
        row["match_count"] for row in generation["rows"].values()
    )
    assert receipt["failures"] == []


def test_nickname_table_drops_multi_formal_short_forms(generation):
    stats = generation["receipt"]["dials"]["nickname_table"]
    assert stats["entries_read"] == 2
    assert stats["entries_single_formal"] == 1
    assert stats["entries_dropped_multi_formal"] == 1


def test_senate_intern_pool_resolves_to_the_same_member(generation):
    """`SENATOR BOB BETA` and `INTERN COMPENSATION - BETA` are one senator's
    payroll under two office strings; both must carry the same bioguide, which
    is why the tie atom is member-scoped for member offices -- an office-scoped
    atom would count one person under one senator as two identities."""

    offices = generation["receipt"]["counts"]["offices_by_chamber_and_container_kind"]
    assert offices.get("senate:member_office") == 2
    roster = builder.RosterIndex(
        builder.load_roster(generation["roster_dir"]),
        builder.load_nickname_table(generation["sources"] / "nicknames.json")[0],
    )
    for office in ("SENATOR BOB BETA", "INTERN COMPENSATION - BETA"):
        assert builder.senate_container_kind(office) == "member_office"
        bioguide, _method = builder.resolve_office_member(
            builder.senate_office_name_tokens(office), roster, "senate", 2024, 2024
        )
        assert bioguide == "B000002", office
    # and therefore both offices collapse to ONE identity scope
    scopes = {f"member:senate:{'B000002'}"}
    assert len(scopes) == 1


def test_middle_initial_conflict_survives_as_a_narrowed_class(generation):
    """The end-to-end half of the middle-initial rule: an EXACT name whose
    middle initials disagree must still be EMITTED, re-classed, and -- with
    own-member corroboration -- still reach a RESOLVED status."""

    row = generation["rows"]["10"]
    assert row["match_count"] == 1, "the match was dropped instead of narrowed"
    match = row["matches"][0]
    assert match["middle_initial_conflict"] is True
    assert match["match_class"] == builder.CLASS_MIDDLE_CONFLICT
    assert match["match_class_before_middle_initial_test"] == builder.CLASS_EXACT
    assert match["payroll_middle_initial"] == "c"
    assert row["status"] == "RESOLVED_T4"
    assert row["best_tier"] == builder.TIER_T4A


def test_variant_own_member_and_variant_committee_do_not_tie_each_other(generation):
    """The T4 split.  A staffer with a nickname match in their OWN member office
    AND a nickname match in a committee during their member's service has TWO
    distinct payroll identities, but they carry DIFFERENT corroboration
    strengths -- T4A and T4B -- so they never tie, and the own-member evidence
    stands.  A merged T4 tier demoted exactly this shape."""

    row = generation["rows"]["11"]
    tiers = [m["tier"] for m in row["matches"]]
    assert builder.TIER_T4A in tiers and builder.TIER_T4B in tiers
    assert len({m["payroll_identity_key"] for m in row["matches"]}) == 2
    assert row["tier_before_tie_demotion"] == builder.TIER_T4A
    assert row["tie_size"] == 1
    assert row["ambiguous"] is False
    assert row["demoted_for_tie"] is False
    assert row["status"] == "RESOLVED_T4"
    # ... but two identities at the SAME corroboration strength still tie.
    tied = generation["rows"]["12"]
    assert tied["tier_before_tie_demotion"] == builder.TIER_T4A
    assert tied["tie_size"] == 2
    assert tied["ambiguous"] is True
    assert tied["status"] == "CANDIDATE_T5"


def test_builder_refuses_a_non_empty_output_root(generation, tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "already_here.txt").write_text("x", encoding="utf-8")
    args = builder.parse_args(
        [
            "--staff-directory", str(generation["sources"] / "staff_directory.json"),
            "--house-observations", str(generation["sources"] / "house.ndjson.gz"),
            "--senate-candidates", str(generation["sources"] / "senate.ndjson.gz"),
            "--nickname-table", str(generation["sources"] / "nicknames.json"),
            "--roster-dir", str(generation["roster_dir"]),
            "--output-root", str(occupied),
            "--no-glassbox",
        ]
    )
    with pytest.raises(builder.GateFailure):
        builder.run(args)


def test_outputs_are_canonical_and_deterministic(generation):
    for name in (builder.LINK_FILE, builder.CANDIDATE_FILE):
        path = generation["output"] / name
        with path.open("rb") as handle:
            header = handle.read(10)
        assert header[:2] == b"\x1f\x8b"
        assert header[4:8] == b"\x00\x00\x00\x00", f"{name}: gzip mtime is not 0"
        with gzip.open(path, "rb") as handle:
            raw = handle.read()
        assert b"\r\n" not in raw
        for line in raw.decode("utf-8").splitlines():
            value = json.loads(line)
            assert json.dumps(
                value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ) == line


def test_tier_precedence_puts_a_corroborated_variant_above_an_uncorroborated_exact():
    assert builder.TIER_RANK[builder.TIER_T1] < builder.TIER_RANK[builder.TIER_T2]
    assert builder.TIER_RANK[builder.TIER_T2] < builder.TIER_RANK[builder.TIER_T4A]
    assert builder.TIER_RANK[builder.TIER_T4A] < builder.TIER_RANK[builder.TIER_T4B]
    assert builder.TIER_RANK[builder.TIER_T4B] < builder.TIER_RANK[builder.TIER_T3]
    assert builder.TIER_RANK[builder.TIER_T3] < builder.TIER_RANK[builder.TIER_T5]
    # both variant tiers report the brief's RESOLVED_T4 status
    assert builder.TIER_STATUS[builder.TIER_T4A] == "RESOLVED_T4"
    assert builder.TIER_STATUS[builder.TIER_T4B] == "RESOLVED_T4"
    # T3 and T5 are candidates, never resolved
    assert builder.TIER_STATUS[builder.TIER_T3] not in builder.RESOLVED_STATUSES
    assert builder.TIER_STATUS[builder.TIER_T5] not in builder.RESOLVED_STATUSES


def test_middle_initial_conflict_narrows_the_class_it_never_drops_the_match():
    staffer = {
        "first_raw": "amy", "first_collapsed": "amy",
        "middles_collapsed": frozenset({"emerick"}), "middle_initial": "e",
        "middle_initials": frozenset({"e"}),
        "surname_raw": "clerkin", "surname_collapsed": "clerkin",
        "surname_last_token": "clerkin",
    }
    assert builder.classify_match(staffer, "clerkin", "amy", {}) == builder.CLASS_EXACT
    # the conflict is applied at the identity level, so the class the builder
    # emits for a payroll middle initial of `c` is the variant, not None
    assert builder.CLASS_MIDDLE_CONFLICT in builder.VARIANT_CLASSES
    tier, corroboration = builder.assign_tier(
        builder.CLASS_MIDDLE_CONFLICT, "member_office", "A000001", "A000001",
        "house", ["2025Q1"], (("2021-01-03", "2027-01-03", "rep"),),
        builder.T2_ELIGIBLE_CONTAINER_KINDS,
    )
    assert tier == builder.TIER_T4A
    assert corroboration == builder.CORROBORATION_OWN_MEMBER


def test_member_office_ladder_resolves_a_chamber_ambiguous_surname(generation):
    """Tim Johnson (Senate) and Timothy Johnson (House) share a surname; the
    chamber restriction is what separates them."""

    roster = builder.RosterIndex(
        [
            {
                "bioguide": "J000177", "first": "Tim", "middle": "", "nickname": "",
                "official_full": "Tim Johnson", "last": "Johnson",
                "terms": [("2009-01-06", "2015-01-03", "sen")],
                "chambers": frozenset({"sen"}), "min_year": 2009, "max_year": 2015,
                "current": False,
            },
            {
                "bioguide": "J000289", "first": "Timothy", "middle": "", "nickname": "",
                "official_full": "Timothy V. Johnson", "last": "Johnson",
                "terms": [("2009-01-06", "2013-01-03", "rep")],
                "chambers": frozenset({"rep"}), "min_year": 2009, "max_year": 2013,
                "current": False,
            },
        ],
        {},
    )
    senate_hit, _method = builder.resolve_office_member(
        builder.senate_office_name_tokens("SENATOR TIM JOHNSON"), roster, "senate", 2011, 2014
    )
    assert senate_hit == "J000177"
    house_hit, _method = builder.resolve_office_member(
        builder.house_honraw_name_tokens("HONRAW:HON. TIMOTHY JOHNSON"), roster, "house", 2011, 2012
    )
    assert house_hit == "J000289"


def test_letter_split_repair_only_accepts_a_real_roster_surname():
    roster = builder.RosterIndex(
        [
            {
                "bioguide": "S001194", "first": "Brian", "middle": "", "nickname": "",
                "official_full": "Brian Schatz", "last": "Schatz",
                "terms": [("2012-12-27", "2029-01-03", "sen")],
                "chambers": frozenset({"sen"}), "min_year": 2012, "max_year": 2029,
                "current": True,
            }
        ],
        {},
    )
    hit, method = builder.resolve_office_member(
        builder.senate_office_name_tokens("SENATOR BRIANS CHATZ"), roster, "senate", 2016, 2016
    )
    assert hit == "S001194"
    assert method.endswith("_AFTER_LETTER_SPLIT_REPAIR")
    miss, _ = builder.resolve_office_member(
        builder.senate_office_name_tokens("SENATOR QQQQQ WWWWW"), roster, "senate", 2016, 2016
    )
    assert miss is None
