from __future__ import annotations

import gzip
import json
from pathlib import Path

import reparse_house_sod_complete as complete


def _row(page: int, y: int, words: list[tuple[int, str]]) -> dict:
    return {
        "page_number": page,
        "row_y_milli": y,
        "words": [[x, value] for x, value in words],
    }


class _Rows:
    def __init__(self) -> None:
        self.values: list[dict] = []

    def write(self, row: dict) -> None:
        self.values.append(row)


def test_numeric_position_code_is_a_personnel_title(tmp_path: Path) -> None:
    visual = tmp_path / "visual.ndjson.gz"
    rows = [
        _row(
            1,
            100,
            [
                (126000, "DATE"),
                (156000, "VOUCHER"),
                (199000, "PAYEE"),
                (365004, "SERVICE"),
                (385984, "DATES"),
                (417004, "DESCRIPTION"),
                (587346, "YTD"),
                (620686, "QUARTERLY"),
                (648338, "AMOUNT"),
            ],
        ),
        _row(1, 110, [(169145, "2013"), (200000, "HON."), (230000, "TEST"), (270000, "OFFICE")]),
        _row(1, 120, [(156000, "PERSONNEL"), (182642, "COMPENSATION")]),
        _row(
            1,
            130,
            [
                (199000, "WEINBERG,DAVID"),
                (240000, "M"),
                (365004, "04/01/13"),
                (390000, "06/30/13"),
                (417004, "198214"),
                (642029, "17,499.99"),
            ],
        ),
    ]
    with gzip.open(visual, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")

    accepted = _Rows()
    residue = _Rows()
    counts, candidates, _headings = complete.parse_period(
        {
            "period": "2013Q2",
            "period_start": "2013-04-01",
            "period_end": "2013-06-30",
            "text_path": str(visual),
            "pdf_sha256": "a" * 64,
            "pdf_url": "https://example.test/official.pdf",
        },
        {"page_printed": {1: 1608}},
        accepted,
        residue,
    )

    assert counts["payroll_candidate_rows"] == 1
    assert not residue.values
    assert candidates[0]["payee_raw"] == "WEINBERG,DAVID M"
    assert candidates[0]["title_description_raw"] == "198214"


def test_toc_abbreviations_and_structural_subunit_resolution() -> None:
    assert complete.office_tokens("Oversight and Government Reform") <= complete.office_tokens(
        "2015 COMM ON OVRSIGHT & GOVT REFORM"
    )
    assert complete.office_tokens("Energy Independence and Global Warming") <= complete.office_tokens(
        "2011 ENERGY INDEPEN AND GLB WARMING"
    )

    toc = [{
        "label_raw": "Chief Administrative Officer",
        "printed_page_number": 32,
        "office_family": "admin",
    }]
    headings = [{
        "employing_office_raw": "2010 CAO ADVANCED BUSINESS SOLUTION",
        "source_pdf_printed_page_number": 33,
    }]
    [resolved] = complete.reconcile_toc_offices(toc, headings)
    assert resolved["office_resolution_status"] == "RESOLVED"
    assert resolved["office_resolution_scope"] == (
        "TOC_DECLARED_OFFICE_ONLY_NO_EMPLOYING_OFFICE_EQUIVALENCE"
    )
    assert resolved["resolved_employing_office_raw"] is None
    assert resolved["resolved_toc_office_label_raw"] == "Chief Administrative Officer"
