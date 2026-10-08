#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the immutable Part A tiered corroboration sidecar.

The sidecar re-runs the 2026-09-01 confirmation ladder as a producer instead of
a measurement.  Every rule is ported from the ladder's own measurement scripts
under ``data/staffer_network/reviews/confirmation_ladder_20260901`` so that the
emitted tier counts reproduce the ladder document exactly (INV-5):

* ``build_ladder.py``            House name uniqueness (H1 reconstruction),
                                 office normalization incl. the U+2014 ``-Con.``
                                 row-continuation artifact and the U+2019
                                 apostrophe, the fixed committee/leadership
                                 phrase dictionary, and the chronology rule.
* ``ladder_senate_multisource.py`` Senate office-token rule, contiguity (split)
                                 rule, and the profile-employer cross-source
                                 office confirmation.
* ``ladder_registrant.py``       registrant-name normalization, LD-203 / FEC /
                                 LittleSis corroboration, and the Hill-versus-
                                 registrant order classification.
* ``part_a.py``                  the roster load and the nickname table used for
                                 strict-bioguide member resolution.
* ``part_b.py``                  the A6 same-string release rule.

Nothing here promotes anything.  Every emitted row carries
``review_status: REVIEW_REQUIRED``, ``canonical_eligible: false`` and
``canonical_employment_promoted: false``; the receipt pins both promotion
counters at zero.  The sidecar is consumed by nothing until Paul rules.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# INV-9: the reviewed interval algebra is reused, never reimplemented.  Both
# modules are import-safe; employment_history / employment_promotion /
# lda_composite_repair / lda_source_native_corpus are never imported.
from fec.staffer_network.intervals import UncertainInterval  # noqa: E402

import yaml  # noqa: E402


STAGE_ID = "tiered-corroboration-sidecar-part-a"
RECORD_SCHEMA = "staffer-network-tiered-person-office-record-v1"
SUMMARY_SCHEMA = "staffer-network-tiered-person-summary-v1"
EPISODE_SCHEMA = "staffer-network-filer-asserted-year-episode-v1"
REGISTRANT_SCHEMA = "staffer-network-registrant-side-record-v1"
RECEIPT_SCHEMA = "staffer-network-tiered-corroboration-receipt-v1"

RECORD_FILE = "tiered_person_office_records.ndjson.gz"
SUMMARY_FILE = "tiered_person_summary_25340.ndjson.gz"
EPISODE_FILE = "filer_asserted_year_episodes.ndjson.gz"
REGISTRANT_FILE = "registrant_side_records.ndjson.gz"
RECEIPT_FILE = "tiered_corroboration_receipt.json"

DEFAULT_LIVE_ROOT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
DEFAULT_APPDATA_ROOT = Path(r"C:\Users\pgoff\AppData\Local\Melange\staffer_network")
DEFAULT_RULE_VERSION = "tiered-corroboration-v2"

SEALED_QUEUE_ROWS = 25340

LANE_H1 = "house_sod_2009q3_2015q4"
LANE_H2 = "house_payroll_2016_2026"
LANE_SENATE = "senate_payroll_2011_2026"
HOUSE_LANES = (LANE_H1, LANE_H2)
ALL_LANES = (LANE_H1, LANE_H2, LANE_SENATE)
TIER_ORDER = ("L0", "L1", "L2", "L3", "L4", "L5")

# INV-10 dials.  UNTESTED DEFAULTS pending Paul's freeze (design section 6).
TIER_STRENGTH = {"L2": 0.25, "L3": 0.50, "L4": 0.75, "L5": 1.00}
R_STRENGTH = {"R0": 0.25, "R1": 0.50, "R2": 1.00}
TAU_DAYS = 365.2425
ALPHA = [0.70, 0.85, 0.95]
CHRONOLOGY_OFFSET_YEARS = 1
ENVELOPE_WIDENING_REPORTING_PERIODS = 1
MAX_EXAMPLES_PER_RECORD = 3
A6_EXCLUDED_FLAGS = (
    "AMBIGUOUS_ROLE_ABBREVIATION",
    "DATE_RANGE_REVERSED",
    "MENTION_SPANS_OVERLAP",
    "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED",
)
A6_RESOLVABLE_ENTITY_CLASSES = frozenset(
    {"COMMITTEE_CANDIDATE", "MEMBER_OFFICE_CANDIDATE"}
)

# INV-7 language law.  The tokens below may never appear in a field name, in a
# value this builder authors, or in receipt prose.  They may appear inside a
# value quoted verbatim from a source ledger -- a person's surname or an
# official office name is a fact, not framing -- and those positions are
# enumerated here, declared in the receipt, and re-derived by the verifier.
LANGUAGE_LAW_TOKENS = (
    "access",
    "causal",
    "friend",
    "ideolog",
    "influence",
    "predict",
)
VERBATIM_SOURCE_QUOTED_FIELDS = (
    "dated_registrant_evidence.matched_employer_name",
    "corroborating_payroll_office_examples[]",
    "ld203.matched_registrant_name",
    "member_surname_text",
    "office_key",
    "office_raw_examples[]",
    "office_text",
    "prong_evidence.multi_source.profile_matched_employer",
    "prong_evidence.multi_source.politico_matched_token",
    "prong_evidence.office_match.matched_token",
    "prong_evidence.office_match.office_normalized",
    "registrants[].employer_name",
    "registrants[].employer_name_normalized",
    "role_text",
    "title_examples[]",
)
LANGUAGE_LAW_POLICY = (
    "Banned tokens are rejected in every field name, in every value this builder "
    "authors, and in all receipt prose. Values quoted verbatim from a source "
    "ledger are exempt and enumerated in verbatim_source_quoted_fields; their "
    "token occurrences are counted and reported rather than suppressed, because "
    "editing an official office string or a person's own name would falsify the "
    "record. No display name is emitted by any Part A file."
)

INV5_EXPECTED = (
    (LANE_H1, "people", 2135),
    (LANE_H1, "L2_name_anchored", 1685),
    (LANE_H1, "L3_office_corroborated", 678),
    (LANE_H1, "L4_chronology_consistent", 678),
    (LANE_H1, "L4_person_office_spans", 861),
    (LANE_H2, "people", 3355),
    (LANE_H2, "L2_name_anchored", 2125),
    (LANE_H2, "L3_office_corroborated", 909),
    (LANE_H2, "L4_chronology_consistent", 858),
    (LANE_H2, "L4_person_office_spans", 1270),
    (LANE_SENATE, "people", 2798),
    (LANE_SENATE, "L2_name_anchored", 1710),
    (LANE_SENATE, "L3_office_corroborated", 667),
    (LANE_SENATE, "L4_chronology_consistent", 640),
    (LANE_SENATE, "S_split_clean", 2195),
    (LANE_SENATE, "L4_and_S", 470),
    (LANE_SENATE, "L4_and_S_person_office_spans", 754),
    ("house_union", "people", 4392),
    ("house_union", "L2_name_anchored", 2878),
    ("house_union", "L3_office_corroborated", 1195),
    ("house_union", "L4_chronology_consistent", 1137),
    ("payroll_union", "people", 6101),
    ("a6_near_candidates", "rows", 3090),
    ("a6_near_candidates", "resolvable_entity_and_both_years", 2525),
    ("registrant", "people_with_lda_registrant_association", 25340),
    ("registrant", "hill_and_registrant_people", 6101),
    ("registrant", "order_ORDERED", 4199),
    ("registrant", "order_OVERLAP_YEAR_GRAIN", 1821),
    ("registrant", "order_REVERSED", 81),
    ("registrant", "ld203_people", 22754),
    ("registrant", "ld203_same_year_name_equal", 22715),
    ("registrant", "ld203_extends_earlier_people", 269),
    ("registrant", "ld203_extends_later_people", 2121),
    ("registrant", "fec_same_year_name_equal", 36),
)


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
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_values(values: Iterable[str]) -> str:
    return hashlib.sha256(compact(sorted(set(values)))).hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
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


def copy_file_streamed(source: Path, destination: Path) -> None:
    """Copy ``source`` to ``destination`` without holding either file fully in RAM.

    STAFFC-13: the multi-GB v2 episode/registrant payloads were copied with a
    read_bytes()/write_bytes() pair -- non-atomic and fully buffered. This streams the
    copy in 1 MiB chunks into a temp file in the destination directory, then renames,
    matching write_ndjson_gz()/write_json_atomic()'s mkstemp + os.replace discipline.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with source.open("rb") as reader, temporary.open("wb") as writer:
            shutil.copyfileobj(reader, writer, length=1024 * 1024)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Name tokenization -- verbatim from build_ladder.py, which itself reproduces
# audits/staffer_network/match_lda_house_payroll.py so the H1 reconstruction
# uses the identical rule that built H2's own uniqueness fields.
# ---------------------------------------------------------------------------
TOKEN_RE = re.compile(r"[A-Z0-9]+")
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def name_tokens(value: str) -> tuple[str, ...]:
    normalized = (
        unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    )
    result = TOKEN_RE.findall(normalized.upper())
    while result and result[-1] in SUFFIXES:
        result.pop()
    return tuple(result)


def queue_name(value: str):
    values = name_tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def payroll_name(value: str):
    values = name_tokens(value)
    if len(values) < 2:
        return None
    surname, given = values[0], values[1]
    middle = tuple(item for item in values[2:] if item not in SUFFIXES)
    return given, surname, middle


def middle_compatible(left, right) -> bool:
    if not left or not right:
        return True
    return left[0][0] == right[0][0]


# ---------------------------------------------------------------------------
# House office normalization -- verbatim from build_ladder.py
# ---------------------------------------------------------------------------
YEAR_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s+")
WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")


def strip_year(value: str) -> str:
    return YEAR_PREFIX_RE.sub("", value or "")


def normalize_office(raw: str) -> str:
    """Strip a leading H1 year prefix, the House SOD U+2014 (em dash) + 'Con.'
    row-continuation suffix, normalize U+2019 to a plain apostrophe, expand '&'
    to ' AND ', collapse whitespace, upper."""

    value = strip_year(raw or "").strip()
    value = value.replace("\u2019", "'")
    value = re.sub(r"[\u2014']?\s*Con\.?\s*$", "", value, flags=re.IGNORECASE).strip()
    value = value.replace("&", " AND ")
    value = re.sub(r"\s+", " ", value).strip()
    return value.upper()


def is_hon_office(normalized: str) -> bool:
    return normalized.startswith("HON.") or normalized.startswith("HON ")


def extract_surname_forms(normalized: str) -> list[str]:
    rest = (
        normalized.split(".", 1)[1]
        if normalized.startswith("HON.")
        else normalized[3:]
    )
    raw_tokens = WORD_TOKEN_RE.findall(rest)
    cleaned = []
    for token in raw_tokens:
        trimmed = token.strip(".").strip(",")
        if not trimmed:
            continue
        if trimmed.upper() in SUFFIXES:
            continue
        cleaned.append(trimmed)
    if not cleaned:
        return []
    surname = cleaned[-1]
    forms = {surname.upper()}
    if "-" in surname:
        for part in surname.split("-"):
            if len(part) > 2:
                forms.add(part.upper())
    return sorted(forms)


def extract_hon_first_and_surname(normalized: str) -> tuple[str | None, str | None]:
    """Given a normalized 'HON. ...' office string return (first, surname) with
    bare single-letter initials and generational suffixes dropped."""

    rest = (
        normalized.split(".", 1)[1]
        if normalized.startswith("HON.")
        else normalized[3:]
    )
    cleaned = []
    for token in WORD_TOKEN_RE.findall(rest):
        trimmed = token.strip(".").strip(",")
        if not trimmed or trimmed.upper() in SUFFIXES:
            continue
        if len(trimmed.replace(".", "")) <= 1:
            continue
        cleaned.append(trimmed)
    if not cleaned:
        return None, None
    surname = cleaned[-1]
    first = cleaned[0] if len(cleaned) >= 2 else None
    return first, surname


def office_group_key(office_raw: str) -> str:
    """Grouping key invariant to the inconsistent middle-initial punctuation the
    House SOD PDF extraction leaves behind ('HON. STENY H HOYER' versus
    'HON. STENY H. HOYER' across quarters for the same member)."""

    normalized = normalize_office(office_raw)
    if is_hon_office(normalized):
        forms = extract_surname_forms(normalized)
        primary = max(forms, key=len) if forms else normalized
        return f"HON:{primary}"
    return normalized


# Committee / leadership office family -> distinctive phrases.  Copied verbatim
# from build_ladder.py; families with no safely distinctive phrase are left
# unmapped and can never be corroborated by this rule.
COMMITTEE_KEYWORDS = {
    "TRANSPORTATION-INFRASTRUCTURE": ["transportation and infrastructure"],
    "COMMITTEE ON WAYS AND MEANS": ["ways and means"],
    "COMMITTEE ON JUDICIARY": ["judiciary"],
    "HOMELAND SECURITY": ["homeland security"],
    "COMMITTEE ON APPROPRIATIONS": ["appropriations"],
    "COMMITTEE ON ENERGY AND COMMERCE": ["energy and commerce"],
    "COMMITTEE ON FINANCIAL SERVICE": ["financial services"],
    "COMMITTEE ON FINANCIAL SERVICES": ["financial services"],
    "COMMITTEE ON AGRICULTURE": ["agriculture"],
    "OFFICE OF THE MAJORITY LEADER": ["majority leader"],
    "COMMITTEE ON NATURAL RESOURCES": ["natural resources"],
    "COMMITTEE ON BUDGET": ["committee on budget", "budget committee"],
    "COMMITTEE ON FOREIGN AFFAIRS": ["foreign affairs"],
    "ARMED SERVICES COMMITTEE": ["armed services"],
    "COMM ON EDUCATION AND WORKFORCE": ["education and workforce"],
    "COMMITTEE ON EDUCATION AND WORKFORCE": ["education and workforce"],
    "COMM-EDUCATION AND WORKFORCE-MIN": ["education and workforce"],
    "COMM ON EDUCATION AND LABOR": ["education and labor"],
    "EDUCATION AND LABOR": ["education and labor"],
    "OFFICE OF THE MAJORITY WHIP": ["majority whip"],
    "OFFICE OF THE MINORITY WHIP": ["minority whip"],
    "COMMITTEE ON RULES": ["committee on rules", "rules committee"],
    "OFFICE OF THE SPEAKER": ["office of the speaker", "speaker of the house"],
    "COMM ON SCIENCE, SPACE AND TECH": ["science, space", "science and technology"],
    "COMM ON SCIENCE AND TECHNOLOGY": ["science and technology"],
    "SCIENCE AND TECHNOLOGY": ["science and technology"],
    "COMM ON SCIENCE SPACE AND TECH": ["science, space", "science and technology"],
    "COMM ON SCIENCE SPACE AND TECH MAJ": ["science, space", "science and technology"],
    "HOUSE ADMINISTRATION": ["house administration"],
    "VETERANS' AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "VETERANS AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "COMMITTEE ON VETERANS AFFAIRS": ["veterans affairs", "veterans' affairs"],
    "REPUBLICAN CONFERENCE": ["republican conference"],
    "DEMOCRATIC CAUCUS": ["democratic caucus"],
    "COMMITTEE ON SMALL BUSINESS": ["small business"],
    "OFFICE OF THE MINORITY LEADER": ["minority leader"],
    "OFFICE OF THE PARLIAMENTARIAN": ["parliamentarian"],
    "INTELLIGENCE": [
        "intelligence committee",
        "select committee on intelligence",
        "permanent select committee on intelligence",
    ],
    "COMM ON OVRSIGHT AND GOVT REFORM": [
        "oversight and government reform",
        "oversight and reform",
    ],
    "OVERSIGHT AND GOVERNMENT REFORM": [
        "oversight and government reform",
        "oversight and reform",
    ],
    "COMM ON OVERSIGHT AND REFORM": [
        "oversight and government reform",
        "oversight and reform",
    ],
    "COMM-OVERSIGHT AND ACCOUNTABILITY": ["oversight and accountability"],
    "COMMITTEE ON OVERSIGHT AND ACCOUNTABILITY": ["oversight and accountability"],
    "SERGEANT AT ARMS": ["sergeant at arms"],
    "COMMITTEE ON ETHICS": ["committee on ethics"],
    "CHIEF ADMIN OFCR OF THE HOUSE": ["chief administrative officer"],
    "JOINT COMMMITTEE ON TAXATION": ["joint committee on taxation"],
    "REPUBLICAN STEERING COMMITTEE": ["republican steering committee"],
    "REPUBLICAN STUDY COMMITTEE": ["republican study committee"],
    "REPUBLICAN POLICY COMMITTEE": ["republican policy committee"],
    "OFFICE OF INSPECTOR GENERAL": ["inspector general"],
    "COMMITTEE ON BENGHAZI": ["benghazi"],
    "DEMOCRATIC STEERING AND POLICY": ["democratic steering"],
    "HOUSE CHILD CARE CENTER": ["child care center"],
    "LEGISLATIVE COUNSEL": ["legislative counsel"],
    "CLERK OF THE HOUSE": ["clerk of the house"],
    "ENERGY INDEP AND GLOBAL WARMING": ["global warming", "energy independence"],
    "ENERGY INDEPEN AND GLB WARMING": ["global warming", "energy independence"],
    "STANDARDS OF OFFICIAL CONDUCT": ["standards of official conduct"],
    "OFFICE OF THE HISTORIAN": ["office of the historian"],
    "OFFICE OF THE DEMOCRATIC WHIP": ["democratic whip"],
    "SELECT COMM ON JANUARY 6TH": [
        "january 6th",
        "select committee to investigate the january 6",
    ],
    "SELECT COMMITTEE COMPETITION US AND CHINA": [
        "strategic competition",
        "chinese communist party",
    ],
    "SEL COMM-COMPETITION US AND CHINA": [
        "strategic competition",
        "chinese communist party",
    ],
    "INTERPARLIAMENTARY AFFAIRS": ["interparliamentary"],
    "SELECT COMM - CLIMATE CRISIS": ["climate crisis"],
    "SELECT COMM-CLIMATE CRISIS": ["climate crisis"],
    "SELECT COMM - MODERNIZATION": ["modernization of congress"],
    "DIVERSITY AND INCLUSION": ["diversity and inclusion"],
    "CONGRESSIONAL BLACK CAUCUS": ["congressional black caucus"],
    "ASIAN PACIFIC AMERICAN CAUCUS": ["asian pacific american"],
    "NEW DEMOCRAT COALITION": ["new democrat coalition"],
    "OFFICE OF CONGRESSIONAL ETHICS": ["office of congressional ethics"],
    "CONGRESSIONAL HISPANIC CAUCUS": ["congressional hispanic caucus"],
    "CONGRESSIONAL PROGRESSIVE CAUCUS": ["congressional progressive caucus"],
    "EQUALITY CAUCUS": ["equality caucus"],
    "CONGRESSIONAL WESTERN CAUCUS": ["congressional western caucus"],
    "DEMOCRATIC WOMENS CAUCUS": ["democratic women's caucus", "democratic womens caucus"],
    "CONGRESSIONAL LABOR CAUCUS": ["congressional labor caucus"],
}

HOUSE_LEADERSHIP_FAMILIES = frozenset(
    {
        "ASIAN PACIFIC AMERICAN CAUCUS",
        "CONGRESSIONAL BLACK CAUCUS",
        "CONGRESSIONAL HISPANIC CAUCUS",
        "CONGRESSIONAL LABOR CAUCUS",
        "CONGRESSIONAL PROGRESSIVE CAUCUS",
        "CONGRESSIONAL WESTERN CAUCUS",
        "DEMOCRATIC CAUCUS",
        "DEMOCRATIC STEERING AND POLICY",
        "DEMOCRATIC WOMENS CAUCUS",
        "EQUALITY CAUCUS",
        "NEW DEMOCRAT COALITION",
        "OFFICE OF THE DEMOCRATIC WHIP",
        "OFFICE OF THE MAJORITY LEADER",
        "OFFICE OF THE MAJORITY WHIP",
        "OFFICE OF THE MINORITY LEADER",
        "OFFICE OF THE MINORITY WHIP",
        "OFFICE OF THE SPEAKER",
        "REPUBLICAN CONFERENCE",
        "REPUBLICAN POLICY COMMITTEE",
        "REPUBLICAN STEERING COMMITTEE",
        "REPUBLICAN STUDY COMMITTEE",
    }
)
HOUSE_ADMIN_FAMILIES = frozenset(
    {
        "CHIEF ADMIN OFCR OF THE HOUSE",
        "CLERK OF THE HOUSE",
        "CLOAKROOM PERSONNEL - MAJ",
        "CLOAKROOM PERSONNEL - MIN",
        "DIVERSITY AND INCLUSION",
        "DS-TRAINING AND PROGRAM DEVEL.",
        "GOVERNMENT CONTRIBUTIONS",
        "HOUSE CHILD CARE CENTER",
        "INTERPARLIAMENTARY AFFAIRS",
        "LAW REVISION COUNSEL",
        "LEGISLATIVE COUNSEL",
        "LEGISLATIVE FLOOR ACTIVITIES",
        "MINORITY EMPLOYEES",
        "OFFICE OF CONGRESSIONAL ETHICS",
        "OFFICE OF FINANCE",
        "OFFICE OF INSPECTOR GENERAL",
        "OFFICE OF THE HISTORIAN",
        "OFFICE OF THE PARLIAMENTARIAN",
        "OTHER ADMINISTRATION",
        "RC-TRAINING AND PROGRAM DEVEL.",
        "SALARIES OFFICERS AND EMPLOYEES",
        "SERGEANT AT ARMS",
        "TRANSITION AIDES",
    }
)
HOUSE_COMMITTEE_SHAPE_RE = re.compile(r"(?:^|\W)(COMM|COMMITTEE)(?:\W|$)")


def word_present(blob_casefolded: str, phrase_casefolded: str) -> bool:
    """Whole-word/phrase containment on a casefolded blob (build_ladder.py)."""

    pattern = (
        r"(?<![a-z0-9])" + re.escape(phrase_casefolded) + r"(?![a-z0-9])"
    )
    return re.search(pattern, blob_casefolded) is not None


def check_office_corroboration_house(
    office_raw: str, covered_blob_casefolded: str
) -> tuple[bool, str, str]:
    """Returns (corroborated, method, matched_form_or_family)."""

    normalized = normalize_office(office_raw)
    if not normalized:
        return False, "EMPTY_OFFICE", ""
    if is_hon_office(normalized):
        forms = extract_surname_forms(normalized)
        if not forms:
            return False, "HON_NO_SURNAME_PARSED", normalized
        for form in forms:
            if word_present(covered_blob_casefolded, form.lower()):
                return True, "MEMBER_SURNAME_MATCH", form
        return False, "MEMBER_SURNAME_NOT_FOUND", "/".join(forms)
    keywords = COMMITTEE_KEYWORDS.get(normalized)
    if not keywords:
        return False, "COMMITTEE_FAMILY_UNMAPPED", normalized
    for keyword in keywords:
        if word_present(covered_blob_casefolded, keyword.lower()):
            return True, "COMMITTEE_KEYWORD_MATCH", keyword
    return False, "COMMITTEE_KEYWORD_NOT_FOUND", normalized


def container_kind_house(office_raw: str) -> str:
    normalized = normalize_office(office_raw)
    if not normalized:
        return "unresolved"
    if is_hon_office(normalized):
        return "member_office"
    if normalized in HOUSE_LEADERSHIP_FAMILIES:
        return "leadership"
    if normalized in HOUSE_ADMIN_FAMILIES:
        return "admin"
    if normalized in COMMITTEE_KEYWORDS or HOUSE_COMMITTEE_SHAPE_RE.search(normalized):
        return "committee"
    return "unresolved"


# ---------------------------------------------------------------------------
# Senate office rule -- verbatim from ladder_senate_multisource.py
# ---------------------------------------------------------------------------
SENATE_SUFFIX_RE = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
SENATOR_RE = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_RE = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
COMMITTEE_STOPWORDS = {
    "JOINT", "SELECT", "SPECIAL", "STANDING", "SUB", "SUBCOMMITTEE",
    "COMMITTEE", "ON", "OF", "THE", "AND",
}
SENATE_LEADERSHIP_PHRASES = (
    "CAUCUS",
    "MAJORITY CONFERENCE",
    "MAJORITY LEADER",
    "MAJORITY WHIP",
    "MINORITY CONFERENCE",
    "MINORITY LEADER",
    "MINORITY WHIP",
    "PRES PRO TEM",
    "PRESIDENT PRO TEMPORE",
    "SECRETARY FOR THE MAJORITY",
    "SECRETARY FOR THE MINORITY",
    "VICE PRESIDENT",
)


def office_token_senate(office: str) -> str | None:
    """Exact O-rule token extraction for a Senate payroll office string."""

    upper = (office or "").strip().upper()
    senator = SENATOR_RE.match(upper)
    if senator:
        remainder = SENATE_SUFFIX_RE.sub("", senator.group(1)).strip()
        tokens = [t.strip(".,") for t in remainder.split() if t.strip(".,")]
        return tokens[-1] if tokens else None
    intern = INTERN_RE.match(upper)
    if intern:
        surname = intern.group(1).strip().strip(".,")
        return surname or None
    if "COMMITTEE" in upper:
        words = [w for w in re.findall(r"[A-Z]+", upper) if w not in COMMITTEE_STOPWORDS]
        return max(words, key=len) if words else None
    if upper == "APPROPRIATIONS":
        return upper
    return None


def whole_word_in(token: str | None, text_upper: str) -> bool:
    if not token:
        return False
    return re.search(r"\b" + re.escape(token) + r"\b", text_upper) is not None


def senate_member_first_and_surname(office: str) -> tuple[str | None, str | None]:
    upper = (office or "").strip().upper()
    senator = SENATOR_RE.match(upper)
    if senator:
        remainder = SENATE_SUFFIX_RE.sub("", senator.group(1)).strip()
        tokens = [t.strip(".,") for t in remainder.split() if t.strip(".,")]
        tokens = [t for t in tokens if len(t.replace(".", "")) > 1]
        if not tokens:
            return None, None
        surname = tokens[-1]
        first = tokens[0] if len(tokens) >= 2 else None
        return first, surname
    intern = INTERN_RE.match(upper)
    if intern:
        surname = intern.group(1).strip().strip(".,")
        return (None, surname) if surname else (None, None)
    return None, None


def container_kind_senate(office: str) -> str:
    upper = (office or "").strip().upper()
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


# House profile-matching token rule -- verbatim from ladder_senate_multisource.py
STOPWORDS_HOUSE = {
    "COMMITTEE", "COMM", "ON", "OF", "THE", "AND", "OFFICE", "CHIEF", "ADMIN",
    "ADMINISTRATION", "OFCR", "HOUSE", "SPEAKER", "SERVICE", "SERVICES",
}
PROFILE_YEAR_PREFIX_RE = re.compile(r"^(19|20)\d{2}\s+")


def office_token_house(office: str) -> list[str]:
    upper = (office or "").strip().upper()
    upper = PROFILE_YEAR_PREFIX_RE.sub("", upper)
    return [
        word
        for word in re.findall(r"[A-Z]+", upper)
        if word not in STOPWORDS_HOUSE and len(word) >= 4
    ]


# ---------------------------------------------------------------------------
# Registrant-name normalization -- verbatim from ladder_registrant.py
# ---------------------------------------------------------------------------
def norm_name(value: str | None) -> str:
    if not value:
        return ""
    value = value.casefold()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


# ---------------------------------------------------------------------------
# Roster + nickname table.
#
# generation v2 (2026-09-02, Paul's authorisation "Extend the nickname table,
# resolve Bill Nelson"): the nickname table is no longer a hardcoded literal.
# It is loaded from the hash-bound reference file
# data/staffer_network/reference/first_name_nicknames_v1.json (INV-3 input;
# see load_nickname_table / NICKNAME_TABLE_SCHEMA below).  Resolution also
# gained two capabilities beyond v1:
#   1. A roster candidate's ``name.nickname`` field and the first token of
#      ``name.official_full`` are now first-name resolution forms alongside
#      ``name.first`` (e.g. Bill Johnson's roster row already has
#      first="Bill", but J.D. Vance's has first="James David" and only
#      nickname="J.D." -- folding punctuation out of both sides lets "JD"
#      match "J.D.").
#   2. A NEW hard constraint (INV-6 extension): a resolved candidate must
#      have a term whose [start, end] overlaps the record's observation
#      window and whose ``type`` matches the chamber.  When exactly one
#      first-name match remains after that filter is applied to a surname
#      collision, the method is STRICT_ROSTER_SURNAME_FIRST_NAME_AND_TERM_
#      WINDOW; when a name match fails the window check outright, the reason
#      is TERM_WINDOW_MISMATCH.  This is what resolves "SENATOR BILL NELSON"
#      -- the roster has two Nelsons whose first name folds to
#      bill/william (N000032 and N000045), and only N000032 has a Senate
#      term overlapping the 2013 observation.
#
# Tier assignment (person_tier_letter / house_lane_tiers / senate_lane_tiers)
# never reads member_bioguide or member_resolution_method, so none of this
# changes any INV-5 ladder count -- it only changes what is recorded in the
# member_bioguide / member_resolution_method fields on already-tiered rows.
# ---------------------------------------------------------------------------
NICKNAME_TABLE_SCHEMA = "staffer-network-first-name-nickname-table-v1"
_TERM_TYPE_BY_CHAMBER = {"house": "rep", "senate": "sen"}


def load_nickname_table(path: Path) -> dict[str, tuple[str, ...]]:
    with path.open("r", encoding="utf-8") as stream:
        payload = json.load(stream)
    if payload.get("schema_id") != NICKNAME_TABLE_SCHEMA:
        raise GateFailure(
            f"nickname table schema mismatch: {path}: {payload.get('schema_id')!r}"
        )
    entries = payload.get("entries") or {}
    return {
        str(key).casefold(): tuple(str(v).casefold() for v in values)
        for key, values in entries.items()
    }


A6_TITLE_RE = re.compile(
    r'\b(?:Rep\.?|Sen\.?|Senator|Representative|Congressman|Congresswoman|Cong\.|Hon\.?)\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)
A6_OFFICE_RE = re.compile(
    r'\bOffice of(?:\s+(?:Sen\.?|Senator|Rep\.?|Representative|Congressman|Congresswoman))?\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)
A6_SUFFIX_TOKENS = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def fold_name(value: str | None) -> str:
    """Loose fold for first-name comparisons: casefold and drop every
    non-alphanumeric character, so 'J.D.' and 'JD' compare equal, and
    trailing/embedded periods on 'Ted.' or 'F.' no longer matter.
    """
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def nickname_expansions(
    value: str, nickname_table: Mapping[str, Sequence[str]]
) -> set[str]:
    """The folded value itself, plus every casefolded formal form the
    nickname table maps it to (a nickname may map to more than one formal
    name, e.g. 'jay' -> jason, james).
    """
    folded = fold_name(value)
    forms = {folded}
    for formal in nickname_table.get(folded, ()):
        forms.add(fold_name(formal))
    return forms


def candidate_first_name_forms(
    candidate: Mapping[str, Any], nickname_table: Mapping[str, Sequence[str]]
) -> set[str]:
    """Resolution forms for one roster candidate: their formal first name,
    the YAML ``name.nickname`` field when present, and the first token of
    ``name.official_full`` when present -- each expanded through the
    nickname table so a nickname spelled either side still lines up.
    """
    forms: set[str] = set()
    for raw in (candidate.get("first"), candidate.get("nickname")):
        if raw:
            forms |= nickname_expansions(str(raw), nickname_table)
    official_full = candidate.get("official_full")
    if official_full:
        tokens = str(official_full).split()
        if tokens:
            forms |= nickname_expansions(tokens[0], nickname_table)
    return forms


def first_name_matches(
    first: str,
    candidate: Mapping[str, Any],
    nickname_table: Mapping[str, Sequence[str]],
) -> bool:
    return bool(
        nickname_expansions(first, nickname_table)
        & candidate_first_name_forms(candidate, nickname_table)
    )


def candidate_has_overlapping_term(
    candidate: Mapping[str, Any],
    chamber: str | None,
    window_start: date | None,
    window_end: date | None,
) -> bool:
    """INV-6 term-window hard constraint.  ``chamber=None`` (used for A6
    filer-asserted mentions whose chamber cannot always be told from the
    matched title) skips the term-type check and only requires date overlap.
    A missing window (no observed periods to check against) is treated as
    "not applicable" so it never blocks a resolution the old, window-less
    rule would have made.
    """
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


def extract_surname_first(captured: str) -> tuple[str | None, str | None]:
    tokens = (captured or "").strip().rstrip(".,;").split()
    cleaned = []
    for token in tokens:
        trimmed = token.strip().rstrip(".,;")
        if trimmed.lower() in A6_SUFFIX_TOKENS:
            continue
        if len(trimmed.replace(".", "")) <= 1:
            continue
        cleaned.append(trimmed)
    if not cleaned:
        return None, None
    surname = cleaned[-1]
    first = cleaned[0] if len(cleaned) >= 2 else None
    return first, surname


def load_roster(
    directory: Path, *, counts: dict[str, int] | None = None
) -> dict[str, list[dict[str, Any]]]:
    by_surname: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        with (directory / filename).open("r", encoding="utf-8") as stream:
            people = yaml.safe_load(stream)
        for person in people:
            bioguide = (person.get("id") or {}).get("bioguide")
            if not bioguide:
                continue
            name = person.get("name") or {}
            years = []
            terms: list[dict[str, Any]] = []
            for term in person.get("terms") or []:
                try:
                    # str() tolerates a term date that YAML parsed as a date object
                    # rather than a string (STAFFC-19); a term that still fails --
                    # e.g. a missing start/end -- is counted, not silently dropped.
                    years.append((int(str(term["start"])[:4]), int(str(term["end"])[:4])))
                except Exception:
                    if counts is not None:
                        counts["roster_terms_unparseable"] = (
                            counts.get("roster_terms_unparseable", 0) + 1
                        )
                start_date = parse_iso(term.get("start"))
                end_date = parse_iso(term.get("end"))
                if start_date is not None and end_date is not None:
                    terms.append(
                        {"type": term.get("type"), "start": start_date, "end": end_date}
                    )
            if not years:
                continue
            by_surname[str(name.get("last", "")).upper()].append(
                {
                    "bioguide": bioguide,
                    "first": str(name.get("first", "")),
                    "nickname": name.get("nickname"),
                    "official_full": name.get("official_full"),
                    "min_year": min(y[0] for y in years),
                    "max_year": max(y[1] for y in years),
                    "terms": terms,
                }
            )
    return {key: sorted(value, key=lambda item: item["bioguide"]) for key, value in by_surname.items()}


def resolve_member_bioguide(
    first: str | None,
    surname: str | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nickname_table: Mapping[str, Sequence[str]],
    *,
    chamber: str | None,
    window_start: date | None,
    window_end: date | None,
) -> tuple[str | None, str]:
    """INV-6 strict-bioguide resolution.

    A bioguide is returned only when the roster surname matches exactly,
    either the first name matches one of the candidate's resolution forms
    (formal first name, YAML nickname field, or official_full's first
    token -- each nickname-table expanded) or the surname is unique with no
    first name in the office string, AND the candidate has a term whose type
    matches ``chamber`` (when given) and whose [start, end] overlaps
    [window_start, window_end] (when given).  When a surname collision is
    resolved only because the term window narrowed it to one candidate, the
    method is STRICT_ROSTER_SURNAME_FIRST_NAME_AND_TERM_WINDOW rather than
    STRICT_ROSTER_SURNAME_AND_FIRST_NAME.  Every other outcome keeps
    ``member_bioguide: null``.  No fuzzy join.
    """

    if not surname:
        return None, "UNRESOLVED_SURNAME_NOT_PARSED"
    candidates = roster.get(surname.upper())
    if not candidates:
        return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"
    if first:
        matched = [
            candidate
            for candidate in candidates
            if first_name_matches(first, candidate, nickname_table)
        ]
        if not matched:
            return None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
        if len(matched) == 1:
            candidate = matched[0]
            if candidate_has_overlapping_term(candidate, chamber, window_start, window_end):
                return candidate["bioguide"], "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
            return None, "TERM_WINDOW_MISMATCH"
        term_matched = [
            candidate
            for candidate in matched
            if candidate_has_overlapping_term(candidate, chamber, window_start, window_end)
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
# Reporting periods
# ---------------------------------------------------------------------------
QUARTER_RE = re.compile(r"^(\d{4})Q(\d)$")


def quarter_key(value: str | None) -> tuple[int, int] | None:
    match = QUARTER_RE.match(value or "")
    if not match:
        return None
    quarter = int(match.group(2))
    if quarter < 1 or quarter > 4:
        return None
    return int(match.group(1)), quarter


def quarter_ordinal(key: tuple[int, int]) -> int:
    return key[0] * 4 + (key[1] - 1)


def ordinal_to_quarter(ordinal: int) -> tuple[int, int]:
    return ordinal // 4, (ordinal % 4) + 1


def quarter_bounds(key: tuple[int, int]) -> tuple[date, date]:
    year, quarter = key
    start = date(year, 3 * quarter - 2, 1)
    if quarter == 4:
        end = date(year, 12, 31)
    else:
        end = date(year, 3 * quarter + 1, 1) - timedelta(days=1)
    return start, end


def quarters_contiguous(keys: Sequence[tuple[int, int]]) -> bool:
    ordered = sorted(keys)
    if len(ordered) <= 1:
        return True
    ordinals = [quarter_ordinal(key) for key in ordered]
    return all(
        ordinals[index + 1] - ordinals[index] == 1 for index in range(len(ordinals) - 1)
    )


def parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        year, month, day = (int(part) for part in value.split("-"))
        return date(year, month, day)
    except Exception:
        return None


def senate_window(day: date) -> tuple[date, date]:
    """Semiannual Senate report window containing ``day`` (Oct 1 - Mar 31 and
    Apr 1 - Sep 30)."""

    if day.month >= 10:
        return date(day.year, 10, 1), date(day.year + 1, 3, 31)
    if day.month <= 3:
        return date(day.year - 1, 10, 1), date(day.year, 3, 31)
    return date(day.year, 4, 1), date(day.year, 9, 30)


def senate_previous_window(window: tuple[date, date]) -> tuple[date, date]:
    return senate_window(window[0] - timedelta(days=1))


def senate_next_window(window: tuple[date, date]) -> tuple[date, date]:
    return senate_window(window[1] + timedelta(days=1))


def periods_contiguous(period_pairs: Sequence[tuple[date | None, date | None]]) -> bool:
    """Reference Senate split rule: every period's start equals the prior
    period's end plus one day (ladder_senate_multisource.py)."""

    for index in range(1, len(period_pairs)):
        previous_end = period_pairs[index - 1][1]
        current_start = period_pairs[index][0]
        if previous_end is None or current_start is None:
            return False
        if current_start != previous_end + timedelta(days=1):
            return False
    return True


def merge_runs(
    intervals: Sequence[tuple[date, date]]
) -> list[list[tuple[date, date]]]:
    """Group sorted date intervals into maximal runs, joining any pair that
    overlaps or is adjacent (next start <= previous end + 1 day)."""

    ordered = sorted(set(intervals))
    runs: list[list[tuple[date, date]]] = []
    for interval in ordered:
        if runs and interval[0] <= runs[-1][-1][1] + timedelta(days=1):
            runs[-1].append(interval)
        else:
            runs.append([interval])
    return runs


# ---------------------------------------------------------------------------
# Input binding
# ---------------------------------------------------------------------------
def input_paths(live_root: Path, appdata_root: Path) -> dict[str, Path]:
    lane = live_root / "audits" / "staffer_network"
    reference = live_root / "data" / "staffer_network" / "reference"
    roster_dir = (
        reference / "congress-legislators" / "750c0608efb6ef1fc3257ba72c99af3771d35088"
    )
    return {
        "a6_near_candidates": lane
        / "lda_conservative_bounded_episode_candidates_20260901_b"
        / "lda_conservative_bounded_episode_blockers.ndjson.gz",
        "a7_fec_employment_observations": lane
        / "a7_machine_local_source_inventory_20260901_primary"
        / "a7_fec_employment_observation_candidates.ndjson.gz",
        "a7_ld203_affiliations": lane
        / "a7_machine_local_source_inventory_20260901_primary"
        / "a7_ld203_affiliation_candidates.ndjson.gz",
        "a9_priority_sidecar": lane
        / "a9_a7_a8_priority_sidecar_20260901_primary"
        / "a9_a7_a8_priority_sidecar_25340.ndjson.gz",
        "employment_lookup_queue": appdata_root
        / "employment-lookup"
        / "generation-20260831T050000Z"
        / "employment_lookup_queue.ndjson.gz",
        "house_payroll_2016_2026": lane
        / "lda_house_payroll_matches_2016_2026"
        / "lda_house_payroll_match_candidates.ndjson.gz",
        "house_sod_2009q3_2015q4": lane
        / "house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
        / "house_sod_pdf_lda_name_match_candidates.ndjson.gz",
        "lda_registrant_employment_episodes": lane
        / "lda_registrant_employment_20260831"
        / "lda_registrant_employment_episodes.ndjson.gz",
        "linkedin_authenticated_evidence": lane
        / "linkedin_authenticated_evidence_20260901"
        / "linkedin_authenticated_evidence.ndjson",
        "littlesis_lda_history_candidates": lane
        / "littlesis_lda_history_candidates_20260831"
        / "littlesis_lda_history_candidates.ndjson.gz",
        "nickname_table": reference / "first_name_nicknames_v1.json",
        "politico_lda_employment_candidates": lane
        / "politico_lda_employment_candidates_20260831"
        / "politico_lda_employment_candidates.ndjson.gz",
        "rapid_structured_profile_evidence": lane
        / "rapid_structured_profile_evidence_20260901_current"
        / "rapid_structured_profile_evidence.ndjson",
        "roster_legislators_current": roster_dir / "legislators-current.yaml",
        "roster_legislators_historical": roster_dir / "legislators-historical.yaml",
        "senate_payroll_2011_2026": lane
        / "lda_senate_payroll_matches_2011_2026_v1"
        / "lda_senate_payroll_match_candidates.ndjson.gz",
        "v3_candidate_adjudication_decisions": lane
        / "employment_adjudication_generation_20260901_v3_primary"
        / "candidate_adjudication_decisions.ndjson.gz",
    }


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def load_queue(path: Path):
    by_person: dict[str, dict[str, Any]] = {}
    by_name_key: defaultdict[tuple[str, str], list[tuple[str, tuple[str, ...], str]]] = (
        defaultdict(list)
    )
    order: list[str] = []
    for row in read_rows(path):
        person = str(row["lda_source_person_id"])
        if person in by_person:
            raise GateFailure(f"duplicate queue person: {person}")
        values = row.get("covered_position_values") or []
        display_name = row.get("display_name") or ""
        by_person[person] = {
            "covered_blob_casefolded": " | ".join(values).casefold(),
            "covered_text_upper": " ".join(values).upper(),
            "covered_position_value_count": len(values),
            "covered_position_substantive": any((v or "").strip() for v in values),
            "filing_years": list(row.get("filing_years") or []),
        }
        order.append(person)
        parsed = queue_name(display_name)
        if parsed:
            given, surname, middle = parsed
            by_name_key[(given, surname)].append((person, middle, display_name))
    return by_person, by_name_key, order


def h1_name_uniqueness(payee_raw: str | None, by_name_key) -> tuple[int | None, int | None]:
    parsed = payroll_name(payee_raw or "")
    if not parsed:
        return None, None
    given, surname, middle = parsed
    candidates = [
        (person, display)
        for person, queue_middle, display in by_name_key.get((given, surname), [])
        if middle_compatible(queue_middle, middle)
    ]
    if not candidates:
        return None, None
    return len(candidates), len({display for _, display in candidates})


def year_of(value: str | None) -> int | None:
    match = re.match(r"^(\d{4})-", value or "")
    return int(match.group(1)) if match else None


def load_house_lane(
    path: Path, lane: str, queue_by_person, by_name_key
) -> dict[str, dict[str, Any]]:
    people: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": [], "offices": defaultdict(list)}
    )
    for record in read_rows(path):
        person = str(record["lda_source_person_id"])
        queue = queue_by_person.get(person)
        if lane == LANE_H1:
            office_raw = record.get("employing_office_raw") or ""
            candidate_count, display_count = h1_name_uniqueness(
                record.get("payroll_payee_raw"), by_name_key
            )
            uniqueness_method = (
                "RECONSTRUCTED_FROM_QUEUE_NAME_INDEX"
                if candidate_count is not None
                else "NO_QUEUE_CANDIDATE_FOR_PAYROLL_NAME"
            )
            name_ok = (
                (candidate_count == 1 and display_count == 1)
                if candidate_count is not None
                else False
            )
            end_year = year_of(record.get("service_end_date_candidate_iso"))
            title = (record.get("title_description_raw") or "").strip()
            quarters = [key for key in (quarter_key(record.get("period")),) if key]
            candidate_id = str(record.get("candidate_match_id") or "")
        else:
            office_raw = record.get("employing_office_candidate") or ""
            candidate_count = record.get("queue_candidate_count_for_name")
            display_count = record.get("queue_display_name_count_for_name")
            uniqueness_method = "LEDGER_FIELDS"
            name_ok = candidate_count == 1 and display_count == 1
            end_year = year_of(record.get("service_end_date_candidate"))
            title = (record.get("title_candidate") or "").strip()
            quarters = [
                key
                for key in (
                    quarter_key(value) for value in record.get("supported_quarters") or []
                )
                if key
            ]
            candidate_id = str(record.get("match_candidate_id") or "")
        blob = queue["covered_blob_casefolded"] if queue else ""
        if queue is None:
            office_ok, office_method, office_detail = False, "NO_QUEUE_ROW", ""
        else:
            office_ok, office_method, office_detail = check_office_corroboration_house(
                office_raw, blob
            )
        entry = {
            "candidate_id": candidate_id,
            "end_year": end_year,
            "name_candidate_count": candidate_count,
            "name_display_count": display_count,
            "name_ok": name_ok,
            "name_method": uniqueness_method,
            "office_detail": office_detail,
            "office_method": office_method,
            "office_ok": office_ok,
            "office_raw": office_raw,
            "quarters": quarters,
            "title": title,
        }
        people[person]["rows"].append(entry)
        people[person]["offices"][office_group_key(office_raw)].append(entry)
    return {person: dict(value) for person, value in people.items()}


def load_senate_lane(path: Path, queue_by_person) -> dict[str, dict[str, Any]]:
    people: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": [], "offices": defaultdict(list)}
    )
    for record in read_rows(path):
        person = str(record["lda_source_person_id"])
        queue = queue_by_person.get(person)
        office_raw = record.get("employing_office_candidate") or ""
        intervals = []
        for interval in record.get("observed_report_intervals") or []:
            start = parse_iso(interval.get("start"))
            end = parse_iso(interval.get("end"))
            intervals.append((start, end))
        token = office_token_senate(office_raw)
        covered_upper = queue["covered_text_upper"] if queue else ""
        if queue is None:
            office_ok, office_method = False, "NO_QUEUE_ROW"
        elif token is None:
            office_ok, office_method = False, "SENATE_OFFICE_TOKEN_NOT_EXTRACTABLE"
        elif whole_word_in(token, covered_upper):
            office_ok, office_method = True, "SENATE_OFFICE_TOKEN_MATCH"
        else:
            office_ok, office_method = False, "SENATE_OFFICE_TOKEN_NOT_FOUND"
        entry = {
            "candidate_id": str(record.get("match_candidate_id") or ""),
            "intervals": intervals,
            "name_candidate_count": record.get("queue_candidate_count_for_name"),
            "name_display_count": record.get("queue_display_name_count_for_name"),
            "name_ok": record.get("queue_candidate_count_for_name") == 1,
            "name_method": "LEDGER_FIELDS",
            "office_detail": token or "",
            "office_method": office_method,
            "office_ok": office_ok,
            "office_raw": office_raw,
            "title": (record.get("title_candidate") or "").strip(),
        }
        people[person]["rows"].append(entry)
        people[person]["offices"][office_raw].append(entry)
    return {person: dict(value) for person, value in people.items()}


# ---------------------------------------------------------------------------
# Lane tier computation (reference rules)
# ---------------------------------------------------------------------------
def chronology_threshold(filing_years: Sequence[int], offset: int) -> int | None:
    return (min(filing_years) + offset) if filing_years else None


def house_lane_tiers(lane_people, queue_by_person, offset: int = CHRONOLOGY_OFFSET_YEARS):
    result = {}
    for person, aggregate in lane_people.items():
        rows = aggregate["rows"]
        queue = queue_by_person.get(person)
        filing_years = (queue or {}).get("filing_years") or []
        threshold = chronology_threshold(filing_years, offset)
        end_years = [r["end_year"] for r in rows if r["end_year"] is not None]
        max_end_year = max(end_years) if end_years else None
        if threshold is None or max_end_year is None:
            chronology = "UNKNOWN"
        elif max_end_year <= threshold:
            chronology = "CONSISTENT"
        else:
            chronology = "INCONSISTENT"
        result[person] = {
            "name_unique": any(r["name_ok"] for r in rows),
            "office_corroborated": any(r["office_ok"] for r in rows),
            "chronology": chronology,
            "split_clean": None,
            "max_end_year": max_end_year,
            "threshold": threshold,
            "first_filing_year": min(filing_years) if filing_years else None,
        }
    return result


def senate_lane_tiers(lane_people, queue_by_person, offset: int = CHRONOLOGY_OFFSET_YEARS):
    result = {}
    for person, aggregate in lane_people.items():
        rows = aggregate["rows"]
        queue = queue_by_person.get(person)
        filing_years = (queue or {}).get("filing_years") or []
        threshold = chronology_threshold(filing_years, offset)
        max_end_year = None
        split_clean = True
        for office_raw, office_rows in aggregate["offices"].items():
            periods = set()
            for row in office_rows:
                for interval in row["intervals"]:
                    periods.add(interval)
            dates_ok = True
            parsed = []
            for start, end in periods:
                if start is None or end is None:
                    dates_ok = False
                else:
                    if max_end_year is None or end.year > max_end_year:
                        max_end_year = end.year
                parsed.append((start, end))
            parsed.sort(key=lambda pair: (pair[0] is None, pair[0]))
            if not (dates_ok and periods_contiguous(parsed)):
                split_clean = False
        if threshold is None or max_end_year is None:
            chronology = "UNKNOWN"
        elif max_end_year <= threshold:
            chronology = "CONSISTENT"
        else:
            chronology = "INCONSISTENT"
        result[person] = {
            "name_unique": all(r["name_candidate_count"] == 1 for r in rows),
            "office_corroborated": any(r["office_ok"] for r in rows),
            "chronology": chronology,
            "split_clean": split_clean,
            "max_end_year": max_end_year,
            "threshold": threshold,
            "first_filing_year": min(filing_years) if filing_years else None,
        }
    return result


def merge_house_union(h1_people, h2_people) -> dict[str, dict[str, Any]]:
    union: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"rows": [], "offices": defaultdict(list)}
    )
    for lane_people in (h1_people, h2_people):
        for person, aggregate in lane_people.items():
            union[person]["rows"].extend(aggregate["rows"])
            for key, rows in aggregate["offices"].items():
                union[person]["offices"][key].extend(rows)
    return {person: dict(value) for person, value in union.items()}


def person_tier_letter(prongs: Mapping[str, Any], multi_source: bool) -> str:
    if not prongs["name_unique"]:
        return "L1"
    if not prongs["office_corroborated"]:
        return "L2"
    if prongs["chronology"] != "CONSISTENT":
        return "L3"
    return "L5" if multi_source else "L4"


def tier_max(left: str, right: str) -> str:
    return left if TIER_ORDER.index(left) >= TIER_ORDER.index(right) else right


# ---------------------------------------------------------------------------
# Multi-source evidence
# ---------------------------------------------------------------------------
def load_profile_employers(paths: Mapping[str, Path]) -> dict[str, list[str]]:
    employers: defaultdict[str, list[str]] = defaultdict(list)
    for record in read_rows(paths["working_history_corpus"]):
        person = record.get("lda_source_person_id")
        for episode in record.get("employment_episodes") or []:
            employer = episode.get("employer")
            if employer:
                employers[str(person)].append(str(employer))
    for record in read_rows(paths["rapid_structured_profile_evidence"]):
        person = record.get("lda_source_person_id")
        for episode in record.get("employment") or []:
            employer = episode.get("employer")
            if employer:
                employers[str(person)].append(str(employer))
    for record in read_rows(paths["linkedin_authenticated_evidence"]):
        person = record.get("lda_source_person_id")
        for fact in record.get("candidate_facts") or []:
            if fact.get("fact_type") == "EMPLOYMENT":
                employer = fact.get("employer_raw")
                if employer:
                    employers[str(person)].append(str(employer))
    return {person: sorted(set(values)) for person, values in employers.items()}


def load_politico_roles(path: Path) -> dict[str, list[str]]:
    roles: defaultdict[str, list[str]] = defaultdict(list)
    for record in read_rows(path):
        text = record.get("role_text_raw")
        if text:
            roles[str(record["lda_source_person_id"])].append(str(text))
    return {person: sorted(set(values)) for person, values in roles.items()}


def load_legilist_people(path: Path) -> set[str]:
    people: set[str] = set()
    for record in read_rows(path):
        if (
            record.get("lane") == "legilist_source_binding"
            and record.get("decision") == "ACCEPTED_SOURCE_BINDING"
        ):
            people.add(str(record["lda_source_person_id"]))
    return people


def office_match_tokens(chamber: str, office_raws: Sequence[str]) -> list[str]:
    tokens: set[str] = set()
    for office_raw in office_raws:
        if chamber == "house":
            tokens.update(office_token_house(office_raw))
        else:
            token = office_token_senate(office_raw)
            if token:
                tokens.add(token)
    return sorted(tokens)


def first_text_naming_office(texts: Sequence[str], tokens: Sequence[str]):
    for text in texts:
        upper = text.upper()
        for token in tokens:
            if whole_word_in(token, upper):
                return text, token
    return None, None


# ---------------------------------------------------------------------------
# Record construction
# ---------------------------------------------------------------------------
def build_person_office_records(
    *,
    lane: str,
    chamber: str,
    lane_people,
    lane_tiers,
    roster,
    nickname_table,
    profile_employers,
    politico_roles,
    legilist_people,
    rule_version: str,
) -> tuple[list[dict[str, Any]], Counter, dict[str, str], dict[str, set[str]]]:
    records: list[dict[str, Any]] = []
    diagnostics: Counter = Counter()
    record_tier_by_person: dict[str, str] = {}
    l4_office_groups: dict[str, set[str]] = defaultdict(set)
    period_kind = "quarter" if chamber == "house" else "half_year"

    for person in sorted(lane_people):
        aggregate = lane_people[person]
        prongs = lane_tiers[person]
        seen_office_keys: set[str] = set()
        for office_group in sorted(aggregate["offices"]):
            office_rows = sorted(
                aggregate["offices"][office_group], key=lambda row: row["candidate_id"]
            )
            office_raws = sorted({row["office_raw"] for row in office_rows})

            # Observation window for this office group (INV-6 term-window hard
            # constraint): the earliest-to-latest span of periods actually
            # observed for the (person, office) pair.  Computed once here and
            # reused below by the run-splitting logic so there is exactly one
            # source of truth for "what was observed" per office group.
            if chamber == "house":
                observed_quarter_keys = sorted(
                    {key for row in office_rows for key in row["quarters"]}
                )
                if observed_quarter_keys:
                    window_start = quarter_bounds(observed_quarter_keys[0])[0]
                    window_end = quarter_bounds(observed_quarter_keys[-1])[1]
                else:
                    window_start = window_end = None
                observed_interval_set = None
            else:
                observed_interval_set = {
                    (start, end)
                    for row in office_rows
                    for start, end in row["intervals"]
                    if start is not None and end is not None
                }
                if observed_interval_set:
                    window_start = min(start for start, _ in observed_interval_set)
                    window_end = max(end for _, end in observed_interval_set)
                else:
                    window_start = window_end = None
                observed_quarter_keys = None

            if chamber == "house":
                office_key = office_group
                container = container_kind_house(office_raws[0])
                normalized = normalize_office(office_raws[0])
                if is_hon_office(normalized):
                    first, surname = extract_hon_first_and_surname(normalized)
                    bioguide, method = resolve_member_bioguide(
                        first,
                        surname,
                        roster,
                        nickname_table,
                        chamber=chamber,
                        window_start=window_start,
                        window_end=window_end,
                    )
                else:
                    bioguide, method = None, "NOT_A_MEMBER_OFFICE"
            else:
                office_key = " ".join(office_group.strip().upper().split())
                container = container_kind_senate(office_group)
                if container == "member_office":
                    first, surname = senate_member_first_and_surname(office_group)
                    bioguide, method = resolve_member_bioguide(
                        first,
                        surname,
                        roster,
                        nickname_table,
                        chamber=chamber,
                        window_start=window_start,
                        window_end=window_end,
                    )
                else:
                    bioguide, method = None, "NOT_A_MEMBER_OFFICE"
            if office_key in seen_office_keys:
                raise GateFailure(
                    f"office key collision for {person} in {lane}: {office_key!r}"
                )
            seen_office_keys.add(office_key)

            matching = [row for row in office_rows if row["office_ok"]]
            office_ok = bool(matching)
            if matching:
                office_method = matching[0]["office_method"]
                matched_token = matching[0]["office_detail"] or None
            else:
                office_method = sorted({row["office_method"] for row in office_rows})[0]
                matched_token = None

            if chamber == "house":
                office_end_years = [
                    row["end_year"]
                    for row in office_rows
                    if row.get("end_year") is not None
                ]
            else:
                office_end_years = [
                    end.year
                    for row in office_rows
                    for _, end in row["intervals"]
                    if end is not None
                ]
            office_max_end_year = max(office_end_years) if office_end_years else None
            office_chronology_consistent = (
                prongs["threshold"] is not None
                and office_max_end_year is not None
                and office_max_end_year <= prongs["threshold"]
            )

            # Runs: maximal stretches of observed reporting periods with no
            # internal gap.  House periods are quarters (consecutive ordinals);
            # Senate periods are the observed semiannual report intervals
            # (joined when they overlap or abut).
            run_specs: list[tuple[int, date, date, date, date]] = []
            if chamber == "house":
                keys = observed_quarter_keys
                if not keys:
                    diagnostics["office_groups_without_parseable_period"] += 1
                    continue
                office_period_count = len(keys)
                key_runs: list[list[tuple[int, int]]] = []
                for key in keys:
                    if key_runs and quarter_ordinal(key) == quarter_ordinal(
                        key_runs[-1][-1]
                    ) + 1:
                        key_runs[-1].append(key)
                    else:
                        key_runs.append([key])
                for key_run in key_runs:
                    core_start = quarter_bounds(key_run[0])[0]
                    core_end = quarter_bounds(key_run[-1])[1]
                    envelope_start = quarter_bounds(
                        ordinal_to_quarter(
                            quarter_ordinal(key_run[0])
                            - ENVELOPE_WIDENING_REPORTING_PERIODS
                        )
                    )[0]
                    envelope_end = quarter_bounds(
                        ordinal_to_quarter(
                            quarter_ordinal(key_run[-1])
                            + ENVELOPE_WIDENING_REPORTING_PERIODS
                        )
                    )[1]
                    run_specs.append(
                        (len(key_run), core_start, core_end, envelope_start, envelope_end)
                    )
                run_count = len(key_runs)
            else:
                interval_set = observed_interval_set
                if not interval_set:
                    diagnostics["office_groups_without_parseable_period"] += 1
                    continue
                office_period_count = len(interval_set)
                date_runs = merge_runs(sorted(interval_set))
                for date_run in date_runs:
                    core_start = date_run[0][0]
                    core_end = max(end for _, end in date_run)
                    envelope_start = senate_previous_window(senate_window(core_start))[0]
                    envelope_end = senate_next_window(senate_window(core_end))[1]
                    run_specs.append(
                        (len(date_run), core_start, core_end, envelope_start, envelope_end)
                    )
                run_count = len(date_runs)
            contiguous = run_count == 1

            candidate_ids = sorted({row["candidate_id"] for row in office_rows if row["candidate_id"]})
            titles = sorted({row["title"] for row in office_rows if row["title"]})

            tokens = office_match_tokens(chamber, office_raws)
            profile_employer, _ = first_text_naming_office(
                profile_employers.get(person, []), tokens
            )
            politico_text, politico_token = first_text_naming_office(
                politico_roles.get(person, []), tokens
            )
            multi_source = []
            if profile_employer is not None:
                multi_source.append("profile")
            if politico_token is not None:
                multi_source.append("politico")
            multi_source.sort()

            base_tier = person_tier_letter(
                {
                    "name_unique": prongs["name_unique"],
                    "office_corroborated": office_ok,
                    "chronology": prongs["chronology"],
                },
                bool(multi_source),
            )
            record_tier_by_person[person] = tier_max(
                record_tier_by_person.get(person, "L1"), base_tier
            )
            if TIER_ORDER.index(base_tier) >= TIER_ORDER.index("L4"):
                l4_office_groups[person].add(office_key)

            for run_index, (
                run_periods,
                core_start,
                core_end,
                envelope_start,
                envelope_end,
            ) in enumerate(run_specs, start=1):
                interval = UncertainInterval(
                    start_earliest=envelope_start,
                    start_latest=core_start,
                    end_earliest=core_end,
                    end_latest=envelope_end,
                    start_precision="day",
                    end_precision="day",
                )
                interval.validate()

                records.append(
                    {
                        "canonical_eligible": False,
                        "canonical_employment_promoted": False,
                        "chamber": chamber,
                        "container_kind": container,
                        "contiguous": contiguous,
                        "core": {
                            "end_earliest": core_end.isoformat(),
                            "start_latest": core_start.isoformat(),
                        },
                        "envelope": {
                            "end_latest": envelope_end.isoformat(),
                            "start_earliest": envelope_start.isoformat(),
                        },
                        "identity_status": (
                            "STRICT_ONE_TO_ONE_REVIEW_CANDIDATE"
                            if prongs["name_unique"]
                            else "NAME_MATCH_ONLY"
                        ),
                        "lda_source_person_id": person,
                        "member_bioguide": bioguide,
                        "member_resolution_method": method,
                        "office_key": office_key,
                        "office_raw_examples": office_raws[:MAX_EXAMPLES_PER_RECORD],
                        "period_kind": period_kind,
                        "periods_observed": run_periods,
                        "precision": "report_period",
                        "prong": {
                            "chronology": prongs["chronology"],
                            "multi_source": multi_source,
                            "name_unique": prongs["name_unique"],
                            "office_corroborated": office_ok,
                            "split_clean": prongs["split_clean"],
                        },
                        "prong_evidence": {
                            "chronology": {
                                "first_filing_year": prongs["first_filing_year"],
                                "max_observed_end_year": prongs["max_end_year"],
                                "office_chronology_consistent": office_chronology_consistent,
                                "office_max_observed_end_year": office_max_end_year,
                                "threshold_year": prongs["threshold"],
                            },
                            "multi_source": {
                                "legilist_names_office": False,
                                "legilist_person_binding": person in legilist_people,
                                "politico_matched_token": politico_token,
                                "profile_matched_employer": profile_employer,
                            },
                            "name_uniqueness": {
                                "method": office_rows[0]["name_method"],
                                "queue_candidate_count_for_name": office_rows[0][
                                    "name_candidate_count"
                                ],
                                "queue_display_name_count_for_name": office_rows[0][
                                    "name_display_count"
                                ],
                            },
                            "office_match": {
                                "matched_token": matched_token,
                                "method": office_method,
                                "office_normalized": (
                                    normalize_office(office_raws[0])
                                    if chamber == "house"
                                    else office_key
                                ),
                            },
                            "payroll_support_digest": digest_values(candidate_ids),
                            "split": {
                                "office_period_count": office_period_count,
                                "office_run_count": run_count,
                                "person_offices_all_contiguous": prongs["split_clean"],
                            },
                        },
                        "review_status": "REVIEW_REQUIRED",
                        "rule_version": rule_version,
                        "run_count": run_count,
                        "run_index": run_index,
                        "schema_id": RECORD_SCHEMA,
                        "source_lane": lane,
                        "tier": base_tier,
                        "title_examples": titles[:MAX_EXAMPLES_PER_RECORD],
                    }
                )
    return records, diagnostics, record_tier_by_person, l4_office_groups


def prong_failure_codes(
    prongs: Mapping[str, Any], lane_people, person: str, queue, chamber: str
) -> set[str]:
    codes: set[str] = set()
    if not prongs["name_unique"]:
        codes.add("NAME_COLLISION_IN_QUEUE")
    if not prongs["office_corroborated"]:
        methods = {row["office_method"] for row in lane_people[person]["rows"]}
        if queue is not None and not queue["covered_position_substantive"]:
            codes.add("COVERED_POSITION_TEXT_EMPTY")
        if "COMMITTEE_FAMILY_UNMAPPED" in methods:
            codes.add("OFFICE_FAMILY_UNMAPPED")
        if "SENATE_OFFICE_TOKEN_NOT_EXTRACTABLE" in methods:
            codes.add("OFFICE_TOKEN_NOT_EXTRACTABLE")
        if "HON_NO_SURNAME_PARSED" in methods:
            codes.add("MEMBER_SURNAME_NOT_PARSED")
        if "EMPTY_OFFICE" in methods:
            codes.add("OFFICE_STRING_EMPTY")
        if methods & {
            "MEMBER_SURNAME_NOT_FOUND",
            "COMMITTEE_KEYWORD_NOT_FOUND",
            "SENATE_OFFICE_TOKEN_NOT_FOUND",
        }:
            codes.add("OFFICE_NOT_IN_COVERED_POSITION_TEXT")
    if prongs["chronology"] == "INCONSISTENT":
        codes.add("CHRONOLOGY_INCONSISTENT")
    elif prongs["chronology"] == "UNKNOWN":
        codes.add("CHRONOLOGY_UNKNOWN")
    if chamber == "senate" and prongs["split_clean"] is False:
        codes.add("SPLIT_NOT_CLEAN")
    return codes


# ---------------------------------------------------------------------------
# A6 filer-asserted year episodes
# ---------------------------------------------------------------------------
def surname_in_office_wholeword(surname: str | None, office_text: str) -> bool:
    if not surname or not office_text:
        return False
    return re.search(
        r"\b" + re.escape(surname.upper()) + r"\b", office_text.upper()
    ) is not None


A6_SENATE_TITLE_RE = re.compile(r"\b(?:SEN\.?|SENATOR)\b")
A6_HOUSE_TITLE_RE = re.compile(
    r"\b(?:REP\.?|REPRESENTATIVE|CONGRESSMAN|CONGRESSWOMAN|CONG\.)\b"
)


def a6_chamber_hint(office_text: str) -> str | None:
    """Best-effort chamber for an A6 office/employer mention, used only to
    apply the INV-6 term-type constraint.  ``Hon.``/bare ``Office of`` text
    names neither chamber explicitly, so this returns ``None`` and the term
    window is checked without a chamber restriction for those rows.
    """
    upper = (office_text or "").upper()
    if A6_SENATE_TITLE_RE.search(upper):
        return "senate"
    if A6_HOUSE_TITLE_RE.search(upper):
        return "house"
    return None


def build_filer_episodes(
    path: Path, roster, nickname_table, payroll_offices_by_person, rule_version: str
):
    rows: list[dict[str, Any]] = []
    stats = Counter()
    for flag in A6_EXCLUDED_FLAGS:
        stats[f"excluded_flag_{flag}"] = 0
    for record in read_rows(path):
        stats["near_candidate_rows"] += 1
        mention = record.get("office_employer_mention") or {}
        dates = record.get("date_range_mention") or {}
        entity_class = mention.get("entity_class")
        start_year = dates.get("explicit_start_year")
        end_year = dates.get("explicit_end_year")
        resolvable = entity_class in A6_RESOLVABLE_ENTITY_CLASSES
        both_years = start_year is not None and end_year is not None
        if resolvable:
            stats["resolvable_entity"] += 1
        if both_years:
            stats["both_explicit_years"] += 1
        if not (resolvable and both_years):
            continue
        stats["resolvable_entity_and_both_years"] += 1
        reasons = set(record.get("rejection_reasons") or [])
        excluded = sorted(reasons & set(A6_EXCLUDED_FLAGS))
        if excluded:
            stats["excluded_by_flags"] += 1
            for flag in excluded:
                stats[f"excluded_flag_{flag}"] += 1
            continue
        stats["released"] += 1
        person = str(record["lda_source_person_id"])
        office_text = str(mention.get("text") or "")
        role_mention = record.get("role_title_mention") or {}
        role_text = role_mention.get("text")
        surname = None
        first = None
        if entity_class == "MEMBER_OFFICE_CANDIDATE":
            for pattern in (A6_TITLE_RE, A6_OFFICE_RE):
                match = pattern.search(office_text)
                if match:
                    first, surname = extract_surname_first(match.group(1))
                    if surname:
                        break
            bioguide, method = resolve_member_bioguide(
                first,
                surname,
                roster,
                nickname_table,
                chamber=a6_chamber_hint(office_text),
                window_start=date(int(start_year), 1, 1),
                window_end=date(int(end_year), 12, 31),
            )
        else:
            bioguide, method = None, "NOT_A_MEMBER_OFFICE"
        corroborating = sorted(
            {
                office
                for office in payroll_offices_by_person.get(person, ())
                if surname_in_office_wholeword(surname, office)
            }
        )
        rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "claim_id": str((record.get("source_pointer") or {}).get("claim_id") or ""),
                "corroborated_by_payroll": bool(corroborating),
                "corroborating_payroll_office_examples": corroborating[
                    :MAX_EXAMPLES_PER_RECORD
                ],
                "excluded_flags": [],
                "lda_source_person_id": person,
                "member_bioguide": bioguide,
                "member_resolution_method": method,
                "member_surname_text": surname,
                "office_entity_class": entity_class,
                "office_text": office_text,
                "precision": "year",
                "review_status": "REVIEW_REQUIRED",
                "role_text": role_text,
                "rule_version": rule_version,
                "schema_id": EPISODE_SCHEMA,
                "single_author": True,
                "start_year": int(start_year),
                "end_year": int(end_year),
            }
        )
    rows.sort(key=lambda row: (row["lda_source_person_id"], row["claim_id"]))
    return rows, stats


# ---------------------------------------------------------------------------
# Registrant side
# ---------------------------------------------------------------------------
def build_registrant_records(
    paths: Mapping[str, Path],
    queue_order: Sequence[str],
    payroll_year_span: Mapping[str, tuple[int, int]],
    profile_dated_employers: Mapping[str, list[tuple[str, bool]]],
    rule_version: str,
):
    episodes: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    names_by_year: defaultdict[str, defaultdict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    names_any_year: defaultdict[str, set[str]] = defaultdict(set)
    year_span: dict[str, tuple[int, int]] = {}
    for record in read_rows(paths["lda_registrant_employment_episodes"]):
        person = str(record["lda_source_person_id"])
        episodes[person].append(record)
    for person, records in episodes.items():
        years: list[int] = []
        for record in records:
            normalized = norm_name(record.get("employer_name"))
            names_any_year[person].add(normalized)
            filing_years = list(record.get("filing_years") or [])
            start_year, end_year = record.get("start_year"), record.get("end_year")
            episode_years = set(filing_years)
            if start_year is not None and end_year is not None:
                episode_years.update(range(start_year, end_year + 1))
            elif start_year is not None:
                episode_years.add(start_year)
            elif end_year is not None:
                episode_years.add(end_year)
            for year in episode_years:
                names_by_year[person][year].add(normalized)
            years.extend(filing_years)
            if start_year is not None:
                years.append(start_year)
            if end_year is not None:
                years.append(end_year)
        if years:
            year_span[person] = (min(years), max(years))

    ld203_years: defaultdict[str, set[int]] = defaultdict(set)
    ld203_names_any: defaultdict[str, set[str]] = defaultdict(set)
    ld203_names_by_year: defaultdict[str, defaultdict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    ld203_raw_by_normalized: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for record in read_rows(paths["a7_ld203_affiliations"]):
        person = str(record["lda_source_person_id"])
        year = record.get("filing_year")
        raw = record.get("lda_registrant_name")
        normalized = norm_name(raw)
        ld203_years[person].add(year)
        ld203_names_any[person].add(normalized)
        ld203_names_by_year[person][year].add(normalized)
        ld203_raw_by_normalized[person].setdefault(normalized, str(raw or ""))

    fec_rows: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in read_rows(paths["a7_fec_employment_observations"]):
        fec_rows[str(record["lda_source_person_id"])].append(record)

    littlesis: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in read_rows(paths["littlesis_lda_history_candidates"]):
        if record.get("fact_type") == "EMPLOYMENT":
            littlesis[str(record["lda_source_person_id"])].append(record)

    rows: list[dict[str, Any]] = []
    order_counts: Counter = Counter()
    tier_counts: Counter = Counter()
    stats: Counter = Counter()
    for person in sorted(queue_order):
        person_episodes = episodes.get(person, [])
        registrants = sorted(
            (
                {
                    "employer_name": record.get("employer_name"),
                    "employer_name_normalized": norm_name(record.get("employer_name")),
                    "end_year": record.get("end_year"),
                    "filing_years": sorted(set(record.get("filing_years") or [])),
                    "registrant_source_org_id": str(
                        record.get("registrant_source_org_id") or ""
                    ),
                    "start_year": record.get("start_year"),
                }
                for record in person_episodes
            ),
            key=lambda item: (item["registrant_source_org_id"], item["employer_name_normalized"]),
        )
        span = year_span.get(person)
        ld_years = {year for year in ld203_years.get(person, set()) if year is not None}
        same_year = False
        matched_name = None
        for year in sorted(ld_years):
            overlap = ld203_names_by_year[person][year] & names_by_year[person].get(year, set())
            if overlap:
                same_year = True
                normalized = sorted(overlap)[0]
                matched_name = ld203_raw_by_normalized[person].get(normalized)
                break
        extends_earlier = 0
        extends_later = 0
        if span and ld_years:
            if min(ld_years) < span[0]:
                extends_earlier = span[0] - min(ld_years)
            if max(ld_years) > span[1]:
                extends_later = max(ld_years) - span[1]
        introduces_unseen = bool(
            ld203_names_any.get(person, set()) - names_any_year.get(person, set())
        )

        fec_same_year = False
        fec_any_year = False
        for record in fec_rows.get(person, []):
            employer = norm_name(record.get("raw_employer"))
            observation = str(record.get("observation_date") or "")
            try:
                observation_year = int(observation[:4])
            except ValueError:
                observation_year = None
            if employer in names_any_year.get(person, set()):
                fec_any_year = True
            if (
                observation_year is not None
                and employer in names_by_year[person].get(observation_year, set())
            ):
                fec_same_year = True

        littlesis_dated = False
        littlesis_bounded = False
        dated_employer = None
        for record in littlesis.get(person, []):
            normalized = norm_name(record.get("container_display_name"))
            if normalized not in names_any_year.get(person, set()):
                continue
            start_raw, end_raw = record.get("raw_start_date"), record.get("raw_end_date")
            if start_raw or end_raw:
                littlesis_dated = True
                if dated_employer is None:
                    dated_employer = str(record.get("container_display_name") or "")
            if start_raw and end_raw:
                littlesis_bounded = True

        profile_dated = False
        profile_bounded = False
        for employer, bounded in profile_dated_employers.get(person, []):
            if norm_name(employer) not in names_any_year.get(person, set()):
                continue
            profile_dated = True
            if dated_employer is None:
                dated_employer = employer
            if bounded:
                profile_bounded = True

        if not person_episodes:
            tier = None
        elif littlesis_dated or littlesis_bounded or profile_dated or profile_bounded:
            tier = "R2"
        elif same_year or fec_same_year:
            tier = "R1"
        else:
            tier = "R0"

        hill_span = payroll_year_span.get(person)
        if hill_span is None:
            order = "NO_HILL_OBSERVATION"
        elif span is None:
            order = "NO_HILL_OBSERVATION"
        elif hill_span[1] < span[0]:
            order = "ORDERED"
        elif span[1] < hill_span[0]:
            order = "REVERSED"
        else:
            order = "OVERLAP_YEAR_GRAIN"
        order_counts[order] += 1
        tier_counts[tier if tier is not None else "NONE"] += 1
        if ld_years:
            stats["ld203_people"] += 1
        stats["ld203_same_year_name_equal"] += int(same_year)
        stats["ld203_extends_earlier_people"] += int(extends_earlier > 0)
        stats["ld203_extends_later_people"] += int(extends_later > 0)
        stats["fec_same_year_name_equal"] += int(fec_same_year)

        rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "dated_registrant_evidence": {
                    "littlesis_bounded": littlesis_bounded,
                    "littlesis_dated": littlesis_dated,
                    "matched_employer_name": dated_employer,
                    "profile_bounded": profile_bounded,
                    "profile_dated": profile_dated,
                },
                "fec": {
                    "any_year_name_equal": fec_any_year,
                    "observation_count": len(fec_rows.get(person, [])),
                    "same_year_name_equal": fec_same_year,
                },
                "hill_payroll_year_span": (
                    {"end_year": hill_span[1], "start_year": hill_span[0]}
                    if hill_span
                    else None
                ),
                "hill_registrant_order": order,
                "ld203": {
                    "extends_earlier_years": extends_earlier,
                    "extends_later_years": extends_later,
                    "filing_year_count": len(ld_years),
                    "first_filing_year": min(ld_years) if ld_years else None,
                    "introduces_unseen_organization": introduces_unseen,
                    "last_filing_year": max(ld_years) if ld_years else None,
                    "matched_registrant_name": matched_name,
                    "same_year_name_equal": same_year,
                },
                "lda_source_person_id": person,
                "registrant_filing_year_span": (
                    {"end_year": span[1], "start_year": span[0]} if span else None
                ),
                "registrant_side_tier": tier,
                "registrants": registrants,
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": REGISTRANT_SCHEMA,
            }
        )
    return rows, order_counts, tier_counts, len(episodes), stats


def load_profile_dated_employers(paths: Mapping[str, Path]) -> dict[str, list[tuple[str, bool]]]:
    result: defaultdict[str, list[tuple[str, bool]]] = defaultdict(list)
    for record in read_rows(paths["working_history_corpus"]):
        person = str(record.get("lda_source_person_id"))
        for episode in record.get("employment_episodes") or []:
            employer = episode.get("employer")
            start_raw, end_raw = episode.get("raw_start_date"), episode.get("raw_end_date")
            if employer and (start_raw or end_raw):
                result[person].append((str(employer), bool(start_raw and end_raw)))
    for record in read_rows(paths["rapid_structured_profile_evidence"]):
        person = str(record.get("lda_source_person_id"))
        for episode in record.get("employment") or []:
            employer = episode.get("employer")
            start_raw, end_raw = episode.get("raw_start_date"), episode.get("raw_end_date")
            if employer and (start_raw or end_raw):
                result[person].append((str(employer), bool(start_raw and end_raw)))
    for record in read_rows(paths["linkedin_authenticated_evidence"]):
        person = str(record.get("lda_source_person_id"))
        for fact in record.get("candidate_facts") or []:
            if fact.get("fact_type") != "EMPLOYMENT":
                continue
            employer = fact.get("employer_raw")
            start_raw, end_raw = fact.get("raw_start_date"), fact.get("raw_end_date")
            if employer and (start_raw or end_raw):
                result[person].append((str(employer), bool(start_raw and end_raw)))
    return {person: sorted(set(values)) for person, values in result.items()}


# ---------------------------------------------------------------------------
# Language law
# ---------------------------------------------------------------------------
def verbatim_field_names() -> set[str]:
    names: set[str] = set()
    for entry in VERBATIM_SOURCE_QUOTED_FIELDS:
        names.add(entry.replace("[]", "").split(".")[-1])
    return names


def scan_language_law(value: Any, verbatim_leaf_names: set[str]):
    """Return (authored_hits, verbatim_occurrences)."""

    authored: list[str] = []
    verbatim: Counter = Counter()

    def walk(node: Any, key: str | None, inside_verbatim: bool) -> None:
        if isinstance(node, Mapping):
            for child_key, child in node.items():
                lowered = str(child_key).casefold()
                for token in LANGUAGE_LAW_TOKENS:
                    if token in lowered:
                        authored.append(f"field_name:{child_key}:{token}")
                walk(child, str(child_key), inside_verbatim or str(child_key) in verbatim_leaf_names)
        elif isinstance(node, list):
            for child in node:
                walk(child, key, inside_verbatim)
        elif isinstance(node, str):
            lowered = node.casefold()
            for token in LANGUAGE_LAW_TOKENS:
                if token in lowered:
                    if inside_verbatim:
                        verbatim[f"{key}|{token}"] += 1
                    else:
                        authored.append(f"value:{key}:{token}")

    walk(value, None, False)
    return authored, verbatim


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> dict[str, Any]:
    live_root = args.live_root.resolve()
    appdata_root = args.appdata_root.resolve()
    output_root = args.output_root.resolve()
    rule_version = args.rule_version

    if output_root.exists() and any(output_root.iterdir()):
        raise GateFailure(f"output directory is nonempty: {output_root}")

    paths = input_paths(live_root, appdata_root)
    paths["working_history_corpus"] = (
        live_root
        / "audits"
        / "staffer_network"
        / "working_history_corpus_20260831T180000Z_8workers"
        / "working_history_corpus.ndjson.gz"
    )
    for label, path in sorted(paths.items()):
        if not path.is_file():
            raise GateFailure(f"input missing: {label}: {path}")

    queue_by_person, queue_by_name_key, queue_order = load_queue(
        paths["employment_lookup_queue"]
    )
    if len(queue_order) != SEALED_QUEUE_ROWS:
        raise GateFailure(
            f"sealed queue is {len(queue_order)} rows, expected {SEALED_QUEUE_ROWS}"
        )

    diagnostics: Counter = Counter()
    roster = load_roster(paths["roster_legislators_current"].parent, counts=diagnostics)
    nickname_table = load_nickname_table(paths["nickname_table"])

    lane_people = {
        LANE_H1: load_house_lane(
            paths["house_sod_2009q3_2015q4"], LANE_H1, queue_by_person, queue_by_name_key
        ),
        LANE_H2: load_house_lane(
            paths["house_payroll_2016_2026"], LANE_H2, queue_by_person, queue_by_name_key
        ),
        LANE_SENATE: load_senate_lane(paths["senate_payroll_2011_2026"], queue_by_person),
    }
    lane_tiers = {
        LANE_H1: house_lane_tiers(lane_people[LANE_H1], queue_by_person),
        LANE_H2: house_lane_tiers(lane_people[LANE_H2], queue_by_person),
        LANE_SENATE: senate_lane_tiers(lane_people[LANE_SENATE], queue_by_person),
    }
    house_union_people = merge_house_union(lane_people[LANE_H1], lane_people[LANE_H2])
    house_union_tiers = house_lane_tiers(house_union_people, queue_by_person)

    profile_employers = load_profile_employers(paths)
    profile_dated_employers = load_profile_dated_employers(paths)
    politico_roles = load_politico_roles(paths["politico_lda_employment_candidates"])
    legilist_people = load_legilist_people(paths["v3_candidate_adjudication_decisions"])

    records: list[dict[str, Any]] = []
    record_tier_by_lane: dict[str, dict[str, str]] = {}
    l4_groups_by_lane: dict[str, dict[str, set[str]]] = {}
    for lane in ALL_LANES:
        chamber = "senate" if lane == LANE_SENATE else "house"
        lane_records, lane_diagnostics, lane_record_tiers, l4_groups = (
            build_person_office_records(
                lane=lane,
                chamber=chamber,
                lane_people=lane_people[lane],
                lane_tiers=lane_tiers[lane],
                roster=roster,
                nickname_table=nickname_table,
                profile_employers=profile_employers,
                politico_roles=politico_roles,
                legilist_people=legilist_people,
                rule_version=rule_version,
            )
        )
        records.extend(lane_records)
        diagnostics.update({f"{lane}:{k}": v for k, v in lane_diagnostics.items()})
        record_tier_by_lane[lane] = lane_record_tiers
        l4_groups_by_lane[lane] = l4_groups
    records.sort(
        key=lambda row: (
            row["chamber"],
            row["source_lane"],
            row["lda_source_person_id"],
            row["office_key"],
            row["run_index"],
        )
    )

    # Lane tier letters used for INV-5 and for the summary.
    lane_tier_letter: dict[str, dict[str, str]] = {}
    for lane in ALL_LANES:
        letters = {}
        for person, prongs in lane_tiers[lane].items():
            multi = record_tier_by_lane[lane].get(person) == "L5"
            letters[person] = person_tier_letter(prongs, multi)
        lane_tier_letter[lane] = letters
    house_union_letter = {}
    for person, prongs in house_union_tiers.items():
        multi = any(
            record_tier_by_lane[lane].get(person) == "L5" for lane in HOUSE_LANES
        )
        house_union_letter[person] = person_tier_letter(prongs, multi)

    # Payroll year spans for the registrant-side order classification.
    payroll_year_span: dict[str, tuple[int, int]] = {}

    def widen(person: str, low: int | None, high: int | None) -> None:
        values = [value for value in (low, high) if value is not None]
        if not values:
            return
        current = payroll_year_span.get(person)
        if current is None:
            payroll_year_span[person] = (min(values), max(values))
        else:
            payroll_year_span[person] = (
                min(current[0], min(values)),
                max(current[1], max(values)),
            )

    for record in read_rows(paths["house_sod_2009q3_2015q4"]):
        widen(
            str(record["lda_source_person_id"]),
            year_of(record.get("service_start_date_candidate_iso"))
            or year_of(record.get("period_start")),
            year_of(record.get("service_end_date_candidate_iso"))
            or year_of(record.get("period_end")),
        )
    for record in read_rows(paths["house_payroll_2016_2026"]):
        widen(
            str(record["lda_source_person_id"]),
            year_of(record.get("service_start_date_candidate")),
            year_of(record.get("service_end_date_candidate")),
        )
    for record in read_rows(paths["senate_payroll_2011_2026"]):
        years = []
        for interval in record.get("observed_report_intervals") or []:
            for value in (interval.get("start"), interval.get("end")):
                parsed = year_of(value)
                if parsed is not None:
                    years.append(parsed)
        if years:
            widen(str(record["lda_source_person_id"]), min(years), max(years))

    payroll_offices_by_person: defaultdict[str, set[str]] = defaultdict(set)
    for lane in ALL_LANES:
        for person, aggregate in lane_people[lane].items():
            for row in aggregate["rows"]:
                if row["office_raw"]:
                    payroll_offices_by_person[person].add(row["office_raw"])

    episodes, a6_stats = build_filer_episodes(
        paths["a6_near_candidates"],
        roster,
        nickname_table,
        payroll_offices_by_person,
        rule_version,
    )
    episode_count_by_person: Counter = Counter(
        row["lda_source_person_id"] for row in episodes
    )

    (
        registrant_rows,
        order_counts,
        registrant_tier_counts,
        registrant_people,
        registrant_stats,
    ) = build_registrant_records(
        paths, queue_order, payroll_year_span, profile_dated_employers, rule_version
    )
    registrant_tier_by_person = {
        row["lda_source_person_id"]: row["registrant_side_tier"] for row in registrant_rows
    }

    a9_bucket: dict[str, str] = {}
    a9_ordinal: dict[str, int] = {}
    for record in read_rows(paths["a9_priority_sidecar"]):
        person = str(record["lda_source_person_id"])
        a9_bucket[person] = str(
            (record.get("revised_priority") or {}).get("priority_bucket") or ""
        )
        a9_ordinal[person] = record.get("sealed_queue_ordinal")

    records_by_person_lane: defaultdict[str, Counter] = defaultdict(Counter)
    for record in records:
        records_by_person_lane[record["lda_source_person_id"]][record["source_lane"]] += 1

    summary_rows: list[dict[str, Any]] = []
    failure_distribution: Counter = Counter()
    for person in sorted(queue_order):
        by_lane = {}
        codes: set[str] = set()
        for lane in ALL_LANES:
            if person in lane_tiers[lane]:
                by_lane[lane] = lane_tier_letter[lane][person]
                chamber = "senate" if lane == LANE_SENATE else "house"
                codes |= prong_failure_codes(
                    lane_tiers[lane][person],
                    lane_people[lane],
                    person,
                    queue_by_person.get(person),
                    chamber,
                )
            else:
                by_lane[lane] = "L0"
        house_tier = house_union_letter.get(person, "L0")
        senate_tier = by_lane[LANE_SENATE]
        max_tier = tier_max(house_tier, senate_tier)
        if max_tier == "L0":
            codes = {"NO_PAYROLL_OBSERVATION"}
        elif max_tier == "L4":
            codes.add("NO_THIRD_SOURCE_NAMES_THE_OFFICE")
        for code in codes:
            failure_distribution[code] += 1
        summary_rows.append(
            {
                "a9_bucket": a9_bucket.get(person),
                "a9_sealed_queue_ordinal": a9_ordinal.get(person),
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "filer_asserted_year_episode_count": episode_count_by_person.get(person, 0),
                "lda_source_person_id": person,
                "max_tier": max_tier,
                "person_office_record_count": sum(
                    records_by_person_lane.get(person, Counter()).values()
                ),
                "prong_failure_codes": sorted(codes),
                "registrant_side_tier": registrant_tier_by_person.get(person),
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "senate_split_clean": (
                    lane_tiers[LANE_SENATE][person]["split_clean"]
                    if person in lane_tiers[LANE_SENATE]
                    else None
                ),
                "schema_id": SUMMARY_SCHEMA,
                "tier_by_chamber": {"house": house_tier, "senate": senate_tier},
                "tier_by_lane": by_lane,
            }
        )

    # ---- measured figures -------------------------------------------------
    def tier_counter(letters: Mapping[str, str]) -> dict[str, int]:
        counts = Counter(letters.values())
        return {tier: counts.get(tier, 0) for tier in TIER_ORDER}

    def at_least(letters: Mapping[str, str], tier: str) -> int:
        index = TIER_ORDER.index(tier)
        return sum(1 for value in letters.values() if TIER_ORDER.index(value) >= index)

    payroll_union_people = set()
    for lane in ALL_LANES:
        payroll_union_people |= set(lane_people[lane])

    senate_split_clean_people = sum(
        1 for prongs in lane_tiers[LANE_SENATE].values() if prongs["split_clean"]
    )
    senate_l4_and_s = sum(
        1
        for person, prongs in lane_tiers[LANE_SENATE].items()
        if prongs["split_clean"]
        and TIER_ORDER.index(lane_tier_letter[LANE_SENATE][person]) >= TIER_ORDER.index("L4")
    )
    senate_l4_s_spans = 0
    for person, prongs in lane_tiers[LANE_SENATE].items():
        if not prongs["split_clean"]:
            continue
        if TIER_ORDER.index(lane_tier_letter[LANE_SENATE][person]) < TIER_ORDER.index("L4"):
            continue
        for office_raw, office_rows in lane_people[LANE_SENATE][person]["offices"].items():
            if any(
                start is not None and end is not None
                for row in office_rows
                for start, end in row["intervals"]
            ):
                senate_l4_s_spans += 1

    def house_l4_span_count(lane: str) -> int:
        total = 0
        for person, aggregate in lane_people[lane].items():
            prongs = lane_tiers[lane][person]
            if not prongs["name_unique"]:
                continue
            threshold = prongs["threshold"]
            for office_group, office_rows in aggregate["offices"].items():
                if not any(row["office_ok"] for row in office_rows):
                    continue
                end_years = [
                    row["end_year"] for row in office_rows if row["end_year"] is not None
                ]
                if threshold is None or not end_years:
                    continue
                if max(end_years) > threshold:
                    continue
                if not any(row["quarters"] for row in office_rows):
                    continue
                total += 1
        return total

    measured = {
        (LANE_H1, "people"): len(lane_people[LANE_H1]),
        (LANE_H1, "L2_name_anchored"): at_least(lane_tier_letter[LANE_H1], "L2"),
        (LANE_H1, "L3_office_corroborated"): at_least(lane_tier_letter[LANE_H1], "L3"),
        (LANE_H1, "L4_chronology_consistent"): at_least(lane_tier_letter[LANE_H1], "L4"),
        (LANE_H1, "L4_person_office_spans"): house_l4_span_count(LANE_H1),
        (LANE_H2, "people"): len(lane_people[LANE_H2]),
        (LANE_H2, "L2_name_anchored"): at_least(lane_tier_letter[LANE_H2], "L2"),
        (LANE_H2, "L3_office_corroborated"): at_least(lane_tier_letter[LANE_H2], "L3"),
        (LANE_H2, "L4_chronology_consistent"): at_least(lane_tier_letter[LANE_H2], "L4"),
        (LANE_H2, "L4_person_office_spans"): house_l4_span_count(LANE_H2),
        (LANE_SENATE, "people"): len(lane_people[LANE_SENATE]),
        (LANE_SENATE, "L2_name_anchored"): at_least(lane_tier_letter[LANE_SENATE], "L2"),
        (LANE_SENATE, "L3_office_corroborated"): at_least(
            lane_tier_letter[LANE_SENATE], "L3"
        ),
        (LANE_SENATE, "L4_chronology_consistent"): at_least(
            lane_tier_letter[LANE_SENATE], "L4"
        ),
        (LANE_SENATE, "S_split_clean"): senate_split_clean_people,
        (LANE_SENATE, "L4_and_S"): senate_l4_and_s,
        (LANE_SENATE, "L4_and_S_person_office_spans"): senate_l4_s_spans,
        ("house_union", "people"): len(house_union_people),
        ("house_union", "L2_name_anchored"): at_least(house_union_letter, "L2"),
        ("house_union", "L3_office_corroborated"): at_least(house_union_letter, "L3"),
        ("house_union", "L4_chronology_consistent"): at_least(house_union_letter, "L4"),
        ("payroll_union", "people"): len(payroll_union_people),
        ("a6_near_candidates", "rows"): a6_stats["near_candidate_rows"],
        ("a6_near_candidates", "resolvable_entity_and_both_years"): a6_stats[
            "resolvable_entity_and_both_years"
        ],
        ("registrant", "people_with_lda_registrant_association"): registrant_people,
        ("registrant", "hill_and_registrant_people"): (
            order_counts["ORDERED"]
            + order_counts["OVERLAP_YEAR_GRAIN"]
            + order_counts["REVERSED"]
        ),
        ("registrant", "order_ORDERED"): order_counts["ORDERED"],
        ("registrant", "order_OVERLAP_YEAR_GRAIN"): order_counts["OVERLAP_YEAR_GRAIN"],
        ("registrant", "order_REVERSED"): order_counts["REVERSED"],
        ("registrant", "ld203_people"): registrant_stats["ld203_people"],
        ("registrant", "ld203_same_year_name_equal"): registrant_stats[
            "ld203_same_year_name_equal"
        ],
        ("registrant", "ld203_extends_earlier_people"): registrant_stats[
            "ld203_extends_earlier_people"
        ],
        ("registrant", "ld203_extends_later_people"): registrant_stats[
            "ld203_extends_later_people"
        ],
        ("registrant", "fec_same_year_name_equal"): registrant_stats[
            "fec_same_year_name_equal"
        ],
    }
    inv5_rows = []
    for lane, metric, expected in INV5_EXPECTED:
        value = measured[(lane, metric)]
        inv5_rows.append(
            {
                "expected": expected,
                "lane": lane,
                "match": value == expected,
                "measured": value,
                "metric": metric,
            }
        )
    inv5_all_match = all(row["match"] for row in inv5_rows)

    # ---- chronology sensitivity sweep (INV-10) ---------------------------
    sensitivity_rows = []
    for label, requested, applied in (
        (
            "minus_50_percent",
            CHRONOLOGY_OFFSET_YEARS * 0.5,
            math.floor(CHRONOLOGY_OFFSET_YEARS * 0.5),
        ),
        ("default", float(CHRONOLOGY_OFFSET_YEARS), CHRONOLOGY_OFFSET_YEARS),
        (
            "plus_50_percent",
            CHRONOLOGY_OFFSET_YEARS * 1.5,
            math.ceil(CHRONOLOGY_OFFSET_YEARS * 1.5),
        ),
    ):
        counts = {}
        for lane in ALL_LANES:
            builder = senate_lane_tiers if lane == LANE_SENATE else house_lane_tiers
            swept = builder(lane_people[lane], queue_by_person, applied)
            counts[lane] = sum(
                1
                for prongs in swept.values()
                if prongs["name_unique"]
                and prongs["office_corroborated"]
                and prongs["chronology"] == "CONSISTENT"
            )
        sensitivity_rows.append(
            {
                "applied_offset": applied,
                "l4_people_by_lane": counts,
                "label": label,
                "requested_value": requested,
            }
        )

    def scaled(values: Mapping[str, float], factor: float) -> dict[str, float]:
        return {key: round(value * factor, 6) for key, value in values.items()}

    strength_sweep = [
        {
            "factor": factor,
            "label": label,
            "part_a_output_invariant": True,
            "values": scaled(TIER_STRENGTH, factor),
        }
        for label, factor in (
            ("minus_50_percent", 0.5),
            ("default", 1.0),
            ("plus_50_percent", 1.5),
        )
    ]
    r_strength_sweep = [
        {
            "factor": factor,
            "label": label,
            "part_a_output_invariant": True,
            "values": scaled(R_STRENGTH, factor),
        }
        for label, factor in (
            ("minus_50_percent", 0.5),
            ("default", 1.0),
            ("plus_50_percent", 1.5),
        )
    ]

    # ---- write ------------------------------------------------------------
    output_root.mkdir(parents=True, exist_ok=True)
    record_path = output_root / RECORD_FILE
    summary_path = output_root / SUMMARY_FILE
    episode_path = output_root / EPISODE_FILE
    registrant_path = output_root / REGISTRANT_FILE
    receipt_path = output_root / RECEIPT_FILE
    write_ndjson_gz(record_path, records)
    write_ndjson_gz(summary_path, summary_rows)
    write_ndjson_gz(episode_path, episodes)
    write_ndjson_gz(registrant_path, registrant_rows)

    # ---- language law ------------------------------------------------------
    leaf_names = verbatim_field_names()
    authored_hits: list[str] = []
    verbatim_counts: Counter = Counter()
    for payload in (records, summary_rows, episodes, registrant_rows):
        hits, occurrences = scan_language_law(payload, leaf_names)
        authored_hits.extend(hits)
        verbatim_counts.update(occurrences)

    input_block = {}
    for label in sorted(paths):
        path = paths[label]
        rows_count = None
        if path.suffix.lower() == ".gz" or path.suffix.lower() == ".ndjson":
            rows_count = sum(1 for _ in read_rows(path))
        input_block[label] = {
            "bytes": path.stat().st_size,
            "path": str(path),
            "rows": rows_count,
            "sha256": sha(path),
        }

    file_block = {}
    for name, path, row_count in (
        (RECORD_FILE, record_path, len(records)),
        (SUMMARY_FILE, summary_path, len(summary_rows)),
        (EPISODE_FILE, episode_path, len(episodes)),
        (REGISTRANT_FILE, registrant_path, len(registrant_rows)),
    ):
        file_block[name] = {
            "bytes": path.stat().st_size,
            "rows": row_count,
            "sha256": sha(path),
        }

    people_at_l0 = sum(1 for row in summary_rows if row["max_tier"] == "L0")
    records_cover = all(
        records_by_person_lane.get(person)
        for person in payroll_union_people
    )
    failures: list[str] = []
    if not inv5_all_match:
        failures.append("INV5_LADDER_REPRODUCTION_MISMATCH")
    if authored_hits:
        failures.append("INV7_LANGUAGE_LAW_AUTHORED_TOKEN")
    if len(summary_rows) != SEALED_QUEUE_ROWS:
        failures.append("INV4_PERSON_SUMMARY_NOT_SEALED_QUEUE")
    if len(registrant_rows) != SEALED_QUEUE_ROWS:
        failures.append("INV4_REGISTRANT_ROWS_NOT_SEALED_QUEUE")
    above_l0_ids = {row["lda_source_person_id"] for row in summary_rows if row["max_tier"] != "L0"}
    if above_l0_ids != payroll_union_people:
        failures.append("INV4_TIER_PARTITION_DOES_NOT_MATCH_PAYROLL_UNION")
    if payroll_union_people - set(queue_order):
        failures.append("INV4_PAYROLL_PERSON_OUTSIDE_SEALED_QUEUE")
    if not records_cover:
        failures.append("PAYROLL_PERSON_WITHOUT_ANY_RECORD")

    receipt = {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "conservation": {
            "payroll_people_outside_sealed_queue": len(
                payroll_union_people - set(queue_order)
            ),
            "payroll_union_people": len(payroll_union_people),
            "people_above_tier_L0": SEALED_QUEUE_ROWS - people_at_l0,
            "people_at_tier_L0": people_at_l0,
            "person_summary_ids_equal_sealed_queue": {
                row["lda_source_person_id"] for row in summary_rows
            }
            == set(queue_order),
            "person_summary_rows": len(summary_rows),
            "records_cover_every_payroll_person": records_cover,
            "registrant_side_ids_equal_sealed_queue": {
                row["lda_source_person_id"] for row in registrant_rows
            }
            == set(queue_order),
            "registrant_side_rows": len(registrant_rows),
            "sealed_queue_rows": len(queue_order),
            "tier_partition_sums_to_queue": sum(
                Counter(row["max_tier"] for row in summary_rows).values()
            )
            == SEALED_QUEUE_ROWS,
        },
        "counts": {
            "a6": {key: value for key, value in sorted(a6_stats.items())},
            "filer_asserted_year_episodes": len(episodes),
            "hill_registrant_order": dict(sorted(order_counts.items())),
            "max_tier_people": tier_counter(
                {row["lda_source_person_id"]: row["max_tier"] for row in summary_rows}
            ),
            "member_resolution_methods": dict(
                sorted(Counter(row["member_resolution_method"] for row in records).items())
            ),
            "people_with_payroll_observation": len(payroll_union_people),
            "person_office_records": len(records),
            "person_summary_rows": len(summary_rows),
            "records_by_container_kind": dict(
                sorted(Counter(row["container_kind"] for row in records).items())
            ),
            "records_by_lane": dict(
                sorted(Counter(row["source_lane"] for row in records).items())
            ),
            "records_by_tier": dict(
                sorted(Counter(row["tier"] for row in records).items())
            ),
            "registrant_side_records": len(registrant_rows),
            "registrant_tier_people": dict(sorted(registrant_tier_counts.items())),
            "senate_split_clean_people": senate_split_clean_people,
            "tier_people_by_chamber": {
                "house": tier_counter(house_union_letter),
                "senate": tier_counter(lane_tier_letter[LANE_SENATE]),
            },
            "tier_people_by_lane": {
                lane: tier_counter(lane_tier_letter[lane]) for lane in ALL_LANES
            },
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_keys": {
                EPISODE_FILE: "lda_source_person_id, claim_id",
                RECORD_FILE: "chamber, source_lane, lda_source_person_id, office_key, run_index",
                REGISTRANT_FILE: "lda_source_person_id",
                SUMMARY_FILE: "lda_source_person_id",
            },
        },
        "dials": {
            "R_STRENGTH": dict(sorted(R_STRENGTH.items())),
            "TIER_STRENGTH": dict(sorted(TIER_STRENGTH.items())),
            "a6_excluded_flags": list(A6_EXCLUDED_FLAGS),
            "alpha": list(ALPHA),
            "chronology_offset_years": CHRONOLOGY_OFFSET_YEARS,
            "envelope_widening_reporting_periods": ENVELOPE_WIDENING_REPORTING_PERIODS,
            "freeze_status": "UNTESTED_DEFAULTS_PENDING_FREEZE",
            "max_examples_per_record": MAX_EXAMPLES_PER_RECORD,
            "tau_days": TAU_DAYS,
        },
        "failures": sorted(set(failures)),
        "files": file_block,
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha(Path(__file__).resolve()),
        },
        "inputs": input_block,
        "inv5_reproduction": {"all_match": inv5_all_match, "rows": inv5_rows},
        "language_law": {
            "authored_value_and_field_name_hits": len(authored_hits),
            "banned_tokens": list(LANGUAGE_LAW_TOKENS),
            "policy": LANGUAGE_LAW_POLICY,
            "verbatim_source_quoted_fields": list(VERBATIM_SOURCE_QUOTED_FIELDS),
            "verbatim_token_occurrences": dict(sorted(verbatim_counts.items())),
        },
        "notes": {
            "diagnostics": json.dumps(dict(sorted(diagnostics.items())), sort_keys=True),
            "l5_legilist": (
                "Accepted LegiList source bindings carry only a person page URL, so "
                "they can never name a container and never raise a record to L5. The "
                "person-level binding is recorded as evidence and pinned out of the "
                "tier rule."
            ),
            "office_chronology": (
                "The tier uses the person-lane chronology class, exactly as the ladder "
                "measured it. The per-office chronology used by the ladder's span "
                "tables is emitted alongside it as office_chronology_consistent."
            ),
            "scope": (
                "Candidate plane only. Nothing here is canonical, nothing is an "
                "identity finding, and no tenure is asserted. Consumed by nothing "
                "until ruled."
            ),
            "split_versus_contiguous": (
                "prong.split_clean is the reference Senate rule (every period starts "
                "the day after the previous one ends, for every office the person "
                "held). contiguous is the weaker union property that the person-office "
                "periods form a single run with no internal gap."
            ),
        },
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "prong_failure_distribution": dict(sorted(failure_distribution.items())),
        "review_status": "REVIEW_REQUIRED",
        "rule_version": rule_version,
        "run_id": args.run_id,
        "schema_id": RECEIPT_SCHEMA,
        "sensitivity": {
            "chronology_offset_years": sensitivity_rows,
            "method": (
                "Every dial is swept at 0.5x, 1.0x and 1.5x of its default. The "
                "chronology offset is the only Part A dial that can move an output. "
                "It is a whole number of years, so the two swept points are rounded "
                "outward to the nearest representable offset -- floor below the "
                "default and ceiling above it, giving 0 and 2 around a default of 1 "
                "-- which brackets the default rather than collapsing onto it; the "
                "L4 population per lane is reported at each point. TIER_STRENGTH and "
                "R_STRENGTH are declared here for Part B and provably cannot move any "
                "Part A output, which emits no weight."
            ),
            "r_strength": r_strength_sweep,
            "tier_strength": strength_sweep,
        },
        "stage_id": STAGE_ID,
        "status": "FAIL" if failures else "PASS",
    }
    # The receipt is scanned for authored tokens too.  Three blocks are held
    # out: inputs/files carry on-disk paths, and language_law is the law itself
    # (its banned_tokens list necessarily spells the banned tokens out).
    receipt_hits, _ = scan_language_law(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"inputs", "files", "language_law"}
        },
        leaf_names,
    )
    if receipt_hits and "INV7_LANGUAGE_LAW_AUTHORED_TOKEN" not in receipt["failures"]:
        receipt["failures"] = sorted(
            set(receipt["failures"]) | {"INV7_LANGUAGE_LAW_AUTHORED_TOKEN_IN_RECEIPT"}
        )
        receipt["status"] = "FAIL"
    receipt["language_law"]["authored_value_and_field_name_hits"] = len(
        authored_hits
    ) + len(receipt_hits)

    write_json_atomic(receipt_path, receipt)
    return {
        "output_root": str(output_root),
        "receipt": receipt,
        "receipt_sha256": sha(receipt_path),
    }


# ---------------------------------------------------------------------------
# v3 SPINE LINK STAGE  (--spine-link)
# ---------------------------------------------------------------------------
# WHAT THIS STAGE IS.  An exact, OFFICE-ANCHORED link from every v2 person-office
# record to the re-keyed Hill personnel spine.  It is a POST-STAGE over the v2
# generation, not a rebuild: the v2 rows are read from disk and carried forward
# byte for byte, so no tier is recomputed and none can move.  The only writes are
# the spine_link_* fields this section adds.
#
# WHY A POST-STAGE AND NOT A REBUILD.  Two reasons, both about proof.
#   (1) "Tiers are NOT recomputed" holds by construction rather than by luck: the
#       tier fields in the v3 rows are the same bytes the v2 files carry, and the
#       receipt re-verifies that field by field, per record.
#   (2) INV-5 is still a REPRODUCTION, not a copy.  All 34 rows are re-measured
#       from the EMITTED corpus (summaries, records, registrant rows) plus the A6
#       blocker input -- a different route than the one that produced them -- and
#       each row must equal BOTH the INV5_EXPECTED constant AND the v2 receipt's
#       own measured value.  See :func:`spine_link_inv5`.
#
# WHY IT LIVES IN THIS FILE.  The record's office grouping is ``office_group_key``
# and the record's own name has to come back from the three lane inputs.  A
# separate script would have to reimplement both, which is the drift INV-9
# forbids.
#
# THE NAME KEY, AND THE ONE JUDGEMENT CALL IN THIS STAGE.  The spine's own LDA
# linker (``build_hill_personnel_spine._resolve_by_name_and_office``) buckets on
# ``(chamber, office_key, last, first_class)`` -- the middle initial is NOT in the
# bucket key -- and then filters the bucket with ``middle_compatible``.  This
# stage applies THAT rule, because "the same way the spine does" is what makes
# the two sides joinable at all.  Measured on the v7 generation:
#     strict three-component equality   LINKED  8,598   NOT_FOUND 9,536
#     the spine's own key equality      LINKED 17,837   NOT_FOUND   260
# and 9,334 of the 9,536 strict misses are a middle-initial disagreement alone.
# The cause is structural, not a defect on either side: the H2 and Senate lanes'
# candidate rows carry NO payroll payee string, only the LDA ``display_name``,
# which carries a middle initial in 891/11,788 and 619/6,953 rows respectively,
# while the spine's key carries one for ~82% of persons.  Every LINKED record
# therefore records ``name_key_equality`` EXACT or MIDDLE_COMPATIBLE so a
# strict-only consumer can recover the exact subset with a filter, and the
# receipt reports both histograms.  Nothing is hidden and nothing is promoted.
#
# WHAT THIS ADDS THAT THE SPINE'S OWN LDA LINK DOES NOT.  Grain and time.
# ``lda_spine_links`` is one row per (LDA person, lane) and applies no temporal
# test at all.  This link is per PERSON-OFFICE RECORD and requires the record's
# observation envelope to overlap the span's.  The window test is not decorative:
# it moves 74 records out of AMBIGUOUS into LINKED by discarding same-name
# candidates who were never in the office at the same time.
#
# D-020.  A name is an identity only within an office.  Two or more distinct
# spine persons surviving the office + window + name test is AMBIGUOUS and
# carries NO id -- and so is a record whose own office strings resolve to more
# than one spine office key, which is exactly the same-surname member collision
# the spine's R-1 rule split apart (HON:SMITH covers both S000583 and S001172).
SPINE_LINK_STAGE_ID = "tiered-corroboration-sidecar-part-a-spine-link"
SPINE_LINK_RECORD_SCHEMA = "staffer-network-tiered-person-office-record-v2"
SPINE_LINK_SUMMARY_SCHEMA = "staffer-network-tiered-person-summary-v2"
SPINE_LINK_RECEIPT_SCHEMA = "staffer-network-tiered-corroboration-spine-link-receipt-v1"
DEFAULT_SPINE_LINK_RULE_VERSION = "tiered-corroboration-spine-link-v1"

SPINE_LINK_STATUSES = ("LINKED", "AMBIGUOUS", "NOT_FOUND")
SPINE_LINK_REASONS = (
    "UNIQUE_SPINE_PERSON",
    "OFFICE_KEY_AMBIGUOUS",
    "MULTIPLE_SPINE_PERSONS",
    "NO_LANE_OBSERVATION_FOR_RECORD",
    "NO_NAME_IN_LANE_OBSERVATION",
    "OFFICE_KEY_ABSENT_FROM_SPINE",
    "NAME_ABSENT_IN_OFFICE",
    "NO_CANDIDATE_SURVIVES_WINDOW_OR_MIDDLE_INITIAL",
)

# (office field, payee field, name-standard source) per lane.
SPINE_LINK_LANE_PAYEE = {
    LANE_H1: ("employing_office_raw", "payroll_payee_raw", "payroll_comma"),
    LANE_H2: ("employing_office_candidate", "display_name", "display"),
    LANE_SENATE: ("employing_office_candidate", "display_name", "display"),
}

# INV-7 amendment, v3 only.  Part A emits no display name; a NAME KEY is not a
# display name but it is a name, so the fields below join the verbatim-quoted
# enumeration on the same footing as office_key.  This follows the spine's own
# rule 12 ("NAMES ARE EMITTED HERE"): a link nobody can re-derive is not
# evidence.  Banned-token occurrences inside these values are COUNTED and
# declared, never edited -- a person named Friend keeps their name.
SPINE_LINK_VERBATIM_FIELDS = (
    "spine_link_basis.name_key",
    "spine_link_basis.office_key",
    "spine_link_basis.span_ids[]",
)


def sidecar_office_key(chamber: str, office_raw: str) -> str:
    """The office key a v2 record carries, from that record's own office string.

    House records key on :func:`office_group_key`; Senate records key on the
    whitespace-collapsed uppercase office string.  Both are read straight off
    ``build_person_office_records``, which is why this stage lives here."""

    if chamber == "house":
        return office_group_key(office_raw)
    return " ".join(office_raw.strip().upper().split())


def load_spine_module(path: Path):
    """Import the spine builder so its OWN office-key and middle-compatibility
    rules are reused rather than restated.  Import only: the module guards its
    entry point behind ``__main__``."""

    import importlib.util

    spec = importlib.util.spec_from_file_location("hill_spine_for_link", str(path))
    if spec is None or spec.loader is None:
        raise GateFailure(f"cannot import spine builder from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hill_spine_for_link"] = module
    spec.loader.exec_module(module)
    return module


def bind_input(block: dict[str, Any], label: str, path: Path) -> Path:
    if not path.is_file():
        raise GateFailure(f"missing spine-link input {label}: {path}")
    block[label] = {
        "bytes": path.stat().st_size,
        "path": str(path),
        "sha256": sha(path),
    }
    return path


def windows_overlap(
    left: tuple[str | None, str | None], right: tuple[str | None, str | None]
) -> tuple[bool, str]:
    """ISO date envelopes, inclusive.  An incomplete envelope cannot DISPROVE
    overlap, so it is reported NOT_APPLICABLE and does not veto -- refusing a
    link over a window nobody observed would be an assertion, not a test."""

    a0, a1 = left
    b0, b1 = right
    if not (a0 and a1 and b0 and b1):
        return True, "NOT_APPLICABLE"
    return (a0 <= b1 and b0 <= a1), "APPLIED"


def build_record_payee_index(lane_paths: Mapping[str, Path]):
    """(person, chamber, lane, sidecar office key) -> the office and payee strings
    that record was built from.

    The v2 record carries neither a payee string (INV-7) nor an untruncated
    office list, so the record's own name is recovered from the lane inputs,
    grouped exactly as ``build_person_office_records`` grouped them."""

    index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    stats: Counter = Counter()
    for lane, path in sorted(lane_paths.items()):
        chamber = "senate" if lane == LANE_SENATE else "house"
        office_field, payee_field, payee_source = SPINE_LINK_LANE_PAYEE[lane]
        for record in read_rows(path):
            person = str(record["lda_source_person_id"])
            office_raw = record.get(office_field) or ""
            payee_raw = (record.get(payee_field) or "").strip()
            key = (person, chamber, lane, sidecar_office_key(chamber, office_raw))
            slot = index.setdefault(
                key,
                {"office_raws": set(), "payees": set(), "payee_source": payee_source},
            )
            slot["office_raws"].add(office_raw)
            stats[f"{lane}:rows"] += 1
            if payee_raw:
                slot["payees"].add(payee_raw)
                stats[f"{lane}:rows_with_payee"] += 1
            else:
                stats[f"{lane}:rows_without_payee"] += 1
    stats["slots"] = len(index)
    return index, stats


def build_spine_index(spine_root: Path, standard, spine_module) -> dict[str, Any]:
    """Index the spine on (chamber, office_key, last, first_class) -- the spine's
    own bucket key -- carrying each span's middle initial and envelope.

    Both the v7 key and every legacy v6 key the id map records for that person
    are indexed, so a record whose name lands on a pre-re-key key still links;
    which generation matched is recorded on the link."""

    name_key_by_person: dict[str, str] = {}
    payee_key_by_person: dict[str, dict[str, Any]] = {}
    for row in read_rows(spine_root / "hill_person_spine.ndjson.gz"):
        person_id = row["spine_person_id"]
        name_key_by_person[person_id] = row["name_key"]
        payee_key_by_person[person_id] = row.get("payee_key") or {}

    legacy_keys: defaultdict[str, set[str]] = defaultdict(set)
    id_map_rows = 0
    for row in read_rows(spine_root / "spine_id_map_v6_to_v7.ndjson.gz"):
        id_map_rows += 1
        person_id = row.get("person_id")
        key_v6 = row.get("key_v6")
        if isinstance(person_id, str) and isinstance(key_v6, str) and key_v6:
            legacy_keys[person_id].add(key_v6)

    # The spine's emitted name_key must agree with a lift of its own payee triple
    # wherever the lift is faithful.  A disagreement is REPORTED, never repaired:
    # parts_from_payee_key cannot see what the builder's tokeniser already threw
    # away, and the standard says so in its own docstring.
    payee_key_lift_disagreements = 0
    for person_id, key in payee_key_by_person.items():
        if not key:
            continue
        lifted = standard.name_key(
            standard.parts_from_payee_key(
                key.get("last"), key.get("first"), key.get("middle_initial")
            )
        )
        if lifted != name_key_by_person[person_id]:
            payee_key_lift_disagreements += 1

    buckets: defaultdict[tuple[str, str, str, str], list] = defaultdict(list)
    office_universe: set[tuple[str, str]] = set()
    span_rows = 0
    for ordinal, row in enumerate(
        read_rows(spine_root / "hill_person_office_spans.ndjson.gz")
    ):
        span_rows += 1
        person_id = row["spine_person_id"]
        chamber = row["chamber"]
        office_key = row["office_key"]
        envelope = row.get("envelope") or {}
        window = (envelope.get("start_earliest"), envelope.get("end_latest"))
        office_universe.add((chamber, office_key))
        span_id = f"{person_id}#{ordinal}"
        current = name_key_by_person.get(person_id)
        candidates: list[tuple[str, str]] = []
        if current:
            candidates.append((current, "v7"))
        for legacy in sorted(legacy_keys.get(person_id, ())):
            if legacy != current:
                candidates.append((legacy, "v6_legacy"))
        for key, generation in candidates:
            last, first_class, middle = key.split("|", 2)
            buckets[(chamber, office_key, last, first_class)].append(
                (person_id, span_id, middle or None, window, generation)
            )
    # How much ambiguity the SPINE itself carries, before this stage adds any.
    # A bucket holding two distinct spine persons whose middle initials are
    # mutually compatible is a name that cannot identify a person inside that
    # office; if their windows also overlap, no temporal test can separate them
    # either.  Reported so the AMBIGUOUS count below is attributable to the
    # spine's own structure rather than read as a fault in the link.
    multi_person_buckets = 0
    multi_person_overlapping = 0
    for entries in buckets.values():
        persons = {entry[0] for entry in entries}
        if len(persons) < 2:
            continue
        multi_person_buckets += 1
        collides = False
        for index, left in enumerate(entries):
            for right in entries[index + 1 :]:
                if left[0] == right[0]:
                    continue
                if not spine_module.middle_compatible(left[2], right[2]):
                    continue
                if windows_overlap(left[3], right[3])[0]:
                    collides = True
                    break
            if collides:
                break
        if collides:
            multi_person_overlapping += 1

    return {
        "buckets": buckets,
        "counts": {
            "bucket_keys": len(buckets),
            "distinct_chamber_office_keys": len(office_universe),
            "id_map_rows": id_map_rows,
            "person_office_spans": span_rows,
            "spine_buckets_with_two_or_more_persons": multi_person_buckets,
            "spine_buckets_with_two_or_more_persons_and_overlapping_windows": (
                multi_person_overlapping
            ),
            "spine_payee_key_lift_disagreements": payee_key_lift_disagreements,
            "spine_persons": len(name_key_by_person),
        },
        "office_universe": office_universe,
    }


def link_one_record(
    record: Mapping[str, Any],
    payee_index: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
    spine_index: Mapping[str, Any],
    house_office_key,
    spine_module,
    standard,
) -> dict[str, Any]:
    """The whole rule, for one person-office record."""

    chamber = record["chamber"]
    lane = record["source_lane"]
    person = record["lda_source_person_id"]
    slot = payee_index.get((person, chamber, lane, record["office_key"]))
    if slot is None:
        return {
            "candidate_count": 0,
            "reason": "NO_LANE_OBSERVATION_FOR_RECORD",
            "status": "NOT_FOUND",
        }

    office_keys = {
        house_office_key(raw)
        if chamber == "house"
        else spine_module.senate_office_key(raw)
        for raw in slot["office_raws"]
    }
    if len(office_keys) != 1:
        # The record's own office strings name more than one spine office.  Under
        # D-020 that is not one office, so no id may attach to it.
        return {
            "candidate_count": len(office_keys),
            "reason": "OFFICE_KEY_AMBIGUOUS",
            "status": "AMBIGUOUS",
        }
    spine_office_key = next(iter(office_keys))

    payee_source = slot["payee_source"]
    name_keys = sorted(
        {
            standard.name_key(standard.parse_name(raw, payee_source))
            for raw in slot["payees"]
        }
    )
    name_keys = [key for key in name_keys if key.split("|", 2)[0]]
    if not name_keys:
        return {
            "candidate_count": 0,
            "reason": "NO_NAME_IN_LANE_OBSERVATION",
            "status": "NOT_FOUND",
        }

    envelope = record.get("envelope") or {}
    record_window = (envelope.get("start_earliest"), envelope.get("end_latest"))

    buckets = spine_index["buckets"]
    hits: dict[str, dict[str, set]] = {}
    bucket_seen = False
    for key in name_keys:
        last, first_class, middle = key.split("|", 2)
        middle = middle or None
        bucket = buckets.get((chamber, spine_office_key, last, first_class))
        if not bucket:
            continue
        bucket_seen = True
        for person_id, span_id, span_middle, span_window, generation in bucket:
            if not spine_module.middle_compatible(span_middle, middle):
                continue
            overlap, window_test = windows_overlap(record_window, span_window)
            if not overlap:
                continue
            entry = hits.setdefault(
                person_id,
                {
                    "equality": set(),
                    "generations": set(),
                    "name_keys": set(),
                    "span_ids": set(),
                    "window_tests": set(),
                },
            )
            entry["span_ids"].add(span_id)
            entry["generations"].add(generation)
            entry["name_keys"].add(key)
            entry["equality"].add(
                "EXACT" if (span_middle or "") == (middle or "") else "MIDDLE_COMPATIBLE"
            )
            entry["window_tests"].add(window_test)

    if len(hits) == 1:
        person_id, entry = next(iter(hits.items()))
        generations = sorted(entry["generations"])
        return {
            "basis": {
                "key_generation": "both" if len(generations) > 1 else generations[0],
                "name_key": sorted(entry["name_keys"])[0],
                "name_key_equality": (
                    "EXACT" if "EXACT" in entry["equality"] else "MIDDLE_COMPATIBLE"
                ),
                "office_key": spine_office_key,
                "payee_source": payee_source,
                "span_ids": sorted(entry["span_ids"]),
                "window": {
                    "end_latest": record_window[1],
                    "start_earliest": record_window[0],
                    "test": (
                        "APPLIED"
                        if "APPLIED" in entry["window_tests"]
                        else "NOT_APPLICABLE"
                    ),
                },
            },
            "candidate_count": 1,
            "reason": "UNIQUE_SPINE_PERSON",
            "spine_person_id": person_id,
            "status": "LINKED",
        }
    if len(hits) > 1:
        return {
            "candidate_count": len(hits),
            "reason": "MULTIPLE_SPINE_PERSONS",
            "status": "AMBIGUOUS",
        }
    if (chamber, spine_office_key) not in spine_index["office_universe"]:
        reason = "OFFICE_KEY_ABSENT_FROM_SPINE"
    elif not bucket_seen:
        reason = "NAME_ABSENT_IN_OFFICE"
    else:
        reason = "NO_CANDIDATE_SURVIVES_WINDOW_OR_MIDDLE_INITIAL"
    return {"candidate_count": 0, "reason": reason, "status": "NOT_FOUND"}


def cross_check_lda_spine_links(
    spine_root: Path, person_ids: Mapping[str, set[str]]
) -> dict[str, Any]:
    """Compare this link against the spine's OWN LDA link, which joins on the
    payroll ROW key (``payroll_candidate_id`` / ``payroll_support_digest``) and
    never on a name.

    REPORTED, NEVER GATING, and the asymmetry is expected rather than a defect:
    the spine's link is one row per (LDA person, lane) with no temporal test,
    while this one is per person-office record with a window test, so the two
    populations are not the same question.  A disagreement is a lead, not a
    failure -- which is why nothing here can set a failure code."""

    path = spine_root / "lda_spine_links.ndjson.gz"
    if not path.is_file():
        return {"available": False}
    theirs: defaultdict[str, set[str]] = defaultdict(set)
    for row in read_rows(path):
        if row.get("link_status") == "LINKED_BY_PAYROLL_KEY" and row.get(
            "spine_person_id"
        ):
            theirs[row["lda_source_person_id"]].add(row["spine_person_id"])
    mine = {person: ids for person, ids in person_ids.items() if ids}
    shared = sorted(set(mine) & set(theirs))
    identical = sum(1 for person in shared if mine[person] == theirs[person])
    subset = sum(1 for person in shared if mine[person] <= theirs[person])
    disjoint = sorted(
        person for person in shared if not (mine[person] & theirs[person])
    )
    return {
        "available": True,
        "gating": False,
        "persons_disjoint": len(disjoint),
        "persons_disjoint_examples": disjoint[:20],
        "persons_identical_id_sets": identical,
        "persons_in_both": len(shared),
        "persons_linked_by_the_spine_only": len(set(theirs) - set(mine)),
        "persons_linked_by_this_stage_only": len(set(mine) - set(theirs)),
        "persons_linked_here": len(mine),
        "persons_linked_there": len(theirs),
        "persons_whose_ids_are_a_subset_of_the_spines": subset,
    }


def spine_link_inv5(
    summaries: Sequence[Mapping[str, Any]],
    records: Sequence[Mapping[str, Any]],
    registrants: Sequence[Mapping[str, Any]],
    a6_path: Path,
) -> dict[tuple[str, str], int]:
    """Re-measure all 34 INV-5 metrics FROM THE EMITTED CORPUS.

    Not one tier is recomputed here: every number is counted off rows that
    already carry their tier.  That is what makes this a reproduction and not a
    copy -- the route differs from the one that produced the numbers, so it CAN
    disagree, and the receipt fails when it does."""

    def at_least(letter: str, floor: str) -> bool:
        return TIER_ORDER.index(letter) >= TIER_ORDER.index(floor)

    measured: dict[tuple[str, str], int] = {}
    for lane in ALL_LANES:
        in_lane = [row for row in summaries if row["tier_by_lane"][lane] != "L0"]
        measured[(lane, "people")] = len(in_lane)
        for floor, metric in (
            ("L2", "L2_name_anchored"),
            ("L3", "L3_office_corroborated"),
            ("L4", "L4_chronology_consistent"),
        ):
            measured[(lane, metric)] = sum(
                1 for row in in_lane if at_least(row["tier_by_lane"][lane], floor)
            )

    house = [row for row in summaries if row["tier_by_chamber"]["house"] != "L0"]
    measured[("house_union", "people")] = len(house)
    for floor, metric in (
        ("L2", "L2_name_anchored"),
        ("L3", "L3_office_corroborated"),
        ("L4", "L4_chronology_consistent"),
    ):
        measured[("house_union", metric)] = sum(
            1 for row in house if at_least(row["tier_by_chamber"]["house"], floor)
        )
    measured[("payroll_union", "people")] = sum(
        1 for row in summaries if row["max_tier"] != "L0"
    )
    measured[(LANE_SENATE, "S_split_clean")] = sum(
        1 for row in summaries if row.get("senate_split_clean") is True
    )
    measured[(LANE_SENATE, "L4_and_S")] = sum(
        1
        for row in summaries
        if row.get("senate_split_clean") is True
        and at_least(row["tier_by_lane"][LANE_SENATE], "L4")
    )

    # The three span counts are (person, office) pairs, re-counted off the runs.
    for lane in HOUSE_LANES:
        measured[(lane, "L4_person_office_spans")] = len(
            {
                (row["lda_source_person_id"], row["office_key"])
                for row in records
                if row["source_lane"] == lane
                and row["prong"]["name_unique"]
                and row["prong"]["office_corroborated"]
                and row["prong_evidence"]["chronology"].get(
                    "office_chronology_consistent"
                )
                and row["periods_observed"]
            }
        )
    senate_tier = {
        row["lda_source_person_id"]: row["tier_by_lane"][LANE_SENATE]
        for row in summaries
    }
    senate_split = {
        row["lda_source_person_id"]: row.get("senate_split_clean") for row in summaries
    }
    measured[(LANE_SENATE, "L4_and_S_person_office_spans")] = len(
        {
            (row["lda_source_person_id"], row["office_key"])
            for row in records
            if row["source_lane"] == LANE_SENATE
            and senate_split.get(row["lda_source_person_id"]) is True
            and at_least(senate_tier[row["lda_source_person_id"]], "L4")
        }
    )

    measured[("registrant", "people_with_lda_registrant_association")] = len(registrants)
    measured[("registrant", "hill_and_registrant_people")] = measured[
        ("payroll_union", "people")
    ]
    order = Counter(row.get("hill_registrant_order") for row in registrants)
    for label in ("ORDERED", "OVERLAP_YEAR_GRAIN", "REVERSED"):
        measured[("registrant", f"order_{label}")] = order.get(label, 0)
    measured[("registrant", "ld203_people")] = sum(
        1 for row in registrants if (row.get("ld203") or {}).get("filing_year_count")
    )
    measured[("registrant", "ld203_same_year_name_equal")] = sum(
        1
        for row in registrants
        if (row.get("ld203") or {}).get("same_year_name_equal") is True
    )
    measured[("registrant", "ld203_extends_earlier_people")] = sum(
        1
        for row in registrants
        if ((row.get("ld203") or {}).get("extends_earlier_years") or 0) > 0
    )
    measured[("registrant", "ld203_extends_later_people")] = sum(
        1
        for row in registrants
        if ((row.get("ld203") or {}).get("extends_later_years") or 0) > 0
    )
    measured[("registrant", "fec_same_year_name_equal")] = sum(
        1
        for row in registrants
        if (row.get("fec") or {}).get("same_year_name_equal") is True
    )

    a6_rows = 0
    a6_resolvable_and_both = 0
    for row in read_rows(a6_path):
        a6_rows += 1
        mention = row.get("office_employer_mention") or {}
        dates = row.get("date_range_mention") or {}
        if (
            mention.get("entity_class") in A6_RESOLVABLE_ENTITY_CLASSES
            and dates.get("explicit_start_year") is not None
            and dates.get("explicit_end_year") is not None
        ):
            a6_resolvable_and_both += 1
    measured[("a6_near_candidates", "rows")] = a6_rows
    measured[
        ("a6_near_candidates", "resolvable_entity_and_both_years")
    ] = a6_resolvable_and_both
    return measured


def spine_link_input_paths(args: argparse.Namespace, inputs: dict[str, Any], standard):
    """Bind and hash every file the link stage reads.  Nothing is opened that is
    not in the receipt."""

    live_root = Path(args.live_root)
    lane_root = live_root / "audits" / "staffer_network"
    v2_root = Path(args.v2_root)
    spine_root = Path(args.spine_root)
    paths = {
        "v2_records": bind_input(
            inputs, "v2:tiered_person_office_records", v2_root / RECORD_FILE
        ),
        "v2_summaries": bind_input(
            inputs, "v2:tiered_person_summary", v2_root / SUMMARY_FILE
        ),
        "v2_episodes": bind_input(
            inputs, "v2:filer_asserted_year_episodes", v2_root / EPISODE_FILE
        ),
        "v2_registrants": bind_input(
            inputs, "v2:registrant_side_records", v2_root / REGISTRANT_FILE
        ),
        "v2_receipt": bind_input(inputs, "v2:receipt", v2_root / RECEIPT_FILE),
        "v2_verification_receipt": bind_input(
            inputs, "v2:verification_receipt", Path(args.v2_verification_receipt)
        ),
        "spine_persons": bind_input(
            inputs, "spine:hill_person_spine", spine_root / "hill_person_spine.ndjson.gz"
        ),
        "spine_spans": bind_input(
            inputs,
            "spine:hill_person_office_spans",
            spine_root / "hill_person_office_spans.ndjson.gz",
        ),
        "spine_id_map": bind_input(
            inputs,
            "spine:spine_id_map_v6_to_v7",
            spine_root / "spine_id_map_v6_to_v7.ndjson.gz",
        ),
        "spine_receipt": bind_input(
            inputs, "spine:receipt", spine_root / "hill_personnel_spine_receipt.json"
        ),
        "spine_verification_receipt": bind_input(
            inputs, "spine:verification_receipt", Path(args.spine_verification_receipt)
        ),
        "spine_builder": bind_input(
            inputs, "spine:builder_module", Path(args.spine_builder)
        ),
        # The module actually imported, not a path guessed from live_root: a
        # receipt that pins a file the run did not read is worse than no pin.
        "name_standard": bind_input(
            inputs, "name_standard:module", Path(standard.__file__).resolve()
        ),
        "name_class_table": bind_input(
            inputs, "name_standard:class_table", Path(standard.class_table_path())
        ),
        "house_ledger": bind_input(
            inputs,
            "house_ledger:observations",
            Path(args.house_ledger_root) / "house_personnel_observations.ndjson.gz",
        ),
        "roster_current": bind_input(
            inputs,
            "roster:legislators-current",
            Path(args.roster_root) / "legislators-current.yaml",
        ),
        "roster_historical": bind_input(
            inputs,
            "roster:legislators-historical",
            Path(args.roster_root) / "legislators-historical.yaml",
        ),
        "nickname_table": bind_input(
            inputs, "spine:nickname_table", Path(args.nickname_table)
        ),
        "a6_near_candidates": bind_input(
            inputs,
            "a6_near_candidates",
            lane_root
            / "lda_conservative_bounded_episode_candidates_20260901_b"
            / "lda_conservative_bounded_episode_blockers.ndjson.gz",
        ),
    }
    paths["lanes"] = {
        LANE_H1: bind_input(
            inputs,
            f"lane:{LANE_H1}",
            lane_root
            / "house_sod_pdf_lda_name_matches_2009Q3_2015Q4_20260831_generation2_personnel_only"
            / "house_sod_pdf_lda_name_match_candidates.ndjson.gz",
        ),
        LANE_H2: bind_input(
            inputs,
            f"lane:{LANE_H2}",
            lane_root
            / "lda_house_payroll_matches_2016_2026"
            / "lda_house_payroll_match_candidates.ndjson.gz",
        ),
        LANE_SENATE: bind_input(
            inputs,
            f"lane:{LANE_SENATE}",
            lane_root
            / "lda_senate_payroll_matches_2011_2026_v1"
            / "lda_senate_payroll_match_candidates.ndjson.gz",
        ),
    }
    return paths


def run_spine_link(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise GateFailure(
            f"INV-2 immutable generation: refusing to write into non-empty {output_root}"
        )
    v2_root = Path(args.v2_root)
    spine_root = Path(args.spine_root)
    rule_version = args.spine_link_rule_version
    generated_at = args.generated_at or (
        __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    from fec.staffer_network import name_standard as standard  # noqa: PLC0415

    inputs: dict[str, Any] = {}
    paths = spine_link_input_paths(args, inputs, standard)

    v2_receipt = json.loads(paths["v2_receipt"].read_text(encoding="utf-8"))
    # The lane inputs the v2 receipt bound MUST be the ones read here, or the
    # names recovered for the records would not be those records' own names.
    lane_binding_failures = []
    for label, receipt_key in (
        (f"lane:{LANE_H1}", LANE_H1),
        (f"lane:{LANE_H2}", LANE_H2),
        (f"lane:{LANE_SENATE}", LANE_SENATE),
        ("a6_near_candidates", "a6_near_candidates"),
    ):
        expected = (v2_receipt.get("inputs") or {}).get(receipt_key, {}).get("sha256")
        if not expected:
            # An absent hash used to make this gate vacuously pass, which is the
            # one state it exists to catch: without it nothing proves the names
            # recovered for the records are those records' own names.
            lane_binding_failures.append(receipt_key + ":NOT_BOUND_BY_THE_V2_RECEIPT")
        elif expected != inputs[label]["sha256"]:
            lane_binding_failures.append(receipt_key)

    spine_module = load_spine_module(paths["spine_builder"])
    roster = spine_module.load_roster(Path(args.roster_root))
    nicknames, _ = spine_module.load_nickname_table(paths["nickname_table"])
    house_office_key, house_key_stats, house_key_failures = (
        spine_module.build_house_office_key(paths["house_ledger"], roster, nicknames)
    )

    payee_index, payee_stats = build_record_payee_index(paths["lanes"])
    spine_index = build_spine_index(spine_root, standard, spine_module)

    v2_records = list(read_rows(paths["v2_records"]))
    v2_summaries = list(read_rows(paths["v2_summaries"]))
    v2_registrants = list(read_rows(paths["v2_registrants"]))

    status_counts: Counter = Counter()
    reason_counts: Counter = Counter()
    equality_counts: Counter = Counter()
    generation_counts: Counter = Counter()
    payee_source_counts: Counter = Counter()
    window_test_counts: Counter = Counter()
    by_chamber: Counter = Counter()
    by_tier: Counter = Counter()
    by_lane: Counter = Counter()
    record_field_mismatches: list[str] = []
    person_links: defaultdict[str, dict[str, Any]] = defaultdict(
        lambda: {"ambiguous": 0, "ids": set(), "linked": 0, "not_found": 0}
    )

    v2_record_keys = sorted(v2_records[0].keys()) if v2_records else []
    out_records: list[dict[str, Any]] = []
    for record in v2_records:
        link = link_one_record(
            record, payee_index, spine_index, house_office_key, spine_module, standard
        )
        status = link["status"]
        status_counts[status] += 1
        reason_counts[link["reason"]] += 1
        by_chamber[(record["chamber"], status)] += 1
        by_tier[(record["tier"], status)] += 1
        by_lane[(record["source_lane"], status)] += 1
        person = record["lda_source_person_id"]
        slot = person_links[person]
        slot[status.lower()] += 1

        row = dict(record)
        row["schema_id"] = SPINE_LINK_RECORD_SCHEMA
        row["spine_link_rule_version"] = rule_version
        row["spine_link_status"] = status
        row["spine_link_reason"] = link["reason"]
        row["spine_link_candidate_count"] = link["candidate_count"]
        if status == "LINKED":
            basis = link["basis"]
            row["spine_person_id"] = link["spine_person_id"]
            row["spine_link_basis"] = basis
            slot["ids"].add(link["spine_person_id"])
            equality_counts[basis["name_key_equality"]] += 1
            generation_counts[basis["key_generation"]] += 1
            payee_source_counts[basis["payee_source"]] += 1
            window_test_counts[basis["window"]["test"]] += 1
        else:
            row["spine_person_id"] = None
            row["spine_link_basis"] = None
        # Byte-identity of every carried-forward field.  schema_id is the only v2
        # field this stage may change, because the row shape did change.
        for key in v2_record_keys:
            if key == "schema_id":
                continue
            if compact(row[key]) != compact(record[key]):
                record_field_mismatches.append(
                    f"{person}|{record['office_key']}|{record['run_index']}|{key}"
                )
        out_records.append(row)

    # Measured off the EMITTED rows, not off the loop's own bookkeeping: an
    # invariant a producer checks against its own variables cannot fail.
    unlinked_with_id = sum(
        1
        for row in out_records
        if row["spine_link_status"] != "LINKED" and row["spine_person_id"] is not None
    )
    linked_without_id = sum(
        1
        for row in out_records
        if row["spine_link_status"] == "LINKED" and not row["spine_person_id"]
    )

    out_summaries: list[dict[str, Any]] = []
    summary_field_mismatches: list[str] = []
    v2_summary_keys = sorted(v2_summaries[0].keys()) if v2_summaries else []
    persons_with_link = 0
    for summary in v2_summaries:
        person = summary["lda_source_person_id"]
        slot = person_links.get(person)
        ids = sorted(slot["ids"]) if slot else []
        if ids:
            persons_with_link += 1
        row = dict(summary)
        row["schema_id"] = SPINE_LINK_SUMMARY_SCHEMA
        row["spine_link_rule_version"] = rule_version
        row["spine_person_ids"] = ids
        row["spine_link_summary"] = {
            "ambiguous": slot["ambiguous"] if slot else 0,
            "linked_records": slot["linked"] if slot else 0,
            "not_found": slot["not_found"] if slot else 0,
        }
        for key in v2_summary_keys:
            if key == "schema_id":
                continue
            if compact(row[key]) != compact(summary[key]):
                summary_field_mismatches.append(f"{person}|{key}")
        out_summaries.append(row)

    record_path = output_root / RECORD_FILE
    summary_path = output_root / SUMMARY_FILE
    write_ndjson_gz(record_path, out_records)
    write_ndjson_gz(summary_path, out_summaries)
    # Episodes and registrant rows carry no tier and gain no link.  They are
    # copied so the generation is self-contained, and their hashes must equal
    # v2's exactly.
    episode_path = output_root / EPISODE_FILE
    registrant_path = output_root / REGISTRANT_FILE
    copy_file_streamed(paths["v2_episodes"], episode_path)
    copy_file_streamed(paths["v2_registrants"], registrant_path)

    inv5_measured = spine_link_inv5(
        out_summaries, out_records, v2_registrants, paths["a6_near_candidates"]
    )
    v2_inv5 = {
        (row["lane"], row["metric"]): row["measured"]
        for row in (v2_receipt.get("inv5_reproduction") or {}).get("rows", [])
    }
    inv5_rows = []
    for lane, metric, expected in INV5_EXPECTED:
        measured = inv5_measured.get((lane, metric))
        v2_value = v2_inv5.get((lane, metric))
        inv5_rows.append(
            {
                "expected": expected,
                "lane": lane,
                "match": measured == expected and measured == v2_value,
                "measured": measured,
                "metric": metric,
                "v2_measured": v2_value,
            }
        )
    inv5_all_match = all(row["match"] for row in inv5_rows) and len(inv5_rows) == len(
        INV5_EXPECTED
    )

    files: dict[str, Any] = {}
    for name, path in (
        (RECORD_FILE, record_path),
        (SUMMARY_FILE, summary_path),
        (EPISODE_FILE, episode_path),
        (REGISTRANT_FILE, registrant_path),
    ):
        files[name] = {
            "bytes": path.stat().st_size,
            "rows": sum(1 for _ in read_rows(path)),
            "sha256": sha(path),
        }
    carried_identical = {
        EPISODE_FILE: files[EPISODE_FILE]["sha256"]
        == inputs["v2:filer_asserted_year_episodes"]["sha256"],
        REGISTRANT_FILE: files[REGISTRANT_FILE]["sha256"]
        == inputs["v2:registrant_side_records"]["sha256"],
    }

    spine_receipt = json.loads(paths["spine_receipt"].read_text(encoding="utf-8"))
    spine_verification = json.loads(
        paths["spine_verification_receipt"].read_text(encoding="utf-8")
    )

    failures: list[str] = []
    if lane_binding_failures:
        failures.append("LANE_INPUT_SHA_DOES_NOT_MATCH_V2_RECEIPT")
    if house_key_failures:
        failures.append("HOUSE_OFFICE_KEY_PREPASS_FAILURE")
    if files[RECORD_FILE]["rows"] != len(v2_records):
        failures.append("RECORD_COUNT_NOT_CONSERVED")
    if files[SUMMARY_FILE]["rows"] != SEALED_QUEUE_ROWS:
        failures.append("SUMMARY_COUNT_NOT_SEALED_QUEUE")
    if record_field_mismatches:
        failures.append("V2_RECORD_FIELD_NOT_BYTE_IDENTICAL")
    if summary_field_mismatches:
        failures.append("V2_SUMMARY_FIELD_NOT_BYTE_IDENTICAL")
    if not inv5_all_match:
        failures.append("INV5_LADDER_REPRODUCTION_MISMATCH")
    if unlinked_with_id:
        failures.append("UNLINKED_RECORD_CARRIES_A_SPINE_ID")
    if linked_without_id:
        failures.append("LINKED_RECORD_CARRIES_NO_SPINE_ID")
    if not all(carried_identical.values()):
        failures.append("CARRIED_FILE_NOT_BYTE_IDENTICAL_TO_V2")
    if spine_receipt.get("status") != "PASS":
        failures.append("SPINE_RECEIPT_NOT_PASS")
    if spine_verification.get("status") != "PASS":
        failures.append("SPINE_VERIFICATION_NOT_PASS")
    if v2_receipt.get("status") != "PASS":
        failures.append("V2_RECEIPT_NOT_PASS")
    if sum(status_counts.values()) != len(v2_records):
        failures.append("LINK_HISTOGRAM_DOES_NOT_SUM_TO_RECORDS")
    if set(reason_counts) - set(SPINE_LINK_REASONS):
        failures.append("UNDECLARED_LINK_REASON")

    receipt: dict[str, Any] = {
        # The bindings this generation is required to carry, NAMED rather than
        # left for a reader to find among two dozen input labels.  Every one is
        # also in `inputs`, hashed the same way, and re-hashed by the verifier.
        "bindings": {
            "id_map_sha256": inputs["spine:spine_id_map_v6_to_v7"]["sha256"],
            "name_standard_class_table_sha256": inputs["name_standard:class_table"][
                "sha256"
            ],
            "name_standard_sha256": inputs["name_standard:module"]["sha256"],
            "name_standard_version": getattr(
                standard, "NAME_STANDARD_VERSION", "unknown"
            ),
            "spine_builder_sha256": inputs["spine:builder_module"]["sha256"],
            "spine_person_office_spans_sha256": inputs[
                "spine:hill_person_office_spans"
            ]["sha256"],
            "spine_receipt_sha256": inputs["spine:receipt"]["sha256"],
            "spine_sha256": inputs["spine:hill_person_spine"]["sha256"],
            "spine_verification_receipt_sha256": inputs["spine:verification_receipt"][
                "sha256"
            ],
            "v2_receipt_sha256": inputs["v2:receipt"]["sha256"],
            "v2_records_sha256": inputs["v2:tiered_person_office_records"]["sha256"],
            "v2_summary_sha256": inputs["v2:tiered_person_summary"]["sha256"],
            "v2_verification_receipt_sha256": inputs["v2:verification_receipt"][
                "sha256"
            ],
        },
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "canonical_promotions_zero": True,
        "conservation": {
            "carried_files_byte_identical_to_v2": carried_identical,
            "link_histogram_sums_to_records": (
                sum(status_counts.values()) == len(v2_records)
            ),
            "linked_records_without_a_spine_id": linked_without_id,
            "person_office_records": files[RECORD_FILE]["rows"],
            "person_office_records_v2": len(v2_records),
            "person_summary_rows": files[SUMMARY_FILE]["rows"],
            "sealed_queue_rows": SEALED_QUEUE_ROWS,
            "unlinked_records_carrying_a_spine_id": unlinked_with_id,
            "v2_record_field_mismatch_examples": sorted(record_field_mismatches)[:20],
            "v2_record_fields_byte_identical": not record_field_mismatches,
            "v2_summary_field_mismatch_examples": sorted(summary_field_mismatches)[:20],
            "v2_summary_fields_byte_identical": not summary_field_mismatches,
        },
        "counts": {
            "cross_check_vs_lda_spine_links": cross_check_lda_spine_links(
                spine_root, {p: v["ids"] for p, v in person_links.items()}
            ),
            "house_office_key_prepass": dict(sorted(house_key_stats.items())),
            "link_by_chamber": {
                f"{chamber}|{status}": count
                for (chamber, status), count in sorted(by_chamber.items())
            },
            "link_by_lane": {
                f"{lane}|{status}": count
                for (lane, status), count in sorted(by_lane.items())
            },
            "link_by_tier": {
                f"{tier}|{status}": count
                for (tier, status), count in sorted(by_tier.items())
            },
            "link_key_generation": dict(sorted(generation_counts.items())),
            "link_name_key_equality": dict(sorted(equality_counts.items())),
            "link_payee_source": dict(sorted(payee_source_counts.items())),
            "link_reason": dict(sorted(reason_counts.items())),
            "link_status": {
                status: status_counts.get(status, 0) for status in SPINE_LINK_STATUSES
            },
            "link_window_test": dict(sorted(window_test_counts.items())),
            "persons_with_at_least_one_link": persons_with_link,
            "record_payee_index": dict(sorted(payee_stats.items())),
            "spine_index": spine_index["counts"],
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "row_order": "carried from the v2 files unchanged, row for row",
            "span_id_recipe": (
                "<spine_person_id>#<zero-based line ordinal in the spine's "
                "hill_person_office_spans.ndjson.gz>"
            ),
        },
        "failures": sorted(set(failures)),
        "files": files,
        "generated_at": generated_at,
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha(Path(__file__).resolve()),
        },
        "inputs": dict(sorted(inputs.items())),
        "inv5_reproduction": {
            "all_match": inv5_all_match,
            "note": (
                "Re-measured from the EMITTED corpus (summaries, records, "
                "registrant rows) plus the A6 blocker input. This stage "
                "recomputes no tier; every row must equal both the "
                "INV5_EXPECTED constant and the v2 receipt's measured value."
            ),
            "rows": inv5_rows,
        },
        "link_rule": {
            "ambiguity_law": (
                "D-020: a name is an identity only within an office. Two or more "
                "distinct spine persons surviving the test, or a record whose own "
                "office strings resolve to more than one spine office key, is "
                "AMBIGUOUS and carries no id."
            ),
            "middle_initial": (
                "middle_compatible, taken from the spine's own "
                "_resolve_by_name_and_office. Every LINKED row records "
                "name_key_equality EXACT or MIDDLE_COMPATIBLE, so the "
                "three-component-equal subset is recoverable with a filter."
            ),
            "name_key_source_by_lane": {
                lane: {"office_field": office, "payee_field": payee, "source": source}
                for lane, (office, payee, source) in sorted(
                    SPINE_LINK_LANE_PAYEE.items()
                )
            },
            "office_key": (
                "the spine builder's own HouseOfficeKey / senate_office_key, "
                "applied to the record's own office strings"
            ),
            "tiers_recomputed": False,
            "window": "record envelope vs span envelope, inclusive, ISO day grain",
        },
        "promotion_policy": (
            "Every emitted row keeps review_status REVIEW_REQUIRED, "
            "canonical_eligible false and canonical_employment_promoted false. A "
            "spine link is an identity POINTER, not an employment finding: "
            "D-021's gates E1-E3 are untouched by it."
        ),
        "review_status": "REVIEW_REQUIRED",
        "rule_version": rule_version,
        "run_id": args.run_id,
        "schema_id": SPINE_LINK_RECEIPT_SCHEMA,
        "spine_generation": {
            "primary": str(spine_root),
            "provisional": bool(args.spine_generation_provisional),
            "receipt_generated_at": spine_receipt.get("generated_at"),
            "receipt_rule_version": spine_receipt.get("rule_version"),
            "receipt_run_id": spine_receipt.get("run_id"),
            "verification_status": spine_verification.get("status"),
        },
        "stage_id": SPINE_LINK_STAGE_ID,
        "status": "PASS",
        "tier_rule_version": v2_receipt.get("rule_version", DEFAULT_RULE_VERSION),
        "v2_generation": {
            "primary": str(v2_root),
            "receipt_sha256": inputs["v2:receipt"]["sha256"],
            "receipt_status": v2_receipt.get("status"),
        },
    }
    if receipt["failures"]:
        receipt["status"] = "FAIL"

    leaf_names = verbatim_field_names() | {
        entry.replace("[]", "").split(".")[-1] for entry in SPINE_LINK_VERBATIM_FIELDS
    }
    authored_hits, verbatim_counts = scan_language_law(out_records, leaf_names)
    summary_hits, summary_verbatim = scan_language_law(out_summaries, leaf_names)
    authored_hits = authored_hits + summary_hits
    verbatim_counts.update(summary_verbatim)
    receipt["language_law"] = {
        "authored_hit_examples": sorted(set(authored_hits))[:20],
        "authored_hits": len(authored_hits),
        "policy": (
            LANGUAGE_LAW_POLICY
            + " AMENDED FOR THE v3 LINK STAGE: a name KEY is emitted on every "
            "LINKED row, because a link nobody can re-derive is not evidence. It "
            "is a folded quotation of the payroll or LDA name, declared verbatim "
            "on the same footing as office_key, and its banned-token occurrences "
            "are counted rather than edited."
        ),
        "verbatim_source_quoted_fields": sorted(
            set(VERBATIM_SOURCE_QUOTED_FIELDS) | set(SPINE_LINK_VERBATIM_FIELDS)
        ),
        "verbatim_token_occurrences": dict(sorted(verbatim_counts.items())),
    }
    if authored_hits:
        receipt["failures"] = sorted(
            set(receipt["failures"]) | {"INV7_LANGUAGE_LAW_AUTHORED_TOKEN"}
        )
        receipt["status"] = "FAIL"

    receipt_path = output_root / RECEIPT_FILE
    write_json_atomic(receipt_path, receipt)
    return {
        "output_root": str(output_root),
        "receipt": receipt,
        "receipt_sha256": sha(receipt_path),
    }


def main_spine_link(args: argparse.Namespace) -> int:
    result = run_spine_link(args)
    receipt = result["receipt"]
    print(f"output_root: {result['output_root']}")
    print(f"status: {receipt['status']}")
    print(f"failures: {receipt['failures']}")
    print("files:")
    for name, entry in sorted(receipt["files"].items()):
        print(
            f"  {name}: rows={entry['rows']} bytes={entry['bytes']} "
            f"sha256={entry['sha256']}"
        )
    print("link_status: " + json.dumps(receipt["counts"]["link_status"], sort_keys=True))
    print("link_reason: " + json.dumps(receipt["counts"]["link_reason"], sort_keys=True))
    print(
        "link_by_chamber: "
        + json.dumps(receipt["counts"]["link_by_chamber"], sort_keys=True)
    )
    print(
        "link_by_tier: " + json.dumps(receipt["counts"]["link_by_tier"], sort_keys=True)
    )
    print(
        "name_key_equality: "
        + json.dumps(receipt["counts"]["link_name_key_equality"], sort_keys=True)
    )
    print(
        "persons_with_at_least_one_link: "
        f"{receipt['counts']['persons_with_at_least_one_link']}"
    )
    print("inv5_reproduction:")
    for row in receipt["inv5_reproduction"]["rows"]:
        flag = "OK " if row["match"] else "DIFF"
        print(
            f"  {flag} {row['lane']:<28s} {row['metric']:<42s} "
            f"expected={row['expected']:<6d} measured={row['measured']} "
            f"v2={row['v2_measured']}"
        )
    print(f"inv5_all_match: {receipt['inv5_reproduction']['all_match']}")
    print(
        "spine_generation_provisional: "
        f"{receipt['spine_generation']['provisional']}"
    )
    print(f"receipt_sha256: {result['receipt_sha256']}")
    return 0 if receipt["status"] == "PASS" else 1


DEFAULT_SPINE_ROOT = (
    DEFAULT_LIVE_ROOT
    / "audits"
    / "staffer_network"
    / "hill_personnel_spine_20260907_v7_primary"
)
DEFAULT_V2_ROOT = (
    DEFAULT_LIVE_ROOT
    / "audits"
    / "staffer_network"
    / "tiered_corroboration_sidecar_20260902_v2_primary"
)


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--live-root", type=Path, default=DEFAULT_LIVE_ROOT)
    parser.add_argument("--appdata-root", type=Path, default=DEFAULT_APPDATA_ROOT)
    parser.add_argument("--rule-version", default=DEFAULT_RULE_VERSION)
    parser.add_argument("--run-id", default="unbound")
    parser.add_argument(
        "--spine-link",
        action="store_true",
        help="run the v3 spine-link post-stage over an existing v2 generation",
    )
    parser.add_argument("--v2-root", type=Path, default=DEFAULT_V2_ROOT)
    parser.add_argument(
        "--v2-verification-receipt",
        type=Path,
        default=DEFAULT_LIVE_ROOT
        / "audits"
        / "staffer_network"
        / "tiered_corroboration_sidecar_20260902_v2_verification"
        / "tiered_corroboration_verification_receipt.json",
    )
    parser.add_argument("--spine-root", type=Path, default=DEFAULT_SPINE_ROOT)
    parser.add_argument(
        "--spine-verification-receipt",
        type=Path,
        default=DEFAULT_LIVE_ROOT
        / "audits"
        / "staffer_network"
        / "hill_personnel_spine_20260907_v7_verification"
        / "hill_personnel_spine_verification_receipt.json",
    )
    parser.add_argument(
        "--spine-builder",
        type=Path,
        default=Path(__file__).resolve().parent / "build_hill_personnel_spine.py",
    )
    parser.add_argument(
        "--house-ledger-root",
        type=Path,
        default=DEFAULT_LIVE_ROOT
        / "audits"
        / "staffer_network"
        / "house_personnel_ledger_20260903_v5_primary",
    )
    parser.add_argument(
        "--roster-root",
        type=Path,
        default=DEFAULT_LIVE_ROOT
        / "data"
        / "staffer_network"
        / "reference"
        / "congress-legislators"
        / "750c0608efb6ef1fc3257ba72c99af3771d35088",
    )
    parser.add_argument(
        "--nickname-table",
        type=Path,
        default=DEFAULT_LIVE_ROOT
        / "data"
        / "staffer_network"
        / "reference"
        / "first_name_nicknames_v1.json",
    )
    parser.add_argument(
        "--spine-link-rule-version", default=DEFAULT_SPINE_LINK_RULE_VERSION
    )
    parser.add_argument("--generated-at", default=None)
    parser.add_argument(
        "--spine-generation-provisional",
        action="store_true",
        help=(
            "pin spine_generation.provisional true: the spine this link was built "
            "against had not landed its own rebuild receipt"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.spine_link:
        return main_spine_link(args)
    result = run(args)
    receipt = result["receipt"]
    print(f"output_root: {result['output_root']}")
    print(f"status: {receipt['status']}")
    print(f"failures: {receipt['failures']}")
    print("files:")
    for name, entry in sorted(receipt["files"].items()):
        print(f"  {name}: rows={entry['rows']} bytes={entry['bytes']} sha256={entry['sha256']}")
    print("counts.tier_people_by_lane:")
    print("  " + json.dumps(receipt["counts"]["tier_people_by_lane"], sort_keys=True))
    print("inv5_reproduction:")
    for row in receipt["inv5_reproduction"]["rows"]:
        flag = "OK " if row["match"] else "DIFF"
        print(
            f"  {flag} {row['lane']:<28s} {row['metric']:<38s} "
            f"expected={row['expected']:<6d} measured={row['measured']}"
        )
    print(f"inv5_all_match: {receipt['inv5_reproduction']['all_match']}")
    print(f"receipt_sha256: {result['receipt_sha256']}")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
