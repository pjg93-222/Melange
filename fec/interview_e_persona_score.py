# -*- coding: utf-8 -*-
import os as _o, sys as _s
_s.path.insert(0, _o.path.dirname(_o.path.abspath(__file__)))
from paths import ROOT as MB_ROOT

"""Collect blinded equal-length observed interview-E ratings under the locked prereg.

Default is read-only coverage status. --go is the explicit Haiku cost/collection gate. Output is a
resumable candidate consumed by no production script and cannot itself authorize a trait look.
"""

import argparse
import collections
import hashlib
import json
import re
import sqlite3
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from moneyball_core import dump_atomic

_s.stdout.reconfigure(encoding="utf-8", errors="replace")
B = MB_ROOT
OUT = _o.path.join(B, "interview_e_persona_halves.json.candidate")
MODEL = "claude-haiku-4-5"
SALTS = {
    "primary": "e-persona-primary-v1",
    "rederive": "e-persona-rederive-v1",
}
MIN_PACKAGES = 3
SAMPLE_WORDS = 1000

FIELDS = (
    "social_energy",
    "enthusiastic_engagement",
    "expressive_affect",
    "spontaneous_self_disclosure",
    "conversational_responsiveness",
    "reserved_flatness",
)

RUBRIC = r"""You are rating OBSERVED EXPRESSIVE-INTERPERSONAL EXTRAVERSION from de-identified
interview responses by one public official. Every sample is exactly the same length and contains
only the official's responses from multiple appearances. Score halves A and B separately.

For each half return integer 0-100 scores for:
- social_energy: lively, socially energized presence in the response content;
- enthusiastic_engagement: active enthusiasm and engaged interpersonal tone;
- expressive_affect: visible emotional animation and vivid personal expression;
- spontaneous_self_disclosure: natural personal revelation, anecdote, humor, or unscripted candor;
- conversational_responsiveness: directly engages the implied other person rather than delivering a detached statement;
- reserved_flatness: restrained, impersonal, emotionally flat, or socially withdrawn presentation.

Judge only cues present in the supplied words. Do not infer identity or use outside political
knowledge, ideology, office, confidence, toughness, aggression, policy position, or polished
professional speaking. Do not score from the amount of text or response length alone; all samples
are equal-length and content-based interpersonal cues are required. Absence of evidence is low, not
average. Output JSON only:
{"A":{"social_energy":0,"enthusiastic_engagement":0,"expressive_affect":0,"spontaneous_self_disclosure":0,"conversational_responsiveness":0,"reserved_flatness":0,"confidence":"low|medium|high"},
 "B":{"social_energy":0,"enthusiastic_engagement":0,"expressive_affect":0,"spontaneous_self_disclosure":0,"conversational_responsiveness":0,"reserved_flatness":0,"confidence":"low|medium|high"}}
"""


def stable_half(package, salt):
    raw = (salt + "\0" + package).encode("utf-8", "surrogatepass")
    return hashlib.sha256(raw).digest()[0] & 1


def deidentify(text, member):
    result = text
    names = [member] + [part for part in re.split(r"[^A-Za-zÀ-ÿ'-]+", member) if len(part) >= 3]
    for name in sorted(set(names), key=len, reverse=True):
        result = re.sub(r"\b%s\b" % re.escape(name), "[OFFICIAL]", result, flags=re.I)
    return result


def excerpt(member, packages):
    candidates = []
    for package, turns in packages:
        for index, text in enumerate(turns):
            if len(text.split()) < 8:
                continue
            key = hashlib.sha256((package + "\0" + str(index)).encode("utf-8", "replace")).hexdigest()
            candidates.append((key, deidentify(text.strip(), member)))
    candidates.sort()
    tokens = []
    for _key, text in candidates:
        tokens.extend(text.split())
        if len(tokens) >= SAMPLE_WORDS:
            break
    if len(tokens) < SAMPLE_WORDS:
        return None
    return " ".join(tokens[:SAMPLE_WORDS])


def build_samples():
    con = sqlite3.connect(_o.path.join(B, "social_media.db"), timeout=60)
    con.execute("PRAGMA query_only=1")
    packs = collections.defaultdict(lambda: collections.defaultdict(list))
    query = "select member,package,text from speeches where source='INTERVIEW' order by rowid"
    for member, package, text in con.execute(query):
        if member and package and text and len(text.split()) >= 8:
            packs[member][package].append(text.strip())
    con.close()

    samples = {name: {} for name in SALTS}
    for split_name, salt in SALTS.items():
        for member, package_map in packs.items():
            halves = [[], []]
            for package, turns in package_map.items():
                halves[stable_half(package, salt)].append((package, turns))
            record = []
            for half in halves:
                text = excerpt(member, half)
                record.append(
                    {
                        "packages": len(half),
                        "available_words": sum(len(t.split()) for _p, ts in half for t in ts if len(t.split()) >= 8),
                        "text": text,
                    }
                )
            if all(row["packages"] >= MIN_PACKAGES and row["text"] is not None for row in record):
                samples[split_name][member] = record
    return samples


def api_key():
    value = _o.environ.get("ANTHROPIC_API_KEY", "").strip()
    path = _o.path.join(B, "fec", "anthropic_key.txt")
    if not value and _o.path.exists(path):
        value = open(path, encoding="utf-8").read().strip()
    return value


def parse_json(text):
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I | re.S)
    obj, _end = json.JSONDecoder().raw_decode(clean.lstrip())
    for half in ("A", "B"):
        row = obj[half]
        for field in FIELDS:
            row[field] = int(max(0, min(100, round(float(row[field])))))
        positive = [row[field] for field in FIELDS[:-1]]
        row["observed_e"] = round((sum(positive) + 100 - row["reserved_flatness"]) / 6.0, 3)
        row["confidence"] = str(row.get("confidence", "low")).lower()
    return obj


def score_one(client, member, split_name, halves):
    prompt = RUBRIC + "\n\nHALF A:\n" + halves[0]["text"] + "\n\nHALF B:\n" + halves[1]["text"]
    error = None
    for attempt in range(5):
        try:
            message = client.messages.create(
                model=MODEL,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            parsed = parse_json(message.content[0].text)
            return member, split_name, {
                "halves": parsed,
                "packages": [halves[0]["packages"], halves[1]["packages"]],
                "available_words": [halves[0]["available_words"], halves[1]["available_words"]],
                "sample_words": SAMPLE_WORDS,
            }, None
        except Exception as exc:
            error = "%s: %s" % (type(exc).__name__, exc)
            time.sleep(2 ** attempt)
    return member, split_name, None, error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--go", action="store_true", help="cost gate: collect Haiku ratings")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    samples = build_samples()
    print(
        "interview observed-E eligible: %s | calls %d | equal sample %d words/half"
        % (", ".join("%s=%d" % (name, len(rows)) for name, rows in samples.items()), sum(map(len, samples.values())), SAMPLE_WORDS)
    )
    if not args.go:
        print("read-only coverage check complete; pass --go to collect with %s" % MODEL)
        return
    key = api_key()
    if not key:
        raise SystemExit("ANTHROPIC_API_KEY / fec/anthropic_key.txt missing")
    import anthropic

    client = anthropic.Anthropic(api_key=key)
    prior = json.load(open(OUT, encoding="utf-8")) if _o.path.exists(OUT) else {}
    members = prior.get("members", {})
    errors = prior.get("errors", {})
    todo = []
    for split_name, rows in samples.items():
        for member in sorted(rows):
            if split_name not in members.get(member, {}):
                todo.append((member, split_name, rows[member]))
    if args.limit:
        todo = todo[: args.limit]
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(score_one, client, *item) for item in todo]
        for index, future in enumerate(as_completed(futures), 1):
            member, split_name, record, error = future.result()
            key_name = member + "|" + split_name
            if record is not None:
                members.setdefault(member, {})[split_name] = record
                errors.pop(key_name, None)
            else:
                errors[key_name] = error
            dump_atomic(
                {
                    "model": MODEL,
                    "rubric_version": "observed-interview-e-v1-locked-2026-07-13",
                    "split_salts": SALTS,
                    "sample_words": SAMPLE_WORDS,
                    "eligible": {name: len(rows) for name, rows in samples.items()},
                    "members": members,
                    "errors": errors,
                },
                OUT,
                indent=1,
            )
            if index % 25 == 0 or index == len(futures):
                complete = sum(len(row) for row in members.values())
                print("  completed %d/%d this run | total %d | errors %d" % (index, len(futures), complete, len(errors)), flush=True)
    print("interview_e_persona_halves.json.candidate: %d ratings | %d errors" % (sum(len(row) for row in members.values()), len(errors)))


if __name__ == "__main__":
    main()
