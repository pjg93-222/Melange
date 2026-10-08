#!/usr/bin/env python3
"""Build the review-only exploratory temporal tier over the tiered sidecar.

Scope
-----
This is Part B of TIERED_SIDECAR_SPEC_20260902.  It consumes the four Part A
outputs plus the Part A receipt, hash-binds every one of them, and emits two
NDJSON files and one receipt into a fresh immutable generation directory.  It
writes nothing into ``data/staffer_network/`` and writes no ``*_current.json``
pointer.  Every emitted row carries ``exploratory: true``, ``primary: false``,
``review_status: "REVIEW_REQUIRED"``, ``canonical_eligible: false`` and
``canonical_employment_promoted: false``; the receipt carries
``primary_weights_emitted: 0``.  Nothing here is an identity finding.

Reviewed mathematics is reused, never reimplemented.  Interval overlap comes
from ``fec/staffer_network/intervals.py``; the transition operator, PageRank,
the component-local eigenvector and bridging diversity come from
``fec/staffer_network/network_math.py``.  ``employment_history.py``,
``employment_promotion.py``, ``lda_composite_repair.py`` and
``lda_source_native_corpus.py`` are never imported (INV-9).

Part A input shapes consumed
----------------------------
Part A had not been built when this module was written, so the fields below
are the shapes this builder reads.  Every field not listed is ignored, and
every optional field has a documented fallback, so a Part A row that carries
more than this still loads.

``tiered_person_office_records.ndjson.gz`` (one row per contiguous run of a
(person, chamber, office_key) container):

* ``lda_source_person_id`` (string, required)
* ``tier`` (string, required; rows outside ``L2..L5`` are dropped)
* ``office_key`` (string, required)
* ``chamber`` (string, optional, default ``"unknown"``)
* ``member_bioguide`` (string or null, optional)
* ``container_kind`` (string, optional; when absent it is inferred as
  ``member_office`` if ``member_bioguide`` is set, else ``unresolved``)
* ``core`` = ``{"start_latest": ISO date, "end_earliest": ISO date}``
  (required; ``end_earliest`` is the EXCLUSIVE half-open end)
* ``envelope`` = ``{"start_earliest": ISO date, "end_latest": ISO date}``
  (optional; when absent the core run is reused, since the envelope always
  contains the core; ``end_latest`` is the EXCLUSIVE half-open end)

``tiered_person_summary_25340.ndjson.gz``:

* ``lda_source_person_id`` (string, required)
* ``max_tier`` (string, required; ``L0``/``L1`` people leave the node universe)
* ``registrant_side_tier`` (``R0``/``R1``/``R2`` or null, optional)

``registrant_side_records.ndjson.gz`` (one row per (person, registrant org) —
the simplest JSON-serialisable form of the spec's "per person: LDA
registrant(s) ..."):

* ``lda_source_person_id`` (string, required)
* ``registrant_source_org_id`` (string, required)
* ``registrant_name`` (string, optional, unused)
* ``filing_year_first`` / ``filing_year_last`` (integer or null, optional;
  when absent they fall back to ``min``/``max`` of ``filing_years``)
* ``filing_years`` (array of integers, optional)
* ``registrant_side_tier`` (``R0``/``R1``/``R2`` or null, optional; falls back
  to the person summary value, then to ``R0`` with a receipt counter)
* ``dated_bounded_evidence`` (optional array of
  ``{"start": ISO date, "end_exclusive": ISO date}``, the R2 dated evidence)
* ``hill_registrant_order`` (optional; read for nothing — the order class is
  always re-derived here)

``filer_asserted_year_episodes.ndjson.gz`` is hash-bound and row-counted only.
Its rows are single-author, year-grain assertions and carry no payroll-observed
calendar, so they contribute no edge weight.

``tiered_corroboration_receipt.json`` is hash-bound and gated: ``status`` must
be ``PASS``; when present, ``canonical_employment_promotions``,
``canonical_identity_promotions`` must be 0 and ``promotion_policy`` must be
``REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS``.

Spec ambiguities resolved here (each is stated in the report and the receipt)
-----------------------------------------------------------------------------
1. Half-open convention.  ``core.end_earliest`` and ``envelope.end_latest`` are
   read as EXCLUSIVE ends, matching the lane's ``end_exclusive`` temporal-path
   schema and ``intervals.guaranteed_overlap_days``, which subtracts without a
   ``+1``.
2. Record floor.  Only person-office records with ``tier >= L2`` produce any
   edge in either layer.  An ``L1`` record is ``NAME_MATCH_ONLY`` identity
   status and must not create graph mass.
3. ``tier_strength`` for co-tenure (2026-09-02 addendum, overriding the
   earlier draft of this point) is ``min`` over the two endpoints of the
   *record* tier that actually supports the container's overlap, not either
   person's ``max_tier``.  A pair's overlap can be supported by more than one
   container; each contributing container's per-person record tier is looked
   up independently (the minimum tier across duplicate records for the same
   person in the same container, fail-closed), and the edge's
   ``tier_strength`` is the minimum of ``min(subject, object)`` over every
   contributing container.  ``max_tier`` remains the quantity the
   L2/L3/L4 tier-threshold restriction uses for node and edge presence
   (``subject_tier``/``object_tier`` on the co-tenure edge stay ``max_tier``
   for that reason); only the *weight* now traces to the supporting record.
   Both quantities are emitted per endpoint as ``endpoint_record_tiers``
   (per contributing container) and ``endpoint_max_tiers`` so the two are
   independently auditable.
4. Revolving order class.  The spec's literal test is
   ``core.end_earliest <= registrant_start``.  Math adjudication section 7
   requires the Hill episode to be GUARANTEED to end no later than the industry
   episode begins under the uncertainty bounds, which is
   ``envelope.end_latest <= registrant_start``.  GUARANTEED here uses the
   adjudicated (stricter, fail-closed) test; the spec's literal test is
   reported alongside it as ``revolving_path_status_counts_core_end_variant``
   so the cost of the strict reading is visible and reversible.
5. Registrant start.  ``registrant_start_earliest`` is Jan 1 of the first
   filing year, lowered further by any earlier ``dated_bounded_evidence``
   start, because an earlier possible start makes ORDERED strictly harder to
   reach.  ``registrant_start_latest`` is Jan 1 of the following year (year
   grain) or the exact dated evidence start when one exists.
6. Revolving edges are emitted only for ``container_kind == "member_office"``
   containers, matching "member office -> registrant organization".
7. ``w_lower`` / ``w_upper`` / ``guaranteed_days`` / ``possible_days`` are null
   on revolving rows: the days-to-weight transform is a co-tenure quantity.
   ``w_tiered_lower`` repeats ``strength_sum`` on revolving rows so a single
   field name feeds the operator in both layers.
8. Edge rows are emitted once, at the full ``L2`` universe.  ``L3``/``L4``
   operators are exact restrictions of that edge set: co-tenure weights are
   unchanged and revolving weights are re-summed over the surviving
   contributors, which the emitted ``contributions`` array makes independently
   re-derivable.
9. Sweep clamp.  The +50% arm multiplies each dial entry by 1.5 and clamps to
   1.0, so ``L4`` and ``L5`` both land on 1.0 and ``R2`` does not move.  The
   clamped entries are named per sweep point.
10. (2026-09-02 addendum, superseded) The draft of this point said no
    person-to-container layer would be invented; a third ``membership``
    layer (undirected, person <-> container, one edge per ``tier >= L2``
    person-office record, weight ``TIER_STRENGTH[record tier]``, status
    always ``GUARANTEED``) is now built so people, containers and
    organizations can share components and ``bridging_diversity`` is not
    identically zero.  Unlike co-tenure/revolving, whose L3/L4 restriction
    gates on max_tier (node presence) while the weight stays record-tier
    based, a membership edge's presence at a given tier threshold is gated
    by *that record's own tier* against the floor: the person and container
    nodes can both still be present at L4 (via the person's other, stronger
    records) while this specific L2 membership edge drops out, which keeps
    "the dependence of every score on confirmation strength" (spec section
    on tier-threshold runs) visible for the membership layer the same way it
    already is for co-tenure and revolving weights.  A duplicate person-office
    record (the same person, container and tier reported twice) legitimately
    produces two membership edges, matching "one edge per record"; the
    per-layer degree accumulator gains a membership slot internally but no
    new ``*_degree`` field is added to the node score schema, since the
    ruling did not ask for one and the layer's contribution is already
    visible through ``raw_strength``, PageRank, the eigenvector and
    ``bridging_diversity_exploratory``.
11. The mandated receipt sentence contains the token ``influence``, which
    INV-7 otherwise bans.  The sentence is a disclaimer mandated by the spec;
    the verifier exempts that exact sentence and bans the token everywhere
    else.  A 2026-09-02 addendum narrows INV-7 further: the verifier exempts
    opaque identifier *values* (``office_key``, ``container_id`` and its
    plural ``container_ids``, ``organization_id``, ``person_id``,
    ``lda_source_person_id``, ``registrant_source_org_id``, ``edge_id``,
    ``support_digest``, and any field whose name ends in ``_id`` or
    ``_key``) from the token grep, since those carry real office and
    organization names verbatim; field names, schema prose and every other
    value position stay checked.
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
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

import numpy as np  # noqa: E402

from fec.staffer_network.intervals import (  # noqa: E402
    UncertainInterval,
    guaranteed_overlap_days,
    possible_overlap_days,
)
from fec.staffer_network.network_math import (  # noqa: E402
    balanced_symmetric_adjacency,
    bridging_diversity,
    componentwise_eigenvector_centrality,
    connectedness_pagerank,
    deduplicate_undirected_layer_edges,
    group_balanced_teleport,
    layer_balanced_transition,
)
from fec.staffer_network.schema_validation import validate_instance  # noqa: E402
from fec.staffer_network.source_manifest import (  # noqa: E402
    canonical_json_bytes,
    sha256_file,
)


EDGE_SCHEMA_ID = "staffer-network-exploratory-temporal-edge-v1"
SCORE_SCHEMA_ID = "staffer-network-exploratory-node-score-v1"
RECEIPT_SCHEMA_ID = "staffer-network-exploratory-temporal-receipt-v1"
RULE_VERSION = "exploratory-temporal-tier-v1"
METHOD_VERSION = "exploratory-temporal-tier-v1"
PROMOTION_POLICY = "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
REVIEW_STATUS = "REVIEW_REQUIRED"
DIAL_STATUS = "UNTESTED_DEFAULTS_PENDING_FREEZE"
STATEMENT = (
    "Exploratory diagnostics over strict one-to-one review candidates; "
    "not identity findings; not primary weights; no influence claim."
)

EDGES_FILENAME = "exploratory_temporal_edges.ndjson.gz"
SCORES_FILENAME = "exploratory_node_scores.ndjson.gz"
RECEIPT_FILENAME = "exploratory_temporal_receipt.json"

SCHEMA_DIR = REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"
EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"
GLASSBOX_SOURCE = "tiered-corroboration-sidecar"

TIER_RANK = {"L0": 0, "L1": 1, "L2": 2, "L3": 3, "L4": 4, "L5": 5}
TIER_THRESHOLDS = ("L2", "L3", "L4")
NODE_KINDS = ("person", "container", "organization")
CO_TENURE_LAYER = 0
REVOLVING_LAYER = 1
MEMBERSHIP_LAYER = 2
LAYER_NAMES = {
    CO_TENURE_LAYER: "co_tenure",
    REVOLVING_LAYER: "revolving",
    MEMBERSHIP_LAYER: "membership",
}
SWEEP_CLAMP_MAXIMUM = 1.0

INPUT_FILES: tuple[tuple[str, str], ...] = (
    ("tiered_person_office_records", "tiered_person_office_records.ndjson.gz"),
    ("tiered_person_summary", "tiered_person_summary_25340.ndjson.gz"),
    ("filer_asserted_year_episodes", "filer_asserted_year_episodes.ndjson.gz"),
    ("registrant_side_records", "registrant_side_records.ndjson.gz"),
    ("tiered_corroboration_receipt", "tiered_corroboration_receipt.json"),
)

WEIGHT_SEMANTICS = (
    "Co-tenure weight is tier_strength times 1 - exp(-guaranteed_days / "
    "tau_days) over the cross-container unioned overlap calendar, where "
    "tier_strength is the minimum, over every contributing container, of the "
    "two endpoints' record tier in that container (not either person's "
    "max_tier); possible-only pairs carry zero weight and zero-overlap pairs "
    "are counted but not emitted. Revolving weight is the sum over unique "
    "people of TIER_STRENGTH[hill_tier] times R_STRENGTH[registrant_tier] for "
    "guaranteed ordered paths only; w_tiered_lower repeats that sum so one "
    "field name feeds the operator in both layers, and the unique-person "
    "count is emitted separately as contributing_person_count. Membership "
    "weight is TIER_STRENGTH[record tier] for one edge per tier >= L2 "
    "person-office record, gated into a given tier threshold by whether the "
    "person's max_tier clears that floor."
)
SWEEP_SEMANTICS = (
    "The layer-balanced operator row-normalizes each node's walk mass within "
    "each active layer, so multiplying every weight in one layer by a single "
    "constant leaves the operator unchanged. The minus-50-percent arm is "
    "therefore rank-preserving by construction, and the plus-50-percent arm "
    "moves scores only where the 1.0 clamp breaks proportionality between "
    "tiers. A rank correlation of 1.0 here is a property of the operator, not "
    "evidence that the dials are well chosen."
)


class BuildError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# small deterministic helpers
# ---------------------------------------------------------------------------


def sha_text(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise BuildError(f"object row required at {path}:{line_number}")
            yield value


def count_rows(path: Path) -> int:
    return sum(1 for _ in read_rows(path))


def load_schema(name: str) -> dict[str, Any]:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def parse_day(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if not isinstance(value, str) or not value:
        raise BuildError(f"date must be an ISO-8601 string: {value!r}")
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise BuildError(f"date is not canonical ISO-8601: {value!r}")
    return parsed


def point_interval(start: date, end_exclusive: date) -> UncertainInterval:
    """Wrap one half-open run as a fully bounded lane interval."""

    interval = UncertainInterval(
        start_earliest=start,
        start_latest=start,
        end_earliest=end_exclusive,
        end_latest=end_exclusive,
        start_precision="day",
        end_precision="day",
        asserted_current=False,
    )
    interval.validate()
    return interval


def union_half_open(
    ranges: Iterable[tuple[date, date]]
) -> list[tuple[date, date]]:
    """Union half-open ``[start, end)`` runs, merging overlapping and adjacent.

    ``intervals.py`` carries no union primitive, so this is written here rather
    than reimplementing anything the math adjudication already reviewed.
    Merging adjacency is required by math section 6 so that duplicate or
    back-to-back reporting periods cannot inflate a calendar.
    """

    cleaned = [(start, end) for start, end in ranges if end > start]
    if not cleaned:
        return []
    cleaned.sort()
    merged: list[tuple[date, date]] = [cleaned[0]]
    for start, end in cleaned[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged


def intersect_calendars(
    left: Sequence[tuple[date, date]],
    right: Sequence[tuple[date, date]],
    *,
    guaranteed: bool,
) -> list[tuple[date, date]]:
    """Intersect two unioned half-open calendars, cross-checked by intervals.py.

    The intersection range is extracted here because ``intervals.py`` returns
    day counts rather than ranges, but every extracted range's length is
    checked against the reviewed ``guaranteed_overlap_days`` /
    ``possible_overlap_days`` result, so the reviewed function stays the
    authority on the day count.
    """

    pieces: list[tuple[date, date]] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            low = max(left_start, right_start)
            high = min(left_end, right_end)
            if high <= low:
                continue
            left_interval = point_interval(left_start, left_end)
            right_interval = point_interval(right_start, right_end)
            days = (
                guaranteed_overlap_days(left_interval, right_interval)
                if guaranteed
                else possible_overlap_days(left_interval, right_interval)
            )
            if days != (high - low).days:
                raise BuildError(
                    "interval intersection disagrees with the reviewed overlap "
                    f"function: {days} vs {(high - low).days}"
                )
            pieces.append((low, high))
    return union_half_open(pieces)


def calendar_days(ranges: Sequence[tuple[date, date]]) -> int:
    return sum((end - start).days for start, end in ranges)


def duration_weight(days: int, tau_days: float) -> float:
    if days < 0:
        raise BuildError("overlap days must be nonnegative")
    return 1.0 - math.exp(-float(days) / tau_days)


def gap_decay(gap_days: int | None, half_life_days: float) -> float | None:
    if gap_days is None:
        return None
    return 2.0 ** (-float(gap_days) / half_life_days)


def spearman(left: Sequence[float], right: Sequence[float]) -> float | None:
    """Spearman rank correlation with average ranks for ties, stdlib only."""

    if len(left) != len(right):
        raise BuildError("rank correlation needs equal-length vectors")
    size = len(left)
    if size < 3:
        return None
    left_ranks = _average_ranks(left)
    right_ranks = _average_ranks(right)
    mean_left = sum(left_ranks) / size
    mean_right = sum(right_ranks) / size
    covariance = 0.0
    variance_left = 0.0
    variance_right = 0.0
    for a, b in zip(left_ranks, right_ranks):
        da = a - mean_left
        db = b - mean_right
        covariance += da * db
        variance_left += da * da
        variance_right += db * db
    if variance_left <= 0.0 or variance_right <= 0.0:
        return None
    value = covariance / math.sqrt(variance_left * variance_right)
    return max(-1.0, min(1.0, value))


def _average_ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(order):
        end = position
        while (
            end + 1 < len(order)
            and values[order[end + 1]] == values[order[position]]
        ):
            end += 1
        shared = (position + end) / 2.0 + 1.0
        for index in range(position, end + 1):
            ranks[order[index]] = shared
        position = end + 1
    return ranks


def parse_named_dial(text: str, allowed: Sequence[str], label: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            raise BuildError(f"{label} entry must be NAME=VALUE: {chunk!r}")
        name, raw = chunk.split("=", 1)
        name = name.strip()
        if name not in allowed:
            raise BuildError(f"{label} name not allowed: {name!r}")
        number = float(raw)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise BuildError(f"{label} value must lie in [0, 1]: {chunk!r}")
        values[name] = number
    missing = [name for name in allowed if name not in values]
    if missing:
        raise BuildError(f"{label} is missing {missing!r}")
    return values


def parse_number_list(text: str, label: str) -> list[float]:
    values: list[float] = []
    for chunk in text.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        number = float(chunk)
        if not math.isfinite(number):
            raise BuildError(f"{label} must be finite: {chunk!r}")
        values.append(number)
    if not values:
        raise BuildError(f"{label} must not be empty")
    return values


def scale_dial(
    dial: Mapping[str, float], factor: float
) -> tuple[dict[str, float], list[str]]:
    scaled: dict[str, float] = {}
    clamped: list[str] = []
    for name, value in dial.items():
        raw = value * factor
        if raw > SWEEP_CLAMP_MAXIMUM:
            raw = SWEEP_CLAMP_MAXIMUM
            clamped.append(name)
        scaled[name] = raw
    return scaled, sorted(clamped)


def emit_glassbox(
    *,
    enabled: bool,
    kind: str,
    status: str,
    summary: str,
    detail: str,
    run_id: str,
    stage: str,
) -> None:
    if not enabled or not EMIT_PS1.is_file():
        return
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(EMIT_PS1),
        "-Lane",
        "claude",
        "-Kind",
        kind,
        "-Status",
        status,
        "-Summary",
        summary,
        "-Detail",
        detail,
        "-RunId",
        run_id,
        "-Stage",
        stage,
        "-Source",
        GLASSBOX_SOURCE,
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        # Observability must never take the build down.
        return


# ---------------------------------------------------------------------------
# input loading
# ---------------------------------------------------------------------------


def container_identity(row: Mapping[str, Any]) -> tuple[str, str]:
    """Return ``(container_id, container_kind)`` for one person-office row."""

    bioguide = row.get("member_bioguide")
    kind = row.get("container_kind")
    if not isinstance(kind, str) or not kind:
        kind = "member_office" if bioguide else "unresolved"
    if isinstance(bioguide, str) and bioguide:
        return f"container:bioguide:{bioguide}", kind
    chamber = str(row.get("chamber") or "unknown")
    office_key = row.get("office_key")
    if not isinstance(office_key, str) or not office_key:
        raise BuildError("person-office row needs member_bioguide or office_key")
    return f"container:office:{chamber}:{office_key}", kind


def _run_from(
    block: Any, start_field: str, end_field: str, label: str
) -> tuple[date, date] | None:
    if not isinstance(block, Mapping):
        return None
    start = parse_day(block.get(start_field))
    end = parse_day(block.get(end_field))
    if start is None or end is None:
        return None
    if end < start:
        raise BuildError(f"{label} run ends before it starts: {start} .. {end}")
    return start, end


def load_person_office_records(path: Path, tier_strength: Mapping[str, float]):
    """Return ``(records, total_rows)`` for usable ``tier >= L2`` rows."""

    records: list[dict[str, Any]] = []
    total = 0
    for row in read_rows(path):
        total += 1
        tier = row.get("tier")
        if tier not in tier_strength:
            continue
        person_id = row.get("lda_source_person_id")
        if not isinstance(person_id, str) or not person_id:
            raise BuildError("person-office row needs lda_source_person_id")
        core = _run_from(row.get("core"), "start_latest", "end_earliest", "core")
        if core is None:
            continue
        envelope = _run_from(
            row.get("envelope"), "start_earliest", "end_latest", "envelope"
        )
        if envelope is None:
            envelope = core
        if envelope[0] > core[0] or envelope[1] < core[1]:
            raise BuildError(
                f"envelope does not contain core for {person_id}: {envelope} vs {core}"
            )
        container_id, container_kind = container_identity(row)
        records.append(
            {
                "lda_source_person_id": person_id,
                "tier": tier,
                "container_id": container_id,
                "container_kind": container_kind,
                "core": core,
                "envelope": envelope,
            }
        )
    return records, total


def load_person_summary(path: Path):
    summary: dict[str, dict[str, Any]] = {}
    total = 0
    for row in read_rows(path):
        total += 1
        person_id = row.get("lda_source_person_id")
        if not isinstance(person_id, str) or not person_id:
            raise BuildError("person summary row needs lda_source_person_id")
        max_tier = row.get("max_tier")
        if max_tier not in TIER_RANK:
            raise BuildError(f"unknown max_tier {max_tier!r} for {person_id}")
        if person_id in summary:
            raise BuildError(f"duplicate person summary row: {person_id}")
        registrant_tier = row.get("registrant_side_tier")
        summary[person_id] = {
            "max_tier": max_tier,
            "registrant_side_tier": (
                registrant_tier if isinstance(registrant_tier, str) else None
            ),
        }
    return summary, total


def _evidence_bounds(block: Any) -> tuple[date | None, date | None]:
    if not isinstance(block, list) or not block:
        return None, None
    starts: list[date] = []
    ends: list[date] = []
    for item in block:
        if not isinstance(item, Mapping):
            continue
        start = parse_day(item.get("start"))
        end = parse_day(item.get("end_exclusive"))
        if start is not None:
            starts.append(start)
        if end is not None:
            ends.append(end)
    return (min(starts) if starts else None, max(ends) if ends else None)


def load_registrant_records(
    path: Path,
    summary: Mapping[str, Mapping[str, Any]],
    r_strength: Mapping[str, float],
):
    """Return ``(records, total_rows, defaulted_tier_count)``."""

    records: list[dict[str, Any]] = []
    total = 0
    defaulted = 0
    for source_row in read_rows(path):
        total += 1
        # Part A v1 emits ONE row per person with a nested ``registrants`` list
        # (each item: registrant_source_org_id, filing_years, start_year,
        # end_year, employer_name) and the tier at row level; the spec's flat
        # one-row-per-pair shape is still accepted for fixtures.
        nested = source_row.get("registrants")
        if isinstance(nested, list):
            expanded = []
            for item in nested:
                if not isinstance(item, Mapping):
                    raise BuildError("registrants entries must be objects")
                merged = {
                    key: value
                    for key, value in source_row.items()
                    if key != "registrants"
                }
                merged.update(item)
                if "filing_year_first" not in merged and isinstance(
                    item.get("start_year"), int
                ):
                    merged["filing_year_first"] = item["start_year"]
                if "filing_year_last" not in merged and isinstance(
                    item.get("end_year"), int
                ):
                    merged["filing_year_last"] = item["end_year"]
                expanded.append(merged)
        else:
            expanded = [source_row]
        for row in expanded:
            defaulted += _append_registrant_record(row, records, summary, r_strength)
    return records, total, defaulted


def _append_registrant_record(
    row: Mapping[str, Any],
    records: list,
    summary: Mapping[str, Mapping[str, Any]],
    r_strength: Mapping[str, float],
) -> int:
    """Append one registrant record; return 1 if its tier was defaulted."""

    defaulted_flag = 0
    if True:
        person_id = row.get("lda_source_person_id")
        if not isinstance(person_id, str) or not person_id:
            raise BuildError("registrant row needs lda_source_person_id")
        org_id = row.get("registrant_source_org_id")
        if not isinstance(org_id, str) or not org_id:
            raise BuildError("registrant row needs registrant_source_org_id")
        years = row.get("filing_years")
        year_list = [int(year) for year in years] if isinstance(years, list) else []
        first = row.get("filing_year_first")
        last = row.get("filing_year_last")
        first_year = int(first) if isinstance(first, int) else (
            min(year_list) if year_list else None
        )
        last_year = int(last) if isinstance(last, int) else (
            max(year_list) if year_list else None
        )
        evidence_start, evidence_end = _evidence_bounds(
            row.get("dated_bounded_evidence")
        )
        year_start = date(first_year, 1, 1) if first_year is not None else None
        year_start_latest = (
            date(first_year + 1, 1, 1) if first_year is not None else None
        )
        year_end = date(last_year + 1, 1, 1) if last_year is not None else None

        candidates = [value for value in (year_start, evidence_start) if value]
        start_earliest = min(candidates) if candidates else None
        if evidence_start is not None:
            start_latest = evidence_start
        else:
            start_latest = year_start_latest
        if start_earliest is not None and start_latest is not None:
            start_latest = max(start_latest, start_earliest)
        end_candidates = [value for value in (year_end, evidence_end) if value]
        end_exclusive = max(end_candidates) if end_candidates else None

        tier = row.get("registrant_side_tier")
        if tier not in r_strength:
            fallback = summary.get(person_id, {}).get("registrant_side_tier")
            if fallback in r_strength:
                tier = fallback
            else:
                tier = "R0"
                defaulted_flag = 1
        records.append(
            {
                "lda_source_person_id": person_id,
                "registrant_source_org_id": org_id,
                "registrant_side_tier": tier,
                "start_earliest": start_earliest,
                "start_latest": start_latest,
                "end_exclusive": end_exclusive,
            }
        )
    return defaulted_flag


def gate_part_a_receipt(path: Path) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise BuildError("Part A receipt must be a JSON object")
    if document.get("status") != "PASS":
        raise BuildError(
            f"Part A receipt status is not PASS: {document.get('status')!r}"
        )
    for field in ("canonical_employment_promotions", "canonical_identity_promotions"):
        if field in document and document[field] != 0:
            raise BuildError(f"Part A receipt reports a nonzero {field}")
    policy = document.get("promotion_policy")
    if policy is not None and policy != PROMOTION_POLICY:
        raise BuildError(f"Part A promotion policy is not the required constant: {policy!r}")


# ---------------------------------------------------------------------------
# co-tenure and revolving model
# ---------------------------------------------------------------------------


def build_co_tenure_pairs(
    records: Sequence[Mapping[str, Any]],
    universe: Mapping[str, str],
    tau_days: float,
    tier_strength: Mapping[str, float],
):
    """Return ``(edges, status_counts, pairs_evaluated, containers_by_person)``."""

    by_container: dict[str, dict[str, dict[str, list]]] = defaultdict(
        lambda: defaultdict(lambda: {"core": [], "envelope": []})
    )
    # Per (container, person), the minimum record tier among that person's
    # (possibly duplicated) rows in that container -- fail-closed when a
    # container somehow carries more than one tier for the same person.  This
    # is what R3 calls "the record that supports that container's overlap",
    # as distinct from the person's global max_tier.
    container_person_tier: dict[str, dict[str, str]] = defaultdict(dict)
    containers_seen: set[str] = set()
    for record in records:
        person_id = record["lda_source_person_id"]
        if person_id not in universe:
            continue
        containers_seen.add(record["container_id"])
        bucket = by_container[record["container_id"]][person_id]
        bucket["core"].append(record["core"])
        bucket["envelope"].append(record["envelope"])
        tiers_here = container_person_tier[record["container_id"]]
        current = tiers_here.get(person_id)
        if current is None or TIER_RANK[record["tier"]] < TIER_RANK[current]:
            tiers_here[person_id] = record["tier"]

    pair_core: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    pair_envelope: dict[tuple[str, str], list[tuple[date, date]]] = defaultdict(list)
    pair_containers: dict[tuple[str, str], set[str]] = defaultdict(set)
    # Per pair, the per-container record tiers that actually supported an
    # overlap contribution (R3); a container that shares people but produces
    # no overlap days does not appear here.
    pair_record_contributions: dict[tuple[str, str], list[dict[str, Any]]] = (
        defaultdict(list)
    )

    for container_id in sorted(by_container):
        people = by_container[container_id]
        unioned = {
            person_id: {
                "core": union_half_open(blocks["core"]),
                "envelope": union_half_open(blocks["envelope"]),
            }
            for person_id, blocks in people.items()
        }
        tiers_here = container_person_tier[container_id]
        ordered = sorted(unioned)
        for left_index in range(len(ordered)):
            for right_index in range(left_index + 1, len(ordered)):
                left = ordered[left_index]
                right = ordered[right_index]
                key = (left, right)
                core_overlap = intersect_calendars(
                    unioned[left]["core"], unioned[right]["core"], guaranteed=True
                )
                envelope_overlap = intersect_calendars(
                    unioned[left]["envelope"],
                    unioned[right]["envelope"],
                    guaranteed=False,
                )
                if not core_overlap and not envelope_overlap:
                    pair_containers[key].add(container_id)
                    continue
                pair_core[key].extend(core_overlap)
                pair_envelope[key].extend(envelope_overlap)
                pair_containers[key].add(container_id)
                pair_record_contributions[key].append(
                    {
                        "container_id": container_id,
                        "subject_tier": tiers_here[left],
                        "object_tier": tiers_here[right],
                    }
                )

    edges: list[dict[str, Any]] = []
    status_counts = Counter({"GUARANTEED": 0, "POSSIBLE_ONLY": 0, "ZERO_OVERLAP": 0})
    for key in sorted(pair_containers):
        left, right = key
        guaranteed_days = calendar_days(union_half_open(pair_core.get(key, [])))
        possible_days = calendar_days(union_half_open(pair_envelope.get(key, [])))
        if guaranteed_days > possible_days:
            raise BuildError(
                f"guaranteed overlap exceeds possible overlap for {key}: "
                f"{guaranteed_days} > {possible_days}"
            )
        if guaranteed_days > 0:
            status = "GUARANTEED"
        elif possible_days > 0:
            status = "POSSIBLE_ONLY"
        else:
            status = "ZERO_OVERLAP"
        status_counts[status] += 1
        if status == "ZERO_OVERLAP":
            continue
        left_tier = universe[left]
        right_tier = universe[right]
        edges.append(
            {
                "subject_person": left,
                "object_person": right,
                "subject_tier": left_tier,
                "object_tier": right_tier,
                "status": status,
                "guaranteed_days": guaranteed_days,
                "possible_days": possible_days,
                "w_lower": duration_weight(guaranteed_days, tau_days),
                "w_upper": duration_weight(possible_days, tau_days),
                "container_ids": sorted(pair_containers[key]),
                "record_tier_contributions": list(pair_record_contributions.get(key, [])),
            }
        )
    # The pair enumeration is quadratic in a container's person count, so the
    # largest container is reported: it is the only thing that can make the
    # emitted edge file grow superlinearly on live data.
    largest_container = max(
        (len(people) for people in by_container.values()), default=0
    )
    return (
        edges,
        status_counts,
        len(pair_containers),
        sorted(containers_seen),
        largest_container,
    )


def classify_revolving(
    hill: Mapping[str, Any],
    registrant: Mapping[str, Any],
) -> tuple[str, str, int | None, int | None]:
    """Return ``(status, core_end_variant_status, gap_min_days, gap_max_days)``.

    ``status`` follows math adjudication section 7: GUARANTEED requires the
    Hill episode to end no later than the registrant span can begin under both
    uncertainty bounds.  ``core_end_variant_status`` is the spec's literal
    ``core.end_earliest`` test, reported for comparison only.  Precedence when
    no guaranteed ordering exists follows the 2026-09-01 addendum: an interval
    with a missing bound is INTERVAL_BLOCKED, never WRONG_ORDER.
    """

    hill_end_latest = hill["envelope"][1]
    hill_end_earliest = hill["core"][1]
    hill_start_earliest = hill["envelope"][0]
    start_earliest = registrant["start_earliest"]
    start_latest = registrant["start_latest"]
    end_exclusive = registrant["end_exclusive"]
    if start_earliest is None or start_latest is None or end_exclusive is None:
        return "INTERVAL_BLOCKED", "INTERVAL_BLOCKED", None, None

    gap_min = max(0, (start_earliest - hill_end_latest).days)
    gap_max = max(0, (start_latest - hill_end_earliest).days)
    if gap_max < gap_min:
        raise BuildError("gap upper bound fell below the gap lower bound")

    if hill_end_latest <= start_earliest:
        status = "GUARANTEED"
    elif end_exclusive <= hill_start_earliest:
        status = "WRONG_ORDER"
    else:
        status = "POSSIBLE_ONLY"

    if hill_end_earliest <= start_earliest:
        variant = "GUARANTEED"
    elif end_exclusive <= hill_start_earliest:
        variant = "WRONG_ORDER"
    else:
        variant = "POSSIBLE_ONLY"
    return status, variant, gap_min, gap_max


def build_revolving_edges(
    records: Sequence[Mapping[str, Any]],
    registrant_records: Sequence[Mapping[str, Any]],
    universe: Mapping[str, str],
    tier_strength: Mapping[str, float],
    r_strength: Mapping[str, float],
    half_life_days: float,
):
    """Return ``(edges, path_status_counts, variant_status_counts, orgs)``."""

    hill_by_person: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for record in records:
        if record["lda_source_person_id"] not in universe:
            continue
        if record["container_kind"] != "member_office":
            continue
        hill_by_person[record["lda_source_person_id"]].append(record)

    path_counts = Counter(
        {"GUARANTEED": 0, "POSSIBLE_ONLY": 0, "WRONG_ORDER": 0, "INTERVAL_BLOCKED": 0}
    )
    variant_counts = Counter(
        {"GUARANTEED": 0, "POSSIBLE_ONLY": 0, "WRONG_ORDER": 0, "INTERVAL_BLOCKED": 0}
    )
    organizations: set[str] = set()
    guaranteed: dict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    observed: dict[tuple[str, str], set[str]] = defaultdict(set)

    for registrant in registrant_records:
        person_id = registrant["lda_source_person_id"]
        if person_id not in universe:
            continue
        organizations.add(registrant["registrant_source_org_id"])
        organization_node = f"organization:{registrant['registrant_source_org_id']}"
        for hill in hill_by_person.get(person_id, ()):
            status, variant, gap_min, gap_max = classify_revolving(hill, registrant)
            path_counts[status] += 1
            variant_counts[variant] += 1
            key = (hill["container_id"], organization_node)
            observed[key].add(status)
            if status != "GUARANTEED":
                continue
            strength = (
                tier_strength[hill["tier"]]
                * r_strength[registrant["registrant_side_tier"]]
            )
            previous = guaranteed[key].get(person_id)
            candidate = {
                "lda_source_person_id": person_id,
                "max_tier": universe[person_id],
                "hill_tier": hill["tier"],
                "registrant_tier": registrant["registrant_side_tier"],
                "strength": strength,
                "gap_min_days": gap_min,
                "gap_max_days": gap_max,
            }
            if previous is None or candidate["strength"] > previous["strength"]:
                guaranteed[key][person_id] = candidate

    edges: list[dict[str, Any]] = []
    for key in sorted(set(observed) | set(guaranteed)):
        container_id, organization_node = key
        contributions = [
            guaranteed[key][person_id] for person_id in sorted(guaranteed.get(key, {}))
        ]
        if contributions:
            status = "GUARANTEED"
        else:
            statuses = observed.get(key, set())
            for candidate in ("POSSIBLE_ONLY", "INTERVAL_BLOCKED", "WRONG_ORDER"):
                if candidate in statuses:
                    status = candidate
                    break
            else:
                raise BuildError(f"revolving key without a status: {key}")
        decay_lowers = [
            gap_decay(item["gap_max_days"], half_life_days) for item in contributions
        ]
        decay_uppers = [
            gap_decay(item["gap_min_days"], half_life_days) for item in contributions
        ]
        edges.append(
            {
                "container_id": container_id,
                "organization_id": organization_node,
                "status": status,
                "contributions": contributions,
                "tier_strength": max(
                    (tier_strength[item["hill_tier"]] for item in contributions),
                    default=0.0,
                ),
                "gap_min_days": min(
                    (item["gap_min_days"] for item in contributions), default=None
                ),
                "gap_max_days": max(
                    (item["gap_max_days"] for item in contributions), default=None
                ),
                "gap_decay_lower": min(decay_lowers) if decay_lowers else None,
                "gap_decay_upper": max(decay_uppers) if decay_uppers else None,
            }
        )
    return edges, path_counts, variant_counts, sorted(organizations)


# ---------------------------------------------------------------------------
# weights per tier threshold
# ---------------------------------------------------------------------------


def record_tier_strength(
    edge: Mapping[str, Any], tier_strength: Mapping[str, float]
) -> float:
    """R3: the min, over every contributing container, of that container's
    ``min(subject_tier, object_tier)`` -- the record tier that actually
    supports the overlap, never the person's ``max_tier``.  Recomputed from
    the tier *labels* on every call so a swept ``tier_strength`` dial still
    rescales this weight correctly.
    """

    contributions = edge["record_tier_contributions"]
    if not contributions:
        return 0.0
    return min(
        min(tier_strength[item["subject_tier"]], tier_strength[item["object_tier"]])
        for item in contributions
    )


def co_tenure_weight(
    edge: Mapping[str, Any], tier_strength: Mapping[str, float]
) -> tuple[float, float]:
    strength = record_tier_strength(edge, tier_strength)
    return strength, strength * edge["w_lower"]


def revolving_weight(
    edge: Mapping[str, Any],
    threshold: str,
    tier_strength: Mapping[str, float],
    r_strength: Mapping[str, float],
) -> float:
    floor = TIER_RANK[threshold]
    total = 0.0
    for item in edge["contributions"]:
        if TIER_RANK[item["max_tier"]] < floor:
            continue
        total += tier_strength[item["hill_tier"]] * r_strength[item["registrant_tier"]]
    return total


def surviving_thresholds_co_tenure(edge: Mapping[str, Any], weight: float) -> list[str]:
    if weight <= 0.0:
        return []
    floor = min(TIER_RANK[edge["subject_tier"]], TIER_RANK[edge["object_tier"]])
    return [name for name in TIER_THRESHOLDS if TIER_RANK[name] <= floor]


def surviving_thresholds_revolving(edge: Mapping[str, Any]) -> list[str]:
    if not edge["contributions"]:
        return []
    best = max(TIER_RANK[item["max_tier"]] for item in edge["contributions"])
    return [name for name in TIER_THRESHOLDS if TIER_RANK[name] <= best]


# ---------------------------------------------------------------------------
# operator
# ---------------------------------------------------------------------------


def operator_inputs(
    co_tenure_edges: Sequence[Mapping[str, Any]],
    revolving_edges: Sequence[Mapping[str, Any]],
    membership_edges: Sequence[Mapping[str, Any]],
    node_index: Mapping[str, int],
    threshold: str,
    tier_strength: Mapping[str, float],
    r_strength: Mapping[str, float],
):
    subjects: list[int] = []
    objects: list[int] = []
    weights: list[float] = []
    layers: list[int] = []
    floor = TIER_RANK[threshold]
    for edge in co_tenure_edges:
        if TIER_RANK[edge["subject_tier"]] < floor:
            continue
        if TIER_RANK[edge["object_tier"]] < floor:
            continue
        _, weight = co_tenure_weight(edge, tier_strength)
        if weight <= 0.0:
            continue
        subjects.append(node_index[f"person:{edge['subject_person']}"])
        objects.append(node_index[f"person:{edge['object_person']}"])
        weights.append(weight)
        layers.append(CO_TENURE_LAYER)
    for edge in revolving_edges:
        weight = revolving_weight(edge, threshold, tier_strength, r_strength)
        if weight <= 0.0:
            continue
        subjects.append(node_index[edge["container_id"]])
        objects.append(node_index[edge["organization_id"]])
        weights.append(weight)
        layers.append(REVOLVING_LAYER)
    for edge in membership_edges:
        # R4: gated by the record's OWN tier against the floor (not the
        # person's max_tier), so the membership layer's density also falls
        # off with the tier-threshold restriction, matching how co-tenure
        # and revolving weights already respond to it.
        if TIER_RANK[edge["tier"]] < floor:
            continue
        weight = tier_strength[edge["tier"]]
        if weight <= 0.0:
            continue
        # The person node is gated on the SUMMARY tier, which can sit below a
        # record tier (Part A unions a person's lanes).  Skip the edge when its
        # person is not a node at this threshold rather than assuming presence.
        person_node = f"person:{edge['lda_source_person_id']}"
        if person_node not in node_index or edge["container_id"] not in node_index:
            continue
        subjects.append(node_index[person_node])
        objects.append(node_index[edge["container_id"]])
        weights.append(weight)
        layers.append(MEMBERSHIP_LAYER)
    return subjects, objects, weights, layers


def run_operator(
    node_ids: Sequence[str],
    group_codes: Sequence[int],
    subjects: Sequence[int],
    objects: Sequence[int],
    weights: Sequence[float],
    layers: Sequence[int],
    alphas: Sequence[float],
    *,
    pagerank_only: bool = False,
):
    node_count = len(node_ids)
    if node_count == 0:
        raise BuildError("operator needs at least one node")
    if subjects:
        deduped = deduplicate_undirected_layer_edges(
            np.asarray(subjects, dtype=np.int64),
            np.asarray(objects, dtype=np.int64),
            np.asarray(weights, dtype=np.float64),
            np.asarray(layers, dtype=np.int32),
        )
    else:
        deduped = (
            np.zeros(0, dtype=np.int64),
            np.zeros(0, dtype=np.int64),
            np.zeros(0, dtype=np.float64),
            np.zeros(0, dtype=np.int32),
        )
    edge_u, edge_v, edge_w, edge_layer = deduped
    transition = layer_balanced_transition(
        node_count, edge_u, edge_v, edge_w, edge_layer
    )
    codes = np.asarray(group_codes, dtype=np.int32)
    teleport = group_balanced_teleport(codes)
    pageranks: dict[float, np.ndarray] = {}
    convergence: list[dict[str, Any]] = []
    for alpha in alphas:
        score, detail = connectedness_pagerank(
            transition,
            damping=alpha,
            teleport=teleport,
            tolerance=1e-11,
            max_iterations=750,
        )
        pageranks[alpha] = score
        convergence.append(
            {
                "alpha": float(alpha),
                "iterations": int(detail["iterations"]),
                "residual_l1": float(detail["residual_l1"]),
            }
        )
    if pagerank_only:
        # Sensitivity arms only need the ranked PageRank vector; the
        # eigenvector and bridging diagnostics are not swept.
        eigenvector = np.zeros(node_count, dtype=np.float64)
        component_labels = np.zeros(node_count, dtype=np.int64)
        eigen_receipt: dict[str, Any] = {}
        bridging = np.zeros(node_count, dtype=np.float64)
    else:
        symmetric = balanced_symmetric_adjacency(transition)
        eigenvector, component_labels, eigen_receipt = (
            componentwise_eigenvector_centrality(
                symmetric, tolerance=1e-9, max_iterations=750, allow_partial=True
            )
        )
        bridging = bridging_diversity(transition, codes)
    raw_strength = np.zeros(node_count, dtype=np.float64)
    if edge_u.size:
        raw_strength = np.bincount(
            np.concatenate((edge_u, edge_v)),
            weights=np.concatenate((edge_w, edge_w)),
            minlength=node_count,
        )
    degrees = {
        CO_TENURE_LAYER: np.zeros(node_count, dtype=np.int64),
        REVOLVING_LAYER: np.zeros(node_count, dtype=np.int64),
        MEMBERSHIP_LAYER: np.zeros(node_count, dtype=np.int64),
    }
    if not pagerank_only:
        for index in range(edge_u.size):
            layer = int(edge_layer[index])
            degrees[layer][int(edge_u[index])] += 1
            degrees[layer][int(edge_v[index])] += 1
    component_sizes = np.bincount(component_labels)
    return {
        "transition": transition,
        "pageranks": pageranks,
        "pagerank_convergence": convergence,
        "eigenvector": eigenvector,
        "eigenvector_receipt": eigen_receipt,
        "component_labels": component_labels,
        "component_sizes": component_sizes,
        "bridging": bridging,
        "raw_strength": raw_strength,
        "degrees": degrees,
        "operator_edges": int(edge_u.size),
    }


# ---------------------------------------------------------------------------
# output
# ---------------------------------------------------------------------------


def open_gzip(path: Path):
    raw = path.open("wb")
    return gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0), raw


def prepare_output(output: Path) -> Path:
    if output.exists():
        if not output.is_dir():
            raise BuildError(f"output root exists and is not a directory: {output}")
        if any(output.iterdir()):
            raise BuildError(f"immutable generation already exists: {output}")
        output.rmdir()
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))


def edge_row_co_tenure(
    edge: Mapping[str, Any], tier_strength: Mapping[str, float]
) -> dict[str, Any]:
    strength, weight = co_tenure_weight(edge, tier_strength)
    subject = f"person:{edge['subject_person']}"
    object_id = f"person:{edge['object_person']}"
    support_digest = sha_text(
        {
            "containers": edge["container_ids"],
            "guaranteed_days": edge["guaranteed_days"],
            "possible_days": edge["possible_days"],
        }
    )
    # Lists, not dicts keyed by container_id: a container_id can embed a real
    # office_key/office name, and the language law only exempts opaque
    # identifier VALUES, not dict KEYS -- so container_id stays in the
    # exempt "container_id" value position, sorted for determinism.
    endpoint_record_tiers = {
        "subject": sorted(
            (
                {"container_id": item["container_id"], "tier": item["subject_tier"]}
                for item in edge["record_tier_contributions"]
            ),
            key=lambda item: item["container_id"],
        ),
        "object": sorted(
            (
                {"container_id": item["container_id"], "tier": item["object_tier"]}
                for item in edge["record_tier_contributions"]
            ),
            key=lambda item: item["container_id"],
        ),
    }
    endpoint_max_tiers = {
        "subject": edge["subject_tier"],
        "object": edge["object_tier"],
    }
    return {
        "schema_id": EDGE_SCHEMA_ID,
        "edge_id": "exploratory:edge:"
        + sha_text(["co_tenure", subject, object_id]),
        "exploratory": True,
        "primary": False,
        "layer": "co_tenure",
        "direction": "undirected",
        "status": edge["status"],
        "subject_id": subject,
        "subject_kind": "person",
        "subject_tier": edge["subject_tier"],
        "object_id": object_id,
        "object_kind": "person",
        "object_tier": edge["object_tier"],
        "tier_strength": strength,
        "w_lower": edge["w_lower"],
        "w_upper": edge["w_upper"],
        "w_tiered_lower": weight,
        "guaranteed_days": edge["guaranteed_days"],
        "possible_days": edge["possible_days"],
        "container_ids": edge["container_ids"],
        "container_count": len(edge["container_ids"]),
        "contributing_person_count": None,
        "strength_sum": None,
        "contributions": [],
        "gap_min_days": None,
        "gap_max_days": None,
        "gap_decay_lower": None,
        "gap_decay_upper": None,
        "strength_sum_gap_decayed_lower": None,
        "strength_sum_gap_decayed_upper": None,
        "surviving_tier_thresholds": surviving_thresholds_co_tenure(edge, weight),
        "endpoint_record_tiers": endpoint_record_tiers,
        "endpoint_max_tiers": endpoint_max_tiers,
        "support_digest": support_digest,
        "review_status": REVIEW_STATUS,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "rule_version": RULE_VERSION,
    }


def edge_row_revolving(
    edge: Mapping[str, Any],
    tier_strength: Mapping[str, float],
    r_strength: Mapping[str, float],
    half_life_days: float,
) -> dict[str, Any]:
    strength_sum = revolving_weight(edge, "L2", tier_strength, r_strength)
    decayed_lower = 0.0
    decayed_upper = 0.0
    for item in edge["contributions"]:
        strength = tier_strength[item["hill_tier"]] * r_strength[item["registrant_tier"]]
        lower = gap_decay(item["gap_max_days"], half_life_days)
        upper = gap_decay(item["gap_min_days"], half_life_days)
        decayed_lower += strength * (lower if lower is not None else 0.0)
        decayed_upper += strength * (upper if upper is not None else 0.0)
    has_contributions = bool(edge["contributions"])
    return {
        "schema_id": EDGE_SCHEMA_ID,
        "edge_id": "exploratory:edge:"
        + sha_text(["revolving", edge["container_id"], edge["organization_id"]]),
        "exploratory": True,
        "primary": False,
        "layer": "revolving",
        "direction": "member_to_organization",
        "status": edge["status"],
        "subject_id": edge["container_id"],
        "subject_kind": "container",
        "subject_tier": None,
        "object_id": edge["organization_id"],
        "object_kind": "organization",
        "object_tier": None,
        "tier_strength": edge["tier_strength"],
        "w_lower": None,
        "w_upper": None,
        "w_tiered_lower": strength_sum,
        "guaranteed_days": None,
        "possible_days": None,
        "container_ids": [],
        "container_count": 0,
        "contributing_person_count": len(edge["contributions"]),
        "strength_sum": strength_sum,
        "contributions": [dict(item) for item in edge["contributions"]],
        "gap_min_days": edge["gap_min_days"],
        "gap_max_days": edge["gap_max_days"],
        "gap_decay_lower": edge["gap_decay_lower"],
        "gap_decay_upper": edge["gap_decay_upper"],
        "strength_sum_gap_decayed_lower": decayed_lower if has_contributions else None,
        "strength_sum_gap_decayed_upper": decayed_upper if has_contributions else None,
        "surviving_tier_thresholds": surviving_thresholds_revolving(edge),
        "endpoint_record_tiers": None,
        "endpoint_max_tiers": None,
        "support_digest": sha_text(
            {
                "people": [
                    item["lda_source_person_id"] for item in edge["contributions"]
                ],
                "status": edge["status"],
            }
        ),
        "review_status": REVIEW_STATUS,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "rule_version": RULE_VERSION,
    }


def build_membership_edges(
    records: Sequence[Mapping[str, Any]], universe: Mapping[str, str]
) -> list[dict[str, Any]]:
    """R4: one membership edge per ``tier >= L2`` person-office record.

    ``records`` is already filtered to ``tier >= L2`` (INV-2 of the record
    floor, enforced in ``load_person_office_records``).  A duplicate input
    record (same person, container and tier reported twice) legitimately
    produces two membership edges here; that is the literal "one edge per
    record" the ruling asks for, and it is harmless downstream because
    ``network_math.deduplicate_undirected_layer_edges`` collapses duplicate
    endpoint/layer pairs before the operator is built.
    """

    edges: list[dict[str, Any]] = []
    for record in records:
        person_id = record["lda_source_person_id"]
        if person_id not in universe:
            continue
        edges.append(
            {
                "lda_source_person_id": person_id,
                "container_id": record["container_id"],
                "tier": record["tier"],
            }
        )
    return edges


def edge_row_membership(
    edge: Mapping[str, Any], tier_strength: Mapping[str, float]
) -> dict[str, Any]:
    subject = f"person:{edge['lda_source_person_id']}"
    object_id = edge["container_id"]
    weight = tier_strength[edge["tier"]]
    support_digest = sha_text(
        {
            "person": edge["lda_source_person_id"],
            "container_id": object_id,
            "tier": edge["tier"],
        }
    )
    return {
        "schema_id": EDGE_SCHEMA_ID,
        "edge_id": "exploratory:edge:"
        + sha_text(["membership", subject, object_id, edge["tier"]]),
        "exploratory": True,
        "primary": False,
        "layer": "membership",
        "direction": "undirected",
        "status": "GUARANTEED",
        "subject_id": subject,
        "subject_kind": "person",
        "subject_tier": edge["tier"],
        "object_id": object_id,
        "object_kind": "container",
        "object_tier": None,
        "tier_strength": weight,
        "w_lower": None,
        "w_upper": None,
        "w_tiered_lower": weight,
        "guaranteed_days": None,
        "possible_days": None,
        "container_ids": [object_id],
        "container_count": 1,
        "contributing_person_count": None,
        "strength_sum": None,
        "contributions": [],
        "gap_min_days": None,
        "gap_max_days": None,
        "gap_decay_lower": None,
        "gap_decay_upper": None,
        "strength_sum_gap_decayed_lower": None,
        "strength_sum_gap_decayed_upper": None,
        "surviving_tier_thresholds": [
            name for name in TIER_THRESHOLDS if TIER_RANK[name] <= TIER_RANK[edge["tier"]]
        ],
        "endpoint_record_tiers": None,
        "endpoint_max_tiers": None,
        "support_digest": support_digest,
        "review_status": REVIEW_STATUS,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "rule_version": RULE_VERSION,
    }


def score_row(
    *,
    threshold: str,
    node_id: str,
    node_kind: str,
    max_tier: str | None,
    result: Mapping[str, Any],
    index: int,
    alphas: Sequence[float],
) -> dict[str, Any]:
    eigen = result["eigenvector"][index]
    raw_strength = float(result["raw_strength"][index])
    component = int(result["component_labels"][index])
    return {
        "schema_id": SCORE_SCHEMA_ID,
        "exploratory": True,
        "primary": False,
        "tier_threshold": threshold,
        "node_id": node_id,
        "node_kind": node_kind,
        "max_tier": max_tier,
        "raw_strength": raw_strength,
        "isolate": bool(raw_strength == 0.0),
        "component_id": component,
        "component_size": int(result["component_sizes"][component]),
        "co_tenure_degree": int(result["degrees"][CO_TENURE_LAYER][index]),
        "revolving_degree": int(result["degrees"][REVOLVING_LAYER][index]),
        "connectedness_pagerank_exploratory": [
            {"alpha": float(alpha), "score": float(result["pageranks"][alpha][index])}
            for alpha in alphas
        ],
        "eigenvector_component_local_exploratory": (
            float(eigen) if np.isfinite(eigen) else None
        ),
        "bridging_diversity_exploratory": (
            float(result["bridging"][index]) if raw_strength > 0.0 else None
        ),
        "review_status": REVIEW_STATUS,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "rule_version": RULE_VERSION,
    }


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------


def run(args: argparse.Namespace) -> dict[str, Any]:
    sidecar = Path(args.sidecar_root).resolve()
    output = Path(args.output_root).resolve()
    tier_strength = parse_named_dial(
        args.tier_strength, ("L2", "L3", "L4", "L5"), "--tier-strength"
    )
    r_strength = parse_named_dial(
        args.r_strength, ("R0", "R1", "R2"), "--r-strength"
    )
    alphas = parse_number_list(args.alphas, "--alphas")
    if any(not 0.0 < alpha < 1.0 for alpha in alphas):
        raise BuildError("every alpha must lie strictly between zero and one")
    if not any(abs(alpha - 0.85) < 1e-12 for alpha in alphas):
        raise BuildError("--alphas must include the 0.85 sweep point")
    sweep_factors = parse_number_list(args.sweep_factors, "--sweep-factors")
    if args.tau_days <= 0 or args.half_life_days <= 0:
        raise BuildError("tau and half-life must be positive")

    paths = {role: sidecar / name for role, name in INPUT_FILES}
    for role, path in paths.items():
        if not path.is_file():
            raise BuildError(f"missing Part A input ({role}): {path}")
    gate_part_a_receipt(paths["tiered_corroboration_receipt"])

    records, person_office_rows = load_person_office_records(
        paths["tiered_person_office_records"], tier_strength
    )
    summary, summary_rows = load_person_summary(paths["tiered_person_summary"])
    registrant_records, registrant_rows, defaulted_tiers = load_registrant_records(
        paths["registrant_side_records"], summary, r_strength
    )
    filer_rows = count_rows(paths["filer_asserted_year_episodes"])

    missing_people = sorted(
        {
            record["lda_source_person_id"]
            for record in records
            if record["lda_source_person_id"] not in summary
        }
    )
    if missing_people:
        raise BuildError(
            "person-office rows reference people absent from the person summary: "
            + ", ".join(missing_people[:5])
        )

    # A record's tier may legitimately exceed its person's summary tier: Part A
    # derives the person tier by re-running the prong rules over the UNION of
    # that person's lanes (the confirmation ladder's own semantics, pinned by
    # INV-5), so an L4 lane combined with a chronology-inconsistent lane yields
    # an L3 person.  Node presence is therefore gated on the summary tier, and
    # a membership edge whose person is absent at a threshold is skipped and
    # counted (see operator_inputs).  The disagreement is reported, never fatal.
    record_max: dict[str, int] = {}
    for record in records:
        rec_tier = str(record.get("tier") or record.get("record_tier"))
        if rec_tier not in TIER_RANK:
            continue
        pid = record["lda_source_person_id"]
        if TIER_RANK[rec_tier] > record_max.get(pid, -1):
            record_max[pid] = TIER_RANK[rec_tier]
    tier_discrepancies = sorted(
        pid for pid, rank in record_max.items()
        if pid in summary and TIER_RANK[str(summary[pid]["max_tier"])] != rank
    )
    # Fail closed on the invariant the operator relies on: within the node
    # universe (summary tier >= L2) no record may out-rank its person's
    # summary tier, or a threshold restriction would keep an edge whose
    # endpoint node is gone.  People below L2 never enter the universe, so a
    # disagreement there is reported but not fatal.
    in_universe_violations = sorted(
        pid for pid in tier_discrepancies
        if TIER_RANK[str(summary[pid]["max_tier"])] >= TIER_RANK["L2"]
        and record_max[pid] > TIER_RANK[str(summary[pid]["max_tier"])]
    )
    print(
        json.dumps(
            {
                "person_tier_differs_from_max_record_tier": len(tier_discrepancies),
                "record_tier_above_person_tier_in_universe": len(in_universe_violations),
                "examples": in_universe_violations[:10] or tier_discrepancies[:10],
            }
        )
    )

    universe = {
        person_id: str(entry["max_tier"])
        for person_id, entry in summary.items()
        if TIER_RANK[str(entry["max_tier"])] >= TIER_RANK["L2"]
    }

    (
        co_tenure_edges,
        co_tenure_counts,
        pairs_evaluated,
        containers_seen,
        largest_container,
    ) = build_co_tenure_pairs(records, universe, args.tau_days, tier_strength)
    del containers_seen  # container node sets are rebuilt per tier threshold
    revolving_edges, revolving_path_counts, revolving_variant_counts, organizations = (
        build_revolving_edges(
            records,
            registrant_records,
            universe,
            tier_strength,
            r_strength,
            args.half_life_days,
        )
    )
    membership_edges = build_membership_edges(records, universe)

    containers_by_threshold: dict[str, list[str]] = {}
    organizations_by_threshold: dict[str, list[str]] = {}
    for threshold in TIER_THRESHOLDS:
        floor = TIER_RANK[threshold]
        people = {
            person_id
            for person_id, tier in universe.items()
            if TIER_RANK[tier] >= floor
        }
        containers_by_threshold[threshold] = sorted(
            {
                record["container_id"]
                for record in records
                if record["lda_source_person_id"] in people
            }
        )
        organizations_by_threshold[threshold] = sorted(
            {
                f"organization:{record['registrant_source_org_id']}"
                for record in registrant_records
                if record["lda_source_person_id"] in people
            }
        )

    staging = prepare_output(output)
    try:
        edges_path = staging / EDGES_FILENAME
        scores_path = staging / SCORES_FILENAME
        edge_schema = load_schema("exploratory_temporal_edge.schema.json")
        score_schema = load_schema("exploratory_node_score.schema.json")
        receipt_schema = load_schema("exploratory_temporal_receipt.schema.json")

        emitted_edges = 0
        co_tenure_operator_l2 = 0
        revolving_operator_l2 = 0
        membership_operator_l2 = 0
        rows: list[dict[str, Any]] = []
        for edge in co_tenure_edges:
            row = edge_row_co_tenure(edge, tier_strength)
            if row["w_tiered_lower"] > 0.0:
                co_tenure_operator_l2 += 1
            rows.append(row)
        for edge in revolving_edges:
            row = edge_row_revolving(edge, tier_strength, r_strength, args.half_life_days)
            if row["w_tiered_lower"] > 0.0:
                revolving_operator_l2 += 1
            rows.append(row)
        for edge in membership_edges:
            row = edge_row_membership(edge, tier_strength)
            if row["w_tiered_lower"] > 0.0:
                membership_operator_l2 += 1
            rows.append(row)
        rows.sort(key=lambda item: (item["layer"], item["subject_id"], item["object_id"]))
        stream, raw = open_gzip(edges_path)
        try:
            for row in rows:
                validate_instance(row, edge_schema)
                stream.write(canonical_json_bytes(row))
                emitted_edges += 1
        finally:
            stream.close()
            raw.close()

        operator_receipt: dict[str, Any] = {}
        node_universe: dict[str, Any] = {}
        sweep_rows: list[dict[str, Any]] = []
        emitted_scores = 0
        stream, raw = open_gzip(scores_path)
        try:
            for threshold in TIER_THRESHOLDS:
                floor = TIER_RANK[threshold]
                people = sorted(
                    person_id
                    for person_id, tier in universe.items()
                    if TIER_RANK[tier] >= floor
                )
                node_ids = (
                    [f"person:{person_id}" for person_id in people]
                    + list(containers_by_threshold[threshold])
                    + list(organizations_by_threshold[threshold])
                )
                node_ids.sort()
                node_universe[threshold] = {
                    "person": len(people),
                    "container": len(containers_by_threshold[threshold]),
                    "organization": len(organizations_by_threshold[threshold]),
                    "total": len(node_ids),
                }
                if not node_ids:
                    operator_receipt[threshold] = {
                        "nodes": 0,
                        "operator_edges": 0,
                        "isolates": 0,
                        "components": 0,
                        "pagerank": [],
                        "eigenvector": None,
                    }
                    continue
                node_index = {node_id: index for index, node_id in enumerate(node_ids)}
                kinds = [node_id.split(":", 1)[0] for node_id in node_ids]
                group_codes = [NODE_KINDS.index(kind) for kind in kinds]
                subjects, objects, weights, layers = operator_inputs(
                    co_tenure_edges,
                    revolving_edges,
                    membership_edges,
                    node_index,
                    threshold,
                    tier_strength,
                    r_strength,
                )
                result = run_operator(
                    node_ids, group_codes, subjects, objects, weights, layers, alphas
                )
                max_tiers = {f"person:{p}": universe[p] for p in people}
                for index, node_id in enumerate(node_ids):
                    row = score_row(
                        threshold=threshold,
                        node_id=node_id,
                        node_kind=kinds[index],
                        max_tier=max_tiers.get(node_id),
                        result=result,
                        index=index,
                        alphas=alphas,
                    )
                    validate_instance(row, score_schema)
                    stream.write(canonical_json_bytes(row))
                    emitted_scores += 1
                operator_receipt[threshold] = {
                    "nodes": len(node_ids),
                    "operator_edges": result["operator_edges"],
                    "isolates": int(np.count_nonzero(result["raw_strength"] == 0.0)),
                    "components": int(result["eigenvector_receipt"]["components"]),
                    "pagerank": result["pagerank_convergence"],
                    "eigenvector": {
                        key: (float(value) if isinstance(value, float) else value)
                        for key, value in result["eigenvector_receipt"].items()
                    },
                }

                baseline_alpha = next(
                    alpha for alpha in alphas if abs(alpha - 0.85) < 1e-12
                )
                baseline = result["pageranks"][baseline_alpha]
                active = [
                    index
                    for index in range(len(node_ids))
                    if result["raw_strength"][index] > 0.0
                ]
                for dial_name, dial in (
                    ("TIER_STRENGTH", tier_strength),
                    ("R_STRENGTH", r_strength),
                ):
                    for factor in sweep_factors:
                        scaled, clamped = scale_dial(dial, factor)
                        sweep_tier = scaled if dial_name == "TIER_STRENGTH" else tier_strength
                        sweep_r = scaled if dial_name == "R_STRENGTH" else r_strength
                        s_subjects, s_objects, s_weights, s_layers = operator_inputs(
                            co_tenure_edges,
                            revolving_edges,
                            membership_edges,
                            node_index,
                            threshold,
                            sweep_tier,
                            sweep_r,
                        )
                        swept = run_operator(
                            node_ids,
                            group_codes,
                            s_subjects,
                            s_objects,
                            s_weights,
                            s_layers,
                            (0.85,),
                            pagerank_only=True,
                        )
                        correlation = spearman(
                            [float(baseline[index]) for index in active],
                            [float(swept["pageranks"][0.85][index]) for index in active],
                        )
                        sweep_rows.append(
                            {
                                "dial": dial_name,
                                "factor": float(factor),
                                "tier_threshold": threshold,
                                "spearman_pagerank_0_85": correlation,
                                "nodes_ranked": len(active),
                                "clamped_dial_entries": clamped,
                                "scaled_dial": scaled,
                            }
                        )
        finally:
            stream.close()
            raw.close()

        inputs = []
        row_counts = {
            "tiered_person_office_records": person_office_rows,
            "tiered_person_summary": summary_rows,
            "filer_asserted_year_episodes": filer_rows,
            "registrant_side_records": registrant_rows,
            "tiered_corroboration_receipt": None,
        }
        for role, path in sorted(paths.items()):
            inputs.append(
                {
                    "role": role,
                    "path": path.as_posix(),
                    "bytes": path.stat().st_size,
                    "rows": row_counts[role],
                    "sha256": sha256_file(path),
                }
            )
        for role, module_path in (
            ("network_math", REPOSITORY_ROOT / "fec" / "staffer_network" / "network_math.py"),
            ("intervals", REPOSITORY_ROOT / "fec" / "staffer_network" / "intervals.py"),
        ):
            inputs.append(
                {
                    "role": role,
                    "path": module_path.as_posix(),
                    "bytes": module_path.stat().st_size,
                    "rows": None,
                    "sha256": sha256_file(module_path),
                }
            )
        inputs.sort(key=lambda item: item["role"])

        receipt = {
            "schema_id": RECEIPT_SCHEMA_ID,
            "generated_at": args.generated_at,
            "status": "PASS",
            "method_version": METHOD_VERSION,
            "rule_version": RULE_VERSION,
            "exploratory": True,
            "primary": False,
            "primary_weights_emitted": 0,
            "statement": STATEMENT,
            "promotion_policy": PROMOTION_POLICY,
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "review_status": REVIEW_STATUS,
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
            "dial_status": DIAL_STATUS,
            "dials": {
                "tau_days": float(args.tau_days),
                "gap_half_life_days": float(args.half_life_days),
                "tier_strength": dict(tier_strength),
                "r_strength": dict(r_strength),
                "alphas": [float(alpha) for alpha in alphas],
                "tier_thresholds": list(TIER_THRESHOLDS),
                "sweep_factors": [float(value) for value in sweep_factors],
                "sweep_clamp_maximum": SWEEP_CLAMP_MAXIMUM,
            },
            "inputs": inputs,
            "files": [
                {
                    "role": "exploratory_temporal_edges",
                    "path": EDGES_FILENAME,
                    "records": emitted_edges,
                    "bytes": edges_path.stat().st_size,
                    "sha256": sha256_file(edges_path),
                },
                {
                    "role": "exploratory_node_scores",
                    "path": SCORES_FILENAME,
                    "records": emitted_scores,
                    "bytes": scores_path.stat().st_size,
                    "sha256": sha256_file(scores_path),
                },
            ],
            "records_read": {
                "person_office_records": person_office_rows,
                "person_office_records_used": len(records),
                "person_summary_rows": summary_rows,
                "filer_asserted_year_episodes": filer_rows,
                "registrant_side_records": registrant_rows,
                "registrant_side_records_used": sum(
                    1
                    for record in registrant_records
                    if record["lda_source_person_id"] in universe
                ),
                "registrant_tier_defaulted_r0": defaulted_tiers,
            },
            "node_universe": node_universe,
            "layers": [LAYER_NAMES[CO_TENURE_LAYER], LAYER_NAMES[REVOLVING_LAYER], LAYER_NAMES[MEMBERSHIP_LAYER]],
            "edge_counts": {
                "co_tenure_emitted": len(co_tenure_edges),
                "co_tenure_in_operator_l2": co_tenure_operator_l2,
                "revolving_emitted": len(revolving_edges),
                "revolving_in_operator_l2": revolving_operator_l2,
                "membership": len(membership_edges),
                "membership_in_operator_l2": membership_operator_l2,
                "co_tenure_pairs_evaluated": pairs_evaluated,
                "largest_container_person_count": largest_container,
            },
            "co_tenure_status_counts": {
                name: int(co_tenure_counts[name])
                for name in ("GUARANTEED", "POSSIBLE_ONLY", "ZERO_OVERLAP")
            },
            "revolving_path_status_counts": {
                name: int(revolving_path_counts[name])
                for name in (
                    "GUARANTEED",
                    "POSSIBLE_ONLY",
                    "WRONG_ORDER",
                    "INTERVAL_BLOCKED",
                )
            },
            "revolving_path_status_counts_core_end_variant": {
                name: int(revolving_variant_counts[name])
                for name in (
                    "GUARANTEED",
                    "POSSIBLE_ONLY",
                    "WRONG_ORDER",
                    "INTERVAL_BLOCKED",
                )
            },
            "revolving_edge_status_counts": {
                name: sum(
                    1 for edge in revolving_edges if edge["status"] == name
                )
                for name in (
                    "GUARANTEED",
                    "POSSIBLE_ONLY",
                    "WRONG_ORDER",
                    "INTERVAL_BLOCKED",
                )
            },
            "operator": operator_receipt,
            "sweep": sweep_rows,
            "sweep_semantics": SWEEP_SEMANTICS,
            "weight_semantics": WEIGHT_SEMANTICS,
            "self_loops": 0,
            "zero_overlap_edges_emitted": 0,
            "implementation": {
                "path": Path(__file__).name,
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "failures": [],
        }
        validate_instance(receipt, receipt_schema)
        (staging / RECEIPT_FILENAME).write_bytes(canonical_json_bytes(receipt))
        os.replace(staging, output)
        return receipt
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the exploratory temporal tier.")
    parser.add_argument("--sidecar-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--generated-at", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--tau-days", type=float, default=365.2425)
    parser.add_argument(
        "--tier-strength", default="L2=0.25,L3=0.50,L4=0.75,L5=1.00"
    )
    parser.add_argument("--r-strength", default="R0=0.25,R1=0.50,R2=1.00")
    parser.add_argument("--alphas", default="0.70,0.85,0.95")
    parser.add_argument("--half-life-days", type=float, default=730.485)
    parser.add_argument("--sweep-factors", default="0.5,1.5")
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox,
        kind="run.start",
        status="running",
        summary="exploratory temporal tier build",
        detail=str(args.output_root),
        run_id=args.run_id,
        stage="partB-build",
    )
    try:
        receipt = run(args)
    except BaseException as error:
        emit_glassbox(
            enabled=glassbox,
            kind="run.fail",
            status="failed",
            summary="exploratory temporal tier build failed",
            detail=f"{type(error).__name__}: {error}",
            run_id=args.run_id,
            stage="partB-build",
        )
        raise
    emit_glassbox(
        enabled=glassbox,
        kind="run.finish",
        status="completed",
        summary="exploratory temporal tier build",
        detail=(
            f"edges={receipt['files'][0]['records']} "
            f"scores={receipt['files'][1]['records']}"
        ),
        run_id=args.run_id,
        stage="partB-build",
    )
    print(json.dumps({"status": receipt["status"], "files": receipt["files"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
