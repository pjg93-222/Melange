"""Exercise actual dirty-page spill and hot-journal recovery on a disposable DB."""
import contextlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "mentat/tools"))
import api_company_cycle_fanout as fanout
import merge_company_shards as merger

with tempfile.TemporaryDirectory(prefix="mentat-hot-journal-") as temporary:
    root = Path(temporary)
    target, ready = root / "source.db", root / "ready"
    with contextlib.closing(sqlite3.connect(target)) as connection, connection:
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("CREATE TABLE records(id INTEGER PRIMARY KEY, payload BLOB)")
        connection.executemany("INSERT INTO records VALUES (?,zeroblob(4096))", [(i,) for i in range(512)])
    baseline = merger.file_sha256(target)
    code = """import sqlite3,sys,time
from pathlib import Path
c=sqlite3.connect(sys.argv[1], isolation_level=None)
c.execute('PRAGMA cache_size=5')
c.execute('PRAGMA cache_spill=ON')
c.execute('BEGIN IMMEDIATE')
c.execute('UPDATE records SET payload=randomblob(4096)')
Path(sys.argv[2]).write_text('spilled')
time.sleep(60)
"""
    process = subprocess.Popen([sys.executable, "-c", code, str(target), str(ready)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 15
        while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        assert ready.exists(), "child did not reach spill boundary"
    finally:
        process.kill()
        output, error = process.communicate(timeout=10)
    before = merger.file_sha256(target)
    assert before != baseline, "fixture did not spill dirty pages"
    journal_bytes = Path(str(target) + "-journal").stat().st_size
    fanout.settle_source_journals(target)
    after_helper = merger.file_sha256(target)
    with contextlib.closing(sqlite3.connect(target)) as connection:
        assert connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
    after_sqlite_read = merger.file_sha256(target)
    assert after_sqlite_read == baseline, "SQLite rollback did not restore exact original bytes"
    result = {"passed": after_helper == baseline, "dirty_pages_spilled": True, "journal_bytes": journal_bytes, "baseline_sha256": baseline, "post_kill_sha256": before, "after_recovery_helper_sha256": after_helper, "after_sqlite_read_sha256": after_sqlite_read}
    Path(__file__).with_name("hot-journal-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    assert result["passed"], "recovery helper left hot journal unresolved before fingerprint"
