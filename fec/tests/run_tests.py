# -*- coding: utf-8 -*-
"""UNIT TESTS for the math kernels (architecture review 2026-07-02, roadmap #5).
Plain-assert style, zero dependencies:  python fec/tests/run_tests.py
Covers the documented invariants of moneyball_core, money_response, and flip_model —
the layer that makes calibration changes and refactors mechanically verifiable
(protocol: change -> run_tests -> run_pipeline -> zero rank delta -> audit clean)."""
import os,sys,importlib.util
FEC=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,FEC)
P=F=0
def ok(name,cond,detail=''):
    global P,F
    P,F=(P+1,F) if cond else (P,F+1)
    print(('  OK   ' if cond else 'FAIL  ')+name+(('  :: '+str(detail)) if (detail and not cond) else ''))

import moneyball_core as MC
print('[core: CRN kernel]')
xs=[MC.sm64(i) for i in range(5000)]
ok('sm64 in [0,1)',all(0<=x<1 for x in xs))
ok('sm64 deterministic',all(MC.sm64(i)==xs[i] for i in range(0,5000,97)))
ok('sm64 well-spread (mean ~0.5)',abs(sum(xs)/len(xs)-0.5)<0.02,sum(xs)/len(xs))
ok('sm64 key-independent (no order effect)',MC.sm64(12345)==MC.sm64(12345) and MC.sm64(1)!=MC.sm64(2))
print('[core: atomic dump]')
import tempfile,json as _json
_tf=os.path.join(tempfile.gettempdir(),'mb_atomic_test.json')
MC.dump_atomic({'a':1,'b':[2,3]},_tf,separators=(',',':'))
ok('dump_atomic writes valid json',_json.load(open(_tf))=={'a':1,'b':[2,3]})
_pre=set(os.listdir(tempfile.gettempdir()))
try: MC.dump_atomic({'x':object()},_tf)   # unserializable -> must raise and leave NO temp behind
except TypeError: pass
_leaked=[f for f in os.listdir(tempfile.gettempdir()) if f.endswith('.tmp') and f not in _pre]
ok('dump_atomic leaves original intact + no temp on failure',_json.load(open(_tf))=={'a':1,'b':[2,3]} and not _leaked)
os.remove(_tf)
print('[core: constants]')
ok('IMP has all 18 categories incl. CU Tax Status',len(MC.IMP)==18 and MC.IMP.get('CU Tax Status')==3.0)
ok('PERS silence == Ally parity (user-ratified 0.45)',MC.PERS['—']==0.45 and MC.PERS['—']<=MC.PERS['Highly Persuadable'])
ok('CFPB blocks folded (99+145)',sorted(MC.CATBLOCKS[99])==[99,145])
ok('SGATE monotone down the ladder',MC.SGATE['Highly Persuadable']>=MC.SGATE['True Neutral']>=MC.SGATE['Lean Skeptic']>=MC.SGATE['Skeptic']>=MC.SGATE['Opponent'])
print('[core: rosters + network]')
mem=MC.members()
ok('533 members',len(mem)==533,len(mem))
prt=MC.party()
ok('party coverage (no ? beyond a handful)',sum(1 for m in mem if prt[m]=='?')<=5,sum(1 for m in mem if prt[m]=='?'))
adj=MC.load_network()
ok('network symmetric',all(abs(adj[u][v]-adj[v][u])<1e-12 for u in list(adj)[:100] for v in adj[u]))
ok('no self-loops',all(u not in adj[u] for u in adj))
ok('all weights positive & sane',all(0<w<=10 for u in adj for w in adj[u].values()))
print('[core: physics]')
d,r=None,None
for a in mem:
    for b in mem[1:]:
        if prt.get(a)=='D' and prt.get(b)=='R': d,r=a,b; break
    if d: break
ok('cpf_diffusion cross-party dampened (<1), same-party 1.0',MC.cpf_diffusion(d,r)<1.0 and MC.cpf_diffusion(d,d)==1.0)
ok('cpf_pressure co-partisan 1.7 / out-partisan 0.5',MC.cpf_pressure(d,d)==1.7 and MC.cpf_pressure(d,r)==0.5)
Pk=MC.build_P(adj)
ok('cascade kernel probabilities in (0,1)',all(0<p<1 for u in Pk for p in Pk[u].values()))
print('[core: receptivity gate]')
gs=[MC.gate(m,{m:'Skeptic'}) for m in mem[:50]]+[MC.gate(m,{}) for m in mem[:50]]
ok('gate within [0.15, 0.90]',all(0.15<=g<=0.90 for g in gs),(min(gs),max(gs)))
ok('opponent gate < persuadable gate (same member)',MC.gate(mem[0],{mem[0]:'Opponent'})<MC.gate(mem[0],{mem[0]:'Highly Persuadable'}))

print('[money_response]')
def imp(n,f):
    s=importlib.util.spec_from_file_location(n,os.path.join(FEC,f)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
mr=imp('mr','money_response.py')
g='Jared Golden'
s1,s2,s4=mr.shift_lean(g,'cu',100000),mr.shift_lean(g,'cu',200000),mr.shift_lean(g,'cu',400000)
ok('saturating (concave) money curve',0<s1<s2<s4 and s2<2*s1 and s4<2*s2,(s1,s2,s4))
ok('bounded by MAXSHIFT x pressure x LOSSFRAME',abs(mr.shift_lean(g,'comp',10**9))<=mr.MAXSHIFT*1.60*mr.LOSSFRAME+1e-9)
ok('loss-frame asymmetry exact',abs(mr.shift_lean(g,'comp',100000)+mr.LOSSFRAME*s1)<1e-9)
ok('sub-threshold absorbed',mr.defection(g,-mr.DTHRESH*0.99) is None)
ok('defection outputs only valid rungs',all((mr.defection(m,-30) in (None,)+tuple(mr.ORDER)) for m in list(mr.C)[:100]))
ok('committed terminal rungs immune',all(mr.defection(m,-99) is None for m in mr.C if mr.PROJ.get(mr.OV.get(m),mr.OV.get(m)) in mr.COMMITTED))

print('[flip_model]')
fm=imp('fm','flip_model.py')
n=fm.members[0]
kw=dict(R_n=fm.R[n],nA_n=1.0,nB_n=1.0,mAt=2.0,mBt=2.0)
p0=fm.pflip(0,0,**kw); p1=fm.pflip(50000,0,**kw); p2=fm.pflip(0,50000,**kw)
ok('pflip in (0,1)',all(0<x<1 for x in (p0,p1,p2)))
ok('CU money raises pflip',p1>p0)
ok('industry money lowers pflip',p2<p0)
ok('receptivity scales money channel (pm=2 amplifies CU effect)',fm.pflip(50000,0,pm=2.0,**kw)>p1)

print('[say-do gate + delivery discount]')
# cap law invariants on a synthetic member (no workbook dependency: inject the corroboration cache)
MC._CORR={'__test__':{'sponsored':{'CFPB'},'advanced':{'CFPB'}}}
_cm={'CFPB':'Champion','Payments':'Champion','Interchange':'Defender','CU Tax Status':'Ally','TCPA':'Skeptic'}
_g,_cap,_prov=MC.cap_uncorroborated('__test__',_cm)
ok('uncorroborated Champion/Defender cap to Ally',_g['Payments']=='Ally' and _g['Interchange']=='Ally')
ok('corroborated Champion survives + earns proven',_g['CFPB']=='Champion' and _prov==['CFPB'])
ok('cap preserves raw tier and touches nothing else',_cap=={'Payments':'Champion','Interchange':'Defender'}
   and _g['CU Tax Status']=='Ally' and _g['TCPA']=='Skeptic')
MC._CORR={}   # empty evidence source -> fail-open (no caps)
_g2,_cap2,_=MC.cap_uncorroborated('__test__',_cm)
ok('missing evidence source fails OPEN (no caps)',_g2==_cm and not _cap2)
MC._CORR=None   # restore lazy loader
MC._DELIV={'talker':4.0,'mild':1.5,'doer':-2.0}
ok('delivery_mult bounds [0.70,1.00] + neutral fallback',
   MC.delivery_mult('talker')==0.70 and abs(MC.delivery_mult('mild')-0.925)<1e-9
   and MC.delivery_mult('doer')==1.0 and MC.delivery_mult('unknown-member')==1.0)
MC._DELIV=None

print('\nKERNEL TESTS — %d passed, %d FAILED'%(P,F))
sys.exit(1 if F else 0)
