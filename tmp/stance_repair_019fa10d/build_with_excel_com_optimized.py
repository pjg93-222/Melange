# -*- coding: utf-8 -*-
"""Build the final stance repair through desktop Excel for native compatibility."""
from __future__ import annotations

import argparse
import collections
import json
import os
import shutil
import sys
import time

import win32com.client as win32


GENERAL_TIERS = (
    "Champion", "Ally", "Highly Persuadable", "Persuadable",
    "Lean Persuadable", "True Neutral", "Lean Skeptic", "Skeptic",
    "Highly Skeptical", "Opponent", "—",
)
CATEGORY_TIERS = (
    "Champion", "Defender", "Ally", "Highly Persuadable", "Persuadable",
    "Lean Persuadable", "True Neutral", "Lean Skeptic", "Skeptic",
    "Highly Skeptical", "Opponent", "—",
)
COLORS = {
    "Champion": "63BE7B", "Defender": "2DD4BF", "Ally": "C6EFCE",
    "Highly Persuadable": "BDD7EE", "Persuadable": "D9EAF7",
    "Lean Persuadable": "FFF2CC", "True Neutral": "E7E7E7",
    "Lean Skeptic": "FCE4D6", "Skeptic": "FFC7CE",
    "Highly Skeptical": "F4B084", "Opponent": "F8696B", "—": "F2F2F2",
}


def excel_color(hex_color):
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[i:i + 2], 16) for i in (0, 2, 4))
    return red + green * 256 + blue * 65536


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    root = os.path.abspath(args.root)
    source = os.path.abspath(args.input)
    output = os.path.abspath(args.output)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    shutil.copy2(source, output)

    sys.path.insert(0, os.path.join(root, "fec"))
    from moneyball_core import overall_display_tier
    from tier_util import legislative_press_tiers

    category = json.load(open(os.path.join(root, "category_stance.json"), encoding="utf-8"))
    matrix = category["matrix"]
    caps = (category.get("gate") or {}).get("overall_capped") or {}
    tier, tier_rank = legislative_press_tiers(list(matrix))

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.AskToUpdateLinks = False
    excel.ScreenUpdating = False
    excel.EnableEvents = False
    book = None
    try:
        book = excel.Workbooks.Open(output, UpdateLinks=0, ReadOnly=False)
        excel.Calculation = -4135  # xlCalculationManual while editing
        ra = book.Worksheets("Rank & Allocation")
        members = [ra.Cells(row, 1).Value for row in range(3, 536) if ra.Cells(row, 1).Value]
        overall = {
            member: overall_display_tier(matrix.get(member, {}), tier.get(member, 0), member, caps)
            for member in members
        }
        champions = {member for member, stance in overall.items() if stance == "Champion"}
        tier_one = {member for member, value in tier.items() if value == 1}
        if champions != tier_one or len(champions) != 12:
            raise RuntimeError("Champion must exactly equal the tier-wise Tier 1 top 12")
        for row in range(3, 536):
            member = ra.Cells(row, 1).Value
            if member:
                ra.Cells(row, 7).Value = overall[member]

        # Current Category Stance matrix.
        cs = book.Worksheets("Category Stance")
        cs.Range("A1:T538").Clear()
        headers = ["Member", "General Stance", *category["cats"]]
        data = [headers]
        for member in members:
            data.append([
                member,
                overall[member],
                *[matrix[member].get(cat, "—") for cat in category["cats"]],
            ])
        cs.Range(cs.Cells(1, 1), cs.Cells(534, 20)).Value = data
        header = cs.Range("A1:T1")
        header.Interior.Color = excel_color("253A5A")
        header.Font.Color = excel_color("FFFFFF")
        header.Font.Bold = True
        header.HorizontalAlignment = -4108
        header.VerticalAlignment = -4108
        header.WrapText = True
        cs.Rows(1).RowHeight = 46
        body = cs.Range("A2:T534")
        body.Borders.LineStyle = 1
        body.Borders.Color = excel_color("E5E7EB")
        body.Font.Size = 9
        body.VerticalAlignment = -4108
        cs.Range("B2:T534").HorizontalAlignment = -4108
        cs.Columns(1).ColumnWidth = 24
        cs.Columns(2).ColumnWidth = 19
        cs.Range("C:T").ColumnWidth = 17
        colored = cs.Range("B2:T534")
        colored.FormatConditions.Delete()
        tier_addresses = {stance: [] for stance in CATEGORY_TIERS}
        for row, values in enumerate(data[1:], start=2):
            for col, stance in enumerate(values[1:], start=2):
                if stance in tier_addresses:
                    tier_addresses[stance].append(f"{chr(64 + col)}{row}")
        for stance, addresses in tier_addresses.items():
            for start in range(0, len(addresses), 150):
                target = cs.Range(",".join(addresses[start:start + 150]))
                target.Interior.Color = excel_color(COLORS[stance])
                if stance in ("Champion", "Opponent"):
                    target.Font.Bold = True
        cs.Range("A536:T536").Merge()
        cs.Range("A536").Value = "Legend — stance toward the CU position, by category"
        cs.Range("A536:T536").Interior.Color = excel_color("D9E2F3")
        cs.Range("A536:T536").Font.Bold = True
        cs.Range("A537:L537").Value = [list(CATEGORY_TIERS)]
        for col, stance in enumerate(CATEGORY_TIERS, start=1):
            cell = cs.Cells(537, col)
            cell.Interior.Color = excel_color(COLORS[stance])
            cell.HorizontalAlignment = -4108
            cell.Font.Bold = stance in ("Champion", "Opponent")
        cs.Range("A538:T538").Merge()
        cs.Range("A538").Value = (
            "Source: category_stance.json. General Stance matches Rank & Allocation column G. "
            "Overall Champion is reserved for Legislative+Press Tier 1 (top 12)."
        )
        cs.Range("A538:T538").Font.Italic = True
        if cs.AutoFilterMode:
            cs.AutoFilterMode = False
        cs.Range("A1:T534").AutoFilter()
        cs.Activate()
        excel.ActiveWindow.FreezePanes = False
        excel.ActiveWindow.SplitColumn = 2
        excel.ActiveWindow.SplitRow = 1
        excel.ActiveWindow.FreezePanes = True
        excel.ActiveWindow.DisplayGridlines = False

        # Coalition profile block and complete current tier summary.
        cp = book.Worksheets("Coalition Profiles")
        cp.Range("J3:U13").Clear()
        cp.Range("J3:T3").Value = [list(GENERAL_TIERS)]
        for col, stance in enumerate(GENERAL_TIERS, start=10):
            cell = cp.Cells(3, col)
            cell.Interior.Color = excel_color(COLORS[stance])
            cell.Font.Bold = True
            cell.HorizontalAlignment = -4108
            cell.WrapText = True
        cp.Cells(3, 21).Value = "Dominant Stance"
        cp.Cells(3, 21).Interior.Color = excel_color("253A5A")
        cp.Cells(3, 21).Font.Color = excel_color("FFFFFF")
        cp.Cells(3, 21).Font.Bold = True
        for row in range(4, 13):
            for col in range(10, 21):
                letter = chr(ord("J") + col - 10)
                cp.Cells(row, col).Formula = (
                    f"=COUNTIFS('Rank & Allocation'!$H$3:$H$535,$A{row},"
                    f"'Rank & Allocation'!$G$3:$G$535,{letter}$3)"
                )
            cp.Cells(row, 21).Formula = (
                f"=INDEX($J$3:$T$3,MATCH(MAX(J{row}:T{row}),J{row}:T{row},0))"
            )
        for col in range(10, 21):
            letter = chr(ord("J") + col - 10)
            cp.Cells(13, col).Formula = f"=SUM({letter}4:{letter}12)"
        cp.Range("J4:U13").Borders.LineStyle = 1
        cp.Range("J4:U13").Borders.Color = excel_color("E5E7EB")
        cp.Range("J4:U13").HorizontalAlignment = -4108
        cp.Range("J:T").ColumnWidth = 17
        cp.Columns(21).ColumnWidth = 20

        cp.Range("A16:F29").Clear()
        cp.Cells(16, 1).Value = "BY CURRENT CU-STANCE TIER"
        cp.Cells(16, 1).Font.Bold = True
        cp.Range("A17:F17").Value = [["Stance", "Members", "Mean Score", "Allocation", "% of Pot", "Funded"]]
        cp.Range("A17:F17").Interior.Color = excel_color("253A5A")
        cp.Range("A17:F17").Font.Color = excel_color("FFFFFF")
        cp.Range("A17:F17").Font.Bold = True
        for row, stance in enumerate(GENERAL_TIERS, start=18):
            cp.Cells(row, 1).Value = stance
            cp.Cells(row, 1).Interior.Color = excel_color(COLORS[stance])
            cp.Cells(row, 1).Font.Bold = True
            cp.Cells(row, 2).Formula = f"=COUNTIF('Rank & Allocation'!$G$3:$G$535,$A{row})"
            cp.Cells(row, 3).Formula = (
                f"=IFERROR(AVERAGEIF('Rank & Allocation'!$G$3:$G$535,$A{row},"
                f"'Blended Model'!$S$3:$S$535),0)"
            )
            cp.Cells(row, 4).Formula = (
                f"=SUMIFS('Blended Model'!$U$3:$U$535,'Rank & Allocation'!$G$3:$G$535,$A{row})"
            )
            cp.Cells(row, 5).Formula = f"=IFERROR(D{row}/'Blended Model'!$AB$6,0)"
            cp.Cells(row, 6).Formula = (
                f'=COUNTIFS(\'Rank & Allocation\'!$G$3:$G$535,$A{row},'
                f'\'Blended Model\'!$U$3:$U$535,">0")'
            )
        cp.Range("A18:F28").Borders.LineStyle = 1
        cp.Range("A18:F28").Borders.Color = excel_color("E5E7EB")
        cp.Cells(29, 1).Value = "TOTAL"
        cp.Cells(29, 2).Formula = "=SUM(B18:B28)"
        cp.Cells(29, 3).Formula = "=AVERAGE('Blended Model'!$S$3:$S$535)"
        cp.Cells(29, 4).Formula = "=SUM(D18:D28)"
        cp.Cells(29, 5).Formula = "=SUM(E18:E28)"
        cp.Cells(29, 6).Formula = "=SUM(F18:F28)"
        cp.Range("A29:F29").Interior.Color = excel_color("253A5A")
        cp.Range("A29:F29").Font.Color = excel_color("FFFFFF")
        cp.Range("A29:F29").Font.Bold = True
        cp.Range("B18:B29").NumberFormat = "0"
        cp.Range("C18:C29").NumberFormat = "0.000"
        cp.Range("D18:D29").NumberFormat = "$#,##0"
        cp.Range("E18:E29").NumberFormat = "0.0%"
        cp.Range("F18:F29").NumberFormat = "0"

        book.ForceFullCalculation = False
        excel.Calculation = -4105
        excel.ScreenUpdating = True
        excel.Calculate()
        deadline = time.time() + 120
        while excel.CalculationState != 0 and time.time() < deadline:
            time.sleep(0.10)
        if excel.CalculationState != 0:
            raise TimeoutError("Excel did not finish dirty-cell calculation within 2 minutes")
        book.Save()
        distribution = collections.Counter(overall.values())
        print("DISTRIBUTION", dict(distribution))
        print("CHAMPIONS", " | ".join(sorted(champions)))
        print("COALITION_TOTAL_MEMBERS", cp.Range("B29").Value)
        print("COALITION_TOTAL_ALLOCATION", cp.Range("D29").Value)
        print("COALITION_TOTAL_FUNDED", cp.Range("F29").Value)
        print("DOMINANT_STANCES", [cp.Cells(row, 21).Value for row in range(4, 13)])
        print("SAVED", output)
    finally:
        if book is not None:
            book.Close(SaveChanges=True)
        excel.Quit()


if __name__ == "__main__":
    main()
