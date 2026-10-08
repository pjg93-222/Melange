# -*- coding: utf-8 -*-
"""LANE B step 2 (part 1): totals straight out of the shipped artifact + cache + receipt.
READ-ONLY. Imports nothing from fec/. Stdlib only."""
import collections, datetime, hashlib, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
ART = LIVE + r'\member_references.json'
CACHE = LIVE + r'\data\members\member_reference_cache_fable.jsonl'
RECEIPT = LIVE + r'\data\members\member_reference_classification_receipt.json'
BASELINE = LIVE + r'\data\members\member_reference_cache_baseline_v2.json'
VERIFY = LIVE + r'\data\members\member_reference_verify.csv'
POLICY = LIVE + r'\data\engine\sentinel_admission_policy.json'


def mt(p):
    if not os.path.exists(p):
        return 'MISSING'
    st = os.stat(p)
    return '%s  %d bytes' % (datetime.datetime.fromtimestamp(st.st_mtime).isoformat(sep=' ')[:19], st.st_size)


print('=' * 78)
print('FILE MTIMES / SIZES')
print('=' * 78)
for p in (ART, CACHE, RECEIPT, BASELINE, VERIFY, POLICY):
    print('%-52s %s' % (os.path.basename(p), mt(p)))

d = json.load(io.open(ART, encoding='utf-8'))
E = d['edges']
print()
print('=' * 78)
print('ARTIFACT member_references.json')
print('=' * 78)
print('top-level keys        : %s' % sorted(d))
print('dyad_cap              : %r' % d.get('dyad_cap'))
print('model (as written)    : %r' % d.get('model'))
print('provenance            : %r' % d.get('provenance'))
print('edges                 : %d' % len(E))
print('edge keys (first edge): %s' % sorted(E[0]))
print('sum n_raw             : %d' % sum(e['n_raw'] for e in E))
print('sum n_scored          : %d' % sum(e['n_scored'] for e in E))
print('sum pos/neg/neu/form  : %d / %d / %d / %d' % (sum(e['pos'] for e in E), sum(e['neg'] for e in E),
                                                     sum(e['neu'] for e in E),
                                                     sum(e.get('formality_dropped', 0) for e in E)))
print('edges n_scored>=2     : %d   (consumer drawing floor, build_dashboard_bundle.py:238)' %
      sum(1 for e in E if e['n_scored'] >= 2))
print('edges n_scored<2      : %d' % sum(1 for e in E if e['n_scored'] < 2))
print('edges n_scored==0     : %d' % sum(1 for e in E if e['n_scored'] == 0))
print('signed edges (pos+neg>0): %d' % sum(1 for e in E if e['pos'] + e['neg'] > 0))
print('net>0.2 / net<-0.2    : %d / %d' % (sum(1 for e in E if e['net'] > 0.2), sum(1 for e in E if e['net'] < -0.2)))
print('examples attached     : %d edges with >=1 example, %d with 2' %
      (sum(1 for e in E if e.get('examples')), sum(1 for e in E if len(e.get('examples') or []) == 2)))

print()
print('RAW MENTIONS BY SOURCE (artifact `sources` counters, summed over edges)')
src = collections.Counter()
for e in E:
    for k, v in (e.get('sources') or {}).items():
        src[k] += v
for k, v in src.most_common():
    print('  %-24s %8d' % (k, v))
print('  %-24s %8d   (== sum n_raw: %s)' % ('TOTAL', sum(src.values()), sum(src.values()) == sum(e['n_raw'] for e in E)))

print()
print('EDGES TOUCHING EACH SOURCE (an edge can touch several)')
ed_src = collections.Counter()
for e in E:
    for k in (e.get('sources') or {}):
        ed_src[k] += 1
for k, v in ed_src.most_common():
    print('  %-24s %8d edges' % (k, v))

print()
print('EXAMPLES BY SOURCE (the only window text the artifact retains)')
ex_src = collections.Counter()
for e in E:
    for x in (e.get('examples') or []):
        ex_src[x.get('src') or '?'] += 1
for k, v in ex_src.most_common():
    print('  %-24s %8d' % (k, v))
print('  NOTE: artifact stores at most 2 windows/edge -> per-source SCORED counts are NOT')
print('        recoverable from the artifact; they require re-derivation (script 02).')

print()
print('=' * 78)
print('CACHE %s' % os.path.basename(CACHE))
print('=' * 78)
n_lines = n_bad = 0
keys = collections.Counter()
models = collections.Counter()
transports = collections.Counter()
cls = collections.Counter()
prov_keys = collections.Counter()
prov_models = collections.Counter()
first_seen = {}
v1 = v2 = 0
any_ts = []
for i, ln in enumerate(io.open(CACHE, encoding='utf-8')):
    ln = ln.strip()
    if not ln:
        continue
    n_lines += 1
    try:
        r = json.loads(ln)
    except Exception:
        n_bad += 1
        continue
    k = r.get('k')
    keys[k] += 1
    if k not in first_seen:
        first_seen[k] = i
    models[r.get('model', '<absent>')] += 1
    transports[r.get('transport', '<absent>')] += 1
    o = r.get('out') or {}
    cls[o.get('cls', '<none>')] += 1
    p = r.get('classifier') or {}
    if isinstance(p, dict):
        for pk in p:
            prov_keys[pk] += 1
        if p.get('model'):
            prov_models[p['model']] += 1
        for tk in ('timestamp', 'created_at', 'date', 'ts', 'checked_at'):
            if p.get(tk):
                any_ts.append(p[tk])
    if str(k).startswith('v2:'):
        v2 += 1
    else:
        v1 += 1
print('cache lines            : %d  (unparseable %d)' % (n_lines, n_bad))
print('distinct keys          : %d' % len(keys))
print('duplicate-key lines    : %d  (first-wins per member_reference_layer.py:238-243)' %
      (n_lines - len(keys)))
print('keys with v2: prefix   : %d   legacy/other prefix: %d' % (v2, v1))
print('model field            : %s' % dict(models))
print('transport field        : %s' % dict(transports))
print('cls distribution       : %s' % dict(cls))
print('classifier-provenance keys present: %s' % dict(prov_keys))
print('classifier.model values: %s' % dict(prov_models.most_common(10)))
print('per-row timestamps found: %d  -> CACHE DATE RANGE FROM ROWS = %s' %
      (len(any_ts), (min(any_ts) + ' .. ' + max(any_ts)) if any_ts else 'UNKNOWN (no timestamp field in any row)'))

print()
print('=' * 78)
print('CLASSIFICATION RECEIPT')
print('=' * 78)
if os.path.exists(RECEIPT):
    print(json.dumps(json.load(io.open(RECEIPT, encoding='utf-8')), indent=2, sort_keys=True))
else:
    print('MISSING')

print()
print('SENTINEL ADMISSION POLICY (reference_* keys drive model/transport at line 213-216)')
if os.path.exists(POLICY):
    pol = json.load(io.open(POLICY, encoding='utf-8'))
    print(json.dumps({k: v for k, v in pol.items() if 'reference' in k.lower()}, indent=2, sort_keys=True))
    print('full policy keys: %s' % sorted(pol))
else:
    print('MISSING')

print()
print('=' * 78)
print('BASELINE member_reference_cache_baseline_v2.json')
print('=' * 78)
if os.path.exists(BASELINE):
    b = json.load(io.open(BASELINE, encoding='utf-8'))
    print('schema     : %r' % b.get('schema'))
    print('provenance : %r' % b.get('provenance'))
    print('bindings   : %d' % len(b.get('bindings') or {}))
    print('ambiguous  : %d' % len(b.get('ambiguous') or []))
else:
    print('MISSING')

print()
print('=' * 78)
print('STEP 7: member_reference_verify.csv vs artifact')
print('=' * 78)
if os.path.exists(VERIFY):
    import csv
    rows = list(csv.reader(io.open(VERIFY, encoding='utf-8-sig', newline='')))
    hdr, body = rows[0], rows[1:]
    body = [r for r in body if any((c or '').strip() for c in r)]
    va, aa = os.stat(VERIFY).st_mtime, os.stat(ART).st_mtime
    print('path      : %s' % VERIFY)
    print('mtime     : %s' % datetime.datetime.fromtimestamp(va).isoformat(sep=' ')[:19])
    print('artifact  : %s' % datetime.datetime.fromtimestamp(aa).isoformat(sep=' ')[:19])
    print('OLDER THAN ARTIFACT: %s   (delta %.1f days)' % (va < aa, (aa - va) / 86400.0))
    print('header    : %s' % hdr)
    print('data rows : %d   (writer caps at 500, member_reference_layer.py:364)' % len(body))
    print('artifact edges now: %d  -> rows cover %.2f%% of current edges' % (len(E), 100.0 * len(body) / len(E)))
    filled = sum(1 for r in body if len(r) > 10 and (r[10] or '').strip())
    print('owner verdict column filled: %d of %d rows' % (filled, len(body)))
else:
    print('MISSING')
print()
print('DONE 01')
