#!/usr/bin/env python3
"""Resumable Politico profile crawler for an isolated authenticated browser profile.

This is the Python/headless alternative to ``politico_profile_crawl_cua.mjs``.
It deliberately does not accept a username, password, cookie jar, or Playwright
``storage_state``.  Authentication is established once, attended, in a dedicated
Chrome profile and is subsequently reused by Chrome itself.

The current signed-in Codex/Chrome-extension tab cannot be attached to by Python
unless that browser was launched with a CDP endpoint.  Do not copy its Cookies or
profile files to work around that boundary.  Use ``--bootstrap-login`` to create
the isolated profile, or ``--cdp-endpoint`` only with a browser the operator
explicitly launched for this crawler.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import urlsplit
try:
    from .politico_crawl_pacing import AsyncRequestPacer, AdmissionStopped
    from .politico_worker_windows import new_worker_window, window_id
    from .politico_sharding import shard_for_uuid
except ImportError:
    from politico_crawl_pacing import AsyncRequestPacer, AdmissionStopped
    from politico_worker_windows import new_worker_window, window_id
    from politico_sharding import shard_for_uuid


DIRECTORY_DEFAULT = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\raw\politico"
    r"\crawl-20260829T221300-0400\directory_rows.ndjson"
)
OUTPUT_DEFAULT = Path(
    r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\audits\staffer_network"
    r"\politico_profile_crawl_20260903_raw"
)
PROFILE_DEFAULT = Path(
    r"C:\Users\pgoff\AppData\Local\Melange\staffer_network\browser"
    r"\politico-playwright-profile"
)
GLASSBOX_EMIT_DEFAULT = Path(r"C:\Users\pgoff\.claude\glassbox\emit.ps1")
PROFILE_BASE_URL = "https://directory.politicopro.com/congress/staffer/"
DIRECTORY_URL = (
    "https://directory.politicopro.com/congress"
    "?Type=staffer&StaffersType=MEMBER_COMMITTEES&CaucusType=MEMBER_CAUCUSES"
)
COMMITTEE_ROLE_RE = re.compile(
    r"\bfor\s+((?:House|Senate)\s+.*(?:Committee|Commission).*)$", re.I
)
CONTACT_VALUE_RE = re.compile(
    r"(?:\b(?:e-?mail|phone|telephone|mobile|fax|office address|contact information)\b"
    r"|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b"
    r"|(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4})",
    re.I,
)
CONTACT_KEY_RE = re.compile(r"email|phone|telephone|mobile|fax|address|contact", re.I)
LOGIN_URL_RE = re.compile(r"/(?:login|signin|sign-in)(?:[/?#]|$)", re.I)

RATE_STAGES: tuple[tuple[str, int, int | None], ...] = (
    ("START_60", 60, 5),
    ("RAMP_80", 80, 6),
    ("RAMP_100", 100, 10),
    ("PROVEN_120", 120, 6),
    ("PROVEN_150", 150, 8),
    ("PROVEN_200", 200, 10),
    ("PROVEN_250", 250, None),
)
MAX_WORKERS = 8


# The page returns only modeled fields and booleans.  Contact-section contents and
# the full body text never cross from the browser into the Python process.
SNAPSHOT_SCRIPT = r"""
() => {
  const tidy = value => String(value ?? "").replace(/\s+/g, " ").trim();
  const texts = selector => [...document.querySelectorAll(selector)]
    .map(node => tidy(node.textContent)).filter(Boolean);
  const records = (itemSelector, fields) => [...document.querySelectorAll(itemSelector)]
    .map(item => Object.fromEntries(Object.entries(fields).map(([key, selector]) => [
      key,
      tidy([...item.querySelectorAll(selector)].map(node => node.textContent).join(" ")),
    ])));
  // innerText forces a synchronous browser layout. Read only DOM text nodes,
  // excluding scripts/styles so embedded application strings cannot trip flags.
  const bodyParts = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.parentElement?.closest('script, style, noscript')) bodyParts.push(node.textContent);
  }
  const body = tidy(bodyParts.join(' '));
  const errorHeadings = [...document.querySelectorAll('main h1, main h2, main h3, [role="main"] h1, [role="main"] h2')]
    .filter(node => node.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}))
    .map(node => tidy(node.textContent));
  return {
    headings: texts("h1, h2, h3, h4"),
    profile_names: texts(".profile-header__name"),
    header_positions: texts(".profile-header__desc"),
    explicit_side_labels: texts("main strong")
      .filter(value => /^(Majority Staff|Minority Staff|Bipartisan Staff)$/i.test(value)),
    issues: texts(".profile-issue-areas__item"),
    employment_history: records(".profile-employment-history__item", {
      employer: ".profile-employment-history__employer",
      date_text: ".profile-employment-history__date",
      title: ".profile-employment-history__title",
    }),
    education: records(".profile-education__item", {
      institution: ".profile-education__institution",
      date_text: ".profile-education__date",
      degree: ".profile-education__degree",
    }),
    flags: {
      authentication_required: /\b401\b.{0,40}\bunauthorized\b|\bauthentication required\b|\bsession (?:has )?expired\b|\bplease (?:log|sign) in\b|\b(?:log|sign) in to (?:continue|politico|your account)\b/i.test(body),
      challenge: /\bverify (?:that )?you are human\b|\bcaptcha\b|\bunusual traffic\b|\bcloudflare ray id\b|\baccess denied\b/i.test(body),
      throttled: /\b429\b.{0,40}\btoo many requests\b|\btoo many requests\b|\brate limit(?:ed| exceeded)?\b/i.test(body),
      unavailable_404: errorHeadings.some(value => /^(?:404(?:\s*[-:–]?\s*(?:error|not found))?|(?:this |the )?page (?:cannot|can't) be found[.!]?|(?:this |the )?profile (?:is )?(?:unavailable|not found)[.!]?)$/i.test(value)),
      document_loaded: document.readyState === 'complete',
      busy: [...document.querySelectorAll('[aria-busy="true"]')].some(node =>
        node.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) &&
        (node.matches('main, [role="main"]') || node.closest('.profile-header, .profile-employment-history, .profile-education'))),
    },
  };
}
"""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u00a0", " ")).strip()


def unique(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = clean(value)
        if not item or item in seen or CONTACT_VALUE_RE.search(item):
            continue
        seen.add(item)
        result.append(item)
    return result


def safe_records(values: Iterable[Mapping[str, Any]], keys: Sequence[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for value in values:
        row = {key: clean(value.get(key)) for key in keys}
        if any(CONTACT_VALUE_RE.search(text) for text in row.values() if text):
            continue
        if not any(row.values()):
            continue
        signature = json.dumps(row, sort_keys=True, ensure_ascii=False)
        if signature not in seen:
            seen.add(signature)
            rows.append(row)
    return rows


def forbidden_contact_paths(value: Any, prefix: str = "$.") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            path = f"{prefix}{key}"
            if CONTACT_KEY_RE.search(str(key)) and key != "contact_fields_collected":
                hits.append(path)
            hits.extend(forbidden_contact_paths(child, f"{path}."))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(forbidden_contact_paths(child, f"{prefix}[{index}]."))
    elif isinstance(value, str) and CONTACT_VALUE_RE.search(value):
        hits.append(prefix.rstrip("."))
    return hits


def read_ndjson(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as error:
                raise RuntimeError(f"invalid NDJSON at {path}:{line_number}: {error}") from error
            if not isinstance(value, dict):
                raise RuntimeError(f"expected object at {path}:{line_number}")
            rows.append(value)
    return rows


def existing_ids(path: Path) -> set[str]:
    if not path.is_file():
        return set()
    return {
        clean(row.get("profile_uuid"))
        for row in read_ndjson(path)
        if clean(row.get("profile_uuid"))
    }


def append_ndjson(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        return
    payload = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows
    ).encode("utf-8")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        written = os.write(descriptor, payload)
        if written != len(payload):
            raise OSError(f"short append to {path}: {written}/{len(payload)} bytes")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    # OneDrive/AV can hold the destination briefly (WinError 5/32 observed 2026-09-04);
    # retry the rename with bounded backoff instead of aborting the whole crawl.
    delay = 0.25
    for attempt in range(12):
        try:
            os.replace(temporary, path)
            return
        except (PermissionError, OSError) as exc:
            winerror = getattr(exc, "winerror", None)
            if winerror not in (5, 32) or attempt == 11:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 4.0)


class CrawlLock:
    """Advisory single-writer lock for Python invocations.

    The legacy JS runner does not take this lock, so ``assert_checkpoint_stale``
    below also prevents an accidental takeover while that runner is active.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.handle: Any = None

    def __enter__(self) -> "CrawlLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.handle = self.path.open("a+b")
        self.handle.seek(0)
        if not self.handle.read(1):
            self.handle.seek(0)
            self.handle.write(b"0")
            self.handle.flush()
        self.handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(self.handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.handle.close()
            raise RuntimeError(f"another Python crawler owns {self.path}") from error
        self.handle.seek(0)
        self.handle.truncate()
        self.handle.write(str(os.getpid()).encode("ascii"))
        self.handle.flush()
        return self

    def __exit__(self, *_: object) -> None:
        if self.handle is None:
            return
        self.handle.seek(0)
        if os.name == "nt":
            import msvcrt

            with contextlib.suppress(OSError):
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            with contextlib.suppress(OSError):
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        self.handle.close()


@dataclasses.dataclass
class RateState:
    stage_index: int = 0
    clean_batches: int = 0
    total_clean_batches: int = 0
    backoff_count: int = 0
    last_event: str = "INITIALIZED_AT_60_RPM"

    @property
    def name(self) -> str:
        return RATE_STAGES[self.stage_index][0]

    @property
    def rpm(self) -> int:
        return RATE_STAGES[self.stage_index][1]

    @classmethod
    def from_checkpoint(cls, checkpoint: Mapping[str, Any] | None) -> "RateState":
        if not isinstance(checkpoint, Mapping):
            return cls()
        control = checkpoint.get("rate_control")
        if not isinstance(control, Mapping) or control.get("mode") != "AUTHORIZED_GENTLE_RAMP":
            return cls()
        stage_index = checkpoint.get("rate_stage_index", 0)
        if not isinstance(stage_index, int) or not 0 <= stage_index < len(RATE_STAGES):
            return cls()
        if checkpoint.get("current_requests_per_minute") != RATE_STAGES[stage_index][1]:
            return cls()
        def counter(name: str) -> int:
            value = checkpoint.get(name, 0)
            return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0

        return cls(
            stage_index=stage_index,
            clean_batches=counter("rate_stage_clean_batches"),
            total_clean_batches=counter("total_clean_batches"),
            backoff_count=counter("rate_backoff_count"),
            last_event=clean(checkpoint.get("last_rate_event")) or "RESUMED_AUTHORIZED_RAMP",
        )

    def record(self, *, attempted: int, succeeded: int, retryable: int, hard: int, slow: int) -> None:
        clean_batch = attempted > 0 and succeeded == attempted and retryable == 0 and hard == 0 and slow == 0
        if not clean_batch:
            prior = self.rpm
            self.stage_index = max(0, self.stage_index - 1)
            self.clean_batches = 0
            self.backoff_count += 1
            self.last_event = f"BACKOFF_{prior}_TO_{self.rpm}_RPM"
            return
        self.clean_batches += 1
        self.total_clean_batches += 1
        threshold = RATE_STAGES[self.stage_index][2]
        if threshold is not None and self.clean_batches >= threshold and self.stage_index < len(RATE_STAGES) - 1:
            prior = self.rpm
            self.stage_index += 1
            self.clean_batches = 0
            self.last_event = f"RAMP_{prior}_TO_{self.rpm}_RPM"
        else:
            self.last_event = f"CLEAN_BATCH_AT_{self.rpm}_RPM"


@dataclasses.dataclass
class FetchResult:
    expected: dict[str, Any]
    ok: bool = False
    retryable: bool = True
    halt: bool = False
    error: str = ""
    row: dict[str, Any] | None = None
    elapsed_ms: int = 0
    started: bool = False
    worker_index: int = -1


def load_checkpoint(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def assert_checkpoint_stale(path: Path, stale_seconds: int) -> None:
    if not path.exists() or stale_seconds <= 0:
        return
    age = time.time() - path.stat().st_mtime
    if age < stale_seconds:
        raise RuntimeError(
            f"checkpoint changed {age:.1f}s ago; pause the existing CUA/JS runner and "
            f"wait until it is at least {stale_seconds}s old before Python takes over"
        )


def rotate_resume_queue(queue: list[dict[str, Any]], source_rows: list[dict[str, Any]],
                        *, next_uuid: str = "", last_completed_uuid: str = "") -> list[dict[str, Any]]:
    """Continue the prior scan without dropping earlier unresolved profiles."""
    if not queue:
        return queue
    pending_positions = {clean(row.get("profile_uuid")): i for i, row in enumerate(queue)}
    if next_uuid in pending_positions:
        split = pending_positions[next_uuid]
        return queue[split:] + queue[:split]
    source_positions = {clean(row.get("profile_uuid")): i for i, row in enumerate(source_rows)}
    if last_completed_uuid in source_positions:
        last_position = source_positions[last_completed_uuid]
        split = next((i for i, row in enumerate(queue)
                      if source_positions[clean(row.get("profile_uuid"))] > last_position), 0)
        return queue[split:] + queue[:split]
    return queue


def build_queue(
    directory_path: Path,
    profiles_path: Path,
    failures_path: Path,
    scope: str,
) -> tuple[list[dict[str, Any]], int, int, int]:
    source_rows = read_ndjson(directory_path)
    if scope == "CURRENT_COMMITTEE_PROFILES_FIRST":
        source_rows = [
            row
            for row in source_rows
            if any(COMMITTEE_ROLE_RE.search(clean(role)) for role in row.get("roles", []))
        ]
    deduplicated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        profile_uuid = clean(row.get("profile_uuid"))
        if not profile_uuid or profile_uuid in seen:
            continue
        seen.add(profile_uuid)
        deduplicated.append(row)
    completed_rows = read_ndjson(profiles_path) if profiles_path.is_file() else []
    completed = {clean(row.get("profile_uuid")) for row in completed_rows}
    failed = existing_ids(failures_path)
    target_ids = {clean(row.get("profile_uuid")) for row in deduplicated}
    base_succeeded = len(target_ids & completed)
    base_failed = len(target_ids & failed)
    queue = [
        row
        for row in deduplicated
        if clean(row.get("profile_uuid")) not in completed | failed
    ]
    checkpoint = load_checkpoint(profiles_path.parent / "state.json") or {}
    queue = rotate_resume_queue(queue, deduplicated,
                                next_uuid=clean(checkpoint.get("next_profile_uuid")),
                                last_completed_uuid=clean(completed_rows[-1].get("profile_uuid")) if completed_rows else "")
    return queue, len(deduplicated), base_succeeded, base_failed


def parse_snapshot(
    snapshot: Mapping[str, Any], expected: Mapping[str, Any], *, unavailable_404: bool = False
) -> dict[str, Any]:
    flags = snapshot.get("flags") if isinstance(snapshot.get("flags"), Mapping) else {}
    # Only the fetch acceptance gate may declare an unavailable profile.
    unavailable = unavailable_404
    names = unique(snapshot.get("profile_names", []))
    observed_name = None if unavailable else (names[0] if names else None)
    expected_name = clean(expected.get("name"))
    identity_status = (
        "PROFILE_UNAVAILABLE_404"
        if unavailable
        else "UUID_AND_NAME_MATCH"
        if observed_name and observed_name.casefold() == expected_name.casefold()
        else "LIVE_NAME_CHANGED_SAME_UUID"
    )
    row: dict[str, Any] = {
        "profile_uuid": clean(expected.get("profile_uuid")),
        "expected_name": expected_name,
        "verified_name": observed_name,
        "identity_status": identity_status,
        "partition": clean(expected.get("partition")) or None,
        "source_card_roles": unique(expected.get("roles", [])),
        "source_card_issue_areas": sorted(unique(expected.get("issue_areas", []))),
        "current_header_positions": unique(snapshot.get("header_positions", [])),
        "explicit_side_labels": sorted(unique(snapshot.get("explicit_side_labels", []))),
        "profile_issue_areas": sorted(unique(snapshot.get("issues", []))),
        "employment_history": safe_records(
            snapshot.get("employment_history", []), ("employer", "date_text", "title")
        ),
        "education": safe_records(
            snapshot.get("education", []), ("institution", "date_text", "degree")
        ),
        "observed_at": utc_now(),
        "source_url": PROFILE_BASE_URL + clean(expected.get("profile_uuid")),
        "review_status": (
            "REVIEW_REQUIRED"
            if identity_status == "UUID_AND_NAME_MATCH"
            else "IDENTITY_EXCEPTION_REVIEW_REQUIRED"
        ),
        "contact_fields_collected": False,
    }
    if unavailable:
        for field in ("current_header_positions", "explicit_side_labels", "profile_issue_areas", "employment_history", "education"):
            row[field] = []
    hits = forbidden_contact_paths(row)
    if hits:
        raise RuntimeError("CONTACT_FIELD_GUARD:" + ",".join(hits[:8]))
    return row


async def fetch_profile(page: Any, expected: dict[str, Any], rpm: int, ordinal: int,
                        pacer: Any = None, stop_event: Any = None) -> FetchResult:
    # Stagger requests even though six pages are available; this avoids a six-request
    # burst and makes each staged aggregate request rate effective.
    if pacer is None:
        await asyncio.sleep(ordinal * (60.0 / rpm))
    result = FetchResult(expected=expected)
    started = time.perf_counter()
    profile_uuid = clean(expected.get("profile_uuid"))
    url = PROFILE_BASE_URL + profile_uuid
    status: int | None = None
    phase = "navigation"
    pending_data: set[Any] = set()
    profile_api_status: int | None = None
    def data_requested(request: Any) -> None:
        endpoint = urlsplit(request.url)
        person_path = '/proxy/lava/api/v1/person/' + profile_uuid
        if request.resource_type in {"xhr", "fetch"} and endpoint.hostname == 'directory.politicopro.com' and (endpoint.path == person_path or endpoint.path.startswith(person_path + '/')):
            # Hold the Request object, not its recyclable object id. Unrelated
            # notification/notes polling is not profile hydration work.
            pending_data.add(request)
    def data_finished(request: Any) -> None:
        pending_data.discard(request)
    def profile_response(response: Any) -> None:
        nonlocal profile_api_status
        endpoint = urlsplit(response.url)
        if endpoint.hostname == 'directory.politicopro.com' and endpoint.path.rstrip('/') == '/proxy/lava/api/v1/person/' + profile_uuid:
            profile_api_status = response.status
    page.on("request", data_requested)
    page.on("requestfinished", data_finished)
    page.on("requestfailed", data_finished)
    page.on("response", profile_response)
    try:
        if pacer is not None:
            await pacer.wait_turn(stop_event)
        result.started = True
        started = time.perf_counter()
        response = await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        status = response.status if response is not None else None
        if status in {401, 403}:
            result.halt = True
            result.error = f"AUTHENTICATION_OR_CHALLENGE_HTTP_{status}"
            return result
        if status == 429:
            result.error = "RATE_LIMIT_429_DETECTED"
            return result
        if status is not None and status >= 500:
            result.error = f"SERVER_HTTP_{status}"
            return result
        if LOGIN_URL_RE.search(str(page.url)):
            result.halt = True
            result.error = "AUTHENTICATION_REDIRECT_DETECTED"
            return result

        snapshot: Mapping[str, Any] = {}
        phase = "snapshot"
        previous_complete: dict[str, Any] | None = None
        stable_samples = 0
        unavailable_samples = 0
        for attempt in range(45):
            snapshot = await asyncio.wait_for(page.evaluate(SNAPSHOT_SCRIPT), timeout=20)
            observed_url = str(page.url).split("?", 1)[0].split("#", 1)[0].rstrip("/")
            if observed_url != url:
                result.halt = True
                safe_location = urlsplit(observed_url)
                result.error = f"PROFILE_FINAL_URL_MISMATCH observed={safe_location.hostname}{safe_location.path}"
                return result
            flags = snapshot.get("flags") if isinstance(snapshot.get("flags"), Mapping) else {}
            if profile_api_status in {400, 401, 403}:
                result.halt = True
                result.error = f"PROFILE_DATA_API_HTTP_{profile_api_status}"
                return result
            if profile_api_status == 429:
                result.error = "RATE_LIMIT_429_DETECTED"
                return result
            if profile_api_status is not None and profile_api_status >= 500:
                result.error = f"PROFILE_DATA_API_HTTP_{profile_api_status}"
                return result
            if flags.get("authentication_required") or flags.get("challenge"):
                result.halt = True
                result.error = "AUTHENTICATION_OR_CHALLENGE_DETECTED"
                return result
            if flags.get("throttled"):
                result.error = "RATE_LIMIT_429_DETECTED"
                return result
            names = unique(snapshot.get("profile_names", []))
            headings = [value.casefold() for value in unique(snapshot.get("headings", []))]
            has_profile_content = bool(names or snapshot.get("employment_history"))
            if status == 404 and has_profile_content:
                result.error = "CONTRADICTORY_HTTP404_PROFILE_CONTENT"
                return result
            unavailable = (status == 404 or (status == 200 and profile_api_status == 404 and bool(flags.get("unavailable_404")))) and not has_profile_content
            # An authoritative person404 has no successful body to hydrate;
            # browsers may leave its failed request pending without a finish
            # event. Still require a visible stable error and zero profile data.
            data_settled = not pending_data or (unavailable and profile_api_status == 404)
            settled = flags.get("document_loaded") is True and not flags.get("busy") and data_settled
            unavailable_samples = unavailable_samples + 1 if unavailable and settled else 0
            employment_present = any("employment history" == value for value in headings)
            candidate = parse_snapshot(snapshot, expected, unavailable_404=unavailable)
            complete = bool(candidate["current_header_positions"] and candidate["employment_history"])
            complete = complete and all(item["employer"] and item["title"] for item in candidate["employment_history"])
            is_complete = bool(names and employment_present and complete and profile_api_status == 200)
            # Poll promptly instead of adding 1.5 seconds to each fast page.
            same = is_complete and previous_complete is not None and all(
                candidate[field] == previous_complete[field]
                for field in ("verified_name", "current_header_positions", "employment_history", "education", "profile_issue_areas", "explicit_side_labels")
            )
            stable_samples = stable_samples + 1 if same and settled else (1 if is_complete and settled else 0)
            # Require a loaded document, drained XHR/fetch requests and three
            # identical modeled samples, not just the first populated item.
            if unavailable_samples >= 3 or stable_samples >= 3:
                candidate["observed_source_url"] = observed_url
                candidate["response_status"] = status
                candidate["profile_api_status"] = profile_api_status
                candidate["unavailable_evidence"] = ("HTTP_404" if status == 404 else "STABLE_SCOPED_ERROR_HEADING") if unavailable else None
                result.row = candidate
                result.ok = True
                result.retryable = False
                return result
            previous_complete = candidate if is_complete else None
            if attempt < 44:
                await asyncio.sleep(0.25)
        result.error = (f"PROFILE_CONTENT_NOT_RENDERED api={profile_api_status} names={len(names)} "
                        f"history={len(candidate['employment_history'])} pending_person_requests={len(pending_data)} "
                        f"loaded={flags.get('document_loaded')} busy={flags.get('busy')}")
        return result
    except AdmissionStopped:
        result.error = "ADMISSION_STOPPED"
        return result
    except Exception as error:  # Playwright exception classes are optional at import time.
        result.error = (f"{phase.upper()}_{type(error).__name__}: {clean(error)[:300]} "
                        f"http={status} person_api={profile_api_status} pending_person_requests={len(pending_data)}")
        return result
    finally:
        page.remove_listener("request", data_requested)
        page.remove_listener("requestfinished", data_finished)
        page.remove_listener("requestfailed", data_finished)
        page.remove_listener("response", profile_response)
        result.elapsed_ms = round((time.perf_counter() - started) * 1000)


async def initialize_directory(page: Any, pacer: Any = None, stop_event: Any = None) -> None:
    for attempt in range(2):
        if pacer is not None:
            await pacer.wait_turn(stop_event)
        response = await page.goto(DIRECTORY_URL, wait_until="domcontentloaded", timeout=30_000)
        location = urlsplit(str(page.url))
        if location.hostname == "login.politicopro.com" or LOGIN_URL_RE.search(str(page.url)):
            raise RuntimeError("DIRECTORY_AUTHENTICATION_REDIRECT")
        if response is not None and response.status in {401, 403, 429}:
            raise RuntimeError(f"DIRECTORY_HTTP_{response.status}")
        try:
            # Actual directory links, not a guessed delay during session setup.
            await page.wait_for_function('() => document.querySelector(\'a[href*="/congress/staffer/\"]\') !== null', timeout=30_000)
            return
        except Exception:
            snapshot = await asyncio.wait_for(page.evaluate(SNAPSHOT_SCRIPT), timeout=20)
            flags = snapshot.get("flags", {})
            location = urlsplit(str(page.url))
            print(json.dumps({"event": "DIRECTORY_NOT_READY", "attempt": attempt + 1,
                              "host": location.hostname, "path": location.path,
                              "flags": flags}), flush=True)
            if location.hostname == "login.politicopro.com" or LOGIN_URL_RE.search(str(page.url)) or flags.get("authentication_required") or flags.get("challenge") or flags.get("throttled"):
                raise RuntimeError("DIRECTORY_AUTHENTICATION_CHALLENGE_OR_THROTTLE")
            if attempt:
                raise


async def bounded_fetch(page: Any, expected: dict[str, Any], rpm: int, ordinal: int,
                        pacer: Any = None, stop_event: Any = None) -> FetchResult:
    attempt_started = time.perf_counter()
    any_started = False
    async def fetch_with_recovery() -> FetchResult:
        nonlocal any_started
        result = await fetch_profile(page, expected, rpm, ordinal, pacer, stop_event)
        any_started = result.started
        if result.error == "PROFILE_DATA_API_HTTP_400":
            # The SPA can retain an invalid context after a deep-link reload.
            # Use only normal directory navigation to reinitialize it, once.
            await initialize_directory(page, pacer, stop_event)
            print(json.dumps({"event": "DIRECTORY_SESSION_REINITIALIZED_AFTER_API400"}), flush=True)
            result = await fetch_profile(page, expected, rpm, 0, pacer, stop_event)
            result.started = result.started or any_started
            result.elapsed_ms = round((time.perf_counter() - attempt_started) * 1000)
        return result
    try:
        return await asyncio.wait_for(fetch_with_recovery(), timeout=60)
    except asyncio.TimeoutError:
        return FetchResult(expected=expected, error="PROFILE_WORKER_TIMEOUT", elapsed_ms=60_000, started=True)
    except AdmissionStopped:
        return FetchResult(expected=expected, error="ADMISSION_STOPPED", started=any_started,
                           elapsed_ms=round((time.perf_counter() - attempt_started) * 1000))


async def fetch_wave(pages: list[Any], batch: list[dict[str, Any]], rate: RateState,
                     pacer: AsyncRequestPacer, slow_response_ms: int,
                     shard_by_uuid: bool = False, max_inflight: int | None = None) -> list[FetchResult]:
    """Several warm pages, one admission clock; no per-profile batch barrier."""
    available: asyncio.Queue[int] = asyncio.Queue()
    for index in range(len(pages)):
        available.put_nowait(index)
    stop_admissions = asyncio.Event()
    shard_locks = [asyncio.Lock() for _ in pages]
    capacity = asyncio.Semaphore(max(1, min(len(pages), max_inflight or len(pages))))

    async def job(expected: dict[str, Any]) -> FetchResult:
        if shard_by_uuid:
            index = shard_for_uuid(clean(expected.get("profile_uuid")), len(pages))
            await shard_locks[index].acquire()
        else:
            index = await available.get()
        try:
            async with capacity:
                if stop_admissions.is_set():
                    return FetchResult(expected=expected, error="ADMISSION_STOPPED")
                result = await bounded_fetch(pages[index], expected, rate.rpm, 0, pacer, stop_admissions)
                if not result.ok:
                    stop_admissions.set()
            result.worker_index = index
            if result.started:
                rate.record(attempted=1, succeeded=int(result.ok),
                            retryable=int(not result.ok and result.retryable),
                            hard=int(not result.ok and not result.retryable),
                            slow=int(result.elapsed_ms > slow_response_ms))
            if not result.ok:
                stop_admissions.set()
            return result
        except BaseException:
            # Stop queued jobs before this page slot becomes available again.
            stop_admissions.set()
            raise
        finally:
            if shard_by_uuid:
                shard_locks[index].release()
            else:
                available.put_nowait(index)

    # Preserve source-order writes even when pages finish out of order. The
    # coordinator alone appends/checkpoints after all active work is drained.
    tasks = [asyncio.create_task(job(expected)) for expected in batch]
    try:
        return await asyncio.gather(*tasks)
    except BaseException:
        stop_admissions.set()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise


def state_payload(
    *,
    scope: str,
    total: int,
    succeeded: int,
    failed: int,
    attempted_this_session: int,
    halted: bool,
    rate: RateState,
    last_batch: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "schema_id": "politico-profile-crawl-state-v1",
        "scope": scope,
        "queue_total": total,
        "total_succeeded": succeeded,
        "total_failed": failed,
        "attempted_this_session": attempted_this_session,
        "remaining": max(0, total - succeeded - failed),
        "halted": halted,
        "max_requests_per_minute": rate.rpm,
        "configured_max_requests_per_minute": 250,
        "current_requests_per_minute": rate.rpm,
        "rate_stage": rate.name,
        "rate_stage_index": rate.stage_index,
        "rate_stage_clean_batches": rate.clean_batches,
        "total_clean_batches": rate.total_clean_batches,
        "rate_backoff_count": rate.backoff_count,
        "last_rate_event": rate.last_event,
        "rate_control": {
            "mode": "AUTHORIZED_GENTLE_RAMP",
            "current_requests_per_minute": rate.rpm,
            "last_batch": {
                "attempted": int(last_batch.get("attempted", 0)),
                "succeeded": int(last_batch.get("succeeded", 0)),
                "retryable_failures": int(last_batch.get("retryable_failures", 0)),
                "hard_failures": int(last_batch.get("hard_failures", 0)),
            },
        },
        "last_batch_health": {
            "slow_responses": int(last_batch.get("slow_responses", 0)),
            "maximum_elapsed_ms": int(last_batch.get("maximum_elapsed_ms", 0)),
        },
        "browser_driver": "PYTHON_PLAYWRIGHT_PERSISTENT_CONTEXT",
        "contact_fields_collected": False,
        "last_updated": utc_now(),
    }


def emit_glassbox(emit_path: Path, payload: Mapping[str, Any]) -> None:
    if not emit_path.is_file():
        return
    remaining = int(payload.get("remaining", -1))
    total = int(payload.get("queue_total", -1))
    succeeded = int(payload.get("total_succeeded", -1))
    failed = int(payload.get("total_failed", -1))
    halted = bool(payload.get("halted"))
    status = "failed" if halted else "completed" if remaining == 0 else "running"
    metadata = {
        "politico_succeeded": succeeded,
        "politico_failed": failed,
        "politico_remaining": remaining,
        "politico_queue_total": total,
        "politico_halted": halted,
        "requests_per_minute": payload.get("current_requests_per_minute"),
        "rate_stage": payload.get("rate_stage"),
        "rate_event": payload.get("last_rate_event"),
        "contact_fields_collected": False,
    }
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(emit_path),
        "-Lane",
        "codex",
        "-Kind",
        "collection.heartbeat",
        "-Status",
        status,
        "-Stage",
        "politico_profile_headless",
        "-Summary",
        f"Politico {succeeded}/{total}; {remaining} remaining at {payload.get('current_requests_per_minute')} RPM",
        "-Detail",
        f"failures={failed}; halted={str(halted).lower()}; rate_event={payload.get('last_rate_event')}",
        "-Source",
        "python_playwright_runner",
        "-Cwd",
        str(Path.cwd()),
        "-MetadataJson",
        json.dumps(metadata, separators=(",", ":")),
        "-Quiet",
    ]
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(command, check=False, capture_output=True, timeout=15)


async def browser_context(args: argparse.Namespace, playwright: Any) -> tuple[Any, Any | None, bool]:
    if args.cdp_endpoint:
        browser = await playwright.chromium.connect_over_cdp(args.cdp_endpoint, timeout=15_000)
        if not browser.contexts:
            raise RuntimeError("CDP browser has no contexts")
        # Caller must not close a CDP-attached browser owned by the operator.
        return browser.contexts[0], browser, True
    args.profile_dir.mkdir(parents=True, exist_ok=True)
    context = await playwright.chromium.launch_persistent_context(
        user_data_dir=str(args.profile_dir),
        channel="chrome",
        headless=not args.headed and not args.bootstrap_login and not args.wait_for_login,
        viewport={"width": 1440, "height": 1000},
        locale="en-US",
        # Revalidate cached proxy responses: cached/stale context previously
        # returned API400 while the SPA misleadingly displayed a404 page.
        extra_http_headers={"Cache-Control": "no-cache"},
        # Avoid request routing: it disables HTTP cache, repeatedly downloading
        # the application bundles on every profile. Chrome can suppress images
        # while keeping its normal persistent cache and all data requests.
        args=["--blink-settings=imagesEnabled=false"],
    )
    return context, None, False


async def bootstrap_login(args: argparse.Namespace, playwright: Any) -> int:
    context, _, _ = await browser_context(args, playwright)
    try:
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(DIRECTORY_URL, wait_until="domcontentloaded", timeout=30_000)
        print(
            "Complete the Politico login in the opened dedicated Chrome window. "
            "The script never receives the username, password, cookies, or storage state."
        )
        await asyncio.to_thread(input, "Press Enter here only after the directory is visibly signed in: ")
        if LOGIN_URL_RE.search(str(page.url)):
            print("LOGIN_NOT_CONFIRMED: browser is still on a login URL", file=sys.stderr)
            return 2
        snapshot = await page.evaluate(SNAPSHOT_SCRIPT)
        flags = snapshot.get("flags") if isinstance(snapshot.get("flags"), Mapping) else {}
        if flags.get("authentication_required") or flags.get("challenge"):
            print("LOGIN_NOT_CONFIRMED: authentication/challenge surface remains", file=sys.stderr)
            return 2
        print("LOGIN_PROFILE_READY")
        return 0
    finally:
        # Chrome on Windows can wait indefinitely for its last persistent page
        # during context shutdown. These pages belong exclusively to this
        # dedicated profile, so close them explicitly before the context.
        for open_page in list(context.pages):
            with contextlib.suppress(Exception):
                await open_page.close()
        await context.close()


async def crawl(args: argparse.Namespace, playwright: Any) -> int:
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    profiles_path = output_dir / "profiles.ndjson"
    failures_path = output_dir / "failures.ndjson"
    state_path = output_dir / "state.json"

    with CrawlLock(output_dir / ".politico-python-crawl.lock"):
        assert_checkpoint_stale(state_path, args.require_stale_seconds)
        prior_checkpoint = load_checkpoint(state_path)
        rate = RateState.from_checkpoint(prior_checkpoint)
        if args.reset_rate:
            rate.stage_index = 0
            rate.clean_batches = 0
            rate.last_event = "GENTLE_RAMP_RESET_FOR_NEW_WORKER_CONFIGURATION"
        pacer = AsyncRequestPacer(lambda: rate.rpm)
        queue, total, base_succeeded, base_failed = build_queue(
            args.directory, profiles_path, failures_path, args.scope
        )
        session_succeeded = 0
        attempted_this_session = 0
        halted = False
        last_batch = {
            "attempted": 0,
            "succeeded": 0,
            "retryable_failures": 0,
            "hard_failures": 0,
            "slow_responses": 0,
            "maximum_elapsed_ms": 0,
        }

        context, cdp_browser, attached_cdp = await browser_context(args, playwright)
        created_pages: list[Any] = []
        try:
            if args.wait_for_login and queue:
                login_page = context.pages[0] if context.pages else await context.new_page()
                probe_url = PROFILE_BASE_URL + "cce4d75f-7b8a-4e60-a286-234e2e4198eb"
                await pacer.wait_turn()
                await login_page.goto(probe_url, wait_until="domcontentloaded", timeout=30_000)
                deadline = time.monotonic() + 1800
                print(json.dumps({"event": "WAITING_FOR_LOGIN", "message": "Sign in to Politico in the dedicated Chrome window. Crawling starts automatically after successful login."}), flush=True)
                while time.monotonic() < deadline:
                    if login_page.is_closed():
                        raise RuntimeError("dedicated login window was closed")
                    if str(login_page.url).startswith("https://directory.politicopro.com/congress"):
                        if await login_page.locator(".profile-header__name").count():
                            check = await asyncio.wait_for(login_page.evaluate(SNAPSHOT_SCRIPT), timeout=10)
                            if check.get("profile_names") and check.get("employment_history"):
                                print(json.dumps({"event": "LOGIN_SURFACE_READY", "workers": args.workers}), flush=True)
                                break
                        elif await login_page.locator('a[href*="/congress/staffer/"]').count():
                            await pacer.wait_turn()
                            await login_page.goto(probe_url, wait_until="domcontentloaded", timeout=30_000)
                    await asyncio.sleep(2)
                else:
                    raise RuntimeError("LOGIN_TIMEOUT: no authenticated profile rendered within 30 minutes")
            pages = list(context.pages)
            print(json.dumps({"event": "STARTUP_CONTEXT", "existing_pages": len(pages), "requested_workers": args.workers}), flush=True)
            if not attached_cdp:
                for unused_page in pages[1:]:
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(unused_page.close(), timeout=3)
                pages = pages[:1]

            known = next((row for row in reversed(read_ndjson(profiles_path)) if row.get("employment_history")), None)
            for worker_index in range(args.workers):
                # Warm one page fully before allocating the next renderer.
                if worker_index >= len(pages):
                    page = (await new_worker_window(context, pages[0])
                            if args.worker_layout == "windows"
                            else await asyncio.wait_for(context.new_page(), timeout=15))
                    pages.append(page)
                    created_pages.append(page)
                page = pages[worker_index]
                if not (args.wait_for_login and worker_index == 0):
                    print(json.dumps({"event": "STARTUP_DIRECTORY_WAIT", "worker": worker_index}), flush=True)
                    await initialize_directory(page, pacer)
                if known:
                    expected_canary = {"profile_uuid": known["profile_uuid"], "name": known["expected_name"], "partition": known.get("partition")}
                    canary = await bounded_fetch(page, expected_canary, rate.rpm, 0, pacer)
                    if not canary.ok or not canary.row or not canary.row.get("employment_history") or canary.row.get("profile_api_status") != 200:
                        raise RuntimeError("STARTUP_CANARY_FAILED: " + (canary.error or "missing content"))
                    print(json.dumps({"event": "STARTUP_CONTENT_CANARY_PASS", "worker": worker_index, "profile_api_status": canary.row.get("profile_api_status")}), flush=True)
                    if args.wait_for_login and worker_index == 0:
                        print(json.dumps({"event": "LOGIN_VERIFIED", "workers": args.workers}), flush=True)
                if args.worker_layout == "windows" and worker_index == 1 and known:
                    # Validate real concurrent execution in two distinct windows
                    # before opening the remaining requested workers.
                    pair = await asyncio.gather(*(bounded_fetch(
                        candidate_page, expected_canary, rate.rpm, 0, pacer)
                        for candidate_page in pages[:2]))
                    if any(not item.ok or not item.row or item.row.get("profile_api_status") != 200
                           or not item.row.get("employment_history") for item in pair):
                        raise RuntimeError("CONCURRENT_WINDOW_CANARY_FAILED: " +
                                           "; ".join(item.error or "missing content" for item in pair if not item.ok))
                    print(json.dumps({"event": "CONCURRENT_WINDOW_CANARY_PASS", "workers": 2}), flush=True)
            pages = pages[:args.workers]
            if args.worker_layout == "windows":
                window_ids = [await window_id(context, page) for page in pages]
                if len(set(window_ids)) != len(pages):
                    raise RuntimeError("WORKERS_ARE_NOT_DISTINCT_WINDOWS")
                shards = [{"worker": index, "window_id": window_ids[index], "profile_uuids": []}
                          for index in range(len(pages))]
                for expected in queue:
                    shards[shard_for_uuid(clean(expected.get("profile_uuid")), len(pages))]["profile_uuids"].append(expected["profile_uuid"])
                assigned = [uuid for shard in shards for uuid in shard["profile_uuids"]]
                if len(assigned) != len(queue) or len(set(assigned)) != len(queue):
                    raise RuntimeError("SHARD_CONSERVATION_FAILED")
                atomic_json(output_dir / "window_shard_manifest.json", {
                    "schema_id": "politico-window-shards-v1", "generated_at": utc_now(),
                    "strategy": "SHA256_UUID_MOD_WORKERS", "workers": len(pages),
                    "pending_profiles": len(queue), "shards": shards,
                })
                print(json.dumps({"event": "WINDOW_SHARDS_READY", "windows": len(set(window_ids)),
                                  "pending_profiles": len(queue),
                                  "shard_sizes": [len(shard["profile_uuids"]) for shard in shards]}), flush=True)

            batches = 0
            no_progress_batches = 0
            last_emit = 0.0
            last_verified_attempts = 0
            processing_started = time.perf_counter()
            inflight_limit = 1
            concurrency_clean_waves = 0
            while queue and not halted:
                if args.max_profiles and attempted_this_session >= args.max_profiles:
                    break
                batch_size = min(25 if len(pages) > 1 else 1, len(queue))
                if args.max_profiles:
                    batch_size = min(batch_size, args.max_profiles - attempted_this_session)
                batch = queue[:batch_size]
                results = await fetch_wave(pages, batch, rate, pacer, args.slow_response_ms,
                                           shard_by_uuid=args.worker_layout == "windows",
                                           max_inflight=inflight_limit)
                actual_attempted = sum(result.started for result in results)
                good = [result.row for result in results if result.ok and result.row is not None]
                retry_rows = [result.expected for result in results if not result.ok and result.retryable]
                hard = [result for result in results if not result.ok and not result.retryable]
                halted = any(result.halt for result in results)
                no_progress_batches = 0 if good else no_progress_batches + 1
                if no_progress_batches >= 5 or hard:
                    halted = True
                append_ndjson(profiles_path, good)
                # failures.ndjson is READ by build_queue (existing_ids -> base_failed)
                # but was never written, so a permanently unfetchable profile stayed in
                # the queue on every resume, total_failed stayed 0 and `remaining` could
                # never reach 0 (the glassbox heartbeat therefore never reports
                # "completed"). Record the non-retryable ones.
                append_ndjson(failures_path, [{
                    "profile_uuid": clean(result.expected.get("profile_uuid")),
                    "expected_name": clean(result.expected.get("name")),
                    "error": result.error,
                    "observed_at": utc_now(),
                } for result in hard])
                session_succeeded += len(good)
                attempted_this_session += actual_attempted
                queue = [*queue[len(batch) :], *retry_rows]
                slow_responses = sum(result.elapsed_ms > args.slow_response_ms for result in results)
                if any(result.started and not result.ok for result in results) or slow_responses:
                    inflight_limit = max(1, inflight_limit // 2)
                    concurrency_clean_waves = 0
                elif good:
                    concurrency_clean_waves += 1
                    if concurrency_clean_waves >= 3:
                        inflight_limit = min(len(pages), inflight_limit + 1)
                        concurrency_clean_waves = 0
                last_batch = {
                    "attempted": actual_attempted,
                    "succeeded": len(good),
                    "retryable_failures": sum(result.started and not result.ok and result.retryable for result in results),
                    "not_attempted": sum(not result.started for result in results),
                    "hard_failures": len(hard),
                    "slow_responses": slow_responses,
                    "maximum_elapsed_ms": max((result.elapsed_ms for result in results), default=0),
                }
                payload = state_payload(
                    scope=args.scope,
                    total=total,
                    succeeded=base_succeeded + session_succeeded,
                    failed=base_failed,
                    attempted_this_session=attempted_this_session,
                    halted=halted,
                    rate=rate,
                    last_batch=last_batch,
                )
                payload["active_workers"] = len(pages)
                payload["next_wave_max_inflight"] = inflight_limit
                payload["worker_layout"] = args.worker_layout
                payload["shard_strategy"] = "SHA256_UUID_MOD_WORKERS" if args.worker_layout == "windows" else "AVAILABLE_PAGE_QUEUE"
                payload["navigation_admissions"] = pacer.admissions
                payload["next_profile_uuid"] = clean(queue[0].get("profile_uuid")) if queue else None
                atomic_json(state_path, payload)
                batches += 1
                if time.monotonic() - last_emit >= 15 or halted:
                    await asyncio.to_thread(emit_glassbox, args.glassbox_emit, payload)
                    last_emit = time.monotonic()
                if batches <= 3 or attempted_this_session - last_verified_attempts >= 50 or halted or not queue:
                    verification = await asyncio.to_thread(subprocess.run, [
                        sys.executable, str(Path(__file__).with_name("verify_politico_profile_crawl.py")),
                        "--directory", str(args.directory), "--profiles", str(profiles_path),
                        "--failures", str(failures_path), "--state", str(state_path),
                        "--output", str(output_dir / "crawl_verification.json"),
                    ], capture_output=True, timeout=120)
                    last_verified_attempts = attempted_this_session
                    if verification.returncode:
                        halted = True
                        payload["halted"] = True
                        atomic_json(state_path, payload)
                        print(json.dumps({"event": "VERIFICATION_FAILED", "returncode": verification.returncode}), flush=True)
                print(
                    json.dumps(
                        {
                            "total_succeeded": payload["total_succeeded"],
                            "remaining": payload["remaining"],
                            "halted": halted,
                            "rpm": rate.rpm,
                            "rate_event": rate.last_event,
                            "last_batch": last_batch,
                            "workers": len(pages),
                            "next_wave_max_inflight": inflight_limit,
                            "navigation_admissions": pacer.admissions,
                            "session_accounted_per_minute": round(session_succeeded * 60 / max(0.001, time.perf_counter() - processing_started), 1),
                            "worker_results": [{"ok": result.ok, "elapsed_ms": result.elapsed_ms} for result in results],
                            "errors": [result.error for result in results if result.error][:6],
                        },
                        separators=(",", ":"),
                    ),
                    flush=True,
                )

                # A wedged renderer must not hold the next batch indefinitely.
                # Only this script's dedicated worker pages are replaced.
                if not attached_cdp and not halted:
                    failed_workers = {result.worker_index for result in results if result.started and not result.ok and not result.halt and result.error != "RATE_LIMIT_429_DETECTED" and result.worker_index >= 0}
                    for index in sorted(failed_workers):
                        # Closing the final tab can terminate a persistent
                        # Chrome context. Create its replacement first.
                        replacement_page = (await new_worker_window(context, pages[index])
                                            if args.worker_layout == "windows"
                                            else await asyncio.wait_for(context.new_page(), timeout=10))
                        with contextlib.suppress(Exception):
                            await asyncio.wait_for(pages[index].close(), timeout=3)
                        pages[index] = replacement_page
                        try:
                            await initialize_directory(pages[index], pacer)
                        except Exception as error:
                            # Navigation timeouts are transient; retain the shard
                            # and its queued UUIDs. Auth/throttle failures still halt.
                            if isinstance(error, asyncio.TimeoutError) or type(error).__name__ == "TimeoutError":
                                inflight_limit = 1
                                concurrency_clean_waves = 0
                                print(json.dumps({"event": "RECOVERY_TIMEOUT_DEFERRED",
                                                  "worker": index}), flush=True)
                            else:
                                raise

                # The shared pacer controls every actual navigation, including
                # retries/reinitialization, without an extra batch-level sleep.

            final_payload = state_payload(
                scope=args.scope,
                total=total,
                succeeded=base_succeeded + session_succeeded,
                failed=base_failed,
                attempted_this_session=attempted_this_session,
                halted=halted,
                rate=rate,
                last_batch=last_batch,
            )
            final_payload["active_workers"] = len(pages)
            final_payload["worker_layout"] = args.worker_layout
            final_payload["shard_strategy"] = "SHA256_UUID_MOD_WORKERS" if args.worker_layout == "windows" else "AVAILABLE_PAGE_QUEUE"
            final_payload["navigation_admissions"] = pacer.admissions
            final_payload["next_profile_uuid"] = clean(queue[0].get("profile_uuid")) if queue else None
            atomic_json(state_path, final_payload)
            emit_glassbox(args.glassbox_emit, final_payload)
            return 3 if halted else 0
        except Exception:
            # This block still owns the single-writer lock. Expose startup or
            # session failure honestly rather than leaving stale "running" state.
            failure_state = state_payload(
                scope=args.scope, total=total,
                succeeded=base_succeeded + session_succeeded,
                failed=base_failed, attempted_this_session=attempted_this_session,
                halted=True, rate=rate, last_batch=last_batch,
            )
            failure_state["halt_reason"] = "CRAWLER_STARTUP_OR_SESSION_FAILURE"
            failure_state["next_profile_uuid"] = clean(queue[0].get("profile_uuid")) if queue else None
            atomic_json(state_path, failure_state)
            emit_glassbox(args.glassbox_emit, failure_state)
            raise
        finally:
            if attached_cdp:
                # Disconnect by stopping Playwright later. Never close the operator's
                # browser or any page that this process did not create.
                for page in created_pages:
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(page.close(), timeout=3)
                _ = cdp_browser
            else:
                for page in list(context.pages):
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(page.close(), timeout=3)
                with contextlib.suppress(Exception):
                    await asyncio.wait_for(context.close(), timeout=10)


def run_self_test() -> None:
    expected = {
        "profile_uuid": "00000000-0000-0000-0000-000000000001",
        "name": "Gordon Holzberg",
        "partition": "staffer",
        "roles": ["Chief of Staff for House Example Committee"],
        "issue_areas": ["Energy"],
    }
    snapshot = {
        "headings": ["Gordon Holzberg", "Employment History", "Education"],
        "profile_names": ["Gordon Holzberg"],
        "header_positions": ["Chief of Staff", "202-555-0199"],
        "explicit_side_labels": ["Majority Staff"],
        "issues": ["Energy", "gordon@example.test"],
        "employment_history": [
            {"employer": "House Example Committee", "date_text": "Jan 2021 - Present", "title": "Chief of Staff"},
            {"employer": "gordon@example.test", "date_text": "", "title": ""},
        ],
        "education": [
            {"institution": "Example University", "date_text": "2004 - 2008", "degree": "BA"}
        ],
        "flags": {},
    }
    row = parse_snapshot(snapshot, expected)
    encoded = json.dumps(row)
    assert "gordon@example.test" not in encoded
    assert "202-555-0199" not in encoded
    assert row["contact_fields_collected"] is False
    assert row["identity_status"] == "UUID_AND_NAME_MATCH"
    assert len(row["employment_history"]) == 1
    missing = parse_snapshot(snapshot, expected, unavailable_404=True)
    assert missing["verified_name"] is None
    assert all(missing[field] == [] for field in (
        "current_header_positions", "explicit_side_labels", "profile_issue_areas", "employment_history", "education"
    ))
    rate = RateState()
    for _ in range(4):
        rate.record(attempted=6, succeeded=6, retryable=0, hard=0, slow=0)
        assert rate.rpm == 60
    rate.record(attempted=6, succeeded=6, retryable=0, hard=0, slow=0)
    assert rate.rpm == 80
    rate.record(attempted=6, succeeded=5, retryable=1, hard=0, slow=0)
    assert rate.rpm == 60
    hydrated_source = RateState(stage_index=2, clean_batches=7, total_clean_batches=18, backoff_count=1)
    hydrated_checkpoint = state_payload(
        scope="ALL_CURRENT_PROFILES",
        total=18_618,
        succeeded=4_461,
        failed=0,
        attempted_this_session=0,
        halted=False,
        rate=hydrated_source,
        last_batch={
            "attempted": 6,
            "succeeded": 6,
            "retryable_failures": 0,
            "hard_failures": 0,
        },
    )
    hydrated = RateState.from_checkpoint(hydrated_checkpoint)
    assert (hydrated.rpm, hydrated.clean_batches, hydrated.total_clean_batches) == (100, 7, 18)
    assert RateState.from_checkpoint({"max_requests_per_minute": 40}).rpm == 60
    assert max(stage[1] for stage in RATE_STAGES) == 250
    print(json.dumps({"passed": True, "fixtures": 3, "maximum_rpm": 250}))


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DIRECTORY_DEFAULT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DEFAULT)
    parser.add_argument("--profile-dir", type=Path, default=PROFILE_DEFAULT)
    parser.add_argument(
        "--scope",
        choices=("CURRENT_COMMITTEE_PROFILES_FIRST", "ALL_CURRENT_PROFILES"),
        default="ALL_CURRENT_PROFILES",
    )
    parser.add_argument("--workers", type=int, choices=range(1, MAX_WORKERS + 1), default=1,
                        help="dedicated pages; one is the verified stable default")
    parser.add_argument("--worker-layout", choices=("tabs", "windows"), default="tabs",
                        help="separate windows use deterministic non-overlapping UUID shards")
    parser.add_argument("--reset-rate", action="store_true", help="restart gentle ramp for a new worker configuration")
    parser.add_argument("--max-profiles", type=int, default=0, help="0 means run until complete/halted")
    parser.add_argument("--headed", action="store_true", help="show the dedicated crawler browser")
    parser.add_argument("--bootstrap-login", action="store_true", help="attended login into the dedicated profile")
    parser.add_argument("--wait-for-login", action="store_true", help="open dedicated Chrome, detect completed login, then crawl automatically")
    parser.add_argument("--cdp-endpoint", help="attach only to an explicitly debug-enabled browser")
    parser.add_argument("--slow-response-ms", type=int, default=12_000)
    parser.add_argument(
        "--require-stale-seconds",
        type=int,
        default=90,
        help="refuse takeover if another crawler updated state more recently",
    )
    parser.add_argument("--glassbox-emit", type=Path, default=GLASSBOX_EMIT_DEFAULT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.max_profiles < 0:
        parser.error("--max-profiles must be nonnegative")
    if args.slow_response_ms <= 0:
        parser.error("--slow-response-ms must be positive")
    if args.bootstrap_login and args.cdp_endpoint:
        parser.error("--bootstrap-login and --cdp-endpoint are mutually exclusive")
    return args


async def async_main(args: argparse.Namespace) -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "PLAYWRIGHT_NOT_INSTALLED: create a small venv and run "
            "`python -m pip install playwright`; installed Chrome is used, so no "
            "browser-cookie export or downloaded profile is required.",
            file=sys.stderr,
        )
        return 4
    async with async_playwright() as playwright:
        if args.bootstrap_login:
            return await bootstrap_login(args, playwright)
        return await crawl(args, playwright)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        run_self_test()
        return 0
    try:
        return asyncio.run(async_main(args))
    except KeyboardInterrupt:
        return 130
    except Exception as error:
        # clean(error) is empty for any exception carrying no message (several
        # Playwright teardown errors do), which produced the bare "CRAWL_ABORTED: "
        # line the watchdog could only classify as unknown. The type name is
        # always present.
        print(f"CRAWL_ABORTED: {type(error).__name__}: {clean(error) or 'no message'}",
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
