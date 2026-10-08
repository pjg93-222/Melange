#!/usr/bin/env python3
"""Create provisional LDA-to-Senate-payroll candidates by conservative name match.

This discovery join never adjudicates identity or employment.  It preserves each
observed report interval instead of turning the first/last observation into a
continuous employment claim.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Iterable


TOKEN_RE = re.compile(r"[A-Z0-9]+")
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tokens(value: str) -> tuple[str, ...]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    values = TOKEN_RE.findall(normalized.upper())
    while values and values[-1] in SUFFIXES:
        values.pop()
    return tuple(values)


def queue_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def queue_name_candidates(value: str) -> list[tuple[str, str, tuple[str, ...]]]:
    """Return bounded surname variants without deciding which interpretation is true."""
    values = tokens(value)
    if len(values) < 2:
        return []
    candidates = {
        (values[0], "".join(values[-surname_length:]), values[1:-surname_length])
        for surname_length in range(1, min(3, len(values) - 1) + 1)
    }
    return sorted(candidates)


def senate_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    # Official reports normally print SURNAME, GIVEN [MIDDLE/SUFFIX].  Requiring
    # the comma avoids silently interpreting malformed OCR as a person name.
    if "," not in value:
        return None
    surname_raw, remainder = value.split(",", 1)
    surnames = tokens(surname_raw)
    given_tokens = tokens(remainder)
    if not surnames or not given_tokens:
        return None
    surname = "".join(surnames)
    given = given_tokens[0]
    middle = tuple(item for item in given_tokens[1:] if item not in SUFFIXES)
    return given, surname, middle


def middle_compatible(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not left or not right:
        return True
    return left[0][0] == right[0][0]


def read_records(path: Path) -> Iterable[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else path.open
    with opener(path, "rt", encoding="utf-8") if path.suffix == ".gz" else opener("rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gzip(path: Path, values: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for value in values:
                stream.write(canonical_bytes(value))
                count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        default=(
            "C:/Users/pgoff/AppData/Local/Melange/staffer_network/"
            "employment-lookup/generation-20260831T050000Z/"
            "employment_lookup_queue.ndjson.gz"
        ),
    )
    parser.add_argument(
        "--payroll",
        default="audits/staffer_network/official_senate_payroll_20260831/senate_payroll_candidates.ndjson",
    )
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    queue_path = Path(args.queue)
    payroll_path = Path(args.payroll)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    queue = list(read_records(queue_path))
    queue_by_key: defaultdict[tuple[str, str], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in queue:
        for name_variant in sorted(set(row.get("name_variants") or []) | {row["display_name"]}):
            for given, surname, middle in queue_name_candidates(name_variant):
                entry = queue_by_key[(given, surname)].setdefault(
                    row["lda_source_person_id"],
                    {"middles": set(), "name_variants": set(), "row": row},
                )
                entry["middles"].add(middle)
                entry["name_variants"].add(name_variant)

    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    payroll_rows = 0
    parsable_name_rows = 0
    name_matched_payroll_rows = 0
    for payroll in read_records(payroll_path):
        payroll_rows += 1
        parsed = senate_name(payroll.get("payee_name_raw") or "")
        if not parsed:
            continue
        parsable_name_rows += 1
        given, surname, payroll_middle = parsed
        queue_candidates = []
        for entry in queue_by_key.get((given, surname), {}).values():
            compatible_middles = sorted(
                middle for middle in entry["middles"] if middle_compatible(middle, payroll_middle)
            )
            if compatible_middles:
                queue_candidates.append((
                    entry["row"], compatible_middles, sorted(entry["name_variants"])
                ))
        queue_candidates.sort(key=lambda item: item[0]["lda_source_person_id"])
        if not queue_candidates:
            continue
        name_matched_payroll_rows += 1
        unique_queue_names = sorted({row["display_name"] for row, _, _ in queue_candidates})
        for row, queue_middles, name_variants in queue_candidates:
            key = (
                row["lda_source_person_id"],
                payroll.get("office_raw") or "",
                payroll.get("title_candidate") or payroll.get("title_raw") or "",
            )
            group = groups.setdefault(
                key,
                {
                    "person": row,
                    "payroll_name_key": [given, surname],
                    "payroll_middle": payroll_middle,
                    "queue_middles": set(),
                    "matched_queue_name_variants": set(),
                    "queue_candidate_count_for_name": len(queue_candidates),
                    "queue_display_name_count_for_name": len(unique_queue_names),
                    "office": key[1],
                    "title": key[2],
                    "intervals": set(),
                    "support_ids": set(),
                    "source_urls": set(),
                    "source_hashes": set(),
                    "parse_statuses": set(),
                },
            )
            group["queue_middles"].update(queue_middles)
            group["matched_queue_name_variants"].update(name_variants)
            for interval in payroll.get("date_intervals") or []:
                group["intervals"].add((interval.get("start"), interval.get("end"), interval.get("basis")))
            group["support_ids"].add(payroll["candidate_id"])
            group["source_urls"].add(payroll["source_pdf_url"])
            group["source_hashes"].add(payroll["source_pdf_sha256"])
            group["parse_statuses"].add(payroll.get("parse_status"))

    output_rows = []
    matched_people = set()
    for key in sorted(groups):
        group = groups[key]
        person = group["person"]
        matched_people.add(person["lda_source_person_id"])
        support_ids = sorted(group["support_ids"])
        support_digest = hashlib.sha256("\n".join(support_ids).encode()).hexdigest()
        candidate_key = "\x1f".join(key) + "\x1f" + support_digest
        output_rows.append(
            {
                "schema_id": "staffer-network-lda-senate-payroll-match-candidate-v1",
                "match_candidate_id": "lda-senate-payroll-match:" + hashlib.sha256(candidate_key.encode()).hexdigest(),
                "lda_source_person_id": person["lda_source_person_id"],
                "display_name": person["display_name"],
                "employing_office_candidate": group["office"],
                "title_candidate": group["title"],
                "observed_report_intervals": [
                    {"start": start, "end": end, "basis": basis}
                    for start, end, basis in sorted(group["intervals"])
                ],
                "payroll_row_support_count": len(support_ids),
                "payroll_support_digest": support_digest,
                "source_urls": sorted(group["source_urls"]),
                "source_pdf_hashes": sorted(group["source_hashes"]),
                "parse_statuses": sorted(item for item in group["parse_statuses"] if item),
                "name_match_method": "EXACT_GIVEN_SURNAME_VARIANT_MIDDLE_COMPATIBLE",
                "matched_queue_name_variants": sorted(group["matched_queue_name_variants"]),
                "queue_middle_variants": [list(value) for value in sorted(group["queue_middles"])],
                "queue_candidate_count_for_name": group["queue_candidate_count_for_name"],
                "queue_display_name_count_for_name": group["queue_display_name_count_for_name"],
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_employment_fact": False,
                "candidate_status": "REVIEW_REQUIRED",
                "employment_claim_status": "UNVERIFIED_CANDIDATE",
                "identity_status": "UNVERIFIED_CANDIDATE",
                "interval_continuity_asserted": False,
                "promotion_gate": "BLOCKED_PENDING_IDENTITY_AND_EMPLOYMENT_REVIEW",
            }
        )

    output_path = output_root / "lda_senate_payroll_match_candidates.ndjson.gz"
    output_count = write_gzip(output_path, output_rows)
    receipt = {
        "schema_id": "staffer-network-lda-senate-payroll-match-receipt-v1",
        "status": "PASS",
        "queue_rows": len(queue),
        "payroll_rows": payroll_rows,
        "parsable_payroll_name_rows": parsable_name_rows,
        "name_matched_payroll_rows": name_matched_payroll_rows,
        "matched_lda_source_people": len(matched_people),
        "unmatched_lda_source_people": len({row["lda_source_person_id"] for row in queue}) - len(matched_people),
        "match_candidate_rows": output_count,
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "source_queue_sha256": sha256_file(queue_path),
        "source_payroll_sha256": sha256_file(payroll_path),
        "output": {
            "path": output_path.name,
            "bytes": output_path.stat().st_size,
            "sha256": sha256_file(output_path),
        },
        "risk_notes": [
            "Exact name compatibility is discovery evidence, not identity adjudication.",
            "OCR errors and compound surnames can create false negatives or malformed candidates.",
            "Each report interval is only an observation window; continuity is never inferred.",
            "Same-name queue multiplicity is retained and explicitly counted.",
        ],
    }
    receipt_path = output_root / "lda_senate_payroll_match_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
