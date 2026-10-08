#!/usr/bin/env python3
"""Bind inputs and outputs by SHA-256, prove exact coverage, and fail closed.

Coverage is not asserted, it is derived: the key sets are read back off the
emitted files and compared against the key sets read off the frozen inputs. A
count that does not reconcile raises, and no receipt is written.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent
EV = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\opus_adjudication\original_method_evidence")
SIDE = pathlib.Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\legfix5\short_act_collision_sidecar")
IN = pathlib.Path(r"C:\Users\pgoff\AppData\Local\Temp\claude\cxwt-acu-registry")
RUN_ID = "amendment_culling_opus5_20260728a"

sys.path.insert(0, str(HERE))
from canon import CANON, CANONICAL_IDS, ALIASES  # noqa: E402


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def nd(path: pathlib.Path) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


class Blocked(Exception):
    pass


def main() -> int:
    blockers: list[str] = []

    content = nd(EV / "amendment_content_v2.ndjson")
    queue = nd(EV / "amendment_review_queue.ndjson")
    corpus_keys = [r["canonical_key"] for r in content]
    queue_keys = [r["canonical_key"] for r in queue]

    p419 = OUT / "proposal_adjudications_419.ndjson"
    p3703 = OUT / "amendment_partition_3703.ndjson"
    pflag = OUT / "flagged_amendments.ndjson"
    r419, r3703, rflag = nd(p419), nd(p3703), nd(pflag)
    k419 = [r["canonical_key"] for r in r419]
    k3703 = [r["canonical_key"] for r in r3703]

    # ---------------- fail-closed coverage proofs ----------------
    checks = {
        "corpus_records_is_3703": len(corpus_keys) == 3703,
        "corpus_keys_unique": len(set(corpus_keys)) == 3703,
        "queue_records_is_419": len(queue_keys) == 419,
        "queue_keys_unique": len(set(queue_keys)) == 419,
        "proposal_rows_is_419": len(k419) == 419,
        "proposal_keys_unique": len(set(k419)) == len(k419),
        "proposal_keys_equal_queue_keys": set(k419) == set(queue_keys),
        "partition_rows_is_3703": len(k3703) == 3703,
        "partition_keys_unique": len(set(k3703)) == len(k3703),
        "partition_keys_equal_corpus_keys": set(k3703) == set(corpus_keys),
        "queue_subset_of_partition": set(queue_keys) <= set(k3703),
        "every_row_has_one_disposition": all(
            r["disposition"] in ("include", "exclude_false_positive", "flagged") for r in r3703),
        "flagged_file_equals_partition_flagged": (
            {r["canonical_key"] for r in rflag}
            == {r["canonical_key"] for r in r3703 if r["disposition"] == "flagged"}),
        "amendment_weight_is_half_everywhere": all(r["amendment_weight"] == 0.5 for r in r3703),
        "no_automated_final_decision": all(r["automated_final_decision"] is False for r in r3703),
        "human_ratification_required_everywhere": all(
            r["human_ratification_required"] is True for r in r3703),
        "parent_relevance_never_transferred": all(
            r["parent_relevance_transferred"] is False for r in r3703),
        "floor_evidence_never_decisive": all(r["floor_evidence_used"] is False for r in r3703),
        "include_rows_all_have_direction": all(
            r["ultimate_direction"] in (1, -1) for r in r3703 if r["disposition"] == "include"),
        "include_rows_all_have_category": all(
            r["category_ids"] for r in r3703 if r["disposition"] == "include"),
        "excluded_rows_carry_no_score": all(
            not r["category_ids"] and r["ultimate_direction"] is None
            for r in r3703 if r["disposition"] == "exclude_false_positive"),
        "flagged_rows_carry_no_direction": all(
            r["ultimate_direction"] is None for r in r3703 if r["disposition"] == "flagged"),
        "proposal_agrees_with_partition": all(
            a["disposition"] == b["disposition"] and a["ultimate_direction"] == b["ultimate_direction"]
            for a, b in zip(sorted(r419, key=lambda x: x["canonical_key"]),
                            sorted((r for r in r3703 if r["canonical_key"] in set(k419)),
                                   key=lambda x: x["canonical_key"]))),
    }
    # Canonical IDs are DERIVED by canon.py from the frozen guard registry plus the
    # production alias map, then cross-checked against the category_review_queue
    # registries. Nothing here is a hand-written list, which is the defect this
    # correction closes: the previous receipt compared the lane against a copy of
    # the same aliased vocabulary it had emitted, so the assertion proved nothing.
    checks["canonical_registry_derived_not_declared"] = (
        CANON["count"] == 19 and len(CANONICAL_IDS) == 19
        and not (CANONICAL_IDS & set(ALIASES))
    )
    checks["canonical_registry_corroborated"] = bool(CANON["corroborating_registries"]) and all(
        c["agrees"] for c in CANON["corroborating_registries"])
    checks["categories_are_canonical_19"] = all(
        set(r["category_ids"]) <= CANONICAL_IDS for r in r3703)

    alias_names = sorted(ALIASES)
    def _alias_hits(rows):
        n = 0
        for r in rows:
            blob = json.dumps(r, ensure_ascii=False)
            if any(a in blob for a in alias_names):
                n += 1
        return n
    checks["no_noncanonical_alias_in_any_output_row"] = (
        _alias_hits(r3703) == 0 and _alias_hits(r419) == 0 and _alias_hits(rflag) == 0)
    lane_src = sorted(HERE.glob("*.py"))
    checks["no_noncanonical_alias_in_lane_rulings"] = not any(
        a in (HERE / "decisions.py").read_text(encoding="utf-8") for a in alias_names)
    checks["lane_helpers_free_of_alias_literals"] = all(
        not any(a in p.read_text(encoding="utf-8") for a in alias_names)
        for p in lane_src if p.name not in ("canon.py", "receipt.py"))

    for name, ok in checks.items():
        if not ok:
            blockers.append(f"COVERAGE PROOF FAILED: {name}")

    # ---------------- identities ----------------
    disp = Counter(r["disposition"] for r in r3703)
    notext = {r["canonical_key"] for r in content if not (r.get("amendment_text") or "").strip()}
    by_rule = Counter(r["rule_id"] for r in r3703)
    dirn = Counter(r["ultimate_direction"] for r in r3703 if r["disposition"] == "include")
    cats = Counter(c for r in r3703 if r["disposition"] == "include" for c in r["category_ids"])

    prior = json.loads((IN / "audits_out" / "amendments" / "amendment_domain_verdict_v2.json")
                       .read_bytes().decode("utf-8-sig"))
    prior_in = {a["canonical_key"] for a in prior["amendments"] if a["verdict"] == "IN"}
    mine = {r["canonical_key"]: r["disposition"] for r in r3703}
    cross = Counter((("prior_IN" if k in prior_in else "prior_OUT"), v) for k, v in mine.items())

    identities = {
        "corpus_total": len(corpus_keys),
        "review_queue_total": len(queue_keys),
        "partition": dict(disp),
        "partition_sums_to_corpus": sum(disp.values()) == len(corpus_keys),
        "include_direction_split": {"positive_1": dirn[1], "negative_minus1": dirn[-1]},
        "include_by_category": dict(cats.most_common()),
        "unavailable_text_subset": {
            "total": len(notext),
            "flagged": sum(1 for r in r3703 if r["canonical_key"] in notext and r["disposition"] == "flagged"),
            "excluded_on_official_purpose": sum(
                1 for r in r3703 if r["canonical_key"] in notext
                and r["disposition"] == "exclude_false_positive"),
            "included": sum(1 for r in r3703 if r["canonical_key"] in notext and r["disposition"] == "include"),
        },
        "queue_partition": dict(Counter(r["disposition"] for r in r419)),
        "rows_by_rule_id": dict(by_rule.most_common()),
        "prior_partition_crosswalk": {f"{a}->{b}": n for (a, b), n in sorted(cross.items())},
        "prior_partition_as_found_on_disk": {
            "artifact": "amendment_domain_verdict_v2.json",
            "IN": prior["IN"], "OUT": prior["OUT"], "total": prior["amendments_total"],
        },
    }
    nt = identities["unavailable_text_subset"]
    if nt["total"] != nt["flagged"] + nt["excluded_on_official_purpose"] + nt["included"]:
        blockers.append("COVERAGE PROOF FAILED: unavailable-text subset does not reconcile")
    if not identities["partition_sums_to_corpus"]:
        blockers.append("COVERAGE PROOF FAILED: partition does not sum to the corpus")

    # ---------------- hash binding ----------------
    ev_files = sorted(p for p in EV.iterdir() if p.is_file())
    side_files = sorted(p for p in SIDE.iterdir() if p.is_file())
    src = [IN / "fec" / n for n in (
        "build_amendment_review_queue.py", "adjudicate_amendment_queue.py",
        "decide_amendment_domain.py", "match_with_query_guards.py")]
    prior_art = [IN / "audits_out" / "amendments" / n for n in (
        "amendment_domain_verdict_v2.json", "amendment_guarded_v2.json",
        "amendment_adjudicated.ndjson", "amendment_review_queue.ndjson")]
    meta = IN / "audits_out" / "media_link" / "amend_meta.json"
    press_src = IN / "audits_out" / "press_sweep" / "link.py"
    strict_src = IN / "audits_out" / "press_sweep" / "refine.py"

    def bind(paths, role):
        return {str(p): {"role": role, "bytes": p.stat().st_size, "sha256": sha256(p)}
                for p in paths if p.exists()}

    inputs = {}
    inputs.update(bind(ev_files, "frozen_evidence_bundle"))
    inputs.update(bind(side_files, "short_act_collision_sidecar"))
    inputs.update(bind([meta], "official_amendment_metadata_and_purpose"))
    inputs.update(bind(src, "original_method_source"))
    inputs.update(bind([press_src, strict_src], "detector_provenance_source"))
    inputs.update(bind(prior_art, "prior_run_artifact_for_comparison"))

    helpers = sorted(p for p in HERE.iterdir() if p.suffix in (".py",))
    work = sorted(p for p in HERE.iterdir() if p.suffix in (".ndjson", ".txt", ".json"))
    outs = [p419, p3703, pflag] + [q for q in [OUT / "summary.md"] if q.exists()]

    before = json.loads((HERE / "_before_correction.json").read_text(encoding="utf-8"))
    before_rows = json.loads((HERE / "_before_rows.json").read_text(encoding="utf-8"))

    # Preservation is PROVEN, not asserted: every substantive field of every one of
    # the 3,703 rows is compared against its pre-correction value, with the two
    # aliases mapped through so a rename does not read as a change.
    COMPARE = {"disposition", "ultimate_direction", "confidence", "rule_id", "reason",
               "amendment_weight", "text_available", "press_evidence_used",
               "parent_context_used"}
    drift = []
    for r in r3703:
        b = before_rows.get(r["canonical_key"])
        if b is None:
            drift.append((r["canonical_key"], "missing_before"))
            continue
        for f in sorted(COMPARE):
            if r[f] != b[f]:
                drift.append((r["canonical_key"], f))
        if sorted(r["category_ids"]) != sorted(b["category_ids_canonicalised"]):
            drift.append((r["canonical_key"], "category_ids"))
        if len(r["evidence_ids"]) != b["n_evidence_ids"]:
            drift.append((r["canonical_key"], "n_evidence_ids"))
    preserved = not drift
    checks["substantive_dispositions_preserved"] = preserved
    checks["before_after_key_sets_identical"] = set(before_rows) == {r["canonical_key"] for r in r3703}
    if drift:
        blockers.append(f"CORRECTION CHANGED SUBSTANCE: {drift[:10]}")
    alias_names = sorted(ALIASES)

    def _count(rows, field):
        return sum(1 for r in rows if any(a in r[field] for a in alias_names)) if field == "category_ids"             else sum(1 for r in rows if any(any(a in e for a in alias_names) for e in r["evidence_ids"]))

    correction = {
        "correction_id": "CORR-01-canonical-category-ids",
        "defect": "the lane validated category IDs against a hand-written list copied out of "
                  "query_guard_registry_v2.json, which carries two noncanonical source aliases, so "
                  "the receipt assertion categories_are_canonical_19 compared the lane against its "
                  "own aliased vocabulary and proved nothing",
        "aliases_replaced": ALIASES,
        "authority": "fec/legislation_original_method_evidence.py CATEGORY_ID_ALIASES, the "
                     "production module that builds this frozen bundle; corroborated by the "
                     "category_review_queue manifests' receipt.category_registry",
        "validation_now": "canon.py derives the canonical nineteen by loading the frozen registry "
                          "and applying the production alias map read out by AST, then cross-checks "
                          "against the queue registries; no list is retyped in this lane",
        "affected_rows_before": {
            "proposal_adjudications_419.ndjson": before["affected"]["proposal_adjudications_419.ndjson"],
            "amendment_partition_3703.ndjson": before["affected"]["amendment_partition_3703.ndjson"],
            "flagged_amendments.ndjson": before["affected"]["flagged_amendments.ndjson"],
            "work/evidence_index.ndjson": before["affected"]["work/evidence_index.ndjson"],
        },
        "affected_rows_after": {
            "proposal_adjudications_419.ndjson": {
                "category_ids_rows": _count(r419, "category_ids"),
                "evidence_ids_rows": _count(r419, "evidence_ids")},
            "amendment_partition_3703.ndjson": {
                "category_ids_rows": _count(r3703, "category_ids"),
                "evidence_ids_rows": _count(r3703, "evidence_ids")},
            "flagged_amendments.ndjson": {
                "category_ids_rows": _count(rflag, "category_ids"),
                "evidence_ids_rows": _count(rflag, "evidence_ids")},
        },
        "hashes_before": before["files"],
        "substantive_dispositions_preserved": preserved,
        "substantive_fields_compared": sorted(COMPARE),
        "scope": "identifier rename and validator replacement only; no disposition, direction, "
                 "confidence, rationale or evidence reference was changed",
    }

    receipt = {
        "schema": "acu-amendment-culling-opus5-adjudication-receipt-v2-corrected",
        "run_id": RUN_ID,
        "adjudicator": "Opus 5 (claude-opus-5), max effort, no delegation of semantic decisions",
        "network_used": False,
        "output_directory": str(OUT),
        "method": {
            "domain_basis": "the amendment's own operative text, or its own official congress.gov "
                            "purpose statement, connected to one or more of the 19 canonical ACU "
                            "categories",
            "parent_role": "context for construing what an internal edit operates on; never a "
                           "source of domain or direction",
            "floor_remarks_role": "sponsor intent and context only; never domain, never direction, "
                                  "never a sponsorship or cosponsorship role",
            "press_role": "direction only where the evidence identifies the exact amendment and "
                          "states ACU's position; absence is neutral",
            "letters_role": "separate corroborative and role surface; never bill or amendment "
                            "sponsorship; not used to admit or cull any amendment in this run",
            "direction_convention": "+1 advances the credit-union interest the category names, "
                                    "-1 sets it back",
            "amendment_weight": 0.5,
            "uncertainty_rule": "uncertainty is never converted into exclusion; unresolved rows are "
                                "flagged and preserved",
        },
        "canonical_category_vocabulary": CANON,
        "correction": correction,
        "coverage_proofs": checks,
        "identities": identities,
        "blockers": blockers,
        "integration_performed": False,
        "production_write_performed": False,
        "scoring_performed": False,
        "rank_recompute_performed": False,
        "discovery_corpus_modified": False,
        "manual_bill_evidence_modified": False,
        "workbook_modified": False,
        "junk_ledger_written": False,
        "recovered_input_folder_modified": False,
        "human_ratification_required": True,
        "inputs": inputs,
        "helper_code": {str(p): {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in helpers},
        "working_artifacts": {str(p): {"bytes": p.stat().st_size, "sha256": sha256(p)} for p in work},
        "outputs": {str(p): {"bytes": p.stat().st_size, "sha256": sha256(p),
                             "records": (len(nd(p)) if p.suffix == ".ndjson" else 1)}
                    for p in outs},
    }

    if blockers:
        print("FAIL CLOSED -- receipt not written")
        for b in blockers:
            print("  ", b)
        raise Blocked(blockers[0])

    path = OUT / "receipt.json"
    path.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    receipt["outputs"][str(path)] = {"bytes": path.stat().st_size, "sha256": sha256(path),
                                     "records": 1, "note": "self-hash excluded by construction"}
    print(json.dumps({"partition": identities["partition"],
                      "queue_partition": identities["queue_partition"],
                      "include_direction_split": identities["include_direction_split"],
                      "unavailable_text_subset": identities["unavailable_text_subset"],
                      "prior_crosswalk": identities["prior_partition_crosswalk"],
                      "proofs_passed": sum(1 for v in checks.values() if v),
                      "proofs_total": len(checks)}, indent=1))
    print("receipt:", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
