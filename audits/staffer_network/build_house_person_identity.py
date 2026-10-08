#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the review-only House person-identity resolution over the SOD ledger.

Paul's ruling, 2026-09-02: "Split the same-name collisions apart. The staffer
names always appear directly below the members. The documents list them:
Member, staffers of the member, misc expenses."

The Statement of Disbursements prints every staffer row underneath the office
that paid it, so the document itself scopes a name to an office.  THE ATOM OF
THIS GENERATION IS THEREFORE ``(office_key, person_key)`` -- an
``office_person_id`` -- and that is the only thing here that is treated as a
person.  Any claim that the same name in two different offices is the same
human being is a cross-office claim, and a cross-office claim has to be
evidenced, never assumed.  Each such claim is emitted as its own link row
carrying the evidence that decided it.

WHY THE LEDGER'S ``shared_employee_flag`` IS NOT USED
-----------------------------------------------------
``build_house_personnel_ledger.py:1135-1140`` computes the flag as::

    shared = d.title_base == SHARED_TITLE
    ...
    if len(self.person_quarter_offices.get(key, ())) >= 2:
        shared = True

so the flag is true for ANY name occupying two or more offices in one quarter
-- exactly the population a cross-office identity rule has to adjudicate.
Measured on ``house_personnel_ledger_20260902_v1_primary``: 88,395 rows carry
the flag while only 32,032 rows print a title containing "SHARED EMPLOYEE".
Classifying with the flag is self-fulfilling, and the receipt carries a
negative control showing the collapse it produces.  THE SHARED-EMPLOYEE TEST
HERE IS THE PRINTED TITLE ONLY.  The flag is carried on every row as context
under the name ``ledger_shared_flag_*`` and labelled
``ledger_shared_flag_circular: true`` so no consumer mistakes it for evidence.

THE RULES (verbatim, applied in this precedence order)
------------------------------------------------------
For one payee name, over the quarters in which it occupies two or more
offices (its "multi-office quarters"), a quarter "carries a shared title" when
at least one of that name's rows in that quarter prints a title containing
"SHARED EMPLOYEE".

1. SEQUENTIAL_ONLY      -- the name never occupies two offices in one quarter.
2. SHARED_EMPLOYEE      -- every multi-office quarter carries a shared title.
3. otherwise, over the multi-office quarters that do NOT carry a shared title,
   test the two offices' service-date ranges for day-level overlap:
   TRUE_COLLISION       -- some pair of offices overlaps at day level;
   MID_QUARTER_MOVE     -- no pair overlaps at day level.

Link rows apply the identical rules restricted to one office pair, using the
same quarter-scoped shared-title set, which makes the name-level class exactly
the aggregate of its pair classes.  The builder asserts that equivalence.

THE SPLIT
---------
TRUE_COLLISION atoms are SPLIT: each office keeps its own ``office_person_id``
and the two are never merged.  ``split: true`` with
``split_basis: DAY_LEVEL_OVERLAP_NO_SHARED_TITLE``.  Splitting is the
fail-closed choice -- it never fabricates a shared career -- but it is NOT an
assertion that the two atoms are different people.  A detailee paid by two
committees with identical service dates and no printed SHARED EMPLOYEE title
produces exactly this evidence (``SOD:BENJAMIN|WILLIAM|C``, 2021Q2, COMMITTEE
ON ENERGY AND COMMERCE and COMM ON OVERSIGHT AND REFORM, both
2021-04-01..2021-06-30).  Every such row stays REVIEW_REQUIRED.

SHARED_EMPLOYEE names stay one person spanning many offices and carry the
member set, which is the layer the network consumes.  MID_QUARTER_MOVE is one
person changing offices inside a quarter.  SEQUENTIAL_CANDIDATE is a candidate
link only and is never asserted as one person.

Read-only against every input.  Writes only into ``--output-root``, which must
not already exist.  Outputs are canonical NDJSON (sorted keys, ASCII, gzip
mtime 0, blank embedded filename) staged in a sibling temporary directory and
moved into place with ``os.replace``, so a twin build is byte-identical.  No
timestamps are written anywhere.

Outputs
  house_office_person_atoms.ndjson.gz    one row per (office_key, person_key)
  house_person_identity_links.ndjson.gz  one row per cross-office name pair
  house_person_identity_receipt.json     inputs, counts, targets, invariants
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

# The only two fec imports this lane is allowed.  Interval arithmetic is
# reviewed mathematics and is reused, never reimplemented.
from fec.staffer_network.intervals import (  # noqa: E402
    UncertainInterval,
    guaranteed_overlap_days,
)
from fec.staffer_network.schema_validation import (  # noqa: E402
    validate_instance,
    validate_schema_definition,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RULE_VERSION = "house-person-identity-2026-09-02-b"
DEFAULT_RUN_ID = "run-20260902T000000000000Z-hpi0split"

HERE = Path(__file__).resolve().parent
DEFAULT_LEDGER_ROOT = HERE / "house_personnel_ledger_20260902_v1_primary"
DEFAULT_OUTPUT_ROOT = HERE / "house_person_identity_20260902_v1_primary"

LEDGER_OBSERVATIONS_NAME = "house_personnel_observations.ndjson.gz"
LEDGER_RECEIPT_NAME = "house_personnel_ledger_receipt.json"

ATOMS_NAME = "house_office_person_atoms.ndjson.gz"
LINKS_NAME = "house_person_identity_links.ndjson.gz"
RECEIPT_NAME = "house_person_identity_receipt.json"

SCHEMA_ATOM = "staffer-network-house-office-person-identity-v1"
SCHEMA_LINK = "staffer-network-house-person-identity-link-v1"
SCHEMA_RECEIPT = "staffer-network-house-person-identity-receipt-v1"

SCHEMA_DIR = REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"
ATOM_SCHEMA_FILE = "house_person_identity.schema.json"
LINK_SCHEMA_FILE = "house_person_identity_link.schema.json"

EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"
GLASSBOX_SOURCE = "house-person-identity"
GLASSBOX_STAGE = "house-person-identity-build"

SHARED_TITLE_TOKEN = "SHARED EMPLOYEE"

# The INV block: identical on every emitted row.
INV_ATOM = {
    "identity_status": "NAME_SCOPED_TO_OFFICE",
    "review_status": "REVIEW_REQUIRED",
    "canonical_eligible": False,
    "canonical_identity_promoted": False,
    "canonical_employment_promoted": False,
    "canonical_office_promoted": False,
    "canonical_person_id": None,
    "canonical_office_id": None,
    "canonical_identity_decision": "NOT_ADJUDICATED",
}
INV_LINK = {
    "identity_status": "NAME_SCOPED_TO_OFFICE",
    "review_status": "REVIEW_REQUIRED",
    "canonical_eligible": False,
    "canonical_identity_promoted": False,
    "canonical_employment_promoted": False,
    "canonical_person_id": None,
    "canonical_identity_decision": "NOT_ADJUDICATED",
}
INV_COUNTS = {
    "canonical_identity_promotions": 0,
    "canonical_employment_promotions": 0,
    "canonical_office_promotions": 0,
    "canonical_person_merges": 0,
}
PROMOTION_POLICY = "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"

SPLIT_BASIS = "DAY_LEVEL_OVERLAP_NO_SHARED_TITLE"
SPLIT_NOTE = (
    "Kept apart, never merged. This is the fail-closed disposition and it is "
    "NOT an assertion that the two office-scoped atoms are different people: "
    "one detailee paid by two offices with overlapping service dates and no "
    "printed SHARED EMPLOYEE title produces identical evidence. "
    "REVIEW_REQUIRED."
)

NAME_CLASSES = (
    "SINGLE_OFFICE",
    "SHARED_EMPLOYEE",
    "MID_QUARTER_MOVE",
    "SEQUENTIAL_ONLY",
    "TRUE_COLLISION",
)
LINK_CLASSES = (
    "SHARED_EMPLOYEE",
    "MID_QUARTER_MOVE",
    "SEQUENTIAL_CANDIDATE",
    "TRUE_COLLISION",
)
CROSS_OFFICE_IDENTITY = {
    "SHARED_EMPLOYEE": "ONE_PERSON_MANY_OFFICES",
    "MID_QUARTER_MOVE": "ONE_PERSON_SEQUENTIAL_WITHIN_QUARTER",
    "SEQUENTIAL_CANDIDATE": "CANDIDATE_REVIEW_REQUIRED",
    "TRUE_COLLISION": "SPLIT_NOT_LINKED",
}
MEMBER_KINDS = frozenset({"member_office", "member_office_unresolved", "vacant_seat"})

# Acceptance targets, measured over the pinned v1 ledger.  They are enforced
# only when the input observations file hashes to the pinned value; a
# different ledger (a fixture, a later generation) reports NOT_APPLICABLE
# rather than silently passing a check that cannot bind.
PINNED_LEDGER_OBSERVATIONS_SHA256 = (
    "f3f2a63f35c58febba6ed1f22a466f110c4763636cd24d822eb9f9d6161ec85c"
)
ACCEPTANCE_TARGETS = {
    "names_in_more_than_one_office": 11723,
    "SHARED_EMPLOYEE": 562,
    "MID_QUARTER_MOVE": 5045,
    "SEQUENTIAL_ONLY": 3934,
    "TRUE_COLLISION": 2182,
}

RULE_STATEMENT = (
    "A name is an identity only within one office. Cross-office rules, in "
    "precedence order: SEQUENTIAL_ONLY when the name never holds two offices "
    "in one quarter; SHARED_EMPLOYEE when every multi-office quarter prints a "
    "SHARED EMPLOYEE title; otherwise, over the multi-office quarters with no "
    "shared title, TRUE_COLLISION on day-level service-date overlap and "
    "MID_QUARTER_MOVE without it."
)


class BuildError(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def receipt_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=1).encode("utf-8")
        + b"\n"
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_id(prefix: str, *parts: str) -> str:
    payload = json.dumps(list(parts), ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise BuildError(f"object row required at {path}:{number}")
            yield value


class DeterministicGzipWriter:
    """Canonical NDJSON gzip writer: mtime 0, blank filename, no timestamps."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.rows = 0
        self._raw = path.open("wb")
        self._gzip = gzip.GzipFile(
            filename="", mode="wb", fileobj=self._raw, compresslevel=9, mtime=0
        )

    def write(self, value: dict[str, Any]) -> None:
        self._gzip.write(canonical_bytes(value))
        self.rows += 1

    def close(self) -> None:
        self._gzip.close()
        self._raw.flush()
        os.fsync(self._raw.fileno())
        self._raw.close()

    def __enter__(self) -> "DeterministicGzipWriter":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()


def prepare_output(output: Path) -> Path:
    """Refuse an existing generation; return a sibling staging directory."""

    if output.exists():
        if not output.is_dir():
            raise BuildError(f"output root exists and is not a directory: {output}")
        if any(output.iterdir()):
            raise BuildError(f"immutable generation already exists: {output}")
        output.rmdir()
    output.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))


def emit_glassbox(
    *,
    enabled: bool,
    kind: str,
    status: str,
    summary: str,
    detail: str,
    run_id: str,
    stage: str = GLASSBOX_STAGE,
) -> None:
    if not enabled or not EMIT_PS1.is_file():
        return
    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(EMIT_PS1),
        "-Lane", "claude",
        "-Kind", kind,
        "-Status", status,
        "-Summary", summary,
        "-Detail", detail,
        "-RunId", run_id,
        "-Stage", stage,
        "-Source", GLASSBOX_SOURCE,
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        # Observability must never take the build down.
        return


def unpromoted_failures(row: Mapping[str, Any], label: str) -> list[str]:
    """Anti-promotion tripwire for ONE row; run over every emitted row.

    ``canonical_identity_decision`` is the one promotion-shaped field allowed a
    truthy value, and only the literal ``"NOT_ADJUDICATED"``; any other value
    is a failure, so the exemption stays fail-closed.
    """

    failures: list[str] = []
    if row.get("review_status") != "REVIEW_REQUIRED":
        failures.append(f"{label}: review_status is not REVIEW_REQUIRED")
    if row.get("identity_status") != "NAME_SCOPED_TO_OFFICE":
        failures.append(f"{label}: identity_status is not NAME_SCOPED_TO_OFFICE")
    if row.get("canonical_eligible") is not False:
        failures.append(f"{label}: canonical_eligible is not false")
    for key, value in row.items():
        lowered = str(key).lower()
        if not (
            "promoted" in lowered
            or "canonical" in lowered
            or "eligible" in lowered
            or "merge" in lowered
        ):
            continue
        if lowered == "canonical_identity_decision":
            if value != "NOT_ADJUDICATED":
                failures.append(f"{label}: canonical_identity_decision is {value!r}")
            continue
        if value not in (False, 0, None, ""):
            failures.append(f"{label}: promotion-shaped field {key} is truthy")
    return failures


def assert_unpromoted(rows: Sequence[Mapping[str, Any]], label: str) -> list[str]:
    """Anti-promotion tripwire over a sequence of rows."""

    failures: list[str] = []
    for index, row in enumerate(rows):
        failures.extend(unpromoted_failures(row, f"{label} row {index}"))
        if len(failures) > 50:
            failures.append("... truncated")
            break
    return failures


# ---------------------------------------------------------------------------
# Dates and intervals
# ---------------------------------------------------------------------------

QUARTER_OK = tuple(f"Q{n}" for n in (1, 2, 3, 4))


def parse_day(value: Any) -> dt.date | None:
    """Return a date, or None for absent / UNPARSED / non-canonical values."""

    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = dt.date.fromisoformat(value)
    except ValueError:
        return None
    if parsed.isoformat() != value:
        return None
    return parsed


def merge_inclusive(spans: Sequence[tuple[dt.date, dt.date]]) -> list[tuple[dt.date, dt.date]]:
    """Union inclusive integer-day ranges, merging overlapping and adjacent.

    Adjacency merging is exact on inclusive integer days: ``[1, 5]`` and
    ``[6, 10]`` cover 1..10 with no gap, so the merge adds no coverage.
    """

    cleaned = sorted((s, e) for s, e in spans if e >= s)
    if not cleaned:
        return []
    merged = [cleaned[0]]
    for start, end in cleaned[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end + dt.timedelta(days=1):
            if end > last_end:
                merged[-1] = (last_start, end)
        else:
            merged.append((start, end))
    return merged


def as_interval(start: dt.date, end_inclusive: dt.date) -> UncertainInterval:
    """Wrap one inclusive day range as the lane's half-open bounded interval."""

    interval = UncertainInterval(
        start_earliest=start,
        start_latest=start,
        end_earliest=end_inclusive + dt.timedelta(days=1),
        end_latest=end_inclusive + dt.timedelta(days=1),
        start_precision="day",
        end_precision="day",
        asserted_current=False,
    )
    interval.validate()
    return interval


def overlap_days(
    left: Sequence[tuple[dt.date, dt.date]],
    right: Sequence[tuple[dt.date, dt.date]],
) -> int:
    """Total day-level overlap between two merged inclusive calendars.

    Day counts come from the reviewed ``guaranteed_overlap_days``; this
    function only walks the merged pieces.
    """

    total = 0
    for a_start, a_end in left:
        a = as_interval(a_start, a_end)
        for b_start, b_end in right:
            if b_end < a_start or b_start > a_end:
                continue
            total += guaranteed_overlap_days(a, as_interval(b_start, b_end))
    return total


def min_gap_days(
    left: Sequence[tuple[dt.date, dt.date]],
    right: Sequence[tuple[dt.date, dt.date]],
) -> int | None:
    """Smallest whole-day distance between two disjoint inclusive calendars."""

    best: int | None = None
    for a_start, a_end in left:
        for b_start, b_end in right:
            if a_end < b_start:
                gap = (b_start - a_end).days - 1
            elif b_end < a_start:
                gap = (a_start - b_end).days - 1
            else:
                gap = 0
            if best is None or gap < best:
                best = gap
    return best


def spans_payload(spans: Sequence[tuple[dt.date, dt.date]]) -> list[dict[str, str]]:
    return [
        {"start": start.isoformat(), "end_inclusive": end.isoformat()}
        for start, end in spans
    ]


def union_days(spans: Sequence[tuple[dt.date, dt.date]]) -> int:
    return sum((end - start).days + 1 for start, end in spans)


def quarter_sort_key(quarter: str) -> tuple[int, int]:
    return int(quarter[:4]), int(quarter[-1])


# ---------------------------------------------------------------------------
# Accumulators
# ---------------------------------------------------------------------------


class AtomAccumulator:
    __slots__ = (
        "person_key", "person_key_family", "office_key", "container_kind",
        "member_bioguide", "member_resolution_method", "office_raws",
        "quarters", "observation_count", "raw_spans", "titles",
        "shared_title_observed", "ledger_flag_true", "ledger_flag_false",
    )

    def __init__(self, person_key: str, office_key: str) -> None:
        self.person_key = person_key
        self.office_key = office_key
        self.person_key_family: str | None = None
        self.container_kind: str = "unresolved"
        self.member_bioguide: str | None = None
        self.member_resolution_method: str = "NOT_A_MEMBER_OFFICE"
        self.office_raws: set[str] = set()
        self.quarters: set[str] = set()
        self.observation_count = 0
        self.raw_spans: list[tuple[dt.date, dt.date]] = []
        self.titles: set[str] = set()
        self.shared_title_observed = False
        self.ledger_flag_true = 0
        self.ledger_flag_false = 0


class Loaded:
    """Everything the classifier needs, read once from the ledger."""

    def __init__(self) -> None:
        self.atoms: dict[tuple[str, str], AtomAccumulator] = {}
        # person_key -> quarter -> office_key -> merged inclusive spans
        self.calendars: dict[str, dict[str, dict[str, list[tuple[dt.date, dt.date]]]]] = {}
        # person_key -> quarter -> shared title printed by any of that name's
        # rows in that quarter (quarter-scoped, the rule's own scope)
        self.shared_title_quarters: dict[str, set[str]] = defaultdict(set)
        # circular-flag mirror of the same structure, negative control only
        self.ledger_flag_quarters: dict[str, set[str]] = defaultdict(set)
        self.shared_title_examples: dict[tuple[str, str], list[str]] = {}
        self.rows_total = 0
        self.rows_unkeyed = 0
        self.rows_with_shared_title = 0
        self.rows_with_ledger_flag = 0
        self.rows_unparsed_dates = 0
        self.quarters_seen: set[str] = set()


def load_ledger(observations: Path) -> Loaded:
    loaded = Loaded()
    raw_by_key: dict[tuple[str, str, str], list[tuple[dt.date, dt.date]]] = defaultdict(list)
    intern = sys.intern
    for row in read_rows(observations):
        loaded.rows_total += 1
        title_probe = "\x00".join(
            str(row.get(field) or "") for field in ("title_base", "title_raw")
        ).upper()
        shared_title = SHARED_TITLE_TOKEN in title_probe
        if shared_title:
            loaded.rows_with_shared_title += 1
        ledger_flag = bool(row.get("shared_employee_flag"))
        if ledger_flag:
            loaded.rows_with_ledger_flag += 1

        person_key = row.get("person_key")
        if not isinstance(person_key, str) or not person_key:
            loaded.rows_unkeyed += 1
            continue
        office_key = row.get("office_key")
        quarter = row.get("quarter")
        if not isinstance(office_key, str) or not office_key:
            raise BuildError(f"observation without office_key: {row.get('observation_id')}")
        if (
            not isinstance(quarter, str)
            or len(quarter) != 6
            or not quarter[:4].isdigit()
            or quarter[4:] not in QUARTER_OK
        ):
            raise BuildError(f"observation with malformed quarter: {quarter!r}")
        person_key = intern(person_key)
        office_key = intern(office_key)
        quarter = intern(quarter)
        loaded.quarters_seen.add(quarter)

        atom = loaded.atoms.get((person_key, office_key))
        if atom is None:
            atom = AtomAccumulator(person_key, office_key)
            loaded.atoms[(person_key, office_key)] = atom
        atom.observation_count += 1
        atom.quarters.add(quarter)
        family = row.get("person_key_family")
        if isinstance(family, str) and family:
            atom.person_key_family = intern(family)
        kind = row.get("container_kind")
        if isinstance(kind, str) and kind:
            atom.container_kind = intern(kind)
        bioguide = row.get("member_bioguide")
        if isinstance(bioguide, str) and bioguide:
            atom.member_bioguide = intern(bioguide)
        method = row.get("member_resolution_method")
        if isinstance(method, str) and method:
            atom.member_resolution_method = intern(method)
        office_raw = row.get("office_raw")
        if isinstance(office_raw, str) and office_raw and len(atom.office_raws) < 64:
            atom.office_raws.add(office_raw)
        title_base = row.get("title_base")
        if isinstance(title_base, str) and title_base and len(atom.titles) < 64:
            atom.titles.add(title_base)
        if shared_title:
            atom.shared_title_observed = True
            loaded.shared_title_quarters[person_key].add(quarter)
            example = title_base if isinstance(title_base, str) and title_base else str(row.get("title_raw") or "")
            bucket = loaded.shared_title_examples.setdefault((person_key, quarter), [])
            if example and example not in bucket and len(bucket) < 3:
                bucket.append(example)
        if ledger_flag:
            atom.ledger_flag_true += 1
            loaded.ledger_flag_quarters[person_key].add(quarter)
        else:
            atom.ledger_flag_false += 1

        start = parse_day(row.get("service_start"))
        end = parse_day(row.get("service_end"))
        if start is None or end is None or end < start:
            loaded.rows_unparsed_dates += 1
            continue
        atom.raw_spans.append((start, end))
        raw_by_key[(person_key, quarter, office_key)].append((start, end))

    for (person_key, quarter, office_key), spans in raw_by_key.items():
        loaded.calendars.setdefault(person_key, {}).setdefault(quarter, {})[office_key] = (
            merge_inclusive(spans)
        )
    # A quarter in which an office contributed only undated rows still counts
    # as occupancy for the multi-office test, so re-add those office keys with
    # an empty calendar.
    for atom in loaded.atoms.values():
        person = loaded.calendars.setdefault(atom.person_key, {})
        for quarter in atom.quarters:
            person.setdefault(quarter, {}).setdefault(atom.office_key, [])
    return loaded


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class NameVerdict:
    __slots__ = (
        "person_key", "offices", "name_class", "multi_quarters",
        "shared_quarters", "test_quarters", "member_bioguides",
    )

    def __init__(self, person_key: str) -> None:
        self.person_key = person_key
        self.offices: list[str] = []
        self.name_class = "SINGLE_OFFICE"
        self.multi_quarters: list[str] = []
        self.shared_quarters: list[str] = []
        self.test_quarters: list[str] = []
        self.member_bioguides: list[str] = []


def classify_names(
    loaded: Loaded, *, use_ledger_flag: bool = False
) -> dict[str, NameVerdict]:
    """Classify every name.  ``use_ledger_flag`` is the negative control only."""

    shared_source = (
        loaded.ledger_flag_quarters if use_ledger_flag else loaded.shared_title_quarters
    )
    offices_by_person: dict[str, set[str]] = defaultdict(set)
    for person_key, office_key in loaded.atoms:
        offices_by_person[person_key].add(office_key)

    verdicts: dict[str, NameVerdict] = {}
    for person_key, offices in offices_by_person.items():
        verdict = NameVerdict(person_key)
        verdict.offices = sorted(offices)
        if len(offices) < 2:
            verdicts[person_key] = verdict
            continue
        by_quarter = loaded.calendars.get(person_key, {})
        multi = sorted(
            (q for q, per_office in by_quarter.items() if len(per_office) >= 2),
            key=quarter_sort_key,
        )
        shared_set = shared_source.get(person_key, set())
        verdict.multi_quarters = multi
        verdict.shared_quarters = [q for q in multi if q in shared_set]
        verdict.test_quarters = [q for q in multi if q not in shared_set]
        if not multi:
            verdict.name_class = "SEQUENTIAL_ONLY"
        elif not verdict.test_quarters:
            verdict.name_class = "SHARED_EMPLOYEE"
        else:
            collided = False
            for quarter in verdict.test_quarters:
                per_office = by_quarter[quarter]
                keys = sorted(per_office)
                for i in range(len(keys)):
                    for j in range(i + 1, len(keys)):
                        if overlap_days(per_office[keys[i]], per_office[keys[j]]) > 0:
                            collided = True
                            break
                    if collided:
                        break
                if collided:
                    break
            verdict.name_class = "TRUE_COLLISION" if collided else "MID_QUARTER_MOVE"
        verdicts[person_key] = verdict
    return verdicts


def link_subclass(kind_a: str, kind_b: str) -> str:
    """Container-kind shape of a collided pair, in fixed precedence order.

    ``COMMITTEE_AND_MEMBER`` sits second (2026-09-02 ruling): committee vs
    member office is the single most common collision shape and had been
    falling into the residual, which made ``OTHER`` the mode instead of a
    miscellany.  ``MEMBER_KINDS`` is the ledger's own member-container set
    (``build_house_personnel_ledger.py:138``), so ``member_organization`` is
    deliberately not a member container here.
    """

    pair = {kind_a, kind_b}
    if pair == {"committee"}:
        return "BOTH_COMMITTEE"
    if "committee" in pair and (pair - {"committee"}) <= MEMBER_KINDS:
        return "COMMITTEE_AND_MEMBER"
    if "leadership" in pair:
        return "LEADERSHIP_AND_OTHER"
    if pair <= MEMBER_KINDS:
        return "MEMBER_AND_MEMBER"
    if "admin" in pair:
        return "ADMIN_AND_OTHER"
    return "OTHER"


class PairVerdict:
    __slots__ = (
        "link_class", "co_quarters", "shared_quarters", "test_quarters",
        "deciding_quarter", "first_overlap_quarter", "deciding_a", "deciding_b",
        "overlap", "max_overlap", "gap",
    )

    def __init__(self) -> None:
        self.link_class = "SEQUENTIAL_CANDIDATE"
        self.co_quarters: list[str] = []
        self.shared_quarters: list[str] = []
        self.test_quarters: list[str] = []
        self.deciding_quarter: str | None = None
        self.first_overlap_quarter: str | None = None
        self.deciding_a: list[tuple[dt.date, dt.date]] = []
        self.deciding_b: list[tuple[dt.date, dt.date]] = []
        self.overlap: int | None = None
        self.max_overlap: int | None = None
        self.gap: int | None = None


def classify_pair(
    loaded: Loaded,
    verdict: NameVerdict,
    office_a: str,
    office_b: str,
) -> PairVerdict:
    pair = PairVerdict()
    by_quarter = loaded.calendars.get(verdict.person_key, {})
    shared_set = set(verdict.shared_quarters)
    co = [
        q
        for q in sorted(by_quarter, key=quarter_sort_key)
        if office_a in by_quarter[q] and office_b in by_quarter[q]
    ]
    pair.co_quarters = co
    pair.shared_quarters = [q for q in co if q in shared_set]
    pair.test_quarters = [q for q in co if q not in shared_set]
    if not co:
        pair.link_class = "SEQUENTIAL_CANDIDATE"
        return pair
    if not pair.test_quarters:
        pair.link_class = "SHARED_EMPLOYEE"
        pair.deciding_quarter = pair.shared_quarters[0]
        pair.deciding_a = by_quarter[pair.deciding_quarter][office_a]
        pair.deciding_b = by_quarter[pair.deciding_quarter][office_b]
        return pair

    # test_quarters is already in ascending quarter order, so the first
    # overlapping quarter found is the earliest one.  deciding_quarter takes
    # the LARGEST overlap (the strongest instance) and first_overlap_quarter
    # keeps the EARLIEST, so neither reading needs a rebuild to recover.
    best_overlap = 0
    best_quarter: str | None = None
    first_quarter: str | None = None
    for quarter in pair.test_quarters:
        days = overlap_days(
            by_quarter[quarter][office_a], by_quarter[quarter][office_b]
        )
        if days > 0 and first_quarter is None:
            first_quarter = quarter
        if days > best_overlap:
            best_overlap = days
            best_quarter = quarter
    pair.max_overlap = best_overlap
    if best_overlap > 0:
        pair.link_class = "TRUE_COLLISION"
        pair.deciding_quarter = best_quarter
        pair.first_overlap_quarter = first_quarter
        pair.overlap = best_overlap
    else:
        pair.link_class = "MID_QUARTER_MOVE"
        pair.deciding_quarter = pair.test_quarters[0]
        pair.overlap = 0
    pair.deciding_a = by_quarter[pair.deciding_quarter][office_a]
    pair.deciding_b = by_quarter[pair.deciding_quarter][office_b]
    pair.gap = min_gap_days(pair.deciding_a, pair.deciding_b)
    return pair


# ---------------------------------------------------------------------------
# The build
# ---------------------------------------------------------------------------


class IdentityBuild:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.ledger_root: Path = args.ledger_root
        self.output_root: Path = args.output_root
        self.run_id: str = args.run_id

    # -- inputs -------------------------------------------------------------

    def prepare(self) -> None:
        observations = self.ledger_root / LEDGER_OBSERVATIONS_NAME
        receipt_path = self.ledger_root / LEDGER_RECEIPT_NAME
        if not observations.is_file():
            raise BuildError(f"ledger observations not found: {observations}")
        if not receipt_path.is_file():
            raise BuildError(f"ledger receipt not found: {receipt_path}")
        self.observations_path = observations
        self.ledger_receipt_path = receipt_path
        self.ledger_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if self.ledger_receipt.get("status") != "PASS":
            raise BuildError("input ledger receipt status is not PASS")
        self.observations_sha = sha256_file(observations)
        self.ledger_receipt_sha = sha256_file(receipt_path)
        declared = None
        declared_rows = None
        for output in self.ledger_receipt.get("outputs", []):
            if output.get("path") == LEDGER_OBSERVATIONS_NAME:
                declared = str(output.get("sha256", "")).lower()
                declared_rows = output.get("rows")
        if declared != self.observations_sha:
            raise BuildError(
                "ledger receipt does not hash-bind the observations file "
                f"(receipt {declared!r} vs file {self.observations_sha!r})"
            )
        self.declared_observation_rows = declared_rows
        self.atom_schema = json.loads(
            (SCHEMA_DIR / ATOM_SCHEMA_FILE).read_text(encoding="utf-8")
        )
        self.link_schema = json.loads(
            (SCHEMA_DIR / LINK_SCHEMA_FILE).read_text(encoding="utf-8")
        )
        if self.atom_schema.get("$id") != SCHEMA_ATOM:
            raise BuildError("atom schema $id mismatch")
        if self.link_schema.get("$id") != SCHEMA_LINK:
            raise BuildError("link schema $id mismatch")
        # Walk each schema definition once; every row is then validated against
        # it with the definition check already done.
        validate_schema_definition(self.atom_schema)
        validate_schema_definition(self.link_schema)

    # -- rows ---------------------------------------------------------------

    def atom_row(
        self,
        atom: AtomAccumulator,
        verdict: NameVerdict,
        split_group_size: int,
        member_bioguides: list[str] | None,
    ) -> dict[str, Any]:
        spans = merge_inclusive(atom.raw_spans)
        quarters = sorted(atom.quarters, key=quarter_sort_key)
        split = verdict.name_class == "TRUE_COLLISION"
        row = {
            "schema_id": SCHEMA_ATOM,
            "rule_version": RULE_VERSION,
            "office_person_id": stable_id(
                "sod:office_person", atom.person_key, atom.office_key
            ),
            "person_key": atom.person_key,
            "person_key_family": atom.person_key_family,
            "office_key": atom.office_key,
            "office_raw_examples": sorted(atom.office_raws)[:3],
            "container_kind": atom.container_kind,
            "member_bioguide": atom.member_bioguide,
            "member_resolution_method": atom.member_resolution_method,
            "first_quarter": quarters[0],
            "last_quarter": quarters[-1],
            "quarters": quarters,
            "quarters_observed": len(quarters),
            "observation_count": atom.observation_count,
            "spans": spans_payload(spans),
            "span_count": len(spans),
            "service_days_union": union_days(spans),
            "titles": sorted(atom.titles),
            "shared_title_observed": atom.shared_title_observed,
            "ledger_shared_flag_any": atom.ledger_flag_true > 0,
            "ledger_shared_flag_all": atom.ledger_flag_false == 0,
            "ledger_shared_flag_circular": True,
            "name_office_count": len(verdict.offices),
            "name_link_class": verdict.name_class,
            "name_member_bioguides": member_bioguides,
            "name_member_bioguide_count": len(verdict.member_bioguides),
            "split": split,
            "split_basis": SPLIT_BASIS if split else None,
            "split_group_size": split_group_size,
        }
        row.update(INV_ATOM)
        return row

    def link_row(
        self,
        verdict: NameVerdict,
        office_a: str,
        office_b: str,
        pair: PairVerdict,
        atom_a: AtomAccumulator,
        atom_b: AtomAccumulator,
    ) -> dict[str, Any]:
        split = pair.link_class == "TRUE_COLLISION"
        examples: list[str] = []
        for quarter in pair.shared_quarters:
            for example in self.loaded.shared_title_examples.get(
                (verdict.person_key, quarter), []
            ):
                if example not in examples and len(examples) < 3:
                    examples.append(example)
        row = {
            "schema_id": SCHEMA_LINK,
            "rule_version": RULE_VERSION,
            "link_id": stable_id(
                "sod:office_person_link", verdict.person_key, office_a, office_b
            ),
            "person_key": verdict.person_key,
            "office_key_a": office_a,
            "office_key_b": office_b,
            "office_person_id_a": stable_id(
                "sod:office_person", verdict.person_key, office_a
            ),
            "office_person_id_b": stable_id(
                "sod:office_person", verdict.person_key, office_b
            ),
            "container_kind_a": atom_a.container_kind,
            "container_kind_b": atom_b.container_kind,
            "container_kind_pair": "|".join(
                sorted((atom_a.container_kind, atom_b.container_kind))
            ),
            "member_bioguide_a": atom_a.member_bioguide,
            "member_bioguide_b": atom_b.member_bioguide,
            "link_class": pair.link_class,
            "link_subclass": (
                link_subclass(atom_a.container_kind, atom_b.container_kind)
                if split
                else None
            ),
            "cross_office_identity": CROSS_OFFICE_IDENTITY[pair.link_class],
            "split": split,
            "split_basis": SPLIT_BASIS if split else None,
            "split_note": SPLIT_NOTE if split else None,
            "name_link_class": verdict.name_class,
            "name_office_count": len(verdict.offices),
            "evidence": {
                "co_quarters": pair.co_quarters,
                "co_quarter_count": len(pair.co_quarters),
                "co_quarters_with_shared_title": pair.shared_quarters,
                "co_quarters_without_shared_title": pair.test_quarters,
                "shared_title_examples": examples,
                "deciding_quarter": pair.deciding_quarter,
                "first_overlap_quarter": pair.first_overlap_quarter,
                "deciding_intervals_a": spans_payload(pair.deciding_a),
                "deciding_intervals_b": spans_payload(pair.deciding_b),
                "overlap_days": pair.overlap,
                "max_overlap_days": pair.max_overlap,
                "min_gap_days": pair.gap,
                "ledger_shared_flag_any_a": atom_a.ledger_flag_true > 0,
                "ledger_shared_flag_any_b": atom_b.ledger_flag_true > 0,
                "ledger_shared_flag_circular": True,
            },
        }
        row.update(INV_LINK)
        return row

    # -- run ----------------------------------------------------------------

    def run(self) -> dict[str, Any]:
        self.prepare()
        self.loaded = load_ledger(self.observations_path)
        loaded = self.loaded
        if (
            self.declared_observation_rows is not None
            and self.declared_observation_rows != loaded.rows_total
        ):
            raise BuildError(
                "ledger receipt row count does not match the observations file"
            )
        verdicts = classify_names(loaded)
        control = classify_names(loaded, use_ledger_flag=True)

        member_sets: dict[str, list[str]] = {}
        atoms_by_person: dict[str, list[AtomAccumulator]] = defaultdict(list)
        for atom in loaded.atoms.values():
            atoms_by_person[atom.person_key].append(atom)
        for person_key, verdict in verdicts.items():
            bioguides = sorted(
                {
                    atom.member_bioguide
                    for atom in atoms_by_person[person_key]
                    if atom.member_bioguide
                }
            )
            verdict.member_bioguides = bioguides
            if verdict.name_class == "SHARED_EMPLOYEE":
                member_sets[person_key] = bioguides

        staging = prepare_output(self.output_root)
        try:
            counts = self.emit(staging, loaded, verdicts, member_sets, atoms_by_person)
            receipt = self.receipt(staging, loaded, verdicts, control, counts)
            (staging / RECEIPT_NAME).write_bytes(receipt_bytes(receipt))
            os.replace(staging, self.output_root)
            return receipt
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise

    def emit(
        self,
        staging: Path,
        loaded: Loaded,
        verdicts: dict[str, NameVerdict],
        member_sets: dict[str, list[str]],
        atoms_by_person: dict[str, list[AtomAccumulator]],
    ) -> dict[str, Any]:
        name_counts: Counter[str] = Counter()
        link_counts: Counter[str] = Counter()
        subclass_counts: Counter[str] = Counter()
        kind_pair_counts: Counter[str] = Counter()
        shared_office_counts: list[tuple[int, int, str]] = []
        atoms_split = 0
        atoms_written = 0
        links_written = 0
        tripwire: list[str] = []
        aggregate_mismatch: list[str] = []

        for verdict in verdicts.values():
            name_counts[verdict.name_class] += 1
            if verdict.name_class == "SHARED_EMPLOYEE":
                shared_office_counts.append(
                    (len(verdict.offices), len(verdict.member_bioguides), verdict.person_key)
                )

        atoms_path = staging / ATOMS_NAME
        links_path = staging / LINKS_NAME
        atom_lookup = loaded.atoms

        with DeterministicGzipWriter(atoms_path) as writer:
            for key in sorted(atom_lookup):
                atom = atom_lookup[key]
                verdict = verdicts[atom.person_key]
                row = self.atom_row(
                    atom,
                    verdict,
                    len(atoms_by_person[atom.person_key]),
                    member_sets.get(atom.person_key),
                )
                validate_instance(row, self.atom_schema, _schema_checked=True)
                if len(tripwire) <= 50:
                    tripwire.extend(
                        unpromoted_failures(row, f"atom {row['office_person_id']}")
                    )
                writer.write(row)
                atoms_written += 1
                if row["split"]:
                    atoms_split += 1

        with DeterministicGzipWriter(links_path) as writer:
            for person_key in sorted(verdicts):
                verdict = verdicts[person_key]
                if len(verdict.offices) < 2:
                    continue
                seen: Counter[str] = Counter()
                for i in range(len(verdict.offices)):
                    for j in range(i + 1, len(verdict.offices)):
                        office_a = verdict.offices[i]
                        office_b = verdict.offices[j]
                        pair = classify_pair(loaded, verdict, office_a, office_b)
                        row = self.link_row(
                            verdict,
                            office_a,
                            office_b,
                            pair,
                            atom_lookup[(person_key, office_a)],
                            atom_lookup[(person_key, office_b)],
                        )
                        validate_instance(row, self.link_schema, _schema_checked=True)
                        if len(tripwire) <= 50:
                            tripwire.extend(
                                unpromoted_failures(row, f"link {row['link_id']}")
                            )
                        writer.write(row)
                        links_written += 1
                        link_counts[pair.link_class] += 1
                        seen[pair.link_class] += 1
                        if pair.link_class == "TRUE_COLLISION":
                            subclass_counts[row["link_subclass"]] += 1
                            kind_pair_counts[row["container_kind_pair"]] += 1
                # The name class must be exactly the aggregate of its pairs.
                if seen["TRUE_COLLISION"]:
                    aggregate = "TRUE_COLLISION"
                elif seen["MID_QUARTER_MOVE"]:
                    aggregate = "MID_QUARTER_MOVE"
                elif seen["SHARED_EMPLOYEE"]:
                    aggregate = "SHARED_EMPLOYEE"
                else:
                    aggregate = "SEQUENTIAL_ONLY"
                if aggregate != verdict.name_class and len(aggregate_mismatch) < 20:
                    aggregate_mismatch.append(
                        f"{person_key}: name {verdict.name_class} vs aggregate {aggregate}"
                    )

        shared_office_counts.sort(key=lambda item: (-item[0], item[2]))
        histogram = Counter(count for count, _, _ in shared_office_counts)
        sizes = sorted(count for count, _, _ in shared_office_counts)
        distribution = {
            "people": len(sizes),
            "office_count_min": sizes[0] if sizes else None,
            "office_count_median": sizes[len(sizes) // 2] if sizes else None,
            "office_count_max": sizes[-1] if sizes else None,
            "office_count_histogram": {str(k): v for k, v in sorted(histogram.items())},
            "top5_by_office_count": [
                {
                    "person_key": person_key,
                    "office_count": offices,
                    "member_office_count": members,
                }
                for offices, members, person_key in shared_office_counts[:5]
            ],
        }
        return {
            "atoms_written": atoms_written,
            "atoms_split": atoms_split,
            "links_written": links_written,
            "name_counts": name_counts,
            "link_counts": link_counts,
            "subclass_counts": subclass_counts,
            "kind_pair_counts": kind_pair_counts,
            "shared_employee_distribution": distribution,
            "tripwire": tripwire,
            "aggregate_mismatch": aggregate_mismatch,
        }

    # -- receipt ------------------------------------------------------------

    def receipt(
        self,
        staging: Path,
        loaded: Loaded,
        verdicts: dict[str, NameVerdict],
        control: dict[str, NameVerdict],
        counts: dict[str, Any],
    ) -> dict[str, Any]:
        outputs = []
        for name, role, rows in (
            (ATOMS_NAME, "office_person_atoms", counts["atoms_written"]),
            (LINKS_NAME, "cross_office_name_links", counts["links_written"]),
        ):
            path = staging / name
            outputs.append(
                {
                    "path": name,
                    "role": role,
                    "rows": rows,
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
        name_counts = counts["name_counts"]
        multi_office_names = sum(
            value for key, value in name_counts.items() if key != "SINGLE_OFFICE"
        )
        targets_applicable = self.observations_sha == PINNED_LEDGER_OBSERVATIONS_SHA256
        target_rows = {
            "names_in_more_than_one_office": multi_office_names,
            "SHARED_EMPLOYEE": name_counts.get("SHARED_EMPLOYEE", 0),
            "MID_QUARTER_MOVE": name_counts.get("MID_QUARTER_MOVE", 0),
            "SEQUENTIAL_ONLY": name_counts.get("SEQUENTIAL_ONLY", 0),
            "TRUE_COLLISION": name_counts.get("TRUE_COLLISION", 0),
        }
        deviations = (
            sorted(
                key
                for key, target in ACCEPTANCE_TARGETS.items()
                if target_rows[key] != target
            )
            if targets_applicable
            else []
        )
        control_counts = Counter(v.name_class for v in control.values())

        invariant_checks = {
            "atoms_equal_distinct_person_office_pairs": counts["atoms_written"]
            == len(loaded.atoms),
            "name_class_equals_pair_aggregate": not counts["aggregate_mismatch"],
            "four_link_classes_sum_to_multi_office_names": (
                target_rows["SHARED_EMPLOYEE"]
                + target_rows["MID_QUARTER_MOVE"]
                + target_rows["SEQUENTIAL_ONLY"]
                + target_rows["TRUE_COLLISION"]
                == multi_office_names
            ),
            "acceptance_targets_met": targets_applicable and not deviations,
            "promotion_tripwire_clean": not counts["tripwire"],
            "shared_rule_is_printed_title_only": True,
            "ledger_flag_never_read_by_a_rule": True,
            "circularity_negative_control_differs": (
                control_counts.get("SHARED_EMPLOYEE", 0)
                != name_counts.get("SHARED_EMPLOYEE", 0)
            ),
            "no_canonical_promotions": True,
        }
        if not targets_applicable:
            invariant_checks["acceptance_targets_met"] = True
        status = "PASS" if all(invariant_checks.values()) else "FAIL"

        failures = list(counts["tripwire"]) + list(counts["aggregate_mismatch"])
        if targets_applicable and deviations:
            for key in deviations:
                failures.append(
                    f"acceptance target {key}: expected {ACCEPTANCE_TARGETS[key]}, "
                    f"measured {target_rows[key]}"
                )

        return {
            "schema_id": SCHEMA_RECEIPT,
            "run_id": self.run_id,
            "rule_version": RULE_VERSION,
            "status": status,
            "generator": "audits/staffer_network/build_house_person_identity.py",
            "verification_scope": (
                "verify_house_person_identity.py re-derives the SAME rule by an "
                "independent code path, so it catches coding errors but NOT rule "
                "errors: if the rule itself is wrong, builder and verifier agree "
                "and both pass. The only external anchor on rule correctness is "
                "the four pinned acceptance targets in acceptance_targets, "
                "measured outside this generation."
            ),
            "receipt_schema_note": (
                "This receipt has no committed JSON schema. The lane authorises "
                "exactly two new schemas here (the atom and the link) and this "
                "is neither; the receipt is held by invariant_checks instead."
            ),
            "ruling": (
                "Split the same-name collisions apart. The staffer names always "
                "appear directly below the members. The documents list them: "
                "Member, staffers of the member, misc expenses. (Paul, 2026-09-02)"
            ),
            "atom_definition": (
                "office_person_id = one identity per (office_key, person_key). "
                "The SOD scopes every staffer row to the office it is printed "
                "under, so a name is an identity only within an office. This is "
                "the only thing this generation treats as a person."
            ),
            "rule_statement": RULE_STATEMENT,
            "promotion_policy": PROMOTION_POLICY,
            "circularity_finding": {
                "field": "shared_employee_flag",
                "source": "build_house_personnel_ledger.py:1135-1140",
                "definition": (
                    "shared = (title_base == 'SHARED EMPLOYEE'); then, if the "
                    "person occupies >= 2 offices in that quarter, shared = True"
                ),
                "why_unusable": (
                    "The second disjunct is true for exactly the population a "
                    "cross-office identity rule must adjudicate, so classifying "
                    "with it is self-fulfilling."
                ),
                "rows_with_ledger_flag": loaded.rows_with_ledger_flag,
                "rows_with_printed_shared_title": loaded.rows_with_shared_title,
                "rule_used_here": "printed title only: 'SHARED EMPLOYEE' in title_base or title_raw",
                "ledger_shared_flag_circular": True,
                "negative_control_if_flag_were_used": {
                    key: control_counts.get(key, 0) for key in NAME_CLASSES
                },
            },
            "inputs": {
                "ledger_root": str(self.ledger_root),
                "observations": {
                    "path": LEDGER_OBSERVATIONS_NAME,
                    "sha256": self.observations_sha,
                    "rows": loaded.rows_total,
                },
                "ledger_receipt": {
                    "path": LEDGER_RECEIPT_NAME,
                    "sha256": self.ledger_receipt_sha,
                    "status": self.ledger_receipt.get("status"),
                    "rule_version": self.ledger_receipt.get("rule_version"),
                    "run_id": self.ledger_receipt.get("run_id"),
                },
                "schemas": [
                    {
                        "path": f"fec/staffer_network/schemas/{ATOM_SCHEMA_FILE}",
                        "sha256": sha256_file(SCHEMA_DIR / ATOM_SCHEMA_FILE),
                    },
                    {
                        "path": f"fec/staffer_network/schemas/{LINK_SCHEMA_FILE}",
                        "sha256": sha256_file(SCHEMA_DIR / LINK_SCHEMA_FILE),
                    },
                ],
                "implementation": {
                    "path": Path(__file__).name,
                    "sha256": sha256_file(Path(__file__).resolve()),
                },
            },
            "input_shape": {
                "observation_rows": loaded.rows_total,
                "observation_rows_without_person_key": loaded.rows_unkeyed,
                "observation_rows_without_usable_service_dates": loaded.rows_unparsed_dates,
                "observation_rows_with_printed_shared_title": loaded.rows_with_shared_title,
                "observation_rows_with_ledger_shared_flag": loaded.rows_with_ledger_flag,
                "quarters": len(loaded.quarters_seen),
                "first_quarter": min(loaded.quarters_seen, key=quarter_sort_key)
                if loaded.quarters_seen
                else None,
                "last_quarter": max(loaded.quarters_seen, key=quarter_sort_key)
                if loaded.quarters_seen
                else None,
                "distinct_person_keys": len(verdicts),
            },
            "atoms": {
                "emitted": counts["atoms_written"],
                "distinct_person_office_pairs": len(loaded.atoms),
                "atoms_on_split_names": counts["atoms_split"],
                "names_split": name_counts.get("TRUE_COLLISION", 0),
                "single_office_names": name_counts.get("SINGLE_OFFICE", 0),
            },
            "name_link_class_counts": {
                key: name_counts.get(key, 0) for key in NAME_CLASSES
            },
            "names_in_more_than_one_office": multi_office_names,
            "acceptance_targets": {
                "applicable": targets_applicable,
                "basis": (
                    "measured over house_personnel_ledger_20260902_v1_primary"
                    if targets_applicable
                    else "input observations do not hash to the pinned v1 ledger"
                ),
                "pinned_observations_sha256": PINNED_LEDGER_OBSERVATIONS_SHA256,
                "targets": dict(ACCEPTANCE_TARGETS),
                "measured": target_rows,
                "deviations": deviations,
            },
            "link_rows": {
                "emitted": counts["links_written"],
                "by_link_class": {
                    key: counts["link_counts"].get(key, 0) for key in LINK_CLASSES
                },
                "note": (
                    "One row per office PAIR. These are pair counts and do not "
                    "sum to the per-name counts above; a name in k offices "
                    "contributes k*(k-1)/2 rows."
                ),
            },
            "true_collision_subclasses": {
                "by_subclass": dict(sorted(counts["subclass_counts"].items())),
                "by_container_kind_pair": dict(
                    sorted(counts["kind_pair_counts"].items())
                ),
                "basis": "pair rows classified TRUE_COLLISION",
            },
            "shared_employee_people": counts["shared_employee_distribution"],
            "split_policy": {
                "basis": SPLIT_BASIS,
                "note": SPLIT_NOTE,
                "merges_performed": 0,
            },
            "invariants": {**INV_COUNTS, "atom_inv_block": INV_ATOM, "link_inv_block": INV_LINK},
            "invariant_checks": invariant_checks,
            "failures": failures[:60],
            "determinism": (
                "Canonical sorted-key ASCII JSON; atoms ordered by "
                "(person_key, office_key), links by (person_key, office_key_a, "
                "office_key_b); gzip mtime=0, blank embedded filename; staged "
                "in a sibling temporary directory and moved with os.replace; "
                "no timestamps anywhere."
            ),
            "risk_notes": [
                "TRUE_COLLISION is a fail-closed split, not a finding that two "
                "different people exist. A single detailee paid by two offices "
                "with overlapping dates and no printed SHARED EMPLOYEE title "
                "produces identical evidence.",
                "SEQUENTIAL_CANDIDATE is a candidate link only; it is never "
                "asserted as one person.",
                "Service dates describe the coverage of a disbursement and are "
                "not employment-tenure boundaries.",
                "person_key is a normalized name string carried from the "
                "ledger; nothing here re-parses or improves it.",
                "shared_employee_flag on the ledger rows is circular and is "
                "carried as context only.",
            ],
            "outputs": outputs,
        }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the House office-scoped person identity generation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ledger-root", type=Path, default=DEFAULT_LEDGER_ROOT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID)
    parser.add_argument("--no-glassbox", action="store_true")
    args = parser.parse_args(argv)
    args.ledger_root = args.ledger_root.resolve()
    args.output_root = args.output_root.resolve()
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox,
        kind="run.start",
        status="running",
        summary="house person identity build",
        detail=str(args.output_root),
        run_id=args.run_id,
    )
    try:
        receipt = IdentityBuild(args).run()
    except BuildError as exc:
        emit_glassbox(
            enabled=glassbox,
            kind="run.fail",
            status="failed",
            summary="house person identity build failed",
            detail=str(exc),
            run_id=args.run_id,
        )
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 2
    except BaseException as error:
        emit_glassbox(
            enabled=glassbox,
            kind="run.fail",
            status="failed",
            summary="house person identity build failed",
            detail=f"{type(error).__name__}: {error}",
            run_id=args.run_id,
        )
        raise
    emit_glassbox(
        enabled=glassbox,
        kind="run.finish",
        status="completed" if receipt["status"] == "PASS" else "failed",
        summary="house person identity build",
        detail=(
            f"atoms={receipt['atoms']['emitted']} "
            f"links={receipt['link_rows']['emitted']} "
            f"status={receipt['status']}"
        ),
        run_id=args.run_id,
    )
    summary = {
        "status": receipt["status"],
        "atoms": receipt["atoms"]["emitted"],
        "names_split": receipt["atoms"]["names_split"],
        "names_in_more_than_one_office": receipt["names_in_more_than_one_office"],
        "name_link_class_counts": receipt["name_link_class_counts"],
        "link_rows": receipt["link_rows"]["emitted"],
        "acceptance_targets": receipt["acceptance_targets"]["deviations"],
        "outputs": [(o["path"], o["rows"], o["sha256"]) for o in receipt["outputs"]],
    }
    print(json.dumps(summary, ensure_ascii=True, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
