#!/usr/bin/env python3
"""Download and mux hash-pinned A/V clips for the 150-case validation tranche."""

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
import time
import urllib.parse
import urllib.request
from pathlib import Path


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "validation_manifest_150.json"
MEDIA = HERE / "media"
WORK = HERE / "media_work"
RECEIPTS = HERE / "media_receipts_150.json"
DEFAULT_FFMPEG = Path(
    r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
)
PRINT_LOCK = threading.Lock()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fetch(url: str, referer: str, attempts: int = 3) -> bytes:
    last_error = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": USER_AGENT, "Referer": referer},
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{url}: {type(last_error).__name__}: {last_error}")


def choose_video_rendition(master_url: str, text: str) -> tuple[str, str]:
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
        if not uri:
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
    _, _, url = min(candidates)
    return url, ""


def audio_rendition(master_url: str, text: str) -> str | None:
    match = re.search(
        r'#EXT-X-MEDIA:[^\n]*TYPE=AUDIO[^\n]*URI="([^"]+)"',
        text,
        flags=re.IGNORECASE,
    )
    return urllib.parse.urljoin(master_url, match.group(1)) if match else None


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
    for raw in text.splitlines():
        line = raw.strip()
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
        raise ValueError(f"{playlist_url}: no HLS segments")
    return segments


def select_window(
    segments: list[dict],
    requested_start: float,
    requested_duration: float,
) -> dict:
    cursor = 0.0
    start_index = None
    for index, segment in enumerate(segments):
        if cursor + segment["duration"] > requested_start:
            start_index = index
            break
        cursor += segment["duration"]
    if start_index is None:
        raise ValueError("requested start exceeds playlist")
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
        raise ValueError(f"coverage {coverage:.3f} < needed {needed:.3f}")
    return {
        "selected": selected,
        "segment_start_sec": round(cursor, 6),
        "local_seek_sec": round(local_seek, 6),
        "coverage_sec": round(coverage, 6),
    }


def download_segments(
    selected: list[dict],
    referer: str,
    destination: Path,
) -> dict:
    segment_receipts = []
    total = 0
    with destination.open("wb") as handle:
        for index, segment in enumerate(selected):
            if segment["key"] or segment["map"]:
                raise ValueError("encrypted or mapped HLS is unsupported")
            payload = fetch(segment["uri"], referer)
            handle.write(payload)
            total += len(payload)
            segment_receipts.append(
                {
                    "index": index,
                    "uri": segment["uri"],
                    "duration_sec": segment["duration"],
                    "bytes": len(payload),
                    "sha256": sha256_bytes(payload),
                }
            )
    return {
        "segment_count": len(segment_receipts),
        "downloaded_bytes": total,
        "segments": segment_receipts,
    }


def stream_inventory(ffmpeg: Path, media: Path) -> dict:
    completed = subprocess.run(
        [str(ffmpeg), "-hide_banner", "-i", str(media), "-f", "null", "-"],
        text=True,
        capture_output=True,
        timeout=180,
    )
    text = completed.stderr or completed.stdout
    return {
        "audio_stream": "Audio:" in text,
        "video_stream": "Video:" in text,
    }


def mux(
    ffmpeg: Path,
    video_input: Path,
    video_seek: float,
    audio_input: Path | None,
    audio_seek: float | None,
    duration: float,
    output: Path,
) -> None:
    command = [
        str(ffmpeg),
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(video_seek),
        "-i",
        str(video_input),
    ]
    if audio_input is not None:
        command.extend(
            ["-ss", str(audio_seek or 0.0), "-i", str(audio_input)]
        )
    command.extend(
        [
            "-t",
            str(duration),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0" if audio_input is not None else "0:a:0",
            "-sn",
            "-dn",
            "-vf",
            "scale=-2:360:flags=lanczos,fps=12,format=yuv420p",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "25",
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
    completed = subprocess.run(
        command, text=True, capture_output=True, timeout=420
    )
    if completed.returncode:
        raise RuntimeError((completed.stderr or completed.stdout)[-2000:])


def fetch_one(ffmpeg: Path, item: dict, force: bool) -> dict:
    case_id = item["case_id"]
    destination = MEDIA / f"{case_id}.mp4"
    if destination.is_file() and not force:
        streams = stream_inventory(ffmpeg, destination)
        if streams["audio_stream"] and streams["video_stream"]:
            return {
                "case_id": case_id,
                "status": "existing_verified",
                "path": str(destination.relative_to(HERE)),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "streams": streams,
            }
    MEDIA.mkdir(parents=True, exist_ok=True)
    WORK.mkdir(parents=True, exist_ok=True)
    video_input = WORK / f"{case_id}.video.part"
    audio_input = WORK / f"{case_id}.audio.part"
    temporary = WORK / f"{case_id}.output.part.mp4"
    for path in (video_input, audio_input, temporary):
        if path.exists():
            path.unlink()
    try:
        source_media_url = item["media_url"]
        master_url = source_media_url
        if source_media_url.endswith(".tsc.m3u8"):
            # C-SPAN pages currently advertise this mobile master for legacy
            # programs whose archived m3u8-N segment hosts return 403.
            master_url = (
                "https://iphone.c-spanvideo.org/m3u8/"
                f"program.{item['program_id']}.m3u8"
            )
        referer = item["source_url"]
        try:
            master_text = fetch(master_url, referer).decode("utf-8-sig")
        except RuntimeError:
            # Some legacy transcript metadata preserves a retired transport-
            # stream-control suffix. The equivalent public C-SPAN master
            # playlist omits ".tsc" and advertises muxed A/V renditions.
            if not master_url.endswith(".tsc.m3u8"):
                raise
            master_url = master_url.removesuffix(".tsc.m3u8") + ".m3u8"
            master_text = fetch(master_url, referer).decode("utf-8-sig")
        video_url, video_text = choose_video_rendition(master_url, master_text)
        if not video_text:
            video_text = fetch(video_url, referer).decode("utf-8-sig")
        requested_start = float(item["start_sec"])
        requested_duration = float(item["duration_sec"])
        video_window = select_window(
            parse_segments(video_url, video_text),
            requested_start,
            requested_duration,
        )
        video_download = download_segments(
            video_window["selected"], referer, video_input
        )
        audio_url = audio_rendition(master_url, master_text)
        audio_window = None
        audio_download = None
        if audio_url:
            audio_text = fetch(audio_url, referer).decode("utf-8-sig")
            audio_window = select_window(
                parse_segments(audio_url, audio_text),
                requested_start,
                requested_duration,
            )
            audio_download = download_segments(
                audio_window["selected"], referer, audio_input
            )
        mux(
            ffmpeg,
            video_input,
            video_window["local_seek_sec"],
            audio_input if audio_url else None,
            audio_window["local_seek_sec"] if audio_window else None,
            requested_duration,
            temporary,
        )
        streams = stream_inventory(ffmpeg, temporary)
        if not streams["audio_stream"] or not streams["video_stream"]:
            raise RuntimeError(f"output stream preflight failed: {streams}")
        os.replace(temporary, destination)
        return {
            "case_id": case_id,
            "status": "downloaded_verified",
            "path": str(destination.relative_to(HERE)),
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "streams": streams,
            "source_url": item["source_url"],
            "source_media_url": source_media_url,
            "master_url": master_url,
            "video_playlist_url": video_url,
            "audio_playlist_url": audio_url,
            "requested_start_sec": requested_start,
            "requested_duration_sec": requested_duration,
            "video_window": {
                key: value
                for key, value in video_window.items()
                if key != "selected"
            },
            "audio_window": (
                {
                    key: value
                    for key, value in audio_window.items()
                    if key != "selected"
                }
                if audio_window
                else None
            ),
            "video_download": video_download,
            "audio_download": audio_download,
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }
    finally:
        for path in (video_input, audio_input, temporary):
            if path.exists():
                path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--jobs", type=int, default=3)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)
    if not 1 <= args.jobs <= 4:
        raise ValueError("--jobs must be 1-4")
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    items = document["items"]
    if args.ids:
        wanted = set(args.ids)
        items = [item for item in items if item["case_id"] in wanted]
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(fetch_one, args.ffmpeg, item, args.force): item["case_id"]
            for item in items
        }
        for future in concurrent.futures.as_completed(futures):
            receipt = future.result()
            receipts.append(receipt)
            with PRINT_LOCK:
                print(json.dumps(receipt, ensure_ascii=False), flush=True)
    receipts.sort(key=lambda row: row["case_id"])
    output = {
        "schema": "interview-av-human-validation-media-receipts-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "manifest_sha256": sha256_file(MANIFEST),
        "ffmpeg": str(args.ffmpeg),
        "requested_count": len(items),
        "verified_count": sum(
            row["status"] in {"downloaded_verified", "existing_verified"}
            for row in receipts
        ),
        "failed_count": sum(row["status"] == "failed" for row in receipts),
        "items": receipts,
    }
    atomic_json(RECEIPTS, output)
    print(
        json.dumps(
            {
                key: value
                for key, value in output.items()
                if key != "items"
            },
            indent=2,
        )
    )
    return 1 if output["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
