"""Read-only PAC-activity differences between two preserved ledgers."""

import argparse
import json
import sqlite3
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("old", type=Path)
parser.add_argument("new", type=Path)
args = parser.parse_args()
old = args.old.resolve()
new = args.new.resolve()
db = sqlite3.connect(f"file:{old.as_posix()}?mode=ro", uri=True)
db.execute("ATTACH DATABASE ? AS newer", (f"file:{new.as_posix()}?mode=ro",))
rows = []
for source_id, before_text, after_text, source_text in db.execute(
    """
    SELECT old.source_id, old.payload_json, new.payload_json, source.payload_json
      FROM decisions AS old
      JOIN newer.decisions AS new USING (source_id)
      JOIN source_records AS source ON source.source_id = old.source_id
     WHERE CAST(json_extract(old.payload_json, '$.pac_activity_cents') AS INTEGER)
           <> CAST(json_extract(new.payload_json, '$.pac_activity_cents') AS INTEGER)
     ORDER BY old.source_id
    """
):
    before = json.loads(before_text)
    after = json.loads(after_text)
    source = json.loads(source_text)
    rows.append({
        "source_id": source_id,
        "before_pac_activity_cents": before["pac_activity_cents"],
        "after_pac_activity_cents": after["pac_activity_cents"],
        "before_status": before["status"],
        "after_status": after["status"],
        "after_reasons": after.get("reasons", []),
        "source": {key: source.get(key) for key in (
            "company", "contributor_name", "entity_type", "receipt_type_full",
            "memo_text", "contribution_receipt_amount", "contribution_receipt_date")},
    })
print(json.dumps(rows, indent=2))
