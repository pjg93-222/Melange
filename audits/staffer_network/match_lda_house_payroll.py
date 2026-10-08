#!/usr/bin/env python3
"""Create unadjudicated LDA-to-House-payroll employment candidates by name.

The matcher is deliberately conservative and never promotes identity.  It
groups official payroll rows only after an exact first/last match with
middle-token compatibility and reports queue/payroll multiplicity.
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
    result = TOKEN_RE.findall(normalized.upper())
    while result and result[-1] in SUFFIXES:
        result.pop()
    return tuple(result)


def queue_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = tokens(value)
    if len(values) < 2:
        return None
    return values[0], values[-1], values[1:-1]


def payroll_name(value: str) -> tuple[str, str, tuple[str, ...]] | None:
    values = tokens(value)
    if len(values) < 2:
        return None
    # House SOD personnel names are stored as SURNAME GIVEN [MIDDLE/SUFFIX].
    surname, given = values[0], values[1]
    middle = tuple(item for item in values[2:] if item not in SUFFIXES)
    return given, surname, middle


def middle_compatible(left: tuple[str, ...], right: tuple[str, ...]) -> bool:
    if not left or not right:
        return True
    return left[0][0] == right[0][0]


def read_gzip(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
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
        default="audits/staffer_network/house_sod_payroll_20260831/house_sod_payroll_candidates.ndjson.gz",
    )
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    queue_path = Path(args.queue)
    payroll_path = Path(args.payroll)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    queue = list(read_gzip(queue_path))
    queue_by_key: defaultdict[tuple[str, str], list[tuple[dict[str, Any], tuple[str, ...]]]] = defaultdict(list)
    for row in queue:
        parsed = queue_name(row["display_name"])
        if parsed:
            given, surname, middle = parsed
            queue_by_key[(given, surname)].append((row, middle))

    # Aggregate exact-name-compatible payroll rows without asserting identity.
    groups: dict[tuple[str, str, str], dict[str, Any]] = {}
    payroll_rows = 0
    name_matched_payroll_rows = 0
    for payroll in read_gzip(payroll_path):
        payroll_rows += 1
        parsed = payroll_name(payroll.get("payee_raw") or "")
        if not parsed:
            continue
        given, surname, payroll_middle = parsed
        queue_candidates = [
            (row, queue_middle)
            for row, queue_middle in queue_by_key.get((given, surname), [])
            if middle_compatible(queue_middle, payroll_middle)
        ]
        if not queue_candidates:
            continue
        name_matched_payroll_rows += 1
        unique_queue_names = sorted({row["display_name"] for row, _ in queue_candidates})
        for row, queue_middle in queue_candidates:
            key = (
                row["lda_source_person_id"],
                payroll.get("employing_office_candidate") or "",
                payroll.get("title_description_raw") or "",
            )
            group = groups.setdefault(
                key,
                {
                    "person": row,
                    "payroll_name_key": [given, surname],
                    "payroll_middle": payroll_middle,
                    "queue_middle": queue_middle,
                    "queue_candidate_count_for_name": len(queue_candidates),
                    "queue_display_name_count_for_name": len(unique_queue_names),
                    "office": payroll.get("employing_office_candidate"),
                    "title": payroll.get("title_description_raw"),
                    "starts": [],
                    "ends": [],
                    "periods": set(),
                    "support_ids": [],
                    "source_urls": set(),
                },
            )
            if payroll.get("service_start_date_candidate_iso"):
                group["starts"].append(payroll["service_start_date_candidate_iso"])
            if payroll.get("service_end_date_candidate_iso"):
                group["ends"].append(payroll["service_end_date_candidate_iso"])
            group["periods"].add(payroll["period"])
            group["support_ids"].append(payroll["candidate_id"])
            group["source_urls"].add(payroll["source_url"])

    output_rows = []
    matched_people = set()
    for key in sorted(groups):
        group = groups[key]
        person = group["person"]
        matched_people.add(person["lda_source_person_id"])
        support_digest = hashlib.sha256("\n".join(group["support_ids"]).encode()).hexdigest()
        candidate_key = "\x1f".join(key) + "\x1f" + support_digest
        output_rows.append(
            {
                "schema_id": "staffer-network-lda-house-payroll-match-candidate-v1",
                "match_candidate_id": "lda-house-payroll-match:" + hashlib.sha256(candidate_key.encode()).hexdigest(),
                "lda_source_person_id": person["lda_source_person_id"],
                "display_name": person["display_name"],
                "employing_office_candidate": group["office"],
                "title_candidate": group["title"],
                "service_start_date_candidate": min(group["starts"]) if group["starts"] else None,
                "service_end_date_candidate": max(group["ends"]) if group["ends"] else None,
                "supported_quarters": sorted(group["periods"]),
                "payroll_row_support_count": len(group["support_ids"]),
                "payroll_support_digest": support_digest,
                "source_urls": sorted(group["source_urls"]),
                "name_match_method": "EXACT_FIRST_LAST_MIDDLE_COMPATIBLE",
                "queue_candidate_count_for_name": group["queue_candidate_count_for_name"],
                "queue_display_name_count_for_name": group["queue_display_name_count_for_name"],
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_employment_fact": False,
                "interval_continuity_asserted": False,
            }
        )

    output_path = output_root / "lda_house_payroll_match_candidates.ndjson.gz"
    output_count = write_gzip(output_path, output_rows)
    receipt = {
        "schema_id": "staffer-network-lda-house-payroll-match-receipt-v1",
        "status": "PASS",
        "queue_rows": len(queue),
        "payroll_rows": payroll_rows,
        "name_matched_payroll_rows": name_matched_payroll_rows,
        "matched_lda_source_people": len(matched_people),
        "unmatched_lda_source_people": len(queue) - len(matched_people),
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
            "House payee strings are surname-first and can contain compound-name edge cases.",
            "Aggregated minimum/maximum dates do not assert continuous employment.",
            "Same-name queue multiplicity is retained and explicitly counted.",
        ],
    }
    receipt_path = output_root / "lda_house_payroll_match_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
