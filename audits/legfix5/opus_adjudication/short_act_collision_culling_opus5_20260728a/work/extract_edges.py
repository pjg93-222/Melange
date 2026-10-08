# -*- coding: utf-8 -*-
"""Stream the 2.76 GB packet file once and pull only the short-act-collision keys.

Read-only against every binding input. Writes only under this lane's work/ dir.
The packet file is never copied or rewritten: we match the top-level
canonical_key with a cheap regex prefilter and json-parse only the hit lines.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

ROOT = pathlib.Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
LANE = ROOT / "audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a"
WORK = LANE / "work"
TEXT_DIR = WORK / "fulltext"

CLASSIFICATION = ROOT / "audits/legfix5/orphan_edge_classification_2026-07-27.ndjson"
SIDECAR = ROOT / "audits/legfix5/short_act_collision_sidecar/short_act_collision_sidecar.ndjson"
PACKETS = (
    ROOT
    / "audits/legfix5/opus_adjudication/packets"
    / "10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59"
    / "packets.ndjson"
)

CK_RE = re.compile(r'"canonical_key":\s*"([^"]+)"')


def load_edges():
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
    return edges


def load_sidecar():
    out = {}
    with SIDECAR.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out[(r["canonical_key"], r["query_id"])] = r
    return out


def main():
    edges = load_edges()
    sidecar = load_sidecar()
    keys = sorted({e["canonical_key"] for e in edges})
    keyset = set(keys)
    print(f"target edges={len(edges)} unique canonical_keys={len(keys)}", flush=True)

    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    found = {}
    scanned = 0
    with PACKETS.open(encoding="utf-8") as f:
        for line in f:
            scanned += 1
            if scanned % 2000 == 0:
                print(f"  scanned={scanned} found={len(found)}", flush=True)
            m = CK_RE.search(line)
            if not m:
                continue
            ck = m.group(1)
            if ck not in keyset:
                continue
            pkt = json.loads(line)
            # guard: the regex must have hit the TOP-LEVEL canonical_key
            assert pkt.get("canonical_key") == ck, (ck, pkt.get("canonical_key"))
            if ck in found:
                print(f"  DUPLICATE PACKET for {ck}", flush=True)
                continue

            oe = pkt.get("official_evidence") or {}
            ft = oe.get("congress_gov_full_text") or {}
            summ = oe.get("official_summary") or {}
            text = ft.get("text") or ""
            if text:
                (TEXT_DIR / f"{ck.replace(':', '_')}.txt").write_text(text, encoding="utf-8")

            slim = {
                "canonical_key": ck,
                "candidate": pkt.get("candidate"),
                "evidence_sha256": pkt.get("evidence_sha256"),
                "candidate_evidence_sha256": pkt.get("candidate_evidence_sha256"),
                "membership_count": pkt.get("membership_count"),
                "eligibility": pkt.get("eligibility"),
                "official_summary": summ,
                "full_text_meta": {k: v for k, v in ft.items() if k != "text"},
                "full_text_bytes": len(text),
                "full_text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest() if text else None,
                "memberships": pkt.get("memberships"),
                "category_slots": pkt.get("category_slots"),
                "other_official_evidence_keys": sorted(oe.keys()),
                "contextual_and_corroborative_evidence": pkt.get(
                    "contextual_and_corroborative_evidence"
                ),
            }
            found[ck] = slim
            if len(found) == len(keyset):
                print(f"  all keys found at line {scanned}; continuing to prove no dupes", flush=True)

    print(f"scan complete: lines={scanned} found={len(found)}/{len(keyset)}", flush=True)
    missing = sorted(keyset - set(found))
    if missing:
        print(f"MISSING {len(missing)}: {missing[:20]}", flush=True)

    with (WORK / "edge_packets_slim.ndjson").open("w", encoding="utf-8", newline="\n") as out:
        for ck in keys:
            if ck in found:
                out.write(json.dumps(found[ck], ensure_ascii=False, sort_keys=True) + "\n")

    meta = {
        "target_edges": len(edges),
        "unique_canonical_keys": len(keys),
        "packet_lines_scanned": scanned,
        "packets_found": len(found),
        "missing_keys": missing,
        "sidecar_covered_edges": sum(
            1 for e in edges if (e["canonical_key"], e["query_id"]) in sidecar
        ),
    }
    (WORK / "extract_meta.json").write_text(
        json.dumps(meta, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(meta, indent=1)[:2000], flush=True)


if __name__ == "__main__":
    main()
