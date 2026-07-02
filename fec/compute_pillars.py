# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root
"""PYTHON PILLAR SHADOW-COMPUTE — roadmap #9 phase 1 (architecture review 2026-07-02).

Reproduces the workbook's ENTIRE rank chain in Python from raw inputs and proves exact parity:

  Press Release - Raw ──(pos/neg-max LET normalization per column)──> normalized matrix
  normalized × row-535 tiered weights ──SUMPRODUCT──> press pillar (R&A col C = Blended col C)
  Blended: Press% = C/max(C) · Influence% = E/max(E) · Leg% = PERCENTRANK(O,5) · Demo% = PERCENTRANK(F,5)
  Score  = AB2·Leg% + AB3·Press% + AB4·Influence% + AB5·Demo%   (weights read live from AB2:AB5)
  Rank   = descending competition rank of Score

Excel-exact notes: PERCENTRANK.INC = (#values strictly below x)/(n−1), TRUNCATED to the given
significance (5 here) — truncation, not rounding, and leading zeros are not significant.

This is the enabling step for demoting the workbook to a rendered view: once Python provably owns
the math, the COM-recalc/OneDrive failure class can be retired. Until then this runs as a PARITY
CHECK (wired into audit_full): any drift between the sheet and the spec'd math fails loudly.

Usage: python compute_pillars.py       # prints parity report; exit 1 on any mismatch"""
import sys,math,json
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
import openpyxl
B=MB_ROOT
wb=openpyxl.load_workbook(B+r'\Moneyball Main Version - Blended.xlsx',data_only=True,read_only=True)
pn=wb['Press Release - Normalized']; ra=wb['Rank & Allocation']; bm=wb['Blended Model']; rw=wb['Press Release - Raw']
# ---- rosters/rows ----
bmrows={};
for r in range(3,536):
    n=bm.cell(r,1).value
    if n: bmrows[n]=r
members=list(bmrows)
prow={pn.cell(r,1).value:r for r in range(2,535) if pn.cell(r,1).value}
rrow={rw.cell(r,1).value:r for r in range(2,535) if rw.cell(r,1).value}
COLS=list(range(5,24))
# ---- 1) normalization: raw -> normalized (pos-max / neg-max per column), verified vs the sheet ----
rawcol={c:{m:(rw.cell(rrow[m],c).value or 0.0) for m in members if m in rrow} for c in COLS}
norm={}
nmis=0
for c in COLS:
    vals=list(rawcol[c].values())
    pmax=max(0.0,max(vals,default=0.0)); nmax=abs(min(0.0,min(vals,default=0.0)))
    col={}
    for m,x in rawcol[c].items():
        col[m]=0.0 if x==0 else (x/pmax if (x>0 and pmax) else (x/nmax if (x<0 and nmax) else 0.0))
    norm[c]=col
    for m in list(rawcol[c])[::37]:   # spot-verify vs the live normalized sheet
        sheet=pn.cell(prow[m],c).value or 0.0
        if abs(col[m]-sheet)>1e-9: nmis+=1
# ---- 2) press pillar: SUMPRODUCT(normalized row, weights row 535) ----
w535={c:(pn.cell(535,c).value or 0.0) for c in COLS}
pillar={m:sum(norm[c].get(m,0.0)*w535[c] for c in COLS) for m in members}
cmis=sum(1 for m in members if abs(pillar[m]-(ra.cell(bmrows[m],3).value or 0.0))>1e-9)
# ---- 3) pillar percents + score + rank ----
def percentrank(vals,x):
    # Excel PERCENTRANK.INC(...,5): (#strictly below)/(n-1), TRUNCATED to 5 DECIMAL digits.
    # (Empirically verified 2026-07-02: Excel's "significance" behaves as decimal places here —
    # 5-significant-digit truncation left 94 sub-0.1 members off by ~2e-6; 5-decimal matches exactly.)
    below=sum(1 for v in vals if v<x)
    return math.floor(below/(len(vals)-1)*1e5)/1e5
O={m:(bm.cell(bmrows[m],15).value or 0.0) for m in members}   # Leg pillar (raw)
E={m:(bm.cell(bmrows[m],5).value or 0.0)  for m in members}   # Committee (raw)
F={m:(bm.cell(bmrows[m],6).value or 0.0)  for m in members}   # Demographic (raw)
AB={r:(bm.cell(r,28).value or 0.0) for r in (2,3,4,5)}        # Legislative/Press/Influence/Demo weights
Ov=list(O.values()); Fv=list(F.values())
pmaxC=max(pillar.values()) or 1.0; emax=max(E.values()) or 1.0
score={};
for m in members:
    legp=percentrank(Ov,O[m]); pressp=pillar[m]/pmaxC; infp=E[m]/emax; demp=percentrank(Fv,F[m])
    score[m]=AB[2]*legp+AB[3]*pressp+AB[4]*infp+AB[5]*demp
order=sorted(members,key=lambda m:-score[m])
rank={};
for i,m in enumerate(order):
    rank[m]=rank[order[i-1]] if i and score[m]==score[order[i-1]] else i+1
# ---- 4) parity vs the live sheet ----
smis=[]; rmis=[]
for m in members:
    s_sheet=bm.cell(bmrows[m],19).value; r_sheet=bm.cell(bmrows[m],20).value
    if s_sheet is None or abs(score[m]-s_sheet)>1e-7: smis.append((m,s_sheet,score[m]))
    if r_sheet!=rank[m]: rmis.append((m,r_sheet,rank[m]))
print('PILLAR SHADOW-COMPUTE PARITY')
print('  normalization spot-checks   : %s'%('OK' if nmis==0 else '%d MISMATCH'%nmis))
print('  press pillar (533 members)  : %s'%('OK (0 mismatch)' if cmis==0 else '%d MISMATCH'%cmis))
print('  score parity                : %s'%('OK max|d|<1e-7' if not smis else '%d MISMATCH e.g. %s'%(len(smis),smis[:2])))
print('  rank parity                 : %s'%('EXACT %d/%d'%(len(members),len(members)) if not rmis else '%d MISMATCH e.g. %s'%(len(rmis),rmis[:3])))
ok=nmis==0 and cmis==0 and not smis and not rmis
print('PARITY: %s'%('CLEAN — Python provably owns the rank math' if ok else 'DRIFT DETECTED'))
sys.exit(0 if ok else 1)
