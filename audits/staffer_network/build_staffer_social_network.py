#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Staffer social network over the FULL payroll population.

Architecture is REUSED VERBATIM from build_exploratory_temporal_tier.py, which the
project owner ruled correct.  What changes is the POPULATION: the exploratory tier
read tiered_person_office_records.ndjson.gz (the slice that touches LDA).  This build
reads the complete declared Hill personnel spine, both chambers, enriched to DAY
precision on the House lane from the House SOD ledger observations.

Reused verbatim from build_exploratory_temporal_tier.py / fec/staffer_network:
  * ``union_half_open``          - union of half-open runs, merging adjacency
  * ``intersect_calendars``      - intersection cross-checked against intervals.py
  * ``calendar_days``            - day count of a unioned calendar
  * ``duration_weight``          - 1 - exp(-days / tau_days)
  * ``TAU_DAYS = 365.2425``
  * GUARANTEED / POSSIBLE_ONLY / ZERO_OVERLAP status vocabulary; ZERO_OVERLAP never
    emitted as an edge
  * receipt shape: schema_id / rule_version / method_version / dial_status /
    promotion_policy / review_status / canonical_* zero counters / files[] with
    sha256 / inputs[] with sha256 / weight_semantics / statement / failures[]

OWNER RULING APPLIED (2026-09-03): no person-to-person edge without actual temporal
overlap.  Two people who served the same office at non-overlapping times NEVER MET; an
edge between them would fabricate a relationship.  Sequence is therefore NOT a
person-person edge here - it is recorded as a property of the person's TRAJECTORY and
as directed office-to-office structure, in staffer_trajectories.ndjson.gz.

D-022 APPLIED (2026-09-06), THE v4 PERSONS-ONLY CHANGE.  Organisations, offices and
policy areas LEAVE the people network.  Concretely:

  * THE OPERATOR IS PERSONS ONLY.  The scored matrix is indexed over person nodes and
    nothing else, its only edge layer is co_tenure, and its restart distribution is
    UNIFORM OVER PERSONS.  ``group_balanced_teleport`` is no longer called from this
    builder (it stays in fec/staffer_network/network_math.py for other callers): it
    gave every node KIND equal restart mass, so 36 policy-area nodes drew the same
    total mass as 144,693 people - 402x per node - and the 2026-09-05 audit measured
    people carrying a Politico policy edge at 11.6x the PageRank of the rest.  A
    persons-only operator with a uniform restart removes that channel structurally
    rather than by re-tuning a dial.
  * containers, organisations and policy areas are emitted as GROUPING LAYERS -
    staffer_social_membership_layer.ndjson.gz, staffer_social_revolving_layer.ndjson.gz,
    staffer_social_policy_layer.ndjson.gz - every row carrying ``operator_included:
    False``, plus a staffer_social_groups.ndjson.gz roster of
    the group nodes themselves.  They never appear in node_scores.
  * ``bridging_diversity`` (Simpson over node KINDS, which only ever measured how many
    of the four kinds a node touched) is REPLACED by ``office_diversity``: Simpson over
    the CONTAINERS that actually produced a person's co-tenure ties.  The old field name
    is gone from the payload.

Nothing here is canonical.  Every row carries review_status REVIEW_REQUIRED and
canonical_employment_promoted false; the receipt pins every promotion counter at 0.
"""

from __future__ import annotations

try:
    from .politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY
except ImportError:
    from politico_completion_contract import completion_accepted, validate_browser_exception, SOURCE_EXCEPTION_POLICY


import argparse
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence

import numpy as np
from scipy import sparse
from scipy.sparse import csgraph
from scipy.sparse.linalg import eigsh

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPOSITORY_ROOT))

from fec.staffer_network.intervals import (  # noqa: E402
    UncertainInterval,
    guaranteed_overlap_days,
    possible_overlap_days,
)
from fec.staffer_network.network_math import (  # noqa: E402
    balanced_symmetric_adjacency,
    componentwise_eigenvector_centrality,
    connectedness_pagerank,
    deduplicate_undirected_layer_edges,
    layer_balanced_transition,
)
# NOT imported on purpose: bridging_diversity (Simpson over node KINDS - meaningless in
# a single-kind operator, replaced here by office_diversity) and group_balanced_teleport
# (equal restart mass per node KIND - the 402x policy-node inflation channel).  Both
# stay in network_math.py for other callers; see D-022 in the module docstring.

from fec.staffer_network.ranking_math import (
    VERSION as RANKING_VERSION, SHARED_ROLE_FACTOR, attributed_support,
    co_tenure_weight, eligible_container, shared_role,
)

# --------------------------------------------------------------------------- constants
EDGE_SCHEMA_ID = "staffer-network-social-edge-v1"
NODE_SCHEMA_ID = "staffer-network-social-node-score-v1"
TRAJ_SCHEMA_ID = "staffer-network-social-trajectory-v1"
MOVE_SCHEMA_ID = "staffer-network-social-office-move-v1"
RECEIPT_SCHEMA_ID = "staffer-network-social-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-social-manifest-v1"
GROUPING_SCHEMA_ID = "staffer-network-social-grouping-layer-v1"
GROUP_SCHEMA_ID = "staffer-network-social-group-v1"
RULE_VERSION = "staffer-social-network-v5-duration-attributed"
METHOD_VERSION = "staffer-social-network-v5-duration-attributed"
CONFIG_NAME = "staffer_social_network_20260908_v7_math"
VINTAGE = "20260908"
PROMOTION_POLICY = "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
REVIEW_STATUS = "REVIEW_REQUIRED"
DIAL_STATUS = "UNTESTED_DEFAULTS_PENDING_FREEZE"

EDGES_FILENAME = "staffer_social_edges.ndjson.gz"
NODES_FILENAME = "staffer_social_node_scores.ndjson.gz"
TRAJ_FILENAME = "staffer_trajectories.ndjson.gz"
MOVES_FILENAME = "staffer_office_moves.ndjson.gz"
RECEIPT_FILENAME = "staffer_social_network_receipt.json"
MANIFEST_FILENAME = "staffer_social_network_manifest.json"
POLITICO_REVIEW_FILENAME = "staffer_social_politico_review_layers.ndjson.gz"
MEMBERSHIP_LAYER_FILENAME = "staffer_social_membership_layer.ndjson.gz"
REVOLVING_LAYER_FILENAME = "staffer_social_revolving_layer.ndjson.gz"
POLICY_LAYER_FILENAME = "staffer_social_policy_layer.ndjson.gz"
GROUPS_FILENAME = "staffer_social_groups.ndjson.gz"

EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"
GLASSBOX_SOURCE = "staffer-social-network"

# ---- dials, ALL UNTESTED DEFAULTS -------------------------------------------------
TAU_DAYS = 365.2425                      # verbatim, build_exploratory_temporal_tier.py
ALPHAS = (0.7, 0.85, 0.95)               # verbatim
SWEEP_FACTORS = (0.5, 1.5)               # verbatim
SWEEP_CLAMP_MAXIMUM = 1.0                # verbatim
# design 6.2 container proximity kappa
KAPPA = {
    "member_office": 1.00,
    "committee_same_side": 0.75,
    "committee_side_unknown": 0.60,
    "committee_bipartisan": 0.60,
    "committee_opposite_side": 0.40,
    "leadership": 0.75,
    "admin": 0.50,
    "unresolved": 0.50,
}
# hill spine identity tiers, strengths taken verbatim from the spine's own published
# dial block (hill_personnel_spine_receipt.json -> dials.s_strength)
S_STRENGTH = {"S1": 0.75, "S2": 0.5, "S3": 0.25}
S_RANK = {"S3": 0, "S2": 1, "S1": 2}

# Layer ids are kept at their historical values so an artifact from this family can be
# read against any generation.  In v4 ONLY layer 0 reaches the operator; 1/2/3 are the
# grouping layers and are emitted to their own files with operator_included False.
CO_TENURE_LAYER = 0
REVOLVING_LAYER = 1
MEMBERSHIP_LAYER = 2
POLICY_AREA_LAYER = 3
LAYER_NAMES = {
    CO_TENURE_LAYER: "co_tenure",
    REVOLVING_LAYER: "revolving",
    MEMBERSHIP_LAYER: "membership",
    POLICY_AREA_LAYER: "policy_area",
}
OPERATOR_LAYERS = (CO_TENURE_LAYER,)
GROUPING_LAYERS = (MEMBERSHIP_LAYER, REVOLVING_LAYER, POLICY_AREA_LAYER)
# Owner ruling 2026-09-07: container kinds that are NOT eligible to enumerate
# co-tenure pairs. Mirrors fec/staffer_network/employment_history.py's
# CO_TENURE_EXCLUDED_CONTAINER_KINDS, which gates the temporal sidecar's clique the
# same way; the two must stay in step. Chamber-wide ADMINISTRATIVE payroll headers
# (Chief Administrative Officer of the House 2,551 people; Office of Congressional
# Accessibility Services 3,373; Sergeant at Arms Senate 2,059; Clerk of the House
# 1,118; SGT@ARMS Capitol Division 1,576; and 49 others -- 54 containers carrying
# 70.8% of every co-tenure pair in the v5 generation) are institutional paymasters,
# not workplaces. Concurrency was enforced correctly there; the UNIT was wrong.
# Excluded containers stay in the graph, keep their membership layer, keep their
# node scores and stay reachable; they simply enumerate no person-person pair.
CO_TENURE_EXCLUDED_CONTAINER_KINDS = frozenset({"admin"})
NODE_KINDS = ("person",)                 # the OPERATOR node universe, D-022
GROUP_KINDS = ("container", "organization", "policy_area")

OPERATOR_DEFINITION = (
    "OPERATOR = PERSONS ONLY (D-022). The scored matrix is indexed over the person "
    "nodes of the Hill personnel spine and nothing else; N = person count. Its only "
    "edge layer is co_tenure, whose undirected weight is "
    "w_tiered_lower = kappa_max * tier_pair * (1 - exp(-guaranteed_days / TAU_DAYS)) "
    "* shared_role_attenuation, derived from duration-attributed container support; "
    "for pairs with STRICTLY POSITIVE guaranteed overlap; POSSIBLE_ONLY and "
    "ZERO_OVERLAP pairs carry no operator weight. Edges are deduplicated to the "
    "strongest support per unordered pair, made bidirectional and row-normalised by "
    "layer_balanced_transition (a no-op balancing step at one layer, i.e. plain row "
    "normalisation of the co-tenure strengths). PageRank runs on that transition at "
    "damping 0.7/0.85/0.95 with a UNIFORM restart over persons (1/N each). The "
    "eigenvector is component-local on the symmetrised transition. Containers, "
    "organisations and policy areas are NOT nodes and contribute NO operator edges; "
    "they are emitted as grouping layers and as a groups roster."
)

PENDING_RULINGS = [
    {
        "id": "decay",
        "question": (
            "should co-tenure weight decay with elapsed time since the shared service "
            "ended, so a tie from 1998 counts less than the same tie from 2024?"
        ),
        "status": "OPEN - Paul's ruling",
        "applied_in_this_build": False,
        "current_behaviour": (
            "no decay of any kind; w_lower depends only on guaranteed overlap DAYS, "
            "never on how long ago those days were"
        ),
    },
    {
        "id": "container_size_normalisation",
        "question": (
            "should an edge formed inside a 3,373-person container be down-weighted "
            "relative to one formed inside a 4-person office?"
        ),
        "status": "OPEN - Paul's ruling",
        "applied_in_this_build": False,
        "current_behaviour": (
            "no container-size normalisation; kappa depends only on container KIND "
            "(design 6.2), never on how many people the container held"
        ),
    },
]

STATEMENT = (
    "A network of PEOPLE. Observed payroll co-tenure only. An edge exists between two "
    "people only where the guaranteed service calendars they were printed under actually "
    "intersect. People who held the same office at non-overlapping times carry NO edge "
    "here: that would assert a relationship the record does not support. Sequence is kept "
    "as trajectory and as office-to-office structure, never as a social tie. Offices, "
    "organisations and policy areas are NOT people and are not scored: they are grouping "
    "layers beside the network, not nodes inside it. Not identity findings, not primary "
    "weights, no influence claim."
)

WEIGHT_SEMANTICS = (
    "co_tenure: for each unordered person pair, every shared container's unioned core "
    "calendars are intersected (design 0A: union BEFORE intersect), the resulting overlap "
    "segments are unioned again ACROSS containers so simultaneous multi-office assignments "
    "do not double count, and guaranteed_days is the day count of that cross-container "
    "unioned overlap calendar. w_lower = 1 - exp(-guaranteed_days / TAU_DAYS) verbatim from "
    "build_exploratory_temporal_tier.duration_weight. kappa is the MAXIMUM design-6.2 "
    "container proximity over the containers that actually contributed guaranteed days (the "
    "closest shared container governs the tie); kappa_min is emitted beside it so the "
    "alternative is recomputable. tier_strength is the minimum spine identity-tier strength "
    "over the two endpoints. w_kappa_lower = kappa * w_lower is the owner's stated rule; "
    "w_tiered_lower = kappa * tier_strength * w_lower * shared_role_attenuation "
    "is what the operator consumes. Intern compensation headers and admin pools "
    "supply no operator edges. "
    "POSSIBLE_ONLY pairs (envelopes intersect, guaranteed cores do not) are emitted with "
    "w_lower 0.0 and are excluded from the operator, exactly as in the exploratory tier. "
    "ZERO_OVERLAP pairs are counted as REJECTED and never emitted. "
    "co_tenure is the ONLY operator layer. "
    "GROUPING LAYERS, none of which touch the operator (every row carries "
    "operator_included False and operator_weight 0.0): "
    "membership: person -> container, grouping_weight kappa(container) * "
    "tier_strength(person), retained as a DESCRIPTIVE attachment strength for the Groups "
    "surface. "
    "revolving: member-office container -> LDA registrant organization, carrying the "
    "verified exploratory temporal layer's w_tiered_lower as a source-side descriptive "
    "strength for guaranteed ordered paths, with ambiguous bioguide-to-office mappings "
    "dividing rather than duplicating source weight; plus, where the source names them, "
    "per-person registrant records joining a spine person to that organisation through "
    "the contributing LDA person id. "
    "policy_area: strict Politico-to-payroll current-staffer links become undated "
    "person -> policy-area memberships. Their duration weight is zero because the "
    "directory card is undated; they never enter w_work and, from v4, never enter the "
    "operator either."
)

INTERVAL_SEMANTICS = (
    "core(e) = [start_latest, end_earliest); envelope(e) = [start_earliest, end_latest), "
    "half-open, per STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md section 0A. House-lane "
    "episodes are enriched to DAY precision by joining the spine span's source_row_ids back "
    "to the House SOD observations' printed service_start/service_end (core == envelope). "
    "OWNER RULING 2026-09-07: a REPORT_PERIOD core is the UNION of the periods observed - "
    "ONE half-open interval per contiguous run of the spine's contiguous_runs, never "
    "first-period-start to last-period-end. The ENVELOPE is deliberately not split by run "
    "and stays widened one reporting period each side of the whole span, because a person "
    "observed in P1, P2 and P4 could genuinely have served P3 under a missing filing; "
    "splitting the core alone can only move a pair from GUARANTEED to POSSIBLE_ONLY."
)


class BuildError(RuntimeError):
    pass


# --------------------------------------------------------------------------- helpers
def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha_text(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def edge_id_of(*parts: str) -> str:
    """Deterministic edge id over a NUL-joined key. Cheaper than canonical JSON on
    tens of millions of rows, same 64-hex sha256 shape as the exploratory tier."""
    return "staffer-social:edge:" + hashlib.sha256("\x00".join(parts).encode("utf-8")).hexdigest()


def review_assertion_id(*parts: str) -> str:
    return "staffer-social:review:" + hashlib.sha256(
        "\x00".join(parts).encode("utf-8")
    ).hexdigest()


def policy_provenance(record: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize the direct Politico bridge without requiring a legacy Quorum id."""
    return {
        "issue_area": record["issue_area"],
        "observed_at": record.get("observed_at"),
        "source_profile_uuid": record.get("source_profile_uuid"),
        "source_profile_uuids": sorted(record.get("source_profile_uuids") or []),
        "identity_bridge": "POLITICO_EXACT_NAME_PLUS_CURRENT_OFFICE_TO_PAYROLL_SPINE",
    }


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def parse_day(value: Any) -> date | None:
    if value is None or value == "":
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise BuildError(f"date is not canonical ISO-8601: {value!r}")
    return parsed


def point_interval(start: date, end_exclusive: date) -> UncertainInterval:
    """Verbatim from build_exploratory_temporal_tier.point_interval."""
    interval = UncertainInterval(
        start_earliest=start, start_latest=start,
        end_earliest=end_exclusive, end_latest=end_exclusive,
        start_precision="day", end_precision="day", asserted_current=False,
    )
    interval.validate()
    return interval


def union_half_open(ranges: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    """Verbatim logic from build_exploratory_temporal_tier.union_half_open, on ordinals.

    Merges overlapping AND adjacent runs, as math section 6 requires so duplicate or
    back-to-back reporting periods cannot inflate a calendar.
    """
    cleaned = [(s, e) for s, e in ranges if e > s]
    if not cleaned:
        return []
    cleaned.sort()
    merged = [list(cleaned[0])]
    for s, e in cleaned[1:]:
        if s <= merged[-1][1]:
            if e > merged[-1][1]:
                merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(a, b) for a, b in merged]


# ------------------------------------------------------- reporting-period calendars
# Mirrors build_hill_personnel_spine.quarter_bounds / senate_window.  The two chambers
# have SEPARATE calendars and are never mixed: House reporting periods are quarters
# (YYYYQn); Senate periods are semiannual windows named by their START date, where
# YYYY-04-01 covers Apr 1 - Sep 30 of that year and YYYY-10-01 covers Oct 1 - Mar 31 of
# the NEXT year.  A "contiguous run" is a maximal block of consecutive periods on ONE of
# those calendars, so a run never spans a calendar gap.
QUARTER_TOKEN_RE = re.compile(r"^(\d{4})Q([1-4])$")


def period_bounds(chamber: str, token: Any) -> tuple[date, date]:
    """INCLUSIVE [start, end] calendar bounds of one reporting-period token."""
    text = str(token or "").strip()
    if chamber == "house":
        match = QUARTER_TOKEN_RE.match(text.upper())
        if not match:
            raise BuildError(f"unparseable house period token {token!r}")
        year, quarter = int(match.group(1)), int(match.group(2))
        start = date(year, 3 * quarter - 2, 1)
        end = (date(year, 12, 31) if quarter == 4
               else date(year, 3 * quarter + 1, 1) - timedelta(days=1))
        return start, end
    day = parse_day(text[:10]) if len(text) >= 10 else None
    if day is None:
        raise BuildError(f"unparseable senate period token {token!r}")
    if day.month >= 10:
        return date(day.year, 10, 1), date(day.year + 1, 3, 31)
    if day.month <= 3:
        return date(day.year - 1, 10, 1), date(day.year, 3, 31)
    return date(day.year, 4, 1), date(day.year, 9, 30)


def period_run_boundaries_agree(chamber: str, raw_runs, core_s: int, core_e: int) -> bool:
    """Does the spine's own core span equal the calendar of its first and last runs?

    A REPORT_PERIOD span's core is written by the spine as
    [period_bounds(first_period).start, period_bounds(last_period).end], and
    contiguous_runs[0][0] IS first_period while contiguous_runs[-1][1] IS last_period.
    Recomputing both ends here and comparing them to the row's own dates is a real
    cross-check of THIS module's period arithmetic against the spine's: it can fail.
    """
    try:
        start = period_bounds(chamber, raw_runs[0][0])[0].toordinal()
        end = period_bounds(chamber, raw_runs[-1][1])[1].toordinal() + 1
    except BuildError:
        return False
    return start == core_s and end == core_e


def span_core_runs(row: Mapping[str, Any], chamber: str, core_s: int, core_e: int):
    """Half-open [start, end) ordinal runs for ONE span's REPORT_PERIOD core calendar.

    OWNER RULING 2026-09-07 (co-tenure clique audit): a REPORT_PERIOD stint is the
    UNION OF THE PERIODS ACTUALLY OBSERVED, never min-to-max.  48,897 of 72,266 Senate
    stints were too long under the old rule - the worst spanned 4,567 days on four
    observations - and every one of those extra days was a chance to fabricate a
    guaranteed co-tenure edge with somebody who was never there.

    The spine states the union as ``contiguous_runs`` - [[start_period, end_period],
    ...] with no calendar gap inside a run.  One run -> one interval -> one stint.

    Two deliberate properties:
      * The FIRST run's start and the LAST run's end are taken from the row's own core
        dates rather than recomputed, so a SINGLE-RUN span is bit-identical to the
        pre-ruling behaviour and only interior boundaries need period arithmetic.
      * Every run is clamped into [core_s, core_e), so this path can only ever NARROW a
        span's calendar.  A span whose core was written from printed service dates can
        never be widened by a coarser period token.

    Returns (runs, basis) where basis is "contiguous_runs" or "span_min_to_max".
    """
    raw = row.get("contiguous_runs")
    if not isinstance(raw, (list, tuple)) or not raw:
        return [(core_s, core_e)], "span_min_to_max"
    last = len(raw) - 1
    runs: list[tuple[int, int]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise BuildError(
                f"contiguous_runs entry {index} is not a [start_period, end_period] "
                f"pair: {item!r}"
            )
        start = core_s if index == 0 else period_bounds(chamber, item[0])[0].toordinal()
        end = core_e if index == last else period_bounds(chamber, item[1])[1].toordinal() + 1
        start = max(start, core_s)
        end = min(end, core_e)
        if end > start:
            runs.append((start, end))
    if not runs:
        return [(core_s, core_e)], "span_min_to_max"
    return union_half_open(runs), "contiguous_runs"


def intersect_calendars(left, right):
    """Intersect two unioned half-open calendars (ordinals). Linear merge."""
    out = []
    i = j = 0
    while i < len(left) and j < len(right):
        lo = max(left[i][0], right[j][0])
        hi = min(left[i][1], right[j][1])
        if hi > lo:
            out.append((lo, hi))
        if left[i][1] < right[j][1]:
            i += 1
        else:
            j += 1
    return out


def calendar_days(ranges) -> int:
    return sum(e - s for s, e in ranges)


def union_pair_days(pair_keys, starts, ends, excluded_keys=()):
    """Union envelope intersections per pair, including across containers."""
    pair_keys = np.asarray(pair_keys, dtype=np.int64)
    starts = np.asarray(starts, dtype=np.int32)
    ends = np.asarray(ends, dtype=np.int32)
    if not (pair_keys.shape == starts.shape == ends.shape) or pair_keys.ndim != 1:
        raise BuildError("pair overlap arrays must be matching one-dimensional arrays")
    if np.any(ends <= starts):
        raise BuildError("pair overlap intervals must have positive duration")
    if len(excluded_keys):
        # Pair codes span billions; avoid a lookup table or a sort/copy of all
        # envelope segments merely to test membership in sorted guaranteed keys.
        excluded = np.asarray(excluded_keys, dtype=np.int64)
        if np.any(excluded[1:] < excluded[:-1]):
            excluded = np.sort(excluded)
        keep = np.ones(pair_keys.size, dtype=bool)
        for offset in range(0, pair_keys.size, 250_000):
            chunk = pair_keys[offset:offset + 250_000]
            positions = np.searchsorted(excluded, chunk)
            hit = positions < excluded.size
            hit[hit] = excluded[positions[hit]] == chunk[hit]
            keep[offset:offset + chunk.size] = ~hit
        pair_keys, starts, ends = pair_keys[keep], starts[keep], ends[keep]
    if not pair_keys.size:
        return np.zeros(0, np.int64), np.zeros(0, np.int64)
    order = np.lexsort((starts, pair_keys))
    pair_keys, starts, ends = pair_keys[order], starts[order], ends[order]
    boundaries = np.flatnonzero(np.r_[True, pair_keys[1:] != pair_keys[:-1]])
    stops = np.r_[boundaries[1:], pair_keys.size]
    days = np.zeros(boundaries.size, dtype=np.int64)
    for index, (lo, hi) in enumerate(zip(boundaries, stops)):
        left, right, total = int(starts[lo]), int(ends[lo]), 0
        for pos in range(int(lo) + 1, int(hi)):
            start, end = int(starts[pos]), int(ends[pos])
            if start <= right:
                right = max(right, end)
            else:
                total += right - left
                left, right = start, end
        days[index] = total + right - left
    return pair_keys[boundaries], days


def validated_person_tiers(person_ids, person_tier):
    missing = [pid for pid in person_ids if person_tier.get(pid) not in S_STRENGTH]
    if missing:
        raise BuildError(f"Missing or invalid identity tier for {len(missing)} people: {missing[:5]}")
    return [person_tier[pid] for pid in person_ids]


def deterministic_leading_eigenpair(matrix):
    """Positive fixed initialization makes the repair independent of RNG state."""
    vals, vecs = eigsh(matrix, k=1, which="LA", maxiter=20000, tol=1e-12,
                       v0=np.ones(matrix.shape[0], dtype=np.float64))
    vec = np.abs(np.asarray(vecs[:, -1]).ravel())
    total = vec.sum()
    if not np.isfinite(total) or total <= 0:
        raise BuildError("degenerate eigenvector")
    vec /= total
    residual = np.linalg.norm(matrix @ vec - float(vals[-1]) * vec)
    scale = max(np.linalg.norm(matrix @ vec), np.finfo(float).tiny)
    if residual / scale > 1e-9:
        raise BuildError("direct eigenvector repair failed the eigenpair residual check")
    return float(vals[-1]), vec


def duration_weight(days: int, tau_days: float) -> float:
    """Verbatim from build_exploratory_temporal_tier.duration_weight."""
    if days < 0:
        raise BuildError("overlap days must be nonnegative")
    return 1.0 - math.exp(-float(days) / tau_days)


OFFICE_DIVERSITY_DEFINITION = (
    "office_diversity - normalised Simpson diversity of the OFFICES that produced a "
    "person's co-tenure ties. For person i let strength(i) be the sum of that person's "
    "co-tenure operator weights. Each co-tenure edge e=(i,j) with weight w_e contributes "
    "w_e / strength(i) of person i's tie mass, and that contribution is split by "
    "guaranteed container days after shared-role damping, normalized to sum to one, "
    "across the containers that actually supplied guaranteed overlap days to e - exactly "
    "the set published on the edge as container_ids. Summing gives m_ic, the share of "
    "person i's co-tenure mass attributable to container c, with sum_c m_ic = 1 for any "
    "person holding at least one edge. Then "
    "office_diversity(i) = clip(1 - sum_c m_ic^2, 0, 1) / (1 - 1/K), where K is the "
    "number of distinct containers in the generation. Isolated persons score 0. Because "
    "the mass is row-normalised the statistic is invariant to a scalar increase in a "
    "person's total tie strength and does NOT restate degree. "
    "THIS REPLACES bridging_diversity, which computed Simpson over node KINDS and so only "
    "ever measured how many of the four heterogeneous node kinds a node touched - a "
    "property of the old node universe, not of bridging between offices. The old field "
    "name is deliberately absent from the payload so no consumer can read the new number "
    "under the old meaning."
)


def office_diversity_simpson(
    person_a,
    person_b,
    weight,
    container_ptr,
    container_flat,
    n_people: int,
    n_containers: int,
    *,
    container_shares,
    chunk: int = 2_000_000,
):
    """Return (office_diversity, distinct_offices, container_mass_matrix).

    ``container_ptr``/``container_flat`` are a CSR-style listing of the containers that
    contributed guaranteed overlap days to each supplied edge, in edge order.  The
    accumulated (person, container) matrix has at most one nonzero per person-container
    cell, so it stays small (bounded by the person_container_cells count) no matter how
    many edges are folded into it; the edge stream is chunked so the intermediate COO
    never grows with the full edge count.
    """
    a = np.asarray(person_a, dtype=np.int64)
    b = np.asarray(person_b, dtype=np.int64)
    w = np.asarray(weight, dtype=np.float64)
    ptr = np.asarray(container_ptr, dtype=np.int64)
    flat = np.asarray(container_flat, dtype=np.int64)
    shares = np.asarray(container_shares, dtype=np.float64)
    if shares.shape != flat.shape or np.any(~np.isfinite(shares)) or np.any(shares <= 0):
        raise BuildError("office diversity requires positive finite attributed shares")
    if not (a.size == b.size == w.size):
        raise BuildError("office diversity edge arrays must have equal length")
    if ptr.size != a.size + 1:
        raise BuildError("office diversity container pointer does not match the edges")
    if a.size and int(ptr[-1]) != flat.size:
        raise BuildError("office diversity container pointer does not close on the flat array")
    if n_people <= 0:
        raise BuildError("office diversity needs at least one person")

    strength = np.bincount(
        np.concatenate((a, b)), weights=np.concatenate((w, w)), minlength=n_people
    )
    mass = sparse.csr_matrix((n_people, max(n_containers, 1)), dtype=np.float64)
    counts = np.maximum(np.diff(ptr), 1) if a.size else np.zeros(0, dtype=np.int64)
    for lo in range(0, a.size, chunk):
        hi = min(lo + chunk, a.size)
        seg_lo, seg_hi = int(ptr[lo]), int(ptr[hi])
        cols = flat[seg_lo:seg_hi]
        repeat = np.diff(ptr[lo:hi + 1])
        ea = np.repeat(a[lo:hi], repeat)
        eb = np.repeat(b[lo:hi], repeat)
        share = np.repeat(w[lo:hi], repeat) * shares[seg_lo:seg_hi]
        rows_ix = np.concatenate((ea, eb))
        cols_ix = np.concatenate((cols, cols))
        vals = np.concatenate(
            (
                np.divide(share, strength[ea], out=np.zeros_like(share), where=strength[ea] > 0),
                np.divide(share, strength[eb], out=np.zeros_like(share), where=strength[eb] > 0),
            )
        )
        mass = mass + sparse.coo_matrix(
            (vals, (rows_ix, cols_ix)), shape=(n_people, max(n_containers, 1))
        ).tocsr()
        del rows_ix, cols_ix, vals, ea, eb, share, cols, repeat
    mass.sum_duplicates()
    mass.eliminate_zeros()
    squared = np.asarray(mass.multiply(mass).sum(axis=1)).ravel()
    distinct = np.asarray(mass.getnnz(axis=1)).ravel().astype(np.int64)
    raw = np.clip(1.0 - squared, 0.0, 1.0)
    if n_containers > 1:
        diversity = raw / (1.0 - 1.0 / float(n_containers))
    else:
        diversity = np.zeros(n_people, dtype=np.float64)
    diversity = np.clip(diversity, 0.0, 1.0)
    diversity[strength <= 0] = 0.0
    distinct[strength <= 0] = 0
    return diversity, distinct, mass


def load_spine_id_map(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """Read a {legacy_person_id, person_id, reason} re-key map emitted by a spine build."""
    mapping: dict[str, str] = {}
    reasons = Counter()
    rows_read = 0
    identity_rows = 0
    for row in read_rows(path):
        rows_read += 1
        legacy = row.get("legacy_person_id")
        current = row.get("person_id")
        if not isinstance(legacy, str) or not isinstance(current, str) or not legacy or not current:
            raise BuildError(
                f"spine id map row {rows_read} is missing legacy_person_id or person_id"
            )
        previous = mapping.get(legacy)
        if previous is not None and previous != current:
            raise BuildError(
                f"spine id map is not a function: {legacy} -> {previous!r} and {current!r}"
            )
        mapping[legacy] = current
        reasons[str(row.get("reason") or "UNSPECIFIED")] += 1
        if legacy == current:
            identity_rows += 1
    return mapping, {
        "rows_read": rows_read,
        "distinct_legacy_ids": len(mapping),
        "identity_rows": identity_rows,
        "rows_by_reason": dict(sorted(reasons.items())),
    }


def politico_bound_spine_files(link_receipt: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract the Hill-spine files the Politico direct-link receipt binds.

    The bridge receipt records its inputs as a mapping of ABSOLUTE PATH -> {bytes,
    sha256}.  The spine files it read are the id namespace its spine_person_id values
    live in, so their declared sha256 is what tells us whether those ids are current.
    """
    wanted = ("hill_person_spine.ndjson.gz", "hill_person_office_spans.ndjson.gz")
    found: dict[str, dict[str, Any]] = {}
    for raw_path, meta in (link_receipt.get("inputs") or {}).items():
        name = str(raw_path).replace("\\", "/").rsplit("/", 1)[-1]
        if name not in wanted or not isinstance(meta, Mapping):
            continue
        entry = {
            "path": str(raw_path),
            "generation": str(raw_path).replace("\\", "/").rsplit("/", 2)[-2],
            "sha256": meta.get("sha256"),
            "bytes": meta.get("bytes"),
        }
        previous = found.get(name)
        if previous is not None and previous["sha256"] != entry["sha256"]:
            raise BuildError(
                f"Politico link receipt binds two different {name} inputs; the spine "
                "namespace is ambiguous"
            )
        found[name] = entry
    return found


def cross_check_intervals() -> dict[str, Any]:
    """Prove the local ordinal intersection agrees with the REVIEWED intervals.py.

    build_exploratory_temporal_tier calls intervals.py per intersection piece; that is
    O(pairs) and this build has tens of millions of pairs, so the reviewed function is
    instead exercised on a deterministic battery that covers every relative position of
    two half-open runs.  A disagreement aborts the build.
    """
    base = date(2015, 1, 1).toordinal()
    cases = []
    for a0, a1 in ((0, 100), (0, 10), (50, 60), (0, 1)):
        for b0, b1 in ((0, 100), (10, 20), (90, 200), (100, 110), (200, 300), (5, 15)):
            cases.append((a0, a1, b0, b1))
    checked = 0
    for a0, a1, b0, b1 in cases:
        ia = point_interval(date.fromordinal(base + a0), date.fromordinal(base + a1))
        ib = point_interval(date.fromordinal(base + b0), date.fromordinal(base + b1))
        g = guaranteed_overlap_days(ia, ib)
        p = possible_overlap_days(ia, ib)
        local = calendar_days(intersect_calendars([(a0, a1)], [(b0, b1)]))
        if g != local or p != local:
            raise BuildError(
                f"local intersection disagrees with reviewed intervals.py: {(a0,a1,b0,b1)} "
                f"guaranteed={g} possible={p} local={local}"
            )
        checked += 1
    return {"cases_checked": checked, "module": "fec/staffer_network/intervals.py", "status": "AGREE"}


def _glassbox_summary(event: str, payload: Mapping[str, Any]) -> str:
    """Short human summary for emit.ps1's -Summary: event name plus payload
    key=value pairs, truncated to stay well under emit.ps1's expectations."""
    parts = [f"{key}={value}" for key, value in payload.items()]
    summary = event + (" " + " ".join(parts) if parts else "")
    if len(summary) > 200:
        summary = summary[:197] + "..."
    return summary


def emit_glassbox(*, enabled: bool, event: str, payload: Mapping[str, Any]) -> None:
    if not enabled or not EMIT_PS1.exists():
        return
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(EMIT_PS1),
             "-Source", GLASSBOX_SOURCE, "-Kind", event,
             "-Summary", _glassbox_summary(event, payload),
             "-MetadataJson", json.dumps(payload, sort_keys=True)],
            check=False, capture_output=True, timeout=30,
        )
        if result.returncode != 0:
            stderr_text = (result.stderr or b"").decode("utf-8", "replace")[:200]
            print(
                f"glassbox emit failed: kind={event!r} returncode={result.returncode} "
                f"stderr={stderr_text!r}",
                file=sys.stderr,
            )
    except Exception:
        return


def open_gzip(path: Path):
    """mtime 0, blank name -- writes to a temp file in the same directory; write_rows renames it
    onto path with os.replace only after a clean close, mirroring build_hill_personnel_spine.py's
    write_ndjson_gz (:484-499, mkstemp + os.replace) so a killed or OOM'd run on a multi-GB edge
    file cannot leave a truncated .ndjson.gz that blocks the next run's empty-output-dir guard."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    temporary = Path(temporary_name)
    raw = temporary.open("wb")
    return gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0), raw, temporary


def write_rows(path: Path, rows: Iterable[Mapping[str, Any]]) -> int:
    handle, raw, temporary = open_gzip(path)
    n = 0
    try:
        try:
            for row in rows:
                handle.write(canonical_json_bytes(row))
                handle.write(b"\n")
                n += 1
        finally:
            handle.close()
            raw.close()
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    return n


def key64(text: str) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=8).digest(), "big", signed=False) >> 1


# --------------------------------------------------------------------------- inputs
def input_paths(root: Path, args: argparse.Namespace) -> dict[str, Path]:
    sn = root / "audits" / "staffer_network"
    spine = (
        Path(args.hill_spine_root).resolve()
        if args.hill_spine_root
        else sn / "hill_personnel_spine_20260907_v7_primary"
    )
    house = (
        Path(args.house_ledger_root).resolve()
        if args.house_ledger_root
        else sn / "house_personnel_ledger_20260903_v4_primary"
    )
    senate_committee = (
        Path(args.senate_committee_root).resolve()
        if args.senate_committee_root
        else sn / "senate_committee_payroll_20260903_v3_primary"
    )
    paths = {
        "hill_person_office_spans": spine / "hill_person_office_spans.ndjson.gz",
        "hill_person_spine": spine / "hill_person_spine.ndjson.gz",
        "hill_member_office_index": spine / "member_office_index.ndjson.gz",
        "hill_personnel_spine_receipt": spine / "hill_personnel_spine_receipt.json",
        "house_personnel_observations": house / "house_personnel_observations.ndjson.gz",
        "house_person_office_spans": house / "house_person_office_spans.ndjson.gz",
        "house_personnel_ledger_receipt": house / "house_personnel_ledger_receipt.json",
        "senate_committee_payroll_candidates": senate_committee / "senate_committee_payroll_candidates_2011_2026.ndjson.gz",
        "senate_committee_payroll_receipt": senate_committee / "senate_committee_payroll_receipt.json",
        "politico_direct_policy_memberships": Path(
            args.politico_direct_policy_memberships
        ).resolve(),
        "politico_direct_link_receipt": Path(args.politico_direct_link_receipt).resolve(),
        "exploratory_revolving_edges": Path(args.exploratory_revolving_edges).resolve(),
        "house_person_identity_receipt": sn / "house_person_identity_20260902_v2_primary" / "house_person_identity_receipt.json",
        "roster_congestion": root / "data" / "engine" / "congestion.json",
        "module_intervals": REPOSITORY_ROOT / "fec" / "staffer_network" / "intervals.py",
        "module_network_math": REPOSITORY_ROOT / "fec" / "staffer_network" / "network_math.py",
        "module_ranking_math": REPOSITORY_ROOT / "fec" / "staffer_network" / "ranking_math.py",
        "design_doc": Path(args.design_doc).resolve(),
        "metrics_doc": Path(args.metrics_doc).resolve(),
    }
    if getattr(args, "spine_id_map", None):
        paths["spine_id_map"] = Path(args.spine_id_map).resolve()
    optional = {
        "politico_current_committee_assertions": args.politico_current_committee_assertions,
        "politico_profile_employment_assertions": args.politico_profile_employment_assertions,
        "politico_profile_education_assertions": args.politico_profile_education_assertions,
        "politico_profile_policy_deltas": args.politico_profile_policy_deltas,
        "politico_explicit_committee_side_assertions": (
            args.politico_explicit_committee_side_assertions
        ),
    }
    supplied = {name: value for name, value in optional.items() if value}
    if supplied and len(supplied) != len(optional):
        missing = sorted(set(optional) - set(supplied))
        raise BuildError(
            "Politico review-layer inputs are all-or-none; missing " + ", ".join(missing)
        )
    paths.update({name: Path(value).resolve() for name, value in supplied.items()})
    return paths


def load_day_precision_map(path: Path):
    """(source_file, source_row_index) -> printed service interval, as sorted arrays."""
    keys = []
    starts = []
    ends = []
    undated = 0
    for row in read_rows(path):
        sf = row.get("source_file")
        ri = row.get("source_row_index")
        if not isinstance(sf, str) or ri is None:
            continue
        s = row.get("service_start")
        e = row.get("service_end")
        if not s or not e:
            undated += 1
            continue
        so = date.fromisoformat(s).toordinal()
        eo = date.fromisoformat(e).toordinal() + 1        # printed end day is INCLUSIVE
        if eo <= so:
            undated += 1
            continue
        keys.append(key64(f"house-ledger:{sf}#{ri}"))
        starts.append(so)
        ends.append(eo)
    k = np.asarray(keys, dtype=np.int64)
    order = np.argsort(k, kind="stable")
    return (k[order], np.asarray(starts, dtype=np.int32)[order],
            np.asarray(ends, dtype=np.int32)[order], undated, len(keys))


# Committee side is FOUR-VALUED, not three (owner ruling 2026-09-03).
#   MAJ / MIN      - the staffer sits on a side-specific committee payroll
#   BIPARTISAN     - a nonpartisan professional staffer who HAS no side; a real
#                    value, not missing data
#   UNKNOWN        - missing data: we could not determine which of the three above
#                    applies
# Design 6.2 collapses BIPARTISAN and UNKNOWN into one kappa=0.60 fallback, which
# makes the C-8c coverage bar unreadable: a low number cannot be told apart from
# "side does not apply here". The field stays four-valued so the distinction can be
# filled in later without a schema change, even though nothing on disk can populate
# BIPARTISAN today.
SIDE_VALUES = ("MAJ", "MIN", "BIPARTISAN", "UNKNOWN")


def kappa_for(kind: str, side: str | None) -> tuple[float, str]:
    if kind == "member_office":
        return KAPPA["member_office"], "member_office"
    if kind == "committee":
        if side in ("MAJ", "MIN"):
            return KAPPA["committee_same_side"], "committee_same_side_known"
        if side == "BIPARTISAN":
            return KAPPA["committee_bipartisan"], "committee_bipartisan_no_side"
        return KAPPA["committee_side_unknown"], "committee_side_unknown"
    if kind == "leadership":
        return KAPPA["leadership"], "leadership"
    if kind == "admin":
        return KAPPA["admin"], "admin"
    return KAPPA["unresolved"], "unresolved"


# A side token must be a WHOLE word. Substring matching reports MIN for
# "COMMITTEE ON MINING" and MAJ for "MAJORCA"; caught by
# test_committee_side_only_fires_on_a_real_token.
SIDE_RE = re.compile(r"(?:^|[^A-Z])(MAJORITY|MINORITY|MAJ|MIN)(?:[^A-Z]|$)")


def committee_side(office_key: str) -> str:
    """Return one of SIDE_VALUES for a committee container.

    A congressional committee employs BOTH majority and minority staff on the same
    payroll, so 'same container' does NOT imply 'same side'. Only a side token in the
    payroll sub-unit string is evidence of side. BIPARTISAN is never returned: no
    source on disk distinguishes a nonpartisan professional staffer from one whose
    side we simply failed to determine, so those all fall to UNKNOWN.
    """
    m = SIDE_RE.search(office_key.upper())
    if not m:
        return "UNKNOWN"
    return "MAJ" if m.group(1).startswith("MAJ") else "MIN"


YEAR_PREFIXES = ("FISCAL YEAR ",)


def normalized_container(office_key: str) -> str:
    up = office_key
    for pref in YEAR_PREFIXES:
        if up.startswith(pref) and len(up) > len(pref) + 5 and up[len(pref):len(pref) + 4].isdigit():
            return up[len(pref) + 5:]
    if len(up) > 5 and up[:4].isdigit() and up[4] == " ":
        return up[5:]
    return up


# --------------------------------------------------------------------------- build
def run(args) -> dict[str, Any]:
    root = Path(args.repository_root).resolve()
    out = Path(args.output).resolve()
    if out.exists() and any(out.iterdir()):
        raise BuildError(f"output directory is not empty: {out}")
    out.mkdir(parents=True, exist_ok=True)
    paths = input_paths(root, args)
    for name, p in paths.items():
        if not p.exists():
            raise BuildError(f"missing input {name}: {p}")
    if args.require_complete_politico_profile_crawl:
        preflight_receipt = json.loads(
            paths["politico_direct_link_receipt"].read_text(encoding="utf-8")
        )
        preflight_gate = preflight_receipt.get("profile_crawl_gate") or {}
        if not (
            preflight_gate.get("status") == "PASS"
            and completion_accepted(preflight_gate, legacy_default=True)
            and int(preflight_gate.get("verification_failure_count") or 0) == 0
            and int(preflight_gate.get("completed_profiles") or 0)
            == int(preflight_gate.get("expected_profiles") or -1)
            and int(preflight_gate.get("unresolved_profiles") or 0) == 0
            and bool(preflight_gate.get("terminal_completion_required"))
        ):
            raise BuildError(
                "Politico bridge receipt does not prove terminal full-profile coverage"
            )

    receipt: dict[str, Any] = {}
    receipt["interval_cross_check"] = cross_check_intervals()

    # ---- person spine ------------------------------------------------------------
    person_tier: dict[str, str] = {}
    person_chambers: dict[str, list[str]] = {}
    person_bios: dict[str, list[str]] = {}
    person_lda: dict[str, str | None] = {}
    person_quorum: dict[str, str | None] = {}
    person_name: dict[str, dict[str, str]] = {}
    for row in read_rows(paths["hill_person_spine"]):
        pid = row["spine_person_id"]
        person_tier[pid] = row["identity_tier"]
        person_chambers[pid] = list(row.get("chambers") or [])
        person_bios[pid] = list(row.get("member_bioguides") or [])
        person_lda[pid] = row.get("lda_source_person_id")
        person_quorum[pid] = row.get("quorum_staff_id")
        person_name[pid] = row.get("payee_key") or {}

    # ---- container metadata ------------------------------------------------------
    container_meta: dict[tuple[str, str], dict[str, Any]] = {}
    container_meta_source_rows = 0
    for row in read_rows(paths["hill_member_office_index"]):
        container_meta_source_rows += 1
        key = (row["chamber"], normalized_container(row["office_key"]))
        current = container_meta.get(key)
        if current is None:
            container_meta[key] = {
                "container_kind": row["container_kind"],
                "member_bioguide": row.get("member_bioguide"),
                "member_resolution_methods": sorted({row.get("member_resolution_method")} - {None}),
                "observation_count": int(row.get("observation_count") or 0),
                "person_count_fragment_sum": int(row.get("person_count") or 0),
                "first_period": row.get("first_period"),
                "last_period": row.get("last_period"),
                "source_office_keys": [row["office_key"]],
            }
            continue
        kinds = {current["container_kind"], row["container_kind"]}
        specific_kinds = kinds - {"unresolved"}
        if len(specific_kinds) > 1:
            raise BuildError(f"container kind conflict after year-prefix normalization: {key}")
        current["container_kind"] = next(iter(specific_kinds), "unresolved")
        bios = {current.get("member_bioguide"), row.get("member_bioguide")} - {None}
        if len(bios) > 1:
            raise BuildError(f"member bioguide conflict after year-prefix normalization: {key}")
        current["member_bioguide"] = next(iter(bios), None)
        current["member_resolution_methods"] = sorted(
            set(current["member_resolution_methods"])
            | ({row.get("member_resolution_method")} - {None})
        )
        current["observation_count"] += int(row.get("observation_count") or 0)
        current["person_count_fragment_sum"] += int(row.get("person_count") or 0)
        periods = [x for x in (current.get("first_period"), row.get("first_period")) if x is not None]
        current["first_period"] = min(periods) if periods else None
        periods = [x for x in (current.get("last_period"), row.get("last_period")) if x is not None]
        current["last_period"] = max(periods) if periods else None
        current["source_office_keys"].append(row["office_key"])

    # ---- day-precision map for the House lane ------------------------------------
    dp_keys, dp_start, dp_end, dp_undated, dp_rows = load_day_precision_map(
        paths["house_personnel_observations"]
    )
    emit_glassbox(enabled=args.glassbox, event="day_precision_map",
                  payload={"rows": int(dp_rows), "undated_rows": int(dp_undated)})

    # ---- episodes ----------------------------------------------------------------
    person_ids: dict[str, int] = {}
    container_ids: dict[tuple[str, str], int] = {}
    episodes: list[tuple] = []
    prec_counts = Counter()
    lane_counts = Counter()
    kind_counts = Counter()
    chamber_counts = Counter()
    source_container_keys: set[tuple[str, str]] = set()
    normalized_container_sources: dict[tuple[str, str], set[str]] = defaultdict(set)
    unmatched_source_rows = 0
    matched_source_rows = 0
    limit_persons = int(getattr(args, "limit_persons", 0) or 0)
    spans_skipped_by_limit = 0
    spans_seen = 0

    # ---- stint census (owner ruling 2026-09-07) ---------------------------------
    # Every counter below is accumulated STREAMING inside the span loop; nothing here
    # holds a per-span list, so the census costs O(1) memory on a 144k-person build.
    stint_total = 0
    spans_multi_run = 0
    spans_with_contiguous_runs = 0
    spans_without_contiguous_runs = 0
    run_boundary_mismatches = 0
    boundary_mismatch_examples: list[dict[str, Any]] = []
    max_run_days = 0
    max_span_days = 0
    run_basis_counts: Counter = Counter()
    run_reductions: list[dict[str, Any]] = []

    def note_reduction(entry: dict[str, Any]) -> None:
        """Keep only the ten largest span->run reductions, bounded memory."""
        run_reductions.append(entry)
        if len(run_reductions) > 200:
            run_reductions.sort(key=lambda item: -item["reduction_days"])
            del run_reductions[10:]

    for row in read_rows(paths["hill_person_office_spans"]):
        spans_seen += 1
        if limit_persons:
            # The limit admits the FIRST limit_persons distinct ids in file order and
            # then drops every later person outright; a person is never half-admitted.
            if row["spine_person_id"] not in person_ids and len(person_ids) >= limit_persons:
                spans_skipped_by_limit += 1
                continue
        pid = person_ids.setdefault(row["spine_person_id"], len(person_ids))
        source_container_keys.add((row["chamber"], row["office_key"]))
        ckey = (row["chamber"], normalized_container(row["office_key"]))
        normalized_container_sources[ckey].add(row["office_key"])
        cid = container_ids.setdefault(ckey, len(container_ids))
        chamber = row["chamber"]
        kind = row["container_kind"]
        core_s = parse_day(row["core"]["start_latest"]).toordinal()
        core_e = parse_day(row["core"]["end_earliest"]).toordinal() + 1     # period end INCLUSIVE
        env_s = parse_day(row["envelope"]["start_earliest"]).toordinal()
        env_e = parse_day(row["envelope"]["end_latest"]).toordinal() + 1
        precision = "REPORT_PERIOD"
        # OWNER RULING 2026-09-07: the REPORT_PERIOD core is the UNION of the observed
        # periods, one interval per contiguous run - NOT first-period-to-last-period.
        core_runs, run_basis = span_core_runs(row, chamber, core_s, core_e)
        raw_runs = row.get("contiguous_runs")
        if run_basis == "contiguous_runs":
            spans_with_contiguous_runs += 1
            # The guard applies only where the row's core WAS written from period
            # bounds. A spine DAY row carries printed service dates in core, which are
            # not period-aligned, so comparing them to period bounds would be a
            # category error rather than a defect.
            if row.get("date_precision") == "REPORT_PERIOD" and not period_run_boundaries_agree(
                    chamber, raw_runs, core_s, core_e):
                run_boundary_mismatches += 1
                if len(boundary_mismatch_examples) < 10:
                    boundary_mismatch_examples.append({
                        "spine_person_id": row["spine_person_id"],
                        "chamber": chamber,
                        "office_key": row["office_key"],
                        "first_period": row.get("first_period"),
                        "last_period": row.get("last_period"),
                        "contiguous_runs": raw_runs[:4],
                        "core": dict(row["core"]),
                    })
        else:
            spans_without_contiguous_runs += 1
        # The ENVELOPE is deliberately NOT split by run. It is the "could have been"
        # calendar, and a person observed in P1, P2 and P4 could genuinely have served
        # P3 under a missing filing, so the span-wide envelope is the honest possible
        # interval. Splitting the core alone can only move pairs from GUARANTEED to
        # POSSIBLE_ONLY (zero operator weight); it can never invent one.
        env_runs = [(env_s, env_e)]
        if chamber == "house":
            got = []
            miss = 0
            for rid in row["source_row_ids"]:
                k = key64(rid)
                i = np.searchsorted(dp_keys, k)
                if i < dp_keys.size and dp_keys[i] == k:
                    got.append((int(dp_start[i]), int(dp_end[i])))
                else:
                    miss += 1
            if got and miss == 0:
                # Printed service dates are strictly better evidence than the period
                # tokens, and union_half_open already yields one interval per maximal
                # contiguous day-run, so the House DAY lane keeps its exact dates and
                # its runs come from those dates.
                core_runs = union_half_open(got)
                run_basis = "day_intervals"
                env_runs = list(core_runs)
                precision = "DAY"
                matched_source_rows += len(got)
            else:
                unmatched_source_rows += miss
        prec_counts[precision] += 1
        lane_counts[row["source_lane"][0] if row.get("source_lane") else "unknown"] += 1
        kind_counts[kind] += 1
        chamber_counts[chamber] += 1
        run_basis_counts[run_basis] += 1
        stint_total += len(core_runs)
        span_days = int(core_e - core_s)
        longest_run_days = max(int(end - start) for start, end in core_runs)
        if span_days > max_span_days:
            max_span_days = span_days
        if longest_run_days > max_run_days:
            max_run_days = longest_run_days
        if len(core_runs) > 1:
            spans_multi_run += 1
            note_reduction({
                "spine_person_id": row["spine_person_id"],
                "chamber": chamber,
                "office_key": row["office_key"],
                "date_precision": precision,
                "run_basis": run_basis,
                "run_count": len(core_runs),
                "span_days": span_days,
                "longest_run_days": longest_run_days,
                "reduction_days": span_days - longest_run_days,
            })
        episodes.append((pid, cid, tuple(core_runs), tuple(env_runs), precision,
                         chamber, kind, row.get("member_bioguide"), row.get("status"),
                         row.get("title_last") or "", int(row.get("periods_observed") or 0),
                         run_basis))

    inv_person = {v: k for k, v in person_ids.items()}
    inv_container = {v: k for k, v in container_ids.items()}
    NP = len(person_ids)
    NC = len(container_ids)
    if NP == 0:
        raise BuildError("the person universe is empty; a persons-only operator needs people")
    limited_run = bool(limit_persons)
    receipt["limited_run"] = {
        "limited_run": limited_run,
        "limit_persons": limit_persons or None,
        "spans_rows_seen": int(spans_seen),
        "spans_rows_skipped_by_limit": int(spans_skipped_by_limit),
        "persons_admitted": NP,
        "rule": (
            "the first --limit-persons distinct spine_person_ids in hill_person_office_"
            "spans file order are admitted whole; every later person's rows are dropped"
        ),
        "warning": (
            "SMOKE TEST ONLY. hill_person_office_spans is ordered by spine_person_id, a "
            "sha256 digest, so a prefix is a pseudo-random subsample of people: co-tenure "
            "pair counts fall roughly as (persons_admitted / full population)^2 and no "
            "count in this receipt is representative of a full build."
        ) if limited_run else None,
    }

    # ---- stint census + the period-arithmetic guard (owner ruling 2026-09-07) -----
    # A boundary mismatch means THIS module's period_bounds and the spine's disagree, or
    # contiguous_runs disagrees with the row's own first_period/last_period. Either way
    # every derived interval below it is untrustworthy, so the build stops.
    if run_boundary_mismatches:
        raise BuildError(
            f"{run_boundary_mismatches} REPORT_PERIOD spans whose contiguous_runs "
            f"endpoints do not reproduce their own core dates; first example: "
            f"{boundary_mismatch_examples[0] if boundary_mismatch_examples else None}"
        )
    run_reductions.sort(key=lambda item: (-item["reduction_days"], item["spine_person_id"],
                                          item["office_key"]))
    stints_from_contiguous_runs = (
        spans_without_contiguous_runs == 0 and spans_with_contiguous_runs > 0
    )
    receipt["stints_from_contiguous_runs"] = bool(stints_from_contiguous_runs)
    receipt["stint_census"] = {
        "ruling": (
            "owner ruling 2026-09-07 (co-tenure clique audit): a REPORT_PERIOD stint is "
            "the UNION of the periods observed, not first-period-to-last-period. "
            "48,897 of 72,266 Senate stints were too long under the old rule, the worst "
            "spanning 4,567 days on four observations."
        ),
        "spans": len(episodes),
        "stints": int(stint_total),
        "spans_with_multiple_runs": int(spans_multi_run),
        "spans_with_contiguous_runs_field": int(spans_with_contiguous_runs),
        "spans_without_contiguous_runs_field": int(spans_without_contiguous_runs),
        "stints_from_contiguous_runs": bool(stints_from_contiguous_runs),
        "run_basis_counts": dict(sorted(run_basis_counts.items())),
        "max_run_days": int(max_run_days),
        "max_span_days": int(max_span_days),
        "days_removed_by_the_run_rule_on_the_longest_span": int(max_span_days - max_run_days),
        "period_boundary_mismatches": int(run_boundary_mismatches),
        "largest_span_to_run_reductions": run_reductions[:10],
        "fallback_rule": (
            "a span with no usable contiguous_runs falls back to min-to-max and stamps "
            "stints_from_contiguous_runs false for the WHOLE build; on a spine that "
            "emits contiguous_runs the flag must be true"
        ),
        "envelope_rule": (
            "the envelope is NOT split by run. Splitting the core alone can only move a "
            "pair from GUARANTEED to POSSIBLE_ONLY (zero operator weight); it can never "
            "invent an edge."
        ),
        "max_days_note": (
            "max_run_days and max_span_days are maxima over DIFFERENT spans in general; "
            "the pairwise reductions are in largest_span_to_run_reductions"
        ),
    }

    # container attributes
    c_kind = [None] * NC
    c_side = [None] * NC
    c_kappa = np.zeros(NC, dtype=np.float64)
    c_kappa_bucket = [None] * NC
    c_bio = [None] * NC
    c_chamber = [None] * NC
    for (ch, ok), cid in container_ids.items():
        meta = container_meta.get((ch, ok), {})
        kind = meta.get("container_kind") or "unresolved"
        side = committee_side(ok) if kind == "committee" else None
        kap, bucket = kappa_for(kind, side)
        c_kind[cid] = kind
        c_side[cid] = side
        c_kappa[cid] = kap
        c_kappa_bucket[cid] = bucket
        c_bio[cid] = meta.get("member_bioguide")
        c_chamber[cid] = ch

    BUCKETS = ("member_office", "committee_same_side_known", "committee_side_unknown",
               "committee_bipartisan_no_side", "leadership", "admin", "unresolved")
    BUCKET_DIAL = {"member_office": "member_office",
                   "committee_same_side_known": "committee_same_side",
                   "committee_side_unknown": "committee_side_unknown",
                   "committee_bipartisan_no_side": "committee_bipartisan",
                   "leadership": "leadership", "admin": "admin", "unresolved": "unresolved"}
    COMMITTEE_BUCKETS = ("committee_same_side_known", "committee_side_unknown",
                         "committee_bipartisan_no_side")
    bucket_pos = {b: i for i, b in enumerate(BUCKETS)}
    c_bucket_idx = [bucket_pos[c_kappa_bucket[c]] for c in range(NC)]

    def mask_table(kappa_by_bucket):
        """kappa max/min for all 2**len(BUCKETS) possible bucket bitmasks."""
        vals = [kappa_by_bucket[BUCKET_DIAL[b]] for b in BUCKETS]
        hi = np.zeros(1 << len(BUCKETS), dtype=np.float64)
        lo = np.ones(1 << len(BUCKETS), dtype=np.float64)
        for m in range(1, 1 << len(BUCKETS)):
            sel = [vals[i] for i in range(len(BUCKETS)) if m & (1 << i)]
            hi[m] = max(sel)
            lo[m] = min(sel)
        return hi, lo

    # ---- per (person, container) unioned calendars -------------------------------
    pc_core: dict[tuple[int, int], list] = defaultdict(list)
    pc_env: dict[tuple[int, int], list] = defaultdict(list)
    pc_shared = set()
    for ep in episodes:
        pc_core[(ep[0], ep[1])].extend(ep[2])
        pc_env[(ep[0], ep[1])].extend(ep[3])
        if shared_role(ep[9]):
            pc_shared.add((ep[0], ep[1]))
    by_container: dict[int, list[tuple[int, list, list]]] = defaultdict(list)
    for (p, c), runs in pc_core.items():
        by_container[c].append((p, union_half_open(runs), union_half_open(pc_env[(p, c)])))

    # ---- co-tenure container eligibility (owner ruling 2026-09-07) ---------------
    # ONE eligibility set, consumed by BOTH the candidate-pair census below and the
    # co-tenure sweep after it. They must see the same universe: the D-019 rejection
    # count is census MINUS admitted, so gating only the sweep would silently
    # re-label every excluded admin pair as "rejected for zero overlap" - a false
    # statement in the very receipt that exists to prove the overlap test fires.
    co_tenure_containers = {
        cid for cid in by_container
        if eligible_container(c_kind[cid], inv_container[cid][1])
    }
    excluded_container_ids = sorted(set(by_container) - co_tenure_containers)
    excluded_pairs_per_container = sum(
        (len(by_container[cid]) * (len(by_container[cid]) - 1)) // 2
        for cid in excluded_container_ids
    )
    excluded_people = {p for cid in excluded_container_ids for p, _, _ in by_container[cid]}
    excluded_people_with_no_other_container = len(
        excluded_people - {p for cid in co_tenure_containers for p, _, _ in by_container[cid]}
    )
    receipt["co_tenure_container_eligibility"] = {
        "ruling": "owner rulings 2026-09-07/08: admin and intern compensation payroll headers are not workplaces",
        "intern_compensation_headers_excluded": sum(
            c_kind[cid] != 'admin' for cid in excluded_container_ids),
        "excluded_container_kinds": sorted(CO_TENURE_EXCLUDED_CONTAINER_KINDS),
        "containers_with_people": len(by_container),
        "containers_eligible_for_co_tenure": len(co_tenure_containers),
        "containers_excluded": len(excluded_container_ids),
        "excluded_by_kind": dict(Counter(c_kind[cid] for cid in excluded_container_ids)),
        "same_container_pairs_removed_counted_per_container": int(excluded_pairs_per_container),
        "people_appearing_in_an_excluded_container": len(excluded_people),
        "people_whose_ONLY_container_is_excluded": int(excluded_people_with_no_other_container),
        "largest_eligible_container_person_count": max(
            (len(by_container[cid]) for cid in co_tenure_containers), default=0
        ),
        "largest_excluded_container_person_count": max(
            (len(by_container[cid]) for cid in excluded_container_ids), default=0
        ),
        "scope": (
            "co-tenure pair enumeration ONLY. Excluded containers keep their nodes, "
            "their membership-layer edges and their scores; people whose only "
            "container is excluded stay in the node universe as co-tenure isolates."
        ),
        "pair_count_note": (
            "same_container_pairs_removed_counted_per_container counts n*(n-1)/2 inside "
            "each excluded container and therefore counts a pair once per excluded "
            "container it shares; it is an upper bound on DISTINCT pairs removed, not "
            "a distinct count."
        ),
    }

    receipt["episodes"] = {
        "episodes_read": len(episodes),
        "person_container_cells": len(pc_core),
        "by_precision": dict(prec_counts),
        "by_chamber": dict(chamber_counts),
        "by_container_kind": dict(kind_counts),
        "by_source_lane": dict(lane_counts),
        "house_source_rows_matched_to_printed_service_dates": int(matched_source_rows),
        "house_source_rows_unmatched": int(unmatched_source_rows),
        "house_observation_rows_without_usable_service_dates": int(dp_undated),
        "interval_semantics": INTERVAL_SEMANTICS,
    }

    # ---- C-8c: committee side coverage, FOUR-VALUED ------------------------------
    side_ep = Counter()
    side_con = Counter()
    for ep in episodes:
        if c_kind[ep[1]] == "committee":
            side_ep[c_side[ep[1]] or "UNKNOWN"] += 1
    for cid in range(NC):
        if c_kind[cid] == "committee":
            side_con[c_side[cid] or "UNKNOWN"] += 1
    com_ep = sum(side_ep.values())
    known = side_ep["MAJ"] + side_ep["MIN"]
    receipt["C8c_committee_side_coverage"] = {
        "side_is_four_valued": list(SIDE_VALUES),
        "committee_episodes": com_ep,
        "episodes_by_side": {v: int(side_ep.get(v, 0)) for v in SIDE_VALUES},
        "committee_containers": int(sum(side_con.values())),
        "containers_by_side": {v: int(side_con.get(v, 0)) for v in SIDE_VALUES},
        "side_known_maj_or_min": int(known),
        "share_known": round(known / com_ep, 6) if com_ep else None,
        "share_unknown": round(side_ep.get("UNKNOWN", 0) / com_ep, 6) if com_ep else None,
        "bipartisan_populated": int(side_ep.get("BIPARTISAN", 0)),
        "why_bipartisan_is_zero": (
            "BIPARTISAN is a REAL value - a nonpartisan professional committee staffer "
            "has no side - but no source on disk distinguishes such a person from one "
            "whose side we merely failed to determine. Every such episode is therefore "
            "emitted as UNKNOWN (missing data), not as BIPARTISAN. The field is kept "
            "four-valued so the distinction can be filled in later without a schema "
            "change."
        ),
        "method": (
            "side is read from a whole-word MAJORITY/MINORITY/MAJ/MIN token in the "
            "committee payroll sub-unit string. No generation on disk joins an external "
            "committee-side roster."
        ),
        "consequence_for_kappa": (
            "The side-conditioned kappa rows of design 6.2 (0.75 same side, 0.40 "
            "opposite side) cannot be populated from data currently on disk for the "
            "unknown share. This is a DATA-COVERAGE limit, not a structural one: a "
            "committee employs both majority and minority staff on the same payroll, so "
            "two people in the same committee container CAN be on opposite sides and the "
            "0.40 row IS reachable in principle. It is unpopulated for want of data."
        ),
    }

    # ---- co-container pair census (the denominator for the rejection count) -------
    cocontainer_chunks = []
    for cid in sorted(co_tenure_containers):
        people = by_container[cid]
        ids = np.asarray(sorted(p for p, _, _ in people), dtype=np.int64)
        n = ids.size
        if n < 2:
            continue
        i, j = np.triu_indices(n, 1)
        cocontainer_chunks.append(ids[i] * NP + ids[j])
    cocontainer = np.concatenate(cocontainer_chunks) if cocontainer_chunks else np.zeros(0, np.int64)
    cocontainer_with_multiplicity = int(cocontainer.size)
    cocontainer.sort()
    distinct_cocontainer = int(np.count_nonzero(np.r_[True, cocontainer[1:] != cocontainer[:-1]])) if cocontainer.size else 0
    del cocontainer, cocontainer_chunks

    # ---- co-tenure sweep ---------------------------------------------------------
    seg_pair: list[np.ndarray] = []
    seg_lo: list[np.ndarray] = []
    seg_hi: list[np.ndarray] = []
    seg_con: list[np.ndarray] = []
    env_pair: list[np.ndarray] = []
    env_lo: list[np.ndarray] = []
    env_hi: list[np.ndarray] = []

    def sweep(people, which):
        """Enumerate only pairs whose calendars actually intersect."""
        segs = []
        for p, core, env in people:
            runs = core if which == "core" else env
            for s, e in runs:
                segs.append((s, e, p))
        segs.sort()
        active: list[tuple[int, int, int]] = []
        out_pair, out_lo, out_hi = [], [], []
        for s, e, p in segs:
            if active:
                active = [a for a in active if a[1] > s]
            for (as_, ae, ap) in active:
                if ap == p:
                    continue
                lo = s if s > as_ else as_
                hi = e if e < ae else ae
                if hi <= lo:
                    continue
                a, b = (p, ap) if p < ap else (ap, p)
                out_pair.append(a * NP + b)
                out_lo.append(lo)
                out_hi.append(hi)
            active.append((s, e, p))
        return out_pair, out_lo, out_hi

    for cid in sorted(co_tenure_containers):
        people = by_container[cid]
        if len(people) < 2:
            continue
        op, ol, oh = sweep(people, "core")
        if op:
            seg_pair.append(np.asarray(op, dtype=np.int64))
            seg_lo.append(np.asarray(ol, dtype=np.int32))
            seg_hi.append(np.asarray(oh, dtype=np.int32))
            seg_con.append(np.full(len(op), cid, dtype=np.int32))
        ep_, el, eh = sweep(people, "env")
        if ep_:
            a = np.asarray(ep_, dtype=np.int64)
            env_pair.append(a)
            env_lo.append(np.asarray(el, dtype=np.int32))
            env_hi.append(np.asarray(eh, dtype=np.int32))

    def cat(chunks, dtype):
        return np.concatenate(chunks) if chunks else np.zeros(0, dtype=dtype)

    P = cat(seg_pair, np.int64)
    L = cat(seg_lo, np.int32)
    H = cat(seg_hi, np.int32)
    C = cat(seg_con, np.int32)
    del seg_pair, seg_lo, seg_hi, seg_con

    order = np.lexsort((L, P))
    P, L, H, C = P[order], L[order], H[order], C[order]
    del order
    starts = np.flatnonzero(np.r_[True, P[1:] != P[:-1]]) if P.size else np.zeros(0, np.int64)
    ends = np.r_[starts[1:], P.size] if starts.size else np.zeros(0, np.int64)

    guaranteed_pairs = starts.size
    receipt["_sweep"] = {
        "core_overlap_segments": int(P.size),
        "guaranteed_pairs": int(guaranteed_pairs),
    }

    # reduce each pair: cross-container union of overlap segments + container set
    g_key = np.zeros(guaranteed_pairs, dtype=np.int64)
    g_days = np.zeros(guaranteed_pairs, dtype=np.int64)
    g_days_naive = np.zeros(guaranteed_pairs, dtype=np.int64)
    g_bucketmask = np.zeros(guaranteed_pairs, dtype=np.uint8)
    g_ncont = np.zeros(guaranteed_pairs, dtype=np.int32)
    g_containers: list[tuple[int, ...]] = [()] * guaranteed_pairs
    g_container_days: list[tuple[int, ...]] = [()] * guaranteed_pairs
    container_tuple_cache = {}
    multi_container_pairs = 0
    naive_total = 0
    unioned_total = 0

    for idx in range(guaranteed_pairs):
        s, e = int(starts[idx]), int(ends[idx])
        g_key[idx] = P[s]
        lo = L[s:e]
        hi = H[s:e]
        naive = int((hi.astype(np.int64) - lo.astype(np.int64)).sum())
        # union of already-sorted-by-lo segments
        cur_lo = int(lo[0]); cur_hi = int(hi[0]); tot = 0
        for t in range(1, e - s):
            a = int(lo[t]); b = int(hi[t])
            if a <= cur_hi:
                if b > cur_hi:
                    cur_hi = b
            else:
                tot += cur_hi - cur_lo
                cur_lo, cur_hi = a, b
        tot += cur_hi - cur_lo
        cons = tuple(sorted(set(int(x) for x in C[s:e])))
        g_days[idx] = tot
        g_days_naive[idx] = naive
        g_ncont[idx] = len(cons)
        g_containers[idx] = container_tuple_cache.setdefault(cons, cons)
        # The cross-container union above controls the edge's duration. Separate
        # within-container unions control attribution, never a second edge count.
        if len(cons) == 1:
            g_container_days[idx] = (tot,)
        else:
            by_support = defaultdict(list)
            for pos in range(s, e):
                by_support[int(C[pos])].append((int(L[pos]), int(H[pos])))
            g_container_days[idx] = tuple(
                calendar_days(union_half_open(by_support[c])) for c in cons)
        mask = 0
        for cc in cons:
            mask |= 1 << c_bucket_idx[cc]
        g_bucketmask[idx] = mask
        if len(cons) > 1:
            multi_container_pairs += 1
            naive_total += naive
            unioned_total += tot
    del P, L, H, C, starts, ends

    # CSR-style listing of the containers that actually supplied guaranteed days to each
    # pair, in pair order.  This is the exact set published on the edge as container_ids,
    # and it is what office_diversity attributes a person's tie mass across.
    g_cont_ptr = np.zeros(guaranteed_pairs + 1, dtype=np.int64)
    if guaranteed_pairs:
        np.cumsum(g_ncont, dtype=np.int64, out=g_cont_ptr[1:])
    g_cont_flat = np.fromiter(
        (c for cons in g_containers for c in cons),
        dtype=np.int64,
        count=int(g_cont_ptr[-1]),
    )
    g_cont_days = np.fromiter(
        (d for values in g_container_days for d in values), dtype=np.int64,
        count=int(g_cont_ptr[-1]))
    g_cont_shared = np.fromiter(
        (((int(g_key[i] // NP), c) in pc_shared or (int(g_key[i] % NP), c) in pc_shared)
         for i, cons in enumerate(g_containers) for c in cons),
        dtype=bool, count=int(g_cont_ptr[-1]))
    g_attenuation, g_cont_shares = attributed_support(g_cont_ptr, g_cont_days, g_cont_shared)

    # possible-only
    EP = cat(env_pair, np.int64)
    EL = cat(env_lo, np.int32)
    EH = cat(env_hi, np.int32)
    del env_pair, env_lo, env_hi
    po_key, po_days = union_pair_days(EP, EL, EH, excluded_keys=g_key)
    del EP, EL, EH
    receipt["possible_overlap_semantics"] = (
        "possible_days is the union of half-open envelope overlap intervals across all "
        "shared containers, for pairs with no guaranteed overlap; operator weight remains zero."
    )

    possible_pairs = int(po_key.size)
    zero_overlap_pairs = distinct_cocontainer - guaranteed_pairs - possible_pairs
    if zero_overlap_pairs < 0:
        raise BuildError(
            f"rejection accounting broke: {distinct_cocontainer} co-container pairs but "
            f"{guaranteed_pairs} guaranteed + {possible_pairs} possible"
        )

    receipt["co_tenure_status_counts"] = {
        "GUARANTEED": int(guaranteed_pairs),
        "POSSIBLE_ONLY": int(possible_pairs),
        "ZERO_OVERLAP": int(zero_overlap_pairs),
    }
    receipt["overlap_rule_check"] = {
        "rule": "no person-person edge without actual temporal overlap (owner ruling 2026-09-03)",
        "candidate_universe": (
            "containers ELIGIBLE for co-tenure only. Kinds in "
            + ", ".join(sorted(CO_TENURE_EXCLUDED_CONTAINER_KINDS))
            + " are excluded before this census (owner ruling 2026-09-07), so no "
            "excluded pair appears in any number below - it is neither a candidate "
            "nor a rejection. See co_tenure_container_eligibility."
        ),
        "candidate_same_container_pairs_distinct": int(distinct_cocontainer),
        "candidate_same_container_pairs_with_multiplicity": int(cocontainer_with_multiplicity),
        "pairs_REJECTED_for_no_overlap": int(zero_overlap_pairs),
        "rejection_share_of_candidates": round(zero_overlap_pairs / distinct_cocontainer, 6) if distinct_cocontainer else None,
        "edges_admitted_guaranteed": int(guaranteed_pairs),
        "edges_admitted_possible_only_zero_weight": int(possible_pairs),
        "control": "a build that admitted every same-container pair would emit "
                   f"{distinct_cocontainer} co_tenure edges; this build emits "
                   f"{guaranteed_pairs + possible_pairs}. The overlap test fires.",
    }
    receipt["cross_container_union_correction"] = {
        "pairs_sharing_2plus_containers": int(multi_container_pairs),
        "naive_summed_days_on_those_pairs": int(naive_total),
        "cross_container_unioned_days_on_those_pairs": int(unioned_total),
        "days_removed_by_the_union_rule": int(naive_total - unioned_total),
        "inflation_factor_if_not_unioned": round(naive_total / unioned_total, 6) if unioned_total else None,
    }

    # ---- container-key fragmentation correction ----------------------------------
    frag = Counter({key: len(values) for key, values in normalized_container_sources.items()})
    receipt["container_key_fragmentation_diagnostic"] = {
        "containers_as_published_by_the_spine": len(source_container_keys),
        "containers_after_stripping_a_leading_fiscal_year_or_year_token": NC,
        "containers_collapsed": len(source_container_keys) - NC,
        "largest_fragmentation_groups": [
            {"container": f"{k[0]}:{k[1]}", "fragments": v}
            for k, v in frag.most_common(10) if v > 1
        ],
        "note": "APPLIED AT GRAPH CONTAINER GRAIN. A leading FISCAL YEAR YYYY or YYYY "
                "token is stripped and no other office-key transformation is allowed. "
                "This reconnects year-prefixed administrative office fragments while "
                "leaving member, committee, leadership and other office identities intact.",
    }

    # ---- Politico bridge: which spine id namespace do its ids live in? -----------
    # The bridge receipt records the spine files it read, by absolute path and sha256.
    # Those files ARE the id namespace of every spine_person_id it emitted. If the spine
    # this build reads is a different generation, the bridge's ids are stale and must be
    # remapped through the re-key map the new spine published; a silent join would drop
    # every re-keyed person without saying so.
    politico_link_receipt = json.loads(
        paths["politico_direct_link_receipt"].read_text(encoding="utf-8")
    )
    declared_politico_files = politico_link_receipt.get("files") or {}
    policy_metadata = declared_politico_files.get(
        paths["politico_direct_policy_memberships"].name
    )
    if (
        not policy_metadata
        or policy_metadata.get("sha256")
        != sha256_file(paths["politico_direct_policy_memberships"])
    ):
        raise BuildError("Politico policy input is not bound by the direct-link receipt")

    bound_spine = politico_bound_spine_files(politico_link_receipt)
    if not bound_spine:
        raise BuildError(
            "the Politico direct-link receipt binds no Hill spine file, so the id "
            "namespace of its spine_person_id values cannot be established"
        )
    spine_roles = {
        "hill_person_spine.ndjson.gz": "hill_person_spine",
        "hill_person_office_spans.ndjson.gz": "hill_person_office_spans",
    }
    spine_binding_rows = []
    binding_matches = True
    for name, entry in sorted(bound_spine.items()):
        role = spine_roles[name]
        current_sha = sha256_file(paths[role])
        same = entry.get("sha256") == current_sha
        binding_matches = binding_matches and same
        spine_binding_rows.append({
            "file": name,
            "links_bound_generation": entry["generation"],
            "links_bound_sha256": entry.get("sha256"),
            "build_spine_generation": paths[role].parent.name,
            "build_spine_sha256": current_sha,
            "same_generation": bool(same),
        })

    spine_id_map: dict[str, str] = {}
    spine_id_map_stats: dict[str, Any] = {}
    remap_supplied = bool(getattr(args, "spine_id_map", None))
    if remap_supplied:
        spine_id_map, spine_id_map_stats = load_spine_id_map(paths["spine_id_map"])
        unknown_targets = sorted(
            {new for new in spine_id_map.values() if new not in person_tier}
        )
        if unknown_targets:
            raise BuildError(
                f"spine id map targets {len(unknown_targets)} person ids that are absent "
                f"from the spine being built against; examples {unknown_targets[:5]}"
            )
    if not binding_matches and not remap_supplied:
        raise BuildError(
            "the Politico direct-link receipt binds a different Hill spine generation "
            "than --hill-spine-root and no --spine-id-map was supplied, so its "
            "spine_person_id values cannot be resolved: " + json.dumps(spine_binding_rows)
        )
    remap_active = bool(spine_id_map) and not binding_matches

    def remap_spine_id(value: Any) -> Any:
        """Map first, then fall through. A re-key only changes the ids it lists."""
        if remap_active and isinstance(value, str) and value in spine_id_map:
            return spine_id_map[value]
        return value

    politico_spine_ids_seen: set[str] = set()
    politico_spine_ids_unmapped: set[str] = set()

    def note_politico_spine_id(original: Any) -> None:
        if not isinstance(original, str) or not original:
            return
        politico_spine_ids_seen.add(original)
        if remap_active and original not in spine_id_map and original not in person_tier:
            politico_spine_ids_unmapped.add(original)

    # ---- policy-area memberships (separate, undated grouping layer) -------------
    policy_memberships: dict[tuple[int, str], dict[str, Any]] = {}
    policy_rows_read = 0
    policy_rows_without_spine = 0
    policy_rows_invalid = 0
    policy_people_joined: set[int] = set()
    for row in read_rows(paths["politico_direct_policy_memberships"]):
        policy_rows_read += 1
        note_politico_spine_id(row.get("spine_person_id"))
        spine_id = remap_spine_id(row.get("spine_person_id"))
        label = row.get("issue_area")
        if not isinstance(spine_id, str) or not isinstance(label, str) or not label.strip():
            policy_rows_invalid += 1
            continue
        p = person_ids.get(spine_id)
        if p is None:
            policy_rows_without_spine += 1
            continue
        issue_key = " ".join(label.casefold().split())
        policy_people_joined.add(p)
        record = policy_memberships.setdefault(
            (p, issue_key),
            {
                "person": p,
                "issue_key": issue_key,
                "issue_area": label.strip(),
                "source_profile_uuid": row.get("source_profile_uuid"),
                "source_profile_uuids": set(),
                "observed_at": row.get("observed_at"),
                "observed_at_values": set(),
            },
        )
        if row.get("source_profile_uuid"):
            record["source_profile_uuids"].add(str(row["source_profile_uuid"]))
        if row.get("observed_at"):
            record["observed_at_values"].add(str(row["observed_at"]))

    receipt["spine_id_binding"] = {
        "rule": (
            "the Politico direct-link receipt's bound Hill spine sha256 defines the id "
            "namespace of its spine_person_id values; a build against a different spine "
            "generation must remap them through that spine's published re-key map "
            "(--spine-id-map, rows {legacy_person_id, person_id, reason}). Remap order "
            "is MAP FIRST, then fall through: an id the map does not list is assumed "
            "unchanged, and an id that is neither mapped nor present in the current "
            "spine is UNMAPPED and fails the build."
        ),
        "bindings": spine_binding_rows,
        "links_bind_the_spine_being_built_against": bool(binding_matches),
        "spine_id_map_supplied": remap_supplied,
        "spine_id_map_path": str(paths["spine_id_map"]) if remap_supplied else None,
        "spine_id_map_stats": spine_id_map_stats or None,
        "remap_applied": bool(remap_active),
        "remap_not_applied_reason": (
            None
            if remap_active
            else (
                "the link receipt binds the same spine generation, so the ids are "
                "already current; a supplied map is validated but deliberately NOT "
                "applied, because remapping current ids would corrupt them"
                if remap_supplied
                else "no remap needed"
            )
        ),
    }

    review_input_roles = (
        "politico_current_committee_assertions",
        "politico_profile_employment_assertions",
        "politico_profile_education_assertions",
        "politico_profile_policy_deltas",
        "politico_explicit_committee_side_assertions",
    )
    review_layers_enabled = all(role in paths for role in review_input_roles)
    if args.require_complete_politico_profile_crawl and not review_layers_enabled:
        raise BuildError(
            "--require-complete-politico-profile-crawl requires all Politico review inputs"
        )
    if review_layers_enabled:
        for role in review_input_roles:
            path = paths[role]
            metadata = declared_politico_files.get(path.name)
            if not metadata or metadata.get("sha256") != sha256_file(path):
                raise BuildError(f"Politico review input is not bound by bridge receipt: {path}")
        gate = politico_link_receipt.get("profile_crawl_gate") or {}
        if args.require_complete_politico_profile_crawl and not (
            gate.get("status") == "PASS"
            and int(gate.get("verification_failure_count") or 0) == 0
            and int(gate.get("completed_profiles") or 0)
            == int(gate.get("expected_profiles") or -1)
            and int(gate.get("unresolved_profiles") or 0) == 0
            and bool(gate.get("terminal_completion_required"))
        ):
            raise BuildError("Politico bridge receipt does not prove terminal full-profile coverage")

    def review_subject(row: Mapping[str, Any]) -> tuple[str, str]:
        note_politico_spine_id(row.get("spine_person_id"))
        spine_id = remap_spine_id(row.get("spine_person_id"))
        if isinstance(spine_id, str) and spine_id in person_ids:
            return f"person:{spine_id}", "person"
        return f"politico-profile:{row.get('source_profile_uuid')}", "source_profile"

    def review_base(layer: str, row: Mapping[str, Any], *identity: str) -> dict[str, Any]:
        subject_id, subject_kind = review_subject(row)
        return {
            "schema_id": "staffer-network-politico-review-assertion-v1",
            "rule_version": RULE_VERSION,
            "assertion_id": review_assertion_id(
                layer, str(row.get("source_profile_uuid") or ""), *identity
            ),
            "layer": layer,
            "subject_id": subject_id,
            "subject_kind": subject_kind,
            "source_profile_uuid": row.get("source_profile_uuid"),
            "spine_person_id": remap_spine_id(row.get("spine_person_id")),
            "link_status": row.get("link_status"),
            "source_url": row.get("source_url"),
            "observed_at": row.get("observed_at"),
            "operator_included": False,
            "operator_weight": 0.0,
            "duration_weight": 0.0,
            "w_tiered_lower": 0.0,
            "exploratory": True,
            "primary": False,
            "canonical_eligible": False,
            "canonical_identity_promoted": False,
            "canonical_employment_promoted": False,
            "review_status": REVIEW_STATUS,
        }

    politico_review_rows: list[dict[str, Any]] = []
    if review_layers_enabled:
        for row in read_rows(paths["politico_profile_employment_assertions"]):
            ordinal = str(row.get("history_ordinal") or "")
            employer = str(row.get("employer") or "")
            body = review_base("politico_employment_history", row, ordinal)
            body.update(
                {
                    "object_id": "politico-employer:"
                    + hashlib.sha256(employer.casefold().encode("utf-8")).hexdigest()[:24],
                    "object_kind": "source_employer",
                    "history_ordinal": row.get("history_ordinal"),
                    "employer": employer,
                    "title": row.get("title"),
                    "date_text": row.get("date_text"),
                    "temporal_scope": "SOURCE_TEXT_ONLY_NO_INTERVAL_PROMOTION",
                }
            )
            politico_review_rows.append(body)
        for row in read_rows(paths["politico_profile_education_assertions"]):
            ordinal = str(row.get("history_ordinal") or "")
            institution = str(row.get("institution") or "")
            body = review_base("politico_education_history", row, ordinal)
            body.update(
                {
                    "object_id": "politico-institution:"
                    + hashlib.sha256(institution.casefold().encode("utf-8")).hexdigest()[:24],
                    "object_kind": "source_institution",
                    "history_ordinal": row.get("history_ordinal"),
                    "institution": institution,
                    "degree": row.get("degree"),
                    "date_text": row.get("date_text"),
                    "temporal_scope": "SOURCE_TEXT_ONLY_NO_INTERVAL_PROMOTION",
                }
            )
            politico_review_rows.append(body)
        for row in read_rows(paths["politico_profile_policy_deltas"]):
            issue = str(row.get("issue_area") or "")
            normalized_issue = " ".join(issue.casefold().split())
            delta = str(row.get("delta") or "")
            body = review_base("politico_policy_delta", row, normalized_issue, delta)
            body.update(
                {
                    "object_id": "policy:politico:"
                    + hashlib.sha256(normalized_issue.encode("utf-8")).hexdigest()[:24],
                    "object_kind": "policy_area",
                    "issue_area": issue,
                    "delta": delta,
                    "source_card_present": row.get("source_card_present"),
                    "live_profile_present": row.get("live_profile_present"),
                    "temporal_scope": "CURRENT_SNAPSHOT_COMPARISON_ONLY",
                }
            )
            politico_review_rows.append(body)

        def add_committee_review(row: Mapping[str, Any], layer: str) -> None:
            chamber = str(row.get("chamber") or "")
            office_keys = [str(value) for value in row.get("payroll_office_keys") or []]
            targets = office_keys or [""]
            for office_key in targets:
                normalized = normalized_container(office_key) if office_key else ""
                c = container_ids.get((chamber, normalized)) if chamber and normalized else None
                object_id = (
                    f"container:office:{chamber}:{normalized}"
                    if c is not None
                    else "politico-committee:"
                    + hashlib.sha256(
                        f"{chamber}\x00{row.get('committee_signature')}".encode("utf-8")
                    ).hexdigest()[:24]
                )
                identity = (
                    str(row.get("committee_signature") or ""),
                    str(row.get("role") or ""),
                    office_key,
                )
                body = review_base(layer, row, *identity)
                body.update(
                    {
                        "object_id": object_id,
                        "object_kind": "container" if c is not None else "source_committee",
                        "chamber": row.get("chamber"),
                        "committee_signature": row.get("committee_signature"),
                        "payroll_office_key": office_key or None,
                        "role": row.get("role"),
                        "party_partition": row.get("party_partition"),
                        "party_derived_side": row.get("party_derived_side")
                        or row.get("side_at_observation"),
                        "explicit_side": row.get("explicit_side"),
                        "explicit_side_labels": row.get("explicit_side_labels") or [],
                        "agrees_with_party_derived_side": row.get(
                            "agrees_with_party_derived_side"
                        ),
                        "mapping_status": row.get("mapping_status")
                        or ("EXACT_PAYROLL_CONTAINER" if c is not None else "UNRESOLVED_CONTAINER"),
                        "temporal_scope": "POINT_OBSERVATION_ONLY",
                    }
                )
                politico_review_rows.append(body)

        for row in read_rows(paths["politico_current_committee_assertions"]):
            add_committee_review(row, "politico_current_committee")
        for row in read_rows(paths["politico_explicit_committee_side_assertions"]):
            add_committee_review(row, "politico_committee_side_explicit")

    politico_review_rows.sort(key=lambda row: row["assertion_id"])
    review_ids = [row["assertion_id"] for row in politico_review_rows]
    if len(review_ids) != len(set(review_ids)):
        raise BuildError("duplicate Politico review assertion id")

    if politico_spine_ids_unmapped:
        examples = sorted(politico_spine_ids_unmapped)[:5]
        raise BuildError(
            f"{len(politico_spine_ids_unmapped)} Politico spine_person_id values are "
            "neither listed in --spine-id-map nor present in the spine being built "
            f"against; examples {examples}"
        )
    remapped_ids = (
        {value for value in politico_spine_ids_seen if value in spine_id_map}
        if remap_active
        else set()
    )
    receipt["spine_id_binding"].update({
        "politico_spine_ids_seen": len(politico_spine_ids_seen),
        "politico_spine_ids_remapped": len(remapped_ids),
        "politico_spine_ids_unchanged": len(politico_spine_ids_seen) - len(remapped_ids),
        "politico_spine_ids_unmapped": 0,
        "politico_spine_ids_present_in_current_spine_after_remap": sum(
            1
            for value in politico_spine_ids_seen
            if remap_spine_id(value) in person_tier
        ),
    })

    policy_keys = sorted({key for _person, key in policy_memberships})
    policy_node_id = {
        key: "policy:politico:" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        for key in policy_keys
    }
    receipt["policy_area_resolution"] = {
        "direct_membership_rows_read": policy_rows_read,
        "direct_membership_rows_invalid": policy_rows_invalid,
        "direct_membership_rows_without_current_spine_id": policy_rows_without_spine,
        "strict_people_joined_to_spine": len(policy_people_joined),
        "policy_areas": len(policy_keys),
        "person_policy_memberships": len(policy_memberships),
        "source_profile_membership_assertions_joined": sum(
            len(row["source_profile_uuids"]) for row in policy_memberships.values()
        ),
        "identity_scope": politico_link_receipt["identity_rule"],
        "source_link_status_counts": politico_link_receipt["counts"]["status"],
        "source_unique_linked_spine_people": politico_link_receipt["counts"]["unique_linked_spine_people"],
        "negative_control": politico_link_receipt["negative_control"],
        "temporal_scope": (
            "current directory snapshot only; duration_weight=0; categorical membership "
            "weight=1 only inside the separate policy_area analysis layer"
        ),
    }
    review_layer_counts = Counter(row["layer"] for row in politico_review_rows)
    receipt["politico_review_layer_resolution"] = {
        "enabled": review_layers_enabled,
        "rows": len(politico_review_rows),
        "rows_by_layer": dict(sorted(review_layer_counts.items())),
        "linked_person_subjects": sum(
            row["subject_kind"] == "person" for row in politico_review_rows
        ),
        "unlinked_source_profile_subjects": sum(
            row["subject_kind"] == "source_profile" for row in politico_review_rows
        ),
        "committee_rows_resolved_to_payroll_container": sum(
            row["layer"] in {"politico_current_committee", "politico_committee_side_explicit"}
            and row["object_kind"] == "container"
            for row in politico_review_rows
        ),
        "operator_rows": sum(bool(row["operator_included"]) for row in politico_review_rows),
        "profile_crawl_gate": politico_link_receipt.get("profile_crawl_gate"),
        "rule": (
            "Employment, education, current-committee, explicit-side and policy-delta "
            "assertions are source-attributed review overlays. They are emitted in a "
            "separate artifact with zero operator weight and do not change the four "
            "modeled analysis layers or any canonical record."
        ),
    }

    # ---- verified revolving-door overlay (kept separate from work weights) -------
    containers_by_bioguide: dict[str, list[int]] = defaultdict(list)
    for c in range(NC):
        if c_bio[c] and c_kind[c] == "member_office":
            containers_by_bioguide[str(c_bio[c])].append(c)
    for bio, cids in list(containers_by_bioguide.items()):
        non_intern = [
            c for c in cids if "INTERN COMPENSATION" not in inv_container[c][1].upper()
        ]
        containers_by_bioguide[bio] = sorted(non_intern or cids)
    containers_by_office = {key: [cid] for key, cid in container_ids.items()}

    revolving_source_rows = 0
    revolving_source_status = Counter()
    revolving_orphan_bioguides = Counter()
    revolving_resolution_method = Counter()
    revolving_records: dict[tuple[int, str, str], dict[str, Any]] = {}
    for source in read_rows(paths["exploratory_revolving_edges"]):
        if source.get("layer") != "revolving":
            continue
        revolving_source_rows += 1
        status = str(source.get("status") or "UNKNOWN")
        revolving_source_status[status] += 1
        subject = str(source.get("subject_id") or "")
        if subject.startswith("container:bioguide:"):
            bioguide = subject[len("container:bioguide:"):]
            cids = containers_by_bioguide.get(bioguide, [])
            resolution_method = "EXACT_BIOGUIDE"
        elif subject.startswith("container:office:"):
            bioguide = None
            rest = subject[len("container:office:"):]
            if ":" not in rest:
                revolving_orphan_bioguides["MALFORMED_SUBJECT"] += 1
                continue
            chamber, office_key = rest.split(":", 1)
            cids = containers_by_office.get((chamber, office_key), [])
            resolution_method = "EXACT_CHAMBER_OFFICE_KEY"
        else:
            revolving_orphan_bioguides["MALFORMED_SUBJECT"] += 1
            continue
        if not cids:
            revolving_orphan_bioguides[subject] += 1
            continue
        revolving_resolution_method[resolution_method] += 1
        organization = source.get("object_id")
        if not isinstance(organization, str) or not organization.startswith("organization:"):
            revolving_orphan_bioguides["MALFORMED_ORGANIZATION"] += 1
            continue
        source_weight = float(source.get("w_tiered_lower") or 0.0)
        split_weight = source_weight / len(cids) if source_weight > 0 else 0.0
        for c in cids:
            key = (c, organization, status)
            record = revolving_records.setdefault(
                key,
                {
                    "container": c,
                    "organization_id": organization,
                    "status": status,
                    "bioguide": c_bio[c],
                    "operator_weight": 0.0,
                    "source_edge_ids": [],
                    "contributing_lda_people": set(),
                    "source_match_count": len(cids),
                    "source_resolution_methods": set(),
                },
            )
            record["operator_weight"] += split_weight
            record["source_resolution_methods"].add(resolution_method)
            if source.get("edge_id"):
                record["source_edge_ids"].append(str(source["edge_id"]))
            for contribution in source.get("contributions") or []:
                person = contribution.get("lda_source_person_id")
                if isinstance(person, str):
                    record["contributing_lda_people"].add(person)

    organization_ids = sorted(
        {record["organization_id"] for record in revolving_records.values()}
    )
    receipt["revolving_resolution"] = {
        "source_rows": revolving_source_rows,
        "source_status_counts": dict(sorted(revolving_source_status.items())),
        "mapped_edge_rows": len(revolving_records),
        "mapped_organizations": len(organization_ids),
        "mapped_source_rows_by_resolution_method": dict(sorted(revolving_resolution_method.items())),
        "orphan_source_rows": int(sum(revolving_orphan_bioguides.values())),
        "orphan_bioguides_top20": revolving_orphan_bioguides.most_common(20),
        "multi_container_rule": (
            "resolve an exact bioguide first, or an exact chamber plus office key for "
            "legacy office-subject rows; drop INTERN COMPENSATION when a main personal-"
            "office container exists; otherwise divide source weight equally across every "
            "exact-bioguide personal office so an ambiguous chamber history never "
            "duplicates walk mass. No surname or truncated-key inference is allowed."
        ),
    }

    # ---- node universe: PERSONS ONLY (D-022) -------------------------------------
    # Containers, organisations and policy areas are NOT nodes.  They are emitted as
    # grouping layers and as a groups roster; nothing about them enters the matrix.
    node_ids: list[str] = [f"person:{inv_person[p]}" for p in range(NP)]
    node_index = {nid: i for i, nid in enumerate(node_ids)}
    NN = NP

    p_tier = validated_person_tiers([inv_person[p] for p in range(NP)], person_tier)
    p_str = np.asarray([S_STRENGTH[t] for t in p_tier], dtype=np.float64)

    # ---- operator edge arrays: co_tenure only ------------------------------------
    hi_tbl, lo_tbl = mask_table(KAPPA)
    g_kappa_max = hi_tbl[g_bucketmask]
    g_kappa_min = lo_tbl[g_bucketmask]

    ga = (g_key // NP).astype(np.int64)
    gb = (g_key % NP).astype(np.int64)
    w_lower = 1.0 - np.exp(-g_days.astype(np.float64) / TAU_DAYS)
    tier_pair = np.minimum(p_str[ga], p_str[gb])
    w_kappa = g_kappa_max * w_lower
    w_tiered = co_tenure_weight(g_days, g_kappa_max, tier_pair, g_attenuation, TAU_DAYS)
    receipt['ranking_math'] = {
        'version': RANKING_VERSION, 'shared_role_factor': SHARED_ROLE_FACTOR,
        'attenuated_edges': int(np.count_nonzero(g_attenuation < 1)),
        'shared_person_container_cells': len(pc_shared),
        'minimum_attenuation': float(g_attenuation.min()) if g_attenuation.size else None,
        'maximum_attenuation': float(g_attenuation.max()) if g_attenuation.size else None,
        'title_basis': 'Exact normalized title_last in person/container span; no person-wide title blacklist',
        'attribution': 'within-container union days times shared-role factor, divided by sum over supplying containers',
        'interpretation': 'exploratory damping; not a calibrated probability or a cap on total person strength',
    }

    # ---- grouping-layer records (NOT operator edges) -----------------------------
    membership_cells = sorted(pc_core)
    mem_group_w = np.asarray(
        [c_kappa[c] * p_str[p] for (p, c) in membership_cells], dtype=np.float64
    )

    rev_positive = [
        record
        for record in revolving_records.values()
        if record["status"] == "GUARANTEED" and record["operator_weight"] > 0.0
    ]
    rev_positive.sort(key=lambda row: (row["container"], row["organization_id"]))

    policy_records = [policy_memberships[key] for key in sorted(policy_memberships)]

    # per-person registrant records: the source revolving rows name the LDA people whose
    # filings produced the container -> organization path, so where a spine person
    # carries that same lda_source_person_id the pairing is recorded person-side too.
    lda_to_spine: dict[str, list[int]] = defaultdict(list)
    for p in range(NP):
        lda_id = person_lda.get(inv_person[p])
        if isinstance(lda_id, str) and lda_id:
            lda_to_spine[lda_id].append(p)
    person_registrant: dict[tuple[int, str, str], dict[str, Any]] = {}
    registrant_lda_ids_unjoined = set()
    for key in sorted(revolving_records):
        record = revolving_records[key]
        for lda_id in sorted(record["contributing_lda_people"]):
            people = lda_to_spine.get(lda_id)
            if not people:
                registrant_lda_ids_unjoined.add(lda_id)
                continue
            for p in people:
                cell = person_registrant.setdefault(
                    (p, record["organization_id"], record["status"]),
                    {
                        "person": p,
                        "organization_id": record["organization_id"],
                        "status": record["status"],
                        "lda_source_person_ids": set(),
                        "container_ids": set(),
                    },
                )
                cell["lda_source_person_ids"].add(lda_id)
                ch_, ok_ = inv_container[record["container"]]
                cell["container_ids"].add(f"container:office:{ch_}:{ok_}")

    # ---- THE OPERATOR ------------------------------------------------------------
    keep = w_tiered > 0.0
    subjects = ga[keep]
    objects = gb[keep]
    weights = w_tiered[keep]
    layers = np.full(int(keep.sum()), CO_TENURE_LAYER, dtype=np.int32)

    emit_glassbox(enabled=args.glassbox, event="operator_start",
                  payload={"nodes": NN, "edges": int(subjects.size),
                           "node_kinds": "person_only", "layers": "co_tenure_only"})

    eu, ev, ew, el = deduplicate_undirected_layer_edges(subjects, objects, weights, layers)
    if not np.all(keep) or eu.size != ga.size or not np.allclose(ew, weights, rtol=0, atol=0):
        raise BuildError('office attribution and operator edge sets diverged')
    transition = layer_balanced_transition(NN, eu, ev, ew, el)
    # Uniform restart over PERSONS.  group_balanced_teleport is deliberately not used:
    # equal mass per node KIND is what gave 36 policy nodes the restart mass of 144,693
    # people.  With one kind the two coincide, but passing the vector explicitly makes
    # the restart auditable from the receipt instead of implied by a default.
    teleport = np.full(NN, 1.0 / float(NN), dtype=np.float64)

    pageranks = {}
    pr_convergence = []
    for alpha in ALPHAS:
        score, detail = connectedness_pagerank(
            transition, damping=alpha, teleport=teleport, tolerance=1e-11, max_iterations=750
        )
        pageranks[alpha] = score
        pr_convergence.append({"alpha": float(alpha), "iterations": int(detail["iterations"]),
                               "residual_l1": float(detail["residual_l1"])})

    symmetric = balanced_symmetric_adjacency(transition)
    eigenvector, comp_labels, eigen_receipt = componentwise_eigenvector_centrality(
        symmetric, tolerance=1e-12, max_iterations=750, allow_partial=True
    )

    # ---- CENTRALITY FIX: resolve any non-converged component with a direct solve --
    comp_count = int(eigen_receipt["components"])
    comp_sizes = np.bincount(comp_labels, minlength=comp_count)
    repaired = []
    nonconv = np.isnan(eigenvector)
    if nonconv.any():
        bad_components = sorted(set(int(x) for x in comp_labels[nonconv]))
        for comp in bad_components:
            idx = np.flatnonzero(comp_labels == comp)
            sub = symmetric[idx][:, idx].tocsr()
            k = 1
            try:
                leading_value, vec = deterministic_leading_eigenpair(sub)
                eigenvector[idx] = vec
                repaired.append({
                    "component_id": int(comp), "component_size": int(idx.size),
                    "method": "scipy.sparse.linalg.eigsh(which=LA, k=1)",
                    "leading_eigenvalue": leading_value,
                    "initial_vector": "all ones, deterministic",
                    "l1_normalized": True, "status": "REPAIRED",
                })
            except Exception as exc:                                  # noqa: BLE001
                repaired.append({
                    "component_id": int(comp), "component_size": int(idx.size),
                    "method": "scipy.sparse.linalg.eigsh(which=LA, k=1)",
                    "status": "FAILED", "error": str(exc)[:300],
                })
    eigen_receipt = dict(eigen_receipt)
    eigen_receipt["direct_solve_repair"] = repaired
    eigen_receipt["status_after_repair"] = (
        "PASS" if not np.isnan(eigenvector).any() else "PARTIAL_NULL"
    )
    eigen_receipt["nodes_null_after_repair"] = int(np.isnan(eigenvector).sum())

    office_div, office_distinct, _office_mass = office_diversity_simpson(
        ga, gb, w_tiered, g_cont_ptr, g_cont_flat, NP, NC,
        container_shares=g_cont_shares,
    )
    raw_strength = np.bincount(np.concatenate((eu, ev)),
                               weights=np.concatenate((ew, ew)), minlength=NN)
    co_tenure_degree = np.bincount(np.concatenate((eu, ev)), minlength=NN)

    # grouping-layer counts, per person, for the node payload.  These are counts of
    # GROUP attachments, not operator degree - the groups are not in the matrix.
    attached_container_count = np.zeros(NP, dtype=np.int64)
    for (p, _c) in membership_cells:
        attached_container_count[p] += 1
    policy_group_count = np.zeros(NP, dtype=np.int64)
    for record in policy_records:
        policy_group_count[record["person"]] += 1
    registrant_org_count = np.zeros(NP, dtype=np.int64)
    for (p, _org, _status) in person_registrant:
        registrant_org_count[p] += 1

    order_sizes = np.sort(comp_sizes)[::-1]
    hist_sizes, hist_counts = (
        np.unique(comp_sizes, return_counts=True) if comp_sizes.size else (np.zeros(0), np.zeros(0))
    )
    receipt["operator"] = {
        "definition": OPERATOR_DEFINITION,
        "node_kinds": list(NODE_KINDS),
        "nodes": NN,
        "person_nodes": NP,
        "non_person_nodes": 0,
        "operator_layers": ["co_tenure"],
        "operator_edges": int(eu.size),
        "teleport": {
            "kind": "uniform_over_persons",
            "mass_per_person": float(1.0 / float(NN)),
            "sums_to_one": bool(abs(float(teleport.sum()) - 1.0) <= 1e-12),
            "note": (
                "group_balanced_teleport (equal restart mass per node KIND) is NOT used "
                "by this builder; it remains in fec/staffer_network/network_math.py for "
                "other callers"
            ),
        },
        # "how many separate colonies" - the whole point of the persons-only operator.
        "components": comp_count,
        "isolates": int(eigen_receipt["isolates"]),
        "isolated_persons": int((co_tenure_degree == 0).sum()),
        "persons_in_a_component_of_size_2_or_more": int(
            NP - int((comp_sizes[comp_labels] == 1).sum())
        ),
        "largest_component": int(order_sizes[0]) if order_sizes.size else 0,
        "largest_component_share_of_nodes": round(float(order_sizes[0]) / NN, 6) if order_sizes.size else None,
        "component_sizes_top20": [int(x) for x in order_sizes[:20]],
        "distinct_component_sizes": int(hist_sizes.size),
        "component_size_histogram": {
            str(int(k)): int(v) for k, v in zip(hist_sizes, hist_counts)
        },
        "component_size_histogram_semantics": (
            "keys are COMPONENT SIZES in persons, values are how many components have "
            "that size; every person is in exactly one component, so "
            "sum(size * count) == person node count"
        ),
        "pagerank": pr_convergence,
        "eigenvector": eigen_receipt,
    }
    hist_total = int(sum(int(k) * int(v) for k, v in zip(hist_sizes, hist_counts)))
    if hist_total != NP:
        raise BuildError(
            f"component size histogram covers {hist_total} persons, not {NP}"
        )
    receipt["office_diversity"] = {
        "definition": OFFICE_DIVERSITY_DEFINITION,
        "replaces": "bridging_diversity (Simpson over node KINDS)",
        "old_field_name_present_in_payload": False,
        "group_count_K_distinct_containers": NC,
        "persons_scored": int((co_tenure_degree > 0).sum()),
        "persons_zero_because_isolated": int((co_tenure_degree == 0).sum()),
        "mean_over_scored_persons": (
            round(float(office_div[co_tenure_degree > 0].mean()), 8)
            if int((co_tenure_degree > 0).sum()) else None
        ),
        "distinct_offices_max": int(office_distinct.max()) if NP else 0,
    }

    # ---- committee bridge ablation ------------------------------------------------
    # Personal offices are partisan silos: a member's staff are all one party. Committees
    # employ BOTH sides on one payroll, so committee co-tenure is where a cross-party tie
    # can form at all. That makes the committee kappa load-bearing for CONNECTIVITY, not a
    # minor cell in the table - so measure whether committees are what holds this graph
    # together, rather than assuming it either way.
    comm_bits = 0
    for _b in COMMITTEE_BUCKETS:
        comm_bits |= 1 << bucket_pos[_b]
    member_bits = 1 << bucket_pos["member_office"]
    noncomm_bits = (~comm_bits) & 0xFF
    nonmember_bits = (~member_bits) & 0xFF
    has_comm = (g_bucketmask & np.uint8(comm_bits)) != 0
    has_noncomm = (g_bucketmask & np.uint8(noncomm_bits)) != 0
    has_member = (g_bucketmask & np.uint8(member_bits)) != 0
    has_nonmember = (g_bucketmask & np.uint8(nonmember_bits)) != 0

    def person_components(sel_mask):
        sel = keep & sel_mask
        n_sel = int(sel.sum())
        if n_sel == 0:
            return {"edges": 0, "people_touched": 0, "components_over_all_people": NP,
                    "isolated_people": NP, "largest_component": 0,
                    "largest_component_share_of_all_people": 0.0}
        u = ga[sel]
        v = gb[sel]
        gmat = sparse.coo_matrix(
            (np.ones(u.size, dtype=np.int8), (u, v)), shape=(NP, NP)
        ).tocsr()
        ncomp_, lab = csgraph.connected_components(gmat, directed=False)
        sizes = np.sort(np.bincount(lab))[::-1]
        deg = np.bincount(np.concatenate((u, v)), minlength=NP)
        touched = int((deg > 0).sum())
        return {
            "edges": n_sel,
            "people_touched": touched,
            "isolated_people": int(NP - touched),
            "components_over_all_people": int(ncomp_),
            "largest_component": int(sizes[0]),
            "largest_component_share_of_all_people": round(float(sizes[0]) / NP, 6),
            "largest_component_share_of_touched": (
                round(float(sizes[0]) / touched, 6) if touched else None
            ),
            "component_sizes_top10": [int(x) for x in sizes[:10]],
        }

    _all = np.ones(guaranteed_pairs, dtype=bool)
    receipt["committee_bridge_ablation"] = {
        "question": (
            "Personal offices are partisan silos, so committees are where cross-party "
            "ties actually form. Is the committee layer what holds this graph together?"
        ),
        "ablation_rule": (
            "an edge SURVIVES an ablation when at least one container that actually "
            "contributed guaranteed overlap days lies outside the removed class"
        ),
        "person_only_graph_all_co_tenure_edges": person_components(_all),
        "committee_derived_edges_REMOVED": person_components(has_noncomm),
        "ONLY_committee_derived_edges": person_components(has_comm),
        "member_office_derived_edges_REMOVED": person_components(has_nonmember),
        "ONLY_member_office_derived_edges": person_components(has_member),
        "edges_touching_a_committee_container": int((keep & has_comm).sum()),
        "edges_touching_a_member_office_container": int((keep & has_member).sum()),
        "edges_that_could_NOT_have_formed_inside_a_personal_office": int(
            (keep & ~has_member).sum()
        ),
        "edges_that_could_NOT_have_formed_outside_a_personal_office": int(
            (keep & ~has_noncomm & has_member).sum()
        ),
    }

    # ---- date precision mix per edge (C-9) ---------------------------------------
    ep_prec = np.zeros(NP, dtype=np.int8)      # 2 = person has any DAY episode
    person_prec: dict[int, set] = defaultdict(set)
    for ep in episodes:
        person_prec[ep[0]].add(ep[4])
    prec_code = np.zeros(NP, dtype=np.int8)
    for p, s in person_prec.items():
        prec_code[p] = 2 if s == {"DAY"} else (0 if s == {"REPORT_PERIOD"} else 1)
    # an edge's precision is the COARSEST of its endpoints
    def edge_precision(a, b):
        pa, pb = prec_code[a], prec_code[b]
        w = np.minimum(pa, pb)
        return w
    ec = edge_precision(ga, gb)
    pa_, pb_ = (po_key // NP), (po_key % NP)
    ec2 = edge_precision(pa_, pb_)
    c9 = {
        "total_person_pair_cowork_edges": int(guaranteed_pairs + possible_pairs),
        "precision_mix": {
            "DAY": int((ec == 2).sum() + (ec2 == 2).sum()),
            "MIXED_DAY_AND_REPORT_PERIOD": int((ec == 1).sum() + (ec2 == 1).sum()),
            "REPORT_PERIOD_quarter_house_or_half_year_senate": int((ec == 0).sum() + (ec2 == 0).sum()),
            "MONTH": 0,
            "YEAR": 0,
            "UNDATED": 0,
        },
        "dated_weight_bearing_edges": int(guaranteed_pairs),
        "zero_weight_edges_possible_overlap_only": int(possible_pairs),
        "undated_edges_weight_zero": 0,
        "binding_assertion": "an undated-only edge would carry weight 0 in every "
                             "duration-weighted computation; this build produced none, "
                             "because every payroll episode is bounded by a printed "
                             "service interval or a reporting period.",
    }
    receipt["C9_edge_date_precision_mix"] = c9
    receipt["C9_non_work_layers"] = {
        "policy_area_current_snapshot_undated": len(policy_records),
        "policy_area_duration_weight_sum": 0.0,
        "policy_area_operator_semantics": (
            "a GROUPING layer from v4: undated categorical membership, zero operator "
            "weight, never a node and never a duration-weighted edge"
        ),
        "revolving_rows": len(revolving_records),
        "revolving_rows_with_positive_source_strength": len(rev_positive),
        "revolving_guaranteed_rows_in_operator": 0,
        "person_registrant_rows": len(person_registrant),
        "politico_review_only_rows": len(politico_review_rows),
        "politico_review_only_operator_rows": sum(
            bool(row["operator_included"]) for row in politico_review_rows
        ),
        "binding_assertion": (
            "undated policy memberships carry duration_weight=0, do not enter w_work, "
            "and from v4 do not enter the operator at all"
        ),
    }

    # ---- trajectories + office moves (SEQUENCE, not a social edge) ---------------
    by_person: dict[int, list] = defaultdict(list)
    for ep in episodes:
        by_person[ep[0]].append(ep)
    moves_counter: Counter = Counter()
    move_gap_hist = Counter()
    total_moves = 0
    movers = 0
    traj_rows = []
    for p in range(NP):
        eps = sorted(by_person.get(p, []), key=lambda e: (min(r[0] for r in e[2]),
                                                          max(r[1] for r in e[2]),
                                                          inv_container[e[1]]))
        stints = []
        for e in eps:
            ch, ok = inv_container[e[1]]
            runs = sorted(e[2])
            # ONE STINT PER CONTIGUOUS RUN (owner ruling 2026-09-07). A stint that
            # spanned a gap in observed service asserted attendance nobody printed.
            for run_index, (s, en) in enumerate(runs):
                stints.append({
                    "container_id": f"container:office:{ch}:{ok}",
                    "chamber": ch,
                    "container_kind": e[6],
                    "member_bioguide": e[7],
                    "core_start": date.fromordinal(s).isoformat(),
                    "core_end_exclusive": date.fromordinal(en).isoformat(),
                    "date_precision": e[4],
                    "title_last": e[9],
                    # SPAN-level: the periods observed across the whole office episode,
                    # not this run alone. Unchanged from v5 so consumers keep their field.
                    "periods_observed": e[10],
                    "status": e[8],
                    "stint_run_index": run_index,
                    "run_count_for_span": len(runs),
                    "run_basis": e[11],
                })
        pmoves = []
        for a, b in zip(eps, eps[1:]):
            if a[1] == b[1]:
                continue
            ae = max(r[1] for r in a[2])
            bs = min(r[0] for r in b[2])
            gap = bs - ae
            ach, aok = inv_container[a[1]]
            bch, bok = inv_container[b[1]]
            if gap < 0:
                bucket = "OVERLAPPING"
            elif gap == 0:
                bucket = "ABUTTING"
            elif gap <= 31:
                bucket = "SHORT_1_31d"
            elif gap <= 92:
                bucket = "QUARTER_32_92d"
            elif gap <= 365:
                bucket = "YEAR_93_365d"
            else:
                bucket = "LONG_over_365d"
            move_gap_hist[bucket] += 1
            pmoves.append({
                "from_container_id": f"container:office:{ach}:{aok}",
                "to_container_id": f"container:office:{bch}:{bok}",
                "from_member_bioguide": a[7],
                "to_member_bioguide": b[7],
                "left_on": date.fromordinal(ae).isoformat(),
                "arrived_on": date.fromordinal(bs).isoformat(),
                "gap_days": int(gap),
                "gap_bucket": bucket,
                "date_precision": "DAY" if a[4] == "DAY" and b[4] == "DAY" else "REPORT_PERIOD",
            })
            moves_counter[(a[1], b[1])] += 1
            total_moves += 1
        if pmoves:
            movers += 1
        traj_rows.append({
            "schema_id": TRAJ_SCHEMA_ID,
            "rule_version": RULE_VERSION,
            "spine_person_id": inv_person[p],
            "identity_tier": p_tier[p],
            "chambers": person_chambers.get(inv_person[p], []),
            "member_bioguides": person_bios.get(inv_person[p], []),
            "span_count": len(eps),
            "stint_count": len(stints),
            "stints": stints,
            "move_count": len(pmoves),
            "moves": pmoves,
            "review_status": REVIEW_STATUS,
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
            "note": "SEQUENCE IS NOT A SOCIAL EDGE. These moves are the person's own "
                    "institutional pathway; they never create a person-person edge. "
                    "stint_count counts CONTIGUOUS RUNS (owner ruling 2026-09-07), so it "
                    "is >= span_count; moves are still office-to-office, one per "
                    "consecutive pair of SPANS.",
        })

    move_rows = []
    for (a, b), n in sorted(moves_counter.items(), key=lambda kv: (-kv[1], kv[0])):
        ach, aok = inv_container[a]
        bch, bok = inv_container[b]
        move_rows.append({
            "schema_id": MOVE_SCHEMA_ID,
            "rule_version": RULE_VERSION,
            "from_container_id": f"container:office:{ach}:{aok}",
            "to_container_id": f"container:office:{bch}:{bok}",
            "from_container_kind": c_kind[a],
            "to_container_kind": c_kind[b],
            "from_member_bioguide": c_bio[a],
            "to_member_bioguide": c_bio[b],
            "people": int(n),
            "direction": "directed",
            "review_status": REVIEW_STATUS,
            "canonical_eligible": False,
            "canonical_employment_promoted": False,
        })

    receipt["trajectories"] = {
        "person_rows": len(traj_rows),
        "people_with_at_least_one_move": movers,
        "total_directed_office_moves": total_moves,
        "distinct_directed_office_pairs": len(moves_counter),
        "gap_bucket_histogram": dict(move_gap_hist),
        "span_rows": int(sum(row["span_count"] for row in traj_rows)),
        "stint_rows": int(sum(row["stint_count"] for row in traj_rows)),
        "rule": "sequence recorded as trajectory + office-to-office structure ONLY; "
                "zero person-person sequence edges emitted",
        "stint_rule": "one stint per CONTIGUOUS RUN of the span's core calendar "
                      "(owner ruling 2026-09-07); see stint_census",
    }

    trajectory_by_person = {row["spine_person_id"]: row for row in traj_rows}

    def named_case(lda_id: str) -> tuple[list[int], list[dict[str, Any]]]:
        people = [
            p for p in range(NP) if person_lda.get(inv_person[p]) == lda_id
        ]
        trajectories = [trajectory_by_person[inv_person[p]] for p in people]
        return people, trajectories

    gordon_people, gordon_trajectories = named_case("lda:lobbyist:147664")
    gordon_stints = [
        stint for row in gordon_trajectories for stint in row.get("stints", [])
    ]
    gordon_moves = [
        move for row in gordon_trajectories for move in row.get("moves", [])
    ]
    gordon_spans = sum(row.get("span_count", 0) for row in gordon_trajectories)
    # The "two stints" clause was written when a stint WAS an office episode; under the
    # 2026-09-07 run ruling the stint array is indexed by contiguous run instead. The
    # office count is therefore ALSO asserted on span_count - but the literal stint bar
    # is KEPT, not relaxed: measured on the v6 spine, both of Gordon's House spans carry
    # unbroken printed service (2017-05-18..2023-02-10 and 2023-02-10..2024-01-03), so
    # they yield exactly one run each. If a later spine splits them, this gate fires and
    # a human adjudicates - which is what it is for.
    gordon_pass = (
        len(gordon_people) == 1
        and gordon_spans == 2
        and len(gordon_stints) == 2
        and {stint.get("member_bioguide") for stint in gordon_stints}
        == {"A000370", "S001223"}
        and len(gordon_moves) == 1
        and gordon_moves[0].get("gap_days") == 0
        and gordon_moves[0].get("gap_bucket") == "ABUTTING"
    )
    stephanie_people, stephanie_trajectories = named_case("lda:lobbyist:147663")
    stephanie_stints = [
        stint for row in stephanie_trajectories for stint in row.get("stints", [])
    ]
    stephanie_pass = (
        len(stephanie_people) == 1
        and any(stint.get("member_bioguide") == "V000127" for stint in stephanie_stints)
    )
    receipt["named_regression_checks"] = {
        "Gordon_Holzberg": {
            "status": "PASS" if gordon_pass else "FAIL",
            "lda_source_person_id": "lda:lobbyist:147664",
            "spine_person_count": len(gordon_people),
            "spine_person_ids": [inv_person[p] for p in gordon_people],
            "span_count": int(gordon_spans),
            "stint_count": len(gordon_stints),
            "member_bioguides": sorted({
                stint.get("member_bioguide") for stint in gordon_stints
                if stint.get("member_bioguide")
            }),
            "move_count": len(gordon_moves),
            "moves": gordon_moves,
            "expected": "one person, two office SPANS (Adams then Sykes), two stints "
                        "(one contiguous run each), one ABUTTING move with gap 0",
        },
        "Stephanie_Belk": {
            "status": "PASS" if stephanie_pass else "FAIL",
            "lda_source_person_id": "lda:lobbyist:147663",
            "spine_person_count": len(stephanie_people),
            "spine_person_ids": [inv_person[p] for p in stephanie_people],
            "span_count": int(sum(row.get("span_count", 0) for row in stephanie_trajectories)),
            "stint_count": len(stephanie_stints),
            "member_bioguides": sorted({
                stint.get("member_bioguide") for stint in stephanie_stints
                if stint.get("member_bioguide")
            }),
            "expected": "one payroll-spine person linked to the David Vitter office",
        },
    }

    # ---- dial sensitivity (reduced sweep, PageRank alpha=0.85) -------------------
    sweep_rows = []
    base_rank = pageranks[0.85]
    from scipy.stats import rankdata
    scenarios = []
    for dial_name, base in (("KAPPA", KAPPA), ("S_STRENGTH", S_STRENGTH)):
        for entry in base:
            for factor in SWEEP_FACTORS:
                scaled = dict(base)
                scaled[entry] = min(base[entry] * factor, SWEEP_CLAMP_MAXIMUM)
                clamped = [entry] if base[entry] * factor > SWEEP_CLAMP_MAXIMUM else []
                scenarios.append((dial_name, entry, factor, scaled, clamped))
    for dial_name, entry, factor, scaled, clamped in scenarios:
        if dial_name == "KAPPA":
            hi2, _lo2 = mask_table(scaled)
            w2 = hi2[g_bucketmask] * tier_pair * w_lower * g_attenuation
        else:
            ps2 = np.asarray([scaled[t] for t in p_tier])
            w2 = g_kappa_max * np.minimum(ps2[ga], ps2[gb]) * w_lower * g_attenuation
        k2 = w2 > 0
        l2 = np.full(int(k2.sum()), CO_TENURE_LAYER, np.int32)
        du, dv, dw, dl = deduplicate_undirected_layer_edges(ga[k2], gb[k2], w2[k2], l2)
        tr = layer_balanced_transition(NN, du, dv, dw, dl)
        r2, _ = connectedness_pagerank(tr, damping=0.85, teleport=teleport,
                                       tolerance=1e-11, max_iterations=750)
        rho = float(np.corrcoef(
            rankdata(base_rank[:NP]), rankdata(r2[:NP])
        )[0, 1])
        sweep_rows.append({
            "dial": dial_name, "entry": entry, "factor": factor, "scaled_dial": scaled,
            "clamped_dial_entries": clamped, "nodes_ranked": NP, "scope": "person nodes",
            "top100_person_overlap": len(set(np.argsort(-base_rank[:NP], kind='stable')[:100]) & set(np.argsort(-r2[:NP], kind='stable')[:100])),
            "spearman_pagerank_0_85": rho,
        })
        del tr, du, dv, dw, dl, l2
    receipt["sweep"] = sweep_rows
    receipt["sweep_semantics"] = (
        "Each scenario perturbs one named kappa or identity-strength entry while holding "
        "all others fixed and rebuilds the PERSONS-ONLY co-tenure operator. Spearman uses "
        "average ranks for ties. The top-100 overlap uses the deterministic node-order tie "
        "break. No dial is calibrated by this sensitivity check; unchanged ranks can "
        "reflect sparse source coverage, clipping or row normalization. Note that a "
        "S_STRENGTH entry can move ranks even though the operator is row-normalized, "
        "because tier_pair is a MINIMUM over the two endpoints and therefore changes "
        "relative edge weights, not just a node's scale."
    )

    # ---- did the policy-edge inflation actually go away? -------------------------
    # The 2026-09-05 audit measured people carrying a Politico policy edge at 11.6x the
    # PageRank of the rest, under a node universe where 36 policy nodes drew the same
    # restart mass as 144,693 people.  Policy memberships are now a grouping layer and
    # cannot reach the operator at all, so any ratio that remains is a statement about
    # WHO POLITICO COVERS - senior current staff - and not about the operator.
    policy_people = np.zeros(NP, dtype=bool)
    for record in policy_records:
        policy_people[record["person"]] = True
    with_policy = base_rank[:NP][policy_people]
    without_policy = base_rank[:NP][~policy_people]
    baseline_top100 = set(np.argsort(-base_rank[:NP], kind='stable')[:100])
    receipt['policy_link_pagerank_control'] = {
        'question': (
            'after removing policy areas from the operator, do people with a Politico '
            'policy link still score differently from everyone else?'
        ),
        'policy_edges_in_operator': 0,
        'people_with_policy_evidence': int(policy_people.sum()),
        'people_without_policy_evidence': int((~policy_people).sum()),
        'mean_pagerank_085_with_policy_evidence': (
            float(with_policy.mean()) if with_policy.size else None
        ),
        'mean_pagerank_085_without_policy_evidence': (
            float(without_policy.mean()) if without_policy.size else None
        ),
        'ratio_with_over_without': (
            float(with_policy.mean() / without_policy.mean())
            if with_policy.size and without_policy.size and without_policy.mean() > 0
            else None
        ),
        'published_top100_people_with_policy_evidence': int(
            policy_people[list(baseline_top100)].sum()
        ) if baseline_top100 else 0,
        'prior_measurement': (
            'the 2026-09-05 audit of the v3/v5 kind-balanced operator measured this ratio '
            'at about 11.6x; that operator gave each of 36 policy_area nodes the restart '
            'mass of 4,019 people'
        ),
        'semantics': (
            'A descriptive comparison on the PUBLISHED persons-only operator. It is NOT a '
            'counterfactual rebuild and NOT a calibration: no dial is chosen from it. A '
            'ratio above one here reflects Politico directory coverage skewing to senior '
            'current staff, who also hold longer and larger co-tenure calendars.'
        ),
    }

    # ---- emit --------------------------------------------------------------------
    def edge_rows():
        for i in range(guaranteed_pairs):
            a = int(g_key[i] // NP); b = int(g_key[i] % NP)
            cons = [f"container:office:{inv_container[c][0]}:{inv_container[c][1]}" for c in g_containers[i]]
            kinds = sorted({c_kind[c] for c in g_containers[i]})
            body = {
                "schema_id": EDGE_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "co_tenure",
                "direction": "undirected",
                "subject_id": f"person:{inv_person[a]}",
                "object_id": f"person:{inv_person[b]}",
                "subject_kind": "person",
                "object_kind": "person",
                "subject_tier": p_tier[a],
                "object_tier": p_tier[b],
                "status": "GUARANTEED",
                "guaranteed_days": int(g_days[i]),
                "guaranteed_days_before_cross_container_union": int(g_days_naive[i]),
                "container_count": int(g_ncont[i]),
                "container_ids": cons,
                "container_guaranteed_days": list(g_container_days[i]),
                "container_shared_role": g_cont_shared[g_cont_ptr[i]:g_cont_ptr[i+1]].tolist(),
                "container_mass_shares": g_cont_shares[g_cont_ptr[i]:g_cont_ptr[i+1]].tolist(),
                "shared_role_attenuation": float(g_attenuation[i]),
                "shared_role_factor": SHARED_ROLE_FACTOR,
                "container_kinds": kinds,
                "kappa": float(g_kappa_max[i]),
                "kappa_min": float(g_kappa_min[i]),
                "tier_strength": float(tier_pair[i]),
                "w_lower": float(w_lower[i]),
                "w_kappa_lower": float(w_kappa[i]),
                "w_tiered_lower": float(w_tiered[i]),
                "date_precision": ["REPORT_PERIOD", "MIXED", "DAY"][int(min(prec_code[a], prec_code[b]))],
                "exploratory": True,
                "primary": False,
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "review_status": REVIEW_STATUS,
            }
            body["edge_id"] = edge_id_of(body["layer"], body["subject_id"], body["object_id"],
                                         *body["container_ids"])
            yield body
        for i in range(possible_pairs):
            a = int(po_key[i] // NP); b = int(po_key[i] % NP)
            body = {
                "schema_id": EDGE_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "co_tenure",
                "direction": "undirected",
                "subject_id": f"person:{inv_person[a]}",
                "object_id": f"person:{inv_person[b]}",
                "subject_kind": "person",
                "object_kind": "person",
                "subject_tier": p_tier[a],
                "object_tier": p_tier[b],
                "status": "POSSIBLE_ONLY",
                "guaranteed_days": 0,
                "possible_days": int(po_days[i]),
                "kappa": None,
                "tier_strength": float(min(p_str[a], p_str[b])),
                "w_lower": 0.0,
                "w_kappa_lower": 0.0,
                "w_tiered_lower": 0.0,
                "date_precision": ["REPORT_PERIOD", "MIXED", "DAY"][int(min(prec_code[a], prec_code[b]))],
                "exploratory": True,
                "primary": False,
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "review_status": REVIEW_STATUS,
                "note": "envelope overlap only; guaranteed calendars do not intersect. "
                        "Weight ZERO in every duration-weighted computation and excluded "
                        "from the operator.",
            }
            body["edge_id"] = edge_id_of(body["layer"], body["subject_id"], body["object_id"],
                                         "POSSIBLE_ONLY")
            yield body

    # ---- grouping layers: NOT operator edges -------------------------------------
    # Every row below carries operator_included False and operator_weight 0.0. They live
    # in their own files precisely so that no reader can mistake a grouping attachment
    # for a person-person tie, and so that the edges file is exactly the operator plus
    # its zero-weight POSSIBLE_ONLY companions.
    GROUPING_FLAGS = {
        "operator_included": False,
        "operator_weight": 0.0,
        "exploratory": True,
        "primary": False,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "review_status": REVIEW_STATUS,
    }

    def membership_rows():
        for (p, c) in membership_cells:
            ch, ok = inv_container[c]
            body = {
                "schema_id": GROUPING_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "membership",
                "record_kind": "person_container",
                "direction": "person_to_container",
                "subject_id": f"person:{inv_person[p]}",
                "object_id": f"container:office:{ch}:{ok}",
                "subject_kind": "person",
                "object_kind": "container",
                "subject_tier": p_tier[p],
                "status": "GUARANTEED",
                "container_kind": c_kind[c],
                "container_member_bioguide": c_bio[c],
                "kappa": float(c_kappa[c]),
                "kappa_bucket": c_kappa_bucket[c],
                "tier_strength": float(p_str[p]),
                "grouping_weight": float(c_kappa[c] * p_str[p]),
                **GROUPING_FLAGS,
            }
            body["row_id"] = edge_id_of(body["layer"], body["subject_id"], body["object_id"])
            yield body

    def revolving_rows():
        for key in sorted(revolving_records):
            record = revolving_records[key]
            c = record["container"]
            ch, ok = inv_container[c]
            body = {
                "schema_id": GROUPING_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "revolving",
                "record_kind": "container_organization",
                "direction": "container_to_organization",
                "subject_id": f"container:office:{ch}:{ok}",
                "object_id": record["organization_id"],
                "subject_kind": "container",
                "object_kind": "organization",
                "status": record["status"],
                "member_bioguide": record["bioguide"],
                "source_container_match_count": record["source_match_count"],
                "source_resolution_methods": sorted(record["source_resolution_methods"]),
                "contributing_lda_people": sorted(record["contributing_lda_people"]),
                "contributing_person_count": len(record["contributing_lda_people"]),
                "source_edge_ids": sorted(set(record["source_edge_ids"])),
                "duration_weight": 0.0,
                "grouping_weight": (
                    float(record["operator_weight"])
                    if record["status"] == "GUARANTEED"
                    else 0.0
                ),
                **GROUPING_FLAGS,
            }
            body["row_id"] = edge_id_of(
                body["layer"], body["subject_id"], body["object_id"], body["status"]
            )
            yield body
        for key in sorted(person_registrant):
            cell = person_registrant[key]
            body = {
                "schema_id": GROUPING_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "revolving",
                "record_kind": "person_registrant",
                "direction": "person_to_organization",
                "subject_id": f"person:{inv_person[cell['person']]}",
                "object_id": cell["organization_id"],
                "subject_kind": "person",
                "object_kind": "organization",
                "subject_tier": p_tier[cell["person"]],
                "status": cell["status"],
                "lda_source_person_ids": sorted(cell["lda_source_person_ids"]),
                "through_container_ids": sorted(cell["container_ids"]),
                "duration_weight": 0.0,
                "grouping_weight": 0.0,
                "identity_bridge": "SPINE_LDA_SOURCE_PERSON_ID_EXACT",
                "employment_claim": (
                    "NONE. This records that the spine person and the registrant path "
                    "share an LDA source person id, not that the person worked there; "
                    "D-021 keeps LDA an identity source only."
                ),
                **GROUPING_FLAGS,
            }
            body["row_id"] = edge_id_of(
                body["layer"], "person_registrant", body["subject_id"],
                body["object_id"], body["status"],
            )
            yield body

    def policy_rows():
        for record in policy_records:
            body = {
                "schema_id": GROUPING_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "layer": "policy_area",
                "record_kind": "person_policy_area",
                "direction": "person_to_policy_area",
                "subject_id": f"person:{inv_person[record['person']]}",
                "object_id": policy_node_id[record["issue_key"]],
                "subject_kind": "person",
                "object_kind": "policy_area",
                "subject_tier": p_tier[record["person"]],
                "status": "CURRENT_SNAPSHOT_UNDATED",
                **policy_provenance(record),
                "duration_weight": 0.0,
                "categorical_membership_weight": 1.0,
                "grouping_weight": 1.0,
                **GROUPING_FLAGS,
            }
            body["row_id"] = edge_id_of(body["layer"], body["subject_id"], body["object_id"])
            yield body

    def group_rows():
        container_people = Counter(c for (_p, c) in membership_cells)
        org_people: dict[str, set[int]] = defaultdict(set)
        for (p, org, _status) in person_registrant:
            org_people[org].add(p)
        org_containers: dict[str, set[int]] = defaultdict(set)
        for record in revolving_records.values():
            org_containers[record["organization_id"]].add(record["container"])
        policy_people_by_key: dict[str, set[int]] = defaultdict(set)
        for record in policy_records:
            policy_people_by_key[record["issue_key"]].add(record["person"])
        for c in range(NC):
            ch, ok = inv_container[c]
            yield {
                "schema_id": GROUP_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "group_id": f"container:office:{ch}:{ok}",
                "group_kind": "container",
                "name": ok,
                "member_bioguide": c_bio[c],
                "people_count": int(container_people.get(c, 0)),
                "chamber": ch,
                "container_kind": c_kind[c],
                "container_side": c_side[c],
                "kappa": float(c_kappa[c]),
                "kappa_bucket": c_kappa_bucket[c],
                "source_system": "PAYROLL",
                "operator_included": False,
                "review_status": REVIEW_STATUS,
            }
        for organization in organization_ids:
            yield {
                "schema_id": GROUP_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "group_id": organization,
                "group_kind": "organization",
                "name": None,
                "member_bioguide": None,
                "people_count": len(org_people.get(organization, ())),
                "attached_container_count": len(org_containers.get(organization, ())),
                "organization_source_id": organization.removeprefix("organization:"),
                "source_system": "LDA_REGISTRANT",
                "operator_included": False,
                "review_status": REVIEW_STATUS,
            }
        for key in policy_keys:
            yield {
                "schema_id": GROUP_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "group_id": policy_node_id[key],
                "group_kind": "policy_area",
                "name": key.title(),
                "member_bioguide": None,
                "people_count": len(policy_people_by_key.get(key, ())),
                "issue_area": key.title(),
                "source_system": "POLITICO_PRO_STAFFER_DIRECTORY",
                "temporal_scope": "CURRENT_SNAPSHOT_UNDATED",
                "operator_included": False,
                "review_status": REVIEW_STATUS,
            }

    edges_path = out / EDGES_FILENAME
    n_edges = write_rows(edges_path, edge_rows())
    membership_path = out / MEMBERSHIP_LAYER_FILENAME
    n_membership = write_rows(membership_path, membership_rows())
    revolving_path = out / REVOLVING_LAYER_FILENAME
    n_revolving = write_rows(revolving_path, revolving_rows())
    policy_path = out / POLICY_LAYER_FILENAME
    n_policy = write_rows(policy_path, policy_rows())
    groups_path = out / GROUPS_FILENAME
    n_groups = write_rows(groups_path, group_rows())

    if n_membership != len(membership_cells):
        raise BuildError("membership grouping layer lost rows")
    if n_revolving != len(revolving_records) + len(person_registrant):
        raise BuildError("revolving grouping layer lost rows")
    if n_policy != len(policy_records):
        raise BuildError("policy grouping layer lost rows")
    if n_groups != NC + len(organization_ids) + len(policy_keys):
        raise BuildError("groups roster lost rows")
    if n_edges != guaranteed_pairs + possible_pairs:
        raise BuildError("edges file is not exactly the co-tenure rows")

    receipt["grouping_layers"] = {
        "rule": (
            "containers, organisations and policy areas leave the people network "
            "(D-022). They are emitted here, never in node_scores and never in the "
            "operator; every row carries operator_included False."
        ),
        "files": {
            "membership_layer": MEMBERSHIP_LAYER_FILENAME,
            "revolving_layer": REVOLVING_LAYER_FILENAME,
            "policy_layer": POLICY_LAYER_FILENAME,
            "groups": GROUPS_FILENAME,
        },
        "membership": {
            "rows": int(n_membership),
            "conserved_against": "person_container_cells",
            "input_count": len(pc_core),
            "conserved": bool(n_membership == len(pc_core)),
        },
        "revolving": {
            "rows": int(n_revolving),
            "container_organization_rows": len(revolving_records),
            "person_registrant_rows": len(person_registrant),
            "conserved_against": "revolving_records + person_registrant cells",
            "input_count": len(revolving_records) + len(person_registrant),
            "conserved": bool(
                n_revolving == len(revolving_records) + len(person_registrant)
            ),
            "contributing_lda_ids_with_no_spine_person": len(registrant_lda_ids_unjoined),
        },
        "policy_area": {
            "rows": int(n_policy),
            "conserved_against": "person_policy_memberships",
            "input_count": len(policy_memberships),
            "conserved": bool(n_policy == len(policy_memberships)),
        },
        "groups": {
            "rows": int(n_groups),
            "container": NC,
            "organization": len(organization_ids),
            "policy_area": len(policy_keys),
            "conserved": bool(n_groups == NC + len(organization_ids) + len(policy_keys)),
        },
        "operator_rows_in_grouping_layers": 0,
    }

    attached_by_person: dict[int, list[str]] = defaultdict(list)
    attached_bios_by_person: dict[int, list[str]] = defaultdict(list)
    for (p, c) in sorted(pc_core):
        ch, ok = inv_container[c]
        attached_by_person[p].append(f"container:office:{ch}:{ok}")
        if c_bio[c]:
            attached_bios_by_person[p].append(c_bio[c])
    for p in attached_bios_by_person:
        attached_bios_by_person[p] = sorted(set(attached_bios_by_person[p]))

    def node_rows():
        """PERSONS ONLY. A container, organisation or policy area never appears here."""
        for i in range(NP):
            pid = inv_person[i]
            yield {
                "schema_id": NODE_SCHEMA_ID,
                "rule_version": RULE_VERSION,
                "node_id": node_ids[i],
                "node_kind": "person",
                "component_id": int(comp_labels[i]),
                "component_size": int(comp_sizes[comp_labels[i]]),
                "isolate": bool(raw_strength[i] == 0.0),
                "raw_strength": float(raw_strength[i]),
                "co_tenure_degree": int(co_tenure_degree[i]),
                "connectedness_pagerank_exploratory": [
                    {"alpha": float(a), "score": float(pageranks[a][i])} for a in ALPHAS
                ],
                "eigenvector_component_local_exploratory": (
                    None if np.isnan(eigenvector[i]) else float(eigenvector[i])
                ),
                "office_diversity_exploratory": float(office_div[i]),
                "office_diversity_distinct_offices": int(office_distinct[i]),
                "office_connection_strengths": {
                    f"container:office:{inv_container[int(c)][0]}:{inv_container[int(c)][1]}": float(m * raw_strength[i])
                    for c, m in zip(_office_mass.getrow(i).indices, _office_mass.getrow(i).data)
                },
                "ranking_math_version": RANKING_VERSION,
                "identity_tier": p_tier[i],
                "chambers": person_chambers.get(pid, []),
                "member_bioguides": person_bios.get(pid, []),
                "attached_container_ids": attached_by_person.get(i, []),
                "attached_member_bioguides": attached_bios_by_person.get(i, []),
                "attached_container_count": int(attached_container_count[i]),
                "policy_area_group_count": int(policy_group_count[i]),
                "registrant_organization_group_count": int(registrant_org_count[i]),
                "lda_source_person_id": person_lda.get(pid),
                "quorum_staff_id": person_quorum.get(pid),
                "grouping_note": (
                    "attached_* and *_group_count are GROUPING attachments, listed in "
                    "membership_layer / revolving_layer / policy_layer and rostered in "
                    "staffer_social_groups.ndjson.gz. They are not operator edges and contribute "
                    "nothing to any score on this row."
                ),
                "exploratory": True,
                "primary": False,
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "review_status": REVIEW_STATUS,
            }

    nodes_path = out / NODES_FILENAME
    n_nodes = write_rows(nodes_path, node_rows())
    if n_nodes != NP:
        raise BuildError("node_scores must contain exactly one row per person")
    traj_path = out / TRAJ_FILENAME
    n_traj = write_rows(traj_path, traj_rows)
    moves_path = out / MOVES_FILENAME
    n_moves = write_rows(moves_path, move_rows)
    review_path = out / POLITICO_REVIEW_FILENAME
    n_review = write_rows(review_path, politico_review_rows) if review_layers_enabled else 0

    # ---- receipt -----------------------------------------------------------------
    # A LIMITED RUN cannot satisfy the full-population gates: the named people and the
    # Politico/LDA joins live outside a 2,000-person prefix by construction. Those gates
    # are recorded as warnings there and stay HARD for any unlimited build - the limited
    # branch is opt-in via --limit-persons and is declared in the receipt.
    build_failures: list[str] = []
    build_warnings: list[str] = []
    population_gates = []
    if not gordon_pass:
        population_gates.append("NAMED_REGRESSION_GORDON_HOLZBERG")
    if not stephanie_pass:
        population_gates.append("NAMED_REGRESSION_STEPHANIE_BELK")
    if not policy_memberships:
        population_gates.append("POLICY_AREA_LAYER_EMPTY")
    if not revolving_records:
        population_gates.append("REVOLVING_LAYER_EMPTY")
    if limited_run:
        build_warnings.extend("LIMITED_RUN_" + name for name in population_gates)
    else:
        build_failures.extend(population_gates)
    receipt.update({
        "schema_id": RECEIPT_SCHEMA_ID,
        "rule_version": RULE_VERSION,
        "method_version": METHOD_VERSION,
        "config_name": args.config_name,
        "vintage": args.vintage,
        "generated_at": args.generated_at,
        "status": "PASS" if not build_failures else "FAIL",
        "failures": build_failures,
        "warnings": build_warnings,
        "operator_definition": OPERATOR_DEFINITION,
        "pending_rulings": PENDING_RULINGS,
        "exploratory": True,
        "primary": False,
        "primary_weights_emitted": 0,
        "review_status": REVIEW_STATUS,
        "promotion_policy": PROMOTION_POLICY,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "canonical_office_promotions": 0,
        "canonical_person_merges": 0,
        "complete_history_assertions": int(
            review_layer_counts.get("politico_employment_history", 0)
            + review_layer_counts.get("politico_education_history", 0)
        ),
        "complete_employment_history_assertions": int(
            review_layer_counts.get("politico_employment_history", 0)
        ),
        "complete_education_history_assertions": int(
            review_layer_counts.get("politico_education_history", 0)
        ),
        "date_promotions": 0,
        "statement": STATEMENT,
        "weight_semantics": WEIGHT_SEMANTICS,
        "layers": ["co_tenure", "revolving", "membership", "policy_area"],
        "operator_layers": ["co_tenure"],
        "grouping_layer_names": ["membership", "revolving", "policy_area"],
        "review_only_layers": sorted(review_layer_counts),
        "revolving_layer_status": {
            "edges": len(revolving_records),
            "operator_edges_guaranteed": 0,
            "rows_with_positive_source_strength": len(rev_positive),
            "status_counts": dict(sorted(Counter(
                row["status"] for row in revolving_records.values()
            ).items())),
            "population_rule": (
                "the payroll co-tenure universe remains complete; the independently "
                "verified LDA slice contributes only the separate revolving layer"
            ),
        },
        "dial_status": DIAL_STATUS,
        "dials": {
            "tau_days": TAU_DAYS,
            "kappa": dict(KAPPA),
            "s_strength": dict(S_STRENGTH),
            "alphas": list(ALPHAS),
            "sweep_factors": list(SWEEP_FACTORS),
            "sweep_clamp_maximum": SWEEP_CLAMP_MAXIMUM,
            "every_value_above": "UNTESTED DEFAULT PENDING PAUL'S FREEZE",
            "kappa_aggregation_declared_choice": (
                "An edge can draw guaranteed overlap from more than one shared container. "
                "This build uses the MAXIMUM design-6.2 kappa over the containers that "
                "actually contributed days - the closest shared office governs the tie. "
                "This is a DECLARED choice, not a silent one: kappa_min is emitted on "
                "every edge beside it, so the minimum-kappa alternative is recomputable "
                "from the artifact without a rebuild."
            ),
            "kappa_committee_opposite_side_unpopulated": (
                "The 0.40 opposite-side row is REACHABLE - a committee employs both "
                "majority and minority staff on one payroll, so two people in the same "
                "committee container can be on opposite sides. It is unpopulated here "
                "purely because side is UNKNOWN for the overwhelming majority of "
                "committee episodes (see C8c_committee_side_coverage). Data coverage, "
                "not structure."
            ),
        },
        "node_universe": {
            "person": NP,
            "total": NN,
            "person_by_chamber": dict(Counter(
                ",".join(person_chambers.get(inv_person[p], [])) for p in range(NP)
            )),
            "note": (
                "the node universe IS the person universe (D-022). Container, "
                "organization and policy_area counts moved to group_universe and are "
                "rostered in staffer_social_groups.ndjson.gz; they are not nodes."
            ),
        },
        "group_universe": {
            "container": NC,
            "organization": len(organization_ids),
            "policy_area": len(policy_keys),
            "total": NC + len(organization_ids) + len(policy_keys),
            "container_by_kind": dict(Counter(c_kind)),
            "container_by_chamber": dict(Counter(c_chamber)),
        },
        "edge_counts": {
            "co_tenure_guaranteed": int(guaranteed_pairs),
            "co_tenure_possible_only_zero_weight": int(possible_pairs),
            "co_tenure_zero_overlap_REJECTED_never_emitted": int(zero_overlap_pairs),
            "membership": int(n_membership),
            "revolving": len(revolving_records),
            "revolving_person_registrant": len(person_registrant),
            "revolving_in_operator": 0,
            "policy_area_membership": int(n_policy),
            "groups": int(n_groups),
            "politico_review_only": int(n_review),
            "sequence_person_person": 0,
            "operator_edges": int(eu.size),
            "edges_file_rows_emitted": int(n_edges),
            "total_rows_emitted": int(
                n_edges + n_membership + n_revolving + n_policy + n_groups
            ),
            "largest_container_person_count": max(
                (len(v) for v in by_container.values()), default=0
            ),
            # The line above spans EVERY container. Co-tenure pairs are enumerated
            # only inside eligible ones, so this is the bound that actually applies
            # to the co_tenure counts beside it (owner ruling 2026-09-07).
            "largest_co_tenure_eligible_container_person_count": max(
                (len(by_container[cid]) for cid in co_tenure_containers), default=0
            ),
        },
        "self_loops": 0,
        "zero_overlap_edges_emitted": 0,
        "records_read": {
            "hill_person_office_spans": len(episodes),
            "hill_person_spine": len(person_tier),
            "hill_member_office_index": container_meta_source_rows,
            "normalized_container_metadata_rows": len(container_meta),
            "house_personnel_observations_with_service_dates": int(dp_rows),
        },
    })

    # inputs + files with sha256
    receipt["inputs"] = [
        {"role": name, "path": str(p), "bytes": p.stat().st_size, "sha256": sha256_file(p)}
        for name, p in sorted(paths.items())
    ]
    receipt["implementation"] = {
        "path": "audits/staffer_network/build_staffer_social_network.py",
        "sha256": sha256_file(Path(__file__).resolve()),
    }
    file_specs = [
        ("staffer_social_edges", edges_path, n_edges),
        ("staffer_social_node_scores", nodes_path, n_nodes),
        ("staffer_trajectories", traj_path, n_traj),
        ("staffer_office_moves", moves_path, n_moves),
        ("membership_layer", membership_path, n_membership),
        ("revolving_layer", revolving_path, n_revolving),
        ("policy_layer", policy_path, n_policy),
        ("groups", groups_path, n_groups),
    ]
    if review_layers_enabled:
        file_specs.append(("staffer_social_politico_review_layers", review_path, n_review))
    receipt["files"] = [
        {"role": role, "path": p.name, "bytes": p.stat().st_size,
         "records": n, "sha256": sha256_file(p)}
        for role, p, n in file_specs
    ]

    # roster metadata (C-10)
    roster = json.load(open(paths["roster_congestion"], encoding="utf-8"))
    roster_bios = {r["bioguide"]: r.get("chamber") for r in roster if r.get("bioguide")}
    attached = {b for b in c_bio if b}
    receipt["roster_metadata"] = {
        "source": str(paths["roster_congestion"]),
        "sha256": sha256_file(paths["roster_congestion"]),
        "roster_size": len(roster_bios),
        "roster_members_with_an_attached_container": len(set(roster_bios) & attached),
        "roster_members_without_an_attached_container": sorted(set(roster_bios) - attached),
        "all_member_bioguides_attached": len(attached),
        "historic_members_attached_not_on_roster": len(attached - set(roster_bios)),
    }

    receipt_path = out / RECEIPT_FILENAME
    receipt_path.write_bytes(canonical_json_bytes(receipt) + b"\n")

    manifest = {
        "schema_id": MANIFEST_SCHEMA_ID,
        "config_name": args.config_name,
        "generation_id": out.name,
        "vintage": args.vintage,
        "rule_version": RULE_VERSION,
        "method_version": METHOD_VERSION,
        "dial_status": DIAL_STATUS,
        "dials": receipt["dials"],
        "layers": receipt["layers"],
        "review_only_layers": receipt["review_only_layers"],
        "roster_metadata": receipt["roster_metadata"],
        "inputs_sha256": {i["role"]: i["sha256"] for i in receipt["inputs"]},
        "implementation_sha256": receipt["implementation"]["sha256"],
        "artifacts": {f["role"]: {"path": f["path"], "bytes": f["bytes"],
                                  "records": f["records"], "sha256": f["sha256"]}
                      for f in receipt["files"]},
        "receipt": {"path": RECEIPT_FILENAME,
                    "sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest()},
        "canonical_output_hash": hashlib.sha256(
            canonical_json_bytes([f["sha256"] for f in receipt["files"]])
        ).hexdigest(),
        "promotion_policy": PROMOTION_POLICY,
        "review_status": REVIEW_STATUS,
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "statement": STATEMENT,
    }
    (out / MANIFEST_FILENAME).write_bytes(canonical_json_bytes(manifest) + b"\n")
    return {"receipt": receipt, "manifest": manifest, "output": str(out)}


def parse_args(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repository-root", default=str(REPOSITORY_ROOT))
    ap.add_argument("--hill-spine-root")
    ap.add_argument("--house-ledger-root")
    ap.add_argument("--senate-committee-root")
    politico_direct = (
        REPOSITORY_ROOT
        / "audits/staffer_network/politico_payroll_direct_links_20260903_v3_primary"
    )
    ap.add_argument(
        "--politico-direct-policy-memberships",
        default=str(politico_direct / "politico_policy_memberships.ndjson.gz"),
    )
    ap.add_argument(
        "--politico-direct-link-receipt",
        default=str(politico_direct / "politico_payroll_direct_link_receipt.json"),
    )
    ap.add_argument("--politico-current-committee-assertions")
    ap.add_argument("--politico-profile-employment-assertions")
    ap.add_argument("--politico-profile-education-assertions")
    ap.add_argument("--politico-profile-policy-deltas")
    ap.add_argument("--politico-explicit-committee-side-assertions")
    ap.add_argument(
        "--require-complete-politico-profile-crawl",
        action="store_true",
        help="Require the bridge receipt to prove verified terminal profile coverage",
    )
    ap.add_argument(
        "--exploratory-revolving-edges",
        default=str(
            REPOSITORY_ROOT
            / "audits/staffer_network/exploratory_temporal_tier_20260902_v1_primary/exploratory_temporal_edges.ndjson.gz"
        ),
    )
    ap.add_argument(
        "--spine-id-map",
        help=(
            "Optional {legacy_person_id, person_id, reason} NDJSON(.gz) re-key map. "
            "REQUIRED whenever the Politico direct-link receipt binds a different Hill "
            "spine generation than --hill-spine-root: the bridge's spine_person_id "
            "values then live in the OLD id namespace and must be remapped before they "
            "can be joined. The build fails loudly rather than silently dropping them."
        ),
    )
    ap.add_argument(
        "--limit-persons",
        type=int,
        default=0,
        help=(
            "SMOKE TEST DIAL. Restrict the person universe to the first N distinct "
            "spine_person_ids encountered while reading hill_person_office_spans in "
            "file order, and drop every span row for a person outside that set. The "
            "spans file is ordered by spine_person_id, which is a sha256 digest, so "
            "this is a deterministic pseudo-random subsample: pair counts fall as "
            "(N/total)^2 and the subgraph is NOT representative. A limited run marks "
            "itself limited_run in the receipt and downgrades the full-population "
            "gates (named regressions, non-empty grouping layers) to warnings."
        ),
    )
    ap.add_argument(
        "--design-doc",
        default=str(Path.home() / "Downloads" / "STAFFER_NETWORK_EXPANSION_DESIGN_20260829.md"),
    )
    ap.add_argument(
        "--metrics-doc",
        default=str(Path.home() / "Downloads" / "STAFFER_NETWORK_METRICS_20260829.md"),
    )
    ap.add_argument("--config-name", default=CONFIG_NAME)
    ap.add_argument("--vintage", default=VINTAGE)
    ap.add_argument("--generated-at", default="2026-09-07T00:00:00Z")
    ap.add_argument("--output", required=True)
    ap.add_argument("--no-glassbox", action="store_true")
    args = ap.parse_args(argv)
    args.glassbox = not args.no_glassbox
    if args.limit_persons < 0:
        ap.error("--limit-persons must be zero (no limit) or positive")
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    emit_glassbox(enabled=args.glassbox, event="build_start", payload={"output": args.output})
    try:
        result = run(args)
    except Exception as exc:                                            # noqa: BLE001
        emit_glassbox(enabled=args.glassbox, event="build_failed", payload={"error": str(exc)[:400]})
        raise
    emit_glassbox(enabled=args.glassbox, event="build_complete",
                  payload={"output": result["output"],
                           "canonical_output_hash": result["manifest"]["canonical_output_hash"]})
    print(json.dumps({k: v for k, v in result["receipt"].items()
                      if k not in ("inputs", "files", "sweep")}, indent=1, default=str))
    return 0 if result["receipt"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
