#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the immutable Part C Hill personnel spine and its connections.

One spine of every person paid by the House (Statement of Disbursements) and the
Senate (Report of the Secretary), keyed to member offices by bioguide, with
tenure spans and titles; onto which are connected the LDA lobbyists carrying
their Part A tier, the current Quorum staff directory, members by roster, and
the registrant-employer episode count.  Nothing here is canonical: every emitted
row carries ``review_status: REVIEW_REQUIRED``, ``canonical_eligible: false``
and ``canonical_employment_promoted: false``, and the receipt pins both
promotion counters at zero (INV-1).

Conventions reused verbatim from ``build_tiered_corroboration_sidecar.py``:
canonical NDJSON (sorted keys, LF, gzip mtime 0) so a primary and a twin are
byte-identical, atomic writes, refusal to write into a non-empty output root,
the A5b anti-promotion tripwire, the receipt shape, the language law with its
identifier-value exemption, and the strict-bioguide member resolution (roster +
nickname table + the Part A v2 term-window rule).  ``intervals.py``,
``schema_validation.py`` and ``network_math.py`` are the only ``fec`` modules
this lane may import; this builder needs none of them at build time and imports
none, which keeps it import-side-effect free.

ASSUMPTIONS AND RESOLVED AMBIGUITIES
------------------------------------
Every one of these is a choice this module makes where the spec left room.  They
are all declared in the receipt (``dials`` and ``notes``) and re-derived by
``verify_hill_personnel_spine.py``.

1.  MISSING INPUTS ARE TOLERATED.  ``--house-ledger-root`` (produced by the
    ``house-sod-track-and-hunt`` workflow) and ``--sidecar-root`` (Part A v2)
    may not exist yet.  Every loader is tolerant: an absent input is recorded in
    the receipt with ``present: false`` and contributes nothing.  A build with
    no personnel source at all fails with ``NO_PERSONNEL_SOURCE_PRESENT``.

2.  OPTIONAL LEDGER FIELDS.  The House ledger's observation rows are read for
    ``quarter``, ``office_raw``, ``office_key``, ``member_bioguide``,
    ``container_kind``, ``payee_raw``, ``person_key``, ``title_raw``,
    ``service_start``, ``service_end``, ``amount``, ``source_file`` and
    ``source_row_index``; every one of them except a usable quarter, office and
    payee is optional.  ``house_person_office_spans.ndjson.gz`` and
    ``house_member_quarters.ndjson.gz`` are hash-bound but not consumed: this
    lane re-derives spans itself so that the span rule is one rule, applied
    identically to all three sources.

3.  MEMBER OFFICES ARE KEYED ON THE MEMBER, BORROWED FROM THE LEDGER.  A House
    MEMBER office key and its ``member_bioguide`` come from the House ledger's
    own strict per-office resolution -- ``HON:<bioguide>`` -- because that
    resolution is verified and Part C must not contradict it.  A member office
    the ledger never resolved falls back to ``HON:<first>|<surname>``,
    normalized, so two members with different names can never share a key.
    ``container_kind`` and every non-member office key are still derived here
    from the raw office string, and the ledger's values for all three are
    compared and reported in ``counts.ledger_field_disagreements`` rather than
    silently overriding or being silently overridden.  Same for ``person_key``:
    the payee key triple is always parsed from ``payee_raw`` by this module's
    own rule.  The ledger's ``shared_employee_flag`` is deliberately NOT read:
    it is set whenever a person holds two offices in a quarter, which is the
    condition the shared-employee rule adjudicates, so it is circular.  The
    spec's title test is used instead.

4.  ONE HOUSE LANE, BOTH ERAS.  From House ledger v3 the ledger carries the
    2009Q3-2015Q4 PDF era and the 2016Q1-2026Q1 CSV era in one file, tagged by
    ``source_form``.  There is no second PDF lane and no overlap rule: nothing
    is dropped for being covered elsewhere, because nothing is read twice.  A
    House row is suppressed only when this module cannot parse it, and every
    suppressed row is counted by lane, era and reason in
    ``sources.source_rows_suppressed_by_reason``.  Suppressed rows are not part
    of conservation, which is stated over ADMITTED rows: admitted equals the
    span observation sum equals the source-row-id union.  Read minus admitted is
    the residue, and it is reported rather than closed.

5.  NAME FORMATS.  A payroll payee string containing a comma is
    ``LAST[, ] FIRST [MIDDLE...]`` (House SOD PDF, Senate).  A payee string
    without a comma is ``LAST FIRST [MIDDLE]`` (House SOD CSV vendor names).  A
    trailing service-date hint (``DALY, BRENDAN 07/01/09``) is stripped before
    parsing.  Multi-token surnames survive only in the comma form; in the
    no-comma form the first token is taken as the surname, which is the House
    SOD CSV convention and a documented limitation.  LDA display names and
    Quorum staffer names are ``FIRST [MIDDLE] LAST`` and are parsed by a
    separate rule.

6.  IDENTITY CLUSTERING.  Office spans of one payee key in one chamber are
    clustered greedily in period order; a span joins the first cluster it is
    pairwise-linkable with against EVERY existing member, so a cluster is a
    clique under the linkability relation and transitivity can never merge two
    spans that overlap in time.  Two spans are linkable when their observed
    period sets are disjoint, when their complete House service-date calendars
    are disjoint even though a reporting quarter is shared, or when every
    shared period is a shared-employee row on at least one side.  The day-level
    rule is what preserves an office move that occurs inside one quarter.

7.  CROSS-CHAMBER (S3).  A House cluster and a Senate cluster merge only when
    the payee key has exactly one cluster in each chamber AND their period sets
    are disjoint.  The same-period rule is applied across chambers as well as
    within one; ambiguous and overlapping cases are left unmerged and counted.

8.  ANNUALIZED ESTIMATE.  ``amount_sum / observed_days * ANNUALIZATION_DAYS``
    where ``observed_days`` is the total length of the distinct observed
    reporting periods.  Null when no amount parsed.  This is an arithmetic
    restatement of the observed pay, not a salary finding.

9.  LDA LINK GRAIN.  One row per (LDA person, lane, resolved spine person), plus
    one row per (LDA person, lane) whose keys resolved to zero or to more than
    one spine person.  ``payroll_key`` carries the lexicographically smallest
    key for the pair and ``payroll_key_count`` how many keys collapsed into it.
    H1 joins on ``payroll_candidate_id`` directly.  H2 and Senate carry an
    opaque ``payroll_support_digest`` whose recipe is not reproducible here, so
    they are re-derived from ``display_name`` + ``employing_office_candidate``
    exactly as the spec's "(+ payroll_payee_raw / office for re-derivation)"
    instructs; the digest is still carried as ``payroll_key``.  The spec's
    ``link_status`` enum has no ambiguity member, so a key that resolves to more
    than one spine person is ``KEY_NOT_FOUND`` with
    ``key_resolution: KEY_AMBIGUOUS`` recording why.

10. QUORUM MEMBER MAP.  ``--congestion`` is the declared bioguide -> member
    display name map.  It covers fewer members than the staff directory does, so
    a strict roster fallback (exact surname + nickname-normalized first name,
    term window covering the latest House period) is applied second and recorded
    per row in ``member_resolution_source``.  The fallback is a declared dial
    and can be turned off.

11. REGISTRANT EPISODES.  Part C emits no registrant output.  The episode file
    is hash-bound and used only to count, in the receipt, how many spine-linked
    LDA people carry a registrant-employer episode.

12. NAMES ARE EMITTED HERE.  Unlike Part A, Part C's spec requires the payee key
    triple on the spine row and the staffer display name on the link row, so
    normalized name components are emitted.  They are declared verbatim-quoted
    fields for the language law.

15. ``--name-standard`` IS OFF BY DEFAULT.  With the flag absent this module
    behaves exactly as it did before the flag existed, imports nothing new and
    emits no new field, so the generation it produced before is reproducible
    byte for byte.  With the flag on it RE-KEYS the person id under
    ``fec/staffer_network/name_standard.py`` and emits an id map alongside the
    payloads.  That module is loaded lazily and BY PATH, only when the flag is
    on; the "only three fec modules" convention above describes the default
    path and this is the one declared exception to it.  See the NAME STANDARD
    block below for the id tuple, what moves, what is held fixed, and the
    two-parse equality that is checked on every build.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Iterator, Mapping, Sequence
import unicodedata

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402


STAGE_ID = "hill-personnel-spine-part-c"
GLASSBOX_SOURCE = "tiered-corroboration-sidecar"
GLASSBOX_SCRIPT = Path(r"C:\Users\pgoff\.claude\glassbox\emit.ps1")

SPAN_SCHEMA = "staffer-network-hill-person-office-span-v1"
SPINE_SCHEMA = "staffer-network-hill-person-spine-v1"
STAFFER_SCHEMA = "staffer-network-current-staffer-link-v1"
LDA_LINK_SCHEMA = "staffer-network-lda-spine-link-v1"
OFFICE_INDEX_SCHEMA = "staffer-network-member-office-index-v1"
RECEIPT_SCHEMA = "staffer-network-hill-personnel-spine-receipt-v1"

SPAN_FILE = "hill_person_office_spans.ndjson.gz"
SPINE_FILE = "hill_person_spine.ndjson.gz"
STAFFER_FILE = "current_staffer_links.ndjson.gz"
LDA_LINK_FILE = "lda_spine_links.ndjson.gz"
OFFICE_INDEX_FILE = "member_office_index.ndjson.gz"
RECEIPT_FILE = "hill_personnel_spine_receipt.json"
PAYLOAD_FILES = (SPAN_FILE, SPINE_FILE, STAFFER_FILE, LDA_LINK_FILE, OFFICE_INDEX_FILE)

DEFAULT_RULE_VERSION = "hill-personnel-spine-v2"

# THE HOUSE HAS EXACTLY ONE LANE.
#
# Up to the House ledger v3 rebind there were two: the ledger (CSV era, 41
# quarters) and a separate 2009Q3-2015Q4 PDF-era candidate file read directly
# (26 quarters, 293,881 rows).  Ledger v3 carries BOTH eras in one file --
# 975,058 observations over 67 quarters, distinguished by ``source_form`` in
# {detail_csv, house_gov_single_volume_pdf} -- so the separate PDF lane is gone.
# Binding that file alongside a v3 ledger would admit every 2009Q3-2015Q4 row
# twice (975,058 + 293,881 = 1,268,939 instead of 975,058), and because the
# duplicate rows would carry different row ids nothing downstream would notice:
# conservation would still balance, the spans would just be built from a
# doubled observation set.  The option to pass that file no longer exists,
# ``sources.separate_pdf_lane_bound`` pins false in the receipt, and the
# verifier fails the generation if any span carries the retired lane name.
LANE_HOUSE_LEDGER = "house_ledger"
LANE_SENATE = "senate_payroll_2011_2026"

# Retired.  Named here only so the verifier can assert its absence.
RETIRED_LANE_HOUSE_PDF = "house_sod_pdf_2009q3_2015q4"

SOURCE_FORM_CSV = "detail_csv"
SOURCE_FORM_PDF = "house_gov_single_volume_pdf"
# The House quarter at which the ledger's CSV era begins; the quarter before it
# is the last PDF-era quarter.  Used only to count the spans that cross it.
CSV_ERA_FIRST_QUARTER = "2016Q1"
PDF_ERA_LAST_QUARTER = "2015Q4"

CHAMBER_HOUSE = "house"
CHAMBER_SENATE = "senate"
PERIOD_KIND = {CHAMBER_HOUSE: "quarter", CHAMBER_SENATE: "half_year"}

# The two sealed denominators the spec names.  They are expectations, not pins:
# the measured denominator is what the rates divide by, and both are reported.
EXPECTED_CURRENT_STAFFERS = 5773
EXPECTED_LDA_PAYROLL_PEOPLE = 6101

# ---- INV-10 dials.  UNTESTED DEFAULTS pending Paul's freeze. ---------------
ANNUALIZATION_DAYS = 365.2425
ENVELOPE_WIDENING_REPORTING_PERIODS = 1
MAX_OFFICE_RAW_EXAMPLES = 3
SHARED_EMPLOYEE_TITLE_PHRASES = ("SHARED EMPLOYEE",)
QUORUM_MEMBER_ROSTER_FALLBACK = True
CROSS_CHAMBER_REQUIRES_DISJOINT_PERIODS = True
# Part B v2 consumes these; Part C emits no weight and they cannot move any
# Part C output.  Declared here so the sweep has one home.
S_STRENGTH = {"S1": 0.75, "S2": 0.50, "S3": 0.25}

# ---- INV-7 language law ----------------------------------------------------
LANGUAGE_LAW_TOKENS = (
    "access",
    "causal",
    "friend",
    "ideolog",
    "influence",
    "predict",
)
VERBATIM_LEAF_NAMES = frozenset(
    {
        "display_name",
        "first",
        "last",
        "member_display",
        "office_key",
        "office_raw_examples",
        "title_first",
        "title_last",
        "title_raw",
        "titles",
    }
)
VERBATIM_SOURCE_QUOTED_FIELDS = (
    "current_staffer_links.display_name",
    "current_staffer_links.display_name_key.first",
    "current_staffer_links.display_name_key.last",
    "current_staffer_links.hill_history[].office_key",
    "current_staffer_links.hill_history[].title_last",
    "current_staffer_links.member_display",
    "current_staffer_links.title_raw",
    "hill_person_office_spans.office_key",
    "hill_person_office_spans.office_raw_examples[]",
    "hill_person_office_spans.title_first",
    "hill_person_office_spans.title_last",
    "hill_person_office_spans.titles[]",
    "hill_person_spine.payee_key.first",
    "hill_person_spine.payee_key.last",
    "member_office_index.office_key",
    "member_office_index.office_raw_examples[]",
)
LANGUAGE_LAW_POLICY = (
    "Banned tokens are rejected in every field name, in every value this builder "
    "authors, and in all receipt prose. Values quoted verbatim from a source "
    "ledger -- an official office string, a job title as printed, a person's own "
    "name -- are exempt and enumerated in verbatim_source_quoted_fields; their "
    "token occurrences are counted and reported rather than suppressed, because "
    "editing the record would falsify it. Part C, unlike Part A, does emit "
    "normalized name components: its spec requires the payee key triple on the "
    "spine row and the staffer display name on the link row."
)


# ---- NAME STANDARD (--name-standard) ---------------------------------------
# Paul ruled on 2026-09-06 that ONE person-name standard governs every
# staffer-network name source, and that the Hill spine is RE-KEYED under it as a
# NEW immutable generation carrying an id map -- not overlaid onto an existing
# generation.  This mode is that re-key.  It is OFF by default.
#
# WHAT MOVES, AND WHAT IS HELD FIXED
#   Moves:  spine_person_id; the spine row's payee_key block; and the
#           spine_person_id every span row, LDA link row and current-staffer
#           link row carries.
#   Fixed:  the observation parse, the office key, the office node grouping,
#           nodes_linkable, cluster_nodes, the cross-chamber rule, every span
#           field other than spine_person_id, and the member office index.
#           The identity DECISIONS of the previous generation are preserved
#           exactly and only the name a person is keyed by changes.  That is
#           what makes the delta attributable and the id map exact and total.
#           It also means the office node grouping still keys on this module's
#           own payee key triple, NOT on the standard's key: re-grouping on the
#           standard's key would merge office nodes and change the span
#           population, which is a different spine, not a re-key of this one.
#
# THE ID TUPLE.  With the flag on,
#
#     spine_person_id = "hill:person:" + sha256(compact({
#         "chamber":          <anchor node chamber>,
#         "first_office_key": <anchor node office key>,
#         "first_period":     <anchor node first period>,
#         "name_key":         "<last>|<first_class>|<middle initial>",
#     })).hexdigest()
#
# against the previous rule, which held ``"payee_key": [last, first, mi]`` in
# the fourth slot where ``"name_key"`` now stands.  The anchor node is the same
# under both rules: the minimum over the person's office nodes of (period start
# ordinal, chamber, office key).  Every spine row also carries
# ``legacy_person_id``, the previous rule's digest over that same anchor, so the
# map between the two generations is read off the build rather than
# reconstructed afterwards.
#
# THE KEY SOURCE IS THE RAW PARSE (lane-owner ruling A, 2026-09-07).
# ``name_key`` is ``parse_name(<chosen raw payee string>, <source>)`` and
# nothing else.  The chosen raw is picked from the raws THIS PERSON was
# recorded under, by the read-only delta's own rule: prefer a key carrying a
# non-empty middle initial, then the most frequently recorded, then the
# lexicographic minimum.
#
# ``parts_from_payee_key`` is NO LONGER a key route.  It lifts this module's
# own already-parsed triple, and the triple cannot express three of the v1.1
# rules: ``payroll_payee_key`` deletes a bare "V", splits a particle surname
# and absorbs a glued annotation before the triple exists.  The lift is still
# computed for every person, and ``receipt.name_standard.
# key_source_disagreements`` is the histogram, BY CAUSE, of how far the two
# routes are apart.  That histogram is a measurement, not a gate: it never
# fails the build.  The two parses are also not equal on the PARTS -- the raw
# parse recovers a suffix ``_name_tokens`` drops before the surname is joined
# -- and that recovered suffix is why both are emitted.
#
# SOURCES.  The Senate lane parses with source "senate", which handles the
# SENATOR and INTERN COMPENSATION forms and falls through to the comma rule
# otherwise.  The House lane parses with "payroll_comma" when this module's own
# comma test says the string carries a comma and with "house_csv" when it does
# not, which is the same branch ``payroll_payee_key`` takes.  Both sources strip
# the same date hints this module strips.
#
# MERGES, AND THE DAY-LEVEL GUARD (lane-owner ruling C, D-020).  Two people
# whose previous ids differed can land on one id tuple when their name keys
# fold together on the same anchor.  They become ONE spine row over the union
# of their office nodes -- UNLESS, in the same office and the same report
# period, their distinct payee lines carry service-date windows that overlap at
# DAY level.  Only House Statement of Disbursements rows print service dates; a
# Senate report period is not a day. From the 2026-09-08 adjudication, missing
# dates ALSO block a merge of same-office, same-period distinct payee lines
# (basis same_period_variant_no_day_dates). A blocked pair is kept apart by
# ``collision_ordinal`` inside the hashed tuple.  A merge still cannot split a
# person: the key is resolved per person and a person carries exactly one
# resolved key, so the map can only be many-to-one.
#
# SPANS AFTER A MERGE.  A merged person can hold two office nodes that are the
# same office under two spellings.  Where their reporting windows overlap or
# abut they are ONE span row; where a real gap separates them they stay two.
# ``counts.spans_unioned_after_merge`` is how many rows that removed.
NAME_STANDARD_ID_MAP_FILE = "spine_id_map_v6_to_v7.ndjson.gz"
NAME_STANDARD_ID_MAP_SCHEMA = "staffer-network-hill-person-spine-id-map-v1"
NAME_STANDARD_MODULE_RELATIVE = ("fec", "staffer_network", "name_standard.py")
NAME_STANDARD_MAX_RAW_EXAMPLES = 3
#: Leaf field names that quote a person's own name and are therefore exempt from
#: the language law, ON TOP OF ``VERBATIM_LEAF_NAMES``, in name-standard mode.
NAME_STANDARD_VERBATIM_LEAF_NAMES = frozenset(
    {
        "first_class",
        "first_folded",
        "first_office_key",
        "format_detected",
        "key_from_payee_key_lift",
        "key_from_raw_parse",
        "key_from_the_delta_reconstruction",
        "key_from_this_build",
        "key_v6",
        "key_v7",
        "keys_before",
        "middle",
        "name_key",
        "nickname_raw",
        "payee_key_first",
        "payee_raw",
        "payee_raw_examples",
        "suffix",
        "suffix_observed",
    }
)
NAME_STANDARD_VERBATIM_SOURCE_QUOTED_FIELDS = (
    "hill_person_spine.display_name",
    "hill_person_spine.name_key",
    "hill_person_spine.name_standard_parts.first",
    "hill_person_spine.name_standard_parts.format_detected",
    "hill_person_spine.name_standard_parts.last",
    "hill_person_spine.name_standard_parts.middle",
    "hill_person_spine.name_standard_parts.nickname_raw",
    "hill_person_spine.name_standard_parts.suffix",
    "hill_person_spine.payee_key.first_class",
    "hill_person_spine.payee_key.suffix",
    "hill_person_spine.payee_key_legacy_variants[].first",
    "hill_person_spine.payee_key_legacy_variants[].last",
    "hill_person_spine.payee_raw",
    "hill_person_spine.payee_raw_examples[]",
    "hill_person_spine.suffix_observed[]",
    "receipt.name_standard.delta_residuals[].key_from_the_delta_reconstruction",
    "receipt.name_standard.delta_residuals[].key_from_this_build",
    "receipt.name_standard.delta_residuals[].payee_raw_examples[]",
    "receipt.name_standard.empty_first_class[].payee_key_first",
    "receipt.name_standard.empty_first_class[].payee_raw",
    "receipt.name_standard.key_source_disagreement_examples[].payee_raw",
    "receipt.name_standard.merge_groups[].keys_before[]",
    "receipt.name_standard.merge_groups[].name_key",
    "receipt.name_standard.merges_blocked[].first_office_key",
    "receipt.name_standard.merges_blocked[].name_key",
    "receipt.name_standard.nickname_class_transitions[].first_class",
    "receipt.name_standard.nickname_class_transitions[].first_folded",
    "spine_id_map_v6_to_v7.key_v6",
    "spine_id_map_v6_to_v7.key_v7",
)

#: Ruling B.  The read-only delta resolves ONE key per payee-key triple; this
#: build resolves per person.  The two can differ only on a triple whose raws
#: disagree, and the delta measured that population exactly: 64 triples, 102
#: people.  More residuals than that means something other than the ambiguity
#: moved, and the build FAILS rather than reporting a difference it cannot
#: account for.
NAME_STANDARD_DELTA_RESIDUAL_ALLOWANCE = 102


class GateFailure(RuntimeError):
    pass


# ---------------------------------------------------------------------------
# Canonical IO -- conventions from build_tiered_corroboration_sidecar.py
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


def digest_of(value: Any) -> str:
    return hashlib.sha256(compact(value)).hexdigest()


def read_rows(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix.lower() == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise GateFailure(f"object required at {path}:{line_number}")
            yield value


def write_ndjson_gz(path: Path, values: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with temporary.open("wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                with io.TextIOWrapper(zipped, encoding="utf-8", newline="\n") as text:
                    for value in values:
                        text.write(compact(value).decode("utf-8") + "\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        temporary.write_bytes(canonical_line(value))
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Glassbox (INV-11).  Never fatal, never recorded in the receipt: the receipt
# must stay byte-identical between a primary run and a twin run that may have
# been launched with --no-glassbox.
# ---------------------------------------------------------------------------
def emit_glassbox(
    enabled: bool,
    run_id: str,
    kind: str,
    status: str,
    summary: str,
    detail: str = "",
    metadata: Mapping[str, Any] | None = None,
) -> bool:
    if not enabled or not GLASSBOX_SCRIPT.is_file():
        return False
    command = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(GLASSBOX_SCRIPT),
        "-Lane",
        "claude",
        "-Kind",
        kind,
        "-Status",
        status,
        "-Summary",
        summary,
        "-Source",
        GLASSBOX_SOURCE,
        "-Stage",
        STAGE_ID,
        "-RunId",
        run_id,
        "-Quiet",
    ]
    if detail:
        command.extend(["-Detail", detail])
    if metadata:
        command.extend(["-MetadataJson", json.dumps(metadata, sort_keys=True)])
    try:
        completed = subprocess.run(  # noqa: S603
            command, capture_output=True, timeout=60, check=False
        )
    except Exception:  # pragma: no cover - environment dependent
        return False
    return completed.returncode == 0


# ---------------------------------------------------------------------------
# Name normalization
# ---------------------------------------------------------------------------
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
DATE_HINT_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b")
NAME_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*")


def _ascii_fold(value: str | None) -> str:
    return (
        unicodedata.normalize("NFKD", value or "")
        .encode("ascii", "ignore")
        .decode("ascii")
    )


def _name_tokens(text: str) -> list[str]:
    tokens = []
    for token in NAME_TOKEN_RE.findall(text):
        trimmed = token.strip("-'")
        if not trimmed:
            continue
        if trimmed.upper() in SUFFIXES:
            continue
        tokens.append(trimmed)
    return tokens


def _triple(last: str, first: str, middle: str | None) -> tuple[str, str, str | None]:
    return (
        last.casefold(),
        first.casefold(),
        middle.casefold()[:1] if middle else None,
    )


def payroll_payee_key(value: str | None) -> tuple[str, str, str | None] | None:
    """``LAST, FIRST M.`` (comma form) or ``LAST FIRST M`` (House SOD CSV)."""

    text = DATE_HINT_RE.sub(" ", _ascii_fold(value))
    if not text.strip():
        return None
    if "," in text:
        left, _, right = text.partition(",")
        surname_tokens = _name_tokens(left)
        rest_tokens = _name_tokens(right)
        if not surname_tokens or not rest_tokens:
            return None
        surname = " ".join(surname_tokens)
        given = rest_tokens[0]
        middle = rest_tokens[1] if len(rest_tokens) > 1 else None
        return _triple(surname, given, middle)
    tokens = _name_tokens(text)
    if len(tokens) < 2:
        return None
    surname = tokens[0]
    given = tokens[1]
    middle = tokens[2] if len(tokens) > 2 else None
    return _triple(surname, given, middle)


def display_payee_key(value: str | None) -> tuple[str, str, str | None] | None:
    """``FIRST [MIDDLE] LAST`` -- LDA display names and Quorum staffer names."""

    tokens = _name_tokens(_ascii_fold(value))
    if len(tokens) < 2:
        return None
    given = tokens[0]
    surname = tokens[-1]
    middle = tokens[1] if len(tokens) > 2 else None
    return _triple(surname, given, middle)


def middle_compatible(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return True
    return left[0] == right[0]


def payee_sort_key(payee_key: tuple[str, str, str | None]) -> tuple[str, str, str]:
    """A total order over payee key triples.

    ``middle_initial`` is ``None`` when the payee string carried no middle token
    and a one-character string otherwise, so the raw triple is NOT orderable:
    ``("daly", "brendan", None) < ("daly", "brendan", "m")`` raises TypeError.
    Real payroll data carries hundreds of such pairs -- the same person written
    ``DALY, BRENDAN`` in one lane and ``DALY BRENDAN M`` in another -- so every
    sort whose key contains a payee key must go through this function.  The
    empty string stands in for ``None`` and sorts first, which is the order the
    triple would have had were the field always a string; ``_triple`` never
    produces an empty middle initial, so the substitution stays injective and
    the order stays total.
    """

    return (payee_key[0], payee_key[1], payee_key[2] or "")


# ---------------------------------------------------------------------------
# Office normalization -- ported verbatim from build_tiered_corroboration_
# sidecar.py, which itself ports the ladder's build_ladder.py.
# ---------------------------------------------------------------------------
YEAR_PREFIX_RE = re.compile(r"^\s*(19|20)\d{2}\s+")
WORD_TOKEN_RE = re.compile(r"[A-Za-z0-9']+(?:-[A-Za-z0-9']+)*")


def strip_year(value: str) -> str:
    return YEAR_PREFIX_RE.sub("", value or "")


# R-2.  The dash or apostrophe that introduces a Statement of Disbursements
# continuation line is REQUIRED.  While it was optional the pattern ate a
# trailing "CON" out of the surname itself: ``HON. DON BACON`` normalized to
# ``HON. DON BA`` and ``HON. CHARLIE MELANCON`` to ``HON. CHARLIE MELAN``, so
# both offices keyed on a truncated surname and neither could resolve against
# the roster.  A census of all 11,391 distinct House office strings finds 2,085
# genuine continuations, every one of them carrying the dash or apostrophe, and
# exactly 12 strings that end in "CON" without one -- the ten BACON allowance
# years and the two MELANCON ones.  The alternation is the same shape as
# ``build_house_personnel_ledger.py``'s CONTINUATION_RE, so Part C's office
# normalization agrees with the ledger it must not contradict.
CONTINUATION_RE = re.compile(
    "(?:[\u2014\u2013\ufffd']\\s*Con\\.?|\\s+Con\\.)\\s*$", re.IGNORECASE
)


@lru_cache(maxsize=None)
def normalize_office(raw: str) -> str:
    value = strip_year(raw or "").strip()
    value = value.replace("\u2019", "'")
    value = CONTINUATION_RE.sub("", value).strip()
    value = value.replace("&", " AND ")
    value = re.sub(r"\s+", " ", value).strip()
    return value.upper()


def is_hon_office(normalized: str) -> bool:
    return normalized.startswith("HON.") or normalized.startswith("HON ")


def _hon_remainder(normalized: str) -> str:
    return normalized.split(".", 1)[1] if normalized.startswith("HON.") else normalized[3:]


def extract_hon_first_and_surname(normalized: str) -> tuple[str | None, str | None]:
    cleaned = []
    for token in WORD_TOKEN_RE.findall(_hon_remainder(normalized)):
        trimmed = token.strip(".").strip(",")
        if not trimmed or trimmed.upper() in SUFFIXES:
            continue
        if len(trimmed.replace(".", "")) <= 1:
            continue
        cleaned.append(trimmed)
    if not cleaned:
        return None, None
    return (cleaned[0] if len(cleaned) >= 2 else None), cleaned[-1]


@lru_cache(maxsize=None)
def senate_office_key(office_raw: str) -> str:
    value = (office_raw or "").replace("\u2019", "'").strip()
    return re.sub(r"\s+", " ", value).upper()


# ---------------------------------------------------------------------------
# R-1.  House MEMBER offices are keyed on the RESOLVED MEMBER, never on the bare
# surname.
#
# ``house_office_key`` above keys a member office ``HON:<SURNAME>``, so every
# member sharing a surname collapsed into one office: 104 of 955 member-office
# keys covered more than one member and ``office_profile`` then stamped the
# alphabetically-first member's bioguide on every span in the merged office --
# a positive false attribution, and one that also suppressed the same-period
# collision rule between two same-surname members.
#
# The replacement keys a member office on the member the HOUSE LEDGER resolved.
# ``build_house_personnel_ledger.py`` already emits ``HON:<bioguide>`` for every
# office string its STRICT surname + first-name + rep-term-in-allowance-year
# rule resolves, and that resolution is the verified one Part C must not
# contradict.  Three levels, in order:
#
#   1. LEDGER OFFICE ROW, EXACT.  The office string appears in the House ledger
#      and the ledger resolved it to a bioguide -> reuse the ledger's own
#      ``HON:<bioguide>``.  Measured over ledger v3: 9,631 distinct member-office
#      strings, zero of which carry two different ledger office keys, so the join
#      is a function.  ``ledger_office_string_key_conflicts`` in the receipt is
#      that zero, re-measured on every build.
#   2. LEDGER OFFICE ROW, BY MEMBER NAME.  The office string does not appear in
#      the ledger -- the LDA lanes' office strings, which carry no allowance-year
#      prefix -- but its (nickname-normalized first name, surname) pair is one
#      the ledger resolved.  Accepted only when that pair carries exactly one
#      ledger bioguide AND at most one roster member holding it served in
#      HOUSE_MEMBER_KEY_ERA, so a namesake from one era can never inherit the
#      other era's member's bioguide.
#
#      SIX era-scoped pairs are ambiguous -- two roster members holding the pair
#      both served in 2009-2026 -- and they are the real modern collisions:
#      DONALD PAYNE, DUNCAN HUNTER, MICHAEL ROGERS, PATRICK MURPHY,
#      ROBERT MENENDEZ, TIMOTHY JOHNSON.  How many of the six are REJECTED here
#      depends on how many of them the BOUND ledger's resolved map contains, and
#      that is why the earlier wording -- "Five pairs are rejected", above a list
#      of six names -- read as a contradiction:
#        - Against ledger v1 (CSV era only, 2016Q1-2026Q1) five of the six were
#          in the resolved map and were rejected on the era-roster test.  TIMOTHY
#          JOHNSON was not in it at all: Rep. Timothy V. Johnson left in 2013,
#          inside the PDF era v1 did not cover, so there was nothing to reject.
#          Six ambiguous, five rejected.
#        - Against ledger v3 (both eras in one file) all six are in the map.
#          Four are rejected on the era-roster test (DUNCAN HUNTER, MICHAEL
#          ROGERS, ROBERT MENENDEZ, TIMOTHY JOHNSON) and two never reach it:
#          DONALD PAYNE and PATRICK MURPHY are rejected one test earlier because
#          the ledger itself now resolves that pair to two different bioguides
#          across the two eras (P000149/P000604 and M001168/M001191).  Six
#          ambiguous, six rejected, none accepted.
#      Both counts are re-measured on every build and reported as
#      ``member_name_pairs_rejected_two_era_roster_members`` and
#      ``member_name_pairs_rejected_two_ledger_bioguides``.  Their SUM is how
#      many ambiguous pairs the bound ledger can see; neither alone is.
#   3. FALLBACK.  ``HON:<FIRST>|<SURNAME>``, normalized, so two members with
#      different names can never share a key.  Two members with the SAME first
#      name and surname still share this key -- that is the residue the office
#      string cannot separate, and the ledger refuses to resolve it too, so the
#      key carries no bioguide and attributes nothing.
#
# The same callable is applied on BOTH sides of every office join -- the two
# personnel lanes, the LDA match lanes and the member office index -- so the
# joins stay self-consistent.
#
# This does not restate Part A's ladder rule.  INV-5 pins Part A's tier counts,
# not Part C's office key.
# ---------------------------------------------------------------------------
HOUSE_MEMBER_KEY_ERA = (2009, 2026)


def house_member_name_pair(
    office_raw: str, nicknames: Mapping[str, str]
) -> tuple[str, str] | None:
    """(nickname-normalized first name, surname) for a HON. office string."""

    normalized = normalize_office(office_raw)
    if not is_hon_office(normalized):
        return None
    first, surname = extract_hon_first_and_surname(normalized)
    if not surname:
        return None
    return normalize_first_name(first, nicknames).upper(), surname.upper()


class HouseOfficeKey:
    """The House office key.  Pure function of the office string."""

    def __init__(
        self,
        ledger_key_by_office_raw: Mapping[str, str],
        bioguide_by_name_pair: Mapping[tuple[str, str], str],
        nicknames: Mapping[str, str],
    ) -> None:
        self._by_raw = dict(ledger_key_by_office_raw)
        self._by_pair = dict(bioguide_by_name_pair)
        self._nicknames = dict(nicknames)
        self._cache: dict[str, str] = {}
        # office_key -> the bioguide that key names, for every key whose member
        # identity came from the House ledger.  ``office_profile`` reads this
        # instead of re-deriving, which is what makes the emitted bioguide equal
        # the ledger's on every row the ledger resolved.
        self.bioguide_by_key: dict[str, str] = {}
        for key in self._by_raw.values():
            self.bioguide_by_key[key] = key.split(":", 1)[1]
        for bioguide in self._by_pair.values():
            self.bioguide_by_key[f"HON:{bioguide}"] = bioguide

    def __call__(self, office_raw: str) -> str:
        cached = self._cache.get(office_raw)
        if cached is not None:
            return cached
        self._cache[office_raw] = key = self._derive(office_raw)
        return key

    def _derive(self, office_raw: str) -> str:
        normalized = normalize_office(office_raw)
        if not is_hon_office(normalized):
            return normalized
        exact = self._by_raw.get(office_raw)
        if exact is not None:
            return exact
        pair = house_member_name_pair(office_raw, self._nicknames)
        if pair is None:
            return f"HON:{normalized}"
        bioguide = self._by_pair.get(pair)
        if bioguide is not None:
            return f"HON:{bioguide}"
        return f"HON:{pair[0]}|{pair[1]}"


def build_house_office_key(
    ledger_observations_path: Path | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nicknames: Mapping[str, str],
) -> tuple[HouseOfficeKey, dict[str, int], list[str]]:
    """Pre-pass over the House ledger to build the two member-office maps."""

    key_by_raw: dict[str, str] = {}
    bios_by_pair: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    failures: list[str] = []
    conflicts = 0
    flagged_rows = 0
    titled_rows = 0
    if ledger_observations_path is not None:
        for row in read_rows(ledger_observations_path):
            # Measured in the same pass, for the receipt's shared-employee note:
            # the ledger's own shared_employee_flag against the title test this
            # lane actually applies.
            if row.get("shared_employee_flag") is True:
                flagged_rows += 1
            if is_shared_employee(clean_title(row.get("title_raw"))):
                titled_rows += 1
            raw = row.get("office_raw")
            key = row.get("office_key")
            bioguide = row.get("member_bioguide")
            if not isinstance(raw, str) or not raw:
                continue
            if not isinstance(key, str) or not isinstance(bioguide, str) or not bioguide:
                continue
            if key != f"HON:{bioguide}":
                continue
            previous = key_by_raw.get(raw)
            if previous is not None and previous != key:
                conflicts += 1
                continue
            key_by_raw[raw] = key
            pair = house_member_name_pair(raw, nicknames)
            if pair is not None:
                bios_by_pair[pair].add(bioguide)
    if conflicts:
        failures.append("HOUSE_LEDGER_OFFICE_KEY_NOT_A_FUNCTION")

    low, high = HOUSE_MEMBER_KEY_ERA
    era_pairs: defaultdict[tuple[str, str], set[str]] = defaultdict(set)
    for surname, people in roster.items():
        for person in people:
            if person["max_year"] < low or person["min_year"] > high:
                continue
            era_pairs[
                (normalize_first_name(person["first"], nicknames).upper(), surname)
            ].add(person["bioguide"])

    accepted: dict[tuple[str, str], str] = {}
    rejected_two_ledger_bioguides = 0
    rejected_two_era_roster_members = 0
    for pair, bioguides in bios_by_pair.items():
        if len(bioguides) > 1:
            rejected_two_ledger_bioguides += 1
            continue
        if len(era_pairs.get(pair, ())) > 1:
            rejected_two_era_roster_members += 1
            continue
        accepted[pair] = next(iter(bioguides))

    stats = {
        "ledger_rows_with_shared_employee_flag": flagged_rows,
        "ledger_rows_with_shared_employee_title": titled_rows,
        "ledger_member_office_strings": len(key_by_raw),
        "ledger_office_string_key_conflicts": conflicts,
        "member_name_pairs_accepted": len(accepted),
        "member_name_pairs_rejected_two_era_roster_members": (
            rejected_two_era_roster_members
        ),
        "member_name_pairs_rejected_two_ledger_bioguides": (
            rejected_two_ledger_bioguides
        ),
        "member_name_pairs_seen_in_ledger": len(bios_by_pair),
    }
    return HouseOfficeKey(key_by_raw, accepted, nicknames), stats, failures


HOUSE_LEADERSHIP_FAMILIES = frozenset(
    {
        "ASIAN PACIFIC AMERICAN CAUCUS",
        "CONGRESSIONAL BLACK CAUCUS",
        "CONGRESSIONAL HISPANIC CAUCUS",
        "CONGRESSIONAL LABOR CAUCUS",
        "CONGRESSIONAL PROGRESSIVE CAUCUS",
        "CONGRESSIONAL WESTERN CAUCUS",
        "DEMOCRATIC CAUCUS",
        "DEMOCRATIC STEERING AND POLICY",
        "DEMOCRATIC WOMENS CAUCUS",
        "EQUALITY CAUCUS",
        "NEW DEMOCRAT COALITION",
        "OFFICE OF THE DEMOCRATIC WHIP",
        "OFFICE OF THE MAJORITY LEADER",
        "OFFICE OF THE MAJORITY WHIP",
        "OFFICE OF THE MINORITY LEADER",
        "OFFICE OF THE MINORITY WHIP",
        "OFFICE OF THE SPEAKER",
        "REPUBLICAN CONFERENCE",
        "REPUBLICAN POLICY COMMITTEE",
        "REPUBLICAN STEERING COMMITTEE",
        "REPUBLICAN STUDY COMMITTEE",
    }
)
HOUSE_ADMIN_FAMILIES = frozenset(
    {
        "CHIEF ADMIN OFCR OF THE HOUSE",
        "CLERK OF THE HOUSE",
        "CLOAKROOM PERSONNEL - MAJ",
        "CLOAKROOM PERSONNEL - MIN",
        "DIVERSITY AND INCLUSION",
        "DS-TRAINING AND PROGRAM DEVEL.",
        "GOVERNMENT CONTRIBUTIONS",
        "HOUSE CHILD CARE CENTER",
        "INTERPARLIAMENTARY AFFAIRS",
        "LAW REVISION COUNSEL",
        "LEGISLATIVE COUNSEL",
        "LEGISLATIVE FLOOR ACTIVITIES",
        "MINORITY EMPLOYEES",
        "OFFICE OF CONGRESSIONAL ETHICS",
        "OFFICE OF FINANCE",
        "OFFICE OF INSPECTOR GENERAL",
        "OFFICE OF THE HISTORIAN",
        "OFFICE OF THE PARLIAMENTARIAN",
        "OTHER ADMINISTRATION",
        "RC-TRAINING AND PROGRAM DEVEL.",
        "SALARIES OFFICERS AND EMPLOYEES",
        "SERGEANT AT ARMS",
        "TRANSITION AIDES",
    }
)
HOUSE_COMMITTEE_SHAPE_RE = re.compile(r"(?:^|\W)(COMM|COMMITTEE)(?:\W|$)")
# The committee/leadership office families build_ladder.py maps by name.  Part A
# keeps them in COMMITTEE_KEYWORDS with their corroboration phrases; Part C needs
# only the key set, so that an office such as TRANSPORTATION-INFRASTRUCTURE --
# which carries no COMM token -- lands on the same container_kind here as it does
# in the Part A sidecar.
HOUSE_COMMITTEE_FAMILIES = frozenset(
    {
        "ARMED SERVICES COMMITTEE",
        "COMMITTEE ON AGRICULTURE",
        "COMMITTEE ON APPROPRIATIONS",
        "COMMITTEE ON BENGHAZI",
        "COMMITTEE ON BUDGET",
        "COMMITTEE ON ENERGY AND COMMERCE",
        "COMMITTEE ON ETHICS",
        "COMMITTEE ON FINANCIAL SERVICE",
        "COMMITTEE ON FINANCIAL SERVICES",
        "COMMITTEE ON FOREIGN AFFAIRS",
        "COMMITTEE ON JUDICIARY",
        "COMMITTEE ON NATURAL RESOURCES",
        "COMMITTEE ON RULES",
        "COMMITTEE ON SMALL BUSINESS",
        "COMMITTEE ON VETERANS AFFAIRS",
        "EDUCATION AND LABOR",
        "ENERGY INDEP AND GLOBAL WARMING",
        "ENERGY INDEPEN AND GLB WARMING",
        "HOMELAND SECURITY",
        "HOUSE ADMINISTRATION",
        "INTELLIGENCE",
        "JOINT COMMMITTEE ON TAXATION",
        "OVERSIGHT AND GOVERNMENT REFORM",
        "SCIENCE AND TECHNOLOGY",
        "STANDARDS OF OFFICIAL CONDUCT",
        "TRANSPORTATION-INFRASTRUCTURE",
        "VETERANS AFFAIRS",
        "VETERANS' AFFAIRS",
    }
)


@lru_cache(maxsize=None)
def container_kind_house(office_raw: str) -> str:
    normalized = normalize_office(office_raw)
    if not normalized:
        return "unresolved"
    if is_hon_office(normalized):
        return "member_office"
    if normalized in HOUSE_LEADERSHIP_FAMILIES:
        return "leadership"
    if normalized in HOUSE_ADMIN_FAMILIES:
        return "admin"
    if normalized in HOUSE_COMMITTEE_FAMILIES or HOUSE_COMMITTEE_SHAPE_RE.search(
        normalized
    ):
        return "committee"
    return "unresolved"


SENATE_SUFFIX_RE = re.compile(r",?\s*(JR\.?|SR\.?|III|II|IV)\.?\s*$", re.IGNORECASE)
SENATOR_RE = re.compile(r"^SENATOR\s+(.+)$", re.IGNORECASE)
INTERN_RE = re.compile(r"^INTERN COMPENSATION\s*-\s*(.+)$", re.IGNORECASE)
SENATE_LEADERSHIP_PHRASES = (
    "CAUCUS",
    "MAJORITY CONFERENCE",
    "MAJORITY LEADER",
    "MAJORITY WHIP",
    "MINORITY CONFERENCE",
    "MINORITY LEADER",
    "MINORITY WHIP",
    "PRES PRO TEM",
    "PRESIDENT PRO TEMPORE",
    "SECRETARY FOR THE MAJORITY",
    "SECRETARY FOR THE MINORITY",
    "VICE PRESIDENT",
)
SENATE_COMMITTEE_OFFICE_KEYS = frozenset({
    "AGRICULTURE NUTR FOR", "AGRICULTURE NUTRITION AND FORESTRY",
    "AGRICULTURE NUTRITION FORESTRY", "APPROPRIATIONS", "ARMED SERVICES",
    "BANKING HOUSING AND URBAN AFFAIRS", "BANKING HOUSING URBAN AFFAIRS",
    "BANKING HOUSING URBDEV", "BUDGET", "COMMERCE SCI TRANS",
    "COMMERCE SCIENCE AND TRANSPORTATION", "COMMERCE SCIENCE TRANSPORTATION",
    "ENERGY AND NATURAL RESOURCES", "ENERGY NATURAL RES",
    "ENERGY NATURAL RESOURCES", "ENVIRONMENT AND PUBLIC WORKS",
    "ENVIRONMENT PUB WORKS", "ENVIRONMENT PUBLIC WORKS", "ETHICS", "FINANCE",
    "FOREIGN RELATIONS", "HEALTH EDU LABOR PENS",
    "HEALTH EDUCATION LABOR AND PENSIONS", "HOMELAND SEC GOV AFF",
    "HOMELAND SECURITY AND GOVERNMENTAL AFFAIRS",
    "HOMELAND SECURITY GOVERNMENTAL AFFAIRS", "INDIAN AFFAIRS", "INTELLIGENCE",
    "JOINT ECONOMIC", "JUDICIARY", "RULES ADMINISTRATION",
    "RULES AND ADMINISTRATION", "SELECT COM ON INTEL", "SMALL BUS ENTREP",
    "SMALL BUSINESS AND ENTREPRENEURSHIP", "SPECIAL COM ON AGING",
    "SPECIAL COMMITTEE ON AGING", "VETERANS AFFAIRS",
})


def senate_member_first_and_surname(office: str) -> tuple[str | None, str | None]:
    upper = (office or "").strip().upper()
    senator = SENATOR_RE.match(upper)
    if senator:
        remainder = SENATE_SUFFIX_RE.sub("", senator.group(1)).strip()
        tokens = [item.strip(".,") for item in remainder.split() if item.strip(".,")]
        tokens = [item for item in tokens if len(item.replace(".", "")) > 1]
        if not tokens:
            return None, None
        return (tokens[0] if len(tokens) >= 2 else None), tokens[-1]
    intern = INTERN_RE.match(upper)
    if intern:
        surname = intern.group(1).strip().strip(".,")
        return (None, surname) if surname else (None, None)
    return None, None


def container_kind_senate(office: str) -> str:
    upper = (office or "").strip().upper()
    if not upper:
        return "unresolved"
    if SENATOR_RE.match(upper) or INTERN_RE.match(upper):
        return "member_office"
    committee_key = re.sub(r"[^A-Z0-9]+", " ", upper).strip()
    if "COMMITTEE" in upper or committee_key in SENATE_COMMITTEE_OFFICE_KEYS:
        return "committee"
    for phrase in SENATE_LEADERSHIP_PHRASES:
        if phrase in upper:
            return "leadership"
    return "admin"


def office_member_name(chamber: str, office_raw: str) -> tuple[str | None, str | None]:
    if chamber == CHAMBER_HOUSE:
        normalized = normalize_office(office_raw)
        if not is_hon_office(normalized):
            return None, None
        return extract_hon_first_and_surname(normalized)
    return senate_member_first_and_surname(office_raw)


# ---------------------------------------------------------------------------
# Roster + nickname table + the Part A v2 term-window rule (INV-6)
# ---------------------------------------------------------------------------
NICKNAME_MAP = {
    'bill': 'william', 'billy': 'william', 'will': 'william',
    'joe': 'joseph', 'joey': 'joseph',
    'mike': 'michael', 'mikey': 'michael',
    'bob': 'robert', 'bobby': 'robert', 'rob': 'robert', 'robbie': 'robert',
    'jim': 'james', 'jimmy': 'james',
    'tom': 'thomas', 'tommy': 'thomas',
    'dave': 'david', 'davey': 'david',
    'chuck': 'charles', 'charlie': 'charles', 'chick': 'charles',
    'ted': 'edward', 'eddie': 'edward', 'ed': 'edward',
    'rich': 'richard', 'rick': 'richard', 'ricky': 'richard', 'dick': 'richard',
    'dan': 'daniel', 'danny': 'daniel',
    'ken': 'kenneth', 'kenny': 'kenneth',
    'greg': 'gregory',
    'steve': 'steven',
    'pat': 'patrick',
    'tony': 'anthony',
    'nick': 'nicholas',
    'andy': 'andrew', 'drew': 'andrew',
    'matt': 'matthew',
    'chris': 'christopher',
    'sam': 'samuel',
    'alex': 'alexander',
    'ben': 'benjamin',
    'gene': 'eugene',
    'larry': 'lawrence',
    'jerry': 'gerald',
    'ron': 'ronald', 'ronnie': 'ronald',
    'russ': 'russell',
    'walt': 'walter',
    'nate': 'nathan',
    'liz': 'elizabeth', 'beth': 'elizabeth',
    'kathy': 'katherine', 'kate': 'katherine', 'katie': 'katherine',
    'debbie': 'deborah', 'deb': 'deborah',
    'sue': 'susan', 'suzy': 'susan',
}


NICKNAME_TABLE_SCHEMA_ID = "staffer-network-first-name-nickname-table-v1"


def _flatten_nickname_payload(payload: Any) -> dict[str, str]:
    """Accept the committed Part A v2 table, a flat ``{nickname: canonical}``
    map, an inverted ``{canonical: [nicknames]}`` map, or either of those nested
    under a ``map``/``nicknames``/``aliases`` key.

    The committed table ``first_name_nicknames_v1.json`` is
    ``{"schema_id": ..., "provenance": ..., "entries": {short: [formal, ...]}}``
    and its own provenance states that each entry maps one casefolded short form
    to ONE OR MORE casefolded formal forms.  It is read short -> formal, and an
    entry carrying more than one formal form is DROPPED rather than collapsed:
    folding ``alan`` and ``albert`` both onto ``al`` would let one office string
    match two different roster people, which is exactly the fuzzy join INV-6
    forbids.  A dropped short form simply stays itself on both sides of the
    comparison, so the strict exact-match rule still applies to it.
    """

    if not isinstance(payload, Mapping):
        return {}
    entries = payload.get("entries")
    if payload.get("schema_id") == NICKNAME_TABLE_SCHEMA_ID and isinstance(
        entries, Mapping
    ):
        committed: dict[str, str] = {}
        for short, formal in entries.items():
            if isinstance(formal, str):
                committed[str(short).strip().lower()] = formal.strip().lower()
            elif (
                isinstance(formal, list)
                and len(formal) == 1
                and isinstance(formal[0], str)
            ):
                committed[str(short).strip().lower()] = formal[0].strip().lower()
        return committed
    for wrapper in ("map", "nicknames", "aliases", "first_name_nicknames"):
        nested = payload.get(wrapper)
        if isinstance(nested, Mapping):
            return _flatten_nickname_payload(nested)
    flat: dict[str, str] = {}
    for key, value in payload.items():
        if isinstance(value, str):
            flat[str(key).strip().lower()] = value.strip().lower()
        elif isinstance(value, list):
            canonical = str(key).strip().lower()
            for item in value:
                if isinstance(item, str):
                    flat[item.strip().lower()] = canonical
    return flat


def load_nickname_table(path: Path | None) -> tuple[dict[str, str], bool]:
    table = dict(NICKNAME_MAP)
    if path is None or not Path(path).is_file():
        return table, False
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return table, False
    flattened = _flatten_nickname_payload(payload)
    table.update(flattened)
    # A file that parses but yields no usable pair is NOT a loaded table: saying
    # otherwise in the receipt would assert a provenance the build does not have.
    return table, bool(flattened)


def normalize_first_name(name: str | None, table: Mapping[str, str]) -> str:
    lowered = (name or "").lower().strip(".")
    return table.get(lowered, lowered)


def load_roster(directory: Path | None) -> dict[str, list[dict[str, Any]]]:
    by_surname: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    if directory is None:
        return {}
    directory = Path(directory)
    for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
        path = directory / filename
        if not path.is_file():
            continue
        with path.open("r", encoding="utf-8") as stream:
            people = yaml.safe_load(stream) or []
        for person in people:
            bioguide = ((person or {}).get("id") or {}).get("bioguide")
            if not bioguide:
                continue
            name = person.get("name") or {}
            years = []
            for term in person.get("terms") or []:
                try:
                    years.append((int(term["start"][:4]), int(term["end"][:4])))
                except Exception:
                    pass
            if not years:
                continue
            by_surname[str(name.get("last", "")).upper()].append(
                {
                    "bioguide": bioguide,
                    "first": str(name.get("first", "")),
                    "official_full": str(name.get("official_full", "")),
                    "min_year": min(item[0] for item in years),
                    "max_year": max(item[1] for item in years),
                }
            )
    return {
        key: sorted(value, key=lambda item: item["bioguide"])
        for key, value in by_surname.items()
    }


def resolve_member_bioguide(
    first: str | None,
    surname: str | None,
    roster: Mapping[str, list[dict[str, Any]]],
    nicknames: Mapping[str, str],
    year_window: tuple[int, int] | None = None,
) -> tuple[str | None, str]:
    """INV-6 strict-bioguide resolution with the Part A v2 term window.

    A bioguide is returned only when the roster surname matches exactly and
    either the first name matches exactly after nickname normalization, or the
    surname is unique and the office string carried no first name.  The term
    window restricts the roster candidates to members whose service years
    intersect the observed reporting years before either rule is applied; when
    the window is what made the answer unique the method records that.  Every
    other outcome keeps ``member_bioguide: null``.  No fuzzy join.
    """

    if not surname:
        return None, "UNRESOLVED_SURNAME_NOT_PARSED"
    candidates = roster.get(surname.upper())
    if not candidates:
        return None, "UNRESOLVED_SURNAME_NOT_IN_ROSTER"
    if year_window is None:
        windowed = list(candidates)
    else:
        low, high = year_window
        windowed = [
            candidate
            for candidate in candidates
            if candidate["min_year"] <= high and candidate["max_year"] >= low
        ]
        if not windowed:
            return None, "UNRESOLVED_NO_ROSTER_TERM_IN_OBSERVED_WINDOW"
    if first:
        normalized = normalize_first_name(first, nicknames)
        matched = [
            candidate
            for candidate in windowed
            if normalize_first_name(candidate["first"], nicknames) == normalized
        ]
        matched_all = [
            candidate
            for candidate in candidates
            if normalize_first_name(candidate["first"], nicknames) == normalized
        ]
        if len(matched) == 1:
            method = (
                "STRICT_ROSTER_SURNAME_AND_FIRST_NAME"
                if len(matched_all) == 1
                else "STRICT_ROSTER_SURNAME_AND_FIRST_NAME_TERM_WINDOW"
            )
            return matched[0]["bioguide"], method
        if len(matched) > 1:
            return None, "UNRESOLVED_FIRST_NAME_DOES_NOT_DISAMBIGUATE"
        return None, "UNRESOLVED_FIRST_NAME_NOT_IN_ROSTER"
    if len(windowed) == 1:
        method = (
            "STRICT_ROSTER_UNIQUE_SURNAME_NO_FIRST_NAME_IN_OFFICE_STRING"
            if len(candidates) == 1
            else "STRICT_ROSTER_UNIQUE_SURNAME_TERM_WINDOW"
        )
        return windowed[0]["bioguide"], method
    return None, "UNRESOLVED_SURNAME_COLLISION_NO_FIRST_NAME"


# ---------------------------------------------------------------------------
# Reporting periods
# ---------------------------------------------------------------------------
QUARTER_RE = re.compile(r"^(\d{4})Q([1-4])$")


def quarter_from_token(token: str | None) -> tuple[int, int] | None:
    match = QUARTER_RE.match((token or "").strip().upper())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def quarter_from_date(day: date) -> tuple[int, int]:
    return day.year, (day.month - 1) // 3 + 1


def quarter_token(key: tuple[int, int]) -> str:
    return f"{key[0]}Q{key[1]}"


def quarter_ordinal(key: tuple[int, int]) -> int:
    return key[0] * 4 + (key[1] - 1)


def quarter_from_ordinal(ordinal: int) -> tuple[int, int]:
    return ordinal // 4, (ordinal % 4) + 1


def quarter_bounds(key: tuple[int, int]) -> tuple[date, date]:
    year, quarter = key
    start = date(year, 3 * quarter - 2, 1)
    end = (
        date(year, 12, 31)
        if quarter == 4
        else date(year, 3 * quarter + 1, 1) - timedelta(days=1)
    )
    return start, end


def senate_window(day: date) -> tuple[date, date]:
    if day.month >= 10:
        return date(day.year, 10, 1), date(day.year + 1, 3, 31)
    if day.month <= 3:
        return date(day.year - 1, 10, 1), date(day.year, 3, 31)
    return date(day.year, 4, 1), date(day.year, 9, 30)


def senate_ordinal(start: date) -> int:
    return start.year * 2 + (0 if start.month == 4 else 1)


def senate_start_from_ordinal(ordinal: int) -> date:
    year, remainder = divmod(ordinal, 2)
    return date(year, 4, 1) if remainder == 0 else date(year, 10, 1)


def period_ordinal(chamber: str, token: str) -> int:
    if chamber == CHAMBER_HOUSE:
        key = quarter_from_token(token)
        if key is None:
            raise GateFailure(f"unparseable house period token {token!r}")
        return quarter_ordinal(key)
    return senate_ordinal(parse_iso(token))


def period_token_from_ordinal(chamber: str, ordinal: int) -> str:
    if chamber == CHAMBER_HOUSE:
        return quarter_token(quarter_from_ordinal(ordinal))
    return senate_start_from_ordinal(ordinal).isoformat()


def period_bounds(chamber: str, token: str) -> tuple[date, date]:
    if chamber == CHAMBER_HOUSE:
        key = quarter_from_token(token)
        if key is None:
            raise GateFailure(f"unparseable house period token {token!r}")
        return quarter_bounds(key)
    return senate_window(parse_iso(token))


def parse_iso(value: str | None) -> date | None:
    if not value:
        return None
    text = str(value).strip()[:10]
    try:
        year, month, day = (int(part) for part in text.split("-"))
        return date(year, month, day)
    except Exception:
        return None


AMOUNT_CLEAN_RE = re.compile(r"[,$\s]")


def parse_amount(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = AMOUNT_CLEAN_RE.sub("", str(value))
    if not text:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1]
    try:
        return float(text)
    except ValueError:
        return None


def clean_title(value: Any) -> str | None:
    if value is None:
        return None
    text = re.sub(r"\s+", " ", str(value)).strip()
    return text or None


def is_shared_employee(title: str | None) -> bool:
    if not title:
        return False
    upper = title.upper()
    return any(phrase in upper for phrase in SHARED_EMPLOYEE_TITLE_PHRASES)


# ---------------------------------------------------------------------------
# Observations
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Observation:
    lane: str
    chamber: str
    period: str
    office_raw: str
    office_key: str
    container_kind: str
    payee_raw: str
    payee_key: tuple[str, str, str | None]
    title: str | None
    amount: float | None
    row_id: str
    shared_employee: bool
    ledger_office_key: str | None
    ledger_container_kind: str | None
    ledger_member_bioguide: str | None
    # ``source_form`` is the ledger's own era marker (detail_csv or
    # house_gov_single_volume_pdf).  It is counted in the receipt and never
    # emitted on a row: an era is a property of the source file, not of the
    # person.  ``source_candidate_id`` is the id the PDF-era candidate file gave
    # the row, carried through the ledger in ``source_locator.candidate_id``; it
    # is what the H1 LDA match lane keys on, and it is the reason dropping the
    # separate PDF lane costs that lane nothing.
    source_form: str | None = None
    source_candidate_id: str | None = None
    # Official House rows carry inclusive printed service dates.  Retaining
    # them here prevents a same-quarter office move from being misclassified as
    # simultaneous employment.  Senate rows remain report-period bounded.
    service_start: date | None = None
    service_end: date | None = None


def _source_candidate_id(row: Mapping[str, Any]) -> str | None:
    locator = row.get("source_locator")
    if isinstance(locator, Mapping):
        value = locator.get("candidate_id")
        if isinstance(value, str) and value:
            return value
    return None


def _house_observation(
    row: Mapping[str, Any], lane: str, row_id: str, house_key: "HouseOfficeKey"
) -> Observation | None:
    office_raw = str(
        row.get("office_raw") or row.get("employing_office_raw") or ""
    ).strip()
    payee_raw = str(row.get("payee_raw") or row.get("payee_name_raw") or "").strip()
    if not office_raw or not payee_raw:
        return None
    token = row.get("quarter") or row.get("period")
    key = quarter_from_token(token if isinstance(token, str) else None)
    if key is None:
        anchor = (
            parse_iso(row.get("period_start"))
            or parse_iso(row.get("service_start"))
            or parse_iso(row.get("service_start_date_candidate_iso"))
        )
        if anchor is None:
            return None
        key = quarter_from_date(anchor)
    payee_key = payroll_payee_key(payee_raw)
    if payee_key is None:
        return None
    title = clean_title(row.get("title_raw") or row.get("title_description_raw"))
    return Observation(
        lane=lane,
        chamber=CHAMBER_HOUSE,
        period=quarter_token(key),
        office_raw=office_raw,
        office_key=house_key(office_raw),
        container_kind=container_kind_house(office_raw),
        payee_raw=payee_raw,
        payee_key=payee_key,
        title=title,
        amount=parse_amount(row.get("amount") or row.get("amount_raw")),
        row_id=row_id,
        shared_employee=is_shared_employee(title),
        ledger_office_key=(
            str(row["office_key"]) if isinstance(row.get("office_key"), str) else None
        ),
        ledger_container_kind=(
            str(row["container_kind"])
            if isinstance(row.get("container_kind"), str)
            else None
        ),
        ledger_member_bioguide=(
            str(row["member_bioguide"])
            if isinstance(row.get("member_bioguide"), str)
            else None
        ),
        source_form=(
            str(row["source_form"]) if isinstance(row.get("source_form"), str) else None
        ),
        source_candidate_id=_source_candidate_id(row),
        service_start=(
            parse_iso(row.get("service_start"))
            or parse_iso(row.get("service_start_date_candidate_iso"))
        ),
        service_end=(
            parse_iso(row.get("service_end"))
            or parse_iso(row.get("service_end_date_candidate_iso"))
        ),
    )


def _senate_suppression_reason(row: Mapping[str, Any]) -> str:
    """Why ``_senate_observation`` returned None.  Reported, never repaired."""

    if not str(row.get("office_raw") or "").strip():
        return "OFFICE_STRING_EMPTY"
    payee_raw = str(row.get("payee_name_raw") or row.get("payee_raw") or "").strip()
    if not payee_raw:
        return "PAYEE_STRING_EMPTY"
    anchor = parse_iso(row.get("report_period_start"))
    if anchor is None:
        intervals = row.get("date_intervals")
        if isinstance(intervals, list):
            for interval in intervals:
                if isinstance(interval, Mapping):
                    anchor = parse_iso(interval.get("start"))
                    if anchor is not None:
                        break
    if anchor is None:
        return "NO_USABLE_REPORTING_PERIOD"
    return "PAYEE_STRING_YIELDS_NO_NAME_KEY"


def _senate_observation(row: Mapping[str, Any], row_id: str) -> Observation | None:
    office_raw = str(row.get("office_raw") or "").strip()
    payee_raw = str(row.get("payee_name_raw") or row.get("payee_raw") or "").strip()
    if not office_raw or not payee_raw:
        return None
    anchor = parse_iso(row.get("report_period_start"))
    if anchor is None:
        intervals = row.get("date_intervals")
        if isinstance(intervals, list):
            for interval in intervals:
                if isinstance(interval, Mapping):
                    anchor = parse_iso(interval.get("start"))
                    if anchor is not None:
                        break
    if anchor is None:
        return None
    payee_key = payroll_payee_key(payee_raw)
    if payee_key is None:
        return None
    title = clean_title(row.get("title_raw") or row.get("title_candidate"))
    window_start, _ = senate_window(anchor)
    return Observation(
        lane=LANE_SENATE,
        chamber=CHAMBER_SENATE,
        period=window_start.isoformat(),
        office_raw=office_raw,
        office_key=senate_office_key(office_raw),
        container_kind=container_kind_senate(office_raw),
        payee_raw=payee_raw,
        payee_key=payee_key,
        title=title,
        amount=parse_amount(row.get("amount_paid_raw") or row.get("amount")),
        row_id=row_id,
        shared_employee=is_shared_employee(title),
        ledger_office_key=None,
        ledger_container_kind=None,
        ledger_member_bioguide=None,
    )


def _ledger_row_id(row: Mapping[str, Any], ordinal: int) -> str:
    source_file = row.get("source_file")
    row_index = row.get("source_row_index")
    if isinstance(source_file, str) and source_file and row_index is not None:
        return f"house-ledger:{source_file}#{row_index}"
    for field in ("observation_id", "candidate_id", "row_id"):
        value = row.get(field)
        if isinstance(value, str) and value:
            return value
    return f"house-ledger:ordinal:{ordinal}"


# ---------------------------------------------------------------------------
# Office span nodes and identity clustering
# ---------------------------------------------------------------------------
@dataclass
class OfficeNode:
    chamber: str
    office_key: str
    payee_key: tuple[str, str, str | None]
    observations: list[Observation]

    @property
    def period_tokens(self) -> set[str]:
        return {observation.period for observation in self.observations}

    @property
    def ordinals(self) -> set[int]:
        return {
            period_ordinal(self.chamber, observation.period)
            for observation in self.observations
        }

    @property
    def shared_periods(self) -> set[str]:
        return {
            observation.period
            for observation in self.observations
            if observation.shared_employee
        }

    @property
    def first_period(self) -> str:
        return period_token_from_ordinal(self.chamber, min(self.ordinals))

    @property
    def last_period(self) -> str:
        return period_token_from_ordinal(self.chamber, max(self.ordinals))

    @property
    def sort_key(self) -> tuple[int, int, str]:
        return (min(self.ordinals), max(self.ordinals), self.office_key)

    @property
    def has_complete_service_dates(self) -> bool:
        return bool(self.observations) and all(
            observation.service_start is not None
            and observation.service_end is not None
            and observation.service_start <= observation.service_end
            for observation in self.observations
        )

    @property
    def service_intervals(self) -> list[tuple[date, date]]:
        if not self.has_complete_service_dates:
            return []
        return [
            (observation.service_start, observation.service_end)
            for observation in self.observations
            if observation.service_start is not None and observation.service_end is not None
        ]


def nodes_linkable(left: OfficeNode, right: OfficeNode) -> tuple[bool, str | None]:
    """Return ``(linkable, exemption_method)`` for two office spans."""

    shared = left.period_tokens & right.period_tokens
    if not shared:
        return True, None
    if (
        left.chamber == CHAMBER_HOUSE
        and right.chamber == CHAMBER_HOUSE
        and left.has_complete_service_dates
        and right.has_complete_service_dates
    ):
        overlaps = any(
            left_start <= right_end and right_start <= left_end
            for left_start, left_end in left.service_intervals
            for right_start, right_end in right.service_intervals
        )
        if not overlaps:
            return True, "DAY_LEVEL_NONOVERLAP"
    left_shared = left.shared_periods
    right_shared = right.shared_periods
    if all(period in left_shared or period in right_shared for period in shared):
        return True, "SHARED_EMPLOYEE"
    return False, None


def cluster_nodes(
    nodes: Sequence[OfficeNode],
) -> tuple[list[list[OfficeNode]], int, int, int]:
    """Greedy clique clustering in period order.

    A node joins the first cluster it is linkable with against every existing
    member, so a cluster is a clique and transitivity can never merge two spans
    that co-occur in one period.  Returns the clusters plus the number of
    shared-employee exemptions used and the number of same-period splits.
    """

    ordered = sorted(nodes, key=lambda node: node.sort_key)
    clusters: list[list[OfficeNode]] = []
    shared_links = 0
    day_nonoverlap_links = 0
    splits = 0
    for node in ordered:
        placed = False
        for cluster in clusters:
            decisions = [nodes_linkable(member, node) for member in cluster]
            if all(linkable for linkable, _ in decisions):
                cluster.append(node)
                shared_links += sum(
                    1 for _, method in decisions if method == "SHARED_EMPLOYEE"
                )
                day_nonoverlap_links += sum(
                    1 for _, method in decisions if method == "DAY_LEVEL_NONOVERLAP"
                )
                placed = True
                break
            splits += sum(1 for linkable, _ in decisions if not linkable)
        if not placed:
            clusters.append([node])
    return clusters, shared_links, day_nonoverlap_links, splits


def spine_person_id(
    payee_key: tuple[str, str, str | None], nodes: Sequence[OfficeNode]
) -> str:
    anchor = min(
        nodes,
        key=lambda node: (
            period_bounds(node.chamber, node.first_period)[0].toordinal(),
            node.chamber,
            node.office_key,
        ),
    )
    digest = digest_of(
        {
            "chamber": anchor.chamber,
            "first_office_key": anchor.office_key,
            "first_period": anchor.first_period,
            "payee_key": [payee_key[0], payee_key[1], payee_key[2]],
        }
    )
    return f"hill:person:{digest}"


# ---------------------------------------------------------------------------
# Name standard re-key (--name-standard).  Everything below is reached only
# when the flag is on; nothing above it changes.
# ---------------------------------------------------------------------------
_NAME_STANDARD_MODULE: list[Any] = []


def load_name_standard() -> Any:
    """Load ``fec/staffer_network/name_standard.py`` by path, once.

    By path rather than by import name so that this module keeps working from
    any working directory and so that the default mode never touches it.
    """

    if _NAME_STANDARD_MODULE:
        return _NAME_STANDARD_MODULE[0]
    path = REPO_ROOT.joinpath(*NAME_STANDARD_MODULE_RELATIVE)
    if not path.is_file():
        raise GateFailure(f"--name-standard needs the name standard: {path}")
    spec = importlib.util.spec_from_file_location("hill_spine_name_standard", path)
    if spec is None or spec.loader is None:
        raise GateFailure(f"--name-standard could not load the name standard: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["hill_spine_name_standard"] = module
    spec.loader.exec_module(module)
    _NAME_STANDARD_MODULE.append(module)
    return module


def name_standard_source(chamber: str, payee_raw: str) -> str:
    """Which of the standard's four sources reads this payee string.

    The Senate lane gets "senate", which handles the SENATOR and INTERN
    COMPENSATION forms and falls through to the comma rule for everything else.
    The House lane gets the branch ``payroll_payee_key`` itself takes: the comma
    rule when the ascii-folded, date-hint-stripped string carries a comma and
    the House SOD CSV rule when it does not.
    """

    if chamber == CHAMBER_SENATE:
        return "senate"
    text = DATE_HINT_RE.sub(" ", _ascii_fold(payee_raw))
    return "payroll_comma" if "," in text else "house_csv"


def anchor_node(nodes: Sequence[OfficeNode]) -> OfficeNode:
    """The office node a person's id is digested over.

    The same minimum ``spine_person_id`` takes -- (period start ordinal,
    chamber, office key) -- with the payee key appended as a total-order
    tiebreak.  Every node the office grouping gives one person carries that
    person's single payee key, so the tiebreak is constant there and cannot
    change the answer.  It is reachable only after a name-standard merge, where
    one person's nodes come from two payee keys and two of them can share an
    office key; the three digested fields are equal across such a tie by
    construction of the merge, so the id does not depend on the tiebreak either.
    Only the raw payee string quoted on the row does, and that must not depend
    on iteration order.
    """

    return min(
        nodes,
        key=lambda node: (
            period_bounds(node.chamber, node.first_period)[0].toordinal(),
            node.chamber,
            node.office_key,
            payee_sort_key(node.payee_key),
        ),
    )


def name_standard_id_tuple(
    name_key_value: str, nodes: Sequence[OfficeNode], collision_ordinal: int
) -> dict[str, Any]:
    """THE hashed tuple, in this exact order and shape.

    ``collision_ordinal`` is 1 for everybody the merge guard did not have to
    separate, which is all but a handful of people; it is 2, 3, ... only where
    ruling C BLOCKED a merge and two people who share the anchor and the name
    key have to stay apart.  It is in the tuple for every row rather than only
    for those, so that the id is reconstructible from fields the spine row
    itself carries, with no case analysis and no lookup.
    """

    anchor = anchor_node(nodes)
    return {
        "chamber": anchor.chamber,
        "collision_ordinal": collision_ordinal,
        "first_office_key": anchor.office_key,
        "first_period": anchor.first_period,
        "name_key": name_key_value,
    }


def name_standard_spine_person_id(
    name_key_value: str, nodes: Sequence[OfficeNode], collision_ordinal: int = 1
) -> str:
    """The re-keyed person id: sha256 over :func:`name_standard_id_tuple`."""

    digest = digest_of(
        name_standard_id_tuple(name_key_value, nodes, collision_ordinal)
    )
    return f"hill:person:{digest}"


def same_office_period_relation(
    left: Sequence[OfficeNode], right: Sequence[OfficeNode]
) -> str:
    """Ruling C (D-020) -- may these two people be one person?

    Returns one of four values, most restrictive first:

      ``day_level_service_overlap``          BLOCKS the merge.  Somewhere the
          two carry distinct payee lines in the SAME office and the SAME
          report period, and both sides print inclusive service dates that
          overlap at DAY level.  Two people were in that office on the same
          day under two spellings, so they are two people.
      ``same_period_variant_no_day_dates``   Same office, same report period,
          but at least one side prints no usable service dates -- every Senate
          report period, and any House row whose dates are missing.  Missing dates BLOCK the merge: a reporting window cannot establish
          that two distinct payee lines represent the same person.
      ``same_period_day_level_disjoint``     Same office, same report period,
          both sides dated, and the calendars do not touch.  A within-quarter
          move, which is one person, not two.
      ``no_same_period_office_co_occurrence`` The two were never in one office
          in one report period at all.  Nothing to adjudicate.

    The day-level test is the same arithmetic :func:`nodes_linkable` already
    applies inside one payee key; ruling C applies it ACROSS payee keys.
    """

    relation = "no_same_period_office_co_occurrence"
    for left_node in left:
        for right_node in right:
            if left_node.chamber != right_node.chamber:
                continue
            if left_node.office_key != right_node.office_key:
                continue
            if not (left_node.period_tokens & right_node.period_tokens):
                continue
            if not (
                left_node.has_complete_service_dates
                and right_node.has_complete_service_dates
            ):
                relation = "same_period_variant_no_day_dates"
                continue
            overlaps = any(
                left_start <= right_end and right_start <= left_end
                for left_start, left_end in left_node.service_intervals
                for right_start, right_end in right_node.service_intervals
            )
            if overlaps:
                return "day_level_service_overlap"
            if relation == "no_same_period_office_co_occurrence":
                relation = "same_period_day_level_disjoint"
    return relation


#: Which basis a merge GROUP reports when its pairs disagree: the weakest
#: ground the group stands on, which is the one a reader must be told about.
NAME_STANDARD_MERGE_BASIS_ORDER = (
    "same_period_variant_no_day_dates",
    "same_period_day_level_disjoint",
    "no_same_period_office_co_occurrence",
)


def union_office_nodes(
    nodes: Sequence[OfficeNode],
) -> list[tuple[OfficeNode, list[tuple[str, str, str | None]]]]:
    """Collapse a person's office nodes into the SPAN rows they emit.

    Ruling C: after a merge, two of a person's nodes can be the same office
    under two spellings.  Where their reporting windows overlap or ABUT they
    are one continuous stretch of service in one office and must be ONE span
    row; where a real gap separates them they stay two, exactly as a single
    speller's gapped service already does.

    Returns ``(node, payee_keys)`` pairs: the node carrying the union of the
    observations, and every payee key that fed it, so the LDA and Quorum name
    joins keep resolving on BOTH spellings.

    Outside a merge this is the identity function and provably so: the office
    grouping keys on (chamber, office key, payee key) and a person who was not
    merged carries exactly one payee key, so no two of that person's nodes can
    share an office.  A default-mode build therefore emits the same spans it
    emitted before this function existed.
    """

    buckets: dict[tuple[str, str], list[OfficeNode]] = {}
    order: list[tuple[str, str]] = []
    for node in nodes:
        office = (node.chamber, node.office_key)
        if office not in buckets:
            buckets[office] = []
            order.append(office)
        buckets[office].append(node)

    def collapse(
        office: tuple[str, str], run: list[OfficeNode]
    ) -> tuple[OfficeNode, list[tuple[str, str, str | None]]]:
        payee_keys = sorted({node.payee_key for node in run}, key=payee_sort_key)
        if len(run) == 1:
            return run[0], payee_keys
        chamber, office_key = office
        observations = sorted(
            [item for node in run for item in node.observations],
            key=lambda item: (period_ordinal(chamber, item.period), item.row_id),
        )
        merged = OfficeNode(
            chamber=chamber,
            office_key=office_key,
            payee_key=payee_keys[0],
            observations=observations,
        )
        return merged, payee_keys

    out: list[tuple[OfficeNode, list[tuple[str, str, str | None]]]] = []
    for office in order:
        members = sorted(
            buckets[office],
            key=lambda node: (
                min(node.ordinals),
                max(node.ordinals),
                payee_sort_key(node.payee_key),
            ),
        )
        run: list[OfficeNode] = []
        run_end = 0
        for node in members:
            start, end = min(node.ordinals), max(node.ordinals)
            if run and start <= run_end + 1:
                run.append(node)
                run_end = max(run_end, end)
                continue
            if run:
                out.append(collapse(office, run))
            run = [node]
            run_end = end
        if run:
            out.append(collapse(office, run))
    return out


#: The four causes that exist ONLY because the raw parse and the payee-key
#: lift read the same person differently.  Under ruling A the raw parse IS the
#: key source, so these are no longer a gate -- they are the histogram that
#: says how far the two routes are apart, reported by cause and never fatal.
NAME_STANDARD_KEY_SOURCE_CAUSES = (
    "v_initial",
    "particle_surname",
    "annotation_strip",
    "first_from_raw",
)

#: The single-cause reasons the id map may carry, in the order the tests fire.
NAME_STANDARD_CAUSE_ORDER = (
    "ascii_punct",
    "suffix",
    "nickname_class",
    "v_initial",
    "particle_surname",
    "annotation_strip",
    "first_from_raw",
    "other",
)


def name_standard_resolve_key(counts: Mapping[str, int]) -> str:
    """THE ruled resolution rule, byte for byte the read-only delta's.

    Given every v1.1 key a population was recorded under, with how often each
    was recorded: prefer a key carrying a NON-EMPTY MIDDLE INITIAL (a middle
    initial present in one recording is evidence; its absence in another is
    silence), then the most frequently recorded, then the lexicographic
    minimum so the answer never depends on iteration order.
    """

    return min(
        counts,
        key=lambda key: (key.split("|")[2] == "", -counts[key], key),
    )


def name_standard_key_causes(
    payee_key: tuple[str, str, str | None],
    key_after: str,
    standard: Any,
    table: Mapping[str, str],
) -> tuple[list[str], str, str]:
    """Why this person's key moves, in the read-only delta's own vocabulary.

    Returns ``(causes, key_before, key_lift)``.  ``key_after`` is the RAW-PARSE
    key the caller resolved -- under ruling A that is the key, and this
    function only explains the distance from ``key_before`` to it.  The tests
    fire in the delta's order and a row can carry more than one:

      ``ascii_punct``       the fold to [a-z0-9] alone moves the key;
      ``suffix``            lifting a separator-delimited suffix out of the
                            surname moves it further;
      ``nickname_class``    folding the given name onto its class stem moves it
                            further still;
      ``v_initial``         R1 -- a bare V the builder's own tokeniser deleted
                            as a Roman numeral is a middle initial in the raw;
      ``particle_surname``  R2 -- a ruled particle joins the surname, so last
                            grows and first/middle shift;
      ``annotation_strip``  R3 -- a glued job title leaves the surname, or a
                            trailing party word stops supplying a phantom
                            middle initial;
      ``first_from_raw``    the raw parse reads a different given name than the
                            stored triple;
      ``other``             the key moved and none of the above explains it,
                            which is reported rather than hidden.

    The first three are functions of the TRIPLE and were all v1.0 could see.
    The next four are functions of the RAW STRING and are exactly the reason
    the key source had to move: ``payroll_payee_key`` deletes the V, splits the
    particle surname and absorbs the annotation before the triple exists, so no
    function of the triple can express them.
    """

    last, first, middle = payee_key[0], payee_key[1], payee_key[2] or ""
    key_before = "%s|%s|%s" % (last, first, middle)
    lift = standard.parts_from_payee_key(last, first, middle)
    key_fold_only = "%s|%s|%s" % (
        standard.fold_key(last),
        standard.fold_key(first),
        standard.fold_key(middle)[:1],
    )
    key_no_nickname = standard.name_key(lift, nicknames=False, table=table)
    key_lift = standard.name_key(lift, nicknames=True, table=table)
    causes: list[str] = []
    if key_fold_only != key_before:
        causes.append("ascii_punct")
    if key_no_nickname != key_fold_only:
        causes.append("suffix")
    if key_lift != key_no_nickname:
        causes.append("nickname_class")
    after_last, after_first, after_middle = key_after.split("|")
    lift_last, lift_first, lift_middle = key_lift.split("|")
    if after_middle == "v" and lift_middle != "v":
        causes.append("v_initial")
    if after_last != lift_last:
        causes.append(
            "particle_surname"
            if after_last.startswith(lift_last)
            else "annotation_strip"
        )
    elif after_middle != lift_middle and not (
        after_middle == "v" and lift_middle != "v"
    ):
        causes.append("annotation_strip")
    if after_first != lift_first:
        causes.append("first_from_raw")
    if key_after != key_before and not causes:
        causes.append("other")
    return causes, key_before, key_lift


#: The id map's ``reason`` vocabulary, derived from the cause flags above.  A
#: merged id reports "merged" whatever moved its key, because the merge is the
#: fact a reader of the map needs first; the exact flags stay on the row in
#: ``causes`` so nothing is lost.  "both" and the "suffix"-wins precedence are
#: the previous generation's names for their combinations and are kept
#: unchanged; every combination the four NEW causes create is the flags joined
#: with "+", in the order they fired, so a reader of the histogram never has to
#: guess what a bucket contains.
def name_standard_reason(causes: Sequence[str], merged: bool) -> str:
    if merged:
        return "merged"
    if not causes:
        return "unchanged"
    flags = list(causes)
    if len(flags) == 1:
        return flags[0]
    if set(flags) == {"ascii_punct", "nickname_class"}:
        return "both"
    if "suffix" in flags:
        return "suffix"
    return "+".join(flags)


def prepare_name_standard(
    people: Sequence[dict[str, Any]], standard: Any, table: Mapping[str, str]
) -> dict[str, Any]:
    """Re-key ``people`` under the standard and return the merged population.

    Reads the office nodes the identity rules already produced and writes
    nothing back into them.  The returned ``people`` list is the same population
    with the merge groups collapsed, each entry carrying
    ``spine_person_id_override`` so the emit loop below uses the new id without
    any other change to it.
    """

    parse_cache: dict[tuple[str, str], Any] = {}

    def parsed(chamber: str, raw: str) -> Any:
        source = name_standard_source(chamber, raw)
        cache_key = (source, raw)
        found = parse_cache.get(cache_key)
        if found is None:
            found = standard.parse_name(raw, source)
            parse_cache[cache_key] = found
        return found

    def key_of(chamber: str, raw: str) -> str:
        return standard.name_key(parsed(chamber, raw), table=table)

    def raw_key_counts(
        nodes: Sequence[OfficeNode],
    ) -> tuple[Counter, dict[tuple[str, str], int]]:
        """``(key -> observations, (chamber, raw) -> observations)``."""

        keys: Counter = Counter()
        raws: Counter = Counter()
        for node in nodes:
            for observation in node.observations:
                keys[key_of(node.chamber, observation.payee_raw)] += 1
                raws[(node.chamber, observation.payee_raw)] += 1
        return keys, raws

    def choose_raw(
        raws: Mapping[tuple[str, str], int], key_after: str
    ) -> tuple[str, str] | None:
        """The one raw string this person is named from, deterministically.

        Ruling A: among the raws that produce the resolved key, the most
        frequently recorded, then the lexicographic minimum.  Returns None when
        no raw produces the key, which a merge cannot cause -- every member of
        a merge group resolved to the group's key from its OWN raws -- and
        which is therefore counted rather than assumed impossible.
        """

        matching = [pair for pair in raws if key_of(pair[0], pair[1]) == key_after]
        if not matching:
            return None
        return min(matching, key=lambda pair: (-raws[pair], pair[1], pair[0]))

    def person_name(nodes: Sequence[OfficeNode], key_after: str) -> dict[str, Any]:
        _keys, raws = raw_key_counts(nodes)
        chosen = choose_raw(raws, key_after)
        fell_back = chosen is None
        if chosen is None:
            anchor = anchor_node(nodes)
            chosen = (anchor.chamber, anchor.observations[0].payee_raw)
        raw_pairs = sorted(raws)
        suffixes = sorted(
            {
                found.suffix
                for chamber, raw in raw_pairs
                for found in (parsed(chamber, raw),)
                if found.suffix
            }
        )
        raw_examples = sorted({raw for _chamber, raw in raw_pairs})
        return {
            "chosen_parts": parsed(chosen[0], chosen[1]),
            "chosen_raw": chosen[1],
            "chosen_raw_fell_back_to_the_anchor": fell_back,
            "raw_example_count": len(raw_examples),
            "raw_examples": raw_examples[:NAME_STANDARD_MAX_RAW_EXAMPLES],
            "suffix_observed": suffixes,
            "suffix": suffixes[0] if len(suffixes) == 1 else None,
        }

    # ---- pass 1: the delta's own reconstruction, per payee-key TRIPLE ------
    # The read-only re-key delta resolved ONE key per triple over every row of
    # the three payroll corpora.  This build resolves per PERSON over that
    # person's own rows, which is the ruled rule and the more specific
    # evidence.  The two answers can only differ on a triple whose raws
    # disagree, so the triple-level answer is computed here as well and every
    # person where the two disagree is listed as a delta residual.  Nothing is
    # kept per person in this pass: only the triple table survives it.
    triple_keys: dict[tuple[str, str, str | None], Counter] = {}
    for person in people:
        by_key = triple_keys.setdefault(person["payee_key"], Counter())
        for node in person["nodes"]:
            for observation in node.observations:
                by_key[key_of(node.chamber, observation.payee_raw)] += 1
    triple_resolved = {
        triple: name_standard_resolve_key(counts)
        for triple, counts in triple_keys.items()
    }
    ambiguous_triples = {
        triple for triple, counts in triple_keys.items() if len(counts) > 1
    }
    del triple_keys

    key_source_disagreement_examples: list[dict[str, Any]] = []
    key_source_disagreements: Counter = Counter()
    key_source_disagreement_people = 0
    suffix_rows_from_payee_key_lift = 0
    cause_counts: Counter = Counter()
    combination_counts: Counter = Counter()
    delta_cause_counts: Counter = Counter()
    delta_residuals: list[dict[str, Any]] = []
    people_on_an_ambiguous_triple = 0
    nickname_transitions: Counter = Counter()
    records: list[dict[str, Any]] = []
    for person in people:
        payee_key = person["payee_key"]
        nodes = person["nodes"]
        legacy_id = spine_person_id(payee_key, nodes)
        keys, raws = raw_key_counts(nodes)
        key_after = name_standard_resolve_key(keys)
        causes, key_before, key_lift = name_standard_key_causes(
            payee_key, key_after, standard, table
        )
        if standard.parts_from_payee_key(
            payee_key[0], payee_key[1], payee_key[2] or ""
        ).suffix:
            suffix_rows_from_payee_key_lift += 1
        if payee_key in ambiguous_triples:
            people_on_an_ambiguous_triple += 1
        # ---- ruling B: the delta invariant, measured not assumed ----------
        delta_key = triple_resolved[payee_key]
        delta_causes, _before, _lift = name_standard_key_causes(
            payee_key, delta_key, standard, table
        )
        for cause in delta_causes:
            delta_cause_counts[cause] += 1
        if delta_key != key_after and len(delta_residuals) < 400:
            delta_residuals.append(
                {
                    "key_from_the_delta_reconstruction": delta_key,
                    "key_from_this_build": key_after,
                    "payee_raw_examples": sorted({raw for _c, raw in raws})[
                        :NAME_STANDARD_MAX_RAW_EXAMPLES
                    ],
                    "spine_person_id_legacy": legacy_id,
                }
            )
        elif delta_key != key_after:
            delta_residuals.append({"spine_person_id_legacy": legacy_id})
        # ---- ruling A: the two key routes, reported, never fatal ----------
        if key_after != key_lift:
            key_source_disagreement_people += 1
            named = [
                cause for cause in causes if cause in NAME_STANDARD_KEY_SOURCE_CAUSES
            ]
            for cause in named or ["other"]:
                key_source_disagreements[cause] += 1
            if len(key_source_disagreement_examples) < 40:
                chosen = choose_raw(raws, key_after)
                key_source_disagreement_examples.append(
                    {
                        "causes": named,
                        "key_from_payee_key_lift": key_lift,
                        "key_from_raw_parse": key_after,
                        "payee_raw": chosen[1] if chosen else "",
                        "spine_person_id_legacy": legacy_id,
                    }
                )
        if causes:
            for cause in causes:
                cause_counts[cause] += 1
            combination_counts["+".join(causes)] += 1
            if "nickname_class" in causes:
                nickname_transitions[
                    (
                        standard.fold_key(payee_key[1]),
                        standard.canonical_first(payee_key[1], table),
                    )
                ] += 1
        records.append(
            {
                "causes": causes,
                "key_after": key_after,
                "key_before": key_before,
                "key_lift": key_lift,
                "legacy_person_id": legacy_id,
                "person": person,
            }
        )
    del triple_resolved
    del ambiguous_triples

    # ---- ruling C: the merge guard, at DAY level ---------------------------
    # Group first on the tuple the id is digested over MINUS the ordinal, then
    # split each group into sub-groups no two of whose members co-occupy an
    # office in a report period at day level.  A member joins the first
    # sub-group it does not collide with against EVERY member already there,
    # so a sub-group is a clique and no blocked pair can ever be merged by
    # transitivity -- the same discipline cluster_nodes applies to office
    # nodes.  The ordinal then separates the sub-groups inside the hash.
    # The bucket is the hashed id tuple MINUS the ordinal -- (chamber,
    # first_office_key, first_period, name_key) -- so two records land in one
    # bucket exactly when the ordinal is the only thing that can tell their
    # ids apart.  The verifier buckets on the same four fields in the same
    # order.
    buckets: dict[tuple[str, str, str, str], list[dict[str, Any]]] = {}
    bucket_order: list[tuple[str, str, str, str]] = []
    for record in records:
        anchor = anchor_node(record["person"]["nodes"])
        bucket = (
            anchor.chamber,
            anchor.office_key,
            anchor.first_period,
            record["key_after"],
        )
        if bucket not in buckets:
            buckets[bucket] = []
            bucket_order.append(bucket)
        buckets[bucket].append(record)

    grouped: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    merges_blocked: list[dict[str, Any]] = []
    merge_basis_by_id: dict[str, str] = {}
    collision_ordinal_by_id: dict[str, int] = {}
    blocked_pairs = 0
    for bucket in bucket_order:
        members = sorted(buckets[bucket], key=lambda item: item["legacy_person_id"])
        subgroups: list[list[dict[str, Any]]] = []
        bases: list[list[str]] = []
        for member in members:
            placed = False
            for index, subgroup in enumerate(subgroups):
                relations = [
                    same_office_period_relation(
                        sibling["person"]["nodes"], member["person"]["nodes"]
                    )
                    for sibling in subgroup
                ]
                if any(relation in {"day_level_service_overlap", "same_period_variant_no_day_dates"} for relation in relations):
                    blocked_pairs += sum(
                        1
                        for relation in relations
                        if relation in {"day_level_service_overlap", "same_period_variant_no_day_dates"}
                    )
                    for sibling, relation in zip(subgroup, relations):
                        if relation not in {"day_level_service_overlap", "same_period_variant_no_day_dates"}:
                            continue
                        if len(merges_blocked) < 200:
                            merges_blocked.append(
                                {
                                    "basis": relation,
                                    "chamber": bucket[0],
                                    "first_office_key": bucket[1],
                                    "first_period": bucket[2],
                                    "name_key": bucket[3],
                                    "pair": [
                                        sibling["legacy_person_id"],
                                        member["legacy_person_id"],
                                    ],
                                }
                            )
                    continue
                subgroups[index].append(member)
                bases[index].extend(relations)
                placed = True
                break
            if not placed:
                subgroups.append([member])
                bases.append([])
        for ordinal, (subgroup, relations) in enumerate(zip(subgroups, bases), start=1):
            new_id = name_standard_spine_person_id(
                bucket[3], subgroup[0]["person"]["nodes"], ordinal
            )
            grouped[new_id] = subgroup
            order.append(new_id)
            collision_ordinal_by_id[new_id] = ordinal
            for record in subgroup:
                record["spine_person_id"] = new_id
            if len(subgroup) > 1:
                merge_basis_by_id[new_id] = min(
                    relations,
                    key=lambda relation: NAME_STANDARD_MERGE_BASIS_ORDER.index(relation),
                )

    merged_people: list[dict[str, Any]] = []
    by_person_id: dict[str, dict[str, Any]] = {}
    merge_groups: list[dict[str, Any]] = []
    anchor_moved = 0
    empty_first_class: list[dict[str, Any]] = []
    chosen_raw_fell_back = 0
    for new_id in order:
        members = sorted(grouped[new_id], key=lambda item: item["legacy_person_id"])
        ordinal = collision_ordinal_by_id[new_id]
        nodes: list[OfficeNode] = []
        for member in members:
            nodes.extend(member["person"]["nodes"])
        nodes.sort(key=lambda node: (node.sort_key, payee_sort_key(node.payee_key)))
        key_after = members[0]["key_after"]
        if name_standard_spine_person_id(key_after, nodes, ordinal) != new_id:
            anchor_moved += 1
        payee_keys = sorted(
            {member["person"]["payee_key"] for member in members}, key=payee_sort_key
        )
        name = person_name(nodes, key_after)
        if name["chosen_raw_fell_back_to_the_anchor"]:
            chosen_raw_fell_back += 1
        lift = standard.parts_from_payee_key(
            payee_keys[0][0], payee_keys[0][1], payee_keys[0][2] or ""
        )
        first_class = standard.canonical_first(lift.first, table)
        if not first_class and len(empty_first_class) < 40:
            # Ruling E: an empty first_class is a name key with no given-name
            # component at all.  It is attributed here and it FAILS the build;
            # it must never be absorbed silently into a key.
            empty_first_class.append(
                {
                    "payee_key_first": lift.first,
                    "payee_raw": name["chosen_raw"],
                    "spine_person_id": new_id,
                }
            )
        elif not first_class:
            empty_first_class.append({"spine_person_id": new_id})
        render = standard.NameParts(
            first=name["chosen_parts"].first,
            middle=name["chosen_parts"].middle,
            last=name["chosen_parts"].last,
            suffix=name["suffix"] or "",
            nickname_raw=name["chosen_parts"].nickname_raw,
            format_detected=name["chosen_parts"].format_detected,
            raw=name["chosen_parts"].raw,
        )
        merged_people.append(
            {
                "collision_ordinal": ordinal,
                "cross_chamber": any(
                    member["person"].get("cross_chamber") for member in members
                ),
                "nodes": nodes,
                "payee_key": payee_keys[0],
                "spine_person_id_override": new_id,
            }
        )
        by_person_id[new_id] = {
            "collision_ordinal": ordinal,
            "display_name": standard.display_name(render),
            "legacy_person_ids": [member["legacy_person_id"] for member in members],
            "name_key": key_after,
            # ``raw`` is deliberately not carried through from ``as_dict``: the
            # row already carries the raw payee string in ``payee_raw`` and one
            # copy of a source string is enough.
            "name_standard_parts": {
                "first": render.first,
                "format_detected": render.format_detected,
                "last": render.last,
                "middle": render.middle,
                "nickname_raw": render.nickname_raw,
                "suffix": render.suffix,
            },
            "payee_key": {
                "first": lift.first,
                "first_class": first_class,
                "last": lift.last,
                "middle_initial": payee_keys[0][2],
                "suffix": name["suffix"],
            },
            "payee_key_legacy_variants": [
                {"first": item[1], "last": item[0], "middle_initial": item[2]}
                for item in payee_keys
            ],
            # Ruling A: the raw string this person is NAMED from, which is the
            # raw the key came from, not the anchor node's first observation.
            "payee_raw": name["chosen_raw"],
            "payee_raw_examples": name["raw_examples"],
            "payee_raw_variant_count": name["raw_example_count"],
            "suffix_observed": name["suffix_observed"],
        }
        if len(members) > 1:
            merge_groups.append(
                {
                    "keys_before": sorted({member["key_before"] for member in members}),
                    "merge_basis": merge_basis_by_id[new_id],
                    "name_key": key_after,
                    "spine_person_id": new_id,
                    "legacy_person_ids": [
                        member["legacy_person_id"] for member in members
                    ],
                }
            )

    id_map_rows: list[dict[str, Any]] = []
    for record in records:
        new_id = record["spine_person_id"]
        siblings = [
            member["legacy_person_id"]
            for member in sorted(
                grouped[new_id], key=lambda item: item["legacy_person_id"]
            )
            if member["legacy_person_id"] != record["legacy_person_id"]
        ]
        id_map_rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "causes": record["causes"],
                "collision_ordinal": collision_ordinal_by_id[new_id],
                "key_v6": record["key_before"],
                "key_v7": record["key_after"],
                "legacy_person_id": record["legacy_person_id"],
                "merge_basis": merge_basis_by_id.get(new_id),
                "merged_with": siblings,
                "person_id": new_id,
                "reason": name_standard_reason(record["causes"], bool(siblings)),
                "review_status": "REVIEW_REQUIRED",
                "schema_id": NAME_STANDARD_ID_MAP_SCHEMA,
            }
        )
    id_map_rows.sort(key=lambda row: row["legacy_person_id"])

    changed = sum(
        1 for record in records if record["key_after"] != record["key_before"]
    )
    return {
        "anchor_moved_under_merge": anchor_moved,
        "by_person_id": by_person_id,
        "cause_counts": dict(sorted(cause_counts.items())),
        "chosen_raw_fell_back_to_the_anchor": chosen_raw_fell_back,
        "collision_ordinals_above_one": sum(
            1 for value in collision_ordinal_by_id.values() if value > 1
        ),
        "combination_counts": dict(sorted(combination_counts.items())),
        # Ruling B.  ``delta_reconstruction_cause_counts`` is what the
        # read-only report measures: ONE key per payee-key triple over every
        # admitted row.  ``cause_counts`` is the ruled per-PERSON resolution.
        # The two can differ only on a person whose own raws resolve
        # differently from the triple's whole population, and every such
        # person is listed, so the difference is bounded and named rather
        # than asserted away.
        "delta_reconstruction_cause_counts": dict(sorted(delta_cause_counts.items())),
        "delta_residuals": delta_residuals,
        "delta_residuals_count": len(delta_residuals),
        "empty_first_class": empty_first_class,
        "empty_first_class_count": len(empty_first_class),
        "id_map_rows": id_map_rows,
        "key_source_disagreement_examples": key_source_disagreement_examples,
        "key_source_disagreement_people": key_source_disagreement_people,
        "key_source_disagreements": dict(sorted(key_source_disagreements.items())),
        "keys_changed": changed,
        "keys_unchanged": len(records) - changed,
        "merge_basis_counts": dict(
            sorted(Counter(merge_basis_by_id.values()).items())
        ),
        "merge_groups": merge_groups,
        "merges_blocked": merges_blocked,
        "merges_blocked_pairs": blocked_pairs,
        "people_on_an_ambiguous_triple": people_on_an_ambiguous_triple,
        # A LIST of objects, not a mapping keyed by the name pair: the language
        # law scans field NAMES as well as values, and a field name has no
        # verbatim-quoted exemption, so a person's name must never become one.
        "nickname_class_transitions": [
            {"first_class": stem, "first_folded": folded, "spine_rows": count}
            for (folded, stem), count in sorted(
                nickname_transitions.items(), key=lambda item: (-item[1], item[0])
            )
        ],
        "people": merged_people,
        "people_before": len(records),
        "reason_counts": dict(
            sorted(Counter(row["reason"] for row in id_map_rows).items())
        ),
        # Two suffix populations, and they are not the same number.  The first
        # is what the read-only re-key delta measured: a suffix still visible in
        # this module's own already-parsed triple, which is only ever a
        # hyphen-glued one because ``_name_tokens`` drops whole-token suffixes
        # before the surname is joined.  The second is what reading the RAW
        # payroll string recovers, which is the whole point of keeping the
        # suffix as a part.  Comparing either against the other is a category
        # error; both are reported.
        "rows_with_a_suffix_from_payee_key_lift": suffix_rows_from_payee_key_lift,
        "rows_with_a_suffix_from_raw_parse": sum(
            1
            for entry in by_person_id.values()
            if entry["name_standard_parts"]["suffix"]
        ),
        "rows_with_more_than_one_observed_suffix": sum(
            1
            for entry in by_person_id.values()
            if len(entry["suffix_observed"]) > 1
        ),
    }


# ---------------------------------------------------------------------------
# Loaders (all tolerant of a missing file)
# ---------------------------------------------------------------------------
def _bind_input(
    label: str, path: Path | None, block: dict[str, Any], count_rows: bool = True
) -> Path | None:
    if path is None:
        return None
    path = Path(path)
    if not path.is_file():
        block[label] = {
            "path": str(path),
            "present": False,
            "bytes": None,
            "rows": None,
            "sha256": None,
        }
        return None
    rows = None
    if count_rows and path.suffix.lower() in {".gz", ".ndjson"}:
        rows = sum(1 for _ in read_rows(path))
    block[label] = {
        "path": str(path),
        "present": True,
        "bytes": path.stat().st_size,
        "rows": rows,
        "sha256": sha(path),
    }
    return path


def load_match_lane(path: Path | None, key_field: str) -> list[dict[str, Any]]:
    if path is None:
        return []
    rows = []
    for row in read_rows(path):
        person = row.get("lda_source_person_id")
        key = row.get(key_field)
        if not isinstance(person, str) or not isinstance(key, str) or not key:
            continue
        rows.append(
            {
                "lda_source_person_id": person,
                "payroll_key": key,
                "display_name": (
                    row.get("display_name") or row.get("lda_display_name") or ""
                ),
                "office": (
                    row.get("employing_office_candidate")
                    or row.get("employing_office_raw")
                    or ""
                ),
                "payee_raw": row.get("payroll_payee_raw") or "",
            }
        )
    return rows


def load_part_a_tiers(sidecar_root: Path | None) -> dict[str, str]:
    if sidecar_root is None:
        return {}
    path = Path(sidecar_root) / "tiered_person_summary_25340.ndjson.gz"
    if not path.is_file():
        return {}
    tiers: dict[str, str] = {}
    for row in read_rows(path):
        person = row.get("lda_source_person_id")
        tier = row.get("max_tier")
        if isinstance(person, str) and isinstance(tier, str):
            tiers[person] = tier
    return tiers


def load_staff_directory(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not Path(path).is_file():
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return []
    entries = []
    for member_display in sorted(payload):
        staff = payload.get(member_display)
        if not isinstance(staff, list):
            continue
        for entry in staff:
            if not isinstance(entry, Mapping):
                continue
            staff_id = entry.get("id")
            name = entry.get("n")
            if not isinstance(staff_id, str) or not isinstance(name, str):
                continue
            if not staff_id.strip() or not name.strip():
                continue
            entries.append(
                {
                    "member_display": str(member_display),
                    "quorum_staff_id": staff_id.strip(),
                    "display_name": name.strip(),
                    "title_raw": clean_title(entry.get("t")),
                }
            )
    entries.sort(
        key=lambda item: (
            item["member_display"],
            item["display_name"],
            item["quorum_staff_id"],
        )
    )
    return entries


def load_member_display_index(path: Path | None) -> dict[str, str | None]:
    """display name -> bioguide, with collisions mapped to None."""

    if path is None or not Path(path).is_file():
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        return {}
    index: dict[str, str | None] = {}
    for bioguide in sorted(payload):
        entry = payload.get(bioguide)
        if not isinstance(entry, Mapping):
            continue
        name = entry.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        normalized = re.sub(r"\s+", " ", _ascii_fold(name)).strip().casefold()
        if normalized in index and index[normalized] != bioguide:
            index[normalized] = None
        else:
            index.setdefault(normalized, bioguide)
    return index


def load_registrant_people(path: Path | None) -> set[str]:
    if path is None:
        return set()
    people = set()
    for row in read_rows(path):
        person = row.get("lda_source_person_id")
        if isinstance(person, str):
            people.add(person)
    return people


# ---------------------------------------------------------------------------
# Language law + tripwire
# ---------------------------------------------------------------------------
def scan_language_law(
    payload: Any, extra_verbatim_leaf_names: Iterable[str] = ()
) -> tuple[list[str], Counter]:
    """Scan ``payload`` for banned tokens.

    ``extra_verbatim_leaf_names`` widens the verbatim-quoted exemption for one
    call only.  It is empty on every default-mode call site, so the default
    behaviour is byte for byte what it was; name-standard mode passes the extra
    name-bearing leaves it emits, which are enumerated in the receipt exactly as
    the standing ones are.
    """

    verbatim_leaf_names = VERBATIM_LEAF_NAMES | frozenset(extra_verbatim_leaf_names)
    authored: list[str] = []
    verbatim: Counter = Counter()

    def walk(node: Any, key: str | None, exempt: bool) -> None:
        if isinstance(node, Mapping):
            for child_key, child in node.items():
                lowered = str(child_key).casefold()
                for token in LANGUAGE_LAW_TOKENS:
                    if token in lowered:
                        authored.append(f"field_name:{child_key}:{token}")
                walk(
                    child,
                    str(child_key),
                    exempt or str(child_key) in verbatim_leaf_names,
                )
        elif isinstance(node, list):
            for child in node:
                walk(child, key, exempt)
        elif isinstance(node, str):
            lowered = node.casefold()
            for token in LANGUAGE_LAW_TOKENS:
                if token in lowered:
                    if exempt:
                        verbatim[f"{key}|{token}"] += 1
                    else:
                        authored.append(f"value:{key}:{token}")

    walk(payload, None, False)
    return authored, verbatim


def assert_unpromoted(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    """A5b-style anti-promotion tripwire, run over every row."""

    failures: list[str] = []
    for index, row in enumerate(rows):
        if row.get("review_status") != "REVIEW_REQUIRED":
            failures.append(f"row {index}: review_status is not REVIEW_REQUIRED")
        if row.get("canonical_eligible") is not False:
            failures.append(f"row {index}: canonical_eligible is not false")
        if row.get("canonical_employment_promoted") is not False:
            failures.append(f"row {index}: canonical_employment_promoted is not false")
        for key, value in row.items():
            lowered = key.lower()
            if (
                ("promoted" in lowered or "canonical" in lowered or "eligible" in lowered)
                and value not in (False, 0, None, "")
            ):
                failures.append(f"row {index}: promotion-shaped field {key} is truthy")
        if len(failures) > 50:
            failures.append("... truncated")
            break
    return failures


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def run(args: argparse.Namespace) -> dict[str, Any]:
    output_root = Path(args.output_root).resolve()
    if output_root.exists() and any(output_root.iterdir()):
        raise GateFailure(
            f"INV-2 immutable generation: refusing to write into non-empty {output_root}"
        )
    rule_version = args.rule_version
    generated_at = args.generated_at
    if generated_at is not None and not re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$",
        generated_at,
    ):
        raise GateFailure(f"--generated-at must be ISO-8601 with a timezone: {generated_at!r}")

    inputs: dict[str, Any] = {}
    ledger_root = Path(args.house_ledger_root) if args.house_ledger_root else None
    ledger_observations_path = None
    if ledger_root is not None:
        ledger_observations_path = _bind_input(
            "house_personnel_observations",
            ledger_root / "house_personnel_observations.ndjson.gz",
            inputs,
        )
        _bind_input(
            "house_person_office_spans",
            ledger_root / "house_person_office_spans.ndjson.gz",
            inputs,
        )
        _bind_input(
            "house_member_quarters",
            ledger_root / "house_member_quarters.ndjson.gz",
            inputs,
        )
        for candidate in sorted(ledger_root.glob("*receipt*.json")):
            _bind_input(f"house_ledger_receipt:{candidate.name}", candidate, inputs, False)

    # Personal-office and committee payrolls are separate official Senate
    # corpora.  Accept both without forcing a lossy pre-concatenation step.
    # Keep the historical single-Path Namespace shape working for callers and
    # tests that construct argparse namespaces directly.
    senate_args = args.senate_candidates
    if senate_args is None:
        senate_candidate_args: list[Path] = []
    elif isinstance(senate_args, (str, Path)):
        senate_candidate_args = [Path(senate_args)]
    else:
        senate_candidate_args = [Path(path) for path in senate_args]
    senate_paths: list[Path] = []
    for index, candidate_path in enumerate(senate_candidate_args, start=1):
        role = (
            "senate_payroll_candidates"
            if len(senate_candidate_args) == 1
            else f"senate_payroll_candidates_{index}"
        )
        bound = _bind_input(role, candidate_path, inputs)
        if bound is not None:
            senate_paths.append(bound)
    h1_path = _bind_input("h1_matches", args.h1_matches, inputs)
    h2_path = _bind_input("h2_matches", args.h2_matches, inputs)
    senate_match_path = _bind_input("senate_matches", args.senate_matches, inputs)
    staff_directory_path = _bind_input(
        "staff_directory", args.staff_directory, inputs, False
    )
    congestion_path = _bind_input("congestion", args.congestion, inputs, False)
    registrant_path = _bind_input("registrant_episodes", args.registrant_episodes, inputs)
    nickname_path = _bind_input("nickname_table", args.nickname_table, inputs, False)
    if args.roster_dir is not None:
        roster_dir = Path(args.roster_dir)
        for filename in ("legislators-current.yaml", "legislators-historical.yaml"):
            _bind_input(f"roster:{filename}", roster_dir / filename, inputs, False)
    else:
        roster_dir = None
    sidecar_root = Path(args.sidecar_root) if args.sidecar_root else None
    if sidecar_root is not None:
        for filename in (
            "tiered_person_office_records.ndjson.gz",
            "tiered_person_summary_25340.ndjson.gz",
            "registrant_side_records.ndjson.gz",
        ):
            _bind_input(f"part_a_v2:{filename}", sidecar_root / filename, inputs)
        _bind_input(
            "part_a_v2:tiered_corroboration_receipt.json",
            sidecar_root / "tiered_corroboration_receipt.json",
            inputs,
            False,
        )

    roster = load_roster(roster_dir)
    nicknames, nickname_table_loaded = load_nickname_table(nickname_path)

    # ---- name standard ----------------------------------------------------
    # Bound as inputs, and therefore hash-pinned in the receipt and re-checked
    # by the verifier, exactly like every other file this build reads.
    name_standard = bool(getattr(args, "name_standard", False))
    standard = None
    class_table: dict[str, str] = {}
    name_standard_failures: list[str] = []
    baseline_receipt_path: Path | None = None
    baseline_spine_path: Path | None = None
    delta_report_path: Path | None = None
    if name_standard:
        delta_report_path = _bind_input(
            "name_standard_delta_report",
            getattr(args, "name_standard_delta_report", None),
            inputs,
            False,
        )
        baseline_root = getattr(args, "name_standard_baseline", None)
        if baseline_root is not None:
            baseline_root = Path(baseline_root)
            baseline_receipt_path = _bind_input(
                "name_standard_baseline_receipt",
                baseline_root / RECEIPT_FILE,
                inputs,
                False,
            )
            baseline_spine_path = _bind_input(
                "name_standard_baseline_spine", baseline_root / SPINE_FILE, inputs
            )
            if baseline_receipt_path is None or baseline_spine_path is None:
                name_standard_failures.append("NAME_STANDARD_BASELINE_NOT_READABLE")
        standard = load_name_standard()
        _bind_input(
            "name_standard_module",
            REPO_ROOT.joinpath(*NAME_STANDARD_MODULE_RELATIVE),
            inputs,
            False,
        )
        _bind_input(
            "name_standard_class_table", standard.class_table_path(), inputs, False
        )
        class_table, class_table_loaded = standard.load_class_table()
        if not class_table_loaded:
            name_standard_failures.append("NAME_STANDARD_CLASS_TABLE_NOT_LOADED")

    # ---- R-1 member office key --------------------------------------------
    # One pre-pass over the House ledger builds the two member-office maps
    # before any observation is keyed, so that exactly one callable keys every
    # office string on both sides of every join.
    house_key, house_key_stats, house_key_failures = build_house_office_key(
        ledger_observations_path, roster, nicknames
    )

    # ---- observations -----------------------------------------------------
    rows_read: Counter = Counter()
    rows_admitted: Counter = Counter()
    rows_suppressed: Counter = Counter()
    observations: list[Observation] = []

    suppression_reasons: Counter = Counter()
    ledger_rows_read_by_form: Counter = Counter()
    ledger_rows_admitted_by_form: Counter = Counter()
    ledger_quarters_by_form: defaultdict[str, set[str]] = defaultdict(set)

    def _suppression_reason(row: Mapping[str, Any]) -> str:
        """Why ``_house_observation`` returned None.  Reported, never repaired.

        The reasons are exhaustive against that function's four early returns,
        in its own order, so a row is attributed to the first test it fails.
        """

        office_raw = str(
            row.get("office_raw") or row.get("employing_office_raw") or ""
        ).strip()
        if not office_raw:
            return "OFFICE_STRING_EMPTY"
        payee_raw = str(row.get("payee_raw") or row.get("payee_name_raw") or "").strip()
        if not payee_raw:
            return "PAYEE_STRING_EMPTY"
        token = row.get("quarter") or row.get("period")
        if quarter_from_token(token if isinstance(token, str) else None) is None and (
            parse_iso(row.get("period_start")) is None
            and parse_iso(row.get("service_start")) is None
            and parse_iso(row.get("service_start_date_candidate_iso")) is None
        ):
            return "NO_USABLE_REPORTING_PERIOD"
        return "PAYEE_STRING_YIELDS_NO_NAME_KEY"

    ledger_quarters: set[str] = set()
    if ledger_observations_path is not None:
        for ordinal, row in enumerate(read_rows(ledger_observations_path)):
            rows_read[LANE_HOUSE_LEDGER] += 1
            source_form = (
                str(row["source_form"])
                if isinstance(row.get("source_form"), str)
                else "unknown"
            )
            ledger_rows_read_by_form[source_form] += 1
            observation = _house_observation(
                row, LANE_HOUSE_LEDGER, _ledger_row_id(row, ordinal), house_key
            )
            if observation is None:
                rows_suppressed[LANE_HOUSE_LEDGER] += 1
                suppression_reasons[
                    f"{LANE_HOUSE_LEDGER}:{source_form}:{_suppression_reason(row)}"
                ] += 1
                continue
            ledger_quarters.add(observation.period)
            ledger_quarters_by_form[source_form].add(observation.period)
            ledger_rows_admitted_by_form[source_form] += 1
            observations.append(observation)
            rows_admitted[LANE_HOUSE_LEDGER] += 1

    for senate_path in senate_paths:
        for ordinal, row in enumerate(read_rows(senate_path)):
            rows_read[LANE_SENATE] += 1
            row_id = row.get("candidate_id")
            observation = _senate_observation(
                row,
                row_id if isinstance(row_id, str) and row_id
                else f"senate-payroll:{senate_path.name}:ordinal:{ordinal}",
            )
            if observation is None:
                rows_suppressed[LANE_SENATE] += 1
                suppression_reasons[
                    f"{LANE_SENATE}:{_senate_suppression_reason(row)}"
                ] += 1
                continue
            observations.append(observation)
            rows_admitted[LANE_SENATE] += 1

    failures: list[str] = list(house_key_failures) + name_standard_failures
    if not observations:
        failures.append("NO_PERSONNEL_SOURCE_PRESENT")

    latest_period: dict[str, str | None] = {CHAMBER_HOUSE: None, CHAMBER_SENATE: None}
    for chamber in (CHAMBER_HOUSE, CHAMBER_SENATE):
        chamber_ordinals = [
            period_ordinal(chamber, observation.period)
            for observation in observations
            if observation.chamber == chamber
        ]
        if chamber_ordinals:
            latest_period[chamber] = period_token_from_ordinal(
                chamber, max(chamber_ordinals)
            )

    # ---- office profiles --------------------------------------------------
    # container_kind and the strict-bioguide resolution are decided once per
    # (chamber, office_key) over that office's whole observed window, so a span
    # row and the office index can never disagree and neither answer can depend
    # on the order the spans happen to be built in.
    office_observations: defaultdict[tuple[str, str], list[Observation]] = defaultdict(
        list
    )
    for observation in observations:
        office_observations[(observation.chamber, observation.office_key)].append(
            observation
        )
    office_profile: dict[tuple[str, str], dict[str, Any]] = {}
    for (chamber, office_key), items in sorted(office_observations.items()):
        office_raws = sorted({item.office_raw for item in items})
        container_kind = _majority_container_kind(items)
        ordinals = [period_ordinal(chamber, item.period) for item in items]
        low = period_bounds(
            chamber, period_token_from_ordinal(chamber, min(ordinals))
        )[0].year
        high = period_bounds(
            chamber, period_token_from_ordinal(chamber, max(ordinals))
        )[1].year
        if container_kind == "member_office":
            # R-1.  When the office key names a member the House ledger resolved,
            # the bioguide IS that member.  Re-deriving it here with Part C's own
            # window rule is what produced the false attribution: it is a
            # different strict rule from the ledger's allowance-year rule and can
            # answer differently, and Part C must not contradict the verified
            # ledger.
            #
            # The method recorded is LEDGER_SUPPLIED_STRICT_RESOLUTION, which
            # says exactly that: the bioguide was taken from the ledger's own
            # resolved map, not re-derived here.  Earlier generations had no
            # such value in the enum and were forced to record the ledger's
            # method name, STRICT_ROSTER_SURNAME_AND_FIRST_NAME, for both cases,
            # so the receipt could not tell a borrowed resolution from one this
            # module derived and that count absorbed both populations.  They are
            # different provenance and they now count separately.
            ledger_bioguide = (
                house_key.bioguide_by_key.get(office_key)
                if chamber == CHAMBER_HOUSE
                else None
            )
            if ledger_bioguide is not None:
                bioguide = ledger_bioguide
                method = "LEDGER_SUPPLIED_STRICT_RESOLUTION"
            else:
                first_name = surname = None
                for raw in office_raws:
                    first_name, surname = office_member_name(chamber, raw)
                    if surname:
                        break
                bioguide, method = resolve_member_bioguide(
                    first_name, surname, roster, nicknames, (low, high)
                )
        else:
            bioguide, method = None, "NOT_A_MEMBER_OFFICE"
        office_profile[(chamber, office_key)] = {
            "bioguide": bioguide,
            "container_kind": container_kind,
            "method": method,
            "office_raws": office_raws,
        }

    # ---- office nodes -----------------------------------------------------
    grouped: defaultdict[
        tuple[str, str, tuple[str, str, str | None]], list[Observation]
    ] = defaultdict(list)
    for observation in observations:
        grouped[
            (observation.chamber, observation.office_key, observation.payee_key)
        ].append(observation)

    nodes_by_person: defaultdict[
        tuple[str, tuple[str, str, str | None]], list[OfficeNode]
    ] = defaultdict(list)
    for (chamber, office_key, payee_key), rows in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], item[0][1], payee_sort_key(item[0][2])),
    ):
        node = OfficeNode(
            chamber=chamber,
            office_key=office_key,
            payee_key=payee_key,
            observations=sorted(
                rows, key=lambda item: (period_ordinal(chamber, item.period), item.row_id)
            ),
        )
        nodes_by_person[(chamber, payee_key)].append(node)

    clusters_by_chamber: defaultdict[
        tuple[str, str, str | None], dict[str, list[list[OfficeNode]]]
    ] = defaultdict(dict)
    shared_employee_links = 0
    day_nonoverlap_links = 0
    same_period_splits = 0
    for (chamber, payee_key), nodes in sorted(
        nodes_by_person.items(),
        key=lambda item: (item[0][0], payee_sort_key(item[0][1])),
    ):
        clusters, shared_links, day_links, splits = cluster_nodes(nodes)
        shared_employee_links += shared_links
        day_nonoverlap_links += day_links
        same_period_splits += splits
        clusters_by_chamber[payee_key][chamber] = clusters

    # ---- cross-chamber merge (S3) ----------------------------------------
    people: list[dict[str, Any]] = []
    cross_chamber_merges = 0
    cross_chamber_ambiguous = 0
    cross_chamber_overlap = 0
    for payee_key in sorted(clusters_by_chamber, key=payee_sort_key):
        by_chamber = clusters_by_chamber[payee_key]
        house_clusters = by_chamber.get(CHAMBER_HOUSE, [])
        senate_clusters = by_chamber.get(CHAMBER_SENATE, [])
        merged = False
        if house_clusters and senate_clusters:
            if len(house_clusters) == 1 and len(senate_clusters) == 1:
                overlap = _windows_overlap(house_clusters[0], senate_clusters[0])
                if overlap and CROSS_CHAMBER_REQUIRES_DISJOINT_PERIODS:
                    cross_chamber_overlap += 1
                else:
                    merged = True
                    cross_chamber_merges += 1
                    people.append(
                        {
                            "payee_key": payee_key,
                            "nodes": house_clusters[0] + senate_clusters[0],
                            "cross_chamber": True,
                        }
                    )
            else:
                cross_chamber_ambiguous += 1
        if not merged:
            for chamber in (CHAMBER_HOUSE, CHAMBER_SENATE):
                for cluster in by_chamber.get(chamber, []):
                    people.append(
                        {
                            "payee_key": payee_key,
                            "nodes": list(cluster),
                            "cross_chamber": False,
                        }
                    )

    # ---- name standard re-key --------------------------------------------
    # Applied to the FINISHED person population, after every identity rule has
    # run.  It replaces the id and the name block and collapses the merge
    # groups; it touches no office node, so the span population that follows is
    # the one the identity rules produced.
    rekey: dict[str, Any] = {}
    if name_standard:
        rekey = prepare_name_standard(people, standard, class_table)
        people = rekey["people"]
        # Ruling A: the two key routes disagreeing is no longer a gate.  The
        # raw parse IS the key source, so the disagreement is the measurement
        # -- reported as a histogram by cause, never fatal.
        if rekey["anchor_moved_under_merge"]:
            failures.append("NAME_STANDARD_MERGE_MOVED_THE_ANCHOR")
        # Ruling E: an empty first_class is attributed and fatal.
        if rekey["empty_first_class_count"]:
            failures.append("NAME_STANDARD_EMPTY_FIRST_CLASS")
        if rekey["chosen_raw_fell_back_to_the_anchor"]:
            failures.append("NAME_STANDARD_CHOSEN_RAW_FELL_BACK_TO_THE_ANCHOR")

    # ---- span + spine rows ------------------------------------------------
    span_rows: list[dict[str, Any]] = []
    spine_rows: list[dict[str, Any]] = []
    person_by_id: dict[str, dict[str, Any]] = {}
    spans_by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    observation_to_person: dict[str, str] = {}
    duplicate_ids = 0
    # Era provenance of the House spans.  The key is the set of ledger
    # source_forms the span's own observations carry, joined with "+", so a span
    # built from both eras is visible as one row rather than inferred from two
    # lanes having been stitched together.
    span_source_forms: Counter = Counter()
    spans_crossing_era_boundary = 0

    # (person id, chamber, office key, THE NODE'S OWN payee key) for every span.
    # The LDA and Quorum name joins key on this rather than on the spine row's
    # payee key block.  In default mode the two are the same value -- the office
    # grouping gives one person exactly one payee key -- so the joins are
    # unchanged.  After a name-standard merge one person carries two payee keys,
    # and keying on the node keeps BOTH spellings resolving, which is what the
    # previous generation did before the merge.
    node_name_index: list[tuple[str, str, str, tuple[str, str, str | None]]] = []
    # Ruling E: a PLAIN dict, not a defaultdict.  Every consumer below reads
    # this by a person id that must already be in it; a defaultdict answered a
    # wrong id with an empty list and lost the join in silence.  A KeyError is
    # the correct answer to a question about a person who does not exist.
    legacy_payee_keys: dict[str, list[tuple[str, str, str | None]]] = {}
    spans_unioned = 0

    for person in people:
        payee_key = person["payee_key"]
        nodes = person["nodes"]
        person_id = person.get("spine_person_id_override") or spine_person_id(
            payee_key, nodes
        )
        if person_id in person_by_id:
            duplicate_ids += 1
        person_by_id[person_id] = person
        legacy_payee_keys.setdefault(person_id, [])
        # Ruling C: the span population is the office nodes with a merged
        # person's same-office, overlapping-or-abutting nodes UNIONED.  Outside
        # a merge this is the identity function -- see union_office_nodes -- so
        # a default-mode build emits exactly the spans it emitted before.
        emitted = union_office_nodes(nodes)
        spans_unioned += len(nodes) - len(emitted)
        link_methods: set[str] = {"SPINE_OFFICE_S1"}
        if len(emitted) > 1:
            link_methods.add("SPINE_CROSS_OFFICE_S2")
        if any(node.shared_periods for node, _keys in emitted) and len(emitted) > 1:
            link_methods.add("SPINE_CROSS_OFFICE_SHARED_EMPLOYEE")
        chambers = sorted({node.chamber for node in nodes})
        if len(chambers) > 1:
            link_methods.add("SPINE_CROSS_CHAMBER_S3")
            identity_tier = "S3"
        elif len(emitted) > 1:
            identity_tier = "S2"
        else:
            identity_tier = "S1"

        bioguides: set[str] = set()
        for node, node_payee_keys in emitted:
            span = _span_row(
                node=node,
                person_id=person_id,
                rule_version=rule_version,
                latest_period=latest_period,
                office_profile=office_profile,
            )
            span_rows.append(span)
            spans_by_person[person_id].append(span)
            for node_payee_key in node_payee_keys:
                node_name_index.append(
                    (person_id, node.chamber, node.office_key, node_payee_key)
                )
                if node_payee_key not in legacy_payee_keys[person_id]:
                    legacy_payee_keys[person_id].append(node_payee_key)
            if node.chamber == CHAMBER_HOUSE:
                span_source_forms[
                    "+".join(
                        sorted(
                            {
                                observation.source_form or "unknown"
                                for observation in node.observations
                            }
                        )
                    )
                ] += 1
                periods = node.period_tokens
                if (
                    PDF_ERA_LAST_QUARTER in periods
                    and CSV_ERA_FIRST_QUARTER in periods
                ):
                    spans_crossing_era_boundary += 1
            if span["member_bioguide"]:
                bioguides.add(span["member_bioguide"])
            for observation in node.observations:
                observation_to_person[observation.row_id] = person_id

        anchor_bounds = [
            (
                period_bounds(node.chamber, node.first_period)[0],
                period_bounds(node.chamber, node.last_period)[1],
                node.chamber,
                node.first_period,
                node.last_period,
            )
            for node, _keys in emitted
        ]
        first_entry = min(anchor_bounds, key=lambda item: (item[0], item[2], item[3]))
        last_entry = max(anchor_bounds, key=lambda item: (item[1], item[2], item[4]))
        spine_rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "chambers": chambers,
                "first_period": first_entry[3],
                "identity_tier": identity_tier,
                "last_period": last_entry[4],
                "lda_source_person_id": None,
                "lda_tier": None,
                "link_methods": sorted(link_methods),
                "member_bioguides": sorted(bioguides),
                "office_count": len({(node.chamber, node.office_key) for node in nodes}),
                "payee_key": {
                    "first": payee_key[1],
                    "last": payee_key[0],
                    "middle_initial": payee_key[2],
                },
                "quorum_staff_id": None,
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": SPINE_SCHEMA,
                "span_count": len(emitted),
                "spine_person_id": person_id,
            }
        )

    spine_by_id = {row["spine_person_id"]: row for row in spine_rows}

    # ---- LDA links --------------------------------------------------------
    part_a_tiers = load_part_a_tiers(sidecar_root)
    # H1 keys on the PDF-era candidate file's own ``candidate_id``.  Before the
    # rebind those ids WERE the PDF lane's row ids; now they arrive inside the
    # ledger as ``source_locator.candidate_id`` while the row id is the ledger's.
    # Keying on the carried candidate id keeps the H1 join intact: all 29,647
    # distinct H1 keys are present in ledger v3, none missing.
    by_candidate_id: dict[str, str] = {}
    for observation in observations:
        if observation.source_candidate_id is not None:
            by_candidate_id[observation.source_candidate_id] = observation_to_person[
                observation.row_id
            ]

    by_name_office_middle: defaultdict[
        tuple[str, str, str, str], set[tuple[str, str | None]]
    ] = defaultdict(set)
    for person_id, chamber, office_key, node_payee_key in node_name_index:
        by_name_office_middle[
            (chamber, office_key, node_payee_key[0], node_payee_key[1])
        ].add((person_id, node_payee_key[2]))

    lda_link_rows: list[dict[str, Any]] = []
    lda_people_in_lanes: set[str] = set()
    lda_linked_people: set[str] = set()
    lda_method_by_person: defaultdict[str, set[str]] = defaultdict(set)

    lane_specs = (
        ("h1_house_sod_pdf", h1_path, "payroll_candidate_id", "LDA_PAYROLL_KEY_H1", CHAMBER_HOUSE),
        ("h2_house_payroll", h2_path, "payroll_support_digest", "LDA_PAYROLL_KEY_H2", CHAMBER_HOUSE),
        ("senate_payroll", senate_match_path, "payroll_support_digest", "LDA_PAYROLL_KEY_SENATE", CHAMBER_SENATE),
    )
    for lane, path, key_field, method, chamber in lane_specs:
        matches = load_match_lane(path, key_field)
        resolved: defaultdict[tuple[str, str | None], list[str]] = defaultdict(list)
        resolution: dict[tuple[str, str | None], str] = {}
        candidates_seen: dict[tuple[str, str | None], int] = {}
        for match in matches:
            person = match["lda_source_person_id"]
            lda_people_in_lanes.add(person)
            if lane == "h1_house_sod_pdf":
                target = by_candidate_id.get(match["payroll_key"])
                found = {target} if target else set()
            else:
                found = _resolve_by_name_and_office(
                    chamber=chamber,
                    display_name=match["display_name"],
                    payee_raw=match["payee_raw"],
                    office=match["office"],
                    by_name_office_middle=by_name_office_middle,
                    house_key=house_key,
                )
            if len(found) == 1:
                spine_id = next(iter(found))
                bucket = (person, spine_id)
                resolution[bucket] = "MATCHED_UNIQUE"
            else:
                bucket = (person, None)
                resolution[bucket] = "KEY_AMBIGUOUS" if found else "KEY_ABSENT"
            resolved[bucket].append(match["payroll_key"])
            candidates_seen[bucket] = max(candidates_seen.get(bucket, 0), len(found))
        for (person, spine_id), keys in sorted(
            resolved.items(), key=lambda item: (item[0][0], item[0][1] or "")
        ):
            linked = spine_id is not None
            if linked:
                lda_linked_people.add(person)
                lda_method_by_person[spine_id].add(person)
            lda_link_rows.append(
                {
                    "canonical_eligible": False,
                    "canonical_employment_promoted": False,
                    "candidate_count": candidates_seen[(person, spine_id)],
                    "key_resolution": resolution[(person, spine_id)],
                    "lane": lane,
                    "lda_source_person_id": person,
                    "link_status": "LINKED_BY_PAYROLL_KEY" if linked else "KEY_NOT_FOUND",
                    "part_a_tier": part_a_tiers.get(person),
                    "payroll_key": min(keys),
                    "payroll_key_count": len(set(keys)),
                    "payroll_key_field": key_field,
                    "review_status": "REVIEW_REQUIRED",
                    "rule_version": rule_version,
                    "schema_id": LDA_LINK_SCHEMA,
                    "spine_person_id": spine_id,
                }
            )
            if linked:
                spine_by_id[spine_id]["link_methods"] = sorted(
                    set(spine_by_id[spine_id]["link_methods"]) | {method}
                )

    for spine_id, lda_people in lda_method_by_person.items():
        row = spine_by_id[spine_id]
        if len(lda_people) == 1:
            person = next(iter(lda_people))
            row["lda_source_person_id"] = person
            row["lda_tier"] = part_a_tiers.get(person)
        else:
            row["link_methods"] = sorted(
                set(row["link_methods"]) | {"LDA_PAYROLL_KEY_AMBIGUOUS"}
            )

    # ---- current staffer links -------------------------------------------
    staff_entries = load_staff_directory(staff_directory_path)
    member_index = load_member_display_index(congestion_path)
    latest_house = latest_period[CHAMBER_HOUSE]
    latest_house_by_bioguide: defaultdict[str, set[str]] = defaultdict(set)
    for span in span_rows:
        if (
            span["chamber"] == CHAMBER_HOUSE
            and span["member_bioguide"]
            and latest_house is not None
            and span["last_period"] == latest_house
        ):
            latest_house_by_bioguide[span["member_bioguide"]].add(span["spine_person_id"])

    staffer_rows: list[dict[str, Any]] = []
    quorum_by_spine: defaultdict[str, set[str]] = defaultdict(set)
    for entry in staff_entries:
        display_key = display_payee_key(entry["display_name"])
        bioguide, source = _resolve_staffer_member(
            entry["member_display"], member_index, roster, nicknames, latest_house
        )
        candidates: set[str] = set()
        if bioguide is not None and display_key is not None:
            for spine_id in sorted(latest_house_by_bioguide.get(bioguide, set())):
                for triple in legacy_payee_keys[spine_id]:
                    if triple[0] != display_key[0] or triple[1] != display_key[1]:
                        continue
                    if not middle_compatible(triple[2], display_key[2]):
                        continue
                    candidates.add(spine_id)
                    break
        if bioguide is None:
            link_status = "MEMBER_UNRESOLVED"
            spine_id = None
        elif len(candidates) == 1:
            link_status = "LINKED"
            spine_id = next(iter(candidates))
        elif candidates:
            link_status = "NAME_COLLISION"
            spine_id = None
        else:
            link_status = "NOT_ON_PAYROLL"
            spine_id = None
        history = []
        if spine_id is not None:
            quorum_by_spine[spine_id].add(entry["quorum_staff_id"])
            for span in sorted(
                spans_by_person[spine_id],
                key=lambda item: (item["chamber"], item["office_key"]),
            ):
                history.append(
                    {
                        "chamber": span["chamber"],
                        "container_kind": span["container_kind"],
                        "first_period": span["first_period"],
                        "last_period": span["last_period"],
                        "member_bioguide": span["member_bioguide"],
                        "office_key": span["office_key"],
                        "periods_observed": span["periods_observed"],
                        "status": span["status"],
                        "title_last": span["title_last"],
                    }
                )
        staffer_rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "candidate_count": len(candidates),
                "display_name": entry["display_name"],
                "display_name_key": {
                    "first": display_key[1] if display_key else None,
                    "last": display_key[0] if display_key else None,
                    "middle_initial": display_key[2] if display_key else None,
                },
                "hill_history": history,
                "link_status": link_status,
                "member_bioguide": bioguide,
                "member_display": entry["member_display"],
                "member_resolution_source": source,
                "quorum_staff_id": entry["quorum_staff_id"],
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": STAFFER_SCHEMA,
                "spine_person_id": spine_id,
                "title_raw": entry["title_raw"],
            }
        )

    for spine_id, staff_ids in quorum_by_spine.items():
        row = spine_by_id[spine_id]
        if len(staff_ids) == 1:
            row["quorum_staff_id"] = next(iter(staff_ids))
            row["link_methods"] = sorted(
                set(row["link_methods"])
                | {"QUORUM_CURRENT_STAFFER_NAME_AND_MEMBER_BIOGUIDE"}
            )
        else:
            row["link_methods"] = sorted(
                set(row["link_methods"]) | {"QUORUM_CURRENT_STAFFER_AMBIGUOUS"}
            )

    # ---- member office index ---------------------------------------------
    office_rows = _member_office_index(
        observations=observations,
        observation_to_person=observation_to_person,
        rule_version=rule_version,
        office_profile=office_profile,
    )

    # ---- name standard: the spine row's name block ------------------------
    id_map_rows: list[dict[str, Any]] = []
    if name_standard:
        id_map_rows = rekey["id_map_rows"]
        for row in spine_rows:
            entry = rekey["by_person_id"][row["spine_person_id"]]
            row["collision_ordinal"] = entry["collision_ordinal"]
            row["display_name"] = entry["display_name"]
            row["legacy_person_id"] = entry["legacy_person_ids"][0]
            row["legacy_person_ids"] = list(entry["legacy_person_ids"])
            row["name_key"] = entry["name_key"]
            row["name_standard_parts"] = dict(entry["name_standard_parts"])
            row["payee_key"] = dict(entry["payee_key"])
            row["payee_key_legacy_variants"] = [
                dict(item) for item in entry["payee_key_legacy_variants"]
            ]
            row["payee_raw"] = entry["payee_raw"]
            row["payee_raw_examples"] = list(entry["payee_raw_examples"])
            row["payee_raw_variant_count"] = entry["payee_raw_variant_count"]
            row["suffix_observed"] = list(entry["suffix_observed"])

    # ---- sort + write -----------------------------------------------------
    # first_period joins the span sort key with ruling C: after a union, a
    # person can still hold two spans in ONE office when a real gap separates
    # them, and (person, chamber, office) alone no longer totally orders the
    # file.  It did before, so adding it changes no existing ordering.
    span_rows.sort(
        key=lambda row: (
            row["spine_person_id"],
            row["chamber"],
            row["office_key"],
            period_ordinal(row["chamber"], row["first_period"]),
        )
    )
    spine_rows.sort(key=lambda row: row["spine_person_id"])
    staffer_rows.sort(
        key=lambda row: (
            row["member_display"],
            row["display_name"],
            row["quorum_staff_id"],
        )
    )
    lda_link_rows.sort(
        key=lambda row: (
            row["lda_source_person_id"],
            row["lane"],
            row["spine_person_id"] or "",
        )
    )
    office_rows.sort(key=lambda row: (row["chamber"], row["office_key"]))

    output_root.mkdir(parents=True, exist_ok=True)
    payloads = {
        SPAN_FILE: span_rows,
        SPINE_FILE: spine_rows,
        STAFFER_FILE: staffer_rows,
        LDA_LINK_FILE: lda_link_rows,
        OFFICE_INDEX_FILE: office_rows,
    }
    if name_standard:
        payloads[NAME_STANDARD_ID_MAP_FILE] = id_map_rows
    for name, rows in payloads.items():
        write_ndjson_gz(output_root / name, rows)

    # ---- tripwire + language law -----------------------------------------
    extra_verbatim: frozenset[str] = (
        NAME_STANDARD_VERBATIM_LEAF_NAMES if name_standard else frozenset()
    )
    tripwire: list[str] = []
    authored_hits: list[str] = []
    verbatim_counts: Counter = Counter()
    for rows in payloads.values():
        tripwire.extend(assert_unpromoted(rows))
        hits, occurrences = scan_language_law(rows, extra_verbatim)
        authored_hits.extend(hits)
        verbatim_counts.update(occurrences)
    if tripwire:
        failures.append("INV1_PROMOTION_TRIPWIRE")
    if authored_hits:
        failures.append("INV7_LANGUAGE_LAW_AUTHORED_TOKEN")

    # ---- conservation -----------------------------------------------------
    span_observation_sum = sum(row["observation_count"] for row in span_rows)
    span_row_id_union: set[str] = set()
    for row in span_rows:
        span_row_id_union.update(row["source_row_ids"])
    distinct_row_ids = len({observation.row_id for observation in observations})
    observation_conservation = span_observation_sum == len(observations)
    spine_ids_in_spans = {row["spine_person_id"] for row in span_rows}
    spine_ids_equal = spine_ids_in_spans == {row["spine_person_id"] for row in spine_rows}
    if not observation_conservation:
        failures.append("CONSERVATION_OBSERVATION_COUNT_MISMATCH")
    if span_row_id_union != {observation.row_id for observation in observations}:
        failures.append("CONSERVATION_SOURCE_ROW_ID_MISMATCH")
    if not spine_ids_equal:
        failures.append("CONSERVATION_SPINE_PERSON_MISMATCH")
    if duplicate_ids:
        failures.append("DUPLICATE_SPINE_PERSON_ID")

    # ---- ruling C: the union actually happened ---------------------------
    # No person may hold two span rows in ONE office whose reporting windows
    # overlap or abut.  Where that was ever true it was a merged person's two
    # spellings of the same stretch of service, and union_office_nodes has
    # collapsed them; a survivor here means the union did not run.
    person_office_windows: dict[tuple[str, str, str], list[tuple[int, int]]] = {}
    for row in span_rows:
        person_office_windows.setdefault(
            (row["spine_person_id"], row["chamber"], row["office_key"]), []
        ).append(
            (
                period_ordinal(row["chamber"], row["first_period"]),
                period_ordinal(row["chamber"], row["last_period"]),
            )
        )
    overlapping_person_office_spans = 0
    for windows in person_office_windows.values():
        if len(windows) < 2:
            continue
        windows.sort()
        for left, right in zip(windows, windows[1:]):
            if right[0] <= left[1] + 1:
                overlapping_person_office_spans += 1
    del person_office_windows
    if overlapping_person_office_spans:
        failures.append("SPAN_ROWS_SHARE_A_PERSON_OFFICE_WITH_TOUCHING_WINDOWS")
    if len(staffer_rows) != len(staff_entries):
        failures.append("CURRENT_STAFFER_ROWS_NOT_DIRECTORY_TOTAL")

    linked_staffers = sum(1 for row in staffer_rows if row["link_status"] == "LINKED")
    registrant_people = load_registrant_people(registrant_path)

    bioguide_resolution: dict[str, Any] = {}
    for chamber in (CHAMBER_HOUSE, CHAMBER_SENATE):
        member_spans = [
            row
            for row in span_rows
            if row["chamber"] == chamber and row["container_kind"] == "member_office"
        ]
        resolved_spans = sum(1 for row in member_spans if row["member_bioguide"])
        bioguide_resolution[chamber] = {
            "member_office_spans": len(member_spans),
            "resolved": resolved_spans,
            "rate": (
                round(resolved_spans / len(member_spans), 6) if member_spans else None
            ),
        }

    file_block = {}
    for name in payloads:
        path = output_root / name
        file_block[name] = {
            "bytes": path.stat().st_size,
            "rows": len(payloads[name]),
            "sha256": sha(path),
        }

    # ---- name standard: the invariants that gate this generation ----------
    # Every one of these is a number this build measured, not a claim.  Each one
    # that is false appends a failure, and a receipt with any failure is FAIL.
    name_standard_block: dict[str, Any] = {}
    if name_standard:
        merge_groups = rekey["merge_groups"]
        people_merged = sum(len(item["legacy_person_ids"]) for item in merge_groups)
        ids_removed = people_merged - len(merge_groups)
        legacy_ids_in_map = [row["legacy_person_id"] for row in id_map_rows]
        baseline: dict[str, Any] = {"bound": baseline_receipt_path is not None}
        if baseline_receipt_path is not None and baseline_spine_path is not None:
            with baseline_receipt_path.open("r", encoding="utf-8") as stream:
                baseline_receipt = json.load(stream)
            baseline_inputs = baseline_receipt.get("inputs") or {}
            here = {
                label: entry.get("sha256")
                for label, entry in inputs.items()
                if not label.startswith("name_standard_")
            }
            there = {
                label: entry.get("sha256") for label, entry in baseline_inputs.items()
            }
            differing = sorted(
                label
                for label in set(here) | set(there)
                if here.get(label) != there.get(label)
            )
            baseline_ids = [
                row["spine_person_id"] for row in read_rows(baseline_spine_path)
            ]
            baseline_id_set = set(baseline_ids)
            map_id_counts = Counter(legacy_ids_in_map)
            baseline_counts = baseline_receipt.get("counts") or {}
            baseline_conservation = baseline_receipt.get("conservation") or {}
            baseline.update(
                {
                    "generation": baseline_root.name if baseline_root else None,
                    "input_sha256_differences": differing,
                    "input_sha256_identical": not differing,
                    "member_office_index_rows": baseline_counts.get(
                        "member_office_index_rows"
                    ),
                    "member_office_index_rows_conserved": baseline_counts.get(
                        "member_office_index_rows"
                    )
                    == len(office_rows),
                    "observations_admitted": baseline_conservation.get(
                        "observations_admitted"
                    ),
                    "observations_conserved": baseline_conservation.get(
                        "observations_admitted"
                    )
                    == len(observations),
                    "person_office_spans": baseline_counts.get("person_office_spans"),
                    # Ruling C: a re-key conserves spans EXCEPT where a merged
                    # person's two spellings of one stretch of service in one
                    # office were unioned into a single row.  spans_unioned is
                    # that count, and it is zero unless a merge happened.
                    "person_office_spans_unioned": spans_unioned,
                    "person_office_spans_equal_baseline_minus_unioned": (
                        isinstance(baseline_counts.get("person_office_spans"), int)
                        and baseline_counts["person_office_spans"] - spans_unioned
                        == len(span_rows)
                    ),
                    "spine_persons": len(baseline_ids),
                    "spine_persons_equals_baseline_minus_merges": (
                        len(baseline_ids) - ids_removed == len(spine_rows)
                    ),
                    "every_baseline_id_in_the_map_exactly_once": (
                        len(baseline_ids) == len(baseline_id_set)
                        and baseline_id_set == set(map_id_counts)
                        and all(count == 1 for count in map_id_counts.values())
                    ),
                    "baseline_ids_missing_from_the_map": sorted(
                        baseline_id_set - set(map_id_counts)
                    )[:20],
                    "map_ids_absent_from_the_baseline": sorted(
                        set(map_id_counts) - baseline_id_set
                    )[:20],
                }
            )
            for label, ok in (
                ("NAME_STANDARD_BASELINE_INPUT_SHA_DRIFT", baseline["input_sha256_identical"]),
                (
                    "NAME_STANDARD_BASELINE_SPINE_COUNT_MISMATCH",
                    baseline["spine_persons_equals_baseline_minus_merges"],
                ),
                (
                    "NAME_STANDARD_ID_MAP_NOT_A_TOTAL_BIJECTION_ON_THE_BASELINE",
                    baseline["every_baseline_id_in_the_map_exactly_once"],
                ),
                (
                    "NAME_STANDARD_BASELINE_SPAN_COUNT_MISMATCH",
                    baseline["person_office_spans_equal_baseline_minus_unioned"],
                ),
                (
                    "NAME_STANDARD_BASELINE_OFFICE_INDEX_COUNT_MISMATCH",
                    baseline["member_office_index_rows_conserved"],
                ),
                (
                    "NAME_STANDARD_BASELINE_OBSERVATION_COUNT_MISMATCH",
                    baseline["observations_conserved"],
                ),
            ):
                if not ok:
                    failures.append(label)
        if len(legacy_ids_in_map) != len(set(legacy_ids_in_map)):
            failures.append("NAME_STANDARD_ID_MAP_HAS_A_REPEATED_LEGACY_ID")
        if len(id_map_rows) != rekey["people_before"]:
            failures.append("NAME_STANDARD_ID_MAP_IS_NOT_ONE_ROW_PER_PERSON")
        if len({row["person_id"] for row in id_map_rows}) != len(spine_rows):
            failures.append("NAME_STANDARD_ID_MAP_TARGETS_DISAGREE_WITH_THE_SPINE")
        # ---- ruling B: the delta invariant ------------------------------
        delta_agreement: dict[str, Any] = {
            "bound": delta_report_path is not None,
            "residuals": rekey["delta_residuals_count"],
            "residual_allowance": NAME_STANDARD_DELTA_RESIDUAL_ALLOWANCE,
        }
        if delta_report_path is not None:
            with delta_report_path.open("r", encoding="utf-8") as stream:
                delta_report = json.load(stream)
            reported = (
                (delta_report.get("key_change") or {}).get("cause_histogram") or {}
            )
            mine = rekey["cause_counts"]
            reconstruction = rekey["delta_reconstruction_cause_counts"]
            residuals = rekey["delta_residuals_count"]
            per_cause = {
                cause: {
                    "this_build": mine.get(cause, 0),
                    "the_delta_report": reported.get(cause, 0),
                    "the_delta_reconstruction": reconstruction.get(cause, 0),
                }
                for cause in sorted(set(mine) | set(reported) | set(reconstruction))
            }
            over_allowance = sorted(
                cause
                for cause, item in per_cause.items()
                if abs(item["this_build"] - item["the_delta_report"]) > residuals
            )
            reconstruction_exact = sorted(
                cause
                for cause, item in per_cause.items()
                if item["the_delta_reconstruction"] != item["the_delta_report"]
            )
            delta_agreement.update(
                {
                    "by_cause": per_cause,
                    "causes_differing_by_more_than_the_residual_count": over_allowance,
                    "causes_where_the_reconstruction_differs_from_the_report":
                        reconstruction_exact,
                    "report_keys_changed": (delta_report.get("key_change") or {}).get(
                        "changed_v1_1_raw_route"
                    ),
                    "report_name_standard_version": delta_report.get(
                        "name_standard_version"
                    ),
                    "this_build_keys_changed": rekey["keys_changed"],
                }
            )
            if residuals > NAME_STANDARD_DELTA_RESIDUAL_ALLOWANCE:
                failures.append("NAME_STANDARD_DELTA_RESIDUALS_OVER_ALLOWANCE")
            if over_allowance:
                failures.append("NAME_STANDARD_DELTA_CAUSE_HISTOGRAM_DISAGREES")
            if reconstruction_exact:
                failures.append("NAME_STANDARD_DELTA_RECONSTRUCTION_DISAGREES")
        else:
            failures.append("NAME_STANDARD_DELTA_REPORT_NOT_BOUND")
        name_standard_block = {
            "baseline": baseline,
            "canonical_promotions": 0,
            "cause_counts": rekey["cause_counts"],
            "chosen_raw_fell_back_to_the_anchor": rekey[
                "chosen_raw_fell_back_to_the_anchor"
            ],
            "class_table_entries": len(class_table),
            "collision_ordinals_above_one": rekey["collision_ordinals_above_one"],
            "combination_counts": rekey["combination_counts"],
            "delta_agreement": delta_agreement,
            "delta_reconstruction_cause_counts": rekey[
                "delta_reconstruction_cause_counts"
            ],
            "delta_residuals": rekey["delta_residuals"][:200],
            "delta_residuals_count": rekey["delta_residuals_count"],
            "empty_first_class": rekey["empty_first_class"][:40],
            "empty_first_class_count": rekey["empty_first_class_count"],
            "id_map_file": NAME_STANDARD_ID_MAP_FILE,
            "id_map_rows": len(id_map_rows),
            "key_source_disagreement_examples": rekey[
                "key_source_disagreement_examples"
            ],
            "key_source_disagreement_people": rekey["key_source_disagreement_people"],
            "key_source_disagreements": rekey["key_source_disagreements"],
            "keys_changed": rekey["keys_changed"],
            "keys_unchanged": rekey["keys_unchanged"],
            "merge_basis_counts": rekey["merge_basis_counts"],
            "merge_groups": merge_groups,
            "merge_groups_count": len(merge_groups),
            "merge_ids_removed": ids_removed,
            "merge_people_in_groups": people_merged,
            "merges_blocked": rekey["merges_blocked"],
            "merges_blocked_pairs": rekey["merges_blocked_pairs"],
            "nickname_class_transitions": rekey["nickname_class_transitions"][:30],
            "people_on_an_ambiguous_triple": rekey["people_on_an_ambiguous_triple"],
            # Ruling A: this is a RE-KEY of the previous generation's people,
            # not a re-grouping of its observations.  The office node grouping
            # still keys on this module's own payee key triple.
            "regrouping": False,
            "spans_unioned": spans_unioned,
            "notes": {
                "canonical_promotions": (
                    "The spine carries no promotion field for a re-key to set. "
                    "Every emitted row still carries review_status REVIEW_REQUIRED, "
                    "canonical_eligible false and canonical_employment_promoted "
                    "false, the anti-promotion tripwire runs over the id map as "
                    "well as the five payloads, and both receipt promotion "
                    "counters stay at zero. A re-key changes what a person is "
                    "called, never what the record claims about them."
                ),
                "id_tuple": (
                    "spine_person_id is sha256 over the compact JSON object "
                    "{chamber, collision_ordinal, first_office_key, "
                    "first_period, name_key}, where name_key is "
                    "last|first_class|middle_initial from the ONE name standard "
                    "and chamber, first_office_key and first_period come from "
                    "the person's anchor office node -- the minimum over the "
                    "person's nodes of (period start ordinal, chamber, office "
                    "key). collision_ordinal is 1 for everybody the merge guard "
                    "did not have to separate and 2, 3, ... only where it did; "
                    "it is in the tuple for every row so the id reconstructs "
                    "from fields the spine row itself carries. The previous "
                    "rule held payee_key [last, first, middle_initial] where "
                    "name_key now stands, over the same anchor and with no "
                    "ordinal. legacy_person_id on every spine row is that "
                    "previous digest, so the id map is read off this build."
                ),
                "key_source": (
                    "name_key is parse_name(chosen raw payee string, source) "
                    "and nothing else. chosen raw is picked from the raws THIS "
                    "person was recorded under: prefer a key carrying a "
                    "non-empty middle initial, then the most frequently "
                    "recorded, then the lexicographic minimum. "
                    "parts_from_payee_key is no longer a key route -- it cannot "
                    "see a bare V, a particle surname or a glued annotation, "
                    "because the builder's own tokeniser removes all three "
                    "before the triple exists. It is still computed, and "
                    "key_source_disagreements is the histogram of how far the "
                    "two routes are apart, by cause. That histogram is a "
                    "measurement, not a gate: it never fails the build."
                ),
                "merge_guard": (
                    "Two previous ids that land on one id tuple are NOT merged "
                    "when, in the same office and the same report period, their "
                    "distinct payee lines carry service-date windows that "
                    "overlap at DAY level. Only House Statement of Disbursements "
                    "rows print service dates; a Senate report period is not a "
                    "day. Missing service dates also block a same-office, same-period "
                    "merge, with basis same_period_variant_no_day_dates. "
                    "A blocked pair is kept "
                    "apart by collision_ordinal inside the hashed tuple, and "
                    "every blocked pair is listed in merges_blocked."
                ),
                "spans_unioned": (
                    "After a merge one person can hold two office nodes that "
                    "are the SAME office under two spellings. Where their "
                    "reporting windows overlap or abut they are one continuous "
                    "stretch of service and are emitted as ONE span row; where "
                    "a real gap separates them they stay two, exactly as one "
                    "speller's gapped service already does. spans_unioned is "
                    "how many span rows that removed, so person_office_spans is "
                    "the previous generation's count minus it. Both payee key "
                    "spellings still enter the LDA and Quorum name joins."
                ),
                "splits_are_impossible": (
                    "The key is resolved per person and a person carries "
                    "exactly one resolved key, so a re-key can only be "
                    "many-to-one. The id map therefore has one row per previous "
                    "person and no row can name two new ids. The merge GUARD "
                    "does not split a person either: it declines to merge two "
                    "people who were already two."
                ),
                "suffix_populations": (
                    "rows_with_a_suffix_from_payee_key_lift counts people whose "
                    "suffix survives in this module's own already-parsed triple, "
                    "which only a hyphen-glued one does. "
                    "rows_with_a_suffix_from_raw_parse counts people whose RAW "
                    "payroll string carries one, which is what the standard "
                    "recovers. The two are different questions and the second is "
                    "much the larger."
                ),
                "what_is_held_fixed": (
                    "The observation parse, the office key, the office node "
                    "grouping, nodes_linkable, cluster_nodes, the cross-chamber "
                    "rule and the member office index are the previous "
                    "generation's. regrouping is false: this is a re-key of the "
                    "previous generation's PEOPLE, not a re-grouping of its "
                    "observations. What moves is the person id, the spine row's "
                    "name block, the id every span, LDA link and staffer link "
                    "row carries, and -- only for a merged person -- the union "
                    "of two same-office spans into one row."
                ),
            },
            "reason_counts": rekey["reason_counts"],
            "rows_with_a_suffix_from_payee_key_lift": rekey[
                "rows_with_a_suffix_from_payee_key_lift"
            ],
            "rows_with_a_suffix_from_raw_parse": rekey[
                "rows_with_a_suffix_from_raw_parse"
            ],
            "rows_with_more_than_one_observed_suffix": rekey[
                "rows_with_more_than_one_observed_suffix"
            ],
            "spine_persons_before": rekey["people_before"],
        }

    receipt = {
        "bioguide_resolution": bioguide_resolution,
        "canonical_employment_promotions": 0,
        "canonical_identity_promotions": 0,
        "conservation": {
            "current_staffer_rows": len(staffer_rows),
            "current_staffer_rows_equal_directory": len(staffer_rows)
            == len(staff_entries),
            "distinct_source_row_ids": distinct_row_ids,
            "duplicate_spine_person_ids": duplicate_ids,
            "observation_conservation_holds": observation_conservation,
            "observations_admitted": len(observations),
            "span_observation_count_sum": span_observation_sum,
            "span_source_row_id_union": len(span_row_id_union),
            "spine_ids_equal": spine_ids_equal,
            "spine_person_ids_in_spans": len(spine_ids_in_spans),
            "spine_rows": len(spine_rows),
            "staff_directory_entries": len(staff_entries),
        },
        "counts": {
            "cross_chamber_merges": cross_chamber_merges,
            "cross_chamber_not_merged_ambiguous": cross_chamber_ambiguous,
            "cross_chamber_not_merged_period_overlap": cross_chamber_overlap,
            "current_staffer_link_status": dict(
                sorted(Counter(row["link_status"] for row in staffer_rows).items())
            ),
            "identity_tier_people": dict(
                sorted(Counter(row["identity_tier"] for row in spine_rows).items())
            ),
            "lda_key_resolution": dict(
                sorted(Counter(row["key_resolution"] for row in lda_link_rows).items())
            ),
            "lda_link_status": dict(
                sorted(Counter(row["link_status"] for row in lda_link_rows).items())
            ),
            "lda_spine_links": len(lda_link_rows),
            "ledger_field_disagreements": dict(
                sorted(
                    {
                        **_ledger_disagreements(observations, office_profile),
                        **_member_office_key_census(observations, office_profile),
                        **house_key_stats,
                    }.items()
                )
            ),
            "member_office_index_rows": len(office_rows),
            "member_resolution_methods": dict(
                sorted(
                    Counter(row["member_resolution_method"] for row in span_rows).items()
                )
            ),
            "person_office_spans": len(span_rows),
            "person_office_spans_with_touching_windows": (
                overlapping_person_office_spans
            ),
            "same_period_day_nonoverlap_office_links": day_nonoverlap_links,
            "same_period_office_splits": same_period_splits,
            "shared_employee_office_links": shared_employee_links,
            "spans_unioned_after_merge": spans_unioned,
            "spans_by_chamber": dict(
                sorted(Counter(row["chamber"] for row in span_rows).items())
            ),
            "spans_by_container_kind": dict(
                sorted(Counter(row["container_kind"] for row in span_rows).items())
            ),
            "spans_by_source_lane": dict(
                sorted(
                    Counter(
                        lane for row in span_rows for lane in row["source_lane"]
                    ).items()
                )
            ),
            "spans_by_house_source_form": dict(sorted(span_source_forms.items())),
            "spans_by_status": dict(
                sorted(Counter(row["status"] for row in span_rows).items())
            ),
            "spans_crossing_csv_pdf_era_boundary": spans_crossing_era_boundary,
            "spine_persons": len(spine_rows),
        },
        "determinism": {
            "gzip_mtime": 0,
            "json_key_order": "lexicographic",
            "newline": "LF",
            "sort_keys": {
                LDA_LINK_FILE: "lda_source_person_id, lane, spine_person_id",
                OFFICE_INDEX_FILE: "chamber, office_key",
                SPAN_FILE: "spine_person_id, chamber, office_key, first_period",
                SPINE_FILE: "spine_person_id",
                STAFFER_FILE: "member_display, display_name, quorum_staff_id",
            },
        },
        "dials": {
            "annualization_days": ANNUALIZATION_DAYS,
            "house_same_quarter_link_rule": (
                "link only when both office nodes have complete printed service dates "
                "and their inclusive service calendars are disjoint"
            ),
            "cross_chamber_requires_disjoint_periods": (
                CROSS_CHAMBER_REQUIRES_DISJOINT_PERIODS
            ),
            "envelope_widening_reporting_periods": (
                ENVELOPE_WIDENING_REPORTING_PERIODS
            ),
            "freeze_status": "UNTESTED_DEFAULTS_PENDING_FREEZE",
            "max_office_raw_examples": MAX_OFFICE_RAW_EXAMPLES,
            "quorum_member_roster_fallback": QUORUM_MEMBER_ROSTER_FALLBACK,
            "s_strength": dict(sorted(S_STRENGTH.items())),
            "shared_employee_title_phrases": list(SHARED_EMPLOYEE_TITLE_PHRASES),
        },
        "failures": sorted(set(failures)),
        "files": file_block,
        "generated_at": generated_at,
        "implementation": {
            "path": Path(__file__).name,
            "sha256": sha(Path(__file__).resolve()),
        },
        "inputs": inputs,
        "language_law": {
            "authored_value_and_field_name_hits": len(authored_hits),
            "banned_tokens": list(LANGUAGE_LAW_TOKENS),
            "policy": LANGUAGE_LAW_POLICY,
            "verbatim_source_quoted_fields": sorted(
                VERBATIM_SOURCE_QUOTED_FIELDS
                + (NAME_STANDARD_VERBATIM_SOURCE_QUOTED_FIELDS if name_standard else ())
            )
            if name_standard
            else list(VERBATIM_SOURCE_QUOTED_FIELDS),
            "verbatim_token_occurrences": dict(sorted(verbatim_counts.items())),
        },
        "latest_period_by_chamber": dict(sorted(latest_period.items())),
        "link_rates": {
            "current_staffers_linked": linked_staffers,
            "current_staffers_linked_rate": (
                round(linked_staffers / len(staffer_rows), 6) if staffer_rows else None
            ),
            "current_staffers_total": len(staffer_rows),
            "expected_current_staffers_total": EXPECTED_CURRENT_STAFFERS,
            "expected_lda_people_in_match_lanes": EXPECTED_LDA_PAYROLL_PEOPLE,
            "lda_people_in_match_lanes": len(lda_people_in_lanes),
            "lda_people_linked": len(lda_linked_people),
            "lda_people_linked_rate": (
                round(len(lda_linked_people) / len(lda_people_in_lanes), 6)
                if lda_people_in_lanes
                else None
            ),
        },
        "notes": {
            "era_boundary_spans": (
                "counts.spans_crossing_csv_pdf_era_boundary counts the House spans "
                "observed in BOTH 2015Q4 and 2016Q1. Before the ledger v3 rebind those "
                "two quarters reached this module through two different lanes and a "
                "span crossing the boundary was a stitch between them. They now reach "
                "it through one lane, from one file, under one parse, so a crossing "
                "span is a property of the span rule alone. "
                "counts.spans_by_house_source_form gives the same fact at span grain: "
                "the ledger source_forms each span's own observations carry."
            ),
            "generation_ids_are_not_comparable": (
                "spine_person_id is a digest over the person's chamber-scoped payee "
                "key, first office key and first period, so every id changes when the "
                "office key changes. The ids in this generation are not comparable "
                "with any other generation's; join on the payee key and the office "
                "instead. The v1 and v2 generations are kept unaltered as the record."
            ),
            "identity_tiers": (
                "S1 is one office; S2 is more than one office in one chamber linked "
                "only across non-overlapping periods, or a shared-employee row; S3 is "
                "cross-chamber and name-only. Every tier is a review candidate, not an "
                "identity finding."
            ),
            "ledger_field_disagreements_block": (
                "That block carries three things: how often this lane's derived "
                "office key, container kind and member bioguide differ from the House "
                "ledger's own value on the same row; the member-office key census that "
                "measures whether one key ever covers two members; and the sizes of "
                "the two maps the member office key is built from. office_key "
                "disagreement is a vocabulary difference outside member offices -- the "
                "ledger prefixes every non-member office with its kind, as "
                "COMMITTEE:COMMITTEE ON RULES, and this lane does not -- and "
                "container_kind disagreement is the same kind of vocabulary "
                "difference, since this lane has no 'other' kind and reports an "
                "unrecognised office family as 'unresolved'. Neither is an attribution "
                "of a person to a member. member_bioguide disagreement is, and it is "
                "the one that must be zero."
            ),
            "house_ledger_v3_rebind": (
                "The House is bound to the ledger and only the ledger. Ledger v3 "
                "carries both eras in one file -- 2009Q3-2015Q4 as source_form "
                "house_gov_single_volume_pdf and 2016Q1-2026Q1 as detail_csv -- so the "
                "separate PDF-era candidate file earlier generations read as a second "
                "lane is not read at all, and no option exists to pass it. Binding "
                "both would admit every 2009Q3-2015Q4 row twice while conservation "
                "still balanced, because the duplicates would carry different row ids. "
                "sources.separate_pdf_lane_bound pins that at false and the verifier "
                "fails the generation if any span carries the retired lane name. The "
                "H1 LDA match lane, which keys on the PDF candidate file's own "
                "candidate_id, is unaffected: the ledger carries that id through in "
                "source_locator.candidate_id and this module joins on it."
            ),
            "member_resolution_method_split": (
                "LEDGER_SUPPLIED_STRICT_RESOLUTION means the member came from the "
                "House ledger's own resolved map for that office key. "
                "STRICT_ROSTER_SURNAME_AND_FIRST_NAME means this module derived it "
                "from the roster for an office the ledger never resolved. Earlier "
                "generations had no separate value and recorded the ledger's method "
                "name for both, so the two populations were summed under one label and "
                "the receipt could not tell borrowed from derived. Comparing that "
                "single earlier count against either of these two is a category error."
            ),
            "member_office_key": (
                "A House member office is keyed on the member the House ledger "
                "resolved, never on the bare surname. The key is the ledger's own "
                "HON:<bioguide> for an office string the ledger resolved; for a string "
                "the ledger never saw -- from ledger v3 that is the LDA lanes, whose "
                "office strings carry no allowance-year prefix, the PDF-era strings "
                "now being in the ledger itself -- it is the "
                "same HON:<bioguide> when the office string's first name and surname "
                "are a pair the ledger resolved unambiguously and at most one roster "
                "member holding that pair served in the covered era; otherwise it is "
                "HON:<first>|<surname>, normalized. A member office key that names a "
                "bioguide takes its member from the ledger rather than re-deriving "
                "one, so a span can never attribute a person to a member the ledger "
                "put in a different office. Two members who share BOTH names still "
                "share the fallback key: the office string cannot separate them, the "
                "ledger declines to resolve them too, and the key therefore carries no "
                "bioguide and attributes nothing."
            ),
            "nickname_table": (
                "loaded from the declared file"
                if nickname_table_loaded
                else "declared file absent; the Part A built-in table was used"
            ),
            "office_string_continuation": (
                "A Statement of Disbursements continuation marker is stripped only "
                "when the dash or apostrophe that introduces it is present. While that "
                "character was optional the pattern also removed a trailing CON from "
                "the surname itself, truncating HON. DON BACON and "
                "HON. CHARLIE MELANCON. Of 11,391 distinct House office strings, 2,085 "
                "carry a genuine continuation and every one of them carries the "
                "introducing character."
            ),
            "registrant_episodes": (
                "Part C emits no registrant output. The episode file is hash-bound and "
                "used here only to count how many spine-linked LDA people also appear "
                "in it: "
                f"{len(registrant_people & lda_linked_people)} of "
                f"{len(lda_linked_people)}. That count is arithmetic, not a finding. "
                "The episode file covers all 25,340 sealed LDA people, so every LDA "
                "person the spine links is in it by construction and the ratio can "
                "only be one. It shows that the join is complete; it shows nothing "
                "about how many of these people were employed by a registrant, and it "
                "corroborates no employment."
            ),
            "shared_employee_flag_not_used": (
                "The shared-employee test here is the TITLE test named in the spec: a "
                "row is a shared-employee row when its title is SHARED EMPLOYEE. The "
                "House ledger's own shared_employee_flag decides nothing here; it is "
                "read only to report the two counts that close this note. "
                "That flag is set whenever a person appears in two or more offices in "
                "one quarter, which is the very condition the shared-employee rule is "
                "asked to adjudicate, so keying the rule on it would make the rule "
                "true by construction. In the bound ledger the flag stands on "
                f"{house_key_stats['ledger_rows_with_shared_employee_flag']} rows "
                f"against {house_key_stats['ledger_rows_with_shared_employee_title']} "
                "rows that actually carry the title."
            ),
            "scope": (
                "Candidate plane only. Nothing here is canonical, nothing is an "
                "identity finding, and no tenure is asserted. Consumed by nothing "
                "until ruled."
            ),
            "span_grain": (
                "Core is the observed reporting-period span at report-period grain; "
                "envelope widens it by one reporting period each side. A span with an "
                "internal gap is emitted as one row with contiguous:false rather than "
                "split, so every observation maps to exactly one span."
            ),
        },
        "period_kind_by_chamber": dict(sorted(PERIOD_KIND.items())),
        "promotion_policy": "REVIEW_REQUIRED_ZERO_CANONICAL_PROMOTIONS",
        "review_status": "REVIEW_REQUIRED",
        "rule_version": rule_version,
        "run_id": args.run_id,
        "schema_id": RECEIPT_SCHEMA,
        "sources": {
            "house_ledger_present": ledger_observations_path is not None,
            "house_ledger_quarters": len(ledger_quarters),
            "house_ledger_quarters_by_source_form": {
                form: len(quarters)
                for form, quarters in sorted(ledger_quarters_by_form.items())
            },
            "house_ledger_rows_admitted_by_source_form": dict(
                sorted(ledger_rows_admitted_by_form.items())
            ),
            "house_ledger_rows_read_by_source_form": dict(
                sorted(ledger_rows_read_by_form.items())
            ),
            # ``senate_paths``, not the loop variable that walked it: with no
            # --senate-candidates bound the loop never ran and reading its
            # variable here raised UnboundLocalError, so a House-only build
            # crashed at receipt time.  With one or more bound, the two spell
            # the same True.
            "senate_present": bool(senate_paths),
            "separate_pdf_lane_bound": False,
            "source_rows_admitted": dict(sorted(rows_admitted.items())),
            "source_rows_read": dict(sorted(rows_read.items())),
            "source_rows_suppressed": dict(sorted(rows_suppressed.items())),
            "source_rows_suppressed_by_reason": dict(
                sorted(suppression_reasons.items())
            ),
            "suppression_rule": (
                "The House has one lane: the ledger, which carries both eras. There "
                "is no second PDF-era lane to deduplicate against, and no row is "
                "dropped for being already covered. A row is suppressed only when "
                "this module cannot parse it: an empty office string, an empty payee "
                "string, no usable reporting period, or a payee string that yields no "
                "name key. Every suppressed row is counted by lane, era and reason in "
                "source_rows_suppressed_by_reason. Suppression is reported, never "
                "repaired: a row this module cannot key is not admitted under a "
                "guess."
            ),
        },
        "stage_id": STAGE_ID,
        "status": "FAIL" if failures else "PASS",
    }
    if name_standard:
        receipt["name_standard"] = name_standard_block
    receipt_hits, _ = scan_language_law(
        {
            key: value
            for key, value in receipt.items()
            if key not in {"inputs", "files", "language_law"}
        },
        extra_verbatim,
    )
    if receipt_hits:
        receipt["failures"] = sorted(
            set(receipt["failures"]) | {"INV7_LANGUAGE_LAW_AUTHORED_TOKEN_IN_RECEIPT"}
        )
        receipt["status"] = "FAIL"
        receipt["language_law"]["authored_value_and_field_name_hits"] = len(
            authored_hits
        ) + len(receipt_hits)

    receipt_path = output_root / RECEIPT_FILE
    write_json_atomic(receipt_path, receipt)
    return {
        "output_root": str(output_root),
        "receipt": receipt,
        "receipt_sha256": sha(receipt_path),
        "tripwire": tripwire,
    }


def _windows_overlap(left: Sequence[OfficeNode], right: Sequence[OfficeNode]) -> bool:
    """Do two clusters share any calendar day at reporting-period grain?"""

    def intervals(cluster: Sequence[OfficeNode]) -> list[tuple[date, date]]:
        result = []
        for node in cluster:
            for period in sorted(node.period_tokens):
                result.append(period_bounds(node.chamber, period))
        return result

    left_intervals = intervals(left)
    right_intervals = intervals(right)
    for left_start, left_end in left_intervals:
        for right_start, right_end in right_intervals:
            if left_start <= right_end and right_start <= left_end:
                return True
    return False


def _span_row(
    node: OfficeNode,
    person_id: str,
    rule_version: str,
    latest_period: Mapping[str, str | None],
    office_profile: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    chamber = node.chamber
    ordinals = sorted(node.ordinals)
    first_token = period_token_from_ordinal(chamber, ordinals[0])
    last_token = period_token_from_ordinal(chamber, ordinals[-1])
    core_start = period_bounds(chamber, first_token)[0]
    core_end = period_bounds(chamber, last_token)[1]
    envelope_start = period_bounds(
        chamber,
        period_token_from_ordinal(
            chamber, ordinals[0] - ENVELOPE_WIDENING_REPORTING_PERIODS
        ),
    )[0]
    envelope_end = period_bounds(
        chamber,
        period_token_from_ordinal(
            chamber, ordinals[-1] + ENVELOPE_WIDENING_REPORTING_PERIODS
        ),
    )[1]
    date_precision = "REPORT_PERIOD"
    # The House source prints inclusive service dates on every admitted row.
    # When the node has complete dates, preserve those observed bounds instead
    # of replacing them with first/last quarter boundaries.  The row ids still
    # retain the full (possibly gapped) calendar for the graph's union step.
    if chamber == CHAMBER_HOUSE and node.has_complete_service_dates:
        exact = node.service_intervals
        core_start = min(start for start, _end in exact)
        core_end = max(end for _start, end in exact)
        envelope_start = core_start
        envelope_end = core_end
        date_precision = "DAY"
    contiguous = all(
        ordinals[index + 1] - ordinals[index] == 1 for index in range(len(ordinals) - 1)
    )
    # 2026-09-07.  first_period and last_period are the min and the max, so a
    # span whose observations are scattered reads as one unbroken stretch and
    # says nothing about the gaps inside it.  These three fields are the
    # observations themselves: the period ids actually seen, how many there
    # are, and the maximal runs of calendar-consecutive ones.
    #
    # The calendar is the chamber's own -- House quarters, Senate half-years --
    # and it is the SAME calendar `contiguous` above already tests against, so
    # ``len(contiguous_runs) == 1`` and ``contiguous`` are one statement made
    # twice; the verifier asserts that they agree rather than assuming it.  It
    # is also the calendar the corpus itself writes: every House period token
    # comes from quarter_token() and every Senate one from the senate_window()
    # start, so each round-trips through period_ordinal, and node.ordinals and
    # node.period_tokens are the same set counted twice.  That is why
    # observed_period_count is periods_observed by construction -- again
    # asserted by the verifier, not assumed here.
    observed_periods = [
        period_token_from_ordinal(chamber, ordinal) for ordinal in ordinals
    ]
    contiguous_runs: list[list[str]] = []
    run_start = previous = ordinals[0]
    for ordinal in ordinals[1:]:
        if ordinal == previous + 1:
            previous = ordinal
            continue
        contiguous_runs.append(
            [
                period_token_from_ordinal(chamber, run_start),
                period_token_from_ordinal(chamber, previous),
            ]
        )
        run_start = previous = ordinal
    contiguous_runs.append(
        [
            period_token_from_ordinal(chamber, run_start),
            period_token_from_ordinal(chamber, previous),
        ]
    )
    office_raws = sorted({observation.office_raw for observation in node.observations})
    titles = sorted(
        {observation.title for observation in node.observations if observation.title}
    )
    ordered = sorted(
        node.observations,
        key=lambda item: (period_ordinal(chamber, item.period), item.row_id),
    )
    title_first = next((item.title for item in ordered if item.title), None)
    title_last = next((item.title for item in reversed(ordered) if item.title), None)
    amounts = [
        observation.amount
        for observation in node.observations
        if observation.amount is not None
    ]
    amount_sum = round(sum(amounts), 2) if amounts else None
    observed_days = sum(
        (period_bounds(chamber, token)[1] - period_bounds(chamber, token)[0]).days + 1
        for token in sorted(node.period_tokens)
    )
    annualized = (
        round(amount_sum / observed_days * ANNUALIZATION_DAYS, 2)
        if amount_sum is not None and observed_days > 0
        else None
    )
    profile = office_profile[(chamber, node.office_key)]
    container_kind = profile["container_kind"]
    bioguide = profile["bioguide"]
    method = profile["method"]
    return {
        "amount_sum": amount_sum,
        "annualized_estimate": annualized,
        "canonical_eligible": False,
        "canonical_employment_promoted": False,
        "chamber": chamber,
        "contiguous": contiguous,
        "contiguous_runs": contiguous_runs,
        "container_kind": container_kind,
        "core": {
            "end_earliest": core_end.isoformat(),
            "start_latest": core_start.isoformat(),
        },
        "envelope": {
            "end_latest": envelope_end.isoformat(),
            "start_earliest": envelope_start.isoformat(),
        },
        "first_period": first_token,
        "last_period": last_token,
        "date_precision": date_precision,
        "member_bioguide": bioguide,
        "member_resolution_method": method,
        "observation_count": len(node.observations),
        "observed_period_count": len(observed_periods),
        "observed_periods": observed_periods,
        "office_key": node.office_key,
        "office_raw_examples": office_raws[:MAX_OFFICE_RAW_EXAMPLES],
        "period_kind": PERIOD_KIND[chamber],
        "periods_observed": len(node.period_tokens),
        "review_status": "REVIEW_REQUIRED",
        "rule_version": rule_version,
        "schema_id": SPAN_SCHEMA,
        "shared_employee": bool(node.shared_periods),
        "source_lane": sorted({observation.lane for observation in node.observations}),
        "source_row_ids": sorted(
            {observation.row_id for observation in node.observations}
        ),
        "spine_person_id": person_id,
        "status": (
            "current" if last_token == latest_period.get(chamber) else "departed"
        ),
        "title_first": title_first,
        "title_last": title_last,
        "titles": titles,
    }


def _majority_container_kind(observations: Sequence[Observation]) -> str:
    counts = Counter(observation.container_kind for observation in observations)
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _member_office_index(
    observations: Sequence[Observation],
    observation_to_person: Mapping[str, str],
    rule_version: str,
    office_profile: Mapping[tuple[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_office: defaultdict[tuple[str, str], list[Observation]] = defaultdict(list)
    for observation in observations:
        by_office[(observation.chamber, observation.office_key)].append(observation)
    rows: list[dict[str, Any]] = []
    for (chamber, office_key), items in sorted(by_office.items()):
        tokens = sorted(
            {item.period for item in items},
            key=lambda token: period_ordinal(chamber, token),
        )
        profile = office_profile[(chamber, office_key)]
        office_raws = list(profile["office_raws"])
        container_kind = profile["container_kind"]
        bioguide = profile["bioguide"]
        method = profile["method"]
        first_token, last_token = tokens[0], tokens[-1]
        periods = []
        for token in tokens:
            period_items = [item for item in items if item.period == token]
            amounts = [
                item.amount for item in period_items if item.amount is not None
            ]
            periods.append(
                {
                    "observation_count": len(period_items),
                    "period": token,
                    "personnel_total": round(sum(amounts), 2) if amounts else None,
                    "staff_count": len(
                        {
                            observation_to_person[item.row_id]
                            for item in period_items
                            if item.row_id in observation_to_person
                        }
                    ),
                }
            )
        rows.append(
            {
                "canonical_eligible": False,
                "canonical_employment_promoted": False,
                "chamber": chamber,
                "container_kind": container_kind,
                "first_period": first_token,
                "last_period": last_token,
                "member_bioguide": bioguide,
                "member_resolution_method": method,
                "observation_count": len(items),
                "office_key": office_key,
                "office_raw_examples": office_raws[:MAX_OFFICE_RAW_EXAMPLES],
                "period_kind": PERIOD_KIND[chamber],
                "periods": periods,
                "periods_observed": len(tokens),
                "person_count": len(
                    {
                        observation_to_person[item.row_id]
                        for item in items
                        if item.row_id in observation_to_person
                    }
                ),
                "review_status": "REVIEW_REQUIRED",
                "rule_version": rule_version,
                "schema_id": OFFICE_INDEX_SCHEMA,
            }
        )
    return rows


def _resolve_by_name_and_office(
    chamber: str,
    display_name: str,
    payee_raw: str,
    office: str,
    by_name_office_middle: Mapping[
        tuple[str, str, str, str], set[tuple[str, str | None]]
    ],
    house_key: "HouseOfficeKey",
) -> set[str]:
    key = payroll_payee_key(payee_raw) if payee_raw else None
    if key is None:
        key = display_payee_key(display_name)
    if key is None or not office:
        return set()
    office_key = (
        house_key(office) if chamber == CHAMBER_HOUSE else senate_office_key(office)
    )
    bucket = by_name_office_middle.get((chamber, office_key, key[0], key[1]), set())
    return {
        spine_id
        for spine_id, middle in bucket
        if middle_compatible(middle, key[2])
    }


def _resolve_staffer_member(
    member_display: str,
    member_index: Mapping[str, str | None],
    roster: Mapping[str, list[dict[str, Any]]],
    nicknames: Mapping[str, str],
    latest_house: str | None,
) -> tuple[str | None, str]:
    normalized = re.sub(r"\s+", " ", _ascii_fold(member_display)).strip().casefold()
    if normalized in member_index:
        bioguide = member_index[normalized]
        if bioguide is not None:
            return bioguide, "MEMBER_DISPLAY_NAME_INDEX"
    if not QUORUM_MEMBER_ROSTER_FALLBACK:
        return None, "UNRESOLVED"
    key = display_payee_key(member_display)
    if key is None:
        return None, "UNRESOLVED"
    window = None
    if latest_house is not None:
        year = period_bounds(CHAMBER_HOUSE, latest_house)[1].year
        window = (year, year)
    bioguide, _method = resolve_member_bioguide(
        key[1], key[0], roster, nicknames, window
    )
    if bioguide is None:
        return None, "UNRESOLVED"
    return bioguide, "ROSTER_STRICT_FALLBACK"


def _member_office_key_census(
    observations: Sequence[Observation],
    office_profile: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, int]:
    """R-1 acceptance measurement, restated over the emitted keys.

    For every House office whose container kind is ``member_office``, how many
    distinct members does its key cover?  Two independent definitions, both of
    which must be zero:

      * how many distinct bioguides the HOUSE LEDGER resolved on that key's rows
        -- the hard test, since it never consults Part C's own rules;
      * how many distinct (first name, surname) pairs, taken raw from the office
        string with no nickname folding, appear on that key -- the definition
        under which the v1 generation merged 104 of 955 keys.
    """

    by_key: defaultdict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        if observation.chamber == CHAMBER_HOUSE:
            by_key[observation.office_key].append(observation)
    counts: Counter = Counter()
    for office_key, items in by_key.items():
        profile = office_profile.get((CHAMBER_HOUSE, office_key), {})
        if profile.get("container_kind") != "member_office":
            continue
        counts["member_office_keys"] += 1
        counts["member_office_observations"] += len(items)
        bioguides = {
            item.ledger_member_bioguide for item in items if item.ledger_member_bioguide
        }
        names = set()
        for item in items:
            first, surname = office_member_name(CHAMBER_HOUSE, item.office_raw)
            if surname:
                names.add(((first or "").upper(), surname.upper()))
        if len(bioguides) > 1:
            counts["member_office_keys_merging_more_than_one_ledger_bioguide"] += 1
            counts["member_office_observations_in_ledger_bioguide_merged_keys"] += len(
                items
            )
        if len(names) > 1:
            counts["member_office_keys_merging_more_than_one_office_name"] += 1
            counts["member_office_observations_in_office_name_merged_keys"] += len(items)
    for key in (
        "member_office_keys_merging_more_than_one_ledger_bioguide",
        "member_office_keys_merging_more_than_one_office_name",
        "member_office_observations_in_ledger_bioguide_merged_keys",
        "member_office_observations_in_office_name_merged_keys",
    ):
        counts.setdefault(key, 0)
    return dict(counts)


def _ledger_disagreements(
    observations: Sequence[Observation],
    office_profile: Mapping[tuple[str, str], Mapping[str, Any]],
) -> dict[str, int]:
    counts: Counter = Counter()
    for observation in observations:
        profile = office_profile.get((observation.chamber, observation.office_key), {})
        if observation.ledger_office_key is not None:
            counts["office_key_present"] += 1
            if observation.ledger_office_key != observation.office_key:
                counts["office_key_disagreement"] += 1
        if observation.ledger_container_kind is not None:
            counts["container_kind_present"] += 1
            if observation.ledger_container_kind != profile.get("container_kind"):
                counts["container_kind_disagreement"] += 1
        if observation.ledger_member_bioguide is not None:
            counts["member_bioguide_present"] += 1
            if observation.ledger_member_bioguide != profile.get("bioguide"):
                counts["member_bioguide_disagreement"] += 1
    # A Counter omits a key it never incremented, which would leave a reader
    # unable to tell a measured zero from a measurement that never ran.  The
    # six are always reported.
    for key in (
        "container_kind_disagreement",
        "container_kind_present",
        "member_bioguide_disagreement",
        "member_bioguide_present",
        "office_key_disagreement",
        "office_key_present",
    ):
        counts.setdefault(key, 0)
    return dict(sorted(counts.items()))


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the Hill personnel spine.")
    parser.add_argument("--house-ledger-root", type=Path, default=None)
    # --house-pdf-candidates is deliberately absent.  The House ledger from v3
    # carries the 2009Q3-2015Q4 PDF era itself; binding that file as well would
    # admit every row of that era twice.  See the LANE_HOUSE_LEDGER note.
    parser.add_argument(
        "--senate-candidates",
        type=Path,
        action="append",
        default=None,
        help=(
            "official Senate payroll candidate file; repeat for personal-office "
            "and committee-volume corpora"
        ),
    )
    parser.add_argument("--roster-dir", type=Path, default=None)
    parser.add_argument("--nickname-table", type=Path, default=None)
    parser.add_argument("--sidecar-root", type=Path, default=None)
    parser.add_argument("--h1-matches", type=Path, default=None)
    parser.add_argument("--h2-matches", type=Path, default=None)
    parser.add_argument("--senate-matches", type=Path, default=None)
    parser.add_argument("--staff-directory", type=Path, default=None)
    parser.add_argument("--congestion", type=Path, default=None)
    parser.add_argument("--registrant-episodes", type=Path, default=None)
    parser.add_argument(
        "--name-standard",
        action="store_true",
        help=(
            "re-key the person id under fec/staffer_network/name_standard.py and "
            "emit the id map; OFF by default, and with it absent this build is "
            "byte for byte the build it was before the flag existed"
        ),
    )
    parser.add_argument(
        "--name-standard-baseline",
        type=Path,
        default=None,
        help=(
            "the generation this re-key is measured against; its receipt and "
            "spine are hash-bound and the invariants in receipt.name_standard."
            "baseline are checked against them"
        ),
    )
    parser.add_argument(
        "--name-standard-delta-report",
        type=Path,
        default=None,
        help=(
            "the read-only re-key delta report json this build's key-change "
            "histogram is asserted against (ruling B); hash-bound, and its "
            "absence is a declared failure in name-standard mode"
        ),
    )
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--generated-at", default=None)
    parser.add_argument("--rule-version", default=DEFAULT_RULE_VERSION)
    parser.add_argument("--run-id", default="unbound")
    parser.add_argument("--no-glassbox", action="store_true")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    glassbox = not args.no_glassbox
    emit_glassbox(
        glassbox,
        args.run_id,
        "run.start",
        "running",
        "hill personnel spine build started",
        detail=str(args.output_root),
    )
    try:
        result = run(args)
    except Exception as error:
        emit_glassbox(
            glassbox,
            args.run_id,
            "run.fail",
            "failed",
            "hill personnel spine build failed",
            detail=f"{type(error).__name__}: {error}",
        )
        raise
    receipt = result["receipt"]
    emit_glassbox(
        glassbox,
        args.run_id,
        "run.finish",
        "completed" if receipt["status"] == "PASS" else "failed",
        f"hill personnel spine build {receipt['status']}",
        detail=result["output_root"],
        metadata={
            "person_office_spans": receipt["counts"]["person_office_spans"],
            "spine_persons": receipt["counts"]["spine_persons"],
            "status": receipt["status"],
        },
    )
    print(f"output_root: {result['output_root']}")
    print(f"status: {receipt['status']}")
    print(f"failures: {receipt['failures']}")
    print("files:")
    for name, entry in sorted(receipt["files"].items()):
        print(
            f"  {name}: rows={entry['rows']} bytes={entry['bytes']} "
            f"sha256={entry['sha256']}"
        )
    print("counts.identity_tier_people:")
    print("  " + json.dumps(receipt["counts"]["identity_tier_people"], sort_keys=True))
    print("link_rates:")
    print("  " + json.dumps(receipt["link_rates"], sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
