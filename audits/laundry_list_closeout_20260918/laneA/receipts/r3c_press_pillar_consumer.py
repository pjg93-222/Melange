# -*- coding: utf-8 -*-
"""LANE A / R3c -- which normalized press columns reach the press pillar / rank? (read-only)

R3b established: 'Press Release - Normalized' (Table13) LET-normalizes ALL 20 media-blend
columns of 'Press Release - Raw' (Table10), including 'CU-Bank Competitive Dynamics' and
'General Credit Union'.  This asks the next hop: which of Table13's columns any other sheet
names, so a column that is written and normalized but never summed is identified as inert.
"""
import os, sys, re, collections, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WBP = os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx')
print('=' * 100)
print('R3c  press pillar consumers of Table13 / Press Release - Normalized   run',
      datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)
wb = openpyxl.load_workbook(WBP, read_only=False, data_only=False)

NEEDLES = ('Table13', 'Press Release - Normalized')
colpat = re.compile(r'Table13\[\[?([^\]\[]+)\]?\]')
sheetcol = re.compile(r"'?Press Release - Normalized'?!\$?([A-Z]{1,3})")
per_sheet = collections.Counter()
cols_named = collections.Counter()
sheet_cols = collections.Counter()
samples = collections.defaultdict(list)
for ws in wb.worksheets:
    if ws.title == 'Press Release - Normalized':
        continue
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not isinstance(v, str) or not any(n in v for n in NEEDLES):
                continue
            per_sheet[ws.title] += 1
            for m in colpat.findall(v):
                cols_named[m.strip()] += 1
            for m in sheetcol.findall(v):
                sheet_cols[m] += 1
            if len(samples[ws.title]) < 3:
                samples[ws.title].append('%s!%s = %s' % (ws.title, c.coordinate,
                                                         ' '.join(v.split())[:900]))

print('\n-- sheets referencing the normalized press sheet/table --')
if not per_sheet:
    print('   (NONE)')
for sh, n in sorted(per_sheet.items(), key=lambda kv: -kv[1]):
    print('   %-34s %6d formula cells' % (sh, n))

print('\n-- Table13 column names appearing in those formulas --')
if not cols_named:
    print('   (none named individually)')
for k, v in sorted(cols_named.items(), key=lambda kv: -kv[1]):
    print('   %-40s %6d' % (k, v))

print('\n-- A1-style column letters of Press Release - Normalized referenced --')
if not sheet_cols:
    print('   (none)')
for k, v in sorted(sheet_cols.items()):
    print('   col %-4s %6d' % (k, v))

print('\n-- samples --')
for sh in sorted(samples):
    for s in samples[sh]:
        print('   %s' % s)
        print('')

# Cross-check: the 20 media columns vs the ones actually named downstream
MEDIA = ['Examination & Supervision', 'Credit Union Capital Requirements',
         'NCUA Budget & Share Insurance Fund', 'Interchange', 'Payments',
         'Technology & Emerging Issues', 'Fraud Prevention', 'Data Privacy & Cybersecurity',
         'Charter Modernization & Governance', 'Defense Credit Union Issues',
         'Field of Membership', 'Credit Union Tax Status', 'CDFI Fund',
         'CU-Bank Competitive Dynamics', 'CFPB Issues & Structural Reform',
         'Credit Card & Consumer-Fee Mandates', 'Telephone Consumer Protection Act',
         'Member Business Lending', 'Mortgage Lending & Housing', 'General Credit Union']
LETTER = {c: chr(ord('E') + i) for i, c in enumerate(MEDIA)}
print('\n-- verdict per media category --')
print('%-38s %-4s %-14s %-14s' % ('category', 'col', 'named by Table13', 'col letter ref'))
for c in MEDIA:
    print('%-38s %-4s %-14s %-14s' % (c, LETTER[c],
                                      cols_named.get(c, 0), sheet_cols.get(LETTER[c], 0)))
wb.close()
print('\nDONE R3c')
