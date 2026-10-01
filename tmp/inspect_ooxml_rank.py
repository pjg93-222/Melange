from __future__ import annotations

from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "fec"))

from legislation.extract_legislation_workbook_audited_layout import (  # noqa: E402
    OOXML_MAIN_NS,
    _ooxml_sheet_targets,
    _read_shared_strings,
)


WORKBOOK = (
    ROOT
    / "audits"
    / "legfix5"
    / "production_baseline_full_downstream"
    / "files"
    / "Moneyball Main Version - Blended.xlsx"
)


def cell_value(cell: ET.Element, shared: list[str]) -> str | None:
    value = cell.find(f"{{{OOXML_MAIN_NS}}}v")
    inline = cell.find(f"{{{OOXML_MAIN_NS}}}is")
    if inline is not None:
        return "".join(inline.itertext())
    if value is None:
        return None
    raw = value.text or ""
    if cell.get("t") == "s":
        return shared[int(raw)]
    return raw


with zipfile.ZipFile(WORKBOOK) as package:
    shared = _read_shared_strings(package)
    targets = _ooxml_sheet_targets(package)
    for sheet_name, addresses in {
        "Blended Model": {
            "A1", "A2", "A3",
            "B2", "B3", "C2", "C3", "D2", "D3", "E2", "E3",
            "F2", "F3", "G2", "G3", "H2", "H3",
            "I2", "I3", "J2", "J3", "K2", "K3", "L2", "L3",
            "M2", "M3", "N2", "N3", "O1", "O2", "O3",
            "P2", "P3", "Q2", "Q3", "R2", "R3", "S1", "S2", "S3",
            "T1", "T2", "T3", "AB2", "AB3", "AB4", "AB5",
            "AB10", "AB11",
        },
        "Rank & Allocation": {"A1", "A2", "A3", "B1", "B2", "B3"},
        "Primary Layer": {
            "A1", "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3",
            "D1", "D2", "D3", "E1", "E2", "E3", "F1", "F2", "F3",
        },
        "Sub Layer - Normalized": {
            "A1", "A2", "A3", "A4", "B1", "B2", "B3", "B4",
            "C1", "C2", "C3", "C4", "D1", "D2", "D3", "D4",
            "E1", "E2", "E3", "E4", "F1", "F2", "F3", "F4",
            "AG1", "AG2", "AG3", "AG4", "AW1", "AW2", "AW3", "AW4",
        },
    }.items():
        root = ET.fromstring(package.read(targets[sheet_name]))
        print(sheet_name)
        for cell in root.findall(
            f".//{{{OOXML_MAIN_NS}}}sheetData/"
            f"{{{OOXML_MAIN_NS}}}row/"
            f"{{{OOXML_MAIN_NS}}}c"
        ):
            address = str(cell.get("r") or "").upper()
            if address not in addresses:
                continue
            formula = cell.find(f"{{{OOXML_MAIN_NS}}}f")
            print(
                address,
                "formula=" + ((formula.text or "") if formula is not None else ""),
                "value=" + str(cell_value(cell, shared)),
            )
