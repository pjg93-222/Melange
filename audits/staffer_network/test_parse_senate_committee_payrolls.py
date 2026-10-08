#!/usr/bin/env python3
"""Synthetic-fixture tests for parse_senate_committee_payrolls.

The fixtures rebuild the Secretary of the Senate Volume II page geometry from
scratch (three coordinate columns, the header block, the ``B-2-n`` footer) so
the parser's behaviour is pinned without depending on any real PDF.  One
fixture is emitted twice -- once upright, once with the real reports' ``/Rotate
90`` -- and the two parses must agree, which pins the rotation transform.

Run:  python -m pytest audits/staffer_network/test_parse_senate_committee_payrolls.py -q
"""

from __future__ import annotations

from pathlib import Path
import sys

import fitz
import pytest

LANE_DIR = Path(__file__).resolve().parent
if str(LANE_DIR) not in sys.path:
    sys.path.insert(0, str(LANE_DIR))

import parse_senate_committee_payrolls as parser  # noqa: E402

PAGE_WIDTH = 792.0
PAGE_HEIGHT = 612.0
FONT = "helv"
FONT_SIZE = 7.0

REPORT = {
    "package_id": "GPO-CDOC-FIXTURE1",
    "period_start": "2025-10-01",
    "period_end": "2026-03-31",
    "full_pdf_url": "https://example.invalid/fixture.pdf",
}

# (x, y, text) in upright landscape display space.
HEADER_BLOCK = [
    (232.0, 40.0, "DETAILED AND SUMMARY STATEMENT OF EXPENDITURES"),
    (62.0, 58.0, "AGRICULTURE, NUTRITION AND FORESTRY"),
    (62.0, 76.0, "S.RES. 94C (119TH)"),
    (62.0, 93.0, "EXPENSES OF INQUIRIES AND INVESTIGATIONS"),
]
COLUMN_HEADER = [
    (74.0, 210.0, "DOCUMENT NO."),
    (140.0, 210.0, "DATE"),
    (210.0, 210.0, "PAYEE NAME"),
    (292.0, 210.0, "OBLIGATION/SERVICE"),
    (426.0, 210.0, "DESCRIPTION"),
    (548.0, 210.0, "AMOUNT ($)"),
]
FOOTER = [(600.0, 199.0, "B-2-5")]

PAYEE_COLUMN_X_LITERAL = 176.0
PAYROLL_ROWS = [
    (250.0, "WILLIAMS, JESSICA L", "CHIEF CLERK", "$112,124.96"),
    (257.0, "MILLER, LAUREN CLAIRE", "PRESS SECRETARY TO MAR. 10", "$8,888.85"),
    (264.0, "HERTEL, WILLIAM HARRIS", "STAFF ASSISTANT FROM DEC. 1", "$18,916.66"),
    (271.0, "WEBER, COREY BROWN", "CHIEF COUNSEL TO NOV. 8 AND FROM NOV. 14", "$107,277.87"),
]
NOISE_ROWS = [
    # Summary labels as the reports place them, to the right of the payee column.
    (285.0, [(322.0, "PERSONNEL COMP. FULL-TIME PERMANENT"), (560.0, "$2,810,687.16")]),
    (292.0, [(322.0, "PERSONNEL BENEFITS"), (569.0, "$5,245.95")]),
    # The same label pulled left into the payee column band, which is what the
    # SUMMARY_LABEL_PREFIXES guard exists for.
    (306.0, [(PAYEE_COLUMN_X_LITERAL, "NET PAYROLL EXPENSES"), (560.0, "$2,815,933.11")]),
    # Expense row: starts in the DOCUMENT NO. column and carries service dates.
    (300.0, [
        (67.0, "DANF20260011"),
        (135.0, "12/06/2025"),
        (176.0, "THOMAS J LIEPOLD"),
        (287.0, "11/10/2025"),
        (325.0, "11/13/2025"),
        (356.0, "STAFF INCIDENTALS"),
        (576.0, "$26.74"),
    ]),
]
PAYEE_COLUMN_X = 176.0
TITLE_COLUMN_X = 356.0
AMOUNT_COLUMN_X = 564.0


def _place(page: fitz.Page, x: float, y: float, text: str, rotated: bool) -> None:
    if rotated:
        # Upright landscape point (x, y) maps to the portrait media box at
        # (y, PAGE_WIDTH - x) with glyphs turned 90 degrees, so that a
        # subsequent /Rotate 90 renders the intended landscape layout.
        page.insert_text((y, PAGE_WIDTH - x), text, fontname=FONT, fontsize=FONT_SIZE, rotate=90)
    else:
        page.insert_text((x, y), text, fontname=FONT, fontsize=FONT_SIZE)


def _build_page(page: fitz.Page, blocks: list[tuple[float, float, str]], rotated: bool) -> None:
    for x, y, text in blocks:
        _place(page, x, y, text, rotated)


def _standard_blocks() -> list[tuple[float, float, str]]:
    blocks: list[tuple[float, float, str]] = []
    blocks.extend(HEADER_BLOCK)
    blocks.extend((x, y, text) for x, y, text in COLUMN_HEADER)
    blocks.extend(FOOTER)
    for y, payee, title, amount in PAYROLL_ROWS:
        blocks.append((PAYEE_COLUMN_X, y, payee))
        blocks.append((TITLE_COLUMN_X, y, title))
        blocks.append((AMOUNT_COLUMN_X, y, amount))
    for y, cells in NOISE_ROWS:
        for x, text in cells:
            blocks.append((x, y, text))
    return blocks


def _new_document(rotated: bool) -> fitz.Document:
    document = fitz.open()
    if rotated:
        page = document.new_page(width=PAGE_HEIGHT, height=PAGE_WIDTH)
    else:
        page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    return document, page


def _finish(document: fitz.Document, page: fitz.Page, rotated: bool, path: Path) -> Path:
    if rotated:
        page.set_rotation(90)
    document.save(str(path))
    document.close()
    return path


def _write_standard_pdf(path: Path, rotated: bool = False) -> Path:
    document, page = _new_document(rotated)
    _build_page(page, _standard_blocks(), rotated)
    return _finish(document, page, rotated, path)


def _parse(path: Path) -> dict:
    return parser.parse_package(path, dict(REPORT))


# --------------------------------------------------------------------------
# Structural extraction
# --------------------------------------------------------------------------


def test_extracts_exactly_the_payroll_rows(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    accepted = result["accepted"]
    assert [row["payee_name_raw"] for row in accepted] == [
        "WILLIAMS, JESSICA L",
        "MILLER, LAUREN CLAIRE",
        "HERTEL, WILLIAM HARRIS",
        "WEBER, COREY BROWN",
    ]
    assert [row["title_raw"] for row in accepted] == [
        "CHIEF CLERK",
        "PRESS SECRETARY TO MAR. 10",
        "STAFF ASSISTANT FROM DEC. 1",
        "CHIEF COUNSEL TO NOV. 8 AND FROM NOV. 14",
    ]
    assert [row["amount_paid_raw"] for row in accepted] == [
        "$112,124.96",
        "$8,888.85",
        "$18,916.66",
        "$107,277.87",
    ]
    assert result["receipt"]["volume_two_page_count"] == 1


def test_summary_and_expense_lines_are_never_payroll_rows(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    emitted = {row["payee_name_raw"] for row in result["accepted"]}
    emitted |= {row["payee_name_raw"] for row in result["rejected"]}
    assert not any("PERSONNEL" in value for value in emitted)
    assert "THOMAS J LIEPOLD" not in emitted
    counts = result["receipt"]["classification_counts"]
    assert counts.get("SUMMARY_LINE", 0) == 1
    assert counts.get("NOT_IN_PAYEE_COLUMN", 0) >= 2
    assert counts.get("EXPENSE_OR_DOCUMENT_LINE", 0) >= 1


def test_office_is_resolved_from_the_page_header(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    for row in result["accepted"]:
        assert row["office_raw"] == "AGRICULTURE, NUTRITION AND FORESTRY"
        assert row["senate_funding_resolution_raw"] == "S.RES. 94C (119TH)"
        assert row["office_attribution_basis"] == "PAGE_HEADER"
        assert row["senate_report_volume"] == "II"


def test_rotated_and_upright_pages_yield_identical_rows(tmp_path: Path) -> None:
    upright = _parse(_write_standard_pdf(tmp_path / "upright.pdf"))
    rotated = _parse(_write_standard_pdf(tmp_path / "rotated.pdf", rotated=True))
    assert rotated["receipt"]["volume_two_page_count"] == 1
    fields = ("office_raw", "payee_name_raw", "title_raw", "amount_paid_raw", "row_ordinal_on_page")
    assert [tuple(row[f] for f in fields) for row in rotated["accepted"]] == [
        tuple(row[f] for f in fields) for row in upright["accepted"]
    ]


# --------------------------------------------------------------------------
# Office-name shapes
# --------------------------------------------------------------------------


def test_committee_name_wrapped_over_two_lines_is_joined(tmp_path: Path) -> None:
    blocks = [block for block in _standard_blocks() if block[:2] != (62.0, 58.0)]
    blocks.append((62.0, 58.0, "HOMELAND SECURITY AND GOVERNMENTAL"))
    blocks.append((62.0, 66.0, "AFFAIRS"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "wrapped.pdf"))
    assert result["accepted"]
    for row in result["accepted"]:
        assert row["office_raw"] == "HOMELAND SECURITY AND GOVERNMENTAL AFFAIRS"


def test_fiscal_year_funding_line_is_not_mistaken_for_the_office(tmp_path: Path) -> None:
    blocks = [
        block for block in _standard_blocks() if block[:2] not in {(62.0, 58.0), (62.0, 76.0)}
    ]
    blocks.append((62.0, 58.0, "ETHICS"))
    blocks.append((62.0, 76.0, "COMMITTEE ON ETHICS - FY 2026"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "ethics.pdf"))
    assert result["accepted"]
    for row in result["accepted"]:
        assert row["office_raw"] == "ETHICS"
        assert row["senate_funding_resolution_raw"] == "COMMITTEE ON ETHICS - FY 2026"


def test_abbreviated_only_header_is_kept_verbatim_and_flagged(tmp_path: Path) -> None:
    """GPO-CDOC-117sdoc5 prints no spelled-out committee line at all."""
    blocks = [
        block for block in _standard_blocks() if block[:2] not in {(62.0, 58.0), (62.0, 76.0)}
    ]
    blocks.append((62.0, 76.0, "HOMELAND SEC.& GOV AFF. 70B (117TH)"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "abbrev.pdf"))
    assert len(result["accepted"]) == len(PAYROLL_ROWS)
    for row in result["accepted"]:
        assert row["office_raw"] == "HOMELAND SEC.& GOV AFF"
        assert row["senate_funding_resolution_raw"] == "HOMELAND SEC.& GOV AFF. 70B (117TH)"
        assert row["office_attribution_basis"] == "PAGE_HEADER_ABBREVIATED_FUNDING_LINE_ONLY"
    assert result["receipt"]["abbreviated_header_office_pages"] == 1


def test_abbreviated_only_header_with_sres_citation(tmp_path: Path) -> None:
    blocks = [
        block for block in _standard_blocks() if block[:2] not in {(62.0, 58.0), (62.0, 76.0)}
    ]
    blocks.append((62.0, 76.0, "AGRICULTURE, NUTR &FOR S.RES.70D(116TH)"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "abbrev_sres.pdf"))
    assert len(result["accepted"]) == len(PAYROLL_ROWS)
    for row in result["accepted"]:
        assert row["office_raw"] == "AGRICULTURE, NUTR &FOR"


def test_page_missing_the_column_header_reuses_the_previous_geometry(tmp_path: Path) -> None:
    document = fitz.open()
    first = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _build_page(first, _standard_blocks(), False)
    second = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    headerless: list[tuple[float, float, str]] = list(HEADER_BLOCK)
    headerless.append((600.0, 199.0, "B-2-94"))
    headerless.append((PAYEE_COLUMN_X, 250.0, "EBARB, AMBER"))
    headerless.append((TITLE_COLUMN_X, 250.0, "REPUBLICAN DEPUTY STAFF DIRECTOR"))
    headerless.append((AMOUNT_COLUMN_X, 250.0, "$60,000.00"))
    _build_page(second, headerless, False)
    path = tmp_path / "no_column_header.pdf"
    document.save(str(path))
    document.close()
    result = _parse(path)
    recovered = [row for row in result["accepted"] if row["page_number"] == 2]
    assert [row["payee_name_raw"] for row in recovered] == ["EBARB, AMBER"]
    assert result["receipt"]["carried_column_anchor_pages"] == [2]
    assert result["receipt"]["pages_without_column_header"] == []


def test_table_of_contents_page_is_not_treated_as_data(tmp_path: Path) -> None:
    document, page = _new_document(False)
    contents = [
        (62.0, 40.0, "TABLE OF CONTENTS"),
        (62.0, 60.0, "AGRICULTURE, NUTRITION AND FORESTRY"),
        (600.0, 60.0, "B-2-1"),
    ]
    _build_page(page, contents, False)
    result = _parse(_finish(document, page, False, tmp_path / "toc.pdf"))
    assert result["accepted"] == []
    assert result["receipt"]["volume_two_page_count"] == 0
    assert result["receipt"]["table_of_contents_pages_skipped"] == [1]


def test_continuation_page_carries_the_previous_office(tmp_path: Path) -> None:
    document = fitz.open()
    first = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    _build_page(first, _standard_blocks(), False)
    second = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    continuation: list[tuple[float, float, str]] = list(COLUMN_HEADER)
    continuation.append((600.0, 199.0, "B-2-6"))
    continuation.append((PAYEE_COLUMN_X, 250.0, "KOTRAIAH, MEGHANA"))
    continuation.append((TITLE_COLUMN_X, 250.0, "LEGISLATIVE AIDE"))
    continuation.append((AMOUNT_COLUMN_X, 250.0, "$31,071.31"))
    _build_page(second, continuation, False)
    path = tmp_path / "continuation.pdf"
    document.save(str(path))
    document.close()
    result = _parse(path)
    carried = [row for row in result["accepted"] if row["page_number"] == 2]
    assert len(carried) == 1
    assert carried[0]["office_raw"] == "AGRICULTURE, NUTRITION AND FORESTRY"
    assert carried[0]["office_attribution_basis"] == "CARRIED_FROM_PREVIOUS_VOLUME_II_PAGE"
    assert result["receipt"]["carried_office_pages"] == 1


def test_volume_one_pages_are_never_parsed(tmp_path: Path) -> None:
    document, page = _new_document(False)
    volume_one = [
        (232.0, 40.0, "DETAILED AND SUMMARY STATEMENT OF EXPENDITURES"),
        (62.0, 58.0, "APPROPRIATIONS"),
        (62.0, 76.0, "Funding Year          2024"),
        (62.0, 93.0, "SALARIES, OFFICERS AND EMPLOYEES"),
        (600.0, 199.0, "B-43"),
    ]
    volume_one.extend(COLUMN_HEADER)
    volume_one.append((PAYEE_COLUMN_X, 250.0, "KAMARCK, JONATHAN"))
    volume_one.append((TITLE_COLUMN_X, 250.0, "PROFESSIONAL STAFF"))
    volume_one.append((AMOUNT_COLUMN_X, 250.0, "$45,597.17"))
    _build_page(page, volume_one, False)
    result = _parse(_finish(document, page, False, tmp_path / "volume_one.pdf"))
    assert result["accepted"] == []
    assert result["rejected"] == []
    assert result["receipt"]["volume_two_page_count"] == 0


def test_orphan_continuation_page_is_dropped_not_misattributed(tmp_path: Path) -> None:
    document, page = _new_document(False)
    orphan: list[tuple[float, float, str]] = list(COLUMN_HEADER)
    orphan.append((600.0, 199.0, "B-2-6"))
    orphan.append((PAYEE_COLUMN_X, 250.0, "KOTRAIAH, MEGHANA"))
    orphan.append((TITLE_COLUMN_X, 250.0, "LEGISLATIVE AIDE"))
    orphan.append((AMOUNT_COLUMN_X, 250.0, "$31,071.31"))
    _build_page(page, orphan, False)
    result = _parse(_finish(document, page, False, tmp_path / "orphan.pdf"))
    assert result["accepted"] == []
    assert result["receipt"]["missing_appropriation_anchor_pages"] == [1]


# --------------------------------------------------------------------------
# Dates and review pins
# --------------------------------------------------------------------------


def test_row_qualifiers_bound_the_interval_inside_the_report_period(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    by_payee = {row["payee_name_raw"]: row for row in result["accepted"]}
    plain = by_payee["WILLIAMS, JESSICA L"]
    assert plain["date_intervals"] == [
        {"start": "2025-10-01", "end": "2026-03-31", "basis": "REPORT_PERIOD_ONLY"}
    ]
    assert plain["title_candidate"] == "CHIEF CLERK"
    leaver = by_payee["MILLER, LAUREN CLAIRE"]
    assert leaver["date_intervals"] == [
        {"start": "2025-10-01", "end": "2026-03-10", "basis": "ROW_TO_QUALIFIER"}
    ]
    assert leaver["title_candidate"] == "PRESS SECRETARY"
    joiner = by_payee["HERTEL, WILLIAM HARRIS"]
    assert joiner["date_intervals"] == [
        {"start": "2025-12-01", "end": "2026-03-31", "basis": "ROW_FROM_QUALIFIER"}
    ]
    split = by_payee["WEBER, COREY BROWN"]
    assert [interval["basis"] for interval in split["date_intervals"]] == [
        "ROW_TO_QUALIFIER",
        "ROW_FROM_QUALIFIER",
    ]


def test_every_interval_is_inside_the_report_period(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    for row in result["accepted"]:
        for interval in row["date_intervals"]:
            assert REPORT["period_start"] <= interval["start"] <= interval["end"] <= REPORT["period_end"]


def test_out_of_period_qualifier_is_flagged_and_never_promoted(tmp_path: Path) -> None:
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 278.0, "DOE, JANE Q"))
    blocks.append((TITLE_COLUMN_X, 278.0, "POLICY ADVISOR FROM JUL. 4"))
    blocks.append((AMOUNT_COLUMN_X, 278.0, "$1,000.00"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "outofperiod.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "DOE, JANE Q")
    assert row["qualifiers"][0]["resolved_date"] is None
    assert row["date_intervals"][0]["basis"] == (
        "INVALID_OR_OUT_OF_PERIOD_QUALIFIER_REVIEW_REQUIRED"
    )
    assert row["date_promotion_eligible"] is False


def test_all_rows_carry_review_pins_and_zero_promotions(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    assert result["accepted"]
    for row in result["accepted"]:
        assert row["review_status"] == "REVIEW_REQUIRED"
        assert row["canonical_employment_decision"] == "NOT_ADJUDICATED"
        assert row["canonical_identity_decision"] == "NOT_ADJUDICATED"
        assert row["employment_claim_status"] == "UNVERIFIED_CANDIDATE"
        assert row["identity_status"] == "UNVERIFIED_CANDIDATE"
        assert row["date_promotion_eligible"] is False
        assert row["completeness_status"] == "PARTIAL"
        assert row["promotion_gate"] == "BLOCKED_PENDING_IDENTITY_AND_ROW_REVIEW"
        assert row["schema_id"] == parser.CANDIDATE_SCHEMA_ID
        assert row["source_tier"] == "OFFICIAL_SECRETARY_OF_THE_SENATE_REPORT"


def test_row_shape_matches_the_existing_senate_candidate_contract(tmp_path: Path) -> None:
    required = {
        "amount_paid_raw", "candidate_id", "canonical_employment_decision",
        "canonical_identity_decision", "completeness_status", "date_intervals",
        "date_promotion_eligible", "employment_claim_status", "evidence_quote",
        "identity_status", "office_raw", "page_number", "parse_status",
        "payee_name_raw", "promotion_gate", "qualifiers", "report_package_id",
        "report_period_end", "report_period_start", "row_ordinal_on_page",
        "schema_id", "source_pdf_sha256", "source_pdf_url", "source_tier",
        "title_candidate", "title_raw",
    }
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    for row in result["accepted"]:
        assert required.issubset(row.keys())


def test_candidate_ids_are_unique_and_namespaced(tmp_path: Path) -> None:
    result = _parse(_write_standard_pdf(tmp_path / "standard.pdf"))
    identifiers = [row["candidate_id"] for row in result["accepted"]]
    identifiers += [row["candidate_id"] for row in result["rejected"]]
    assert len(identifiers) == len(set(identifiers))
    for identifier in identifiers:
        assert identifier.startswith(parser.CANDIDATE_ID_PREFIX)


def test_untitled_payroll_row_is_rejected_not_silently_dropped(tmp_path: Path) -> None:
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 278.0, "NOTITLE, SAMPLE A"))
    blocks.append((AMOUNT_COLUMN_X, 278.0, "$500.00"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "untitled.pdf"))
    assert all(row["payee_name_raw"] != "NOTITLE, SAMPLE A" for row in result["accepted"])
    rejected = next(r for r in result["rejected"] if r["payee_name_raw"] == "NOTITLE, SAMPLE A")
    assert rejected["rejection_reason"] == "MISSING_OR_UNSPLIT_TITLE"


def test_page_label_sharing_a_row_band_does_not_destroy_the_row(tmp_path: Path) -> None:
    """The B-2-n label lands in a payroll row's band often enough to matter."""
    blocks = _standard_blocks()
    blocks.append((700.0, 250.0, "B-2-65"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "label_collision.pdf"))
    payees = [row["payee_name_raw"] for row in result["accepted"]]
    assert "WILLIAMS, JESSICA L" in payees
    assert len(result["accepted"]) == len(PAYROLL_ROWS)
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "WILLIAMS, JESSICA L")
    assert row["amount_paid_raw"] == "$112,124.96"


def test_left_margin_fragment_sharing_a_row_band_is_ignored(tmp_path: Path) -> None:
    blocks = _standard_blocks()
    blocks.append((40.0, 250.0, "00"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "margin_fragment.pdf"))
    assert len(result["accepted"]) == len(PAYROLL_ROWS)
    assert "WILLIAMS, JESSICA L" in {r["payee_name_raw"] for r in result["accepted"]}


def test_wrapped_title_continuation_is_appended(tmp_path: Path) -> None:
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 330.0, "SCHULTZ, MARY BETH"))
    # Long enough to reach the amount column, which is what makes it a wrap.
    blocks.append((TITLE_COLUMN_X, 330.0, "ASSOC STAFF DIR/CHIEF COUNSEL FOR HOMELAND PREP &"))
    blocks.append((AMOUNT_COLUMN_X + 6.0, 330.0, "$62,499.96"))
    blocks.append((TITLE_COLUMN_X, 336.0, "RESPONSE"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "wrapped.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "SCHULTZ, MARY BETH")
    assert row["title_raw"].endswith("PREP & RESPONSE")
    assert row["parse_status"].endswith("_WITH_WRAPPED_TITLE")


def test_short_title_never_absorbs_the_next_rows_wrapped_title(tmp_path: Path) -> None:
    """The false positive found by the verifier on GPO-CDOC-118sdoc11 p2550."""
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 330.0, "SCHAEFER, SARAH E"))
    blocks.append((TITLE_COLUMN_X, 330.0, "CHIEF TAX ADVISOR"))
    blocks.append((AMOUNT_COLUMN_X, 330.0, "$75,000.00"))
    blocks.append((TITLE_COLUMN_X, 336.0, "SENIOR TECHNOLOGIST, SENIOR ADVISOR"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "short_title.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "SCHAEFER, SARAH E")
    assert row["title_raw"] == "CHIEF TAX ADVISOR"
    assert not row["parse_status"].endswith("_WITH_WRAPPED_TITLE")


def test_travel_route_line_is_never_appended_as_a_title(tmp_path: Path) -> None:
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 330.0, "DOE, JOHN Q"))
    blocks.append((TITLE_COLUMN_X, 330.0, "PROFESSIONAL STAFF"))
    blocks.append((AMOUNT_COLUMN_X, 330.0, "$1,000.00"))
    blocks.append((TITLE_COLUMN_X, 336.0, "WASHINGTON DC TO DETROIT MI AND RETURN"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "route.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "DOE, JOHN Q")
    assert row["title_raw"] == "PROFESSIONAL STAFF"


def _title_block_blocks(payee_line: list[tuple[float, str]]) -> list[tuple[float, float, str]]:
    """A three-line title block bracketed by ordinary payroll rows.

    The real pages (e.g. GPO-CDOC-117sdoc8 p2117, GPO-CDOC-119sdoc6 p2403) set a
    long title as its own block whose leading is tighter than the roster's row
    pitch, with the payee and the amount aligned to the middle fragment.
    """
    blocks = _standard_blocks()
    blocks += [(PAYEE_COLUMN_X, 320.0, "PRIOR, ROW A"),
               (TITLE_COLUMN_X, 320.0, "CLERK"),
               (AMOUNT_COLUMN_X, 320.0, "$1.00")]
    blocks.append((TITLE_COLUMN_X, 326.0,
                   "CHIEF COMMUNICATIONS ADVISOR-DEPUTY POLICY DIRECTOR FOR"))
    blocks += [(x, 331.0, text) for x, text in payee_line]
    blocks.append((TITLE_COLUMN_X, 336.0, "SPOKESPERSON TO MAY 29"))
    blocks += [(PAYEE_COLUMN_X, 342.0, "NEXT, ROW B"),
               (TITLE_COLUMN_X, 342.0, "AIDE"),
               (AMOUNT_COLUMN_X, 342.0, "$2.00")]
    return blocks


def test_title_block_above_the_payee_line_is_not_truncated(tmp_path: Path) -> None:
    blocks = _title_block_blocks([
        (PAYEE_COLUMN_X, "CHU, KEITH T"),
        # short enough not to collide with this fixture's amount column: the
        # real pages set the description column far wider than the fixture does.
        (TITLE_COLUMN_X, "ENERGY AND COMMERCE-"),
        (AMOUNT_COLUMN_X, "$44,828.60"),
    ])
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "title_block.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "CHU, KEITH T")
    assert row["title_raw"] == (
        "CHIEF COMMUNICATIONS ADVISOR-DEPUTY POLICY DIRECTOR FOR "
        "ENERGY AND COMMERCE- SPOKESPERSON TO MAY 29"
    )
    assert "_WITH_LEADING_TITLE" in row["parse_status"]
    assert row["parse_status"].endswith("_WITH_WRAPPED_TITLE")
    # the fragments must not also land on the rows bracketing the block
    assert next(r for r in result["accepted"]
                if r["payee_name_raw"] == "PRIOR, ROW A")["title_raw"] == "CLERK"
    assert next(r for r in result["accepted"]
                if r["payee_name_raw"] == "NEXT, ROW B")["title_raw"] == "AIDE"


def test_payee_line_carrying_no_title_column_is_recovered_not_rejected(tmp_path: Path) -> None:
    """The whole title sits on the lines above and below the payee's own line.

    v1 classified these as PAYROLL_ROW_WITHOUT_TITLE and rejected them as
    MISSING_OR_UNSPLIT_TITLE, losing the employment candidate outright.
    """
    blocks = _title_block_blocks([
        (PAYEE_COLUMN_X, "GOLDFINCH, COLIN E"),
        (AMOUNT_COLUMN_X, "$45,333.31"),
    ])
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "no_title_column.pdf"))
    assert all(r["payee_name_raw"] != "GOLDFINCH, COLIN E" for r in result["rejected"])
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "GOLDFINCH, COLIN E")
    assert row["title_raw"] == (
        "CHIEF COMMUNICATIONS ADVISOR-DEPUTY POLICY DIRECTOR FOR SPOKESPERSON TO MAY 29"
    )
    assert row["amount_paid_raw"] == "$45,333.31"


def test_payroll_reversal_with_sign_outside_the_currency_symbol_is_kept(tmp_path: Path) -> None:
    """GPO-CDOC-117sdoc14 p2640 prints a reversal as ``-$7,555.54``.

    v1's money pattern allowed ``$-x`` and ``-x`` but not ``-$x``, so the whole
    row -- an employment candidate, and that package's entire V3 overage --
    was dropped with no rejection receipt.
    """
    blocks = _standard_blocks()
    blocks.append((PAYEE_COLUMN_X, 330.0, "GARCIA, MICHAEL A"))
    blocks.append((TITLE_COLUMN_X, 330.0, "PROFESSIONAL STAFF MEMBER"))
    blocks.append((AMOUNT_COLUMN_X, 330.0, "-$7,555.54"))
    document, page = _new_document(False)
    _build_page(page, blocks, False)
    result = _parse(_finish(document, page, False, tmp_path / "reversal.pdf"))
    row = next(r for r in result["accepted"] if r["payee_name_raw"] == "GARCIA, MICHAEL A")
    assert row["amount_paid_raw"] == "-$7,555.54"
    assert row["title_raw"] == "PROFESSIONAL STAFF MEMBER"


def test_money_pattern_accepts_every_printed_sign_placement() -> None:
    for text in ("$112,124.96", "112,124.96", "-112,124.96", "$-112,124.96",
                 "-$112,124.96", "26.74", "-$7,555.54"):
        assert parser.MONEY_RE.match(text), text
    for text in ("112124.96", "$1,234", "B-2-59", "11/10/2025", ""):
        assert not parser.MONEY_RE.match(text), text


def test_determinism_across_repeated_parses(tmp_path: Path) -> None:
    path = _write_standard_pdf(tmp_path / "standard.pdf")
    first = _parse(path)["accepted"]
    second = _parse(path)["accepted"]
    assert first == second


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
