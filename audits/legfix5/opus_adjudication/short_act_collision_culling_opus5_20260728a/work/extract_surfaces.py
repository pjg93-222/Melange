# -*- coding: utf-8 -*-
"""Second read-only pass: capture the official title / status / version surfaces.

Pass 1 kept summary + full text. The disposition record also needs the official
title surface (title_reviewed) and the stage/actions surface
(official_summary_status), plus the declared text-version inventory that governs
whether an all-version review is even possible.
"""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
LANE = ROOT / "audits/legfix5/opus_adjudication/short_act_collision_culling_opus5_20260728a"
WORK = LANE / "work"
PACKETS = (
    ROOT
    / "audits/legfix5/opus_adjudication/packets"
    / "10ddf7efa28bcd26a8ee3e805133f57c73078050585122152a09c29978cf8b59"
    / "packets.ndjson"
)
CK_RE = re.compile(r'"canonical_key":\s*"([^"]+)"')


def main():
    keys = set()
    with (WORK / "edge_packets_slim.ndjson").open(encoding="utf-8") as f:
        for line in f:
            keys.add(json.loads(line)["canonical_key"])
    print(f"targets={len(keys)}", flush=True)

    out = {}
    scanned = 0
    with PACKETS.open(encoding="utf-8") as f:
        for line in f:
            scanned += 1
            m = CK_RE.search(line)
            if not m or m.group(1) not in keys:
                continue
            pkt = json.loads(line)
            ck = pkt["canonical_key"]
            oe = pkt.get("official_evidence") or {}
            out[ck] = {
                "canonical_key": ck,
                "title": oe.get("title"),
                "stage_and_actions": oe.get("stage_and_actions"),
                "official_text_versions": oe.get("official_text_versions"),
                "relationship_roles": oe.get("relationship_roles"),
            }
            if scanned % 4000 == 0:
                print(f"  scanned={scanned} found={len(out)}", flush=True)

    print(f"done lines={scanned} found={len(out)}/{len(keys)}", flush=True)
    with (WORK / "edge_surfaces.ndjson").open("w", encoding="utf-8", newline="\n") as fh:
        for ck in sorted(out):
            fh.write(json.dumps(out[ck], ensure_ascii=False, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
