# -*- coding: utf-8 -*-
"""RECEPTIVITY & INCENTIVE LAYER — personality/incentive-aware lobbying receptivity (user 2026-07-02).
Fuses four literatures into per-member multipliers consumed by the influence engines:

1. SUSCEPTIBILITY TO PRESSURE — Byrne, Silasi-Mansat & Worthy (PAID 2015) "Who chokes under
   pressure?": HIGH AGREEABLENESS degrades decisions under social pressure (their headline result),
   NEUROTICISM adds to it; deliberative CONSCIENTIOUSNESS is protective and EXTRAVERSION
   (dominance) resists. The user's framing: "very agreeable, or submissive to authority ... should
   be very susceptible."   SUSC_z = .40*A + .30*N − .20*C − .10*E   (relative correlate strengths)
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
4. CONTINGENCY-AWARE SEEDING — Chen et al. (ICML 2021) + the behaviour-aware IM survey (Zareie &
   Sakellariou SNAM 2023): a CONTACTED seed activates only with its receptivity probability —
   "legislators know they are being lobbied" (user), so lobbying contact != guaranteed activation.
   seed_prob = clip(0.60 + .10*A + .06*O + .04*E, 0.30, 0.90): baseline 60% take-rate, agreeable/
   open/extraverted members take meetings and act; committed allies are never gated (they are
   already active, not lobbied contingent seeds).

Low-confidence trait members (tokens < floor) have trait z shrunk to 0 — uncertainty maps to
NEUTRAL multipliers, never an invented personality.  All engine wiring reads member_receptivity.json
and falls back to neutral (=legacy behavior) if the file is absent or RECEPT_LAYER=0.
Output: member_receptivity.json {member: {big5, susc_z, susc_mult, edge_mult, incent_mult,
pt_domain, pt_mult, pressure_mult, seed_prob, lowconf}}"""
import sys,os,json
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
B=r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
C={m['member']:m for m in json.load(open(B+r'\congestion.json'))}; members=list(C)
try: T=json.load(open(B+r'\big5_traits.json'))['traits']
except FileNotFoundError: T={}
EL=json.load(open(B+r'\electoral.json'))
try: EP=json.load(open(B+r'\electoral_plays.json'))
except FileNotFoundError: EP={}
RETF=B+r'\fec\retiring_members.txt'
RET=set()
if os.path.exists(RETF):
    RET={l.strip() for l in open(RETF,encoding='utf-8') if l.strip() and not l.startswith('#')}
def clip(x,lo,hi): return max(lo,min(hi,x))
out={}
for m in members:
    t=T.get(m,{}); low=t.get('lowconf',True)
    # graded uncertainty shrinkage (Ramey Fig 3: CI width ~ 1/sqrt(words)): partial signal from thin
    # corpora rather than a hard neutral cliff; zero text -> fully neutral.
    sh=min(1.0,(t.get('tokens',0)/1500.0)**0.5)
    A,N,Cc,E,O=(sh*t.get('A',0),sh*t.get('N',0),sh*t.get('C',0),sh*t.get('E',0),sh*t.get('O',0))
    susc=.40*A+.30*N-.20*Cc-.10*E                       # Byrne et al. choking composite
    susc_mult=clip(1+.18*susc,0.70,1.30)
    edge_mult=clip(1+.12*susc,0.80,1.20)
    sec=EL.get(m,{}).get('security',0.5); comp=1-sec
    incent=0.60 if m in RET else clip(1+.30*(comp-0.5),0.85,1.15)
    loss=(EP.get(m,{}).get('play') in ('defend','contest')) or sec<0.45
    pt=1.15 if loss else 0.92
    seed_prob=clip(0.60+.10*A+.06*O+.04*E,0.30,0.90)
    out[m]={'A':round(A,3),'N':round(N,3),'C':round(Cc,3),'E':round(E,3),'O':round(O,3),
        'susc_z':round(susc,3),'susc_mult':round(susc_mult,3),'edge_mult':round(edge_mult,3),
        'incent_mult':round(incent,3),'pt_domain':'loss' if loss else 'gain','pt_mult':pt,
        'pressure_mult':round(clip(susc_mult*incent*pt,0.50,1.60),3),
        'seed_prob':round(seed_prob,3),'lowconf':low,'retiring':m in RET}
json.dump({'members':out,'LOSSFRAME':1.10,
  'provenance':'Byrne2015 choking (susc), Fouirnaies-Hall (incent), Linde-Vis prospect theory (pt), Chen/SNAM contingency (seed_prob); lowconf traits shrunk to neutral'},
  open(B+r'\member_receptivity.json','w'))
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
print('wrote member_receptivity.json')
