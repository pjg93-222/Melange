import json,sys,heapq,math,random,collections,glob,os,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
random.seed(7)
# ================= DIALS =================
BUDGET=2_000_000; INC=1000; CAP=50_000
WM,WP=0.6,0.4            # weight: direct money vs network proximity
MC=45                    # IC monte-carlo runs
SEED_COST=15_000         # coalition-mode cost to seed one member
PERS={'Neutral':1.0,'Skeptic':0.85,'Unengaged':0.55,'Ally':0.45,'Champion':0.20,'Opponent':0.10}
PRO={'Champion','Ally'}; ANTI={'Opponent','Skeptic'}
# ================ INPUTS =================
C={m['member']:m for m in json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json'))}
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; ra=wb['Rank & Allocation']
stance={ra.cell(r,1).value:ra.cell(r,7).value for r in range(3,536) if ra.cell(r,1).value}
score={bm.cell(r,1).value:(bm.cell(r,19).value or 0) for r in range(3,536) if bm.cell(r,1).value}
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
cu={n:(C[n]['cu'] or 0) for n in members}
st={n:stance.get(n,'Neutral') for n in members}
camp={n:('pro' if st[n] in PRO else 'anti' if st[n] in ANTI else 'neu') for n in members}
# network adjacency among members
net=max(glob.glob(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
adj=collections.defaultdict(dict); mem=set(members)
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
        adj[a][b]=adj[a].get(b,0)+w; adj[b][a]=adj[b].get(a,0)+w
# proximity to pro/anti SEEDS (1-hop weighted)
nbrA={n:sum(w for u,w in adj[n].items() if camp[u]=='pro') for n in members}
nbrB={n:sum(w for u,w in adj[n].items() if camp[u]=='anti') for n in members}
mA=max(nbrA.values()) or 1; mB=max(nbrB.values()) or 1
moneyscale=max(max(math.sqrt(cu[n]+CAP) for n in members),max(math.sqrt(ind[n]+1) for n in members)) or 1  # FIX: common $ scale (equal-dollar, no implicit premium)
# =============== FLIP = competitive LINEAR THRESHOLD ===============
def A_lt(n,al): return WM*math.sqrt(cu[n]+al+1)/moneyscale + WP*nbrA[n]/mA
def B_lt(n):    return WM*math.sqrt(ind[n]+1)/moneyscale + WP*nbrB[n]/mB   # congestion + opponent-proximity, common scale
def pflip(n,al):
    a=A_lt(n,al); b=B_lt(n); return a/(a+b) if (a+b)>0 else 0
def flip_alloc():
    alloc={n:0 for n in members}; tgt={n:score[n]*PERS[st[n]] for n in members}
    def marg(n): return 0.0 if alloc[n]>=CAP else tgt[n]*(pflip(n,alloc[n]+INC)-pflip(n,alloc[n]))
    h=[(-marg(n),n) for n in members]; heapq.heapify(h); spent=0
    base=sum(tgt[n]*pflip(n,0) for n in members)
    while spent<BUDGET and h:
        g,n=heapq.heappop(h)
        if -g<=0: break
        alloc[n]+=INC; spent+=INC; heapq.heappush(h,(-marg(n),n))
    val=sum(tgt[n]*pflip(n,alloc[n]) for n in members)
    return alloc,spent,base,val
# =============== COALITION = competitive INDEPENDENT CASCADE ===============
P={n:{u:w/(w+4.0) for u,w in adj[n].items()} for n in members}   # edge activation prob
def cascade(Aseeds,Bseeds):
    colA=dict.fromkeys(Aseeds,'A'); colB=dict.fromkeys(Bseeds,'B')
    col={**colA,**colB}; frontier=list(col.items())
    while frontier:
        nf=[]
        for u,c in frontier:
            for v,p in P[u].items():
                if v not in col and random.random()<p:
                    col[v]=c; nf.append((v,c))
        frontier=nf
    return sum(1 for c in col.values() if c=='A')
BSCALE=350000   # congestion enters IC -- industry $ at which a neutral ~certainly leans opposition (tuned)
def spread(extraA):
    Aseed=set([n for n in members if camp[n]=='pro']+list(extraA)); anti=[n for n in members if camp[n]=='anti']
    tot=0
    for _ in range(MC):
        bx=[n for n in members if camp[n]=='neu' and n not in Aseed and random.random()<min(0.9,ind[n]/BSCALE)]
        tot+=cascade(Aseed,set(anti)|set(bx))
    return tot/MC
def coalition_alloc():
    cand=[n for n in members if (camp[n]=='neu' or st[n]=='Ally')]
    cand=sorted(cand,key=lambda n:-score[n])[:90]      # winnable seeds
    base=spread(set())
    mg={n:max(0.0,spread({n})-base) for n in cand}     # single-pass marginal A-spread per candidate
    pos={n:v for n,v in mg.items() if v>0}; tot=sum(pos.values()) or 1
    alloc={n:0 for n in members}
    for n,v in pos.items(): alloc[n]=min(CAP,round(BUDGET*v/tot/1000)*1000)   # full budget, proportional to spread, capped
    funded=sorted(pos.items(),key=lambda x:-x[1])
    return alloc,sum(alloc.values()),base,base+sum(pos.values()),funded
# ================= RUN BOTH =================
fa,fs,fb,fv=flip_alloc()
print('=== FLIP (competitive Linear Threshold) ===')
print('spent $%s | funded %d | flip-value %.1f -> %.1f (+%.1f)'%(f'{fs:,}',sum(1 for v in fa.values() if v>0),fb,fv,fv-fb))
for n,a in sorted([(n,fa[n]) for n in members if fa[n]>0],key=lambda x:-x[1])[:10]:
    print('   %-22s $%6s  %-9s P %.2f->%.2f  ind$%s nbrAnti%.0f'%(n,f'{a:,}',st[n],pflip(n,0),pflip(n,fa[n]),f"{ind[n]:,}",nbrB[n]))
ca,cs,cb,cv,cf=coalition_alloc()
print('\n=== COALITION (competitive Independent Cascade) ===')
print('A-coalition spread %.1f -> %.1f (+%.1f) | seeded %d members @ $%s'%(cb,cv,cv-cb,len(cf),f'{SEED_COST:,}'))
for n,mg in sorted(cf,key=lambda x:-x[1])[:10]:
    print('   %-22s +%.2f nodes  %-9s nbrPro%.0f nbrAnti%.0f'%(n,mg,st[n],nbrA[n],nbrB[n]))
json.dump({'flip':{n:fa[n] for n in members if fa[n]>0},'coalition':{n:ca[n] for n in members if ca[n]>0}},open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\im_allocation.json','w'))
print('\nwrote im_allocation.json (both modes)')
