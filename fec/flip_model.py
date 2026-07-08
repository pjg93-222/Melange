import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MC
"""Shared Linear-Threshold flip model (imported by scenario.py and optimize.py).
Winnability of a member on a topic:  pflip(n) = a/(a+b),
  a = WM*sqrt(cu+alloc)/scale + WP*(bridge-amplified proximity to THIS issue's champions)
  b = WM*sqrt(ind)/scale      + WP*(bridge-amplified proximity to THIS issue's opponents)
CU money raises a (with sqrt-diminishing returns), competitor money raises b.
Expected flips on a topic = sum_n tgt(n)*pflip(n).  Faithful to per_topic_flip.py.
"""
import json, os, openpyxl
B=MB_ROOT
WM,WP=0.35,0.65; CAP=50000; BASE=0.15   # CALIBRATED: money is the minority partner to peer/network influence (money buys access/effort > votes — Ansolabehere; Hall&Wayman; Kalla&Broockman)
# M5: '—' = member has taken NO recorded position on THIS issue, which is 59.8% of matrix cells.
# At the old 0.55 a silent member ranked as MORE persuadable than a known 'Ally' (0.45) -- conceptually
# backwards: a declared Ally has already signaled sympathy, whereas silence is honest uncertainty, not
# enthusiasm. Sensitivity test (—∈{0.30,0.45,0.55,0.75,0.95}): total winnability ran 149.5->245.8 (the
# value scales the whole objective since '—' dominates), and top-20 overlap vs 0.55 was 16/18/20/18/15 --
# the extremes (esp. 0.95) pulled record-less freshmen up the board. We set 0.45 so a silent member sits
# at PARITY with a known Ally (uncertain, not presumed eager) and never outranks one. Judgment dial,
# env-overridable via PERS_NONE.
from moneyball_core import PERS   # single copy (was drift-prone x5)
PRO={'Champion','Defender','Ally'}; ANTI={'Opponent','Skeptic'}
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}
members=[m['member'] for m in C.values()]
HALFF=float(os.environ.get('HALFF','0.10'))   # capacity scale: money == HALFF*receipts -> half the max money-pull (reconciles with money_response)
_rv=sorted((C[n].get('receipts') or 0) for n in members if (C[n].get('receipts') or 0)>0); _RMED=_rv[len(_rv)//2] if _rv else 200000
R={n:(max((C[n].get('receipts') or 0),200000) if (C[n].get('receipts') or 0)>0 else _RMED) for n in members}   # HIGH-2: receipts=0 is MISSING data -> impute MEDIAN (floor only real small fundraisers). Flooring no-record members to $200k had made them the CHEAPEST to convert / most winnable. Matches money_response.receipts().
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
cu0={n:(C[n]['cu'] or 0) for n in members}; ind0={n:(C[n]['banks'] or 0)+(C[n]['finserv'] or 0) for n in members}
# H3 (CORRECTED after FEC re-verification): impute industry money ONLY for members with NO FEC fundraising record
# at all -- receipts=0, i.e. TRULY BLIND (new/special-election winners, unresolved joins; 18 members). A member who
# RAISED money but shows ind=0 has a VERIFIED-REAL zero: the FEC gap-test (itpas2.txt, 24K/24Z) confirmed their $0
# from the 33 tracked major bank/finserv PACs (ABA/Citi/Wells/JPM/BofA/Visa/MC/Amex...) is genuine -- 91 such members,
# heavily no-corporate-PAC Democrats; their other "industry" money is insurance / false-positives (END CITIZENS
# UNITED matched on "citi"), not banks. Imputing those would FABRICATE bank opposition they don't have, so we trust
# the real zero (it correctly means "not captured by the banking industry"). IMPUTE_IND0=0 disables imputation.
_iv=sorted(v for v in ind0.values() if v>0); _imed=_iv[len(_iv)//2] if _iv else 0
ind_imputed={n for n in members if (C[n].get('receipts') or 0)==0} if os.environ.get('IMPUTE_IND0','1')!='0' else set()
ind0={n:(_imed if n in ind_imputed else ind0[n]) for n in members}
nodata=set(ind_imputed)   # truly-blind members (no FEC record): winnability is imputed, not measured
wb=openpyxl.load_workbook(B+r'\Moneyball Main Version - Blended.xlsx',data_only=True)
bm=wb['Blended Model']; nrm=wb['Legislative Score - Normalized']
score=MC.scores(); smax=max(score.values()) or 1   # PHASE-2: Python rank authority (ranks_python.json), not the workbook view
CS0=json.load(open(B+r'\category_stance.json'))['matrix']
adj=MC.load_network()
# (moneyscale removed -- dead since the capacity-aware pflip rewrite; CU pull is now receipts-relative, not /moneyscale)
prt=MC.party()
bpf=MC.bpf()
cpf=MC.cpf_pressure   # named physics (was ambiguous 'cpf' x8)
from moneyball_core import blocks,BLOCKCAT
cat2sc={}
for sc in blocks: cat2sc.setdefault(BLOCKCAT[sc],sc)
# M3: two legislative blocks map to the single 'CFPB' category -- 99 (CFPB Restrain) and 145 (CFPB Reach).
# The combined CFPB STANCE already merges both (category_stance.json), but the legislative `eng` signal here
# previously kept block 99 ONLY (cat2sc.setdefault dropped 145), discarding CFPB-Reach engagement. Fold both
# blocks INTO the CFPB eng signal so the engagement grain matches the combined-stance grain and no signal is
# lost. cat2blocks lists every contributing block per canonical category sc.
cat2blocks={sc:[b for b in blocks if BLOCKCAT[b]==BLOCKCAT[sc]] for sc in set(cat2sc.values())}
nrow={nrm.cell(r,1).value:r for r in range(3,536) if nrm.cell(r,1).value}
eng={}
for sc in set(cat2sc.values()):
    d={n:0.0 for n in members}
    for blk in cat2blocks[sc]:                                  # sum engagement across all blocks for this category (CFPB: 99+145)
        sw=[nrm.cell(2,blk+o).value or 0 for o in (0,2,4)]
        for n in members:
            r=nrow.get(n)
            if r: d[n]+=sum(sw[i]*(nrm.cell(r,blk+[0,2,4][i]).value or 0) for i in range(3))
    eng[sc]=d
def camp(t): return 'pro' if t in PRO else 'anti' if t in ANTI else 'neu'
# RECEPTIVITY LAYER (2026-07-02): pressure_mult scales how hard MONEY pressure lands on this member
# (Byrne susceptibility x F&H electoral incentive x Linde-Vis PT domain); peer channel is handled by
# edge_mult inside the cascade engines. Neutral fallback = legacy.
rc=MC.rc
def pflip(cu_n,ind_n,R_n,nA_n,nB_n,mAt,mBt,pm=1.0):
    # capacity-aware saturating money pull (Michaelis-Menten form): $X moves a big-receipts member less,
    # diminishes within a member, and matches money_response's curve -> one consistent diminishing-returns model.
    a=WM*pm*(cu_n+1)/((cu_n+1)+HALFF*R_n)+WP*nA_n/mAt
    b=WM*pm*(ind_n+1)/((ind_n+1)+HALFF*R_n)+WP*nB_n/mBt
    return a/(a+b) if a+b>0 else 0.0
_cache={}
def topic_setup(cat,MAT):
    """Fixed parts for a topic given stance (camp, proximity nA/nB, target value tgt). Cached per stance signature."""
    sc=cat2sc[cat]; sig=(cat,tuple(MAT[n].get(cat,'—') for n in members))
    if sig in _cache: return _cache[sig]
    cs={n:MAT[n].get(cat,'—') for n in members}; campT={n:camp(cs[n]) for n in members}
    nA={n:sum(w*cpf(n,u) for u,w in adj[n].items() if campT[u]=='pro') for n in members}
    nB={n:sum(w*cpf(n,u) for u,w in adj[n].items() if campT[u]=='anti') for n in members}
    mAt=max(nA.values()) or 1; mBt=max(nB.values()) or 1
    tgt={n:(eng[sc][n]+BASE*score[n]/smax)*PERS[cs[n]]*(1+0.3*bpf[n])*MC.delivery_mult(n) for n in members}   # +PASSAGE bonus (Volden-Wiseman +8-14%); x say-do delivery discount (2026-07-07): a talker's expected value priced down up to 30%
    r=(cs,campT,nA,nB,mAt,mBt,tgt); _cache[sig]=r; return r
def flip_value(cat,MAT,cu_state,ind_state):
    """Expected weighted flips on a topic = sum tgt*pflip, given a money state."""
    cs,campT,nA,nB,mAt,mBt,tgt=topic_setup(cat,MAT)
    return sum(tgt[n]*pflip(cu_state[n],ind_state[n],R[n],nA[n],nB[n],mAt,mBt,rc(n,'pressure_mult')) for n in members)
cats=list(cat2sc.keys())
