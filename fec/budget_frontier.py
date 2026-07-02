import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import json,sys,math,random,collections,glob,os,csv,openpyxl,heapq
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
SEED=int(os.environ.get('SEED','7')); random.seed(SEED)
MC=int(os.environ.get('MC','20')); CAP=50_000; BSCALE=400000; MAXSEEDS=int(os.environ.get('MAXSEEDS','60'))
LEVON=os.environ.get('LEV','1')!='0'   # electoral leverage on (competitive seats cheaper to move)
ONLY=os.environ.get('TOPIC')           # optional single-topic filter (substring) for fast validation
PRO={'Champion','Defender','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(os.environ.get('CONGEST',B+r'\congestion.json')))}   # scenario can override money state
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
wb=openpyxl.load_workbook(MB_ROOT+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; nrm=wb['Legislative Score - Normalized']
score={bm.cell(r,1).value:(bm.cell(r,19).value or 0) for r in range(3,536) if bm.cell(r,1).value}
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
# M6 fix 2026-07-02: align with flip_model's H3 — members with NO FEC record (receipts=0) get the MEDIAN
# industry money imputed, so bystander activation treats them like a typical member instead of never-activated.
_iv=sorted(v for v in ind.values() if v>0); _imed=_iv[len(_iv)//2] if _iv else 0
if os.environ.get('IMPUTE_IND0','1')!='0':
    ind={n:(_imed if (C[n].get('receipts') or 0)==0 else ind[n]) for n in members}
CS=json.load(open(os.environ.get('CATSTANCE',B+r'\category_stance.json')))['matrix']   # scenario can override stance state
BP=json.load(open(B+r'\bipartisan.json')); bpf={m:BP.get(m,24)/100.0 for m in members}
EL=json.load(open(B+r'\electoral.json')); lev={m:(EL.get(m,{}).get('leverage',1.0) if LEVON else 1.0) for m in members}
ELECTORAL=os.environ.get('ELECTORAL','0')=='1' or '--electoral' in sys.argv   # toggleable mode: add contest plays to the frontier
REPFAC=float(os.environ.get('REPFAC','0.6'))                                   # primary-win feasibility discount on contest plays
EP=json.load(open(B+r'\electoral_plays.json'))
party={}
for congN in (119,118,117):
    pth=B+r'\votes\HS%d_members.csv'%congN
    if os.path.exists(pth):
        for row in csv.DictReader(open(pth,encoding='utf-8')):
            b=row.get('bioguide_id'); pc=str(row.get('party_code'))
            if b and b not in party: party[b]={'100':'D','200':'R'}.get(pc,'I')
prt={m:party.get(C[m].get('bioguide',''),'?') for m in members}
def cpf(n,u): return 0.4+0.6*math.sqrt(bpf.get(n,0.24)*bpf.get(u,0.24)) if (prt.get(n)!=prt.get(u) and prt.get(n) in 'DR' and prt.get(u) in 'DR') else 1.0
net=max(glob.glob(B+r'\congress_cosponsor_network_*.xlsx'),key=os.path.getmtime)
ne=openpyxl.load_workbook(net,data_only=True)['Edges']
adj=collections.defaultdict(dict); mem=set(members)
for r in range(2,ne.max_row+1):
    a,b,w=ne.cell(r,1).value,ne.cell(r,2).value,ne.cell(r,3).value
    a=bio2name.get(a); b=bio2name.get(b)
    if a in mem and b in mem and a!=b and isinstance(w,(int,float)):
        w=(adj[a][b]+w)/2 if b in adj[a] else w   # D2 2026-07-01: 41 reverse-dup pairs carry ASYMMETRIC directed weights (up to 3x) -- mean-symmetrize (was silent last-write-wins)
        adj[a][b]=w; adj[b][a]=w
# RECEPTIVITY LAYER (2026-07-02): edge_mult = receiver susceptibility (Byrne); seed_prob = contingency-
# aware activation (Chen ICML'21 / SNAM behaviour-aware IM: a lobbied seed takes with probability, it is
# not a guaranteed activation). Neutral fallback = legacy behavior.
try:
    REC=json.load(open(B+r'\member_receptivity.json'))['members'] if os.environ.get('RECEPT_LAYER','1')!='0' else {}
except FileNotFoundError: REC={}
def rc(m,k,d=1.0): return REC.get(m,{}).get(k,d)
# STANCE-GRADED GATE (user 2026-07-02): the contingency take-rate falls down the stance ladder — an
# ally is never gated (already active core), a Highly Persuadable takes the meeting at full personality
# rate, a Skeptic mostly doesn't, a contested Opponent rarely does. Multiplies the personality
# seed_prob per TOPIC (stance is per-category); floor 0.15 so no funded seed is ever impossible.
SGATE={'Highly Persuadable':1.00,'True Neutral':0.90,'Neutral':0.90,'—':0.85,'Lean Skeptic':0.75,
       'Skeptic':0.55,'Opponent':0.35,'Ally':1.0,'Champion':1.0,'Defender':1.0}
def gate(n,cs): return max(0.15,rc(n,'seed_prob',1.0)*SGATE.get(cs.get(n,'—'),0.85))
P={n:{u:(w*cpf(n,u)*rc(u,'edge_mult'))/(w*cpf(n,u)*rc(u,'edge_mult')+6.0) for u,w in adj[n].items()} for n in members}
idx={n:i for i,n in enumerate(members)}; NM=len(members)
def _sm(x):   # splitmix64 -> [0,1): deterministic per-(iteration,edge) draw, independent of activation order (TRUE CRN)
    x=(x+0x9E3779B97F4A7C15)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>30))*0xBF58476D1CE4E5B9)&0xFFFFFFFFFFFFFFFF
    x=((x^(x>>27))*0x94D049BB133111EB)&0xFFFFFFFFFFFFFFFF
    return ((x^(x>>31))&0xFFFFFFFFFFFFFFFF)/0x10000000000000000
def cascade(A,Bs,it):
    # HIGH-1 fix: edge-keyed CRN (see scenario.py) -- adding a seed no longer desyncs the draw stream,
    # so a marginal spread(S+c)-spread(S) isolates the true effect instead of MC noise.
    col={**dict.fromkeys(sorted(A),'A'),**dict.fromkeys(sorted(Bs),'B')}; fr=list(col.items())
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
BLOCKCAT={3:'Examination & Supervision',11:'CU Capital Requirements',19:'NCUA Budget & Insurance',27:'Interchange',35:'Payments',
43:'Technology & Emerging',51:'Fraud Prevention',59:'Data Privacy & Cyber',67:'Charter Modernization',75:'Defense CU Issues',
83:'Field of Membership',91:'CDFI Fund',99:'CFPB',145:'CFPB',115:'TCPA',107:'Credit Card Mandates',123:'Member Business Lending',131:'Mortgage & Housing'}
nrow={nrm.cell(r,1).value:r for r in range(3,536) if nrm.cell(r,1).value}
# H2 fix 2026-07-02: the M3 block merge (CFPB Restrain 99 + CFPB Reach 145 -> one CFPB engagement signal)
# was applied to flip_model but never here — the CFPB coalition-candidate ranking ran on half the signal.
CATBLOCKS={sc:[b for b in blocks if BLOCKCAT[b]==BLOCKCAT[sc]] for sc in blocks}
def eng(sc,n):
    r=nrow.get(n)
    if not r: return 0
    return sum((nrm.cell(2,blk+o).value or 0)*(nrm.cell(r,blk+o).value or 0) for blk in CATBLOCKS[sc] for o in (0,2,4))
smax=max(score.values()) or 1
frontier={}
for sc in blocks:
    if sc in (145,): continue
    lab=labels[sc]
    if ONLY and ONLY.lower() not in lab.lower(): continue
    cat=BLOCKCAT[sc]; cs={n:CS.get(n,{}).get(cat,'—') for n in members}
    campT={n:('pro' if cs[n] in PRO else 'anti' if cs[n] in ANTI else 'neu') for n in members}
    Aseed=set(n for n in members if campT[n]=='pro'); anti=set(n for n in members if campT[n]=='anti')
    comp={n:1-EL.get(n,{}).get('security',0.5) for n in members}
    atrisk=sorted([n for n in Aseed if ELECTORAL and EP.get(n,{}).get('play')=='defend' and comp[n]>=0.4])  # competitive allies that can be insured
    Asafe=Aseed-set(atrisk); risk={n:comp[n] for n in atrisk}
    def spread(extra,defended=()):
        defended=set(defended); ex=set(extra); aa=anti-ex; tot=0   # funded contest converts anti->pro; defended allies are forced to hold
        for it in range(MC):
            random.seed(1000003*SEED+it)
            held=set()
            for m in atrisk:
                r=random.random()
                if m in defended or r<(1-risk[m]): held.add(m)   # always draw (CRN); undefended at-risk ally holds only w.p. 1-risk
            # CONTINGENCY-AWARE seeding: a lobbied seed activates only w.p. personality seed_prob x
            # stance gate (dedicated CRN stream, offset past the edge keys — no draw collisions).
            s=Asafe|held|{n for n in ex if _sm((1<<62)+it*NM+idx[n])<gate(n,cs)}
            bx=[n for n in members if random.random()<min(0.9,ind[n]/BSCALE) and campT[n]=='neu' and n not in s]  # roll for every member (CRN-stable), then filter
            tot+=cascade(s,aa|set(bx),it)
        return tot/MC
    ev={n:eng(sc,n)+0.15*score[n]/smax for n in members}
    cand=sorted([n for n in members if campT[n]=='neu'],key=lambda n:-ev[n])[:45]   # coalition = activate Neutrals; Allies already in pro core / defend pool
    repl=[n for n in members if ELECTORAL and EP.get(n,{}).get('play')=='contest' and campT[n]=='anti'] if ELECTORAL else []
    rset=set(repl); dset=set(atrisk); pool=cand+repl+atrisk
    fac={n:(REPFAC*lev[n] if n in rset else 1.0 if n in dset else lev[n]) for n in pool}
    def marg(c,S,D,cur): return max(0.0,(spread(S,D|{c}) if c in dset else spread(S|{c},D))-cur)*fac[c]
    base=spread(set(),set()); cur=base; prev=base; S=set(); D=set(); path=[{'b':0,'spread':round(base,1),'seed':None}]
    pq=[]
    for c in pool: heapq.heappush(pq,(-marg(c,set(),set(),base),c,0))
    it=0
    while pq and (len(S)+len(D))<MAXSEEDS:
        negeff,c,liter=heapq.heappop(pq)
        if liter==it:
            if c in dset: D.add(c); typ='defend'
            else: S.add(c); typ='contest' if c in rset else 'coalition'
            it+=1; cur=spread(S,D); prev=max(prev,cur)   # display curve clamped non-decreasing (dips are MC noise); cur stays true for marginals
            path.append({'b':(len(S)+len(D))*CAP,'spread':round(prev,1),'seed':c,'type':typ})
        else:
            heapq.heappush(pq,(-marg(c,S,D,cur),c,it))
    # diminishing-returns knee: last seed whose marginal >= 25% of the best marginal
    margs=[path[i]['spread']-path[i-1]['spread'] for i in range(1,len(path))]
    peak=max(margs) if margs else 0; knee=0
    for i,mg in enumerate(margs):
        if mg>=0.25*peak: knee=(i+1)*CAP
    nrep=sum(1 for p in path[1:] if p.get('type')=='contest'); ndef=sum(1 for p in path[1:] if p.get('type')=='defend')
    frontier[lab]={'base':round(base,1),'core_seeds':len(Aseed),'knee':knee,'contest_seeds':nrep,'defend_seeds':ndef,'path':path}
    print('%-26s core %3d (base %.0f) -> +%d (%dR %dD) to %.0f | knee $%dk | first: %s'%(
        lab[:26],len(Aseed),base,len(S)+len(D),nrep,ndef,cur,knee//1000,', '.join(p['seed'].split()[-1]+{'contest':'*','defend':'^'}.get(p.get('type'),'') for p in path[1:4])))
defend_ov=sorted([m for m in members if EP.get(m,{}).get('play')=='defend'],key=lambda m:-EP[m]['value'])[:20]
out={'mode':'electoral' if ELECTORAL else 'coalition','leverage':LEVON,
     'defend_overview':[{'m':m,'v':EP[m]['value'],'party':EP[m].get('party'),'elavg':EP[m].get('elavg')} for m in defend_ov],
     'topics':frontier}
json.dump(out,open(os.environ.get('FRONTIER_OUT',B+r'\budget_frontier%s.json'%('_electoral' if ELECTORAL else '')),'w'))   # FRONTIER_OUT lets the audit test a single topic without clobbering the production all-topics json
print('\nwrote budget_frontier.json (mode %s, leverage %s, %d topics)'%('ELECTORAL' if ELECTORAL else 'coalition','ON' if LEVON else 'OFF',len(frontier)))
