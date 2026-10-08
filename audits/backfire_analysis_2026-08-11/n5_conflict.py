# -*- coding: utf-8 -*-
"""READ-ONLY N5: conflict-cell case studies - who authors cross-industry harm."""
import json, os
from collections import defaultdict

ROOT = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
SC = os.path.dirname(os.path.abspath(__file__))
table = {t["member"]: t for t in json.load(open(os.path.join(SC, "analysis_table.json"), encoding="utf-8"))}

# conflict acts: (key, helped industries, harmed industries) from ledger+tensor signs
CONFLICTS = [
    ("S.3538|118",     ["bank", "credit_union"], ["fintech"], "ILC closure"),
    ("S.3734|119",     ["bank", "credit_union"], ["fintech"], "ILC closure reintro"),
    ("S.Amdt.2299|119", ["bank", "credit_union"], ["crypto"], "yield ban"),
    ("S.Amdt.2305|119", ["bank", "credit_union"], ["crypto"], "yield ban variant"),
    ("S.Amdt.2315|119", ["bank", "credit_union"], ["crypto"], "absolute yield ban"),
    ("S.Amdt.2329|119", ["bank", "credit_union"], ["crypto"], "Fed-services moat"),
    ("S.Amdt.2320|119", ["crypto"], ["bank"], "TBTF stablecoin-issuance ban"),
]

bundle = json.load(open(os.path.join(ROOT, "member_desk_bundle.json"), encoding="utf-8"))
holders = defaultdict(list)
for m in bundle["members"]:
    for b in m.get("bills") or []:
        holders["%s|%s" % (b.get("bill"), b.get("congress"))].append((m["name"], b.get("role")))

print("=== conflict-cell sponsors: alignment with the HARMED industry ===")
print("(board scores; harmed-industry mean vs roster mean - do the harmed industry's OWN allies author its harm?)")
roster_means = {}
for ind in ("credit_union", "bank", "crypto", "fintech"):
    vals = [t["align_%s" % ind] for t in table.values()]
    roster_means[ind] = sum(vals) / len(vals)
for key, helped, harmed, label in CONFLICTS:
    people = holders.get(key, [])
    if not people:
        print("%-18s NO SPONSORS IN ROSTER" % key)
        continue
    h = harmed[0]
    scores_h = [table[n]["align_%s" % h] for n, _ in people if n in table]
    scores_helped = [table[n]["align_%s" % helped[0]] for n, _ in people if n in table]
    print("%-18s %-28s sponsors=%d  harmed(%s) align mean=%+.3f (roster %+.3f)  helped(%s) mean=%+.3f (roster %+.3f)"
          % (key, label, len(people), h, sum(scores_h)/len(scores_h), roster_means[h],
             helped[0], sum(scores_helped)/len(scores_helped), roster_means[helped[0]]))
    for n, role in people:
        t = table.get(n)
        if t:
            print("    %-24s [%s]  harmed-align=%+.3f  helped-align=%+.3f  exp_%s=%.1f"
                  % (n, role, t["align_%s" % h], t["align_%s" % helped[0]], h, t["exp_%s" % h]))

# top-quartile champions of A with HIGH exposure to B vs their B-alignment residual
print()
print("=== the danger zone: A-champions (top 25 by align_A) with above-median B exposure ===")
import statistics
for a, b in (("crypto", "bank"), ("crypto", "credit_union"), ("bank", "fintech"), ("credit_union", "bank")):
    rows = sorted(table.values(), key=lambda t: -t["align_%s" % a])[:25]
    med_exp = statistics.median([t["exp_%s" % b] for t in table.values()])
    hot = [t for t in rows if t["exp_%s" % b] > med_exp]
    if not hot: continue
    mean_b_all = roster_means[b]
    mean_b_hot = sum(t["align_%s" % b] for t in hot) / len(hot)
    print("A=%-12s B=%-12s  %d/25 champions above-median B-exposed | their mean align_B=%+.3f vs roster %+.3f"
          % (a, b, len(hot), mean_b_hot, mean_b_all))
