#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Independent verification of the A6 prose release.

This file does NOT import the producer.  The release rule (R1-R5), the
same-string binding test and the cross-check precedence are re-implemented
here from the written specification and then compared against what the
producer actually emitted.  Where the two implementations disagree the
verification FAILS -- that is the point of the trio, and it is why
``independent_release_decision`` deliberately re-derives the reason codes
rather than reading them off the emitted rows.

What is RE-DERIVED from the upstream source (never trusted from the release):
  * the release/exclusion partition over all 3,090 upstream near-candidate
    rows, by an independent implementation of R1-R5;
  * the same-string binding for every released row, re-checked against the
    upstream ``claim_text``;
  * every released row's verbatim payload -- claim_id, source string, spans,
    role/office/date text, years, entity class -- against its upstream row;
  * the four-way cross-check tally, re-counted from the emitted rows, and its
    internal consistency with ``name_found_in_declared_office`` /
    ``name_found_with_period_overlap`` / ``window_reachable_chambers``;
  * every payroll CONFIRMED_BY_PAYROLL claim, re-verified by going back to the
    payroll ledgers and checking that the cited evidence row really exists,
    really sits in the declared member's own office, and really overlaps;
  * the coverage figures (distinct people, newly reachable) from the join
    ledgers;
  * every declared input hash, recomputed from the file on disk.

What is RE-READ and compared, never trusted:
  * primary vs twin byte identity and sha256 identity, per artifact;
  * the receipt's own outputs block against the bytes on disk;
  * the promotion counters and every per-row promotion pin.

The verification receipt is ALWAYS written, including on failure; the
exception is raised afterwards.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, timedelta
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Any, Iterator, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fec.staffer_network.schema_validation import (  # noqa: E402
    validate_instance,
    validate_schema_definition,
)

SCHEMA_ID = "staffer-network-a6-prose-release-independent-verification-v1"
EPISODE_SCHEMA = "staffer-network-a6-prose-release-episode-v1"
EXCLUSION_SCHEMA = "staffer-network-a6-prose-release-exclusion-v1"
RECEIPT_SCHEMA = "staffer-network-a6-prose-release-receipt-v1"

EPISODE_FILE = "a6_prose_release_episodes.ndjson.gz"
EXCLUSION_FILE = "a6_prose_release_exclusions.ndjson.gz"
RECEIPT_FILE = "a6_prose_release_receipt.json"
VERIFICATION_FILE = "verification_receipt.json"

EXCLUDING_BLOCKERS = (
    "AMBIGUOUS_ROLE_ABBREVIATION",
    "DATE_RANGE_REVERSED",
    "MENTION_SPANS_OVERLAP",
    "TWO_DIGIT_YEAR_NOT_CENTURY_EXPANDED",
)
UNIVERSAL_BLOCKERS = (
    "DATE_RANGE_NOT_LINKED_TO_SPECIFIC_EPISODE",
    "ROLE_EMPLOYER_BOUNDARY_NOT_ADJUDICATED",
)
RELEASABLE_ENTITY_CLASSES = frozenset(
    {"COMMITTEE_CANDIDATE", "MEMBER_OFFICE_CANDIDATE"}
)

HOUSE_CORPUS_START = date(2009, 7, 1)
HOUSE_CORPUS_END = date(2026, 3, 31)
SENATE_CORPUS_START = date(2011, 4, 1)
SENATE_CORPUS_END = date(2026, 3, 31)

PROMOTION_KEYS = {
    "canonical_eligible",
    "canonical_employment_promoted",
    "canonical_identity_promoted",
    "canonical_office_promoted",
    "complete_lifetime_employment_asserted",
}
TOKEN_PATTERN = re.compile(
    rb"(?i)(?:password|passwd|api[_-]?key|access[_-]?token|secret)\s*[:=]\s*[\"'][^\"']+[\"']"
)


class VerificationFailure(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# IO
# ---------------------------------------------------------------------------
def compact(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def logical_bytes(path: Path) -> bytes:
    if path.suffix.lower() == ".gz":
        with gzip.open(path, "rb") as stream:
            return stream.read()
    return path.read_bytes()


def rows(path: Path) -> Iterator[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(compact(value) + b"\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def parse_iso(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) < 10:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# The independent gate (R1-R5), written from the specification
# ---------------------------------------------------------------------------
def independent_same_string_binding(record: Mapping[str, Any]) -> bool:
    """R1, re-implemented: the three mentions are present and every span
    resolves to its own text inside the single ``claim_text``."""

    claim_text = record.get("claim_text")
    if not isinstance(claim_text, str) or not claim_text:
        return False
    length = len(claim_text)
    for field in ("role_title_mention", "office_employer_mention", "date_range_mention"):
        mention = record.get(field) or {}
        text = mention.get("text")
        start = mention.get("span_start")
        end = mention.get("span_end")
        if not isinstance(text, str) or not text:
            return False
        if not isinstance(start, int) or not isinstance(end, int):
            return False
        if start < 0 or end <= start or end > length:
            return False
        if claim_text[start:end] != text:
            return False
    return True


def independent_release_decision(record: Mapping[str, Any]) -> list[str]:
    """The whole release rule, re-derived.  Returns the SORTED exclusion reason
    codes; an empty list means the row is released."""

    reasons: list[str] = []
    if not independent_same_string_binding(record):
        reasons.append("R1_SAME_STRING_BINDING_NOT_ESTABLISHED")

    mention = record.get("office_employer_mention") or {}
    if mention.get("entity_class") not in RELEASABLE_ENTITY_CLASSES:
        reasons.append("R2_OFFICE_NOT_MEMBER_OFFICE_OR_COMMITTEE")

    dates = record.get("date_range_mention") or {}
    start_year = dates.get("explicit_start_year")
    end_year = dates.get("explicit_end_year")
    both = isinstance(start_year, int) and isinstance(end_year, int)
    if not both:
        reasons.append("R3_YEARS_NOT_BOTH_EXPLICIT")

    flagged = set(record.get("rejection_reasons") or [])
    for blocker in EXCLUDING_BLOCKERS:
        if blocker in flagged:
            reasons.append(f"R4_{blocker}")

    if both and int(start_year) > int(end_year):
        reasons.append("R5_START_YEAR_AFTER_END_YEAR")
    return sorted(reasons)


# ---------------------------------------------------------------------------
# Interval and name helpers, re-implemented independently of the producer
# ---------------------------------------------------------------------------
def overlaps(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    if a_end < a_start or b_end < b_start:
        return False
    return a_start <= b_end and b_start <= a_end


def strip_accents(value: str) -> str:
    import unicodedata

    return "".join(
        ch
        for ch in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(ch)
    )


def norm_token(value: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", strip_accents(value or "").upper())


# ---------------------------------------------------------------------------
# Promotion tripwire
# ---------------------------------------------------------------------------
def promotion_failures(value: Any, context: str, failures: Counter) -> None:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            lowered = str(key).lower()
            if lowered in PROMOTION_KEYS and nested not in (False, 0, None, ""):
                failures[f"promotion:{context}:{key}"] += 1
            if lowered.endswith(
                (
                    "canonical_person_id",
                    "canonical_employment_episode_id",
                    "canonical_employment_fact_id",
                    "canonical_fact_id",
                )
            ) and nested not in (False, 0, None, ""):
                failures[f"canonical_id:{context}:{key}"] += 1
            promotion_failures(nested, context, failures)
    elif isinstance(value, list):
        for nested in value:
            promotion_failures(nested, context, failures)


# ---------------------------------------------------------------------------
# Payroll re-verification of the CONFIRMED claims
# ---------------------------------------------------------------------------
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")


def quarter_bounds(value: str | None) -> tuple[date, date] | None:
    match = QUARTER_RE.match(value or "")
    if not match:
        return None
    year, quarter = int(match.group(1)), int(match.group(2))
    start_month = 3 * (quarter - 1) + 1
    start = date(year, start_month, 1)
    end = (
        date(year, 12, 31)
        if quarter == 4
        else date(year, start_month + 3, 1) - timedelta(days=1)
    )
    return start, end


def fold_name(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", strip_accents(value or "").casefold())


def load_nickname_forms(path: Path) -> dict[str, tuple[str, ...]]:
    """Re-load the nickname table under the same MULTI-FORMAL-DROPPED rule the
    release uses, so a nickname-mediated confirmation can be reproduced here."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    kept: dict[str, tuple[str, ...]] = {}
    for key, values in (payload.get("entries") or {}).items():
        forms = tuple(str(v).casefold() for v in values)
        if len(set(forms)) == 1:
            kept[str(key).casefold()] = forms
    return kept


def given_names_bind(
    left: str, right: str, table: Mapping[str, Sequence[str]]
) -> bool:
    """The producer accepts a given-name match either exactly or through the
    nickname table ('BOBBY' <-> 'ROBERT').  Both routes are re-derived here."""

    if norm_token(left) == norm_token(right):
        return True

    def forms(value: str) -> set[str]:
        folded = fold_name(value)
        out = {folded}
        for formal in table.get(folded, ()):
            out.add(fold_name(formal))
        return out

    return bool(forms(left) & forms(right))


def reverify_house_confirmations(
    spans_path: Path, wanted: Mapping[str, set[str]]
) -> tuple[dict[str, list[tuple[str, date, date]]], int]:
    """For each bioguide -> {surname} actually asserted as confirmed, collect
    every House span in HON:<bioguide> whose person_key carries that surname,
    keeping the span's own given name and window.  The given-name comparison
    is deferred to the caller so the nickname route is testable there.
    Independent of the producer's index."""

    found: defaultdict[str, list[tuple[str, date, date]]] = defaultdict(list)
    scanned = 0
    keys = {f"HON:{bioguide}" for bioguide in wanted}
    for record in rows(spans_path):
        scanned += 1
        office_key = record.get("office_key")
        if office_key not in keys:
            continue
        bioguide = str(office_key)[4:]
        person_key = str(record.get("person_key") or "")
        if not person_key.startswith("SOD:"):
            continue
        parts = person_key[4:].split("|")
        if len(parts) < 2:
            continue
        surname, given = norm_token(parts[0]), norm_token(parts[1])
        if surname not in wanted.get(bioguide, set()):
            continue
        start = parse_iso(record.get("service_start_min"))
        end = parse_iso(record.get("service_end_max"))
        if start is None or end is None:
            first_bounds = quarter_bounds(record.get("first_report_quarter"))
            last_bounds = quarter_bounds(record.get("last_report_quarter"))
            if first_bounds is None or last_bounds is None:
                continue
            start, end = first_bounds[0], last_bounds[1]
        found[f"{bioguide}|{surname}"].append((given, start, end))
    return dict(found), scanned


def reverify_senate_confirmations(
    senate_path: Path, offices: set[str], wanted: set[str]
) -> dict[str, list[tuple[str, date, date]]]:
    found: defaultdict[str, list[tuple[str, date, date]]] = defaultdict(list)
    for record in rows(senate_path):
        office_raw = record.get("office_raw")
        if office_raw not in offices:
            continue
        raw = record.get("payee_name_raw")
        if not isinstance(raw, str) or "," not in raw:
            continue
        surname_part, _, given_part = raw.partition(",")
        surname = "".join(norm_token(part) for part in surname_part.split())
        given_tokens = [norm_token(part) for part in given_part.split()]
        given_tokens = [token for token in given_tokens if len(token) > 1]
        if not surname or not given_tokens or surname not in wanted:
            continue
        windows: list[tuple[date, date]] = []
        for interval in record.get("date_intervals") or []:
            start = parse_iso(interval.get("start"))
            end = parse_iso(interval.get("end"))
            if start and end and end >= start:
                windows.append((start, end))
        if not windows:
            start = parse_iso(record.get("report_period_start"))
            end = parse_iso(record.get("report_period_end"))
            if start and end and end >= start:
                windows.append((start, end))
        for start, end in windows:
            found[f"{office_raw}|{surname}"].append((given_tokens[0], start, end))
    return dict(found)


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------
def verify(primary_dir: Path, twin_dir: Path, output_dir: Path) -> dict[str, Any]:
    assertions: dict[str, bool] = {}
    counts: dict[str, Any] = {}
    row_failures: Counter = Counter()
    source_failures: Counter = Counter()

    files: dict[str, Path] = {}
    for prefix, directory in (("primary", primary_dir), ("twin", twin_dir)):
        files[f"{prefix}_episodes"] = (directory / EPISODE_FILE).resolve(strict=True)
        files[f"{prefix}_exclusions"] = (directory / EXCLUSION_FILE).resolve(strict=True)
        files[f"{prefix}_receipt"] = (directory / RECEIPT_FILE).resolve(strict=True)

    # ---- twin byte identity ------------------------------------------------
    for artifact in ("episodes", "exclusions", "receipt"):
        primary = files[f"primary_{artifact}"]
        twin = files[f"twin_{artifact}"]
        assertions[f"{artifact}_twins_byte_equal"] = (
            primary.read_bytes() == twin.read_bytes()
        )
        assertions[f"{artifact}_twins_sha256_equal"] = sha(primary) == sha(twin)

    receipt = json.loads(files["primary_receipt"].read_text(encoding="utf-8"))
    assertions["receipt_schema_id_matches"] = receipt.get("schema_id") == RECEIPT_SCHEMA
    assertions["receipt_status_is_released_review_required"] = (
        receipt.get("status") == "RELEASED_REVIEW_REQUIRED"
    )
    assertions["receipt_promotion_policy_pinned"] = (
        receipt.get("promotion_policy") == "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS"
    )
    for key in (
        "canonical_employment_promotions",
        "canonical_identity_promotions",
        "canonical_eligible_rows",
        "complete_lifetime_employment_assertions",
    ):
        assertions[f"receipt_{key}_is_zero"] = receipt.get(key) == 0

    # ---- receipt outputs block vs bytes on disk ---------------------------
    declared_outputs = receipt.get("outputs") or {}
    for label, path in (("episodes", files["primary_episodes"]), ("exclusions", files["primary_exclusions"])):
        block = declared_outputs.get(label) or {}
        assertions[f"receipt_binds_{label}_sha256"] = block.get("sha256") == sha(path)
        assertions[f"receipt_binds_{label}_bytes"] = block.get("bytes") == path.stat().st_size

    # ---- every declared input hash recomputed -----------------------------
    source_block = receipt.get("source") or {}
    input_ok = True
    missing_inputs: list[str] = []
    for label, entry in sorted(source_block.items()):
        path = Path(entry.get("path", ""))
        if not path.exists():
            input_ok = False
            missing_inputs.append(label)
            continue
        if sha(path) != entry.get("sha256") or path.stat().st_size != entry.get("bytes"):
            input_ok = False
            source_failures[f"input_hash_drift:{label}"] += 1
    assertions["every_declared_input_hash_reproduces"] = input_ok
    counts["missing_declared_inputs"] = missing_inputs

    # ---- re-derive the release partition from the upstream source ---------
    upstream_path = Path((source_block.get("blockers") or {}).get("path", ""))
    episodes = list(rows(files["primary_episodes"]))
    exclusions = list(rows(files["primary_exclusions"]))
    counts["episodes"] = len(episodes)
    counts["exclusions"] = len(exclusions)

    if upstream_path.exists():
        upstream: dict[str, dict[str, Any]] = {}
        expected_released: set[str] = set()
        expected_excluded: dict[str, list[str]] = {}
        upstream_rows = 0
        universal_on_every_row = True
        for record in rows(upstream_path):
            upstream_rows += 1
            claim_id = str((record.get("source_pointer") or {}).get("claim_id") or "")
            upstream[claim_id] = record
            reasons = independent_release_decision(record)
            if reasons:
                expected_excluded[claim_id] = reasons
            else:
                expected_released.add(claim_id)
            flagged = set(record.get("rejection_reasons") or [])
            if not set(UNIVERSAL_BLOCKERS) <= flagged:
                universal_on_every_row = False
        counts["upstream_rows"] = upstream_rows
        counts["independently_released"] = len(expected_released)
        counts["independently_excluded"] = len(expected_excluded)
        assertions["upstream_row_count_is_3090"] = upstream_rows == 3090
        assertions["both_universal_blockers_present_on_every_upstream_row"] = (
            universal_on_every_row
        )

        emitted_released = {row["claim_id"] for row in episodes}
        emitted_excluded = {row["claim_id"]: row["exclusion_reasons"] for row in exclusions}
        assertions["released_set_exactly_matches_independent_gate"] = (
            emitted_released == expected_released
        )
        assertions["excluded_set_exactly_matches_independent_gate"] = (
            set(emitted_excluded) == set(expected_excluded)
        )
        reason_agreement = True
        for claim_id, reasons in expected_excluded.items():
            if emitted_excluded.get(claim_id) != reasons:
                reason_agreement = False
                source_failures[f"exclusion_reason_mismatch:{claim_id}"] += 1
        assertions["exclusion_reason_codes_agree_row_by_row"] = reason_agreement
        assertions["released_plus_excluded_equals_upstream"] = (
            len(episodes) + len(exclusions) == upstream_rows
        )

        # ---- every released row's payload re-checked against upstream -----
        for row in episodes:
            source = upstream.get(row["claim_id"])
            if source is None:
                row_failures["released_row_has_no_upstream_source"] += 1
                continue
            mention = source.get("office_employer_mention") or {}
            dates = source.get("date_range_mention") or {}
            role = source.get("role_title_mention") or {}
            if row["source_string"] != source.get("claim_text"):
                row_failures["source_string_differs_from_upstream_claim_text"] += 1
            if row["office_text"] != mention.get("text"):
                row_failures["office_text_differs_from_upstream"] += 1
            if row["role_text"] != role.get("text"):
                row_failures["role_text_differs_from_upstream"] += 1
            if row["date_range_text"] != dates.get("text"):
                row_failures["date_range_text_differs_from_upstream"] += 1
            if row["start_year"] != dates.get("explicit_start_year"):
                row_failures["start_year_differs_from_upstream"] += 1
            if row["end_year"] != dates.get("explicit_end_year"):
                row_failures["end_year_differs_from_upstream"] += 1
            if row["office_entity_class"] != mention.get("entity_class"):
                row_failures["entity_class_differs_from_upstream"] += 1
            if not independent_same_string_binding(source):
                row_failures["released_row_fails_independent_binding"] += 1
            binding = row["same_string_binding"]
            if binding.get("role_span") != [role.get("span_start"), role.get("span_end")]:
                row_failures["role_span_differs_from_upstream"] += 1
            if binding.get("office_span") != [
                mention.get("span_start"),
                mention.get("span_end"),
            ]:
                row_failures["office_span_differs_from_upstream"] += 1
            if binding.get("date_span") != [dates.get("span_start"), dates.get("span_end")]:
                row_failures["date_span_differs_from_upstream"] += 1
            if row["source_string_sha256"] != hashlib.sha256(
                str(source.get("claim_text") or "").encode("utf-8")
            ).hexdigest():
                row_failures["source_string_sha256_mismatch"] += 1
    else:
        assertions["upstream_source_readable"] = False

    # ---- per-row pins ------------------------------------------------------
    pin_ok = True
    for row in episodes:
        if (
            row.get("canonical_eligible") is not False
            or row.get("canonical_employment_promoted") is not False
            or row.get("canonical_identity_decision") != "NOT_ADJUDICATED"
            or row.get("review_status") != "REVIEW_REQUIRED"
            or row.get("precision") != "year"
            or row.get("single_author") is not True
            or row.get("temporal_semantics") != "ASSERTED_EPISODE"
            or (row.get("same_string_binding") or {}).get("verified") is not True
        ):
            pin_ok = False
            row_failures["released_row_violates_a_pin"] += 1
        if row.get("start_year", 0) > row.get("end_year", 0):
            pin_ok = False
            row_failures["released_row_has_reversed_years"] += 1
    assertions["every_released_row_carries_the_release_pins"] = pin_ok

    pin_ok = True
    for row in exclusions:
        if (
            row.get("canonical_eligible") is not False
            or row.get("canonical_employment_promoted") is not False
            or row.get("canonical_identity_decision") != "NOT_ADJUDICATED"
            or row.get("review_status") != "REVIEW_REQUIRED"
            or row.get("release_decision") != "NOT_RELEASED"
        ):
            pin_ok = False
            row_failures["excluded_row_violates_a_pin"] += 1
    assertions["every_excluded_row_carries_the_release_pins"] = pin_ok

    # ---- schema ------------------------------------------------------------
    schema_entry = source_block.get("schema") or {}
    schema_path = Path(schema_entry.get("path", ""))
    if schema_path.exists():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assertions["episode_schema_id_matches"] = schema.get("$id") == EPISODE_SCHEMA
        try:
            validate_schema_definition(schema)
            schema_ok = True
        except Exception:
            schema_ok = False
        assertions["episode_schema_definition_is_supported"] = schema_ok
        if schema_ok:
            invalid = 0
            for row in episodes:
                try:
                    validate_instance(row, schema, _schema_checked=True)
                except Exception:
                    invalid += 1
            row_failures["episode_rows_failing_schema"] += invalid
            assertions["every_released_row_validates_against_the_schema"] = invalid == 0
    else:
        assertions["episode_schema_present"] = False

    # ---- four-way cross-check internal consistency -------------------------
    tally: Counter = Counter()
    consistent = True
    for row in episodes:
        cross = row["payroll_cross_check"]
        status = cross["status"]
        tally[status] += 1
        if status == "NOT_CHECKED_MEMBER_UNRESOLVED":
            # The producer returns before any corpus work for an unresolved
            # member, so these rows carry empty chamber lists BY CONSTRUCTION.
            # Re-deriving reachability for them would invent a check that was
            # never run; assert the emptiness instead.
            if (
                row["member_bioguide"] is not None
                or cross["chambers_checked"]
                or cross["window_reachable_chambers"]
                or cross["name_found_in_declared_office"]
                or cross["name_found_with_period_overlap"]
                or cross["evidence"]
            ):
                consistent = False
                row_failures["unresolved_row_is_not_cleanly_unchecked"] += 1
            continue
        if row["member_bioguide"] is None:
            consistent = False
            row_failures["checked_but_member_unresolved"] += 1
        if status == "CONFIRMED_BY_PAYROLL" and not (
            cross["name_found_in_declared_office"]
            and cross["name_found_with_period_overlap"]
            and cross["window_reachable_chambers"]
        ):
            consistent = False
            row_failures["confirmed_without_supporting_flags"] += 1
        if status == "NAME_FOUND_PERIOD_MISMATCH" and (
            not cross["name_found_in_declared_office"]
            or cross["name_found_with_period_overlap"]
        ):
            consistent = False
            row_failures["period_mismatch_with_inconsistent_flags"] += 1
        if status == "NAME_ABSENT_FROM_DECLARED_OFFICE" and cross[
            "name_found_in_declared_office"
        ] and cross["window_reachable_chambers"]:
            consistent = False
            row_failures["absent_but_name_was_found"] += 1
        if status == "OFFICE_OUT_OF_CORPUS_WINDOW" and cross["window_reachable_chambers"]:
            consistent = False
            row_failures["out_of_window_but_window_reachable"] += 1
        # Re-derive reachability from the declared years and the corpus floors.
        declared_start = parse_iso(cross["declared_window_start"])
        declared_end = parse_iso(cross["declared_window_end"])
        if declared_start is None or declared_end is None:
            consistent = False
            row_failures["declared_window_unparseable"] += 1
            continue
        corpora = {
            "house": (HOUSE_CORPUS_START, HOUSE_CORPUS_END),
            "senate": (SENATE_CORPUS_START, SENATE_CORPUS_END),
        }
        expected_reach = sorted(
            chamber
            for chamber in (cross["chambers_checked"] or ["house", "senate"])
            if overlaps(declared_start, declared_end, *corpora[chamber])
        )
        if expected_reach != cross["window_reachable_chambers"]:
            consistent = False
            row_failures["window_reachability_not_reproducible"] += 1
        if declared_start != date(row["start_year"], 1, 1) or declared_end != date(
            row["end_year"], 12, 31
        ):
            consistent = False
            row_failures["declared_window_does_not_match_years"] += 1
    assertions["cross_check_labels_are_internally_consistent"] = consistent
    counts["cross_check_tally"] = dict(sorted(tally.items()))
    declared_tally = ((receipt.get("cross_check") or {}).get("counts")) or {}
    assertions["receipt_cross_check_tally_matches_rows"] = all(
        declared_tally.get(key, 0) == tally.get(key, 0)
        for key in set(declared_tally) | set(tally)
    )

    # ---- re-verify every CONFIRMED claim against the payroll ledgers -------
    house_wanted: defaultdict[str, set[str]] = defaultdict(set)
    senate_wanted: set[str] = set()
    senate_offices: set[str] = set()
    confirmed_rows = [
        row
        for row in episodes
        if row["payroll_cross_check"]["status"] == "CONFIRMED_BY_PAYROLL"
    ]
    for row in confirmed_rows:
        cross = row["payroll_cross_check"]
        surname = str(cross["filer_surname_normalized"] or "")
        for evidence in cross["evidence"]:
            if evidence["chamber"] == "house":
                house_wanted[str(row["member_bioguide"])].add(surname)
            else:
                senate_wanted.add(surname)
                senate_offices.add(str(evidence["office"]))
    nickname_path = Path((source_block.get("nicknames") or {}).get("path", ""))
    nickname_forms = (
        load_nickname_forms(nickname_path) if nickname_path.exists() else {}
    )
    assertions["nickname_table_readable_for_reverification"] = bool(nickname_forms)

    house_spans_path = Path((source_block.get("house_spans") or {}).get("path", ""))
    senate_path = Path((source_block.get("senate_candidates") or {}).get("path", ""))
    confirmations_reproduced = 0
    confirmations_not_reproduced = 0
    if house_wanted and house_spans_path.exists():
        house_found, scanned = reverify_house_confirmations(house_spans_path, house_wanted)
        counts["house_span_rows_scanned"] = scanned
    else:
        house_found = {}
    if senate_wanted and senate_path.exists():
        senate_found = reverify_senate_confirmations(
            senate_path, senate_offices, senate_wanted
        )
    else:
        senate_found = {}

    for row in confirmed_rows:
        cross = row["payroll_cross_check"]
        declared_start = date(row["start_year"], 1, 1)
        declared_end = date(row["end_year"], 12, 31)
        surname = str(cross["filer_surname_normalized"] or "")
        given = str(cross["filer_given_normalized"] or "")
        reproduced = False
        key_house = f"{row['member_bioguide']}|{surname}"
        for payroll_given, start, end in house_found.get(key_house, ()):
            if given_names_bind(given, payroll_given, nickname_forms) and overlaps(
                declared_start, declared_end, start, end
            ):
                reproduced = True
                break
        if not reproduced:
            for evidence in cross["evidence"]:
                if evidence["chamber"] != "senate":
                    continue
                key_senate = f"{evidence['office']}|{surname}"
                for payroll_given, start, end in senate_found.get(key_senate, ()):
                    if given_names_bind(
                        given, payroll_given, nickname_forms
                    ) and overlaps(declared_start, declared_end, start, end):
                        reproduced = True
                        break
                if reproduced:
                    break
        if reproduced:
            confirmations_reproduced += 1
        else:
            confirmations_not_reproduced += 1
            row_failures["confirmation_not_reproduced_from_payroll"] += 1
    counts["confirmations_reproduced"] = confirmations_reproduced
    counts["confirmations_not_reproduced"] = confirmations_not_reproduced
    assertions["every_confirmation_reproduces_from_the_payroll_ledgers"] = (
        confirmations_not_reproduced == 0
    )

    # ---- coverage re-derivation -------------------------------------------
    spine_path = Path((source_block.get("lda_spine_links") or {}).get("path", ""))
    resolution_path = Path((source_block.get("lda_resolution") or {}).get("path", ""))
    if spine_path.exists() and resolution_path.exists():
        linked = {
            str(row["lda_source_person_id"])
            for row in rows(spine_path)
            if row.get("link_status") == "LINKED_BY_PAYROLL_KEY"
        }
        resolved = {
            str(row["lda_source_person_id"])
            for row in rows(resolution_path)
            if row.get("status") in ("RESOLVED_R1", "RESOLVED_R2")
        }
        covered = {row["lda_source_person_id"] for row in episodes}
        newly = covered - (linked | resolved)
        declared_coverage = receipt.get("coverage") or {}
        assertions["coverage_distinct_people_reproduces"] = (
            declared_coverage.get("distinct_lda_people_in_release") == len(covered)
        )
        assertions["coverage_newly_reachable_reproduces"] = (
            declared_coverage.get("distinct_lda_people_newly_reachable") == len(newly)
        )
        counts["coverage_distinct_people"] = len(covered)
        counts["coverage_newly_reachable"] = len(newly)
    else:
        assertions["coverage_join_ledgers_readable"] = False

    # ---- promotion tripwire + token scan ----------------------------------
    promo: Counter = Counter()
    for row in episodes:
        promotion_failures(row, "episode", promo)
    for row in exclusions:
        promotion_failures(row, "exclusion", promo)
    assertions["no_promotion_field_is_set_on_any_emitted_row"] = not promo
    counts["promotion_failures"] = dict(sorted(promo.items()))

    scanned_paths = tuple(files.values())
    token_matches = sum(
        len(TOKEN_PATTERN.findall(logical_bytes(path))) for path in scanned_paths
    )
    assertions["token_negative_structured_artifact_scan"] = token_matches == 0

    failures = sorted(name for name, passed in assertions.items() if not passed)
    verification = {
        "assertions": dict(sorted(assertions.items())),
        "counts": {key: counts[key] for key in sorted(counts)},
        "failures": failures,
        "hashes": {
            f"{name}_sha256": sha(path) for name, path in sorted(files.items())
        },
        "primary_dir": str(primary_dir),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "row_failure_counts": dict(sorted(row_failures.items())),
        "schema_id": SCHEMA_ID,
        "source_failure_counts": dict(sorted(source_failures.items())),
        "status": "PASS" if not failures else "FAIL",
        "token_negative_scan": {
            "matches": token_matches,
            "scan_mode": "DECOMPRESSED_LOGICAL_BYTES_FOR_GZIP",
            "scanned_files": len(scanned_paths),
        },
        "twin_dir": str(twin_dir),
    }
    write_json_atomic(output_dir / VERIFICATION_FILE, verification)
    if failures:
        raise VerificationFailure("verification failed: " + ", ".join(failures))
    return verification


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--primary-dir", required=True, type=Path)
    parser.add_argument("--twin-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    result = verify(args.primary_dir, args.twin_dir, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
