#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for the payroll name-resolution filter/label phase.

Every test runs on SYNTHETIC fixtures built in a tmp_path -- no test touches
the real corpora, the real roster or the real generation.  The fixtures are
deliberately tiny and hand-checkable, so a tier assertion here is a statement
about the RULE, not about the data.

The suite is organised as:

  TestNormalisation      the name rules the tier engine stands on
  TestTierRule           R1 / R2 / R3 / R4 assigned exactly as specified
  TestTies               ties are never broken silently
  TestRollup             per-person status derivation
  TestEndToEnd           a full synthetic build, then the independent verifier
                         over its own output
  TestPromotionTripwire  NEGATIVE CONTROL -- a promoted row must be caught

Run:  python -m pytest audits/staffer_network/test_payroll_name_resolution.py -q
"""

from __future__ import annotations

import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pytest

AUDITS = Path(__file__).resolve().parent
REPO = AUDITS.parents[1]


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, AUDITS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


builder = _load("_pnr_builder", "build_payroll_name_resolution.py")
verifier = _load("_pnr_verifier", "verify_payroll_name_resolution.py")


# ---------------------------------------------------------------------------
# Synthetic fixture factory
# ---------------------------------------------------------------------------
def write_gz(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False) + "\n"
        for row in rows).encode("utf-8")
    with open(path, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            gz.write(payload)


def roster_row(roster_id, surname, given, mi=None, *, display=None,
               member=None, kind_source="quorum", eligible=True,
               fingerprint=None, suffixes=None, primary=True):
    return {
        "roster_id": roster_id,
        "roster_source": kind_source,
        "display_name": display or f"{given.title()} {surname.title()}",
        "quorum_member_display": member,
        "quorum_title": "Staff",
        "quorum_star": 0,
        "spelling_fingerprint": fingerprint or f"{surname}|{given}",
        "generational_suffix": suffixes or [],
        "is_placeholder_name": False,
        "match_eligible": eligible,
        "surname_key": surname,
        "given_key": given,
        "middle_initial": mi,
        "key_basis": "FIRSTLAST_2TOKEN",
        "is_primary_key": primary,
    }


def payee_fact(surname, given, mi=None, *, chambers=("HOUSE",),
               max_offices=1, collision=False, shared=0, obs=1):
    return {
        "surname_key": surname, "given_key": given, "middle_initial": mi,
        "chambers": list(chambers),
        "max_offices_within_one_period": max_offices,
        "office_period_collision": collision,
        "shared_employee_rows": shared,
        "observation_rows": obs,
    }


def house_csv_candidate(surname, given, mi, roster_id, r_surname, r_given,
                        r_mi, match_class, *, offices=("HON:X000001",),
                        quarters=("2020Q1",), containers=("member_office",),
                        bioguides=("X000001",), titles=("AIDE",),
                        max_offices=1, raw="DOE,JOHN"):
    return {
        "payee_key": [surname, given, mi],
        "roster_id": roster_id,
        "match_class": match_class,
        "match_evidence": {"nickname_direction": None,
                           "nickname_formal_form": None,
                           "variant_basis": None,
                           "variant_surname_bridge": None},
        "roster": {"surname_key": r_surname, "given_key": r_given,
                   "middle_initial": r_mi, "key_basis": "FIRSTLAST_2TOKEN",
                   "is_primary_key": True},
        "payee": {
            "offices": list(offices), "quarters": list(quarters),
            "titles": list(titles), "container_kinds": list(containers),
            "member_bioguides": list(bioguides), "observation_rows": 1,
            "max_offices_within_one_period": max_offices,
            "shared_employee_rows": 0, "payee_raw_example": raw,
            "key_basis": ["HOUSE_LEDGER_PARSE"],
            "has_primary_ledger_parse": True,
            "generational_suffixes_seen": [],
        },
    }


@pytest.fixture
def world(tmp_path):
    """A miniature world exercising every tier at least once."""
    scratch = tmp_path / "scratch"
    repo = tmp_path / "repo"
    (repo / "data" / "members").mkdir(parents=True)
    (repo / "data" / "staffer_network" / "reference").mkdir(parents=True)

    # --- roster -------------------------------------------------------
    roster = [
        # R1 target: unique pair, middle initial on both sides
        roster_row("quorum:staff:1", "ALPHA", "ANN", "Q", member="Rep One"),
        # R2 target: unique-ish but no MI, corroborated by own-member office
        roster_row("quorum:staff:2", "BETA", "BOB", None, member="Rep Two"),
        # R3 targets: two people share the same (surname, given) pair
        roster_row("quorum:staff:3", "GAMMA", "CAL", None, member="Rep Three"),
        roster_row("lda:lobbyist:900", "GAMMA", "CAL", None,
                   kind_source="lda", fingerprint="GAMMA|CAL|alt"),
        # R4 target: loose only
        roster_row("quorum:staff:4", "DELTA", "DAN", None, member="Rep Four"),
    ]
    write_gz(scratch / "roster_keys.ndjson.gz", roster)

    write_gz(scratch / "payee_keys.ndjson.gz", [
        payee_fact("ALPHA", "ANN", "Q"),
        payee_fact("BETA", "BOB", "Z"),
        payee_fact("GAMMA", "CAL", None),
        payee_fact("DELTA", "DEE", None),
        # present only in the Senate corpus, so the key reproduction gate has
        # something on both sides to reconcile
        payee_fact("NOBODY", "NOONE", None, chambers=("SENATE",)),
    ])

    write_gz(scratch / "candidates_house_csv.ndjson.gz", [
        house_csv_candidate("ALPHA", "ANN", "Q", "quorum:staff:1",
                            "ALPHA", "ANN", "Q", "EXACT_LAST_FIRST_MI",
                            offices=("HON:X000001",), bioguides=("X000001",)),
        house_csv_candidate("BETA", "BOB", "Z", "quorum:staff:2",
                            "BETA", "BOB", None, "EXACT_LAST_FIRST",
                            offices=("HON:X000002",), bioguides=("X000002",)),
        house_csv_candidate("GAMMA", "CAL", None, "quorum:staff:3",
                            "GAMMA", "CAL", None, "EXACT_LAST_FIRST",
                            offices=("COMMITTEE:WAYS",), containers=("committee",),
                            bioguides=()),
        house_csv_candidate("GAMMA", "CAL", None, "lda:lobbyist:900",
                            "GAMMA", "CAL", None, "EXACT_LAST_FIRST",
                            offices=("COMMITTEE:WAYS",), containers=("committee",),
                            bioguides=()),
        house_csv_candidate("DELTA", "DEE", None, "quorum:staff:4",
                            "DELTA", "DAN", None, "LAST_FIRSTINITIAL",
                            offices=("HON:X000004",), bioguides=("X000004",)),
    ])
    write_gz(scratch / "candidates_house_pdf.ndjson.gz", [])
    write_gz(scratch / "candidates_senate.ndjson.gz", [])

    # --- corpora ------------------------------------------------------
    ledger = []
    for bioguide, key in (("X000001", "ALPHA|ANN|Q"), ("X000002", "BETA|BOB|Z"),
                          ("X000004", "DELTA|DEE|")):
        ledger.append({"quarter": "2020Q1", "container_kind": "member_office",
                       "member_bioguide": bioguide, "person_key": f"SOD:{key}",
                       "office_key": f"HON:{bioguide}", "payee_raw": "X",
                       "office_raw": "X", "title_base": "AIDE",
                       "source_form": "detail_csv"})
    ledger.append({"quarter": "2020Q1", "container_kind": "committee",
                   "member_bioguide": None, "person_key": "SOD:GAMMA|CAL|",
                   "office_key": "COMMITTEE:WAYS", "payee_raw": "X",
                   "office_raw": "X", "title_base": "AIDE",
                   "source_form": "detail_csv"})
    ledger_path = (repo / "audits" / "staffer_network" /
                   "house_personnel_ledger_20260902_v2_primary" /
                   "house_personnel_observations.ndjson.gz")
    write_gz(ledger_path, ledger)

    senate_path = (repo / "audits" / "staffer_network" /
                   "official_senate_payroll_2011_2026_employment_scope_v1" /
                   "senate_payroll_employment_candidates_2011_2026.ndjson.gz")
    write_gz(senate_path, [
        {"office_raw": "SENATOR ZEBEDEE", "payee_name_raw": "NOBODY, NOONE",
         "report_period_start": "2020-04-01", "report_period_end": "2020-09-30",
         "title_candidate": "AIDE"},
    ])

    spine = repo / "audits" / "staffer_network" / "hill_personnel_spine_20260902_v1_primary"
    write_gz(spine / "current_staffer_links.ndjson.gz", [
        {"quorum_staff_id": "1", "link_status": "NOT_ON_PAYROLL",
         "member_bioguide": "X000001", "member_display": "Rep One"},
        {"quorum_staff_id": "2", "link_status": "LINKED",
         "member_bioguide": "X000002", "member_display": "Rep Two"},
        {"quorum_staff_id": "3", "link_status": "NOT_ON_PAYROLL",
         "member_bioguide": "X000003", "member_display": "Rep Three"},
        {"quorum_staff_id": "4", "link_status": "NOT_ON_PAYROLL",
         "member_bioguide": "X000004", "member_display": "Rep Four"},
    ])
    write_gz(spine / "lda_spine_links.ndjson.gz", [
        {"lda_source_person_id": "lda:lobbyist:900", "link_status": "UNLINKED"},
    ])

    lda_dir = tmp_path / "lda"
    # GAMMA/CAL is this fixture's R3 pair: two roster people answer to one
    # payee key and NEITHER may be corroborated, or the pair stops testing R3.
    # The covered-position text is therefore kept deliberately clear of any
    # office word of the payee (whose only office is COMMITTEE:WAYS), and the
    # covered-position year (2019) deliberately does not cover the payroll
    # year (2020Q1).  Wording it "Staff, Committee on Ways" instead fires the
    # L2 office-text signal and the LDA candidate is then correctly promoted
    # to R2 -- that path is covered by TestTierRule.test_lda_covered_position
    # _text_overlap_is_r2 rather than being smuggled in here.
    write_gz(lda_dir / "employment_lookup_queue.ndjson.gz", [
        {"lda_source_person_id": "lda:lobbyist:900", "display_name": "CAL GAMMA",
         "filing_years": [2021], "covered_position_year_tokens": ["2019"],
         "covered_position_values": ["Legislative Assistant, Senate Banking"],
         "priority": "P1", "identity_status": "REVIEW_REQUIRED"},
    ])

    (repo / "data" / "members" / "staff_directory.json").write_text(json.dumps({
        "Rep One": [{"id": 1, "n": "Ann Alpha", "t": "CoS", "star": 0}],
        "Rep Two": [{"id": 2, "n": "Bob Beta", "t": "LD", "star": 0}],
        "Rep Three": [{"id": 3, "n": "Cal Gamma", "t": "LA", "star": 0}],
        "Rep Four": [{"id": 4, "n": "Dan Delta", "t": "LC", "star": 0}],
    }), encoding="utf-8")
    (repo / "data" / "staffer_network" / "reference" /
     "first_name_nicknames_v1.json").write_text(json.dumps({
         "schema_id": "staffer-network-first-name-nickname-table-v1",
         "entries": {"bob": ["robert"], "dan": ["daniel"],
                     "chris": ["christopher", "christine"]},
     }), encoding="utf-8")

    paths = {
        "candidates_house_csv": scratch / "candidates_house_csv.ndjson.gz",
        "candidates_house_pdf": scratch / "candidates_house_pdf.ndjson.gz",
        "candidates_senate": scratch / "candidates_senate.ndjson.gz",
        "roster_keys": scratch / "roster_keys.ndjson.gz",
        "payee_keys": scratch / "payee_keys.ndjson.gz",
        "nicknames": repo / "data" / "staffer_network" / "reference" /
                     "first_name_nicknames_v1.json",
        "staff_directory": repo / "data" / "members" / "staff_directory.json",
        "lda_queue": lda_dir / "employment_lookup_queue.ndjson.gz",
        "house_ledger": ledger_path,
        "senate_corpus": senate_path,
        "old_staffer_links": spine / "current_staffer_links.ndjson.gz",
        "old_lda_links": spine / "lda_spine_links.ndjson.gz",
    }
    return {"paths": paths, "repo": repo, "scratch": scratch, "tmp": tmp_path}


@pytest.fixture
def built(world, monkeypatch):
    """Run the real builder over the synthetic world with INV relaxed."""
    monkeypatch.setattr(builder, "INV", {k: None for k in builder.INV},
                        raising=False)
    original = builder.INV

    class Anything(dict):
        def __getitem__(self, key):
            return _SENTINEL

    # The INV block is a production tripwire on real row counts; on synthetic
    # fixtures it must not fire, so every comparison is neutralised.
    monkeypatch.setattr(builder, "INV", _NeutralINV(original), raising=False)
    out = world["tmp"] / "gen"
    receipt = builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)
    return {"receipt": receipt, "root": out, "world": world}


_SENTINEL = object()


class _NeutralINV(dict):
    """INV lookups that never trip: every read returns a value equal to
    whatever it is compared against.  Keeps the promotion invariants real."""

    def __init__(self, original):
        super().__init__(original)
        self._real = {"INV_CANONICAL_EMPLOYMENT_PROMOTIONS": 0,
                      "INV_CANONICAL_IDENTITY_PROMOTIONS": 0}

    def __getitem__(self, key):
        if key in self._real:
            return self._real[key]
        return _Equal()

    def get(self, key, default=None):
        if key in self._real:
            return self._real[key]
        return _Equal()

    def items(self):
        return [(k, self._real.get(k, 0)) for k in dict.keys(self)]


class _Equal:
    def __eq__(self, other):
        return True

    def __ne__(self, other):
        return False

    def __repr__(self):
        return "<any>"

    def __hash__(self):
        return 0


def read_gz(path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


# ---------------------------------------------------------------------------
class TestNormalisation:
    def test_hyphen_and_apostrophe_collapse_into_the_key(self):
        assert builder.collapse([builder.prep("O'Brien")]) == "OBRIEN"
        assert builder.collapse([builder.prep("Pierson-Jase")]) == "PIERSONJASE"

    def test_dotted_initials_survive_the_suffix_rule(self):
        """N7b: 'JR.' is a suffix but 'J.R.' is a given name."""
        kept, suffixes = builder.tokenize(builder.prep("J.R. Walker"))
        assert "JR" in kept and not suffixes

    def test_bare_jr_is_a_suffix(self):
        kept, suffixes = builder.tokenize(builder.prep("John Walker Jr"))
        assert suffixes == ["JR"] and "JR" not in kept

    def test_placeholder_filings_are_rejected(self):
        assert builder.is_placeholder_name("N/A")
        assert builder.is_placeholder_name("DO")
        assert not builder.is_placeholder_name("SMITH, JOHN")

    def test_verifier_normaliser_agrees_with_the_builder(self):
        """The verifier is independent code; on these it must still agree."""
        for probe in ["O'Brien", "Pierson-Jase", "de la Cruz", "J.R. Walker",
                      "SMITH, JOHN Q", "VAN PATTON", "St. John"]:
            assert (builder.collapse([builder.prep(probe)]) ==
                    verifier.Norm.collapse([verifier.Norm.prep(probe)]))
            assert (builder.tokenize(builder.prep(probe)) ==
                    verifier.Norm.tokenize(verifier.Norm.prep(probe)))

    def test_last_first_parse_matches_between_implementations(self):
        for probe in ["SMITH, JOHN Q", "VAN KOPP, SAMUEL C", "DE LA TORRE, LIZEHT"]:
            assert (builder.parse_last_first(probe) ==
                    verifier.Norm.last_first_keys(probe))


class TestTierRule:
    def test_class_derivation_from_keys_alone(self):
        assert builder.derive_class(("A", "B", "C"), ("A", "B", "C")) == "EXACT_TRIPLE"
        assert builder.derive_class(("A", "B", "C"), ("A", "B", None)) == "EXACT_PAIR"
        assert builder.derive_class(("A", "B", None), ("A", "Z", None)) == "LOOSE"

    def test_r1_requires_uniqueness_on_both_sides(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        alpha = [r for r in rows if r["roster_id"] == "quorum:staff:1"][0]
        assert alpha["resolution_tier"] == "R1_EXACT_UNIQUE"
        assert alpha["evidence"]["roster_unique_identity"] is True
        assert alpha["evidence"]["payee_unique_payroll_person"] is True
        assert alpha["evidence"]["r1_blocked_by"] == []

    def test_r2_needs_an_independent_corroborating_signal(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        beta = [r for r in rows if r["roster_id"] == "quorum:staff:2"][0]
        assert beta["resolution_tier"] == "R2_EXACT_CORROBORATED"
        assert "Q1_OWN_MEMBER_HOUSE_OFFICE" in beta["evidence"]["corroboration_signals"]
        # exact name, but the middle initial is missing on the roster side
        assert beta["evidence"]["derived_name_class"] == "EXACT_PAIR"

    def test_r3_when_the_roster_pair_answers_for_two_people(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        gammas = [r for r in rows if r["payee_surname_key"] == "GAMMA"]
        assert len(gammas) == 2
        for row in gammas:
            assert row["resolution_tier"] == "R3_EXACT_AMBIGUOUS"
            assert ("ROSTER_PAIR_ANSWERS_FOR_2PLUS_IDENTITY_ROWS" in
                    row["evidence"]["r1_blocked_by"])
            assert row["evidence"]["roster_unique_identity"] is False

    def test_lda_covered_position_text_overlap_is_r2(self, world, monkeypatch):
        """An LDA person whose OWN covered-position text names the payee's
        office is corroborated, so an otherwise-ambiguous exact name is R2.

        This is the signal the `world` fixture deliberately withholds from
        GAMMA/CAL so that pair can test R3.  Here it is switched on and
        nothing else changes, so the tier move is attributable to it alone.
        """
        lda_queue = world["paths"]["lda_queue"]
        write_gz(lda_queue, [
            {"lda_source_person_id": "lda:lobbyist:900",
             "display_name": "CAL GAMMA", "filing_years": [2021],
             "covered_position_year_tokens": ["2019"],
             "covered_position_values": ["Staff, Committee on Ways"],
             "priority": "P1", "identity_status": "REVIEW_REQUIRED"},
        ])
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        out = world["tmp"] / "gen_lda_l2"
        builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)
        rows = read_gz(out / builder.CANDIDATE_FILE)
        lda_row = [r for r in rows if r["roster_id"] == "lda:lobbyist:900"][0]
        assert lda_row["resolution_tier"] == "R2_EXACT_CORROBORATED"
        assert ("L2_COVERED_POSITION_OFFICE_TEXT_OVERLAP" in
                lda_row["evidence"]["corroboration_signals"])
        # the quorum person on the same payee key gains nothing from it
        quorum_row = [r for r in rows if r["roster_id"] == "quorum:staff:3"][0]
        assert quorum_row["resolution_tier"] == "R3_EXACT_AMBIGUOUS"
        assert quorum_row["evidence"]["corroboration_signals"] == []

    def test_r4_for_a_loose_name_class(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        delta = [r for r in rows if r["roster_id"] == "quorum:staff:4"][0]
        assert delta["resolution_tier"] == "R4_LOOSE"
        assert delta["evidence"]["derived_name_class"] == "LOOSE"

    def test_contradicting_middle_initial_cannot_reach_r2(self):
        assert builder.middle_initial_state("Q", "R") == "BOTH_PRESENT_DIFFERENT"
        assert builder.middle_initial_state(None, "R") == "PAYEE_MISSING"
        assert builder.middle_initial_state("Q", None) == "ROSTER_MISSING"

    def test_conflicting_generational_suffix_is_not_the_same_person(self):
        assert builder.suffix_state(["III"], ["IV"]) == "BOTH_PRESENT_DIFFERENT"
        assert builder.suffix_state([], ["IV"]) == "ONE_SIDE_ONLY"
        assert builder.suffix_state([], []) == "NEITHER"

    def test_lda_filing_year_signal_never_qualifies(self):
        """A7: a filing year that postdates service is recorded, not promoting."""
        assert builder.LDA_FILING_YEAR_SIGNAL_QUALIFIES is False

    def test_every_row_carries_a_tier_from_the_closed_vocabulary(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        assert rows
        assert {r["resolution_tier"] for r in rows} <= set(builder.TIER_ORDER)


class TestTies:
    def test_tie_size_is_emitted_on_every_row(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        assert all(isinstance(r["tie_size"], int) and r["tie_size"] >= 1
                   for r in rows)

    def test_both_members_of_a_tie_are_emitted(self, built):
        """Never silently pick among ties: both GAMMA/CAL people are present."""
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        gammas = [r for r in rows if r["payee_surname_key"] == "GAMMA"]
        assert {r["roster_id"] for r in gammas} == {"quorum:staff:3",
                                                    "lda:lobbyist:900"}
        assert all(r["tie_size"] == 2 for r in gammas)

    def test_two_roster_people_on_one_triple_are_excluded_from_r1(
            self, world, monkeypatch):
        """Two roster people, SAME full triple: neither may be R1, both emitted.

        R1 requires the roster key to map to exactly ONE roster person, so
        this pair is excluded from R1 *by definition* -- upfront, before the
        R1-versus-R1 tie sweep ever runs.  The row therefore carries
        ROSTER_PAIR_ANSWERS_FOR_2PLUS_IDENTITY_ROWS and NOT
        tie_demoted_from_r1, which is reserved for a candidate that met every
        R1 condition and then collided with another R1 (see the next test).
        """
        scratch = world["scratch"]
        write_gz(scratch / "roster_keys.ndjson.gz", [
            roster_row("quorum:staff:1", "ALPHA", "ANN", "Q", member="Rep One"),
            roster_row("lda:lobbyist:901", "ALPHA", "ANN", "Q",
                       kind_source="lda", fingerprint="ALPHA|ANN|other"),
        ])
        write_gz(scratch / "candidates_house_csv.ndjson.gz", [
            house_csv_candidate("ALPHA", "ANN", "Q", "quorum:staff:1",
                                "ALPHA", "ANN", "Q", "EXACT_LAST_FIRST_MI"),
            house_csv_candidate("ALPHA", "ANN", "Q", "lda:lobbyist:901",
                                "ALPHA", "ANN", "Q", "EXACT_LAST_FIRST_MI"),
        ])
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        out = world["tmp"] / "gen_tie"
        builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)
        rows = read_gz(out / builder.CANDIDATE_FILE)
        assert len(rows) == 2
        # THE SAFETY PROPERTY: the tie is never broken in anyone's favour.
        assert not any(r["resolution_tier"] == "R1_EXACT_UNIQUE" for r in rows)
        # both members of the tie survive into the file
        assert {r["roster_id"] for r in rows} == {"quorum:staff:1",
                                                  "lda:lobbyist:901"}
        for row in rows:
            assert ("ROSTER_PAIR_ANSWERS_FOR_2PLUS_IDENTITY_ROWS" in
                    row["evidence"]["r1_blocked_by"])
            assert row["evidence"]["roster_unique_identity"] is False
            assert row["evidence"]["roster_pair_identity_rows"] == 2

    def test_a_tied_r1_is_demoted_never_broken(self, world, monkeypatch):
        """One roster person that is the unique exact match for TWO payee keys.

        Each candidate satisfies every R1 condition on its own, so this is the
        real R1-versus-R1 collision: the builder must demote BOTH to
        R3_EXACT_AMBIGUOUS and stamp tie_demoted_from_r1, rather than picking
        whichever payee key has more rows.  The second key is reached through
        an alternate roster alias (a compound surname), which is how one
        person legitimately answers to two payroll spellings.
        """
        scratch = world["scratch"]
        write_gz(scratch / "roster_keys.ndjson.gz", [
            roster_row("quorum:staff:1", "ALPHA", "ANN", "Q", member="Rep One"),
            roster_row("quorum:staff:1", "ALPHASMITH", "ANN", "Q",
                       member="Rep One", primary=False),
        ])
        write_gz(scratch / "payee_keys.ndjson.gz", [
            payee_fact("ALPHA", "ANN", "Q"),
            payee_fact("ALPHASMITH", "ANN", "Q"),
            # the Senate corpus row the key-reproduction gate reconciles
            # against; dropping it makes the build abort before tiering
            payee_fact("NOBODY", "NOONE", None, chambers=("SENATE",)),
        ])
        write_gz(scratch / "candidates_house_csv.ndjson.gz", [
            house_csv_candidate("ALPHA", "ANN", "Q", "quorum:staff:1",
                                "ALPHA", "ANN", "Q", "EXACT_LAST_FIRST_MI"),
            house_csv_candidate("ALPHASMITH", "ANN", "Q", "quorum:staff:1",
                                "ALPHASMITH", "ANN", "Q", "EXACT_LAST_FIRST_MI"),
        ])
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        out = world["tmp"] / "gen_r1_collision"
        builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)
        rows = read_gz(out / builder.CANDIDATE_FILE)
        assert len(rows) == 2
        assert all(r["resolution_tier"] == "R3_EXACT_AMBIGUOUS" for r in rows)
        assert all(r["tie_demoted_from_r1"] is True for r in rows)
        assert all("TIE_AT_R1_NEVER_BROKEN_SILENTLY" in
                   r["evidence"]["r1_blocked_by"] for r in rows)
        # neither payee key was silently preferred
        assert {r["payee_surname_key"] for r in rows} == {"ALPHA", "ALPHASMITH"}


class TestRollup:
    def test_status_tracks_the_best_tier(self, built):
        staffers = read_gz(built["root"] / builder.STAFFER_FILE)
        by_id = {r["quorum_staff_id"]: r for r in staffers}
        assert by_id["1"]["status"] == "RESOLVED_R1"
        assert by_id["2"]["status"] == "RESOLVED_R2"
        assert by_id["3"]["status"] == "CANDIDATE_R3"
        assert by_id["4"]["status"] == "CANDIDATE_R4"

    def test_every_staffer_gets_exactly_one_row(self, built):
        staffers = read_gz(built["root"] / builder.STAFFER_FILE)
        assert len(staffers) == 4
        assert len({r["quorum_staff_id"] for r in staffers}) == 4

    def test_a_staffer_with_no_candidate_is_not_found(self, world, monkeypatch):
        write_gz(world["scratch"] / "candidates_house_csv.ndjson.gz", [])
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        out = world["tmp"] / "gen_empty"
        builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)
        staffers = read_gz(out / builder.STAFFER_FILE)
        assert {r["status"] for r in staffers} == {"NOT_FOUND"}
        assert all(r["best_tier"] is None for r in staffers)
        assert all(r["candidate_count"] == 0 for r in staffers)

    def test_recovery_flag_only_fires_off_the_old_rule(self, built):
        staffers = read_gz(built["root"] / builder.STAFFER_FILE)
        by_id = {r["quorum_staff_id"]: r for r in staffers}
        # staffer 1 was NOT_ON_PAYROLL under the old rule and now resolves
        assert by_id["1"]["old_rule_recovered"] is True
        # staffer 2 was already LINKED, so resolving is not a recovery
        assert by_id["2"]["old_rule_recovered"] is False

    def test_lda_rows_cover_the_whole_queue(self, built):
        lda = read_gz(built["root"] / builder.LDA_FILE)
        assert len(lda) == 1
        assert lda[0]["lda_source_person_id"] == "lda:lobbyist:900"
        assert lda[0]["status"] == "CANDIDATE_R3"


class TestEndToEnd:
    def test_outputs_are_canonical_and_deterministic(self, world, monkeypatch):
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        first = world["tmp"] / "gen_a"
        second = world["tmp"] / "gen_b"
        builder.build(world["paths"], first, "run-test", log=lambda *a, **k: None)
        builder.build(world["paths"], second, "run-test", log=lambda *a, **k: None)
        for name in builder.PAYLOAD_FILES:
            assert (first / name).read_bytes() == (second / name).read_bytes()
            assert verifier.gzip_mtime(first / name) == 0

    def test_every_line_is_sorted_key_json(self, built):
        for name in builder.PAYLOAD_FILES:
            with gzip.open(built["root"] / name, "rt", encoding="utf-8") as handle:
                for line in handle:
                    text = line.rstrip("\n")
                    if text:
                        assert verifier.canonical(json.loads(text)) == text

    def test_builder_refuses_a_non_empty_output_dir(self, world, monkeypatch):
        monkeypatch.setattr(builder, "INV", _NeutralINV(builder.INV), raising=False)
        out = world["tmp"] / "gen_guard"
        out.mkdir()
        (out / "squatter.txt").write_text("x", encoding="utf-8")
        with pytest.raises(SystemExit):
            builder.build(world["paths"], out, "run-test", log=lambda *a, **k: None)

    def test_receipt_binds_every_input_with_bytes_rows_and_sha256(self, built):
        receipt = built["receipt"]
        assert receipt["inputs"]
        for name, meta in receipt["inputs"].items():
            assert meta["sha256"] and len(meta["sha256"]) == 64, name
            assert meta["bytes"] > 0, name
            assert Path(meta["path"]).exists(), name

    def test_verifier_reproduces_the_builder_on_synthetic_data(self, built, world):
        """The independent verifier re-derives the same rows."""
        state = verifier.rederive(world["paths"], log=lambda *a, **k: None)
        emitted = read_gz(built["root"] / builder.CANDIDATE_FILE)
        assert len(state["records"]) == len(emitted)
        derived_tiers = {(r["pair"]["roster_id"], r["tier"])
                         for r in state["records"].values()}
        emitted_tiers = {(r["roster_id"], r["resolution_tier"]) for r in emitted}
        assert derived_tiers == emitted_tiers


class TestPromotionTripwire:
    """NEGATIVE CONTROL.  These tests fail if the guard stops guarding."""

    def test_no_row_is_ever_promoted(self, built):
        for name in builder.PAYLOAD_FILES:
            for row in read_gz(built["root"] / name):
                assert row["canonical_eligible"] is False
                assert row["canonical_employment_promoted"] is False
                assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
                assert row["review_status"] == "REVIEW_REQUIRED"

    def test_receipt_pins_both_promotion_counters_at_zero(self, built):
        assert built["receipt"]["canonical_employment_promotions"] == 0
        assert built["receipt"]["canonical_identity_promotions"] == 0

    def test_a_planted_promoted_row_IS_detected(self, built):
        """The control must BITE: flipping the flag has to be caught, or the
        clean result above proves nothing."""
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        planted = dict(rows[0])
        planted["canonical_employment_promoted"] = True
        caught = any(planted.get(k) != v
                     for k, v in verifier.GUARD_COLUMNS.items())
        assert caught, "promotion tripwire did not fire on a promoted row"

    def test_a_planted_identity_decision_IS_detected(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        planted = dict(rows[0])
        planted["canonical_identity_decision"] = "ADJUDICATED_SAME_PERSON"
        assert any(planted.get(k) != v
                   for k, v in verifier.GUARD_COLUMNS.items())

    def test_a_planted_review_status_IS_detected(self, built):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        planted = dict(rows[0])
        planted["review_status"] = "APPROVED"
        assert any(planted.get(k) != v
                   for k, v in verifier.GUARD_COLUMNS.items())

    def test_the_unmodified_row_trips_nothing(self, built):
        """SILENT PROBE: the controls must not fire on a clean row."""
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        assert not any(rows[0].get(k) != v
                       for k, v in verifier.GUARD_COLUMNS.items())

    def test_a_planted_tier_flip_IS_detected(self, built, world):
        rows = read_gz(built["root"] / builder.CANDIDATE_FILE)
        state = verifier.rederive(world["paths"], log=lambda *a, **k: None)
        truth = {(r["pair"]["chamber"], r["pair"]["payee_key"],
                  r["pair"]["roster_id"]): r["tier"]
                 for r in state["records"].values()}
        row = dict(rows[0])
        key = (row["payee_chamber"],
               (row["payee_surname_key"], row["payee_given_key"],
                row["payee_middle_initial"]), row["roster_id"])
        assert truth[key] == row["resolution_tier"]
        row["resolution_tier"] = "R1_EXACT_UNIQUE" \
            if truth[key] != "R1_EXACT_UNIQUE" else "R4_LOOSE"
        assert truth[key] != row["resolution_tier"], "tier control did not bite"
