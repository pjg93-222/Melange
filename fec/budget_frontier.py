import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MBC
import json, sys, random, os, openpyxl, heapq
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
score=MBC.scores()   # PHASE-2: Python rank authority
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
# M6 fix 2026-07-02: align with flip_model's H3 — members with NO FEC record (receipts=0) get the MEDIAN
# industry money imputed, so bystander activation treats them like a typical member instead of never-activated.
_iv=sorted(v for v in ind.values() if v>0); _imed=_iv[len(_iv)//2] if _iv else 0
if os.environ.get('IMPUTE_IND0','1')!='0':
    ind={n:(_imed if (C[n].get('receipts') or 0)==0 else ind[n]) for n in members}
CS=json.load(open(os.environ.get('CATSTANCE',B+r'\category_stance.json')))['matrix']   # scenario can override stance state
bpf=MBC.bpf()
EL=json.load(open(B+r'\electoral.json')); lev={m:(EL.get(m,{}).get('leverage',1.0) if LEVON else 1.0) for m in members}
ELECTORAL=os.environ.get('ELECTORAL','0')=='1' or '--electoral' in sys.argv   # toggleable mode: add contest plays to the frontier
REPFAC=float(os.environ.get('REPFAC','0.6'))                                   # primary-win feasibility discount on contest plays
EP=json.load(open(B+r'\electoral_plays.json'))
prt=MBC.party()
cpf=MBC.cpf_diffusion
adj=MBC.load_network()
# RECEPTIVITY LAYER (2026-07-02): edge_mult = receiver susceptibility (Byrne); seed_prob = contingency-
# aware activation (Chen UAI'21 / SNAM behaviour-aware IM: a lobbied seed takes with probability, it is
# not a guaranteed activation). Neutral fallback = legacy behavior.
rc=MBC.rc
from moneyball_core import gate
P=MBC.build_P(adj)
idx={n:i for i,n in enumerate(members)}; NM=len(members)
_sm=MBC.sm64
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
from moneyball_core import blocks,BLOCKCAT
labels={sc:str(nrm.cell(1,sc).value).replace(' - Sponsor','').replace(' Sponsor','').strip() for sc in blocks}
nrow={nrm.cell(r,1).value:r for r in range(3,536) if nrm.cell(r,1).value}
# H2 fix 2026-07-02: the M3 block merge (CFPB Restrain 99 + CFPB Reach 145 -> one CFPB engagement signal)
# was applied to flip_model but never here — the CFPB coalition-candidate ranking ran on half the signal.
from moneyball_core import CATBLOCKS
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
_outpath=os.environ.get('FRONTIER_OUT',B+r'\budget_frontier%s.json'%('_electoral' if ELECTORAL else ''))   # FRONTIER_OUT lets the audit test a single topic without clobbering the production all-topics json
MBC.dump_atomic(out,_outpath)
print('\nwrote %s (mode %s, leverage %s, %d topics)'%(os.path.basename(_outpath),'ELECTORAL' if ELECTORAL else 'coalition','ON' if LEVON else 'OFF',len(frontier)))
