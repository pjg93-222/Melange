#!/usr/bin/env python3
"""Extract Senate standing/select committee payroll rows from Volume II pages.

The Secretary of the Senate's semiannual report is published in two volumes
inside one "Full Report" PDF.  Volume I carries the ``SALARIES, OFFICERS AND
EMPLOYEES`` appropriation, whose page header block is

    DETAILED AND SUMMARY STATEMENT OF EXPENDITURES
    <office>
    Funding Year          <year>
    SALARIES, OFFICERS AND EMPLOYEES
    B-<n>

Volume II carries ``EXPENSES OF INQUIRIES AND INVESTIGATIONS`` -- the
appropriation that funds every Senate standing and select committee except the
Committee on Appropriations.  Its header block is

    DETAILED AND SUMMARY STATEMENT OF EXPENDITURES
    <committee>
    S.RES. <n><letter> (<congress>TH)
    EXPENSES OF INQUIRIES AND INVESTIGATIONS
    B-2-<n>

``build_official_senate_payroll_lane.OFFICE_RE`` requires the literal
``Funding Year <year>`` line, so it never resolves a Volume II office; because
that builder carries ``current_office`` forward across pages, Volume II payroll
rows are emitted under whichever Volume I office was seen last.  This script
parses Volume II pages only, resolves the committee from the page's own header
block, and splits payee / title / amount by glyph coordinates rather than by
the naive text stream (which glues the name and title columns together).

Every row is REVIEW_REQUIRED.  This script never links a payee to a canonical
person, never asserts a complete employment history, and never promotes a date.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

import fitz

LANE_DIR = Path(__file__).resolve().parent
if str(LANE_DIR) not in sys.path:
    sys.path.insert(0, str(LANE_DIR))

from build_official_senate_payroll_lane import (  # noqa: E402
    TITLE_STARTERS,
    TITLE_TERMINALS,
    parse_qualifiers,
)
from filter_senate_payroll_employment_candidates import (  # noqa: E402
    NON_EMPLOYMENT_TITLE_PATTERNS,
    ROUTE_TEXT_MARKERS,
    TOKEN_RE,
    person_name_like,
)

PARSER_VERSION = "senate-committee-payroll-parser-v2"
CANDIDATE_SCHEMA_ID = "staffer-network-official-senate-payroll-candidate-v1"
REJECTION_SCHEMA_ID = "staffer-network-senate-committee-payroll-rejection-v1"
RECEIPT_SCHEMA_ID = "staffer-network-senate-committee-payroll-receipt-v1"
MANIFEST_SCHEMA_ID = "staffer-network-senate-committee-payroll-manifest-v1"
CANDIDATE_ID_PREFIX = "senate:committee-payroll-candidate:v1:"
APPROPRIATION_LABEL = "EXPENSES OF INQUIRIES AND INVESTIGATIONS"

VOLUME_TWO_FOOTER_RE = re.compile(r"^\s*B\s*-\s*2\s*-\s*\d+\s*$", re.M)
PAGE_LABEL_RE = re.compile(r"\bB\s*-\s*2\s*-\s*(\d+)\b")
TABLE_OF_CONTENTS_RE = re.compile(r"TABLE OF CONTENTS", re.IGNORECASE)
FUNDING_CITATION_RE = re.compile(r"\s*S\s*\.?\s*RES\s*\..*$", re.IGNORECASE)
FUNDING_TAIL_RE = re.compile(r"\s*\d+[A-Z]?\s*\(\s*\d+\s*(?:ST|ND|RD|TH)\s*\)\s*$", re.IGNORECASE)
# A payroll reversal is printed with the sign OUTSIDE the currency symbol
# ("-$7,555.54" -- GPO-CDOC-117sdoc14 p2640, GARCIA, MICHAEL A).  v1 accepted
# only "$-x" / "-x" and silently dropped the row, which is both a lost employment
# candidate and the whole of that package's V3 overage.
MONEY_RE = re.compile(r"^-?\$?-?[0-9]{1,3}(?:,[0-9]{3})*\.\d{2}$")
CALENDAR_DATE_RE = re.compile(r"\b\d{2}/\d{2}/\d{4}\b")
SRES_RE = re.compile(r"S\s*\.?\s*RES\s*\.", re.IGNORECASE)
COLUMN_GAP_POINTS = 5.0
LINE_TOLERANCE_POINTS = 2.0
PAYEE_COLUMN_MARGIN_POINTS = 15.0
MARGIN_ARTEFACT_POINTS = 2.0
PAGE_LABEL_ONLY_RE = re.compile(r"B(?:\s*-\s*\d+)+")
MARGIN_NUMERIC_ARTEFACT_RE = re.compile(r"\d{1,2}(?:\.\d{2})?")

SUMMARY_LABEL_PREFIXES = (
    "PERSONNEL COMP",
    "PERSONNEL BENEFITS",
    "NET PAYROLL EXPENSES",
    "ORGANIZATION TOTALS",
    "UNEXPENDED BALANCE",
    "TRAVEL AND TRANSPORTATION",
    "ACQUISITION OF ASSETS",
    "OTHER CONTRACTUAL SERVICES",
    "SUPPLIES AND MATERIALS",
    "PRINTING AND REPRODUCTION",
    "RENT, COMMUNICATIONS",
    "AUTHORIZATION",
    "SUPPLEMENTALS",
    "TRANSFERS",
    "RESC / WITHDRAWALS",
)


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


def write_ndjson_gzip(path: Path, rows: list[dict[str, Any]]) -> int:
    temporary = path.with_name(path.name + ".part")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as stream:
            for row in rows:
                stream.write((compact_json(row) + "\n").encode("utf-8"))
    os.replace(temporary, path)
    return len(rows)


def artifact_description(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "path": path.name, "sha256": sha256_file(path)}


def display_words(page: "fitz.Page") -> list[tuple[float, float, float, float, str]]:
    """Return page words in reading-order display coordinates.

    Senate report pages are stored landscape with ``/Rotate 90``; PyMuPDF reports
    word boxes in the unrotated media box, so the rotation is undone here.
    """
    rotation = page.rotation
    box = page.mediabox
    width = float(box.width)
    height = float(box.height)
    out: list[tuple[float, float, float, float, str]] = []
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        if rotation == 90:
            dx0, dy0, dx1, dy1 = height - y1, x0, height - y0, x1
        elif rotation == 270:
            dx0, dy0, dx1, dy1 = y0, width - x1, y1, width - x0
        elif rotation == 180:
            dx0, dy0, dx1, dy1 = width - x1, height - y1, width - x0, height - y0
        else:
            dx0, dy0, dx1, dy1 = x0, y0, x1, y1
        if word.strip():
            out.append((dx0, dy0, dx1, dy1, word))
    return out


def group_lines_with_baselines(
    words: list[tuple[float, float, float, float, str]],
) -> list[tuple[float, list[tuple[float, float, float, float, str]]]]:
    """Group words into visual lines, keeping each line's baseline.

    The baseline is what separates a wrapped title's fragments from the payroll
    rows above and below them: inside a multi-line title block the leading is
    tighter than the roster's own row pitch, so a fragment is always vertically
    nearer to the row it belongs to than to its neighbour.
    """
    buckets: list[tuple[float, list]] = []
    for word in sorted(words, key=lambda item: (item[1], item[0])):
        placed = False
        for index, (baseline, members) in enumerate(buckets):
            if abs(baseline - word[1]) <= LINE_TOLERANCE_POINTS:
                members.append(word)
                placed = True
                break
        if not placed:
            buckets.append((word[1], [word]))
    buckets.sort(key=lambda item: item[0])
    return [(baseline, sorted(members, key=lambda item: item[0])) for baseline, members in buckets]


def group_lines(words: list[tuple[float, float, float, float, str]]) -> list[list[tuple[float, float, float, float, str]]]:
    return [members for _baseline, members in group_lines_with_baselines(words)]


def column_runs(line: list[tuple[float, float, float, float, str]]) -> list[tuple[float, float, str]]:
    """Split one visual line into column runs on horizontal gaps."""
    runs: list[list[tuple[float, float, float, float, str]]] = [[line[0]]]
    for previous, current in zip(line, line[1:]):
        if current[0] - previous[2] > COLUMN_GAP_POINTS:
            runs.append([current])
        else:
            runs[-1].append(current)
    return [(run[0][0], run[-1][2], " ".join(word[4] for word in run)) for run in runs]


def page_column_anchors(lines_runs: list[list[tuple[float, float, str]]]) -> dict[str, float] | None:
    """Locate the repeated column header and return its run x-origins."""
    for runs in lines_runs:
        texts = [text.upper() for _, _, text in runs]
        if not any(text.startswith("DOCUMENT NO") for text in texts):
            continue
        if not any(text.startswith("PAYEE NAME") for text in texts):
            continue
        anchors: dict[str, float] = {}
        for (x0, _, text), upper in zip(runs, texts):
            if upper.startswith("DOCUMENT NO"):
                anchors["document"] = x0
            elif upper.startswith("PAYEE NAME"):
                anchors["payee"] = x0
            elif upper.startswith("OBLIGATION"):
                anchors["obligation"] = x0
            elif upper.startswith("DESCRIPTION"):
                anchors["description"] = x0
            elif upper.startswith("AMOUNT"):
                anchors["amount"] = x0
        if "document" in anchors and "obligation" in anchors:
            return anchors
    return None


def resolve_page_office(lines_runs: list[list[tuple[float, float, str]]]) -> tuple[str | None, str | None, str | None]:
    """Return (office, funding_resolution, failure_reason) from a page header block."""
    anchor_index: int | None = None
    anchor_x: float | None = None
    for index, runs in enumerate(lines_runs):
        for x0, _, text in runs:
            if text.upper().startswith(APPROPRIATION_LABEL):
                anchor_index = index
                anchor_x = x0
                break
        if anchor_index is not None:
            break
    if anchor_index is None or anchor_x is None:
        return None, None, "NO_APPROPRIATION_ANCHOR"
    header_lines: list[str] = []
    for runs in lines_runs[:anchor_index]:
        leading = None
        for x0, _, text in runs:
            if abs(x0 - anchor_x) <= 3.0:
                leading = text
                break
        if leading is None:
            continue
        cleaned = " ".join(leading.split())
        if not cleaned or not any(character.isalpha() for character in cleaned):
            continue
        if cleaned.upper().startswith("DETAILED AND SUMMARY"):
            continue
        header_lines.append(cleaned)
    if not header_lines:
        return None, None, "OFFICE_LINE_NOT_FOUND"
    if len(header_lines) == 1:
        # Some editions (e.g. GPO-CDOC-117sdoc5) print only the abbreviated
        # funding line and omit the spelled-out committee line entirely.  Keep
        # the page's own text, minus the resolution citation, and flag the
        # weaker basis rather than dropping the rows or inventing a name.
        only = header_lines[0]
        abbreviated = FUNDING_TAIL_RE.sub("", FUNDING_CITATION_RE.sub("", only)).strip(" .,")
        if not abbreviated or not any(character.isalpha() for character in abbreviated):
            return None, only, "OFFICE_LINE_NOT_FOUND"
        return abbreviated, only, "ABBREVIATED_FUNDING_LINE_ONLY"
    # The line immediately above the appropriation label is the funding
    # authority (an ``S.RES.`` citation, or a fiscal-year line for Ethics);
    # everything above it is the committee name, which may wrap over lines.
    funding_resolution = header_lines[-1]
    office = " ".join(header_lines[:-1])
    return office, funding_resolution, None


def classify_line(
    runs: list[tuple[float, float, str]],
    anchors: dict[str, float],
) -> tuple[str, dict[str, str] | None]:
    """Return (classification, parts) for one visual line."""
    # The ``B-2-n`` page label and the left-margin artefacts sit in the same
    # horizontal band as a payroll row often enough that leaving them in place
    # silently destroys rows: the label becomes the line's last run, so the
    # amount test fails and the row is dropped.
    runs = [
        (x0, x1, text)
        for x0, x1, text in runs
        if not PAGE_LABEL_ONLY_RE.fullmatch(text.strip())
        and x1 >= anchors["document"] - MARGIN_ARTEFACT_POINTS
    ]
    if not runs:
        return "NOT_A_ROW", None
    # The left margin of these pages carries stray sub-total fragments ("00",
    # "3.00") that can share a row's horizontal band.  Drop such a leading run
    # only when doing so exposes a run that starts in the payee column.
    while (
        len(runs) > 2
        and runs[0][0] < anchors["document"]
        and MARGIN_NUMERIC_ARTEFACT_RE.fullmatch(runs[0][2].strip())
        and anchors["document"] + PAYEE_COLUMN_MARGIN_POINTS <= runs[1][0] < anchors["obligation"]
    ):
        runs = runs[1:]
    joined = " ".join(text for _, _, text in runs)
    if CALENDAR_DATE_RE.search(joined):
        return "EXPENSE_OR_DOCUMENT_LINE", None
    if len(runs) < 2:
        return "NOT_A_ROW", None
    if not MONEY_RE.match(runs[-1][2].replace(" ", "")):
        return "NOT_A_ROW", None
    left_x = runs[0][0]
    lower_bound = anchors["document"] + PAYEE_COLUMN_MARGIN_POINTS
    upper_bound = anchors["obligation"]
    if not (lower_bound <= left_x < upper_bound):
        return "NOT_IN_PAYEE_COLUMN", None
    head = " ".join(runs[0][2].upper().split())
    if any(head.startswith(prefix) for prefix in SUMMARY_LABEL_PREFIXES):
        return "SUMMARY_LINE", None
    if len(runs) == 2:
        return "PAYROLL_ROW_WITHOUT_TITLE", {
            "payee": runs[0][2],
            "title": "",
            "amount": runs[-1][2],
            "split": "COLUMN_COORDINATE_SPLIT_NO_TITLE_COLUMN",
        }
    middle = [text for _, _, text in runs[1:-1]]
    split = (
        "COLUMN_COORDINATE_SPLIT"
        if len(runs) == 3
        else "COLUMN_COORDINATE_SPLIT_MULTIRUN_TITLE"
    )
    return "PAYROLL_ROW", {
        "payee": runs[0][2],
        "title": " ".join(middle),
        "amount": runs[-1][2],
        "split": split,
    }


CONTINUATION_BLOCKLIST = ("WASHINGTON DC TO", "INTERDEPARTMENTAL", "AND RETURN", "AIRFARE FOR")
TITLE_OVERFLOW_SLACK_POINTS = 14.0
TITLE_COLUMN_TOLERANCE_POINTS = 3.0
TITLE_FRAGMENT_CHARSET_RE = re.compile(r"[A-Z0-9À-ÖØ-Þ .,'’&()/\-]+")


def title_column_origin(
    lines_runs: list[list[tuple[float, float, str]]],
    anchors: dict[str, float],
) -> float | None:
    """The x-origin of the roster's description column on this page."""
    counts: dict[float, int] = {}
    for runs in lines_runs:
        if len(runs) < 3:
            continue
        left = runs[0][0]
        if not (anchors["document"] + PAYEE_COLUMN_MARGIN_POINTS <= left < anchors["obligation"]):
            continue
        if not MONEY_RE.match(runs[-1][2].replace(" ", "")):
            continue
        key = round(runs[1][0], 1)
        counts[key] = counts.get(key, 0) + 1
    if not counts:
        return None
    return max(counts.items(), key=lambda item: (item[1], -item[0]))[0]


def title_fragment_text(
    runs: list[tuple[float, float, str]],
    title_x: float | None,
) -> str | None:
    """A visual line carrying nothing but a title fragment in the title column."""
    if title_x is None or len(runs) != 1:
        return None
    x0, _x1, text = runs[0]
    if abs(x0 - title_x) > TITLE_COLUMN_TOLERANCE_POINTS:
        return None
    cleaned = " ".join(text.split())
    if not cleaned or MONEY_RE.search(cleaned.replace(" ", "")):
        return None
    if CALENDAR_DATE_RE.search(cleaned):
        return None
    upper = cleaned.upper()
    if any(marker in upper for marker in CONTINUATION_BLOCKLIST):
        return None
    if any(upper.startswith(prefix) for prefix in SUMMARY_LABEL_PREFIXES):
        return None
    if not TITLE_FRAGMENT_CHARSET_RE.fullmatch(cleaned):
        return None
    return cleaned


def assign_title_fragments(
    lines_runs: list[list[tuple[float, float, str]]],
    baselines: list[float],
    payroll_indices: set[int],
    title_x: float | None,
) -> tuple[dict[int, dict[str, list[str]]], set[int]]:
    """Attach each orphan title fragment to the payroll row it belongs to.

    A long title is set as its own block of visual lines with the payee and the
    amount aligned to one of them; the block's leading is tighter than the
    roster's row pitch, so a fragment is always vertically nearer to its own row
    than to the neighbouring row.  A fragment is only claimed when there is a
    payroll row on BOTH sides of an unbroken run of fragments -- otherwise the
    comparison has nothing to arbitrate it and the fragment is left to
    ``title_continuation``'s overflow rule.
    """
    assignment: dict[int, dict[str, list[str]]] = {}
    claimed: set[int] = set()
    if title_x is None or not payroll_indices:
        return assignment, claimed
    fragments = {
        index: text
        for index, runs in enumerate(lines_runs)
        if index not in payroll_indices
        and (text := title_fragment_text(runs, title_x)) is not None
    }
    index = 0
    total = len(lines_runs)
    while index < total:
        if index not in fragments:
            index += 1
            continue
        end = index
        while end + 1 < total and (end + 1) in fragments:
            end += 1
        previous = index - 1 if (index - 1) in payroll_indices else None
        following = end + 1 if (end + 1) in payroll_indices else None
        if previous is not None and following is not None:
            for position in range(index, end + 1):
                gap_previous = abs(baselines[position] - baselines[previous])
                gap_following = abs(baselines[following] - baselines[position])
                owner = previous if gap_previous <= gap_following else following
                side = "after" if owner == previous else "before"
                assignment.setdefault(owner, {"before": [], "after": []})[side].append(
                    fragments[position]
                )
                claimed.add(position)
        index = end + 1
    return assignment, claimed


def title_continuation(
    lines_runs: list[list[tuple[float, float, str]]],
    index: int,
    runs: list[tuple[float, float, str]],
    anchors: dict[str, float],
) -> str | None:
    """Return the wrapped remainder of a payroll row's title, if any.

    A long job title wraps onto the next visual line inside the description
    column, with no amount of its own.  Without this the title is silently
    truncated at the column edge.
    """
    if index + 1 >= len(lines_runs) or len(runs) < 3:
        return None
    # A title only wraps when it has run out of horizontal room, so require the
    # title run to reach the amount column.  Without this the rule swallows the
    # wrapped first line of the *next* row's title.
    if runs[1][1] < runs[-1][0] - TITLE_OVERFLOW_SLACK_POINTS:
        return None
    title_x = runs[1][0]
    following = lines_runs[index + 1]
    if len(following) != 1:
        return None
    x0, _, text = following[0]
    if abs(x0 - title_x) > 3.0:
        return None
    cleaned = " ".join(text.split())
    if not cleaned or MONEY_RE.search(cleaned.replace(" ", "")):
        return None
    if CALENDAR_DATE_RE.search(cleaned):
        return None
    upper = cleaned.upper()
    if any(marker in upper for marker in CONTINUATION_BLOCKLIST):
        return None
    if any(upper.startswith(prefix) for prefix in SUMMARY_LABEL_PREFIXES):
        return None
    if not re.fullmatch(r"[A-Z0-9À-ÖØ-Þ .,'’&()/\-]+", cleaned):
        return None
    return cleaned


def employment_scope_rejection(payee: str, title_candidate: str | None, title_raw: str | None) -> str | None:
    """Mirror of ``filter_senate_payroll_employment_candidates.rejection_reason``."""
    payee = (payee or "").strip()
    title = (title_candidate or title_raw or "").strip()
    if not payee:
        return "MISSING_OR_UNSPLIT_PAYEE"
    if not person_name_like(payee):
        return "PAYEE_NOT_PERSON_NAME_SHAPE"
    upper_payee = payee.upper()
    if any(marker in upper_payee for marker in ROUTE_TEXT_MARKERS):
        return "ROUTE_TEXT_AS_PAYEE"
    if not title:
        return "MISSING_OR_UNSPLIT_TITLE"
    upper_title = " ".join(title.upper().split())
    if any(pattern in upper_title for pattern in NON_EMPLOYMENT_TITLE_PATTERNS):
        return "NON_EMPLOYMENT_EXPENSE_CATEGORY"
    role_tokens = TOKEN_RE.findall(upper_title)
    if not any(token in TITLE_STARTERS or token in TITLE_TERMINALS for token in role_tokens):
        return "NO_RECOGNIZED_ROLE_TOKEN"
    return None


def candidate_identifier(package_id: str, page: int, ordinal: int, evidence: str) -> str:
    payload = compact_json([package_id, page, ordinal, evidence]).encode("utf-8")
    return CANDIDATE_ID_PREFIX + sha256_bytes(payload)


def parse_package(pdf_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    """Parse every Volume II page of one report PDF."""
    package_id = report["package_id"]
    period_start = report["period_start"]
    period_end = report["period_end"]
    pdf_sha256 = sha256_file(pdf_path)
    document = fitz.open(str(pdf_path))
    page_count = document.page_count
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    volume_two_pages = 0
    pages_with_rows = 0
    header_pages = 0
    carried_pages = 0
    abbreviated_header_pages = 0
    unresolved_office_pages: list[int] = []
    missing_anchor_pages: list[int] = []
    pages_without_column_header: list[int] = []
    table_of_contents_pages: list[int] = []
    carried_anchor_pages: list[int] = []
    carried_anchors: dict[str, float] | None = None
    carried_title_x: float | None = None
    office_row_counts: dict[str, int] = {}
    split_counts: dict[str, int] = {}
    scope_reason_counts: dict[str, int] = {}
    interval_basis_counts: dict[str, int] = {}
    classification_counts: dict[str, int] = {}
    carried_office: str | None = None
    carried_resolution: str | None = None

    for page_index in range(document.page_count):
        page = document[page_index]
        raw_text = page.get_text() or ""
        if not VOLUME_TWO_FOOTER_RE.search(raw_text):
            continue
        if TABLE_OF_CONTENTS_RE.search(raw_text):
            # The contents pages cite the B-2 page range; they are not data.
            table_of_contents_pages.append(page_index + 1)
            continue
        volume_two_pages += 1
        page_number = page_index + 1
        label_match = PAGE_LABEL_RE.search(raw_text)
        page_label = f"B-2-{label_match.group(1)}" if label_match else None
        grouped = group_lines_with_baselines(display_words(page))
        baselines = [baseline for baseline, _members in grouped]
        lines_runs = [column_runs(members) for _baseline, members in grouped]
        office, funding_resolution, failure = resolve_page_office(lines_runs)
        if office is not None:
            carried_office = office
            carried_resolution = funding_resolution
            if failure == "ABBREVIATED_FUNDING_LINE_ONLY":
                attribution = "PAGE_HEADER_ABBREVIATED_FUNDING_LINE_ONLY"
                abbreviated_header_pages += 1
            else:
                attribution = "PAGE_HEADER"
            header_pages += 1
        elif failure == "NO_APPROPRIATION_ANCHOR" and carried_office is not None:
            office = carried_office
            funding_resolution = carried_resolution
            attribution = "CARRIED_FROM_PREVIOUS_VOLUME_II_PAGE"
            carried_pages += 1
        else:
            if failure == "OFFICE_LINE_NOT_FOUND":
                unresolved_office_pages.append(page_number)
            else:
                missing_anchor_pages.append(page_number)
            continue
        anchors = page_column_anchors(lines_runs)
        if anchors is None:
            # Rare pages omit the repeated column header.  The column geometry
            # is a constant of the edition, so reuse the previous Volume II
            # page's anchors rather than dropping the page's payroll rows.
            if carried_anchors is None:
                pages_without_column_header.append(page_number)
                continue
            anchors = carried_anchors
            carried_anchor_pages.append(page_number)
        else:
            carried_anchors = anchors
        classified = [classify_line(runs, anchors) for runs in lines_runs]
        payroll_indices = {
            index for index, (_classification, parts) in enumerate(classified) if parts is not None
        }
        title_x = title_column_origin(lines_runs, anchors)
        if title_x is None:
            title_x = carried_title_x
        else:
            carried_title_x = title_x
        fragments, claimed_fragment_lines = assign_title_fragments(
            lines_runs, baselines, payroll_indices, title_x
        )
        ordinal = 0
        page_rows = 0
        for line_index, runs in enumerate(lines_runs):
            classification, parts = classified[line_index]
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
            if parts is None:
                continue
            ordinal += 1
            evidence_quote = " ".join(text for _, _, text in runs)
            # A title set as its own block of visual lines puts fragments both
            # above and below the line that carries the payee and the amount.
            # v1 read only downwards, so it truncated those titles and rejected
            # the rows whose title column is entirely off the payee's own line.
            block = fragments.get(line_index)
            if block and block["before"]:
                leading = " ".join(block["before"])
                parts["title"] = f"{leading} {parts['title']}".strip()
                parts["split"] = parts["split"] + "_WITH_LEADING_TITLE"
                evidence_quote = f"{leading} {evidence_quote}"
            if block and block["after"]:
                trailing = " ".join(block["after"])
                parts["title"] = f"{parts['title']} {trailing}".strip()
                parts["split"] = parts["split"] + "_WITH_WRAPPED_TITLE"
                evidence_quote = f"{evidence_quote} {trailing}"
            elif line_index + 1 not in claimed_fragment_lines:
                # No row follows the fragment, so the baseline comparison has
                # nothing to arbitrate it; fall back to the overflow rule.
                continuation = title_continuation(lines_runs, line_index, runs, anchors)
                if continuation:
                    parts["title"] = f"{parts['title']} {continuation}".strip()
                    parts["split"] = parts["split"] + "_WITH_WRAPPED_TITLE"
                    evidence_quote = f"{evidence_quote} {continuation}"
            payee = " ".join(parts["payee"].split())
            title_raw = " ".join(parts["title"].split()) or None
            qualifiers, intervals, title_candidate = parse_qualifiers(
                title_raw, period_start, period_end
            )
            for interval in intervals:
                if not (period_start <= interval["start"] <= interval["end"] <= period_end):
                    raise RuntimeError(
                        f"Out-of-period interval escaped fail-closed parsing: "
                        f"{package_id} p{page_number} {interval}"
                    )
                interval_basis_counts[interval["basis"]] = (
                    interval_basis_counts.get(interval["basis"], 0) + 1
                )
            row = {
                "amount_paid_raw": parts["amount"],
                "candidate_id": candidate_identifier(
                    package_id, page_number, ordinal, evidence_quote
                ),
                "canonical_employment_decision": "NOT_ADJUDICATED",
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "completeness_status": "PARTIAL",
                "date_intervals": intervals,
                "date_promotion_eligible": False,
                "employment_claim_status": "UNVERIFIED_CANDIDATE",
                "evidence_columns": [parts["payee"], parts["title"], parts["amount"]],
                "evidence_quote": evidence_quote,
                "extraction_engine": f"PyMuPDF {fitz.VersionBind}",
                "identity_status": "UNVERIFIED_CANDIDATE",
                "office_attribution_basis": attribution,
                "office_raw": office,
                "page_label_raw": page_label,
                "page_number": page_number,
                "parse_status": parts["split"],
                "parser_version": PARSER_VERSION,
                "payee_name_raw": payee,
                "promotion_gate": "BLOCKED_PENDING_IDENTITY_AND_ROW_REVIEW",
                "qualifiers": qualifiers,
                "report_package_id": package_id,
                "report_period_end": period_end,
                "report_period_start": period_start,
                "review_status": "REVIEW_REQUIRED",
                "row_ordinal_on_page": ordinal,
                "schema_id": CANDIDATE_SCHEMA_ID,
                "senate_appropriation_raw": APPROPRIATION_LABEL,
                "senate_funding_resolution_raw": funding_resolution,
                "senate_report_volume": "II",
                "source_pdf_sha256": pdf_sha256,
                "source_pdf_url": report["full_pdf_url"],
                "source_tier": "OFFICIAL_SECRETARY_OF_THE_SENATE_REPORT",
                "title_candidate": title_candidate,
                "title_raw": title_raw,
            }
            reason = employment_scope_rejection(payee, title_candidate, title_raw)
            split_counts[parts["split"]] = split_counts.get(parts["split"], 0) + 1
            if reason is None:
                accepted.append(row)
                office_row_counts[office] = office_row_counts.get(office, 0) + 1
                page_rows += 1
            else:
                scope_reason_counts[reason] = scope_reason_counts.get(reason, 0) + 1
                rejected.append({
                    "candidate_id": row["candidate_id"],
                    "evidence_quote": evidence_quote,
                    "office_raw": office,
                    "page_number": page_number,
                    "parse_status": parts["split"],
                    "payee_name_raw": payee,
                    "rejection_reason": reason,
                    "report_package_id": package_id,
                    "schema_id": REJECTION_SCHEMA_ID,
                    "title_raw": title_raw,
                })
        if page_rows:
            pages_with_rows += 1
    document.close()

    identifiers = [row["candidate_id"] for row in accepted] + [
        row["candidate_id"] for row in rejected
    ]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError(f"Duplicate committee payroll candidate IDs in {package_id}")
    return {
        "accepted": accepted,
        "rejected": rejected,
        "receipt": {
            "abbreviated_header_office_pages": abbreviated_header_pages,
            "accepted_row_count": len(accepted),
            "carried_column_anchor_pages": carried_anchor_pages,
            "carried_office_pages": carried_pages,
            "classification_counts": dict(sorted(classification_counts.items())),
            "distinct_offices": sorted(office_row_counts),
            "header_office_pages": header_pages,
            "interval_basis_counts": dict(sorted(interval_basis_counts.items())),
            "missing_appropriation_anchor_pages": missing_anchor_pages,
            "office_row_counts": dict(sorted(office_row_counts.items())),
            "package_id": package_id,
            "page_count": page_count,
            "pages_with_accepted_rows": pages_with_rows,
            "pages_without_column_header": pages_without_column_header,
            "parse_status_counts": dict(sorted(split_counts.items())),
            "parser_version": PARSER_VERSION,
            "pdf_bytes": pdf_path.stat().st_size,
            "pdf_sha256": pdf_sha256,
            "period_end": period_end,
            "period_start": period_start,
            "rejected_row_count": len(rejected),
            "scope_rejection_counts": dict(sorted(scope_reason_counts.items())),
            "table_of_contents_pages_skipped": table_of_contents_pages,
            "unresolved_office_pages": unresolved_office_pages,
            "volume_two_page_count": volume_two_pages,
        },
    }


def _worker(payload: tuple[str, dict[str, Any]]) -> dict[str, Any]:
    pdf_path, report = payload
    return parse_package(Path(pdf_path), report)


def run(args: argparse.Namespace) -> int:
    output_root: Path = args.output_root
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"Output root is nonempty (generations are immutable): {output_root}")
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    reports = inventory["periods"]
    jobs: list[tuple[str, dict[str, Any]]] = []
    missing: list[str] = []
    for report in reports:
        pdf_path = args.raw_dir / f"{report['package_id']}.pdf"
        if not pdf_path.exists():
            missing.append(report["package_id"])
            continue
        jobs.append((str(pdf_path), report))
    if missing:
        raise RuntimeError(f"Source PDFs absent locally (no network permitted): {missing}")

    started = dt.datetime.now(dt.timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(_worker, jobs):
            results.append(result)
    finished = dt.datetime.now(dt.timezone.utc).isoformat()

    results.sort(key=lambda item: (item["receipt"]["period_start"], item["receipt"]["package_id"]))
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for result in results:
        accepted.extend(result["accepted"])
        rejected.extend(result["rejected"])
    accepted.sort(key=lambda row: (row["report_package_id"], row["page_number"], row["row_ordinal_on_page"]))
    rejected.sort(key=lambda row: (row["report_package_id"], row["page_number"], row["candidate_id"]))

    identifiers = [row["candidate_id"] for row in accepted] + [row["candidate_id"] for row in rejected]
    if len(identifiers) != len(set(identifiers)):
        raise RuntimeError("Duplicate candidate_id across packages")

    output_root.mkdir(parents=True, exist_ok=True)
    accepted_path = output_root / "senate_committee_payroll_candidates_2011_2026.ndjson.gz"
    rejected_path = output_root / "senate_committee_payroll_rejections_2011_2026.ndjson.gz"
    write_ndjson_gzip(accepted_path, accepted)
    write_ndjson_gzip(rejected_path, rejected)
    package_receipts = [result["receipt"] for result in results]
    package_receipt_path = output_root / "senate_committee_payroll_package_receipts.ndjson"
    write_bytes_atomic(
        package_receipt_path,
        "".join(compact_json(row) + "\n" for row in package_receipts).encode("utf-8"),
    )

    office_totals: dict[str, int] = {}
    payees: set[str] = set()
    periods: set[str] = set()
    for row in accepted:
        office_totals[row["office_raw"]] = office_totals.get(row["office_raw"], 0) + 1
        payees.add(row["payee_name_raw"].upper())
        periods.add(row["report_period_start"])
    scope_totals: dict[str, int] = {}
    for row in rejected:
        scope_totals[row["rejection_reason"]] = scope_totals.get(row["rejection_reason"], 0) + 1

    anomalies = {
        "packages_with_zero_volume_two_pages": [
            item["package_id"] for item in package_receipts if item["volume_two_page_count"] == 0
        ],
        "packages_with_zero_accepted_rows": [
            item["package_id"] for item in package_receipts if item["accepted_row_count"] == 0
        ],
        "unresolved_office_page_total": sum(
            len(item["unresolved_office_pages"]) for item in package_receipts
        ),
        "missing_appropriation_anchor_page_total": sum(
            len(item["missing_appropriation_anchor_pages"]) for item in package_receipts
        ),
        "pages_without_column_header_total": sum(
            len(item["pages_without_column_header"]) for item in package_receipts
        ),
        "carried_column_anchor_page_total": sum(
            len(item["carried_column_anchor_pages"]) for item in package_receipts
        ),
        "abbreviated_header_office_page_total": sum(
            item["abbreviated_header_office_pages"] for item in package_receipts
        ),
    }
    receipt = {
        "accepted_candidates": artifact_description(accepted_path),
        "accepted_row_count": len(accepted),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "complete_history_assertions": 0,
        "date_promotions": 0,
        "distinct_office_count": len(office_totals),
        "distinct_payee_name_count": len(payees),
        "distinct_period_count": len(periods),
        "extraction_engine": f"PyMuPDF {fitz.VersionBind}",
        "finished_utc": finished,
        "generation_anomalies": anomalies,
        "inventory_source": {
            "path": str(args.inventory),
            "sha256": sha256_file(args.inventory),
        },
        "office_row_counts": dict(sorted(office_totals.items())),
        "package_count": len(package_receipts),
        "package_receipts": artifact_description(package_receipt_path),
        "parser_version": PARSER_VERSION,
        "period_starts": sorted(periods),
        "python_version": sys.version.split()[0],
        "rejected_candidates": artifact_description(rejected_path),
        "rejected_row_count": len(rejected),
        "review_rule": "EVERY_ROW_REVIEW_REQUIRED",
        "schema_id": RECEIPT_SCHEMA_ID,
        "scope_rejection_counts": dict(sorted(scope_totals.items())),
        "sequencing_rule": "COLLECT_FIRST_IDENTITY_ADJUDICATION_LATER",
        "source_scope": "SENATE_REPORT_VOLUME_II_EXPENSES_OF_INQUIRIES_AND_INVESTIGATIONS",
        "started_utc": started,
        "status": "PASS" if not anomalies["packages_with_zero_accepted_rows"] else "REVIEW",
    }
    receipt_path = output_root / "senate_committee_payroll_receipt.json"
    write_json_atomic(receipt_path, receipt)
    manifest = {
        "artifacts": {
            "accepted_candidates": artifact_description(accepted_path),
            "package_receipts": artifact_description(package_receipt_path),
            "receipt": artifact_description(receipt_path),
            "rejections": artifact_description(rejected_path),
        },
        "generation_id": output_root.name,
        "schema_id": MANIFEST_SCHEMA_ID,
    }
    write_json_atomic(output_root / "manifest.json", manifest)
    print(compact_json({
        "accepted_row_count": receipt["accepted_row_count"],
        "distinct_office_count": receipt["distinct_office_count"],
        "distinct_payee_name_count": receipt["distinct_payee_name_count"],
        "output_root": str(output_root),
        "rejected_row_count": receipt["rejected_row_count"],
        "status": receipt["status"],
    }))
    return 0


def parse_args() -> argparse.Namespace:
    default_source = LANE_DIR / "official_senate_payroll_2011_2026_full_8workers"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=default_source / "raw")
    parser.add_argument(
        "--inventory", type=Path, default=default_source / "senate_report_archive_inventory.json"
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run(parse_args()))
