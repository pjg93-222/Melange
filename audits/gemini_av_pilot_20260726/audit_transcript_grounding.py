#!/usr/bin/env python3
"""Exploratory audit of Gemini excerpts against the project's caption cache."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PILOT = Path(__file__).resolve().parent
MANIFEST = PILOT / "manifest.json"
RESULTS = PILOT / "results"
CAPTIONS = ROOT / "b5_caption_cache.json"
OUTPUT = PILOT / "transcript_grounding_report.json"


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower())


def bag_coverage(needle: list[str], haystack: list[str]) -> float:
    if not needle:
        return 0.0
    available = Counter(haystack)
    matched = 0
    for token in needle:
        if available[token] > 0:
            matched += 1
            available[token] -= 1
    return matched / len(needle)


def longest_contiguous_match(needle: list[str], haystack: list[str]) -> int:
    if not needle or not haystack:
        return 0
    previous = [0] * (len(haystack) + 1)
    best = 0
    for left in needle:
        current = [0]
        for index, right in enumerate(haystack, start=1):
            value = previous[index - 1] + 1 if left == right else 0
            current.append(value)
            best = max(best, value)
        previous = current
    return best


def youtube_id(item: dict) -> str:
    source_id = str(item.get("source_id", ""))
    if source_id:
        return source_id.split(":", 1)[-1]
    url = str(item.get("source_url", ""))
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{6,})", url)
    return match.group(1) if match else ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    manifest_document = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest = manifest_document["items"]
    caption_cache = json.loads(CAPTIONS.read_text(encoding="utf-8"))
    rows = []

    for item in manifest:
        pilot_id = item["pilot_id"]
        result_path = args.results / f"{pilot_id}.json"
        if not result_path.exists():
            continue
        result = json.loads(result_path.read_text(encoding="utf-8"))
        excerpt = str(result.get("transcript_excerpt", ""))
        source_key = youtube_id(item)
        caption = str(caption_cache.get(source_key, ""))
        excerpt_tokens = tokens(excerpt)
        caption_tokens = tokens(caption)
        coverage = bag_coverage(excerpt_tokens, caption_tokens)
        contiguous = longest_contiguous_match(excerpt_tokens, caption_tokens)
        grounded = bool(caption_tokens) and (coverage >= 0.80 or contiguous >= 4)
        rows.append(
            {
                "pilot_id": pilot_id,
                "source_id": source_key,
                "excerpt": excerpt,
                "excerpt_token_count": len(excerpt_tokens),
                "caption_available": bool(caption_tokens),
                "bag_token_coverage": round(coverage, 6),
                "longest_contiguous_token_match": contiguous,
                "exploratory_grounded": grounded,
            }
        )

    available = [row for row in rows if row["caption_available"]]
    grounded = [row for row in available if row["exploratory_grounded"]]
    report = {
        "status": "exploratory_post_primary",
        "method": (
            "A Gemini excerpt is provisionally grounded when at least 80% of its "
            "bag-of-token content appears in the cached caption, or it shares an "
            "exact contiguous sequence of at least four normalized tokens."
        ),
        "important_limitations": [
            "This check was specified after the primary run and is not a preregistered gate.",
            "The caption cache is an ASR-derived reference, not a human transcript.",
            "Token overlap demonstrates speech-content access, not speaker identity.",
        ],
        "n_total": len(rows),
        "n_caption_available": len(available),
        "n_exploratory_grounded": len(grounded),
        "grounded_rate_among_available": (
            round(len(grounded) / len(available), 6) if available else None
        ),
        "rows": rows,
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "rows"}, indent=2))


if __name__ == "__main__":
    main()
