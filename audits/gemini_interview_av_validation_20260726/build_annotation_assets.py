#!/usr/bin/env python3
"""Build visually timestamped 4x4 storyboards for admitted validation clips."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "validation_manifest_150.json"
MEDIA = HERE / "media"
STORYBOARDS = HERE / "storyboards"
DEFAULT_FFMPEG = Path(
    r"C:\Users\pgoff\AppData\Local\Programs\Python\Python312"
    r"\Lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
)


def build_one(ffmpeg: Path, item: dict, force: bool) -> dict:
    case_id = item["case_id"]
    source = MEDIA / f"{case_id}.mp4"
    destination = STORYBOARDS / f"{case_id}.jpg"
    if not source.is_file():
        return {"case_id": case_id, "status": "failed", "error": "media_missing"}
    if destination.is_file() and not force:
        return {
            "case_id": case_id,
            "status": "existing",
            "path": str(destination.relative_to(HERE)),
        }
    duration = float(item["duration_sec"])
    sample_count = 16
    fps = sample_count / max(duration, 0.001)
    try:
        with tempfile.TemporaryDirectory(prefix=f"{case_id}_", dir=HERE) as tmp:
            pattern = Path(tmp) / "frame_%03d.jpg"
            command = [
                str(ffmpeg),
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vf",
                (
                    f"fps={fps:.9f},"
                    "scale=320:180:force_original_aspect_ratio=decrease,"
                    "pad=320:180:(ow-iw)/2:(oh-ih)/2:black"
                ),
                "-frames:v",
                str(sample_count),
                "-q:v",
                "3",
                str(pattern),
            ]
            completed = subprocess.run(
                command, text=True, capture_output=True, timeout=240
            )
            if completed.returncode:
                raise RuntimeError((completed.stderr or completed.stdout)[-1500:])
            frames = sorted(Path(tmp).glob("frame_*.jpg"))
            if len(frames) < 12:
                raise RuntimeError(f"only {len(frames)} storyboard frames")
            canvas = Image.new("RGB", (1312, 800), "#101820")
            draw = ImageDraw.Draw(canvas)
            font = ImageFont.load_default(size=18)
            small = ImageFont.load_default(size=15)
            draw.text((12, 8), f"{case_id}  |  target {item['target_start_sec_in_clip']:.1f}s-"
                      f"{item['target_end_sec_in_clip']:.1f}s", fill="white", font=font)
            for index in range(sample_count):
                frame = Image.open(frames[min(index, len(frames) - 1)]).convert("RGB")
                col = index % 4
                row = index // 4
                x = 8 + col * 328
                y = 40 + row * 188
                canvas.paste(frame, (x, y))
                midpoint = min(duration, (index + 0.5) * duration / sample_count)
                label = f"{midpoint:05.1f}s"
                draw.rectangle((x + 4, y + 4, x + 74, y + 27), fill="#000000")
                draw.text((x + 9, y + 7), label, fill="#FFFFFF", font=small)
            STORYBOARDS.mkdir(parents=True, exist_ok=True)
            canvas.save(destination, "JPEG", quality=88, optimize=True)
        return {
            "case_id": case_id,
            "status": "built",
            "path": str(destination.relative_to(HERE)),
            "bytes": destination.stat().st_size,
        }
    except Exception as exc:
        return {
            "case_id": case_id,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ffmpeg", type=Path, default=DEFAULT_FFMPEG)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if not args.ffmpeg.is_file():
        raise FileNotFoundError(args.ffmpeg)
    if not 1 <= args.jobs <= 4:
        raise ValueError("--jobs must be 1-4")
    document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    STORYBOARDS.mkdir(parents=True, exist_ok=True)
    receipts = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [
            pool.submit(build_one, args.ffmpeg, item, args.force)
            for item in document["items"]
        ]
        for future in concurrent.futures.as_completed(futures):
            receipt = future.result()
            receipts.append(receipt)
            print(json.dumps(receipt), flush=True)
    failed = [row for row in receipts if row["status"] == "failed"]
    print(json.dumps({"built": len(receipts) - len(failed), "failed": len(failed)}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
