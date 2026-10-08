#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify the Part A tiered corroboration sidecar.

This script does not import the builder.  It re-derives every prong, every
person-office run, every summary row, every filer-asserted episode and every
registrant-side record straight from the hash-bound inputs, and requires the
re-derived rows to equal the emitted rows exactly -- a 100% pass, not a sample.
It also recomputes every hash, compares the primary and twin generations byte
for byte, runs the anti-promotion tripwire over every row and the receipt,
greps the language law, checks conservation against the sealed 25,340-person
queue, and re-checks the ladder reproduction table.

Exit code 0 on PASS, 1 on FAIL.  The verification receipt is written to
``<generation>_verification/tiered_corroboration_verification_receipt.json``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

import yaml


SCHEMA_ID = "staffer-network-tiered-corroboration-independent-verification-v1"
STAGE_ID = "tiered-corroboration-sidecar-part-a"
#: The v2 rule version this verifier is written against.  Pinned here, not
#: read from the receipt: ``rederive`` is handed the receipt's own
#: ``rule_version`` and stamps it onto every re-derived row, so the
#: row-by-row comparison can never disagree about that field.
EXPECTED_RULE_VERSION = "tiered-corroboration-v2"
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
PAYLOAD_FILES = (RECORD_FILE, SUMMARY_FILE, EPISODE_FILE, REGISTRANT_FILE)
VERIFICATION_FILE = "tiered_corroboration_verification_receipt.json"

SEALED_QUEUE_ROWS = 25340
LANE_H1 = "house_sod_2009q3_2015q4"
LANE_H2 = "house_payroll_2016_2026"
LANE_SENATE = "senate_payroll_2011_2026"
HOUSE_LANES = (LANE_H1, LANE_H2)
ALL_LANES = (LANE_H1, LANE_H2, LANE_SENATE)
TIER_ORDER = ("L0", "L1", "L2", "L3", "L4", "L5")

CHRONOLOGY_OFFSET_YEARS = 1
ENVELOPE_WIDENING_REPORTING_PERIODS = 1
MAX_EXAMPLES_PER_RECORD = 3
A6_EXCLUDED_FLAGS = frozenset(
    {
        "AMBIGUOUS_ROLE_ABBREVIATION",
        "DATE_RANGE_REVERSED",
        "MENTION_SPANS_OVERLAP",
        "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED",
    }
)
A6_RESOLVABLE_ENTITY_CLASSES = frozenset(
    {"COMMITTEE_CANDIDATE", "MEMBER_OFFICE_CANDIDATE"}
)

LANGUAGE_LAW_TOKENS = (
    "access",
    "causal",
    "friend",
    "ideolog",
    "influence",
    "predict",
)
# Independently restated here: the leaf field names whose values are quoted
# verbatim from a source ledger and are therefore exempt from the language law.
VERBATIM_LEAF_NAMES = frozenset(
    {
        "corroborating_payroll_office_examples",
        "employer_name",
        "employer_name_normalized",
        "matched_employer_name",
        "matched_registrant_name",
        "matched_token",
        "member_surname_text",
        "office_key",
        "office_normalized",
        "office_raw_examples",
        "office_text",
        "politico_matched_token",
        "profile_matched_employer",
        "role_text",
        "title_examples",
    }
)

INV5_EXPECTED = {
    (LANE_H1, "people"): 2135,
    (LANE_H1, "L2_name_anchored"): 1685,
    (LANE_H1, "L3_office_corroborated"): 678,
    (LANE_H1, "L4_chronology_consistent"): 678,
    (LANE_H1, "L4_person_office_spans"): 861,
    (LANE_H2, "people"): 3355,
    (LANE_H2, "L2_name_anchored"): 2125,
    (LANE_H2, "L3_office_corroborated"): 909,
    (LANE_H2, "L4_chronology_consistent"): 858,
    (LANE_H2, "L4_person_office_spans"): 1270,
    (LANE_SENATE, "people"): 2798,
    (LANE_SENATE, "L2_name_anchored"): 1710,
    (LANE_SENATE, "L3_office_corroborated"): 667,
    (LANE_SENATE, "L4_chronology_consistent"): 640,
    (LANE_SENATE, "S_split_clean"): 2195,
    (LANE_SENATE, "L4_and_S"): 470,
    (LANE_SENATE, "L4_and_S_person_office_spans"): 754,
    ("house_union", "people"): 4392,
    ("house_union", "L2_name_anchored"): 2878,
    ("house_union", "L3_office_corroborated"): 1195,
    ("house_union", "L4_chronology_consistent"): 1137,
    ("payroll_union", "people"): 6101,
    ("a6_near_candidates", "rows"): 3090,
    ("a6_near_candidates", "resolvable_entity_and_both_years"): 2525,
    ("registrant", "people_with_lda_registrant_association"): 25340,
    ("registrant", "hill_and_registrant_people"): 6101,
    ("registrant", "order_ORDERED"): 4199,
    ("registrant", "order_OVERLAP_YEAR_GRAIN"): 1821,
    ("registrant", "order_REVERSED"): 81,
    ("registrant", "ld203_people"): 22754,
    ("registrant", "ld203_same_year_name_equal"): 22715,
    ("registrant", "ld203_extends_earlier_people"): 269,
    ("registrant", "ld203_extends_later_people"): 2121,
    ("registrant", "fec_same_year_name_equal"): 36,
}


class VerificationFailure(RuntimeError):
    pass


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
        for line in stream:
            if line.strip():
                yield json.loads(line)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Independent rule restatement
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[A-Z0-9]+")
_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def ascii_tokens(value: str) -> tuple[str, ...]:
    folded = (
        unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    )
    parts = _TOKEN_RE.findall(folded.upper())
    while parts and parts[-1] in _SUFFIXES:
        parts.pop()
    return tuple(parts)


def split_queue_name(value: str):
    parts = ascii_tokens(value)
    if len(parts) < 2:
        return None
    return parts[0], parts[-1], parts[1:-1]


def split_payroll_name(value: str):
    parts = ascii_tokens(value)
    if len(parts) < 2:
        return None
    return parts[1], parts[0], tuple(p for p in parts[2:] if p not in _SUFFIXES)


def middles_compatible(left, right) -> bool:
    if not left or not right:
        return True
    return left[0][0] == right[0][0]


_LEADING_YEAR = re.compile(r"^\s*(19|20)\d{2}\s+")
_OFFICE_WORD = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")


def house_normalize_office(raw: str) -> str:
    text = _LEADING_YEAR.sub("", raw or "").strip()
    text = text.replace("’", "'")
    text = re.sub(r"[—']?\s*Con\.?\s*$", "", text, flags=re.IGNORECASE).strip()
    text = text.replace("&", " AND ")
    return re.sub(r"\s+", " ", text).strip().upper()


def house_is_member_office(normalized: str) -> bool:
    return normalized[:4] == "HON." or normalized[:4] == "HON "


def house_surname_forms(normalized: str) -> list[str]:
    tail = normalized.split(".", 1)[1] if normalized[:4] == "HON." else normalized[3:]
    kept = []
    for raw_token in _OFFICE_WORD.findall(tail):
        token = raw_token.strip(".").strip(",")
        if not token or token.upper() in _SUFFIXES:
            continue
        kept.append(token)
    if not kept:
        return []
    surname = kept[-1]
    forms = {surname.upper()}
    if "-" in surname:
        forms.update(part.upper() for part in surname.split("-") if len(part) > 2)
    return sorted(forms)


def house_first_and_surname(normalized: str) -> tuple[str | None, str | None]:
    tail = normalized.split(".", 1)[1] if normalized[:4] == "HON." else normalized[3:]
    kept = []
    for raw_token in _OFFICE_WORD.findall(tail):
        token = raw_token.strip(".").strip(",")
        if not token or token.upper() in _SUFFIXES:
            continue
        if len(token.replace(".", "")) <= 1:
            continue
        kept.append(token)
    if not kept:
        return None, None
    return (kept[0] if len(kept) >= 2 else None), kept[-1]


def house_office_group(raw: str) -> str:
    normalized = house_normalize_office(raw)
    if house_is_member_office(normalized):
        forms = house_surname_forms(normalized)
        return "HON:" + (max(forms, key=len) if forms else normalized)
    return normalized


HOUSE_OFFICE_PHRASES = {
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

HOUSE_LEADERSHIP = frozenset(
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
HOUSE_ADMIN = frozenset(
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
_HOUSE_COMMITTEE_SHAPE = re.compile(r"(?:^|\W)(COMM|COMMITTEE)(?:\W|$)")


def casefolded_phrase_present(blob: str, phrase: str) -> bool:
    return (
        re.search(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", blob)
        is not None
    )


def house_office_check(raw: str, blob: str) -> tuple[bool, str, str]:
    normalized = house_normalize_office(raw)
    if not normalized:
        return False, "EMPTY_OFFICE", ""
    if house_is_member_office(normalized):
        forms = house_surname_forms(normalized)
        if not forms:
            return False, "HON_NO_SURNAME_PARSED", normalized
        for form in forms:
            if casefolded_phrase_present(blob, form.lower()):
                return True, "MEMBER_SURNAME_MATCH", form
        return False, "MEMBER_SURNAME_NOT_FOUND", "/".join(forms)
    phrases = HOUSE_OFFICE_PHRASES.get(normalized)
    if not phrases:
        return False, "COMMITTEE_FAMILY_UNMAPPED", normalized
    for phrase in phrases:
        if casefolded_phrase_present(blob, phrase.lower()):
            return True, "COMMITTEE_KEYWORD_MATCH", phrase
    return False, "COMMITTEE_KEYWORD_NOT_FOUND", normalized


def house_container(raw: str) -> str:
    normalized = house_normalize_office(raw)
    if not normalized:
        return "unresolved"
    if house_is_member_office(normalized):
        return "member_office"
    if normalized in HOUSE_LEADERSHIP:
        return "leadership"
    if normalized in HOUSE_ADMIN:
        return "admin"
    if normalized in HOUSE_OFFICE_PHRASES or _HOUSE_COMMITTEE_SHAPE.search(normalized):
        return "committee"
    return "unresolved"


_SENATE_SUFFIX = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
_SENATOR = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
_INTERN = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
_SENATE_COMMITTEE_STOPWORDS = {
    "JOINT", "SELECT", "SPECIAL", "STANDING", "SUB", "SUBCOMMITTEE",
    "COMMITTEE", "ON", "OF", "THE", "AND",
}
_SENATE_LEADERSHIP = (
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


def senate_office_token(office: str) -> str | None:
    upper = (office or "").strip().upper()
    match = _SENATOR.match(upper)
    if match:
        tail = _SENATE_SUFFIX.sub("", match.group(1)).strip()
        parts = [p.strip(".,") for p in tail.split() if p.strip(".,")]
        return parts[-1] if parts else None
    match = _INTERN.match(upper)
    if match:
        return match.group(1).strip().strip(".,") or None
    if "COMMITTEE" in upper:
        words = [
            w
            for w in re.findall(r"[A-Z]+", upper)
            if w not in _SENATE_COMMITTEE_STOPWORDS
        ]
        return max(words, key=len) if words else None
    if upper == "APPROPRIATIONS":
        return upper
    return None


def upper_word_present(token: str | None, text_upper: str) -> bool:
    if not token:
        return False
    return re.search(r"\b" + re.escape(token) + r"\b", text_upper) is not None


def senate_first_and_surname(office: str) -> tuple[str | None, str | None]:
    upper = (office or "").strip().upper()
    match = _SENATOR.match(upper)
    if match:
        tail = _SENATE_SUFFIX.sub("", match.group(1)).strip()
        parts = [p.strip(".,") for p in tail.split() if p.strip(".,")]
        parts = [p for p in parts if len(p.replace(".", "")) > 1]
        if not parts:
            return None, None
        return (parts[0] if len(parts) >= 2 else None), parts[-1]
    match = _INTERN.match(upper)
    if match:
        surname = match.group(1).strip().strip(".,")
        return (None, surname) if surname else (None, None)
    return None, None


def senate_container(office: str) -> str:
    upper = (office or "").strip().upper()
    if not upper:
        return "unresolved"
    if _SENATOR.match(upper) or _INTERN.match(upper):
        return "member_office"
    if "COMMITTEE" in upper or upper == "APPROPRIATIONS":
        return "committee"
    if any(phrase in upper for phrase in _SENATE_LEADERSHIP):
        return "leadership"
    return "admin"


_PROFILE_STOPWORDS = {
    "COMMITTEE", "COMM", "ON", "OF", "THE", "AND", "OFFICE", "CHIEF", "ADMIN",
    "ADMINISTRATION", "OFCR", "HOUSE", "SPEAKER", "SERVICE", "SERVICES",
}


def house_profile_tokens(office: str) -> list[str]:
    upper = re.sub(r"^(19|20)\d{2}\s+", "", (office or "").strip().upper())
    return [
        w
        for w in re.findall(r"[A-Z]+", upper)
        if w not in _PROFILE_STOPWORDS and len(w) >= 4
    ]


def normalized_org_name(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.casefold()).split())


# generation v2 (2026-09-02, Paul's authorisation "Extend the nickname table,
# resolve Bill Nelson"): the nickname table is a hash-bound reference file
# (INV-3 input "nickname_table"), independently re-derived here rather than
# imported from the builder -- see build_tiered_corroboration_sidecar.py for
# the parallel design note.  This mirrors that implementation independently:
# a candidate's name.nickname and the first token of name.official_full are
# additional resolution forms, and a resolved candidate must have a term
# whose type matches the chamber and whose [start, end] overlaps the
# record's observation window (INV-6 extension).
NICKNAME_TABLE_SCHEMA = "staffer-network-first-name-nickname-table-v1"
_TERM_TYPE_BY_CHAMBER = {"house": "rep", "senate": "sen"}


def load_nickname_table(path: Path) -> dict[str, tuple[str, ...]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_id") != NICKNAME_TABLE_SCHEMA:
        raise VerificationFailure(
            f"nickname table schema mismatch: {path}: {payload.get('schema_id')!r}"
        )
    entries = payload.get("entries") or {}
    return {
        str(key).casefold(): tuple(str(v).casefold() for v in values)
        for key, values in entries.items()
    }


def fold_name(value: str | None) -> str:
    """Loose fold for first-name comparisons: casefold and drop every
    non-alphanumeric character, so 'J.D.' and 'JD' compare equal.
    """
    return re.sub(r"[^a-z0-9]", "", (value or "").casefold())


def nickname_expansions(
    value: str, nickname_table: Mapping[str, Sequence[str]]
) -> set[str]:
    folded = fold_name(value)
    forms = {folded}
    for formal in nickname_table.get(folded, ()):
        forms.add(fold_name(formal))
    return forms


def candidate_first_name_forms(
    candidate: Mapping[str, Any], nickname_table: Mapping[str, Sequence[str]]
) -> set[str]:
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


_A6_TITLE = re.compile(
    r'\b(?:Rep\.?|Sen\.?|Senator|Representative|Congressman|Congresswoman|Cong\.|Hon\.?)\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)
_A6_OFFICE = re.compile(
    r'\bOffice of(?:\s+(?:Sen\.?|Senator|Rep\.?|Representative|Congressman|Congresswoman))?\s+'
    r'([A-Z][A-Za-z\'\.-]*(?:\s+[A-Z][A-Za-z\'\.-]*){0,3})'
)
_A6_SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}
_A6_SENATE_TITLE = re.compile(r"\b(?:SEN\.?|SENATOR)\b")
_A6_HOUSE_TITLE = re.compile(
    r"\b(?:REP\.?|REPRESENTATIVE|CONGRESSMAN|CONGRESSWOMAN|CONG\.)\b"
)


def a6_chamber_hint(office_text: str) -> str | None:
    upper = (office_text or "").upper()
    if _A6_SENATE_TITLE.search(upper):
        return "senate"
    if _A6_HOUSE_TITLE.search(upper):
        return "house"
    return None


def a6_first_and_surname(captured: str) -> tuple[str | None, str | None]:
    kept = []
    for token in (captured or "").strip().rstrip(".,;").split():
        trimmed = token.strip().rstrip(".,;")
        if trimmed.lower() in _A6_SUFFIXES:
            continue
        if len(trimmed.replace(".", "")) <= 1:
            continue
        kept.append(trimmed)
    if not kept:
        return None, None
    return (kept[0] if len(kept) >= 2 else None), kept[-1]


def _parse_term_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except Exception:
        return None


def build_roster(
    current: Path, historical: Path, *, counts: dict[str, int] | None = None
) -> dict[str, list[dict[str, Any]]]:
    index: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in (current, historical):
        for person in yaml.safe_load(path.read_text(encoding="utf-8")):
            bioguide = (person.get("id") or {}).get("bioguide")
            if not bioguide:
                continue
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
                start_date = _parse_term_date(term.get("start"))
                end_date = _parse_term_date(term.get("end"))
                if start_date is not None and end_date is not None:
                    terms.append(
                        {"type": term.get("type"), "start": start_date, "end": end_date}
                    )
            if not years:
                continue
            name = person.get("name") or {}
            index[str(name.get("last", "")).upper()].append(
                {
                    "bioguide": bioguide,
                    "first": str(name.get("first", "")),
                    "nickname": name.get("nickname"),
                    "official_full": name.get("official_full"),
                    "terms": terms,
                }
            )
    return {key: sorted(value, key=lambda item: item["bioguide"]) for key, value in index.items()}


def resolve_bioguide(
    first: str | None,
    surname: str | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nickname_table: Mapping[str, Sequence[str]],
    *,
    chamber: str | None,
    window_start: date | None,
    window_end: date | None,
) -> tuple[str | None, str]:
    if not surname:
        return None, "UNRESOLVED_SURNAME_NOT_PARSED"
    candidates = roster.get(surname.upper())
    if not candidates:
        return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"
    if first:
        matched = [
            c for c in candidates if first_name_matches(first, c, nickname_table)
        ]
        if not matched:
            return None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
        if len(matched) == 1:
            candidate = matched[0]
            if candidate_has_overlapping_term(candidate, chamber, window_start, window_end):
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


_QUARTER = re.compile(r"^(\d{4})Q(\d)$")


def parse_quarter(value: str | None):
    match = _QUARTER.match(value or "")
    if not match:
        return None
    quarter = int(match.group(2))
    if not 1 <= quarter <= 4:
        return None
    return int(match.group(1)), quarter


def quarter_index(key) -> int:
    return key[0] * 4 + key[1] - 1


def index_quarter(index: int):
    return index // 4, index % 4 + 1


def quarter_span(key) -> tuple[date, date]:
    year, quarter = key
    start = date(year, 3 * quarter - 2, 1)
    end = (
        date(year, 12, 31)
        if quarter == 4
        else date(year, 3 * quarter + 1, 1) - timedelta(days=1)
    )
    return start, end


def parse_day(value: str | None):
    if not value:
        return None
    try:
        parts = [int(p) for p in value.split("-")]
        return date(parts[0], parts[1], parts[2])
    except Exception:
        return None


def semiannual_window(day: date) -> tuple[date, date]:
    if day.month >= 10:
        return date(day.year, 10, 1), date(day.year + 1, 3, 31)
    if day.month <= 3:
        return date(day.year - 1, 10, 1), date(day.year, 3, 31)
    return date(day.year, 4, 1), date(day.year, 9, 30)


def strictly_adjacent(pairs) -> bool:
    for index in range(1, len(pairs)):
        previous_end = pairs[index - 1][1]
        current_start = pairs[index][0]
        if previous_end is None or current_start is None:
            return False
        if current_start != previous_end + timedelta(days=1):
            return False
    return True


def first_year(value: str | None):
    match = re.match(r"^(\d{4})-", value or "")
    return int(match.group(1)) if match else None


def tier_rank(letter: str) -> int:
    return TIER_ORDER.index(letter)


def letter_for(name_unique, office_ok, chronology, multi) -> str:
    if not name_unique:
        return "L1"
    if not office_ok:
        return "L2"
    if chronology != "CONSISTENT":
        return "L3"
    return "L5" if multi else "L4"


# ---------------------------------------------------------------------------
# Independent re-derivation
# ---------------------------------------------------------------------------
def rederive(inputs: Mapping[str, Path], rule_version: str):
    queue: dict[str, dict[str, Any]] = {}
    queue_index: defaultdict[tuple[str, str], list[tuple[str, tuple, str]]] = defaultdict(
        list
    )
    queue_order: list[str] = []
    for row in read_rows(inputs["employment_lookup_queue"]):
        person = str(row["lda_source_person_id"])
        values = row.get("covered_position_values") or []
        queue[person] = {
            "blob": " | ".join(values).casefold(),
            "upper": " ".join(values).upper(),
            "substantive": any((value or "").strip() for value in values),
            "filing_years": list(row.get("filing_years") or []),
        }
        queue_order.append(person)
        parsed = split_queue_name(row.get("display_name") or "")
        if parsed:
            queue_index[(parsed[0], parsed[1])].append(
                (person, parsed[2], row.get("display_name") or "")
            )

    roster_counts: dict[str, int] = {}
    roster = build_roster(
        inputs["roster_legislators_current"], inputs["roster_legislators_historical"],
        counts=roster_counts,
    )
    nickname_table = load_nickname_table(inputs["nickname_table"])

    lanes: dict[str, dict[str, dict[str, list[dict[str, Any]]]]] = {
        lane: defaultdict(lambda: defaultdict(list)) for lane in ALL_LANES
    }

    for row in read_rows(inputs["house_sod_2009q3_2015q4"]):
        person = str(row["lda_source_person_id"])
        office = row.get("employing_office_raw") or ""
        parsed = split_payroll_name(row.get("payroll_payee_raw") or "")
        candidate_count = display_count = None
        if parsed:
            given, surname, middle = parsed
            pool = [
                (pid, display)
                for pid, queue_middle, display in queue_index.get((given, surname), [])
                if middles_compatible(queue_middle, middle)
            ]
            if pool:
                candidate_count = len(pool)
                display_count = len({display for _, display in pool})
        blob = queue[person]["blob"] if person in queue else ""
        ok, method, detail = (
            house_office_check(office, blob) if person in queue else (False, "NO_QUEUE_ROW", "")
        )
        quarter = parse_quarter(row.get("period"))
        lanes[LANE_H1][person][house_office_group(office)].append(
            {
                "candidate_id": str(row.get("candidate_match_id") or ""),
                "end_year": first_year(row.get("service_end_date_candidate_iso")),
                "intervals": [],
                "name_candidate_count": candidate_count,
                "name_display_count": display_count,
                "name_method": (
                    "RECONSTRUCTED_FROM_QUEUE_NAME_INDEX"
                    if candidate_count is not None
                    else "NO_QUEUE_CANDIDATE_FOR_PAYROLL_NAME"
                ),
                "name_ok": bool(candidate_count == 1 and display_count == 1),
                "office_detail": detail,
                "office_method": method,
                "office_ok": ok,
                "office_raw": office,
                "quarters": [quarter] if quarter else [],
                "title": (row.get("title_description_raw") or "").strip(),
            }
        )

    for row in read_rows(inputs["house_payroll_2016_2026"]):
        person = str(row["lda_source_person_id"])
        office = row.get("employing_office_candidate") or ""
        blob = queue[person]["blob"] if person in queue else ""
        ok, method, detail = (
            house_office_check(office, blob) if person in queue else (False, "NO_QUEUE_ROW", "")
        )
        candidate_count = row.get("queue_candidate_count_for_name")
        display_count = row.get("queue_display_name_count_for_name")
        quarters = [
            key
            for key in (
                parse_quarter(value) for value in row.get("supported_quarters") or []
            )
            if key
        ]
        lanes[LANE_H2][person][house_office_group(office)].append(
            {
                "candidate_id": str(row.get("match_candidate_id") or ""),
                "end_year": first_year(row.get("service_end_date_candidate")),
                "intervals": [],
                "name_candidate_count": candidate_count,
                "name_display_count": display_count,
                "name_method": "LEDGER_FIELDS",
                "name_ok": bool(candidate_count == 1 and display_count == 1),
                "office_detail": detail,
                "office_method": method,
                "office_ok": ok,
                "office_raw": office,
                "quarters": quarters,
                "title": (row.get("title_candidate") or "").strip(),
            }
        )

    for row in read_rows(inputs["senate_payroll_2011_2026"]):
        person = str(row["lda_source_person_id"])
        office = row.get("employing_office_candidate") or ""
        token = senate_office_token(office)
        upper = queue[person]["upper"] if person in queue else ""
        if person not in queue:
            ok, method = False, "NO_QUEUE_ROW"
        elif token is None:
            ok, method = False, "SENATE_OFFICE_TOKEN_NOT_EXTRACTABLE"
        elif upper_word_present(token, upper):
            ok, method = True, "SENATE_OFFICE_TOKEN_MATCH"
        else:
            ok, method = False, "SENATE_OFFICE_TOKEN_NOT_FOUND"
        lanes[LANE_SENATE][person][office].append(
            {
                "candidate_id": str(row.get("match_candidate_id") or ""),
                "end_year": None,
                "intervals": [
                    (parse_day(item.get("start")), parse_day(item.get("end")))
                    for item in row.get("observed_report_intervals") or []
                ],
                "name_candidate_count": row.get("queue_candidate_count_for_name"),
                "name_display_count": row.get("queue_display_name_count_for_name"),
                "name_method": "LEDGER_FIELDS",
                "name_ok": row.get("queue_candidate_count_for_name") == 1,
                "office_detail": token or "",
                "office_method": method,
                "office_ok": ok,
                "office_raw": office,
                "quarters": [],
                "title": (row.get("title_candidate") or "").strip(),
            }
        )

    def lane_prongs(lane: str, offices_by_person, chamber: str, offset: int):
        result = {}
        for person, offices in offices_by_person.items():
            rows = [row for office_rows in offices.values() for row in office_rows]
            filing_years = queue.get(person, {}).get("filing_years") or []
            threshold = (min(filing_years) + offset) if filing_years else None
            split_clean = None
            if chamber == "senate":
                split_clean = True
                end_years = []
                for office_rows in offices.values():
                    pairs = sorted(
                        {pair for row in office_rows for pair in row["intervals"]},
                        key=lambda pair: (pair[0] is None, pair[0]),
                    )
                    complete = all(
                        pair[0] is not None and pair[1] is not None for pair in pairs
                    )
                    end_years.extend(
                        pair[1].year
                        for pair in pairs
                        if pair[0] is not None and pair[1] is not None
                    )
                    if not (complete and strictly_adjacent(pairs)):
                        split_clean = False
                max_end_year = max(end_years) if end_years else None
                name_unique = all(row["name_candidate_count"] == 1 for row in rows)
            else:
                end_years = [
                    row["end_year"] for row in rows if row["end_year"] is not None
                ]
                max_end_year = max(end_years) if end_years else None
                name_unique = any(row["name_ok"] for row in rows)
            if threshold is None or max_end_year is None:
                chronology = "UNKNOWN"
            elif max_end_year <= threshold:
                chronology = "CONSISTENT"
            else:
                chronology = "INCONSISTENT"
            result[person] = {
                "chronology": chronology,
                "first_filing_year": min(filing_years) if filing_years else None,
                "max_end_year": max_end_year,
                "name_unique": name_unique,
                "office_corroborated": any(row["office_ok"] for row in rows),
                "split_clean": split_clean,
                "threshold": threshold,
            }
        return result

    prongs = {
        LANE_H1: lane_prongs(LANE_H1, lanes[LANE_H1], "house", CHRONOLOGY_OFFSET_YEARS),
        LANE_H2: lane_prongs(LANE_H2, lanes[LANE_H2], "house", CHRONOLOGY_OFFSET_YEARS),
        LANE_SENATE: lane_prongs(
            LANE_SENATE, lanes[LANE_SENATE], "senate", CHRONOLOGY_OFFSET_YEARS
        ),
    }
    union_offices: defaultdict[str, defaultdict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    for lane in HOUSE_LANES:
        for person, offices in lanes[lane].items():
            for key, rows in offices.items():
                union_offices[person][key].extend(rows)
    union_prongs = lane_prongs(
        "house_union", union_offices, "house", CHRONOLOGY_OFFSET_YEARS
    )

    # third-source evidence
    profile_employers: defaultdict[str, set[str]] = defaultdict(set)
    profile_dated: defaultdict[str, set[tuple[str, bool]]] = defaultdict(set)
    for row in read_rows(inputs["working_history_corpus"]):
        person = str(row.get("lda_source_person_id"))
        for episode in row.get("employment_episodes") or []:
            employer = episode.get("employer")
            if employer:
                profile_employers[person].add(str(employer))
                start, end = episode.get("raw_start_date"), episode.get("raw_end_date")
                if start or end:
                    profile_dated[person].add((str(employer), bool(start and end)))
    for row in read_rows(inputs["rapid_structured_profile_evidence"]):
        person = str(row.get("lda_source_person_id"))
        for episode in row.get("employment") or []:
            employer = episode.get("employer")
            if employer:
                profile_employers[person].add(str(employer))
                start, end = episode.get("raw_start_date"), episode.get("raw_end_date")
                if start or end:
                    profile_dated[person].add((str(employer), bool(start and end)))
    for row in read_rows(inputs["linkedin_authenticated_evidence"]):
        person = str(row.get("lda_source_person_id"))
        for fact in row.get("candidate_facts") or []:
            if fact.get("fact_type") != "EMPLOYMENT":
                continue
            employer = fact.get("employer_raw")
            if employer:
                profile_employers[person].add(str(employer))
                start, end = fact.get("raw_start_date"), fact.get("raw_end_date")
                if start or end:
                    profile_dated[person].add((str(employer), bool(start and end)))
    politico: defaultdict[str, set[str]] = defaultdict(set)
    for row in read_rows(inputs["politico_lda_employment_candidates"]):
        text = row.get("role_text_raw")
        if text:
            politico[str(row["lda_source_person_id"])].add(str(text))
    legilist: set[str] = set()
    for row in read_rows(inputs["v3_candidate_adjudication_decisions"]):
        if (
            row.get("lane") == "legilist_source_binding"
            and row.get("decision") == "ACCEPTED_SOURCE_BINDING"
        ):
            legilist.add(str(row["lda_source_person_id"]))

    records: list[dict[str, Any]] = []
    record_letter: dict[str, dict[str, str]] = {lane: {} for lane in ALL_LANES}
    span_counts: Counter = Counter()
    for lane in ALL_LANES:
        chamber = "senate" if lane == LANE_SENATE else "house"
        for person in sorted(lanes[lane]):
            person_prongs = prongs[lane][person]
            for office_group in sorted(lanes[lane][person]):
                office_rows = sorted(
                    lanes[lane][person][office_group],
                    key=lambda row: row["candidate_id"],
                )
                office_raws = sorted({row["office_raw"] for row in office_rows})

                # Observation window for this office group (INV-6 term-window
                # hard constraint), computed once here and reused below by
                # the run-splitting logic.
                if chamber == "house":
                    observed_quarter_keys = sorted(
                        {key for row in office_rows for key in row["quarters"]}
                    )
                    if observed_quarter_keys:
                        window_start = quarter_span(observed_quarter_keys[0])[0]
                        window_end = quarter_span(observed_quarter_keys[-1])[1]
                    else:
                        window_start = window_end = None
                    observed_interval_pairs = None
                else:
                    observed_interval_pairs = sorted(
                        {
                            pair
                            for row in office_rows
                            for pair in row["intervals"]
                            if pair[0] is not None and pair[1] is not None
                        }
                    )
                    if observed_interval_pairs:
                        window_start = min(start for start, _ in observed_interval_pairs)
                        window_end = max(end for _, end in observed_interval_pairs)
                    else:
                        window_start = window_end = None
                    observed_quarter_keys = None

                if chamber == "house":
                    office_key = office_group
                    container = house_container(office_raws[0])
                    normalized = house_normalize_office(office_raws[0])
                    if house_is_member_office(normalized):
                        bioguide, method = resolve_bioguide(
                            *house_first_and_surname(normalized),
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
                    container = senate_container(office_group)
                    if container == "member_office":
                        bioguide, method = resolve_bioguide(
                            *senate_first_and_surname(office_group),
                            roster,
                            nickname_table,
                            chamber=chamber,
                            window_start=window_start,
                            window_end=window_end,
                        )
                    else:
                        bioguide, method = None, "NOT_A_MEMBER_OFFICE"

                matching = [row for row in office_rows if row["office_ok"]]
                office_ok = bool(matching)
                if matching:
                    office_method = matching[0]["office_method"]
                    matched_token = matching[0]["office_detail"] or None
                else:
                    office_method = sorted(
                        {row["office_method"] for row in office_rows}
                    )[0]
                    matched_token = None

                if chamber == "house":
                    office_end_years = [
                        row["end_year"]
                        for row in office_rows
                        if row["end_year"] is not None
                    ]
                else:
                    office_end_years = [
                        end.year
                        for row in office_rows
                        for _, end in row["intervals"]
                        if end is not None
                    ]
                office_max_end_year = max(office_end_years) if office_end_years else None
                office_consistent = bool(
                    person_prongs["threshold"] is not None
                    and office_max_end_year is not None
                    and office_max_end_year <= person_prongs["threshold"]
                )

                runs: list[tuple[int, date, date, date, date]] = []
                if chamber == "house":
                    keys = observed_quarter_keys
                    if not keys:
                        continue
                    period_count = len(keys)
                    grouped: list[list[tuple[int, int]]] = []
                    for key in keys:
                        if grouped and quarter_index(key) == quarter_index(
                            grouped[-1][-1]
                        ) + 1:
                            grouped[-1].append(key)
                        else:
                            grouped.append([key])
                    for group in grouped:
                        runs.append(
                            (
                                len(group),
                                quarter_span(group[0])[0],
                                quarter_span(group[-1])[1],
                                quarter_span(
                                    index_quarter(
                                        quarter_index(group[0])
                                        - ENVELOPE_WIDENING_REPORTING_PERIODS
                                    )
                                )[0],
                                quarter_span(
                                    index_quarter(
                                        quarter_index(group[-1])
                                        + ENVELOPE_WIDENING_REPORTING_PERIODS
                                    )
                                )[1],
                            )
                        )
                else:
                    pairs = observed_interval_pairs
                    if not pairs:
                        continue
                    period_count = len(pairs)
                    grouped_pairs: list[list[tuple[date, date]]] = []
                    for pair in pairs:
                        if grouped_pairs and pair[0] <= grouped_pairs[-1][-1][
                            1
                        ] + timedelta(days=1):
                            grouped_pairs[-1].append(pair)
                        else:
                            grouped_pairs.append([pair])
                    for group in grouped_pairs:
                        core_start = group[0][0]
                        core_end = max(end for _, end in group)
                        runs.append(
                            (
                                len(group),
                                core_start,
                                core_end,
                                semiannual_window(
                                    semiannual_window(core_start)[0] - timedelta(days=1)
                                )[0],
                                semiannual_window(
                                    semiannual_window(core_end)[1] + timedelta(days=1)
                                )[1],
                            )
                        )
                run_count = len(runs)

                tokens = sorted(
                    {
                        token
                        for office_raw in office_raws
                        for token in (
                            house_profile_tokens(office_raw)
                            if chamber == "house"
                            else ([senate_office_token(office_raw)] or [])
                        )
                        if token
                    }
                )
                profile_hit = None
                for employer in sorted(profile_employers.get(person, set())):
                    if any(upper_word_present(t, employer.upper()) for t in tokens):
                        profile_hit = employer
                        break
                politico_hit = None
                for text in sorted(politico.get(person, set())):
                    match = next(
                        (t for t in tokens if upper_word_present(t, text.upper())), None
                    )
                    if match:
                        politico_hit = match
                        break
                multi = []
                if profile_hit is not None:
                    multi.append("profile")
                if politico_hit is not None:
                    multi.append("politico")
                multi.sort()

                tier = letter_for(
                    person_prongs["name_unique"],
                    office_ok,
                    person_prongs["chronology"],
                    bool(multi),
                )
                previous = record_letter[lane].get(person, "L1")
                record_letter[lane][person] = (
                    tier if tier_rank(tier) >= tier_rank(previous) else previous
                )

                titles = sorted({row["title"] for row in office_rows if row["title"]})
                candidate_ids = sorted(
                    {row["candidate_id"] for row in office_rows if row["candidate_id"]}
                )
                for run_index, (
                    period_total,
                    core_start,
                    core_end,
                    envelope_start,
                    envelope_end,
                ) in enumerate(runs, start=1):
                    records.append(
                        {
                            "canonical_eligible": False,
                            "canonical_employment_promoted": False,
                            "chamber": chamber,
                            "container_kind": container,
                            "contiguous": run_count == 1,
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
                                if person_prongs["name_unique"]
                                else "NAME_MATCH_ONLY"
                            ),
                            "lda_source_person_id": person,
                            "member_bioguide": bioguide,
                            "member_resolution_method": method,
                            "office_key": office_key,
                            "office_raw_examples": office_raws[:MAX_EXAMPLES_PER_RECORD],
                            "period_kind": "quarter" if chamber == "house" else "half_year",
                            "periods_observed": period_total,
                            "precision": "report_period",
                            "prong": {
                                "chronology": person_prongs["chronology"],
                                "multi_source": multi,
                                "name_unique": person_prongs["name_unique"],
                                "office_corroborated": office_ok,
                                "split_clean": person_prongs["split_clean"],
                            },
                            "prong_evidence": {
                                "chronology": {
                                    "first_filing_year": person_prongs["first_filing_year"],
                                    "max_observed_end_year": person_prongs["max_end_year"],
                                    "office_chronology_consistent": office_consistent,
                                    "office_max_observed_end_year": office_max_end_year,
                                    "threshold_year": person_prongs["threshold"],
                                },
                                "multi_source": {
                                    "legilist_names_office": False,
                                    "legilist_person_binding": person in legilist,
                                    "politico_matched_token": politico_hit,
                                    "profile_matched_employer": profile_hit,
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
                                        house_normalize_office(office_raws[0])
                                        if chamber == "house"
                                        else office_key
                                    ),
                                },
                                "payroll_support_digest": digest_values(candidate_ids),
                                "split": {
                                    "office_period_count": period_count,
                                    "office_run_count": run_count,
                                    "person_offices_all_contiguous": person_prongs[
                                        "split_clean"
                                    ],
                                },
                            },
                            "review_status": "REVIEW_REQUIRED",
                            "rule_version": rule_version,
                            "run_count": run_count,
                            "run_index": run_index,
                            "schema_id": RECORD_SCHEMA,
                            "source_lane": lane,
                            "tier": tier,
                            "title_examples": titles[:MAX_EXAMPLES_PER_RECORD],
                        }
                    )
    records.sort(
        key=lambda row: (
            row["chamber"],
            row["source_lane"],
            row["lda_source_person_id"],
            row["office_key"],
            row["run_index"],
        )
    )

    lane_letter: dict[str, dict[str, str]] = {}
    for lane in ALL_LANES:
        lane_letter[lane] = {
            person: letter_for(
                value["name_unique"],
                value["office_corroborated"],
                value["chronology"],
                record_letter[lane].get(person) == "L5",
            )
            for person, value in prongs[lane].items()
        }
    union_letter = {
        person: letter_for(
            value["name_unique"],
            value["office_corroborated"],
            value["chronology"],
            any(record_letter[lane].get(person) == "L5" for lane in HOUSE_LANES),
        )
        for person, value in union_prongs.items()
    }

    # ladder span counts
    for lane in HOUSE_LANES:
        total = 0
        for person, offices in lanes[lane].items():
            person_prongs = prongs[lane][person]
            if not person_prongs["name_unique"]:
                continue
            threshold = person_prongs["threshold"]
            for office_rows in offices.values():
                if not any(row["office_ok"] for row in office_rows):
                    continue
                ends = [
                    row["end_year"] for row in office_rows if row["end_year"] is not None
                ]
                if threshold is None or not ends or max(ends) > threshold:
                    continue
                if not any(row["quarters"] for row in office_rows):
                    continue
                total += 1
        span_counts[lane] = total
    senate_spans = 0
    for person, offices in lanes[LANE_SENATE].items():
        value = prongs[LANE_SENATE][person]
        if not value["split_clean"] or tier_rank(lane_letter[LANE_SENATE][person]) < tier_rank("L4"):
            continue
        for office_rows in offices.values():
            if any(
                pair[0] is not None and pair[1] is not None
                for row in office_rows
                for pair in row["intervals"]
            ):
                senate_spans += 1
    span_counts["senate_l4_s"] = senate_spans

    # A6 episodes
    payroll_offices: defaultdict[str, set[str]] = defaultdict(set)
    for lane in ALL_LANES:
        for person, offices in lanes[lane].items():
            for office_rows in offices.values():
                for row in office_rows:
                    if row["office_raw"]:
                        payroll_offices[person].add(row["office_raw"])
    episodes: list[dict[str, Any]] = []
    a6_counts: Counter = Counter()
    for row in read_rows(inputs["a6_near_candidates"]):
        a6_counts["rows"] += 1
        mention = row.get("office_employer_mention") or {}
        dates = row.get("date_range_mention") or {}
        entity_class = mention.get("entity_class")
        start_year, end_year = dates.get("explicit_start_year"), dates.get("explicit_end_year")
        if entity_class not in A6_RESOLVABLE_ENTITY_CLASSES:
            continue
        if start_year is None or end_year is None:
            continue
        a6_counts["resolvable_entity_and_both_years"] += 1
        if set(row.get("rejection_reasons") or []) & A6_EXCLUDED_FLAGS:
            continue
        person = str(row["lda_source_person_id"])
        office_text = str(mention.get("text") or "")
        surname = first = None
        if entity_class == "MEMBER_OFFICE_CANDIDATE":
            for pattern in (_A6_TITLE, _A6_OFFICE):
                found = pattern.search(office_text)
                if found:
                    first, surname = a6_first_and_surname(found.group(1))
                    if surname:
                        break
            bioguide, method = resolve_bioguide(
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
            office
            for office in payroll_offices.get(person, set())
            if surname
            and re.search(r"\b" + re.escape(surname.upper()) + r"\b", office.upper())
        )
        episodes.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "claim_id": str((row.get("source_pointer") or {}).get("claim_id") or ""),
                "corroborated_by_payroll": bool(corroborating),
                "corroborating_payroll_office_examples": corroborating[
                    :MAX_EXAMPLES_PER_RECORD
                ],
                "end_year": int(end_year),
                "excluded_flags": [],
                "lda_source_person_id": person,
                "member_bioguide": bioguide,
                "member_resolution_method": method,
                "member_surname_text": surname,
                "office_entity_class": entity_class,
                "office_text": office_text,
                "precision": "year",
                "review_status": "REVIEW_REQUIRED",
                "role_text": (row.get("role_title_mention") or {}).get("text"),
                "rule_version": rule_version,
                "schema_id": EPISODE_SCHEMA,
                "single_author": True,
                "start_year": int(start_year),
            }
        )
    episodes.sort(key=lambda row: (row["lda_source_person_id"], row["claim_id"]))

    # registrant side
    registrant_episodes: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_rows(inputs["lda_registrant_employment_episodes"]):
        registrant_episodes[str(row["lda_source_person_id"])].append(row)
    names_by_year: defaultdict[str, defaultdict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    names_any: defaultdict[str, set[str]] = defaultdict(set)
    registrant_span: dict[str, tuple[int, int]] = {}
    for person, rows in registrant_episodes.items():
        years: list[int] = []
        for row in rows:
            normalized = normalized_org_name(row.get("employer_name"))
            names_any[person].add(normalized)
            filing_years = list(row.get("filing_years") or [])
            start_year, end_year = row.get("start_year"), row.get("end_year")
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
            for value in (start_year, end_year):
                if value is not None:
                    years.append(value)
        if years:
            registrant_span[person] = (min(years), max(years))
    ld203_years: defaultdict[str, set[int]] = defaultdict(set)
    ld203_by_year: defaultdict[str, defaultdict[int, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    ld203_any: defaultdict[str, set[str]] = defaultdict(set)
    ld203_raw: defaultdict[str, dict[str, str]] = defaultdict(dict)
    for row in read_rows(inputs["a7_ld203_affiliations"]):
        person = str(row["lda_source_person_id"])
        year = row.get("filing_year")
        normalized = normalized_org_name(row.get("lda_registrant_name"))
        ld203_years[person].add(year)
        ld203_by_year[person][year].add(normalized)
        ld203_any[person].add(normalized)
        ld203_raw[person].setdefault(normalized, str(row.get("lda_registrant_name") or ""))
    fec_by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_rows(inputs["a7_fec_employment_observations"]):
        fec_by_person[str(row["lda_source_person_id"])].append(row)
    littlesis_by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_rows(inputs["littlesis_lda_history_candidates"]):
        if row.get("fact_type") == "EMPLOYMENT":
            littlesis_by_person[str(row["lda_source_person_id"])].append(row)

    payroll_span: dict[str, tuple[int, int]] = {}

    def extend(person: str, low, high) -> None:
        values = [value for value in (low, high) if value is not None]
        if not values:
            return
        current = payroll_span.get(person)
        payroll_span[person] = (
            min(values) if current is None else min(current[0], min(values)),
            max(values) if current is None else max(current[1], max(values)),
        )

    for row in read_rows(inputs["house_sod_2009q3_2015q4"]):
        extend(
            str(row["lda_source_person_id"]),
            first_year(row.get("service_start_date_candidate_iso"))
            or first_year(row.get("period_start")),
            first_year(row.get("service_end_date_candidate_iso"))
            or first_year(row.get("period_end")),
        )
    for row in read_rows(inputs["house_payroll_2016_2026"]):
        extend(
            str(row["lda_source_person_id"]),
            first_year(row.get("service_start_date_candidate")),
            first_year(row.get("service_end_date_candidate")),
        )
    for row in read_rows(inputs["senate_payroll_2011_2026"]):
        years = [
            value
            for item in row.get("observed_report_intervals") or []
            for value in (first_year(item.get("start")), first_year(item.get("end")))
            if value is not None
        ]
        if years:
            extend(str(row["lda_source_person_id"]), min(years), max(years))

    registrant_rows: list[dict[str, Any]] = []
    order_counts: Counter = Counter()
    registrant_stats: Counter = Counter()
    for person in sorted(queue_order):
        person_episodes = registrant_episodes.get(person, [])
        registrants = sorted(
            (
                {
                    "employer_name": row.get("employer_name"),
                    "employer_name_normalized": normalized_org_name(row.get("employer_name")),
                    "end_year": row.get("end_year"),
                    "filing_years": sorted(set(row.get("filing_years") or [])),
                    "registrant_source_org_id": str(row.get("registrant_source_org_id") or ""),
                    "start_year": row.get("start_year"),
                }
                for row in person_episodes
            ),
            key=lambda item: (
                item["registrant_source_org_id"],
                item["employer_name_normalized"],
            ),
        )
        span = registrant_span.get(person)
        years = {year for year in ld203_years.get(person, set()) if year is not None}
        same_year = False
        matched_name = None
        for year in sorted(years):
            overlap = ld203_by_year[person][year] & names_by_year[person].get(year, set())
            if overlap:
                same_year = True
                matched_name = ld203_raw[person].get(sorted(overlap)[0])
                break
        earlier = later = 0
        if span and years:
            if min(years) < span[0]:
                earlier = span[0] - min(years)
            if max(years) > span[1]:
                later = max(years) - span[1]
        fec_same = fec_any = False
        for row in fec_by_person.get(person, []):
            employer = normalized_org_name(row.get("raw_employer"))
            stamp = str(row.get("observation_date") or "")
            try:
                stamp_year = int(stamp[:4])
            except ValueError:
                stamp_year = None
            if employer in names_any.get(person, set()):
                fec_any = True
            if stamp_year is not None and employer in names_by_year[person].get(
                stamp_year, set()
            ):
                fec_same = True
        ls_dated = ls_bounded = False
        dated_employer = None
        for row in littlesis_by_person.get(person, []):
            if normalized_org_name(row.get("container_display_name")) not in names_any.get(
                person, set()
            ):
                continue
            start, end = row.get("raw_start_date"), row.get("raw_end_date")
            if start or end:
                ls_dated = True
                if dated_employer is None:
                    dated_employer = str(row.get("container_display_name") or "")
            if start and end:
                ls_bounded = True
        pr_dated = pr_bounded = False
        for employer, bounded in sorted(profile_dated.get(person, set())):
            if normalized_org_name(employer) not in names_any.get(person, set()):
                continue
            pr_dated = True
            if dated_employer is None:
                dated_employer = employer
            if bounded:
                pr_bounded = True
        if not person_episodes:
            tier = None
        elif ls_dated or ls_bounded or pr_dated or pr_bounded:
            tier = "R2"
        elif same_year or fec_same:
            tier = "R1"
        else:
            tier = "R0"
        hill = payroll_span.get(person)
        if hill is None or span is None:
            order = "NO_HILL_OBSERVATION"
        elif hill[1] < span[0]:
            order = "ORDERED"
        elif span[1] < hill[0]:
            order = "REVERSED"
        else:
            order = "OVERLAP_YEAR_GRAIN"
        order_counts[order] += 1
        if years:
            registrant_stats["ld203_people"] += 1
        registrant_stats["ld203_same_year_name_equal"] += int(same_year)
        registrant_stats["ld203_extends_earlier_people"] += int(earlier > 0)
        registrant_stats["ld203_extends_later_people"] += int(later > 0)
        registrant_stats["fec_same_year_name_equal"] += int(fec_same)
        registrant_rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "dated_registrant_evidence": {
                    "littlesis_bounded": ls_bounded,
                    "littlesis_dated": ls_dated,
                    "matched_employer_name": dated_employer,
                    "profile_bounded": pr_bounded,
                    "profile_dated": pr_dated,
                },
                "fec": {
                    "any_year_name_equal": fec_any,
                    "observation_count": len(fec_by_person.get(person, [])),
                    "same_year_name_equal": fec_same,
                },
                "hill_payroll_year_span": (
                    {"end_year": hill[1], "start_year": hill[0]} if hill else None
                ),
                "hill_registrant_order": order,
                "ld203": {
                    "extends_earlier_years": earlier,
                    "extends_later_years": later,
                    "filing_year_count": len(years),
                    "first_filing_year": min(years) if years else None,
                    "introduces_unseen_organization": bool(
                        ld203_any.get(person, set()) - names_any.get(person, set())
                    ),
                    "last_filing_year": max(years) if years else None,
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
    registrant_tier = {
        row["lda_source_person_id"]: row["registrant_side_tier"] for row in registrant_rows
    }

    # summary
    a9_bucket: dict[str, Any] = {}
    a9_ordinal: dict[str, Any] = {}
    for row in read_rows(inputs["a9_priority_sidecar"]):
        person = str(row["lda_source_person_id"])
        a9_bucket[person] = str((row.get("revised_priority") or {}).get("priority_bucket") or "")
        a9_ordinal[person] = row.get("sealed_queue_ordinal")
    episode_counts = Counter(row["lda_source_person_id"] for row in episodes)
    record_counts: Counter = Counter(row["lda_source_person_id"] for row in records)

    summary: list[dict[str, Any]] = []
    failure_distribution: Counter = Counter()
    for person in sorted(queue_order):
        by_lane = {}
        codes: set[str] = set()
        for lane in ALL_LANES:
            if person not in prongs[lane]:
                by_lane[lane] = "L0"
                continue
            by_lane[lane] = lane_letter[lane][person]
            value = prongs[lane][person]
            rows = [
                row
                for office_rows in lanes[lane][person].values()
                for row in office_rows
            ]
            if not value["name_unique"]:
                codes.add("NAME_COLLISION_IN_QUEUE")
            if not value["office_corroborated"]:
                methods = {row["office_method"] for row in rows}
                if person in queue and not queue[person]["substantive"]:
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
            if value["chronology"] == "INCONSISTENT":
                codes.add("CHRONOLOGY_INCONSISTENT")
            elif value["chronology"] == "UNKNOWN":
                codes.add("CHRONOLOGY_UNKNOWN")
            if lane == LANE_SENATE and value["split_clean"] is False:
                codes.add("SPLIT_NOT_CLEAN")
        house_tier = union_letter.get(person, "L0")
        senate_tier = by_lane[LANE_SENATE]
        max_tier = house_tier if tier_rank(house_tier) >= tier_rank(senate_tier) else senate_tier
        if max_tier == "L0":
            codes = {"NO_PAYROLL_OBSERVATION"}
        elif max_tier == "L4":
            codes.add("NO_THIRD_SOURCE_NAMES_THE_OFFICE")
        for code in codes:
            failure_distribution[code] += 1
        summary.append(
            {
                "a9_bucket": a9_bucket.get(person),
                "a9_sealed_queue_ordinal": a9_ordinal.get(person),
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "filer_asserted_year_episode_count": episode_counts.get(person, 0),
                "lda_source_person_id": person,
                "max_tier": max_tier,
                "person_office_record_count": record_counts.get(person, 0),
                "prong_failure_codes": sorted(codes),
                "registrant_side_tier": registrant_tier.get(person),
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": SUMMARY_SCHEMA,
                "senate_split_clean": (
                    prongs[LANE_SENATE][person]["split_clean"]
                    if person in prongs[LANE_SENATE]
                    else None
                ),
                "tier_by_chamber": {"house": house_tier, "senate": senate_tier},
                "tier_by_lane": by_lane,
            }
        )

    def at_least(letters: Mapping[str, str], tier: str) -> int:
        floor = tier_rank(tier)
        return sum(1 for value in letters.values() if tier_rank(value) >= floor)

    payroll_union = set()
    for lane in ALL_LANES:
        payroll_union |= set(lanes[lane])
    senate_split_people = sum(
        1 for value in prongs[LANE_SENATE].values() if value["split_clean"]
    )
    senate_l4_s = sum(
        1
        for person, value in prongs[LANE_SENATE].items()
        if value["split_clean"] and tier_rank(lane_letter[LANE_SENATE][person]) >= tier_rank("L4")
    )
    measured = {
        (LANE_H1, "people"): len(lanes[LANE_H1]),
        (LANE_H1, "L2_name_anchored"): at_least(lane_letter[LANE_H1], "L2"),
        (LANE_H1, "L3_office_corroborated"): at_least(lane_letter[LANE_H1], "L3"),
        (LANE_H1, "L4_chronology_consistent"): at_least(lane_letter[LANE_H1], "L4"),
        (LANE_H1, "L4_person_office_spans"): span_counts[LANE_H1],
        (LANE_H2, "people"): len(lanes[LANE_H2]),
        (LANE_H2, "L2_name_anchored"): at_least(lane_letter[LANE_H2], "L2"),
        (LANE_H2, "L3_office_corroborated"): at_least(lane_letter[LANE_H2], "L3"),
        (LANE_H2, "L4_chronology_consistent"): at_least(lane_letter[LANE_H2], "L4"),
        (LANE_H2, "L4_person_office_spans"): span_counts[LANE_H2],
        (LANE_SENATE, "people"): len(lanes[LANE_SENATE]),
        (LANE_SENATE, "L2_name_anchored"): at_least(lane_letter[LANE_SENATE], "L2"),
        (LANE_SENATE, "L3_office_corroborated"): at_least(lane_letter[LANE_SENATE], "L3"),
        (LANE_SENATE, "L4_chronology_consistent"): at_least(lane_letter[LANE_SENATE], "L4"),
        (LANE_SENATE, "S_split_clean"): senate_split_people,
        (LANE_SENATE, "L4_and_S"): senate_l4_s,
        (LANE_SENATE, "L4_and_S_person_office_spans"): span_counts["senate_l4_s"],
        ("house_union", "people"): len(union_prongs),
        ("house_union", "L2_name_anchored"): at_least(union_letter, "L2"),
        ("house_union", "L3_office_corroborated"): at_least(union_letter, "L3"),
        ("house_union", "L4_chronology_consistent"): at_least(union_letter, "L4"),
        ("payroll_union", "people"): len(payroll_union),
        ("a6_near_candidates", "rows"): a6_counts["rows"],
        ("a6_near_candidates", "resolvable_entity_and_both_years"): a6_counts[
            "resolvable_entity_and_both_years"
        ],
        ("registrant", "people_with_lda_registrant_association"): len(registrant_episodes),
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
    return {
        "episodes": episodes,
        "failure_distribution": dict(sorted(failure_distribution.items())),
        "measured": measured,
        "payroll_union": payroll_union,
        "queue_order": queue_order,
        "records": records,
        "registrant_rows": registrant_rows,
        "roster_terms_unparseable": roster_counts.get("roster_terms_unparseable", 0),
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Tripwires
# ---------------------------------------------------------------------------
def assert_unpromoted(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """A5b-style anti-promotion tripwire, run over every row."""

    failures: list[str] = []
    for index, row in enumerate(rows):
        if row.get("review_status") != "REVIEW_REQUIRED":
            failures.append(f"row {index}: review_status is not REVIEW_REQUIRED")
        if row.get("canonical_eligible") is not False:
            failures.append(f"row {index}: canonical_eligible is not false")
        if row.get("canonical_employment_promoted") is not False:
            failures.append(f"row {index}: canonical_employment_promoted is not false")
        for key, value in row.items():
            lowered = key.lower()
            if (
                ("promoted" in lowered or "canonical" in lowered or "eligible" in lowered)
                and value not in (False, 0, None, "")
            ):
                failures.append(f"row {index}: promotion-shaped field {key} is truthy")
        if len(failures) > 50:
            failures.append("... truncated")
            break
    return failures


def language_law_scan(payload: Any) -> tuple[list[str], Counter]:
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
# Verify
# ---------------------------------------------------------------------------
def verify(args: argparse.Namespace) -> dict[str, Any]:
    primary = args.primary.resolve()
    twin = args.twin.resolve()
    assertions: dict[str, bool] = {}
    failures: list[str] = []
    detail: dict[str, Any] = {}

    for directory in (primary, twin):
        for name in (*PAYLOAD_FILES, RECEIPT_FILE):
            if not (directory / name).is_file():
                raise VerificationFailure(f"missing output: {directory / name}")

    receipt = load_json(primary / RECEIPT_FILE)
    twin_receipt = load_json(twin / RECEIPT_FILE)

    assertions["receipt_schema_id_exact"] = receipt.get("schema_id") == RECEIPT_SCHEMA
    assertions["receipt_stage_id_exact"] = receipt.get("stage_id") == STAGE_ID
    assertions["receipt_status_pass"] = receipt.get("status") == "PASS"
    assertions["receipt_zero_promotions"] = (
        receipt.get("canonical_employment_promotions") == 0
        and receipt.get("canonical_identity_promotions") == 0
        and receipt.get("promotion_policy")
        == "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
        and receipt.get("review_status") == "REVIEW_REQUIRED"
    )
    assertions["receipt_declares_no_failures"] = receipt.get("failures") == []

    # twin byte identity
    twin_equal = True
    for name in (*PAYLOAD_FILES, RECEIPT_FILE):
        if (primary / name).read_bytes() != (twin / name).read_bytes():
            twin_equal = False
            failures.append(f"TWIN_BYTES_DIFFER:{name}")
    assertions["primary_twin_byte_identical"] = twin_equal
    assertions["twin_receipt_equals_primary_receipt"] = receipt == twin_receipt
    assertions["gzip_mtime_zero"] = all(
        (primary / name).read_bytes()[4:8] == b"\x00\x00\x00\x00"
        for name in PAYLOAD_FILES
    )

    # file hashes
    file_hash_ok = True
    hashes: dict[str, str] = {}
    for name in PAYLOAD_FILES:
        digest = sha(primary / name)
        hashes[name] = digest
        entry = receipt.get("files", {}).get(name, {})
        if entry.get("sha256") != digest or entry.get("bytes") != (
            primary / name
        ).stat().st_size:
            file_hash_ok = False
            failures.append(f"RECEIPT_FILE_BINDING_MISMATCH:{name}")
    assertions["receipt_binds_every_output_file"] = file_hash_ok

    # input hashes
    inputs: dict[str, Path] = {}
    input_ok = True
    for label, entry in sorted(receipt.get("inputs", {}).items()):
        path = Path(str(entry["path"]))
        inputs[label] = path
        if not path.is_file():
            input_ok = False
            failures.append(f"INPUT_MISSING:{label}")
            continue
        if path.stat().st_size != entry.get("bytes") or sha(path) != entry.get("sha256"):
            input_ok = False
            failures.append(f"INPUT_SEAL_MISMATCH:{label}")
    assertions["every_receipt_input_hash_bound"] = input_ok
    forbidden = {
        "employment_history",
        "employment_promotion",
        "lda_composite_repair",
        "lda_source_native_corpus",
    }
    assertions["no_forbidden_module_consumed"] = not any(
        any(token in label for token in forbidden) for label in receipt.get("inputs", {})
    )
    if not input_ok:
        raise VerificationFailure("inputs are not hash-bound; cannot re-derive")

    assertions["receipt_rule_version_is_the_pinned_v2_rule"] = (
        receipt.get("rule_version") == EXPECTED_RULE_VERSION
    )
    rederived = rederive(inputs, str(receipt.get("rule_version")))
    detail["roster_terms_unparseable"] = rederived["roster_terms_unparseable"]

    emitted_records = list(read_rows(primary / RECORD_FILE))
    emitted_summary = list(read_rows(primary / SUMMARY_FILE))
    emitted_episodes = list(read_rows(primary / EPISODE_FILE))
    emitted_registrant = list(read_rows(primary / REGISTRANT_FILE))

    def compare(name: str, emitted: Sequence[Mapping], expected: Sequence[Mapping]) -> int:
        if len(emitted) != len(expected):
            failures.append(
                f"{name}: row count {len(emitted)} != re-derived {len(expected)}"
            )
        mismatches = 0
        examples: list[str] = []
        for index in range(min(len(emitted), len(expected))):
            if emitted[index] != expected[index]:
                mismatches += 1
                if len(examples) < 3:
                    differing = sorted(
                        key
                        for key in set(emitted[index]) | set(expected[index])
                        if emitted[index].get(key) != expected[index].get(key)
                    )
                    examples.append(
                        f"row {index} ({emitted[index].get('lda_source_person_id')}): {differing}"
                    )
        detail[f"{name}_mismatch_examples"] = examples
        return mismatches

    record_mismatches = compare("records", emitted_records, rederived["records"])
    summary_mismatches = compare("summary", emitted_summary, rederived["summary"])
    episode_mismatches = compare("episodes", emitted_episodes, rederived["episodes"])
    registrant_mismatches = compare(
        "registrant", emitted_registrant, rederived["registrant_rows"]
    )
    assertions["all_person_office_records_independently_rederived"] = (
        record_mismatches == 0 and len(emitted_records) == len(rederived["records"])
    )
    assertions["all_summary_rows_independently_rederived"] = (
        summary_mismatches == 0 and len(emitted_summary) == len(rederived["summary"])
    )
    assertions["all_filer_episodes_independently_rederived"] = (
        episode_mismatches == 0 and len(emitted_episodes) == len(rederived["episodes"])
    )
    assertions["all_registrant_rows_independently_rederived"] = (
        registrant_mismatches == 0
        and len(emitted_registrant) == len(rederived["registrant_rows"])
    )

    # anti-promotion tripwire over every row and the receipt
    tripwire: list[str] = []
    for rows in (
        emitted_records,
        emitted_summary,
        emitted_episodes,
        emitted_registrant,
    ):
        tripwire.extend(assert_unpromoted(rows))
    if receipt.get("canonical_employment_promotions") != 0:
        tripwire.append("receipt: canonical_employment_promotions is not 0")
    if receipt.get("canonical_identity_promotions") != 0:
        tripwire.append("receipt: canonical_identity_promotions is not 0")
    if receipt.get("promotion_policy") != "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS":
        tripwire.append("receipt: promotion_policy is not the zero-promotion policy")
    assertions["anti_promotion_tripwire_clean"] = not tripwire
    detail["anti_promotion_tripwire"] = tripwire[:20]

    # language law
    authored_hits: list[str] = []
    verbatim_counts: Counter = Counter()
    for payload in (
        emitted_records,
        emitted_summary,
        emitted_episodes,
        emitted_registrant,
    ):
        hits, occurrences = language_law_scan(payload)
        authored_hits.extend(hits)
        verbatim_counts.update(occurrences)
    receipt_hits, _ = language_law_scan(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"inputs", "files", "language_law"}
        }
    )
    authored_hits.extend(receipt_hits)
    assertions["language_law_no_authored_token"] = not authored_hits
    assertions["receipt_language_law_block_agrees"] = (
        list(receipt.get("language_law", {}).get("banned_tokens") or [])
        == list(LANGUAGE_LAW_TOKENS)
        and receipt.get("language_law", {}).get("verbatim_token_occurrences")
        == dict(sorted(verbatim_counts.items()))
    )
    detail["language_law_authored_hits"] = authored_hits[:20]
    detail["language_law_verbatim_token_occurrences"] = dict(
        sorted(verbatim_counts.items())
    )

    # conservation (INV-4)
    summary_ids = [row["lda_source_person_id"] for row in emitted_summary]
    registrant_ids = [row["lda_source_person_id"] for row in emitted_registrant]
    queue_ids = rederived["queue_order"]
    payroll_union = rederived["payroll_union"]
    above_l0 = {
        row["lda_source_person_id"] for row in emitted_summary if row["max_tier"] != "L0"
    }
    assertions["summary_is_the_sealed_queue_exactly_once"] = (
        len(summary_ids) == SEALED_QUEUE_ROWS
        and len(set(summary_ids)) == SEALED_QUEUE_ROWS
        and set(summary_ids) == set(queue_ids)
    )
    assertions["registrant_rows_are_the_sealed_queue_exactly_once"] = (
        len(registrant_ids) == SEALED_QUEUE_ROWS
        and len(set(registrant_ids)) == SEALED_QUEUE_ROWS
        and set(registrant_ids) == set(queue_ids)
    )
    assertions["every_payroll_person_is_above_L0"] = above_l0 == payroll_union
    assertions["payroll_union_inside_sealed_queue"] = not (payroll_union - set(queue_ids))
    assertions["record_people_are_a_subset_of_payroll_union"] = {
        row["lda_source_person_id"] for row in emitted_records
    } <= payroll_union
    record_counts = Counter(row["lda_source_person_id"] for row in emitted_records)
    assertions["summary_record_counts_match_record_file"] = all(
        row["person_office_record_count"] == record_counts.get(row["lda_source_person_id"], 0)
        for row in emitted_summary
    )
    episode_counts = Counter(row["lda_source_person_id"] for row in emitted_episodes)
    assertions["summary_episode_counts_match_episode_file"] = all(
        row["filer_asserted_year_episode_count"]
        == episode_counts.get(row["lda_source_person_id"], 0)
        for row in emitted_summary
    )
    assertions["receipt_prong_failure_distribution_exact"] = (
        receipt.get("prong_failure_distribution") == rederived["failure_distribution"]
    )

    # per-record uniqueness and ordering
    keys = [
        (
            row["chamber"],
            row["source_lane"],
            row["lda_source_person_id"],
            row["office_key"],
            row["run_index"],
        )
        for row in emitted_records
    ]
    assertions["record_keys_unique"] = len(keys) == len(set(keys))
    assertions["record_file_sorted"] = keys == sorted(keys)
    assertions["record_core_inside_envelope"] = all(
        row["envelope"]["start_earliest"] < row["core"]["start_latest"]
        and row["core"]["start_latest"] <= row["core"]["end_earliest"]
        and row["core"]["end_earliest"] < row["envelope"]["end_latest"]
        for row in emitted_records
    )
    assertions["record_schema_ids_exact"] = all(
        row.get("schema_id") == RECORD_SCHEMA for row in emitted_records
    ) and all(row.get("schema_id") == SUMMARY_SCHEMA for row in emitted_summary)

    # INV-5 table
    inv5_rows = []
    inv5_ok = True
    for (lane, metric), expected in sorted(INV5_EXPECTED.items()):
        value = rederived["measured"][(lane, metric)]
        match = value == expected
        inv5_ok = inv5_ok and match
        inv5_rows.append(
            {
                "expected": expected,
                "lane": lane,
                "match": match,
                "measured": value,
                "metric": metric,
            }
        )
    assertions["inv5_ladder_reproduction_exact"] = inv5_ok
    receipt_inv5 = {
        (row["lane"], row["metric"]): row["measured"]
        for row in receipt.get("inv5_reproduction", {}).get("rows", [])
    }
    assertions["receipt_inv5_table_matches_independent_measurement"] = all(
        receipt_inv5.get((lane, metric))
        == rederived["measured"][(lane, metric)]
        for lane, metric in INV5_EXPECTED
    )

    for name, passed in assertions.items():
        if not passed:
            failures.append(name)

    result = {
        "assertions": dict(sorted(assertions.items())),
        "counts": {
            "emitted_filer_asserted_year_episodes": len(emitted_episodes),
            "emitted_person_office_records": len(emitted_records),
            "emitted_person_summary_rows": len(emitted_summary),
            "emitted_registrant_side_records": len(emitted_registrant),
            "rederived_filer_asserted_year_episodes": len(rederived["episodes"]),
            "rederived_person_office_records": len(rederived["records"]),
            "rederived_person_summary_rows": len(rederived["summary"]),
            "rederived_registrant_side_records": len(rederived["registrant_rows"]),
            "row_mismatches_episodes": episode_mismatches,
            "row_mismatches_records": record_mismatches,
            "row_mismatches_registrant": registrant_mismatches,
            "row_mismatches_summary": summary_mismatches,
        },
        "detail": detail,
        "failures": sorted(set(failures)),
        "hashes": {
            "primary_receipt_sha256": sha(primary / RECEIPT_FILE),
            "twin_receipt_sha256": sha(twin / RECEIPT_FILE),
            "verifier_implementation_sha256": sha(Path(__file__).resolve()),
            **{f"primary_{name}_sha256": digest for name, digest in sorted(hashes.items())},
            **{
                f"twin_{name}_sha256": sha(twin / name)
                for name in PAYLOAD_FILES
            },
        },
        "inv5_reproduction": {"all_match": inv5_ok, "rows": inv5_rows},
        "primary": str(primary),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "review_status": "REVIEW_REQUIRED",
        "schema_id": SCHEMA_ID,
        "stage_id": STAGE_ID,
        "status": "PASS" if not failures else "FAIL",
        "twin": str(twin),
        "verified_rule_version": receipt.get("rule_version"),
    }
    output = args.output
    if output is None:
        name = primary.name
        base = name[: -len("_primary")] if name.endswith("_primary") else name
        output = primary.parent / f"{base}_verification" / VERIFICATION_FILE
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_line(result))
    result["output"] = str(output)
    return result


# ---------------------------------------------------------------------------
# v3 SPINE LINK VERIFICATION  (--spine-link)
# ---------------------------------------------------------------------------
# INDEPENDENCE, STATED HONESTLY.  This verifier re-derives the record grouping,
# the bucket construction, the middle-initial and window filters, the status
# assignment, the summary aggregation and all 34 INV-5 metrics with its own
# code, and re-compares every carried-forward v2 field against the v2 files the
# receipt bound.  Two dependencies are REUSED rather than restated, and both are
# pinned by sha in the receipt this verifier re-hashes:
#   * the name standard (``fec/staffer_network/name_standard.py``) -- the single
#     ruled parser; a second copy of it would be a second standard.
#   * the spine's OWN office key (``HouseOfficeKey`` / ``senate_office_key``) --
#     restating 120 lines of the spine's member-office resolution here would
#     produce a verifier that can disagree with the spine about what an office
#     IS, which is not a check, it is a second opinion.
# Both facts are asserted in the output receipt so a reader is never left to
# assume the check was blind where it was not.
SPINE_LINK_VERIFICATION_SCHEMA = (
    "staffer-network-tiered-corroboration-spine-link-verification-v1"
)
SPINE_LINK_STAGE_ID = "tiered-corroboration-sidecar-part-a-spine-link"
SPINE_LINK_VERIFICATION_FILE = "tiered_corroboration_spine_link_verification_receipt.json"
SPINE_LINK_LANE_FIELDS = {
    LANE_H1: ("employing_office_raw", "payroll_payee_raw", "payroll_comma"),
    LANE_H2: ("employing_office_candidate", "display_name", "display"),
    LANE_SENATE: ("employing_office_candidate", "display_name", "display"),
}


def load_sibling_module(name: str, path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        raise VerificationFailure(f"cannot import {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verifier_sidecar_office_key(chamber: str, office_raw: str) -> str:
    """This module's OWN restatement of the record office key, from
    :func:`house_office_group` and the Senate whitespace rule."""

    if chamber == "house":
        return house_office_group(office_raw)
    return " ".join(office_raw.strip().upper().split())


def verifier_middle_compatible(left, right) -> bool:
    if not left or not right:
        return True
    return left[0] == right[0]


def verifier_windows_overlap(left, right) -> tuple[bool, str]:
    a0, a1 = left
    b0, b1 = right
    if not (a0 and a1 and b0 and b1):
        return True, "NOT_APPLICABLE"
    return (a0 <= b1 and b0 <= a1), "APPLIED"


def verifier_spine_link_inv5(summaries, records, registrants, a6_path: Path):
    """This module's own re-measurement of the 34 ladder metrics, off the
    EMITTED v3 corpus.  No tier is recomputed; each is counted from rows that
    already carry theirs."""

    def ge(letter: str, floor: str) -> bool:
        return tier_rank(letter) >= tier_rank(floor)

    measured: dict[tuple[str, str], int] = {}
    for lane in (LANE_H1, LANE_H2, LANE_SENATE):
        in_lane = [row for row in summaries if row["tier_by_lane"][lane] != "L0"]
        measured[(lane, "people")] = len(in_lane)
        for floor, metric in (
            ("L2", "L2_name_anchored"),
            ("L3", "L3_office_corroborated"),
            ("L4", "L4_chronology_consistent"),
        ):
            measured[(lane, metric)] = sum(
                1 for row in in_lane if ge(row["tier_by_lane"][lane], floor)
            )
    house = [row for row in summaries if row["tier_by_chamber"]["house"] != "L0"]
    measured[("house_union", "people")] = len(house)
    for floor, metric in (
        ("L2", "L2_name_anchored"),
        ("L3", "L3_office_corroborated"),
        ("L4", "L4_chronology_consistent"),
    ):
        measured[("house_union", metric)] = sum(
            1 for row in house if ge(row["tier_by_chamber"]["house"], floor)
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
        and ge(row["tier_by_lane"][LANE_SENATE], "L4")
    )
    for lane in (LANE_H1, LANE_H2):
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
            and ge(senate_tier[row["lda_source_person_id"]], "L4")
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
    a6_both = 0
    for row in read_rows(a6_path):
        a6_rows += 1
        mention = row.get("office_employer_mention") or {}
        dates = row.get("date_range_mention") or {}
        if (
            mention.get("entity_class")
            in {"COMMITTEE_CANDIDATE", "MEMBER_OFFICE_CANDIDATE"}
            and dates.get("explicit_start_year") is not None
            and dates.get("explicit_end_year") is not None
        ):
            a6_both += 1
    measured[("a6_near_candidates", "rows")] = a6_rows
    measured[("a6_near_candidates", "resolvable_entity_and_both_years")] = a6_both
    return measured


def verify_spine_link(args: argparse.Namespace) -> dict[str, Any]:
    primary = Path(args.primary)
    twin = Path(args.twin)
    receipt = load_json(primary / RECEIPT_FILE)
    twin_receipt = load_json(twin / RECEIPT_FILE)
    failures: list[str] = []
    assertions: dict[str, bool] = {}
    detail: dict[str, Any] = {}

    inputs = receipt.get("inputs") or {}
    drifted = []
    for label, entry in sorted(inputs.items()):
        path = Path(entry["path"])
        if not path.is_file():
            drifted.append(f"{label}:MISSING")
            continue
        if sha(path) != entry["sha256"]:
            drifted.append(f"{label}:SHA")
    assertions["every_receipt_input_rehashes"] = not drifted
    detail["input_drift"] = sorted(drifted)
    if drifted:
        failures.append("RECEIPT_INPUT_HASH_DRIFT")

    v3_records = list(read_rows(primary / RECORD_FILE))
    v3_summaries = list(read_rows(primary / SUMMARY_FILE))
    v2_records = list(read_rows(Path(inputs["v2:tiered_person_office_records"]["path"])))
    v2_summaries = list(read_rows(Path(inputs["v2:tiered_person_summary"]["path"])))
    v2_registrants = list(read_rows(Path(inputs["v2:registrant_side_records"]["path"])))
    v2_receipt = load_json(Path(inputs["v2:receipt"]["path"]))

    # --- carried-forward byte identity, re-compared here -------------------
    carried_mismatch: list[str] = []
    if len(v3_records) != len(v2_records):
        failures.append("RECORD_COUNT_NOT_CONSERVED")
    else:
        v2_keys = sorted(v2_records[0].keys()) if v2_records else []
        for new, old in zip(v3_records, v2_records):
            if new["lda_source_person_id"] != old["lda_source_person_id"]:
                carried_mismatch.append("ROW_ORDER")
                break
            for key in v2_keys:
                if key == "schema_id":
                    continue
                if compact(new.get(key)) != compact(old.get(key)):
                    carried_mismatch.append(
                        f"{old['lda_source_person_id']}|{old['office_key']}|{key}"
                    )
    summary_mismatch: list[str] = []
    if len(v3_summaries) != len(v2_summaries):
        failures.append("SUMMARY_COUNT_NOT_CONSERVED")
    else:
        v2_summary_keys = sorted(v2_summaries[0].keys()) if v2_summaries else []
        for new, old in zip(v3_summaries, v2_summaries):
            for key in v2_summary_keys:
                if key == "schema_id":
                    continue
                if compact(new.get(key)) != compact(old.get(key)):
                    summary_mismatch.append(f"{old['lda_source_person_id']}|{key}")
    assertions["v2_record_fields_byte_identical"] = not carried_mismatch
    assertions["v2_summary_fields_byte_identical"] = not summary_mismatch
    detail["carried_record_mismatch_examples"] = sorted(carried_mismatch)[:20]
    detail["carried_summary_mismatch_examples"] = sorted(summary_mismatch)[:20]
    if carried_mismatch:
        failures.append("V2_RECORD_FIELD_NOT_BYTE_IDENTICAL")
    if summary_mismatch:
        failures.append("V2_SUMMARY_FIELD_NOT_BYTE_IDENTICAL")

    carried_files_ok = True
    for name, label in (
        (EPISODE_FILE, "v2:filer_asserted_year_episodes"),
        (REGISTRANT_FILE, "v2:registrant_side_records"),
    ):
        if sha(primary / name) != inputs[label]["sha256"]:
            carried_files_ok = False
    assertions["carried_files_byte_identical_to_v2"] = carried_files_ok
    if not carried_files_ok:
        failures.append("CARRIED_FILE_NOT_BYTE_IDENTICAL_TO_V2")

    # --- independent re-derivation of the link -----------------------------
    standard = load_sibling_module(
        "spine_link_name_standard", Path(inputs["name_standard:module"]["path"])
    )
    spine_module = load_sibling_module(
        "spine_link_spine_builder", Path(inputs["spine:builder_module"]["path"])
    )
    roster_current = Path(inputs["roster:legislators-current"]["path"])
    roster = spine_module.load_roster(roster_current.parent)
    nicknames, _ = spine_module.load_nickname_table(
        Path(inputs["spine:nickname_table"]["path"])
    )
    house_office_key, _stats, key_failures = spine_module.build_house_office_key(
        Path(inputs["house_ledger:observations"]["path"]), roster, nicknames
    )
    if key_failures:
        failures.append("HOUSE_OFFICE_KEY_PREPASS_FAILURE")

    payee_index: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for lane, (office_field, payee_field, payee_source) in sorted(
        SPINE_LINK_LANE_FIELDS.items()
    ):
        chamber = "senate" if lane == LANE_SENATE else "house"
        for row in read_rows(Path(inputs[f"lane:{lane}"]["path"])):
            person = str(row["lda_source_person_id"])
            office_raw = row.get(office_field) or ""
            payee_raw = (row.get(payee_field) or "").strip()
            key = (
                person,
                chamber,
                lane,
                verifier_sidecar_office_key(chamber, office_raw),
            )
            slot = payee_index.setdefault(
                key,
                {"office_raws": set(), "payees": set(), "payee_source": payee_source},
            )
            slot["office_raws"].add(office_raw)
            if payee_raw:
                slot["payees"].add(payee_raw)

    spine_root = Path(inputs["spine:hill_person_spine"]["path"]).parent
    name_key_by_person = {
        row["spine_person_id"]: row["name_key"]
        for row in read_rows(spine_root / "hill_person_spine.ndjson.gz")
    }
    legacy_keys: defaultdict[str, set[str]] = defaultdict(set)
    for row in read_rows(spine_root / "spine_id_map_v6_to_v7.ndjson.gz"):
        person_id = row.get("person_id")
        key_v6 = row.get("key_v6")
        if isinstance(person_id, str) and isinstance(key_v6, str) and key_v6:
            legacy_keys[person_id].add(key_v6)
    buckets: defaultdict[tuple[str, str, str, str], list] = defaultdict(list)
    office_universe: set[tuple[str, str]] = set()
    for ordinal, row in enumerate(
        read_rows(spine_root / "hill_person_office_spans.ndjson.gz")
    ):
        person_id = row["spine_person_id"]
        envelope = row.get("envelope") or {}
        office_universe.add((row["chamber"], row["office_key"]))
        current = name_key_by_person.get(person_id)
        keys = ([(current, "v7")] if current else []) + [
            (legacy, "v6_legacy")
            for legacy in sorted(legacy_keys.get(person_id, ()))
            if legacy != current
        ]
        for key, generation in keys:
            last, first_class, middle = key.split("|", 2)
            buckets[(row["chamber"], row["office_key"], last, first_class)].append(
                (
                    person_id,
                    f"{person_id}#{ordinal}",
                    middle or None,
                    (envelope.get("start_earliest"), envelope.get("end_latest")),
                    generation,
                )
            )

    status_counts: Counter = Counter()
    link_mismatches: list[str] = []
    id_mismatches: list[str] = []
    basis_mismatches: list[str] = []
    person_ids: defaultdict[str, set[str]] = defaultdict(set)
    person_hist: defaultdict[str, Counter] = defaultdict(Counter)
    for record in v3_records:
        chamber = record["chamber"]
        lane = record["source_lane"]
        person = record["lda_source_person_id"]
        slot = payee_index.get((person, chamber, lane, record["office_key"]))
        status = "NOT_FOUND"
        spine_person_id = None
        basis = None
        if slot is not None:
            office_keys = {
                house_office_key(raw)
                if chamber == "house"
                else spine_module.senate_office_key(raw)
                for raw in slot["office_raws"]
            }
            if len(office_keys) != 1:
                status = "AMBIGUOUS"
            else:
                spine_office_key = next(iter(office_keys))
                name_keys = sorted(
                    {
                        standard.name_key(
                            standard.parse_name(raw, slot["payee_source"])
                        )
                        for raw in slot["payees"]
                    }
                )
                name_keys = [key for key in name_keys if key.split("|", 2)[0]]
                envelope = record.get("envelope") or {}
                record_window = (
                    envelope.get("start_earliest"),
                    envelope.get("end_latest"),
                )
                hits: dict[str, dict[str, set]] = {}
                for key in name_keys:
                    last, first_class, middle = key.split("|", 2)
                    middle = middle or None
                    for (
                        candidate_id,
                        span_id,
                        span_middle,
                        span_window,
                        generation,
                    ) in buckets.get(
                        (chamber, spine_office_key, last, first_class), ()
                    ):
                        if not verifier_middle_compatible(span_middle, middle):
                            continue
                        overlap, window_test = verifier_windows_overlap(
                            record_window, span_window
                        )
                        if not overlap:
                            continue
                        entry = hits.setdefault(
                            candidate_id,
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
                            "EXACT"
                            if (span_middle or "") == (middle or "")
                            else "MIDDLE_COMPATIBLE"
                        )
                        entry["window_tests"].add(window_test)
                if len(hits) == 1:
                    status = "LINKED"
                    spine_person_id, entry = next(iter(hits.items()))
                    generations = sorted(entry["generations"])
                    basis = {
                        "key_generation": (
                            "both" if len(generations) > 1 else generations[0]
                        ),
                        "name_key": sorted(entry["name_keys"])[0],
                        "name_key_equality": (
                            "EXACT"
                            if "EXACT" in entry["equality"]
                            else "MIDDLE_COMPATIBLE"
                        ),
                        "office_key": spine_office_key,
                        "payee_source": slot["payee_source"],
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
                    }
                elif len(hits) > 1:
                    status = "AMBIGUOUS"
        status_counts[status] += 1
        tag = f"{person}|{record['office_key']}|{record['run_index']}"
        if record["spine_link_status"] != status:
            link_mismatches.append(f"{tag}|{record['spine_link_status']}!={status}")
        if record["spine_person_id"] != spine_person_id:
            id_mismatches.append(tag)
        if compact(record["spine_link_basis"]) != compact(basis):
            basis_mismatches.append(tag)
        if status == "LINKED":
            person_ids[person].add(spine_person_id)
        person_hist[person][status] += 1

    assertions["every_link_status_independently_rederived"] = not link_mismatches
    assertions["every_spine_id_independently_rederived"] = not id_mismatches
    assertions["every_link_basis_independently_rederived"] = not basis_mismatches
    detail["link_status_mismatch_examples"] = sorted(link_mismatches)[:20]
    detail["spine_id_mismatch_examples"] = sorted(id_mismatches)[:20]
    detail["link_basis_mismatch_examples"] = sorted(basis_mismatches)[:20]
    if link_mismatches:
        failures.append("LINK_STATUS_NOT_REDERIVED")
    if id_mismatches:
        failures.append("SPINE_ID_NOT_REDERIVED")
    if basis_mismatches:
        failures.append("LINK_BASIS_NOT_REDERIVED")

    summary_link_mismatches = []
    for summary in v3_summaries:
        person = summary["lda_source_person_id"]
        expected_ids = sorted(person_ids.get(person, ()))
        hist = person_hist.get(person, Counter())
        expected_summary = {
            "ambiguous": hist.get("AMBIGUOUS", 0),
            "linked_records": hist.get("LINKED", 0),
            "not_found": hist.get("NOT_FOUND", 0),
        }
        if summary["spine_person_ids"] != expected_ids or compact(
            summary["spine_link_summary"]
        ) != compact(expected_summary):
            summary_link_mismatches.append(person)
    assertions["every_summary_link_independently_rederived"] = (
        not summary_link_mismatches
    )
    detail["summary_link_mismatch_examples"] = sorted(summary_link_mismatches)[:20]
    if summary_link_mismatches:
        failures.append("SUMMARY_LINK_NOT_REDERIVED")

    unlinked_with_id = sum(
        1
        for row in v3_records
        if row["spine_link_status"] != "LINKED" and row["spine_person_id"] is not None
    )
    assertions["no_unlinked_record_carries_a_spine_id"] = unlinked_with_id == 0
    if unlinked_with_id:
        failures.append("UNLINKED_RECORD_CARRIES_A_SPINE_ID")

    every_id_in_spine = all(
        pid in name_key_by_person
        for row in v3_records
        if row["spine_person_id"]
        for pid in (row["spine_person_id"],)
    )
    assertions["every_emitted_spine_id_exists_in_the_spine"] = every_id_in_spine
    if not every_id_in_spine:
        failures.append("EMITTED_SPINE_ID_NOT_IN_THE_SPINE")

    # --- INV-5, re-measured here ------------------------------------------
    measured = verifier_spine_link_inv5(
        v3_summaries,
        v3_records,
        v2_registrants,
        Path(inputs["a6_near_candidates"]["path"]),
    )
    receipt_inv5 = {
        (row["lane"], row["metric"]): row for row in receipt["inv5_reproduction"]["rows"]
    }
    v2_inv5 = {
        (row["lane"], row["metric"]): row["measured"]
        for row in (v2_receipt.get("inv5_reproduction") or {}).get("rows", [])
    }
    inv5_rows = []
    for key, expected in INV5_EXPECTED.items():
        lane, metric = key
        row = {
            "expected": expected,
            "lane": lane,
            "measured": measured.get(key),
            "metric": metric,
            "receipt_measured": (receipt_inv5.get(key) or {}).get("measured"),
            "v2_measured": v2_inv5.get(key),
        }
        row["match"] = (
            row["measured"] == expected
            and row["receipt_measured"] == expected
            and row["v2_measured"] == expected
        )
        inv5_rows.append(row)
    inv5_all_match = all(row["match"] for row in inv5_rows) and len(inv5_rows) == 34
    assertions["inv5_ladder_reproduction_exact_against_v2_and_the_constant"] = (
        inv5_all_match
    )
    if not inv5_all_match:
        failures.append("INV5_LADDER_REPRODUCTION_MISMATCH")

    # --- schemas ------------------------------------------------------------
    # audits/staffer_network/<this file> -> parents[2] is the live root.
    repo_root = Path(__file__).resolve().parents[2]
    schema_dir = repo_root / "fec" / "staffer_network" / "schemas"
    schema_ok = True
    schema_error = None
    try:
        if str(repo_root) not in sys.path:
            sys.path.insert(0, str(repo_root))
        from fec.staffer_network.schema_validation import (  # noqa: PLC0415
            validate_instance,
            validate_schema_definition,
        )

        record_schema = load_json(schema_dir / "tiered_person_office_record_v2.schema.json")
        summary_schema = load_json(schema_dir / "tiered_person_summary_v2.schema.json")
        receipt_schema = load_json(
            schema_dir / "tiered_corroboration_spine_link_receipt.schema.json"
        )
        for schema in (record_schema, summary_schema, receipt_schema):
            validate_schema_definition(schema)
        for row in v3_records:
            validate_instance(row, record_schema)
        for row in v3_summaries:
            validate_instance(row, summary_schema)
        validate_instance(receipt, receipt_schema)
    except Exception as error:  # noqa: BLE001 - reported, never swallowed
        schema_ok = False
        schema_error = f"{type(error).__name__}: {error}"
    assertions["every_row_validates_against_the_committed_schema"] = schema_ok
    detail["schema_error"] = schema_error
    if not schema_ok:
        failures.append("SCHEMA_VALIDATION_FAILED")

    # --- twin ---------------------------------------------------------------
    hashes: dict[str, str] = {}
    twin_identical = True
    for name in (RECORD_FILE, SUMMARY_FILE, EPISODE_FILE, REGISTRANT_FILE):
        primary_sha = sha(primary / name)
        twin_sha = sha(twin / name)
        hashes[f"primary_{name}_sha256"] = primary_sha
        hashes[f"twin_{name}_sha256"] = twin_sha
        if primary_sha != twin_sha:
            twin_identical = False
    hashes["primary_receipt_sha256"] = sha(primary / RECEIPT_FILE)
    hashes["twin_receipt_sha256"] = sha(twin / RECEIPT_FILE)
    volatile = {"generated_at", "run_id"}
    receipts_equal = compact(
        {k: v for k, v in receipt.items() if k not in volatile}
    ) == compact({k: v for k, v in twin_receipt.items() if k not in volatile})
    assertions["primary_twin_payload_byte_identical"] = twin_identical
    assertions["twin_receipt_equals_primary_receipt_excluding_generated_at"] = (
        receipts_equal
    )
    if not twin_identical:
        failures.append("PRIMARY_TWIN_NOT_BYTE_IDENTICAL")
    if not receipts_equal:
        failures.append("TWIN_RECEIPT_DIFFERS")

    # --- receipt agreement --------------------------------------------------
    assertions["receipt_stage_id_exact"] = receipt.get("stage_id") == SPINE_LINK_STAGE_ID
    assertions["receipt_status_pass"] = receipt.get("status") == "PASS"
    assertions["receipt_declares_no_failures"] = not receipt.get("failures")
    assertions["receipt_zero_promotions"] = (
        receipt.get("canonical_identity_promotions") == 0
        and receipt.get("canonical_employment_promotions") == 0
        and receipt.get("canonical_promotions_zero") is True
    )
    assertions["receipt_declares_tiers_not_recomputed"] = (
        (receipt.get("link_rule") or {}).get("tiers_recomputed") is False
    )
    receipt_hist = (receipt.get("counts") or {}).get("link_status") or {}
    assertions["receipt_link_histogram_matches_independent_count"] = all(
        receipt_hist.get(status, 0) == status_counts.get(status, 0)
        for status in ("LINKED", "AMBIGUOUS", "NOT_FOUND")
    )
    if not assertions["receipt_link_histogram_matches_independent_count"]:
        failures.append("RECEIPT_LINK_HISTOGRAM_DISAGREES")
    for key in (
        "receipt_stage_id_exact",
        "receipt_status_pass",
        "receipt_declares_no_failures",
        "receipt_zero_promotions",
        "receipt_declares_tiers_not_recomputed",
    ):
        if not assertions[key]:
            failures.append(key.upper())

    unpromoted = assert_unpromoted(v3_records) + assert_unpromoted(v3_summaries)
    assertions["anti_promotion_tripwire_clean"] = not unpromoted
    detail["anti_promotion_tripwire"] = unpromoted[:20]
    if unpromoted:
        failures.append("ANTI_PROMOTION_TRIPWIRE")

    result = {
        "assertions": dict(sorted(assertions.items())),
        "counts": {
            "emitted_person_office_records": len(v3_records),
            "emitted_person_summary_rows": len(v3_summaries),
            "rederived_link_status": dict(sorted(status_counts.items())),
            "unlinked_records_carrying_a_spine_id": unlinked_with_id,
        },
        "detail": detail,
        "failures": sorted(set(failures)),
        "hashes": hashes,
        "independence": {
            "reimplemented_here": [
                "record office grouping",
                "record-to-lane payee recovery",
                "spine bucket construction",
                "middle-initial and window filters",
                "link status assignment",
                "summary aggregation",
                "all 34 INV-5 metrics",
                "carried-forward v2 field comparison",
            ],
            "reused_not_reimplemented": [
                "fec/staffer_network/name_standard.py (the one ruled parser)",
                "build_hill_personnel_spine.HouseOfficeKey / senate_office_key "
                "(the spine's own definition of an office)",
            ],
            "why": (
                "A second copy of the name standard would be a second standard, "
                "and a restated office key would let this verifier disagree with "
                "the spine about what an office IS. Both are pinned by sha in the "
                "receipt and re-hashed above."
            ),
        },
        "inv5_reproduction": {"all_match": inv5_all_match, "rows": inv5_rows},
        "primary": str(primary),
        "schema_id": SPINE_LINK_VERIFICATION_SCHEMA,
        "stage_id": SPINE_LINK_STAGE_ID,
        "status": "PASS",
        "twin": str(twin),
    }
    if result["failures"]:
        result["status"] = "FAIL"
    output = args.output
    if output is None:
        base = primary.name
        for suffix in ("_primary", "_twin"):
            if base.endswith(suffix):
                base = base[: -len(suffix)]
        output = primary.parent / f"{base}_verification" / SPINE_LINK_VERIFICATION_FILE
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(canonical_line(result))
    result["output"] = str(output)
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary", required=True, type=Path)
    parser.add_argument("--twin", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--spine-link",
        action="store_true",
        help="verify a v3 spine-link generation instead of a v2 generation",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    result = verify_spine_link(args) if args.spine_link else verify(args)
    print(f"status: {result['status']}")
    print(f"output: {result['output']}")
    print("counts:")
    for key, value in sorted(result["counts"].items()):
        print(f"  {key}: {value}")
    print("assertions:")
    for key, value in result["assertions"].items():
        print(f"  {'PASS' if value else 'FAIL'}  {key}")
    print(f"failures: {result['failures']}")
    print(f"inv5_all_match: {result['inv5_reproduction']['all_match']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
