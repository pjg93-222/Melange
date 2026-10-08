# -*- coding: utf-8 -*-
"""LANE A / R3 -- does every column the media blend writes reach the press pillar? (read-only)

build_media_blend writes 20 category columns into 'Press Release - Raw'.  Two of them
('General Credit Union', 'CU-Bank Competitive Dynamics') have no dashboard issue column.
This asks the workbook itself, by formula: which of those 20 columns are consumed downstream.

Loads the workbook twice: data_only=False (formulas) for the consumer scan.  Writes nothing.
"""
import os, sys, io, re, json, collections, datetime
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import openpyxl

ROOT = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WBP = os.path.join(ROOT, 'Moneyball Main Version - Blended.xlsx')
print('=' * 100)
print('R3  WORKBOOK CONSUMPTION OF THE MEDIA BLEND COLUMNS   run',
      datetime.datetime.now().isoformat(timespec='seconds'))
print('=' * 100)

wb = openpyxl.load_workbook(WBP, read_only=False, data_only=False)
print('sheets (%d):' % len(wb.sheetnames))
for s in wb.sheetnames:
    print('   %s' % s)

TARGET = 'Press Release - Raw'
pat = re.compile(r"'?Press Release - Raw'?!(\$?[A-Z]{1,3}\$?\d*(?::\$?[A-Z]{1,3}\$?\d*)?)")
hits = collections.Counter()
ref_by_sheet = collections.defaultdict(collections.Counter)
sample = collections.defaultdict(list)
scanned = 0
for ws in wb.worksheets:
    if ws.title == TARGET:
        continue
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not isinstance(v, str) or 'Press Release - Raw' not in v:
                continue
            scanned += 1
            for m in pat.findall(v):
                col = re.sub(r'[\$\d]', '', m.split(':')[0])
                hits[col] += 1
                ref_by_sheet[ws.title][col] += 1
                if len(sample[(ws.title, col)]) < 1:
                    sample[(ws.title, col)].append('%s!%s = %s' % (ws.title, c.coordinate, v[:220]))

print("\nformula cells referencing '%s': %d" % (TARGET, scanned))
print('\nreferencing sheets and the columns they pull:')
for sh, cols in sorted(ref_by_sheet.items()):
    print('   %-38s %s' % (sh, dict(sorted(cols.items()))))

COLLET = {5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L', 13: 'M', 14: 'N',
          15: 'O', 16: 'P', 17: 'Q', 18: 'R', 19: 'S', 20: 'T', 21: 'U', 22: 'V', 23: 'W', 24: 'X'}
HDRS = {5: 'Examination & Supervision', 6: 'Credit Union Capital Requirements',
        7: 'NCUA Budget & Share Insurance Fund', 8: 'Interchange', 9: 'Payments',
        10: 'Technology & Emerging Issues', 11: 'Fraud Prevention',
        12: 'Data Privacy & Cybersecurity', 13: 'Charter Modernization & Governance',
        14: 'Defense Credit Union Issues', 15: 'Field of Membership',
        16: 'Credit Union Tax Status', 17: 'CDFI Fund', 18: 'CU-Bank Competitive Dynamics',
        19: 'CFPB Issues & Structural Reform', 20: 'Credit Card & Consumer-Fee Mandates',
        21: 'Telephone Consumer Protection Act', 22: 'Member Business Lending',
        23: 'Mortgage Lending & Housing', 24: 'General Credit Union'}
print('\n-- per category column: is it referenced by any other sheet? --')
print('%-4s %-38s %-10s %s' % ('col', 'header', 'refs', 'referencing sheets'))
unconsumed = []
for idx in sorted(HDRS):
    L = COLLET[idx]
    n = hits.get(L, 0)
    shs = sorted(s for s, c in ref_by_sheet.items() if c.get(L))
    if n == 0:
        unconsumed.append((L, HDRS[idx]))
    print('%-4s %-38s %-10d %s' % (L, HDRS[idx], n, ', '.join(shs) or '(NONE)'))
print('\ncolumns written by the media blend but referenced by NO other sheet: %d' % len(unconsumed))
for L, h in unconsumed:
    print('   %s  %s' % (L, h))

print('\n-- sample formulas per (sheet, column) --')
for k in sorted(sample):
    print('   %s' % sample[k][0])

# whole-range references (e.g. 'Press Release - Raw'!$A:$X) are reported separately, because a
# range reference consumes EVERY column inside it regardless of the per-column tally above
print('\n-- range-style references (these consume every column in the range) --')
rng = re.compile(r"'?Press Release - Raw'?!\$?([A-Z]{1,3})\$?\d*:\$?([A-Z]{1,3})\$?\d*")
rcount = collections.Counter()
rsample = {}
for ws in wb.worksheets:
    if ws.title == TARGET:
        continue
    for row in ws.iter_rows():
        for c in row:
            v = c.value
            if not isinstance(v, str) or 'Press Release - Raw' not in v:
                continue
            for a, b in rng.findall(v):
                rcount[(ws.title, a, b)] += 1
                rsample.setdefault((ws.title, a, b), '%s!%s = %s' % (ws.title, c.coordinate, v[:220]))
for k, v in sorted(rcount.items(), key=lambda kv: -kv[1]):
    print('   %-34s %s:%s  x%d' % (k[0], k[1], k[2], v))
    print('       %s' % rsample[k])
wb.close()
print('\nDONE R3')
