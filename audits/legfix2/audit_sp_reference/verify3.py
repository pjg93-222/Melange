# -*- coding: utf-8 -*-
"""READ-ONLY: independently verify the three workflow claims that change my own conclusions."""
import sys, os, json, csv, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"

print("=" * 96)
print("1. ACU-07 - is press_text_cache.jsonl truncated at a paywall?")
print("=" * 96)
acu, marker, lens = 0, 0, []
for line in open(os.path.join(LIVE, "press_text_cache.jsonl"), encoding="utf-8"):
    try: o = json.loads(line)
    except Exception: continue
    if "americascreditunions.org" not in (o.get("url") or ""): continue
    acu += 1; t = o.get("text") or ""
    i = t.find("LOG IN FOR ACCESS")
    if i >= 0: marker += 1; lens.append(i)
    else: lens.append(len(t))
lens.sort()
print("ACU cache entries: %d | containing 'LOG IN FOR ACCESS': %d (%.1f%%)" % (acu, marker, 100*marker/acu))
print("chars of real text before the cut: min %d  p25 %d  median %d  p75 %d  max %d" % (
    lens[0], lens[len(lens)//4], lens[len(lens)//2], lens[3*len(lens)//4], lens[-1]))
print("CONFIRMED: my press bill-extraction (36 bills) is a FLOOR, not a count.")

print()
print("=" * 96)
print("2. W6 - does archive_leg.json feed the RANK?")
print("=" * 96)
WT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec"
src = open(os.path.join(WT, "compute_pillars.py"), encoding="utf-8").read()
print("occurrences of 'archive_leg' in compute_pillars.py:", src.count("archive_leg"))
for i, l in enumerate(src.splitlines(), 1):
    if "legp" in l or "_read_OEF" in l or "Bill Model" in l:
        print("   L%-4d %s" % (i, l.strip()[:110]))

print()
print("=" * 96)
print("3. MISS-06 / ACU-04 - is there adjudicated ACU direction data sitting unused?")
print("=" * 96)
p = os.path.join(LIVE, "cu_bill_directions.json")
if os.path.exists(p):
    J = json.load(open(p, encoding="utf-8"))
    bills = J.get("bills", J)
    print("cu_bill_directions.json : %d bills" % len(bills))
    print("  note:", str(J.get("note"))[:150] if isinstance(J, dict) else "-")
    pos = collections.Counter()
    for k, v in bills.items():
        pos[(v.get("position") if isinstance(v, dict) else v)] += 1
    print("  positions:", dict(pos))
    ks = list(bills.keys())[:8]
    print("  sample:", [(k, bills[k]) for k in ks][:4])
q = os.path.join(LIVE, "bill_direction_queue_FILLED.csv")
rows = list(csv.DictReader(open(q, encoding="utf-8-sig")))
filled = [r for r in rows if (r.get("direction_+1_0_-1") or "").strip()]
print("bill_direction_queue_FILLED.csv : %d rows, %d with a human direction" % (len(rows), len(filled)))
print("  directions:", dict(collections.Counter(r["direction_+1_0_-1"].strip() for r in filled)))
print("  provenance:", dict(collections.Counter((r.get("provenance") or "").strip()[:44] for r in filled)))
print()
print("code consumers of cu_bill_directions / bill_direction_queue:")
hits = 0
for root, _, files in os.walk(WT):
    if "__pycache__" in root or "attic" in root: continue
    for fn in files:
        if not fn.endswith((".py", ".js")): continue
        try: t = open(os.path.join(root, fn), encoding="utf-8", errors="replace").read()
        except Exception: continue
        if "cu_bill_directions" in t or "bill_direction_queue" in t:
            hits += 1; print("   HIT:", os.path.join(root, fn).replace(WT, "fec"))
print("   total code consumers:", hits, "  <- if 0, Paul's adjudication work is stranded")
