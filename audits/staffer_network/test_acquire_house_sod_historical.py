from __future__ import annotations

import gzip
import io
import json
from pathlib import Path

import acquire_house_sod_historical as historical


def _row(page: int, y: int, words: list[tuple[int, str]]) -> dict:
    return {"page_number": page, "row_y_milli": y, "words": [[x, value] for x, value in words]}


def test_personnel_total_beyond_ytd_boundary_closes_section(tmp_path: Path) -> None:
    """Expense rows after a right-shifted personnel total must not leak in."""
    visual_path = tmp_path / "visual.ndjson.gz"
    rows = [
        _row(
            1,
            100,
            [
                (126000, "DATE"),
                (156000, "VOUCHER"),
                (179320, "NO."),
                (199000, "PAYEE"),
                (365004, "SERVICE"),
                (385984, "DATES"),
                (417004, "DESCRIPTION"),
                (587346, "YTD"),
                (598336, "AMOUNT"),
                (620686, "QUARTERLY"),
                (648338, "AMOUNT"),
            ],
        ),
        _row(1, 110, [(169145, "2010"), (200000, "HON."), (230000, "TEST"), (270000, "OFFICE")]),
        _row(1, 120, [(156000, "PERSONNEL"), (182642, "COMPENSATION")]),
        _row(
            1,
            130,
            [
                (199000, "DOE,"),
                (230000, "JANE"),
                (365004, "10/01/10"),
                (390000, "12/31/10"),
                (417004, "PRESS"),
                (450000, "SECRETARY"),
                (642029, "12,500.00"),
            ],
        ),
        # TOTALS is deliberately to the right of the bounded detail slice.
        _row(
            1,
            140,
            [
                (538068, "PERSONNEL"),
                (564710, "COMPENSATION"),
                (599350, "TOTALS:"),
                (642029, "12,500.00"),
            ],
        ),
        _row(
            1,
            150,
            [
                (199000, "DOE,"),
                (230000, "JANE"),
                (365004, "09/20/10"),
                (390000, "10/04/10"),
                (417004, "PRIVATE"),
                (450000, "AUTO"),
                (480000, "MILEAGE"),
                (642029, "84.50"),
            ],
        ),
    ]
    with gzip.open(visual_path, "wt", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row) + "\n")

    output = io.StringIO()
    stats = historical.parse_visual_period(
        {
            "pdf_sha256": "a" * 64,
            "pdf_url": "https://www.house.gov/test.pdf",
            "period": "2010Q4",
            "period_end": "2010-12-31",
            "period_start": "2010-10-01",
            "text_path": str(visual_path),
        },
        output,
    )
    candidates = [json.loads(line) for line in output.getvalue().splitlines()]
    assert stats["personnel_total_rows"] == 1
    assert stats["payroll_candidate_rows"] == 1
    assert [row["title_description_raw"] for row in candidates] == ["PRESS SECRETARY"]
