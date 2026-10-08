# -*- coding: utf-8 -*-
"""measR1d U2c: the FIFTH residual class -- COLON-LESS foreign tags.

D-U2 and U2b both anchor on a colon.  Lane B's 04b showed the splitter sometimes loses the colon
entirely ("... SEN. RICHARD BLUMENTHAL, D-CONN.There's a gra..."), which no colon-anchored
detector can see.  This re-runs lane B's NOCOLON regex VERBATIM over every INTERVIEW row, drops
self-naming tags, and reports how many rows it adds on top of D-U2 + R1-R4.  READ-ONLY.
"""
import collections, io, json, os, re, sqlite3, sys, unicodedata

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PK = os.path.dirname(os.path.abspath(__file__))
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'

# lane B 04b_p2_colonless.py:32-35, verbatim
HON = (r'(?:SEN\.|REP\.|PRES\.|GOV\.|DR\.|FMR\.|AMB\.|SENATOR|REPRESENTATIVE|CONGRESSMAN|'
       r'CONGRESSWOMAN|CHAIRMAN|CHAIRWOMAN|PRESIDENT|GOVERNOR|SPEAKER)')
TAIL = r'(?:\s*,\s*[RDI]-[A-Z][A-Z\.]{1,14}\.?|\s*\([RDI]-[A-Z]{2}[^)]{0,22}\)|\s*\([^)]{1,22}\))?'
NOCOLON = re.compile(HON + r'\s+[A-Z][A-Z\'\.\-]{1,22}(?:\s+[A-Z][A-Z\'\.\-]{1,22}){0,3}' + TAIL)


def nrm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c)).replace('`', "'")
    return re.sub(r'[^a-z ]', '', s.lower()).strip()


def allcaps(t):
    L = [c for c in t if c.isalpha()]
    return bool(L) and sum(1 for c in L if c.isupper()) / len(L) > 0.85


flag = {r['rowid'] for r in json.load(io.open(os.path.join(PK, 'U2_flagged_rows.json'), encoding='utf-8'))}
res = json.load(io.open(os.path.join(PK, 'U2b_residual_rows.json'), encoding='utf-8'))
resids = {r['rowid'] for k in res for r in res[k]}

con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True, timeout=300)
con.execute('PRAGMA query_only=ON')
rows = con.execute("SELECT rowid, member, chamber, text FROM speeches WHERE source='INTERVIEW'").fetchall()
con.close()

hit, tg = [], collections.Counter()
for rid, mem, cham, t in rows:
    if not t or allcaps(t):
        continue
    mp = nrm(mem).split()
    msur = mp[-1] if mp else ''
    for m in NOCOLON.finditer(t):
        toks = [nrm(w) for w in re.split(r'[^A-Za-z]+', m.group(0)) if w]
        if msur and msur in toks:
            continue
        hit.append((rid, mem, cham, m.start(), m.group(0), t))
        tg[' '.join(m.group(0).split())] += 1
        break

ids = {h[0] for h in hit}
new = ids - flag - resids
print('R5 colon-less (NOCOLON, non-self) rows : %d' % len(ids))
print('    already in D-U2 flagged            : %d' % len(ids & flag))
print('    already in R1-R4                   : %d' % len(ids & resids))
print('    NEW rows added by R5               : %d' % len(new))
print('    top tags:')
for s, n in tg.most_common(10):
    print('      %5d  %s' % (n, s[:62]))
print()
print('    6 NEW examples:')
c = 0
for rid, mem, cham, a, tag, t in hit:
    if rid not in new:
        continue
    print('    rowid=%s mem=%s show=%s tag=%r' % (rid, mem, cham, tag))
    print('      B: ...%s' % ' '.join(t[max(0, a - 110):a].split()))
    print('      A: %s...' % ' '.join(t[a:a + 250].split()))
    c += 1
    if c >= 6:
        break
tot = len(flag | resids | new)
print()
print('CORRECTED TOTAL affected INTERVIEW rows: %d of %d (%.3f%%)' % (tot, len(rows), 100.0 * tot / len(rows)))
io.open(os.path.join(PK, 'U2c_colonless_new_ids.json'), 'w', encoding='utf-8').write(json.dumps(sorted(new)))
io.open(os.path.join(PK, 'U2c_all_affected_ids.json'), 'w', encoding='utf-8').write(
    json.dumps(sorted(flag | resids | new)))
print('wrote U2c_colonless_new_ids.json, U2c_all_affected_ids.json')
print('DONE U2c')
