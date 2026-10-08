"""Negative controls for title candidates and one-to-many ID migration."""
from copy import deepcopy

import pytest

import rebuild_spine_identity as release
from rebuild_spine_identity import migration_map, senate_signatures, sha, verify_bindings


def source(ident, period="2021-04-01", title="POLICY ADVISOR FROM MAR. 24"):
    return {"candidate_id": ident, "report_period_start": period, "title_raw": title,
            "payee_name_raw": "DOE, JANE", "page_number": 1}


OWNERS = {"a": ("p1", "doe|jane|", "office1"), "b": ("p2", "doe|jane|", "office2")}


def test_exact_title_same_period_produces_review_not_identity():
    result = senate_signatures([source("a"), source("b")], OWNERS)
    assert len(result) == 1
    assert result[0]["spine_person_ids"] == ["p1", "p2"]
    assert result[0]["identity_merge_authorized"] is False
    assert result[0]["canonical_eligible"] is False
    assert {r["source_row_id"] for r in result[0]["evidence"]} == {"a", "b"}


@pytest.mark.parametrize("right", [
    source("b", period="2021-10-01"),
    source("b", title="POLICY ADVISOR FROM MAR. 25"),
    source("b", title="POLICY ADVISOR"),
    source("unknown"),
])
def test_no_span_wide_title_cartesian_product(right):
    assert senate_signatures([source("a"), right], OWNERS) == []


def test_one_office_is_not_a_cross_office_candidate():
    owners = {"a": ("p1", "doe|jane|", "office1"), "b": ("p2", "doe|jane|", "office1")}
    assert senate_signatures([source("a"), source("b")], owners) == []


def test_split_map_never_picks_an_arbitrary_target():
    old = {"old": {"legacy_person_ids": ["a", "b"]}}
    new = {p: {"spine_person_id": p, "legacy_person_ids": [legacy]}
           for p, legacy in [("p1", "a"), ("p2", "b")]}
    result = migration_map(old, new)
    assert result[0]["target_person_ids"] == ["p1", "p2"]
    assert result[0]["relation"] == "SPLIT_REQUIRES_SOURCE_ROW"
    broken = deepcopy(new)
    broken["p2"]["legacy_person_ids"] = ["a"]
    with pytest.raises(ValueError, match="Repeated"):
        migration_map(old, broken)
    with pytest.raises(ValueError, match="same unique"):
        migration_map(old, {"p1": new["p1"]})


def test_stale_verification_cannot_release_changed_payload(tmp_path):
    path = tmp_path / "payload"
    path.write_text("verified")
    bindings = {str(path): sha(path)}
    verify_bindings(bindings)
    path.write_text("changed after verification")
    with pytest.raises(ValueError, match="Verified artifact changed"):
        verify_bindings(bindings)


def test_native_bridge_remap_preserves_premerge_identity_and_holds_missing_ids(tmp_path, monkeypatch):
    v6 = tmp_path / "native_v6"
    v6.mkdir()
    monkeypatch.setattr(release, "HERE", tmp_path)
    monkeypatch.setattr(release, "REVIEW", tmp_path / "review")
    monkeypatch.setattr(release, "V6", v6)
    source = v6 / "hill_person_spine.ndjson.gz"
    source.write_bytes(b"native spine fixture")
    a, b = "hill:person:" + "a" * 64, "hill:person:" + "b" * 64
    payload = tmp_path / "politico.ndjson.gz"
    release.write_rows(payload, [{"spine_person_id": a}, {"spine_person_id": b}])
    bridge = tmp_path / "bridge.json"
    release.write_json(bridge, {"status": "PASS", "failures": [],
                                "inputs": {str(source): {"sha256": sha(source)}}})
    graph = tmp_path / "staffer_social_network_20260907_v6_primary" / "staffer_social_network_receipt.json"
    release.write_json(graph, {"inputs": [
        {"role": "politico_direct_link_receipt", "path": str(bridge), "sha256": sha(bridge)},
        {"role": "politico_direct_policy_memberships", "path": str(payload), "sha256": sha(payload)},
    ]})
    new = {p: {"spine_person_id": p, "legacy_person_ids": [legacy]}
           for p, legacy in [("p1", a), ("p2", b)]}
    map_path, _, proof = release.legacy_bridge_handoff(new)
    assert proof["status"] == "PASS"
    assert proof["referenced_native_person_ids"] == 2
    assert {r["legacy_person_id"]: r["person_id"] for r in release.rows(map_path)} == {a: "p1", b: "p2"}
    _, _, proof = release.legacy_bridge_handoff({"p1": new["p1"]})
    assert proof["status"] == "HOLD"
    assert proof["missing_native_person_ids"] == [b]
    payload.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="input changed"):
        release.legacy_bridge_handoff(new)


def test_quoted_office_names_are_not_authored_claims():
    hits, _ = release.verifier.language_law_scan(
        {"first_office_key": "OFFICE OF CONGRESSIONAL ACCESSIBILITY SERVICES"},
        release.verifier.NAME_STANDARD_VERBATIM_LEAF_NAMES)
    assert hits == []
    hits, _ = release.verifier.language_law_scan(
        {"explanation": "This proves access"},
        release.verifier.NAME_STANDARD_VERBATIM_LEAF_NAMES)
    assert hits


def test_replicas_have_distinct_directories_and_identical_batch_metadata(tmp_path, monkeypatch):
    import build_hill_personnel_spine as builder
    delta = tmp_path / "delta.json"
    release.write_json(delta, {"name_standard_sha256": sha(release.ns.__file__)})
    monkeypatch.setattr(release, "DELTA", delta)
    captured = []
    monkeypatch.setattr(builder, "main", lambda argv: captured.append(argv) or 0)
    labels = ["house_personnel_observations", "roster:legislators-current.yaml",
              "part_a_v2:tiered_person_summary_25340.ndjson.gz", "nickname_table", "h1_matches",
              "h2_matches", "senate_matches", "staff_directory", "congestion", "registrant_episodes"]
    bindings = {label: {"path": str(tmp_path / "input")} for label in labels}
    release.build(bindings, "primary")
    release.build(bindings, "twin")
    def argument(argv, flag):
        return argv[argv.index(flag) + 1]
    assert argument(captured[0], "--run-id") == argument(captured[1], "--run-id")
    assert argument(captured[0], "--output-root") != argument(captured[1], "--output-root")
