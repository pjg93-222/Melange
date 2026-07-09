# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
"""RECEPTIVITY & INCENTIVE LAYER — personality/incentive-aware lobbying receptivity (user 2026-07-02).
Fuses four literatures into per-member multipliers consumed by the influence engines:

1. SUSCEPTIBILITY TO PRESSURE — Byrne, Silasi-Mansat & Worthy (PAID 2015) "Who chokes under
   pressure?": NEUROTICISM degrades decision-making under pressure (their replicated core result);
   HIGH AGREEABLENESS adds to it under *social* pressure (their Exp-2 interaction). Attribution
   honesty (lit-audit 2026-07-04): the C−/E− dampeners are OUR design priors, NOT Byrne findings
   (their E effect was null; their lone C signal was weak, unreplicated, and opposite-signed);
   A ranked above N per the user's framing: "very agreeable, or submissive to authority ... should
   be very susceptible."   SUSC_z = .40*A + .30*N − .20*C − .10*E   (weights = local calibration,
   decision-robust per receptivity_sensitivity.py: 9/9 variants keep the top-20, rho>=.998)
   -> susc_mult (pressure & diffusion), edge_mult (cascade receiver susceptibility).
2. ELECTORAL INCENTIVE — Fouirnaies & Hall (APSR): legislators WITHOUT a reelection incentive
   (final term) systematically reduce effort/responsiveness — "nothing to lose politically."
   incent_mult = 0.60 for retiring members (their last-term effect direction, conservatively
   sized), else 1 + 0.30*(competitiveness − 0.5) — safe-seat members sit below 1, competitive
   members above.  Retiring list = fec/retiring_members.txt (one canonical name/line; hook file —
   populate as retirements are announced).
3. PROSPECT THEORY — Linde & Vis (Pol.Psych 2016): politicians conform to prospect theory —
   risk-averse in the GAIN domain, risk-seeking in the LOSS domain, loss-averse overall.
   Domain: LOSS if the member has a live race (electoral play defend/contest, or security<0.45)
   -> pt_mult 1.15 (gambles under threat, more movable); GAIN (safe) -> 0.92 (protects the
   status quo).  LOSSFRAME = 1.10: a competitor THREAT (loss frame) moves lean more than an
   equally-sized CU gift (gain frame) — K&T loss aversion (lambda~2.25) attenuated to elite scale
   per Linde & Vis's finding that MPs' framing effects are real but smaller than students'.
4. CONTINGENCY-AWARE SEEDING — Chen et al. (UAI 2021) + the behaviour-aware IM survey (Zareie &
   Sakellariou SNAM 2023): a CONTACTED seed activates only with its receptivity probability —
   "legislators know they are being lobbied" (user), so lobbying contact != guaranteed activation.
   seed_prob = clip(0.60 + .10*A + .06*O + .04*E, 0.30, 0.90): baseline 60% take-rate, agreeable/
   open/extraverted members take meetings and act; committed allies are never gated (they are
   already active, not lobbied contingent seeds).

Trait uncertainty uses GRADED shrinkage sh=sqrt(tokens/1500) capped at 1 (Ramey Fig 3: CI width
scales ~1/sqrt(words)) — thin corpora keep partial signal, zero text maps to fully NEUTRAL
multipliers, never an invented personality.  All engine wiring reads member_receptivity.json
and falls back to neutral (=legacy behavior) if the file is absent or RECEPT_LAYER=0.
Output: member_receptivity.json {member: {big5, susc_z, susc_mult, edge_mult, incent_mult,
pt_domain, pt_mult, pressure_mult, seed_prob, lowconf}}"""
import sys,os,json
from moneyball_core import dump_atomic   # S3-01 audit run-2: chain artifacts write atomically
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=MB_ROOT
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}; members=list(C)
try: T=json.load(open(B+r'\big5_traits.json'))['traits']
except FileNotFoundError: T={}
if not T: print('  !! big5_traits.json MISSING/EMPTY — every member falls to trait-neutral (personality layer OFF). Run big5_traits.py.')
# ---- BEHAVIORAL BASIS (nomological fix 2026-07-04, user: 'fix it — do whatever it takes') ----
# The pre-registered label-free validation (big5_nomological_prereg.md) INDICTED the lexical Big5
# for behavioral prediction (C REVERSED on participation, E = broadcast talkativeness, r_alerting
# -0.76). Dispositions are now measured FROM BEHAVIOR (behavioral_dispositions.py): cooperation
# (A-role, the one corner lexical A validated on, now measured directly), diligence (C-role,
# roll-call participation — RKH's own C criterion), dominance (E-resistance role, interview turn
# stats + leadership), visibility/breadth (seed-prob roles). N stays TEXT-based (no behavioral
# criterion exists for it) with the same graded shrinkage. RECEPT_TRAITS=lexical reverts wholesale.
BASIS=os.environ.get('RECEPT_TRAITS','behavioral')
# ---- N-SLOT (round-3 2026-07-09, user-ratified: "can you safely create it? proceed") ----
# The Byrne composite's N was the engine's LAST text-derived leg ("no behavioral criterion exists"),
# and the 07-09 psych-audit closed every ES/N validation route for text and voice. The behavioral
# operationalization (Celli-Rossi round-3 survivor): reactivity_z = live-interview cutoff proneness
# (behavioral_dispositions.py; orthogonal to all dispositions, party/gender-clean, program-split-half
# SB .43 w/ graded shrinkage). RECEPT_N=behavioral (default) uses it, missing -> neutral 0 (same rule
# as every other behavioral component — never a text fallback, never an invented disposition);
# RECEPT_N=text reverts the slot to the shrunken lexical N wholesale (the pre-round-3 legacy math).
RECEPT_N=os.environ.get('RECEPT_N','behavioral')
BD={}
if BASIS=='behavioral':
    try: BD=json.load(open(B+r'\behavioral_dispositions.json'))['members']
    except FileNotFoundError: pass
    if not BD:
        print('  !! behavioral_dispositions.json MISSING — falling back to LEXICAL basis (run behavioral_dispositions.py)')
        BASIS='lexical'
    else: print('  BEHAVIORAL basis: %d members with measured dispositions (RECEPT_TRAITS=lexical reverts)'%len(BD))
EL=json.load(open(B+r'\electoral.json'))
try: EP=json.load(open(B+r'\electoral_plays.json'))
except FileNotFoundError: EP={}
if not EP: print('  !! electoral_plays.json MISSING/EMPTY — prospect-theory loss domain falls back to security<0.45 only. Run build_electoral_plays.py.')
RETF=B+r'\fec\retiring_members.txt'
RET=set()
if os.path.exists(RETF):
    RET={l.strip() for l in open(RETF,encoding='utf-8') if l.strip() and not l.startswith('#')}
def clip(x,lo,hi): return max(lo,min(hi,x))
# ---- PERSONA CHANNEL (user-ratified 2026-07-03: "wire into susceptibility/neuroticism") ----
# Birkenmaier-Lechner cue shares (agency_communion.json, agency_communion_llm.py): the PROJECTED
# persona — warm/communal rhetoric reads as approachable-agreeable (Byrne susceptible), dominant/
# assertive rhetoric resists pressure. persona_susc_z = .60*z(communion) − .40*z(agency), blended
# into the trait susceptibility at PERSONA_W (default 0.30) for members with >=15 classified
# sentences; everyone else stays trait-only. The two reads are also CROSS-COMPARED per member
# ('susc_read': agree-susceptible / agree-resistant / mixed / diverge) — divergence means the
# trait and persona instruments disagree: verify in person before leaning on either.
PW=float(os.environ.get('PERSONA_W','0.30'))
PS={}
try:
    _ac={m:d for m,d in json.load(open(B+r'\agency_communion.json'))['members'].items() if d.get('n',0)>=15}
    if _ac:
        _ag=[d['agency'] for d in _ac.values()]; _co=[d['communion'] for d in _ac.values()]
        _ma=sum(_ag)/len(_ag); _sa=(sum((x-_ma)**2 for x in _ag)/max(1,len(_ag)-1))**.5 or 1.0
        _mc=sum(_co)/len(_co); _sc=(sum((x-_mc)**2 for x in _co)/max(1,len(_co)-1))**.5 or 1.0
        PS={m:{'z':.60*((d['communion']-_mc)/_sc)-.40*((d['agency']-_ma)/_sa),
               'agency':d['agency'],'communion':d['communion'],'n':d['n']} for m,d in _ac.items()}
except FileNotFoundError: pass
if not PS: print('  !! agency_communion.json MISSING/EMPTY — persona channel OFF (trait-only susceptibility). Run agency_communion_llm.py --all.')
else: print('  persona channel: %d members with cue coverage (PERSONA_W=%.2f)'%(len(PS),PW))
out={}
for m in members:
    t=T.get(m,{}); low=t.get('lowconf',True)
    # graded uncertainty shrinkage (Ramey Fig 3: CI width ~ 1/sqrt(words)): partial signal from thin
    # corpora rather than a hard neutral cliff; zero text -> fully neutral.
    sh=min(1.0,(t.get('tokens',0)/1500.0)**0.5)
    A,N,Cc,E,O=(sh*t.get('A',0),sh*t.get('N',0),sh*t.get('C',0),sh*t.get('E',0),sh*t.get('O',0))
    if BASIS=='behavioral':
        bd=BD.get(m,{})
        coop=bd.get('cooperation_z',0.0) or 0.0; dil=bd.get('diligence_z',0.0) or 0.0
        dom=bd.get('dominance_z',0.0) or 0.0
        # Byrne composite, same structure/weights, behavioral inputs (missing component -> 0 neutral);
        # N-slot: behavioral reactivity (RECEPT_N=behavioral, round-3 default) or shrunken text N
        # (RECEPT_N=text, pre-round-3 legacy).
        rea=bd.get('reactivity_z')
        Nn=(rea if rea is not None else 0.0) if RECEPT_N!='text' else N
        susc_trait=.40*coop+.30*Nn-.20*dil-.10*dom
        low=not bd   # lowconf now = no behavioral coverage at all
    else:
        susc_trait=.40*A+.30*N-.20*Cc-.10*E             # Byrne et al. choking composite (lexical read)
    ps=PS.get(m)
    susc=(1-PW)*susc_trait+PW*ps['z'] if ps else susc_trait
    if ps is None: read='trait-only'
    elif abs(susc_trait)<=0.5 and abs(ps['z'])<=0.5: read='both-neutral'
    elif susc_trait>0.5 and ps['z']>0.5: read='agree-susceptible'
    elif susc_trait<-0.5 and ps['z']<-0.5: read='agree-resistant'
    elif susc_trait*ps['z']<0 and abs(susc_trait-ps['z'])>1.0: read='diverge'
    else: read='mixed'
    susc_mult=clip(1+.18*susc,0.70,1.30)
    edge_mult=clip(1+.12*susc,0.80,1.20)
    sec=EL.get(m,{}).get('security',0.5); comp=1-sec
    incent=0.60 if m in RET else clip(1+.30*(comp-0.5),0.85,1.15)
    loss=(EP.get(m,{}).get('play') in ('defend','contest')) or sec<0.45
    pt=1.15 if loss else 0.92
    if BASIS=='behavioral':
        bd=BD.get(m,{})
        seed_prob=clip(0.60+.10*(bd.get('cooperation_z',0.0) or 0.0)
                           +.06*(bd.get('breadth_z',0.0) or 0.0)
                           +.04*(bd.get('visibility_z',0.0) or 0.0),0.30,0.90)
    else:
        seed_prob=clip(0.60+.10*A+.06*O+.04*E,0.30,0.90)
    out[m]={'A':round(A,3),'N':round(N,3),'C':round(Cc,3),'E':round(E,3),'O':round(O,3),
        'basis':BASIS,'n_source':('text' if (BASIS!='behavioral' or RECEPT_N=='text') else ('reactivity' if BD.get(m,{}).get('reactivity_z') is not None else 'neutral')),
        **({k:BD[m][k] for k in BD.get(m,{})} if BASIS=='behavioral' and m in BD else {}),
        'susc_z':round(susc,3),'susc_trait_z':round(susc_trait,3),
        'persona_susc_z':round(ps['z'],3) if ps else None,'susc_read':read,
        'agency':ps['agency'] if ps else None,'communion':ps['communion'] if ps else None,
        'susc_mult':round(susc_mult,3),'edge_mult':round(edge_mult,3),
        'incent_mult':round(incent,3),'pt_domain':'loss' if loss else 'gain','pt_mult':pt,
        'pressure_mult':round(clip(susc_mult*incent*pt,0.50,1.60),3),
        'seed_prob':round(seed_prob,3),'lowconf':low,'retiring':m in RET}
dump_atomic({'members':out,'LOSSFRAME':1.10,'basis':BASIS,'n_slot':(RECEPT_N if BASIS=='behavioral' else 'text'),
  'provenance':'Byrne2015 choking (susc), Fouirnaies-Hall (incent), Linde-Vis prospect theory (pt), Chen/SNAM contingency (seed_prob); '
    +(('BEHAVIORAL basis (nomological fix 2026-07-04): cooperation/diligence/dominance/visibility/breadth measured from behavior_panel; '
       +('N-slot = behavioral reactivity (live-interview cutoff proneness, round-3 2026-07-09; missing -> neutral; RECEPT_N=text reverts)' if RECEPT_N!='text'
         else 'N-slot = text N with sqrt shrinkage (RECEPT_N=text legacy)'))
      if BASIS=='behavioral' else 'LEXICAL basis; graded sqrt(tokens/1500) trait shrinkage toward neutral')},
  B+r'\member_receptivity.json')
import collections
d=collections.Counter(out[m]['pt_domain'] for m in out)
neu=sum(1 for m in out if out[m]['lowconf'])
sp=sorted(out[m]['seed_prob'] for m in out); pm=sorted(out[m]['pressure_mult'] for m in out)
print('RECEPTIVITY: %d members | pt domains %s | retiring %d | trait-neutral(lowconf) %d'%(len(out),dict(d),len(RET),neu))
print('  seed_prob med %.2f [%.2f..%.2f] | pressure_mult med %.2f [%.2f..%.2f]'%(
    sp[len(sp)//2],sp[0],sp[-1],pm[len(pm)//2],pm[0],pm[-1]))
hi=sorted((m for m in out if not out[m]['lowconf']),key=lambda m:-out[m]['pressure_mult'])[:5]
lo=sorted((m for m in out if not out[m]['lowconf']),key=lambda m:out[m]['pressure_mult'])[:5]
print('  most pressure-susceptible:',', '.join('%s %.2f'%(m,out[m]['pressure_mult']) for m in hi))
print('  most pressure-resistant:  ',', '.join('%s %.2f'%(m,out[m]['pressure_mult']) for m in lo))
if PS:
    rd=collections.Counter(out[m]['susc_read'] for m in out if out[m]['persona_susc_z'] is not None)
    print('  trait-vs-persona cross-comparison:',dict(rd))
    div=[m for m in out if out[m]['susc_read']=='diverge']
    if div: print('  DIVERGING (verify in person before leaning on either read):',', '.join(sorted(div)[:8]))
print('wrote member_receptivity.json')
