import json, collections
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
rows=json.load(open(R+r"\legislation_routing_audit.json",encoding="utf-8"))["rows"]
sel=[r for r in rows if r["disposition"]=="selected"]
trip=collections.defaultdict(set); tripc=collections.defaultdict(list)
for r in sel:
    k=(r["member"], str(r.get("bill") or "").strip().lower(), str(r.get("congress")))
    trip[k].add(r["effective_category"]); tripc[k].append(r)
multi={k:v for k,v in trip.items() if len(v)>1}
print("== (member,bill,congress) TRIPLES SCORED UNDER 2+ EFFECTIVE CATEGORIES ==")
print("  distinct triples total:", len(trip))
print("  triples with >=2 categories:", len(multi), "(%.2f%% of triples)" % (100*len(multi)/len(trip)))
print("  category-count histogram:", dict(collections.Counter(len(v) for v in trip.values())))
extra_events=sum(len(v)-1 for v in multi.values())
print("  EXTRA scored events beyond one-per-(member,bill,congress): %d of %d selected (%.1f%%)" % (extra_events,len(sel),100*extra_events/len(sel)))
extra_w=0.0; tot_w=sum(abs(r["contribution"]) for r in sel)
for k,cs in multi.items():
    rs=sorted(tripc[k],key=lambda r:-abs(r["contribution"]))
    extra_w+=sum(abs(r["contribution"]) for r in rs[1:])
print("  EXTRA absolute weight from the duplicate categories: %.1f of %.1f total (%.1f%%)" % (extra_w,tot_w,100*extra_w/tot_w))

print("\n== TOP BILLS BY NUMBER OF DOUBLE-COUNTED MEMBER EVENTS ==")
billn=collections.Counter(); billcats=collections.defaultdict(set); billw=collections.Counter(); billtitle={}
for k,cs in multi.items():
    b=k[1]; billn[b]+=1; billcats[b]|=cs
    rs=sorted(tripc[k],key=lambda r:-abs(r["contribution"])); billw[b]+=sum(abs(r["contribution"]) for r in rs[1:])
    billtitle[b]=tripc[k][0].get("title")
print("%-14s %6s %10s  %s" % ("bill","members","extra|w|","categories"))
for b,n in billn.most_common(15):
    print("%-14s %6d %10.1f  %s" % (b,n,billw[b],sorted(billcats[b])))
    print("               title: %s" % str(billtitle[b])[:100])

print("\n== WHICH CATEGORY PAIRS CO-OCCUR MOST ==")
pair=collections.Counter()
for k,cs in multi.items():
    cl=sorted(cs)
    for i in range(len(cl)):
        for j in range(i+1,len(cl)): pair[(cl[i],cl[j])]+=1
for (a,b),n in pair.most_common(12): print("   %-28s + %-28s %5d" % (a,b,n))

print("\n== PER-CATEGORY: how much of each category's weight is a SECOND filing of a bill already scored elsewhere ==")
catextra=collections.Counter(); cattot=collections.Counter()
for r in sel: cattot[r["effective_category"]]+=abs(r["contribution"])
for k,cs in multi.items():
    rs=sorted(tripc[k],key=lambda r:-abs(r["contribution"]))
    for r in rs[1:]: catextra[r["effective_category"]]+=abs(r["contribution"])
for c in sorted(cattot,key=lambda c:-catextra[c]/max(1e-9,cattot[c])):
    print("   %-28s extra=%8.1f / total=%8.1f = %5.1f%%" % (c,catextra[c],cattot[c],100*catextra[c]/cattot[c]))
