# -*- coding: utf-8 -*-
"""REVERSE the press de-dup: put the 1310 billstatus bill-cosponsorship rows BACK into the press pillar
('Press Release - Raw'), using the exact run_stage5 aggregation INCLUDING bills. They stay HIDDEN from the
member-desk press display (that filter is in make_member_desk). Leaves the stance-gated leg pillar (col4)
untouched. COM write + recalc -> Press% / Score / Rank update. Backs up first."""
import csv, collections, sys, shutil, os, datetime, unicodedata
import win32com.client as win32
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
WB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\Moneyball Main Version - Blended.xlsx'
ST = r'C:\Users\pgoff\OneDrive\Desktop\Draft Systems\cu_press_stance_tone.csv'
def nfc(s): return unicodedata.normalize('NFC', str(s)) if s is not None else s
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0

# ---- WITH-bills by-category (recency-weighted mean over ALL rows incl billstatus) = original press pillar ----
rows = list(csv.DictReader(open(ST, encoding='utf-8-sig', newline='')))
acc = collections.defaultdict(lambda: [0.0, 0.0])
for r in rows:                                       # NO billstatus exclusion -> bills back in
    pv = num(r.get('press_value')); rw = num(r.get('recency_weight')) or 1.0
    m = nfc(r.get('member'))
    for c in str(r.get('categories', '')).split(';'):
        c = c.strip()
        if not c: continue
        a = acc[(m, c)]; a[0] += pv * rw; a[1] += rw
withb = {k: round(v[0] / v[1], 6) for k, v in acc.items() if v[1]}
print('with-bills by-category cells: %d' % len(withb))

bk = WB.replace('.xlsx', '.PRE-PRESSREDUP-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    wb = xl.Workbooks.Open(WB); ws = wb.Worksheets('Press Release - Raw')
    data = ws.UsedRange.Value; hdr = data[0]
    catcols = {hdr[c]: c for c in range(len(hdr)) if hdr[c] and hdr[c] not in ('member', 'chamber', 'state', 'party')}
    changed = 0
    for ri in range(1, len(data)):
        mname = data[ri][0]
        if not mname: continue
        mn = nfc(mname)
        for cat, ci in catcols.items():
            newv = withb.get((mn, cat), 0.0)
            cur = data[ri][ci]; cur = cur if isinstance(cur, (int, float)) else 0.0
            if abs(cur - newv) > 1e-9:
                ws.Cells(ri + 1, ci + 1).Value = newv; changed += 1
    print('cells restored (bills back in press pillar): %d' % changed)
    xl.CalculateFull()
    wb.Save(); wb.Close(SaveChanges=True); print('SAVED + recalculated')
finally:
    xl.Quit()
