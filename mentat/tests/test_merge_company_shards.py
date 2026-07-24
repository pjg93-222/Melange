from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "tools"))
import merge_company_shards as merger  # noqa: E402


SCHEMA = """
CREATE TABLE contributions (
  sub_id TEXT PRIMARY KEY,
  company TEXT NOT NULL,
  matched_variant TEXT NOT NULL DEFAULT '',
  phase TEXT NOT NULL DEFAULT '',
  match_confidence TEXT,
  company_match_status TEXT NOT NULL DEFAULT 'accepted',
  company_match_reason TEXT,
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
            """
            INSERT INTO contributions (sub_id, company, amount)
            VALUES (?, ?, ?)
            """,
            (f"contribution-{suffix}", company, 100.0),
        )
        connection.execute(
            """
            INSERT INTO contributions (sub_id, company, amount)
            VALUES (?, ?, ?)
            """,
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


def seed_attribution(
    path: Path,
    *,
    sub_id: str,
    company: str,
    phase: str,
    amount: float = 100.0,
) -> None:
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            """
            INSERT INTO contributions (
              sub_id, company, matched_variant, phase, match_confidence,
              company_match_status, company_match_reason, amount
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sub_id,
                company,
                f"{company} variant",
                phase,
                f"{company} confidence",
                "accepted",
                f"{company} reason",
                amount,
            ),
        )


class MergeCompanyShardsTest(unittest.TestCase):
    def test_ten_shard_atomic_batch_matches_serial_reference(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mentat-ten-shard-") as temp:
            root = Path(temp)
            batched = root / "batched.db"
            serial = root / "serial.db"
            create_database(batched)
            create_database(serial)
            specifications: list[str] = []
            for index in range(10):
                company = f"Company {index:02d}"
                other = f"Other {index:02d}"
                shard = root / f"shard-{index:02d}.db"
                create_database(shard)
                seed_shard(shard, company, other, f"{index:02d}")
                specifications.append(f"{shard}::{company}")

            self.assertEqual(
                merger.main([str(batched), *reversed(specifications)]),
                0,
            )
            for specification in specifications:
                self.assertEqual(
                    merger.main([str(serial), specification]),
                    0,
                )

            batched_counts = {
                table: scalar(batched, f"SELECT COUNT(*) FROM {table}")
                for table in merger.REQUIRED_COLLECTOR_TABLES
            }
            serial_counts = {
                table: scalar(serial, f"SELECT COUNT(*) FROM {table}")
                for table in merger.REQUIRED_COLLECTOR_TABLES
            }
            batched_sub_ids = scalar(
                batched,
                "SELECT COUNT(DISTINCT sub_id) FROM contributions",
            )
            serial_sub_ids = scalar(
                serial,
                "SELECT COUNT(DISTINCT sub_id) FROM contributions",
            )

        self.assertEqual(batched_counts, serial_counts)
        self.assertEqual(batched_sub_ids, serial_sub_ids)
        self.assertEqual(batched_counts["contributions"], 10)
        self.assertEqual(batched_sub_ids, 10)

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

    def test_attribution_collision_uses_canonical_order_in_any_shard_order(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mentat-attribution-conflict-"
        ) as temp:
            root = Path(temp)
            first_target = root / "first.db"
            second_target = root / "second.db"
            alpha_shard = root / "a.db"
            zulu_shard = root / "z.db"
            for path in (
                first_target,
                second_target,
                alpha_shard,
                zulu_shard,
            ):
                create_database(path)
            seed_attribution(
                alpha_shard,
                sub_id="shared-sub-id",
                company="Alpha",
                phase="alpha-phase",
            )
            seed_attribution(
                zulu_shard,
                sub_id="shared-sub-id",
                company="Zulu",
                phase="zulu-phase",
            )
            company_order = '["Zulu", "Alpha"]'
            first_output = StringIO()
            with redirect_stdout(first_output):
                self.assertEqual(
                    merger.main(
                        [
                            str(first_target),
                            "--company-order-json",
                            company_order,
                            f"{alpha_shard}::Alpha",
                            f"{zulu_shard}::Zulu",
                        ]
                    ),
                    0,
                )
            second_output = StringIO()
            with redirect_stdout(second_output):
                self.assertEqual(
                    merger.main(
                        [
                            str(second_target),
                            "--company-order-json",
                            company_order,
                            f"{zulu_shard}::Zulu",
                            f"{alpha_shard}::Alpha",
                        ]
                    ),
                    0,
                )

            def merged_rows(path: Path) -> tuple[list[tuple[object, ...]], ...]:
                with closing(sqlite3.connect(path)) as connection:
                    contribution = list(
                        connection.execute(
                            """
                            SELECT sub_id, company, matched_variant, phase,
                                   match_confidence, company_match_status,
                                   company_match_reason, amount
                            FROM contributions
                            ORDER BY sub_id
                            """
                        )
                    )
                    conflicts = list(
                        connection.execute(
                            """
                            SELECT sub_id, stored_company, incoming_company,
                                   incoming_phase, created_at
                            FROM attribution_conflicts
                            ORDER BY sub_id, incoming_company, incoming_phase
                            """
                        )
                    )
                return contribution, conflicts

            first_rows = merged_rows(first_target)
            second_rows = merged_rows(second_target)
            self.assertEqual(first_rows, second_rows)
            self.assertEqual(first_target.read_bytes(), second_target.read_bytes())
            self.assertEqual(first_rows[0][0][1], "Zulu")
            self.assertEqual(
                first_rows[1],
                [
                    (
                        "shared-sub-id",
                        "Zulu",
                        "Alpha",
                        "alpha-phase",
                        merger.DETERMINISTIC_CONFLICT_TIMESTAMP,
                    )
                ],
            )
            self.assertIn(
                "attribution_conflicts_recorded=1",
                first_output.getvalue(),
            )
            self.assertEqual(
                first_output.getvalue().count(
                    "attribution_conflict key={'sub_id': 'shared-sub-id'}"
                ),
                1,
            )

    def test_cross_shard_raw_pk_conflict_fails_before_writes(self) -> None:
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
                    SET sub_id='contribution-A', amount=101
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

    def test_three_way_attribution_collision_records_each_loser(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="mentat-three-way-attribution-"
        ) as temp:
            root = Path(temp)
            target = root / "target.db"
            create_database(target)
            specifications: list[str] = []
            for path_name, company, phase in (
                ("alpha.db", "Alpha", "alpha-phase"),
                ("beta.db", "Beta", "beta-phase"),
                ("gamma.db", "Gamma", "gamma-phase"),
            ):
                shard = root / path_name
                create_database(shard)
                seed_attribution(
                    shard,
                    sub_id="three-way",
                    company=company,
                    phase=phase,
                )
                specifications.append(f"{shard}::{company}")

            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    merger.main(
                        [
                            str(target),
                            "--company-order-json",
                            '["Gamma", "Alpha", "Beta"]',
                            *reversed(specifications),
                        ]
                    ),
                    0,
                )
            self.assertEqual(
                scalar(
                    target,
                    "SELECT company FROM contributions WHERE sub_id='three-way'",
                ),
                "Gamma",
            )
            with closing(sqlite3.connect(target)) as connection:
                conflicts = list(
                    connection.execute(
                        """
                        SELECT stored_company, incoming_company, incoming_phase
                        FROM attribution_conflicts
                        WHERE sub_id='three-way'
                        ORDER BY incoming_company
                        """
                    )
                )
            self.assertEqual(
                conflicts,
                [
                    ("Gamma", "Alpha", "alpha-phase"),
                    ("Gamma", "Beta", "beta-phase"),
                ],
            )
            self.assertIn(
                "attribution_conflicts_recorded=2",
                output.getvalue(),
            )
            self.assertEqual(
                output.getvalue().count(
                    "attribution_conflict key={'sub_id': 'three-way'}"
                ),
                2,
            )

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
                    INSERT INTO contributions (sub_id, company, amount) VALUES
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
