import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MBC
import json, sys, random, os, openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
SEED=int(os.environ.get('SEED','7')); random.seed(SEED)   # fixed seed -> reproducible; scenarios use SAME seed so deltas aren't MC noise
BUDGET=2_000_000; CAP=50_000; MC=int(os.environ.get('MC','20')); BSCALE=400000
PRO={'Champion','Defender','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(MB_ROOT+r'\congestion.json'))}
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
wb=openpyxl.load_workbook(MB_ROOT+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; nrm=wb['Legislative Score - Normalized']
score=MBC.scores()   # PHASE-2: Python rank authority
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
CS=json.load(open(MB_ROOT+r'\category_stance.json'))['matrix']
bpf=MBC.bpf()
BETA_C=0.8   # bipartisan members get a coalition-seed boost (natural cross-aisle bridges)
prt=MBC.party()
cpf=MBC.cpf_diffusion
adj=MBC.load_network()
# RECEPTIVITY LAYER (2026-07-02): receiver susceptibility on edges + contingency-aware seed activation.
rc=MBC.rc
from moneyball_core import gate
P=MBC.build_P(adj)
idx={n:i for i,n in enumerate(members)}; NM=len(members)
_sm=MBC.sm64
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
from moneyball_core import blocks,BLOCKCAT
labels={sc:str(nrm.cell(1,sc).value).replace(' - Sponsor','').replace(' Sponsor','').strip() for sc in blocks}
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
    ev={n:(eng(sc,n)+0.15*score[n]/smax)*MBC.delivery_mult(n) for n in members}   # x say-do delivery discount (2026-07-07): don't court talkers at list price
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
MBC.dump_atomic(ALL,MB_ROOT+r'\per_topic_coalition%s.json'%tag)
print('\nwrote per_topic_coalition%s.json (seed %d, MC %d, %d sub-categories)'%(tag,SEED,MC,len(ALL)))
