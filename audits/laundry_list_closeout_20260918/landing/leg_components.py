import json, sys
b = json.load(open(sys.argv[1], encoding="utf-8")); a = json.load(open(sys.argv[2], encoding="utf-8"))
lb, la = b["legislative_pillar"], a["legislative_pillar"]
print("legislative_pillar components:", sorted(la))
for m in ("Tim Scott", "Andrew Ogles", "Pete Sessions"):
    print("==", m)
    for k in sorted(la):
        vb = lb.get(k, {}).get(m) if isinstance(lb.get(k), dict) else None
        va = la.get(k, {}).get(m) if isinstance(la.get(k), dict) else None
        if vb != va: print("   %-28s %s -> %s" % (k, vb, va))
changed = {}
for k in sorted(la):
    if isinstance(la.get(k), dict) and isinstance(lb.get(k), dict):
        n = sum(1 for m in la[k] if lb[k].get(m) != la[k][m]); 
        if n: changed[k] = n
print("members changed per component:", changed)
for k in la:
    if not isinstance(la[k], dict): print("scalar", k, ":", str(lb.get(k))[:120], "->", str(la[k])[:120])
