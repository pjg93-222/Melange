import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
from moneyball_core import dump_atomic   # S2-03: crash-safe artifact write
"""ADAPTIVE BUDGET OPTIMIZER (Golovin & Krause, "Adaptive Submodularity").
Greedily allocates a CU budget across members to maximize total Linear-Threshold winnability
(sum over topics of expected weighted flips).  The objective is monotone & submodular in the
allocation (pflip has sqrt-diminishing returns), so a LAZY (CELF) greedy is near-optimal — the
(1-1/e) guarantee.  ADAPTIVE: as we spend, a member whose cumulative CU crosses their money-response
defection threshold CONVERTS (joins the pro coalition); we observe that, update the stance, and
re-optimize the remaining budget (an adaptive policy, not a fixed plan).

Usage:  python optimize.py            (default $2M, all issues)
        BUDGET=1000000 INC=25000 python optimize.py
        TOPIC=Interchange python optimize.py     (optimize one issue's winnability)
"""
import sys, os, heapq, collections, importlib.util
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
def imp(n,f): s=importlib.util.spec_from_file_location(n,B+r'\fec\%s'%f); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
fm=imp('fm','flip_model.py'); mr=imp('mr','money_response.py')
BUDGET=int(os.environ.get('BUDGET','2500000')); INC=int(os.environ.get('INC','500'))   # TOTAL pot ~$2.5M (user 2026-07-01) -- THE joint allocation across all 17 issues (per-topic tools are per-issue diagnostics, not additive budgets). INC = allocation granularity ($500 = realistic contribution step)
PMAX=int(os.environ.get('PMAX','10000'))   # per-member max = FEC PAC->candidate per-cycle limit (~$10k: $5k primary + $5k general). No candidate can legally take more.
OUTF=os.environ.get('OPT_OUT',B+r'\optimize_result.json')   # audits pass OPT_OUT=<tmp> so test runs don't clobber the production result
ONLY=os.environ.get('TOPIC')
cats=[c for c in fm.cats if (not ONLY or ONLY.lower() in c.lower())]
members=fm.members
MAT={m:dict(fm.CS0[m]) for m in members}; cu=dict(fm.cu0); ind=dict(fm.ind0)
won=set(); secured=0.0      # H1: members WON via conversion are realized (their flip banked in `secured`) and leave the flippable pool
CTORD=['Champion','Defender','Ally','Highly Persuadable','True Neutral','Lean Skeptic','Skeptic','Opponent']
def marg(m):                                      # marginal winnability from +INC CU on m (only m's pflip moves), across topics where m is a target
    if m in won or cu[m]+INC>fm.cu0[m]+PMAX: return 0.0   # a won member is realized (no more spend); per-member cap requires room for a FULL chunk (never overshoot the FEC limit when INC does not divide PMAX)
    g=0.0; pm=fm.rc(m,'pressure_mult')
    for c in cats:
        cs,campT,nA,nB,mAt,mBt,tgt=fm.topic_setup(c,MAT)
        if tgt[m]<=0: continue
        g+=tgt[m]*(fm.pflip(cu[m]+INC,ind[m],fm.R[m],nA[m],nB[m],mAt,mBt,pm)-fm.pflip(cu[m],ind[m],fm.R[m],nA[m],nB[m],mAt,mBt,pm))
    return g
def total_winnability(): return sum(fm.flip_value(c,MAT,cu,ind) for c in cats)
def unwon_winnability():                          # winnability over members NOT yet won (won members are realized -> in `secured`)
    t=0.0
    for c in cats:
        cs,campT,nA,nB,mAt,mBt,tgt=fm.topic_setup(c,MAT)
        t+=sum(tgt[n]*fm.pflip(cu[n],ind[n],fm.R[n],nA[n],nB[n],mAt,mBt,fm.rc(n,'pressure_mult')) for n in members if n not in won)
    return t
def shift_pro(m,steps):                           # a converted member improves toward pro on their movable positions
    # M2: `steps` is derived from the OVERALL 5-tier spectrum (dlean//DTHRESH) but advances tiers in the
    # finer per-category 8-tier CTORD -- the cross-taxonomy magnitude mapping is unjustified (one coarse
    # step != one fine step). A single money-triggered defection is one disposition nudge; cap the
    # per-category move at 1 fine tier so the magnitude is defensible and robust to DTHRESH/MAXSHIFT env
    # changes (env-tunable via CONV_MAXSTEP for callers who want a larger move).
    steps=min(steps,int(os.environ.get('CONV_MAXSTEP','1')))
    moved=[]
    for c in cats:
        t=MAT[m].get(c)
        if t in CTORD and t not in ('Champion','Defender','Opponent'):
            j=max(0,CTORD.index(t)-steps)
            if CTORD[j]!=t: MAT[m][c]=CTORD[j]; moved.append(c)
    return moved
def dd_bound(val_now):
    # Golovin-Krause DATA-DEPENDENT optimality bound (JAIR'11 Lemma 5.3 / A.9): from the current observed
    # state, NO policy spending <= BUDGET can gain more than the budget-filling sum of current per-chunk
    # marginals -- by concavity a member's later chunks each gain <= their current next-chunk marginal, and
    # a member can absorb at most their PMAX headroom. The run is deterministic (no stochastic observations),
    # so the bound is valid at every state; we report the tightest of start/end. Much tighter than the
    # worst-case (1-1/e)=63.2% guarantee.
    cand=sorted(((marg(m),(fm.cu0[m]+PMAX-cu[m])//INC) for m in members if m not in won),reverse=True)
    left=BUDGET//INC; z=0.0
    for g,nch in cand:
        if left<=0 or g<=1e-12: break
        t=min(int(nch),left); z+=t*g; left-=t
    return val_now+z
base=total_winnability(); cur=base
bound0=dd_bound(base)   # bound on OPT($BUDGET) from the initial state
alloc=collections.Counter(); spent=0; conversions=[]; converted=set(); path=[(0,round(base,3))]
pq=[(-marg(m),m,0) for m in members]; heapq.heapify(pq); step=0
while spent<BUDGET and pq:
    neg,m,le=heapq.heappop(pq)
    if -neg<=1e-12: break                         # no positive marginal left
    if le==step:
        alloc[m]+=INC; cu[m]+=INC; spent+=INC; cur+=-neg; step+=1
        # ADAPTIVE observation: did the cumulative CU on m convert them?
        converted_now=False
        if m not in converted:
            added=cu[m]-fm.cu0[m]; nv=mr.defection(m,mr.shift_lean(m,'cu',added))
            if nv and mr.OV.get(m) not in ('Champion','Opponent'):
                steps=int(abs(mr.shift_lean(m,'cu',added))//mr.DTHRESH)
                contrib=sum(fm.topic_setup(c,MAT)[6][m] for c in cats)   # H1: bank m's flip at certainty (winning is a GAIN, not the old persuadability-loss)
                mv=shift_pro(m,steps); converted.add(m); won.add(m); secured+=contrib; conversions.append((m,added,nv,mv))
                fm._cache.clear(); cur=secured+unwon_winnability()       # re-optimize: m realized into `secured`, others' proximity updated
                pq=[(-marg(x),x,0) for x in members]; heapq.heapify(pq); step=0; converted_now=True
        path.append((spent,round(cur,3)))
        # re-queue m for a further INC (multi-increment greedy: a high-value member accumulates up to PMAX in
        # $500 steps as its marginal stays competitive). Skip if it just converted (pq already rebuilt) or hit cap.
        if not converted_now and m not in won and cu[m]+INC <= fm.cu0[m]+PMAX:
            heapq.heappush(pq,(-marg(m),m,step))
    else:
        heapq.heappush(pq,(-marg(m),m,step))
# diminishing-returns knee (last $ whose per-chunk marginal >= 20% of peak). MEDIUM-2: a min-chunk thin spread
# keeps every marginal near-flat, so a "knee" often does not exist within budget -- report that honestly rather
# than implying the knee sits exactly at the full budget. Conversion jumps are excluded from the marginal series.
margs=[path[i][1]-path[i-1][1] for i in range(1,len(path))]; peak=max(margs) if margs else 0
knee=0
for i,g in enumerate(margs):
    if g>=0.20*peak: knee=(i+1)*INC
knee_found = 0<knee<spent           # a real knee means returns fell off BEFORE the budget was exhausted
top=sorted(alloc.items(),key=lambda kv:-kv[1])
print('ADAPTIVE OPTIMIZER — budget $%s, INC $%s%s'%(f'{BUDGET:,}',f'{INC:,}',' | issue: '+ONLY if ONLY else ' | all %d issues'%len(cats)))
kmsg=('knee at $%s'%f'{knee:,}') if knee_found else 'no diminishing-returns knee within budget (marginals stay flat -- thin spread)'
print('total winnability %.2f -> %.2f  (+%.2f expected flips)  | %s'%(base,cur,cur-base,kmsg))
opt_bound=min(bound0,dd_bound(cur))
print('G-K data-dependent certificate: OPT($%s) <= %.2f -> greedy gain is >= %.1f%% of any policy\'s gain (worst-case floor: 63.2%%)'%(
    f'{BUDGET:,}',opt_bound,100*(cur-base)/max(opt_bound-base,1e-9)))
print('\nTop CU allocations:')
for m,v in top[:14]: print('   %-24s $%-9s%s'%(m,f'{v:,}','  [CONVERTED->coalition]' if m in converted else ''))
print('\nADAPTIVE CONVERSIONS observed (cumulative CU crossed their defection threshold -> joined coalition):')
for m,a,nv,mv in conversions[:12]: print('   %-22s at $%-8s -> %s (improved on %d issues)'%(m,f'{int(a):,}',nv,len(mv)))
if not conversions: print('   (none at this budget)')
dump_atomic({'budget':BUDGET,'base':base,'final':cur,'opt_bound':round(opt_bound,3),'knee':knee,'alloc':dict(alloc),'conversions':[(m,a,nv) for m,a,nv,_ in conversions],'path':path},OUTF)
print('\nwrote %s (frontier + allocation + conversions)'%os.path.basename(OUTF))
