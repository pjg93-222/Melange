#!/usr/bin/env python3
"""Replace two unavailable frozen HLS programs using Fable's deterministic rule."""

from __future__ import annotations

import hashlib
import json
import sqlite3

from freeze_fable_30 import RUN_ID, choose_unit
from inventory_and_freeze import DB, HERE, ROSTER, read_turns, transcript_metadata


SOURCE = HERE / "pilot_manifest_30_fable.json"
OUTPUT = HERE / "pilot_manifest_30_fable_media_ready.json"
REPLACEMENTS = {"F026": "610520", "F029": "668940"}
UNAVAILABLE = [
    {
        "pilot_id": "F026",
        "program_id": "545299",
        "expected_member": "Pete Stauber",
        "reason": "stored HLS URL and obvious host/suffix variants returned HTTP 403",
    },
    {
        "pilot_id": "F029",
        "program_id": "547435",
        "expected_member": "Al Green",
        "reason": "stored HLS URL and obvious host/suffix variants returned HTTP 403",
    },
]


def audit_map() -> dict[str, dict]:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return {
            str(row["program_id"]): dict(row)
            for row in connection.execute(
                """
                SELECT package,program_id,date,title,expected_member,status,
                       member_turns,member_words,detail
                FROM cspan_attribution_audit
                WHERE status='ok'
                """
            )
        }
    finally:
        connection.close()


def build_replacement(
    pilot_id: str,
    program_id: str,
    audit: dict,
    metadata: dict,
    by_program: dict,
    roster: dict,
) -> dict:
    row_audit = audit[program_id]
    member = row_audit["expected_member"]
    meta = metadata[program_id]
    unit = choose_unit(by_program[program_id], member)
    if unit is None:
        raise ValueError(f"{program_id}: no usable target unit")
    row = unit["row"]
    return {
        "pilot_id": pilot_id,
        "media_status": "REMOTE_HLS_BINDING_NOT_YET_DOWNLOADED",
        "planned_local_media": f"media_fable/{pilot_id}.mp4",
        "selection_hash": hashlib.sha256(
            f"{RUN_ID}\0{program_id}".encode("utf-8")
        ).hexdigest(),
        "program_id": program_id,
        "expected_member": member,
        "bioguide": roster[member].get("bioguide"),
        "current_chamber": roster[member].get("chamber"),
        "date": str(meta.get("date") or row_audit["date"] or ""),
        "title": str(meta.get("title") or row_audit["title"] or ""),
        "source_url": str(meta["url"]),
        "media_url": str(meta["media_url"]),
        "target_turn_seq": row["seq"],
        "target_turn_words": row["nwords"],
        "target_transcript_excerpt": str(row.get("text") or "")[:500],
        "label_provenance": (
            "social_media.db cspan_attribution_audit status=ok; "
            f"member_turns={row_audit['member_turns']}; "
            f"member_words={row_audit['member_words']}; "
            f"expected_member={member!r}; deterministic media-unavailable "
            "replacement selected by Fable; joined to cspan_out/turns.csv"
        ),
        **{key: value for key, value in unit.items() if key != "row"},
    }


def main() -> None:
    document = json.loads(SOURCE.read_text(encoding="utf-8"))
    metadata, failures = transcript_metadata()
    _, by_program = read_turns()
    roster = {
        row["member"]: row
        for row in json.loads(ROSTER.read_text(encoding="utf-8"))
    }
    audits = audit_map()
    items = []
    for item in document["items"]:
        program_id = REPLACEMENTS.get(item["pilot_id"])
        items.append(
            build_replacement(
                item["pilot_id"],
                program_id,
                audits,
                metadata,
                by_program,
                roster,
            )
            if program_id
            else item
        )
    if len(items) != 30:
        raise ValueError("media-ready manifest must contain 30 items")
    if len({row["program_id"] for row in items}) != 30:
        raise ValueError("media-ready manifest has duplicate programs")
    if len({row["expected_member"] for row in items}) != 30:
        raise ValueError("media-ready manifest has duplicate members")
    document.update(
        {
            "schema": "gemini-flash-interview-av-fable-media-ready-manifest-v1",
            "status": "FROZEN_WITH_DETERMINISTIC_MEDIA_REPLACEMENTS",
            "replacement_rule": (
                "When a frozen HLS binding is unavailable, preserve the pilot ID "
                "and take the next eligible SHA-ordered program whose member is "
                "not already selected."
            ),
            "unavailable_originals": UNAVAILABLE,
            "metadata_parse_failures": failures,
            "items": items,
        }
    )
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "items": len(items),
                "replacements": {
                    pilot_id: {
                        "program_id": program_id,
                        "expected_member": next(
                            row["expected_member"]
                            for row in items
                            if row["pilot_id"] == pilot_id
                        ),
                    }
                    for pilot_id, program_id in REPLACEMENTS.items()
                },
                "output": str(OUTPUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
