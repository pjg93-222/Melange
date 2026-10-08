#!/usr/bin/env python3
"""Independent verification of a senate_committee_payroll generation.

This verifier does not import the builder and does not use its extraction
engine.  The builder resolves offices and columns from PyMuPDF glyph
coordinates; this script re-reads the same PDFs with ``pypdf``'s plain text
stream and re-derives the committee from line adjacency instead.  Agreement
between two different libraries and two different anchoring rules is the
evidence.

The strongest check is V3: each Volume II block prints its own payroll total,
so the document validates the parse against itself.

Checks
    V1  office resolved independently from the pypdf text header block
    V2  payee+title+amount present in the page's own text (whitespace-insensitive)
    V3  block amount reconciliation against the document's printed totals
    V4  volume scope -- every row sits on a B-2 page, never a Volume I page
    V5  cross-check of the mis-attribution the builder set out to repair
    V6  review pins and zero promotion counters on every row
    V7  candidate id uniqueness

Nothing here promotes a row, links a payee to a person, or writes to the
generation being verified.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import datetime as dt
import gzip
import hashlib
import json
import os
from pathlib import Path
import random
import re
import sys
from typing import Any

from pypdf import PdfReader

LANE_DIR = Path(__file__).resolve().parent
RECEIPT_SCHEMA_ID = "staffer-network-senate-committee-payroll-verification-v1"
APPROPRIATION_LABEL = "EXPENSES OF INQUIRIES AND INVESTIGATIONS"
VOLUME_TWO_LABEL_RE = re.compile(r"\bB\s*-\s*2\s*-\s*\d+\b")
VOLUME_ONE_HEADER_RE = re.compile(r"Funding Year\s+\d{4}")
SRES_LINE_RE = re.compile(
    r"S\s*\.?\s*RES\s*\.|\(\s*\d+\s*(?:ST|ND|RD|TH)\s*\)", re.IGNORECASE
)
FY_LINE_RE = re.compile(r"\bFY\s*\d{4}\b", re.IGNORECASE)
MONEY_IN_TEXT_RE = re.compile(r"-?\$?[\d,]+\.\d{2}")
PERSONNEL_COMP_RE = re.compile(
    r"(?:OTHER PERSONNEL COMPENSATION|PERSONNEL COMP\.[^0-9\n]*)\s*\$?(-?[\d,]+\.\d{2})",
    re.IGNORECASE,
)
NET_PAYROLL_TRAILING_RE = re.compile(
    r"(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})\s*Net Payroll Expenses", re.IGNORECASE
)
NET_PAYROLL_LEADING_RE = re.compile(
    r"Net Payroll Expenses\s+(-?[\d,]+\.\d{2})\s+(-?[\d,]+\.\d{2})", re.IGNORECASE
)
RATIO_FLOOR = 0.88
# Over-itemisation allowance, in dollars, not as a ratio.
#
# v1 capped the observed/printed ratio at 1.0005 on the premise that the printed
# PERSONNEL COMP. subtotal is an upper bound on the printed roster.  It is not.
# The Senate's own document over-itemises in two committees:
#
#   GPO-CDOC-115sdoc9 p2069-2071  ARMED SERVICES     S.RES. 62C (115TH)
#       roster (53 printed rows)                     3,079,784.68
#       "OTHER PERSONNEL COMPENSATION"                   5,307.95
#       "PERSONNEL COMP. FULL-TIME PERMANENT"        3,014,476.73
#       residue                                         60,000.00
#   GPO-CDOC-115sdoc9 p2127-2134  FOREIGN RELATIONS  S.RES. 62C (115TH)
#       roster (65 printed rows)                     3,177,135.97
#       "PERSONNEL COMP. FULL-TIME PERMANENT"        3,117,135.97
#       residue                                         60,000.00
#
# The same residue appears in ARMED SERVICES or FOREIGN RELATIONS -- and in no
# other committee -- in twelve blocks across five Congresses, in amounts
# consistent with one pro-rated $120,000/yr employee (60,000.00 for a whole
# period; 59,144.45, 56,861.64, 50,416.63, 11,166.70, 46.62 for partial ones).
# It is not attributable to the parse: an independent pypdf extraction
# reproduces 35,507 of the generation's 35,520 rows verbatim, the thirteen
# exceptions are pypdf line-assembly artefacts around wrapped titles, and the
# document's own arithmetic (NET PAYROLL = FTP + OTHER + ANNUITANTS + BENEFITS)
# balances in the same blocks.
#
# The residue is a whole number of salaries, so the allowance is denominated in
# dollars: two whole residues, the most seen in one report (GPO-CDOC-115sdoc9).
# A package that breaches it must be diagnosed, never accommodated by widening
# this number.
OVER_ITEMISATION_ALLOWANCE_USD = 120000.0


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".part")
    temporary.write_bytes((compact_json(value) + "\n").encode("utf-8"))
    os.replace(temporary, path)


def read_gzip(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def squash(value: str) -> str:
    return re.sub(r"\s+", "", value or "").upper()


def money(value: str) -> float:
    return float(value.replace("$", "").replace(",", "").strip())


def normalize_office(value: str) -> str:
    text = (value or "").upper()
    text = text.replace("&", " AND ")
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return " ".join(text.split())


def office_is_literal_page_text(page_text: str, office: str) -> str | None:
    """Confirm the builder's office is literally printed on that page.

    Independent of the builder's column geometry: it only asks whether the
    assigned string occurs in the page's own text, as one line, as two
    consecutive wrapped lines, or as the head of the abbreviated funding line.
    """
    target = squash(office)
    if not target:
        return None
    lines = [squash(line) for line in page_text.splitlines() if line.strip()]
    for line in lines:
        if line == target:
            return "EXACT_LINE"
    for first, second in zip(lines, lines[1:]):
        if first + second == target:
            return "WRAPPED_OVER_TWO_LINES"
    for line in lines:
        if line.startswith(target) and len(line) > len(target):
            return "HEAD_OF_ABBREVIATED_FUNDING_LINE"
    return None


def independent_office_from_text(page_text: str) -> tuple[str | None, str | None]:
    """Re-derive (committee, funding line) from the pypdf text stream alone.

    Rule: the funding line is the line carrying the ``S.RES.`` citation (or a
    committee fiscal-year line); the committee is the nearest non-empty line
    above it.  This is line adjacency, not column geometry -- a different
    anchoring rule from the builder's.
    """
    lines = [" ".join(line.split()) for line in page_text.splitlines()]
    for index, line in enumerate(lines):
        if not line:
            continue
        is_funding = SRES_LINE_RE.search(line) or (
            FY_LINE_RE.search(line) and "COMMITTEE" in line.upper()
        )
        if not is_funding:
            continue
        if line.upper().startswith("DETAILED AND SUMMARY"):
            continue
        for previous in range(index - 1, -1, -1):
            candidate = lines[previous]
            if not candidate or not any(ch.isalpha() for ch in candidate):
                continue
            upper = candidate.upper()
            if upper.startswith("DETAILED AND SUMMARY") or upper.startswith(APPROPRIATION_LABEL):
                break
            if MONEY_IN_TEXT_RE.fullmatch(candidate.replace(" ", "")):
                continue
            return candidate, line
        return None, line
    return None, None


def printed_block_totals(page_text: str) -> dict[str, float | None]:
    comp = PERSONNEL_COMP_RE.search(page_text)
    net = NET_PAYROLL_TRAILING_RE.search(page_text) or NET_PAYROLL_LEADING_RE.search(page_text)
    return {
        "personnel_compensation": money(comp.group(1)) if comp else None,
        "net_payroll_expenses": abs(money(net.group(1))) if net else None,
    }


def verify(args: argparse.Namespace) -> int:
    output_root: Path = args.output_root
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(f"Output root is nonempty (generations are immutable): {output_root}")
    generation: Path = args.generation
    candidates_path = generation / "senate_committee_payroll_candidates_2011_2026.ndjson.gz"
    rows = list(read_gzip(candidates_path))
    if not rows:
        raise RuntimeError("Generation has no accepted rows")

    by_package: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_package[row["report_package_id"]].append(row)

    rng = random.Random(args.seed)
    packages = sorted(by_package)
    if args.sample_packages and args.sample_packages < len(packages):
        packages = sorted(rng.sample(packages, args.sample_packages))

    findings: dict[str, Counter] = {name: Counter() for name in ("V1", "V2", "V3", "V4", "V9")}
    failures: list[dict[str, Any]] = []
    sampled_rows = 0
    sampled_pages = 0
    blocks_checked = 0
    blocks_exact = 0
    blocks_in_band = 0
    block_details: list[dict[str, Any]] = []
    office_pairs: Counter = Counter()

    for package_id in packages:
        pdf_path = args.raw_dir / f"{package_id}.pdf"
        if not pdf_path.exists():
            raise RuntimeError(f"Source PDF absent locally: {pdf_path}")
        reader = PdfReader(str(pdf_path))
        package_rows = by_package[package_id]
        pages_needed = sorted({row["page_number"] for row in package_rows})
        page_text: dict[int, str] = {}
        for number in pages_needed:
            page_text[number] = reader.pages[number - 1].extract_text() or ""

        # ---- blocks -------------------------------------------------------
        blocks: dict[tuple[int, str, str | None], list[dict[str, Any]]] = defaultdict(list)
        current: tuple[int, str, str | None] | None = None
        for row in sorted(package_rows, key=lambda r: (r["page_number"], r["row_ordinal_on_page"])):
            if row["office_attribution_basis"].startswith("PAGE_HEADER"):
                current = (
                    row["page_number"],
                    row["office_raw"],
                    row["senate_funding_resolution_raw"],
                )
            if current is None:
                failures.append({
                    "check": "V3",
                    "reason": "ROW_BEFORE_ANY_BLOCK_HEADER",
                    "package_id": package_id,
                    "page_number": row["page_number"],
                })
                continue
            blocks[current].append(row)

        # ---- V3: itemisation coverage against the document's own totals -----
        # The Senate does not partition the payroll roster by S.Res. block: a
        # committee's roster is printed once while the money is charged across
        # several funding resolutions.  The reconcilable unit is therefore the
        # committee's whole Volume II run inside one report, and the reference
        # number is the sum of every printed PERSONNEL COMP. / OTHER PERSONNEL
        # COMPENSATION line in that run.
        header_office_by_page = {
            row["page_number"]: row["office_raw"]
            for row in package_rows
            if row["office_attribution_basis"].startswith("PAGE_HEADER")
        }
        first_page = min(pages_needed)
        last_page = max(pages_needed)
        printed_by_office: Counter = Counter()
        printed_total = 0.0
        current_office: str | None = None
        for number in range(max(1, first_page - 12), min(len(reader.pages), last_page + 12) + 1):
            text = page_text.get(number)
            if text is None:
                text = reader.pages[number - 1].extract_text() or ""
                page_text[number] = text
            if not VOLUME_TWO_LABEL_RE.search(text) or "TABLE OF CONTENTS" in text.upper():
                continue
            if number in header_office_by_page:
                current_office = header_office_by_page[number]
            for match in PERSONNEL_COMP_RE.finditer(text):
                value = money(match.group(1))
                printed_total += value
                if current_office:
                    printed_by_office[current_office] += value
        observed_by_office: Counter = Counter()
        for row in package_rows:
            observed_by_office[row["office_raw"]] += money(row["amount_paid_raw"])
        for row in read_gzip(generation / "senate_committee_payroll_rejections_2011_2026.ndjson.gz"):
            if row.get("report_package_id") != package_id:
                continue
            match = re.search(r"(-?\$?[\d,]+\.\d{2})\s*$", row.get("evidence_quote") or "")
            if match:
                observed_by_office[row["office_raw"]] += money(match.group(1))
        observed_total = round(sum(observed_by_office.values()), 2)
        printed_total = round(printed_total, 2)
        ratio = (observed_total / printed_total) if printed_total else None
        blocks_checked += 1
        detail = {
            "observed_payroll_row_sum": observed_total,
            "package_id": package_id,
            "printed_personnel_compensation_sum": printed_total,
            "ratio_observed_over_printed": round(ratio, 6) if ratio is not None else None,
            "row_count": len(package_rows),
            "scope": "PACKAGE",
        }
        detail["observed_minus_printed"] = round(observed_total - printed_total, 2)
        if ratio is None:
            detail["verdict"] = "NO_PRINTED_TOTAL"
            findings["V3"]["NO_PRINTED_TOTAL"] += 1
        elif abs(observed_total - printed_total) <= 0.02:
            blocks_exact += 1
            blocks_in_band += 1
            detail["verdict"] = "EXACT_MATCH_TO_PRINTED_PERSONNEL_COMPENSATION"
            findings["V3"]["EXACT"] += 1
        elif (RATIO_FLOOR <= ratio
              and observed_total - printed_total <= OVER_ITEMISATION_ALLOWANCE_USD):
            blocks_in_band += 1
            detail["verdict"] = "WITHIN_ITEMISATION_BAND"
            findings["V3"]["IN_BAND"] += 1
        else:
            detail["verdict"] = "OUTSIDE_ITEMISATION_BAND"
            findings["V3"]["OUT_OF_BAND"] += 1
            failures.append({"check": "V3", **detail})
        block_details.append(detail)
        for office in sorted(set(observed_by_office) | set(printed_by_office)):
            block_details.append({
                "observed_payroll_row_sum": round(observed_by_office[office], 2),
                "office_raw": office,
                "package_id": package_id,
                "printed_personnel_compensation_sum": round(printed_by_office[office], 2),
                "scope": "COMMITTEE",
            })

        for key, members in blocks.items():
            header_page, office, _funding = key

            # ---- V1: independent office resolution -------------------------
            text = page_text.get(header_page, "")
            literal = office_is_literal_page_text(text, office)
            derived, funding_line = independent_office_from_text(text)
            if derived is not None and normalize_office(derived) == normalize_office(office):
                findings["V1"]["MATCH_BY_ADJACENCY_RULE"] += 1
            elif literal is not None:
                findings["V1"][f"MATCH_AS_{literal}"] += 1
            else:
                findings["V1"]["MISMATCH"] += 1
                failures.append({
                    "builder_office_raw": office,
                    "check": "V1",
                    "block_header_page": header_page,
                    "independently_derived": derived,
                    "independently_derived_funding_line": funding_line,
                    "package_id": package_id,
                })
            office_pairs[(office, derived or "")] += 1

        # ---- V2 / V4: row-level sample ------------------------------------
        sample = package_rows if args.sample_rows_per_package <= 0 else rng.sample(
            package_rows, min(args.sample_rows_per_package, len(package_rows))
        )
        for row in sample:
            sampled_rows += 1
            text = page_text.get(row["page_number"], "")
            squashed_page = squash(text)
            strict = squash(
                (row["payee_name_raw"] or "")
                + (row["title_raw"] or "")
                + (row["amount_paid_raw"] or "")
            )
            # A title that wraps is interleaved with the amount in the text
            # stream, so the strict triple is a stronger-than-necessary test.
            # The identity claim the corpus rests on is payee + amount.
            payee = squash(row["payee_name_raw"] or "")
            needle = squash((row["payee_name_raw"] or "") + (row["title_raw"] or "")[:24])
            amount = squash(row["amount_paid_raw"] or "")
            if strict and strict in squashed_page:
                findings["V2"]["PRESENT_STRICT_TRIPLE"] += 1
            elif needle and needle in squashed_page and amount in squashed_page:
                findings["V2"]["PRESENT_PAYEE_AND_AMOUNT"] += 1
            elif payee and payee in squashed_page and amount in squashed_page:
                # PyPDF's plain text stream can serialize a vertically wrapped
                # leading title fragment before the payee even though the
                # coordinate parser correctly assigns that fragment to the
                # row.  In that layout payee+title can never be contiguous.
                # The independent identity check documented above is payee +
                # amount, so test those two source literals separately and
                # retain the distinction in the receipt instead of recording
                # a false absence.
                findings["V2"]["PRESENT_PAYEE_AND_AMOUNT_SEPARATE"] += 1
            else:
                findings["V2"]["ABSENT"] += 1
                failures.append({
                    "check": "V2",
                    "candidate_id": row["candidate_id"],
                    "evidence_quote": row["evidence_quote"],
                    "package_id": package_id,
                    "page_number": row["page_number"],
                })
            if VOLUME_TWO_LABEL_RE.search(text) and not VOLUME_ONE_HEADER_RE.search(text):
                findings["V4"]["VOLUME_II_ONLY"] += 1
            else:
                findings["V4"]["SCOPE_VIOLATION"] += 1
                failures.append({
                    "check": "V4",
                    "candidate_id": row["candidate_id"],
                    "package_id": package_id,
                    "page_number": row["page_number"],
                })
        sampled_pages += len(pages_needed)

        # ---- V9: no row may be emitted more often than the page prints it ----
        # The itemisation band is denominated in dollars and so cannot by itself
        # catch a page or a row parsed twice.  This does: a payee+title+amount
        # triple may not appear in the generation more times than it occurs in
        # the page's own text.
        page_triples: dict[int, Counter] = defaultdict(Counter)
        for row in package_rows:
            page_triples[row["page_number"]][squash(
                (row["payee_name_raw"] or "")
                + (row["title_raw"] or "")
                + (row["amount_paid_raw"] or "")
            )] += 1
        for number, counts in page_triples.items():
            squashed_page = squash(page_text.get(number, ""))
            for triple, emitted in counts.items():
                if not triple:
                    continue
                printed = squashed_page.count(triple)
                if printed == 0:
                    # A title that wraps is interleaved with the amount in the
                    # text stream, so the triple is not contiguous there.  V2
                    # already carries those rows; they are not judgeable here.
                    findings["V9"]["UNJUDGEABLE_WRAPPED_TITLE"] += 1
                elif emitted > printed:
                    findings["V9"]["MORE_ROWS_THAN_THE_PAGE_PRINTS"] += 1
                    failures.append({
                        "check": "V9",
                        "package_id": package_id,
                        "page_number": number,
                        "emitted_rows": emitted,
                        "occurrences_in_page_text": printed,
                        "triple": triple[:120],
                    })
                else:
                    findings["V9"]["OK"] += 1

    # ---- V5: what the existing lane called these same rows -----------------
    misattribution: dict[str, Any] = {"status": "ARCHIVE_NOT_AVAILABLE"}
    if args.full_archive and args.full_archive.exists():
        recovered_pages: dict[tuple[str, int], str] = {}
        for row in rows:
            recovered_pages[(row["report_package_id"], row["page_number"])] = row["office_raw"]
        legacy_office_counts: Counter = Counter()
        legacy_rows_on_recovered_pages = 0
        legacy_agreeing = 0
        for row in read_gzip(args.full_archive):
            key = (row.get("report_package_id"), row.get("page_number"))
            if key not in recovered_pages:
                continue
            legacy_rows_on_recovered_pages += 1
            legacy_office_counts[row.get("office_raw")] += 1
            if normalize_office(row.get("office_raw") or "") == normalize_office(recovered_pages[key]):
                legacy_agreeing += 1
        misattribution = {
            "distinct_legacy_offices_on_recovered_pages": len(legacy_office_counts),
            "legacy_office_top_20": legacy_office_counts.most_common(20),
            "legacy_rows_agreeing_with_recovered_office": legacy_agreeing,
            "legacy_rows_on_recovered_pages": legacy_rows_on_recovered_pages,
            "recovered_pages": len(recovered_pages),
            "status": "COMPARED",
        }

    # ---- V6 / V7: invariants over every row --------------------------------
    pin_violations: list[dict[str, Any]] = []
    pins = {
        "canonical_employment_decision": "NOT_ADJUDICATED",
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "completeness_status": "PARTIAL",
        "date_promotion_eligible": False,
        "employment_claim_status": "UNVERIFIED_CANDIDATE",
        "identity_status": "UNVERIFIED_CANDIDATE",
        "promotion_gate": "BLOCKED_PENDING_IDENTITY_AND_ROW_REVIEW",
        "review_status": "REVIEW_REQUIRED",
    }
    interval_violations = 0
    for row in rows:
        for field, expected in pins.items():
            if row.get(field) != expected:
                pin_violations.append({"candidate_id": row["candidate_id"], "field": field})
        for interval in row.get("date_intervals") or []:
            if not (
                row["report_period_start"] <= interval["start"] <= interval["end"] <= row["report_period_end"]
            ):
                interval_violations += 1
    identifiers = [row["candidate_id"] for row in rows]
    duplicate_ids = len(identifiers) - len(set(identifiers))

    v3_denominator = blocks_checked
    report = {
        "checks": {
            "V1_office_resolved_independently": dict(findings["V1"]),
            "V2_row_text_present_in_page": dict(findings["V2"]),
            "V3_block_amount_reconciliation": dict(findings["V3"]),
            "V4_volume_scope": dict(findings["V4"]),
            "V5_misattribution_cross_check": misattribution,
            "V6_review_pin_violations": len(pin_violations),
            "V6_out_of_period_interval_violations": interval_violations,
            "V7_duplicate_candidate_ids": duplicate_ids,
            "V9_row_multiplicity_against_page_text": dict(findings["V9"]),
        },
        "itemisation_reconciliation": {
            "packages_checked": v3_denominator,
            "packages_exact_against_printed_personnel_compensation": blocks_exact,
            "packages_within_tolerance": blocks_in_band,
            "ratio_floor": RATIO_FLOOR,
            "over_itemisation_allowance_usd": OVER_ITEMISATION_ALLOWANCE_USD,
            "reference": "sum of printed PERSONNEL COMP. / OTHER PERSONNEL COMPENSATION lines",
            "expectation": (
                "The printed personnel-compensation subtotal is a control total for the "
                "printed roster in 222 of 388 committee blocks to the cent, but it is not "
                "a bound in either direction: COMMITTEE ON ETHICS under-itemises by exactly "
                "one top-of-scale salary in every report, and ARMED SERVICES / FOREIGN "
                "RELATIONS over-itemise by up to $60,000.00 per block.  The over-side "
                "allowance is therefore in dollars, not a ratio."
            ),
        },
        "failures": failures[:200],
        "failure_count": len(failures),
        "finished_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "generation": {
            "accepted_candidates_sha256": sha256_file(candidates_path),
            "path": str(generation),
            "row_count": len(rows),
        },
        "method": {
            "builder_engine": "PyMuPDF glyph coordinates (not used here)",
            "independent_office_rule": "nearest non-empty line above the S.RES/FY funding line",
            "verifier_engine": f"pypdf text stream",
            "verifier_imports_builder": False,
        },
        "pin_violation_sample": pin_violations[:50],
        "sampling": {
            "packages_verified": len(packages),
            "packages_total": len(by_package),
            "rows_sampled": sampled_rows,
            "rows_total": len(rows),
            "pages_read": sampled_pages,
            "seed": args.seed,
        },
        "schema_id": RECEIPT_SCHEMA_ID,
    }
    report["status"] = "PASS" if (
        not failures and not pin_violations and not duplicate_ids and not interval_violations
    ) else "FAIL"

    output_root.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output_root / "verification_report.json", report)
    write_json_atomic(
        output_root / "itemisation_reconciliation.json",
        {"reconciliation": block_details, "schema_id": RECEIPT_SCHEMA_ID + "-reconciliation"},
    )
    print(compact_json({
        "packages_checked": v3_denominator,
        "packages_exact": blocks_exact,
        "packages_within_tolerance": blocks_in_band,
        "failure_count": len(failures),
        "rows_sampled": sampled_rows,
        "status": report["status"],
    }))
    return 0 if report["status"] == "PASS" else 1


def parse_args() -> argparse.Namespace:
    default_source = LANE_DIR / "official_senate_payroll_2011_2026_full_8workers"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, default=default_source / "raw")
    parser.add_argument(
        "--full-archive",
        type=Path,
        default=default_source / "senate_payroll_candidates_2011_2026.ndjson.gz",
    )
    parser.add_argument("--sample-packages", type=int, default=0)
    # 0 == every accepted row.  v1 defaulted to a 60-row sample, which checked
    # 1,800 of 34,864 rows; the row-presence test is the check with real teeth,
    # so it now runs at full coverage by default.
    parser.add_argument("--sample-rows-per-package", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260903)
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(verify(parse_args()))
