import json,sys,math,random,collections,glob,os,csv,openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
SEED=int(os.environ.get('SEED','7')); random.seed(SEED)   # fixed seed -> reproducible; scenarios use SAME seed so deltas aren't MC noise
BUDGET=2_000_000; CAP=50_000; MC=int(os.environ.get('MC','20')); BSCALE=400000
PRO={'Champion','Defender','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congestion.json'))}
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
wb=openpyxl.load_workbook(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; nrm=wb['Legislative Score - Normalized']
score={bm.cell(r,1).value:(bm.cell(r,19).value or 0) for r in range(3,536) if bm.cell(r,1).value}
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
CS=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\category_stance.json'))['matrix']
BP=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\bipartisan.json')); bpf={m['member']:BP.get(m['member'],24)/100.0 for m in C.values()}
BETA_C=0.8   # bipartisan members get a coalition-seed boost (natural cross-aisle bridges)
party={}
for congN in (119,118,117):
    pth=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\votes\HS%d_members.csv'%congN
    if os.path.exists(pth):
        for row in csv.DictReader(open(pth,encoding='utf-8')):
            b=row.get('bioguide_id'); pc=str(row.get('party_code'))
            if b and b not in party: party[b]={'100':'D','200':'R'}.get(pc,'I')
prt={m['member']:party.get(m.get('bioguide',''),'?') for m in C.values()}
def cpf(n,u):   # bridges spread further across the aisle in the cascade
    return 0.4+0.6*math.sqrt(bpf.get(n,0.24)*bpf.get(u,0.24)) if (prt.get(n)!=prt.get(u) and prt.get(n) in 'DR' and prt.get(u) in 'DR') else 1.0
net=max(glob.glob(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
adj=collections.defaultdict(dict); mem=set(members)
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
        w=(adj[a][b]+w)/2 if b in adj[a] else w   # D2 2026-07-01: 41 reverse-dup pairs carry ASYMMETRIC directed weights (up to 3x) -- mean-symmetrize (was silent last-write-wins)
        adj[a][b]=w; adj[b][a]=w
# RECEPTIVITY LAYER (2026-07-02): receiver susceptibility on edges + contingency-aware seed activation.
try:
    REC=json.load(open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\member_receptivity.json'))['members'] if os.environ.get('RECEPT_LAYER','1')!='0' else {}
except FileNotFoundError: REC={}
def rc(m,k,d=1.0): return REC.get(m,{}).get(k,d)
# stance-graded contingency gate (matches budget_frontier: allies ungated core; take-rate falls down the ladder)
SGATE={'Highly Persuadable':1.00,'True Neutral':0.90,'Neutral':0.90,'—':0.85,'Lean Skeptic':0.75,
       'Skeptic':0.55,'Opponent':0.35,'Ally':1.0,'Champion':1.0,'Defender':1.0}
def gate(n,cs): return max(0.15,rc(n,'seed_prob',1.0)*SGATE.get(cs.get(n,'—'),0.85))
P={n:{u:(w*cpf(n,u)*rc(u,'edge_mult'))/(w*cpf(n,u)*rc(u,'edge_mult')+6.0) for u,w in adj[n].items()} for n in members}   # cross-party bridge ties carry more cascade probability
idx={n:i for i,n in enumerate(members)}; NM=len(members)
def _sm(x):   # splitmix64 -> [0,1): deterministic per-(iteration,edge) draw, independent of activation order (TRUE CRN)
    x=(x+0x9E3779B97F4A7C15)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>30))*0xBF58476D1CE4E5B9)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>27))*0x94D049BB133111EB)&0xFFFFFFFFFFFFFFFF
    return ((x^(x>>31))&0xFFFFFFFFFFFFFFFF)/0x10000000000000000
def cascade(Aseeds,Bseeds,it):
    # HIGH-1 fix: edge (u,v) at iteration `it` always draws the SAME value regardless of which seeds changed,
    # so adding a seed no longer desyncs the stream -> marginal isolates the TRUE effect, not RNG noise.
    col={**dict.fromkeys(sorted(Aseeds),'A'),**dict.fromkeys(sorted(Bseeds),'B')}; fr=list(col.items())
    while fr:
        nf=[]
        for u,c in fr:
            iu=idx[u]*NM
            for v,p in P[u].items():
                if v not in col and _sm(it*NM*NM+iu+idx[v])<p: col[v]=c; nf.append((v,c))
        fr=nf
    return sum(1 for c in col.values() if c=='A')
blocks=[3,11,19,27,35,43,51,59,67,75,83,91,99,145,115,107,123,131]
labels={sc:str(nrm.cell(1,sc).value).replace(' - Sponsor','').replace(' Sponsor','').strip() for sc in blocks}
BLOCKCAT={3:'Examination & Supervision',11:'CU Capital Requirements',19:'NCUA Budget & Insurance',27:'Interchange',
35:'Payments',43:'Technology & Emerging',51:'Fraud Prevention',59:'Data Privacy & Cyber',67:'Charter Modernization',
75:'Defense CU Issues',83:'Field of Membership',91:'CDFI Fund',99:'CFPB',145:'CFPB',115:'TCPA',
107:'Credit Card Mandates',123:'Member Business Lending',131:'Mortgage & Housing'}
nrow={nrm.cell(r,1).value:r for r in range(3,536) if nrm.cell(r,1).value}
def eng(sc,n):
    r=nrow.get(n); sw=[nrm.cell(2,sc+o).value or 0 for o in (0,2,4)]
    return sum(sw[i]*(nrm.cell(r,sc+[0,2,4][i]).value or 0) for i in range(3)) if r else 0
smax=max(score.values()) or 1
ALL={}; summ=[]
for sc in blocks:
    cat=BLOCKCAT[sc]; cs={n:CS.get(n,{}).get(cat,'—') for n in members}
    campT={n:('pro' if cs[n] in PRO else 'anti' if cs[n] in ANTI else 'neu') for n in members}
    Aseed=set(n for n in members if campT[n]=='pro'); anti=[n for n in members if campT[n]=='anti']
    def spread(extra):
        ex=set(extra); tot=0
        for it in range(MC):
            random.seed(1000003*SEED+it)   # CRN: base & every spread({n}) share draws -> marginal isolates the true effect, not noise
            # contingency-aware: lobbied seeds take w.p. personality seed_prob x stance gate (dedicated _sm stream)
            s=Aseed|{n for n in ex if _sm((1<<62)+it*NM+idx[n])<gate(n,cs)}
            bx=[n for n in members if random.random()<min(0.9,ind[n]/BSCALE) and campT[n]=='neu' and n not in s]   # 5.A FIX: roll for EVERY member FIRST (CRN-stable -- base & spread({n}) share draws), THEN filter. The old order gated the draw behind `n not in s`, so adding a seed changed how many draws fired -> stream desync -> MC noise in the marginal.
            tot+=cascade(s,set(anti)|set(bx),it)
        return tot/MC
    ev={n:eng(sc,n)+0.15*score[n]/smax for n in members}
    cand=sorted([n for n in members if campT[n] in ('neu',) or cs[n]=='Ally'],key=lambda n:-ev[n])[:45]
    base=spread(set()); mg={n:max(0.0,spread({n})-base) for n in cand}
    pos={n:v for n,v in mg.items() if v>0}
    boost={n:v*(1+BETA_C*bpf.get(n,0.24)) for n,v in pos.items()}; tot=sum(boost.values()) or 1   # bridges get a larger seed
    al={n:0 for n in members}
    for n,v in boost.items(): al[n]=min(CAP,round(BUDGET*v/tot/1000)*1000)
    top=sorted([(n,al[n]) for n in members if al[n]>0],key=lambda x:-x[1])
    ALL[labels[sc]]={n:a for n,a in top}
    # M2 fix 2026-07-02: spread is submodular, so summing INDIVIDUAL marginals overstates the joint gain.
    # Report the honest joint spread of the funded seed set (one extra MC evaluation per topic).
    joint=spread(set(pos)) if pos else base
    summ.append((labels[sc],sum(al.values()),len(top),base,joint,top[:4]))
    print('%-30s base %.0f -> %.0f (+%.1f joint; naive-additive +%.1f) | $%s, %d seeds: %s'%(labels[sc][:30],base,joint,joint-base,sum(pos.values()),f'{sum(al.values()):,}',len(top),', '.join('%s $%dk'%(n.split()[-1],a//1000) for n,a in top[:4])))
tag='' if (SEED==7 and os.environ.get('MC','20')=='20') else '_seed%d_mc%d'%(SEED,MC)
json.dump(ALL,open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\per_topic_coalition%s.json'%tag,'w'))
print('\nwrote per_topic_coalition%s.json (seed %d, MC %d, %d sub-categories)'%(tag,SEED,MC,len(ALL)))
