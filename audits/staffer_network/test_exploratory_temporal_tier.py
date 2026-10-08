# -*- coding: utf-8 -*-
"""Synthetic-fixture tests for the exploratory temporal tier (Part B).

No live data is read.  Every test constructs a small Part A generation in a
pytest ``tmp_path``, builds the exploratory tier from it, and checks the rules
the spec names: duplicate periods must not inflate a calendar, possible-only
pairs must carry zero weight, ``tier_strength`` must be the minimum of the two
endpoint tiers, the four revolving order classes must be reachable, one person
must contribute once per member office and organization, the tier thresholds
must restrict both the node universe and the revolving weight, every emitted
row must validate against its committed schema, and a fixture with
``exploratory: false`` must make the verifier FAIL.
"""

from __future__ import annotations

from collections import Counter
from datetime import date
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import pytest

import build_exploratory_temporal_tier as subject
import verify_exploratory_temporal_tier as verifier


GENERATED_AT = "2026-09-02T00:00:00Z"

PERSON_SUMMARY = [
    {"lda_source_person_id": "P1", "max_tier": "L4", "registrant_side_tier": "R2"},
    {"lda_source_person_id": "P2", "max_tier": "L3", "registrant_side_tier": "R1"},
    {"lda_source_person_id": "P3", "max_tier": "L2", "registrant_side_tier": None},
    {"lda_source_person_id": "P4", "max_tier": "L1", "registrant_side_tier": None},
    {"lda_source_person_id": "P5", "max_tier": "L0", "registrant_side_tier": None},
    {"lda_source_person_id": "P6", "max_tier": "L3", "registrant_side_tier": None},
]

MEMBER_OFFICE = {
    "chamber": "house",
    "office_key": "HOYER_MD",
    "member_bioguide": "A000001",
    "container_kind": "member_office",
}
COMMITTEE = {
    "chamber": "house",
    "office_key": "COMMITTEE_ON_FINANCIAL_SERVICES",
    "member_bioguide": None,
    "container_kind": "committee",
}


def _record(person: str, tier: str, container: dict, core, envelope) -> dict:
    row = {
        "lda_source_person_id": person,
        "tier": tier,
        "core": {"start_latest": core[0], "end_earliest": core[1]},
        "envelope": {"start_earliest": envelope[0], "end_latest": envelope[1]},
        "review_status": "REVIEW_REQUIRED",
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
    }
    row.update(container)
    return row


PERSON_OFFICE_RECORDS = [
    # P1 files the same pay window twice: the union must not double count.
    _record("P1", "L4", MEMBER_OFFICE, ("2013-01-01", "2014-01-01"),
            ("2012-10-01", "2014-04-01")),
    _record("P1", "L4", MEMBER_OFFICE, ("2013-01-01", "2014-01-01"),
            ("2012-10-01", "2014-04-01")),
    _record("P2", "L3", MEMBER_OFFICE, ("2013-07-01", "2015-01-01"),
            ("2013-04-01", "2015-04-01")),
    _record("P3", "L2", MEMBER_OFFICE, ("2014-07-01", "2014-10-01"),
            ("2014-01-01", "2015-01-01")),
    _record("P6", "L3", MEMBER_OFFICE, ("2020-01-01", "2020-04-01"),
            ("2020-01-01", "2020-04-01")),
    # A second shared container whose overlap sits inside the first one:
    # the cross-container union must not add days.
    _record("P1", "L4", COMMITTEE, ("2013-09-01", "2013-12-01"),
            ("2013-09-01", "2013-12-01")),
    _record("P2", "L3", COMMITTEE, ("2013-09-01", "2013-12-01"),
            ("2013-09-01", "2013-12-01")),
    # Below the L2 record floor and below the node-universe floor.
    _record("P4", "L2", MEMBER_OFFICE, ("2013-01-01", "2014-01-01"),
            ("2013-01-01", "2014-01-01")),
    _record("P2", "L1", MEMBER_OFFICE, ("2001-01-01", "2002-01-01"),
            ("2001-01-01", "2002-01-01")),
]

REGISTRANT_RECORDS = [
    {
        "lda_source_person_id": "P1",
        "registrant_source_org_id": "ORG1",
        "registrant_name": "First Registrant LLC",
        "filing_year_first": 2016,
        "filing_year_last": 2018,
        "registrant_side_tier": "R2",
        "hill_registrant_order": "ORDERED",
    },
    {
        "lda_source_person_id": "P3",
        "registrant_source_org_id": "ORG1",
        "filing_year_first": 2016,
        "filing_year_last": 2017,
        "registrant_side_tier": "R1",
    },
    {
        "lda_source_person_id": "P2",
        "registrant_source_org_id": "ORG2",
        "filing_year_first": 2015,
        "filing_year_last": 2016,
        "registrant_side_tier": "R1",
    },
    {
        "lda_source_person_id": "P3",
        "registrant_source_org_id": "ORG3",
        "filing_years": [2010, 2011, 2012],
        "registrant_side_tier": "R0",
    },
    {
        "lda_source_person_id": "P3",
        "registrant_source_org_id": "ORG4",
    },
]

FILER_EPISODES = [
    {"lda_source_person_id": "P1", "start_year": 2013, "end_year": 2014},
    {"lda_source_person_id": "P2", "start_year": 2014, "end_year": 2015},
]

PART_A_RECEIPT = {
    "schema_id": "staffer-network-tiered-corroboration-receipt-v1",
    "status": "PASS",
    "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
    "canonical_employment_promotions": 0,
    "canonical_identity_promotions": 0,
}


# ---------------------------------------------------------------------------
# fixture plumbing
# ---------------------------------------------------------------------------


def canonical(value) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def write_gzip(path: Path, rows) -> None:
    raw = path.open("wb")
    stream = gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=6, mtime=0)
    try:
        for row in rows:
            stream.write(canonical(row))
    finally:
        stream.close()
        raw.close()


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_part_a(root: Path, *, records=None, summary=None, registrants=None) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write_gzip(
        root / "tiered_person_office_records.ndjson.gz",
        PERSON_OFFICE_RECORDS if records is None else records,
    )
    write_gzip(
        root / "tiered_person_summary_25340.ndjson.gz",
        PERSON_SUMMARY if summary is None else summary,
    )
    write_gzip(root / "filer_asserted_year_episodes.ndjson.gz", FILER_EPISODES)
    write_gzip(
        root / "registrant_side_records.ndjson.gz",
        REGISTRANT_RECORDS if registrants is None else registrants,
    )
    (root / "tiered_corroboration_receipt.json").write_bytes(canonical(PART_A_RECEIPT))
    return root


def build(sidecar: Path, output: Path, extra=()) -> dict:
    argv = [
        "--sidecar-root", str(sidecar),
        "--output-root", str(output),
        "--generated-at", GENERATED_AT,
        "--no-glassbox",
        *extra,
    ]
    return subject.run(subject.parse_args(argv))


def read_rows(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


@pytest.fixture(scope="module")
def generation(tmp_path_factory) -> dict:
    root = tmp_path_factory.mktemp("exploratory")
    sidecar = write_part_a(root / "sidecar")
    primary = root / "generation_primary"
    receipt = build(sidecar, primary)
    return {
        "root": root,
        "sidecar": sidecar,
        "primary": primary,
        "receipt": receipt,
        "edges": read_rows(primary / subject.EDGES_FILENAME),
        "scores": read_rows(primary / subject.SCORES_FILENAME),
    }


def co_tenure_edge(generation: dict, left: str, right: str) -> dict:
    for row in generation["edges"]:
        if row["layer"] != "co_tenure":
            continue
        if row["subject_id"] == f"person:{left}" and row["object_id"] == f"person:{right}":
            return row
    raise AssertionError(f"no co-tenure edge for {left} and {right}")


def revolving_edge(generation: dict, organization: str) -> dict:
    for row in generation["edges"]:
        if row["layer"] == "revolving" and row["object_id"] == f"organization:{organization}":
            return row
    raise AssertionError(f"no revolving edge for {organization}")


def run_verifier(primary: Path, report: Path, twin: Path | None = None) -> dict:
    argv = [
        "--primary-root", str(primary),
        "--report-root", str(report),
        "--generated-at", GENERATED_AT,
        "--no-glassbox",
    ]
    if twin is not None:
        argv += ["--twin-root", str(twin)]
    return verifier.verify(verifier.parse_args(argv))


def clone(primary: Path, destination: Path) -> Path:
    shutil.copytree(primary, destination)
    return destination


def rewrite_edges(generation_dir: Path, rows) -> None:
    """Rewrite the edge file and re-bind its hash in the receipt."""

    path = generation_dir / subject.EDGES_FILENAME
    write_gzip(path, rows)
    receipt_path = generation_dir / subject.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for entry in receipt["files"]:
        if entry["role"] == "exploratory_temporal_edges":
            entry["records"] = len(rows)
            entry["bytes"] = path.stat().st_size
            entry["sha256"] = sha256_of(path)
    receipt_path.write_bytes(canonical(receipt))


# ---------------------------------------------------------------------------
# interval algebra
# ---------------------------------------------------------------------------


def test_duplicate_and_adjacent_runs_union_without_inflating() -> None:
    duplicated = [
        (date(2013, 1, 1), date(2014, 1, 1)),
        (date(2013, 1, 1), date(2014, 1, 1)),
    ]
    assert subject.union_half_open(duplicated) == [
        (date(2013, 1, 1), date(2014, 1, 1))
    ]
    assert subject.calendar_days(subject.union_half_open(duplicated)) == 365
    adjacent = [
        (date(2013, 1, 1), date(2013, 4, 1)),
        (date(2013, 4, 1), date(2013, 7, 1)),
    ]
    assert subject.union_half_open(adjacent) == [(date(2013, 1, 1), date(2013, 7, 1))]


def test_intersection_agrees_with_the_reviewed_interval_functions() -> None:
    left = [(date(2013, 1, 1), date(2014, 1, 1))]
    right = [(date(2013, 7, 1), date(2015, 1, 1))]
    guaranteed = subject.intersect_calendars(left, right, guaranteed=True)
    assert guaranteed == [(date(2013, 7, 1), date(2014, 1, 1))]
    assert subject.calendar_days(guaranteed) == 184
    assert subject.intersect_calendars(
        left, [(date(2020, 1, 1), date(2021, 1, 1))], guaranteed=False
    ) == []


def test_spearman_handles_ties_and_reversal() -> None:
    assert subject.spearman([1.0, 2.0, 3.0, 4.0], [1.0, 2.0, 3.0, 4.0]) == 1.0
    assert subject.spearman([1.0, 2.0, 3.0, 4.0], [4.0, 3.0, 2.0, 1.0]) == -1.0
    assert subject.spearman([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None
    assert subject.spearman([1.0], [1.0]) is None


# ---------------------------------------------------------------------------
# co-tenure rules
# ---------------------------------------------------------------------------


def test_duplicate_periods_do_not_inflate_the_pair_calendar(generation) -> None:
    edge = co_tenure_edge(generation, "P1", "P2")
    assert edge["status"] == "GUARANTEED"
    # 2013-07-01 .. 2014-01-01 counted once despite the duplicated P1 record.
    assert edge["guaranteed_days"] == 184


def test_cross_container_union_does_not_double_count(generation) -> None:
    edge = co_tenure_edge(generation, "P1", "P2")
    assert edge["container_count"] == 2
    assert edge["guaranteed_days"] == 184
    assert edge["possible_days"] == 365


def test_possible_only_pair_carries_zero_tiered_weight(generation) -> None:
    edge = co_tenure_edge(generation, "P1", "P3")
    assert edge["status"] == "POSSIBLE_ONLY"
    assert edge["guaranteed_days"] == 0
    assert edge["possible_days"] == 90
    assert edge["w_lower"] == 0.0
    assert edge["w_upper"] > 0.0
    assert edge["w_tiered_lower"] == 0.0
    assert edge["surviving_tier_thresholds"] == []


def test_zero_overlap_pairs_are_counted_but_never_emitted(generation) -> None:
    counts = generation["receipt"]["co_tenure_status_counts"]
    assert counts["ZERO_OVERLAP"] == 3
    assert counts["GUARANTEED"] == 2
    assert counts["POSSIBLE_ONLY"] == 1
    assert generation["receipt"]["edge_counts"]["co_tenure_pairs_evaluated"] == 6
    # The pair enumeration is quadratic in this number; the receipt exposes it.
    assert generation["receipt"]["edge_counts"]["largest_container_person_count"] == 4
    assert generation["receipt"]["zero_overlap_edges_emitted"] == 0
    assert all(row["status"] != "ZERO_OVERLAP" for row in generation["edges"])


def test_tier_strength_is_the_minimum_of_the_two_endpoint_tiers(generation) -> None:
    strong = co_tenure_edge(generation, "P1", "P2")
    assert strong["subject_tier"] == "L4"
    assert strong["object_tier"] == "L3"
    assert strong["tier_strength"] == pytest.approx(0.50)
    assert strong["w_tiered_lower"] == pytest.approx(0.50 * strong["w_lower"])

    weak = co_tenure_edge(generation, "P2", "P3")
    assert weak["tier_strength"] == pytest.approx(0.25)
    assert weak["guaranteed_days"] == 92


def test_people_below_the_node_universe_floor_never_appear(generation) -> None:
    node_ids = {row["node_id"] for row in generation["scores"]}
    assert "person:P4" not in node_ids
    assert "person:P5" not in node_ids
    endpoints = {row["subject_id"] for row in generation["edges"]}
    endpoints |= {row["object_id"] for row in generation["edges"]}
    assert "person:P4" not in endpoints


# ---------------------------------------------------------------------------
# R4: person-to-container membership layer
# ---------------------------------------------------------------------------


def test_membership_edge_is_emitted_once_per_l2_plus_record(generation) -> None:
    membership_edges = [row for row in generation["edges"] if row["layer"] == "membership"]
    # P1 (2 duplicate MEMBER_OFFICE rows + 1 COMMITTEE row), P2 (MEMBER_OFFICE
    # + COMMITTEE), P3 and P6 (one MEMBER_OFFICE row each): 7 total. P4's
    # single L2 record does not count -- P4's max_tier is L1, below the
    # node-universe floor, and its L1 record from P2 never entered the
    # sidecar universe at all (the record floor).
    assert len(membership_edges) == 7
    assert generation["receipt"]["edge_counts"]["membership"] == 7
    by_person = Counter(row["subject_id"] for row in membership_edges)
    assert by_person == {
        "person:P1": 3,
        "person:P2": 2,
        "person:P3": 1,
        "person:P6": 1,
    }
    default_strength = {"L2": 0.25, "L3": 0.50, "L4": 0.75, "L5": 1.00}
    for row in membership_edges:
        assert row["status"] == "GUARANTEED"
        assert row["direction"] == "undirected"
        assert row["object_kind"] == "container"
        assert row["subject_kind"] == "person"
        expected_weight = default_strength[row["subject_tier"]]
        assert row["tier_strength"] == pytest.approx(expected_weight)
        assert row["w_tiered_lower"] == pytest.approx(expected_weight)


def test_membership_layer_declared_in_the_receipt(generation) -> None:
    assert generation["receipt"]["layers"] == ["co_tenure", "revolving", "membership"]


def test_bridging_diversity_is_not_identically_zero(generation) -> None:
    """R4: once membership ties people to containers alongside the existing
    container-to-organization revolving ties, a container that has both
    kinds of neighbor must show nonzero bridging diversity somewhere.
    """

    container_id = "container:bioguide:A000001"
    rows = [row for row in generation["scores"] if row["node_id"] == container_id]
    assert rows
    nonzero = [
        row for row in rows
        if (row["bridging_diversity_exploratory"] or 0.0) > 0.0
    ]
    assert nonzero, "container bridging diversity is identically zero"


def test_pagerank_operator_stays_row_stochastic_across_three_layers() -> None:
    """Direct unit check of run_operator with all three layers active at
    once: row sums stay 1 (PageRank's underlying transition operator), and
    a node touching two different node kinds shows nonzero bridging.
    """

    node_ids = ["container:c1", "organization:o1", "person:p1", "person:p2"]
    group_codes = [1, 2, 0, 0]
    subjects = [2, 0, 2, 3]
    objects = [3, 1, 0, 0]
    weights = [0.5, 0.5, 0.25, 0.5]
    layers = [
        subject.CO_TENURE_LAYER,
        subject.REVOLVING_LAYER,
        subject.MEMBERSHIP_LAYER,
        subject.MEMBERSHIP_LAYER,
    ]
    result = subject.run_operator(
        node_ids, group_codes, subjects, objects, weights, layers, (0.85,)
    )
    import numpy as np

    row_sums = np.asarray(result["transition"].sum(axis=1)).ravel()
    assert all(abs(value - 1.0) < 1e-9 for value in row_sums)
    container_index = node_ids.index("container:c1")
    assert result["bridging"][container_index] > 0.0


# ---------------------------------------------------------------------------
# revolving rules
# ---------------------------------------------------------------------------


def test_revolving_order_classes_are_all_reachable(generation) -> None:
    assert revolving_edge(generation, "ORG1")["status"] == "GUARANTEED"
    assert revolving_edge(generation, "ORG2")["status"] == "POSSIBLE_ONLY"
    assert revolving_edge(generation, "ORG3")["status"] == "WRONG_ORDER"
    assert revolving_edge(generation, "ORG4")["status"] == "INTERVAL_BLOCKED"
    counts = generation["receipt"]["revolving_path_status_counts"]
    assert counts == {
        "GUARANTEED": 3,
        "POSSIBLE_ONLY": 1,
        "WRONG_ORDER": 1,
        "INTERVAL_BLOCKED": 1,
    }


def test_core_end_variant_is_reported_separately(generation) -> None:
    variant = generation["receipt"]["revolving_path_status_counts_core_end_variant"]
    # The spec's literal core-end test promotes the P2/ORG2 path that the
    # adjudicated guaranteed-ordering test leaves at POSSIBLE_ONLY.
    assert variant["GUARANTEED"] == 4
    assert variant["POSSIBLE_ONLY"] == 0


def test_only_member_office_containers_produce_revolving_edges(generation) -> None:
    subjects = {
        row["subject_id"] for row in generation["edges"] if row["layer"] == "revolving"
    }
    assert subjects == {"container:bioguide:A000001"}


def test_one_person_contributes_once_per_member_and_organization(generation) -> None:
    edge = revolving_edge(generation, "ORG1")
    people = [item["lda_source_person_id"] for item in edge["contributions"]]
    assert people == ["P1", "P3"]
    assert len(people) == len(set(people))
    assert edge["contributing_person_count"] == 2
    # P1 duplicated its Hill record; the edge still counts P1 once.
    assert edge["strength_sum"] == pytest.approx(0.75 * 1.00 + 0.25 * 0.50)
    assert edge["w_tiered_lower"] == pytest.approx(edge["strength_sum"])


def test_non_guaranteed_revolving_edges_carry_zero_weight(generation) -> None:
    for organization in ("ORG2", "ORG3", "ORG4"):
        edge = revolving_edge(generation, organization)
        assert edge["contributions"] == []
        assert edge["contributing_person_count"] == 0
        assert edge["strength_sum"] == 0.0
        assert edge["w_tiered_lower"] == 0.0
        assert edge["surviving_tier_thresholds"] == []


def test_interval_blocked_keeps_null_gap_bounds(generation) -> None:
    blocked = revolving_edge(generation, "ORG4")
    assert blocked["gap_min_days"] is None
    assert blocked["gap_max_days"] is None
    assert blocked["gap_decay_lower"] is None
    assert blocked["gap_decay_upper"] is None


def test_gap_decay_bounds_are_ordered_and_bounded(generation) -> None:
    edge = revolving_edge(generation, "ORG1")
    assert 0.0 < edge["gap_decay_lower"] <= edge["gap_decay_upper"] <= 1.0


def test_registrant_tier_defaults_to_r0_and_is_counted(generation) -> None:
    assert generation["receipt"]["records_read"]["registrant_tier_defaulted_r0"] == 1


# ---------------------------------------------------------------------------
# thresholds, scores, schemas
# ---------------------------------------------------------------------------


def test_tier_threshold_restricts_the_node_universe(generation) -> None:
    universe = generation["receipt"]["node_universe"]
    assert universe["L2"] == {"person": 4, "container": 2, "organization": 4, "total": 10}
    assert universe["L3"] == {"person": 3, "container": 2, "organization": 2, "total": 7}
    assert universe["L4"] == {"person": 1, "container": 2, "organization": 1, "total": 4}


def test_tier_threshold_restricts_edge_weight(generation) -> None:
    by_threshold = {}
    for row in generation["scores"]:
        by_threshold.setdefault(row["tier_threshold"], {})[row["node_id"]] = row
    container = "container:bioguide:A000001"
    # Revolving strength drops to P1's share as the floor rises (only P1
    # survives at L4); membership strength drops the same way, gated by
    # each record's OWN tier against the floor (R4): at L2 every MEMBER_OFFICE
    # occupant's membership edge counts (P1 0.75 [duplicate row deduped, not
    # doubled] + P2 0.50 + P3 0.25 + P6 0.50 = 2.00), at L3 P3's L2 record
    # drops out (P1 0.75 + P2 0.50 + P6 0.50 = 1.75), at L4 only P1's L4
    # record survives (0.75).
    assert by_threshold["L2"][container]["raw_strength"] == pytest.approx(0.875 + 2.00)
    assert by_threshold["L3"][container]["raw_strength"] == pytest.approx(0.75 + 1.75)
    assert by_threshold["L4"][container]["raw_strength"] == pytest.approx(0.75 + 0.75)
    # P1's own MEMBER_OFFICE membership edge keeps it non-isolate at every
    # threshold once the membership layer is fed into the operator (R4),
    # even at L4 where the co-tenure layer alone empties out.
    assert by_threshold["L2"]["person:P1"]["isolate"] is False
    assert by_threshold["L3"]["person:P1"]["isolate"] is False
    assert by_threshold["L4"]["person:P1"]["isolate"] is False
    # P6 has no co-tenure or revolving edge, but its own L3 MEMBER_OFFICE
    # record still produces a membership edge, so P6 is not an isolate at L2.
    assert by_threshold["L2"]["person:P6"]["isolate"] is False


def test_every_threshold_emits_every_alpha(generation) -> None:
    for row in generation["scores"]:
        alphas = [entry["alpha"] for entry in row["connectedness_pagerank_exploratory"]]
        assert alphas == [0.70, 0.85, 0.95]
        for entry in row["connectedness_pagerank_exploratory"]:
            assert 0.0 <= entry["score"] <= 1.0


def test_emitted_rows_validate_against_the_committed_schemas(generation) -> None:
    from fec.staffer_network.schema_validation import validate_instance

    edge_schema = subject.load_schema("exploratory_temporal_edge.schema.json")
    score_schema = subject.load_schema("exploratory_node_score.schema.json")
    receipt_schema = subject.load_schema("exploratory_temporal_receipt.schema.json")
    for row in generation["edges"]:
        validate_instance(row, edge_schema)
    for row in generation["scores"]:
        validate_instance(row, score_schema)
    validate_instance(generation["receipt"], receipt_schema)


def test_receipt_pins_the_exploratory_constants(generation) -> None:
    receipt = generation["receipt"]
    assert receipt["exploratory"] is True
    assert receipt["primary"] is False
    assert receipt["primary_weights_emitted"] == 0
    assert receipt["canonical_employment_promotions"] == 0
    assert receipt["canonical_identity_promotions"] == 0
    assert receipt["promotion_policy"] == "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
    assert receipt["statement"] == (
        "Exploratory diagnostics over strict one-to-one review candidates; "
        "not identity findings; not primary weights; no influence claim."
    )
    assert all(row["exploratory"] is True for row in generation["edges"])
    assert all(row["primary"] is False for row in generation["edges"])
    assert all(row["exploratory"] is True for row in generation["scores"])


def test_receipt_binds_every_input_by_hash(generation) -> None:
    roles = {entry["role"] for entry in generation["receipt"]["inputs"]}
    assert roles == {
        "tiered_person_office_records",
        "tiered_person_summary",
        "filer_asserted_year_episodes",
        "registrant_side_records",
        "tiered_corroboration_receipt",
        "network_math",
        "intervals",
    }
    for entry in generation["receipt"]["inputs"]:
        path = Path(entry["path"])
        assert path.is_file()
        assert sha256_of(path) == entry["sha256"]


def test_sweep_reports_a_rank_correlation_per_threshold(generation) -> None:
    sweep = generation["receipt"]["sweep"]
    assert {row["dial"] for row in sweep} == {"TIER_STRENGTH", "R_STRENGTH"}
    assert {row["factor"] for row in sweep} == {0.5, 1.5}
    assert {row["tier_threshold"] for row in sweep} == {"L2", "L3", "L4"}
    halved = [
        row for row in sweep
        if row["dial"] == "TIER_STRENGTH" and row["factor"] == 0.5
    ]
    # A uniform rescaling of a layer cancels in the row-normalized operator.
    for row in halved:
        assert row["clamped_dial_entries"] == []
        assert row["spearman_pagerank_0_85"] in (None, 1.0)
    raised = [
        row for row in sweep
        if row["dial"] == "TIER_STRENGTH" and row["factor"] == 1.5
    ]
    for row in raised:
        assert row["clamped_dial_entries"] == ["L4", "L5"]
        assert row["scaled_dial"]["L4"] == 1.0
        assert row["scaled_dial"]["L5"] == 1.0


def test_sweep_detects_a_clamp_induced_rank_change(tmp_path) -> None:
    """The +50% arm must be able to move ranks, not just report 1.0.

    A uniform rescaling cancels in the row-normalized operator, so the sweep
    can only bite where the 1.0 clamp breaks proportionality between tiers.
    This mixed-tier hub makes that happen, which proves the sweep is a live
    measurement rather than a constant.
    """

    tiers = {"H": "L4", "A": "L2", "B": "L4", "C": "L2", "D": "L5", "E": "L3"}
    windows = {
        "H": ("2010-01-01", "2020-01-01"),
        "A": ("2011-01-01", "2012-01-01"),
        "B": ("2012-01-01", "2019-01-01"),
        "C": ("2013-01-01", "2013-06-01"),
        "D": ("2014-01-01", "2018-01-01"),
        "E": ("2015-01-01", "2016-01-01"),
    }
    summary = [
        {"lda_source_person_id": name, "max_tier": tier, "registrant_side_tier": None}
        for name, tier in tiers.items()
    ]
    records = [
        _record(name, tiers[name], MEMBER_OFFICE, window, window)
        for name, window in windows.items()
    ]
    sidecar = write_part_a(
        tmp_path / "sidecar", records=records, summary=summary, registrants=[]
    )
    receipt = build(sidecar, tmp_path / "primary")
    raised = {
        (row["tier_threshold"], row["factor"]): row["spearman_pagerank_0_85"]
        for row in receipt["sweep"]
        if row["dial"] == "TIER_STRENGTH"
    }
    assert raised[("L3", 1.5)] is not None
    assert raised[("L3", 1.5)] < 1.0
    # The uniform halving arm cannot move a rank, by construction.
    assert raised[("L2", 0.5)] == 1.0
    assert raised[("L3", 0.5)] == 1.0


# ---------------------------------------------------------------------------
# generation discipline
# ---------------------------------------------------------------------------


def test_twin_is_byte_identical(tmp_path) -> None:
    sidecar = write_part_a(tmp_path / "sidecar")
    primary = tmp_path / "primary"
    twin = tmp_path / "twin"
    build(sidecar, primary)
    build(sidecar, twin)
    for name in (
        subject.EDGES_FILENAME, subject.SCORES_FILENAME, subject.RECEIPT_FILENAME
    ):
        assert sha256_of(primary / name) == sha256_of(twin / name)


def test_non_empty_output_directory_is_refused(tmp_path) -> None:
    sidecar = write_part_a(tmp_path / "sidecar")
    output = tmp_path / "occupied"
    output.mkdir()
    (output / "keepme.txt").write_text("existing generation", encoding="utf-8")
    with pytest.raises(subject.BuildError, match="immutable generation already exists"):
        build(sidecar, output)
    assert (output / "keepme.txt").is_file()


def test_part_a_receipt_must_pass(tmp_path) -> None:
    sidecar = write_part_a(tmp_path / "sidecar")
    receipt_path = sidecar / "tiered_corroboration_receipt.json"
    receipt_path.write_bytes(canonical({"status": "FAIL"}))
    with pytest.raises(subject.BuildError, match="status is not PASS"):
        build(sidecar, tmp_path / "primary")


# ---------------------------------------------------------------------------
# verifier
# ---------------------------------------------------------------------------


def test_verifier_passes_on_an_untouched_generation(generation, tmp_path) -> None:
    document = run_verifier(generation["primary"], tmp_path / "report")
    assert document["failures"] == []
    assert document["status"] == "PASS"
    assert document["checks"]["language_law_hits"] == 0
    assert document["checks"]["co_tenure_edges_re_derived"] == 3
    assert document["checks"]["revolving_edges_re_derived"] == 4


def test_verifier_checks_twin_byte_identity(tmp_path) -> None:
    sidecar = write_part_a(tmp_path / "sidecar")
    primary = tmp_path / "primary"
    twin = tmp_path / "twin"
    build(sidecar, primary)
    build(sidecar, twin)
    good = run_verifier(primary, tmp_path / "report_good", twin=twin)
    assert good["status"] == "PASS"
    assert good["twin_checked"] is True

    broken = tmp_path / "twin_broken"
    clone(twin, broken)
    rows = read_rows(broken / subject.EDGES_FILENAME)
    write_gzip(broken / subject.EDGES_FILENAME, rows[:-1])
    bad = run_verifier(primary, tmp_path / "report_bad", twin=broken)
    assert bad["status"] == "FAIL"
    assert any("twin differs" in item for item in bad["failures"])


def test_exploratory_false_negative_control_fails_the_verifier(
    generation, tmp_path
) -> None:
    broken = clone(generation["primary"], tmp_path / "broken")
    rows = read_rows(broken / subject.EDGES_FILENAME)
    rows[0]["exploratory"] = False
    rewrite_edges(broken, rows)
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("exploratory" in item for item in document["failures"])


def test_promotion_tripwire_fails_the_verifier(generation, tmp_path) -> None:
    broken = clone(generation["primary"], tmp_path / "promoted")
    rows = read_rows(broken / subject.EDGES_FILENAME)
    rows[0]["canonical_employment_promoted"] = True
    rewrite_edges(broken, rows)
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("canonical_employment_promoted" in item for item in document["failures"])


def test_zero_overlap_row_fails_the_verifier(generation, tmp_path) -> None:
    broken = clone(generation["primary"], tmp_path / "zero_overlap")
    rows = read_rows(broken / subject.EDGES_FILENAME)
    for row in rows:
        if row["layer"] == "co_tenure":
            row["status"] = "ZERO_OVERLAP"
            break
    rewrite_edges(broken, rows)
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("ZERO_OVERLAP" in item for item in document["failures"])


def test_tampered_weight_fails_the_verifier(generation, tmp_path) -> None:
    broken = clone(generation["primary"], tmp_path / "tampered")
    rows = read_rows(broken / subject.EDGES_FILENAME)
    for row in rows:
        if row["layer"] == "co_tenure" and row["status"] == "GUARANTEED":
            row["w_tiered_lower"] = row["w_tiered_lower"] * 2.0
            break
    rewrite_edges(broken, rows)
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("w_tiered_lower" in item for item in document["failures"])


def test_language_law_negative_control(generation, tmp_path) -> None:
    broken = clone(generation["primary"], tmp_path / "language")
    receipt_path = broken / subject.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["weight_semantics"] = "this wording would claim causal influence"
    receipt_path.write_bytes(canonical(receipt))
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("language law" in item for item in document["failures"])
    assert document["checks"]["language_law_hits"] >= 2


# ---------------------------------------------------------------------------
# R2: language law value-position exemption (2026-09-02)
# ---------------------------------------------------------------------------


def test_language_law_exempt_field_predicate() -> None:
    """Unit-level check of the exemption predicate itself."""

    assert verifier.is_language_law_exempt_field("office_key") is True
    assert verifier.is_language_law_exempt_field("container_id") is True
    assert verifier.is_language_law_exempt_field("container_ids") is True
    assert verifier.is_language_law_exempt_field("organization_id") is True
    assert verifier.is_language_law_exempt_field("person_id") is True
    assert verifier.is_language_law_exempt_field("lda_source_person_id") is True
    assert verifier.is_language_law_exempt_field("registrant_source_org_id") is True
    assert verifier.is_language_law_exempt_field("edge_id") is True
    assert verifier.is_language_law_exempt_field("support_digest") is True
    assert verifier.is_language_law_exempt_field("some_new_key") is True
    assert verifier.is_language_law_exempt_field("some_new_id") is True
    # Field NAMES and free-text prose are never exempt.
    assert verifier.is_language_law_exempt_field("weight_semantics") is False
    assert verifier.is_language_law_exempt_field("statement") is False
    assert verifier.is_language_law_exempt_field(None) is False


def test_office_key_containing_a_banned_substring_is_exempt(tmp_path) -> None:
    """R2: an office_key/container_id VALUE containing 'ACCESS' (as in
    ACCESSIBILITY) must not trip the language law, since INV-7 exempts
    opaque identifier values, not just field names.
    """

    committee = {
        "chamber": "house",
        "office_key": "OFFICE_OF_ACCESSIBILITY_SERVICES",
        "member_bioguide": None,
        "container_kind": "committee",
    }
    records = [
        _record("P1", "L4", MEMBER_OFFICE, ("2013-01-01", "2014-01-01"),
                ("2012-10-01", "2014-04-01")),
        _record("P2", "L3", MEMBER_OFFICE, ("2013-07-01", "2015-01-01"),
                ("2013-04-01", "2015-04-01")),
        _record("P1", "L4", committee, ("2013-09-01", "2013-12-01"),
                ("2013-09-01", "2013-12-01")),
        _record("P2", "L3", committee, ("2013-09-01", "2013-12-01"),
                ("2013-09-01", "2013-12-01")),
    ]
    sidecar = write_part_a(tmp_path / "sidecar", records=records, registrants=[])
    primary = tmp_path / "primary"
    build(sidecar, primary)
    edges = read_rows(primary / subject.EDGES_FILENAME)
    edge = co_tenure_edge({"edges": edges}, "P1", "P2")
    assert any("ACCESSIBILITY" in container_id for container_id in edge["container_ids"])
    assert any(
        "ACCESSIBILITY" in item["container_id"]
        for item in edge["endpoint_record_tiers"]["subject"]
    )

    document = run_verifier(primary, tmp_path / "report")
    assert document["status"] == "PASS"
    assert document["checks"]["language_law_hits"] == 0
    assert "office_key" in document["language_law_exempt_fields"]
    assert "container_id" in document["language_law_exempt_fields"]
    assert "container_ids" in document["language_law_exempt_fields"]


def test_free_text_field_containing_influence_fails_the_language_law(
    generation, tmp_path
) -> None:
    """R2: a description/prose field is NOT a value position and must still
    be checked -- an 'influence' claim outside the mandated STATEMENT
    sentence fails the verifier.
    """

    broken = clone(generation["primary"], tmp_path / "influence_claim")
    receipt_path = broken / subject.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["sweep_semantics"] = receipt["sweep_semantics"] + " This description implies influence."
    receipt_path.write_bytes(canonical(receipt))
    document = run_verifier(broken, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("language law" in item for item in document["failures"])
    assert document["checks"]["language_law_hits"] >= 1


# ---------------------------------------------------------------------------
# R3: co-tenure tier_strength traces the supporting record, not max_tier
# ---------------------------------------------------------------------------


def test_co_tenure_tier_strength_uses_the_contributing_container_record_tier(
    tmp_path,
) -> None:
    container_x = {
        "chamber": "house", "office_key": "OFFICE_X",
        "member_bioguide": "X00001", "container_kind": "member_office",
    }
    container_y = {
        "chamber": "house", "office_key": "OFFICE_Y",
        "member_bioguide": "Y00001", "container_kind": "member_office",
    }
    summary = [
        {"lda_source_person_id": "PX", "max_tier": "L4", "registrant_side_tier": None},
        {"lda_source_person_id": "PY", "max_tier": "L3", "registrant_side_tier": None},
    ]
    window = ("2015-01-01", "2016-01-01")
    container_y_id = "container:bioguide:Y00001"

    # Below-floor variant: PX's Y record is L1, so it never enters the
    # sidecar universe at all (the record floor) and the Y overlap with PY
    # cannot exist -- confirming the base case the ruling names.
    below_floor_records = [
        _record("PX", "L4", container_x, window, window),
        _record("PX", "L1", container_y, window, window),
        _record("PY", "L3", container_y, window, window),
    ]
    sidecar_below = write_part_a(
        tmp_path / "sidecar_below", records=below_floor_records,
        summary=summary, registrants=[],
    )
    primary_below = tmp_path / "primary_below"
    build(sidecar_below, primary_below)
    edges_below = read_rows(primary_below / subject.EDGES_FILENAME)
    assert not any(
        row["layer"] == "co_tenure"
        and {row["subject_id"], row["object_id"]} == {"person:PX", "person:PY"}
        for row in edges_below
    )

    # Elevated variant: PX's Y record is L2 (clears the record floor). The
    # edge must be strength min(L2, PY's L3) -- the RECORD tier that
    # supports the Y overlap -- not min(PX's max_tier L4, PY's L3).
    elevated_records = [
        _record("PX", "L4", container_x, window, window),
        _record("PX", "L2", container_y, window, window),
        _record("PY", "L3", container_y, window, window),
    ]
    sidecar_elevated = write_part_a(
        tmp_path / "sidecar_elevated", records=elevated_records,
        summary=summary, registrants=[],
    )
    primary_elevated = tmp_path / "primary_elevated"
    build(sidecar_elevated, primary_elevated)
    edges_elevated = read_rows(primary_elevated / subject.EDGES_FILENAME)
    edge = next(
        row for row in edges_elevated
        if row["layer"] == "co_tenure"
        and {row["subject_id"], row["object_id"]} == {"person:PX", "person:PY"}
    )
    assert edge["subject_id"] == "person:PX"
    assert edge["object_id"] == "person:PY"
    assert edge["endpoint_max_tiers"] == {"subject": "L4", "object": "L3"}
    assert edge["endpoint_record_tiers"]["subject"] == [
        {"container_id": container_y_id, "tier": "L2"}
    ]
    assert edge["endpoint_record_tiers"]["object"] == [
        {"container_id": container_y_id, "tier": "L3"}
    ]
    # min(TIER_STRENGTH[L2], TIER_STRENGTH[L3]) = min(0.25, 0.50), NOT
    # min(TIER_STRENGTH[L4], TIER_STRENGTH[L3]) = 0.50.
    assert edge["tier_strength"] == pytest.approx(0.25)
    assert edge["w_tiered_lower"] == pytest.approx(0.25 * edge["w_lower"])

    document = run_verifier(primary_elevated, tmp_path / "report_elevated")
    assert document["status"] == "PASS"


def test_input_rebinding_detects_a_changed_input(generation, tmp_path) -> None:
    moved = clone(generation["primary"], tmp_path / "rebound")
    sidecar_copy = write_part_a(tmp_path / "sidecar_copy")
    receipt_path = moved / subject.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    for entry in receipt["inputs"]:
        if entry["role"] == "tiered_person_summary":
            entry["path"] = (
                sidecar_copy / "tiered_person_summary_25340.ndjson.gz"
            ).as_posix()
            entry["sha256"] = "0" * 64
    receipt_path.write_bytes(canonical(receipt))
    document = run_verifier(moved, tmp_path / "report")
    assert document["status"] == "FAIL"
    assert any("hash changed" in item for item in document["failures"])


def test_verifier_report_is_written_and_is_immutable(generation, tmp_path) -> None:
    report_root = tmp_path / "report"
    document = run_verifier(generation["primary"], report_root)
    path = verifier.write_report(document, report_root)
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["exploratory"] is True
    assert payload["primary_weights_emitted"] == 0
    with pytest.raises(SystemExit):
        verifier.write_report(document, report_root)
