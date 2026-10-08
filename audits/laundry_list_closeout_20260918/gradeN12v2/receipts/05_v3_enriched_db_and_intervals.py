# -*- coding: utf-8 -*-
"""V3 enriched stratum + LIVE-DB reconciliation + exact binomial intervals.

DATABASE ACCESS IS READ-ONLY: sqlite3 URI file:...?mode=ro plus PRAGMA query_only=ON.
No production module is imported.
"""
import hashlib
import io
import json
import math
import random
import re
import sqlite3
import sys
import unicodedata

LEDGER, DB, OUTDIR = sys.argv[1], sys.argv[2], sys.argv[3]
_AP = "'`\u2019\u2018\u02bc"


def norm(s):
    s = unicodedata.normalize('NFD', s or '')
    s = ''.join(c for c in s if not unicodedata.combining(c))
    for ch in _AP:
        s = s.replace(ch, "'")
    return re.sub(r"[^a-z ]", '', s.lower()).strip()


def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(0, k + 1))


def clopper_pearson(k, n):
    """Exact 95% interval, by bisection on the binomial CDF."""
    if n == 0:
        return (0.0, 1.0)
    lo = 0.0 if k == 0 else _solve(lambda p: binom_cdf(k - 1, n, p) - 0.975)
    hi = 1.0 if k == n else _solve(lambda p: binom_cdf(k, n, p) - 0.025)
    return (lo, hi)


def _solve(f):
    a, b = 0.0, 1.0
    for _ in range(200):
        m = (a + b) / 2.0
        if f(m) > 0:
            a = m
        else:
            b = m
    return (a + b) / 2.0


rows, truncated = {}, []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        rows[r['rowid']] = r
        if not r['skip']:
            truncated.append(r)

out = io.open(OUTDIR + '/V3V5_enriched_db_intervals.txt', 'w', encoding='utf-8', newline='\n')


def W(s=''):
    out.write(s + '\n')


# ---------------------------------------------------- 1. LIVE-DB reconciliation (read-only)
con = sqlite3.connect('file:%s?mode=ro' % DB.replace('\\', '/'), uri=True)
con.execute('PRAGMA query_only=ON')
W('=' * 100)
W('1.  LIVE DATABASE RECONCILIATION  (file:...?mode=ro, PRAGMA query_only=ON, no writes)')
W('=' * 100)
n_rows, n_iv = con.execute(
    "SELECT (SELECT COUNT(*) FROM speeches),"
    " (SELECT COUNT(*) FROM speeches WHERE source='INTERVIEW')").fetchone()
W('speeches rows=%d  INTERVIEW rows=%d' % (n_rows, n_iv))
ledger_tbl = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND "
                         "name='speeches_turn_split_ledger'").fetchone()[0]
W('ledger table already present in the live db: %s  (0 = the migration has never been applied)'
  % ledger_tbl)
mism, missing, ok = [], [], 0
for rid, r in rows.items():
    got = con.execute('SELECT text,nwords,member FROM speeches WHERE rowid=?', (rid,)).fetchone()
    if got is None:
        missing.append(rid)
        continue
    if got[0] == r['original']['text'] and got[2] == r['member']:
        ok += 1
    else:
        mism.append(rid)
W('flagged rowids whose LIVE text still equals the ledger original: %d of %d' % (ok, len(rows)))
W('   mismatched: %d %s' % (len(mism), mism[:20]))
W('   missing:    %d %s' % (len(missing), missing[:20]))

# corpus-wide censuses the v1 grade quoted, re-measured on the live text
cur = con.execute("SELECT rowid,member,text FROM speeches WHERE source='INTERVIEW'")
CURLY_TAG = re.compile(r'(?:^|(?<=[.?!])|(?<=--)|(?<=\u2014))\s*[A-Z][A-Z.\u2019\'`\- ]{1,40}'
                       r'\u2019[A-Z][A-Z.\u2019\'`\- ]{0,40}\s*(?:\([^)]{1,30}\))?:')
NOSPACE = re.compile(r'(?:^|(?<=[.?!])|(?<=--)|(?<=\u2014))\s*[A-Z][A-Z.\'`\u2019\- ]{2,50}:[A-Za-z]')
BAREQ = re.compile(r'(?:^|(?<=[.?!]))\s*Q:\s')
c_curly = c_nospace = c_bareq = 0
curly_ids, nospace_ids, bareq_ids = [], [], []
for rid, member, text in cur:
    if not text:
        continue
    if CURLY_TAG.search(text):
        c_curly += 1
        curly_ids.append(rid)
    if NOSPACE.search(text):
        c_nospace += 1
        nospace_ids.append(rid)
    if BAREQ.search(text):
        c_bareq += 1
        bareq_ids.append(rid)
con.close()
flagged = set(rows)
W()
W('corpus-wide shapes the v1 grade called UNDER-REPAIR, re-measured on the live INTERVIEW text:')
for name, ids in (('curly-apostrophe ALL-CAPS tag', curly_ids),
                  ('no-space colon after an ALL-CAPS tag', nospace_ids),
                  ('bare "Q: " turn', bareq_ids)):
    f = len(set(ids) & flagged)
    t = len([i for i in ids if i in rows and not rows[i]['skip']])
    W('   %-38s rows=%-6d flagged by v2=%-5d truncated by v2=%-5d still untouched=%d'
      % (name, len(ids), f, t, len(ids) - f))

# ------------------------------------------------------- 2. V3 enriched member-return stratum
W()
W('=' * 100)
W('2.  V3 ENRICHED STRATUM -- the 83061 shape: the removed text NAMES the row member in the')
W('    third person AND carries a sentence-initial first person, i.e. where an UNTAGGED return')
W('    to the member would hide.  Seeded sample (20260920) of 30 read in full.')
W('=' * 100)
FP = re.compile(r'(?:^|(?<=[.?!])|(?<=--)|(?<=\u2014))\s*(?:I|I\'m|I\'ve|I\'d|My|We|We\'re|Our)\b')
enriched = []
for r in truncated:
    msur = (norm(r['member']).split() or [''])[-1]
    rem = r['removed']['raw']
    if not msur or len(msur) < 4:
        continue
    if msur in norm(rem).split() and FP.search(rem):
        enriched.append(r)
W('enriched stratum size: %d of %d truncated rows (%.2f%%)'
  % (len(enriched), len(truncated), 100.0 * len(enriched) / len(truncated)))
rnd = random.Random(20260920)
samp = sorted(rnd.sample(enriched, min(30, len(enriched))), key=lambda r: r['rowid'])
W('sampled rowids: %s' % [r['rowid'] for r in samp])
W()
for i, r in enumerate(samp, 1):
    W('--- %02d rowid=%s member=%r %s removed=%sw segs=%d cut_tag=%r'
      % (i, r['rowid'], r['member'], r['date'], r['removed']['nwords'],
         len(r['removed']['segments']), r['cut_tag']))
    W('    KEPT ...%s' % r['kept']['text'][-160:])
    for s in r['removed']['segments']:
        b = s['text'] or ''
        W('    seg tag=%r (%dw)' % (s['tag'], s['nwords']))
        W('       %s' % b[:320].replace('\n', ' '))
        if len(b) > 460:
            W('       ...TAIL: %s' % b[-320:].replace('\n', ' '))
    W()

# ------------------------------------------- 3. what a smarter OWN-tag rule could recover
W('=' * 100)
W('3.  ROWS WITH AN EXPLICIT OWN-MEMBER TAG AFTER THE CUT (a smarter rule could keep these)')
W('=' * 100)
tot_own_words = 0
n_own_rows = 0
for r in truncated:
    msur = (norm(r['member']).split() or [''])[-1]
    owned = [s for s in r['removed']['segments']
             if s['ownership'] == 'own' or (msur and msur in norm(s['tag']).split())]
    if owned:
        n_own_rows += 1
        w = sum(s['nwords'] for s in owned)
        tot_own_words += w
        W('   rowid=%-7s %-24s own-tagged segments=%d words=%d  tags=%s'
          % (r['rowid'], r['member'][:24], len(owned), w,
             sorted({s['tag'] for s in owned})))
W('   rows=%d  words recoverable by an own-tag rule=%d' % (n_own_rows, tot_own_words))

# ------------------------------------------------------------------ 4. exact intervals
W()
W('=' * 100)
W('4.  EXACT (CLOPPER-PEARSON) 95%% INTERVALS')
W('=' * 100)


def line(label, k, n, scale=None):
    lo, hi = clopper_pearson(k, n)
    s = '   %-46s %3d/%-4d = %6.4f   95%% CI %.4f - %.4f' % (label, k, n, k / float(n), lo, hi)
    if scale:
        s += '   -> %d of %d rows (CI %d - %d)' % (round(k / float(n) * scale), scale,
                                                   math.floor(lo * scale), math.ceil(hi * scale))
    W(s)


N = len(truncated)
line('V2 sample: FOREIGN-TAG-REAL', 90, 90)
line('V2 sample: CUT-TOO-EARLY', 0, 90, N)
line('V2 sample: UNCLEAR', 0, 90, N)
line('V3 sample: member words removed (SOME)', 0, 90, N)
line('V3 enriched stratum: SOME (see section 2)', 1, 30, len(enriched))
for cls in sorted({r['cut_class'] for r in truncated}):
    k = sum(1 for r in truncated if r['cut_class'] == cls)
    line('  per-class n in sample (15 each), pool=%s' % cls, 15, 15)
W()
W('   truncated rows N = %d' % N)
W('   per-class pools: %s' % json.dumps(
    {c: sum(1 for r in truncated if r['cut_class'] == c)
     for c in sorted({r['cut_class'] for r in truncated})}))
out.close()
print('written; enriched=%d own_rows=%d own_words=%d' % (len(enriched), n_own_rows,
                                                         tot_own_words))
