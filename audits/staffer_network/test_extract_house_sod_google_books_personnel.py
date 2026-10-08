from __future__ import annotations

import extract_house_sod_google_books_personnel as subject


def _vertical_word(logical_x: float, logical_y: float, value: str, page_height: float = 800.0) -> tuple:
    y1 = page_height - logical_x
    return (logical_y, y1 - 8.0, logical_y + 1.0, y1, value, 0, 0, 0)


def test_rotated_ocr_rows_merge_split_header_and_amount() -> None:
    words = [
        _vertical_word(270, 100.0, ".PAYEE"),
        _vertical_word(440, 100.0, "SERVICE"),
        _vertical_word(450, 100.0, "DATES"),
        _vertical_word(500, 101.5, "DESCRIPTION"),
        _vertical_word(715, 100.0, "YTD"),
        _vertical_word(730, 100.0, "QUARTERLY"),
        _vertical_word(280, 200.0, "DOE,"),
        _vertical_word(330, 200.0, "JANE"),
        _vertical_word(510, 200.0, "01/03/97"),
        _vertical_word(530, 200.0, "03/31/97"),
        _vertical_word(560, 200.0, "PRESS"),
        _vertical_word(600, 200.0, "SECRETARY"),
        _vertical_word(720, 201.7, "7,500.00"),
    ]
    rows = subject.logical_rows_from_words(800.0, words)
    assert len(rows) == 2
    columns = subject.header_columns(rows[0]["tokens"])
    assert columns is not None
    parsed = subject.parse_candidate_row(rows[1]["tokens"], columns)
    assert parsed == {
        "amount_raw": "7,500.00",
        "payee_raw": "DOE, JANE",
        "service_end_date_raw": "03/31/97",
        "service_start_date_raw": "01/03/97",
        "title_description_raw": "PRESS SECRETARY",
    }


def test_candidate_row_requires_two_dates_and_amount() -> None:
    columns = {"amount": 715000, "description": 500000, "payee": 270000, "service": 440000}
    tokens = [[280000, "DOE,"], [330000, "JANE"], [510000, "01/03/97"], [560000, "PRESS"], [600000, "SECRETARY"]]
    assert subject.parse_candidate_row(tokens, columns) is None


def test_period_bounds_and_two_digit_candidate_dates() -> None:
    assert subject.period_bounds("1997Q1") == ("1997-01-01", "1997-03-31")
    assert subject.parse_candidate_date("01/03/97") == "1997-01-03"
    assert subject.parse_candidate_date("13/40/97") is None
