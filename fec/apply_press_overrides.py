# -*- coding: utf-8 -*-
import os as _o,sys as _s;_s.path.insert(0,_o.path.dirname(_o.path.abspath(__file__)));from paths import ROOT as MB_ROOT,DRAFT as MB_DRAFT  # centralized root (arch review 2026-07-02)
"""Apply MANUAL press-stance overrides to the workbook (the dashboard "manual override switch" back-end).

Flow:
  1. If 'press_overrides_from_dashboard.json' exists (exported from Moneyball.html), MERGE its url-keyed
     corrections into the canonical 'press_stance_overrides.json' (existing title_contains entries preserved).
  2. Re-flow the PRESS PILLAR: rebuild 'Press Release - Raw' with the EXACT de-dup aggregation (billstatus
     rows excluded, recency-weighted mean of per-release press_value), but for every article matched by an
     override, flip its press_value to the chosen stance sign (support=+|v|, oppose=-|v|, neutral=0).
  3. COM write + full recalc so Blended Model ranks update. Backs the workbook up first.

After running:  python fec/make_member_desk.py  then  python fec/make_combined.py   (display picks up the
same overrides file automatically). Match is by 'url' (exact) OR 'title_contains' (case-insensitive substring).
"""
import csv, json, io, collections, sys, shutil, os, datetime, unicodedata
import win32com.client as win32
import moneyball_core as MC   # dump_atomic (S2-01 audit run-2): the overrides registry is user data, never truncate-in-place
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
B  = MB_ROOT
WB = B + r'\Moneyball Main Version - Blended.xlsx'
ST = MB_DRAFT+r'\cu_press_stance_tone.csv'
OVR = B + r'\press_stance_overrides.json'
DASH = B + r'\press_overrides_from_dashboard.json'
SIGN = {'support': 1.0, 'oppose': -1.0, 'neutral': 0.0}
def nfc(s): return unicodedata.normalize('NFC', str(s)) if s is not None else s
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0

# ---- 1. merge dashboard export into the canonical overrides file (preserve existing) ----
doc = json.load(io.open(OVR, encoding='utf-8')) if os.path.exists(OVR) else {'corrections': []}
corr = doc.get('corrections', [])
if os.path.exists(DASH):
    dash = json.load(io.open(DASH, encoding='utf-8')).get('corrections', [])
    by_url = {c['url']: i for i, c in enumerate(corr) if c.get('url')}
    added = updated = 0
    for c in dash:
        u = c.get('url')
        if not u or c.get('stance') not in SIGN: continue
        if u in by_url: corr[by_url[u]] = c; updated += 1
        else: corr.append(c); by_url[u] = len(corr) - 1; added += 1
    doc['corrections'] = corr
    MC.dump_atomic(doc, OVR, ensure_ascii=False, indent=2)
    print('merged dashboard export -> press_stance_overrides.json (added %d, updated %d)' % (added, updated))
else:
    print('no press_overrides_from_dashboard.json found; using existing press_stance_overrides.json only')

url_ov   = {c['url']: c['stance'] for c in corr if c.get('url') and c.get('stance') in SIGN}
title_ov = [(c['title_contains'].lower(), c['stance']) for c in corr
            if c.get('title_contains') and c.get('stance') in SIGN]
print('active overrides: %d by url, %d by title_contains' % (len(url_ov), len(title_ov)))
if not url_ov and not title_ov:
    print('nothing to apply; exiting.'); sys.exit(0)

def ov_stance(url, title):
    if url in url_ov: return url_ov[url]
    t = (title or '').lower()
    for sub, st in title_ov:
        if sub in t: return st
    return None

# ---- 2. re-flow the de-duped press pillar with overrides applied ----
rows = list(csv.DictReader(open(ST, encoding='utf-8-sig', newline='')))
acc = collections.defaultdict(lambda: [0.0, 0.0])
nbill = nov = 0
for r in rows:
    if str(r.get('url', '')).startswith('billstatus:') or r.get('stance_src') == 'bill':
        nbill += 1; continue                                   # bills stay OUT of the press pillar (de-duped)
    pv = num(r.get('press_value')); rw = num(r.get('recency_weight')) or 1.0
    st = ov_stance(r.get('url', ''), r.get('title', ''))
    if st is not None:
        pv = SIGN[st] * abs(pv); nov += 1                      # override: keep magnitude, set the sign
    m = nfc(r.get('member'))
    for c in str(r.get('categories', '')).split(';'):
        c = c.strip()
        if not c: continue
        a = acc[(m, c)]; a[0] += pv * rw; a[1] += rw
newvals = {k: round(v[0] / v[1], 6) for k, v in acc.items() if v[1]}
print('applied overrides to %d article-rows | rebuilt %d (member,category) cells' % (nov, len(newvals)))

# ---- 3. backup + COM write to 'Press Release - Raw' + recalc ----
bk = WB.replace('.xlsx', '.PRE-PRESSOVERRIDE-%s.xlsx' % datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(WB, bk); print('backup ->', os.path.basename(bk))
xl = win32.DispatchEx('Excel.Application'); xl.Visible = False; xl.DisplayAlerts = False
try:
    xl.Calculation = -4105   # xlCalculationAutomatic (the dedup/redup baseline left it manual via stance sync)
except Exception:
    pass
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
            newv = newvals.get((mn, cat), 0.0)
            cur = data[ri][ci]; cur = cur if isinstance(cur, (int, float)) else 0.0
            if abs(cur - newv) > 1e-9:
                ws.Cells(ri + 1, ci + 1).Value = newv; changed += 1
    print('cells updated: %d' % changed)
    xl.CalculateFull()
    wb.Save(); wb.Close(SaveChanges=True)
    print('SAVED + recalculated (Blended Model ranks updated).')
finally:
    xl.Quit()
print('\nNEXT: python fec/make_member_desk.py   then   python fec/make_combined.py   (to refresh the dashboard display)')
