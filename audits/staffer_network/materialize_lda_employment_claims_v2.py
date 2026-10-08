#!/usr/bin/env python3
"""Materialize LDA covered-position claims with v2 identity and receipt gates.

The output is a source-native candidate layer. It preserves every nonblank
covered-position literal and every derived fragment, distinguishes response
presence from substantive position claims, and never promotes LDA disclosures
to canonical identity, canonical employment, or complete history.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable


YEAR_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
YEAR_RANGE_RE = re.compile(
    r"(?<!\d)((?:19|20)\d{2})\s*(?:-|–|—|to|through)\s*"
    r"((?:19|20)\d{2}|present|current)(?!\d)",
    re.I,
)
MONTH_RE = re.compile(
    r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\b",
    re.I,
)
SPLIT_RE = re.compile(r"\s*(?:;|\n|\r|\u2022|\|)\s*")
NO_POSITION_RE = re.compile(
    r"^(?:n/?a|none|not applicable|no covered positions?|no position|nil)\.?$",
    re.I,
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def claim_id(
    person_id: str,
    literal: str,
    fragment: str,
    fragment_ordinal: int,
) -> str:
    payload = "\x1f".join(
        ("v2", person_id, literal, str(fragment_ordinal), fragment)
    ).encode("utf-8")
    return "lda:employment-claim:v2:" + hashlib.sha256(payload).hexdigest()


def split_fragments(literal: str) -> list[str]:
    parts = [part.strip(" .") for part in SPLIT_RE.split(literal) if part.strip(" .")]
    return parts or [literal.strip()]


def parse_literal(person_id: str, literal: str) -> list[dict[str, Any]]:
    rows = []
    for ordinal, fragment in enumerate(split_fragments(literal)):
        ranges = [
            {
                "start_year": int(match.group(1)),
                "end_year": (
                    int(match.group(2)) if match.group(2).isdigit() else None
                ),
                "open_ended": not match.group(2).isdigit(),
                "raw": match.group(0),
            }
            for match in YEAR_RANGE_RE.finditer(fragment)
        ]
        years = sorted({int(value) for value in YEAR_RE.findall(fragment)})
        rows.append(
            {
                "schema_id": "staffer-network-lda-employment-claim-v2",
                "claim_id": claim_id(person_id, literal, fragment, ordinal),
                "lda_source_person_id": person_id,
                "fragment_ordinal": ordinal,
                "raw_covered_position_literal": literal,
                "claim_text": fragment,
                "year_tokens": years,
                "year_ranges": ranges,
                "month_token_present": bool(MONTH_RE.search(fragment)),
                "explicit_no_position": bool(NO_POSITION_RE.fullmatch(fragment)),
                "evidence_class": "LDA_SELF_REPORTED_COVERED_POSITION",
                "identity_status": "LDA_SOURCE_IDENTITY_ONLY",
                "canonical_identity_decision": "NOT_ADJUDICATED",
                "canonical_employment_fact": False,
                "complete_employment_history_asserted": False,
            }
        )
    return rows


def response_class(claims: list[dict[str, Any]]) -> str:
    if not claims:
        return "NO_NONBLANK_RESPONSE"
    substantive = any(not claim["explicit_no_position"] for claim in claims)
    explicit_no_position = any(claim["explicit_no_position"] for claim in claims)
    if substantive and explicit_no_position:
        return "MIXED_SUBSTANTIVE_AND_EXPLICIT_NO_POSITION"
    if substantive:
        return "SUBSTANTIVE_ONLY"
    return "EXPLICIT_NO_POSITION_ONLY"


def materialize_person(
    pair: tuple[int, dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rank, row = pair
    literals = list(
        dict.fromkeys(
            value.strip()
            for value in row.get("covered_position_values", [])
            if value.strip()
        )
    )
    claims = [
        claim
        for literal in literals
        for claim in parse_literal(row["lda_source_person_id"], literal)
    ]
    substantive_count = sum(not claim["explicit_no_position"] for claim in claims)
    explicit_no_position_count = sum(
        claim["explicit_no_position"] for claim in claims
    )
    person = {
        "schema_id": "staffer-network-lda-employment-person-v2",
        "queue_rank": rank,
        "candidate_id": row["candidate_id"],
        "lda_source_person_id": row["lda_source_person_id"],
        "display_name": row["display_name"],
        "filing_years": row.get("filing_years", []),
        "covered_position_literal_count": len(literals),
        "employment_claim_count": len(claims),
        "substantive_position_claim_count": substantive_count,
        "explicit_no_position_claim_count": explicit_no_position_count,
        "has_covered_position_response": bool(literals),
        "has_substantive_covered_position_claim": bool(substantive_count),
        "covered_position_response_class": response_class(claims),
        "has_explicit_year_token": any(claim["year_tokens"] for claim in claims),
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "complete_employment_history_asserted": False,
        "education_status": "NOT_REPORTED_IN_LDA_COVERED_POSITION_FIELD",
    }
    return person, claims


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in rows:
                stream.write(canonical_bytes(row))
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
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")

    queue_path = Path(args.queue).resolve()
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)
    with gzip.open(queue_path, "rt", encoding="utf-8") as stream:
        queue = [json.loads(line) for line in stream if line.strip()]

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        parsed = list(executor.map(materialize_person, enumerate(queue, start=1)))
    people = [item[0] for item in parsed]
    claims = [claim for item in parsed for claim in item[1]]

    if len({row["lda_source_person_id"] for row in people}) != len(people):
        raise RuntimeError("duplicate lda_source_person_id in people output")
    if len({row["claim_id"] for row in claims}) != len(claims):
        raise RuntimeError("duplicate claim_id in claims output")
    if any(row["canonical_identity_decision"] != "NOT_ADJUDICATED" for row in people):
        raise RuntimeError("canonical identity promotion is forbidden")
    if any(row["canonical_employment_fact"] for row in claims):
        raise RuntimeError("canonical employment promotion is forbidden")
    if any(row["complete_employment_history_asserted"] for row in people + claims):
        raise RuntimeError("complete history assertion is forbidden")

    people_path = output_root / "lda_employment_people.ndjson.gz"
    claims_path = output_root / "lda_employment_claims.ndjson.gz"
    people_count = write_gzip(people_path, people)
    claims_count = write_gzip(claims_path, claims)
    class_counts = dict(
        sorted(Counter(row["covered_position_response_class"] for row in people).items())
    )
    receipt = {
        "schema_id": "staffer-network-lda-employment-materialization-receipt-v2",
        "status": "PASS",
        "workers": args.workers,
        "source_queue": str(queue_path),
        "source_queue_bytes": queue_path.stat().st_size,
        "source_queue_sha256": sha256_file(queue_path),
        "queue_rows": len(queue),
        "people_rows": people_count,
        "people_with_covered_position_response": sum(
            row["has_covered_position_response"] for row in people
        ),
        "people_without_covered_position_response": sum(
            not row["has_covered_position_response"] for row in people
        ),
        "people_with_substantive_covered_position": sum(
            row["has_substantive_covered_position_claim"] for row in people
        ),
        "people_with_explicit_no_position_only": class_counts.get(
            "EXPLICIT_NO_POSITION_ONLY", 0
        ),
        "people_with_mixed_substantive_and_explicit_no_position": class_counts.get(
            "MIXED_SUBSTANTIVE_AND_EXPLICIT_NO_POSITION", 0
        ),
        "covered_position_response_class_counts": class_counts,
        "people_with_explicit_year_token": sum(
            row["has_explicit_year_token"] for row in people
        ),
        "employment_claim_rows": claims_count,
        "claim_flag_counts": dict(
            sorted(
                Counter(
                    "EXPLICIT_NO_POSITION"
                    if row["explicit_no_position"]
                    else "POSITION_CLAIM"
                    for row in claims
                ).items()
            )
        ),
        "duplicate_claim_ids": len(claims)
        - len({row["claim_id"] for row in claims}),
        "canonical_identity_promotions": 0,
        "canonical_employment_promotions": 0,
        "complete_history_assertions": 0,
        "files": [
            {
                "role": "people",
                "path": people_path.name,
                "bytes": people_path.stat().st_size,
                "sha256": sha256_file(people_path),
            },
            {
                "role": "claims",
                "path": claims_path.name,
                "bytes": claims_path.stat().st_size,
                "sha256": sha256_file(claims_path),
            },
        ],
    }
    receipt_path = output_root / "lda_employment_materialization_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
