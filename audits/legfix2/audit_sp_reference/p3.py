import json, collections, sys
sys.path.insert(0, r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec")
import bill_rules as BR
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
rows = json.load(open(R+r"\legislation_routing_audit.json", encoding="utf-8"))["rows"]
sel = [r for r in rows if r["disposition"]=="selected"]

print("== CONGRESS x decay_weight ACTUALLY APPLIED (selected events) ==")
print("%-10s %8s %14s %14s %16s %16s" % ("congress","n","expected 0.8^age","distinct dw","sum |contrib|","sum contrib"))
byc = collections.defaultdict(list)
for r in sel: byc[str(r.get("congress"))].append(r)
tot_abs = sum(abs(r["contribution"]) for r in sel)
for c in sorted(byc, key=lambda x: (x.isdigit()==False, -int(x) if x.isdigit() else 0)):
    rs = byc[c]
    dws = sorted(set(round(float(r["decay_weight"]),6) for r in rs))
    try: exp = BR.congress_decay(c)
    except Exception: exp = "n/a"
    sa = sum(abs(r["contribution"]) for r in rs); ss = sum(r["contribution"] for r in rs)
    print("%-10s %8d %14s %14s %16.1f %16.1f   (%.1f%% of |W|)" % (c, len(rs), exp, dws if len(dws)<=4 else str(dws[:4])+"...", sa, ss, 100*sa/tot_abs))
print("TOTAL selected |contrib| = %.1f ; signed = %.1f" % (tot_abs, sum(r["contribution"] for r in sel)))

print("\n== decay_weight value histogram over ALL selected ==")
for k,v in collections.Counter(round(float(r["decay_weight"]),6) for r in sel).most_common(): print("   dw=%-10s n=%d" % (k,v))

print("\n== rows where decay_weight != 0.8^(119-congress) ==")
bad = []
for r in sel:
    try: exp = BR.congress_decay(r.get("congress"))
    except Exception: exp = None
    if exp is None or abs(float(r["decay_weight"]) - exp) > 1e-9: bad.append((r, exp))
print("  count:", len(bad), "of", len(sel))
cc = collections.Counter((str(r.get("congress")), round(float(r["decay_weight"]),4), e) for r,e in bad)
for k,v in cc.most_common(20): print("   congress=%s stored_dw=%s should_be=%s  n=%d" % (k[0],k[1],k[2],v))
print("  sum |contrib| of mis-decayed rows: %.1f (%.1f%% of total)" % (sum(abs(r["contribution"]) for r,_ in bad), 100*sum(abs(r["contribution"]) for r,_ in bad)/tot_abs))

print("\n== WHAT THE TOTAL WOULD BE IF congress_decay WERE APPLIED TO ALL ROWS ==")
alt = 0.0
for r in sel:
    try: exp = BR.congress_decay(r.get("congress"))
    except Exception: exp = 1.0
    w = abs(r["contribution"]) / (float(r["decay_weight"]) or 1.0)   # recover sign*rolewt magnitude
    alt += w * exp
print("  actual sum|W| = %.1f ; with-decay sum|W| = %.1f ; ratio = %.3f" % (tot_abs, alt, alt/tot_abs))
