# -*- coding: utf-8 -*-
"""N12-v2 PROBE.  READ-ONLY.  Print the live text around every shape the gradeN12 FINDINGS names,
so the v2 grammar is written against the bytes rather than against a description of them."""
import io
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
DB = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\social_media.db'

GROUPS = [
    ('G1 NOT-SPEECH chyron inserts', [80238, 192027, 226287]),
    ('G1 WRONG-SPEAKER (Mike Johnson)', [245558]),
    ('G1 partial-foreign / no-space colon / UNIDENTIFIED', [68730, 102837, 104285, 108647,
                                                            111034, 242833]),
    ('G2a PBS anchor invisible to class D', [258736, 258820, 258130, 257343, 258713]),
    ('G2b abbreviation period satisfies the anchor', [82055, 71147, 70812, 205497]),
    ('G2c already the wrong person', [225986]),
    ('G2d class C keeps the next speaker NAME', [70149, 83941, 192133, 193439]),
    ('G3 member words removed', [83061]),
    ('G4 the five named rows', [69544, 244993, 278454, 278528, 66969]),
    ('gold / CU', [245771]),
]

con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
want = sorted({r for _n, ids in GROUPS for r in ids})
rows = {r[0]: r for r in con.execute(
    'SELECT rowid,member,date,source,chamber,package,nwords,text FROM speeches '
    'WHERE rowid IN (%s)' % ','.join('?' * len(want)), want)}

PROBE = [
    ('no-space colon after an ALL-CAPS tag', re.compile(r"\b[A-Z][A-Z.'`\u2019\-]{2,}:(?=[A-Za-z])")),
    ('U+2019 inside an ALL-CAPS token', re.compile(r"\b[A-Z]{1,12}\u2019[A-Z]{1,12}\b")),
    ('UNIDENTIFIED / UNKNOWN role label', re.compile(r'\b(?:UNIDENTIFIED|UNKNOWN)\s+[A-Z]+')),
    ('role tail after (R-XX) / (R)', re.compile(r'\([RDI](?:-[A-Z]{2})?\),?\s+[A-Z][A-Z .,&\'\-]{6,}')),
    ('bare Q: turn', re.compile(r'(?:^|(?<=[.?!])) ?Q:\s')),
    ('dotted abbreviation then an ALL-CAPS run',
     re.compile(r"\b[A-Z](?:\.[A-Z])+\.\s+[A-Z][A-Z'`\u2019\-]{2,}")),
]

for name, ids in GROUPS:
    print('=' * 100)
    print(name)
    print('=' * 100)
    for rid in ids:
        r = rows.get(rid)
        if not r:
            print('  rowid %s NOT FOUND' % rid)
            continue
        _rid, member, date, source, chamber, package, nwords, text = r
        text = text or ''
        print('-' * 96)
        print('rowid=%-7d %-24s %s  show=%-22s nwords=%s len=%d'
              % (rid, member[:24], date, str(chamber)[:22], nwords, len(text)))
        print('  pkg=%s' % str(package)[:92])
        hits = []
        for pname, rx in PROBE:
            for m in rx.finditer(text):
                hits.append((m.start(), pname, text[max(0, m.start() - 60):m.start() + 90]))
        hits.sort()
        for pos, pname, ctx in hits[:8]:
            print('  [%-42s @%6d] %s' % (pname, pos, ' '.join(ctx.split())))
        print('  HEAD  %s' % ' '.join(text[:300].split()))
        if len(text) > 300:
            print('  TAIL  %s' % ' '.join(text[-220:].split()))
con.close()

# corpus-wide censuses for the same shapes, so the fix has a denominator
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
cnt = {name: 0 for name, _ in PROBE}
ex = {name: [] for name, _ in PROBE}
n = 0
for rid, mem, cham, text in con.execute(
        "SELECT rowid,member,chamber,text FROM speeches WHERE source='INTERVIEW'"):
    n += 1
    t = text or ''
    for pname, rx in PROBE:
        m = rx.search(t)
        if m:
            cnt[pname] += 1
            if len(ex[pname]) < 6:
                ex[pname].append((rid, mem, cham,
                                  ' '.join(t[max(0, m.start() - 70):m.start() + 100].split())))
con.close()
print()
print('=' * 100)
print('CORPUS-WIDE CENSUS over %d INTERVIEW rows' % n)
print('=' * 100)
for pname, _rx in PROBE:
    print('%-52s %6d rows' % (pname, cnt[pname]))
    for rid, mem, cham, ctx in ex[pname]:
        print('      %-7d %-22s %-18s %s' % (rid, str(mem)[:22], str(cham)[:18], ctx[:150]))
with io.open(os.path.join(HERE, 'v2_probe_census.json'), 'w', encoding='utf-8') as fh:
    json.dump({'interview_rows': n, 'counts': cnt}, fh, indent=1, sort_keys=True)
print('DONE')
