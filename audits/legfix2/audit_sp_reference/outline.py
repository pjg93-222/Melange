# -*- coding: utf-8 -*-
"""READ-ONLY: every bill named in Paul's Feb-2026 outline vs the corpus."""
import sys, os, json, collections
sys.path.insert(0, r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec")
import pandas as pd, bill_rules as BR
LIVE = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUTLINE = [
 ("Examination & Supervision","FIRM Act","S.875"),("Examination & Supervision","FIRM Act","H.R.2702"),
 ("Examination & Supervision","TAILOR Act","S.427"),("Examination & Supervision","TAILOR Act","H.R.3380"),
 ("Examination & Supervision","FAIR Exams Act","H.R.940"),("Examination & Supervision","HUMPS Act","H.R.3379"),
 ("Examination & Supervision","SMART Act","H.R.4437"),("Examination & Supervision","STREAMLINE Act","S.3017"),
 ("Examination & Supervision","Fin Reporting Threshold Modernization","H.R.1799"),
 ("Examination & Supervision","Community Bank Regulatory Tailoring","H.R.7056"),
 ("NCUA Budget & Insurance","NCUA CLF Enhancements Act","S.3575"),
 ("Interchange","Credit Card Competition Act","S.3623"),("Interchange","Credit Card Competition Act","H.R.7035"),
 ("Technology & Emerging","Anti-CBDC Surveillance State Act","S.1124"),("Technology & Emerging","Anti-CBDC Surveillance State Act","H.R.1919"),
 ("Technology & Emerging","CLARITY Act","H.R.3633"),("Technology & Emerging","GENIUS Act","S.919"),
 ("Technology & Emerging","STABLE Act","H.R.2392"),("Technology & Emerging","SECURE Notarization Act","S.1561"),
 ("Technology & Emerging","SECURE Notarization Act","H.R.1777"),
 ("Fraud Prevention","TRAPS Act","S.2019"),("Fraud Prevention","TRAPS Act","H.R.4936"),
 ("Data Privacy & Cyber","Homebuyers Privacy Protection Act","S.1467"),("Data Privacy & Cyber","Homebuyers Privacy Protection Act","H.R.2808"),
 ("Charter Modernization","CU Board Modernization Act","S.522"),("Charter Modernization","CU Board Modernization Act","H.R.975"),
 ("Charter Modernization","American Access to Banking Act","H.R.4544"),("Charter Modernization","MORE Opportunities for Homeownership","H.R.7647"),
 ("CU Tax Status","One Big Beautiful Bill Act","H.R.1"),
 ("CDFI Fund","CDFI Fund Transparency Act","S.2704"),("CDFI Fund","AFFORD Act","S.3940"),("CDFI Fund","CDFI Bond Guarantee Improvement","S.1880"),
 ("CFPB","Transparency in CFPB Cost-Benefit Analysis","H.R.2331"),("CFPB","CFP Commission Act","H.R.3445"),
 ("CFPB","Rectifying UDAAP Act","H.R.1652"),("CFPB","TABS Act","H.R.654"),
 ("CFPB","1071 Repeal","S.557"),("CFPB","1071 Repeal","H.R.976"),
 ("CFPB","Business of Insurance Regulatory Reform","S.2419"),("CFPB","Business of Insurance Regulatory Reform","H.R.4735"),
 ("Credit Card Mandates","10% Rate Cap Act","S.381"),("Credit Card Mandates","10% Rate Cap Act","H.R.1944"),
 ("Credit Card Mandates","Credit Card Fairness Act","S.3660"),
 ("Credit Card Mandates","CRA overdraft disapproval","S.J.Res.18"),("Credit Card Mandates","CRA overdraft disapproval","H.J.Res.59"),
 ("Member Business Lending","Veterans MBL Act","S.110"),("Member Business Lending","Veterans MBL Act","H.R.507"),
 ("Member Business Lending","Increasing CU Lending for Business Growth","H.R.1791"),
 ("Member Business Lending","Expanding Access to Lending Options","S.3616"),("Member Business Lending","Expanding Access to Lending Options","H.R.4167"),
 ("Member Business Lending","Protecting Access to Credit for Small Biz","S.2486"),
 ("Mortgage & Housing","HELPER Act","S.978"),("Mortgage & Housing","HELPER Act","H.R.2094"),
 ("Mortgage & Housing","Home of Your Own Act","H.R.2064"),("Mortgage & Housing","SUPPLY Act","H.R.4568"),
]
A = pd.read_excel(os.path.join(LIVE, "congress_bills_archive_20260624_115822.xlsx"), sheet_name="All Bills")
M = pd.read_csv(os.path.join(LIVE, "manual_bill_evidence.csv"))
RA = json.load(open(os.path.join(LIVE, "legislation_routing_audit.json"), encoding="utf-8"))
sel = [r for r in RA["rows"] if r.get("disposition") == "selected"]
effc = collections.defaultdict(set); effw = collections.defaultdict(float)
for r in sel:
    k = BR.bill_key(r.get("bill"))
    if k: effc[k].add(r["effective_category"]); effw[k] += abs(float(r.get("contribution") or 0))
a119 = collections.defaultdict(int)
for _, r in A.iterrows():
    k = BR.bill_key(r.get("Name"))
    if k and str(r.get("Congress")).strip() == "119": a119[k] += 1
akeys = collections.Counter(BR.bill_key(v) for v in A["Name"].astype(str) if BR.bill_key(v))
print("%-24s %-38s %-11s %6s %6s %7s  %s" % ("OUTLINE CATEGORY","BILL","NUMBER","ROWS","119th","WEIGHT","LANDS IN"))
print("-" * 152)
miss, wrong = [], []
for cat, name, num in OUTLINE:
    k = BR.bill_key(num); n = akeys.get(k, 0); n119 = a119.get(k, 0)
    lands = ",".join(sorted(effc.get(k, []))) or "-"
    if n == 0:
        miss.append((cat, name, num)); lands = "*** ABSENT ***"
    elif cat not in effc.get(k, set()):
        wrong.append((cat, name, num, lands))
    print("%-24s %-38s %-11s %6d %6d %7.1f  %s" % (cat[:24], name[:38], num, n, n119, effw.get(k, 0.0), lands[:44]))
print()
print("=" * 100)
print("A. OUTLINE-NAMED BILLS COMPLETELY ABSENT FROM THE CORPUS: %d of %d" % (len(miss), len(OUTLINE)))
print("=" * 100)
for cat, name, num in miss:
    print("   %-11s %-40s (outline category: %s)" % (num, name, cat))
print()
print("=" * 100)
print("B. OUTLINE-NAMED BILLS PRESENT BUT NOT SCORED IN THEIR OUTLINE CATEGORY: %d" % len(wrong))
print("=" * 100)
for cat, name, num, lands in wrong:
    print("   %-11s %-36s outline=%-24s actually scored in: %s" % (num, name[:36], cat[:24], lands))
