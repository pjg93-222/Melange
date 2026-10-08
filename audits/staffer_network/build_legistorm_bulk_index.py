#!/usr/bin/env python3
"""Build a bulk public LegiStorm profile index from Common Crawl CDX data.

This removes search-engine/person-by-person discovery from the acquisition hot
path.  It does not authenticate to LegiStorm and it does not promote identity
matches: all output rows remain candidates for later adjudication.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import gzip
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any, Iterable
from urllib.parse import unquote, urlsplit

import requests


COLLINFO_URL = "https://index.commoncrawl.org/collinfo.json"
PROFILE_RE = re.compile(r"/person/bio/(\d+)/([^/?#]+?)\.html$", re.I)
TOKEN_RE = re.compile(r"[a-z0-9]+")
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}
USER_AGENT = (
    "MelangeResearchBot/1.0 "
    "(public-records research; bulk index discovery from Common Crawl)"
)


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tokens(value: str) -> tuple[str, ...]:
    result = TOKEN_RE.findall(unquote(value).replace("_", " ").casefold())
    while result and result[-1] in SUFFIXES:
        result.pop()
    return tuple(result)


def profile_parts(url: str) -> tuple[str, tuple[str, ...]] | None:
    match = PROFILE_RE.search(urlsplit(url).path)
    if not match:
        return None
    name_tokens = tokens(match.group(2))
    if len(name_tokens) < 2:
        return None
    return match.group(1), name_tokens


def read_queue(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = list(rows)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for row in materialized:
                stream.write(canonical_bytes(row))
    return len(materialized)


def get_collections(timeout: float) -> list[dict[str, Any]]:
    response = requests.get(
        COLLINFO_URL,
        headers={"User-Agent": USER_AGENT},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def query_collection(collection: dict[str, Any], timeout: float) -> dict[str, Any]:
    params = {
        "url": "www.legistorm.com/person/bio/",
        "matchType": "prefix",
        "output": "json",
        "filter": "status:200",
    }
    error = None
    for attempt in range(4):
        try:
            response = requests.get(
                collection["cdx-api"],
                params=params,
                headers={"User-Agent": USER_AGENT},
                timeout=timeout,
            )
            if response.status_code == 404:
                return {
                    "collection": collection["id"],
                    "records": [],
                    "status": "NO_CAPTURES",
                }
            response.raise_for_status()
            records = []
            for line in response.text.splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                parts = profile_parts(row.get("url", ""))
                if parts is None:
                    continue
                profile_id, name_tokens = parts
                records.append(
                    {
                        "profile_id": profile_id,
                        "name_tokens": name_tokens,
                        "url": row["url"],
                        "timestamp": row.get("timestamp", ""),
                        "digest": row.get("digest"),
                        "filename": row.get("filename"),
                        "offset": int(row["offset"]) if row.get("offset") else None,
                        "length": int(row["length"]) if row.get("length") else None,
                        "collection": collection["id"],
                    }
                )
            return {
                "collection": collection["id"],
                "records": records,
                "status": "CAPTURED",
            }
        except (requests.RequestException, ValueError) as exc:
            error = type(exc).__name__
            time.sleep(min(2**attempt, 8))
    return {"collection": collection["id"], "records": [], "status": error or "ERROR"}


def candidate_row(
    rank: int,
    queue_row: dict[str, Any],
    exact: dict[tuple[str, ...], list[str]],
    first_last: dict[tuple[str, str], list[str]],
    profiles: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    name_tokens = tokens(queue_row["display_name"])
    candidate_ids: list[str]
    method: str
    if name_tokens and exact.get(name_tokens):
        candidate_ids = sorted(set(exact[name_tokens]), key=int)
        method = "EXACT_NORMALIZED_FULL_NAME"
    elif len(name_tokens) >= 2 and first_last.get((name_tokens[0], name_tokens[-1])):
        candidate_ids = sorted(
            set(first_last[(name_tokens[0], name_tokens[-1])]), key=int
        )
        method = "UNIQUE_FIRST_LAST" if len(candidate_ids) == 1 else "AMBIGUOUS_FIRST_LAST"
    else:
        candidate_ids = []
        method = "NO_INDEX_MATCH"
    return {
        "schema_id": "staffer-network-legistorm-bulk-url-candidate-v1",
        "queue_rank": rank,
        "candidate_id": queue_row["candidate_id"],
        "lda_source_person_id": queue_row["lda_source_person_id"],
        "display_name": queue_row["display_name"],
        "name_tokens": name_tokens,
        "match_method": method,
        "candidate_count": len(candidate_ids),
        "canonical_identity_decision": "NOT_ADJUDICATED",
        "canonical_merge": False,
        "profile_candidates": [profiles[profile_id] for profile_id in candidate_ids[:20]],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        default=(
            "C:/Users/pgoff/AppData/Local/Melange/staffer_network/"
            "employment-lookup/generation-20260831T050000Z/"
            "employment_lookup_queue.ndjson.gz"
        ),
    )
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--max-collections", type=int)
    parser.add_argument(
        "--collection-id",
        action="append",
        help="Query only this Common Crawl collection id; may be repeated.",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.timeout <= 0:
        raise SystemExit("invalid workers or timeout")

    queue_path = Path(args.queue)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    if args.collection_id:
        collections = [
            {
                "id": collection_id,
                "cdx-api": f"https://index.commoncrawl.org/{collection_id}-index",
            }
            for collection_id in args.collection_id
        ]
    else:
        collections = get_collections(args.timeout)
    if args.max_collections is not None:
        collections = collections[: args.max_collections]

    collection_results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(query_collection, collection, args.timeout): collection["id"]
            for collection in collections
        }
        for future in as_completed(futures):
            result = future.result()
            collection_results.append(result)
            print(
                json.dumps(
                    {
                        "collection": result["collection"],
                        "records": len(result["records"]),
                        "status": result["status"],
                    },
                    sort_keys=True,
                ),
                flush=True,
            )

    # Keep the newest known capture for each stable LegiStorm profile id.
    profiles: dict[str, dict[str, Any]] = {}
    capture_count = 0
    for result in collection_results:
        for record in result["records"]:
            capture_count += 1
            current = profiles.get(record["profile_id"])
            if current is None or record["timestamp"] > current["timestamp"]:
                profiles[record["profile_id"]] = record

    profile_rows = [profiles[key] for key in sorted(profiles, key=int)]
    exact: defaultdict[tuple[str, ...], list[str]] = defaultdict(list)
    first_last: defaultdict[tuple[str, str], list[str]] = defaultdict(list)
    for profile in profile_rows:
        profile_tokens = tuple(profile["name_tokens"])
        exact[profile_tokens].append(profile["profile_id"])
        first_last[(profile_tokens[0], profile_tokens[-1])].append(profile["profile_id"])

    queue = read_queue(queue_path)
    match_rows = [
        candidate_row(rank, row, exact, first_last, profiles)
        for rank, row in enumerate(queue, start=1)
    ]

    profiles_path = output_root / "legistorm_public_profile_index.ndjson.gz"
    matches_path = output_root / "legistorm_queue_url_candidates.ndjson.gz"
    write_gzip(profiles_path, profile_rows)
    write_gzip(matches_path, match_rows)
    method_counts = Counter(row["match_method"] for row in match_rows)
    matched = sum(row["candidate_count"] > 0 for row in match_rows)
    unambiguous = sum(row["candidate_count"] == 1 for row in match_rows)
    receipt = {
        "schema_id": "staffer-network-legistorm-bulk-index-receipt-v1",
        "status": "PASS",
        "collections_queried": len(collections),
        "collection_status_counts": dict(
            sorted(Counter(row["status"] for row in collection_results).items())
        ),
        "common_crawl_capture_rows": capture_count,
        "unique_legistorm_profiles": len(profile_rows),
        "queue_rows": len(queue),
        "queue_rows_with_candidates": matched,
        "queue_rows_with_one_candidate": unambiguous,
        "match_method_counts": dict(sorted(method_counts.items())),
        "identity_adjudication_performed": False,
        "authenticated_sessions_used": 0,
        "files": [
            {
                "role": "profile_index",
                "path": profiles_path.name,
                "bytes": profiles_path.stat().st_size,
                "sha256": sha256_file(profiles_path),
            },
            {
                "role": "queue_candidates",
                "path": matches_path.name,
                "bytes": matches_path.stat().st_size,
                "sha256": sha256_file(matches_path),
            },
        ],
    }
    receipt_path = output_root / "legistorm_bulk_index_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    print(json.dumps(receipt, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
