import json, collections, csv, sys
sys.path.insert(0, r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec")
import bill_rules as BR
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
rows=json.load(open(R+r"\legislation_routing_audit.json",encoding="utf-8"))["rows"]
sel=[r for r in rows if r["disposition"]=="selected"]
print("== DEDUP KEY USES RAW LOWERCASED NAME, NOT bill_key() (build_archive_legislative.py:113) ==")
g=collections.defaultdict(set)
for r in sel:
    bk=BR.bill_key(r.get("bill"))
    if bk: g[(r["member"],bk,str(r.get("congress")),r["effective_category"])].add(str(r.get("bill") or "").strip().lower())
var={k:v for k,v in g.items() if len(v)>1}
print("   (member,bill_key,congress,category) groups with >1 distinct raw name string:",len(var))
for k,v in list(var.items())[:10]: print("      ",k,"->",v)
allnames=collections.defaultdict(set)
for r in sel:
    bk=BR.bill_key(r.get("bill"))
    if bk: allnames[bk].add(str(r.get("bill") or "").strip())
mv={k:v for k,v in allnames.items() if len(v)>1}
print("   bill_keys with >1 raw spelling anywhere in the selected set:",len(mv))
for k,v in list(mv.items())[:10]: print("      ",k,"->",sorted(v))

print("\n== HOW EACH SELECTED EVENT'S SIGN WAS DECIDED ==")
bdir={}
for row in csv.DictReader(open(R+r"\bill_directions.csv",encoding="utf-8-sig")):
    bk=BR.bill_key(row["Bill"])
    if bk: bdir[bk]=row["Direction"].strip()
ov=BR.load_overrides(R+r"\bill_overrides.csv")
man={}
for r in csv.DictReader(open(R+r"\manual_bill_evidence.csv",encoding="utf-8-sig")):
    if str(r.get("Direction") or "").strip(): man[(r["Member"],str(r["Bill"]).strip().lower())]=r["Direction"]
src=collections.Counter(); w=collections.Counter()
for r in sel:
    bk=BR.bill_key(r.get("bill"))
    o=BR.override_for(ov,r.get("bill"),r.get("congress"))
    if o and str(o.get("Direction") or "").strip(): k="1 bill_overrides.csv Direction"
    elif (r["member"],str(r.get("bill") or "").strip().lower()) in man: k="2 manual ManualDirection"
    elif bk in bdir: k="3 bill_directions.csv registry"
    elif r["effective_category"]=="CFPB": k="4 CFPB code default (+1)"
    elif r["effective_category"]=="Credit Card Mandates": k="5 CreditCard title-keyword default"
    else: k="6 CODE DEFAULT: -1 if NEG else +1"
    src[k]+=1; w[k]+=abs(r["contribution"])
tw=sum(w.values())
for k in sorted(src): print("   %-38s n=%5d (%5.1f%%)  |w|=%8.1f (%5.1f%%)" % (k,src[k],100*src[k]/len(sel),w[k],100*w[k]/tw))
print("\n== bill_directions.csv coverage of the archive ==")
sb=set(BR.bill_key(r.get("bill")) for r in sel if BR.bill_key(r.get("bill")))
print("   distinct bill_keys in selected events: %d ; present in bill_directions.csv: %d (%.1f%%)" % (len(sb),len(sb&set(bdir)),100*len(sb&set(bdir))/len(sb)))
print("   rows in bill_directions.csv: %d ; that match NO selected archive bill: %d" % (len(bdir),len(set(bdir)-sb)))
