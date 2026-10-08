#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the immutable A6 prose release: filer-asserted employment episodes
recovered from LDA covered-position prose under a STRICT same-string binding
rule, plus the payroll cross-check no prior lane ran.

WHAT THIS IS
------------
``audits/staffer_network/lda_conservative_bounded_episode_candidates_20260901_b``
holds 3,090 near-candidate rows whose receipt status is
``BLOCKED_SAFE_LINKAGE_NOT_ESTABLISHED`` and whose ``candidate_rows`` is 0.
Every one of those rows already has exactly one parsed role mention, one
office/employer mention and one date-range mention (the upstream funnel's
``exact_one_role_one_office_one_date_range: 3090``), and every one of them is
blocked by two reasons that are present on all 3,090 rows *by design* --
``DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE`` and
``ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED``.  Those two are the upstream lane
declining to adjudicate; they are not evidence of a defect in the row.

This producer performs that adjudication, once, under a rule written down in
full below, and emits the surviving rows as REVIEW_REQUIRED prose episodes.
It promotes nothing.

THE STRICT SAME-STRING BINDING RULE (the adjudication)
------------------------------------------------------
A near-candidate row is RELEASED only when all five conditions hold:

  R1  SAME-STRING BINDING.  The role mention, the office mention and the
      date-range mention are all present, and all three of their character
      spans resolve inside ONE source string -- the row's ``claim_text`` --
      with ``claim_text[span_start:span_end] == mention.text`` for each.
      This is what licenses reading the three mentions as one assertion
      rather than three unrelated fragments of a longer resume blob;
      ``claim_text`` is itself a single covered-position segment (in 2,579 of
      the 3,090 rows it is a proper substring of the longer
      ``raw_covered_position_literal``, i.e. the literal really does carry
      more than one segment and the segmentation is what makes "one string"
      meaningful).
  R2  MEMBER OFFICE OR COMMITTEE.  ``office_employer_mention.entity_class``
      is ``MEMBER_OFFICE_CANDIDATE`` or ``COMMITTEE_CANDIDATE``.
  R3  BOTH YEARS EXPLICIT.  ``date_range_mention.explicit_start_year`` and
      ``.explicit_end_year`` are both non-null.
  R4  NO CONTENT-SPECIFIC BLOCKER.  None of AMBIGUOUS_ROLE_ABBREVIATION,
      TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED, DATE_RANGE_REVERSED,
      MENTION_SPANS_OVERLAP is in ``rejection_reasons``.
  R5  YEAR ORDER.  ``start_year <= end_year`` re-derived here rather than
      trusted from the upstream flag.

The two universal blockers are deliberately NOT treated as exclusions -- they
are the question this producer answers.  ``DATE_MENTION_REVIEW_FLAG_PRESENT``,
``DATE_RANGE_NOT_CLOSED_WITH_EXPLICIT_YEARS`` and ``GENERIC_ROLE_TITLE_RISK``
are also not exclusions: the first two are subsumed by R3 (a row without both
explicit years cannot pass), and GENERIC_ROLE_TITLE_RISK is carried onto the
released row as a field so a reviewer can filter on it, because a generic
title ("Director") weakens the ROLE but not the OFFICE or the YEARS, and the
release does not claim the title is canonical.

Released rows carry ``precision: "year"``, ``single_author: true`` and
``temporal_semantics: "ASSERTED_EPISODE"``.  The episode is what ONE filer
asserted about themselves in ONE string; it is not an observation.

MEMBER RESOLUTION
-----------------
Strict roster match only, ported from the reviewed rule in
``build_tiered_corroboration_sidecar.py`` (INV-6): exact surname, plus first
name through the nickname table, plus a term-window check that the declared
years overlap a term of that member of the right chamber type.  Two
differences from that lane, both STRICTER, both deliberate:

  * The nickname table is loaded with MULTI-FORMAL SHORT FORMS DROPPED.  An
    entry such as ``jay -> [james, jason]`` cannot license a resolution,
    because it would let one prose token match two different roster people
    and the surviving pick would then be an artifact of which surname
    happened to collide.  144 of the table's 188 entries survive.
  * ``start_year <= end_year`` is re-derived (R5) instead of trusted.

Where the member does not resolve, the row is KEPT with
``member_bioguide: null`` and a reason code.  There is no fuzzy match
anywhere in this file.

THE PAYROLL CROSS-CHECK
-----------------------
For every released episode whose member resolves, this producer looks inside
THAT member's own payroll office for the filer's own name and records a
four-way outcome:

  CONFIRMED_BY_PAYROLL            name found in the declared office with
                                  period overlap
  NAME_FOUND_PERIOD_MISMATCH      name found in the declared office, no
                                  period overlap
  OFFICE_OUT_OF_CORPUS_WINDOW     the declared years do not overlap the
                                  payroll corpus at all (House corpus starts
                                  2009Q3, Senate 2011-04-01).  This is
                                  EXPECTED to be common and is NOT a failure
                                  -- it says the assertion is unreachable by
                                  the evidence on disk, not that it is wrong.
  NAME_ABSENT_FROM_DECLARED_OFFICE the window was reachable and the name is
                                  not there.

OFFICE_OUT_OF_CORPUS_WINDOW takes precedence over the other three: when the
declared window cannot reach the corpus, no period overlap is possible, so
calling such a row NAME_FOUND_PERIOD_MISMATCH or NAME_ABSENT would attribute
to the assertion what is really a property of the corpus.  Nothing is lost:
``name_found_in_declared_office`` is carried as its own field on every row.

NOTHING IS PROMOTED
-------------------
Every emitted row carries ``canonical_eligible: false``,
``canonical_employment_promoted: false``,
``canonical_identity_decision: "NOT_ADJUDICATED"`` and
``review_status: "REVIEW_REQUIRED"``.  The receipt hash-binds every input and
pins both promotion counters at 0.  This generation is consumed by nothing
until Paul rules.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Only these two fec modules may be imported by this lane.
from fec.staffer_network.intervals import (  # noqa: E402
    UncertainInterval,
    possible_overlap_days,
)
from fec.staffer_network.schema_validation import (  # noqa: E402
    validate_instance,
    validate_schema_definition,
)

import yaml  # noqa: E402


# ---------------------------------------------------------------------------
# Identity of this build
# ---------------------------------------------------------------------------
STAGE_ID = "a6-prose-release"
RULE_VERSION = "a6-prose-release-v1"
DEFAULT_RUN_ID = "run-20260903T001500000000Z-a6release"

EPISODE_SCHEMA = "staffer-network-a6-prose-release-episode-v1"
EXCLUSION_SCHEMA = "staffer-network-a6-prose-release-exclusion-v1"
RECEIPT_SCHEMA = "staffer-network-a6-prose-release-receipt-v1"

EPISODE_FILE = "a6_prose_release_episodes.ndjson.gz"
EXCLUSION_FILE = "a6_prose_release_exclusions.ndjson.gz"
RECEIPT_FILE = "a6_prose_release_receipt.json"

DEFAULT_LIVE_ROOT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
ROSTER_SNAPSHOT = "750c0608efb6ef1fc3257ba72c99af3771d35088"

# The four content-specific blockers that DO exclude a row (R4).
EXCLUDING_BLOCKERS = (
    "AMBIGUOUS_ROLE_ABBREVIATION",
    "DATE_RANGE_REVERSED",
    "MENTION_SPANS_OVERLAP",
    "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED",
)
# The two blockers present on every row by design, which this lane adjudicates.
ADJUDICATED_UNIVERSAL_BLOCKERS = (
    "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
    "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
)
RELEASABLE_ENTITY_CLASSES = frozenset(
    {"COMMITTEE_CANDIDATE", "MEMBER_OFFICE_CANDIDATE"}
)

# Measured payroll corpus windows (re-derived at build time and gate-checked
# against these constants, never assumed).
HOUSE_CORPUS_START = date(2009, 7, 1)      # 2009Q3
HOUSE_CORPUS_END = date(2026, 3, 31)       # 2026Q1
SENATE_CORPUS_START = date(2011, 4, 1)
SENATE_CORPUS_END = date(2026, 3, 31)

CROSS_CHECK_STATUSES = (
    "CONFIRMED_BY_PAYROLL",
    "NAME_ABSENT_FROM_DECLARED_OFFICE",
    "NAME_FOUND_PERIOD_MISMATCH",
    "NOT_CHECKED_MEMBER_UNRESOLVED",
    "OFFICE_OUT_OF_CORPUS_WINDOW",
)
MAX_EVIDENCE_EXAMPLES = 3


class GateFailure(RuntimeError):
    """A build-blocking invariant failed.  Never caught inside this module."""


# ---------------------------------------------------------------------------
# Canonical IO
# ---------------------------------------------------------------------------
def canonical_json_line(record: Mapping[str, Any]) -> str:
    """One NDJSON line: lexicographic keys, no spaces, LF supplied by caller."""

    return json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    except BaseException:
        if tmp.exists():
            tmp.unlink()
        raise


def write_ndjson_gz(path: Path, records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic gzip NDJSON: sorted keys, LF, gzip mtime pinned to 0."""

    raw = io.BytesIO()
    for record in records:
        raw.write(canonical_json_line(record).encode("utf-8"))
        raw.write(b"\n")
    body = raw.getvalue()
    buffer = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buffer, mtime=0) as stream:
        stream.write(body)
    payload = buffer.getvalue()
    atomic_write_bytes(path, payload)
    return {
        "bytes": len(payload),
        "path": path.name,
        "rows": len(records),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "uncompressed_sha256": hashlib.sha256(body).hexdigest(),
    }


def write_receipt(path: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Lane convention: receipts are canonical COMPACT JSON with one trailing
    LF -- no indentation anywhere in this lane's receipts."""

    payload = canonical_json_line(receipt).encode("utf-8") + b"\n"
    atomic_write_bytes(path, payload)
    return {
        "bytes": len(payload),
        "path": path.name,
        "sha256": hashlib.sha256(payload).hexdigest(),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hash_binding(path: Path) -> dict[str, Any]:
    """The input-binding block written into the receipt for every input."""

    return {
        "bytes": path.stat().st_size,
        "path": str(path),
        "sha256": sha256_file(path),
    }


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def refuse_non_empty(directory: Path) -> None:
    """Lane law: a generation directory is immutable, so refuse to write into
    one that already has content rather than silently overwriting a prior
    generation."""

    if directory.exists() and any(directory.iterdir()):
        raise GateFailure(f"output directory is nonempty: {directory}")


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------
SUFFIX_TOKENS = {"jr", "sr", "ii", "iii", "iv", "v"}
# LDA display names are self-entered and 4,603 of the 25,340 people in the LDA
# ledger carry a leading honorific ("mr JAKE OKEN-BERG").  Reading that token as
# the given name makes the payroll name binding impossible, so it is stripped.
HONORIFIC_TOKENS = {"dr", "hon", "miss", "mr", "mrs", "ms", "mx", "prof", "rev", "sir", "the"}


def strip_accents(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm_token(value: str | None) -> str:
    """Uppercase, accent-stripped, A-Z0-9 only.  This is the form the House
    ``person_key`` uses ('Aalim-Johnson' -> 'AALIMJOHNSON'), so filer names and
    payroll keys become comparable without any fuzzy step."""

    return re.sub(r"[^A-Z0-9]", "", strip_accents(value or "").upper())


def fold_name(value: str | None) -> str:
    """Loose fold for first-name comparison only: casefold, drop non-alnum, so
    'J.D.' and 'JD' compare equal.  Ported from the reviewed sidecar rule."""

    return re.sub(r"[^a-z0-9]", "", strip_accents(value or "").casefold())


def name_tokens(value: str | None) -> list[str]:
    cleaned = strip_accents(value or "").upper()
    cleaned = re.sub(r"[^A-Z0-9\s]", " ", cleaned)
    return [token for token in cleaned.split() if token]


def person_name_tokens(value: str | None) -> list[str]:
    """Tokenize a PERSON name on whitespace only, normalizing each token to
    A-Z0-9.  This mirrors how the House payroll ``person_key`` is built
    ('Aalim-Johnson' -> 'AALIMJOHNSON'), so an internal hyphen or apostrophe
    never splits a name on one side of the comparison and not the other.
    Office strings keep the looser ``name_tokens`` split, because there the
    punctuation is usually a real separator."""

    return [token for token in (norm_token(part) for part in (value or "").split()) if token]


def split_display_name(display_name: str | None) -> tuple[str | None, str | None]:
    """LDA display names are '[HONORIFIC] FIRST [MIDDLE...] LAST [SUFFIX]'.
    Returns (given, surname) as normalized tokens, or (None, None) when the
    name has too few usable tokens to bind.

    KNOWN RESIDUAL, deliberately not guessed at: this reads the LAST token as
    the surname, so a filer whose surname is two separate words ('Cortez
    Masto') is parsed with only the second word.  The LDA display name carries
    no field boundary that would distinguish a middle name from a compound
    surname, and inventing one would be a fuzzy match.  Such rows land in
    NAME_ABSENT_FROM_DECLARED_OFFICE, which is why that bucket is reported as
    a floor rather than a verdict."""

    tokens = person_name_tokens(display_name)
    while tokens and tokens[0].lower() in HONORIFIC_TOKENS:
        tokens.pop(0)
    while tokens and tokens[-1].lower() in SUFFIX_TOKENS:
        tokens.pop()
    tokens = [token for token in tokens if len(token) > 1]
    if len(tokens) < 2:
        return None, None
    return tokens[0], tokens[-1]


def split_payroll_comma_name(raw: str | None) -> tuple[str | None, str | None]:
    """Payroll payee names are 'LAST, FIRST [MIDDLE]'.  Returns
    (given, surname) normalized."""

    if not raw or "," not in raw:
        return None, None
    surname_part, _, given_part = raw.partition(",")
    surname_tokens = [
        token
        for token in person_name_tokens(surname_part)
        if token.lower() not in SUFFIX_TOKENS
    ]
    given_tokens = [
        token
        for token in person_name_tokens(given_part)
        if token.lower() not in SUFFIX_TOKENS and token.lower() not in HONORIFIC_TOKENS
    ]
    given_tokens = [token for token in given_tokens if len(token) > 1]
    if not surname_tokens or not given_tokens:
        return None, None
    return given_tokens[0], "".join(surname_tokens)


# ---------------------------------------------------------------------------
# Nickname table (multi-formal short forms DROPPED)
# ---------------------------------------------------------------------------
NICKNAME_TABLE_SCHEMA = "staffer-network-first-name-nickname-table-v1"


def load_nickname_table(path: Path) -> tuple[dict[str, tuple[str, ...]], dict[str, int]]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema_id") != NICKNAME_TABLE_SCHEMA:
        raise GateFailure(
            f"nickname table schema mismatch: {path}: {payload.get('schema_id')!r}"
        )
    entries = payload.get("entries") or {}
    kept: dict[str, tuple[str, ...]] = {}
    dropped = 0
    for key, values in entries.items():
        forms = tuple(str(v).casefold() for v in values)
        if len(set(forms)) != 1:
            dropped += 1
            continue
        kept[str(key).casefold()] = forms
    stats = {
        "entries_in_file": len(entries),
        "entries_dropped_multi_formal": dropped,
        "entries_retained": len(kept),
    }
    return kept, stats


def nickname_expansions(
    value: str, table: Mapping[str, Sequence[str]]
) -> set[str]:
    folded = fold_name(value)
    forms = {folded}
    for formal in table.get(folded, ()):
        forms.add(fold_name(formal))
    return forms


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
_TERM_TYPE_BY_CHAMBER = {"house": "rep", "senate": "sen"}


def parse_iso(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def load_roster(directory: Path) -> tuple[
    dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]
]:
    """Returns (by_surname, by_bioguide).  Ported from the reviewed sidecar
    loader; extended only with the accent-folded surname token list needed to
    match a Senate payroll office string back to an already-resolved member."""

    by_surname: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    by_bioguide: dict[str, dict[str, Any]] = {}
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        with (directory / filename).open("r", encoding="utf-8") as stream:
            people = yaml.safe_load(stream)
        for person in people:
            bioguide = (person.get("id") or {}).get("bioguide")
            if not bioguide:
                continue
            name = person.get("name") or {}
            years: list[tuple[int, int]] = []
            terms: list[dict[str, Any]] = []
            for term in person.get("terms") or []:
                try:
                    years.append((int(term["start"][:4]), int(term["end"][:4])))
                except Exception:
                    pass
                start_date = parse_iso(term.get("start"))
                end_date = parse_iso(term.get("end"))
                if start_date is not None and end_date is not None:
                    terms.append(
                        {"type": term.get("type"), "start": start_date, "end": end_date}
                    )
            if not years:
                continue
            last = str(name.get("last", ""))
            entry = {
                "bioguide": bioguide,
                "first": str(name.get("first", "")),
                "last": last,
                "last_tokens": name_tokens(last),
                "nickname": name.get("nickname"),
                "official_full": name.get("official_full"),
                "min_year": min(y[0] for y in years),
                "max_year": max(y[1] for y in years),
                "terms": terms,
            }
            by_surname[last.upper()].append(entry)
            if bioguide not in by_bioguide:
                by_bioguide[bioguide] = entry
    return (
        {
            key: sorted(value, key=lambda item: item["bioguide"])
            for key, value in by_surname.items()
        },
        by_bioguide,
    )


def candidate_first_name_forms(
    candidate: Mapping[str, Any], table: Mapping[str, Sequence[str]]
) -> set[str]:
    forms: set[str] = set()
    for raw in (candidate.get("first"), candidate.get("nickname")):
        if raw:
            forms |= nickname_expansions(str(raw), table)
    official_full = candidate.get("official_full")
    if official_full:
        tokens = str(official_full).split()
        if tokens:
            forms |= nickname_expansions(tokens[0], table)
    return forms


def first_name_matches(
    first: str, candidate: Mapping[str, Any], table: Mapping[str, Sequence[str]]
) -> bool:
    return bool(
        nickname_expansions(first, table) & candidate_first_name_forms(candidate, table)
    )


def candidate_has_overlapping_term(
    candidate: Mapping[str, Any],
    chamber: str | None,
    window_start: date | None,
    window_end: date | None,
) -> bool:
    if window_start is None or window_end is None:
        return True
    required_type = _TERM_TYPE_BY_CHAMBER.get(chamber) if chamber else None
    for term in candidate.get("terms") or ():
        if required_type is not None and term.get("type") != required_type:
            continue
        start, end = term.get("start"), term.get("end")
        if start is None or end is None:
            continue
        if start <= window_end and window_start <= end:
            return True
    return False


def declared_chambers(
    candidate: Mapping[str, Any], window_start: date, window_end: date
) -> list[str]:
    """Which chamber(s) the member actually served in across the declared
    window.  This is what decides which payroll corpus to search -- never the
    prose title, which is often absent or wrong."""

    chambers: set[str] = set()
    for term in candidate.get("terms") or ():
        start, end = term.get("start"), term.get("end")
        if start is None or end is None:
            continue
        if start <= window_end and window_start <= end:
            if term.get("type") == "rep":
                chambers.add("house")
            elif term.get("type") == "sen":
                chambers.add("senate")
    return sorted(chambers)


TITLE_RE = re.compile(
    r"\b(?:Rep\.?|Sen\.?|Senator|Representative|Congressman|Congresswoman|Cong\.|Hon\.?)\s+"
    r"([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})"
)
OFFICE_RE = re.compile(
    r"\bOffice of(?:\s+(?:Sen\.?|Senator|Rep\.?|Representative|Congressman|Congresswoman))?\s+"
    r"([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})"
)
SENATE_TITLE_RE = re.compile(r"\b(?:SEN\.?|SENATOR)\b")
HOUSE_TITLE_RE = re.compile(
    r"\b(?:REP\.?|REPRESENTATIVE|CONGRESSMAN|CONGRESSWOMAN|CONG\.)\b"
)


def chamber_hint(office_text: str) -> str | None:
    upper = (office_text or "").upper()
    if SENATE_TITLE_RE.search(upper):
        return "senate"
    if HOUSE_TITLE_RE.search(upper):
        return "house"
    return None


def extract_surname_first(captured: str) -> tuple[str | None, str | None]:
    tokens = (captured or "").strip().rstrip(".,;").split()
    cleaned: list[str] = []
    for token in tokens:
        trimmed = token.strip().rstrip(".,;")
        if trimmed.lower().rstrip(".") in SUFFIX_TOKENS:
            continue
        if len(trimmed.replace(".", "")) <= 1:
            continue
        cleaned.append(trimmed)
    if not cleaned:
        return None, None
    surname = cleaned[-1]
    first = cleaned[0] if len(cleaned) >= 2 else None
    return first, surname


def resolve_member_bioguide(
    first: str | None,
    surname: str | None,
    roster: Mapping[str, list[dict[str, Any]]],
    table: Mapping[str, Sequence[str]],
    *,
    chamber: str | None,
    window_start: date | None,
    window_end: date | None,
) -> tuple[str | None, str]:
    """Strict roster resolution.  No fuzzy match, ever."""

    if not surname:
        return None, "UNRESOLVED_SURNAME_NOT_PARSED"
    candidates = roster.get(surname.upper())
    if not candidates:
        return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"
    if first:
        matched = [c for c in candidates if first_name_matches(first, c, table)]
        if not matched:
            return None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
        if len(matched) == 1:
            candidate = matched[0]
            if candidate_has_overlapping_term(
                candidate, chamber, window_start, window_end
            ):
                return candidate["bioguide"], "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
            return None, "TERM_WINDOW_MISMATCH"
        term_matched = [
            c
            for c in matched
            if candidate_has_overlapping_term(c, chamber, window_start, window_end)
        ]
        if len(term_matched) == 1:
            return (
                term_matched[0]["bioguide"],
                "STRICT_ROSTER_SURNAME_FIRST_NAME_AND_TERM_WINDOW",
            )
        if not term_matched:
            return None, "TERM_WINDOW_MISMATCH"
        return None, "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"
    if len(candidates) == 1:
        candidate = candidates[0]
        if candidate_has_overlapping_term(candidate, chamber, window_start, window_end):
            return (
                candidate["bioguide"],
                "STRICT_ROSTER_UNIQUE_SURNAME_NO_FIRST_NAME_IN_OFFICE_STRING",
            )
        return None, "TERM_WINDOW_MISMATCH"
    return None, "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME"


# ---------------------------------------------------------------------------
# Interval algebra (INV-9: reuse the reviewed module, never reimplement)
# ---------------------------------------------------------------------------
def closed_interval(start: date, end: date) -> UncertainInterval:
    """Represent an inclusive [start, end] day range as the reviewed
    half-open UncertainInterval, so overlap goes through the reviewed
    ``possible_overlap_days`` rather than an ad-hoc comparison."""

    end_exclusive = end + timedelta(days=1)
    return UncertainInterval(
        start_earliest=start,
        start_latest=start,
        end_earliest=end_exclusive,
        end_latest=end_exclusive,
        start_precision="day",
        end_precision="day",
        asserted_current=False,
    )


def intervals_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    if a_end < a_start or b_end < b_start:
        return False
    return (
        possible_overlap_days(
            closed_interval(a_start, a_end), closed_interval(b_start, b_end)
        )
        > 0
    )


QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")


def quarter_bounds(value: str | None) -> tuple[date, date] | None:
    match = QUARTER_RE.match(value or "")
    if not match:
        return None
    year, quarter = int(match.group(1)), int(match.group(2))
    start_month = 3 * (quarter - 1) + 1
    start = date(year, start_month, 1)
    if quarter == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, start_month + 3, 1) - timedelta(days=1)
    return start, end


# ---------------------------------------------------------------------------
# Payroll indexes
# ---------------------------------------------------------------------------
def load_house_office_index(
    path: Path, targets: set[str]
) -> tuple[dict[str, list[dict[str, Any]]], set[str], tuple[str, str]]:
    """Index House person-office spans for the target bioguides only.

    Returns (by_bioguide -> list of span entries, bioguides present in corpus,
    (min_quarter, max_quarter) observed across the whole file).
    """

    wanted = {f"HON:{bioguide}" for bioguide in targets}
    index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    present: set[str] = set()
    min_quarter: str | None = None
    max_quarter: str | None = None
    for record in read_rows(path):
        first_q = record.get("first_report_quarter")
        last_q = record.get("last_report_quarter")
        if isinstance(first_q, str) and QUARTER_RE.match(first_q):
            min_quarter = first_q if min_quarter is None else min(min_quarter, first_q)
        if isinstance(last_q, str) and QUARTER_RE.match(last_q):
            max_quarter = last_q if max_quarter is None else max(max_quarter, last_q)
        office_key = record.get("office_key")
        if office_key not in wanted:
            continue
        bioguide = str(office_key)[4:]
        present.add(bioguide)
        person_key = str(record.get("person_key") or "")
        if not person_key.startswith("SOD:"):
            continue
        parts = person_key[4:].split("|")
        if len(parts) < 2:
            continue
        surname, given = norm_token(parts[0]), norm_token(parts[1])
        if not surname or not given:
            continue
        start = parse_iso(record.get("service_start_min"))
        end = parse_iso(record.get("service_end_max"))
        if start is None or end is None:
            first_bounds = quarter_bounds(first_q)
            last_bounds = quarter_bounds(last_q)
            if first_bounds is None or last_bounds is None:
                continue
            start, end = first_bounds[0], last_bounds[1]
        index[bioguide].append(
            {
                "surname": surname,
                "given": given,
                "start": start,
                "end": end,
                "office_key": office_key,
                "span_id": record.get("span_id"),
                "first_report_quarter": first_q,
                "last_report_quarter": last_q,
                "titles": list(record.get("titles") or [])[:MAX_EVIDENCE_EXAMPLES],
            }
        )
    return dict(index), present, (min_quarter or "", max_quarter or "")


def senate_office_matches_member(
    office_raw: str, candidate: Mapping[str, Any], table: Mapping[str, Sequence[str]]
) -> bool:
    """Does this free-text Senate payroll office name the given roster member?

    STRICT and directional: the office string must contain the member's roster
    surname as a CONTIGUOUS token subsequence (so 'Cortez Masto', 'Van Hollen'
    and 'Blunt Rochester' survive, which a last-token rule silently loses) AND
    one of the member's own first-name forms as a token.  Both sides are
    accent-folded.  There is no edit-distance step, so OCR-damaged office
    strings ('SENATOR RANDP AUL', 'SENATOR BRIANS CHATZ') simply do not match
    and are reported as unmatched rather than guessed at.
    """

    tokens = name_tokens(office_raw)
    if not tokens or tokens[0] != "SENATOR":
        return False
    tokens = tokens[1:]
    surname_tokens = [norm_token(t) for t in candidate.get("last_tokens") or []]
    surname_tokens = [t for t in surname_tokens if t]
    if not surname_tokens:
        return False
    folded = [norm_token(t) for t in tokens]
    width = len(surname_tokens)
    if not any(
        folded[i : i + width] == surname_tokens for i in range(0, len(folded) - width + 1)
    ):
        return False
    forms = candidate_first_name_forms(candidate, table)
    return any(fold_name(token) in forms for token in tokens)


def load_senate_office_index(
    path: Path,
    targets: set[str],
    by_bioguide: Mapping[str, Mapping[str, Any]],
    table: Mapping[str, Sequence[str]],
) -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[str]],
    dict[str, Any],
    tuple[date | None, date | None],
]:
    """Two passes.  Pass 1 enumerates the distinct 'SENATOR ...' office strings
    and maps each to the target bioguides it names.  Pass 2 collects payee rows
    only for offices that map to exactly one target."""

    office_counts: Counter[str] = Counter()
    corpus_start: date | None = None
    corpus_end: date | None = None
    for record in read_rows(path):
        office_raw = record.get("office_raw")
        if isinstance(office_raw, str) and office_raw.upper().startswith("SENATOR"):
            office_counts[office_raw] += 1
        start = parse_iso(record.get("report_period_start"))
        end = parse_iso(record.get("report_period_end"))
        if start and (corpus_start is None or start < corpus_start):
            corpus_start = start
        if end and (corpus_end is None or end > corpus_end):
            corpus_end = end

    office_to_bioguides: defaultdict[str, list[str]] = defaultdict(list)
    for office_raw in sorted(office_counts):
        for bioguide in sorted(targets):
            candidate = by_bioguide.get(bioguide)
            if candidate is None:
                continue
            if senate_office_matches_member(office_raw, candidate, table):
                office_to_bioguides[office_raw].append(bioguide)

    unique_offices = {
        office: bios[0]
        for office, bios in office_to_bioguides.items()
        if len(bios) == 1
    }
    ambiguous = {
        office: bios for office, bios in office_to_bioguides.items() if len(bios) > 1
    }

    index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in read_rows(path):
        office_raw = record.get("office_raw")
        bioguide = unique_offices.get(office_raw) if isinstance(office_raw, str) else None
        if bioguide is None:
            continue
        given, surname = split_payroll_comma_name(record.get("payee_name_raw"))
        if not given or not surname:
            continue
        windows: list[tuple[date, date]] = []
        for interval in record.get("date_intervals") or []:
            start = parse_iso(interval.get("start"))
            end = parse_iso(interval.get("end"))
            if start and end and end >= start:
                windows.append((start, end))
        if not windows:
            start = parse_iso(record.get("report_period_start"))
            end = parse_iso(record.get("report_period_end"))
            if start and end and end >= start:
                windows.append((start, end))
        if not windows:
            continue
        for start, end in windows:
            index[bioguide].append(
                {
                    "surname": surname,
                    "given": given,
                    "start": start,
                    "end": end,
                    "office_raw": office_raw,
                    "candidate_id": record.get("candidate_id"),
                    "title": record.get("title_candidate"),
                }
            )

    stats = {
        "distinct_senator_offices_in_corpus": len(office_counts),
        "offices_matched_to_exactly_one_target": len(unique_offices),
        "offices_matched_to_more_than_one_target": len(ambiguous),
        "target_bioguides_with_a_matched_office": len(set(unique_offices.values())),
        "unmatched_senator_offices": len(office_counts) - len(office_to_bioguides),
    }
    return dict(index), {k: sorted(v) for k, v in ambiguous.items()}, stats, (
        corpus_start,
        corpus_end,
    )


# ---------------------------------------------------------------------------
# Name binding between the filer and a payroll payee
# ---------------------------------------------------------------------------
def payee_name_matches(
    filer_given: str,
    filer_surname: str,
    entry: Mapping[str, Any],
    table: Mapping[str, Sequence[str]],
) -> str | None:
    """Strict name binding.  Surname must be equal on the normalized form.
    Given name must be equal, or equal after nickname-table expansion (the
    same table, multi-formal forms already dropped).  Returns the method or
    None."""

    if entry["surname"] != filer_surname:
        return None
    if entry["given"] == filer_given:
        return "EXACT_SURNAME_AND_GIVEN"
    left = nickname_expansions(filer_given, table)
    right = nickname_expansions(entry["given"], table)
    if left & right:
        return "SURNAME_AND_GIVEN_VIA_NICKNAME_TABLE"
    return None


def cross_check_episode(
    *,
    bioguide: str | None,
    filer_given: str | None,
    filer_surname: str | None,
    start_year: int,
    end_year: int,
    chambers: Sequence[str],
    house_index: Mapping[str, Sequence[Mapping[str, Any]]],
    house_present: set[str],
    senate_index: Mapping[str, Sequence[Mapping[str, Any]]],
    table: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """The four-way payroll cross-check for one released episode."""

    declared_start = date(start_year, 1, 1)
    declared_end = date(end_year, 12, 31)
    result: dict[str, Any] = {
        "chambers_checked": [],
        "declared_window_end": declared_end.isoformat(),
        "declared_window_start": declared_start.isoformat(),
        "evidence": [],
        "filer_given_normalized": filer_given,
        "filer_surname_normalized": filer_surname,
        "house_office_key": f"HON:{bioguide}" if bioguide else None,
        "house_office_present_in_corpus": (
            bioguide in house_present if bioguide else None
        ),
        "name_found_in_declared_office": False,
        "name_found_with_period_overlap": False,
        "name_match_method": None,
        "reason": "",
        "status": "NOT_CHECKED_MEMBER_UNRESOLVED",
        "window_reachable_chambers": [],
    }
    if bioguide is None:
        result["reason"] = "member did not resolve to a bioguide by strict roster match"
        return result
    corpora = {
        "house": (HOUSE_CORPUS_START, HOUSE_CORPUS_END),
        "senate": (SENATE_CORPUS_START, SENATE_CORPUS_END),
    }
    chambers = list(chambers) or ["house", "senate"]
    result["chambers_checked"] = sorted(chambers)
    reachable = [
        chamber
        for chamber in chambers
        if intervals_overlap(
            declared_start, declared_end, corpora[chamber][0], corpora[chamber][1]
        )
    ]
    result["window_reachable_chambers"] = sorted(reachable)

    found_any = False
    found_overlap = False
    evidence: list[dict[str, Any]] = []
    method: str | None = None
    # A filer whose own display name carries no usable given/surname pair
    # cannot be bound to any payee.  That is recorded as an absence with its
    # own reason -- but the window fields are still filled in above, so
    # OFFICE_OUT_OF_CORPUS_WINDOW keeps its precedence and the row stays
    # internally consistent with every other row.
    unusable_filer_name = not filer_given or not filer_surname
    for chamber in () if unusable_filer_name else sorted(set(chambers)):
        entries = (
            house_index.get(bioguide, ())
            if chamber == "house"
            else senate_index.get(bioguide, ())
        )
        for entry in entries:
            hit = payee_name_matches(filer_given, filer_surname, entry, table)
            if hit is None:
                continue
            found_any = True
            if method is None or hit == "EXACT_SURNAME_AND_GIVEN":
                method = hit
            overlaps = intervals_overlap(
                declared_start, declared_end, entry["start"], entry["end"]
            )
            found_overlap = found_overlap or overlaps
            if len(evidence) < MAX_EVIDENCE_EXAMPLES or overlaps:
                evidence.append(
                    {
                        "chamber": chamber,
                        "match_method": hit,
                        "office": entry.get("office_key") or entry.get("office_raw"),
                        "payroll_end": entry["end"].isoformat(),
                        "payroll_start": entry["start"].isoformat(),
                        "period_overlaps_declared_window": overlaps,
                        "record_id": entry.get("span_id") or entry.get("candidate_id"),
                    }
                )
    evidence.sort(
        key=lambda item: (
            not item["period_overlaps_declared_window"],
            item["payroll_start"],
            str(item["record_id"]),
        )
    )
    result["evidence"] = evidence[:MAX_EVIDENCE_EXAMPLES]
    result["name_found_in_declared_office"] = found_any
    result["name_found_with_period_overlap"] = found_overlap
    result["name_match_method"] = method

    if not reachable:
        result["status"] = "OFFICE_OUT_OF_CORPUS_WINDOW"
        result["reason"] = (
            "the declared years do not overlap the payroll corpus for any chamber the "
            "member served in across that window; the assertion is unreachable by the "
            "evidence on disk, which is not a finding against the assertion"
        )
        return result
    if found_overlap:
        result["status"] = "CONFIRMED_BY_PAYROLL"
        result["reason"] = (
            "the filer name appears in the declared member office with a payroll period "
            "overlapping the declared years"
        )
        return result
    if found_any:
        result["status"] = "NAME_FOUND_PERIOD_MISMATCH"
        result["reason"] = (
            "the filer name appears in the declared member office but no payroll period "
            "overlaps the declared years"
        )
        return result
    result["status"] = "NAME_ABSENT_FROM_DECLARED_OFFICE"
    result["reason"] = (
        "the filer display name does not split into a usable given/surname pair, so no "
        "payroll name binding is possible"
        if unusable_filer_name
        else "the declared window is reachable by the corpus and the filer name does not "
        "appear in the declared member office"
    )
    return result


# ---------------------------------------------------------------------------
# The same-string binding predicate (R1)
# ---------------------------------------------------------------------------
def same_string_binding(record: Mapping[str, Any]) -> tuple[bool, dict[str, Any]]:
    """R1.  All three mentions present, and all three spans resolving inside
    the single ``claim_text`` with exact substring equality."""

    claim_text = record.get("claim_text")
    detail: dict[str, Any] = {
        "date_span": None,
        "office_span": None,
        "role_span": None,
        "source_string_length": len(claim_text) if isinstance(claim_text, str) else None,
        "verified": False,
        "verification_method": (
            "each mention span resolves to its own text inside one claim_text"
        ),
    }
    if not isinstance(claim_text, str) or not claim_text:
        return False, detail
    pairs = (
        ("role_span", record.get("role_title_mention") or {}),
        ("office_span", record.get("office_employer_mention") or {}),
        ("date_span", record.get("date_range_mention") or {}),
    )
    ok = True
    for key, mention in pairs:
        text = mention.get("text")
        start, end = mention.get("span_start"), mention.get("span_end")
        if not isinstance(text, str) or not text:
            ok = False
            continue
        if not isinstance(start, int) or not isinstance(end, int):
            ok = False
            continue
        detail[key] = [start, end]
        if not (0 <= start < end <= len(claim_text)):
            ok = False
            continue
        if claim_text[start:end] != text:
            ok = False
    detail["verified"] = ok
    return ok, detail


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def resolve_paths(live_root: Path) -> dict[str, Path]:
    audits = live_root / "audits" / "staffer_network"
    reference = live_root / "data" / "staffer_network" / "reference"
    roster_dir = reference / "congress-legislators" / ROSTER_SNAPSHOT
    return {
        "blockers": audits
        / "lda_conservative_bounded_episode_candidates_20260901_b"
        / "lda_conservative_bounded_episode_blockers.ndjson.gz",
        "blockers_receipt": audits
        / "lda_conservative_bounded_episode_candidates_20260901_b"
        / "lda_conservative_bounded_episode_receipt.json",
        "house_spans": audits
        / "house_personnel_ledger_20260902_v3_primary"
        / "house_person_office_spans.ndjson.gz",
        "house_receipt": audits
        / "house_personnel_ledger_20260902_v3_primary"
        / "house_personnel_ledger_receipt.json",
        "lda_people": audits
        / "lda_employment_materialization_20260831_v2"
        / "lda_employment_people.ndjson.gz",
        "lda_resolution": audits
        / "payroll_name_resolution_20260902_v1_primary"
        / "lda_resolution.ndjson.gz",
        "lda_spine_links": audits
        / "hill_personnel_spine_20260902_v3_primary"
        / "lda_spine_links.ndjson.gz",
        "nicknames": reference / "first_name_nicknames_v1.json",
        "roster_current": roster_dir / "legislators-current.yaml",
        "roster_historical": roster_dir / "legislators-historical.yaml",
        "schema": live_root
        / "fec"
        / "staffer_network"
        / "schemas"
        / "a6_prose_release_episode.schema.json",
        "senate_candidates": audits
        / "official_senate_payroll_2011_2026_employment_scope_v1"
        / "senate_payroll_employment_candidates_2011_2026.ndjson.gz",
        "senate_receipt": audits
        / "official_senate_payroll_2011_2026_employment_scope_v1"
        / "senate_payroll_employment_scope_receipt.json",
    }


def classify_rows(
    source_rows: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Counter]:
    """Apply R1-R5 and split the pool into released and excluded."""

    released: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    funnel: Counter = Counter()
    for record in source_rows:
        funnel["input_near_candidate_rows"] += 1
        mention = record.get("office_employer_mention") or {}
        dates = record.get("date_range_mention") or {}
        reasons = set(record.get("rejection_reasons") or [])

        bound, binding_detail = same_string_binding(record)
        entity_class = mention.get("entity_class")
        releasable_entity = entity_class in RELEASABLE_ENTITY_CLASSES
        start_year = dates.get("explicit_start_year")
        end_year = dates.get("explicit_end_year")
        both_years = isinstance(start_year, int) and isinstance(end_year, int)
        blocking = sorted(reasons & set(EXCLUDING_BLOCKERS))
        year_order_ok = both_years and int(start_year) <= int(end_year)

        if bound:
            funnel["r1_same_string_bound"] += 1
        if releasable_entity:
            funnel["r2_member_office_or_committee"] += 1
        if both_years:
            funnel["r3_both_years_explicit"] += 1
        if not blocking:
            funnel["r4_no_content_specific_blocker"] += 1
        if year_order_ok:
            funnel["r5_year_order_ok"] += 1
        if releasable_entity and both_years:
            funnel["r2_and_r3"] += 1

        failures: list[str] = []
        if not bound:
            failures.append("R1_SAME_STRING_BINDING_NOT_ESTABLISHED")
        if not releasable_entity:
            failures.append("R2_OFFICE_NOT_MEMBER_OFFICE_OR_COMMITTEE")
        if not both_years:
            failures.append("R3_YEARS_NOT_BOTH_EXPLICIT")
        for flag in blocking:
            failures.append(f"R4_{flag}")
        if both_years and not year_order_ok:
            failures.append("R5_START_YEAR_AFTER_END_YEAR")

        if failures:
            excluded.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "canonical_identity_decision": "NOT_ADJUDICATED",
                    "claim_id": str(
                        (record.get("source_pointer") or {}).get("claim_id") or ""
                    ),
                    "exclusion_reasons": sorted(failures),
                    "lda_source_person_id": str(record["lda_source_person_id"]),
                    "office_entity_class": entity_class,
                    "release_decision": "NOT_RELEASED",
                    "review_status": "REVIEW_REQUIRED",
                    "rule_version": RULE_VERSION,
                    "schema_id": EXCLUSION_SCHEMA,
                    "source_claim_row_ordinal": (record.get("source_pointer") or {}).get(
                        "source_claim_row_ordinal"
                    ),
                    "upstream_rejection_reasons": sorted(reasons),
                }
            )
            for failure in failures:
                funnel[f"excluded_{failure}"] += 1
            continue
        funnel["released"] += 1
        released.append({"record": record, "binding": binding_detail})
    return released, excluded, funnel


def build(
    live_root: Path,
    out_dir: Path,
    run_id: str,
    *,
    validate_schema: bool = True,
) -> dict[str, Any]:
    paths = resolve_paths(live_root)
    for key, path in paths.items():
        if not path.exists():
            raise GateFailure(f"required input is missing: {key}: {path}")
    refuse_non_empty(out_dir)

    nickname_table, nickname_stats = load_nickname_table(paths["nicknames"])
    roster_by_surname, roster_by_bioguide = load_roster(paths["roster_current"].parent)

    display_names: dict[str, str] = {}
    for person in read_rows(paths["lda_people"]):
        display_names[str(person["lda_source_person_id"])] = str(
            person.get("display_name") or ""
        )

    source_rows = list(read_rows(paths["blockers"]))
    released, excluded, funnel = classify_rows(source_rows)

    # ---- member resolution -------------------------------------------------
    resolution_methods: Counter = Counter()
    staged: list[dict[str, Any]] = []
    for item in released:
        record = item["record"]
        mention = record["office_employer_mention"]
        dates = record["date_range_mention"]
        role = record.get("role_title_mention") or {}
        entity_class = mention.get("entity_class")
        office_text = str(mention.get("text") or "")
        start_year = int(dates["explicit_start_year"])
        end_year = int(dates["explicit_end_year"])
        window_start = date(start_year, 1, 1)
        window_end = date(end_year, 12, 31)

        first = surname = None
        if entity_class == "MEMBER_OFFICE_CANDIDATE":
            for pattern in (TITLE_RE, OFFICE_RE):
                match = pattern.search(office_text)
                if match:
                    first, surname = extract_surname_first(match.group(1))
                    if surname:
                        break
            bioguide, method = resolve_member_bioguide(
                first,
                surname,
                roster_by_surname,
                nickname_table,
                chamber=chamber_hint(office_text),
                window_start=window_start,
                window_end=window_end,
            )
        else:
            bioguide, method = None, "NOT_A_MEMBER_OFFICE"
        resolution_methods[method] += 1
        chambers = (
            declared_chambers(roster_by_bioguide[bioguide], window_start, window_end)
            if bioguide
            else []
        )
        staged.append(
            {
                "record": record,
                "binding": item["binding"],
                "bioguide": bioguide,
                "method": method,
                "first": first,
                "surname": surname,
                "chambers": chambers,
                "start_year": start_year,
                "end_year": end_year,
                "office_text": office_text,
                "role": role,
                "entity_class": entity_class,
            }
        )

    targets = {item["bioguide"] for item in staged if item["bioguide"]}

    # ---- payroll indexes ---------------------------------------------------
    house_index, house_present, house_quarters = load_house_office_index(
        paths["house_spans"], targets
    )
    senate_index, senate_ambiguous, senate_stats, senate_window = (
        load_senate_office_index(
            paths["senate_candidates"], targets, roster_by_bioguide, nickname_table
        )
    )

    # Gate the declared corpus windows against what the corpora actually carry.
    observed_house = quarter_bounds(house_quarters[0]), quarter_bounds(house_quarters[1])
    if observed_house[0] is None or observed_house[1] is None:
        raise GateFailure("could not derive the House corpus quarter range")
    if observed_house[0][0] != HOUSE_CORPUS_START or observed_house[1][1] != HOUSE_CORPUS_END:
        raise GateFailure(
            "House corpus window moved: expected "
            f"{HOUSE_CORPUS_START}..{HOUSE_CORPUS_END}, observed "
            f"{observed_house[0][0]}..{observed_house[1][1]}"
        )
    if senate_window[0] != SENATE_CORPUS_START or senate_window[1] != SENATE_CORPUS_END:
        raise GateFailure(
            "Senate corpus window moved: expected "
            f"{SENATE_CORPUS_START}..{SENATE_CORPUS_END}, observed "
            f"{senate_window[0]}..{senate_window[1]}"
        )

    # ---- emit --------------------------------------------------------------
    cross_check_counts: Counter = Counter()
    episodes: list[dict[str, Any]] = []
    for item in staged:
        record = item["record"]
        pointer = record.get("source_pointer") or {}
        person = str(record["lda_source_person_id"])
        display_name = display_names.get(person, "")
        filer_given, filer_surname = split_display_name(display_name)
        cross = cross_check_episode(
            bioguide=item["bioguide"],
            filer_given=filer_given,
            filer_surname=filer_surname,
            start_year=item["start_year"],
            end_year=item["end_year"],
            chambers=item["chambers"],
            house_index=house_index,
            house_present=house_present,
            senate_index=senate_index,
            table=nickname_table,
        )
        cross_check_counts[cross["status"]] += 1
        role = item["role"]
        dates = record["date_range_mention"]
        mention = record["office_employer_mention"]
        episodes.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "claim_id": str(pointer.get("claim_id") or ""),
                "date_range_text": dates.get("text"),
                "end_year": item["end_year"],
                "filer_display_name": display_name,
                "lda_source_person_id": person,
                "member_bioguide": item["bioguide"],
                "member_chambers_in_declared_window": item["chambers"],
                "member_given_text": item["first"],
                "member_resolution_method": item["method"],
                "member_surname_text": item["surname"],
                "office_entity_class": item["entity_class"],
                "office_pattern_id": mention.get("pattern_id"),
                "office_text": item["office_text"],
                "payroll_cross_check": cross,
                "precision": "year",
                "review_status": "REVIEW_REQUIRED",
                "role_generic_title_risk": bool(role.get("generic_title_risk")),
                "role_pattern_id": role.get("pattern_id"),
                "role_text": role.get("text"),
                "rule_version": RULE_VERSION,
                "run_id": run_id,
                "same_string_binding": item["binding"],
                "schema_id": EPISODE_SCHEMA,
                "single_author": True,
                "source_claim_row_ordinal": pointer.get("source_claim_row_ordinal"),
                "source_filing_years": list(pointer.get("source_filing_years") or []),
                "source_string": record.get("claim_text"),
                "source_string_sha256": hashlib.sha256(
                    str(record.get("claim_text") or "").encode("utf-8")
                ).hexdigest(),
                "start_year": item["start_year"],
                "temporal_semantics": "ASSERTED_EPISODE",
                "upstream_rejection_reasons": sorted(
                    record.get("rejection_reasons") or []
                ),
            }
        )

    episodes.sort(
        key=lambda row: (
            row["source_claim_row_ordinal"] is None,
            row["source_claim_row_ordinal"] or 0,
            row["claim_id"],
        )
    )
    excluded.sort(
        key=lambda row: (
            row["source_claim_row_ordinal"] is None,
            row["source_claim_row_ordinal"] or 0,
            row["claim_id"],
        )
    )

    # ---- fail-closed pins -------------------------------------------------
    for row in episodes:
        if (
            row["canonical_eligible"] is not False
            or row["canonical_employment_promoted"] is not False
            or row["canonical_identity_decision"] != "NOT_ADJUDICATED"
            or row["review_status"] != "REVIEW_REQUIRED"
            or row["single_author"] is not True
            or row["precision"] != "year"
            or row["temporal_semantics"] != "ASSERTED_EPISODE"
            or row["same_string_binding"]["verified"] is not True
        ):
            raise GateFailure(f"emitted row violates a release pin: {row['claim_id']}")
        if row["start_year"] > row["end_year"]:
            raise GateFailure(f"emitted row has reversed years: {row['claim_id']}")

    if validate_schema:
        schema = json.loads(paths["schema"].read_text(encoding="utf-8"))
        if schema.get("$id") != EPISODE_SCHEMA:
            raise GateFailure(
                f"episode schema $id mismatch: {schema.get('$id')!r} != {EPISODE_SCHEMA!r}"
            )
        validate_schema_definition(schema)
        for row in episodes:
            validate_instance(row, schema, _schema_checked=True)

    # ---- coverage ----------------------------------------------------------
    linked = set()
    for row in read_rows(paths["lda_spine_links"]):
        if row.get("link_status") == "LINKED_BY_PAYROLL_KEY":
            linked.add(str(row["lda_source_person_id"]))
    resolved = set()
    resolution_universe = set()
    for row in read_rows(paths["lda_resolution"]):
        resolution_universe.add(str(row["lda_source_person_id"]))
        if row.get("status") in ("RESOLVED_R1", "RESOLVED_R2"):
            resolved.add(str(row["lda_source_person_id"]))
    covered_people = {row["lda_source_person_id"] for row in episodes}
    already = linked | resolved
    newly = sorted(covered_people - already)

    outputs = {
        "episodes": write_ndjson_gz(out_dir / EPISODE_FILE, episodes),
        "exclusions": write_ndjson_gz(out_dir / EXCLUSION_FILE, excluded),
    }

    # A person can file the same assertion in several years, so the row count
    # over-counts episodes.  Both denominators are reported; neither is the
    # "right" one on its own.
    def episode_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            row["lda_source_person_id"],
            row["member_bioguide"] or row["office_text"],
            row["role_text"],
            row["start_year"],
            row["end_year"],
        )

    distinct_status: Counter = Counter()
    first_seen: dict[tuple[Any, ...], str] = {}
    for row in episodes:
        key = episode_key(row)
        if key not in first_seen:
            first_seen[key] = row["payroll_cross_check"]["status"]
            distinct_status[first_seen[key]] += 1

    confirmed_denominator = sum(
        cross_check_counts[key]
        for key in (
            "CONFIRMED_BY_PAYROLL",
            "NAME_ABSENT_FROM_DECLARED_OFFICE",
            "NAME_FOUND_PERIOD_MISMATCH",
            "OFFICE_OUT_OF_CORPUS_WINDOW",
        )
    )
    receipt = {
        "canonical_eligible_rows": sum(
            1 for row in episodes if row["canonical_eligible"] is not False
        ),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_lifetime_employment_assertions": 0,
        "corpus_windows": {
            "house_end": HOUSE_CORPUS_END.isoformat(),
            "house_observed_quarter_max": house_quarters[1],
            "house_observed_quarter_min": house_quarters[0],
            "house_start": HOUSE_CORPUS_START.isoformat(),
            "senate_end": SENATE_CORPUS_END.isoformat(),
            "senate_observed_period_end": (
                senate_window[1].isoformat() if senate_window[1] else None
            ),
            "senate_observed_period_start": (
                senate_window[0].isoformat() if senate_window[0] else None
            ),
            "senate_start": SENATE_CORPUS_START.isoformat(),
        },
        "coverage": {
            "distinct_episodes_in_release": len(first_seen),
            "distinct_lda_people_in_release": len(covered_people),
            "distinct_lda_people_with_a_confirmed_episode": len(
                {
                    row["lda_source_person_id"]
                    for row in episodes
                    if row["payroll_cross_check"]["status"] == "CONFIRMED_BY_PAYROLL"
                }
            ),
            "distinct_lda_people_newly_reachable": len(newly),
            "lda_people_already_linked_or_resolved": len(already),
            "lda_people_linked_by_spine": len(linked),
            "lda_people_resolved_r1_r2": len(resolved),
            "lda_resolution_universe": len(resolution_universe),
            "newly_reachable_sample": newly[:20],
        },
        "cross_check": {
            "absent_diagnostics": {
                "note": (
                    "NAME_ABSENT_FROM_DECLARED_OFFICE is a floor, not a verdict: these two "
                    "sub-counts are rows where the corpus itself cannot see the office"
                ),
                "rows_absent_total": cross_check_counts["NAME_ABSENT_FROM_DECLARED_OFFICE"],
                "rows_absent_with_house_office_missing_from_corpus": sum(
                    1
                    for row in episodes
                    if row["payroll_cross_check"]["status"]
                    == "NAME_ABSENT_FROM_DECLARED_OFFICE"
                    and row["payroll_cross_check"]["house_office_present_in_corpus"] is False
                ),
                "rows_absent_with_senate_only_reachable_window": sum(
                    1
                    for row in episodes
                    if row["payroll_cross_check"]["status"]
                    == "NAME_ABSENT_FROM_DECLARED_OFFICE"
                    and row["payroll_cross_check"]["window_reachable_chambers"] == ["senate"]
                ),
            },
            "counts": {key: cross_check_counts[key] for key in CROSS_CHECK_STATUSES},
            "counts_by_distinct_episode": dict(sorted(distinct_status.items())),
            "denominator_member_resolved": confirmed_denominator,
            "denominator_distinct_episodes": len(first_seen),
            "denominator_released": len(episodes),
            "precedence": (
                "OFFICE_OUT_OF_CORPUS_WINDOW dominates: when the declared years cannot "
                "reach the corpus, no period overlap is possible, so the other three "
                "labels would describe the corpus rather than the assertion"
            ),
            "senate_office_index": senate_stats,
            "senate_offices_ambiguous_across_targets": senate_ambiguous,
            "target_bioguides": len(targets),
            "target_bioguides_present_in_house_corpus": len(house_present),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_key": ["source_claim_row_ordinal", "claim_id"],
        },
        "filter_funnel": dict(sorted(funnel.items())),
        "generator": "audits/staffer_network/build_a6_prose_release.py",
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "member_resolution": {
            "methods": dict(sorted(resolution_methods.items())),
            "resolved": sum(1 for item in staged if item["bioguide"]),
            "resolved_distinct_bioguides": len(targets),
            "denominator_released": len(episodes),
            "denominator_member_office_rows": sum(
                1 for item in staged if item["entity_class"] == "MEMBER_OFFICE_CANDIDATE"
            ),
        },
        "nickname_table": nickname_stats,
        "outputs": outputs,
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "release_rule": {
            "adjudicated_universal_blockers": list(ADJUDICATED_UNIVERSAL_BLOCKERS),
            "excluding_blockers": list(EXCLUDING_BLOCKERS),
            "precision": "year",
            "releasable_entity_classes": sorted(RELEASABLE_ENTITY_CLASSES),
            "rules": [
                "R1 same-string binding: role, office and date spans all resolve inside one claim_text",
                "R2 office entity_class is MEMBER_OFFICE_CANDIDATE or COMMITTEE_CANDIDATE",
                "R3 both explicit years present",
                "R4 none of the four content-specific blockers is flagged",
                "R5 start_year <= end_year re-derived here",
            ],
            "single_author": True,
            "temporal_semantics": "ASSERTED_EPISODE",
        },
        "risk_notes": [
            "Years are never converted to day-level bounds; precision stays 'year'.",
            "Continuity between episodes is never inferred.",
            "A released row is what one filer asserted about themselves in one string; it is not an observation.",
            "OFFICE_OUT_OF_CORPUS_WINDOW is an expected outcome, not a failure: the House corpus starts 2009Q3 and the Senate corpus 2011-04-01, so any declared episode ending before those floors is structurally unreachable.",
            "NAME_ABSENT_FROM_DECLARED_OFFICE is bounded below by two known corpus defects, not by the assertion alone: House office keys carry a HONRAW: unresolved form for a minority of member-office rows, and Senate office strings carry OCR damage that this lane refuses to guess through.",
            "Committee-office rows can never be confirmed by this cross-check because both payroll corpora are indexed by member office here; they are reported as member-unresolved, not as absent.",
        ],
        "rule_version": RULE_VERSION,
        "run_id": run_id,
        "schema_id": RECEIPT_SCHEMA,
        "source": {key: hash_binding(path) for key, path in sorted(paths.items())},
        "stage_id": STAGE_ID,
        "status": "RELEASED_REVIEW_REQUIRED",
    }
    receipt["receipt_file"] = RECEIPT_FILE
    write_receipt(out_dir / RECEIPT_FILE, receipt)
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-root", type=Path, default=DEFAULT_LIVE_ROOT)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--no-schema-validation", action="store_true")
    args = parser.parse_args(argv)
    receipt = build(
        args.live_root,
        args.out_dir,
        args.run_id,
        validate_schema=not args.no_schema_validation,
    )
    summary = {
        "coverage": {
            key: value
            for key, value in receipt["coverage"].items()
            if key != "newly_reachable_sample"
        },
        "cross_check": receipt["cross_check"]["counts"],
        "excluded": receipt["outputs"]["exclusions"]["rows"],
        "member_resolution": receipt["member_resolution"],
        "released": receipt["outputs"]["episodes"]["rows"],
        "status": receipt["status"],
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
