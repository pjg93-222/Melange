# -*- coding: utf-8 -*-
"""LANE B P4: byte-identical windows counted more than once.

member_reference_layer.py:322-330 increments n_scored (and pos/neg/neu/form) once per CONTRIBUTING
window.  Contributing windows are todo_all = the newest DYAD_CAP *cached* windows per (a,b,source)
(line 318).  Two identical windows produce the SAME cache key -- reference_cache.key() hashes
['reference-window-v2', a, b, w[:400]] -- so they always carry the SAME label and add no
information, yet each one increments n_scored.  n_scored is the consumers' drawing floor
(build_dashboard_bundle.py:238, n_scored>=2) and the desk's sort key (make_member_desk.py:677).

DETECTOR D-P4
  Normalise each contributing window with re.sub(r'\\s+',' ',w).strip() (speeches windows are
  already whitespace-collapsed at line 132; X/PRESS/POM windows are not).  For each shipped edge:
     windows            = len(contributing)
     distinct           = len(set(normalised))
     surplus            = windows - distinct
  Reported: edges with >=2 contributing windows identical after normalisation (surplus>0), the
  total surplus window count, and edges that would drop below n_scored>=2 if identical windows
  counted once.  Also reported on w[:400] (the exact cache-key slice) as a cross-check.
READ-ONLY. Consumes SCRATCH/refs.jsonl."""
import collections, hashlib, io, json, os, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')

refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}


def nz(w): return re.sub(r'\s+', ' ', w or '').strip()


contrib = collections.defaultdict(list)
for r in refs:
    if r['_counted_scored']: contrib[(r['a'], r['b'])].append(r)
print('edges with >=1 contributing window : %d   (shipped edges %d)' % (len(contrib), len(AE)))
tot_ctb = sum(len(v) for v in contrib.values())
print('total contributing windows         : %d' % tot_ctb)
print('sum artifact n_scored              : %d' % sum(e['n_scored'] for e in art['edges']))

rows = []
for k, v in contrib.items():
    if k not in AE: continue
    e = AE[k]
    norm = [nz(x['w']) for x in v]
    k400 = [nz(x['w'])[:400] for x in v]
    d = len(set(norm))
    rows.append({'a': k[0], 'b': k[1], 'windows': len(v), 'distinct': d, 'surplus': len(v) - d,
                 'distinct400': len(set(k400)), 'n_scored': e['n_scored'], 'pos': e['pos'],
                 'neg': e['neg'], 'neu': e['neu'], 'form': e.get('formality_dropped', 0),
                 'net': e['net'], 'sources': e.get('sources'),
                 'srcs_of_dupes': sorted({x['src'] for x in v}),
                 'dupe_groups': [{'n': c, 'src': [x['src'] for x in v if nz(x['w']) == w][0],
                                  'w': w[:180]}
                                 for w, c in collections.Counter(norm).items() if c >= 2]})
dup = [r for r in rows if r['surplus'] > 0]
print()
print('=' * 78)
print('P4 RESULTS  (shipped edges only)')
print('=' * 78)
print('shipped edges with >=2 contributing windows identical after whitespace normalisation : %d' % len(dup))
print('  = %.2f%% of shipped edges' % (100.0 * len(dup) / len(AE)))
print('SURPLUS window count (double/triple/... counted)                                    : %d' % sum(r['surplus'] for r in dup))
print('  = %.2f%% of the artifact\'s %d scored windows' % (100.0 * sum(r['surplus'] for r in dup) / sum(e['n_scored'] for e in art['edges']), sum(e['n_scored'] for e in art['edges'])))
print('multiplicity histogram (max identical-group size per edge): %s' %
      dict(sorted(collections.Counter(max(g['n'] for g in r['dupe_groups']) for r in dup).items())))
print()
below = [r for r in dup if r['n_scored'] >= 2 and r['distinct'] < 2]
print('edges that would FALL BELOW the consumers\' n_scored>=2 floor if identical windows counted once : %d' % len(below))
print('  (currently drawn by build_dashboard_bundle.py:238, would stop being drawn)')
print('edges currently drawn (n_scored>=2) with ANY surplus : %d' % sum(1 for r in dup if r['n_scored'] >= 2))
print('edges whose n_scored is ENTIRELY duplicate-inflated (distinct==1, n_scored>=2): %d' % len(below))
print()
print('by source mix of duplicate-bearing edges:')
for s, n in collections.Counter(tuple(r['srcs_of_dupes']) for r in dup).most_common(12):
    print('   %-46s %5d' % (str(s)[:46], n))
print()
print('surplus windows by source (source of the duplicated window):')
sd = collections.Counter()
for r in dup:
    for g in r['dupe_groups']: sd[g['src']] += g['n'] - 1
print('   %s' % dict(sd.most_common()))
print()
print('signed impact:')
print('   duplicate-bearing edges that are SIGNED (pos+neg>0) : %d' % sum(1 for r in dup if r['pos'] + r['neg'] > 0))
print('   ...and drawn (n_scored>=2)                          : %d' % sum(1 for r in dup if r['pos'] + r['neg'] > 0 and r['n_scored'] >= 2))
print('   NOTE: net = (pos-neg)/(pos+neg+neu) is a RATIO, so identical windows (identical cache')
print('         key -> identical label) leave net unchanged; they inflate n_scored only.')
print()
print('=== 25 worst duplicate-bearing edges ===')
for r in sorted(dup, key=lambda x: (-x['surplus'], -x['windows']))[:25]:
    print('%-26s -> %-26s win=%d distinct=%d surplus=%d n_scored=%d net=%+0.2f src=%s' %
          (r['a'][:26], r['b'][:26], r['windows'], r['distinct'], r['surplus'], r['n_scored'], r['net'], r['sources']))
    for g in r['dupe_groups'][:2]:
        print('      x%d [%s] %s' % (g['n'], g['src'], g['w'][:120]))
print()
print('=== cross-check on the exact cache-key slice w[:400] ===')
dup400 = [r for r in rows if r['windows'] - r['distinct400'] > 0]
print('edges with duplicate w[:400] : %d | surplus %d' % (len(dup400), sum(r['windows'] - r['distinct400'] for r in dup400)))
print()
print('=== X-source duplicate tweets (July: duplicate tweets counted 2-4x) ===')
xd = [r for r in dup if 'X' in r['srcs_of_dupes']]
print('duplicate-bearing edges touching X : %d' % len(xd))
xg = collections.Counter()
for r in xd:
    for g in r['dupe_groups']:
        if g['src'] == 'X': xg[g['n']] += 1
print('X identical-group sizes: %s' % dict(sorted(xg.items())))
for r in sorted(xd, key=lambda x: -x['surplus'])[:8]:
    print('   %-24s -> %-24s win=%d distinct=%d n_scored=%d' % (r['a'][:24], r['b'][:24], r['windows'], r['distinct'], r['n_scored']))
    for g in r['dupe_groups'][:1]:
        print('        x%d [%s] %s' % (g['n'], g['src'], g['w'][:130]))
with io.open(os.path.join(PK, '06_p4_duplicate_edges.json'), 'w', encoding='utf-8') as f:
    json.dump({'edges_with_surplus': sorted(dup, key=lambda x: -x['surplus'])}, f, ensure_ascii=False, indent=1)
print()
print('wrote receipts/06_p4_duplicate_edges.json (%d edges)' % len(dup))
print('DONE 06')
