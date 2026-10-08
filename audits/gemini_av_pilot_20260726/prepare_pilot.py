"""Freeze the 30-item Gemini media pilot and create neutralized media files.

This script is intentionally isolated from the production pipeline. It reads
the existing Wav2Vec benchmark and legacy review queue, then writes only under
this audit directory.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import subprocess
import wave
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE_CSV = ROOT / "audio_wav2vec_30member_scores.csv"
LEGACY_REVIEW = ROOT / "b5_audio_verify.json"
MEDIA_DIR = HERE / "media"
MANIFEST = HERE / "manifest.json"
BLINDED = HERE / "blinded_tasks.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate() or 1)


def bool_value(value: str) -> bool:
    return str(value).strip().lower() == "true"


def candidate_set(row: dict[str, str], cohort: list[str], pilot_id: str) -> list[str]:
    candidates: list[str] = []
    for name in (
        row["expected_member"],
        row.get("predicted_member", ""),
        row.get("max_impostor_member", ""),
    ):
        if name and name not in candidates:
            candidates.append(name)

    seed = int(hashlib.sha256(pilot_id.encode("ascii")).hexdigest()[:16], 16)
    rng = random.Random(seed)
    pool = cohort[:]
    rng.shuffle(pool)
    for name in pool:
        if name not in candidates:
            candidates.append(name)
        if len(candidates) == 5:
            break

    if len(candidates) != 5:
        raise ValueError(f"{pilot_id}: could not construct five unique candidates")
    rng.shuffle(candidates)
    return candidates


def neutral_link(source: Path, destination: Path) -> str:
    if destination.exists():
        if os.path.samefile(source, destination):
            return "existing_hardlink"
        raise FileExistsError(f"neutral path exists but does not match source: {destination}")
    try:
        os.link(source, destination)
        return "hardlink"
    except OSError:
        shutil.copy2(source, destination)
        return "copy"


def convert_mp3(ffmpeg: Path, source: Path, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 10_000:
        return
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-codec:a",
        "libmp3lame",
        "-b:a",
        "64k",
        str(destination),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=180)
    if run.returncode or not destination.exists() or destination.stat().st_size <= 10_000:
        raise RuntimeError(
            f"ffmpeg failed for {source.name}: {(run.stderr or 'no stderr')[-600:]}"
        )


def convert_mp4(ffmpeg: Path, source: Path, destination: Path) -> None:
    """Wrap audio in a label-free black-frame MP4 for Gemini media ingestion."""
    if destination.exists() and destination.stat().st_size > 10_000:
        return
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=320x180:r=1",
        "-i",
        str(source),
        "-shortest",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-tune",
        "stillimage",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "64k",
        "-movflags",
        "+faststart",
        str(destination),
    ]
    run = subprocess.run(command, capture_output=True, text=True, timeout=240)
    if run.returncode or not destination.exists() or destination.stat().st_size <= 10_000:
        raise RuntimeError(
            f"ffmpeg MP4 wrap failed for {source.name}: "
            f"{(run.stderr or 'no stderr')[-600:]}"
        )


def build(ffmpeg: Path | None) -> tuple[list[dict], list[dict]]:
    if not SOURCE_CSV.exists():
        raise FileNotFoundError(SOURCE_CSV)
    with SOURCE_CSV.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 30:
        raise ValueError(f"frozen benchmark must have exactly 30 rows, found {len(rows)}")

    legacy = json.loads(LEGACY_REVIEW.read_text(encoding="utf-8"))
    cohort = [row["expected_member"] for row in rows]
    if len(set(cohort)) != 30:
        raise ValueError("frozen benchmark must have 30 unique expected members")

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    tasks: list[dict] = []

    for index, row in enumerate(rows, 1):
        pilot_id = f"P{index:03d}"
        video_id = row["source_id"].removeprefix("youtube:")
        source = ROOT / "audio_pilot" / row["expected_member"] / f"clip_{video_id}.wav"
        if not source.is_file():
            raise FileNotFoundError(source)

        wav_path = MEDIA_DIR / f"{pilot_id}.wav"
        mp3_path = MEDIA_DIR / f"{pilot_id}.mp3"
        mp4_path = MEDIA_DIR / f"{pilot_id}.mp4"
        link_kind = neutral_link(source, wav_path)
        if ffmpeg is not None:
            convert_mp3(ffmpeg, wav_path, mp3_path)
            convert_mp4(ffmpeg, wav_path, mp4_path)

        legacy_key = f"{row['expected_member']}/clip_{video_id}.wav"
        candidates = candidate_set(row, cohort, pilot_id)
        duration = round(wav_duration(source), 3)
        source_hash = sha256_file(source)
        media_hash = sha256_file(mp4_path) if mp4_path.exists() else None
        item = {
            "pilot_id": pilot_id,
            "expected_member": row["expected_member"],
            "label_status": "WEAK_MACHINE_CAPTION_EXPECTATION_NOT_GOLD",
            "source_id": row["source_id"],
            "source_url": row["source_url"],
            "source_path": str(source.relative_to(ROOT)),
            "neutral_wav_path": str(wav_path.relative_to(HERE)),
            "neutral_mp3_path": (
                str(mp3_path.relative_to(HERE)) if mp3_path.exists() else None
            ),
            "neutral_mp4_path": (
                str(mp4_path.relative_to(HERE)) if mp4_path.exists() else None
            ),
            "neutralization": link_kind,
            "duration_sec": duration,
            "audio_sha256": source_hash,
            "media_sha256": media_hash,
            "candidate_set": candidates,
            "wav2vec_baseline": {
                "predicted_member": row["predicted_member"],
                "correct_against_recorded_label": bool_value(row["correct"]),
                "expected_cosine": float(row["expected_cosine"]),
                "max_impostor_member": row["max_impostor_member"],
                "max_impostor_cosine": float(row["max_impostor_cosine"]),
                "impostor_margin": float(row["impostor_margin"]),
                "identity_guard": row["identity_guard"],
            },
            "legacy_caption_review": legacy.get(legacy_key),
        }
        manifest.append(item)
        tasks.append(
            {
                "pilot_id": pilot_id,
                "media_path": (
                    item["neutral_mp4_path"]
                    or item["neutral_mp3_path"]
                    or item["neutral_wav_path"]
                ),
                "candidate_set": candidates,
                "duration_sec": duration,
                "media_sha256": media_hash,
                "instructions": (
                    "Analyze the media directly. Choose one candidate or abstain. "
                    "Report only observable, timestamped delivery behavior. Do not "
                    "infer personality, mental state, demographics, or protected attributes."
                ),
            }
        )

    return manifest, tasks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ffmpeg",
        type=Path,
        help="Optional existing ffmpeg executable used to create Gemini-ready MP3 copies.",
    )
    args = parser.parse_args()
    if args.ffmpeg is not None and not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)

    manifest, tasks = build(args.ffmpeg)
    document = {
        "schema": "gemini-congressional-av-pilot-manifest-v1",
        "status": "RESEARCH_CANDIDATE_NOT_CONSUMED",
        "source_benchmark": SOURCE_CSV.name,
        "sample_n": len(manifest),
        "label_status": "WEAK_MACHINE_CAPTION_EXPECTATION_NOT_GOLD",
        "production_consumers": 0,
        "items": manifest,
    }
    MANIFEST.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    BLINDED.write_text(
        json.dumps(
            {
                "schema": "gemini-congressional-av-pilot-tasks-v1",
                "status": "BLINDED_TASKS",
                "sample_n": len(tasks),
                "items": tasks,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "sample_n": len(manifest),
                "media_ready": sum(
                    1 for item in manifest if item["neutral_mp4_path"] is not None
                ),
                "manifest": str(MANIFEST),
                "blinded_tasks": str(BLINDED),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
