# -*- coding: utf-8 -*-
"""N14 Q2b.  When was the SHEET's press content last written, as distinct from the FILE?
READ-ONLY.  Opens only the SCRATCH copy of the workbook and the named owner-label files.

The workbook FILE mtime is written by every chain step that saves the workbook, so it cannot
date the sheet.  Three independent probes:
  1. the .xlsx ZIP member timestamp for the sheet part (Excel stamps each part on save);
  2. the press sheet's own max date value and its header, against the tone files' max date;
  3. which artifact the sheet's press bytes MATCH -- the Draft tone xlsx, the LIVE tone xlsx,
     the base tone CSV, or none -- measured on the 57 and on the whole overlap.
Also diffs the LIVE press_stance_overrides.json against the worktree overlay copy field by
field, because the two files have different byte lengths and both feed the desk and the engine.
"""
import collections
import io
import json
import os
import zipfile

import openpyxl

import n14_common as C

C.banner('N14 Q2b  DATING THE SHEET ITSELF')

# ---- 1. ZIP member timestamps -----------------------------------------------------------
print('-- 1. .xlsx ZIP MEMBER TIMESTAMPS (workbook copy in SCRATCH; same sha256 as LIVE) --')
with zipfile.ZipFile(C.WB_SCRATCH) as zf:
    infos = sorted(zf.infolist(), key=lambda i: i.date_time)
    stamps = collections.Counter('%04d-%02d-%02dT%02d:%02d:%02d' % i.date_time for i in infos)
    print('   distinct ZIP timestamps across %d parts: %d' % (len(infos), len(stamps)))
    for stamp, n in sorted(stamps.items()):
        print('      %s  %4d parts' % (stamp, n))
    print('   VERDICT: a single stamp means every part was rewritten by the last save, so the')
    print('   ZIP cannot date the press sheet independently.')

# ---- 2. the sheet's own content dates ---------------------------------------------------
rows, ph = C.sheet_rows()
print('\n-- 2. CONTENT DATES --')
print('   sheet header: %s' % ', '.join(str(h) for h in sorted(ph, key=lambda k: ph[k])))
sheet_dates = []
for row in rows:
    value = row[ph['date']]
    text = str(value)[:10] if str(value)[:4].isdigit() else ''
    if text:
        sheet_dates.append(text)
sheet_dates.sort()
print('   press sheet date range        : %s .. %s  (%d dated of %d rows)'
      % (sheet_dates[0], sheet_dates[-1], len(sheet_dates), len(rows)))

base_rows = C.read_csv_rows(C.PS.BASE_TONE_PATH)
refresh_rows = C.read_csv_rows(C.PS.REFRESH_TONE_PATH)


def csv_dates(rowset):
    out = []
    for row in rowset:
        text = C.DPS.engine_date(row.get('date'))
        text = str(text)[:10] if str(text)[:4].isdigit() else ''
        if text:
            out.append(text)
    out.sort()
    return out


bd, rd = csv_dates(base_rows), csv_dates(refresh_rows)
print('   BASE tone CSV date range      : %s .. %s  (%d dated of %d rows)'
      % (bd[0], bd[-1], len(bd), len(base_rows)))
print('   REFRESH tone CSV date range   : %s .. %s  (%d dated of %d rows)'
      % (rd[0], rd[-1], len(rd), len(refresh_rows)))
src_sheet = collections.Counter(str(r[ph['stance_src']] or '(blank)') for r in rows)
src_base = collections.Counter(str(r.get('stance_src') or '(blank)') for r in base_rows)
src_refresh = collections.Counter(str(r.get('stance_src') or '(blank)') for r in refresh_rows)
print('\n   stance_src census')
print('      sheet        : %s' % dict(src_sheet.most_common()))
print('      BASE csv     : %s' % dict(src_base.most_common()))
print('      REFRESH csv  : %s' % dict(src_refresh.most_common()))
print("   The sheet carries ZERO 'human_label' rows: %s"
      % ('CONFIRMED' if src_sheet.get('human_label', 0) == 0 else
         'NO -- %d' % src_sheet.get('human_label')))

# ---- 3. which artifact do the SHEET's press bytes match? --------------------------------
print('\n-- 3. WHICH TONE ARTIFACT DOES THE SHEET MATCH? --')
CANDIDATES = [
    ('Draft CU_Press_Stance_Tone.xlsx', os.path.join(C.SCRATCH, 'tone_draft.xlsx')),
    ('LIVE CU_Press_Stance_Tone.xlsx', os.path.join(C.SCRATCH, 'tone_live.xlsx')),
]
q1 = json.load(io.open(os.path.join(C.HERE, 'n14_q1_disagreement_sets.json'), encoding='utf-8'))
the57 = q1['stance_disagreement_rows']
keys57 = {(r['release_key'], r['identity']): r for r in the57}

for label, path in CANDIDATES:
    if not os.path.exists(path):
        print('   %-34s MISSING in scratch' % label)
        continue
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    print('   %-34s sheets: %s' % (label, wb.sheetnames))
    for name in wb.sheetnames:
        ws = wb[name]
        header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
        hidx = {h: i for i, h in enumerate(header) if h}
        if not {'url', 'stance'} <= set(hidx):
            print('      [%s] header lacks url/stance: %s' % (name, list(hidx)[:12]))
            continue
        agree_sheet = agree_csv = neither = 0
        found = 0
        src_seen = collections.Counter()
        by_key = {}
        for row in ws.iter_rows(min_row=2, values_only=True):
            url = str(row[hidx['url']] or '')
            if not url or url.startswith('billstatus:'):
                continue
            key = C.DPS.row_key(url,
                                row[hidx['bioguide']] if 'bioguide' in hidx else None,
                                row[hidx['member']] if 'member' in hidx else '')
            if key[0]:
                by_key.setdefault(key, row)
        for key, rec in keys57.items():
            row = by_key.get(key)
            if row is None:
                continue
            found += 1
            stance = str(row[hidx['stance']] or '').strip()
            src_seen[str(row[hidx['stance_src']] or '') if 'stance_src' in hidx else '?'] += 1
            if stance == rec['sheet_stance']:
                agree_sheet += 1
            elif stance == rec['csv_stance']:
                agree_csv += 1
            else:
                neither += 1
        print('      [%-24s] rows keyed %5d | of the 57 found %2d -> matches SHEET %2d,'
              ' matches CSV %2d, neither %2d  stance_src seen %s'
              % (name[:24], len(by_key), found, agree_sheet, agree_csv, neither,
                 dict(src_seen)))
    wb.close()

# ---- 4. LIVE vs worktree override ledger, field by field --------------------------------
print('\n-- 4. press_stance_overrides.json: LIVE vs WORKTREE OVERLAY --')
live = json.load(io.open(os.path.join(C.LIVE, 'data', 'stance',
                                      'press_stance_overrides.json'), encoding='utf-8'))
wt = json.load(io.open(os.path.join(C.WT, 'data', 'stance',
                                    'press_stance_overrides.json'), encoding='utf-8'))


def keyed(doc):
    out = {}
    for row in doc.get('corrections') or []:
        key = ('url', (row.get('url') or '').strip().lower()) if row.get('url') else \
              ('title_contains', (row.get('title_contains') or '').strip().lower())
        out[key] = row
    return out


lk, wk = keyed(live), keyed(wt)
print('   LIVE corrections %d | worktree %d | identities only in LIVE %d | only in worktree %d'
      % (len(lk), len(wk), len(set(lk) - set(wk)), len(set(wk) - set(lk))))
stance_diff = [k for k in set(lk) & set(wk)
               if (lk[k].get('stance') or '') != (wk[k].get('stance') or '')]
other_diff = [k for k in set(lk) & set(wk) if lk[k] != wk[k] and k not in stance_diff]
print('   shared identities whose STANCE differs : %d  <- the only difference that can move a'
      ' displayed or scored label' % len(stance_diff))
for k in stance_diff:
    print('      %s=%r  LIVE=%r  WORKTREE=%r'
          % (k[0], k[1][:64], lk[k].get('stance'), wk[k].get('stance')))
print('   shared identities differing on OTHER fields only: %d' % len(other_diff))
for k in other_diff[:8]:
    diffs = sorted(set(lk[k]) | set(wk[k]))
    print('      %s=%r' % (k[0], k[1][:60]))
    for f in diffs:
        if lk[k].get(f) != wk[k].get(f):
            print('         %-16s LIVE=%r  WT=%r'
                  % (f, str(lk[k].get(f))[:56], str(wk[k].get(f))[:56]))
print('   top-level keys: LIVE %s | worktree %s'
      % (sorted(live), sorted(wt)))

C.dump('n14_q2b_sheet_age_probe.json', {
    'schema': 'n14-q2b-sheet-age-v1',
    'zip_timestamps': dict(stamps),
    'sheet_date_min': sheet_dates[0], 'sheet_date_max': sheet_dates[-1],
    'sheet_dated_rows': len(sheet_dates), 'sheet_rows': len(rows),
    'base_csv_date_min': bd[0], 'base_csv_date_max': bd[-1], 'base_csv_rows': len(base_rows),
    'refresh_csv_date_min': rd[0], 'refresh_csv_date_max': rd[-1],
    'refresh_csv_rows': len(refresh_rows),
    'stance_src_sheet': dict(src_sheet), 'stance_src_base': dict(src_base),
    'stance_src_refresh': dict(src_refresh),
    'override_ledger': {'live': len(lk), 'worktree': len(wk),
                        'stance_differs': [list(k) for k in stance_diff],
                        'other_fields_differ': len(other_diff)},
})
print('DONE N14 Q2b')
