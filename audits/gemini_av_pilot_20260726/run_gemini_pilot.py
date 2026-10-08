"""Run the frozen 30-item pilot through Google Antigravity/Gemini.

The script is resumable. Each invocation is a fresh, blinded conversation and
receives one neutral MP4 plus a five-person candidate set.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import subprocess
import threading
import time
from pathlib import Path


HERE = Path(__file__).resolve().parent
TASKS = HERE / "blinded_tasks.json"
RESULTS = HERE / "results"
RAW = HERE / "raw"
DEFAULT_AGY = Path(r"C:\Users\pgoff\AppData\Local\agy\bin\agy.exe")
PRINT_LOCK = threading.Lock()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def parse_model_json(output: str) -> dict:
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
        raise ValueError("Gemini response is not a JSON object")
    return value


def prompt_for(task: dict) -> str:
    candidate_json = json.dumps(task["candidate_set"], ensure_ascii=False)
    absolute_media = HERE / task["media_path"]
    return f"""Perform a blinded research evaluation using actual multimodal
analysis of this exact local MP4: {absolute_media}

The visual track is intentionally a blank, label-free frame wrapping the
original audio. Invoke the media-capable file reader and directly inspect the
audio track. Do not use shell commands, web search, source metadata, the
filename, or prior knowledge from this workspace.

The five candidate names are:
{candidate_json}

The recording duration is approximately {task['duration_sec']:.3f} seconds.
Every evidence timestamp must be between zero and that duration.

For the dominant congressional speaker, choose exactly one candidate only when
the audio supports it; otherwise abstain. The recording may contain an
interviewer, moderator, or multiple speakers. Identity matching is a research
test and must not relabel any recording.

Report only observable delivery. Do not infer Big Five traits, personality,
mental state, emotion as an internal state, demographics, health, protected
attributes, honesty, intent, or ideology. Use not_observable where the audio
does not support a field. Give short timestamped observations grounded in the
audio; do not reveal chain-of-thought.

Return only one valid compact JSON object with exactly this schema:
{{
  "pilot_id": "{task['pilot_id']}",
  "media_processed": true,
  "modality": "audio_wrapped_mp4",
  "estimated_speaker_count": 1,
  "dominant_speaker_fraction": 0.0,
  "candidate_choice": null,
  "identity_confidence": 0.0,
  "abstained": true,
  "observable_delivery": {{
    "pace": "not_observable",
    "pause_frequency": "not_observable",
    "disfluency_frequency": "not_observable",
    "prosodic_variability": "not_observable",
    "turn_competition": "not_observable",
    "response_directness": "not_observable"
  }},
  "evidence": [
    {{"timestamp_sec": 0.0, "observation": "short observable description"}}
  ],
  "transcript_excerpt": "maximum twenty words",
  "quality_flags": [],
  "error": null
}}

Categorical delivery values must be exactly low, medium, high, or
not_observable. dominant_speaker_fraction and identity_confidence must be
numbers from 0 to 1. candidate_choice must be one of the five supplied names or
null when abstained. If the media cannot be directly processed, set
media_processed false, abstained true, candidate_choice null, use
not_observable delivery values, and explain briefly in error."""


def run_one(
    agy: Path,
    model: str,
    effort: str,
    task: dict,
    retries: int,
    force: bool,
    results_dir: Path,
    raw_dir: Path,
) -> dict:
    pilot_id = task["pilot_id"]
    result_path = results_dir / f"{pilot_id}.json"
    if result_path.exists() and not force:
        try:
            existing = json.loads(result_path.read_text(encoding="utf-8"))
            if existing.get("pilot_id") == pilot_id:
                return {"pilot_id": pilot_id, "status": "skipped"}
        except Exception:
            pass

    prompt = prompt_for(task)
    absolute_media = (HERE / task["media_path"]).resolve()
    command = [
        str(agy),
        "--model",
        model,
        "--effort",
        effort,
        "--mode",
        "plan",
        "--add-dir",
        str(absolute_media.parent),
        "--print-timeout",
        "12m",
        "--print",
        prompt,
    ]
    last_error = ""
    for attempt in range(1, retries + 2):
        started = time.monotonic()
        run = subprocess.run(
            command,
            cwd=absolute_media.parent,
            text=True,
            capture_output=True,
            timeout=780,
        )
        elapsed = round(time.monotonic() - started, 3)
        raw_document = {
            "pilot_id": pilot_id,
            "model": model,
            "effort": effort,
            "attempt": attempt,
            "returncode": run.returncode,
            "elapsed_sec": elapsed,
            "stdout": run.stdout,
            "stderr": run.stderr,
        }
        atomic_text(
            raw_dir / f"{pilot_id}.attempt{attempt}.json",
            json.dumps(raw_document, indent=2, ensure_ascii=False) + "\n",
        )
        try:
            if run.returncode:
                raise RuntimeError(
                    f"agy exit {run.returncode}: {(run.stderr or run.stdout)[-500:]}"
                )
            result = parse_model_json(run.stdout)
            if result.get("pilot_id") != pilot_id:
                raise ValueError(
                    f"response pilot_id {result.get('pilot_id')!r} != {pilot_id}"
                )
            result["_receipt"] = {
                "model": model,
                "effort": effort,
                "attempt": attempt,
                "elapsed_sec": elapsed,
                "media_sha256": task.get("media_sha256"),
                "workspace_scope": str(absolute_media.parent),
            }
            atomic_text(
                result_path,
                json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            )
            return {
                "pilot_id": pilot_id,
                "status": "completed",
                "elapsed_sec": elapsed,
            }
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt <= retries:
                time.sleep(min(10, attempt * 3))

    atomic_text(
        results_dir / f"{pilot_id}.error.json",
        json.dumps(
            {"pilot_id": pilot_id, "status": "failed", "error": last_error},
            indent=2,
        )
        + "\n",
    )
    return {"pilot_id": pilot_id, "status": "failed", "error": last_error}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agy", type=Path, default=DEFAULT_AGY)
    parser.add_argument("--model", default="gemini-3.1-pro-high")
    parser.add_argument("--effort", choices=("low", "medium", "high"), default="high")
    parser.add_argument("--jobs", type=int, default=2)
    parser.add_argument("--retries", type=int, default=1)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ids", nargs="*")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--results-dir", type=Path, default=RESULTS)
    parser.add_argument("--raw-dir", type=Path, default=RAW)
    args = parser.parse_args()
    if not args.agy.is_file():
        raise FileNotFoundError(args.agy)
    if args.jobs < 1 or args.jobs > 4:
        raise ValueError("--jobs must be from 1 to 4")

    document = json.loads(TASKS.read_text(encoding="utf-8"))
    tasks = document["items"]
    if args.ids:
        selected = set(args.ids)
        tasks = [task for task in tasks if task["pilot_id"] in selected]
    if args.limit is not None:
        tasks = tasks[: args.limit]

    args.results_dir.mkdir(parents=True, exist_ok=True)
    args.raw_dir.mkdir(parents=True, exist_ok=True)
    statuses = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = {
            pool.submit(
                run_one,
                args.agy,
                args.model,
                args.effort,
                task,
                args.retries,
                args.force,
                args.results_dir,
                args.raw_dir,
            ): task["pilot_id"]
            for task in tasks
        }
        for future in concurrent.futures.as_completed(futures):
            status = future.result()
            statuses.append(status)
            with PRINT_LOCK:
                print(json.dumps(status, ensure_ascii=False), flush=True)

    summary = {
        "requested": len(tasks),
        "completed": sum(row["status"] == "completed" for row in statuses),
        "skipped": sum(row["status"] == "skipped" for row in statuses),
        "failed": sum(row["status"] == "failed" for row in statuses),
        "model": args.model,
    }
    print(json.dumps(summary), flush=True)
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
