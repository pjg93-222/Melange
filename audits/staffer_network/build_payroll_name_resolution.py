#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter and label the payroll name-resolution candidates into tiers.

WHAT THIS IS
------------
Paul's directive for this lane is "literally every time you see a name you
extract it and check it ... against the +30,000 names we have on file, then
filter."  The three preceding phases did the extract-and-check half without any
office, member, chamber or period restriction:

  Index    every roster name and every payroll payee name normalised to a
           (surname_key, given_key, middle_initial) triple, with alternate
           parses beside the primary.
  Match    three candidate lanes, each a full cross product of the payee key
           space against the WHOLE roster:
             candidates_house_csv.ndjson.gz  59,426 rows (detail_csv era)
             candidates_house_pdf.ndjson.gz  27,520 rows (single-volume PDF era)
             candidates_senate.ndjson.gz     42,765 rows

This phase is the "then filter" half.  It merges the three lanes, assigns one
resolution tier per (payee, roster person) candidate, and rolls the candidates
up to one row per Quorum current staffer and one row per LDA person.

NOTHING HERE IS A LINK AND NOTHING IS PROMOTED.  Every emitted row carries
``review_status: REVIEW_REQUIRED``, ``canonical_eligible: false``,
``canonical_employment_promoted: false`` and
``canonical_identity_decision: NOT_ADJUDICATED``.  The receipt pins
``canonical_employment_promotions`` and ``canonical_identity_promotions`` at
zero.  A tier is a NAME-EVIDENCE grade, not an employment finding and not an
identity adjudication.

THE TIER RULE, AS APPLIED
-------------------------
R1_EXACT_UNIQUE
    surname, given AND middle initial all present and equal on both sides
    (the Match lanes' EXACT_LAST_FIRST_MI class, re-derived here from the keys
    rather than trusted from the label), AND the roster key answers for exactly
    one roster identity row, AND the payee key answers for exactly one payroll
    person, AND the candidate is not part of a tie.

R2_EXACT_CORROBORATED
    surname and given equal (middle initial equal, absent on one side, or
    absent on both), NOT R1, no contradicting middle initial, no contradicting
    generational suffix, AND at least one independent corroborating signal
    fires.  The signals are enumerated in CORROBORATION_SIGNALS below.

R3_EXACT_AMBIGUOUS
    surname and given equal, but neither R1 nor R2.  Kept as a candidate,
    never a link.

R4_LOOSE
    everything else -- nickname, first-initial and surname-variant classes.
    Candidate only.

TIES ARE NEVER BROKEN SILENTLY.  One row is emitted for every (payee, roster
person) pair, so every member of every tie is in the file.  ``tie_size`` is
carried on each row, and a candidate that would otherwise be R1 but shares its
tier with another candidate on either side is DEMOTED to R3_EXACT_AMBIGUOUS with
``tie_demoted_from_r1: true``.  No tie is resolved by recency, row count, office
plausibility or any other tiebreak.

ASSUMPTIONS, EACH SETTLED BY MEASUREMENT AND DECLARED IN THE RECEIPT
-------------------------------------------------------------------
A1. THE PAYEE ATOM IS (chamber, key triple).  The two House lanes are two eras
    of ONE ledger over ONE person-key space, so a key seen in both is one House
    payee entity.  The Senate is a different corpus with a different extractor,
    so a key seen in both chambers yields TWO payee entities and two candidate
    rows, each with its own evidence, plus
    ``payee_key_seen_in_other_chamber: true``.  6,875 of 122,342 keys are in
    both chambers.  Merging them would assert that one human held both jobs;
    splitting them asserts nothing.

A2. R1 REQUIRES A LITERAL MIDDLE INITIAL ON BOTH SIDES.  The tier rule as
    written says "exact last+first+middle-initial", and that is applied
    literally.  It is a severe requirement here: the Index phase measured a
    middle initial on 21.5% of roster keys (6,678 / 31,095) against 81.4% of
    payee keys (99,561 / 122,342), because Quorum and LDA publish "First Last"
    while payroll prints "SURNAME, GIVEN M".  Every row therefore also carries
    ``would_be_r1_under_relaxed_middle_initial``, true when the row is an exact
    surname+given match, unique on both sides, tie-free, and fails R1 ONLY
    because one side does not print a middle initial.  The receipt reports that
    count so the strict-versus-relaxed reading is one predicate away and does
    not need a rebuild.

A3. ROSTER-SIDE UNIQUENESS IS COUNTED ON THE (surname, given) PAIR, NOT THE
    TRIPLE.  A roster person printed without a middle initial has an UNKNOWN
    middle initial, not an absent one, so they remain a plausible answer to a
    payee string that does carry one.  Counting uniqueness on the triple would
    call (SMITH, JOHN, A) unique while a second roster "John Smith" sits beside
    it.  Pair counting is the strict reading and it is the one applied.

A4. ROSTER-SIDE UNIQUENESS COUNTS IDENTITY ROWS, NOT DEDUPLICATED HUMANS.  The
    LDA side is a registration queue: one human is filed under several
    ``lda_source_person_id`` values with the identical spelling (JARROD
    LOADHOLT holds five).  Collapsing those would be a person-identity claim
    this lane is not authorised to make, so the strict count is used and rows
    denied R1 for this reason alone are counted separately and reported as
    ``r1_blocked_by_same_spelling_duplicate_registration``.

A5. PAYEE-SIDE UNIQUENESS.  A payee key answers for exactly one payroll person
    when it was never observed in two distinct offices inside one reporting
    period (``max_offices_within_one_period <= 1``) and it is not also present
    in the other chamber.  Shared staff legitimately sit in two offices at
    once, so ``shared_employee_rows`` is carried on every row rather than being
    used to excuse a collision.

A6. THE COMMITTEE / LEADERSHIP CORROBORATION LEG IS PAIRED WHERE THE DATA
    ALLOWS.  "A committee or leadership office in a period their member served"
    is only meaningful if the office and the period are the SAME observation.
    House pairing is read from the ledger's own ``person_key`` +
    ``container_kind`` + ``quarter``, which covers 24,242 of the 25,260 matched
    House keys; the residue are alternate-parse keys the ledger's own parser
    never produced.  Senate pairing is rebuilt from ``payee_name_raw`` with the
    Index phase's LASTFIRST rules, a reproduction validated against the
    published key set (47,963 keys, symmetric difference 0).  Where an exact
    pairing is unavailable but EVERY container the payee was ever seen in is a
    non-member office, the pairing is implied and the signal still fires;
    otherwise the signal is recorded UNAVAILABLE and never fires.  Availability
    is on every row.

A7. LDA FILING YEARS ARE RECORDED BUT DO NOT QUALIFY FOR R2.  The tier rule
    offers "covered-position text or filing years".  The covered-position
    signals (a year the person themselves stated, or a distinctive office token
    they themselves wrote) are specific to the person.  A filing-year ordering
    -- registration begins at or after payroll service ends -- is satisfied by
    a large fraction of candidates by construction, because LDA registration
    years cluster in 2021-2026 while the payroll spans 2009-2026.  It is
    computed, carried as ``L3_FILING_YEARS_POSTDATE_SERVICE`` in
    ``corroboration_signals_recorded_non_qualifying``, and its counterfactual
    effect on R2 is reported.  ``LDA_FILING_YEAR_SIGNAL_QUALIFIES`` is the dial.

A8. SENATE OFFICE -> MEMBER RESOLUTION.  The Senate corpus carries no bioguide
    and no container kind.  Personal offices are the strings "SENATOR <NAME>"
    and "INTERN COMPENSATION - <NAME>"; everything else is treated as
    non-personal.  A personal office resolves to a Quorum member when its
    trailing surname run matches exactly one current member, or matches several
    and exactly one of those agrees on the given name (directly, through the
    single-formal nickname table, or on the first initial).  A senator who no
    longer serves cannot resolve, because the Quorum roster is current members
    only; that is a coverage limit, not an error, and the resolution rate is
    reported.

A9. THE OLD RULE'S BASELINE.  1,985 LINKED / 3,650 NOT_ON_PAYROLL /
    138 MEMBER_UNRESOLVED of 5,773, and 6,101 LDA people in the match lanes,
    are read from ``hill_personnel_spine_20260902_v1_primary`` at run time and
    asserted against the INV constants below, so the recovery report is bound
    to the artefact it claims to improve on rather than to a remembered number.

INPUT PROVENANCE.  The three candidate files and the roster key index are
products of this lane's earlier phases and live in a scratch directory.  They
are COPIED into ``<generation>/inputs/`` so the generation is reproducible after
the scratch directory is gone, and they are hash-bound in the receipt either
way.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fec.staffer_network.schema_validation import (  # noqa: E402
    validate_instance,
    validate_schema_definition,
)

# ---------------------------------------------------------------------------
# Identity of this build
# ---------------------------------------------------------------------------
RULE_VERSION = "payroll-name-resolution-v1"
DEFAULT_RUN_ID = "run-20260902T143000000000Z-nameresolve"
PHASE = "filter-label"

CANDIDATE_SCHEMA_ID = "staffer-network-payroll-name-resolution-v1"
STAFFER_SCHEMA_ID = "staffer-network-current-staffer-resolution-v1"
LDA_SCHEMA_ID = "staffer-network-lda-resolution-v1"
RECEIPT_SCHEMA_ID = "staffer-network-payroll-name-resolution-receipt-v1"

CANDIDATE_FILE = "payroll_name_resolutions.ndjson.gz"
STAFFER_FILE = "current_staffer_resolution.ndjson.gz"
LDA_FILE = "lda_resolution.ndjson.gz"
RECEIPT_FILE = "payroll_name_resolution_receipt.json"
PAYLOAD_FILES = (CANDIDATE_FILE, STAFFER_FILE, LDA_FILE)

SCHEMA_DIR_NAME = "payroll_name_resolution_schemas"
SCHEMA_FILES = {
    CANDIDATE_FILE: "payroll_name_resolutions.schema.json",
    STAFFER_FILE: "current_staffer_resolution.schema.json",
    LDA_FILE: "lda_resolution.schema.json",
    RECEIPT_FILE: "payroll_name_resolution_receipt.schema.json",
}

# ---------------------------------------------------------------------------
# INV constants.  Every one of these is asserted against the artefacts at run
# time; a mismatch aborts the build rather than being reported as a delta.
# ---------------------------------------------------------------------------
INV = {
    "INV_CURRENT_STAFFERS": 5773,
    "INV_QUORUM_MEMBERS": 533,
    "INV_LDA_QUEUE_ROWS": 25340,
    "INV_ROSTER_ALIAS_ROWS": 38231,
    "INV_ROSTER_IDENTITY_ROWS": 31108,
    "INV_ROSTER_MATCH_ELIGIBLE_IDENTITY_ROWS": 31095,
    "INV_HOUSE_LEDGER_ROWS": 975058,
    "INV_SENATE_CORPUS_ROWS": 233009,
    "INV_PAYEE_KEY_UNIVERSE": 122342,
    "INV_PAYEE_KEYS_BOTH_CHAMBERS": 6875,
    "INV_CANDIDATES_HOUSE_CSV": 59426,
    "INV_CANDIDATES_HOUSE_PDF": 27520,
    "INV_CANDIDATES_SENATE": 42765,
    "INV_OLD_RULE_LINKED": 1985,
    "INV_OLD_RULE_NOT_ON_PAYROLL": 3650,
    "INV_OLD_RULE_MEMBER_UNRESOLVED": 138,
    "INV_OLD_RULE_LDA_IN_MATCH_LANES": 6101,
    "INV_CANONICAL_EMPLOYMENT_PROMOTIONS": 0,
    "INV_CANONICAL_IDENTITY_PROMOTIONS": 0,
}

# ---------------------------------------------------------------------------
# Dials.  UNTESTED DEFAULTS pending Paul's freeze; each is declared in the
# receipt and each is re-derived by the independent verifier.
# ---------------------------------------------------------------------------
LDA_FILING_YEAR_SIGNAL_QUALIFIES = False          # A7
NON_MEMBER_CONTAINER_KINDS = (
    "admin", "committee", "leadership", "member_organization",
)
MEMBER_CONTAINER_KINDS = ("member_office", "member_office_unresolved")
# The Senate corpus carries no container_kind at all, so an office kind is
# derived there from the office string instead.  The two vocabularies are
# unified on the emitted row so that a recovery figure spanning both chambers
# can be quoted against one denominator.
SENATE_PERSONAL_OFFICE_KIND = "senate_personal_office"
SENATE_NON_PERSONAL_OFFICE_KIND = "senate_non_personal_office"
MEMBER_OFFICE_KINDS = MEMBER_CONTAINER_KINDS + (SENATE_PERSONAL_OFFICE_KIND,)
COMMITTEE_OR_LEADERSHIP_KINDS = ("committee", "leadership",
                                 SENATE_NON_PERSONAL_OFFICE_KIND)
LIST_CAP = 20                                      # list fields truncate here
SENATE_PERSONAL_OFFICE_PREFIXES = ("SENATOR ", "INTERN COMPENSATION - ")

TIER_ORDER = ("R1_EXACT_UNIQUE", "R2_EXACT_CORROBORATED",
              "R3_EXACT_AMBIGUOUS", "R4_LOOSE")
TIER_RANK = {name: index + 1 for index, name in enumerate(TIER_ORDER)}
STATUS_FOR_TIER = {
    "R1_EXACT_UNIQUE": "RESOLVED_R1",
    "R2_EXACT_CORROBORATED": "RESOLVED_R2",
    "R3_EXACT_AMBIGUOUS": "CANDIDATE_R3",
    "R4_LOOSE": "CANDIDATE_R4",
}
STATUS_VALUES = ("RESOLVED_R1", "RESOLVED_R2", "CANDIDATE_R3",
                 "CANDIDATE_R4", "NOT_FOUND")

CORROBORATION_SIGNALS = {
    "Q1_OWN_MEMBER_HOUSE_OFFICE":
        "the payee was paid out of office HON:<bioguide> of the staffer's own "
        "member",
    "Q2_OWN_MEMBER_SENATE_OFFICE":
        "the payee was paid out of a Senate personal office that resolves to "
        "the staffer's own member",
    "Q3_NON_MEMBER_HOUSE_OFFICE_IN_MEMBER_SERVICE_QUARTER":
        "the payee was paid out of a House committee / leadership / admin / "
        "member-organization office in a quarter their own member's office was "
        "on the House payroll",
    "Q4_NON_MEMBER_SENATE_OFFICE_IN_MEMBER_SERVICE_PERIOD":
        "the payee was paid out of a non-personal Senate office in a report "
        "period their own member's personal office was on the Senate payroll",
    "L1_COVERED_POSITION_YEAR_OVERLAP":
        "a payroll year of the payee falls inside the year span the LDA person "
        "themselves wrote into their covered-position text",
    "L2_COVERED_POSITION_OFFICE_TEXT_OVERLAP":
        "a distinctive office word of the payee appears in the LDA person's own "
        "covered-position text",
}
NON_QUALIFYING_SIGNALS = {
    "L3_FILING_YEARS_POSTDATE_SERVICE":
        "the LDA person's first filing year is at or after the payee's last "
        "payroll year.  Recorded, never qualifying: see A7.",
}

# Office words that carry no discriminating power when matched against a
# covered-position sentence, so they are excluded from the L2 overlap test.
OFFICE_STOPWORDS = frozenset({
    "AND", "COMMITTEE", "COMMISSION", "CONGRESS", "CONGRESSIONAL", "FOR",
    "HON", "HOUSE", "MEMBER", "OF", "OFFICE", "ON", "REPRESENTATIVES",
    "SENATE", "SENATOR", "STAFF", "SUBCOMMITTEE", "THE", "TO", "UNITED",
    "US", "USA", "STATES", "JOINT", "SELECT", "SPECIAL", "PERMANENT",
    "MAJORITY", "MINORITY", "LEADER", "WHIP", "CONFERENCE", "POLICY",
    "SERVICES", "SERVICE", "DIVISION", "OPERATIONS", "SUPPORT", "GENERAL",
    "ADMINISTRATIVE", "EXECUTIVE", "CENTRAL", "CAPITOL", "COMPENSATION",
    "INTERN", "RESERVE", "RESOLUTION", "REORGANIZATION", "SGT", "ARMS",
    "SERGEANT", "DOORKEEPER", "SECRETARY", "COUNSEL", "LEGISLATIVE",
})

# ---------------------------------------------------------------------------
# Name normalisation.  Vendored from the Index phase's normalize.py so this
# builder has no dependency on a scratch directory.  Only the pieces the Senate
# office/period pairing needs are carried; the candidate lanes already supply
# every key this phase matches on.
# ---------------------------------------------------------------------------
_HONORIFIC = {"MR", "MRS", "MS", "MISS", "DR", "HON", "REV", "PROF", "SIR",
              "ATTY", "MX"}
_CREDENTIAL_ANY = {"JD", "MD", "PHD", "ESQ", "ESQUIRE", "CPA", "MBA", "MPA",
                   "MPH", "MSW", "RN", "DDS", "DVM", "LLM", "CFA", "EDD",
                   "DPHIL", "MSC"}
_CREDENTIAL_TRAILING_ONLY = {"MS", "D"}
_SUFFIX = {"JR", "SR", "II", "III", "IV"}
_PLACEHOLDER = {"NA", "N", "A", "NONE", "NULL", "UNKNOWN", "TEST", "VACANT",
                "TBD", "X", "XX", "XXX", "NOTAPPLICABLE", "FARA",
                "EXEMPTION", "NOTAPPLICABL", "DO", "SAME", "DITTO"}
_DATE_RE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
_YEAR_RE = re.compile(r"^(19|20)\d{2}$")
_PAREN_RE = re.compile(r"\([^)]*\)|\[[^\]]*\]")
_TRANS = {0x2019: "'", 0x02BC: "'", 0x2013: "-", 0x2014: "-", 0x2011: "-",
          0x00A0: " ", 0x2018: "'"}


def prep(raw: Any) -> str:
    if not raw:
        return ""
    text = str(raw).translate(_TRANS)
    text = text.split("|", 1)[0]
    text = _PAREN_RE.sub(" ", text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.upper()


def tokenize(text: str) -> tuple[list[str], list[str]]:
    tokens = [t for t in re.split(r"\s+", text) if t]
    while tokens and re.sub(r"[^A-Z0-9]", "", tokens[0]) in _HONORIFIC:
        tokens.pop(0)
    kept: list[str] = []
    suffixes: list[str] = []
    for token in tokens:
        bare = re.sub(r"[^A-Z0-9]", "", token)
        if not bare:
            continue
        if _DATE_RE.match(token) or _YEAR_RE.match(bare):
            continue
        dotted_initials = "." in token.rstrip(".")
        if not dotted_initials:
            if bare in _SUFFIX:
                suffixes.append(bare)
                continue
            if bare in _CREDENTIAL_ANY:
                continue
        kept.append(bare)
    while len(kept) > 2 and kept[-1] in _CREDENTIAL_TRAILING_ONLY:
        kept.pop()
    return kept, suffixes


def collapse(parts: Iterable[str]) -> str:
    return re.sub(r"[^A-Z0-9]", "", "".join(parts))


def make_key(surname_tokens: Sequence[str], given_tokens: Sequence[str],
             middle_tokens: Sequence[str]) -> tuple[str, str, str | None] | None:
    surname = collapse(surname_tokens)
    given = collapse(given_tokens)
    if len(surname) < 2 or len(given) < 1:
        return None
    middle_initial = None
    for token in middle_tokens:
        folded = collapse([token])
        if folded:
            middle_initial = folded[0]
            break
    return (surname, given, middle_initial)


def is_placeholder_name(raw: Any) -> bool:
    tokens, _suffixes = tokenize(prep(raw))
    if not tokens:
        return True
    return all(token in _PLACEHOLDER for token in tokens)


def parse_last_first(raw: Any) -> list[tuple[str, str, str | None]]:
    """Every key a "SURNAME, GIVEN [MIDDLE]" payee string produces, primary
    first.  Reproduces the Index phase exactly; the reproduction is asserted
    against the published Senate key set before it is used."""

    text = prep(raw)
    if "," not in text:
        return []
    head, tail = text.split(",", 1)
    surname_tokens, _s1 = tokenize(head)
    given_tokens, _s2 = tokenize(tail)
    if not surname_tokens or not given_tokens:
        return []
    keys: list[tuple[str, str, str | None]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for candidate_tokens in ([surname_tokens] +
                             ([surname_tokens[-1:]] if len(surname_tokens) > 1 else [])):
        key = make_key(candidate_tokens, given_tokens[:1], given_tokens[1:])
        if key is not None and key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_ndjson_gz(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def canonical_line(row: Mapping[str, Any]) -> str:
    return json.dumps(row, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


REPLACE_ATTEMPTS = 8
REPLACE_BACKOFF_SECONDS = 0.75


def atomic_replace(temporary: Path, path: Path) -> None:
    """os.replace, retried around a transient Windows sharing violation.

    This generation is written inside a OneDrive-synced tree.  The sync
    engine opens a file it has just seen appear, and on Windows an open
    handle makes os.replace fail with WinError 32 ("used by another
    process") - which is exactly how the previous run of this builder died
    mid-emit, leaving a stale primary next to a good twin.  The rename is
    still atomic; only the moment it lands is retried.  A lock that never
    clears re-raises, so a genuine permission fault is never swallowed.
    """

    last: OSError | None = None
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(temporary, path)
            return
        except PermissionError as exc:  # WinError 32 / 5 from the sync engine
            last = exc
            time.sleep(REPLACE_BACKOFF_SECONDS * (attempt + 1))
    raise RuntimeError(
        f"could not atomically replace {path} after {REPLACE_ATTEMPTS} "
        f"attempts; the file is held by another process (last error: {last})"
    ) from last


def write_ndjson_gz(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    """Canonical NDJSON: sorted keys, gzip header mtime pinned to 0, atomic
    replace so a partial file can never be mistaken for a generation."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    count = 0
    with open(temporary, "wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as gz:
            for row in rows:
                gz.write((canonical_line(row) + "\n").encode("utf-8"))
                count += 1
    atomic_replace(temporary, path)
    return count


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    temporary.write_text(text + "\n", encoding="utf-8")
    atomic_replace(temporary, path)


def copy_file(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".partial")
    with source.open("rb") as reader, open(temporary, "wb") as writer:
        for block in iter(lambda: reader.read(1 << 20), b""):
            writer.write(block)
    atomic_replace(temporary, target)


def validated(rows: Iterable[Mapping[str, Any]],
              schema: Mapping[str, Any]) -> Iterator[Mapping[str, Any]]:
    """Every emitted row is validated against the committed schema for its file
    BEFORE it reaches the artefact, so a schema violation aborts the build
    instead of shipping."""

    for row in rows:
        validate_instance(row, schema)
        yield row


def capped(values: Iterable[str]) -> tuple[list[str], bool]:
    ordered = sorted({v for v in values if v})
    if len(ordered) <= LIST_CAP:
        return ordered, False
    return ordered[:LIST_CAP], True


# ---------------------------------------------------------------------------
# Default input locations
# ---------------------------------------------------------------------------
def default_paths(repo: Path, scratch: Path) -> dict[str, Path]:
    audits = repo / "audits" / "staffer_network"
    return {
        "candidates_house_csv": scratch / "candidates_house_csv.ndjson.gz",
        "candidates_house_pdf": scratch / "candidates_house_pdf.ndjson.gz",
        "candidates_senate": scratch / "candidates_senate.ndjson.gz",
        "roster_keys": scratch / "roster_keys.ndjson.gz",
        "payee_keys": scratch / "payee_keys.ndjson.gz",
        "staff_directory": repo / "data" / "members" / "staff_directory.json",
        "nicknames": (repo / "data" / "staffer_network" / "reference" /
                      "first_name_nicknames_v1.json"),
        "lda_queue": Path(
            r"C:\Users\pgoff\AppData\Local\Melange\staffer_network"
            r"\employment-lookup\generation-20260831T050000Z"
            r"\employment_lookup_queue.ndjson.gz"),
        "house_ledger": (audits / "house_personnel_ledger_20260902_v2_primary" /
                         "house_personnel_observations.ndjson.gz"),
        "senate_corpus": (
            audits /
            "official_senate_payroll_2011_2026_employment_scope_v1" /
            "senate_payroll_employment_candidates_2011_2026.ndjson.gz"),
        "old_staffer_links": (audits / "hill_personnel_spine_20260902_v1_primary" /
                              "current_staffer_links.ndjson.gz"),
        "old_lda_links": (audits / "hill_personnel_spine_20260902_v1_primary" /
                          "lda_spine_links.ndjson.gz"),
    }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_nicknames(path: Path) -> dict[str, str]:
    """Short form -> the single formal form.  Short forms with two or more
    formal forms are DROPPED, never collapsed: collapsing would let two
    distinct people answer to one string."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries") or {}
    table: dict[str, str] = {}
    for short, formals in entries.items():
        forms = [f for f in (formals or []) if f]
        if len(forms) == 1:
            table[collapse([prep(short)])] = collapse([prep(forms[0])])
    return table


def load_roster(path: Path) -> tuple[dict[str, dict[str, Any]],
                                     dict[tuple[str, str], set[str]],
                                     dict[str, int]]:
    """Returns (identity rows by roster_id, roster ids by (surname, given)
    pair, counters)."""

    people: dict[str, dict[str, Any]] = {}
    by_pair: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    counters = collections.Counter()
    for row in read_ndjson_gz(path):
        counters["alias_rows"] += 1
        roster_id = row["roster_id"]
        record = people.get(roster_id)
        if record is None:
            record = {
                "roster_id": roster_id,
                "roster_kind": ("quorum_staffer"
                                if roster_id.startswith("quorum:")
                                else "lda_lobbyist"),
                "roster_source": row.get("roster_source"),
                "display_name": row.get("display_name"),
                "quorum_member_display": row.get("quorum_member_display"),
                "quorum_title": row.get("quorum_title"),
                "quorum_star": row.get("quorum_star"),
                "spelling_fingerprint": row.get("spelling_fingerprint"),
                "generational_suffix": flat_strings(row.get("generational_suffix")),
                "is_placeholder_name": bool(row.get("is_placeholder_name")),
                "match_eligible": bool(row.get("match_eligible")),
                "keys": [],
            }
            people[roster_id] = record
            counters["identity_rows"] += 1
            if record["match_eligible"]:
                counters["match_eligible_identity_rows"] += 1
        record["keys"].append({
            "surname_key": row.get("surname_key"),
            "given_key": row.get("given_key"),
            "middle_initial": row.get("middle_initial"),
            "key_basis": row.get("key_basis"),
            "is_primary_key": bool(row.get("is_primary_key")),
        })
        if row.get("match_eligible") and row.get("surname_key") and row.get("given_key"):
            by_pair[(row["surname_key"], row["given_key"])].add(roster_id)
    return people, dict(by_pair), dict(counters)


def load_staff_directory(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    staff: dict[str, dict[str, Any]] = {}
    for member_display, entries in payload.items():
        for entry in entries or []:
            staff[str(entry["id"])] = {
                "quorum_staff_id": str(entry["id"]),
                "display_name": entry.get("n"),
                "member_display": member_display,
                "title_raw": entry.get("t"),
                "star": entry.get("star"),
            }
    return staff


def load_lda_queue(path: Path) -> dict[str, dict[str, Any]]:
    people: dict[str, dict[str, Any]] = {}
    for row in read_ndjson_gz(path):
        person_id = row["lda_source_person_id"]
        years = sorted({int(y) for y in (row.get("covered_position_year_tokens") or [])
                        if str(y).isdigit()})
        text = " ".join(str(v) for v in (row.get("covered_position_values") or []))
        people[person_id] = {
            "lda_source_person_id": person_id,
            "display_name": row.get("display_name"),
            "filing_years": sorted({int(y) for y in (row.get("filing_years") or [])}),
            "covered_position_years": years,
            "covered_position_tokens": frozenset(
                token for token in re.split(r"[^A-Z0-9]+", prep(text))
                if len(token) >= 4 and token not in OFFICE_STOPWORDS),
            "covered_position_present": bool(text.strip()),
            "priority": row.get("priority"),
            "identity_status": row.get("identity_status"),
        }
    return people


def load_old_staffer_links(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in read_ndjson_gz(path):
        out[str(row["quorum_staff_id"])] = {
            "link_status": row.get("link_status"),
            "member_bioguide": row.get("member_bioguide"),
            "member_display": row.get("member_display"),
        }
    return out


def load_old_lda_links(path: Path) -> tuple[set[str], set[str]]:
    in_lanes: set[str] = set()
    linked: set[str] = set()
    for row in read_ndjson_gz(path):
        person_id = row.get("lda_source_person_id")
        if not person_id:
            continue
        in_lanes.add(person_id)
        status = str(row.get("link_status") or "")
        if status.startswith("LINKED"):
            linked.add(person_id)
    return in_lanes, linked


def load_payee_keys(path: Path) -> dict[tuple[str, str, str | None], dict[str, Any]]:
    """The Index phase's own per-key measures.  These are used in preference to
    any per-lane figure because the House PDF candidate lane does not carry
    ``max_offices_within_one_period`` at all: taking the lane's silence for a
    zero would hand spurious payee-side uniqueness to every key that appears
    only in the 2009-2015 era."""

    out: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for row in read_ndjson_gz(path):
        key = (row["surname_key"], row["given_key"], row.get("middle_initial") or None)
        out[key] = {
            "chambers": frozenset(row.get("chambers") or ()),
            "max_offices_within_one_period":
                int(row.get("max_offices_within_one_period") or 0),
            "office_period_collision": bool(row.get("office_period_collision")),
            "shared_employee_rows": int(row.get("shared_employee_rows") or 0),
            "observation_rows": int(row.get("observation_rows") or 0),
        }
    return out


# ---------------------------------------------------------------------------
# Corpus passes
# ---------------------------------------------------------------------------
def house_pass(path: Path) -> dict[str, Any]:
    """One stream of the House ledger.  Produces, per payee person_key, the
    quarters in which that key was paid out of a NON-member office, and per
    member bioguide the quarters that member's own office was on the payroll."""

    quarter_index: dict[str, int] = {}
    non_member_quarters: dict[tuple[str, str, str | None], int] = {}
    seen_keys: set[tuple[str, str, str | None]] = set()
    member_service: dict[str, set[str]] = collections.defaultdict(set)
    counters = collections.Counter()

    for row in read_ndjson_gz(path):
        counters["rows"] += 1
        quarter = row.get("quarter") or ""
        if quarter not in quarter_index:
            quarter_index[quarter] = len(quarter_index)
        bit = 1 << quarter_index[quarter]
        container = row.get("container_kind") or ""
        bioguide = row.get("member_bioguide")
        if container == "member_office" and bioguide:
            member_service[bioguide].add(quarter)
        person_key = row.get("person_key") or ""
        if not person_key.startswith("SOD:"):
            counters["rows_without_person_key"] += 1
            continue
        parts = person_key[4:].split("|")
        if len(parts) != 3:
            counters["rows_with_malformed_person_key"] += 1
            continue
        key = (parts[0], parts[1], parts[2] or None)
        seen_keys.add(key)
        if container in NON_MEMBER_CONTAINER_KINDS:
            non_member_quarters[key] = non_member_quarters.get(key, 0) | bit
    counters["distinct_person_keys"] = len(seen_keys)
    return {
        "quarter_index": quarter_index,
        "non_member_quarters": non_member_quarters,
        "keys_with_ledger_parse": seen_keys,
        "member_service": {k: sorted(v) for k, v in member_service.items()},
        "counters": dict(counters),
    }


def senate_office_is_personal(office_raw: str) -> str | None:
    text = prep(office_raw).strip()
    for prefix in SENATE_PERSONAL_OFFICE_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


def build_member_index(staff: Mapping[str, Mapping[str, Any]],
                       nicknames: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    """(surname_key, given forms) for each current Quorum member display."""

    index: dict[str, dict[str, Any]] = {}
    for record in staff.values():
        display = record["member_display"]
        if display in index:
            continue
        tokens, _suffixes = tokenize(prep(display))
        if len(tokens) < 2:
            index[display] = {"surname_key": None, "given_forms": frozenset()}
            continue
        given = collapse([tokens[0]])
        surname = collapse(tokens[1:])
        forms = {given}
        expanded = nicknames.get(given)
        if expanded:
            forms.add(expanded)
        index[display] = {
            "surname_key": surname,
            "surname_token_count": len(tokens) - 1,
            "given_forms": frozenset(forms),
        }
    return index


def resolve_senate_office(office_raw: str,
                          member_index: Mapping[str, Mapping[str, Any]]
                          ) -> tuple[str | None, str]:
    """Map a Senate personal office string to a current Quorum member display."""

    remainder = senate_office_is_personal(office_raw)
    if remainder is None:
        return None, "NOT_A_PERSONAL_OFFICE"
    tokens, _suffixes = tokenize(remainder)
    if not tokens:
        return None, "EMPTY_AFTER_PREFIX"
    by_surname: dict[str, list[str]] = collections.defaultdict(list)
    for display, info in member_index.items():
        if info.get("surname_key"):
            by_surname[info["surname_key"]].append(display)
    pool: list[tuple[str, int]] = []
    for take in (1, 2, 3):
        if take > len(tokens):
            break
        surname = collapse(tokens[-take:])
        for display in by_surname.get(surname, ()):
            pool.append((display, take))
    if not pool:
        return None, "SURNAME_NOT_IN_CURRENT_ROSTER"
    distinct = {display for display, _take in pool}
    if len(distinct) == 1:
        return next(iter(distinct)), "UNIQUE_SURNAME"
    hits: set[str] = set()
    for display, take in pool:
        head = tokens[:len(tokens) - take]
        forms = member_index[display]["given_forms"]
        for token in head:
            folded = collapse([token])
            if not folded:
                continue
            if folded in forms:
                hits.add(display)
            elif len(folded) == 1 and any(f.startswith(folded) for f in forms):
                hits.add(display)
    if len(hits) == 1:
        return next(iter(hits)), "SURNAME_AND_GIVEN_FORM"
    return None, "AMBIGUOUS_SURNAME_NO_GIVEN_AGREEMENT"


def senate_pass(path: Path, member_index: Mapping[str, Mapping[str, Any]],
                published_senate_keys: set[tuple[str, str, str | None]]
                ) -> dict[str, Any]:
    """One stream of the Senate corpus.  Produces, per payee key, the report
    periods in which the key was paid out of a NON-personal office, and per
    current member the periods their own personal office was on the payroll."""

    office_resolution: dict[str, tuple[str | None, str]] = {}
    non_personal_periods: dict[tuple[str, str, str | None], set[str]] = (
        collections.defaultdict(set))
    member_service: dict[str, set[str]] = collections.defaultdict(set)
    reproduced_keys: set[tuple[str, str, str | None]] = set()
    counters = collections.Counter()

    for row in read_ndjson_gz(path):
        counters["rows"] += 1
        office = row.get("office_raw") or ""
        if office not in office_resolution:
            office_resolution[office] = resolve_senate_office(office, member_index)
        member_display, _method = office_resolution[office]
        period = f"{row.get('report_period_start')}..{row.get('report_period_end')}"
        if member_display is not None:
            member_service[member_display].add(period)
        raw = row.get("payee_name_raw") or ""
        if is_placeholder_name(raw):
            counters["placeholder_rows"] += 1
            continue
        keys = parse_last_first(raw)
        if not keys:
            counters["rows_without_key"] += 1
            continue
        personal = senate_office_is_personal(office) is not None
        for key in keys:
            reproduced_keys.add(key)
            if not personal:
                non_personal_periods[key].add(period)
    return {
        "office_resolution": office_resolution,
        "non_personal_periods": {k: frozenset(v)
                                 for k, v in non_personal_periods.items()},
        "keys_reproduced": reproduced_keys,
        "member_service": {k: sorted(v) for k, v in member_service.items()},
        "key_reproduction": {
            "reproduced": len(reproduced_keys),
            "published": len(published_senate_keys),
            "missing_from_reproduction": len(published_senate_keys - reproduced_keys),
            "extra_in_reproduction": len(reproduced_keys - published_senate_keys),
            "exact": reproduced_keys == published_senate_keys,
        },
        "counters": dict(counters),
    }


# ---------------------------------------------------------------------------
# Candidate lane adapters
# ---------------------------------------------------------------------------
def _triple(surname: Any, given: Any, middle: Any) -> tuple[str, str, str | None]:
    return (str(surname), str(given), (str(middle) if middle else None))


def flat_strings(value: Any) -> list[str]:
    """The three candidate lanes do not agree on the shape of the generational
    suffix field: the House lanes emit ["III"], the Senate lane emits
    [["II"], ["III"]] (one list per payee spelling).  Both are flattened here
    rather than one of them being trusted."""

    out: list[str] = []
    if value is None:
        return out
    if isinstance(value, str):
        return [value]
    for item in value:
        out.extend(flat_strings(item))
    return out


def adapt_house_csv(row: Mapping[str, Any]) -> dict[str, Any]:
    payee = row["payee"]
    roster = row["roster"]
    key = row["payee_key"]
    return {
        "lane": "house_csv",
        "chamber": "HOUSE",
        "payee_key": _triple(key[0], key[1], key[2]),
        "roster_id": row["roster_id"],
        "roster_key": _triple(roster["surname_key"], roster["given_key"],
                              roster.get("middle_initial")),
        "roster_key_basis": roster.get("key_basis"),
        "roster_is_primary_key": bool(roster.get("is_primary_key")),
        "source_match_class": row["match_class"],
        "nickname_direction": row["match_evidence"].get("nickname_direction"),
        "nickname_formal_form": row["match_evidence"].get("nickname_formal_form"),
        "variant_basis": row["match_evidence"].get("variant_basis"),
        "variant_bridge": row["match_evidence"].get("variant_surname_bridge"),
        "payee": {
            "offices": list(payee.get("offices") or []),
            "periods": list(payee.get("quarters") or []),
            "titles": list(payee.get("titles") or []),
            "container_kinds": list(payee.get("container_kinds") or []),
            "member_bioguides": list(payee.get("member_bioguides") or []),
            "observation_rows": int(payee.get("observation_rows") or 0),
            "max_offices_within_one_period":
                int(payee.get("max_offices_within_one_period") or 0),
            "shared_employee_rows": int(payee.get("shared_employee_rows") or 0),
            "raw_example": payee.get("payee_raw_example"),
            "key_basis": list(payee.get("key_basis") or []),
            "has_primary_parse": bool(payee.get("has_primary_ledger_parse")),
            "generational_suffixes": flat_strings(payee.get("generational_suffixes_seen")),
        },
    }


def adapt_house_pdf(row: Mapping[str, Any]) -> dict[str, Any]:
    payee_key = row["payee_key"].split("|")
    roster_key = row["roster_key"].split("|")
    return {
        "lane": "house_pdf",
        "chamber": "HOUSE",
        "payee_key": _triple(payee_key[0], payee_key[1], payee_key[2]),
        "roster_id": row["roster_id"],
        "roster_key": _triple(roster_key[0], roster_key[1], roster_key[2]),
        "roster_key_basis": row.get("roster_key_basis"),
        "roster_is_primary_key": bool(row.get("roster_is_primary_key")),
        "source_match_class": row["match_class"],
        "nickname_direction": None,
        "nickname_formal_form": None,
        "variant_basis": (sorted(row.get("variant_reasons") or [])[0]
                          if row.get("variant_reasons") else None),
        "variant_bridge": None,
        "payee": {
            "offices": list(row.get("payee_office_keys") or []),
            "periods": list(row.get("payee_quarters") or []),
            "titles": list(row.get("payee_title_bases") or []),
            "container_kinds": list(row.get("payee_container_kinds") or []),
            "member_bioguides": list(row.get("payee_member_bioguides") or []),
            "observation_rows": int(row.get("payee_observation_rows") or 0),
            "max_offices_within_one_period": 0,
            "shared_employee_rows": int(row.get("payee_shared_employee_rows") or 0),
            "raw_example": row.get("payee_raw_example"),
            "key_basis": list(row.get("payee_key_basis") or []),
            "has_primary_parse": int(row.get("payee_primary_parse_rows") or 0) > 0,
            "generational_suffixes": flat_strings(row.get("payee_generational_suffixes")),
        },
    }


def adapt_senate(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "lane": "senate",
        "chamber": "SENATE",
        "payee_key": _triple(row["payee_surname_key"], row["payee_given_key"],
                             row.get("payee_middle_initial")),
        "roster_id": row["roster_id"],
        "roster_key": _triple(row["roster_surname_key"], row["roster_given_key"],
                              row.get("roster_middle_initial")),
        "roster_key_basis": row.get("roster_key_basis"),
        "roster_is_primary_key": bool(row.get("roster_key_is_primary")),
        "source_match_class": row["match_class"],
        "nickname_direction": row.get("match_subclass"),
        "nickname_formal_form": None,
        "variant_basis": (row.get("match_subclass")
                          if row["match_class"] == "VARIANT_HYPHEN_APOSTROPHE_SUFFIX"
                          else None),
        "variant_bridge": None,
        "payee": {
            "offices": list(row.get("offices") or []),
            "periods": list(row.get("periods") or []),
            "titles": list(row.get("titles") or []),
            "container_kinds": [],
            "member_bioguides": [],
            "observation_rows": int(row.get("payee_observation_rows") or 0),
            "max_offices_within_one_period":
                int(row.get("max_offices_within_one_period") or 0),
            "shared_employee_rows": 0,
            "raw_example": (sorted(row.get("payee_raw_examples") or [""])[0]
                            if row.get("payee_raw_examples") else None),
            "key_basis": list(row.get("payee_key_basis") or []),
            "has_primary_parse": int(row.get("payee_primary_parse_rows") or 0) > 0,
            "generational_suffixes":
                flat_strings(row.get("payee_generational_suffixes_seen")),
        },
    }


ADAPTERS = {
    "candidates_house_csv": adapt_house_csv,
    "candidates_house_pdf": adapt_house_pdf,
    "candidates_senate": adapt_senate,
}


# ---------------------------------------------------------------------------
# Tier engine
# ---------------------------------------------------------------------------
def derive_class(payee_key: tuple[str, str, str | None],
                 roster_key: tuple[str, str, str | None]) -> str:
    """Re-derived from the two key triples alone.  The lane's own match_class
    label is carried for provenance and cross-checked, never trusted."""

    if payee_key[0] == roster_key[0] and payee_key[1] == roster_key[1]:
        if payee_key[2] and roster_key[2] and payee_key[2] == roster_key[2]:
            return "EXACT_TRIPLE"
        return "EXACT_PAIR"
    return "LOOSE"


def middle_initial_state(payee_mi: str | None, roster_mi: str | None) -> str:
    if payee_mi and roster_mi:
        return "BOTH_PRESENT_EQUAL" if payee_mi == roster_mi else "BOTH_PRESENT_DIFFERENT"
    if payee_mi:
        return "ROSTER_MISSING"
    if roster_mi:
        return "PAYEE_MISSING"
    return "NEITHER"


def suffix_state(payee: Sequence[str], roster: Sequence[str]) -> str:
    left = {s.upper() for s in payee if s}
    right = {s.upper() for s in roster if s}
    if not left and not right:
        return "NEITHER"
    if not left or not right:
        return "ONE_SIDE_ONLY"
    return "BOTH_PRESENT_EQUAL" if left == right else "BOTH_PRESENT_DIFFERENT"


def quarter_year(period: str) -> int | None:
    match = re.match(r"^(\d{4})Q[1-4]$", period or "")
    return int(match.group(1)) if match else None


def senate_period_years(period: str) -> list[int]:
    years = [int(y) for y in re.findall(r"(\d{4})-\d{2}-\d{2}", period or "")]
    if not years:
        return []
    return list(range(min(years), max(years) + 1))


def payee_years(chamber: str, periods: Sequence[str]) -> list[int]:
    out: set[int] = set()
    for period in periods:
        if chamber == "HOUSE":
            year = quarter_year(period)
            if year is not None:
                out.add(year)
        else:
            out.update(senate_period_years(period))
    return sorted(out)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build(paths: Mapping[str, Path], output_root: Path, run_id: str,
          log=print) -> dict[str, Any]:
    output_root = Path(output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(
            f"immutable generation: refusing to write into non-empty {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    receipt_inputs: dict[str, Any] = {}

    def bind(name: str, rows: int | None = None) -> None:
        path = Path(paths[name])
        receipt_inputs[name] = {
            "path": str(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_of(path),
            "rows": rows,
        }

    log("[1/9] roster, staff directory, LDA queue, nickname table")
    roster, roster_by_pair, roster_counters = load_roster(paths["roster_keys"])
    staff = load_staff_directory(paths["staff_directory"])
    nicknames = load_nicknames(paths["nicknames"])
    lda_people = load_lda_queue(paths["lda_queue"])

    if roster_counters["alias_rows"] != INV["INV_ROSTER_ALIAS_ROWS"]:
        raise SystemExit(f"INV_ROSTER_ALIAS_ROWS: {roster_counters['alias_rows']}")
    if roster_counters["identity_rows"] != INV["INV_ROSTER_IDENTITY_ROWS"]:
        raise SystemExit(f"INV_ROSTER_IDENTITY_ROWS: {roster_counters['identity_rows']}")
    if (roster_counters["match_eligible_identity_rows"] !=
            INV["INV_ROSTER_MATCH_ELIGIBLE_IDENTITY_ROWS"]):
        raise SystemExit("INV_ROSTER_MATCH_ELIGIBLE_IDENTITY_ROWS")
    if len(staff) != INV["INV_CURRENT_STAFFERS"]:
        raise SystemExit(f"INV_CURRENT_STAFFERS: {len(staff)}")
    if len(lda_people) != INV["INV_LDA_QUEUE_ROWS"]:
        raise SystemExit(f"INV_LDA_QUEUE_ROWS: {len(lda_people)}")

    bind("roster_keys", roster_counters["alias_rows"])
    bind("staff_directory", len(staff))
    bind("nicknames", len(nicknames))
    bind("lda_queue", len(lda_people))

    log("[2/9] payee key universe (chambers, office/period collisions)")
    payee_key_facts = load_payee_keys(paths["payee_keys"])
    if len(payee_key_facts) != INV["INV_PAYEE_KEY_UNIVERSE"]:
        raise SystemExit(f"INV_PAYEE_KEY_UNIVERSE: {len(payee_key_facts)}")
    both_chambers = {k for k, v in payee_key_facts.items()
                     if len(v["chambers"]) > 1}
    if len(both_chambers) != INV["INV_PAYEE_KEYS_BOTH_CHAMBERS"]:
        raise SystemExit(f"INV_PAYEE_KEYS_BOTH_CHAMBERS: {len(both_chambers)}")
    published_senate = {k for k, v in payee_key_facts.items()
                        if "SENATE" in v["chambers"]}
    bind("payee_keys", len(payee_key_facts))

    log("[3/9] old-rule baseline")
    old_staffers = load_old_staffer_links(paths["old_staffer_links"])
    old_lda_in_lanes, old_lda_linked = load_old_lda_links(paths["old_lda_links"])
    old_status = collections.Counter(v["link_status"] for v in old_staffers.values())
    for label, key in (("LINKED", "INV_OLD_RULE_LINKED"),
                       ("NOT_ON_PAYROLL", "INV_OLD_RULE_NOT_ON_PAYROLL"),
                       ("MEMBER_UNRESOLVED", "INV_OLD_RULE_MEMBER_UNRESOLVED")):
        if old_status.get(label, 0) != INV[key]:
            raise SystemExit(f"{key}: {old_status.get(label, 0)}")
    if len(old_lda_in_lanes) != INV["INV_OLD_RULE_LDA_IN_MATCH_LANES"]:
        raise SystemExit(f"INV_OLD_RULE_LDA_IN_MATCH_LANES: {len(old_lda_in_lanes)}")
    bind("old_staffer_links", len(old_staffers))
    bind("old_lda_links", len(old_lda_in_lanes))

    log("[4/9] House ledger pass")
    house = house_pass(paths["house_ledger"])
    if house["counters"]["rows"] != INV["INV_HOUSE_LEDGER_ROWS"]:
        raise SystemExit(f"INV_HOUSE_LEDGER_ROWS: {house['counters']['rows']}")
    bind("house_ledger", house["counters"]["rows"])
    member_index = build_member_index(staff, nicknames)
    if len(member_index) != INV["INV_QUORUM_MEMBERS"]:
        raise SystemExit(f"INV_QUORUM_MEMBERS: {len(member_index)}")

    log("[5/9] Senate corpus pass")
    senate = senate_pass(paths["senate_corpus"], member_index, published_senate)
    if senate["counters"]["rows"] != INV["INV_SENATE_CORPUS_ROWS"]:
        raise SystemExit(f"INV_SENATE_CORPUS_ROWS: {senate['counters']['rows']}")
    if not senate["key_reproduction"]["exact"]:
        raise SystemExit(
            "Senate key reproduction is not exact; the office/period pairing "
            f"cannot be trusted: {senate['key_reproduction']}")
    bind("senate_corpus", senate["counters"]["rows"])

    log("[6/9] candidate lanes")
    lane_rows = collections.Counter()
    payees: dict[tuple[str, tuple[str, str, str | None]], dict[str, Any]] = {}
    pairs: dict[tuple[str, tuple[str, str, str | None], str], dict[str, Any]] = {}
    class_disagreements = collections.Counter()

    for name, expected in (("candidates_house_csv", INV["INV_CANDIDATES_HOUSE_CSV"]),
                           ("candidates_house_pdf", INV["INV_CANDIDATES_HOUSE_PDF"]),
                           ("candidates_senate", INV["INV_CANDIDATES_SENATE"])):
        adapter = ADAPTERS[name]
        count = 0
        for raw in read_ndjson_gz(paths[name]):
            count += 1
            record = adapter(raw)
            entity_key = (record["chamber"], record["payee_key"])
            entity = payees.get(entity_key)
            if entity is None:
                entity = {
                    "chamber": record["chamber"],
                    "key": record["payee_key"],
                    "offices": set(),
                    "periods": set(),
                    "titles": set(),
                    "container_kinds": set(),
                    "member_bioguides": set(),
                    "observation_rows": 0,
                    "max_offices_within_one_period": 0,
                    "shared_employee_rows": 0,
                    "raw_examples": set(),
                    "key_basis": set(),
                    "has_primary_parse": False,
                    "generational_suffixes": set(),
                    "lanes": set(),
                }
                payees[entity_key] = entity
            payee = record["payee"]
            entity["offices"].update(payee["offices"])
            entity["periods"].update(payee["periods"])
            entity["titles"].update(payee["titles"])
            entity["container_kinds"].update(payee["container_kinds"])
            entity["member_bioguides"].update(payee["member_bioguides"])
            entity["observation_rows"] += payee["observation_rows"]
            entity["max_offices_within_one_period"] = max(
                entity["max_offices_within_one_period"],
                payee["max_offices_within_one_period"])
            entity["shared_employee_rows"] += payee["shared_employee_rows"]
            if payee["raw_example"]:
                entity["raw_examples"].add(payee["raw_example"])
            entity["key_basis"].update(payee["key_basis"])
            entity["has_primary_parse"] |= payee["has_primary_parse"]
            entity["generational_suffixes"].update(payee["generational_suffixes"])
            entity["lanes"].add(record["lane"])

            pair_key = (record["chamber"], record["payee_key"], record["roster_id"])
            pair = pairs.get(pair_key)
            derived = derive_class(record["payee_key"], record["roster_key"])
            source_exact = record["source_match_class"] in (
                "EXACT_LAST_FIRST_MI", "EXACT_LAST_FIRST")
            if source_exact != (derived != "LOOSE"):
                class_disagreements[
                    f"{record['lane']}|{record['source_match_class']}|{derived}"] += 1
            if pair is None:
                pairs[pair_key] = {
                    "chamber": record["chamber"],
                    "payee_key": record["payee_key"],
                    "roster_id": record["roster_id"],
                    "roster_key": record["roster_key"],
                    "roster_key_basis": record["roster_key_basis"],
                    "roster_is_primary_key": record["roster_is_primary_key"],
                    "derived_class": derived,
                    "source_match_classes": {record["source_match_class"]},
                    "lanes": {record["lane"]},
                    "nickname_direction": record["nickname_direction"],
                    "nickname_formal_form": record["nickname_formal_form"],
                    "variant_basis": record["variant_basis"],
                    "variant_bridge": record["variant_bridge"],
                }
            else:
                pair["source_match_classes"].add(record["source_match_class"])
                pair["lanes"].add(record["lane"])
                if pair["derived_class"] != derived:
                    raise SystemExit(
                        "same pair derived two different classes: "
                        f"{pair_key} {pair['derived_class']} vs {derived}")
                pair["nickname_direction"] = (pair["nickname_direction"] or
                                              record["nickname_direction"])
                pair["variant_basis"] = pair["variant_basis"] or record["variant_basis"]
                pair["variant_bridge"] = pair["variant_bridge"] or record["variant_bridge"]
        lane_rows[name] = count
        if count != expected:
            raise SystemExit(f"INV rows for {name}: {count} != {expected}")
        bind(name, count)

    log(f"      payee entities {len(payees)}  candidate pairs {len(pairs)}")

    log("[7/9] tier assignment")
    quarter_index = house["quarter_index"]
    house_service = {b: set(q) for b, q in house["member_service"].items()}
    senate_service = {m: set(p) for m, p in senate["member_service"].items()}

    provisional: dict[tuple, dict[str, Any]] = {}
    for pair_key, pair in pairs.items():
        entity = payees[(pair["chamber"], pair["payee_key"])]
        person = roster[pair["roster_id"]]
        payee_key = pair["payee_key"]
        roster_key = pair["roster_key"]

        mi_state = middle_initial_state(payee_key[2], roster_key[2])
        suf_state = suffix_state(sorted(entity["generational_suffixes"]),
                                 person["generational_suffix"])
        pair_group = roster_by_pair.get((roster_key[0], roster_key[1]), set())
        roster_unique = len(pair_group) == 1
        duplicate_registration = (
            not roster_unique and
            len({roster[r]["spelling_fingerprint"] for r in pair_group}) == 1 and
            len({roster[r]["roster_kind"] for r in pair_group}) == 1)
        seen_other_chamber = payee_key in both_chambers
        facts = payee_key_facts.get(payee_key)
        if facts is None:
            raise SystemExit(
                f"payee key absent from the Index phase key universe: {payee_key}")
        payee_collision = (facts["office_period_collision"] or
                           facts["max_offices_within_one_period"] > 1 or
                           entity["max_offices_within_one_period"] > 1)
        payee_unique = (not payee_collision) and (not seen_other_chamber)

        signals: list[str] = []
        recorded: list[str] = []
        pairing = "NOT_APPLICABLE"

        if person["roster_kind"] == "quorum_staffer":
            staff_id = pair["roster_id"].split(":")[-1]
            member_display = person["quorum_member_display"]
            bioguide = (old_staffers.get(staff_id) or {}).get("member_bioguide")
            if pair["chamber"] == "HOUSE":
                if bioguide and f"HON:{bioguide}" in entity["offices"]:
                    signals.append("Q1_OWN_MEMBER_HOUSE_OFFICE")
                service = house_service.get(bioguide or "", set())
                if payee_key in house["keys_with_ledger_parse"]:
                    # The ledger's own parse produced this key, so the exact
                    # (container, quarter) pairing is known for it.
                    pairing = "EXACT"
                    mask = house["non_member_quarters"].get(payee_key, 0)
                    hit = any((mask >> quarter_index[q]) & 1
                              for q in service if q in quarter_index)
                elif entity["container_kinds"] and not (
                        set(entity["container_kinds"]) & set(MEMBER_CONTAINER_KINDS)):
                    # Alternate-parse key: no pairing, but every container this
                    # payee was ever seen in is a non-member office, so any
                    # overlapping quarter carries the pairing implicitly.
                    pairing = "IMPLIED_ALL_CONTAINERS_NON_MEMBER"
                    hit = bool(service & set(entity["periods"]))
                else:
                    pairing = "UNAVAILABLE"
                    hit = False
                if hit and service:
                    signals.append(
                        "Q3_NON_MEMBER_HOUSE_OFFICE_IN_MEMBER_SERVICE_QUARTER")
            else:
                for office in entity["offices"]:
                    resolved, _method = senate["office_resolution"].get(
                        office, (None, "OFFICE_NOT_IN_CORPUS"))
                    if resolved is not None and resolved == member_display:
                        signals.append("Q2_OWN_MEMBER_SENATE_OFFICE")
                        break
                service = senate_service.get(member_display or "", set())
                if payee_key in senate["keys_reproduced"]:
                    pairing = "EXACT"
                    hit = bool(service &
                               senate["non_personal_periods"].get(payee_key, frozenset()))
                else:
                    pairing = "UNAVAILABLE"
                    hit = False
                if hit and service:
                    signals.append(
                        "Q4_NON_MEMBER_SENATE_OFFICE_IN_MEMBER_SERVICE_PERIOD")
        else:
            info = lda_people.get(pair["roster_id"])
            years = payee_years(pair["chamber"], sorted(entity["periods"]))
            if info:
                cp_years = info["covered_position_years"]
                if cp_years and years:
                    low, high = min(cp_years), max(cp_years)
                    if any(low <= y <= high for y in years):
                        signals.append("L1_COVERED_POSITION_YEAR_OVERLAP")
                if info["covered_position_tokens"]:
                    office_tokens = set()
                    for office in entity["offices"]:
                        for token in re.split(r"[^A-Z0-9]+", prep(office)):
                            if len(token) >= 4 and token not in OFFICE_STOPWORDS:
                                office_tokens.add(token)
                    if office_tokens & info["covered_position_tokens"]:
                        signals.append("L2_COVERED_POSITION_OFFICE_TEXT_OVERLAP")
                if info["filing_years"] and years and min(info["filing_years"]) >= max(years):
                    if LDA_FILING_YEAR_SIGNAL_QUALIFIES:
                        signals.append("L3_FILING_YEARS_POSTDATE_SERVICE")
                    else:
                        recorded.append("L3_FILING_YEARS_POSTDATE_SERVICE")

        blocked: list[str] = []
        if pair["derived_class"] == "LOOSE":
            tier = "R4_LOOSE"
        else:
            if pair["derived_class"] != "EXACT_TRIPLE":
                blocked.append("MIDDLE_INITIAL_NOT_PRESENT_AND_EQUAL_ON_BOTH_SIDES")
            if not roster_unique:
                blocked.append("ROSTER_PAIR_ANSWERS_FOR_2PLUS_IDENTITY_ROWS")
            if payee_collision:
                blocked.append("PAYEE_KEY_IN_2PLUS_OFFICES_IN_ONE_PERIOD")
            if seen_other_chamber:
                blocked.append("PAYEE_KEY_ALSO_PRESENT_IN_THE_OTHER_CHAMBER")
            if not entity["has_primary_parse"]:
                # Every row behind this key came from a non-primary parse, i.e.
                # the last-token-only surname alternate parse_last_first emits
                # beside the full surname ("DE LA CRUZ, MARIA" -> also
                # ("cruz","maria",None)).  derive_class cannot see that and
                # grades the truncated match EXACT, so R1 would assert an
                # identity on a surname the record never printed.
                blocked.append("PAYEE_KEY_FROM_A_TRUNCATED_SURNAME_PARSE_ONLY")
            contradicted = (mi_state == "BOTH_PRESENT_DIFFERENT" or
                            suf_state == "BOTH_PRESENT_DIFFERENT")
            if not blocked:
                tier = "R1_EXACT_UNIQUE"
            elif signals and not contradicted:
                tier = "R2_EXACT_CORROBORATED"
            else:
                tier = "R3_EXACT_AMBIGUOUS"
                if contradicted:
                    blocked.append("CONTRADICTING_MIDDLE_INITIAL_OR_SUFFIX")

        would_be_r1_relaxed = (
            pair["derived_class"] == "EXACT_PAIR" and
            mi_state in ("ROSTER_MISSING", "PAYEE_MISSING", "NEITHER") and
            roster_unique and payee_unique)

        provisional[pair_key] = {
            "pair": pair,
            "entity": entity,
            "person": person,
            "tier": tier,
            "signals": signals,
            "recorded_signals": recorded,
            "pairing": pairing,
            "mi_state": mi_state,
            "suffix_state": suf_state,
            "roster_unique": roster_unique,
            "roster_pair_identity_rows": len(pair_group),
            "roster_pair_fingerprints": len(
                {roster[r]["spelling_fingerprint"] for r in pair_group}),
            "duplicate_registration": duplicate_registration,
            "payee_unique": payee_unique,
            "payee_collision": payee_collision,
            "index_max_offices_within_one_period":
                facts["max_offices_within_one_period"],
            "index_shared_employee_rows": facts["shared_employee_rows"],
            "index_observation_rows": facts["observation_rows"],
            "seen_other_chamber": seen_other_chamber,
            "blocked": blocked,
            "would_be_r1_relaxed": would_be_r1_relaxed,
            "tie_demoted_from_r1": False,
        }

    # Ties.  A candidate that would be R1 but shares its tier with another
    # candidate on either side is demoted; no tie is broken.
    r1_by_payee = collections.Counter()
    r1_by_roster = collections.Counter()
    for key, record in provisional.items():
        if record["tier"] == "R1_EXACT_UNIQUE":
            r1_by_payee[(record["pair"]["chamber"], record["pair"]["payee_key"])] += 1
            r1_by_roster[record["pair"]["roster_id"]] += 1
    for key, record in provisional.items():
        if record["tier"] != "R1_EXACT_UNIQUE":
            continue
        payee_ref = (record["pair"]["chamber"], record["pair"]["payee_key"])
        if r1_by_payee[payee_ref] > 1 or r1_by_roster[record["pair"]["roster_id"]] > 1:
            record["tier"] = "R3_EXACT_AMBIGUOUS"
            record["tie_demoted_from_r1"] = True
            record["blocked"].append("TIE_AT_R1_NEVER_BROKEN_SILENTLY")

    tie_by_payee = collections.Counter()
    tie_by_roster = collections.Counter()
    for record in provisional.values():
        tie_by_payee[(record["pair"]["chamber"], record["pair"]["payee_key"],
                      record["tier"])] += 1
        tie_by_roster[(record["pair"]["roster_id"], record["tier"])] += 1

    log("[8/9] emit")
    counters = collections.Counter()
    rows_by_roster: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)

    def candidate_rows() -> Iterator[dict[str, Any]]:
        for key in sorted(provisional,
                          key=lambda k: (k[2], k[0], k[1][0], k[1][1], k[1][2] or "")):
            record = provisional[key]
            pair = record["pair"]
            entity = record["entity"]
            person = record["person"]
            tier = record["tier"]
            payee_ref = (pair["chamber"], pair["payee_key"], tier)
            tie_roster_for_payee = tie_by_payee[payee_ref]
            tie_payee_for_roster = tie_by_roster[(pair["roster_id"], tier)]
            offices, offices_truncated = capped(entity["offices"])
            periods, periods_truncated = capped(entity["periods"])
            titles, titles_truncated = capped(entity["titles"])
            staff_id = (pair["roster_id"].split(":")[-1]
                        if person["roster_kind"] == "quorum_staffer" else None)
            lda_info = (lda_people.get(pair["roster_id"])
                        if person["roster_kind"] == "lda_lobbyist" else None)
            all_periods = sorted(entity["periods"])
            if pair["chamber"] == "HOUSE":
                office_kinds = sorted(entity["container_kinds"])
            else:
                office_kinds = sorted({
                    (SENATE_PERSONAL_OFFICE_KIND
                     if senate_office_is_personal(office) is not None
                     else SENATE_NON_PERSONAL_OFFICE_KIND)
                    for office in entity["offices"]})
            row = {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "evidence": {
                    "corroboration_signal_count": len(record["signals"]),
                    "corroboration_signals": sorted(record["signals"]),
                    "corroboration_signals_recorded_non_qualifying":
                        sorted(record["recorded_signals"]),
                    "derived_name_class": pair["derived_class"],
                    "generational_suffix_agreement": record["suffix_state"],
                    "generational_suffix_payee": sorted(entity["generational_suffixes"]),
                    "generational_suffix_roster": sorted(person["generational_suffix"]),
                    "member_service_pairing_availability": record["pairing"],
                    "middle_initial_agreement": record["mi_state"],
                    "middle_initial_payee": pair["payee_key"][2],
                    "middle_initial_roster": pair["roster_key"][2],
                    "nickname_direction": pair["nickname_direction"],
                    "nickname_formal_form": pair["nickname_formal_form"],
                    "payee_key_seen_in_other_chamber": record["seen_other_chamber"],
                    "payee_office_period_collision": record["payee_collision"],
                    "payee_unique_payroll_person": record["payee_unique"],
                    "r1_blocked_by": sorted(set(record["blocked"])),
                    "r1_blocked_by_same_spelling_duplicate_registration":
                        record["duplicate_registration"],
                    "roster_pair_distinct_spelling_fingerprints":
                        record["roster_pair_fingerprints"],
                    "roster_pair_identity_rows": record["roster_pair_identity_rows"],
                    "roster_unique_identity": record["roster_unique"],
                    "source_match_classes": sorted(pair["source_match_classes"]),
                    "variant_basis": pair["variant_basis"],
                    "variant_surname_bridge": pair["variant_bridge"],
                    "would_be_r1_under_relaxed_middle_initial":
                        record["would_be_r1_relaxed"],
                },
                "lanes": sorted(pair["lanes"]),
                "lda_covered_position_years": (lda_info["covered_position_years"]
                                               if lda_info else None),
                "lda_filing_years": lda_info["filing_years"] if lda_info else None,
                "lda_priority": lda_info["priority"] if lda_info else None,
                "payee_chamber": pair["chamber"],
                "payee_container_kinds": sorted(entity["container_kinds"]),
                "payee_given_key": pair["payee_key"][1],
                "payee_has_primary_parse": entity["has_primary_parse"],
                "payee_key_basis": sorted(entity["key_basis"]),
                "payee_max_offices_within_one_period":
                    record["index_max_offices_within_one_period"],
                "payee_max_offices_within_one_period_lane":
                    entity["max_offices_within_one_period"],
                "payee_member_bioguides": sorted(entity["member_bioguides"]),
                "payee_middle_initial": pair["payee_key"][2],
                "payee_observation_rows": entity["observation_rows"],
                "payee_office_kinds": office_kinds,
                "payee_offices": offices,
                "payee_offices_distinct": len(entity["offices"]),
                "payee_offices_truncated": offices_truncated,
                "payee_period_first": all_periods[0] if all_periods else None,
                "payee_period_last": all_periods[-1] if all_periods else None,
                "payee_periods": periods,
                "payee_periods_distinct": len(entity["periods"]),
                "payee_periods_truncated": periods_truncated,
                "payee_raw_example": (sorted(entity["raw_examples"])[0]
                                      if entity["raw_examples"] else None),
                "payee_shared_employee_rows": record["index_shared_employee_rows"],
                "payee_shared_employee_rows_lane": entity["shared_employee_rows"],
                "payee_surname_key": pair["payee_key"][0],
                "payee_titles": titles,
                "payee_titles_distinct": len(entity["titles"]),
                "payee_titles_truncated": titles_truncated,
                "phase": PHASE,
                "quorum_member_bioguide": (
                    (old_staffers.get(staff_id) or {}).get("member_bioguide")
                    if staff_id else None),
                "quorum_member_display": person["quorum_member_display"],
                "quorum_staff_id": staff_id,
                "quorum_title": person["quorum_title"],
                "resolution_tier": tier,
                "resolution_tier_rank": TIER_RANK[tier],
                "review_status": "REVIEW_REQUIRED",
                "roster_display_name": person["display_name"],
                "roster_given_key": pair["roster_key"][1],
                "roster_id": pair["roster_id"],
                "roster_is_primary_key": pair["roster_is_primary_key"],
                "roster_key_basis": pair["roster_key_basis"],
                "roster_kind": person["roster_kind"],
                "roster_middle_initial": pair["roster_key"][2],
                "roster_source": person["roster_source"],
                "roster_spelling_fingerprint": person["spelling_fingerprint"],
                "roster_surname_key": pair["roster_key"][0],
                "rule_version": RULE_VERSION,
                "run_id": run_id,
                "schema_id": CANDIDATE_SCHEMA_ID,
                "tie_demoted_from_r1": record["tie_demoted_from_r1"],
                "tie_size": max(tie_roster_for_payee, tie_payee_for_roster),
                "tie_size_payee_for_roster": tie_payee_for_roster,
                "tie_size_roster_for_payee": tie_roster_for_payee,
            }
            counters[f"tier:{tier}"] += 1
            counters[f"tier_kind:{tier}|{person['roster_kind']}"] += 1
            for signal in record["signals"]:
                counters[f"signal:{signal}"] += 1
            if tier == "R2_EXACT_CORROBORATED":
                counters["r2:signature:" + "+".join(sorted(record["signals"]))] += 1
                if not (set(record["signals"]) &
                        {"Q1_OWN_MEMBER_HOUSE_OFFICE",
                         "Q2_OWN_MEMBER_SENATE_OFFICE",
                         "L1_COVERED_POSITION_YEAR_OVERLAP",
                         "L2_COVERED_POSITION_OFFICE_TEXT_OVERLAP"}):
                    counters["r2_resting_only_on_the_service_period_leg"] += 1
            if record["would_be_r1_relaxed"]:
                counters["would_be_r1_relaxed"] += 1
            if record["duplicate_registration"]:
                counters["duplicate_registration_rows"] += 1
            if record["recorded_signals"]:
                counters["rows_with_non_qualifying_signal"] += 1
                if tier == "R3_EXACT_AMBIGUOUS" and not record["signals"]:
                    counters["r3_rows_that_L3_alone_would_promote"] += 1
            rows_by_roster[pair["roster_id"]].append({
                "tier": tier,
                "tier_rank": TIER_RANK[tier],
                "chamber": pair["chamber"],
                "offices": sorted(entity["offices"]),
                "periods": all_periods,
                "titles": sorted(entity["titles"]),
                "container_kinds": sorted(entity["container_kinds"]),
                "office_kinds": office_kinds,
                "tie_size": max(tie_roster_for_payee, tie_payee_for_roster),
                "signals": sorted(record["signals"]),
                "payee_key": list(pair["payee_key"]),
            })
            yield row

    schemas = all_schemas()
    candidate_count = write_ndjson_gz(
        output_root / CANDIDATE_FILE,
        validated(candidate_rows(), schemas[CANDIDATE_FILE]))

    def rollup(roster_id: str) -> dict[str, Any]:
        rows = rows_by_roster.get(roster_id, [])
        by_tier = collections.Counter(r["tier"] for r in rows)
        if rows:
            best_rank = min(r["tier_rank"] for r in rows)
            best_tier = TIER_ORDER[best_rank - 1]
            best_rows = [r for r in rows if r["tier"] == best_tier]
            status = STATUS_FOR_TIER[best_tier]
        else:
            best_tier, best_rank, best_rows, status = None, None, [], "NOT_FOUND"
        offices, offices_truncated = capped(
            o for r in best_rows for o in r["offices"])
        periods = sorted({p for r in best_rows for p in r["periods"]})
        titles, titles_truncated = capped(t for r in best_rows for t in r["titles"])
        containers = sorted({c for r in best_rows for c in r["container_kinds"]})
        office_kinds = sorted({k for r in best_rows for k in r["office_kinds"]})
        signals = sorted({s for r in best_rows for s in r["signals"]})
        return {
            "best_tier": best_tier,
            "best_tier_rank": best_rank,
            "candidate_count": len(rows),
            "candidates_by_tier": {t: by_tier.get(t, 0) for t in TIER_ORDER},
            "corroboration_signals_at_best_tier": signals,
            "matched_chambers": sorted({r["chamber"] for r in best_rows}),
            "matched_container_kinds": containers,
            "matched_office_kinds": office_kinds,
            "matched_offices": offices,
            "matched_offices_distinct": len({o for r in best_rows for o in r["offices"]}),
            "matched_offices_truncated": offices_truncated,
            "matched_period_first": periods[0] if periods else None,
            "matched_period_last": periods[-1] if periods else None,
            "matched_periods_distinct": len(periods),
            "matched_titles": titles,
            "matched_titles_truncated": titles_truncated,
            "payee_keys_at_best_tier": sorted(
                "|".join(str(p) if p is not None else "" for p in r["payee_key"])
                for r in best_rows),
            "status": status,
            "tie_size_at_best_tier": max((r["tie_size"] for r in best_rows), default=0),
        }

    def staffer_rows() -> Iterator[dict[str, Any]]:
        for staff_id in sorted(staff, key=lambda s: int(s)):
            entry = staff[staff_id]
            roster_id = f"quorum:staff:{staff_id}"
            person = roster.get(roster_id, {})
            old = old_staffers.get(staff_id) or {}
            body = rollup(roster_id)
            recovered = (body["status"] in ("RESOLVED_R1", "RESOLVED_R2") and
                         old.get("link_status") != "LINKED")
            counters[f"staffer_status:{body['status']}"] += 1
            counters[f"staffer_old_new:{old.get('link_status')}|{body['status']}"] += 1
            if recovered:
                counters["staffer_recovered"] += 1
                if body["matched_container_kinds"] and not (
                        set(body["matched_container_kinds"]) &
                        set(MEMBER_CONTAINER_KINDS)):
                    counters["staffer_recovered_non_member_office_only"] += 1
                if set(body["matched_container_kinds"]) & {"committee", "leadership"}:
                    counters["staffer_recovered_touching_committee_or_leadership"] += 1
                if "SENATE" in body["matched_chambers"]:
                    counters["staffer_recovered_reaching_senate"] += 1
            row = dict(body)
            row.update({
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "display_name": entry["display_name"],
                "member_bioguide": old.get("member_bioguide"),
                "member_display": entry["member_display"],
                "old_rule_link_status": old.get("link_status"),
                "old_rule_recovered": recovered,
                "phase": PHASE,
                "quorum_staff_id": staff_id,
                "quorum_star": entry.get("star"),
                "review_status": "REVIEW_REQUIRED",
                "roster_id": roster_id,
                "roster_match_eligible": bool(person.get("match_eligible")),
                "rule_version": RULE_VERSION,
                "run_id": run_id,
                "schema_id": STAFFER_SCHEMA_ID,
                "title_raw": entry["title_raw"],
            })
            yield row

    staffer_count = write_ndjson_gz(
        output_root / STAFFER_FILE, validated(staffer_rows(), schemas[STAFFER_FILE]))

    def lda_rows() -> Iterator[dict[str, Any]]:
        for person_id in sorted(lda_people):
            info = lda_people[person_id]
            person = roster.get(person_id, {})
            body = rollup(person_id)
            counters[f"lda_status:{body['status']}"] += 1
            in_lanes = person_id in old_lda_in_lanes
            if body["status"] in ("RESOLVED_R1", "RESOLVED_R2"):
                counters["lda_resolved"] += 1
                if not in_lanes:
                    counters["lda_resolved_outside_old_match_lanes"] += 1
            row = dict(body)
            row.update({
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "covered_position_present": info["covered_position_present"],
                "covered_position_years": info["covered_position_years"],
                "display_name": info["display_name"],
                "filing_years": info["filing_years"],
                "lda_identity_status": info["identity_status"],
                "lda_priority": info["priority"],
                "lda_source_person_id": person_id,
                "old_rule_in_match_lanes": in_lanes,
                "old_rule_linked": person_id in old_lda_linked,
                "phase": PHASE,
                "review_status": "REVIEW_REQUIRED",
                "roster_id": person_id,
                "roster_match_eligible": bool(person.get("match_eligible")),
                "rule_version": RULE_VERSION,
                "run_id": run_id,
                "schema_id": LDA_SCHEMA_ID,
            })
            yield row

    lda_count = write_ndjson_gz(
        output_root / LDA_FILE, validated(lda_rows(), schemas[LDA_FILE]))

    log("[9/9] receipt")
    inputs_dir = output_root / "inputs"
    for name in ("candidates_house_csv", "candidates_house_pdf",
                 "candidates_senate", "roster_keys", "payee_keys"):
        copy_file(Path(paths[name]), inputs_dir / Path(paths[name]).name)

    old_to_new = {k.split(":", 1)[1]: v for k, v in counters.items()
                  if k.startswith("staffer_old_new:")}
    recovery_from_not_on_payroll = {
        status: sum(v for k, v in old_to_new.items()
                    if k.startswith("NOT_ON_PAYROLL|") and k.endswith("|" + status))
        for status in STATUS_VALUES}
    recovery_from_member_unresolved = {
        status: sum(v for k, v in old_to_new.items()
                    if k.startswith("MEMBER_UNRESOLVED|") and k.endswith("|" + status))
        for status in STATUS_VALUES}
    recovery_from_linked = {
        status: sum(v for k, v in old_to_new.items()
                    if k.startswith("LINKED|") and k.endswith("|" + status))
        for status in STATUS_VALUES}

    files: dict[str, Any] = {}
    for name, rows in ((CANDIDATE_FILE, candidate_count),
                       (STAFFER_FILE, staffer_count),
                       (LDA_FILE, lda_count)):
        path = output_root / name
        files[name] = {"bytes": path.stat().st_size, "rows": rows,
                       "sha256": sha256_of(path)}

    office_methods = collections.Counter(
        method for _display, method in senate["office_resolution"].values())
    senate_personal = [o for o in senate["office_resolution"]
                       if senate_office_is_personal(o) is not None]
    senate_personal_resolved = [
        o for o in senate_personal if senate["office_resolution"][o][0] is not None]

    receipt = {
        "canonical_employment_promotions": INV["INV_CANONICAL_EMPLOYMENT_PROMOTIONS"],
        "canonical_identity_promotions": INV["INV_CANONICAL_IDENTITY_PROMOTIONS"],
        "corroboration_signals": CORROBORATION_SIGNALS,
        "corroboration_signals_recorded_non_qualifying": NON_QUALIFYING_SIGNALS,
        "counts": {
            "candidate_rows": candidate_count,
            "candidate_rows_by_tier": {
                t: counters.get(f"tier:{t}", 0) for t in TIER_ORDER},
            "candidate_rows_by_tier_and_roster_kind": {
                f"{t}|{kind}": counters.get(f"tier_kind:{t}|{kind}", 0)
                for t in TIER_ORDER
                for kind in ("quorum_staffer", "lda_lobbyist")},
            "class_label_disagreements": dict(class_disagreements),
            "current_staffer_rows": staffer_count,
            "lda_rows": lda_count,
            "payee_entities": len(payees),
            "payee_entities_by_chamber": dict(collections.Counter(
                chamber for chamber, _key in payees)),
            "rows_with_duplicate_registration_block":
                counters.get("duplicate_registration_rows", 0),
            "rows_with_non_qualifying_signal":
                counters.get("rows_with_non_qualifying_signal", 0),
            "would_be_r1_under_relaxed_middle_initial":
                counters.get("would_be_r1_relaxed", 0),
            "r3_rows_that_the_filing_year_signal_alone_would_promote":
                counters.get("r3_rows_that_L3_alone_would_promote", 0),
        },
        "dials": {
            "LDA_FILING_YEAR_SIGNAL_QUALIFIES": LDA_FILING_YEAR_SIGNAL_QUALIFIES,
            "LIST_CAP": LIST_CAP,
            "MEMBER_CONTAINER_KINDS": list(MEMBER_CONTAINER_KINDS),
            "NON_MEMBER_CONTAINER_KINDS": list(NON_MEMBER_CONTAINER_KINDS),
            "SENATE_PERSONAL_OFFICE_PREFIXES": list(SENATE_PERSONAL_OFFICE_PREFIXES),
            "freeze_status": "UNTESTED_DEFAULTS_PENDING_FREEZE",
        },
        "files": files,
        "inv": INV,
        "inputs": receipt_inputs,
        "inputs_copied_into_generation": sorted(
            p.name for p in inputs_dir.iterdir()) if inputs_dir.exists() else [],
        "lda_resolution": {
            "denominator_lda_queue_rows": len(lda_people),
            "denominator_old_rule_in_match_lanes": len(old_lda_in_lanes),
            "old_rule_linked": len(old_lda_linked),
            "resolved_r1_or_r2": counters.get("lda_resolved", 0),
            "resolved_outside_old_match_lanes":
                counters.get("lda_resolved_outside_old_match_lanes", 0),
            "status_counts": {s: counters.get(f"lda_status:{s}", 0)
                              for s in STATUS_VALUES},
        },
        "member_resolution": {
            "house_bioguides_with_service_quarters": len(house["member_service"]),
            "senate_office_resolution_methods": dict(office_methods),
            "senate_personal_offices": len(senate_personal),
            "senate_personal_offices_resolved_to_a_current_member":
                len(senate_personal_resolved),
            "senate_members_with_service_periods": len(senate["member_service"]),
        },
        "phase": PHASE,
        "quarter_index_size": len(quarter_index),
        "recovery_against_old_rule": {
            "denominator_current_staffers": len(staff),
            "new_status_counts": {s: counters.get(f"staffer_status:{s}", 0)
                                  for s in STATUS_VALUES},
            "old_status_counts": dict(old_status),
            "recovered_total": counters.get("staffer_recovered", 0),
            "recovered_reaching_senate":
                counters.get("staffer_recovered_reaching_senate", 0),
            "recovered_touching_committee_or_leadership":
                counters.get("staffer_recovered_touching_committee_or_leadership", 0),
            "recovered_with_no_member_office_container_at_all":
                counters.get("staffer_recovered_non_member_office_only", 0),
            "transition_matrix": old_to_new,
            "from_LINKED": recovery_from_linked,
            "from_MEMBER_UNRESOLVED": recovery_from_member_unresolved,
            "from_NOT_ON_PAYROLL": recovery_from_not_on_payroll,
        },
        "review_status": "REVIEW_REQUIRED",
        "rule_version": RULE_VERSION,
        "run_id": run_id,
        "schema_id": RECEIPT_SCHEMA_ID,
        "senate_key_reproduction": senate["key_reproduction"],
        "status": "PASS",
        "tier_definitions": {
            "R1_EXACT_UNIQUE":
                "surname, given and middle initial all present and equal; the "
                "roster (surname, given) pair answers for exactly one identity "
                "row; the payee key was never in two offices in one period and "
                "is not present in the other chamber; and the candidate is not "
                "in a tie.",
            "R2_EXACT_CORROBORATED":
                "surname and given equal, not R1, no contradicting middle "
                "initial or generational suffix, and at least one qualifying "
                "corroboration signal.",
            "R3_EXACT_AMBIGUOUS":
                "surname and given equal, neither R1 nor R2.  Candidate only.",
            "R4_LOOSE":
                "nickname, first-initial or surname-variant class.  Candidate "
                "only.",
        },
        "tier_order": list(TIER_ORDER),
    }
    validate_instance(receipt, schemas[RECEIPT_FILE])
    write_json(output_root / RECEIPT_FILE, receipt)
    return receipt


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
def _gate_properties() -> dict[str, Any]:
    return {
        "canonical_eligible": {"type": "boolean", "const": False},
        "canonical_employment_promoted": {"type": "boolean", "const": False},
        "canonical_identity_decision": {"type": "string",
                                        "const": "NOT_ADJUDICATED"},
        "review_status": {"type": "string", "const": "REVIEW_REQUIRED"},
    }


# Every emitted field is enumerated below and every schema is CLOSED
# ("additionalProperties": False).  That is load-bearing, not cosmetic: with
# additionalProperties True an undeclared field is PERMITTED, so the
# "schema rejects an unknown field" negative control can never fire and the
# conformance gate is vacuous - it would pass a row carrying any amount of
# undeclared content.  Closing the schemas is what gives that gate teeth.
# Because write_rows() validates every row against its schema at write time,
# a field added to an output without being declared here now fails the build
# loudly instead of shipping unnoticed.
_STRING: dict[str, Any] = {"type": "string"}
_STRING_OR_NULL: dict[str, Any] = {"type": ["string", "null"]}
_BOOLEAN: dict[str, Any] = {"type": "boolean"}
_COUNT: dict[str, Any] = {"type": "integer", "minimum": 0}
_COUNT_OR_NULL: dict[str, Any] = {"type": ["integer", "null"]}
_OBJECT: dict[str, Any] = {"type": "object"}
_STRING_LIST: dict[str, Any] = {"type": "array", "items": {"type": "string"}}
_INT_LIST: dict[str, Any] = {"type": "array", "items": {"type": "integer"}}
_INT_LIST_OR_NULL: dict[str, Any] = {"type": ["array", "null"],
                                     "items": {"type": "integer"}}


def _closed(schema_id: str, properties: Mapping[str, Any]) -> dict[str, Any]:
    """A closed object schema that requires every declared property.

    Each payload writes a fixed record shape - every field is present on 100%
    of rows, nullable where the value can be absent - so "required" is the
    full property list rather than a hand-picked subset.  That keeps the
    dropped-required-field control meaningful for any field, not just a few.
    """

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": schema_id,
        "type": "object",
        "required": sorted(properties),
        "properties": dict(properties),
        "additionalProperties": False,
    }


def candidate_schema() -> dict[str, Any]:
    return _closed(CANDIDATE_SCHEMA_ID, {
        **_gate_properties(),
        "evidence": _OBJECT,
        "lanes": _STRING_LIST,
        "lda_covered_position_years": _INT_LIST_OR_NULL,
        "lda_filing_years": _INT_LIST_OR_NULL,
        "lda_priority": _STRING_OR_NULL,
        "payee_chamber": {"type": "string", "enum": ["HOUSE", "SENATE"]},
        "payee_container_kinds": _STRING_LIST,
        "payee_given_key": _STRING,
        "payee_has_primary_parse": _BOOLEAN,
        "payee_key_basis": _STRING_LIST,
        "payee_max_offices_within_one_period": _COUNT,
        "payee_max_offices_within_one_period_lane": _COUNT,
        "payee_member_bioguides": _STRING_LIST,
        "payee_middle_initial": _STRING_OR_NULL,
        "payee_observation_rows": _COUNT,
        "payee_office_kinds": _STRING_LIST,
        "payee_offices": _STRING_LIST,
        "payee_offices_distinct": _COUNT,
        "payee_offices_truncated": _BOOLEAN,
        "payee_period_first": _STRING,
        "payee_period_last": _STRING,
        "payee_periods": _STRING_LIST,
        "payee_periods_distinct": _COUNT,
        "payee_periods_truncated": _BOOLEAN,
        "payee_raw_example": _STRING,
        "payee_shared_employee_rows": _COUNT,
        "payee_shared_employee_rows_lane": _COUNT,
        "payee_surname_key": _STRING,
        "payee_titles": _STRING_LIST,
        "payee_titles_distinct": _COUNT,
        "payee_titles_truncated": _BOOLEAN,
        "phase": {"type": "string", "const": PHASE},
        "quorum_member_bioguide": _STRING_OR_NULL,
        "quorum_member_display": _STRING_OR_NULL,
        "quorum_staff_id": _STRING_OR_NULL,
        "quorum_title": _STRING_OR_NULL,
        "resolution_tier": {"type": "string", "enum": list(TIER_ORDER)},
        "resolution_tier_rank": {"type": "integer", "minimum": 1, "maximum": 4},
        "roster_display_name": _STRING,
        "roster_given_key": _STRING,
        "roster_id": _STRING,
        "roster_is_primary_key": _BOOLEAN,
        "roster_key_basis": _STRING,
        "roster_kind": {"type": "string",
                        "enum": ["quorum_staffer", "lda_lobbyist"]},
        "roster_middle_initial": _STRING_OR_NULL,
        "roster_source": _STRING,
        "roster_spelling_fingerprint": _STRING,
        "roster_surname_key": _STRING,
        "rule_version": {"type": "string", "const": RULE_VERSION},
        "run_id": _STRING,
        "schema_id": {"type": "string", "const": CANDIDATE_SCHEMA_ID},
        "tie_demoted_from_r1": _BOOLEAN,
        "tie_size": {"type": "integer", "minimum": 1},
        "tie_size_payee_for_roster": {"type": "integer", "minimum": 1},
        "tie_size_roster_for_payee": {"type": "integer", "minimum": 1},
    })


def _rollup_common_properties(schema_id: str) -> dict[str, Any]:
    return {
        **_gate_properties(),
        "best_tier": {"type": ["string", "null"], "enum": [*TIER_ORDER, None]},
        "best_tier_rank": _COUNT_OR_NULL,
        "candidate_count": _COUNT,
        "candidates_by_tier": _OBJECT,
        "corroboration_signals_at_best_tier": _STRING_LIST,
        "display_name": _STRING,
        "matched_chambers": _STRING_LIST,
        "matched_container_kinds": _STRING_LIST,
        "matched_office_kinds": _STRING_LIST,
        "matched_offices": _STRING_LIST,
        "matched_offices_distinct": _COUNT,
        "matched_offices_truncated": _BOOLEAN,
        "matched_period_first": _STRING_OR_NULL,
        "matched_period_last": _STRING_OR_NULL,
        "matched_periods_distinct": _COUNT,
        "matched_titles": _STRING_LIST,
        "matched_titles_truncated": _BOOLEAN,
        "payee_keys_at_best_tier": _STRING_LIST,
        "phase": {"type": "string", "const": PHASE},
        "roster_id": _STRING,
        "roster_match_eligible": _BOOLEAN,
        "rule_version": {"type": "string", "const": RULE_VERSION},
        "run_id": _STRING,
        "schema_id": {"type": "string", "const": schema_id},
        "status": {"type": "string", "enum": list(STATUS_VALUES)},
        "tie_size_at_best_tier": _COUNT,
    }


def staffer_schema() -> dict[str, Any]:
    return _closed(STAFFER_SCHEMA_ID, {
        **_rollup_common_properties(STAFFER_SCHEMA_ID),
        "member_bioguide": _STRING_OR_NULL,
        "member_display": _STRING,
        "old_rule_link_status": _STRING,
        "old_rule_recovered": _BOOLEAN,
        "quorum_staff_id": _STRING,
        "quorum_star": {"type": "integer"},
        "title_raw": _STRING,
    })


def lda_schema() -> dict[str, Any]:
    return _closed(LDA_SCHEMA_ID, {
        **_rollup_common_properties(LDA_SCHEMA_ID),
        "covered_position_present": _BOOLEAN,
        "covered_position_years": _INT_LIST,
        "filing_years": _INT_LIST,
        "lda_identity_status": _STRING,
        "lda_priority": _STRING,
        "lda_source_person_id": _STRING,
        "old_rule_in_match_lanes": _BOOLEAN,
        "old_rule_linked": _BOOLEAN,
    })


def receipt_schema() -> dict[str, Any]:
    return _closed(RECEIPT_SCHEMA_ID, {
        "canonical_employment_promotions": {"type": "integer", "const": 0},
        "canonical_identity_promotions": {"type": "integer", "const": 0},
        "corroboration_signals": _OBJECT,
        "corroboration_signals_recorded_non_qualifying": _OBJECT,
        "counts": _OBJECT,
        "dials": _OBJECT,
        "files": _OBJECT,
        "inputs": _OBJECT,
        "inputs_copied_into_generation": _STRING_LIST,
        "inv": _OBJECT,
        "lda_resolution": _OBJECT,
        "member_resolution": _OBJECT,
        "phase": {"type": "string", "const": PHASE},
        "quarter_index_size": _COUNT,
        "recovery_against_old_rule": _OBJECT,
        "review_status": {"type": "string", "const": "REVIEW_REQUIRED"},
        "rule_version": {"type": "string", "const": RULE_VERSION},
        "run_id": _STRING,
        "schema_id": {"type": "string", "const": RECEIPT_SCHEMA_ID},
        "senate_key_reproduction": _OBJECT,
        "status": {"type": "string", "enum": ["PASS", "FAIL"]},
        "tier_definitions": _OBJECT,
        "tier_order": _STRING_LIST,
    })


def all_schemas() -> dict[str, dict[str, Any]]:
    return {
        CANDIDATE_FILE: candidate_schema(),
        STAFFER_FILE: staffer_schema(),
        LDA_FILE: lda_schema(),
        RECEIPT_FILE: receipt_schema(),
    }


def write_schemas(target_dir: Path) -> list[str]:
    written: list[str] = []
    for output_name, schema in all_schemas().items():
        validate_schema_definition(schema)
        path = target_dir / SCHEMA_FILES[output_name]
        write_json(path, schema)
        written.append(str(path))
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--scratch-dir", required=True)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--write-schemas", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo_root).resolve()
    paths = default_paths(repo, Path(args.scratch_dir).resolve())
    log = (lambda *a, **k: None) if args.quiet else print

    if args.write_schemas:
        target = repo / "audits" / "staffer_network" / SCHEMA_DIR_NAME
        for path in write_schemas(target):
            log("schema", path)

    receipt = build(paths, Path(args.output_root).resolve(), args.run_id, log=log)
    log(json.dumps({
        "status": receipt["status"],
        "candidate_rows": receipt["counts"]["candidate_rows"],
        "by_tier": receipt["counts"]["candidate_rows_by_tier"],
        "staffers": receipt["recovery_against_old_rule"]["new_status_counts"],
        "lda": receipt["lda_resolution"]["status_counts"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
