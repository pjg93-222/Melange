"""Run one industry's FEC API collection across private SQLite key lanes.

The initialized source database is never modified until every company-cycle
task succeeds. Each company belongs to exactly one lane (the merge invariant),
all cycles for that company run sequentially in that lane, and lanes run in
parallel with one API key each. A failed lane is retried in a fresh R process;
remaining failures are then split into one fresh process per company-cycle.
Keys are supplied only through child-process environments and are never
written to manifests, receipts, command lines, or logs. On complete success,
the final deterministic merge writes the source database in place; on any
collection/recovery failure it remains untouched.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

from sqlite_snapshot import create_snapshot, verify_database


SUPPORTED_CYCLES = (2022, 2024, 2026)
MERGE_ATTACHMENT_LIMIT = 10
DEFAULT_MEMORY_PER_LANE_MB = 640
DEFAULT_MEMORY_RESERVE_MB = 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(f".{path.name}.{os.getpid()}.pending")
    pending.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def split_keys(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[\r\n,;|]+", value)
        if item.strip()
    ]


def discover_keys(keys_file: Path | None, environment: dict[str, str]) -> list[str]:
    values: list[str] = []
    if keys_file is not None:
        for line in keys_file.read_text(encoding="utf-8-sig").splitlines():
            clean = line.strip()
            if clean and not clean.startswith("#"):
                values.extend(split_keys(clean))
    values.extend(split_keys(environment.get("FEC_API_KEYS", "")))
    single = environment.get("FEC_API_KEY", "").strip()
    if single:
        values.append(single)
    numbered = sorted(
        (
            (int(match.group(1)), value.strip())
            for name, value in environment.items()
            if (match := re.fullmatch(r"FEC_API_KEY_(\d+)", name))
            and value.strip()
        ),
        key=lambda item: item[0],
    )
    values.extend(value for _, value in numbered)
    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    if not unique:
        raise RuntimeError(
            "No FEC API keys were found. Set FEC_API_KEY, set delimiter-separated "
            "FEC_API_KEYS, or pass --keys-file. Key values are never logged."
        )
    return unique


def key_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def available_memory_bytes() -> int:
    if sys.platform == "win32":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [
                ("length", ctypes.c_ulong),
                ("memory_load", ctypes.c_ulong),
                ("total_physical", ctypes.c_ulonglong),
                ("available_physical", ctypes.c_ulonglong),
                ("total_page_file", ctypes.c_ulonglong),
                ("available_page_file", ctypes.c_ulonglong),
                ("total_virtual", ctypes.c_ulonglong),
                ("available_virtual", ctypes.c_ulonglong),
                ("available_extended_virtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatus()
        status.length = ctypes.sizeof(MemoryStatus)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return int(status.available_physical)
    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        available_pages = os.sysconf("SC_AVPHYS_PAGES")
        return int(page_size * available_pages)
    except (AttributeError, OSError, ValueError):
        return 0


def parse_cycles(value: str) -> tuple[int, ...]:
    labels = [item.strip() for item in re.split(r"[,|]+", value) if item.strip()]
    cycle_map = {
        "2021-2022": 2022,
        "2022": 2022,
        "2023-2024": 2024,
        "2024": 2024,
        "2025-2026": 2026,
        "2026": 2026,
    }
    unknown = [label for label in labels if label not in cycle_map]
    if not labels or unknown:
        raise argparse.ArgumentTypeError(
            "cycles must be a delimited subset of 2022, 2024, 2026 "
            f"(invalid: {','.join(unknown)})"
        )
    return tuple(sorted({cycle_map[label] for label in labels}))


def database_companies(database: Path, industry: str) -> list[tuple[str, int]]:
    connection = sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro",
        uri=True,
        timeout=30,
    )
    try:
        rows = list(
            connection.execute(
                """
                SELECT company, COUNT(*) AS variants
                FROM companies
                WHERE industry=?
                GROUP BY company
                ORDER BY company COLLATE NOCASE, company
                """,
                (industry,),
            )
        )
    finally:
        connection.close()
    if not rows:
        raise RuntimeError(
            f"No companies were found for industry {industry!r} in {database}."
        )
    return [(str(company), int(variants)) for company, variants in rows]


def company_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "company"


def task_id(company: str, cycle: int) -> str:
    return f"{company_slug(company)}-{cycle}"


def resource_cap(
    *,
    key_count: int,
    company_count: int,
    requested_parallel: int,
    memory_per_lane_mb: int,
    memory_reserve_mb: int,
) -> dict[str, int]:
    cpu_count = max(1, os.cpu_count() or 1)
    available = available_memory_bytes()
    available_mb = available // (1024 * 1024) if available else 0
    memory_cap = (
        max(1, (available_mb - memory_reserve_mb) // memory_per_lane_mb)
        if available_mb
        else 1
    )
    requested = requested_parallel if requested_parallel > 0 else MERGE_ATTACHMENT_LIMIT
    cap = max(
        1,
        min(
            requested,
            key_count,
            company_count,
            cpu_count,
            memory_cap,
            MERGE_ATTACHMENT_LIMIT,
        ),
    )
    return {
        "requested_parallel": requested_parallel,
        "logical_cpu": cpu_count,
        "available_memory_mb": int(available_mb),
        "memory_per_lane_mb": memory_per_lane_mb,
        "memory_reserve_mb": memory_reserve_mb,
        "memory_lane_cap": int(memory_cap),
        "key_cap": key_count,
        "company_cap": company_count,
        "sqlite_merge_cap": MERGE_ATTACHMENT_LIMIT,
        "active_lane_cap": cap,
    }


def schedule_companies(
    companies: Sequence[tuple[str, int]],
    cycles: Sequence[int],
    lane_count: int,
) -> list[dict[str, Any]]:
    lanes = [
        {"lane": index + 1, "weight": 0, "companies": [], "tasks": []}
        for index in range(lane_count)
    ]
    ordered = sorted(
        companies,
        key=lambda item: (-item[1], item[0].upper(), item[0]),
    )
    for company, variants in ordered:
        lane = min(lanes, key=lambda item: (item["weight"], item["lane"]))
        lane["companies"].append(company)
        lane["weight"] += max(1, variants) * len(cycles)
    for lane in lanes:
        lane["companies"].sort(key=lambda value: (value.upper(), value))
        lane["tasks"] = [
            {
                "task_id": task_id(company, cycle),
                "company": company,
                "cycle": int(cycle),
            }
            for company in lane["companies"]
            for cycle in sorted(cycles)
        ]
    return lanes


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def last_nonempty_log_line(path: Path, tail_bytes: int = 64 * 1024) -> str:
    if not path.is_file():
        return ""
    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        size = stream.tell()
        stream.seek(max(0, size - tail_bytes), os.SEEK_SET)
        tail = stream.read().decode("utf-8", errors="replace")
    lines = [line.strip() for line in tail.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def failed_tasks(receipt: dict[str, Any], fallback: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    tasks = receipt.get("tasks")
    if not isinstance(tasks, list):
        return list(fallback)
    failed = [
        {
            "task_id": str(item["task_id"]),
            "company": str(item["company"]),
            "cycle": int(item["cycle"]),
        }
        for item in tasks
        if item.get("status") != "succeeded"
    ]
    return failed


@dataclass(frozen=True)
class LaneRun:
    lane: int
    database: Path
    assignments: Path
    receipt: Path
    state: Path
    log: Path
    key: str
    key_id: str
    tasks: tuple[dict[str, Any], ...]
    attempt: int


def execute_lane(
    lane_run: LaneRun,
    *,
    rscript_path: Path,
    lane_script: Path,
    r_library_path: Path | None,
    concurrency: int,
    sqlite_cache_mb: int,
    budget_database: Path,
) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["FEC_API_KEY"] = lane_run.key
    environment.pop("FEC_API_KEYS", None)
    for name in list(environment):
        if re.fullmatch(r"FEC_API_KEY_\d+", name):
            environment.pop(name, None)
    environment["MENTAT_LANE_STATUS_PATH"] = str(lane_run.state)
    environment["MENTAT_SQLITE_CACHE_MB"] = str(sqlite_cache_mb)
    environment["MENTAT_API_BUDGET_DB"] = str(budget_database)
    environment["MENTAT_API_BUDGET_ID"] = (
        f"openfec:sha256:{lane_run.key_id}"
    )
    if r_library_path is not None:
        environment["R_LIBS_USER"] = str(r_library_path)
    command = [
        str(rscript_path),
        str(lane_script),
        str(lane_run.database),
        read_json(lane_run.assignments)["industry"],
        str(lane_run.assignments),
        str(lane_run.receipt),
        lane_run.key_id,
        str(concurrency),
    ]
    started_wall = utc_now()
    started = time.monotonic()
    lane_run.log.parent.mkdir(parents=True, exist_ok=True)
    with lane_run.log.open("a", encoding="utf-8", errors="replace") as log:
        log.write(
            f"\n[{utc_now()}] lane={lane_run.lane} attempt={lane_run.attempt} "
            f"tasks={len(lane_run.tasks)} key_id={lane_run.key_id}\n"
        )
        log.flush()
        process = subprocess.run(
            command,
            cwd=str(lane_script.parents[2]),
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    elapsed = round(time.monotonic() - started, 3)
    last_log_line = last_nonempty_log_line(lane_run.log)
    receipt: dict[str, Any] = {}
    if lane_run.receipt.is_file():
        try:
            receipt = read_json(lane_run.receipt)
        except (OSError, ValueError):
            receipt = {}
    state = lane_state(lane_run.state)
    received_tasks = receipt.get("tasks")
    if not isinstance(received_tasks, list):
        received_tasks = state.get("tasks", [])
    latest_tasks = {
        str(task.get("task_id", "")): dict(task)
        for task in received_tasks
        if isinstance(task, dict) and task.get("task_id")
    }
    for task in lane_run.tasks:
        identifier = str(task["task_id"])
        if identifier in latest_tasks:
            continue
        latest_tasks[identifier] = {
            **task,
            "status": "failed",
            "wall_clock_seconds": elapsed,
            "error": (
                f"Managed Rscript exited with code {int(process.returncode)} "
                "before producing a task receipt."
            ),
        }
    normalized_tasks = [
        latest_tasks[str(task["task_id"])]
        for task in lane_run.tasks
    ]
    failed_count = sum(
        1 for task in normalized_tasks if task.get("status") != "succeeded"
    )
    receipt.update(
        {
            "status": "failed" if failed_count else "succeeded",
            "task_count": len(normalized_tasks),
            "succeeded": len(normalized_tasks) - failed_count,
            "failed": failed_count,
            "wall_clock_seconds": elapsed,
            "exit_code": int(process.returncode),
            "last_log_line": last_log_line,
            "tasks": normalized_tasks,
        }
    )
    if process.returncode and not receipt.get("error"):
        receipt["error"] = (
            f"Managed Rscript exited with code {int(process.returncode)}."
        )
    atomic_json(lane_run.receipt, receipt)
    invocation_receipt = lane_run.receipt.with_name(
        f"{lane_run.receipt.stem}.invocation.json"
    )
    invocation = {
        "lane": lane_run.lane,
        "attempt": lane_run.attempt,
        "started_at": started_wall,
        "ended_at": utc_now(),
        "exit_code": int(process.returncode),
        "wall_clock_seconds": elapsed,
        "last_log_line": last_log_line,
        "log_path": str(lane_run.log),
        "database": str(lane_run.database),
        "key_id": lane_run.key_id,
        "units": [
            {
                "task_id": str(task["task_id"]),
                "company": str(task["company"]),
                "cycle": int(task["cycle"]),
            }
            for task in lane_run.tasks
        ],
    }
    atomic_json(invocation_receipt, invocation)
    return {
        "lane": lane_run.lane,
        "attempt": lane_run.attempt,
        "exit_code": int(process.returncode),
        "wall_clock_seconds": elapsed,
        "last_log_line": last_log_line,
        "receipt_path": str(lane_run.receipt),
        "invocation_receipt_path": str(invocation_receipt),
        "state_path": str(lane_run.state),
        "log_path": str(lane_run.log),
        "database": str(lane_run.database),
        "key_id": lane_run.key_id,
        "units": invocation["units"],
        "receipt": receipt,
    }


def lane_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except (OSError, ValueError):
        return {}


def write_status(
    status_path: Path,
    *,
    run_id: str,
    industry: str,
    total: int,
    lane_runs: Sequence[LaneRun],
    stage: str,
    started_monotonic: float,
    final_failed: int | None = None,
) -> None:
    states = [lane_state(run.state) for run in lane_runs]
    latest_tasks: dict[str, dict[str, Any]] = {}
    for state in states:
        for task in state.get("tasks", []):
            identifier = str(task.get("task_id", ""))
            if identifier:
                latest_tasks[identifier] = task
    completed = len(latest_tasks)
    running_states = [
        state for state in states if state.get("status") == "running"
    ]
    failed = (
        final_failed
        if final_failed is not None
        else sum(
            1
            for task in latest_tasks.values()
            if task.get("status") != "succeeded"
        )
    )
    durations = [
        float(task.get("wall_clock_seconds", 0))
        for task in latest_tasks.values()
        if task.get("status") == "succeeded"
        and float(task.get("wall_clock_seconds", 0)) > 0
    ]
    remaining = max(0, total - completed)
    estimated = None
    if durations and remaining:
        active = max(1, len(running_states))
        estimated = round((sum(durations) / len(durations)) * remaining / active, 1)
    current = [
        {
            "lane": int(state.get("lane", 0)),
            "company": state.get("current_company"),
            "cycle": state.get("current_cycle"),
        }
        for state in running_states
        if state.get("current_company")
    ]
    atomic_json(
        status_path,
        {
            "run_id": run_id,
            "industry": industry,
            "status": stage,
            "updated_at": utc_now(),
            "elapsed_seconds": round(time.monotonic() - started_monotonic, 3),
            "completed": completed,
            "total": total,
            "running": len(running_states),
            "failed": int(failed),
            "estimated_remaining_seconds": estimated,
            "current": current,
        },
    )


def combine_task_results(
    plans: Sequence[dict[str, Any]],
    attempts: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    latest: dict[str, dict[str, Any]] = {}
    expected = {
        task["task_id"]: task
        for plan in plans
        for task in plan["tasks"]
    }
    for attempt in sorted(
        attempts,
        key=lambda item: (int(item["attempt"]), int(item["lane"])),
    ):
        for task in attempt.get("receipt", {}).get("tasks", []):
            latest[str(task.get("task_id", ""))] = dict(task)
    combined: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for identifier in sorted(expected):
        task = latest.get(
            identifier,
            {
                **expected[identifier],
                "status": "failed",
                "error": "No task receipt was produced.",
            },
        )
        combined.append(task)
        if task.get("status") != "succeeded":
            failed.append(task)
    return combined, failed


def receipt_attempt_number(path: Path) -> int:
    if path.name == "receipt.json":
        return 1
    recovery = re.fullmatch(
        r"receipt\.recovery-(\d+)(?:-[a-z0-9-]+)?\.json",
        path.name,
    )
    if recovery:
        return 1 + int(recovery.group(1))
    split = re.fullmatch(
        r"receipt\.split-(\d+)-[a-z0-9-]+\.json",
        path.name,
    )
    if split:
        return int(split.group(1))
    resume = re.fullmatch(r"receipt\.resume-(\d+)\.json", path.name)
    return int(resume.group(1)) if resume else 1


def existing_lane_attempts(lane_directory: Path, lane: int) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    for path in sorted(
        (
            path
            for path in lane_directory.glob("receipt*.json")
            if not path.name.endswith(".invocation.json")
        ),
        key=lambda item: (receipt_attempt_number(item), item.name),
    ):
        try:
            receipt = read_json(path)
        except (OSError, ValueError):
            continue
        attempts.append(
            {
                "lane": lane,
                "attempt": receipt_attempt_number(path),
                "exit_code": 0 if receipt.get("status") == "succeeded" else 2,
                "wall_clock_seconds": float(
                    receipt.get("wall_clock_seconds", 0)
                ),
                "receipt_path": str(path),
                "state_path": str(
                    path.with_name(path.name.replace("receipt", "status", 1))
                ),
                "log_path": str(lane_directory / "process.log"),
                "database": str(lane_directory / "mentat.db"),
                "key_id": str(receipt.get("key_id", "")),
                "receipt": receipt,
            }
        )
    return attempts


def latest_tasks_from_attempts(
    attempts: Sequence[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for attempt in sorted(
        attempts,
        key=lambda item: (int(item.get("attempt", 0)), int(item.get("lane", 0))),
    ):
        for task in attempt.get("receipt", {}).get("tasks", []):
            identifier = str(task.get("task_id", ""))
            if identifier:
                latest[identifier] = dict(task)
    return latest


def parse_arguments(arguments: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-database", type=Path, required=True)
    parser.add_argument("--industry", required=True)
    parser.add_argument("--cycles", type=parse_cycles, default=SUPPORTED_CYCLES)
    parser.add_argument("--run-directory", type=Path, required=True)
    parser.add_argument("--output-receipt", type=Path)
    parser.add_argument("--keys-file", type=Path)
    parser.add_argument("--max-parallel", type=int, default=0)
    parser.add_argument("--recovery-workers", type=int, default=1)
    parser.add_argument("--concurrency-per-key", type=int, default=8)
    parser.add_argument(
        "--rscript-path",
        type=Path,
        default=Path(r"C:\Program Files\R\R-4.6.0\bin\Rscript.exe"),
    )
    parser.add_argument("--r-library-path", type=Path)
    parser.add_argument(
        "--memory-per-lane-mb",
        type=int,
        default=DEFAULT_MEMORY_PER_LANE_MB,
    )
    parser.add_argument(
        "--memory-reserve-mb",
        type=int,
        default=DEFAULT_MEMORY_RESERVE_MB,
    )
    parser.add_argument("--sqlite-cache-mb", type=int, default=256)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reuse verified lane databases and run only non-success tasks.",
    )
    parser.add_argument(
        "--budget-database",
        type=Path,
        help=(
            "Persistent redacted per-key hourly-budget SQLite. Defaults to "
            "mentat/.cache/fec-api-budget.sqlite."
        ),
    )
    parsed = parser.parse_args(arguments)
    if parsed.max_parallel < 0:
        parser.error("--max-parallel must be zero (auto) or positive.")
    if parsed.recovery_workers != 1:
        parser.error("--recovery-workers must be 1; failures recover serially.")
    if parsed.concurrency_per_key < 1 or parsed.concurrency_per_key > 64:
        parser.error("--concurrency-per-key must be between 1 and 64.")
    if parsed.memory_per_lane_mb < 128:
        parser.error("--memory-per-lane-mb must be at least 128.")
    if parsed.memory_reserve_mb < 256:
        parser.error("--memory-reserve-mb must be at least 256.")
    if parsed.sqlite_cache_mb < 32 or parsed.sqlite_cache_mb > 2048:
        parser.error("--sqlite-cache-mb must be between 32 and 2048.")
    return parsed


def main(arguments: Sequence[str] | None = None) -> int:
    options = parse_arguments(sys.argv[1:] if arguments is None else arguments)
    source_database = options.source_database.resolve(strict=True)
    run_directory = options.run_directory.resolve(strict=False)
    run_directory.mkdir(parents=True, exist_ok=True)
    output_receipt = (
        options.output_receipt.resolve(strict=False)
        if options.output_receipt
        else run_directory / "receipt.json"
    )
    status_path = run_directory / "status.json"
    manifest_path = run_directory / "manifest.json"
    lane_script = Path(__file__).with_name("collect_api_lane.R").resolve(strict=True)
    merge_script = Path(__file__).with_name("merge_company_shards.py").resolve(
        strict=True
    )
    rscript_path = options.rscript_path.resolve(strict=True)
    r_library_path = (
        options.r_library_path.resolve(strict=True)
        if options.r_library_path
        else None
    )
    budget_database = (
        options.budget_database.resolve(strict=False)
        if options.budget_database
        else Path(__file__).resolve().parents[1]
        / ".cache"
        / "fec-api-budget.sqlite"
    )
    budget_database.parent.mkdir(parents=True, exist_ok=True)
    if options.keys_file is not None:
        options.keys_file = options.keys_file.resolve(strict=True)

    if manifest_path.is_file() and not options.resume:
        raise RuntimeError(
            "RunDirectory already contains a fanout manifest; refusing to "
            "recreate lane snapshots and lose checkpoints. Resume with: "
            f"{sys.executable} {Path(__file__).resolve()} "
            f"--source-database \"{source_database}\" "
            f"--industry \"{options.industry.strip()}\" "
            f"--cycles \"{'|'.join(map(str, options.cycles))}\" "
            f"--run-directory \"{run_directory}\" --resume"
        )
    if options.resume and not manifest_path.is_file():
        raise RuntimeError(
            f"--resume requires an existing manifest: {manifest_path}"
        )
    if options.resume and output_receipt.is_file():
        prior_final = read_json(output_receipt)
        if (
            prior_final.get("status") == "succeeded"
            and prior_final.get("merged") is True
        ):
            print(
                "MENTAT API FANOUT ALREADY COMPLETE "
                f"receipt={output_receipt}",
                flush=True,
            )
            return 0

    verify_database(source_database)
    keys = discover_keys(options.keys_file, dict(os.environ))
    companies = database_companies(source_database, options.industry.strip())
    resources = resource_cap(
        key_count=len(keys),
        company_count=len(companies),
        requested_parallel=options.max_parallel,
        memory_per_lane_mb=options.memory_per_lane_mb,
        memory_reserve_mb=options.memory_reserve_mb,
    )
    if options.resume:
        existing_manifest = read_json(manifest_path)
        if Path(existing_manifest["source_database"]).resolve() != source_database:
            raise RuntimeError("Resume source database does not match manifest.")
        if existing_manifest.get("industry") != options.industry.strip():
            raise RuntimeError("Resume industry does not match manifest.")
        if tuple(existing_manifest.get("cycles", [])) != tuple(options.cycles):
            raise RuntimeError("Resume cycles do not match manifest.")
        lane_count = int(existing_manifest["lane_count"])
        if len(keys) < lane_count:
            raise RuntimeError(
                f"Resume requires at least {lane_count} configured keys so "
                "existing lanes never share a key concurrently."
            )
        plans = [
            {
                "lane": int(lane["lane"]),
                "weight": 0,
                "companies": list(lane["companies"]),
                "tasks": list(lane["tasks"]),
            }
            for lane in existing_manifest["lanes"]
        ]
        plans.sort(key=lambda item: item["lane"])
        run_id = str(existing_manifest["run_id"])
    else:
        lane_count = resources["active_lane_cap"]
        plans = schedule_companies(companies, options.cycles, lane_count)
        run_id = f"{datetime.now().strftime('%Y%m%dT%H%M%S')}-{os.getpid()}"
    spare_keys = keys[lane_count:]
    started_wall = utc_now()
    started_monotonic = time.monotonic()
    all_lane_runs: list[LaneRun] = []
    primary_runs: list[LaneRun] = []
    merge_runs: list[LaneRun] = []
    attempts: list[dict[str, Any]] = []

    for index, plan in enumerate(plans):
        lane_number = int(plan["lane"])
        lane_directory = run_directory / "lanes" / f"lane-{lane_number:02d}"
        lane_directory.mkdir(parents=True, exist_ok=True)
        lane_database = lane_directory / "mentat.db"
        if options.resume:
            verify_database(lane_database)
        else:
            create_snapshot(source_database, lane_database)
        prior_attempts = (
            existing_lane_attempts(lane_directory, lane_number)
            if options.resume
            else []
        )
        attempts.extend(prior_attempts)
        latest_prior = latest_tasks_from_attempts(prior_attempts)
        pending_tasks = [
            task
            for task in plan["tasks"]
            if latest_prior.get(task["task_id"], {}).get("status") != "succeeded"
        ]
        resume_number = (
            max(
                (int(item["attempt"]) for item in prior_attempts),
                default=0,
            )
            + 1
        )
        assignment_path = lane_directory / (
            f"assignments.resume-{resume_number}.json"
            if options.resume
            else "assignments.json"
        )
        receipt_path = lane_directory / (
            f"receipt.resume-{resume_number}.json"
            if options.resume
            else "receipt.json"
        )
        state_path = lane_directory / (
            f"status.resume-{resume_number}.json"
            if options.resume
            else "status.json"
        )
        log_path = lane_directory / "process.log"
        if not options.resume or pending_tasks:
            atomic_json(
                assignment_path,
                {
                    "run_id": run_id,
                    "industry": options.industry.strip(),
                    "lane": lane_number,
                    "companies": plan["companies"],
                    "cycles": list(options.cycles),
                    "resume": bool(options.resume),
                    "tasks": pending_tasks if options.resume else plan["tasks"],
                },
            )
        merge_run = LaneRun(
            lane=lane_number,
            database=lane_database,
            assignments=assignment_path,
            receipt=receipt_path,
            state=state_path,
            log=log_path,
            key=keys[index],
            key_id=key_id(keys[index]),
            tasks=tuple(pending_tasks if options.resume else plan["tasks"]),
            attempt=resume_number if options.resume else 1,
        )
        merge_runs.append(merge_run)
        if prior_attempts:
            baseline_state = lane_directory / "status.resume-baseline.json"
            prior_tasks = list(latest_prior.values())
            atomic_json(
                baseline_state,
                {
                    "status": "checkpointed",
                    "lane": lane_number,
                    "completed": len(prior_tasks),
                    "total": len(plan["tasks"]),
                    "failed": sum(
                        1
                        for task in prior_tasks
                        if task.get("status") != "succeeded"
                    ),
                    "current_company": None,
                    "current_cycle": None,
                    "tasks": prior_tasks,
                },
            )
            all_lane_runs.append(
                LaneRun(
                    lane=lane_number,
                    database=lane_database,
                    assignments=assignment_path,
                    receipt=receipt_path,
                    state=baseline_state,
                    log=log_path,
                    key="",
                    key_id="",
                    tasks=tuple(),
                    attempt=0,
                )
            )
        if merge_run.tasks:
            primary_runs.append(merge_run)
            all_lane_runs.append(merge_run)

    task_total = sum(len(plan["tasks"]) for plan in plans)
    if not options.resume:
        atomic_json(
            manifest_path,
            {
            "run_id": run_id,
            "industry": options.industry.strip(),
            "source_database": str(source_database),
            "cycles": list(options.cycles),
            "started_at": started_wall,
            "task_count": task_total,
            "company_count": len(companies),
            "configured_key_count": len(keys),
            "spare_key_count": len(spare_keys),
            "lane_count": lane_count,
            "resource_cap": resources,
            "concurrency_per_key": options.concurrency_per_key,
            "recovery_workers": options.recovery_workers,
            "recovery_ladder": [
                "primary_lane",
                "fresh_lane_retry",
                "fresh_company_cycle_split",
            ],
            "runtimes": {
                "python_path": str(Path(sys.executable).resolve()),
                "rscript_path": str(rscript_path),
                "r_library_path": (
                    str(r_library_path) if r_library_path else None
                ),
            },
            "budget_database": str(budget_database),
            "lanes": [
                {
                    "lane": run.lane,
                    "key_id": run.key_id,
                    "companies": plans[run.lane - 1]["companies"],
                    "tasks": plans[run.lane - 1]["tasks"],
                    "database": str(run.database),
                    "receipt": str(run.receipt),
                    "state": str(run.state),
                    "log": str(run.log),
                }
                for run in merge_runs
            ],
            },
        )
    print(
        "MENTAT API FANOUT "
        f"industry={options.industry.strip()} tasks={task_total} "
        f"keys={len(keys)} lanes={lane_count} cpu_cap={resources['logical_cpu']} "
        f"memory_cap={resources['memory_lane_cap']} "
        f"available_memory_mb={resources['available_memory_mb']} "
        f"merge_cap={resources['sqlite_merge_cap']} "
        f"resume={options.resume} pending_tasks="
        f"{sum(len(run.tasks) for run in primary_runs)}",
        flush=True,
    )

    recovery_futures: dict[concurrent.futures.Future[dict[str, Any]], LaneRun] = {}
    recovery_results: list[tuple[LaneRun, dict[str, Any]]] = []
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=lane_count,
        thread_name_prefix="mentat-api-primary",
    ) as primary_pool, concurrent.futures.ThreadPoolExecutor(
        max_workers=options.recovery_workers,
        thread_name_prefix="mentat-api-recovery",
    ) as recovery_pool:
        primary_futures = {
            primary_pool.submit(
                execute_lane,
                run,
                rscript_path=rscript_path,
                lane_script=lane_script,
                r_library_path=r_library_path,
                concurrency=options.concurrency_per_key,
                sqlite_cache_mb=options.sqlite_cache_mb,
                budget_database=budget_database,
            ): run
            for run in primary_runs
        }
        pending: set[concurrent.futures.Future[dict[str, Any]]] = set(
            primary_futures
        )
        while pending:
            write_status(
                status_path,
                run_id=run_id,
                industry=options.industry.strip(),
                total=task_total,
                lane_runs=all_lane_runs,
                stage="collecting",
                started_monotonic=started_monotonic,
            )
            done, pending = concurrent.futures.wait(
                pending,
                timeout=1,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                run = primary_futures[future]
                attempt = future.result()
                attempts.append(attempt)
                retry_tasks = failed_tasks(attempt["receipt"], run.tasks)
                if not retry_tasks:
                    continue
                recovery_assignment = run.assignments.with_name(
                    f"assignments.recovery-{run.attempt}.json"
                )
                recovery_receipt = run.receipt.with_name(
                    f"receipt.recovery-{run.attempt}.json"
                )
                recovery_state = run.state.with_name(
                    f"status.recovery-{run.attempt}.json"
                )
                atomic_json(
                    recovery_assignment,
                    {
                        "run_id": run_id,
                        "industry": options.industry.strip(),
                        "lane": run.lane,
                        "recovery_attempt": run.attempt,
                        "tasks": retry_tasks,
                    },
                )
                recovery_run = LaneRun(
                    lane=run.lane,
                    database=run.database,
                    assignments=recovery_assignment,
                    receipt=recovery_receipt,
                    state=recovery_state,
                    log=run.log,
                    key=(
                        spare_keys[(run.lane - 1) % len(spare_keys)]
                        if spare_keys
                        else run.key
                    ),
                    key_id=key_id(
                        spare_keys[(run.lane - 1) % len(spare_keys)]
                        if spare_keys
                        else run.key
                    ),
                    tasks=tuple(retry_tasks),
                    attempt=run.attempt + 1,
                )
                all_lane_runs.append(recovery_run)
                recovery_future = recovery_pool.submit(
                    execute_lane,
                    recovery_run,
                    rscript_path=rscript_path,
                    lane_script=lane_script,
                    r_library_path=r_library_path,
                    concurrency=options.concurrency_per_key,
                    sqlite_cache_mb=options.sqlite_cache_mb,
                    budget_database=budget_database,
                )
                recovery_futures[recovery_future] = recovery_run

        recovery_pending = set(recovery_futures)
        while recovery_pending:
            write_status(
                status_path,
                run_id=run_id,
                industry=options.industry.strip(),
                total=task_total,
                lane_runs=all_lane_runs,
                stage="recovering",
                started_monotonic=started_monotonic,
            )
            done, recovery_pending = concurrent.futures.wait(
                recovery_pending,
                timeout=1,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                recovery_run = recovery_futures[future]
                recovery_result = future.result()
                attempts.append(recovery_result)
                recovery_results.append((recovery_run, recovery_result))

        split_futures: dict[
            concurrent.futures.Future[dict[str, Any]], LaneRun
        ] = {}
        for recovery_run, recovery_result in recovery_results:
            split_tasks = failed_tasks(
                recovery_result["receipt"],
                recovery_run.tasks,
            )
            for task in split_tasks:
                identifier = str(task["task_id"])
                token = re.sub(r"[^a-z0-9-]+", "-", identifier.lower()).strip(
                    "-"
                )
                if not token:
                    token = f"unit-{recovery_run.lane}"
                split_attempt = recovery_run.attempt + 1
                split_assignment = recovery_run.assignments.with_name(
                    f"assignments.split-{split_attempt}-{token}.json"
                )
                split_receipt = recovery_run.receipt.with_name(
                    f"receipt.split-{split_attempt}-{token}.json"
                )
                split_state = recovery_run.state.with_name(
                    f"status.split-{split_attempt}-{token}.json"
                )
                atomic_json(
                    split_assignment,
                    {
                        "run_id": run_id,
                        "industry": options.industry.strip(),
                        "lane": recovery_run.lane,
                        "split_attempt": split_attempt,
                        "parent_attempt": recovery_run.attempt,
                        "tasks": [task],
                    },
                )
                split_run = LaneRun(
                    lane=recovery_run.lane,
                    database=recovery_run.database,
                    assignments=split_assignment,
                    receipt=split_receipt,
                    state=split_state,
                    log=recovery_run.log,
                    key=recovery_run.key,
                    key_id=recovery_run.key_id,
                    tasks=(task,),
                    attempt=split_attempt,
                )
                all_lane_runs.append(split_run)
                split_future = recovery_pool.submit(
                    execute_lane,
                    split_run,
                    rscript_path=rscript_path,
                    lane_script=lane_script,
                    r_library_path=r_library_path,
                    concurrency=options.concurrency_per_key,
                    sqlite_cache_mb=options.sqlite_cache_mb,
                    budget_database=budget_database,
                )
                split_futures[split_future] = split_run

        split_pending = set(split_futures)
        while split_pending:
            write_status(
                status_path,
                run_id=run_id,
                industry=options.industry.strip(),
                total=task_total,
                lane_runs=all_lane_runs,
                stage="splitting",
                started_monotonic=started_monotonic,
            )
            done, split_pending = concurrent.futures.wait(
                split_pending,
                timeout=1,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            for future in done:
                attempts.append(future.result())

    combined_tasks, final_failed = combine_task_results(plans, attempts)
    merge_log = run_directory / "merge.log"
    merge_result: dict[str, Any] = {
        "attempted": False,
        "exit_code": None,
        "log": str(merge_log),
    }
    merged = False
    if not final_failed:
        write_status(
            status_path,
            run_id=run_id,
            industry=options.industry.strip(),
            total=task_total,
            lane_runs=all_lane_runs,
            stage="merging",
            started_monotonic=started_monotonic,
            final_failed=0,
        )
        merge_command = [
            sys.executable,
            str(merge_script),
            str(source_database),
            *[
                f"{run.database}::{'|'.join(plans[run.lane - 1]['companies'])}"
                for run in merge_runs
            ],
        ]
        merge_started = time.monotonic()
        with merge_log.open("w", encoding="utf-8", errors="replace") as log:
            merge_process = subprocess.run(
                merge_command,
                cwd=str(merge_script.parents[2]),
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
            )
        merge_result = {
            "attempted": True,
            "exit_code": int(merge_process.returncode),
            "wall_clock_seconds": round(time.monotonic() - merge_started, 3),
            "log": str(merge_log),
        }
        if merge_process.returncode == 0:
            verify_database(source_database)
            merged = True
        else:
            final_failed = [
                {
                    "task_id": "merge",
                    "status": "failed",
                    "error": "Deterministic shard merge failed; see merge log.",
                }
            ]

    final_status = "succeeded" if merged and not final_failed else "failed"
    ended_wall = utc_now()
    receipt = {
        "run_id": run_id,
        "status": final_status,
        "industry": options.industry.strip(),
        "source_database": str(source_database),
        "run_directory": str(run_directory),
        "manifest": str(manifest_path),
        "status_path": str(status_path),
        "started_at": started_wall,
        "ended_at": ended_wall,
        "wall_clock_seconds": round(time.monotonic() - started_monotonic, 3),
        "company_count": len(companies),
        "task_count": task_total,
        "succeeded": task_total - len(final_failed),
        "failed": len(final_failed),
        "merged": merged,
        "configured_key_count": len(keys),
        "spare_key_count": len(spare_keys),
        "lane_count": lane_count,
        "resource_cap": resources,
        "recovery_ladder": [
            "primary_lane",
            "fresh_lane_retry",
            "fresh_company_cycle_split",
        ],
        "runtimes": {
            "python_path": str(Path(sys.executable).resolve()),
            "rscript_path": str(rscript_path),
            "r_library_path": (
                str(r_library_path) if r_library_path else None
            ),
        },
        "budget_database": str(budget_database),
        "tasks": combined_tasks,
        "failures": final_failed,
        "lane_attempts": [
            {
                key: value
                for key, value in attempt.items()
                if key != "receipt"
            }
            for attempt in attempts
        ],
        "merge": merge_result,
    }
    atomic_json(output_receipt, receipt)
    write_status(
        status_path,
        run_id=run_id,
        industry=options.industry.strip(),
        total=task_total,
        lane_runs=all_lane_runs,
        stage=final_status,
        started_monotonic=started_monotonic,
        final_failed=len(final_failed),
    )
    print(
        f"MENTAT API FANOUT {final_status.upper()} "
        f"succeeded={receipt['succeeded']}/{task_total} merged={merged} "
        f"wall={receipt['wall_clock_seconds']:.3f}s receipt={output_receipt}",
        flush=True,
    )
    return 0 if final_status == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
