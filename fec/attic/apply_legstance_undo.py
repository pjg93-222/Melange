# -*- coding: utf-8 -*-
"""Undo ONLY the leg-stance (stance detection): restore Blended Model col4 (Legislative agenda raw) from the
static stance-gated values back to its original formula ='Rank & Allocation'!D{r} (the un-gated, topic-signed
legislative pillar). Leaves the press pillar (bills re-dup'd back in) untouched. COM + recalc."""
import sys, shutil, os, datetime
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
bk = WB.replace('.xlsx', '.PRE-LEGSTANCE-UNDO-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB); ws = wb.Worksheets('Blended Model')
    print('before: col4 row3 =', ws.Cells(3, 4).Formula)
    ws.Range('D3:D535').Formula = "='Rank & Allocation'!D3"   # relative ref fills down: D4->D4, D5->D5, ...
    print('after:  col4 row3 =', ws.Cells(3, 4).Formula, '| row4 =', ws.Cells(4, 4).Formula)
    xl.CalculateFull()
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED + recalc (leg-stance undone; press re-dup kept)')
finally:
    xl.Quit()
