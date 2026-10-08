"""Compare small/batched merges on disposable copies of the verified pilot."""
import contextlib
import io
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mentat" / "tools"))
import merge_company_shards as merger

prior = json.loads((ROOT / "outputs/mentat-pilot-integration-20260927/final-verification.json").read_text())
pilot = next(item for item in prior["pilot_files"] if item["path"].endswith("mentat.db"))
source = Path(pilot["path"])
assert merger.file_sha256(source) == pilot["sha256"]
assert not Path(str(source) + "-wal").exists() or Path(str(source) + "-wal").stat().st_size == 0

with tempfile.TemporaryDirectory(prefix="mentat-production-schema-") as temporary:
    root = Path(temporary)
    direct, batched, expected_state = root / "direct.db", root / "batched.db", root / "expected.db"
    for path in (direct, batched, expected_state):
        shutil.copy2(source, path)
    with contextlib.closing(sqlite3.connect(direct)) as connection:
        company = connection.execute("SELECT company FROM contributions LIMIT 1").fetchone()[0]
        tables = [row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        before_counts = {table: connection.execute(f"SELECT count(*) FROM {merger.quoted(table)}").fetchone()[0] for table in tables}
    specs = []
    for index, selected in enumerate((company, "Recovery Fixture B", "Recovery Fixture C")):
        shard = root / f"shard-{index}.db"
        shutil.copy2(source, shard)
        with contextlib.closing(sqlite3.connect(shard)) as connection, connection:
            for table in ("contributions", "corporate_giving"):
                columns = [row[1] for row in connection.execute(f"PRAGMA table_info({table})")]
                template = dict(zip(columns, connection.execute(f"SELECT * FROM {table} LIMIT 1").fetchone()))
                template.update(sub_id=f"recovery-fixture-{table}-{index}", company=selected)
                connection.execute(
                    f"INSERT INTO {table} ({','.join(merger.quoted(c) for c in columns)}) VALUES ({','.join('?' for _ in columns)})",
                    [template[column] for column in columns],
                )
                with contextlib.closing(sqlite3.connect(expected_state)) as expected_connection, expected_connection:
                    expected_connection.execute(
                        f"INSERT INTO {table} ({','.join(merger.quoted(c) for c in columns)}) VALUES ({','.join('?' for _ in columns)})",
                        [template[column] for column in columns],
                    )
        specs.append(f"{shard}::{selected}")
    logs = {}
    results = {}
    for label, target, batch_limit in (("direct", direct, "10"), ("batched", batched, "2")):
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            assert merger.main([str(target), "--expected-target-sha256", merger.file_sha256(target), "--merge-batch-limit", batch_limit, *specs]) == 0
        logs[label] = capture.getvalue()
        with contextlib.closing(sqlite3.connect(target)) as connection:
            results[label] = {
                "logical_sha256": merger.logical_database_sha256(connection),
                "quick_check": connection.execute("PRAGMA quick_check").fetchone()[0],
                "table_counts": {table: connection.execute(f"SELECT count(*) FROM {merger.quoted(table)}").fetchone()[0] for table in tables},
            }
    assert results["direct"] == results["batched"], results
    with contextlib.closing(sqlite3.connect(expected_state)) as expected_connection:
        assert results["batched"]["logical_sha256"] == merger.logical_database_sha256(expected_connection)
    for table, count in before_counts.items():
        expected = count + (3 if table in ("contributions", "corporate_giving") else 0)
        assert results["batched"]["table_counts"][table] == expected, (table, count, results)

assert merger.file_sha256(source) == pilot["sha256"]
report = {"passed": True, "live_pilot_unchanged": True, "source_sha256": pilot["sha256"], "result": results["batched"], "checks": ["direct and batched full typed logical state equal", "both merge results equal independently constructed expected database", "all production schema tables and baseline rows preserved", "three synthetic employee and three corporate records added", "baseline row counts preserved", "SQLite quick_check ok"]}
destination = Path(__file__).with_name("real-schema-verification.json")
destination.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
Path(__file__).with_name("real-schema-merge.log").write_text(json.dumps(logs, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
