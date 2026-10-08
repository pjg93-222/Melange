# -*- coding: utf-8 -*-
"""FIX R1: why the shipped filter collapses 192 windows where lane B measured 170.

Lane B's P4 detector (laneB/receipts/06_p4_duplicate_windows.py:48-49) counts surplus windows
on SHIPPED EDGES ONLY -- it skips every dyad that is not in member_references.json. The shipped
filter has no such restriction: a dyad whose every classified window is FORMALITY never becomes
an edge (member_reference_layer.py:342, `if sub == 0: continue`) but its duplicate windows are
still collapsed on the way there. This script splits the 192 on that line, and confirms the
consumer-visible number -- 53 drawn edges that fall below n_scored>=2 -- is lane B's exactly.

READ-ONLY, consumes lane B's refs.jsonl and the live cache/artifact."""
import collections, hashlib, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WORK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
        r'\unfinished-work-handoff-a3bbad')
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
sys.path.insert(0, os.path.join(WORK, 'fec'))
from members import reference_filters as RF

DYAD_CAP = 4
C = [m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))]
SUR = RF.roster_surnames(C)
REFS = []
for line in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    if r['src'] == 'PRESS': r['url'] = r.get('_url') or ''
    REFS.append(r)
CACHE_MAP = {}
for ln in io.open(LIVE + r'\data\members\member_reference_cache_fable.jsonl', encoding='utf-8'):
    try:
        d = json.loads(ln)
        if d['k'] not in CACHE_MAP: CACHE_MAP[d['k']] = d['out']
    except Exception: pass
baseline = json.load(io.open(LIVE + r'\data\members\member_reference_cache_baseline_v2.json', encoding='utf-8'))
for new, old in baseline['bindings'].items():
    if new not in CACHE_MAP and old in CACHE_MAP: CACHE_MAP[new] = CACHE_MAP[old]
AE = {(e['a'], e['b']) for e in json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))['edges']}


def ckey(row):
    return 'v2:' + hashlib.sha256(json.dumps(['reference-window-v2', row['a'], row['b'], row['w'][:400]],
                                             ensure_ascii=False).encode('utf-8')).hexdigest()
for r in REFS: r['_k'] = ckey(r)


def scored_queue(refs):
    bykey = collections.defaultdict(list)
    for r in refs: bykey[(r['a'], r['b'], r['src'])].append(r)
    for v in bykey.values(): v.sort(key=lambda r: r['date'], reverse=True)
    return [r for g in bykey.values() for r in [x for x in g if x['_k'] in CACHE_MAP][:DYAD_CAP]]


def census(label, refs):
    q = scored_queue(refs)
    by_edge = collections.defaultdict(list)
    for r in q: by_edge[(r['a'], r['b'])].append(r)
    surplus_all = surplus_shipped = 0
    ed_all = ed_shipped = 0
    for ab, rows in by_edge.items():
        d = len({RF.normalized_window(r['w']) for r in rows})
        s = len(rows) - d
        if s:
            surplus_all += s; ed_all += 1
            if ab in AE: surplus_shipped += s; ed_shipped += 1
    kept, dropped = RF.collapse_identical(q)
    print('%-42s queue %6d | collapse drops %4d | surplus(all dyads) %4d over %4d dyads | '
          'surplus(shipped edges only) %4d over %4d edges'
          % (label, len(q), dropped, surplus_all, ed_all, surplus_shipped, ed_shipped))
    return surplus_all, surplus_shipped


print('lane B receipt 06 measured: 157 shipped edges, 170 surplus windows, 53 drawn edges below the floor')
print()
a_all, a_ship = census('no other filter (lane B\'s own population)', REFS)
b_refs, _ = RF.apply_admission_filters(REFS, SUR)
b_all, b_ship = census('behind the press + roster filters (shipped)', b_refs)
print()
print('reconciliation of the count the artifact reports:')
print('  lane B counted surplus on SHIPPED EDGES only (06_p4:48 `if k not in AE: continue`) : %d' % a_ship)
print('  the shipped filter also collapses dyads that never become edges (formality-only)   : %d'
      % (a_all - a_ship))
print('  ->  total windows the filter removes from the scored queue, its own population      : %d' % a_all)
print('  with the press + roster filters in front of it the population changes slightly      : %d' % b_all)
print()
# formality-only proof: which dyads carry surplus but no edge
q = scored_queue(REFS)
by_edge = collections.defaultdict(list)
for r in q: by_edge[(r['a'], r['b'])].append(r)
off_edge = [(ab, rows) for ab, rows in by_edge.items()
            if ab not in AE and len(rows) - len({RF.normalized_window(r['w']) for r in rows})]
print('dyads with duplicate windows that are NOT shipped edges: %d' % len(off_edge))
cls = collections.Counter()
for ab, rows in off_edge:
    for r in rows:
        o = CACHE_MAP.get(r['_k'])
        if o: cls[o['cls']] += 1
print('  their windows classify as: %s' % dict(cls))
print('  (all formality => the dyad is dropped at member_reference_layer.py:342 and no consumer ever saw it)')
print('DONE 13')
