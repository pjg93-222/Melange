#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify a ``current_staffer_links_*`` generation.

This module does NOT import ``build_current_staffer_links.py``.  It re-derives
every emitted row from the five declared sources -- the Quorum staff directory,
the House personnel ledger, the Senate payroll candidate file, the nickname
table and the congress-legislators roster -- and compares the result to what the
generation actually says.  The expectation therefore comes from a DIFFERENT
source than the artifact being checked, which is the property a self-describing
artifact's check must have (CONSTRAINTS; DE-012).

Checks, in the order the receipt reports them:

  V1  INPUT BINDING.  Every input the generation's receipt hash-binds is present
      on disk NOW with the sha256 the receipt recorded.  A source that moved
      under the generation is a failure, not a warning.
  V2  CONSERVATION.  Exactly one link row per staff-directory entry, 5,773 of
      them, ids distinct, and one candidate row per (staffer, match) pair.
  V3  FULL RE-DERIVATION.  Every one of the 5,773 rows is rebuilt from the
      sources -- member resolution, office facts, name classification, tier,
      tie, demotion -- and compared field by field, including the complete match
      list.  100% of rows, not a sample.
  V4  TIE HANDLING.  tie_size equals the number of distinct payroll identities
      supporting the pre-demotion tier; ambiguous is exactly tie_size > 1; no
      RESOLVED_* status survives on an ambiguous row; a demoted row lands on the
      declared demotion target.
  V5  TRIPWIRE, WITH A NEGATIVE CONTROL.  Every row in both payloads carries
      review_status REVIEW_REQUIRED, canonical_eligible false,
      canonical_employment_promoted false and canonical_identity_decision
      NOT_ADJUDICATED; the receipt pins both promotion counters at zero.  The
      check is then run against a synthetic PROMOTED row and must REJECT it --
      a tripwire that cannot fire is not a tripwire (DE-011).
  V6  LANGUAGE LAW.  Both payloads are rescanned; authored field names and
      authored values must contain none of the banned tokens, and the verbatim
      occurrence counts must equal the receipt's.
  V7  DETERMINISM.  gzip member mtime 0, LF line endings, lexicographic key
      order, and the declared sort order actually holds over the emitted rows.
  V8  RECEIPT AGREEMENT.  Every count block the receipt publishes is recomputed
      from the payload and must agree.

Exit code 0 only when every check passes.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

LINK_FILE = "current_staffer_links.ndjson.gz"
CANDIDATE_FILE = "current_staffer_match_candidates.ndjson.gz"
RECEIPT_FILE = "current_staffer_links_receipt.json"
VERIFICATION_FILE = "current_staffer_links_verification_receipt.json"
VERIFICATION_SCHEMA = "staffer-network-current-staffer-links-verification-receipt-v2"

EXPECTED_CURRENT_STAFFERS = 5773
BANNED_TOKENS = ("access", "causal", "friend", "ideolog", "influence", "predict")
VERBATIM_LEAF_NAMES = frozenset(
    {
        "display_name", "first", "last", "member_display", "office_key", "office_raw",
        "payroll_first", "payroll_identity_key", "payroll_last", "title_raw", "titles",
    }
)
UNPROMOTED_ALLOWED = (False, 0, None, "", "NOT_ADJUDICATED")

TIER_T1 = "T1_OWN_MEMBER_EXACT"
TIER_T2 = "T2_NON_MEMBER_OFFICE_EXACT"
TIER_T3 = "T3_OTHER_MEMBER_EXACT"
TIER_T4A = "T4A_VARIANT_OWN_MEMBER"
TIER_T4B = "T4B_VARIANT_PERIOD_CORROBORATED"
TIER_T5 = "T5_WEAK_CANDIDATE"
TIER_PRECEDENCE = (TIER_T1, TIER_T2, TIER_T4A, TIER_T4B, TIER_T3, TIER_T5)
TIER_RANK = {tier: index for index, tier in enumerate(TIER_PRECEDENCE)}
TIER_STATUS = {
    TIER_T1: "RESOLVED_T1", TIER_T2: "RESOLVED_T2",
    TIER_T4A: "RESOLVED_T4", TIER_T4B: "RESOLVED_T4",
    TIER_T3: "CANDIDATE_T3", TIER_T5: "CANDIDATE_T5",
}
RESOLVED_STATUSES = ("RESOLVED_T1", "RESOLVED_T2", "RESOLVED_T4")
TIE_DEMOTION = {
    TIER_T1: TIER_T3, TIER_T2: TIER_T3, TIER_T4A: TIER_T5, TIER_T4B: TIER_T5,
}

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
    CLASS_EXACT, CLASS_PUNCT, CLASS_MIDDLE_CONFLICT, CLASS_COMPOUND, CLASS_NICKNAME,
    CLASS_PREFIX, CLASS_MIDDLE, CLASS_INITIAL_ONLY, CLASS_INITIAL_SHARED,
)
CLASS_RANK = {name: index for index, name in enumerate(CLASS_ORDER)}
VARIANT_CLASSES = frozenset(
    {CLASS_PUNCT, CLASS_MIDDLE_CONFLICT, CLASS_COMPOUND, CLASS_NICKNAME, CLASS_PREFIX, CLASS_MIDDLE}
)
T2_ELIGIBLE = frozenset({"admin", "committee", "leadership", "member_organization"})

SUFFIX_WORDS = frozenset(
    {"jr", "sr", "ii", "iii", "iv", "v", "md", "phd", "esq", "dds", "jd", "dvm", "rn", "cpa"}
)
PARTICLE_WORDS = frozenset(
    {
        "abu", "al", "bin", "da", "das", "de", "del", "dela", "della", "den", "der",
        "di", "dos", "du", "ibn", "la", "le", "mac", "mc", "saint", "st", "ten",
        "ter", "van", "vande", "vander", "von",
    }
)
WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['\-][A-Za-z0-9]+)*")


# ---------------------------------------------------------------------------
# Independent primitives
# ---------------------------------------------------------------------------
def ascii_fold(value: Any) -> str:
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return stripped.encode("ascii", "ignore").decode("ascii")


def words(value: Any) -> list[str]:
    return [w for w in (m.strip("-'") for m in WORD_RE.findall(ascii_fold(value).lower())) if w]


def squeeze(value: Any) -> str:
    return "".join(ch for ch in ascii_fold(value).lower() if ch.isalnum())


def trim_suffix(items: Sequence[str]) -> list[str]:
    result = list(items)
    while len(result) > 1 and result[-1] in SUFFIX_WORDS:
        result.pop()
    return result


def split_person_name(value: Any) -> tuple[str, list[str], list[str]]:
    items = trim_suffix(words(value))
    if not items:
        return "", [], []
    if len(items) == 1:
        return items[0], [], []
    cut = len(items) - 1
    while cut > 1 and items[cut - 1] in PARTICLE_WORDS:
        cut -= 1
    return items[0], items[1:cut], items[cut:]


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ndjson_gz_rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ---------------------------------------------------------------------------
# Nickname table (short form -> single formal form; multi-formal DROPPED)
# ---------------------------------------------------------------------------
def read_nicknames(path: Path) -> tuple[dict[str, str], dict[str, frozenset[str]]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = payload.get("entries") if isinstance(payload, Mapping) else None
    if not isinstance(entries, Mapping):
        entries = payload if isinstance(payload, Mapping) else {}
    table: dict[str, str] = {}
    for short, formal in entries.items():
        if not isinstance(short, str):
            continue
        forms = [formal] if isinstance(formal, str) else [
            f for f in (formal or []) if isinstance(f, str)
        ] if isinstance(formal, list) else []
        if len(forms) != 1:
            continue
        left, right = squeeze(short), squeeze(forms[0])
        if left and right:
            table[left] = right
    linked: defaultdict[str, set[str]] = defaultdict(set)
    for short, formal in table.items():
        linked[short].add(formal)
        linked[formal].add(short)
    for anchor in list(linked):
        for member in list(linked[anchor]):
            linked[member] |= linked[anchor] - {member}
    return table, {k: frozenset(v) for k, v in linked.items()}


def canonical_first(value: Any, table: Mapping[str, str]) -> str:
    key = squeeze(value)
    return table.get(key, key)


# ---------------------------------------------------------------------------
# Roster
# ---------------------------------------------------------------------------
class Roster:
    def __init__(self, directory: Path, table: Mapping[str, str]) -> None:
        self.table = dict(table)
        people: list[dict[str, Any]] = []
        for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
            path = Path(directory) / filename
            if not path.is_file():
                continue
            for entry in yaml.safe_load(path.read_text(encoding="utf-8")) or []:
                bioguide = ((entry or {}).get("id") or {}).get("bioguide")
                if not isinstance(bioguide, str) or not bioguide:
                    continue
                name = entry.get("name") or {}
                spans = []
                for term in entry.get("terms") or []:
                    start, end = str(term.get("start", ""))[:10], str(term.get("end", ""))[:10]
                    if len(start) == 10 and len(end) == 10:
                        spans.append((start, end, str(term.get("type", ""))))
                if not spans:
                    continue
                spans.sort()
                forms = {canonical_first(name.get("first"), self.table)}
                for field in ("nickname", "middle"):
                    if name.get(field):
                        forms.add(canonical_first(name.get(field), self.table))
                for token in words(name.get("official_full")):
                    forms.add(canonical_first(token, self.table))
                forms.discard("")
                people.append(
                    {
                        "bioguide": bioguide,
                        "surname_key": squeeze(name.get("last")),
                        "forms": frozenset(forms),
                        "terms": spans,
                        "types": frozenset(t for _s, _e, t in spans),
                        "low": min(int(s[:4]) for s, _e, _t in spans),
                        "high": max(int(e[:4]) for _s, e, _t in spans),
                        "current": filename.endswith("current.yaml"),
                    }
                )
        people.sort(key=lambda item: item["bioguide"])
        self.people = people
        self.by_surname: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for person in people:
            self.by_surname[person["surname_key"]].append(person)
        self.surname_keys = frozenset(self.by_surname)
        self.by_bioguide = {person["bioguide"]: person for person in people}

    def terms(self, bioguide: str | None) -> Sequence[tuple[str, str, str]]:
        person = self.by_bioguide.get(bioguide or "")
        return person["terms"] if person else ()


TRAILING_PAREN = re.compile(r"\s*\([^)]*\)\s*$")


def name_ladder(
    tokens: Sequence[str], roster: Roster, chamber: str | None, low: int | None, high: int | None
) -> tuple[str | None, str]:
    """Independent restatement of the A6 resolution ladder."""

    tokens = [t for t in tokens if t]
    if not tokens:
        return None, "UNRESOLVED_OFFICE_NAME_NOT_PARSED"
    wanted = {"house": "rep", "senate": "sen"}.get(chamber or "")

    def candidates(surname_key: str) -> list[dict[str, Any]]:
        pool = list(roster.by_surname.get(surname_key, ()))
        if wanted:
            typed = [p for p in pool if wanted in p["types"]]
            if typed:
                pool = typed
        if low is not None and high is not None:
            dated = [p for p in pool if p["low"] <= high and p["high"] >= low]
            if dated:
                pool = dated
        return pool

    def try_tokens(items: Sequence[str]) -> tuple[str | None, str] | None:
        fallback = None
        for width in range(min(3, len(items)), 0, -1):
            surname_key = squeeze("".join(items[-width:]))
            if not surname_key:
                continue
            pool = candidates(surname_key)
            if not pool:
                continue
            givens = [g for g in items[: len(items) - width] if g]
            if not givens:
                if len(pool) == 1:
                    return pool[0]["bioguide"], "UNIQUE_SURNAME_NO_FIRST_NAME"
                fallback = fallback or (None, "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME")
                continue
            saw_multi = False
            for given in givens:
                target = canonical_first(given, roster.table)
                if len(target) < 2:
                    continue
                hits = [p for p in pool if target in p["forms"]]
                if len(hits) == 1:
                    return hits[0]["bioguide"], "SURNAME_AND_FIRST_NAME_FORM"
                if len(hits) > 1:
                    saw_multi = True
            for given in givens:
                letter = squeeze(given)[:1]
                if not letter:
                    continue
                hits = [p for p in pool if any(f.startswith(letter) for f in p["forms"])]
                if len(hits) == 1:
                    return hits[0]["bioguide"], "SURNAME_AND_FIRST_INITIAL"
            if len(pool) == 1:
                return pool[0]["bioguide"], "UNIQUE_SURNAME_FIRST_NAME_NOT_MATCHED"
            fallback = fallback or (
                None,
                "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE" if saw_multi
                else "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER",
            )
        return fallback

    direct = try_tokens(tokens)
    if direct is not None and direct[0] is not None:
        return direct
    for rebuilt in resplit_variants(tokens, roster):
        healed = try_tokens(rebuilt)
        if healed is not None and healed[0] is not None:
            return healed[0], healed[1] + "_AFTER_LETTER_SPLIT_REPAIR"
    if direct is not None:
        return direct
    return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"


def resplit_variants(tokens: Sequence[str], roster: Roster) -> list[list[str]]:
    if not tokens:
        return []
    out: list[list[str]] = []
    seen: set[tuple[str, ...]] = {tuple(tokens)}

    def add(head: str, tail: str, prefix: Sequence[str]) -> None:
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

    tail_token = squeeze(tokens[-1])
    for cut in range(1, len(tail_token)):
        add(tail_token[:cut], tail_token[cut:], tokens[:-1])
    if len(tokens) >= 2:
        pair = squeeze(tokens[-2] + tokens[-1])
        for cut in range(0, len(pair)):
            add(pair[:cut], pair[cut:], tokens[:-2])
    return out


# ---------------------------------------------------------------------------
# Office facts
# ---------------------------------------------------------------------------
SENATOR_PATTERN = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_PATTERN = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
SUFFIX_TAIL = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
HONRAW_PATTERN = re.compile(r"^HONRAW:HON\.?\s*(.+)$", re.IGNORECASE)
LEADERSHIP_MARKERS = (
    "CAUCUS", "MAJORITY CONFERENCE", "MAJORITY LEADER", "MAJORITY WHIP",
    "MINORITY CONFERENCE", "MINORITY LEADER", "MINORITY WHIP", "PRES PRO TEM",
    "PRESIDENT PRO TEMPORE", "SECRETARY FOR THE MAJORITY",
    "SECRETARY FOR THE MINORITY", "VICE PRESIDENT",
)


def senate_key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("’", "'").strip()).upper()


def senate_kind(key: str) -> str:
    upper = (key or "").strip().upper()
    if not upper:
        return "unresolved"
    if SENATOR_PATTERN.match(upper) or INTERN_PATTERN.match(upper):
        return "member_office"
    if "COMMITTEE" in upper or upper == "APPROPRIATIONS":
        return "committee"
    if any(marker in upper for marker in LEADERSHIP_MARKERS):
        return "leadership"
    return "admin"


def office_name_words(remainder: str) -> list[str]:
    text = SUFFIX_TAIL.sub("", TRAILING_PAREN.sub("", remainder or "").strip()).strip()
    return [t for t in (squeeze(p) for p in text.split()) if t and t not in SUFFIX_WORDS]


def office_person_words(chamber: str, office_key: str) -> list[str]:
    if chamber == "senate":
        match = SENATOR_PATTERN.match(office_key) or INTERN_PATTERN.match(office_key)
        return office_name_words(match.group(1)) if match else []
    match = HONRAW_PATTERN.match(office_key)
    return office_name_words(match.group(1)) if match else []


QUARTER_PATTERN = re.compile(r"^(\d{4})Q([1-4])$")
DATE_PATTERN = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")


def window_of(chamber: str, token: str) -> tuple[str, str] | None:
    if chamber == "house":
        match = QUARTER_PATTERN.match(str(token or "").strip().upper())
        if not match:
            return None
        year, quarter = int(match.group(1)), int(match.group(2))
        first_month = 3 * quarter - 2
        last_month = 3 * quarter
        last_day = 31 if last_month in (3, 12) else 30
        return f"{year:04d}-{first_month:02d}-01", f"{year:04d}-{last_month:02d}-{last_day:02d}"
    match = DATE_PATTERN.match(str(token or "").strip())
    if not match:
        return None
    year, month = int(match.group(1)), int(match.group(2))
    if month >= 10:
        return f"{year:04d}-10-01", f"{year + 1:04d}-03-31"
    if month <= 3:
        return f"{year - 1:04d}-10-01", f"{year:04d}-03-31"
    return f"{year:04d}-04-01", f"{year:04d}-09-30"


def served_during(chamber: str, periods: Sequence[str], terms: Sequence[tuple[str, str, str]]) -> bool:
    for token in periods:
        window = window_of(chamber, token)
        if window is None:
            continue
        for term_start, term_end, _kind in terms:
            if window[0] <= term_end and window[1] >= term_start:
                return True
    return False


# ---------------------------------------------------------------------------
# Re-derivation
# ---------------------------------------------------------------------------
def senate_name_parts(value: Any) -> tuple[list[str], str, str | None]:
    text = str(value or "")
    if "," in text:
        head, _, tail = text.partition(",")
        surname, rest = trim_suffix(words(head)), trim_suffix(words(tail))
    else:
        items = trim_suffix(words(text))
        if len(items) < 2:
            return [], "", None
        surname, rest = [items[-1]], items[:-1]
    if not surname or not rest:
        return [], "", None
    return surname, rest[0], (squeeze(rest[1])[:1] or None if len(rest) > 1 else None)


def house_name_parts(parse: Mapping[str, Any]) -> tuple[list[str], str, str | None]:
    surname = trim_suffix(words(parse.get("surname")))
    given = words(parse.get("given"))
    if not surname or not given:
        return [], "", None
    initial = squeeze(parse.get("middle_initial"))[:1] or None
    if initial is None:
        extra = parse.get("middle_tokens") or []
        if extra:
            initial = squeeze(extra[0])[:1] or None
    return surname, given[0], initial


def name_class(
    staffer: Mapping[str, Any], payroll_surname: str, payroll_given: str,
    linked: Mapping[str, frozenset[str]],
) -> str | None:
    p_last = squeeze(payroll_surname)
    parts = words(payroll_surname)
    p_last_tail = squeeze(parts[-1]) if parts else ""
    p_first = squeeze(payroll_given)
    s_last_raw, s_last, s_tail = staffer["last_raw"], staffer["last_key"], staffer["last_tail"]
    exact_last = bool(payroll_surname) and payroll_surname == s_last_raw
    punct_last = bool(p_last) and p_last == s_last
    token_last = bool(p_last) and p_last != s_last and (
        p_last == s_tail or p_last_tail == s_last or p_last_tail == s_tail
        or (s_tail and p_last.endswith(s_tail)) or (p_last_tail and s_last.endswith(p_last_tail))
    )
    if not (exact_last or punct_last or token_last):
        return None
    exact_first = bool(payroll_given) and payroll_given == staffer["first_raw"]
    punct_first = bool(p_first) and p_first == staffer["first_key"]
    if exact_last and exact_first:
        return CLASS_EXACT
    if (exact_last or punct_last) and (exact_first or punct_first):
        return CLASS_PUNCT
    if token_last and (exact_first or punct_first):
        return CLASS_COMPOUND
    if p_first and staffer["first_key"] and p_first != staffer["first_key"] and (
        staffer["first_key"] in linked.get(p_first, frozenset())
        or p_first in linked.get(staffer["first_key"], frozenset())
    ):
        return CLASS_NICKNAME
    if (
        p_first and staffer["first_key"] and len(p_first) >= 2 and len(staffer["first_key"]) >= 2
        and p_first != staffer["first_key"]
        and (p_first.startswith(staffer["first_key"]) or staffer["first_key"].startswith(p_first))
    ):
        return CLASS_PREFIX
    if p_first and p_first in staffer["middle_keys"]:
        return CLASS_MIDDLE
    if p_first and staffer["first_key"] and p_first[0] == staffer["first_key"][0] and (
        len(p_first) == 1 or len(staffer["first_key"]) == 1
    ):
        return CLASS_INITIAL_ONLY
    if p_first and staffer["first_key"] and p_first[0] == staffer["first_key"][0]:
        return CLASS_INITIAL_SHARED
    return None


def tier_for(
    match_class: str, kind: str, office_bioguide: str | None, own_bioguide: str | None,
    chamber: str, periods: Sequence[str], own_terms: Sequence[tuple[str, str, str]],
) -> tuple[str, str]:
    own = kind == "member_office" and bool(office_bioguide) and office_bioguide == own_bioguide
    dated = kind in T2_ELIGIBLE and bool(own_bioguide) and served_during(chamber, periods, own_terms)
    if match_class == CLASS_EXACT:
        if own:
            return TIER_T1, "OWN_MEMBER_OFFICE"
        if dated:
            return TIER_T2, "MEMBER_SERVICE_PERIOD_OVERLAP"
        if kind in ("member_office", "member_office_unresolved"):
            return TIER_T3, "NONE"
        return TIER_T5, "NONE"
    if match_class in VARIANT_CLASSES:
        if own:
            return TIER_T4A, "OWN_MEMBER_OFFICE"
        if dated:
            return TIER_T4B, "MEMBER_SERVICE_PERIOD_OVERLAP"
        return TIER_T5, "NONE"
    return TIER_T5, "NONE"


def identity_split(bucket: Mapping[str | None, Mapping[str, Any]]) -> list[dict[str, Any]]:
    labelled = sorted(k for k in bucket if k)
    if len(labelled) <= 1:
        periods: set[str] = set()
        titles: Counter = Counter()
        rows = 0
        for entry in bucket.values():
            periods |= set(entry["periods"])
            titles += Counter(entry["titles"])
            rows += entry["rows"]
        return [{"mi": labelled[0] if labelled else None, "periods": periods,
                 "titles": titles, "rows": rows}]
    result = [
        {"mi": k, "periods": set(bucket[k]["periods"]), "titles": Counter(bucket[k]["titles"]),
         "rows": bucket[k]["rows"]}
        for k in labelled
    ]
    if None in bucket:
        result.append({"mi": None, "periods": set(bucket[None]["periods"]),
                       "titles": Counter(bucket[None]["titles"]), "rows": bucket[None]["rows"]})
    return result


def rederive(paths: Mapping[str, Path]) -> dict[str, Any]:
    """Rebuild every link row from the sources.  Returns {staff_id: row}."""

    table, linked = read_nicknames(paths["nickname_table"])
    roster = Roster(paths["roster_dir"], table)

    directory = json.loads(Path(paths["staff_directory"]).read_text(encoding="utf-8"))
    entries: list[dict[str, Any]] = []
    for member_display in sorted(directory):
        for record in directory[member_display] or []:
            if not isinstance(record, Mapping):
                continue
            staff_id, name = record.get("id"), record.get("n")
            if staff_id is None or not isinstance(name, str) or not name.strip():
                continue
            title = record.get("t")
            entries.append(
                {
                    "member_display": str(member_display),
                    "quorum_staff_id": str(staff_id).strip(),
                    "display_name": name.strip(),
                    "title_raw": re.sub(r"\s+", " ", str(title)).strip() if title else None,
                }
            )
    entries.sort(key=lambda item: (item["member_display"], item["display_name"], item["quorum_staff_id"]))

    members: dict[str, tuple[str | None, str]] = {}
    for member_display in sorted({item["member_display"] for item in entries}):
        first, middles, surname = split_person_name(member_display)
        attempts = [list(surname)] + [
            list(middles[len(middles) - w:]) + list(surname) for w in range(1, len(middles) + 1)
        ]
        outcome: tuple[str | None, str] = (None, "UNRESOLVED_MEMBER")
        for candidate in attempts:
            bioguide, method = name_ladder(
                [first] + candidate, roster, None, 2025, max(2026, date.today().year)
            )
            if bioguide is not None:
                outcome = (bioguide, method)
                break
        if outcome[0] is None:
            for candidate in attempts:
                pool = [p for p in roster.by_surname.get(squeeze("".join(candidate)), ()) if p["current"]]
                if len(pool) == 1:
                    outcome = (pool[0]["bioguide"], "UNIQUE_CURRENT_ROSTER_SURNAME")
                    break
        members[member_display] = outcome

    staffers = []
    for entry in entries:
        first, middles, surname = split_person_name(entry["display_name"])
        bioguide, method = members[entry["member_display"]]
        staffers.append(
            {
                **entry,
                "first_raw": ascii_fold(first).lower(),
                "first_key": squeeze(first),
                "middle_keys": frozenset(squeeze(m) for m in middles if squeeze(m)),
                "middle_letters": frozenset(squeeze(m)[:1] for m in middles if squeeze(m)),
                "middle_initial": (squeeze(middles[0])[:1] or None) if middles else None,
                "last_raw": " ".join(surname),
                "last_key": squeeze("".join(surname)),
                "last_tail": squeeze(surname[-1]) if surname else "",
                "bioguide": bioguide,
                "member_method": method,
                "terms": roster.terms(bioguide),
            }
        )

    wanted_surnames = set()
    for staffer in staffers:
        wanted_surnames |= {staffer["last_key"], staffer["last_tail"]} - {""}

    groups: dict[tuple[str, str, str, str], dict[str | None, dict[str, Any]]] = {}
    offices: dict[tuple[str, str], dict[str, Any]] = {}
    source_counts: Counter = Counter()

    def note_office(chamber: str, key: str, raw: Any, kind: Any, bioguide: Any, period: Any) -> None:
        meta = offices.get((chamber, key))
        text = str(raw or "")
        if meta is None:
            meta = offices[(chamber, key)] = {
                "kind_source": kind, "bioguide_source": bioguide, "raw": text, "periods": set()
            }
        elif text and (not meta["raw"] or text < meta["raw"]):
            meta["raw"] = text
        if period:
            meta["periods"].add(str(period))

    def note_person(
        chamber: str, key: str, surname: Sequence[str], given: str, initial: str | None,
        period: Any, title: Any
    ) -> None:
        joined = " ".join(surname)
        collapsed = squeeze(joined)
        tail = squeeze(surname[-1]) if surname else ""
        if collapsed not in wanted_surnames and tail not in wanted_surnames:
            return
        source_counts[f"{chamber}_rows_reaching_a_staffer_surname"] += 1
        bucket = groups.setdefault((chamber, key, joined, ascii_fold(given).lower()), {})
        slot = bucket.setdefault(initial, {"periods": set(), "titles": Counter(), "rows": 0})
        if period:
            slot["periods"].add(str(period))
        if title:
            slot["titles"][str(title)] += 1
        slot["rows"] += 1

    for row in ndjson_gz_rows(paths["house_personnel_observations"]):
        source_counts["house_rows"] += 1
        key = row.get("office_key")
        if not isinstance(key, str) or not key:
            source_counts["house_rows_without_office_key"] += 1
            continue
        note_office("house", key, row.get("office_raw"), row.get("container_kind"),
                    row.get("member_bioguide"), row.get("quarter"))
        surname, given, initial = house_name_parts(row.get("payee_parse") or {})
        if not surname or not given:
            source_counts["house_rows_without_a_parsed_payee"] += 1
            continue
        note_person("house", key, surname, given, initial, row.get("quarter"), row.get("title_raw"))

    for row in ndjson_gz_rows(paths["senate_payroll_candidates"]):
        source_counts["senate_rows"] += 1
        key = senate_key(row.get("office_raw"))
        if not key:
            source_counts["senate_rows_without_office_key"] += 1
            continue
        note_office("senate", key, row.get("office_raw"), senate_kind(key), None,
                    row.get("report_period_start"))
        surname, given, initial = senate_name_parts(row.get("payee_name_raw"))
        if not surname or not given:
            source_counts["senate_rows_without_a_parsed_payee"] += 1
            continue
        note_person("senate", key, surname, given, initial, row.get("report_period_start"),
                    row.get("title_candidate") or row.get("title_raw"))

    office_facts: dict[tuple[str, str], dict[str, Any]] = {}
    office_methods: Counter = Counter()
    for (chamber, key), meta in sorted(offices.items()):
        kind = meta["kind_source"] or "unresolved"
        bioguide = meta["bioguide_source"]
        method = "HOUSE_LEDGER" if bioguide else None
        if kind in ("member_office", "member_office_unresolved") and not bioguide:
            years = [int(str(p)[:4]) for p in meta["periods"] if str(p)[:4].isdigit()]
            low, high = (min(years), max(years)) if years else (None, None)
            bioguide, method = name_ladder(
                office_person_words(chamber, key), roster, chamber, low, high
            )
            kind = "member_office" if bioguide else "member_office_unresolved"
        office_methods[f"{chamber}:{method or 'NONE'}"] += 1
        office_facts[(chamber, key)] = {"kind": kind, "bioguide": bioguide, "raw": meta["raw"]}

    lookup: defaultdict[str, list[tuple[str, str, str, str]]] = defaultdict(list)
    for key in groups:
        joined = key[2]
        collapsed = squeeze(joined)
        parts = words(joined)
        tail = squeeze(parts[-1]) if parts else ""
        lookup[collapsed].append(key)
        if tail and tail != collapsed:
            lookup[tail].append(key)

    rebuilt: dict[str, dict[str, Any]] = {}
    for staffer in staffers:
        reached: list[tuple[str, str, str, str]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for probe in (staffer["last_key"], staffer["last_tail"]):
            if not probe:
                continue
            for key in lookup.get(probe, ()):
                if key not in seen:
                    seen.add(key)
                    reached.append(key)
        matches: list[dict[str, Any]] = []
        for key in sorted(reached):
            chamber, office_key, surname_raw, given_raw = key
            base = name_class(staffer, surname_raw, given_raw, linked)
            if base is None:
                continue
            facts = office_facts[(chamber, office_key)]
            for identity in identity_split(groups[key]):
                initial = identity["mi"]
                conflict = bool(
                    staffer["middle_letters"] and initial
                    and initial not in staffer["middle_letters"]
                )
                effective = CLASS_MIDDLE_CONFLICT if (conflict and base == CLASS_EXACT) else base
                periods = sorted(identity["periods"])
                tier, corroboration = tier_for(
                    effective, facts["kind"], facts["bioguide"], staffer["bioguide"],
                    chamber, periods, staffer["terms"],
                )
                if facts["kind"] == "member_office" and facts["bioguide"]:
                    scope = f"member:{chamber}:{facts['bioguide']}"
                else:
                    scope = f"office:{chamber}:{office_key}"
                matches.append(
                    {
                        "chamber": chamber,
                        "container_kind": facts["kind"],
                        "corroboration": corroboration,
                        "match_class": effective,
                        "match_class_before_middle_initial_test": base,
                        "member_bioguide": facts["bioguide"],
                        "middle_initial_conflict": conflict,
                        "office_key": office_key,
                        "office_raw": facts["raw"],
                        "payroll_first": given_raw,
                        "payroll_identity_key": "|".join(
                            [scope, squeeze(surname_raw), squeeze(given_raw), initial or ""]
                        ),
                        "payroll_last": surname_raw,
                        "payroll_middle_initial": initial,
                        "period_count": len(periods),
                        "period_first": periods[0] if periods else None,
                        "period_last": periods[-1] if periods else None,
                        "periods": periods,
                        "row_count": identity["rows"],
                        "tier": tier,
                        "titles": [
                            title for title, _n in sorted(
                                identity["titles"].items(), key=lambda item: (-item[1], item[0])
                            )
                        ],
                    }
                )
        matches.sort(
            key=lambda item: (
                TIER_RANK[item["tier"]], CLASS_RANK[item["match_class"]], item["chamber"],
                item["office_key"], item["payroll_last"], item["payroll_first"],
                item["payroll_middle_initial"] or "",
            )
        )
        if matches:
            pre = min(matches, key=lambda item: TIER_RANK[item["tier"]])["tier"]
            supporting = [item for item in matches if item["tier"] == pre]
            tie = len({item["payroll_identity_key"] for item in supporting})
            ambiguous = tie > 1
            demoted = ambiguous and pre in TIE_DEMOTION
            final = TIE_DEMOTION[pre] if demoted else pre
            status = TIER_STATUS[final]
        else:
            pre = final = None
            tie = 0
            ambiguous = demoted = False
            status = "NOT_FOUND"
        rebuilt[staffer["quorum_staff_id"]] = {
            "ambiguous": ambiguous,
            "best_tier": final,
            "demoted_for_tie": demoted,
            "display_name": staffer["display_name"],
            "match_count": len(matches),
            "matches": matches,
            "member_bioguide": staffer["bioguide"],
            "member_display": staffer["member_display"],
            "member_resolution_method": staffer["member_method"],
            "payroll_identity_count": len({m["payroll_identity_key"] for m in matches}),
            "quorum_staff_id": staffer["quorum_staff_id"],
            "status": status,
            "tie_size": tie,
            "tier_before_tie_demotion": pre,
            "title_raw": staffer["title_raw"],
        }
    return {
        "rows": rebuilt,
        "entries": len(entries),
        "members": len(members),
        "members_resolved": sum(1 for b, _m in members.values() if b),
        "office_methods": dict(sorted(office_methods.items())),
        "source_counts": dict(sorted(source_counts.items())),
    }


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
def promotion_failures(rows: Iterable[Mapping[str, Any]], label: str) -> list[str]:
    out: list[str] = []
    for index, row in enumerate(rows):
        if row.get("review_status") != "REVIEW_REQUIRED":
            out.append(f"{label}[{index}] review_status")
        if row.get("canonical_eligible") is not False:
            out.append(f"{label}[{index}] canonical_eligible")
        if row.get("canonical_employment_promoted") is not False:
            out.append(f"{label}[{index}] canonical_employment_promoted")
        if row.get("canonical_identity_decision") != "NOT_ADJUDICATED":
            out.append(f"{label}[{index}] canonical_identity_decision")
        for key, value in row.items():
            lowered = key.lower()
            if ("promoted" in lowered or "canonical" in lowered or "eligible" in lowered) \
                    and value not in UNPROMOTED_ALLOWED:
                out.append(f"{label}[{index}] promotion-shaped {key}")
        if len(out) > 40:
            out.append("... truncated")
            break
    return out


def language_scan(payload: Any) -> tuple[list[str], Counter]:
    authored: list[str] = []
    verbatim: Counter = Counter()

    def walk(node: Any, key: str | None, exempt: bool) -> None:
        if isinstance(node, Mapping):
            for child_key, child in node.items():
                lowered = str(child_key).casefold()
                for token in BANNED_TOKENS:
                    if token in lowered:
                        authored.append(f"field_name:{child_key}:{token}")
                walk(child, str(child_key), exempt or str(child_key) in VERBATIM_LEAF_NAMES)
        elif isinstance(node, list):
            for child in node:
                walk(child, key, exempt)
        elif isinstance(node, str):
            lowered = node.casefold()
            for token in BANNED_TOKENS:
                if token in lowered:
                    (verbatim.__setitem__(f"{key}|{token}", verbatim[f"{key}|{token}"] + 1)
                     if exempt else authored.append(f"value:{key}:{token}"))

    walk(payload, None, False)
    return authored, verbatim


def gzip_mtime(path: Path) -> int | None:
    with Path(path).open("rb") as handle:
        header = handle.read(10)
    if len(header) < 10 or header[:2] != b"\x1f\x8b":
        return None
    return struct.unpack("<I", header[4:8])[0]


def check_determinism(path: Path, sort_key) -> list[str]:
    problems: list[str] = []
    if gzip_mtime(path) != 0:
        problems.append(f"{path.name}: gzip mtime is not 0")
    with gzip.open(path, "rb") as handle:
        raw = handle.read()
    if b"\r\n" in raw:
        problems.append(f"{path.name}: CRLF present")
    previous = None
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        value = json.loads(line)
        if canonical_bytes(value).decode("utf-8") != line:
            problems.append(f"{path.name}: line is not canonical (sorted keys / separators)")
            break
        current = sort_key(value)
        if previous is not None and current < previous:
            problems.append(f"{path.name}: declared sort order violated at {current!r}")
            break
        previous = current
    return problems


def run(generation: Path, output: Path | None) -> dict[str, Any]:
    generation = Path(generation).resolve()
    receipt = json.loads((generation / RECEIPT_FILE).read_text(encoding="utf-8"))
    checks: dict[str, Any] = {}
    failures: list[str] = []

    # ---- V1 input binding ------------------------------------------------
    binding: dict[str, Any] = {}
    paths: dict[str, Path] = {}
    for label, block in sorted(receipt["inputs"].items()):
        if not block.get("present"):
            binding[label] = "ABSENT_IN_RECEIPT"
            continue
        path = REPO_ROOT / block["path"]
        if not path.is_file():
            binding[label] = "MISSING_ON_DISK"
            failures.append(f"V1 {label} missing on disk")
            continue
        digest = sha256_of(path)
        binding[label] = "MATCH" if digest == block["sha256"] else f"SHA_MISMATCH:{digest}"
        if digest != block["sha256"]:
            failures.append(f"V1 {label} sha256 disagrees with the receipt")
        if label == "staff_directory":
            paths["staff_directory"] = path
        elif label == "house_personnel_observations":
            paths["house_personnel_observations"] = path
        elif label == "senate_payroll_candidates":
            paths["senate_payroll_candidates"] = path
        elif label == "nickname_table":
            paths["nickname_table"] = path
        elif label.startswith("roster:"):
            paths["roster_dir"] = path.parent
    checks["V1_input_binding"] = binding
    for required in ("staff_directory", "house_personnel_observations",
                     "senate_payroll_candidates", "nickname_table", "roster_dir"):
        if required not in paths:
            failures.append(f"V1 required input {required} is not bound")
    if failures:
        return finish(generation, output, receipt, checks, failures)

    link_rows = list(ndjson_gz_rows(generation / LINK_FILE))
    candidate_rows = list(ndjson_gz_rows(generation / CANDIDATE_FILE))

    # ---- V2 conservation -------------------------------------------------
    by_id = {row["quorum_staff_id"]: row for row in link_rows}
    conservation = {
        "candidate_rows": len(candidate_rows),
        "candidate_rows_equal_match_sum": len(candidate_rows) == sum(
            row["match_count"] for row in link_rows
        ),
        "distinct_quorum_staff_ids": len(by_id),
        "expected_rows": EXPECTED_CURRENT_STAFFERS,
        "link_rows": len(link_rows),
        "link_rows_equal_expected": len(link_rows) == EXPECTED_CURRENT_STAFFERS,
    }
    if len(link_rows) != EXPECTED_CURRENT_STAFFERS:
        failures.append(f"V2 link rows {len(link_rows)} != {EXPECTED_CURRENT_STAFFERS}")
    if len(by_id) != len(link_rows):
        failures.append("V2 duplicate quorum_staff_id")
    if not conservation["candidate_rows_equal_match_sum"]:
        failures.append("V2 candidate rows do not equal the sum of match_count")
    orphans = {row["quorum_staff_id"] for row in candidate_rows} - set(by_id)
    if orphans:
        failures.append(f"V2 {len(orphans)} candidate rows have no link row")
    checks["V2_conservation"] = conservation

    # ---- V3 full re-derivation -------------------------------------------
    model = rederive(paths)
    compare_fields = (
        "ambiguous", "best_tier", "demoted_for_tie", "display_name", "match_count",
        "member_bioguide", "member_display", "member_resolution_method",
        "payroll_identity_count", "status", "tie_size", "tier_before_tie_demotion",
        "title_raw",
    )
    mismatches: list[str] = []
    match_mismatches: list[str] = []
    for staff_id, expected in model["rows"].items():
        actual = by_id.get(staff_id)
        if actual is None:
            mismatches.append(f"{staff_id}: absent from the generation")
            continue
        for field in compare_fields:
            if actual.get(field) != expected[field]:
                mismatches.append(
                    f"{staff_id}.{field}: generation={actual.get(field)!r} rederived={expected[field]!r}"
                )
        if canonical_bytes(actual.get("matches")) != canonical_bytes(expected["matches"]):
            match_mismatches.append(staff_id)
    extra = set(by_id) - set(model["rows"])
    if extra:
        mismatches.append(f"{len(extra)} generation rows have no re-derived counterpart")
    checks["V3_rederivation"] = {
        "rows_rederived": len(model["rows"]),
        "rows_compared": len(by_id),
        "field_mismatches": len(mismatches),
        "field_mismatch_examples": mismatches[:15],
        "match_list_mismatches": len(match_mismatches),
        "match_list_mismatch_examples": match_mismatches[:15],
        "coverage": round(len(model["rows"]) / len(by_id), 6) if by_id else None,
    }
    if mismatches:
        failures.append(f"V3 {len(mismatches)} field mismatches against the re-derivation")
    if match_mismatches:
        failures.append(f"V3 {len(match_mismatches)} rows whose match list disagrees")

    # ---- V4 tie handling --------------------------------------------------
    tie_problems: list[str] = []
    tie_hist: Counter = Counter()
    for row in link_rows:
        pre = row["tier_before_tie_demotion"]
        supporting = [m for m in row["matches"] if m["tier"] == pre] if pre else []
        recomputed = len({m["payroll_identity_key"] for m in supporting})
        if row["tie_size"] != recomputed:
            tie_problems.append(f"{row['quorum_staff_id']}: tie_size {row['tie_size']} != {recomputed}")
        if row["ambiguous"] != (row["tie_size"] > 1):
            tie_problems.append(f"{row['quorum_staff_id']}: ambiguous disagrees with tie_size")
        if row["status"] in RESOLVED_STATUSES and row["ambiguous"]:
            tie_problems.append(f"{row['quorum_staff_id']}: RESOLVED status on an ambiguous row")
        expected_final = (
            TIE_DEMOTION[pre] if (row["ambiguous"] and pre in TIE_DEMOTION) else pre
        )
        if row["best_tier"] != expected_final:
            tie_problems.append(f"{row['quorum_staff_id']}: demotion target disagrees")
        if row["demoted_for_tie"] != (row["ambiguous"] and pre in TIE_DEMOTION):
            tie_problems.append(f"{row['quorum_staff_id']}: demoted_for_tie disagrees")
        if (row["status"] == "NOT_FOUND") != (row["match_count"] == 0):
            tie_problems.append(f"{row['quorum_staff_id']}: NOT_FOUND disagrees with match_count")
        if pre:
            tie_hist[f"{pre}|{min(row['tie_size'], 6)}"] += 1
    checks["V4_tie_handling"] = {
        "ambiguous_rows": sum(1 for row in link_rows if row["ambiguous"]),
        "demoted_rows": sum(1 for row in link_rows if row["demoted_for_tie"]),
        "max_tie_size": max((row["tie_size"] for row in link_rows), default=0),
        "problems": len(tie_problems),
        "problem_examples": tie_problems[:15],
        "staffers_reaching_more_than_one_payroll_identity": sum(
            1 for row in link_rows if row["payroll_identity_count"] > 1
        ),
        "tie_size_histogram_by_tier_before_demotion": dict(sorted(tie_hist.items())),
    }
    if tie_problems:
        failures.append(f"V4 {len(tie_problems)} tie-handling problems")

    # ---- V5 tripwire, with a negative control -----------------------------
    tripwire = promotion_failures(link_rows, LINK_FILE) + promotion_failures(
        candidate_rows, CANDIDATE_FILE
    )
    control_row = dict(link_rows[0]) if link_rows else {
        "review_status": "REVIEW_REQUIRED", "canonical_eligible": False,
        "canonical_employment_promoted": False, "canonical_identity_decision": "NOT_ADJUDICATED",
    }
    control_row["canonical_employment_promoted"] = True
    negative_control_fired = bool(promotion_failures([control_row], "NEGATIVE_CONTROL"))
    checks["V5_tripwire"] = {
        "canonical_employment_promotions_in_receipt": receipt.get("canonical_employment_promotions"),
        "canonical_identity_promotions_in_receipt": receipt.get("canonical_identity_promotions"),
        "failures": len(tripwire),
        "failure_examples": tripwire[:10],
        "negative_control_rejects_a_promoted_row": negative_control_fired,
    }
    if tripwire:
        failures.append(f"V5 {len(tripwire)} rows are not in the unpromoted state")
    if not negative_control_fired:
        failures.append("V5 negative control did NOT fire -- the tripwire cannot fail")
    if receipt.get("canonical_employment_promotions") != 0:
        failures.append("V5 receipt does not pin canonical_employment_promotions at 0")
    if receipt.get("canonical_identity_promotions") != 0:
        failures.append("V5 receipt does not pin canonical_identity_promotions at 0")

    # ---- V6 language law ---------------------------------------------------
    authored: list[str] = []
    verbatim: Counter = Counter()
    for rows in (link_rows, candidate_rows):
        hits, occurrences = language_scan(rows)
        authored.extend(hits)
        verbatim += occurrences
    receipt_verbatim = receipt["language_law"]["verbatim_token_occurrences"]
    verbatim_agrees = dict(verbatim) == {k: v for k, v in receipt_verbatim.items()}
    checks["V6_language_law"] = {
        "authored_hits": len(authored),
        "authored_examples": sorted(set(authored))[:10],
        "verbatim_agrees_with_receipt": verbatim_agrees,
        "verbatim_token_occurrences": dict(sorted(verbatim.items())),
    }
    if authored:
        failures.append(f"V6 {len(authored)} authored banned-token hits")
    if not verbatim_agrees:
        failures.append("V6 verbatim occurrence counts disagree with the receipt")

    # ---- V7 determinism ----------------------------------------------------
    determinism = check_determinism(
        generation / LINK_FILE,
        lambda row: (row["member_display"], row["display_name"], row["quorum_staff_id"]),
    ) + check_determinism(
        generation / CANDIDATE_FILE,
        lambda row: (
            row["quorum_staff_id"], row["chamber"], row["office_key"],
            row["payroll_last"], row["payroll_first"], row["payroll_middle_initial"] or "",
        ),
    )
    checks["V7_determinism"] = {"problems": determinism}
    if determinism:
        failures.append(f"V7 {len(determinism)} determinism problems")

    # ---- V8 receipt agreement ----------------------------------------------
    status_counts = Counter(row["status"] for row in link_rows)
    resolved = sum(status_counts[s] for s in RESOLVED_STATUSES)
    pre_counts = Counter(
        row["tier_before_tie_demotion"] for row in link_rows if row["tier_before_tie_demotion"]
    )
    agreement = {
        "class_matches": Counter(
            m["match_class"] for row in link_rows for m in row["matches"]
        ),
        "member_office_resolution_methods": model["office_methods"],
        "members_resolved_to_a_bioguide": model["members_resolved"],
        "resolved_staffers_whose_name_reaches_more_than_one_payroll_identity": sum(
            1 for row in link_rows
            if row["status"] in RESOLVED_STATUSES and row["payroll_identity_count"] > 1
        ),
        "resolved_total": resolved,
        "source_rows": model["source_counts"],
        "staffers_ambiguous_at_best_tier": sum(1 for row in link_rows if row["ambiguous"]),
        "staffers_with_a_surname_match_but_no_first_name_match": sum(
            1 for row in link_rows
            if row["matches"] and all(
                m["match_class"] in (CLASS_INITIAL_ONLY, CLASS_INITIAL_SHARED)
                for m in row["matches"]
            )
        ),
        "surname_only_matches_by_status": dict(sorted(Counter(
            row["status"] for row in link_rows
            if row["matches"] and all(
                m["match_class"] in (CLASS_INITIAL_ONLY, CLASS_INITIAL_SHARED)
                for m in row["matches"]
            )
        ).items())),
        "staffers_whose_name_reaches_more_than_one_payroll_identity": sum(
            1 for row in link_rows if row["payroll_identity_count"] > 1
        ),
        "status": dict(sorted(status_counts.items())),
        "tier_before_tie_demotion": dict(sorted(pre_counts.items())),
    }
    agreement["class_matches"] = dict(sorted(agreement["class_matches"].items()))
    published = receipt["counts"]
    disagreements = []
    for field, value in agreement.items():
        if published.get(field) != value:
            disagreements.append(field)
    checks["V8_receipt_agreement"] = {
        "disagreements": disagreements,
        "recomputed": agreement,
    }
    if disagreements:
        failures.append(f"V8 receipt disagrees on {disagreements}")

    files = {}
    for name in (LINK_FILE, CANDIDATE_FILE, RECEIPT_FILE):
        path = generation / name
        files[name] = {"bytes": path.stat().st_size, "sha256": sha256_of(path)}
    checks["files"] = files
    return finish(generation, output, receipt, checks, failures)


def finish(
    generation: Path, output: Path | None, receipt: Mapping[str, Any],
    checks: Mapping[str, Any], failures: Sequence[str],
) -> dict[str, Any]:
    verification = {
        "checks": checks,
        "failures": list(failures),
        "generation": str(generation),
        "generation_receipt_sha256": hashlib.sha256(
            canonical_bytes(receipt)
        ).hexdigest(),
        "independent_of_builder": True,
        "schema_id": VERIFICATION_SCHEMA,
        "status": "PASS" if not failures else "FAIL",
        "verifier_sha256": sha256_of(Path(__file__)),
    }
    if output is not None:
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        target = output / VERIFICATION_FILE
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(canonical_bytes(verification) + b"\n")
        os.replace(temporary, target)
    return verification


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify a current-staffer-links generation.")
    parser.add_argument("--generation", required=True, type=Path)
    parser.add_argument("--output-root", type=Path, default=None)
    args = parser.parse_args(argv)
    verification = run(args.generation, args.output_root)
    print(json.dumps(
        {
            "status": verification["status"],
            "failures": verification["failures"],
            "V2": verification["checks"].get("V2_conservation"),
            "V3": {
                k: v for k, v in (verification["checks"].get("V3_rederivation") or {}).items()
                if not k.endswith("examples")
            },
            "V4": {
                k: v for k, v in (verification["checks"].get("V4_tie_handling") or {}).items()
                if k not in ("problem_examples", "tie_size_histogram_by_tier_before_demotion")
            },
            "V5": verification["checks"].get("V5_tripwire"),
            "V6": {
                k: v for k, v in (verification["checks"].get("V6_language_law") or {}).items()
                if k != "verbatim_token_occurrences"
            },
            "V7": verification["checks"].get("V7_determinism"),
            "V8": {"disagreements": (verification["checks"].get("V8_receipt_agreement") or {}).get("disagreements")},
        },
        indent=1, sort_keys=True,
    ))
    return 0 if verification["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
