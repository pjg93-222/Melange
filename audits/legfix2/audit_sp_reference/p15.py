import json, collections, math
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
LEG=json.load(open(R+r"\archive_leg.json",encoding="utf-8"))
rows=json.load(open(R+r"\legislation_routing_audit.json",encoding="utf-8"))["rows"]
sel=[r for r in rows if r["disposition"]=="selected"]
bym=collections.defaultdict(list)
for r in sel: bym[r["member"]].append(r)
print("== TOP-DISAGREEMENT MEMBERS: what drives their archive_leg total ==")
for who in ["Jeff Merkley","Rashida Tlaib","Chris Van Hollen","Maxine Waters","Elizabeth Warren"]:
    rs=bym.get(who,[])
    tot=sum(r["contribution"] for r in rs)
    safe=[r for r in rs if "safe" in str(r.get("title","")).lower() and "banking act" in str(r.get("title","")).lower()]
    ltr=[r for r in rs if str(r.get("bill","")).upper().startswith("LTR-")]
    trips=collections.defaultdict(set)
    for r in rs: trips[(r.get("bill"),str(r.get("congress")))].add(r["effective_category"])
    dup=sum(len(v)-1 for v in trips.values())
    print("  %-20s events=%3d  signed total=%+7.2f | SAFE-Banking events=%2d (%+.2f, %.0f%%) | letters=%2d (%+.2f) | extra cross-cat events=%d" %
          (who,len(rs),tot,len(safe),sum(r['contribution'] for r in safe),100*sum(r['contribution'] for r in safe)/tot if tot else 0,len(ltr),sum(r['contribution'] for r in ltr),dup))
    print("       cells:", {k:round(v,2) for k,v in sorted(LEG.get(who,{}).items(),key=lambda x:-abs(x[1]))})

print("\n== COUNTERFACTUAL 2 ROBUSTNESS: alternate tie-breaks ==")
IMP={'Examination & Supervision':0.75,'CU Capital Requirements':0.25,'NCUA Budget & Insurance':1.0,'Interchange':2.0,
 'Payments':0.75,'Technology & Emerging':0.75,'Fraud Prevention':0.75,'Data Privacy & Cyber':1.0,'Charter Modernization':1.0,
 'Defense CU Issues':0.2,'Field of Membership':1.0,'CDFI Fund':0.1,'CFPB':1.0,'Credit Card Mandates':3.0,'TCPA':0.2,
 'Member Business Lending':0.3,'Mortgage & Housing':0.4,'CU Tax Status':3.0}
byt=collections.defaultdict(list)
for r in sel: byt[(r["member"],str(r.get("bill") or "").strip().lower(),str(r.get("congress")))].append(r)
def ln_of(v): return max(-1.0,min(1.0,math.copysign(math.sqrt(abs(v)),v)/2.0))
def topband(v): return abs(ln_of(v))>=0.70 and v>0
for name,key in [("highest IMP wins",lambda r:(IMP.get(r["effective_category"],0.5),abs(r["contribution"]))),
                 ("lowest IMP wins",lambda r:(-IMP.get(r["effective_category"],0.5),abs(r["contribution"]))),
                 ("first source_row wins",lambda r:(-r["source_row"],))]:
    leg2=collections.defaultdict(lambda:collections.defaultdict(float))
    for k,rs in byt.items():
        best=max(rs,key=key); leg2[k[0]][best["effective_category"]]+=best["contribution"]
    lost=sum(1 for m in LEG for c,v in LEG[m].items() if topband(v) and not topband(leg2.get(m,{}).get(c,0.0)))
    tw=sum(abs(v) for m in leg2 for v in leg2[m].values())
    print("   %-24s sum|w|=%.1f (-%.1f%%)  top-band cells lost=%d" % (name,tw,100*(1-tw/sum(abs(r['contribution']) for r in sel)),lost))

print("\n== 120th-CONGRESS ROLLOVER DECAY RISK ==")
print("  bill_rules.CURRENT_CONGRESS = env LEGISLATIVE_CURRENT_CONGRESS or 119")
print("  evidence_decay(): LTR-* -> congress_decay(congress) [RECOMPUTED]; everything else -> stored DecayWeight [FROZEN]")
d=collections.Counter((str(r.get("congress")),round(float(r["decay_weight"]),4)) for r in sel if not str(r.get("bill","")).upper().startswith("LTR-"))
print("  non-letter selected events by (congress, stored dw):",dict(d))
print("  -> at CURRENT_CONGRESS=120 letters re-decay by 0.8 but %d non-letter bill events keep their 119-era stored weights" % sum(d.values()))
