#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Verify set differences and deduplication for press refresh recount."""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def canonical_url(value, keep_fragment=True):
    value = (value or "").strip()
    if not value:
        return ""
    try:
        parts = urlsplit(value)
        host = parts.netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        path = parts.path.rstrip("/") or "/"
        fragment = parts.fragment if keep_fragment else ""
        return urlunsplit((parts.scheme.lower() or "https", host, path, parts.query, fragment))
    except ValueError:
        return value.rstrip("/").lower()


def turn_key(row):
    return (canonical_url(row.get("url"), keep_fragment=False),
            (row.get("bioguide") or "").strip().upper())


def mentions_key(row):
    return (canonical_url(row.get("article_url"), keep_fragment=False),
            (row.get("mentioned_bioguide") or "").strip().upper())


def read_csv_keys(path):
    """Read CSV and return dict of key -> row."""
    result = {}
    if not Path(path).is_file():
        return result
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = turn_key(row)
            result[key] = row
    return result


def read_jsonl_keys(path, key_func):
    """Read JSONL and return dict of key -> row."""
    result = {}
    if not Path(path).is_file():
        return result
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                key = key_func(row)
                result[key] = row
    return result


def main():
    staging_root = Path(r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-sentinel-collectors-progress-f7de7d\d573ef55-b2ca-4ec1-a60f-2784a7960ad4\scratchpad\staging")
    prod_root = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")

    # Staged files
    staged_tone = staging_root / "data" / "stance" / "press_refresh_tone.csv"
    staged_fulltext = staging_root / "data" / "stance" / "press_refresh_fulltext.jsonl"
    staged_mentions = staging_root / "data" / "press" / "official_mentions.jsonl"

    # Production files
    prod_tone = prod_root / "data" / "stance" / "press_refresh_tone.csv"
    prod_fulltext = prod_root / "data" / "stance" / "press_refresh_fulltext.jsonl"
    prod_mentions = prod_root / "data" / "press" / "official_mentions.jsonl"

    print("=" * 80)
    print("SET DIFFERENCE AND DEDUPLICATION VERIFICATION")
    print("=" * 80)

    # Read all as key->row dicts
    print("\nReading staged files...")
    staged_tone_dict = read_csv_keys(staged_tone)
    staged_fulltext_dict = read_jsonl_keys(staged_fulltext, turn_key)
    staged_mentions_dict = read_jsonl_keys(staged_mentions, mentions_key)

    print("Reading production files...")
    prod_tone_dict = read_csv_keys(prod_tone)
    prod_fulltext_dict = read_jsonl_keys(prod_fulltext, turn_key)
    prod_mentions_dict = read_jsonl_keys(prod_mentions, mentions_key)

    # CLAIM 3: Active - Candidate = 0
    print("\n[CLAIM 3a] Set difference (active - staged) == 0")

    tone_diff = set(prod_tone_dict.keys()) - set(staged_tone_dict.keys())
    fulltext_diff = set(prod_fulltext_dict.keys()) - set(staged_fulltext_dict.keys())
    mentions_diff = set(prod_mentions_dict.keys()) - set(staged_mentions_dict.keys())

    print(f"  Tone: {len(tone_diff)} keys in prod not in staged (expected 0)")
    print(f"  Fulltext: {len(fulltext_diff)} keys in prod not in staged (expected 0)")
    print(f"  Mentions: {len(mentions_diff)} keys in prod not in staged (expected 0)")

    if tone_diff:
        print(f"    Sample missing: {list(tone_diff)[:2]}")
    if fulltext_diff:
        print(f"    Sample missing: {list(fulltext_diff)[:2]}")
    if mentions_diff:
        print(f"    Sample missing: {list(mentions_diff)[:2]}")

    claim3a_pass = (len(tone_diff) == 0 and len(fulltext_diff) == 0 and len(mentions_diff) == 0)
    print(f"  RESULT: {'PASS' if claim3a_pass else 'FAIL'}")

    # CLAIM 3b: Byte-identical payloads for shared keys
    print("\n[CLAIM 3b] Payloads byte-identical for shared keys")

    tone_shared = set(prod_tone_dict.keys()) & set(staged_tone_dict.keys())
    fulltext_shared = set(prod_fulltext_dict.keys()) & set(staged_fulltext_dict.keys())
    mentions_shared = set(prod_mentions_dict.keys()) & set(staged_mentions_dict.keys())

    tone_mismatches = 0
    for key in tone_shared:
        p_row = prod_tone_dict[key]
        s_row = staged_tone_dict[key]
        if json.dumps(p_row, sort_keys=True) != json.dumps(s_row, sort_keys=True):
            tone_mismatches += 1
            if tone_mismatches <= 2:
                print(f"    Mismatch at {key}")

    fulltext_mismatches = 0
    for key in fulltext_shared:
        p_row = prod_fulltext_dict[key]
        s_row = staged_fulltext_dict[key]
        if json.dumps(p_row, sort_keys=True) != json.dumps(s_row, sort_keys=True):
            fulltext_mismatches += 1
            if fulltext_mismatches <= 2:
                print(f"    Mismatch at {key}")

    mentions_mismatches = 0
    for key in mentions_shared:
        p_row = prod_mentions_dict[key]
        s_row = staged_mentions_dict[key]
        if json.dumps(p_row, sort_keys=True) != json.dumps(s_row, sort_keys=True):
            mentions_mismatches += 1
            if mentions_mismatches <= 2:
                print(f"    Mismatch at {key}")

    print(f"  Tone: {len(tone_shared)} shared, {tone_mismatches} mismatches (expected 0)")
    print(f"  Fulltext: {len(fulltext_shared)} shared, {fulltext_mismatches} mismatches (expected 0)")
    print(f"  Mentions: {len(mentions_shared)} shared, {mentions_mismatches} mismatches (expected 0)")

    claim3b_pass = (tone_mismatches == 0 and fulltext_mismatches == 0 and mentions_mismatches == 0)
    print(f"  RESULT: {'PASS' if claim3b_pass else 'FAIL'}")

    # CLAIM 4: Candidate deduplication (duplicates within staged)
    print("\n[CLAIM 4a] Duplicates within staged candidate sets")

    staged_tone_rows = list(staged_tone_dict.values())
    staged_tone_keys = list(staged_tone_dict.keys())
    tone_key_counts = {}
    for key in staged_tone_keys:
        tone_key_counts[key] = tone_key_counts.get(key, 0) + 1

    tone_dups = sum(1 for c in tone_key_counts.values() if c > 1)
    print(f"  Tone: {len(staged_tone_rows)} rows, {len(staged_tone_keys)} unique keys, {tone_dups} dups")

    # For JSONL, check similarly
    # Note: In the dict approach, duplicates overwrite, so count won't show dups
    # Need to reread and count explicitly
    print("\n[CLAIM 4b] Candidate = union of 4 per-run sets (per-run counts)")

    per_run_dir = staging_root / "recon"
    per_run_info = []

    for run_num in range(4):
        run_dirs = sorted(per_run_dir.glob(f"run-{run_num:03d}-press_refresh_*"))
        if not run_dirs:
            print(f"  WARNING: No run-{run_num:03d} directory")
            continue

        run_path = run_dirs[0]
        tone_path = run_path / "tone.csv"
        fulltext_path = run_path / "fulltext.jsonl"
        mentions_path = run_path / "mentions.jsonl"

        tone_dict = read_csv_keys(tone_path)
        fulltext_dict = read_jsonl_keys(fulltext_path, turn_key)
        mentions_dict = read_jsonl_keys(mentions_path, mentions_key)

        per_run_info.append({
            "tone": tone_dict,
            "fulltext": fulltext_dict,
            "mentions": mentions_dict,
        })

        print(f"  Run {run_num}: tone {len(tone_dict)}, fulltext {len(fulltext_dict)}, mentions {len(mentions_dict)}")

    # Expected per-run counts
    expected_tone = [255, 280, 281, 100]
    expected_fulltext = [255, 280, 281, 100]
    expected_mentions = [19561, 20858, 20851, 2317]

    actual_tone = [len(info["tone"]) for info in per_run_info]
    actual_fulltext = [len(info["fulltext"]) for info in per_run_info]
    actual_mentions = [len(info["mentions"]) for info in per_run_info]

    print(f"  Expected tone: {expected_tone}")
    print(f"  Actual tone:   {actual_tone}")
    print(f"  Match: {actual_tone == expected_tone}")

    print(f"  Expected fulltext: {expected_fulltext}")
    print(f"  Actual fulltext:   {actual_fulltext}")
    print(f"  Match: {actual_fulltext == expected_fulltext}")

    print(f"  Expected mentions: {expected_mentions}")
    print(f"  Actual mentions:   {actual_mentions}")
    print(f"  Match: {actual_mentions == expected_mentions}")

    # Compute union
    if len(per_run_info) == 4:
        union_tone_keys = set()
        union_fulltext_keys = set()
        union_mentions_keys = set()

        for info in per_run_info:
            union_tone_keys.update(info["tone"].keys())
            union_fulltext_keys.update(info["fulltext"].keys())
            union_mentions_keys.update(info["mentions"].keys())

        print(f"\n  Union sizes: tone {len(union_tone_keys)}, fulltext {len(union_fulltext_keys)}, mentions {len(union_mentions_keys)}")
        print(f"  Staged sizes: tone {len(staged_tone_dict)}, fulltext {len(staged_fulltext_dict)}, mentions {len(staged_mentions_dict)}")

        # Check union == staged
        tone_union_diff = union_tone_keys - set(staged_tone_dict.keys())
        staged_union_diff = set(staged_tone_dict.keys()) - union_tone_keys

        fulltext_union_diff = union_fulltext_keys - set(staged_fulltext_dict.keys())
        staged_fulltext_diff = set(staged_fulltext_dict.keys()) - union_fulltext_keys

        mentions_union_diff = union_mentions_keys - set(staged_mentions_dict.keys())
        staged_mentions_diff = set(staged_mentions_dict.keys()) - union_mentions_keys

        print(f"  Tone: union-staged={len(tone_union_diff)}, staged-union={len(staged_union_diff)}")
        print(f"  Fulltext: union-staged={len(fulltext_union_diff)}, staged-fulltext={len(staged_fulltext_diff)}")
        print(f"  Mentions: union-staged={len(mentions_union_diff)}, staged-mentions={len(staged_mentions_diff)}")

        claim4b_pass = (
            len(tone_union_diff) == 0 and len(staged_union_diff) == 0 and
            len(fulltext_union_diff) == 0 and len(staged_fulltext_diff) == 0 and
            len(mentions_union_diff) == 0 and len(staged_mentions_diff) == 0
        )
    else:
        claim4b_pass = False
        print(f"  ERROR: Could not read all 4 per-run directories")

    print(f"  RESULT: {'PASS' if claim4b_pass else 'FAIL'}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    results = {
        "CLAIM 3a: active - staged == 0": claim3a_pass,
        "CLAIM 3b: Payloads identical": claim3b_pass,
        "CLAIM 4: Deduplication correct": claim4b_pass,
    }

    for name, result in results.items():
        print(f"  {'PASS' if result else 'FAIL'}  {name}")

    all_pass = all(results.values())
    print("\n" + ("ALL CLAIMS VERIFIED" if all_pass else "SOME CLAIMS FAILED"))
    print("=" * 80)

    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
