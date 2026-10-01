# -*- coding: utf-8 -*-
"""Re-derive the Institutional Influence view from its five raw source columns.

The normalized source block's headers were shifted one column right, its last column duplicated
Party Leadership, and Sub Layer - Raw carried one stale all-zero row for Juan Vargas.  This repair
materializes a coherent source block and then copies it into the display plane:

  Legislative Raw EI:EM -> Legislative Normalized EI:EM -> Sub Layer Raw AX:BB

Column EN is retained as a named reserved table column (rather than a duplicate Party Leadership
field) because the normalized Excel table spans it.  No score/rank input is changed.

Usage: python fec/repair_institutional_influence.py [--dry-run]
"""
import datetime
import os
import shutil
import sys

import openpyxl

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from moneyball_core import save_workbook_atomic
from paths import BACKUPS, WORKBOOK

RAW_SHEET = "Legislative Score - Raw"
NORM_SHEET = "Legislative Score - Normalized"
DISPLAY_SHEET = "Sub Layer - Raw"
FIRST_RAW_ROW, LAST_RAW_ROW = 3, 535
FIRST_DISPLAY_ROW, LAST_DISPLAY_ROW = 4, 536
RAW_COLS = tuple(range(139, 144))       # EI:EM
NORM_COLS = tuple(range(139, 144))      # EI:EM
DISPLAY_COLS = tuple(range(50, 55))     # AX:BB
RESERVED_COL = 144                      # EN; inside Table7, no raw counterpart
HEADERS = (
    "Relevant Committee Positions",
    "Leadership Positions",
    "Caucus Positions",
    "Caucus Leadership",
    "Party Leadership",
)
RAW_HEADERS = (
    "Relevant Committee Positions",
    "Leadership Positions",
    "Caucus_Positions",
    "Caucus_Leadership",
    "Party_Leadership",
)
RESERVED_HEADER = "Institutional Influence - Reserved"


def _guard_not_locked():
    lock = os.path.join(os.path.dirname(WORKBOOK), "~$" + os.path.basename(WORKBOOK))
    if os.path.exists(lock):
        raise RuntimeError("Excel lock file present; close the workbook first: %s" % lock)


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise TypeError("expected numeric Institutional Influence source, got %r" % (value,))
    return float(value)


def main():
    dry_run = "--dry-run" in sys.argv
    _guard_not_locked()
    wb = openpyxl.load_workbook(WORKBOOK, data_only=False)
    raw = wb[RAW_SHEET]
    norm = wb[NORM_SHEET]
    display = wb[DISPLAY_SHEET]

    got_raw_headers = tuple(raw.cell(1, column).value for column in RAW_COLS)
    if got_raw_headers != RAW_HEADERS:
        wb.close()
        raise RuntimeError("raw Institutional Influence headers drifted: %r" % (got_raw_headers,))

    for raw_row, display_row in zip(
        range(FIRST_RAW_ROW, LAST_RAW_ROW + 1),
        range(FIRST_DISPLAY_ROW, LAST_DISPLAY_ROW + 1),
    ):
        if str(raw.cell(raw_row, 1).value or "").strip() != str(display.cell(display_row, 2).value or "").strip():
            wb.close()
            raise RuntimeError("member row map mismatch at raw %d / display %d" % (raw_row, display_row))

    expected = {}
    for raw_col, norm_col, display_col in zip(RAW_COLS, NORM_COLS, DISPLAY_COLS):
        values = [_number(raw.cell(row, raw_col).value) for row in range(FIRST_RAW_ROW, LAST_RAW_ROW + 1)]
        minimum, maximum = min(values), max(values)
        normalized = [0.0 if maximum == minimum else (value - minimum) / (maximum - minimum)
                      for value in values]
        expected[(norm_col, display_col)] = normalized

    norm_changes = display_changes = 0
    for (norm_col, display_col), values in expected.items():
        for offset, raw_row in enumerate(range(FIRST_RAW_ROW, LAST_RAW_ROW + 1)):
            want = values[offset]
            current_norm = norm.cell(raw_row, norm_col).value
            current_display = display.cell(raw_row + 1, display_col).value
            if not isinstance(current_norm, (int, float)) or abs(float(current_norm) - want) > 1e-12:
                norm_changes += 1
            if not isinstance(current_display, (int, float)) or abs(float(current_display) - want) > 1e-12:
                display_changes += 1

    print("Institutional Influence repair")
    print("  normalized source cells changing:", norm_changes)
    print("  display cells changing          :", display_changes)
    print("  Juan Vargas expected            :", [
        expected[(norm_col, display_col)][271 - FIRST_RAW_ROW]
        for norm_col, display_col in zip(NORM_COLS, DISPLAY_COLS)
    ])
    print("  source mapping                  : Raw EI:EM -> Norm EI:EM -> Sub AX:BB")
    if dry_run:
        wb.close()
        print("--dry-run: no file written.")
        return 0

    os.makedirs(BACKUPS, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = os.path.join(
        BACKUPS,
        os.path.basename(WORKBOOK).replace(".xlsx", ".PRE-INSTITUTIONAL-%s.xlsx" % timestamp),
    )
    shutil.copy2(WORKBOOK, backup)
    print("  backup                         :", backup)

    for column, header in zip(NORM_COLS, HEADERS):
        norm.cell(1, column).value = header
    norm.cell(1, RESERVED_COL).value = RESERVED_HEADER
    for row in range(FIRST_RAW_ROW, LAST_RAW_ROW + 1):
        norm.cell(row, RESERVED_COL).value = None

    table = norm.tables["Table7"]
    for column, header in zip(NORM_COLS, HEADERS):
        table.tableColumns[column - 1].name = header
    table.tableColumns[RESERVED_COL - 1].name = RESERVED_HEADER

    for (norm_col, display_col), values in expected.items():
        for offset, raw_row in enumerate(range(FIRST_RAW_ROW, LAST_RAW_ROW + 1)):
            value = values[offset]
            norm.cell(raw_row, norm_col).value = value
            display.cell(raw_row + 1, display_col).value = value

    wb.calculation.fullCalcOnLoad = True
    save_workbook_atomic(wb, WORKBOOK)
    print("SAVED: coherent Institutional Influence source and display blocks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
