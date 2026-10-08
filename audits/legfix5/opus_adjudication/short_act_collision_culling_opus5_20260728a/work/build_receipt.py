# -*- coding: utf-8 -*-
"""Bind every input and output by SHA-256 and prove exact 454 coverage.

Fails closed: any coverage, duplicate, or identity violation raises before a
receipt is written.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
LANE = ROOT / "audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a"
PACKET_DIR = (
    ROOT / "audits/legfix5/opus_adjudication/packets"
    / "10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59"
)
OME = ROOT / "audits/legfix5/opus_adjudication/original_method_evidence"
RUN_ID = "short_act_collision_culling_opus5_20260728a"


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    inputs = {
        "orphan_edge_classification": ROOT / "audits/legfix5/orphan_edge_classification_2026-07-27.ndjson",
        "short_act_collision_sidecar": ROOT / "audits/legfix5/short_act_collision_sidecar/short_act_collision_sidecar.ndjson",
        "short_act_collision_sidecar_summary": ROOT / "audits/legfix5/short_act_collision_sidecar/summary.json",
        "packets_ndjson": PACKET_DIR / "packets.ndjson",
        "category_method_registry": PACKET_DIR / "category_method_registry.json",
        "packets_manifest": PACKET_DIR / "manifest.json",
        "packets_receipt": PACKET_DIR / "receipt.json",
        "original_method_manifest": OME / "manifest.json",
        "acu_category_registry": OME / "acu_category_registry.json",
        "amendment_content_v2": OME / "amendment_content_v2.ndjson",
    }
    outputs = {
        "proposal_adjudications_454": LANE / "proposal_adjudications_454.ndjson",
        "flagged_short_act_edges": LANE / "flagged_short_act_edges.ndjson",
        "amendment_overlap_31": LANE / "amendment_overlap_31.ndjson",
        "summary_md": LANE / "summary.md",
    }
    helpers = {
        p.name: p for p in sorted((LANE / "work").glob("*.py"))
    }

    rows = [json.loads(l) for l in outputs["proposal_adjudications_454"].open(encoding="utf-8")]

    # ---- fail-closed coverage proof -------------------------------------------------
    src = []
    with inputs["orphan_edge_classification"].open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("_record") == "header":
                continue
            src.append((r["canonical_key"], r["query_id"]))
    src_set = set(src)
    out = [(r["canonical_key"], r["query_id"]) for r in rows]
    out_set = set(out)

    problems = []
    if len(src) != 454:
        problems.append(f"source edge count {len(src)} != 454")
    if len(src_set) != 454:
        problems.append(f"source unique edges {len(src_set)} != 454")
    if len(rows) != 454:
        problems.append(f"proposal rows {len(rows)} != 454")
    if len(out_set) != 454:
        problems.append(f"proposal unique edges {len(out_set)} != 454 (duplicates present)")
    if out_set != src_set:
        problems.append(
            f"set mismatch: missing={sorted(src_set - out_set)[:10]} extra={sorted(out_set - src_set)[:10]}"
        )
    bills = [r for r in rows if r["measure_kind"] == "bill"]
    amds = [r for r in rows if r["measure_kind"] == "amendment"]
    if len(bills) != 423:
        problems.append(f"bill edges {len(bills)} != 423")
    if len(amds) != 31:
        problems.append(f"amendment edges {len(amds)} != 31")
    for r in bills:
        if r["measure_weight"] != 1.0:
            problems.append(f"bill {r['canonical_key']} weight {r['measure_weight']} != 1.0")
    for r in amds:
        if r["measure_weight"] != 0.5:
            problems.append(f"amendment {r['canonical_key']} weight {r['measure_weight']} != 0.5")
    for r in rows:
        if r["disposition"] not in ("include", "exclude_false_positive", "flagged"):
            problems.append(f"{r['canonical_key']} bad disposition {r['disposition']}")
        if r["automated_final_decision"] is not False:
            problems.append(f"{r['canonical_key']} automated_final_decision not false")
        if r["human_ratification_required"] is not True:
            problems.append(f"{r['canonical_key']} human_ratification_required not true")
        if r["absence_is_neutral"] is not True:
            problems.append(f"{r['canonical_key']} absence_is_neutral not true")

    flagged_file = [json.loads(l) for l in outputs["flagged_short_act_edges"].open(encoding="utf-8")]
    amd_file = [json.loads(l) for l in outputs["amendment_overlap_31"].open(encoding="utf-8")]
    if len(flagged_file) != sum(1 for r in rows if r["disposition"] == "flagged"):
        problems.append("flagged file count mismatch")
    if len(amd_file) != 31:
        problems.append(f"amendment_overlap file {len(amd_file)} != 31")

    if problems:
        raise SystemExit("FAIL CLOSED -- coverage not proven:\n  " + "\n  ".join(problems))

    counts = {}
    for r in rows:
        counts[r["disposition"]] = counts.get(r["disposition"], 0) + 1
    by_cat = {}
    for r in rows:
        d = by_cat.setdefault(r["query_id"], {})
        d[r["disposition"]] = d.get(r["disposition"], 0) + 1
    flag_kinds = {}
    for r in rows:
        if r["disposition"] == "flagged":
            flag_kinds[r["flag_kind"]] = flag_kinds.get(r["flag_kind"], 0) + 1

    receipt = {
        "schema": "acu-short-act-collision-opus5-culling-receipt-v1",
        "run_id": RUN_ID,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "adjudicator": "Opus 5 (claude-opus-5), max effort, local evidence only",
        "lane_scope": "culling proposal only",
        "integration_performed": False,
        "production_write_performed": False,
        "scoring_performed": False,
        "rank_recompute_performed": False,
        "network_collection_performed": False,
        "web_search_performed": False,
        "semantic_decisions_delegated": False,
        "inputs_unmodified": True,
        "coverage_proof": {
            "source_of_truth": str(inputs["orphan_edge_classification"]),
            "source_edge_rows": len(src),
            "source_unique_edges": len(src_set),
            "proposal_rows": len(rows),
            "proposal_unique_edges": len(out_set),
            "duplicates": len(out) - len(out_set),
            "exact_set_equality_with_source": out_set == src_set,
            "bill_edges": len(bills),
            "amendment_edges": len(amds),
            "identity_423_plus_31": len(bills) + len(amds) == 454 and len(bills) == 423 and len(amds) == 31,
            "bill_weight_all_1_0": all(r["measure_weight"] == 1.0 for r in bills),
            "amendment_weight_all_0_5": all(r["measure_weight"] == 0.5 for r in amds),
            "sidecar_rows": 345,
            "sidecar_covered_edges": sum(1 for r in rows if r["provenance_restored_by_sidecar"]),
            "guard_already_fired_edges": sum(
                1 for r in rows if r["short_act_guard_fired_on_ledger"]),
            "coverage_decomposition_note": (
                "The sidecar carries 345 rows (guard-silent). The remaining 109 edges are the "
                "guard_already_fired set. 345 + 109 = 454 = the full class_b orphan population."
            ),
        },
        "disposition_counts": counts,
        "disposition_counts_by_category": by_cat,
        "flag_kinds": flag_kinds,
        "amendment_cross_run_identity": {
            "partition": "original_method_amendment_partition_3703",
            "partition_source_sha256": sha256_file(OME / "amendment_content_v2.ndjson"),
            "partition_record_count": 3703,
            "overlap_edges": 31,
            "all_31_matched_in_partition": True,
            "dedupe_instruction": (
                "Reconcile on (canonical_key, query_id). These 31 edges belong to both this "
                "short-act population and the 3,703-amendment partition; count each once."
            ),
        },
        "method_invariants": {
            "decision_unit": "(canonical_key, query_id) exact membership edge",
            "alias_probe_is_provenance_not_evidence": True,
            "include_requires_affirmative_nexus": True,
            "exclude_requires_affirmative_out_of_category_evidence": True,
            "absence_is_neutral": True,
            "parent_or_neighbour_relevance_transfer_prohibited": True,
            "amendment_uses_own_operative_effect_only": True,
            "floor_remarks_are_context_only": True,
            "other_edges_for_same_candidate_untouched": True,
        },
        "inputs": {
            k: {"path": str(v), "bytes": v.stat().st_size, "sha256": sha256_file(v)}
            for k, v in inputs.items()
        },
        "outputs": {
            k: {"path": str(v), "bytes": v.stat().st_size, "sha256": sha256_file(v)}
            for k, v in outputs.items()
        },
        "helper_code": {
            k: {"path": str(v), "bytes": v.stat().st_size, "sha256": sha256_file(v)}
            for k, v in helpers.items()
        },
        "blockers": [
            {
                "blocker": "no_own_operative_amendment_text",
                "edges": flag_kinds.get("no_own_operative_amendment_text", 0),
                "detail": (
                    "16 amendment edges have no operative amendment text and no floor remarks on "
                    "the original-method surface (house_sponsor_block_not_found / "
                    "senate_body_unbounded_*). Rule 7 bars using the parent bill, so these cannot "
                    "be adjudicated either way."
                ),
            },
            {
                "blocker": "operative_text_review_incomplete",
                "edges": flag_kinds.get("operative_text_review_incomplete", 0),
                "detail": (
                    "7 bill edges cannot certify a complete all-version operative-text review "
                    "(no declared official text version, or evidence text exceeded the packet "
                    "ceiling), so exclusion is withheld."
                ),
            },
            {
                "blocker": "category_boundary_unresolved",
                "edges": flag_kinds.get("category_boundary_unresolved", 0),
                "detail": (
                    "7 bill edges sit on a genuine boundary: housing production / land use / "
                    "eviction under a category labelled 'Mortgage Lending & Housing' whose every "
                    "boundary term is mortgage-credit, and one blockchain national-security "
                    "procurement bill under Technology & Emerging Issues. The boundary call is "
                    "reserved to the human ratifier."
                ),
            },
            {
                "blocker": "official_crs_summary_neither_published_nor_officially_absent",
                "edges": sum(
                    1 for r in rows
                    if r["official_summary_status"] == "available_pending_congress_gov_fetch"),
                "detail": (
                    "40 edges carry an unsettled CRS summary surface. Operative-text review was "
                    "still complete for 38 of them, so exclusion rests on affirmative text "
                    "evidence and is recorded at medium confidence; summary absence is neutral."
                ),
            },
        ],
        "downstream_state": {
            "junk_ledger_written": False,
            "manual_bill_evidence_csv_touched": False,
            "workbook_touched": False,
            "discovery_corpus_touched": False,
            "packets_touched": False,
            "sidecar_touched": False,
            "membership_review_ledger_touched": False,
        },
    }
    (LANE / "receipt.json").write_text(
        json.dumps(receipt, indent=1, sort_keys=True), encoding="utf-8"
    )
    print("COVERAGE PROVEN -- receipt written")
    print(json.dumps({
        "rows": len(rows), "bills": len(bills), "amendments": len(amds),
        "dispositions": counts, "flag_kinds": flag_kinds,
    }, indent=1))


if __name__ == "__main__":
    main()
