import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MC
import json, sys, heapq, os, openpyxl
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
WM,WP=0.35,0.65; CAP=50000; BUDGET=2_000_000; INC=1000; BASE=0.15
# per-CATEGORY persuadability (same scale as overall PERS; '—' = no position on this issue)
# M5: '—' (no recorded position on this issue, ~60% of cells) lowered 0.55->0.45 so a silent member sits
# at PARITY with a known 'Ally' rather than ranking ABOVE one (silence is uncertainty, not enthusiasm).
# Kept identical to flip_model.py for grain consistency; env-overridable via PERS_NONE.
from moneyball_core import PERS
PRO={'Champion','Defender','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(MB_ROOT+r'\congestion.json'))}
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
wb=openpyxl.load_workbook(MB_ROOT+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; ra=wb['Rank & Allocation']; nrm=wb['Legislative Score - Normalized']
score=MC.scores()   # PHASE-2: Python rank authority
members=[m['member'] for m in C.values()]
ind={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
_iv=sorted(v for v in ind.values() if v>0); _imed=_iv[len(_iv)//2] if _iv else 0
# H3 (corrected via FEC re-verification): impute industry money ONLY for members with NO FEC record (receipts=0,
# truly blind). A member who raised money but shows ind=0 has a verified-real zero (no money from the 33 tracked
# major bank/finserv PACs) -- trust it, don't fabricate opposition. IMPUTE_IND0=0 disables imputation.
_imp0=os.environ.get('IMPUTE_IND0','1')!='0'
ind={n:(_imed if (_imp0 and (C[n].get('receipts') or 0)==0) else ind[n]) for n in members}
cu={n:(C[n]['cu'] or 0) for n in members}
HALFF=float(os.environ.get('HALFF','0.10'))   # capacity scale: money == HALFF*receipts -> half max money-pull (matches money_response + flip_model)
_rv=sorted((C[n].get('receipts') or 0) for n in members if (C[n].get('receipts') or 0)>0); _RMED=_rv[len(_rv)//2] if _rv else 200000
Rcap={n:(max((C[n].get('receipts') or 0),200000) if (C[n].get('receipts') or 0)>0 else _RMED) for n in members}   # HIGH-2: receipts=0 = MISSING -> impute median (not floor to $200k, which made no-record members cheapest to convert); matches money_response + flip_model
# PER-CATEGORY stance matrix (the 3rd dimension) -- drives camp/persuadability/proximity per issue
CS=json.load(open(MB_ROOT+r'\category_stance.json'))['matrix']
# network proximity
adj=MC.load_network()
# (moneyscale removed -- dead since the capacity-aware pflip rewrite)
# bipartisanship: a cross-party tie carries more flip-influence when BOTH ends are bridge-builders (taken seriously across the aisle)
prt=MC.party()
bpf=MC.bpf()
DIRECT=('--bridge' in sys.argv) or os.environ.get('BRIDGE')=='1'; GAMMA=1.2   # toggleable mode: directly prioritize bridge-builders in flip targeting
cpf=MC.cpf_pressure
# RECEPTIVITY LAYER (2026-07-02): money pressure scaled by pressure_mult (matches flip_model).
rc=MC.rc
def pflip(n,al,nA,nB,mAt,mBt):
    pm=rc(n,'pressure_mult')
    a=WM*pm*(cu[n]+al+1)/((cu[n]+al+1)+HALFF*Rcap[n])+WP*nA[n]/mAt   # capacity-aware saturating CU pull
    b=WM*pm*(ind[n]+1)/((ind[n]+1)+HALFF*Rcap[n])+WP*nB[n]/mBt        # ... and industry pull
    return a/(a+b) if a+b>0 else 0
# 18 legislative topic blocks -> the 17 matrix categories (CFPB Restrain+Reach share the combined CFPB stance)
from moneyball_core import blocks,BLOCKCAT
labels={sc:str(nrm.cell(1,sc).value).replace(' - Sponsor','').replace(' Sponsor','').strip() for sc in blocks}
nrow={nrm.cell(r,1).value:r for r in range(3,536) if nrm.cell(r,1).value}
eng={}
for sc in blocks:
    sw=[nrm.cell(2,sc+o).value or 0 for o in (0,2,4)]; d={}
    for n in members:
        r=nrow.get(n); d[n]=sum(sw[i]*(nrm.cell(r,sc+[0,2,4][i]).value or 0) for i in range(3)) if r else 0
    eng[sc]=d
smax=max(score.values()) or 1
def alloc_topic(sc):
    cat=BLOCKCAT[sc]
    cs={n:CS.get(n,{}).get(cat,'—') for n in members}                       # THIS issue's stance per member
    campT={n:('pro' if cs[n] in PRO else 'anti' if cs[n] in ANTI else 'neu') for n in members}
    nA={n:sum(w*cpf(n,u) for u,w in adj[n].items() if campT[u]=='pro') for n in members}   # bridge-amplified proximity to THIS issue's champions
    nB={n:sum(w*cpf(n,u) for u,w in adj[n].items() if campT[u]=='anti') for n in members}  # ... and opponents
    mAt=max(nA.values()) or 1; mBt=max(nB.values()) or 1
    tgt={n:(eng[sc][n]+BASE*score[n]/smax)*PERS[cs[n]]*((1+GAMMA*bpf[n]) if DIRECT else (1+0.3*bpf[n])) for n in members}  # strategic value x persuadability (x bridge boost when --bridge)
    al={n:0 for n in members}
    def marg(n): return 0.0 if al[n]>=CAP else tgt[n]*(pflip(n,al[n]+INC,nA,nB,mAt,mBt)-pflip(n,al[n],nA,nB,mAt,mBt))
    h=[(-marg(n),n) for n in members if tgt[n]>0]; heapq.heapify(h); spent=0
    while spent<BUDGET and h:
        g,n=heapq.heappop(h)
        if -g<=0: break
        al[n]+=INC; spent+=INC; heapq.heappush(h,(-marg(n),n))
    return al,spent,cs
def main():   # L3: guarded so importing this module for its functions doesn't run the pipeline / overwrite per_topic_alloc.json
    ALL={}
    print('PER-SUB-CATEGORY FLIP -- driven by PER-CATEGORY stance (topic-specific camp/persuadability/proximity):\n')
    for sc in blocks:
        al,sp,cs=alloc_topic(sc); top=sorted([(n,al[n]) for n in members if al[n]>0],key=lambda x:-x[1])
        ALL[labels[sc]]={n:al[n] for n,a in top}
        nch=sum(1 for n in members if cs[n] in PRO); nop=sum(1 for n in members if cs[n] in ANTI)
        print('%-30s ($%s, %d funded | %d pro/%d anti here): %s'%(labels[sc][:30],f'{sp:,}',len(top),nch,nop,
            ', '.join('%s $%dk'%(n.split()[-1],a//1000) for n,a in top[:4])))
    outf=MB_ROOT+r'\per_topic_alloc_bridge.json' if DIRECT else MB_ROOT+r'\per_topic_alloc.json'
    MC.dump_atomic(ALL,outf)
    print('\nwrote %s  (mode: %s, %d sub-categories)'%(os.path.basename(outf),'BRIDGE-BOOST' if DIRECT else 'baseline',len(ALL)))
if __name__=='__main__': main()
