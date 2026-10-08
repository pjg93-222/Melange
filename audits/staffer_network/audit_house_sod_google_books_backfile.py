#!/usr/bin/env python3
"""Audit and attempt direct public acquisition of the 1996-2008 House SOD scans.

The discovery inputs are immutable.  Network access is restricted to the 23
Google Books candidate download URLs in the quarter-query discovery generation,
uses no authentication or cookies, and passes every request (including manual
redirect hops) through one shared pacer.  A completed response body is reused;
there are no retries, cache clearing, or alternate-endpoint attempts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any
import urllib.error
import urllib.parse
import urllib.request

import fitz


SCHEMA_ID = "staffer-network-house-sod-google-books-acquisition-audit-v1"
ID_RE = re.compile(r"^[A-Za-z0-9_-]{12}$")
TITLE_RE = re.compile(
    r"^Statement of Disbursements of the House: As Compiled by the Chief "
    r"Administrative Officer from "
    r"(?P<start_month>January|April|July|October) 1, (?P<year>\d{4}) to "
    r"(?P<end_month>March|June|September|December) (?:30|31), (?P=year), "
    r"Part (?P<part>\d+)$"
)
QUARTER_BY_START_MONTH = {"January": 1, "April": 2, "July": 3, "October": 4}
EXPECTED_END_MONTH = {1: "March", 2: "June", 3: "September", 4: "December"}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def expected_periods() -> list[str]:
    return [f"{year}Q{quarter}" for year in range(1996, 2009) for quarter in range(1, 5)]


def derive_period_and_part(title: str) -> tuple[str, int]:
    match = TITLE_RE.fullmatch(title)
    if match is None:
        raise ValueError(f"title does not carry an exact period and part: {title!r}")
    quarter = QUARTER_BY_START_MONTH[match.group("start_month")]
    if match.group("end_month") != EXPECTED_END_MONTH[quarter]:
        raise ValueError(f"title has inconsistent quarter boundary: {title!r}")
    return f"{match.group('year')}Q{quarter}", int(match.group("part"))


def validate_discovery(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    discovery = json.loads(path.read_text(encoding="utf-8"))
    errors: list[str] = []
    expected = expected_periods()
    if discovery.get("expected_periods") != expected:
        errors.append("expected_periods_not_exact_1996Q1_through_2008Q4")
    if len(expected) != 52 or len(set(expected)) != 52:
        errors.append("independent_expected_period_construction_failed")

    receipt_checks = []
    for receipt in discovery.get("search_receipts", []):
        source_path = path.parent / receipt["path"]
        exists = source_path.is_file()
        actual_bytes = source_path.stat().st_size if exists else None
        actual_sha256 = sha256_file(source_path) if exists else None
        check = {
            "actual_bytes": actual_bytes,
            "actual_sha256": actual_sha256,
            "declared_bytes": receipt.get("bytes"),
            "declared_sha256": receipt.get("sha256"),
            "path": receipt["path"],
            "verified": exists and actual_bytes == receipt.get("bytes") and actual_sha256 == receipt.get("sha256"),
        }
        if not check["verified"]:
            errors.append(f"search_receipt_mismatch:{receipt['path']}")
        receipt_checks.append(check)

    candidates = discovery.get("target_candidates", [])
    seen_ids: set[str] = set()
    candidate_checks = []
    derived_periods: set[str] = set()
    for candidate in candidates:
        book_id = candidate.get("book_id")
        try:
            title_period, title_part = derive_period_and_part(candidate.get("title", ""))
        except ValueError as error:
            errors.append(str(error))
            title_period, title_part = None, None
        id_valid = isinstance(book_id, str) and ID_RE.fullmatch(book_id) is not None
        unique_id = book_id not in seen_ids
        seen_ids.add(book_id)
        url_ids = {
            urllib.parse.parse_qs(urllib.parse.urlparse(candidate.get("download_url_template", "")).query).get("id", [None])[0],
            urllib.parse.parse_qs(urllib.parse.urlparse(candidate.get("metadata_url", "")).query).get("id", [None])[0],
        }
        verified = (
            id_valid
            and unique_id
            and url_ids == {book_id}
            and title_period == candidate.get("period")
            and title_part == candidate.get("part")
            and title_period in expected
        )
        if not verified:
            errors.append(f"candidate_metadata_mismatch:{book_id}")
        if title_period:
            derived_periods.add(title_period)
        candidate_checks.append(
            {
                "book_id": book_id,
                "candidate_sha256": hashlib.sha256(canonical_bytes(candidate)).hexdigest(),
                "part": candidate.get("part"),
                "period": candidate.get("period"),
                "title": candidate.get("title"),
                "verified": verified,
            }
        )

    covered = sorted(derived_periods)
    missing = [period for period in expected if period not in derived_periods]
    counts = discovery.get("counts", {})
    declared_consistent = (
        counts.get("expected_periods") == 52
        and counts.get("target_book_candidates") == len(candidates)
        and counts.get("target_periods_with_candidates") == len(covered)
        and counts.get("missing_periods") == len(missing)
        and discovery.get("missing_periods") == missing
    )
    if not declared_consistent:
        errors.append("declared_discovery_counts_or_missing_periods_inconsistent")
    verification = {
        "candidate_checks": candidate_checks,
        "counts": {
            "candidate_ids": len(seen_ids),
            "candidates": len(candidates),
            "covered_periods": len(covered),
            "expected_periods": len(expected),
            "missing_periods": len(missing),
            "search_receipts": len(receipt_checks),
        },
        "covered_periods": covered,
        "discovery_bytes": path.stat().st_size,
        "discovery_path": str(path),
        "discovery_sha256": sha256_file(path),
        "errors": errors,
        "missing_periods": missing,
        "search_receipt_checks": receipt_checks,
        "status": "PASS" if not errors else "FAIL",
    }
    return discovery, verification


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class SharedPacer:
    def __init__(self, minimum_interval: float) -> None:
        self.minimum_interval = minimum_interval
        self.last_request_start: float | None = None

    def wait(self) -> float:
        now = time.monotonic()
        if self.last_request_start is not None:
            delay = self.minimum_interval - (now - self.last_request_start)
            if delay > 0:
                time.sleep(delay)
        request_start = time.monotonic()
        interval = None if self.last_request_start is None else request_start - self.last_request_start
        self.last_request_start = request_start
        return interval if interval is not None else -1.0


def response_headers(headers: Any) -> dict[str, str | None]:
    return {
        "content_disposition": headers.get("Content-Disposition"),
        "content_length": headers.get("Content-Length"),
        "content_type": headers.get("Content-Type"),
        "location": headers.get("Location"),
    }


def direct_capture(
    candidate: dict[str, Any],
    output_dir: Path,
    pacer: SharedPacer,
    existing_capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    book_id = candidate["book_id"]
    body_path = output_dir / "raw_http" / f"{book_id}.response.bin"
    body_path.parent.mkdir(parents=True, exist_ok=True)
    request_url = candidate["download_url_template"]
    if body_path.is_file() and body_path.stat().st_size:
        payload = body_path.read_bytes()
        if existing_capture is not None:
            if existing_capture.get("body_bytes") != len(payload) or existing_capture.get("body_sha256") != hashlib.sha256(payload).hexdigest():
                raise RuntimeError(f"sealed response body drift for {book_id}")
            return {**existing_capture, **candidate}
        return {
            **candidate,
            "body_bytes": len(payload),
            "body_path": str(body_path.relative_to(output_dir)),
            "body_sha256": hashlib.sha256(payload).hexdigest(),
            "content_type": None,
            "download_state": "REUSED_COMPLETE_RESPONSE_BODY",
            "error": None,
            "final_url": request_url,
            "pdf_magic_verified": payload.startswith(b"%PDF-"),
            "redirect_chain": [],
            "request_count": 0,
            "response_status": None,
        }

    opener = urllib.request.build_opener(NoRedirect)
    redirect_chain = []
    current_url = request_url
    final_response: Any = None
    error_text = None
    request_count = 0
    minimum_observed_interval: float | None = None
    for _ in range(6):
        interval = pacer.wait()
        if interval >= 0:
            minimum_observed_interval = interval if minimum_observed_interval is None else min(minimum_observed_interval, interval)
        request_count += 1
        request = urllib.request.Request(
            current_url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; MelangeResearch/1.0)"},
        )
        try:
            response = opener.open(request, timeout=240)
        except urllib.error.HTTPError as error:
            response = error
        except Exception as error:
            error_text = f"{type(error).__name__}: {error}"
            break
        status = getattr(response, "status", response.getcode())
        headers = response_headers(response.headers)
        if status in {301, 302, 303, 307, 308} and headers["location"]:
            next_url = urllib.parse.urljoin(current_url, headers["location"])
            redirect_chain.append({"headers": headers, "status": status, "url": current_url})
            response.close()
            current_url = next_url
            continue
        final_response = response
        break

    if final_response is None:
        payload = b""
        status = None
        headers = {"content_disposition": None, "content_length": None, "content_type": None, "location": None}
    else:
        status = getattr(final_response, "status", final_response.getcode())
        headers = response_headers(final_response.headers)
        payload = final_response.read()
        final_response.close()
    temporary = body_path.with_name(body_path.name + ".part")
    temporary.write_bytes(payload)
    os.replace(temporary, body_path)
    return {
        **candidate,
        "body_bytes": len(payload),
        "body_path": str(body_path.relative_to(output_dir)),
        "body_sha256": hashlib.sha256(payload).hexdigest(),
        "content_disposition": headers["content_disposition"],
        "content_length_header": headers["content_length"],
        "content_type": headers["content_type"],
        "download_state": "DOWNLOADED_PUBLIC_UNAUTHENTICATED",
        "error": error_text,
        "final_url": current_url,
        "minimum_observed_inter_request_seconds": minimum_observed_interval,
        "pdf_magic_verified": payload.startswith(b"%PDF-"),
        "redirect_chain": redirect_chain,
        "request_count": request_count,
        "response_status": status,
    }


def inspect_pdf(path: Path, capture: dict[str, Any]) -> dict[str, Any]:
    result = {
        "document_opened": False,
        "extracted_text_characters": 0,
        "pages": None,
        "pages_with_personnel_compensation_text": 0,
        "pages_with_text": 0,
        "personnel_text_extractable": False,
        "front_matter_part_verified": False,
        "front_matter_period_verified": False,
        "front_matter_title_verified": False,
    }
    try:
        with fitz.open(path) as document:
            result["document_opened"] = True
            result["pages"] = len(document)
            front_text = " ".join((document[index].get_text("text") or "") for index in range(min(12, len(document))))
            normalized_front = " ".join(front_text.split()).upper()
            year = int(capture["period"][:4])
            quarter = int(capture["period"][-1])
            month_bounds = {
                1: ("JANUARY", "MARCH", 31),
                2: ("APRIL", "JUNE", 30),
                3: ("JULY", "SEPTEMBER", 30),
                4: ("OCTOBER", "DECEMBER", 31),
            }
            start_month, end_month, end_day = month_bounds[quarter]
            result["front_matter_text_sha256"] = hashlib.sha256(normalized_front.encode("utf-8")).hexdigest()
            result["front_matter_title_verified"] = "STATEMENT OF DISBURSEMENTS OF THE HOUSE" in normalized_front
            result["front_matter_period_verified"] = (
                f"{start_month} 1, {year} TO {end_month} {end_day}, {year}" in normalized_front
                or f"{start_month} 1, {year} THROUGH {end_month} {end_day}, {year}" in normalized_front
            )
            result["front_matter_part_verified"] = re.search(
                rf"\bPART\s+{int(capture['part'])}\s+OF\s+\d+\b", normalized_front
            ) is not None
            for page in document:
                text = page.get_text("text") or ""
                result["extracted_text_characters"] += len(text)
                result["pages_with_text"] += int(bool(text.strip()))
                result["pages_with_personnel_compensation_text"] += int(
                    re.search(r"PERSONNEL\s+COMPENSATION", text.upper()) is not None
                )
    except Exception as error:
        result["inspection_error"] = f"{type(error).__name__}: {error}"
    result["personnel_text_extractable"] = bool(result["pages_with_personnel_compensation_text"])
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generation1", type=Path, required=True)
    parser.add_argument("--generation2", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--minimum-request-interval", type=float, default=2.0)
    args = parser.parse_args()
    if args.minimum_request_interval < 2.0:
        parser.error("--minimum-request-interval must be at least 2 seconds")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    discovery1, verification1 = validate_discovery(args.generation1.resolve())
    discovery2, verification2 = validate_discovery(args.generation2.resolve())
    if verification1["status"] != "PASS" or verification2["status"] != "PASS":
        raise RuntimeError("discovery validation failed; network acquisition was not started")
    candidates1 = {row["book_id"]: row for row in discovery1["target_candidates"]}
    candidates2 = {row["book_id"]: row for row in discovery2["target_candidates"]}
    if len(candidates2) != 23:
        raise RuntimeError(f"authorized generation does not contain exactly 23 candidates: {len(candidates2)}")
    common_ids = sorted(set(candidates1) & set(candidates2))
    only1 = sorted(set(candidates1) - set(candidates2))
    only2 = sorted(set(candidates2) - set(candidates1))
    slot_map1 = {(row["period"], row["part"], row["title"]): row["book_id"] for row in candidates1.values()}
    slot_map2 = {(row["period"], row["part"], row["title"]): row["book_id"] for row in candidates2.values()}
    slot_differences = [
        {"generation1_book_id": slot_map1.get(slot), "generation2_book_id": slot_map2.get(slot), "part": slot[1], "period": slot[0], "title": slot[2]}
        for slot in sorted(set(slot_map1) | set(slot_map2))
        if slot_map1.get(slot) != slot_map2.get(slot)
    ]

    manifest_path = args.output_dir / "house_sod_google_books_acquisition_manifest.json"
    existing_by_id: dict[str, dict[str, Any]] = {}
    if manifest_path.is_file():
        previous = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing_by_id = {row["book_id"]: row for row in previous.get("captures", [])}
    pacer = SharedPacer(args.minimum_request_interval)
    captures = []
    ordered_candidates = sorted(candidates2.values(), key=lambda row: (row["period"], row["part"], row["book_id"]))
    for index, candidate in enumerate(ordered_candidates, start=1):
        capture = direct_capture(candidate, args.output_dir, pacer, existing_by_id.get(candidate["book_id"]))
        if capture["pdf_magic_verified"]:
            capture["pdf_inspection"] = inspect_pdf(args.output_dir / capture["body_path"], capture)
            capture["response_diagnostic"] = "DIRECT_PDF"
        else:
            capture["pdf_inspection"] = None
            body = (args.output_dir / capture["body_path"]).read_bytes()
            capture["response_diagnostic"] = (
                "GOOGLE_BOOKS_CAPTCHA_REQUIRED"
                if b"To continue with your download, please type the characters you see below" in body
                else "NON_PDF_RESPONSE"
            )
        captures.append(capture)
        print(json.dumps({"body_bytes": capture["body_bytes"], "book_id": capture["book_id"], "index": index, "pdf_magic_verified": capture["pdf_magic_verified"], "response_status": capture["response_status"]}, sort_keys=True), flush=True)

    pdf_captures = [row for row in captures if row["pdf_magic_verified"]]
    extractable = [row for row in pdf_captures if row["pdf_inspection"]["personnel_text_extractable"]]
    covered = verification2["covered_periods"]
    missing = verification2["missing_periods"]
    if len(covered) != 12 or len(missing) != 40:
        raise RuntimeError("independent 12-covered/40-missing conservation failed")
    blocker_reasons = []
    captcha_captures = [row for row in captures if row["response_diagnostic"] == "GOOGLE_BOOKS_CAPTCHA_REQUIRED"]
    if len(pdf_captures) != 23:
        blocker_reasons.append(f"DIRECT_RESPONSES_WITHOUT_PDF_MAGIC:{23 - len(pdf_captures)}")
    if captcha_captures:
        blocker_reasons.append(f"GOOGLE_BOOKS_CAPTCHA_REQUIRED:{len(captcha_captures)}")
    if len(extractable) != 23:
        blocker_reasons.append(f"CANDIDATE_PDFS_WITHOUT_EXTRACTABLE_PERSONNEL_TEXT:{23 - len(extractable)}")
    blocker_reasons.append("SOURCE_COVERAGE_MISSING_QUARTERS:40")
    status = "BLOCKED_ACQUISITION_INCOMPLETE"
    manifest = {
        "acquisition_policy": {
            "authentication_used": False,
            "cache_clearing_used": False,
            "candidate_scope": "GENERATION2_EXACT_23_ONLY",
            "canonical_employment_promotions": 0,
            "canonical_identity_promotions": 0,
            "direct_download_attempts_per_candidate": 1,
            "minimum_request_interval_seconds": args.minimum_request_interval,
            "redirect_hops_manually_paced": True,
            "request_concurrency": 1,
        },
        "blocker_diagnostic": {
            "reasons": blocker_reasons,
            "status": status,
        },
        "captures": captures,
        "counts": {
            "authorized_candidates": len(ordered_candidates),
            "covered_periods": len(covered),
            "captcha_html_responses": len(captcha_captures),
            "direct_pdf_responses": len(pdf_captures),
            "expected_periods": 52,
            "missing_periods": len(missing),
            "personnel_text_extractable_pdfs": len(extractable),
        },
        "covered_periods": covered,
        "discovery_comparison": {
            "common_candidate_ids": common_ids,
            "common_candidate_ids_count": len(common_ids),
            "generation1_only_candidate_ids": only1,
            "generation2_only_candidate_ids": only2,
            "slot_differences": slot_differences,
        },
        "discovery_verification": {
            "generation1": verification1,
            "generation2": verification2,
        },
        "missing_periods": missing,
        "implementation": {
            "script_path": Path(__file__).name,
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "schema_id": SCHEMA_ID,
        "status": status,
        "validation": {
            "all_candidate_metadata_verified": all(row["verified"] for row in verification2["candidate_checks"]),
            "canonical_promotions": 0,
            "exact_52_quarter_accounting": len(covered) + len(missing) == 52 and not (set(covered) & set(missing)),
            "generation_inputs_preserved": True,
            "target_candidate_count_exact": len(ordered_candidates) == 23,
            "zero_scope_expansion": True,
        },
    }
    manifest_path.write_bytes(canonical_bytes(manifest))
    print(json.dumps({"manifest": str(manifest_path), "manifest_sha256": sha256_file(manifest_path), "status": status, **manifest["counts"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
