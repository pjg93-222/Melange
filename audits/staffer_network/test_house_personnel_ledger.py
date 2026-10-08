# -*- coding: utf-8 -*-
"""pytest for build_house_personnel_ledger.py / verify_house_personnel_ledger.py on synthetic fixtures.

Fixtures are constructed in the real CSV column shapes (12-col, 13-col trailing-empty
variant with one shifted row, 18-col) and a tiny pinned-roster YAML.  The 18-col fixture is
the HON. KEVIN KILEY 2025Q2 slice of the real 2025q2_sod_detail.csv (personnel rows,
subtotal rows, a few travel rows, the 2024-prefixed block and the intern block) plus
synthetic offices that exercise every office-resolution branch.
"""
from __future__ import annotations

import gzip
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import build_house_personnel_ledger as bl  # noqa: E402
import verify_house_personnel_ledger as vl  # noqa: E402

# ---------------------------------------------------------------------------
# Gold block (pasted into the task)
# ---------------------------------------------------------------------------

GOLD = {
    "member": "HON. KEVIN KILEY", "quarter": "2025Q2", "personnel_total": "282,805.54",
    "rows": [
        ["CAMERON, CARSON S.", "04/01/25", "06/30/25", "LEGISLATIVE ASSISTANT", "17,124.99"],
        ["CAMPBELL, HUNTLEY J.", "04/01/25", "06/30/25", "LEGISLATIVE ASSISTANT", "15,999.99"],
        ["EUCEDA, ANTHONY", "04/01/25", "06/30/25", "STAFF ASSISTANT", "14,000.01"],
        ["FATZINGER, MARY P.", "04/01/25", "04/23/25", "SCHEDULER", "4,280.56"],
        ["GEMELLARO, PETER J.", "04/01/25", "06/30/25", "CASEWORKER", "18,999.99"],
        ["HARTL, KELLIE J.", "04/01/25", "06/30/25", "SHARED EMPLOYEE", "5,000.01"],
        ["HOLSTE, ROBERT L.", "04/01/25", "06/30/25", "CHIEF OF STAFF", "56,424.99"],
        ["HORVAT, CHELYSSA I.", "04/01/25", "06/30/25", "DISTRICT DIRECTOR", "27,500.01"],
        ["MOYER, ALEXANDRA M.", "04/22/25", "06/30/25", "DIRECTOR OF OPERATIONS", "15,333.34"],
        ["PIRSOS, JOHN", "04/23/25", "06/30/25", "COMMUNICATIONS DIRECTOR", "17,000.00"],
        ["RAUBER, MICHAEL B.", "04/01/25", "05/31/25", "COMMUNICATIONS DIRECTOR", "7,916.67"],
        ["SHOOK, JAMES R.", "04/01/25", "06/30/25", "SENIOR ADVISOR", "21,600.00"],
        ["THOMPSON, JACK W.", "04/01/25", "06/30/25", "DISTRICT REPRESENTATIVE", "18,999.99"],
        ["VASQUEZ-PAVICHEVICH, NATALIA", "04/01/25", "06/30/25", "CASEWORKER", "16,374.99"],
        ["ZANDSTRA, JAMES R.", "04/01/25", "06/30/25", "LEGISLATIVE DIRECTOR", "26,250.00"],
    ],
}

# ---------------------------------------------------------------------------
# 18-col fixture: real Kiley 2025Q2 slice (verbatim rows) + synthetic offices
# ---------------------------------------------------------------------------

HEADER_18 = ("ORGANIZATION,FISCAL YEAR OR LEGISLATIVE YEAR,ORGANIZATION CODE,PROGRAM,PROGRAM CODE,"
             "SORT SUBTOTAL DESCRIPTION,BUDGET OBJECT CLASS,SORT SEQUENCE,TRANSACTION DATE,DATA SOURCE,"
             "DOCUMENT,VENDOR NAME,VENDOR ID,PERFORM START DT,PERFORM END DT,DESCRIPTION,BUDGET OBJECT CODE,"
             "AMOUNT                                                      ")

KILEY_SLICE = """2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,CAMERON CARSON S.,,1-Apr-25,30-Jun-25,LEGISLATIVE ASSISTANT,1101,17124.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,CAMPBELL HUNTLEY J.,,1-Apr-25,30-Jun-25,LEGISLATIVE ASSISTANT,1101,15999.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,EUCEDA ANTHONY,,1-Apr-25,30-Jun-25,STAFF ASSISTANT,1101,14000.01
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,FATZINGER MARY P.,,1-Apr-25,23-Apr-25,SCHEDULER,1101,4280.56
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,GEMELLARO PETER J.,,1-Apr-25,30-Jun-25,CASEWORKER,1101,18999.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,HARTL KELLIE J.,,1-Apr-25,30-Jun-25,SHARED EMPLOYEE,1101,5000.01
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,HOLSTE ROBERT L.,,1-Apr-25,30-Jun-25,CHIEF OF STAFF,1101,56424.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,HORVAT CHELYSSA I.,,1-Apr-25,30-Jun-25,DISTRICT DIRECTOR,1101,27500.01
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,MOYER ALEXANDRA M.,,22-Apr-25,30-Jun-25,DIRECTOR OF OPERATIONS,1101,15333.34
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,PIRSOS JOHN,,23-Apr-25,30-Jun-25,COMMUNICATIONS DIRECTOR,1101,17000
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,RAUBER MICHAEL B.,,1-Apr-25,31-May-25,COMMUNICATIONS DIRECTOR,1101,7916.67
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,SHOOK JAMES R.,,1-Apr-25,30-Jun-25,SENIOR ADVISOR,1101,21600
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,THOMPSON JACK W.,,1-Apr-25,30-Jun-25,DISTRICT REPRESENTATIVE,1101,18999.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,VASQUEZ-PAVICHEVICH NATALIA,,1-Apr-25,30-Jun-25,CASEWORKER,1101,16374.99
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,11,DETAIL,,GL,,ZANDSTRA JAMES R.,,1-Apr-25,30-Jun-25,LEGISLATIVE DIRECTOR,1101,26250
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PERSONNEL COMPENSATION,,SUBTOTAL,,,,,,,,PERSONNEL COMPENSATION TOTALS:,,282805.54
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,TRAVEL,21,DETAIL,23-Apr-25,AP,X0246802,HORVAT CHELYSSA I.,,10-Mar-25,12-Mar-25,PRIVATE AUTO MILEAGE,2130,67.86
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,TRAVEL,21,DETAIL,24-Apr-25,AP,X0232651,THOMPSON JACK W.,,11-Feb-25,28-Feb-25,PRIVATE AUTO MILEAGE,2130,83.14
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,TRAVEL,,SUBTOTAL,,,,,,,,TRAVEL TOTALS:,,17851.02
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,RENT  COMMUNICATION  UTILITIES,,SUBTOTAL,,,,,,,,RENT  COMMUNICATION  UTILITIES TOTALS:,,70316.35
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,FRANKED MAIL,,SUBTOTAL,,,,,,,,FRANKED MAIL TOTALS:,,22000.67
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,PRINTING AND REPRODUCTION,,SUBTOTAL,,,,,,,,PRINTING AND REPRODUCTION TOTALS:,,576
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,OTHER SERVICES,,SUBTOTAL,,,,,,,,OTHER SERVICES TOTALS:,,12635
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,SUPPLIES AND MATERIALS,,SUBTOTAL,,,,,,,,SUPPLIES AND MATERIALS TOTALS:,,7123.93
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,EQUIPMENT,,SUBTOTAL,,,,,,,,EQUIPMENT TOTALS:,,588
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,EQUIPMENT,,SUBTOTAL,,,,,,,,OFFICIAL EXPENSES OF MEMBERS TOTALS:,,413896.51
2025 HON. KEVIN KILEY,LY2025,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,,EQUIPMENT,,GRAND TOTAL FOR ORGANIZATION,,,,,,,,OFFICE TOTALS:,,413896.51
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,TRAVEL,21,DETAIL,17-Jun-25,AP,X0265541,HON KEVIN KILEY,MEMCA03KIK,14-Dec-24,23-Dec-24,PRIVATE AUTO MILEAGE,2130,33.45
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,TRAVEL,,SUBTOTAL,,,,,,,,TRAVEL TOTALS:,,33.45
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,SUPPLIES AND MATERIALS,26,DETAIL,9-Apr-25,AP,1823366,CAPITOL MARKING PRODUCTS INC,11983,7-Apr-25,7-Apr-25,OFFICE SUPPLIES (OUTSIDE) QTY - 2,2620,94.2
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,SUPPLIES AND MATERIALS,,SUBTOTAL,,,,,,,,SUPPLIES AND MATERIALS TOTALS:,,94.2
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,OTHER,SUPPLIES AND MATERIALS,,SUBTOTAL,,,,,,,,OFFICIAL EXPENSES OF MEMBERS TOTALS:,,127.65
2024 HON. KEVIN KILEY,LY2024,CA03KIK,OFFICIAL EXPENSES OF MEMBERS,,SUPPLIES AND MATERIALS,,GRAND TOTAL FOR ORGANIZATION,,,,,,,,OFFICE TOTALS:,,127.65
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,11,DETAIL,,GL,,CHATTIN ANDREW,,1-Apr-25,30-Apr-25,DISTRICT OFFICE PAID INTERN -,1101,650
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,11,DETAIL,,GL,,MUNOZ KEVIN M.,,1-Apr-25,23-May-25,PAID INTERN - HOUSE PROGRAM,1101,3180
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,11,DETAIL,,GL,,OTTO GRANT,,1-Apr-25,14-Apr-25,PAID INTERN - HOUSE PROGRAM,1101,840
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,11,DETAIL,,GL,,SCOTT MITCHELL,,13-May-25,30-Jun-25,PAID INTERN - HOUSE PROGRAM,1101,2400
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,11,DETAIL,,GL,,SLOAN CONNOR J.,,1-Feb-25,2-Feb-25,PAID INTERN - HOUSE PROGRAM,1101,-2666.66
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,,SUBTOTAL,,,,,,,,PERSONNEL COMPENSATION TOTALS:,,4403.34
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,INTRN,PERSONNEL COMPENSATION,,SUBTOTAL,,,,,,,,INTERN ALLOWANCES TOTALS:,,4403.34
2025 HON. KEVIN KILEY,LY2025,CA03KIK,INTERN ALLOWANCES,,PERSONNEL COMPENSATION,,GRAND TOTAL FOR ORGANIZATION,,,,,,,,OFFICE TOTALS:,,4403.34"""

OEM = "OFFICIAL EXPENSES OF MEMBERS"


def pc18(org, ly, code, program, vendor, start, end, desc, amount, pcode="OTHER"):
    return f'{org},{ly},{code},{program},{pcode},PERSONNEL COMPENSATION,11,DETAIL,,GL,,{vendor},,{start},{end},{desc},1101,{amount}'


def sub18(org, ly, code, program, amount, pcode="OTHER"):
    return f'{org},{ly},{code},{program},{pcode},PERSONNEL COMPENSATION,,SUBTOTAL,,,,,,,,PERSONNEL COMPENSATION TOTALS:,,{amount}'


EXTRA_2025 = [
    pc18("2025 HON. DON BACON", "LY2025", "NE02BAD", OEM, "NGUYEN LINH", "1-Apr-25", "30-Jun-25", "CHIEF OF STAFF", "30000"),
    sub18("2025 HON. DON BACON", "LY2025", "NE02BAD", OEM, "30000"),
    pc18("2025 HON. ANDY BARR", "LY2025", "KY06BAA", OEM, "ROGERS MIKE J.", "1-Apr-25", "30-Jun-25", "STAFF ASSISTANT", "10000"),
    sub18("2025 HON. ANDY BARR", "LY2025", "KY06BAA", OEM, "10000"),
    pc18("2025 HON. MIKE ROGERS", "LY2025", "AL03ROM", OEM, "SMITH ANN", "1-Apr-25", "30-Jun-25", "STAFF ASSISTANT", "9000"),
    sub18("2025 HON. MIKE ROGERS", "LY2025", "AL03ROM", OEM, "9000"),
    pc18("2025 HON. 1ST DISTRICT OF FLORIDA", "LY2025", "FL01V25", OEM, "VACANT STAFF", "1-Apr-25", "30-Jun-25", "STAFF ASSISTANT", "5000"),
    sub18("2025 HON. 1ST DISTRICT OF FLORIDA", "LY2025", "FL01V25", OEM, "5000"),
    pc18("2025 HON. BLUE DOG COALITION", "LY2025", "AACMBDC", OEM, "COAL PERSON", "1-Apr-25", "30-Jun-25", "EXECUTIVE DIRECTOR", "12000"),
    sub18("2025 HON. BLUE DOG COALITION", "LY2025", "AACMBDC", OEM, "12000"),
    pc18("2025 HON. MICHELLE LUJAN GRISHAM", "LY2025", "NM01LUM", OEM, "OLD STAFF", "1-Apr-25", "30-Jun-25", "STAFF ASSISTANT", "1000"),
    sub18("2025 HON. MICHELLE LUJAN GRISHAM", "LY2025", "NM01LUM", OEM, "1000"),
    pc18("FISCAL YEAR 2025 COMMITTEE ON APPROPRIATIONS", "FY2025", "11AP000", "APPROPRIATIONS COMMITTEE", "HARTL KELLIE J.", "1-Apr-25", "30-Jun-25", "ASSISTANT TO CONG VALADAO", "10868.76"),
    sub18("FISCAL YEAR 2025 COMMITTEE ON APPROPRIATIONS", "FY2025", "11AP000", "APPROPRIATIONS COMMITTEE", "10868.76"),
    pc18("FISCAL YEAR 2025 CLERK OF THE HOUSE", "FY2025", "40CL000", "SALARIES  OFFICERS & EMPLOYEES", "CLERK STAFF", "1-Apr-25", "30-Jun-25", "CLERK", "8000"),
    sub18("FISCAL YEAR 2025 CLERK OF THE HOUSE", "FY2025", "40CL000", "SALARIES  OFFICERS & EMPLOYEES", "8000"),
    pc18("2025 OFFICE OF THE SPEAKER", "LY2025", "21SH203", "GENERAL EXPENDITURES", "SPEAKER STAFF A", "1-Apr-25", "30-Jun-25", "POLICY ADVISOR", "20000"),
    sub18("2025 OFFICE OF THE SPEAKER", "LY2025", "21SH203", "GENERAL EXPENDITURES", "20000"),
    pc18("2025 COMMITTEE ON JUDICIARY", "LY2025", "10JU000", "GENERAL EXPENDITURES", "JUDGE STAFF", "1-Apr-25", "30-Jun-25", "COUNSEL", "7000"),
    sub18("2025 COMMITTEE ON JUDICIARY", "LY2025", "10JU000", "GENERAL EXPENDITURES", "7001"),
]

# ---------------------------------------------------------------------------
# 12-col / 13-col fixtures (span logic)
# ---------------------------------------------------------------------------

HEADER_12 = ("ORGANIZATION,PROGRAM,SORT SUBTOTAL DESCRIPTION,SORT SEQUENCE,TRANSACTION DATE,DATA SOURCE,DOCUMENT,"
             "VENDOR NAME,PERFORM START DT,PERFORM END DT,DESCRIPTION,"
             "AMOUNT                                                                                                                                             ")
BLANK = "   "


def pc12(org, vendor, start, end, desc, amount, program=OEM):
    return ",".join([org, program, "PERSONNEL COMPENSATION", "DETAIL", BLANK, BLANK, BLANK, vendor, start, end, desc, amount])


def sub12(org, amount, program=OEM):
    return ",".join([org, program, "PERSONNEL COMPENSATION", "SUBTOTAL", BLANK, BLANK, BLANK, BLANK, BLANK, BLANK,
                     "PERSONNEL COMPENSATION TOTALS:", amount])


def travel12(org, vendor, amount):
    return ",".join([org, OEM, "TRAVEL", "DETAIL", "12-Feb-16", "AP", "X1", vendor, "1-Feb-16", "1-Feb-16", "PRIVATE AUTO MILEAGE", amount])


Q2016Q1 = [
    pc12("2015 HON. JANE DOE", "SMITH JOHN Q", "1-Dec-15", "2-Jan-16", "STAFF ASSISTANT", "1200"),
    sub12("2015 HON. JANE DOE", "1200"),
    pc12("2016 HON. JANE DOE", "SMITH JOHN Q", "3-Jan-16", "31-Mar-16", "STAFF ASSISTANT", "9000"),
    pc12("2016 HON. JANE DOE", "GAP PERSON", "3-Jan-16", "31-Mar-16", "CASEWORKER", "6000"),
    pc12("2016 HON. JANE DOE", "COLLIDE ANNA B", "3-Jan-16", "31-Mar-16", "SCHEDULER", "5000"),
    pc12("2016 HON. JANE DOE", "COLLIDE ANNA C", "3-Jan-16", "31-Mar-16", "SCHEDULER", "5000"),
    pc12("2016 HON. JANE DOE", "LINK BOB", "3-Jan-16", "31-Mar-16", "DRIVER", "4000"),
    pc12("2016 HON. JANE DOE", "FISCHER JR ROBERT V.", "3-Jan-16", "31-Mar-16", "LEGISLATIVE DIRECTOR", "20000"),
    pc12("2016 HON. JANE DOE", "CONNELLY HENRY V", "3-Jan-16", "31-Mar-16", "CONSTITUENT SERVICES REPRESENT", "7000"),
    pc12("2016 HON. JANE DOE", BLANK, "3-Jan-16", "31-Mar-16", "STAFF ASSISTANT", "100"),
    pc12("2016 HON. JANE DOE", "SHARE PERSON", "3-Jan-16", "31-Mar-16", "SHARED EMPLOYEE", "2000"),
    travel12("2016 HON. JANE DOE", "SMITH JOHN Q", "55.5"),
    sub12("2016 HON. JANE DOE", "58100"),
    pc12("2016 HON. MICHELLE LUJAN GRISHAM", "SHARE PERSON", "3-Jan-16", "31-Mar-16", "SHARED EMPLOYEE", "3000"),
    sub12("2016 HON. MICHELLE LUJAN GRISHAM", "3000"),
    pc12("FISCAL YEAR 2016 CLERK OF THE HOUSE", "SMITH JOHN Q", "3-Jan-16", "31-Mar-16", "CLERK ASSISTANT", "3000", "SALARIES  OFFICERS & EMPLOYEES"),
    sub12("FISCAL YEAR 2016 CLERK OF THE HOUSE", "3000", "SALARIES  OFFICERS & EMPLOYEES"),
]
Q2016Q2 = [
    pc12("2016 HON. JANE DOE", "SMITH JOHN Q", "1-Apr-16", "30-Jun-16", "STAFF ASSISTANT", "9000"),
    pc12("2016 HON. JANE DOE", "SMITH JOHN Q", "1-Apr-16", "30-Jun-16", "STAFF ASSISTANT (OTHER COMPENSATION)", "500"),
    pc12("2016 HON. JANE DOE", "GAP PERSON", "15-Apr-16", "30-Jun-16", "CASEWORKER", "5000"),
    pc12("2016 HON. JANE DOE", "LINK BOB D", "1-Apr-16", "30-Jun-16", "DRIVER", "4000"),
    pc12("2016 HON. JANE DOE", "ORPHAN ONLY", "1-Apr-16", "30-Jun-16", "STAFF ASSISTANT (OTHER COMPENSATION)", "250"),
    sub12("2016 HON. JANE DOE", "18750"),
]
# 13-col variant: header ends with an empty cell; every row carries an empty trailing cell except the shifted one.
Q2016Q3_13COL = [
    pc12("2016 HON. JANE DOE", "SMITH JOHN Q", "1-Jul-16", "30-Sep-16", "LEGISLATIVE ASSISTANT", "9500") + ",",
    pc12("2016 HON. JANE DOE", "GAP PERSON", "1-Jul-16", "30-Sep-16", "CASEWORKER", "5000") + ",",
    ",".join(["2016 HON. JANE DOE", OEM, "SUPPLIES AND MATERIALS", "DETAIL", "12-Aug-16", "AP", "X9",
              "CITI PCARD-CNDTL CR, AMZN MKTP US M79", "1-Aug-16", "1-Aug-16", "OFFICE SUPPLIES (OUTSIDE)", "-102.86"]),
    sub12("2016 HON. JANE DOE", "14500") + ",",
]
Q2016Q4 = [
    pc12("2016 HON. JANE DOE", "SMITH JOHN Q", "1-Oct-16", "15-Nov-16", "LEGISLATIVE ASSISTANT", "4500"),
    sub12("2016 HON. JANE DOE", "4500"),
]
Q2017Q2 = [
    pc12("2017 HON. JANE DOE", "SMITH JOHN Q", "1-Apr-17", "30-Jun-17", "LEGISLATIVE ASSISTANT", "9500"),
    sub12("2017 HON. JANE DOE", "9500"),
]

ROSTER_YAML = """- id: {bioguide: K000401}
  name: {first: Kevin, middle: Patrick, last: Kiley}
  terms:
  - {type: rep, start: '2023-01-03', end: '2025-01-03'}
  - {type: rep, start: '2025-01-03', end: '2027-01-03'}
- id: {bioguide: B001298}
  name: {first: Don, last: Bacon}
  terms:
  - {type: rep, start: '2017-01-03', end: '2027-01-03'}
- id: {bioguide: B001282}
  name: {first: Garland, last: Barr, nickname: Andy}
  terms:
  - {type: rep, start: '2013-01-03', end: '2027-01-03'}
- id: {bioguide: R000575}
  name: {first: Mike, last: Rogers}
  terms:
  - {type: rep, start: '2003-01-07', end: '2027-01-03'}
- id: {bioguide: R000572}
  name: {first: Mike, last: Rogers}
  terms:
  - {type: rep, start: '2001-01-03', end: '2027-01-03'}
- id: {bioguide: L000570}
  name: {first: Michelle, last: Lujan Grisham}
  terms:
  - {type: rep, start: '2013-01-03', end: '2019-01-01'}
- id: {bioguide: D000001}
  name: {first: Jane, last: Doe}
  terms:
  - {type: rep, start: '2015-01-06', end: '2019-01-03'}
- id: {bioguide: S000001}
  name: {first: Sam, last: Senator}
  terms:
  - {type: sen, start: '2015-01-06', end: '2021-01-03'}
"""


def write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\r\n".join([header] + rows) + "\r\n", encoding="utf-8", newline="")


def make_roster(tmp: Path) -> Path:
    root = tmp / "roster"
    root.mkdir()
    (root / "legislators-current.yaml").write_text(ROSTER_YAML, encoding="utf-8")
    (root / "legislators-historical.yaml").write_text("[]\n", encoding="utf-8")
    return root


def make_csv_root_2025(tmp: Path) -> Path:
    root = tmp / "csv2025"
    root.mkdir()
    write_csv(root / "2025q2_sod_detail.csv", HEADER_18, KILEY_SLICE.split("\n") + EXTRA_2025)
    return root


def make_csv_root_2016(tmp: Path) -> Path:
    root = tmp / "csv2016"
    root.mkdir()
    write_csv(root / "2016q1_sod_detail.csv", HEADER_12, Q2016Q1)
    write_csv(root / "2016q2_sod_detail.csv", HEADER_12, Q2016Q2)
    write_csv(root / "2016q3_sod_detail.csv", HEADER_12 + ",", Q2016Q3_13COL)
    write_csv(root / "2016q4_sod_detail.csv", HEADER_12, Q2016Q4)
    write_csv(root / "2017q2_sod_detail.csv", HEADER_12, Q2017Q2)
    return root


def run_build(csv_root: Path, roster: Path, out: Path, extra: list[str] | None = None) -> dict:
    argv = ["--output-root", str(out), "--csv-root", str(csv_root), "--roster-root", str(roster),
            "--url-inventory", str(out.parent / "no_inventory.json")] + (extra or [])
    code = bl.main(argv)
    assert code == 0, f"build exit code {code}"
    return json.loads((out / bl.RECEIPT_NAME).read_text(encoding="utf-8"))


def read_gz(path: Path) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


# ---------------------------------------------------------------------------
# Unit tests: normalization
# ---------------------------------------------------------------------------

def test_parse_payee_csv_shapes():
    p = bl.parse_payee("CAMERON CARSON S.", False)
    assert p["person_key"] == "SOD:CAMERON|CARSON|S" and p["person_key_family"] == "SODFAM:CAMERON|CARSON"
    p = bl.parse_payee("FISCHER JR ROBERT V.", False)
    assert p["person_key"] == "SOD:FISCHER|ROBERT|V" and p["payee_parse"]["suffix_tokens"] == ["JR"]
    p = bl.parse_payee("CONNELLY HENRY V", False)
    assert p["person_key"] == "SOD:CONNELLY|HENRY|V"
    p = bl.parse_payee("VASQUEZ-PAVICHEVICH NATALIA", False)
    assert p["person_key"] == "SOD:VASQUEZPAVICHEVICH|NATALIA|" and p["payee_parse"]["token_count"] == 2
    p = bl.parse_payee("O'BRIEN MARY K.", False)
    assert p["person_key"] == "SOD:OBRIEN|MARY|K"
    p = bl.parse_payee("VAN HOOK ADDISON C.", False)
    assert "PAYEE_PARSE_AMBIGUOUS" in p["payee_parse"]["parse_flags"] and p["person_key"] == "SOD:VAN|HOOK|A"
    assert bl.parse_payee("   ", False)["person_key"] is None
    assert "PAYEE_SINGLE_TOKEN" in bl.parse_payee("DO", False)["payee_parse"]["parse_flags"]


def test_parse_payee_pdf_shapes():
    p = bl.parse_payee("DALY, BRENDAN 07/01/09", True)
    assert p["person_key"] == "SOD:DALY|BRENDAN|" and p["payee_parse"]["date_leak_tokens"] == ["07/01/09"]
    p = bl.parse_payee("DE LA O, IRVIN F", True)
    assert p["person_key"] == "SOD:DE LA O|IRVIN|F" and "PAYEE_MULTITOKEN_SURNAME_PDF" in p["payee_parse"]["parse_flags"]
    p = bl.parse_payee("ONEK JOSEPH", True)
    assert "PAYEE_PDF_NO_COMMA" in p["payee_parse"]["parse_flags"]


def test_title_amount_date_helpers():
    assert bl.parse_title("STAFF ASSISTANT (OTHER COMPENSATION)") == ("STAFF ASSISTANT", "OTHER COMPENSATION", False)
    assert bl.parse_title("CONSTITUENT SERVICES REPRESENT") == ("CONSTITUENT SERVICES REPRESENT", "BASE", True)
    assert bl.parse_title("COUNSEL (A)") == ("COUNSEL (A)", "BASE", False)
    assert bl.parse_amount("17000") == Decimal("17000") and bl.parse_amount("(12.50)") == Decimal("-12.50")
    assert bl.parse_amount("–5,194.44") == Decimal("-5194.44") and bl.parse_amount("abc") is None
    assert bl.parse_date("1-Apr-25").isoformat() == "2025-04-01" and bl.parse_date("07/01/09").isoformat() == "2009-07-01"
    assert bl.parse_date("nonsense") == "UNPARSED" and bl.parse_date("") is None


def test_normalize_office_keeps_bacon_and_strips_continuation():
    assert bl.normalize_office("2025 HON. DON BACON") == "HON. DON BACON"
    assert bl.normalize_office("2009 OFFICE OF THE SPEAKER—Con.") == "OFFICE OF THE SPEAKER"
    assert bl.normalize_office("2009 OFFICE OF THE SPEAKER�Con.") == "OFFICE OF THE SPEAKER"
    assert bl.normalize_office("2016 VETERANS’ AFFAIRS & X") == "VETERANS' AFFAIRS AND X"
    assert bl.legacy_office_group_key("HON. DEBBIE WASSERMAN-SCHULTZ") == "HON:WASSERMAN-SCHULTZ"


def test_merge_intervals_and_annualize():
    import datetime as dt
    d = dt.date
    merged = bl.merge_intervals([(d(2016, 1, 3), d(2016, 3, 31)), (d(2015, 12, 1), d(2016, 1, 2))])
    assert merged == [(d(2015, 12, 1), d(2016, 3, 31))]
    assert bl.union_days(merged) == 122
    assert bl.merge_intervals([(d(2016, 1, 1), d(2016, 1, 10)), (d(2016, 1, 12), d(2016, 1, 20))]) == [(d(2016, 1, 1), d(2016, 1, 10)), (d(2016, 1, 12), d(2016, 1, 20))]
    assert bl.annualize(Decimal("24444.43"), 89) == "100249.63"
    assert bl.annualize(Decimal("-1"), 10) is None and bl.annualize(Decimal("5"), 0) is None


# ---------------------------------------------------------------------------
# Kiley gold block (18-col fixture)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def build_2025(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("k2025")
    roster = make_roster(tmp)
    csv_root = make_csv_root_2025(tmp)
    out = tmp / "gen_primary"
    receipt = run_build(csv_root, roster, out)
    return {"tmp": tmp, "roster": roster, "csv_root": csv_root, "out": out, "receipt": receipt}


def test_kiley_gold_block_reproduced(build_2025):
    receipt = build_2025["receipt"]
    gold = receipt["kiley_gold_check"]
    assert gold["status"] == "PASS", gold
    assert gold["rows_matched_in_order"] == 15 and gold["reproduced_rows"] == 15
    assert gold["personnel_total_from_detail_sum"] == GOLD["personnel_total"]
    assert gold["personnel_total_from_subtotal_row"] == GOLD["personnel_total"]
    obs = read_gz(build_2025["out"] / bl.OBSERVATIONS_NAME)
    kiley = [o for o in obs if o["office_raw"] == "2025 HON. KEVIN KILEY" and o["program"] == OEM]
    rebuilt = [[bl.gold_payee(o["payee_raw"]), bl.gold_date(bl.dt.date.fromisoformat(o["service_start"])),
                bl.gold_date(bl.dt.date.fromisoformat(o["service_end"])), o["title_raw"], f"{Decimal(o['amount']):,.2f}"] for o in kiley]
    assert rebuilt == GOLD["rows"]
    assert all(o["member_bioguide"] == "K000401" and o["office_key"] == "HON:K000401" for o in kiley)
    assert all(o["container_kind"] == "member_office" for o in kiley)
    hartl = next(o for o in kiley if o["payee_raw"] == "HARTL KELLIE J.")
    assert hartl["shared_employee_flag"] is True and hartl["title_base"] == "SHARED EMPLOYEE"
    assert sum(1 for o in obs if o["office_raw"] == "2025 HON. KEVIN KILEY" and o["program"] == "INTERN ALLOWANCES") == 5


def test_member_quarters_kiley(build_2025):
    rows = read_gz(build_2025["out"] / bl.MEMBER_QUARTERS_NAME)
    by_org = {r["office_raw"]: r for r in rows}
    k = by_org["2025 HON. KEVIN KILEY"]
    assert k["staff_count"] == 15 and k["personnel_row_count"] == 15
    assert k["personnel_total"] == "282805.54" and k["personnel_subtotal_row_total"] == "282805.54"
    assert k["personnel_reconciliation"] == "RECONCILED"
    assert k["intern_row_count"] == 5 and k["intern_total"] == "4403.34"
    assert k["member_bioguide"] == "K000401" and k["organization_codes"] == ["CA03KIK"]
    k24 = by_org["2024 HON. KEVIN KILEY"]
    assert k24["staff_count"] == 0 and k24["personnel_reconciliation"] == "NO_PERSONNEL_BLOCK" and k24["allowance_year"] == 2024
    assert "2025 HON. 1ST DISTRICT OF FLORIDA" in by_org and by_org["2025 HON. 1ST DISTRICT OF FLORIDA"]["container_kind"] == "vacant_seat"
    assert "2025 HON. BLUE DOG COALITION" not in by_org  # member_organization container, not a member office
    assert "2025 OFFICE OF THE SPEAKER" not in by_org and "FISCAL YEAR 2025 CLERK OF THE HOUSE" not in by_org


def test_office_resolution_branches(build_2025):
    obs = read_gz(build_2025["out"] / bl.OBSERVATIONS_NAME)
    by_org = {}
    for o in obs:
        by_org.setdefault(o["office_raw"], o)
    assert by_org["2025 HON. DON BACON"]["member_bioguide"] == "B001298"
    barr = by_org["2025 HON. ANDY BARR"]
    assert barr["member_resolution_method"] == "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
    assert barr["member_resolution_evidence"]["roster_nickname_would_match"] is True
    assert barr["office_key"] == "HONRAW:HON. ANDY BARR" and barr["container_kind"] == "member_office_unresolved"
    rogers = by_org["2025 HON. MIKE ROGERS"]
    assert rogers["member_resolution_method"] == "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"
    vacant = by_org["2025 HON. 1ST DISTRICT OF FLORIDA"]
    assert vacant["container_kind"] == "vacant_seat" and vacant["office_key"].startswith("VACANT:")
    caucus = by_org["2025 HON. BLUE DOG COALITION"]
    assert caucus["container_kind"] == "member_organization" and caucus["member_resolution_method"] == "NOT_A_MEMBER_NAME_CAUCUS_STRING"
    lujan = by_org["2025 HON. MICHELLE LUJAN GRISHAM"]
    assert lujan["member_resolution_method"] == "UNRESOLVED_NO_REP_TERM_IN_YEAR"
    assert lujan["member_resolution_evidence"]["surname_matched"] == "LUJAN GRISHAM"
    approp = by_org["FISCAL YEAR 2025 COMMITTEE ON APPROPRIATIONS"]
    assert approp["container_kind"] == "committee" and approp["office_key"] == "COMMITTEE:COMMITTEE ON APPROPRIATIONS"
    assert approp["allowance_year_kind"] == "FISCAL_YEAR" and approp["allowance_year"] == 2025
    assert by_org["FISCAL YEAR 2025 CLERK OF THE HOUSE"]["container_kind"] == "admin"
    assert by_org["2025 OFFICE OF THE SPEAKER"]["container_kind"] == "leadership"
    assert by_org["2025 COMMITTEE ON JUDICIARY"]["container_kind"] == "committee"
    hartl_keys = {o["office_key"] for o in obs if o["payee_raw"] == "HARTL KELLIE J."}
    assert hartl_keys == {"HON:K000401", "COMMITTEE:COMMITTEE ON APPROPRIATIONS"}


def test_reconciliation_mismatch_is_reported_not_hidden(build_2025):
    receipt = build_2025["receipt"]
    recon = receipt["totals"]["personnel_block_reconciliation"]
    assert recon.get("MISMATCH") == 1
    example = next(e for e in receipt["personnel_block_reconciliation_examples"] if e["status"] == "MISMATCH")
    assert example["organization"] == "2025 COMMITTEE ON JUDICIARY" and example["detail_sum"] == "7000" and example["subtotal_sum"] == "7001"
    assert receipt["status"] == "PASS"  # reported, never silently skipped; the build still stands


def test_inv_block_and_no_promotions(build_2025):
    for name in (bl.OBSERVATIONS_NAME, bl.SPANS_NAME, bl.MEMBER_QUARTERS_NAME):
        for row in read_gz(build_2025["out"] / name):
            for key, value in bl.INV.items():
                assert row[key] == value, (name, key)
            for key, value in row.items():
                if key.startswith("canonical_"):
                    assert value in (False, None, "NOT_ADJUDICATED"), (name, key, value)
    receipt = build_2025["receipt"]
    assert receipt["invariants"]["canonical_employment_promotions"] == 0
    assert receipt["invariants"]["canonical_identity_promotions"] == 0
    assert receipt["inputs"]["pdf_era"]["status"] == "NOT_INGESTED_CSV_ONLY"


def test_immutable_output_dir(build_2025):
    argv = ["--output-root", str(build_2025["out"]), "--csv-root", str(build_2025["csv_root"]),
            "--roster-root", str(build_2025["roster"]), "--url-inventory", str(build_2025["tmp"] / "none.json")]
    assert bl.main(argv) == 2


def test_twin_is_byte_identical(build_2025):
    twin = build_2025["tmp"] / "gen_twin"
    run_build(build_2025["csv_root"], build_2025["roster"], twin)
    for name in (bl.OBSERVATIONS_NAME, bl.SPANS_NAME, bl.MEMBER_QUARTERS_NAME, bl.RECEIPT_NAME):
        assert (build_2025["out"] / name).read_bytes() == (twin / name).read_bytes(), name


def test_verifier_passes_on_fixture(build_2025):
    twin = build_2025["tmp"] / "gen_twin"
    if not twin.exists():
        run_build(build_2025["csv_root"], build_2025["roster"], twin)
    verification = build_2025["tmp"] / "verification"
    code = vl.main(["--primary", str(build_2025["out"]), "--twin", str(twin), "--csv-root", str(build_2025["csv_root"]),
                    "--output-root", str(verification), "--script", str(HERE / "build_house_personnel_ledger.py"),
                    "--script", str(HERE / "verify_house_personnel_ledger.py"), "--script", str(HERE / "test_house_personnel_ledger.py")])
    assert code == 0
    report = json.loads((verification / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert report["status"] == "PASS", {k: v for k, v in report["checks"].items() if not v}
    assert report["twin"]["all_byte_identical"] is True
    assert report["kiley_gold_check"]["status"] == "PASS"
    assert report["language_scan"]["hits"] == []
    # A CSV-only build has no PDF era to cover, so the omitted --pdf-rows is not a gap.
    assert report["pdf_era_coverage"] == "NOT_APPLICABLE_CSV_ONLY_BUILD"
    assert report["checks"]["pdf_era_covered"] is True
    assert report["details"]["member_quarter_rows_by_era"] == {bl.ERA_CSV: report["details"]["member_quarter_rows"]}


def test_verifier_detects_tampered_twin(build_2025, tmp_path):
    twin = tmp_path / "twin_bad"
    run_build(build_2025["csv_root"], build_2025["roster"], twin)
    receipt_path = twin / bl.RECEIPT_NAME
    receipt_path.write_bytes(receipt_path.read_bytes() + b"\n")
    code = vl.main(["--primary", str(build_2025["out"]), "--twin", str(twin), "--csv-root", str(build_2025["csv_root"]),
                    "--output-root", str(tmp_path / "ver_bad")])
    assert code == 1


def test_verifier_tripwire_on_promoted_row(build_2025, tmp_path):
    bad = tmp_path / "promoted"
    bad.mkdir()
    for name in (bl.OBSERVATIONS_NAME, bl.SPANS_NAME, bl.MEMBER_QUARTERS_NAME, bl.RECEIPT_NAME):
        (bad / name).write_bytes((build_2025["out"] / name).read_bytes())
    rows = read_gz(bad / bl.SPANS_NAME)
    rows[0]["canonical_employment_promoted"] = True
    with bl.DeterministicGzipWriter(bad / bl.SPANS_NAME) as writer:
        for row in rows:
            writer.write(row)
    code = vl.main(["--primary", str(bad), "--csv-root", str(build_2025["csv_root"]), "--output-root", str(tmp_path / "ver_promoted")])
    assert code == 1
    report = json.loads((tmp_path / "ver_promoted" / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert report["checks"]["anti_promotion_tripwire"] is False


# ---------------------------------------------------------------------------
# Span logic (12-col / 13-col fixtures)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def build_2016(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("s2016")
    roster = make_roster(tmp)
    csv_root = make_csv_root_2016(tmp)
    out = tmp / "gen"
    receipt = run_build(csv_root, roster, out)
    spans = read_gz(out / bl.SPANS_NAME)
    obs = read_gz(out / bl.OBSERVATIONS_NAME)
    return {"tmp": tmp, "roster": roster, "csv_root": csv_root, "out": out, "receipt": receipt, "spans": spans, "obs": obs}


def spans_for(build, person_key, office_key):
    return sorted((s for s in build["spans"] if s["person_key"] == person_key and s["office_key"] == office_key), key=lambda s: s["run_index"])


def test_shifted_row_repair_and_13col(build_2016):
    q3 = build_2016["receipt"]["per_quarter"]["2016Q3"]["csv"]
    assert q3["trailing_empty_column"] is True and q3["shifted_rows_repaired"] == 1 and q3["malformed_width_rows"] == 0
    assert build_2016["receipt"]["per_quarter"]["2016Q3"]["admitted_rows"] == 2
    assert build_2016["receipt"]["per_quarter"]["2016Q3"]["personnel_block_reconciliation"] == {"RECONCILED": 1}


def test_span_chain_breaks(build_2016):
    smith = spans_for(build_2016, "SOD:SMITH|JOHN|Q", "HON:D000001")
    assert len(smith) == 2 and all(s["run_count"] == 2 for s in smith)
    first, second = smith
    assert first["quarters_observed"] == ["2016Q1", "2016Q2", "2016Q3", "2016Q4"]
    assert first["service_start_min"] == "2015-12-01" and first["service_end_max"] == "2016-11-15"
    assert first["contiguous"] is True and first["service_days_union"] == 351
    assert first["break_reason"] == "NEXT_QUARTER_ABSENT" and first["gap_quarters_to_next_span"] == 1
    assert first["base_amount_total"] == "33200" and first["other_comp_amount_total"] == "500" and first["other_comp_row_count"] == 1
    assert first["amount_sum"] == "33700" and first["status"] == "departed_or_unobserved"
    assert first["title_change_events"] == [{"quarter": "2016Q3", "from": ["STAFF ASSISTANT"], "to": ["LEGISLATIVE ASSISTANT"], "comparability": "EXACT"}]
    assert first["titles"] == ["LEGISLATIVE ASSISTANT", "STAFF ASSISTANT"]
    assert set(first["office_raw_examples"]) == {"2015 HON. JANE DOE", "2016 HON. JANE DOE"}
    assert "SAME_KEY_MEMBER_AND_ADMIN_SAME_QUARTER" in first["review_flags"] and "2016Q1" in first["shared_employee_quarters"]
    assert first["interval"] == {"start_earliest": "2015-12-01", "start_latest": "2015-12-01", "end_earliest": "2016-11-16",
                                 "end_latest": "2016-11-16", "start_precision": "day", "end_precision": "day", "asserted_current": False}
    assert second["quarters_observed"] == ["2017Q2"] and second["break_reason"] == "LATEST_QUARTER_REACHED" and second["status"] == "current"
    assert second["annualized_estimate"] == bl.annualize(Decimal("9500"), 91)
    clerk = spans_for(build_2016, "SOD:SMITH|JOHN|Q", "ADMIN:CLERK OF THE HOUSE")
    assert len(clerk) == 1 and clerk[0]["break_reason"] == "NOT_OBSERVED_AFTER"


def test_span_date_gap_breaks_with_zero_tolerance(build_2016):
    gap = spans_for(build_2016, "SOD:GAP|PERSON|", "HON:D000001")
    assert len(gap) == 2
    assert gap[0]["quarters_observed"] == ["2016Q1"] and gap[0]["break_reason"] == "DATE_GAP_WITHIN_CONSECUTIVE_QUARTERS"
    assert gap[0]["gap_days_to_next_span"] == 14
    assert gap[1]["quarters_observed"] == ["2016Q2", "2016Q3"] and gap[1]["break_reason"] == "NOT_OBSERVED_AFTER"


def test_orphan_family_and_payee_flags(build_2016):
    obs = build_2016["obs"]
    assert not spans_for(build_2016, "SOD:ORPHAN|ONLY|", "HON:D000001")
    orphan = next(o for o in obs if o["payee_raw"] == "ORPHAN ONLY")
    assert "ORPHAN_COMPENSATION_CELL" in orphan["review_flags"] and orphan["compensation_class"] == "OTHER COMPENSATION"
    collide = [o for o in obs if o["payee_raw"].startswith("COLLIDE")]
    assert all("PERSON_KEY_FAMILY_COLLISION" in o["review_flags"] for o in collide)
    link_empty = next(o for o in obs if o["payee_raw"] == "LINK BOB")
    link_full = next(o for o in obs if o["payee_raw"] == "LINK BOB D")
    assert link_empty["family_link_candidate"] == "SOD:LINK|BOB|D" and "MIDDLE_INITIAL_ABSENT_IN_FAMILY" in link_empty["review_flags"]
    assert link_full["family_link_candidate"] is None and "MIDDLE_INITIAL_ABSENT_IN_FAMILY" in link_full["review_flags"]
    fischer = next(o for o in obs if o["payee_raw"] == "FISCHER JR ROBERT V.")
    assert fischer["person_key"] == "SOD:FISCHER|ROBERT|V" and fischer["payee_parse"]["suffix_tokens"] == ["JR"]
    connelly = next(o for o in obs if o["payee_raw"] == "CONNELLY HENRY V")
    assert connelly["person_key"] == "SOD:CONNELLY|HENRY|V" and connelly["title_truncated_30"] is True
    empty = next(o for o in obs if o["payee_raw"] == "")
    assert empty["person_key"] is None and "PAYEE_EMPTY" in empty["review_flags"]
    straddle = next(o for o in obs if o["office_raw"] == "2015 HON. JANE DOE")
    assert straddle["interval_vs_quarter"] == "STRADDLES_QUARTER_EDGE" and straddle["allowance_year"] == 2015 and straddle["office_key"] == "HON:D000001"
    share = [o for o in obs if o["payee_raw"] == "SHARE PERSON"]
    assert {o["office_key"] for o in share} == {"HON:D000001", "HON:L000570"} and all(o["shared_employee_flag"] for o in share)
    assert len(spans_for(build_2016, "SOD:SHARE|PERSON|", "HON:L000570")) == 1
    assert build_2016["receipt"]["observation_conservation"]["identity_holds"] is True
    assert build_2016["receipt"]["totals"]["person_key_family_shape_histogram"]["FAMILY_MULTIPLE_MIDDLE_INITIALS"] == 1
    assert build_2016["receipt"]["totals"]["person_key_family_shape_histogram"]["FAMILY_ONE_INITIAL_PLUS_EMPTY"] == 1


def test_source_row_index_is_data_row_ordinal(build_2016):
    obs = build_2016["obs"]
    first = next(o for o in obs if o["quarter"] == "2016Q1" and o["payee_raw"] == "SMITH JOHN Q" and o["office_raw"] == "2015 HON. JANE DOE")
    assert first["source_row_index"] == 1 and first["source_file"] == "2016q1_sod_detail.csv"
    travel_excluded = [o for o in obs if o["title_raw"] == "PRIVATE AUTO MILEAGE"]
    assert travel_excluded == []
    assert first["observation_id"].startswith("sod:obs:") and len(first["observation_id"]) == len("sod:obs:") + 64


# ---------------------------------------------------------------------------
# PDF-era admission and failure modes
# ---------------------------------------------------------------------------

def pdf_row(period, office, payee, start, end, title, amount, page, y):
    return {
        "schema_id": "staffer-network-house-sod-pdf-payroll-candidate-v1",
        "period": period, "period_start": f"{period[:4]}-10-01", "period_end": f"{period[:4]}-12-31",
        "employing_office_raw": office, "payee_raw": payee, "service_start_date_raw": start, "service_end_date_raw": end,
        "service_start_date_candidate_iso": bl.dt.datetime.strptime(start, "%m/%d/%y").date().isoformat(),
        "service_end_date_candidate_iso": bl.dt.datetime.strptime(end, "%m/%d/%y").date().isoformat(),
        "title_description_raw": title, "amount_raw": amount, "source_pdf_page_number": page, "source_pdf_row_y_milli": y,
        "source_pdf_sha256": "ab" * 32, "source_url": "https://www.house.gov/sites/default/files/uploads/documents/2015q4-singlevolume.pdf",
        "candidate_id": f"house-sod-pdf-payroll:{'0' * 64}",
    }


def write_pdf_rows(path: Path, rows: list[dict]) -> None:
    with bl.DeterministicGzipWriter(path) as writer:
        for row in rows:
            writer.write(row)


def test_pdf_rows_are_admitted_and_flagged(tmp_path):
    roster = make_roster(tmp_path)
    csv_root = make_csv_root_2016(tmp_path)
    pdf = tmp_path / "pdf_rows.ndjson.gz"
    write_pdf_rows(pdf, [
        pdf_row("2015Q4", "2015 HON. JANE DOE—Con.", "SMITH, JOHN Q.", "10/01/15", "12/31/15", "STAFF ASSISTANT", "9,000.00", 5, 12345),
        pdf_row("2015Q4", "2015 HON. JANE DOE—Con.", "DO", "10/01/15", "12/31/15", "STAFF ASSISTANT (OVERTIME)", "–100.00", 5, 12400),
    ])
    out = tmp_path / "gen_pdf"
    receipt = run_build(csv_root, roster, out, ["--pdf-rows", str(pdf)])
    assert receipt["inputs"]["pdf_era"]["status"] == "INGESTED"
    assert receipt["per_quarter"]["2015Q4"]["admitted_rows"] == 2
    obs = [o for o in read_gz(out / bl.OBSERVATIONS_NAME) if o["source_form"] == "house_gov_single_volume_pdf"]
    assert len(obs) == 2 and all(o["row_admission"] == "PDF_LAYOUT_TEXT" for o in obs)
    smith = next(o for o in obs if o["payee_raw"] == "SMITH, JOHN Q.")
    assert smith["person_key"] == "SOD:SMITH|JOHN|Q" and smith["office_key"] == "HON:D000001" and smith["amount"] == "9000.00"
    assert smith["source_locator"]["source_pdf_page_number"] == 5 and smith["source_file"] == "pdf_rows.ndjson.gz"
    ditto = next(o for o in obs if o["payee_raw"] == "DO")
    assert ditto["person_key"] is None and "PAYEE_SINGLE_TOKEN" in ditto["review_flags"] and ditto["amount"] == "-100.00"
    spans = read_gz(out / bl.SPANS_NAME)
    first = sorted((s for s in spans if s["person_key"] == "SOD:SMITH|JOHN|Q" and s["office_key"] == "HON:D000001"), key=lambda s: s["run_index"])[0]
    assert first["quarters_observed"][0] == "2015Q4" and first["service_start_min"] == "2015-10-01"
    assert "SPAN_MIXES_SOURCE_FORMS" in first["review_flags"] and first["source_forms"] == ["detail_csv", "house_gov_single_volume_pdf"]


def test_pdf_rows_out_of_period_order_fail_closed(tmp_path):
    roster = make_roster(tmp_path)
    csv_root = make_csv_root_2016(tmp_path)
    pdf = tmp_path / "pdf_bad.ndjson.gz"
    write_pdf_rows(pdf, [
        pdf_row("2015Q4", "2015 HON. JANE DOE", "SMITH, JOHN Q.", "10/01/15", "12/31/15", "STAFF ASSISTANT", "9,000.00", 5, 1),
        pdf_row("2015Q3", "2015 HON. JANE DOE", "SMITH, JOHN Q.", "07/01/15", "09/30/15", "STAFF ASSISTANT", "9,000.00", 5, 2),
    ])
    code = bl.main(["--output-root", str(tmp_path / "gen_bad"), "--csv-root", str(csv_root), "--roster-root", str(roster),
                    "--url-inventory", str(tmp_path / "none.json"), "--pdf-rows", str(pdf)])
    assert code == 2 and not (tmp_path / "gen_bad" / bl.OBSERVATIONS_NAME).exists()


# ---------------------------------------------------------------------------
# PDF-era member quarters and the verifier's PDF-era coverage
# ---------------------------------------------------------------------------

PDF_ERA_ROWS_SPEC = [
    # 2015Q3 and 2015Q4 are absent from the 2016 CSV fixture, so they are PDF-only quarters.
    ("2015Q3", "2015 HON. JANE DOE—Con.", "SMITH, JOHN Q.", "07/01/15", "09/30/15", "STAFF ASSISTANT", "8,000.00", 3, 1000),
    ("2015Q4", "2015 HON. JANE DOE—Con.", "SMITH, JOHN Q.", "10/01/15", "12/31/15", "STAFF ASSISTANT", "9,000.00", 5, 1000),
    # single-token payee: admitted, unkeyed, so it counts as a personnel row but not a person
    ("2015Q4", "2015 HON. JANE DOE—Con.", "DO", "10/01/15", "12/31/15", "STAFF ASSISTANT (OVERTIME)", "–100.00", 5, 2000),
    # leadership container: admitted as an observation, never a member-quarter row
    ("2015Q4", "2015 OFFICE OF THE SPEAKER—Con.", "STAFF, ALICE B.", "10/01/15", "12/31/15", "SENIOR ADVISOR", "12,000.00", 9, 1000),
]


@pytest.fixture(scope="module")
def build_pdf_era(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("pdfera")
    roster = make_roster(tmp)
    csv_root = make_csv_root_2016(tmp)
    pdf = tmp / "pdf_era_rows.ndjson.gz"
    write_pdf_rows(pdf, [pdf_row(*spec) for spec in PDF_ERA_ROWS_SPEC])
    out = tmp / "gen_primary"
    twin = tmp / "gen_twin"
    receipt = run_build(csv_root, roster, out, ["--pdf-rows", str(pdf)])
    run_build(csv_root, roster, twin, ["--pdf-rows", str(pdf)])
    csv_only = tmp / "gen_csv_only"
    csv_only_receipt = run_build(csv_root, roster, csv_only)
    return {"tmp": tmp, "roster": roster, "csv_root": csv_root, "pdf": pdf, "out": out, "twin": twin,
            "receipt": receipt, "csv_only_receipt": csv_only_receipt}


def test_pdf_era_member_quarters_carry_pdf_markers(build_pdf_era):
    rows = read_gz(build_pdf_era["out"] / bl.MEMBER_QUARTERS_NAME)
    pdf_rows_out = [r for r in rows if r["era"] == bl.ERA_PDF]
    assert {(r["quarter"], r["office_raw"]) for r in pdf_rows_out} == {
        ("2015Q3", "2015 HON. JANE DOE—Con."), ("2015Q4", "2015 HON. JANE DOE—Con.")}
    # the leadership office is admitted as an observation but is not a member container
    assert not any(r["office_raw"].startswith("2015 OFFICE OF THE SPEAKER") for r in rows)
    speaker_obs = [o for o in read_gz(build_pdf_era["out"] / bl.OBSERVATIONS_NAME)
                   if o["office_raw"] == "2015 OFFICE OF THE SPEAKER—Con."]
    assert len(speaker_obs) == 1 and speaker_obs[0]["container_kind"] == "leadership"

    q4 = next(r for r in pdf_rows_out if r["quarter"] == "2015Q4")
    assert q4["schema_id"] == "staffer-network-sod-member-office-quarter-v2"
    assert q4["source_form"] == bl.PDF_SOURCE_FORM
    assert q4["program"] is None
    assert q4["subtotal_basis"] == bl.SUBTOTAL_BASIS_PDF
    assert q4["personnel_subtotal_row_total"] is None      # never a fabricated 0
    assert q4["personnel_reconciliation"] == "NO_SUBTOTAL_ROW"
    assert q4["intern_row_count"] is None and q4["intern_total"] is None  # no program split to be 0
    assert q4["personnel_row_count"] == 2 and q4["staff_count"] == 1      # DO is admitted but unkeyed
    assert q4["personnel_total"] == "8900.00"                             # 9,000.00 + (-100.00)
    assert q4["rows_any_class"] == 2 and q4["rows_any_class_basis"] == bl.ROWS_BASIS_PDF
    assert q4["organization_codes"] == []
    assert q4["member_bioguide"] == "D000001" and q4["office_key"] == "HON:D000001"
    assert q4["programs"] == [{
        "program": None, "source_forms": [bl.PDF_SOURCE_FORM], "personnel_row_count": 2, "base_row_count": 1,
        "other_comp_row_count": 0, "overtime_row_count": 1, "shared_employee_title_rows": 0, "negative_rows": 1,
        "unkeyed_rows": 1, "distinct_person_keys": 1, "personnel_detail_sum": "8900.00",
        "personnel_subtotal_rows": 0, "personnel_subtotal_sum": "0", "reconciliation": "NO_SUBTOTAL_ROW"}]
    q3 = next(r for r in pdf_rows_out if r["quarter"] == "2015Q3")
    assert q3["personnel_row_count"] == 1 and q3["staff_count"] == 1 and q3["personnel_total"] == "8000.00"

    # CSV-era rows keep their CSV markers and are unchanged in number by the PDF pass
    csv_rows = [r for r in rows if r["era"] == bl.ERA_CSV]
    assert all(r["source_form"] == bl.CSV_SOURCE_FORM and r["rows_any_class_basis"] == bl.ROWS_BASIS_CSV for r in csv_rows)
    assert all(r["intern_row_count"] is not None and r["intern_total"] is not None for r in csv_rows)
    assert any(r["subtotal_basis"] == bl.SUBTOTAL_BASIS_CSV_ROW for r in csv_rows)
    assert len(csv_rows) == build_pdf_era["csv_only_receipt"]["totals"]["member_quarter_rows"]

    totals = build_pdf_era["receipt"]["totals"]
    assert totals["member_quarter_rows_by_era"] == {bl.ERA_CSV: len(csv_rows), bl.ERA_PDF: 2}
    assert totals["member_quarter_rows"] == len(rows) == len(csv_rows) + 2
    assert totals["member_quarter_distinct_office_keys_by_era"][bl.ERA_PDF] == 1
    assert totals["member_quarter_quarters_without_rows_despite_member_office_rows"] == []
    checks = build_pdf_era["receipt"]["invariant_checks"]
    assert checks["every_quarter_with_member_office_rows_has_member_quarters"] is True
    for quarter in ("2015Q3", "2015Q4"):
        assert build_pdf_era["receipt"]["per_quarter"][quarter]["member_quarter_rows"] >= 1


def test_pdf_era_build_twin_is_byte_identical(build_pdf_era):
    for name in (bl.OBSERVATIONS_NAME, bl.SPANS_NAME, bl.MEMBER_QUARTERS_NAME, bl.RECEIPT_NAME):
        assert (build_pdf_era["out"] / name).read_bytes() == (build_pdf_era["twin"] / name).read_bytes(), name


def test_verifier_pdf_era_coverage_requires_pdf_rows(build_pdf_era):
    """Without --pdf-rows the PDF era is unread: say so and fail, never pass a subset."""
    common = ["--primary", str(build_pdf_era["out"]), "--twin", str(build_pdf_era["twin"]),
              "--csv-root", str(build_pdf_era["csv_root"])]
    without = build_pdf_era["tmp"] / "ver_without_pdf"
    code = vl.main(common + ["--output-root", str(without)])
    report = json.loads((without / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert code == 1 and report["status"] == "FAIL"
    assert report["pdf_era_coverage"] == "NOT_SUPPLIED"
    assert report["details"]["pdf_era_coverage"] == "NOT_SUPPLIED"
    assert report["checks"]["pdf_era_covered"] is False
    assert report["checks"]["reconciliation_histogram_equals_receipt"] is False
    assert "pdf_rows_sha256_matches_receipt" not in report["checks"]
    # the CSV-only histogram is a strict subset of the receipt's full-era histogram
    receipt_recon = build_pdf_era["receipt"]["totals"]["personnel_block_reconciliation"]
    assert report["details"]["personnel_block_reconciliation"] != receipt_recon
    assert receipt_recon["NO_SUBTOTAL_ROW"] == 3  # 2 JANE DOE blocks + 1 SPEAKER block

    with_pdf = build_pdf_era["tmp"] / "ver_with_pdf"
    code = vl.main(common + ["--output-root", str(with_pdf), "--pdf-rows", str(build_pdf_era["pdf"]),
                             "--script", str(HERE / "build_house_personnel_ledger.py"),
                             "--script", str(HERE / "verify_house_personnel_ledger.py")])
    report = json.loads((with_pdf / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert code == 0, {k: v for k, v in report["checks"].items() if not v}
    assert report["status"] == "PASS"
    assert report["pdf_era_coverage"] == "VERIFIED"
    assert report["checks"]["pdf_era_covered"] is True
    assert report["checks"]["reconciliation_histogram_equals_receipt"] is True
    assert report["checks"]["pdf_rows_sha256_matches_receipt"] is True
    assert report["checks"]["pdf_rows_schema_id_uniform"] is True
    assert report["checks"]["pdf_rows_carry_no_program_or_subtotal_column"] is True
    assert report["checks"]["per_quarter_counts_pdf_equals_observations"] is True
    assert report["checks"]["member_quarters_pdf_era_rows_marked"] is True
    assert report["checks"]["block_sums_observations_equal_pdf"] is True
    assert report["details"]["personnel_block_reconciliation"] == receipt_recon
    assert report["details"]["personnel_block_reconciliation_pdf_era_blocks"] == 3
    assert report["details"]["member_quarter_rows_by_era"][bl.ERA_PDF] == 2
    assert report["details"]["pdf_era"]["quarters_read"] == 2
    assert report["details"]["pdf_era"]["rows_read"] == len(PDF_ERA_ROWS_SPEC)
    assert report["details"]["per_quarter"]["2015Q4"] == {
        "csv_recount": 0, "pdf_recount": 3, "observations": 3,
        "receipt": build_pdf_era["receipt"]["per_quarter"]["2015Q4"]["admitted_rows"]}


def test_mixed_era_member_quarter_uses_the_csv_program_block(tmp_path):
    """A --pdf-rows extraction that overlaps a CSV quarter is labelled, not silently merged."""
    roster = make_roster(tmp_path)
    csv_root = make_csv_root_2016(tmp_path)
    pdf = tmp_path / "pdf_overlap.ndjson.gz"
    write_pdf_rows(pdf, [pdf_row("2016Q4", "2016 HON. JANE DOE", "PDFPERSON, PAT", "10/01/16", "12/31/16",
                                 "CASEWORKER", "1,111.00", 7, 500)])
    out = tmp_path / "gen_mixed"
    twin = tmp_path / "gen_mixed_twin"
    receipt = run_build(csv_root, roster, out, ["--pdf-rows", str(pdf)])
    run_build(csv_root, roster, twin, ["--pdf-rows", str(pdf)])
    rows = read_gz(out / bl.MEMBER_QUARTERS_NAME)
    mixed = next(r for r in rows if r["quarter"] == "2016Q4" and r["office_raw"] == "2016 HON. JANE DOE")
    assert mixed["era"] == bl.ERA_MIXED
    assert mixed["source_form"] == bl.CSV_SOURCE_FORM + "+" + bl.PDF_SOURCE_FORM
    assert mixed["rows_any_class_basis"] == bl.ROWS_BASIS_MIXED
    # the scalars stay on the CSV program block; the PDF block is visible but not folded in
    assert mixed["program"] == OEM and mixed["subtotal_basis"] == bl.SUBTOTAL_BASIS_CSV_ROW
    assert mixed["personnel_total"] == "4500" and mixed["personnel_subtotal_row_total"] == "4500"
    assert mixed["staff_count"] == 1 and mixed["personnel_row_count"] == 1
    assert mixed["intern_row_count"] == 0 and mixed["intern_total"] == "0"
    assert [(p["program"], p["personnel_detail_sum"]) for p in mixed["programs"]] == [
        (None, "1111.00"), (OEM, "4500")]
    assert receipt["totals"]["member_quarter_rows_by_era"][bl.ERA_MIXED] == 1
    assert receipt["totals"]["member_quarter_rows_by_era"].get(bl.ERA_PDF) is None
    verification = tmp_path / "ver_mixed"
    code = vl.main(["--primary", str(out), "--twin", str(twin), "--csv-root", str(csv_root),
                    "--pdf-rows", str(pdf), "--output-root", str(verification)])
    report = json.loads((verification / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert code == 0, {k: v for k, v in report["checks"].items() if not v}
    assert report["checks"]["pdf_and_csv_blocks_disjoint"] is True
    assert report["details"]["member_quarter_rows_by_era"][bl.ERA_MIXED] == 1


def test_verifier_pdf_rows_supplied_to_a_csv_only_build_is_flagged(build_pdf_era, tmp_path):
    csv_only = build_pdf_era["tmp"] / "gen_csv_only"
    out = tmp_path / "ver_csv_only_with_pdf"
    code = vl.main(["--primary", str(csv_only), "--csv-root", str(build_pdf_era["csv_root"]),
                    "--output-root", str(out), "--pdf-rows", str(build_pdf_era["pdf"])])
    report = json.loads((out / vl.REPORT_NAME).read_text(encoding="utf-8"))
    assert code == 1
    assert report["pdf_era_coverage"] == "SUPPLIED_BUT_BUILD_WAS_CSV_ONLY"
    assert report["checks"]["pdf_era_covered"] is False


def test_unknown_header_names_the_quarter(tmp_path):
    roster = make_roster(tmp_path)
    root = tmp_path / "csvbad"
    root.mkdir()
    write_csv(root / "2016q1_sod_detail.csv", HEADER_12, Q2016Q1)
    write_csv(root / "2016q2_sod_detail.csv", "ORGANIZATION,PROGRAM,AMOUNT", ["2016 HON. JANE DOE,X,1"])
    args = bl.parse_args(["--output-root", str(tmp_path / "gen_hdr"), "--csv-root", str(root), "--roster-root", str(roster),
                          "--url-inventory", str(tmp_path / "none.json")])
    with pytest.raises(bl.BuildError, match="2016q2_sod_detail.csv: unknown header"):
        bl.LedgerBuild(args).run()
