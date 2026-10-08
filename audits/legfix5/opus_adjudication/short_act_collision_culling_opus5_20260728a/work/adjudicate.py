# -*- coding: utf-8 -*-
"""Emit the Opus 5 short-act-collision culling proposal for all 454 exact edges.

Every disposition below was reached by reading the measure's own official title,
official summary where published, and operative text. This script only encodes
and serialises those readings -- it does not infer them. The stemmed short-act
alias is recorded as discovery provenance and is never disposition evidence.

Nothing here integrates, promotes, scores, or recomputes ranks.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import time

ROOT = pathlib.Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
LANE = ROOT / "audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a"
WORK = LANE / "work"

CLASSIFICATION = ROOT / "audits/legfix5/orphan_edge_classification_2026-07-27.ndjson"
SIDECAR_DIR = ROOT / "audits/legfix5/short_act_collision_sidecar"
PACKET_DIR = (
    ROOT / "audits/legfix5/opus_adjudication/packets"
    / "10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59"
)
OME = ROOT / "audits/legfix5/opus_adjudication/original_method_evidence"
AMD_CONTENT = OME / "amendment_content_v2.ndjson"

RUN_ID = "short_act_collision_culling_opus5_20260728a"

CATEGORY_BOUNDARY = {
    "cdfi_fund": (
        "CDFI Fund: CDFI/MDI certification, CDFI Fund appropriations, the CDFI Bond "
        "Guarantee Program, and underserved-community lending by depository institutions"
    ),
    "examination_supervision": (
        "Examination & Supervision: credit union examination and supervision practice, "
        "CAMELS, FFIEC, safety-and-soundness exams, exam appeal rights, supervisory "
        "tailoring, and BSA CTR/SAR filing thresholds"
    ),
    "fraud_prevention": (
        "Fraud Prevention: payment fraud and scams, check fraud, elder financial "
        "exploitation, identity theft, and fraud information-sharing safe harbours"
    ),
    "mortgage_lending_housing": (
        "Mortgage Lending & Housing (section: Lending): credit union mortgage lending, "
        "FHA mortgage insurance, HMDA reporting, NFIP affordability/reauthorization, "
        "first-time homebuyer and down-payment assistance, ADU financing, and secondary-"
        "market liquidity"
    ),
    "technology_emerging_issues": (
        "Technology & Emerging Issues (section: Payment & Technology): central bank "
        "digital currency, digital assets/digital commodities and cryptocurrency custody, "
        "remote online notarization, open banking, fintech partnerships, and AI/ML in "
        "credit underwriting"
    ),
}

# ---- Dispositions reached by reading each measure's own official evidence -------------

INCLUDE = {
    "117:hr:3962": ("SECURE Notarization Act of 2022 -- the measure named in this category's "
                    "agenda. Operative text authorises notaries public to perform electronic and "
                    "remote notarizations for remotely located individuals and compels Federal and "
                    "State recognition. Remote online notarization is an enumerated category term.",
                    "high"),
    "118:hr:1059": ("SECURE Notarization Act of 2023 -- same named measure, later Congress. "
                    "Operative text authorises electronic and remote notarization and compels "
                    "recognition. Remote online notarization is an enumerated category term.",
                    "high"),
    "116:hr:8378": ("Securities Clarity Act. Operative text amends the securities laws to carve "
                    "investment contract assets out of the definition of a security, addressed on "
                    "its face to digital assets raised through blockchain-based protocols. Digital-"
                    "asset market structure is core category subject matter.", "medium"),
    "117:hr:4451": ("Securities Clarity Act (117th). Operative text excludes investment contract "
                    "assets from the security definition, expressly for digital assets and "
                    "blockchain-based protocols. Digital-asset market structure is core category "
                    "subject matter.", "medium"),
    "118:hr:3572": ("Securities Clarity Act (118th). Operative text excludes investment contract "
                    "assets from the security definition, expressly for digital assets and "
                    "blockchain-based protocols. Digital-asset market structure is core category "
                    "subject matter.", "medium"),
    "119:hr:2365": ("Securities Clarity Act of 2025. Operative text defines the carve-out by "
                    "reference to value recorded on a cryptographically secured public distributed "
                    "ledger. Digital-asset market structure is core category subject matter.",
                    "medium"),
    "117:hr:5082": ("Cryptocurrency Tax Clarity Act. Operative text amends IRC s.6045 to define "
                    "'digital asset' as value recorded on a cryptographically secured distributed "
                    "ledger and to treat digital assets as specified securities for broker "
                    "reporting. The regulated instrument is the digital asset itself.", "medium"),
}

BOUNDARY_FLAG = {
    "117:hr:9522": ("Strengthening Housing Supply Act of 2022. Sole operative section makes "
                    "affordable housing construction an eligible CDBG activity -- housing "
                    "production, with no mortgage-credit, insurance, secondary-market or credit "
                    "union provision. The category label includes 'Housing' while every boundary "
                    "term and named bill is mortgage-credit, so neither the include nor the "
                    "exclude test is affirmatively met.", "medium"),
    "118:hr:6948": ("Strengthening Housing Supply Act of 2024 -- identical single-section CDBG "
                    "affordable-housing-construction eligibility change. Same unresolved "
                    "'Housing' vs mortgage-credit boundary question.", "medium"),
    "119:hr:5077": ("Strengthening Housing Supply Act of 2025 -- identical single-section CDBG "
                    "affordable-housing-construction eligibility change. Same unresolved "
                    "'Housing' vs mortgage-credit boundary question.", "medium"),
    "119:hr:4659": ("Identifying Regulatory Barriers to Housing Supply Act. Operative text "
                    "requires CDBG grantees to file land-use plans tracking burdensome zoning, "
                    "expressly including accessory dwelling units. 'ADU financing' is a boundary "
                    "term but this measure regulates land use, not financing.", "medium"),
    "119:s:2416": ("Identifying Regulatory Barriers to Housing Supply Act (Senate companion). "
                   "Operative text requires CDBG grantee land-use plans covering accessory "
                   "dwelling units; regulates land use, not financing.", "medium"),
    "119:hr:8185": ("HELP Act of 2026 (Housing Emergencies Lifeline Program Act). Operative text "
                    "creates an eviction database, eviction-prevention grants, and limits housing "
                    "court records in consumer reports. Rental/eviction policy sits inside the "
                    "'Housing' label but outside every mortgage-credit boundary term; mortgage "
                    "appears only in definitional exclusions.", "medium"),
    "118:hr:6307": ("CLARITY Act of 2023. Operative text bans Federal acquisition of covered "
                    "distributed ledger technology and blockchain equipment from foreign "
                    "adversaries and orders reports. The measure's primary subject IS an "
                    "enumerated emerging technology, but the policy domain is national-security "
                    "procurement rather than credit union payment/technology policy.", "medium"),
}

GATE_FLAG_NOTE = (
    "Operative-text review cannot be certified complete for this candidate "
    "(exclude_all_version_review_complete=false), so an affirmative exclusion is "
    "withheld and the edge remains flagged. Absence is neutral."
)


def sha256_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    cards = {}
    with (WORK / "review_cards.ndjson").open(encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            cards[(c["canonical_key"], c["query_id"])] = c

    edges = []
    with CLASSIFICATION.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("_record") == "header":
                continue
            edges.append(r)

    sidecar = {}
    with (SIDECAR_DIR / "short_act_collision_sidecar.ndjson").open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                sidecar[(r["canonical_key"], r["query_id"])] = r

    amd = {}
    with AMD_CONTENT.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            amd[r["canonical_key"]] = r

    rows, flagged, amendment_rows = [], [], []
    for e in edges:
        ck, qid = e["canonical_key"], e["query_id"]
        c = cards[(ck, qid)]
        sc = sidecar.get((ck, qid))
        is_amd = c["record_kind"] == "amendment"
        a = amd.get(ck) if is_amd else None
        amd_text = None
        if a and a.get("amendment_text") not in (None, "None", ""):
            amd_text = a["amendment_text"]

        subject = (c["purpose"] or (c["summary"] or "").strip().split("\n")[0] or
                   (c["sections"][0] if c["sections"] else "") or c["title"] or "")
        subject = " ".join(str(subject).split())[:230]

        disposition = None
        reason = None
        confidence = None
        flag_kind = None

        if is_amd and not amd_text:
            disposition = "flagged"
            flag_kind = "no_own_operative_amendment_text"
            reason = (
                f"Amendment edge with no operative amendment text on the original-method "
                f"surface (text_unresolved_reason={a.get('text_unresolved_reason')}) and no "
                f"floor remarks. Rule: the amendment's own operative effect governs and the "
                f"parent bill ({a.get('amends')}) cannot transfer relevance. Absence is "
                f"neutral, so neither include nor exclude is available."
            )
            confidence = "n/a_evidence_absent"
        elif ck in INCLUDE and not is_amd:
            disposition = "include"
            reason, confidence = INCLUDE[ck]
        elif ck in BOUNDARY_FLAG and not is_amd:
            disposition = "flagged"
            flag_kind = "category_boundary_unresolved"
            reason, confidence = BOUNDARY_FLAG[ck]
        elif not is_amd and not c["all_version_review_complete"]:
            disposition = "flagged"
            flag_kind = "operative_text_review_incomplete"
            reason = (
                f"Stemmed '{c['probe_alias']}' title-alias probe supplied this edge. Official "
                f"title/subject: {subject}. No {qid} nexus was found in the reviewed text, but "
                f"{GATE_FLAG_NOTE} Blockers: {c['blockers'] or 'none declared'}."
            )
            confidence = "n/a_review_incomplete"
        elif is_amd:
            disposition = "exclude_false_positive"
            head = " ".join(amd_text.split())[:200]
            reason = (
                f"Amendment's own operative text (not the parent bill {a.get('amends')}) reads: "
                f"\"{head}\". That operative effect falls outside {CATEGORY_BOUNDARY[qid]}. The "
                f"edge arose only from the stemmed '{c['probe_alias']}' title-alias probe, which "
                f"is discovery provenance and not disposition evidence."
            )
            confidence = "high"
        else:
            disposition = "exclude_false_positive"
            reason = (
                f"Stemmed '{c['probe_alias']}' title-alias probe matched only the measure's name "
                f"form, never the category. Official title: '{c['title']}'. Operative subject: "
                f"{subject}. Complete operative-text review found no provision touching "
                f"{CATEGORY_BOUNDARY[qid]}; the measure affirmatively legislates on other subject "
                f"matter. Alias provenance is not disposition evidence."
            )
            ss = c["summary_status"]
            confidence = "medium" if ss == "available_pending_congress_gov_fetch" else "high"

        evidence_ids = [
            {"id": "official_title", "sha256": c["title_sha256"],
             "status": c["title_status"], "source_url": c["final_url"]},
            {"id": "official_summary", "sha256": c["summary_sha256"],
             "status": c["summary_status"]},
            {"id": "congress_gov_full_text", "sha256": c["full_text_sha256"],
             "status": c["text_status"], "bytes": c["text_bytes"],
             "archive_path": c["archive_path"],
             "extraction_receipt_path": c["extraction_receipt_path"]},
            {"id": "candidate_packet", "sha256": c["evidence_sha256"],
             "path": str(PACKET_DIR / "packets.ndjson")},
        ]
        if is_amd:
            evidence_ids.append({
                "id": "amendment_content_v2_record",
                "sha256": a.get("amendment_text_sha256"),
                "text_bytes": int(a.get("amendment_text_len") or 0),
                "path": str(AMD_CONTENT),
                "text_unresolved_reason": a.get("text_unresolved_reason"),
            })

        row = {
            "schema": "acu-short-act-collision-opus5-proposal-v1",
            "run_id": RUN_ID,
            "canonical_key": ck,
            "query_id": qid,
            "category_label": e.get("category_label"),
            "disposition": disposition,
            "flag_kind": flag_kind,
            "measure_kind": c["record_kind"],
            "measure_weight": 0.5 if is_amd else 1.0,
            "source_title_alias_probe_id": (
                (sc or {}).get("source_title_alias_probe_id")
                or ((e.get("supplying_title_alias_probes") or [None])[0])
            ),
            "probe_alias": c["probe_alias"],
            "probe_is_ambiguous_short_act": e.get("supplying_probe_is_ambiguous_short_act"),
            "short_act_guard_fired_on_ledger": e.get("short_act_guard_fired"),
            "provenance_restored_by_sidecar": (ck, qid) in sidecar,
            "alias_match_is_provenance_not_evidence": True,
            "evidence_ids": evidence_ids,
            "title_reviewed": bool(c["title"]) and c["title_status"] == "available",
            "official_summary_status": c["summary_status"],
            "operative_text_reviewed": bool(amd_text) if is_amd else True,
            "operative_text_review_complete": bool(c["all_version_review_complete"]),
            "absence_is_neutral": True,
            "parent_relevance_transfer_used": False,
            "reason": reason,
            "confidence": confidence,
            "automated_final_decision": False,
            "human_ratification_required": True,
        }
        if is_amd:
            row["amends_bill"] = c["amends_bill"]
            row["amendment_partition_identity"] = {
                "partition": "original_method_amendment_partition_3703",
                "partition_source": str(AMD_CONTENT),
                "partition_record_count": 3703,
                "join_key": "canonical_key",
                "dedupe_key": [ck, qid],
                "note": (
                    "This edge is also a member of the separate 3,703-amendment partition. "
                    "Reconcile on (canonical_key, query_id) so the same edge is counted once."
                ),
            }
        rows.append(row)
        if disposition == "flagged":
            flagged.append(row)
        if is_amd:
            amendment_rows.append(row)

    def write(name, data):
        p = LANE / name
        with p.open("w", encoding="utf-8", newline="\n") as fh:
            for r in data:
                fh.write(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n")
        return p

    rows.sort(key=lambda r: (r["query_id"], r["canonical_key"]))
    flagged.sort(key=lambda r: (r["query_id"], r["canonical_key"]))
    amendment_rows.sort(key=lambda r: (r["query_id"], r["canonical_key"]))

    write("proposal_adjudications_454.ndjson", rows)
    write("flagged_short_act_edges.ndjson", flagged)
    write("amendment_overlap_31.ndjson", amendment_rows)

    counts = {}
    for r in rows:
        counts[r["disposition"]] = counts.get(r["disposition"], 0) + 1
    print(json.dumps({
        "rows": len(rows),
        "bills": sum(1 for r in rows if r["measure_kind"] == "bill"),
        "amendments": sum(1 for r in rows if r["measure_kind"] == "amendment"),
        "dispositions": counts,
        "flagged": len(flagged),
    }, indent=1))


if __name__ == "__main__":
    main()
