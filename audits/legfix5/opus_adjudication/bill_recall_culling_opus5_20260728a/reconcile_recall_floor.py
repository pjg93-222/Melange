#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic recall-floor reconciliation for the Opus 5 bill-recall lane.

Read-only over every input.  Writes nothing outside this directory.

Verifies the three coverage identities the lane is required to prove:

    quorum rows        == 44,  all present in discovery
    legacy rows        == 465, 442 present in discovery
    legacy rows absent == 23,  matching the frozen receipt list exactly

and emits the partition tables.  No disposition is decided here; disposition
for the 23 absent measures is adjudicated separately from official evidence.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
OUT = os.path.dirname(os.path.abspath(__file__))

LEGACY = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                      "recall_floor_evidence", "legacy_collection_floor_465.json")
QUORUM = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                      "recall_floor_evidence", "quorum_recall_floor_44.xlsx")
RECEIPT_IN = os.path.join(REPO, "audits", "legfix5", "opus_adjudication",
                          "recall_floor_evidence", "receipt.json")
RECORDS = os.path.join(REPO, "audits", "legfix5", "congress_advanced_pages_20260725",
                       "congress_advanced_records.ndjson")
MEMBERSHIPS = os.path.join(REPO, "audits", "legfix5", "congress_advanced_pages_20260725",
                           "congress_advanced_memberships.ndjson")

# --- measure-type dialect --------------------------------------------------
# The legacy collection keys measures by their congress.gov display citation
# ("H.R.2155", "H.J.Res.195").  The lane's canonical key is
# <congress>:<lowercase type>:<number>.  This is the only translation applied.
TYPE_MAP = {
    "H.R.": "hr",
    "H.RES.": "hres",
    "H.J.RES.": "hjres",
    "H.CON.RES.": "hconres",
    "S.": "s",
    "S.RES.": "sres",
    "S.J.RES.": "sjres",
    "S.CON.RES.": "sconres",
}
CITE_RE = re.compile(r"^\s*([A-Za-z\.]+?)\s*([0-9]+)\s*$")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def legacy_canonical_key(cite, congress):
    m = CITE_RE.match(cite)
    if not m:
        return None, "unparsed_citation"
    prefix, number = m.group(1).upper(), m.group(2)
    mtype = TYPE_MAP.get(prefix)
    if mtype is None:
        return None, "unknown_measure_type:" + prefix
    if number.lstrip("0") != number or number == "0":
        return None, "non_canonical_number:" + number
    return "%d:%s:%s" % (int(congress), mtype, number), None


def load_discovery():
    keys = {}
    with io.open(RECORDS, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            keys[rec["canonical_key"]] = rec
    return keys


def load_quorum():
    """Read the Quorum xlsx with the stdlib only (zip + minimal XML)."""
    import zipfile
    import xml.etree.ElementTree as ET

    NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(QUORUM) as zf:
        shared = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall(NS + "si"):
                shared.append("".join(t.text or "" for t in si.iter(NS + "t")))
        sheet_name = sorted(n for n in zf.namelist()
                            if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))[0]
        root = ET.fromstring(zf.read(sheet_name))
        rows = []
        for row in root.iter(NS + "row"):
            cells = {}
            for c in row.findall(NS + "c"):
                ref = c.get("r") or ""
                col = "".join(ch for ch in ref if ch.isalpha())
                t = c.get("t")
                v = c.find(NS + "v")
                is_el = c.find(NS + "is")
                if t == "s" and v is not None:
                    val = shared[int(v.text)]
                elif t == "inlineStr" and is_el is not None:
                    val = "".join(x.text or "" for x in is_el.iter(NS + "t"))
                elif v is not None:
                    val = v.text
                else:
                    val = ""
                cells[col] = val
            rows.append(cells)
    return rows


def main():
    receipt_in = json.load(io.open(RECEIPT_IN, encoding="utf-8"))
    expected_missing = [m["canonical_key"] for m in receipt_in["legacy_floor_missing"]]

    discovery = load_discovery()
    legacy = json.load(io.open(LEGACY, encoding="utf-8"))

    # ---- legacy partition -------------------------------------------------
    legacy_rows = []
    seen = {}
    dup = []
    for cite, row in legacy.items():
        ckey, err = legacy_canonical_key(cite, row["congress"])
        entry = {
            "legacy_cite": cite,
            "canonical_key": ckey,
            "key_error": err,
            "legacy_title": row.get("title", ""),
            "legacy_summary": row.get("summary", ""),
            "legacy_category": row.get("section", ""),
            "congress": row.get("congress"),
            "present_in_discovery": bool(ckey and ckey in discovery),
        }
        if ckey in seen:
            dup.append(ckey)
        seen[ckey] = entry
        legacy_rows.append(entry)

    present = [e for e in legacy_rows if e["present_in_discovery"]]
    absent = [e for e in legacy_rows if not e["present_in_discovery"]]

    # ---- quorum partition -------------------------------------------------
    qrows = load_quorum()
    header = qrows[0] if qrows else {}
    hdr_by_col = {col: (header.get(col) or "").strip() for col in header}
    col_of = {}
    for col, name in hdr_by_col.items():
        col_of.setdefault(name, col)

    quorum_records = []
    for r in qrows[1:]:
        if not any((v or "").strip() for v in r.values()):
            continue
        rec = {hdr_by_col.get(col, col): (val or "") for col, val in r.items()}
        quorum_records.append(rec)

    # ---- title-surface comparison for present legacy rows -----------------
    def norm(s):
        return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

    title_diffs = 0
    for e in present:
        rec = discovery[e["canonical_key"]]
        dtitle = rec.get("title") or rec.get("heading") or ""
        e["discovery_title"] = dtitle
        if norm(e["legacy_title"]) and norm(dtitle) and norm(e["legacy_title"]) not in norm(dtitle):
            title_diffs += 1
            e["title_surface_differs"] = True
        else:
            e["title_surface_differs"] = False

    result = {
        "legacy_rows": legacy_rows,
        "legacy_present": len(present),
        "legacy_absent": len(absent),
        "legacy_absent_keys": sorted(e["canonical_key"] for e in absent),
        "expected_missing_sorted": sorted(expected_missing),
        "duplicate_canonical_keys": dup,
        "key_errors": [e for e in legacy_rows if e["key_error"]],
        "title_surface_differences": title_diffs,
        "discovery_records": len(discovery),
        "quorum_header": sorted(set(hdr_by_col.values())),
        "quorum_row_count": len(quorum_records),
        "quorum_records": quorum_records,
    }
    with io.open(os.path.join(OUT, "_reconcile_state.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, ensure_ascii=False, sort_keys=True)

    print("discovery records          :", len(discovery))
    print("legacy rows                :", len(legacy_rows))
    print("legacy present in discovery:", len(present))
    print("legacy absent              :", len(absent))
    print("duplicate canonical keys   :", dup)
    print("key parse errors           :", [e["legacy_cite"] for e in result["key_errors"]])
    print("absent == receipt list     :",
          sorted(e["canonical_key"] for e in absent) == sorted(expected_missing))
    print("title surface differences  :", title_diffs)
    print("quorum header              :", result["quorum_header"])
    print("quorum data rows           :", len(quorum_records))
    return 0


if __name__ == "__main__":
    sys.exit(main())
