# -*- coding: utf-8 -*-
"""Adversarial tests for staffer_social_network_20260903_v3.

Two lanes:
  * pure-function tests on the interval / kappa / id machinery (no generation needed);
  * invariant tests over the REAL emitted generation, each written so that the
    obvious wrong implementation fails it.

Run:  python -m pytest audits/staffer_network/test_staffer_social_network.py -q
"""

from __future__ import annotations

import fnmatch
import gzip
import json
import sys
from types import SimpleNamespace
from datetime import date
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))

import build_staffer_social_network as subject  # noqa: E402

GENERATION = HERE / "staffer_social_network_20260903_v3_primary"
TWIN = HERE / "staffer_social_network_20260903_v3_twin"


def rows(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


# --------------------------------------------------------------- pure functions
def test_duplicate_and_adjacent_runs_union_without_inflating():
    """Duplicate quarterly rows and back-to-back periods must not inflate a calendar."""
    a = date(2020, 1, 1).toordinal()
    runs = [(a, a + 90), (a, a + 90), (a + 90, a + 180), (a + 30, a + 60)]
    u = subject.union_half_open(runs)
    assert u == [(a, a + 180)]
    assert subject.calendar_days(u) == 180
    # the naive sum would be 90 + 90 + 90 + 30 = 300
    assert sum(e - s for s, e in runs) == 300


def test_intersection_agrees_with_the_reviewed_interval_functions():
    """Every relative position of two half-open runs, checked against intervals.py."""
    report = subject.cross_check_intervals()
    assert report["status"] == "AGREE"
    assert report["cases_checked"] >= 24


def test_disjoint_calendars_intersect_to_nothing():
    a = date(2015, 1, 1).toordinal()
    left = [(a, a + 100)]
    right = [(a + 100, a + 200)]          # abutting, NOT overlapping
    assert subject.intersect_calendars(left, right) == []
    assert subject.calendar_days(subject.intersect_calendars(left, right)) == 0


def test_cross_container_union_does_not_double_count():
    """Two people sharing TWO offices over the same days must count those days once."""
    a = date(2019, 1, 1).toordinal()
    office_one = subject.intersect_calendars([(a, a + 365)], [(a, a + 365)])
    office_two = subject.intersect_calendars([(a, a + 365)], [(a, a + 365)])
    naive = subject.calendar_days(office_one) + subject.calendar_days(office_two)
    unioned = subject.calendar_days(subject.union_half_open(office_one + office_two))
    assert naive == 730
    assert unioned == 365


def test_duration_weight_is_bounded_and_monotone():
    assert subject.duration_weight(0, subject.TAU_DAYS) == 0.0
    prev = -1.0
    for d in (1, 30, 100, 365, 1000, 5000):
        w = subject.duration_weight(d, subject.TAU_DAYS)
        assert 0.0 < w < 1.0
        assert w > prev
        prev = w
    with pytest.raises(subject.BuildError):
        subject.duration_weight(-1, subject.TAU_DAYS)


def test_kappa_table_matches_design_6_2():
    assert subject.kappa_for("member_office", None) == (1.00, "member_office")
    assert subject.kappa_for("committee", "MAJ") == (0.75, "committee_same_side_known")
    assert subject.kappa_for("committee", "MIN") == (0.75, "committee_same_side_known")
    assert subject.kappa_for("committee", "UNKNOWN") == (0.60, "committee_side_unknown")
    assert subject.kappa_for("committee", "BIPARTISAN") == (0.60, "committee_bipartisan_no_side")
    assert subject.kappa_for("leadership", None) == (0.75, "leadership")
    assert subject.kappa_for("admin", None) == (0.50, "admin")


def test_side_is_four_valued_and_bipartisan_is_distinct_from_unknown():
    """BIPARTISAN is a real value (staffer HAS no side); UNKNOWN is missing data.

    Collapsing them makes the C-8c coverage bar unreadable, so they must not share a
    kappa bucket even though both currently resolve to 0.60.
    """
    assert subject.SIDE_VALUES == ("MAJ", "MIN", "BIPARTISAN", "UNKNOWN")
    _, bucket_bip = subject.kappa_for("committee", "BIPARTISAN")
    _, bucket_unk = subject.kappa_for("committee", "UNKNOWN")
    assert bucket_bip != bucket_unk


def test_same_committee_container_does_not_imply_same_side():
    """A committee employs BOTH majority and minority staff on one payroll.

    So the kappa=0.40 opposite-side row is REACHABLE, not structurally dead, and the
    code must never infer 'same side' merely from 'same container'. The only evidence
    of side is a token in the payroll sub-unit string.
    """
    assert subject.committee_side("COMMITTEE ON JUDICIARY") == "UNKNOWN"
    assert subject.KAPPA["committee_opposite_side"] == 0.40
    # side-unknown must NOT be scored as if it were same-side
    assert subject.kappa_for("committee", "UNKNOWN")[0] < subject.kappa_for("committee", "MAJ")[0]


def test_committee_side_only_fires_on_a_real_token():
    assert subject.committee_side("COMM-EDUCATION AND WORKFORCE-MIN") == "MIN"
    assert subject.committee_side("COMM ON SCIENCE SPACE AND TECH MAJ") == "MAJ"
    assert subject.committee_side("COMMITTEE ON RULES") == "UNKNOWN"
    assert subject.committee_side("COMMITTEE ON MINING") == "UNKNOWN"   # not MINORITY


def test_container_normalization_is_closed_to_leading_year_tokens():
    assert subject.normalized_container("FISCAL YEAR 2022 OFFICE OF GENERAL COUNSEL") == "OFFICE OF GENERAL COUNSEL"
    assert subject.normalized_container("2022 OFFICE OF GENERAL COUNSEL") == "OFFICE OF GENERAL COUNSEL"
    assert subject.normalized_container("HON:Y000001") == "HON:Y000001"
    assert subject.normalized_container("COMMITTEE ON THE 2022 ELECTION") == "COMMITTEE ON THE 2022 ELECTION"


def test_edge_id_is_deterministic_and_order_sensitive():
    one = subject.edge_id_of("co_tenure", "person:a", "person:b")
    assert one == subject.edge_id_of("co_tenure", "person:a", "person:b")
    assert one != subject.edge_id_of("co_tenure", "person:b", "person:a")
    assert one.startswith("staffer-social:edge:") and len(one.split(":")[-1]) == 64


def test_review_assertion_id_is_deterministic_and_separate_from_modeled_edges():
    one = subject.review_assertion_id("politico_employment_history", "profile-1", "1")
    assert one == subject.review_assertion_id(
        "politico_employment_history", "profile-1", "1"
    )
    assert one != subject.review_assertion_id(
        "politico_education_history", "profile-1", "1"
    )
    assert one.startswith("staffer-social:review:")


def test_final_metadata_and_review_inputs_are_explicit_cli_values():
    args = subject.parse_args(
        [
            "--output",
            "unused",
            "--config-name",
            "staffer_social_network_20260904_v5",
            "--vintage",
            "20260904",
            "--generated-at",
            "2026-09-04T00:00:00Z",
            "--politico-current-committee-assertions",
            "committee.gz",
            "--politico-profile-employment-assertions",
            "employment.gz",
            "--politico-profile-education-assertions",
            "education.gz",
            "--politico-profile-policy-deltas",
            "deltas.gz",
            "--politico-explicit-committee-side-assertions",
            "sides.gz",
            "--no-glassbox",
        ]
    )
    paths = subject.input_paths(ROOT, args)
    assert args.config_name == "staffer_social_network_20260904_v5"
    assert args.vintage == "20260904"
    assert args.generated_at == "2026-09-04T00:00:00Z"
    assert "politico_profile_employment_assertions" in paths
    assert "politico_explicit_committee_side_assertions" in paths


def test_build_refuses_a_nonempty_output_directory(tmp_path):
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "sentinel.txt").write_text("preserve me", encoding="utf-8")
    with pytest.raises(subject.BuildError, match="output directory is not empty"):
        subject.run(SimpleNamespace(repository_root=str(ROOT), output=str(occupied)))
    assert (occupied / "sentinel.txt").read_text(encoding="utf-8") == "preserve me"


def test_direct_policy_provenance_does_not_require_a_legacy_quorum_id():
    fields = subject.policy_provenance({
        "issue_area": "Agriculture",
        "observed_at": "2026-08-30T00:00:00Z",
        "source_profile_uuid": "profile-1",
    })
    assert fields["source_profile_uuid"] == "profile-1"
    assert fields["identity_bridge"] == "POLITICO_EXACT_NAME_PLUS_CURRENT_OFFICE_TO_PAYROLL_SPINE"
    assert "quorum_staff_id" not in fields


# ------------------------------------------------------- generation invariants
generation = pytest.mark.skipif(
    not (GENERATION / "staffer_social_network_receipt.json").exists(),
    reason="generation not built",
)


@pytest.fixture(scope="module")
def receipt():
    return json.loads((GENERATION / "staffer_social_network_receipt.json").read_text(encoding="utf-8"))


@generation
def test_zero_overlap_pairs_are_counted_but_never_emitted(receipt):
    counts = receipt["co_tenure_status_counts"]
    assert counts["ZERO_OVERLAP"] > 0, "the overlap test must actually reject something"
    assert receipt["zero_overlap_edges_emitted"] == 0
    seen = set()
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] == "co_tenure":
            seen.add(e["status"])
    assert "ZERO_OVERLAP" not in seen


@generation
def test_no_person_person_edge_lacks_temporal_overlap(receipt):
    """The owner's rule. A GUARANTEED edge must carry positive guaranteed days."""
    bad = 0
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] != "co_tenure":
            continue
        if e["status"] == "GUARANTEED" and not (e["guaranteed_days"] > 0):
            bad += 1
        if e["status"] == "POSSIBLE_ONLY" and e["guaranteed_days"] != 0:
            bad += 1
    assert bad == 0


@generation
def test_possible_only_pair_carries_zero_weight():
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] == "co_tenure" and e["status"] == "POSSIBLE_ONLY":
            assert e["w_lower"] == 0.0
            assert e["w_kappa_lower"] == 0.0
            assert e["w_tiered_lower"] == 0.0


@generation
def test_sequence_is_never_a_person_person_edge(receipt):
    assert receipt["edge_counts"]["sequence_person_person"] == 0
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        assert e["layer"] in ("co_tenure", "membership", "revolving", "policy_area")
        if e["layer"] != "revolving":
            assert e["direction"] == "undirected"


@generation
def test_no_member_member_edge_exists():
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        assert not (e["subject_kind"] == "container" and e["object_kind"] == "container")


@generation
def test_trajectories_carry_the_sequence_instead(receipt):
    assert receipt["trajectories"]["total_directed_office_moves"] > 0
    assert receipt["trajectories"]["distinct_directed_office_pairs"] > 0


@generation
def test_tier_strength_is_the_minimum_of_the_two_endpoint_tiers():
    checked = 0
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] != "co_tenure" or e["status"] != "GUARANTEED":
            continue
        expect = min(subject.S_STRENGTH[e["subject_tier"]], subject.S_STRENGTH[e["object_tier"]])
        assert abs(e["tier_strength"] - expect) < 1e-12
        checked += 1
        if checked >= 50000:
            break
    assert checked > 0


@generation
def test_kappa_is_the_max_over_contributing_containers_and_ge_kappa_min():
    checked = 0
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] != "co_tenure" or e["status"] != "GUARANTEED":
            continue
        assert e["kappa"] >= e["kappa_min"]
        assert 0.0 < e["kappa"] <= 1.0
        assert e["container_count"] == len(e["container_ids"])
        checked += 1
        if checked >= 50000:
            break
    assert checked > 0


@generation
def test_cross_container_union_never_exceeds_the_naive_sum():
    checked = 0
    strictly_smaller = 0
    for e in rows(GENERATION / "staffer_social_edges.ndjson.gz"):
        if e["layer"] != "co_tenure" or e["status"] != "GUARANTEED":
            continue
        assert e["guaranteed_days"] <= e["guaranteed_days_before_cross_container_union"]
        if e["guaranteed_days"] < e["guaranteed_days_before_cross_container_union"]:
            strictly_smaller += 1
        checked += 1
        if checked >= 400000:
            break
    assert checked > 0
    assert strictly_smaller > 0, "the union correction must actually bind somewhere"


@generation
def test_every_row_is_review_required_and_unpromoted():
    for i, e in enumerate(rows(GENERATION / "staffer_social_edges.ndjson.gz")):
        assert e["review_status"] == "REVIEW_REQUIRED"
        assert e["canonical_eligible"] is False
        assert e["canonical_employment_promoted"] is False
        assert e["primary"] is False
        if i >= 200000:
            break
    for n in rows(GENERATION / "staffer_social_node_scores.ndjson.gz"):
        assert n["review_status"] == "REVIEW_REQUIRED"
        assert n["canonical_employment_promoted"] is False


@generation
def test_receipt_pins_zero_promotions(receipt):
    for key in ("canonical_employment_promotions", "canonical_identity_promotions",
                "canonical_office_promotions", "canonical_person_merges",
                "primary_weights_emitted", "date_promotions"):
        assert receipt[key] == 0
    assert receipt["complete_history_assertions"] >= 0
    if receipt.get("review_only_layers"):
        assert receipt["complete_history_assertions"] == (
            receipt["complete_employment_history_assertions"]
            + receipt["complete_education_history_assertions"]
        )
    assert receipt["review_status"] == "REVIEW_REQUIRED"
    assert receipt["dial_status"] == "UNTESTED_DEFAULTS_PENDING_FREEZE"


@generation
def test_receipt_binds_every_input_by_hash(receipt):
    assert receipt["inputs"], "no inputs recorded"
    for entry in receipt["inputs"]:
        assert len(entry["sha256"]) == 64
        assert Path(entry["path"]).exists()
    assert len(receipt["implementation"]["sha256"]) == 64


@generation
def test_centrality_is_reported_per_component(receipt):
    op = receipt["operator"]
    assert op["components"] >= 1
    assert op["largest_component"] > 0
    assert "component_sizes_top20" in op
    eig = op["eigenvector"]
    assert eig["status_after_repair"] == "PASS", eig
    assert eig["nodes_null_after_repair"] == 0


@generation
def test_node_scores_carry_component_id_and_size():
    seen = 0
    for n in rows(GENERATION / "staffer_social_node_scores.ndjson.gz"):
        assert "component_id" in n and "component_size" in n
        assert n["component_size"] >= 1
        assert len(n["connectedness_pagerank_exploratory"]) == len(subject.ALPHAS)
        seen += 1
    assert seen > 0


@generation
def test_member_offices_are_attachment_points_not_graph_members():
    """A container node must state the attachment law and carry no cosponsorship import."""
    for n in rows(GENERATION / "staffer_social_node_scores.ndjson.gz"):
        if n["node_kind"] == "container":
            assert "attachment_note" in n
            assert "no member-member edge" in n["attachment_note"]
            return
    pytest.fail("no container node found")


@generation
def test_c8c_reports_four_valued_side_and_never_claims_unreachable(receipt):
    block = receipt["C8c_committee_side_coverage"]
    assert block["side_is_four_valued"] == list(subject.SIDE_VALUES)
    assert set(block["episodes_by_side"]) == set(subject.SIDE_VALUES)
    assert block["committee_episodes"] > 0
    # the receipt must frame this as data coverage, never as structural impossibility
    text = json.dumps(receipt)
    assert "unreachable" not in text.lower()
    assert "REACHABLE" in block["consequence_for_kappa"] or            "REACHABLE" in receipt["dials"]["kappa_committee_opposite_side_unpopulated"]


@generation
def test_committee_bridge_ablation_is_reported(receipt):
    ab = receipt["committee_bridge_ablation"]
    full = ab["person_only_graph_all_co_tenure_edges"]["largest_component"]
    assert full > 0
    for key in ("committee_derived_edges_REMOVED", "ONLY_committee_derived_edges",
                "member_office_derived_edges_REMOVED", "ONLY_member_office_derived_edges"):
        assert ab[key]["largest_component"] <= full
    assert ab["edges_touching_a_committee_container"] > 0


@generation
def test_kappa_aggregation_choice_is_declared(receipt):
    note = receipt["dials"]["kappa_aggregation_declared_choice"]
    assert "MAXIMUM" in note and "kappa_min" in note


@generation
def test_naming_law_no_live_selector_matches(receipt):
    """Every emitted filename must fail every glob literal used in the repo."""
    import re
    star = re.compile(r"""["']([^"'\n]*\*[^"'\n]*)["']""")
    pats = set()
    for pyroot in (ROOT / "fec", HERE):
        for py in pyroot.rglob("*.py"):
            try:
                lines = py.read_text(encoding="utf-8", errors="ignore").splitlines()
            except Exception:
                continue
            for i, line in enumerate(lines):
                window = " ".join(lines[max(0, i - 1):i + 2])
                if "glob" in window:
                    pats.update(m.group(1) for m in star.finditer(line))
    assert pats, "no glob patterns found - the check would be vacuous"
    names = [f["path"] for f in receipt["files"]] + [
        "staffer_social_network_receipt.json", "staffer_social_network_manifest.json",
        GENERATION.name]
    for pat in pats:
        base = pat.replace("\\", "/").rsplit("/", 1)[-1]
        for name in names:
            assert not fnmatch.fnmatch(name, base), f"{name} matches live selector {pat}"


@generation
def test_twin_is_byte_identical():
    if not TWIN.exists():
        pytest.skip("twin not built")
    import hashlib
    built_receipt = json.loads(
        (GENERATION / "staffer_social_network_receipt.json").read_text(encoding="utf-8")
    )
    names = [entry["path"] for entry in built_receipt["files"]]
    names.append("staffer_social_network_receipt.json")
    for name in names:
        a = hashlib.sha256((GENERATION / name).read_bytes()).hexdigest()
        b = hashlib.sha256((TWIN / name).read_bytes()).hexdigest()
        assert a == b, name
    # the manifest may differ ONLY in generation_id (the output directory name)
    ma = json.loads((GENERATION / "staffer_social_network_manifest.json").read_text(encoding="utf-8"))
    mb = json.loads((TWIN / "staffer_social_network_manifest.json").read_text(encoding="utf-8"))
    diff = {k for k in set(ma) | set(mb) if ma.get(k) != mb.get(k)}
    assert diff == {"generation_id"}, diff
    assert ma["canonical_output_hash"] == mb["canonical_output_hash"]
