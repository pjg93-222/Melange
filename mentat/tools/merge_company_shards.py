"""Merge isolated Mentat company shards into one SQLite database.

Usage:
    python merge_company_shards.py TARGET \
      SHARD_DB::Company|Company [SHARD_DB::Company|Company ...]
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def table_columns(connection: sqlite3.Connection, schema: str, table: str) -> list[str]:
    return [
        row[1]
        for row in connection.execute(
            f"PRAGMA {quoted(schema)}.table_info({quoted(table)})"
        )
    ]


def placeholders(values: list[str]) -> str:
    return ",".join("?" for _ in values)


def merge_shard(
    connection: sqlite3.Connection,
    shard_index: int,
    shard_path: Path,
    companies: list[str],
) -> None:
    schema = f"shard_{shard_index}"
    connection.execute(
        f"ATTACH DATABASE ? AS {quoted(schema)}",
        (str(shard_path),),
    )
    try:
        for table in ("contributions", "corporate_giving"):
            main_columns = table_columns(connection, "main", table)
            shard_columns = table_columns(connection, schema, table)
            if main_columns != shard_columns:
                raise RuntimeError(f"{table} schema mismatch in {shard_path}")
            column_sql = ",".join(quoted(column) for column in main_columns)
            connection.execute(
                f"""
                INSERT OR IGNORE INTO main.{quoted(table)} ({column_sql})
                SELECT {column_sql}
                FROM {quoted(schema)}.{quoted(table)}
                WHERE company IN ({placeholders(companies)})
                """,
                companies,
            )

        progress_columns = [
            "company",
            "cycle",
            "variant_set",
            "last_page",
            "records_total",
            "updated_at",
        ]
        progress_sql = ",".join(quoted(column) for column in progress_columns)
        connection.execute(
            f"""
            INSERT INTO main.scrape_progress ({progress_sql})
            SELECT {progress_sql}
            FROM {quoted(schema)}.scrape_progress
            WHERE company IN ({placeholders(companies)}) AND 1
            ON CONFLICT(company, cycle, variant_set) DO UPDATE SET
              last_page=excluded.last_page,
              records_total=excluded.records_total,
              updated_at=excluded.updated_at
            """,
            companies,
        )

        connection.execute(
            f"""
            INSERT INTO main.canary_log
              (company, cycle, variant_set, page, check_name, passed, detail, checked_at)
            SELECT s.company, s.cycle, s.variant_set, s.page, s.check_name,
                   s.passed, s.detail, s.checked_at
            FROM {quoted(schema)}.canary_log AS s
            WHERE s.company IN ({placeholders(companies)})
              AND NOT EXISTS (
                SELECT 1
                FROM main.canary_log AS m
                WHERE m.company=s.company
                  AND m.cycle=s.cycle
                  AND m.variant_set=s.variant_set
                  AND m.page=s.page
                  AND m.check_name=s.check_name
                  AND COALESCE(m.detail, '')=COALESCE(s.detail, '')
              )
            """,
            companies,
        )
    finally:
        connection.execute(f"DETACH DATABASE {quoted(schema)}")


def main(arguments: list[str]) -> int:
    if len(arguments) < 2:
        raise SystemExit(__doc__)
    target = Path(arguments[0]).resolve()
    specifications: list[tuple[Path, list[str]]] = []
    for value in arguments[1:]:
        try:
            path_value, companies_value = value.split("::", 1)
        except ValueError as error:
            raise SystemExit(f"Invalid shard specification: {value}") from error
        companies = [
            company.strip()
            for company in companies_value.split("|")
            if company.strip()
        ]
        shard = Path(path_value).resolve()
        if not shard.is_file() or not companies:
            raise SystemExit(f"Invalid shard path or company list: {value}")
        specifications.append((shard, companies))

    connection = sqlite3.connect(target, timeout=30)
    try:
        connection.execute("PRAGMA busy_timeout=30000")
        for index, (shard, companies) in enumerate(specifications):
            with connection:
                merge_shard(connection, index, shard, companies)
        check = connection.execute("PRAGMA quick_check(1)").fetchone()[0]
        if check != "ok":
            raise RuntimeError(f"merged database quick_check failed: {check}")
        rows = connection.execute(
            """
            SELECT company, COUNT(*)
            FROM contributions
            GROUP BY company ORDER BY company
            """
        ).fetchall()
        print(f"quick_check={check}")
        for company, count in rows:
            print(f"{company}|{count}")
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
