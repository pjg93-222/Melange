#!/usr/bin/env python3
r"""Build the control-cleared declaration-widened recovery tier as an immutable generation.

What this builds, and only this
-------------------------------
The recovery lane (``scratchpad/recover``) measured four given-name widening rules
against a paired negative control and cleared them, then applied them to the
targets PHASE Adjudicate had left at ``D4b_NO_HIT_AT_ALL``.  It also searched the
offices PHASE Search had resolved but never searched (``D5c``).  This builder
turns that measurement into a generation, and encodes the refusals explicitly
rather than by omission.

Three files:

* ``declaration_widened_employment_links.ndjson.gz`` -- the 70 E1 rows, tier
  ``E1_DECLARED_OFFICE_WIDENED_GIVEN_UNIQUE``.  This is its OWN tier and it is
  explicitly BELOW D1 (``tier_rank_relative_to_d1: "BELOW"``): the surname matched
  at the strictest level its scope has and the office is the filer's own
  declaration, but the GIVEN NAME was widened.  The firing rule travels on every
  row as ``widening_rule`` together with that rule's own declared/control counts
  and status false-positive bounds.
* ``declaration_directed_recovered_links.ndjson.gz`` -- the 18 A3 rows whose
  winning office had RESOLVED provenance.  These are not widened: surname and
  given name matched at the census exact class, so they rank EQUAL to D1 and are
  tiered ``D1_DECLARED_OFFICE_EXACT_UNIQUE_RECOVERED``.
* ``held_for_review.ndjson.gz`` -- the 14 A3 rows whose only winning office had
  FLAGGED provenance.  ``build_targets.py`` documents that tier as containing
  confirmed false office attachments ("Rep. Bill McCollum" resolving to Betty
  McCollum), so they are preserved and visible but never linked.  Their
  ``hold_reason`` says so on the row.

Refusals that are recorded, not hidden
--------------------------------------
* The compound-surname rule (S1) is NOT implemented.  The House ``payee_parse``
  strips hyphens, so ``GRECO-JOHNSON`` arrives as ``GRECOJOHNSON`` with no token
  boundary; the rule is unsafe because it is unpowered on this corpus.  The
  forgone yield is carried in the receipt as a declared refusal.
* Rule Z (surname only, any given) is never used to recover anything.  It exists
  only as the positive control that proves the control arm could fire, and its
  numbers are carried next to the zero they license.

The cross-clause guard
----------------------
``ADJUDICATION.md`` defect 4: PHASE Target matched office aliases as substrings of
the WHOLE declared value rather than span-anchored, so a value naming several
employers could attach an office belonging to a clause that carries no
legislative cue.  Every row this builder emits is re-anchored: the mention that
produced the winning office key is located inside the filer's own
covered-position text, the text is cut into clauses, and at least one clause
containing the anchor must also contain a legislative cue.  A row that fails --
including one whose anchor cannot be located at all, the fail-closed reading --
is demoted into ``held_for_review.ndjson.gz`` with reason
``CROSS_CLAUSE_ATTACHMENT``.  The guard is measured whether or not it fires.

Nothing here is promoted.  Every emitted row carries ``canonical_eligible:
false``, ``canonical_employment_promoted: false``, ``canonical_identity_decision:
"NOT_ADJUDICATED"`` and ``review_status: "REVIEW_REQUIRED"``, and the receipt pins
both promotion counters to 0.

Read-only on every input.  Never imports a ``fec`` module other than
``fec/staffer_network/intervals.py`` and ``fec/staffer_network/schema_validation.py``.
Runs no git command.  Refuses a non-empty output directory, stages into a sibling
temporary directory and renames it into place, and writes canonical NDJSON
(sorted keys, gzip mtime 0) so a twin run is byte-identical.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
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

ROW_SCHEMA_ID = "staffer-network-declaration-widened-employment-link-v1"
RECEIPT_SCHEMA_ID = "staffer-network-declaration-widened-tier-receipt-v1"
RULE_VERSION = "declaration-widened-employment-tier-v1"
METHOD_VERSION = "declaration-widened-employment-tier-v1"
PHASE = "build-declaration-widened-tier"
PROMOTION_POLICY = "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
REVIEW_STATUS = "REVIEW_REQUIRED"
GLASSBOX_SOURCE = "declaration-directed-e1"
EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"

WIDENED_FILENAME = "declaration_widened_employment_links.ndjson.gz"
RECOVERED_FILENAME = "declaration_directed_recovered_links.ndjson.gz"
HELD_FILENAME = "held_for_review.ndjson.gz"
RECEIPT_FILENAME = "declaration_widened_tier_receipt.json"

ROW_SCHEMA_FILENAME = "declaration_widened_employment_link.schema.json"

E1_TIER = "E1_DECLARED_OFFICE_WIDENED_GIVEN_UNIQUE"
D1R_TIER = "D1_DECLARED_OFFICE_EXACT_UNIQUE_RECOVERED"
HELD_TIER = "D1_RECOVERED_HELD_FOR_REVIEW"

HOLD_FLAGGED = "FLAGGED_OFFICE_PROVENANCE_CONFIRMED_FALSE_ATTACHMENT_CLASS"
HOLD_CROSS_CLAUSE = "CROSS_CLAUSE_ATTACHMENT"

SAFE_RULES = ("A_GIVEN_ALT_TOKEN", "B_NICK_DROPPED", "C_GIVEN_PREFIX", "D_GIVEN_ED1")
POSITIVE_CONTROL_RULE = "Z_SURNAME_ONLY_ANY_GIVEN"

SCOPE_PUBLIC = {
    "house_member": "house_member",
    "house_nonmember": "house_nonmember",
    "senate_all": "senate",
}

# Counts the recovery lane published.  Reproduced, never assumed: a mismatch is a
# build failure, so the tier can never silently drift off its own basis.
EXPECTED_E1_ROWS = 70
EXPECTED_E1_BY_RULE = {
    "A_GIVEN_ALT_TOKEN": 5,
    "B_NICK_DROPPED": 30,
    "C_GIVEN_PREFIX": 21,
    "D_GIVEN_ED1": 14,
}
EXPECTED_E1_BY_YEAR = {"E1_YEAR_CORROBORATED": 17, "E1_YEAR_UNTESTABLE": 53}
EXPECTED_E1_BY_SCOPE = {"house_member": 44, "house_nonmember": 11, "senate": 15}
EXPECTED_E1_BY_PRIOR = {"CANDIDATE_R4": 64, "CANDIDATE_R3": 1, "NOT_FOUND": 5}
EXPECTED_RECOVERED_ROWS = 18
EXPECTED_HELD_ROWS = 14
EXPECTED_CONTROL_SEARCHES_PER_ARM = 2783
EXPECTED_POOLED_DECLARED_UNIQUE_TARGETS = 72
EXPECTED_POOLED_CONTROL_UNIQUE_TARGETS = 0

# The compound-surname rule that was measured and refused.
S1_FORGONE_YIELD_RULED = 2

RECOVER_INPUTS: tuple[tuple[str, str], ...] = (
    ("e3_recovered", "e3_recovered.json"),
    ("a3_rows", "a3_rows.json"),
    ("control_newrules", "control_newrules.json"),
    ("control_newrules_per_target", "control_newrules_per_target.json.gz"),
    ("newrules_source", "newrules.py"),
    ("matchers_source", "matchers.py"),
    ("control_newrules_source", "control_newrules.py"),
    ("e3_recover_source", "e3_recover.py"),
    ("a3_search_source", "a3_search.py"),
    ("e3_strict", "e3_strict.json"),
    ("metric_delta", "metric_delta.json"),
    ("residual", "residual.json"),
    ("index_manifest", "index_manifest.json"),
)
DECLAIM_INPUTS: tuple[tuple[str, str], ...] = (
    ("targets", "targets.ndjson.gz"),
    ("adjudication", "adjudication.ndjson.gz"),
    ("adjudication_doc", "ADJUDICATION.md"),
    ("build_targets_source", "build_targets.py"),
)
CORPUS_INPUTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("house_personnel_observations",
     ("audits", "staffer_network", "house_personnel_ledger_20260902_v3_primary",
      "house_personnel_observations.ndjson.gz")),
    ("house_person_office_spans",
     ("audits", "staffer_network", "house_personnel_ledger_20260902_v3_primary",
      "house_person_office_spans.ndjson.gz")),
    ("senate_payroll_employment_candidates",
     ("audits", "staffer_network",
      "official_senate_payroll_2011_2026_employment_scope_v1",
      "senate_payroll_employment_candidates_2011_2026.ndjson.gz")),
)

QUARTER_START = {"Q1": (1, 1), "Q2": (4, 1), "Q3": (7, 1), "Q4": (10, 1)}
QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}

# ---------------------------------------------------------------------------
# guard vocabularies -- identical in effect to build_declaration_directed_tier.py
# so the E1 tier is graded on the same scale the shipped D1 tier was graded on
# ---------------------------------------------------------------------------

CLAUSE_STOPWORDS = frozenset({"AND", "THE", "OF"})
LEGISLATIVE_CUE = re.compile(
    r"\b(REP|REPS|REPRESENTATIVE|REPRESENTATIVES|CONGRESSMAN|CONGRESSWOMAN|"
    r"CONGRESSMEMBER|CONGRESSMEN|CONGRESSWOMEN|CONG|CONGR|SEN|SENS|SENATOR|"
    r"SENATORS|SENATE|HOUSE|CONGRESS|CONGRESSIONAL|COMMITTEE|COMMITTEES|"
    r"SUBCOMMITTEE|SUBCOMMITTEES|CMTE|CAUCUS|CAPITOL|HILL|SPEAKER|WHIP|"
    r"DELEGATE|LEADERSHIP|CLOAKROOM|PARLIAMENTARIAN|MAJORITY|MINORITY|"
    r"LEADER|CHAIRMAN|CHAIRWOMAN|RANKING|MEMBER)\b"
)
DISCLAIMER_LEADING_NEGATION = re.compile(r"^(NO|NOT|NONE|NEVER)\b")
CLAUSE_SPLIT = re.compile(r"[;\n\[\]]")
CLAUSE_SPLIT_AGGRESSIVE = re.compile(r"[;\n\[\]/|]")
NON_ALNUM = re.compile(r"[^A-Z0-9]+")
LETTERS_ONLY = re.compile(r"[^A-Z]")


class BuildError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# deterministic io helpers
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


def contains_ordered_subsequence(anchor: Sequence[str], clause: Sequence[str]) -> bool:
    """Fallback location test: the anchor's tokens, in order, inside one clause."""
    if not anchor:
        return False
    cursor = iter(clause)
    return all(any(token == want for token in cursor) for want in anchor)


def declared_anchors(target: Mapping[str, Any], office_key: str) -> list[tuple[str, str]]:
    """(mention kind, anchor text) pairs that attached this office key."""
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
                    "leading_negation": bool(DISCLAIMER_LEADING_NEGATION.match(joined)),
                })
    if not supporting:
        return {
            "anchors": anchors, "supporting": [],
            "cross_clause_status": "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE",
            "cross_clause_basis": "NONE",
            "disclaimer_status": "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT",
        }
    with_cue = [s for s in supporting if s["legislative_cue"]]
    if with_cue:
        status = "CLAUSE_CARRIES_LEGISLATIVE_CUE"
        basis = min((s["basis"] for s in with_cue), key=lambda b: basis_rank[b])
    else:
        status = "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
        basis = min((s["basis"] for s in supporting), key=lambda b: basis_rank[b])
    negations = sum(1 for s in supporting if s["leading_negation"])
    if negations == 0:
        disclaimer = "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT"
    elif negations == len(supporting):
        disclaimer = "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"
    else:
        disclaimer = "SOME_SUPPORTING_CLAUSES_ARE_DISCLAIMERS"
    return {
        "anchors": anchors, "supporting": supporting,
        "cross_clause_status": status, "cross_clause_basis": basis,
        "disclaimer_status": disclaimer,
    }


def declaration_has_disclaimer_clause(target: Mapping[str, Any]) -> bool:
    for value in target.get("covered_position_values") or []:
        for clause in split_clauses(value):
            joined = " ".join(clause_tokens(clause))
            if DISCLAIMER_LEADING_NEGATION.match(joined) and LEGISLATIVE_CUE.search(joined):
                return True
    return False


GUARD_POWER_SUBSTITUTIONS = 25
GUARD_POWER_STRIDE = 7919


def guard_power(
    targets: Mapping[str, Mapping[str, Any]],
    audited: Sequence[tuple[str, str]],
) -> dict[str, Any]:
    """A guard that never fires needs proof it could.

    Two deterministic negative controls, both run over exactly the rows this
    build emits:

    * FOREIGN OFFICE KEY -- substitute an office key the filer never declared
      for the winning one.  The guard must reject it.
    * SYNTHETIC ANCHOR IN A NON-CUE CLAUSE -- keep the filer's own declaration
      and invent an anchor drawn from a clause of it that carries no legislative
      cue.  The guard must reject that too, unless the same token run also
      appears in a clause that does carry a cue, which is a correct acceptance.

    No RNG: the substitution index is a stride over a sorted key list, seeded by
    a digest of the person id, so the measurement is byte-reproducible.
    """
    all_keys = sorted({
        key
        for target in targets.values()
        for mention in (target.get("declared_office_mentions") or [])
        for key in (mention.get("office_keys") or [])
    })
    foreign = Counter()
    foreign_trials = 0
    synthetic = Counter()
    synthetic_trials = 0
    for pid, _office_key in audited:
        target = targets[pid]
        own = {
            key
            for mention in (target.get("declared_office_mentions") or [])
            for key in (mention.get("office_keys") or [])
        }
        seed = int(hashlib.sha256(pid.encode("utf-8")).hexdigest()[:8], 16)
        for step in range(GUARD_POWER_SUBSTITUTIONS):
            candidate = all_keys[(seed + step * GUARD_POWER_STRIDE) % len(all_keys)]
            if candidate in own:
                continue
            foreign_trials += 1
            foreign[attachment_evidence(target, candidate)["cross_clause_status"]] += 1
        for value in target.get("covered_position_values") or []:
            picked = None
            for clause in split_clauses(value):
                tokens = clause_tokens(clause)
                if not tokens or LEGISLATIVE_CUE.search(" ".join(tokens)):
                    continue
                picked = tokens[:3]
                break
            if picked is None:
                continue
            fake = {
                "covered_position_values": target.get("covered_position_values"),
                "declared_office_mentions": [{
                    "kind": "MEMBER", "office_keys": ["SYNTHETIC_NON_CUE_ANCHOR"],
                    "text": " ".join(picked),
                }],
            }
            synthetic_trials += 1
            synthetic[
                attachment_evidence(fake, "SYNTHETIC_NON_CUE_ANCHOR")["cross_clause_status"]
            ] += 1
            break
    return {
        "why_it_is_here": (
            "The guard demoted nobody. A zero demotion rate is only meaningful "
            "beside evidence that the guard rejects an attachment it should."
        ),
        "foreign_office_key_substitution": {
            "definition": (
                "For each audited row, up to %d office keys the filer never "
                "declared are substituted for the winning key and the guard is "
                "re-run. A guard with power rejects all of them."
                % GUARD_POWER_SUBSTITUTIONS
            ),
            "trials": foreign_trials,
            "status_counts": counter_to_dict(foreign),
            "rejected": sum(count for status, count in foreign.items()
                            if status != "CLAUSE_CARRIES_LEGISLATIVE_CUE"),
        },
        "synthetic_anchor_in_a_non_cue_clause": {
            "definition": (
                "For each audited row whose own declaration has a clause carrying "
                "no legislative cue, a synthetic anchor is built from that clause "
                "and the guard is re-run. An acceptance here is correct only when "
                "the same token run also appears in a cue-carrying clause."
            ),
            "trials": synthetic_trials,
            "status_counts": counter_to_dict(synthetic),
        },
    }


# ---------------------------------------------------------------------------
# payroll enrichment, read straight from the corpora
# ---------------------------------------------------------------------------


def letters(value: str | None) -> str:
    return LETTERS_ONLY.sub("", (value or "").upper())


def senate_person_key(payee_name_raw: str | None) -> str | None:
    """SURNAME|GIVEN|MI from a Senate payee string, conservatively.

    The recovery lane keyed Senate people with the shipped Senate matcher; this
    builder does not import that matcher, so it derives the same triple from the
    raw payee string directly and the build gates on every wanted key resolving.
    """
    text = (payee_name_raw or "").upper().replace(".", " ")
    if "," not in text:
        return None
    left, right = text.split(",", 1)
    surname = letters(left)
    tokens = [letters(token) for token in right.split() if letters(token)]
    if not surname or not tokens:
        return None
    middle = tokens[1][:1] if len(tokens) > 1 else ""
    return "%s|%s|%s" % (surname, tokens[0], middle)


def normalise_person_key(scope: str, person_key: str) -> str:
    """The Senate carries two key shapes; reduce both to SURNAME|GIVEN|MI."""
    if scope != "senate_all":
        return person_key
    parts = person_key.split("|")
    if len(parts) >= 5:
        return "|".join(parts[-3:])
    return person_key


def quarter_bounds(quarter: str, end: bool) -> str | None:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", quarter or "")
    if not match:
        return None
    year = int(match.group(1))
    month, day = (QUARTER_END if end else QUARTER_START)[match.group(2)]
    return date(year, month, day).isoformat()


def collect_payroll(
    wanted: set[tuple[str, str, str]], corpus_paths: Mapping[str, Path]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """One pass per corpus; only the wanted (scope, office, person) triples."""
    out: dict[tuple[str, str, str], dict[str, Any]] = {}

    def slot(key: tuple[str, str, str]) -> dict[str, Any]:
        entry = out.get(key)
        if entry is None:
            entry = out[key] = {
                "titles": set(), "quarters": set(), "raw": set(),
                "service_starts": set(), "service_ends": set(),
                "spans": set(), "periods": set(), "years": set(),
                "container_kinds": set(), "bioguides": set(), "rows": 0,
            }
        return entry

    member = {(o, p) for s, o, p in wanted if s == "house_member"}
    nonmember = {(o, p) for s, o, p in wanted if s == "house_nonmember"}
    senate = {(o, p) for s, o, p in wanted if s == "senate_all"}
    senate_offices = {o for o, _ in senate}

    if member:
        for row in read_rows(corpus_paths["house_personnel_observations"]):
            pair = (row.get("office_key"), row.get("person_key"))
            if pair not in member:
                continue
            entry = slot(("house_member", pair[0], pair[1]))
            entry["rows"] += 1
            if row.get("title_raw"):
                entry["titles"].add(str(row["title_raw"]))
            if row.get("quarter"):
                entry["quarters"].add(str(row["quarter"]))
            if row.get("payee_raw"):
                entry["raw"].add(str(row["payee_raw"]))
            if row.get("service_start"):
                entry["service_starts"].add(str(row["service_start"]))
            if row.get("service_end"):
                entry["service_ends"].add(str(row["service_end"]))
            if row.get("container_kind"):
                entry["container_kinds"].add(str(row["container_kind"]))
            if row.get("member_bioguide"):
                entry["bioguides"].add(str(row["member_bioguide"]))

    if nonmember:
        for row in read_rows(corpus_paths["house_person_office_spans"]):
            pair = (row.get("office_key"), row.get("person_key"))
            if pair not in nonmember:
                continue
            entry = slot(("house_nonmember", pair[0], pair[1]))
            entry["rows"] += 1
            entry["titles"].update(str(t) for t in (row.get("titles") or []))
            entry["quarters"].update(str(q) for q in (row.get("quarters_observed") or []))
            entry["raw"].update(str(x) for x in (row.get("office_raw_examples") or [])[:0])
            start, end = row.get("service_start_min"), row.get("service_end_max")
            if start and end:
                entry["spans"].add((str(start), str(end)))
            if row.get("container_kind"):
                entry["container_kinds"].add(str(row["container_kind"]))
            if row.get("member_bioguide"):
                entry["bioguides"].add(str(row["member_bioguide"]))

    if senate:
        for row in read_rows(corpus_paths["senate_payroll_employment_candidates"]):
            office = row.get("office_raw")
            if office not in senate_offices:
                continue
            derived = senate_person_key(row.get("payee_name_raw"))
            if derived is None or (office, derived) not in senate:
                continue
            entry = slot(("senate_all", office, derived))
            entry["rows"] += 1
            title = row.get("title_candidate") or row.get("title_raw")
            if title:
                entry["titles"].add(str(title))
            if row.get("payee_name_raw"):
                entry["raw"].add(str(row["payee_name_raw"]))
            start, end = row.get("report_period_start"), row.get("report_period_end")
            if start and end:
                entry["periods"].add((str(start), str(end)))
                entry["years"].update(range(int(start[:4]), int(end[:4]) + 1))
            for interval in row.get("date_intervals") or []:
                a, b = interval.get("start"), interval.get("end")
                if a and b:
                    entry["years"].update(range(int(a[:4]), int(b[:4]) + 1))
    return out


def payroll_view(scope: str, entry: Mapping[str, Any] | None) -> dict[str, Any]:
    """Titles, periods and years for one payroll person inside one office."""
    if entry is None:
        return {"titles": [], "periods": [], "years": [], "raw": [], "rows": 0,
                "container_kind": None, "member_bioguide": None}
    periods: list[dict[str, Any]] = []
    if scope == "house_member":
        starts = sorted(entry["service_starts"])
        ends = sorted(entry["service_ends"])
        if starts and ends:
            periods.append({"start": starts[0], "end": ends[-1],
                            "basis": "HOUSE_SOD_SERVICE_SPAN"})
        else:
            quarters = sorted(entry["quarters"])
            if quarters:
                periods.append({"start": quarter_bounds(quarters[0], end=False),
                                "end": quarter_bounds(quarters[-1], end=True),
                                "basis": "HOUSE_SOD_QUARTER_ENVELOPE"})
        years = sorted({int(q[:4]) for q in entry["quarters"] if q[:4].isdigit()})
    elif scope == "house_nonmember":
        for start, end in sorted(entry["spans"]):
            periods.append({"start": start, "end": end,
                            "basis": "HOUSE_SOD_SERVICE_SPAN"})
        if not periods:
            quarters = sorted(entry["quarters"])
            if quarters:
                periods.append({"start": quarter_bounds(quarters[0], end=False),
                                "end": quarter_bounds(quarters[-1], end=True),
                                "basis": "HOUSE_SOD_QUARTER_ENVELOPE"})
        years = sorted({int(q[:4]) for q in entry["quarters"] if q[:4].isdigit()})
    else:
        for start, end in sorted(entry["periods"]):
            periods.append({"start": start, "end": end,
                            "basis": "SENATE_REPORT_PERIOD"})
        years = sorted(entry["years"])
    unique = {(p["start"], p["end"], p["basis"]): p for p in periods}
    containers = sorted(entry["container_kinds"])
    bioguides = sorted(entry["bioguides"])
    return {
        "titles": sorted(entry["titles"]),
        "periods": [unique[key] for key in sorted(unique)],
        "years": years,
        "raw": sorted(entry["raw"]),
        "rows": entry["rows"],
        "container_kind": containers[0] if containers else None,
        "member_bioguide": bioguides[0] if bioguides else None,
    }


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


# ---------------------------------------------------------------------------
# year strengthener
# ---------------------------------------------------------------------------

E1_YEAR = {
    "OVERLAP": "E1_YEAR_CORROBORATED",
    "RANGE_OVERLAP": "E1_YEAR_RANGE_ONLY",
    "NONE": "E1_YEAR_UNTESTABLE",
    "NO_PAYROLL_YEARS": "E1_YEAR_UNTESTABLE",
    "NO_OVERLAP": "E1_YEAR_CONTRADICTED",
}
D1_YEAR = {
    "OVERLAP": "D1_YEAR_CORROBORATED",
    "RANGE_OVERLAP": "D1_YEAR_CORROBORATED",
    "NONE": "D1_YEAR_UNTESTABLE",
    "NO_PAYROLL_YEARS": "D1_YEAR_UNTESTABLE",
    "NO_OVERLAP": "D1_YEAR_CONTRADICTED",
}


def year_overlap(declared: Sequence[int], payroll: Sequence[int]) -> str:
    if not declared:
        return "NONE"
    if not payroll:
        return "NO_PAYROLL_YEARS"
    if set(declared) & set(payroll):
        return "OVERLAP"
    if max(declared) >= min(payroll) and min(declared) <= max(payroll):
        return "RANGE_OVERLAP"
    return "NO_OVERLAP"


# ---------------------------------------------------------------------------
# inputs
# ---------------------------------------------------------------------------


def load_inputs(recover_root: Path, declaim_root: Path) -> dict[str, Any]:
    manifest: list[dict[str, Any]] = []
    payload: dict[str, Any] = {}
    for name, filename in RECOVER_INPUTS:
        path = recover_root / filename
        if not path.is_file():
            raise BuildError(f"required recover input missing: {path}")
        record = {"name": name, "path": str(path), "sha256": sha256_file(path),
                  "bytes": path.stat().st_size, "records": None}
        if filename.endswith(".json"):
            payload[name] = json.loads(path.read_text(encoding="utf-8"))
        elif filename.endswith(".json.gz"):
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                payload[name] = json.load(stream)
        manifest.append(record)
    for name, filename in DECLAIM_INPUTS:
        path = declaim_root / filename
        if not path.is_file():
            raise BuildError(f"required declaim input missing: {path}")
        record = {"name": name, "path": str(path), "sha256": sha256_file(path),
                  "bytes": path.stat().st_size, "records": None}
        if filename.endswith(".ndjson.gz"):
            rows = list(read_rows(path))
            record["records"] = len(rows)
            payload[name] = rows
        manifest.append(record)
    corpus_paths: dict[str, Path] = {}
    for name, parts in CORPUS_INPUTS:
        path = REPOSITORY_ROOT.joinpath(*parts)
        if not path.is_file():
            raise BuildError(f"required corpus missing: {path}")
        corpus_paths[name] = path
        manifest.append({"name": name, "path": str(path), "sha256": sha256_file(path),
                         "bytes": path.stat().st_size, "records": None})
    payload["_corpus_paths"] = corpus_paths
    payload["_manifest"] = manifest
    return payload


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------


def base_row(
    *, run_id: str, generation_id: str, target: Mapping[str, Any],
    adjudicated: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_id": ROW_SCHEMA_ID,
        "rule_version": RULE_VERSION,
        "method_version": METHOD_VERSION,
        "run_id": run_id,
        "generation_id": generation_id,
        "phase": PHASE,
        "lda_source_person_id": target["lda_source_person_id"],
        "display_name": adjudicated.get("display_name") or target.get("display_name") or "",
        "lda_priority": target.get("lda_priority"),
        "source_census_status": adjudicated["adjudicated_status"],
        "source_census_substatus": adjudicated["adjudicated_substatus"],
        "prior_resolution_status": adjudicated.get("prior_resolution_status"),
        "prior_best_tier": target.get("prior_best_tier"),
        "held_status": adjudicated.get("held_status"),
        "in_instructed_target_set": bool(adjudicated.get("in_instructed_target_set")),
        "review_status": REVIEW_STATUS,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_identity_promoted": False,
        "status_is_a_label_not_a_promotion": True,
    }


def office_provenance_of(target: Mapping[str, Any], office_key: str) -> str:
    resolved = set(target.get("candidate_office_keys_house") or []) | set(
        target.get("candidate_office_keys_senate") or [])
    if office_key in resolved:
        return "RESOLVED"
    flagged = set(target.get("flagged_candidate_office_keys_house") or []) | set(
        target.get("flagged_candidate_office_keys_senate") or [])
    if office_key in flagged:
        return "FLAGGED"
    raise BuildError(
        f"office {office_key!r} is neither a resolved nor a flagged candidate of "
        f"{target['lda_source_person_id']}"
    )


def build_rows(
    payload: Mapping[str, Any], run_id: str, generation_id: str
) -> dict[str, Any]:
    targets = {row["lda_source_person_id"]: row for row in payload["targets"]}
    adjudication = {row["lda_source_person_id"]: row for row in payload["adjudication"]}
    control = payload["control_newrules"]

    e1_source = [row for row in payload["e3_recovered"]["rows"]
                 if row["census_status"] != "D1_DECLARED_OFFICE_EXACT_UNIQUE"]
    a3_all = payload["a3_rows"]["rows"]
    a3_resolved = [row for row in a3_all
                   if row["recovered_status_resolved_offices_only"]
                   == "D1_DECLARED_OFFICE_EXACT_UNIQUE"]
    a3_held = [row for row in a3_all
               if row["recovered_status_any_provenance"] == "D1_DECLARED_OFFICE_EXACT_UNIQUE"
               and row["recovered_status_resolved_offices_only"]
               != "D1_DECLARED_OFFICE_EXACT_UNIQUE"]

    diagnostics: dict[str, Any] = {
        "cross_clause_status_counts": Counter(),
        "cross_clause_basis_counts": Counter(),
        "cross_clause_status_counts_aggressive_split": Counter(),
        "cross_clause_anchor_mention_kinds": Counter(),
        "cross_clause_clause_structure": Counter(),
        "disclaimer_status_counts": Counter(),
        "demoted_cross_clause_attachment": 0,
        "demotions": [],
        "period_review_flags": Counter(),
        "winner_office_multiplicity": Counter(),
        "year_overlap_reproduced": 0,
        "year_overlap_diverged": [],
        "payroll_years_reproduced": 0,
        "payroll_years_diverged": [],
        "unresolved_payroll_triples": [],
    }

    # ---- payroll enrichment, one pass per corpus --------------------------
    wanted: set[tuple[str, str, str]] = set()
    for row in e1_source:
        wanted.add((row["winning_scope"], row["winning_office_key"],
                    normalise_person_key(row["winning_scope"],
                                         row["winning_payroll_person_key"])))
    for rows, key in ((a3_resolved, "recovered_winner_resolved_only"),
                      (a3_held, "recovered_winner_any")):
        for row in rows:
            winner = row[key]
            wanted.add((winner["scope"], winner["office_key"],
                        normalise_person_key(winner["scope"],
                                             winner["payroll_person_key"])))
    payroll = collect_payroll(wanted, payload["_corpus_paths"])
    for triple in sorted(wanted):
        if triple not in payroll:
            diagnostics["unresolved_payroll_triples"].append(list(triple))

    # ---- the four rules' own control numbers ------------------------------
    rule_stats = {
        name: {
            "declared_unique": control["rules"][name]["declared_unique"],
            "control_unique": control["rules"][name]["control_unique"],
            "status_fpr_point_pct": control["rules"][name]["status_fpr_point_pct"],
            "status_fpr_upper95_pct": control["rules"][name]["status_fpr_upper95_pct"],
        }
        for name in SAFE_RULES
    }

    widened: list[dict[str, Any]] = []
    recovered: list[dict[str, Any]] = []
    held: list[dict[str, Any]] = []

    def finish(row: dict[str, Any], target: Mapping[str, Any], office_key: str,
               scope: str, person_key: str) -> dict[str, Any]:
        """Attach the payroll view, the clause guard and the period check."""
        view = payroll_view(scope, payroll.get((scope, office_key, person_key)))
        evidence = attachment_evidence(target, office_key)
        aggressive = attachment_evidence(target, office_key, aggressive=True)
        clauses = sorted({s["clause"] for s in evidence["supporting"] if s["clause"]})
        row.update({
            "scope": SCOPE_PUBLIC[scope],
            "source_scope": scope,
            "office_key": office_key,
            "office_provenance": office_provenance_of(target, office_key),
            "office_container_kind": view["container_kind"],
            "office_member_bioguide": view["member_bioguide"],
            "resolved_payroll_person_key": person_key,
            "payroll_payee_raw_examples": view["raw"][:6],
            "payroll_titles": view["titles"],
            "payroll_periods": view["periods"],
            "payroll_period_count": len(view["periods"]),
            "payroll_years": view["years"],
            "payroll_year_first": view["years"][0] if view["years"] else None,
            "payroll_year_last": view["years"][-1] if view["years"] else None,
            "payroll_observation_rows": view["rows"],
            "declared_office_texts": sorted({a for _k, a in evidence["anchors"]}),
            "declared_office_supporting_clauses": clauses,
            "declared_office_mention_kinds": sorted({k for k, _a in evidence["anchors"]}),
            "guard_cross_clause_attachment_status": evidence["cross_clause_status"],
            "guard_cross_clause_attachment_basis": evidence["cross_clause_basis"],
            "guard_cross_clause_attachment_status_aggressive_split":
                aggressive["cross_clause_status"],
            "guard_disclaimer_status": evidence["disclaimer_status"],
            "declaration_contains_disclaimer_clause":
                declaration_has_disclaimer_clause(target),
        })
        diagnostics["cross_clause_status_counts"][evidence["cross_clause_status"]] += 1
        diagnostics["cross_clause_basis_counts"][evidence["cross_clause_basis"]] += 1
        diagnostics["cross_clause_status_counts_aggressive_split"][
            aggressive["cross_clause_status"]] += 1
        diagnostics["disclaimer_status_counts"][evidence["disclaimer_status"]] += 1
        for kind, _anchor in evidence["anchors"]:
            diagnostics["cross_clause_anchor_mention_kinds"][kind] += 1
        distinct = sorted({" ".join(clause_tokens(c))
                           for value in (target.get("covered_position_values") or [])
                           for c in split_clauses(value) if clause_tokens(c)})
        with_cue = sum(1 for c in distinct if LEGISLATIVE_CUE.search(c))
        if len(distinct) <= 1:
            diagnostics["cross_clause_clause_structure"]["SINGLE_CLAUSE"] += 1
        elif with_cue == len(distinct):
            diagnostics["cross_clause_clause_structure"]["MULTI_CLAUSE_ALL_LEGISLATIVE"] += 1
        elif with_cue == 0:
            diagnostics["cross_clause_clause_structure"]["MULTI_CLAUSE_NONE_LEGISLATIVE"] += 1
        else:
            diagnostics["cross_clause_clause_structure"][
                "MULTI_CLAUSE_MIXED_GUARD_CAN_BITE"] += 1
        for flag in check_periods(row["payroll_periods"]):
            diagnostics["period_review_flags"][flag] += 1
        return row

    # ---- E1: the widened tier ---------------------------------------------
    for source in sorted(e1_source, key=lambda r: r["lda_source_person_id"]):
        pid = source["lda_source_person_id"]
        target = targets[pid]
        scope = source["winning_scope"]
        office_key = source["winning_office_key"]
        person_key = normalise_person_key(scope, source["winning_payroll_person_key"])
        row = base_row(run_id=run_id, generation_id=generation_id, target=target,
                       adjudicated=adjudication[pid])
        rule = source["firing_rule"]
        stats = rule_stats[rule]
        declared_years = [int(y) for y in (source["declared_years"] or [])]
        row = finish(row, target, office_key, scope, person_key)
        overlap = year_overlap(declared_years, row["payroll_years"])
        if overlap == source["year_overlap"]:
            diagnostics["year_overlap_reproduced"] += 1
        else:
            diagnostics["year_overlap_diverged"].append(
                {"lda_source_person_id": pid, "recover": source["year_overlap"],
                 "rebuilt": overlap})
        if row["payroll_years"] == list(source["payroll_years"]):
            diagnostics["payroll_years_reproduced"] += 1
        else:
            diagnostics["payroll_years_diverged"].append(
                {"lda_source_person_id": pid, "recover": source["payroll_years"],
                 "rebuilt": row["payroll_years"]})
        competing = []
        for hit in source["all_rule_hits"]:
            key = normalise_person_key(hit["scope"], hit["payroll_person_key"])
            if (hit["scope"], hit["office_key"], key) == (scope, office_key, person_key):
                continue
            competing.append({
                "source_scope": hit["scope"],
                "office_key": hit["office_key"],
                "payroll_person_key": key,
                "widening_rule": hit["rule"] if hit["rule"] in SAFE_RULES else None,
                "year_overlap_basis": hit["year_overlap"],
            })
        competing.sort(key=lambda c: (c["source_scope"], c["office_key"],
                                      c["payroll_person_key"]))
        diagnostics["winner_office_multiplicity"][1 + len(competing)] += 1
        row.update({
            "evidence_tier": E1_TIER,
            "evidence_tier_family": "LINK_BELOW_D1",
            "tier_rank_relative_to_d1": "BELOW",
            "match_class": "WIDENED_GIVEN_SURNAME_EXACT",
            "widening_rule": rule,
            "widening_rule_declared_unique_target_scope_rows": stats["declared_unique"],
            "widening_rule_control_unique_target_scope_rows": stats["control_unique"],
            "widening_rule_status_fpr_point_pct": stats["status_fpr_point_pct"],
            "widening_rule_status_fpr_upper95_pct": stats["status_fpr_upper95_pct"],
            "office_distinct_payroll_people": source["office_pool"],
            "office_contains_exact_class_person": False,
            "in_office_tie_size": 1,
            "in_office_tie_size_basis": (
                "control_newrules.py admits a declared-arm hit only when the firing "
                "rule resolves exactly one payroll person inside the declared office "
                "AND the office contains no person the target matches at the census "
                "exact class, so the widened rule is never competing with a strict "
                "match"
            ),
            "payroll_given": source["winning_payroll_given"],
            "payroll_surname": source["winning_payroll_surname"],
            "declared_years": declared_years,
            "year_strengthener": E1_YEAR[overlap],
            "year_overlap_basis": overlap,
            "winner_selected_among_multiple_offices": bool(competing),
            "competing_office_hits": competing,
            "hold_reason": None,
        })
        if row["guard_cross_clause_attachment_status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE":
            diagnostics["demoted_cross_clause_attachment"] += 1
            diagnostics["demotions"].append({
                "lda_source_person_id": pid,
                "display_name": row["display_name"],
                "from_tier": E1_TIER,
                "office_key": office_key,
                "reason": HOLD_CROSS_CLAUSE,
                "guard_status": row["guard_cross_clause_attachment_status"],
            })
            row.update({"evidence_tier": HELD_TIER, "evidence_tier_family": "HELD",
                        "tier_rank_relative_to_d1": "NOT_RANKED",
                        "hold_reason": HOLD_CROSS_CLAUSE})
            held.append(row)
        else:
            widened.append(row)

    # ---- A3: strict recoveries from offices that were never searched -------
    for source, winner_key, tier in (
            [(r, "recovered_winner_resolved_only", D1R_TIER) for r in a3_resolved]
            + [(r, "recovered_winner_any", HELD_TIER) for r in a3_held]):
        pid = source["lda_source_person_id"]
        target = targets[pid]
        winner = source[winner_key]
        scope = winner["scope"]
        office_key = winner["office_key"]
        person_key = normalise_person_key(scope, winner["payroll_person_key"])
        row = base_row(run_id=run_id, generation_id=generation_id, target=target,
                       adjudicated=adjudication[pid])
        declared_years = [int(y) for y in (source["declared_years"] or [])]
        row = finish(row, target, office_key, scope, person_key)
        overlap = year_overlap(declared_years, row["payroll_years"])
        if overlap == winner["year_overlap"]:
            diagnostics["year_overlap_reproduced"] += 1
        else:
            diagnostics["year_overlap_diverged"].append(
                {"lda_source_person_id": pid, "recover": winner["year_overlap"],
                 "rebuilt": overlap})
        parts = person_key.split("|")
        row.update({
            "evidence_tier": tier,
            "evidence_tier_family": "LINK" if tier == D1R_TIER else "HELD",
            "tier_rank_relative_to_d1": "EQUAL" if tier == D1R_TIER else "NOT_RANKED",
            "match_class": winner["match_class"],
            "widening_rule": None,
            "widening_rule_declared_unique_target_scope_rows": None,
            "widening_rule_control_unique_target_scope_rows": None,
            "widening_rule_status_fpr_point_pct": None,
            "widening_rule_status_fpr_upper95_pct": None,
            "office_distinct_payroll_people": winner["office_pool"],
            "office_contains_exact_class_person": True,
            "in_office_tie_size": winner["tie_at_class"],
            "in_office_tie_size_basis": (
                "a3_search.py reproduced the shipped matcher's own tie definition for "
                "this scope; tie_conservative (unique at ANY class) is %d"
                % winner["tie_conservative"]
            ),
            "payroll_given": (parts[1].split(":")[-1] if len(parts) > 1 else None),
            "payroll_surname": (parts[0].split(":")[-1] if parts else None),
            "declared_years": declared_years,
            "year_strengthener": D1_YEAR[overlap],
            "year_overlap_basis": overlap,
            "winner_selected_among_multiple_offices": False,
            "competing_office_hits": [],
            "hold_reason": None if tier == D1R_TIER else HOLD_FLAGGED,
        })
        if row["guard_cross_clause_attachment_status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE":
            diagnostics["demoted_cross_clause_attachment"] += 1
            diagnostics["demotions"].append({
                "lda_source_person_id": pid,
                "display_name": row["display_name"],
                "from_tier": tier,
                "office_key": office_key,
                "reason": HOLD_CROSS_CLAUSE,
                "guard_status": row["guard_cross_clause_attachment_status"],
            })
            row.update({"evidence_tier": HELD_TIER, "evidence_tier_family": "HELD",
                        "tier_rank_relative_to_d1": "NOT_RANKED",
                        "hold_reason": HOLD_CROSS_CLAUSE})
            held.append(row)
        elif tier == D1R_TIER:
            recovered.append(row)
        else:
            held.append(row)

    key = lambda r: (r["lda_source_person_id"], r["office_key"])  # noqa: E731
    widened.sort(key=key)
    recovered.sort(key=key)
    held.sort(key=lambda r: (r["hold_reason"], r["lda_source_person_id"], r["office_key"]))
    return {"widened": widened, "recovered": recovered, "held": held,
            "diagnostics": diagnostics, "rule_stats": rule_stats,
            "a3_held_source": a3_held}


def counter_to_dict(counter: Counter) -> dict[Any, int]:
    return {key: counter[key] for key in sorted(counter, key=str)}


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------


def coverage_effect(
    metric_module: Path | None, routes: Mapping[str, Sequence[str]]
) -> dict[str, Any]:
    """RCR before and after, computed from metric.py's own code, imported by path."""
    if metric_module is None:
        return {"status": "NOT_COMPUTED",
                "note": "no --metric-module supplied; coverage not recomputed"}
    if not metric_module.is_file():
        return {"status": "NOT_COMPUTED",
                "note": f"metric module not found: {metric_module}"}
    spec = importlib.util.spec_from_file_location(
        "declaration_widened_metric", metric_module)
    module = importlib.util.module_from_spec(spec)
    sys.modules["declaration_widened_metric"] = module
    spec.loader.exec_module(module)

    queue = {r["lda_source_person_id"]: r for r in module.stream(module.QUEUE)}
    reachable: set[str] = set()
    for pid, row in queue.items():
        tags: set[str] = set()
        for value in row.get("covered_position_values") or []:
            tags |= module.classify_value(value)[0]
        person_class = module.person_class(tags)
        if person_class in ("C_BLANK", "C_NONE_EXPLICIT", "C_JUNK_ONLY",
                            "C_AMBIG_NONGOV", "C_EXEC_ONLY"):
            continue
        years = []
        for token in row.get("covered_position_year_tokens") or []:
            try:
                value = int(token)
            except (TypeError, ValueError):
                continue
            if 1930 <= value <= 2026:
                years.append(value)
        if person_class == "C_LEGISLATIVE" and years and max(years) < 2009:
            continue
        reachable.add(pid)

    spine = {r["lda_source_person_id"] for r in module.stream(module.SPINE)
             if r.get("link_status") == "LINKED_BY_PAYROLL_KEY"}
    resolution = {r["lda_source_person_id"] for r in module.stream(module.RESOL)
                  if r.get("status") in ("RESOLVED_R1", "RESOLVED_R2")}
    prose = {r["lda_source_person_id"] for r in module.stream(module.A6)
             if (r.get("payroll_cross_check") or {}).get("status")
             == "CONFIRMED_BY_PAYROLL"}
    covered = spine | resolution | prose

    denominator = len(reachable)
    numerator = len(covered & reachable)
    out: dict[str, Any] = {
        "status": "COMPUTED",
        "metric_module": str(metric_module),
        "metric_module_sha256": sha256_file(metric_module),
        "reachable_denominator": denominator,
        "covered_numerator_before": numerator,
        "rcr_before_pct": round(100.0 * numerator / denominator, 4),
        "reproduces_published_reachable_6867": denominator == 6867,
        "reproduces_published_covered_3905": numerator == 3905,
        "routes": {},
    }
    for label in sorted(routes):
        added = set(routes[label])
        in_reach = added & reachable
        newly = in_reach - covered
        after = numerator + len(newly)
        out["routes"][label] = {
            "route_size": len(added),
            "inside_reachable": len(in_reach),
            "already_covered": len(in_reach & covered),
            "newly_covered": len(newly),
            "numerator_before": numerator,
            "numerator_after": after,
            "denominator": denominator,
            "rcr_before_pct": round(100.0 * numerator / denominator, 4),
            "rcr_after_pct": round(100.0 * after / denominator, 4),
            "points": round(100.0 * (after - numerator) / denominator, 4),
            "newly_covered_ids": sorted(newly),
        }
    return out


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> dict[str, Any]:
    recover_root = Path(args.recover_root).resolve()
    declaim_root = Path(args.declaim_root).resolve()
    output = Path(args.output_root).resolve()
    schema_path = (
        REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas" / ROW_SCHEMA_FILENAME
    )
    row_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    payload = load_inputs(recover_root, declaim_root)
    manifest = payload["_manifest"]
    manifest.append({"name": "row_schema", "path": str(schema_path),
                     "sha256": sha256_file(schema_path),
                     "bytes": schema_path.stat().st_size, "records": None})

    generation_id = re.sub(r"_(primary|twin)$", "", output.name)
    built = build_rows(payload, args.run_id, generation_id)
    widened = built["widened"]
    recovered = built["recovered"]
    held = built["held"]
    diagnostics = built["diagnostics"]

    for row in widened + recovered + held:
        validate_instance(row, row_schema)

    power = guard_power(
        {row["lda_source_person_id"]: row for row in payload["targets"]},
        [(row["lda_source_person_id"], row["office_key"])
         for row in widened + recovered + held],
    )

    control = payload["control_newrules"]
    per_target = payload["control_newrules_per_target"]
    pooled_declared = sum(
        1 for scopes in per_target.values()
        if any(rule in SAFE_RULES
               for entry in scopes.values() for rule in entry["declared_unique"])
    )
    pooled_control = sum(
        1 for scopes in per_target.values()
        if any(rule in SAFE_RULES
               for entry in scopes.values() for rule in entry["control_unique"])
    )
    searches = control["pooled_target_scope_rows_per_arm"]
    # The same Clopper-Pearson bound the control run used, re-expressed on the
    # declared denominator: 100 * upper_rate * searches / declared.
    upper_rate = max(control["rules"][name]["control_unique_upper95_pct"]
                     for name in SAFE_RULES) / 100.0
    pooled_upper95 = round(100.0 * upper_rate * searches / pooled_declared, 4)

    surname_present_control = sum(
        scope["control_surname_present_pairs"] for scope in control["per_scope"].values())
    surname_present_declared = sum(
        scope["declared_surname_present_pairs"] for scope in control["per_scope"].values())
    exact_control = sum(
        scope["control_exact_pairs"] for scope in control["per_scope"].values())
    exact_declared = sum(
        scope["declared_exact_pairs"] for scope in control["per_scope"].values())

    routes = {
        "E1_widened_tier_as_built": [r["lda_source_person_id"] for r in widened],
        "D1_recovered_tier_as_built": [r["lda_source_person_id"] for r in recovered],
        "both_linked_tiers_as_built": sorted(
            {r["lda_source_person_id"] for r in widened + recovered}),
        "held_for_review_not_linked": sorted(
            {r["lda_source_person_id"] for r in held}),
    }
    metric_module = Path(args.metric_module).resolve() if args.metric_module else None
    coverage = coverage_effect(metric_module, routes)
    if coverage.get("status") == "COMPUTED":
        manifest.append({"name": "metric_module", "path": coverage["metric_module"],
                         "sha256": coverage["metric_module_sha256"],
                         "bytes": Path(coverage["metric_module"]).stat().st_size,
                         "records": None})

    # ---- gates ------------------------------------------------------------
    failures: list[str] = []
    if len(widened) + diagnostics["demoted_cross_clause_attachment"] != EXPECTED_E1_ROWS:
        # a demotion moves a row out of `widened`, so the arithmetic must close
        if len(widened) != EXPECTED_E1_ROWS:
            failures.append("E1_ROW_COUNT_MISMATCH")
    if diagnostics["demoted_cross_clause_attachment"] == 0:
        if dict(Counter(r["widening_rule"] for r in widened)) != EXPECTED_E1_BY_RULE:
            failures.append("E1_RULE_SPLIT_MISMATCH")
        if dict(Counter(r["year_strengthener"] for r in widened)) != EXPECTED_E1_BY_YEAR:
            failures.append("E1_YEAR_SPLIT_MISMATCH")
        if dict(Counter(r["scope"] for r in widened)) != EXPECTED_E1_BY_SCOPE:
            failures.append("E1_SCOPE_SPLIT_MISMATCH")
        if dict(Counter(r["prior_resolution_status"] for r in widened)) != EXPECTED_E1_BY_PRIOR:
            failures.append("E1_PRIOR_STRATUM_SPLIT_MISMATCH")
        if len(recovered) != EXPECTED_RECOVERED_ROWS:
            failures.append("RECOVERED_D1_COUNT_MISMATCH")
        if len(held) != EXPECTED_HELD_ROWS:
            failures.append("HELD_COUNT_MISMATCH")
    if any(r["office_provenance"] != "RESOLVED" for r in widened):
        failures.append("E1_ROW_ON_A_FLAGGED_OFFICE")
    if any(r["office_provenance"] != "RESOLVED" for r in recovered):
        failures.append("RECOVERED_D1_ROW_ON_A_FLAGGED_OFFICE")
    if any(r["hold_reason"] == HOLD_FLAGGED and r["office_provenance"] != "FLAGGED"
           for r in held):
        failures.append("HELD_FLAGGED_ROW_IS_NOT_FLAGGED_PROVENANCE")
    if any(r["in_office_tie_size"] != 1 for r in widened + recovered):
        failures.append("LINKED_ROW_WITH_A_TIE")
    if any(r["canonical_employment_promoted"] or r["canonical_identity_promoted"]
           or r["canonical_eligible"] for r in widened + recovered + held):
        failures.append("PROMOTION_FLAG_SET")
    if any(r["guard_cross_clause_attachment_status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE"
           for r in widened + recovered):
        failures.append("LINKED_ROW_FAILED_THE_CROSS_CLAUSE_GUARD")
    if diagnostics["unresolved_payroll_triples"]:
        failures.append("PAYROLL_TRIPLE_NOT_FOUND_IN_THE_CORPORA")
    if diagnostics["payroll_years_diverged"]:
        failures.append("PAYROLL_YEARS_DO_NOT_REPRODUCE_THE_RECOVERY_LANE")
    if diagnostics["year_overlap_diverged"]:
        failures.append("YEAR_OVERLAP_DOES_NOT_REPRODUCE_THE_RECOVERY_LANE")
    if pooled_declared != EXPECTED_POOLED_DECLARED_UNIQUE_TARGETS:
        failures.append("POOLED_DECLARED_COUNT_MISMATCH")
    if pooled_control != EXPECTED_POOLED_CONTROL_UNIQUE_TARGETS:
        failures.append("POOLED_CONTROL_COUNT_MISMATCH")
    if searches != EXPECTED_CONTROL_SEARCHES_PER_ARM:
        failures.append("CONTROL_SEARCH_COUNT_MISMATCH")
    if any(control["rules"][name]["control_unique"] != 0 for name in SAFE_RULES):
        failures.append("A_CLEARED_RULE_HAS_A_CONTROL_HIT")
    if control["rules"][POSITIVE_CONTROL_RULE]["control_unique"] <= 0:
        failures.append("POSITIVE_CONTROL_DID_NOT_FIRE")
    if surname_present_control <= 0:
        failures.append("CONTROL_ARM_HAD_NO_SURNAME_PRESENT_OFFICE_PAIR")
    if power["foreign_office_key_substitution"]["rejected"] <= 0:
        failures.append("CROSS_CLAUSE_GUARD_IS_UNPOWERED")
    if coverage.get("status") == "COMPUTED" and not (
            coverage["reproduces_published_reachable_6867"]
            and coverage["reproduces_published_covered_3905"]):
        failures.append("COVERAGE_BASELINE_DOES_NOT_REPRODUCE")

    staging = prepare_output(output)
    try:
        write_ndjson(staging / WIDENED_FILENAME, widened)
        write_ndjson(staging / RECOVERED_FILENAME, recovered)
        write_ndjson(staging / HELD_FILENAME, held)

        residual = payload["residual"]
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
                "Control-cleared declaration-widened recovery tier. E1 is its OWN "
                "tier and ranks BELOW D1: the surname matched strictly and the "
                "office is self-declared, but the given name was widened by a rule "
                "whose false-positive rate was measured against a paired negative "
                "control. The 18 recovered D1 rows are strict exact-class matches "
                "on offices the census resolved but never searched. Nothing here "
                "is promoted and nothing here is an identity finding."
            ),
            "tier_definitions": {
                E1_TIER: {
                    "rank_relative_to_d1": "BELOW",
                    "why": (
                        "The surname matches at the strictest level the scope has "
                        "and the office is the filer's own declaration, but the "
                        "GIVEN NAME was widened. That is strictly weaker evidence "
                        "than D1, where surname and given name both match at the "
                        "census exact class."
                    ),
                    "emitted_to": WIDENED_FILENAME,
                    "rows": len(widened),
                },
                D1R_TIER: {
                    "rank_relative_to_d1": "EQUAL",
                    "why": (
                        "Same match class, same in-office uniqueness rule and same "
                        "declared-office requirement as the census D1 tier. The only "
                        "difference is that PHASE Search never searched these offices, "
                        "which is a coverage gap, not a weaker rule."
                    ),
                    "emitted_to": RECOVERED_FILENAME,
                    "rows": len(recovered),
                },
                HELD_TIER: {
                    "rank_relative_to_d1": "NOT_RANKED",
                    "why": (
                        "Found, preserved and visible, but deliberately not linked. "
                        "hold_reason carries which refusal applies."
                    ),
                    "emitted_to": HELD_FILENAME,
                    "rows": len(held),
                },
            },
            "inputs": sorted(manifest, key=lambda m: m["name"]),
            "counts": {
                "e1_rows": len(widened),
                "e1_by_widening_rule": counter_to_dict(
                    Counter(r["widening_rule"] for r in widened)),
                "e1_by_year_strengthener": counter_to_dict(
                    Counter(r["year_strengthener"] for r in widened)),
                "e1_by_scope": counter_to_dict(Counter(r["scope"] for r in widened)),
                "e1_by_prior_resolution_status": counter_to_dict(
                    Counter(r["prior_resolution_status"] for r in widened)),
                "e1_by_office_provenance": counter_to_dict(
                    Counter(r["office_provenance"] for r in widened)),
                "e1_in_office_tie_sizes": counter_to_dict(
                    Counter(r["in_office_tie_size"] for r in widened)),
                "e1_winner_office_multiplicity": counter_to_dict(
                    diagnostics["winner_office_multiplicity"]),
                "recovered_d1_rows": len(recovered),
                "recovered_d1_by_match_class": counter_to_dict(
                    Counter(r["match_class"] for r in recovered)),
                "recovered_d1_by_year_strengthener": counter_to_dict(
                    Counter(r["year_strengthener"] for r in recovered)),
                "recovered_d1_by_prior_resolution_status": counter_to_dict(
                    Counter(r["prior_resolution_status"] for r in recovered)),
                "held_rows": len(held),
                "held_by_reason": counter_to_dict(
                    Counter(r["hold_reason"] for r in held)),
                "held_by_prior_resolution_status": counter_to_dict(
                    Counter(r["prior_resolution_status"] for r in held)),
                "rows_total": len(widened) + len(recovered) + len(held),
            },
            "control_evidence": {
                "design": (
                    "Paired negative control. For every declared (target, office) "
                    "search the control arm ran the identical search against a "
                    "randomly drawn office the target never declared, so the two "
                    "arms have identical target-scope rows and differ only in "
                    "whether the office is the one the filer named."
                ),
                "searches_per_arm": searches,
                "pooled_four_rules": {
                    "declared_unique_targets": pooled_declared,
                    "control_unique_targets": pooled_control,
                    "status_false_positive_rate_point_pct": (
                        round(100.0 * pooled_control / pooled_declared, 4)
                        if pooled_declared else None),
                    "status_false_positive_rate_upper95_pct": pooled_upper95,
                    "basis": (
                        "%d declared-arm targets reached a unique hit under one of "
                        "the four rules; %d control-arm targets did, across %d "
                        "paired searches per arm."
                        % (pooled_declared, pooled_control, searches)
                    ),
                },
                "per_rule": {
                    name: {
                        "declared_any_target_scope_rows":
                            control["rules"][name]["declared_any"],
                        "declared_unique_target_scope_rows":
                            control["rules"][name]["declared_unique"],
                        "control_any_target_scope_rows":
                            control["rules"][name]["control_any"],
                        "control_unique_target_scope_rows":
                            control["rules"][name]["control_unique"],
                        "status_false_positive_rate_point_pct":
                            control["rules"][name]["status_fpr_point_pct"],
                        "status_false_positive_rate_upper95_pct":
                            control["rules"][name]["status_fpr_upper95_pct"],
                        "rows_built_with_this_rule": sum(
                            1 for r in widened if r["widening_rule"] == name),
                    }
                    for name in SAFE_RULES
                },
                "positive_control": {
                    "rule": POSITIVE_CONTROL_RULE,
                    "why_it_is_here": (
                        "A zero is only meaningful beside proof that the arm could "
                        "fire. Rule Z is the deliberately unsafe surname-only rule. "
                        "It was run in the SAME control arm and it fired there."
                    ),
                    "declared_any_target_scope_rows":
                        control["rules"][POSITIVE_CONTROL_RULE]["declared_any"],
                    "declared_unique_target_scope_rows":
                        control["rules"][POSITIVE_CONTROL_RULE]["declared_unique"],
                    "control_any_target_scope_rows":
                        control["rules"][POSITIVE_CONTROL_RULE]["control_any"],
                    "control_unique_target_scope_rows":
                        control["rules"][POSITIVE_CONTROL_RULE]["control_unique"],
                    "control_unique_rate_pct":
                        control["rules"][POSITIVE_CONTROL_RULE]["control_unique_rate_pct"],
                    "status_false_positive_rate_point_pct":
                        control["rules"][POSITIVE_CONTROL_RULE]["status_fpr_point_pct"],
                    "status_false_positive_rate_upper95_pct":
                        control["rules"][POSITIVE_CONTROL_RULE]["status_fpr_upper95_pct"],
                    "never_used_to_recover_anything": True,
                },
                "control_arm_capability": {
                    "why_it_is_here": (
                        "The control arm's zero would be uninformative if its offices "
                        "simply had nobody to match. They did."
                    ),
                    "control_office_pairs_with_a_strict_same_surname_person":
                        surname_present_control,
                    "declared_office_pairs_with_a_strict_same_surname_person":
                        surname_present_declared,
                    "control_office_pairs_with_an_exact_class_person": exact_control,
                    "declared_office_pairs_with_an_exact_class_person": exact_declared,
                    "by_scope": {
                        scope: {
                            "control_surname_present_pairs":
                                value["control_surname_present_pairs"],
                            "declared_surname_present_pairs":
                                value["declared_surname_present_pairs"],
                            "control_exact_pairs": value["control_exact_pairs"],
                            "declared_exact_pairs": value["declared_exact_pairs"],
                        }
                        for scope, value in sorted(control["per_scope"].items())
                    },
                },
            },
            "declared_refusals": {
                "S1_COMPOUND_SURNAME_RULE": {
                    "implemented": False,
                    "reason": (
                        "Unsafe because unpowered. The House payee_parse strips "
                        "hyphens, so GRECO-JOHNSON arrives as GRECOJOHNSON with no "
                        "token boundary and a whole-component compound rule cannot "
                        "be expressed against it on the House side."
                    ),
                    "forgone_yield_targets_ruled": S1_FORGONE_YIELD_RULED,
                    "forgone_yield_provenance": (
                        "Stated by the ruling that directed this build. It is not "
                        "reproduced here because implementing the rule is exactly "
                        "what was refused."
                    ),
                    "reproducible_bracket": {
                        "e3_targets_whose_only_surname_evidence_is_a_whole_component_"
                        "compound_match": len(payload["e3_strict"]["component_only"]),
                        "e3_unrecovered_targets_whose_primary_cause_is_S1":
                            residual["e3_unrecovered_causes"].get(
                                "S1_COMPOUND_OR_SUFFIX_SURNAME_NOT_EXPRESSIBLE"),
                        "note": (
                            "The ruled forgone yield of %d sits inside this bracket; "
                            "neither endpoint is the yield."
                            % S1_FORGONE_YIELD_RULED
                        ),
                    },
                },
                "Z_SURNAME_ONLY_ANY_GIVEN": {
                    "implemented": False,
                    "reason": (
                        "Measured at a 54.41 percent status false-positive rate in "
                        "the same control arm. It exists only as the positive "
                        "control and recovers nothing."
                    ),
                },
                "A3_FLAGGED_OFFICE_PROVENANCE": {
                    "implemented_as_links": False,
                    "reason": (
                        "build_targets.py documents the flagged surname-only office "
                        "tier as containing confirmed false office attachments "
                        "(\"Rep. Bill McCollum\" resolving to Betty McCollum). The "
                        "14 rows whose only winning office came from that tier are "
                        "preserved in %s and never linked." % HELD_FILENAME
                    ),
                    "rows_held": sum(
                        1 for r in held if r["hold_reason"] == HOLD_FLAGGED),
                },
            },
            "guards": {
                "cross_clause_attachment": {
                    "reason_code": HOLD_CROSS_CLAUSE,
                    "escalated_as": "ADJUDICATION.md defect 4",
                    "definition": (
                        "A row survives only when at least one clause of the filer's "
                        "own covered-position text both contains the anchor that "
                        "attached the winning office key (the member name for a "
                        "MEMBER mention, the matched alias for a COMMITTEE mention) "
                        "and contains a legislative cue. An anchor that cannot be "
                        "located in any clause is treated as a failure, which is the "
                        "fail-closed reading."
                    ),
                    "clause_boundaries": "; newline [ ]",
                    "rows_audited": len(widened) + len(recovered) + len(held),
                    "demoted": diagnostics["demoted_cross_clause_attachment"],
                    "status_counts": counter_to_dict(
                        diagnostics["cross_clause_status_counts"]),
                    "location_basis_counts": counter_to_dict(
                        diagnostics["cross_clause_basis_counts"]),
                    "anchor_mention_kinds": counter_to_dict(
                        diagnostics["cross_clause_anchor_mention_kinds"]),
                    "declaration_clause_structure": counter_to_dict(
                        diagnostics["cross_clause_clause_structure"]),
                    "sensitivity_aggressive_clause_split": {
                        "clause_boundaries": "; newline [ ] / |",
                        "status_counts": counter_to_dict(
                            diagnostics["cross_clause_status_counts_aggressive_split"]),
                        "applied": False,
                    },
                    "power": power,
                },
                "declaration_is_a_disclaimer": {
                    "demotes": False,
                    "definition": (
                        "A supporting clause is a disclaimer when its leading token "
                        "is a negation and it then names the office anchor. Reported "
                        "as a field on every row; this build demotes nobody for it."
                    ),
                    "status_counts": counter_to_dict(
                        diagnostics["disclaimer_status_counts"]),
                    "rows_whose_declaration_contains_a_disclaimer_clause": sum(
                        1 for r in widened + recovered + held
                        if r["declaration_contains_disclaimer_clause"]),
                },
                "demotions": sorted(diagnostics["demotions"],
                                    key=lambda d: d["lda_source_person_id"]),
            },
            "reproduction": {
                "payroll_years_rebuilt_from_the_corpora_and_matching_the_recovery_lane":
                    diagnostics["payroll_years_reproduced"],
                "payroll_years_diverged": diagnostics["payroll_years_diverged"],
                "year_overlap_rebuilt_and_matching_the_recovery_lane":
                    diagnostics["year_overlap_reproduced"],
                "year_overlap_diverged": diagnostics["year_overlap_diverged"],
                "payroll_triples_wanted": len(widened) + len(recovered) + len(held),
                "payroll_triples_unresolved_in_the_corpora":
                    diagnostics["unresolved_payroll_triples"],
                "note": (
                    "Titles, periods and years on every row are read straight from "
                    "the House SOD observations, the House office spans and the "
                    "Senate candidates file, not from the recovery lane's indexes, "
                    "so the lane's own year arithmetic is re-derived rather than "
                    "trusted."
                ),
            },
            "coverage_effect": coverage,
            "period_review_flags": counter_to_dict(diagnostics["period_review_flags"]),
            "promotion_policy": PROMOTION_POLICY,
            "canonical_identity_promotions": 0,
            "canonical_employment_promotions": 0,
            "review_status": REVIEW_STATUS,
            "files": [],
            "implementation": {
                "path": Path(__file__).name,
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "failures": failures,
        }
        files = []
        for filename, rows in ((WIDENED_FILENAME, widened),
                               (RECOVERED_FILENAME, recovered),
                               (HELD_FILENAME, held)):
            path = staging / filename
            files.append({"name": filename, "records": len(rows),
                          "bytes": path.stat().st_size, "sha256": sha256_file(path)})
        receipt["files"] = files
        (staging / RECEIPT_FILENAME).write_bytes(canonical_json_bytes(receipt))
        os.replace(staging, output)
        return receipt
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the control-cleared declaration-widened recovery tier."
    )
    parser.add_argument("--recover-root", required=True)
    parser.add_argument("--declaim-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--metric-module", default="")
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox, kind="run.start", status="running",
        summary="declaration-widened E1 recovery tier build",
        detail=str(args.output_root), run_id=args.run_id, stage=PHASE,
    )
    try:
        receipt = run(args)
    except BaseException as error:
        emit_glassbox(
            enabled=glassbox, kind="run.finish", status="failed",
            summary="declaration-widened E1 recovery tier build failed",
            detail=f"{type(error).__name__}: {error}", run_id=args.run_id, stage=PHASE,
        )
        raise
    emit_glassbox(
        enabled=glassbox, kind="run.finish",
        status="completed" if receipt["status"] == "PASS" else "failed",
        summary=(
            "declaration-widened tier %s: %d E1, %d recovered D1, %d held"
            % (receipt["status"], receipt["counts"]["e1_rows"],
               receipt["counts"]["recovered_d1_rows"], receipt["counts"]["held_rows"])
        ),
        detail=str(args.output_root), run_id=args.run_id, stage=PHASE,
    )
    print(json.dumps({
        "status": receipt["status"],
        "counts": receipt["counts"],
        "cross_clause": receipt["guards"]["cross_clause_attachment"]["status_counts"],
        "demoted": receipt["guards"]["cross_clause_attachment"]["demoted"],
        "failures": receipt["failures"],
        "files": receipt["files"],
    }, indent=1, sort_keys=True))
    return 1 if receipt["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
