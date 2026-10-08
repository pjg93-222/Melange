#!/usr/bin/env python3
"""Build a deterministic, review-only lane from official Senate reports.

The lane inventories the Secretary of the Senate's semiannual report archive,
downloads one full GovInfo PDF at a time through a single pacer, and extracts
payee/title candidates from the ``SALARIES, OFFICERS AND EMPLOYEES`` pages.
Rows remain unverified candidates.  This script never links a payee to a
canonical person, asserts complete employment history, or promotes exact dates.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html.parser
import json
import os
from pathlib import Path
import re
import shutil
import time
from typing import Any
import urllib.parse
import urllib.request

from pypdf import PdfReader


ARCHIVE_URL = "https://www.senate.gov/legislative/common/generic/report_secsen.htm"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "official_senate_payroll_20260831"
USER_AGENT = "MelangeSystemsSenateReport/1.0 (official-public-data research; sequential requests)"
INVENTORY_SCHEMA_ID = "staffer-network-official-senate-report-inventory-v1"
CANDIDATE_SCHEMA_ID = "staffer-network-official-senate-payroll-candidate-v1"
RECEIPT_SCHEMA_ID = "staffer-network-official-senate-payroll-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-official-senate-payroll-manifest-v1"
PARSER_VERSION = "senate-payroll-parser-v5"

PERIOD_RE = re.compile(
    r"^(January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(\d{1,2}), (20\d{2}) to "
    r"(January|February|March|April|May|June|July|August|September|October|November|December) "
    r"(\d{1,2}), (20\d{2})$"
)
PACKAGE_RE = re.compile(r"/(GPO-CDOC-[^/]+)/", re.IGNORECASE)
OFFICE_RE = re.compile(
    r"DETAILED AND SUMMARY STATEMENT OF EXPENDITURES\s*\n(.+?)\nFunding Year\s+\d{4}\b",
    re.DOTALL,
)
PAYROLL_LINE_RE = re.compile(
    r"^(?P<left>[A-ZÀ-ÖØ-Þ][A-Z0-9À-ÖØ-Þ .,'’&()/-]+)\s*\$\s*(?P<amount>[0-9,]+\.\d{2})$"
)
QUALIFIER_RE = re.compile(
    r"\b(?P<kind>FROM|TO)\s+"
    r"(?P<month>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\.\s*"
    r"(?P<day>\d{1,2})\b"
)
TITLE_STARTERS = {
    "ACCOUNTANT", "ACCOUNTS", "ACTING", "ADMINISTRATIVE", "ADMINISTRATOR", "ADVANCE",
    "ADVISOR", "AIDE", "ANALYST", "APPOINTMENT", "ARCHITECT", "ARCHIVIST", "ART",
    "ASSISTANT", "ASSOCIATE", "ATTORNEY", "BROADCAST", "BUDGET", "CAPITOL", "CHAMBER",
    "CHAPLAIN", "CHIEF", "CLERK", "COMMUNICATIONS", "CONSTITUENT", "CORRESPONDENT",
    "COUNSEL", "CUSTOMER", "CYBERSECURITY", "DEPUTY", "DIGITAL", "DIRECTOR", "DOORKEEPER",
    "EAP", "ECONOMIST", "EDITOR", "ENGINEER", "ENGAGEMENT", "EXECUTIVE", "FIELD", "FINANCIAL",
    "FRAMER", "FURNISHINGS", "GENERAL", "GRAPHIC", "HAIR", "HUMAN", "INFORMATION", "INTERN",
    "IT", "JOURNALIST", "JUNIOR", "LABOR", "LAW", "LEAD", "LEGAL", "LEGISLATIVE",
    "LIBRARIAN", "LOGISTICS", "MAIL", "MAJORITY", "MANAGER", "MINORITY", "NETWORK", "OFFICE",
    "OPERATIONS", "OUTREACH", "PAGE", "PARKING", "PASSPORT", "PERSONAL", "PHOTOGRAPHER", "PHYSICAL",
    "POLICY", "PRESS", "PRINCIPAL", "PRINTING", "PROCTOR", "PROFESSIONAL", "PROGRAM",
    "PROJECT", "PROJECTS", "PROTECTIVE", "RAPID", "REALTIME", "RECEPTIONIST", "RECORDS",
    "REGIONAL", "REPORTER", "REPROGRAPHICS", "RESEARCH", "RESEARCHER", "RESIDENCE", "RTM",
    "SCHEDULER", "SCHEDULING", "SCOPIST", "SECRETARY", "SENATOR", "SENIOR", "SERVICE",
    "SHUTTLE", "SPECIAL", "SPECIALIST", "SPEECHWRITER", "STAFF", "STATE", "SUBCOMMITTEE",
    "SUPERVISOR", "SYSTEMS", "TECHNICIAN", "TECHNOLOGY", "TRANSPORTATION", "VENDOR", "WATCH",
    "WINDOW", "WRITER",
}
TITLE_TERMINALS = {
    "ACCOUNTANT", "ADMINISTRATOR", "ADVISOR", "AIDE", "ANALYST", "ARCHITECT", "ARCHIVIST",
    "ASSISTANT", "ATTORNEY", "CAPTIONER", "CHAPLAIN", "CLERK", "COORDINATOR", "CORRESPONDENT",
    "COUNSEL", "DIRECTOR", "DOORKEEPER", "ECONOMIST", "EDITOR", "ENGINEER", "FRAMER",
    "INTERN", "JOURNALIST", "LIBRARIAN", "MANAGER", "MEMBER", "OPERATOR", "PAGE",
    "PHOTOGRAPHER", "PROCTOR", "RECEPTIONIST", "REPORTER", "REPRESENTATIVE", "RESEARCHER",
    "SCHEDULER", "SCOPIST", "SECRETARY", "SPECIALIST", "SPEECHWRITER", "STAFF", "SUPERVISOR",
    "TECHNICIAN", "WRITER", "AFFAIRS", "CENTER", "CHAIRMAN", "DIRECTOR-DPCC", "GENERALIST", "MEDIA",
}
OLD_AMOUNT_START_RE = re.compile(r"^(?P<amount>[0-9]{1,3}(?:,[0-9]{3})*\.\d{2})(?P<rest>.+)$")
OLD_FULL_PAYEE_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ .'’&()/-]+,\s*[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ .'’&()/-]+$")
OLD_DATE_TITLE_BOUNDARY_RE = re.compile(
    r"^(?P<title>.*\b(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|SEPT|OCT|NOV|DEC)\.\s*\d{1,2})"
    r"(?P<surname>[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ'’ .&()/-]{1,35})$"
)
MONTH_NUMBER = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "SEPT": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bytes_atomic(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def write_json_atomic(path: Path, value: Any) -> None:
    write_bytes_atomic(path, (compact_json(value) + "\n").encode("utf-8"))


def write_ndjson_atomic(path: Path, rows: list[dict[str, Any]]) -> None:
    value = "".join(compact_json(row) + "\n" for row in rows).encode("utf-8")
    write_bytes_atomic(path, value)


class AnchorCollector(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.anchors: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a" or self._href is not None:
            return
        href = dict(attrs).get("href")
        if href:
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


class SharedPacer:
    def __init__(self, minimum_interval_seconds: float) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self._last_request_started: float | None = None

    def wait(self) -> None:
        if self._last_request_started is not None:
            remaining = self.minimum_interval_seconds - (time.monotonic() - self._last_request_started)
            if remaining > 0:
                time.sleep(remaining)
        self._last_request_started = time.monotonic()

    def get(self, url: str, accept: str) -> bytes:
        self.wait()
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
        with urllib.request.urlopen(request, timeout=180) as response:
            return response.read()


def parse_period(label: str) -> tuple[str, str] | None:
    match = PERIOD_RE.match(label)
    if not match:
        return None
    start = dt.datetime.strptime(
        f"{match.group(1)} {match.group(2)}, {match.group(3)}", "%B %d, %Y"
    ).date()
    end = dt.datetime.strptime(
        f"{match.group(4)} {match.group(5)}, {match.group(6)}", "%B %d, %Y"
    ).date()
    return start.isoformat(), end.isoformat()


def expected_period_starts(first: str, last: str) -> list[str]:
    current = dt.date.fromisoformat(first)
    end = dt.date.fromisoformat(last)
    expected: list[str] = []
    while current <= end:
        expected.append(current.isoformat())
        current = dt.date(current.year, 10, 1) if current.month == 4 else dt.date(current.year + 1, 4, 1)
    return expected


def build_inventory(index_bytes: bytes) -> dict[str, Any]:
    parser = AnchorCollector()
    parser.feed(index_bytes.decode("utf-8", errors="replace"))
    periods: dict[str, dict[str, Any]] = {}
    for href, label in parser.anchors:
        bounds = parse_period(label)
        package_match = PACKAGE_RE.search(href)
        if bounds is None or package_match is None or "/app/details/" not in href:
            continue
        package_id = package_match.group(1)
        periods[package_id] = {
            "context_url": urllib.parse.urljoin(ARCHIVE_URL, href),
            "full_pdf_url": None,
            "label": label,
            "package_id": package_id,
            "part_i_pdf_url": None,
            "part_ii_pdf_url": None,
            "period_end": bounds[1],
            "period_start": bounds[0],
        }
    for href, label in parser.anchors:
        package_match = PACKAGE_RE.search(href)
        if package_match is None or package_match.group(1) not in periods or not href.lower().endswith(".pdf"):
            continue
        row = periods[package_match.group(1)]
        absolute = urllib.parse.urljoin(ARCHIVE_URL, href)
        if label == "Full Report":
            row["full_pdf_url"] = absolute
        elif label == "Part I":
            row["part_i_pdf_url"] = absolute
        elif label == "Part II":
            row["part_ii_pdf_url"] = absolute
    ordered = sorted(periods.values(), key=lambda row: (row["period_start"], row["package_id"]))
    incomplete = [row["package_id"] for row in ordered if not all(
        row[key] for key in ("full_pdf_url", "part_i_pdf_url", "part_ii_pdf_url")
    )]
    if not ordered:
        raise RuntimeError("Official Senate archive yielded no semiannual reports")
    present_starts = [row["period_start"] for row in ordered]
    expected_starts = expected_period_starts(min(present_starts), max(present_starts))
    missing_starts = sorted(set(expected_starts) - set(present_starts))
    if incomplete or missing_starts:
        raise RuntimeError(f"Archive inventory gaps: incomplete={incomplete}; missing={missing_starts}")
    return {
        "archive_index": {
            "bytes": len(index_bytes),
            "sha256": sha256_bytes(index_bytes),
            "url": ARCHIVE_URL,
        },
        "coverage": {
            "first_period_start": ordered[0]["period_start"],
            "full_pdf_endpoint_count": len(ordered),
            "last_period_end": ordered[-1]["period_end"],
            "missing_semiannual_period_starts": missing_starts,
            "part_i_pdf_endpoint_count": len(ordered),
            "part_ii_pdf_endpoint_count": len(ordered),
            "period_count": len(ordered),
            "total_pdf_endpoint_count": len(ordered) * 3,
        },
        "periods": ordered,
        "schema_id": INVENTORY_SCHEMA_ID,
    }


def load_source_bytes(path: Path | None, url: str, pacer: SharedPacer, accept: str) -> bytes:
    if path is not None:
        return path.read_bytes()
    return pacer.get(url, accept)


def title_split(left: str) -> tuple[str | None, str | None, str]:
    if "," not in left:
        return None, None, "NO_COMMA"
    surname, remainder = left.split(",", 1)
    remainder = remainder.strip()
    tokens = remainder.split()
    for index in range(1, len(tokens)):
        normalized = re.sub(r"[^A-Z]", "", tokens[index].upper())
        if normalized in TITLE_STARTERS:
            return f"{surname.strip()}, {' '.join(tokens[:index])}", " ".join(tokens[index:]), "HEURISTIC_SPLIT"
    return None, None, "UNSPLIT_REVIEW_REQUIRED"


def old_layout_office(text: str) -> str | None:
    lines = [" ".join(line.split()) for line in text.splitlines()]
    for index, line in enumerate(lines):
        if line.upper() != "AUTHORIZATION":
            continue
        candidates: list[str] = []
        for following in lines[index + 1:index + 7]:
            if "NET PAYROLL EXPENSES" in following.upper():
                break
            if (
                following
                and any(character.isalpha() for character in following)
                and not re.search(r"\d", following)
                and not following.startswith("$")
            ):
                candidates.append(following)
        if candidates:
            return " ".join(candidates)
    return None


def split_old_inline_title_payee(value: str) -> tuple[str | None, str | None, str]:
    if "," not in value:
        return None, None, "UNSPLIT_REVIEW_REQUIRED"
    before_comma, given = value.rsplit(",", 1)
    given = given.strip()
    if not given or not re.fullmatch(r"[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ .'’&()/-]*", given):
        return None, None, "UNSPLIT_REVIEW_REQUIRED"
    date_match = OLD_DATE_TITLE_BOUNDARY_RE.match(before_comma)
    if date_match:
        return (
            f"{date_match.group('surname').strip()}, {given}",
            date_match.group("title").strip(),
            "HISTORICAL_REVERSE_LAYOUT_HEURISTIC_SPLIT",
        )
    choices: list[tuple[int, str, str]] = []
    for terminal in TITLE_TERMINALS | TITLE_STARTERS:
        if len(re.sub(r"[^A-Z]", "", terminal)) < 4:
            continue
        for match in re.finditer(re.escape(terminal), before_comma):
            if match.start() and before_comma[match.start() - 1].isalpha():
                continue
            surname = before_comma[match.end():].strip()
            if re.fullmatch(r"[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ'’ .&()/-]{1,35}", surname):
                choices.append((match.end(), before_comma[:match.end()].strip(), surname))
    if not choices:
        return None, None, "UNSPLIT_REVIEW_REQUIRED"
    _, title, surname = max(choices, key=lambda item: item[0])
    return f"{surname}, {given}", title, "HISTORICAL_REVERSE_LAYOUT_HEURISTIC_SPLIT"


def extract_old_layout_rows(text: str) -> list[dict[str, str | None]]:
    rows: list[dict[str, str | None]] = []
    active_amount: str | None = None
    active_parts: list[str] = []

    def finish() -> None:
        nonlocal active_amount, active_parts
        if active_amount is None or not active_parts:
            active_amount = None
            active_parts = []
            return
        raw_body = " ".join(active_parts)
        if "NET PAYROLL EXPENSES" in raw_body.upper():
            active_amount = None
            active_parts = []
            return
        if re.search(r"\b\d{2}/\d{2}/\d{4}\b", raw_body):
            active_amount = None
            active_parts = []
            return
        if len(active_parts) > 1 and OLD_FULL_PAYEE_RE.fullmatch(active_parts[-1]):
            payee = active_parts[-1]
            title = " ".join(active_parts[:-1]).strip()
            status = "HISTORICAL_REVERSE_LAYOUT_LINE_SPLIT"
        else:
            payee, title, status = split_old_inline_title_payee(raw_body)
        if "," in raw_body:
            rows.append({
                "amount": active_amount,
                "payee": payee,
                "raw": active_amount + raw_body,
                "status": status,
                "title": title,
            })
        active_amount = None
        active_parts = []

    for raw in text.splitlines():
        line = " ".join(raw.split())
        amount_match = OLD_AMOUNT_START_RE.match(line)
        if amount_match:
            finish()
            active_amount = amount_match.group("amount")
            active_parts = [amount_match.group("rest")]
            if "," in active_parts[0]:
                finish()
            continue
        if active_amount is None:
            continue
        if line.startswith("B -") or line.startswith("B-") or len(active_parts) >= 4:
            finish()
            continue
        if line and re.fullmatch(r"[A-ZÀ-ÖØ-Þ0-9 .'’&(),/-]+", line):
            active_parts.append(line)
            if "," in line:
                finish()
        else:
            finish()
    finish()
    return rows


def resolve_qualifier_date(month: str, day: int, period_start: str, period_end: str) -> str | None:
    start = dt.date.fromisoformat(period_start)
    end = dt.date.fromisoformat(period_end)
    number = MONTH_NUMBER[month]
    for year in range(start.year, end.year + 1):
        try:
            candidate = dt.date(year, number, day)
        except ValueError:
            continue
        if start <= candidate <= end:
            return candidate.isoformat()
    return None


def parse_qualifiers(title: str | None, period_start: str, period_end: str) -> tuple[list[dict[str, Any]], list[dict[str, str]], str | None]:
    if not title:
        return [], [{"start": period_start, "end": period_end, "basis": "REPORT_PERIOD_ONLY"}], None
    qualifiers: list[dict[str, Any]] = []
    for match in QUALIFIER_RE.finditer(title):
        qualifiers.append({
            "kind": match.group("kind"),
            "raw": match.group(0),
            "resolved_date": resolve_qualifier_date(
                match.group("month"), int(match.group("day")), period_start, period_end
            ),
        })
    clean = QUALIFIER_RE.sub("", title)
    clean = re.sub(r"\s+AND\s*$|\s+", " ", clean).strip()
    if not qualifiers:
        return [], [{"start": period_start, "end": period_end, "basis": "REPORT_PERIOD_ONLY"}], clean
    if any(item["resolved_date"] is None for item in qualifiers):
        return qualifiers, [{
            "start": period_start,
            "end": period_end,
            "basis": "INVALID_OR_OUT_OF_PERIOD_QUALIFIER_REVIEW_REQUIRED",
        }], clean
    kinds = [item["kind"] for item in qualifiers]
    if kinds == ["FROM"]:
        intervals = [{"start": qualifiers[0]["resolved_date"], "end": period_end, "basis": "ROW_FROM_QUALIFIER"}]
    elif kinds == ["TO"]:
        intervals = [{"start": period_start, "end": qualifiers[0]["resolved_date"], "basis": "ROW_TO_QUALIFIER"}]
    elif kinds == ["FROM", "TO"]:
        if qualifiers[0]["resolved_date"] <= qualifiers[1]["resolved_date"]:
            intervals = [{
                "start": qualifiers[0]["resolved_date"],
                "end": qualifiers[1]["resolved_date"],
                "basis": "ROW_FROM_TO_QUALIFIERS",
            }]
        else:
            intervals = [{
                "start": period_start,
                "end": period_end,
                "basis": "INVALID_OR_REVERSED_QUALIFIER_RANGE_REVIEW_REQUIRED",
            }]
    elif kinds == ["TO", "FROM"]:
        if qualifiers[0]["resolved_date"] <= qualifiers[1]["resolved_date"]:
            intervals = [
                {"start": period_start, "end": qualifiers[0]["resolved_date"], "basis": "ROW_TO_QUALIFIER"},
                {"start": qualifiers[1]["resolved_date"], "end": period_end, "basis": "ROW_FROM_QUALIFIER"},
            ]
        else:
            intervals = [{
                "start": period_start,
                "end": period_end,
                "basis": "INVALID_OR_REVERSED_QUALIFIER_RANGE_REVIEW_REQUIRED",
            }]
    else:
        intervals = [{"start": period_start, "end": period_end, "basis": "COMPLEX_QUALIFIER_REVIEW_REQUIRED"}]
    return qualifiers, intervals, clean


def candidate_id(package_id: str, page: int, row_ordinal: int, raw_line: str) -> str:
    payload = compact_json([package_id, page, row_ordinal, raw_line]).encode("utf-8")
    return "senate:payroll-candidate:v1:" + sha256_bytes(payload)


def extract_candidates(pdf_path: Path, report: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    pdf_sha256 = sha256_file(pdf_path)
    candidates: list[dict[str, Any]] = []
    page_with_rows = 0
    split_counts: dict[str, int] = {}
    office_counts: dict[str, int] = {}
    interval_basis_counts: dict[str, int] = {}
    qualifier_row_count = 0
    unresolved_qualifier_row_count = 0
    invalid_or_reversed_qualifier_row_count = 0
    current_office: str | None = None
    for page_index, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        office_match = OFFICE_RE.search(text)
        if office_match is not None:
            current_office = " ".join(office_match.group(1).split())
        historical_office = old_layout_office(text)
        if historical_office is not None:
            current_office = historical_office
        if current_office is None:
            continue
        office = current_office
        page_rows = 0
        parsed_rows: list[dict[str, str | None]] = []
        for line in text.splitlines():
            raw_line = " ".join(line.split())
            line_match = PAYROLL_LINE_RE.match(raw_line)
            if line_match is None or "," not in line_match.group("left"):
                continue
            if re.search(r"\b\d{2}/\d{2}/\d{4}\b", line_match.group("left")):
                continue
            payee, title, split_status = title_split(line_match.group("left").strip())
            parsed_rows.append({
                "amount": line_match.group("amount"),
                "payee": payee,
                "raw": raw_line,
                "status": split_status,
                "title": title,
            })
        parsed_rows.extend(extract_old_layout_rows(text))
        for parsed in parsed_rows:
            payee = parsed["payee"]
            title = parsed["title"]
            split_status = parsed["status"] or "UNSPLIT_REVIEW_REQUIRED"
            raw_line = parsed["raw"] or ""
            qualifiers, intervals, title_candidate = parse_qualifiers(
                title, report["period_start"], report["period_end"]
            )
            if qualifiers:
                qualifier_row_count += 1
            if any(item["resolved_date"] is None for item in qualifiers):
                unresolved_qualifier_row_count += 1
            if any(interval["basis"].startswith("INVALID_OR_") for interval in intervals):
                invalid_or_reversed_qualifier_row_count += 1
            for interval in intervals:
                if not (
                    report["period_start"] <= interval["start"] <= interval["end"] <= report["period_end"]
                ):
                    raise RuntimeError(
                        f"Out-of-period or reversed interval escaped fail-closed parsing: "
                        f"{report['package_id']} {interval}"
                    )
                basis = interval["basis"]
                interval_basis_counts[basis] = interval_basis_counts.get(basis, 0) + 1
            row_ordinal = page_rows + 1
            page_rows += 1
            split_counts[split_status] = split_counts.get(split_status, 0) + 1
            office_counts[office] = office_counts.get(office, 0) + 1
            candidates.append({
                "amount_paid_raw": "$" + (parsed["amount"] or ""),
                "candidate_id": candidate_id(report["package_id"], page_index + 1, row_ordinal, raw_line),
                "canonical_employment_decision": "NOT_ADJUDICATED",
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "completeness_status": "PARTIAL",
                "date_intervals": intervals,
                "date_promotion_eligible": False,
                "employment_claim_status": "UNVERIFIED_CANDIDATE",
                "evidence_quote": raw_line,
                "identity_status": "UNVERIFIED_CANDIDATE",
                "office_raw": office,
                "page_number": page_index + 1,
                "parse_status": split_status,
                "payee_name_raw": payee,
                "promotion_gate": "BLOCKED_PENDING_IDENTITY_AND_ROW_REVIEW",
                "qualifiers": qualifiers,
                "report_package_id": report["package_id"],
                "report_period_end": report["period_end"],
                "report_period_start": report["period_start"],
                "row_ordinal_on_page": row_ordinal,
                "schema_id": CANDIDATE_SCHEMA_ID,
                "source_pdf_sha256": pdf_sha256,
                "source_pdf_url": report["full_pdf_url"],
                "source_tier": "OFFICIAL_SECRETARY_OF_THE_SENATE_REPORT",
                "title_candidate": title_candidate,
                "title_raw": title,
            })
        if page_rows:
            page_with_rows += 1
    ids = [row["candidate_id"] for row in candidates]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate Senate payroll candidate IDs")
    return candidates, {
        "candidate_count": len(candidates),
        "office_count": len(office_counts),
        "page_count": len(reader.pages),
        "pages_with_candidates": page_with_rows,
        "parser_version": PARSER_VERSION,
        "interval_basis_counts": dict(sorted(interval_basis_counts.items())),
        "qualifier_row_count": qualifier_row_count,
        "unresolved_qualifier_row_count": unresolved_qualifier_row_count,
        "invalid_or_reversed_qualifier_row_count": invalid_or_reversed_qualifier_row_count,
        "parse_status_counts": dict(sorted(split_counts.items())),
    }


def copy_or_download_pdf(args: argparse.Namespace, report: dict[str, Any], pacer: SharedPacer) -> Path:
    path = args.output_dir / "raw" / f"{report['package_id']}.pdf"
    if args.source_pdf:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".part")
        shutil.copyfile(args.source_pdf, temporary)
        os.replace(temporary, path)
    elif not path.exists():
        write_bytes_atomic(path, pacer.get(report["full_pdf_url"], "application/pdf,*/*;q=0.1"))
    return path


def artifact_description(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "path": path.name, "sha256": sha256_file(path)}


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = args.output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    pacer = SharedPacer(args.minimum_interval_seconds)

    index_bytes = load_source_bytes(args.source_index, args.archive_url, pacer, "text/html,*/*;q=0.1")
    index_path = raw_dir / "senate_report_archive_index.html"
    write_bytes_atomic(index_path, index_bytes)
    inventory = build_inventory(index_bytes)
    inventory_path = args.output_dir / "senate_report_archive_inventory.json"
    write_json_atomic(inventory_path, inventory)

    reports = inventory["periods"]
    report = reports[-1] if args.period == "latest" else next(
        (row for row in reports if row["period_start"] == args.period), None
    )
    if report is None:
        raise RuntimeError(f"No report found for period start {args.period}")
    pdf_path = copy_or_download_pdf(args, report, pacer)
    candidates, extraction = extract_candidates(pdf_path, report)
    candidate_path = args.output_dir / "senate_payroll_candidates.ndjson"
    write_ndjson_atomic(candidate_path, candidates)

    receipt = {
        "archive_coverage": inventory["coverage"],
        "archive_reports_extracted": 1,
        "archive_reports_remaining": inventory["coverage"]["period_count"] - 1,
        "candidate_file": artifact_description(candidate_path),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_history_assertions": 0,
        "extraction": extraction,
        "index_source": {
            "bytes": len(index_bytes),
            "sha256": sha256_bytes(index_bytes),
            "url": args.archive_url,
        },
        "inventory_file": artifact_description(inventory_path),
        "pdf_source": {
            "bytes": pdf_path.stat().st_size,
            "package_id": report["package_id"],
            "sha256": sha256_file(pdf_path),
            "url": report["full_pdf_url"],
        },
        "report_period_end": report["period_end"],
        "report_period_start": report["period_start"],
        "schema_id": RECEIPT_SCHEMA_ID,
        "sequencing_rule": "COLLECT_FIRST_IDENTITY_ADJUDICATION_LATER",
    }
    receipt_path = args.output_dir / "senate_payroll_receipt.json"
    write_json_atomic(receipt_path, receipt)
    manifest = {
        "artifacts": {
            "archive_index": artifact_description(index_path),
            "candidate_rows": artifact_description(candidate_path),
            "full_report_pdf": artifact_description(pdf_path),
            "inventory": artifact_description(inventory_path),
            "receipt": artifact_description(receipt_path),
        },
        "schema_id": MANIFEST_SCHEMA_ID,
    }
    write_json_atomic(args.output_dir / "manifest.json", manifest)
    print(compact_json(receipt))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-url", default=ARCHIVE_URL)
    parser.add_argument("--minimum-interval-seconds", type=float, default=2.0)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--period", default="latest", help="latest or an ISO period-start date")
    parser.add_argument("--source-index", type=Path, help="Use an exact local archive-index snapshot")
    parser.add_argument("--source-pdf", type=Path, help="Use an exact local full-report PDF snapshot")
    return parser.parse_args()


if __name__ == "__main__":
    run(parse_args())
