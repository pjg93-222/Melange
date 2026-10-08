#!/usr/bin/env python3
r"""Independently verify the declaration-widened recovery tier.

This verifier does NOT import the builder.  It re-derives every emitted row from
the recovery-lane artifacts and the live corpora and then compares, field by
field, with what the generation actually contains.  Where the builder read a
summary, the verifier goes one layer deeper: the E1 winner is re-selected from
``control_newrules_per_target.json.gz`` -- the raw control measurement -- rather
than from ``e3_recovered.json``, and the payroll titles, periods and years are
rebuilt from ``house_personnel_observations``, ``house_person_office_spans`` and
the Senate candidates file.

What it checks
--------------
1.  every emitted row validates against the committed row schema;
2.  the emitted row sets are exactly the ruled populations -- 70 E1 rows, the 18
    RESOLVED-provenance A3 D1s, and the 14 FLAGGED-provenance A3 rows held;
3.  no lda person appears in more than one file, and no held row appears in a
    linked file;
4.  every row's payroll person, titles, periods and years reproduce from the
    corpora;
5.  the cross-clause guard status on every row reproduces, and the guard is
    shown to be powered by a foreign-office-key negative control;
6.  the control evidence in the receipt reproduces from ``control_newrules.json``
    and its per-target detail, including the positive control and the control
    arm's demonstrated capability to fire;
7.  every row is review-only and both promotion counters are pinned to 0;
8.  the receipt's file digests match the files on disk;
9.  primary and twin are byte-identical file by file;
10. the coverage effect recomputes from ``metric.py``.

Read-only.  Never imports a ``fec`` module other than
``fec/staffer_network/intervals.py`` and ``fec/staffer_network/schema_validation.py``.
Runs no git command.  Refuses a non-empty output directory.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
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

VERIFICATION_SCHEMA_ID = "staffer-network-declaration-widened-tier-verification-v1"
VERIFICATION_FILENAME = "declaration_widened_tier_verification_receipt.json"
ROW_SCHEMA_FILENAME = "declaration_widened_employment_link.schema.json"

WIDENED_FILENAME = "declaration_widened_employment_links.ndjson.gz"
RECOVERED_FILENAME = "declaration_directed_recovered_links.ndjson.gz"
HELD_FILENAME = "held_for_review.ndjson.gz"
RECEIPT_FILENAME = "declaration_widened_tier_receipt.json"

E1_TIER = "E1_DECLARED_OFFICE_WIDENED_GIVEN_UNIQUE"
D1R_TIER = "D1_DECLARED_OFFICE_EXACT_UNIQUE_RECOVERED"
HELD_TIER = "D1_RECOVERED_HELD_FOR_REVIEW"
HOLD_FLAGGED = "FLAGGED_OFFICE_PROVENANCE_CONFIRMED_FALSE_ATTACHMENT_CLASS"
HOLD_CROSS_CLAUSE = "CROSS_CLAUSE_ATTACHMENT"
SAFE_RULES = ("A_GIVEN_ALT_TOKEN", "B_NICK_DROPPED", "C_GIVEN_PREFIX", "D_GIVEN_ED1")
POSITIVE_CONTROL_RULE = "Z_SURNAME_ONLY_ANY_GIVEN"
SCOPE_PUBLIC = {"house_member": "house_member", "house_nonmember": "house_nonmember",
                "senate_all": "senate"}

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

QUARTER_START = {"Q1": (1, 1), "Q2": (4, 1), "Q3": (7, 1), "Q4": (10, 1)}
QUARTER_END = {"Q1": (3, 31), "Q2": (6, 30), "Q3": (9, 30), "Q4": (12, 31)}

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


class VerifyError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# io
# ---------------------------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                   allow_nan=False)
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


def load_json(path: Path) -> Any:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return json.load(stream)
    return json.loads(path.read_text(encoding="utf-8"))


def prepare_output(output: Path) -> Path:
    if output.exists():
        if not output.is_dir():
            raise VerifyError(f"output root exists and is not a directory: {output}")
        if any(output.iterdir()):
            raise VerifyError(f"immutable verification already exists: {output}")
        output.rmdir()
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))


# ---------------------------------------------------------------------------
# clause machinery, written here rather than imported
# ---------------------------------------------------------------------------


def tokens_of(text: str | None) -> list[str]:
    raw = (text or "").upper().replace("&", " AND ")
    return [t for t in NON_ALNUM.sub(" ", raw).split() if t not in CLAUSE_STOPWORDS]


def clauses_of(value: str | None, aggressive: bool = False) -> list[str]:
    splitter = CLAUSE_SPLIT_AGGRESSIVE if aggressive else CLAUSE_SPLIT
    return [part for part in splitter.split(value or "") if part.strip()]


def locate(anchor: Sequence[str], clause: Sequence[str]) -> str | None:
    """CONTIGUOUS, ORDERED_SUBSEQUENCE or None."""
    if not anchor:
        return None
    width = len(anchor)
    if width <= len(clause):
        for index in range(len(clause) - width + 1):
            if list(clause[index:index + width]) == list(anchor):
                return "CONTIGUOUS"
    position = 0
    for want in anchor:
        while position < len(clause) and clause[position] != want:
            position += 1
        if position == len(clause):
            return None
        position += 1
    return "ORDERED_SUBSEQUENCE"


def anchors_for(target: Mapping[str, Any], office_key: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for mention in target.get("declared_office_mentions") or []:
        if office_key not in (mention.get("office_keys") or []):
            continue
        kind = mention.get("kind") or "UNKNOWN"
        if kind == "COMMITTEE" and mention.get("alias_hit"):
            found.append((kind, str(mention["alias_hit"])))
        elif mention.get("text"):
            found.append((kind, str(mention["text"])))
    return found


def grade_attachment(
    target: Mapping[str, Any], office_key: str, aggressive: bool = False
) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for kind, anchor in anchors_for(target, office_key):
        anchor_tokens = tokens_of(anchor)
        if not anchor_tokens:
            continue
        for value in target.get("covered_position_values") or []:
            for clause in clauses_of(value, aggressive=aggressive):
                clause_tokens = tokens_of(clause)
                basis = locate(anchor_tokens, clause_tokens)
                if basis is None:
                    continue
                joined = " ".join(clause_tokens)
                hits.append({
                    "kind": kind, "anchor": anchor, "clause": clause.strip(),
                    "basis": basis,
                    "cue": bool(LEGISLATIVE_CUE.search(joined)),
                    "negation": bool(DISCLAIMER_LEADING_NEGATION.match(joined)),
                })
    if not hits:
        return {"status": "ANCHOR_NOT_LOCATED_IN_ANY_CLAUSE", "basis": "NONE",
                "disclaimer": "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT",
                "clauses": [], "kinds": [], "anchors": []}
    order = {"CONTIGUOUS": 0, "ORDERED_SUBSEQUENCE": 1}
    cued = [h for h in hits if h["cue"]]
    if cued:
        status = "CLAUSE_CARRIES_LEGISLATIVE_CUE"
        basis = min((h["basis"] for h in cued), key=lambda b: order[b])
    else:
        status = "NO_LOCATED_CLAUSE_CARRIES_A_LEGISLATIVE_CUE"
        basis = min((h["basis"] for h in hits), key=lambda b: order[b])
    negations = sum(1 for h in hits if h["negation"])
    if negations == 0:
        disclaimer = "NO_DISCLAIMER_CLAUSE_SUPPORTS_THE_ATTACHMENT"
    elif negations == len(hits):
        disclaimer = "EVERY_SUPPORTING_CLAUSE_IS_A_DISCLAIMER"
    else:
        disclaimer = "SOME_SUPPORTING_CLAUSES_ARE_DISCLAIMERS"
    return {
        "status": status, "basis": basis, "disclaimer": disclaimer,
        "clauses": sorted({h["clause"] for h in hits if h["clause"]}),
        "kinds": sorted({h["kind"] for h in hits}),
        "anchors": sorted({h["anchor"] for h in hits}),
    }


def has_disclaimer_clause(target: Mapping[str, Any]) -> bool:
    for value in target.get("covered_position_values") or []:
        for clause in clauses_of(value):
            joined = " ".join(tokens_of(clause))
            if DISCLAIMER_LEADING_NEGATION.match(joined) and LEGISLATIVE_CUE.search(joined):
                return True
    return False


# ---------------------------------------------------------------------------
# payroll, rebuilt from the corpora
# ---------------------------------------------------------------------------


def only_letters(value: str | None) -> str:
    return LETTERS_ONLY.sub("", (value or "").upper())


def senate_triple(payee_name_raw: str | None) -> str | None:
    text = (payee_name_raw or "").upper().replace(".", " ")
    if "," not in text:
        return None
    surname_part, rest = text.split(",", 1)
    surname = only_letters(surname_part)
    parts = [only_letters(p) for p in rest.split() if only_letters(p)]
    if not surname or not parts:
        return None
    return "%s|%s|%s" % (surname, parts[0], parts[1][:1] if len(parts) > 1 else "")


def canonical_person_key(scope: str, person_key: str) -> str:
    if scope != "senate_all":
        return person_key
    pieces = person_key.split("|")
    return "|".join(pieces[-3:]) if len(pieces) >= 5 else person_key


def quarter_edge(quarter: str, end: bool) -> str | None:
    match = re.fullmatch(r"(\d{4})(Q[1-4])", quarter or "")
    if not match:
        return None
    month, day = (QUARTER_END if end else QUARTER_START)[match.group(2)]
    return date(int(match.group(1)), month, day).isoformat()


def rebuild_payroll(
    wanted: set[tuple[str, str, str]], corpora: Mapping[str, Path]
) -> dict[tuple[str, str, str], dict[str, Any]]:
    blank = {
        "titles": set(), "quarters": set(), "raw": set(), "starts": set(),
        "ends": set(), "spans": set(), "periods": set(), "years": set(),
        "containers": set(), "bioguides": set(), "rows": 0,
    }
    store: dict[tuple[str, str, str], dict[str, Any]] = {}

    def bucket(key: tuple[str, str, str]) -> dict[str, Any]:
        if key not in store:
            store[key] = {name: (set() if isinstance(value, set) else 0)
                          for name, value in blank.items()}
        return store[key]

    member = {(o, p) for s, o, p in wanted if s == "house_member"}
    nonmember = {(o, p) for s, o, p in wanted if s == "house_nonmember"}
    senate = {(o, p) for s, o, p in wanted if s == "senate_all"}
    senate_offices = {o for o, _ in senate}

    if member:
        for row in read_rows(corpora["house_personnel_observations"]):
            pair = (row.get("office_key"), row.get("person_key"))
            if pair not in member:
                continue
            entry = bucket(("house_member",) + pair)
            entry["rows"] += 1
            for field, slot in (("title_raw", "titles"), ("quarter", "quarters"),
                                ("payee_raw", "raw"), ("service_start", "starts"),
                                ("service_end", "ends"),
                                ("container_kind", "containers"),
                                ("member_bioguide", "bioguides")):
                if row.get(field):
                    entry[slot].add(str(row[field]))
    if nonmember:
        for row in read_rows(corpora["house_person_office_spans"]):
            pair = (row.get("office_key"), row.get("person_key"))
            if pair not in nonmember:
                continue
            entry = bucket(("house_nonmember",) + pair)
            entry["rows"] += 1
            entry["titles"].update(str(t) for t in (row.get("titles") or []))
            entry["quarters"].update(str(q) for q in (row.get("quarters_observed") or []))
            if row.get("service_start_min") and row.get("service_end_max"):
                entry["spans"].add((str(row["service_start_min"]),
                                    str(row["service_end_max"])))
            if row.get("container_kind"):
                entry["containers"].add(str(row["container_kind"]))
            if row.get("member_bioguide"):
                entry["bioguides"].add(str(row["member_bioguide"]))
    if senate:
        for row in read_rows(corpora["senate_payroll_employment_candidates"]):
            office = row.get("office_raw")
            if office not in senate_offices:
                continue
            triple = senate_triple(row.get("payee_name_raw"))
            if triple is None or (office, triple) not in senate:
                continue
            entry = bucket(("senate_all", office, triple))
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
    return store


def payroll_fields(scope: str, entry: Mapping[str, Any] | None) -> dict[str, Any]:
    if entry is None:
        return {"titles": [], "periods": [], "years": [], "raw": [], "rows": 0,
                "container": None, "bioguide": None}
    periods: list[dict[str, Any]] = []
    if scope == "house_member":
        starts, ends = sorted(entry["starts"]), sorted(entry["ends"])
        if starts and ends:
            periods.append({"start": starts[0], "end": ends[-1],
                            "basis": "HOUSE_SOD_SERVICE_SPAN"})
        else:
            quarters = sorted(entry["quarters"])
            if quarters:
                periods.append({"start": quarter_edge(quarters[0], end=False),
                                "end": quarter_edge(quarters[-1], end=True),
                                "basis": "HOUSE_SOD_QUARTER_ENVELOPE"})
        years = sorted({int(q[:4]) for q in entry["quarters"] if q[:4].isdigit()})
    elif scope == "house_nonmember":
        for start, end in sorted(entry["spans"]):
            periods.append({"start": start, "end": end,
                            "basis": "HOUSE_SOD_SERVICE_SPAN"})
        if not periods:
            quarters = sorted(entry["quarters"])
            if quarters:
                periods.append({"start": quarter_edge(quarters[0], end=False),
                                "end": quarter_edge(quarters[-1], end=True),
                                "basis": "HOUSE_SOD_QUARTER_ENVELOPE"})
        years = sorted({int(q[:4]) for q in entry["quarters"] if q[:4].isdigit()})
    else:
        for start, end in sorted(entry["periods"]):
            periods.append({"start": start, "end": end, "basis": "SENATE_REPORT_PERIOD"})
        years = sorted(entry["years"])
    unique = {(p["start"], p["end"], p["basis"]): p for p in periods}
    containers, bioguides = sorted(entry["containers"]), sorted(entry["bioguides"])
    return {
        "titles": sorted(entry["titles"]),
        "periods": [unique[k] for k in sorted(unique)],
        "years": years,
        "raw": sorted(entry["raw"]),
        "rows": entry["rows"],
        "container": containers[0] if containers else None,
        "bioguide": bioguides[0] if bioguides else None,
    }


def overlap_of(declared: Sequence[int], payroll: Sequence[int]) -> str:
    if not declared:
        return "NONE"
    if not payroll:
        return "NO_PAYROLL_YEARS"
    if set(declared) & set(payroll):
        return "OVERLAP"
    if max(declared) >= min(payroll) and min(declared) <= max(payroll):
        return "RANGE_OVERLAP"
    return "NO_OVERLAP"


E1_YEAR = {"OVERLAP": "E1_YEAR_CORROBORATED", "RANGE_OVERLAP": "E1_YEAR_RANGE_ONLY",
           "NONE": "E1_YEAR_UNTESTABLE", "NO_PAYROLL_YEARS": "E1_YEAR_UNTESTABLE",
           "NO_OVERLAP": "E1_YEAR_CONTRADICTED"}
D1_YEAR = {"OVERLAP": "D1_YEAR_CORROBORATED", "RANGE_OVERLAP": "D1_YEAR_CORROBORATED",
           "NONE": "D1_YEAR_UNTESTABLE", "NO_PAYROLL_YEARS": "D1_YEAR_UNTESTABLE",
           "NO_OVERLAP": "D1_YEAR_CONTRADICTED"}


def period_flags(periods: Sequence[Mapping[str, Any]]) -> list[str]:
    flags: list[str] = []
    for period in periods:
        try:
            start = date.fromisoformat(period["start"])
            end = date.fromisoformat(period["end"])
        except (TypeError, ValueError):
            flags.append("UNPARSEABLE_PERIOD_BOUND")
            continue
        try:
            UncertainInterval(
                start_earliest=start, start_latest=start, end_earliest=end,
                end_latest=end, start_precision="day", end_precision="day",
            ).validate()
        except ValueError:
            flags.append("PERIOD_BOUNDS_OUT_OF_ORDER")
    return sorted(set(flags))


# ---------------------------------------------------------------------------
# coverage
# ---------------------------------------------------------------------------


def recompute_coverage(
    metric_module: Path | None, routes: Mapping[str, Sequence[str]]
) -> dict[str, Any]:
    if metric_module is None or not metric_module.is_file():
        return {"status": "NOT_COMPUTED"}
    spec = importlib.util.spec_from_file_location("verify_widened_metric", metric_module)
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_widened_metric"] = module
    spec.loader.exec_module(module)
    reachable: set[str] = set()
    for row in module.stream(module.QUEUE):
        pid = row["lda_source_person_id"]
        tags: set[str] = set()
        for value in row.get("covered_position_values") or []:
            tags |= module.classify_value(value)[0]
        person_class = module.person_class(tags)
        if person_class in ("C_BLANK", "C_NONE_EXPLICIT", "C_JUNK_ONLY",
                            "C_AMBIG_NONGOV", "C_EXEC_ONLY"):
            continue
        years = [int(t) for t in (row.get("covered_position_year_tokens") or [])
                 if str(t).isdigit() and 1930 <= int(t) <= 2026]
        if person_class == "C_LEGISLATIVE" and years and max(years) < 2009:
            continue
        reachable.add(pid)
    covered = (
        {r["lda_source_person_id"] for r in module.stream(module.SPINE)
         if r.get("link_status") == "LINKED_BY_PAYROLL_KEY"}
        | {r["lda_source_person_id"] for r in module.stream(module.RESOL)
           if r.get("status") in ("RESOLVED_R1", "RESOLVED_R2")}
        | {r["lda_source_person_id"] for r in module.stream(module.A6)
           if (r.get("payroll_cross_check") or {}).get("status")
           == "CONFIRMED_BY_PAYROLL"}
    )
    denominator = len(reachable)
    numerator = len(covered & reachable)
    result: dict[str, Any] = {
        "status": "COMPUTED",
        "metric_module_sha256": sha256_file(metric_module),
        "reachable_denominator": denominator,
        "covered_numerator_before": numerator,
        "rcr_before_pct": round(100.0 * numerator / denominator, 4),
        "routes": {},
    }
    for label in sorted(routes):
        added = set(routes[label]) & reachable
        newly = added - covered
        after = numerator + len(newly)
        result["routes"][label] = {
            "route_size": len(set(routes[label])),
            "inside_reachable": len(added),
            "already_covered": len(added & covered),
            "newly_covered": len(newly),
            "numerator_before": numerator,
            "numerator_after": after,
            "denominator": denominator,
            "rcr_before_pct": round(100.0 * numerator / denominator, 4),
            "rcr_after_pct": round(100.0 * after / denominator, 4),
            "points": round(100.0 * (after - numerator) / denominator, 4),
        }
    return result


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> dict[str, Any]:
    primary = Path(args.primary_root).resolve()
    twin = Path(args.twin_root).resolve() if args.twin_root else None
    output = Path(args.output_root).resolve()
    recover_root = Path(args.recover_root).resolve()
    declaim_root = Path(args.declaim_root).resolve()
    schema_path = (
        REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas" / ROW_SCHEMA_FILENAME
    )
    row_schema = json.loads(schema_path.read_text(encoding="utf-8"))

    failures: list[str] = []
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL",
                       "detail": detail})
        if not passed:
            failures.append(name)

    receipt = json.loads((primary / RECEIPT_FILENAME).read_text(encoding="utf-8"))
    emitted = {
        E1_TIER: list(read_rows(primary / WIDENED_FILENAME)),
        D1R_TIER: list(read_rows(primary / RECOVERED_FILENAME)),
        HELD_TIER: list(read_rows(primary / HELD_FILENAME)),
    }
    all_rows = emitted[E1_TIER] + emitted[D1R_TIER] + emitted[HELD_TIER]

    # ---- 1. schema ---------------------------------------------------------
    schema_errors: list[str] = []
    for row in all_rows:
        try:
            validate_instance(row, row_schema)
        except SchemaValidationError as error:
            schema_errors.append(
                "%s: %s" % (row.get("lda_source_person_id"), error))
    record("every_row_validates_against_the_committed_schema", not schema_errors,
           {"errors": schema_errors[:20], "rows": len(all_rows)})

    # ---- 2. populations re-derived from the recovery lane -------------------
    e3 = load_json(recover_root / "e3_recovered.json")["rows"]
    a3 = load_json(recover_root / "a3_rows.json")["rows"]
    expect_e1 = {r["lda_source_person_id"] for r in e3
                 if r["census_status"] != "D1_DECLARED_OFFICE_EXACT_UNIQUE"}
    expect_recovered = {
        r["lda_source_person_id"] for r in a3
        if r["recovered_status_resolved_offices_only"] == "D1_DECLARED_OFFICE_EXACT_UNIQUE"}
    expect_held = {
        r["lda_source_person_id"] for r in a3
        if r["recovered_status_any_provenance"] == "D1_DECLARED_OFFICE_EXACT_UNIQUE"
        and r["recovered_status_resolved_offices_only"] != "D1_DECLARED_OFFICE_EXACT_UNIQUE"}
    got_e1 = {r["lda_source_person_id"] for r in emitted[E1_TIER]}
    got_recovered = {r["lda_source_person_id"] for r in emitted[D1R_TIER]}
    got_held = {r["lda_source_person_id"] for r in emitted[HELD_TIER]}
    record("e1_population_is_exactly_the_70_non_d1_e3_recoveries",
           got_e1 == expect_e1 and len(got_e1) == 70,
           {"emitted": len(got_e1), "expected": len(expect_e1),
            "missing": sorted(expect_e1 - got_e1)[:10],
            "unexpected": sorted(got_e1 - expect_e1)[:10]})
    record("recovered_d1_population_is_exactly_the_18_resolved_provenance_a3_rows",
           got_recovered == expect_recovered and len(got_recovered) == 18,
           {"emitted": len(got_recovered), "expected": len(expect_recovered)})
    record("held_population_is_exactly_the_14_flagged_provenance_a3_rows",
           got_held == expect_held and len(got_held) == 14,
           {"emitted": len(got_held), "expected": len(expect_held)})
    record("no_person_appears_in_more_than_one_file",
           not (got_e1 & got_recovered) and not (got_e1 & got_held)
           and not (got_recovered & got_held),
           {"e1_and_recovered": sorted(got_e1 & got_recovered),
            "e1_and_held": sorted(got_e1 & got_held),
            "recovered_and_held": sorted(got_recovered & got_held)})
    record("no_held_row_carries_a_link_family",
           all(r["evidence_tier_family"] == "HELD" for r in emitted[HELD_TIER])
           and all(r["hold_reason"] for r in emitted[HELD_TIER]),
           {"families": sorted({r["evidence_tier_family"] for r in emitted[HELD_TIER]})})
    record("e1_tier_is_ranked_below_d1",
           all(r["tier_rank_relative_to_d1"] == "BELOW" and
               r["evidence_tier_family"] == "LINK_BELOW_D1" and
               r["match_class"] == "WIDENED_GIVEN_SURNAME_EXACT" and
               r["widening_rule"] in SAFE_RULES
               for r in emitted[E1_TIER]))

    # ---- 3. review-only invariants -----------------------------------------
    record("every_row_is_review_only_and_unpromoted",
           all(r["canonical_eligible"] is False
               and r["canonical_employment_promoted"] is False
               and r["canonical_identity_promoted"] is False
               and r["canonical_identity_decision"] == "NOT_ADJUDICATED"
               and r["review_status"] == "REVIEW_REQUIRED"
               and r["status_is_a_label_not_a_promotion"] is True
               for r in all_rows))
    record("receipt_pins_both_promotion_counters_to_zero",
           receipt["canonical_identity_promotions"] == 0
           and receipt["canonical_employment_promotions"] == 0)
    record("every_linked_row_has_an_in_office_tie_size_of_one",
           all(r["in_office_tie_size"] == 1
               for r in emitted[E1_TIER] + emitted[D1R_TIER]))

    # ---- 4. payroll rebuilt from the corpora --------------------------------
    corpora = {name: REPOSITORY_ROOT.joinpath(*parts) for name, parts in CORPUS_INPUTS}
    missing_corpus = [name for name, path in corpora.items() if not path.is_file()]
    record("every_corpus_is_present", not missing_corpus, {"missing": missing_corpus})
    wanted = {(r["source_scope"], r["office_key"], r["resolved_payroll_person_key"])
              for r in all_rows}
    store = rebuild_payroll(wanted, corpora)
    unresolved = sorted(t for t in wanted if t not in store)
    record("every_payroll_person_resolves_in_the_corpora", not unresolved,
           {"unresolved": [list(t) for t in unresolved[:10]], "wanted": len(wanted)})

    targets = {r["lda_source_person_id"]: r
               for r in read_rows(declaim_root / "targets.ndjson.gz")}
    adjudication = {r["lda_source_person_id"]: r
                    for r in read_rows(declaim_root / "adjudication.ndjson.gz")}

    field_mismatches: list[dict[str, Any]] = []
    guard_mismatches: list[dict[str, Any]] = []
    guard_status_counts = Counter()
    guard_basis_counts = Counter()
    period_flag_counts = Counter()
    for row in all_rows:
        pid = row["lda_source_person_id"]
        scope = row["source_scope"]
        rebuilt = payroll_fields(
            scope, store.get((scope, row["office_key"],
                              row["resolved_payroll_person_key"])))
        expected = {
            "scope": SCOPE_PUBLIC[scope],
            "payroll_titles": rebuilt["titles"],
            "payroll_periods": rebuilt["periods"],
            "payroll_period_count": len(rebuilt["periods"]),
            "payroll_years": rebuilt["years"],
            "payroll_year_first": rebuilt["years"][0] if rebuilt["years"] else None,
            "payroll_year_last": rebuilt["years"][-1] if rebuilt["years"] else None,
            "payroll_observation_rows": rebuilt["rows"],
            "payroll_payee_raw_examples": rebuilt["raw"][:6],
            "office_container_kind": rebuilt["container"],
            "office_member_bioguide": rebuilt["bioguide"],
            "display_name": adjudication[pid].get("display_name")
            or targets[pid].get("display_name") or "",
            "prior_resolution_status": adjudication[pid].get("prior_resolution_status"),
            "held_status": adjudication[pid].get("held_status"),
            "source_census_status": adjudication[pid]["adjudicated_status"],
            "source_census_substatus": adjudication[pid]["adjudicated_substatus"],
            "lda_priority": targets[pid].get("lda_priority"),
            "prior_best_tier": targets[pid].get("prior_best_tier"),
        }
        overlap = overlap_of(row["declared_years"], rebuilt["years"])
        table = E1_YEAR if row["evidence_tier"] == E1_TIER or (
            row["evidence_tier"] == HELD_TIER
            and row["year_strengthener"].startswith("E1_")) else D1_YEAR
        expected["year_overlap_basis"] = overlap
        expected["year_strengthener"] = table[overlap]
        for field, value in expected.items():
            if row[field] != value:
                field_mismatches.append(
                    {"lda_source_person_id": pid, "field": field,
                     "emitted": row[field], "rebuilt": value})
        graded = grade_attachment(targets[pid], row["office_key"])
        aggressive = grade_attachment(targets[pid], row["office_key"], aggressive=True)
        guard_status_counts[graded["status"]] += 1
        guard_basis_counts[graded["basis"]] += 1
        for flag in period_flags(row["payroll_periods"]):
            period_flag_counts[flag] += 1
        if (row["guard_cross_clause_attachment_status"] != graded["status"]
                or row["guard_cross_clause_attachment_basis"] != graded["basis"]
                or row["guard_disclaimer_status"] != graded["disclaimer"]
                or row["declared_office_supporting_clauses"] != graded["clauses"]
                or row["declared_office_mention_kinds"] != graded["kinds"]
                or row["declared_office_texts"] != graded["anchors"]
                or row["guard_cross_clause_attachment_status_aggressive_split"]
                != aggressive["status"]
                or row["declaration_contains_disclaimer_clause"]
                != has_disclaimer_clause(targets[pid])):
            guard_mismatches.append({"lda_source_person_id": pid,
                                     "office_key": row["office_key"],
                                     "emitted": row["guard_cross_clause_attachment_status"],
                                     "rebuilt": graded["status"]})
    record("every_row_field_rebuilt_from_the_corpora_matches", not field_mismatches,
           {"mismatches": field_mismatches[:20], "count": len(field_mismatches)})
    record("every_cross_clause_guard_result_reproduces", not guard_mismatches,
           {"mismatches": guard_mismatches[:20], "count": len(guard_mismatches)})
    record("every_linked_row_passes_the_cross_clause_guard",
           all(r["guard_cross_clause_attachment_status"] == "CLAUSE_CARRIES_LEGISLATIVE_CUE"
               for r in emitted[E1_TIER] + emitted[D1R_TIER]),
           {"status_counts": dict(guard_status_counts)})

    # ---- 5. the guard is powered -------------------------------------------
    key_universe = sorted({
        key for target in targets.values()
        for mention in (target.get("declared_office_mentions") or [])
        for key in (mention.get("office_keys") or [])
    })
    rejected = 0
    trials = 0
    for row in all_rows:
        target = targets[row["lda_source_person_id"]]
        own = {key for mention in (target.get("declared_office_mentions") or [])
               for key in (mention.get("office_keys") or [])}
        seed = int(hashlib.sha256(
            row["lda_source_person_id"].encode("utf-8")).hexdigest()[8:16], 16)
        for step in range(20):
            candidate = key_universe[(seed + step * 4093) % len(key_universe)]
            if candidate in own:
                continue
            trials += 1
            if grade_attachment(target, candidate)["status"] != "CLAUSE_CARRIES_LEGISLATIVE_CUE":
                rejected += 1
    record("the_cross_clause_guard_rejects_a_foreign_office_key",
           trials > 0 and rejected == trials,
           {"trials": trials, "rejected": rejected})

    # ---- 6. control evidence recomputed ------------------------------------
    control = load_json(recover_root / "control_newrules.json")
    per_target = load_json(recover_root / "control_newrules_per_target.json.gz")
    pooled_declared = sum(
        1 for scopes in per_target.values()
        if any(rule in SAFE_RULES for entry in scopes.values()
               for rule in entry["declared_unique"]))
    pooled_control = sum(
        1 for scopes in per_target.values()
        if any(rule in SAFE_RULES for entry in scopes.values()
               for rule in entry["control_unique"]))
    stated = receipt["control_evidence"]["pooled_four_rules"]
    record("pooled_control_counts_reproduce_from_the_per_target_detail",
           stated["declared_unique_targets"] == pooled_declared == 72
           and stated["control_unique_targets"] == pooled_control == 0,
           {"receipt": stated, "recomputed_declared": pooled_declared,
            "recomputed_control": pooled_control})
    record("control_searches_per_arm_reproduce",
           receipt["control_evidence"]["searches_per_arm"]
           == control["pooled_target_scope_rows_per_arm"] == 2783)
    record("no_cleared_rule_has_a_control_hit",
           all(control["rules"][name]["control_unique"] == 0 for name in SAFE_RULES),
           {name: control["rules"][name]["control_unique"] for name in SAFE_RULES})
    positive = receipt["control_evidence"]["positive_control"]
    record("the_positive_control_fired_in_the_same_control_arm",
           positive["control_unique_target_scope_rows"]
           == control["rules"][POSITIVE_CONTROL_RULE]["control_unique"] > 0
           and positive["status_false_positive_rate_point_pct"]
           == control["rules"][POSITIVE_CONTROL_RULE]["status_fpr_point_pct"],
           {"control_unique": positive["control_unique_target_scope_rows"],
            "status_fpr_point_pct": positive["status_false_positive_rate_point_pct"]})
    capability = receipt["control_evidence"]["control_arm_capability"]
    recomputed_surname = sum(s["control_surname_present_pairs"]
                             for s in control["per_scope"].values())
    record("the_control_arm_was_demonstrably_capable_of_firing",
           capability["control_office_pairs_with_a_strict_same_surname_person"]
           == recomputed_surname > 0,
           {"receipt": capability["control_office_pairs_with_a_strict_same_surname_person"],
            "recomputed": recomputed_surname})
    record("every_e1_row_carries_its_own_rule_control_numbers",
           all(r["widening_rule_control_unique_target_scope_rows"] == 0
               and r["widening_rule_declared_unique_target_scope_rows"]
               == control["rules"][r["widening_rule"]]["declared_unique"]
               and r["widening_rule_status_fpr_upper95_pct"]
               == control["rules"][r["widening_rule"]]["status_fpr_upper95_pct"]
               for r in emitted[E1_TIER]))
    record("the_compound_surname_rule_is_recorded_as_a_declared_refusal",
           receipt["declared_refusals"]["S1_COMPOUND_SURNAME_RULE"]["implemented"] is False
           and isinstance(
               receipt["declared_refusals"]["S1_COMPOUND_SURNAME_RULE"][
                   "forgone_yield_targets_ruled"], int),
           receipt["declared_refusals"]["S1_COMPOUND_SURNAME_RULE"])

    # ---- 7. the E1 winner re-selected from the raw control measurement ------
    rule_order = {name: index for index, name in enumerate(SAFE_RULES)}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for pid, scopes in per_target.items():
        for entry in scopes.values():
            for detail in entry["declared_detail"]:
                if detail["rule"] not in SAFE_RULES:
                    continue
                grouped.setdefault(pid, []).append(detail)
    reselection_divergences: list[dict[str, Any]] = []
    reselection_checked = 0
    winner_wanted = {
        (d["scope"], d["office_key"],
         canonical_person_key(d["scope"], d["payroll_person_key"]))
        for pid in got_e1 for d in grouped.get(pid, [])
    }
    winner_store = rebuild_payroll(winner_wanted - set(store), corpora)
    winner_store.update(store)
    by_pid = {r["lda_source_person_id"]: r for r in emitted[E1_TIER]}
    for pid in sorted(got_e1):
        hits = list(grouped.get(pid, []))
        if not hits:
            reselection_divergences.append({"lda_source_person_id": pid,
                                            "reason": "NO_DECLARED_DETAIL"})
            continue
        declared_years = by_pid[pid]["declared_years"]
        annotated = []
        for detail in hits:
            key = canonical_person_key(detail["scope"], detail["payroll_person_key"])
            years = payroll_fields(
                detail["scope"],
                winner_store.get((detail["scope"], detail["office_key"], key)))["years"]
            annotated.append((detail, key, overlap_of(declared_years, years)))
        annotated.sort(key=lambda item: (
            rule_order[item[0]["rule"]],
            0 if item[2] in ("OVERLAP", "RANGE_OVERLAP") else 1))
        winner = annotated[0]
        reselection_checked += 1
        row = by_pid[pid]
        if (winner[0]["scope"], winner[0]["office_key"], winner[1]) != (
                row["source_scope"], row["office_key"],
                row["resolved_payroll_person_key"]):
            reselection_divergences.append({
                "lda_source_person_id": pid,
                "emitted": [row["source_scope"], row["office_key"],
                            row["resolved_payroll_person_key"]],
                "reselected": [winner[0]["scope"], winner[0]["office_key"], winner[1]],
                "candidates": len(annotated),
            })
    record("the_e1_winner_reselects_from_the_raw_control_measurement",
           not reselection_divergences,
           {"checked": reselection_checked,
            "divergences": reselection_divergences[:20],
            "count": len(reselection_divergences)})
    record("every_e1_row_declares_its_competing_offices",
           all(r["winner_selected_among_multiple_offices"]
               == bool(r["competing_office_hits"]) for r in emitted[E1_TIER])
           and all(len(r["competing_office_hits"]) + 1 == len(grouped.get(
               r["lda_source_person_id"], [])) for r in emitted[E1_TIER]),
           {"multiplicity": dict(Counter(
               1 + len(r["competing_office_hits"]) for r in emitted[E1_TIER]))})

    # ---- 8. office provenance ----------------------------------------------
    def provenance(target: Mapping[str, Any], office_key: str) -> str:
        resolved = set(target.get("candidate_office_keys_house") or []) | set(
            target.get("candidate_office_keys_senate") or [])
        flagged = set(target.get("flagged_candidate_office_keys_house") or []) | set(
            target.get("flagged_candidate_office_keys_senate") or [])
        if office_key in resolved:
            return "RESOLVED"
        if office_key in flagged:
            return "FLAGGED"
        return "NEITHER"

    provenance_mismatch = [
        {"lda_source_person_id": r["lda_source_person_id"],
         "emitted": r["office_provenance"],
         "rebuilt": provenance(targets[r["lda_source_person_id"]], r["office_key"])}
        for r in all_rows
        if r["office_provenance"] != provenance(
            targets[r["lda_source_person_id"]], r["office_key"])
    ]
    record("office_provenance_reproduces_from_the_target_rows",
           not provenance_mismatch, {"mismatches": provenance_mismatch[:10]})
    record("no_linked_row_sits_on_a_flagged_office",
           all(r["office_provenance"] == "RESOLVED"
               for r in emitted[E1_TIER] + emitted[D1R_TIER]))
    record("every_flagged_hold_row_really_is_flagged_provenance",
           all(r["office_provenance"] == "FLAGGED" for r in emitted[HELD_TIER]
               if r["hold_reason"] == HOLD_FLAGGED))

    # ---- 9. digests, files, twin -------------------------------------------
    digest_rows = []
    digest_ok = True
    for entry in receipt["files"]:
        path = primary / entry["name"]
        actual = sha256_file(path)
        rows = sum(1 for _ in read_rows(path))
        ok = (actual == entry["sha256"] and rows == entry["records"]
              and path.stat().st_size == entry["bytes"])
        digest_ok = digest_ok and ok
        digest_rows.append({"name": entry["name"], "sha256": actual, "records": rows,
                            "bytes": path.stat().st_size, "matches_receipt": ok})
    record("receipt_file_digests_match_the_files_on_disk", digest_ok, digest_rows)
    expected_names = {WIDENED_FILENAME, RECOVERED_FILENAME, HELD_FILENAME,
                      RECEIPT_FILENAME}
    actual_names = {p.name for p in primary.iterdir()}
    record("the_generation_contains_exactly_the_expected_files",
           actual_names == expected_names,
           {"unexpected": sorted(actual_names - expected_names),
            "missing": sorted(expected_names - actual_names)})

    twin_checks: list[dict[str, Any]] = []
    if twin is not None:
        for filename in (WIDENED_FILENAME, RECOVERED_FILENAME, HELD_FILENAME):
            left, right = primary / filename, twin / filename
            if not right.is_file():
                twin_checks.append({"name": filename, "present": False,
                                    "identical": False})
                continue
            identical = left.read_bytes() == right.read_bytes()
            twin_checks.append({"name": filename, "present": True,
                                "identical": identical,
                                "sha256": sha256_file(left),
                                "twin_sha256": sha256_file(right)})
        left_body = dict(receipt)
        right_body = json.loads(
            (twin / RECEIPT_FILENAME).read_text(encoding="utf-8"))
        for body in (left_body, right_body):
            body.pop("materialisation", None)
        twin_checks.append({
            "name": RECEIPT_FILENAME, "present": True,
            "identical": canonical_json_bytes(left_body)
            == canonical_json_bytes(right_body),
            "comparison": "receipt body excluding the materialisation name",
        })
        record("primary_and_twin_are_byte_identical",
               all(entry["identical"] for entry in twin_checks), twin_checks)

    # ---- 10. coverage -------------------------------------------------------
    metric_module = Path(args.metric_module).resolve() if args.metric_module else None
    routes = {
        "E1_widened_tier_as_built": sorted(got_e1),
        "D1_recovered_tier_as_built": sorted(got_recovered),
        "both_linked_tiers_as_built": sorted(got_e1 | got_recovered),
        "held_for_review_not_linked": sorted(got_held),
    }
    coverage = recompute_coverage(metric_module, routes)
    if coverage["status"] == "COMPUTED":
        stated_coverage = receipt["coverage_effect"]
        agree = (
            stated_coverage.get("status") == "COMPUTED"
            and stated_coverage["reachable_denominator"] == coverage["reachable_denominator"]
            and stated_coverage["covered_numerator_before"]
            == coverage["covered_numerator_before"]
            and all(
                stated_coverage["routes"][label]["newly_covered"]
                == coverage["routes"][label]["newly_covered"]
                and stated_coverage["routes"][label]["rcr_after_pct"]
                == coverage["routes"][label]["rcr_after_pct"]
                for label in coverage["routes"]
            )
        )
        record("the_coverage_effect_recomputes", agree,
               {"recomputed": coverage, "receipt_status": stated_coverage.get("status")})
        record("the_coverage_baseline_reproduces_the_published_metric",
               coverage["reachable_denominator"] == 6867
               and coverage["covered_numerator_before"] == 3905,
               {"reachable": coverage["reachable_denominator"],
                "covered": coverage["covered_numerator_before"]})

    record("the_build_receipt_reports_no_failures", not receipt["failures"],
           receipt["failures"])

    verification = {
        "schema_id": VERIFICATION_SCHEMA_ID,
        "schema_note": (
            "This verification receipt has no committed JSON schema; the task "
            "authorises exactly one new committed schema and it is the row schema."
        ),
        "run_id": args.run_id,
        "generated_at_utc": args.generated_at,
        "primary_root": str(primary),
        "twin_root": str(twin) if twin else None,
        "recover_root": str(recover_root),
        "declaim_root": str(declaim_root),
        "generation_id": receipt["generation_id"],
        "status": "FAIL" if failures else "PASS",
        "independence": (
            "This verifier does not import the builder. Row populations are "
            "re-selected from the recovery-lane artifacts, the E1 winner is "
            "re-selected from the raw control measurement rather than from the "
            "recovery lane's summary, and payroll titles, periods and years are "
            "rebuilt by streaming the House SOD observations, the House office "
            "spans and the Senate candidates file."
        ),
        "checks": checks,
        "counts": {
            "rows_verified": len(all_rows),
            "e1_rows": len(emitted[E1_TIER]),
            "recovered_d1_rows": len(emitted[D1R_TIER]),
            "held_rows": len(emitted[HELD_TIER]),
            "cross_clause_status_counts": {k: guard_status_counts[k]
                                           for k in sorted(guard_status_counts)},
            "cross_clause_basis_counts": {k: guard_basis_counts[k]
                                          for k in sorted(guard_basis_counts)},
            "period_review_flags": {k: period_flag_counts[k]
                                    for k in sorted(period_flag_counts)},
        },
        "coverage_recomputed": coverage,
        "files": digest_rows,
        "twin": twin_checks,
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "failures": failures,
    }

    staging = prepare_output(output)
    try:
        (staging / VERIFICATION_FILENAME).write_bytes(canonical_json_bytes(verification))
        os.replace(staging, output)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return verification


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independently verify the declaration-widened recovery tier."
    )
    parser.add_argument("--primary-root", required=True)
    parser.add_argument("--twin-root", default="")
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--recover-root", required=True)
    parser.add_argument("--declaim-root", required=True)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--metric-module", default="")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    verification = run(args)
    print(json.dumps({
        "status": verification["status"],
        "counts": verification["counts"],
        "failures": verification["failures"],
        "checks": [{"check": c["check"], "status": c["status"]}
                   for c in verification["checks"]],
    }, indent=1, sort_keys=True))
    return 1 if verification["failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
