# -*- coding: utf-8 -*-
"""Cosmetic polish: give the raw float columns a consistent 0.000 format on the two results sheets and label
the weights-value column. Format-only (no recalc). Backs up to backups/."""
import sys, shutil, os, datetime
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WB = B + r'\Moneyball Main Version - Blended.xlsx'
bk = B + r'\backups\Moneyball Main Version - Blended.PRE-FORMATS-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB)
    bm = wb.Worksheets('Blended Model')
    for col in [3,4,5,6,7,8,15,17,22,23]:
        bm.Range(bm.Cells(3,col), bm.Cells(535,col)).NumberFormat = '0.000'
    for col in [20,25]:
        bm.Range(bm.Cells(3,col), bm.Cells(535,col)).NumberFormat = '0'
    bm.Cells(1,28).Value = 'Value'
    ra = wb.Worksheets('Rank & Allocation')
    for col in [3,4,5,6]:
        ra.Range(ra.Cells(3,col), ra.Cells(535,col)).NumberFormat = '0.000'
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED (number formats applied; no recalc)')
finally:
    xl.Quit()
