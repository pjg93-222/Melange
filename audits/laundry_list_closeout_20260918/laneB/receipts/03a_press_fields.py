# -*- coding: utf-8 -*-
"""LANE B P1 recon: what URL/domain evidence the PRESS and PRESS_OFFICIAL_MENTION feeds carry."""
import collections, csv, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DRAFT = os.path.abspath(os.path.join(LIVE, os.pardir, 'Draft Systems'))
om = os.path.join(LIVE, 'data', 'press', 'official_mentions.jsonl')

print('=== official_mentions.jsonl ===')
print('exists %s  %d bytes' % (os.path.exists(om), os.path.getsize(om) if os.path.exists(om) else 0))
keys = collections.Counter(); n = 0; first = None
rows = []
for ln in io.open(om, encoding='utf-8'):
    try: r = json.loads(ln)
    except ValueError: continue
    n += 1
    if first is None: first = r
    for k in r: keys[k] += 1
    rows.append(r)
print('lines: %d' % n)
print('field frequency: %s' % dict(keys))
print('FIRST ROW:')
print(json.dumps(first, indent=2, ensure_ascii=False)[:2500])
print()
print('=== candidate url/domain fields, sample values ===')
for fld in ('url', 'host_url', 'source_url', 'link', 'domain', 'host_domain', 'outlet', 'source', 'article_url'):
    vals = [str(r[fld])[:110] for r in rows if r.get(fld)][:5]
    print(' %-14s present=%-7d %s' % (fld, sum(1 for r in rows if r.get(fld)), vals))
print()
print('=== domain histogram over every url-ish field present ===')
from urllib.parse import urlsplit
for fld in ('url', 'host_url', 'source_url', 'link', 'article_url'):
    if not any(r.get(fld) for r in rows): continue
    h = collections.Counter()
    for r in rows:
        v = r.get(fld)
        if v:
            try: h[urlsplit(str(v)).netloc.lower()] += 1
            except ValueError: h['<unparseable>'] += 1
    print('-- %s : %d distinct hosts' % (fld, len(h)))
    for k, v in h.most_common(25):
        print('     %-52s %6d' % (k[:52], v))
print()
for p in (os.path.join(DRAFT, 'cu_press_stance_tone.csv'), os.path.join(LIVE, 'data', 'stance', 'press_refresh_tone.csv')):
    print('=== %s ===' % os.path.basename(p))
    print('exists %s  %d bytes' % (os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else 0))
    if os.path.exists(p):
        rd = csv.DictReader(io.open(p, encoding='utf-8-sig', newline=''))
        print('columns: %s' % rd.fieldnames)
        allr = list(rd)
        print('rows: %d' % len(allr))
        h = collections.Counter()
        for r in allr:
            try: h[urlsplit((r.get('url') or '')).netloc.lower()] += 1
            except ValueError: h['<unparseable>'] += 1
        print('top 20 hosts:')
        for k, v in h.most_common(20):
            print('   %-52s %6d' % (k[:52], v))
        own = sum(v for k, v in h.items() if '.house.gov' in k or '.senate.gov' in k)
        print('own-domain rows (.house.gov/.senate.gov): %d of %d' % (own, len(allr)))
    print()
print('DONE 03a')
