# -*- coding: utf-8 -*-
"""LANE D read-only measurement. Reads named LIVE paths only; no fec/ imports, no writes to LIVE."""
import json, os, glob, time, collections, hashlib, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
R = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'

def ts(p):
    try:
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(os.path.getmtime(p)))
    except OSError as e:
        return 'MISSING (%s)' % e.__class__.__name__

def load(p):
    with open(p, encoding='utf-8') as h:
        return json.load(h)

print('=' * 78)
print('E6  FRESHNESS / MTIMES')
print('=' * 78)
vcl = R + r'\vote_category_lean.json'
arch = sorted(glob.glob(R + r'\congress_bills_archive_*.xlsx'))          # audit_full uses sorted() = NAME order
arch_by_mtime = sorted(arch, key=os.path.getmtime)
print('vote_category_lean.json        %s  mtime %s' % (os.path.exists(vcl), ts(vcl)))
print('archive_leg.json               mtime %s' % ts(R + r'\archive_leg.json'))
print('congress_bills_archive_*.xlsx  count %d' % len(arch))
for p in arch:
    print('    %-46s  %s' % (os.path.basename(p), ts(p)))
print('audit picks sorted()[-1] (NAME order) : %s' % (os.path.basename(arch[-1]) if arch else 'n/a'))
print('newest by MTIME                      : %s' % (os.path.basename(arch_by_mtime[-1]) if arch_by_mtime else 'n/a'))
if arch and os.path.exists(vcl):
    newest = arch[-1]
    dt = os.path.getmtime(vcl) - os.path.getmtime(newest)
    stale = os.path.getmtime(vcl) < os.path.getmtime(newest) - 30 * 86400
    print('vcl_mtime - archive_mtime = %+.2f days   (>30d behind => STALE)' % (dt / 86400.0))
    print('audit_full _stale  = %s   -> check "not _stale" would %s' % (stale, 'FAIL' if stale else 'PASS'))
    n2 = arch_by_mtime[-1]
    s2 = os.path.getmtime(vcl) < os.path.getmtime(n2) - 30 * 86400
    print('same test vs newest-by-mtime: delta %+.2f d, stale=%s' % (
        (os.path.getmtime(vcl) - os.path.getmtime(n2)) / 86400.0, s2))

print()
print('-- culling check inputs (audit_full.py:1906-1921) --')
cp = R + r'\data\legislation\legislation_culling_status.json'
print('legislation_culling_status.json  exists %s  mtime %s' % (os.path.exists(cp), ts(cp)))
if os.path.exists(cp):
    cs = load(cp)
    for k in ('status', 'phase', 'promotion_performed', 'production_workbook_written', 'rank_written'):
        print('   %-32s %r' % (k, cs.get(k)))
    print('   %-32s %r' % ('promotion_receipt.status', (cs.get('promotion_receipt') or {}).get('status')))
    ok = (cs.get('status') == 'PASS_PRODUCTION_CULLING_INTEGRATED' and cs.get('phase') == 'production'
          and cs.get('promotion_performed') is True and cs.get('production_workbook_written') is True
          and cs.get('rank_written') is True
          and (cs.get('promotion_receipt') or {}).get('status') == 'PASS_PRODUCTION_INPUTS_PROMOTED')
    print('   => culling promotion check would %s' % ('PASS' if ok else 'FAIL'))
    cc = cs.get('counts') or {}
    ledger = (cc.get('scoring_ready_candidates') == 60 and cc.get('scoring_ready_category_edges') == 74
              and cc.get('held_decision_units') == 1184
              and (cc.get('integration_state_counts') or {}).get('excluded_false_positive') == 2908)
    print('   counts: cand=%r edges=%r held=%r excl_fp=%r' % (
        cc.get('scoring_ready_candidates'), cc.get('scoring_ready_category_edges'),
        cc.get('held_decision_units'), (cc.get('integration_state_counts') or {}).get('excluded_false_positive')))
    print('   => culling ledger check would %s' % ('PASS' if ledger else 'FAIL'))

print()
print('=' * 78)
print('E4  ELECTORAL FRONTIER SEED ORDER')
print('=' * 78)
for name in ('budget_frontier_electoral.json', 'budget_frontier.json'):
    p = R + r'\data\money\%s' % name
    print()
    print('### %s   mtime %s' % (name, ts(p)))
    if not os.path.exists(p):
        print('    MISSING')
        continue
    d = load(p)
    print('    sha256 %s' % hashlib.sha256(open(p, 'rb').read()).hexdigest().upper()[:16])
    print('    mode=%r leverage=%r topic=%r  topics=%d' % (
        d.get('mode'), d.get('leverage'), d.get('topic'), len(d.get('topics') or {})))
    print('    top-level keys: %s' % sorted(d.keys()))
    firsts = collections.Counter(); top3 = collections.Counter()
    print('    %-30s %-22s %-22s %-22s %s' % ('TOPIC', 'seed#1', 'seed#2', 'seed#3', 'knee/knee_found'))
    for lab, t in (d.get('topics') or {}).items():
        path = t.get('path') or []
        seeds = [(s.get('seed'), s.get('type')) for s in path[1:4]]
        while len(seeds) < 3:
            seeds.append((None, None))
        if seeds[0][0]:
            firsts[seeds[0][0]] += 1
        for s, _ty in seeds:
            if s:
                top3[s] += 1
        print('    %-30s %-22s %-22s %-22s %s/%s' % (
            lab[:30],
            '%s[%s]' % (seeds[0][0], seeds[0][1]) if seeds[0][0] else '-',
            '%s[%s]' % (seeds[1][0], seeds[1][1]) if seeds[1][0] else '-',
            '%s[%s]' % (seeds[2][0], seeds[2][1]) if seeds[2][0] else '-',
            t.get('knee'), t.get('knee_found')))
    print('    FIRST-SEED frequency (of %d topics):' % len(d.get('topics') or {}))
    for m, c in firsts.most_common():
        print('        %-26s %d' % (m, c))
    print('    TOP-3-SEED frequency:')
    for m, c in top3.most_common(12):
        print('        %-26s %d' % (m, c))
    ks = sorted(set(k for t in (d.get('topics') or {}).values() for k in t.keys()))
    print('    per-topic keys: %s' % ks)
    dv = d.get('defend_overview')
    if dv:
        print('    defend_overview[0:3]: %s' % json.dumps(dv[:3]))

print()
print('=' * 78)
print('E4  ELECTORAL POOL INPUTS (topic-independence)')
print('=' * 78)
ep = R + r'\data\money\electoral_plays.json'
print('electoral_plays.json  mtime %s' % ts(ep))
if os.path.exists(ep):
    E = load(ep)
    plays = collections.Counter((v or {}).get('play') for v in E.values())
    print('   members=%d  play counts=%s' % (len(E), dict(plays)))
    print('   sample record keys: %s' % sorted(next(iter(E.values())).keys()))
    print('   any topic/category key present? %s' % any(
        k in ('topic', 'category', 'issue') for v in E.values() for k in v.keys()))
el = R + r'\data\money\electoral.json'
print('electoral.json        mtime %s' % ts(el))
if os.path.exists(el):
    L = load(el)
    levs = sorted(set(round((v or {}).get('leverage', 1.0), 6) for v in L.values()))
    print('   members=%d  distinct leverage values=%d' % (len(L), len(levs)))
    print('   leverage values (first 20): %s' % levs[:20])
    print('   sample record keys: %s' % sorted(next(iter(L.values())).keys()))
