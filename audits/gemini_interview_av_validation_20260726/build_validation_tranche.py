#!/usr/bin/env python3
"""Freeze a deterministic 150-case human-grounded interview validation tranche."""

from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TURNS = ROOT / "cspan_out" / "turns.csv"
TRANSCRIPTS = ROOT / "cspan_out" / "transcripts"
ROSTER = ROOT / "congestion.json"
DB = ROOT / "social_media.db"
OUTPUT = HERE / "validation_manifest_150.json"
SEED = "interview-av-human-validation-v1-20260726"
CORE_TARGETS = {"House": 108, "Senate": 12}
CHALLENGE_TARGETS = {"House": 26, "Senate": 4}
MAX_PER_MEMBER = 4

CALLER_RE = re.compile(
    r"\b(CALLER|CALL (?:HERE )?FROM|CALL FROM|"
    r"DEMOCRATS? LINE|REPUBLICANS? LINE|INDEPENDENTS? LINE)\b",
    flags=re.IGNORECASE,
)
HANDOFF_RE = re.compile(
    r"\b(FINAL THOUGHTS|CONGRESS(?:MAN|WOMAN),?\s+FINAL|"
    r"THANK YOU,?\s+(?:CONGRESSMAN|CONGRESSWOMAN|SENATOR)|"
    r"ONE MORE (?:QUICK )?CALL)\b",
    flags=re.IGNORECASE,
)


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def integer(value: object) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def read_turns() -> dict[str, list[dict]]:
    by_program: dict[str, list[dict]] = defaultdict(list)
    with TURNS.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            row["offset"] = integer(row.get("offset"))
            row["seq"] = integer(row.get("seq"))
            row["nwords"] = integer(row.get("nwords"))
            by_program[str(row["id"])].append(row)
    for rows in by_program.values():
        rows.sort(key=lambda row: (row["offset"], row["seq"]))
    return by_program


def transcript_metadata() -> tuple[dict[str, dict], int]:
    documents = {}
    failures = 0
    for path in sorted(TRANSCRIPTS.glob("*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
            documents[str(document["id"])] = document
        except Exception:
            failures += 1
    return documents, failures


def audit_rows() -> list[dict]:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        return [
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


def duration_bin(seconds: float) -> str:
    if seconds < 45:
        return "short_25_45"
    if seconds < 70:
        return "medium_45_70"
    return "long_70_90"


def risk_flags(row: dict, expected_member: str, target_duration: float) -> list[str]:
    text = str(row.get("text") or "")
    flags = []
    if CALLER_RE.search(text):
        flags.append("caller_marker")
    if HANDOFF_RE.search(text):
        flags.append("host_handoff_marker")
    surname = normalize(expected_member).split(" ")[-1]
    if surname and surname not in normalize(str(row.get("speaker") or "")):
        flags.append("speaker_label_weak")
    rate = row["nwords"] / max(target_duration, 0.001)
    if rate < 1.0 or rate > 4.2:
        flags.append("implausible_word_rate")
    if text.count(":") >= 2:
        flags.append("multiple_colon_boundaries")
    return flags


def choose_unit(
    rows: list[dict],
    expected_member: str,
    desired_risk_tier: str,
) -> dict | None:
    units = []
    for index, row in enumerate(rows):
        if (
            str(row.get("is_member", "")).upper() != "TRUE"
            or row.get("resolved_member") != expected_member
        ):
            continue
        # A final transcript turn has no independently observed endpoint.
        # Do not manufacture one from word count or a fixed duration: the
        # resulting clip can overrun the recording and cannot support precise
        # human event timing.
        if index + 1 >= len(rows):
            continue
        next_offset = (
            rows[index + 1]["offset"]
        )
        raw_duration = float(next_offset) - float(row["offset"]) - 0.2
        if row["nwords"] < 45 or raw_duration < 20:
            continue
        target_duration = min(raw_duration, 90.0)
        context_before = 6.0
        context_after = 3.0
        start = max(0.0, float(row["offset"]) - context_before)
        target_start = float(row["offset"]) - start
        target_end = target_start + target_duration
        clip_duration = target_end + context_after
        flags = risk_flags(row, expected_member, target_duration)
        tier = "challenge" if flags else "core"
        if tier != desired_risk_tier:
            continue
        units.append(
            {
                "row": row,
                "start_sec": round(start, 3),
                "duration_sec": round(clip_duration, 3),
                "target_start_sec_in_clip": round(target_start, 3),
                "target_end_sec_in_clip": round(target_end, 3),
                "target_turn_duration_sec": round(target_duration, 3),
                "duration_bin": duration_bin(target_duration),
                "label_risk_flags": flags,
                "label_risk_tier": tier,
            }
        )
    if not units:
        return None
    return max(
        units,
        key=lambda unit: (
            min(unit["target_turn_duration_sec"], 70),
            unit["row"]["nwords"],
            -unit["row"]["seq"],
        ),
    )


def build_candidates() -> tuple[list[dict], dict]:
    roster = {
        row["member"]: row
        for row in json.loads(ROSTER.read_text(encoding="utf-8"))
    }
    metadata, metadata_failures = transcript_metadata()
    turns = read_turns()
    candidates = []
    for audit in audit_rows():
        program_id = str(audit["program_id"])
        member = str(audit["expected_member"])
        meta = metadata.get(program_id)
        rows = turns.get(program_id)
        roster_row = roster.get(member)
        if (
            not meta
            or not rows
            or not roster_row
            or roster_row.get("chamber") not in {"House", "Senate"}
            or "/washington-journal/" not in str(meta.get("url") or "")
            or not str(meta.get("media_url") or "").startswith(
                ("http://", "https://")
            )
        ):
            continue
        for desired_tier in ("core", "challenge"):
            unit = choose_unit(rows, member, desired_tier)
            if not unit:
                continue
            row = unit["row"]
            year_match = re.match(
                r"(\d{4})", str(meta.get("date") or audit["date"])
            )
            if not year_match:
                continue
            year = int(year_match.group(1))
            if not 2020 <= year <= 2025:
                continue
            selection_hash = hashlib.sha256(
                f"{SEED}\0{program_id}\0{row['seq']}\0{desired_tier}".encode(
                    "utf-8"
                )
            ).hexdigest()
            candidates.append(
                {
                    "selection_hash": selection_hash,
                    "program_id": program_id,
                    "expected_member": member,
                    "bioguide": roster_row.get("bioguide"),
                    "current_chamber": roster_row["chamber"],
                    "year": year,
                    "date": str(meta.get("date") or audit["date"] or ""),
                    "title": str(meta.get("title") or audit["title"] or ""),
                    "source_url": str(meta["url"]),
                    "media_url": str(meta["media_url"]),
                    "target_turn_seq": int(row["seq"]),
                    "target_turn_words": int(row["nwords"]),
                    "target_transcript": str(row.get("text") or ""),
                    "source_speaker_label": str(row.get("speaker") or ""),
                    "label_provenance": (
                        "social_media.db cspan_attribution_audit status=ok; "
                        f"member_turns={audit['member_turns']}; "
                        f"member_words={audit['member_words']}; joined to "
                        "cspan_out/turns.csv"
                    ),
                    **{
                        key: value
                        for key, value in unit.items()
                        if key != "row"
                    },
                }
            )
    metadata_summary = {
        "metadata_files": len(metadata),
        "metadata_parse_failures": metadata_failures,
        "eligible_candidates": len(candidates),
        "eligible_programs": len({row["program_id"] for row in candidates}),
        "candidate_by_chamber": dict(
            Counter(row["current_chamber"] for row in candidates)
        ),
        "candidate_by_year": dict(Counter(row["year"] for row in candidates)),
        "candidate_by_risk": dict(
            Counter(row["label_risk_tier"] for row in candidates)
        ),
    }
    return candidates, metadata_summary


def round_robin(
    candidates: list[dict],
    targets: dict[str, int],
    used_programs: set[str],
    member_counts: Counter,
) -> list[dict]:
    selected = []
    for chamber, target in targets.items():
        pool = [
            row
            for row in candidates
            if row["current_chamber"] == chamber
            and row["program_id"] not in used_programs
        ]
        buckets: dict[tuple[int, str], list[dict]] = defaultdict(list)
        for row in pool:
            buckets[(row["year"], row["duration_bin"])].append(row)
        for rows in buckets.values():
            rows.sort(key=lambda row: row["selection_hash"])
        keys = sorted(buckets)
        cursor = 0
        no_progress = 0
        while sum(row["current_chamber"] == chamber for row in selected) < target:
            if not keys:
                break
            key = keys[cursor % len(keys)]
            cursor += 1
            bucket = buckets[key]
            chosen = None
            while bucket:
                candidate = bucket.pop(0)
                if candidate["program_id"] in used_programs:
                    continue
                if member_counts[candidate["expected_member"]] >= MAX_PER_MEMBER:
                    continue
                chosen = candidate
                break
            if chosen is None:
                no_progress += 1
                if no_progress >= len(keys) * 2:
                    keys = [candidate_key for candidate_key in keys if buckets[candidate_key]]
                    no_progress = 0
                continue
            no_progress = 0
            selected.append(chosen)
            used_programs.add(chosen["program_id"])
            member_counts[chosen["expected_member"]] += 1
        actual = sum(row["current_chamber"] == chamber for row in selected)
        if actual != target:
            raise ValueError(f"{chamber}: needed {target}, selected {actual}")
    return selected


def main() -> None:
    candidates, metadata_summary = build_candidates()
    core = [row for row in candidates if row["label_risk_tier"] == "core"]
    challenge = [
        row for row in candidates if row["label_risk_tier"] == "challenge"
    ]
    used_programs: set[str] = set()
    member_counts: Counter = Counter()
    selected_challenge = round_robin(
        challenge, CHALLENGE_TARGETS, used_programs, member_counts
    )
    selected_core = round_robin(
        core, CORE_TARGETS, used_programs, member_counts
    )
    selected = selected_core + selected_challenge
    selected.sort(
        key=lambda row: (
            row["label_risk_tier"],
            row["current_chamber"],
            row["year"],
            row["selection_hash"],
        )
    )
    items = []
    for index, row in enumerate(selected, start=1):
        case_id = f"V{index:03d}"
        items.append(
            {
                "case_id": case_id,
                "media_status": "REMOTE_HLS_NOT_DOWNLOADED",
                "planned_local_media": f"media/{case_id}.mp4",
                **row,
            }
        )
    document = {
        "schema": "interview-av-human-validation-manifest-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "seed": SEED,
        "status": "FROZEN_REMOTE_MEDIA_NOT_DOWNLOADED_NOT_ANNOTATED",
        "selection": (
            "150 stored C-SPAN Washington Journal programs: 120 low-risk core "
            "(108 House/12 Senate) plus 30 automated ownership-challenge cases "
            "(26 House/4 Senate), round-robin over 2020-2025 and three target "
            "duration bins, maximum four programs per expected member."
        ),
        "automated_risk_note": (
            "Risk flags prioritize human review and are not ground-truth labels."
        ),
        "production_consumers": 0,
        "metadata_summary": metadata_summary,
        "selected_summary": {
            "count": len(items),
            "by_chamber": dict(
                Counter(row["current_chamber"] for row in items)
            ),
            "by_year": dict(Counter(row["year"] for row in items)),
            "by_duration_bin": dict(
                Counter(row["duration_bin"] for row in items)
            ),
            "by_risk": dict(
                Counter(row["label_risk_tier"] for row in items)
            ),
            "distinct_members": len(
                {row["expected_member"] for row in items}
            ),
            "max_programs_per_member": max(member_counts.values()),
        },
        "items": items,
    }
    OUTPUT.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                **metadata_summary,
                **document["selected_summary"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
