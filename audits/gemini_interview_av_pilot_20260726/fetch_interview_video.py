#!/usr/bin/env python3
"""Clip the frozen C-SPAN HLS interview segments into real local MP4s."""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import threading
import urllib.parse
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "pilot_manifest_30.json"
MEDIA = HERE / "media"
RECEIPTS = HERE / "media_receipts.json"
DEFAULT_FFMPEG = Path(
    r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)
PRINT_LOCK = threading.Lock()
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch_playlist(url: str, referer: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Referer": referer},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig")


def fetch_bytes(url: str, referer: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Referer": referer},
    )
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def choose_rendition(master_url: str, text: str) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        uri = next(
            (
                candidate
                for candidate in lines[index + 1 :]
                if not candidate.startswith("#")
            ),
            None,
        )
        if uri is None:
            continue
        resolution = re.search(r"RESOLUTION=(\d+)x(\d+)", line)
        bandwidth = re.search(r"BANDWIDTH=(\d+)", line)
        height = int(resolution.group(2)) if resolution else 10_000
        bitrate = int(bandwidth.group(1)) if bandwidth else 10_000_000
        candidates.append(
            (
                abs(height - 360),
                abs(bitrate - 720_000),
                urllib.parse.urljoin(master_url, uri),
            )
        )
    if not candidates:
        return master_url, text
    _, _, rendition_url = min(candidates)
    return rendition_url, ""


def absolutize_tag_uri(tag: str, playlist_url: str) -> str:
    match = re.search(r'URI="([^"]+)"', tag)
    if not match:
        return tag
    absolute = urllib.parse.urljoin(playlist_url, match.group(1))
    return tag[: match.start(1)] + absolute + tag[match.end(1) :]


def parse_segments(playlist_url: str, text: str) -> list[dict]:
    segments = []
    duration = None
    active_key = None
    active_map = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("#EXT-X-KEY:"):
            active_key = absolutize_tag_uri(line, playlist_url)
        elif line.startswith("#EXT-X-MAP:"):
            active_map = absolutize_tag_uri(line, playlist_url)
        elif line.startswith("#EXTINF:"):
            duration = float(line.split(":", 1)[1].split(",", 1)[0])
        elif not line.startswith("#") and duration is not None:
            segments.append(
                {
                    "duration": duration,
                    "uri": urllib.parse.urljoin(playlist_url, line),
                    "key": active_key,
                    "map": active_map,
                }
            )
            duration = None
    if not segments:
        raise ValueError(f"{playlist_url}: no HLS segments found")
    return segments


def build_trimmed_transport_stream(
    item: dict,
    media_dir: Path,
) -> tuple[Path, dict]:
    master_text = fetch_playlist(item["media_url"], item["source_url"])
    rendition_url, rendition_text = choose_rendition(
        item["media_url"],
        master_text,
    )
    if not rendition_text:
        rendition_text = fetch_playlist(rendition_url, item["source_url"])
    segments = parse_segments(rendition_url, rendition_text)
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
            f"{item['pilot_id']}: start {requested_start} exceeds playlist"
        )
    segment_start = cursor
    local_seek = max(0.0, requested_start - segment_start)
    required_coverage = local_seek + requested_duration
    selected = []
    coverage = 0.0
    for segment in segments[start_index:]:
        selected.append(segment)
        coverage += segment["duration"]
        if coverage >= required_coverage + segment["duration"]:
            break
    usable_duration = coverage - local_seek
    if usable_duration <= 1:
        raise ValueError(
            f"{item['pilot_id']}: no usable media after requested start"
        )
    output_duration = min(requested_duration, usable_duration - 0.05)

    transport_path = media_dir / f"{item['pilot_id']}.trim.ts"
    if transport_path.exists():
        transport_path.unlink()
    downloaded_bytes = 0
    with transport_path.open("wb") as handle:
        for segment in selected:
            if segment["key"] or segment["map"]:
                raise ValueError(
                    f"{item['pilot_id']}: encrypted or mapped HLS is unsupported"
                )
            payload = fetch_bytes(segment["uri"], item["source_url"])
            handle.write(payload)
            downloaded_bytes += len(payload)
    return transport_path, {
        "temporal_selection": "hls-segment-trim-v2",
        "rendition_url": rendition_url,
        "requested_start_sec": requested_start,
        "source_segment_start_sec": round(segment_start, 6),
        "local_seek_sec": round(local_seek, 6),
        "requested_duration_sec": requested_duration,
        "output_duration_sec": round(output_duration, 6),
        "selected_segment_count": len(selected),
        "selected_segment_coverage_sec": round(coverage, 6),
        "selected_segment_bytes": downloaded_bytes,
    }


def clip_one(ffmpeg: Path, media_dir: Path, item: dict, force: bool) -> dict:
    pilot_id = item["pilot_id"]
    destination = media_dir / f"{pilot_id}.mp4"
    if destination.exists() and destination.stat().st_size > 100_000 and not force:
        return {
            "pilot_id": pilot_id,
            "status": "existing",
            "path": str(destination.relative_to(HERE)),
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
        }

    media_dir.mkdir(parents=True, exist_ok=True)
    temporary = media_dir / f"{pilot_id}.part.mp4"
    trimmed_input = media_dir / f"{pilot_id}.trim.ts"
    if temporary.exists():
        temporary.unlink()
    if trimmed_input.exists():
        trimmed_input.unlink()
    temporal = {}
    try:
        trimmed_input, temporal = build_trimmed_transport_stream(item, media_dir)
        command = [
            str(ffmpeg),
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(trimmed_input),
            "-ss",
            str(temporal["local_seek_sec"]),
            "-t",
            str(temporal["output_duration_sec"]),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-sn",
            "-dn",
            "-vf",
            "scale=-2:360:flags=lanczos,fps=12",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "25",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "80k",
            "-movflags",
            "+faststart",
            str(temporary),
        ]
        run = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=420,
        )
    except Exception as exc:
        run = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if trimmed_input.exists():
            trimmed_input.unlink()
    if run.returncode or not temporary.exists() or temporary.stat().st_size <= 100_000:
        if temporary.exists():
            temporary.unlink()
        return {
            "pilot_id": pilot_id,
            "status": "failed",
            "error": (run.stderr or run.stdout or "ffmpeg produced no usable file")[-1000:],
        }
    os.replace(temporary, destination)
    return {
        "pilot_id": pilot_id,
        "status": "downloaded",
        "path": str(destination.relative_to(HERE)),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "source_url": item["source_url"],
        "media_url": item["media_url"],
        "start_sec": item["start_sec"],
        "duration_sec": temporal["output_duration_sec"],
        **temporal,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--media-dir", type=Path, default=MEDIA)
    parser.add_argument("--receipts", type=Path, default=RECEIPTS)
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)
    if not 1 <= args.jobs <= 3:
        raise ValueError("--jobs must be from 1 to 3")

    manifest_path = args.manifest.resolve()
    media_dir = args.media_dir.resolve()
    receipts_path = args.receipts.resolve()
    document = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = document["items"]
    if args.ids:
        selected = set(args.ids)
        items = [item for item in items if item["pilot_id"] in selected]
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                clip_one, args.ffmpeg, media_dir, item, args.force
            ): item["pilot_id"]
            for item in items
        }
        for future in concurrent.futures.as_completed(futures):
            receipt = future.result()
            receipts.append(receipt)
            with PRINT_LOCK:
                print(json.dumps(receipt, ensure_ascii=False), flush=True)
    receipts.sort(key=lambda row: row["pilot_id"])
    receipts_path.write_text(
        json.dumps(
            {
                "schema": "gemini-interview-av-media-receipts-v2",
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "ffmpeg": str(args.ffmpeg),
                "items": receipts,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    failed = sum(row["status"] == "failed" for row in receipts)
    print(
        json.dumps(
            {
                "requested": len(items),
                "ready": len(items) - failed,
                "failed": failed,
                "receipt": str(receipts_path),
            }
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
