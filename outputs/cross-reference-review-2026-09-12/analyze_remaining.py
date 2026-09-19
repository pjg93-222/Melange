"""Read-only profiling of the unresolved cross-reference queue."""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--run",
        default="20260913T054905-dc11ad68c0c8",
        help="Cross-reference run directory name or absolute path.",
    )
    parser.add_argument(
        "--output",
        default="remaining-profile-second-pass.json",
        help="Output filename beside this script.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_arg = Path(args.run)
    run = (
        run_arg
        if run_arg.is_absolute()
        else ROOT / "mentat" / "state" / "cross-reference" / run_arg
    )
    db_path = (run / "ledger.sqlite").resolve()
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    reasons_by_id: dict[str, set[str]] = defaultdict(set)
    queue_counts = Counter()
    for (payload_text,) in db.execute("SELECT payload_json FROM review_queue"):
        payload = json.loads(payload_text)
        queue_counts[payload["reason"]] += 1
        for source_id in payload["source_ids"]:
            reasons_by_id[str(source_id)].add(payload["reason"])

    rows: dict[str, dict] = {}
    for source_id, payload_text in db.execute(
        "SELECT source_id, payload_json FROM source_records ORDER BY id"
    ):
        source_id = str(source_id)
        if source_id in reasons_by_id:
            rows[source_id] = json.loads(payload_text)

    def text(value: object) -> str:
        return " ".join(str(value or "").upper().split())

    def gross(row: dict) -> int:
        return round(abs(float(row.get("contribution_receipt_amount") or 0)) * 100)

    def profile(reason: str, fields: tuple[str, ...], limit: int = 30) -> list[dict]:
        groups: dict[tuple[str, ...], list[int]] = defaultdict(lambda: [0, 0])
        for source_id, item_reasons in reasons_by_id.items():
            if reason not in item_reasons:
                continue
            row = rows[source_id]
            key = tuple(text(row.get(field)) for field in fields)
            groups[key][0] += 1
            groups[key][1] += gross(row)
        ranked = sorted(groups.items(), key=lambda item: (-item[1][0], -item[1][1], item[0]))
        return [
            {**dict(zip(fields, key)), "records": values[0], "gross_cents": values[1]}
            for key, values in ranked[:limit]
        ]

    profiles = {
        "queue_counts": dict(queue_counts),
        "unique_review_records": len(reasons_by_id),
        "loaded_review_records": len(rows),
        "company_attribution_by_entity": profile(
            "company_attribution_unresolved", ("entity_type",), 20
        ),
        "company_attribution_by_reason": profile(
            "company_attribution_unresolved",
            ("company_match_status", "company_match_reason", "phase"),
            40,
        ),
        "company_attribution_by_employer": profile(
            "company_attribution_unresolved",
            ("company", "contributor_employer", "entity_type"),
            1000,
        ),
        "company_attribution_by_name": profile(
            "company_attribution_unresolved",
            ("company", "contributor_name", "contributor_id", "entity_type"),
            1000,
        ),
        "receipt_role_by_text": profile(
            "receipt_role_unresolved",
            ("line_number", "receipt_type_full", "memo_text", "entity_type"),
            80,
        ),
        "treasury_by_name": profile(
            "treasury_ownership_unresolved",
            ("company", "contributor_name", "contributor_employer", "entity_type"),
            60,
        ),
        "memo_by_text": profile(
            "memo_parent_not_established",
            ("committee_id", "memo_text", "receipt_type_full", "line_number"),
            80,
        ),
        "transfer_by_text": profile(
            "original_source_of_transfer_unresolved",
            ("contributor_name", "receipt_type_full", "memo_text", "line_number"),
            80,
        ),
        "adjustment_by_text": profile(
            "signed_adjustment_not_linked_refund",
            ("contributor_name", "receipt_type_full", "memo_text", "line_number"),
            50,
        ),
    }
    output = Path(__file__).with_name(args.output)
    output.write_text(json.dumps(profiles, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "queue_rows": sum(queue_counts.values()),
        "unique_review_records": len(reasons_by_id),
        "loaded_review_records": len(rows),
    }, indent=2))


if __name__ == "__main__":
    main()
