"""Read-only logical payload sizes for a cross-reference ledger."""

import argparse
import json
import sqlite3
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("ledger", type=Path)
args = parser.parse_args()
path = args.ledger.resolve()
db = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
result = []
for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    columns = [row[1] for row in db.execute(f"PRAGMA table_info({name})")]
    expression = "SUM(LENGTH(payload_json))" if "payload_json" in columns else "0"
    count, total = db.execute(f"SELECT COUNT(*), {expression} FROM {name}").fetchone()
    result.append({"table": name, "rows": count, "payload_bytes": total or 0})
print(json.dumps(result, indent=2))
