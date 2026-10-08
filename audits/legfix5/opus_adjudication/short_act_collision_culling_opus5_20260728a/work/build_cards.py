# -*- coding: utf-8 -*-
"""Build one compact review card per edge for human/Opus semantic adjudication.

This surfaces evidence; it decides nothing. Term hits are recall probes into the
operative text so the reviewer can read the actual passage -- a hit is never a
disposition, and a miss is never negative evidence (absence is neutral).
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
LANE = ROOT / "audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a"
WORK = LANE / "work"
TEXT_DIR = WORK / "fulltext"
CLASSIFICATION = ROOT / "audits/legfix5/orphan_edge_classification_2026-07-27.ndjson"
SIDECAR = ROOT / "audits/legfix5/short_act_collision_sidecar/short_act_collision_sidecar.ndjson"

# Generous recall probes into the operative text, per ACU category boundary.
NEXUS = {
    "cdfi_fund": [
        "cdfi", "community development financial institution", "community development bank",
        "minority depository institution", "bond guarantee", "underserved",
        "community development revolving loan", "bank enterprise award", "riegle community",
        "low-income credit union", "native american lending", "community development fund",
        "credit union", "depository institution",
    ],
    "examination_supervision": [
        "examination", "examiner", "supervision", "supervisory", "camels", "ffiec",
        "safety and soundness", "call report", "currency transaction report",
        "suspicious activity report", "bank secrecy act", "reputational risk",
        "asset threshold", "regulatory relief", "tailor", "credit union", "ncua",
        "prudential regulator", "financial institutions examination",
    ],
    "fraud_prevention": [
        "fraud", "scam", "elder financial exploitation", "identity theft", "check fraud",
        "payment scam", "mail theft", "information sharing", "safe harbor", "credit union",
        "financial exploitation", "imposter", "romance",
    ],
    "mortgage_lending_housing": [
        "mortgage", "hmda", "home mortgage disclosure", "flood insurance", "nfip",
        "homebuyer", "home buyer", "down payment", "fha ", "federal housing administration",
        "accessory dwelling", "housing", "secondary market", "ginnie mae", "fannie mae",
        "freddie mac", "credit union", "appraisal", "real estate", "foreclosure",
        "loan originator",
    ],
    "technology_emerging_issues": [
        "central bank digital currency", "cbdc", "digital asset", "stablecoin",
        "cryptocurrency", "crypto", "notarization", "notary", "open banking", "fintech",
        "artificial intelligence", "machine learning", "algorithmic", "digital commodity",
        "blockchain", "credit union", "virtual currency", "distributed ledger",
    ],
}

SEC_RE = re.compile(r"^\s*(SEC(?:TION)?\.?\s+\d+[A-Za-z]?\s*\.\s*[^\n]{0,120})", re.M)
PURPOSE_RE = re.compile(r"\n(To [^\n]{10,400}?\.)\n", re.S)
SHORTTITLE_RE = re.compile(r"may be cited as the\s+[\u201c\"']?([^\u201d\"'\n]{3,160})", re.I)


def ctx(text, low, i, n, width=150):
    a = max(0, i - width)
    b = min(len(text), i + n + width)
    s = text[a:b].replace("\n", " ")
    return re.sub(r"\s+", " ", s).strip()


def main():
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
    with SIDECAR.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                r = json.loads(line)
                sidecar[(r["canonical_key"], r["query_id"])] = r

    slim = {}
    with (WORK / "edge_packets_slim.ndjson").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            slim[r["canonical_key"]] = r
    surf = {}
    with (WORK / "edge_surfaces.ndjson").open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            surf[r["canonical_key"]] = r

    cards = []
    for e in edges:
        ck, qid = e["canonical_key"], e["query_id"]
        p, s = slim[ck], surf[ck]
        text = (TEXT_DIR / f"{ck.replace(':', '_')}.txt").read_text(encoding="utf-8")
        low = text.lower()

        hits = []
        for t in NEXUS[qid]:
            start = 0
            c = 0
            while c < 3:
                i = low.find(t, start)
                if i < 0:
                    break
                hits.append({"term": t, "at": i, "ctx": ctx(text, low, i, len(t))})
                start = i + len(t)
                c += 1

        sc = sidecar.get((ck, qid))
        alias = (sc or {}).get("probe_alias") or (e.get("supplying_probe_aliases") or [None])[0]
        probe_id = (sc or {}).get("source_title_alias_probe_id") or (
            (e.get("supplying_title_alias_probes") or [None])[0]
        )

        title_obj = s.get("title") or {}
        summ = p.get("official_summary") or {}
        otv = s.get("official_text_versions") or {}

        cards.append({
            "canonical_key": ck,
            "query_id": qid,
            "category_label": e.get("category_label"),
            "record_kind": p["candidate"]["record_kind"],
            "measure_weight": p["candidate"].get("fixed_downstream_weight"),
            "display_number": p["candidate"].get("display_number"),
            "amends_bill": p["candidate"].get("amends_bill"),
            "sponsor": p["candidate"].get("sponsor_display"),
            "probe_alias": alias,
            "probe_id": probe_id,
            "guard_fired": e.get("short_act_guard_fired"),
            "in_sidecar": (ck, qid) in sidecar,
            "title_status": title_obj.get("status"),
            "title": title_obj.get("text"),
            "summary_status": summ.get("status"),
            "summary": (summ.get("text") or "")[:1800],
            "stage": (s.get("stage_and_actions") or {}).get("value"),
            "text_bytes": len(text),
            "text_status": p["full_text_meta"].get("status"),
            "purpose": (PURPOSE_RE.search(text[:6000]).group(1).strip()
                        if PURPOSE_RE.search(text[:6000]) else None),
            "short_title": (SHORTTITLE_RE.search(text).group(1).strip()
                            if SHORTTITLE_RE.search(text) else None),
            "sections": [m.group(1).strip() for m in SEC_RE.finditer(text)][:28],
            "alias_literal_in_text": (alias or "").lower() in low if alias else None,
            "nexus_hit_count": len(hits),
            "nexus_terms_hit": sorted({h["term"] for h in hits}),
            "nexus_hits": hits[:14],
            "exclude_all_version_review_complete": p["eligibility"].get(
                "exclude_all_version_review_complete"),
            "include_evidence_complete": p["eligibility"].get("include_evidence_complete"),
            "blockers": p["eligibility"].get("blockers") or [],
            "warnings": p["eligibility"].get("warnings") or [],
            "all_version_review_complete": otv.get("all_version_review_complete"),
            "expected_version_count": otv.get("expected_version_count"),
            "declared_reviewed_version_count": otv.get("declared_reviewed_version_count"),
            "evidence_sha256": p.get("evidence_sha256"),
            "full_text_sha256": p.get("full_text_sha256"),
            "summary_sha256": summ.get("text_sha256"),
            "title_sha256": title_obj.get("text_sha256"),
            "archive_path": p["full_text_meta"].get("archive_path"),
            "extraction_receipt_path": p["full_text_meta"].get("extraction_receipt_path"),
            "final_url": p["full_text_meta"].get("final_url"),
        })

    with (WORK / "review_cards.ndjson").open("w", encoding="utf-8", newline="\n") as fh:
        for c in cards:
            fh.write(json.dumps(c, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"cards={len(cards)}")


if __name__ == "__main__":
    main()
