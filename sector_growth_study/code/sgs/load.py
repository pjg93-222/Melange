"""Read the study workbooks read-only and validate them. Any violation raises LoadError naming file, sheet and column.

Checks per sheet read: the sheet exists; header in row 1 with unique non-empty names; required columns present;
no cell anywhere in the workbook starts with "=" (formula or formula-like text); the key columns are complete and unique.
Every study workbook names its study-sector column `study_sector` (04 renamed `sector` -> `study_sector` on
2026-09-25, Paul's uniform-column ruling). Sheets flagged `study_sector=True` require that column; a sheet that still
carries only `sector` is rejected with a message naming the rename (in 01, 06 and 07 `sector` is a source label).
Optional sheets (SheetSpec.optional) are validated when present and skipped when absent: 02 `expected_control_2023_2026`
(Paul's ruling of 2026-09-25) and 02 `expected_control_markets` (a Polymarket/Kalshi daily history that may be added).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import openpyxl
import pandas as pd

from . import config


class LoadError(Exception):
    """A workbook failed validation."""


@dataclass(frozen=True)
class SheetSpec:
    required: tuple
    key: tuple
    study_sector: bool = False  # the sheet must carry the study-sector column `study_sector`
    optional: bool = False  # validated when present; absent is allowed (the frame is then not in `frames`)


@dataclass(frozen=True)
class WorkbookSpec:
    name: str
    file: str
    sheets: dict


WORKBOOKS = (
    WorkbookSpec("controls", "00_controls.xlsx", {
        "data": SheetSpec(("year", "presidential_year", "midterm_year", "status"), ("year",)),
    }),
    WorkbookSpec("lobbying", "01_lobbying_expenditures.xlsx", {
        "data": SheetSpec(
            ("source", "sector", "confidence", "year", "period", "lobby_income_real_2025_usd",
             "lobby_expenses_real_2025_usd", "lobby_amount_undifferentiated_real_2025_usd", "status"),
            ("source", "sector", "confidence", "year", "period")),
    }),
    WorkbookSpec("election", "02_election_forecasting.xlsx", {
        "data": SheetSpec(("calendar_year", "chamber", "p_dem_expected", "status"), ("calendar_year", "chamber")),
        "seat_calls": SheetSpec(("chamber", "election_year", "pred_dem_net_change", "status"), ("chamber", "election_year")),
        "expected_control_2023_2026": SheetSpec(
            ("calendar_year", "chamber", "exp_dem", "method", "flag", "status", "source_id"), ("calendar_year", "chamber"),
            optional=True),
        "expected_control_markets": SheetSpec(
            ("date", "calendar_year", "chamber", "market", "status"), ("date", "chamber", "market"), optional=True),
    }),
    WorkbookSpec("seats", "03_actual_seat_gain.xlsx", {
        "current_control": SheetSpec(("calendar_year", "chamber", "dem_control", "status"), ("calendar_year", "chamber")),
    }),
    WorkbookSpec("spending", "04_campaign_spending.xlsx", {
        "data": SheetSpec(
            ("year", "company", "recipient_category", "party", "funding_source", "giving_real_2025_usd", "status"),
            ("year", "study_sector", "company", "recipient_category", "party", "funding_source"), study_sector=True),
        "sector_year": SheetSpec(("year", "giving_real_2025_usd", "status"), ("study_sector", "year"), study_sector=True),
        "tier_by_year": SheetSpec(
            ("year", "company", "employee_tier", "giving_real_2025_usd", "status"),
            ("year", "study_sector", "company", "employee_tier"), study_sector=True),
    }),
    WorkbookSpec("predicted", "06_predicted_industry_growth.xlsx", {
        "data": SheetSpec(
            ("year", "predicted_growth_pct", "forecast_publication_month", "forecast_age_months", "status"),
            ("study_sector", "year"), study_sector=True),
    }),
    WorkbookSpec("actual", "07_actual_industry_growth.xlsx", {
        "data": SheetSpec(
            ("sector", "year", "growth_same_year_pct", "growth_previous_year_pct", "status"),
            ("sector", "year"), study_sector=True),
    }),
    WorkbookSpec("crosswalk", "sector_crosswalk.xlsx", {
        "data": SheetSpec(("mentat_industry", "lda_lobbying_sector"), ("study_sector",), study_sector=True),
    }),
)


@dataclass
class LoadedWorkbook:
    name: str
    path: Path
    sha256: str
    size_bytes: int
    mtime_utc: str
    read_at_utc: str
    frames: dict = field(default_factory=dict)  # sheet name -> DataFrame


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _utc_iso(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sheet_rows(ws, file_label: str):
    """All rows of a sheet as tuples; raises on any cell whose value starts with '='."""
    rows = []
    for r_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
        for c_idx, v in enumerate(row, start=1):
            if isinstance(v, str) and v.startswith("="):
                col = openpyxl.utils.get_column_letter(c_idx)
                raise LoadError(
                    f"{file_label} [{ws.title}] cell {col}{r_idx}: value starts with '=' ({v[:40]!r}); "
                    "the study format is values only")
        rows.append(row)
    return rows


def _frame(rows, file_label: str, sheet: str) -> pd.DataFrame:
    if not rows:
        raise LoadError(f"{file_label} [{sheet}]: empty sheet (no header row)")
    header = list(rows[0])
    while header and header[-1] is None:  # trailing empty header cells
        header.pop()
    names = []
    for i, h in enumerate(header, start=1):
        if h is None or (isinstance(h, str) and not h.strip()):
            raise LoadError(f"{file_label} [{sheet}] header column {i}: empty header name in row 1")
        names.append(h if not isinstance(h, str) else h.strip())
    dup = sorted({str(n) for n in names if names.count(n) > 1})
    if dup:
        raise LoadError(f"{file_label} [{sheet}] header: duplicate column names {dup}")
    body = [tuple(r[: len(names)]) + (None,) * max(0, len(names) - len(r)) for r in rows[1:]]
    body = [r for r in body if any(v is not None for v in r)]
    return pd.DataFrame.from_records(body, columns=names)


def validate_frame(df: pd.DataFrame, spec: SheetSpec, file_label: str, sheet: str) -> pd.DataFrame:
    df = df.copy()
    if spec.study_sector and "study_sector" not in df.columns:
        extra = (" (a `sector` column is present: the study format names the study-sector column `study_sector` since "
                 "the 2026-09-25 uniform-column ruling)") if "sector" in df.columns else ""
        raise LoadError(f"{file_label} [{sheet}] column study_sector: required column missing{extra}")
    for col in spec.required:
        if col not in df.columns:
            raise LoadError(f"{file_label} [{sheet}] column {col}: required column missing")
    for col in spec.key:
        if col not in df.columns:
            raise LoadError(f"{file_label} [{sheet}] column {col}: key column missing")
    key = list(spec.key)
    # Key columns must be complete except where a key part is legitimately blank (e.g. LobbyView confidence on LDA
    # rows); blanks are compared as their own value.
    keyed = df[key].astype(object).where(df[key].notna(), "<blank>")
    dups = keyed.duplicated(keep=False)
    if dups.any():
        example = keyed[dups].head(3).to_dict("records")
        raise LoadError(f"{file_label} [{sheet}] key {key}: {int(dups.sum())} rows share a key; e.g. {example}")
    return df


def read_workbook(path: Path, sheets: dict, name: str = "") -> LoadedWorkbook:
    path = Path(path)
    label = path.name
    if not path.exists():
        raise LoadError(f"{label}: file not found at {path}")
    st = path.stat()
    read_at = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
    try:
        frames = {}
        all_rows = {}
        for ws in wb.worksheets:  # the '=' rule covers every sheet of the workbook
            all_rows[ws.title] = _sheet_rows(ws, label)
        for sheet, spec in sheets.items():
            if sheet not in all_rows:
                if spec.optional:
                    continue
                raise LoadError(f"{label} [{sheet}]: sheet missing (present: {sorted(all_rows)})")
            frames[sheet] = validate_frame(_frame(all_rows[sheet], label, sheet), spec, label, sheet)
    finally:
        wb.close()
    return LoadedWorkbook(name=name or label, path=path, sha256=sha256_file(path), size_bytes=st.st_size,
                          mtime_utc=_utc_iso(st.st_mtime), read_at_utc=read_at, frames=frames)


def load_all(data_dir: Path | None = None) -> dict:
    """Load and validate every study workbook. Returns {workbook name: LoadedWorkbook}."""
    data_dir = Path(data_dir or config.DATA_DIR)
    out = {}
    for spec in WORKBOOKS:
        out[spec.name] = read_workbook(data_dir / spec.file, spec.sheets, spec.name)
    return out
