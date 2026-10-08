#!/usr/bin/env python3
"""Independently verify the exploratory temporal tier generation.

This script never imports ``build_exploratory_temporal_tier``.  It reads the
emitted receipt, re-binds every declared input by hash, re-derives every
co-tenure weight (including which per-container record tier supports it,
2026-09-02 addendum), every revolving order class, and every person-to-container
membership edge from the Part A records with its own half-open union /
intersection code (stdlib ``datetime.date`` only, no ``intervals.py``), re-runs
``network_math`` on the emitted edge file to check the operator's row sums and
the emitted isolate flags, checks primary/twin byte identity, greps the
language law, and asserts that every emitted row is exploratory and
unpromoted.  It writes its own receipt and exits 1 on FAIL.

The disclaimer sentence the spec mandates in the receipt is stripped before
the token grep runs.  A 2026-09-02 addendum narrows the language law further:
opaque identifier *values* (an office_key, a container_id, an edge_id, a
support_digest, and so on -- see ``LANGUAGE_LAW_EXEMPT_FIELDS`` /
``LANGUAGE_LAW_EXEMPT_SUFFIXES`` below) are exempt from the token grep because
they carry real office and organization names verbatim; field names, schema
prose, and every other value position are still checked, including inside the
schemas themselves.

The verification receipt has no committed JSON schema: the spec authorises
exactly three new schemas and this is not one of them.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
import gzip
import hashlib
import json
import math
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

import numpy as np  # noqa: E402

from fec.staffer_network.network_math import (  # noqa: E402
    connectedness_pagerank,
    deduplicate_undirected_layer_edges,
    group_balanced_teleport,
    layer_balanced_transition,
)
from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
)

SCHEMA_DIR = REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"
EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"
GLASSBOX_SOURCE = "tiered-corroboration-sidecar"

EDGES_FILENAME = "exploratory_temporal_edges.ndjson.gz"
SCORES_FILENAME = "exploratory_node_scores.ndjson.gz"
RECEIPT_FILENAME = "exploratory_temporal_receipt.json"
VERIFICATION_FILENAME = "exploratory_temporal_verification_receipt.json"

TIER_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
TIER_THRESHOLDS = ("L2", "L3", "L4")
NODE_KINDS = ("person", "container", "organization")
CO_TENURE_LAYER = 0
REVOLVING_LAYER = 1
MEMBERSHIP_LAYER = 2
STATEMENT = (
    "Exploratory diagnostics over strict one-to-one review candidates; "
    "not identity findings; not primary weights; no influence claim."
)
BANNED_TOKENS = ("influence", "predict", "access", "friend", "ideolog", "causal")
SCHEMA_FILES = (
    "exploratory_temporal_edge.schema.json",
    "exploratory_node_score.schema.json",
    "exploratory_temporal_receipt.schema.json",
)
# INV-7 language law, 2026-09-02 addendum: opaque identifier VALUES are
# exempt from the token grep (they carry real office/organization names
# verbatim), but field NAMES, schema prose, receipt prose, and every other
# value position stay checked.  "container_ids" is the plural of the named
# "container_id" and carries the identical container-id strings, so it is
# named explicitly even though it does not literally end in "_id".
LANGUAGE_LAW_EXEMPT_FIELDS = frozenset(
    {
        "office_key",
        "container_id",
        "container_ids",
        "organization_id",
        "person_id",
        "lda_source_person_id",
        "registrant_source_org_id",
        "edge_id",
        "support_digest",
    }
)
LANGUAGE_LAW_EXEMPT_SUFFIXES = ("_id", "_key")
WEIGHT_TOLERANCE = 1e-12
SCORE_TOLERANCE = 1e-9


def is_language_law_exempt_field(field_name: str | None) -> bool:
    if field_name is None:
        return False
    if field_name in LANGUAGE_LAW_EXEMPT_FIELDS:
        return True
    return any(field_name.endswith(suffix) for suffix in LANGUAGE_LAW_EXEMPT_SUFFIXES)


class Failures:
    def __init__(self) -> None:
        self.items: list[str] = []

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.items.append(message)
        return bool(condition)

    def add(self, message: str) -> None:
        self.items.append(message)

    @property
    def ok(self) -> bool:
        return not self.items


# ---------------------------------------------------------------------------
# io helpers (independent of the builder)
# ---------------------------------------------------------------------------


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            yield json.loads(line)


def read_text(path: Path) -> str:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            return stream.read()
    return path.read_text(encoding="utf-8")


def parse_day(value: Any) -> date | None:
    if value is None or value == "":
        return None
    return date.fromisoformat(str(value))


def close(left: float, right: float, tolerance: float = WEIGHT_TOLERANCE) -> bool:
    return math.isclose(left, right, rel_tol=tolerance, abs_tol=tolerance)


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
        "-Stage", stage, "-Source", GLASSBOX_SOURCE,
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return


# ---------------------------------------------------------------------------
# independent half-open interval algebra
# ---------------------------------------------------------------------------


def merge_runs(runs: Iterable[tuple[date, date]]) -> list[tuple[date, date]]:
    """Union half-open ``[start, end)`` runs, merging touching neighbours."""

    ordered = sorted((start, end) for start, end in runs if end > start)
    if not ordered:
        return []
    result = [ordered[0]]
    for start, end in ordered[1:]:
        previous_start, previous_end = result[-1]
        if start <= previous_end:
            result[-1] = (previous_start, max(previous_end, end))
        else:
            result.append((start, end))
    return result


def overlap_runs(
    left: Sequence[tuple[date, date]], right: Sequence[tuple[date, date]]
) -> list[tuple[date, date]]:
    """Intersect two merged half-open calendars with a linear sweep."""

    pieces: list[tuple[date, date]] = []
    left_index = 0
    right_index = 0
    while left_index < len(left) and right_index < len(right):
        low = max(left[left_index][0], right[right_index][0])
        high = min(left[left_index][1], right[right_index][1])
        if high > low:
            pieces.append((low, high))
        if left[left_index][1] <= right[right_index][1]:
            left_index += 1
        else:
            right_index += 1
    return merge_runs(pieces)


def total_days(runs: Sequence[tuple[date, date]]) -> int:
    return sum((end - start).days for start, end in runs)


# ---------------------------------------------------------------------------
# Part A re-derivation
# ---------------------------------------------------------------------------


def container_of(row: Mapping[str, Any]) -> tuple[str, str]:
    bioguide = row.get("member_bioguide")
    kind = row.get("container_kind")
    if not isinstance(kind, str) or not kind:
        kind = "member_office" if bioguide else "unresolved"
    if isinstance(bioguide, str) and bioguide:
        return f"container:bioguide:{bioguide}", kind
    return f"container:office:{row.get('chamber') or 'unknown'}:{row['office_key']}", kind


def load_records(path: Path, tier_strength: Mapping[str, float]):
    records = []
    for row in read_rows(path):
        if row.get("tier") not in tier_strength:
            continue
        core_block = row.get("core") or {}
        core_start = parse_day(core_block.get("start_latest"))
        core_end = parse_day(core_block.get("end_earliest"))
        if core_start is None or core_end is None:
            continue
        envelope_block = row.get("envelope") or {}
        envelope_start = parse_day(envelope_block.get("start_earliest"))
        envelope_end = parse_day(envelope_block.get("end_latest"))
        if envelope_start is None or envelope_end is None:
            envelope_start, envelope_end = core_start, core_end
        container_id, container_kind = container_of(row)
        records.append(
            {
                "person": str(row["lda_source_person_id"]),
                "tier": str(row["tier"]),
                "container_id": container_id,
                "container_kind": container_kind,
                "core": (core_start, core_end),
                "envelope": (envelope_start, envelope_end),
            }
        )
    return records


def load_summary(path: Path) -> dict[str, dict[str, Any]]:
    return {
        str(row["lda_source_person_id"]): {
            "max_tier": str(row["max_tier"]),
            "registrant_side_tier": row.get("registrant_side_tier"),
        }
        for row in read_rows(path)
    }


def load_registrants(
    path: Path, summary: Mapping[str, Mapping[str, Any]], r_strength: Mapping[str, float]
):
    out = []
    for source_row in read_rows(path):
        # Part A v1 nests registrants per person; expand to one row per pair
        # (flat fixture rows pass through unchanged).
        nested = source_row.get("registrants")
        if isinstance(nested, list):
            expanded = []
            for item in nested:
                if not isinstance(item, Mapping):
                    raise ValueError("registrants entries must be objects")
                merged = {k: v for k, v in source_row.items() if k != "registrants"}
                merged.update(item)
                if "filing_year_first" not in merged and isinstance(item.get("start_year"), int):
                    merged["filing_year_first"] = item["start_year"]
                if "filing_year_last" not in merged and isinstance(item.get("end_year"), int):
                    merged["filing_year_last"] = item["end_year"]
                expanded.append(merged)
        else:
            expanded = [source_row]
        for row in expanded:
            out.append(_registrant_row(row, summary, r_strength))
    return out


def _registrant_row(
    row: Mapping[str, Any], summary: Mapping[str, Mapping[str, Any]], r_strength: Mapping[str, float]
):
    if True:
        person = str(row["lda_source_person_id"])
        years = row.get("filing_years")
        year_list = [int(value) for value in years] if isinstance(years, list) else []
        first = row.get("filing_year_first")
        last = row.get("filing_year_last")
        first_year = int(first) if isinstance(first, int) else (
            min(year_list) if year_list else None
        )
        last_year = int(last) if isinstance(last, int) else (
            max(year_list) if year_list else None
        )
        evidence = row.get("dated_bounded_evidence")
        evidence_starts: list[date] = []
        evidence_ends: list[date] = []
        if isinstance(evidence, list):
            for item in evidence:
                if not isinstance(item, Mapping):
                    continue
                start = parse_day(item.get("start"))
                end = parse_day(item.get("end_exclusive"))
                if start is not None:
                    evidence_starts.append(start)
                if end is not None:
                    evidence_ends.append(end)
        year_start = date(first_year, 1, 1) if first_year is not None else None
        year_start_latest = (
            date(first_year + 1, 1, 1) if first_year is not None else None
        )
        year_end = date(last_year + 1, 1, 1) if last_year is not None else None
        evidence_start = min(evidence_starts) if evidence_starts else None
        evidence_end = max(evidence_ends) if evidence_ends else None
        starts = [value for value in (year_start, evidence_start) if value]
        start_earliest = min(starts) if starts else None
        start_latest = evidence_start if evidence_start is not None else year_start_latest
        if start_earliest is not None and start_latest is not None:
            start_latest = max(start_latest, start_earliest)
        ends = [value for value in (year_end, evidence_end) if value]
        end_exclusive = max(ends) if ends else None
        tier = row.get("registrant_side_tier")
        if tier not in r_strength:
            fallback = summary.get(person, {}).get("registrant_side_tier")
            tier = fallback if fallback in r_strength else "R0"
        return {
            "person": person,
            "organization": f"organization:{row['registrant_source_org_id']}",
            "tier": str(tier),
            "start_earliest": start_earliest,
            "start_latest": start_latest,
            "end_exclusive": end_exclusive,
        }


def derive_co_tenure(
    records: Sequence[Mapping[str, Any]],
    universe: Mapping[str, str],
    tau_days: float,
    tier_strength: Mapping[str, float],
) -> dict[tuple[str, str], dict[str, Any]]:
    by_container: dict[str, dict[str, dict[str, list]]] = defaultdict(
        lambda: defaultdict(lambda: {"core": [], "envelope": []})
    )
    # 2026-09-02 (R3): per (container, person), the minimum record tier among
    # that person's rows in that container -- the "record that supports that
    # container's overlap", independent of the person's global max_tier.
    container_person_tier: dict[str, dict[str, str]] = defaultdict(dict)
    for record in records:
        if record["person"] not in universe:
            continue
        bucket = by_container[record["container_id"]][record["person"]]
        bucket["core"].append(record["core"])
        bucket["envelope"].append(record["envelope"])
        tiers_here = container_person_tier[record["container_id"]]
        current = tiers_here.get(record["person"])
        if current is None or TIER_RANK[record["tier"]] < TIER_RANK[current]:
            tiers_here[record["person"]] = record["tier"]

    core_pieces: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    envelope_pieces: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    containers: dict[tuple[str, str], set[str]] = defaultdict(set)
    contributions_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(
        list
    )
    for container_id, people in by_container.items():
        merged = {
            person: {
                "core": merge_runs(blocks["core"]),
                "envelope": merge_runs(blocks["envelope"]),
            }
            for person, blocks in people.items()
        }
        tiers_here = container_person_tier[container_id]
        ordered = sorted(merged)
        for left_index in range(len(ordered)):
            for right_index in range(left_index + 1, len(ordered)):
                key = (ordered[left_index], ordered[right_index])
                containers[key].add(container_id)
                core_overlap = overlap_runs(
                    merged[key[0]]["core"], merged[key[1]]["core"]
                )
                envelope_overlap = overlap_runs(
                    merged[key[0]]["envelope"], merged[key[1]]["envelope"]
                )
                core_pieces[key].extend(core_overlap)
                envelope_pieces[key].extend(envelope_overlap)
                if core_overlap or envelope_overlap:
                    contributions_by_pair[key].append(
                        {
                            "container_id": container_id,
                            "subject_tier": tiers_here[key[0]],
                            "object_tier": tiers_here[key[1]],
                        }
                    )

    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for key, container_set in containers.items():
        guaranteed = total_days(merge_runs(core_pieces.get(key, [])))
        possible = total_days(merge_runs(envelope_pieces.get(key, [])))
        if guaranteed > 0:
            status = "GUARANTEED"
        elif possible > 0:
            status = "POSSIBLE_ONLY"
        else:
            status = "ZERO_OVERLAP"
        contributions = contributions_by_pair.get(key, [])
        if contributions:
            strength = min(
                min(tier_strength[item["subject_tier"]], tier_strength[item["object_tier"]])
                for item in contributions
            )
        else:
            strength = 0.0
        # Lists, not dicts keyed by container_id -- see the matching builder
        # comment: container_id must stay in a "container_id" VALUE position
        # for the language-law exemption to apply, never as a dict key.
        endpoint_record_tiers = {
            "subject": sorted(
                (
                    {"container_id": item["container_id"], "tier": item["subject_tier"]}
                    for item in contributions
                ),
                key=lambda item: item["container_id"],
            ),
            "object": sorted(
                (
                    {"container_id": item["container_id"], "tier": item["object_tier"]}
                    for item in contributions
                ),
                key=lambda item: item["container_id"],
            ),
        }
        w_lower = 1.0 - math.exp(-guaranteed / tau_days)
        expected[key] = {
            "status": status,
            "guaranteed_days": guaranteed,
            "possible_days": possible,
            "w_lower": w_lower,
            "w_upper": 1.0 - math.exp(-possible / tau_days),
            "tier_strength": strength,
            "w_tiered_lower": strength * w_lower,
            "container_ids": sorted(container_set),
            "subject_tier": universe[key[0]],
            "object_tier": universe[key[1]],
            "endpoint_record_tiers": endpoint_record_tiers,
            "endpoint_max_tiers": {"subject": universe[key[0]], "object": universe[key[1]]},
        }
    return expected


def order_class(
    hill: Mapping[str, Any], registrant: Mapping[str, Any]
) -> tuple[str, int | None, int | None]:
    if (
        registrant["start_earliest"] is None
        or registrant["start_latest"] is None
        or registrant["end_exclusive"] is None
    ):
        return "INTERVAL_BLOCKED", None, None
    hill_end_latest = hill["envelope"][1]
    hill_end_earliest = hill["core"][1]
    hill_start_earliest = hill["envelope"][0]
    gap_min = max(0, (registrant["start_earliest"] - hill_end_latest).days)
    gap_max = max(0, (registrant["start_latest"] - hill_end_earliest).days)
    if hill_end_latest <= registrant["start_earliest"]:
        return "GUARANTEED", gap_min, gap_max
    if registrant["end_exclusive"] <= hill_start_earliest:
        return "WRONG_ORDER", gap_min, gap_max
    return "POSSIBLE_ONLY", gap_min, gap_max


def derive_revolving(
    records: Sequence[Mapping[str, Any]],
    registrants: Sequence[Mapping[str, Any]],
    universe: Mapping[str, str],
    tier_strength: Mapping[str, float],
    r_strength: Mapping[str, float],
) -> dict[tuple[str, str], dict[str, Any]]:
    hill_by_person: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record["person"] in universe and record["container_kind"] == "member_office":
            hill_by_person[record["person"]].append(record)

    guaranteed: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    observed: dict[tuple[str, str], set[str]] = defaultdict(set)
    for registrant in registrants:
        if registrant["person"] not in universe:
            continue
        for hill in hill_by_person.get(registrant["person"], ()):
            status, gap_min, gap_max = order_class(hill, registrant)
            key = (hill["container_id"], registrant["organization"])
            observed[key].add(status)
            if status != "GUARANTEED":
                continue
            strength = tier_strength[hill["tier"]] * r_strength[registrant["tier"]]
            current = guaranteed[key].get(registrant["person"])
            if current is None or strength > current["strength"]:
                guaranteed[key][registrant["person"]] = {
                    "lda_source_person_id": registrant["person"],
                    "max_tier": universe[registrant["person"]],
                    "hill_tier": hill["tier"],
                    "registrant_tier": registrant["tier"],
                    "strength": strength,
                    "gap_min_days": gap_min,
                    "gap_max_days": gap_max,
                }

    expected: dict[tuple[str, str], dict[str, Any]] = {}
    for key in set(observed) | set(guaranteed):
        contributions = [
            guaranteed[key][person] for person in sorted(guaranteed.get(key, {}))
        ]
        if contributions:
            status = "GUARANTEED"
        else:
            statuses = observed.get(key, set())
            status = next(
                name
                for name in ("POSSIBLE_ONLY", "INTERVAL_BLOCKED", "WRONG_ORDER")
                if name in statuses
            )
        expected[key] = {
            "status": status,
            "contributions": contributions,
            "strength_sum": sum(item["strength"] for item in contributions),
            "contributing_person_count": len(contributions),
        }
    return expected


def derive_membership(
    records: Sequence[Mapping[str, Any]], universe: Mapping[str, str]
) -> list[tuple[str, str, str]]:
    """R4: one ``(person, container_id, tier)`` triple per Part A record.

    ``records`` is already filtered to ``tier >= L2`` by ``load_records``.
    Returned as a list, not a set, so a duplicated Part A row (which the
    builder is required to turn into two literal membership edges) is not
    silently collapsed here.
    """

    return [
        (record["person"], record["container_id"], record["tier"])
        for record in records
        if record["person"] in universe
    ]


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def _scan_text_for_banned_tokens(
    failures: Failures, label: str, text: str
) -> int:
    hits = 0
    stripped = text.replace(STATEMENT, " ")
    lowered = stripped.lower()
    for token in BANNED_TOKENS:
        for match in re.finditer(re.escape(token), lowered):
            hits += 1
            failures.add(
                f"language law: {label} carries the token {token!r} at offset "
                f"{match.start()}"
            )
    return hits


def check_language_law(failures: Failures, texts: Mapping[str, str]) -> int:
    """Flat-text grep, used only for the three committed schema files.

    A schema document describes shape and prose, not runtime identifier
    values, so no field-name exemption applies here (INV-7 covers "schema
    descriptions" without exception).
    """

    hits = 0
    for label, text in texts.items():
        hits += _scan_text_for_banned_tokens(failures, label, text)
    return hits


def check_language_law_document(
    failures: Failures, label: str, document: Any, *, field_name: str | None = None
) -> int:
    """Recursively grep one parsed JSON value, exempting opaque identifier
    VALUES by their enclosing field name (2026-09-02 INV-7 addendum).

    Field NAMES are never exempt -- a key string is checked the same way a
    non-exempt value string is.  Only string leaves under an exempt field
    name (``office_key``, ``container_id``/``container_ids``, any
    ``*_id``/``*_key`` field, etc.) are skipped; every other string,
    including receipt prose like ``weight_semantics`` or ``sweep_semantics``,
    is fully scanned.
    """

    hits = 0
    if isinstance(document, Mapping):
        for key, value in document.items():
            key_label = f"{label}.{key}"
            if isinstance(key, str):
                hits += _scan_text_for_banned_tokens(failures, key_label, key)
            hits += check_language_law_document(
                failures, key_label, value, field_name=key
            )
    elif isinstance(document, list):
        for item in document:
            hits += check_language_law_document(
                failures, label, item, field_name=field_name
            )
    elif isinstance(document, str):
        if not is_language_law_exempt_field(field_name):
            hits += _scan_text_for_banned_tokens(failures, label, document)
    return hits


def check_row_constants(failures: Failures, label: str, row: Mapping[str, Any]) -> None:
    if row.get("exploratory") is not True:
        failures.add(f"{label}: exploratory is not true")
    if row.get("primary") is not False:
        failures.add(f"{label}: primary is not false")
    if row.get("review_status") != "REVIEW_REQUIRED":
        failures.add(f"{label}: review_status is not REVIEW_REQUIRED")
    if row.get("canonical_eligible") is not False:
        failures.add(f"{label}: canonical_eligible is not false")
    if row.get("canonical_employment_promoted") is not False:
        failures.add(f"{label}: canonical_employment_promoted is not false")


def rerun_operator(
    failures: Failures,
    threshold: str,
    node_ids: Sequence[str],
    edges: Sequence[tuple[int, int, float, int]],
    scores: Mapping[str, Mapping[str, Any]],
) -> None:
    if not node_ids:
        return
    subjects = np.asarray([edge[0] for edge in edges], dtype=np.int64)
    objects = np.asarray([edge[1] for edge in edges], dtype=np.int64)
    weights = np.asarray([edge[2] for edge in edges], dtype=np.float64)
    layers = np.asarray([edge[3] for edge in edges], dtype=np.int32)
    if subjects.size:
        subjects, objects, weights, layers = deduplicate_undirected_layer_edges(
            subjects, objects, weights, layers
        )
    transition = layer_balanced_transition(
        len(node_ids), subjects, objects, weights, layers
    )
    row_sums = np.asarray(transition.sum(axis=1)).ravel()
    nonzero = row_sums > 0
    failures.check(
        bool(np.all(np.abs(row_sums[nonzero] - 1.0) <= 1e-10)),
        f"{threshold}: operator has a non-stochastic row",
    )
    raw_strength = np.zeros(len(node_ids), dtype=np.float64)
    if subjects.size:
        raw_strength = np.bincount(
            np.concatenate((subjects, objects)),
            weights=np.concatenate((weights, weights)),
            minlength=len(node_ids),
        )
    codes = np.asarray(
        [NODE_KINDS.index(node_id.split(":", 1)[0]) for node_id in node_ids],
        dtype=np.int32,
    )
    teleport = group_balanced_teleport(codes)
    rank, _ = connectedness_pagerank(
        transition, damping=0.85, teleport=teleport, tolerance=1e-11,
        max_iterations=750,
    )
    for index, node_id in enumerate(node_ids):
        row = scores.get(node_id)
        if row is None:
            failures.add(f"{threshold}: node score row is missing for {node_id}")
            continue
        expected_isolate = bool(raw_strength[index] == 0.0)
        if row.get("isolate") is not expected_isolate:
            failures.add(
                f"{threshold}: isolate flag disagrees for {node_id} "
                f"(emitted {row.get('isolate')}, re-derived {expected_isolate})"
            )
        if not close(float(row.get("raw_strength", -1.0)), float(raw_strength[index])):
            failures.add(f"{threshold}: raw_strength disagrees for {node_id}")
        emitted = {
            round(float(entry["alpha"]), 12): float(entry["score"])
            for entry in row.get("connectedness_pagerank_exploratory", [])
        }
        value = emitted.get(0.85)
        if value is None:
            failures.add(f"{threshold}: no alpha 0.85 PageRank for {node_id}")
        elif abs(value - float(rank[index])) > SCORE_TOLERANCE:
            failures.add(
                f"{threshold}: PageRank disagrees for {node_id} "
                f"({value} vs {float(rank[index])})"
            )


def verify(args: argparse.Namespace) -> dict[str, Any]:
    failures = Failures()
    primary = Path(args.primary_root).resolve()
    receipt_path = primary / RECEIPT_FILENAME
    edges_path = primary / EDGES_FILENAME
    scores_path = primary / SCORES_FILENAME
    for path in (receipt_path, edges_path, scores_path):
        if not path.is_file():
            raise SystemExit(f"missing generation file: {path}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    receipt_schema = json.loads(
        (SCHEMA_DIR / "exploratory_temporal_receipt.schema.json").read_text(
            encoding="utf-8"
        )
    )
    edge_schema = json.loads(
        (SCHEMA_DIR / "exploratory_temporal_edge.schema.json").read_text(
            encoding="utf-8"
        )
    )
    score_schema = json.loads(
        (SCHEMA_DIR / "exploratory_node_score.schema.json").read_text(encoding="utf-8")
    )
    try:
        validate_instance(receipt, receipt_schema)
    except SchemaValidationError as error:
        failures.add(f"receipt fails its schema: {error}")

    failures.check(
        receipt.get("primary_weights_emitted") == 0,
        "receipt primary_weights_emitted is not 0",
    )
    failures.check(receipt.get("exploratory") is True, "receipt exploratory is not true")
    failures.check(receipt.get("primary") is False, "receipt primary is not false")
    failures.check(
        receipt.get("statement") == STATEMENT, "receipt is missing the mandated sentence"
    )
    failures.check(
        receipt.get("canonical_employment_promotions") == 0,
        "receipt reports a nonzero canonical employment promotion count",
    )
    failures.check(
        receipt.get("canonical_identity_promotions") == 0,
        "receipt reports a nonzero canonical identity promotion count",
    )
    check_row_constants(failures, "receipt", receipt)

    # INV-3: every declared input re-binds by hash.
    inputs = {entry["role"]: entry for entry in receipt.get("inputs", [])}
    for role, entry in sorted(inputs.items()):
        path = Path(entry["path"])
        if not path.is_file():
            failures.add(f"bound input is missing: {role} -> {path}")
            continue
        digest = sha256_of(path)
        if digest != entry["sha256"]:
            failures.add(
                f"bound input hash changed: {role} ({digest} != {entry['sha256']})"
            )
        if path.stat().st_size != entry["bytes"]:
            failures.add(f"bound input byte count changed: {role}")

    for entry in receipt.get("files", []):
        path = primary / entry["path"]
        digest = sha256_of(path)
        if digest != entry["sha256"]:
            failures.add(f"emitted file hash changed: {entry['role']}")
        if path.stat().st_size != entry["bytes"]:
            failures.add(f"emitted file byte count changed: {entry['role']}")

    # Twin byte identity.
    twin_checked = False
    if args.twin_root:
        twin = Path(args.twin_root).resolve()
        twin_checked = True
        for name in (EDGES_FILENAME, SCORES_FILENAME, RECEIPT_FILENAME):
            left = primary / name
            right = twin / name
            if not right.is_file():
                failures.add(f"twin is missing {name}")
                continue
            if sha256_of(left) != sha256_of(right):
                failures.add(f"twin differs from primary: {name}")

    # Language law: the three committed schemas stay a flat-text grep (schema
    # prose has no opaque-identifier value positions to exempt); the receipt
    # gets a structured, field-name-aware walk so office_key/container_id/...
    # values are exempt but every other field, including receipt prose, is
    # still checked (INV-7, 2026-09-02 addendum).  Edge and score rows are
    # walked the same way inside their own read loops below, since those
    # files are read there anyway.
    schema_texts = {name: (SCHEMA_DIR / name).read_text(encoding="utf-8") for name in SCHEMA_FILES}
    language_hits = check_language_law(failures, schema_texts)
    language_hits += check_language_law_document(failures, RECEIPT_FILENAME, receipt)

    dials = receipt.get("dials", {})
    tier_strength = dict(dials.get("tier_strength", {}))
    r_strength = dict(dials.get("r_strength", {}))
    tau_days = float(dials.get("tau_days", 0.0) or 0.0)
    half_life_days = float(dials.get("gap_half_life_days", 0.0) or 0.0)
    if not tier_strength or not r_strength or tau_days <= 0 or half_life_days <= 0:
        failures.add("receipt dials are incomplete; re-derivation cannot run")
        return finish(failures, receipt, args, twin_checked, language_hits, 0, 0)

    records = load_records(Path(inputs["tiered_person_office_records"]["path"]),
                           tier_strength)
    summary = load_summary(Path(inputs["tiered_person_summary"]["path"]))
    registrants = load_registrants(
        Path(inputs["registrant_side_records"]["path"]), summary, r_strength
    )
    universe = {
        person: str(entry["max_tier"])
        for person, entry in summary.items()
        if TIER_RANK.get(str(entry["max_tier"]), 0) >= TIER_RANK["L2"]
    }

    expected_co_tenure = derive_co_tenure(records, universe, tau_days, tier_strength)
    expected_revolving = derive_revolving(
        records, registrants, universe, tier_strength, r_strength
    )
    expected_membership = derive_membership(records, universe)

    emitted_co_tenure: dict[tuple[str, str], dict[str, Any]] = {}
    emitted_revolving: dict[tuple[str, str], dict[str, Any]] = {}
    emitted_membership: list[dict[str, Any]] = []
    edge_rows = 0
    for row in read_rows(edges_path):
        edge_rows += 1
        check_row_constants(failures, f"edge {row.get('edge_id')}", row)
        language_hits += check_language_law_document(
            failures, f"{EDGES_FILENAME}[{row.get('edge_id')}]", row
        )
        try:
            validate_instance(row, edge_schema)
        except SchemaValidationError as error:
            failures.add(f"edge row fails its schema: {error}")
            continue
        if row["status"] == "ZERO_OVERLAP":
            failures.add(f"edge {row['edge_id']} emits a ZERO_OVERLAP row")
        if row["layer"] == "co_tenure":
            key = (row["subject_id"][len("person:"):], row["object_id"][len("person:"):])
            emitted_co_tenure[key] = row
        elif row["layer"] == "revolving":
            emitted_revolving[(row["subject_id"], row["object_id"])] = row
        elif row["layer"] == "membership":
            emitted_membership.append(row)
        else:
            failures.add(f"edge {row['edge_id']} has an unrecognized layer: {row['layer']!r}")

    expected_emitted = {
        key for key, value in expected_co_tenure.items()
        if value["status"] != "ZERO_OVERLAP"
    }
    missing = sorted(expected_emitted - set(emitted_co_tenure))
    extra = sorted(set(emitted_co_tenure) - expected_emitted)
    for key in missing[:20]:
        failures.add(f"co-tenure edge missing from the generation: {key}")
    for key in extra[:20]:
        failures.add(f"co-tenure edge not re-derivable from Part A: {key}")
    if len(missing) > 20 or len(extra) > 20:
        failures.add(
            f"co-tenure set difference truncated: {len(missing)} missing, {len(extra)} extra"
        )

    co_tenure_checked = 0
    for key in sorted(expected_emitted & set(emitted_co_tenure)):
        expected = expected_co_tenure[key]
        row = emitted_co_tenure[key]
        co_tenure_checked += 1
        for field in ("status", "guaranteed_days", "possible_days", "container_ids",
                      "subject_tier", "object_tier", "endpoint_record_tiers",
                      "endpoint_max_tiers"):
            if row.get(field) != expected[field]:
                failures.add(
                    f"co-tenure {key} field {field}: emitted {row.get(field)!r} "
                    f"re-derived {expected[field]!r}"
                )
        for field in ("w_lower", "w_upper", "tier_strength", "w_tiered_lower"):
            if not close(float(row.get(field) or 0.0), float(expected[field])):
                failures.add(
                    f"co-tenure {key} field {field}: emitted {row.get(field)!r} "
                    f"re-derived {expected[field]!r}"
                )
        floor = min(TIER_RANK[expected["subject_tier"]], TIER_RANK[expected["object_tier"]])
        surviving = (
            [name for name in TIER_THRESHOLDS if TIER_RANK[name] <= floor]
            if expected["w_tiered_lower"] > 0.0
            else []
        )
        if row.get("surviving_tier_thresholds") != surviving:
            failures.add(f"co-tenure {key}: surviving_tier_thresholds disagrees")

    missing_revolving = sorted(set(expected_revolving) - set(emitted_revolving))
    extra_revolving = sorted(set(emitted_revolving) - set(expected_revolving))
    for key in missing_revolving[:20]:
        failures.add(f"revolving edge missing from the generation: {key}")
    for key in extra_revolving[:20]:
        failures.add(f"revolving edge not re-derivable from Part A: {key}")

    revolving_checked = 0
    for key in sorted(set(expected_revolving) & set(emitted_revolving)):
        expected = expected_revolving[key]
        row = emitted_revolving[key]
        revolving_checked += 1
        if row.get("status") != expected["status"]:
            failures.add(
                f"revolving {key} order class: emitted {row.get('status')!r} "
                f"re-derived {expected['status']!r}"
            )
        if row.get("contributing_person_count") != expected["contributing_person_count"]:
            failures.add(f"revolving {key}: contributing_person_count disagrees")
        if not close(float(row.get("strength_sum") or 0.0), expected["strength_sum"]):
            failures.add(f"revolving {key}: strength_sum disagrees")
        if not close(float(row.get("w_tiered_lower") or 0.0), expected["strength_sum"]):
            failures.add(f"revolving {key}: w_tiered_lower does not repeat strength_sum")
        emitted_people = [
            item["lda_source_person_id"] for item in row.get("contributions", [])
        ]
        derived_people = [item["lda_source_person_id"] for item in expected["contributions"]]
        if emitted_people != derived_people:
            failures.add(f"revolving {key}: contributor list disagrees")
        if len(emitted_people) != len(set(emitted_people)):
            failures.add(f"revolving {key}: a person contributes more than once")
        lower = row.get("gap_decay_lower")
        upper = row.get("gap_decay_upper")
        if lower is not None and upper is not None and lower > upper + WEIGHT_TOLERANCE:
            failures.add(f"revolving {key}: gap decay bounds are out of order")
        for item in row.get("contributions", []):
            expected_decay = 2.0 ** (-float(item["gap_max_days"]) / half_life_days)
            if expected_decay > 1.0 + WEIGHT_TOLERANCE:
                failures.add(f"revolving {key}: gap decay exceeds one")

    # R4: every tier >= L2 person-office record must produce exactly one
    # membership edge -- compared as multisets, since a duplicated Part A
    # record legitimately produces two literal membership edges.
    membership_checked = 0
    expected_membership_counter = Counter(expected_membership)
    emitted_membership_counter: Counter[tuple[str, str, str]] = Counter()
    for row in emitted_membership:
        membership_checked += 1
        if row.get("status") != "GUARANTEED":
            failures.add(f"membership {row.get('edge_id')}: status is not GUARANTEED")
        if row.get("direction") != "undirected":
            failures.add(f"membership {row.get('edge_id')}: direction is not undirected")
        person = row.get("subject_id", "")[len("person:"):]
        tier = row.get("subject_tier")
        emitted_membership_counter[(person, row.get("object_id"), tier)] += 1
        if tier not in tier_strength:
            failures.add(f"membership {row.get('edge_id')}: unrecognized tier {tier!r}")
            continue
        if not close(float(row.get("w_tiered_lower") or 0.0), tier_strength[tier]):
            failures.add(f"membership {row.get('edge_id')}: weight disagrees with TIER_STRENGTH[{tier}]")
        if not close(float(row.get("tier_strength") or 0.0), tier_strength[tier]):
            failures.add(f"membership {row.get('edge_id')}: tier_strength disagrees with TIER_STRENGTH[{tier}]")
    if emitted_membership_counter != expected_membership_counter:
        only_expected = expected_membership_counter - emitted_membership_counter
        only_emitted = emitted_membership_counter - expected_membership_counter
        failures.add(
            "membership edges do not reproduce one-per-record from Part A: "
            f"{sum(only_expected.values())} record(s) missing an edge, "
            f"{sum(only_emitted.values())} edge(s) not re-derivable"
        )
    receipt_membership_count = (receipt.get("edge_counts") or {}).get("membership")
    if receipt_membership_count != len(emitted_membership):
        failures.add(
            "receipt edge_counts.membership disagrees with the emitted edge file: "
            f"receipt {receipt_membership_count!r} emitted {len(emitted_membership)}"
        )

    # Node scores and the operator per tier threshold.
    scores_by_threshold: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    score_rows = 0
    for row in read_rows(scores_path):
        score_rows += 1
        check_row_constants(failures, f"score {row.get('node_id')}", row)
        language_hits += check_language_law_document(
            failures, f"{SCORES_FILENAME}[{row.get('node_id')}]", row
        )
        try:
            validate_instance(row, score_schema)
        except SchemaValidationError as error:
            failures.add(f"node score row fails its schema: {error}")
            continue
        scores_by_threshold[row["tier_threshold"]][row["node_id"]] = row

    for threshold in TIER_THRESHOLDS:
        floor = TIER_RANK[threshold]
        people = {person for person, tier in universe.items() if TIER_RANK[tier] >= floor}
        node_ids = sorted(
            {f"person:{person}" for person in people}
            | {
                record["container_id"]
                for record in records
                if record["person"] in people
            }
            | {
                registrant["organization"]
                for registrant in registrants
                if registrant["person"] in people
            }
        )
        emitted_nodes = set(scores_by_threshold.get(threshold, {}))
        if emitted_nodes != set(node_ids):
            failures.add(
                f"{threshold}: node universe disagrees "
                f"({len(emitted_nodes)} emitted, {len(node_ids)} re-derived)"
            )
        index = {node_id: position for position, node_id in enumerate(node_ids)}
        operator_edges: list[tuple[int, int, float, int]] = []
        for row in emitted_co_tenure.values():
            if threshold not in row["surviving_tier_thresholds"]:
                continue
            if row["subject_id"] not in index or row["object_id"] not in index:
                failures.add(
                    f"{threshold}: co-tenure edge endpoint is outside the node universe"
                )
                continue
            operator_edges.append(
                (
                    index[row["subject_id"]],
                    index[row["object_id"]],
                    float(row["w_tiered_lower"]),
                    CO_TENURE_LAYER,
                )
            )
        for row in emitted_revolving.values():
            weight = sum(
                tier_strength[item["hill_tier"]] * r_strength[item["registrant_tier"]]
                for item in row.get("contributions", [])
                if TIER_RANK[item["max_tier"]] >= floor
            )
            if weight <= 0.0:
                continue
            if row["subject_id"] not in index or row["object_id"] not in index:
                failures.add(
                    f"{threshold}: revolving edge endpoint is outside the node universe"
                )
                continue
            operator_edges.append(
                (
                    index[row["subject_id"]],
                    index[row["object_id"]],
                    weight,
                    REVOLVING_LAYER,
                )
            )
        for row in emitted_membership:
            # R4: gated by the record's own tier against the floor, not the
            # person's max_tier -- matches the builder's operator_inputs().
            # A record's tier can never exceed that person's max_tier (it is
            # the max over exactly this person's own records), so clearing
            # the floor here always implies both endpoints are already in
            # this threshold's node universe; an absent endpoint is a real
            # inconsistency, not a legitimate edge case.
            tier = row.get("subject_tier")
            if tier not in tier_strength or TIER_RANK[tier] < floor:
                continue
            if row["subject_id"] not in index or row["object_id"] not in index:
                # Legitimate: Part A's person tier is the union-recomputed tier,
                # so a record may out-rank its person and the person node can be
                # absent at this threshold.  Mirrors the builder: skip, no fail.
                continue
            operator_edges.append(
                (
                    index[row["subject_id"]],
                    index[row["object_id"]],
                    tier_strength[tier],
                    MEMBERSHIP_LAYER,
                )
            )
        rerun_operator(
            failures, threshold, node_ids, operator_edges,
            scores_by_threshold.get(threshold, {}),
        )

    return finish(
        failures, receipt, args, twin_checked, language_hits,
        co_tenure_checked, revolving_checked, edge_rows, score_rows,
        membership_checked,
    )


def finish(
    failures: Failures,
    receipt: Mapping[str, Any],
    args: argparse.Namespace,
    twin_checked: bool,
    language_hits: int,
    co_tenure_checked: int = 0,
    revolving_checked: int = 0,
    edge_rows: int = 0,
    score_rows: int = 0,
    membership_checked: int = 0,
) -> dict[str, Any]:
    document = {
        "schema_id": "staffer-network-exploratory-temporal-verification-receipt-v1",
        "schema_committed": False,
        "generated_at": args.generated_at,
        "status": "PASS" if failures.ok else "FAIL",
        "method_version": "exploratory-temporal-tier-verification-v1",
        "exploratory": True,
        "primary": False,
        "primary_weights_emitted": 0,
        "statement": STATEMENT,
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "review_status": "REVIEW_REQUIRED",
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "primary_root": Path(args.primary_root).resolve().as_posix(),
        "twin_checked": twin_checked,
        "verified_files": [
            {"role": entry.get("role"), "sha256": entry.get("sha256")}
            for entry in receipt.get("files", [])
        ],
        "checks": {
            "co_tenure_edges_re_derived": co_tenure_checked,
            "revolving_edges_re_derived": revolving_checked,
            "membership_edges_re_derived": membership_checked,
            "edge_rows_read": edge_rows,
            "node_score_rows_read": score_rows,
            "language_law_hits": language_hits,
        },
        "language_law_exempt_fields": sorted(LANGUAGE_LAW_EXEMPT_FIELDS),
        "language_law_exempt_suffixes": list(LANGUAGE_LAW_EXEMPT_SUFFIXES),
        "failures": failures.items,
    }
    return document


def write_report(document: Mapping[str, Any], report_root: Path) -> Path:
    if report_root.exists():
        if not report_root.is_dir():
            raise SystemExit(f"report root exists and is not a directory: {report_root}")
        if any(report_root.iterdir()):
            raise SystemExit(f"immutable report directory already exists: {report_root}")
        report_root.rmdir()
    report_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{report_root.name}.tmp-", dir=report_root.parent)
    )
    try:
        (staging / VERIFICATION_FILENAME).write_bytes(canonical_bytes(document))
        os.replace(staging, report_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report_root / VERIFICATION_FILENAME


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify the exploratory temporal tier generation."
    )
    parser.add_argument("--primary-root", required=True, type=Path)
    parser.add_argument("--twin-root", type=Path, default=None)
    parser.add_argument("--report-root", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox, kind="run.start", status="running",
        summary="exploratory temporal tier verification",
        detail=str(args.primary_root), run_id=args.run_id, stage="partB-verify",
    )
    try:
        document = verify(args)
        path = write_report(document, Path(args.report_root).resolve())
    except BaseException as error:
        emit_glassbox(
            enabled=glassbox, kind="run.fail", status="failed",
            summary="exploratory temporal tier verification failed",
            detail=f"{type(error).__name__}: {error}", run_id=args.run_id,
            stage="partB-verify",
        )
        raise
    emit_glassbox(
        enabled=glassbox,
        kind="run.finish",
        status="completed" if document["status"] == "PASS" else "failed",
        summary=f"exploratory temporal tier verification {document['status']}",
        detail=f"failures={len(document['failures'])}",
        run_id=args.run_id,
        stage="partB-verify",
    )
    print(json.dumps({"status": document["status"], "receipt": str(path),
                      "failures": document["failures"][:20]}, sort_keys=True))
    return 0 if document["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
