from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
import merge_company_shards as merger  # noqa: E402


SCHEMA = """
CREATE TABLE contributions (
  sub_id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  amount REAL
);
CREATE TABLE corporate_giving (
  sub_id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  amount REAL
);
CREATE TABLE scrape_progress (
  company TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  variant_set TEXT NOT NULL,
  last_page INTEGER NOT NULL,
  records_total INTEGER NOT NULL,
  updated_at TEXT NOT NULL,
  PRIMARY KEY (company, cycle, variant_set)
);
CREATE TABLE api_work_progress (
  unit_id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  kind TEXT NOT NULL,
  last_page INTEGER NOT NULL DEFAULT -1,
  rows_seen INTEGER NOT NULL DEFAULT 0,
  records_total INTEGER,
  last_index TEXT,
  last_contribution_receipt_date TEXT,
  seen_keysets TEXT,
  fetched_complete INTEGER NOT NULL DEFAULT 0
    CHECK (fetched_complete IN (0,1)),
  stored_complete INTEGER NOT NULL DEFAULT 0
    CHECK (stored_complete IN (0,1)),
  updated_at TEXT NOT NULL
);
CREATE TABLE api_page_checkpoints (
  unit_id TEXT NOT NULL,
  page INTEGER NOT NULL,
  payload_json TEXT NOT NULL,
  PRIMARY KEY (unit_id, page)
);
CREATE TABLE observed_employers (
  cycle INTEGER NOT NULL,
  employer_string TEXT NOT NULL,
  n_rows INTEGER NOT NULL,
  PRIMARY KEY (cycle, employer_string)
);
CREATE TABLE bulk_candidates (
  cycle INTEGER NOT NULL,
  company TEXT NOT NULL,
  sub_id TEXT NOT NULL,
  amount REAL,
  PRIMARY KEY (company, cycle, sub_id)
);
CREATE TABLE review_queue_identity (
  review_id INTEGER PRIMARY KEY,
  seed_sub_id TEXT,
  candidate_sub_id TEXT,
  company TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  reason TEXT NOT NULL,
  UNIQUE (seed_sub_id, candidate_sub_id, company, cycle)
);
CREATE TABLE attribution_conflicts (
  sub_id TEXT NOT NULL,
  stored_company TEXT NOT NULL,
  incoming_company TEXT NOT NULL,
  incoming_phase TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (
    sub_id, stored_company, incoming_company, incoming_phase
  )
);
CREATE TABLE canary_log (
  canary_id INTEGER PRIMARY KEY,
  company TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  variant_set TEXT NOT NULL,
  page INTEGER NOT NULL,
  check_name TEXT NOT NULL,
  passed INTEGER NOT NULL,
  detail TEXT,
  checked_at TEXT NOT NULL
);
CREATE TABLE run_log (
  run_id TEXT NOT NULL,
  cycle INTEGER NOT NULL,
  status TEXT NOT NULL,
  PRIMARY KEY (run_id, cycle)
);
CREATE TABLE run_metrics (
  run_id TEXT NOT NULL,
  phase TEXT NOT NULL,
  rows_processed INTEGER NOT NULL,
  PRIMARY KEY (run_id, phase)
);
"""


def create_database(path: Path) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.executescript(SCHEMA)


def scalar(path: Path, sql: str, parameters: tuple[object, ...] = ()) -> object:
    with closing(sqlite3.connect(path)) as connection, connection:
        return connection.execute(sql, parameters).fetchone()[0]


def seed_shard(
    path: Path,
    company: str,
    other_company: str,
    suffix: str,
) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            "INSERT INTO contributions VALUES (?, ?, ?)",
            (f"contribution-{suffix}", company, 100.0),
        )
        connection.execute(
            "INSERT INTO contributions VALUES (?, ?, ?)",
            (f"unselected-{suffix}", other_company, 999.0),
        )
        connection.execute(
            "INSERT INTO corporate_giving VALUES (?, ?, ?)",
            (f"corporate-{suffix}", company, 200.0),
        )
        connection.execute(
            "INSERT INTO scrape_progress VALUES (?, 2026, 'P1', 9, 10, ?)",
            (company, f"2026-07-23T00:00:0{suffix}"),
        )
        connection.execute(
            """
            INSERT INTO api_work_progress VALUES (
              ?, ?, 2026, 'schedule_a', 4, 500, 500,
              'cursor', '2026-01-01', 'keys', 1, 0, ?
            )
            """,
            (
                f"unit-{suffix}",
                company,
                f"2026-07-23T00:00:0{suffix}",
            ),
        )
        connection.execute(
            "INSERT INTO api_page_checkpoints VALUES (?, 4, ?)",
            (f"unit-{suffix}", f'{{"company":"{company}"}}'),
        )
        connection.execute(
            "INSERT INTO observed_employers VALUES (2026, ?, 5)",
            (f"EMPLOYER-{suffix}",),
        )
        connection.execute(
            "INSERT INTO bulk_candidates VALUES (2026, ?, ?, 100)",
            (company, f"bulk-{suffix}"),
        )
        connection.execute(
            """
            INSERT INTO review_queue_identity
              (review_id, seed_sub_id, candidate_sub_id, company, cycle, reason)
            VALUES (1, ?, ?, ?, 2026, 'review')
            """,
            (f"seed-{suffix}", f"candidate-{suffix}", company),
        )
        connection.execute(
            """
            INSERT INTO attribution_conflicts VALUES
              (?, ?, ?, 'P1', ?)
            """,
            (
                f"conflict-{suffix}",
                company,
                other_company,
                f"2026-07-23T00:00:0{suffix}",
            ),
        )
        connection.execute(
            """
            INSERT INTO canary_log
              (canary_id, company, cycle, variant_set, page, check_name,
               passed, detail, checked_at)
            VALUES (1, ?, 2026, 'P1', 4, 'row_count', 1, 'ok', ?)
            """,
            (company, f"2026-07-23T00:00:0{suffix}"),
        )
        connection.execute(
            "INSERT INTO run_log VALUES (?, 2026, 'ok')",
            (f"run-{suffix}",),
        )
        connection.execute(
            "INSERT INTO run_metrics VALUES (?, 'collect', 500)",
            (f"run-{suffix}",),
        )


class MergeCompanyShardsTest(unittest.TestCase):
    def test_atomic_company_merge_and_idempotency(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mentat-shard-merge-") as temp:
            root = Path(temp)
            target = root / "target.db"
            shard_a = root / "a.db"
            shard_b = root / "b.db"
            for path in (target, shard_a, shard_b):
                create_database(path)

            with closing(sqlite3.connect(target)) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO scrape_progress
                    VALUES ('Alpha', 2026, 'P1', 1, 10, '2026-07-20')
                    """
                )
                connection.execute(
                    """
                    INSERT INTO api_work_progress VALUES (
                      'unit-A', 'Alpha', 2026, 'schedule_a', 1, 100, 500,
                      '', '', '', 0, 0, '2026-07-20'
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO api_page_checkpoints
                    VALUES ('unit-A', 1, '{"old":true}')
                    """
                )

            seed_shard(shard_a, "Alpha", "Beta", "A")
            seed_shard(shard_b, "Beta", "Alpha", "B")
            arguments = [
                str(target),
                f"{shard_b}::Beta",
                f"{shard_a}::Alpha",
            ]
            self.assertEqual(merger.main(arguments), 0)

            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM contributions"),
                2,
            )
            self.assertEqual(
                scalar(
                    target,
                    "SELECT COUNT(*) FROM contributions WHERE sub_id LIKE 'unselected-%'",
                ),
                0,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM corporate_giving"),
                2,
            )
            self.assertEqual(
                scalar(
                    target,
                    """
                    SELECT last_page FROM scrape_progress
                    WHERE company='Alpha' AND cycle=2026 AND variant_set='P1'
                    """,
                ),
                9,
            )
            self.assertEqual(
                scalar(
                    target,
                    """
                    SELECT payload_json FROM api_page_checkpoints
                    WHERE unit_id='unit-A' AND page=4
                    """,
                ),
                '{"company":"Alpha"}',
            )
            self.assertEqual(
                scalar(
                    target,
                    "SELECT COUNT(*) FROM api_page_checkpoints WHERE unit_id='unit-A'",
                ),
                1,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM review_queue_identity"),
                2,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM canary_log"),
                2,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM attribution_conflicts"),
                2,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM run_log"),
                2,
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM run_metrics"),
                2,
            )
            self.assertEqual(
                scalar(target, "PRAGMA quick_check"),
                "ok",
            )

            counts_before = {
                table: scalar(target, f"SELECT COUNT(*) FROM {table}")
                for table in merger.REQUIRED_COLLECTOR_TABLES
            }
            self.assertEqual(merger.main(arguments), 0)
            counts_after = {
                table: scalar(target, f"SELECT COUNT(*) FROM {table}")
                for table in merger.REQUIRED_COLLECTOR_TABLES
            }
            self.assertEqual(counts_after, counts_before)

    def test_cross_shard_pk_conflict_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mentat-shard-conflict-") as temp:
            root = Path(temp)
            target = root / "target.db"
            shard_a = root / "a.db"
            shard_b = root / "b.db"
            for path in (target, shard_a, shard_b):
                create_database(path)

            seed_shard(shard_a, "Alpha", "Beta", "A")
            seed_shard(shard_b, "Beta", "Alpha", "B")
            with closing(sqlite3.connect(shard_b)) as connection, connection:
                connection.execute(
                    """
                    UPDATE contributions
                    SET sub_id='contribution-A'
                    WHERE sub_id='contribution-B'
                    """
                )

            with self.assertRaisesRegex(
                RuntimeError,
                "Non-identical primary-key collision in contributions",
            ):
                merger.main(
                    [
                        str(target),
                        f"{shard_a}::Alpha",
                        f"{shard_b}::Beta",
                    ]
                )

            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM contributions"),
                0,
            )
            self.assertEqual(scalar(target, "PRAGMA quick_check"), "ok")

    def test_target_pk_conflict_fails_before_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mentat-target-conflict-") as temp:
            root = Path(temp)
            target = root / "target.db"
            shard = root / "shard.db"
            create_database(target)
            create_database(shard)
            seed_shard(shard, "Alpha", "Beta", "A")
            with closing(sqlite3.connect(target)) as connection, connection:
                connection.execute(
                    """
                    INSERT INTO contributions VALUES
                      ('contribution-A', 'Different Company', 999)
                    """
                )

            with self.assertRaisesRegex(
                RuntimeError,
                "Non-identical primary-key collision in contributions",
            ):
                merger.main([str(target), f"{shard}::Alpha"])

            self.assertEqual(
                scalar(
                    target,
                    """
                    SELECT company || ':' || amount
                    FROM contributions
                    WHERE sub_id='contribution-A'
                    """,
                ),
                "Different Company:999.0",
            )
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM corporate_giving"),
                0,
            )
            self.assertEqual(scalar(target, "PRAGMA quick_check"), "ok")

    def test_schema_mismatch_fails_without_writes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mentat-shard-mismatch-") as temp:
            root = Path(temp)
            target = root / "target.db"
            shard = root / "bad.db"
            create_database(target)
            create_database(shard)
            with closing(sqlite3.connect(shard)) as connection, connection:
                connection.execute(
                    "ALTER TABLE contributions ADD COLUMN unexpected TEXT"
                )
                connection.execute(
                    "INSERT INTO contributions (sub_id, company, amount) VALUES ('x', 'Alpha', 1)"
                )
            with self.assertRaisesRegex(RuntimeError, "schema/uniqueness mismatch"):
                merger.main([str(target), f"{shard}::Alpha"])
            self.assertEqual(
                scalar(target, "SELECT COUNT(*) FROM contributions"),
                0,
            )
            self.assertEqual(scalar(target, "PRAGMA quick_check"), "ok")


if __name__ == "__main__":
    unittest.main()
