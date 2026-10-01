"""Collect legislator X posts through headless Grok CLI batches."""

from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Callable, Sequence


MELANGE_ROOT = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")


def _resolve_repo_path(relative_name: str) -> Path:
    """Prefer the post-reorg data\\stance\\ home, fall back to the legacy root.

    The July 2026 reorg moved several live-tree JSON/JSONL artifacts under
    data\\stance\\. Existing collector state and command-line defaults were
    written against the pre-reorg root path, so resolve against whichever
    location is actually present, preferring the new one.
    """

    current = MELANGE_ROOT / "data" / "stance" / relative_name
    if current.exists():
        return current
    legacy = MELANGE_ROOT / relative_name
    if legacy.exists():
        return legacy
    # CollectorError is defined later in this module, so this early,
    # import-time resolver raises a builtin instead of forward-referencing it.
    raise FileNotFoundError(
        f"could not find {relative_name!r} at either "
        f"{current} or {legacy}"
    )


DEFAULT_HANDLES_FILE = _resolve_repo_path("legislators_social_media.json")
DEFAULT_CATALOG = _resolve_repo_path("x_catalog.jsonl")
DEFAULT_STATE_DIR = Path(
    os.environ.get(
        "LOCALAPPDATA",
        str(Path.home() / "AppData" / "Local"),
    )
) / "melange_x_collector"
GROK_BIN_DIR = Path(r"C:\Users\pgoff\.grok\bin")
DEFAULT_GROK_COMMAND = (str(GROK_BIN_DIR / "grok.exe"),)
MAX_QUERY_CHARS = 480
MAX_HANDLES_PER_BATCH = 5
INTER_BATCH_SLEEP_SECONDS = 20
FAILURE_EVIDENCE_LIMIT = 50
DEFAULT_MAX_PAGES = 10
QUOTA_ERROR_MARKERS = (
    "402",
    "payment required",
    "usage balance exhausted",
)


class CollectorError(RuntimeError):
    """The collector cannot safely continue."""


class BatchError(RuntimeError):
    """One Grok batch failed and may be retried."""

    def __init__(
        self,
        message: str,
        *,
        stdout: bytes = b"",
        stderr: bytes = b"",
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr


class CollectorLockActive(RuntimeError):
    """Another collector instance may still own the state-directory lock."""


@dataclass(frozen=True)
class HandleRef:
    handle: str
    bioguide: str | None


@dataclass(frozen=True)
class Batch:
    query: str
    handles: tuple[HandleRef, ...]


class GrokOutput(str):
    """Decoded stdout that retains the subprocess bytes used as evidence."""

    raw_stdout: bytes
    stderr: bytes

    def __new__(
        cls,
        value: str,
        *,
        raw_stdout: bytes,
        stderr: bytes,
    ) -> GrokOutput:
        instance = super().__new__(cls, value)
        instance.raw_stdout = raw_stdout
        instance.stderr = stderr
        return instance


Runner = Callable[[Sequence[str], str, Path], str]


def pid_is_alive(pid: int) -> bool:
    """Check a PID without signaling it, using OpenProcess on Windows."""

    if os.name == "nt":
        process_query_limited_information = 0x1000
        error_invalid_parameter = 87
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = [
            ctypes.c_uint32,
            ctypes.c_int,
            ctypes.c_uint32,
        ]
        open_process.restype = ctypes.c_void_p
        close_handle = kernel32.CloseHandle
        close_handle.argtypes = [ctypes.c_void_p]
        close_handle.restype = ctypes.c_int
        handle = open_process(
            process_query_limited_information,
            False,
            pid,
        )
        if handle:
            close_handle(handle)
            return True
        return ctypes.get_last_error() != error_invalid_parameter

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _create_collector_lock(path: Path) -> Path:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_BINARY"):
        flags |= os.O_BINARY
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="ascii",
            newline="\n",
        ) as lock_file:
            lock_file.write(f"{os.getpid()}\n")
            lock_file.flush()
            os.fsync(lock_file.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    return path


def _read_lock_pid(path: Path) -> int:
    try:
        value = path.read_text(encoding="ascii").strip()
        if not value:
            raise ValueError("empty lock")
        pid = int(value)
        if pid < 0:
            raise ValueError("negative PID")
        return pid
    except (OSError, UnicodeError, ValueError) as exc:
        raise CollectorLockActive(
            "collector.lock is empty or unreadable"
        ) from exc


def acquire_collector_lock(state_dir: Path) -> Path:
    """Exclusively create the lock, replacing one whose PID is dead."""

    lock_path = state_dir / "collector.lock"
    try:
        return _create_collector_lock(lock_path)
    except FileExistsError:
        existing_pid = _read_lock_pid(lock_path)
        if pid_is_alive(existing_pid):
            raise CollectorLockActive(
                f"collector.lock is active for PID {existing_pid}"
            )

    try:
        lock_path.unlink()
    except FileNotFoundError:
        pass
    try:
        return _create_collector_lock(lock_path)
    except FileExistsError as exc:
        raise CollectorLockActive(
            "collector.lock was acquired by another process"
        ) from exc


def release_collector_lock(path: Path) -> None:
    """Remove the lock owned by this collector invocation."""

    try:
        path.unlink()
    except FileNotFoundError:
        pass


def positive_int(value: str) -> int:
    """Parse a strictly positive integer for argparse."""

    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def parse_date_argument(value: str) -> date:
    """Parse an ISO calendar date for argparse."""

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be YYYY-MM-DD") from exc


def command_from_json(value: str, *, label: str = "Grok command") -> tuple[str, ...]:
    """Parse a JSON argv prefix without accepting shell command strings."""

    try:
        command = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON array of argv strings") from exc
    if (
        not isinstance(command, list)
        or not command
        or any(not isinstance(part, str) or not part for part in command)
    ):
        raise ValueError(f"{label} must be a non-empty JSON array of argv strings")
    return tuple(command)


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Collect new legislator X posts through sequential headless Grok "
            "search batches."
        )
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="bypass the Monday/staleness run gate",
    )
    parser.add_argument(
        "--handles-limit",
        type=positive_int,
        help=(
            "use only the first N freshly extracted handles; "
            "carried failed batches are not limited"
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=positive_int,
        default=DEFAULT_MAX_PAGES,
        help=(
            "maximum paginated search calls per batch "
            f"(default: {DEFAULT_MAX_PAGES})"
        ),
    )
    parser.add_argument(
        "--since",
        type=parse_date_argument,
        help="override the query window start (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--grok-command-json",
        help=(
            "JSON argv prefix to use instead of grok.exe; "
            "--prompt-file PATH is appended"
        ),
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        default=DEFAULT_CATALOG,
        help=f"JSONL catalog path (default: {DEFAULT_CATALOG})",
    )
    parser.add_argument(
        "--handles-file",
        type=Path,
        default=DEFAULT_HANDLES_FILE,
        help=f"legislator social-media JSON path (default: {DEFAULT_HANDLES_FILE})",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=DEFAULT_STATE_DIR,
        help=f"state and log directory (default: {DEFAULT_STATE_DIR})",
    )
    return parser


def load_handles(
    path: Path,
    *,
    limit: int | None = None,
) -> tuple[list[HandleRef], int]:
    """Load Twitter handles and return them with the missing-handle count."""

    with path.open("r", encoding="utf-8-sig") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise CollectorError("handles file must contain a JSON list")

    extracted: list[HandleRef] = []
    skipped = 0
    for entry in data:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        social = entry.get("social")
        twitter = social.get("twitter") if isinstance(social, dict) else None
        if not isinstance(twitter, str) or not twitter.strip():
            skipped += 1
            continue

        identifiers = entry.get("id")
        bioguide_value = (
            identifiers.get("bioguide") if isinstance(identifiers, dict) else None
        )
        bioguide = (
            bioguide_value.strip()
            if isinstance(bioguide_value, str) and bioguide_value.strip()
            else None
        )
        extracted.append(HandleRef(twitter.strip(), bioguide))

    if limit is not None:
        if limit <= 0:
            raise ValueError("handle limit must be greater than zero")
        extracted = extracted[:limit]
    return extracted, skipped


def iso_utc(value: datetime) -> str:
    """Format an aware datetime as an ISO UTC timestamp."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("UTC timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_iso_utc(value: str) -> datetime:
    """Parse and normalize an ISO timestamp that includes an offset."""

    if not isinstance(value, str) or not value:
        raise CollectorError("last_success_utc must be an ISO timestamp or null")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise CollectorError("last_success_utc is not a valid ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CollectorError("last_success_utc must include a UTC offset")
    return parsed.astimezone(timezone.utc)


def should_run(
    *,
    today: date,
    now_utc: datetime,
    last_success_utc: str | None,
    force: bool,
) -> bool:
    """Apply the force, Monday, absent-state, and seven-day gate."""

    if force or today.weekday() == 0 or last_success_utc is None:
        return True
    last_success = parse_iso_utc(last_success_utc)
    return last_success < now_utc.astimezone(timezone.utc) - timedelta(days=7)


def compute_window(
    *,
    today: date,
    last_success_utc: str | None,
    since_override: date | None,
) -> tuple[date, date]:
    """Compute the inclusive textual query dates."""

    if since_override is not None:
        since = since_override
    elif last_success_utc is not None:
        since = parse_iso_utc(last_success_utc).date() - timedelta(days=1)
    else:
        since = today - timedelta(days=8)
    return since, today


def _validate_query_handle(handle: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_]+", handle):
        raise CollectorError(f"invalid X handle for query: {handle!r}")


def make_query(handles: Sequence[HandleRef], since: date, until: date) -> str:
    """Construct one exact X OR-query."""

    if not handles:
        raise ValueError("cannot build a query without handles")
    for item in handles:
        _validate_query_handle(item.handle)
    terms = " OR ".join(f"from:{item.handle}" for item in handles)
    return (
        f"({terms}) since:{since.isoformat()} until:{until.isoformat()}"
    )


def build_batches(
    handles: Sequence[HandleRef],
    since: date,
    until: date,
    *,
    max_query_chars: int = MAX_QUERY_CHARS,
) -> list[Batch]:
    """Group handles into the largest order-preserving queries under the cap."""

    batches: list[Batch] = []
    current: list[HandleRef] = []
    for item in handles:
        candidate = [*current, item]
        candidate_query = make_query(candidate, since, until)
        if (
            len(candidate) <= MAX_HANDLES_PER_BATCH
            and len(candidate_query) < max_query_chars
        ):
            current = candidate
            continue
        if not current:
            raise CollectorError(
                f"single-handle query is not under {max_query_chars} characters"
            )
        current_query = make_query(current, since, until)
        batches.append(Batch(current_query, tuple(current)))
        current = [item]
        single_query = make_query(current, since, until)
        if len(single_query) >= max_query_chars:
            raise CollectorError(
                f"single-handle query is not under {max_query_chars} characters"
            )
    if current:
        batches.append(Batch(make_query(current, since, until), tuple(current)))
    return batches


_SAVED_QUERY = re.compile(
    r"^\((from:[^()\s]+(?: OR from:[^()\s]+)*)\) "
    r"since:(\d{4}-\d{2}-\d{2}) until:(\d{4}-\d{2}-\d{2})$"
)


def parse_query_handles(query: str) -> tuple[str, ...]:
    """Recover the exact handles from a collector-generated saved query."""

    if not isinstance(query, str) or len(query) >= MAX_QUERY_CHARS:
        raise CollectorError("failed batch contains an invalid query")
    match = _SAVED_QUERY.fullmatch(query)
    if match is None:
        raise CollectorError("failed batch query has an invalid shape")
    try:
        date.fromisoformat(match.group(2))
        date.fromisoformat(match.group(3))
    except ValueError as exc:
        raise CollectorError("failed batch query has an invalid date") from exc
    handles = tuple(term.removeprefix("from:") for term in match.group(1).split(" OR "))
    for handle in handles:
        _validate_query_handle(handle)
    return handles


def index_handles(handles: Sequence[HandleRef]) -> dict[str, HandleRef]:
    """Build a case-insensitive source-handle index."""

    indexed: dict[str, HandleRef] = {}
    for item in handles:
        key = item.handle.casefold()
        if key in indexed:
            raise CollectorError(
                f"duplicate case-insensitive X handle in source: {item.handle!r}"
            )
        indexed[key] = item
    return indexed


def batches_from_failed_queries(
    queries: Sequence[str],
    handle_index: dict[str, HandleRef],
) -> list[Batch]:
    """Restore exact failed queries ahead of newly generated batches."""

    batches: list[Batch] = []
    for query in queries:
        names = parse_query_handles(query)
        refs = tuple(
            handle_index.get(name.casefold(), HandleRef(name, None)) for name in names
        )
        batches.append(Batch(query, refs))
    return batches


def split_batch_into_single_handles(batch: Batch) -> list[Batch]:
    """Split a batch into single-handle queries with its original window."""

    match = _SAVED_QUERY.fullmatch(batch.query)
    if match is None:
        raise CollectorError("cannot split a batch with an invalid query")
    since = date.fromisoformat(match.group(2))
    until = date.fromisoformat(match.group(3))
    return [
        Batch(make_query((item,), since, until), (item,))
        for item in batch.handles
    ]


def dedupe_batches(batches: Sequence[Batch]) -> list[Batch]:
    """Dedupe exact query strings while preserving first occurrence order."""

    seen: set[str] = set()
    unique: list[Batch] = []
    for batch in batches:
        if batch.query in seen:
            continue
        seen.add(batch.query)
        unique.append(batch)
    return unique


def build_prompt(query: str, *, max_pages: int = DEFAULT_MAX_PAGES) -> str:
    """Build the exact paginated-search Grok instruction."""

    return (
        "Call x_keyword_search repeatedly with the exact query on the next line. "
        "Do not alter the query or drop any handle:\n"
        f"{query}\n"
        "Use mode Latest. Paginate with a cursor, or make repeated calls according "
        "to the tool's affordances, until the query window is exhausted or "
        f"{max_pages} "
        "calls have been made. Aggregate ALL results from every call.\n"
        "Output ONLY the single JSON array of every post found, with objects "
        "containing exactly these fields: "
        '{"handle": string, "utc_date": string, "text": string, '
        '"url": string or null}.\n'
        "Do not output prose or Markdown fences.\n"
    )


def run_prompt_process(
    command: Sequence[str],
    prompt: str,
    state_dir: Path,
    *,
    timeout_seconds: float = 300,
) -> str:
    """Run a command prefix with a BOM-free temporary --prompt-file."""

    if not command:
        raise BatchError("Grok command prefix must not be empty")
    descriptor, temp_name = tempfile.mkstemp(
        prefix="monday-x-prompt-",
        suffix=".txt",
        dir=state_dir,
    )
    prompt_path = Path(temp_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as prompt_file:
            prompt_file.write(prompt)

        environment = os.environ.copy()
        existing_path = environment.get("PATH", "")
        environment["PATH"] = str(GROK_BIN_DIR) + (
            os.pathsep + existing_path if existing_path else ""
        )
        try:
            completed = subprocess.run(
                [*command, "--prompt-file", str(prompt_path)],
                cwd=state_dir,
                env=environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                shell=False,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            timeout_stdout = (
                exc.stdout.encode("utf-8")
                if isinstance(exc.stdout, str)
                else exc.stdout or b""
            )
            timeout_stderr = (
                exc.stderr.encode("utf-8")
                if isinstance(exc.stderr, str)
                else exc.stderr or b""
            )
            raise BatchError(
                f"Grok dispatch timed out after {timeout_seconds:g}s",
                stdout=timeout_stdout,
                stderr=timeout_stderr,
            ) from exc
        except OSError as exc:
            raise BatchError(f"Grok command could not start: {exc}") from exc
        if completed.returncode:
            stderr_text = completed.stderr.decode("utf-8", "replace").strip()
            message = f"Grok command exited with code {completed.returncode}"
            if stderr_text:
                message = f"{message}: {stderr_text}"
            raise BatchError(
                message,
                stdout=completed.stdout,
                stderr=completed.stderr,
            )
        try:
            stdout = completed.stdout.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise BatchError(
                "Grok stdout was not valid UTF-8",
                stdout=completed.stdout,
                stderr=completed.stderr,
            ) from exc
        return GrokOutput(
            stdout,
            raw_stdout=completed.stdout,
            stderr=completed.stderr,
        )
    finally:
        try:
            prompt_path.unlink()
        except FileNotFoundError:
            pass


def is_quota_batch_error(error: BatchError, stderr: bytes) -> bool:
    """Return whether a batch failure carries exhausted-quota evidence."""

    evidence = f"{error}\n{stderr.decode('utf-8', 'replace')}".casefold()
    return any(marker in evidence for marker in QUOTA_ERROR_MARKERS)


def strip_json_fence(value: str) -> str:
    """Strip one whole-response plain or json Markdown fence."""

    stripped = value.strip()
    lines = stripped.splitlines()
    if (
        len(lines) >= 3
        and lines[0].strip().lower() in {"```", "```json"}
        and lines[-1].strip() == "```"
    ):
        return "\n".join(lines[1:-1]).strip()
    return stripped


def _json_value_from(
    value: str,
    start: int,
) -> tuple[object, int] | None:
    """Strictly parse one balanced JSON array or object at an opener."""

    stack: list[str] = []
    in_string = False
    escaped = False
    for index in range(start, len(value)):
        character = value[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if character == '"':
            in_string = True
        elif character == "[":
            stack.append("]")
        elif character == "{":
            stack.append("}")
        elif character in "]}":
            if not stack or character != stack[-1]:
                return None
            stack.pop()
            if not stack:
                try:
                    parsed = json.loads(value[start : index + 1])
                except json.JSONDecodeError:
                    return None
                if isinstance(parsed, (list, dict)):
                    return parsed, index + 1
                return None
    return None


def json_value_candidates(value: str) -> list[object]:
    """Scan the whole response for top-level JSON array or object values."""

    candidates: list[object] = []
    index = 0
    while index < len(value):
        if value[index] not in "[{":
            index += 1
            continue
        parsed = _json_value_from(value, index)
        if parsed is None:
            index += 1
            continue
        candidate, index = parsed
        candidates.append(candidate)
    return candidates


def parse_posts(response: str, batch: Batch) -> list[dict[str, object]]:
    """Strictly parse and validate one complete Grok batch response."""

    if not isinstance(response, str):
        raise BatchError("Grok response must be text")
    parseable_arrays = [
        candidate
        for candidate in json_value_candidates(response)
        if isinstance(candidate, list)
    ]
    if len(parseable_arrays) != 1:
        raise BatchError("Grok response was not one JSON array")
    data = parseable_arrays[0]

    queried = {item.handle.casefold(): item for item in batch.handles}
    posts: list[dict[str, object]] = []
    required = {"handle", "utc_date", "text", "url"}
    for item in data:
        if not isinstance(item, dict):
            raise BatchError("every Grok result must be a JSON object")
        if set(item) != required:
            raise BatchError(
                "every Grok result must contain exactly the required fields"
            )

        returned_handle = item["handle"]
        text = item["text"]
        utc_date = item["utc_date"]
        url = item["url"]
        if not isinstance(returned_handle, str) or not returned_handle.strip():
            raise BatchError("every Grok result needs a nonempty handle")
        if returned_handle != returned_handle.strip():
            raise BatchError("Grok result handles must not contain outer whitespace")
        if not isinstance(text, str) or not text.strip():
            raise BatchError("every Grok result needs nonempty text")
        if not isinstance(utc_date, str) or re.fullmatch(
            r"\d{4}-\d{2}-\d{2}[T ]?[\d:.Z+-]*",
            utc_date,
        ) is None:
            raise BatchError("every Grok result needs a valid string utc_date")
        if url is not None and not isinstance(url, str):
            raise BatchError("every Grok result URL must be a string or null")

        source = queried.get(returned_handle.casefold())
        if source is None:
            raise BatchError("Grok returned a handle outside the queried batch")
        posts.append(
            {
                "handle": source.handle,
                "bioguide": source.bioguide,
                "utc_date": utc_date,
                "text": text,
                "url": url,
            }
        )
    return posts


def catalog_key(
    *,
    handle: str,
    utc_date: str,
    text: str,
    url: str | None,
) -> str:
    """Create the URL-first, exact-concatenation fallback dedupe key."""

    if url is not None:
        return f"url:{url}"
    digest = hashlib.sha256(
        (handle + utc_date + text).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def load_catalog_keys(path: Path) -> set[str]:
    """Load and validate the existing additive catalog's dedupe keys."""

    if not path.exists():
        return set()
    keys: set[str] = set()
    with path.open("r", encoding="utf-8") as catalog:
        for line_number, line in enumerate(catalog, start=1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CollectorError(
                    f"catalog line {line_number} is not valid JSON"
                ) from exc
            if not isinstance(item, dict):
                raise CollectorError(
                    f"catalog line {line_number} is not a JSON object"
                )
            handle = item.get("handle")
            bioguide = item.get("bioguide")
            utc_date = item.get("utc_date")
            text = item.get("text")
            url = item.get("url")
            collected_at = item.get("collected_at")
            if (
                not isinstance(handle, str)
                or (bioguide is not None and not isinstance(bioguide, str))
                or not isinstance(utc_date, str)
                or not isinstance(text, str)
                or (url is not None and not isinstance(url, str))
                or not isinstance(collected_at, str)
            ):
                raise CollectorError(
                    f"catalog line {line_number} has an invalid record shape"
                )
            keys.add(
                catalog_key(
                    handle=handle,
                    utc_date=utc_date,
                    text=text,
                    url=url,
                )
            )
    return keys


def new_catalog_records(
    posts: Sequence[dict[str, object]],
    known_keys: set[str],
    *,
    collected_at: str,
) -> list[dict[str, object]]:
    """Filter existing/in-run duplicates and add collection timestamps."""

    records: list[dict[str, object]] = []
    for post in posts:
        handle = post["handle"]
        utc_date = post["utc_date"]
        text = post["text"]
        url = post["url"]
        if (
            not isinstance(handle, str)
            or not isinstance(utc_date, str)
            or not isinstance(text, str)
            or (url is not None and not isinstance(url, str))
        ):
            raise CollectorError("validated post has an invalid catalog shape")
        key = catalog_key(
            handle=handle,
            utc_date=utc_date,
            text=text,
            url=url,
        )
        if key in known_keys:
            continue
        known_keys.add(key)
        records.append(
            {
                "handle": handle,
                "bioguide": post["bioguide"],
                "utc_date": utc_date,
                "text": text,
                "url": url,
                "collected_at": collected_at,
            }
        )
    return records


def append_catalog(path: Path, records: Sequence[dict[str, object]]) -> None:
    """Append pre-encoded JSONL through one Windows-safe binary handle."""

    if not records:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = "".join(
        json.dumps(
            record,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for record in records
    ).encode("utf-8")
    with path.open("a+b") as catalog:
        catalog.seek(0, os.SEEK_END)
        size = catalog.tell()
        prefix = b""
        if size:
            catalog.seek(-1, os.SEEK_END)
            if catalog.read(1) != b"\n":
                prefix = b"\n"
        catalog.seek(0, os.SEEK_END)
        catalog.write(prefix + payload)
        catalog.flush()
        os.fsync(catalog.fileno())


def default_state() -> dict[str, object]:
    """Return an empty collector state."""

    return {
        "batch_format_version": 2,
        "last_success_utc": None,
        "failed_batches": [],
    }


def load_state(path: Path) -> dict[str, object]:
    """Load and validate collector state."""

    if not path.exists():
        return default_state()
    with path.open("r", encoding="utf-8") as state_file:
        data = json.load(state_file)
    if not isinstance(data, dict):
        raise CollectorError("state.json must contain a JSON object")
    batch_format_version = data.get("batch_format_version")
    last_success = data.get("last_success_utc")
    failed_batches = data.get("failed_batches", [])
    if last_success is not None:
        if not isinstance(last_success, str):
            raise CollectorError("state last_success_utc must be a string or null")
        parse_iso_utc(last_success)
    if (
        not isinstance(failed_batches, list)
        or any(not isinstance(query, str) for query in failed_batches)
    ):
        raise CollectorError("state failed_batches must be an array of query strings")
    return {
        "batch_format_version": batch_format_version,
        "last_success_utc": last_success,
        "failed_batches": list(failed_batches),
    }


def write_state_atomic(path: Path, state: dict[str, object]) -> None:
    """Write BOM-free JSON state through an atomic same-directory replace."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix="state-",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as state_file:
            json.dump(
                state,
                state_file,
                ensure_ascii=False,
                separators=(",", ":"),
            )
            state_file.write("\n")
            state_file.flush()
            os.fsync(state_file.fileno())
        os.replace(temp_path, path)
    finally:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass


def append_log(path: Path, message: str) -> None:
    """Append BOM-free UTF-8 collector log text."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as log_file:
        log_file.write(message.encode("utf-8"))


def prune_failure_evidence(
    path: Path,
    *,
    keep: int = FAILURE_EVIDENCE_LIMIT,
) -> None:
    """Prune the failure-evidence directory to its newest ordinary files."""

    if not path.exists():
        return
    files = [candidate for candidate in path.iterdir() if candidate.is_file()]
    files.sort(
        key=lambda candidate: (
            candidate.stat().st_mtime_ns,
            candidate.name,
        ),
        reverse=True,
    )
    for stale in files[keep:]:
        stale.unlink()


def write_failure_evidence(
    path: Path,
    *,
    dispatch_number: int,
    raw_stdout: bytes,
    stderr: bytes,
) -> Path:
    """Persist raw stdout and replacement-decoded stderr without a BOM."""

    path.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    evidence_path = path / f"{timestamp}-b{dispatch_number}.txt"
    decoded_stderr = stderr.decode("utf-8", "replace").encode("utf-8")
    evidence_path.write_bytes(
        b"STDOUT (raw):\n"
        + raw_stdout
        + b"\nSTDERR (decoded UTF-8):\n"
        + decoded_stderr
        + b"\n"
    )
    return evidence_path


def write_failed_marker(path: Path, error: BaseException) -> None:
    """Write a BOM-free marker naming a fatal error."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"{type(error).__name__}: {error}\n",
        encoding="utf-8",
        newline="\n",
    )


def remove_failed_marker(path: Path) -> None:
    """Remove a stale fatal marker after a fully successful run."""

    try:
        path.unlink()
    except FileNotFoundError:
        pass


def write_partial_marker(
    path: Path,
    *,
    appended: int,
    failed_batches: Sequence[Batch],
) -> None:
    """Write counts and the first failed query for an incomplete run."""

    if not failed_batches:
        raise ValueError("partial marker requires at least one failed batch")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            f"appended={appended}\n"
            f"failed_batches={len(failed_batches)}\n"
            f"first_failed_query={failed_batches[0].query}\n"
        ),
        encoding="utf-8",
        newline="\n",
    )


def remove_partial_marker(path: Path) -> None:
    """Remove a stale incomplete-run marker after a zero-failure run."""

    try:
        path.unlink()
    except FileNotFoundError:
        pass


def run_collection(
    args: argparse.Namespace,
    *,
    runner: Runner | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> int:
    """Run one gated collection and return its process exit code."""

    state_dir: Path = args.state_dir
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    log_path = state_dir / "collector.log"
    marker_path = state_dir / "FAILED.marker"
    partial_marker_path = state_dir / "PARTIAL.marker"
    failures_path = state_dir / "failures"
    prune_failure_evidence(failures_path)

    started_utc = datetime.now(timezone.utc)
    local_today = datetime.now().astimezone().date()
    run_stamp = iso_utc(started_utc)
    append_log(log_path, f"=== run {run_stamp} ===\n")

    state = load_state(state_path)
    last_success = state["last_success_utc"]
    if last_success is not None and not isinstance(last_success, str):
        raise CollectorError("validated state contains an invalid success timestamp")
    failed_values = state["failed_batches"]
    if not isinstance(failed_values, list):
        raise CollectorError("validated state contains invalid failed batches")
    stale_carried_count = 0
    stale_state_format = state["batch_format_version"] != 2
    if stale_state_format:
        stale_carried_count = len(failed_values)
        failed_values = []
    else:
        current_format_values: list[str] = []
        for query in failed_values:
            if len(parse_query_handles(query)) > MAX_HANDLES_PER_BATCH:
                stale_carried_count += 1
            else:
                current_format_values.append(query)
        failed_values = current_format_values
    if stale_state_format or stale_carried_count:
        append_log(
            log_path,
            (
                f"discarding {stale_carried_count} "
                "stale-format carried batches\n"
            ),
        )
    if not should_run(
        today=local_today,
        now_utc=started_utc,
        last_success_utc=last_success,
        force=args.force,
    ):
        append_log(log_path, "gate=skip\n")
        return 0

    since, until = compute_window(
        today=local_today,
        last_success_utc=last_success,
        since_override=args.since,
    )
    all_handles, skipped = load_handles(args.handles_file)
    handle_index = index_handles(all_handles)
    fresh_handles = (
        all_handles[: args.handles_limit]
        if args.handles_limit is not None
        else all_handles
    )
    carried_batches = batches_from_failed_queries(failed_values, handle_index)
    fresh_batches = build_batches(fresh_handles, since, until)
    candidate_batches = [*carried_batches, *fresh_batches]
    append_log(
        log_path,
        (
            f"gate=run since={since.isoformat()} until={until.isoformat()} "
            f"handles={len(fresh_handles)} skipped={skipped} "
            f"carried_batches={len(carried_batches)} "
            f"fresh_batches={len(fresh_batches)}\n"
        ),
    )

    known_keys = load_catalog_keys(args.catalog)
    command = (
        command_from_json(args.grok_command_json)
        if args.grok_command_json is not None
        else DEFAULT_GROK_COMMAND
    )
    active_runner = runner or run_prompt_process
    active_sleep = sleep_fn or time.sleep
    dispatch_count = 0

    def dispatch(
        batch: Batch,
    ) -> tuple[list[dict[str, object]], str | None, bool]:
        nonlocal dispatch_count
        if dispatch_count:
            active_sleep(INTER_BATCH_SLEEP_SECONDS)
        dispatch_count += 1
        output: str | None = None
        raw_stdout = b""
        stderr = b""
        try:
            output = active_runner(
                command,
                build_prompt(batch.query, max_pages=args.max_pages),
                state_dir,
            )
            if isinstance(output, GrokOutput):
                raw_stdout = output.raw_stdout
                stderr = output.stderr
            elif isinstance(output, str):
                raw_stdout = output.encode("utf-8")
            posts = parse_posts(output, batch)
        except BatchError as exc:
            if exc.stdout:
                raw_stdout = exc.stdout
            if exc.stderr:
                stderr = exc.stderr
            write_failure_evidence(
                failures_path,
                dispatch_number=dispatch_count,
                raw_stdout=raw_stdout,
                stderr=stderr,
            )
            append_log(
                log_path,
                f"batch=failed query={batch.query} error={exc}\n",
            )
            return [], str(exc), is_quota_batch_error(exc, stderr)
        append_log(
            log_path,
            f"batch=success query={batch.query} posts={len(posts)}\n",
        )
        return posts, None, False

    collected_posts: list[dict[str, object]] = []
    work_queue: list[tuple[Batch, int]] = []
    queued_queries: set[str] = set()
    query_outcomes: dict[str, str] = {}
    terminal_failures: dict[str, Batch] = {}
    successful_queries: set[str] = set()
    initial_batches: list[Batch] = []

    def enqueue(
        batch: Batch,
        stage: int,
        *,
        initial: bool = False,
    ) -> bool:
        outcome = query_outcomes.get(batch.query)
        if (
            batch.query in queued_queries
            or outcome in {"running", "succeeded", "failed", "split"}
        ):
            return False
        work_queue.append((batch, stage))
        queued_queries.add(batch.query)
        query_outcomes[batch.query] = "queued"
        if initial:
            initial_batches.append(batch)
        return True

    for batch in candidate_batches:
        enqueue(batch, 0, initial=True)

    work_index = 0
    consecutive_quota_failures = 0
    while work_index < len(work_queue):
        batch, stage = work_queue[work_index]
        work_index += 1
        queued_queries.remove(batch.query)
        query_outcomes[batch.query] = "running"
        if stage == 1:
            append_log(log_path, f"batch=retry query={batch.query}\n")
        posts, error, is_quota_failure = dispatch(batch)
        if error is None:
            consecutive_quota_failures = 0
            collected_posts.extend(posts)
            successful_queries.add(batch.query)
            terminal_failures.pop(batch.query, None)
            query_outcomes[batch.query] = "succeeded"
            continue
        if is_quota_failure:
            consecutive_quota_failures += 1
            query_outcomes[batch.query] = "failed"
            terminal_failures[batch.query] = batch
            if consecutive_quota_failures >= 2:
                for remaining_batch, _remaining_stage in work_queue[work_index:]:
                    queued_queries.discard(remaining_batch.query)
                    query_outcomes[remaining_batch.query] = "failed"
                    terminal_failures[remaining_batch.query] = remaining_batch
                append_log(
                    log_path,
                    (
                        "quota circuit breaker tripped after "
                        f"{dispatch_count} dispatches\n"
                    ),
                )
                break
            continue
        consecutive_quota_failures = 0
        if stage == 0:
            query_outcomes[batch.query] = "retryable"
            enqueue(batch, 1)
        elif stage == 1 and len(batch.handles) > 1:
            split_batches = split_batch_into_single_handles(batch)
            query_outcomes[batch.query] = "split"
            append_log(
                log_path,
                (
                    f"batch=split query={batch.query} "
                    f"single_batches={len(split_batches)}\n"
                ),
            )
            for single_batch in split_batches:
                enqueue(single_batch, 2)
        else:
            query_outcomes[batch.query] = "failed"
            terminal_failures[batch.query] = batch

    remaining_failures = [
        batch
        for query, batch in terminal_failures.items()
        if query not in successful_queries
    ]

    finished_stamp = iso_utc(datetime.now(timezone.utc))
    records = new_catalog_records(
        collected_posts,
        known_keys,
        collected_at=finished_stamp,
    )
    try:
        append_catalog(args.catalog, records)
    except Exception as exc:
        write_state_atomic(
            state_path,
            {
                "batch_format_version": 2,
                "last_success_utc": last_success,
                "failed_batches": [
                    batch.query for batch in initial_batches
                ],
            },
        )
        write_failed_marker(marker_path, exc)
        raise

    if remaining_failures:
        write_state_atomic(
            state_path,
            {
                "batch_format_version": 2,
                "last_success_utc": last_success,
                "failed_batches": [
                    batch.query for batch in remaining_failures
                ],
            },
        )
        write_partial_marker(
            partial_marker_path,
            appended=len(records),
            failed_batches=remaining_failures,
        )
        append_log(
            log_path,
            (
                f"run=incomplete appended={len(records)} "
                f"failed_batches={len(remaining_failures)}\n"
            ),
        )
        return 2

    remove_failed_marker(marker_path)
    remove_partial_marker(partial_marker_path)
    append_log(
        log_path,
        f"run=success appended={len(records)} failed_batches=0\n",
    )
    next_success = finished_stamp
    if args.handles_limit is not None:
        next_success = last_success
        append_log(log_path, "limit run: success cursor unchanged\n")
    write_state_atomic(
        state_path,
        {
            "batch_format_version": 2,
            "last_success_utc": next_success,
            "failed_batches": [],
        },
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, run the collector, and mark fatal errors."""

    args = build_parser().parse_args(argv)
    try:
        args.state_dir.mkdir(parents=True, exist_ok=True)
        try:
            lock_path = acquire_collector_lock(args.state_dir)
        except CollectorLockActive as exc:
            try:
                append_log(
                    args.state_dir / "collector.log",
                    f"run=locked exit=3 error={exc}\n",
                )
            except OSError:
                pass
            return 3
        try:
            return run_collection(args)
        finally:
            release_collector_lock(lock_path)
    except Exception as exc:
        marker_path = args.state_dir / "FAILED.marker"
        log_path = args.state_dir / "collector.log"
        marker_error: OSError | None = None
        try:
            write_failed_marker(marker_path, exc)
        except OSError as write_error:
            marker_error = write_error
        try:
            append_log(
                log_path,
                f"run=fatal error={type(exc).__name__}: {exc}\n",
            )
        except OSError:
            pass
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        if marker_error is not None:
            print(
                f"could not write FAILED.marker: {marker_error}",
                file=sys.stderr,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
