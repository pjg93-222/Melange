"""Safely merge isolated Mentat company shards into one SQLite database.

Usage:
    python merge_company_shards.py TARGET \
      "SHARD_DB::Company|Company" ["SHARD_DB::Company|Company" ...]

TARGET must already exist. Shards are attached read-only, schemas and
quick_check are verified before any write, and the entire merge is committed
as one transaction. A company may be assigned to exactly one shard.
"""

from __future__ import annotations

import sqlite3
import sys
from collections import defaultdict
from contextlib import closing
from pathlib import Path
from typing import Iterable, Sequence


# Tables populated or updated by collection. Static roster/register tables
# (companies, categories, leadership, trade, executives, etc.) remain owned by
# the initialized target database and are deliberately not copied from shards.
REQUIRED_COLLECTOR_TABLES = (
    "contributions",
    "corporate_giving",
    "scrape_progress",
    "api_work_progress",
    "api_page_checkpoints",
    "observed_employers",
    "bulk_candidates",
    "review_queue_identity",
    "attribution_conflicts",
    "canary_log",
    "run_log",
    "run_metrics",
)

COMPANY_TABLES = {
    "contributions": "company",
    "corporate_giving": "company",
    "scrape_progress": "company",
    "api_work_progress": "company",
    "bulk_candidates": "company",
    "review_queue_identity": "company",
    "canary_log": "company",
}

GLOBAL_APPEND_TABLES = (
    "observed_employers",
    "run_log",
    "run_metrics",
)

# These rows retain their source primary keys during the merge. Any duplicate
# key must therefore describe the exact same logical row. Progress/checkpoint
# tables are excluded because their differing versions are resolved by the
# explicit winner logic below; review/canary surrogate IDs are not copied.
EXACT_PARITY_TABLES = (
    "contributions",
    "corporate_giving",
    "bulk_candidates",
    "attribution_conflicts",
    *GLOBAL_APPEND_TABLES,
)


def quoted(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def placeholders(values: Sequence[object]) -> str:
    if not values:
        raise ValueError("SQL placeholder list cannot be empty")
    return ",".join("?" for _ in values)


def table_info(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> list[tuple[object, ...]]:
    return list(
        connection.execute(
            f"PRAGMA {quoted(schema)}.table_info({quoted(table)})"
        )
    )


def table_columns(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> list[str]:
    return [str(row[1]) for row in table_info(connection, schema, table)]


def primary_key_columns(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> list[str]:
    rows = table_info(connection, schema, table)
    return [
        str(row[1])
        for row in sorted(
            (row for row in rows if int(row[5]) > 0),
            key=lambda row: int(row[5]),
        )
    ]


def unique_signatures(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> set[tuple[str, int, tuple[str, ...]]]:
    signatures: set[tuple[str, int, tuple[str, ...]]] = set()
    indexes = list(
        connection.execute(
            f"PRAGMA {quoted(schema)}.index_list({quoted(table)})"
        )
    )
    for row in indexes:
        # seq, name, unique, origin, partial
        if int(row[2]) != 1:
            continue
        index_name = str(row[1])
        columns = tuple(
            str(item[2])
            for item in connection.execute(
                f"PRAGMA {quoted(schema)}.index_info({quoted(index_name)})"
            )
        )
        signatures.add((str(row[3]), int(row[4]), columns))
    return signatures


def schema_signature(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> tuple[tuple[tuple[object, ...], ...], frozenset[tuple[str, int, tuple[str, ...]]]]:
    columns = tuple(
        (
            str(row[1]),
            str(row[2]).upper(),
            int(row[3]),
            None if row[4] is None else str(row[4]),
            int(row[5]),
        )
        for row in table_info(connection, schema, table)
    )
    return columns, frozenset(unique_signatures(connection, schema, table))


def quick_check(connection: sqlite3.Connection, schema: str) -> None:
    rows = [
        str(row[0])
        for row in connection.execute(
            f"PRAGMA {quoted(schema)}.quick_check"
        )
    ]
    if rows != ["ok"]:
        raise RuntimeError(
            f"{schema} quick_check failed: {'; '.join(rows) or 'no result'}"
        )


def ensure_schema_compatible(
    connection: sqlite3.Connection,
    schema: str,
    shard_path: Path,
) -> None:
    for table in REQUIRED_COLLECTOR_TABLES:
        main_signature = schema_signature(connection, "main", table)
        shard_signature = schema_signature(connection, schema, table)
        if not main_signature[0]:
            raise RuntimeError(f"target is missing required table {table}")
        if not shard_signature[0]:
            raise RuntimeError(
                f"shard {shard_path} is missing required table {table}"
            )
        if shard_signature != main_signature:
            raise RuntimeError(
                f"{table} schema/uniqueness mismatch in {shard_path}"
            )


def null_safe_equal(
    left_alias: str,
    right_alias: str,
    columns: Iterable[str],
) -> str:
    return " AND ".join(
        f"{left_alias}.{quoted(column)} IS {right_alias}.{quoted(column)}"
        for column in columns
    )


def merge_selection(
    table: str,
    alias: str,
    companies: Sequence[str] | None,
) -> tuple[str, tuple[object, ...]]:
    if companies is None or table in GLOBAL_APPEND_TABLES:
        return "1", ()
    if table in COMPANY_TABLES:
        company_column = COMPANY_TABLES[table]
        return (
            f"{alias}.{quoted(company_column)} IN "
            f"({placeholders(companies)})",
            tuple(companies),
        )
    if table == "attribution_conflicts":
        company_sql = placeholders(companies)
        return (
            f"({alias}.stored_company IN ({company_sql}) "
            f"OR {alias}.incoming_company IN ({company_sql}))",
            tuple(companies) + tuple(companies),
        )
    raise ValueError(f"No exact-parity merge selection for {table}")


def audit_exact_pk_pair(
    connection: sqlite3.Connection,
    table: str,
    left_schema: str,
    left_label: str,
    left_companies: Sequence[str] | None,
    right_schema: str,
    right_label: str,
    right_companies: Sequence[str] | None,
) -> None:
    columns = table_columns(connection, "main", table)
    pk_columns = primary_key_columns(connection, "main", table)
    if not pk_columns:
        raise RuntimeError(f"{table} has no primary key")
    key_match = null_safe_equal("l", "r", pk_columns)
    row_match = null_safe_equal("l", "r", columns)
    left_where, left_parameters = merge_selection(
        table,
        "l",
        left_companies,
    )
    right_where, right_parameters = merge_selection(
        table,
        "r",
        right_companies,
    )
    selected = ",".join(
        [
            *(f"l.{quoted(column)}" for column in columns),
            *(f"r.{quoted(column)}" for column in columns),
        ]
    )
    with closing(
        connection.execute(
            f"""
            SELECT {selected}
            FROM {quoted(left_schema)}.{quoted(table)} AS l
            JOIN {quoted(right_schema)}.{quoted(table)} AS r
              ON {key_match}
            WHERE {left_where}
              AND {right_where}
              AND NOT ({row_match})
            LIMIT 1
            """,
            left_parameters + right_parameters,
        )
    ) as cursor:
        collision = cursor.fetchone()
    if collision is None:
        return

    column_count = len(columns)
    left_values = collision[:column_count]
    right_values = collision[column_count:]
    key = {
        column: left_values[columns.index(column)]
        for column in pk_columns
    }
    differing = [
        column
        for index, column in enumerate(columns)
        if left_values[index] != right_values[index]
    ]
    raise RuntimeError(
        f"Non-identical primary-key collision in {table}: "
        f"{left_label} vs {right_label}; key={key!r}; "
        f"differing_columns={differing!r}"
    )


def audit_exact_pk_collisions(
    connection: sqlite3.Connection,
    specifications: Sequence[tuple[Path, tuple[str, ...]]],
) -> None:
    sources: list[tuple[str, str, Sequence[str] | None]] = [
        ("main", "target", None)
    ]
    sources.extend(
        (
            f"shard_{index}",
            str(shard),
            companies,
        )
        for index, (shard, companies) in enumerate(specifications)
    )
    for table in EXACT_PARITY_TABLES:
        for right_index in range(1, len(sources)):
            right_schema, right_label, right_companies = sources[right_index]
            for left_index in range(right_index):
                left_schema, left_label, left_companies = sources[left_index]
                audit_exact_pk_pair(
                    connection,
                    table,
                    left_schema,
                    left_label,
                    left_companies,
                    right_schema,
                    right_label,
                    right_companies,
                )


def insert_or_ignore(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
    where_sql: str = "1",
    parameters: Sequence[object] = (),
    columns: Sequence[str] | None = None,
) -> int:
    selected_columns = list(columns) if columns is not None else table_columns(
        connection,
        "main",
        table,
    )
    column_sql = ",".join(quoted(column) for column in selected_columns)
    connection.execute(
        f"""
        INSERT OR IGNORE INTO main.{quoted(table)} ({column_sql})
        SELECT {column_sql}
        FROM {quoted(schema)}.{quoted(table)} AS s
        WHERE {where_sql}
        """,
        tuple(parameters),
    )
    return int(connection.execute("SELECT changes()").fetchone()[0])


def merge_company_fact_table(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
    companies: Sequence[str],
) -> tuple[int, int]:
    company_column = COMPANY_TABLES[table]
    where = (
        f"s.{quoted(company_column)} IN ({placeholders(companies)})"
    )
    pk_columns = primary_key_columns(connection, "main", table)
    if not pk_columns:
        raise RuntimeError(f"{table} has no primary key")
    pk_match = null_safe_equal("m", "s", pk_columns)
    ignored_existing = int(
        connection.execute(
            f"""
            SELECT COUNT(*)
            FROM {quoted(schema)}.{quoted(table)} AS s
            WHERE {where}
              AND EXISTS (
                SELECT 1 FROM main.{quoted(table)} AS m
                WHERE {pk_match}
              )
            """,
            tuple(companies),
        ).fetchone()[0]
    )
    inserted = insert_or_ignore(
        connection,
        schema,
        table,
        where,
        companies,
    )
    return inserted, ignored_existing


def merge_scrape_progress(
    connection: sqlite3.Connection,
    schema: str,
    companies: Sequence[str],
) -> int:
    columns = table_columns(connection, "main", "scrape_progress")
    column_sql = ",".join(quoted(column) for column in columns)
    connection.execute(
        f"""
        INSERT INTO main.scrape_progress ({column_sql})
        SELECT {column_sql}
        FROM {quoted(schema)}.scrape_progress AS s
        WHERE s.company IN ({placeholders(companies)}) AND 1
        ON CONFLICT(company, cycle, variant_set) DO UPDATE SET
          last_page=excluded.last_page,
          records_total=excluded.records_total,
          updated_at=excluded.updated_at
        WHERE excluded.last_page > scrape_progress.last_page
           OR (
             excluded.last_page = scrape_progress.last_page
             AND excluded.updated_at > scrape_progress.updated_at
           )
        """,
        tuple(companies),
    )
    return int(connection.execute("SELECT changes()").fetchone()[0])


def merge_api_progress(
    connection: sqlite3.Connection,
    schema: str,
    shard_index: int,
    companies: Sequence[str],
) -> tuple[int, int]:
    unit_stage = f"_mentat_merge_units_{shard_index}"
    connection.execute(
        f"CREATE TEMP TABLE {quoted(unit_stage)} (unit_id TEXT PRIMARY KEY)"
    )
    try:
        connection.execute(
            f"""
            INSERT INTO temp.{quoted(unit_stage)} (unit_id)
            SELECT s.unit_id
            FROM {quoted(schema)}.api_work_progress AS s
            LEFT JOIN main.api_work_progress AS m
              ON m.unit_id=s.unit_id
            WHERE s.company IN ({placeholders(companies)})
              AND (
                m.unit_id IS NULL
                OR s.stored_complete > m.stored_complete
                OR (
                  s.stored_complete = m.stored_complete
                  AND s.fetched_complete > m.fetched_complete
                )
                OR (
                  s.stored_complete = m.stored_complete
                  AND s.fetched_complete = m.fetched_complete
                  AND s.last_page > m.last_page
                )
                OR (
                  s.stored_complete = m.stored_complete
                  AND s.fetched_complete = m.fetched_complete
                  AND s.last_page = m.last_page
                  AND s.rows_seen > m.rows_seen
                )
                OR (
                  s.stored_complete = m.stored_complete
                  AND s.fetched_complete = m.fetched_complete
                  AND s.last_page = m.last_page
                  AND s.rows_seen = m.rows_seen
                  AND s.updated_at > m.updated_at
                )
              )
            """,
            tuple(companies),
        )
        selected_units = int(
            connection.execute(
                f"SELECT COUNT(*) FROM temp.{quoted(unit_stage)}"
            ).fetchone()[0]
        )
        if not selected_units:
            return 0, 0

        connection.execute(
            f"""
            DELETE FROM main.api_page_checkpoints
            WHERE unit_id IN (
              SELECT unit_id FROM temp.{quoted(unit_stage)}
            )
            """
        )
        checkpoint_columns = table_columns(
            connection,
            "main",
            "api_page_checkpoints",
        )
        checkpoint_sql = ",".join(
            quoted(column) for column in checkpoint_columns
        )
        connection.execute(
            f"""
            INSERT INTO main.api_page_checkpoints ({checkpoint_sql})
            SELECT {checkpoint_sql}
            FROM {quoted(schema)}.api_page_checkpoints AS p
            WHERE p.unit_id IN (
              SELECT unit_id FROM temp.{quoted(unit_stage)}
            )
            """
        )
        checkpoint_rows = int(
            connection.execute("SELECT changes()").fetchone()[0]
        )

        progress_columns = table_columns(
            connection,
            "main",
            "api_work_progress",
        )
        progress_sql = ",".join(
            quoted(column) for column in progress_columns
        )
        update_columns = [
            column for column in progress_columns if column != "unit_id"
        ]
        update_sql = ",".join(
            f"{quoted(column)}=excluded.{quoted(column)}"
            for column in update_columns
        )
        connection.execute(
            f"""
            INSERT INTO main.api_work_progress ({progress_sql})
            SELECT {progress_sql}
            FROM {quoted(schema)}.api_work_progress AS s
            WHERE s.unit_id IN (
              SELECT unit_id FROM temp.{quoted(unit_stage)}
            ) AND 1
            ON CONFLICT(unit_id) DO UPDATE SET {update_sql}
            """
        )
        progress_rows = int(
            connection.execute("SELECT changes()").fetchone()[0]
        )
        return progress_rows, checkpoint_rows
    finally:
        connection.execute(f"DROP TABLE temp.{quoted(unit_stage)}")


def merge_review_queue(
    connection: sqlite3.Connection,
    schema: str,
    companies: Sequence[str],
) -> int:
    columns = [
        column
        for column in table_columns(
            connection,
            "main",
            "review_queue_identity",
        )
        if column != "review_id"
    ]
    return insert_or_ignore(
        connection,
        schema,
        "review_queue_identity",
        f"s.company IN ({placeholders(companies)})",
        companies,
        columns,
    )


def merge_canary_log(
    connection: sqlite3.Connection,
    schema: str,
    companies: Sequence[str],
) -> int:
    columns = [
        column
        for column in table_columns(connection, "main", "canary_log")
        if column != "canary_id"
    ]
    column_sql = ",".join(quoted(column) for column in columns)
    natural_match = null_safe_equal("m", "s", columns)
    connection.execute(
        f"""
        INSERT INTO main.canary_log ({column_sql})
        SELECT {column_sql}
        FROM {quoted(schema)}.canary_log AS s
        WHERE s.company IN ({placeholders(companies)})
          AND NOT EXISTS (
            SELECT 1 FROM main.canary_log AS m
            WHERE {natural_match}
          )
        ORDER BY s.company, s.cycle, s.variant_set, s.page,
                 s.check_name, s.checked_at, s.canary_id
        """,
        tuple(companies),
    )
    return int(connection.execute("SELECT changes()").fetchone()[0])


def merge_attribution_conflicts(
    connection: sqlite3.Connection,
    schema: str,
    companies: Sequence[str],
) -> int:
    company_sql = placeholders(companies)
    return insert_or_ignore(
        connection,
        schema,
        "attribution_conflicts",
        (
            f"s.stored_company IN ({company_sql}) "
            f"OR s.incoming_company IN ({company_sql})"
        ),
        tuple(companies) + tuple(companies),
    )


def merge_global_table(
    connection: sqlite3.Connection,
    schema: str,
    table: str,
) -> int:
    # These tables have declared PK/UNIQUE constraints. INSERT OR IGNORE
    # therefore preserves the target's existing row for a cloned baseline and
    # adds only genuinely new shard records.
    return insert_or_ignore(connection, schema, table)


def merge_shard(
    connection: sqlite3.Connection,
    shard_index: int,
    schema: str,
    shard_path: Path,
    companies: Sequence[str],
) -> dict[str, int]:
    stats: dict[str, int] = {}
    for table in (
        "contributions",
        "corporate_giving",
        "bulk_candidates",
    ):
        inserted, existing = merge_company_fact_table(
            connection,
            schema,
            table,
            companies,
        )
        stats[f"{table}_inserted"] = inserted
        stats[f"{table}_pk_existing"] = existing

    stats["scrape_progress_changed"] = merge_scrape_progress(
        connection,
        schema,
        companies,
    )
    (
        stats["api_work_progress_changed"],
        stats["api_page_checkpoints_replaced"],
    ) = merge_api_progress(
        connection,
        schema,
        shard_index,
        companies,
    )
    stats["review_queue_identity_inserted"] = merge_review_queue(
        connection,
        schema,
        companies,
    )
    stats["attribution_conflicts_inserted"] = merge_attribution_conflicts(
        connection,
        schema,
        companies,
    )
    stats["canary_log_inserted"] = merge_canary_log(
        connection,
        schema,
        companies,
    )
    for table in GLOBAL_APPEND_TABLES:
        stats[f"{table}_inserted"] = merge_global_table(
            connection,
            schema,
            table,
        )
    return stats


def parse_specifications(
    values: Sequence[str],
    target: Path,
) -> list[tuple[Path, tuple[str, ...]]]:
    grouped: dict[Path, set[str]] = defaultdict(set)
    company_owner: dict[str, Path] = {}
    for value in values:
        try:
            path_value, companies_value = value.split("::", 1)
        except ValueError as error:
            raise SystemExit(f"Invalid shard specification: {value}") from error
        shard = Path(path_value).resolve()
        companies = {
            company.strip()
            for company in companies_value.split("|")
            if company.strip()
        }
        if not shard.is_file() or not companies:
            raise SystemExit(f"Invalid shard path or company list: {value}")
        if shard == target:
            raise SystemExit("A shard path cannot be the target database")
        for company in companies:
            previous = company_owner.get(company)
            if previous is not None and previous != shard:
                raise SystemExit(
                    f"Company {company!r} is assigned to both "
                    f"{previous} and {shard}"
                )
            company_owner[company] = shard
        grouped[shard].update(companies)

    specifications = [
        (path, tuple(sorted(companies, key=lambda value: (value.upper(), value))))
        for path, companies in grouped.items()
    ]
    specifications.sort(key=lambda item: str(item[0]).lower())
    if len(specifications) > 10:
        raise SystemExit(
            "SQLite supports at most 10 attached shard databases per atomic merge"
        )
    return specifications


def target_connection(target: Path) -> sqlite3.Connection:
    if not target.is_file():
        raise SystemExit(f"Target database does not exist: {target}")
    connection = sqlite3.connect(
        target.as_uri() + "?mode=rw",
        timeout=60,
        isolation_level=None,
        uri=True,
    )
    connection.execute("PRAGMA busy_timeout=60000")
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def main(arguments: Sequence[str]) -> int:
    if len(arguments) < 2:
        raise SystemExit(__doc__)
    target = Path(arguments[0]).resolve()
    specifications = parse_specifications(arguments[1:], target)
    connection = target_connection(target)
    attached: list[str] = []
    all_stats: list[tuple[Path, tuple[str, ...], dict[str, int]]] = []
    try:
        quick_check(connection, "main")
        for index, (shard, companies) in enumerate(specifications):
            schema = f"shard_{index}"
            shard_uri = shard.as_uri() + "?mode=ro"
            connection.execute(
                f"ATTACH DATABASE ? AS {quoted(schema)}",
                (shard_uri,),
            )
            attached.append(schema)
            quick_check(connection, schema)
            ensure_schema_compatible(connection, schema, shard)

        # Fail before BEGIN IMMEDIATE or any target write if INSERT OR IGNORE
        # would otherwise make a non-identical duplicate path-order dependent.
        audit_exact_pk_collisions(connection, specifications)

        connection.execute("BEGIN IMMEDIATE")
        try:
            for index, (shard, companies) in enumerate(specifications):
                schema = f"shard_{index}"
                stats = merge_shard(
                    connection,
                    index,
                    schema,
                    shard,
                    companies,
                )
                all_stats.append((shard, companies, stats))
            quick_check(connection, "main")
            connection.execute("COMMIT")
        except BaseException:
            connection.execute("ROLLBACK")
            raise

        # Validate committed bytes, not just the transaction view.
        quick_check(connection, "main")
        print("quick_check=ok")
        for shard, companies, stats in all_stats:
            print(
                "shard="
                + str(shard)
                + " companies="
                + "|".join(companies)
            )
            for name in sorted(stats):
                print(f"  {name}={stats[name]}")
    finally:
        for schema in reversed(attached):
            try:
                connection.execute(f"DETACH DATABASE {quoted(schema)}")
            except sqlite3.Error:
                pass
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
