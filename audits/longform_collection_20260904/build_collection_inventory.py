"""Read-only source/media audit. Writes inventory artifacts only in this folder."""
from __future__ import annotations

import hashlib
import json
import sys
import wave
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fec.speech.acquire_member_longform_audio import (  # noqa: E402
    acquisition_matches_candidate, acquisition_matches_queue, candidate_source_key, safe_name,
)

OUT = Path(__file__).resolve().parent
SPEECH = ROOT / "data/speech"
MEDIA = Path("C:/melange-data")


def stamp():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dump(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def check_file(value):
    path = Path(value)
    result = {"path": str(path), "exists": path.is_file()}
    if not result["exists"]:
        return result
    before = path.stat()
    result.update(size_bytes=before.st_size, actual_sha256=sha(path))
    after = path.stat()
    result["stable_while_hashed"] = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as sound:
                result["wave"] = {
                    "channels": sound.getnchannels(), "sample_rate": sound.getframerate(),
                    "sample_width": sound.getsampwidth(), "frames": sound.getnframes(),
                    "duration_seconds": round(sound.getnframes() / sound.getframerate(), 6),
                }
        except Exception as exc:
            result["wave_error"] = str(exc)
    return result


def main():
    started = stamp()
    paths = sorted(set(
        list(SPEECH.glob("member_longform*acquisition*.jsonl"))
        + list(SPEECH.glob("member_leadership_prerole*acquisition*.jsonl"))
        + list(SPEECH.glob("member_longform*queue*.jsonl"))
        + [SPEECH / name for name in (
            "member_longform_profile_source_selection_v1.jsonl",
            "member_longform_reviewed_source_overrides_v1.jsonl",
            "member_leadership_prerole_reviewed_sources_v1.jsonl",
            "member_interview_sources_20260903.jsonl",
        )]
        + list(MEDIA.glob("member_longform*transcripts*.jsonl"))
        + list(MEDIA.glob("member_leadership_prerole*transcripts*.jsonl"))
    ))
    ledgers, inputs = {}, {}
    for path in paths:
        if not path.exists():
            continue
        content = path.read_bytes()
        rows = [json.loads(line) for line in content.decode("utf-8-sig").splitlines() if line.strip()]
        ledgers[path.name] = rows
        inputs[str(path)] = {
            "sha256_at_snapshot": hashlib.sha256(content).hexdigest(),
            "rows": len(rows), "statuses": dict(Counter(r.get("status", "UNLABELED") for r in rows)),
            "duplicate_members": [n for n, count in Counter(r.get("member") for r in rows).items() if n and count > 1],
        }
    basis = json.loads((ROOT / "data/members/profile_basis_v2.json").read_text(encoding="utf-8"))
    roster = sorted(basis["members"])
    queue = {r["member"]: r for r in ledgers["member_longform_acquisition_queue_v1.jsonl"]}
    primary = {r["member"]: r for r in ledgers["member_longform_acquisition_v1.jsonl"]}
    selected = {r["member"]: r for r in ledgers["member_longform_profile_source_selection_v1.jsonl"]}
    overrides = {r["member"]: r for r in ledgers["member_longform_reviewed_source_overrides_v1.jsonl"]}
    acquisition_names = [n for n in ledgers if "acquisition" in n and "queue" not in n]
    acquisitions = defaultdict(list)
    for ledger in acquisition_names:
        for row in ledgers[ledger]:
            acquisitions[row["member"]].append({"ledger": ledger, **row})
    original_sources = ledgers.get("member_interview_sources_20260903.jsonl", [])
    for row in original_sources:
        acquisitions[row["member"]].append({
            "ledger": "member_interview_sources_20260903.jsonl", **row,
            "source_id": row.get("video_id"), "wav_sha256": row.get("source_audio_sha256"),
            "status": "ORIGINAL_SOURCE_LEDGER_NO_NEW_IDENTITY_ASSERTION",
        })
    gaps = []
    for name in roster:
        current = primary.get(name, {})
        wanted = queue.get(name, {}).get("primary") or {}
        if not current or not acquisition_matches_queue(current, queue[name]):
            gaps.append({
                "member": name, "old_source_id": current.get("source_id"),
                "old_title": current.get("title"), "old_wav": current.get("wav"),
                "required_source_id": candidate_source_key(wanted), "required_title": wanted.get("title"),
                "required_url": wanted.get("url"), "required_audio_url": wanted.get("audio_url"),
                "review_reason": overrides.get(name, {}).get("review_reason"),
                "reviewed_replacement": bool(wanted.get("reviewed_replacement")),
            })
    dump("primary_reacquisition_gaps.json", {"snapshot_at": started, "count": len(gaps), "members": gaps})
    print(json.dumps({"snapshot_at": started, "primary_slots": len(primary), "current_queue_mismatches": len(gaps)}, ensure_ascii=False), flush=True)
    references = set()
    for rows in ledgers.values():
        for row in rows:
            for key in ("wav", "transcript"):
                if row.get(key):
                    references.add(row[key])
    checks = {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        work = {pool.submit(check_file, path): path for path in references}
        for index, future in enumerate(as_completed(work), 1):
            path = work[future]
            try:
                checks[path] = future.result()
            except Exception as exc:
                checks[path] = {"path": path, "exists": Path(path).is_file(), "error": str(exc)}
            if index % 100 == 0:
                print(json.dumps({"files_checked": index, "total": len(work)}), flush=True)

    def binding(row, field="wav", digest_field="wav_sha256"):
        value = row.get(field)
        check = checks.get(value, {})
        expected = row.get(digest_field)
        return {
            "path": value, "exists": bool(check.get("exists")), "expected_sha256": expected,
            "actual_sha256": check.get("actual_sha256"),
            "hash_matches": bool(expected and expected == check.get("actual_sha256") and check.get("stable_while_hashed")),
            "measured_duration_seconds": (check.get("wave") or {}).get("duration_seconds"),
        }

    inventories = []
    for name in roster:
        current = primary.get(name, {})
        q = queue.get(name, {})
        s = selected.get(name, {})
        records = []
        for row in acquisitions[name]:
            records.append({
                **{key: row.get(key) for key in ("ledger", "status", "source_id", "source_type", "title", "channel", "url", "acquired_at", "recorded_at", "published", "source_era")},
                "media": binding(row),
                "matches_current_primary_queue": bool(q and acquisition_matches_queue(row, q)),
                "matches_exact_current_primary": bool(q.get("primary") and acquisition_matches_candidate(row, q["primary"])),
            })
        valid_hashes = {r["media"]["actual_sha256"] for r in records if r["media"]["hash_matches"]}
        inventories.append({
            "member": name,
            "queue": {"status": q.get("status"), "primary": q.get("primary"), "candidate_count": q.get("candidate_count"), "reviewed_replacement": name in overrides},
            "primary_acquisition": {"status": current.get("status"), "source_id": current.get("source_id"), "media": binding(current), "matches_current_queue": bool(q and acquisition_matches_queue(current, q))},
            "acquired_records": records,
            "distinct_hash_verified_recordings": len(valid_hashes),
            "selection": {
                **{key: s.get(key) for key in ("status", "selection", "source_id", "title", "source_era")},
                "media": binding(s), "transcript": binding(s, "transcript", "transcript_sha256"),
                "matches_current_primary_queue": bool(q and acquisition_matches_queue(s, q)),
                "matches_any_acquisition_record": any(acquisition_matches_candidate(r, s) for r in acquisitions[name]) if s.get("source_id") else False,
                "matches_required_leadership_queue": next((acquisition_matches_queue(s, r) for r in ledgers.get("member_leadership_prerole_acquisition_queue_v1.jsonl", []) if r["member"] == name), None),
            },
        })
    for path, entry in inputs.items():
        entry["sha256_at_end"] = sha(Path(path))
        entry["changed_during_audit"] = entry["sha256_at_end"] != entry["sha256_at_snapshot"]
    ledger_media = {}
    for name in acquisition_names:
        rows = ledgers[name]
        ledger_media[name] = {
            "rows": len(rows), "members": len({r["member"] for r in rows}),
            "statuses": dict(Counter(r.get("status") for r in rows)),
            "audio_files_present": sum(binding(r)["exists"] for r in rows),
            "audio_hash_matches": sum(binding(r)["hash_matches"] for r in rows),
            "audio_hours": round(sum(binding(r)["measured_duration_seconds"] or 0 for r in rows) / 3600, 3),
            "problems": [{"member": r["member"], "source_id": r.get("source_id"), "status": r.get("status"), "media": binding(r)} for r in rows if not binding(r)["hash_matches"]],
        }
    leadership_queue = ledgers.get("member_leadership_prerole_acquisition_queue_v1.jsonl", [])
    summary = {
        "snapshot_at": started, "finished_at": stamp(), "roster": len(roster),
        "scope": "File bytes and source-binding inventory only. No listening review, speaker verification, interview-independence determination, behavioral promotion, or profile editing.",
        "selection_comparison_note": "The list of selections outside the current primary/leadership queues includes legitimate retry recordings. It is not an identity or quality rejection; the approved replacement bindings must be evaluated separately.",
        "input_ledgers_changed_during_audit": [path for path, r in inputs.items() if r["changed_during_audit"]],
        "primary_acquisition_rows": len(primary),
        "primary_audio_present": sum(r["primary_acquisition"]["media"]["exists"] for r in inventories),
        "primary_audio_hash_matches": sum(r["primary_acquisition"]["media"]["hash_matches"] for r in inventories),
        "primary_recordings_at_least_ten_minutes": sum((r["primary_acquisition"]["media"]["measured_duration_seconds"] or 0) >= 600 for r in inventories),
        "primary_matches_current_queue": sum(r["primary_acquisition"]["matches_current_queue"] for r in inventories),
        "primary_current_queue_mismatches": len(gaps),
        "reviewed_source_overrides": len(overrides),
        "members_with_any_hash_verified_recording": sum(r["distinct_hash_verified_recordings"] > 0 for r in inventories),
        "members_with_two_or_more_distinct_hash_verified_recordings": sum(r["distinct_hash_verified_recordings"] >= 2 for r in inventories),
        "members_with_zero_hash_verified_recordings": [r["member"] for r in inventories if not r["distinct_hash_verified_recordings"]],
        "selected_statuses": dict(Counter(r.get("status") for r in selected.values())),
        "selected_audio_hash_matches": sum(r["selection"]["media"]["hash_matches"] for r in inventories),
        "selected_transcript_hash_matches": sum(r["selection"]["transcript"]["hash_matches"] for r in inventories),
        "selection_not_current_queue_or_leadership_queue": [
            {"member": r["member"], "source_id": r["selection"]["source_id"], "status": r["selection"]["status"]}
            for r in inventories if r["selection"]["source_id"] and not r["selection"]["matches_current_primary_queue"] and r["selection"]["matches_required_leadership_queue"] is not True
        ],
        "selection_no_source": [{"member": r["member"], "status": r["selection"]["status"]} for r in inventories if not r["selection"]["source_id"]],
        "leadership_queue_rows": len(leadership_queue),
        "leadership_reviewed_source_statuses": dict(Counter(r.get("status") for r in ledgers.get("member_leadership_prerole_reviewed_sources_v1.jsonl", []))),
        "acquisition_ledgers": ledger_media,
        "total_unique_referenced_files": len(checks),
        "unique_referenced_audio_gb": round(sum(v.get("size_bytes", 0) for k, v in checks.items() if Path(k).suffix.lower() == ".wav") / 1e9, 3),
    }
    dump("collection_inventory_summary.json", summary)
    dump("collection_inventory_members.json", {"snapshot_at": started, "members": inventories})
    dump("collection_inventory_files.json", {"snapshot_at": started, "inputs": inputs, "files": checks})
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
