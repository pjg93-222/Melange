import json, collections, csv, math
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
CS=json.load(open(R+r"\category_stance.json",encoding="utf-8")); MX=CS["matrix"]; gate=CS["gate"]
corrob=gate["corrob"]; LEG=json.load(open(R+r"\archive_leg.json",encoding="utf-8"))
rows=json.load(open(R+r"\legislation_routing_audit.json",encoding="utf-8"))["rows"]
sel=[r for r in rows if r["disposition"]=="selected"]
print("== 'sponsor' SUBSTRING TEST on manual_bill_evidence Role values (moneyball_core.py:359) ==")
man=list(csv.DictReader(open(R+r"\manual_bill_evidence.csv",encoding="utf-8-sig")))
for role,n in collections.Counter(r["Role"] for r in man).most_common():
    print("   Role=%-22r n=%3d   \"'sponsor' not in role\" -> %s   => %s" % (role,n,("sponsor" not in role.lower()),"SKIPPED" if "sponsor" not in role.lower() else "COUNTED AS RULE-A AUTHORSHIP"))
print("   -> %d of %d manual rows (all letters) are admitted as 'authored an in-category bill'" % (sum(1 for r in man if 'sponsor' in r['Role'].lower()),len(man)))
lead=[r for r in man if r["Role"].strip()=="sponsor"]
print("   -> %d rows also enter direct_sponsored_bills (moneyball_core.py:366-368), feeding the 10+ volume test" % len(lead))

# COUNTERFACTUAL 1: letters removed from Rule A
letcats=collections.defaultdict(lambda:collections.defaultdict(list))
for r in sel: letcats[r["member"]][r["effective_category"]].append(str(r.get("bill","")).upper().startswith("LTR-"))
vote={}
try:
    VL=json.load(open(R+r"\vote_category_lean.json",encoding="utf-8")); nof=VL["name_of"]
    for bio,cats in VL["votes"].items():
        nm=nof.get(bio)
        if nm: vote[nm]={c for c,d in cats.items() if (d.get("lean",0) or 0)>=0.5 and (d.get("n",0) or 0)>=1}
except Exception as e: print("vote load fail",e)
cf1=[]
for m in MX:
    for c,t in MX[m].items():
        if t in ("Champion","Defender") and corrob.get(m,{}).get(c)=="A":
            ev=letcats.get(m,{}).get(c)
            if ev and all(ev) and c not in vote.get(m,set()): cf1.append((m,c))
print("\n== COUNTERFACTUAL 1: exclude LTR-* from Rule A ==")
print("   Champion/Defender cells that would cap to Ally: %d" % len(cf1))
print("   by category:",dict(collections.Counter(c for _,c in cf1)))
print("   current say-do caps: %d cells -> would become %d (+%.0f%%)" % (sum(len(d) for d in gate['capped'].values()),sum(len(d) for d in gate['capped'].values())+len(cf1),100*len(cf1)/sum(len(d) for d in gate['capped'].values())))

# COUNTERFACTUAL 2: one scored event per (member,bill,congress) - keep highest-IMP category
IMP={'Examination & Supervision':0.75,'CU Capital Requirements':0.25,'NCUA Budget & Insurance':1.0,'Interchange':2.0,
 'Payments':0.75,'Technology & Emerging':0.75,'Fraud Prevention':0.75,'Data Privacy & Cyber':1.0,'Charter Modernization':1.0,
 'Defense CU Issues':0.2,'Field of Membership':1.0,'CDFI Fund':0.1,'CFPB':1.0,'Credit Card Mandates':3.0,'TCPA':0.2,
 'Member Business Lending':0.3,'Mortgage & Housing':0.4,'CU Tax Status':3.0}
byt=collections.defaultdict(list)
for r in sel: byt[(r["member"],str(r.get("bill") or "").strip().lower(),str(r.get("congress")))].append(r)
leg2=collections.defaultdict(lambda:collections.defaultdict(float))
for k,rs in byt.items():
    best=max(rs,key=lambda r:(IMP.get(r["effective_category"],0.5),abs(r["contribution"])))
    leg2[k[0]][best["effective_category"]]+=best["contribution"]
def ln_of(v): return max(-1.0,min(1.0,math.copysign(math.sqrt(abs(v)),v)/2.0))
BANDS=((0.70,'Champion/Defender'),(0.35,'Ally'),(0.25,'Highly Persuadable'),(0.15,'Persuadable'),(0.05,'Lean Persuadable'),(-0.05,'True Neutral'),(-0.15,'Lean Skeptic'),(-0.35,'Skeptic'),(-0.70,'Highly Skeptical'))
def band(x):
    for cut,l in BANDS:
        if x>=cut: return l
    return 'Opponent'
print("\n== COUNTERFACTUAL 2: dedup on (member,bill,congress) only, highest-IMP category wins ==")
print("   scored events: %d -> %d" % (len(sel),sum(len(byt[k]) and 1 for k in byt)))
print("   sum|weight|: %.1f -> %.1f (-%.1f%%)" % (sum(abs(r['contribution']) for r in sel),sum(abs(v) for m in leg2 for v in leg2[m].values()),100*(1-sum(abs(v) for m in leg2 for v in leg2[m].values())/sum(abs(r['contribution']) for r in sel))))
chg=collections.Counter(); dropped=0; tot=0
for m in LEG:
    for c,v in LEG[m].items():
        tot+=1
        b0=band(ln_of(v)); b1=band(ln_of(leg2.get(m,{}).get(c,0.0))) if abs(leg2.get(m,{}).get(c,0.0))>1e-9 else "NO EVIDENCE"
        if b0!=b1: chg[(b0,b1)]+=1
        if b0=="Champion/Defender" and b1!="Champion/Defender": dropped+=1
print("   legislation-only cells whose BAND changes: %d of %d (%.1f%%)" % (sum(chg.values()),tot,100*sum(chg.values())/tot))
print("   Champion/Defender-band cells that lose the top band: %d" % dropped)
for k,v in chg.most_common(10): print("      %-20s -> %-20s %4d" % (k[0],k[1],v))
print("\n   per-category sum|leg| before -> after:")
a=collections.Counter(); b=collections.Counter()
for m in LEG:
    for c,v in LEG[m].items(): a[c]+=abs(v)
for m in leg2:
    for c,v in leg2[m].items(): b[c]+=abs(v)
for c in sorted(a,key=lambda c:-a[c]): print("      %-28s %8.1f -> %8.1f  (%+.1f%%)" % (c,a[c],b[c],100*(b[c]/a[c]-1)))
