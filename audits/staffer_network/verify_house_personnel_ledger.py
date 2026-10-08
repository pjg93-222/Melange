#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent verifier for a House personnel ledger generation.

Recomputes, without importing the builder:
  * per-quarter admitted personnel row counts straight from the detail CSVs
    (own csv.DictReader path; DETAIL + PERSONNEL COMPENSATION) and, with ``--pdf-rows``,
    from the PDF-era candidate file the build was given (own reader, own block keying);
    the reconciliation histogram is then a FULL-era recount.  Without ``--pdf-rows`` the
    report says ``pdf_era_coverage: NOT_SUPPLIED`` and the histogram check fails rather
    than passing on a CSV-only subset while the PDF era goes unread
  * per (quarter, ORGANIZATION, PROGRAM) personnel sums from the CSVs against the
    CSVs' own PERSONNEL COMPENSATION TOTALS: subtotal rows, and against the
    member-quarter file's personnel_total / staff_count
  * observation-level facts: INV block on every row, amount == amount_raw,
    source_row_index unique per file, per-quarter counts
  * span conservation: every span observation id exists, no id in two spans,
    quarters consecutive, base totals and date bounds equal the member rows
  * twin byte identity (primary vs twin, all three payloads and the receipt)
  * anti-promotion tripwire: no canonical_* value other than false/null/NOT_ADJUDICATED
    anywhere in the outputs, receipt promotion counters all 0, no script assigns one
  * language scan over scripts, receipt and every output line
  * the HON. KEVIN KILEY 2025Q2 gold block re-derived from the observations file

Writes one verification report into --output-root (must not already exist) and
exits 0 on PASS, 1 on FAIL.  Read-only against every input.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterator

REPORT_NAME = "house_personnel_ledger_verification.json"
OBSERVATIONS_NAME = "house_personnel_observations.ndjson.gz"
SPANS_NAME = "house_person_office_spans.ndjson.gz"
MEMBER_QUARTERS_NAME = "house_member_quarters.ndjson.gz"
RECEIPT_NAME = "house_personnel_ledger_receipt.json"
PAYLOADS = (OBSERVATIONS_NAME, SPANS_NAME, MEMBER_QUARTERS_NAME, RECEIPT_NAME)

HERE = Path(__file__).resolve().parent
DEFAULT_CSV_ROOT = HERE / "house_sod_payroll_20260831" / "raw_detail_csv"
CSV_NAME_RE = re.compile(r"^(?P<year>\d{4})q(?P<q>[1-4])_sod_detail\.csv$", re.I)
HON_ORG_RE = re.compile(r"^(?:FISCAL YEAR\s+)?(?:19|20)\d{2}\s+HON[. ]", re.I)
CAUCUS_TOKEN_RE = re.compile(r"\b(CAUCUS|COALITION|COMMITTEE|TEAM)\b")
MEMBER_PROGRAM = "OFFICIAL EXPENSES OF MEMBERS"

# PDF era (--pdf-rows).  The candidate schema publishes no PROGRAM column and no subtotal
# row, so its blocks are keyed (quarter, office, "") and can only be NO_SUBTOTAL_ROW.
PDF_SCHEMA_IDS = {
    "staffer-network-house-sod-pdf-payroll-candidate-v1",
    "staffer-network-house-sod-pdf-payroll-candidate-v2",
}
PDF_SOURCE_FORM = "house_gov_single_volume_pdf"
PDF_PROGRAM_KEY = ""
ERA_PDF = "PDF"
ERA_CSV = "CSV"
SUBTOTAL_BASIS_PDF = "NO_SUBTOTAL_ROW_PDF_ERA"
NO_SUBTOTAL_ROW = "NO_SUBTOTAL_ROW"
# Column names that would have to exist for a PDF row to carry a program split or a subtotal.
PDF_FORBIDDEN_COLUMNS = {"PROGRAM", "PROGRAM CODE", "SORT SEQUENCE", "SORT SUBTOTAL DESCRIPTION"}

INV_EXPECTED = {
    "identity_status": "NAME_MATCH_ONLY",
    "review_status": "REVIEW_REQUIRED",
    "canonical_eligible": False,
    "canonical_employment_promoted": False,
    "canonical_identity_promoted": False,
    "canonical_office_promoted": False,
    "canonical_person_id": None,
    "canonical_office_id": None,
    "canonical_identity_decision": "NOT_ADJUDICATED",
}
PROMOTION_COUNTERS = (
    "canonical_employment_promotions", "canonical_identity_promotions",
    "canonical_office_promotions", "canonical_service_date_promotions",
)
# Terms are assembled from pieces so this file never contains them literally.
FORBIDDEN_TERMS = [
    "in" + "fluenc", "pre" + "dictor", "pre" + "dictive", "pre" + "dicts", "pre" + "diction",
    "revolv" + "ing door", "revolv" + "ing-door", "lever" + "age", "causal" + " effect",
]
PROMOTION_ASSIGNMENT_RE = re.compile(r"(canonical_[a-z_]*promot[a-z_]*)[\"']?\s*[:=]\s*True")
# A field whose NAME asserts the invariant (``canonical_promotions_zero: True``)
# is the opposite of a promotion; source text cannot tell the two apart by shape
# alone, so assertion-shaped names are excluded BY NAME.  The row-level
# invariant is untouched and still requires zero rows failing.
PROMOTION_ASSERTION_SUFFIXES = ("_zero", "_none", "_absent")

GOLD_KILEY_ROWS = [
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
]
GOLD_KILEY_TOTAL = "282,805.54"
GOLD_KILEY_ORG = "2025 HON. KEVIN KILEY"
GOLD_KILEY_QUARTER = "2025Q2"


class VerificationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_ndjson_gz(path: Path) -> Iterator[tuple[str, dict[str, Any]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line in stream:
            if line.strip():
                yield line, json.loads(line)


def to_decimal(text: str) -> Decimal | None:
    value = (text or "").replace("$", "").replace(",", "").strip()
    if value.startswith("(") and value.endswith(")"):
        value = "-" + value[1:-1]
    if value.startswith("–") or value.startswith("−"):
        value = "-" + value[1:]
    try:
        return Decimal(value) if value else None
    except InvalidOperation:
        return None


def quarter_index(quarter: str) -> int:
    return int(quarter[:4]) * 4 + int(quarter[-1]) - 1


# ---------------------------------------------------------------------------
# Independent CSV recount
# ---------------------------------------------------------------------------

def recount_csvs(csv_root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for path in sorted(csv_root.iterdir()):
        match = CSV_NAME_RE.match(path.name)
        if not match:
            continue
        quarter = f"{match.group('year')}Q{match.group('q')}"
        admitted = 0
        detail_sums: dict[tuple[str, str], Decimal] = defaultdict(lambda: Decimal(0))
        detail_rows: Counter[tuple[str, str]] = Counter()
        subtotals: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
        hon_orgs: set[str] = set()
        with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
            reader = csv.DictReader(stream, restkey="_extra", restval="")
            reader.fieldnames = [name.strip() for name in reader.fieldnames or []]
            for row in reader:
                org = (row.get("ORGANIZATION") or "").strip()
                if HON_ORG_RE.match(org):
                    hon_orgs.add(org)
                sequence = (row.get("SORT SEQUENCE") or "").strip().upper()
                ssd = (row.get("SORT SUBTOTAL DESCRIPTION") or "").strip().upper()
                if ssd != "PERSONNEL COMPENSATION":
                    continue
                program = (row.get("PROGRAM") or "").strip()
                if sequence == "DETAIL":
                    admitted += 1
                    amount = to_decimal(row.get("AMOUNT") or "")
                    detail_rows[(org, program)] += 1
                    if amount is not None:
                        detail_sums[(org, program)] += amount
                elif sequence == "SUBTOTAL" and (row.get("DESCRIPTION") or "").strip().upper() == "PERSONNEL COMPENSATION TOTALS:":
                    amount = to_decimal(row.get("AMOUNT") or "")
                    if amount is not None:
                        subtotals[(org, program)].append(amount)
        result[quarter] = {
            "file": path.name, "sha256": sha256_file(path), "admitted": admitted,
            "detail_sums": dict(detail_sums), "detail_rows": dict(detail_rows), "subtotals": dict(subtotals),
            "hon_orgs": hon_orgs,
        }
    return result


def recount_pdf_rows(path: Path) -> dict[str, Any]:
    """Independent ingest of the PDF-era rows the builder was handed.

    Same input file as the builder, this file's own reader and own block keying; the builder
    is never imported.  The candidate schema carries no PROGRAM column and no SORT SEQUENCE,
    so every block is keyed ``(quarter, employing_office_raw, "")`` and there is no published
    subtotal to reconcile against -- the block status can only be ``NO_SUBTOTAL_ROW``.  That
    absence is itself checked (``rows_with_forbidden_columns``) rather than assumed.
    """
    quarters: dict[str, Any] = {}
    schema_ids: Counter[str] = Counter()
    forbidden_columns: Counter[str] = Counter()
    rows_with_forbidden_columns = 0
    unparsed_amounts = 0
    total_rows = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            total_rows += 1
            schema_ids[str(row.get("schema_id"))] += 1
            hit = {key.upper() for key in row} & PDF_FORBIDDEN_COLUMNS
            if hit:
                rows_with_forbidden_columns += 1
                forbidden_columns.update(sorted(hit))
            quarter = str(row["period"])
            entry = quarters.get(quarter)
            if entry is None:
                entry = quarters[quarter] = {
                    "admitted": 0, "detail_sums": {}, "detail_rows": Counter(), "hon_orgs": set()}
            org = str(row["employing_office_raw"])
            if HON_ORG_RE.match(org):
                entry["hon_orgs"].add(org)
            entry["admitted"] += 1
            block = (org, PDF_PROGRAM_KEY)
            entry["detail_rows"][block] += 1
            amount = to_decimal(str(row.get("amount_raw") or ""))
            if amount is None:
                unparsed_amounts += 1
            else:
                entry["detail_sums"][block] = entry["detail_sums"].get(block, Decimal(0)) + amount
    # A block with only unparsed amounts still exists: give it a zero-valued sum entry so it
    # is counted in the histogram exactly as the builder's block_detail does.
    for entry in quarters.values():
        for block in entry["detail_rows"]:
            entry["detail_sums"].setdefault(block, Decimal(0))
    return {
        "quarters": quarters,
        "sha256": sha256_file(path),
        "rows": total_rows,
        "schema_ids": dict(sorted(schema_ids.items())),
        "rows_with_forbidden_columns": rows_with_forbidden_columns,
        "forbidden_columns_seen": dict(sorted(forbidden_columns.items())),
        "unparsed_amount_rows": unparsed_amounts,
    }


# ---------------------------------------------------------------------------
# Language and tripwire scans
# ---------------------------------------------------------------------------

def scan_text(text: str, label: str, hits: list[dict[str, Any]], limit: int = 50) -> None:
    lowered = text.lower()
    for term in FORBIDDEN_TERMS:
        start = 0
        while True:
            pos = lowered.find(term, start)
            if pos < 0:
                break
            if len(hits) < limit:
                hits.append({"where": label, "term": term, "context": text[max(0, pos - 40): pos + 40]})
            start = pos + len(term)


def inv_ok(row: dict[str, Any]) -> bool:
    for key, value in INV_EXPECTED.items():
        if key not in row or row[key] != value:
            return False
    for key, value in row.items():
        if key.startswith("canonical_") and value not in (False, None, "NOT_ADJUDICATED", 0):
            return False
    return True


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify(primary: Path, twin: Path | None, csv_root: Path, scripts: list[Path],
           pdf_rows: Path | None = None) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    language_hits: list[dict[str, Any]] = []
    tripwire: dict[str, Any] = {"rows_failing_inv": 0, "examples": [], "script_promotion_assignments": []}

    receipt_path = primary / RECEIPT_NAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    checks["receipt_status_pass"] = receipt.get("status") == "PASS"
    checks["receipt_promotion_counters_zero"] = all(receipt.get("invariants", {}).get(k) == 0 for k in PROMOTION_COUNTERS)
    checks["receipt_invariant_checks_all_true"] = bool(receipt.get("invariant_checks")) and all(receipt["invariant_checks"].values())
    checks["receipt_no_quarter_failed"] = receipt.get("quarters", {}).get("failed_to_parse") == []
    scan_text(receipt_path.read_text(encoding="utf-8"), RECEIPT_NAME, language_hits)

    # receipt input hashes vs the CSVs on disk
    recount = recount_csvs(csv_root)
    receipt_csvs = {entry["quarter"]: entry for entry in receipt.get("inputs", {}).get("csv_files", [])}
    checks["receipt_csv_set_equals_disk"] = set(receipt_csvs) == set(recount)
    checks["receipt_csv_sha256_match"] = all(
        receipt_csvs.get(q, {}).get("sha256") == recount[q]["sha256"] for q in recount
    )

    # ---- PDF era: independently ingested, or explicitly declared uncovered ----
    # The CSV recount alone cannot reproduce a full-era reconciliation histogram.  Narrowing
    # the comparison to the CSV quarters would report PASS while the entire PDF era went
    # unread, so the PDF era is either recounted here from the same file the builder was
    # given, or the report says NOT_SUPPLIED and the histogram check fails.
    receipt_pdf = receipt.get("inputs", {}).get("pdf_era", {}) or {}
    build_ingested_pdf = receipt_pdf.get("status") == "INGESTED"
    pdf_recount: dict[str, Any] = {}
    pdf_meta: dict[str, Any] = {}
    if pdf_rows is None:
        pdf_coverage = "NOT_SUPPLIED" if build_ingested_pdf else "NOT_APPLICABLE_CSV_ONLY_BUILD"
        checks["pdf_era_covered"] = not build_ingested_pdf
    else:
        pdf_meta = recount_pdf_rows(pdf_rows)
        pdf_recount = pdf_meta["quarters"]
        checks["pdf_rows_sha256_matches_receipt"] = pdf_meta["sha256"] == receipt_pdf.get("sha256")
        observed_pdf_schema_ids = list(pdf_meta["schema_ids"])
        checks["pdf_rows_schema_id_uniform"] = (
            len(observed_pdf_schema_ids) == 1 and observed_pdf_schema_ids[0] in PDF_SCHEMA_IDS
        )
        checks["pdf_rows_carry_no_program_or_subtotal_column"] = pdf_meta["rows_with_forbidden_columns"] == 0
        pdf_coverage = "VERIFIED" if build_ingested_pdf else "SUPPLIED_BUT_BUILD_WAS_CSV_ONLY"
        checks["pdf_era_covered"] = build_ingested_pdf
    details["pdf_era_coverage"] = pdf_coverage
    details["pdf_era"] = {
        "receipt_status": receipt_pdf.get("status"),
        "receipt_sha256": receipt_pdf.get("sha256"),
        "supplied_path": str(pdf_rows) if pdf_rows else None,
        "supplied_sha256": pdf_meta.get("sha256"),
        "rows_read": pdf_meta.get("rows"),
        "quarters_read": len(pdf_recount),
        "schema_ids": pdf_meta.get("schema_ids"),
        "rows_with_forbidden_columns": pdf_meta.get("rows_with_forbidden_columns"),
        "forbidden_columns_seen": pdf_meta.get("forbidden_columns_seen"),
        "unparsed_amount_rows": pdf_meta.get("unparsed_amount_rows"),
    }

    # ---- observations ----
    per_quarter_obs: Counter[str] = Counter()
    obs_sums: dict[tuple[str, str, str], Decimal] = defaultdict(lambda: Decimal(0))
    obs_rows: Counter[tuple[str, str, str]] = Counter()
    obs_persons: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    obs_index: dict[str, tuple[str, str | None, str, str, str | None, str | None, str | None]] = {}
    seen_row_index: set[tuple[str, int]] = set()
    duplicate_row_index = 0
    amount_mismatch = 0
    unkeyed_without_flag = 0
    keyed_rows = 0
    unkeyed_rows = 0
    cell_has_base: set[tuple[str, str, str]] = set()
    cell_rows: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    kiley: list[tuple[int, list[str]]] = []
    total_obs = 0
    for line, row in read_ndjson_gz(primary / OBSERVATIONS_NAME):
        total_obs += 1
        scan_text(line, OBSERVATIONS_NAME, language_hits)
        if not inv_ok(row):
            tripwire["rows_failing_inv"] += 1
            if len(tripwire["examples"]) < 5:
                tripwire["examples"].append({"file": OBSERVATIONS_NAME, "id": row.get("observation_id")})
        quarter = row["quarter"]
        per_quarter_obs[quarter] += 1
        key = (row["source_file"], row["source_row_index"])
        if key in seen_row_index:
            duplicate_row_index += 1
        seen_row_index.add(key)
        amount = to_decimal(row["amount_raw"])
        if (amount is None) != (row["amount"] is None) or (amount is not None and Decimal(row["amount"]) != amount):
            amount_mismatch += 1
        block = (quarter, row["office_raw"], row["program"] or "")
        obs_rows[block] += 1
        if amount is not None:
            obs_sums[block] += amount
        if row["person_key"] is None:
            unkeyed_rows += 1
            if not ({"PAYEE_EMPTY", "PAYEE_SINGLE_TOKEN"} & set(row["review_flags"])):
                unkeyed_without_flag += 1
        else:
            keyed_rows += 1
            obs_persons[block].add(row["person_key"])
            cell = (row["person_key"], row["office_key"], quarter)
            cell_rows[cell].append(row["observation_id"])
            if row["compensation_class"] == "BASE":
                cell_has_base.add(cell)
        obs_index[row["observation_id"]] = (
            quarter, row["person_key"], row["office_key"], row["compensation_class"], row["amount"],
            row["service_start"], row["service_end"],
        )
        if quarter == GOLD_KILEY_QUARTER and row["office_raw"] == GOLD_KILEY_ORG and row["program"] == MEMBER_PROGRAM:
            payee = row["payee_raw"]
            parts = payee.split(" ", 1)
            payee_gold = payee if len(parts) == 1 else parts[0] + ", " + parts[1]
            fmt = lambda iso: dt.date.fromisoformat(iso).strftime("%m/%d/%y") if iso else ""  # noqa: E731
            kiley.append((row["source_row_index"], [payee_gold, fmt(row["service_start"]), fmt(row["service_end"]), row["title_raw"], f"{Decimal(row['amount']):,.2f}"]))
    checks["observation_ids_unique"] = len(obs_index) == total_obs
    checks["source_row_index_unique_per_file"] = duplicate_row_index == 0
    checks["amount_equals_amount_raw"] = amount_mismatch == 0
    checks["unkeyed_rows_are_flagged"] = unkeyed_without_flag == 0
    # Expected admitted rows per quarter from the independent source recounts only -- never
    # from the receipt, which is the artefact under test.
    expected_admitted: Counter[str] = Counter()
    for quarter, rec in recount.items():
        expected_admitted[quarter] += rec["admitted"]
    for quarter, rec in pdf_recount.items():
        expected_admitted[quarter] += rec["admitted"]
    checks["per_quarter_counts_csv_equals_observations"] = all(
        expected_admitted[q] == per_quarter_obs.get(q, 0) for q in expected_admitted
    ) and all(q in expected_admitted for q in per_quarter_obs)
    if pdf_rows is not None:
        pdf_only_quarters = [q for q in pdf_recount if q not in recount]
        checks["per_quarter_counts_pdf_equals_observations"] = all(
            pdf_recount[q]["admitted"] == per_quarter_obs.get(q, 0) for q in pdf_only_quarters)
    checks["per_quarter_counts_receipt_equals_observations"] = all(
        receipt.get("per_quarter", {}).get(q, {}).get("admitted_rows") == per_quarter_obs.get(q, 0) for q in per_quarter_obs
    )
    details["per_quarter"] = {
        q: {"csv_recount": recount.get(q, {}).get("admitted", 0),
            "pdf_recount": pdf_recount.get(q, {}).get("admitted", 0),
            "observations": per_quarter_obs.get(q, 0),
            "receipt": receipt.get("per_quarter", {}).get(q, {}).get("admitted_rows")}
        for q in sorted(set(recount) | set(pdf_recount) | set(per_quarter_obs), key=quarter_index)
    }
    details["observations_total"] = total_obs

    # ---- block sums: observations vs CSV recount vs CSV subtotals ----
    block_mismatch_obs_vs_csv = 0
    reconciliation: Counter[str] = Counter()
    unreconciled_examples: list[dict[str, Any]] = []
    block_status: dict[tuple[str, str, str], tuple[str, Decimal, Decimal, int]] = {}
    for quarter, rec in recount.items():
        keys = set(rec["detail_sums"]) | set(rec["subtotals"])
        for org, program in keys:
            block = (quarter, org, program)
            csv_sum = rec["detail_sums"].get((org, program), Decimal(0))
            if (org, program) in rec["detail_sums"] and obs_sums.get(block, Decimal(0)) != csv_sum:
                block_mismatch_obs_vs_csv += 1
            subs = rec["subtotals"].get((org, program), [])
            sub_sum = sum(subs, Decimal(0))
            if (org, program) in rec["detail_sums"] and subs:
                status = "MULTI_SUBTOTAL_ROWS" if len(subs) > 1 else ("RECONCILED" if csv_sum == sub_sum else "MISMATCH")
            elif (org, program) in rec["detail_sums"]:
                status = "NO_SUBTOTAL_ROW"
            else:
                status = "SUBTOTAL_WITHOUT_DETAIL_ROWS"
            block_status[block] = (status, csv_sum, sub_sum, len(subs))
            reconciliation[status] += 1
            if status != "RECONCILED" and len(unreconciled_examples) < 40:
                unreconciled_examples.append({"quarter": quarter, "organization": org, "program": program, "status": status,
                                              "csv_detail_sum": format(csv_sum, "f"), "csv_subtotal_sum": format(sub_sum, "f")})
    checks["block_sums_observations_equal_csv"] = block_mismatch_obs_vs_csv == 0

    # ---- PDF-era blocks, from the independent PDF ingest ----
    block_mismatch_obs_vs_pdf = 0
    pdf_csv_block_collisions: list[str] = []
    pdf_blocks = 0
    for quarter, rec in pdf_recount.items():
        for (org, program) in rec["detail_sums"]:
            block = (quarter, org, program)
            pdf_sum = rec["detail_sums"][(org, program)]
            if obs_sums.get(block, Decimal(0)) != pdf_sum:
                block_mismatch_obs_vs_pdf += 1
            if block in block_status:
                # A CSV block with the same (quarter, office, program) key would make the two
                # eras indistinguishable in the histogram; say so instead of overwriting.
                if len(pdf_csv_block_collisions) < 20:
                    pdf_csv_block_collisions.append(f"{quarter}|{org}|{program}")
                continue
            pdf_blocks += 1
            block_status[block] = (NO_SUBTOTAL_ROW, pdf_sum, Decimal(0), 0)
            reconciliation[NO_SUBTOTAL_ROW] += 1
            if len(unreconciled_examples) < 40:
                unreconciled_examples.append({"quarter": quarter, "organization": org, "program": program,
                                              "status": NO_SUBTOTAL_ROW, "csv_detail_sum": format(pdf_sum, "f"),
                                              "csv_subtotal_sum": "0", "era": ERA_PDF})
    checks["block_sums_observations_equal_pdf"] = block_mismatch_obs_vs_pdf == 0
    checks["pdf_and_csv_blocks_disjoint"] = not pdf_csv_block_collisions

    receipt_recon = receipt.get("totals", {}).get("personnel_block_reconciliation", {})
    checks["reconciliation_histogram_equals_receipt"] = dict(sorted(reconciliation.items())) == dict(sorted(receipt_recon.items()))
    details["personnel_block_reconciliation"] = dict(sorted(reconciliation.items()))
    details["personnel_block_reconciliation_pdf_era_blocks"] = pdf_blocks
    details["pdf_and_csv_block_collisions"] = pdf_csv_block_collisions
    details["unreconciled_examples"] = unreconciled_examples

    # ---- member quarters ----
    # HON. offices seen by the independent recounts, both eras.
    hon_orgs_by_quarter: dict[str, set[str]] = defaultdict(set)
    for quarter, rec in recount.items():
        hon_orgs_by_quarter[quarter] |= rec["hon_orgs"]
    for quarter, rec in pdf_recount.items():
        hon_orgs_by_quarter[quarter] |= rec["hon_orgs"]
    mq_rows = 0
    mq_bad_total = mq_bad_staff = mq_bad_status = mq_not_hon = 0
    mq_pdf_unmarked = mq_era_mislabelled = 0
    mq_era: Counter[str] = Counter()
    mq_era_offices: dict[str, set[str]] = defaultdict(set)
    mq_orgs: dict[str, set[str]] = defaultdict(set)
    mq_marker_examples: list[dict[str, Any]] = []
    for line, row in read_ndjson_gz(primary / MEMBER_QUARTERS_NAME):
        mq_rows += 1
        scan_text(line, MEMBER_QUARTERS_NAME, language_hits)
        if not inv_ok(row):
            tripwire["rows_failing_inv"] += 1
        quarter, org = row["quarter"], row["office_raw"]
        era = row.get("era") or ERA_CSV
        mq_era[era] += 1
        mq_era_offices[era].add(row.get("office_key") or org)
        mq_orgs[quarter].add(org)
        if quarter in hon_orgs_by_quarter and org not in hon_orgs_by_quarter[quarter]:
            mq_not_hon += 1
        # The PDF schema has no program column, so a PDF-era row's personnel block is the
        # single programless block; a CSV-era row's is OFFICIAL EXPENSES OF MEMBERS.
        block = (quarter, org, PDF_PROGRAM_KEY if era == ERA_PDF else MEMBER_PROGRAM)
        expected_total = obs_sums.get(block, Decimal(0))
        if Decimal(row["personnel_total"]) != expected_total:
            mq_bad_total += 1
        if row["staff_count"] != len(obs_persons.get(block, set())):
            mq_bad_staff += 1
        expected_status = block_status.get(block, ("NO_PERSONNEL_BLOCK",))[0]
        if row["personnel_reconciliation"] != expected_status:
            mq_bad_status += 1
        if block in block_status:
            subtotal_rows = block_status[block][3]
            reported = row["personnel_subtotal_row_total"]
            if subtotal_rows == 0:
                # No published subtotal row: the field must be absent, never a fabricated 0.
                if reported is not None:
                    mq_bad_total += 1
            elif reported is None or Decimal(reported) != block_status[block][2]:
                mq_bad_total += 1
        # PDF-era rows must say so on the row, so no consumer reads one as a CSV-era
        # reconciled row.
        if era == ERA_PDF:
            marked = (row.get("program") is None
                      and row.get("subtotal_basis") == SUBTOTAL_BASIS_PDF
                      and row.get("source_form") == PDF_SOURCE_FORM
                      and row.get("personnel_subtotal_row_total") is None
                      and row.get("intern_row_count") is None
                      and row.get("intern_total") is None)
            if not marked:
                mq_pdf_unmarked += 1
                if len(mq_marker_examples) < 10:
                    mq_marker_examples.append({"quarter": quarter, "office_raw": org, "reason": "PDF_MARKERS_INCOMPLETE"})
        if quarter in pdf_recount and quarter not in recount and era != ERA_PDF:
            mq_era_mislabelled += 1
            if len(mq_marker_examples) < 10:
                mq_marker_examples.append({"quarter": quarter, "office_raw": org, "reason": "PDF_ONLY_QUARTER_NOT_LABELLED_PDF"})
    mq_missing_hon: list[str] = []
    for quarter, orgs in hon_orgs_by_quarter.items():
        for org in orgs - mq_orgs.get(quarter, set()):
            if not CAUCUS_TOKEN_RE.search(org.upper()):
                mq_missing_hon.append(f"{quarter}:{org}")
    checks["member_quarters_all_hon_offices"] = mq_not_hon == 0
    checks["member_quarters_cover_every_hon_org"] = not mq_missing_hon
    checks["member_quarters_totals_equal_observations"] = mq_bad_total == 0
    checks["member_quarters_staff_count_equals_distinct_person_keys"] = mq_bad_staff == 0
    checks["member_quarters_reconciliation_status_recomputed"] = mq_bad_status == 0
    checks["member_quarters_pdf_era_rows_marked"] = mq_pdf_unmarked == 0 and mq_era_mislabelled == 0
    checks["member_quarter_rows_by_era_equals_receipt"] = (
        dict(sorted(mq_era.items())) == dict(sorted((receipt.get("totals", {}).get("member_quarter_rows_by_era") or {}).items())))
    details["member_quarter_rows"] = mq_rows
    details["member_quarter_rows_by_era"] = dict(sorted(mq_era.items()))
    details["member_quarter_distinct_office_keys_by_era"] = {era: len(v) for era, v in sorted(mq_era_offices.items())}
    details["member_quarter_marker_problems"] = mq_marker_examples
    details["member_quarters_missing_hon_orgs"] = mq_missing_hon[:20]

    # ---- spans ----
    span_rows = 0
    span_obs_seen: set[str] = set()
    span_dup_obs = 0
    span_unknown_obs = 0
    span_bad = Counter()
    for line, row in read_ndjson_gz(primary / SPANS_NAME):
        span_rows += 1
        scan_text(line, SPANS_NAME, language_hits)
        if not inv_ok(row):
            tripwire["rows_failing_inv"] += 1
            if len(tripwire["examples"]) < 5:
                tripwire["examples"].append({"file": SPANS_NAME, "id": row.get("span_id")})
        quarters = row["quarters_observed"]
        indexes = [quarter_index(q) for q in quarters]
        if indexes != list(range(indexes[0], indexes[0] + len(indexes))):
            span_bad["quarters_not_consecutive"] += 1
        if row["first_report_quarter"] != quarters[0] or row["last_report_quarter"] != quarters[-1] or row["quarters_count"] != len(quarters):
            span_bad["quarter_fields_inconsistent"] += 1
        latest = receipt.get("quarters", {}).get("latest_quarter_on_disk")
        if (row["last_report_quarter"] == latest) != (row["status"] == "current"):
            span_bad["status_inconsistent"] += 1
        base_total = Decimal(0)
        starts: list[str] = []
        ends: list[str] = []
        obs_quarters: set[str] = set()
        for obs_id in row["observation_ids"]:
            if obs_id in span_obs_seen:
                span_dup_obs += 1
            span_obs_seen.add(obs_id)
            entry = obs_index.get(obs_id)
            if entry is None:
                span_unknown_obs += 1
                continue
            q, person_key, office_key, comp_class, amount, start, end = entry
            obs_quarters.add(q)
            if person_key != row["person_key"] or office_key != row["office_key"]:
                span_bad["observation_key_mismatch"] += 1
            if comp_class == "BASE":
                if amount is not None:
                    base_total += Decimal(amount)
                if start and end and end >= start:
                    starts.append(start)
                    ends.append(end)
        if base_total != Decimal(row["base_amount_total"]):
            span_bad["base_total_mismatch"] += 1
        if sorted(obs_quarters, key=quarter_index) != quarters:
            span_bad["quarters_vs_observations_mismatch"] += 1
        if starts and (min(starts) != row["service_start_min"] or max(ends) != row["service_end_max"]):
            span_bad["date_bounds_mismatch"] += 1
        if row["contiguous"] and starts:
            expected_days = (dt.date.fromisoformat(row["service_end_max"]) - dt.date.fromisoformat(row["service_start_min"])).days + 1
            if expected_days != row["service_days_union"]:
                span_bad["contiguous_days_mismatch"] += 1
    in_base_cells = sum(len(ids) for cell, ids in cell_rows.items() if cell in cell_has_base)
    orphan_rows = sum(len(ids) for cell, ids in cell_rows.items() if cell not in cell_has_base)
    checks["span_observation_ids_exist"] = span_unknown_obs == 0
    checks["span_observation_ids_disjoint"] = span_dup_obs == 0
    checks["span_conservation_base_cells_equal_span_rows"] = len(span_obs_seen) == in_base_cells
    checks["span_conservation_orphans_outside_spans"] = all(
        not any(obs_id in span_obs_seen for obs_id in ids) for cell, ids in cell_rows.items() if cell not in cell_has_base
    )
    checks["span_internal_consistency"] = not span_bad
    receipt_cons = receipt.get("observation_conservation", {})
    checks["conservation_equals_receipt"] = (
        receipt_cons.get("observations_in_spans") == len(span_obs_seen)
        and receipt_cons.get("observations_in_orphan_cells") == orphan_rows
        and receipt_cons.get("observations_with_person_key") == keyed_rows
        and receipt_cons.get("observations_without_person_key") == unkeyed_rows
    )
    details["spans"] = {"rows": span_rows, "observation_ids_in_spans": len(span_obs_seen), "orphan_rows": orphan_rows,
                        "keyed_rows": keyed_rows, "unkeyed_rows": unkeyed_rows, "problems": dict(span_bad)}

    # ---- receipt output hashes ----
    output_hash_ok = True
    for entry in receipt.get("outputs", []):
        path = primary / entry["path"]
        if not path.is_file() or sha256_file(path) != entry["sha256"] or path.stat().st_size != entry["bytes"]:
            output_hash_ok = False
    checks["receipt_output_hashes_match_files"] = output_hash_ok

    # ---- twin ----
    twin_report: dict[str, Any] = {"twin_root": str(twin) if twin else None, "files": {}, "all_byte_identical": None}
    if twin is not None:
        all_equal = True
        for name in PAYLOADS:
            p, t = primary / name, twin / name
            equal = p.is_file() and t.is_file() and p.read_bytes() == t.read_bytes()
            twin_report["files"][name] = {
                "primary_sha256": sha256_file(p) if p.is_file() else None,
                "twin_sha256": sha256_file(t) if t.is_file() else None,
                "byte_identical": equal,
            }
            all_equal = all_equal and equal
        twin_report["all_byte_identical"] = all_equal
        checks["twin_byte_identical"] = all_equal

    # ---- scripts: language + promotion assignment ----
    for script in scripts:
        text = script.read_text(encoding="utf-8")
        scan_text(text, script.name, language_hits)
        for match in PROMOTION_ASSIGNMENT_RE.finditer(text):
            if match.group(1).endswith(PROMOTION_ASSERTION_SUFFIXES):
                continue
            tripwire["script_promotion_assignments"].append({"script": script.name, "text": match.group(0)})
    checks["language_scan_clean"] = not language_hits
    checks["anti_promotion_tripwire"] = (
        tripwire["rows_failing_inv"] == 0 and not tripwire["script_promotion_assignments"]
        and checks["receipt_promotion_counters_zero"]
    )

    # ---- Kiley gold ----
    kiley_rows = [r for _, r in sorted(kiley)]
    subtotal = None
    if GOLD_KILEY_QUARTER in recount:
        subs = recount[GOLD_KILEY_QUARTER]["subtotals"].get((GOLD_KILEY_ORG, MEMBER_PROGRAM), [])
        subtotal = f"{subs[0]:,.2f}" if len(subs) == 1 else None
    detail_total = f"{sum((Decimal(r[4].replace(',', '')) for r in kiley_rows), Decimal(0)):,.2f}"
    kiley_report = {
        "status": "NOT_RUN_QUARTER_ABSENT" if GOLD_KILEY_QUARTER not in recount else (
            "PASS" if kiley_rows == GOLD_KILEY_ROWS and detail_total == GOLD_KILEY_TOTAL and subtotal == GOLD_KILEY_TOTAL else "FAIL"),
        "rows_reproduced": len(kiley_rows),
        "rows_matched_in_order": sum(1 for a, b in zip(kiley_rows, GOLD_KILEY_ROWS) if a == b),
        "personnel_total_from_observations": detail_total,
        "personnel_total_from_csv_subtotal": subtotal,
        "gold_total": GOLD_KILEY_TOTAL,
    }
    checks["kiley_gold_check"] = kiley_report["status"] in ("PASS", "NOT_RUN_QUARTER_ABSENT")
    checks["kiley_gold_check_matches_receipt"] = receipt.get("kiley_gold_check", {}).get("status") == kiley_report["status"]

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "schema_id": "staffer-network-house-personnel-ledger-verification-v1",
        "status": status,
        "primary_root": str(primary),
        "csv_root": str(csv_root),
        "pdf_rows": str(pdf_rows) if pdf_rows else None,
        "pdf_era_coverage": pdf_coverage,
        "checks": checks,
        "details": details,
        "twin": twin_report,
        "anti_promotion_tripwire": tripwire,
        "language_scan": {"terms_checked": len(FORBIDDEN_TERMS), "hits": language_hits, "scripts": [s.name for s in scripts]},
        "kiley_gold_check": kiley_report,
        "primary_files": {name: {"sha256": sha256_file(primary / name), "bytes": (primary / name).stat().st_size}
                          for name in PAYLOADS if (primary / name).is_file()},
        "receipt_status": receipt.get("status"),
        "receipt_run_id": receipt.get("run_id"),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--twin", type=Path, default=None)
    parser.add_argument("--csv-root", type=Path, default=DEFAULT_CSV_ROOT)
    parser.add_argument("--pdf-rows", type=Path, default=None,
                        help="the PDF-era candidate rows the build was given (.ndjson.gz); omit and the report "
                             "says pdf_era_coverage: NOT_SUPPLIED and the reconciliation histogram check fails "
                             "for a build that ingested them")
    parser.add_argument("--output-root", type=Path, required=True, help="verification directory (must not exist)")
    parser.add_argument("--script", type=Path, action="append", default=[], help="script to language-scan; repeatable")
    args = parser.parse_args(argv)
    args.primary = args.primary.resolve()
    args.csv_root = args.csv_root.resolve()
    args.output_root = args.output_root.resolve()
    if args.twin is not None:
        args.twin = args.twin.resolve()
    if args.pdf_rows is not None:
        args.pdf_rows = args.pdf_rows.resolve()
    args.script = [p.resolve() for p in args.script]
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.output_root.exists():
        print(f"VERIFY REFUSED: output directory already exists: {args.output_root}", file=sys.stderr)
        return 2
    try:
        report = verify(args.primary, args.twin, args.csv_root, args.script, args.pdf_rows)
    except (OSError, ValueError, KeyError, VerificationError) as exc:
        print(f"VERIFY FAILED: {exc!r}", file=sys.stderr)
        return 2
    args.output_root.mkdir(parents=True, exist_ok=False)
    path = args.output_root / REPORT_NAME
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(json.dumps(report, ensure_ascii=True, sort_keys=True, indent=1).encode("utf-8") + b"\n")
    os.replace(tmp, path)
    summary = {
        "status": report["status"],
        "failed_checks": sorted(k for k, v in report["checks"].items() if not v),
        "observations": report["details"]["observations_total"],
        "spans": report["details"]["spans"]["rows"],
        "member_quarter_rows": report["details"]["member_quarter_rows"],
        "member_quarter_rows_by_era": report["details"]["member_quarter_rows_by_era"],
        "pdf_era_coverage": report["pdf_era_coverage"],
        "reconciliation": report["details"]["personnel_block_reconciliation"],
        "twin_byte_identical": report["twin"]["all_byte_identical"],
        "kiley_gold_check": report["kiley_gold_check"]["status"],
        "language_hits": len(report["language_scan"]["hits"]),
        "report": str(path),
    }
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
