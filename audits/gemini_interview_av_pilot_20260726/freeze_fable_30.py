#!/usr/bin/env python3
"""Freeze Fable's deterministic 30-program C-SPAN audiovisual sample."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from inventory_and_freeze import (
    DB,
    HERE,
    ROSTER,
    read_turns,
    transcript_metadata,
)


RUN_ID = "run-20260726T2104070055741Z-4c0563910a"
OUTPUT = HERE / "pilot_manifest_30_fable.json"


def audit_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT package,program_id,date,title,expected_member,status,
                       member_turns,member_words,detail
                FROM cspan_attribution_audit
                WHERE status='ok' AND member_turns>=5 AND member_words>=500
                """
            )
        ]
    finally:
        connection.close()
    return rows


def choose_unit(rows: list[dict], expected_member: str) -> dict | None:
    indexes = {id(row): index for index, row in enumerate(rows)}
    units = []
    for row in rows:
        if (
            str(row.get("is_member", "")).upper() != "TRUE"
            or row.get("resolved_member") != expected_member
        ):
            continue
        index = indexes[id(row)]
        next_offset = (
            rows[index + 1]["offset"]
            if index + 1 < len(rows)
            else row["offset"] + 90
        )
        target_duration = next_offset - row["offset"] - 0.2
        if row["nwords"] < 40 or target_duration < 18:
            continue
        start = max(0.0, row["offset"] - 12.0)
        target_end = min(float(next_offset) - 0.2, row["offset"] + 90.0)
        duration = min(105.0, target_end - start + 2.0)
        if duration < 25:
            continue
        units.append(
            {
                "row": row,
                "start_sec": round(start, 3),
                "duration_sec": round(duration, 3),
                "target_start_sec_in_clip": round(row["offset"] - start, 3),
                "target_end_sec_in_clip": round(target_end - start, 3),
                "target_turn_duration_sec": round(target_duration, 3),
            }
        )
    if not units:
        return None
    return max(
        units,
        key=lambda unit: (
            min(unit["target_turn_duration_sec"], 75),
            unit["row"]["nwords"],
            -unit["row"]["seq"],
        ),
    )


def main() -> None:
    roster = {
        row["member"]: row
        for row in json.loads(ROSTER.read_text(encoding="utf-8"))
    }
    metadata, failures = transcript_metadata()
    _, by_program = read_turns()
    eligible = []
    for audit in audit_rows():
        program_id = str(audit["program_id"])
        expected_member = audit["expected_member"]
        meta = metadata.get(program_id)
        rows = by_program.get(program_id)
        if (
            not meta
            or not rows
            or expected_member not in roster
            or "/washington-journal/" not in str(meta.get("url", ""))
            or not str(meta.get("media_url", "")).startswith(("http://", "https://"))
        ):
            continue
        unit = choose_unit(rows, expected_member)
        if not unit:
            continue
        row = unit["row"]
        selection_hash = hashlib.sha256(
            f"{RUN_ID}\0{program_id}".encode("utf-8")
        ).hexdigest()
        eligible.append(
            {
                "selection_hash": selection_hash,
                "program_id": program_id,
                "expected_member": expected_member,
                "bioguide": roster[expected_member].get("bioguide"),
                "current_chamber": roster[expected_member].get("chamber"),
                "date": str(meta.get("date") or audit["date"] or ""),
                "title": str(meta.get("title") or audit["title"] or ""),
                "source_url": str(meta["url"]),
                "media_url": str(meta["media_url"]),
                "target_turn_seq": row["seq"],
                "target_turn_words": row["nwords"],
                "target_transcript_excerpt": str(row.get("text") or "")[:500],
                "label_provenance": (
                    "social_media.db cspan_attribution_audit status=ok; "
                    f"member_turns={audit['member_turns']}; "
                    f"member_words={audit['member_words']}; expected_member="
                    f"{expected_member!r}; joined to cspan_out/turns.csv"
                ),
                **{key: value for key, value in unit.items() if key != "row"},
            }
        )

    selected = []
    used_members = set()
    for row in sorted(eligible, key=lambda item: item["selection_hash"]):
        if row["expected_member"] in used_members:
            continue
        selected.append(row)
        used_members.add(row["expected_member"])
        if len(selected) == 30:
            break
    if len(selected) != 30:
        raise ValueError(f"needed 30 unique eligible members, found {len(selected)}")
    items = [
        {
            "pilot_id": f"F{index:03d}",
            "media_status": "REMOTE_HLS_BINDING_NOT_YET_DOWNLOADED",
            "planned_local_media": f"media_fable/F{index:03d}.mp4",
            **row,
        }
        for index, row in enumerate(selected, start=1)
    ]
    document = {
        "schema": "gemini-flash-interview-av-fable-manifest-v1",
        "status": "FROZEN_LOCAL_CANDIDATE_NOT_DOWNLOADED_NOT_SCORED",
        "run_id": RUN_ID,
        "selection": (
            "cspan_attribution_audit status=ok, at least 5 accepted member turns "
            "and 500 accepted member words, stored Washington Journal HLS media "
            "binding, current roster member, usable 25-105 second target segment; "
            "SHA-256(run_id + NUL + program_id) order with one program per member."
        ),
        "eligible_programs_with_usable_unit": len(eligible),
        "metadata_parse_failures": failures,
        "model_contract": "Gemini Flash only; no Pro fallback.",
        "identity_contract": (
            "Private expected identity is allowed by the user. Gemini must confirm "
            "or flag mismatch; results measure manifest-consistent sorting and "
            "observable behavior, not open-set biometric identification."
        ),
        "visual_contract": (
            "Use real source video and report only observable gaze direction, "
            "gesture frequency/amplitude, head movement, posture shifts, facial "
            "animation, and visual turn-taking with timestamps and uncertainty."
        ),
        "production_consumers": 0,
        "items": items,
    }
    OUTPUT.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "eligible": len(eligible),
                "selected": len(items),
                "program_ids": [row["program_id"] for row in items],
                "output": str(OUTPUT),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
