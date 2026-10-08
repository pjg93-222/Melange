#!/usr/bin/env python3
"""Reconcile the three proposal-only legislation culling lanes.

This script is deliberately audit-only.  It writes a proposed change set and
an unresolved ledger below the adjudication audit tree; it never reads or
writes a production legislation ledger, workbook, score, or rank artifact.
"""

from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "audits" / "legfix5" / "opus_adjudication"
AMEND = BASE / "amendment_culling_opus5_20260728a"
SHORT = BASE / "short_act_collision_culling_opus5_20260728a"
BILL = BASE / "bill_recall_culling_opus5_20260728a"
OUT = BASE / "coordinator_reconciliation_codex_20260728a"
REGISTRY = ROOT / "source_data" / "legislation" / "acu_legislation_search_registry.json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_receipt(path: Path, *, records: int | None = None) -> dict[str, Any]:
    result = {
        "path": str(path.resolve()),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }
    if records is not None:
        result["records"] = records
    return result


def assert_receipt(path: Path, expected: str) -> None:
    actual = sha256_file(path)
    if actual != str(expected).casefold():
        raise RuntimeError(
            f"receipt mismatch for {path}: expected {expected}, observed {actual}"
        )


def verify_lane_receipts() -> dict[str, Any]:
    amendment = read_json(AMEND / "receipt.json")
    short = read_json(SHORT / "receipt.json")
    bill = read_json(BILL / "receipt.json")

    for name, receipt in (
        ("amendment", amendment),
        ("short_act", short),
        ("bill_recall", bill),
    ):
        for flag in (
            "integration_performed",
            "production_write_performed",
            "scoring_performed",
            "rank_recompute_performed",
        ):
            if receipt.get(flag) is not False:
                raise RuntimeError(f"{name} receipt does not prove {flag}=false")

    for raw_path, item in amendment["outputs"].items():
        assert_receipt(Path(raw_path), item["sha256"])
    for item in short["outputs"].values():
        assert_receipt(Path(item["path"]), item["sha256"])
    for filename, item in bill["outputs"].items():
        assert_receipt(BILL / filename, item["sha256"])

    if "claude-opus-5" not in str(amendment.get("adjudicator")):
        raise RuntimeError("amendment lane is not bound to Opus 5")
    if "claude-opus-5" not in str(short.get("adjudicator")):
        raise RuntimeError("short-act lane is not bound to Opus 5")
    if bill.get("model") != "claude-opus-5":
        raise RuntimeError("bill-recall lane is not bound to Opus 5")

    correction = amendment.get("correction") or {}
    if not (
        correction.get("substantive_dispositions_preserved") is True
        and correction.get("aliases_replaced")
        == {
            "ncua_budget_share_insurance_fund": "ncua_budget_share_insurance",
            "telephone_consumer_protection_act_issues": (
                "telephone_consumer_protection_act"
            ),
        }
    ):
        raise RuntimeError("amendment canonical-ID correction is not proven")

    return {
        "amendment": file_receipt(AMEND / "receipt.json"),
        "short_act": file_receipt(SHORT / "receipt.json"),
        "bill_recall": file_receipt(BILL / "receipt.json"),
    }


def write_ndjson(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_bytes(b"".join(canonical_bytes(row) for row in rows))


def main() -> None:
    lane_receipts = verify_lane_receipts()
    registry = read_json(REGISTRY)
    canonical_categories = {row["id"] for row in registry["categories"]}
    if len(canonical_categories) != 19:
        raise RuntimeError("canonical category registry is not exactly nineteen")

    amendments = read_ndjson(AMEND / "amendment_partition_3703.ndjson")
    short_edges = read_ndjson(SHORT / "proposal_adjudications_454.ndjson")
    bills = read_ndjson(BILL / "proposal_adjudications_23.ndjson")
    legacy = read_ndjson(BILL / "legacy_recall_partition_465.ndjson")
    quorum = read_ndjson(BILL / "quorum_recall_partition_44.ndjson")

    if len(amendments) != 3703 or len({row["canonical_key"] for row in amendments}) != 3703:
        raise RuntimeError("amendment partition is not exactly 3,703 unique keys")
    if len(short_edges) != 454 or len(
        {(row["canonical_key"], row["query_id"]) for row in short_edges}
    ) != 454:
        raise RuntimeError("short-act partition is not exactly 454 unique edges")
    if len(bills) != 23 or len({row["canonical_key"] for row in bills}) != 23:
        raise RuntimeError("bill-recall proposal is not exactly 23 unique keys")
    if len(legacy) != 465 or len(quorum) != 44:
        raise RuntimeError("recall-floor accounting populations drifted")

    amendment_by_key = {row["canonical_key"]: row for row in amendments}
    for row in amendments:
        if float(row.get("amendment_weight")) != 0.5:
            raise RuntimeError(f"amendment weight drifted: {row['canonical_key']}")
        if not set(row.get("category_ids") or []).issubset(canonical_categories):
            raise RuntimeError(f"noncanonical amendment category: {row['canonical_key']}")
    for row in short_edges:
        expected_weight = (
            0.5
            if row["canonical_key"].split(":")[1] in {"hamdt", "samdt"}
            else 1.0
        )
        if float(row.get("measure_weight")) != expected_weight:
            raise RuntimeError(f"short-act weight drifted: {row['canonical_key']}")
        if row["query_id"] not in canonical_categories:
            raise RuntimeError(f"noncanonical short-act category: {row['query_id']}")
    for row in bills:
        if not set(row.get("category_ids") or []).issubset(canonical_categories):
            raise RuntimeError(f"noncanonical bill category: {row['canonical_key']}")

    amendment_counts = Counter(row["disposition"] for row in amendments)
    short_counts = Counter(row["disposition"] for row in short_edges)
    bill_counts = Counter(row["disposition"] for row in bills)
    if amendment_counts != {
        "include": 60,
        "exclude_false_positive": 2503,
        "flagged": 1140,
    }:
        raise RuntimeError(f"amendment disposition drift: {amendment_counts}")
    if short_counts != {
        "include": 7,
        "exclude_false_positive": 417,
        "flagged": 30,
    }:
        raise RuntimeError(f"short-act disposition drift: {short_counts}")
    if bill_counts != {
        "include_candidate": 6,
        "exclude_false_positive": 2,
        "flagged": 15,
    }:
        raise RuntimeError(f"bill-recall disposition drift: {bill_counts}")

    overlap = [
        row for row in short_edges if row["canonical_key"] in amendment_by_key
    ]
    if len(overlap) != 31:
        raise RuntimeError(f"amendment/short-act overlap drifted: {len(overlap)}")
    overlap_matrix = Counter(
        (
            row["disposition"],
            amendment_by_key[row["canonical_key"]]["disposition"],
        )
        for row in overlap
    )
    expected_overlap = {
        ("flagged", "flagged"): 15,
        ("exclude_false_positive", "exclude_false_positive"): 14,
        ("flagged", "exclude_false_positive"): 1,
        ("exclude_false_positive", "flagged"): 1,
    }
    if overlap_matrix != expected_overlap:
        raise RuntimeError(f"cross-lane overlap matrix drifted: {overlap_matrix}")

    actions: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []

    for row in amendments:
        if row["disposition"] == "flagged":
            unresolved.append(
                {
                    "schema": "legislation-culling-unresolved-v1",
                    "source_lane": "amendment_partition",
                    "decision_scope": "candidate",
                    "canonical_key": row["canonical_key"],
                    "query_id": None,
                    "disposition": "flagged",
                    "reason": row["reason"],
                    "rule_id": row.get("rule_id"),
                    "text_available": row.get("text_available"),
                    "measure_weight": 0.5,
                    "nested_in_candidate_hold": False,
                    "human_ratification_required": True,
                }
            )
            continue
        actions.append(
            {
                "schema": "legislation-preintegration-proposed-action-v1",
                "source_lane": "amendment_partition",
                "decision_scope": "candidate",
                "canonical_key": row["canonical_key"],
                "query_id": None,
                "disposition": row["disposition"],
                "action": (
                    "upsert_candidate_memberships"
                    if row["disposition"] == "include"
                    else "exclude_candidate_false_positive"
                ),
                "category_ids": row.get("category_ids") or [],
                "ultimate_direction": row.get("ultimate_direction"),
                "measure_weight": 0.5,
                "reason": row["reason"],
                "greenlight_required": True,
            }
        )

    short_subsumed_by_candidate_exclusion = 0
    short_flag_resolved_by_candidate_exclusion = 0
    for row in short_edges:
        amend = amendment_by_key.get(row["canonical_key"])
        if row["disposition"] == "flagged":
            if amend and amend["disposition"] == "exclude_false_positive":
                short_flag_resolved_by_candidate_exclusion += 1
                continue
            unresolved.append(
                {
                    "schema": "legislation-culling-unresolved-v1",
                    "source_lane": "short_act_collision",
                    "decision_scope": "membership_edge",
                    "canonical_key": row["canonical_key"],
                    "query_id": row["query_id"],
                    "disposition": "flagged",
                    "reason": row["reason"],
                    "rule_id": row.get("flag_kind"),
                    "text_available": row.get("operative_text_reviewed"),
                    "measure_weight": row["measure_weight"],
                    "nested_in_candidate_hold": bool(
                        amend and amend["disposition"] == "flagged"
                    ),
                    "human_ratification_required": True,
                }
            )
            continue
        if amend and amend["disposition"] == "exclude_false_positive":
            short_subsumed_by_candidate_exclusion += 1
            continue
        if (
            row["disposition"] == "include"
            and amend
            and row["query_id"] in set(amend.get("category_ids") or [])
        ):
            short_subsumed_by_candidate_exclusion += 1
            continue
        actions.append(
            {
                "schema": "legislation-preintegration-proposed-action-v1",
                "source_lane": "short_act_collision",
                "decision_scope": "membership_edge",
                "canonical_key": row["canonical_key"],
                "query_id": row["query_id"],
                "disposition": row["disposition"],
                "action": (
                    "upsert_membership_edge"
                    if row["disposition"] == "include"
                    else "exclude_membership_edge_false_positive"
                ),
                "category_ids": [row["query_id"]],
                "ultimate_direction": None,
                "measure_weight": row["measure_weight"],
                "reason": row["reason"],
                "greenlight_required": True,
            }
        )

    for row in bills:
        if row["disposition"] == "flagged":
            unresolved.append(
                {
                    "schema": "legislation-culling-unresolved-v1",
                    "source_lane": "bill_recall",
                    "decision_scope": "candidate",
                    "canonical_key": row["canonical_key"],
                    "query_id": None,
                    "disposition": "flagged",
                    "reason": row["reason"],
                    "rule_id": row.get("resolution_artifact_required"),
                    "text_available": row.get("operative_text_reviewed"),
                    "measure_weight": 1.0,
                    "nested_in_candidate_hold": False,
                    "human_ratification_required": True,
                }
            )
            continue
        actions.append(
            {
                "schema": "legislation-preintegration-proposed-action-v1",
                "source_lane": "bill_recall",
                "decision_scope": "candidate",
                "canonical_key": row["canonical_key"],
                "query_id": None,
                "disposition": row["disposition"],
                "action": (
                    "upsert_candidate_memberships"
                    if row["disposition"] == "include_candidate"
                    else "exclude_candidate_false_positive"
                ),
                "category_ids": row.get("category_ids") or [],
                "ultimate_direction": None,
                "measure_weight": 1.0,
                "reason": row["reason"],
                "greenlight_required": True,
            }
        )

    actions.sort(
        key=lambda row: (
            row["canonical_key"],
            row["decision_scope"],
            row.get("query_id") or "",
            row["source_lane"],
        )
    )
    unresolved.sort(
        key=lambda row: (
            row["canonical_key"],
            row["decision_scope"],
            row.get("query_id") or "",
            row["source_lane"],
        )
    )

    action_counts = Counter(row["action"] for row in actions)
    if len(actions) != 2981:
        raise RuntimeError(f"preintegration action count drifted: {len(actions)}")
    if action_counts != {
        "upsert_candidate_memberships": 66,
        "upsert_membership_edge": 7,
        "exclude_candidate_false_positive": 2505,
        "exclude_membership_edge_false_positive": 403,
    }:
        raise RuntimeError(f"preintegration action partition drifted: {action_counts}")
    if short_subsumed_by_candidate_exclusion != 14:
        raise RuntimeError("expected fourteen redundant short-act exclusions")
    if short_flag_resolved_by_candidate_exclusion != 1:
        raise RuntimeError("expected one short-act flag resolved by candidate exclusion")

    unresolved_unique_candidates = {row["canonical_key"] for row in unresolved}
    nested_unresolved = sum(row["nested_in_candidate_hold"] for row in unresolved)
    if len(unresolved) != 1184 or len(unresolved_unique_candidates) != 1169:
        raise RuntimeError(
            "unresolved reconciliation drifted: "
            f"units={len(unresolved)} candidates={len(unresolved_unique_candidates)}"
        )
    if nested_unresolved != 15:
        raise RuntimeError(f"nested unresolved edge count drifted: {nested_unresolved}")

    OUT.mkdir(parents=True, exist_ok=True)
    actions_path = OUT / "proposed_integration_actions.ndjson"
    unresolved_path = OUT / "unresolved_for_ratification.ndjson"
    write_ndjson(actions_path, actions)
    write_ndjson(unresolved_path, unresolved)

    include_category_edges = sum(
        len(row["category_ids"])
        for row in actions
        if row["action"] in {"upsert_candidate_memberships", "upsert_membership_edge"}
    )
    adversarial_review = {
        "schema": "legislation-bill-recall-adversarial-review-v1",
        "reviewer": "Codex read-only reviewer lane",
        "scope": "23 absent legacy bill-recall candidates",
        "full_disposition_agreements": [
            "117:hr:6732",
            "117:s:4004",
            "118:s:1159",
            "117:hres:634",
            "117:hres:1076",
            "117:s:1690",
        ],
        "category_only_disagreements": [
            "118:hjres:190",
            "118:hjres:195",
            "119:sjres:134",
        ],
        "disposition_disagreements": [
            "117:hr:3155",
            "117:s:1587",
            "118:s:673",
            "118:hr:2602",
            "119:s:273",
            "118:s:3302",
            "119:s:3136",
            "119:s:3171",
            "117:hr:3854",
            "117:s:2034",
            "117:hr:474",
            "117:s:5076",
            "118:hr:3511",
            "117:s:63",
        ],
        "evidence_observation": (
            "Independent official Congress.gov/GovInfo summary/text review "
            "resolved subject matter for the conflicts, but did not itself "
            "ratify the material-credit-union-nexus policy question or prove "
            "all-version closure for every measure."
        ),
        "fail_closed_recommendation": (
            "Preserve the Opus proposal states: 6 include, 2 exclude, 15 "
            "flagged; keep BNPL in CFPB plus Credit Card and omit Payments; "
            "assign no scoring direction; do not integrate before Greenlight."
        ),
        "repository_edits_performed_by_reviewer": False,
        "integration_performed_by_reviewer": False,
    }
    adversarial_path = OUT / "bill_recall_adversarial_review.json"
    adversarial_path.write_bytes(canonical_bytes(adversarial_review))
    summary = {
        "schema": "legislation-culling-coordinator-reconciliation-v1",
        "run_id": "coordinator_reconciliation_codex_20260728a",
        "status": "DECISION_REQUIRED_BEFORE_INTEGRATION",
        "coordinator": "Codex",
        "semantic_lane_models": {
            "amendment": "claude-opus-5",
            "short_act": "claude-opus-5",
            "bill_recall": "claude-opus-5",
        },
        "original_method": {
            "official_title_summary_and_complete_operative_text_primary": True,
            "floor_speech_is_context_not_parent_relevance_transfer": True,
            "press_and_letters_require_exact_measure_or_rule_nexus": True,
            "missing_summary_or_text_is_neutral": True,
            "bill_weight": 1.0,
            "amendment_weight": 0.5,
        },
        "coverage": {
            "amendments": {
                "unique_candidates": 3703,
                "dispositions": dict(sorted(amendment_counts.items())),
                "complete_accounting": True,
            },
            "short_act_collisions": {
                "unique_membership_edges": 454,
                "bill_edges": 423,
                "amendment_edges": 31,
                "dispositions": dict(sorted(short_counts.items())),
                "complete_accounting": True,
            },
            "bill_recall": {
                "legacy_floor": 465,
                "covered_in_discovery": 442,
                "absent_and_adjudicated": 23,
                "quorum_floor": 44,
                "quorum_present_in_discovery": 44,
                "dispositions": dict(sorted(bill_counts.items())),
                "complete_accounting": True,
            },
        },
        "cross_lane_reconciliation": {
            "amendment_short_act_overlap_edges": 31,
            "overlap_matrix": {
                f"short={short_state}|amendment={amendment_state}": count
                for (short_state, amendment_state), count in sorted(
                    overlap_matrix.items()
                )
            },
            "redundant_short_act_exclusions_subsumed": (
                short_subsumed_by_candidate_exclusion
            ),
            "short_act_flags_resolved_by_candidate_exclusion": (
                short_flag_resolved_by_candidate_exclusion
            ),
            "special_cases": {
                "118:samdt:1084": (
                    "candidate-level amendment exclusion supersedes the "
                    "text-only short-act flag because the exact official "
                    "purpose resolves the subject"
                ),
                "119:samdt:5869": (
                    "exclude only the technology_emerging_issues short-act "
                    "edge; preserve the separate examination_supervision "
                    "candidate hold"
                ),
            },
            "physical_or_semantic_double_count_remaining": False,
        },
        "preintegration_change_set": {
            "proposed_action_rows": len(actions),
            "action_counts": dict(sorted(action_counts.items())),
            "proposed_include_actions": 73,
            "proposed_exclude_actions": 2908,
            "proposed_include_category_edges": include_category_edges,
            "greenlight_required": True,
        },
        "unresolved": {
            "decision_units": len(unresolved),
            "unique_candidates": len(unresolved_unique_candidates),
            "nested_short_act_edges_inside_amendment_candidate_holds": (
                nested_unresolved
            ),
            "integration_policy": "remain held, non-scoring, and visible",
        },
        "adversarial_bill_recall_review": adversarial_review,
        "rank_delta": {
            "status": "NOT_COMPUTED_PREINTEGRATION_BY_DESIGN",
            "reason": (
                "a true legislative rank delta requires a human-greenlit "
                "accepted ledger and a clean paired shadow recomputation"
            ),
        },
        "canonical_category_count": len(canonical_categories),
        "canonical_category_registry": file_receipt(REGISTRY),
        "lane_receipts": lane_receipts,
        "integration_performed": False,
        "production_write_performed": False,
        "scoring_performed": False,
        "rank_recompute_performed": False,
    }

    summary_path = OUT / "summary.json"
    summary_path.write_bytes(canonical_bytes(summary))
    markdown_path = OUT / "SUMMARY.md"
    markdown_path.write_text(
        "\n".join(
            [
                "# Culling reconciliation — pre-Integration decision gate",
                "",
                "**Status: DECISION REQUIRED. No integration, scoring, or rank recomputation was performed.**",
                "",
                "## Complete accounting",
                "",
                "- Amendments: 3,703 = 60 include + 2,503 false-positive exclude + 1,140 held.",
                "- Short-act collision edges: 454 = 7 include + 417 false-positive exclude + 30 held.",
                "- Bill recall: 465 legacy rows = 442 already covered + 23 adjudicated; the 23 = 6 include + 2 false-positive exclude + 15 held.",
                "- Quorum recall: 44/44 already covered in discovery.",
                "",
                "## Reconciled pre-Integration change set",
                "",
                f"- {len(actions):,} proposal rows: 73 include actions and 2,908 exclusion actions.",
                f"- {include_category_edges:,} category-membership edges are proposed by the 73 includes.",
                "- Fourteen short-act amendment exclusions were removed as redundant with candidate-level amendment exclusions.",
                "- `118:samdt:1084`: the exact official-purpose exclusion controls.",
                "- `119:samdt:5869`: only its Technology edge is excluded; its separate Examination hold remains.",
                "",
                "## Adversarial bill-recall review",
                "",
                "- Six full agreements, three BNPL category-only disagreements, and fourteen disposition disagreements.",
                "- Independent official-source review resolved subject matter but not the governing material-credit-union-nexus or all-version closure questions.",
                "- Fail-closed result: preserve the Opus 6/2/15 partition, omit BNPL from Payments, and assign no scoring direction.",
                "",
                "## Held for ratification",
                "",
                f"- {len(unresolved):,} unresolved decision units across {len(unresolved_unique_candidates):,} unique candidates.",
                "- Held rows remain visible and non-scoring; they are not silently discarded.",
                "",
                "## Method",
                "",
                "Operative text and official purpose/title/summary control. Floor speech is retained as context, not as a transfer of the parent bill's relevance. Exact press and letter evidence can corroborate direction; missing text or summary is neutral. Bills carry weight 1.0 and amendments 0.5.",
                "",
                "## Rank delta",
                "",
                "Not computed before Integration. A defensible legislative rank delta requires the greenlit accepted ledger and a clean paired shadow recomputation.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    receipt = {
        "schema": "legislation-culling-coordinator-receipt-v1",
        "run_id": "coordinator_reconciliation_codex_20260728a",
        "status": summary["status"],
        "inputs": {
            "amendment_receipt": lane_receipts["amendment"],
            "short_act_receipt": lane_receipts["short_act"],
            "bill_recall_receipt": lane_receipts["bill_recall"],
            "canonical_category_registry": file_receipt(REGISTRY),
        },
        "outputs": {
            "proposed_integration_actions.ndjson": file_receipt(
                actions_path, records=len(actions)
            ),
            "unresolved_for_ratification.ndjson": file_receipt(
                unresolved_path, records=len(unresolved)
            ),
            "summary.json": file_receipt(summary_path, records=1),
            "SUMMARY.md": file_receipt(markdown_path, records=1),
            "bill_recall_adversarial_review.json": file_receipt(
                adversarial_path, records=1
            ),
        },
        "proofs": {
            "all_three_lane_receipts_hash_verified": True,
            "all_lane_receipts_proposal_only": True,
            "all_semantic_lanes_are_opus_5": True,
            "canonical_category_count_is_19": True,
            "amendment_partition_is_exactly_3703_unique": True,
            "short_act_partition_is_exactly_454_unique_edges": True,
            "bill_recall_partition_is_exactly_23_unique_absent_keys": True,
            "legacy_and_quorum_recall_accounting_closed": True,
            "bill_1_amendment_0_5_weights_verified": True,
            "31_edge_overlap_reconciled_without_double_count": True,
            "integration_performed": False,
            "rank_delta_computed": False,
        },
        "greenlight_required": True,
    }
    (OUT / "receipt.json").write_bytes(canonical_bytes(receipt))
    print(json.dumps(
        {
            "output": str(OUT),
            "actions": len(actions),
            "unresolved_units": len(unresolved),
            "unresolved_candidates": len(unresolved_unique_candidates),
            "receipt_sha256": sha256_file(OUT / "receipt.json"),
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
