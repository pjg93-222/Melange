"""Per-reason rows and dollars for one cross-reference run, read from its ledger.

Usage: python reason_table.py <run_dir>
Read-only. For every reason code on a decision: rows, gross (|amount|),
counted, pac_activity, baseline. Separately: review-queue reasons from
report.json, summary, and attribution_status / bucket censuses.
"""
import json, sqlite3, sys
from collections import defaultdict

run = sys.argv[1]
report = json.load(open(run + r"\report.json", encoding="utf-8"))
print("run", report["run_id"], "industry", report["scope"]["industries"], "elapsed", report.get("elapsed_seconds"), "status", report.get("status"))
print("database", report["scope"]["database"])
print("summary", json.dumps(report["summary"], sort_keys=True))
print()
print("== review-queue reasons (report.json unresolved_reasons) ==")
for item in report["unresolved_reasons"]:
    print(f"  {item['reason']:55s} records={item['records']:7d} amount=${item['amount']:>16,.2f}")
print()

def stat():
    return dict(rows=0, gross=0, counted=0, pac=0, baseline=0)

by_reason = defaultdict(stat)
by_status = defaultdict(stat)
by_bucket = defaultdict(stat)
by_attr = defaultdict(stat)
excluded_by_reason = defaultdict(stat)
n = 0
con = sqlite3.connect("file:" + run + r"\ledger.sqlite?mode=ro", uri=True)
for (pj,) in con.execute("select payload_json from decisions"):
    d = json.loads(pj)
    n += 1
    amt = abs(int(d["amount_cents"]))
    def add(s):
        s["rows"] += 1; s["gross"] += amt; s["counted"] += int(d["counted_cents"]); s["pac"] += int(d["pac_activity_cents"]); s["baseline"] += int(d["baseline_cents"])
    for r in d["reasons"]:
        add(by_reason[r])
        if d["status"] == "excluded_with_evidence":
            add(excluded_by_reason[r])
    add(by_status[d["status"]])
    add(by_bucket[d["bucket"]])
    add(by_attr[d.get("attribution_status")])
print("decisions read:", n)

def money(c):
    return f"${c/100:,.2f}"

def show(title, table):
    print("== " + title + " ==")
    for k, s in sorted(table.items(), key=lambda kv: -kv[1]["gross"]):
        print(f"  {str(k):60s} rows={s['rows']:7d} gross={money(s['gross']):>17s} counted={money(s['counted']):>17s} pac={money(s['pac']):>15s} baseline={money(s['baseline']):>17s}")
    print()

show("every decision reason (rows carry several)", by_reason)
show("reasons on EXCLUDED decisions (dollars removed)", excluded_by_reason)
show("status", by_status)
show("bucket", by_bucket)
show("attribution_status", by_attr)
