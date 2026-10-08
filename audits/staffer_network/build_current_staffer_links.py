#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rebuild the current-staffer -> Hill payroll links under the CORRECTED rule.

WHY THIS EXISTS
---------------
``build_hill_personnel_spine.py`` links a Quorum current staffer to the payroll
only through ``latest_house_by_bioguide`` (:2162-2187): a House span, belonging
to the staffer's OWN member's office, whose ``last_period`` equals the LATEST
House quarter.  Three structural exclusions follow from that one predicate, none
of them intended:

  * the ENTIRE SENATE is unreachable -- the candidate set is built from House
    spans only, so no Senate staffer can ever link;
  * every committee, leadership, admin and member-organization office is
    unreachable -- the candidate set is keyed on ``member_bioguide``, which only
    a member office carries;
  * anyone whose payroll trace stops before the latest quarter is unreachable.

Measured consequence on generation ``hill_personnel_spine_20260902_v1_primary``:
LINKED 1,985 / NOT_ON_PAYROLL 3,650 / MEMBER_UNRESOLVED 138 / NAME_COLLISION 0
of 5,773.

THE CORRECTED RULE
------------------
For every one of the 5,773 staffers, search ALL offices in BOTH chambers across
ALL periods -- never restricted by office or by period -- then assign the single
best tier:

  T1_OWN_MEMBER_EXACT        exact last+first (+ middle initial when both sides
                             carry one); the office is their own member's
                             office.
  T2_NON_MEMBER_OFFICE_EXACT exact name in a committee / leadership / admin /
                             member-organization office, AND the observed
                             periods overlap a period their own member served.
  T3_OTHER_MEMBER_EXACT      exact name in a DIFFERENT member's office, or in a
                             member office whose member could not be resolved.
                             CANDIDATE ONLY: equally consistent with a namesake
                             and with the staffer having moved.
  T4A_VARIANT_OWN_MEMBER     a looser class (punctuation / compound surname /
                             nickname / first-name prefix / middle-name-as-first
                             / middle-initial conflict) matched in the staffer's
                             OWN member office.  Corroboration strength of T1,
                             name evidence weaker than T1.
  T4B_VARIANT_PERIOD_CORROBORATED
                             the same looser classes in a committee / leadership
                             / admin / member-organization office during a period
                             the staffer's own member served.  Corroboration
                             strength of T2.
  T5_WEAK_CANDIDATE          a looser class without corroboration, and every
                             FIRST_INITIAL_* class regardless.  CANDIDATE ONLY.
  NOT_FOUND                  no match in any source.

Tier precedence is T1 > T2 > T4A > T4B > T3 > T5: a corroborated variant is
stronger evidence than an uncorroborated exact name in someone else's office.
T4A and T4B both report status RESOLVED_T4; they are separate TIERS so that a
tie is never compared across two different corroboration strengths (A12).

TIES ARE NEVER BROKEN SILENTLY.  Every payroll identity a staffer's name reaches
is emitted.  When the best tier is supported by two or more DISTINCT payroll
identities the row carries ``ambiguous: true`` with its ``tie_size``, and the
tier is DEMOTED to a candidate tier -- T1/T2 -> CANDIDATE_T3 (exact-name
evidence that cannot be resolved to one payroll person), T4 -> CANDIDATE_T5.
A tie is never resolved by recency, row count, or any other tiebreak.

NOTHING HERE IS CANONICAL.  Every emitted row carries
``review_status: REVIEW_REQUIRED``, ``canonical_eligible: false``,
``canonical_employment_promoted: false`` and
``canonical_identity_decision: NOT_ADJUDICATED``; the receipt hash-binds every
input and pins ``canonical_employment_promotions`` and
``canonical_identity_promotions`` at zero.  A tier is a NAME-EVIDENCE grade, not
an employment finding and not an identity adjudication.

ASSUMPTIONS AND RESOLVED AMBIGUITIES
------------------------------------
Each of these is a place the adjudication left room.  Every one was settled by
measurement before a row was written, is declared in the receipt under ``dials``
and ``notes``, and is re-derived independently by
``verify_current_staffer_links.py``.

A1. PAYROLL IDENTITY -- THE TIE ATOM.  A payroll identity is
    ``(scope, surname, given, middle-initial group)`` where the scope is the
    MEMBER for a member office whose bioguide resolved, and the OFFICE
    otherwise.  Measured reason for the member scope: the Senate writes one
    senator's payroll under two office strings -- ``SENATOR <NAME>`` and
    ``INTERN COMPENSATION - <NAME>`` -- so an office-scoped atom counts one
    person under one senator as two identities and ties away 150 otherwise
    resolvable Senate staffers (RESOLVED 4,235 office-scoped vs 4,385
    member-scoped; House unchanged at 2,782 either way, because a House member
    office key IS ``HON:<bioguide>``).  That is a parsing artifact, not an
    identity hazard.  The office-scoped counterfactual is reported in the
    receipt under ``counts.tie_scope_counterfactual_office_scoped`` so the
    choice is auditable rather than buried.

A2. MIDDLE-INITIAL GROUPS make the tie test capable of firing at T1.  Within
    one scope+surname+given, rows are grouped by middle initial: zero or one
    distinct non-null initial collapses to ONE identity (``DALY, BRENDAN`` and
    ``DALY BRENDAN M`` are one person); two or more distinct non-null initials
    yield one identity per initial plus one for the no-initial rows.  Without
    this the T1 tie test would be true by construction -- a check that cannot
    fail is not a check (DE-011/DE-012).  It fires: 66 staffers are demoted out
    of T1 on it.

A3. T2-ELIGIBLE CONTAINERS are exactly the four the adjudication names --
    ``committee``, ``leadership``, ``admin``, ``member_organization``.  The
    House ledger also emits ``other`` (cloakroom, floor activities, House
    Information Resources) and ``vacant_seat``, which are non-member Hill
    offices too; admitting them is a one-staffer change (RESOLVED 4,385 -> 4,386)
    and is reported as ``counts.t2_container_counterfactual_wide`` rather than
    taken.

A4. HOUSE OFFICE FACTS ARE THE LEDGER'S.  ``office_key``, ``container_kind`` and
    ``member_bioguide`` are read from the House ledger, which resolved them
    under its own verified strict rule; measured over the 975,058 rows, all
    716,160 ``member_office`` rows carry a bioguide, all 1,023 member-office
    keys have the shape ``HON:<bioguide>``, and no office key carries two
    container kinds.  This lane must not contradict that resolution, so it does
    not re-derive it.

A5. SENATE OFFICE FACTS ARE DERIVED HERE, because the Senate candidate file
    carries neither.  ``container_kind`` comes from the office string by the
    same rule ``build_hill_personnel_spine.py`` applies; the member bioguide
    comes from a declared resolution ladder (A6).  The ladder is strict at every
    rung: exact folded surname, first-name form match, uniqueness.  No fuzzy
    join.

A6. THE MEMBER-OFFICE RESOLUTION LADDER, applied to Senate ``SENATOR <NAME>`` /
    ``INTERN COMPENSATION - <NAME>`` strings and to House ``HONRAW:`` strings
    the ledger declined to resolve.  In order: strip a trailing parenthetical
    state code; repair the Statement-of-Disbursements / Secretary-of-the-Senate
    OCR artifact that splits a leading letter off a surname (``-B ROWN``,
    ``BRIANS CHATZ``) but ONLY when the rejoined form is itself a roster
    surname; try compound surnames from the trailing 1..3 tokens; try EVERY
    non-surname token as the first-name candidate; restrict the roster pool to
    people who held a term in the office's OWN CHAMBER whose years intersect the
    office's observed years.  A rung is accepted only when it leaves exactly one
    roster person.  Chamber restriction is what separates the Senate's Tim
    Johnson from the House's Timothy Johnson and Bob Menendez from Rob Menendez.

A7. NAME PARSING.  Quorum display names are ``FIRST [MIDDLE...] LAST``, with a
    trailing particle run (``van``, ``de``, ``mc``, ...) folded into the
    surname.  House payee names are already split by the ledger's
    ``payee_parse``.  Senate payee names are ``LAST, FIRST [MIDDLE]`` in the
    comma form and ``FIRST [MIDDLE] LAST`` otherwise.  All comparisons run on
    NFKD-folded, ASCII-restricted, lowercased text; the COLLAPSED form (letters
    only) is what the surname index is keyed on, so a hyphen or apostrophe can
    never hide a name.  A defect this replaces: joining Senate surname tokens
    without collapsing left ``zahnle-hostetler`` unfindable and made 44 staffers
    look absent who are not.

A8. EXACT vs PUNCT_SUFFIX_VARIANT.  ``EXACT`` requires the folded surname and
    given name to agree INCLUDING punctuation and internal spacing;
    agreement only after collapsing is ``PUNCT_SUFFIX_VARIANT``, one of the
    looser classes, and therefore reaches T4 rather than T1/T2.  Both reach a
    RESOLVED status when corroborated, so the distinction costs a label, not a
    link.

A9. UNRESOLVED MEMBER OFFICES.  A member office whose bioguide did not resolve
    is ``member_office_unresolved``.  An exact match there is T3, never T1 (the
    office cannot be shown to be the staffer's own) and never T2 (it is a member
    office, not a committee).

A10. NO PERIOD FILTER ANYWHERE.  Recency is emitted as evidence
    (``period_first``, ``period_last``, ``period_count``) and never used to
    admit, reject, or rank a match.  The old rule's latest-quarter predicate is
    exactly the defect being repaired.

A12. T4 IS SPLIT BY CORROBORATION STRENGTH, SO TIES NEVER COMPARE ACROSS IT.
    T1 and T2 already separate own-member corroboration from
    member-service-period corroboration; the original T4 named both in ONE tier.
    Because the tie is counted among the matches carrying the best tier, that
    merge made T4 compare non-comparable evidence -- and only T4, since
    corroboration is constant within every other tier.  Measured on the first
    build: 11 staffers the old rule had LINKED came out CANDIDATE_T5 for exactly
    this reason.  Worked example, Patrick O'Connor (Henry Cuellar): one payroll
    identity in HON:C001063 -- his own member's office -- and one in COMMITTEE
    ON APPROPRIATIONS, same middle initial, overlapping quarters.  Both graded
    T4, so tie_size was 2 and the row was demoted, even though the own-member
    match is strictly the stronger evidence and is what the conclusion rests on.

    Paul's ruling, implemented here: split the tier rather than flatten it.
      * ``T4A_VARIANT_OWN_MEMBER``            -- a looser name class matched in
        the staffer's OWN member office.  Corroboration strength of T1, name
        evidence weaker than T1.
      * ``T4B_VARIANT_PERIOD_CORROBORATED``   -- a looser name class in a
        committee / leadership / admin / member-organization office during a
        period the staffer's own member served.  Corroboration strength of T2.
    Ties are then compared only within a corroboration strength, never across
    it, with no change to the tie rule itself.  Precedence keeps the brief's
    shape: T1 > T2 > T4A > T4B > T3 > T5.  The STATUS enum is unchanged -- both
    variant tiers report RESOLVED_T4 -- and T3 and T5 remain candidates that are
    never resolved.  ``counts.tie_grouping_counterfactual_merged_t4`` reports
    what the coarser single-T4 grouping would have produced.

A11. A MIDDLE INITIAL NARROWS A CLASS; IT NEVER DROPS A MATCH.  The adjudication
    asks for exact last+first "(+ middle initial when both sides have one)".
    Enforcing that as an admission filter DESTROYS evidence, because the Quorum
    directory's "middle" token is usually a maiden or compound surname rather
    than a middle name -- ``Amy Emerick Clerkin`` against payroll
    ``CLERKIN, AMY C``, ``Shelby Settles Harper`` against ``HARPER, SHELBY L``.
    Measured: an admission filter made 18 staffers whose names ARE on the
    payroll come out NOT_FOUND with zero emitted evidence, which is a silent
    break of the same kind the tie law forbids.  The rule applied instead: when
    both sides carry a middle initial and none of the staffer's middle-token
    initials matches the payroll's, an ``EXACT`` match is re-classed
    ``MIDDLE_INITIAL_CONFLICT`` -- a variant class, so it reaches T4 with
    corroboration and T5 without, and every match is still emitted with
    ``middle_initial_conflict: true`` and its pre-test class.

KNOWN RESIDUAL, MEASURED AND NOT PATCHED
----------------------------------------
The House ledger's ``payee_parse`` reads a no-comma CSV payee as
``LAST FIRST [MIDDLE]``.  498 rows / 52 distinct payroll people break that
convention with a single-letter given name and a full-word middle token, and the
break runs in BOTH directions: ``BOSSE, C. MELISSA`` and ``STEINBAUM V MATTHEW``
are ``LAST INITIAL FIRST``, while ``CHARLES P MEACHUM`` and ``NANCY G MATTHEWS``
are ``FIRST INITIAL LAST``.  Nothing in the row says which.  One current staffer
is affected (Matthew Steinbaum / Jerrold Nadler, HON:N000002 2026Q1, title
LEG ASSISTANT), and the old generation linked him only as an accident: its
``_name_tokens`` deletes the token ``V`` wherever it appears because ``V`` is in
its Roman-numeral suffix set, which silently rewrote ``STEINBAUM V MATTHEW`` to
``STEINBAUM MATTHEW``.  Resolving 52 ambiguous payroll people to recover one
link would be choosing a fix by proximity to the case last examined, so it is
reported rather than taken.  It belongs to the House ledger's parse lane.

``fec/staffer_network/intervals.py`` and ``schema_validation.py`` are the only
``fec`` modules this lane may import; this builder needs neither and imports no
``fec`` module at all, which keeps it import-side-effect free.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

STAGE_ID = "current-staffer-links-v2"
GLASSBOX_SOURCE = "current-staffer-links-v2"
GLASSBOX_SCRIPT = Path(r"C:\Users\pgoff\.claude\glassbox\emit.ps1")

LINK_SCHEMA = "staffer-network-current-staffer-link-v2"
CANDIDATE_SCHEMA = "staffer-network-current-staffer-match-candidate-v2"
RECEIPT_SCHEMA = "staffer-network-current-staffer-links-receipt-v2"

LINK_FILE = "current_staffer_links.ndjson.gz"
CANDIDATE_FILE = "current_staffer_match_candidates.ndjson.gz"
RECEIPT_FILE = "current_staffer_links_receipt.json"
PAYLOAD_FILES = (LINK_FILE, CANDIDATE_FILE)

DEFAULT_RULE_VERSION = "current-staffer-links-v2"
DEFAULT_RUN_ID = "run-20260902T143000000000Z-nameresolve"

CHAMBER_HOUSE = "house"
CHAMBER_SENATE = "senate"

EXPECTED_CURRENT_STAFFERS = 5773

# The old generation's measured baseline, carried so the receipt can state the
# delta against a denominator instead of a bare count.
OLD_BASELINE = {
    "LINKED": 1985,
    "MEMBER_UNRESOLVED": 138,
    "NAME_COLLISION": 0,
    "NOT_ON_PAYROLL": 3650,
}

# ---- dials.  UNTESTED DEFAULTS pending Paul's freeze. ----------------------
TIE_IDENTITY_SCOPE = "member_office_collapsed"   # see A1
T2_ELIGIBLE_CONTAINER_KINDS = ("admin", "committee", "leadership", "member_organization")
T2_CONTAINER_KINDS_WIDE = T2_ELIGIBLE_CONTAINER_KINDS + ("other", "vacant_seat")
MEMBER_RESOLUTION_MAX_SURNAME_TOKENS = 3
MEMBER_RESOLUTION_CHAMBER_RESTRICTED = True
MEMBER_RESOLUTION_REPAIR_LETTER_SPLIT = True

# ---- language law ----------------------------------------------------------
LANGUAGE_LAW_TOKENS = ("access", "causal", "friend", "ideolog", "influence", "predict")
VERBATIM_LEAF_NAMES = frozenset(
    {
        "display_name",
        "first",
        "last",
        "member_display",
        "office_key",
        "office_raw",
        "payroll_first",
        "payroll_identity_key",
        "payroll_last",
        "title_raw",
        "titles",
    }
)
VERBATIM_SOURCE_QUOTED_FIELDS = (
    "current_staffer_links.display_name",
    "current_staffer_links.display_name_key.first",
    "current_staffer_links.display_name_key.last",
    "current_staffer_links.matches[].office_key",
    "current_staffer_links.matches[].office_raw",
    "current_staffer_links.matches[].payroll_first",
    "current_staffer_links.matches[].payroll_identity_key",
    "current_staffer_links.matches[].payroll_last",
    "current_staffer_links.matches[].titles[]",
    "current_staffer_links.member_display",
    "current_staffer_links.title_raw",
    "current_staffer_match_candidates.display_name",
    "current_staffer_match_candidates.member_display",
    "current_staffer_match_candidates.office_key",
    "current_staffer_match_candidates.office_raw",
    "current_staffer_match_candidates.payroll_first",
    "current_staffer_match_candidates.payroll_identity_key",
    "current_staffer_match_candidates.payroll_last",
    "current_staffer_match_candidates.title_raw",
    "current_staffer_match_candidates.titles[]",
)
LANGUAGE_LAW_POLICY = (
    "Banned tokens are rejected in every field name, in every value this builder "
    "authors, and in all receipt prose. Values quoted verbatim from a source -- an "
    "official office string as printed, a job title, a person's own name -- are "
    "exempt and enumerated in verbatim_source_quoted_fields; their occurrences are "
    "counted and reported rather than edited, because editing the record would "
    "falsify it. The Senate office string OFFICE OF CONGRESSIONAL ACCESSIBILITY "
    "SERVICES is the largest single contributor and is a real office name."
)

TIER_T1 = "T1_OWN_MEMBER_EXACT"
TIER_T2 = "T2_NON_MEMBER_OFFICE_EXACT"
TIER_T3 = "T3_OTHER_MEMBER_EXACT"
TIER_T4A = "T4A_VARIANT_OWN_MEMBER"
TIER_T4B = "T4B_VARIANT_PERIOD_CORROBORATED"
TIER_T5 = "T5_WEAK_CANDIDATE"
TIER_PRECEDENCE = (TIER_T1, TIER_T2, TIER_T4A, TIER_T4B, TIER_T3, TIER_T5)
TIER_RANK = {tier: index for index, tier in enumerate(TIER_PRECEDENCE)}
# The STATUS enum the adjudication names is UNCHANGED: both variant tiers report
# RESOLVED_T4.  The split lives in the tier, which is the thing the tie is
# computed within (A12).
TIER_STATUS = {
    TIER_T1: "RESOLVED_T1",
    TIER_T2: "RESOLVED_T2",
    TIER_T4A: "RESOLVED_T4",
    TIER_T4B: "RESOLVED_T4",
    TIER_T3: "CANDIDATE_T3",
    TIER_T5: "CANDIDATE_T5",
}
RESOLVED_STATUSES = ("RESOLVED_T1", "RESOLVED_T2", "RESOLVED_T4")
TIE_DEMOTION = {
    TIER_T1: TIER_T3,
    TIER_T2: TIER_T3,
    TIER_T4A: TIER_T5,
    TIER_T4B: TIER_T5,
}
# The merged-T4 grouping the first build used, carried only so the receipt can
# report what the coarser grouping would have produced.
MERGED_T4_LABEL = "T4_VARIANT_CORROBORATED"
TIER_MERGED = {TIER_T4A: MERGED_T4_LABEL, TIER_T4B: MERGED_T4_LABEL}

CLASS_EXACT = "EXACT"
CLASS_PUNCT = "PUNCT_SUFFIX_VARIANT"
CLASS_MIDDLE_CONFLICT = "MIDDLE_INITIAL_CONFLICT"
CLASS_COMPOUND = "COMPOUND_SURNAME_VARIANT"
CLASS_NICKNAME = "NICKNAME_VARIANT"
CLASS_PREFIX = "FIRST_NAME_PREFIX"
CLASS_MIDDLE = "MIDDLE_NAME_AS_FIRST"
CLASS_INITIAL_ONLY = "FIRST_INITIAL_ONLY"
CLASS_INITIAL_SHARED = "FIRST_INITIAL_SHARED_LETTER"
CLASS_ORDER = (
    CLASS_EXACT,
    CLASS_PUNCT,
    CLASS_MIDDLE_CONFLICT,
    CLASS_COMPOUND,
    CLASS_NICKNAME,
    CLASS_PREFIX,
    CLASS_MIDDLE,
    CLASS_INITIAL_ONLY,
    CLASS_INITIAL_SHARED,
)
CLASS_RANK = {name: index for index, name in enumerate(CLASS_ORDER)}
EXACT_CLASSES = (CLASS_EXACT,)
VARIANT_CLASSES = (
    CLASS_PUNCT,
    CLASS_MIDDLE_CONFLICT,
    CLASS_COMPOUND,
    CLASS_NICKNAME,
    CLASS_PREFIX,
    CLASS_MIDDLE,
)
INITIAL_CLASSES = (CLASS_INITIAL_ONLY, CLASS_INITIAL_SHARED)

CORROBORATION_OWN_MEMBER = "OWN_MEMBER_OFFICE"
CORROBORATION_PERIOD = "MEMBER_SERVICE_PERIOD_OVERLAP"
CORROBORATION_NONE = "NONE"


class GateFailure(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Canonical IO
# ---------------------------------------------------------------------------
def compact(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_line(value: Any) -> bytes:
    return compact(value) + b"\n"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    path = Path(path)
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise GateFailure(f"object required at {path}:{line_number}")
            yield value


def write_ndjson_gz(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="\n") as text:
                    for value in values:
                        text.write(compact(value).decode("utf-8") + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_atomic(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(canonical_line(value))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Glassbox.  Never fatal, never recorded in the receipt: the receipt must stay
# byte-identical between a primary run and a twin that used --no-glassbox.
#
# GLASSBOX_STATUS is not free text.  ``emit.ps1`` declares
# ``[ValidateSet('queued','running','completed','failed','blocked','skipped',
# 'waiting','info')]`` on -Status, and PowerShell rejects the whole invocation
# for anything outside it.  The first build of this lane sent "ok"/"fail" on
# run.finish; every one was refused with exit code 1 while run.start ("running")
# was accepted, so the run opened in the glass box and NEVER CLOSED -- the
# same shape as a fan-out that reports coverage it does not have (DE-013).
# emit_glassbox swallows the failure by contract, which is why it hid: a silent
# False is indistinguishable from a disabled emitter.  It now writes the
# rejection to stderr, which is observable without entering the receipt.
# ---------------------------------------------------------------------------
GLASSBOX_STATUSES = frozenset(
    {"queued", "running", "completed", "failed", "blocked", "skipped", "waiting", "info"}
)


def emit_glassbox(
    enabled: bool,
    run_id: str,
    kind: str,
    status: str,
    summary: str,
    detail: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    if not enabled or not GLASSBOX_SCRIPT.is_file():
        return False
    if status not in GLASSBOX_STATUSES:
        print(
            f"glassbox: refusing to emit {kind} with status {status!r}; "
            f"emit.ps1 accepts only {sorted(GLASSBOX_STATUSES)}",
            file=sys.stderr,
        )
        return False
    command = [
        "powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy",
        "Bypass", "-File", str(GLASSBOX_SCRIPT),
        "-Lane", "claude", "-Kind", kind, "-Status", status, "-Summary", summary,
        "-Source", GLASSBOX_SOURCE, "-Stage", STAGE_ID, "-RunId", run_id, "-Quiet",
    ]
    if detail:
        command.extend(["-Detail", detail])
    if metadata:
        command.extend(["-MetadataJson", json.dumps(metadata, sort_keys=True)])
    try:
        completed = subprocess.run(  # noqa: S603
            command, capture_output=True, timeout=60, check=False
        )
    except Exception as error:  # pragma: no cover - environment dependent
        print(f"glassbox: {kind} emission raised {error}", file=sys.stderr)
        return False
    if completed.returncode != 0:
        print(
            f"glassbox: {kind} emission failed rc={completed.returncode}: "
            f"{completed.stderr.decode('utf-8', 'replace').strip()[:300]}",
            file=sys.stderr,
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Name normalization (A7)
# ---------------------------------------------------------------------------
NAME_SUFFIXES = frozenset(
    {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq", "dds", "jd", "dvm", "rn", "cpa"}
)
SURNAME_PARTICLES = frozenset(
    {
        "abu", "al", "bin", "da", "das", "de", "del", "dela", "della", "den", "der",
        "di", "dos", "du", "ibn", "la", "le", "mac", "mc", "saint", "st", "ten",
        "ter", "van", "vande", "vander", "von",
    }
)
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")


def fold(value: Any) -> str:
    """NFKD, drop combining marks, restrict to ASCII."""

    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.encode("ascii", "ignore").decode("ascii")


def name_tokens(value: Any) -> list[str]:
    out: list[str] = []
    for token in TOKEN_RE.findall(fold(value).lower()):
        trimmed = token.strip("-'")
        if trimmed:
            out.append(trimmed)
    return out


def collapse(value: Any) -> str:
    return "".join(ch for ch in fold(value).lower() if ch.isalnum())


def drop_suffixes(tokens: Sequence[str]) -> list[str]:
    out = list(tokens)
    while len(out) > 1 and out[-1] in NAME_SUFFIXES:
        out.pop()
    return out


def parse_display_name(value: Any) -> tuple[str, list[str], list[str]]:
    """``FIRST [MIDDLE...] LAST`` -> (first, middles, surname tokens)."""

    tokens = drop_suffixes(name_tokens(value))
    if not tokens:
        return "", [], []
    if len(tokens) == 1:
        return tokens[0], [], []
    first = tokens[0]
    surname = [tokens[-1]]
    index = len(tokens) - 2
    while index >= 1 and tokens[index] in SURNAME_PARTICLES:
        surname.insert(0, tokens[index])
        index -= 1
    return first, tokens[1:index + 1], surname


def parse_senate_payee(value: Any) -> tuple[list[str], str, str | None]:
    """``LAST, FIRST [MIDDLE]`` (comma form) or ``FIRST [MIDDLE] LAST``."""

    text = str(value or "")
    if "," in text:
        left, _, right = text.partition(",")
        surname = drop_suffixes(name_tokens(left))
        rest = drop_suffixes(name_tokens(right))
    else:
        tokens = drop_suffixes(name_tokens(text))
        if len(tokens) < 2:
            return [], "", None
        surname = [tokens[-1]]
        rest = tokens[:-1]
    if not surname or not rest:
        return [], "", None
    middle = None
    if len(rest) > 1:
        middle = collapse(rest[1])[:1] or None
    return surname, rest[0], middle


def house_payee_parts(parse: Mapping[str, Any]) -> tuple[list[str], str, str | None]:
    surname = drop_suffixes(name_tokens(parse.get("surname")))
    given_tokens = name_tokens(parse.get("given"))
    if not surname or not given_tokens:
        return [], "", None
    middle = collapse(parse.get("middle_initial"))[:1] or None
    if middle is None:
        middle_tokens = parse.get("middle_tokens") or []
        if middle_tokens:
            middle = collapse(middle_tokens[0])[:1] or None
    return surname, given_tokens[0], middle


def surname_forms(tokens: Sequence[str]) -> tuple[str, str, str]:
    """(raw joined, collapsed, collapsed last token)."""

    raw = " ".join(tokens)
    return raw, collapse(raw), collapse(tokens[-1]) if tokens else ""


# ---------------------------------------------------------------------------
# Nickname table.  A short form with more than one formal form is DROPPED, not
# collapsed: folding `al` onto both `alan` and `albert` would let one name match
# two different people, which is the fuzzy join this lane forbids.
# ---------------------------------------------------------------------------
NICKNAME_TABLE_SCHEMA_ID = "staffer-network-first-name-nickname-table-v1"


def load_nickname_table(path: Path | None) -> tuple[dict[str, str], dict[str, frozenset[str]], dict[str, int]]:
    canonical: dict[str, str] = {}
    stats = {"entries_read": 0, "entries_single_formal": 0, "entries_dropped_multi_formal": 0}
    if path is not None and Path(path).is_file():
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        entries = payload.get("entries") if isinstance(payload, Mapping) else None
        if not isinstance(entries, Mapping):
            entries = payload if isinstance(payload, Mapping) else {}
        for short, formal in entries.items():
            if not isinstance(short, str):
                continue
            stats["entries_read"] += 1
            if isinstance(formal, str):
                forms = [formal]
            elif isinstance(formal, list):
                forms = [item for item in formal if isinstance(item, str)]
            else:
                continue
            if len(forms) != 1:
                stats["entries_dropped_multi_formal"] += 1
                continue
            key, value = collapse(short), collapse(forms[0])
            if not key or not value:
                continue
            canonical[key] = value
            stats["entries_single_formal"] += 1
    groups: defaultdict[str, set[str]] = defaultdict(set)
    for short, formal in canonical.items():
        groups[short].add(formal)
        groups[formal].add(short)
    for formal in list(groups):
        for member in list(groups[formal]):
            groups[member] |= groups[formal] - {member}
    return canonical, {k: frozenset(v) for k, v in groups.items()}, stats


def normalize_first(value: Any, table: Mapping[str, str]) -> str:
    key = collapse(value)
    return table.get(key, key)


def nickname_related(left: str, right: str, groups: Mapping[str, frozenset[str]]) -> bool:
    if not left or not right or left == right:
        return False
    return right in groups.get(left, frozenset()) or left in groups.get(right, frozenset())


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
ROSTER_FILES = ("legislators-current.yaml", "legislators-historical.yaml")


def load_roster(directory: Path | None) -> list[dict[str, Any]]:
    people: list[dict[str, Any]] = []
    if directory is None:
        return people
    directory = Path(directory)
    for filename in ROSTER_FILES:
        path = directory / filename
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as stream:
            payload = yaml.safe_load(stream) or []
        for person in payload:
            bioguide = ((person or {}).get("id") or {}).get("bioguide")
            if not isinstance(bioguide, str) or not bioguide:
                continue
            name = person.get("name") or {}
            terms: list[tuple[str, str, str]] = []
            for term in person.get("terms") or []:
                start = str(term.get("start", ""))[:10]
                end = str(term.get("end", ""))[:10]
                kind = str(term.get("type", ""))
                if len(start) == 10 and len(end) == 10:
                    terms.append((start, end, kind))
            if not terms:
                continue
            terms.sort()
            people.append(
                {
                    "bioguide": bioguide,
                    "first": str(name.get("first", "") or ""),
                    "middle": str(name.get("middle", "") or ""),
                    "nickname": str(name.get("nickname", "") or ""),
                    "official_full": str(name.get("official_full", "") or ""),
                    "last": str(name.get("last", "") or ""),
                    "terms": terms,
                    "chambers": frozenset(kind for _s, _e, kind in terms),
                    "min_year": min(int(s[:4]) for s, _e, _k in terms),
                    "max_year": max(int(e[:4]) for _s, e, _k in terms),
                    "current": filename == ROSTER_FILES[0],
                }
            )
    people.sort(key=lambda item: item["bioguide"])
    return people


def first_name_forms(person: Mapping[str, Any], table: Mapping[str, str]) -> frozenset[str]:
    forms = {normalize_first(person["first"], table)}
    if person["nickname"]:
        forms.add(normalize_first(person["nickname"], table))
    if person["middle"]:
        forms.add(normalize_first(person["middle"], table))
    for token in name_tokens(person["official_full"]):
        forms.add(normalize_first(token, table))
    forms.discard("")
    return frozenset(forms)


class RosterIndex:
    def __init__(self, people: Sequence[Mapping[str, Any]], nicknames: Mapping[str, str]) -> None:
        self.people = list(people)
        self.by_bioguide = {person["bioguide"]: person for person in self.people}
        self.by_surname: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
        self.forms: dict[str, frozenset[str]] = {}
        for person in self.people:
            self.by_surname[collapse(person["last"])].append(person)
            self.forms[person["bioguide"]] = first_name_forms(person, nicknames)
        self.surname_keys = frozenset(self.by_surname)
        self.nicknames = dict(nicknames)

    def terms(self, bioguide: str | None) -> Sequence[tuple[str, str, str]]:
        person = self.by_bioguide.get(bioguide or "")
        return person["terms"] if person else ()


PAREN_RE = re.compile(r"\s*\([^)]*\)\s*$")


def letter_split_repairs(tokens: Sequence[str], roster: RosterIndex) -> list[list[str]]:
    """The Statement-of-Disbursements / Secretary-of-the-Senate OCR artifact that
    moves the boundary between a given name and a surname by one or two letters:
    ``-B ROWN`` (BROWN), ``BRIANS CHATZ`` (BRIAN SCHATZ), ``JOHN NK ENNEDY``
    (JOHN N KENNEDY), ``BENJAMIN LC ARDIN`` (BENJAMIN L CARDIN), ``J.TOOMEY``
    (J TOOMEY).

    The repair re-splits the last token, and the last two tokens joined, at every
    position whose TAIL is a surname the roster actually carries -- so it can
    never invent a name.  Every candidate it returns still has to clear the same
    strict uniqueness rungs as an unrepaired one; this widens the surface the
    ladder is offered, never the standard it applies.
    """

    if not MEMBER_RESOLUTION_REPAIR_LETTER_SPLIT or not tokens:
        return []
    out: list[list[str]] = []
    seen: set[tuple[str, ...]] = {tuple(tokens)}

    def offer(head: str, tail: str, prefix: Sequence[str]) -> None:
        # A three-letter floor keeps the re-split from finding a degenerate tail
        # such as "o" or "ee"; the shortest surnames the roster actually carries
        # (LEE, KIM) are three.
        if len(tail) < 3 or tail not in roster.surname_keys:
            return
        rebuilt = [item for item in prefix if item]
        if head:
            rebuilt.append(head)
        rebuilt.append(tail)
        key = tuple(rebuilt)
        if key not in seen:
            seen.add(key)
            out.append(rebuilt)

    last = collapse(tokens[-1])
    for split in range(1, len(last)):
        offer(last[:split], last[split:], tokens[:-1])
    if len(tokens) >= 2:
        joined = collapse(tokens[-2] + tokens[-1])
        for split in range(0, len(joined)):
            offer(joined[:split], joined[split:], tokens[:-2])
    return out


def resolve_office_member(
    office_tokens: Sequence[str],
    roster: RosterIndex,
    chamber: str | None,
    year_low: int | None,
    year_high: int | None,
) -> tuple[str | None, str]:
    """The A6 ladder.  Returns (bioguide, method).  Strict at every rung: a rung
    is accepted only when it leaves exactly one roster person."""

    tokens = [token for token in office_tokens if token]
    if not tokens:
        return None, "UNRESOLVED_OFFICE_NAME_NOT_PARSED"
    term_kind = {CHAMBER_HOUSE: "rep", CHAMBER_SENATE: "sen"}.get(chamber or "")

    def pool_for(surname_key: str) -> list[Mapping[str, Any]]:
        pool = list(roster.by_surname.get(surname_key, ()))
        if MEMBER_RESOLUTION_CHAMBER_RESTRICTED and term_kind:
            narrowed = [p for p in pool if term_kind in p["chambers"]]
            if narrowed:
                pool = narrowed
        if year_low is not None and year_high is not None:
            narrowed = [
                p for p in pool if p["min_year"] <= year_high and p["max_year"] >= year_low
            ]
            if narrowed:
                pool = narrowed
        return pool

    def attempt(tokens_in: Sequence[str]) -> tuple[str | None, str] | None:
        """None = this token list reached no roster surname at all."""

        reached = None
        width_cap = min(MEMBER_RESOLUTION_MAX_SURNAME_TOKENS, len(tokens_in))
        for width in range(width_cap, 0, -1):
            surname_key = collapse("".join(tokens_in[-width:]))
            if not surname_key:
                continue
            pool = pool_for(surname_key)
            if not pool:
                continue
            given_tokens = [item for item in tokens_in[: len(tokens_in) - width] if item]
            if not given_tokens:
                if len(pool) == 1:
                    return pool[0]["bioguide"], "UNIQUE_SURNAME_NO_FIRST_NAME"
                reached = reached or (None, "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME")
                continue
            ambiguous = False
            for given in given_tokens:
                target = normalize_first(given, roster.nicknames)
                if len(target) < 2:
                    continue
                hits = [p for p in pool if target in roster.forms[p["bioguide"]]]
                if len(hits) == 1:
                    return hits[0]["bioguide"], "SURNAME_AND_FIRST_NAME_FORM"
                if len(hits) > 1:
                    ambiguous = True
            for given in given_tokens:
                initial = collapse(given)[:1]
                if not initial:
                    continue
                hits = [
                    p
                    for p in pool
                    if any(form.startswith(initial) for form in roster.forms[p["bioguide"]])
                ]
                if len(hits) == 1:
                    return hits[0]["bioguide"], "SURNAME_AND_FIRST_INITIAL"
            if len(pool) == 1:
                return pool[0]["bioguide"], "UNIQUE_SURNAME_FIRST_NAME_NOT_MATCHED"
            reached = reached or (
                None,
                "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"
                if ambiguous
                else "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER",
            )
        return reached

    outcome = attempt(tokens)
    if outcome is not None and outcome[0] is not None:
        return outcome
    for repaired in letter_split_repairs(tokens, roster):
        healed = attempt(repaired)
        if healed is not None and healed[0] is not None:
            return healed[0], healed[1] + "_AFTER_LETTER_SPLIT_REPAIR"
    if outcome is not None:
        return outcome
    return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"


def resolve_quorum_member(
    member_display: str, roster: RosterIndex
) -> tuple[str | None, str]:
    """The Quorum member display name is ``FIRST [MIDDLE...] LAST``; every one of
    the 533 is a sitting member, so the current roster is tried first."""

    first, middles, surname = parse_display_name(member_display)
    if not surname:
        return None, "UNRESOLVED_MEMBER_NAME_NOT_PARSED"
    year = date.today().year
    for surname_tokens in _surname_candidates(middles, surname):
        tokens = [first] + list(surname_tokens)
        bioguide, method = resolve_office_member(tokens, roster, None, 2025, max(2026, year))
        if bioguide is not None:
            return bioguide, method
    for surname_tokens in _surname_candidates(middles, surname):
        key = collapse("".join(surname_tokens))
        pool = [p for p in roster.by_surname.get(key, ()) if p["current"]]
        if len(pool) == 1:
            return pool[0]["bioguide"], "UNIQUE_CURRENT_ROSTER_SURNAME"
    return None, "UNRESOLVED_MEMBER"


def _surname_candidates(middles: Sequence[str], surname: Sequence[str]) -> list[list[str]]:
    """`April McClain Delaney` -- the Quorum parse calls `McClain` a middle name;
    a compound surname is tried by walking middles back into the surname."""

    out = [list(surname)]
    for width in range(1, len(middles) + 1):
        out.append(list(middles[len(middles) - width:]) + list(surname))
    return out


# ---------------------------------------------------------------------------
# Senate office facts (A5)
# ---------------------------------------------------------------------------
SENATE_SUFFIX_RE = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
SENATOR_RE = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_RE = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
SENATE_LEADERSHIP_PHRASES = (
    "CAUCUS", "MAJORITY CONFERENCE", "MAJORITY LEADER", "MAJORITY WHIP",
    "MINORITY CONFERENCE", "MINORITY LEADER", "MINORITY WHIP", "PRES PRO TEM",
    "PRESIDENT PRO TEMPORE", "SECRETARY FOR THE MAJORITY",
    "SECRETARY FOR THE MINORITY", "VICE PRESIDENT",
)


def senate_office_key(office_raw: Any) -> str:
    value = str(office_raw or "").replace("\u2019", "'").strip()
    return re.sub(r"\s+", " ", value).upper()


def senate_container_kind(office_key: str) -> str:
    upper = (office_key or "").strip().upper()
    if not upper:
        return "unresolved"
    if SENATOR_RE.match(upper) or INTERN_RE.match(upper):
        return "member_office"
    if "COMMITTEE" in upper or upper == "APPROPRIATIONS":
        return "committee"
    for phrase in SENATE_LEADERSHIP_PHRASES:
        if phrase in upper:
            return "leadership"
    return "admin"


def _office_name_tokens(remainder: str) -> list[str]:
    """Single-letter tokens are KEPT: ``R SCOTT`` and ``T SCOTT`` are the only
    thing separating Rick Scott from Tim Scott in the Senate intern pools, and
    ``J. GRESHAM BARRETT``'s initial is what the ladder falls back to."""

    cleaned = PAREN_RE.sub("", remainder or "").strip()
    cleaned = SENATE_SUFFIX_RE.sub("", cleaned).strip()
    out: list[str] = []
    for item in cleaned.split():
        token = collapse(item)
        if token and token not in NAME_SUFFIXES:
            out.append(token)
    return out


def senate_office_name_tokens(office_key: str) -> list[str]:
    upper = (office_key or "").strip().upper()
    match = SENATOR_RE.match(upper) or INTERN_RE.match(upper)
    if match:
        return _office_name_tokens(match.group(1))
    return []


HONRAW_RE = re.compile(r"^HONRAW:HON\.?\s*(.+)$", re.IGNORECASE)


def house_honraw_name_tokens(office_key: str) -> list[str]:
    match = HONRAW_RE.match(office_key or "")
    if not match:
        return []
    return _office_name_tokens(match.group(1))


# ---------------------------------------------------------------------------
# Reporting periods (evidence only -- never a filter, A10)
# ---------------------------------------------------------------------------
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")
ISO_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def period_bounds(chamber: str, token: str) -> tuple[str, str] | None:
    if chamber == CHAMBER_HOUSE:
        match = QUARTER_RE.match(str(token or "").strip().upper())
        if not match:
            return None
        year, quarter = int(match.group(1)), int(match.group(2))
        start = f"{year:04d}-{3 * quarter - 2:02d}-01"
        if quarter == 4:
            return start, f"{year:04d}-12-31"
        end_month = 3 * quarter
        end_day = 30 if end_month in (4, 6, 9, 11) else 31
        if end_month == 3:
            end_day = 31
        return start, f"{year:04d}-{end_month:02d}-{end_day:02d}"
    match = ISO_RE.match(str(token or "").strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if month >= 10:
        return f"{year:04d}-10-01", f"{year + 1:04d}-03-31"
    if month <= 3:
        return f"{year - 1:04d}-10-01", f"{year:04d}-03-31"
    return f"{year:04d}-04-01", f"{year:04d}-09-30"


def periods_overlap_service(
    chamber: str, periods: Sequence[str], terms: Sequence[tuple[str, str, str]]
) -> bool:
    if not terms:
        return False
    for period in periods:
        bounds = period_bounds(chamber, period)
        if bounds is None:
            continue
        start, end = bounds
        for term_start, term_end, _kind in terms:
            if start <= term_end and end >= term_start:
                return True
    return False


def period_year(token: str) -> int | None:
    text = str(token or "")
    return int(text[:4]) if len(text) >= 4 and text[:4].isdigit() else None


# ---------------------------------------------------------------------------
# Payroll aggregation
# ---------------------------------------------------------------------------
class PayrollScan:
    """Streams both sources once, keeping only rows whose surname can reach a
    staffer.  The surname index is keyed on BOTH the collapsed full surname and
    its collapsed last token, so a compound payroll surname is reachable from a
    single-token staffer surname and vice versa."""

    def __init__(self, surname_keys: frozenset[str]) -> None:
        self.surname_keys = surname_keys
        self.groups: dict[tuple[str, str, str, str], dict[str | None, dict[str, Any]]] = {}
        self.office_meta: dict[tuple[str, str], dict[str, Any]] = {}
        self.counts: Counter = Counter()

    def _admit(
        self,
        chamber: str,
        office_key: str,
        surname_tokens: Sequence[str],
        given: str,
        middle: str | None,
        period: str | None,
        title: str | None,
    ) -> None:
        raw_surname, collapsed, last_token = surname_forms(surname_tokens)
        if collapsed not in self.surname_keys and last_token not in self.surname_keys:
            return
        self.counts[f"{chamber}_rows_reaching_a_staffer_surname"] += 1
        key = (chamber, office_key, raw_surname, fold(given).lower())
        bucket = self.groups.setdefault(key, {})
        entry = bucket.get(middle)
        if entry is None:
            entry = bucket[middle] = {"periods": set(), "titles": Counter(), "rows": 0}
        if period:
            entry["periods"].add(str(period))
        if title:
            entry["titles"][str(title)] += 1
        entry["rows"] += 1

    def _office(self, chamber: str, office_key: str, office_raw: Any, facts: Mapping[str, Any]) -> None:
        meta = self.office_meta.get((chamber, office_key))
        raw = str(office_raw or "")
        if meta is None:
            meta = self.office_meta[(chamber, office_key)] = {
                "container_kind": facts.get("container_kind"),
                "ledger_member_bioguide": facts.get("member_bioguide"),
                "office_raw": raw,
                "periods": set(),
                "rows": 0,
            }
        elif raw and (not meta["office_raw"] or raw < meta["office_raw"]):
            # The lexicographically smallest raw string observed for the key, so
            # the emitted example is a function of the input set rather than of
            # the order the stream happened to present it in.
            meta["office_raw"] = raw
        meta["rows"] += 1
        period = facts.get("period")
        if period:
            meta["periods"].add(str(period))

    def scan_house(self, path: Path) -> None:
        for row in read_rows(path):
            self.counts["house_rows"] += 1
            office_key = row.get("office_key")
            if not isinstance(office_key, str) or not office_key:
                self.counts["house_rows_without_office_key"] += 1
                continue
            self._office(
                CHAMBER_HOUSE,
                office_key,
                row.get("office_raw"),
                {
                    "container_kind": row.get("container_kind"),
                    "member_bioguide": row.get("member_bioguide"),
                    "period": row.get("quarter"),
                },
            )
            surname, given, middle = house_payee_parts(row.get("payee_parse") or {})
            if not surname or not given:
                self.counts["house_rows_without_a_parsed_payee"] += 1
                continue
            self._admit(
                CHAMBER_HOUSE, office_key, surname, given, middle,
                row.get("quarter"), row.get("title_raw"),
            )

    def scan_senate(self, path: Path) -> None:
        for row in read_rows(path):
            self.counts["senate_rows"] += 1
            office_key = senate_office_key(row.get("office_raw"))
            if not office_key:
                self.counts["senate_rows_without_office_key"] += 1
                continue
            self._office(
                CHAMBER_SENATE,
                office_key,
                row.get("office_raw"),
                {
                    "container_kind": senate_container_kind(office_key),
                    "member_bioguide": None,
                    "period": row.get("report_period_start"),
                },
            )
            surname, given, middle = parse_senate_payee(row.get("payee_name_raw"))
            if not surname or not given:
                self.counts["senate_rows_without_a_parsed_payee"] += 1
                continue
            self._admit(
                CHAMBER_SENATE, office_key, surname, given, middle,
                row.get("report_period_start"),
                row.get("title_candidate") or row.get("title_raw"),
            )


def split_identities(bucket: Mapping[str | None, Mapping[str, Any]]) -> list[dict[str, Any]]:
    """A2.  Middle-initial grouping inside one scope+surname+given."""

    non_null = sorted(key for key in bucket if key)
    if len(non_null) <= 1:
        merged = {
            "middle_initial": non_null[0] if non_null else None,
            "periods": set(),
            "titles": Counter(),
            "rows": 0,
        }
        for entry in bucket.values():
            merged["periods"] |= set(entry["periods"])
            merged["titles"] += Counter(entry["titles"])
            merged["rows"] += entry["rows"]
        return [merged]
    out = []
    for key in non_null:
        entry = bucket[key]
        out.append(
            {
                "middle_initial": key,
                "periods": set(entry["periods"]),
                "titles": Counter(entry["titles"]),
                "rows": entry["rows"],
            }
        )
    if None in bucket:
        entry = bucket[None]
        out.append(
            {
                "middle_initial": None,
                "periods": set(entry["periods"]),
                "titles": Counter(entry["titles"]),
                "rows": entry["rows"],
            }
        )
    return out


# ---------------------------------------------------------------------------
# Classification (A8)
# ---------------------------------------------------------------------------
def classify_match(
    staffer: Mapping[str, Any],
    payroll_surname_raw: str,
    payroll_given_raw: str,
    nickname_groups: Mapping[str, frozenset[str]],
) -> str | None:
    payroll_last_c = collapse(payroll_surname_raw)
    payroll_last_token_c = collapse(name_tokens(payroll_surname_raw)[-1]) if payroll_surname_raw else ""
    payroll_first_c = collapse(payroll_given_raw)
    staff_last_raw = staffer["surname_raw"]
    staff_last_c = staffer["surname_collapsed"]
    staff_last_token_c = staffer["surname_last_token"]
    staff_first_raw = staffer["first_raw"]
    staff_first_c = staffer["first_collapsed"]

    last_exact = bool(payroll_surname_raw) and payroll_surname_raw == staff_last_raw
    last_punct = bool(payroll_last_c) and payroll_last_c == staff_last_c
    last_token = bool(payroll_last_c) and payroll_last_c != staff_last_c and (
        payroll_last_c == staff_last_token_c
        or payroll_last_token_c == staff_last_c
        or payroll_last_token_c == staff_last_token_c
        or (staff_last_token_c and payroll_last_c.endswith(staff_last_token_c))
        or (payroll_last_token_c and staff_last_c.endswith(payroll_last_token_c))
    )
    if not (last_exact or last_punct or last_token):
        return None
    first_exact = bool(payroll_given_raw) and payroll_given_raw == staff_first_raw
    first_punct = bool(payroll_first_c) and payroll_first_c == staff_first_c
    if last_exact and first_exact:
        return CLASS_EXACT
    if (last_exact or last_punct) and (first_exact or first_punct):
        return CLASS_PUNCT
    if last_token and (first_exact or first_punct):
        return CLASS_COMPOUND
    if nickname_related(payroll_first_c, staff_first_c, nickname_groups):
        return CLASS_NICKNAME
    if (
        payroll_first_c
        and staff_first_c
        and len(payroll_first_c) >= 2
        and len(staff_first_c) >= 2
        and payroll_first_c != staff_first_c
        and (payroll_first_c.startswith(staff_first_c) or staff_first_c.startswith(payroll_first_c))
    ):
        return CLASS_PREFIX
    if payroll_first_c and payroll_first_c in staffer["middles_collapsed"]:
        return CLASS_MIDDLE
    if (
        payroll_first_c
        and staff_first_c
        and payroll_first_c[0] == staff_first_c[0]
        and (len(payroll_first_c) == 1 or len(staff_first_c) == 1)
    ):
        return CLASS_INITIAL_ONLY
    if payroll_first_c and staff_first_c and payroll_first_c[0] == staff_first_c[0]:
        return CLASS_INITIAL_SHARED
    return None


def assign_tier(
    match_class: str,
    container_kind: str,
    office_bioguide: str | None,
    own_bioguide: str | None,
    chamber: str,
    periods: Sequence[str],
    own_terms: Sequence[tuple[str, str, str]],
    t2_kinds: Sequence[str],
) -> tuple[str, str]:
    own_office = (
        container_kind == "member_office"
        and bool(office_bioguide)
        and bool(own_bioguide)
        and office_bioguide == own_bioguide
    )
    period_corroborated = (
        container_kind in t2_kinds
        and bool(own_bioguide)
        and periods_overlap_service(chamber, periods, own_terms)
    )
    if match_class in EXACT_CLASSES:
        if own_office:
            return TIER_T1, CORROBORATION_OWN_MEMBER
        if period_corroborated:
            return TIER_T2, CORROBORATION_PERIOD
        if container_kind in ("member_office", "member_office_unresolved"):
            return TIER_T3, CORROBORATION_NONE
        return TIER_T5, CORROBORATION_NONE
    if match_class in VARIANT_CLASSES:
        if own_office:
            return TIER_T4A, CORROBORATION_OWN_MEMBER
        if period_corroborated:
            return TIER_T4B, CORROBORATION_PERIOD
        return TIER_T5, CORROBORATION_NONE
    return TIER_T5, CORROBORATION_NONE


# ---------------------------------------------------------------------------
# Tripwire + language law
# ---------------------------------------------------------------------------
UNPROMOTED_ALLOWED = (False, 0, None, "", "NOT_ADJUDICATED")


def assert_unpromoted(rows: Sequence[Mapping[str, Any]], label: str) -> list[str]:
    failures: list[str] = []
    for index, row in enumerate(rows):
        if row.get("review_status") != "REVIEW_REQUIRED":
            failures.append(f"{label} row {index}: review_status is not REVIEW_REQUIRED")
        if row.get("canonical_eligible") is not False:
            failures.append(f"{label} row {index}: canonical_eligible is not false")
        if row.get("canonical_employment_promoted") is not False:
            failures.append(f"{label} row {index}: canonical_employment_promoted is not false")
        if row.get("canonical_identity_decision") != "NOT_ADJUDICATED":
            failures.append(
                f"{label} row {index}: canonical_identity_decision is not NOT_ADJUDICATED"
            )
        for key, value in row.items():
            lowered = key.lower()
            if (
                "promoted" in lowered or "canonical" in lowered or "eligible" in lowered
            ) and value not in UNPROMOTED_ALLOWED:
                failures.append(f"{label} row {index}: promotion-shaped field {key} is truthy")
        if len(failures) > 50:
            failures.append("... truncated")
            return failures
    return failures


def scan_language_law(payload: Any) -> tuple[list[str], Counter]:
    authored: list[str] = []
    verbatim: Counter = Counter()

    def walk(node: Any, key: str | None, exempt: bool) -> None:
        if isinstance(node, Mapping):
            for child_key, child in node.items():
                lowered = str(child_key).casefold()
                for token in LANGUAGE_LAW_TOKENS:
                    if token in lowered:
                        authored.append(f"field_name:{child_key}:{token}")
                walk(child, str(child_key), exempt or str(child_key) in VERBATIM_LEAF_NAMES)
        elif isinstance(node, list):
            for child in node:
                walk(child, key, exempt)
        elif isinstance(node, str):
            lowered = node.casefold()
            for token in LANGUAGE_LAW_TOKENS:
                if token in lowered:
                    if exempt:
                        verbatim[f"{key}|{token}"] += 1
                    else:
                        authored.append(f"value:{key}:{token}")

    walk(payload, None, False)
    return authored, verbatim


# ---------------------------------------------------------------------------
# Input binding
# ---------------------------------------------------------------------------
def bind_input(label: str, path: Path | None, block: dict[str, Any], count_rows: bool = False) -> Path | None:
    if path is None:
        block[label] = {"path": None, "present": False, "bytes": None, "rows": None, "sha256": None}
        return None
    path = Path(path)
    try:
        relative = str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        relative = str(path)
    if not path.is_file():
        block[label] = {"path": relative, "present": False, "bytes": None, "rows": None, "sha256": None}
        return None
    rows = sum(1 for _ in read_rows(path)) if count_rows else None
    block[label] = {
        "path": relative,
        "present": True,
        "bytes": path.stat().st_size,
        "rows": rows,
        "sha256": sha(path),
    }
    return path


def load_staff_directory(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise GateFailure("staff directory is not an object")
    entries: list[dict[str, Any]] = []
    for member_display in sorted(payload):
        staff = payload.get(member_display)
        if not isinstance(staff, list):
            continue
        for entry in staff:
            if not isinstance(entry, Mapping):
                continue
            staff_id = entry.get("id")
            name = entry.get("n")
            if staff_id is None or not isinstance(name, str) or not name.strip():
                continue
            title = entry.get("t")
            entries.append(
                {
                    "member_display": str(member_display),
                    "quorum_staff_id": str(staff_id).strip(),
                    "display_name": name.strip(),
                    "title_raw": re.sub(r"\s+", " ", str(title)).strip() if title else None,
                }
            )
    entries.sort(key=lambda item: (item["member_display"], item["display_name"], item["quorum_staff_id"]))
    return entries


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise GateFailure(
            f"immutable generation: refusing to write into non-empty {output_root}"
        )
    rule_version = args.rule_version
    inputs: dict[str, Any] = {}

    staff_path = bind_input("staff_directory", args.staff_directory, inputs)
    house_path = bind_input("house_personnel_observations", args.house_observations, inputs)
    senate_path = bind_input("senate_payroll_candidates", args.senate_candidates, inputs)
    nickname_path = bind_input("nickname_table", args.nickname_table, inputs)
    roster_dir = Path(args.roster_dir) if args.roster_dir else None
    for filename in ROSTER_FILES:
        bind_input(f"roster:{filename}", roster_dir / filename if roster_dir else None, inputs)

    if staff_path is None:
        raise GateFailure("STAFF_DIRECTORY_ABSENT")
    if house_path is None and senate_path is None:
        raise GateFailure("NO_PAYROLL_SOURCE_PRESENT")

    nicknames, nickname_groups, nickname_stats = load_nickname_table(nickname_path)
    roster = RosterIndex(load_roster(roster_dir), nicknames)
    if not roster.people:
        raise GateFailure("ROSTER_ABSENT")

    # ---- staffers ---------------------------------------------------------
    entries = load_staff_directory(staff_path)
    member_resolution: dict[str, tuple[str | None, str]] = {}
    for member_display in sorted({entry["member_display"] for entry in entries}):
        member_resolution[member_display] = resolve_quorum_member(member_display, roster)

    staffers: list[dict[str, Any]] = []
    for entry in entries:
        first, middles, surname = parse_display_name(entry["display_name"])
        raw_surname, collapsed, last_token = surname_forms(surname)
        bioguide, method = member_resolution[entry["member_display"]]
        staffers.append(
            {
                **entry,
                "first_raw": fold(first).lower(),
                "first_collapsed": collapse(first),
                "middles_collapsed": frozenset(collapse(item) for item in middles if collapse(item)),
                "middle_initial": (collapse(middles[0])[:1] or None) if middles else None,
                "middle_initials": frozenset(
                    collapse(item)[:1] for item in middles if collapse(item)
                ),
                "surname_raw": raw_surname,
                "surname_collapsed": collapsed,
                "surname_last_token": last_token,
                "member_bioguide": bioguide,
                "member_resolution_method": method,
                "member_terms": roster.terms(bioguide),
            }
        )
    if len(staffers) != EXPECTED_CURRENT_STAFFERS:
        # Not fatal -- the measured denominator is what the receipt divides by --
        # but it is reported so a silent directory change cannot pass unnoticed.
        pass

    surname_keys = set()
    for staffer in staffers:
        if staffer["surname_collapsed"]:
            surname_keys.add(staffer["surname_collapsed"])
        if staffer["surname_last_token"]:
            surname_keys.add(staffer["surname_last_token"])

    # ---- payroll ----------------------------------------------------------
    scan = PayrollScan(frozenset(surname_keys))
    if house_path is not None:
        scan.scan_house(house_path)
    if senate_path is not None:
        scan.scan_senate(senate_path)

    # ---- office facts -----------------------------------------------------
    office_resolution: Counter = Counter()
    offices: dict[tuple[str, str], dict[str, Any]] = {}
    for (chamber, office_key), meta in sorted(scan.office_meta.items()):
        container_kind = meta["container_kind"] or "unresolved"
        bioguide = meta["ledger_member_bioguide"]
        method = "HOUSE_LEDGER" if bioguide else None
        # The House ledger labels a member office it could not resolve
        # `member_office_unresolved`; that is an ABSENCE, not a contrary
        # assertion, so the ladder is offered it.  A member office the ledger DID
        # resolve is never re-derived (A4).
        if container_kind in ("member_office", "member_office_unresolved") and not bioguide:
            years = [period_year(item) for item in meta["periods"]]
            years = [year for year in years if year is not None]
            low, high = (min(years), max(years)) if years else (None, None)
            tokens = (
                senate_office_name_tokens(office_key)
                if chamber == CHAMBER_SENATE
                else house_honraw_name_tokens(office_key)
            )
            bioguide, method = resolve_office_member(tokens, roster, chamber, low, high)
            container_kind = "member_office" if bioguide else "member_office_unresolved"
        office_resolution[f"{chamber}:{method or 'NONE'}"] += 1
        offices[(chamber, office_key)] = {
            "container_kind": container_kind,
            "member_bioguide": bioguide,
            "member_resolution_method": method,
            "office_raw": meta["office_raw"],
        }

    # ---- match ------------------------------------------------------------
    index: defaultdict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for key in scan.groups:
        _chamber, _office_key, surname_raw, _given = key
        collapsed = collapse(surname_raw)
        tokens = name_tokens(surname_raw)
        last_token = collapse(tokens[-1]) if tokens else ""
        index[collapsed].append(key)
        if last_token and last_token != collapsed:
            index[last_token].append(key)
    for bucket in index.values():
        bucket.sort()

    link_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    counts: Counter = Counter()
    tier_before: Counter = Counter()
    tie_histogram: Counter = Counter()
    class_counts: Counter = Counter()
    resolved_by_chamber: Counter = Counter()
    resolved_by_container: Counter = Counter()
    counterfactual_office_scoped: Counter = Counter()
    counterfactual_wide_t2: Counter = Counter()
    counterfactual_merged_t4: Counter = Counter()

    for staffer in staffers:
        seen: set[tuple[str, str, str, str]] = set()
        keys: list[tuple[str, str, str, str]] = []
        for lookup in (staffer["surname_collapsed"], staffer["surname_last_token"]):
            if not lookup:
                continue
            for key in index.get(lookup, ()):
                if key not in seen:
                    seen.add(key)
                    keys.append(key)
        matches: list[dict[str, Any]] = []
        for key in sorted(keys):
            chamber, office_key, surname_raw, given_raw = key
            match_class = classify_match(staffer, surname_raw, given_raw, nickname_groups)
            if match_class is None:
                continue
            office = offices[(chamber, office_key)]
            for identity in split_identities(scan.groups[key]):
                middle = identity["middle_initial"]
                # A middle initial NARROWS a class; it never drops a match.  The
                # Quorum directory's "middle" token is usually a maiden or
                # compound surname (`Amy Emerick Clerkin`, `Shelby Settles
                # Harper`), so its initial routinely disagrees with the payroll's
                # real middle initial.  Dropping on disagreement silently
                # destroyed the evidence for 18 staffers whose names ARE present
                # -- a silent break of exactly the kind the tie law forbids.
                conflict = bool(
                    staffer["middle_initials"] and middle
                    and middle not in staffer["middle_initials"]
                )
                effective_class = (
                    CLASS_MIDDLE_CONFLICT
                    if conflict and match_class == CLASS_EXACT
                    else match_class
                )
                periods = sorted(identity["periods"])
                tier, corroboration = assign_tier(
                    effective_class,
                    office["container_kind"],
                    office["member_bioguide"],
                    staffer["member_bioguide"],
                    chamber,
                    periods,
                    staffer["member_terms"],
                    T2_ELIGIBLE_CONTAINER_KINDS,
                )
                tier_wide, _ = assign_tier(
                    effective_class,
                    office["container_kind"],
                    office["member_bioguide"],
                    staffer["member_bioguide"],
                    chamber,
                    periods,
                    staffer["member_terms"],
                    T2_CONTAINER_KINDS_WIDE,
                )
                if (
                    office["container_kind"] == "member_office"
                    and office["member_bioguide"]
                    and TIE_IDENTITY_SCOPE == "member_office_collapsed"
                ):
                    scope = f"member:{chamber}:{office['member_bioguide']}"
                else:
                    scope = f"office:{chamber}:{office_key}"
                identity_key = "|".join(
                    [scope, collapse(surname_raw), collapse(given_raw), middle or ""]
                )
                office_scoped_key = "|".join(
                    [f"office:{chamber}:{office_key}", collapse(surname_raw),
                     collapse(given_raw), middle or ""]
                )
                titles = [
                    title
                    for title, _n in sorted(
                        identity["titles"].items(), key=lambda item: (-item[1], item[0])
                    )
                ]
                matches.append(
                    {
                        "chamber": chamber,
                        "container_kind": office["container_kind"],
                        "corroboration": corroboration,
                        "match_class": effective_class,
                        "match_class_before_middle_initial_test": match_class,
                        "member_bioguide": office["member_bioguide"],
                        "middle_initial_conflict": conflict,
                        "office_key": office_key,
                        "office_raw": office["office_raw"],
                        "payroll_first": given_raw,
                        "payroll_identity_key": identity_key,
                        "payroll_last": surname_raw,
                        "payroll_middle_initial": middle,
                        "period_count": len(periods),
                        "period_first": periods[0] if periods else None,
                        "period_last": periods[-1] if periods else None,
                        "periods": periods,
                        "row_count": identity["rows"],
                        "tier": tier,
                        "titles": titles,
                        "_office_scoped_key": office_scoped_key,
                        "_tier_wide": tier_wide,
                    }
                )
                class_counts[effective_class] += 1

        matches.sort(
            key=lambda item: (
                TIER_RANK[item["tier"]],
                CLASS_RANK[item["match_class"]],
                item["chamber"],
                item["office_key"],
                item["payroll_last"],
                item["payroll_first"],
                item["payroll_middle_initial"] or "",
            )
        )

        if not matches:
            status = "NOT_FOUND"
            best_tier = None
            final_tier = None
            tie_size = 0
            ambiguous = False
            demoted = False
        else:
            best_tier = min(matches, key=lambda item: TIER_RANK[item["tier"]])["tier"]
            at_best = [item for item in matches if item["tier"] == best_tier]
            tie_size = len({item["payroll_identity_key"] for item in at_best})
            ambiguous = tie_size > 1
            demoted = ambiguous and best_tier in TIE_DEMOTION
            final_tier = TIE_DEMOTION[best_tier] if demoted else best_tier
            status = TIER_STATUS[final_tier]
            tier_before[best_tier] += 1
            tie_histogram[f"{best_tier}|{min(tie_size, 6)}"] += 1
            if status in RESOLVED_STATUSES:
                resolved_by_chamber[at_best[0]["chamber"]] += 1
                resolved_by_container[at_best[0]["container_kind"]] += 1
            # counterfactuals (A1, A3) -- measured, never applied
            office_tie = len({item["_office_scoped_key"] for item in at_best})
            cf_tier = TIE_DEMOTION[best_tier] if (office_tie > 1 and best_tier in TIE_DEMOTION) else best_tier
            counterfactual_office_scoped[TIER_STATUS[cf_tier]] += 1
            wide_best = min(matches, key=lambda item: TIER_RANK[item["_tier_wide"]])["_tier_wide"]
            wide_at_best = [item for item in matches if item["_tier_wide"] == wide_best]
            wide_tie = len({item["payroll_identity_key"] for item in wide_at_best})
            wide_tier = TIE_DEMOTION[wide_best] if (wide_tie > 1 and wide_best in TIE_DEMOTION) else wide_best
            counterfactual_wide_t2[TIER_STATUS[wide_tier]] += 1
            # A12 counterfactual: what a single merged T4 tier would have said.
            merged_best = TIER_MERGED.get(best_tier, best_tier)
            merged_at_best = [
                item for item in matches
                if TIER_MERGED.get(item["tier"], item["tier"]) == merged_best
            ]
            merged_tie = len({item["payroll_identity_key"] for item in merged_at_best})
            if merged_best == MERGED_T4_LABEL:
                merged_status = "CANDIDATE_T5" if merged_tie > 1 else "RESOLVED_T4"
            else:
                merged_status = TIER_STATUS[
                    TIE_DEMOTION[merged_best]
                    if (merged_tie > 1 and merged_best in TIE_DEMOTION)
                    else merged_best
                ]
            counterfactual_merged_t4[merged_status] += 1
        if not matches:
            counterfactual_office_scoped["NOT_FOUND"] += 1
            counterfactual_wide_t2["NOT_FOUND"] += 1
            counterfactual_merged_t4["NOT_FOUND"] += 1

        counts[status] += 1
        if ambiguous:
            counts["staffers_ambiguous_at_best_tier"] += 1
        if demoted:
            counts[f"demoted_for_tie_from_{best_tier}"] += 1
        distinct_identities = len({item["payroll_identity_key"] for item in matches})
        if distinct_identities > 1:
            counts["staffers_whose_name_reaches_more_than_one_payroll_identity"] += 1
            if status in RESOLVED_STATUSES:
                # How much of the recovery rests on a name that is not unique on
                # the payroll.  These rows are RESOLVED because the office
                # corroborates them, not because the name is unambiguous.
                counts["resolved_staffers_whose_name_reaches_more_than_one_payroll_identity"] += 1
        # Surname reached, first name never did: every match this staffer has is
        # a FIRST_INITIAL_* class.  These are the rows the rule REFUSES to
        # resolve however many of them there are.
        if matches and all(item["match_class"] in INITIAL_CLASSES for item in matches):
            counts["staffers_with_a_surname_match_but_no_first_name_match"] += 1
            counts[f"surname_only_by_status_{status}"] += 1

        emitted_matches = []
        for match in matches:
            body = {k: v for k, v in match.items() if not k.startswith("_")}
            emitted_matches.append(body)
            candidate_rows.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "display_name": staffer["display_name"],
                    "is_best_tier_match": match["tier"] == best_tier,
                    "member_bioguide": staffer["member_bioguide"],
                    "member_display": staffer["member_display"],
                    "quorum_staff_id": staffer["quorum_staff_id"],
                    "review_status": "REVIEW_REQUIRED",
                    "rule_version": rule_version,
                    "schema_id": CANDIDATE_SCHEMA,
                    "staffer_ambiguous": ambiguous,
                    "staffer_best_tier": best_tier,
                    "staffer_status": status,
                    "tie_size": tie_size,
                    "title_raw": staffer["title_raw"],
                    **body,
                }
            )

        link_rows.append(
            {
                "ambiguous": ambiguous,
                "best_tier": final_tier,
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "demoted_for_tie": demoted,
                "display_name": staffer["display_name"],
                "display_name_key": {
                    "first": staffer["first_raw"] or None,
                    "last": staffer["surname_raw"] or None,
                    "middle_initial": staffer["middle_initial"],
                    "middle_initials": sorted(staffer["middle_initials"]),
                },
                "match_count": len(matches),
                "matches": emitted_matches,
                "member_bioguide": staffer["member_bioguide"],
                "member_display": staffer["member_display"],
                "member_resolution_method": staffer["member_resolution_method"],
                "payroll_identity_count": distinct_identities,
                "quorum_staff_id": staffer["quorum_staff_id"],
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": LINK_SCHEMA,
                "status": status,
                "tie_size": tie_size,
                "tier_before_tie_demotion": best_tier,
                "title_raw": staffer["title_raw"],
            }
        )

    link_rows.sort(
        key=lambda row: (row["member_display"], row["display_name"], row["quorum_staff_id"])
    )
    candidate_rows.sort(
        key=lambda row: (
            row["quorum_staff_id"],
            row["chamber"],
            row["office_key"],
            row["payroll_last"],
            row["payroll_first"],
            row["payroll_middle_initial"] or "",
        )
    )

    output_root.mkdir(parents=True, exist_ok=True)
    payloads = {LINK_FILE: link_rows, CANDIDATE_FILE: candidate_rows}
    for name, rows in payloads.items():
        write_ndjson_gz(output_root / name, rows)

    tripwire: list[str] = []
    authored: list[str] = []
    verbatim: Counter = Counter()
    for name, rows in payloads.items():
        tripwire.extend(assert_unpromoted(rows, name))
        hits, occurrences = scan_language_law(rows)
        authored.extend(hits)
        verbatim += occurrences

    failures: list[str] = []
    if tripwire:
        failures.append("ANTI_PROMOTION_TRIPWIRE")
    if len(link_rows) != len(entries):
        failures.append("CURRENT_STAFFER_ROW_CONSERVATION")
    if len({row["quorum_staff_id"] for row in link_rows}) != len(link_rows):
        failures.append("DUPLICATE_QUORUM_STAFF_ID")
    for row in link_rows:
        if row["status"] in RESOLVED_STATUSES and row["ambiguous"]:
            failures.append("RESOLVED_STATUS_ON_AMBIGUOUS_ROW")
            break
    for row in link_rows:
        if (row["status"] == "NOT_FOUND") != (row["match_count"] == 0):
            failures.append("NOT_FOUND_STATUS_DISAGREES_WITH_MATCH_COUNT")
            break

    resolved_total = sum(counts.get(status, 0) for status in RESOLVED_STATUSES)
    denominator = len(link_rows)

    receipt = {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "conservation": {
            "current_staffer_rows": len(link_rows),
            "current_staffer_rows_equal_directory": len(link_rows) == len(entries),
            "distinct_quorum_staff_ids": len({row["quorum_staff_id"] for row in link_rows}),
            "expected_current_staffers": EXPECTED_CURRENT_STAFFERS,
            "match_candidate_rows": len(candidate_rows),
            "match_candidate_rows_equal_match_sum": len(candidate_rows)
            == sum(row["match_count"] for row in link_rows),
            "members_in_directory": len(member_resolution),
            "staff_directory_entries": len(entries),
        },
        "counts": {
            "class_matches": dict(sorted(class_counts.items())),
            "demotions_for_tie": {
                key.replace("demoted_for_tie_from_", ""): value
                for key, value in sorted(counts.items())
                if key.startswith("demoted_for_tie_from_")
            },
            "member_office_resolution_methods": dict(sorted(office_resolution.items())),
            "member_resolution_methods": dict(
                sorted(Counter(method for _b, method in member_resolution.values()).items())
            ),
            "members_resolved_to_a_bioguide": sum(
                1 for bioguide, _m in member_resolution.values() if bioguide
            ),
            "offices_by_chamber_and_container_kind": dict(
                sorted(
                    Counter(
                        f"{chamber}:{office['container_kind']}"
                        for (chamber, _key), office in offices.items()
                    ).items()
                )
            ),
            "old_baseline_link_status": dict(sorted(OLD_BASELINE.items())),
            "resolved_by_chamber": dict(sorted(resolved_by_chamber.items())),
            "resolved_by_container_kind": dict(sorted(resolved_by_container.items())),
            "resolved_total": resolved_total,
            "source_rows": dict(sorted(scan.counts.items())),
            "staffers_ambiguous_at_best_tier": counts.get("staffers_ambiguous_at_best_tier", 0),
            "staffers_whose_name_reaches_more_than_one_payroll_identity": counts.get(
                "staffers_whose_name_reaches_more_than_one_payroll_identity", 0
            ),
            "status": dict(
                sorted((key, value) for key, value in counts.items() if key in
                       set(TIER_STATUS.values()) | {"NOT_FOUND"})
            ),
            "resolved_staffers_whose_name_reaches_more_than_one_payroll_identity": counts.get(
                "resolved_staffers_whose_name_reaches_more_than_one_payroll_identity", 0
            ),
            "staffers_with_a_surname_match_but_no_first_name_match": counts.get(
                "staffers_with_a_surname_match_but_no_first_name_match", 0
            ),
            "surname_only_matches_by_status": {
                key.replace("surname_only_by_status_", ""): value
                for key, value in sorted(counts.items())
                if key.startswith("surname_only_by_status_")
            },
            "t2_container_counterfactual_wide": dict(sorted(counterfactual_wide_t2.items())),
            "tie_grouping_counterfactual_merged_t4": dict(
                sorted(counterfactual_merged_t4.items())
            ),
            "tie_scope_counterfactual_office_scoped": dict(
                sorted(counterfactual_office_scoped.items())
            ),
            "tie_size_histogram_by_tier_before_demotion": dict(sorted(tie_histogram.items())),
            "tier_before_tie_demotion": dict(sorted(tier_before.items())),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_keys": {
                CANDIDATE_FILE: (
                    "quorum_staff_id, chamber, office_key, payroll_last, payroll_first, "
                    "payroll_middle_initial"
                ),
                LINK_FILE: "member_display, display_name, quorum_staff_id",
            },
        },
        "dials": {
            "freeze_status": "UNTESTED_DEFAULTS_PENDING_FREEZE",
            "member_resolution_chamber_restricted": MEMBER_RESOLUTION_CHAMBER_RESTRICTED,
            "member_resolution_max_surname_tokens": MEMBER_RESOLUTION_MAX_SURNAME_TOKENS,
            "member_resolution_repair_letter_split": MEMBER_RESOLUTION_REPAIR_LETTER_SPLIT,
            "nickname_table": dict(sorted(nickname_stats.items())),
            "t2_eligible_container_kinds": list(T2_ELIGIBLE_CONTAINER_KINDS),
            "tie_identity_scope": TIE_IDENTITY_SCOPE,
            "tier_precedence": list(TIER_PRECEDENCE),
        },
        "failures": sorted(set(failures)),
        "files": {
            name: {
                "bytes": (output_root / name).stat().st_size,
                "rows": len(rows),
                "sha256": sha(output_root / name),
            }
            for name, rows in payloads.items()
        },
        "generated_at": args.generated_at or "2026-09-02T00:00:00Z",
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha(Path(__file__)),
        },
        "inputs": dict(sorted(inputs.items())),
        "language_law": {
            "authored_value_and_field_name_hits": len(authored),
            "authored_hits": sorted(set(authored))[:20],
            "banned_tokens": list(LANGUAGE_LAW_TOKENS),
            "policy": LANGUAGE_LAW_POLICY,
            "verbatim_source_quoted_fields": list(VERBATIM_SOURCE_QUOTED_FIELDS),
            "verbatim_token_occurrences": dict(sorted(verbatim.items())),
        },
        "notes": {
            "old_rule_defect": (
                "build_hill_personnel_spine.py:2162-2187 built the candidate set from "
                "House spans whose last_period equals the latest House quarter and whose "
                "member_bioguide equals the staffer's member. That predicate excludes the "
                "whole Senate, every non-member office, and every trace ending before the "
                "latest quarter."
            ),
            "tier_is_name_evidence": (
                "A tier grades NAME EVIDENCE and office corroboration. It is not an "
                "employment finding, not an identity adjudication, and no row is "
                "promotable: every row carries review_status REVIEW_REQUIRED, "
                "canonical_eligible false, canonical_employment_promoted false and "
                "canonical_identity_decision NOT_ADJUDICATED."
            ),
            "tie_rule": (
                "A tie is never broken. Every payroll identity reached is emitted; when "
                "the best tier is supported by more than one distinct payroll identity the "
                "row is marked ambiguous and demoted to a candidate tier."
            ),
        },
        "rate": {
            "denominator": denominator,
            "not_found_rate": round(counts.get("NOT_FOUND", 0) / denominator, 6) if denominator else None,
            "resolved_rate": round(resolved_total / denominator, 6) if denominator else None,
        },
        "rule_version": rule_version,
        "run_id": args.run_id,
        "schema_id": RECEIPT_SCHEMA,
        "stage_id": STAGE_ID,
        "tripwire": {
            "anti_promotion_failures": tripwire[:20],
            "anti_promotion_failure_count": len(tripwire),
        },
    }
    write_json_atomic(output_root / RECEIPT_FILE, receipt)
    return receipt


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild current-staffer -> Hill payroll links under the corrected rule."
    )
    parser.add_argument("--staff-directory", type=Path, default=None)
    parser.add_argument("--house-observations", type=Path, default=None)
    parser.add_argument("--senate-candidates", type=Path, default=None)
    parser.add_argument("--nickname-table", type=Path, default=None)
    parser.add_argument("--roster-dir", type=Path, default=None)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--rule-version", default=DEFAULT_RULE_VERSION)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        glassbox, args.run_id, "run.start", "running",
        "current staffer link rebuild v2 start",
        detail=f"output_root={args.output_root}",
    )
    try:
        receipt = run(args)
    except Exception as error:
        emit_glassbox(
            glassbox, args.run_id, "run.finish", "failed",
            "current staffer link rebuild v2 failed", detail=str(error)[:500],
        )
        print(f"FAILED: {error}", file=sys.stderr)
        return 1
    status = "completed" if not receipt["failures"] else "failed"
    emit_glassbox(
        glassbox, args.run_id, "run.finish", status,
        "current staffer link rebuild v2 finish",
        detail=json.dumps(receipt["counts"]["status"], sort_keys=True),
        metadata={
            "resolved_total": receipt["counts"]["resolved_total"],
            "rows": receipt["conservation"]["current_staffer_rows"],
        },
    )
    print(json.dumps(
        {
            "conservation": receipt["conservation"],
            "failures": receipt["failures"],
            "files": receipt["files"],
            "status": receipt["counts"]["status"],
            "resolved_total": receipt["counts"]["resolved_total"],
        },
        indent=1, sort_keys=True,
    ))
    return 0 if not receipt["failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
