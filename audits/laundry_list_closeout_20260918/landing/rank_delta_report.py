# Read-only: compare the pre-landing rank snapshot with the live rank authority and attribute every mover.
import json, sys
before = json.load(open(sys.argv[1], encoding="utf-8")); after = json.load(open(sys.argv[2], encoding="utf-8"))
rb, ra = before["rank"], after["rank"]; pb, pa = before.get("pcts", {}), after.get("pcts", {})
EPS = 1e-9
def comp_changes(m):
    out = []
    for k in ("leg", "press", "inf", "dem"):
        b = (pb.get(m) or {}).get(k); a = (pa.get(m) or {}).get(k)
        if b is None or a is None or abs(a - b) > EPS: out.append((k, b, a))
    return out
members = sorted(set(rb) | set(ra))
movers = [(m, rb.get(m), ra.get(m)) for m in members if rb.get(m) != ra.get(m)]
print("members before/after: %d / %d | movers: %d" % (len(rb), len(ra), len(movers)))
print("ab_weights before:", before.get("ab_weights"), "| after:", after.get("ab_weights"))
changed = {k: 0 for k in ("leg", "press", "inf", "dem")}; 
for m in members:
    for k, b, a in comp_changes(m): changed[k] += 1
print("members whose pillar percentile changed:", changed)
klass = {}
for m, b, a in movers:
    ks = tuple(k for k, _, _ in comp_changes(m)) or ("none(displaced)",)
    klass[ks] = klass.get(ks, 0) + 1
print("movers by which of THEIR OWN pillars changed:", dict(sorted(klass.items(), key=lambda kv: -kv[1])))
big = sorted(movers, key=lambda t: -abs((t[2] or 0) - (t[1] or 0)))
print("max |rank move|:", (abs(big[0][2] - big[0][1]) if big else 0))
print("--- top 25 movers")
for m, b, a in big[:25]:
    print("  %-28s %4s -> %4s  %s" % (m, b, a, "; ".join("%s %.5f->%.5f" % (k, x if x is not None else float('nan'), y if y is not None else float('nan')) for k, x, y in comp_changes(m))))
print("--- named members")
for m in ("Tim Scott", "Roger Marshall", "Anna Luna", "Anna Paulina Luna", "Juan Vargas", "Mike Crapo"):
    if m in rb or m in ra:
        print("  %-20s rank %s -> %s | score %.6f -> %.6f | %s" % (m, rb.get(m), ra.get(m), before["score"].get(m, float('nan')), after["score"].get(m, float('nan')), comp_changes(m)))
