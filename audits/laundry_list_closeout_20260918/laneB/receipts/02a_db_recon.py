# -*- coding: utf-8 -*-
"""LANE B recon: speeches-table schema, source values, C-SPAN identifiability, speaker-tag format.
READ-ONLY (sqlite3 mode=ro URI). Imports nothing from fec/."""
import collections, io, json, os, re, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=120)
con.execute('PRAGMA query_only=ON')

print('=== speeches schema ===')
for r in con.execute("SELECT sql FROM sqlite_master WHERE name='speeches'"):
    print(r[0])
print()
print('=== columns ===')
cols = [r[1] for r in con.execute('PRAGMA table_info(speeches)')]
print(cols)
print()
print('=== source value counts ===')
for src, n in con.execute('SELECT source, COUNT(*) FROM speeches GROUP BY source ORDER BY COUNT(*) DESC'):
    print('  %-28r %8d' % (src, n))
print()
print('=== total rows ===')
print(con.execute('SELECT COUNT(*) FROM speeches').fetchone()[0])
print()
for c in cols:
    if c.lower() in ('url', 'show', 'program', 'venue', 'network', 'outlet', 'channel', 'title', 'id', 'rowid'):
        print('=== distinct-ish %s (top 15) ===' % c)
        try:
            for v, n in con.execute('SELECT %s, COUNT(*) FROM speeches GROUP BY %s ORDER BY COUNT(*) DESC LIMIT 15' % (c, c)):
                print('  %-70r %6d' % (str(v)[:70], n))
        except Exception as e:
            print('  ERR %s' % e)
        print()

print('=== C-SPAN identifiability: rows whose any text column mentions c-span/cspan ===')
for c in cols:
    try:
        n = con.execute("SELECT COUNT(*) FROM speeches WHERE lower(CAST(%s AS TEXT)) LIKE '%%c-span%%' OR lower(CAST(%s AS TEXT)) LIKE '%%cspan%%'" % (c, c)).fetchone()[0]
        if n:
            print('  col %-14s %6d rows' % (c, n))
    except Exception as e:
        print('  col %-14s ERR %s' % (c, str(e)[:50]))
print()
print('=== INTERVIEW sample: first 3 texts, 1200 chars each (speaker-tag format) ===')
q = "SELECT member, date, source, substr(text,1,1200) FROM speeches WHERE source='INTERVIEW' AND text IS NOT NULL LIMIT 3"
for m, d, s, t in con.execute(q):
    print('-' * 70)
    print('member=%r date=%r source=%r' % (m, d, s))
    print(repr(t))
print()
print('=== CHRG sample: 2 texts, 900 chars ===')
for m, d, s, t in con.execute("SELECT member, date, source, substr(text,1,900) FROM speeches WHERE source='CHRG' AND text IS NOT NULL LIMIT 2"):
    print('-' * 70)
    print('member=%r date=%r' % (m, d))
    print(repr(t))
print()
print('=== CREC sample: 2 texts, 600 chars ===')
for m, d, s, t in con.execute("SELECT member, date, source, substr(text,1,600) FROM speeches WHERE source='CREC' AND text IS NOT NULL LIMIT 2"):
    print('-' * 70)
    print('member=%r date=%r' % (m, d))
    print(repr(t))
print()
print('=== speaker-tag pattern frequency inside INTERVIEW texts (sampled 400 rows) ===')
pats = {
    'ALLCAPS_NAME_COLON': re.compile(r'(?m)(?:^|[>\n]\s*|(?<=[.!?]\s))([A-Z][A-Z\.\' -]{2,40}):'),
    'ANGLE_ANGLE': re.compile(r'>>'),
    'PAREN_CROSSTALK': re.compile(r'\((?:CROSSTALK|LAUGHTER|INAUDIBLE)\)', re.I),
    'SEN_REP_TAG': re.compile(r'(?m)(?:SEN\.|REP\.|GOV\.|SENATOR|REPRESENTATIVE)\s+[A-Z][A-Z\' -]{2,30}:'),
    'NEWLINE': re.compile(r'\n'),
}
cnt = collections.Counter(); rows = 0; tot_len = 0
samples = collections.defaultdict(list)
for (t,) in con.execute("SELECT text FROM speeches WHERE source='INTERVIEW' AND text IS NOT NULL LIMIT 400"):
    rows += 1; tot_len += len(t)
    for nm, p in pats.items():
        ms = p.findall(t)
        if ms:
            cnt[nm] += 1
            if len(samples[nm]) < 6:
                samples[nm].append(ms[:4])
print('rows sampled %d | mean len %.0f' % (rows, tot_len / max(1, rows)))
for nm in pats:
    print('  %-20s in %4d/%d rows   eg %s' % (nm, cnt[nm], rows, samples[nm][:2]))
print()
print('=== same for CHRG (sampled 200) ===')
cnt2 = collections.Counter(); rows2 = 0
s2 = collections.defaultdict(list)
for (t,) in con.execute("SELECT text FROM speeches WHERE source='CHRG' AND text IS NOT NULL LIMIT 200"):
    rows2 += 1
    for nm, p in pats.items():
        ms = p.findall(t)
        if ms:
            cnt2[nm] += 1
            if len(s2[nm]) < 3:
                s2[nm].append(ms[:4])
for nm in pats:
    print('  %-20s in %4d/%d rows   eg %s' % (nm, cnt2[nm], rows2, s2[nm][:1]))
print()
print('=== same for CREC (sampled 200) ===')
cnt3 = collections.Counter(); rows3 = 0
for (t,) in con.execute("SELECT text FROM speeches WHERE source='CREC' AND text IS NOT NULL LIMIT 200"):
    rows3 += 1
    for nm, p in pats.items():
        if p.search(t):
            cnt3[nm] += 1
for nm in pats:
    print('  %-20s in %4d/%d rows' % (nm, cnt3[nm], rows3))
con.close()
print('DONE 02a')
