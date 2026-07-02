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
BETA=1.5
cpf=MBC.cpf_diffusion
P={u:{v:(w*cpf(u,v))/(w*cpf(u,v)+6.0) for v,w in adj[u].items()} for u in members}   # bridge-amplified (L4)
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
def prime(v):
    tier=MAT.get(v,{}).get(cat)
    if tier not in THETA or tier in PRO: return None
    theta=THETA[tier]+max(0,-(C[v].get('net_lean') or 0)/120)        # money-captured members resist more
    pressure=sum(P[v].get(u,0) for u in proset if u in P[v])          # current pro pull from already-pro neighbors
    gap=theta-pressure
    if gap<=1e-6: return {'v':v,'tier':tier,'theta':round(theta,2),'pressure':round(pressure,2),'gap':round(gap,2),'cost':0,'money':0,'recruits':[]}
    money_only=dollars_for_units(v,min(0.97,gap))                     # $ to close whole gap with money alone
    avg_rate=money_only/min(0.97,gap)                                 # money's average $ per influence-unit
    # recruit not-yet-pro neighbors that are cheaper per unit than money; each adds P[u][v]
    cands=sorted([(P[v][u],u,CEDGE/max(0.1,P[v][u])) for u in P[v] if u not in proset],key=lambda x:x[2]/x[0])
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
