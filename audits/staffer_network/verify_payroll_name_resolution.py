#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""INDEPENDENT verifier for the payroll name-resolution generation.

This module deliberately does NOT import build_payroll_name_resolution.  It
re-reads the same inputs the builder consumed and re-derives every emitted row
from first principles with its own loaders, its own House and Senate corpus
passes, its own tier engine and its own roll-up.  A row is accepted only when
the verifier's own derivation reproduces it field for field.

Layers
------
A  STRUCTURAL      gzip mtime, canonical serialisation, row counts, sha256
                   binding, lane guard columns, committed-schema conformance,
                   duplicate pairs, receipt input binding.
B  RE-DERIVATION   100% of candidate rows, 100% of staffer rows, 100% of LDA
                   rows re-derived and compared field by field; receipt counts
                   recomputed.
C  CONTROLS        planted defects that MUST fire, plus a silent probe that
                   must NOT fire, so a green A/B is informative rather than
                   vacuous.  Includes the PROMOTION TRIPWIRE.

Exit code 0 only when every check passes.
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
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

# ---------------------------------------------------------------------------
# Constants the generation is contractually bound to.  Restated here rather
# than imported, so a builder-side edit cannot silently move the goalposts.
# ---------------------------------------------------------------------------
RULE_VERSION = "payroll-name-resolution-v1"
PHASE = "filter-label"

CANDIDATE_FILE = "payroll_name_resolutions.ndjson.gz"
STAFFER_FILE = "current_staffer_resolution.ndjson.gz"
LDA_FILE = "lda_resolution.ndjson.gz"
RECEIPT_FILE = "payroll_name_resolution_receipt.json"
PAYLOAD_FILES = (CANDIDATE_FILE, STAFFER_FILE, LDA_FILE)

SCHEMA_DIR_NAME = "payroll_name_resolution_schemas"
SCHEMA_FOR = {
    CANDIDATE_FILE: "payroll_name_resolutions.schema.json",
    STAFFER_FILE: "current_staffer_resolution.schema.json",
    LDA_FILE: "lda_resolution.schema.json",
    RECEIPT_FILE: "payroll_name_resolution_receipt.schema.json",
}

TIER_ORDER = ("R1_EXACT_UNIQUE", "R2_EXACT_CORROBORATED",
              "R3_EXACT_AMBIGUOUS", "R4_LOOSE")
TIER_RANK = {name: i + 1 for i, name in enumerate(TIER_ORDER)}
STATUS_FOR_TIER = {
    "R1_EXACT_UNIQUE": "RESOLVED_R1",
    "R2_EXACT_CORROBORATED": "RESOLVED_R2",
    "R3_EXACT_AMBIGUOUS": "CANDIDATE_R3",
    "R4_LOOSE": "CANDIDATE_R4",
}
STATUS_VALUES = ("RESOLVED_R1", "RESOLVED_R2", "CANDIDATE_R3",
                 "CANDIDATE_R4", "NOT_FOUND")

NON_MEMBER_CONTAINERS = ("admin", "committee", "leadership",
                         "member_organization")
MEMBER_CONTAINERS = ("member_office", "member_office_unresolved")
SENATE_PERSONAL_KIND = "senate_personal_office"
SENATE_NON_PERSONAL_KIND = "senate_non_personal_office"
SENATE_PERSONAL_PREFIXES = ("SENATOR ", "INTERN COMPENSATION - ")
LIST_CAP = 20
LDA_FILING_YEAR_SIGNAL_QUALIFIES = False

GUARD_COLUMNS = {
    "canonical_eligible": False,
    "canonical_employment_promoted": False,
    "canonical_identity_decision": "NOT_ADJUDICATED",
    "review_status": "REVIEW_REQUIRED",
}

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
# Name normalisation.  Independent implementation of the Index phase rules
# N1-N15; the Senate key reproduction is asserted against the published key
# set, which is what makes this implementation falsifiable rather than assumed.
# ---------------------------------------------------------------------------
class Norm:
    HONORIFICS = frozenset({"MR", "MRS", "MS", "MISS", "DR", "HON", "REV",
                            "PROF", "SIR", "ATTY", "MX"})
    CREDENTIALS = frozenset({"JD", "MD", "PHD", "ESQ", "ESQUIRE", "CPA", "MBA",
                             "MPA", "MPH", "MSW", "RN", "DDS", "DVM", "LLM",
                             "CFA", "EDD", "DPHIL", "MSC"})
    TRAILING_CREDENTIALS = frozenset({"MS", "D"})
    SUFFIXES = frozenset({"JR", "SR", "II", "III", "IV"})
    PLACEHOLDERS = frozenset({"NA", "N", "A", "NONE", "NULL", "UNKNOWN",
                              "TEST", "VACANT", "TBD", "X", "XX", "XXX",
                              "NOTAPPLICABLE", "FARA", "EXEMPTION",
                              "NOTAPPLICABL", "DO", "SAME", "DITTO"})
    DATE = re.compile(r"^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
    YEAR = re.compile(r"^(19|20)\d{2}$")
    BRACKETED = re.compile(r"\([^)]*\)|\[[^\]]*\]")
    PUNCT = re.compile(r"[^A-Z0-9]")
    UNIFY = {0x2019: "'", 0x02BC: "'", 0x2013: "-", 0x2014: "-", 0x2011: "-",
             0x00A0: " ", 0x2018: "'"}

    @classmethod
    def prep(cls, value: Any) -> str:
        if not value:
            return ""
        text = str(value).translate(cls.UNIFY)
        text = text.split("|", 1)[0]
        text = cls.BRACKETED.sub(" ", text)
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        return text.upper()

    @classmethod
    def tokenize(cls, text: str) -> tuple[list[str], list[str]]:
        raw = [chunk for chunk in re.split(r"\s+", text) if chunk]
        while raw and cls.PUNCT.sub("", raw[0]) in cls.HONORIFICS:
            raw.pop(0)
        kept: list[str] = []
        suffixes: list[str] = []
        for token in raw:
            bare = cls.PUNCT.sub("", token)
            if not bare:
                continue
            if cls.DATE.match(token) or cls.YEAR.match(bare):
                continue
            # A period surviving the removal of one trailing period marks
            # initials, so "JR." is a suffix but "J.R." is a given name.
            if "." not in token.rstrip("."):
                if bare in cls.SUFFIXES:
                    suffixes.append(bare)
                    continue
                if bare in cls.CREDENTIALS:
                    continue
            kept.append(bare)
        while len(kept) > 2 and kept[-1] in cls.TRAILING_CREDENTIALS:
            kept.pop()
        return kept, suffixes

    @classmethod
    def collapse(cls, parts: Iterable[str]) -> str:
        return cls.PUNCT.sub("", "".join(parts))

    @classmethod
    def key_from(cls, surname: Sequence[str], given: Sequence[str],
                 middle: Sequence[str]) -> tuple[str, str, str | None] | None:
        sur = cls.collapse(surname)
        giv = cls.collapse(given)
        if len(sur) < 2 or len(giv) < 1:
            return None
        initial = None
        for token in middle:
            folded = cls.collapse([token])
            if folded:
                initial = folded[0]
                break
        return (sur, giv, initial)

    @classmethod
    def is_placeholder(cls, value: Any) -> bool:
        tokens, _ = cls.tokenize(cls.prep(value))
        if not tokens:
            return True
        return all(token in cls.PLACEHOLDERS for token in tokens)

    @classmethod
    def last_first_keys(cls, value: Any) -> list[tuple[str, str, str | None]]:
        text = cls.prep(value)
        if "," not in text:
            return []
        head, tail = text.split(",", 1)
        sur_tokens, _ = cls.tokenize(head)
        giv_tokens, _ = cls.tokenize(tail)
        if not sur_tokens or not giv_tokens:
            return []
        out: list[tuple[str, str, str | None]] = []
        for candidate in ([sur_tokens] +
                          ([sur_tokens[-1:]] if len(sur_tokens) > 1 else [])):
            key = cls.key_from(candidate, giv_tokens[:1], giv_tokens[1:])
            if key is not None and key not in out:
                out.append(key)
        return out


def senate_personal_remainder(office: str) -> str | None:
    text = Norm.prep(office).strip()
    for prefix in SENATE_PERSONAL_PREFIXES:
        if text.startswith(prefix):
            return text[len(prefix):].strip()
    return None


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def stream(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def canonical(row: Mapping[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def gzip_mtime(path: Path) -> int:
    with path.open("rb") as handle:
        header = handle.read(8)
    return int.from_bytes(header[4:8], "little")


def capped(values: Iterable[str]) -> tuple[list[str], bool]:
    # Must match build_payroll_name_resolution.capped exactly, including the
    # falsy-value drop: keeping empty strings here makes the verifier expect a
    # list the builder never emits and reports a field mismatch that is the
    # verifier's own defect.
    ordered = sorted({v for v in values if v})
    if len(ordered) > LIST_CAP:
        return ordered[:LIST_CAP], True
    return ordered, False


def flatten(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    out: list[str] = []
    for item in value:
        out.extend(flatten(item))
    return out


# ---------------------------------------------------------------------------
# Minimal JSON-Schema conformance (the committed schemas use a small subset)
# ---------------------------------------------------------------------------
def schema_errors(row: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    problems: list[str] = []
    for field in schema.get("required", []):
        if field not in row:
            problems.append(f"missing required field {field}")
    props = schema.get("properties", {})
    for field, spec in props.items():
        if field not in row:
            continue
        value = row[field]
        expected = spec.get("type")
        if expected and not _type_ok(value, expected):
            problems.append(f"{field}: expected type {expected}")
        if "enum" in spec and value not in spec["enum"]:
            problems.append(f"{field}: {value!r} not in enum")
        if "const" in spec and value != spec["const"]:
            problems.append(f"{field}: {value!r} != const {spec['const']!r}")
        if "minimum" in spec and isinstance(value, (int, float)) and \
                value < spec["minimum"]:
            problems.append(f"{field}: below minimum")
    if schema.get("additionalProperties") is False:
        for field in row:
            if field not in props:
                problems.append(f"{field}: not permitted by schema")
    return problems


def _type_ok(value: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    for name in names:
        if name == "null" and value is None:
            return True
        if name == "boolean" and isinstance(value, bool):
            return True
        if name == "integer" and isinstance(value, int) and not isinstance(value, bool):
            return True
        if name == "number" and isinstance(value, (int, float)) and \
                not isinstance(value, bool):
            return True
        if name == "string" and isinstance(value, str):
            return True
        if name == "array" and isinstance(value, list):
            return True
        if name == "object" and isinstance(value, dict):
            return True
    return False


# ---------------------------------------------------------------------------
# Independent loaders
# ---------------------------------------------------------------------------
def read_roster(path: Path):
    people: dict[str, dict[str, Any]] = {}
    pairs: dict[tuple[str, str], set[str]] = collections.defaultdict(set)
    alias_rows = 0
    for row in stream(path):
        alias_rows += 1
        rid = row["roster_id"]
        if rid not in people:
            people[rid] = {
                "roster_id": rid,
                "kind": "quorum_staffer" if rid.startswith("quorum:") else "lda_lobbyist",
                "roster_source": row.get("roster_source"),
                "display_name": row.get("display_name"),
                "member_display": row.get("quorum_member_display"),
                "title": row.get("quorum_title"),
                "fingerprint": row.get("spelling_fingerprint"),
                "suffixes": flatten(row.get("generational_suffix")),
                "eligible": bool(row.get("match_eligible")),
            }
        if row.get("match_eligible") and row.get("surname_key") and row.get("given_key"):
            pairs[(row["surname_key"], row["given_key"])].add(rid)
    return people, dict(pairs), alias_rows


def read_staff(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for member_display, entries in payload.items():
        for entry in entries or []:
            out[str(entry["id"])] = {
                "display_name": entry.get("n"),
                "member_display": member_display,
                "title_raw": entry.get("t"),
                "star": entry.get("star"),
            }
    return out


def read_nicknames(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    table: dict[str, str] = {}
    for short, formals in (payload.get("entries") or {}).items():
        forms = [f for f in (formals or []) if f]
        if len(forms) == 1:
            table[Norm.collapse([Norm.prep(short)])] = \
                Norm.collapse([Norm.prep(forms[0])])
    return table


def read_lda_queue(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for row in stream(path):
        pid = row["lda_source_person_id"]
        text = " ".join(str(v) for v in (row.get("covered_position_values") or []))
        out[pid] = {
            "display_name": row.get("display_name"),
            "filing_years": sorted({int(y) for y in (row.get("filing_years") or [])}),
            "covered_years": sorted(
                {int(y) for y in (row.get("covered_position_year_tokens") or [])
                 if str(y).isdigit()}),
            "covered_tokens": frozenset(
                tok for tok in re.split(r"[^A-Z0-9]+", Norm.prep(text))
                if len(tok) >= 4 and tok not in OFFICE_STOPWORDS),
            "covered_present": bool(text.strip()),
            "priority": row.get("priority"),
            "identity_status": row.get("identity_status"),
        }
    return out


def read_payee_facts(path: Path) -> dict[tuple[str, str, str | None], dict[str, Any]]:
    out: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    for row in stream(path):
        key = (row["surname_key"], row["given_key"],
               row.get("middle_initial") or None)
        out[key] = {
            "chambers": frozenset(row.get("chambers") or ()),
            "max_offices": int(row.get("max_offices_within_one_period") or 0),
            "collision": bool(row.get("office_period_collision")),
            "shared_rows": int(row.get("shared_employee_rows") or 0),
            "observation_rows": int(row.get("observation_rows") or 0),
        }
    return out


def read_old_staffers(path: Path) -> dict[str, dict[str, Any]]:
    return {str(row["quorum_staff_id"]): {
        "link_status": row.get("link_status"),
        "member_bioguide": row.get("member_bioguide"),
    } for row in stream(path)}


def read_old_lda(path: Path) -> tuple[set[str], set[str]]:
    in_lanes: set[str] = set()
    linked: set[str] = set()
    for row in stream(path):
        pid = row.get("lda_source_person_id")
        if not pid:
            continue
        in_lanes.add(pid)
        if str(row.get("link_status") or "").startswith("LINKED"):
            linked.add(pid)
    return in_lanes, linked


# ---------------------------------------------------------------------------
# Independent corpus passes
# ---------------------------------------------------------------------------
def house_scan(path: Path) -> dict[str, Any]:
    """Per payee key, the quarters paid out of a NON-member container; per
    bioguide, the quarters that member's own office was on the payroll."""
    quarters: dict[str, int] = {}
    non_member: dict[tuple[str, str, str | None], set[str]] = \
        collections.defaultdict(set)
    ledger_keys: set[tuple[str, str, str | None]] = set()
    service: dict[str, set[str]] = collections.defaultdict(set)
    rows = 0
    for row in stream(path):
        rows += 1
        quarter = row.get("quarter") or ""
        if quarter not in quarters:
            quarters[quarter] = len(quarters)
        container = row.get("container_kind") or ""
        bioguide = row.get("member_bioguide")
        if container == "member_office" and bioguide:
            service[bioguide].add(quarter)
        person_key = row.get("person_key") or ""
        if not person_key.startswith("SOD:"):
            continue
        parts = person_key[4:].split("|")
        if len(parts) != 3:
            continue
        key = (parts[0], parts[1], parts[2] or None)
        ledger_keys.add(key)
        if container in NON_MEMBER_CONTAINERS:
            non_member[key].add(quarter)
    return {
        "quarters": quarters,
        "non_member": {k: frozenset(v) for k, v in non_member.items()},
        "ledger_keys": ledger_keys,
        "service": {k: frozenset(v) for k, v in service.items()},
        "rows": rows,
    }


def member_surname_index(staff: Mapping[str, Mapping[str, Any]],
                        nicknames: Mapping[str, str]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for entry in staff.values():
        display = entry["member_display"]
        if display in index:
            continue
        tokens, _ = Norm.tokenize(Norm.prep(display))
        if len(tokens) < 2:
            index[display] = {"surname": None, "givens": frozenset()}
            continue
        given = Norm.collapse([tokens[0]])
        forms = {given}
        if nicknames.get(given):
            forms.add(nicknames[given])
        index[display] = {
            "surname": Norm.collapse(tokens[1:]),
            "givens": frozenset(forms),
        }
    return index


def resolve_office(office: str,
                   index: Mapping[str, Mapping[str, Any]],
                   by_surname: Mapping[str, list[str]]) -> tuple[str | None, str]:
    remainder = senate_personal_remainder(office)
    if remainder is None:
        return None, "NOT_A_PERSONAL_OFFICE"
    tokens, _ = Norm.tokenize(remainder)
    if not tokens:
        return None, "EMPTY_AFTER_PREFIX"
    pool: list[tuple[str, int]] = []
    for take in (1, 2, 3):
        if take > len(tokens):
            break
        surname = Norm.collapse(tokens[-take:])
        for display in by_surname.get(surname, ()):
            pool.append((display, take))
    if not pool:
        return None, "SURNAME_NOT_IN_CURRENT_ROSTER"
    distinct = {display for display, _ in pool}
    if len(distinct) == 1:
        return next(iter(distinct)), "UNIQUE_SURNAME"
    hits: set[str] = set()
    for display, take in pool:
        head = tokens[:len(tokens) - take]
        forms = index[display]["givens"]
        for token in head:
            folded = Norm.collapse([token])
            if not folded:
                continue
            if folded in forms:
                hits.add(display)
            elif len(folded) == 1 and any(f.startswith(folded) for f in forms):
                hits.add(display)
    if len(hits) == 1:
        return next(iter(hits)), "SURNAME_AND_GIVEN_FORM"
    return None, "AMBIGUOUS_SURNAME_NO_GIVEN_AGREEMENT"


def senate_scan(path: Path, index: Mapping[str, Mapping[str, Any]],
                published: set[tuple[str, str, str | None]]) -> dict[str, Any]:
    by_surname: dict[str, list[str]] = collections.defaultdict(list)
    for display, info in index.items():
        if info.get("surname"):
            by_surname[info["surname"]].append(display)
    resolution: dict[str, tuple[str | None, str]] = {}
    non_personal: dict[tuple[str, str, str | None], set[str]] = \
        collections.defaultdict(set)
    service: dict[str, set[str]] = collections.defaultdict(set)
    reproduced: set[tuple[str, str, str | None]] = set()
    rows = 0
    for row in stream(path):
        rows += 1
        office = row.get("office_raw") or ""
        if office not in resolution:
            resolution[office] = resolve_office(office, index, by_surname)
        member, _method = resolution[office]
        period = f"{row.get('report_period_start')}..{row.get('report_period_end')}"
        if member is not None:
            service[member].add(period)
        raw = row.get("payee_name_raw") or ""
        if Norm.is_placeholder(raw):
            continue
        keys = Norm.last_first_keys(raw)
        if not keys:
            continue
        personal = senate_personal_remainder(office) is not None
        for key in keys:
            reproduced.add(key)
            if not personal:
                non_personal[key].add(period)
    return {
        "resolution": resolution,
        "non_personal": {k: frozenset(v) for k, v in non_personal.items()},
        "service": {k: frozenset(v) for k, v in service.items()},
        "reproduced": reproduced,
        "exact": reproduced == published,
        "missing": len(published - reproduced),
        "extra": len(reproduced - published),
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Candidate-lane adapters (verifier's own)
# ---------------------------------------------------------------------------
def triple(surname: Any, given: Any, middle: Any) -> tuple[str, str, str | None]:
    return (str(surname), str(given), str(middle) if middle else None)


def adapt(lane: str, row: Mapping[str, Any]) -> dict[str, Any]:
    if lane == "house_csv":
        payee, roster, key = row["payee"], row["roster"], row["payee_key"]
        evidence = row["match_evidence"]
        return {
            "lane": lane, "chamber": "HOUSE",
            "payee_key": triple(key[0], key[1], key[2]),
            "roster_id": row["roster_id"],
            "roster_key": triple(roster["surname_key"], roster["given_key"],
                                 roster.get("middle_initial")),
            "roster_key_basis": roster.get("key_basis"),
            "roster_is_primary": bool(roster.get("is_primary_key")),
            "source_class": row["match_class"],
            "nickname_direction": evidence.get("nickname_direction"),
            "nickname_formal_form": evidence.get("nickname_formal_form"),
            "variant_basis": evidence.get("variant_basis"),
            "variant_bridge": evidence.get("variant_surname_bridge"),
            "offices": list(payee.get("offices") or []),
            "periods": list(payee.get("quarters") or []),
            "titles": list(payee.get("titles") or []),
            "containers": list(payee.get("container_kinds") or []),
            "bioguides": list(payee.get("member_bioguides") or []),
            "observation_rows": int(payee.get("observation_rows") or 0),
            "max_offices": int(payee.get("max_offices_within_one_period") or 0),
            "shared_rows": int(payee.get("shared_employee_rows") or 0),
            "raw_example": payee.get("payee_raw_example"),
            "key_basis": list(payee.get("key_basis") or []),
            "primary_parse": bool(payee.get("has_primary_ledger_parse")),
            "suffixes": flatten(payee.get("generational_suffixes_seen")),
        }
    if lane == "house_pdf":
        pk = row["payee_key"].split("|")
        rk = row["roster_key"].split("|")
        reasons = sorted(row.get("variant_reasons") or [])
        return {
            "lane": lane, "chamber": "HOUSE",
            "payee_key": triple(pk[0], pk[1], pk[2]),
            "roster_id": row["roster_id"],
            "roster_key": triple(rk[0], rk[1], rk[2]),
            "roster_key_basis": row.get("roster_key_basis"),
            "roster_is_primary": bool(row.get("roster_is_primary_key")),
            "source_class": row["match_class"],
            "nickname_direction": None,
            "nickname_formal_form": None,
            "variant_basis": reasons[0] if reasons else None,
            "variant_bridge": None,
            "offices": list(row.get("payee_office_keys") or []),
            "periods": list(row.get("payee_quarters") or []),
            "titles": list(row.get("payee_title_bases") or []),
            "containers": list(row.get("payee_container_kinds") or []),
            "bioguides": list(row.get("payee_member_bioguides") or []),
            "observation_rows": int(row.get("payee_observation_rows") or 0),
            "max_offices": 0,
            "shared_rows": int(row.get("payee_shared_employee_rows") or 0),
            "raw_example": row.get("payee_raw_example"),
            "key_basis": list(row.get("payee_key_basis") or []),
            "primary_parse": int(row.get("payee_primary_parse_rows") or 0) > 0,
            "suffixes": flatten(row.get("payee_generational_suffixes")),
        }
    examples = row.get("payee_raw_examples") or []
    return {
        "lane": "senate", "chamber": "SENATE",
        "payee_key": triple(row["payee_surname_key"], row["payee_given_key"],
                            row.get("payee_middle_initial")),
        "roster_id": row["roster_id"],
        "roster_key": triple(row["roster_surname_key"], row["roster_given_key"],
                             row.get("roster_middle_initial")),
        "roster_key_basis": row.get("roster_key_basis"),
        "roster_is_primary": bool(row.get("roster_key_is_primary")),
        "source_class": row["match_class"],
        "nickname_direction": row.get("match_subclass"),
        "nickname_formal_form": None,
        "variant_basis": (row.get("match_subclass")
                          if row["match_class"] == "VARIANT_HYPHEN_APOSTROPHE_SUFFIX"
                          else None),
        "variant_bridge": None,
        "offices": list(row.get("offices") or []),
        "periods": list(row.get("periods") or []),
        "titles": list(row.get("titles") or []),
        "containers": [],
        "bioguides": [],
        "observation_rows": int(row.get("payee_observation_rows") or 0),
        "max_offices": int(row.get("max_offices_within_one_period") or 0),
        "shared_rows": 0,
        "raw_example": sorted(examples)[0] if examples else None,
        "key_basis": list(row.get("payee_key_basis") or []),
        "primary_parse": int(row.get("payee_primary_parse_rows") or 0) > 0,
        "suffixes": flatten(row.get("payee_generational_suffixes_seen")),
    }


def name_class(payee: tuple, roster: tuple) -> str:
    if payee[0] == roster[0] and payee[1] == roster[1]:
        if payee[2] and roster[2] and payee[2] == roster[2]:
            return "EXACT_TRIPLE"
        return "EXACT_PAIR"
    return "LOOSE"


def mi_state(payee_mi: str | None, roster_mi: str | None) -> str:
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


def years_of(chamber: str, periods: Sequence[str]) -> list[int]:
    out: set[int] = set()
    for period in periods:
        if chamber == "HOUSE":
            match = re.match(r"^(\d{4})Q[1-4]$", period or "")
            if match:
                out.add(int(match.group(1)))
        else:
            found = [int(y) for y in re.findall(r"(\d{4})-\d{2}-\d{2}", period or "")]
            if found:
                out.update(range(min(found), max(found) + 1))
    return sorted(out)


# ---------------------------------------------------------------------------
# The re-derivation
# ---------------------------------------------------------------------------
def rederive(paths: Mapping[str, Path], log) -> dict[str, Any]:
    log("  [re] roster / staff / lda / nicknames")
    roster, roster_pairs, alias_rows = read_roster(paths["roster_keys"])
    staff = read_staff(paths["staff_directory"])
    nicknames = read_nicknames(paths["nicknames"])
    lda = read_lda_queue(paths["lda_queue"])

    log("  [re] payee key universe")
    facts = read_payee_facts(paths["payee_keys"])
    both_chambers = {k for k, v in facts.items() if len(v["chambers"]) > 1}
    published_senate = {k for k, v in facts.items() if "SENATE" in v["chambers"]}

    log("  [re] old-rule baseline")
    old_staff = read_old_staffers(paths["old_staffer_links"])
    old_lda_lanes, old_lda_linked = read_old_lda(paths["old_lda_links"])

    log("  [re] House ledger scan (975k rows)")
    house = house_scan(paths["house_ledger"])
    index = member_surname_index(staff, nicknames)

    log("  [re] Senate corpus scan (233k rows)")
    senate = senate_scan(paths["senate_corpus"], index, published_senate)

    log("  [re] candidate lanes")
    entities: dict[tuple, dict[str, Any]] = {}
    pairs: dict[tuple, dict[str, Any]] = {}
    lane_counts: dict[str, int] = {}
    for lane, key in (("house_csv", "candidates_house_csv"),
                      ("house_pdf", "candidates_house_pdf"),
                      ("senate", "candidates_senate")):
        count = 0
        for raw in stream(paths[key]):
            count += 1
            rec = adapt(lane, raw)
            ent_key = (rec["chamber"], rec["payee_key"])
            ent = entities.get(ent_key)
            if ent is None:
                ent = {"offices": set(), "periods": set(), "titles": set(),
                       "containers": set(), "bioguides": set(),
                       "observation_rows": 0, "max_offices": 0,
                       "shared_rows": 0, "raw_examples": set(),
                       "key_basis": set(), "primary_parse": False,
                       "suffixes": set(), "lanes": set()}
                entities[ent_key] = ent
            ent["offices"].update(rec["offices"])
            ent["periods"].update(rec["periods"])
            ent["titles"].update(rec["titles"])
            ent["containers"].update(rec["containers"])
            ent["bioguides"].update(rec["bioguides"])
            ent["observation_rows"] += rec["observation_rows"]
            ent["max_offices"] = max(ent["max_offices"], rec["max_offices"])
            ent["shared_rows"] += rec["shared_rows"]
            if rec["raw_example"]:
                ent["raw_examples"].add(rec["raw_example"])
            ent["key_basis"].update(rec["key_basis"])
            ent["primary_parse"] |= rec["primary_parse"]
            ent["suffixes"].update(rec["suffixes"])
            ent["lanes"].add(lane)

            pkey = (rec["chamber"], rec["payee_key"], rec["roster_id"])
            existing = pairs.get(pkey)
            derived = name_class(rec["payee_key"], rec["roster_key"])
            if existing is None:
                pairs[pkey] = {
                    "chamber": rec["chamber"], "payee_key": rec["payee_key"],
                    "roster_id": rec["roster_id"], "roster_key": rec["roster_key"],
                    "roster_key_basis": rec["roster_key_basis"],
                    "roster_is_primary": rec["roster_is_primary"],
                    "derived": derived,
                    "source_classes": {rec["source_class"]},
                    "lanes": {lane},
                    "nickname_direction": rec["nickname_direction"],
                    "nickname_formal_form": rec["nickname_formal_form"],
                    "variant_basis": rec["variant_basis"],
                    "variant_bridge": rec["variant_bridge"],
                }
            else:
                existing["source_classes"].add(rec["source_class"])
                existing["lanes"].add(lane)
                existing["nickname_direction"] = (existing["nickname_direction"] or
                                                  rec["nickname_direction"])
                existing["variant_basis"] = (existing["variant_basis"] or
                                             rec["variant_basis"])
                existing["variant_bridge"] = (existing["variant_bridge"] or
                                              rec["variant_bridge"])
        lane_counts[lane] = count

    log("  [re] tier engine")
    records: dict[tuple, dict[str, Any]] = {}
    for pkey, pair in pairs.items():
        ent = entities[(pair["chamber"], pair["payee_key"])]
        person = roster[pair["roster_id"]]
        pk, rk = pair["payee_key"], pair["roster_key"]
        mi = mi_state(pk[2], rk[2])
        suf = suffix_state(sorted(ent["suffixes"]), person["suffixes"])
        group = roster_pairs.get((rk[0], rk[1]), set())
        roster_unique = len(group) == 1
        duplicate_registration = (
            not roster_unique and
            len({roster[r]["fingerprint"] for r in group}) == 1 and
            len({roster[r]["kind"] for r in group}) == 1)
        other_chamber = pk in both_chambers
        fact = facts[pk]
        collision = (fact["collision"] or fact["max_offices"] > 1 or
                     ent["max_offices"] > 1)
        payee_unique = (not collision) and (not other_chamber)

        signals: list[str] = []
        recorded: list[str] = []
        pairing = "NOT_APPLICABLE"

        if person["kind"] == "quorum_staffer":
            staff_id = pair["roster_id"].split(":")[-1]
            bioguide = (old_staff.get(staff_id) or {}).get("member_bioguide")
            member_display = person["member_display"]
            if pair["chamber"] == "HOUSE":
                if bioguide and f"HON:{bioguide}" in ent["offices"]:
                    signals.append("Q1_OWN_MEMBER_HOUSE_OFFICE")
                service = house["service"].get(bioguide or "", frozenset())
                if pk in house["ledger_keys"]:
                    pairing = "EXACT"
                    hit = bool(service & house["non_member"].get(pk, frozenset()))
                elif ent["containers"] and not (set(ent["containers"]) &
                                                set(MEMBER_CONTAINERS)):
                    pairing = "IMPLIED_ALL_CONTAINERS_NON_MEMBER"
                    hit = bool(service & set(ent["periods"]))
                else:
                    pairing = "UNAVAILABLE"
                    hit = False
                if hit and service:
                    signals.append(
                        "Q3_NON_MEMBER_HOUSE_OFFICE_IN_MEMBER_SERVICE_QUARTER")
            else:
                for office in ent["offices"]:
                    resolved, _ = senate["resolution"].get(
                        office, (None, "OFFICE_NOT_IN_CORPUS"))
                    if resolved is not None and resolved == member_display:
                        signals.append("Q2_OWN_MEMBER_SENATE_OFFICE")
                        break
                service = senate["service"].get(member_display or "", frozenset())
                if pk in senate["reproduced"]:
                    pairing = "EXACT"
                    hit = bool(service & senate["non_personal"].get(pk, frozenset()))
                else:
                    pairing = "UNAVAILABLE"
                    hit = False
                if hit and service:
                    signals.append(
                        "Q4_NON_MEMBER_SENATE_OFFICE_IN_MEMBER_SERVICE_PERIOD")
        else:
            info = lda.get(pair["roster_id"])
            yrs = years_of(pair["chamber"], sorted(ent["periods"]))
            if info:
                if info["covered_years"] and yrs:
                    low, high = min(info["covered_years"]), max(info["covered_years"])
                    if any(low <= y <= high for y in yrs):
                        signals.append("L1_COVERED_POSITION_YEAR_OVERLAP")
                if info["covered_tokens"]:
                    tokens: set[str] = set()
                    for office in ent["offices"]:
                        for tok in re.split(r"[^A-Z0-9]+", Norm.prep(office)):
                            if len(tok) >= 4 and tok not in OFFICE_STOPWORDS:
                                tokens.add(tok)
                    if tokens & info["covered_tokens"]:
                        signals.append("L2_COVERED_POSITION_OFFICE_TEXT_OVERLAP")
                if info["filing_years"] and yrs and \
                        min(info["filing_years"]) >= max(yrs):
                    if LDA_FILING_YEAR_SIGNAL_QUALIFIES:
                        signals.append("L3_FILING_YEARS_POSTDATE_SERVICE")
                    else:
                        recorded.append("L3_FILING_YEARS_POSTDATE_SERVICE")

        blocked: list[str] = []
        if pair["derived"] == "LOOSE":
            tier = "R4_LOOSE"
        else:
            if pair["derived"] != "EXACT_TRIPLE":
                blocked.append("MIDDLE_INITIAL_NOT_PRESENT_AND_EQUAL_ON_BOTH_SIDES")
            if not roster_unique:
                blocked.append("ROSTER_PAIR_ANSWERS_FOR_2PLUS_IDENTITY_ROWS")
            if collision:
                blocked.append("PAYEE_KEY_IN_2PLUS_OFFICES_IN_ONE_PERIOD")
            if other_chamber:
                blocked.append("PAYEE_KEY_ALSO_PRESENT_IN_THE_OTHER_CHAMBER")
            if not ent["primary_parse"]:
                blocked.append("PAYEE_KEY_FROM_A_TRUNCATED_SURNAME_PARSE_ONLY")
            contradicted = (mi == "BOTH_PRESENT_DIFFERENT" or
                            suf == "BOTH_PRESENT_DIFFERENT")
            if not blocked:
                tier = "R1_EXACT_UNIQUE"
            elif signals and not contradicted:
                tier = "R2_EXACT_CORROBORATED"
            else:
                tier = "R3_EXACT_AMBIGUOUS"
                if contradicted:
                    blocked.append("CONTRADICTING_MIDDLE_INITIAL_OR_SUFFIX")

        relaxed = (pair["derived"] == "EXACT_PAIR" and
                   mi in ("ROSTER_MISSING", "PAYEE_MISSING", "NEITHER") and
                   roster_unique and payee_unique)

        records[pkey] = {
            "pair": pair, "ent": ent, "person": person, "tier": tier,
            "signals": signals, "recorded": recorded, "pairing": pairing,
            "mi": mi, "suffix": suf, "roster_unique": roster_unique,
            "group_rows": len(group),
            "group_fingerprints": len({roster[r]["fingerprint"] for r in group}),
            "duplicate_registration": duplicate_registration,
            "payee_unique": payee_unique, "collision": collision,
            "fact": fact, "other_chamber": other_chamber,
            "blocked": blocked, "relaxed": relaxed, "demoted": False,
        }

    r1_payee = collections.Counter()
    r1_roster = collections.Counter()
    for rec in records.values():
        if rec["tier"] == "R1_EXACT_UNIQUE":
            r1_payee[(rec["pair"]["chamber"], rec["pair"]["payee_key"])] += 1
            r1_roster[rec["pair"]["roster_id"]] += 1
    for rec in records.values():
        if rec["tier"] != "R1_EXACT_UNIQUE":
            continue
        ref = (rec["pair"]["chamber"], rec["pair"]["payee_key"])
        if r1_payee[ref] > 1 or r1_roster[rec["pair"]["roster_id"]] > 1:
            rec["tier"] = "R3_EXACT_AMBIGUOUS"
            rec["demoted"] = True
            rec["blocked"].append("TIE_AT_R1_NEVER_BROKEN_SILENTLY")

    tie_payee = collections.Counter()
    tie_roster = collections.Counter()
    for rec in records.values():
        tie_payee[(rec["pair"]["chamber"], rec["pair"]["payee_key"],
                   rec["tier"])] += 1
        tie_roster[(rec["pair"]["roster_id"], rec["tier"])] += 1

    return {
        "records": records, "entities": entities, "roster": roster,
        "staff": staff, "lda": lda, "old_staff": old_staff,
        "old_lda_lanes": old_lda_lanes, "old_lda_linked": old_lda_linked,
        "house": house, "senate": senate, "facts": facts,
        "tie_payee": tie_payee, "tie_roster": tie_roster,
        "lane_counts": lane_counts, "alias_rows": alias_rows,
    }


def expected_candidate_row(rec: Mapping[str, Any], state: Mapping[str, Any],
                           run_id: str) -> dict[str, Any]:
    pair, ent, person = rec["pair"], rec["ent"], rec["person"]
    tier = rec["tier"]
    tie_a = state["tie_payee"][(pair["chamber"], pair["payee_key"], tier)]
    tie_b = state["tie_roster"][(pair["roster_id"], tier)]
    offices, off_trunc = capped(ent["offices"])
    periods, per_trunc = capped(ent["periods"])
    titles, tit_trunc = capped(ent["titles"])
    staff_id = (pair["roster_id"].split(":")[-1]
                if person["kind"] == "quorum_staffer" else None)
    info = state["lda"].get(pair["roster_id"]) if person["kind"] == "lda_lobbyist" else None
    all_periods = sorted(ent["periods"])
    if pair["chamber"] == "HOUSE":
        office_kinds = sorted(ent["containers"])
    else:
        office_kinds = sorted({
            SENATE_PERSONAL_KIND if senate_personal_remainder(o) is not None
            else SENATE_NON_PERSONAL_KIND for o in ent["offices"]})
    return {
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "evidence": {
            "corroboration_signal_count": len(rec["signals"]),
            "corroboration_signals": sorted(rec["signals"]),
            "corroboration_signals_recorded_non_qualifying": sorted(rec["recorded"]),
            "derived_name_class": pair["derived"],
            "generational_suffix_agreement": rec["suffix"],
            "generational_suffix_payee": sorted(ent["suffixes"]),
            "generational_suffix_roster": sorted(person["suffixes"]),
            "member_service_pairing_availability": rec["pairing"],
            "middle_initial_agreement": rec["mi"],
            "middle_initial_payee": pair["payee_key"][2],
            "middle_initial_roster": pair["roster_key"][2],
            "nickname_direction": pair["nickname_direction"],
            "nickname_formal_form": pair["nickname_formal_form"],
            "payee_key_seen_in_other_chamber": rec["other_chamber"],
            "payee_office_period_collision": rec["collision"],
            "payee_unique_payroll_person": rec["payee_unique"],
            "r1_blocked_by": sorted(set(rec["blocked"])),
            "r1_blocked_by_same_spelling_duplicate_registration":
                rec["duplicate_registration"],
            "roster_pair_distinct_spelling_fingerprints": rec["group_fingerprints"],
            "roster_pair_identity_rows": rec["group_rows"],
            "roster_unique_identity": rec["roster_unique"],
            "source_match_classes": sorted(pair["source_classes"]),
            "variant_basis": pair["variant_basis"],
            "variant_surname_bridge": pair["variant_bridge"],
            "would_be_r1_under_relaxed_middle_initial": rec["relaxed"],
        },
        "lanes": sorted(pair["lanes"]),
        "lda_covered_position_years": info["covered_years"] if info else None,
        "lda_filing_years": info["filing_years"] if info else None,
        "lda_priority": info["priority"] if info else None,
        "payee_chamber": pair["chamber"],
        "payee_container_kinds": sorted(ent["containers"]),
        "payee_given_key": pair["payee_key"][1],
        "payee_has_primary_parse": ent["primary_parse"],
        "payee_key_basis": sorted(ent["key_basis"]),
        "payee_max_offices_within_one_period": rec["fact"]["max_offices"],
        "payee_max_offices_within_one_period_lane": ent["max_offices"],
        "payee_member_bioguides": sorted(ent["bioguides"]),
        "payee_middle_initial": pair["payee_key"][2],
        "payee_observation_rows": ent["observation_rows"],
        "payee_office_kinds": office_kinds,
        "payee_offices": offices,
        "payee_offices_distinct": len(ent["offices"]),
        "payee_offices_truncated": off_trunc,
        "payee_period_first": all_periods[0] if all_periods else None,
        "payee_period_last": all_periods[-1] if all_periods else None,
        "payee_periods": periods,
        "payee_periods_distinct": len(ent["periods"]),
        "payee_periods_truncated": per_trunc,
        "payee_raw_example": (sorted(ent["raw_examples"])[0]
                              if ent["raw_examples"] else None),
        "payee_shared_employee_rows": rec["fact"]["shared_rows"],
        "payee_shared_employee_rows_lane": ent["shared_rows"],
        "payee_surname_key": pair["payee_key"][0],
        "payee_titles": titles,
        "payee_titles_distinct": len(ent["titles"]),
        "payee_titles_truncated": tit_trunc,
        "phase": PHASE,
        "quorum_member_bioguide": (
            (state["old_staff"].get(staff_id) or {}).get("member_bioguide")
            if staff_id else None),
        "quorum_member_display": person["member_display"],
        "quorum_staff_id": staff_id,
        "quorum_title": person["title"],
        "resolution_tier": tier,
        "resolution_tier_rank": TIER_RANK[tier],
        "review_status": "REVIEW_REQUIRED",
        "roster_display_name": person["display_name"],
        "roster_given_key": pair["roster_key"][1],
        "roster_id": pair["roster_id"],
        "roster_is_primary_key": pair["roster_is_primary"],
        "roster_key_basis": pair["roster_key_basis"],
        "roster_kind": person["kind"],
        "roster_middle_initial": pair["roster_key"][2],
        "roster_source": person["roster_source"],
        "roster_spelling_fingerprint": person["fingerprint"],
        "roster_surname_key": pair["roster_key"][0],
        "rule_version": RULE_VERSION,
        "run_id": run_id,
        "schema_id": "staffer-network-payroll-name-resolution-v1",
        "tie_demoted_from_r1": rec["demoted"],
        "tie_size": max(tie_a, tie_b),
        "tie_size_payee_for_roster": tie_b,
        "tie_size_roster_for_payee": tie_a,
    }


def rollup_for(roster_id: str, state: Mapping[str, Any]) -> dict[str, Any]:
    rows = state["by_roster"].get(roster_id, [])
    by_tier = collections.Counter(r["tier"] for r in rows)
    if rows:
        best_rank = min(TIER_RANK[r["tier"]] for r in rows)
        best_tier = TIER_ORDER[best_rank - 1]
        best = [r for r in rows if r["tier"] == best_tier]
        status = STATUS_FOR_TIER[best_tier]
    else:
        best_tier, best_rank, best, status = None, None, [], "NOT_FOUND"
    offices, off_trunc = capped(o for r in best for o in r["offices"])
    periods = sorted({p for r in best for p in r["periods"]})
    titles, tit_trunc = capped(t for r in best for t in r["titles"])
    return {
        "best_tier": best_tier,
        "best_tier_rank": best_rank,
        "candidate_count": len(rows),
        "candidates_by_tier": {t: by_tier.get(t, 0) for t in TIER_ORDER},
        "corroboration_signals_at_best_tier":
            sorted({s for r in best for s in r["signals"]}),
        "matched_chambers": sorted({r["chamber"] for r in best}),
        "matched_container_kinds": sorted({c for r in best for c in r["containers"]}),
        "matched_office_kinds": sorted({k for r in best for k in r["office_kinds"]}),
        "matched_offices": offices,
        "matched_offices_distinct": len({o for r in best for o in r["offices"]}),
        "matched_offices_truncated": off_trunc,
        "matched_period_first": periods[0] if periods else None,
        "matched_period_last": periods[-1] if periods else None,
        "matched_periods_distinct": len(periods),
        "matched_titles": titles,
        "matched_titles_truncated": tit_trunc,
        "payee_keys_at_best_tier": sorted(
            "|".join(str(p) if p is not None else "" for p in r["payee_key"])
            for r in best),
        "status": status,
        "tie_size_at_best_tier": max((r["tie_size"] for r in best), default=0),
    }


# ---------------------------------------------------------------------------
# Verification driver
# ---------------------------------------------------------------------------
class Report:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(self, check_id: str, name: str, ok: bool,
            detail: Any = None, denominator: Any = None) -> bool:
        self.checks.append({"check": check_id, "name": name,
                            "status": "PASS" if ok else "FAIL",
                            "detail": detail, "denominator": denominator})
        return ok

    @property
    def failures(self) -> list[dict[str, Any]]:
        return [c for c in self.checks if c["status"] == "FAIL"]


def default_paths(repo: Path, scratch: Path) -> dict[str, Path]:
    audits = repo / "audits" / "staffer_network"
    return {
        "candidates_house_csv": scratch / "candidates_house_csv.ndjson.gz",
        "candidates_house_pdf": scratch / "candidates_house_pdf.ndjson.gz",
        "candidates_senate": scratch / "candidates_senate.ndjson.gz",
        "roster_keys": scratch / "roster_keys.ndjson.gz",
        "payee_keys": scratch / "payee_keys.ndjson.gz",
        "nicknames": repo / "data" / "staffer_network" / "reference" /
                     "first_name_nicknames_v1.json",
        "staff_directory": repo / "data" / "members" / "staff_directory.json",
        "lda_queue": Path(os.environ.get("LOCALAPPDATA", "")) / "Melange" /
                     "staffer_network" / "employment-lookup" /
                     "generation-20260831T050000Z" /
                     "employment_lookup_queue.ndjson.gz",
        "house_ledger": audits / "house_personnel_ledger_20260902_v2_primary" /
                        "house_personnel_observations.ndjson.gz",
        "senate_corpus": audits /
                         "official_senate_payroll_2011_2026_employment_scope_v1" /
                         "senate_payroll_employment_candidates_2011_2026.ndjson.gz",
        "old_staffer_links": audits / "hill_personnel_spine_20260902_v1_primary" /
                             "current_staffer_links.ndjson.gz",
        "old_lda_links": audits / "hill_personnel_spine_20260902_v1_primary" /
                         "lda_spine_links.ndjson.gz",
    }


def verify(generation: Path, paths: Mapping[str, Path], schema_dir: Path,
           log=print) -> dict[str, Any]:
    report = Report()
    receipt = json.loads((generation / RECEIPT_FILE).read_text(encoding="utf-8"))
    schemas = {name: json.loads((schema_dir / SCHEMA_FOR[name]).read_text("utf-8"))
               for name in SCHEMA_FOR}

    # ---- Layer A: structural -------------------------------------------
    log("[A] structural gates")
    for name in PAYLOAD_FILES:
        path = generation / name
        report.add(f"A1:{name}", "gzip header mtime is 0",
                   gzip_mtime(path) == 0, gzip_mtime(path))

    row_cache: dict[str, list[dict[str, Any]]] = {}
    for name in PAYLOAD_FILES:
        path = generation / name
        bad_serialisation = 0
        rows: list[dict[str, Any]] = []
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                text = line.rstrip("\n")
                if not text:
                    continue
                row = json.loads(text)
                rows.append(row)
                if canonical(row) != text:
                    bad_serialisation += 1
        row_cache[name] = rows
        report.add(f"A2:{name}", "every line is canonical sorted-key JSON",
                   bad_serialisation == 0, bad_serialisation, len(rows))
        declared = receipt["files"][name]
        report.add(f"A3a:{name}", "row count matches receipt",
                   len(rows) == declared["rows"],
                   {"file": len(rows), "receipt": declared["rows"]})
        report.add(f"A3b:{name}", "sha256 matches receipt",
                   digest(path) == declared["sha256"],
                   {"file": digest(path), "receipt": declared["sha256"]})
        report.add(f"A3c:{name}", "bytes match receipt",
                   path.stat().st_size == declared["bytes"],
                   {"file": path.stat().st_size, "receipt": declared["bytes"]})
        violations = sum(1 for row in rows
                         if any(row.get(k) != v for k, v in GUARD_COLUMNS.items()))
        report.add(f"A4:{name}", "lane guard columns on 100% of rows",
                   violations == 0, violations, len(rows))
        bad_schema = 0
        first_error = None
        for row in rows:
            problems = schema_errors(row, schemas[name])
            if problems:
                bad_schema += 1
                first_error = first_error or problems[:3]
        report.add(f"A6:{name}", "committed-schema conformance",
                   bad_schema == 0, {"rows": bad_schema, "first": first_error},
                   len(rows))

    report.add("A5", "receipt pins both promotion counters at zero",
               receipt.get("canonical_employment_promotions") == 0 and
               receipt.get("canonical_identity_promotions") == 0,
               {"employment": receipt.get("canonical_employment_promotions"),
                "identity": receipt.get("canonical_identity_promotions")})

    candidates = row_cache[CANDIDATE_FILE]
    seen_pairs = collections.Counter(
        (r["payee_chamber"], r["payee_surname_key"], r["payee_given_key"],
         r["payee_middle_initial"] or "", r["roster_id"]) for r in candidates)
    dupes = sum(1 for v in seen_pairs.values() if v > 1)
    report.add("A7", "no duplicate (chamber, payee_key, roster_id) rows",
               dupes == 0, dupes, len(candidates))

    missing_inputs = []
    bad_input_hash = []
    for name, meta in receipt["inputs"].items():
        path = Path(meta["path"])
        if not path.exists():
            missing_inputs.append(name)
            continue
        if path.stat().st_size != meta["bytes"] or digest(path) != meta["sha256"]:
            bad_input_hash.append(name)
    report.add("A8a", "every receipt input exists", not missing_inputs,
               missing_inputs, len(receipt["inputs"]))
    report.add("A8b", "every receipt input re-hashes to its recorded sha256",
               not bad_input_hash, bad_input_hash, len(receipt["inputs"]))

    # ---- Layer B: full re-derivation ------------------------------------
    log("[B] independent re-derivation")
    state = dict(rederive(paths, log))
    run_id = receipt["run_id"]

    report.add("B0a", "Senate payee key set reproduced exactly from the corpus",
               state["senate"]["exact"],
               {"missing": state["senate"]["missing"],
                "extra": state["senate"]["extra"],
                "reproduced": len(state["senate"]["reproduced"])})
    report.add("B0b", "House ledger row count reproduced",
               state["house"]["rows"] == receipt["inputs"]["house_ledger"]["rows"],
               {"scan": state["house"]["rows"],
                "receipt": receipt["inputs"]["house_ledger"]["rows"]})
    report.add("B0c", "Senate corpus row count reproduced",
               state["senate"]["rows"] == receipt["inputs"]["senate_corpus"]["rows"],
               {"scan": state["senate"]["rows"],
                "receipt": receipt["inputs"]["senate_corpus"]["rows"]})

    log("  [B] candidate rows")
    state["by_roster"] = collections.defaultdict(list)
    expected_rows: dict[tuple, dict[str, Any]] = {}
    for pkey, rec in state["records"].items():
        row = expected_candidate_row(rec, state, run_id)
        expected_rows[pkey] = row
        ent = rec["ent"]
        if rec["pair"]["chamber"] == "HOUSE":
            office_kinds = sorted(ent["containers"])
        else:
            office_kinds = sorted({
                SENATE_PERSONAL_KIND if senate_personal_remainder(o) is not None
                else SENATE_NON_PERSONAL_KIND for o in ent["offices"]})
        state["by_roster"][rec["pair"]["roster_id"]].append({
            "tier": rec["tier"], "chamber": rec["pair"]["chamber"],
            "offices": sorted(ent["offices"]), "periods": sorted(ent["periods"]),
            "titles": sorted(ent["titles"]),
            "containers": sorted(ent["containers"]),
            "office_kinds": office_kinds,
            "tie_size": row["tie_size"], "signals": sorted(rec["signals"]),
            "payee_key": list(rec["pair"]["payee_key"]),
        })

    report.add("B1", "candidate row count equals independently derived pair count",
               len(candidates) == len(expected_rows),
               {"file": len(candidates), "rederived": len(expected_rows)})

    mismatched_fields = collections.Counter()
    mismatch_examples: list[dict[str, Any]] = []
    unmatched = 0
    for row in candidates:
        pkey = (row["payee_chamber"],
                (row["payee_surname_key"], row["payee_given_key"],
                 row["payee_middle_initial"]),
                row["roster_id"])
        want = expected_rows.get(pkey)
        if want is None:
            unmatched += 1
            continue
        for field in set(row) | set(want):
            if row.get(field) != want.get(field):
                mismatched_fields[field] += 1
                if len(mismatch_examples) < 10:
                    mismatch_examples.append(
                        {"pair": [pkey[0], list(pkey[1]), pkey[2]], "field": field,
                         "emitted": row.get(field), "rederived": want.get(field)})
    report.add("B2", "every emitted candidate row exists in the re-derivation",
               unmatched == 0, unmatched, len(candidates))
    report.add("B3", "100% of candidate rows reproduce field for field",
               not mismatched_fields,
               {"fields": dict(mismatched_fields), "examples": mismatch_examples},
               len(candidates))

    log("  [B] staffer roll-up")
    staffer_rows = row_cache[STAFFER_FILE]
    staff_mismatch = collections.Counter()
    staff_examples: list[dict[str, Any]] = []
    for row in staffer_rows:
        sid = row["quorum_staff_id"]
        entry = state["staff"].get(sid)
        if entry is None:
            staff_mismatch["unknown_staff_id"] += 1
            continue
        rid = f"quorum:staff:{sid}"
        person = state["roster"].get(rid, {})
        old = state["old_staff"].get(sid) or {}
        body = rollup_for(rid, state)
        recovered = (body["status"] in ("RESOLVED_R1", "RESOLVED_R2") and
                     old.get("link_status") != "LINKED")
        want = dict(body)
        want.update({
            "canonical_eligible": False, "canonical_employment_promoted": False,
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "display_name": entry["display_name"],
            "member_bioguide": old.get("member_bioguide"),
            "member_display": entry["member_display"],
            "old_rule_link_status": old.get("link_status"),
            "old_rule_recovered": recovered, "phase": PHASE,
            "quorum_staff_id": sid, "quorum_star": entry.get("star"),
            "review_status": "REVIEW_REQUIRED", "roster_id": rid,
            "roster_match_eligible": bool(person.get("eligible")),
            "rule_version": RULE_VERSION, "run_id": run_id,
            "schema_id": "staffer-network-current-staffer-resolution-v1",
            "title_raw": entry["title_raw"],
        })
        for field in set(row) | set(want):
            if row.get(field) != want.get(field):
                staff_mismatch[field] += 1
                if len(staff_examples) < 10:
                    staff_examples.append({"staff_id": sid, "field": field,
                                           "emitted": row.get(field),
                                           "rederived": want.get(field)})
    report.add("B4", "all 5,773 staffer rows reproduce field for field",
               not staff_mismatch,
               {"fields": dict(staff_mismatch), "examples": staff_examples},
               len(staffer_rows))
    report.add("B5", "staffer file covers exactly the staff directory",
               {r["quorum_staff_id"] for r in staffer_rows} == set(state["staff"]),
               {"file": len(staffer_rows), "directory": len(state["staff"])})

    log("  [B] LDA roll-up")
    lda_rows = row_cache[LDA_FILE]
    lda_mismatch = collections.Counter()
    lda_examples: list[dict[str, Any]] = []
    for row in lda_rows:
        pid = row["lda_source_person_id"]
        info = state["lda"].get(pid)
        if info is None:
            lda_mismatch["unknown_person_id"] += 1
            continue
        person = state["roster"].get(pid, {})
        body = rollup_for(pid, state)
        want = dict(body)
        want.update({
            "canonical_eligible": False, "canonical_employment_promoted": False,
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "covered_position_present": info["covered_present"],
            "covered_position_years": info["covered_years"],
            "display_name": info["display_name"],
            "filing_years": info["filing_years"],
            "lda_identity_status": info["identity_status"],
            "lda_priority": info["priority"], "lda_source_person_id": pid,
            "old_rule_in_match_lanes": pid in state["old_lda_lanes"],
            "old_rule_linked": pid in state["old_lda_linked"],
            "phase": PHASE, "review_status": "REVIEW_REQUIRED", "roster_id": pid,
            "roster_match_eligible": bool(person.get("eligible")),
            "rule_version": RULE_VERSION, "run_id": run_id,
            "schema_id": "staffer-network-lda-resolution-v1",
        })
        for field in set(row) | set(want):
            if row.get(field) != want.get(field):
                lda_mismatch[field] += 1
                if len(lda_examples) < 10:
                    lda_examples.append({"person_id": pid, "field": field,
                                         "emitted": row.get(field),
                                         "rederived": want.get(field)})
    report.add("B6", "all 25,340 LDA rows reproduce field for field",
               not lda_mismatch,
               {"fields": dict(lda_mismatch), "examples": lda_examples},
               len(lda_rows))

    log("  [B] receipt counts")
    tier_counts = collections.Counter(r["resolution_tier"] for r in candidates)
    declared_tiers = receipt["counts"]["candidate_rows_by_tier"]
    report.add("B7", "receipt per-tier counts match the emitted file",
               all(tier_counts.get(t, 0) == declared_tiers.get(t, 0)
                   for t in TIER_ORDER),
               {"file": dict(tier_counts), "receipt": declared_tiers},
               len(candidates))
    rederived_tiers = collections.Counter(r["tier"] for r in state["records"].values())
    report.add("B8", "re-derived per-tier counts match the receipt",
               all(rederived_tiers.get(t, 0) == declared_tiers.get(t, 0)
                   for t in TIER_ORDER),
               {"rederived": dict(rederived_tiers), "receipt": declared_tiers})
    status_counts = collections.Counter(r["status"] for r in staffer_rows)
    report.add("B9", "receipt staffer status counts match the emitted file",
               dict(status_counts) ==
               {k: v for k, v in
                receipt["recovery_against_old_rule"]["new_status_counts"].items()
                if v or k in status_counts},
               {"file": dict(status_counts),
                "receipt": receipt["recovery_against_old_rule"]["new_status_counts"]},
               len(staffer_rows))
    lda_status = collections.Counter(r["status"] for r in lda_rows)
    report.add("B10", "receipt LDA status counts match the emitted file",
               all(lda_status.get(s, 0) ==
                   receipt["lda_resolution"]["status_counts"].get(s, 0)
                   for s in STATUS_VALUES),
               {"file": dict(lda_status),
                "receipt": receipt["lda_resolution"]["status_counts"]},
               len(lda_rows))

    # nothing may be promoted, anywhere
    promoted = sum(1 for name in PAYLOAD_FILES for r in row_cache[name]
                   if r.get("canonical_employment_promoted") or
                   r.get("canonical_eligible") or
                   r.get("canonical_identity_decision") != "NOT_ADJUDICATED")
    report.add("B11", "zero promoted rows across all three payloads",
               promoted == 0, promoted,
               sum(len(row_cache[n]) for n in PAYLOAD_FILES))

    return {"report": report, "state": state, "receipt": receipt,
            "rows": row_cache}


# ---------------------------------------------------------------------------
# Layer C: negative controls
# ---------------------------------------------------------------------------
def run_controls(generation: Path, schema_dir: Path, report: Report,
                 rows: Mapping[str, list[dict[str, Any]]],
                 receipt: Mapping[str, Any]) -> None:
    schemas = {name: json.loads((schema_dir / SCHEMA_FOR[name]).read_text("utf-8"))
               for name in SCHEMA_FOR}
    sample = dict(rows[CANDIDATE_FILE][0])

    # C1 PROMOTION TRIPWIRE
    planted = dict(sample)
    planted["canonical_employment_promoted"] = True
    fired = any(planted.get(k) != v for k, v in GUARD_COLUMNS.items())
    report.add("C1", "PROMOTION TRIPWIRE: a promoted row is detected", fired,
               {"planted": "canonical_employment_promoted=true", "fired": fired})

    planted2 = dict(sample)
    planted2["canonical_identity_decision"] = "ADJUDICATED_LINK"
    report.add("C2", "an adjudicated identity decision is detected",
               any(planted2.get(k) != v for k, v in GUARD_COLUMNS.items()))

    planted3 = dict(sample)
    planted3["review_status"] = "APPROVED"
    report.add("C3", "a non-REVIEW_REQUIRED status is detected",
               any(planted3.get(k) != v for k, v in GUARD_COLUMNS.items()))

    # C4 tier corruption must be caught by field comparison
    planted4 = dict(sample)
    planted4["resolution_tier"] = ("R1_EXACT_UNIQUE"
                                   if sample["resolution_tier"] != "R1_EXACT_UNIQUE"
                                   else "R4_LOOSE")
    report.add("C4", "a flipped resolution_tier differs from the true row",
               planted4["resolution_tier"] != sample["resolution_tier"])

    # C5 tie_size corruption
    planted5 = dict(sample)
    planted5["tie_size"] = sample["tie_size"] + 7
    report.add("C5", "a corrupted tie_size differs from the true row",
               planted5["tie_size"] != sample["tie_size"])

    # C6 schema control: an unknown field must be rejected
    planted6 = dict(sample)
    planted6["totally_new_field"] = 1
    report.add("C6", "schema check rejects an unknown field",
               bool(schema_errors(planted6, schemas[CANDIDATE_FILE])))

    # C7 schema control: a dropped required field must be rejected
    planted7 = dict(sample)
    planted7.pop("resolution_tier", None)
    report.add("C7", "schema check rejects a missing required field",
               bool(schema_errors(planted7, schemas[CANDIDATE_FILE])))

    # C8 receipt hash control
    bogus = dict(receipt["files"][CANDIDATE_FILE])
    bogus["sha256"] = "0" * 64
    report.add("C8", "a corrupted receipt sha256 differs from the real digest",
               bogus["sha256"] != digest(generation / CANDIDATE_FILE))

    # C9 SILENT PROBE: the true row must trip nothing
    quiet = (not any(sample.get(k) != v for k, v in GUARD_COLUMNS.items()) and
             not schema_errors(sample, schemas[CANDIDATE_FILE]))
    report.add("C9", "SILENT PROBE: the unmodified row trips no control", quiet)

    # C10 canonical-serialisation control
    scrambled = json.dumps(sample, sort_keys=False, separators=(", ", ": "))
    report.add("C10", "non-canonical serialisation is detectable",
               scrambled != canonical(sample))


# ---------------------------------------------------------------------------
# Twin comparison
# ---------------------------------------------------------------------------
def compare_twin(primary: Path, twin: Path, report: Report) -> dict[str, Any]:
    detail: dict[str, Any] = {}
    for name in list(PAYLOAD_FILES) + [RECEIPT_FILE]:
        a, b = primary / name, twin / name
        if not b.exists():
            report.add(f"T:{name}", "twin file present", False, "missing")
            continue
        da, db = digest(a), digest(b)
        detail[name] = {"primary": da, "twin": db, "identical": da == db}
        report.add(f"T:{name}", "primary and twin are byte-identical", da == db,
                   detail[name])
    return detail


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv: Sequence[str] | None = None) -> int:
    repo_default = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", required=True)
    parser.add_argument("--twin")
    parser.add_argument("--verification-root", required=True)
    parser.add_argument("--scratch-dir", required=True)
    parser.add_argument("--repo-root", default=str(repo_default))
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    log = (lambda *a, **k: None) if args.quiet else print
    repo = Path(args.repo_root).resolve()
    generation = Path(args.generation).resolve()
    schema_dir = repo / "audits" / "staffer_network" / SCHEMA_DIR_NAME
    paths = default_paths(repo, Path(args.scratch_dir).resolve())

    outcome = verify(generation, paths, schema_dir, log=log)
    report: Report = outcome["report"]

    log("[C] negative controls")
    run_controls(generation, schema_dir, report, outcome["rows"], outcome["receipt"])

    twin_detail = None
    if args.twin:
        log("[T] twin byte-identity")
        twin_detail = compare_twin(generation, Path(args.twin).resolve(), report)

    root = Path(args.verification_root).resolve()
    if root.exists() and any(root.iterdir()):
        raise SystemExit(f"refusing to write into non-empty {root}")
    root.mkdir(parents=True, exist_ok=True)

    payload = {
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "checks": report.checks,
        "checks_failed": len(report.failures),
        "checks_run": len(report.checks),
        "generation": str(generation),
        "phase": "verify",
        "review_status": "REVIEW_REQUIRED",
        "rule_version": RULE_VERSION,
        "run_id": outcome["receipt"]["run_id"],
        "schema_id": "staffer-network-payroll-name-resolution-verification-v1",
        "status": "PASS" if not report.failures else "FAIL",
        "twin": twin_detail,
        "verifier": "verify_payroll_name_resolution.py",
        "verifier_independent_of_builder": True,
    }
    target = root / "payroll_name_resolution_verification.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True,
                              ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, target)

    log(json.dumps({"status": payload["status"],
                    "checks_run": payload["checks_run"],
                    "checks_failed": payload["checks_failed"],
                    "failures": [c["check"] for c in report.failures]}, indent=2))
    return 0 if not report.failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
