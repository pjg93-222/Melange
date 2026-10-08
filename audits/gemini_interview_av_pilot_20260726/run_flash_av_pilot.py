#!/usr/bin/env python3
"""Run the real-video interview pilot through Gemini Flash only."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import subprocess
import threading
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "pilot_manifest_30_fable_temporally_verified.json"
MEDIA = HERE / "media_fable_v2"
RESULTS = HERE / "results_v2_cli"
RAW = HERE / "raw_v2_cli"
AGY = Path(r"C:\Users\pgoff\AppData\Local\agy\bin\agy.exe")
MODEL = "gemini-3.6-flash-high"
PRINT_LOCK = threading.Lock()
LEVELS = ["low", "medium", "high", "not_observable"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def parse_json(output: str) -> dict:
    text = output.strip()
    if text.startswith("```"):
        first_break = text.find("\n")
        last_fence = text.rfind("```")
        if first_break >= 0 and last_fence > first_break:
            text = text[first_break + 1 : last_fence].strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(text[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("response is not a JSON object")
    return value


def prompt(item: dict, media_path: Path) -> str:
    return f"""Directly inspect the audio and video tracks in this exact interview
clip: {media_path}

This is a stored C-SPAN Washington Journal interview segment. The private
project manifest identifies the expected congressional subject as
{item['expected_member']}. The user permits this identity manifest. Confirm
whether the visible/audible subject is consistent with that identity, flag a
mismatch or uncertainty, and attribute observations only to that target.

The clip duration is approximately {item['duration_sec']:.3f} seconds. The
target turn begins near {item['target_start_sec_in_clip']:.3f} seconds and ends
near {item['target_end_sec_in_clip']:.3f} seconds. Every timestamp must fall
within the clip.

Report only directly observable behavior. Do not infer Big Five traits,
personality, mental state, emotion as an internal state, health, protected
attributes, honesty, intent, intelligence, ideology, attractiveness, or
character. Camera edits and framing are production artifacts, not behavior.
Use not_observable whenever framing or audio does not support a field. Give
brief timestamped evidence, not chain-of-thought.

Return only one valid JSON object with exactly this structure:
{{
  "pilot_id": "{item['pilot_id']}",
  "model_family_required": "Gemini Flash",
  "media_processed": true,
  "modality": "audiovisual",
  "identity": {{
    "expected_member": {json.dumps(item['expected_member'])},
    "status": "confirmed",
    "confidence": 0.0,
    "basis": ["on_screen_label", "host_introduction", "face_voice_continuity"]
  }},
  "estimated_speaker_count": 1,
  "target_visible_fraction": 0.0,
  "target_face_visible_fraction": 0.0,
  "target_upper_body_visible_fraction": 0.0,
  "audio_observables": {{
    "pace": "not_observable",
    "pause_frequency": "not_observable",
    "disfluency_frequency": "not_observable",
    "prosodic_variability": "not_observable",
    "turn_competition": "not_observable",
    "response_directness": "not_observable"
  }},
  "visual_observables": {{
    "gaze_to_interviewer": "not_observable",
    "direct_camera_gaze": "not_observable",
    "gesture_frequency": "not_observable",
    "gesture_amplitude": "not_observable",
    "head_movement": "not_observable",
    "posture_shift": "not_observable",
    "facial_animation": "not_observable",
    "visual_turn_coordination": "not_observable"
  }},
  "evidence": [
    {{
      "timestamp_sec": 0.0,
      "modality": "visual",
      "observation": "short directly observable description"
    }}
  ],
  "transcript_excerpt": "maximum twenty words",
  "quality_flags": [],
  "error": null
}}

Identity status must be exactly confirmed, mismatch, or uncertain. Every audio
or visual observable must be exactly one of {json.dumps(LEVELS)}. Basis values
may include on_screen_label, host_introduction, face_voice_continuity,
speech_content, or insufficient. If direct audiovisual inspection fails, set
media_processed false, identity status uncertain, all observables
not_observable, and provide a short error."""


def run_one(item: dict, results: Path, raw: Path, force: bool) -> dict:
    pilot_id = item["pilot_id"]
    result_path = results / f"{pilot_id}.json"
    if result_path.exists() and not force:
        return {"pilot_id": pilot_id, "status": "existing"}
    media_path = (MEDIA / f"{pilot_id}.mp4").resolve()
    if not media_path.is_file():
        return {"pilot_id": pilot_id, "status": "missing_media"}
    media_hash = sha256_file(media_path)
    command = [
        str(AGY),
        "--model",
        MODEL,
        "--effort",
        "high",
        "--mode",
        "plan",
        "--add-dir",
        str(media_path.parent),
        "--print-timeout",
        "12m",
        "--print",
        prompt(item, media_path),
    ]
    started = time.monotonic()
    run = subprocess.run(
        command,
        cwd=media_path.parent,
        text=True,
        capture_output=True,
        timeout=780,
    )
    elapsed = round(time.monotonic() - started, 3)
    atomic_json(
        raw / f"{pilot_id}.json",
        {
            "pilot_id": pilot_id,
            "model": MODEL,
            "returncode": run.returncode,
            "elapsed_sec": elapsed,
            "stdout": run.stdout,
            "stderr": run.stderr,
        },
    )
    if run.returncode:
        return {
            "pilot_id": pilot_id,
            "status": "failed",
            "error": (run.stderr or run.stdout)[-500:],
        }
    try:
        result = parse_json(run.stdout)
        if result.get("pilot_id") != pilot_id:
            raise ValueError("pilot_id mismatch")
        result["_receipt"] = {
            "model": MODEL,
            "model_family": "Gemini Flash",
            "media_sha256": media_hash,
            "elapsed_sec": elapsed,
            "completed_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        atomic_json(result_path, result)
        return {"pilot_id": pilot_id, "status": "completed"}
    except Exception as exc:
        return {
            "pilot_id": pilot_id,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--raw", type=Path, default=RAW)
    args = parser.parse_args()
    if not AGY.is_file():
        raise FileNotFoundError(AGY)
    if not 1 <= args.jobs <= 3:
        raise ValueError("--jobs must be from 1 to 3")
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = document["items"]
    if args.ids:
        selected = set(args.ids)
        items = [item for item in items if item["pilot_id"] in selected]
    statuses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(run_one, item, args.results, args.raw, args.force)
            for item in items
        ]
        for future in concurrent.futures.as_completed(futures):
            status = future.result()
            statuses.append(status)
            with PRINT_LOCK:
                print(json.dumps(status), flush=True)
    completed = sum(row["status"] in {"completed", "existing"} for row in statuses)
    failed = len(statuses) - completed
    print(
        json.dumps(
            {
                "requested": len(statuses),
                "completed_or_existing": completed,
                "failed": failed,
                "model": MODEL,
            }
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
