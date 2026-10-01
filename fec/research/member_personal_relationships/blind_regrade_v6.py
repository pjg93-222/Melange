# -*- coding: utf-8 -*-
"""Blind re-grade kit for the 73 v6 chamber-degree records (review item P1-12).

Two independent blind passes re-grade each v6 record as a single directed
episode, actor -> target, under the SAME frozen rubric (`grading_rubric.md`)
used for the 180-pair development sample. This never grades anything itself:
`--build-kit` writes prompts + schema + batches for a grader (human or an
independent Claude Code subagent) to fill in, and `--ingest` reads the two
passes back, scores agreement against each other and against the original v6
grades, and queues disagreements for Paul.

Blinding here is allowlist projection, same discipline as `blind_grading.py`:
the packet is built by copying named-safe fields OUT of the record, so
affinity, friction, the ranges, the original rationale, neutral_evidence,
confidence, display, coverage_tiers, families, and source_urls never enter the
payload because their keys are never on the allowlist. Pass B receives its
evidence rows in reverse order -- a second, cheap form of blinding-by-
reordering, in the same spirit as `blind_grading.seeded_order` (a literal
reversal here, not a seeded shuffle, per the P1-12 spec).

This module reuses `blind_grading.py` (same directory, same frozen rubric
file) by importing its generic helpers -- IO, hashing, the mini JSON-Schema
validator, the schema-node builders, quadratic_weighted_kappa, the filename
sanitiser, the chunker, the SYSTEM/USER prompt framing, and `_glassbox_emit`
-- rather than duplicating them. Import-safety was verified before reuse:
`blind_grading.py`'s own docstring states nothing runs on import, and its only
top-level side-effecting code is guarded by `if __name__ == "__main__":` at
the bottom of the file; transitively, `fec.surfaces.glassbox_emit` also does
no I/O above the `emit()` function body. Importing THIS module is equally
inert: nothing runs, no file is read, until `main()` is entered.

THE EVIDENCE GAP (read before trusting `--build-kit`'s record count):
31 of the 73 v6 records cite an evidence_id absent from `reviewed_events.
ndjson`. A repo-wide search (every *.ndjson/*.json under
outputs/member_personal_relationships/) resolves 30 of those 31 ids to a
record in `20260910_original_work_context/graded_events.ndjson`,
`.../exchange_context.ndjson`, or `20260910_hearing_pilot/reviewed_cases.
ndjson` -- but EVERY one of those is a PRIOR REVIEWER'S PARAPHRASE OR GRADING
DECISION (`note`, `interpretation`, `evidence`/`alternative`/`decision`), not
a verbatim quotation; one id (cited by v6:cotton_welch_20231017) resolves
nowhere at all. Showing a prior judgement to a supposedly blind re-grader
would leak that judgement into the "independent" pass, so `resolve_evidence`
only ever treats `reviewed_events.ndjson` as a source of packet text. A
record with ANY unresolvable evidence_id -- fully absent, or resolvable only
as paraphrase -- is EXCLUDED from the kit outright (never a placeholder
packet: `build_packet` returns None for it) and listed in `manifest.json`
under `evidence_missing_in_repo`, which records the id, evidence_ids,
source_urls, and -- for the 30 paraphrase-only cases -- exactly what file and
what non-verbatim text the broadened search actually found, so the exclusion
is auditable rather than opaque. This shrinks the real kit to 42 of 73
records (84 prompts, not 146; 3 batches per pass, not 4) -- a data finding,
not a bug in this script.

`--build-kit-supplement` (added after the gap above was documented) goes
past the paraphrase layer to PRIMARY text for those same 31 records: the
`speeches` table row named by exchange_context.ndjson's own
`source_locator` (written at collection time, never a paraphrase field), or
the local PDF page text `fetch_hearing_pilot.py` already extracted for the
three House Oversight hearings/markups the hearing-based records cite. A
record that fully recovers gets NEW prompt files and NEW index.json/
batches.json entries appended after the existing 84/6, built with the exact
same build_packet/render_user_text/build_system_text/forbidden_word_sweep
--build-kit already uses; nothing --build-kit already wrote is ever opened
for writing again. See the "--build-kit-supplement" section below.

Two deliberate departures from blind_grading's own conventions, both forced by
this record set rather than chosen for their own sake:

* v6 record ids (e.g. ``v6:history-rollcall_civility_20171204-0``) contain a
  colon, which Windows forbids in filenames. blind_grading.py can afford to
  key its response files by the raw, unsanitised item_id because pair_ids are
  already filesystem-safe; that assumption does not hold here, so both the
  prompt path and the response path are built from the sanitised stem
  (`_safe_filename_stem`), and the raw id is carried separately as
  `item_id` in index.json/batches.json for round-tripping.
* quadratic_weighted_kappa(a, b) returns 1.0 or 0.0 when either rater shows
  zero variance (its own `den == 0` branch) rather than an explicit null.
  That reads as measured agreement/disagreement, not as an undefined
  statistic, so `qwk_or_null` below checks variance itself and only calls
  into the reused function on the side of that check where it is well-defined.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from fec.research.member_personal_relationships import blind_grading as bg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUTS = ROOT / "outputs" / "member_personal_relationships"
DEFAULT_RECORDS = OUTPUTS / "20260910_chamber_degrees_v6" / "annotations.ndjson"
DEFAULT_EVIDENCE = OUTPUTS / "20260910_full_history" / "reviewed_events.ndjson"
DEFAULT_OUT = OUTPUTS / "20260911_v6_regrade"
RUBRIC_PATH = bg.RUBRIC_PATH  # same frozen rubric file, same directory as this script

# Repo-wide search hits for the 31-of-73 evidence gap (see module docstring).
# Read-only, best-effort, diagnostic ONLY: never a source of packet text.
SECONDARY_EVIDENCE_FILES = (
    OUTPUTS / "20260910_original_work_context" / "graded_events.ndjson",
    OUTPUTS / "20260910_original_work_context" / "exchange_context.ndjson",
    OUTPUTS / "20260910_hearing_pilot" / "reviewed_cases.ndjson",
)
PARAPHRASE_FIELDS = ("note", "interpretation", "evidence", "grading_reason", "decision")

PASSES = ("A", "B")
BATCH_MAX = 19  # per-pass batch cap from the P1-12 spec

# The record-level (non-schema) fields shown per evidence row. Whitelist
# projection: nothing else on an evidence row is ever copied into a packet.
PACKET_EVIDENCE_FIELDS = ("evidence_id", "event_date", "source", "attribution", "text")

# Words that must never appear in a rendered prompt file outside the verbatim
# rubric block: the stripped v6/evidence field names plus the two blinded
# analytical dimensions Paul named explicitly for this kit.
FORBIDDEN_WORDS = ["affinity_range", "friction_range", "rationale", "neutral_evidence",
                   "coverage_tiers", "sign", "category", "model_score", "dw1", "party"]

# blind_grading.DEGREE_VALUES is ["0","1","2","3","4","unassessable"]; a range
# endpoint is only ever recorded when the degree itself is NOT unassessable
# (the whole *_range field is null in that case, per the P1-12 spec), so range
# endpoints are restricted to the four numeric strings.
NUMERIC_DEGREES = bg.DEGREE_VALUES[:-1]


class RegradeKitError(Exception):
    """An input violates an assumption this builder depends on. Raised loudly
    rather than silently guessed around, matching blind_grading's SchemaDrift."""


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def _degree_range_schema():
    return {"anyOf": [{"type": "null"},
                      {"type": "array", "items": bg._enum(NUMERIC_DEGREES)}]}


def record_grade_schema():
    """Adapted from blind_grading.pair_grade_schema()/direction_schema() to a
    single directed episode. additionalProperties False and every property
    required, via the same `_obj` builder blind_grading uses."""
    return bg._obj({
        "affinity": bg._enum(bg.DEGREE_VALUES, "affinity degree 0-4, or unassessable"),
        "friction": bg._enum(bg.DEGREE_VALUES, "friction degree 0-4, or unassessable"),
        "affinity_range": _degree_range_schema(),
        "friction_range": _degree_range_schema(),
        "neutral_evidence": {
            "type": "boolean",
            "description": "true ONLY with affirmative evidence of routine, uninvested "
                           "contact; never the default for silence or courtesy alone"},
        "closeness_trust_evidence": {
            "type": "array", "items": bg._enum(bg.INDICATORS),
            "description": "descriptive closeness/trust indicators actually shown by cited text"},
        "ritual_courtesy_only": {
            "type": "boolean",
            "description": "true when every warm expression cited is ceremonial courtesy only"},
        "cited_evidence_ids": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string", "description": "<=120 words, describes the cited text"},
    })


def validate_record_grade(obj, schema=None):
    """bg.validate_against_schema plus the two checks the mini-validator's
    supported subset (type/enum/properties/required/additionalProperties/
    items/anyOf) cannot express: exact range length, and the word cap."""
    schema = schema if schema is not None else record_grade_schema()
    errors = bg.validate_against_schema(obj, schema)
    if isinstance(obj, dict):
        for dim in ("affinity", "friction"):
            rng = obj.get("%s_range" % dim)
            if isinstance(rng, list) and len(rng) != 2:
                errors.append("$.%s_range must have exactly 2 items, got %d" % (dim, len(rng)))
        rationale = obj.get("rationale")
        if isinstance(rationale, str) and len(rationale.split()) > 120:
            errors.append("$.rationale exceeds 120 words (%d)" % len(rationale.split()))
    return errors


# ---------------------------------------------------------------------------
# loading -- fail loudly on drift, same ethic as blind_grading's loaders
# ---------------------------------------------------------------------------

def load_records(path):
    rows = bg.read_ndjson(path)
    seen = set()
    for row in rows:
        rid = row.get("id")
        if not rid:
            raise RegradeKitError("record missing 'id': %r" % (row,))
        if rid in seen:
            raise RegradeKitError("duplicate record id: %s" % rid)
        seen.add(rid)
        names = row.get("names")
        if not (isinstance(names, list) and len(names) == 2):
            raise RegradeKitError("%s: 'names' must have exactly 2 entries, got %r" % (rid, names))
        if not row.get("actor") or not row.get("target"):
            raise RegradeKitError("%s: missing actor/target bioguide" % rid)
        if not row.get("evidence_ids"):
            raise RegradeKitError("%s: no evidence_ids; every v6 record is expected to cite "
                                  "at least one" % rid)
    return rows


def load_evidence_index(path):
    """Primary, verbatim-text-bearing evidence source (reviewed_events.ndjson
    ONLY). See module docstring: this is deliberately the one and only source
    `resolve_evidence` will accept."""
    by_id = {}
    for row in bg.read_ndjson(path):
        eid = row.get("evidence_id")
        if eid:
            by_id[eid] = row
    return by_id


def load_secondary_paraphrase_index(paths=None):
    """Best-effort index built from the repo-wide search for the 31-of-73
    evidence gap. NEVER used as packet text (see module docstring) -- only to
    make manifest.json honest about what the broadened search actually found
    for a record that still gets excluded.

    `paths` resolves against the CURRENT value of the module-level
    SECONDARY_EVIDENCE_FILES at call time (default is None, not the constant
    itself) so a caller -- or a test -- that reassigns the module constant is
    actually respected; binding the constant as the parameter's default would
    freeze it at function-definition time instead."""
    if paths is None:
        paths = SECONDARY_EVIDENCE_FILES
    index = {}
    for path in paths:
        path = Path(path)
        if not path.exists():
            continue
        for row in bg.read_ndjson(path):
            rid = row.get("id") or row.get("evidence_id")
            if not rid or rid in index:
                continue
            paraphrase = next((row[k] for k in PARAPHRASE_FIELDS if row.get(k)), None)
            if paraphrase is not None:
                index[rid] = {"file": str(path), "paraphrase": paraphrase}
    return index


def safe_stem(record_id):
    return bg._safe_filename_stem(record_id)


# ---------------------------------------------------------------------------
# packet construction (allowlist projection) and rendering
# ---------------------------------------------------------------------------

def resolve_evidence(evidence_id, evidence_by_id):
    """Whitelisted row, or None when no VERBATIM text exists for this
    evidence_id in reviewed_events.ndjson -- the only file the repo-wide
    search found to carry verbatim quoted text at all (see module docstring
    and load_secondary_paraphrase_index)."""
    row = evidence_by_id.get(evidence_id)
    if row is None:
        return None
    return {k: row.get(k) for k in PACKET_EVIDENCE_FIELDS}


def build_packet(record, evidence_by_id, pass_tag):
    """Whitelist projection for ONE directed episode. Only the keys assembled
    here are ever copied out of `record`; affinity, friction, the ranges, the
    original rationale, neutral_evidence, confidence, display, coverage_tiers,
    families, and source_urls are dropped by omission, per P1-12. `names` is
    ordered [actor_name, target_name] in this record set (verified against
    actor/target bioguides on a sample where `pair` -- a separately sorted,
    undirected key -- disagreed with actor/target order; `names` tracked
    actor/target, not `pair`, every time).

    Returns (packet_or_None, unresolved_evidence_ids). ANY unresolvable
    evidence_id -- absent everywhere, or resolvable only as a paraphrase --
    excludes the WHOLE record (packet is None): a record whose citation list
    is incomplete should not be shown with a silently-shrunk evidence set."""
    actor_name, target_name = record["names"][0], record["names"][1]
    ordered_ids = list(record["evidence_ids"])
    if pass_tag == "B":
        ordered_ids = list(reversed(ordered_ids))
    evidence_rows, unresolved = [], []
    for eid in ordered_ids:
        row = resolve_evidence(eid, evidence_by_id)
        if row is None:
            unresolved.append(eid)
        else:
            evidence_rows.append(row)
    if unresolved:
        return None, unresolved
    packet = {
        "record_id": record["id"],
        "pass": pass_tag,
        "actor_name": actor_name,
        "target_name": target_name,
        "actor_bioguide": record["actor"],
        "target_bioguide": record["target"],
        "chamber": record.get("chamber"),
        "episode_date": record.get("date"),
        "venue": record.get("venue"),
        "evidence": evidence_rows,
    }
    return packet, []


def render_user_text(packet):
    n = len(packet["evidence"])
    lines = [
        "RECORD: %s" % packet["record_id"],
        "PASS: %s" % packet["pass"],
        "DIRECTION: %s -> %s (grade this direction only)" % (packet["actor_name"],
                                                              packet["target_name"]),
        "ACTOR: %s (bioguide %s)" % (packet["actor_name"], packet["actor_bioguide"]),
        "TARGET: %s (bioguide %s)" % (packet["target_name"], packet["target_bioguide"]),
        "CHAMBER: %s" % packet["chamber"],
        "EPISODE DATE: %s" % packet["episode_date"],
        "VENUE: %s" % packet["venue"],
        "",
        "=" * 72,
        "EVIDENCE (%d row%s)" % (n, "" if n == 1 else "s"),
        "=" * 72,
    ]
    for ev in packet["evidence"]:
        lines.append("")
        lines.append("[%s] %s | source: %s | attribution: %s"
                     % (ev["evidence_id"], ev["event_date"], ev["source"], ev["attribution"]))
        lines.append(str(ev["text"]).strip() if ev["text"] is not None else "(no text)")
    lines.append("")
    lines.append("=" * 72)
    lines.append("Grade this one direction. Return only the JSON object the response schema "
                 "requires.")
    return "\n".join(lines)


def build_system_text(rubric_text):
    """Deliberately never names a record_grade_schema.json key (see
    FORBIDDEN_WORDS): the schema itself, not this prose, tells a grader which
    JSON keys to produce."""
    return (rubric_text + "\n\n---\n\n"
            "You are one blind reviewer performing an independent re-grade of a single "
            "directed episode, actor -> target, for a blind re-grade check of a set of "
            "already-graded records. Apply the rubric above. Decide the affinity degree and "
            "the friction degree for this direction only, each independently allowed to be "
            "'unassessable' when the evidence does not support a degree on that axis -- "
            "absence of evidence is never a 0. For each degree you do assign a number to, also "
            "give the low-to-high span of interpretations the evidence still supports, using "
            "null instead of a span when the degree itself is unassessable. Say whether the "
            "evidence affirmatively shows an ordinary, routine, emotionally uninvested contact "
            "between these two people -- never as a default for silence or for courtesy alone. "
            "List which of the rubric's closeness-and-trust indicators the cited text actually "
            "shows, and say whether every warm expression cited is ceremonial courtesy only. "
            "Cite the evidence ids you relied on exactly as printed below; never invent one. "
            "Add a short prose explanation, no more than 120 words, describing what the cited "
            "text shows. Decide everything from the packet below, never from memory of these "
            "two people. Return only the JSON object the response schema requires.\n")


# ---------------------------------------------------------------------------
# forbidden-word sweep
# ---------------------------------------------------------------------------

def forbidden_word_sweep(prompt_dir, rubric_text, words=FORBIDDEN_WORDS):
    """Scans every written prompt file for `words`, case-insensitive, on word
    boundaries, with the one legitimate verbatim occurrence of the rubric text
    removed first. No other carve-out: a hit inside a verbatim evidence quote
    is reported exactly like a hit anywhere else, honestly, per P1-12 (this is
    not blind_grading's assert_blind, which exempts excerpts by design)."""
    hits = []
    files = sorted(Path(prompt_dir).rglob("*.md"))
    for path in files:
        text = path.read_text(encoding="utf-8")
        scaffold = text.replace(rubric_text, " ")
        lowered = scaffold.lower()
        found = sorted({w for w in words if re.search(r"\b%s\b" % re.escape(w.lower()), lowered)})
        if found:
            hits.append({"file": str(path), "words": found})
    return {"ok": not hits, "hits": hits, "files_scanned": len(files)}


# ---------------------------------------------------------------------------
# --build-kit
# ---------------------------------------------------------------------------

def build_batches(items, batch_max=BATCH_MAX, start_at=None, prefix="regrade"):
    """`start_at`, when given, maps pass -> the last batch NUMBER already
    used for that pass (e.g. {"A": 3, "B": 3} after a kit with 3 batches per
    pass): numbering then continues from start_at[pass]+1 instead of 1, so
    build_kit_supplement's new batches never collide with build_kit's
    (regrade__A__0004.. rather than a second regrade__A__0001..). Absent or
    empty reproduces build_kit's original from-1 numbering exactly.

    `prefix` names the batch_id family (default "regrade", matching every
    batch_id build_kit/build_kit_supplement have ever written); a caller
    that passes a different prefix -- e.g. build_kit_retext's
    "regrade_retext" -- starts a distinct, non-colliding batch_id namespace
    without changing this function's behaviour for either existing caller,
    both of which rely on the default."""
    start_at = start_at or {}
    by_pass = {}
    for item in items:
        by_pass.setdefault(item["pass"], []).append(item)
    batches = []
    for pass_tag in sorted(by_pass):
        group = sorted(by_pass[pass_tag], key=lambda it: it["item_id"])
        first = start_at.get(pass_tag, 0) + 1
        for i, chunk in enumerate(bg._chunk(group, batch_max), first):
            batches.append({
                "batch_id": "%s__%s__%04d" % (prefix, pass_tag, i),
                "pass": pass_tag,
                "item_count": len(chunk),
                "schema_path": chunk[0]["schema_path"],
                "items": [{"item_id": it["item_id"], "prompt_path": it["prompt_path"],
                          "response_path": it["response_path"]} for it in chunk],
            })
    return batches


def build_kit(out_dir, records_path, evidence_path, rubric_text, log=print):
    out_dir = Path(out_dir).resolve()
    kit_dir = out_dir / "grading_kit"
    prompts_root = kit_dir / "prompts"
    responses_root = kit_dir / "responses"
    for pass_tag in PASSES:
        (prompts_root / pass_tag).mkdir(parents=True, exist_ok=True)
        (responses_root / pass_tag).mkdir(parents=True, exist_ok=True)

    records = load_records(records_path)
    evidence_by_id = load_evidence_index(evidence_path)
    secondary = load_secondary_paraphrase_index()
    schema = record_grade_schema()
    schema_path = kit_dir / "record_grade_schema.json"
    bg.write_json(schema_path, schema)

    system_text = build_system_text(rubric_text)

    items = []
    stems = {}
    excluded = []
    for record in sorted(records, key=lambda r: r["id"]):
        packet_a, unresolved = build_packet(record, evidence_by_id, "A")
        if unresolved:
            entry = {"record_id": record["id"], "evidence_ids": record["evidence_ids"],
                     "source_urls": record.get("source_urls", []), "unresolved_evidence_ids": []}
            for eid in unresolved:
                hit = secondary.get(eid)
                if hit:
                    entry["unresolved_evidence_ids"].append({
                        "evidence_id": eid, "status": "found_only_as_paraphrase_elsewhere",
                        "resolved_in_file": hit["file"],
                        "paraphrase_not_used_as_evidence": hit["paraphrase"]})
                else:
                    entry["unresolved_evidence_ids"].append({
                        "evidence_id": eid, "status": "not_found_anywhere_searched"})
            excluded.append(entry)
            continue

        stem = safe_stem(record["id"])
        prior = stems.get(stem)
        if prior is not None:
            raise RegradeKitError("filename collision after sanitising ids: %r and %r both -> %s"
                                  % (prior, record["id"], stem))
        stems[stem] = record["id"]
        for pass_tag in PASSES:
            packet = packet_a if pass_tag == "A" else build_packet(record, evidence_by_id,
                                                                    pass_tag)[0]
            user_text = render_user_text(packet)
            full_text = bg.full_prompt_text(system_text, user_text)
            prompt_path = prompts_root / pass_tag / ("%s.md" % stem)
            prompt_path.write_text(full_text, encoding="utf-8", newline="\n")
            response_path = responses_root / pass_tag / ("%s.json" % stem)
            items.append({"item_id": record["id"], "pass": pass_tag,
                          "prompt_path": str(prompt_path), "schema_path": str(schema_path),
                          "response_path": str(response_path)})

    items.sort(key=lambda it: (it["item_id"], it["pass"]))
    meta = {
        "records_total": len(records),
        "records_included": len(records) - len(excluded),
        "records_excluded": len(excluded),
        "items_total": len(items),
        "passes": list(PASSES),
        "batch_max": BATCH_MAX,
    }
    index_path = kit_dir / "index.json"
    bg.write_json(index_path, {"meta": meta, "items": items})

    batches = build_batches(items)
    batches_path = kit_dir / "batches.json"
    bg.write_json(batches_path, {"meta": {"batch_count": len(batches), "batch_max": BATCH_MAX},
                                 "batches": batches})

    manifest = {
        "records_total": len(records),
        "records_included_in_kit": len(records) - len(excluded),
        "records_excluded": len(excluded),
        "evidence_missing_in_repo": excluded,
    }
    manifest_path = kit_dir / "manifest.json"
    bg.write_json(manifest_path, manifest)

    sweep = forbidden_word_sweep(prompts_root, rubric_text)
    log("build-kit: %d records total, %d included (%d items) / %d excluded, %d batches; "
       "forbidden-key sweep %s (%d files)"
       % (len(records), meta["records_included"], len(items), len(excluded), len(batches),
          "CLEAN" if sweep["ok"] else "HITS FOUND", sweep["files_scanned"]))

    return {"kit_dir": str(kit_dir), "index_path": str(index_path),
           "batches_path": str(batches_path), "schema_path": str(schema_path),
           "manifest_path": str(manifest_path), "meta": meta, "batch_count": len(batches),
           "sweep": sweep, "excluded_count": len(excluded)}


# ---------------------------------------------------------------------------
# --build-kit-supplement: primary-source recovery for the 31 v6 records
# excluded from --build-kit (see "THE EVIDENCE GAP" above). Every one of
# those 31 cites an evidence_id that graded_events.ndjson / exchange_
# context.ndjson / reviewed_cases.ndjson resolves only as a PRIOR REVIEWER'S
# PARAPHRASE (30 of them) or not at all (v6:cotton_welch_20231017's
# `source_row_153803_and_original_S5030_S5031`). This section never reads
# those paraphrase fields (PARAPHRASE_FIELDS stays the sole authority on
# what to exclude) -- it goes past them to the PRIMARY text: either the
# `speeches` table row named by exchange_context.ndjson's own
# `source_locator` (written at collection time by
# data.extract_candidates / exchange_context_audit.py), or the local PDF
# page text `fetch_hearing_pilot.py` already extracted for the three House
# Oversight hearings/markups these records cite.
#
# A record that fully recovers gets NEW prompt files / index.json entries /
# batches.json batches, built with the exact same build_packet/
# render_user_text/build_system_text/forbidden_word_sweep --build-kit
# already uses -- so the packet layout and the rubric bytes shown to a
# grader are identical by construction, never by re-implementation. Nothing
# already written by --build-kit is ever opened for writing again: new
# record ids always land in new files (they could not have collided with
# the kit's existing stems, since --build-kit only ever excluded them for
# lacking verbatim evidence, never for a filename clash), and index.json /
# batches.json are rewritten from the parsed structure with every existing
# entry first, followed only by new entries appended after.
# ---------------------------------------------------------------------------

SOCIAL_MEDIA_DB = ROOT / "social_media.db"
HEARING_SOURCES_DIR = OUTPUTS / "20260910_hearing_pilot" / "sources"
DEFAULT_LOCATOR_PATH = OUTPUTS / "20260910_original_work_context" / "exchange_context.ndjson"
DEFAULT_ATTRIBUTION_PATH = OUTPUTS / "20260910_hearing_pilot" / "reviewed_cases.ndjson"

# The three hearing/markup/organizational-meeting transcripts recovered here
# are all House Oversight Committee proceedings -- the same document TYPE
# the GPO eventually publishes under its CHRG (Congressional Hearing)
# series (one of the three, comer_moskowitz_20231114, already carries a
# CHRG serial: CHRG-118hhrg54309). `speeches.source` only ever holds
# 'CREC', 'INTERVIEW' or 'CHRG' elsewhere in this lane
# (systematic_encounters.py); reusing 'CHRG' here for all three keeps that
# vocabulary closed at 3 values instead of inventing a 4th tag for what is,
# substantively, the same kind of document.
HEARING_SOURCE_TAG = "CHRG"

_SQLITE_LOCATOR_RE = re.compile(r"^sqlite:(?P<db>[^#]+)#(?P<table>[^/]+)/rowid=(?P<rowid>\d+)$")
_REVIEW_ID_RE = re.compile(r"^(?:new_)?review_(\d+)$")
_SOURCE_ROW_TOKEN_RE = re.compile(r"(?:^|_)source_row_(\d+)(?:_|$)")


def parse_sqlite_locator(locator):
    """Parses the canonical `sqlite:<db>#<table>/rowid=<n>` locator string
    this lane writes at collection time (data.extract_candidates,
    exchange_context_audit.py) -- e.g.
    'sqlite:social_media.db#speeches/rowid=19040'. Returns
    {"db": "social_media.db", "table": "speeches", "rowid": 19040}, or None
    for anything that is not exactly that shape (wrong scheme, missing
    rowid, non-numeric rowid, not a string, ...): a locator this script
    cannot parse must never be silently treated as absent evidence."""
    if not isinstance(locator, str):
        return None
    m = _SQLITE_LOCATOR_RE.match(locator.strip())
    if not m:
        return None
    return {"db": m.group("db"), "table": m.group("table"), "rowid": int(m.group("rowid"))}


def resolve_rowid(evidence_id, locator_row=None):
    """Best-effort `speeches` rowid for one evidence_id, cheapest and most
    specific rule first:

    1. an explicit `source_locator.sqlite` string on the SECONDARY row
       itself, parsed by `parse_sqlite_locator` -- never guessed;
    2. this lane's own `review_N` / `new_review_N` id-naming convention
       (exchange_context_audit.py: ``id='review_'+str(source_rowid)``), for
       when rule 1 has nothing to read;
    3. a bare `source_row_N` token inside the evidence_id itself -- the one
       id in this record set (v6:cotton_welch_20231017's own
       `source_row_153803_and_original_S5030_S5031`) that was never written
       to graded_events.ndjson, exchange_context.ndjson OR
       reviewed_cases.ndjson, so rules 1-2 have no row to read at all, yet
       the id plainly names its own source_rowid.

    Returns an int, or None if none of the three rules match."""
    if locator_row is not None:
        loc = locator_row.get("source_locator")
        sqlite_str = loc.get("sqlite") if isinstance(loc, dict) else loc
        parsed = parse_sqlite_locator(sqlite_str)
        if parsed:
            return parsed["rowid"]
    m = _REVIEW_ID_RE.match(evidence_id)
    if m:
        return int(m.group(1))
    m = _SOURCE_ROW_TOKEN_RE.search(evidence_id)
    if m:
        return int(m.group(1))
    return None


def fetch_sqlite_row(rowid, db_path=None):
    """Read-only fetch of one `speeches` row by rowid (mode=ro, same access
    pattern data.extract_candidates already uses). Opens and closes its own
    connection per call -- this runs at most ~19 times per
    --build-kit-supplement invocation, so that cost is immaterial next to
    the safety of never holding the database open across calls. Returns
    None (never raises) when the rowid does not exist, so a caller can log
    that as a specific still_missing reason."""
    db_path = Path(db_path) if db_path else SOCIAL_MEDIA_DB
    con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        con.execute("PRAGMA query_only=ON")
        row = con.execute(
            "SELECT member, date, source, chamber, package, text FROM speeches WHERE rowid=?",
            (rowid,)).fetchone()
    finally:
        con.close()
    if row is None:
        return None
    member, date, source, chamber, package, text = row
    return {"rowid": rowid, "member": member, "date": date, "source": source,
           "chamber": chamber, "package": package, "text": text}


def fetch_pdf_pages_text(source_id, pages, sources_dir=None):
    """Exact page text `fetch_hearing_pilot.py` already extracted to
    `<source_id>.pages.json` (pypdf `PdfReader`, one {"pdf_page", "text"}
    row per physical page, 1-indexed) -- this never re-parses the PDF
    itself, only the extract already on disk. Joined in the same
    "[PDF PAGE N]\\n<text>" shape fetch_hearing_pilot.py already writes to
    its own *.txt sibling, so a multi-page excerpt reads identically here
    and there. Raises RegradeKitError (fail loudly, same ethic as
    load_records) if the extract is missing or a requested page is not in
    it -- never silently drops a page. Returns (text, pages_path)."""
    sources_dir = Path(sources_dir) if sources_dir else HEARING_SOURCES_DIR
    pages_path = sources_dir / ("%s.pages.json" % source_id)
    if not pages_path.exists():
        raise RegradeKitError("no local PDF page extract for source_id=%r (looked for %s)"
                              % (source_id, pages_path))
    by_page = {p["pdf_page"]: p["text"]
              for p in json.loads(pages_path.read_text(encoding="utf-8"))}
    missing = [p for p in pages if p not in by_page]
    if missing:
        raise RegradeKitError("%s: page(s) %r not present in %s" % (source_id, missing, pages_path))
    text = "\n\n".join("[PDF PAGE %d]\n%s" % (p, by_page[p]) for p in pages)
    return text, pages_path


def load_locator_index(path=None):
    """Authoritative locator source for the evidence-missing v6 records that
    still have a secondary row: exchange_context.ndjson's own
    `source_locator` / `source_family` / `date` / `actor_name` fields,
    written at collection time. Deliberately never reads `interpretation` or
    any other PARAPHRASE_FIELDS-listed key from this file -- those stay
    excluded on principle, not merely unused."""
    path = Path(path) if path else DEFAULT_LOCATOR_PATH
    index = {}
    if path.exists():
        for row in bg.read_ndjson(path):
            rid = row.get("id")
            if rid:
                index[rid] = {"source_locator": row.get("source_locator"),
                              "source_family": row.get("source_family"),
                              "date": row.get("date"), "actor_name": row.get("actor_name")}
    return index


def load_attribution_index(path=None):
    """reviewed_cases.ndjson's own factual `attribution` tag for the
    hearing-based records (e.g. 'direct_reply_sequence',
    'quotation_of_another_speaker', 'chair_enforcing_procedure') --
    `attribution` is one of the fields evidence packets are allowed to show
    (PACKET_EVIDENCE_FIELDS already includes it for every record in the
    kit), never a grading judgement."""
    path = Path(path) if path else DEFAULT_ATTRIBUTION_PATH
    index = {}
    if path.exists():
        for row in bg.read_ndjson(path):
            rid = row.get("id")
            if rid and row.get("attribution"):
                index[rid] = {"attribution": row["attribution"]}
    return index


def recover_one(evidence_id, locator_row, attribution_row=None, db_path=None, sources_dir=None):
    """One evidence_id -> (evidence_row_or_None, why_missing_or_None,
    bookkeeping_or_None).

    `evidence_row`, when not None, is shaped exactly like a
    reviewed_events.ndjson row restricted to PACKET_EVIDENCE_FIELDS, so
    resolve_evidence/build_packet accept it completely unchanged.
    `bookkeeping` is {"locator", "source_file", "chars"} for manifest.json's
    `recovered` entry -- never part of the packet itself."""
    loc = (locator_row or {}).get("source_locator")
    pdf_pages = loc.get("pdf_pages") if isinstance(loc, dict) else None
    if pdf_pages:
        source_id = (locator_row or {}).get("source_family")
        if not source_id:
            return None, "source_locator has pdf_pages but no source_family to name the PDF", None
        try:
            text, pages_path = fetch_pdf_pages_text(source_id, pdf_pages, sources_dir)
        except RegradeKitError as exc:
            return None, str(exc), None
        attribution = (attribution_row or {}).get("attribution") or "direct_speaker"
        row = {"evidence_id": evidence_id, "event_date": locator_row.get("date"),
              "source": HEARING_SOURCE_TAG, "attribution": attribution, "text": text}
        pages_str = ",".join(str(p) for p in pdf_pages)
        try:
            rel = pages_path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            rel = str(pages_path)
        bookkeeping = {"locator": "pdf:%s#pages=%s" % (rel, pages_str),
                       "source_file": str(pages_path), "chars": len(text)}
        return row, None, bookkeeping

    rowid = resolve_rowid(evidence_id, locator_row)
    if rowid is None:
        return None, "no sqlite rowid or pdf_pages locator resolvable for this evidence_id", None
    db_row = fetch_sqlite_row(rowid, db_path)
    if db_row is None:
        return None, "rowid %d resolved from its locator but is absent from speeches" % rowid, None
    row = {"evidence_id": evidence_id, "event_date": db_row["date"], "source": db_row["source"],
          "attribution": "direct_speaker", "text": db_row["text"]}
    bookkeeping = {"locator": "sqlite:social_media.db#speeches/rowid=%d" % rowid,
                  "source_file": str(db_path or SOCIAL_MEDIA_DB), "chars": len(db_row["text"])}
    return row, None, bookkeeping


def recover_missing_evidence(manifest, locator_index, attribution_index=None,
                             db_path=None, sources_dir=None):
    """Walks manifest["evidence_missing_in_repo"] (the exact structure
    --build-kit already writes) and tries to recover verbatim primary text
    for every still-unresolved evidence_id. Returns (recovered_by_id,
    recovered_log, still_missing_log): `recovered_by_id` is ready to merge
    straight into an evidence_by_id dict for build_packet."""
    attribution_index = attribution_index or {}
    recovered, recovered_log, still_missing = {}, [], []
    for entry in manifest.get("evidence_missing_in_repo", []):
        record_id = entry["record_id"]
        for unresolved in entry.get("unresolved_evidence_ids", []):
            eid = unresolved["evidence_id"]
            row, why, bookkeeping = recover_one(eid, locator_index.get(eid),
                                                attribution_index.get(eid), db_path, sources_dir)
            if row is None:
                still_missing.append({"record_id": record_id, "evidence_id": eid, "why": why})
            else:
                recovered[eid] = row
                recovered_log.append(dict({"record_id": record_id, "evidence_id": eid}, **bookkeeping))
    return recovered, recovered_log, still_missing


def build_kit_supplement(out_dir, records_path, evidence_path, rubric_text, log=print,
                         locator_path=None, attribution_path=None, db_path=None, sources_dir=None):
    """Additive companion to build_kit. Recovers verbatim primary-source
    text for records --build-kit excluded (manifest.json's
    evidence_missing_in_repo) and, for every one that fully resolves, writes
    NEW prompt files / index.json items / batches.json batches -- reusing
    build_packet/render_user_text/build_system_text/forbidden_word_sweep
    unchanged, so the packet layout and rubric bytes match --build-kit's
    kit exactly. index.json and batches.json are rewritten with every
    existing entry first, then the new ones appended; no existing prompt or
    response file is ever opened for writing."""
    out_dir = Path(out_dir).resolve()
    kit_dir = out_dir / "grading_kit"
    manifest_path = kit_dir / "manifest.json"
    index_path = kit_dir / "index.json"
    batches_path = kit_dir / "batches.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    batches_data = json.loads(batches_path.read_text(encoding="utf-8"))

    records_by_id = {r["id"]: r for r in load_records(records_path)}
    evidence_by_id = load_evidence_index(evidence_path)
    locator_index = load_locator_index(locator_path)
    attribution_index = load_attribution_index(attribution_path)
    recovered, recovered_log, still_missing = recover_missing_evidence(
        manifest, locator_index, attribution_index, db_path, sources_dir)
    merged_evidence = dict(evidence_by_id)
    merged_evidence.update(recovered)

    existing_stems = {safe_stem(it["item_id"]) for it in index_data["items"]}
    schema_path = (Path(index_data["items"][0]["schema_path"]) if index_data["items"]
                  else kit_dir / "record_grade_schema.json")
    system_text = build_system_text(rubric_text)

    new_items = []
    recovered_record_ids = set()
    for entry in sorted(manifest.get("evidence_missing_in_repo", []), key=lambda e: e["record_id"]):
        record_id = entry["record_id"]
        record = records_by_id.get(record_id)
        if record is None:
            still_missing.append({"record_id": record_id, "evidence_id": None,
                                  "why": "record id not found in %s" % records_path})
            continue
        packet_a, unresolved = build_packet(record, merged_evidence, "A")
        if unresolved:
            for eid in unresolved:
                if not any(m["record_id"] == record_id and m["evidence_id"] == eid
                          for m in still_missing):
                    still_missing.append({"record_id": record_id, "evidence_id": eid,
                                          "why": "still unresolved when building the supplement "
                                                 "packet (not recovered, and absent from "
                                                 "reviewed_events.ndjson)"})
            continue
        stem = safe_stem(record_id)
        if stem in existing_stems:
            raise RegradeKitError("supplement stem collision with an existing kit item: %s" % record_id)
        existing_stems.add(stem)
        for pass_tag in PASSES:
            packet = packet_a if pass_tag == "A" else build_packet(record, merged_evidence, pass_tag)[0]
            user_text = render_user_text(packet)
            full_text = bg.full_prompt_text(system_text, user_text)
            prompt_path = kit_dir / "prompts" / pass_tag / ("%s.md" % stem)
            prompt_path.write_text(full_text, encoding="utf-8", newline="\n")
            response_path = kit_dir / "responses" / pass_tag / ("%s.json" % stem)
            new_items.append({"item_id": record_id, "pass": pass_tag,
                              "prompt_path": str(prompt_path), "schema_path": str(schema_path),
                              "response_path": str(response_path)})
        recovered_record_ids.add(record_id)

    new_items.sort(key=lambda it: (it["item_id"], it["pass"]))
    last_batch_num = {}
    for b in batches_data["batches"]:
        n = int(b["batch_id"].rsplit("__", 1)[-1])
        last_batch_num[b["pass"]] = max(last_batch_num.get(b["pass"], 0), n)
    new_batches = build_batches(new_items, start_at=last_batch_num)

    index_data["items"] = list(index_data["items"]) + new_items
    bg.write_json(index_path, index_data)

    batches_data["batches"] = list(batches_data["batches"]) + new_batches
    batches_data["meta"]["batch_count"] = len(batches_data["batches"])
    bg.write_json(batches_path, batches_data)

    manifest["recovered"] = sorted(recovered_log, key=lambda r: (r["record_id"], r["evidence_id"]))
    manifest["still_missing"] = sorted(still_missing,
                                       key=lambda r: (r["record_id"], r["evidence_id"] or ""))
    bg.write_json(manifest_path, manifest)

    sweep = forbidden_word_sweep(kit_dir / "prompts", rubric_text)
    log("build-kit-supplement: %d recovered / %d still missing; %d new items in %d new batches; "
       "forbidden-key sweep %s (%d files)"
       % (len(recovered_record_ids),
          len({m["record_id"] for m in manifest["still_missing"]}),
          len(new_items), len(new_batches), "CLEAN" if sweep["ok"] else "HITS FOUND",
          sweep["files_scanned"]))

    return {"kit_dir": str(kit_dir), "index_path": str(index_path), "batches_path": str(batches_path),
           "manifest_path": str(manifest_path), "recovered_records": len(recovered_record_ids),
           "recovered": manifest["recovered"], "still_missing": manifest["still_missing"],
           "new_items": len(new_items), "new_batches": [b["batch_id"] for b in new_batches],
           "sweep": sweep}


# ---------------------------------------------------------------------------
# --build-kit-retext: LOCAL-ONLY recovery for evidence rows that resolve in
# reviewed_events.ndjson (so build_packet never excludes their record) but
# whose row has no `text` key at all -- render_user_text prints these as the
# literal string "(no text)" (see its `if ev["text"] is not None else
# "(no text)"` branch). These are a different gap than build_kit_supplement's
# 31-record "evidence_missing_in_repo" list above: a "(no text)" record was
# never excluded from the kit -- its evidence_id IS in reviewed_events.ndjson,
# just without verbatim text, only an external source_urls citation (a CNN
# interview segment, a floor speech, a press interview, ...).
#
# This section never touches reviewed_events.ndjson and never reads any
# PARAPHRASE_FIELDS-style reviewer judgement -- the ONLY text it will ever
# put in a packet is a `speeches.text` value fetched read-only, by rowid,
# from social_media.db, mechanically trimmed by trim_evidence_text below.
#
# Matching a "(no text)" row to a `speeches` row is a two-rule, single-
# candidate-only procedure (classify_source_urls + match_local_speech):
#   1. an interview/transcript row's source_urls includes an exact
#      https://transcripts.cnn.com/... URL -- `speeches.package` for CNN
#      transcript rows IS that URL verbatim, but one segment holds one row
#      PER SPEAKER, so the candidate set is narrowed to `member` == the
#      record's own actor name, and, only when that alone is not already a
#      single row, further to rows whose text mentions the target's surname;
#   2. a CREC floor-proceedings row's source_urls includes a
#      .../CREC-YYYY-MM-DD/pdf/CREC-YYYY-MM-DD[-house|-senate].pdf URL --
#      `speeches.package` is "CREC-YYYY-MM-DD"; the same member-then-surname
#      narrowing applies.
# A row is "recovered" only when exactly one candidate survives; more than
# one is "ambiguous" (candidate count recorded, never guessed at); zero, or
# a source_urls domain neither rule recognises (a member's own .senate.gov/
# .house.gov page, a plain news article, a C-SPAN program page, a magazine
# feature -- none of these is a document type `speeches` was ever built
# from), is reported "no local copy".
#
# A single-candidate SYNTACTIC match is still not proof the row is ABOUT the
# cited episode: `speeches` interview rows are per-topic soundbites, not
# full transcripts, so the same speaker can have exactly one row on the same
# show/date that is a completely different news item. RETEXT_REJECTED_MATCHES
# records the one case this task's own read-only investigation found and
# rejected on that basis (see its docstring) -- an explicit, auditable
# override, not a silent skip.
# ---------------------------------------------------------------------------

RETEXT_MAX_CHARS = 6000
RETEXT_TRIM_MARKER = "[trimmed to name-bearing paragraphs]"
RETEXT_BATCH_PREFIX = "regrade_retext"
RETEXT_ITEM_SUFFIX = "#retext"

_CNN_TRANSCRIPT_RE = re.compile(r"^https://transcripts\.cnn\.com/")
_CREC_PDF_RE = re.compile(r"/CREC-(\d{4}-\d{2}-\d{2})(?:-([a-z]+))?\.pdf$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def classify_source_urls(source_urls):
    """Read-only-safe, mechanical strategy pick for ONE evidence row's
    `source_urls` -- never any other field on the row. Returns
    {"strategy": "interview_url", "package": <exact url>} for a CNN
    transcript segment, {"strategy": "crec_date", "package": "CREC-<date>",
    "chamber": "house"|"senate"|None} for a CREC floor-proceedings PDF (the
    chamber narrows the query further only when the filename actually names
    one), or None when no source_url matches either shape -- `speeches` was
    only ever built from CREC bulk data and CNN transcript scrapes
    (confirmed: `SELECT DISTINCT source FROM speeches` is exactly
    {CREC, INTERVIEW, CHRG}), so a member's own office page, a plain news
    article, a C-SPAN program page, or a magazine feature could never have a
    local row under either rule, and this returns None for those rather
    than guessing at a third rule."""
    for url in source_urls or []:
        if not isinstance(url, str):
            continue
        if _CNN_TRANSCRIPT_RE.match(url):
            return {"strategy": "interview_url", "package": url}
        m = _CREC_PDF_RE.search(url)
        if m:
            chamber = m.group(2) if m.group(2) in ("house", "senate") else None
            return {"strategy": "crec_date", "package": "CREC-%s" % m.group(1), "chamber": chamber}
    return None


def surname_of(full_name):
    """Mechanical surname: the last whitespace-separated token of a display
    name ("Alexandria Ocasio-Cortez" -> "Ocasio-Cortez", "Derrick Van Orden"
    -> "Orden"). A two-word surname like "Van Orden" is reduced to its last
    token, but that is still a superset match (any text containing "Van
    Orden" also contains "Orden"), so this never produces a false negative
    for the plain-substring mention check below -- only, at worst, a wider
    substring than the full surname, which plain-text floor/interview
    speech makes negligible in practice."""
    parts = (full_name or "").split()
    return parts[-1] if parts else ""


def split_into_sentences(text):
    """Mechanical stand-in for "paragraph" in this evidence source: every
    `speeches.text` value in social_media.db is stored as one continuous
    run with NO blank-line paragraph breaks at all (verified for this task:
    zero '\\n' characters in every row inspected, short interview soundbites
    and multi-thousand-character CREC floor speeches alike), so the nearest
    document-order sub-unit the raw text actually offers is the sentence.
    Splits after '.', '!' or '?' followed by whitespace; reorders nothing,
    drops nothing, never looks at anything but `text` itself."""
    text = (text or "").strip()
    if not text:
        return []
    return [s for s in _SENTENCE_SPLIT_RE.split(text) if s]


def trim_evidence_text(text, surnames, max_chars=RETEXT_MAX_CHARS, splitter=split_into_sentences,
                       joiner=" "):
    """MECHANICAL evidence-text builder: keep only the units (see `splitter`
    -- split_into_sentences, this source's actual "paragraph" unit, unless a
    caller passes a different one) that contain any of `surnames` (plain,
    case-sensitive substring; never a regex, never word-stemmed), plus one
    unit immediately before and one immediately after each hit, in original
    document order, with overlapping windows merged and de-duplicated, then
    capped at `max_chars`. When no unit mentions either surname at all (a
    short soundbite that never spells out the other person's name, e.g. a
    single clipped floor retort), there is nothing to anchor a window on, so
    the full text is kept mechanically rather than guessed at -- subject to
    the same cap. Reads nothing but `text` and `surnames`: no prior
    reviewer's reason, paraphrase, note, sign, or category ever passes
    through this function, because none is ever passed in. Returns
    (built_text, was_trimmed); `built_text` carries the literal
    RETEXT_TRIM_MARKER, appended after the text (never counted against
    `max_chars` itself), the moment anything was actually cut -- a dropped
    unit, a truncated cap, or both.

    `splitter`/`joiner` let a second caller reuse this exact windowing/cap/
    marker rule over a different document-order unit than the sentence this
    source (`speeches.text`, never blank-line-broken) needs:
    build_kit_retext_fetched passes split_into_paragraphs/"\\n\\n" for
    fetched web-page text, which -- unlike every `speeches.text` row --
    does carry real blank-line paragraph breaks. Both defaults reproduce
    the original sentence-only, space-joined behaviour exactly, so every
    existing caller is unaffected."""
    units = splitter(text)
    if not units:
        return "", False
    surnames = [s for s in surnames if s]
    hit_idx = [i for i, s in enumerate(units) if any(sn in s for sn in surnames)]
    if hit_idx:
        keep = set()
        for i in hit_idx:
            keep.update(range(max(0, i - 1), min(len(units), i + 2)))
        kept_idx = sorted(keep)
    else:
        kept_idx = list(range(len(units)))
    kept = joiner.join(units[i] for i in kept_idx)
    trimmed = len(kept_idx) < len(units)
    if len(kept) > max_chars:
        kept = kept[:max_chars].rstrip()
        trimmed = True
    if trimmed:
        kept = "%s\n\n%s" % (kept, RETEXT_TRIM_MARKER)
    return kept, trimmed


def query_speeches(package, member, chamber=None, db_path=None):
    """Read-only (mode=ro, PRAGMA query_only=ON -- same access pattern
    fetch_sqlite_row already uses) exact-match lookup against `speeches`:
    package and member always; chamber too when given (CREC candidates
    whose filename names a chamber). Returns a list of
    (rowid, date, source, text) tuples, never raises on zero rows."""
    db_path = Path(db_path) if db_path else SOCIAL_MEDIA_DB
    con = sqlite3.connect(db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    try:
        con.execute("PRAGMA query_only=ON")
        if chamber:
            sql = "SELECT rowid, date, source, text FROM speeches WHERE package=? AND member=? AND chamber=?"
            params = (package, member, chamber)
        else:
            sql = "SELECT rowid, date, source, text FROM speeches WHERE package=? AND member=?"
            params = (package, member)
        rows = con.execute(sql, params).fetchall()
    finally:
        con.close()
    return rows


# This task's own read-only investigation (--build-kit-retext's step 1)
# found exactly one syntactic candidate for evidence_id
# "anchor-aoc_fetterman_20240517-0" via rule 1 above: `speeches` rowid 67697
# is the ONLY Alexandria Ocasio-Cortez row anywhere on
# https://transcripts.cnn.com/show/sotu/date/2024-05-19/segment/01 (indeed
# the only row of ANY member on that URL, and the only Ocasio-Cortez row on
# that show/date at all). Its text -- "I would like to move to take down
# Ms. Greene's words. That is absolutely unacceptable. How dare you attack
# the physical appearance of another person?" -- is Ocasio-Cortez objecting
# to Rep. Marjorie Taylor Greene, a different news item; it never mentions
# Fetterman, and no Ocasio-Cortez row anywhere in `speeches` mentions
# Fetterman either (checked directly: zero rows). A single-candidate match
# on package+member is therefore rejected here as a content mismatch rather
# than accepted on syntax alone -- explicit and auditable, not a silent
# skip. No other evidence_id this task investigated needed this override.
RETEXT_REJECTED_MATCHES = {
    "anchor-aoc_fetterman_20240517-0":
        "single same-package/same-speaker local row (rowid 67697) is a different news item "
        "(Ocasio-Cortez objecting to Rep. Greene's remarks); it never mentions Fetterman and no "
        "other local Ocasio-Cortez row anywhere mentions Fetterman either -- rejected as a content "
        "mismatch rather than accepted on syntactic match alone",
}


def match_local_speech(evidence_id, source_urls, actor_name, target_surname, db_path=None):
    """Re-derives one "(no text)" evidence row's local match from scratch,
    read-only, per the two-rule procedure documented above. Returns exactly
    one of:
      {"status": "recovered", "rowid": N, "rule": "...", "date":, "source":, "text":}
      {"status": "ambiguous", "candidate_count": N, "rule": "..."}
      {"status": "missing", "reason": "..."}
    never partial, never a guess outside these rules."""
    strategy = classify_source_urls(source_urls)
    if strategy is None:
        return {"status": "missing",
               "reason": "external URL only; no local copy (source is neither a CNN transcript "
                         "segment nor a CREC floor-proceedings PDF)"}
    rows = query_speeches(strategy["package"], actor_name, strategy.get("chamber"), db_path)
    rule = "interview_url_package" if strategy["strategy"] == "interview_url" else "crec_date_member"
    if not rows:
        return {"status": "missing",
               "reason": "no local speeches row for member=%r on package=%r"
                         % (actor_name, strategy["package"])}
    if len(rows) > 1:
        narrowed = [r for r in rows if target_surname and target_surname in (r[3] or "")]
        if len(narrowed) == 1:
            rows = narrowed
            rule = rule + "+surname"
        elif narrowed:
            # More than one same-member row also mentions the target's
            # surname: THIS narrowed count is the meaningful ambiguity (not
            # the raw member-match count, which includes rows plainly about
            # something else) -- e.g. Tom Cole has 6 speeches in the
            # CREC-2019-05-15 house session, but only 2 mention McGovern.
            return {"status": "ambiguous", "candidate_count": len(narrowed), "rule": rule + "+surname"}
        else:
            return {"status": "ambiguous", "candidate_count": len(rows), "rule": rule}
    if evidence_id in RETEXT_REJECTED_MATCHES:
        return {"status": "missing", "reason": RETEXT_REJECTED_MATCHES[evidence_id]}
    rowid, date, source, text = rows[0]
    return {"status": "recovered", "rowid": rowid, "rule": rule, "date": date, "source": source,
           "text": text}


def build_kit_retext(out_dir, records_path, evidence_path, rubric_text, log=print, db_path=None,
                     locator_path=None, attribution_path=None, sources_dir=None):
    """Additive companion to build_kit/build_kit_supplement. For every
    record already in the kit that has at least one evidence row rendering
    as "(no text)" (resolved in reviewed_events.ndjson, but with no `text`
    key), re-derives a local `speeches` match per match_local_speech for
    each such row. A record where that recovers text for AT LEAST ONE such
    row gets a REPLACEMENT packet -- every already-text-bearing evidence row
    copied in completely unchanged, only the newly-recovered row(s) built
    from mechanically trimmed `speeches` text (trim_evidence_text) -- written
    under a NEW item_id (`<record_id>#retext`) in NEW
    `regrade_retext__{A,B}__NNNN` batches. No existing prompt or response
    file, nor any existing item_id, is ever opened for writing; index.json
    and batches.json are rewritten from every existing entry first, with
    only new entries appended after, exactly as build_kit_supplement already
    does. manifest.json gains two keys: `retext` (every "(no text)" row this
    run looked at, recovered or still missing, with its rule/reason) and
    `superseded` ({"A": {old_item_id: new_item_id}, "B": {...}}) for
    --ingest to reconcile.

    Two records this task recovers (v6:mace_to_crockett_confrontation,
    v6:comer_to_moskowitz_personal_escalation) cite a SECOND evidence_id
    that is itself only ever resolvable through build_kit_supplement's own
    PDF-page recovery (it is not, and was never meant to be, written back
    into reviewed_events.ndjson -- see build_kit_supplement's docstring).
    Loading evidence_by_id from evidence_path alone would make build_packet
    call BOTH of those records still-unresolved (the OTHER evidence_id, not
    the "(no text)" one this pass is trying to fix) and skip them outright.
    recover_missing_evidence is therefore re-run here, read-only, exactly as
    build_kit_supplement already runs it, purely to reconstruct in memory
    the same merged evidence view the live kit's own prompts were already
    built from -- nothing it returns is ever written anywhere by this
    function."""
    out_dir = Path(out_dir).resolve()
    kit_dir = out_dir / "grading_kit"
    manifest_path = kit_dir / "manifest.json"
    index_path = kit_dir / "index.json"
    batches_path = kit_dir / "batches.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    batches_data = json.loads(batches_path.read_text(encoding="utf-8"))

    records_by_id = {r["id"]: r for r in load_records(records_path)}
    evidence_by_id = load_evidence_index(evidence_path)
    locator_index = load_locator_index(locator_path)
    attribution_index = load_attribution_index(attribution_path)
    supplement_recovered, _log, _still_missing = recover_missing_evidence(
        manifest, locator_index, attribution_index, db_path, sources_dir)
    evidence_by_id = dict(evidence_by_id)
    evidence_by_id.update(supplement_recovered)
    schema_path = (Path(index_data["items"][0]["schema_path"]) if index_data["items"]
                  else kit_dir / "record_grade_schema.json")
    system_text = build_system_text(rubric_text)

    existing_stems = {safe_stem(it["item_id"]) for it in index_data["items"]}
    kit_record_ids = sorted({it["item_id"] for it in index_data["items"]
                             if not it["item_id"].endswith(RETEXT_ITEM_SUFFIX)})

    retext_rows_log = []
    superseded = {"A": {}, "B": {}}
    new_items = []

    for record_id in kit_record_ids:
        record = records_by_id.get(record_id)
        if record is None:
            continue
        packet_a, unresolved = build_packet(record, evidence_by_id, "A")
        if packet_a is None or unresolved:
            continue  # not a fully-resolved kit record; out of scope for a text-only retext
        missing_rows = [ev for ev in packet_a["evidence"] if ev["text"] is None]
        if not missing_rows:
            continue

        actor_name, target_name = record["names"][0], record["names"][1]
        actor_surname, target_surname = surname_of(actor_name), surname_of(target_name)
        recovered_here = {}
        for ev in missing_rows:
            eid = ev["evidence_id"]
            source_urls = (evidence_by_id.get(eid) or {}).get("source_urls")
            result = match_local_speech(eid, source_urls, actor_name, target_surname, db_path)
            if result["status"] == "recovered":
                trimmed_text, was_trimmed = trim_evidence_text(
                    result["text"], [actor_surname, target_surname])
                recovered_here[eid] = {"evidence_id": eid, "event_date": result["date"],
                                       "source": result["source"], "attribution": "direct_speaker",
                                       "text": trimmed_text}
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": "recovered", "rule": result["rule"],
                                        "rowid": result["rowid"], "trimmed": was_trimmed,
                                        "chars": len(trimmed_text)})
            else:
                reason = result.get("reason")
                if reason is None:
                    reason = "ambiguous local candidates (%d)" % result["candidate_count"]
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": result["status"], "reason": reason})

        if not recovered_here:
            continue

        merged_evidence = dict(evidence_by_id)
        merged_evidence.update(recovered_here)
        new_id = record_id + RETEXT_ITEM_SUFFIX
        stem = safe_stem(new_id)
        if stem in existing_stems:
            raise RegradeKitError("retext stem collision with an existing kit item: %s" % new_id)
        existing_stems.add(stem)

        for pass_tag in PASSES:
            packet = build_packet(record, merged_evidence, pass_tag)[0]
            if packet is None:
                raise RegradeKitError(
                    "%s: still unresolved evidence after merging retext recoveries" % record_id)
            user_text = render_user_text(packet)
            full_text = bg.full_prompt_text(system_text, user_text)
            prompt_path = kit_dir / "prompts" / pass_tag / ("%s.md" % stem)
            prompt_path.write_text(full_text, encoding="utf-8", newline="\n")
            response_path = kit_dir / "responses" / pass_tag / ("%s.json" % stem)
            new_items.append({"item_id": new_id, "pass": pass_tag, "prompt_path": str(prompt_path),
                              "schema_path": str(schema_path), "response_path": str(response_path)})
            superseded[pass_tag][record_id] = new_id

    new_items.sort(key=lambda it: (it["item_id"], it["pass"]))
    new_batches = build_batches(new_items, prefix=RETEXT_BATCH_PREFIX)

    index_data["items"] = list(index_data["items"]) + new_items
    bg.write_json(index_path, index_data)
    batches_data["batches"] = list(batches_data["batches"]) + new_batches
    batches_data["meta"]["batch_count"] = len(batches_data["batches"])
    bg.write_json(batches_path, batches_data)

    manifest["retext"] = {
        "records_checked": len({r["record_id"] for r in retext_rows_log}),
        "records_retexted": len(superseded["A"]),
        "rows": sorted(retext_rows_log, key=lambda r: (r["record_id"], r["evidence_id"])),
    }
    manifest["superseded"] = superseded
    bg.write_json(manifest_path, manifest)

    sweep = forbidden_word_sweep(kit_dir / "prompts", rubric_text)
    log("build-kit-retext: %d records retexted, %d new items in %d new batches; "
       "forbidden-key sweep %s (%d files)"
       % (len(superseded["A"]), len(new_items), len(new_batches),
          "CLEAN" if sweep["ok"] else "HITS FOUND", sweep["files_scanned"]))

    return {"kit_dir": str(kit_dir), "index_path": str(index_path), "batches_path": str(batches_path),
           "manifest_path": str(manifest_path), "records_retexted": len(superseded["A"]),
           "new_items": len(new_items), "new_batches": [b["batch_id"] for b in new_batches],
           "retext": manifest["retext"], "superseded": superseded, "sweep": sweep}


# ---------------------------------------------------------------------------
# --build-kit-retext-fetched: second recovery SOURCE for the exact same
# "(no text)" evidence-row gap build_kit_retext (above) targets. Where that
# LOCAL pass tries a `speeches`-table match, this pass tries a Paul-approved
# fetch of the evidence row's own external source_urls that has ALREADY
# happened -- grading_kit/fetched_sources/index.json plus one <sha256(url)>
# .txt/.json pair per attempted URL -- and never fetches anything itself
# (no network access here or anywhere in this module).
#
# Scope is exactly the records the local pass could not retext: any
# record_id already a key in manifest["superseded"]["A"] already has a
# replacement packet and is skipped outright here, untouched -- this pass
# can therefore never collide with, duplicate, or re-derive the local
# pass's 13 replacements, and calling it again after a run that changed
# nothing is a clean no-op (every record it retexts is, by the same rule,
# skipped on any later call).
#
# fetched_sources/index.json's "ok" flag is NOT usability: a CNN transcript
# URL that WebFetch condensed into a summary instead of quoting verbatim is
# recorded "ok": true, "status_or_error": "ok_summary_only: ...", with its
# own saved .txt -- exactly as unusable as evidence here as a failed fetch
# or an excluded PDF link, despite the file existing on disk. Only an entry
# that is "ok" AND NOT summary-only is ever read as evidence text
# (classify_fetched_entry).
# ---------------------------------------------------------------------------

def split_into_paragraphs(text):
    """Mechanical stand-in for "paragraph" in THIS evidence source -- the
    opposite situation from split_into_sentences's own docstring: a fetched
    web page's saved text (grading_kit/fetched_sources/<sha256>.txt) DOES
    carry real blank-line paragraph breaks (verified against every fixture
    this task fetched), so paragraphs, not sentences, are the nearest
    document-order unit worth windowing on here. Splits on runs of blank
    lines, strips each paragraph, drops any that go empty, reorders
    nothing."""
    text = (text or "").strip()
    if not text:
        return []
    return [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def classify_fetched_entry(entry):
    """Mechanical usable/summary_only/failed/excluded_pdf read of ONE
    fetched_sources/index.json entry, matching the fetch step's own
    `counts` bucketing (ok_full/ok_summary_only/failed/excluded_pdf)
    exactly. `ok_summary_only` entries are recorded with `"ok": true`
    (WebFetch still "succeeded", just not with verbatim text), so `ok`
    alone is never the usability test -- `status_or_error`'s own prefix is
    checked first. Returns "usable", "summary_only", "failed",
    "excluded_pdf", or "unknown" (defensive: a status_or_error prefix this
    task never produced)."""
    status_or_error = entry.get("status_or_error") or ""
    if entry.get("ok") and status_or_error.startswith("ok_summary_only"):
        return "summary_only"
    if entry.get("ok"):
        return "usable"
    if status_or_error.startswith("excluded_pdf"):
        return "excluded_pdf"
    if status_or_error.startswith("failed"):
        return "failed"
    return "unknown"


def load_fetched_sources_index(kit_dir):
    """Read-only load of grading_kit/fetched_sources/index.json's `entries`
    list into a {url: entry} dict, exactly as the (separately-authorised,
    already-completed) fetch step wrote it -- this never fetches, never
    re-hashes; sha256 is read off the entry itself, the same value the
    fetch step already used to name the <sha256>.txt/.json sidecar files.
    Returns {} when the kit has no fetched_sources directory at all (e.g. a
    synthetic test kit that never ran the fetch step), never raises."""
    index_path = Path(kit_dir) / "fetched_sources" / "index.json"
    if not index_path.exists():
        return {}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return {e["url"]: e for e in data.get("entries", []) if e.get("url")}


def match_fetched_source(source_urls, fetched_by_url, kit_dir):
    """Re-derives one "(no text)" evidence row's fetched-page match. Mirrors
    match_local_speech's contract but over fetched_sources/index.json
    instead of `speeches`: tries each of the row's own `source_urls`, IN
    CITATION ORDER, and returns on the first one with a recorded fetch
    entry -- never a guess across multiple entries, never a preference for
    a "better" status further down the list (mirrors
    classify_source_urls's own documented first-match-wins rule). Returns
    exactly one of:
      {"status": "recovered", "source_url":, "sha256":, "text":}
      {"status": "missing", "reason": "..."}
    A url the fetch step never attempted at all (absent from source_urls,
    or simply not a key in the index) is reported "missing", same
    vocabulary match_local_speech already uses for its own no-strategy
    case."""
    for url in source_urls or []:
        if not isinstance(url, str):
            continue
        entry = fetched_by_url.get(url)
        if entry is None:
            continue
        kind = classify_fetched_entry(entry)
        if kind == "usable":
            text_path = Path(kit_dir) / "fetched_sources" / ("%s.txt" % entry["sha256"])
            if not text_path.exists():
                return {"status": "missing",
                       "reason": "fetched_sources index marks %s ok/usable but %s is absent "
                                 "on disk" % (url, text_path)}
            return {"status": "recovered", "source_url": url, "sha256": entry["sha256"],
                   "text": text_path.read_text(encoding="utf-8")}
        if kind == "summary_only":
            return {"status": "missing",
                   "reason": "fetched source is summary-only, not usable as evidence: %s"
                             % entry.get("status_or_error")}
        if kind == "excluded_pdf":
            return {"status": "missing",
                   "reason": "fetched source is a PDF/binary link, skipped: %s"
                             % entry.get("status_or_error")}
        if kind == "failed":
            return {"status": "missing",
                   "reason": "fetch failed for this URL: %s" % entry.get("status_or_error")}
        return {"status": "missing",
               "reason": "fetched_sources entry for %s has an unrecognised status_or_error: %r"
                         % (url, entry.get("status_or_error"))}
    return {"status": "missing",
           "reason": "no fetched-source entry recorded for any source_urls on this evidence row"}


def build_kit_retext_fetched(out_dir, records_path, evidence_path, rubric_text, log=print,
                             db_path=None, locator_path=None, attribution_path=None,
                             sources_dir=None):
    """Additive companion to build_kit_retext, second recovery SOURCE for
    the same "(no text)" evidence-row gap (see module section header
    above). Records build_kit_retext's own LOCAL `speeches`-table pass
    already retexted (a key in manifest["superseded"]["A"]) are skipped
    outright -- never re-attempted, never re-written. For every remaining
    kit record with at least one "(no text)" row, each such row's own
    `source_urls` are tried, in order, against
    grading_kit/fetched_sources/index.json (match_fetched_source); a row
    recovers only from an entry the fetch step marked ok AND NOT
    summary-only (classify_fetched_entry) -- summary-only, failed, and
    excluded-PDF entries are exactly as unusable here as no entry at all.
    A recovered page's saved text is trimmed by the EXISTING
    trim_evidence_text rule -- same +/-1-unit window, same 6,000-char cap,
    same RETEXT_TRIM_MARKER -- but over PARAGRAPHS (split_into_paragraphs),
    the fetched page's own real "paragraph" unit, never sentences (unlike
    `speeches.text`, which has none). Only `text` is ever replaced on the
    row: event_date/source/attribution stay exactly as reviewed_events.
    ndjson already had them, since (unlike a `speeches` match, a genuinely
    different row) this is the SAME evidence row, just no longer missing
    its text. Never includes any reviewer paraphrase, note, or judgement --
    the only text this function ever puts in a packet is a fetched page's
    own saved .txt, mechanically trimmed.

    A record where that recovers text for its missing row gets a
    REPLACEMENT packet, written under item_id `<record_id>#retext` --
    DELIBERATELY the SAME suffix/namespace build_kit_retext's local pass
    uses (RETEXT_ITEM_SUFFIX), not a new one: run_ingest's kit_record_ids
    computation excludes items by that exact suffix, and apply_supersession
    reconciles purely from manifest["superseded"], so reusing it is what
    keeps a fetched-recovered record's response landing in --ingest under
    its ORIGINAL record id, with no changes needed to either function.
    This is safe only because this pass never processes a record the local
    pass already claimed (see above) -- so no stem it writes can ever
    collide with one build_kit_retext already wrote.

    New batches continue the SAME `regrade_retext` batch_id family, at the
    highest existing batch NUMBER already used *for that family specifically*
    (never the plain `regrade` family's own, higher, numbers) -- e.g.
    regrade_retext__A__0002 after a kit whose retext family stops at
    __0001. index.json/batches.json are rewritten from every existing
    entry first, new entries appended after; no existing prompt or
    response file is ever opened for writing.

    manifest["retext"] is EXTENDED, never replaced: this run's rows
    (recovered or still missing) are appended after every row already
    logged there, so a record's local-pass "missing" reason and its
    fetched-pass outcome both stay on the record side by side -- an honest
    two-attempts audit trail, never one overwriting the other.
    manifest["superseded"] is likewise extended: this run adds one new
    {old_item_id: new_item_id} pair per pass for each newly-recovered
    record only -- a record already keyed there is never touched, enforced
    structurally (this function never iterates over manifest["superseded"]
    itself, only skips what is already in it)."""
    out_dir = Path(out_dir).resolve()
    kit_dir = out_dir / "grading_kit"
    manifest_path = kit_dir / "manifest.json"
    index_path = kit_dir / "index.json"
    batches_path = kit_dir / "batches.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    batches_data = json.loads(batches_path.read_text(encoding="utf-8"))

    records_by_id = {r["id"]: r for r in load_records(records_path)}
    evidence_by_id = load_evidence_index(evidence_path)
    locator_index = load_locator_index(locator_path)
    attribution_index = load_attribution_index(attribution_path)
    supplement_recovered, _log, _still_missing = recover_missing_evidence(
        manifest, locator_index, attribution_index, db_path, sources_dir)
    evidence_by_id = dict(evidence_by_id)
    evidence_by_id.update(supplement_recovered)
    schema_path = (Path(index_data["items"][0]["schema_path"]) if index_data["items"]
                  else kit_dir / "record_grade_schema.json")
    system_text = build_system_text(rubric_text)

    existing_stems = {safe_stem(it["item_id"]) for it in index_data["items"]}
    kit_record_ids = sorted({it["item_id"] for it in index_data["items"]
                             if not it["item_id"].endswith(RETEXT_ITEM_SUFFIX)})
    already_retexted = set(manifest.get("superseded", {}).get("A", {}))
    fetched_by_url = load_fetched_sources_index(kit_dir)

    retext_rows_log = []
    superseded = {"A": dict(manifest.get("superseded", {}).get("A", {})),
                 "B": dict(manifest.get("superseded", {}).get("B", {}))}
    new_items = []

    for record_id in kit_record_ids:
        if record_id in already_retexted:
            continue  # build_kit_retext's local pass already claimed this one
        record = records_by_id.get(record_id)
        if record is None:
            continue
        packet_a, unresolved = build_packet(record, evidence_by_id, "A")
        if packet_a is None or unresolved:
            continue  # not a fully-resolved kit record; out of scope for a text-only retext
        missing_rows = [ev for ev in packet_a["evidence"] if ev["text"] is None]
        if not missing_rows:
            continue

        actor_name, target_name = record["names"][0], record["names"][1]
        actor_surname, target_surname = surname_of(actor_name), surname_of(target_name)
        recovered_here = {}
        for ev in missing_rows:
            eid = ev["evidence_id"]
            source_urls = (evidence_by_id.get(eid) or {}).get("source_urls")
            result = match_fetched_source(source_urls, fetched_by_url, kit_dir)
            if result["status"] == "recovered":
                trimmed_text, was_trimmed = trim_evidence_text(
                    result["text"], [actor_surname, target_surname],
                    splitter=split_into_paragraphs, joiner="\n\n")
                recovered_here[eid] = dict(ev, text=trimmed_text)
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": "recovered", "source_url": result["source_url"],
                                        "sha256": result["sha256"], "trimmed": was_trimmed,
                                        "chars": len(trimmed_text)})
            else:
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": result["status"], "reason": result["reason"]})

        if not recovered_here:
            continue

        merged_evidence = dict(evidence_by_id)
        merged_evidence.update(recovered_here)
        new_id = record_id + RETEXT_ITEM_SUFFIX
        stem = safe_stem(new_id)
        if stem in existing_stems:
            raise RegradeKitError("retext-fetched stem collision with an existing kit item: %s"
                                  % new_id)
        existing_stems.add(stem)

        for pass_tag in PASSES:
            packet = build_packet(record, merged_evidence, pass_tag)[0]
            if packet is None:
                raise RegradeKitError(
                    "%s: still unresolved evidence after merging retext-fetched recoveries"
                    % record_id)
            user_text = render_user_text(packet)
            full_text = bg.full_prompt_text(system_text, user_text)
            prompt_path = kit_dir / "prompts" / pass_tag / ("%s.md" % stem)
            prompt_path.write_text(full_text, encoding="utf-8", newline="\n")
            response_path = kit_dir / "responses" / pass_tag / ("%s.json" % stem)
            new_items.append({"item_id": new_id, "pass": pass_tag, "prompt_path": str(prompt_path),
                              "schema_path": str(schema_path), "response_path": str(response_path)})
            superseded[pass_tag][record_id] = new_id

    new_items.sort(key=lambda it: (it["item_id"], it["pass"]))
    last_batch_num = {}
    family_prefix = RETEXT_BATCH_PREFIX + "__"
    for b in batches_data["batches"]:
        if not b["batch_id"].startswith(family_prefix):
            continue  # never let the plain "regrade" family's higher numbers leak in here
        n = int(b["batch_id"].rsplit("__", 1)[-1])
        last_batch_num[b["pass"]] = max(last_batch_num.get(b["pass"], 0), n)
    new_batches = build_batches(new_items, start_at=last_batch_num, prefix=RETEXT_BATCH_PREFIX)

    index_data["items"] = list(index_data["items"]) + new_items
    bg.write_json(index_path, index_data)
    batches_data["batches"] = list(batches_data["batches"]) + new_batches
    batches_data["meta"]["batch_count"] = len(batches_data["batches"])
    bg.write_json(batches_path, batches_data)

    newly_retexted = set(superseded["A"]) - already_retexted
    existing_retext = manifest.get("retext") or {"records_checked": 0, "records_retexted": 0,
                                                 "rows": []}
    merged_rows = list(existing_retext.get("rows", [])) + retext_rows_log
    merged_rows.sort(key=lambda r: (r["record_id"], r["evidence_id"]))
    manifest["retext"] = {
        "records_checked": len({r["record_id"] for r in merged_rows}),
        "records_retexted": len(superseded["A"]),
        "rows": merged_rows,
    }
    manifest["superseded"] = superseded
    bg.write_json(manifest_path, manifest)

    sweep = forbidden_word_sweep(kit_dir / "prompts", rubric_text)
    log("build-kit-retext-fetched: %d records retexted, %d new items in %d new batches; "
       "forbidden-key sweep %s (%d files)"
       % (len(newly_retexted), len(new_items), len(new_batches),
          "CLEAN" if sweep["ok"] else "HITS FOUND", sweep["files_scanned"]))

    return {"kit_dir": str(kit_dir), "index_path": str(index_path), "batches_path": str(batches_path),
           "manifest_path": str(manifest_path), "records_retexted": len(newly_retexted),
           "new_items": len(new_items), "new_batches": [b["batch_id"] for b in new_batches],
           "retext": manifest["retext"], "superseded": superseded, "sweep": sweep,
           "rows_this_run": retext_rows_log}


# ---------------------------------------------------------------------------
# --build-kit-retext-pdf: third recovery SOURCE for the same "(no text)"
# evidence-row gap build_kit_retext (LOCAL speeches-table match) and
# build_kit_retext_fetched (fetched web pages) target. This pass reads a
# LOCAL PDF page-text extract Paul separately downloaded and had extracted
# -- no network access here or anywhere in this module -- recorded at
# grading_kit/fetched_sources/pdf/index.json plus one <sha256(url)>.pages.
# json (a list of {"page": <1-indexed int>, "text": <str>} rows, one per
# physical page) per PDF.
#
# Scope is exactly the records neither earlier pass could retext: a
# record_id already a key in manifest["superseded"]["A"] is skipped
# outright, the same skip rule build_kit_retext_fetched already applies to
# build_kit_retext's own claims -- this pass can therefore never collide
# with, duplicate, or re-derive either earlier pass's replacements, and
# calling it again after a run that changed nothing is a clean no-op.
#
# Matching a "(no text)" row to a PDF is a direct lookup, not a
# classify-then-query guess: fetched_sources/pdf/index.json's own
# `evidence_ids` list already names, per PDF, exactly which evidence_id(s)
# it was fetched for (written at fetch time by whoever chose the URL) --
# match_pdf_source below trusts that mapping completely rather than
# re-deriving it from source_urls the way classify_source_urls does for
# the local speeches-table pass.
#
# CASE CONVENTION, empirically verified against the real kit's own PDFs
# before any selection logic was written (never assumed): a raw CREC
# floor-proceedings PDF text-extract prints speaker attribution in full
# capitals -- "the gentleman from Oklahoma (Mr. COLE)", "Mr. MCGOVERN.
# Madam Speaker, ..." -- while running prose, roll-call vote tallies, and
# bill-cosponsor lists print the SAME surname in ordinary title case
# ("... Maloney, Sean Matsui McAdams McBath McCollum McEachin McGovern
# McNerney ..."). A case-SENSITIVE match against the record's own stored
# title-case name (surname_of("Tom Cole") == "Cole") therefore
# systematically MISSES genuine speaker-attributed floor colloquy and
# surfaces only roll-call/cosponsor-list co-occurrences instead --
# confirmed directly against v6:anchor-cole_mcgovern_20190515-0's own PDF
# (CREC-2019-05-15-house.pdf): a case-sensitive scan's only same-paragraph
# hit was a Yea/Nay roll-call list, while the actual Rules Committee floor
# exchange between Mr. COLE and Mr. MCGOVERN that same day appears only in
# full capitals and was invisible to it. Every co-occurrence/fallback test
# below is therefore explicitly case-INSENSITIVE (plain substring on
# upper-cased text -- never a regex, never word-stemmed, the same "plain
# substring" ethic trim_evidence_text documents, only case-folded).
#
# DISCLOSED LIMITATION, never silently hidden: case-insensitive surname
# co-occurrence still cannot tell a genuine floor exchange apart from a
# roll-call vote tally or bill-cosponsor list that happens to print both
# surnames -- CREC renders both as plain runs of member names, and
# distinguishing them is a content judgement this MECHANICAL selector
# deliberately does not attempt. A packet built here can therefore include
# such a fragment alongside genuine colloquy, verbatim and page-numbered
# either way, for a grader to weigh -- never a reviewer paraphrase, and
# never silently dropped either way.
# ---------------------------------------------------------------------------

PDF_SOURCES_SUBDIR = "pdf"


def load_pdf_index(kit_dir):
    """Read-only load of grading_kit/fetched_sources/pdf/index.json's
    `entries` list into {evidence_id: entry}. One entry can name more than
    one evidence_id (the comer_jeffries PDF covers both
    anchor-comer_jeffries_20251120-0 and -1); every evidence_id it lists
    maps to that SAME entry. Returns {} when the kit has no fetched_sources/
    pdf directory at all (e.g. a synthetic test kit that never seeded one),
    never raises."""
    index_path = Path(kit_dir) / "fetched_sources" / PDF_SOURCES_SUBDIR / "index.json"
    if not index_path.exists():
        return {}
    data = json.loads(index_path.read_text(encoding="utf-8"))
    by_evidence_id = {}
    for entry in data.get("entries", []):
        for eid in entry.get("evidence_ids") or []:
            by_evidence_id[eid] = entry
    return by_evidence_id


def load_pdf_pages(kit_dir, sha256):
    """Read-only load of one <sha256>.pages.json -- a list of {"page": int,
    "text": str} rows, one per physical page -- sorted into page order.
    Raises RegradeKitError (fail loudly, same ethic as
    fetch_pdf_pages_text) when the file is absent: a missing extract is
    never silently treated as no evidence."""
    pages_path = Path(kit_dir) / "fetched_sources" / PDF_SOURCES_SUBDIR / ("%s.pages.json" % sha256)
    if not pages_path.exists():
        raise RegradeKitError("no local PDF page extract for sha256=%r (looked for %s)"
                              % (sha256, pages_path))
    pages = json.loads(pages_path.read_text(encoding="utf-8"))
    return sorted(pages, key=lambda p: p["page"])


def pdf_paragraph_units(pages):
    """Flat, document-ordered (page, paragraph_text) list built from
    `pages` (load_pdf_pages's own shape): each page's own text is split
    into paragraphs independently (split_into_paragraphs -- real
    blank-line breaks, verified against the real kit's own PDF extracts),
    never merged across a page boundary. Page order, then paragraph order
    within a page: "document order" throughout this section means exactly
    this list's own order."""
    units = []
    for p in pages:
        for para in split_into_paragraphs(p.get("text")):
            units.append((p["page"], para))
    return units


def pdf_cooccurrence_windows(units, actor_surname, target_surname):
    """Windows into `units` -- (page, text) pairs, e.g.
    pdf_paragraph_units's own output -- where the actor's and target's
    surnames CO-OCCUR. See the module section header above for the
    case-insensitive rationale and the disclosed roll-call/cosponsor-list
    limitation.

    A "hit" is either ONE unit containing both surnames, or TWO ADJACENT
    units each containing one of the two surnames (either order). Every
    hit is expanded by one unit of context on each side; touching or
    overlapping expanded ranges are then merged into ONE window -- two
    hits close enough that their own context paragraphs meet are the
    single contiguous excerpt they become, never two. Plain,
    case-insensitive substring containment only -- never a regex, never
    word-stemmed, never reordered.

    Returns a list of {"start", "end", "density"} dicts, `start`/`end`
    inclusive indices into `units`, sorted by document order (`start`
    ascending -- windows never overlap by construction, so this is also
    sorted by `end`). `density` is the co-occurrence DENSITY task step 1
    asks build_pdf_evidence_text to rank windows by: the count of indices
    in [start, end] where BOTH surnames appear in that SAME unit (an
    adjacent-pair hit contributes to a window's span but never, by itself,
    to its density -- neither unit in the pair names both surnames).
    Empty list when either surname is empty (nothing to anchor a match on)
    or no hit exists."""
    if not actor_surname or not target_surname:
        return []
    n = len(units)
    upper = [text.upper() for _page, text in units]
    a, t = actor_surname.upper(), target_surname.upper()
    has_a = [a in u for u in upper]
    has_t = [t in u for u in upper]
    raw_spans = []
    for i in range(n):
        if has_a[i] and has_t[i]:
            raw_spans.append((i, i))
        elif i + 1 < n and ((has_a[i] and has_t[i + 1]) or (has_t[i] and has_a[i + 1])):
            raw_spans.append((i, i + 1))
    if not raw_spans:
        return []
    expanded = sorted((max(0, s - 1), min(n - 1, e + 1)) for s, e in raw_spans)
    merged = []
    for s, e in expanded:
        if merged and s <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))
    return [{"start": s, "end": e,
            "density": sum(1 for i in range(s, e + 1) if has_a[i] and has_t[i])}
           for s, e in merged]


def pdf_actor_surname_fallback(units, actor_surname):
    """Fallback selection for pdf_cooccurrence_windows's own "fewer than 2
    windows" case (see build_pdf_evidence_text): every unit containing the
    actor's surname alone, same case-insensitive plain-substring rule,
    document order. The task instruction for this fallback names only
    "paragraphs with the actor's surname" -- unlike the co-occurrence rule
    above, it adds no one-paragraph-of-context margin, so none is added
    here either. Returns indices sorted, deduped; empty when the surname
    itself is empty or nothing matches."""
    if not actor_surname:
        return []
    a = actor_surname.upper()
    return [i for i, (_page, text) in enumerate(units) if a in text.upper()]


RANK_RULE_DESCRIPTION = ("co-occurrence density desc (paragraphs within the window naming both "
                         "surnames together), ties broken by document order; windows filled "
                         "into the character budget whole, in that rank order; the first window "
                         "that does not fit whole is truncated to the remaining budget rather "
                         "than skipped for a smaller one, then everything is rendered back in "
                         "document order")


def _fill_budget_by_rank(units, windows, max_chars):
    """Greedy fill over `windows` (pdf_cooccurrence_windows's own shape) in
    RANK order -- highest `density` first, ties broken by `start` (earlier
    window first, i.e. document order) -- so the character budget is spent
    on the strongest evidence first rather than on whichever window merely
    happens to occur earliest in a long daily edition (the failure this
    ranking rule replaces: the highest-signal exchange in a real record was
    previously starved by an earlier, thinner window).

    A window is added WHOLE the moment doing so keeps the running total at
    or under `max_chars`. The FIRST window that does NOT fit whole is
    truncated instead -- as many of ITS OWN paragraphs, in document order,
    as still fit in what remains of the budget -- and selection then STOPS
    (no lower-ranked window is tried after it). A too-big top window is
    therefore never dropped in favour of a smaller, weaker one: on a real
    Congressional Record daily edition a single window (its own paragraph
    plus one unit of context on each side) can easily exceed `max_chars`
    by itself, and discarding the single highest-density window outright
    would defeat the ranking rule's own purpose -- confirmed against
    v6:anchor-mcgovern_cole_20200423-0's own PDF, where skip-not-truncate
    landed on an early, low-density window (page 1) while the actual
    density-3 Cole/McGovern exchange (page 13, ~8,000 characters alone)
    was dropped outright for not fitting whole.

    Selection is by rank; the RETURNED indices are sorted back into
    document order, since a grader should read events as they happened
    even though rank order decided which events made the cut. Returns a
    sorted list of kept indices into `units` (possibly empty)."""
    ranked = sorted(windows, key=lambda w: (-w["density"], w["start"]))
    selected = set()
    for w in ranked:
        window_idx = [i for i in range(w["start"], w["end"] + 1) if i not in selected]
        if not window_idx:
            continue
        candidate = selected | set(window_idx)
        length = sum(len(units[i][1]) for i in candidate) + 2 * max(0, len(candidate) - 1)
        if length <= max_chars:
            selected = candidate
            continue
        for i in window_idx:  # already in document order
            trial = selected | {i}
            trial_length = sum(len(units[j][1]) for j in trial) + 2 * max(0, len(trial) - 1)
            if trial_length > max_chars:
                break
            selected = trial
        break  # stop entirely once a window has been truncated, whole or partial
    return sorted(selected)


def build_pdf_evidence_text(pages, actor_surname, target_surname,
                            max_chars=RETEXT_MAX_CHARS, marker=RETEXT_TRIM_MARKER):
    """Mechanical evidence-text builder for one PDF-cited "(no text)" row:
    pdf_paragraph_units, then pdf_cooccurrence_windows; when that finds
    FEWER THAN 2 windows, pdf_actor_surname_fallback over the SAME page set
    instead (per task instruction -- these PDFs are single-calendar-day
    Congressional Record editions, so "the episode date's pages" is every
    page `pages` already contains; a multi-date PDF is out of scope for
    this kit). Two or more windows are ranked and fit to the character
    budget by _fill_budget_by_rank (see its own docstring for why: document
    order alone let an early, thin window starve a later, denser one); the
    fallback keeps every actor-surname hit unranked, exactly as before.
    Either way the kept units are then capped at `max_chars` and marked
    with `marker` the moment anything was actually cut -- a dropped unit, a
    truncated cap, or both -- the same cap-and-marker rule trim_evidence_
    text already uses, reimplemented (not called) only because it must
    apply here to a caller-selected kept-index set rather than to
    trim_evidence_text's own single-surname-OR hit test. (The rank-and-fit
    pass already keeps the co-occurrence path's own total at or under
    `max_chars`, so this second check is a no-op there in practice and a
    real cap only for the fallback path, which has no budget-fitting step
    of its own.)

    Returns (text, was_trimmed, pages_used, used_fallback, rank_rule):
    `pages_used` is the sorted, deduped list of physical page numbers that
    actually survive in `text` -- computed AFTER the `max_chars` cap, not
    before, so a page whose own paragraph(s) fall entirely past the cut is
    never listed as "used" just because it was part of the pre-cap
    selection. `rank_rule` is RANK_RULE_DESCRIPTION when the co-occurrence
    path ranked and filled the budget, or None when the fallback path was
    used instead (ranking does not apply there). `text` is "" (untrimmed,
    pages_used [], rank_rule None) when neither rule matches anything at
    all -- the caller treats that as a still-missing row, never a
    fabricated empty packet."""
    units = pdf_paragraph_units(pages)
    windows = pdf_cooccurrence_windows(units, actor_surname, target_surname)
    used_fallback = len(windows) < 2
    rank_rule = None
    if used_fallback:
        kept_idx = pdf_actor_surname_fallback(units, actor_surname)
    else:
        rank_rule = RANK_RULE_DESCRIPTION
        kept_idx = _fill_budget_by_rank(units, windows, max_chars)
    if not kept_idx:
        return "", False, [], used_fallback, rank_rule
    trimmed = len(kept_idx) < len(units)
    kept_text = "\n\n".join(units[i][1] for i in kept_idx)
    if len(kept_text) > max_chars:
        kept_text = kept_text[:max_chars].rstrip()
        trimmed = True
    pages_used = []
    offset = 0
    for i in kept_idx:
        if offset >= len(kept_text):
            break  # every later unit was cut away entirely by the cap above
        page = units[i][0]
        if page not in pages_used:
            pages_used.append(page)
        offset += len(units[i][1]) + 2  # +2 for the "\n\n" joiner
    pages_used.sort()
    if trimmed:
        kept_text = "%s\n\n%s" % (kept_text, marker)
    return kept_text, trimmed, pages_used, used_fallback, rank_rule


def match_pdf_source(evidence_id, pdf_by_evidence_id):
    """Direct-lookup counterpart to match_local_speech/match_fetched_source
    for the PDF recovery source: `pdf_by_evidence_id` (load_pdf_index) is
    already keyed by evidence_id, written at fetch time by whoever chose
    which PDF to fetch for which evidence_id -- never re-derived from
    source_urls here. Returns the raw index entry, or None when this
    evidence_id has no PDF entry at all (out of scope for this pass)."""
    return pdf_by_evidence_id.get(evidence_id)


def build_kit_retext_pdf(out_dir, records_path, evidence_path, rubric_text, log=print,
                         db_path=None, locator_path=None, attribution_path=None,
                         sources_dir=None):
    """Additive companion to build_kit_retext/build_kit_retext_fetched,
    third recovery SOURCE for the same "(no text)" evidence-row gap (see
    module section header above). Records either earlier pass already
    retexted (a key in manifest["superseded"]["A"]) are skipped outright.
    For every remaining kit record with at least one "(no text)" row whose
    evidence_id has a PDF entry (match_pdf_source), build_pdf_evidence_text
    selects and caps the replacement text; a record where that recovers
    text for AT LEAST ONE such row gets a REPLACEMENT packet -- every
    already-text-bearing evidence row copied in completely unchanged, only
    the newly-recovered row(s) built from the PDF -- written under item_id
    `<record_id>#retext` (the SAME suffix/namespace the other two recovery
    sources use, for the same reconciliation reason
    build_kit_retext_fetched's own docstring already gives) in NEW
    `regrade_retext__{A,B}__NNNN` batches, continuing that family's own
    highest existing batch number. No existing prompt or response file,
    nor any existing item_id, is ever opened for writing; index.json and
    batches.json are rewritten from every existing entry first, with only
    new entries appended after.

    manifest["retext"] is EXTENDED (this run's rows appended after every
    row already logged there) and manifest["superseded"] likewise (this
    run adds one new {old_item_id: new_item_id} pair per pass for each
    newly-recovered record only), exactly as build_kit_retext_fetched
    already does.

    manifest["pdf_available"] is a NEW key: for every kit record whose
    evidence cites a PDF, where neither that record's own evidence_id nor a
    sibling evidence_id sharing the SAME PDF has EVER been retexted BY THIS
    PDF PASS specifically (this run or an earlier one -- e.g.
    anchor-comer_jeffries_20251120-0 shares its PDF with -1, retexted by
    this pass this run), one entry records the record id, evidence id, PDF
    sha256, and page count, so the alternative source is on file even
    though that record's existing replacement -- built by the LOCAL
    speeches-table or FETCHED-web pass, or still just "(no text)" -- is
    left untouched. A record this pass HAS retexted is never also given a
    redundant note. Extended, never replaced, on a later run; a record
    already recorded here is never re-added."""
    out_dir = Path(out_dir).resolve()
    kit_dir = out_dir / "grading_kit"
    manifest_path = kit_dir / "manifest.json"
    index_path = kit_dir / "index.json"
    batches_path = kit_dir / "batches.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_data = json.loads(index_path.read_text(encoding="utf-8"))
    batches_data = json.loads(batches_path.read_text(encoding="utf-8"))

    records_by_id = {r["id"]: r for r in load_records(records_path)}
    evidence_by_id = load_evidence_index(evidence_path)
    locator_index = load_locator_index(locator_path)
    attribution_index = load_attribution_index(attribution_path)
    supplement_recovered, _log, _still_missing = recover_missing_evidence(
        manifest, locator_index, attribution_index, db_path, sources_dir)
    evidence_by_id = dict(evidence_by_id)
    evidence_by_id.update(supplement_recovered)
    schema_path = (Path(index_data["items"][0]["schema_path"]) if index_data["items"]
                  else kit_dir / "record_grade_schema.json")
    system_text = build_system_text(rubric_text)

    existing_stems = {safe_stem(it["item_id"]) for it in index_data["items"]}
    kit_record_ids = sorted({it["item_id"] for it in index_data["items"]
                             if not it["item_id"].endswith(RETEXT_ITEM_SUFFIX)})
    already_retexted = set(manifest.get("superseded", {}).get("A", {}))
    pdf_by_evidence_id = load_pdf_index(kit_dir)

    retext_rows_log = []
    superseded = {"A": dict(manifest.get("superseded", {}).get("A", {})),
                 "B": dict(manifest.get("superseded", {}).get("B", {}))}
    pdf_available = list(manifest.get("pdf_available", []))
    pdf_available_ids = {e["record_id"] for e in pdf_available}
    new_items = []

    for record_id in kit_record_ids:
        if record_id in already_retexted:
            continue  # an earlier pass (local speeches-table or fetched-web) already claimed this one
        record = records_by_id.get(record_id)
        if record is None:
            continue
        packet_a, unresolved = build_packet(record, evidence_by_id, "A")
        if packet_a is None or unresolved:
            continue  # not a fully-resolved kit record; out of scope for a text-only retext
        missing_rows = [ev for ev in packet_a["evidence"] if ev["text"] is None]
        if not missing_rows:
            continue

        actor_name, target_name = record["names"][0], record["names"][1]
        actor_surname, target_surname = surname_of(actor_name), surname_of(target_name)
        recovered_here = {}
        for ev in missing_rows:
            eid = ev["evidence_id"]
            pdf_entry = match_pdf_source(eid, pdf_by_evidence_id)
            if pdf_entry is None:
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": "missing",
                                        "reason": "no PDF entry recorded for this evidence_id in "
                                                  "fetched_sources/pdf/index.json"})
                continue
            sha256 = pdf_entry["sha256"]
            pages = load_pdf_pages(kit_dir, sha256)
            text, was_trimmed, pages_used, used_fallback, rank_rule = build_pdf_evidence_text(
                pages, actor_surname, target_surname)
            if not text:
                retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                        "status": "missing",
                                        "reason": "actor surname %r not found anywhere in the "
                                                  "cited PDF text (sha256=%s)"
                                                  % (actor_surname, sha256)})
                continue
            recovered_here[eid] = dict(ev, text=text)
            retext_rows_log.append({"record_id": record_id, "evidence_id": eid,
                                    "status": "recovered", "source": "pdf", "sha256": sha256,
                                    "pages": pages_used, "trimmed": was_trimmed,
                                    "used_fallback": used_fallback, "rank_rule": rank_rule,
                                    "chars": len(text)})

        if not recovered_here:
            continue

        merged_evidence = dict(evidence_by_id)
        merged_evidence.update(recovered_here)
        new_id = record_id + RETEXT_ITEM_SUFFIX
        stem = safe_stem(new_id)
        if stem in existing_stems:
            raise RegradeKitError("retext-pdf stem collision with an existing kit item: %s" % new_id)
        existing_stems.add(stem)

        for pass_tag in PASSES:
            packet = build_packet(record, merged_evidence, pass_tag)[0]
            if packet is None:
                raise RegradeKitError(
                    "%s: still unresolved evidence after merging retext-pdf recoveries" % record_id)
            user_text = render_user_text(packet)
            full_text = bg.full_prompt_text(system_text, user_text)
            prompt_path = kit_dir / "prompts" / pass_tag / ("%s.md" % stem)
            prompt_path.write_text(full_text, encoding="utf-8", newline="\n")
            response_path = kit_dir / "responses" / pass_tag / ("%s.json" % stem)
            new_items.append({"item_id": new_id, "pass": pass_tag, "prompt_path": str(prompt_path),
                              "schema_path": str(schema_path), "response_path": str(response_path)})
            superseded[pass_tag][record_id] = new_id

    new_items.sort(key=lambda it: (it["item_id"], it["pass"]))
    last_batch_num = {}
    family_prefix = RETEXT_BATCH_PREFIX + "__"
    for b in batches_data["batches"]:
        if not b["batch_id"].startswith(family_prefix):
            continue  # never let the plain "regrade" family's higher numbers leak in here
        n = int(b["batch_id"].rsplit("__", 1)[-1])
        last_batch_num[b["pass"]] = max(last_batch_num.get(b["pass"], 0), n)
    new_batches = build_batches(new_items, start_at=last_batch_num, prefix=RETEXT_BATCH_PREFIX)

    index_data["items"] = list(index_data["items"]) + new_items
    bg.write_json(index_path, index_data)
    batches_data["batches"] = list(batches_data["batches"]) + new_batches
    batches_data["meta"]["batch_count"] = len(batches_data["batches"])
    bg.write_json(batches_path, batches_data)

    newly_retexted = set(superseded["A"]) - already_retexted

    # pdf_available (see docstring): "untouched by THIS recovery source"
    # means untouched by the PDF pass SPECIFICALLY -- a record already
    # superseded by the LOCAL speeches-table or FETCHED-web pass (most of
    # the real kit's PDF-cited records: mace_to_crockett,
    # comer_to_moskowitz, omar_aoc_personal_defense, gosar_aoc_video,
    # durbin_grassley, durbin_duckworth, roy_massie) is EXACTLY the case
    # this note exists to document, so `superseded["A"]` in general (mixes
    # all three recovery sources) is the wrong exclusion set -- only a
    # record_id this PDF pass itself has EVER recovered (this run or an
    # earlier one) is excluded, identified the same way
    # classify_final_packets tells recovery sources apart: this function's
    # own retext_rows_log rows always carry "source": "pdf", persisted into
    # manifest["retext"]["rows"] every run, so re-reading that (merged with
    # this run's own retext_rows_log) reconstructs the full PDF-pass
    # history without a new manifest key -- and stays correct across
    # reruns, unlike keying off newly_retexted (this run only) or
    # superseded["A"] in full (every source), both of which the real-kit
    # rerun test below caught being wrong.
    existing_retext_rows = (manifest.get("retext") or {}).get("rows", [])
    pdf_retexted_record_ids = {r["record_id"] for r in existing_retext_rows
                               if r.get("source") == "pdf" and r.get("status") == "recovered"}
    pdf_retexted_record_ids |= {r["record_id"] for r in retext_rows_log
                               if r.get("source") == "pdf" and r.get("status") == "recovered"}
    touched_shas = {pdf_by_evidence_id[eid]["sha256"]
                    for rid in pdf_retexted_record_ids
                    for eid in (records_by_id.get(rid) or {}).get("evidence_ids", [])
                    if eid in pdf_by_evidence_id}
    for record_id in kit_record_ids:
        if record_id in pdf_available_ids or record_id in pdf_retexted_record_ids:
            continue
        record = records_by_id.get(record_id)
        if record is None:
            continue
        for eid in record.get("evidence_ids", []):
            pdf_entry = pdf_by_evidence_id.get(eid)
            if pdf_entry is None or pdf_entry["sha256"] in touched_shas:
                continue
            pdf_available.append({"record_id": record_id, "evidence_id": eid,
                                  "sha256": pdf_entry["sha256"], "pages": pdf_entry.get("pages")})
            pdf_available_ids.add(record_id)
            break

    existing_retext = manifest.get("retext") or {"records_checked": 0, "records_retexted": 0,
                                                 "rows": []}
    merged_rows = list(existing_retext.get("rows", [])) + retext_rows_log
    merged_rows.sort(key=lambda r: (r["record_id"], r["evidence_id"]))
    manifest["retext"] = {
        "records_checked": len({r["record_id"] for r in merged_rows}),
        "records_retexted": len(superseded["A"]),
        "rows": merged_rows,
    }
    manifest["superseded"] = superseded
    manifest["pdf_available"] = sorted(pdf_available, key=lambda e: e["record_id"])
    bg.write_json(manifest_path, manifest)

    sweep = forbidden_word_sweep(kit_dir / "prompts", rubric_text)
    log("build-kit-retext-pdf: %d records retexted, %d new items in %d new batches, %d records "
       "noted pdf_available; forbidden-key sweep %s (%d files)"
       % (len(newly_retexted), len(new_items), len(new_batches), len(pdf_available),
          "CLEAN" if sweep["ok"] else "HITS FOUND", sweep["files_scanned"]))

    return {"kit_dir": str(kit_dir), "index_path": str(index_path), "batches_path": str(batches_path),
           "manifest_path": str(manifest_path), "records_retexted": len(newly_retexted),
           "new_items": len(new_items), "new_batches": [b["batch_id"] for b in new_batches],
           "retext": manifest["retext"], "superseded": superseded,
           "pdf_available": manifest["pdf_available"], "sweep": sweep,
           "rows_this_run": retext_rows_log}


# ---------------------------------------------------------------------------
# --ingest
# ---------------------------------------------------------------------------

def _norm_original_degree(value):
    """v6 annotations.ndjson convention: an int 0-4, or JSON null meaning
    unassessable (per the P1-12 spec: 'original affinity/friction, null =
    unassessable')."""
    return "unassessable" if value is None else str(value)


def load_index(kit_dir):
    data = json.loads((Path(kit_dir) / "index.json").read_text(encoding="utf-8"))
    return data["meta"], data["items"]


def _alt_response_stem_candidates(item_id):
    """Alternate filename stems for `item_id`'s response file, beyond the
    canonical safe_stem(item_id) that response_path is built from (see
    build_kit/build_kit_retext/build_kit_retext_fetched). Root cause of the
    20260911 v6 regrade pass-B ingest mismatch: batch regrade_retext__B__0001's
    response writer sanitised item_id by replacing only ':' -- the one
    character actually illegal in a Windows filename -- and left every other
    character untouched, including a "#retext" item's literal '#', which
    safe_stem (build_kit's own convention) folds to '_' same as ':'. Every
    candidate here is derived solely from THIS item's own item_id, never from
    another item's, so resolving to one is never a guess between two
    different records."""
    canonical = safe_stem(item_id)
    colon_only = str(item_id).replace(":", "_")
    return [s for s in (colon_only,) if s != canonical]


def _resolve_response_path(item, canonical_paths):
    """The response path recorded in index.json (item["response_path"]),
    unless that exact file is absent AND an alternate filename derived from
    this SAME item's own item_id (see _alt_response_stem_candidates) exists
    on disk instead. An alternate is never used when it collides with some
    OTHER item's own recorded response_path -- that would silently attribute
    one record's response to a different record, exactly what a resolver
    here must never do. `canonical_paths` is the set of every item's
    recorded response_path string (computed once per read_responses() call)."""
    recorded = Path(item["response_path"])
    if recorded.exists():
        return recorded
    for alt_stem in _alt_response_stem_candidates(item["item_id"]):
        alt_path = recorded.with_name(alt_stem + ".json")
        if str(alt_path) in canonical_paths:
            continue  # another item's own file -- never borrow it
        if alt_path.exists():
            return alt_path
    return recorded


def read_responses(items, schema):
    """Returns (by_pass, failures). A response file that is absent, is not
    valid JSON, or fails schema validation is a failure, listed with its
    reason -- never imputed, never silently dropped from the count.

    Tries item["response_path"] exactly as recorded first; only when that
    exact file is absent does it also try this same item's alternate
    filename (see _resolve_response_path) before calling it missing."""
    by_pass = {"A": {}, "B": {}}
    failures = []
    canonical_paths = {item["response_path"] for item in items}
    for item in items:
        path = _resolve_response_path(item, canonical_paths)
        if not path.exists():
            failures.append({"item_id": item["item_id"], "pass": item["pass"],
                             "reason": "missing_response", "path": str(path)})
            continue
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            failures.append({"item_id": item["item_id"], "pass": item["pass"],
                             "reason": "invalid_json: %s" % exc, "path": str(path)})
            continue
        errors = validate_record_grade(obj, schema)
        if errors:
            failures.append({"item_id": item["item_id"], "pass": item["pass"],
                             "reason": "schema_invalid", "errors": errors, "path": str(path)})
            continue
        by_pass[item["pass"]][item["item_id"]] = obj
    return by_pass, failures


def qwk_or_null(pairs, categories=5):
    """Wraps bg.quadratic_weighted_kappa but returns (None, reason) on zero
    variance instead of letting blind_grading's own den==0 branch collapse
    that case to 0.0/1.0 -- see the module docstring."""
    if not pairs:
        return None, "n=0 both-assessed items"
    a = [x for x, _ in pairs]
    b = [y for _, y in pairs]
    if len(set(a)) <= 1 or len(set(b)) <= 1:
        return None, ("zero variance: at least one rater assigned the same degree to every "
                      "both-assessed item, so kappa is undefined, not measured (dis)agreement")
    return bg.quadratic_weighted_kappa(a, b, categories=categories), None


def axis_agreement(values_x, values_y, record_ids, dim):
    """values_x/values_y: {record_id: grade_dict}, already normalised so `dim`
    is either a numeric string '0'..'4' or 'unassessable'. n_total is always
    len(record_ids); a record missing from either side counts toward
    `missing`, never toward agree/disagree -- missing responses are failures,
    not imputed values, per P1-12. Every rate carries its own n via bg._rate."""
    n_total = len(record_ids)
    missing = []
    assess_agree = 0
    both_present = []
    for rid in record_ids:
        gx, gy = values_x.get(rid), values_y.get(rid)
        if gx is None or gy is None:
            missing.append(rid)
            continue
        vx, vy = gx.get(dim), gy.get(dim)
        ux, uy = (vx == "unassessable"), (vy == "unassessable")
        if ux == uy:
            assess_agree += 1
        if not ux and not uy:
            both_present.append((int(vx), int(vy)))
    n_present = n_total - len(missing)
    exact = sum(1 for x, y in both_present if x == y)
    within1 = sum(1 for x, y in both_present if abs(x - y) <= 1)
    kappa, kappa_note = qwk_or_null(both_present)
    return {
        "n_total": n_total,
        "missing": missing,
        "assessability_agreement": bg._rate(assess_agree, n_present),
        "both_assessed_n": len(both_present),
        "exact_agreement": bg._rate(exact, len(both_present)),
        "within_1_agreement": bg._rate(within1, len(both_present)),
        "quadratic_weighted_kappa": kappa,
        "quadratic_weighted_kappa_note": kappa_note,
    }


def compute_agreement(record_ids, pass_a, pass_b, original):
    dims = ("affinity", "friction")
    return {
        "n_records": len(record_ids),
        "between_passes": {d: axis_agreement(pass_a, pass_b, record_ids, d) for d in dims},
        "pass_a_vs_original": {d: axis_agreement(pass_a, original, record_ids, d) for d in dims},
        "pass_b_vs_original": {d: axis_agreement(pass_b, original, record_ids, d) for d in dims},
    }


def disagreement_queue(record_ids, pass_a, pass_b, original, records_by_id):
    """One row per record where the two blind passes disagree on either axis,
    or where either pass is missing (a missing side can never be shown as
    agreeing). For Paul: both passes' values and rationale, the original
    grade, and the evidence ids, so adjudication needs no other file open."""
    rows = []
    for rid in record_ids:
        ga, gb = pass_a.get(rid), pass_b.get(rid)
        if ga is None or gb is None:
            disagree = True
        else:
            disagree = any(ga.get(d) != gb.get(d) for d in ("affinity", "friction"))
        if not disagree:
            continue
        orig = records_by_id.get(rid, {})
        rows.append({
            "record_id": rid,
            "pass_a": ({"affinity": ga.get("affinity"), "friction": ga.get("friction"),
                       "rationale": ga.get("rationale")} if ga else None),
            "pass_b": ({"affinity": gb.get("affinity"), "friction": gb.get("friction"),
                       "rationale": gb.get("rationale")} if gb else None),
            "original": {"affinity": _norm_original_degree(orig.get("affinity")),
                        "friction": _norm_original_degree(orig.get("friction")),
                        "rationale": orig.get("rationale")},
            "evidence_ids": orig.get("evidence_ids", []),
        })
    return rows


def _fmt_rate(block):
    r = block["rate"]
    return "n/a (n=0)" if r is None else "%.1f%% (%d/%d)" % (r * 100, block["agree"], block["n"])


def _fmt_kappa(block):
    if block["quadratic_weighted_kappa"] is None:
        return "null (%s)" % block["quadratic_weighted_kappa_note"]
    return "%.3f (n=%d both-assessed)" % (block["quadratic_weighted_kappa"], block["both_assessed_n"])


EVIDENCE_CLASS_LABELS = (
    ("verbatim_reviewed_events", "verbatim reviewed_events text"),
    ("supplement_recovered",
     "recovered in the supplement (local hearing PDF pages, or the speech database)"),
    ("retext_local_speechdb", "recovered from the speech database in the local retext"),
    ("retext_pdf_page", "recovered from a local PDF page extract in the retext"),
    ("retext_fetched_web", "recovered from a fetched web page"),
    ("no_text_available", "no text available (packet carried only `(no text)` rows)"),
)


def _retext_source_class(row):
    """Which recovery source produced ONE manifest["retext"]["rows"] entry,
    read from the row's own shape -- never batch-id sniffing (the previous
    approach here), which breaks the moment a new recovery source's
    batches start at a number another family already used, or an existing
    family's numbering shifts: "rule"/"rowid" is the LOCAL speeches-table
    pass (build_kit_retext)'s own row shape; an explicit "source": "pdf" is
    the PDF pass (build_kit_retext_pdf)'s own shape; "source_url" with
    neither of the above is the FETCHED-web pass
    (build_kit_retext_fetched)'s own shape -- each pass's retext_rows_log
    entry for a "recovered" row is shaped differently by construction, so
    this never guesses between them. Returns "retext_local_speechdb",
    "retext_pdf_page", or "retext_fetched_web"; None for a row shape none
    of the three sources has ever written (defensive -- surfaced via
    evidence_class_rows's own "unclassified" list, never guessed at)."""
    if "rule" in row or "rowid" in row:
        return "retext_local_speechdb"
    if row.get("source") == "pdf":
        return "retext_pdf_page"
    if "source_url" in row:
        return "retext_fetched_web"
    return None


def classify_final_packets(kit_dir, record_ids):
    """Class of the packet each record was ACTUALLY graded from -- i.e. after
    supersession, not the packet --build-kit first wrote.

    manifest.json carries no single "evidence class" field, so each class is
    re-derived from fields it does carry:

    * superseded -> the matching manifest["retext"]["rows"] "recovered" row
      for that record says which recovery pass produced the final packet
      (_retext_source_class, read from the row's own shape).
    * never superseded but present in `retext.rows` -> it was checked for a
      "(no text)" row and nothing was recovered, so the graded packet still
      carried only "(no text)": the honest gap class, never imputed.
    * never superseded and listed in `evidence_missing_in_repo` -> its text
      came from --build-kit-supplement (that list IS the supplement's set).
    * everything else -> the main kit's verbatim reviewed_events text.

    Pass A's maps are used throughout: manifest.superseded["A"] and ["B"] key
    the same record ids (both passes are superseded together or not at all).
    Returns {record_id: class_key}, or None when the kit files needed are
    absent -- the report then omits the table rather than guessing."""
    kit_dir = Path(kit_dir)
    manifest_path, batches_path = kit_dir / "manifest.json", kit_dir / "batches.json"
    if not manifest_path.exists() or not batches_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    superseded = (manifest.get("superseded") or {}).get("A") or {}
    retext_rows = (manifest.get("retext") or {}).get("rows") or []
    retext_checked = {row["record_id"] for row in retext_rows}
    supplement = {row["record_id"]
                  for row in (manifest.get("evidence_missing_in_repo") or [])}
    source_class_by_record = {}
    for row in retext_rows:
        if row.get("status") != "recovered":
            continue
        cls = _retext_source_class(row)
        if cls is not None:
            source_class_by_record.setdefault(row["record_id"], cls)

    classes = {}
    for rid in record_ids:
        if rid in superseded:
            classes[rid] = source_class_by_record.get(rid, "retext_fetched_web")
        elif rid in retext_checked:
            classes[rid] = "no_text_available"
        elif rid in supplement:
            classes[rid] = "supplement_recovered"
        else:
            classes[rid] = "verbatim_reviewed_events"
    return classes


def evidence_class_rows(classes, record_ids, pass_a, pass_b):
    """One row per class: how many records were graded from that evidence
    class, and how many of those BOTH passes called unassessable on BOTH
    axes. A record missing from either pass is not counted as unassessable
    (a missing response is a failure, not a judgement) -- same rule as
    axis_agreement. Also returns any record whose class is unrecognised, so
    a class set that fails to cover the kit is visible instead of silent."""
    rows = []
    for key, label in EVIDENCE_CLASS_LABELS:
        ids = [rid for rid in record_ids if classes.get(rid) == key]
        both_unassessable = 0
        for rid in ids:
            ga, gb = pass_a.get(rid), pass_b.get(rid)
            if ga is None or gb is None:
                continue
            if all(g.get(dim) == "unassessable" for g in (ga, gb)
                   for dim in ("affinity", "friction")):
                both_unassessable += 1
        rows.append({"class": key, "label": label, "n_records": len(ids),
                     "unassessable_both_axes_both_passes": both_unassessable})
    known = {key for key, _ in EVIDENCE_CLASS_LABELS}
    unclassified = [rid for rid in record_ids if classes.get(rid) not in known]
    return rows, unclassified


def build_regrade_report(agreement, queue, meta, failures, evidence_class_table=None):
    lines = ["STATUS: EXPLORATORY. Two blind passes of one model over one rubric measure that "
            "rubric's own consistency, not human inter-rater reliability.",
            "",
            "**Blind re-grade, v6 chamber-degree records (P1-12)**", "",
            "Records in kit: %d. Failures (missing/invalid responses, never imputed): %d"
            % (meta.get("n_records", agreement["n_records"]), len(failures))]
    for comparison, label in (("between_passes", "Pass A vs pass B"),
                              ("pass_a_vs_original", "Pass A vs original v6"),
                              ("pass_b_vs_original", "Pass B vs original v6")):
        lines.append("")
        lines.append("### %s" % label)
        for dim in ("affinity", "friction"):
            block = agreement[comparison][dim]
            lines.append("- **%s** (n=%d): assessability %s; exact %s; within-1 %s; QWK %s"
                         % (dim, block["n_total"], _fmt_rate(block["assessability_agreement"]),
                            _fmt_rate(block["exact_agreement"]), _fmt_rate(block["within_1_agreement"]),
                            _fmt_kappa(block)))
            if block["missing"]:
                lines.append("  missing from this comparison (%d): %s"
                             % (len(block["missing"]), ", ".join(block["missing"])))
    if evidence_class_table:
        rows, unclassified = evidence_class_table["rows"], evidence_class_table["unclassified"]
        total = sum(r["n_records"] for r in rows)
        total_unassessable = sum(r["unassessable_both_axes_both_passes"] for r in rows)
        lines.append("")
        lines.append("### Evidence class of the packet each record was graded from")
        lines.append("")
        lines.append("Class of the FINAL packet (after supersession), not the packet "
                     "--build-kit first wrote. The last column counts records both passes "
                     "called unassessable on BOTH axes.")
        lines.append("")
        lines.append("| evidence class | records | unassessable both axes, both passes |")
        lines.append("| --- | ---: | ---: |")
        for row in rows:
            lines.append("| %s | %d | %d |" % (row["label"], row["n_records"],
                                               row["unassessable_both_axes_both_passes"]))
        lines.append("| **total** | **%d** | **%d** |" % (total, total_unassessable))
        if unclassified:
            lines.append("")
            lines.append("Unclassified (not covered by any class above, %d): %s"
                         % (len(unclassified), ", ".join(unclassified)))
    lines.append("")
    lines.append("### Disagreement queue for Paul (%d of %d records)"
                 % (len(queue), meta.get("n_records", agreement["n_records"])))
    if not queue:
        lines.append("(none)")
    for row in queue:
        lines.append("")
        lines.append("- **%s**" % row["record_id"])
        lines.append("  original: affinity=%s friction=%s -- %s"
                     % (row["original"]["affinity"], row["original"]["friction"],
                        (row["original"]["rationale"] or "")[:200]))
        for tag in ("pass_a", "pass_b"):
            p = row[tag]
            if p is None:
                lines.append("  %s: MISSING" % tag)
            else:
                lines.append("  %s: affinity=%s friction=%s -- %s"
                             % (tag, p["affinity"], p["friction"], (p["rationale"] or "")[:200]))
        lines.append("  evidence_ids: %s" % ", ".join(row["evidence_ids"]))
    return "\n".join(lines) + "\n"


def apply_supersession(by_pass, failures, superseded):
    """Task-required --ingest extension: a superseded item's response is
    ignored once its replacement's response exists, and counted as a
    `no_text_packet` failure otherwise; agreement tables use the
    replacement's response. `superseded` is manifest.json's own
    {"A": {old_item_id: new_item_id}, "B": {...}} (build_kit_retext's
    output) -- absent or empty reproduces the pre-retext behaviour exactly
    (nothing to reconcile).

    Every raw failure entry for either side of a superseded pair (the old
    "(no text)" item_id and its "#retext" replacement) is dropped first --
    neither one's raw missing/invalid status is meaningful on its own once
    superseded -- then exactly one outcome is re-derived per pair, per pass:
    the replacement's (valid) response takes over the OLD item_id's slot in
    by_pass (so compute_agreement/disagreement_queue, which key everything
    by the original v6 record id, need no changes at all), or, when the
    replacement has no usable response yet, a single `no_text_packet`
    failure is recorded for the old item_id. Returns (effective_by_pass,
    effective_failures); never mutates its inputs."""
    superseded = superseded or {}
    effective_by_pass = {"A": dict(by_pass.get("A", {})), "B": dict(by_pass.get("B", {}))}
    superseded_ids = {pass_tag: set() for pass_tag in ("A", "B")}
    for pass_tag in ("A", "B"):
        for old_id, new_id in superseded.get(pass_tag, {}).items():
            superseded_ids[pass_tag].add(old_id)
            superseded_ids[pass_tag].add(new_id)

    effective_failures = [f for f in failures if f["item_id"] not in superseded_ids.get(f["pass"], ())]

    for pass_tag in ("A", "B"):
        for old_id, new_id in superseded.get(pass_tag, {}).items():
            effective_by_pass[pass_tag].pop(old_id, None)
            # Pop (not get) new_id unconditionally: it must never survive as
            # its OWN key in the reconciled dict either way -- only ever
            # re-seated under old_id, or absent entirely.
            replacement = effective_by_pass[pass_tag].pop(new_id, None)
            if replacement is not None:
                effective_by_pass[pass_tag][old_id] = replacement
            else:
                effective_failures.append({"item_id": old_id, "pass": pass_tag,
                                          "reason": "no_text_packet",
                                          "replacement_item_id": new_id})
    return effective_by_pass, effective_failures


def run_ingest(out_dir, records_path, log=print):
    kit_dir = Path(out_dir) / "grading_kit"
    meta, items = load_index(kit_dir)
    schema = record_grade_schema()
    by_pass, failures = read_responses(items, schema)

    manifest_path = kit_dir / "manifest.json"
    if manifest_path.exists():
        superseded = json.loads(manifest_path.read_text(encoding="utf-8")).get("superseded")
        if superseded:
            by_pass, failures = apply_supersession(by_pass, failures, superseded)

    records = load_records(records_path)
    records_by_id = {r["id"]: r for r in records}
    kit_record_ids = sorted({it["item_id"] for it in items
                             if not it["item_id"].endswith(RETEXT_ITEM_SUFFIX)})
    original = {rid: {"affinity": _norm_original_degree(records_by_id[rid].get("affinity")),
                      "friction": _norm_original_degree(records_by_id[rid].get("friction"))}
               for rid in kit_record_ids}

    bg.write_ndjson(Path(out_dir) / "pass_A.ndjson",
                    [dict(id=rid, **by_pass["A"][rid]) for rid in sorted(by_pass["A"])])
    bg.write_ndjson(Path(out_dir) / "pass_B.ndjson",
                    [dict(id=rid, **by_pass["B"][rid]) for rid in sorted(by_pass["B"])])

    agreement = compute_agreement(kit_record_ids, by_pass["A"], by_pass["B"], original)
    agreement["failures"] = failures
    bg.write_json(Path(out_dir) / "agreement.json", agreement)

    queue = disagreement_queue(kit_record_ids, by_pass["A"], by_pass["B"], original, records_by_id)
    # Report-only: agreement.json's own numbers are left exactly as computed.
    classes = classify_final_packets(kit_dir, kit_record_ids)
    evidence_class_table = None
    if classes is not None:
        rows, unclassified = evidence_class_rows(classes, kit_record_ids,
                                                 by_pass["A"], by_pass["B"])
        evidence_class_table = {"rows": rows, "unclassified": unclassified}
    report = build_regrade_report(agreement, queue, {"n_records": len(kit_record_ids)},
                                  failures, evidence_class_table=evidence_class_table)
    (Path(out_dir) / "REPORT.md").write_text(report, encoding="utf-8", newline="\n")

    log("ingest: %d/%d pass A present, %d/%d pass B present, %d failures, %d queued for Paul"
       % (len(by_pass["A"]), len(kit_record_ids), len(by_pass["B"]), len(kit_record_ids),
          len(failures), len(queue)))
    return {"agreement": agreement, "failures": failures, "queue": queue,
           "pass_a_present": len(by_pass["A"]), "pass_b_present": len(by_pass["B"]),
           "n_records": len(kit_record_ids)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--build-kit", action="store_true", help="write the grading kit and exit")
    mode.add_argument("--build-kit-supplement", action="store_true",
                      help="recover verbatim primary-source text for records --build-kit "
                           "excluded and append new prompts/items/batches for them")
    mode.add_argument("--build-kit-retext", action="store_true",
                      help="recover LOCAL speeches-table text for '(no text)' evidence rows "
                           "already in the kit and append regrade_retext prompts/items/batches "
                           "for the records that gain at least one text-bearing row")
    mode.add_argument("--build-kit-retext-fetched", action="store_true",
                      help="recover FETCHED-WEB-PAGE text (grading_kit/fetched_sources/, "
                           "already downloaded -- no network access here) for '(no text)' "
                           "evidence rows --build-kit-retext's local speeches-table pass could "
                           "not retext, and append regrade_retext prompts/items/batches for the "
                           "records that gain at least one text-bearing row")
    mode.add_argument("--build-kit-retext-pdf", action="store_true",
                      help="recover LOCAL PDF page-text (grading_kit/fetched_sources/pdf/, "
                           "already downloaded and extracted -- no network access here) for "
                           "'(no text)' evidence rows neither earlier retext pass could recover, "
                           "and append regrade_retext prompts/items/batches for the records that "
                           "gain at least one text-bearing row; also records a pdf_available "
                           "note in manifest.json for every other PDF-cited record left on its "
                           "existing (non-PDF) replacement")
    mode.add_argument("--ingest", action="store_true",
                      help="read grading_kit/responses back and score agreement")
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    parser.add_argument("--evidence", default=str(DEFAULT_EVIDENCE))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--locator-path", default=str(DEFAULT_LOCATOR_PATH),
                        help="--build-kit-supplement/--build-kit-retext only: "
                             "exchange_context.ndjson-shaped source_locator index")
    parser.add_argument("--attribution-path", default=str(DEFAULT_ATTRIBUTION_PATH),
                        help="--build-kit-supplement/--build-kit-retext only: "
                             "reviewed_cases.ndjson-shaped attribution index")
    parser.add_argument("--db-path", default=str(SOCIAL_MEDIA_DB),
                        help="--build-kit-supplement/--build-kit-retext only: social_media.db "
                             "path (read-only)")
    parser.add_argument("--sources-dir", default=str(HEARING_SOURCES_DIR),
                        help="--build-kit-supplement/--build-kit-retext only: hearing "
                             "*.pages.json directory")
    args = parser.parse_args(argv)

    rubric_text = RUBRIC_PATH.read_text(encoding="utf-8")
    rubric_sha = bg.sha256_text(rubric_text)
    run_id = "mpr-v6-regrade-%s" % datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    started = time.time()
    mode_name = ("build-kit" if args.build_kit
                else "build-kit-supplement" if args.build_kit_supplement
                else "build-kit-retext" if args.build_kit_retext
                else "build-kit-retext-fetched" if args.build_kit_retext_fetched
                else "build-kit-retext-pdf" if args.build_kit_retext_pdf else "ingest")

    receipt = {"run_id": run_id, "mode": mode_name, "started_utc": bg.utc_now(),
              "rubric_path": str(RUBRIC_PATH), "rubric_sha256": rubric_sha,
              "out_dir": str(out_dir), "records_path": str(args.records),
              "evidence_path": str(args.evidence), "counts": {}, "failures": []}

    bg._glassbox_emit("research", "start", "blind_regrade_v6: mode=%s" % mode_name, run_id=run_id,
                      stage="member_personal_relationships/blind_regrade_v6",
                      detail="rubric %s" % rubric_sha, metadata={"out_dir": str(out_dir)})

    if args.build_kit:
        result = build_kit(out_dir, args.records, args.evidence, rubric_text)
        receipt["counts"] = {
            "records_total": result["meta"]["records_total"],
            "records_included": result["meta"]["records_included"],
            "records_excluded": result["meta"]["records_excluded"],
            "items_total": result["meta"]["items_total"],
            "batch_count": result["batch_count"],
        }
        receipt["forbidden_key_sweep"] = result["sweep"]
        receipt["kit_paths"] = {"kit_dir": result["kit_dir"], "index_path": result["index_path"],
                                "batches_path": result["batches_path"],
                                "schema_path": result["schema_path"],
                                "manifest_path": result["manifest_path"]}
        ok = result["sweep"]["ok"]
        summary = ("build-kit: %d/%d records included (%d items) in %d batches; forbidden-key "
                  "sweep %s"
                  % (result["meta"]["records_included"], result["meta"]["records_total"],
                     result["meta"]["items_total"], result["batch_count"],
                     "clean" if ok else "HITS FOUND"))
    elif args.build_kit_supplement:
        result = build_kit_supplement(out_dir, args.records, args.evidence, rubric_text,
                                      locator_path=args.locator_path,
                                      attribution_path=args.attribution_path,
                                      db_path=args.db_path, sources_dir=args.sources_dir)
        still_missing_records = len({m["record_id"] for m in result["still_missing"]})
        receipt["counts"] = {
            "recovered_records": result["recovered_records"],
            "still_missing_records": still_missing_records,
            "new_items": result["new_items"],
            "new_batches": len(result["new_batches"]),
        }
        receipt["forbidden_key_sweep"] = result["sweep"]
        receipt["recovered"] = result["recovered"]
        receipt["still_missing"] = result["still_missing"]
        receipt["kit_paths"] = {"kit_dir": result["kit_dir"], "index_path": result["index_path"],
                                "batches_path": result["batches_path"],
                                "manifest_path": result["manifest_path"]}
        ok = result["sweep"]["ok"]
        summary = ("build-kit-supplement: %d recovered, %d still missing, %d new items in %d new "
                  "batches (%s); forbidden-key sweep %s"
                  % (result["recovered_records"], still_missing_records, result["new_items"],
                     len(result["new_batches"]), ", ".join(result["new_batches"]),
                     "clean" if ok else "HITS FOUND"))
    elif args.build_kit_retext:
        result = build_kit_retext(out_dir, args.records, args.evidence, rubric_text,
                                  locator_path=args.locator_path,
                                  attribution_path=args.attribution_path,
                                  db_path=args.db_path, sources_dir=args.sources_dir)
        retext = result["retext"]
        rows_missing = [r for r in retext["rows"] if r["status"] != "recovered"]
        receipt["counts"] = {
            "records_checked": retext["records_checked"],
            "records_retexted": result["records_retexted"],
            "rows_recovered": len(retext["rows"]) - len(rows_missing),
            "rows_missing": len(rows_missing),
            "new_items": result["new_items"],
            "new_batches": len(result["new_batches"]),
        }
        receipt["forbidden_key_sweep"] = result["sweep"]
        receipt["retext"] = retext
        receipt["superseded"] = result["superseded"]
        receipt["kit_paths"] = {"kit_dir": result["kit_dir"], "index_path": result["index_path"],
                                "batches_path": result["batches_path"],
                                "manifest_path": result["manifest_path"]}
        ok = result["sweep"]["ok"]
        summary = ("build-kit-retext: %d records retexted (%d rows recovered / %d rows still "
                  "missing), %d new items in %d new batches (%s); forbidden-key sweep %s"
                  % (result["records_retexted"], receipt["counts"]["rows_recovered"],
                     receipt["counts"]["rows_missing"], result["new_items"],
                     len(result["new_batches"]), ", ".join(result["new_batches"]),
                     "clean" if ok else "HITS FOUND"))
    elif args.build_kit_retext_fetched:
        result = build_kit_retext_fetched(out_dir, args.records, args.evidence, rubric_text,
                                          locator_path=args.locator_path,
                                          attribution_path=args.attribution_path,
                                          db_path=args.db_path, sources_dir=args.sources_dir)
        rows_this_run = result["rows_this_run"]
        rows_missing_this_run = [r for r in rows_this_run if r["status"] != "recovered"]
        receipt["counts"] = {
            "records_retexted_this_run": result["records_retexted"],
            "records_retexted_total": result["retext"]["records_retexted"],
            "rows_recovered_this_run": len(rows_this_run) - len(rows_missing_this_run),
            "rows_missing_this_run": len(rows_missing_this_run),
            "new_items": result["new_items"],
            "new_batches": len(result["new_batches"]),
        }
        receipt["forbidden_key_sweep"] = result["sweep"]
        receipt["retext"] = result["retext"]
        receipt["superseded"] = result["superseded"]
        receipt["rows_this_run"] = rows_this_run
        receipt["kit_paths"] = {"kit_dir": result["kit_dir"], "index_path": result["index_path"],
                                "batches_path": result["batches_path"],
                                "manifest_path": result["manifest_path"]}
        ok = result["sweep"]["ok"]
        summary = ("build-kit-retext-fetched: %d records retexted (%d rows recovered / %d rows "
                  "still missing this run), %d new items in %d new batches (%s); forbidden-key "
                  "sweep %s"
                  % (result["records_retexted"], receipt["counts"]["rows_recovered_this_run"],
                     receipt["counts"]["rows_missing_this_run"], result["new_items"],
                     len(result["new_batches"]), ", ".join(result["new_batches"]),
                     "clean" if ok else "HITS FOUND"))
    elif args.build_kit_retext_pdf:
        result = build_kit_retext_pdf(out_dir, args.records, args.evidence, rubric_text,
                                      locator_path=args.locator_path,
                                      attribution_path=args.attribution_path,
                                      db_path=args.db_path, sources_dir=args.sources_dir)
        rows_this_run = result["rows_this_run"]
        rows_missing_this_run = [r for r in rows_this_run if r["status"] != "recovered"]
        receipt["counts"] = {
            "records_retexted_this_run": result["records_retexted"],
            "records_retexted_total": result["retext"]["records_retexted"],
            "rows_recovered_this_run": len(rows_this_run) - len(rows_missing_this_run),
            "rows_missing_this_run": len(rows_missing_this_run),
            "new_items": result["new_items"],
            "new_batches": len(result["new_batches"]),
            "pdf_available_total": len(result["pdf_available"]),
        }
        receipt["forbidden_key_sweep"] = result["sweep"]
        receipt["retext"] = result["retext"]
        receipt["superseded"] = result["superseded"]
        receipt["pdf_available"] = result["pdf_available"]
        receipt["rows_this_run"] = rows_this_run
        receipt["kit_paths"] = {"kit_dir": result["kit_dir"], "index_path": result["index_path"],
                                "batches_path": result["batches_path"],
                                "manifest_path": result["manifest_path"]}
        ok = result["sweep"]["ok"]
        summary = ("build-kit-retext-pdf: %d records retexted (%d rows recovered / %d rows still "
                  "missing this run), %d new items in %d new batches (%s), %d records noted "
                  "pdf_available; forbidden-key sweep %s"
                  % (result["records_retexted"], receipt["counts"]["rows_recovered_this_run"],
                     receipt["counts"]["rows_missing_this_run"], result["new_items"],
                     len(result["new_batches"]), ", ".join(result["new_batches"]),
                     len(result["pdf_available"]), "clean" if ok else "HITS FOUND"))
    else:
        result = run_ingest(out_dir, args.records)
        receipt["counts"] = {"records_total": result["n_records"],
                             "pass_a_present": result["pass_a_present"],
                             "pass_b_present": result["pass_b_present"],
                             "failures": len(result["failures"]),
                             "disagreements_queued": len(result["queue"])}
        receipt["failures"] = result["failures"]
        ok = not result["failures"]
        summary = ("ingest: %d/%d pass A, %d/%d pass B present, %d failures, %d queued for Paul"
                  % (result["pass_a_present"], result["n_records"], result["pass_b_present"],
                     result["n_records"], len(result["failures"]), len(result["queue"])))

    receipt["finished_utc"] = bg.utc_now()
    receipt["duration_ms"] = int((time.time() - started) * 1000)
    receipt["glassbox_run_id"] = run_id
    bg.write_json(out_dir / "run_receipt.json", receipt)

    bg._glassbox_emit("research", "ok" if ok else "warn", summary, run_id=run_id,
                      stage="member_personal_relationships/blind_regrade_v6",
                      duration_ms=receipt["duration_ms"],
                      detail=json.dumps(receipt["counts"], sort_keys=True),
                      metadata={"out_dir": str(out_dir)})
    print(summary)
    print(json.dumps(receipt["counts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
