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
import bill_rules as BR
import stance_rules as SR
import media_rules as MR
import influence_roles as IR
from member_identity import Resolver
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
_txt=_tf+'.html'; MC.write_text_atomic('<b>complete</b>',_txt)
ok('write_text_atomic writes complete text',open(_txt,encoding='utf-8').read()=='<b>complete</b>')
os.remove(_txt)
import openpyxl as _ox
_xf=_tf+'.xlsx'; _tw=_ox.Workbook(); _tw.active['A1']='complete'; MC.save_workbook_atomic(_tw,_xf)
_tr=_ox.load_workbook(_xf,read_only=True,data_only=True)
ok('save_workbook_atomic writes a readable verified workbook',_tr.active['A1'].value=='complete')
_tr.close(); os.remove(_xf)
os.remove(_tf)
print('[core: constants]')
ok('IMP has all 18 categories incl. CU Tax Status',len(MC.IMP)==18 and MC.IMP.get('CU Tax Status')==3.0)
ok('PERS silence == Ally parity (user-ratified 0.45)',MC.PERS['—']==0.45 and MC.PERS['—']<=MC.PERS['Highly Persuadable'])
ok('CFPB blocks folded (99+145)',sorted(MC.CATBLOCKS[99])==[99,145])
ok('SGATE monotone down the full ladder',
   all(MC.SGATE[a]>=MC.SGATE[b] for a,b in zip(
       ('Highly Persuadable','Persuadable','Lean Persuadable','True Neutral','Lean Skeptic','Skeptic','Highly Skeptical'),
       ('Persuadable','Lean Persuadable','True Neutral','Lean Skeptic','Skeptic','Highly Skeptical','Opponent'))))
ok('auto-repair SMART Acts excluded even when source title is ambiguous',
   BR.excluded_bill('H.R.3664',117,'SMART Act','') and
   BR.excluded_bill('H.R.1707',118,'SMART Act',''))
ok('financial/regulatory SMART Acts remain included',
   not BR.excluded_bill('S.2801',117,'SMART Act of 2022','') and
   not BR.excluded_bill('S.4264',118,'SMART Act of 2024','') and
   not BR.excluded_bill('H.R.4437',119,'Supervisory Modifications for Appropriate Risk-based Testing Act',''))
_elite={'role_type':'party_elite','influence_bonus':1.5}
ok('Influence bonus is limited to party elites',
   IR.eligible_bonus(_elite,'Banking (full) [Highly]')[0]==1.5 and
   IR.eligible_bonus({'role_type':'constitutional_officer','influence_bonus':1},'')[0]==0)
ok('committee Chair/Ranking overlap zeros the party-elite bonus',
   IR.eligible_bonus(_elite,'Finance (full) [Highly/Chair]')[0]==0 and
   IR.eligible_bonus(_elite,'Banking (full) [Highly/Ranking]')[0]==0)
print('[stance: fixed bands + bounded rounding]')
ok('same thresholds in every domain; only top label changes',
   SR.classify(.70,True,False)=='Champion' and SR.classify(.70,True,True)=='Defender' and
   SR.classify(.34,True,False)=='Highly Persuadable' and SR.classify(-.11,True,True)=='Lean Skeptic')
ok('all ten fixed tiers are reachable without a curve',
   [SR.classify(x) for x in (.70,.35,.25,.15,.05,0,-.10,-.20,-.50,-.80)]==
   ['Champion','Ally','Highly Persuadable','Persuadable','Lean Persuadable','True Neutral',
    'Lean Skeptic','Skeptic','Highly Skeptical','Opponent'])
ok('positive scores cannot be skeptic and negative scores cannot be highly persuadable',
   all(SR.classify(x) not in ('Lean Skeptic','Skeptic','Opponent') for x in (.001,.099,.1,.69,1.0)) and
   all(SR.classify(x) not in ('Highly Persuadable','Ally','Champion') for x in (-.001,-.099,-.1,-.69,-1.0)))
ok('no-signal stance remains em dash',SR.classify(.99,False)=='—' and MC.overall_tier({})=='—')
ok('missing media does not dilute present sponsored-legislation evidence',
   SR.combine_evidence({'legislation':.86,'media':None,'vote':None},
                       {'legislation':.55,'media':.35,'vote':.10})==.86)
_near={'Examination & Supervision':'Champion','CU Capital Requirements':'Champion',
       'Technology & Emerging':'Champion','Fraud Prevention':'Champion','Charter Modernization':'Champion',
       'CFPB':'Champion','Member Business Lending':'Champion','Data Privacy & Cyber':'Ally',
       'Credit Card Mandates':'Ally','Mortgage & Housing':'Ally','Interchange':'Highly Persuadable',
       'Defense CU Issues':'Highly Persuadable','Payments':'True Neutral'}
ok('overall exceptional-performance rounding is bounded and can resolve a near boundary',
   MC.overall_rounding(_near)==.05 and MC.overall_tier(_near)=='Champion')
_opp_probe={'hs%d'%i:'Highly Skeptical' for i in range(4)}; _opp_probe['opp']='Opponent'
ok('overall Opponent cutoff is ordered, provenance-visible, and reachable',
   MC.OVERALL_BANDS[-2][0]>MC.OVERALL_OPPONENT_CUTOFF and
   MC.overall_thresholds()['bands'][-1]['minimum']==MC.OVERALL_OPPONENT_CUTOFF and
   MC.overall_tier(_opp_probe)=='Opponent')
_adj,_fac=SR.exceptional_rounding({'a':.69,'b':.9,'c':-.8,'empty':0},{'a':1,'b':1,'c':1,'empty':0})
ok('exceptional rounding is bounded, sign-aware, and never fills empty domains',
   all(abs(v)<=SR.ROUNDING_CAP+1e-12 for v in _fac.values()) and _fac['empty']==0 and _adj['empty']==0)
print('[media: shared routing + signed normalization + General CU exclusion]')
ok('General CU subject words route to a real policy domain',
   MR.route_raw_categories('Credit unions help underserved rural communities')==['Field of Membership'])
_norm=MR.normalize_signed_extrema({'A':8,'B':2,'C':-10,'D':-2.5,'E':0})
ok('domain normalization preserves relative signed magnitude',
   _norm=={'A':1.0,'B':.25,'C':-1.0,'D':-.25,'E':0.0})
_general=MR.general_exclusion_ledger({'A':.8,'B':0,'C':-.4})
ok('residual General CU evidence is explicit and never projected into policy domains',
   set(_general)=={'A','C'} and all(not a['applied_to_policy_domains'] for a in _general.values()))
print('[identity: fail-closed joins]')
_ir=Resolver(['John Smith','Jane Smith','Tim Scott'],{'Tim Scott':'S001184'})
ok('identity resolver accepts exact, Last/First, and bioguide matches',
   _ir.resolve('Scott, Tim')=='Tim Scott' and _ir.resolve(None,'S001184')=='Tim Scott')
ok('identity resolver rejects an ambiguous surname instead of taking first roster row',
   _ir.resolve('Smith') is None and _ir.resolve('X. Smith') is None)
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
# Cap law invariants on a synthetic member. Committee office is intentionally not an action path.
MC._CORR={'__test__':{'sponsored':{'CFPB'},'advanced':{'CFPB'}}}
MC._VOTECORR={'__test__':{'Payments'}}
_cm={'CFPB':'Champion','Payments':'Champion','Interchange':'Defender','CU Tax Status':'Champion','TCPA':'Skeptic'}
_g,_cap,_prov,_cor=MC.cap_uncorroborated('__test__',_cm)
ok('authored Champion survives + earns proven (Path A)',_g['CFPB']=='Champion' and _prov==['CFPB'] and _cor.get('CFPB')=='A')
ok('recorded floor vote corroborates (Path V)',_g['Payments']=='Champion' and _cor.get('Payments')=='V')
ok('committee title does not substitute for action',_g['CU Tax Status']=='Ally' and 'CU Tax Status' in _cap)
ok('uncorroborated top cells cap to Ally, raw preserved',
   _g['Interchange']=='Ally' and _cap=={'Interchange':'Defender','CU Tax Status':'Champion'})
ok('cap touches nothing else',_g['TCPA']=='Skeptic')
_ov,_od=MC.overall_say_do_gate('__test__',_g,_cm,_cor)
ok('overall Champion requires delivery in at least two-thirds of raw top cells',
   _od['raw']=='Champion' and _ov=='Ally' and _od['delivery_ratio']==.5)
MC._CORR['__test__']['sponsored'].update({'Technology & Emerging','Fraud Prevention'})
_raw6={'CFPB':'Champion','Payments':'Champion','Technology & Emerging':'Champion',
       'Fraud Prevention':'Champion','Interchange':'Defender','CU Tax Status':'Champion'}
_g3,_c3,_p3,_r3=MC.cap_uncorroborated('__test__',_raw6)
_ov3,_od3=MC.overall_say_do_gate('__test__',_g3,_raw6,_r3)
ok('six top domains with two-thirds delivered clear the aggregate say-do rule',
   len(_od3['top_cells'])==6 and _od3['delivery_ratio']>=2/3 and _ov3=='Champion')
MC._CORR['__test__']['direct_sponsored_bills']={('H.R.%d'%i,'119') for i in range(10)}
MC._CORR['__test__']['advanced_direct_bills']={('H.R.0','119'),('H.R.1','119')}
_ov4,_od4=MC.overall_say_do_gate('__test__',_g3,_raw6,_r3)
ok('fixed high-volume low-followthrough rule caps an introduced-only paper trail',
   _ov4=='Ally' and 'high_volume_low_followthrough' in _od4['cap_reasons'])
MC._CORR['__test__']['direct_sponsored_bills']={('H.R.%d'%i,'119') for i in range(20)}
_r5={c:'A' for c in _raw6}
_ov5,_od5=MC.overall_say_do_gate('__test__',_raw6,_raw6,_r5)
ok('exceptional direct authorship with full domain delivery clears the paper-trail cap',
   _ov5=='Champion' and _od5['exceptional_authorship_override'] and not _od5['cap_reasons'])
MC._CORR={}   # empty authorship source -> fail-open (no caps), regardless of vote file
_g2,_cap2,_,_=MC.cap_uncorroborated('__test__',_cm)
_ov2,_od2=MC.overall_say_do_gate('__test__',_g2,_cm,{})
ok('missing evidence source fails OPEN (no cell or overall caps)',_g2==_cm and not _cap2 and _ov2=='Champion')
MC._CORR=None; MC._VOTECORR=None   # restore lazy loaders
MC._DELIV={'talker':4.0,'mild':1.5,'doer':-2.0}
ok('delivery_mult bounds [0.70,1.00] + neutral fallback',
   MC.delivery_mult('talker')==0.70 and abs(MC.delivery_mult('mild')-0.925)<1e-9
   and MC.delivery_mult('doer')==1.0 and MC.delivery_mult('unknown-member')==1.0)
MC._DELIV=None

print('[CHRG attribution + ordinary-questioning guards]')
cr=imp('cr','fetch_congressional_record.py')
_hearing='''OPENING STATEMENT OF HON. FRENCH HILL, A REPRESENTATIVE
Chairman Hill. This opening statement is deliberately long and must never enter the ordinary question-period corpus even though it resembles member speech in every mechanical way.
STATEMENT OF SUSANNAH MARSHALL, BANK COMMISSIONER
Ms. Marshall. This witness testimony is deliberately long and must never be attributed to a current member who happens to have the same surname as this witness.
[The prepared statement of Ms. Marshall follows:]
Chairman Hill. I recognize myself for five minutes for questions. This is the live question-period member turn and it is deliberately long enough to clear the procedural-fragment floor. Ms. Marshall, what do you think about this policy and how should Congress respond to it?
Ms. Marshall. This witness answer is deliberately long enough that only the explicit witness-surname guard, rather than the length threshold, can prevent its admission to the member corpus.
QUESTIONS SUBMITTED BY MEMBERS POST HEARING
Chairman Hill. This written question is deliberately long but belongs to the post-hearing appendix and therefore must not enter the live question-period corpus.'''
ok('comma direct-address is not a speaker label',
   not any(m.group(2)=='Marshall' for m in cr.TURN.finditer('    Ms. Marshall, what do you think?')))
ok('opening member statement is not classified as witness',
   'HILL' not in cr.witness_surnames(_hearing,'house',119))
ok('same-surname outside witness is blocklisted',
   'MARSHALL' in cr.witness_surnames(_hearing,'house',119))
_mem=__import__('sqlite3').connect(':memory:')
_mem.execute('CREATE TABLE speeches(member,date,source,chamber,package,nwords,text)')
cr.parse_pages([('synthetic.htm',_hearing)],lambda _:'house','2025-02-05','CHRG',
               'CHRG-119hhrg99999',_mem.cursor(),congress=119)
_rows=list(_mem.execute('SELECT member,chamber,text FROM speeches')); _mem.close()
ok('only live member questioning survives hearing parser',
   len(_rows)==1 and _rows[0][0]=='French Hill' and _rows[0][1]=='house' and
   'live question-period' in _rows[0][2] and 'opening statement' not in _rows[0][2].lower() and
   'written question' not in _rows[0][2].lower(),_rows)
ok('joint package scope is explicit',cr.chrg_scope('CHRG-117jhrg12345')==(117,'joint'))

print('\nKERNEL TESTS — %d passed, %d FAILED'%(P,F))
sys.exit(1 if F else 0)
