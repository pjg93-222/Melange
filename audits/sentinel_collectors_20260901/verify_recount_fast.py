#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fast press refresh recount verification."""
from __future__ import annotations

import csv
import hashlib
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


def count_csv(path):
    count = 0
    if not Path(path).is_file():
        return 0
    with io.open(path, encoding="utf-8-sig", newline="") as handle:
        for _ in csv.DictReader(handle):
            count += 1
    return count


def count_jsonl(path):
    count = 0
    if not Path(path).is_file():
        return 0
    with io.open(path, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                count += 1
    return count


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    staging_root = Path(r"C:\Users\pgoff\AppData\Local\Temp\claude\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-sentinel-collectors-progress-f7de7d\d573ef55-b2ca-4ec1-a60f-2784a7960ad4\scratchpad\staging")
    prod_root = Path(r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems")

    print("=" * 80)
    print("PRESS REFRESH RECOUNT VERIFICATION (FAST)")
    print("=" * 80)

    # Staged files
    staged_tone = staging_root / "data" / "stance" / "press_refresh_tone.csv"
    staged_fulltext = staging_root / "data" / "stance" / "press_refresh_fulltext.jsonl"
    staged_mentions = staging_root / "data" / "press" / "official_mentions.jsonl"
    staged_receipt = staging_root / "data" / "stance" / "press_refresh_feed_receipt.json"

    # Production files
    prod_tone = prod_root / "data" / "stance" / "press_refresh_tone.csv"
    prod_fulltext = prod_root / "data" / "stance" / "press_refresh_fulltext.jsonl"
    prod_mentions = prod_root / "data" / "press" / "official_mentions.jsonl"
    prod_receipt = prod_root / "data" / "stance" / "press_refresh_feed_receipt.json"

    # Count rows
    print("\n[COUNT CHECK]")
    c_tone_count = count_csv(staged_tone)
    c_fulltext_count = count_jsonl(staged_fulltext)
    c_mentions_count = count_jsonl(staged_mentions)

    a_tone_count = count_csv(prod_tone)
    a_fulltext_count = count_jsonl(prod_fulltext)
    a_mentions_count = count_jsonl(prod_mentions)

    print(f"  Staged: tone {c_tone_count} (exp 294), fulltext {c_fulltext_count} (exp 294), mentions {c_mentions_count} (exp 22243)")
    print(f"  Prod:   tone {a_tone_count} (exp 255), fulltext {a_fulltext_count} (exp 255), mentions {a_mentions_count} (exp 19561)")

    c1_pass = (c_tone_count == 294 and c_fulltext_count == 294 and c_mentions_count == 22243)
    c2_pass = (a_tone_count == 255 and a_fulltext_count == 255 and a_mentions_count == 19561)

    print(f"  Staged counts: {'PASS' if c1_pass else 'FAIL'}")
    print(f"  Prod counts: {'PASS' if c2_pass else 'FAIL'}")

    # Check hashes
    print("\n[FILE HASHES]")
    try:
        receipt = json.loads(staged_receipt.read_text(encoding="utf-8"))
        outputs_sha256 = receipt.get("outputs_sha256") or {}

        tone_hash_actual = sha256_file(staged_tone)
        fulltext_hash_actual = sha256_file(staged_fulltext)
        mentions_hash_actual = sha256_file(staged_mentions)

        tone_hash_receipt = outputs_sha256.get("data/stance/press_refresh_tone.csv")
        fulltext_hash_receipt = outputs_sha256.get("data/stance/press_refresh_fulltext.jsonl")
        mentions_hash_receipt = outputs_sha256.get("data/press/official_mentions.jsonl")

        print(f"  Tone CSV:      {tone_hash_receipt == tone_hash_actual}")
        print(f"  Fulltext JSONL: {fulltext_hash_receipt == fulltext_hash_actual}")
        print(f"  Mentions JSONL: {mentions_hash_receipt == mentions_hash_actual}")

        c5_pass = (
            tone_hash_receipt == tone_hash_actual and
            fulltext_hash_receipt == fulltext_hash_actual and
            mentions_hash_receipt == mentions_hash_actual
        )
        print(f"  All hashes match: {'PASS' if c5_pass else 'FAIL'}")

        # Check receipt metadata
        print("\n[RECEIPT METADATA]")
        promotion_mode = receipt.get("promotion_mode")
        c6_pass = promotion_mode == "CUMULATIVE_ACCEPTED_RUN_LEDGER"
        print(f"  promotion_mode: {promotion_mode} ({'PASS' if c6_pass else 'FAIL'})")

        accepted_runs = receipt.get("accepted_runs") or []
        dates = []
        for run in accepted_runs:
            source_run = run.get("source_run") or ""
            if "press_refresh_" in source_run:
                date_part = source_run.split("press_refresh_")[-1]
                if date_part:
                    dates.append(date_part)

        expected_dates = ["20260828", "20260830", "20260831", "20260901"]
        c7_pass = dates == expected_dates
        print(f"  accepted_runs: {dates}")
        print(f"  Expected:      {expected_dates}")
        print(f"  Match: {'PASS' if c7_pass else 'FAIL'}")

    except Exception as e:
        print(f"  ERROR reading receipt: {e}")
        c5_pass = c6_pass = c7_pass = False

    # Check archive receipts
    print("\n[ARCHIVE RECEIPTS]")
    archive_dir = staging_root / "data" / "engine" / "press_collection_receipts"
    if archive_dir.is_dir():
        receipt_files = sorted(archive_dir.glob("press_refresh_*.json"))
        print(f"  Found {len(receipt_files)} receipt files")

        has_20260829 = any("20260829" in f.name for f in receipt_files)
        all_accepted = all(
            json.loads(f.read_text(encoding="utf-8")).get("status") == "ACCEPTED"
            for f in receipt_files if f.is_file()
        )

        c8_pass = (len(receipt_files) == 4 and not has_20260829 and all_accepted)
        print(f"  Count: {len(receipt_files)} ({'PASS' if len(receipt_files) == 4 else 'FAIL'})")
        print(f"  No 20260829: {not has_20260829} ({'PASS' if not has_20260829 else 'FAIL'})")
        print(f"  All ACCEPTED: {all_accepted} ({'PASS' if all_accepted else 'FAIL'})")
    else:
        c8_pass = False
        print(f"  ERROR: Archive directory not found")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    results = {
        "Staged row counts": c1_pass,
        "Production row counts": c2_pass,
        "File hashes match": c5_pass,
        "promotion_mode correct": c6_pass,
        "accepted_runs dates": c7_pass,
        "Archive receipts": c8_pass,
    }

    for name, result in results.items():
        print(f"  {'PASS' if result else 'FAIL'}  {name}")

    all_pass = all(results.values())
    print("\n" + ("ALL CHECKS PASSED" if all_pass else "SOME CHECKS FAILED"))
    print("=" * 80)

    return 0 if all_pass else 1


if __name__ == "__main__":
    exit(main())
