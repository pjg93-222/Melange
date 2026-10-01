from __future__ import annotations

import collections
import json
import math
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


ROOT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")
WORKBOOK = ROOT / "Moneyball Main Version - Blended.xlsx"
FEC = ROOT / "fec"
sys.path.insert(0, str(FEC))

import moneyball_core as MC
from tier_util import legislative_press_tiers


NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "pr": "http://schemas.openxmlformats.org/package/2006/relationships",
}


def read_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
    return ["".join(t.text or "" for t in si.iterfind(".//m:t", NS)) for si in root]


def workbook_sheet_paths(zf: zipfile.ZipFile) -> dict[str, str]:
    workbook = ET.fromstring(zf.read("xl/workbook.xml"))
    rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    relmap = {
        rel.attrib["Id"]: rel.attrib["Target"].lstrip("/")
        for rel in rels.findall("pr:Relationship", NS)
    }
    out = {}
    for sheet in workbook.findall("m:sheets/m:sheet", NS):
        target = relmap[sheet.attrib[f"{{{NS['r']}}}id"]]
        if not target.startswith("xl/"):
            target = "xl/" + target
        out[sheet.attrib["name"]] = target
    return out


def read_sheet(
    zf: zipfile.ZipFile, path: str, shared: list[str]
) -> tuple[dict[str, object], dict[str, str]]:
    values: dict[str, object] = {}
    formulas: dict[str, str] = {}
    root = ET.fromstring(zf.read(path))
    for cell in root.findall(".//m:sheetData/m:row/m:c", NS):
        ref = cell.attrib["r"]
        cell_type = cell.attrib.get("t")
        fnode = cell.find("m:f", NS)
        vnode = cell.find("m:v", NS)
        inode = cell.find("m:is", NS)
        if fnode is not None and fnode.text is not None:
            formulas[ref] = fnode.text
        if cell_type == "inlineStr" and inode is not None:
            values[ref] = "".join(t.text or "" for t in inode.iterfind(".//m:t", NS))
            continue
        if vnode is None:
            continue
        raw = vnode.text or ""
        if cell_type == "s":
            values[ref] = shared[int(raw)]
        elif cell_type == "b":
            values[ref] = raw == "1"
        elif cell_type in ("str", "e"):
            values[ref] = raw
        else:
            try:
                number = float(raw)
                values[ref] = int(number) if number.is_integer() else number
            except ValueError:
                values[ref] = raw
    return values, formulas


def cell(values: dict[str, object], col: str, row: int):
    return values.get(f"{col}{row}")


def weighted_value(category_map: dict[str, str]) -> float | None:
    sw = 0.0
    si = 0.0
    for category, tier in category_map.items():
        if tier in MC.TORD:
            weight = MC.IMP.get(category, 0.5)
            sw += MC.TORD[tier] * weight
            si += weight
    if not si:
        return None
    return sw / si + MC.overall_rounding(category_map)


def spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 3:
        return None

    def ranks(values):
        order = sorted(range(len(values)), key=values.__getitem__)
        out = [0.0] * len(values)
        i = 0
        while i < len(order):
            j = i + 1
            while j < len(order) and values[order[j]] == values[order[i]]:
                j += 1
            rank = (i + j - 1) / 2.0
            for k in range(i, j):
                out[order[k]] = rank
            i = j
        return out

    rx, ry = ranks(xs), ranks(ys)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    vx = sum((a - mx) ** 2 for a in rx)
    vy = sum((b - my) ** 2 for b in ry)
    return cov / math.sqrt(vx * vy) if vx and vy else None


category_doc = json.loads((ROOT / "category_stance.json").read_text(encoding="utf-8"))
matrix = category_doc["matrix"]
categories = category_doc["cats"]
tier1, tier_rank = legislative_press_tiers(list(matrix), root=str(ROOT))

with zipfile.ZipFile(WORKBOOK) as zf:
    shared = read_shared_strings(zf)
    sheet_paths = workbook_sheet_paths(zf)
    category_values, category_formulas = read_sheet(
        zf, sheet_paths["Category Stance"], shared
    )
    rank_values, rank_formulas = read_sheet(
        zf, sheet_paths["Rank & Allocation"], shared
    )

    formula_errors = []
    cached_errors = []
    formula_cells = 0
    for sheet_name, path in sheet_paths.items():
        xml = zf.read(path).decode("utf-8", errors="replace")
        formula_cells += len(re.findall(r"<f(?:\s|>)", xml))
        for match in re.finditer(r'<c\b[^>]*\br="([^"]+)"[^>]*>.*?<f[^>]*>(.*?)</f>', xml, re.S):
            if "#REF!" in match.group(2) or "#NAME?" in match.group(2):
                formula_errors.append([sheet_name, match.group(1), match.group(2)[:300]])
        for match in re.finditer(r'<c\b[^>]*\br="([^"]+)"[^>]*\bt="e"[^>]*>.*?<v>(.*?)</v>', xml, re.S):
            cached_errors.append([sheet_name, match.group(1), match.group(2)])

headers = [cell(category_values, chr(ord("A") + i), 1) for i in range(20)]
category_columns = {headers[i]: chr(ord("A") + i) for i in range(2, 20)}
category_rows = {}
for row in range(2, 539):
    member = cell(category_values, "A", row)
    if not member:
        continue
    category_rows[str(member)] = {
        "row": row,
        "general": cell(category_values, "B", row),
        "matrix": {
            category: cell(category_values, column, row)
            for category, column in category_columns.items()
        },
    }

rank_rows = {}
for row in range(3, 536):
    member = cell(rank_values, "A", row)
    if member:
        rank_rows[str(member)] = {
            "row": row,
            "general": cell(rank_values, "G", row),
        }

display_expected = {
    member: MC.overall_display_tier(
        matrix.get(member, {}),
        tier1.get(member, 0),
        member,
        (category_doc.get("gate") or {}).get("overall_capped") or {},
    )
    for member in matrix
}
base_expected = {
    member: MC.overall_tier(matrix.get(member, {}), member)
    for member in matrix
}
overall_values = {
    member: weighted_value(matrix.get(member, {}))
    for member in matrix
}

category_general_vs_rank = []
category_general_vs_expected = []
rank_vs_expected = []
category_cell_mismatches = []
for member, expected in display_expected.items():
    cat_general = category_rows.get(member, {}).get("general")
    rank_general = rank_rows.get(member, {}).get("general")
    if cat_general != rank_general:
        category_general_vs_rank.append(
            [member, category_rows.get(member, {}).get("row"), cat_general,
             rank_rows.get(member, {}).get("row"), rank_general]
        )
    if cat_general != expected:
        category_general_vs_expected.append(
            [member, category_rows.get(member, {}).get("row"), cat_general,
             expected, base_expected[member], overall_values[member], tier1.get(member, 0)]
        )
    if rank_general != expected:
        rank_vs_expected.append(
            [member, rank_rows.get(member, {}).get("row"), rank_general,
             expected, base_expected[member], overall_values[member], tier1.get(member, 0)]
        )
    for category in categories:
        workbook_value = category_rows.get(member, {}).get("matrix", {}).get(category)
        json_value = matrix.get(member, {}).get(category)
        if workbook_value != json_value:
            category_cell_mismatches.append(
                [member, category_rows.get(member, {}).get("row"), category,
                 workbook_value, json_value]
            )

legacy_tiers = {"Neutral", "Unengaged"}
current_tiers = set(MC.TORD) | {"—"}
category_general_distribution = collections.Counter(
    row["general"] for row in category_rows.values()
)
rank_general_distribution = collections.Counter(
    row["general"] for row in rank_rows.values()
)
expected_distribution = collections.Counter(display_expected.values())
base_distribution = collections.Counter(base_expected.values())

stale_by_category = collections.Counter(item[2] for item in category_cell_mismatches)
stale_by_member = collections.Counter(item[0] for item in category_cell_mismatches)

old_general_order = {
    "Champion": 4,
    "Defender": 4,
    "Ally": 3,
    "Highly Persuadable": 2,
    "Persuadable": 1,
    "Lean Persuadable": 0.5,
    "Neutral": 0,
    "True Neutral": 0,
    "Unengaged": 0,
    "Lean Skeptic": -0.5,
    "Skeptic": -1,
    "Highly Skeptical": -2,
    "Opponent": -4,
    "—": 0,
    None: 0,
}
paired = [
    (old_general_order.get(category_rows[m]["general"], 0), overall_values[m])
    for m in matrix
    if m in category_rows and overall_values[m] is not None
]

members_only_in_json = sorted(set(matrix) - set(category_rows))
members_only_in_category_sheet = sorted(set(category_rows) - set(matrix))
members_only_in_rank_sheet = sorted(set(rank_rows) - set(matrix))

coverage = {}
for category in categories:
    coverage[category] = {
        "json_nonmissing": sum(matrix[m].get(category) not in (None, "—") for m in matrix),
        "workbook_nonmissing": sum(
            category_rows.get(m, {}).get("matrix", {}).get(category) not in (None, "—")
            for m in matrix
        ),
        "mismatches": stale_by_category[category],
    }

report = {
    "workbook": str(WORKBOOK),
    "workbook_mtime": WORKBOOK.stat().st_mtime,
    "category_json_mtime": (ROOT / "category_stance.json").stat().st_mtime,
    "counts": {
        "json_members": len(matrix),
        "category_sheet_members": len(category_rows),
        "rank_sheet_members": len(rank_rows),
        "category_sheet_formulas": len(category_formulas),
        "rank_sheet_formulas": len(rank_formulas),
        "all_workbook_formula_cells": formula_cells,
        "category_general_vs_rank": len(category_general_vs_rank),
        "category_general_vs_expected": len(category_general_vs_expected),
        "rank_vs_expected": len(rank_vs_expected),
        "category_cell_mismatches": len(category_cell_mismatches),
        "members_with_category_cell_mismatches": len(stale_by_member),
        "formula_ref_or_name_errors": len(formula_errors),
        "cached_formula_errors": len(cached_errors),
    },
    "headers": headers,
    "distributions": {
        "category_sheet_general": dict(category_general_distribution),
        "rank_sheet_general": dict(rank_general_distribution),
        "expected_display": dict(expected_distribution),
        "expected_base": dict(base_distribution),
    },
    "taxonomy": {
        "legacy_labels_on_category_sheet": {
            tier: category_general_distribution[tier] for tier in sorted(legacy_tiers)
        },
        "unexpected_current_labels_on_category_sheet": sorted(
            tier for tier in category_general_distribution
            if tier not in current_tiers
        ),
    },
    "correlation": {
        "category_sheet_general_vs_current_weighted_matrix_spearman": (
            spearman([x for x, _ in paired], [y for _, y in paired])
        ),
    },
    "members_only_in_json": members_only_in_json,
    "members_only_in_category_sheet": members_only_in_category_sheet,
    "members_only_in_rank_sheet": members_only_in_rank_sheet,
    "coverage": coverage,
    "samples": {
        "category_general_vs_rank": category_general_vs_rank[:30],
        "category_general_vs_expected": sorted(
            category_general_vs_expected,
            key=lambda x: (
                -(abs((x[5] or 0))),
                x[0],
            ),
        )[:50],
        "rank_vs_expected": rank_vs_expected[:50],
        "category_cell_mismatches": category_cell_mismatches[:80],
        "members_most_category_mismatches": stale_by_member.most_common(30),
        "formula_errors": formula_errors[:50],
        "cached_errors": cached_errors[:50],
    },
}

print(json.dumps(report, indent=2, ensure_ascii=False))
