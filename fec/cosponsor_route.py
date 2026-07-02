import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""Multi-objective co-sponsor recruitment route finder (roadmap step 3, RELINK + MOPBD*).
Edge-activation IM: champions are seeds; each recruiter whips <=K colleagues (out-degree budget).
Builds recruitment ROUTES and returns the Pareto front over (co-sponsors gained, money, cascade-failure risk)."""
import json,sys,os,glob,collections,openpyxl,heapq,random,csv,math
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
K=int(os.environ.get('K','5'))               # recruitment bandwidth: a member personally whips <=K colleagues
CEDGE=float(os.environ.get('CEDGE','10000')) # base $ per recruitment ask
TOPIC=os.environ.get('TOPIC','Interchange')
PRO={'Champion','Defender','Ally'}
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}; members=list(C.keys())
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
CS=json.load(open(B+r'\category_stance.json')); MAT=CS['matrix']; cats=CS['cats']
cat=[c for c in cats if TOPIC.lower() in c.lower()][0]
net=max(glob.glob(B+r'\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
adj=collections.defaultdict(dict); mem=set(members)
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
        w=(adj[a][b]+w)/2 if b in adj[a] else w   # D2 2026-07-01: 41 reverse-dup pairs carry ASYMMETRIC directed weights (up to 3x) -- mean-symmetrize (was silent last-write-wins)
        adj[a][b]=w; adj[b][a]=w
# L4: unify the diffusion kernel with the rest of the system. The coalition/scenario/frontier modules use a
# BRIDGE-AMPLIFIED edge prob P=(w*cpf)/(w*cpf+4); this module previously used the un-amplified P=w/(w+4),
# so a cross-party recruitment between two bridge-builders spread LESS here than in the cascade -- one model,
# two kernels. Adopt the amplified kernel here too so co-sponsor recruitment shares the single diffusion law.
BP=json.load(open(B+r'\bipartisan.json')); bpf={n:BP.get(n,24)/100.0 for n in members}
party={}
for cn in (119,118,117):
    pth=B+r'\votes\HS%d_members.csv'%cn
    if os.path.exists(pth):
        for row in csv.DictReader(open(pth,encoding='utf-8')):
            b=row.get('bioguide_id'); pc=str(row.get('party_code'))
            if b and b not in party: party[b]={'100':'D','200':'R'}.get(pc,'I')
prt={n:party.get(C[n].get('bioguide',''),'?') for n in members}
BETA=1.5
def cpf(n,u):   # cross-party bridge amplifier (identical to scenario/coalition/frontier)
    return 0.4+0.6*math.sqrt(bpf.get(n,0.24)*bpf.get(u,0.24)) if (prt.get(n)!=prt.get(u) and prt.get(n) in 'DR' and prt.get(u) in 'DR') else 1.0
P={u:{v:(w*cpf(u,v))/(w*cpf(u,v)+6.0) for v,w in adj[u].items()} for u in members}     # activation prob if u whips v (bridge-amplified)
seeds=[m for m in members if MAT.get(m,{}).get(cat) in PRO]
MCMODE=os.environ.get('MCMODE','0')=='1'; MC=int(os.environ.get('MC','40'))
def mc_spread(R):
    """Exact reach via MC IC-cascade over the induced subgraph on seeds + recruited R (captures reinforcement:
    a member whipped by several activated colleagues fires more often than tree-reach's single path). CRN-deterministic."""
    nodes=set(seeds)|set(R); tot=0
    for it in range(MC):
        random.seed(1009*it); active=set(seeds); fr=sorted(active)
        while fr:
            nf=[]
            for u in fr:
                for v,p in P[u].items():
                    if v in nodes and v not in active and random.random()<p: active.add(v); nf.append(v)
            fr=sorted(nf)
        tot+=len(active)-len(seeds)
    return tot/MC
def edge_cost(p): return CEDGE/max(0.1,p)                           # unlikely recruitments cost more to land
def build_route(lam,budget):
    """Greedy recruitment route, risk-aversion lam (prefer reliable edges). Returns nested path of (cost,spread,risk)."""
    reach={s:1.0 for s in seeds}; outdeg=collections.Counter(); spent=0.0; got=[]
    path=[(0.0,0.0,0.0)]; pf=0.0; nrec=0
    pq=[]   # candidate edges (u recruited -> v not), keyed by value-per-$ minus risk penalty
    def push_edges(u):
        for v,p in P[u].items():
            if v not in reach and MAT.get(v,{}).get(cat) not in PRO:
                gain=reach[u]*p; c=edge_cost(p); val=(gain-lam*(1-p))/c
                heapq.heappush(pq,(-val,u,v,p,c,gain))
    for s in seeds: push_edges(s)
    while pq and spent<budget:
        nval,u,v,p,c,gain=heapq.heappop(pq)
        if v in reach or outdeg[u]>=K: continue
        if reach.get(u,0)*p<1e-6: continue
        if -nval<=0: break          # best remaining recruitment adds no net value (risk penalty exceeds gain) -> stop
        gain=reach[u]*p
        reach[v]=gain; outdeg[u]+=1; spent+=c; got.append((u,v,p)); nrec+=1
        pf+=p; push_edges(v)
        spread=sum(reach[m] for m in reach if m not in seeds)
        risk=round(1-pf/nrec,3)
        path.append((round(spent),round(spread,2),risk))
    return path,got
def dominated(a,P):   # a=(cost,spread,risk); want spread up, cost & risk down
    for b in P:
        if b is a: continue
        if b[1]>=a[1] and b[0]<=a[0] and b[2]<=a[2] and (b[1]>a[1] or b[0]<a[0] or b[2]<a[2]): return True
    return False
pts=[]
for lam in (0.0,0.5,1.0,2.0,4.0):
    path,got=build_route(lam,1_000_000)
    rec=[v for u,v,p in got]
    for i,(cost,spread,risk) in enumerate(path[1:],start=1):
        if MCMODE: spread=round(mc_spread(set(rec[:i])),2)          # exact reach (reinforcement) instead of tree-reach
        pts.append((cost,spread,risk,lam))
front=[p for p in pts if not dominated(p,pts)]
front=sorted(set(front))
print('CO-SPONSOR ROUTE — issue: %s | %d champion seeds | out-degree budget K=%d'%(cat,len(seeds),K))
print('Pareto front (money, expected co-sponsors gained, risk):')
seen=set()
for cost,spread,risk,lam in sorted(front,key=lambda x:x[0]):
    key=(cost//25000,round(spread));
    if key in seen: continue
    seen.add(key)
    print('   $%-9s -> +%-5.1f co-sponsors  risk %.2f  (λ=%.1f)'%(f'{cost:,}',spread,risk,lam))
# a concrete cheap route at low risk for illustration
path,got=build_route(2.0,300000)
print('\nExample low-risk route ($300k cap, %d recruitments):'%len(got))
for u,v,p in got[:10]: print('   %-22s whips %-22s (p=%.2f)'%(u,v,p))
