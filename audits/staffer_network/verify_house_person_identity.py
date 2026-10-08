#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independently verify a House person-identity generation.

This script NEVER imports ``build_house_person_identity``.  It re-reads the
ledger, re-derives every office-scoped atom, every name class and every
office-pair link class with its own code -- raw unmerged inclusive-day
intervals and a naive pairwise test, deliberately a different code path from
the builder's merged-calendar / ``intervals.py`` arithmetic -- and compares
the result row by row against what was emitted.  It also:

* re-binds the ledger observations, the ledger receipt and both committed
  schemas by sha256, and gates on the ledger receipt being PASS;
* validates every emitted atom and link row against the committed schemas;
* re-runs the anti-promotion tripwire over every row;
* checks the split invariant -- every atom of a TRUE_COLLISION name carries
  ``split: true`` and a distinct ``office_person_id``, and no two atoms
  anywhere collide on that id;
* re-runs the circularity negative control, confirming that classifying with
  the ledger's ``shared_employee_flag`` gives a DIFFERENT answer, which is
  what proves the emitted classification did not read that field;
* checks primary/twin byte identity of all three output files.

It writes its own receipt and exits 1 on FAIL.  The verification receipt has
no committed JSON schema: the lane authorises exactly two new schemas and this
is neither.
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

from fec.staffer_network.schema_validation import (  # noqa: E402
    SchemaValidationError,
    validate_instance,
    validate_schema_definition,
)

HERE = Path(__file__).resolve().parent
SCHEMA_DIR = REPOSITORY_ROOT / "fec" / "staffer_network" / "schemas"

LEDGER_OBSERVATIONS_NAME = "house_personnel_observations.ndjson.gz"
LEDGER_RECEIPT_NAME = "house_personnel_ledger_receipt.json"
ATOMS_NAME = "house_office_person_atoms.ndjson.gz"
LINKS_NAME = "house_person_identity_links.ndjson.gz"
RECEIPT_NAME = "house_person_identity_receipt.json"
VERIFICATION_NAME = "house_person_identity_verification_receipt.json"

ATOM_SCHEMA_FILE = "house_person_identity.schema.json"
LINK_SCHEMA_FILE = "house_person_identity_link.schema.json"

EMIT_PS1 = Path.home() / ".claude" / "glassbox" / "emit.ps1"
GLASSBOX_SOURCE = "house-person-identity"
GLASSBOX_STAGE = "house-person-identity-verify"

SHARED_TITLE_TOKEN = "SHARED EMPLOYEE"
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
NAME_CLASSES = (
    "SINGLE_OFFICE", "SHARED_EMPLOYEE", "MID_QUARTER_MOVE", "SEQUENTIAL_ONLY",
    "TRUE_COLLISION",
)
LINK_CLASSES = (
    "SHARED_EMPLOYEE", "MID_QUARTER_MOVE", "SEQUENTIAL_CANDIDATE",
    "TRUE_COLLISION",
)
EXPECTED_CROSS_OFFICE_IDENTITY = {
    "SHARED_EMPLOYEE": "ONE_PERSON_MANY_OFFICES",
    "MID_QUARTER_MOVE": "ONE_PERSON_SEQUENTIAL_WITHIN_QUARTER",
    "SEQUENTIAL_CANDIDATE": "CANDIDATE_REVIEW_REQUIRED",
    "TRUE_COLLISION": "SPLIT_NOT_LINKED",
}


class Failures:
    def __init__(self) -> None:
        self.items: list[str] = []

    def check(self, condition: bool, message: str) -> bool:
        if not condition:
            self.add(message)
        return bool(condition)

    def add(self, message: str) -> None:
        if len(self.items) < 200:
            self.items.append(message)
        elif len(self.items) == 200:
            self.items.append("... truncated")

    @property
    def ok(self) -> bool:
        return not self.items


# ---------------------------------------------------------------------------
# io (independent of the builder)
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def receipt_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, indent=1).encode("utf-8")
        + b"\n"
    )


def stable_id(prefix: str, *parts: str) -> str:
    """Re-derived here from the documented recipe, not imported."""

    payload = json.dumps(list(parts), ensure_ascii=True, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


def emit_glassbox(
    *, enabled: bool, kind: str, status: str, summary: str, detail: str, run_id: str
) -> None:
    if not enabled or not EMIT_PS1.is_file():
        return
    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(EMIT_PS1),
        "-Lane", "claude", "-Kind", kind, "-Status", status,
        "-Summary", summary, "-Detail", detail, "-RunId", run_id,
        "-Stage", GLASSBOX_STAGE, "-Source", GLASSBOX_SOURCE,
    ]
    try:
        subprocess.run(command, check=False, capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return


# ---------------------------------------------------------------------------
# the independent re-derivation
# ---------------------------------------------------------------------------


def parse_day(value: Any) -> dt.date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        year, month, day = value.split("-")
        return dt.date(int(year), int(month), int(day))
    except (ValueError, TypeError):
        return None


def inclusive_overlap(
    left: Sequence[tuple[dt.date, dt.date]],
    right: Sequence[tuple[dt.date, dt.date]],
) -> bool:
    """Naive pairwise inclusive-day overlap over RAW, unmerged ranges."""

    for a_start, a_end in left:
        for b_start, b_end in right:
            if a_start <= b_end and b_start <= a_end:
                return True
    return False


class Rederived:
    def __init__(self) -> None:
        # person -> quarter -> office -> raw inclusive ranges
        self.by_person: dict[str, dict[str, dict[str, list[tuple[dt.date, dt.date]]]]] = {}
        self.shared_title_quarters: dict[str, set[str]] = defaultdict(set)
        self.ledger_flag_quarters: dict[str, set[str]] = defaultdict(set)
        self.atom_keys: set[tuple[str, str]] = set()
        # (person, office) -> container_kind, last row in file order wins,
        # matching how the builder accumulates it.
        self.container_kind: dict[tuple[str, str], str] = {}
        self.rows_total = 0
        self.rows_unkeyed = 0
        self.rows_shared_title = 0
        self.rows_ledger_flag = 0
        self.name_class: dict[str, str] = {}
        self.control_class: dict[str, str] = {}


def rederive(observations: Path) -> Rederived:
    state = Rederived()
    for row in read_rows(observations):
        state.rows_total += 1
        title = "\x00".join(
            str(row.get(field) or "") for field in ("title_base", "title_raw")
        ).upper()
        shared_title = SHARED_TITLE_TOKEN in title
        flag = bool(row.get("shared_employee_flag"))
        if shared_title:
            state.rows_shared_title += 1
        if flag:
            state.rows_ledger_flag += 1
        person = row.get("person_key")
        if not isinstance(person, str) or not person:
            state.rows_unkeyed += 1
            continue
        office = row["office_key"]
        quarter = row["quarter"]
        state.atom_keys.add((person, office))
        kind = row.get("container_kind")
        if isinstance(kind, str) and kind:
            state.container_kind[(person, office)] = kind
        bucket = state.by_person.setdefault(person, {}).setdefault(quarter, {})
        ranges = bucket.setdefault(office, [])
        if shared_title:
            state.shared_title_quarters[person].add(quarter)
        if flag:
            state.ledger_flag_quarters[person].add(quarter)
        start = parse_day(row.get("service_start"))
        end = parse_day(row.get("service_end"))
        if start is not None and end is not None and end >= start:
            ranges.append((start, end))

    for use_flag in (False, True):
        source = state.ledger_flag_quarters if use_flag else state.shared_title_quarters
        target = state.control_class if use_flag else state.name_class
        for person, quarters in state.by_person.items():
            offices = {office for per_office in quarters.values() for office in per_office}
            if len(offices) < 2:
                target[person] = "SINGLE_OFFICE"
                continue
            multi = [q for q, per_office in quarters.items() if len(per_office) >= 2]
            if not multi:
                target[person] = "SEQUENTIAL_ONLY"
                continue
            shared = source.get(person, set())
            test = [q for q in multi if q not in shared]
            if not test:
                target[person] = "SHARED_EMPLOYEE"
                continue
            collided = False
            for quarter in test:
                per_office = quarters[quarter]
                keys = list(per_office)
                for i in range(len(keys)):
                    for j in range(i + 1, len(keys)):
                        if inclusive_overlap(per_office[keys[i]], per_office[keys[j]]):
                            collided = True
                            break
                    if collided:
                        break
                if collided:
                    break
            target[person] = "TRUE_COLLISION" if collided else "MID_QUARTER_MOVE"
    return state


def rederive_link_class(
    state: Rederived, person: str, office_a: str, office_b: str
) -> tuple[str, str | None]:
    """Return ``(link_class, first_overlap_quarter)`` for one office pair."""

    quarters = state.by_person[person]
    shared = state.shared_title_quarters.get(person, set())
    co = [q for q, per_office in quarters.items() if office_a in per_office and office_b in per_office]
    if not co:
        return "SEQUENTIAL_CANDIDATE", None
    test = sorted(
        (q for q in co if q not in shared),
        key=lambda q: (int(q[:4]), int(q[-1])),
    )
    if not test:
        return "SHARED_EMPLOYEE", None
    for quarter in test:
        per_office = quarters[quarter]
        if inclusive_overlap(per_office[office_a], per_office[office_b]):
            return "TRUE_COLLISION", quarter
    return "MID_QUARTER_MOVE", None


MEMBER_KINDS = frozenset({"member_office", "member_office_unresolved", "vacant_seat"})


def rederive_subclass(kind_a: str, kind_b: str) -> str:
    """Independent re-derivation of the collided-pair container shape."""

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


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------


def unpromoted_failures(row: Mapping[str, Any], label: str) -> list[str]:
    failures: list[str] = []
    if row.get("review_status") != "REVIEW_REQUIRED":
        failures.append(f"{label}: review_status is not REVIEW_REQUIRED")
    if row.get("identity_status") != "NAME_SCOPED_TO_OFFICE":
        failures.append(f"{label}: identity_status is not NAME_SCOPED_TO_OFFICE")
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


def verify(args: argparse.Namespace) -> dict[str, Any]:
    failures = Failures()
    ledger_root: Path = args.ledger_root
    primary: Path = args.primary_root
    twin: Path | None = args.twin_root

    observations = ledger_root / LEDGER_OBSERVATIONS_NAME
    ledger_receipt_path = ledger_root / LEDGER_RECEIPT_NAME
    for path in (observations, ledger_receipt_path, primary / ATOMS_NAME,
                 primary / LINKS_NAME, primary / RECEIPT_NAME):
        if not path.is_file():
            raise SystemExit(f"VERIFY FAILED: missing input {path}")

    observations_sha = sha256_file(observations)
    ledger_receipt = json.loads(ledger_receipt_path.read_text(encoding="utf-8"))
    failures.check(ledger_receipt.get("status") == "PASS", "ledger receipt is not PASS")
    declared = None
    for output in ledger_receipt.get("outputs", []):
        if output.get("path") == LEDGER_OBSERVATIONS_NAME:
            declared = str(output.get("sha256", "")).lower()
    failures.check(
        declared == observations_sha,
        f"ledger receipt does not hash-bind observations ({declared} vs {observations_sha})",
    )

    receipt = json.loads((primary / RECEIPT_NAME).read_text(encoding="utf-8"))
    failures.check(receipt.get("status") == "PASS", "primary receipt is not PASS")
    failures.check(
        (receipt.get("inputs", {}).get("observations", {}).get("sha256"))
        == observations_sha,
        "primary receipt does not bind the observations file it was verified against",
    )

    atom_schema = json.loads((SCHEMA_DIR / ATOM_SCHEMA_FILE).read_text(encoding="utf-8"))
    link_schema = json.loads((SCHEMA_DIR / LINK_SCHEMA_FILE).read_text(encoding="utf-8"))
    validate_schema_definition(atom_schema)
    validate_schema_definition(link_schema)
    declared_schemas = {
        entry["path"]: entry["sha256"] for entry in receipt.get("inputs", {}).get("schemas", [])
    }
    for filename in (ATOM_SCHEMA_FILE, LINK_SCHEMA_FILE):
        key = f"fec/staffer_network/schemas/{filename}"
        failures.check(
            declared_schemas.get(key) == sha256_file(SCHEMA_DIR / filename),
            f"receipt does not bind the committed schema {filename}",
        )

    state = rederive(observations)

    # -- atoms --------------------------------------------------------------
    atom_ids: set[str] = set()
    atom_keys: set[tuple[str, str]] = set()
    emitted_name_class: dict[str, str] = {}
    atoms_split = 0
    schema_errors = 0
    tripwire: list[str] = []
    split_ids_by_name: dict[str, set[str]] = defaultdict(set)
    previous_sort_key: tuple[str, str] | None = None
    order_ok = True
    atoms_seen = 0
    for row in read_rows(primary / ATOMS_NAME):
        atoms_seen += 1
        if schema_errors < 5:
            try:
                validate_instance(row, atom_schema, _schema_checked=True)
            except SchemaValidationError as exc:
                schema_errors += 1
                failures.add(f"atom schema: {exc}")
        if len(tripwire) < 20:
            tripwire.extend(unpromoted_failures(row, f"atom {row.get('office_person_id')}"))
        key = (row["person_key"], row["office_key"])
        sort_key = key
        if previous_sort_key is not None and sort_key < previous_sort_key:
            order_ok = False
        previous_sort_key = sort_key
        atom_keys.add(key)
        atom_ids.add(row["office_person_id"])
        expected_id = stable_id("sod:office_person", key[0], key[1])
        if row["office_person_id"] != expected_id:
            failures.add(f"atom id mismatch for {key}")
        emitted_name_class[row["person_key"]] = row["name_link_class"]
        expected_class = state.name_class.get(row["person_key"])
        if row["name_link_class"] != expected_class:
            failures.add(
                f"atom {key}: name_link_class {row['name_link_class']} vs "
                f"independently derived {expected_class}"
            )
        if row["split"] != (expected_class == "TRUE_COLLISION"):
            failures.add(f"atom {key}: split flag disagrees with the class")
        if row["split"]:
            atoms_split += 1
            split_ids_by_name[row["person_key"]].add(row["office_person_id"])
            if row["split_basis"] != "DAY_LEVEL_OVERLAP_NO_SHARED_TITLE":
                failures.add(f"atom {key}: wrong split_basis")
        elif row["split_basis"] is not None:
            failures.add(f"atom {key}: split_basis set on an unsplit atom")
        if row["ledger_shared_flag_circular"] is not True:
            failures.add(f"atom {key}: circular flag is not labelled")
        if row["name_link_class"] == "SHARED_EMPLOYEE":
            if row["name_member_bioguides"] is None:
                failures.add(f"atom {key}: shared employee without a member set")
        elif row["name_member_bioguides"] is not None:
            failures.add(f"atom {key}: member set on a non-shared name")
    tripwire_failures = list(tripwire)
    for message in tripwire_failures[:20]:
        failures.add(message)
    failures.check(order_ok, "atom rows are not sorted by (person_key, office_key)")
    failures.check(
        atom_keys == state.atom_keys,
        f"atom universe differs: emitted {len(atom_keys)} vs derived {len(state.atom_keys)}",
    )
    failures.check(
        len(atom_ids) == len(atom_keys), "office_person_id collision between two atoms"
    )
    for person, ids in split_ids_by_name.items():
        expected = sum(1 for key in state.atom_keys if key[0] == person)
        failures.check(
            len(ids) == expected,
            f"split name {person} does not keep one identity per office",
        )

    # -- links --------------------------------------------------------------
    link_counts: Counter[str] = Counter()
    subclass_counts: Counter[str] = Counter()
    links_seen = 0
    link_pairs: set[tuple[str, str, str]] = set()
    link_schema_errors = 0
    link_tripwire: list[str] = []
    aggregate: dict[str, Counter[str]] = defaultdict(Counter)
    for row in read_rows(primary / LINKS_NAME):
        links_seen += 1
        if link_schema_errors < 5:
            try:
                validate_instance(row, link_schema, _schema_checked=True)
            except SchemaValidationError as exc:
                link_schema_errors += 1
                failures.add(f"link schema: {exc}")
        if len(link_tripwire) < 20:
            link_tripwire.extend(unpromoted_failures(row, f"link {row.get('link_id')}"))
        person = row["person_key"]
        office_a, office_b = row["office_key_a"], row["office_key_b"]
        if office_a >= office_b:
            failures.add(f"link {row['link_id']}: office pair is not ordered")
        link_pairs.add((person, office_a, office_b))
        expected, expected_first = rederive_link_class(state, person, office_a, office_b)
        if row["link_class"] != expected:
            failures.add(
                f"link {person} {office_a}|{office_b}: link_class "
                f"{row['link_class']} vs independently derived {expected}"
            )
        if row["evidence"]["first_overlap_quarter"] != expected_first:
            failures.add(
                f"link {row['link_id']}: first_overlap_quarter "
                f"{row['evidence']['first_overlap_quarter']} vs independently "
                f"derived {expected_first}"
            )
        deciding = row["evidence"]["deciding_quarter"]
        if expected_first is not None and deciding is not None:
            if (int(deciding[:4]), int(deciding[-1])) < (
                int(expected_first[:4]), int(expected_first[-1])
            ):
                failures.add(
                    f"link {row['link_id']}: deciding_quarter precedes the first "
                    f"overlapping quarter"
                )
        if row["cross_office_identity"] != EXPECTED_CROSS_OFFICE_IDENTITY[row["link_class"]]:
            failures.add(f"link {row['link_id']}: cross_office_identity disagrees")
        if row["split"] != (row["link_class"] == "TRUE_COLLISION"):
            failures.add(f"link {row['link_id']}: split flag disagrees with link_class")
        if row["split"]:
            if row["link_subclass"] is None:
                failures.add(f"link {row['link_id']}: split without a subclass")
            if not row["split_note"] or "NOT an assertion" not in row["split_note"]:
                failures.add(f"link {row['link_id']}: split note does not disclaim")
            expected_subclass = rederive_subclass(
                state.container_kind.get((person, office_a), "unresolved"),
                state.container_kind.get((person, office_b), "unresolved"),
            )
            if row["link_subclass"] != expected_subclass:
                failures.add(
                    f"link {row['link_id']}: link_subclass {row['link_subclass']} "
                    f"vs independently derived {expected_subclass}"
                )
            subclass_counts[row["link_subclass"]] += 1
        elif row["link_subclass"] is not None:
            failures.add(f"link {row['link_id']}: subclass on an unsplit link")
        if row["link_id"] != stable_id("sod:office_person_link", person, office_a, office_b):
            failures.add(f"link {row['link_id']}: id mismatch")
        if row["evidence"]["ledger_shared_flag_circular"] is not True:
            failures.add(f"link {row['link_id']}: circular flag is not labelled")
        link_counts[row["link_class"]] += 1
        aggregate[person][row["link_class"]] += 1
    for message in link_tripwire[:20]:
        failures.add(message)

    expected_pairs = 0
    offices_by_person: dict[str, list[str]] = defaultdict(list)
    for person, office in sorted(state.atom_keys):
        offices_by_person[person].append(office)
    for person, offices in offices_by_person.items():
        if len(offices) > 1:
            expected_pairs += len(offices) * (len(offices) - 1) // 2
    failures.check(
        links_seen == expected_pairs,
        f"link rows {links_seen} vs expected office pairs {expected_pairs}",
    )
    failures.check(
        len(link_pairs) == links_seen, "duplicate link row for one office pair"
    )

    # name class must be exactly the aggregate of its pair classes
    for person, seen in aggregate.items():
        if seen["TRUE_COLLISION"]:
            derived = "TRUE_COLLISION"
        elif seen["MID_QUARTER_MOVE"]:
            derived = "MID_QUARTER_MOVE"
        elif seen["SHARED_EMPLOYEE"]:
            derived = "SHARED_EMPLOYEE"
        else:
            derived = "SEQUENTIAL_ONLY"
        if derived != emitted_name_class.get(person):
            failures.add(
                f"{person}: pair aggregate {derived} vs atom class "
                f"{emitted_name_class.get(person)}"
            )

    # -- counts, targets and the negative control ---------------------------
    derived_name_counts = Counter(state.name_class.values())
    control_counts = Counter(state.control_class.values())
    multi_office_names = sum(
        value for key, value in derived_name_counts.items() if key != "SINGLE_OFFICE"
    )
    receipt_name_counts = receipt.get("name_link_class_counts", {})
    for key in NAME_CLASSES:
        failures.check(
            receipt_name_counts.get(key, 0) == derived_name_counts.get(key, 0),
            f"receipt name count for {key}: {receipt_name_counts.get(key)} vs "
            f"independently derived {derived_name_counts.get(key, 0)}",
        )
    receipt_link_counts = receipt.get("link_rows", {}).get("by_link_class", {})
    for key in LINK_CLASSES:
        failures.check(
            receipt_link_counts.get(key, 0) == link_counts.get(key, 0),
            f"receipt link count for {key} disagrees with the emitted rows",
        )

    targets_applicable = observations_sha == PINNED_LEDGER_OBSERVATIONS_SHA256
    measured = {
        "names_in_more_than_one_office": multi_office_names,
        "SHARED_EMPLOYEE": derived_name_counts.get("SHARED_EMPLOYEE", 0),
        "MID_QUARTER_MOVE": derived_name_counts.get("MID_QUARTER_MOVE", 0),
        "SEQUENTIAL_ONLY": derived_name_counts.get("SEQUENTIAL_ONLY", 0),
        "TRUE_COLLISION": derived_name_counts.get("TRUE_COLLISION", 0),
    }
    deviations = []
    if targets_applicable:
        deviations = sorted(
            key for key, target in ACCEPTANCE_TARGETS.items() if measured[key] != target
        )
        for key in deviations:
            failures.add(
                f"acceptance target {key}: expected {ACCEPTANCE_TARGETS[key]}, "
                f"independently measured {measured[key]}"
            )

    control_differs = control_counts.get("SHARED_EMPLOYEE", 0) != derived_name_counts.get(
        "SHARED_EMPLOYEE", 0
    )
    failures.check(
        control_differs,
        "circularity negative control did not differ; the emitted classification "
        "cannot be shown to be independent of shared_employee_flag",
    )
    receipt_control = (
        receipt.get("circularity_finding", {}).get("negative_control_if_flag_were_used", {})
    )
    for key in NAME_CLASSES:
        failures.check(
            receipt_control.get(key, 0) == control_counts.get(key, 0),
            f"receipt negative control for {key} disagrees",
        )
    failures.check(
        receipt.get("circularity_finding", {}).get("rows_with_printed_shared_title")
        == state.rows_shared_title,
        "receipt printed-shared-title row count disagrees",
    )
    failures.check(
        receipt.get("circularity_finding", {}).get("rows_with_ledger_flag")
        == state.rows_ledger_flag,
        "receipt ledger-flag row count disagrees",
    )

    # -- outputs and twin ---------------------------------------------------
    for output in receipt.get("outputs", []):
        path = primary / output["path"]
        failures.check(
            sha256_file(path) == output["sha256"],
            f"primary receipt sha256 does not match {output['path']}",
        )
    twin_identical = None
    twin_detail: dict[str, Any] = {}
    if twin is not None:
        twin_identical = True
        for name in (ATOMS_NAME, LINKS_NAME, RECEIPT_NAME):
            left, right = primary / name, twin / name
            if not right.is_file():
                twin_identical = False
                failures.add(f"twin missing {name}")
                continue
            same = left.read_bytes() == right.read_bytes()
            twin_detail[name] = {
                "primary_sha256": sha256_file(left),
                "twin_sha256": sha256_file(right),
                "identical": same,
            }
            if not same:
                twin_identical = False
                failures.add(f"twin is not byte-identical for {name}")

    checks = {
        "ledger_receipt_pass_and_hash_bound": declared == observations_sha
        and ledger_receipt.get("status") == "PASS",
        "primary_receipt_pass": receipt.get("status") == "PASS",
        "schemas_bound_and_valid": schema_errors == 0 and link_schema_errors == 0,
        "atom_universe_agrees": atom_keys == state.atom_keys,
        "atom_ids_unique_and_rederivable": len(atom_ids) == len(atom_keys),
        "independent_classification_agrees": not any(
            "independently derived" in item for item in failures.items
        ),
        "name_class_equals_pair_aggregate": not any(
            "pair aggregate" in item for item in failures.items
        ),
        "split_keeps_one_identity_per_office": not any(
            "does not keep one identity per office" in item for item in failures.items
        ),
        "promotion_tripwire_clean": not tripwire_failures and not link_tripwire,
        "circularity_negative_control_differs": bool(control_differs),
        "acceptance_targets_met": (not deviations) if targets_applicable else None,
        "twin_byte_identical": twin_identical,
        "output_hashes_match_receipt": not any(
            "sha256 does not match" in item for item in failures.items
        ),
    }
    status = "PASS" if failures.ok else "FAIL"
    return {
        "schema_id": "staffer-network-house-person-identity-verification-receipt-v1",
        "status": status,
        "run_id": args.run_id,
        "verifier": "audits/staffer_network/verify_house_person_identity.py",
        "receipt_schema_note": (
            "No committed JSON schema: the lane authorises exactly two new "
            "schemas (the atom and the link) and this is neither."
        ),
        "independence": (
            "build_house_person_identity is never imported. Atoms, name classes, "
            "link classes, collided-pair subclasses and first_overlap_quarter are "
            "re-derived here from raw unmerged inclusive-day ranges with a naive "
            "pairwise overlap test, a different code path from the builder's "
            "merged-calendar intervals.py arithmetic."
        ),
        "verification_scope": (
            "This verifier re-derives the SAME rule by an independent code path, "
            "so it catches coding errors but NOT rule errors: if the rule itself "
            "is wrong, builder and verifier agree and both pass. The only "
            "external anchor on rule correctness is the four pinned acceptance "
            "targets, measured outside this generation."
        ),
        "inputs": {
            "ledger_root": str(ledger_root),
            "observations_sha256": observations_sha,
            "ledger_receipt_sha256": sha256_file(ledger_receipt_path),
            "primary_root": str(primary),
            "twin_root": str(twin) if twin else None,
            "schemas": {
                filename: sha256_file(SCHEMA_DIR / filename)
                for filename in (ATOM_SCHEMA_FILE, LINK_SCHEMA_FILE)
            },
        },
        "measured": {
            "observation_rows": state.rows_total,
            "observation_rows_without_person_key": state.rows_unkeyed,
            "rows_with_printed_shared_title": state.rows_shared_title,
            "rows_with_ledger_shared_flag": state.rows_ledger_flag,
            "atoms": atoms_seen,
            "atoms_split": atoms_split,
            "links": links_seen,
            "expected_office_pairs": expected_pairs,
            "name_link_class_counts": {
                key: derived_name_counts.get(key, 0) for key in NAME_CLASSES
            },
            "names_in_more_than_one_office": multi_office_names,
            "link_class_counts": {key: link_counts.get(key, 0) for key in LINK_CLASSES},
            "true_collision_subclasses": dict(sorted(subclass_counts.items())),
        },
        "acceptance_targets": {
            "applicable": targets_applicable,
            "targets": dict(ACCEPTANCE_TARGETS),
            "measured": measured,
            "deviations": deviations,
        },
        "circularity_negative_control": {
            "note": (
                "Re-running the same rules with the ledger's shared_employee_flag "
                "in place of the printed title. It must differ; if it did not, the "
                "emitted classification could not be shown to be independent of a "
                "field that is true for the whole population under adjudication."
            ),
            "counts_if_flag_were_used": {
                key: control_counts.get(key, 0) for key in NAME_CLASSES
            },
            "counts_as_emitted": {
                key: derived_name_counts.get(key, 0) for key in NAME_CLASSES
            },
            "differs": bool(control_differs),
        },
        "twin": twin_detail,
        "checks": checks,
        "failures": failures.items,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Independently verify a House person-identity generation."
    )
    parser.add_argument("--ledger-root", type=Path, required=True)
    parser.add_argument("--primary-root", type=Path, required=True)
    parser.add_argument("--twin-root", type=Path, default=None)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--no-glassbox", action="store_true")
    args = parser.parse_args(argv)
    args.ledger_root = args.ledger_root.resolve()
    args.primary_root = args.primary_root.resolve()
    args.output_root = args.output_root.resolve()
    if args.twin_root is not None:
        args.twin_root = args.twin_root.resolve()
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        enabled=glassbox, kind="run.start", status="running",
        summary="house person identity verification",
        detail=str(args.primary_root), run_id=args.run_id,
    )
    output = args.output_root
    if output.exists():
        if not output.is_dir():
            raise SystemExit(f"VERIFY FAILED: output exists and is not a directory: {output}")
        if any(output.iterdir()):
            raise SystemExit(f"VERIFY FAILED: immutable generation already exists: {output}")
        output.rmdir()
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.tmp-", dir=output.parent))
    try:
        receipt = verify(args)
        (staging / VERIFICATION_NAME).write_bytes(receipt_bytes(receipt))
        os.replace(staging, output)
    except BaseException as error:
        shutil.rmtree(staging, ignore_errors=True)
        emit_glassbox(
            enabled=glassbox, kind="run.fail", status="failed",
            summary="house person identity verification failed",
            detail=f"{type(error).__name__}: {error}", run_id=args.run_id,
        )
        raise
    emit_glassbox(
        enabled=glassbox, kind="run.finish",
        status="completed" if receipt["status"] == "PASS" else "failed",
        summary="house person identity verification",
        detail=f"status={receipt['status']} failures={len(receipt['failures'])}",
        run_id=args.run_id,
    )
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "checks": receipt["checks"],
                "failures": receipt["failures"][:10],
            },
            ensure_ascii=True,
            sort_keys=True,
        )
    )
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
