# -*- coding: utf-8 -*-
"""Sync the workbook's Rank & Allocation 'Stance Tier' column (G) to the dashboard's overall stance =
importance-weighted aggregate of the per-category tiers (category_stance.json), 10-tier symmetric ladder.
Writes static values (the L3:L9 press/leg dials no longer drive this column). Excel COM + backup."""
import json, io, sys, shutil, datetime, collections
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
cs = json.load(io.open(r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\category_stance.json', encoding='utf-8'))
M = cs['matrix']
TORD = {'Champion':4,'Defender':4,'Ally':2,'Highly Persuadable':1,'True Neutral':0,'Neutral':0,'Lean Skeptic':-1,'Skeptic':-2,'Opponent':-4}
IMP = {'Examination & Supervision':0.75,'CU Capital Requirements':0.25,'NCUA Budget & Insurance':1.0,'Interchange':2.0,
 'Payments':0.75,'Technology & Emerging':0.75,'Fraud Prevention':0.75,'Data Privacy & Cyber':1.0,'Charter Modernization':1.0,
 'Defense CU Issues':0.2,'Field of Membership':1.0,'CDFI Fund':0.1,'CFPB':1.0,'Credit Card Mandates':3.0,'TCPA':0.2,
 'Member Business Lending':0.3,'Mortgage & Housing':0.4,'CU Tax Status':3.0}   # ABB26-anchored (2026-07-01)
def agg(n):
    cm = M.get(n, {}); sw = si = 0.0
    for c, t in cm.items():
        if t in TORD: w = IMP.get(c, 0.5); sw += TORD[t]*w; si += w
    if si == 0: return 'Neutral'
    x = sw/si
    return ('Champion' if x>=2.5 else 'Ally' if x>=1.75 else 'Highly Persuadable' if x>=1.25 else
            'Persuadable' if x>=0.75 else 'Lean Persuadable' if x>=0.25 else 'True Neutral' if x>=-0.25 else
            'Lean Skeptic' if x>=-0.75 else 'Skeptic' if x>=-1.25 else 'Highly Skeptical' if x>=-1.9 else 'Opponent')

bak = WB.replace('.xlsx', '.PRE-STANCESYNC-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bak); print('backup ->', bak)
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB); ws = wb.Worksheets('Rank & Allocation')
    n = 0; cnt = collections.Counter()
    for r in range(3, 536):
        nm = ws.Cells(r, 1).Value
        if not nm: continue
        s = agg(nm); ws.Cells(r, 7).Value = s; cnt[s] += 1; n += 1
    print('wrote %d stance cells' % n)
    print('distribution:', dict(cnt))
    for r in (51, 458, 491):
        print('  %-16s -> %s' % (ws.Cells(r, 1).Value, ws.Cells(r, 7).Value))
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED workbook (Stance Tier synced).')
finally:
    xl.Quit()
