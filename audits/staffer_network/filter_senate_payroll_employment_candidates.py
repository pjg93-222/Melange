#!/usr/bin/env python3
"""Fail-closed employment-scope filter for extracted Senate report rows.

Historical Senate PDF text can place an amount before either a personnel row or
an expense description.  This pass preserves every rejected row and its reason,
but exposes only person-like payees with role-like titles to identity matching.
It never adjudicates a person or promotes an employment fact.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Iterable

from build_official_senate_payroll_lane import (
    OLD_AMOUNT_START_RE,
    TITLE_STARTERS,
    TITLE_TERMINALS,
    parse_qualifiers,
    split_old_inline_title_payee,
)


FILTER_VERSION = "senate-payroll-employment-scope-filter-v1"
PERSON_PART_RE = re.compile(r"^[A-ZÀ-ÖØ-Þ][A-ZÀ-ÖØ-Þ .'’&()/-]*$", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Z]+")
NON_EMPLOYMENT_TITLE_PATTERNS = (
    "TRANSPORTATION",
    "PER DIEM",
    "MILEAGE",
    "AIRFARE",
    "LODGING",
    "CAR RENTAL",
    "TAXI",
    "OTHER CONTRACTUAL SERVICES",
    "SUPPLIES AND MATERIALS",
    "PRINTING AND REPRODUCTION",
)
ROUTE_TEXT_MARKERS = (" AND RETURN", " TO WASHINGTON", "WASHINGTON DC TO ")


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("rb") as probe:
        is_gzip = probe.read(2) == b"\x1f\x8b"
    opener = gzip.open if is_gzip else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    temporary = path.with_name(path.name + ".part")
    count = 0
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as stream:
            for row in rows:
                stream.write((compact_json(row) + "\n").encode("utf-8"))
                count += 1
    os.replace(temporary, path)
    return count


def artifact(path: Path) -> dict[str, Any]:
    return {"bytes": path.stat().st_size, "path": path.name, "sha256": sha256_file(path)}


def person_name_like(value: str) -> bool:
    if "," not in value:
        return False
    surname, given = (part.strip() for part in value.split(",", 1))
    return bool(surname and given and PERSON_PART_RE.fullmatch(surname) and PERSON_PART_RE.fullmatch(given))


def rejection_reason(row: dict[str, Any]) -> str | None:
    payee = (row.get("payee_name_raw") or "").strip()
    title = (row.get("title_candidate") or row.get("title_raw") or "").strip()
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
    period_start = row.get("report_period_start")
    period_end = row.get("report_period_end")
    intervals = row.get("date_intervals") or []
    if not period_start or not period_end or not intervals:
        return "MISSING_PERIOD_OR_INTERVAL"
    for interval in intervals:
        if not (period_start <= interval.get("start", "") <= interval.get("end", "") <= period_end):
            return "INVALID_OR_OUT_OF_PERIOD_INTERVAL"
    return None


def repair_historical_boundary(row: dict[str, Any]) -> bool:
    """Repair a title/surname join from immutable raw evidence, without adjudication."""
    if row.get("parse_status") != "HISTORICAL_REVERSE_LAYOUT_HEURISTIC_SPLIT":
        return False
    raw = row.get("evidence_quote") or ""
    match = OLD_AMOUNT_START_RE.match(raw)
    if match is None:
        return False
    payee, title, status = split_old_inline_title_payee(match.group("rest"))
    if not payee or not title or status == "UNSPLIT_REVIEW_REQUIRED":
        return False
    if payee == row.get("payee_name_raw") and title == row.get("title_raw"):
        return False
    row["pre_boundary_repair_payee_name_raw"] = row.get("payee_name_raw")
    row["pre_boundary_repair_title_raw"] = row.get("title_raw")
    row["payee_name_raw"] = payee
    row["title_raw"] = title
    qualifiers, intervals, title_candidate = parse_qualifiers(
        title, row["report_period_start"], row["report_period_end"]
    )
    row["qualifiers"] = qualifiers
    row["date_intervals"] = intervals
    row["title_candidate"] = title_candidate
    row["boundary_repair_status"] = "RAW_EVIDENCE_HEURISTIC_REPAIR_REVIEW_REQUIRED"
    return True


def run(source: Path, output_root: Path) -> dict[str, Any]:
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"Output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    reasons: Counter[str] = Counter()
    boundary_repair_count = 0
    seen_ids: set[str] = set()
    for row in read_gzip(source):
        candidate_id = row["candidate_id"]
        if candidate_id in seen_ids:
            raise RuntimeError(f"Duplicate candidate_id: {candidate_id}")
        seen_ids.add(candidate_id)
        if repair_historical_boundary(row):
            boundary_repair_count += 1
        reason = rejection_reason(row)
        if reason is None:
            accepted.append(row)
        else:
            reasons[reason] += 1
            rejected.append({
                "candidate_id": candidate_id,
                "evidence_quote": row.get("evidence_quote"),
                "office_raw": row.get("office_raw"),
                "parse_status": row.get("parse_status"),
                "payee_name_raw": row.get("payee_name_raw"),
                "rejection_reason": reason,
                "report_package_id": row.get("report_package_id"),
                "schema_id": "staffer-network-senate-payroll-employment-scope-rejection-v1",
                "title_raw": row.get("title_raw"),
            })
    accepted_path = output_root / "senate_payroll_employment_candidates_2011_2026.ndjson.gz"
    rejected_path = output_root / "senate_payroll_employment_scope_rejections_2011_2026.ndjson.gz"
    accepted_count = write_gzip(accepted_path, accepted)
    rejected_count = write_gzip(rejected_path, rejected)
    receipt = {
        "accepted_candidate_count": accepted_count,
        "accepted_candidates": artifact(accepted_path),
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "boundary_repair_count": boundary_repair_count,
        "complete_history_assertions": 0,
        "filter_version": FILTER_VERSION,
        "input_candidate_count": len(seen_ids),
        "rejected_candidate_count": rejected_count,
        "rejection_reason_counts": dict(sorted(reasons.items())),
        "rejections": artifact(rejected_path),
        "schema_id": "staffer-network-senate-payroll-employment-scope-receipt-v1",
        "source": artifact(source),
        "status": "PASS" if accepted_count + rejected_count == len(seen_ids) else "FAIL",
    }
    receipt_path = output_root / "senate_payroll_employment_scope_receipt.json"
    receipt_path.write_text(compact_json(receipt) + "\n", encoding="utf-8", newline="\n")
    print(compact_json(receipt))
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    receipt = run(args.source, args.output_root)
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
