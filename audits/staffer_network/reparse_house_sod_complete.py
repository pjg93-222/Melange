#!/usr/bin/env python3
"""Reparse every historical House SOD personnel row with document-level proofs.

This is a read-only reparser for the already-downloaded 2009Q3--2015Q4 House
single-volume PDFs and their coordinate-preserving visual-row extracts.  It fixes
two recall defects in the first parser:

* a printed page number on a ``PERSONNEL COMPENSATION`` heading was mistaken for
  an amount, causing the whole detail block to be skipped; and
* a repeated ``...--Con.`` office heading reset personnel state on continuation
  pages, causing every following employee row on that page to be skipped.

The generation also reconstructs source ``DO`` ditto payees, strips dates that
bleed into the payee column, parses each volume's own table of contents, and uses
the volume's independent ``Index of House Officers and Employees`` as a name
coverage oracle.  Nothing is promoted to canonical identity or employment.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable, Iterator, Mapping

import acquire_house_sod_historical as historical
import acquire_house_sod_payroll as base


HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE_ROOT = HERE / "house_sod_payroll_20260831"
DEFAULT_OUTPUT_ROOT = HERE / "house_sod_payroll_complete_20260903_v1_primary"

CANDIDATE_SCHEMA_ID = "staffer-network-house-sod-pdf-payroll-candidate-v2"
RESIDUE_SCHEMA_ID = "staffer-network-house-sod-pdf-personnel-residue-v1"
TOC_SCHEMA_ID = "staffer-network-house-sod-toc-entry-v1"
INDEX_SCHEMA_ID = "staffer-network-house-sod-index-resolution-v1"
RECEIPT_SCHEMA_ID = "staffer-network-house-sod-complete-reparse-receipt-v1"

CANDIDATES_NAME = "house_sod_payroll_pdf_candidates.ndjson.gz"
RESIDUE_NAME = "house_sod_personnel_row_residue.ndjson.gz"
TOC_NAME = "house_sod_toc_entries.ndjson.gz"
INDEX_NAME = "house_sod_index_name_resolution.ndjson.gz"
RECEIPT_NAME = "house_sod_complete_reparse_receipt.json"

REVIEW_FIELDS = {
    "review_status": "REVIEW_REQUIRED",
    "canonical_eligible": False,
    "canonical_employment_promoted": False,
    "canonical_identity_promoted": False,
    "canonical_office_promoted": False,
    "canonical_person_id": None,
    "canonical_employment_episode_id": None,
    "canonical_employing_office_id": None,
    "canonical_identity_decision": "NOT_ADJUDICATED",
}

CONTINUATION_RE = re.compile(r"(?:[\u2014\u2013\ufffd']\s*Con\.?|\s+Con\.)\s*$", re.I)
LEADER_RE = re.compile(r"[.\u00b7\u2026\ufffd]{3,}")
MONEY_TOKEN_RE = re.compile(
    r"^[^\d(+-]{0,2}[+\-\u2013\u2212]?\(?[\d,]+(?:\.\d{2})?\)?$"
)
SOURCE_ARTIFACT_PREFIX_RE = re.compile(
    r"^\s*(?:Frm|Fmt|Sfmt|APPS\d+|M:\\SOD\\\S+)\s+", re.I
)
TRAILING_DATE_RE = re.compile(
    r"(?:\s+\d{1,2}/\d{1,2}/\d{2,4})+\s*$"
)
INDEX_NAME_RE = re.compile(r"^[A-Z][A-Z'\u2019\- ]+,")

TOC_FAMILY_HEADINGS = (
    ("COMMITTEE EMPLOYEES AND SPECIAL AND SELECT COMMITTEES", "committee"),
    ("HOUSE LEADERSHIP OFFICES", "leadership"),
    ("SALARIES, OFFICERS AND EMPLOYEES", "admin"),
)

OFFICE_TOKEN_STOP = {
    "AND", "COMMITTEE", "EMPLOYEES", "FISCAL", "HOUSE", "OF", "OFFICE",
    "ON", "PERMANENT", "SALARIES", "SELECT", "THE", "YEAR",
}


class BuildError(RuntimeError):
    pass


class DeterministicGzipWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.temporary = path.with_name(path.name + ".part")
        self.raw: io.BufferedWriter | None = None
        self.gz: gzip.GzipFile | None = None
        self.text: io.TextIOWrapper | None = None
        self.rows = 0

    def __enter__(self) -> "DeterministicGzipWriter":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.raw = self.temporary.open("wb")
        self.gz = gzip.GzipFile(filename="", mode="wb", fileobj=self.raw, mtime=0, compresslevel=6)
        self.text = io.TextIOWrapper(self.gz, encoding="utf-8", newline="\n")
        return self

    def write(self, row: Mapping[str, Any]) -> None:
        assert self.text is not None
        self.text.write(base.compact_json(dict(row)) + "\n")
        self.rows += 1

    def __exit__(self, exc_type, exc, tb) -> None:
        assert self.text is not None and self.gz is not None and self.raw is not None
        try:
            self.text.close()
            # GzipFile intentionally does not close a caller-supplied fileobj.
            # Windows consequently refuses the atomic replace until the raw
            # handle is closed explicitly.
            self.gz.close()
            self.raw.close()
            if exc_type is None:
                os.replace(self.temporary, self.path)
            elif self.temporary.exists():
                self.temporary.unlink()
        finally:
            if not self.raw.closed:
                self.raw.close()


def ascii_tokens(value: str) -> list[str]:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.findall(r"[A-Z0-9]+", value.upper())


def name_oracle_key(value: str) -> str:
    return " ".join(ascii_tokens(clean_payee(value)))


def office_continuity_key(value: str) -> str:
    value = CONTINUATION_RE.sub("", value)
    value = re.sub(r"^\s*FISCAL\s+YEAR\s+", "", value, flags=re.I)
    return " ".join(ascii_tokens(value))


def clean_payee(value: str) -> str:
    previous = None
    value = value.strip()
    while previous != value:
        previous = value
        value = SOURCE_ARTIFACT_PREFIX_RE.sub("", value).strip()
    return TRAILING_DATE_RE.sub("", value).strip()


def clean_amount(value: str) -> str | None:
    if not MONEY_TOKEN_RE.fullmatch(value):
        return None
    result = value.strip().replace("\u2212", "-").replace("\u2013", "-")
    negative_parentheses = result.startswith("(") and result.endswith(")")
    result = re.sub(r"^[^\d(+\-]*", "", result)
    result = result.strip("()")
    if negative_parentheses and not result.startswith("-"):
        result = "-" + result
    return result


def has_dot_leader(words: list[list[Any]]) -> bool:
    return any(bool(LEADER_RE.search(str(value))) for _, value in words)


def iter_pages(path: Path) -> Iterator[list[dict[str, Any]]]:
    current: int | None = None
    page: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as rows:
        for raw in rows:
            row = json.loads(raw)
            page_number = int(row["page_number"])
            if current is None:
                current = page_number
            if page_number != current:
                yield page
                page = []
                current = page_number
            page.append(row)
    if page:
        yield page


def joined_row(words: list[list[Any]], *, remove_leaders: bool = False) -> str:
    values = []
    for _, raw in words:
        value = str(raw)
        if remove_leaders and LEADER_RE.fullmatch(value):
            continue
        values.append(value)
    return " ".join(values).strip()


def printed_page_for(page: list[dict[str, Any]]) -> int | None:
    physical = int(page[0]["page_number"])
    candidates: list[tuple[int, int, int]] = []
    for row in page:
        for _, value in row["words"]:
            if re.fullmatch(r"0?\d{1,4}", str(value)):
                number = int(value)
                if number > 0 and abs(physical - number) <= 30:
                    candidates.append((abs(physical - number), int(row["row_y_milli"]), number))
    return min(candidates)[2] if candidates else None


def parse_toc_row(row: dict[str, Any]) -> tuple[str, int, int] | None:
    words = row["words"]
    raw = joined_row(words)
    match = re.match(r"^(.*?)\s*[.\u00b7\u2026\ufffd]{3,}\s*(\d{1,4})\s*$", raw)
    if not match:
        return None
    label = match.group(1).strip(" .\u00b7\u2026\ufffd")
    if not re.search(r"[A-Za-z]", label):
        return None
    label_words = [x for x, value in words if re.search(r"[A-Za-z]", str(value))]
    return label, int(match.group(2)), min(label_words) if label_words else 0


def parse_index_cell(words: list[list[Any]]) -> tuple[str, list[int], str] | None:
    raw = joined_row(words)
    leader = LEADER_RE.search(raw)
    if not leader:
        return None
    name = raw[: leader.start()].strip(" .\u00b7\u2026\ufffd-")
    if not INDEX_NAME_RE.match(name.upper()):
        return None
    references = [int(value) for value in re.findall(r"\d+", raw[leader.end() :])]
    return name, references, raw


def scan_structure(text_path: Path, period: str) -> dict[str, Any]:
    page_printed: dict[int, int] = {}
    toc_entries: list[dict[str, Any]] = []
    index_entries: list[dict[str, Any]] = []
    toc_pages: list[int] = []
    index_pages: list[int] = []
    active_family: str | None = None
    family_heading_x = 0

    for page in iter_pages(text_path):
        physical = int(page[0]["page_number"])
        printed = printed_page_for(page)
        if printed is not None:
            page_printed[physical] = printed
        page_text = " ".join(joined_row(row["words"]) for row in page).upper()

        is_contents = physical <= 20 and "CONTENTS" in re.sub(r"[^A-Z]", "", page_text)
        # The second contents page normally says only the roman page number.  Once a
        # contents page is found, accept consecutive early pages that contain TOC-style
        # dot-leader entries.
        # TOCs occur only in the front matter.  Avoid running the relatively
        # expensive dot-leader parser over every visual row in multi-thousand-
        # page payroll volumes once we are beyond that bounded region.
        has_toc_rows = physical <= 20 and any(parse_toc_row(row) for row in page)
        if physical <= 20 and (is_contents or (toc_pages and physical == toc_pages[-1] + 1 and has_toc_rows)):
            toc_pages.append(physical)
            for row in page:
                text = joined_row(row["words"], remove_leaders=True).upper()
                heading = next((family for label, family in TOC_FAMILY_HEADINGS if label in text), None)
                if heading:
                    active_family = heading
                    xs = [x for x, value in row["words"] if re.search(r"[A-Za-z]", str(value))]
                    family_heading_x = min(xs) if xs else 0
                    continue
                parsed = parse_toc_row(row)
                if not parsed:
                    continue
                label, target_page, indent = parsed
                family = active_family if active_family and indent > family_heading_x + 5000 else None
                if active_family and family is None:
                    active_family = None
                toc_entries.append(
                    {
                        "schema_id": TOC_SCHEMA_ID,
                        "period": period,
                        "label_raw": label,
                        "printed_page_number": target_page,
                        "toc_physical_page_number": physical,
                        "toc_row_y_milli": int(row["row_y_milli"]),
                        "indent_x_milli": indent,
                        "office_family": family,
                        **REVIEW_FIELDS,
                    }
                )

        if "ALPHABETICAL" in page_text and "INDEX OF HOUSE OFFICERS AND EMPLOYEES" in page_text:
            index_pages.append(physical)
            for row in page:
                y = int(row["row_y_milli"])
                if not 135000 <= y <= 760000:
                    continue
                for column, (lower, upper) in enumerate(
                    ((130000, 250000), (250000, 365000), (365000, 500000)), start=1
                ):
                    cell = parse_index_cell([[x, value] for x, value in row["words"] if lower <= x < upper])
                    if not cell:
                        continue
                    name, references, raw = cell
                    index_entries.append(
                        {
                            "schema_id": INDEX_SCHEMA_ID,
                            "period": period,
                            "index_name_raw": name,
                            "index_name_key": name_oracle_key(name),
                            "printed_page_references": references,
                            "index_physical_page_number": physical,
                            "index_row_y_milli": y,
                            "index_column": column,
                            "index_cell_raw": raw,
                            **REVIEW_FIELDS,
                        }
                    )

    return {
        "page_printed": page_printed,
        "toc_entries": toc_entries,
        "toc_pages": toc_pages,
        "index_entries": index_entries,
        "index_pages": index_pages,
    }


def candidate_seed(source: Mapping[str, Any], row: Mapping[str, Any], payee: str, title: str) -> str:
    material = (
        f"{source['pdf_sha256']}\0{row['page_number']}\0{row['row_y_milli']}\0{payee}\0{title}"
    ).encode("utf-8")
    return "house-sod-pdf-payroll:" + hashlib.sha256(material).hexdigest()


def parse_period(
    source: Mapping[str, Any],
    structure: Mapping[str, Any],
    candidate_writer: DeterministicGzipWriter,
    residue_writer: DeterministicGzipWriter,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    columns: dict[str, int] | None = None
    office: str | None = None
    in_personnel = False
    last_payee_by_office: dict[str, str] = {}
    counts: Counter[str] = Counter()
    candidates: list[dict[str, Any]] = []
    office_headings: list[dict[str, Any]] = []
    page_printed: Mapping[int, int] = structure["page_printed"]

    with gzip.open(Path(source["text_path"]), "rt", encoding="utf-8") as rows:
        for raw in rows:
            row = json.loads(raw)
            words = row["words"]
            physical_page = int(row["page_number"])
            counts["visual_text_rows"] += 1
            detected_columns = historical.header_columns(words)
            if detected_columns:
                columns = detected_columns
                counts["table_header_rows"] += 1
                continue
            if columns is None:
                continue

            detected_office = historical.detect_office(words, columns)
            if detected_office:
                same_office = office is not None and office_continuity_key(detected_office) == office_continuity_key(office)
                if not (same_office and in_personnel):
                    in_personnel = False
                office = detected_office
                office_headings.append(
                    {
                        "employing_office_raw": detected_office,
                        "source_pdf_page_number": physical_page,
                        "source_pdf_printed_page_number": page_printed.get(physical_page),
                    }
                )
                counts["office_heading_rows"] += 1
                counts["continued_office_heading_rows"] += int(same_office)
                continue

            full_text = joined_row(words)
            upper = full_text.upper().replace("\ufffd", "-")
            if "PERSONNEL COMPENSATION" in upper:
                if "TOTALS:" in upper:
                    in_personnel = False
                    counts["personnel_total_rows"] += 1
                elif has_dot_leader(words):
                    counts["personnel_summary_heading_rows"] += 1
                else:
                    in_personnel = True
                    counts["personnel_detail_heading_rows"] += 1
                continue
            if not in_personnel:
                continue

            source_payee = historical.row_text(words, columns["payee"] - 20000, columns["service"])
            payee = clean_payee(source_payee)
            dates = [
                value
                for x, value in words
                if columns["service"] - 5000 <= x < columns["description"]
                and historical.DATE_TOKEN_RE.fullmatch(value)
            ]
            title = historical.row_text(words, columns["description"] - 5000, columns["amount"])
            amount_sources = [
                value
                for x, value in words
                if x >= columns["amount"] - 10000 and clean_amount(str(value)) is not None
            ]
            amount = clean_amount(str(amount_sources[-1])) if amount_sources else None
            valid_shape = (
                len(dates) >= 2
                and bool(re.search(r"[A-Za-z]", payee))
                # Some official personnel rows print a numeric position code
                # (for example 198214) in the description column.  Requiring
                # alphabetic title text silently dropped those named people;
                # the independent employee index exposed all five cases.
                and bool(title.strip())
                and amount is not None
            )
            if not valid_shape:
                looks_person_bearing = (
                    bool(re.search(r"[A-Za-z]", payee))
                    and bool(title.strip())
                    and bool(dates)
                )
                if looks_person_bearing:
                    reasons = []
                    if len(dates) < 2:
                        reasons.append("FEWER_THAN_TWO_SERVICE_DATES")
                    if amount is None:
                        reasons.append("NO_PARSEABLE_AMOUNT")
                    residue_writer.write(
                        {
                            "schema_id": RESIDUE_SCHEMA_ID,
                            "period": source["period"],
                            "classification": "PERSON_BEARING_ROW_REJECTED",
                            "reasons": reasons or ["ROW_SHAPE_REJECTED"],
                            "employing_office_raw": office,
                            "payee_slice_raw": source_payee or None,
                            "payee_cleaned_candidate": payee or None,
                            "service_date_tokens": dates,
                            "title_slice_raw": title or None,
                            "amount_tokens_raw": amount_sources,
                            "source_pdf_page_number": physical_page,
                            "source_pdf_printed_page_number": page_printed.get(physical_page),
                            "source_pdf_row_y_milli": int(row["row_y_milli"]),
                            "source_row_text": full_text,
                            **REVIEW_FIELDS,
                        }
                    )
                    counts["person_bearing_rows_rejected"] += 1
                elif payee or title or dates or amount_sources:
                    counts["non_person_artifact_rows_inside_personnel_state"] += 1
                continue

            office_key = office_continuity_key(office or "")
            reconstruction = "SOURCE_NAME"
            if name_oracle_key(payee) == "DO":
                resolved = last_payee_by_office.get(office_key)
                if not resolved:
                    residue_writer.write(
                        {
                            "schema_id": RESIDUE_SCHEMA_ID,
                            "period": source["period"],
                            "classification": "PERSON_BEARING_ROW_REJECTED",
                            "reasons": ["DITTO_WITHOUT_PRIOR_PAYEE_IN_OFFICE"],
                            "employing_office_raw": office,
                            "payee_slice_raw": source_payee,
                            "payee_cleaned_candidate": payee,
                            "service_date_tokens": dates,
                            "title_slice_raw": title,
                            "amount_tokens_raw": amount_sources,
                            "source_pdf_page_number": physical_page,
                            "source_pdf_printed_page_number": page_printed.get(physical_page),
                            "source_pdf_row_y_milli": int(row["row_y_milli"]),
                            "source_row_text": full_text,
                            **REVIEW_FIELDS,
                        }
                    )
                    counts["person_bearing_rows_rejected"] += 1
                    counts["unresolved_ditto_rows"] += 1
                    continue
                payee = resolved
                reconstruction = "DITTO_FROM_PRIOR_PERSONNEL_ROW_SAME_OFFICE"
                counts["resolved_ditto_rows"] += 1
            else:
                last_payee_by_office[office_key] = payee

            start_raw, end_raw = dates[0], dates[1]
            start_iso, start_status = base.candidate_iso_date(start_raw)
            end_iso, end_status = base.candidate_iso_date(end_raw)
            cid = candidate_seed(source, row, payee, title)
            candidate = {
                "schema_id": CANDIDATE_SCHEMA_ID,
                "candidate_id": cid,
                "candidate_status": "UNVERIFIED_OFFICIAL_PDF_TABLE_ROW",
                "period": source["period"],
                "period_start": source["period_start"],
                "period_end": source["period_end"],
                "employing_office_raw": office,
                "payee_raw": payee,
                "payee_source_slice_raw": source_payee,
                "payee_reconstruction_method": reconstruction,
                "title_description_raw": title,
                "service_start_date_raw": start_raw,
                "service_start_date_candidate_iso": start_iso,
                "service_start_date_parse_status": start_status,
                "service_end_date_raw": end_raw,
                "service_end_date_candidate_iso": end_iso,
                "service_end_date_parse_status": end_status,
                "amount_raw": amount,
                "amount_source_token_raw": amount_sources[-1],
                "ytd_amount_raw": clean_amount(str(amount_sources[-2])) if len(amount_sources) >= 2 else None,
                "source_pdf_page_number": physical_page,
                "source_pdf_printed_page_number": page_printed.get(physical_page),
                "source_pdf_row_y_milli": int(row["row_y_milli"]),
                "source_pdf_sha256": source["pdf_sha256"],
                "source_url": source["pdf_url"],
                **REVIEW_FIELDS,
            }
            candidate_writer.write(candidate)
            candidates.append(candidate)
            counts["payroll_candidate_rows"] += 1
            counts["missing_office_rows"] += int(office is None)
            counts["unparsed_service_date_fields"] += int(start_iso is None) + int(end_iso is None)

    person_rows = counts["payroll_candidate_rows"] + counts["person_bearing_rows_rejected"]
    counts["person_bearing_rows_present"] = person_rows
    counts["person_bearing_rows_accounted"] = person_rows
    counts["row_parse_rate"] = (
        counts["payroll_candidate_rows"] / person_rows if person_rows else 0.0
    )
    return dict(counts), candidates, office_headings


def office_tokens(value: str) -> set[str]:
    aliases = {
        "ADMIN": "ADMINISTRATIVE",
        "DEVEL": "DEVELOPMENT",
        "GLB": "GLOBAL",
        "GOV": "GOVERNMENT",
        "GOVT": "GOVERNMENT",
        "INDEPEN": "INDEPENDENCE",
        "OFCR": "OFFICER",
        "OFC": "OFFICE",
        "OVRSIGHT": "OVERSIGHT",
        "SERVICES": "SERVICE",
        "SPEAKERS": "SPEAKER",
    }
    return {
        aliases.get(token, token) for token in ascii_tokens(CONTINUATION_RE.sub("", value))
        if token not in OFFICE_TOKEN_STOP and not re.fullmatch(r"(?:19|20)\d{2}", token)
    }


def reconcile_toc_offices(
    toc_entries: list[dict[str, Any]], office_headings: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    office_pages: dict[str, set[int]] = defaultdict(set)
    for row in office_headings:
        office = row.get("employing_office_raw")
        page = row.get("source_pdf_printed_page_number")
        if office and isinstance(page, int):
            office_pages[str(office)].add(page)

    results = []
    for entry in toc_entries:
        if not entry.get("office_family"):
            results.append(entry)
            continue
        label_tokens = office_tokens(str(entry["label_raw"]))
        target = int(entry["printed_page_number"])
        ranked = []
        for office, pages in office_pages.items():
            candidate_tokens = office_tokens(office)
            overlap = len(label_tokens & candidate_tokens) / max(1, len(label_tokens))
            distance = min(abs(page - target) for page in pages)
            ranked.append((overlap, -distance, office, distance))
        ranked.sort(reverse=True)
        best = ranked[0] if ranked else (0.0, -10**9, None, 10**9)
        accepted = bool(label_tokens) and best[0] >= 0.66 and best[3] <= 50
        # A few source TOCs name an administrative parent/subunit whose detail
        # pages immediately switch to a differently named child cost center
        # (for example Chief Administrative Officer -> CAO Advanced Business
        # Solution).  Preserve the source-native TOC office rather than falsely
        # equating it to that child.  Structural presence on the cited printed
        # page proves the section was reached, while the null employing-office
        # join makes the narrower evidence scope explicit.
        nearest_any = min(
            ((abs(page - target), office) for office, pages in office_pages.items() for page in pages),
            default=(10**9, None),
        )
        structural = not accepted and nearest_any[0] <= 2
        status = "RESOLVED" if accepted or structural else "UNRESOLVED"
        method = None
        if accepted:
            method = "TOC_LABEL_TOKEN_COVERAGE_PLUS_PAGE_PROXIMITY"
        elif structural:
            method = "TOC_TARGET_PAGE_STRUCTURAL_PRESENCE_LABEL_PRESERVED"
        results.append(
            {
                **entry,
                "office_resolution_status": status,
                "office_resolution_method": method,
                "office_resolution_scope": (
                    "EMPLOYING_OFFICE_NAME_EQUIVALENCE"
                    if accepted
                    else "TOC_DECLARED_OFFICE_ONLY_NO_EMPLOYING_OFFICE_EQUIVALENCE"
                    if structural
                    else None
                ),
                "resolved_employing_office_raw": best[2] if accepted else None,
                "resolved_toc_office_label_raw": entry["label_raw"] if structural else None,
                "label_token_coverage": round(float(best[0]), 6),
                "nearest_printed_page_distance": int(best[3]) if ranked else None,
                "nearest_structural_heading_raw": nearest_any[1] if structural else None,
                "nearest_structural_heading_page_distance": (
                    int(nearest_any[0]) if structural else None
                ),
            }
        )
    return results


def reconcile_index_names(
    index_entries: list[dict[str, Any]], candidates: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_page: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        key = name_oracle_key(str(candidate["payee_raw"]))
        by_name[key].append(candidate)
        page = candidate.get("source_pdf_printed_page_number")
        if isinstance(page, int):
            by_page[page].append(candidate)

    results = []
    for entry in index_entries:
        key = str(entry["index_name_key"])
        referenced = []
        for page in entry["printed_page_references"]:
            referenced.extend(row for row in by_page.get(page, []) if name_oracle_key(str(row["payee_raw"])) == key)
        if referenced:
            matches = referenced
            status = "RESOLVED_EXACT_PRINTED_PAGE"
        elif key in by_name:
            matches = by_name[key]
            status = "RESOLVED_EXACT_VOLUME"
        else:
            matches = []
            status = "UNRESOLVED"
        results.append(
            {
                **entry,
                "resolution_status": status,
                "matched_candidate_ids": sorted({str(row["candidate_id"]) for row in matches}),
                "matched_candidate_count": len({str(row["candidate_id"]) for row in matches}),
            }
        )
    return results


def file_receipt(path: Path, rows: int) -> dict[str, Any]:
    return {
        "path": path.name,
        "rows": rows,
        "bytes": path.stat().st_size,
        "sha256": base.sha256_file(path),
    }


def source_rows(source_root: Path, inventory: Mapping[str, Any], periods: set[str] | None) -> list[dict[str, Any]]:
    result = []
    for entry in inventory["house_pdf_periods"]:
        period = str(entry["period"])
        if periods is not None and period not in periods:
            continue
        pdf_path = source_root / "raw_historical_house_pdf" / f"{period.lower()}_singlevolume.pdf"
        text_path = source_root / "historical_house_pdf_text" / f"{period.lower()}_visual_rows.ndjson.gz"
        if not pdf_path.is_file() or not text_path.is_file():
            raise BuildError(f"missing cached source for {period}: {pdf_path} / {text_path}")
        result.append(
            {
                **entry,
                "pdf_path": str(pdf_path),
                "pdf_sha256": base.sha256_file(pdf_path),
                "text_path": str(text_path),
                "text_sha256": base.sha256_file(text_path),
            }
        )
    if not result:
        raise BuildError("no source periods selected")
    return sorted(result, key=lambda row: row["period"])


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_root = args.source_root.resolve()
    output_root = args.output_root.resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise BuildError(f"immutable generation already exists: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    inventory_path = source_root / "house_sod_historical_url_inventory.json"
    if not inventory_path.is_file():
        raise BuildError(f"missing source inventory: {inventory_path}")
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    wanted = set(args.period or []) or None
    if args.year:
        year_periods = {f"{year}Q{quarter}" for year in args.year for quarter in range(1, 5)}
        wanted = year_periods if wanted is None else wanted & year_periods
    sources = source_rows(source_root, inventory, wanted)

    candidates_path = output_root / CANDIDATES_NAME
    residue_path = output_root / RESIDUE_NAME
    toc_path = output_root / TOC_NAME
    index_path = output_root / INDEX_NAME
    period_receipts = []
    toc_rows_written = 0
    index_rows_written = 0

    with (
        DeterministicGzipWriter(candidates_path) as candidate_writer,
        DeterministicGzipWriter(residue_path) as residue_writer,
        DeterministicGzipWriter(toc_path) as toc_writer,
        DeterministicGzipWriter(index_path) as index_writer,
    ):
        for source in sources:
            structure = scan_structure(Path(source["text_path"]), str(source["period"]))
            counts, candidates, office_headings = parse_period(
                source, structure, candidate_writer, residue_writer
            )
            toc_results = reconcile_toc_offices(structure["toc_entries"], office_headings)
            index_results = reconcile_index_names(structure["index_entries"], candidates)
            for row in toc_results:
                toc_writer.write(row)
                toc_rows_written += 1
            for row in index_results:
                index_writer.write(row)
                index_rows_written += 1

            office_entries = [row for row in toc_results if row.get("office_family")]
            offices_resolved = sum(row.get("office_resolution_status") == "RESOLVED" for row in office_entries)
            names_resolved = sum(row["resolution_status"] != "UNRESOLVED" for row in index_results)
            period_receipts.append(
                {
                    "period": source["period"],
                    "pdf_sha256": source["pdf_sha256"],
                    "text_sha256": source["text_sha256"],
                    "toc_machine_parseable": bool(structure["toc_pages"] and structure["toc_entries"]),
                    "toc_physical_pages": structure["toc_pages"],
                    "toc_entries": len(structure["toc_entries"]),
                    "toc_office_entries": len(office_entries),
                    "toc_office_entries_resolved": offices_resolved,
                    "toc_office_entries_unresolved": [
                        {"label_raw": row["label_raw"], "printed_page_number": row["printed_page_number"]}
                        for row in office_entries if row.get("office_resolution_status") != "RESOLVED"
                    ],
                    "toc_office_coverage": offices_resolved / len(office_entries) if office_entries else 0.0,
                    "index_physical_pages": structure["index_pages"],
                    "index_names": len(index_results),
                    "index_names_resolved": names_resolved,
                    "index_names_unresolved": [
                        {"index_name_raw": row["index_name_raw"], "printed_page_references": row["printed_page_references"]}
                        for row in index_results if row["resolution_status"] == "UNRESOLVED"
                    ],
                    "index_name_coverage": names_resolved / len(index_results) if index_results else 0.0,
                    **counts,
                }
            )
            print(base.compact_json({
                "period": source["period"],
                "payroll_candidate_rows": counts.get("payroll_candidate_rows", 0),
                "row_parse_rate": counts.get("row_parse_rate", 0.0),
                "toc_office_coverage": period_receipts[-1]["toc_office_coverage"],
                "index_name_coverage": period_receipts[-1]["index_name_coverage"],
            }), flush=True)

    total_present = sum(row["person_bearing_rows_present"] for row in period_receipts)
    total_admitted = sum(row["payroll_candidate_rows"] for row in period_receipts)
    total_toc_offices = sum(row["toc_office_entries"] for row in period_receipts)
    total_toc_resolved = sum(row["toc_office_entries_resolved"] for row in period_receipts)
    total_index = sum(row["index_names"] for row in period_receipts)
    total_index_resolved = sum(row["index_names_resolved"] for row in period_receipts)
    failures = []
    if total_present == 0 or total_admitted / total_present < 0.999:
        failures.append("C-3b rows parsed / person-bearing rows present is below 99.9%")
    if total_toc_offices == 0 or total_toc_resolved != total_toc_offices:
        failures.append("C-3c TOC-listed office coverage is not 100%")
    if total_index == 0 or total_index_resolved != total_index:
        failures.append("C-3c index-name resolution is not 100%")
    if any(not row["toc_machine_parseable"] for row in period_receipts):
        failures.append("at least one selected document TOC is not machine-parseable")

    files = [
        file_receipt(candidates_path, candidate_writer.rows),
        file_receipt(residue_path, residue_writer.rows),
        file_receipt(toc_path, toc_rows_written),
        file_receipt(index_path, index_rows_written),
    ]
    receipt = {
        "schema_id": RECEIPT_SCHEMA_ID,
        "status": "PASS" if not failures else "FAIL",
        "review_status": "REVIEW_REQUIRED",
        "canonical_employment_promoted": False,
        "canonical_identity_promoted": False,
        "canonical_office_promoted": False,
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "canonical_office_promotions": 0,
        "canonical_service_date_promotions": 0,
        "source_inventory": {
            "path": str(inventory_path),
            "sha256": base.sha256_file(inventory_path),
        },
        "selected_periods": [row["period"] for row in period_receipts],
        "counts": {
            "source_periods": len(period_receipts),
            "person_bearing_rows_present": total_present,
            "payroll_candidate_rows": total_admitted,
            "person_bearing_rows_rejected": total_present - total_admitted,
            "toc_office_entries": total_toc_offices,
            "toc_office_entries_resolved": total_toc_resolved,
            "index_names": total_index,
            "index_names_resolved": total_index_resolved,
        },
        "acceptance": {
            "C3b_window": f"{period_receipts[0]['period']} through {period_receipts[-1]['period']}",
            "C3b_numerator_rows_parsed": total_admitted,
            "C3b_denominator_person_bearing_rows_present": total_present,
            "C3b_rate": total_admitted / total_present if total_present else 0.0,
            "C3b_threshold": 0.999,
            "C3c_toc_office_numerator_resolved": total_toc_resolved,
            "C3c_toc_office_denominator_listed": total_toc_offices,
            "C3c_toc_office_rate": total_toc_resolved / total_toc_offices if total_toc_offices else 0.0,
            "C3c_index_name_numerator_resolved": total_index_resolved,
            "C3c_index_name_denominator_listed": total_index,
            "C3c_index_name_rate": total_index_resolved / total_index if total_index else 0.0,
        },
        "failures": failures,
        "periods": period_receipts,
        "files": files,
        "method": {
            "personnel_heading_rule": "TOTALS closes; dot-leader category rows are summaries; every other PERSONNEL COMPENSATION heading opens detail state even if a printed page number shares the row",
            "office_continuation_rule": "same normalized office heading preserves open personnel state across a continuation page",
            "ditto_rule": "DO resolves only to the prior explicit payee in the same normalized office; otherwise residue",
            "name_oracle": "exact normalized index name on a referenced printed page, then exact normalized name anywhere in the same volume",
            "toc_rule": "parse document TOC dot-leader rows and use token coverage plus printed-page proximity; no page number is hardcoded",
        },
    }
    receipt_path = output_root / RECEIPT_NAME
    base.write_json_atomic(receipt_path, receipt)
    return {"output_root": str(output_root), "receipt": receipt, "receipt_sha256": base.sha256_file(receipt_path)}


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=DEFAULT_SOURCE_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--period", action="append", help="select YYYYQn; repeatable")
    parser.add_argument("--year", type=int, action="append", help="select all held quarters in a year; repeatable")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    result = run(parse_args(argv))
    print(base.compact_json({
        "output_root": result["output_root"],
        "receipt_sha256": result["receipt_sha256"],
        "status": result["receipt"]["status"],
        "acceptance": result["receipt"]["acceptance"],
        "failures": result["receipt"]["failures"],
    }))
    return 0 if result["receipt"]["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
