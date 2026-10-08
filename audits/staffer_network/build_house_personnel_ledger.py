#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the review-only House personnel ledger from the House Statement of
Disbursements (SOD) detail CSVs.

Implements METHOD_HOUSE_SOD_CSV.md (file format, row admission, schema
generations, shifted-row repair) and METHOD_STAFFER_TRACKING.md (person key,
office key, STRICT roster resolution, cells, tenure spans, annualization,
current-vs-departed labelling) over the CSV era (2016Q1-2026Q1).  PDF-era rows
can be admitted through the same schema with ``--pdf-rows``; the default build
is CSV-only and the receipt says so.

Every emitted row sits on the candidate plane: ``identity_status`` is
``NAME_MATCH_ONLY``, ``review_status`` is ``REVIEW_REQUIRED`` and no
``canonical_*`` field is ever promoted.  The ledger records what the published
disbursement rows say about pay periods; it does not assert identity,
employment tenure boundaries, or current employment.

Read-only against every input.  Writes only into ``--output-root``, which must
not already exist (immutable generation).  Outputs are canonical NDJSON
(sorted keys, ASCII, gzip mtime 0, blank embedded filename) written atomically
via a temporary file and ``os.replace`` so a twin build is byte-identical.

Outputs
  house_personnel_observations.ndjson.gz  one row per admitted personnel row
  house_person_office_spans.ndjson.gz     tenure spans per (person_key, office_key)
  house_member_quarters.ndjson.gz         every member office per quarter, CSV era and PDF era
  house_personnel_ledger_receipt.json     inputs, counts, gold check, invariants
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RULE_VERSION = "sod-tracking-2026-09-02-a"
DEFAULT_RUN_ID = "run-20260902T043000000000Z-sod0hunt"

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_CSV_ROOT = HERE / "house_sod_payroll_20260831" / "raw_detail_csv"
DEFAULT_URL_INVENTORY = HERE / "house_sod_payroll_20260831" / "house_sod_url_inventory.json"
DEFAULT_ROSTER_ROOT = (
    REPO_ROOT / "data" / "staffer_network" / "reference" / "congress-legislators"
    / "750c0608efb6ef1fc3257ba72c99af3771d35088"
)
DEFAULT_OUTPUT_ROOT = HERE / "house_personnel_ledger_20260902_primary"

OBSERVATIONS_NAME = "house_personnel_observations.ndjson.gz"
SPANS_NAME = "house_person_office_spans.ndjson.gz"
MEMBER_QUARTERS_NAME = "house_member_quarters.ndjson.gz"
RECEIPT_NAME = "house_personnel_ledger_receipt.json"

SCHEMA_OBSERVATION = "staffer-network-sod-personnel-observation-v1"
SCHEMA_SPAN = "staffer-network-sod-person-office-span-v1"
SCHEMA_MEMBER_QUARTER = "staffer-network-sod-member-office-quarter-v2"
SCHEMA_RECEIPT = "staffer-network-house-personnel-ledger-receipt-v1"

# The INV block: identical on every row of every output (METHOD_STAFFER_TRACKING section 10).
INV = {
    "identity_status": "NAME_MATCH_ONLY",
    "review_status": "REVIEW_REQUIRED",
    "canonical_eligible": False,
    "canonical_employment_promoted": False,
    "canonical_identity_promoted": False,
    "canonical_office_promoted": False,
    "canonical_person_id": None,
    "canonical_office_id": None,
    "canonical_identity_decision": "NOT_ADJUDICATED",
}
INV_COUNTS = {
    "canonical_employment_promotions": 0,
    "canonical_identity_promotions": 0,
    "canonical_office_promotions": 0,
    "canonical_service_date_promotions": 0,
}

# CSV schema generations (METHOD_HOUSE_SOD_CSV section 1.1), verbatim.
SCHEMA_12 = [
    "ORGANIZATION", "PROGRAM", "SORT SUBTOTAL DESCRIPTION", "SORT SEQUENCE", "TRANSACTION DATE",
    "DATA SOURCE", "DOCUMENT", "VENDOR NAME", "PERFORM START DT", "PERFORM END DT", "DESCRIPTION", "AMOUNT",
]
SCHEMA_18 = [
    "ORGANIZATION", "FISCAL YEAR OR LEGISLATIVE YEAR", "ORGANIZATION CODE", "PROGRAM", "PROGRAM CODE",
    "SORT SUBTOTAL DESCRIPTION", "BUDGET OBJECT CLASS", "SORT SEQUENCE", "TRANSACTION DATE", "DATA SOURCE",
    "DOCUMENT", "VENDOR NAME", "VENDOR ID", "PERFORM START DT", "PERFORM END DT", "DESCRIPTION",
    "BUDGET OBJECT CODE", "AMOUNT",
]

CSV_NAME_RE = re.compile(r"^(?P<year>\d{4})q(?P<q>[1-4])_sod_detail\.csv$", re.I)
PERSONNEL_CLASS = "PERSONNEL COMPENSATION"
PERSONNEL_SUBTOTAL_DESCRIPTION = "PERSONNEL COMPENSATION TOTALS:"
MEMBER_PROGRAM = "OFFICIAL EXPENSES OF MEMBERS"
INTERN_PROGRAM = "INTERN ALLOWANCES"

# METHOD_STAFFER_TRACKING section 2: organization prefix.
ORG_PREFIX_RE = re.compile(r"^\s*(FISCAL YEAR\s+)?((?:19|20)\d{2})\s+(.*)$", re.I)
# Quoted from audits/staffer_network/acquire_house_sod_payroll.py:292.
DATE_FORMATS = ("%d-%b-%y", "%d-%b-%Y", "%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d")
QUALIFIER_RE = re.compile(r"\s*\(([^()]*)\)\s*$")
COMPENSATION_QUALIFIERS = {"OTHER COMPENSATION", "OVERTIME"}
SHARED_TITLE = "SHARED EMPLOYEE"
DATE_LEAK_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(?:19|20)\d{2}\b")
# Generational suffixes on payee rows.  METHOD_HOUSE_SOD_CSV section 6 (measured on the
# data): they sit right after the surname token and a bare trailing V is a middle
# initial, so V is NOT a payee suffix here (deviation from the tracking method's
# trailing-pop set, recorded in the receipt).
PAYEE_SUFFIXES = {"JR", "SR", "II", "III", "IV"}
OFFICE_SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
POST_NOMINALS = {"MD", "DDS", "DVM", "PHD", "JD", "DO"}
CAUCUS_TOKENS = {"CAUCUS", "COALITION", "COMMITTEE", "TEAM"}
VACANT_TOKENS = {"DISTRICT", "VACANT"}
LEADERSHIP_KEYWORDS = (
    "OFFICE OF THE SPEAKER", "MAJORITY LEADER", "MINORITY LEADER", "MAJORITY WHIP", "MINORITY WHIP",
    "DEMOCRATIC WHIP", "REPUBLICAN CONFERENCE", "DEMOCRATIC CAUCUS", "STEERING",
)
COMMITTEE_KEYWORDS = ("COMMITTEE", "COMM ON", "COMM-", "SELECT COMM", "JOINT")
COMMITTEE_BARE_FAMILIES = {
    "VETERANS' AFFAIRS", "HOMELAND SECURITY", "TRANSPORTATION-INFRASTRUCTURE", "INTELLIGENCE",
    "ARMED SERVICES COMMITTEE", "HOUSE ADMINISTRATION", "EDUCATION AND LABOR", "SCIENCE AND TECHNOLOGY",
}
MEMBER_CONTAINER_KINDS = {"member_office", "member_office_unresolved", "vacant_seat"}
CSV_SOURCE_FORM = "detail_csv"
PDF_SOURCE_FORM = "house_gov_single_volume_pdf"
# Member-quarter era markers.  The PDF candidate schemas (v1/v2)
# has no PROGRAM column and no subtotal rows, so a PDF-era member quarter can never carry the
# OFFICIAL EXPENSES OF MEMBERS / INTERN ALLOWANCES split nor a published subtotal to reconcile
# against.  These constants mark that on the row so a PDF-era row is never read as a CSV-era
# reconciled one.  Nothing here manufactures a subtotal or a program.
ERA_CSV = "CSV"
ERA_PDF = "PDF"
ERA_MIXED = "MIXED_CSV_AND_PDF"
SUBTOTAL_BASIS_PDF = "NO_SUBTOTAL_ROW_PDF_ERA"
SUBTOTAL_BASIS_CSV_ROW = "CSV_PERSONNEL_COMPENSATION_TOTALS_ROW"
SUBTOTAL_BASIS_CSV_ABSENT = "CSV_NO_SUBTOTAL_ROW"
SUBTOTAL_BASIS_NO_BLOCK = "NO_PERSONNEL_BLOCK"
ROWS_BASIS_CSV = "CSV_ROWS_FOR_THE_ORGANIZATION_ALL_SORT_SEQUENCES"
ROWS_BASIS_PDF = "PDF_ADMITTED_PERSONNEL_ROWS_ONLY_THE_CANDIDATE_FILE_CARRIES_NO_OTHER_ROWS"
ROWS_BASIS_MIXED = "CSV_ROWS_ALL_SORT_SEQUENCES_PLUS_PDF_ADMITTED_PERSONNEL_ROWS"
STAFF_BASIS_CSV = "distinct person_key over OFFICIAL EXPENSES OF MEMBERS personnel rows (all compensation classes)"
STAFF_BASIS_PDF = ("distinct person_key over the admitted PDF-era personnel rows for this office "
                   "(all compensation classes); the PDF schema has no program column, so no "
                   "OFFICIAL EXPENSES OF MEMBERS / INTERN ALLOWANCES split exists")
QUOTED_NICKNAME_RE = re.compile(r"[\"“”″]([^\"“”″]+)[\"“”″]")

# Office-string normalization, ported from
# data/staffer_network/reviews/confirmation_ladder_20260901/build_ladder.py:86-100 with one
# change: the continuation marker is only stripped after an em/en dash, U+FFFD or apostrophe,
# or as the separate word "Con." -- the verbatim regex strips the bare letters CON off any
# surname that ends in them (HON. DON BACON -> HON. DON BA).
YEAR_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s+")
CONTINUATION_RE = re.compile(r"(?:[—–�']\s*Con\.?|\s+Con\.)\s*$", re.I)
WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")

GOLD_KILEY = {
    "member": "HON. KEVIN KILEY",
    "organization": "2025 HON. KEVIN KILEY",
    "quarter": "2025Q2",
    "personnel_total": "282,805.54",
    "rows": [
        ["CAMERON, CARSON S.", "04/01/25", "06/30/25", "LEGISLATIVE ASSISTANT", "17,124.99"],
        ["CAMPBELL, HUNTLEY J.", "04/01/25", "06/30/25", "LEGISLATIVE ASSISTANT", "15,999.99"],
        ["EUCEDA, ANTHONY", "04/01/25", "06/30/25", "STAFF ASSISTANT", "14,000.01"],
        ["FATZINGER, MARY P.", "04/01/25", "04/23/25", "SCHEDULER", "4,280.56"],
        ["GEMELLARO, PETER J.", "04/01/25", "06/30/25", "CASEWORKER", "18,999.99"],
        ["HARTL, KELLIE J.", "04/01/25", "06/30/25", "SHARED EMPLOYEE", "5,000.01"],
        ["HOLSTE, ROBERT L.", "04/01/25", "06/30/25", "CHIEF OF STAFF", "56,424.99"],
        ["HORVAT, CHELYSSA I.", "04/01/25", "06/30/25", "DISTRICT DIRECTOR", "27,500.01"],
        ["MOYER, ALEXANDRA M.", "04/22/25", "06/30/25", "DIRECTOR OF OPERATIONS", "15,333.34"],
        ["PIRSOS, JOHN", "04/23/25", "06/30/25", "COMMUNICATIONS DIRECTOR", "17,000.00"],
        ["RAUBER, MICHAEL B.", "04/01/25", "05/31/25", "COMMUNICATIONS DIRECTOR", "7,916.67"],
        ["SHOOK, JAMES R.", "04/01/25", "06/30/25", "SENIOR ADVISOR", "21,600.00"],
        ["THOMPSON, JACK W.", "04/01/25", "06/30/25", "DISTRICT REPRESENTATIVE", "18,999.99"],
        ["VASQUEZ-PAVICHEVICH, NATALIA", "04/01/25", "06/30/25", "CASEWORKER", "16,374.99"],
        ["ZANDSTRA, JAMES R.", "04/01/25", "06/30/25", "LEGISLATIVE DIRECTOR", "26,250.00"],
    ],
}

RULE_DEVIATIONS = [
    "PAYEE_SUFFIX_V: a bare trailing V on a CSV-era payee is kept as a middle initial "
    "(METHOD_HOUSE_SOD_CSV section 6, CONNELLY HENRY V); JR/SR/II/III/IV are removed at any "
    "position because they sit right after the surname (FISCHER JR ROBERT V.).",
    "PAYEE_HYPHEN_JOIN: a hyphen inside a payee token is removed rather than turned into a space "
    "(VASQUEZ-PAVICHEVICH NATALIA -> surname VASQUEZPAVICHEVICH); office strings keep the "
    "hyphen-to-space rule so multi-word roster surnames match.",
    "OFFICE_CONTINUATION_MARKER: normalize_office strips Con. only after a dash/U+FFFD/apostrophe "
    "or as the separate word Con.; the verbatim build_ladder.py regex would strip the letters CON "
    "from surnames such as BACON.",
    "CONTAINER_RULE_ORDER: leadership/committee keyword tests run before the FISCAL_YEAR->admin "
    "rule so FISCAL YEAR ... COMMITTEE ON APPROPRIATIONS classifies as committee.",
    "TITLE_CHANGE_COMPARABILITY: TRUNCATED_PREFIX_EQUAL is applied symmetrically -- the longer "
    "title of a prefix pair must be exactly 30 characters (the published field width).",
]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

class BuildError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dec_str(value: Decimal) -> str:
    text = format(value, "f")
    if text == "-0":
        text = "0"
    return text


def atomic_write_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(tmp, path)


class DeterministicGzipWriter:
    """Canonical NDJSON gzip writer: mtime 0, blank filename, atomic replace on close."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.tmp = path.with_name(path.name + ".tmp")
        self.rows = 0
        self._raw = self.tmp.open("wb")
        self._gzip = gzip.GzipFile(filename="", mode="wb", fileobj=self._raw, compresslevel=9, mtime=0)

    def write(self, value: dict[str, Any]) -> None:
        self._gzip.write(canonical_bytes(value))
        self.rows += 1

    def __enter__(self) -> "DeterministicGzipWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._gzip.close()
        self._raw.flush()
        os.fsync(self._raw.fileno())
        self._raw.close()
        if exc_type is None:
            os.replace(self.tmp, self.path)
        else:
            try:
                self.tmp.unlink()
            except OSError:
                pass


def quarter_index(quarter: str) -> int:
    return int(quarter[:4]) * 4 + int(quarter[-1]) - 1


def quarter_label(index: int) -> str:
    return f"{index // 4}Q{index % 4 + 1}"


def quarter_bounds(quarter: str) -> tuple[dt.date, dt.date]:
    year, number = int(quarter[:4]), int(quarter[-1])
    start = dt.date(year, 3 * (number - 1) + 1, 1)
    end_month = 3 * number
    if end_month == 12:
        end = dt.date(year, 12, 31)
    else:
        end = dt.date(year, end_month + 1, 1) - dt.timedelta(days=1)
    return start, end


# ---------------------------------------------------------------------------
# Name / office normalization (METHOD_STAFFER_TRACKING sections 3 and 4)
# ---------------------------------------------------------------------------

_QUOTE_TABLE = str.maketrans({"’": "'", "“": "'", "”": "'", '"': "'"})


def ascii_upper(value: str) -> str:
    text = (value or "").translate(_QUOTE_TABLE)
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().upper()


def name_tokens(value: str, hyphen_join: bool) -> list[str]:
    text = ascii_upper(value).replace("'", "").replace(".", "")
    if hyphen_join:
        text = text.replace("-", "")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return text.split()


def parse_payee(payee_raw: str, pdf_era: bool) -> dict[str, Any]:
    text = ascii_upper(payee_raw)
    leaks = DATE_LEAK_RE.findall(text)
    if leaks:
        text = DATE_LEAK_RE.sub(" ", text)
    flags: list[str] = []
    surname = given = None
    middle: list[str] = []
    suffix: list[str] = []
    token_count = 0
    if pdf_era and "," in text:
        left, right = text.split(",", 1)
        left_tokens = name_tokens(left, True)
        right_tokens = name_tokens(right, True)
        suffix = [t for t in left_tokens + right_tokens if t in PAYEE_SUFFIXES]
        surname_tokens = [t for t in left_tokens if t not in PAYEE_SUFFIXES]
        rest_tokens = [t for t in right_tokens if t not in PAYEE_SUFFIXES]
        token_count = len(surname_tokens) + len(rest_tokens)
        if surname_tokens and rest_tokens:
            surname = " ".join(surname_tokens)
            given = rest_tokens[0]
            middle = rest_tokens[1:]
            if len(surname_tokens) > 1:
                flags.append("PAYEE_MULTITOKEN_SURNAME_PDF")
        else:
            tokens = surname_tokens + rest_tokens
            token_count = len(tokens)
            if token_count == 0:
                flags.append("PAYEE_EMPTY")
            elif token_count == 1:
                flags.append("PAYEE_SINGLE_TOKEN")
            else:
                surname, given, middle = tokens[0], tokens[1], tokens[2:]
    else:
        tokens = name_tokens(text, True)
        suffix = [t for t in tokens if t in PAYEE_SUFFIXES]
        tokens = [t for t in tokens if t not in PAYEE_SUFFIXES]
        token_count = len(tokens)
        if pdf_era:
            flags.append("PAYEE_PDF_NO_COMMA")
        if token_count == 0:
            flags.append("PAYEE_EMPTY")
        elif token_count == 1:
            flags.append("PAYEE_SINGLE_TOKEN")
        else:
            surname, given, middle = tokens[0], tokens[1], tokens[2:]
            if token_count >= 4:
                flags.append("PAYEE_PARSE_AMBIGUOUS")
    middle_initial = middle[0][0] if middle else ""
    person_key = f"SOD:{surname}|{given}|{middle_initial}" if surname and given else None
    family_key = f"SODFAM:{surname}|{given}" if surname and given else None
    return {
        "person_key": person_key,
        "person_key_family": family_key,
        "payee_parse": {
            "surname": surname,
            "given": given,
            "middle_tokens": middle,
            "middle_initial": middle_initial,
            "suffix_tokens": suffix,
            "date_leak_tokens": leaks,
            "token_count": token_count,
            "parse_flags": flags,
        },
    }


def parse_title(title_raw: str) -> tuple[str, str, bool]:
    match = QUALIFIER_RE.search(title_raw)
    compensation_class = "BASE"
    base = title_raw
    if match:
        qualifier = match.group(1).strip().upper()
        if qualifier in COMPENSATION_QUALIFIERS:
            compensation_class = qualifier
            base = title_raw[: match.start()]
    title_base = re.sub(r"\s+", " ", base).strip().upper()
    return title_base, compensation_class, len(title_base) == 30


def parse_date(raw: str) -> dt.date | None | str:
    text = (raw or "").strip()
    if not text:
        return None
    for fmt in DATE_FORMATS:
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return "UNPARSED"


def parse_amount(raw: str) -> Decimal | None:
    text = (raw or "").replace("$", "").replace(",", "").strip()
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1].strip()
    if text.startswith("–") or text.startswith("−"):
        text = "-" + text[1:]
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        return None
    if not value.is_finite():
        return None
    return value


def normalize_office(raw: str) -> str:
    text = YEAR_PREFIX_RE.sub("", raw or "").strip()
    text = text.replace("’", "'")
    text = CONTINUATION_RE.sub("", text).strip()
    text = text.replace("&", " AND ")
    text = re.sub(r"\s+", " ", text).strip()
    return text.upper()


def is_hon_office(normalized: str) -> bool:
    return normalized.startswith("HON.") or normalized.startswith("HON ")


def legacy_office_group_key(normalized: str) -> str | None:
    """build_ladder.py office_group_key for HON. strings: HON:<SURNAME>."""
    rest = normalized.split(".", 1)[1] if normalized.startswith("HON.") else normalized[3:]
    cleaned = []
    for token in WORD_TOKEN_RE.findall(rest):
        token = token.strip(".").strip(",")
        if not token or token.upper() in OFFICE_SUFFIXES:
            continue
        cleaned.append(token)
    if not cleaned:
        return None
    surname = cleaned[-1]
    forms = {surname.upper()}
    if "-" in surname:
        for part in surname.split("-"):
            if len(part) > 2:
                forms.add(part.upper())
    return "HON:" + max(sorted(forms), key=len)


# ---------------------------------------------------------------------------
# Roster (pinned congress-legislators snapshot)
# ---------------------------------------------------------------------------

def load_roster(roster_root: Path) -> dict[str, Any]:
    import yaml  # PyYAML; precedent: build_tiered_corroboration_sidecar.py

    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    files = []
    people = 0
    for name in ("legislators-current.yaml", "legislators-historical.yaml"):
        path = roster_root / name
        with path.open("r", encoding="utf-8") as stream:
            data = yaml.load(stream, Loader=loader)
        files.append({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path), "people": len(data)})
        for entry in data:
            people += 1
            name_block = entry.get("name") or {}
            bioguide = (entry.get("id") or {}).get("bioguide")
            last = name_block.get("last")
            if not bioguide or not last:
                continue
            person = {
                "bioguide": str(bioguide),
                "first_norm": " ".join(name_tokens(str(name_block.get("first") or ""), False)),
                "nickname_norm": " ".join(name_tokens(str(name_block.get("nickname") or ""), False)),
                "terms": [
                    (str(term.get("type")), str(term.get("start")), str(term.get("end")))
                    for term in entry.get("terms") or []
                ],
            }
            index[" ".join(name_tokens(str(last), False))].append(person)
    for entries in index.values():
        entries.sort(key=lambda p: p["bioguide"])
    return {"index": dict(index), "people": people, "surnames": len(index), "files": files}


def rep_term_in_year(person: dict[str, Any], year: int) -> bool:
    first_day, last_day = f"{year:04d}-01-01", f"{year:04d}-12-31"
    for term_type, start, end in person["terms"]:
        if term_type != "rep" or not start or not end or start == "None" or end == "None":
            continue
        if start <= last_day and end >= first_day:
            return True
    return False


class OfficeResolver:
    """Container kind, office key and STRICT member resolution, cached per ORGANIZATION string."""

    def __init__(self, roster_index: dict[str, list[dict[str, Any]]]) -> None:
        self.index = roster_index
        self.cache: dict[str, dict[str, Any]] = {}

    def classify(self, organization_raw: str) -> dict[str, Any]:
        cached = self.cache.get(organization_raw)
        if cached is None:
            cached = self._classify(organization_raw)
            self.cache[organization_raw] = cached
        return cached

    def _classify(self, organization_raw: str) -> dict[str, Any]:
        match = ORG_PREFIX_RE.match(organization_raw)
        if match:
            allowance_year = int(match.group(2))
            allowance_year_kind = "FISCAL_YEAR" if match.group(1) else "LEGISLATIVE_YEAR"
            family_raw = match.group(3).strip()
        else:
            allowance_year = None
            allowance_year_kind = "NONE"
            family_raw = organization_raw.strip()
        family_norm = normalize_office(family_raw)
        base = {
            "allowance_year": allowance_year,
            "allowance_year_kind": allowance_year_kind,
            "office_family_raw": family_raw,
            "office_family_normalized": family_norm,
            "member_bioguide": None,
            "office_group_key_legacy": None,
            "member_resolution_evidence": None,
        }
        if is_hon_office(family_norm):
            base.update(self._resolve_hon(family_norm, allowance_year, allowance_year_kind))
            base["office_group_key_legacy"] = legacy_office_group_key(family_norm)
            return base
        if any(keyword in family_norm for keyword in LEADERSHIP_KEYWORDS):
            kind = "leadership"
        elif any(keyword in family_norm for keyword in COMMITTEE_KEYWORDS) or family_norm in COMMITTEE_BARE_FAMILIES:
            kind = "committee"
        elif allowance_year_kind == "FISCAL_YEAR":
            kind = "admin"
        else:
            kind = "other"
        base["container_kind"] = kind
        base["office_key"] = f"{kind.upper()}:{family_norm}"
        base["member_resolution_method"] = "NOT_A_MEMBER_OFFICE"
        return base

    def _resolve_hon(self, family_norm: str, year: int | None, year_kind: str) -> dict[str, Any]:
        rest = family_norm[4:] if family_norm.startswith("HON.") else family_norm[3:]
        quoted = QUOTED_NICKNAME_RE.findall(rest)
        rest_no_quotes = QUOTED_NICKNAME_RE.sub(" ", rest)
        tokens = name_tokens(rest_no_quotes, False)
        dropped = [t for t in tokens if len(t) == 1 or t in OFFICE_SUFFIXES or t in POST_NOMINALS]
        core = [t for t in tokens if not (len(t) == 1 or t in OFFICE_SUFFIXES or t in POST_NOMINALS)]
        evidence: dict[str, Any] = {
            "first_token": core[0] if core else None,
            "surname_candidates": [],
            "surname_matched": None,
            "year_candidate_count": 0,
            "first_hit_count": 0,
            "roster_nickname_would_match": False,
            "dropped_tokens": dropped,
            "quoted_nickname": quoted[0].strip() if quoted else None,
        }

        def unresolved(method: str, kind: str = "member_office_unresolved", prefix: str = "HONRAW:") -> dict[str, Any]:
            return {
                "container_kind": kind,
                "office_key": prefix + family_norm,
                "member_resolution_method": method,
                "member_resolution_evidence": evidence,
            }

        if any(t in VACANT_TOKENS for t in tokens):
            return unresolved("NOT_A_MEMBER_NAME_VACANT_SEAT_STRING", "vacant_seat", "VACANT:")
        if len(core) < 2:
            return unresolved("UNRESOLVED_SURNAME_NOT_PARSED")
        candidates = [" ".join(core[-k:]) for k in (3, 2, 1) if len(core) - k >= 1]
        evidence["surname_candidates"] = candidates
        matched = next((c for c in candidates if c in self.index), None)
        if matched is None:
            if any(t in CAUCUS_TOKENS for t in tokens):
                return unresolved("NOT_A_MEMBER_NAME_CAUCUS_STRING", "member_organization", "CAUCUS:")
            return unresolved("UNRESOLVED_SURNAME_NOT_IN_ROSTER")
        evidence["surname_matched"] = matched
        if year_kind != "LEGISLATIVE_YEAR" or year is None:
            return unresolved("UNRESOLVED_YEAR_KIND_NOT_LEGISLATIVE")
        first_token = core[0]
        year_candidates = [p for p in self.index[matched] if rep_term_in_year(p, year)]
        evidence["year_candidate_count"] = len(year_candidates)
        if not year_candidates:
            evidence["roster_nickname_would_match"] = any(p["nickname_norm"] == first_token for p in self.index[matched])
            return unresolved("UNRESOLVED_NO_REP_TERM_IN_YEAR")
        first_hits = [p for p in year_candidates if p["first_norm"] == first_token]
        evidence["first_hit_count"] = len(first_hits)
        if len(first_hits) == 1:
            return {
                "container_kind": "member_office",
                "office_key": "HON:" + first_hits[0]["bioguide"],
                "member_bioguide": first_hits[0]["bioguide"],
                "member_resolution_method": "STRICT_ROSTER_SURNAME_AND_FIRST_NAME",
                "member_resolution_evidence": evidence,
            }
        if len(first_hits) > 1:
            return unresolved("UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE")
        evidence["roster_nickname_would_match"] = any(p["nickname_norm"] == first_token for p in year_candidates)
        return unresolved("UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER")


# ---------------------------------------------------------------------------
# Sources: CSV files (and optional PDF-era rows) -> raw personnel rows
# ---------------------------------------------------------------------------

class CsvSource:
    """One quarterly detail CSV.  Streams rows; counts everything it does not admit."""

    def __init__(self, path: Path, quarter: str, sha256: str, source_url: str | None) -> None:
        self.path = path
        self.quarter = quarter
        self.sha256 = sha256
        self.source_url = source_url
        self.stats: dict[str, Any] = {}

    def iter_rows(self) -> Iterator[tuple[int, dict[str, str]]]:
        """Yield (data-row ordinal, stripped row dict) for every well-formed data row."""
        stats = {
            "data_rows": 0, "malformed_width_rows": 0, "malformed_width_ordinals": [],
            "shifted_rows_repaired": 0, "shifted_row_ordinals": [], "column_count": 0, "trailing_empty_column": False,
        }
        self.stats = stats
        with self.path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
            reader = csv.reader(stream)
            try:
                header = [h.strip() for h in next(reader)]
            except StopIteration:
                raise BuildError(f"{self.path.name}: empty file")
            extra_col = header[-1] == ""
            if extra_col:
                header = header[:-1]
            if header not in (SCHEMA_12, SCHEMA_18):
                raise BuildError(f"{self.path.name}: unknown header ({len(header)} cols): {header}")
            width = len(header)
            stats["column_count"] = width
            stats["trailing_empty_column"] = extra_col
            vendor_index = header.index("VENDOR NAME")
            for ordinal, row in enumerate(reader, 1):
                stats["data_rows"] += 1
                if extra_col and len(row) == width + 1:
                    if row[-1].strip() == "":
                        row = row[:-1]
                    else:
                        row = row[:vendor_index] + [row[vendor_index] + ", " + row[vendor_index + 1]] + row[vendor_index + 2:]
                        stats["shifted_rows_repaired"] += 1
                        if len(stats["shifted_row_ordinals"]) < 20:
                            stats["shifted_row_ordinals"].append(ordinal)
                if len(row) != width:
                    stats["malformed_width_rows"] += 1
                    if len(stats["malformed_width_ordinals"]) < 20:
                        stats["malformed_width_ordinals"].append(ordinal)
                    continue
                yield ordinal, {h: c.strip() for h, c in zip(header, row)}


def discover_csv_sources(csv_root: Path, url_inventory: dict[str, Any] | None) -> list[CsvSource]:
    urls: dict[str, str] = {}
    if url_inventory:
        for period in url_inventory.get("periods", []):
            if period.get("detail_csv_url"):
                urls[period["period"]] = period["detail_csv_url"]
    sources = []
    for path in sorted(csv_root.iterdir()):
        match = CSV_NAME_RE.match(path.name)
        if not match:
            continue
        quarter = f"{match.group('year')}Q{match.group('q')}"
        sources.append(CsvSource(path, quarter, sha256_file(path), urls.get(quarter)))
    sources.sort(key=lambda s: quarter_index(s.quarter))
    return sources


PDF_ROW_REQUIRED = (
    "period", "employing_office_raw", "payee_raw", "title_description_raw", "amount_raw",
    "service_start_date_raw", "service_end_date_raw", "source_pdf_page_number", "source_pdf_row_y_milli",
)


def iter_pdf_rows(path: Path) -> Iterator[tuple[int, dict[str, Any]]]:
    """Stream PDF-era candidate rows (lane schema v1/v2)."""
    last_index = -1
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for ordinal, line in enumerate(stream, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            missing = [k for k in PDF_ROW_REQUIRED if k not in row]
            if missing:
                raise BuildError(f"{path.name}:{ordinal}: PDF row lacks {missing}")
            index = quarter_index(row["period"])
            if index < last_index:
                raise BuildError(f"{path.name}:{ordinal}: PDF rows are not in ascending period order")
            last_index = index
            yield ordinal, row


# ---------------------------------------------------------------------------
# Per-row derivation (shared by both passes)
# ---------------------------------------------------------------------------

class Derived:
    __slots__ = (
        "quarter", "qi", "ordinal", "obs_id", "office", "payee", "person_key", "family_key", "middle_initial",
        "title_raw", "title_base", "compensation_class", "title_truncated", "start", "end", "start_raw", "end_raw",
        "service_days", "interval_vs_quarter", "amount", "amount_raw", "amount_sign", "organization_raw",
        "program", "flags", "source_form", "extra", "payee_raw_text", "row",
    )


def derive_csv_row(source: CsvSource, ordinal: int, row: dict[str, str], resolver: OfficeResolver,
                   bounds: tuple[dt.date, dt.date]) -> Derived:
    d = Derived()
    d.quarter = source.quarter
    d.qi = quarter_index(source.quarter)
    d.ordinal = ordinal
    d.obs_id = "sod:obs:" + sha256_bytes(canonical_bytes([source.sha256, ordinal]))
    d.organization_raw = row["ORGANIZATION"]
    d.office = resolver.classify(d.organization_raw)
    d.payee = parse_payee(row["VENDOR NAME"], False)
    d.person_key = d.payee["person_key"]
    d.family_key = d.payee["person_key_family"]
    d.middle_initial = d.payee["payee_parse"]["middle_initial"]
    d.title_raw = row["DESCRIPTION"]
    d.title_base, d.compensation_class, d.title_truncated = parse_title(d.title_raw)
    d.start_raw, d.end_raw = row["PERFORM START DT"], row["PERFORM END DT"]
    d.program = row["PROGRAM"]
    d.source_form = CSV_SOURCE_FORM
    d.amount_raw = row["AMOUNT"]
    d.extra = {
        "transaction_date": row["TRANSACTION DATE"] or None,
        "data_source": row["DATA SOURCE"] or None,
        "document": row["DOCUMENT"] or None,
        "vendor_id": row.get("VENDOR ID") or None,
        "organization_code": row.get("ORGANIZATION CODE") or None,
        "budget_object_code": row.get("BUDGET OBJECT CODE") or None,
        "fiscal_or_legislative_year_column": row.get("FISCAL YEAR OR LEGISLATIVE YEAR") or None,
        "source_locator": None,
    }
    _finish_derived(d, bounds)
    return d


def derive_pdf_row(path_name: str, file_sha: str, ordinal: int, row: dict[str, Any], resolver: OfficeResolver) -> Derived:
    d = Derived()
    d.quarter = row["period"]
    d.qi = quarter_index(d.quarter)
    d.ordinal = ordinal
    d.obs_id = "sod:obs:" + sha256_bytes(canonical_bytes([file_sha, ordinal]))
    d.organization_raw = str(row["employing_office_raw"])
    d.office = resolver.classify(d.organization_raw)
    d.payee = parse_payee(str(row["payee_raw"]), True)
    d.person_key = d.payee["person_key"]
    d.family_key = d.payee["person_key_family"]
    d.middle_initial = d.payee["payee_parse"]["middle_initial"]
    d.title_raw = str(row["title_description_raw"])
    d.title_base, d.compensation_class, d.title_truncated = parse_title(d.title_raw)
    d.start_raw = row.get("service_start_date_candidate_iso") or row.get("service_start_date_raw") or ""
    d.end_raw = row.get("service_end_date_candidate_iso") or row.get("service_end_date_raw") or ""
    d.program = None
    d.source_form = PDF_SOURCE_FORM
    d.amount_raw = str(row["amount_raw"])
    d.extra = {
        "transaction_date": None, "data_source": None, "document": None, "vendor_id": None,
        "organization_code": None, "budget_object_code": None, "fiscal_or_legislative_year_column": None,
        "source_locator": {
            "source_pdf_page_number": row["source_pdf_page_number"],
            "source_pdf_row_y_milli": row["source_pdf_row_y_milli"],
            "source_pdf_sha256": row.get("source_pdf_sha256"),
            "candidate_id": row.get("candidate_id"),
        },
    }
    _finish_derived(d, quarter_bounds(d.quarter))
    return d


def _finish_derived(d: Derived, bounds: tuple[dt.date, dt.date]) -> None:
    flags = list(d.payee["payee_parse"]["parse_flags"])
    start, end = parse_date(d.start_raw), parse_date(d.end_raw)
    d.start = start if isinstance(start, dt.date) else None
    d.end = end if isinstance(end, dt.date) else None
    if start == "UNPARSED" or end == "UNPARSED":
        flags.append("UNPARSED_SERVICE_DATE")
    if d.start and d.end:
        if d.end < d.start:
            d.interval_vs_quarter = "END_BEFORE_START"
            d.service_days = None
            flags.append("END_BEFORE_START")
        else:
            d.service_days = (d.end - d.start).days + 1
            q_start, q_end = bounds
            if d.end < q_start:
                d.interval_vs_quarter = "ENTIRELY_BEFORE_QUARTER"
                flags.append("RETROACTIVE_INTERVAL")
            elif d.start > q_end:
                d.interval_vs_quarter = "ENTIRELY_AFTER_QUARTER"
            elif d.start < q_start or d.end > q_end:
                d.interval_vs_quarter = "STRADDLES_QUARTER_EDGE"
            else:
                d.interval_vs_quarter = "WITHIN_QUARTER"
    else:
        d.service_days = None
        d.interval_vs_quarter = "UNPARSED" if (start == "UNPARSED" or end == "UNPARSED") else "EMPTY"
    d.amount = parse_amount(d.amount_raw)
    if d.amount is None:
        d.amount_sign = "UNPARSED"
        flags.append("UNPARSED_AMOUNT")
    elif d.amount < 0:
        d.amount_sign = "NEG"
        if d.compensation_class == "BASE":
            flags.append("NEGATIVE_BASE_ROW")
    elif d.amount == 0:
        d.amount_sign = "ZERO"
    else:
        d.amount_sign = "POS"
    d.flags = flags


# ---------------------------------------------------------------------------
# Cells (person_key, office_key, quarter)
# ---------------------------------------------------------------------------

class CellRow:
    __slots__ = ("obs_id", "ordinal", "compensation_class", "start", "end", "amount", "title_base", "title_raw",
                 "negative", "retroactive", "shared_title", "unparsed_date", "source_form")


class Cell:
    __slots__ = ("person_key", "office_key", "qi", "rows", "organization_raws", "container_kind", "member_bioguide",
                 "member_resolution_method", "office_group_key_legacy", "family_key", "flags")

    def __init__(self, person_key: str, office_key: str, qi: int, d: Derived) -> None:
        self.person_key = person_key
        self.office_key = office_key
        self.qi = qi
        self.rows: list[CellRow] = []
        self.organization_raws: set[str] = set()
        self.container_kind = d.office["container_kind"]
        self.member_bioguide = d.office["member_bioguide"]
        self.member_resolution_method = d.office["member_resolution_method"]
        self.office_group_key_legacy = d.office["office_group_key_legacy"]
        self.family_key = d.family_key
        self.flags: set[str] = set()

    def base_rows(self) -> list[CellRow]:
        return [r for r in self.rows if r.compensation_class == "BASE"]

    def base_intervals(self) -> list[tuple[dt.date, dt.date]]:
        return [(r.start, r.end) for r in self.rows if r.compensation_class == "BASE" and r.start and r.end and r.end >= r.start]

    def amount(self, compensation_class: str) -> Decimal:
        return sum((r.amount for r in self.rows if r.compensation_class == compensation_class and r.amount is not None), Decimal(0))


def merge_intervals(intervals: list[tuple[dt.date, dt.date]]) -> list[tuple[dt.date, dt.date]]:
    merged: list[tuple[dt.date, dt.date]] = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1] + dt.timedelta(days=1):
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def union_days(merged: list[tuple[dt.date, dt.date]]) -> int:
    return sum((end - start).days + 1 for start, end in merged)


def annualize(amount: Decimal, days: int) -> str | None:
    if days <= 0 or amount <= 0:
        return None
    return dec_str((amount / Decimal(days) * Decimal(365)).quantize(Decimal("0.01")))


ANNUALIZATION_BASIS = "BASE_ROWS_ONLY; DAYS=UNION_OF_INCLUSIVE_INTERVALS; YEAR=365"


def titles_prefix_equal(left: list[str], right: list[str]) -> bool:
    def covered(a: list[str], b: list[str]) -> bool:
        for t in a:
            if not any(t == u or (len(t) == 30 and u.startswith(t)) or (len(u) == 30 and t.startswith(u)) for u in b):
                return False
        return True
    return covered(left, right) and covered(right, left)


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------

class Ledger:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.output_root: Path = args.output_root
        self.csv_root: Path = args.csv_root
        self.pdf_rows_path: Path | None = args.pdf_rows
        self.roster_root: Path = args.roster_root
        self.run_id: str = args.run_id
        self.method_docs: list[Path] = list(args.method_doc or [])
        self.url_inventory_path: Path | None = args.url_inventory if args.url_inventory and args.url_inventory.is_file() else None

    # -- inputs ---------------------------------------------------------------

    def prepare(self) -> None:
        if self.output_root.exists():
            raise BuildError(f"immutable generation already exists: {self.output_root}")
        if not self.csv_root.is_dir():
            raise BuildError(f"csv root is not a directory: {self.csv_root}")
        url_inventory = None
        if self.url_inventory_path:
            url_inventory = json.loads(self.url_inventory_path.read_text(encoding="utf-8"))
        self.url_inventory = url_inventory
        self.sources = discover_csv_sources(self.csv_root, url_inventory)
        if not self.sources:
            raise BuildError(f"no *_sod_detail.csv files under {self.csv_root}")
        self.period_bounds: dict[str, tuple[dt.date, dt.date]] = {}
        for source in self.sources:
            computed = quarter_bounds(source.quarter)
            if url_inventory:
                for period in url_inventory.get("periods", []):
                    if period.get("period") == source.quarter and period.get("period_start") and period.get("period_end"):
                        listed = (dt.date.fromisoformat(period["period_start"]), dt.date.fromisoformat(period["period_end"]))
                        if listed != computed:
                            raise BuildError(f"{source.quarter}: url inventory period bounds {listed} differ from calendar quarter {computed}")
            self.period_bounds[source.quarter] = computed
        self.roster = load_roster(self.roster_root)
        self.resolver = OfficeResolver(self.roster["index"])
        self.pdf_sha = sha256_file(self.pdf_rows_path) if self.pdf_rows_path else None
        quarters = [s.quarter for s in self.sources]
        if len(set(quarters)) != len(quarters):
            raise BuildError("duplicate quarter among CSV sources")
        self.latest_qi = max(quarter_index(q) for q in quarters)
        self.latest_quarter = quarter_label(self.latest_qi)
        self.latest_quarter_published_known = None
        if url_inventory:
            coverage = url_inventory.get("coverage") or {}
            self.latest_quarter_published_known = coverage.get("last_detail_csv_period")

    # -- pass 1 ---------------------------------------------------------------

    def iter_derived(self, pass_label: str) -> Iterator[Derived]:
        """Every admitted personnel row, PDF-era rows first (ascending period), then CSVs ascending."""
        if self.pdf_rows_path:
            for ordinal, row in iter_pdf_rows(self.pdf_rows_path):
                d = derive_pdf_row(self.pdf_rows_path.name, self.pdf_sha, ordinal, row, self.resolver)
                if d.quarter not in self.period_bounds:
                    self.period_bounds[d.quarter] = quarter_bounds(d.quarter)
                yield d
        for source in self.sources:
            bounds = self.period_bounds[source.quarter]
            stats_key = source.quarter
            quarter_stats = self.quarter_stats[stats_key]
            try:
                for ordinal, row in source.iter_rows():
                    sequence = row["SORT SEQUENCE"].upper()
                    ssd = row["SORT SUBTOTAL DESCRIPTION"].upper()
                    if pass_label == "pass1":
                        quarter_stats["sort_sequence"][sequence] += 1
                        self._note_org(source.quarter, row)
                        if sequence == "SUBTOTAL" and ssd == PERSONNEL_CLASS and row["DESCRIPTION"].upper() == PERSONNEL_SUBTOTAL_DESCRIPTION:
                            amount = parse_amount(row["AMOUNT"])
                            if amount is None:
                                quarter_stats["unparsed_subtotal_amounts"] += 1
                            else:
                                self.subtotals[(source.quarter, row["ORGANIZATION"], row["PROGRAM"])].append(amount)
                    if sequence != "DETAIL" or ssd != PERSONNEL_CLASS:
                        continue
                    yield derive_csv_row(source, ordinal, row, self.resolver, bounds)
            except BuildError:
                raise
            except Exception as exc:  # never a silent skip: name the quarter and stop
                raise BuildError(f"{source.quarter} ({source.path.name}) failed to parse in {pass_label}: {exc!r}") from exc
            if pass_label == "pass1":
                quarter_stats["csv"] = dict(source.stats)

    def _note_org(self, quarter: str, row: dict[str, str]) -> None:
        """CSV pass-1 hook: every CSV row of every SORT SEQUENCE for a member container."""
        org = row["ORGANIZATION"]
        office = self.resolver.classify(org)
        if office["container_kind"] in MEMBER_CONTAINER_KINDS:
            entry = self.member_orgs_seen[(quarter, org)]
            entry["csv_rows"] += 1
            code = row.get("ORGANIZATION CODE")
            if code:
                entry["codes"].add(code)

    def _note_pdf_org(self, d: Derived) -> None:
        """PDF-era counterpart of _note_org.

        PDF rows never reach ``_note_org`` -- they are yielded straight out of
        ``iter_pdf_rows`` and carry no CSV row dict -- so without this the member-quarter
        output is blind to the PDF era.  Only admitted personnel rows exist in the PDF
        candidate file, so the counter is explicitly a personnel-row counter and the emitted
        row says so through ``rows_any_class_basis``.
        """
        if d.office["container_kind"] in MEMBER_CONTAINER_KINDS:
            self.member_orgs_seen[(d.quarter, d.organization_raw)]["pdf_personnel_rows"] += 1

    def pass1(self) -> None:
        self.quarter_stats: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "sort_sequence": Counter(), "admitted_rows": 0, "unparsed_subtotal_amounts": 0, "csv": {},
            "container_kind": Counter(), "compensation_class": Counter(), "interval_vs_quarter": Counter(),
            "flags": Counter(), "person_keys": set(), "office_keys": set(), "bioguides": set(),
            "hon_pairs": {}, "hon_rows": 0, "hon_rows_with_bioguide": 0, "source_form": Counter(),
        })
        self.subtotals: dict[tuple[str, str, str], list[Decimal]] = defaultdict(list)
        self.member_orgs_seen: dict[tuple[str, str], dict[str, Any]] = defaultdict(
            lambda: {"csv_rows": 0, "pdf_personnel_rows": 0, "codes": set()})
        self.cells: dict[tuple[str, str], dict[int, Cell]] = defaultdict(dict)
        self.person_quarter_offices: dict[tuple[str, int], set[str]] = defaultdict(set)
        self.person_quarter_kinds: dict[tuple[str, int], set[str]] = defaultdict(set)
        self.family_initials: dict[str, set[str]] = defaultdict(set)
        self.block_detail: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(lambda: {
            "rows": 0, "base_rows": 0, "sum": Decimal(0), "persons": set(), "shared_rows": 0,
            "other_comp_rows": 0, "overtime_rows": 0, "negative_rows": 0, "unkeyed_rows": 0,
        })
        self.block_source_forms: dict[tuple[str, str, str], set[str]] = defaultdict(set)
        self.total_admitted = 0
        for d in self.iter_derived("pass1"):
            self.total_admitted += 1
            qs = self.quarter_stats[d.quarter]
            qs["admitted_rows"] += 1
            qs["source_form"][d.source_form] += 1
            kind = d.office["container_kind"]
            qs["container_kind"][kind] += 1
            qs["compensation_class"][d.compensation_class] += 1
            qs["interval_vs_quarter"][d.interval_vs_quarter] += 1
            for flag in d.flags:
                qs["flags"][flag] += 1
            qs["office_keys"].add(d.office["office_key"])
            if d.office["member_bioguide"]:
                qs["bioguides"].add(d.office["member_bioguide"])
            if is_hon_office(d.office["office_family_normalized"]):
                qs["hon_rows"] += 1
                if d.office["member_bioguide"]:
                    qs["hon_rows_with_bioguide"] += 1
                pair = (d.office["allowance_year"], d.office["office_family_normalized"])
                qs["hon_pairs"][pair] = d.office["member_resolution_method"]
            if d.source_form != CSV_SOURCE_FORM:
                self._note_pdf_org(d)
            block_key = (d.quarter, d.organization_raw, d.program or "")
            self.block_source_forms[block_key].add(d.source_form)
            block = self.block_detail[block_key]
            block["rows"] += 1
            if d.amount is not None:
                block["sum"] += d.amount
            if d.compensation_class == "BASE":
                block["base_rows"] += 1
            elif d.compensation_class == "OTHER COMPENSATION":
                block["other_comp_rows"] += 1
            else:
                block["overtime_rows"] += 1
            if d.title_base == SHARED_TITLE:
                block["shared_rows"] += 1
            if d.amount_sign == "NEG":
                block["negative_rows"] += 1
            if d.person_key is None:
                block["unkeyed_rows"] += 1
                continue
            block["persons"].add(d.person_key)
            qs["person_keys"].add(d.person_key)
            self.family_initials[d.family_key].add(d.middle_initial)
            office_key = d.office["office_key"]
            cell = self.cells[(d.person_key, office_key)].get(d.qi)
            if cell is None:
                cell = Cell(d.person_key, office_key, d.qi, d)
                self.cells[(d.person_key, office_key)][d.qi] = cell
            row = CellRow()
            row.obs_id = d.obs_id
            row.ordinal = d.ordinal
            row.compensation_class = d.compensation_class
            row.start, row.end = d.start, d.end
            row.amount = d.amount
            row.title_base = sys.intern(d.title_base)
            row.title_raw = sys.intern(d.title_raw)
            row.negative = d.amount_sign == "NEG"
            row.retroactive = d.interval_vs_quarter == "ENTIRELY_BEFORE_QUARTER"
            row.shared_title = d.title_base == SHARED_TITLE
            row.unparsed_date = "UNPARSED_SERVICE_DATE" in d.flags
            row.source_form = d.source_form
            cell.rows.append(row)
            cell.organization_raws.add(sys.intern(d.organization_raw))
            cell.flags.update(d.flags)
            if d.compensation_class == "BASE":
                self.person_quarter_offices[(d.person_key, d.qi)].add(office_key)
            self.person_quarter_kinds[(d.person_key, d.qi)].add(kind)

    # -- cross-row flags ------------------------------------------------------

    def cross_row_flags(self) -> None:
        self.family_shape: dict[str, str] = {}
        self.family_link: dict[str, str] = {}
        shape_counter: Counter[str] = Counter()
        for family, initials in self.family_initials.items():
            nonempty = sorted(i for i in initials if i)
            if len(nonempty) > 1:
                shape = "FAMILY_MULTIPLE_MIDDLE_INITIALS"
            elif nonempty and "" in initials:
                shape = "FAMILY_ONE_INITIAL_PLUS_EMPTY"
                self.family_link[family] = f"SOD:{family[len('SODFAM:'):]}|{nonempty[0]}"
            elif nonempty:
                shape = "FAMILY_SINGLE_INITIAL_ONLY"
            else:
                shape = "FAMILY_EMPTY_ONLY"
            self.family_shape[family] = shape
            shape_counter[shape] += 1
        self.family_shape_histogram = dict(sorted(shape_counter.items()))

        # per-key single-office per-day maximum, then the two-office overlap heuristic
        per_day_max: dict[str, Decimal] = defaultdict(lambda: Decimal(0))
        cell_per_day: dict[tuple[str, str, int], Decimal] = {}
        for (person_key, office_key), by_q in self.cells.items():
            for qi, cell in by_q.items():
                merged = merge_intervals(cell.base_intervals())
                days = union_days(merged)
                base = cell.amount("BASE")
                if days > 0 and base > 0:
                    rate = base / Decimal(days)
                    cell_per_day[(person_key, office_key, qi)] = rate
                    if rate > per_day_max[person_key]:
                        per_day_max[person_key] = rate
        self.overlap_flagged: set[tuple[str, int]] = set()
        self.member_admin_flagged: set[tuple[str, int]] = set()
        self.orphan_cells: set[tuple[str, str, int]] = set()
        for (person_key, qi), offices in self.person_quarter_offices.items():
            if len(offices) < 2:
                continue
            office_list = sorted(offices)
            for i in range(len(office_list)):
                for j in range(i + 1, len(office_list)):
                    a = self.cells[(person_key, office_list[i])][qi]
                    b = self.cells[(person_key, office_list[j])][qi]
                    if any(r.shared_title for r in a.rows) or any(r.shared_title for r in b.rows):
                        continue
                    ia, ib = merge_intervals(a.base_intervals()), merge_intervals(b.base_intervals())
                    overlap = any(s1 <= e2 and s2 <= e1 for s1, e1 in ia for s2, e2 in ib)
                    if not overlap:
                        continue
                    rate = cell_per_day.get((person_key, office_list[i], qi), Decimal(0)) + cell_per_day.get((person_key, office_list[j], qi), Decimal(0))
                    if rate > per_day_max[person_key]:
                        self.overlap_flagged.add((person_key, qi))
        for (person_key, qi), kinds in self.person_quarter_kinds.items():
            if "member_office" in kinds and "admin" in kinds:
                self.member_admin_flagged.add((person_key, qi))
        for (person_key, office_key), by_q in self.cells.items():
            for qi, cell in by_q.items():
                if not cell.base_rows():
                    self.orphan_cells.add((person_key, office_key, qi))

    def row_flags(self, d: Derived) -> tuple[list[str], bool, str | None]:
        flags = set(d.flags)
        shared = d.title_base == SHARED_TITLE
        link = None
        if d.person_key is not None:
            key = (d.person_key, d.qi)
            if len(self.person_quarter_offices.get(key, ())) >= 2:
                shared = True
            shape = self.family_shape.get(d.family_key)
            if shape == "FAMILY_MULTIPLE_MIDDLE_INITIALS":
                flags.add("PERSON_KEY_FAMILY_COLLISION")
            elif shape == "FAMILY_ONE_INITIAL_PLUS_EMPTY":
                flags.add("MIDDLE_INITIAL_ABSENT_IN_FAMILY")
                if d.middle_initial == "":
                    link = self.family_link.get(d.family_key)
            if key in self.overlap_flagged:
                flags.add("SAME_KEY_OVERLAPPING_BASE_IN_TWO_NONSHARED_OFFICES")
            if key in self.member_admin_flagged:
                flags.add("SAME_KEY_MEMBER_AND_ADMIN_SAME_QUARTER")
            if (d.person_key, d.office["office_key"], d.qi) in self.orphan_cells:
                flags.add("ORPHAN_COMPENSATION_CELL")
        return sorted(flags), shared, link

    # -- pass 2: observations ---------------------------------------------------

    def observation_row(self, d: Derived, source_file: str, source_sha: str, source_url: str | None) -> dict[str, Any]:
        flags, shared, link = self.row_flags(d)
        q_start, q_end = self.period_bounds[d.quarter]
        row = {
            "schema_id": SCHEMA_OBSERVATION,
            "rule_version": RULE_VERSION,
            "observation_id": d.obs_id,
            "source_form": d.source_form,
            "row_admission": "CSV_DETAIL_PERSONNEL_COMPENSATION" if d.source_form == "detail_csv" else "PDF_LAYOUT_TEXT",
            "source_file": source_file,
            "source_url": source_url,
            "source_sha256": source_sha,
            "source_row_index": d.ordinal,
            "quarter": d.quarter,
            "report_period_start": q_start.isoformat(),
            "report_period_end": q_end.isoformat(),
            "office_raw": d.organization_raw,
            "allowance_year": d.office["allowance_year"],
            "allowance_year_kind": d.office["allowance_year_kind"],
            "office_family_raw": d.office["office_family_raw"],
            "office_family_normalized": d.office["office_family_normalized"],
            "container_kind": d.office["container_kind"],
            "office_key": d.office["office_key"],
            "office_group_key_legacy": d.office["office_group_key_legacy"],
            "member_bioguide": d.office["member_bioguide"],
            "member_resolution_method": d.office["member_resolution_method"],
            "member_resolution_evidence": d.office["member_resolution_evidence"],
            "payee_raw": d.payee_raw_text,
            "person_key": d.person_key,
            "person_key_family": d.family_key,
            "payee_parse": d.payee["payee_parse"],
            "family_link_candidate": link,
            "title_raw": d.title_raw,
            "title_base": d.title_base,
            "compensation_class": d.compensation_class,
            "title_truncated_30": d.title_truncated,
            "service_start_raw": d.start_raw or None,
            "service_end_raw": d.end_raw or None,
            "service_start": d.start.isoformat() if d.start else None,
            "service_end": d.end.isoformat() if d.end else None,
            "service_days": d.service_days,
            "interval_vs_quarter": d.interval_vs_quarter,
            "amount_raw": d.amount_raw,
            "amount": dec_str(d.amount) if d.amount is not None else None,
            "amount_sign": d.amount_sign,
            "program": d.program,
            "shared_employee_flag": shared,
            "review_flags": flags,
        }
        row.update(d.extra)
        row.update(INV)
        return row


def gold_payee(vendor: str) -> str:
    """METHOD_HOUSE_SOD_CSV section 6 fmt_payee: comma after the first whitespace token."""
    parts = vendor.split(" ", 1)
    return vendor if len(parts) == 1 else parts[0] + ", " + parts[1]


def gold_date(value: dt.date | None) -> str:
    return value.strftime("%m/%d/%y") if value else ""


class LedgerBuild(Ledger):
    """Concrete build: pass 2 (observations), spans, member quarters, receipt."""

    def pass2(self) -> None:
        self.source_by_quarter = {s.quarter: s for s in self.sources}
        self.kiley_rows = []
        self.observation_counts = Counter()
        self.rows_in_cells = 0
        self.rows_unkeyed = 0
        with DeterministicGzipWriter(self.output_root / OBSERVATIONS_NAME) as writer:
            for d in self._iter_pass2():
                writer.write(d.row)
                self.observation_counts[d.quarter] += 1
                if d.person_key is None:
                    self.rows_unkeyed += 1
                else:
                    self.rows_in_cells += 1
                if (d.quarter == GOLD_KILEY["quarter"] and d.organization_raw == GOLD_KILEY["organization"]
                        and d.program == MEMBER_PROGRAM):
                    self.kiley_rows.append([
                        gold_payee(d.row["payee_raw"]), gold_date(d.start), gold_date(d.end), d.title_raw,
                        f"{d.amount:,.2f}" if d.amount is not None else "",
                    ])
        self.observations_written = writer.rows

    def _iter_pass2(self) -> Iterator[Derived]:
        if self.pdf_rows_path:
            for ordinal, raw in iter_pdf_rows(self.pdf_rows_path):
                d = derive_pdf_row(self.pdf_rows_path.name, self.pdf_sha, ordinal, raw, self.resolver)
                d.payee_raw_text = str(raw["payee_raw"])
                d.row = self.observation_row(d, self.pdf_rows_path.name, self.pdf_sha, raw.get("source_url"))
                yield d
        for source in self.sources:
            bounds = self.period_bounds[source.quarter]
            try:
                for ordinal, raw in source.iter_rows():
                    if raw["SORT SEQUENCE"].upper() != "DETAIL" or raw["SORT SUBTOTAL DESCRIPTION"].upper() != PERSONNEL_CLASS:
                        continue
                    d = derive_csv_row(source, ordinal, raw, self.resolver, bounds)
                    d.payee_raw_text = raw["VENDOR NAME"]
                    d.row = self.observation_row(d, source.path.name, source.sha256, source.source_url)
                    yield d
            except BuildError:
                raise
            except Exception as exc:
                raise BuildError(f"{source.quarter} ({source.path.name}) failed to parse in pass2: {exc!r}") from exc

    # -- spans ----------------------------------------------------------------

    def build_spans(self) -> None:
        self.span_counts: Counter[str] = Counter()
        self.break_reasons: Counter[str] = Counter()
        self.span_status: Counter[str] = Counter()
        self.rows_in_spans = 0
        self.orphan_rows = 0
        self.span_person_keys: set[str] = set()
        with DeterministicGzipWriter(self.output_root / SPANS_NAME) as writer:
            for pair in sorted(self.cells):
                person_key, office_key = pair
                by_q = self.cells[pair]
                base_cells = [by_q[qi] for qi in sorted(by_q) if by_q[qi].base_rows()]
                for qi in by_q:
                    if not by_q[qi].base_rows():
                        self.orphan_rows += len(by_q[qi].rows)
                if not base_cells:
                    continue
                runs = self._chain(base_cells)
                spans = [self._span(person_key, office_key, run, index, len(runs)) for index, run in enumerate(runs, 1)]
                for i, span in enumerate(spans):
                    if span["break_reason"] == "DATE_GAP_WITHIN_CONSECUTIVE_QUARTERS" and i + 1 < len(spans):
                        nxt = spans[i + 1]
                        if span["service_end_max"] and nxt["service_start_min"]:
                            gap = (dt.date.fromisoformat(nxt["service_start_min"]) - dt.date.fromisoformat(span["service_end_max"])).days - 1
                            span["gap_days_to_next_span"] = max(0, gap)
                    span["run_count"] = len(spans)
                    writer.write(span)
                    self.span_counts["spans"] += 1
                    self.break_reasons[span["break_reason"]] += 1
                    self.span_status[span["status"]] += 1
                    self.rows_in_spans += len(span["observation_ids"])
                    self.span_person_keys.add(person_key)
        self.spans_written = writer.rows

    def _chain(self, base_cells: list[Cell]) -> list[dict[str, Any]]:
        runs: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for cell in base_cells:
            if current is None:
                current = self._open_run(cell, retro=False)
                continue
            last_qi = current["cells"][-1].qi
            if cell.qi == last_qi + 1:
                merged = merge_intervals(current["intervals"] + cell.base_intervals())
                if len(merged) <= 1:
                    current["cells"].append(cell)
                    current["intervals"] = merged
                    continue
                current["break_reason"] = "DATE_GAP_WITHIN_CONSECUTIVE_QUARTERS"
                runs.append(current)
                current = self._open_run(cell, retro=False)
            else:
                current["break_reason"] = "NEXT_QUARTER_ABSENT"
                current["gap_quarters"] = cell.qi - last_qi - 1
                runs.append(current)
                current = self._open_run(cell, retro=True)
        assert current is not None
        last_qi = current["cells"][-1].qi
        current["break_reason"] = "LATEST_QUARTER_REACHED" if last_qi == self.latest_qi else "NOT_OBSERVED_AFTER"
        runs.append(current)
        return runs

    def _open_run(self, cell: Cell, retro: bool) -> dict[str, Any]:
        intervals = merge_intervals(cell.base_intervals())
        run = {"cells": [cell], "intervals": intervals, "break_reason": None, "gap_quarters": None, "flags": set()}
        if retro and intervals:
            q_start = self.period_bounds[quarter_label(cell.qi)][0]
            if intervals[0][0] < q_start:
                run["flags"].add("RETROACTIVE_COVERAGE_ACROSS_BREAK")
        return run

    def _span(self, person_key: str, office_key: str, run: dict[str, Any], run_index: int, run_count: int) -> dict[str, Any]:
        cells: list[Cell] = run["cells"]
        merged = run["intervals"]
        quarters = [quarter_label(c.qi) for c in cells]
        obs_ids: list[str] = []
        titles_by_quarter = []
        title_examples: list[str] = []
        org_examples: list[str] = []
        shared_quarters = []
        annualized = []
        flags = set(run["flags"])
        base_total = other_total = overtime_total = Decimal(0)
        base_rows = other_rows = overtime_rows = negative_rows = retro_rows = 0
        source_forms: set[str] = set()
        all_titles: set[str] = set()
        for cell in cells:
            q = quarter_label(cell.qi)
            cell_titles = sorted({r.title_base for r in cell.rows if r.compensation_class == "BASE"})
            titles_by_quarter.append({"quarter": q, "titles": cell_titles})
            all_titles.update(cell_titles)
            for r in cell.rows:
                obs_ids.append(r.obs_id)
                source_forms.add(r.source_form)
                if r.title_raw not in title_examples and len(title_examples) < 3:
                    title_examples.append(r.title_raw)
                if r.compensation_class == "BASE":
                    base_rows += 1
                    if r.amount is not None:
                        base_total += r.amount
                    negative_rows += int(r.negative)
                    retro_rows += int(r.retroactive)
                elif r.compensation_class == "OTHER COMPENSATION":
                    other_rows += 1
                    if r.amount is not None:
                        other_total += r.amount
                else:
                    overtime_rows += 1
                    if r.amount is not None:
                        overtime_total += r.amount
            for org in sorted(cell.organization_raws):
                if org not in org_examples and len(org_examples) < 3:
                    org_examples.append(org)
            cell_shared = any(r.shared_title for r in cell.rows) or len(self.person_quarter_offices.get((person_key, cell.qi), ())) >= 2
            if cell_shared:
                shared_quarters.append(q)
            cell_merged = merge_intervals(cell.base_intervals())
            cell_days = union_days(cell_merged)
            cell_base = cell.amount("BASE")
            annualized.append({
                "quarter": q,
                "base_amount": dec_str(cell_base),
                "service_days_union": cell_days,
                "annualized_pay_office": annualize(cell_base, cell_days),
                "includes_retroactive_rows": any(r.retroactive for r in cell.rows if r.compensation_class == "BASE"),
            })
            flags.update(cell.flags)
            if (person_key, cell.qi) in self.overlap_flagged:
                flags.add("SAME_KEY_OVERLAPPING_BASE_IN_TWO_NONSHARED_OFFICES")
            if (person_key, cell.qi) in self.member_admin_flagged:
                flags.add("SAME_KEY_MEMBER_AND_ADMIN_SAME_QUARTER")
        shape = self.family_shape.get(cells[0].family_key)
        if shape == "FAMILY_MULTIPLE_MIDDLE_INITIALS":
            flags.add("PERSON_KEY_FAMILY_COLLISION")
        elif shape == "FAMILY_ONE_INITIAL_PLUS_EMPTY":
            flags.add("MIDDLE_INITIAL_ABSENT_IN_FAMILY")
        if len(source_forms) > 1:
            flags.add("SPAN_MIXES_SOURCE_FORMS")
        if not merged:
            flags.add("SPAN_NO_PARSEABLE_DATES")
        title_events = []
        for prev, cur in zip(titles_by_quarter, titles_by_quarter[1:]):
            if prev["titles"] != cur["titles"]:
                title_events.append({
                    "quarter": cur["quarter"], "from": prev["titles"], "to": cur["titles"],
                    "comparability": "TRUNCATED_PREFIX_EQUAL" if titles_prefix_equal(prev["titles"], cur["titles"]) else "EXACT",
                })
        days = union_days(merged)
        start = merged[0][0] if merged else None
        end = merged[-1][1] if merged else None
        last_quarter = quarters[-1]
        observed_latest = cells[-1].qi == self.latest_qi
        span_id = "sod:span:" + sha256_bytes(canonical_bytes([person_key, office_key, quarters[0], start.isoformat() if start else None]))
        return {
            "schema_id": SCHEMA_SPAN,
            "rule_version": RULE_VERSION,
            "span_id": span_id,
            "person_key": person_key,
            "person_key_family": cells[0].family_key,
            "office_key": office_key,
            "container_kind": cells[0].container_kind,
            "member_bioguide": cells[0].member_bioguide,
            "member_resolution_method": cells[0].member_resolution_method,
            "office_group_key_legacy": cells[0].office_group_key_legacy,
            "office_raw_examples": org_examples,
            "source_forms": sorted(source_forms),
            "run_index": run_index,
            "run_count": run_count,
            "first_report_quarter": quarters[0],
            "last_report_quarter": last_quarter,
            "quarters_observed": quarters,
            "quarters_count": len(quarters),
            "service_start_min": start.isoformat() if start else None,
            "service_end_max": end.isoformat() if end else None,
            "service_days_union": days,
            "contiguous": len(merged) == 1,
            "interval": {
                "start_earliest": start.isoformat() if start else None,
                "start_latest": start.isoformat() if start else None,
                "end_earliest": (end + dt.timedelta(days=1)).isoformat() if end else None,
                "end_latest": (end + dt.timedelta(days=1)).isoformat() if end else None,
                "start_precision": "day",
                "end_precision": "day",
                "asserted_current": False,
            },
            "break_reason": run["break_reason"],
            "gap_days_to_next_span": None,
            "gap_quarters_to_next_span": run["gap_quarters"],
            "observed_in_latest_quarter": observed_latest,
            "status": "current" if observed_latest else "departed_or_unobserved",
            "status_basis": "current = span reaches latest_quarter_on_disk; otherwise departed_or_unobserved (not asserted as departure)",
            "latest_quarter_on_disk": self.latest_quarter,
            "titles": sorted(all_titles),
            "titles_by_quarter": titles_by_quarter,
            "title_examples": title_examples,
            "title_change_events": title_events,
            "shared_employee_quarters": shared_quarters,
            "amount_sum": dec_str(base_total + other_total + overtime_total),
            "base_amount_total": dec_str(base_total),
            "other_comp_amount_total": dec_str(other_total),
            "overtime_amount_total": dec_str(overtime_total),
            "base_row_count": base_rows,
            "other_comp_row_count": other_rows,
            "overtime_row_count": overtime_rows,
            "negative_base_row_count": negative_rows,
            "retroactive_row_count": retro_rows,
            "annualized_estimate": annualize(base_total, days),
            "annualization_basis": ANNUALIZATION_BASIS,
            "annualized_pay_by_quarter": annualized,
            "observation_ids": obs_ids,
            "support_digest": sha256_bytes(canonical_bytes(sorted(obs_ids))),
            "review_flags": sorted(flags),
            **INV,
        }

    # -- member quarters ----------------------------------------------------------

    def build_member_quarters(self) -> None:
        self.member_quarter_counts: Counter[str] = Counter()
        self.reconciliation: dict[str, Counter[str]] = defaultdict(Counter)
        self.reconciliation_examples: list[dict[str, Any]] = []
        # every (quarter, org, program) block with detail rows or a subtotal row
        block_keys = set(self.block_detail) | set(self.subtotals)
        self.block_status: dict[tuple[str, str, str], dict[str, Any]] = {}
        for key in sorted(block_keys):
            quarter = key[0]
            detail = self.block_detail.get(key)
            subs = self.subtotals.get(key, [])
            detail_sum = detail["sum"] if detail else Decimal(0)
            sub_sum = sum(subs, Decimal(0))
            if detail and subs:
                if len(subs) > 1:
                    status = "MULTI_SUBTOTAL_ROWS"
                elif detail_sum == sub_sum:
                    status = "RECONCILED"
                else:
                    status = "MISMATCH"
            elif detail:
                status = "NO_SUBTOTAL_ROW"
            else:
                status = "SUBTOTAL_WITHOUT_DETAIL_ROWS"
            self.block_status[key] = {"status": status, "detail_sum": detail_sum, "subtotal_sum": sub_sum, "subtotal_rows": len(subs)}
            self.reconciliation[quarter][status] += 1
            if status != "RECONCILED" and len(self.reconciliation_examples) < 40:
                self.reconciliation_examples.append({
                    "quarter": quarter, "organization": key[1], "program": key[2], "status": status,
                    "detail_sum": dec_str(detail_sum), "subtotal_sum": dec_str(sub_sum), "subtotal_rows": len(subs),
                    "detail_rows": detail["rows"] if detail else 0,
                })
        self.member_quarter_era_counts: Counter[str] = Counter()
        self.member_quarter_office_keys_by_era: dict[str, set[str]] = defaultdict(set)
        self.member_quarter_offices_by_era: dict[str, set[str]] = defaultdict(set)
        # Group block_keys by (quarter, org) once so the per-office loop below is a dict
        # lookup instead of a full block_keys scan: the scan was O(offices x blocks), the
        # lookup makes the whole phase O(offices + blocks).
        blocks_by_office: dict[tuple[str, str], list[tuple[str, str, str]]] = defaultdict(list)
        for key in block_keys:
            blocks_by_office[(key[0], key[1])].append(key)
        with DeterministicGzipWriter(self.output_root / MEMBER_QUARTERS_NAME) as writer:
            for (quarter, org) in sorted(self.member_orgs_seen, key=lambda k: (quarter_index(k[0]), k[1])):
                seen = self.member_orgs_seen[(quarter, org)]
                office = self.resolver.classify(org)
                # Era is decided by which source form the office was observed through, not by the
                # quarter label: a corrected --pdf-rows extraction is free to overlap the CSV era.
                if seen["csv_rows"] and seen["pdf_personnel_rows"]:
                    era, source_form = ERA_MIXED, CSV_SOURCE_FORM + "+" + PDF_SOURCE_FORM
                    rows_basis = ROWS_BASIS_MIXED
                elif seen["pdf_personnel_rows"]:
                    era, source_form, rows_basis = ERA_PDF, PDF_SOURCE_FORM, ROWS_BASIS_PDF
                else:
                    era, source_form, rows_basis = ERA_CSV, CSV_SOURCE_FORM, ROWS_BASIS_CSV
                programs = []
                oem = None
                intern = None
                pdf_block = None
                for key in sorted(blocks_by_office.get((quarter, org), ())):
                    detail = self.block_detail.get(key)
                    status = self.block_status[key]
                    forms = self.block_source_forms.get(key, set())
                    pdf_only_block = bool(forms) and forms == {PDF_SOURCE_FORM}
                    entry = {
                        # The PDF schema has no PROGRAM column; its block key is the empty
                        # string, which is reported as null rather than as a program named "".
                        "program": None if pdf_only_block else key[2],
                        "source_forms": sorted(forms),
                        "personnel_row_count": detail["rows"] if detail else 0,
                        "base_row_count": detail["base_rows"] if detail else 0,
                        "other_comp_row_count": detail["other_comp_rows"] if detail else 0,
                        "overtime_row_count": detail["overtime_rows"] if detail else 0,
                        "shared_employee_title_rows": detail["shared_rows"] if detail else 0,
                        "negative_rows": detail["negative_rows"] if detail else 0,
                        "unkeyed_rows": detail["unkeyed_rows"] if detail else 0,
                        "distinct_person_keys": len(detail["persons"]) if detail else 0,
                        "personnel_detail_sum": dec_str(status["detail_sum"]),
                        "personnel_subtotal_rows": status["subtotal_rows"],
                        "personnel_subtotal_sum": dec_str(status["subtotal_sum"]),
                        "reconciliation": status["status"],
                    }
                    programs.append(entry)
                    if pdf_only_block:
                        pdf_block = entry
                    elif key[2] == MEMBER_PROGRAM:
                        oem = entry
                    elif key[2] == INTERN_PROGRAM:
                        intern = entry
                # Which block supplies the row-level scalars.  CSV/MIXED: the OFFICIAL EXPENSES
                # OF MEMBERS program block, as before.  PDF: the single programless block, which
                # is all this era publishes.
                if era == ERA_PDF:
                    scalar = pdf_block
                    program_field = None
                    staff_basis = STAFF_BASIS_PDF
                    subtotal_basis = SUBTOTAL_BASIS_PDF if scalar else SUBTOTAL_BASIS_NO_BLOCK
                    # The PDF era has no INTERN ALLOWANCES block to be zero: interns are not
                    # separable from staff here, so the intern fields are null, never 0.
                    intern_rows: int | None = None
                    intern_sum: str | None = None
                else:
                    scalar = oem
                    program_field = MEMBER_PROGRAM if oem else None
                    staff_basis = STAFF_BASIS_CSV
                    if not oem:
                        subtotal_basis = SUBTOTAL_BASIS_NO_BLOCK
                    elif oem["personnel_subtotal_rows"] > 0:
                        subtotal_basis = SUBTOTAL_BASIS_CSV_ROW
                    else:
                        subtotal_basis = SUBTOTAL_BASIS_CSV_ABSENT
                    intern_rows = intern["personnel_row_count"] if intern else 0
                    intern_sum = intern["personnel_detail_sum"] if intern else "0"
                # A block with zero published subtotal rows reports null, not "0": a subtotal
                # that was never published is absent, not zero.
                subtotal_total = (
                    scalar["personnel_subtotal_sum"] if scalar and scalar["personnel_subtotal_rows"] > 0 else None
                )
                row = {
                    "schema_id": SCHEMA_MEMBER_QUARTER,
                    "rule_version": RULE_VERSION,
                    "quarter": quarter,
                    "office_raw": org,
                    "era": era,
                    "source_form": source_form,
                    "program": program_field,
                    "subtotal_basis": subtotal_basis,
                    "allowance_year": office["allowance_year"],
                    "allowance_year_kind": office["allowance_year_kind"],
                    "office_family_normalized": office["office_family_normalized"],
                    "office_key": office["office_key"],
                    "container_kind": office["container_kind"],
                    "member_bioguide": office["member_bioguide"],
                    "member_resolution_method": office["member_resolution_method"],
                    "office_group_key_legacy": office["office_group_key_legacy"],
                    "organization_codes": sorted(seen["codes"]),
                    "rows_any_class": seen["csv_rows"] + seen["pdf_personnel_rows"],
                    "rows_any_class_basis": rows_basis,
                    "staff_count": scalar["distinct_person_keys"] if scalar else 0,
                    "staff_count_basis": staff_basis,
                    "personnel_row_count": scalar["personnel_row_count"] if scalar else 0,
                    "personnel_total": scalar["personnel_detail_sum"] if scalar else "0",
                    "personnel_subtotal_row_total": subtotal_total,
                    "personnel_reconciliation": scalar["reconciliation"] if scalar else "NO_PERSONNEL_BLOCK",
                    "intern_row_count": intern_rows,
                    "intern_total": intern_sum,
                    "programs": programs,
                    **INV,
                }
                writer.write(row)
                self.member_quarter_counts[quarter] += 1
                self.member_quarter_era_counts[era] += 1
                self.member_quarter_office_keys_by_era[era].add(office["office_key"])
                self.member_quarter_offices_by_era[era].add(org)
        self.member_quarters_written = writer.rows

    # -- receipt ----------------------------------------------------------------

    def kiley_check(self) -> dict[str, Any]:
        if GOLD_KILEY["quarter"] not in self.period_bounds:
            return {"status": "NOT_RUN_QUARTER_ABSENT", "quarter": GOLD_KILEY["quarter"]}
        rows = self.kiley_rows
        matches = sum(1 for a, b in zip(rows, GOLD_KILEY["rows"]) if a == b)
        detail_sum = sum((Decimal(r[4].replace(",", "")) for r in rows if r[4]), Decimal(0))
        subtotal = self.subtotals.get((GOLD_KILEY["quarter"], GOLD_KILEY["organization"], MEMBER_PROGRAM), [])
        subtotal_text = f"{subtotal[0]:,.2f}" if len(subtotal) == 1 else None
        detail_text = f"{detail_sum:,.2f}"
        ok = (rows == GOLD_KILEY["rows"] and detail_text == GOLD_KILEY["personnel_total"]
              and subtotal_text == GOLD_KILEY["personnel_total"])
        return {
            "status": "PASS" if ok else "FAIL",
            "member": GOLD_KILEY["member"],
            "organization": GOLD_KILEY["organization"],
            "quarter": GOLD_KILEY["quarter"],
            "gold_rows": len(GOLD_KILEY["rows"]),
            "reproduced_rows": len(rows),
            "rows_matched_in_order": matches,
            "personnel_total_gold": GOLD_KILEY["personnel_total"],
            "personnel_total_from_detail_sum": detail_text,
            "personnel_total_from_subtotal_row": subtotal_text,
            "mismatches": [{"index": i, "gold": g, "reproduced": r} for i, (g, r) in enumerate(zip(GOLD_KILEY["rows"], rows)) if g != r][:15],
        }

    def receipt(self) -> dict[str, Any]:
        outputs = []
        for name, role, rows in (
            (OBSERVATIONS_NAME, "personnel_observations", self.observations_written),
            (SPANS_NAME, "person_office_spans", self.spans_written),
            (MEMBER_QUARTERS_NAME, "member_office_quarters", self.member_quarters_written),
        ):
            path = self.output_root / name
            outputs.append({"path": name, "role": role, "rows": rows, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        per_quarter = {}
        total_pairs = total_resolved = 0
        all_bioguides: set[str] = set()
        all_persons: set[str] = set()
        all_offices: set[str] = set()
        hon_rows_total = hon_rows_bioguide = 0
        for quarter in sorted(self.quarter_stats, key=quarter_index):
            qs = self.quarter_stats[quarter]
            histogram = Counter(qs["hon_pairs"].values())
            pairs = len(qs["hon_pairs"])
            resolved = histogram.get("STRICT_ROSTER_SURNAME_AND_FIRST_NAME", 0)
            total_pairs += pairs
            total_resolved += resolved
            all_bioguides.update(qs["bioguides"])
            all_persons.update(qs["person_keys"])
            all_offices.update(qs["office_keys"])
            hon_rows_total += qs["hon_rows"]
            hon_rows_bioguide += qs["hon_rows_with_bioguide"]
            per_quarter[quarter] = {
                "admitted_rows": qs["admitted_rows"],
                "observations_written": self.observation_counts.get(quarter, 0),
                "source_form": dict(sorted(qs["source_form"].items())),
                "csv": qs["csv"],
                "sort_sequence": dict(sorted(qs["sort_sequence"].items())),
                "container_kind": dict(sorted(qs["container_kind"].items())),
                "compensation_class": dict(sorted(qs["compensation_class"].items())),
                "interval_vs_quarter": dict(sorted(qs["interval_vs_quarter"].items())),
                "review_flags": dict(sorted(qs["flags"].items())),
                "distinct_person_keys": len(qs["person_keys"]),
                "distinct_office_keys": len(qs["office_keys"]),
                "distinct_member_bioguides": len(qs["bioguides"]),
                "hon_pairs_distinct": pairs,
                "hon_pairs_resolved": resolved,
                "hon_pair_resolution_rate": round(resolved / pairs, 4) if pairs else None,
                "hon_pair_resolution_histogram": dict(sorted(histogram.items())),
                "hon_rows": qs["hon_rows"],
                "hon_rows_with_bioguide": qs["hon_rows_with_bioguide"],
                "hon_row_resolution_rate": round(qs["hon_rows_with_bioguide"] / qs["hon_rows"], 4) if qs["hon_rows"] else None,
                "member_quarter_rows": self.member_quarter_counts.get(quarter, 0),
                "personnel_block_reconciliation": dict(sorted(self.reconciliation.get(quarter, Counter()).items())),
                "unparsed_subtotal_amounts": qs["unparsed_subtotal_amounts"],
            }
        reconciliation_total: Counter[str] = Counter()
        for counter in self.reconciliation.values():
            reconciliation_total.update(counter)
        kiley = self.kiley_check()
        conservation = {
            "observations_total": self.observations_written,
            "observations_with_person_key": self.rows_in_cells,
            "observations_without_person_key": self.rows_unkeyed,
            "observations_in_spans": self.rows_in_spans,
            "observations_in_orphan_cells": self.orphan_rows,
            "identity_holds": self.rows_in_spans + self.orphan_rows == self.rows_in_cells,
        }
        quarters_failed: list[str] = []
        # A quarter that admitted member-container personnel rows must appear in the
        # member-quarter output.  This is the tripwire for the PDF-era blind spot: before the
        # PDF rows were routed through the member-org note, all 26 PDF quarters admitted
        # member_office rows and emitted 0 member-quarter rows.
        member_quarter_gaps = sorted(
            quarter for quarter, qs in self.quarter_stats.items()
            if any(qs["container_kind"].get(kind, 0) for kind in MEMBER_CONTAINER_KINDS)
            and self.member_quarter_counts.get(quarter, 0) == 0
        )
        invariant_checks = {
            "canonical_promotions_zero": True,
            "every_row_carries_inv_block": True,
            "observation_count_equals_admitted": self.observations_written == self.total_admitted,
            "per_quarter_counts_equal": all(per_quarter[q]["admitted_rows"] == per_quarter[q]["observations_written"] for q in per_quarter),
            "observation_conservation": conservation["identity_holds"],
            "kiley_gold_check_pass": kiley["status"] != "FAIL",
            "no_quarter_failed_to_parse": not quarters_failed,
            "no_unknown_csv_header": True,
            "every_quarter_with_member_office_rows_has_member_quarters": not member_quarter_gaps,
        }
        status = "PASS" if all(invariant_checks.values()) else "FAIL"
        pdf_note = (
            {"status": "INGESTED", "path": str(self.pdf_rows_path), "sha256": self.pdf_sha}
            if self.pdf_rows_path else
            {
                "status": "NOT_INGESTED_CSV_ONLY",
                "reason": (
                    "The on-disk PDF-era extraction (house_sod_payroll_20260831/house_sod_payroll_pdf_candidates.ndjson.gz and the "
                    "generation1 personnel-scope repair) is not usable as tenure evidence by the lane's own measurement "
                    "(METHOD_HOUSE_SOD_PDF.md section 3.1): rows after a mid-section page break are dropped (3,266 rows in 2009Q3, "
                    "3,021 in 2015Q4), en-dash negatives are absent, bare page numbers are accepted as amounts (160 rows in 2009Q3), "
                    "dates bleed into payee strings (1,403 rows) and DO ditto rows are unresolved (461). A missing quarter breaks a "
                    "span, so ingesting those rows would manufacture tenure breaks. --pdf-rows accepts a corrected extraction in the "
                    "lane's candidate schema."
                ),
            }
        )
        return {
            "schema_id": SCHEMA_RECEIPT,
            "run_id": self.run_id,
            "rule_version": RULE_VERSION,
            "status": status,
            "generator": "audits/staffer_network/build_house_personnel_ledger.py",
            "methods": {
                "csv": "METHOD_HOUSE_SOD_CSV.md",
                "tracking": "METHOD_STAFFER_TRACKING.md",
                "row_admission": "SORT SEQUENCE == DETAIL AND SORT SUBTOTAL DESCRIPTION == PERSONNEL COMPENSATION (all offices, all programs)",
                "member_office_personnel_total": (
                    "CSV era: OFFICIAL EXPENSES OF MEMBERS program only, INTERN ALLOWANCES reported separately. "
                    "PDF era: the single programless block of admitted PDF personnel rows, because the PDF schema "
                    "publishes no PROGRAM column and no subtotal row; such rows carry era=PDF, program=null, "
                    "subtotal_basis=NO_SUBTOTAL_ROW_PDF_ERA, source_form=house_gov_single_volume_pdf, a null "
                    "personnel_subtotal_row_total and null intern fields.  No subtotal and no program split is "
                    "ever manufactured for the PDF era."),
                "person_key": "SOD:<SURNAME>|<GIVEN>|<MIDDLE_INITIAL> from the positional payee parse; NAME key only",
                "office_key": "HON:<bioguide> under STRICT surname+first-name+rep-term-in-year; otherwise HONRAW:/VACANT:/CAUCUS:/<KIND>:",
                "span": "consecutive report quarters, 0-day gap tolerance over the union of BASE service intervals; a missing quarter breaks",
                "source_row_index": "1-based data-row ordinal in the CSV, header excluded",
                "rule_deviations_from_method_text": RULE_DEVIATIONS,
            },
            "inputs": {
                "csv_root": str(self.csv_root),
                "csv_files": [
                    {"path": s.path.name, "quarter": s.quarter, "bytes": s.path.stat().st_size, "sha256": s.sha256, "source_url": s.source_url}
                    for s in self.sources
                ],
                "roster": {"root": str(self.roster_root), "files": self.roster["files"], "people": self.roster["people"], "surnames": self.roster["surnames"]},
                "url_inventory": (
                    {"path": str(self.url_inventory_path), "sha256": sha256_file(self.url_inventory_path)}
                    if self.url_inventory_path else None
                ),
                "method_docs": [
                    {"path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in self.method_docs if p.is_file()
                ],
                "pdf_era": pdf_note,
            },
            "quarters": {
                "count": len(per_quarter),
                "first": min(per_quarter, key=quarter_index) if per_quarter else None,
                "latest_quarter_on_disk": self.latest_quarter,
                "latest_quarter_published_known": self.latest_quarter_published_known,
                "failed_to_parse": quarters_failed,
            },
            "per_quarter": per_quarter,
            "totals": {
                "admitted_rows": self.total_admitted,
                "observations": self.observations_written,
                "spans": self.spans_written,
                "member_quarter_rows": self.member_quarters_written,
                "member_quarter_rows_by_era": dict(sorted(self.member_quarter_era_counts.items())),
                "member_quarter_distinct_offices_raw_by_era": {
                    era: len(v) for era, v in sorted(self.member_quarter_offices_by_era.items())},
                "member_quarter_distinct_office_keys_by_era": {
                    era: len(v) for era, v in sorted(self.member_quarter_office_keys_by_era.items())},
                "member_quarter_quarters_without_rows_despite_member_office_rows": member_quarter_gaps,
                "distinct_person_keys": len(all_persons),
                "distinct_person_keys_with_spans": len(self.span_person_keys),
                "distinct_office_keys": len(all_offices),
                "distinct_member_bioguides": len(all_bioguides),
                "hon_pairs_distinct_sum_over_quarters": total_pairs,
                "hon_pairs_resolved_sum_over_quarters": total_resolved,
                "hon_pair_resolution_rate": round(total_resolved / total_pairs, 4) if total_pairs else None,
                "hon_rows": hon_rows_total,
                "hon_rows_with_bioguide": hon_rows_bioguide,
                "hon_row_resolution_rate": round(hon_rows_bioguide / hon_rows_total, 4) if hon_rows_total else None,
                "person_key_family_shape_histogram": self.family_shape_histogram,
                "span_break_reason_histogram": dict(sorted(self.break_reasons.items())),
                "span_status_histogram": dict(sorted(self.span_status.items())),
                "personnel_block_reconciliation": dict(sorted(reconciliation_total.items())),
            },
            "personnel_block_reconciliation_examples": self.reconciliation_examples,
            "observation_conservation": conservation,
            "kiley_gold_check": kiley,
            "invariant_checks": invariant_checks,
            "invariants": {**INV_COUNTS, "row_inv_block": INV},
            "determinism": "Canonical sorted-key ASCII JSON, ascending quarter then source row order, gzip mtime=0, blank embedded filename, atomic replace; no timestamps.",
            "risk_notes": [
                "Service dates describe the coverage of a disbursement and must not be treated as complete employment-tenure boundaries.",
                "person_key is a normalized name string; identical keys are a review queue, not an identity decision.",
                "departed_or_unobserved means the key was not observed in the latest quarter on disk; it is not a departure assertion.",
                "Member offices are keyed by bioguide only under the STRICT rule; unresolved HON. strings stay HONRAW: keys.",
                "PDF-era member-quarter rows carry era=PDF and a null program: the PDF schema publishes no program "
                "split and no subtotal row, so their personnel_total is not comparable to a CSV-era RECONCILED total.",
            ],
            "outputs": outputs,
        }

    def run(self) -> dict[str, Any]:
        self.prepare()
        self.output_root.mkdir(parents=True, exist_ok=False)
        self.pass1()
        self.cross_row_flags()
        self.pass2()
        self.build_spans()
        self.build_member_quarters()
        receipt = self.receipt()
        atomic_write_bytes(self.output_root / RECEIPT_NAME, json.dumps(receipt, ensure_ascii=True, sort_keys=True, indent=1).encode("utf-8") + b"\n")
        return receipt


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT, help="immutable generation directory (must not exist)")
    parser.add_argument("--csv-root", type=Path, default=DEFAULT_CSV_ROOT, help="directory of <yyyy>q<n>_sod_detail.csv files")
    parser.add_argument("--pdf-rows", type=Path, default=None, help="optional PDF-era personnel rows (.ndjson.gz, lane candidate schema)")
    parser.add_argument("--roster-root", type=Path, default=DEFAULT_ROSTER_ROOT, help="pinned congress-legislators snapshot directory")
    parser.add_argument("--url-inventory", type=Path, default=DEFAULT_URL_INVENTORY, help="house_sod_url_inventory.json (source URLs, period bounds)")
    parser.add_argument("--method-doc", type=Path, action="append", help="method document to pin (sha256) in the receipt; repeatable")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    args = parser.parse_args(argv)
    args.output_root = args.output_root.resolve()
    args.csv_root = args.csv_root.resolve()
    args.roster_root = args.roster_root.resolve()
    if args.pdf_rows is not None:
        args.pdf_rows = args.pdf_rows.resolve()
    if args.url_inventory is not None:
        args.url_inventory = args.url_inventory.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        receipt = LedgerBuild(args).run()
    except BuildError as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 2
    summary = {
        "status": receipt["status"],
        "quarters": receipt["quarters"]["count"],
        "observations": receipt["totals"]["observations"],
        "spans": receipt["totals"]["spans"],
        "member_quarter_rows": receipt["totals"]["member_quarter_rows"],
        "member_quarter_rows_by_era": receipt["totals"]["member_quarter_rows_by_era"],
        "distinct_person_keys": receipt["totals"]["distinct_person_keys"],
        "distinct_member_bioguides": receipt["totals"]["distinct_member_bioguides"],
        "hon_pair_resolution_rate": receipt["totals"]["hon_pair_resolution_rate"],
        "kiley_gold_check": receipt["kiley_gold_check"]["status"],
        "reconciliation": receipt["totals"]["personnel_block_reconciliation"],
        "quarters_failed_to_parse": receipt["quarters"]["failed_to_parse"],
        "outputs": [(o["path"], o["rows"], o["sha256"]) for o in receipt["outputs"]],
    }
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
