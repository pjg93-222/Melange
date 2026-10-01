# -*- coding: utf-8 -*-
"""Blind two-pass grading harness for the development probability sample.

P0 item 3. Two independent model passes grade (a) the 180 development pairs on
the v6 affinity/friction degrees and (b) a per-mention calibration sample on the
frozen-v5 review keys. Disagreements are queued for Paul; nothing here assigns a
final label on its own.

Blinding is structural, not a promise. The prompt payload is built by WHITELIST
projection from the packet -- party, state, ideology, work/cosponsorship, cue
flags, model values, and the sampling design never enter the projection because
their keys are not on the whitelist -- and `assert_blind` then re-checks the
rendered prompt for forbidden key names and for the literal values of every
packet field the whitelist dropped. A blinding failure raises; it never warns.

The held-out split is sealed. `load_pair_packets` refuses any row whose split is
not 'development', loudly, before anything is prompted.

Import-safe: this module defines constants and functions only. Nothing runs, no
file is read, and no API call is made until `main()` is entered.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import random
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:  # Observation must never break the observed process.
    from fec.surfaces.glassbox_emit import emit as _glassbox_emit
except Exception:  # pragma: no cover - exercised only when fec/ is off sys.path
    def _glassbox_emit(*_a, **_k):
        return None

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUTPUTS = ROOT / "outputs" / "member_personal_relationships"
DEFAULT_PACKETS = OUTPUTS / "20260910_systematic_encounters" / "development_pair_packets.ndjson"
DEFAULT_CALIBRATION = OUTPUTS / "20260910_systematic_encounters" / "calibration_sample.ndjson"
DEFAULT_HIDDEN_CUES = OUTPUTS / "20260910_systematic_encounters" / "calibration_sample_hidden_cues.ndjson"
DEFAULT_OUT = OUTPUTS / "20260910_probability_sample_labels"
RUBRIC_PATH = HERE / "grading_rubric.md"
KEYS_JSON = Path(r"C:\Users\pgoff\OneDrive\Desktop\API Keys\keys.json")

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"

# Sonnet 5, not Paul's standing Haiku default: this is blind gold that the
# ordinal model will be scored against, so grading fidelity outranks unit cost.
# One line changes it; the price table must change with it.
MODEL = "claude-sonnet-5"
EFFORT = "medium"
MAX_TOKENS = 4000
# Measured precedent (fec/members/gen_demo_briefs.py:851-861): claude-sonnet-5
# left on adaptive thinking can spend an entire small max_tokens budget inside
# the thinking block and return HTTP 200 with stop_reason max_tokens and zero
# text. That is the one retry that must not be identical, so the max_tokens
# retry doubles the ceiling. Recorded per call in the receipt.
MAX_TOKENS_RETRY_MULTIPLIER = 2
PRICE_PER_MTOK = {"claude-sonnet-5": {"input": 2.0, "output": 10.0}}
CACHE_READ_DISCOUNT = 0.1      # cache reads bill at ~0.1x input
CACHE_WRITE_MULTIPLIER = 1.25  # cache writes bill at ~1.25x input

# --transport CLI selector values.
TRANSPORT_API = "api"
TRANSPORT_SUBAGENT_FILES = "subagent_files"

# Label recorded on every pass row and in the run receipt once grading was
# actually performed by independent Claude Code subagents reading an
# --export-prompts kit and writing back one JSON response per item, rather
# than by a live API call. Deliberately a DIFFERENT string from the
# --transport CLI value above: TRANSPORT_SUBAGENT_FILES selects the transport
# ("--transport subagent_files"); TRANSPORT_LABEL_SUBAGENT_FILES is what gets
# WRITTEN once that transport is used ("transport": "claude_code_subagent"),
# so nothing downstream can mistake a subagent-graded row for a metered
# model call.
TRANSPORT_LABEL_SUBAGENT_FILES = "claude_code_subagent"

# --export-prompts batch sizes: a grader (human or subagent) works one batch
# at a sitting. Pairs carry two directions and can hold dozens of excerpts
# each; calibration items are one short excerpt, hence the higher ceiling.
PAIR_KIT_BATCH_MAX = 16
CALIBRATION_KIT_BATCH_MAX = 40

DEGREE_VALUES = ["0", "1", "2", "3", "4", "unassessable"]
DIRECTIONS = ("a_to_b", "b_to_a")
DIMENSIONS = ("affinity", "friction")
INDICATORS = ["disclosure", "personal_reliance", "off_duty_contact", "concrete_support"]
COVERAGE_VALUES = ["adequate", "thin", "none"]
CONFIDENCE_VALUES = ["low", "medium", "high"]
SPEECH_PURPOSES = ["floor_debate", "floor_tribute", "procedural_yield", "hearing_question",
                   "hearing_exchange", "interview_answer", "other"]
PROMPTEDNESS = ["spontaneous", "prompted", "unknown"]
ESCALATION = ["none", "single_exchange", "sustained", "unknown"]
ALTERNATIVE_EXPLANATION = ["none", "institutional_courtesy", "ceremonial_tribute", "policy_dispute",
                           "procedural", "constituent_or_third_party", "other"]
REVIEW_KEYS = ["speaker_verified", "target_verified", "quoted_only", "content_status",
               "substantive_warmth", "personal_hostility", "promptedness", "ritual_language",
               "personal_act", "escalation", "reciprocity", "repair", "alternative_explanation"]
REVIEWER_BLINDING = {"model_scores": False, "personality_values": False, "work_scores": False}
PAIR_SAMPLING_BASIS = "development_probability_sample"
CALIBRATION_SAMPLING_BASIS = "systematic_encounter_review"
MERGED_LABEL_STATUS = "two_blind_model_passes_merged"
NO_EVIDENCE_LABEL_STATUS = "no_evidence_deterministic"

# Key names that must never appear anywhere in a prompt payload.
FORBIDDEN_KEYS = {
    "party", "parties", "same_party", "state", "same_state", "ideology", "dw_nominate", "dw1",
    "dw2", "dw1_distance", "nominate", "cosponsor", "cosponsors", "cosponsorship", "work",
    "work_score", "work_scores", "shared_bills", "log_shared_bills", "network_proximity",
    "direct_propensity", "weighted_shared_jaccard", "issue_similarity", "cue", "cues",
    "cue_warm", "cue_hostile", "hidden_cue", "hidden_cues", "hidden_cue_counts",
    "model_score", "model_scores", "model_values", "prediction", "predictions", "predicted",
    "personality", "personality_values", "big5", "big_five", "traits", "trait", "extraversion",
    "agreeableness", "openness", "neuroticism", "conscientiousness", "design_weight",
    "design_weight_population", "coverage_tier", "coverage_tiers", "coverage_bucket", "stratum",
    "split", "heldout", "held_out", "conditional_inclusion_probability", "affinity", "antagonism",
    "affinity_score", "antagonism_score", "arm",
}
# Packet fields the prompt whitelist deliberately drops. Their literal string
# values are re-checked against the rendered prompt.
PAIR_PACKET_REQUIRED = ("pair_id", "pair", "names", "split", "directions")
DIRECTION_REQUIRED = ("mentions",)
MENTION_REQUIRED = ("mention_id", "date", "source", "context_650")
CALIBRATION_REQUIRED = ("mention_id", "actor", "target", "actor_name", "target_name", "date",
                        "source", "context_650")


class SchemaDrift(Exception):
    """An input file does not match the schema this harness was built against."""


class BlindingError(Exception):
    """A prompt payload carried something the grader must never see."""


class SealedSplitError(Exception):
    """Something tried to read the held-out split."""


class NonRetryableAPIError(Exception):
    """A 4xx that will fail identically on every retry -- a malformed request, a
    dead key, an exhausted credit balance. Retrying it only doubles the bill and
    the wall clock, so the item fails on the first response."""


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_ndjson(path):
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SchemaDrift("%s:%d is not valid JSON: %s" % (path, lineno, exc))
    return rows


def write_ndjson(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True),
                    encoding="utf-8", newline="\n")
    return path


def seeded_order(items, pair_id, pass_tag):
    """Deterministic per (item, pass) shuffle. Same inputs -> same order, always."""
    digest = hashlib.blake2b(("%s|%s" % (pair_id, pass_tag)).encode("utf-8"), digest_size=8).digest()
    rng = random.Random(int.from_bytes(digest, "big"))
    out = list(items)
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------------------
# loaders -- fail loudly on drift, refuse the sealed split
# ---------------------------------------------------------------------------

def canonicalise_directions(row, where):
    """The producer keys directions '<actor_bioguide>-><target_bioguide>'
    (systematic_encounters.py:782); this harness works in a_to_b / b_to_a, where
    a is pair[0]. Accept either shape, map by the bioguides, and refuse anything
    that does not resolve to exactly the two directions of this pair."""
    directions = row["directions"]
    if not isinstance(directions, dict):
        raise SchemaDrift("%s directions is not an object" % where)
    if set(directions) == set(DIRECTIONS):
        return directions
    a, b = row["pair"]
    out = {}
    for key, block in directions.items():
        actor = target = None
        if isinstance(block, dict):
            actor, target = block.get("actor"), block.get("target")
        if actor is None and isinstance(key, str) and "->" in key:
            actor, target = key.split("->", 1)
        if actor == a and target == b:
            out["a_to_b"] = block
        elif actor == b and target == a:
            out["b_to_a"] = block
    if set(out) != set(DIRECTIONS):
        raise SchemaDrift(
            "%s directions %s do not resolve to both directions of pair %s; expected either "
            "%s or '<actor>-><target>' keys carrying actor/target bioguides"
            % (where, sorted(directions), row["pair"], list(DIRECTIONS)))
    return out


def hearing_dates(coappearances):
    """`dates` if the producer supplies it, else the date on each package entry
    (systematic_encounters.py:800 emits packages=[{package, date}] and no dates)."""
    if not isinstance(coappearances, dict):
        return []
    dates = [d for d in (coappearances.get("dates") or []) if d]
    if dates:
        return list(dates)
    return [p.get("date") for p in (coappearances.get("packages") or [])
            if isinstance(p, dict) and p.get("date")]


def load_pair_packets(path, limit=None):
    rows = read_ndjson(path)
    packets = []
    for i, row in enumerate(rows):
        where = "%s row %d" % (Path(path).name, i + 1)
        if not isinstance(row, dict):
            raise SchemaDrift("%s is not an object" % where)
        missing = [k for k in PAIR_PACKET_REQUIRED if k not in row]
        if missing:
            raise SchemaDrift("%s is missing required key(s) %s" % (where, missing))
        split = row.get("split")
        if split == "heldout":
            raise SealedSplitError(
                "%s carries split='heldout'. The held-out split is sealed: it may not be "
                "loaded, packeted, or graded. Fix the packet producer." % where)
        if split != "development":
            raise SchemaDrift("%s has split=%r; only 'development' is gradable here" % (where, split))
        if not isinstance(row["pair"], list) or len(row["pair"]) != 2:
            raise SchemaDrift("%s pair must be a 2-element list" % where)
        if not isinstance(row["names"], list) or len(row["names"]) != 2:
            raise SchemaDrift("%s names must be a 2-element list" % where)
        directions = canonicalise_directions(row, where)
        row = dict(row, directions=directions)
        for d in DIRECTIONS:
            block = directions[d]
            if not isinstance(block, dict):
                raise SchemaDrift("%s directions.%s is not an object" % (where, d))
            for k in DIRECTION_REQUIRED:
                if k not in block:
                    raise SchemaDrift("%s directions.%s is missing %r" % (where, d, k))
            if not isinstance(block["mentions"], list):
                raise SchemaDrift("%s directions.%s.mentions is not a list" % (where, d))
            seen = set()
            for j, mention in enumerate(block["mentions"]):
                if not isinstance(mention, dict):
                    raise SchemaDrift("%s directions.%s.mentions[%d] is not an object" % (where, d, j))
                miss = [k for k in MENTION_REQUIRED if k not in mention]
                if miss:
                    raise SchemaDrift("%s directions.%s.mentions[%d] missing %s" % (where, d, j, miss))
                mid = mention["mention_id"]
                if mid in seen:
                    raise SchemaDrift("%s directions.%s has duplicate mention_id %r" % (where, d, mid))
                seen.add(mid)
        packets.append(row)
        if limit and len(packets) >= limit:
            break
    if not packets:
        raise SchemaDrift("%s contained no gradable development packets" % path)
    return packets


def load_calibration(path, limit=None):
    rows = read_ndjson(path)
    out = []
    for i, row in enumerate(rows):
        where = "%s row %d" % (Path(path).name, i + 1)
        if not isinstance(row, dict):
            raise SchemaDrift("%s is not an object" % where)
        missing = [k for k in CALIBRATION_REQUIRED if k not in row]
        if missing:
            raise SchemaDrift("%s is missing required key(s) %s" % (where, missing))
        leaked = sorted(k for k in row if k.lower() in FORBIDDEN_KEYS)
        if leaked:
            raise BlindingError(
                "%s carries cue/design key(s) %s. Cue flags live in the hidden-cues file and "
                "must never reach a grading code path." % (where, leaked))
        out.append(row)
        if limit and len(out) >= limit:
            break
    if not out:
        raise SchemaDrift("%s contained no calibration mentions" % path)
    return out


def load_hidden_cues(path):
    """Read ONLY by the precision/recall scorer, never by a grading code path."""
    rows = read_ndjson(path)
    cues = {}
    for i, row in enumerate(rows):
        if "mention_id" not in row:
            raise SchemaDrift("%s row %d has no mention_id" % (Path(path).name, i + 1))
        warm = _cue_flag(row, ("cue_warm", "warm", "cue_warm_flag", "warm_cue"))
        hostile = _cue_flag(row, ("cue_hostile", "hostile", "cue_hostile_flag", "hostile_cue"))
        if warm is None or hostile is None:
            raise SchemaDrift(
                "%s row %d has no recognisable warm/hostile cue flag (looked for cue_warm / "
                "warm / cue_warm_flag and the hostile equivalents); found keys %s"
                % (Path(path).name, i + 1, sorted(row)))
        cues[row["mention_id"]] = {"cue_warm": warm, "cue_hostile": hostile}
    return cues


def _cue_flag(row, names):
    for name in names:
        if name in row:
            value = row[name]
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return value > 0
            if isinstance(value, list):
                return len(value) > 0
            if isinstance(value, str):
                return value.strip().lower() in ("1", "true", "yes", "y")
    return None


# ---------------------------------------------------------------------------
# blinding
# ---------------------------------------------------------------------------

def _all_keys(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for k, v in obj.items():
            acc.add(str(k))
            _all_keys(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _all_keys(v, acc)
    return acc


def _string_values(obj, acc=None):
    acc = set() if acc is None else acc
    if isinstance(obj, dict):
        for v in obj.values():
            _string_values(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            _string_values(v, acc)
    elif isinstance(obj, str):
        token = obj.strip()
        if len(token) >= 3 and not token.isdigit():
            acc.add(token)
    return acc


def assert_blind(payload, rendered, source=None, protected_text=()):
    """Raise unless `rendered` is clean. Never returns a warning.

    Three independent checks:
      1. no payload key is a forbidden name (the whitelist projection should
         already guarantee this; this proves it);
      2. the scaffolding -- the rendered prompt minus the verbatim source
         excerpts -- mentions no forbidden term. Excerpts are exempt from the
         term scan because a floor speech legitimately says "the State of
         North Dakota"; that is source text, not a leak;
      3. no string value that exists in the source packet but NOT in the
         whitelisted payload survives in the scaffolding once every value the
         payload legitimately prints has been subtracted from it. The
         subtraction matters: a dropped bioguide is a substring of the
         whitelisted pair_id, and that is not a leak.
    """
    bad_keys = sorted(k for k in _all_keys(payload) if k.lower() in FORBIDDEN_KEYS)
    if bad_keys:
        raise BlindingError("prompt payload carries forbidden key(s): %s" % bad_keys)
    scaffold = rendered
    for chunk in protected_text:
        if chunk:
            scaffold = scaffold.replace(chunk, " ")
    lowered = scaffold.lower()
    hits = sorted({k for k in FORBIDDEN_KEYS if re.search(r"\b%s\b" % re.escape(k), lowered)})
    if hits:
        raise BlindingError("prompt scaffolding mentions forbidden term(s): %s" % hits)
    if source is not None:
        printed = _string_values(payload)
        residual = scaffold
        for value in sorted(printed, key=len, reverse=True):
            residual = residual.replace(value, " ")
        for value in sorted(_string_values(source) - printed):
            if value in residual:
                raise BlindingError(
                    "prompt leaks the value of a dropped packet field: %r" % value[:80])
    return True


# ---------------------------------------------------------------------------
# prompt construction
# ---------------------------------------------------------------------------

PAIR_WHITELIST_TOP = {"pair_id", "names", "directions", "hearing_coappearances", "chambers"}
DIRECTION_WHITELIST = {"mentions", "mention_total", "mention_by_source"}
MENTION_WHITELIST = {"mention_id", "date", "source", "context_650"}
CALIBRATION_WHITELIST = {"mention_id", "actor_name", "target_name", "date", "source", "chamber",
                         "context_650"}


def chamber_statement(packet):
    """Per-member chamber when the producer supplies it; an honest hedge otherwise."""
    chambers = packet.get("chambers")
    names = packet["names"]
    if isinstance(chambers, dict):
        got = [chambers.get(b) for b in packet["pair"]]
        if all(isinstance(c, str) and c for c in got):
            return "%s served in the %s; %s served in the %s." % (names[0], got[0], names[1], got[1])
    if isinstance(chambers, list) and len(chambers) == 2 and all(isinstance(c, str) and c for c in chambers):
        return "%s served in the %s; %s served in the %s." % (names[0], chambers[0], names[1], chambers[1])
    stratum = packet.get("stratum")
    if isinstance(stratum, str) and "|" in stratum:
        tail = stratum.split("|")[-1]
        parts = [p.strip() for p in tail.split("+") if p.strip() in ("House", "Senate")]
        if len(parts) == 2:
            if parts[0] == parts[1]:
                return "Both members served in the %s." % parts[0]
            return ("One member served in the House and one in the Senate; which is which is not "
                    "supplied, so do not assume it.")
    return "Chamber context was not supplied for this pair."


def build_pair_payload(packet, pass_tag):
    """Whitelist projection. Nothing reaches the grader that is not built here."""
    names = packet["names"]
    payload = {
        "run": pass_tag,
        "pair_id": packet["pair_id"],
        "member_a": names[0],
        "member_b": names[1],
        "chamber_context": chamber_statement(packet),
        "directions": {},
    }
    co = packet.get("hearing_coappearances") or {}
    payload["hearing_coappearances"] = {
        "count": (co.get("count", 0) if isinstance(co, dict) else 0),
        "dates": hearing_dates(co)[:20],
    }
    for d in DIRECTIONS:
        block = packet["directions"][d]
        mentions = [{k: m.get(k) for k in MENTION_WHITELIST} for m in block["mentions"]]
        order = seeded_order([m["mention_id"] for m in mentions], packet["pair_id"], pass_tag)
        index = {m["mention_id"]: m for m in mentions}
        payload["directions"][d] = {
            "mentions_supplied": len(mentions),
            "mention_total": block.get("mention_total", len(mentions)),
            "mentions": [index[mid] for mid in order],
        }
    return payload


def render_pair_prompt(payload):
    lines = [
        "RUN TAG: %s" % payload["run"],
        "PAIR: %s" % payload["pair_id"],
        "MEMBER A: %s" % payload["member_a"],
        "MEMBER B: %s" % payload["member_b"],
        "CHAMBER CONTEXT: %s" % payload["chamber_context"],
        "HEARINGS AT WHICH BOTH APPEARED: %d%s" % (
            payload["hearing_coappearances"]["count"],
            (" (dates: %s)" % ", ".join(payload["hearing_coappearances"]["dates"]))
            if payload["hearing_coappearances"]["dates"] else ""),
        "",
    ]
    labels = {"a_to_b": ("MEMBER A", "MEMBER B"), "b_to_a": ("MEMBER B", "MEMBER A")}
    for d in DIRECTIONS:
        block = payload["directions"][d]
        speaker, about = labels[d]
        lines.append("=" * 72)
        lines.append("DIRECTION %s -- encounters in which %s speaks about or to %s"
                     % (d, speaker, about))
        # mention_total counts distinct TURNS (systematic_encounters.py:809 sums
        # mention_turns per source); the supplied excerpts are per-occurrence, so
        # a turn naming the colleague twice supplies two. Supplied may therefore
        # exceed the turn count, and "24 of 20" would read as an error. State the
        # two numbers as what they are instead.
        lines.append("excerpts supplied: %d; distinct turns recorded in this direction: %s"
                     % (block["mentions_supplied"], block["mention_total"]))
        lines.append("=" * 72)
        if not block["mentions"]:
            lines.append("(no encounters supplied for this direction)")
        for m in block["mentions"]:
            lines.append("")
            lines.append("[%s] %s | venue: %s" % (m["mention_id"], m["date"], m["source"]))
            lines.append(str(m["context_650"]).strip())
        lines.append("")
    lines.append("=" * 72)
    lines.append("Grade both directions. Return only the JSON object the schema requires.")
    return "\n".join(lines)


def pair_prompt(packet, pass_tag):
    payload = build_pair_payload(packet, pass_tag)
    rendered = render_pair_prompt(payload)
    protected = [str(m.get("context_650") or "").strip()
                 for d in DIRECTIONS for m in packet["directions"][d]["mentions"]]
    assert_blind(payload, rendered, source=packet, protected_text=protected)
    return payload, rendered


def build_calibration_payload(row, pass_tag):
    payload = {k: row.get(k) for k in CALIBRATION_WHITELIST}
    payload["run"] = pass_tag
    return payload


def render_calibration_prompt(payload):
    return "\n".join([
        "RUN TAG: %s" % payload["run"],
        "MENTION: %s" % payload["mention_id"],
        "ACTOR (the speaker being reviewed): %s" % payload["actor_name"],
        "TARGET (the colleague spoken about or to): %s" % payload["target_name"],
        "DATE: %s" % payload["date"],
        "VENUE: %s" % payload["source"],
        "CHAMBER: %s" % (payload.get("chamber") or "not supplied"),
        "",
        "EXCERPT",
        "-" * 72,
        str(payload["context_650"]).strip(),
        "-" * 72,
        "",
        "Review this excerpt only. Return only the JSON object the schema requires.",
    ])


def calibration_prompt(row, pass_tag):
    payload = build_calibration_payload(row, pass_tag)
    rendered = render_calibration_prompt(payload)
    assert_blind(payload, rendered, source=row,
                 protected_text=[str(row.get("context_650") or "").strip()])
    return payload, rendered


# ---------------------------------------------------------------------------
# output schemas
# ---------------------------------------------------------------------------

def _enum(values, desc=""):
    node = {"type": "string", "enum": list(values)}
    if desc:
        node["description"] = desc
    return node


def _obj(properties, desc=""):
    node = {"type": "object", "properties": properties, "required": sorted(properties),
            "additionalProperties": False}
    if desc:
        node["description"] = desc
    return node


def _range_schema(dim):
    return _obj({
        "lo": _enum(DEGREE_VALUES, "lowest %s degree the evidence still supports" % dim),
        "hi": _enum(DEGREE_VALUES, "highest %s degree the evidence still supports" % dim),
    }, "supported-interpretation range; both endpoints 'unassessable' when the degree is")


def direction_schema():
    props = {}
    for dim in DIMENSIONS:
        props["%s_degree" % dim] = _enum(DEGREE_VALUES, "%s degree 0-4, or unassessable" % dim)
        props["%s_range" % dim] = _range_schema(dim)
        props["%s_cited_mention_ids" % dim] = {
            "type": "array", "items": {"type": "string"},
            "description": "mention_ids supporting the %s degree; empty only when unassessable "
                           "or 0" % dim}
    props["closeness_trust_evidence"] = {
        "type": "array",
        "items": _obj({"indicator": _enum(INDICATORS),
                       "mention_ids": {"type": "array", "items": {"type": "string"}}}),
        "description": "descriptive closeness indicators actually shown by cited text"}
    props["ritual_courtesy_only"] = {
        "type": "boolean",
        "description": "true when every warmth cited is ceremonial courtesy with no spontaneous "
                       "specificity, concrete support, or reciprocity; caps affinity at 1"}
    props["episode_dates_used"] = {"type": "array", "items": {"type": "string"}}
    props["period_covered"] = _obj({"first": {"type": "string"}, "last": {"type": "string"}})
    return _obj(props)


def pair_grade_schema():
    return _obj({
        "directions": _obj({d: direction_schema() for d in DIRECTIONS}),
        "observation_coverage": _enum(COVERAGE_VALUES),
        "observation_coverage_basis": {"type": "string", "description": "one line: count, span, venues"},
        "neutral_assessment": _enum(["true", "false", "unknown"],
                                    "true ONLY with both degrees <=1 both directions AND repeated "
                                    "routine contact AND contextual evidence of an ordinary "
                                    "uninvested relationship; silence never supports it"),
        "mixed_ambivalent": {"type": "boolean",
                             "description": "affinity >=2 and friction >=2 in the same direction "
                                            "and the same period"},
        "rationale": {"type": "string", "description": "<=120 words, describes the cited text"},
        "confidence": _enum(CONFIDENCE_VALUES),
    })


def calibration_schema():
    return _obj({
        "speaker_verified": {"type": "boolean"},
        "target_verified": {"type": "boolean"},
        "quoted_only": {"type": "boolean"},
        "content_status": _enum(["resolved", "unresolved"]),
        "substantive_warmth": {"type": "boolean"},
        "personal_hostility": {"type": "boolean"},
        "promptedness": _enum(PROMPTEDNESS),
        "ritual_language": {"type": "boolean"},
        "personal_act": {"type": "boolean"},
        "escalation": _enum(ESCALATION),
        "reciprocity": {"type": "boolean"},
        "repair": {"type": "boolean"},
        "alternative_explanation": _enum(ALTERNATIVE_EXPLANATION),
        "speech_purpose": _enum(SPEECH_PURPOSES),
        "rationale": {"type": "string", "description": "one line"},
    })


def validate_against_schema(obj, schema, path="$"):
    """Minimal structural validator. Returns [] when valid, else a list of errors.

    Supports the JSON-Schema subset the Messages API accepts: type, enum,
    properties, required, additionalProperties:false, items, anyOf.
    """
    errors = []
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            if not validate_against_schema(obj, option, path):
                return []
        return ["%s matches none of the anyOf options" % path]
    kind = schema.get("type")
    if kind == "object":
        if not isinstance(obj, dict):
            return ["%s expected object, got %s" % (path, type(obj).__name__)]
        for key in schema.get("required", []):
            if key not in obj:
                errors.append("%s missing required %r" % (path, key))
        if schema.get("additionalProperties") is False:
            for key in obj:
                if key not in schema.get("properties", {}):
                    errors.append("%s has unexpected key %r" % (path, key))
        for key, sub in schema.get("properties", {}).items():
            if key in obj:
                errors.extend(validate_against_schema(obj[key], sub, "%s.%s" % (path, key)))
        return errors
    if kind == "array":
        if not isinstance(obj, list):
            return ["%s expected array, got %s" % (path, type(obj).__name__)]
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(obj):
                errors.extend(validate_against_schema(item, item_schema, "%s[%d]" % (path, i)))
        return errors
    if kind == "string":
        if not isinstance(obj, str):
            return ["%s expected string, got %s" % (path, type(obj).__name__)]
    elif kind == "boolean":
        if not isinstance(obj, bool):
            return ["%s expected boolean, got %s" % (path, type(obj).__name__)]
    elif kind == "integer":
        if isinstance(obj, bool) or not isinstance(obj, int):
            return ["%s expected integer, got %s" % (path, type(obj).__name__)]
    elif kind == "number":
        if isinstance(obj, bool) or not isinstance(obj, (int, float)):
            return ["%s expected number, got %s" % (path, type(obj).__name__)]
    elif kind == "null":
        if obj is not None:
            return ["%s expected null" % path]
    if "enum" in schema and obj not in schema["enum"]:
        errors.append("%s value %r is not in enum %s" % (path, obj, schema["enum"]))
    return errors


# ---------------------------------------------------------------------------
# normalisation and rubric invariants
# ---------------------------------------------------------------------------

def norm_degree(value):
    """'3' -> 3 ; 'unassessable' -> 'unassessable'."""
    if value == "unassessable":
        return "unassessable"
    return int(value)


def norm_range(degree, raw):
    """Returns (range_or_None, coercion_note_or_None). Never silently repairs."""
    if degree == "unassessable":
        return None, None
    lo, hi = raw.get("lo"), raw.get("hi")
    if lo == "unassessable" or hi == "unassessable":
        return [degree, degree], "range endpoint was unassessable on an assessed degree"
    lo, hi = int(lo), int(hi)
    note = None
    if lo > hi:
        lo, hi = hi, lo
        note = "range endpoints were inverted"
    if not (lo <= degree <= hi):
        lo, hi = min(lo, degree), max(hi, degree)
        note = "range widened to contain the degree"
    return [lo, hi], note


def normalise_pair_grade(raw):
    """Wire form -> persisted form, enforcing the rubric invariants that are
    mechanical. Every coercion is recorded in `coercions`; none is silent."""
    out = {"directions": {}, "coercions": []}
    for d in DIRECTIONS:
        block = raw["directions"][d]
        rec = {}
        for dim in DIMENSIONS:
            degree = norm_degree(block["%s_degree" % dim])
            rng, note = norm_range(degree, block["%s_range" % dim])
            if note:
                out["coercions"].append("%s.%s %s" % (d, dim, note))
            rec["%s_degree" % dim] = degree
            rec["%s_range" % dim] = rng
            rec["%s_cited_mention_ids" % dim] = list(block["%s_cited_mention_ids" % dim])
        rec["closeness_trust_evidence"] = block["closeness_trust_evidence"]
        rec["ritual_courtesy_only"] = bool(block["ritual_courtesy_only"])
        rec["episode_dates_used"] = list(block["episode_dates_used"])
        rec["period_covered"] = dict(block["period_covered"])
        out["directions"][d] = rec

    degrees = [out["directions"][d]["%s_degree" % dim] for d in DIRECTIONS for dim in DIMENSIONS]
    neutral = {"true": True, "false": False, "unknown": "unknown"}[raw["neutral_assessment"]]
    if neutral is True:
        if any(isinstance(x, int) and x >= 2 for x in degrees):
            neutral = "unknown"
            out["coercions"].append("neutral_assessment forced to unknown: a degree was >=2")
        elif any(x == "unassessable" for x in degrees):
            neutral = "unknown"
            out["coercions"].append("neutral_assessment forced to unknown: a degree was unassessable")
    out["neutral_assessment"] = neutral

    mixed = bool(raw["mixed_ambivalent"])
    both_high = any(
        isinstance(out["directions"][d]["affinity_degree"], int)
        and isinstance(out["directions"][d]["friction_degree"], int)
        and out["directions"][d]["affinity_degree"] >= 2
        and out["directions"][d]["friction_degree"] >= 2
        for d in DIRECTIONS)
    if mixed and not both_high:
        mixed = False
        out["coercions"].append("mixed_ambivalent forced to false: no direction had both degrees >=2")
    out["mixed_ambivalent"] = mixed
    out["mixed_flag_both_ge2_but_false"] = (both_high and not mixed)
    out["observation_coverage"] = raw["observation_coverage"]
    out["observation_coverage_basis"] = raw["observation_coverage_basis"]
    out["rationale"] = raw["rationale"]
    out["confidence"] = raw["confidence"]
    out["graded_via"] = "api"
    return out


# ---------------------------------------------------------------------------
# the no-evidence short circuit
#
# 135 of the 180 development packets carry zero mentions in BOTH directions
# (manifest.json packets.pairs_with_zero_mentions_in_both_directions), and 133
# of those also have no hearing at which both members appeared. Sending an empty
# packet to a grader buys nothing and risks the one failure mode this lane can
# least afford: a model asked to grade nothing, inventing something. A packet
# with no evidence at all gets a deterministic row instead -- both dimensions
# unassessable in both directions, coverage 'none', neutral 'unknown' -- written
# without an API call and counted separately in the receipt, so the graded
# denominator never silently absorbs the empty ones.
#
# The test is deliberately generous: ANY supplied excerpt, ANY recorded mention
# turn, or ANY hearing co-appearance sends the packet to the model. Only the
# genuinely empty short-circuit.
# ---------------------------------------------------------------------------

def direction_evidence(block):
    return {"mentions_supplied": len(block.get("mentions") or []),
            "mention_turns": int(block.get("mention_total") or 0)}


def packet_evidence(packet):
    """What this packet actually contains. `has_evidence` False means nothing
    to grade: no excerpt, no recorded turn, no shared hearing."""
    per = {d: direction_evidence(packet["directions"][d]) for d in DIRECTIONS}
    co = packet.get("hearing_coappearances")
    hearings = int((co or {}).get("count") or 0) if isinstance(co, dict) else 0
    supplied = sum(v["mentions_supplied"] for v in per.values())
    turns = sum(v["mention_turns"] for v in per.values())
    return {"directions": per,
            "hearing_coappearances": hearings,
            "mentions_supplied_total": supplied,
            "mention_turns_total": turns,
            "has_evidence": bool(supplied or turns or hearings)}


def has_evidence(packet):
    return packet_evidence(packet)["has_evidence"]


def partition_by_evidence(packets):
    """(gradable, empty) preserving input order. Nothing is dropped."""
    gradable, empty = [], []
    for packet in packets:
        (gradable if has_evidence(packet) else empty).append(packet)
    return gradable, empty


NO_EVIDENCE_BASIS = ("no encounter between these two members in the packet: no excerpt, no "
                     "recorded mention turn in either direction, and no hearing at which both "
                     "appeared")
NO_EVIDENCE_RATIONALE = ("Deterministic row, not a model judgement. The packet is empty, so "
                         "neither dimension is assessable in either direction. Absence of "
                         "evidence is not a 0 and is not neutrality; this is retrieval "
                         "nonresponse, recorded as such.")


def no_evidence_grade():
    """The deterministic stand-in, in the shape `normalise_pair_grade` returns."""
    grade = {"directions": {}, "coercions": []}
    for d in DIRECTIONS:
        rec = {}
        for dim in DIMENSIONS:
            rec["%s_degree" % dim] = "unassessable"
            rec["%s_range" % dim] = None
            rec["%s_cited_mention_ids" % dim] = []
        rec["closeness_trust_evidence"] = []
        rec["ritual_courtesy_only"] = False
        rec["episode_dates_used"] = []
        rec["period_covered"] = {"first": "", "last": ""}
        grade["directions"][d] = rec
    grade["neutral_assessment"] = "unknown"
    grade["mixed_ambivalent"] = False
    grade["mixed_flag_both_ge2_but_false"] = False
    grade["observation_coverage"] = "none"
    grade["observation_coverage_basis"] = NO_EVIDENCE_BASIS
    grade["rationale"] = NO_EVIDENCE_RATIONALE
    grade["confidence"] = "low"
    grade["graded_via"] = "no_evidence_short_circuit"
    return grade


def no_evidence_label_row(packet, meta):
    """A labels_v1 row for an empty packet. Same field names a merged row uses,
    so one file reads end to end, but `label_status` and `graded_via` say plainly
    that no model saw it and `pass_a`/`pass_b` are null rather than invented."""
    grade = no_evidence_grade()
    row = {
        "pair_id": packet["pair_id"],
        "pair": packet["pair"],
        "names": packet["names"],
        "split": packet["split"],
        "stratum": packet.get("stratum"),
        "design_weight": packet.get("design_weight"),
        "sampling_basis": PAIR_SAMPLING_BASIS,
        "reviewer_blinding": dict(REVIEWER_BLINDING),
        "label_status": NO_EVIDENCE_LABEL_STATUS,
        "graded_via": "no_evidence_short_circuit",
        "api_calls": 0,
        "evidence": packet_evidence(packet),
        "directions": {},
        "adjudication_needed": False,
        "adjudication_reasons": [],
    }
    row.update(meta)
    for d in DIRECTIONS:
        block = {"ritual_courtesy_only": False,
                 "ritual_courtesy_mismatch": False,
                 "closeness_trust_evidence_pass_a": [],
                 "closeness_trust_evidence_pass_b": [],
                 "episode_dates_used": [],
                 "period_covered_pass_a": {"first": "", "last": ""},
                 "period_covered_pass_b": {"first": "", "last": ""}}
        for dim in DIMENSIONS:
            entry = {"pass_a": None, "pass_b": None, "value": "unassessable",
                     "merge_rule": "no_evidence", "adjudication_needed": False,
                     "adjudication_reason": None, "range": None,
                     "cited_mention_ids_pass_a": [], "cited_mention_ids_pass_b": []}
            if dim == "affinity":
                entry["ritual_cap_applied"] = False
            block[dim] = entry
        row["directions"][d] = block
    for field in ("neutral_assessment", "mixed_ambivalent", "observation_coverage"):
        row[field] = {"pass_a": None, "pass_b": None, "value": grade[field],
                      "adjudication_needed": False}
    row["confidence"] = {"pass_a": None, "pass_b": None, "value": grade["confidence"]}
    row["rationale_pass_a"] = None
    row["rationale_pass_b"] = None
    row["rationale"] = grade["rationale"]
    row["observation_coverage_basis_pass_a"] = None
    row["observation_coverage_basis_pass_b"] = None
    row["observation_coverage_basis"] = grade["observation_coverage_basis"]
    return row


def label_summary(rows):
    """Counts over the written label rows: how each row was produced, how many
    directions are assessable per dimension, and the neutral/mixed tallies. The
    denominators the report has to print come from here, not from a guess."""
    summary = {
        "rows": len(rows),
        "by_label_status": {},
        "by_graded_via": {},
        "assessability": {dim: {d: {"assessable": 0, "unassessable": 0, "adjudication_pending": 0}
                                for d in DIRECTIONS} for dim in DIMENSIONS},
        "degree_histogram": {dim: {d: {} for d in DIRECTIONS} for dim in DIMENSIONS},
        "neutral_assessment": {"true": 0, "false": 0, "unknown": 0, "adjudication_pending": 0},
        "mixed_ambivalent": {"true": 0, "false": 0, "adjudication_pending": 0},
        "observation_coverage": {},
        "pairs_needing_adjudication": 0,
    }
    for row in rows:
        status = row.get("label_status")
        via = row.get("graded_via")
        summary["by_label_status"][status] = summary["by_label_status"].get(status, 0) + 1
        summary["by_graded_via"][via] = summary["by_graded_via"].get(via, 0) + 1
        if row.get("adjudication_needed"):
            summary["pairs_needing_adjudication"] += 1
        for d in DIRECTIONS:
            for dim in DIMENSIONS:
                value = row["directions"][d][dim]["value"]
                cell = summary["assessability"][dim][d]
                if value is None:
                    cell["adjudication_pending"] += 1
                elif value == "unassessable":
                    cell["unassessable"] += 1
                else:
                    cell["assessable"] += 1
                key = "adjudication_pending" if value is None else str(value)
                hist = summary["degree_histogram"][dim][d]
                hist[key] = hist.get(key, 0) + 1
        for field in ("neutral_assessment", "mixed_ambivalent"):
            value = row[field]["value"]
            key = "adjudication_pending" if value is None else str(value).lower()
            if key in summary[field]:
                summary[field][key] += 1
            else:
                summary[field][key] = summary[field].get(key, 0) + 1
        coverage = row["observation_coverage"]["value"]
        key = "adjudication_pending" if coverage is None else str(coverage)
        summary["observation_coverage"][key] = summary["observation_coverage"].get(key, 0) + 1
    return summary


def most_evidenced(packets, n):
    """The n packets carrying the most evidence, deterministically ordered.

    A smoke test drawn off the top of the file would land on empty packets, make
    zero API calls, and prove nothing; a smoke test exists to exercise the live
    call path on real material."""
    scored = []
    for packet in packets:
        ev = packet_evidence(packet)
        scored.append((-ev["mention_turns_total"], -ev["mentions_supplied_total"],
                       -ev["hearing_coappearances"], packet["pair_id"], packet))
    scored.sort(key=lambda item: item[:4])
    return [item[4] for item in scored[:n]]


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------

def load_api_key(index=0):
    """Read the key. Never printed, never logged, never written to an output."""
    document = json.loads(KEYS_JSON.read_text(encoding="utf-8"))
    keys = ((document.get("anthropic") or {}).get("keys")) or []
    if index >= len(keys):
        raise SystemExit("anthropic.keys[%d] is not present in the key store" % index)
    key = str(keys[index]).strip()
    if not key:
        raise SystemExit("anthropic.keys[%d] is empty" % index)
    return key


class GradingClient:
    """One call path, chosen once. Both paths send the identical request body."""

    transport = TRANSPORT_API

    def __init__(self, key, model=MODEL, effort=EFFORT, max_tokens=MAX_TOKENS, prefer_sdk=True):
        self.model = model
        self.effort = effort
        self.max_tokens = max_tokens
        self._key = key
        self._lock = threading.Lock()
        self.sdk = None
        self.path = "urllib"
        if prefer_sdk:
            try:
                import anthropic  # noqa: F401  (deferred: presence is the probe)
                self.sdk = anthropic.Anthropic(api_key=key, max_retries=0)
                self.path = "anthropic-sdk %s" % getattr(anthropic, "__version__", "?")
            except Exception:
                self.sdk = None
                self.path = "urllib"

    def _body(self, system_text, user_text, schema, max_tokens):
        return {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": [{"type": "text", "text": system_text,
                        "cache_control": {"type": "ephemeral"}}],
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort,
                              "format": {"type": "json_schema", "schema": schema}},
            "messages": [{"role": "user", "content": user_text}],
        }

    def _once(self, body):
        """One HTTP round trip with transport retries. Returns a normalised dict."""
        delay, last = 2.0, None
        for attempt in range(5):
            try:
                if self.sdk is not None:
                    resp = self.sdk.messages.create(**body)
                    return {"stop_reason": resp.stop_reason,
                            "text": "".join(b.text for b in resp.content if b.type == "text"),
                            "usage": {"input_tokens": resp.usage.input_tokens,
                                      "output_tokens": resp.usage.output_tokens,
                                      "cache_creation_input_tokens":
                                          getattr(resp.usage, "cache_creation_input_tokens", 0) or 0,
                                      "cache_read_input_tokens":
                                          getattr(resp.usage, "cache_read_input_tokens", 0) or 0},
                            "stop_details": (resp.stop_details.to_dict()
                                             if getattr(resp, "stop_details", None) is not None
                                             else None),
                            "transport_attempts": attempt + 1}
                request = urllib.request.Request(
                    API_URL, data=json.dumps(body).encode("utf-8"), method="POST")
                request.add_header("content-type", "application/json")
                request.add_header("x-api-key", self._key)
                request.add_header("anthropic-version", API_VERSION)
                with urllib.request.urlopen(request, timeout=600) as handle:
                    payload = json.loads(handle.read().decode("utf-8"))
                return {"stop_reason": payload.get("stop_reason"),
                        "text": "".join(b.get("text", "") for b in payload.get("content", [])
                                        if b.get("type") == "text"),
                        "usage": {k: (payload.get("usage") or {}).get(k, 0) or 0
                                  for k in ("input_tokens", "output_tokens",
                                            "cache_creation_input_tokens",
                                            "cache_read_input_tokens")},
                        "stop_details": payload.get("stop_details"),
                        "transport_attempts": attempt + 1}
            except Exception as exc:  # retry only what is retryable
                status = _status_of(exc)
                last = "%s: %s" % (type(exc).__name__, str(exc)[:300])
                if status is not None and 400 <= status < 500 and status not in (408, 409, 429):
                    raise NonRetryableAPIError(last)
                retryable = status in (408, 409, 429) or (status is not None and status >= 500) \
                    or status is None and isinstance(exc, (urllib.error.URLError, TimeoutError, OSError))
                if not retryable or attempt == 4:
                    raise RuntimeError(last)
                time.sleep(min(delay + random.uniform(0, 1), 60.0))
                delay *= 2
        raise RuntimeError(last or "exhausted transport retries")

    def count_input_tokens(self, system_text, user_text, schema):
        """Free endpoint. Measures the exact billable input size without spending.

        Returns (input_tokens, shape) where shape says whether the counter
        accepted the full grading request or only its system+messages core.
        """
        core = {"model": self.model,
                "system": [{"type": "text", "text": system_text,
                            "cache_control": {"type": "ephemeral"}}],
                "messages": [{"role": "user", "content": user_text}]}
        full = dict(core, thinking={"type": "adaptive"},
                    output_config={"effort": self.effort,
                                   "format": {"type": "json_schema", "schema": schema}})
        for shape, body in (("full_request", full), ("system_and_messages_only", core)):
            try:
                if self.sdk is not None:
                    return self.sdk.messages.count_tokens(**body).input_tokens, shape
                request = urllib.request.Request(
                    API_URL + "/count_tokens", data=json.dumps(body).encode("utf-8"),
                    method="POST")
                request.add_header("content-type", "application/json")
                request.add_header("x-api-key", self._key)
                request.add_header("anthropic-version", API_VERSION)
                with urllib.request.urlopen(request, timeout=120) as handle:
                    return json.loads(handle.read().decode("utf-8"))["input_tokens"], shape
            except Exception as exc:
                last = "%s: %s" % (type(exc).__name__, str(exc)[:200])
        raise RuntimeError(last)

    def call(self, system_text, user_text, schema):
        """Content-level policy: refusal / max_tokens / invalid JSON -> retry once."""
        attempts, usage_total = [], {"input_tokens": 0, "output_tokens": 0,
                                     "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0}
        max_tokens = self.max_tokens
        for content_attempt in range(2):
            started = time.time()
            try:
                result = self._once(self._body(system_text, user_text, schema, max_tokens))
            except NonRetryableAPIError as exc:
                attempts.append({"attempt": content_attempt + 1, "outcome": "non_retryable_4xx",
                                 "error": str(exc)[:400],
                                 "duration_ms": int((time.time() - started) * 1000)})
                break
            except Exception as exc:
                attempts.append({"attempt": content_attempt + 1, "outcome": "transport_failed",
                                 "error": str(exc)[:400],
                                 "duration_ms": int((time.time() - started) * 1000)})
                continue
            for k in usage_total:
                usage_total[k] += result["usage"].get(k, 0)
            record = {"attempt": content_attempt + 1, "stop_reason": result["stop_reason"],
                      "max_tokens_sent": max_tokens, "usage": result["usage"],
                      "transport_attempts": result["transport_attempts"],
                      "duration_ms": int((time.time() - started) * 1000)}
            if result["stop_reason"] == "refusal":
                record["outcome"] = "refusal"
                record["stop_details"] = result.get("stop_details")
                attempts.append(record)
                continue
            if result["stop_reason"] == "max_tokens":
                record["outcome"] = "max_tokens"
                attempts.append(record)
                max_tokens = max_tokens * MAX_TOKENS_RETRY_MULTIPLIER
                continue
            try:
                data = json.loads(result["text"])
            except Exception as exc:
                record["outcome"] = "unparseable_json"
                record["error"] = str(exc)[:200]
                attempts.append(record)
                continue
            errors = validate_against_schema(data, schema)
            if errors:
                record["outcome"] = "schema_invalid"
                record["error"] = "; ".join(errors[:5])
                attempts.append(record)
                continue
            record["outcome"] = "ok"
            attempts.append(record)
            return {"ok": True, "data": data, "attempts": attempts, "usage": usage_total,
                    "raw_text": result["text"]}
        return {"ok": False, "data": None, "attempts": attempts, "usage": usage_total,
                "raw_text": None,
                "error": attempts[-1].get("outcome", "failed") if attempts else "failed"}


def _status_of(exc):
    status = getattr(exc, "status_code", None)
    if status is None:
        status = getattr(exc, "code", None)
    response = getattr(exc, "response", None)
    if status is None and response is not None:
        status = getattr(response, "status_code", None)
    return status if isinstance(status, int) else None


# ---------------------------------------------------------------------------
# file transport -- grading performed by independent Claude Code subagents
# ---------------------------------------------------------------------------

_RUN_TAG_HEADER_RE = re.compile(r"^RUN TAG:\s*(.+)$", re.MULTILINE)
_PAIR_ID_HEADER_RE = re.compile(r"^PAIR:\s*(.+)$", re.MULTILINE)
_MENTION_ID_HEADER_RE = re.compile(r"^MENTION:\s*(.+)$", re.MULTILINE)


def _item_identity(user_text):
    """(item_id, phase, pass_tag), recovered from a rendered prompt's OWN
    header lines rather than from a caller-supplied id. render_pair_prompt's
    first two lines are always 'RUN TAG: <A|B>' then 'PAIR: <pair_id>';
    render_calibration_prompt's are 'RUN TAG: <A|B>' then
    'MENTION: <mention_id>'. Recovering identity this way -- instead of adding
    an item_id parameter to GradingClient.call -- keeps call(system_text,
    user_text, schema) the one signature every transport implements: the
    live API client, every test double in test_blind_grading.py, and this
    file transport."""
    run_match = _RUN_TAG_HEADER_RE.search(user_text)
    if not run_match:
        raise ValueError("prompt carries no 'RUN TAG:' header; cannot identify the pass")
    pass_tag = run_match.group(1).strip()
    pair_match = _PAIR_ID_HEADER_RE.search(user_text)
    if pair_match:
        return pair_match.group(1).strip(), "pairs", pass_tag
    mention_match = _MENTION_ID_HEADER_RE.search(user_text)
    if mention_match:
        return mention_match.group(1).strip(), "calibration", pass_tag
    raise ValueError("prompt carries neither a 'PAIR:' nor a 'MENTION:' header; cannot identify "
                     "the item")


class SubagentFileClient:
    """Drop-in replacement for GradingClient when the Anthropic key has no
    credit: the two blind grading passes are instead performed by independent
    Claude Code subagents, each reading one prompt file from an
    --export-prompts kit and writing back one JSON response per (pass,
    item_id) under a shared responses directory.

    `.call(system_text, user_text, schema)` returns the identical {"ok",
    "data", "attempts", "usage", "raw_text"} shape GradingClient.call returns,
    so run_pairs / run_calibration and everything downstream of them --
    normalise_pair_grade, merge_labels, the no_evidence rows, pair_agreement,
    the adjudication queue, calibration_gate, cue_precision_recall,
    build_report -- run completely unchanged.

    usage is always None, never a zero-usage dict: this was not a metered
    call, and None is exactly what sum_usage / estimate_cost already treat as
    contributing nothing (see sum_usage's `(rec.get("usage") or {})`), so a
    run graded this way totals to cost 0 with no special-casing of the cost
    math.
    """

    transport = TRANSPORT_LABEL_SUBAGENT_FILES

    def __init__(self, responses_dir):
        self.responses_dir = Path(responses_dir)

    def _paths(self, pass_tag, item_id):
        base = self.responses_dir / pass_tag
        return base / ("%s.json" % item_id), base / ("%s.error.txt" % item_id)

    @staticmethod
    def _write_error(error_path, outcome, message):
        error_path.parent.mkdir(parents=True, exist_ok=True)
        error_path.write_text("%s\n%s\n" % (outcome, message), encoding="utf-8", newline="\n")

    def call(self, system_text, user_text, schema):
        try:
            item_id, _phase, pass_tag = _item_identity(user_text)
        except ValueError as exc:
            return {"ok": False, "data": None, "usage": None, "raw_text": None,
                    "attempts": [{"attempt": 1, "outcome": "unidentifiable_prompt",
                                  "error": str(exc)}],
                    "error": "unidentifiable_prompt"}
        response_path, error_path = self._paths(pass_tag, item_id)
        if not response_path.exists():
            message = "no response file at %s" % response_path
            return {"ok": False, "data": None, "usage": None, "raw_text": None,
                    "attempts": [{"attempt": 1, "outcome": "response_file_missing",
                                  "error": message}],
                    "error": "response_file_missing"}
        raw_text = response_path.read_text(encoding="utf-8")
        try:
            data = json.loads(raw_text)
        except Exception as exc:
            message = "%s: %s" % (type(exc).__name__, str(exc)[:300])
            self._write_error(error_path, "unparseable_json", message)
            return {"ok": False, "data": None, "usage": None, "raw_text": raw_text,
                    "attempts": [{"attempt": 1, "outcome": "unparseable_json", "error": message}],
                    "error": "unparseable_json"}
        errors = validate_against_schema(data, schema)
        if errors:
            message = "; ".join(errors[:5])
            self._write_error(error_path, "schema_invalid", message)
            return {"ok": False, "data": None, "usage": None, "raw_text": raw_text,
                    "attempts": [{"attempt": 1, "outcome": "schema_invalid", "error": message}],
                    "error": "schema_invalid"}
        return {"ok": True, "data": data, "usage": None, "raw_text": raw_text,
                "attempts": [{"attempt": 1, "outcome": "ok"}]}


# ---------------------------------------------------------------------------
# agreement metrics
# ---------------------------------------------------------------------------

def quadratic_weighted_kappa(a, b, categories=5):
    """QWK on paired ordinal ratings. Perfect agreement -> 1.0 by convention."""
    n = len(a)
    if n == 0:
        return None
    observed = [[0] * categories for _ in range(categories)]
    for x, y in zip(a, b):
        observed[x][y] += 1
    hist_a = [sum(row) for row in observed]
    hist_b = [sum(observed[i][j] for i in range(categories)) for j in range(categories)]
    num = den = 0.0
    for i in range(categories):
        for j in range(categories):
            w = ((i - j) ** 2) / float((categories - 1) ** 2)
            num += w * observed[i][j]
            den += w * hist_a[i] * hist_b[j] / float(n)
    if den == 0:
        return 1.0 if num == 0 else 0.0
    return 1.0 - num / den


def cohen_kappa(a, b):
    labels = sorted({str(x) for x in a} | {str(x) for x in b})
    n = len(a)
    if n == 0:
        return None
    index = {lab: i for i, lab in enumerate(labels)}
    k = len(labels)
    table = [[0] * k for _ in range(k)]
    for x, y in zip(a, b):
        table[index[str(x)]][index[str(y)]] += 1
    po = sum(table[i][i] for i in range(k)) / float(n)
    pe = sum((sum(table[i]) / float(n)) * (sum(table[r][i] for r in range(k)) / float(n))
             for i in range(k))
    if pe == 1.0:
        return 1.0 if po == 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


def _rate(agree, n):
    return {"n": n, "agree": agree, "rate": (agree / float(n)) if n else None}


def dimension_agreement(pairs_a, pairs_b, direction, dimension):
    """pairs_a/pairs_b are {pair_id: normalised grade} for the same pair ids."""
    ids = [pid for pid in pairs_a if pid in pairs_b]
    assess_agree, both, exact, within1 = 0, [], 0, 0
    confusion = [[0] * 5 for _ in range(5)]
    for pid in ids:
        va = pairs_a[pid]["directions"][direction]["%s_degree" % dimension]
        vb = pairs_b[pid]["directions"][direction]["%s_degree" % dimension]
        ua, ub = (va == "unassessable"), (vb == "unassessable")
        if ua == ub:
            assess_agree += 1
        if not ua and not ub:
            both.append((va, vb))
            confusion[va][vb] += 1
            if va == vb:
                exact += 1
            if abs(va - vb) <= 1:
                within1 += 1
    return {
        "n": len(ids),
        "assessability_agreement": _rate(assess_agree, len(ids)),
        "both_assessed_n": len(both),
        "exact_agreement": _rate(exact, len(both)),
        "within_1_agreement": _rate(within1, len(both)),
        "quadratic_weighted_kappa": quadratic_weighted_kappa([x for x, _ in both],
                                                             [y for _, y in both]),
        "confusion_pass_a_rows_pass_b_cols": confusion,
    }


def pair_agreement(pairs_a, pairs_b, packets_by_id=None):
    ids = [pid for pid in pairs_a if pid in pairs_b]
    report = {"n_pairs_both_passes": len(ids), "dimensions": {}, "disagreements": []}
    for dim in DIMENSIONS:
        report["dimensions"][dim] = {d: dimension_agreement(pairs_a, pairs_b, d, dim)
                                     for d in DIRECTIONS}
    neutral = sum(1 for pid in ids
                  if pairs_a[pid]["neutral_assessment"] == pairs_b[pid]["neutral_assessment"])
    mixed = sum(1 for pid in ids
                if pairs_a[pid]["mixed_ambivalent"] == pairs_b[pid]["mixed_ambivalent"])
    coverage = sum(1 for pid in ids
                   if pairs_a[pid]["observation_coverage"] == pairs_b[pid]["observation_coverage"])
    report["neutral_assessment_agreement"] = _rate(neutral, len(ids))
    report["mixed_ambivalent_agreement"] = _rate(mixed, len(ids))
    report["observation_coverage_agreement"] = _rate(coverage, len(ids))
    report["ritual_courtesy_only_agreement"] = {
        d: _rate(sum(1 for pid in ids
                     if pairs_a[pid]["directions"][d]["ritual_courtesy_only"]
                     == pairs_b[pid]["directions"][d]["ritual_courtesy_only"]), len(ids))
        for d in DIRECTIONS}

    for pid in ids:
        a, b = pairs_a[pid], pairs_b[pid]
        for d in DIRECTIONS:
            for dim in DIMENSIONS:
                va = a["directions"][d]["%s_degree" % dim]
                vb = b["directions"][d]["%s_degree" % dim]
                category = None
                if (va == "unassessable") != (vb == "unassessable"):
                    category = "assessability_mismatch"
                elif va != "unassessable" and abs(va - vb) >= 2:
                    category = "degree_delta_ge2"
                if category:
                    report["disagreements"].append(
                        {"pair_id": pid, "direction": d, "dimension": dim, "category": category,
                         "pass_a": va, "pass_b": vb})
            if a["directions"][d]["ritual_courtesy_only"] != b["directions"][d]["ritual_courtesy_only"]:
                report["disagreements"].append(
                    {"pair_id": pid, "direction": d, "dimension": "affinity",
                     "category": "ritual_courtesy_mismatch",
                     "pass_a": a["directions"][d]["ritual_courtesy_only"],
                     "pass_b": b["directions"][d]["ritual_courtesy_only"]})
        if a["neutral_assessment"] != b["neutral_assessment"]:
            report["disagreements"].append(
                {"pair_id": pid, "direction": "pair", "dimension": "neutral_assessment",
                 "category": "neutral_mismatch",
                 "pass_a": a["neutral_assessment"], "pass_b": b["neutral_assessment"]})
        if a["mixed_ambivalent"] != b["mixed_ambivalent"]:
            report["disagreements"].append(
                {"pair_id": pid, "direction": "pair", "dimension": "mixed_ambivalent",
                 "category": "mixed_mismatch",
                 "pass_a": a["mixed_ambivalent"], "pass_b": b["mixed_ambivalent"]})
    counts = {}
    for row in report["disagreements"]:
        counts[row["category"]] = counts.get(row["category"], 0) + 1
    report["disagreement_counts"] = counts
    report["pairs_needing_adjudication"] = len({r["pair_id"] for r in report["disagreements"]})
    return report


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def _merge_degree(va, vb):
    """Returns (value, adjudication_needed, reason, merge_rule)."""
    ua, ub = (va == "unassessable"), (vb == "unassessable")
    if ua and ub:
        return "unassessable", False, None, "both_unassessable"
    if ua != ub:
        return None, True, "assessability_mismatch", None
    if va == vb:
        return va, False, None, "exact"
    if abs(va - vb) >= 2:
        return None, True, "degree_delta_ge2", None
    # adjacent disagreement: take the lower degree (the more conservative claim
    # on both dimensions) and widen the range. Recorded, not hidden.
    return min(va, vb), False, None, "min_of_adjacent"


def merge_labels(packets_by_id, pairs_a, pairs_b, meta):
    rows = []
    for pid in sorted(set(pairs_a) & set(pairs_b)):
        a, b, packet = pairs_a[pid], pairs_b[pid], packets_by_id[pid]
        row = {
            "pair_id": pid,
            "pair": packet["pair"],
            "names": packet["names"],
            "split": packet["split"],
            "stratum": packet.get("stratum"),
            "design_weight": packet.get("design_weight"),
            "sampling_basis": PAIR_SAMPLING_BASIS,
            "reviewer_blinding": dict(REVIEWER_BLINDING),
            "label_status": MERGED_LABEL_STATUS,
            "graded_via": "api",
            "api_calls": 2,
            "evidence": packet_evidence(packet),
            "directions": {},
            "adjudication_needed": False,
            "adjudication_reasons": [],
        }
        row.update(meta)
        for d in DIRECTIONS:
            da, db = a["directions"][d], b["directions"][d]
            ritual_agreed = da["ritual_courtesy_only"] == db["ritual_courtesy_only"]
            ritual = da["ritual_courtesy_only"] and db["ritual_courtesy_only"]
            block = {"ritual_courtesy_only": ritual,
                     "ritual_courtesy_mismatch": not ritual_agreed,
                     "closeness_trust_evidence_pass_a": da["closeness_trust_evidence"],
                     "closeness_trust_evidence_pass_b": db["closeness_trust_evidence"],
                     "episode_dates_used": sorted(set(da["episode_dates_used"])
                                                  | set(db["episode_dates_used"])),
                     "period_covered_pass_a": da["period_covered"],
                     "period_covered_pass_b": db["period_covered"]}
            for dim in DIMENSIONS:
                va, vb = da["%s_degree" % dim], db["%s_degree" % dim]
                value, needed, reason, rule = _merge_degree(va, vb)
                entry = {"pass_a": va, "pass_b": vb, "value": value, "merge_rule": rule,
                         "adjudication_needed": needed, "adjudication_reason": reason,
                         "cited_mention_ids_pass_a": da["%s_cited_mention_ids" % dim],
                         "cited_mention_ids_pass_b": db["%s_cited_mention_ids" % dim]}
                ranges = [r for r in (da["%s_range" % dim], db["%s_range" % dim]) if r]
                entry["range"] = ([min(r[0] for r in ranges), max(r[1] for r in ranges)]
                                  if ranges else None)
                if dim == "affinity":
                    entry["ritual_cap_applied"] = False
                    if not ritual_agreed:
                        entry["adjudication_needed"] = True
                        entry["adjudication_reason"] = (entry["adjudication_reason"]
                                                        or "ritual_courtesy_mismatch")
                    elif ritual and isinstance(entry["value"], int) and entry["value"] > 1:
                        entry["pre_cap_value"] = entry["value"]
                        entry["value"] = 1
                        entry["ritual_cap_applied"] = True
                        if entry["range"]:
                            entry["range"] = [min(entry["range"][0], 1), 1]
                    elif ritual and entry["range"] and entry["range"][1] > 1:
                        entry["range"] = [entry["range"][0], 1]
                        entry["ritual_cap_applied"] = True
                if entry["adjudication_needed"]:
                    row["adjudication_needed"] = True
                    row["adjudication_reasons"].append(
                        "%s.%s:%s" % (d, dim, entry["adjudication_reason"]))
                block[dim] = entry
            row["directions"][d] = block

        for field, category in (("neutral_assessment", "neutral_mismatch"),
                                ("mixed_ambivalent", "mixed_mismatch"),
                                ("observation_coverage", "coverage_mismatch")):
            va, vb = a[field], b[field]
            entry = {"pass_a": va, "pass_b": vb,
                     "value": va if va == vb else None,
                     "adjudication_needed": va != vb}
            if va != vb and field != "observation_coverage":
                row["adjudication_needed"] = True
                row["adjudication_reasons"].append("%s:%s" % (field, category))
            row[field] = entry
        order = {"low": 0, "medium": 1, "high": 2}
        row["confidence"] = {"pass_a": a["confidence"], "pass_b": b["confidence"],
                             "value": min([a["confidence"], b["confidence"]], key=lambda c: order[c])}
        row["rationale_pass_a"] = a["rationale"]
        row["rationale_pass_b"] = b["rationale"]
        row["observation_coverage_basis_pass_a"] = a["observation_coverage_basis"]
        row["observation_coverage_basis_pass_b"] = b["observation_coverage_basis"]
        rows.append(row)
    return rows


def adjudication_queue_markdown(agreement, merged_rows, packets_by_id, pairs_a, pairs_b, meta):
    by_id = {r["pair_id"]: r for r in merged_rows}
    lines = [
        "# Adjudication queue -- development probability sample",
        "",
        "STATUS: EXPLORATORY. Two blind model passes disagreed on the items below.",
        "Each item needs Paul's ruling; nothing here is a label until he rules.",
        "",
        "- Model: `%s`, effort `%s`, two passes differing only in mention order and run tag."
        % (meta.get("model"), meta.get("effort")),
        "- Rubric sha256: `%s`" % meta.get("rubric_sha256"),
        "- Packets sha256: `%s`" % meta.get("packet_sha256"),
        "- Pairs graded by both passes: %d. Pairs with at least one disagreement: %d (%.1f%%)."
        % (agreement["n_pairs_both_passes"], agreement["pairs_needing_adjudication"],
           100.0 * agreement["pairs_needing_adjudication"] / agreement["n_pairs_both_passes"]
           if agreement["n_pairs_both_passes"] else 0.0),
    ]
    if meta.get("no_evidence_pairs") is not None:
        lines.append(
            "- %d of the %s pairs in the sample carried no evidence at all: no excerpt, no "
            "recorded mention turn in either direction, and no hearing at which both appeared. "
            "Those received a deterministic `no_evidence` row (both dimensions unassessable, "
            "coverage `none`, neutral `unknown`). No model saw them, so they are neither in the "
            "percentage above nor in this queue."
            % (meta["no_evidence_pairs"], meta.get("pairs_total", "?")))
    lines += [
        "",
        "Disagreement categories: " + (", ".join("%s=%d" % (k, v) for k, v in
                                                 sorted(agreement["disagreement_counts"].items()))
                                       or "none"),
        "",
    ]
    grouped = {}
    for row in agreement["disagreements"]:
        grouped.setdefault(row["pair_id"], []).append(row)
    for pid in sorted(grouped):
        packet = packets_by_id[pid]
        lines.append("---")
        lines.append("")
        lines.append("## %s -- %s and %s" % (pid, packet["names"][0], packet["names"][1]))
        lines.append("")
        for item in grouped[pid]:
            lines.append("- **%s / %s / %s**: pass A `%s`, pass B `%s`"
                         % (item["direction"], item["dimension"], item["category"],
                            item["pass_a"], item["pass_b"]))
        lines.append("")
        lines.append("**Pass A rationale.** %s" % pairs_a[pid]["rationale"])
        lines.append("")
        lines.append("**Pass B rationale.** %s" % pairs_b[pid]["rationale"])
        lines.append("")
        directions = {i["direction"] for i in grouped[pid]} & set(DIRECTIONS)
        for d in sorted(directions) or sorted(DIRECTIONS):
            excerpts = _top_cited(packet, pairs_a[pid], pairs_b[pid], d, 3)
            if excerpts:
                lines.append("**Most-cited excerpts, %s**" % d)
                lines.append("")
                for mid, count, text in excerpts:
                    lines.append("- `%s` (cited %dx): %s" % (mid, count, text))
                lines.append("")
    if not grouped:
        lines.append("No disagreements. Nothing to adjudicate.")
        lines.append("")
    return "\n".join(lines)


def _top_cited(packet, a, b, direction, k):
    counts = {}
    for grade in (a, b):
        for dim in DIMENSIONS:
            for mid in grade["directions"][direction]["%s_cited_mention_ids" % dim]:
                counts[mid] = counts.get(mid, 0) + 1
    texts = {m["mention_id"]: str(m.get("context_650") or "")
             for m in packet["directions"][direction]["mentions"]}
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
    return [(mid, n, (texts.get(mid, "(mention not in packet)")[:400].replace("\n", " ")))
            for mid, n in ranked]


# ---------------------------------------------------------------------------
# calibration merge, gate, and cue scoring
# ---------------------------------------------------------------------------

GATE_AGREEMENT_KEYS = ("substantive_warmth", "personal_hostility", "speaker_verified",
                       "target_verified")


def calibration_agreement(rows_a, rows_b):
    ids = [mid for mid in rows_a if mid in rows_b]
    report = {"n_mentions_both_passes": len(ids), "keys": {}}
    for key in REVIEW_KEYS + ["speech_purpose"]:
        va = [rows_a[m][key] for m in ids]
        vb = [rows_b[m][key] for m in ids]
        agree = sum(1 for x, y in zip(va, vb) if x == y)
        report["keys"][key] = {"n": len(ids), "agree": agree,
                               "rate": (agree / float(len(ids))) if ids else None,
                               "cohen_kappa": cohen_kappa(va, vb)}
    gate = sum(1 for m in ids if all(rows_a[m][k] == rows_b[m][k] for k in GATE_AGREEMENT_KEYS))
    report["gate_agreement"] = _rate(gate, len(ids))
    report["gate_keys"] = list(GATE_AGREEMENT_KEYS)
    return report


def calibration_gate(sample_by_id, rows_a, rows_b, meta):
    """Emit rows in the chamber_expression.matched_expression gate schema."""
    out = []
    for mid in sorted(set(rows_a) & set(rows_b)):
        a, b, src = rows_a[mid], rows_b[mid], sample_by_id[mid]
        agreed = all(a[k] == b[k] for k in GATE_AGREEMENT_KEYS)
        content_agreed = a["content_status"] == b["content_status"] == "resolved"
        quoted_agreed = a["quoted_only"] == b["quoted_only"]
        purpose_agreed = a["speech_purpose"] == b["speech_purpose"]
        reviewed = bool(agreed and content_agreed and quoted_agreed and purpose_agreed)
        row = {
            "mention_id": mid,
            "actor": src["actor"], "target": src["target"], "date": src["date"],
            "venue": src["source"],
            "source_family": src.get("source_family") or src.get("package") or src["source"],
            "episode_id": src.get("episode_id") or src.get("package") or
                          ("%s:%s" % (src["source"], src["date"])),
            "source_rowid": src.get("source_rowid"),
            "chamber_supplied": src.get("chamber"),
            "review_status": "context_reviewed" if reviewed else "ambiguous",
            "sampling_basis": CALIBRATION_SAMPLING_BASIS,
            "speaker_verified": bool(a["speaker_verified"]) if agreed else None,
            "target_verified": bool(a["target_verified"]) if agreed else None,
            "quoted_only": bool(a["quoted_only"]) if quoted_agreed else None,
            "content_status": a["content_status"] if a["content_status"] == b["content_status"] else "unresolved",
            "speech_purpose": a["speech_purpose"] if purpose_agreed else None,
            "substantive_warmth": bool(a["substantive_warmth"]) if agreed else None,
            "personal_hostility": bool(a["personal_hostility"]) if agreed else None,
            "reviewer_blinding": dict(REVIEWER_BLINDING),
            "pass_a": a, "pass_b": b,
            "adjudication_needed": not reviewed,
        }
        row.update(meta)
        out.append(row)
    return out


def cue_precision_recall(gate_rows, cues):
    """Per stratum (chamber x source) precision/recall/F1 of the cue flags.

    Denominator is the context_reviewed rows only: an ambiguous row has no
    agreed warmth/hostility value to score a cue against.
    """
    strata, excluded, missing_cue = {}, 0, 0
    for row in gate_rows:
        if row["review_status"] != "context_reviewed":
            excluded += 1
            continue
        cue = cues.get(row["mention_id"])
        if cue is None:
            missing_cue += 1
            continue
        key = "%s|%s" % (row.get("chamber_supplied") or "unknown", row["venue"])
        cell = strata.setdefault(key, {"n": 0,
                                       "cue_warm_vs_substantive_warmth": _counts(),
                                       "cue_hostile_vs_personal_hostility": _counts()})
        cell["n"] += 1
        _tally(cell["cue_warm_vs_substantive_warmth"], cue["cue_warm"], row["substantive_warmth"])
        _tally(cell["cue_hostile_vs_personal_hostility"], cue["cue_hostile"], row["personal_hostility"])
    overall = {"n": 0, "cue_warm_vs_substantive_warmth": _counts(),
               "cue_hostile_vs_personal_hostility": _counts()}
    for cell in strata.values():
        overall["n"] += cell["n"]
        for channel in ("cue_warm_vs_substantive_warmth", "cue_hostile_vs_personal_hostility"):
            for k in ("tp", "fp", "fn", "tn"):
                overall[channel][k] += cell[channel][k]
    for cell in list(strata.values()) + [overall]:
        for channel in ("cue_warm_vs_substantive_warmth", "cue_hostile_vs_personal_hostility"):
            cell[channel].update(_prf(cell[channel]))
    return {"strata": strata, "overall": overall,
            "excluded_ambiguous_rows": excluded,
            "reviewed_rows_without_a_cue_record": missing_cue,
            "denominator": "context_reviewed rows only (both passes agreed on warmth, hostility, "
                           "and speaker/target verification)"}


def _counts():
    return {"tp": 0, "fp": 0, "fn": 0, "tn": 0}


def _tally(cell, predicted, actual):
    if predicted and actual:
        cell["tp"] += 1
    elif predicted and not actual:
        cell["fp"] += 1
    elif not predicted and actual:
        cell["fn"] += 1
    else:
        cell["tn"] += 1


def _prf(cell):
    tp, fp, fn = cell["tp"], cell["fp"], cell["fn"]
    precision = tp / float(tp + fp) if (tp + fp) else None
    recall = tp / float(tp + fn) if (tp + fn) else None
    if precision and recall and (precision + recall):
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None
    return {"precision": precision, "recall": recall, "f1": f1,
            "predicted_positive": tp + fp, "actual_positive": tp + fn}


# ---------------------------------------------------------------------------
# cost
# ---------------------------------------------------------------------------

def estimate_cost(usage, model=MODEL):
    price = PRICE_PER_MTOK.get(model)
    if price is None:
        raise SystemExit("no price entry for model %r; add one before spending against it" % model)
    dollars = (usage.get("input_tokens", 0) * price["input"]
               + usage.get("cache_creation_input_tokens", 0) * price["input"] * CACHE_WRITE_MULTIPLIER
               + usage.get("cache_read_input_tokens", 0) * price["input"] * CACHE_READ_DISCOUNT
               + usage.get("output_tokens", 0) * price["output"]) / 1e6
    return round(dollars, 6)


def sum_usage(records):
    total = {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
             "cache_read_input_tokens": 0}
    for rec in records:
        for k in total:
            total[k] += (rec.get("usage") or {}).get(k, 0)
    return total


# ---------------------------------------------------------------------------
# runners
# ---------------------------------------------------------------------------

def _run_batch(jobs, worker, concurrency):
    """First job alone (writes the prompt cache), the rest concurrently."""
    results = []
    if not jobs:
        return results
    results.append(worker(jobs[0]))
    rest = jobs[1:]
    if not rest:
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(concurrency, 4))) as pool:
        for out in pool.map(worker, rest):
            results.append(out)
    return results


def _zero_usage():
    return {"input_tokens": 0, "output_tokens": 0, "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0}


def _safe_filename_stem(item_id):
    """Filesystem-safe stem for a prompt file name. Never used to build a
    response_path -- the file transport keys responses by the RAW item_id,
    unsanitised, so the exporter and the reader agree; this is purely
    cosmetic for the human/grader-facing .txt prompt files."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", str(item_id))


def _write_prompts(directory, prompts):
    directory.mkdir(parents=True, exist_ok=True)
    for key, rendered in sorted(prompts.items(), key=lambda kv: (str(kv[0][0]), kv[0][1])):
        safe = _safe_filename_stem(key[0])
        (directory / ("%s__pass%s.txt" % (safe, key[1]))).write_text(
            rendered, encoding="utf-8", newline="\n")
    return directory


PROMPT_KIT_SYSTEM_HEADER = "SYSTEM\n" + "=" * 72 + "\n"
PROMPT_KIT_USER_HEADER = "USER\n" + "=" * 72 + "\n"


def full_prompt_text(system_text, rendered_user_text):
    """The complete text a grader must read to reproduce one API call: the
    system rubric first, then the user payload, exactly as GradingClient._body
    sends them (system message, then the one user message). Shared by the
    --dry-run single worked example and by --export-prompts, which writes one
    such file per item x pass. An independent forbidden-key sweep over an
    exported kit splits back on PROMPT_KIT_USER_HEADER to check only the user
    portion -- the rubric is static prose that legitimately uses ordinary
    words like "state"; assert_blind itself never scans the system text,
    only the rendered user payload, and an outside sweep has to match that
    scope or it will flag the rubric's own prose as a leak."""
    return (PROMPT_KIT_SYSTEM_HEADER + system_text + "\n\n" + PROMPT_KIT_USER_HEADER
            + rendered_user_text)


def run_pairs(packets, client, system_text, out_dir, concurrency=4, dry_run=False, log=print):
    schema = pair_grade_schema()
    gradable, empty = partition_by_evidence(packets)
    prompts, not_sent = {}, {}
    for packet in gradable:
        for pass_tag in ("A", "B"):
            _, rendered = pair_prompt(packet, pass_tag)
            prompts[(packet["pair_id"], pass_tag)] = rendered
    # An empty packet is never sent, but its prompt is still built -- and so
    # still blinding-checked by pair_prompt -- so that a dry run proves the
    # whitelist over every packet in the sample, not only the graded minority.
    for packet in empty:
        for pass_tag in ("A", "B"):
            _, rendered = pair_prompt(packet, pass_tag)
            not_sent[(packet["pair_id"], pass_tag)] = rendered
    log("pairs: %d of %d carry evidence -> %d API calls; %d empty -> deterministic no_evidence "
        "rows, %d calls not made"
        % (len(gradable), len(packets), 2 * len(gradable), len(empty), 2 * len(empty)))
    partition = {"gradable_pair_ids": [p["pair_id"] for p in gradable],
                 "no_evidence_pair_ids": [p["pair_id"] for p in empty],
                 "pairs_total": len(packets),
                 "pairs_with_evidence": len(gradable),
                 "pairs_no_evidence": len(empty),
                 "api_calls_planned": 2 * len(gradable),
                 "api_calls_avoided": 2 * len(empty)}

    if dry_run:
        root = Path(out_dir) / "prompts"
        sent_dir = _write_prompts(root / "pairs", prompts)
        _write_prompts(root / "pairs_no_evidence_not_sent", not_sent)
        write_json(root / "pair_grade_schema.json", schema)
        write_json(root / "pair_partition.json", partition)
        if prompts:
            first = sorted(prompts)[0]
            (root / "pair_prompt_full_example_with_system.txt").write_text(
                full_prompt_text(system_text, prompts[first]), encoding="utf-8", newline="\n")
        log("dry run: wrote %d pair prompts to %s and %d never-sent prompts alongside"
            % (len(prompts), sent_dir, len(not_sent)))
        out = {"dry_run": True, "prompts": len(prompts), "prompts_not_sent": len(not_sent),
               "schema_sha256": sha256_text(json.dumps(schema, sort_keys=True))}
        out.update(partition)
        return out

    by_id = {p["pair_id"]: p for p in packets}
    raw = {"A": [], "B": []}
    failures = []
    for pass_tag in ("A", "B"):
        jobs = [(p["pair_id"], prompts[(p["pair_id"], pass_tag)]) for p in gradable]

        def worker(job, _tag=pass_tag):
            pid, rendered = job
            started = time.time()
            record = {"pair_id": pid, "pass": _tag, "ok": False, "usage": _zero_usage(),
                      "attempts": [], "packet_sha256": sha256_text(json.dumps(by_id[pid],
                                                                             sort_keys=True)),
                      "prompt_sha256": sha256_text(rendered), "graded_utc": utc_now(),
                      "transport": getattr(client, "transport", TRANSPORT_API)}
            try:
                result = client.call(system_text, rendered, schema)
            except Exception as exc:
                # concurrent.futures.Executor.map re-raises on iteration, which
                # would discard every item already graded in this pass. An
                # unexpected exception fails its own item and nothing else.
                record["error"] = "worker_exception: %s: %s" % (type(exc).__name__, str(exc)[:300])
                record["duration_ms"] = int((time.time() - started) * 1000)
                return record
            record["usage"] = result["usage"]
            record["attempts"] = result["attempts"]
            record["duration_ms"] = int((time.time() - started) * 1000)
            if result["ok"]:
                try:
                    record["grade"] = normalise_pair_grade(result["data"])
                    record["grade_raw"] = result["data"]
                    record["ok"] = True
                except Exception as exc:
                    record["error"] = "normalise_failed: %s: %s" % (type(exc).__name__,
                                                                    str(exc)[:300])
                    record["grade_raw"] = result["data"]
            else:
                record["error"] = result.get("error")
            return record

        results = _run_batch(jobs, worker, concurrency)
        raw[pass_tag] = results
        write_ndjson(Path(out_dir) / ("pass_%s.ndjson" % pass_tag), results)
        ok = sum(1 for r in results if r["ok"])
        log("pass %s: %d/%d graded" % (pass_tag, ok, len(results)))
        failures.extend([{"pair_id": r["pair_id"], "pass": pass_tag, "error": r.get("error"),
                          "attempts": r["attempts"]} for r in results if not r["ok"]])
    return {"raw": raw, "failures": failures, "schema": schema,
            "gradable": gradable, "no_evidence": empty, "partition": partition}


def run_calibration(sample, client, system_text, out_dir, concurrency=4, dry_run=False, log=print):
    schema = calibration_schema()
    prompts = {}
    for row in sample:
        for pass_tag in ("A", "B"):
            _, rendered = calibration_prompt(row, pass_tag)
            prompts[(row["mention_id"], pass_tag)] = rendered
    if dry_run:
        root = Path(out_dir) / "prompts"
        prompt_dir = _write_prompts(root / "calibration", prompts)
        write_json(root / "calibration_schema.json", schema)
        first = sorted(prompts, key=lambda k: (str(k[0]), k[1]))[0]
        (root / "calibration_prompt_full_example_with_system.txt").write_text(
            full_prompt_text(system_text, prompts[first]), encoding="utf-8", newline="\n")
        log("dry run: wrote %d calibration prompts to %s" % (len(prompts), prompt_dir))
        return {"dry_run": True, "prompts": len(prompts)}

    raw = {"A": [], "B": []}
    failures = []
    for pass_tag in ("A", "B"):
        jobs = [(row["mention_id"], prompts[(row["mention_id"], pass_tag)]) for row in sample]

        def worker(job, _tag=pass_tag):
            mid, rendered = job
            started = time.time()
            record = {"mention_id": mid, "pass": _tag, "ok": False, "usage": _zero_usage(),
                      "attempts": [], "prompt_sha256": sha256_text(rendered),
                      "graded_utc": utc_now(),
                      "transport": getattr(client, "transport", TRANSPORT_API)}
            try:
                result = client.call(system_text, rendered, schema)
            except Exception as exc:
                record["error"] = "worker_exception: %s: %s" % (type(exc).__name__, str(exc)[:300])
                record["duration_ms"] = int((time.time() - started) * 1000)
                return record
            record["usage"] = result["usage"]
            record["attempts"] = result["attempts"]
            record["ok"] = bool(result["ok"])
            record["duration_ms"] = int((time.time() - started) * 1000)
            if result["ok"]:
                record["review"] = result["data"]
            else:
                record["error"] = result.get("error")
            return record

        results = _run_batch(jobs, worker, concurrency)
        raw[pass_tag] = results
        write_ndjson(Path(out_dir) / ("calibration_pass_%s.ndjson" % pass_tag), results)
        log("calibration pass %s: %d/%d reviewed"
            % (pass_tag, sum(1 for r in results if r["ok"]), len(results)))
        failures.extend([{"mention_id": r["mention_id"], "pass": pass_tag, "error": r.get("error")}
                         for r in results if not r["ok"]])
    return {"raw": raw, "failures": failures, "schema": schema}


# ---------------------------------------------------------------------------
# export-prompts: a self-contained offline grading kit
#
# When the Anthropic key has no credit, the two blind passes are instead
# performed by independent Claude Code subagents: each reads one exported
# prompt file -- the exact system+user text a live call would have sent --
# and writes back one JSON response, to be validated against the same schema
# a live response is validated against. This writes that kit.
# --transport subagent_files / SubagentFileClient (above) is what later reads
# the responses back in through the ordinary run_pairs / run_calibration path.
# ---------------------------------------------------------------------------

def _kit_prompt_filename(item_id, pass_tag):
    return "%s__pass%s.txt" % (_safe_filename_stem(item_id), pass_tag)


def _chunk(seq, size):
    return [seq[i:i + size] for i in range(0, len(seq), size)]


def _build_kit_batches(items):
    """Batches grouped by (phase, pass), each capped at that phase's limit,
    items ordered by item_id so the same inputs always produce the same
    batches (response_path naming, like the batches themselves, is stable)."""
    limits = {"pairs": PAIR_KIT_BATCH_MAX, "calibration": CALIBRATION_KIT_BATCH_MAX}
    by_group = {}
    for item in items:
        by_group.setdefault((item["phase"], item["pass"]), []).append(item)
    batches = []
    for phase, pass_tag in sorted(by_group):
        group_items = sorted(by_group[(phase, pass_tag)], key=lambda it: it["item_id"])
        for i, chunk in enumerate(_chunk(group_items, limits[phase]), 1):
            batches.append({
                "batch_id": "%s__%s__%04d" % (phase, pass_tag, i),
                "phase": phase,
                "pass": pass_tag,
                "item_count": len(chunk),
                "schema_path": chunk[0]["schema_path"],
                "items": [{"item_id": it["item_id"], "prompt_path": it["prompt_path"],
                          "response_path": it["response_path"]} for it in chunk],
            })
    return batches


def export_prompt_kit(out_dir, packets_path, calibration_path, rubric_text, limit=None,
                      log=print):
    """Write a self-contained offline grading kit to `out_dir`:

      index.json                every (item, pass) that needs grading, plus meta counts
      batches.json               those items grouped into grader-sized batches
      pair_grade_schema.json     standalone copy of pair_grade_schema()
      calibration_schema.json    standalone copy of calibration_schema()
      prompts/pairs/*.txt        one file per pair item x pass: full system+user text
      prompts/calibration/*.txt  one file per calibration item x pass: full system+user text
      responses/A/, responses/B/ empty, waiting for a grader to write <item_id>.json

    Makes no API call and reads no key -- the whole point is grading while
    the key has no credit. Reuses pair_prompt / calibration_prompt (hence
    assert_blind) completely unchanged, so an exported prompt's user section
    is byte-identical to what the live transport would have sent. Applies the
    same no_evidence short circuit run_pairs applies: a packet with no
    excerpt, no recorded mention turn, and no shared hearing is graded by no
    one, model or subagent, and is left out of the index entirely -- counted
    only in index.json's meta, exactly as a live run counts it in the receipt
    rather than folding it into the graded denominator.
    """
    # Resolved to absolute up front: every path this function records (prompt_path,
    # schema_path, response_path, in both index.json and batches.json) is derived
    # from out_dir, and a "self-contained" kit has to mean a grader can use those
    # paths directly -- without knowing or reconstructing the cwd this export ran
    # from -- not just when re-read from that same directory.
    out_dir = Path(out_dir).resolve()
    prompts_root = out_dir / "prompts"
    responses_root = out_dir / "responses"
    for pass_tag in ("A", "B"):
        (responses_root / pass_tag).mkdir(parents=True, exist_ok=True)

    system_text = build_system_text(rubric_text)
    pair_schema_path = out_dir / "pair_grade_schema.json"
    calib_schema_path = out_dir / "calibration_schema.json"
    write_json(pair_schema_path, pair_grade_schema())
    write_json(calib_schema_path, calibration_schema())

    items = []
    meta = {"pair_batch_max": PAIR_KIT_BATCH_MAX,
            "calibration_batch_max": CALIBRATION_KIT_BATCH_MAX,
            "pairs_total": 0, "pairs_with_evidence": 0, "pairs_no_evidence_excluded": 0,
            "no_evidence_pair_ids": [], "calibration_total": 0}

    packets_path = Path(packets_path)
    if packets_path.exists():
        packets = load_pair_packets(packets_path, limit=limit)
        gradable, empty = partition_by_evidence(packets)
        meta["pairs_total"] = len(packets)
        meta["pairs_with_evidence"] = len(gradable)
        meta["pairs_no_evidence_excluded"] = len(empty)
        meta["no_evidence_pair_ids"] = sorted(p["pair_id"] for p in empty)
        pairs_dir = prompts_root / "pairs"
        pairs_dir.mkdir(parents=True, exist_ok=True)
        for packet in sorted(gradable, key=lambda p: p["pair_id"]):
            for pass_tag in ("A", "B"):
                _, rendered = pair_prompt(packet, pass_tag)
                path = pairs_dir / _kit_prompt_filename(packet["pair_id"], pass_tag)
                path.write_text(full_prompt_text(system_text, rendered), encoding="utf-8",
                                newline="\n")
                items.append({
                    "item_id": packet["pair_id"], "phase": "pairs", "pass": pass_tag,
                    "prompt_path": str(path), "schema_path": str(pair_schema_path),
                    "response_path": str(responses_root / pass_tag /
                                         ("%s.json" % packet["pair_id"]))})
    else:
        log("export-prompts: pair packets not found at %s; no pair items exported" % packets_path)

    calibration_path = Path(calibration_path)
    if calibration_path.exists():
        rows = load_calibration(calibration_path, limit=limit)
        meta["calibration_total"] = len(rows)
        calib_dir = prompts_root / "calibration"
        calib_dir.mkdir(parents=True, exist_ok=True)
        for row in sorted(rows, key=lambda r: r["mention_id"]):
            for pass_tag in ("A", "B"):
                _, rendered = calibration_prompt(row, pass_tag)
                path = calib_dir / _kit_prompt_filename(row["mention_id"], pass_tag)
                path.write_text(full_prompt_text(system_text, rendered), encoding="utf-8",
                                newline="\n")
                items.append({
                    "item_id": row["mention_id"], "phase": "calibration", "pass": pass_tag,
                    "prompt_path": str(path), "schema_path": str(calib_schema_path),
                    "response_path": str(responses_root / pass_tag /
                                         ("%s.json" % row["mention_id"]))})
    else:
        log("export-prompts: calibration sample not found at %s; no calibration items exported"
            % calibration_path)

    items.sort(key=lambda it: (it["phase"], it["item_id"], it["pass"]))
    meta["items_total"] = len(items)
    for phase in ("pairs", "calibration"):
        meta["%s_items_total" % phase] = sum(1 for it in items if it["phase"] == phase)
        for pass_tag in ("A", "B"):
            meta["%s_pass_%s_items" % (phase, pass_tag.lower())] = sum(
                1 for it in items if it["phase"] == phase and it["pass"] == pass_tag)

    index_path = out_dir / "index.json"
    write_json(index_path, {"meta": meta, "items": items})

    batches = _build_kit_batches(items)
    batches_path = out_dir / "batches.json"
    write_json(batches_path, {"meta": {"batch_count": len(batches),
                                       "pair_batch_max": PAIR_KIT_BATCH_MAX,
                                       "calibration_batch_max": CALIBRATION_KIT_BATCH_MAX},
                              "batches": batches})

    log("export-prompts: %d items (%d pair items over %d of %d evidenced pairs, %d calibration "
        "items over %d mentions), %d no_evidence pairs excluded, %d batches -> %s"
        % (len(items), meta["pairs_items_total"], meta["pairs_with_evidence"], meta["pairs_total"],
           meta["calibration_items_total"], meta["calibration_total"],
           meta["pairs_no_evidence_excluded"], len(batches), out_dir))
    return {"index_path": str(index_path), "batches_path": str(batches_path),
           "pair_schema_path": str(pair_schema_path), "calib_schema_path": str(calib_schema_path),
           "meta": meta, "batch_count": len(batches)}


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def build_report(receipt, agreement=None, calib_agreement=None, cue_scores=None):
    n = (agreement or {}).get("n_pairs_both_passes", 0)
    lines = [
        "**Blind two-pass grading, development probability sample**",
        "",
        "STATUS: EXPLORATORY. These are two blind model passes over a frozen rubric, not human "
        "gold and not independent inter-rater reliability. Every disagreement is queued for "
        "Paul; no merged value is a final label until he rules on the queue.",
        "",
        "Run `%s`, %s. Model `%s`, effort `%s`, adaptive thinking, max_tokens %d. Call path: %s. "
        "Rubric sha256 `%s`." % (receipt["run_id"], receipt["started_utc"], receipt["model"],
                                 receipt["effort"], receipt["max_tokens"], receipt["api_path"],
                                 receipt["rubric_sha256"]),
        "",
    ]
    counts = receipt.get("counts", {})
    if agreement:
        lines += ["**Pair agreement**", ""]
        if counts.get("pairs_no_evidence_deterministic_rows") is not None:
            lines += [
                "Denominators. The sample holds %s pairs. %s carried evidence and went to the "
                "model, two passes each; %d carried none at all -- no excerpt, no recorded "
                "mention turn in either direction, no hearing at which both appeared -- and "
                "received a deterministic `no_evidence` row with no API call, %d calls not made. "
                "Every agreement figure below is over the API-graded pairs only. The "
                "deterministic rows agree with themselves by construction and would inflate "
                "assessability agreement if folded in."
                % (counts.get("pairs_total", n), counts.get("pairs_with_evidence_sent_to_api", n),
                   counts["pairs_no_evidence_deterministic_rows"],
                   counts.get("api_calls_avoided_by_no_evidence", 0)),
                ""]
        lines += ["Pairs graded by both passes: %d of %d sent to the model."
                  % (n, counts.get("pairs_with_evidence_sent_to_api",
                                   counts.get("pairs_attempted", n))),
                  ""]
        lines.append("| Dimension | Direction | Both assessed | Exact | Within 1 | QWK | Assessability |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: |")
        for dim in DIMENSIONS:
            for d in DIRECTIONS:
                cell = agreement["dimensions"][dim][d]
                lines.append("| %s | %s | %d of %d | %s | %s | %s | %s |" % (
                    dim, d, cell["both_assessed_n"], cell["n"],
                    _pct(cell["exact_agreement"]), _pct(cell["within_1_agreement"]),
                    _num(cell["quadratic_weighted_kappa"]),
                    _pct(cell["assessability_agreement"])))
        lines += ["",
                  "Neutral assessment agreed on %s. Mixed/ambivalent agreed on %s. Observation "
                  "coverage agreed on %s." % (_pct(agreement["neutral_assessment_agreement"]),
                                              _pct(agreement["mixed_ambivalent_agreement"]),
                                              _pct(agreement["observation_coverage_agreement"])),
                  "",
                  "Items queued for adjudication: %d, across %d of %d pairs (%s)."
                  % (len(agreement["disagreements"]), agreement["pairs_needing_adjudication"], n,
                     _pct({"agree": agreement["pairs_needing_adjudication"], "n": n,
                           "rate": (agreement["pairs_needing_adjudication"] / float(n)) if n else None})),
                  ""]
        if agreement["disagreement_counts"]:
            lines.append("By category: " + ", ".join(
                "%s %d" % (k, v) for k, v in sorted(agreement["disagreement_counts"].items())) + ".")
            lines.append("")
    summary = receipt.get("label_summary")
    if summary:
        lines += ["**What the label file actually contains**", "",
                  "%d rows: %s." % (summary["rows"], ", ".join(
                      "%d %s" % (v, k) for k, v in sorted(summary["by_label_status"].items()))),
                  "",
                  "| Dimension | Direction | Assessable | Unassessable | Awaiting adjudication |",
                  "| --- | --- | ---: | ---: | ---: |"]
        for dim in DIMENSIONS:
            for d in DIRECTIONS:
                cell = summary["assessability"][dim][d]
                lines.append("| %s | %s | %d | %d | %d |" % (
                    dim, d, cell["assessable"], cell["unassessable"],
                    cell["adjudication_pending"]))
        lines += ["",
                  "Neutral assessment: " + ", ".join(
                      "%s %d" % (k, v) for k, v in sorted(summary["neutral_assessment"].items())
                      if v) + ".",
                  "",
                  "Observation coverage: " + ", ".join(
                      "%s %d" % (k, v) for k, v in sorted(summary["observation_coverage"].items())
                      if v) + ".",
                  ""]
    if calib_agreement:
        m = calib_agreement["n_mentions_both_passes"]
        lines += ["**Calibration review agreement**", "",
                  "Mentions reviewed by both passes: %d." % m, "",
                  "| Key | Agreement | Cohen kappa |", "| --- | ---: | ---: |"]
        for key, cell in sorted(calib_agreement["keys"].items()):
            lines.append("| %s | %s | %s |" % (key, _pct(cell), _num(cell["cohen_kappa"])))
        lines += ["",
                  "Gate keys (%s) agreed on %s; only those rows carry review_status "
                  "context_reviewed." % (", ".join(calib_agreement["gate_keys"]),
                                         _pct(calib_agreement["gate_agreement"])),
                  ""]
    if cue_scores:
        overall = cue_scores["overall"]
        lines += ["**Cue precision and recall**", "",
                  "Denominator: %s. Rows excluded as ambiguous: %d. Reviewed rows with no cue "
                  "record: %d." % (cue_scores["denominator"], cue_scores["excluded_ambiguous_rows"],
                                   cue_scores["reviewed_rows_without_a_cue_record"]),
                  "",
                  "| Stratum | n | Channel | Precision | Recall | F1 | Predicted + | Actual + |",
                  "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |"]
        for name in sorted(cue_scores["strata"]) + ["ALL"]:
            cell = overall if name == "ALL" else cue_scores["strata"][name]
            for channel in ("cue_warm_vs_substantive_warmth", "cue_hostile_vs_personal_hostility"):
                c = cell[channel]
                lines.append("| %s | %d | %s | %s | %s | %s | %d | %d |" % (
                    name, cell["n"], channel, _num(c["precision"]), _num(c["recall"]),
                    _num(c["f1"]), c["predicted_positive"], c["actual_positive"]))
        lines.append("")
    usage = receipt["usage_total"]
    lines += ["**Cost**", "",
              "Calls: %d. Input tokens %d, cache writes %d, cache reads %d, output tokens %d. "
              "Estimated spend $%.4f at $%.2f/$%.2f per MTok."
              % (receipt["counts"].get("api_calls", 0), usage["input_tokens"],
                 usage["cache_creation_input_tokens"], usage["cache_read_input_tokens"],
                 usage["output_tokens"], receipt["estimated_cost_usd"],
                 PRICE_PER_MTOK[receipt["model"]]["input"],
                 PRICE_PER_MTOK[receipt["model"]]["output"]),
              ""]
    if receipt.get("failures"):
        lines += ["**Failures**", "",
                  "%d item-passes failed after their one content retry." % len(receipt["failures"]),
                  ""]
    lines += ["**What this does not establish**", "",
              "Two passes of one model over one rubric measure the rubric's internal consistency "
              "under a reordered packet. They do not measure human inter-rater reliability, and "
              "they do not measure whether a graded degree corresponds to a private relationship. "
              "Agreement between passes that share a model and a rubric is not independent "
              "corroboration.", ""]
    return "\n".join(lines)


def _pct(cell):
    if not cell or cell.get("rate") is None:
        return "n/a"
    return "%.1f%% (%d/%d)" % (100.0 * cell["rate"], cell["agree"], cell["n"])


def _num(value):
    return "n/a" if value is None else "%.3f" % value


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def run_token_census(client, system_text, pair_items, calib_items, out_dir, log=print):
    """Measured input sizes from the free counter. No grading, no spend."""
    census = {"measured_utc": utc_now(), "model": client.model, "effort": client.effort,
              "system_only": None, "pairs": [], "calibration": []}
    census["system_only"] = dict(zip(("input_tokens", "shape"),
                                     client.count_input_tokens(system_text, "x",
                                                               pair_grade_schema())))
    for packet in pair_items:
        _, rendered = pair_prompt(packet, "A")
        tokens, shape = client.count_input_tokens(system_text, rendered, pair_grade_schema())
        mentions = sum(len(packet["directions"][d]["mentions"]) for d in DIRECTIONS)
        census["pairs"].append({"pair_id": packet["pair_id"], "mentions": mentions,
                                "input_tokens": tokens, "shape": shape})
        log("  pair %-24s mentions=%2d input_tokens=%d" % (packet["pair_id"], mentions, tokens))
    for row in calib_items:
        _, rendered = calibration_prompt(row, "A")
        tokens, shape = client.count_input_tokens(system_text, rendered, calibration_schema())
        census["calibration"].append({"mention_id": row["mention_id"], "input_tokens": tokens,
                                      "shape": shape})
    if census["pairs"]:
        fixed = min(p["input_tokens"] for p in census["pairs"])
        spread = [(p["mentions"], p["input_tokens"]) for p in census["pairs"]]
        lo, hi = min(spread), max(spread)
        per_mention = ((hi[1] - lo[1]) / float(hi[0] - lo[0])) if hi[0] != lo[0] else None
        census["pair_model"] = {"smallest_prompt_input_tokens": fixed,
                                "tokens_per_additional_mention": per_mention,
                                "note": "two-point estimate from the smallest and largest packet "
                                        "in this census; widen the census before trusting it"}
    write_json(Path(out_dir) / "token_census.json", census)
    return census


def build_system_text(rubric_text):
    return (rubric_text + "\n\n---\n\n"
            "You are one blind reviewer. Apply the rubric above to the packet in the user "
            "message and return only the JSON object the response schema requires. Decide every "
            "field from the packet, never from memory. If the packet does not support a degree, "
            "say 'unassessable'; absence of evidence is never a 0.\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--phase", choices=["pairs", "calibration", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--smoke", type=int, default=None,
                        help="live run over N items, into a smoke/ subdirectory")
    parser.add_argument("--dry-run", action="store_true", help="no API calls; write prompts to disk")
    parser.add_argument("--count-tokens", action="store_true",
                        help="measure billable input tokens per prompt on the FREE token-counting "
                             "endpoint and write token_census.json; grades nothing, spends nothing")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--packets", default=str(DEFAULT_PACKETS))
    parser.add_argument("--calibration", default=str(DEFAULT_CALIBRATION))
    parser.add_argument("--hidden-cues", default=str(DEFAULT_HIDDEN_CUES))
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT))
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--effort", default=EFFORT)
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS)
    parser.add_argument("--key-index", type=int, default=0)
    parser.add_argument("--transport", choices=[TRANSPORT_API, TRANSPORT_SUBAGENT_FILES],
                        default=TRANSPORT_API,
                        help="'%s' calls the Anthropic API directly (default). '%s' reads "
                             "pre-computed grading responses from --responses-dir instead of "
                             "calling the API, for when independent Claude Code subagents "
                             "performed the two passes offline over an --export-prompts kit."
                             % (TRANSPORT_API, TRANSPORT_SUBAGENT_FILES))
    parser.add_argument("--responses-dir", default=None,
                        help="required with --transport %s: directory holding "
                             "<pass>/<item_id>.json response files (and where "
                             "<pass>/<item_id>.error.txt is written on a validation failure)"
                             % TRANSPORT_SUBAGENT_FILES)
    parser.add_argument("--export-prompts", default=None, metavar="DIR",
                        help="write a self-contained grading kit to DIR (index.json, "
                             "batches.json, both response schemas, and one full system+user "
                             "prompt file per item x pass) and exit; makes no API call and reads "
                             "no key")
    args = parser.parse_args(argv)
    if args.model not in PRICE_PER_MTOK:
        raise SystemExit("no price entry for model %r; add one to PRICE_PER_MTOK before spending "
                         "money against it" % args.model)
    if args.count_tokens and args.transport != TRANSPORT_API:
        raise SystemExit("--count-tokens measures billable API input size; it requires "
                         "--transport %s (the default), not %r" % (TRANSPORT_API, args.transport))

    rubric_text = RUBRIC_PATH.read_text(encoding="utf-8")
    rubric_sha = sha256_text(rubric_text)

    if args.export_prompts:
        kit_dir = Path(args.export_prompts)
        result = export_prompt_kit(kit_dir, args.packets, args.calibration, rubric_text,
                                   limit=args.limit)
        _glassbox_emit("research", "ok",
                       "blind grading harness: export-prompts wrote %d items in %d batches to %s"
                       % (result["meta"]["items_total"], result["batch_count"], kit_dir),
                       stage="member_personal_relationships/blind_grading",
                       detail="rubric %s" % rubric_sha,
                       metadata={"out_dir": str(kit_dir),
                                 "items_total": result["meta"]["items_total"]})
        print("wrote %s" % kit_dir)
        print(json.dumps({"index_path": result["index_path"], "batches_path": result["batches_path"],
                          "items_total": result["meta"]["items_total"],
                          "batch_count": result["batch_count"]}, indent=1))
        return 0

    started = time.time()
    run_id = "mpr-blindgrade-%s" % datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_dir = Path(args.out_dir)
    if args.smoke:
        out_dir = out_dir / "smoke"
    out_dir.mkdir(parents=True, exist_ok=True)
    limit = args.smoke or args.limit

    system_text = build_system_text(rubric_text)

    _glassbox_emit("research", "start",
                   "blind grading harness: phase=%s limit=%s dry_run=%s"
                   % (args.phase, limit, args.dry_run),
                   run_id=run_id, stage="member_personal_relationships/blind_grading",
                   detail="rubric %s" % rubric_sha,
                   metadata={"phase": args.phase, "limit": limit, "dry_run": args.dry_run,
                             "model": args.model, "effort": args.effort})

    client = None
    api_path = "dry-run (no API)"
    if not args.dry_run:
        if args.transport == TRANSPORT_SUBAGENT_FILES:
            if not args.responses_dir:
                raise SystemExit("--transport %s requires --responses-dir"
                                 % TRANSPORT_SUBAGENT_FILES)
            client = SubagentFileClient(args.responses_dir)
            api_path = "%s (responses read from %s)" % (TRANSPORT_LABEL_SUBAGENT_FILES,
                                                         args.responses_dir)
        else:
            client = GradingClient(load_api_key(args.key_index), model=args.model,
                                   effort=args.effort, max_tokens=args.max_tokens)
            api_path = client.path

    if args.count_tokens:
        pair_items, calib_items = [], []
        if args.phase in ("pairs", "all") and Path(args.packets).exists():
            # Measure what would actually be SENT: the empty packets are
            # short-circuited, so counting their tokens would understate the
            # per-call size and overstate the call count at the same time.
            pair_items = load_pair_packets(args.packets, limit=(None if args.smoke else limit))
            pair_items, _empty = partition_by_evidence(pair_items)
            if args.smoke:
                pair_items = most_evidenced(pair_items, args.smoke)
        if args.phase in ("calibration", "all") and Path(args.calibration).exists():
            calib_items = load_calibration(args.calibration, limit=limit)
        census = run_token_census(client, system_text, pair_items, calib_items, out_dir)
        print(json.dumps({"pairs_measured": len(census["pairs"]),
                          "calibration_measured": len(census["calibration"]),
                          "system_only_input_tokens": census["system_only"]["input_tokens"],
                          "pair_model": census.get("pair_model")}, indent=1))
        return 0

    receipt = {"run_id": run_id, "started_utc": utc_now(), "model": args.model,
               "effort": args.effort, "max_tokens": args.max_tokens,
               "thinking": "adaptive", "api_path": api_path,
               "transport": getattr(client, "transport", TRANSPORT_API),
               "model_choice_note": "claude-sonnet-5 chosen for grading fidelity on blind gold; "
                                    "Paul's standing default elsewhere is Haiku. One line "
                                    "(blind_grading.MODEL) switches it; PRICE_PER_MTOK must "
                                    "change with it.",
               "rubric_path": str(RUBRIC_PATH), "rubric_sha256": rubric_sha,
               "out_dir": str(out_dir), "phase": args.phase, "limit": limit,
               "dry_run": bool(args.dry_run), "smoke": bool(args.smoke),
               "concurrency": args.concurrency, "counts": {}, "failures": [],
               "usage_total": {"input_tokens": 0, "output_tokens": 0,
                               "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0},
               "inputs": {}}
    agreement = calib_agreement = cue_scores = None
    all_usage_records = []

    if args.phase in ("pairs", "all"):
        packets_path = Path(args.packets)
        if not packets_path.exists():
            raise SystemExit("pair packets not found: %s (the packet producer has not run; pass "
                             "--packets to point at a file)" % packets_path)
        packets = load_pair_packets(packets_path, limit=(None if args.smoke else limit))
        if args.smoke:
            # A smoke test exists to exercise the live call path on real
            # material. Most packets here are empty, so taking the first N off
            # the file would short-circuit all N and make zero calls.
            packets = most_evidenced(packets, args.smoke)
            print("smoke: grading the %d most-evidenced packets: %s"
                  % (len(packets), ", ".join(p["pair_id"] for p in packets)))
        receipt["inputs"]["pair_packets"] = {"path": str(packets_path),
                                             "sha256": sha256_file(packets_path),
                                             "packets_loaded": len(packets)}
        receipt["counts"]["pairs_attempted"] = len(packets)
        result = run_pairs(packets, client, system_text, out_dir, args.concurrency,
                           dry_run=args.dry_run)
        if args.dry_run:
            receipt["counts"].update({k: result[k] for k in
                                      ("pairs_with_evidence", "pairs_no_evidence",
                                       "api_calls_planned", "api_calls_avoided")})
        else:
            by_id = {p["pair_id"]: p for p in packets}
            partition = result["partition"]
            meta = {"model": args.model, "effort": args.effort, "rubric_sha256": rubric_sha,
                    "packet_sha256": receipt["inputs"]["pair_packets"]["sha256"],
                    "run_id": run_id}
            pa = {r["pair_id"]: r["grade"] for r in result["raw"]["A"] if r["ok"]}
            pb = {r["pair_id"]: r["grade"] for r in result["raw"]["B"] if r["ok"]}
            agreement = pair_agreement(pa, pb, by_id)
            agreement["failures"] = result["failures"]
            # Agreement is over the API-graded pairs ONLY. Folding the
            # deterministic no_evidence rows in would push assessability
            # agreement towards 100% without a single model judgement behind it.
            agreement["denominators"] = dict(
                partition,
                pairs_graded_by_both_passes=agreement["n_pairs_both_passes"],
                note="agreement covers API-graded pairs only; the no_evidence rows are "
                     "deterministic and carry no inter-pass information")
            write_json(out_dir / "agreement.json", agreement)
            merged = merge_labels(by_id, pa, pb, meta)
            queue_meta = dict(meta, no_evidence_pairs=partition["pairs_no_evidence"],
                              pairs_total=partition["pairs_total"])
            no_evidence_rows = [no_evidence_label_row(p, meta) for p in result["no_evidence"]]
            labels = sorted(merged + no_evidence_rows, key=lambda r: r["pair_id"])
            write_ndjson(out_dir / "labels_v1.ndjson", labels)
            summary = label_summary(labels)
            write_json(out_dir / "label_summary.json", summary)
            (out_dir / "adjudication_queue.md").write_text(
                adjudication_queue_markdown(agreement, merged, by_id, pa, pb, queue_meta),
                encoding="utf-8", newline="\n")
            all_usage_records += result["raw"]["A"] + result["raw"]["B"]
            receipt["failures"] += result["failures"]
            receipt["counts"].update({
                "pairs_total": partition["pairs_total"],
                "pairs_with_evidence_sent_to_api": partition["pairs_with_evidence"],
                "pairs_no_evidence_deterministic_rows": partition["pairs_no_evidence"],
                "api_calls_avoided_by_no_evidence": partition["api_calls_avoided"],
                "pairs_graded_both_passes": agreement["n_pairs_both_passes"],
                "pairs_needing_adjudication": agreement["pairs_needing_adjudication"],
                "label_rows_written": len(labels)})
            receipt["no_evidence_pair_ids"] = partition["no_evidence_pair_ids"]
            receipt["label_summary"] = summary

    if args.phase in ("calibration", "all"):
        calib_path = Path(args.calibration)
        if not calib_path.exists():
            if args.phase == "calibration":
                raise SystemExit("calibration sample not found: %s" % calib_path)
            print("calibration sample absent (%s); skipping the calibration phase" % calib_path)
        else:
            sample = load_calibration(calib_path, limit=limit)
            receipt["inputs"]["calibration_sample"] = {"path": str(calib_path),
                                                       "sha256": sha256_file(calib_path),
                                                       "mentions_loaded": len(sample)}
            receipt["counts"]["calibration_attempted"] = len(sample)
            result = run_calibration(sample, client, system_text, out_dir, args.concurrency,
                                     dry_run=args.dry_run)
            if not args.dry_run:
                by_id = {r["mention_id"]: r for r in sample}
                meta = {"model": args.model, "effort": args.effort, "rubric_sha256": rubric_sha,
                        "run_id": run_id}
                ra = {r["mention_id"]: r["review"] for r in result["raw"]["A"] if r["ok"]}
                rb = {r["mention_id"]: r["review"] for r in result["raw"]["B"] if r["ok"]}
                calib_agreement = calibration_agreement(ra, rb)
                calib_agreement["failures"] = result["failures"]
                write_json(out_dir / "calibration_agreement.json", calib_agreement)
                gate_rows = calibration_gate(by_id, ra, rb, meta)
                write_ndjson(out_dir / "calibration_reviewed.ndjson", gate_rows)
                cues_path = Path(args.hidden_cues)
                if cues_path.exists():
                    cues = load_hidden_cues(cues_path)
                    receipt["inputs"]["hidden_cues"] = {"path": str(cues_path),
                                                        "sha256": sha256_file(cues_path),
                                                        "rows": len(cues)}
                    cue_scores = cue_precision_recall(gate_rows, cues)
                    write_json(out_dir / "cue_precision_recall.json", cue_scores)
                else:
                    print("hidden cues file absent (%s); cue precision/recall not computed"
                          % cues_path)
                all_usage_records += result["raw"]["A"] + result["raw"]["B"]
                receipt["failures"] += result["failures"]
                receipt["counts"]["calibration_reviewed_context_reviewed"] = sum(
                    1 for r in gate_rows if r["review_status"] == "context_reviewed")

    receipt["counts"]["api_calls"] = len(all_usage_records)
    receipt["usage_total"] = sum_usage(all_usage_records)
    receipt["estimated_cost_usd"] = estimate_cost(receipt["usage_total"], args.model)
    receipt["cost_per_call_usd"] = (round(receipt["estimated_cost_usd"] / len(all_usage_records), 6)
                                    if all_usage_records else None)
    receipt["finished_utc"] = utc_now()
    receipt["duration_ms"] = int((time.time() - started) * 1000)
    receipt["glassbox_run_id"] = run_id
    write_json(out_dir / "run_receipt.json", receipt)
    (out_dir / "REPORT.md").write_text(
        build_report(receipt, agreement, calib_agreement, cue_scores),
        encoding="utf-8", newline="\n")

    _glassbox_emit("research", "ok" if not receipt["failures"] else "warn",
                   "blind grading harness finished: %d calls, $%.4f, %d failures"
                   % (receipt["counts"]["api_calls"], receipt["estimated_cost_usd"],
                      len(receipt["failures"])),
                   run_id=run_id, stage="member_personal_relationships/blind_grading",
                   duration_ms=receipt["duration_ms"],
                   detail=json.dumps(receipt["counts"], sort_keys=True),
                   metadata={"out_dir": str(out_dir), "cost_usd": receipt["estimated_cost_usd"]})
    print("wrote %s" % out_dir)
    print(json.dumps({"calls": receipt["counts"]["api_calls"],
                      "cost_usd": receipt["estimated_cost_usd"],
                      "cost_per_call_usd": receipt["cost_per_call_usd"],
                      "failures": len(receipt["failures"])}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
