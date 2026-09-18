"""D5 figure: probable-duplicate dollars inside observed_filing_versions_unresolved.

Usage: python dup_versions.py <run_dir>
For every review item with that reason (one per group of same committee /
transaction id / company / donor / date), the counted dollars beyond the first
row of the group are the probable duplicate. Read-only.
"""
import json, sqlite3, sys

run = sys.argv[1]
con = sqlite3.connect("file:" + run + r"\ledger.sqlite?mode=ro", uri=True)
groups = []
for (pj,) in con.execute("select payload_json from review_queue"):
    o = json.loads(pj)
    if o["reason"] == "observed_filing_versions_unresolved":
        groups.append(o["source_ids"])
ids = sorted({s for g in groups for s in g})
counted = {}
for i in range(0, len(ids), 900):
    chunk = ids[i:i + 900]
    for sid, pj in con.execute("select source_id, payload_json from decisions where source_id in (%s)" % ",".join("?" * len(chunk)), chunk):
        d = json.loads(pj)
        counted[sid] = (int(d["counted_cents"]), int(d["pac_activity_cents"]), int(d["amount_cents"]))
gross = sum(abs(counted[s][2]) for s in ids)
dup = 0
identical = 0
for g in groups:
    amounts = [counted[s][2] for s in g]
    if len(set(amounts)) == 1:
        identical += 1
    dup += sum(counted[s][0] + counted[s][1] for s in sorted(g)[1:])
print(f"groups={len(groups)} rows={len(ids)} gross=${gross/100:,.2f} groups_with_identical_amounts={identical} probable_duplicate_counted=${dup/100:,.2f}")
