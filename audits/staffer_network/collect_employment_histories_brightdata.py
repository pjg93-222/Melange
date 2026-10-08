#!/usr/bin/env python3
"""Collect LinkedIn employment/education history for LDA lobbyists and current
congressional staffers via Bright Data's pre-built LinkedIn Web Scraper API
datasets (``linkedin_people_search`` -> ``linkedin_person_profile``).

Purpose (Paul): "a scraper that collects where LDA [lobbyists] and former
staffers previously worked or currently worked and for how long", and the same
for current staffers. This is third-party licensed collection; the tool is
usable only once a Bright Data key exists and Paul approves the source. This
module makes ZERO network calls unless ``--mode`` is ``sample`` or ``full``
AND a Bright Data API key is available; ``--mode dry-run`` (the default) never
touches the network and never requires a key.

------------------------------------------------------------------------------
ENDPOINTS (Bright Data Web Scraper API / "Datasets v3")
------------------------------------------------------------------------------
Source: the ``bright-data-best-practices`` skill's
``references/web-scraper-api.md`` (Bright Data plugin skill cache, read
2026-09-02), sections "Asynchronous Requests", "Monitor Progress", "Download
Results", and "Finding Dataset IDs".

    TRIGGER_URL   = POST https://api.brightdata.com/datasets/v3/trigger
                    params: dataset_id, format=json; body: {"input": [...]}
                    -> {"snapshot_id": "..."}
    PROGRESS_URL  = GET  https://api.brightdata.com/datasets/v3/progress/{snapshot_id}
                    -> {"status": "starting"|"running"|"ready"|"failed", ...}
    SNAPSHOT_URL  = GET  https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}
                    -> JSON array of result records (or {"results": [...]})
    DATASETS_LIST_URL = GET https://api.brightdata.com/datasets/list
                    -> [{"id": "gd_...", "name": "...", "size": N}, ...]

Pipeline *type names* ``linkedin_person_profile`` and ``linkedin_people_search``
are confirmed (as CLI pipeline identifiers, not raw ``gd_`` dataset hashes) in
the same plugin cache's ``skills/brightdata-cli/references/pipelines.md``
line 46 and line 50, and ``skills/data-feeds/references/flags.md`` line 48
and line 71.

------------------------------------------------------------------------------
DEVIATION FLAG -- raw dataset_id ("gd_...") could not be sourced verbatim
------------------------------------------------------------------------------
The task brief pointed at a file
``skills/scraper-builder/scripts/datasets.sh`` as the place holding the exact
``gd_...`` dataset IDs for ``linkedin_person_profile``/``linkedin_people_search``
and the endpoint URLs. As of 2026-09-02 that file does not exist anywhere on
this machine (confirmed: the scraper-builder skill directory under the local
Bright Data plugin cache has only ``SKILL.md``, ``references/``, and
``evals/`` -- no ``scripts/`` directory at all; nor does any other file in the
plugin cache, nor anywhere in this repository, contain a ``gd_`` hash tied to
either LinkedIn pipeline). Every reference that *does* exist documents the
Datasets v3 endpoints precisely (cited above) but only ever calls the LinkedIn
scrapers by pipeline *name* through the ``bdata``/`brightdata` CLI wrapper,
which resolves names to hashes on Bright Data's server side and never
publishes the hash locally.

Rather than fabricate a plausible-looking ``gd_...`` string, this collector
requires the real dataset ID to be supplied explicitly once it is known:
``--dataset-id-profile`` / ``--dataset-id-search`` (or the environment
variables ``BRIGHTDATA_DATASET_ID_LINKEDIN_PERSON_PROFILE`` /
``BRIGHTDATA_DATASET_ID_LINKEDIN_PEOPLE_SEARCH``). If neither is set,
``--mode sample`` / ``--mode full`` abort loudly (``UNKNOWN_DATASET_ID``)
*before any network call*, with the exact resolution command
(``GET https://api.brightdata.com/datasets/list``, see "Finding Dataset IDs"
in web-scraper-api.md) printed in the error. ``--mode dry-run`` is unaffected
since it never needs a dataset ID.

------------------------------------------------------------------------------
ASSUMED BRIGHT DATA I/O SHAPES (undocumented in the available skill cache)
------------------------------------------------------------------------------
No file in the plugin cache shows a raw JSON request/response body for either
LinkedIn dataset (only CLI positional-arg usage, e.g.
``linkedin_people_search <url> <first_name> <last_name>``). The shapes below
are a documented, best-effort reconstruction from the CLI usage strings, the
generic Web Scraper API request/response conventions (input rows are JSON
objects; PDP-style scrapers echo the requested ``url`` back in each result
record), and the ``experience``/``education`` field names Paul's own brief
names explicitly. They MUST be confirmed against real API output the first
time ``--mode sample`` is run with a live key -- that is exactly what sample
mode is for. Every mapping function below is written to be tolerant of
several plausible key-name variants so a near-miss in this guess does not
crash the collector.

linkedin_people_search -- one input row per queued person:
    {"first_name": str, "last_name": str, "keyword": str}
  one result record per candidate found for a query:
    {
      "name": str,                                  # candidate's LinkedIn name
      "url" | "profile_url": str,                    # candidate's profile URL
      "headline" | "position" | "current_title": str | None,
      "current_company": {"name": str, "title": str} | str | None,
      "experience": [ {...} ] | None,                 # optional lightweight list
    }
  NOTE: no correlation id is assumed to be echoed back per input row. This
  collector correlates a batch's flat result list back to the queued person by
  normalized first+last name equality, which doubles as the mandatory identity
  check below. This means two different queued people sharing an identical
  normalized name inside the SAME batch cannot be reliably disambiguated by
  this collector; that is a known, documented limitation, not a bug.

linkedin_person_profile -- one input row per accepted profile URL:
    {"url": str}
  one result record per requested profile URL (echoing "url"):
    {
      "url": str,
      "name": str,
      "experience": [
        {"company" | "company_name" | "employer": str,
         "title" | "position": str,
         "location" | "location_raw": str | None,
         "start_date" | "starts_at" | "date_from": str | None,
         "end_date" | "ends_at" | "date_to": str | None,
         "current" | "is_current": bool | None,
         "description": str | None},
        ...
      ],
      "education": [
        {"institution" | "school" | "institution_name": str,
         "degree" | "degree_name": str | None,
         "field_of_study" | "field": str | None,
         "start_year" | "starts_at" | "start_date": int | str | None,
         "end_year" | "ends_at" | "end_date": int | str | None},
        ...
      ],
      # plus arbitrary other fields (contact info, photo, posts, connections,
      # summary, ...) that this collector deliberately NEVER reads or stores.
    }

------------------------------------------------------------------------------
Identity discipline (non-negotiable, per the staffer_network lane's rule)
------------------------------------------------------------------------------
A profile URL is accepted only if, after (a) requiring normalized first+last
name equality against the queued person's display name, and (b) requiring at
least one discovery-hint token (a whole word, casefolded) to appear in the
candidate's reported experience company/title text, EXACTLY ONE candidate
survives. Otherwise the person's discovery outcome is recorded as
``NO_UNIQUE_CANDIDATE`` (zero survivors) or ``NAME_COLLISION`` (two or more
survivors) and nothing is fetched for them. Every accepted row carries
``identity_status: "REVIEW_REQUIRED"``, ``canonical_identity_decision:
"NOT_ADJUDICATED"``, ``canonical_employment_promoted: False``,
``canonical_eligible: False`` -- this collector never promotes anything to
canonical status.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_PLAN = "staffer-network-brightdata-collection-plan-v1"
SCHEMA_MANIFEST = "staffer-network-brightdata-profile-evidence-manifest-v1"
SCHEMA_ROW = "staffer-network-brightdata-profile-evidence-v1"
SCHEMA_RECEIPT = "staffer-network-brightdata-profile-evidence-receipt-v1"
STAGE_ID = "brightdata-linkedin-employment-history-collector"

TRIGGER_URL = "https://api.brightdata.com/datasets/v3/trigger"
PROGRESS_URL_TMPL = "https://api.brightdata.com/datasets/v3/progress/{snapshot_id}"
SNAPSHOT_URL_TMPL = "https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}"
DATASETS_LIST_URL = "https://api.brightdata.com/datasets/list"

PIPELINE_NAME_PERSON_PROFILE = "linkedin_person_profile"
PIPELINE_NAME_PEOPLE_SEARCH = "linkedin_people_search"

DEFAULT_LIVE_ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
DEFAULT_APPDATA_ROOT = r"C:\Users\pgoff\AppData\Local\Melange\staffer_network"
DEFAULT_KEYS_JSON = r"C:\Users\pgoff\OneDrive\Desktop\API Keys\keys.json"
DEFAULT_EMPLOYMENT_LOOKUP_GENERATION = "generation-20260831T050000Z"
DEFAULT_GLASSBOX_EVENTS_DIR = r"C:\Users\pgoff\.claude\glassbox\events"

MAX_TRIGGER_BATCH_SIZE = 20
RECORDS_PER_PERSON_ESTIMATE = 2  # 1 search-stage record + 1 profile-stage record

TOKEN_RE = re.compile(r"[A-Za-z0-9]+")

COMPANY_STOPWORDS = {
    "llc", "inc", "incorporated", "corp", "corporation", "company", "co",
    "group", "the", "of", "and", "llp", "pllc", "pc", "associates",
    "partners", "international", "america", "americas", "holdings",
    "enterprises", "global", "solutions", "services", "consulting", "law",
    "firm", "office", "offices", "ltd", "limited", "na",
}

CURRENT_WORDS = {"present", "current", "now"}

FULL_MONTHS = [
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
]
MONTH_LOOKUP: dict[str, int] = {}
for _index, _name in enumerate(FULL_MONTHS, start=1):
    MONTH_LOOKUP[_name] = _index
    MONTH_LOOKUP[_name[:3]] = _index

DATE_ISO_RE = re.compile(r"^(?P<year>\d{4})(?:-(?P<month>\d{2}))?$")
DATE_TEXT_RE = re.compile(r"^(?P<month>[A-Za-z]+)\.?\s+(?P<year>\d{4})$")
YEAR_ONLY_RE = re.compile(r"^(\d{4})$")
LEADING_YEAR_RE = re.compile(r"^(\d{4})")

NOTICE_SENTENCE = (
    "Third-party profile evidence; identity is a review candidate; "
    "not canonical; not a complete history."
)


class GateFailure(RuntimeError):
    """Raised for any condition that must abort the run loudly."""


class CostCapExceeded(GateFailure):
    """Raised when the estimated Bright Data spend would exceed --max-cost-usd."""


# ---------------------------------------------------------------------------
# Canonical JSON / gzip helpers (lane convention: see
# audits/staffer_network/a9_build_a7_a8_priority_sidecar.py compact()/
# write_gzip() -- sorted keys, LF newlines, gzip mtime=0, atomic replace)
# ---------------------------------------------------------------------------


def compact(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def canonical_line(value: Any) -> bytes:
    return compact(value) + b"\n"


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        tmp_path.write_bytes(payload)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def write_gzip(path: Path, values: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        with tmp_path.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="\n") as text:
                    for value in values:
                        text.write(compact(value).decode("utf-8") + "\n")
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def read_ndjson_gz(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            value = json.loads(line)
            if isinstance(value, dict):
                yield value


def describe_input_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"path": str(path), "present": False, "bytes": None, "sha256": None}
    return {
        "path": str(path),
        "present": True,
        "bytes": path.stat().st_size,
        "sha256": sha(path),
    }


# ---------------------------------------------------------------------------
# Anti-promotion tripwire (adapted verbatim from the lane convention in
# audits/staffer_network/build_employment_adjudication_priority_queue.py)
# ---------------------------------------------------------------------------


def assert_unpromoted(value: Mapping[str, Any], context: str) -> None:
    for key, child in value.items():
        lowered = str(key).lower()
        if lowered in {
            "canonical_employment_promoted",
            "canonical_identity_promoted",
            "canonical_employment_fact",
            "canonical_identity_fact",
            "complete_lifetime_employment_asserted",
        } and child not in (False, 0, None, ""):
            raise GateFailure(f"promotion field set at {context}:{key}")
        if lowered.endswith(
            (
                "canonical_person_id",
                "canonical_employment_episode_id",
                "canonical_employment_fact_id",
                "canonical_fact_id",
            )
        ) and child not in (False, 0, None, ""):
            raise GateFailure(f"canonical ID set at {context}:{key}")
        if lowered == "canonical_identity_decision" and child not in (
            "NOT_ADJUDICATED",
            None,
        ):
            raise GateFailure(f"canonical identity decision set at {context}:{key}")


# ---------------------------------------------------------------------------
# Glassbox event emission (stdlib only; schema per task brief)
# ---------------------------------------------------------------------------


def emit_glassbox_event(
    events_dir: Path,
    *,
    run_id: str,
    correlation_id: str,
    kind: str,
    status: str,
    stage: str,
    summary: str,
    detail: str = "",
) -> None:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%S%f")
    event_id = f"evt-{stamp}Z-{secrets.token_hex(5)}"
    payload = {
        "schema_version": 1,
        "id": event_id,
        "timestamp_utc": now.strftime("%Y-%m-%dT%H:%M:%S.%f") + "Z",
        "run_id": run_id,
        "correlation_id": correlation_id,
        "parent_id": "",
        "lane": "claude",
        "source": "employment-history-scraper",
        "kind": kind,
        "status": status,
        "stage": stage,
        "summary": summary,
        "detail": detail,
        "cwd": str(Path.cwd()),
        "duration_ms": -1,
        "bytes": -1,
        "metadata": {},
    }
    try:
        events_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_bytes(events_dir / f"{event_id}.json", canonical_line(payload)[:-1])
    except OSError:
        # Glassbox emission must never take down the collector itself.
        pass


def new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"run-brightdata-collector-{stamp}-{secrets.token_hex(4)}"


def new_correlation_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"corr-{stamp}Z-{secrets.token_hex(5)}"


# ---------------------------------------------------------------------------
# Queue data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class QueuePerson:
    subject_kind: str  # "lda_lobbyist" | "current_staffer"
    lda_source_person_id: str | None
    quorum_staff_id: str | None
    display_name: str
    discovery_hints: tuple[str, ...]
    member_office: str | None = None
    title: str | None = None
    name_variants: tuple[str, ...] = field(default_factory=tuple)


def person_key(person: QueuePerson) -> str:
    identifier = person.lda_source_person_id or person.quorum_staff_id or ""
    return f"{person.subject_kind}:{identifier}"


def tokenize_company(name: str) -> list[str]:
    tokens: list[str] = []
    for raw in TOKEN_RE.findall(name):
        low = raw.casefold()
        if low in COMPANY_STOPWORDS:
            continue
        tokens.append(low)
    return tokens


def member_surname(member_display_name: str) -> str:
    parts = [p for p in re.split(r"\s+", member_display_name.strip()) if p]
    if not parts:
        return ""
    last = re.sub(r"[^\w'-]", "", parts[-1])
    return last.casefold()


def default_lda_queue_path(appdata_root: Path) -> Path:
    return (
        appdata_root
        / "employment-lookup"
        / DEFAULT_EMPLOYMENT_LOOKUP_GENERATION
        / "employment_lookup_queue.ndjson.gz"
    )


def default_registrant_episodes_path(live_root: Path) -> Path:
    return (
        live_root
        / "audits"
        / "staffer_network"
        / "lda_registrant_employment_20260831"
        / "lda_registrant_employment_episodes.ndjson.gz"
    )


def default_staff_directory_path(live_root: Path) -> Path:
    return live_root / "data" / "members" / "staff_directory.json"


def load_registrant_employer_map(path: Path) -> dict[str, list[str]]:
    mapping: defaultdict[str, set[str]] = defaultdict(set)
    for row in read_ndjson_gz(path):
        lda_id = str(row.get("lda_source_person_id") or "").strip()
        employer = str(row.get("employer_name") or "").strip()
        if lda_id and employer:
            mapping[lda_id].add(employer)
    return {key: sorted(values) for key, values in mapping.items()}


def build_lda_queue(
    lda_queue_path: Path, registrant_map: Mapping[str, list[str]]
) -> list[QueuePerson]:
    people: list[QueuePerson] = []
    seen: set[str] = set()
    for row in read_ndjson_gz(lda_queue_path):
        lda_id = str(row.get("lda_source_person_id") or "").strip()
        if not lda_id or lda_id in seen:
            continue
        seen.add(lda_id)
        display_name = str(row.get("display_name") or "").strip()
        if not display_name:
            continue
        name_variants = tuple(
            sorted({str(v).strip() for v in (row.get("name_variants") or []) if str(v).strip()})
        )
        hints: set[str] = set()
        for employer in registrant_map.get(lda_id, []):
            hints.update(tokenize_company(employer))
        people.append(
            QueuePerson(
                subject_kind="lda_lobbyist",
                lda_source_person_id=lda_id,
                quorum_staff_id=None,
                display_name=display_name,
                discovery_hints=tuple(sorted(hints)),
                name_variants=name_variants,
            )
        )
    return people


def build_staffer_queue(staff_directory_path: Path) -> list[QueuePerson]:
    people: list[QueuePerson] = []
    if not staff_directory_path.is_file():
        return people
    data = json.loads(staff_directory_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return people
    for member_name in sorted(data.keys()):
        entries = data.get(member_name) or []
        surname = member_surname(str(member_name))
        hints = (surname,) if surname else ()
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            staff_id = str(entry.get("id") or "").strip()
            name = str(entry.get("n") or "").strip()
            if not staff_id or not name:
                continue
            title = entry.get("t")
            people.append(
                QueuePerson(
                    subject_kind="current_staffer",
                    lda_source_person_id=None,
                    quorum_staff_id=staff_id,
                    display_name=name,
                    discovery_hints=hints,
                    member_office=str(member_name),
                    title=str(title) if title else None,
                )
            )
    return people


def build_queue(args: argparse.Namespace) -> list[QueuePerson]:
    people: list[QueuePerson] = []
    if args.queue in ("lda", "both"):
        registrant_map = load_registrant_employer_map(args.lda_registrant_episodes_path)
        people.extend(build_lda_queue(args.employment_lookup_queue_path, registrant_map))
    if args.queue in ("staffdir", "both"):
        people.extend(build_staffer_queue(args.staff_directory_path))
    return people


# ---------------------------------------------------------------------------
# Identity discipline
# ---------------------------------------------------------------------------


@dataclass
class DiscoveryResult:
    status: str  # "ACCEPTED" | "NO_UNIQUE_CANDIDATE" | "NAME_COLLISION"
    record: dict[str, Any] | None
    matched_tokens: list[str]
    candidate_count: int
    reason: str | None = None


def normalize_name(name: str) -> str:
    stripped = re.sub(r"[^\w\s'-]", " ", name)
    return re.sub(r"\s+", " ", stripped).strip().casefold()


def first_last_tokens(name: str) -> tuple[str, str] | None:
    parts = normalize_name(name).split()
    if len(parts) < 2:
        return None
    return parts[0], parts[-1]


def names_match(expected: str, candidate: str) -> bool:
    a = first_last_tokens(expected)
    b = first_last_tokens(candidate)
    return a is not None and a == b


def experience_text_blobs(record: Mapping[str, Any]) -> list[str]:
    blobs: list[str] = []
    for exp in record.get("experience") or []:
        if isinstance(exp, Mapping):
            blobs.append(str(exp.get("company") or exp.get("company_name") or exp.get("employer") or ""))
            blobs.append(str(exp.get("title") or exp.get("position") or ""))
    current_company = record.get("current_company")
    if isinstance(current_company, Mapping):
        blobs.append(str(current_company.get("name") or ""))
        blobs.append(str(current_company.get("title") or ""))
    elif isinstance(current_company, str):
        blobs.append(current_company)
    for key in ("headline", "position", "current_title"):
        value = record.get(key)
        if isinstance(value, str):
            blobs.append(value)
    return [blob for blob in blobs if blob]


def matched_hint_tokens(hints: Iterable[str], record: Mapping[str, Any]) -> list[str]:
    hints = list(hints)
    if not hints:
        return []
    text_tokens: set[str] = set()
    for blob in experience_text_blobs(record):
        text_tokens.update(match.casefold() for match in TOKEN_RE.findall(blob))
    return sorted(hint for hint in hints if hint in text_tokens)


def evaluate_candidates(person: QueuePerson, records: list[dict[str, Any]]) -> DiscoveryResult:
    name_matched = [r for r in records if names_match(person.display_name, str(r.get("name") or ""))]
    if not person.discovery_hints:
        # Identity discipline is non-negotiable: with no supporting token to
        # test against, this collector will not accept ANY candidate, even a
        # sole name match.
        return DiscoveryResult(
            status="NO_UNIQUE_CANDIDATE",
            record=None,
            matched_tokens=[],
            candidate_count=len(records),
            reason="NO_TOKEN_SUPPORT" if name_matched else "NOT_FOUND",
        )
    surviving = [r for r in name_matched if matched_hint_tokens(person.discovery_hints, r)]
    if len(surviving) == 1:
        record = surviving[0]
        return DiscoveryResult(
            status="ACCEPTED",
            record=record,
            matched_tokens=matched_hint_tokens(person.discovery_hints, record),
            candidate_count=len(records),
        )
    if len(surviving) >= 2:
        return DiscoveryResult(
            status="NAME_COLLISION",
            record=None,
            matched_tokens=[],
            candidate_count=len(records),
            reason="MULTIPLE_TOKEN_SUPPORTED_CANDIDATES",
        )
    return DiscoveryResult(
        status="NO_UNIQUE_CANDIDATE",
        record=None,
        matched_tokens=[],
        candidate_count=len(records),
        reason="NOT_FOUND" if not name_matched else "NO_TOKEN_SUPPORT",
    )


# ---------------------------------------------------------------------------
# Profile -> lane-shape mapping (tolerant; strips everything not whitelisted)
# ---------------------------------------------------------------------------


def parse_date_fragment(raw: Any) -> dict[str, Any] | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.casefold() in CURRENT_WORDS:
        return None
    iso = DATE_ISO_RE.match(text)
    if iso:
        month_s = iso.group("month")
        return {"year": int(iso.group("year")), "month": int(month_s) if month_s else None}
    textual = DATE_TEXT_RE.match(text)
    if textual:
        month = MONTH_LOOKUP.get(textual.group("month").casefold())
        return {"year": int(textual.group("year")), "month": month}
    year_only = YEAR_ONLY_RE.match(text)
    if year_only:
        return {"year": int(year_only.group(1)), "month": None}
    return None


def is_current_marker(raw: Any) -> bool:
    if raw is None:
        return True
    text = str(raw).strip().casefold()
    return text == "" or text in CURRENT_WORDS


def extract_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    match = LEADING_YEAR_RE.match(str(value).strip())
    return int(match.group(1)) if match else None


def map_experience_entry(exp: Mapping[str, Any]) -> dict[str, Any]:
    employer = str(exp.get("company") or exp.get("company_name") or exp.get("employer") or "").strip()
    title = str(exp.get("title") or exp.get("position") or "").strip()
    location = exp.get("location") or exp.get("location_raw")
    location_raw = location.strip() if isinstance(location, str) and location.strip() else None

    raw_start = exp.get("start_date") or exp.get("starts_at") or exp.get("date_from")
    raw_end = exp.get("end_date") or exp.get("ends_at") or exp.get("date_to")

    explicit_current = exp.get("current")
    if not isinstance(explicit_current, bool):
        candidate_flag = exp.get("is_current")
        explicit_current = candidate_flag if isinstance(candidate_flag, bool) else None
    current = bool(explicit_current) if explicit_current is not None else is_current_marker(raw_end)

    start = parse_date_fragment(raw_start)
    end = None if current else parse_date_fragment(raw_end)

    if (start and start.get("month")) or (end and end.get("month")):
        precision = "month"
    elif start or end:
        precision = "year"
    else:
        precision = "none"

    description = exp.get("description")
    description_present = bool(isinstance(description, str) and description.strip())

    return {
        "employer_raw": employer,
        "title_raw": title,
        "location_raw": location_raw,
        "start": start,
        "end": end,
        "current": current,
        "precision": precision,
        "description_present": description_present,
    }


def map_education_entry(edu: Mapping[str, Any]) -> dict[str, Any]:
    institution = str(
        edu.get("institution") or edu.get("school") or edu.get("institution_name") or ""
    ).strip()
    degree = edu.get("degree") or edu.get("degree_name")
    field_of_study = edu.get("field_of_study") or edu.get("field")

    start_year = extract_year(edu.get("start_year"))
    if start_year is None:
        start_year = extract_year(edu.get("starts_at") or edu.get("start_date"))
    end_year = extract_year(edu.get("end_year"))
    if end_year is None:
        end_year = extract_year(edu.get("ends_at") or edu.get("end_date"))

    return {
        "institution_raw": institution,
        "degree_raw": degree.strip() if isinstance(degree, str) and degree.strip() else None,
        "field_raw": (
            field_of_study.strip()
            if isinstance(field_of_study, str) and field_of_study.strip()
            else None
        ),
        "start_year": start_year,
        "end_year": end_year,
    }


def build_evidence_row(
    person: QueuePerson,
    profile: Mapping[str, Any],
    dataset_id: str,
    snapshot_id: str,
    observed_on: str,
    matched_tokens: list[str],
) -> dict[str, Any]:
    profile_url = str(profile.get("url") or profile.get("profile_url") or "").strip()
    employment = [
        map_experience_entry(exp)
        for exp in (profile.get("experience") or [])
        if isinstance(exp, Mapping)
    ]
    education = [
        map_education_entry(edu)
        for edu in (profile.get("education") or [])
        if isinstance(edu, Mapping)
    ]
    row = {
        "schema_id": SCHEMA_ROW,
        "subject_kind": person.subject_kind,
        "lda_source_person_id": person.lda_source_person_id,
        "quorum_staff_id": person.quorum_staff_id,
        "display_name": person.display_name,
        "profile_url": profile_url,
        "observed_on": observed_on,
        "source": "brightdata:linkedin_person_profile",
        "dataset_id": dataset_id,
        "snapshot_id": snapshot_id,
        "employment": employment,
        "education": education,
        "identity_status": "REVIEW_REQUIRED",
        "identity_support": list(matched_tokens),
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_employment_promoted": False,
        "canonical_eligible": False,
        "privacy_class": "restricted-machine-local",
    }
    assert_unpromoted(row, person_key(person))
    return row


# ---------------------------------------------------------------------------
# HTTP layer (calls requests.post / requests.get directly so tests can
# monkeypatch those module attributes, per the task's mocking contract)
# ---------------------------------------------------------------------------


def auth_headers(api_key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def chunked(items: list[Any], size: int) -> Iterator[list[Any]]:
    step = max(1, size)
    for index in range(0, len(items), step):
        yield items[index : index + step]


def trigger_batch(
    api_key: str,
    dataset_id: str,
    input_rows: list[dict[str, Any]],
    *,
    retries: int = 3,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> str:
    last_exc: Exception | None = None
    for attempt in range(retries):
        try:
            response = requests.post(
                TRIGGER_URL,
                params={"dataset_id": dataset_id, "format": "json"},
                headers=auth_headers(api_key),
                json={"input": input_rows},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            snapshot_id = data.get("snapshot_id") if isinstance(data, dict) else None
            if not snapshot_id:
                raise RuntimeError(f"trigger response missing snapshot_id: {data!r}")
            return str(snapshot_id)
        except Exception as exc:  # noqa: BLE001 - retried generically, re-raised on exhaustion
            last_exc = exc
            if attempt < retries - 1:
                sleep_fn(2**attempt)
    raise RuntimeError(f"trigger failed for dataset {dataset_id} after {retries} attempts: {last_exc}")


def poll_until_ready(
    api_key: str,
    snapshot_id: str,
    *,
    poll_interval: int,
    timeout: int,
    sleep_fn: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    deadline = clock() + timeout
    consecutive_errors = 0
    while True:
        try:
            response = requests.get(
                PROGRESS_URL_TMPL.format(snapshot_id=snapshot_id),
                headers=auth_headers(api_key),
                timeout=30,
            )
            response.raise_for_status()
            payload = response.json()
        except Exception as exc:  # noqa: BLE001 - transient poll errors are not a dead snapshot
            # The snapshot is already triggered and already billed. One 429/503 or
            # one dropped connection used to abandon it, losing paid records.
            consecutive_errors += 1
            if consecutive_errors > 5 or clock() >= deadline:
                raise RuntimeError(
                    f"Bright Data snapshot {snapshot_id} progress poll failed "
                    f"{consecutive_errors} time(s): {exc}"
                ) from exc
            sleep_fn(min(poll_interval * (2 ** (consecutive_errors - 1)), 120))
            continue
        consecutive_errors = 0
        status = payload.get("status") if isinstance(payload, dict) else None
        if status == "ready":
            return payload
        if status == "failed":
            raise RuntimeError(f"Bright Data snapshot {snapshot_id} failed")
        if clock() >= deadline:
            raise TimeoutError(f"timed out waiting for snapshot {snapshot_id} (status={status!r})")
        sleep_fn(poll_interval)


def fetch_snapshot(api_key: str, snapshot_id: str) -> list[dict[str, Any]]:
    response = requests.get(
        SNAPSHOT_URL_TMPL.format(snapshot_id=snapshot_id),
        params={"format": "json"},
        headers=auth_headers(api_key),
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, dict) and "results" in data:
        data = data["results"]
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected snapshot payload shape for {snapshot_id}")
    return [row for row in data if isinstance(row, dict)]


def extract_reported_cost(progress_payload: Mapping[str, Any]) -> float | None:
    for key in ("cost", "cost_usd", "price", "total_cost", "total_cost_usd"):
        value = progress_payload.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def resolve_price_per_record(
    assumed_price_per_record: float | None,
    api_key: str,
    dataset_id: str,
) -> tuple[float, str]:
    if assumed_price_per_record is not None:
        return float(assumed_price_per_record), "ASSUMED_CLI_OVERRIDE"
    try:
        response = requests.get(DATASETS_LIST_URL, headers=auth_headers(api_key), timeout=30)
        response.raise_for_status()
        listing = response.json()
    except Exception:  # noqa: BLE001 - price discovery failure is non-fatal
        return 0.0, "UNKNOWN_LOOKUP_FAILED"
    if isinstance(listing, list):
        for entry in listing:
            if isinstance(entry, dict) and str(entry.get("id")) == dataset_id:
                for key in ("price_per_record", "price", "cost_per_record", "record_price_usd"):
                    value = entry.get(key)
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        return float(value), "DATASET_LIST_API"
    return 0.0, "UNKNOWN_NOT_IN_LISTING"


# ---------------------------------------------------------------------------
# Dataset ID / key resolution
# ---------------------------------------------------------------------------


def resolve_dataset_ids(args: argparse.Namespace) -> tuple[str, str]:
    profile_id = args.dataset_id_profile or os.environ.get(
        "BRIGHTDATA_DATASET_ID_LINKEDIN_PERSON_PROFILE"
    )
    search_id = args.dataset_id_search or os.environ.get(
        "BRIGHTDATA_DATASET_ID_LINKEDIN_PEOPLE_SEARCH"
    )
    missing = [
        name
        for name, value in (
            (PIPELINE_NAME_PERSON_PROFILE, profile_id),
            (PIPELINE_NAME_PEOPLE_SEARCH, search_id),
        )
        if not value
    ]
    if missing:
        raise GateFailure(
            "UNKNOWN_DATASET_ID: no Bright Data dataset id configured for: "
            + ", ".join(missing)
            + ". scripts/datasets.sh (expected to hold these verbatim) is not "
            "present in this environment's Bright Data plugin skill cache as of "
            "2026-09-02. Resolve the real id(s) via "
            "`GET https://api.brightdata.com/datasets/list` (see "
            "bright-data-best-practices/references/web-scraper-api.md, "
            "'Finding Dataset IDs') once a key exists, then pass "
            "--dataset-id-profile/--dataset-id-search or set "
            "BRIGHTDATA_DATASET_ID_LINKEDIN_PERSON_PROFILE/"
            "BRIGHTDATA_DATASET_ID_LINKEDIN_PEOPLE_SEARCH. Refusing to guess."
        )
    return str(profile_id), str(search_id)


def load_brightdata_key(args: argparse.Namespace) -> tuple[str | None, str | None]:
    env_key = os.environ.get("BRIGHTDATA_API_KEY")
    env_zone = os.environ.get("BRIGHTDATA_UNLOCKER_ZONE")
    if env_key:
        return env_key, env_zone
    path = args.keys_json
    if not path.is_file():
        return None, env_zone
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, env_zone
    entry = data.get("brightdata") if isinstance(data, dict) else None
    if not isinstance(entry, dict):
        return None, env_zone
    key = entry.get("api_key")
    zone = entry.get("unlocker_zone") or env_zone
    return (str(key) if key else None), (str(zone) if zone else None)


# ---------------------------------------------------------------------------
# Cost cap
# ---------------------------------------------------------------------------


def check_cost_cap(
    num_people: int, price_search: float, price_profile: float, max_cost_usd: float
) -> dict[str, Any]:
    estimated_records = num_people * RECORDS_PER_PERSON_ESTIMATE
    estimated_cost = num_people * (price_search + price_profile)
    if estimated_cost > max_cost_usd:
        raise CostCapExceeded(
            f"estimated cost ${estimated_cost:.4f} for {estimated_records} records "
            f"({num_people} people x (search ${price_search:.4f} + profile "
            f"${price_profile:.4f})/record) exceeds --max-cost-usd {max_cost_usd:.2f}; "
            "aborting before any Bright Data trigger call"
        )
    return {"estimated_records": estimated_records, "estimated_cost_usd": estimated_cost}


# ---------------------------------------------------------------------------
# Manifest (single source of truth for resumability)
# ---------------------------------------------------------------------------


def load_manifest(path: Path) -> dict[str, Any]:
    if path.is_file():
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict) and value.get("schema_id") == SCHEMA_MANIFEST:
            value.setdefault("batches", {})
            value.setdefault("people", {})
            return value
    return {"schema_id": SCHEMA_MANIFEST, "batches": {}, "people": {}}


def save_manifest(path: Path, manifest: Mapping[str, Any]) -> None:
    atomic_write_bytes(
        path, json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
    )


def base_person_entry(person: QueuePerson) -> dict[str, Any]:
    return {
        "subject_kind": person.subject_kind,
        "lda_source_person_id": person.lda_source_person_id,
        "quorum_staff_id": person.quorum_staff_id,
        "display_name": person.display_name,
        "discovery_status": "NOT_STARTED",
        "discovery_reason": None,
        "candidate_count": None,
        "matched_tokens": [],
        "profile_url": None,
        "profile_status": "NOT_STARTED",
        "evidence_row": None,
    }


def batch_id_for(stage: str, person_keys: list[str]) -> str:
    digest = hashlib.sha256(compact({"stage": stage, "people": sorted(person_keys)})).hexdigest()
    return f"{stage}:{digest[:16]}"


def is_batch_fetched(manifest: Mapping[str, Any], stage: str, batch: list[QueuePerson]) -> bool:
    keys = [person_key(p) for p in batch]
    record = manifest["batches"].get(batch_id_for(stage, keys))
    return bool(record and record.get("status") == "FETCHED")


def normalize_url(url: str | None) -> str:
    return (url or "").strip().rstrip("/").casefold()


# ---------------------------------------------------------------------------
# Batch execution
# ---------------------------------------------------------------------------


def build_search_input_row(person: QueuePerson) -> dict[str, Any]:
    parts = person.display_name.strip().split()
    first_name = parts[0] if parts else ""
    last_name = parts[-1] if len(parts) > 1 else ""
    keyword = " ".join(person.discovery_hints) if person.discovery_hints else (person.member_office or "")
    return {"first_name": first_name, "last_name": last_name, "keyword": keyword}


def process_discovery_records(
    batch: list[QueuePerson], records: list[dict[str, Any]], manifest: dict[str, Any]
) -> None:
    for person in batch:
        key = person_key(person)
        result = evaluate_candidates(person, records)
        entry = manifest["people"].setdefault(key, base_person_entry(person))
        entry["discovery_status"] = result.status
        entry["discovery_reason"] = result.reason
        entry["candidate_count"] = result.candidate_count
        entry["matched_tokens"] = result.matched_tokens
        if result.status == "ACCEPTED" and result.record is not None:
            url = str(result.record.get("url") or result.record.get("profile_url") or "").strip()
            entry["profile_url"] = url or None
        else:
            entry["profile_url"] = None


def process_profile_records(
    batch: list[QueuePerson],
    records: list[dict[str, Any]],
    manifest: dict[str, Any],
    dataset_id: str,
    snapshot_id: str,
    observed_on: str,
) -> None:
    by_url: dict[str, dict[str, Any]] = {}
    for record in records:
        url = str(record.get("url") or record.get("profile_url") or "").strip()
        if url:
            by_url[normalize_url(url)] = record
    for person in batch:
        key = person_key(person)
        entry = manifest["people"].setdefault(key, base_person_entry(person))
        target_url = entry.get("profile_url")
        record = by_url.get(normalize_url(target_url)) if target_url else None
        if record is None:
            entry["profile_status"] = "FAILED"
            entry["evidence_row"] = None
            continue
        row = build_evidence_row(
            person, record, dataset_id, snapshot_id, observed_on, entry.get("matched_tokens") or []
        )
        entry["profile_status"] = "FETCHED"
        entry["evidence_row"] = row


def run_stage_batches(
    stage: str,
    people: list[QueuePerson],
    dataset_id: str,
    api_key: str,
    manifest: dict[str, Any],
    *,
    batch_size: int,
    poll_interval: int,
    timeout: int,
    resume: bool,
    concurrency: int,
    build_input_row: Callable[[QueuePerson], dict[str, Any]],
    process_records: Callable[[list[QueuePerson], list[dict[str, Any]], str], None],
    sleep_fn: Callable[[float], None] = time.sleep,
) -> None:
    all_batches = list(chunked(people, batch_size))
    pending = [b for b in all_batches if not (resume and is_batch_fetched(manifest, stage, b))]
    lock = threading.Lock()

    def worker(batch: list[QueuePerson]) -> None:
        keys = [person_key(p) for p in batch]
        batch_id = batch_id_for(stage, keys)
        input_rows = [build_input_row(p) for p in batch]
        snapshot_id = trigger_batch(api_key, dataset_id, input_rows, sleep_fn=sleep_fn)
        progress = poll_until_ready(
            api_key, snapshot_id, poll_interval=poll_interval, timeout=timeout, sleep_fn=sleep_fn
        )
        records = fetch_snapshot(api_key, snapshot_id)
        with lock:
            process_records(batch, records, snapshot_id)
            manifest["batches"][batch_id] = {
                "cost_usd": extract_reported_cost(progress),
                "dataset_id": dataset_id,
                "person_keys": keys,
                "record_count": len(records),
                "snapshot_id": snapshot_id,
                "stage": stage,
                "status": "FETCHED",
            }

    if not pending:
        return
    if concurrency <= 1 or len(pending) <= 1:
        for batch in pending:
            worker(batch)
    else:
        with ThreadPoolExecutor(max_workers=concurrency) as pool:
            futures = [pool.submit(worker, batch) for batch in pending]
            for future in futures:
                future.result()


# ---------------------------------------------------------------------------
# Dry-run plan
# ---------------------------------------------------------------------------


def handle_dry_run(args: argparse.Namespace, people: list[QueuePerson], run_id: str) -> dict[str, Any]:
    lda_people = [p for p in people if p.subject_kind == "lda_lobbyist"]
    staffer_people = [p for p in people if p.subject_kind == "current_staffer"]
    lda_with_hints = sum(1 for p in lda_people if p.discovery_hints)
    staffer_with_hints = sum(1 for p in staffer_people if p.discovery_hints)
    total = len(people)
    return {
        "schema_id": SCHEMA_PLAN,
        "run_id": run_id,
        "mode": "dry-run",
        "queue": args.queue,
        "network_calls_made": 0,
        "queue_counts": {
            "lda_lobbyist": len(lda_people),
            "current_staffer": len(staffer_people),
            "total": total,
        },
        "discovery_hint_coverage": {
            "lda_lobbyist_with_hint": lda_with_hints,
            "lda_lobbyist_without_hint": len(lda_people) - lda_with_hints,
            "current_staffer_with_hint": staffer_with_hints,
            "current_staffer_without_hint": len(staffer_people) - staffer_with_hints,
            "total_with_hint": lda_with_hints + staffer_with_hints,
            "total_without_hint": total - (lda_with_hints + staffer_with_hints),
        },
        "would_search_full_mode": total,
        "would_search_sample_mode": min(args.sample_size, total),
        "sample_size": args.sample_size,
        "cost_formula": (
            "estimated_records = people_attempted * 2 "
            "(1 linkedin_people_search record + up to 1 linkedin_person_profile "
            "record per person, upper bound assuming every search yields a "
            "unique accepted candidate); estimated_cost_usd = people_attempted * "
            "(price_per_record[linkedin_people_search] + "
            "price_per_record[linkedin_person_profile]); price is read from "
            "GET https://api.brightdata.com/datasets/list when a key exists, "
            "else --assumed-price-per-record (default 0.0, flagged UNKNOWN)."
        ),
        "inputs": {
            "employment_lookup_queue": describe_input_file(args.employment_lookup_queue_path),
            "lda_registrant_employment_episodes": describe_input_file(
                args.lda_registrant_episodes_path
            ),
            "staff_directory": describe_input_file(args.staff_directory_path),
        },
        "notes": [
            "dry-run makes zero network calls and requires no Bright Data key.",
            "Dataset IDs are unresolved until --dataset-id-profile/--dataset-id-search "
            "(or the matching env vars) are supplied; sample/full modes will abort "
            "loudly (UNKNOWN_DATASET_ID) before any trigger call if they remain unset.",
        ],
    }


# ---------------------------------------------------------------------------
# Receipt
# ---------------------------------------------------------------------------


def build_receipt(
    args: argparse.Namespace,
    manifest: Mapping[str, Any],
    queue_people: list[QueuePerson],
    selected_people: list[QueuePerson],
    run_id: str,
    price_info: tuple[float, float, str],
    cost_estimate: Mapping[str, Any],
    output_path: Path,
    manifest_path: Path,
) -> dict[str, Any]:
    price_search, price_profile, price_source = price_info
    lda_total = sum(1 for p in queue_people if p.subject_kind == "lda_lobbyist")
    staffer_total = sum(1 for p in queue_people if p.subject_kind == "current_staffer")

    selected_keys = {person_key(p) for p in selected_people}
    people_entries = [
        entry for key, entry in manifest["people"].items() if key in selected_keys
    ]

    outcome_counts = {"accepted": 0, "no_unique_candidate": 0, "name_collision": 0, "not_found": 0}
    for entry in people_entries:
        status = entry.get("discovery_status")
        reason = entry.get("discovery_reason")
        if status == "ACCEPTED":
            outcome_counts["accepted"] += 1
        elif status == "NAME_COLLISION":
            outcome_counts["name_collision"] += 1
        elif status == "NO_UNIQUE_CANDIDATE":
            if reason == "NOT_FOUND":
                outcome_counts["not_found"] += 1
            else:
                outcome_counts["no_unique_candidate"] += 1

    fetched_rows = [
        entry["evidence_row"]
        for entry in people_entries
        if entry.get("profile_status") == "FETCHED" and entry.get("evidence_row")
    ]
    employment_rows = sum(len(row["employment"]) for row in fetched_rows)
    education_rows = sum(len(row["education"]) for row in fetched_rows)
    precision_distribution: Counter[str] = Counter()
    for row in fetched_rows:
        for exp in row["employment"]:
            precision_distribution[exp["precision"]] += 1

    reported_costs = [
        b.get("cost_usd")
        for b in manifest["batches"].values()
        if isinstance(b.get("cost_usd"), (int, float))
    ]
    any_batch_missing_cost = any(
        b.get("cost_usd") is None for b in manifest["batches"].values()
    )
    reported_cost_total = sum(reported_costs) if reported_costs else None
    reported_cost_status = (
        "UNKNOWN"
        if (any_batch_missing_cost or not manifest["batches"])
        else "REPORTED"
    )

    output_bytes = output_path.stat().st_size if output_path.is_file() else 0
    manifest_bytes = manifest_path.stat().st_size if manifest_path.is_file() else 0

    return {
        "schema_id": SCHEMA_RECEIPT,
        "stage_id": STAGE_ID,
        "run_id": run_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": args.mode,
        "queue": args.queue,
        "queue_sizes": {"lda_lobbyist": lda_total, "current_staffer": staffer_total, "total": len(queue_people)},
        "processed": {"attempted": len(selected_people), "resumed": bool(args.resume)},
        "discovery_outcomes": outcome_counts,
        "profiles_fetched": len(fetched_rows),
        "employment_rows": employment_rows,
        "education_rows": education_rows,
        "precision_distribution": dict(sorted(precision_distribution.items())),
        "cost": {
            "search_price_per_record_usd": price_search,
            "profile_price_per_record_usd": price_profile,
            "price_source": price_source,
            "estimated_cost_usd": cost_estimate["estimated_cost_usd"],
            "estimated_records": cost_estimate["estimated_records"],
            "reported_cost_usd": reported_cost_total,
            "reported_cost_status": reported_cost_status,
            "max_cost_usd": args.max_cost_usd,
        },
        "inputs": {
            "employment_lookup_queue": describe_input_file(args.employment_lookup_queue_path),
            "lda_registrant_employment_episodes": describe_input_file(
                args.lda_registrant_episodes_path
            ),
            "staff_directory": describe_input_file(args.staff_directory_path),
        },
        "files": [
            {
                "role": "profile_evidence",
                "path": output_path.name,
                "bytes": output_bytes,
                "sha256": sha(output_path) if output_path.is_file() else None,
                "rows": len(fetched_rows),
            },
            {
                "role": "manifest",
                "path": manifest_path.name,
                "bytes": manifest_bytes,
                "sha256": sha(manifest_path) if manifest_path.is_file() else None,
            },
        ],
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "privacy_class": "restricted-machine-local",
        "notice": NOTICE_SENTENCE,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def execute(
    args: argparse.Namespace,
    selected_people: list[QueuePerson],
    api_key: str,
    dataset_ids: tuple[str, str],
    manifest: dict[str, Any],
) -> None:
    profile_dataset_id, search_dataset_id = dataset_ids
    observed_on = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for person in selected_people:
        manifest["people"].setdefault(person_key(person), base_person_entry(person))

    run_stage_batches(
        "discovery",
        selected_people,
        search_dataset_id,
        api_key,
        manifest,
        batch_size=args.batch_size,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        resume=args.resume,
        concurrency=args.concurrency,
        build_input_row=build_search_input_row,
        process_records=lambda batch, records, snapshot_id: process_discovery_records(
            batch, records, manifest
        ),
    )

    accepted_people = [
        p
        for p in selected_people
        if manifest["people"][person_key(p)]["discovery_status"] == "ACCEPTED"
        and manifest["people"][person_key(p)].get("profile_url")
    ]

    run_stage_batches(
        "profile",
        accepted_people,
        profile_dataset_id,
        api_key,
        manifest,
        batch_size=args.batch_size,
        poll_interval=args.poll_interval,
        timeout=args.timeout,
        resume=args.resume,
        concurrency=args.concurrency,
        build_input_row=lambda p: {"url": manifest["people"][person_key(p)]["profile_url"]},
        process_records=lambda batch, records, snapshot_id: process_profile_records(
            batch, records, manifest, profile_dataset_id, snapshot_id, observed_on
        ),
    )


def run(args: argparse.Namespace, run_id: str) -> dict[str, Any]:
    people = build_queue(args)

    if args.mode == "dry-run":
        plan = handle_dry_run(args, people, run_id)
        args.output_root.mkdir(parents=True, exist_ok=True)
        plan_path = args.output_root / "brightdata_collection_plan.json"
        atomic_write_bytes(plan_path, canonical_line(plan))
        plan["plan_path"] = str(plan_path)
        return plan

    api_key, _unlocker_zone = load_brightdata_key(args)
    if not api_key:
        raise GateFailure(
            "no Bright Data API key available; this collector is usable only once "
            "Paul supplies a key. Add it to "
            f'{args.keys_json} under a top-level "brightdata" entry '
            '{"api_key": "...", "unlocker_zone": "..."}, or set BRIGHTDATA_API_KEY.'
        )
    profile_dataset_id, search_dataset_id = resolve_dataset_ids(args)

    if args.assumed_price_per_record is not None:
        price_search = price_profile = float(args.assumed_price_per_record)
        price_source = "ASSUMED_CLI_OVERRIDE"
    else:
        price_search, source_search = resolve_price_per_record(None, api_key, search_dataset_id)
        price_profile, source_profile = resolve_price_per_record(None, api_key, profile_dataset_id)
        price_source = (
            source_search if source_search == source_profile else f"search={source_search},profile={source_profile}"
        )
        # resolve_price_per_record returns 0.0 when the listing lookup raises or
        # the dataset is absent from the listing. A 0.0 price makes check_cost_cap
        # estimate $0.0000, which can never exceed --max-cost-usd, so one transient
        # HTTP error silently disabled the spend cap. Unknown must refuse, not
        # read as free.
        for _price_label, _price_source in (
            ("search", source_search), ("profile", source_profile)
        ):
            if _price_source.startswith("UNKNOWN"):
                raise CostCapExceeded(
                    f"Bright Data {_price_label} dataset price is unknown "
                    f"({_price_source}); --max-cost-usd cannot be evaluated. "
                    "Re-run with --assumed-price-per-record to state the price."
                )

    selected_people = people if args.mode == "full" else people[: args.sample_size]
    cost_estimate = check_cost_cap(len(selected_people), price_search, price_profile, args.max_cost_usd)

    args.output_root.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output_root / "manifest.json"
    manifest = load_manifest(manifest_path)

    execute(args, selected_people, api_key, (profile_dataset_id, search_dataset_id), manifest)
    save_manifest(manifest_path, manifest)

    selected_keys = {person_key(p) for p in selected_people}
    evidence_rows = [
        entry["evidence_row"]
        for key, entry in manifest["people"].items()
        if key in selected_keys
        and entry.get("profile_status") == "FETCHED"
        and entry.get("evidence_row")
    ]
    evidence_rows.sort(
        key=lambda row: (
            row["subject_kind"],
            row["lda_source_person_id"] or "",
            row["quorum_staff_id"] or "",
        )
    )
    output_path = args.output_root / "brightdata_profile_evidence.ndjson.gz"
    write_gzip(output_path, evidence_rows)

    receipt = build_receipt(
        args,
        manifest,
        people,
        selected_people,
        run_id,
        (price_search, price_profile, price_source),
        cost_estimate,
        output_path,
        manifest_path,
    )
    receipt_path = args.output_root / "brightdata_profile_evidence_receipt.json"
    atomic_write_bytes(receipt_path, canonical_line(receipt))
    receipt["receipt_path"] = str(receipt_path)
    receipt["output_path"] = str(output_path)
    return receipt


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", choices=["lda", "staffdir", "both"], default="both")
    parser.add_argument("--live-root", type=Path, default=Path(DEFAULT_LIVE_ROOT))
    parser.add_argument("--appdata-root", type=Path, default=Path(DEFAULT_APPDATA_ROOT))
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--mode", choices=["dry-run", "sample", "full"], default="dry-run")
    parser.add_argument("--sample-size", type=int, default=3)
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--poll-interval", type=int, default=10)
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--max-cost-usd", type=float, default=25.0)
    parser.add_argument("--assumed-price-per-record", type=float, default=None)
    parser.add_argument("--keys-json", type=Path, default=Path(DEFAULT_KEYS_JSON))
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--batch-size", type=int, default=MAX_TRIGGER_BATCH_SIZE)
    parser.add_argument("--dataset-id-profile", default=None)
    parser.add_argument("--dataset-id-search", default=None)
    parser.add_argument("--employment-lookup-queue-path", type=Path, default=None)
    parser.add_argument("--lda-registrant-episodes-path", type=Path, default=None)
    parser.add_argument("--staff-directory-path", type=Path, default=None)
    parser.add_argument("--glassbox-events-dir", type=Path, default=None)
    return parser


def resolve_paths(args: argparse.Namespace) -> argparse.Namespace:
    args.live_root = args.live_root.resolve()
    args.appdata_root = args.appdata_root.resolve()
    if args.employment_lookup_queue_path is None:
        args.employment_lookup_queue_path = default_lda_queue_path(args.appdata_root)
    else:
        args.employment_lookup_queue_path = args.employment_lookup_queue_path.resolve()
    if args.lda_registrant_episodes_path is None:
        args.lda_registrant_episodes_path = default_registrant_episodes_path(args.live_root)
    else:
        args.lda_registrant_episodes_path = args.lda_registrant_episodes_path.resolve()
    if args.staff_directory_path is None:
        args.staff_directory_path = default_staff_directory_path(args.live_root)
    else:
        args.staff_directory_path = args.staff_directory_path.resolve()
    if args.output_root is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.output_root = args.appdata_root / "brightdata" / f"profile-evidence-{stamp}"
    args.output_root = args.output_root.resolve()
    if args.glassbox_events_dir is None:
        args.glassbox_events_dir = Path(DEFAULT_GLASSBOX_EVENTS_DIR)
    else:
        args.glassbox_events_dir = args.glassbox_events_dir.resolve()
    args.keys_json = args.keys_json.resolve()
    args.batch_size = max(1, min(args.batch_size, MAX_TRIGGER_BATCH_SIZE))
    return args


def main(argv: Iterable[str] | None = None) -> int:
    args = resolve_paths(build_arg_parser().parse_args(argv))
    run_id = new_run_id()
    correlation_id = new_correlation_id()
    emit_glassbox_event(
        args.glassbox_events_dir,
        run_id=run_id,
        correlation_id=correlation_id,
        kind="run.start",
        status="running",
        stage=args.mode,
        summary=f"collect_employment_histories_brightdata start mode={args.mode} queue={args.queue}",
    )
    try:
        result = run(args, run_id)
    except Exception as exc:  # noqa: BLE001 - reported then re-raised
        emit_glassbox_event(
            args.glassbox_events_dir,
            run_id=run_id,
            correlation_id=correlation_id,
            kind="run.fail",
            status="failed",
            stage=args.mode,
            summary=f"collect_employment_histories_brightdata failed: {exc}",
        )
        raise
    emit_glassbox_event(
        args.glassbox_events_dir,
        run_id=run_id,
        correlation_id=correlation_id,
        kind="run.finish",
        status="completed",
        stage=args.mode,
        summary=f"collect_employment_histories_brightdata finished mode={args.mode}",
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
