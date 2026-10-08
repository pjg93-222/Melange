#!/usr/bin/env python3
"""Build hash-pinned audio, V16, A/V, and mismatch media for diagnostic v3."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


AUDIT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
SOURCE_MANIFEST = AUDIT / "pilot_manifest_30_fable_temporally_verified.json"
SOURCE_MEDIA = AUDIT / "media_fable_v2"
REPAIRED_MEDIA = HERE / "v3_source_repairs"
OUTPUT_MEDIA = HERE / "v3_media"
OUTPUT_MANIFEST = HERE / "v3_manifest.json"
DEFAULT_FFMPEG = Path(
    r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)

CASE_IDS = [
    "F004",
    "F006",
    "F008",
    "F011",
    "F013",
    "F018",
    "F020",
    "F025",
    "F019",
    "F027",
]
V2_FAILURES = CASE_IDS[:8]
SENTINELS = CASE_IDS[8:]
MISMATCHES = [
    {"case_id": "M001", "video_case": "F004", "audio_case": "F011"},
    {"case_id": "M002", "video_case": "F018", "audio_case": "F025"},
]


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run(command: list[str]) -> None:
    completed = subprocess.run(command, text=True, capture_output=True)
    if completed.returncode:
        detail = (completed.stderr or completed.stdout)[-2000:]
        raise RuntimeError(f"ffmpeg failed ({completed.returncode}): {detail}")


def stream_inventory(ffmpeg: Path, media: Path) -> dict:
    completed = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(media), "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    text = completed.stderr or completed.stdout
    return {
        "audio_stream": "Audio:" in text,
        "video_stream": "Video:" in text,
    }


def source_for_case(case_id: str) -> Path:
    repaired = REPAIRED_MEDIA / f"{case_id}.mp4"
    return repaired if repaired.is_file() else SOURCE_MEDIA / f"{case_id}.mp4"


def normalized_av(
    ffmpeg: Path,
    source: Path,
    output: Path,
    start_sec: float,
    duration_sec: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_sec:.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration_sec:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-vf",
            "scale=640:-2:flags=lanczos,fps=25,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def audio_wav(
    ffmpeg: Path,
    source: Path,
    output: Path,
    start_sec: float,
    duration_sec: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_sec:.3f}",
            "-i",
            str(source),
            "-t",
            f"{duration_sec:.3f}",
            "-vn",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )


def frame_at(ffmpeg: Path, source: Path, output: Path, second: float) -> None:
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{second:.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-c:v",
            "png",
            str(output),
        ]
    )


def build_storyboard(
    ffmpeg: Path,
    source_av: Path,
    frames_dir: Path,
    output: Path,
    duration_sec: float,
) -> tuple[list[dict], str]:
    frames_dir.mkdir(parents=True, exist_ok=True)
    # Use the midpoint of each of 16 equal temporal bins. This is deterministic,
    # spans the whole window, and avoids decoder failures at the exact final PTS.
    timestamps = [
        (index + 0.5) * duration_sec / 16 for index in range(16)
    ]
    frames = []
    for index, timestamp in enumerate(timestamps, start=1):
        path = frames_dir / f"{index:02d}.png"
        frame_at(ffmpeg, source_av, path, timestamp)
        frames.append(
            {
                "index": index,
                "timestamp_sec": round(timestamp, 3),
                "path": str(path.relative_to(HERE)),
                "sha256": sha256_file(path),
            }
        )

    tile_width, tile_height = 480, 270
    label_height = 34
    sheet = Image.new(
        "RGB",
        (tile_width * 4, (tile_height + label_height) * 4),
        "white",
    )
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default(size=20)
    for slot, record in enumerate(frames):
        row, column = divmod(slot, 4)
        x = column * tile_width
        y = row * (tile_height + label_height)
        with Image.open(HERE / record["path"]) as raw:
            image = raw.convert("RGB")
            image.thumbnail((tile_width, tile_height), Image.Resampling.LANCZOS)
            paste_x = x + (tile_width - image.width) // 2
            paste_y = y + (tile_height - image.height) // 2
            sheet.paste(image, (paste_x, paste_y))
        label = (
            f"frame {record['index']:02d}/16  "
            f"t={record['timestamp_sec']:.3f}s"
        )
        draw.rectangle(
            (x, y + tile_height, x + tile_width, y + tile_height + label_height),
            fill="black",
        )
        draw.text(
            (x + 8, y + tile_height + 6),
            label,
            fill="white",
            font=font,
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output, format="JPEG", quality=92, optimize=True)
    return frames, sha256_file(output)


def mismatch_av(
    ffmpeg: Path,
    video_source: Path,
    audio_source: Path,
    output: Path,
    duration_sec: float,
) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(video_source),
            "-i",
            str(audio_source),
            "-t",
            f"{duration_sec:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            "scale=640:-2:flags=lanczos,fps=25,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def prompt_for(case_id: str, condition: str, duration_sec: float) -> str:
    media_description = {
        "audio_only": (
            "The attachment contains audio only. Analyze the primary interview "
            "subject speaking in this admitted target-turn extract."
        ),
        "visual16_only": (
            "The attachment is a silent 4x4 storyboard containing exactly 16 "
            "equally spaced frames. Use the printed relative timestamps."
        ),
        "audiovisual": (
            "The attachment contains the audio and video from one admitted "
            "target-turn extract. Decide whether the streams are mutually "
            "consistent; deliberate mismatches are possible."
        ),
    }[condition]
    return f"""Gemini Flash diagnostic case {case_id}. {media_description}

No identity manifest is supplied. Do not identify or guess any person. Report
only directly observable perception evidence. Do not infer personality, Big
Five traits, mental state, emotion as an internal state, intent, honesty,
intelligence, ideology, character, health, protected attributes, or
attractiveness. Camera cuts, framing, and direct-camera setup are production
artifacts. The target-relative duration is {duration_sec:.3f} seconds; every
timestamp must be between 0 and {duration_sec:.3f}.

First assess audio and visual evidence independently, then temporal order, then
the composite. Missing modalities must be marked unobservable, never filled
from expectation. A short excerpt must be verbatim and at most 20 words. Give
brief evidence, not chain-of-thought. Return only one JSON object with exactly
these keys and structure:
{{
  "schema": "interview-av-v3.0",
  "case_id": "{case_id}-{condition}",
  "condition": "{condition}",
  "media_processed": true,
  "abstained": false,
  "quality_flags": [],
  "atomic": {{
    "audio": {{
      "speech": "present|absent|uncertain|not_observable",
      "speaker_count": 0,
      "target_active_intervals": [{{"start_sec": 0.0, "end_sec": 0.0}}],
      "events": [{{"event_id": "a1", "start_sec": 0.0, "end_sec": 0.0, "description": "observable only"}}],
      "excerpt": "maximum twenty verbatim words",
      "pace": "low|medium|high|not_observable",
      "pause_frequency": "low|medium|high|not_observable",
      "disfluency_frequency": "low|medium|high|not_observable",
      "prosodic_variability": "low|medium|high|not_observable"
    }},
    "visual": {{
      "person_visible": "yes|no|uncertain|not_observable",
      "face_visible": "yes|no|uncertain|not_observable",
      "upper_body_visible": "yes|no|uncertain|not_observable",
      "displayed_text": [],
      "events": [{{"event_id": "v1", "type": "gesture|head_move|posture_shift|shot_change|turn_coordination|other", "start_sec": 0.0, "end_sec": 0.0, "description": "observable only"}}]
    }},
    "temporal": {{
      "order_pairs": [{{"first_event_id": "a1", "second_event_id": "v1", "relation": "before|after|overlaps|uncertain"}}]
    }}
  }},
  "composite": {{
    "av_consistency": "matched|mismatched|uncertain|not_applicable",
    "synchronization": "synchronized|audio_leads|video_leads|not_observable",
    "lag_ms": null,
    "absent_modality": "none|audio|video|not_applicable",
    "confidence": 0.0
  }},
  "evidence": [{{"timestamp_sec": 0.0, "modality": "audio|visual|audiovisual", "observation": "direct observation"}}],
  "prohibited_inference_detected": false,
  "error": null
}}

Use the exact condition and case_id shown. When a modality is unavailable,
use not_observable, empty arrays/text, and no evidence from that modality.
For single-modality conditions, av_consistency must be not_applicable and
synchronization must be not_observable."""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)
    document = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    by_id = {item["pilot_id"]: item for item in document["items"]}
    missing = sorted(set(CASE_IDS) - set(by_id))
    if missing:
        raise ValueError(f"missing manifest cases: {missing}")

    all_source_streams = {}
    for case_id in sorted(by_id):
        source = source_for_case(case_id)
        if not source.is_file():
            all_source_streams[case_id] = {
                "audio_stream": False,
                "video_stream": False,
                "missing_file": True,
            }
        else:
            all_source_streams[case_id] = stream_inventory(args.ffmpeg, source)
    source_streams = {
        case_id: all_source_streams[case_id] for case_id in CASE_IDS
    }
    invalid_sources = {
        case_id: streams
        for case_id, streams in source_streams.items()
        if not streams["audio_stream"] or not streams["video_stream"]
    }
    atomic_json(
        HERE / "v3_source_stream_preflight.json",
        {
            "schema": "interview-av-v3-source-stream-preflight",
            "all_cases": all_source_streams,
            "selected_cases": source_streams,
            "invalid_sources": invalid_sources,
            "status": "FAIL_CLOSED" if invalid_sources else "PASS",
        },
    )
    if invalid_sources:
        raise ValueError(
            "selected source clips are not audiovisual: "
            + json.dumps(invalid_sources, sort_keys=True)
        )

    cases = []
    for case_id in CASE_IDS:
        item = by_id[case_id]
        source = source_for_case(case_id)
        source_duration = float(item["duration_sec"])
        start = float(item["target_start_sec_in_clip"])
        end = float(item["target_end_sec_in_clip"])
        if not all(math.isfinite(value) for value in (source_duration, start, end)):
            raise ValueError(f"{case_id}: non-finite target bounds")
        if start < 0 or end <= start or end > source_duration + 0.25:
            raise ValueError(
                f"{case_id}: target [{start}, {end}] outside {source_duration}"
            )
        duration = round(min(end, source_duration) - start, 3)
        case_dir = OUTPUT_MEDIA / case_id
        av_path = case_dir / f"{case_id}-audiovisual.mp4"
        audio_path = case_dir / f"{case_id}-audio_only.wav"
        storyboard_path = case_dir / f"{case_id}-visual16_only.jpg"
        frames_dir = case_dir / "visual16_frames"
        if args.force or not av_path.exists():
            normalized_av(args.ffmpeg, source, av_path, start, duration)
        if args.force or not audio_path.exists():
            audio_wav(args.ffmpeg, source, audio_path, start, duration)
        existing_png_frames = sorted(frames_dir.glob("*.png"))
        if (
            args.force
            or not storyboard_path.exists()
            or len(existing_png_frames) != 16
        ):
            frames, storyboard_hash = build_storyboard(
                args.ffmpeg,
                av_path,
                frames_dir,
                storyboard_path,
                duration,
            )
        else:
            frame_paths = existing_png_frames
            if len(frame_paths) != 16:
                raise ValueError(f"{case_id}: expected 16 frames")
            frames = [
                {
                    "index": index,
                    "timestamp_sec": round(
                        (index - 0.5) * duration / 16,
                        3,
                    ),
                    "path": str(path.relative_to(HERE)),
                    "sha256": sha256_file(path),
                }
                for index, path in enumerate(frame_paths, start=1)
            ]
            storyboard_hash = sha256_file(storyboard_path)
        derivatives = {}
        for condition, path in (
            ("audio_only", audio_path),
            ("visual16_only", storyboard_path),
            ("audiovisual", av_path),
        ):
            inventory = stream_inventory(args.ffmpeg, path)
            derivatives[condition] = {
                "path": str(path.relative_to(HERE)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "duration_sec": duration,
                "streams": inventory,
                "prompt": prompt_for(case_id, condition, duration),
            }
        cases.append(
            {
                "case_id": case_id,
                "role": (
                    "known_v2_semantic_failure"
                    if case_id in V2_FAILURES
                    else "aligned_sentinel"
                ),
                "source": {
                    "path": (
                        str(source.relative_to(AUDIT))
                        if AUDIT in source.parents
                        else str(source)
                    ),
                    "sha256": sha256_file(source),
                    "duration_sec": source_duration,
                    "program_id": str(item["program_id"]),
                    "target_turn_seq": int(item["target_turn_seq"]),
                    "target_start_sec": start,
                    "target_end_sec": end,
                    "stored_target_text": item["target_transcript_excerpt"],
                    "streams": source_streams[case_id],
                },
                "derivatives": derivatives,
                "visual16": {
                    "frame_count": len(frames),
                    "storyboard_sha256": storyboard_hash,
                    "frames": frames,
                },
            }
        )

    case_map = {case["case_id"]: case for case in cases}
    mismatch_rows = []
    for mismatch in MISMATCHES:
        video_case = case_map[mismatch["video_case"]]
        audio_case = case_map[mismatch["audio_case"]]
        video_path = HERE / video_case["derivatives"]["audiovisual"]["path"]
        audio_path = HERE / audio_case["derivatives"]["audio_only"]["path"]
        duration = min(
            video_case["derivatives"]["audiovisual"]["duration_sec"],
            audio_case["derivatives"]["audio_only"]["duration_sec"],
        )
        output = OUTPUT_MEDIA / mismatch["case_id"] / (
            f"{mismatch['case_id']}-audiovisual.mp4"
        )
        if args.force or not output.exists():
            mismatch_av(args.ffmpeg, video_path, audio_path, output, duration)
        mismatch_rows.append(
            {
                **mismatch,
                "hidden_label": "mismatched",
                "derivative": {
                    "path": str(output.relative_to(HERE)),
                    "bytes": output.stat().st_size,
                    "sha256": sha256_file(output),
                    "duration_sec": duration,
                    "streams": stream_inventory(args.ffmpeg, output),
                    "prompt": prompt_for(
                        mismatch["case_id"], "audiovisual", duration
                    ),
                },
            }
        )

    output = {
        "schema": "interview-av-diagnostic-v3-manifest",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model_contract": "Gemini Flash only; independent fresh sessions",
        "identity_contract": "blind case IDs; no expected names in prompts",
        "production_consumers": 0,
        "case_ids": CASE_IDS,
        "known_v2_failures": V2_FAILURES,
        "aligned_sentinels": SENTINELS,
        "primary_call_count": len(cases) * 3,
        "hidden_mismatch_call_count": len(mismatch_rows),
        "cases": cases,
        "mismatches": mismatch_rows,
    }
    atomic_json(OUTPUT_MANIFEST, output)
    print(
        json.dumps(
            {
                "manifest": str(OUTPUT_MANIFEST),
                "cases": len(cases),
                "primary_calls": len(cases) * 3,
                "hidden_mismatches": len(mismatch_rows),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
