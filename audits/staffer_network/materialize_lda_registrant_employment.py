#!/usr/bin/env python3
"""Derive dated lobbyist-to-registrant employment/association episodes from LDA.

Every episode is supported by filings on which the person was named as a
lobbyist and the registrant was the filer.  These are source-native dated
employment/association facts, not claims of exhaustive lifetime history.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Iterable


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


def rows(path: Path) -> Iterable[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def write_gzip(path: Path, values: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            for value in values:
                stream.write(canonical_bytes(value))
                count += 1
    return count


def insert_batches(
    connection: sqlite3.Connection,
    statement: str,
    values: Iterable[tuple[Any, ...]],
    batch_size: int = 50_000,
) -> int:
    batch = []
    count = 0
    for value in values:
        batch.append(value)
        if len(batch) >= batch_size:
            connection.executemany(statement, batch)
            connection.commit()
            count += len(batch)
            batch.clear()
    if batch:
        connection.executemany(statement, batch)
        connection.commit()
        count += len(batch)
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lda-root",
        default=(
            "C:/Users/pgoff/AppData/Local/Melange/staffer_network/normalized/"
            "lda-source-native/generation-20260830T231200Z"
        ),
    )
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    lda_root = Path(args.lda_root)
    output_root = Path(args.output_root)
    if output_root.exists() and any(output_root.iterdir()):
        raise SystemExit(f"output root is nonempty: {output_root}")
    output_root.mkdir(parents=True, exist_ok=True)

    organizations = {
        row["source_org_id"]: row["display_name"]
        for row in rows(lda_root / "lda_organization_assertions.ndjson.gz")
        if row.get("organization_kind") == "registrant"
    }
    people = {
        row["source_person_id"]: row
        for row in rows(lda_root / "lda_lobbyist_assertions.ndjson.gz")
    }

    database_path = output_root / "join_work.sqlite3"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=MEMORY")
    connection.execute("PRAGMA cache_size=-524288")
    connection.execute(
        "CREATE TABLE activity (activity_id TEXT PRIMARY KEY, registrant_id TEXT NOT NULL, filing_year INTEGER NOT NULL, dt_posted TEXT NOT NULL) WITHOUT ROWID"
    )
    connection.execute(
        "CREATE TABLE person_activity (person_id TEXT NOT NULL, activity_id TEXT NOT NULL)"
    )

    activity_count = insert_batches(
        connection,
        "INSERT OR REPLACE INTO activity VALUES (?,?,?,?)",
        (
            (
                row["source_activity_id"],
                row["registrant_source_org_id"],
                int(row["filing_year"]),
                row["dt_posted"],
            )
            for row in rows(lda_root / "lda_activity_assertions.ndjson.gz")
        ),
    )
    person_activity_count = insert_batches(
        connection,
        "INSERT INTO person_activity VALUES (?,?)",
        (
            (row["subject_id"], row["object_id"])
            for row in rows(lda_root / "lda_industry_edges.ndjson.gz")
            if row.get("predicate") == "NAMED_ON_ACTIVITY"
            and row.get("subject_kind") == "person"
            and row.get("object_kind") == "lda_activity"
        ),
    )
    connection.execute("CREATE INDEX idx_person_activity_activity ON person_activity(activity_id)")
    connection.execute("CREATE INDEX idx_person_activity_person ON person_activity(person_id)")
    connection.commit()

    query = """
        SELECT pa.person_id, a.registrant_id,
               MIN(a.filing_year), MAX(a.filing_year),
               MIN(a.dt_posted), MAX(a.dt_posted),
               COUNT(*), GROUP_CONCAT(DISTINCT a.filing_year)
        FROM person_activity pa
        JOIN activity a ON a.activity_id = pa.activity_id
        GROUP BY pa.person_id, a.registrant_id
        ORDER BY pa.person_id, MIN(a.filing_year), a.registrant_id
    """
    episodes = []
    by_person: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for (
        person_id,
        registrant_id,
        first_year,
        last_year,
        first_dt,
        last_dt,
        support_count,
        year_csv,
    ) in connection.execute(query):
        filing_years = sorted({int(value) for value in year_csv.split(",")})
        episode_key = "\x1f".join((person_id, registrant_id, ",".join(map(str, filing_years))))
        episode = {
            "schema_id": "staffer-network-lda-registrant-employment-episode-v1",
            "episode_id": "lda:registrant-employment:" + hashlib.sha256(episode_key.encode()).hexdigest(),
            "lda_source_person_id": person_id,
            "display_name": people.get(person_id, {}).get("display_name"),
            "registrant_source_org_id": registrant_id,
            "employer_name": organizations.get(registrant_id),
            "start_year": int(first_year),
            "end_year": int(last_year),
            "filing_years": filing_years,
            "first_filing_posted_at": first_dt,
            "last_filing_posted_at": last_dt,
            "filing_activity_support_count": int(support_count),
            "date_precision": "filing_year",
            "relationship_type": "LOBBYIST_NAMED_ON_REGISTRANT_FILINGS",
            "source_system_id": "senate-lda-api",
            "canonical_employment_fact": False,
            "complete_lifetime_history_asserted": False,
        }
        episodes.append(episode)
        by_person[person_id].append(episode)

    person_rows = []
    for person_id in sorted(people, key=lambda value: int(value.rsplit(":", 1)[1])):
        person_episodes = by_person.get(person_id, [])
        years = sorted({year for episode in person_episodes for year in episode["filing_years"]})
        person_rows.append(
            {
                "schema_id": "staffer-network-lda-registrant-employment-person-v1",
                "lda_source_person_id": person_id,
                "display_name": people[person_id]["display_name"],
                "employment_episode_count": len(person_episodes),
                "employment_years_covered": years,
                "first_employment_year": min(years) if years else None,
                "last_employment_year": max(years) if years else None,
                "has_dated_employment_evidence": bool(years),
                "complete_lifetime_history_asserted": False,
            }
        )

    episodes_path = output_root / "lda_registrant_employment_episodes.ndjson.gz"
    people_path = output_root / "lda_registrant_employment_people.ndjson.gz"
    episode_count = write_gzip(episodes_path, episodes)
    person_count = write_gzip(people_path, person_rows)
    missing = [row["lda_source_person_id"] for row in person_rows if not row["has_dated_employment_evidence"]]
    receipt = {
        "schema_id": "staffer-network-lda-registrant-employment-receipt-v1",
        "status": "PASS" if not missing else "FAIL",
        "source_activity_rows": activity_count,
        "source_person_activity_edges": person_activity_count,
        "source_people": len(people),
        "person_rows": person_count,
        "employment_episode_rows": episode_count,
        "people_with_dated_employment_evidence": person_count - len(missing),
        "people_without_dated_employment_evidence": len(missing),
        "people_without_dated_employment_ids": missing[:100],
        "complete_lifetime_history_assertions": 0,
        "files": [
            {
                "role": "people",
                "path": people_path.name,
                "bytes": people_path.stat().st_size,
                "sha256": sha256_file(people_path),
            },
            {
                "role": "episodes",
                "path": episodes_path.name,
                "bytes": episodes_path.stat().st_size,
                "sha256": sha256_file(episodes_path),
            },
        ],
    }
    receipt_path = output_root / "lda_registrant_employment_receipt.json"
    receipt_path.write_bytes(canonical_bytes(receipt))
    connection.close()
    database_path.unlink()
    print(json.dumps(receipt, sort_keys=True))
    return 0 if receipt["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
