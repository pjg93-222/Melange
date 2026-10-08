# -*- coding: utf-8 -*-
"""READ-ONLY: COVERAGE GAP B - where ACU spends its advocacy vs where the pillar spends its weight.
ACU side uses ACU's OWN Layer-1 issue tags on its 533 policy/comment letters (2024-01..2026-07)."""
import sys, os, json, collections
LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# ACU's own tag counts, pulled live from the site's GraphQL (fieldAdvocacyIssueTypes on 533 letters)
ACU = {"Examination and Supervision":176, "Payments & Technology":92, "Consumer Protection":87,
       "Lending":85, "Tax, Budget & Bank Attacks":82, "Credit Union Powers & Charter":74,
       "Regulatory Relief":23, "Information Security":21, "Diversity, Equity & Inclusion":2}
L1 = {
 "Examination and Supervision": ["Examination & Supervision","CU Capital Requirements","NCUA Budget & Insurance"],
 "Payments & Technology":       ["Interchange","Payments","Technology & Emerging"],
 "Information Security":        ["Fraud Prevention","Data Privacy & Cyber"],
 "Credit Union Powers & Charter":["Charter Modernization","Defense CU Issues","Field of Membership"],
 "Tax, Budget & Bank Attacks":  ["CU Tax Status","CDFI Fund"],
 "Consumer Protection":         ["CFPB","Credit Card Mandates","TCPA"],
 "Lending":                     ["Member Business Lending","Mortgage & Housing"],
}
RA = json.load(open(os.path.join(LIVE, "legislation_routing_audit.json"), encoding="utf-8"))
sel = [r for r in RA["rows"] if r.get("disposition") == "selected"]
w = collections.defaultdict(float)
for r in sel:
    w[r["effective_category"]] += abs(float(r.get("contribution") or 0))
tot = sum(w.values())
acu_tot = sum(ACU[k] for k in L1)          # exclude Regulatory Relief / DEI: no mapped category exists
print("=" * 100)
print("COVERAGE GAP B - ACU's advocacy attention vs the legislative pillar's weight, by Layer-1 issue")
print("=" * 100)
print("  %-32s %10s %10s %12s" % ("ACU LAYER-1 ISSUE", "ACU SHARE", "PILLAR", "RATIO"))
rows = []
for k, cats in L1.items():
    pw = sum(w.get(c, 0.0) for c in cats)
    a, p = 100*ACU[k]/acu_tot, 100*pw/tot
    rows.append((k, a, p, p/a if a else 0, cats))
for k, a, p, ratio, cats in sorted(rows, key=lambda x: -x[3]):
    flag = "OVER-WEIGHTED" if ratio >= 1.5 else ("UNDER-WEIGHTED" if ratio <= 0.67 else "")
    print("  %-32s %9.1f%% %9.1f%% %10.2fx  %s" % (k, a, p, ratio, flag))
print()
print("  Unmapped ACU issue tags with NO category anywhere in the model:")
print("     Regulatory Relief            %d letters" % ACU["Regulatory Relief"])
print("     Diversity, Equity & Inclusion %d letters" % ACU["Diversity, Equity & Inclusion"])
print()
print("PER-CATEGORY PILLAR SHARE (18 categories):")
for c, v in sorted(w.items(), key=lambda x: -x[1]):
    print("     %-28s %8.1f  %5.2f%%" % (c, v, 100*v/tot))
