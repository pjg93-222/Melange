import json, collections, math, os, glob
R = r"C:\Users\pgoff\OneDrive\Desktop\Melange Systems"
# find the pillar snapshot
cand=[f for f in glob.glob(R+r"\*.json") if "pillar" in os.path.basename(f).lower() or "snapshot" in os.path.basename(f).lower()]
print("snapshot candidates:",[os.path.basename(c) for c in cand])
LEG=json.load(open(R+r"\archive_leg.json",encoding="utf-8"))
tot={m:sum(v for v in LEG[m].values()) for m in LEG}
sn=None
for c in cand:
    try:
        d=json.load(open(c,encoding="utf-8"))
        if isinstance(d,dict) and "O" in d: sn=d; print("using",os.path.basename(c),"stamped",d.get("stamped")); break
    except Exception: pass
if sn:
    O=sn["O"]
    common=[m for m in O if m in tot]
    print("members in both:",len(common))
    def spear(a,b):
        def rk(x):
            s=sorted(range(len(x)),key=lambda i:x[i]); r=[0]*len(x); i=0
            while i<len(s):
                j=i
                while j+1<len(s) and x[s[j+1]]==x[s[i]]: j+=1
                for k in range(i,j+1): r[s[k]]=(i+j)/2.0+1
                i=j+1
            return r
        ra,rb=rk(a),rk(b); n=len(a); ma=sum(ra)/n; mb=sum(rb)/n
        num=sum((ra[i]-ma)*(rb[i]-mb) for i in range(n))
        den=math.sqrt(sum((ra[i]-ma)**2 for i in range(n))*sum((rb[i]-mb)**2 for i in range(n)))
        return num/den
    a=[float(O[m] or 0) for m in common]; b=[tot[m] for m in common]
    print("Spearman rho( workbook Bill Model col O , archive_leg member total ) = %.3f" % spear(a,b))
    print("  O range: %.2f .. %.2f ; archive_leg total range: %.2f .. %.2f" % (min(a),max(a),min(b),max(b)))
    # biggest disagreements
    def rank(x):
        o=sorted(range(len(x)),key=lambda i:-x[i]); r=[0]*len(x)
        for p,i in enumerate(o): r[i]=p+1
        return r
    ra,rb=rank(a),rank(b)
    d=sorted(range(len(common)),key=lambda i:-abs(ra[i]-rb[i]))[:12]
    print("  largest rank disagreements (member: O-rank vs archive_leg-rank):")
    for i in d: print("     %-26s O#%-4d archive#%-4d  |delta|=%d" % (common[i],ra[i],rb[i],abs(ra[i]-rb[i])))
else:
    print("no pillar snapshot with O found -> cannot compare the two legislative measures")
