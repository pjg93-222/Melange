#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify a Hill personnel spine generation.

This script does not import the builder.  It reads the primary receipt, rebinds
every declared input by recomputing its sha256, and then re-derives all five
payload files from the source ledgers with its own implementation of every rule
-- payee key parsing, office keys, container kinds, strict-bioguide resolution
with the term window, reporting-period algebra, identity clustering, the
cross-chamber merge, the LDA payroll-key join and the current-staffer link rule.
The re-derived rows must equal the emitted rows byte for byte: a 100% pass, not
a sample.

It also compares the primary and twin generations byte for byte, recomputes the
file hashes against the receipt, validates every row and the receipt against the
committed schemas, runs the A5b anti-promotion tripwire over every row and the
receipt, greps the language law, and rechecks conservation.

Exit code 0 on PASS, 1 on FAIL.  The verification receipt is written to
``--report-root/hill_personnel_spine_verification_receipt.json``.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
)

import yaml  # noqa: E402


SCHEMA_ID = "staffer-network-hill-personnel-spine-verification-v1"
STAGE_ID = "hill-personnel-spine-part-c"
GLASSBOX_SOURCE = "tiered-corroboration-sidecar"
GLASSBOX_SCRIPT = Path(r"C:\Users\pgoff\.claude\glassbox\emit.ps1")
RECEIPT_SCHEMA = "staffer-network-hill-personnel-spine-receipt-v1"

SPAN_FILE = "hill_person_office_spans.ndjson.gz"
SPINE_FILE = "hill_person_spine.ndjson.gz"
STAFFER_FILE = "current_staffer_links.ndjson.gz"
LDA_LINK_FILE = "lda_spine_links.ndjson.gz"
OFFICE_INDEX_FILE = "member_office_index.ndjson.gz"
RECEIPT_FILE = "hill_personnel_spine_receipt.json"
PAYLOAD_FILES = (SPAN_FILE, SPINE_FILE, STAFFER_FILE, LDA_LINK_FILE, OFFICE_INDEX_FILE)
VERIFICATION_FILE = "hill_personnel_spine_verification_receipt.json"

# Pinned from build_hill_personnel_spine.py's DEFAULT_RULE_VERSION, so a receipt cannot pass by
# echoing whatever rule_version it happens to carry (STAFFC-10 / DE-012 verifier blind spot).
EXPECTED_RULE_VERSION = "hill-personnel-spine-v2"

SCHEMA_DIR = REPO_ROOT / "fec" / "staffer_network" / "schemas"
SCHEMA_BY_FILE = {
    SPAN_FILE: "hill_person_office_span.schema.json",
    SPINE_FILE: "hill_person_spine.schema.json",
    STAFFER_FILE: "current_staffer_link.schema.json",
    LDA_LINK_FILE: "lda_spine_link.schema.json",
    OFFICE_INDEX_FILE: "member_office_index.schema.json",
}

# ---- name standard -----------------------------------------------------
# A generation built with the builder's ``--name-standard`` carries a sixth
# payload -- the id map -- and a ``name_standard`` block in its receipt.  This
# verifier learns the mode from that block and from nothing else: it has no
# such flag, and a generation without the block is verified exactly as before.
NAME_STANDARD_ID_MAP_FILE = "spine_id_map_v6_to_v7.ndjson.gz"
NAME_STANDARD_ID_MAP_SCHEMA_FILE = "hill_person_spine_id_map.schema.json"
#: Independently restated, as ``VERBATIM_LEAF_NAMES`` is: the leaf names a
#: name-standard generation adds that quote a person's own name.
NAME_STANDARD_VERBATIM_LEAF_NAMES = frozenset(
    {
        "first_class",
        "first_folded",
        # The blocked-merge receipt quotes the source office key. The builder
        # already classifies this field as verbatim; do not censor real names
        # such as OFFICE OF CONGRESSIONAL ACCESSIBILITY SERVICES.
        "first_office_key",
        "format_detected",
        "key_from_payee_key_lift",
        "key_from_raw_parse",
        "key_v6",
        "key_v7",
        "keys_before",
        "middle",
        "name_key",
        "nickname_raw",
        "payee_raw",
        "payee_raw_examples",
        "suffix",
        "suffix_observed",
    }
)

LANE_HOUSE_LEDGER = "house_ledger"
LANE_SENATE = "senate_payroll_2011_2026"

# Retired at the House ledger v3 rebind: the ledger carries the 2009Q3-2015Q4
# PDF era itself, so reading the separate candidate file as a second lane would
# admit every row of that era twice.  Named here so this verifier can assert
# that neither the receipt's inputs nor any emitted span carries it.
RETIRED_LANE_HOUSE_PDF = "house_sod_pdf_2009q3_2015q4"
RETIRED_PDF_INPUT_LABEL = "house_sod_pdf_candidates"
SOURCE_FORM_CSV = "detail_csv"
SOURCE_FORM_PDF = "house_gov_single_volume_pdf"
PDF_ERA_LAST_QUARTER = "2015Q4"
CSV_ERA_FIRST_QUARTER = "2016Q1"
CHAMBER_HOUSE = "house"
CHAMBER_SENATE = "senate"
PERIOD_KIND = {CHAMBER_HOUSE: "quarter", CHAMBER_SENATE: "half_year"}

ANNUALIZATION_DAYS = 365.2425
ENVELOPE_WIDENING_REPORTING_PERIODS = 1
MAX_OFFICE_RAW_EXAMPLES = 3
#: Ruling E.  The cap on payee raw examples is its OWN constant.  It happened
#: to equal MAX_OFFICE_RAW_EXAMPLES, which caps OFFICE raw examples on a span
#: row -- an unrelated quantity that a future change to either would have
#: silently dragged the other along with.  The builder's own name for this is
#: NAME_STANDARD_MAX_RAW_EXAMPLES and it is the same value.
NAME_STANDARD_MAX_RAW_EXAMPLES = 3
SHARED_EMPLOYEE_TITLE_PHRASES = ("SHARED EMPLOYEE",)
QUORUM_MEMBER_ROSTER_FALLBACK = True
CROSS_CHAMBER_REQUIRES_DISJOINT_PERIODS = True

LANGUAGE_LAW_TOKENS = (
    "access",
    "causal",
    "friend",
    "ideolog",
    "influence",
    "predict",
)
# Independently restated: the leaf field names whose values are quoted verbatim
# from a source ledger and are therefore exempt from the language law.
VERBATIM_LEAF_NAMES = frozenset(
    {
        "display_name",
        "first",
        "last",
        "member_display",
        "office_key",
        "office_raw_examples",
        "title_first",
        "title_last",
        "title_raw",
        "titles",
    }
)


class VerificationFailure(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# INV-11 glassbox -- same emitter, lane, source, stage and run id as the builder
# ---------------------------------------------------------------------------
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
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(GLASSBOX_SCRIPT),
        "-Lane",
        "claude",
        "-Kind",
        kind,
        "-Status",
        status,
        "-Summary",
        summary,
        "-Source",
        GLASSBOX_SOURCE,
        "-Stage",
        STAGE_ID,
        "-RunId",
        run_id,
        "-Quiet",
    ]
    if detail:
        command.extend(["-Detail", detail])
    if metadata:
        command.extend(["-MetadataJson", json.dumps(metadata, sort_keys=True)])
    try:
        completed = subprocess.run(  # noqa: S603
            command, capture_output=True, timeout=60, check=False
        )
    except Exception:  # pragma: no cover - environment dependent
        return False
    return completed.returncode == 0


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


def digest_of(value: Any) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            yield json.loads(line)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Rules -- restated here, not imported
# ---------------------------------------------------------------------------
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
DATE_HINT_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
NAME_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")
YEAR_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s+")
WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")
AMOUNT_CLEAN_RE = re.compile(r"[,$\s]")
SENATE_SUFFIX_RE = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
SENATOR_RE = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_RE = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
HOUSE_COMMITTEE_SHAPE_RE = re.compile(r"(?:^|\W)(COMM|COMMITTEE)(?:\W|$)")

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
HOUSE_COMMITTEE_FAMILIES = frozenset(
    {
        "ARMED SERVICES COMMITTEE",
        "COMMITTEE ON AGRICULTURE",
        "COMMITTEE ON APPROPRIATIONS",
        "COMMITTEE ON BENGHAZI",
        "COMMITTEE ON BUDGET",
        "COMMITTEE ON ENERGY AND COMMERCE",
        "COMMITTEE ON ETHICS",
        "COMMITTEE ON FINANCIAL SERVICE",
        "COMMITTEE ON FINANCIAL SERVICES",
        "COMMITTEE ON FOREIGN AFFAIRS",
        "COMMITTEE ON JUDICIARY",
        "COMMITTEE ON NATURAL RESOURCES",
        "COMMITTEE ON RULES",
        "COMMITTEE ON SMALL BUSINESS",
        "COMMITTEE ON VETERANS AFFAIRS",
        "EDUCATION AND LABOR",
        "ENERGY INDEP AND GLOBAL WARMING",
        "ENERGY INDEPEN AND GLB WARMING",
        "HOMELAND SECURITY",
        "HOUSE ADMINISTRATION",
        "INTELLIGENCE",
        "JOINT COMMMITTEE ON TAXATION",
        "OVERSIGHT AND GOVERNMENT REFORM",
        "SCIENCE AND TECHNOLOGY",
        "STANDARDS OF OFFICIAL CONDUCT",
        "TRANSPORTATION-INFRASTRUCTURE",
        "VETERANS AFFAIRS",
        "VETERANS' AFFAIRS",
    }
)
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
SENATE_COMMITTEE_OFFICE_KEYS = frozenset({
    "AGRICULTURE NUTR FOR", "AGRICULTURE NUTRITION AND FORESTRY",
    "AGRICULTURE NUTRITION FORESTRY", "APPROPRIATIONS", "ARMED SERVICES",
    "BANKING HOUSING AND URBAN AFFAIRS", "BANKING HOUSING URBAN AFFAIRS",
    "BANKING HOUSING URBDEV", "BUDGET", "COMMERCE SCI TRANS",
    "COMMERCE SCIENCE AND TRANSPORTATION", "COMMERCE SCIENCE TRANSPORTATION",
    "ENERGY AND NATURAL RESOURCES", "ENERGY NATURAL RES",
    "ENERGY NATURAL RESOURCES", "ENVIRONMENT AND PUBLIC WORKS",
    "ENVIRONMENT PUB WORKS", "ENVIRONMENT PUBLIC WORKS", "ETHICS", "FINANCE",
    "FOREIGN RELATIONS", "HEALTH EDU LABOR PENS",
    "HEALTH EDUCATION LABOR AND PENSIONS", "HOMELAND SEC GOV AFF",
    "HOMELAND SECURITY AND GOVERNMENTAL AFFAIRS",
    "HOMELAND SECURITY GOVERNMENTAL AFFAIRS", "INDIAN AFFAIRS", "INTELLIGENCE",
    "JOINT ECONOMIC", "JUDICIARY", "RULES ADMINISTRATION",
    "RULES AND ADMINISTRATION", "SELECT COM ON INTEL", "SMALL BUS ENTREP",
    "SMALL BUSINESS AND ENTREPRENEURSHIP", "SPECIAL COM ON AGING",
    "SPECIAL COMMITTEE ON AGING", "VETERANS AFFAIRS",
})
NICKNAME_MAP = {
    'bill': 'william', 'billy': 'william', 'will': 'william',
    'joe': 'joseph', 'joey': 'joseph',
    'mike': 'michael', 'mikey': 'michael',
    'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'robbie': 'robert',
    'jim': 'james', 'jimmy': 'james',
    'tom': 'thomas', 'tommy': 'thomas',
    'dave': 'david', 'davey': 'david',
    'chuck': 'charles', 'charlie': 'charles', 'chick': 'charles',
    'ted': 'edward', 'eddie': 'edward', 'ed': 'edward',
    'rich': 'richard', 'rick': 'richard', 'ricky': 'richard', 'dick': 'richard',
    'dan': 'daniel', 'danny': 'daniel',
    'ken': 'kenneth', 'kenny': 'kenneth',
    'greg': 'gregory',
    'steve': 'steven',
    'pat': 'patrick',
    'tony': 'anthony',
    'nick': 'nicholas',
    'andy': 'andrew', 'drew': 'andrew',
    'matt': 'matthew',
    'chris': 'christopher',
    'sam': 'samuel',
    'alex': 'alexander',
    'ben': 'benjamin',
    'gene': 'eugene',
    'larry': 'lawrence',
    'jerry': 'gerald',
    'ron': 'ronald', 'ronnie': 'ronald',
    'russ': 'russell',
    'walt': 'walter',
    'nate': 'nathan',
    'liz': 'elizabeth', 'beth': 'elizabeth',
    'kathy': 'katherine', 'kate': 'katherine', 'katie': 'katherine',
    'debbie': 'deborah', 'deb': 'deborah',
    'sue': 'susan', 'suzy': 'susan',
}


def ascii_fold(value: str | None) -> str:
    return (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def name_tokens(text: str) -> list[str]:
    result = []
    for token in NAME_TOKEN_RE.findall(text):
        trimmed = token.strip("-'")
        if trimmed and trimmed.upper() not in SUFFIXES:
            result.append(trimmed)
    return result


def triple(last: str, first: str, middle: str | None):
    return (last.casefold(), first.casefold(), middle.casefold()[:1] if middle else None)


def payroll_payee_key(value: str | None):
    text = DATE_HINT_RE.sub(" ", ascii_fold(value))
    if not text.strip():
        return None
    if "," in text:
        left, _, right = text.partition(",")
        surname_tokens = name_tokens(left)
        rest_tokens = name_tokens(right)
        if not surname_tokens or not rest_tokens:
            return None
        return triple(
            " ".join(surname_tokens),
            rest_tokens[0],
            rest_tokens[1] if len(rest_tokens) > 1 else None,
        )
    tokens = name_tokens(text)
    if len(tokens) < 2:
        return None
    return triple(tokens[0], tokens[1], tokens[2] if len(tokens) > 2 else None)


def display_payee_key(value: str | None):
    tokens = name_tokens(ascii_fold(value))
    if len(tokens) < 2:
        return None
    return triple(tokens[-1], tokens[0], tokens[1] if len(tokens) > 2 else None)


def middle_compatible(left: str | None, right: str | None) -> bool:
    return not left or not right or left[0] == right[0]


def payee_sort_key(payee_key) -> tuple[str, str, str]:
    """A total order over payee key triples.

    ``middle_initial`` is ``None`` or a one-character string, so the raw triple
    is not orderable across the two forms.  The empty string stands in for
    ``None`` and sorts first; ``triple`` never emits an empty middle initial, so
    the substitution is injective and the order is total.
    """

    return (payee_key[0], payee_key[1], payee_key[2] or "")


# Independently restated.  The dash or apostrophe that introduces a Statement of
# Disbursements continuation is REQUIRED; with it optional the pattern also ate a
# trailing CON out of BACON and MELANCON.  Same shape as the House ledger's own
# continuation pattern.
CONTINUATION_RE = re.compile(
    "(?:[—–�']\\s*Con\\.?|\\s+Con\\.)\\s*$", re.IGNORECASE
)


@lru_cache(maxsize=None)
def normalize_office(raw: str) -> str:
    value = YEAR_PREFIX_RE.sub("", raw or "").strip()
    value = value.replace("’", "'")
    value = CONTINUATION_RE.sub("", value).strip()
    value = value.replace("&", " AND ")
    return re.sub(r"\s+", " ", value).strip().upper()


def is_hon_office(normalized: str) -> bool:
    return normalized.startswith("HON.") or normalized.startswith("HON ")


def hon_tokens(normalized: str, drop_initials: bool) -> list[str]:
    remainder = (
        normalized.split(".", 1)[1] if normalized.startswith("HON.") else normalized[3:]
    )
    cleaned = []
    for token in WORD_TOKEN_RE.findall(remainder):
        trimmed = token.strip(".").strip(",")
        if not trimmed or trimmed.upper() in SUFFIXES:
            continue
        if drop_initials and len(trimmed.replace(".", "")) <= 1:
            continue
        cleaned.append(trimmed)
    return cleaned


@lru_cache(maxsize=None)
def senate_office_key(office_raw: str) -> str:
    value = (office_raw or "").replace("’", "'").strip()
    return re.sub(r"\s+", " ", value).upper()


# ---------------------------------------------------------------------------
# House member office key -- independently restated.
#
# A member office is keyed on the member the House ledger resolved, never on the
# bare surname.  Level 1 is the ledger's own HON:<bioguide> for an office string
# the ledger resolved; level 2 is that same key reached by the office string's
# (nickname-normalized first name, surname) pair, accepted only when the pair
# carries exactly one ledger bioguide and at most one roster member holding that
# pair served in the covered era; level 3 is HON:<first>|<surname>.
# ---------------------------------------------------------------------------
HOUSE_MEMBER_KEY_ERA = (2009, 2026)


def house_member_name_pair(
    office_raw: str, nicknames: Mapping[str, str]
) -> tuple[str, str] | None:
    normalized = normalize_office(office_raw)
    if not is_hon_office(normalized):
        return None
    cleaned = hon_tokens(normalized, drop_initials=True)
    if not cleaned:
        return None
    first = cleaned[0] if len(cleaned) >= 2 else None
    return normalize_first_name(first, nicknames).upper(), cleaned[-1].upper()


class HouseOfficeKey:
    def __init__(
        self,
        ledger_key_by_office_raw: Mapping[str, str],
        bioguide_by_name_pair: Mapping[tuple[str, str], str],
        nicknames: Mapping[str, str],
    ) -> None:
        self._by_raw = dict(ledger_key_by_office_raw)
        self._by_pair = dict(bioguide_by_name_pair)
        self._nicknames = dict(nicknames)
        self._cache: dict[str, str] = {}
        self.bioguide_by_key: dict[str, str] = {}
        for key in self._by_raw.values():
            self.bioguide_by_key[key] = key.split(":", 1)[1]
        for bioguide in self._by_pair.values():
            self.bioguide_by_key[f"HON:{bioguide}"] = bioguide

    def __call__(self, office_raw: str) -> str:
        cached = self._cache.get(office_raw)
        if cached is not None:
            return cached
        self._cache[office_raw] = key = self._derive(office_raw)
        return key

    def _derive(self, office_raw: str) -> str:
        normalized = normalize_office(office_raw)
        if not is_hon_office(normalized):
            return normalized
        exact = self._by_raw.get(office_raw)
        if exact is not None:
            return exact
        pair = house_member_name_pair(office_raw, self._nicknames)
        if pair is None:
            return f"HON:{normalized}"
        bioguide = self._by_pair.get(pair)
        if bioguide is not None:
            return f"HON:{bioguide}"
        return f"HON:{pair[0]}|{pair[1]}"


def build_house_office_key(
    ledger_observations_path: Path | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nicknames: Mapping[str, str],
) -> HouseOfficeKey:
    key_by_raw: dict[str, str] = {}
    bios_by_pair: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    if ledger_observations_path is not None:
        for row in read_rows(ledger_observations_path):
            raw = row.get("office_raw")
            key = row.get("office_key")
            bioguide = row.get("member_bioguide")
            if not isinstance(raw, str) or not raw:
                continue
            if not isinstance(key, str) or not isinstance(bioguide, str) or not bioguide:
                continue
            if key != f"HON:{bioguide}":
                continue
            if key_by_raw.setdefault(raw, key) != key:
                continue
            pair = house_member_name_pair(raw, nicknames)
            if pair is not None:
                bios_by_pair[pair].add(bioguide)

    low, high = HOUSE_MEMBER_KEY_ERA
    era_pairs: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for surname, people in roster.items():
        for person in people:
            if person["max_year"] < low or person["min_year"] > high:
                continue
            era_pairs[
                (normalize_first_name(person["first"], nicknames).upper(), surname)
            ].add(person["bioguide"])

    accepted = {
        pair: next(iter(bioguides))
        for pair, bioguides in bios_by_pair.items()
        if len(bioguides) == 1 and len(era_pairs.get(pair, ())) <= 1
    }
    return HouseOfficeKey(key_by_raw, accepted, nicknames)


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
    if normalized in HOUSE_COMMITTEE_FAMILIES or HOUSE_COMMITTEE_SHAPE_RE.search(
        normalized
    ):
        return "committee"
    return "unresolved"


def container_kind_senate(office_raw: str) -> str:
    upper = (office_raw or "").strip().upper()
    if not upper:
        return "unresolved"
    if SENATOR_RE.match(upper) or INTERN_RE.match(upper):
        return "member_office"
    committee_key = re.sub(r"[^A-Z0-9]+", " ", upper).strip()
    if "COMMITTEE" in upper or committee_key in SENATE_COMMITTEE_OFFICE_KEYS:
        return "committee"
    if any(phrase in upper for phrase in SENATE_LEADERSHIP_PHRASES):
        return "leadership"
    return "admin"


def office_member_name(chamber: str, office_raw: str) -> tuple[str | None, str | None]:
    if chamber == CHAMBER_HOUSE:
        normalized = normalize_office(office_raw)
        if not is_hon_office(normalized):
            return None, None
        cleaned = hon_tokens(normalized, drop_initials=True)
        if not cleaned:
            return None, None
        return (cleaned[0] if len(cleaned) >= 2 else None), cleaned[-1]
    upper = (office_raw or "").strip().upper()
    senator = SENATOR_RE.match(upper)
    if senator:
        remainder = SENATE_SUFFIX_RE.sub("", senator.group(1)).strip()
        tokens = [item.strip(".,") for item in remainder.split() if item.strip(".,")]
        tokens = [item for item in tokens if len(item.replace(".", "")) > 1]
        if not tokens:
            return None, None
        return (tokens[0] if len(tokens) >= 2 else None), tokens[-1]
    intern = INTERN_RE.match(upper)
    if intern:
        surname = intern.group(1).strip().strip(".,")
        return (None, surname) if surname else (None, None)
    return None, None


NICKNAME_TABLE_SCHEMA_ID = "staffer-network-first-name-nickname-table-v1"


def flatten_nickname_payload(payload: Any) -> dict[str, str]:
    """Independently restated.  The committed table is
    ``{"schema_id": ..., "entries": {short: [formal, ...]}}``; it is read
    short -> formal and an entry with more than one formal form is dropped, so
    two different roster first names can never fold onto one token (INV-6)."""

    if not isinstance(payload, Mapping):
        return {}
    entries = payload.get("entries")
    if payload.get("schema_id") == NICKNAME_TABLE_SCHEMA_ID and isinstance(
        entries, Mapping
    ):
        committed: dict[str, str] = {}
        for short, formal in entries.items():
            if isinstance(formal, str):
                committed[str(short).strip().lower()] = formal.strip().lower()
            elif (
                isinstance(formal, list)
                and len(formal) == 1
                and isinstance(formal[0], str)
            ):
                committed[str(short).strip().lower()] = formal[0].strip().lower()
        return committed
    for wrapper in ("map", "nicknames", "aliases", "first_name_nicknames"):
        nested = payload.get(wrapper)
        if isinstance(nested, Mapping):
            return flatten_nickname_payload(nested)
    flat: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            flat[str(key).strip().lower()] = value.strip().lower()
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    flat[item.strip().lower()] = str(key).strip().lower()
    return flat


def load_nickname_table(path: Path | None) -> dict[str, str]:
    table = dict(NICKNAME_MAP)
    if path is None or not path.is_file():
        return table
    try:
        table.update(flatten_nickname_payload(load_json(path)))
    except (OSError, json.JSONDecodeError):
        return table
    return table


def normalize_first_name(name: str | None, table: Mapping[str, str]) -> str:
    lowered = (name or "").lower().strip(".")
    return table.get(lowered, lowered)


def load_roster(directory: Path | None) -> dict[str, list[dict[str, Any]]]:
    if directory is None:
        return {}
    by_surname: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        path = directory / filename
        if not path.is_file():
            continue
        people = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        for person in people:
            bioguide = ((person or {}).get("id") or {}).get("bioguide")
            if not bioguide:
                continue
            spans = []
            for term in person.get("terms") or []:
                try:
                    spans.append((int(term["start"][:4]), int(term["end"][:4])))
                except Exception:
                    pass
            if not spans:
                continue
            name = person.get("name") or {}
            by_surname[str(name.get("last", "")).upper()].append(
                {
                    "bioguide": bioguide,
                    "first": str(name.get("first", "")),
                    "min_year": min(item[0] for item in spans),
                    "max_year": max(item[1] for item in spans),
                }
            )
    return {
        key: sorted(value, key=lambda item: item["bioguide"])
        for key, value in by_surname.items()
    }


def resolve_member_bioguide(
    first: str | None,
    surname: str | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nicknames: Mapping[str, str],
    year_window: tuple[int, int] | None,
) -> tuple[str | None, str]:
    if not surname:
        return None, "UNRESOLVED_SURNAME_NOT_PARSED"
    candidates = roster.get(surname.upper())
    if not candidates:
        return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"
    if year_window is None:
        windowed = list(candidates)
    else:
        low, high = year_window
        windowed = [
            item
            for item in candidates
            if item["min_year"] <= high and item["max_year"] >= low
        ]
        if not windowed:
            return None, "UNRESOLVED_NO_ROSTER_TERM_IN_OBSERVED_WINDOW"
    if first:
        wanted = normalize_first_name(first, nicknames)
        matched = [
            item
            for item in windowed
            if normalize_first_name(item["first"], nicknames) == wanted
        ]
        matched_all = [
            item
            for item in candidates
            if normalize_first_name(item["first"], nicknames) == wanted
        ]
        if len(matched) == 1:
            return matched[0]["bioguide"], (
                "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
                if len(matched_all) == 1
                else "STRICT_ROSTER_SURNAME_AND_FIRST_NAME_TERM_WINDOW"
            )
        if len(matched) > 1:
            return None, "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"
        return None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
    if len(windowed) == 1:
        return windowed[0]["bioguide"], (
            "STRICT_ROSTER_UNIQUE_SURNAME_NO_FIRST_NAME_IN_OFFICE_STRING"
            if len(candidates) == 1
            else "STRICT_ROSTER_UNIQUE_SURNAME_TERM_WINDOW"
        )
    return None, "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME"


def parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    try:
        parts = str(value).strip()[:10].split("-")
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        return None


def quarter_from_token(token: str | None):
    match = QUARTER_RE.match((token or "").strip().upper())
    return (int(match.group(1)), int(match.group(2))) if match else None


def quarter_bounds(key: tuple[int, int]) -> tuple[date, date]:
    year, quarter = key
    start = date(year, 3 * quarter - 2, 1)
    end = (
        date(year, 12, 31)
        if quarter == 4
        else date(year, 3 * quarter + 1, 1) - timedelta(days=1)
    )
    return start, end


def senate_window(day: date) -> tuple[date, date]:
    if day.month >= 10:
        return date(day.year, 10, 1), date(day.year + 1, 3, 31)
    if day.month <= 3:
        return date(day.year - 1, 10, 1), date(day.year, 3, 31)
    return date(day.year, 4, 1), date(day.year, 9, 30)


def period_ordinal(chamber: str, token: str) -> int:
    if chamber == CHAMBER_HOUSE:
        key = quarter_from_token(token)
        if key is None:
            raise VerificationFailure(f"unparseable house period {token!r}")
        return key[0] * 4 + (key[1] - 1)
    start = parse_iso(token)
    if start is None:
        raise VerificationFailure(f"unparseable senate period {token!r}")
    return start.year * 2 + (0 if start.month == 4 else 1)


def period_token_from_ordinal(chamber: str, ordinal: int) -> str:
    if chamber == CHAMBER_HOUSE:
        year, remainder = divmod(ordinal, 4)
        return f"{year}Q{remainder + 1}"
    year, remainder = divmod(ordinal, 2)
    return (date(year, 4, 1) if remainder == 0 else date(year, 10, 1)).isoformat()


def period_bounds(chamber: str, token: str) -> tuple[date, date]:
    if chamber == CHAMBER_HOUSE:
        key = quarter_from_token(token)
        if key is None:
            raise VerificationFailure(f"unparseable house period {token!r}")
        return quarter_bounds(key)
    return senate_window(parse_iso(token))


def parse_amount(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = AMOUNT_CLEAN_RE.sub("", str(value))
    if not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return None


def clean_title(value: Any) -> str | None:
    if value is None:
        return None
    return re.sub(r"\s+", " ", str(value)).strip() or None


def is_shared_employee(title: str | None) -> bool:
    if not title:
        return False
    upper = title.upper()
    return any(phrase in upper for phrase in SHARED_EMPLOYEE_TITLE_PHRASES)


# ---------------------------------------------------------------------------
# Tripwire + language law
# ---------------------------------------------------------------------------
def assert_unpromoted(rows: Sequence[Mapping[str, Any]]) -> list[str]:
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


def language_law_scan(
    payload: Any, extra_verbatim_leaf_names: Iterable[str] = ()
) -> tuple[list[str], Counter]:
    verbatim_leaf_names = VERBATIM_LEAF_NAMES | frozenset(extra_verbatim_leaf_names)
    authored: list[str] = []
    verbatim: Counter = Counter()

    def walk(node: Any, key: str | None, exempt: bool) -> None:
        if isinstance(node, Mapping):
            for child_key, child in node.items():
                lowered = str(child_key).casefold()
                for token in LANGUAGE_LAW_TOKENS:
                    if token in lowered:
                        authored.append(f"field_name:{child_key}:{token}")
                walk(child, str(child_key), exempt or str(child_key) in verbatim_leaf_names)
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
# Independent re-derivation
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Name standard re-key, re-implemented here.  The name STANDARD itself is the
# one shipped module -- there is exactly one, and re-typing its rules would be
# re-typing the spec rather than checking it -- but the re-key MECHANICS below
# (which node anchors a person, what goes into the digest, how a merge group is
# collapsed, how a cause flag is decided) are written from the spec a second
# time, independently of the builder's copy.
# ---------------------------------------------------------------------------
def load_name_standard(path: Path | None) -> Any:
    """Load the ONE name standard from the path the receipt bound."""

    target = (
        Path(path)
        if path is not None
        else REPO_ROOT / "fec" / "staffer_network" / "name_standard.py"
    )
    if not target.is_file():
        raise VerificationFailure(f"name standard not found: {target}")
    spec = importlib.util.spec_from_file_location("verify_spine_name_standard", target)
    if spec is None or spec.loader is None:
        raise VerificationFailure(f"name standard not loadable: {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_spine_name_standard"] = module
    spec.loader.exec_module(module)
    return module


def node_first_period(node: Mapping[str, Any]) -> str:
    return period_token_from_ordinal(node["chamber"], min(node["ordinals"]))


def name_standard_anchor(nodes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    """The node the person id is digested over: the earliest, then chamber,
    then office key, then payee key as a total-order tiebreak."""

    return min(
        nodes,
        key=lambda node: (
            period_bounds(node["chamber"], node_first_period(node))[0].toordinal(),
            node["chamber"],
            node["office_key"],
            payee_sort_key(node["payee_key"]),
        ),
    )


def name_standard_source(chamber: str, payee_raw: str) -> str:
    """The standard's source for a payroll payee string in this chamber."""

    if chamber == CHAMBER_SENATE:
        return "senate"
    return (
        "payroll_comma"
        if "," in DATE_HINT_RE.sub(" ", ascii_fold(payee_raw))
        else "house_csv"
    )


#: Ruling A.  The four causes that exist only because the raw parse and the
#: payee-key lift read the same person differently.  Reported, never fatal.
NAME_STANDARD_KEY_SOURCE_CAUSES = (
    "v_initial",
    "particle_surname",
    "annotation_strip",
    "first_from_raw",
)

#: Ruling B.  64 ambiguous triples / 102 people, measured by the read-only
#: delta; more than that means something other than the ambiguity moved.
NAME_STANDARD_DELTA_RESIDUAL_ALLOWANCE = 102

#: Ruling C.  Weakest ground first: a merge group reports the basis a reader
#: must be told about.
NAME_STANDARD_MERGE_BASIS_ORDER = (
    "same_period_variant_no_day_dates",
    "same_period_day_level_disjoint",
    "no_same_period_office_co_occurrence",
)


def name_standard_id_tuple(
    name_key_value: str,
    nodes: Sequence[Mapping[str, Any]],
    collision_ordinal: int,
) -> dict[str, Any]:
    anchor = name_standard_anchor(nodes)
    return {
        "chamber": anchor["chamber"],
        "collision_ordinal": collision_ordinal,
        "first_office_key": anchor["office_key"],
        "first_period": node_first_period(anchor),
        "name_key": name_key_value,
    }


def name_standard_person_id(
    name_key_value: str,
    nodes: Sequence[Mapping[str, Any]],
    collision_ordinal: int = 1,
) -> str:
    return "hill:person:" + digest_of(
        name_standard_id_tuple(name_key_value, nodes, collision_ordinal)
    )


def name_standard_resolve_key(counts: Mapping[str, int]) -> str:
    """Prefer a non-empty middle initial, then most frequent, then lexical min."""

    return min(
        counts,
        key=lambda key: (key.split("|")[2] == "", -counts[key], key),
    )


def name_standard_causes(
    payee_key: tuple[str, str, str | None],
    key_after: str,
    standard: Any,
    table: Mapping[str, str],
) -> tuple[list[str], str, str]:
    """``(causes, key_before, key_lift)`` -- the seven tests, in order.

    ``key_after`` is the RAW-PARSE key the caller resolved.  The first three
    causes are functions of the triple; the last four exist only because the
    raw string carries what the triple already discarded.
    """

    last, first, middle = payee_key[0], payee_key[1], payee_key[2] or ""
    before = "%s|%s|%s" % (last, first, middle)
    lift_parts = standard.parts_from_payee_key(last, first, middle)
    fold_only = "%s|%s|%s" % (
        standard.fold_key(last),
        standard.fold_key(first),
        standard.fold_key(middle)[:1],
    )
    without_nicknames = standard.name_key(lift_parts, nicknames=False, table=table)
    lift = standard.name_key(lift_parts, nicknames=True, table=table)
    causes: list[str] = []
    if fold_only != before:
        causes.append("ascii_punct")
    if without_nicknames != fold_only:
        causes.append("suffix")
    if lift != without_nicknames:
        causes.append("nickname_class")
    after_last, after_first, after_middle = key_after.split("|")
    lift_last, lift_first, lift_middle = lift.split("|")
    if after_middle == "v" and lift_middle != "v":
        causes.append("v_initial")
    if after_last != lift_last:
        causes.append(
            "particle_surname"
            if after_last.startswith(lift_last)
            else "annotation_strip"
        )
    elif after_middle != lift_middle and not (
        after_middle == "v" and lift_middle != "v"
    ):
        causes.append("annotation_strip")
    if after_first != lift_first:
        causes.append("first_from_raw")
    if key_after != before and not causes:
        causes.append("other")
    return causes, before, lift


def name_standard_reason(causes: Sequence[str], merged: bool) -> str:
    if merged:
        return "merged"
    if not causes:
        return "unchanged"
    flags = list(causes)
    if len(flags) == 1:
        return flags[0]
    if set(flags) == {"ascii_punct", "nickname_class"}:
        return "both"
    if "suffix" in flags:
        return "suffix"
    return "+".join(flags)


def service_intervals(node: Mapping[str, Any]) -> list[tuple[date, date]] | None:
    """Every observation's inclusive printed service window, or None."""

    intervals: list[tuple[date, date]] = []
    for observation in node["observations"]:
        start = observation.get("service_start")
        end = observation.get("service_end")
        if not isinstance(start, date) or not isinstance(end, date) or start > end:
            return None
        intervals.append((start, end))
    return intervals or None


def same_office_period_relation(
    left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]
) -> str:
    """Ruling C (D-020).  See the builder's function of the same name."""

    relation = "no_same_period_office_co_occurrence"
    for left_node in left:
        for right_node in right:
            if left_node["chamber"] != right_node["chamber"]:
                continue
            if left_node["office_key"] != right_node["office_key"]:
                continue
            if not (left_node["periods"] & right_node["periods"]):
                continue
            left_intervals = service_intervals(left_node)
            right_intervals = service_intervals(right_node)
            if left_intervals is None or right_intervals is None:
                relation = "same_period_variant_no_day_dates"
                continue
            overlaps = any(
                left_start <= right_end and right_start <= left_end
                for left_start, left_end in left_intervals
                for right_start, right_end in right_intervals
            )
            if overlaps:
                return "day_level_service_overlap"
            if relation == "no_same_period_office_co_occurrence":
                relation = "same_period_day_level_disjoint"
    return relation


def union_office_nodes(
    nodes: Sequence[Mapping[str, Any]],
) -> list[tuple[dict[str, Any], list[tuple[str, str, str | None]]]]:
    """Ruling C.  See the builder's function of the same name."""

    buckets: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    order: list[tuple[str, str]] = []
    for node in nodes:
        office = (node["chamber"], node["office_key"])
        if office not in buckets:
            buckets[office] = []
            order.append(office)
        buckets[office].append(node)

    def collapse(office, run):
        payee_keys = sorted({node["payee_key"] for node in run}, key=payee_sort_key)
        if len(run) == 1:
            return dict(run[0]), payee_keys
        chamber, office_key = office
        observations = sorted(
            [item for node in run for item in node["observations"]],
            key=lambda item: (period_ordinal(chamber, item["period"]), item["row_id"]),
        )
        periods = {item["period"] for item in observations}
        return (
            {
                "chamber": chamber,
                "observations": observations,
                "office_key": office_key,
                "ordinals": {period_ordinal(chamber, period) for period in periods},
                "payee_key": payee_keys[0],
                "periods": periods,
                "shared_periods": {
                    item["period"] for item in observations if item["shared_employee"]
                },
            },
            payee_keys,
        )

    out: list[tuple[dict[str, Any], list[tuple[str, str, str | None]]]] = []
    for office in order:
        members = sorted(
            buckets[office],
            key=lambda node: (
                min(node["ordinals"]),
                max(node["ordinals"]),
                payee_sort_key(node["payee_key"]),
            ),
        )
        run: list[Mapping[str, Any]] = []
        run_end = 0
        for node in members:
            start, end = min(node["ordinals"]), max(node["ordinals"])
            if run and start <= run_end + 1:
                run.append(node)
                run_end = max(run_end, end)
                continue
            if run:
                out.append(collapse(office, run))
            run = [node]
            run_end = end
        if run:
            out.append(collapse(office, run))
    return out


class Deriver:
    """A second implementation of every Part C rule, driven by the receipt."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.receipt = receipt
        self.rule_version = receipt.get("rule_version", "")
        self.inputs = receipt.get("inputs", {})
        self.roster = load_roster(self._roster_dir())
        self.nicknames = load_nickname_table(self._path("nickname_table"))
        self.house_key = build_house_office_key(
            self._path("house_personnel_observations"), self.roster, self.nicknames
        )
        self.observations: list[dict[str, Any]] = []
        self.latest: dict[str, str | None] = {CHAMBER_HOUSE: None, CHAMBER_SENATE: None}
        self.office_profile: dict[tuple[str, str], dict[str, Any]] = {}
        self.spans: list[dict[str, Any]] = []
        self.spine: list[dict[str, Any]] = []
        self.staffers: list[dict[str, Any]] = []
        self.lda_links: list[dict[str, Any]] = []
        self.offices: list[dict[str, Any]] = []
        self.observation_to_person: dict[str, str] = {}
        self.spans_by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        # ---- name standard -----------------------------------------------
        # Read off the receipt, never off a flag: a generation that was not
        # re-keyed has no such block and every line below is dead.
        self.name_standard = isinstance(receipt.get("name_standard"), Mapping)
        self.standard: Any = None
        self.class_table: dict[str, str] = {}
        self.id_map: list[dict[str, Any]] = []
        self.rekey_by_person: dict[str, dict[str, Any]] = {}
        # (person id, chamber, office key, THE NODE'S OWN payee key), one per
        # span.  The LDA and Quorum name joins key on this rather than on the
        # spine row, which after a merge carries only one of the two spellings.
        self.node_name_index: list[
            tuple[str, str, str, tuple[str, str, str | None]]
        ] = []
        # Ruling E: a PLAIN dict.  A defaultdict answered a question about a
        # person who does not exist with an empty list and lost the join in
        # silence; a KeyError is the correct answer.
        self.legacy_payee_keys: dict[str, list[tuple[str, str, str | None]]] = {}
        self.spans_unioned = 0
        self.rekey_summary: dict[str, Any] = {}
        if self.name_standard:
            self.standard = load_name_standard(self._path("name_standard_module"))
            self.class_table, loaded = self.standard.load_class_table(
                self._path("name_standard_class_table")
            )
            if not loaded:
                raise VerificationFailure(
                    "name-standard generation: the nickname class table did not load"
                )

    # -- input access ------------------------------------------------------
    def _path(self, label: str) -> Path | None:
        entry = self.inputs.get(label)
        if not isinstance(entry, Mapping) or not entry.get("present"):
            return None
        return Path(entry["path"])

    def _paths(self, label: str) -> list[Path]:
        """Return a singular bound input or every repeatable numbered binding."""
        exact = self._path(label)
        if exact is not None:
            return [exact]
        out: list[Path] = []
        prefix = f"{label}_"
        for key, entry in sorted(self.inputs.items()):
            if (
                key.startswith(prefix)
                and isinstance(entry, Mapping)
                and entry.get("present")
            ):
                out.append(Path(entry["path"]))
        return out

    def _roster_dir(self) -> Path | None:
        path = self._path("roster:legislators-current.yaml")
        if path is None:
            path = self._path("roster:legislators-historical.yaml")
        return path.parent if path is not None else None

    # -- observations ------------------------------------------------------
    def load_observations(self) -> None:
        # The House has exactly one lane.  The ledger carries both eras, so
        # there is nothing to deduplicate against and no second file to read.
        # ``verify`` asserts separately that the receipt bound no PDF-era
        # candidate file, which is the condition that would make this loop
        # under-read while the generation over-counted.
        ledger = self._path("house_personnel_observations")
        if ledger is not None:
            for ordinal, row in enumerate(read_rows(ledger)):
                observation = self._house_row(row, LANE_HOUSE_LEDGER, ordinal)
                if observation is not None:
                    self.observations.append(observation)
        senate_ordinal = 0
        for senate in self._paths("senate_payroll_candidates"):
            for row in read_rows(senate):
                ordinal = senate_ordinal
                senate_ordinal += 1
                observation = self._senate_row(row, ordinal)
                if observation is not None:
                    self.observations.append(observation)
        for chamber in (CHAMBER_HOUSE, CHAMBER_SENATE):
            ordinals = [
                period_ordinal(chamber, item["period"])
                for item in self.observations
                if item["chamber"] == chamber
            ]
            if ordinals:
                self.latest[chamber] = period_token_from_ordinal(chamber, max(ordinals))

    def _house_row(
        self, row: Mapping[str, Any], lane: str, ordinal: int
    ) -> dict[str, Any] | None:
        office_raw = str(row.get("office_raw") or row.get("employing_office_raw") or "").strip()
        payee_raw = str(row.get("payee_raw") or row.get("payee_name_raw") or "").strip()
        if not office_raw or not payee_raw:
            return None
        token = row.get("quarter") or row.get("period")
        key = quarter_from_token(token if isinstance(token, str) else None)
        if key is None:
            anchor = (
                parse_iso(row.get("period_start"))
                or parse_iso(row.get("service_start"))
                or parse_iso(row.get("service_start_date_candidate_iso"))
            )
            if anchor is None:
                return None
            key = (anchor.year, (anchor.month - 1) // 3 + 1)
        payee_key = payroll_payee_key(payee_raw)
        if payee_key is None:
            return None
        source_file = row.get("source_file")
        row_index = row.get("source_row_index")
        if isinstance(source_file, str) and source_file and row_index is not None:
            row_id = f"house-ledger:{source_file}#{row_index}"
        else:
            row_id = next(
                (
                    str(row[field])
                    for field in ("observation_id", "candidate_id", "row_id")
                    if isinstance(row.get(field), str) and row.get(field)
                ),
                f"house-ledger:ordinal:{ordinal}",
            )
        locator = row.get("source_locator")
        source_candidate_id = None
        if isinstance(locator, Mapping):
            value = locator.get("candidate_id")
            if isinstance(value, str) and value:
                source_candidate_id = value
        title = clean_title(row.get("title_raw") or row.get("title_description_raw"))
        return {
            "amount": parse_amount(row.get("amount") or row.get("amount_raw")),
            "chamber": CHAMBER_HOUSE,
            "container_kind": container_kind_house(office_raw),
            "lane": lane,
            "ledger_container_kind": (
                row.get("container_kind")
                if isinstance(row.get("container_kind"), str)
                else None
            ),
            "ledger_member_bioguide": (
                row.get("member_bioguide")
                if isinstance(row.get("member_bioguide"), str)
                else None
            ),
            "ledger_office_key": (
                row.get("office_key") if isinstance(row.get("office_key"), str) else None
            ),
            "office_key": self.house_key(office_raw),
            "office_raw": office_raw,
            "payee_key": payee_key,
            # Retained for the name-standard re-key, which reads the RAW payee
            # string through the standard.  Nothing is emitted from it.
            "payee_raw": payee_raw,
            "period": f"{key[0]}Q{key[1]}",
            "row_id": row_id,
            "shared_employee": is_shared_employee(title),
            "source_candidate_id": source_candidate_id,
            "source_form": (
                row.get("source_form")
                if isinstance(row.get("source_form"), str)
                else None
            ),
            "service_start": (
                parse_iso(row.get("service_start"))
                or parse_iso(row.get("service_start_date_candidate_iso"))
            ),
            "service_end": (
                parse_iso(row.get("service_end"))
                or parse_iso(row.get("service_end_date_candidate_iso"))
            ),
            "title": title,
        }

    def _senate_row(self, row: Mapping[str, Any], ordinal: int) -> dict[str, Any] | None:
        office_raw = str(row.get("office_raw") or "").strip()
        payee_raw = str(row.get("payee_name_raw") or row.get("payee_raw") or "").strip()
        if not office_raw or not payee_raw:
            return None
        anchor = parse_iso(row.get("report_period_start"))
        if anchor is None:
            for interval in row.get("date_intervals") or []:
                if isinstance(interval, Mapping):
                    anchor = parse_iso(interval.get("start"))
                    if anchor is not None:
                        break
        if anchor is None:
            return None
        payee_key = payroll_payee_key(payee_raw)
        if payee_key is None:
            return None
        candidate = row.get("candidate_id")
        title = clean_title(row.get("title_raw") or row.get("title_candidate"))
        return {
            "amount": parse_amount(row.get("amount_paid_raw") or row.get("amount")),
            "chamber": CHAMBER_SENATE,
            "container_kind": container_kind_senate(office_raw),
            "lane": LANE_SENATE,
            "ledger_container_kind": None,
            "ledger_member_bioguide": None,
            "ledger_office_key": None,
            "office_key": senate_office_key(office_raw),
            "office_raw": office_raw,
            "payee_key": payee_key,
            # Retained for the name-standard re-key; nothing is emitted from it.
            "payee_raw": payee_raw,
            "period": senate_window(anchor)[0].isoformat(),
            "row_id": (
                candidate
                if isinstance(candidate, str) and candidate
                else f"senate-payroll:ordinal:{ordinal}"
            ),
            "shared_employee": is_shared_employee(title),
            "title": title,
        }

    # -- offices -----------------------------------------------------------
    def build_office_profiles(self) -> None:
        grouped: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in self.observations:
            grouped[(item["chamber"], item["office_key"])].append(item)
        for (chamber, office_key), items in sorted(grouped.items()):
            raws = sorted({item["office_raw"] for item in items})
            counts = Counter(item["container_kind"] for item in items)
            container_kind = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]
            ordinals = [period_ordinal(chamber, item["period"]) for item in items]
            low = period_bounds(
                chamber, period_token_from_ordinal(chamber, min(ordinals))
            )[0].year
            high = period_bounds(
                chamber, period_token_from_ordinal(chamber, max(ordinals))
            )[1].year
            if container_kind == "member_office":
                # A member office key that names a bioguide takes its member
                # from the House ledger's own strict per-office resolution
                # rather than re-deriving one under a different rule.  The
                # method recorded says so -- LEDGER_SUPPLIED_STRICT_RESOLUTION
                # -- so a borrowed resolution and one derived here from the
                # roster are counted apart.
                ledger_bioguide = (
                    self.house_key.bioguide_by_key.get(office_key)
                    if chamber == CHAMBER_HOUSE
                    else None
                )
                if ledger_bioguide is not None:
                    bioguide = ledger_bioguide
                    method = "LEDGER_SUPPLIED_STRICT_RESOLUTION"
                else:
                    first = surname = None
                    for raw in raws:
                        first, surname = office_member_name(chamber, raw)
                        if surname:
                            break
                    bioguide, method = resolve_member_bioguide(
                        first, surname, self.roster, self.nicknames, (low, high)
                    )
            else:
                bioguide, method = None, "NOT_A_MEMBER_OFFICE"
            self.office_profile[(chamber, office_key)] = {
                "bioguide": bioguide,
                "container_kind": container_kind,
                "method": method,
                "office_raws": raws,
            }

    # -- identity ----------------------------------------------------------
    def build_people(self) -> None:
        nodes: defaultdict[
            tuple[str, tuple[str, str, str | None]], list[dict[str, Any]]
        ] = defaultdict(list)
        grouped: defaultdict[tuple[str, str, Any], list[dict[str, Any]]] = defaultdict(list)
        for item in self.observations:
            grouped[(item["chamber"], item["office_key"], item["payee_key"])].append(item)
        for (chamber, office_key, payee_key), items in sorted(
            grouped.items(),
            key=lambda pair: (pair[0][0], pair[0][1], payee_sort_key(pair[0][2])),
        ):
            periods = {item["period"] for item in items}
            node = {
                "chamber": chamber,
                "observations": sorted(
                    items,
                    key=lambda item: (
                        period_ordinal(chamber, item["period"]),
                        item["row_id"],
                    ),
                ),
                "office_key": office_key,
                "ordinals": {period_ordinal(chamber, period) for period in periods},
                "payee_key": payee_key,
                "periods": periods,
                "shared_periods": {
                    item["period"] for item in items if item["shared_employee"]
                },
            }
            nodes[(chamber, payee_key)].append(node)

        clusters_by_payee: defaultdict[Any, dict[str, list[list[dict[str, Any]]]]] = (
            defaultdict(dict)
        )
        for (chamber, payee_key), node_list in sorted(
            nodes.items(), key=lambda pair: (pair[0][0], payee_sort_key(pair[0][1]))
        ):
            clusters_by_payee[payee_key][chamber] = self._cluster(node_list)

        people: list[dict[str, Any]] = []
        for payee_key in sorted(clusters_by_payee, key=payee_sort_key):
            by_chamber = clusters_by_payee[payee_key]
            house = by_chamber.get(CHAMBER_HOUSE, [])
            senate = by_chamber.get(CHAMBER_SENATE, [])
            merged = False
            if len(house) == 1 and len(senate) == 1:
                if not (
                    CROSS_CHAMBER_REQUIRES_DISJOINT_PERIODS
                    and self._clusters_overlap(house[0], senate[0])
                ):
                    merged = True
                    people.append({"nodes": house[0] + senate[0], "payee_key": payee_key})
            if not merged:
                for chamber in (CHAMBER_HOUSE, CHAMBER_SENATE):
                    for cluster in by_chamber.get(chamber, []):
                        people.append({"nodes": list(cluster), "payee_key": payee_key})

        if self.name_standard:
            people = self._rekey(people)
        for person in people:
            self._emit_person(person)

    # -- name standard -----------------------------------------------------
    def _rekey(self, people: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Re-key the finished person population and collapse the merge groups.

        Reads the office nodes the identity rules produced and writes nothing
        back into them, so the span population that follows is the one those
        rules produced.
        """

        standard = self.standard
        table = self.class_table
        cache: dict[tuple[str, str], Any] = {}

        def parsed(chamber: str, raw: str) -> Any:
            source = name_standard_source(chamber, raw)
            found = cache.get((source, raw))
            if found is None:
                found = standard.parse_name(raw, source)
                cache[(source, raw)] = found
            return found

        def key_of(chamber: str, raw: str) -> str:
            return standard.name_key(parsed(chamber, raw), table=table)

        def raw_key_counts(nodes):
            keys: Counter = Counter()
            raws: Counter = Counter()
            for node in nodes:
                for item in node["observations"]:
                    keys[key_of(node["chamber"], item["payee_raw"])] += 1
                    raws[(node["chamber"], item["payee_raw"])] += 1
            return keys, raws

        def choose_raw(raws, key_after):
            matching = [pair for pair in raws if key_of(pair[0], pair[1]) == key_after]
            if not matching:
                return None
            return min(matching, key=lambda pair: (-raws[pair], pair[1], pair[0]))

        # ---- pass 1: the delta's own per-TRIPLE reconstruction -------------
        triple_keys: dict[tuple[str, str, str | None], Counter] = {}
        for person in people:
            bucket = triple_keys.setdefault(person["payee_key"], Counter())
            for node in person["nodes"]:
                for item in node["observations"]:
                    bucket[key_of(node["chamber"], item["payee_raw"])] += 1
        triple_resolved = {
            triple: name_standard_resolve_key(counts)
            for triple, counts in triple_keys.items()
        }
        del triple_keys

        cause_counts: Counter = Counter()
        delta_cause_counts: Counter = Counter()
        key_source_disagreements: Counter = Counter()
        key_source_disagreement_people = 0
        delta_residuals = 0
        empty_first_class = 0
        chosen_raw_fell_back = 0
        records: list[dict[str, Any]] = []
        for person in people:
            payee_key = person["payee_key"]
            nodes = person["nodes"]
            legacy = "hill:person:" + digest_of(
                {
                    "chamber": name_standard_anchor(nodes)["chamber"],
                    "first_office_key": name_standard_anchor(nodes)["office_key"],
                    "first_period": node_first_period(name_standard_anchor(nodes)),
                    "payee_key": [payee_key[0], payee_key[1], payee_key[2]],
                }
            )
            keys, _raws = raw_key_counts(nodes)
            after = name_standard_resolve_key(keys)
            causes, before, lift_key = name_standard_causes(
                payee_key, after, standard, table
            )
            for cause in causes:
                cause_counts[cause] += 1
            delta_key = triple_resolved[payee_key]
            for cause in name_standard_causes(payee_key, delta_key, standard, table)[0]:
                delta_cause_counts[cause] += 1
            if delta_key != after:
                delta_residuals += 1
            if after != lift_key:
                key_source_disagreement_people += 1
                named = [
                    cause
                    for cause in causes
                    if cause in NAME_STANDARD_KEY_SOURCE_CAUSES
                ]
                for cause in named or ["other"]:
                    key_source_disagreements[cause] += 1
            records.append(
                {
                    "causes": causes,
                    "key_after": after,
                    "key_before": before,
                    "legacy_person_id": legacy,
                    "person": person,
                }
            )
        del triple_resolved

        # ---- ruling C: bucket on the tuple, then split on the day guard ----
        buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
        bucket_order: list[tuple[str, str, str, str]] = []
        for record in records:
            anchor = name_standard_anchor(record["person"]["nodes"])
            bucket = (
                anchor["chamber"],
                anchor["office_key"],
                node_first_period(anchor),
                record["key_after"],
            )
            if bucket not in buckets:
                buckets[bucket] = []
                bucket_order.append(bucket)
            buckets[bucket].append(record)

        grouped: dict[str, list[dict[str, Any]]] = {}
        order: list[str] = []
        blocked_pairs = 0
        merge_basis_by_id: dict[str, str] = {}
        for bucket in bucket_order:
            members = sorted(buckets[bucket], key=lambda item: item["legacy_person_id"])
            subgroups: list[list[dict[str, Any]]] = []
            bases: list[list[str]] = []
            for member in members:
                placed = False
                for index, subgroup in enumerate(subgroups):
                    relations = [
                        same_office_period_relation(
                            sibling["person"]["nodes"], member["person"]["nodes"]
                        )
                        for sibling in subgroup
                    ]
                    if any(relation in {"day_level_service_overlap", "same_period_variant_no_day_dates"} for relation in relations):
                        blocked_pairs += sum(
                            1
                            for relation in relations
                            if relation in {"day_level_service_overlap", "same_period_variant_no_day_dates"}
                        )
                        continue
                    subgroups[index].append(member)
                    bases[index].extend(relations)
                    placed = True
                    break
                if not placed:
                    subgroups.append([member])
                    bases.append([])
            for ordinal, (subgroup, relations) in enumerate(
                zip(subgroups, bases), start=1
            ):
                person_id = name_standard_person_id(
                    bucket[3], subgroup[0]["person"]["nodes"], ordinal
                )
                grouped[person_id] = subgroup
                order.append(person_id)
                for record in subgroup:
                    record["person_id"] = person_id
                    record["collision_ordinal"] = ordinal
                if len(subgroup) > 1:
                    merge_basis_by_id[person_id] = min(
                        relations,
                        key=lambda relation: NAME_STANDARD_MERGE_BASIS_ORDER.index(
                            relation
                        ),
                    )

        merged_people: list[dict[str, Any]] = []
        for person_id in order:
            members = sorted(grouped[person_id], key=lambda item: item["legacy_person_id"])
            ordinal = members[0]["collision_ordinal"]
            nodes: list[dict[str, Any]] = []
            for member in members:
                nodes.extend(member["person"]["nodes"])
            nodes.sort(
                key=lambda node: (
                    min(node["ordinals"]),
                    max(node["ordinals"]),
                    node["office_key"],
                    payee_sort_key(node["payee_key"]),
                )
            )
            payee_keys = sorted(
                {member["person"]["payee_key"] for member in members},
                key=payee_sort_key,
            )
            key_after = members[0]["key_after"]
            _keys, raws = raw_key_counts(nodes)
            chosen = choose_raw(raws, key_after)
            if chosen is None:
                chosen_raw_fell_back += 1
                anchor = name_standard_anchor(nodes)
                chosen = (anchor["chamber"], anchor["observations"][0]["payee_raw"])
            parts = parsed(chosen[0], chosen[1])
            raw_pairs = sorted(raws)
            suffixes = sorted(
                {
                    parsed(chamber, value).suffix
                    for chamber, value in raw_pairs
                    if parsed(chamber, value).suffix
                }
            )
            suffix = suffixes[0] if len(suffixes) == 1 else None
            render = standard.NameParts(
                first=parts.first,
                middle=parts.middle,
                last=parts.last,
                suffix=suffix or "",
                nickname_raw=parts.nickname_raw,
                format_detected=parts.format_detected,
                raw=parts.raw,
            )
            lift = standard.parts_from_payee_key(
                payee_keys[0][0], payee_keys[0][1], payee_keys[0][2] or ""
            )
            first_class = standard.canonical_first(lift.first, table)
            if not first_class:
                empty_first_class += 1
            raw_examples = sorted({value for _chamber, value in raw_pairs})
            self.rekey_by_person[person_id] = {
                "collision_ordinal": ordinal,
                "display_name": standard.display_name(render),
                "legacy_person_id": members[0]["legacy_person_id"],
                "legacy_person_ids": [
                    member["legacy_person_id"] for member in members
                ],
                "name_key": key_after,
                "name_standard_parts": {
                    "first": render.first,
                    "format_detected": render.format_detected,
                    "last": render.last,
                    "middle": render.middle,
                    "nickname_raw": render.nickname_raw,
                    "suffix": render.suffix,
                },
                "payee_key": {
                    "first": lift.first,
                    "first_class": first_class,
                    "last": lift.last,
                    "middle_initial": payee_keys[0][2],
                    "suffix": suffix,
                },
                "payee_key_legacy_variants": [
                    {"first": item[1], "last": item[0], "middle_initial": item[2]}
                    for item in payee_keys
                ],
                "payee_raw": chosen[1],
                "payee_raw_examples": raw_examples[:NAME_STANDARD_MAX_RAW_EXAMPLES],
                "payee_raw_variant_count": len(raw_examples),
                "suffix_observed": suffixes,
            }
            merged_people.append(
                {
                    "nodes": nodes,
                    "payee_key": payee_keys[0],
                    "spine_person_id_override": person_id,
                }
            )

        self.rekey_summary = {
            "cause_counts": dict(sorted(cause_counts.items())),
            "chosen_raw_fell_back_to_the_anchor": chosen_raw_fell_back,
            "delta_reconstruction_cause_counts": dict(
                sorted(delta_cause_counts.items())
            ),
            "delta_residuals_count": delta_residuals,
            "empty_first_class_count": empty_first_class,
            "key_source_disagreement_people": key_source_disagreement_people,
            "key_source_disagreements": dict(sorted(key_source_disagreements.items())),
            "merges_blocked_pairs": blocked_pairs,
            "spine_persons_before": len(records),
        }

        for record in records:
            siblings = [
                member["legacy_person_id"]
                for member in sorted(
                    grouped[record["person_id"]],
                    key=lambda item: item["legacy_person_id"],
                )
                if member["legacy_person_id"] != record["legacy_person_id"]
            ]
            self.id_map.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "collision_ordinal": record["collision_ordinal"],
                    "merge_basis": merge_basis_by_id.get(record["person_id"]),
                    "causes": record["causes"],
                    "key_v6": record["key_before"],
                    "key_v7": record["key_after"],
                    "legacy_person_id": record["legacy_person_id"],
                    "merged_with": siblings,
                    "person_id": record["person_id"],
                    "reason": name_standard_reason(record["causes"], bool(siblings)),
                    "review_status": "REVIEW_REQUIRED",
                    "schema_id": "staffer-network-hill-person-spine-id-map-v1",
                }
            )
        self.id_map.sort(key=lambda row: row["legacy_person_id"])
        return merged_people

    @staticmethod
    def _linkable(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
        shared = left["periods"] & right["periods"]
        if not shared:
            return True
        if left["chamber"] == CHAMBER_HOUSE and right["chamber"] == CHAMBER_HOUSE:
            def exact_intervals(node: Mapping[str, Any]) -> list[tuple[date, date]] | None:
                intervals: list[tuple[date, date]] = []
                for observation in node["observations"]:
                    start = observation.get("service_start")
                    end = observation.get("service_end")
                    if not isinstance(start, date) or not isinstance(end, date) or start > end:
                        return None
                    intervals.append((start, end))
                return intervals if intervals else None

            left_intervals = exact_intervals(left)
            right_intervals = exact_intervals(right)
            if left_intervals is not None and right_intervals is not None:
                overlaps = any(
                    left_start <= right_end and right_start <= left_end
                    for left_start, left_end in left_intervals
                    for right_start, right_end in right_intervals
                )
                if not overlaps:
                    return True
        return all(
            period in left["shared_periods"] or period in right["shared_periods"]
            for period in shared
        )

    def _cluster(self, node_list: Sequence[Mapping[str, Any]]):
        ordered = sorted(
            node_list,
            key=lambda node: (min(node["ordinals"]), max(node["ordinals"]), node["office_key"]),
        )
        clusters: list[list[dict[str, Any]]] = []
        for node in ordered:
            for cluster in clusters:
                if all(self._linkable(member, node) for member in cluster):
                    cluster.append(dict(node))
                    break
            else:
                clusters.append([dict(node)])
        return clusters

    @staticmethod
    def _clusters_overlap(
        left: Sequence[Mapping[str, Any]], right: Sequence[Mapping[str, Any]]
    ) -> bool:
        def bounds(cluster):
            return [
                period_bounds(node["chamber"], period)
                for node in cluster
                for period in sorted(node["periods"])
            ]

        for left_start, left_end in bounds(left):
            for right_start, right_end in bounds(right):
                if left_start <= right_end and right_start <= left_end:
                    return True
        return False

    def _emit_person(self, person: Mapping[str, Any]) -> None:
        nodes = person["nodes"]
        payee_key = person["payee_key"]
        anchor = min(
            nodes,
            key=lambda node: (
                period_bounds(
                    node["chamber"],
                    period_token_from_ordinal(node["chamber"], min(node["ordinals"])),
                )[0].toordinal(),
                node["chamber"],
                node["office_key"],
            ),
        )
        person_id = person.get("spine_person_id_override") or (
            "hill:person:"
            + digest_of(
                {
                    "chamber": anchor["chamber"],
                    "first_office_key": anchor["office_key"],
                    "first_period": period_token_from_ordinal(
                        anchor["chamber"], min(anchor["ordinals"])
                    ),
                    "payee_key": [payee_key[0], payee_key[1], payee_key[2]],
                }
            )
        )
        self.legacy_payee_keys.setdefault(person_id, [])
        # Ruling C: the union of a merged person's same-office, overlapping or
        # abutting nodes.  Outside a merge this is the identity function.
        emitted = union_office_nodes(nodes)
        self.spans_unioned += len(nodes) - len(emitted)
        link_methods = {"SPINE_OFFICE_S1"}
        if len(emitted) > 1:
            link_methods.add("SPINE_CROSS_OFFICE_S2")
            if any(node["shared_periods"] for node, _keys in emitted):
                link_methods.add("SPINE_CROSS_OFFICE_SHARED_EMPLOYEE")
        chambers = sorted({node["chamber"] for node in nodes})
        if len(chambers) > 1:
            link_methods.add("SPINE_CROSS_CHAMBER_S3")
            identity_tier = "S3"
        elif len(emitted) > 1:
            identity_tier = "S2"
        else:
            identity_tier = "S1"

        bioguides: set[str] = set()
        entries = []
        for node, node_payee_keys in emitted:
            span = self._span_row(node, person_id)
            self.spans.append(span)
            self.spans_by_person[person_id].append(span)
            for node_payee_key in node_payee_keys:
                self.node_name_index.append(
                    (person_id, node["chamber"], node["office_key"], node_payee_key)
                )
                if node_payee_key not in self.legacy_payee_keys[person_id]:
                    self.legacy_payee_keys[person_id].append(node_payee_key)
            if span["member_bioguide"]:
                bioguides.add(span["member_bioguide"])
            for item in node["observations"]:
                self.observation_to_person[item["row_id"]] = person_id
            entries.append(
                (
                    period_bounds(span["chamber"], span["first_period"])[0],
                    period_bounds(span["chamber"], span["last_period"])[1],
                    span["chamber"],
                    span["first_period"],
                    span["last_period"],
                )
            )
        first_entry = min(entries, key=lambda item: (item[0], item[2], item[3]))
        last_entry = max(entries, key=lambda item: (item[1], item[2], item[4]))
        self.spine.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "chambers": chambers,
                "first_period": first_entry[3],
                "identity_tier": identity_tier,
                "last_period": last_entry[4],
                "lda_source_person_id": None,
                "lda_tier": None,
                "link_methods": sorted(link_methods),
                "member_bioguides": sorted(bioguides),
                "office_count": len(
                    {(node["chamber"], node["office_key"]) for node in nodes}
                ),
                "payee_key": {
                    "first": payee_key[1],
                    "last": payee_key[0],
                    "middle_initial": payee_key[2],
                },
                "quorum_staff_id": None,
                "review_status": "REVIEW_REQUIRED",
                "rule_version": self.rule_version,
                "schema_id": "staffer-network-hill-person-spine-v1",
                "span_count": len(emitted),
                "spine_person_id": person_id,
            }
        )
        if self.name_standard:
            entry = self.rekey_by_person[person_id]
            row = self.spine[-1]
            row["collision_ordinal"] = entry["collision_ordinal"]
            row["display_name"] = entry["display_name"]
            row["legacy_person_id"] = entry["legacy_person_id"]
            row["legacy_person_ids"] = list(entry["legacy_person_ids"])
            row["name_key"] = entry["name_key"]
            row["name_standard_parts"] = dict(entry["name_standard_parts"])
            row["payee_key"] = dict(entry["payee_key"])
            row["payee_key_legacy_variants"] = [
                dict(item) for item in entry["payee_key_legacy_variants"]
            ]
            row["payee_raw"] = entry["payee_raw"]
            row["payee_raw_examples"] = list(entry["payee_raw_examples"])
            row["payee_raw_variant_count"] = entry["payee_raw_variant_count"]
            row["suffix_observed"] = list(entry["suffix_observed"])

    def _span_row(self, node: Mapping[str, Any], person_id: str) -> dict[str, Any]:
        chamber = node["chamber"]
        ordinals = sorted(node["ordinals"])
        first_token = period_token_from_ordinal(chamber, ordinals[0])
        last_token = period_token_from_ordinal(chamber, ordinals[-1])
        core_start = period_bounds(chamber, first_token)[0]
        core_end = period_bounds(chamber, last_token)[1]
        envelope_start = period_bounds(
            chamber,
            period_token_from_ordinal(
                chamber, ordinals[0] - ENVELOPE_WIDENING_REPORTING_PERIODS
            ),
        )[0]
        envelope_end = period_bounds(
            chamber,
            period_token_from_ordinal(
                chamber, ordinals[-1] + ENVELOPE_WIDENING_REPORTING_PERIODS
            ),
        )[1]
        date_precision = "REPORT_PERIOD"
        if chamber == CHAMBER_HOUSE:
            exact = [
                (item.get("service_start"), item.get("service_end"))
                for item in node["observations"]
            ]
            if exact and all(
                isinstance(start, date) and isinstance(end, date) and start <= end
                for start, end in exact
            ):
                core_start = min(start for start, _end in exact)
                core_end = max(end for _start, end in exact)
                envelope_start = core_start
                envelope_end = core_end
                date_precision = "DAY"
        # 2026-09-07.  Re-derived here the same way the emitted row derives it
        # and, like every other rule in this file, WITHOUT importing the
        # builder: walk the sorted ordinals and cut a new run wherever the step
        # is not one.  The three fields go through the byte-level re-derivation
        # comparison with the rest of the row; the statements ABOUT them --
        # that the runs cover exactly the observed periods, that there is at
        # least one, and that they sit inside [first_period, last_period] --
        # are asserted separately against the EMITTED rows, so a row that
        # agreed with a wrong re-derivation would still be caught.
        observed_periods = [
            period_token_from_ordinal(chamber, ordinal) for ordinal in ordinals
        ]
        contiguous_runs: list[list[str]] = []
        run_start = previous = ordinals[0]
        for ordinal in ordinals[1:]:
            if ordinal == previous + 1:
                previous = ordinal
                continue
            contiguous_runs.append(
                [
                    period_token_from_ordinal(chamber, run_start),
                    period_token_from_ordinal(chamber, previous),
                ]
            )
            run_start = previous = ordinal
        contiguous_runs.append(
            [
                period_token_from_ordinal(chamber, run_start),
                period_token_from_ordinal(chamber, previous),
            ]
        )
        observations = node["observations"]
        raws = sorted({item["office_raw"] for item in observations})
        titles = sorted({item["title"] for item in observations if item["title"]})
        amounts = [item["amount"] for item in observations if item["amount"] is not None]
        amount_sum = round(sum(amounts), 2) if amounts else None
        observed_days = sum(
            (period_bounds(chamber, token)[1] - period_bounds(chamber, token)[0]).days + 1
            for token in sorted(node["periods"])
        )
        profile = self.office_profile[(chamber, node["office_key"])]
        return {
            "amount_sum": amount_sum,
            "annualized_estimate": (
                round(amount_sum / observed_days * ANNUALIZATION_DAYS, 2)
                if amount_sum is not None and observed_days > 0
                else None
            ),
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
            "chamber": chamber,
            "contiguous": all(
                ordinals[index + 1] - ordinals[index] == 1
                for index in range(len(ordinals) - 1)
            ),
            "contiguous_runs": contiguous_runs,
            "container_kind": profile["container_kind"],
            "core": {
                "end_earliest": core_end.isoformat(),
                "start_latest": core_start.isoformat(),
            },
            "envelope": {
                "end_latest": envelope_end.isoformat(),
                "start_earliest": envelope_start.isoformat(),
            },
            "date_precision": date_precision,
            "first_period": first_token,
            "last_period": last_token,
            "member_bioguide": profile["bioguide"],
            "member_resolution_method": profile["method"],
            "observation_count": len(observations),
            "observed_period_count": len(observed_periods),
            "observed_periods": observed_periods,
            "office_key": node["office_key"],
            "office_raw_examples": raws[:MAX_OFFICE_RAW_EXAMPLES],
            "period_kind": PERIOD_KIND[chamber],
            "periods_observed": len(node["periods"]),
            "review_status": "REVIEW_REQUIRED",
            "rule_version": self.rule_version,
            "schema_id": "staffer-network-hill-person-office-span-v1",
            "shared_employee": bool(node["shared_periods"]),
            "source_lane": sorted({item["lane"] for item in observations}),
            "source_row_ids": sorted({item["row_id"] for item in observations}),
            "spine_person_id": person_id,
            "status": (
                "current" if last_token == self.latest.get(chamber) else "departed"
            ),
            "title_first": next(
                (item["title"] for item in observations if item["title"]), None
            ),
            "title_last": next(
                (item["title"] for item in reversed(observations) if item["title"]), None
            ),
            "titles": titles,
        }

    # -- links -------------------------------------------------------------
    def build_links(self) -> None:
        spine_by_id = {row["spine_person_id"]: row for row in self.spine}
        part_a = {}
        sidecar = self._path("part_a_v2:tiered_person_summary_25340.ndjson.gz")
        if sidecar is not None:
            for row in read_rows(sidecar):
                if isinstance(row.get("lda_source_person_id"), str) and isinstance(
                    row.get("max_tier"), str
                ):
                    part_a[row["lda_source_person_id"]] = row["max_tier"]

        # H1 keys on the PDF-era candidate file's own candidate_id.  The ledger
        # carries it through in source_locator.candidate_id, so the join
        # survives the removal of the separate PDF lane unchanged.
        by_candidate = {
            item["source_candidate_id"]: self.observation_to_person[item["row_id"]]
            for item in self.observations
            if item.get("source_candidate_id")
        }
        by_name_office: defaultdict[
            tuple[str, str, str, str], set[tuple[str, str | None]]
        ] = defaultdict(set)
        for person_id, chamber, office_key, node_payee_key in self.node_name_index:
            by_name_office[
                (chamber, office_key, node_payee_key[0], node_payee_key[1])
            ].add((person_id, node_payee_key[2]))

        lda_by_spine: defaultdict[str, set[str]] = defaultdict(set)
        for lane, label, key_field, method, chamber in (
            ("h1_house_sod_pdf", "h1_matches", "payroll_candidate_id", "LDA_PAYROLL_KEY_H1", CHAMBER_HOUSE),
            ("h2_house_payroll", "h2_matches", "payroll_support_digest", "LDA_PAYROLL_KEY_H2", CHAMBER_HOUSE),
            ("senate_payroll", "senate_matches", "payroll_support_digest", "LDA_PAYROLL_KEY_SENATE", CHAMBER_SENATE),
        ):
            path = self._path(label)
            if path is None:
                continue
            resolved: defaultdict[tuple[str, str | None], list[str]] = defaultdict(list)
            resolution: dict[tuple[str, str | None], str] = {}
            counts: dict[tuple[str, str | None], int] = {}
            for row in read_rows(path):
                person = row.get("lda_source_person_id")
                key = row.get(key_field)
                if not isinstance(person, str) or not isinstance(key, str) or not key:
                    continue
                if lane == "h1_house_sod_pdf":
                    target = by_candidate.get(key)
                    found = {target} if target else set()
                else:
                    found = self._resolve_by_name_and_office(
                        chamber,
                        row.get("display_name") or row.get("lda_display_name") or "",
                        row.get("payroll_payee_raw") or "",
                        row.get("employing_office_candidate")
                        or row.get("employing_office_raw")
                        or "",
                        by_name_office,
                    )
                if len(found) == 1:
                    bucket = (person, next(iter(found)))
                    resolution[bucket] = "MATCHED_UNIQUE"
                else:
                    bucket = (person, None)
                    resolution[bucket] = "KEY_AMBIGUOUS" if found else "KEY_ABSENT"
                resolved[bucket].append(key)
                counts[bucket] = max(counts.get(bucket, 0), len(found))
            for (person, spine_id), keys in sorted(
                resolved.items(), key=lambda item: (item[0][0], item[0][1] or "")
            ):
                linked = spine_id is not None
                if linked:
                    lda_by_spine[spine_id].add(person)
                    spine_by_id[spine_id]["link_methods"] = sorted(
                        set(spine_by_id[spine_id]["link_methods"]) | {method}
                    )
                self.lda_links.append(
                    {
                        "canonical_eligible": False,
                        "canonical_employment_promoted": False,
                        "candidate_count": counts[(person, spine_id)],
                        "key_resolution": resolution[(person, spine_id)],
                        "lane": lane,
                        "lda_source_person_id": person,
                        "link_status": (
                            "LINKED_BY_PAYROLL_KEY" if linked else "KEY_NOT_FOUND"
                        ),
                        "part_a_tier": part_a.get(person),
                        "payroll_key": min(keys),
                        "payroll_key_count": len(set(keys)),
                        "payroll_key_field": key_field,
                        "review_status": "REVIEW_REQUIRED",
                        "rule_version": self.rule_version,
                        "schema_id": "staffer-network-lda-spine-link-v1",
                        "spine_person_id": spine_id,
                    }
                )
        for spine_id, people in lda_by_spine.items():
            row = spine_by_id[spine_id]
            if len(people) == 1:
                person = next(iter(people))
                row["lda_source_person_id"] = person
                row["lda_tier"] = part_a.get(person)
            else:
                row["link_methods"] = sorted(
                    set(row["link_methods"]) | {"LDA_PAYROLL_KEY_AMBIGUOUS"}
                )

        self._build_staffers(spine_by_id)

    def _resolve_by_name_and_office(
        self,
        chamber: str,
        display_name: str,
        payee_raw: str,
        office: str,
        by_name_office: Mapping[tuple[str, str, str, str], set[tuple[str, str | None]]],
    ) -> set[str]:
        key = payroll_payee_key(payee_raw) if payee_raw else None
        if key is None:
            key = display_payee_key(display_name)
        if key is None or not office:
            return set()
        office_key = (
            self.house_key(office)
            if chamber == CHAMBER_HOUSE
            else senate_office_key(office)
        )
        bucket = by_name_office.get((chamber, office_key, key[0], key[1]), set())
        return {
            spine_id
            for spine_id, middle in bucket
            if middle_compatible(middle, key[2])
        }

    def _build_staffers(self, spine_by_id: Mapping[str, dict[str, Any]]) -> None:
        directory = self._path("staff_directory")
        entries: list[dict[str, Any]] = []
        if directory is not None:
            payload = load_json(directory)
            for member_display in sorted(payload):
                for entry in payload.get(member_display) or []:
                    if not isinstance(entry, Mapping):
                        continue
                    staff_id = entry.get("id")
                    name = entry.get("n")
                    if (
                        not isinstance(staff_id, str)
                        or not isinstance(name, str)
                        or not staff_id.strip()
                        or not name.strip()
                    ):
                        continue
                    entries.append(
                        {
                            "display_name": name.strip(),
                            "member_display": str(member_display),
                            "quorum_staff_id": staff_id.strip(),
                            "title_raw": clean_title(entry.get("t")),
                        }
                    )
        member_index: dict[str, str | None] = {}
        congestion = self._path("congestion")
        if congestion is not None:
            payload = load_json(congestion)
            for bioguide in sorted(payload):
                entry = payload.get(bioguide)
                if not isinstance(entry, Mapping):
                    continue
                name = entry.get("name")
                if not isinstance(name, str) or not name.strip():
                    continue
                normalized = re.sub(r"\s+", " ", ascii_fold(name)).strip().casefold()
                if normalized in member_index and member_index[normalized] != bioguide:
                    member_index[normalized] = None
                else:
                    member_index.setdefault(normalized, bioguide)

        latest_house = self.latest.get(CHAMBER_HOUSE)
        by_bioguide: defaultdict[str, set[str]] = defaultdict(set)
        for span in self.spans:
            if (
                span["chamber"] == CHAMBER_HOUSE
                and span["member_bioguide"]
                and latest_house is not None
                and span["last_period"] == latest_house
            ):
                by_bioguide[span["member_bioguide"]].add(span["spine_person_id"])

        quorum_by_spine: defaultdict[str, set[str]] = defaultdict(set)
        for entry in entries:
            key = display_payee_key(entry["display_name"])
            bioguide, source = self._resolve_staffer_member(
                entry["member_display"], member_index, latest_house
            )
            candidates: set[str] = set()
            if bioguide is not None and key is not None:
                for spine_id in sorted(by_bioguide.get(bioguide, set())):
                    for item in self.legacy_payee_keys[spine_id]:
                        if item[0] != key[0] or item[1] != key[1]:
                            continue
                        if not middle_compatible(item[2], key[2]):
                            continue
                        candidates.add(spine_id)
                        break
            if bioguide is None:
                status, spine_id = "MEMBER_UNRESOLVED", None
            elif len(candidates) == 1:
                status, spine_id = "LINKED", next(iter(candidates))
            elif candidates:
                status, spine_id = "NAME_COLLISION", None
            else:
                status, spine_id = "NOT_ON_PAYROLL", None
            history = []
            if spine_id is not None:
                quorum_by_spine[spine_id].add(entry["quorum_staff_id"])
                for span in sorted(
                    self.spans_by_person[spine_id],
                    key=lambda item: (item["chamber"], item["office_key"]),
                ):
                    history.append(
                        {
                            "chamber": span["chamber"],
                            "container_kind": span["container_kind"],
                            "first_period": span["first_period"],
                            "last_period": span["last_period"],
                            "member_bioguide": span["member_bioguide"],
                            "office_key": span["office_key"],
                            "periods_observed": span["periods_observed"],
                            "status": span["status"],
                            "title_last": span["title_last"],
                        }
                    )
            self.staffers.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "candidate_count": len(candidates),
                    "display_name": entry["display_name"],
                    "display_name_key": {
                        "first": key[1] if key else None,
                        "last": key[0] if key else None,
                        "middle_initial": key[2] if key else None,
                    },
                    "hill_history": history,
                    "link_status": status,
                    "member_bioguide": bioguide,
                    "member_display": entry["member_display"],
                    "member_resolution_source": source,
                    "quorum_staff_id": entry["quorum_staff_id"],
                    "review_status": "REVIEW_REQUIRED",
                    "rule_version": self.rule_version,
                    "schema_id": "staffer-network-current-staffer-link-v1",
                    "spine_person_id": spine_id,
                    "title_raw": entry["title_raw"],
                }
            )
        for spine_id, staff_ids in quorum_by_spine.items():
            row = spine_by_id[spine_id]
            if len(staff_ids) == 1:
                row["quorum_staff_id"] = next(iter(staff_ids))
                row["link_methods"] = sorted(
                    set(row["link_methods"])
                    | {"QUORUM_CURRENT_STAFFER_NAME_AND_MEMBER_BIOGUIDE"}
                )
            else:
                row["link_methods"] = sorted(
                    set(row["link_methods"]) | {"QUORUM_CURRENT_STAFFER_AMBIGUOUS"}
                )

    def _resolve_staffer_member(
        self,
        member_display: str,
        member_index: Mapping[str, str | None],
        latest_house: str | None,
    ) -> tuple[str | None, str]:
        normalized = re.sub(r"\s+", " ", ascii_fold(member_display)).strip().casefold()
        if member_index.get(normalized) is not None:
            return member_index[normalized], "MEMBER_DISPLAY_NAME_INDEX"
        if not QUORUM_MEMBER_ROSTER_FALLBACK:
            return None, "UNRESOLVED"
        key = display_payee_key(member_display)
        if key is None:
            return None, "UNRESOLVED"
        window = None
        if latest_house is not None:
            year = period_bounds(CHAMBER_HOUSE, latest_house)[1].year
            window = (year, year)
        bioguide, _method = resolve_member_bioguide(
            key[1], key[0], self.roster, self.nicknames, window
        )
        return (bioguide, "ROSTER_STRICT_FALLBACK") if bioguide else (None, "UNRESOLVED")

    # -- office index ------------------------------------------------------
    def build_office_index(self) -> None:
        grouped: defaultdict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        for item in self.observations:
            grouped[(item["chamber"], item["office_key"])].append(item)
        for (chamber, office_key), items in sorted(grouped.items()):
            tokens = sorted(
                {item["period"] for item in items},
                key=lambda token: period_ordinal(chamber, token),
            )
            profile = self.office_profile[(chamber, office_key)]
            periods = []
            for token in tokens:
                subset = [item for item in items if item["period"] == token]
                amounts = [
                    item["amount"] for item in subset if item["amount"] is not None
                ]
                periods.append(
                    {
                        "observation_count": len(subset),
                        "period": token,
                        "personnel_total": round(sum(amounts), 2) if amounts else None,
                        "staff_count": len(
                            {
                                self.observation_to_person[item["row_id"]]
                                for item in subset
                                if item["row_id"] in self.observation_to_person
                            }
                        ),
                    }
                )
            self.offices.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "chamber": chamber,
                    "container_kind": profile["container_kind"],
                    "first_period": tokens[0],
                    "last_period": tokens[-1],
                    "member_bioguide": profile["bioguide"],
                    "member_resolution_method": profile["method"],
                    "observation_count": len(items),
                    "office_key": office_key,
                    "office_raw_examples": list(profile["office_raws"])[
                        :MAX_OFFICE_RAW_EXAMPLES
                    ],
                    "period_kind": PERIOD_KIND[chamber],
                    "periods": periods,
                    "periods_observed": len(tokens),
                    "person_count": len(
                        {
                            self.observation_to_person[item["row_id"]]
                            for item in items
                            if item["row_id"] in self.observation_to_person
                        }
                    ),
                    "review_status": "REVIEW_REQUIRED",
                    "rule_version": self.rule_version,
                    "schema_id": "staffer-network-member-office-index-v1",
                }
            )

    def derive(self) -> dict[str, list[dict[str, Any]]]:
        self.load_observations()
        self.build_office_profiles()
        self.build_people()
        self.build_links()
        self.build_office_index()
        self.spans.sort(
            key=lambda row: (
                row["spine_person_id"],
                row["chamber"],
                row["office_key"],
                period_ordinal(row["chamber"], row["first_period"]),
            )
        )
        self.spine.sort(key=lambda row: row["spine_person_id"])
        self.staffers.sort(
            key=lambda row: (
                row["member_display"],
                row["display_name"],
                row["quorum_staff_id"],
            )
        )
        self.lda_links.sort(
            key=lambda row: (
                row["lda_source_person_id"],
                row["lane"],
                row["spine_person_id"] or "",
            )
        )
        self.offices.sort(key=lambda row: (row["chamber"], row["office_key"]))
        derived = {
            LDA_LINK_FILE: self.lda_links,
            OFFICE_INDEX_FILE: self.offices,
            SPAN_FILE: self.spans,
            SPINE_FILE: self.spine,
            STAFFER_FILE: self.staffers,
        }
        if self.name_standard:
            derived[NAME_STANDARD_ID_MAP_FILE] = self.id_map
        return derived


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------
def verify(args: argparse.Namespace) -> dict[str, Any]:
    primary = Path(args.primary_root).resolve()
    twin = Path(args.twin_root).resolve()
    assertions: dict[str, bool] = {}
    failures: list[str] = []
    detail: dict[str, Any] = {}

    for directory in (primary, twin):
        if not (directory / RECEIPT_FILE).is_file():
            raise VerificationFailure(f"missing output: {directory / RECEIPT_FILE}")

    receipt = load_json(primary / RECEIPT_FILE)
    twin_receipt = load_json(twin / RECEIPT_FILE)

    # A name-standard generation carries a sixth payload, the id map.  The mode
    # is read off the receipt; a generation without the block is verified over
    # exactly the five files it always was.
    name_standard = isinstance(receipt.get("name_standard"), Mapping)
    payload_files: tuple[str, ...] = PAYLOAD_FILES + (
        (NAME_STANDARD_ID_MAP_FILE,) if name_standard else ()
    )
    schema_by_file = dict(SCHEMA_BY_FILE)
    extra_verbatim: frozenset[str] = frozenset()
    if name_standard:
        schema_by_file[NAME_STANDARD_ID_MAP_FILE] = NAME_STANDARD_ID_MAP_SCHEMA_FILE
        extra_verbatim = NAME_STANDARD_VERBATIM_LEAF_NAMES

    for directory in (primary, twin):
        for name in payload_files:
            if not (directory / name).is_file():
                raise VerificationFailure(f"missing output: {directory / name}")

    # ---- receipt pins ----------------------------------------------------
    assertions["receipt_schema_id_exact"] = receipt.get("schema_id") == RECEIPT_SCHEMA
    assertions["receipt_stage_id_exact"] = receipt.get("stage_id") == STAGE_ID
    assertions["receipt_status_pass"] = receipt.get("status") == "PASS"
    assertions["receipt_zero_promotions"] = (
        receipt.get("canonical_employment_promotions") == 0
        and receipt.get("canonical_identity_promotions") == 0
    )
    assertions["receipt_promotion_policy"] = (
        receipt.get("promotion_policy") == "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
    )
    assertions["receipt_review_required"] = receipt.get("review_status") == "REVIEW_REQUIRED"
    assertions["receipt_no_declared_failures"] = not receipt.get("failures")

    # ---- the House double-count gate -------------------------------------
    # From House ledger v3 the ledger carries both eras.  Binding the separate
    # 2009Q3-2015Q4 candidate file alongside it would admit every row of that
    # era twice, and nothing downstream would notice: the duplicates carry
    # different row ids, so conservation would still balance over a doubled
    # observation set.  The only way to catch it is to refuse the second lane
    # outright, at both ends -- the inputs the receipt binds and the lanes the
    # spans declare.
    sources_block = receipt.get("sources") or {}
    inputs_block = receipt.get("inputs") or {}
    bound_pdf_inputs = sorted(
        label
        for label, entry in inputs_block.items()
        if RETIRED_PDF_INPUT_LABEL in label and (entry or {}).get("present")
    )
    assertions["no_separate_pdf_lane_input_bound"] = not bound_pdf_inputs
    assertions["receipt_pins_separate_pdf_lane_false"] = (
        sources_block.get("separate_pdf_lane_bound") is False
    )
    if bound_pdf_inputs:
        failures.append("SEPARATE_PDF_LANE_BOUND_ALONGSIDE_LEDGER")
        detail["bound_pdf_inputs"] = bound_pdf_inputs

    # ---- twin identity ---------------------------------------------------
    twin_identical = True
    for name in (*payload_files, RECEIPT_FILE):
        if sha(primary / name) != sha(twin / name):
            twin_identical = False
            failures.append(f"TWIN_BYTE_MISMATCH:{name}")
    assertions["primary_and_twin_byte_identical"] = twin_identical
    assertions["twin_receipt_equals_primary_receipt"] = twin_receipt == receipt

    # ---- file block ------------------------------------------------------
    payloads: dict[str, list[dict[str, Any]]] = {}
    file_ok = True
    for name in payload_files:
        path = primary / name
        rows = list(read_rows(path))
        payloads[name] = rows
        declared = (receipt.get("files") or {}).get(name) or {}
        if (
            declared.get("sha256") != sha(path)
            or declared.get("bytes") != path.stat().st_size
            or declared.get("rows") != len(rows)
        ):
            file_ok = False
            failures.append(f"RECEIPT_FILE_BLOCK_MISMATCH:{name}")
    assertions["receipt_file_block_matches_disk"] = file_ok

    retired_lane_spans = [
        index
        for index, row in enumerate(payloads[SPAN_FILE])
        if RETIRED_LANE_HOUSE_PDF in (row.get("source_lane") or ())
    ]
    assertions["no_span_carries_the_retired_pdf_lane"] = not retired_lane_spans
    if retired_lane_spans:
        failures.append("SPAN_CARRIES_RETIRED_PDF_LANE")
        detail["retired_lane_span_indexes"] = retired_lane_spans[:20]

    # ---- input hashes ----------------------------------------------------
    inputs_ok = True
    missing_inputs = []
    for label, entry in sorted((receipt.get("inputs") or {}).items()):
        if not entry.get("present"):
            continue
        path = Path(entry["path"])
        if not path.is_file():
            inputs_ok = False
            missing_inputs.append(label)
            continue
        if sha(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            inputs_ok = False
            failures.append(f"INPUT_HASH_MISMATCH:{label}")
    if missing_inputs:
        failures.append("INPUT_MISSING_ON_DISK")
        detail["missing_inputs"] = missing_inputs
    assertions["input_hashes_rebind"] = inputs_ok

    # ---- schemas ---------------------------------------------------------
    schema_ok = True
    schema_errors: list[str] = []
    for name, schema_file in schema_by_file.items():
        schema = load_json(SCHEMA_DIR / schema_file)
        for index, row in enumerate(payloads[name]):
            try:
                validate_instance(row, schema)
            except SchemaValidationError as error:
                schema_ok = False
                if len(schema_errors) < 10:
                    schema_errors.append(f"{name}[{index}]: {error}")
    try:
        validate_instance(
            receipt, load_json(SCHEMA_DIR / "hill_personnel_spine_receipt.schema.json")
        )
    except SchemaValidationError as error:
        schema_ok = False
        schema_errors.append(f"{RECEIPT_FILE}: {error}")
    assertions["every_row_validates_against_its_schema"] = schema_ok
    if not schema_ok:
        failures.append("SCHEMA_VALIDATION_FAILED")
        detail["schema_errors"] = schema_errors

    # ---- tripwire --------------------------------------------------------
    tripwire: list[str] = []
    for name in payload_files:
        tripwire.extend(f"{name}: {item}" for item in assert_unpromoted(payloads[name]))
    assertions["anti_promotion_tripwire_clean"] = not tripwire
    if tripwire:
        failures.append("INV1_PROMOTION_TRIPWIRE")
        detail["tripwire"] = tripwire[:20]

    # ---- language law ----------------------------------------------------
    authored: list[str] = []
    verbatim: Counter = Counter()
    for name in payload_files:
        hits, occurrences = language_law_scan(payloads[name], extra_verbatim)
        authored.extend(f"{name}: {item}" for item in hits)
        verbatim.update(occurrences)
    receipt_hits, _ = language_law_scan(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"inputs", "files", "language_law"}
        },
        extra_verbatim,
    )
    authored.extend(f"{RECEIPT_FILE}: {item}" for item in receipt_hits)
    assertions["language_law_clean"] = not authored
    if authored:
        failures.append("INV7_LANGUAGE_LAW_AUTHORED_TOKEN")
        detail["language_law_hits"] = authored[:20]

    # ---- independent re-derivation --------------------------------------
    deriver = Deriver(receipt)
    if deriver.rule_version != EXPECTED_RULE_VERSION:
        failures.append("RULE_VERSION_MISMATCH")
    derived = deriver.derive()
    rederivation_ok = True
    rederivation_detail: dict[str, Any] = {}
    for name in payload_files:
        emitted = [compact(row) for row in payloads[name]]
        rebuilt = [compact(row) for row in derived[name]]
        matched = sum(1 for left, right in zip(emitted, rebuilt) if left == right)
        rederivation_detail[name] = {
            "emitted_rows": len(emitted),
            "matched_rows": matched,
            "rederived_rows": len(rebuilt),
        }
        if emitted != rebuilt:
            rederivation_ok = False
            failures.append(f"REDERIVATION_MISMATCH:{name}")
            for index, (left, right) in enumerate(zip(emitted, rebuilt)):
                if left != right:
                    rederivation_detail.setdefault("first_difference", {})[name] = {
                        "emitted": left.decode("utf-8")[:600],
                        "index": index,
                        "rederived": right.decode("utf-8")[:600],
                    }
                    break
    assertions["rederived_rows_equal_emitted_rows"] = rederivation_ok
    detail["rederivation"] = rederivation_detail

    # ---- conservation ----------------------------------------------------
    span_observation_sum = sum(row["observation_count"] for row in payloads[SPAN_FILE])
    observations = len(deriver.observations)
    conservation_ok = span_observation_sum == observations
    receipt_observations_admitted = (receipt.get("conservation") or {}).get("observations_admitted")
    conservation_matches_receipt = receipt_observations_admitted == observations
    span_ids = {row["spine_person_id"] for row in payloads[SPAN_FILE]}
    spine_ids = {row["spine_person_id"] for row in payloads[SPINE_FILE]}
    assertions["observation_conservation"] = conservation_ok
    assertions["observation_conservation_matches_receipt"] = conservation_matches_receipt
    assertions["span_spine_person_ids_equal"] = span_ids == spine_ids
    assertions["spine_person_ids_unique"] = len(spine_ids) == len(payloads[SPINE_FILE])
    union: set[str] = set()
    for row in payloads[SPAN_FILE]:
        union.update(row["source_row_ids"])
    assertions["source_row_id_union_equals_observations"] = union == {
        item["row_id"] for item in deriver.observations
    }
    if not conservation_ok:
        failures.append("CONSERVATION_OBSERVATION_COUNT_MISMATCH")
    if not conservation_matches_receipt:
        failures.append("CONSERVATION_RECEIPT_OBSERVATIONS_ADMITTED_MISMATCH")
    if span_ids != spine_ids:
        failures.append("CONSERVATION_SPINE_PERSON_MISMATCH")
    detail["conservation"] = {
        "observations_rederived": observations,
        "receipt_observations_admitted": receipt_observations_admitted,
        "span_observation_count_sum": span_observation_sum,
        "span_source_row_id_union": len(union),
        "spine_rows": len(payloads[SPINE_FILE]),
    }

    # ---- observed periods and contiguous runs (2026-09-07) ---------------
    # These read the EMITTED rows, not the re-derived ones.  The re-derivation
    # above already proves the two implementations agree; this proves the
    # emitted values are internally coherent, which a shared mistake in both
    # implementations would not.  Each check is a statement a reader can make
    # with nothing but one span row in hand.
    observed_period_fields = (
        "observed_periods",
        "observed_period_count",
        "contiguous_runs",
    )
    missing_fields: list[str] = []
    count_mismatch: list[str] = []
    coverage_mismatch: list[str] = []
    non_maximal_runs: list[str] = []
    runs_outside_window: list[str] = []
    flag_disagrees: list[str] = []
    runs_histogram: Counter = Counter()
    longest_run_periods = 0
    longest_span_periods = 0
    for row in payloads[SPAN_FILE]:
        label = f"{row['spine_person_id']}|{row['chamber']}|{row['office_key']}"
        if any(row.get(field) is None for field in observed_period_fields):
            missing_fields.append(label)
            continue
        chamber = row["chamber"]
        emitted_periods = row["observed_periods"]
        emitted_runs = row["contiguous_runs"]
        if (
            row["observed_period_count"] != len(emitted_periods)
            or row["observed_period_count"] != row["periods_observed"]
        ):
            count_mismatch.append(label)
        # Expand every run over the chamber calendar, in the order the runs are
        # written.  Comparing the expansion to observed_periods as a LIST -- not
        # as a set -- makes one statement out of three: the runs cover exactly
        # the periods observed, in calendar order, with nothing repeated.
        expanded: list[str] = []
        run_ok = bool(emitted_runs)
        previous_end: int | None = None
        for run in emitted_runs:
            if not isinstance(run, list) or len(run) != 2:
                run_ok = False
                break
            start_ordinal = period_ordinal(chamber, run[0])
            end_ordinal = period_ordinal(chamber, run[1])
            if end_ordinal < start_ordinal:
                run_ok = False
                break
            # A maximal run cannot start one period after the previous one
            # ended: that pair would be a single run.  This is what makes
            # "one run" and "contiguous" the same statement.
            if previous_end is not None and start_ordinal <= previous_end + 1:
                non_maximal_runs.append(label)
            previous_end = end_ordinal
            expanded.extend(
                period_token_from_ordinal(chamber, ordinal)
                for ordinal in range(start_ordinal, end_ordinal + 1)
            )
            longest_run_periods = max(
                longest_run_periods, end_ordinal - start_ordinal + 1
            )
        if not run_ok:
            non_maximal_runs.append(label)
        if expanded != emitted_periods:
            coverage_mismatch.append(label)
        first_ordinal = period_ordinal(chamber, row["first_period"])
        last_ordinal = period_ordinal(chamber, row["last_period"])
        longest_span_periods = max(
            longest_span_periods, last_ordinal - first_ordinal + 1
        )
        if emitted_runs and (
            period_ordinal(chamber, emitted_runs[0][0]) < first_ordinal
            or period_ordinal(chamber, emitted_runs[-1][1]) > last_ordinal
        ):
            runs_outside_window.append(label)
        if row["contiguous"] != (len(emitted_runs) == 1):
            flag_disagrees.append(label)
        run_count = len(emitted_runs)
        runs_histogram[
            f"spans_with_{run_count}_runs"
            if run_count < 5
            else "spans_with_5_or_more_runs"
        ] += 1
    assertions["every_span_carries_the_observed_period_fields"] = not missing_fields
    assertions["span_observed_period_count_agrees_with_periods_observed"] = (
        not count_mismatch
    )
    assertions["span_contiguous_runs_cover_exactly_the_observed_periods"] = (
        not coverage_mismatch
    )
    assertions["span_contiguous_runs_are_maximal_and_non_empty"] = not non_maximal_runs
    assertions["span_contiguous_runs_lie_within_the_first_last_period_window"] = (
        not runs_outside_window
    )
    assertions["span_contiguous_flag_agrees_with_the_run_count"] = not flag_disagrees
    for key, offenders in (
        ("SPAN_OBSERVED_PERIOD_FIELDS_MISSING", missing_fields),
        ("SPAN_OBSERVED_PERIOD_COUNT_MISMATCH", count_mismatch),
        (
            "SPAN_CONTIGUOUS_RUNS_DO_NOT_COVER_THE_OBSERVED_PERIODS",
            coverage_mismatch,
        ),
        ("SPAN_CONTIGUOUS_RUNS_NOT_MAXIMAL_OR_EMPTY", non_maximal_runs),
        ("SPAN_CONTIGUOUS_RUNS_OUTSIDE_THE_SPAN_WINDOW", runs_outside_window),
        ("SPAN_CONTIGUOUS_FLAG_DISAGREES_WITH_THE_RUN_COUNT", flag_disagrees),
    ):
        if offenders:
            failures.append(key)
    detail["observed_periods"] = {
        "coverage_mismatch_examples": sorted(coverage_mismatch)[:3],
        "count_mismatch_examples": sorted(count_mismatch)[:3],
        "flag_disagreement_examples": sorted(flag_disagrees)[:3],
        "longest_contiguous_run_periods": longest_run_periods,
        "longest_first_to_last_window_periods": longest_span_periods,
        "missing_field_examples": sorted(missing_fields)[:3],
        "non_maximal_run_examples": sorted(non_maximal_runs)[:3],
        "runs_outside_window_examples": sorted(runs_outside_window)[:3],
        "spans_by_run_count": dict(
            sorted(
                (key, value)
                for key, value in runs_histogram.items()
                if key.startswith("spans_with_")
            )
        ),
        "spans_with_more_than_one_run": sum(
            1
            for row in payloads[SPAN_FILE]
            if len(row.get("contiguous_runs") or []) > 1
        ),
    }

    # ---- name standard ---------------------------------------------------
    # These check the PUBLISHED files against each other and against the
    # receipt's own claims.  They are independent of the re-derivation above:
    # the id is rebuilt here from the anchor span and the name key the row
    # carries, which is the reconstruction a reader of the generation can do
    # with nothing but the generation in hand.
    if name_standard:
        block = receipt["name_standard"]
        id_map = payloads[NAME_STANDARD_ID_MAP_FILE]
        spine_rows_out = payloads[SPINE_FILE]
        legacy_ids = [row["legacy_person_id"] for row in id_map]
        map_targets = {row["person_id"] for row in id_map}
        spine_ids_out = {row["spine_person_id"] for row in spine_rows_out}
        merge_groups_seen = {row["person_id"] for row in id_map if row["merged_with"]}
        people_in_groups = sum(1 for row in id_map if row["merged_with"])
        ids_removed = len(legacy_ids) - len(map_targets)
        keys_changed = sum(1 for row in id_map if row["key_v6"] != row["key_v7"])
        key_by_person = {row["person_id"]: row["key_v7"] for row in id_map}

        anchor_by_person: dict[str, tuple[Any, str, str, str]] = {}
        for row in payloads[SPAN_FILE]:
            ordering = (
                period_bounds(row["chamber"], row["first_period"])[0].toordinal(),
                row["chamber"],
                row["office_key"],
            )
            found = anchor_by_person.get(row["spine_person_id"])
            if found is None or ordering < found[0]:
                anchor_by_person[row["spine_person_id"]] = (
                    ordering,
                    row["chamber"],
                    row["office_key"],
                    row["first_period"],
                )
        reconstructed = 0
        for row in spine_rows_out:
            found = anchor_by_person.get(row["spine_person_id"])
            if found is None:
                continue
            _ordering, chamber, office_key, first_period = found
            # Ruling C: the ordinal is part of the tuple, so it is part of the
            # reconstruction.  A generation whose rows carried no ordinal would
            # not reconstruct here, which is the point: the tuple is exactly
            # what the row says it is.
            rebuilt_id = "hill:person:" + digest_of(
                {
                    "chamber": chamber,
                    "collision_ordinal": row.get("collision_ordinal"),
                    "first_office_key": office_key,
                    "first_period": first_period,
                    "name_key": row.get("name_key"),
                }
            )
            if rebuilt_id == row["spine_person_id"]:
                reconstructed += 1

        assertions["id_map_has_one_row_per_previous_person"] = len(legacy_ids) == len(
            set(legacy_ids)
        )
        assertions["id_map_targets_are_exactly_the_spine_ids"] = (
            map_targets == spine_ids_out
        )
        assertions["every_spine_row_carries_its_previous_ids"] = all(
            bool(row.get("legacy_person_ids"))
            and row.get("legacy_person_id") == sorted(row["legacy_person_ids"])[0]
            for row in spine_rows_out
        )
        assertions["spine_name_key_matches_the_id_map"] = all(
            row.get("name_key") == key_by_person.get(row["spine_person_id"])
            for row in spine_rows_out
        )
        assertions["every_id_reconstructs_from_its_anchor_span_and_name_key"] = (
            reconstructed == len(spine_rows_out)
        )
        assertions["receipt_name_standard_arithmetic_holds"] = (
            block.get("spine_persons_before") == len(id_map)
            and block.get("id_map_rows") == len(id_map)
            and block.get("merge_ids_removed") == ids_removed
            and block.get("merge_groups_count") == len(merge_groups_seen)
            and block.get("merge_people_in_groups") == people_in_groups
            and block.get("keys_changed") == keys_changed
            and block.get("keys_unchanged") == len(id_map) - keys_changed
            and block.get("reason_counts")
            == dict(sorted(Counter(row["reason"] for row in id_map).items()))
            and len(id_map) - ids_removed == len(spine_rows_out)
        )
        # Ruling A: the key-source histogram is a MEASUREMENT.  It is checked
        # against this verifier's own recomputation, not against zero.
        summary = deriver.rekey_summary
        assertions["receipt_name_standard_key_source_histogram_rederives"] = (
            block.get("key_source_disagreements")
            == summary.get("key_source_disagreements")
            and block.get("key_source_disagreement_people")
            == summary.get("key_source_disagreement_people")
        )
        # Ruling B: residuals are bounded by the ambiguity the delta measured,
        # and the per-triple reconstruction is recomputed here as well.
        assertions["receipt_name_standard_delta_residuals_within_allowance"] = (
            isinstance(block.get("delta_residuals_count"), int)
            and block["delta_residuals_count"]
            == summary.get("delta_residuals_count")
            and block["delta_residuals_count"]
            <= NAME_STANDARD_DELTA_RESIDUAL_ALLOWANCE
        )
        assertions["receipt_name_standard_cause_histograms_rederive"] = (
            block.get("cause_counts") == summary.get("cause_counts")
            and block.get("delta_reconstruction_cause_counts")
            == summary.get("delta_reconstruction_cause_counts")
        )
        assertions["receipt_name_standard_delta_report_agrees"] = bool(
            (block.get("delta_agreement") or {}).get("bound")
        ) and not (
            (block.get("delta_agreement") or {}).get(
                "causes_differing_by_more_than_the_residual_count"
            )
            or (block.get("delta_agreement") or {}).get(
                "causes_where_the_reconstruction_differs_from_the_report"
            )
        )
        # Ruling C: the blocked merges and the span union both re-derive.
        assertions["receipt_name_standard_merge_guard_rederives"] = (
            block.get("merges_blocked_pairs") == summary.get("merges_blocked_pairs")
            and all(
                item.get("merge_basis") in NAME_STANDARD_MERGE_BASIS_ORDER
                for item in (block.get("merge_groups") or [])
            )
        )
        assertions["name_standard_never_merges_on_missing_dates"] = (
            all(row.get("merge_basis") != "same_period_variant_no_day_dates" for row in id_map)
            and all(item.get("merge_basis") != "same_period_variant_no_day_dates"
                    for item in (block.get("merge_groups") or []))
        )
        assertions["receipt_spans_unioned_rederives"] = (
            (receipt.get("counts") or {}).get("spans_unioned_after_merge")
            == deriver.spans_unioned
        )
        assertions["no_person_office_holds_two_touching_span_windows"] = (
            (receipt.get("counts") or {}).get(
                "person_office_spans_with_touching_windows"
            )
            == 0
        )
        # Ruling E: an empty first_class is fatal, and stays fatal here.
        assertions["receipt_name_standard_no_empty_first_class"] = (
            block.get("empty_first_class_count") == 0
            and summary.get("empty_first_class_count") == 0
            and all(
                (row.get("payee_key") or {}).get("first_class")
                for row in spine_rows_out
            )
        )
        assertions["receipt_name_standard_zero_canonical_promotions"] = (
            block.get("canonical_promotions") == 0
        )
        for key, ok in (
            ("NAME_STANDARD_ID_MAP_NOT_ONE_ROW_PER_PERSON", assertions["id_map_has_one_row_per_previous_person"]),
            ("NAME_STANDARD_ID_MAP_TARGETS_DISAGREE_WITH_THE_SPINE", assertions["id_map_targets_are_exactly_the_spine_ids"]),
            ("NAME_STANDARD_SPINE_MISSING_A_PREVIOUS_ID", assertions["every_spine_row_carries_its_previous_ids"]),
            ("NAME_STANDARD_SPINE_NAME_KEY_DISAGREES_WITH_THE_ID_MAP", assertions["spine_name_key_matches_the_id_map"]),
            ("NAME_STANDARD_ID_DOES_NOT_RECONSTRUCT", assertions["every_id_reconstructs_from_its_anchor_span_and_name_key"]),
            ("NAME_STANDARD_RECEIPT_ARITHMETIC_MISMATCH", assertions["receipt_name_standard_arithmetic_holds"]),
            ("NAME_STANDARD_KEY_SOURCE_HISTOGRAM_MISMATCH", assertions["receipt_name_standard_key_source_histogram_rederives"]),
            ("NAME_STANDARD_DELTA_RESIDUALS_OVER_ALLOWANCE", assertions["receipt_name_standard_delta_residuals_within_allowance"]),
            ("NAME_STANDARD_CAUSE_HISTOGRAM_MISMATCH", assertions["receipt_name_standard_cause_histograms_rederive"]),
            ("NAME_STANDARD_DELTA_REPORT_DISAGREES", assertions["receipt_name_standard_delta_report_agrees"]),
            ("NAME_STANDARD_MERGE_GUARD_MISMATCH", assertions["receipt_name_standard_merge_guard_rederives"]),
            ("NAME_STANDARD_UNDATED_MERGE", assertions["name_standard_never_merges_on_missing_dates"]),
            ("NAME_STANDARD_SPANS_UNIONED_MISMATCH", assertions["receipt_spans_unioned_rederives"]),
            ("SPAN_ROWS_SHARE_A_PERSON_OFFICE_WITH_TOUCHING_WINDOWS", assertions["no_person_office_holds_two_touching_span_windows"]),
            ("NAME_STANDARD_EMPTY_FIRST_CLASS", assertions["receipt_name_standard_no_empty_first_class"]),
        ):
            if not ok:
                failures.append(key)
        detail["name_standard"] = {
            "cause_counts_rederived": summary.get("cause_counts"),
            "collision_ordinals_above_one": sum(
                1 for row in spine_rows_out if (row.get("collision_ordinal") or 1) > 1
            ),
            "delta_reconstruction_cause_counts_rederived": summary.get(
                "delta_reconstruction_cause_counts"
            ),
            "delta_residuals_rederived": summary.get("delta_residuals_count"),
            "id_map_rows": len(id_map),
            "ids_reconstructed_from_the_anchor_span": reconstructed,
            "key_source_disagreements_rederived": summary.get(
                "key_source_disagreements"
            ),
            "keys_changed": keys_changed,
            "merge_basis_counts": dict(
                sorted(
                    Counter(
                        item.get("merge_basis")
                        for item in (block.get("merge_groups") or [])
                    ).items()
                )
            ),
            "merge_groups": len(merge_groups_seen),
            "merge_ids_removed": ids_removed,
            "merge_people_in_groups": people_in_groups,
            "merges_blocked_pairs_rederived": summary.get("merges_blocked_pairs"),
            "reason_counts": dict(
                sorted(Counter(row["reason"] for row in id_map).items())
            ),
            "spans_unioned_rederived": deriver.spans_unioned,
            "spine_rows": len(spine_rows_out),
        }

    # ---- era provenance, re-derived -------------------------------------
    # The receipt claims which ledger era each House span came from and how many
    # spans cross 2015Q4 -> 2016Q1.  Re-derive both from the observations rather
    # than trusting the claim, and check the bound ledger really does carry both
    # eras: a ledger carrying only one would make the whole rebind vacuous.
    form_by_row = {
        item["row_id"]: item.get("source_form")
        for item in deriver.observations
        if item["chamber"] == CHAMBER_HOUSE
    }
    period_by_row = {
        item["row_id"]: item["period"]
        for item in deriver.observations
        if item["chamber"] == CHAMBER_HOUSE
    }
    derived_forms: Counter = Counter()
    derived_crossing = 0
    for row in payloads[SPAN_FILE]:
        if row["chamber"] != CHAMBER_HOUSE:
            continue
        row_ids = row["source_row_ids"]
        derived_forms[
            "+".join(sorted({form_by_row.get(item) or "unknown" for item in row_ids}))
        ] += 1
        periods = {period_by_row.get(item) for item in row_ids}
        if PDF_ERA_LAST_QUARTER in periods and CSV_ERA_FIRST_QUARTER in periods:
            derived_crossing += 1
    observed_forms = {value for value in form_by_row.values() if value}
    counts_block = receipt.get("counts") or {}
    # How many rows of each era were admitted is a claim in the receipt; check
    # it against the observations rather than against itself.  Which eras the
    # bound ledger happens to carry is a property of that ledger and is
    # reported, not asserted: a fixture ledger legitimately carries one.
    admitted_by_form: Counter = Counter()
    for value in form_by_row.values():
        admitted_by_form[value or "unknown"] += 1
    assertions["receipt_admitted_rows_by_source_form_rederives"] = (
        sources_block.get("house_ledger_rows_admitted_by_source_form") or {}
    ) == dict(sorted(admitted_by_form.items()))
    assertions["receipt_spans_by_house_source_form_rederives"] = counts_block.get(
        "spans_by_house_source_form"
    ) == dict(sorted(derived_forms.items()))
    assertions["receipt_era_boundary_span_count_rederives"] = (
        counts_block.get("spans_crossing_csv_pdf_era_boundary") == derived_crossing
    )
    detail["era_provenance"] = {
        "house_ledger_carries_both_eras": observed_forms
        == {SOURCE_FORM_CSV, SOURCE_FORM_PDF},
        "observed_source_forms": sorted(observed_forms),
        "spans_by_house_source_form_rederived": dict(sorted(derived_forms.items())),
        "spans_crossing_csv_pdf_era_boundary_rederived": derived_crossing,
    }

    # ---- link rules ------------------------------------------------------
    link_counts = {
        "current_staffer_link_status": dict(
            sorted(Counter(row["link_status"] for row in payloads[STAFFER_FILE]).items())
        ),
        "lda_link_status": dict(
            sorted(Counter(row["link_status"] for row in payloads[LDA_LINK_FILE]).items())
        ),
    }
    linked_staffers = sum(
        1 for row in payloads[STAFFER_FILE] if row["link_status"] == "LINKED"
    )
    linked_with_person = sum(
        1
        for row in payloads[STAFFER_FILE]
        if (row["link_status"] == "LINKED") != (row["spine_person_id"] is not None)
    )
    assertions["staffer_link_status_agrees_with_spine_person_id"] = linked_with_person == 0
    lda_disagree = sum(
        1
        for row in payloads[LDA_LINK_FILE]
        if (row["link_status"] == "LINKED_BY_PAYROLL_KEY")
        != (row["spine_person_id"] is not None)
    )
    assertions["lda_link_status_agrees_with_spine_person_id"] = lda_disagree == 0
    assertions["linked_staffers_have_history"] = all(
        row["hill_history"] for row in payloads[STAFFER_FILE] if row["link_status"] == "LINKED"
    )
    if linked_with_person or lda_disagree:
        failures.append("LINK_STATUS_INCONSISTENT")
    detail["link_counts"] = link_counts
    detail["linked_staffers"] = linked_staffers

    for key, value in assertions.items():
        if not value:
            failures.append(f"ASSERTION_FAILED:{key}")

    result = {
        "assertions": assertions,
        "counts": {
            "lda_spine_links": len(payloads[LDA_LINK_FILE]),
            "member_office_index_rows": len(payloads[OFFICE_INDEX_FILE]),
            "person_office_spans": len(payloads[SPAN_FILE]),
            "spine_persons": len(payloads[SPINE_FILE]),
            "current_staffer_links": len(payloads[STAFFER_FILE]),
        },
        "detail": detail,
        "failures": sorted(set(failures)),
        "language_law": {
            "authored_hits": len(authored),
            "verbatim_token_occurrences": dict(sorted(verbatim.items())),
        },
        "primary": str(primary),
        "schema_id": SCHEMA_ID,
        "stage_id": STAGE_ID,
        "status": "PASS" if not failures else "FAIL",
        "twin": str(twin),
        "verified_rule_version": receipt.get("rule_version"),
    }
    report_root = Path(args.report_root)
    report_root.mkdir(parents=True, exist_ok=True)
    output = report_root / VERIFICATION_FILE
    output.write_bytes(canonical_line(result))
    result["output"] = str(output)
    return result


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-root", required=True, type=Path)
    parser.add_argument("--twin-root", required=True, type=Path)
    parser.add_argument("--report-root", required=True, type=Path)
    parser.add_argument("--run-id", default="unbound")
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    # INV-11.  The verifier emits the same three events the builder does, under
    # the same run id, so a verification run is visible in the glass box.
    glassbox = not args.no_glassbox
    emit_glassbox(
        glassbox,
        args.run_id,
        "run.start",
        "running",
        "hill personnel spine verification started",
        detail=str(args.primary_root),
    )
    try:
        result = verify(args)
    except Exception as error:
        emit_glassbox(
            glassbox,
            args.run_id,
            "run.fail",
            "failed",
            "hill personnel spine verification failed",
            detail=f"{type(error).__name__}: {error}",
        )
        raise
    emit_glassbox(
        glassbox,
        args.run_id,
        "run.finish",
        "completed" if result["status"] == "PASS" else "failed",
        f"hill personnel spine verification {result['status']}",
        detail=result["output"],
        metadata={
            "failures": len(result["failures"]),
            "person_office_spans": result["counts"]["person_office_spans"],
            "spine_persons": result["counts"]["spine_persons"],
            "status": result["status"],
        },
    )
    print(f"status: {result['status']}")
    print(f"output: {result['output']}")
    print("counts:")
    for key, value in sorted(result["counts"].items()):
        print(f"  {key}: {value}")
    print("assertions:")
    for key, value in result["assertions"].items():
        print(f"  {'PASS' if value else 'FAIL'}  {key}")
    print(f"failures: {result['failures']}")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
