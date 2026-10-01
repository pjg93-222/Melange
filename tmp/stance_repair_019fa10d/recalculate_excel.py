# -*- coding: utf-8 -*-
"""Open a repaired workbook in desktop Excel, fully recalculate, and save caches."""
from __future__ import annotations

import argparse
import os
import time

import win32com.client as win32


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook")
    args = parser.parse_args()
    path = os.path.abspath(args.workbook)
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    excel = win32.DispatchEx("Excel.Application")
    excel.Visible = False
    excel.DisplayAlerts = False
    excel.AskToUpdateLinks = False
    book = None
    try:
        book = excel.Workbooks.Open(path, UpdateLinks=0, ReadOnly=False)
        book.ForceFullCalculation = True
        excel.Calculation = -4105  # xlCalculationAutomatic
        excel.CalculateFullRebuild()
        deadline = time.time() + 600
        while excel.CalculationState != 0 and time.time() < deadline:
            time.sleep(0.25)
        if excel.CalculationState != 0:
            raise TimeoutError("Excel did not finish full calculation within 10 minutes")
        book.Save()
        cp = book.Worksheets("Coalition Profiles")
        print("COALITION_TOTAL_MEMBERS", cp.Range("B29").Value)
        print("COALITION_TOTAL_ALLOCATION", cp.Range("D29").Value)
        print("COALITION_TOTAL_FUNDED", cp.Range("F29").Value)
        print("DOMINANT_STANCES", [cp.Cells(row, 21).Value for row in range(4, 13)])
        print("EXCEL_RECALC_SAVED", path)
    finally:
        if book is not None:
            book.Close(SaveChanges=True)
        excel.Quit()


if __name__ == "__main__":
    main()
