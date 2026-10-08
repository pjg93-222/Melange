#!/usr/bin/env python3
"""Inventory stored interviews and freeze 30 true audiovisual candidates.

This script is local and read-only with respect to project source data. It
writes only inventory.json and pilot_manifest_30.json beside itself. Network
access and media downloads are deliberately out of scope.
"""

from __future__ import annotations

import csv
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TURNS = ROOT / "cspan_out" / "turns.csv"
TRANSCRIPTS = ROOT / "cspan_out" / "transcripts"
ROSTER = ROOT / "congestion.json"
DB = ROOT / "social_media.db"
INVENTORY = HERE / "inventory.json"
MANIFEST = HERE / "pilot_manifest_30.json"
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def integer(value: str | int | None) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def transcript_metadata() -> tuple[dict[str, dict], int]:
    documents: dict[str, dict] = {}
    failures = 0
    for path in sorted(TRANSCRIPTS.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            documents[str(document["id"])] = document
        except Exception:
            failures += 1
    return documents, failures


def read_turns() -> tuple[list[dict], dict[str, list[dict]]]:
    with TURNS.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    by_program: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        row["offset"] = integer(row.get("offset"))
        row["seq"] = integer(row.get("seq"))
        row["nwords"] = integer(row.get("nwords"))
        by_program[str(row["id"])].append(row)
    for values in by_program.values():
        values.sort(key=lambda row: (row["offset"], row["seq"]))
    return rows, by_program


def db_inventory() -> dict:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    try:
        total, members, packages = connection.execute(
            """
            SELECT count(*), count(DISTINCT member), count(DISTINCT package)
            FROM speeches WHERE source='INTERVIEW'
            """
        ).fetchone()
        distinct_program_labels = connection.execute(
            """
            SELECT count(DISTINCT chamber)
            FROM speeches WHERE source='INTERVIEW'
            """
        ).fetchone()[0]
        by_program = [
            {
                "program": row[0],
                "rows": row[1],
                "members": row[2],
                "packages": row[3],
            }
            for row in connection.execute(
                """
                SELECT chamber, count(*), count(DISTINCT member),
                       count(DISTINCT package)
                FROM speeches WHERE source='INTERVIEW'
                GROUP BY chamber ORDER BY count(*) DESC, chamber
                LIMIT 100
                """
            )
        ]
    finally:
        connection.close()
    return {
        "rows": total,
        "distinct_members": members,
        "distinct_packages": packages,
        "distinct_program_labels": distinct_program_labels,
        "top_100_programs": by_program,
    }


def local_video_inventory() -> list[dict]:
    results = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        relative = path.relative_to(ROOT)
        # The earlier audio-wrapper audit contains generated black-frame MP4s,
        # not source interview video.
        kind = (
            "derived_blank_frame_audio_wrapper"
            if relative.parts[:2] == ("audits", "gemini_av_pilot_20260726")
            else "other_local_video"
        )
        results.append(
            {
                "path": str(relative),
                "bytes": path.stat().st_size,
                "kind": kind,
            }
        )
    return results


def build_candidates(
    metadata: dict[str, dict],
    by_program: dict[str, list[dict]],
    roster: dict[str, dict],
) -> list[dict]:
    candidates = []
    for program_id, rows in by_program.items():
        meta = metadata.get(program_id)
        if not meta or not str(meta.get("media_url", "")).startswith(("http://", "https://")):
            continue

        member_rows = [
            row
            for row in rows
            if str(row.get("is_member", "")).upper() == "TRUE"
            and row.get("resolved_member") in roster
        ]
        if not member_rows:
            continue

        counts = Counter(row["resolved_member"] for row in member_rows)
        member, _ = counts.most_common(1)[0]
        member_rows = [row for row in member_rows if row["resolved_member"] == member]
        if len(member_rows) < 3 or sum(row["nwords"] for row in member_rows) < 250:
            continue

        title_tokens = set(normalize(str(meta.get("title", ""))).split())
        member_tokens = normalize(member).split()
        if not member_tokens or member_tokens[-1] not in title_tokens:
            continue

        indexes = {id(row): index for index, row in enumerate(rows)}
        units = []
        for row in member_rows:
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
            continue
        chosen = max(
            units,
            key=lambda unit: (
                min(unit["target_turn_duration_sec"], 75),
                unit["row"]["nwords"],
                -unit["row"]["seq"],
            ),
        )
        roster_row = roster[member]
        row = chosen["row"]
        candidates.append(
            {
                "program_id": program_id,
                "expected_member": member,
                "bioguide": roster_row.get("bioguide"),
                "current_chamber": roster_row.get("chamber"),
                "date": str(meta.get("date") or row.get("date") or ""),
                "title": str(meta.get("title") or row.get("title") or ""),
                "source_url": str(meta.get("url") or row.get("url") or ""),
                "media_url": str(meta["media_url"]),
                "target_turn_seq": row["seq"],
                "target_turn_words": row["nwords"],
                "target_transcript_excerpt": str(row.get("text") or "")[:500],
                "label_provenance": (
                    "cspan_out/turns.csv resolved_member plus member surname in "
                    "cspan_out/transcripts title"
                ),
                **{key: value for key, value in chosen.items() if key != "row"},
            }
        )
    return candidates


def freeze_thirty(candidates: list[dict]) -> list[dict]:
    selected = []
    used_members = set()
    by_chamber = defaultdict(list)
    for row in candidates:
        by_chamber[row.get("current_chamber")].append(row)
    for chamber in by_chamber:
        by_chamber[chamber].sort(
            key=lambda row: (
                row["date"],
                row["target_turn_words"],
                row["program_id"],
            ),
            reverse=True,
        )

    for chamber in ("House", "Senate"):
        for row in by_chamber.get(chamber, []):
            if row["expected_member"] in used_members:
                continue
            selected.append(row)
            used_members.add(row["expected_member"])
            if sum(item["current_chamber"] == chamber for item in selected) >= 15:
                break

    if len(selected) < 30:
        remainder = sorted(
            candidates,
            key=lambda row: (
                row["date"],
                row["target_turn_words"],
                row["program_id"],
            ),
            reverse=True,
        )
        for row in remainder:
            if row["expected_member"] in used_members:
                continue
            selected.append(row)
            used_members.add(row["expected_member"])
            if len(selected) == 30:
                break
    if len(selected) != 30:
        raise ValueError(f"needed 30 distinct-member interview programs, found {len(selected)}")

    selected.sort(key=lambda row: (row["current_chamber"], row["expected_member"]))
    return [
        {
            "pilot_id": f"I{index:03d}",
            "media_status": "REMOTE_HLS_BINDING_NOT_YET_DOWNLOADED",
            "planned_local_media": f"media/I{index:03d}.mp4",
            **row,
        }
        for index, row in enumerate(selected, start=1)
    ]


def main() -> None:
    roster_rows = json.loads(ROSTER.read_text(encoding="utf-8"))
    roster = {row["member"]: row for row in roster_rows}
    metadata, metadata_failures = transcript_metadata()
    turns, by_program = read_turns()
    member_turns = [
        row
        for row in turns
        if str(row.get("is_member", "")).upper() == "TRUE"
        and row.get("resolved_member")
    ]
    candidates = build_candidates(metadata, by_program, roster)
    selected = freeze_thirty(candidates)
    local_videos = local_video_inventory()
    inventory = {
        "schema": "gemini-interview-av-inventory-v1",
        "status": "LOCAL_INVENTORY_ONLY",
        "social_media_interviews": db_inventory(),
        "cspan_washington_journal": {
            "metadata_files": len(metadata),
            "metadata_parse_failures": metadata_failures,
            "media_url_bindings": sum(
                str(row.get("media_url", "")).startswith(("http://", "https://"))
                for row in metadata.values()
            ),
            "turn_rows": len(turns),
            "resolved_member_turns": len(member_turns),
            "resolved_member_programs": len({row["id"] for row in member_turns}),
            "resolved_members": len({row["resolved_member"] for row in member_turns}),
            "qualified_current_member_programs": len(candidates),
        },
        "local_video_files": {
            "count": len(local_videos),
            "source_interview_video_count": sum(
                row["kind"] == "other_local_video" for row in local_videos
            ),
            "files": local_videos,
        },
        "conclusion": (
            "The stored Washington Journal corpus contains transcript metadata "
            "and direct HLS audiovisual bindings. Source interview video binaries "
            "are not presently stored locally and must be clipped from those "
            "bindings before visual analysis."
        ),
    }
    manifest = {
        "schema": "gemini-flash-interview-av-pilot-manifest-v1",
        "status": "FROZEN_LOCAL_CANDIDATE_NOT_DOWNLOADED_NOT_SCORED",
        "selection": (
            "30 distinct current members; target 15 current House and 15 current "
            "Senate; newest qualified Washington Journal program per member; "
            "at least three resolved member turns and 250 member words; title "
            "surname confirmation; one 25-105 second host-context plus target-turn clip."
        ),
        "model_contract": "Gemini Flash only; no Pro fallback.",
        "identity_contract": (
            "Expected identity may be provided from the private manifest. Gemini "
            "must confirm or flag mismatch; manifest access is permitted by user."
        ),
        "visual_contract": (
            "Use real source video. Report only observable gaze direction, gesture "
            "frequency/amplitude, head movement, posture shifts, facial animation, "
            "and visual turn-taking with timestamps and not_observable options."
        ),
        "production_consumers": 0,
        "items": selected,
    }
    INVENTORY.write_text(json.dumps(inventory, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "inventory": str(INVENTORY),
                "manifest": str(MANIFEST),
                "metadata_files": len(metadata),
                "resolved_member_programs": len({row["id"] for row in member_turns}),
                "qualified_current_member_programs": len(candidates),
                "selected": len(selected),
                "selected_by_chamber": dict(
                    Counter(row["current_chamber"] for row in selected)
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
