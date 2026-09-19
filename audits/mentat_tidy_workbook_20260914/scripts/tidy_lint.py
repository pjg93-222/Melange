"""Tableau-rules lint for any .xlsx. Exit 0 when clean, 1 when a rule is broken.

The rules are Tableau's "Structure Data for Analysis" guidance plus the two
hard constraints the Mentat console reader imposes (`app/report_insights.py`):
header on row 1, one type per column, one Excel Table per sheet spanning the
whole grid, no merged cells, no formulas (their cached results are what a reader
gets), no packed `;` multi-values, no pre-aggregated Total/Average/Other rows,
identifiers stored as text, dates stored as real dates, and no sheet named with a
bare cycle label (`app/graph_data.py`:148,187 would parse it with header row 4).

Reads only: the workbook is opened `read_only=True` and its table and merge
definitions are parsed straight out of the ZIP, so nothing is rewritten.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import openpyxl
from openpyxl.utils import get_column_letter, range_boundaries

NAMESPACE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
PACKAGE = "{http://schemas.openxmlformats.org/package/2006/relationships}"
# workbook.xml carries r:id in the officeDocument namespace, not the package one.
RELATIONSHIPS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"

# Documented free-text / JSON / prose columns: a ';' inside them is a sentence or
# an encoded record, not a packed multi-value list. Must stay in step with
# build_tidy_workbook.MULTIVALUE_EXEMPT_HEADERS.
# Mirrors build_tidy_workbook.MULTIVALUE_CHECKED_HEADERS verbatim. The rule is an
# INCLUDE-LIST of categorical dimensions we derive, not "every text column except
# prose" (Paul's ruling, 2026-09-15). FEC names and filed descriptions legitimately
# contain ';' - "MADISON PAC; THE" is one committee - and cannot be enumerated, so
# only columns our own derivations write are checked for packed "a; b" values.
# These two lists MUST stay in step; a column checked by one and not the other means
# the lint and the writer disagree about the same workbook.
MULTIVALUE_CHECKED_HEADERS = frozenset((
    "Election Cycle", "Cycle Alignment", "Contributor Tier", "Recipient Category",
    "Category Source", "Recipient Party", "Party Source", "Committee Type",
    "Committee Designation", "Record Type", "Source Table", "Funding Source Type",
    "Funding Direction", "Receipt Role", "Committee Relationship", "Mapping Source",
    "Relationship", "Link Source", "Candidate Party", "Office", "Incumbent Status",
    "Activity Type", "Support / Oppose", "Transaction Type", "Funding Type",
    "Direction", "Traversal Status", "State", "Sponsor State", "Sponsor Office",
    "Committee Party", "Committee State", "Office Code",
))

# DOCUMENTATION ONLY - no longer consulted. The columns the previous exempt-list form
# named as deliberate prose, kept to explain why each stays OUT of the list above:
#     "Memo Text", "Source URL", "Representative Path", "Transfer Records",
#     "Unresolved Reasons", "Detail", "Inclusion Reason", "Duplicate Reason",
#     "Company Match Reason", "Accounting Note", "Rule", "Ownership Status"
# "Traversal Status" moved from that list into the checked list above; see the note in
# build_tidy_workbook.py.
MULTIVALUE_EXEMPT_HEADERS_DOC = (
    "Memo Text", "Source URL", "Representative Path", "Transfer Records",
    "Unresolved Reasons", "Detail", "Inclusion Reason", "Duplicate Reason",
    "Company Match Reason", "Accounting Note", "Rule", "Ownership Status",
)

IDENTIFIER_HEADER = re.compile(
    r"(\bID\b|\bIDs\b|ZIP|District|\bKey\b|\bKeys\b|Line Number)", re.I)
DATE_HEADER = re.compile(r"(^|\s)(Date|Dates)$|^(First|Last) .*Date$", re.I)
AGGREGATE_ROW = re.compile(r"^\s*(Total|Average|Other \()", re.I)
BARE_CYCLE = re.compile(r"^\d{4}-\d{4}$")


class Findings:
    def __init__(self):
        self.rows = []

    def add(self, sheet, rule, detail):
        self.rows.append((sheet, rule, detail))

    def report(self, title, stream=sys.stdout):
        print(f"\n=== {title} ===", file=stream)
        if not self.rows:
            print("PASS - no findings.", file=stream)
            return 0
        width = max(len(r[0]) for r in self.rows)
        rule_width = max(len(r[1]) for r in self.rows)
        for sheet, rule, detail in self.rows:
            print(f"  {sheet:<{width}}  {rule:<{rule_width}}  {detail}", file=stream)
        counts = {}
        for _, rule, _ in self.rows:
            counts[rule] = counts.get(rule, 0) + 1
        print(f"FAIL - {len(self.rows)} finding(s): "
              + ", ".join(f"{k} x{v}" for k, v in sorted(counts.items())), file=stream)
        return 1


def zip_facts(path):
    """Sheet order, per-sheet merged ranges and table refs, read from the ZIP."""
    sheets, merges, tables = [], {}, {}
    with zipfile.ZipFile(path) as archive:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        relations = {node.get("Id"): node.get("Target") for node in
                     ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))}
        for node in workbook.iter(f"{NAMESPACE}sheet"):
            name = node.get("name")
            target = relations.get(node.get(f"{RELATIONSHIPS}id"), "")
            member = "xl/" + target.lstrip("/").removeprefix("xl/")
            sheets.append((name, member))
            merges[name], tables[name] = [], []
            if member not in archive.namelist():
                continue
            for _, element in ET.iterparse(archive.open(member), events=("end",)):
                if element.tag == f"{NAMESPACE}mergeCell":
                    merges[name].append(element.get("ref"))
                if element.tag == f"{NAMESPACE}sheetData":
                    element.clear()
            rels = member.replace("worksheets/", "worksheets/_rels/") + ".rels"
            if rels not in archive.namelist():
                continue
            for node in ET.fromstring(archive.read(rels)):
                target = node.get("Target", "")
                if "/tables/" not in target and not target.startswith("../tables/"):
                    continue
                part = "xl/tables/" + target.rsplit("/", 1)[-1]
                if part in archive.namelist():
                    table = ET.fromstring(archive.read(part))
                    tables[name].append((table.get("displayName"), table.get("ref")))
    return sheets, merges, tables


def value_kind(value):
    """One kind per Excel storage class.

    bool is counted separately from a number, because openpyxl round-trips a
    real boolean and the console reader's `numeric()` returns None for it. int
    and float collapse to one "number" kind: XLSX has a single numeric type and
    openpyxl reads 25.0 back as int 25, so an int/float mix is a serialisation
    artefact, not a column holding two kinds of thing.
    """
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (datetime.datetime, datetime.date)):
        return "date"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__


def lint(path, header_row=1):
    findings = Findings()
    sheets, merges, tables = zip_facts(path)
    book = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        for name, _ in sheets:
            if BARE_CYCLE.fullmatch(name.strip()):
                findings.add(name, "sheet-name", "sheet name is a bare cycle label")
            if merges.get(name):
                findings.add(name, "merged-cells",
                             f"{len(merges[name])} merged range(s), e.g. {merges[name][0]}")
            sheet = book[name]
            headers, kinds, formulas, aggregate = None, [], 0, 0
            rows = 0
            columns = 0
            for index, row in enumerate(sheet.iter_rows(values_only=True), 1):
                if index < header_row:
                    continue
                if headers is None:
                    values = list(row)
                    while values and values[-1] is None:
                        values.pop()
                    headers = [None if v is None else str(v) for v in values]
                    columns = len(headers)
                    kinds = [set() for _ in headers]
                    blank = [i for i, h in enumerate(headers)
                             if h is None or not h.strip()]
                    if blank:
                        findings.add(name, "header-row",
                                     f"row {header_row} has {len(blank)} blank header(s) "
                                     f"at column(s) "
                                     f"{', '.join(get_column_letter(i + 1) for i in blank[:6])}")
                    named = [h for h in headers if h and h.strip()]
                    if len(named) != len(set(named)):
                        duplicates = sorted({h for h in named if named.count(h) > 1})
                        findings.add(name, "header-row",
                                     f"duplicate header(s): {', '.join(duplicates[:6])}")
                    if any(v is not None and not isinstance(v, str) for v in values):
                        findings.add(name, "header-row",
                                     "row 1 holds a non-text cell, so it is not a header")
                    continue
                if all(v is None or v == "" for v in row[:columns]):
                    continue
                rows += 1
                first = row[0]
                if isinstance(first, str) and AGGREGATE_ROW.match(first):
                    aggregate += 1
                for position in range(columns):
                    value = row[position] if position < len(row) else None
                    if value is None or value == "":
                        continue
                    if isinstance(value, str) and value.startswith("="):
                        formulas += 1
                        continue
                    kinds[position].add(value_kind(value))
                    header = headers[position] or ""
                    if (isinstance(value, str) and ";" in value
                            and header in MULTIVALUE_CHECKED_HEADERS):
                        kinds[position].add("SEMICOLON")
            if headers is None:
                findings.add(name, "header-row", "sheet is empty")
                continue
            if formulas:
                findings.add(name, "formulas", f"{formulas:,} formula cell(s)")
            if aggregate:
                findings.add(name, "aggregate-rows",
                             f"{aggregate:,} row(s) start with Total/Average/Other (")
            for position, header in enumerate(headers):
                observed = kinds[position]
                if "SEMICOLON" in observed:
                    findings.add(name, "multivalue",
                                 f"'{header}' contains ';' packed values")
                    observed = observed - {"SEMICOLON"}
                if len(observed) > 1:
                    findings.add(name, "mixed-type",
                                 f"'{header}' holds {sorted(observed)}")
                if header and IDENTIFIER_HEADER.search(header) and observed - {"str"}:
                    findings.add(name, "identifier-type",
                                 f"'{header}' is an identifier stored as "
                                 f"{sorted(observed - {'str'})}")
                if header and DATE_HEADER.search(header) and observed - {"date"}:
                    findings.add(name, "date-type",
                                 f"'{header}' is a date header stored as "
                                 f"{sorted(observed - {'date'})}")
            found = tables.get(name, [])
            if len(found) != 1:
                findings.add(name, "table-count",
                             f"{len(found)} Excel Table(s); exactly one is required")
            else:
                reference = found[0][1]
                minimum_column, minimum_row, maximum_column, maximum_row = \
                    range_boundaries(reference)
                if (minimum_row, minimum_column) != (1, 1):
                    findings.add(name, "table-ref",
                                 f"table {found[0][0]} starts at {reference}, not A1")
                if maximum_row != rows + header_row or maximum_column != columns:
                    findings.add(name, "table-ref",
                                 f"table {found[0][0]} ref {reference} does not span "
                                 f"{columns} column(s) x {rows + header_row} row(s)")
    finally:
        book.close()
    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("workbook")
    parser.add_argument("--header-row", type=int, default=1,
                        help="only for inspecting a non-conforming book")
    parser.add_argument("--expect", choices=("pass", "fail"), default="pass",
                        help="negative control: 'fail' inverts the exit code")
    arguments = parser.parse_args(argv if argv is not None else sys.argv[1:])
    path = Path(arguments.workbook)
    findings = lint(path, arguments.header_row)
    status = findings.report(path.name)
    if arguments.expect == "fail":
        if status:
            print("NEGATIVE CONTROL SATISFIED: the lint rejects this workbook.")
            return 0
        print("NEGATIVE CONTROL FAILED: the lint accepted a workbook it should reject.")
        return 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
