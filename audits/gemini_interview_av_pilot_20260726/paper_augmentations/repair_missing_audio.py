#!/usr/bin/env python3
"""Mux separate C-SPAN audio renditions into v2 clips that are video-only."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path


AUDIT = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
MANIFEST = AUDIT / "pilot_manifest_30_fable_temporally_verified.json"
SOURCE_MEDIA = AUDIT / "media_fable_v2"
OUTPUT_MEDIA = HERE / "v3_source_repairs"
RECEIPTS = HERE / "v3_source_repairs.json"
DEFAULT_FFMPEG = Path(
    r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)


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


def fetch(url: str, referer: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Referer": referer},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


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


def audio_playlist(master_url: str, master_text: str) -> str:
    match = re.search(
        r'#EXT-X-MEDIA:[^\n]*TYPE=AUDIO[^\n]*URI="([^"]+)"',
        master_text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise ValueError(f"{master_url}: no separate audio rendition")
    return urllib.parse.urljoin(master_url, match.group(1))


def parse_segments(playlist_url: str, text: str) -> list[dict]:
    duration = None
    segments = []
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            duration = float(line.split(":", 1)[1].split(",", 1)[0])
        elif line and not line.startswith("#") and duration is not None:
            segments.append(
                {
                    "duration": duration,
                    "uri": urllib.parse.urljoin(playlist_url, line),
                }
            )
            duration = None
    if not segments:
        raise ValueError(f"{playlist_url}: no audio segments")
    return segments


def download_audio_window(
    item: dict,
    destination: Path,
) -> dict:
    master_url = item["media_url"]
    referer = item["source_url"]
    master_text = fetch(master_url, referer).decode("utf-8-sig")
    playlist_url = audio_playlist(master_url, master_text)
    playlist_text = fetch(playlist_url, referer).decode("utf-8-sig")
    segments = parse_segments(playlist_url, playlist_text)
    requested_start = float(item["start_sec"])
    requested_duration = float(item["duration_sec"])
    cursor = 0.0
    start_index = None
    for index, segment in enumerate(segments):
        if cursor + segment["duration"] > requested_start:
            start_index = index
            break
        cursor += segment["duration"]
    if start_index is None:
        raise ValueError(
            f"{item['pilot_id']}: audio start exceeds playlist duration"
        )
    local_seek = max(0.0, requested_start - cursor)
    needed = local_seek + requested_duration
    selected = []
    coverage = 0.0
    for segment in segments[start_index:]:
        selected.append(segment)
        coverage += segment["duration"]
        if coverage >= needed + 0.05:
            break
    if coverage < needed:
        raise ValueError(
            f"{item['pilot_id']}: audio coverage {coverage} < {needed}"
        )
    downloaded = 0
    with destination.open("wb") as handle:
        for segment in selected:
            payload = fetch(segment["uri"], referer)
            handle.write(payload)
            downloaded += len(payload)
    return {
        "audio_playlist_url": playlist_url,
        "audio_segment_start_sec": round(cursor, 6),
        "audio_local_seek_sec": round(local_seek, 6),
        "audio_selected_segment_count": len(selected),
        "audio_coverage_sec": round(coverage, 6),
        "audio_downloaded_bytes": downloaded,
    }


def repair_one(ffmpeg: Path, item: dict, force: bool) -> dict:
    case_id = item["pilot_id"]
    source = SOURCE_MEDIA / f"{case_id}.mp4"
    before = stream_inventory(ffmpeg, source)
    if not before["video_stream"]:
        return {"case_id": case_id, "status": "failed", "error": "no video"}
    if before["audio_stream"]:
        return {"case_id": case_id, "status": "not_needed", "before": before}
    OUTPUT_MEDIA.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_MEDIA / f"{case_id}.mp4"
    if output.is_file() and not force:
        after = stream_inventory(ffmpeg, output)
        if after["audio_stream"] and after["video_stream"]:
            return {
                "case_id": case_id,
                "status": "existing_repair",
                "before": before,
                "after": after,
                "path": str(output.relative_to(HERE)),
                "sha256": sha256_file(output),
            }
    audio = OUTPUT_MEDIA / f"{case_id}.window.aac"
    temporary = OUTPUT_MEDIA / f"{case_id}.part.mp4"
    for path in (audio, temporary):
        if path.exists():
            path.unlink()
    temporal = download_audio_window(item, audio)
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-ss",
        str(temporal["audio_local_seek_sec"]),
        "-i",
        str(audio),
        "-t",
        str(item["duration_sec"]),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
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
        "-shortest",
        str(temporary),
    ]
    completed = subprocess.run(
        command, text=True, capture_output=True, timeout=420
    )
    try:
        if completed.returncode:
            raise RuntimeError((completed.stderr or completed.stdout)[-1500:])
        after = stream_inventory(ffmpeg, temporary)
        if not after["audio_stream"] or not after["video_stream"]:
            raise RuntimeError(f"repaired stream inventory failed: {after}")
        os.replace(temporary, output)
    finally:
        if audio.exists():
            audio.unlink()
        if temporary.exists():
            temporary.unlink()
    return {
        "case_id": case_id,
        "status": "repaired",
        "before": before,
        "after": after,
        "source_path": str(source.relative_to(AUDIT)),
        "source_sha256": sha256_file(source),
        "path": str(output.relative_to(HERE)),
        "bytes": output.stat().st_size,
        "sha256": sha256_file(output),
        **temporal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = document["items"]
    if args.ids:
        wanted = set(args.ids)
        items = [item for item in items if item["pilot_id"] in wanted]
    receipts = []
    for item in items:
        receipt = repair_one(args.ffmpeg, item, args.force)
        receipts.append(receipt)
        print(json.dumps(receipt, ensure_ascii=False), flush=True)
    output = {
        "schema": "interview-av-v3-source-audio-repair",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "items": receipts,
        "repaired_count": sum(
            row["status"] in {"repaired", "existing_repair"} for row in receipts
        ),
        "failed_count": sum(row["status"] == "failed" for row in receipts),
    }
    atomic_json(RECEIPTS, output)
    return 1 if output["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
