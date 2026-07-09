import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MBC
"""Linear-Threshold priming (roadmap step 3, the flip/join side of the two models).
A member co-sponsors / flips when their PRO-influence clears their threshold:
    pressure(active pro neighbors) + money-influence  >=  theta(resistance)   [Linear Threshold]
For each persuadable target we solve for the CHEAPEST balance of network pressure (which neighbors to
recruit) and direct money (diminishing returns) that tips them over."""
import json, sys, os
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
TOPIC=os.environ.get('TOPIC','Mortgage')
CEDGE=float(os.environ.get('CEDGE','10000'))
MAXSHIFT=18.0; HALF=0.10; RFLOOR=200000          # money curve (shared with money_response.py)
PRO={'Champion','Defender','Ally'}
# requirement to flip, by current tier (units of pro-influence); committed opponents excluded
THETA={'Highly Persuadable':0.6,'True Neutral':1.0,'Neutral':1.0,'Lean Skeptic':1.5,'Skeptic':2.0,'Opponent':3.0,'Ally':0.0}   # CALIBRATED: widen resistance at the committed/opposed end (Bakker asymmetry; Kalla-Broockman ~0 on the opposed)
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}; members=list(C.keys())
bio2name={m['bioguide']:m['member'] for m in C.values() if m['bioguide']}
CS=json.load(open(B+r'\category_stance.json')); MAT=CS['matrix']; cats=CS['cats']
cat=[c for c in cats if TOPIC.lower() in c.lower()][0]
adj=MBC.load_network()
# L4: unify the diffusion kernel with the rest of the system (coalition/scenario/frontier use the
# bridge-amplified P=(w*cpf)/(w*cpf+4); this module previously used the un-amplified P=w/(w+4)). Adopt the
# amplified kernel so the pressure a primeable target feels from cross-party bridge neighbors matches the
# cascade -- one diffusion law everywhere.
bpf=MBC.bpf()
prt=MBC.party()
# N-1 (audit 2026-07-08): the ONE shared cascade kernel. build_P adds the receiver-susceptibility factor
# em(v)=edge_mult that this inline copy dropped -- the old P=(w*cpf)/(w*cpf+6) diverged from the live
# kernel by up to ~13%/edge (530/533 members have edge_mult!=1), silently feeding a divergent kernel into
# lt_priming.json despite this module's "one diffusion law everywhere" intent. (BETA was dead.)
P=MBC.build_P(adj)   # bridge-amplified (L4) + susceptibility-aware
# BAKKER CROSS-CUE SIGNING (lit-audit run-4j forward item, applied at the 2026-07-05 merge; BAKKER_XCUE=0
# reverts). Bakker-Lelkes-Malka (JOP): out-party cues do NOT persuade (null-to-backfire) — the kernel's
# unconditional 0.4 cross-party floor is exactly an attenuated-positive out-party cue. In the PRIMING
# pressure/recruit terms ONLY (kernel untouched): a cross-party pro-cue passes through sqrt(bpf_u*bpf_v),
# so perfect bridge pairs keep full influence (the kernel's own philosophy at cpf=1.0) and non-bridge
# out-party cues fall to ~0 (clamped at 0, never negative — backfire magnitude not invented). Mirrored in
# the dashboard JS port (make_dashboard_html_00.tpl prime()).
XCUE=os.environ.get('BAKKER_XCUE','1')!='0'
def xf(u,v): return 1.0 if (not XCUE or prt.get(u)==prt.get(v)) else (bpf.get(u,0.0)*bpf.get(v,0.0))**0.5
_rvals=sorted((C[m].get('receipts') or 0) for m in C if (C[m].get('receipts') or 0)>0); _RMED=_rvals[len(_rvals)//2] if _rvals else RFLOOR
def receipts(m):
    # HIGH-2 (ported 2026-07-01; the fix landed in money_response/flip_model/per_topic_flip but was missed here):
    # receipts=0 is MISSING data, not a tiny fundraiser -- flooring to $200k made the 18 no-record members look
    # ~5-10x cheaper to prime with money. Impute the MEDIAN so they read as typically movable.
    rr=C[m].get('receipts') or 0
    return max(rr,RFLOOR) if rr>0 else _RMED
def money_units(m,dollars):                         # net_lean shift -> pro-influence units (MAXSHIFT pts == 1 unit)
    r=dollars/receipts(m); return (MAXSHIFT*(r/(r+HALF)))/MAXSHIFT
def dollars_for_units(m,u):                         # invert: $ needed for u units of pro-influence (diminishing)
    u=min(u,0.98); return HALF*receipts(m)*u/(1-u)
proset={m for m in members if MAT.get(m,{}).get(cat) in PRO}
# ---- stance-integrity gates (user-ratified 2026-07-04; 'Lean Skeptic' explicitly carved out of every one) ----
# Root cause (the Warren sighting, July-1 artifact): single-cell myopia admitted a system-level Skeptic
# (overall tier, CFPB/FoM/Tech Opponent) as a True-Neutral Mortgage target AND as a pro-pressure recruit,
# and the net_lean resistance term only sees money-TAKERS — a PAC-free ideologue priced as CHEAP.
# Mirrored in the dashboard's in-browser port (make_dashboard_html_00.tpl prime/cheapestFlips).
BLOCK_OVERALL={'Skeptic','Highly Skeptical','Opponent'}   # kernel overall_tier read; overall 'Lean Skeptic' stays eligible
BLOCK_RECRUIT_CELL={'Skeptic','Opponent'}                 # topic-cell floor for recruits (the JS port already had this; 'Lean Skeptic' cell stays eligible)
COMMIT=0.25                                               # +theta per declared Opponent cell anywhere in the matrix — opposition breadth the money term can't see
OVT={m:MBC.overall_tier(MAT.get(m,{})) for m in members}
def recruit_cost(u):
    # CEDGE scaled by persuadability (kernel PERS, anchored so True Neutral == CEDGE exactly);
    # Lean Skeptic pinned to flat CEDGE — the carve-out: gates/pricing leave LS exactly as before
    t=MAT.get(u,{}).get(cat)
    if t=='Lean Skeptic': return CEDGE
    return CEDGE*0.50/max(0.05,MBC.PERS.get(t,MBC.PERS_NONE))
def prime(v):
    tier=MAT.get(v,{}).get(cat)
    if tier not in THETA or tier in PRO: return None
    if OVT.get(v) in BLOCK_OVERALL: return None                      # one mild topic cell can't make a system-level Skeptic a target
    theta=THETA[tier]+max(0,-(C[v].get('net_lean') or 0)/120)        # money-captured members resist more
    theta+=COMMIT*sum(1 for t in MAT.get(v,{}).values() if t=='Opponent')   # ideological commitment resists too (PAC-free opponents no longer read cheap)
    pressure=sum(P[v].get(u,0)*xf(u,v) for u in proset if u in P[v])  # pro pull; cross-party cues bridge-gated (Bakker)
    gap=theta-pressure
    if gap<=1e-6: return {'v':v,'tier':tier,'theta':round(theta,2),'pressure':round(pressure,2),'gap':round(gap,2),'cost':0,'money':0,'recruits':[]}
    money_only=dollars_for_units(v,min(0.97,gap))                     # $ to close whole gap with money alone
    avg_rate=money_only/min(0.97,gap)                                 # money's average $ per influence-unit
    # recruit not-yet-pro neighbors that are cheaper per unit than money; each adds P[u][v].
    # Stance floors (2026-07-04): the model may not enlist as a pro-advocate a member its own stance law
    # calls opposed — no Skeptic/Opponent topic cell, no Skeptic-or-worse overall read (Lean Skeptic allowed).
    cands=sorted([(P[v][u]*xf(u,v),u,recruit_cost(u)/max(0.1,P[v][u]*xf(u,v))) for u in P[v]
                  if u not in proset and MAT.get(u,{}).get(cat) not in BLOCK_RECRUIT_CELL
                  and OVT.get(u) not in BLOCK_OVERALL and P[v][u]*xf(u,v)>1e-6],key=lambda x:x[2]/x[0])
    got=0.0; cost=0.0; recruits=[]
    for add,u,c in cands:
        if got>=gap: break
        if c/add<avg_rate: got+=add; cost+=c; recruits.append((u,round(add,2)))
    resid=max(0.0,gap-got)
    if resid>0.97: return None                                       # money can't close (>1 unit residual) -> not primeable on money alone
    money=round(dollars_for_units(v,resid)) if resid>1e-6 else 0
    cost+=money
    return {'v':v,'tier':tier,'theta':round(theta,2),'pressure':round(pressure,2),'gap':round(gap,2),
            'cost':round(cost),'money':money,'recruits':recruits}
res=[r for r in (prime(v) for v in members) if r and r['cost']>0]
res.sort(key=lambda r:r['cost'])
print('LT PRIMING — issue: %s | %d pro, %d primeable targets'%(cat,len(proset),len(res)))
print('Cheapest members to tip into co-sponsoring (pressure + money balance):')
MBC.dump_atomic(res,B+r'\lt_priming.json')
print('%-22s %-18s %5s %5s   %10s = %9s money + pressure(recruit)'%('member','tier','gap','press','TOTAL$',''))
for r in res[:14]:
    rc=', '.join('%s'%u.split()[-1] for u,a in r['recruits'][:3]) or '—'
    print('   %-22s [%-16s] %.2f %.2f  $%-8s = $%-7s + recruit %s'%(
        r['v'][:22],r['tier'],r['gap'],r['pressure'],f"{r['cost']:,}",f"{r['money']:,}",rc))
