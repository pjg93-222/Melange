# -*- coding: utf-8 -*-
"""LANE B recon 2: FULL-CORPUS census of speaker-tag / turn-boundary artefacts and the
`package` field (C-SPAN identifiability).  Not a sample -- every row.
READ-ONLY (sqlite3 mode=ro). Imports nothing from fec/."""
import collections, re, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=180)
con.execute('PRAGMA query_only=ON')

# ---- speaker-tag candidates.  A turn-segmented corpus should show ~zero of these.
TAG = re.compile(r'(?:^|(?<=[\s>"\u201c])) ?((?:SEN\.|REP\.|GOV\.|DR\.|MR\.|MS\.|MRS\.|SENATOR|REPRESENTATIVE|CHAIRMAN|CHAIRWOMAN)?\s?[A-Z][A-Z\.\'-]{2,24}(?:\s+[A-Z][A-Z\.\'-]{1,24})?)\s*:')
ANGLE = re.compile(r'>>')
NL = re.compile(r'[\r\n]')
BRACKET = re.compile(r'\[(?:CROSSTALK|LAUGHTER|INAUDIBLE|APPLAUSE)\]|\((?:CROSSTALK|LAUGHTER|INAUDIBLE|APPLAUSE)\)', re.I)

print('=' * 78)
print('FULL-CORPUS TURN-ARTEFACT CENSUS (every speeches row)')
print('=' * 78)
per = collections.defaultdict(lambda: collections.Counter())
lens = collections.defaultdict(list)
tag_examples = collections.defaultdict(list)
n = 0
for src, txt, mem, pkg in con.execute('SELECT source, text, member, package FROM speeches'):
    n += 1
    if not txt:
        per[src]['null_or_empty_text'] += 1
        continue
    c = per[src]
    c['rows'] += 1
    L = len(txt)
    c['chars'] += L
    if L > 2000:
        c['len_gt_2000'] += 1
    if L > 6000:
        c['len_gt_6000'] += 1
    if NL.search(txt):
        c['has_newline'] += 1
    if ANGLE.search(txt):
        c['has_>>'] += 1
    if BRACKET.search(txt):
        c['has_crosstalk_marker'] += 1
    m = TAG.search(txt)
    if m:
        c['has_ALLCAPS_tag'] += 1
        if len(tag_examples[src]) < 12:
            tag_examples[src].append((mem, m.group(1), txt[max(0, m.start() - 60):m.end() + 60]))
print('rows scanned: %d' % n)
for src in sorted(per):
    c = per[src]
    print()
    print('-- source=%r  rows=%d  mean_len=%.0f' % (src, c['rows'], c['chars'] / max(1, c['rows'])))
    for k in ('null_or_empty_text', 'len_gt_2000', 'len_gt_6000', 'has_newline', 'has_>>',
              'has_crosstalk_marker', 'has_ALLCAPS_tag'):
        print('     %-22s %8d  (%.3f%%)' % (k, c[k], 100.0 * c[k] / max(1, c['rows'])))
print()
print('=== ALLCAPS-tag examples (these are the only turn-boundary candidates) ===')
for src in sorted(tag_examples):
    print('-- %s' % src)
    for mem, tag, ctx in tag_examples[src]:
        print('   member=%-24s tag=%-22r ctx=%r' % (mem[:24], tag, ' '.join(ctx.split())[:150]))

print()
print('=' * 78)
print('`package` FIELD -- C-SPAN IDENTIFIABILITY')
print('=' * 78)
for src in ('INTERVIEW', 'CHRG', 'CREC'):
    rows = con.execute("SELECT COUNT(*), COUNT(DISTINCT package) FROM speeches WHERE source=?", (src,)).fetchone()
    print('%-10s rows=%d distinct package=%d' % (src, rows[0], rows[1]))
print()
print('=== top 25 package values overall ===')
for v, k in con.execute('SELECT package, COUNT(*) FROM speeches GROUP BY package ORDER BY COUNT(*) DESC LIMIT 25'):
    print('  %-62r %7d' % (str(v)[:62], k))
print()
print('=== rows whose package matches c-span/cspan, by source ===')
for src, k in con.execute("SELECT source, COUNT(*) FROM speeches WHERE lower(package) LIKE '%c-span%' OR lower(package) LIKE '%cspan%' GROUP BY source"):
    print('  %-12s %7d' % (src, k))
print()
print('=== distinct c-span package values (top 30) ===')
for v, k in con.execute("SELECT package, COUNT(*) FROM speeches WHERE lower(package) LIKE '%c-span%' OR lower(package) LIKE '%cspan%' GROUP BY package ORDER BY COUNT(*) DESC LIMIT 30"):
    print('  %-62r %7d' % (str(v)[:62], k))
print()
print('=== INTERVIEW package prefix census (token before first "_" or ":") ===')
pre = collections.Counter()
for (v,) in con.execute("SELECT package FROM speeches WHERE source='INTERVIEW'"):
    s = str(v or '')
    pre[re.split(r'[_:|/]', s)[0][:40]] += 1
for v, k in pre.most_common(30):
    print('  %-44r %7d' % (v, k))
con.close()
print('DONE 02b')
