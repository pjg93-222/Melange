# -*- coding: utf-8 -*-
"""Set the Blended Model score weights (AB2:AB5) and recalc. Edit WEIGHTS below.
Score = AB2*Legislative% + AB3*Press% + AB4*Influence(committee)% + AB5*Demo%.
Current truthful config: committee-weighted (press was an over-weighted tone proxy that mis-ranked power players)."""
import sys, shutil, os, datetime
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
WEIGHTS = {'AB2_leg': 0.30, 'AB3_press': 0.20, 'AB4_committee': 0.40, 'AB5_demo': 0.10}   # sums to 1.00 (committee-weighted final)
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, 'weights must sum to 1'
bk = WB.replace('.xlsx', '.PRE-WEIGHTS-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB); ws = wb.Worksheets('Blended Model')
    print('before: Leg=%s Press=%s Cmte=%s Demo=%s' % (ws.Range('AB2').Value, ws.Range('AB3').Value, ws.Range('AB4').Value, ws.Range('AB5').Value))
    ws.Range('AB2').Value = WEIGHTS['AB2_leg']; ws.Range('AB3').Value = WEIGHTS['AB3_press']
    ws.Range('AB4').Value = WEIGHTS['AB4_committee']; ws.Range('AB5').Value = WEIGHTS['AB5_demo']
    ws.Range('R3:R535').Formula = '=E3/MAX($E$3:$E$535)'   # re-assert committee-pillar fix (collision-proof: in same write)
    xl.CalculateFull()
    print('after:  Leg=%s Press=%s Cmte=%s Demo=%s' % (ws.Range('AB2').Value, ws.Range('AB3').Value, ws.Range('AB4').Value, ws.Range('AB5').Value))
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED + recalculated')
finally:
    xl.Quit()
