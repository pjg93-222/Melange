#!/usr/bin/env python3
r"""Independently verify the declaration-directed employment tier generation.

This script never imports ``build_declaration_directed_tier``.  It reads the
emitted receipt, re-binds every declared input by hash, and then re-derives
100 percent of the emitted rows -- every field of every row in all three files
-- straight from the adjudication and the three search corpora, using its own
clause-anchoring, disclaimer and alias-stripping implementations.  It then:

* checks that the pinned adjudication sha256 is the one that was consumed;
* checks the emitted rows against the committed row schema;
* checks primary and twin are byte-identical file by file;
* checks that no row is promoted, no row is canonical-eligible, no row carries
  a canonical identity decision other than ``NOT_ADJUDICATED``, and no
  FIRST_INITIAL row appears in the link or candidate file;
* checks the receipt's own counters against the rows on disk, including the
  two promotion counters, which must both be 0;
* re-measures the guard demotion counts and the middle-initial repair from
  scratch and compares them with the receipt.

It writes its own receipt and exits 1 on FAIL.  The verification receipt has
no committed JSON schema: the task authorises exactly one new committed schema
and that is the row schema.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Iterator, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
)

ROW_SCHEMA_ID = "staffer-network-declaration-directed-employment-link-v1"
ROW_SCHEMA_FILENAME = "declaration_directed_employment_link.schema.json"
RULE_VERSION = "declaration-directed-employment-tier-v1"
PHASE = "build-declaration-directed-tier"
ADJUDICATION_SHA256 = (
    "b6f122658d1e5928beff1602d69473ff9407ea664caf1326fb0f07cb7e65dde2"
)

LINKS_FILENAME = "declaration_directed_employment_links.ndjson.gz"
CANDIDATES_FILENAME = "declaration_directed_candidates.ndjson.gz"
NON_EVIDENTIAL_FILENAME = "declaration_directed_non_evidential.ndjson.gz"
RECEIPT_FILENAME = "declaration_directed_tier_receipt.json"
VERIFICATION_FILENAME = "declaration_directed_tier_verification_receipt.json"

DATA_FILENAMES = (LINKS_FILENAME, CANDIDATES_FILENAME, NON_EVIDENTIAL_FILENAME)

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

STOPWORDS = frozenset({"AND", "THE", "OF"})
CUE_WORDS = frozenset(
    "REP REPS REPRESENTATIVE REPRESENTATIVES CONGRESSMAN CONGRESSWOMAN "
    "CONGRESSMEMBER CONGRESSMEN CONGRESSWOMEN CONG CONGR SEN SENS SENATOR "
    "SENATORS SENATE HOUSE CONGRESS CONGRESSIONAL COMMITTEE COMMITTEES "
    "SUBCOMMITTEE SUBCOMMITTEES CMTE CAUCUS CAPITOL HILL SPEAKER WHIP "
    "DELEGATE LEADERSHIP CLOAKROOM PARLIAMENTARIAN MAJORITY MINORITY LEADER "
    "CHAIRMAN CHAIRWOMAN RANKING MEMBER".split()
)
NEGATIONS = frozenset({"NO", "NOT", "NONE", "NEVER"})
HONORIFICS = frozenset(
    "MR MRS MS MISS DR PROF HON HONORABLE REP REPRESENTATIVE SEN SENATOR THE "
    "SIR RT REV CAPT COL GEN MAJ LT SGT ADM AMB".split()
)
SUFFIXES = frozenset(
    "JR SR II III IV V VI ESQ PHD MD JD DDS DVM MBA CPA RET USA USN USAF "
    "USMC".split()
)
QUARTER_START = {"Q1": (1, 1), "Q2": (4, 1), "Q3": (7, 1), "Q4": (10, 1)}
QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}


class VerifyError(RuntimeError):
    pass


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
        for line in stream:
            if line.strip():
                yield json.loads(line)


# ---------------------------------------------------------------------------
# independent clause / anchor implementation
# ---------------------------------------------------------------------------


def tokenise(text: str | None) -> list[str]:
    upper = (text or "").upper().replace("&", " AND ")
    out: list[str] = []
    buffer: list[str] = []
    for character in upper:
        if character.isalnum():
            buffer.append(character)
        elif buffer:
            out.append("".join(buffer))
            buffer = []
    if buffer:
        out.append("".join(buffer))
    return [token for token in out if token not in STOPWORDS]


def cut_clauses(value: str | None, aggressive: bool = False) -> list[str]:
    boundaries = set(";\n[]")
    if aggressive:
        boundaries |= set("/|")
    parts: list[str] = []
    current: list[str] = []
    for character in value or "":
        if character in boundaries:
            parts.append("".join(current))
            current = []
        else:
            current.append(character)
    parts.append("".join(current))
    return [part for part in parts if part.strip()]


def locate(anchor: Sequence[str], clause: Sequence[str]) -> str | None:
    """Return the location basis, or None when the anchor is not in the clause."""
    if not anchor:
        return None
    needle = "\x00" + "\x00".join(anchor) + "\x00"
    haystack = "\x00" + "\x00".join(clause) + "\x00"
    if needle in haystack:
        return "CONTIGUOUS"
    position = 0
    for want in anchor:
        while position < len(clause) and clause[position] != want:
            position += 1
        if position >= len(clause):
            return None
        position += 1
    return "ORDERED_SUBSEQUENCE"


def anchors_of(target: Mapping[str, Any], office_key: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for mention in target.get("declared_office_mentions") or []:
        if office_key not in (mention.get("office_keys") or []):
            continue
        kind = mention.get("kind") or "UNKNOWN"
        alias = mention.get("alias_hit")
        if kind == "COMMITTEE" and alias:
            found.append((kind, str(alias)))
        elif mention.get("text"):
            found.append((kind, str(mention["text"])))
    return found


def grade_attachment(
    target: Mapping[str, Any], office_key: str, aggressive: bool = False
) -> dict[str, Any]:
    anchors = anchors_of(target, office_key)
    supporting: list[dict[str, Any]] = []
    for kind, anchor in anchors:
        anchor_tokens = tokenise(anchor)
        if not anchor_tokens:
            continue
        for value in target.get("covered_position_values") or []:
            for clause in cut_clauses(value, aggressive=aggressive):
                clause_tokens = tokenise(clause)
                basis = locate(anchor_tokens, clause_tokens)
                if basis is None:
                    continue
                supporting.append({
                    "clause": clause.strip(),
                    "basis": basis,
                    "cue": bool(set(clause_tokens) & CUE_WORDS),
                    "negation": bool(clause_tokens) and clause_tokens[0] in NEGATIONS,
                })
    if not supporting:
        return {
            "anchors": anchors, "supporting": supporting,
            "cross_clause_status": "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE",
            "cross_clause_basis": "NONE",
            "disclaimer_status": "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT",
        }
    cued = [item for item in supporting if item["cue"]]
    pool = cued or supporting
    basis = "CONTIGUOUS" if any(i["basis"] == "CONTIGUOUS" for i in pool) else (
        "ORDERED_SUBSEQUENCE"
    )
    negations = sum(1 for item in supporting if item["negation"])
    if negations == 0:
        disclaimer = "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT"
    elif negations == len(supporting):
        disclaimer = "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"
    else:
        disclaimer = "SOME_SUPPORTING_CLAUSES_ARE_DISCLAIMERS"
    return {
        "anchors": anchors,
        "supporting": supporting,
        "cross_clause_status": (
            "CLAUSE_CARRIES_LEGISLATIVE_CUE" if cued
            else "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
        ),
        "cross_clause_basis": basis,
        "disclaimer_status": disclaimer,
    }


def has_disclaimer_clause(target: Mapping[str, Any]) -> bool:
    for value in target.get("covered_position_values") or []:
        for clause in cut_clauses(value):
            tokens = tokenise(clause)
            if tokens and tokens[0] in NEGATIONS and (set(tokens) & CUE_WORDS):
                return True
    return False


def year_tokens_only_in_disclaimers(target: Mapping[str, Any]) -> bool:
    declared = {str(t) for t in (target.get("covered_position_year_tokens") or [])}
    if not declared:
        return False
    inside: set[str] = set()
    outside: set[str] = set()
    for value in target.get("covered_position_values") or []:
        for clause in cut_clauses(value):
            tokens = tokenise(clause)
            present = declared & set(tokens)
            if tokens and tokens[0] in NEGATIONS:
                inside |= present
            else:
                outside |= present
    return bool(inside) and not (declared - inside) and not (outside & inside)


# ---------------------------------------------------------------------------
# independent alias stripping
# ---------------------------------------------------------------------------


class Aliases:
    def __init__(self, entries: Mapping[str, Sequence[str]]):
        self.single = {
            key.upper(): str(value[0]).upper()
            for key, value in entries.items() if len(value) == 1
        }

    def canon(self, given: str) -> str:
        return self.single.get(given, given)

    def embedded(self, given: str, token: str) -> bool:
        if not given or not token or token == given:
            return False
        if self.canon(token) == self.canon(given):
            return True
        if len(token) > 2 and (token[: len(given)] == given or given[: len(token)] == token):
            return True
        if len(token) == 1 and token == given[:1]:
            return True
        return False


def name_tokens(display_name: str | None) -> list[str]:
    text = (display_name or "").upper()
    tokens = [
        token for token in re.split(r"[^A-Z'-]+", text) if token and token != "-"
    ]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    while len(tokens) > 2 and tokens[0] in HONORIFICS:
        tokens = tokens[1:]
    return tokens


def middle_initials(display_name: str | None, aliases: Aliases) -> dict[str, Any]:
    tokens = name_tokens(display_name)
    if len(tokens) < 2:
        return {"raw": None, "repaired": None, "stripped": []}
    given = tokens[0]
    middles = tokens[1:-1]
    stripped = [token for token in middles if aliases.embedded(given, token)]
    retained = [token for token in middles if token not in stripped]
    return {
        "raw": middles[0][0] if middles else "",
        "repaired": retained[0][0] if retained else "",
        "stripped": stripped,
    }


# ---------------------------------------------------------------------------
# independent hit normalisation
# ---------------------------------------------------------------------------


def quarter_edge(quarter: str, end: bool) -> str | None:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", quarter or "")
    if not match:
        return None
    month, day = (QUARTER_END if end else QUARTER_START)[match.group(2)]
    return date(int(match.group(1)), month, day).isoformat()


def periods_of(hit: Mapping[str, Any], scope: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    if scope == "senate_all":
        for period in hit.get("payroll_periods") or []:
            if period.get("start") and period.get("end"):
                collected.append({
                    "start": period["start"], "end": period["end"],
                    "basis": "SENATE_REPORT_PERIOD",
                })
    elif scope == "house_nonmember":
        for span in hit.get("payroll_spans") or []:
            if span.get("service_start_min") and span.get("service_end_max"):
                collected.append({
                    "start": span["service_start_min"],
                    "end": span["service_end_max"],
                    "basis": "HOUSE_SOD_SERVICE_SPAN",
                })
    else:
        if hit.get("payroll_service_start_min") and hit.get("payroll_service_end_max"):
            collected.append({
                "start": hit["payroll_service_start_min"],
                "end": hit["payroll_service_end_max"],
                "basis": "HOUSE_SOD_SERVICE_SPAN",
            })
    if not collected and scope != "senate_all":
        quarters = sorted(hit.get("payroll_quarters") or [])
        if quarters:
            collected.append({
                "start": quarter_edge(quarters[0], end=False),
                "end": quarter_edge(quarters[-1], end=True),
                "basis": "HOUSE_SOD_QUARTER_ENVELOPE",
            })
    seen: dict[tuple, dict[str, Any]] = {}
    for period in collected:
        seen[(period["start"], period["end"], period["basis"])] = period
    return [seen[key] for key in sorted(seen)]


def payroll_mi(hit: Mapping[str, Any], scope: str) -> str:
    if scope == "senate_all":
        parts = str(hit.get("payroll_person_key") or "").split("|")
        return parts[-1] if len(parts) >= 5 else ""
    if hit.get("payroll_middle_initial"):
        return str(hit["payroll_middle_initial"])
    return str((hit.get("match_detail") or {}).get("payroll_middle_initial") or "")


def mi_conflict(hit: Mapping[str, Any], scope: str) -> bool:
    if scope == "house_member":
        return bool(hit.get("middle_initial_conflict"))
    return (hit.get("match_detail") or {}).get("middle_initial_status") == "CONFLICT"


def container_kind(hit: Mapping[str, Any], scope: str) -> str | None:
    if scope == "house_member":
        kinds = hit.get("office_container_kinds") or []
        return str(kinds[0]) if kinds else None
    key = "office_container_kind" if scope == "house_nonmember" else (
        "office_container_kind_derived"
    )
    return str(hit[key]) if hit.get(key) else None


def bioguide(hit: Mapping[str, Any], scope: str) -> str | None:
    key = "office_member_bioguide" if scope == "house_member" else (
        "payroll_member_bioguide"
    )
    return str(hit[key]) if hit.get(key) else None


TIE_FIELD = {
    "house_member": "in_office_tie_size_at_row_class",
    "house_nonmember": "in_office_tie_size_at_class",
    "senate_all": "in_office_tie_size",
}


def tie_at_class(hit: Mapping[str, Any], scope: str) -> int | None:
    return hit.get(TIE_FIELD[scope])


def payroll_years(hit: Mapping[str, Any], scope: str) -> tuple[Any, Any]:
    if scope == "house_member":
        return hit.get("payroll_year_first"), hit.get("payroll_year_last")
    if scope == "house_nonmember":
        years = sorted(hit.get("payroll_years") or [])
        return (years[0], years[-1]) if years else (None, None)
    return hit.get("payroll_first_year"), hit.get("payroll_last_year")


# ---------------------------------------------------------------------------
# re-derivation
# ---------------------------------------------------------------------------


def rederive(
    declaim_root: Path, aliases: Aliases, run_id: str, generation_id: str
) -> dict[str, Any]:
    adjudication = list(read_rows(declaim_root / "adjudication.ndjson.gz"))
    targets = {r["lda_source_person_id"]: r for r in
               read_rows(declaim_root / "targets.ndjson.gz")}
    control = json.loads(
        (declaim_root / "control_report.json").read_text(encoding="utf-8")
    )["by_match_class"]
    hits: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for filename, scope in (
        ("hits_house_member.ndjson.gz", "house_member"),
        ("hits_house_nonmember.ndjson.gz", "house_nonmember"),
        ("hits_senate_all.ndjson.gz", "senate_all"),
    ):
        for row in read_rows(declaim_root / filename):
            row = dict(row)
            row["_scope"] = scope
            hits[row["lda_source_person_id"]].append(row)

    rows: dict[str, list[dict[str, Any]]] = {
        "links": [], "candidates": [], "non_evidential": []
    }
    measured = {
        "d1_before_guards": 0,
        "demoted_cross_clause_attachment": 0,
        "demoted_declaration_is_a_disclaimer": 0,
        "mi_conflicts_original": Counter(),
        "mi_conflicts_after_alias_strip": Counter(),
        "cross_clause_status_counts": Counter(),
        "disclaimer_status_counts": Counter(),
    }

    for adjudicated in sorted(adjudication, key=lambda r: r["lda_source_person_id"]):
        status = adjudicated["adjudicated_status"]
        substatus = adjudicated["adjudicated_substatus"]
        is_d4a = status == "D4_NO_HIT" and substatus == "D4a_NON_EVIDENTIAL_HIT_ONLY"
        if status not in STATUS_TO_TIER and not is_d4a:
            continue
        person_id = adjudicated["lda_source_person_id"]
        target = targets[person_id]
        scope = adjudicated["winning_scope"]
        office_key = adjudicated["winning_office_key"]
        match_class = adjudicated["winning_match_class"]
        payroll_key = adjudicated["winning_payroll_person_key"]

        pool = [
            hit for hit in hits[person_id]
            if hit["_scope"] == scope and hit["office_key"] == office_key
            and hit["payroll_person_key"] == payroll_key
            and hit["match_class"] == match_class
        ]
        if not pool:
            raise VerifyError(f"winner hit absent for {person_id}")
        pool.sort(key=lambda h: canonical_json_bytes(
            {k: v for k, v in h.items() if not k.startswith("_")}
        ))
        winner = pool[0]
        # every payroll person this target matched inside the winning office,
        # at any match class -- see the builder's note on understated contention
        tied = sorted({
            hit["payroll_person_key"] for hit in hits[person_id]
            if hit["_scope"] == scope and hit["office_key"] == office_key
        })

        grade = grade_attachment(target, office_key)
        mi = middle_initials(adjudicated["display_name"], aliases)
        pmi = payroll_mi(winner, scope)
        conflict_original = mi_conflict(winner, scope)
        conflict_repaired = bool(mi["repaired"] and pmi and mi["repaired"] != pmi)

        reason = None
        if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE":
            measured["d1_before_guards"] += 1
            measured["cross_clause_status_counts"][grade["cross_clause_status"]] += 1
            measured["disclaimer_status_counts"][grade["disclaimer_status"]] += 1
            if grade["cross_clause_status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE":
                reason = "CROSS_CLAUSE_ATTACHMENT"
                measured["demoted_cross_clause_attachment"] += 1
            elif grade["disclaimer_status"] == (
                "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"
            ):
                reason = "DECLARATION_IS_A_DISCLAIMER"
                measured["demoted_declaration_is_a_disclaimer"] += 1
            if conflict_original:
                measured["mi_conflicts_original"][SCOPE_PUBLIC[scope]] += 1
                if conflict_repaired:
                    measured["mi_conflicts_after_alias_strip"][
                        SCOPE_PUBLIC[scope]
                    ] += 1

        if is_d4a:
            tier = "NON_EVIDENTIAL_HIT_ONLY"
        elif reason is not None:
            tier = "D1_DEMOTED_CANDIDATE"
        else:
            tier = STATUS_TO_TIER[status]
        is_link = tier == "D1_DECLARED_OFFICE_EXACT_UNIQUE"
        resolved = tier in {"D1_DECLARED_OFFICE_EXACT_UNIQUE", "D3_CANDIDATE"}
        periods = periods_of(winner, scope) if resolved else []
        year_first, year_last = payroll_years(winner, scope) if resolved else (
            None, None
        )
        class_control = control.get(match_class, {})
        disclaimer_anywhere = has_disclaimer_clause(target)

        row = {
            "schema_id": ROW_SCHEMA_ID,
            "rule_version": RULE_VERSION,
            "method_version": RULE_VERSION,
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
            "scope": SCOPE_PUBLIC[scope],
            "source_scope": scope,
            "declared_office_texts": sorted({a for _, a in grade["anchors"]}),
            "declared_office_supporting_clauses": sorted({
                item["clause"] for item in grade["supporting"] if item["clause"]
            }),
            "declared_office_mention_kinds": sorted({k for k, _ in grade["anchors"]}),
            "office_key": office_key,
            "office_container_kind": container_kind(winner, scope),
            "office_member_bioguide": bioguide(winner, scope),
            "office_distinct_payroll_people": winner.get(
                "office_distinct_payroll_people"
            ),
            "resolved_payroll_person_key": payroll_key if resolved else None,
            "candidate_payroll_person_keys": [] if resolved else tied,
            "payroll_titles": sorted({
                str(t) for t in (winner.get("payroll_titles") or [])
            }) if resolved else [],
            "payroll_periods": periods,
            "payroll_period_count": len(periods),
            "payroll_year_first": year_first,
            "payroll_year_last": year_last,
            "in_office_tie_size": adjudicated["winning_tie_at_class"],
            "in_office_tie_size_conservative": adjudicated["winning_tie_conservative"],
            "year_strengthener": substatus if is_link else None,
            "d3_strengthened": (
                substatus == "D3_STRENGTHENED_CLASS_EVIDENTIAL_AND_YEARS_OVERLAP"
                if tier == "D3_CANDIDATE" else None
            ),
            "demotion_reason": reason,
            "guard_cross_clause_attachment_status": (
                grade["cross_clause_status"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NOT_APPLICABLE"
            ),
            "guard_cross_clause_attachment_basis": (
                grade["cross_clause_basis"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NONE"
            ),
            "guard_disclaimer_status": (
                grade["disclaimer_status"]
                if status == "D1_DECLARED_OFFICE_EXACT_UNIQUE" else "NOT_APPLICABLE"
            ),
            "declaration_contains_disclaimer_clause": disclaimer_anywhere,
            "year_strengthener_disclaimer_caveat": bool(
                disclaimer_anywhere and year_tokens_only_in_disclaimers(target)
            ),
            "middle_initial_target_raw": mi["raw"],
            "middle_initial_target_after_alias_strip": mi["repaired"],
            "middle_initial_payroll": pmi,
            "middle_initial_conflict_original": conflict_original,
            "middle_initial_conflict_after_alias_strip": conflict_repaired,
            "middle_initial_alias_tokens_stripped": mi["stripped"],
            "held_status": adjudicated.get("held_status"),
            "prior_resolution_status": adjudicated.get("prior_resolution_status"),
            "prior_best_tier": adjudicated.get("prior_best_tier"),
            "in_instructed_target_set": bool(
                adjudicated.get("in_instructed_target_set")
            ),
            "review_status": "REVIEW_REQUIRED",
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
            "canonical_identity_decision": "NOT_ADJUDICATED",
            "canonical_identity_promoted": False,
            "status_is_a_label_not_a_promotion": True,
        }
        if tier == "NON_EVIDENTIAL_HIT_ONLY":
            rows["non_evidential"].append(row)
        elif is_link:
            rows["links"].append(row)
        else:
            rows["candidates"].append(row)

    # Independent re-derivation of the tie size straight from the hit corpora.
    # Only rows with an unambiguous resolved payroll person can be checked this
    # way: for an ambiguous candidate there is no single hit row to read the
    # at-class tie size off.
    for bucket in rows.values():
        for row in bucket:
            resolved_key = row["resolved_payroll_person_key"]
            if not resolved_key:
                continue
            scope = row["source_scope"]
            same = [
                hit for hit in hits[row["lda_source_person_id"]]
                if hit["_scope"] == scope and hit["office_key"] == row["office_key"]
                and hit["payroll_person_key"] == resolved_key
                and hit["match_class"] == row["match_class"]
            ]
            if same and tie_at_class(same[0], scope) != row["in_office_tie_size"]:
                raise VerifyError(
                    f"tie size disagreement for {row['lda_source_person_id']}"
                )
    return {"rows": rows, "measured": measured}


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------


def compare_rows(
    label: str, emitted: Sequence[Mapping[str, Any]],
    expected: Sequence[Mapping[str, Any]], failures: list[str],
    details: list[dict[str, Any]],
) -> None:
    emitted_index = {row["lda_source_person_id"]: row for row in emitted}
    expected_index = {row["lda_source_person_id"]: row for row in expected}
    if len(emitted_index) != len(emitted):
        failures.append(f"{label}_DUPLICATE_PERSON_ID")
    missing = sorted(set(expected_index) - set(emitted_index))
    extra = sorted(set(emitted_index) - set(expected_index))
    if missing:
        failures.append(f"{label}_MISSING_ROWS")
        details.append({"file": label, "missing": missing[:20],
                        "missing_total": len(missing)})
    if extra:
        failures.append(f"{label}_UNEXPECTED_ROWS")
        details.append({"file": label, "unexpected": extra[:20],
                        "unexpected_total": len(extra)})
    mismatched: list[dict[str, Any]] = []
    for person_id in sorted(set(emitted_index) & set(expected_index)):
        left = emitted_index[person_id]
        right = expected_index[person_id]
        diff = sorted(
            key for key in set(left) | set(right) if left.get(key) != right.get(key)
        )
        if diff:
            mismatched.append({
                "lda_source_person_id": person_id,
                "fields": diff[:10],
                "emitted": {k: left.get(k) for k in diff[:5]},
                "rederived": {k: right.get(k) for k in diff[:5]},
            })
    if mismatched:
        failures.append(f"{label}_FIELD_MISMATCH")
        details.append({"file": label, "mismatched_total": len(mismatched),
                        "examples": mismatched[:10]})


def run(args: argparse.Namespace) -> dict[str, Any]:
    primary = Path(args.primary_root).resolve()
    twin = Path(args.twin_root).resolve() if args.twin_root else None
    output = Path(args.output_root).resolve()
    declaim_root = Path(args.declaim_root).resolve()

    failures: list[str] = []
    details: list[dict[str, Any]] = []

    receipt = json.loads(
        (primary / RECEIPT_FILENAME).read_text(encoding="utf-8")
    )
    if receipt.get("status") != "PASS":
        failures.append("BUILD_RECEIPT_NOT_PASS")
    if receipt.get("failures"):
        failures.append("BUILD_RECEIPT_CARRIES_FAILURES")
    if receipt.get("canonical_identity_promotions") != 0:
        failures.append("IDENTITY_PROMOTION_COUNTER_NONZERO")
    if receipt.get("canonical_employment_promotions") != 0:
        failures.append("EMPLOYMENT_PROMOTION_COUNTER_NONZERO")

    # ---- 1. rebind every declared input by hash --------------------------
    input_checks = []
    for record in receipt.get("inputs", []):
        path = Path(record["path"])
        present = path.is_file()
        actual = sha256_file(path) if present else None
        ok = present and actual == record["sha256"]
        input_checks.append({
            "name": record["name"], "path": str(path), "present": present,
            "declared_sha256": record["sha256"], "actual_sha256": actual,
            "match": ok,
        })
        if not ok:
            failures.append("INPUT_HASH_MISMATCH")
    directed = receipt.get("directed_by", {})
    if directed.get("adjudication_sha256_expected") != ADJUDICATION_SHA256:
        failures.append("ADJUDICATION_PIN_WRONG")
    if directed.get("adjudication_sha256_actual") != ADJUDICATION_SHA256:
        failures.append("ADJUDICATION_CONSUMED_WRONG_FILE")
    adjudication_on_disk = sha256_file(declaim_root / "adjudication.ndjson.gz")
    if adjudication_on_disk != ADJUDICATION_SHA256:
        failures.append("ADJUDICATION_ON_DISK_DOES_NOT_MATCH_PIN")

    # ---- 2. schema ------------------------------------------------------
    schema_path = (
        REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas" / ROW_SCHEMA_FILENAME
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    emitted: dict[str, list[dict[str, Any]]] = {}
    schema_errors: list[str] = []
    for label, filename in (
        ("links", LINKS_FILENAME), ("candidates", CANDIDATES_FILENAME),
        ("non_evidential", NON_EVIDENTIAL_FILENAME),
    ):
        rows = list(read_rows(primary / filename))
        emitted[label] = rows
        for row in rows:
            try:
                validate_instance(row, schema)
            except SchemaValidationError as error:
                schema_errors.append(f"{filename}:{row.get('lda_source_person_id')}: {error}")
    if schema_errors:
        failures.append("SCHEMA_VALIDATION_FAILED")
        details.append({"schema_errors": schema_errors[:10],
                        "schema_errors_total": len(schema_errors)})

    # ---- 3. re-derive every row from the adjudication + corpora ----------
    nickname_path = Path(args.nickname_file).resolve()
    aliases = Aliases(
        json.loads(nickname_path.read_text(encoding="utf-8"))["entries"]
    )
    run_id = receipt.get("run_id", "")
    generation_id = receipt.get("generation_id", primary.name)
    rederived = rederive(declaim_root, aliases, run_id, generation_id)
    for label in ("links", "candidates", "non_evidential"):
        compare_rows(label, emitted[label], rederived["rows"][label], failures, details)

    # ---- 4. refusals are structural -------------------------------------
    for label in ("links", "candidates", "non_evidential"):
        for row in emitted[label]:
            if row["canonical_eligible"] is not False:
                failures.append("CANONICAL_ELIGIBLE_TRUE")
            if row["canonical_employment_promoted"] is not False:
                failures.append("EMPLOYMENT_PROMOTED_TRUE")
            if row["canonical_identity_promoted"] is not False:
                failures.append("IDENTITY_PROMOTED_TRUE")
            if row["canonical_identity_decision"] != "NOT_ADJUDICATED":
                failures.append("IDENTITY_DECISION_NOT_NOT_ADJUDICATED")
            if row["review_status"] != "REVIEW_REQUIRED":
                failures.append("REVIEW_STATUS_NOT_REVIEW_REQUIRED")
    if any(row["match_class"] == "FIRST_INITIAL"
           for row in emitted["links"] + emitted["candidates"]):
        failures.append("FIRST_INITIAL_OUTSIDE_NON_EVIDENTIAL_FILE")
    if any(row["evidence_tier_family"] == "LINK" for row in emitted["candidates"]):
        failures.append("LINK_FAMILY_ROW_IN_CANDIDATE_FILE")
    if any(row["evidence_tier_family"] != "LINK" for row in emitted["links"]):
        failures.append("NON_LINK_FAMILY_ROW_IN_LINK_FILE")
    if any(row["in_office_tie_size"] != 1 for row in emitted["links"]):
        failures.append("LINK_WITH_TIE_SIZE_ABOVE_ONE")
    if any(row["resolved_payroll_person_key"] for row in emitted["candidates"]
           if row["evidence_tier"] in {"D2_CANDIDATE", "D3M_CANDIDATE"}):
        failures.append("D2_OR_D3M_RESOLVED")
    if any(row["resolved_payroll_person_key"] for row in emitted["non_evidential"]):
        failures.append("NON_EVIDENTIAL_RESOLVED")

    # ---- 5. receipt counters vs the rows on disk -------------------------
    counts = receipt.get("counts", {})
    recomputed = {
        "d1_after_guards": len(emitted["links"]),
        "candidates_total": len(emitted["candidates"]),
        "non_evidential_total": len(emitted["non_evidential"]),
        "rows_total": sum(len(v) for v in emitted.values()),
        "d1_by_match_class": dict(sorted(
            Counter(r["match_class"] for r in emitted["links"]).items()
        )),
        "d1_by_scope": dict(sorted(
            Counter(r["scope"] for r in emitted["links"]).items()
        )),
        "d1_by_year_strengthener": dict(sorted(
            Counter(r["year_strengthener"] for r in emitted["links"]).items()
        )),
        "d3_strengthened": sum(
            1 for r in emitted["candidates"] if r["d3_strengthened"]
        ),
    }
    for key, value in recomputed.items():
        if counts.get(key) != value:
            failures.append(f"RECEIPT_COUNT_MISMATCH_{key.upper()}")
            details.append({"counter": key, "receipt": counts.get(key),
                            "recomputed": value})

    guards = receipt.get("guards", {})
    guard_checks = {
        "cross_clause_attachment_demoted": (
            guards.get("cross_clause_attachment", {}).get("demoted"),
            rederived["measured"]["demoted_cross_clause_attachment"],
        ),
        "declaration_is_a_disclaimer_demoted": (
            guards.get("declaration_is_a_disclaimer", {}).get("demoted"),
            rederived["measured"]["demoted_declaration_is_a_disclaimer"],
        ),
        "middle_initial_conflicts_original_total": (
            guards.get("middle_initial_alias_strip", {}).get(
                "conflicts_original_total"
            ),
            sum(rederived["measured"]["mi_conflicts_original"].values()),
        ),
        "middle_initial_conflicts_after_alias_strip_total": (
            guards.get("middle_initial_alias_strip", {}).get(
                "conflicts_after_alias_strip_total"
            ),
            sum(rederived["measured"]["mi_conflicts_after_alias_strip"].values()),
        ),
        "d1_before_guards": (
            counts.get("d1_before_guards"),
            rederived["measured"]["d1_before_guards"],
        ),
    }
    for key, (declared, remeasured) in guard_checks.items():
        if declared != remeasured:
            failures.append(f"GUARD_MEASUREMENT_MISMATCH_{key.upper()}")
            details.append({"guard": key, "receipt": declared,
                            "recomputed": remeasured})

    # ---- 6. file digests + twin byte identity ---------------------------
    file_checks = []
    declared_files = {entry["name"]: entry for entry in receipt.get("files", [])}
    for filename in DATA_FILENAMES:
        path = primary / filename
        actual = sha256_file(path)
        entry = declared_files.get(filename, {})
        ok = entry.get("sha256") == actual
        file_checks.append({
            "name": filename, "sha256": actual,
            "declared_sha256": entry.get("sha256"), "match": ok,
            "records": sum(1 for _ in read_rows(path)),
            "bytes": path.stat().st_size,
        })
        if not ok:
            failures.append("FILE_DIGEST_MISMATCH")
    twin_checks: list[dict[str, Any]] = []
    if twin is not None:
        for filename in DATA_FILENAMES + (RECEIPT_FILENAME,):
            left = primary / filename
            right = twin / filename
            if not right.is_file():
                failures.append("TWIN_FILE_MISSING")
                twin_checks.append({"name": filename, "present": False,
                                    "identical": False})
                continue
            if filename == RECEIPT_FILENAME:
                # The receipt names the directory it was materialised into, so
                # byte equality is reported but the gate is on the body.
                identical_bytes = left.read_bytes() == right.read_bytes()
                left_body = json.loads(left.read_text(encoding="utf-8"))
                right_body = json.loads(right.read_text(encoding="utf-8"))
                for body in (left_body, right_body):
                    body.pop("materialisation", None)
                identical = canonical_json_bytes(left_body) == canonical_json_bytes(
                    right_body
                )
                twin_checks.append({
                    "name": filename, "present": True, "identical": identical,
                    "identical_bytes": identical_bytes,
                    "comparison": "receipt body excluding the materialisation name",
                })
            else:
                identical = sha256_file(left) == sha256_file(right)
                twin_checks.append({
                    "name": filename, "present": True, "identical": identical,
                    "comparison": "sha256 of the gzip file",
                    "sha256": sha256_file(left),
                })
            if not identical:
                failures.append("TWIN_NOT_BYTE_IDENTICAL")

    verification = {
        "schema_id": "staffer-network-declaration-directed-tier-verification-v1",
        "schema_note": (
            "No committed JSON schema: the task authorises exactly one new "
            "committed schema and it is the row schema."
        ),
        "run_id": args.run_id,
        "glassbox_source": "declaration-directed-d1",
        "generated_at_utc": args.generated_at,
        "primary_root": str(primary),
        "twin_root": str(twin) if twin else None,
        "status": "FAIL" if failures else "PASS",
        "independence": (
            "This verifier does not import build_declaration_directed_tier. "
            "Every emitted row is re-derived field by field from "
            "adjudication.ndjson.gz, targets.ndjson.gz and the three hit "
            "corpora with this file's own clause-anchoring, disclaimer and "
            "alias-stripping implementations."
        ),
        "input_rebinding": input_checks,
        "adjudication_pin": {
            "expected": ADJUDICATION_SHA256,
            "on_disk": adjudication_on_disk,
            "match": adjudication_on_disk == ADJUDICATION_SHA256,
        },
        "schema_validation": {
            "schema_path": str(schema_path),
            "schema_sha256": sha256_file(schema_path),
            "rows_validated": sum(len(v) for v in emitted.values()),
            "errors": len(schema_errors),
        },
        "rederivation": {
            "links": len(rederived["rows"]["links"]),
            "candidates": len(rederived["rows"]["candidates"]),
            "non_evidential": len(rederived["rows"]["non_evidential"]),
            "measured_guards": {
                "d1_before_guards": rederived["measured"]["d1_before_guards"],
                "demoted_cross_clause_attachment":
                    rederived["measured"]["demoted_cross_clause_attachment"],
                "demoted_declaration_is_a_disclaimer":
                    rederived["measured"]["demoted_declaration_is_a_disclaimer"],
                "cross_clause_status_counts": dict(sorted(
                    rederived["measured"]["cross_clause_status_counts"].items()
                )),
                "disclaimer_status_counts": dict(sorted(
                    rederived["measured"]["disclaimer_status_counts"].items()
                )),
                "middle_initial_conflicts_original": dict(sorted(
                    rederived["measured"]["mi_conflicts_original"].items()
                )),
                "middle_initial_conflicts_after_alias_strip": dict(sorted(
                    rederived["measured"]["mi_conflicts_after_alias_strip"].items()
                )),
            },
        },
        "recomputed_counts": recomputed,
        "files": file_checks,
        "twin": twin_checks,
        "promotion_counters": {
            "canonical_identity_promotions": receipt.get(
                "canonical_identity_promotions"
            ),
            "canonical_employment_promotions": receipt.get(
                "canonical_employment_promotions"
            ),
            "rows_with_any_promotion_flag": sum(
                1 for bucket in emitted.values() for row in bucket
                if row["canonical_employment_promoted"]
                or row["canonical_identity_promoted"]
                or row["canonical_eligible"]
            ),
        },
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "details": details,
        "failures": sorted(set(failures)),
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / VERIFICATION_FILENAME).write_bytes(canonical_json_bytes(verification))
    return verification


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the declaration-directed employment tier."
    )
    parser.add_argument("--primary-root", required=True)
    parser.add_argument("--twin-root", default="")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--declaim-root", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument(
        "--nickname-file",
        default=str(
            REPOSITORY_ROOT / "data" / "staffer_network" / "reference"
            / "first_name_nicknames_v1.json"
        ),
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    verification = run(args)
    print(json.dumps({
        "status": verification["status"],
        "failures": verification["failures"],
        "rederivation": verification["rederivation"],
        "twin": verification["twin"],
    }, sort_keys=True))
    return 1 if verification["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
