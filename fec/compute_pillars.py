# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""PYTHON RANK AUTHORITY — roadmap #9 phase 2 (system-of-record inversion, user sign-off 2026-07-02).

Python computes the ENTIRE rank chain from raw inputs; the workbook is a self-refreshing VIEW
(fullCalcOnLoad — Excel recalculates its formulas whenever the user opens it):

  Press Release - Raw ──(pos/neg-max normalization, Python: moneyball_core.press_matrix)──> normalized
  normalized × row-535 tiered weights (user dial literals) ──> press pillar
  Press% = pillar/max · Influence% = E/max · Leg% = PERCENTRANK(O,5) · Demo% = PERCENTRANK(F,5)
  Score  = AB2·Leg% + AB3·Press% + AB4·Influence% + AB5·Demo%   (AB weights read live — user dials)
  Rank   = descending competition rank

Excel-exact PERCENTRANK, pinned empirically (phase 1): truncate to 5 DECIMAL digits.

MODES
  --write : write ranks_python.json (atomic) = THE rank authority the engines read
            (moneyball_core.scores()/ranks()); also reports view coherence informationally.
  (none)  : audit mode. If the workbook's cached formula results are COHERENT with its raw inputs
            (i.e. Excel recalculated since the last raw write), enforce EXACT parity — the
            formula-drift tripwire. If the view is stale (expected between pipeline runs and user
            opens), verify the authority file matches a fresh recompute instead. Exit 1 only on
            real drift or a stale AUTHORITY (rerun pipeline)."""
import sys,math,json,os
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import openpyxl
import moneyball_core as MC
B=MB_ROOT
WRITE='--write' in sys.argv
wb=openpyxl.load_workbook(B+r'\Moneyball Main Version - Blended.xlsx',data_only=True,read_only=True)
pn=wb['Press Release - Normalized']; ra=wb['Rank & Allocation']; bm=wb['Blended Model']
bmrows={}
for r in range(3,536):
    n=bm.cell(r,1).value
    if n: bmrows[n]=r
members=list(bmrows)
prow={pn.cell(r,1).value:r for r in range(2,535) if pn.cell(r,1).value}
norm,w535,hdrs=MC.press_matrix()
COLS=list(norm)
# ---- press pillar ----
pillar={m:sum(norm[c].get(m,0.0)*w535[c] for c in COLS) for m in members}
# ---- percents + score + rank (Excel-exact) ----
def percentrank(vals,x):
    # Excel PERCENTRANK.INC(...,5): (#strictly below)/(n-1), TRUNCATED to 5 DECIMAL digits
    # (empirically pinned 2026-07-02: 'significance' behaves as decimal places, not sig digits).
    below=sum(1 for v in vals if v<x)
    return math.floor(below/(len(vals)-1)*1e5)/1e5
O={m:(bm.cell(bmrows[m],15).value or 0.0) for m in members}   # Leg pillar (raw)
E={m:(bm.cell(bmrows[m],5).value or 0.0)  for m in members}   # Committee (raw)
F={m:(bm.cell(bmrows[m],6).value or 0.0)  for m in members}   # Demographic (raw)
AB={r:(bm.cell(r,28).value or 0.0) for r in (2,3,4,5)}        # pillar weights (user dials)
Ov=list(O.values()); Fv=list(F.values())
pmaxC=max(pillar.values()) or 1.0; emax=max(E.values()) or 1.0
score={}; pcts={}
for m in members:
    legp=percentrank(Ov,O[m]); pressp=pillar[m]/pmaxC; infp=E[m]/emax; demp=percentrank(Fv,F[m])
    pcts[m]={'leg':legp,'press':round(pressp,9),'inf':round(infp,9),'dem':demp}
    score[m]=AB[2]*legp+AB[3]*pressp+AB[4]*infp+AB[5]*demp
order=sorted(members,key=lambda m:-score[m])
rank={}
for i,m in enumerate(order):
    rank[m]=rank[order[i-1]] if i and score[m]==score[order[i-1]] else i+1
# ---- view coherence: does the sheet's normalized CACHE match Python's normalization of raw? ----
coherent=True
for c in list(COLS)[::4]:
    for m in list(norm[c])[::97]:
        if m in prow and abs((pn.cell(prow[m],c).value or 0.0)-norm[c][m])>1e-9: coherent=False; break
    if not coherent: break
if WRITE:
    MC.dump_atomic({'score':score,'rank':rank,'press_pillar':{m:round(v,9) for m,v in pillar.items()},
        'pcts':pcts,'ab_weights':AB,'provenance':'python rank authority (compute_pillars --write); workbook = view'},
        B+r'\ranks_python.json')
    print('wrote ranks_python.json (rank authority): %d members | view cache %s'%(
        len(members),'coherent' if coherent else 'stale (self-heals on next Excel open — fullCalcOnLoad)'))
    sys.exit(0)
# ---- audit mode ----
if coherent:
    smis=[m for m in members if bm.cell(bmrows[m],19).value is None or abs(score[m]-bm.cell(bmrows[m],19).value)>1e-7]
    rmis=[m for m in members if bm.cell(bmrows[m],20).value!=rank[m]]
    print('view COHERENT -> exact-parity tripwire: score %s | rank %s'%(
        'OK' if not smis else '%d MISMATCH'%len(smis),'EXACT %d/%d'%(len(members)-len(rmis),len(members))))
    if smis or rmis:
        print('PARITY: DRIFT DETECTED — a workbook formula no longer matches the spec math (e.g. %s)'%(smis or rmis)[:3]); sys.exit(1)
else:
    print('view STALE (expected between pipeline runs and Excel opens) -> verifying the AUTHORITY instead')
try:
    auth=json.load(open(B+r'\ranks_python.json'))
    amis=[m for m in members if abs(auth['score'].get(m,-1)-score[m])>1e-12 or auth['rank'].get(m)!=rank[m]]
    if amis:
        print('PARITY: AUTHORITY STALE — ranks_python.json does not match current inputs (%d members, e.g. %s). Rerun the pipeline.'%(len(amis),amis[:3])); sys.exit(1)
except FileNotFoundError:
    print('PARITY: AUTHORITY MISSING — run `python fec/compute_pillars.py --write` / the pipeline.'); sys.exit(1)
print('PARITY: CLEAN — Python authority verified against a fresh recompute%s'%(' + exact sheet parity' if coherent else ' (view will self-heal on open)'))
sys.exit(0)
