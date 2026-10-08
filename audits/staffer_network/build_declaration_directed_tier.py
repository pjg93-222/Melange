#!/usr/bin/env python3
r"""Build the D1 declaration-directed employment tier as an immutable generation.

What this builds, and only this
-------------------------------
PHASE Adjudicate (``ADJUDICATION.md``, rule version
``declaration-directed-matching-adjudication-v1``) recommended a narrow build:
D1 as a distinct higher-evidence employment tier, D3 as a candidate tier only,
D2 and D3M as candidates that are never resolved, and D4a/FIRST_INITIAL as
nothing at all.  This builder emits exactly that, and encodes the refusals
explicitly rather than by omission:

* ``declaration_directed_employment_links.ndjson.gz`` -- the D1 tier.
* ``declaration_directed_candidates.ndjson.gz`` -- D3 (with the 38
  ``D3_STRENGTHENED`` rows marked), D2 and D3M with their tie size and no
  resolved payroll person, plus any D1 row a defect guard demoted.
* ``declaration_directed_non_evidential.ndjson.gz`` -- the 31 targets whose
  only hit is FIRST_INITIAL, labelled ``NON_EVIDENTIAL_HIT_ONLY``.  The paired
  control measured this class at 6.98 percent false-positive (95 percent upper
  bound 20.38 percent); that number is carried into the receipt next to the
  exclusion so the refusal is self-documenting.

Nothing here is promoted.  Every emitted row carries ``canonical_eligible:
false``, ``canonical_employment_promoted: false``, ``canonical_identity_
decision: "NOT_ADJUDICATED"`` and ``review_status: "REVIEW_REQUIRED"``, and the
receipt pins both promotion counters to 0.  A tier is a label with a measured
error rate attached, not an identity finding.

The three defects PHASE Adjudicate escalated
--------------------------------------------
They are handled here, not inherited.  Each guard is measured and reported
whether or not it fires; a guard that fires zero times is a measurement, not a
missing feature.

1. ``CROSS_CLAUSE_ATTACHMENT``.  PHASE Target matched committee aliases as
   substrings of the WHOLE declared value rather than span-anchored, so a value
   listing several employers could attach an office belonging to a different
   clause.  This builder re-anchors the attachment: for the winning office key
   it takes the declared-office mention that produced the key, locates that
   mention's anchor (the member name for a MEMBER mention, the matched
   committee alias for a COMMITTEE mention) inside the filer's own
   covered-position text, cuts the text into clauses, and requires at least one
   clause that contains the anchor to also contain a legislative cue.  A D1 row
   with no such clause -- including one whose anchor cannot be located at all,
   which is the fail-closed reading -- is demoted to a candidate.

2. ``DECLARATION_IS_A_DISCLAIMER``.  Some covered-position values are
   disclaimers ("*No lobby activity or contact made to US Senator John
   Cornyn's Offic") that were parsed as positions.  A clause whose leading
   token is a negation and which then names the office anchor is a disclaimer
   clause.  A D1 row is demoted only when EVERY clause supporting its
   attachment is a disclaimer clause: a filer who prefixes a real declaration
   with a lobbying disclaimer still declared the position, and demoting that
   would destroy evidence rather than protect it.

3. Middle-initial conflicts.  The Senate searcher strips inlined go-by names
   ("ms KATHERINE KATIE MEYER" -> middle "K") before comparing middle initials;
   the House-member searcher does not, which manufactures conflicts.  This
   builder re-runs the Senate searcher's ``is_embedded_alias`` rule over every
   scope's target display name and re-derives the middle initial, so the
   artifact disappears.  A surviving conflict is reported as a field, never as
   a demotion: the class is a data-quality signal, not evidence against a
   match.

Read-only on every input.  Never imports a ``fec`` module other than
``fec/staffer_network/intervals.py`` and
``fec/staffer_network/schema_validation.py``.  Runs no git command.  Refuses a
non-empty output directory, stages into a sibling temporary directory and
renames it into place, and writes canonical NDJSON (sorted keys, gzip mtime 0)
so a twin run is byte-identical.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from typing import Any, Iterable, Iterator, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from fec.staffer_network.intervals import UncertainInterval  # noqa: E402
from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
)

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

ROW_SCHEMA_ID = "staffer-network-declaration-directed-employment-link-v1"
RECEIPT_SCHEMA_ID = "staffer-network-declaration-directed-tier-receipt-v1"
RULE_VERSION = "declaration-directed-employment-tier-v1"
METHOD_VERSION = "declaration-directed-employment-tier-v1"
PHASE = "build-declaration-directed-tier"
PROMOTION_POLICY = "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
REVIEW_STATUS = "REVIEW_REQUIRED"
GLASSBOX_SOURCE = "declaration-directed-d1"
EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"

LINKS_FILENAME = "declaration_directed_employment_links.ndjson.gz"
CANDIDATES_FILENAME = "declaration_directed_candidates.ndjson.gz"
NON_EVIDENTIAL_FILENAME = "declaration_directed_non_evidential.ndjson.gz"
RECEIPT_FILENAME = "declaration_directed_tier_receipt.json"

ROW_SCHEMA_FILENAME = "declaration_directed_employment_link.schema.json"

# The adjudication this build is directed by.  Pinned by content, not by path.
ADJUDICATION_SHA256 = (
    "b6f122658d1e5928beff1602d69473ff9407ea664caf1326fb0f07cb7e65dde2"
)
ADJUDICATION_ROWS = 3555
ADJUDICATION_RULE_VERSION = "declaration-directed-matching-adjudication-v1"

# Counts the adjudication published.  Reproduced, never assumed: a mismatch is
# a build failure, so the tier can never silently drift off its own basis.
EXPECTED_STATUS_COUNTS = {
    "D1_DECLARED_OFFICE_EXACT_UNIQUE": 736,
    "D2_DECLARED_OFFICE_EXACT_MULTI": 9,
    "D3_DECLARED_OFFICE_LOOSE": 183,
    "D3M_DECLARED_OFFICE_LOOSE_MULTI": 2,
    "D4_NO_HIT": 1375,
    "D5_OFFICE_UNRESOLVABLE": 1250,
}
EXPECTED_D1_BY_CLASS = {"EXACT_TRIPLE": 355, "EXACT_PAIR": 381}
EXPECTED_D1_BY_SCOPE = {"house_member": 439, "senate": 176, "house_nonmember": 121}
EXPECTED_D1_BY_YEAR = {
    "D1_YEAR_CORROBORATED": 212,
    "D1_YEAR_UNTESTABLE": 521,
    "D1_YEAR_CONTRADICTED": 3,
}
EXPECTED_D3_STRENGTHENED = 38
EXPECTED_D4A = 31

INPUT_FILES: tuple[tuple[str, str], ...] = (
    ("adjudication", "adjudication.ndjson.gz"),
    ("adjudication_report", "adjudication_report.json"),
    ("targets", "targets.ndjson.gz"),
    ("hits_house_member", "hits_house_member.ndjson.gz"),
    ("hits_house_nonmember", "hits_house_nonmember.ndjson.gz"),
    ("hits_senate_all", "hits_senate_all.ndjson.gz"),
    ("control_report", "control_report.json"),
    ("adj_control_d1", "adj_control_d1.json"),
)

SCOPE_PUBLIC = {
    "house_member": "house_member",
    "house_nonmember": "house_nonmember",
    "senate_all": "senate",
}

STATUS_TO_TIER = {
    "D1_DECLARED_OFFICE_EXACT_UNIQUE": "D1_DECLARED_OFFICE_EXACT_UNIQUE",
    "D2_DECLARED_OFFICE_EXACT_MULTI": "D2_CANDIDATE",
    "D3_DECLARED_OFFICE_LOOSE": "D3_CANDIDATE",
    "D3M_DECLARED_OFFICE_LOOSE_MULTI": "D3M_CANDIDATE",
}
TIER_FAMILY = {
    "D1_DECLARED_OFFICE_EXACT_UNIQUE": "LINK",
    "D1_DEMOTED_CANDIDATE": "CANDIDATE",
    "D2_CANDIDATE": "CANDIDATE",
    "D3_CANDIDATE": "CANDIDATE",
    "D3M_CANDIDATE": "CANDIDATE",
    "NON_EVIDENTIAL_HIT_ONLY": "NON_EVIDENTIAL",
}

QUARTER_START = {"Q1": (1, 1), "Q2": (4, 1), "Q3": (7, 1), "Q4": (10, 1)}
QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}

# ---------------------------------------------------------------------------
# guard vocabularies
# ---------------------------------------------------------------------------

# Tokens dropped on both sides before an anchor is located, so that
# "Science, Space & Technology" and the alias "SCIENCE SPACE AND TECHNOLOGY"
# are the same string.  Without this the ampersand form fails to locate and a
# real match would be demoted for a punctuation difference.
CLAUSE_STOPWORDS = frozenset({"AND", "THE", "OF"})

# A clause carries a legislative cue when it names a chamber, a member title, a
# committee, or a leadership post.  The cue test is what separates the clause
# that really names the declared office from a neighbouring clause that names
# an executive-branch employer.
LEGISLATIVE_CUE = re.compile(
    r"\b(REP|REPS|REPRESENTATIVE|REPRESENTATIVES|CONGRESSMAN|CONGRESSWOMAN|"
    r"CONGRESSMEMBER|CONGRESSMEN|CONGRESSWOMEN|CONG|CONGR|SEN|SENS|SENATOR|"
    r"SENATORS|SENATE|HOUSE|CONGRESS|CONGRESSIONAL|COMMITTEE|COMMITTEES|"
    r"SUBCOMMITTEE|SUBCOMMITTEES|CMTE|CAUCUS|CAPITOL|HILL|SPEAKER|WHIP|"
    r"DELEGATE|LEADERSHIP|CLOAKROOM|PARLIAMENTARIAN|MAJORITY|MINORITY|"
    r"LEADER|CHAIRMAN|CHAIRWOMAN|RANKING|MEMBER)\b"
)

# A disclaimer clause opens with a negation and then names the office.
DISCLAIMER_LEADING_NEGATION = re.compile(r"^(NO|NOT|NONE|NEVER)\b")

# Clause boundaries.  Semicolons, newlines and square brackets are how these
# filers separate employers; a slash is deliberately NOT a boundary because it
# far more often joins two titles held in one office ("Legislative
# Correspondent/Staff Assistant") than it separates employers.  The slash
# variant is measured as a sensitivity and reported, never applied.
CLAUSE_SPLIT = re.compile(r"[;\n\[\]]")
CLAUSE_SPLIT_AGGRESSIVE = re.compile(r"[;\n\[\]/|]")

NON_ALNUM = re.compile(r"[^A-Z0-9]+")

# Senate searcher name vocabulary, reused verbatim so the House-member path
# gets the same alias stripping.
NAME_HONORIFICS = frozenset({
    "MR", "MRS", "MS", "MISS", "DR", "PROF", "HON", "HONORABLE", "REP",
    "REPRESENTATIVE", "SEN", "SENATOR", "THE", "SIR", "RT", "REV", "CAPT",
    "COL", "GEN", "MAJ", "LT", "SGT", "ADM", "AMB",
})
NAME_SUFFIXES = frozenset({
    "JR", "SR", "II", "III", "IV", "V", "VI", "ESQ", "PHD", "MD", "JD",
    "DDS", "DVM", "MBA", "CPA", "RET", "USA", "USN", "USAF", "USMC",
})


class BuildError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# deterministic io helpers (local: fec.source_manifest is not importable here)
# ---------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise BuildError(f"object row required at {path}:{number}")
            yield value


def write_ndjson(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    """Canonical NDJSON: sorted keys, no spaces, gzip mtime 0, LF endings."""
    with path.open("wb") as raw:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0
        ) as stream:
            for row in rows:
                stream.write(
                    json.dumps(
                        row, ensure_ascii=False, sort_keys=True,
                        separators=(",", ":"), allow_nan=False,
                    ).encode("utf-8")
                )
                stream.write(b"\n")


def prepare_output(output: Path) -> Path:
    if output.exists():
        if not output.is_dir():
            raise BuildError(f"output root exists and is not a directory: {output}")
        if any(output.iterdir()):
            raise BuildError(f"immutable generation already exists: {output}")
        output.rmdir()
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))


def emit_glassbox(
    *, enabled: bool, kind: str, status: str, summary: str, detail: str,
    run_id: str, stage: str,
) -> None:
    if not enabled or not EMIT_PS1.is_file():
        return
    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
        str(EMIT_PS1), "-Lane", "claude", "-Kind", kind, "-Status", status,
        "-Summary", summary, "-Detail", detail, "-RunId", run_id,
        "-Stage", stage, "-Source", GLASSBOX_SOURCE, "-Quiet",
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        # Observability must never take the build down.
        return


# ---------------------------------------------------------------------------
# clause machinery -- the span anchoring PHASE Target did not do
# ---------------------------------------------------------------------------


def clause_tokens(text: str | None) -> list[str]:
    upper = (text or "").upper().replace("&", " AND ")
    return [t for t in NON_ALNUM.sub(" ", upper).split() if t not in CLAUSE_STOPWORDS]


def split_clauses(value: str | None, aggressive: bool = False) -> list[str]:
    pattern = CLAUSE_SPLIT_AGGRESSIVE if aggressive else CLAUSE_SPLIT
    return [part for part in pattern.split(value or "") if part.strip()]


def contains_contiguous(anchor: Sequence[str], clause: Sequence[str]) -> bool:
    size = len(anchor)
    if not size or size > len(clause):
        return False
    anchor_list = list(anchor)
    return any(
        list(clause[index:index + size]) == anchor_list
        for index in range(len(clause) - size + 1)
    )


def contains_ordered_subsequence(
    anchor: Sequence[str], clause: Sequence[str]
) -> bool:
    """Fallback location test.

    A MEMBER mention's text can bleed past the name ("Billy Long Senior
    Legislative"), and a filer can wedge a party-state marker into the middle
    of it ("Rep. Shelley Moore Capito (R-WV) Jan. 2006"), so the contiguous
    test misses a clause that plainly does name the member.  Requiring the
    anchor's tokens in order inside one clause recovers those without letting
    an anchor match a clause that never mentions it.
    """
    if not anchor:
        return False
    cursor = iter(clause)
    return all(any(token == want for token in cursor) for want in anchor)


def declared_anchors(
    target: Mapping[str, Any], office_key: str
) -> list[tuple[str, str]]:
    """(mention kind, anchor text) pairs that attached this office key.

    For a COMMITTEE mention the anchor is the matched alias, not the mention
    text: PHASE Target stored the WHOLE covered-position value as a committee
    mention's text, which is exactly the unanchored behaviour being repaired.
    """
    anchors: list[tuple[str, str]] = []
    for mention in target.get("declared_office_mentions") or []:
        if office_key not in (mention.get("office_keys") or []):
            continue
        kind = mention.get("kind") or "UNKNOWN"
        if kind == "COMMITTEE" and mention.get("alias_hit"):
            anchors.append((kind, str(mention["alias_hit"])))
        elif mention.get("text"):
            anchors.append((kind, str(mention["text"])))
    return anchors


def attachment_evidence(
    target: Mapping[str, Any], office_key: str, aggressive: bool = False
) -> dict[str, Any]:
    """Locate every clause that supports this office attachment and grade it."""
    anchors = declared_anchors(target, office_key)
    values = list(target.get("covered_position_values") or [])
    supporting: list[dict[str, Any]] = []
    basis_rank = {"CONTIGUOUS": 0, "ORDERED_SUBSEQUENCE": 1}
    for kind, anchor in anchors:
        anchor_tokens = clause_tokens(anchor)
        if not anchor_tokens:
            continue
        for value in values:
            for clause in split_clauses(value, aggressive=aggressive):
                tokens = clause_tokens(clause)
                if contains_contiguous(anchor_tokens, tokens):
                    basis = "CONTIGUOUS"
                elif contains_ordered_subsequence(anchor_tokens, tokens):
                    basis = "ORDERED_SUBSEQUENCE"
                else:
                    continue
                joined = " ".join(tokens)
                supporting.append({
                    "mention_kind": kind,
                    "anchor": anchor,
                    "clause": clause.strip(),
                    "basis": basis,
                    "legislative_cue": bool(LEGISLATIVE_CUE.search(joined)),
                    "leading_negation": bool(
                        DISCLAIMER_LEADING_NEGATION.match(joined)
                    ),
                })
    if not supporting:
        cross_clause = "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE"
        best_basis = "NONE"
        disclaimer = "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT"
    else:
        with_cue = [s for s in supporting if s["legislative_cue"]]
        if with_cue:
            cross_clause = "CLAUSE_CARRIES_LEGISLATIVE_CUE"
            best_basis = min(
                (s["basis"] for s in with_cue), key=lambda b: basis_rank[b]
            )
        else:
            cross_clause = "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
            best_basis = min(
                (s["basis"] for s in supporting), key=lambda b: basis_rank[b]
            )
        negations = sum(1 for s in supporting if s["leading_negation"])
        if negations == 0:
            disclaimer = "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT"
        elif negations == len(supporting):
            disclaimer = "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"
        else:
            disclaimer = "SOME_SUPPORTING_CLAUSES_ARE_DISCLAIMERS"
    return {
        "anchors": anchors,
        "supporting": supporting,
        "cross_clause_status": cross_clause,
        "cross_clause_basis": best_basis,
        "disclaimer_status": disclaimer,
    }


def declaration_has_disclaimer_clause(target: Mapping[str, Any]) -> bool:
    """Any clause anywhere in this filer's declaration that negates an office."""
    for value in target.get("covered_position_values") or []:
        for clause in split_clauses(value):
            joined = " ".join(clause_tokens(clause))
            if DISCLAIMER_LEADING_NEGATION.match(joined) and LEGISLATIVE_CUE.search(
                joined
            ):
                return True
    return False


def year_tokens_only_in_disclaimer_clauses(target: Mapping[str, Any]) -> bool:
    """True when every declared year token sits inside a disclaimer clause.

    ``mr HOLTEN STRINGER``'s only year token, 2023, comes from
    "*No lobby activity ... thru 1/3/2023" and made the row
    ``D1_YEAR_CONTRADICTED``.  This is a caveat field, not a re-grade: the
    adjudication owns the year strengthener and this build does not overrule
    it, it flags it.
    """
    declared = {
        str(token) for token in (target.get("covered_position_year_tokens") or [])
    }
    if not declared:
        return False
    outside: set[str] = set()
    inside: set[str] = set()
    for value in target.get("covered_position_values") or []:
        for clause in split_clauses(value):
            joined = " ".join(clause_tokens(clause))
            found = {t for t in declared if re.search(r"\b%s\b" % re.escape(t), joined)}
            if DISCLAIMER_LEADING_NEGATION.match(joined):
                inside |= found
            else:
                outside |= found
    return bool(inside) and not (declared - inside) and not (outside & inside)


# ---------------------------------------------------------------------------
# the Senate searcher's alias stripping, applied to every scope
# ---------------------------------------------------------------------------


class NameAliasRule:
    """``is_embedded_alias`` from ``search_senate_all.py``, verbatim in effect.

    An LDA display name inlines the go-by name -- "KATHERINE KATIE MEYER",
    "ELIZABETH (LIZ) BANICKI", "JOHN J.P. DOWD".  Such a token is not a middle
    name, and treating it as one manufactures a middle-initial conflict.
    """

    def __init__(self, nickname_entries: Mapping[str, Sequence[str]]):
        self.short_to_formal = {
            key.upper(): str(value[0]).upper()
            for key, value in nickname_entries.items()
            if len(value) == 1
        }
        # Reported as a sensitivity only; never used by the applied rule.
        self.all_expansions = {
            key.upper(): {str(v).upper() for v in value}
            for key, value in nickname_entries.items()
        }

    def canon_given(self, given: str) -> str:
        return self.short_to_formal.get(given, given)

    def is_embedded_alias(self, given: str, token: str) -> bool:
        if not given or not token or token == given:
            return False
        if self.canon_given(token) == self.canon_given(given):
            return True
        if len(token) >= 3 and (given.startswith(token) or token.startswith(given)):
            return True
        if len(token) == 1 and token == given[0]:
            return True
        return False

    def is_embedded_alias_full_table(self, given: str, token: str) -> bool:
        """Sensitivity variant: consult multi-expansion nickname entries too."""
        if self.is_embedded_alias(given, token):
            return True
        if given in self.all_expansions.get(token, set()):
            return True
        if token in self.all_expansions.get(given, set()):
            return True
        return False


def display_name_tokens(display_name: str | None) -> list[str]:
    cleaned = re.sub(r"[^A-Z' -]", " ", (display_name or "").upper())
    tokens = [t for t in cleaned.split() if t and t != "-"]
    while tokens and tokens[-1] in NAME_SUFFIXES:
        tokens.pop()
    while len(tokens) > 2 and tokens[0] in NAME_HONORIFICS:
        tokens = tokens[1:]
    return tokens


def middle_initial_repair(
    display_name: str | None, rule: NameAliasRule
) -> dict[str, Any]:
    tokens = display_name_tokens(display_name)
    if len(tokens) < 2:
        return {
            "raw": None, "repaired": None, "stripped": [], "middles": [],
            "repaired_full_table": None,
        }
    given = tokens[0]
    middles = tokens[1:-1]
    stripped = [m for m in middles if rule.is_embedded_alias(given, m)]
    retained = [m for m in middles if m not in stripped]
    stripped_full = [
        m for m in middles if rule.is_embedded_alias_full_table(given, m)
    ]
    retained_full = [m for m in middles if m not in stripped_full]
    return {
        "raw": middles[0][0] if middles else "",
        "repaired": retained[0][0] if retained else "",
        "repaired_full_table": retained_full[0][0] if retained_full else "",
        "stripped": stripped,
        "middles": middles,
    }


# ---------------------------------------------------------------------------
# hit-row normalisation
# ---------------------------------------------------------------------------


def quarter_bounds(quarter: str, end: bool) -> str | None:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", quarter or "")
    if not match:
        return None
    year = int(match.group(1))
    month, day = (QUARTER_END if end else QUARTER_START)[match.group(2)]
    return date(year, month, day).isoformat()


def payroll_periods_for(hit: Mapping[str, Any], scope: str) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    if scope == "house_member":
        start = hit.get("payroll_service_start_min")
        end = hit.get("payroll_service_end_max")
        if start and end:
            periods.append(
                {"start": start, "end": end, "basis": "HOUSE_SOD_SERVICE_SPAN"}
            )
        else:
            quarters = sorted(hit.get("payroll_quarters") or [])
            if quarters:
                periods.append({
                    "start": quarter_bounds(quarters[0], end=False),
                    "end": quarter_bounds(quarters[-1], end=True),
                    "basis": "HOUSE_SOD_QUARTER_ENVELOPE",
                })
    elif scope == "house_nonmember":
        for span in hit.get("payroll_spans") or []:
            start = span.get("service_start_min")
            end = span.get("service_end_max")
            if start and end:
                periods.append(
                    {"start": start, "end": end, "basis": "HOUSE_SOD_SERVICE_SPAN"}
                )
        if not periods:
            quarters = sorted(hit.get("payroll_quarters") or [])
            if quarters:
                periods.append({
                    "start": quarter_bounds(quarters[0], end=False),
                    "end": quarter_bounds(quarters[-1], end=True),
                    "basis": "HOUSE_SOD_QUARTER_ENVELOPE",
                })
    else:
        for period in hit.get("payroll_periods") or []:
            if period.get("start") and period.get("end"):
                periods.append({
                    "start": period["start"], "end": period["end"],
                    "basis": "SENATE_REPORT_PERIOD",
                })
    unique = {(p["start"], p["end"], p["basis"]): p for p in periods}
    return [unique[key] for key in sorted(unique)]


def check_periods(periods: Sequence[Mapping[str, Any]]) -> list[str]:
    """Sanity-check each emitted period with the lane's reviewed interval type."""
    flags: list[str] = []
    for period in periods:
        try:
            start = date.fromisoformat(period["start"])
            end = date.fromisoformat(period["end"])
        except (TypeError, ValueError):
            flags.append("UNPARSEABLE_PERIOD_BOUND")
            continue
        interval = UncertainInterval(
            start_earliest=start, start_latest=start,
            end_earliest=end, end_latest=end,
            start_precision="day", end_precision="day",
        )
        try:
            interval.validate()
        except ValueError:
            flags.append("PERIOD_BOUNDS_OUT_OF_ORDER")
    return sorted(set(flags))


def payroll_middle_initial(hit: Mapping[str, Any], scope: str) -> str:
    if scope == "senate_all":
        parts = str(hit.get("payroll_person_key") or "").split("|")
        return parts[-1] if len(parts) >= 5 else ""
    value = hit.get("payroll_middle_initial")
    if value:
        return str(value)
    detail = hit.get("match_detail") or {}
    return str(detail.get("payroll_middle_initial") or "")


def hit_middle_initial_conflict(hit: Mapping[str, Any], scope: str) -> bool:
    if scope == "house_member":
        return bool(hit.get("middle_initial_conflict"))
    detail = hit.get("match_detail") or {}
    return detail.get("middle_initial_status") == "CONFLICT"


def office_container_kind(hit: Mapping[str, Any], scope: str) -> str | None:
    if scope == "house_member":
        kinds = hit.get("office_container_kinds") or []
        return str(kinds[0]) if kinds else None
    if scope == "house_nonmember":
        value = hit.get("office_container_kind")
        return str(value) if value else None
    value = hit.get("office_container_kind_derived")
    return str(value) if value else None


def office_member_bioguide(hit: Mapping[str, Any], scope: str) -> str | None:
    if scope == "house_member":
        value = hit.get("office_member_bioguide")
    else:
        value = hit.get("payroll_member_bioguide")
    return str(value) if value else None


def hit_tie_at_class(hit: Mapping[str, Any], scope: str) -> int | None:
    if scope == "house_member":
        return hit.get("in_office_tie_size_at_row_class")
    if scope == "house_nonmember":
        return hit.get("in_office_tie_size_at_class")
    return hit.get("in_office_tie_size")


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def load_inputs(declaim_root: Path) -> dict[str, Any]:
    manifest: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    for name, filename in INPUT_FILES:
        path = declaim_root / filename
        if not path.is_file():
            raise BuildError(f"required input missing: {path}")
        digest = sha256_file(path)
        record = {
            "name": name,
            "path": str(path),
            "sha256": digest,
            "bytes": path.stat().st_size,
        }
        if filename.endswith(".ndjson.gz"):
            rows = list(read_rows(path))
            record["records"] = len(rows)
            payload[name] = rows
        else:
            record["records"] = None
            payload[name] = json.loads(path.read_text(encoding="utf-8"))
        manifest.append(record)
    payload["_manifest"] = manifest
    return payload


def build_rows(
    payload: Mapping[str, Any], rule: NameAliasRule, run_id: str, generation_id: str
) -> dict[str, Any]:
    adjudication = payload["adjudication"]
    targets = {row["lda_source_person_id"]: row for row in payload["targets"]}
    control = payload["control_report"]["by_match_class"]

    hits_by_person: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, scope in (
        ("hits_house_member", "house_member"),
        ("hits_house_nonmember", "house_nonmember"),
        ("hits_senate_all", "senate_all"),
    ):
        for row in payload[key]:
            enriched = dict(row)
            enriched["_scope"] = scope
            hits_by_person[row["lda_source_person_id"]].append(enriched)

    status_counts = Counter(row["adjudicated_status"] for row in adjudication)
    if dict(status_counts) != EXPECTED_STATUS_COUNTS:
        raise BuildError(
            "adjudication status counts do not reproduce: "
            f"{dict(status_counts)!r} != {EXPECTED_STATUS_COUNTS!r}"
        )

    links: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    non_evidential: list[dict[str, Any]] = []
    diagnostics: dict[str, Any] = {
        "d1_before_guards": 0,
        "demoted_cross_clause_attachment": 0,
        "demoted_declaration_is_a_disclaimer": 0,
        "cross_clause_status_counts": Counter(),
        "cross_clause_basis_counts": Counter(),
        "cross_clause_status_counts_aggressive_split": Counter(),
        "disclaimer_status_counts": Counter(),
        "d1_declaration_contains_disclaimer_clause": 0,
        "d1_year_strengthener_disclaimer_caveat": 0,
        "middle_initial_conflicts_original": Counter(),
        "middle_initial_conflicts_after_alias_strip": Counter(),
        "middle_initial_conflicts_full_nickname_table": Counter(),
        "middle_initial_survivors": [],
        "middle_initial_cleared": [],
        "winner_hit_multiplicity": Counter(),
        "period_review_flags": Counter(),
        "demotions": [],
    }

    for adjudicated in sorted(adjudication, key=lambda r: r["lda_source_person_id"]):
        status = adjudicated["adjudicated_status"]
        substatus = adjudicated["adjudicated_substatus"]
        person_id = adjudicated["lda_source_person_id"]
        is_d4a = status == "D4_NO_HIT" and substatus == "D4a_NON_EVIDENTIAL_HIT_ONLY"
        if status not in STATUS_TO_TIER and not is_d4a:
            continue

        target = targets.get(person_id)
        if target is None:
            raise BuildError(f"adjudicated person absent from targets: {person_id}")

        source_scope = adjudicated["winning_scope"]
        office_key = adjudicated["winning_office_key"]
        match_class = adjudicated["winning_match_class"]
        payroll_key = adjudicated["winning_payroll_person_key"]
        if not (source_scope and office_key and match_class and payroll_key):
            raise BuildError(f"hit row without a winner: {person_id} {status}")

        matches = [
            hit for hit in hits_by_person.get(person_id, [])
            if hit["_scope"] == source_scope
            and hit["office_key"] == office_key
            and hit["payroll_person_key"] == payroll_key
            and hit["match_class"] == match_class
        ]
        if not matches:
            raise BuildError(f"winner hit not found for {person_id}")
        diagnostics["winner_hit_multiplicity"][len(matches)] += 1
        matches.sort(key=lambda h: canonical_json_bytes(
            {k: v for k, v in h.items() if not k.startswith("_")}
        ))
        winner = matches[0]

        # The contending set inside the winning office, at ANY match class.
        # Collecting only the winning class would understate the contention: a
        # D2 row whose tie size is 2 can have its second contender matched at a
        # different class, and printing one key next to "tie size 2" invites a
        # reader to treat that key as the answer, which is exactly what "never
        # resolved" exists to prevent.
        tied = sorted({
            hit["payroll_person_key"] for hit in hits_by_person.get(person_id, [])
            if hit["_scope"] == source_scope
            and hit["office_key"] == office_key
        })

        evidence = attachment_evidence(target, office_key)
        aggressive = attachment_evidence(target, office_key, aggressive=True)
        mi = middle_initial_repair(adjudicated["display_name"], rule)
        payroll_mi = payroll_middle_initial(winner, source_scope)
        conflict_original = hit_middle_initial_conflict(winner, source_scope)
        conflict_repaired = bool(
            mi["repaired"] and payroll_mi and mi["repaired"] != payroll_mi
        )
        conflict_full_table = bool(
            mi["repaired_full_table"]
            and payroll_mi
            and mi["repaired_full_table"] != payroll_mi
        )

        periods = payroll_periods_for(winner, source_scope)
        for flag in check_periods(periods):
            diagnostics["period_review_flags"][flag] += 1

        # ---- tier assignment, with the two demotion guards ----------------
        demotion_reason: str | None = None
        if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE":
            diagnostics["d1_before_guards"] += 1
            diagnostics["cross_clause_status_counts"][
                evidence["cross_clause_status"]
            ] += 1
            diagnostics["cross_clause_basis_counts"][
                evidence["cross_clause_basis"]
            ] += 1
            diagnostics["cross_clause_status_counts_aggressive_split"][
                aggressive["cross_clause_status"]
            ] += 1
            diagnostics["disclaimer_status_counts"][
                evidence["disclaimer_status"]
            ] += 1
            if evidence["cross_clause_status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE":
                demotion_reason = "CROSS_CLAUSE_ATTACHMENT"
            elif evidence["disclaimer_status"] == "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER":
                demotion_reason = "DECLARATION_IS_A_DISCLAIMER"
            if conflict_original:
                diagnostics["middle_initial_conflicts_original"][
                    SCOPE_PUBLIC[source_scope]
                ] += 1
                entry = {
                    "lda_source_person_id": person_id,
                    "display_name": adjudicated["display_name"],
                    "scope": SCOPE_PUBLIC[source_scope],
                    "middle_tokens": mi["middles"],
                    "alias_tokens_stripped": mi["stripped"],
                    "target_middle_initial_after_alias_strip": mi["repaired"],
                    "payroll_middle_initial": payroll_mi,
                    "payroll_person_key": payroll_key,
                }
                if conflict_repaired:
                    diagnostics["middle_initial_conflicts_after_alias_strip"][
                        SCOPE_PUBLIC[source_scope]
                    ] += 1
                    diagnostics["middle_initial_survivors"].append(entry)
                else:
                    diagnostics["middle_initial_cleared"].append(entry)
                if conflict_full_table:
                    diagnostics["middle_initial_conflicts_full_nickname_table"][
                        SCOPE_PUBLIC[source_scope]
                    ] += 1

        if is_d4a:
            tier = "NON_EVIDENTIAL_HIT_ONLY"
        elif demotion_reason is not None:
            tier = "D1_DEMOTED_CANDIDATE"
            diagnostics[
                "demoted_cross_clause_attachment"
                if demotion_reason == "CROSS_CLAUSE_ATTACHMENT"
                else "demoted_declaration_is_a_disclaimer"
            ] += 1
            diagnostics["demotions"].append({
                "lda_source_person_id": person_id,
                "display_name": adjudicated["display_name"],
                "reason": demotion_reason,
                "office_key": office_key,
                "scope": SCOPE_PUBLIC[source_scope],
                "cross_clause_status": evidence["cross_clause_status"],
                "disclaimer_status": evidence["disclaimer_status"],
                "anchors": [anchor for _, anchor in evidence["anchors"]],
            })
        else:
            tier = STATUS_TO_TIER[status]

        is_link = tier == "D1_DECLARED_OFFICE_EXACT_UNIQUE"
        resolved = tier in {"D1_DECLARED_OFFICE_EXACT_UNIQUE", "D3_CANDIDATE"}
        tie_at_class = adjudicated["winning_tie_at_class"]
        recomputed_tie = hit_tie_at_class(winner, source_scope)
        if recomputed_tie != tie_at_class:
            raise BuildError(
                f"tie size disagreement for {person_id}: "
                f"{recomputed_tie!r} != {tie_at_class!r}"
            )
        if is_link and tie_at_class != 1:
            raise BuildError(f"D1 link with tie size {tie_at_class}: {person_id}")

        class_control = control.get(match_class, {})
        disclaimer_anywhere = declaration_has_disclaimer_clause(target)
        caveat = bool(
            disclaimer_anywhere and year_tokens_only_in_disclaimer_clauses(target)
        )
        if is_link and disclaimer_anywhere:
            diagnostics["d1_declaration_contains_disclaimer_clause"] += 1
        if is_link and caveat:
            diagnostics["d1_year_strengthener_disclaimer_caveat"] += 1

        row = {
            "schema_id": ROW_SCHEMA_ID,
            "rule_version": RULE_VERSION,
            "method_version": METHOD_VERSION,
            "run_id": run_id,
            "generation_id": generation_id,
            "phase": PHASE,
            "lda_source_person_id": person_id,
            "display_name": adjudicated["display_name"],
            "lda_priority": adjudicated.get("lda_priority"),
            "evidence_tier": tier,
            "evidence_tier_family": TIER_FAMILY[tier],
            "source_adjudicated_status": status,
            "source_adjudicated_substatus": substatus,
            "match_class": match_class,
            "match_class_control_fpr_point_pct": float(
                class_control.get("false_positive_rate_pct_point", 0.0)
            ),
            "match_class_control_fpr_upper95_pct": float(
                class_control.get("false_positive_rate_pct_upper95", 0.0)
            ),
            "scope": SCOPE_PUBLIC[source_scope],
            "source_scope": source_scope,
            "declared_office_texts": sorted({a for _, a in evidence["anchors"]}),
            "declared_office_supporting_clauses": sorted({
                s["clause"] for s in evidence["supporting"] if s["clause"]
            }),
            "declared_office_mention_kinds": sorted({
                k for k, _ in evidence["anchors"]
            }),
            "office_key": office_key,
            "office_container_kind": office_container_kind(winner, source_scope),
            "office_member_bioguide": office_member_bioguide(winner, source_scope),
            "office_distinct_payroll_people": winner.get(
                "office_distinct_payroll_people"
            ),
            "resolved_payroll_person_key": payroll_key if resolved else None,
            "candidate_payroll_person_keys": [] if resolved else tied,
            "payroll_titles": sorted({
                str(t) for t in (winner.get("payroll_titles") or [])
            }) if resolved else [],
            "payroll_periods": periods if resolved else [],
            "payroll_period_count": len(periods) if resolved else 0,
            "payroll_year_first": (
                adjudicated_year(winner, source_scope, first=True) if resolved else None
            ),
            "payroll_year_last": (
                adjudicated_year(winner, source_scope, first=False) if resolved else None
            ),
            "in_office_tie_size": tie_at_class,
            "in_office_tie_size_conservative": adjudicated[
                "winning_tie_conservative"
            ],
            "year_strengthener": substatus if is_link else None,
            "d3_strengthened": (
                substatus == "D3_STRENGTHENED_CLASS_EVIDENTIAL_AND_YEARS_OVERLAP"
                if tier == "D3_CANDIDATE" else None
            ),
            "demotion_reason": demotion_reason,
            "guard_cross_clause_attachment_status": (
                evidence["cross_clause_status"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NOT_APPLICABLE"
            ),
            "guard_cross_clause_attachment_basis": (
                evidence["cross_clause_basis"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NONE"
            ),
            "guard_disclaimer_status": (
                evidence["disclaimer_status"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NOT_APPLICABLE"
            ),
            "declaration_contains_disclaimer_clause": disclaimer_anywhere,
            "year_strengthener_disclaimer_caveat": caveat,
            "middle_initial_target_raw": mi["raw"],
            "middle_initial_target_after_alias_strip": mi["repaired"],
            "middle_initial_payroll": payroll_mi,
            "middle_initial_conflict_original": conflict_original,
            "middle_initial_conflict_after_alias_strip": conflict_repaired,
            "middle_initial_alias_tokens_stripped": mi["stripped"],
            "held_status": adjudicated.get("held_status"),
            "prior_resolution_status": adjudicated.get("prior_resolution_status"),
            "prior_best_tier": adjudicated.get("prior_best_tier"),
            "in_instructed_target_set": bool(
                adjudicated.get("in_instructed_target_set")
            ),
            "review_status": REVIEW_STATUS,
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "canonical_identity_promoted": False,
            "status_is_a_label_not_a_promotion": True,
        }
        if tier == "NON_EVIDENTIAL_HIT_ONLY":
            non_evidential.append(row)
        elif is_link:
            links.append(row)
        else:
            candidates.append(row)

    return {
        "links": links,
        "candidates": candidates,
        "non_evidential": non_evidential,
        "diagnostics": diagnostics,
    }


def adjudicated_year(hit: Mapping[str, Any], scope: str, first: bool) -> int | None:
    if scope == "house_member":
        return hit.get("payroll_year_first" if first else "payroll_year_last")
    if scope == "house_nonmember":
        years = sorted(hit.get("payroll_years") or [])
        if not years:
            return None
        return years[0] if first else years[-1]
    return hit.get("payroll_first_year" if first else "payroll_last_year")


def counter_to_dict(counter: Counter) -> dict[str, int]:
    return {str(key): int(value) for key, value in sorted(counter.items(),
                                                          key=lambda kv: str(kv[0]))}


def run(args: argparse.Namespace) -> dict[str, Any]:
    declaim_root = Path(args.declaim_root).resolve()
    output = Path(args.output_root).resolve()
    schema_path = (
        REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas" / ROW_SCHEMA_FILENAME
    )
    row_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    nickname_path = Path(args.nickname_file).resolve()
    nickname_entries = json.loads(nickname_path.read_text(encoding="utf-8"))["entries"]
    rule = NameAliasRule(nickname_entries)

    payload = load_inputs(declaim_root)
    manifest = payload["_manifest"]
    adjudication_record = next(m for m in manifest if m["name"] == "adjudication")
    if adjudication_record["sha256"] != ADJUDICATION_SHA256:
        raise BuildError(
            "adjudication.ndjson.gz does not match the pinned sha256: "
            f"{adjudication_record['sha256']} != {ADJUDICATION_SHA256}"
        )
    if adjudication_record["records"] != ADJUDICATION_ROWS:
        raise BuildError(
            f"adjudication row count {adjudication_record['records']} != "
            f"{ADJUDICATION_ROWS}"
        )
    manifest.append({
        "name": "first_name_nicknames",
        "path": str(nickname_path),
        "sha256": sha256_file(nickname_path),
        "bytes": nickname_path.stat().st_size,
        "records": len(nickname_entries),
    })
    manifest.append({
        "name": "row_schema",
        "path": str(schema_path),
        "sha256": sha256_file(schema_path),
        "bytes": schema_path.stat().st_size,
        "records": None,
    })

    # The generation id must NOT carry the _primary / _twin materialisation
    # suffix: primary and twin are the same generation built twice, and a row
    # that names its own directory can never be byte-identical across the two.
    generation_id = re.sub(r"_(primary|twin)$", "", output.name)
    built = build_rows(payload, rule, args.run_id, generation_id)
    links = built["links"]
    candidates = built["candidates"]
    non_evidential = built["non_evidential"]
    diagnostics = built["diagnostics"]

    for row in links + candidates + non_evidential:
        validate_instance(row, row_schema)

    # ---- gates: the emitted tier must reproduce the adjudication ----------
    failures: list[str] = []
    if diagnostics["d1_before_guards"] != EXPECTED_STATUS_COUNTS[
        "D1_DECLARED_OFFICE_EXACT_UNIQUE"
    ]:
        failures.append("D1_INPUT_COUNT_MISMATCH")
    demoted = (
        diagnostics["demoted_cross_clause_attachment"]
        + diagnostics["demoted_declaration_is_a_disclaimer"]
    )
    if len(links) != diagnostics["d1_before_guards"] - demoted:
        failures.append("D1_AFTER_GUARDS_ARITHMETIC_MISMATCH")
    by_class = Counter(row["match_class"] for row in links)
    by_scope = Counter(row["scope"] for row in links)
    by_year = Counter(row["year_strengthener"] for row in links)
    if demoted == 0:
        if dict(by_class) != EXPECTED_D1_BY_CLASS:
            failures.append("D1_CLASS_SPLIT_MISMATCH")
        if dict(by_scope) != EXPECTED_D1_BY_SCOPE:
            failures.append("D1_SCOPE_SPLIT_MISMATCH")
        if dict(by_year) != EXPECTED_D1_BY_YEAR:
            failures.append("D1_YEAR_SPLIT_MISMATCH")
    strengthened = sum(1 for row in candidates if row["d3_strengthened"])
    if strengthened != EXPECTED_D3_STRENGTHENED:
        failures.append("D3_STRENGTHENED_MISMATCH")
    if len(non_evidential) != EXPECTED_D4A:
        failures.append("D4A_COUNT_MISMATCH")
    if any(row["canonical_employment_promoted"] for row in
           links + candidates + non_evidential):
        failures.append("PROMOTION_FLAG_SET")
    if any(row["evidence_tier"] == "NON_EVIDENTIAL_HIT_ONLY"
           for row in links + candidates):
        failures.append("NON_EVIDENTIAL_ROW_OUTSIDE_ITS_FILE")
    if any(row["match_class"] == "FIRST_INITIAL" for row in links + candidates):
        failures.append("FIRST_INITIAL_IN_A_LINK_OR_CANDIDATE_FILE")

    staging = prepare_output(output)
    try:
        write_ndjson(staging / LINKS_FILENAME, links)
        write_ndjson(staging / CANDIDATES_FILENAME, candidates)
        write_ndjson(staging / NON_EVIDENTIAL_FILENAME, non_evidential)

        first_initial_control = payload["control_report"]["by_match_class"][
            "FIRST_INITIAL"
        ]
        d1_control = payload["adj_control_d1"]["pooled"]

        receipt = {
            "schema_id": RECEIPT_SCHEMA_ID,
            "schema_note": (
                "This receipt has no committed JSON schema. The task authorises "
                "exactly one new committed schema and it is the row schema."
            ),
            "run_id": args.run_id,
            "glassbox_source": GLASSBOX_SOURCE,
            "generation_id": generation_id,
            "materialisation": output.name,
            "generated_at_utc": args.generated_at,
            "rule_version": RULE_VERSION,
            "method_version": METHOD_VERSION,
            "phase": PHASE,
            "status": "FAIL" if failures else "PASS",
            "statement": (
                "Declaration-directed employment tier. D1 is a label with a "
                "measured status false-positive rate attached, not an identity "
                "finding and not a promotion. D3, D2 and D3M are candidates. "
                "FIRST_INITIAL is excluded from every link tier."
            ),
            "directed_by": {
                "document": "ADJUDICATION.md",
                "rule_version": ADJUDICATION_RULE_VERSION,
                "adjudication_sha256_expected": ADJUDICATION_SHA256,
                "adjudication_sha256_actual": adjudication_record["sha256"],
                "adjudication_sha256_match": True,
                "adjudication_rows": adjudication_record["records"],
                "adjudication_status_counts_reproduced": EXPECTED_STATUS_COUNTS,
            },
            "inputs": sorted(manifest, key=lambda m: m["name"]),
            "counts": {
                "adjudicated_rows_read": adjudication_record["records"],
                "d1_before_guards": diagnostics["d1_before_guards"],
                "d1_after_guards": len(links),
                "d1_demoted_total": demoted,
                "d1_by_match_class": counter_to_dict(by_class),
                "d1_by_scope": counter_to_dict(by_scope),
                "d1_by_year_strengthener": counter_to_dict(by_year),
                "candidates_total": len(candidates),
                "candidates_by_tier": counter_to_dict(
                    Counter(row["evidence_tier"] for row in candidates)
                ),
                "d3_strengthened": strengthened,
                "non_evidential_total": len(non_evidential),
                "rows_total": len(links) + len(candidates) + len(non_evidential),
            },
            "guards": {
                "cross_clause_attachment": {
                    "reason_code": "CROSS_CLAUSE_ATTACHMENT",
                    "definition": (
                        "A D1 row survives only when at least one clause of the "
                        "filer's own covered-position text both contains the "
                        "anchor that attached the winning office key (the member "
                        "name for a MEMBER mention, the matched alias for a "
                        "COMMITTEE mention) and contains a legislative cue. An "
                        "anchor that cannot be located in any clause is treated "
                        "as a failure, which is the fail-closed reading."
                    ),
                    "clause_boundaries": "; newline [ ]",
                    "demoted": diagnostics["demoted_cross_clause_attachment"],
                    "status_counts": counter_to_dict(
                        diagnostics["cross_clause_status_counts"]
                    ),
                    "location_basis_counts": counter_to_dict(
                        diagnostics["cross_clause_basis_counts"]
                    ),
                    "sensitivity_aggressive_clause_split": {
                        "clause_boundaries": "; newline [ ] / |",
                        "status_counts": counter_to_dict(
                            diagnostics[
                                "cross_clause_status_counts_aggressive_split"
                            ]
                        ),
                        "applied": False,
                    },
                },
                "declaration_is_a_disclaimer": {
                    "reason_code": "DECLARATION_IS_A_DISCLAIMER",
                    "definition": (
                        "A supporting clause is a disclaimer when its leading "
                        "token is a negation and it then names the office anchor. "
                        "A D1 row is demoted only when EVERY supporting clause is "
                        "a disclaimer: a filer who prefixes a real declaration "
                        "with a lobbying disclaimer still declared the position."
                    ),
                    "demoted": diagnostics["demoted_declaration_is_a_disclaimer"],
                    "status_counts": counter_to_dict(
                        diagnostics["disclaimer_status_counts"]
                    ),
                    "d1_rows_whose_declaration_contains_a_disclaimer_clause":
                        diagnostics["d1_declaration_contains_disclaimer_clause"],
                    "d1_rows_flagged_year_strengthener_disclaimer_caveat":
                        diagnostics["d1_year_strengthener_disclaimer_caveat"],
                },
                "middle_initial_alias_strip": {
                    "demotes": False,
                    "definition": (
                        "The Senate searcher's is_embedded_alias rule is applied "
                        "to every scope's target display name and the middle "
                        "initial re-derived, so inlined go-by names stop "
                        "manufacturing conflicts. A surviving conflict is a "
                        "field, never a demotion."
                    ),
                    "conflicts_original": counter_to_dict(
                        diagnostics["middle_initial_conflicts_original"]
                    ),
                    "conflicts_original_total": sum(
                        diagnostics["middle_initial_conflicts_original"].values()
                    ),
                    "conflicts_after_alias_strip": counter_to_dict(
                        diagnostics["middle_initial_conflicts_after_alias_strip"]
                    ),
                    "conflicts_after_alias_strip_total": sum(
                        diagnostics[
                            "middle_initial_conflicts_after_alias_strip"
                        ].values()
                    ),
                    "sensitivity_full_nickname_table": {
                        "note": (
                            "The Senate rule's canon_given consults only "
                            "nickname entries with exactly one formal expansion, "
                            "so KATIE -> {KATHERINE, KATHRYN} is invisible to it. "
                            "Consulting every expansion in both directions would "
                            "leave this many conflicts. Measured, not applied."
                        ),
                        "conflicts": counter_to_dict(
                            diagnostics[
                                "middle_initial_conflicts_full_nickname_table"
                            ]
                        ),
                        "conflicts_total": sum(
                            diagnostics[
                                "middle_initial_conflicts_full_nickname_table"
                            ].values()
                        ),
                        "applied": False,
                    },
                    "surviving_conflicts": sorted(
                        diagnostics["middle_initial_survivors"],
                        key=lambda e: e["lda_source_person_id"],
                    ),
                    "cleared_conflicts": sorted(
                        diagnostics["middle_initial_cleared"],
                        key=lambda e: e["lda_source_person_id"],
                    ),
                },
                "demotions": sorted(
                    diagnostics["demotions"],
                    key=lambda d: d["lda_source_person_id"],
                ),
            },
            "measured_error_rates": {
                "d1_status_false_positive_rate_point_pct": d1_control[
                    "D1_status_fpr_point_pct"
                ],
                "d1_status_false_positive_rate_upper95_pct": d1_control[
                    "D1_status_fpr_upper95_pct"
                ],
                "d1_status_fpr_basis": (
                    "2 control D1s in 2,783 paired control searches per arm; "
                    "850 declared D1s in the same 2,783."
                ),
                "d1_status_fpr_control_d1": d1_control["control_D1"],
                "d1_status_fpr_declared_d1": d1_control["declared_D1"],
                "d1_status_fpr_searches_per_arm": d1_control[
                    "target_scope_rows_per_arm"
                ],
                "per_match_class": {
                    name: {
                        "false_positive_rate_pct_point": payload["control_report"][
                            "by_match_class"][name]["false_positive_rate_pct_point"],
                        "false_positive_rate_pct_upper95": payload["control_report"][
                            "by_match_class"][name]["false_positive_rate_pct_upper95"],
                        "verdict": payload["control_report"]["class_verdicts"][name],
                    }
                    for name in sorted(payload["control_report"]["by_match_class"])
                },
            },
            "exclusions": {
                "FIRST_INITIAL": {
                    "emitted_as": "NON_EVIDENTIAL_HIT_ONLY",
                    "rows": len(non_evidential),
                    "never_a_link_tier": True,
                    "control_false_positive_rate_pct_point": first_initial_control[
                        "false_positive_rate_pct_point"
                    ],
                    "control_false_positive_rate_pct_upper95": first_initial_control[
                        "false_positive_rate_pct_upper95"
                    ],
                    "control_hits": first_initial_control["control"]["hits"],
                    "control_searches": first_initial_control["control"]["searches"],
                    "reason": (
                        "The paired control measured this class at a 6.98 percent "
                        "point false-positive rate with a 20.38 percent 95 percent "
                        "upper bound, and it supplied 3 of the 5 total control "
                        "hits. It is also not one rule: search_house_nonmember "
                        "accepts any two given names sharing a first letter while "
                        "the House-member and Senate matchers require a bare "
                        "initial."
                    ),
                },
                "D3": {
                    "emitted_as": "D3_CANDIDATE",
                    "rows": sum(
                        1 for row in candidates if row["evidence_tier"] == "D3_CANDIDATE"
                    ),
                    "strengthened": strengthened,
                    "never_a_link": True,
                },
                "D2_and_D3M": {
                    "emitted_as": ["D2_CANDIDATE", "D3M_CANDIDATE"],
                    "rows": sum(
                        1 for row in candidates
                        if row["evidence_tier"] in {"D2_CANDIDATE", "D3M_CANDIDATE"}
                    ),
                    "never_resolved": True,
                    "resolved_payroll_person_key_emitted": 0,
                },
            },
            "promotion_policy": PROMOTION_POLICY,
            "canonical_identity_promotions": 0,
            "canonical_employment_promotions": 0,
            "review_status": REVIEW_STATUS,
            "period_review_flags": counter_to_dict(
                diagnostics["period_review_flags"]
            ),
            "winner_hit_multiplicity": counter_to_dict(
                diagnostics["winner_hit_multiplicity"]
            ),
            "files": [],
            "implementation": {
                "path": Path(__file__).name,
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "failures": failures,
        }
        files = []
        for filename, rows in (
            (LINKS_FILENAME, links),
            (CANDIDATES_FILENAME, candidates),
            (NON_EVIDENTIAL_FILENAME, non_evidential),
        ):
            path = staging / filename
            files.append({
                "name": filename,
                "records": len(rows),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })
        receipt["files"] = files
        (staging / RECEIPT_FILENAME).write_bytes(canonical_json_bytes(receipt))
        os.replace(staging, output)
        return receipt
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the D1 declaration-directed employment tier."
    )
    parser.add_argument("--declaim-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--nickname-file",
        default=str(
            REPOSITORY_ROOT / "data" / "staffer_network" / "reference"
            / "first_name_nicknames_v1.json"
        ),
    )
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox, kind="run.start", status="running",
        summary="declaration-directed D1 employment tier build",
        detail=str(args.output_root), run_id=args.run_id,
        stage="build-declaration-directed-tier",
    )
    try:
        receipt = run(args)
    except BaseException as error:
        emit_glassbox(
            enabled=glassbox, kind="run.finish", status="failed",
            summary="declaration-directed D1 employment tier build failed",
            detail=f"{type(error).__name__}: {error}", run_id=args.run_id,
            stage="build-declaration-directed-tier",
        )
        raise
    emit_glassbox(
        enabled=glassbox, kind="run.finish",
        status="completed" if receipt["status"] == "PASS" else "failed",
        summary="declaration-directed D1 employment tier build",
        detail=(
            f"links={receipt['counts']['d1_after_guards']} "
            f"candidates={receipt['counts']['candidates_total']} "
            f"non_evidential={receipt['counts']['non_evidential_total']} "
            f"demoted={receipt['counts']['d1_demoted_total']}"
        ),
        run_id=args.run_id, stage="build-declaration-directed-tier",
    )
    print(json.dumps(
        {"status": receipt["status"], "counts": receipt["counts"],
         "files": receipt["files"], "failures": receipt["failures"]},
        sort_keys=True,
    ))
    return 1 if receipt["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
