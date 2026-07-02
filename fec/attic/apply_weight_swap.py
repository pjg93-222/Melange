# -*- coding: utf-8 -*-
"""Swap the Blended Model score weights: Press 0.40->0.20, Legislative 0.20->0.40 (AB3 and AB2).
Influence 0.35 and Demo 0.05 unchanged. Writes via Excel COM + full recalc so ranks update. Backs up first."""
import sys, shutil, os, datetime
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
bk = WB.replace('.xlsx', '.PRE-WEIGHTSWAP-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB); ws = wb.Worksheets('Blended Model')
    print('before: AB2(Legislative w)=%s  AB3(Press w)=%s' % (ws.Range('AB2').Value, ws.Range('AB3').Value))
    ws.Range('AB2').Value = 0.40   # Legislative weight
    ws.Range('AB3').Value = 0.20   # Press weight
    xl.CalculateFull()
    print('after:  AB2=%s  AB3=%s  AB4(Infl)=%s  AB5(Demo)=%s' % (ws.Range('AB2').Value, ws.Range('AB3').Value, ws.Range('AB4').Value, ws.Range('AB5').Value))
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED + recalculated (ranks updated)')
finally:
    xl.Quit()
