# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT  # centralized root (arch review 2026-07-02)
import moneyball_core as MC
"""Col-G-ONLY stance sync (SAFE variant of sync_stance_clean.py, 2026-07-01): recompute the overall
stance ladder from the category_stance matrix with the CURRENT IMP weights and write ONLY Rank &
Allocation col G, calc=MANUAL. Unlike sync_stance_clean, this does NOT restore the pristine
PRE-STANCEGUARD backup first (that restore would wipe the leg-stance col D and every later model edit).
Run after any IMP change or Category Stance sheet edit."""
import json, io, sys, collections
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = MB_ROOT
WB = B + r'\Moneyball Main Version - Blended.xlsx'
M = json.load(io.open(B + r'\category_stance.json', encoding='utf-8'))['matrix']
TORD = {'Champion':4,'Defender':4,'Ally':2,'Highly Persuadable':1,'True Neutral':0,'Neutral':0,'Lean Skeptic':-1,'Skeptic':-2,'Opponent':-4}
# IMP anchored to the ABB26 handout (America's Credit Unions 2026 Advocacy Priorities) -- keep in sync with
# apply_leg_stance / sync_stance(.clean) / build_dashboard_bundle / corrected_signals.
from moneyball_core import IMP   # single copy (was x6, one drifted)
def agg(n):
    cm = M.get(n, {}); sw = si = 0.0
    for c, t in cm.items():
        if t in TORD: w = IMP.get(c, 0.5); sw += TORD[t]*w; si += w
    if si == 0: return 'Neutral'
    x = sw/si
    return ('Champion' if x>=2.5 else 'Ally' if x>=1.75 else 'Highly Persuadable' if x>=1.25 else
            'Persuadable' if x>=0.75 else 'Lean Persuadable' if x>=0.25 else 'True Neutral' if x>=-0.25 else
            'Lean Skeptic' if x>=-0.75 else 'Skeptic' if x>=-1.25 else 'Highly Skeptical' if x>=-1.9 else 'Opponent')

MANUAL = -4135
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try: xl.Calculation = MANUAL
except Exception: pass
try:
    wb = xl.Workbooks.Open(WB)
    try: xl.Calculation = MANUAL
    except Exception: pass
    ws = wb.Worksheets('Rank & Allocation'); cnt = collections.Counter(); n = 0
    for r in range(3, 536):
        nm = ws.Cells(r, 1).Value
        if not nm: continue
        s = agg(nm); ws.Cells(r, 7).Value = s; cnt[s] += 1; n += 1
    print('wrote %d stance cells to col G (calc=MANUAL, no recalc, NO pristine restore)' % n)
    print('distribution:', dict(cnt))
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED.')
finally:
    xl.Quit()
