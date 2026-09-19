"""Console-reader proof: run the LIVE Mentat reader over the mock workbook.

Imports `app/report_insights.py` and `app/contribution_data.py` from the live
working tree read-only and calls exactly what the console calls -
`worksheet_data(stamp(path), sheet, 0)` (`app/server.py`:1761) - on every sheet,
then `contribution_data._workbook_source(...)` for the pinned source lineage.

Nothing is written to the Mentat tree and no console port is touched.
"""
from __future__ import annotations

import sys
import time
import traceback
from pathlib import Path

APP = r"C:\Users\pgoff\Mentat\mentat\app"
if APP not in sys.path:
    sys.path.insert(0, APP)

import report_insights                                    # noqa: E402
import contribution_data                                  # noqa: E402

MOCK = (Path(__file__).parent / "out"
        / "Credit Union Industry Spending Data (MOCK).xlsx")

# What the sheet must look like to the reader once it has parsed it.
EXPECTED_TYPES = {
    "Date": "date", "First Gift Date": "date", "Last Gift Date": "date",
    "First Activity Date": "date", "Last Activity Date": "date",
    "Include in Analysis": "category", "Memo Leg": "category",
    "Conduit Leg": "category", "Superseded Amendment": "category",
    "Duplicate Filing Version": "category", "Duplicate Memo": "category",
    "Passed": "category", "Has Support Activity": "category",
    "Has Oppose Activity": "category",
    "Giving": "number", "Amount": "number", "Analysis Amount": "number",
    "Reported Amount": "number", "Net Included Amount": "number",
    "Downstream Activity": "number", "Associated Funding": "number",
    "Gift Count": "number", "Distinct Contributors": "number",
}
CURRENCY = {"Giving", "Amount", "Analysis Amount", "Reported Amount",
            "Net Included Amount", "Downstream Activity", "Associated Funding",
            "Excluded Amount", "Top Downstream Activity", "Conditional Estimate",
            "Reported Net Transfer"}


def check(condition, message, failures, sheet):
    if not condition:
        failures.append(f"{sheet}: {message}")
    return condition


def main():
    report = []
    failures = []
    started = time.time()
    file_stamp = report_insights.stamp(MOCK)
    listing = report_insights.worksheet_data(file_stamp)
    sheets = listing["sheets"]
    report.append(f"workbook: {MOCK}")
    report.append(f"bytes: {MOCK.stat().st_size:,}")
    report.append(f"sha256 (reader): {listing['sha256']}")
    report.append(f"sheets: {len(sheets)}")
    report.append("")
    header = (f"{'sheet':<32}{'hdr':>4}{'rows':>9}{'cols':>6}  "
              f"{'safe_to_sum':<12}{'grain':<26}note/status")
    report.append(header)
    report.append("-" * len(header))

    def emit(line):
        report.append(line)
        print(line, flush=True)
        (Path(__file__).parent / "reader_check.txt").write_text(
            chr(10).join(report), encoding="utf-8")

    for line in report:
        print(line, flush=True)
    for name in sheets:
        sheet_started = time.time()
        # The console keeps report_insights' lru_cache of six sheet payloads; a
        # 22-sheet sweep in one process would hold six of them at once, so the
        # cache is cleared between sheets to keep this harness inside memory.
        report_insights.worksheet_data.cache_clear()
        try:
            data = report_insights.worksheet_data(file_stamp, name, 0)
        except ValueError as error:
            emit(f"{name:<32}{'-':>4}{'-':>9}{'-':>6}  "
                 f"{'-':<12}{'-':<26}REFUSED after {time.time()-sheet_started:.0f}s: "
                 f"{error}")
            failures.append(f"{name}: reader refused the sheet - {error}")
            continue
        columns = {c["name"]: c for c in data["columns"]}
        accounting = data["accounting"]
        check(data["header_row"] == 1, f"header_row is {data['header_row']}, not 1",
              failures, name)
        for column_name, expected in EXPECTED_TYPES.items():
            column = columns.get(column_name)
            if column is None:
                continue
            check(column["type"] == expected,
                  f"column '{column_name}' typed {column['type']}, expected {expected}",
                  failures, name)
            if column_name in CURRENCY:
                check(column.get("unit") == "currency",
                      f"column '{column_name}' has unit {column.get('unit')!r}, "
                      f"expected 'currency'", failures, name)
        if "Distinct Contributors" in columns:
            check(columns["Distinct Contributors"].get("accounting", {})
                  .get("safe_to_sum") is False,
                  "Distinct Contributors is not marked non-summable", failures, name)
        if "Giving" in columns:
            check(columns["Giving"].get("accounting", {}).get("safe_to_sum", True),
                  "Giving is marked non-summable at column level", failures, name)
        if name == "Giving Facts":
            check(accounting["safe_to_sum"] is True,
                  "Giving Facts is not sheet-level summable", failures, name)
        if "Source ID" in columns:
            check(accounting["grain"] == "FEC source observation",
                  f"Source ID sheet grain is {accounting['grain']!r}", failures, name)
            check("Analysis Amount" in data["note"],
                  "Source ID sheet is missing the Analysis Amount grain note",
                  failures, name)
            check(columns["Amount"].get("accounting", {}).get("safe_to_sum") is False,
                  "raw Amount is not marked non-summable next to Analysis Amount",
                  failures, name)
        check("overlapping summary rows were excluded" not in data["note"],
              "the reader auto-filtered rows out of this sheet", failures, name)
        check(accounting["row_role_column"] is None,
              "the reader found a View/Scope/Section row-role column", failures, name)
        emit(f"{name:<32}{data['header_row']:>4}{data['row_count']:>9,}"
             f"{len(data['columns']):>6}  "
             f"{str(accounting['safe_to_sum']):<12}{accounting['grain']:<26}"
             f"ok in {time.time() - sheet_started:.0f}s")
        del data, columns

    report.append("")
    try:
        found = contribution_data._workbook_source(
            contribution_data._stamp(MOCK)
            if hasattr(contribution_data, "_stamp") else file_stamp)
        report.append(f"contribution_data._workbook_source -> {found}")
        check(found == "f9e956354525acb069cae220eb8d1538c479eea1bf23df1b3154adee8f416686",
              f"lineage sha is {found}", failures, "About")
    except Exception as error:                              # noqa: BLE001
        report.append(f"contribution_data._workbook_source RAISED: {error}")
        failures.append(f"About: _workbook_source raised {error}")
        traceback.print_exc()

    report.append("")
    report.append(f"elapsed: {time.time() - started:.1f}s")
    if failures:
        report.append(f"FAILURES ({len(failures)}):")
        report += [f"  - {f}" for f in failures]
    else:
        report.append("ALL READER ASSERTIONS PASSED")
    text = "\n".join(report)
    print(text)
    (Path(__file__).parent / "reader_check.txt").write_text(text, encoding="utf-8")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
