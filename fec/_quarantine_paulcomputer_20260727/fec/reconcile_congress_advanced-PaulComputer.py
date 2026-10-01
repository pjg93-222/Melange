#!/usr/bin/env python3
"""Reconcile the 62 Congress.gov Advanced Search query files into the two
authoritative discovery NDJSON artifacts.

Rebuilt 2026-07-27 after the original was lost. The raw collection artifacts
(``queries/*.json`` and ``raw/pages/**``) survived intact, so this reconstructs
the derived layer from them rather than re-scraping Congress.gov.

Outputs
-------
* ``congress_advanced_records.ndjson``     -- one row per unique candidate
  (declared: 18,557), keyed by ``canonical_key``.
* ``congress_advanced_memberships.ndjson`` -- one row per
  ``(canonical_key, query_id)`` edge (declared: 64,004).

Canonical encoding
------------------
Recovered empirically from the surviving ``records_sha256`` values: compact
separators, ``ensure_ascii=False``, insertion-ordered keys. ``interchange`` has
a single page, so its page-level and query-level hashes coincide, which pins
the encoding exactly. ``--verify-encoding`` re-proves this against all 62 files
before anything is written.

Safety
------
Read-only with respect to every collection artifact. Writes only the two output
files, and only when ``--write`` is given. ``--verify`` computes and reports
without writing anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from collections import Counter

WORKSPACE = pathlib.Path(__file__).resolve().parents[1]
PAGES_DIR = (
    WORKSPACE / "audits" / "legfix5" / "congress_advanced_pages_20260725"
)

RECORDS_NAME = "congress_advanced_records.ndjson"
MEMBERSHIPS_NAME = "congress_advanced_memberships.ndjson"

# Per-query provenance carried on the membership edge, not on the union record.
EDGE_FIELDS = ("source_query_id", "source_page", "source_rank")

# Query-registry fields that describe the edge's authority.
QUERY_META = (
    "query_id",
    "label",
    "scoring_category",
    "record_kind",
    "parent_category_id",
    "parent_category_label",
    "identifier_text",
    "title_alias",
    "ambiguous_short_act_alias",
    "membership_non_dispositive",
)


def dumps(obj) -> str:
    """The canonical encoding recovered from records_sha256."""
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf8")).hexdigest()


def load_queries() -> list[dict]:
    files = sorted((PAGES_DIR / "queries").glob("*.json"))
    if not files:
        raise SystemExit("no query files under %s" % (PAGES_DIR / "queries"))
    out = []
    for f in files:
        out.append(json.loads(f.read_text("utf8")))
    return out


def verify_encoding(queries: list[dict]) -> tuple[int, int]:
    """Re-prove the canonical encoding against every query's records_sha256."""
    ok = bad = 0
    for q in queries:
        declared = q.get("records_sha256")
        if not declared:
            continue
        if sha256_text(dumps(q["records"])) == declared:
            ok += 1
        else:
            bad += 1
            print("  encoding mismatch: %s" % q.get("query_id"))
    return ok, bad


def build(queries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Union the per-query record lists into records and membership edges.

    A candidate discovered by several queries yields one record and one edge
    per query. Record identity is ``canonical_key``; the first occurrence wins,
    with queries processed in registry order so the result is deterministic.
    """
    records: dict[str, dict] = {}
    memberships: list[dict] = []

    for q in queries:
        qmeta = {k: q.get(k) for k in QUERY_META}
        qid = q["query_id"]
        for rec in q["records"]:
            key = rec["canonical_key"]
            if key not in records:
                records[key] = {
                    k: v for k, v in rec.items() if k not in EDGE_FIELDS
                }
            edge = {"canonical_key": key}
            edge.update(qmeta)
            edge["source_page"] = rec.get("source_page")
            edge["source_rank"] = rec.get("source_rank")
            memberships.append(edge)

    return list(records.values()), memberships


def classify(records: list[dict], memberships: list[dict],
             queries: list[dict]) -> dict:
    """Reproduce the manifest.union coverage counters as a content check."""
    by_query = {q["query_id"]: q for q in queries}
    scoring_keys, probe_keys, monitor_keys = set(), set(), set()

    for e in memberships:
        q = by_query[e["query_id"]]
        key = e["canonical_key"]
        if q.get("scoring_category"):
            scoring_keys.add(key)
        elif q.get("record_kind") == "coverage_probe":
            probe_keys.add(key)
        else:
            monitor_keys.add(key)

    return {
        "unique_record_count": len(records),
        "membership_count": len(memberships),
        "scoring_candidate_count": len(scoring_keys),
        "monitor_candidate_count": len(monitor_keys),
        "recall_probe_count": len(probe_keys),
        "recall_only_unclassified_count": len(
            (probe_keys | monitor_keys) - scoring_keys),
        "counts_by_congress": dict(
            sorted(Counter(str(r["congress"]) for r in records).items())),
        "counts_by_type": dict(
            sorted(Counter(r["type"] for r in records).items())),
    }


def compare(label: str, got, want) -> bool:
    same = got == want
    print("  %-34s %-9s got=%s%s" % (
        label, "MATCH" if same else "DIFF", got,
        "" if same else "  want=%s" % (want,)))
    return same


def atomic_write(path: pathlib.Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf8", newline="")
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="compute and report without writing")
    ap.add_argument("--write", action="store_true",
                    help="write the two NDJSON artifacts")
    ap.add_argument("--verify-encoding", action="store_true",
                    help="re-prove the canonical encoding, then exit")
    args = ap.parse_args()

    if not (args.verify or args.write or args.verify_encoding):
        ap.error("choose --verify, --write, or --verify-encoding")

    queries = load_queries()
    print("query files loaded: %d" % len(queries))

    print("\n=== canonical encoding check ===")
    ok, bad = verify_encoding(queries)
    print("  records_sha256 reproduced: %d ok, %d mismatched" % (ok, bad))
    if bad:
        print("  REFUSING: encoding is not proven; outputs would be unfaithful.")
        return 2
    if args.verify_encoding:
        return 0

    records, memberships = build(queries)
    stats = classify(records, memberships, queries)

    manifest = json.loads((PAGES_DIR / "manifest.json").read_text("utf8"))
    union = manifest["union"]

    print("\n=== content reconciliation vs manifest.union ===")
    allok = True
    for k in ("unique_record_count", "membership_count",
              "scoring_candidate_count", "monitor_candidate_count",
              "recall_probe_count", "counts_by_congress", "counts_by_type"):
        allok &= compare(k, stats[k], union.get(k))
    compare("recall_only_unclassified_count",
            stats["recall_only_unclassified_count"],
            union.get("coverage_visibility", {}).get(
                "recall_only_unclassified_count"))

    rec_text = "".join(dumps(r) + "\n" for r in records)
    mem_text = "".join(dumps(m) + "\n" for m in memberships)

    print("\n=== output hashes ===")
    print("  records      %s  (%d bytes)" % (
        sha256_text(rec_text), len(rec_text.encode("utf8"))))
    print("  memberships  %s  (%d bytes)" % (
        sha256_text(mem_text), len(mem_text.encode("utf8"))))
    print("  collection-time targets : %s / %s" % (
        union.get("records_sha256", "")[:16],
        union.get("memberships_sha256", "")[:16]))
    print("  pipeline-consumed targets: f71add90ab1d33ac / f6d61c830c1079bd")

    if not allok:
        print("\nCONTENT MISMATCH -- not writing.")
        return 1

    if args.write:
        atomic_write(PAGES_DIR / RECORDS_NAME, rec_text)
        atomic_write(PAGES_DIR / MEMBERSHIPS_NAME, mem_text)
        print("\nwrote %s and %s" % (RECORDS_NAME, MEMBERSHIPS_NAME))
    else:
        print("\n--verify only; nothing written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
