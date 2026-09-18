"""Trace the rows a BEFORE run held under company_attribution_unresolved into
their AFTER-run verdicts. Usage: python trace_held.py <before_run_dir> <after_run_dir>
Read-only. Prints rows / gross / counted per verdict and per attribution status."""
import json, sqlite3, sys
from collections import defaultdict

before, after = sys.argv[1], sys.argv[2]
b = sqlite3.connect("file:" + before + r"\ledger.sqlite?mode=ro", uri=True)
held = set()
for (pj,) in b.execute("select payload_json from review_queue"):
    o = json.loads(pj)
    if o["reason"] == "company_attribution_unresolved":
        held.update(o["source_ids"])
print("before held rows:", len(held))
a = sqlite3.connect("file:" + after + r"\ledger.sqlite?mode=ro", uri=True)
verdict = defaultdict(lambda: dict(rows=0, gross=0, counted=0, pac=0))
status = defaultdict(lambda: dict(rows=0, gross=0, counted=0, pac=0))
seen = 0
for sid, pj in a.execute("select source_id, payload_json from decisions"):
    if sid not in held:
        continue
    seen += 1
    d = json.loads(pj)
    r = set(d["reasons"])
    v = ("contradicted" if "attribution_contradicted_by_text" in r else
         "named" if "company_named_unverified" in r else
         "unverified" if "company_attribution_unverified" in r else
         "other:" + ",".join(sorted(r)))
    for table, key in ((verdict, v), (status, (d.get("attribution_status"), v))):
        s = table[key]
        s["rows"] += 1; s["gross"] += abs(int(d["amount_cents"])); s["counted"] += int(d["counted_cents"]); s["pac"] += int(d["pac_activity_cents"])
print("after decisions seen for those rows:", seen)


def show(title, table):
    print("== " + title + " ==")
    for k, s in sorted(table.items(), key=lambda kv: -kv[1]["gross"]):
        print(f"  {str(k):90s} rows={s['rows']:6d} gross=${s['gross']/100:>15,.2f} counted=${s['counted']/100:>15,.2f} pac=${s['pac']/100:>14,.2f}")
    print(f"  TOTAL rows={sum(s['rows'] for s in table.values())} gross=${sum(s['gross'] for s in table.values())/100:,.2f} counted=${sum(s['counted'] for s in table.values())/100:,.2f} pac=${sum(s['pac'] for s in table.values())/100:,.2f}")


show("verdict of the formerly held rows", verdict)
show("attribution_status x verdict", status)
