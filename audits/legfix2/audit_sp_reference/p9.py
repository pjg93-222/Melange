import json, collections
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
rows=json.load(open(R+r"\legislation_routing_audit.json",encoding="utf-8"))["rows"]
sel=[r for r in rows if r["disposition"]=="selected"]
print("== FIELD OF MEMBERSHIP: every selected event ==")
fom=[r for r in sel if r["effective_category"]=="Field of Membership"]
bb=collections.Counter((r.get("bill"),str(r.get("congress")),str(r.get("title"))[:60],r.get("source_section")) for r in fom)
for k,v in bb.most_common(): print("   %-12s C%-4s n=%2d  sec=%-34s %s" % (k[0],k[1],v,str(k[3])[:34],k[2]))
# what other categories those same bills land in
fbills=set((r["member"],str(r.get("bill") or "").strip().lower(),str(r.get("congress"))) for r in fom)
oth=collections.Counter()
for r in sel:
    k=(r["member"],str(r.get("bill") or "").strip().lower(),str(r.get("congress")))
    if k in fbills and r["effective_category"]!="Field of Membership": oth[r["effective_category"]]+=1
print("   same (member,bill,congress) ALSO scored in:",dict(oth))

print("\n== SAFE/SAFER BANKING ACT (cannabis banking) FOOTPRINT ==")
safe=[r for r in sel if "safe" in str(r.get("title","")).lower() and "banking act" in str(r.get("title","")).lower()]
print("   selected events:",len(safe),"  sum|w|=%.1f (%.1f%% of all legislative weight)" % (sum(abs(r['contribution']) for r in safe),100*sum(abs(r['contribution']) for r in safe)/sum(abs(x['contribution']) for x in sel)))
print("   by bill:")
for k,v in collections.Counter((r.get("bill"),str(r.get("congress")),str(r.get("title"))[:45]) for r in safe).most_common(): print("      %-12s C%-4s n=%3d  %s" % (k[0],k[1],v,k[2]))
print("   by effective_category:")
for k,v in collections.Counter(r["effective_category"] for r in safe).most_common(): print("      %-28s %4d" % (k,v))
print("   by source_section (what the scraper filed it under):")
for k,v in collections.Counter(str(r.get("source_section")) for r in safe).most_common(): print("      %-45s %4d" % (k,v))
dt=collections.defaultdict(set)
for r in safe: dt[(r["member"],r.get("bill"),str(r.get("congress")))].add(r["effective_category"])
print("   distinct (member,bill,congress):",len(dt),"; mean categories each = %.2f" % (len(safe)/len(dt)))
