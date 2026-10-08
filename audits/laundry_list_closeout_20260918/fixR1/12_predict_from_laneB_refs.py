# -*- coding: utf-8 -*-
"""FIX R1: the same prediction as 10_predict_admission_filters.py, computed directly on lane B's
own re-derived mention list (SCRATCH/laneB/refs.jsonl, 53,011 rows, written 2026-09-18 23:40 by
laneB/receipts/02c_rederive.py, which reproduced the shipped artifact 8,017 of 8,017 edges).

This is the literal reading of "extend lane B's re-derivation": the extraction is lane B's, and
the only thing added is the three filters, imported from the shipped pure helper. The companion
script 10 re-derives the extraction from the databases again and must agree; this one exists
because the extraction pass is ~8 CPU-minutes and several other lanes were saturating the box.

READ-ONLY. Reads refs.jsonl, the label cache, the cache baseline and member_references.json;
writes only into this receipts directory. Nothing under fec/ is imported except the helper."""
import collections, hashlib, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
WORK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
        r'\unfinished-work-handoff-a3bbad')
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
OUT = os.path.join(WORK, 'audits', 'laundry_list_closeout_20260918', 'fixR1')
sys.path.insert(0, os.path.join(WORK, 'fec'))
from members import reference_filters as RF

DYAD_CAP = 4
CACHE = LIVE + r'\data\members\member_reference_cache_fable.jsonl'
BASELINE = LIVE + r'\data\members\member_reference_cache_baseline_v2.json'

C = [m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json', encoding='utf-8'))]
SUR = RF.roster_surnames(C)
print('roster %d members | %d distinct surnames' % (len(C), len(SUR)))

REFS = []
for line in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8'):
    r = json.loads(line)
    if r['src'] == 'PRESS': r['url'] = r.get('_url') or ''   # the producer now carries this itself
    REFS.append(r)
print('lane B mentions: %d   by source %s' % (len(REFS), dict(collections.Counter(r['src'] for r in REFS))))


def ckey(row):
    return 'v2:' + hashlib.sha256(json.dumps(['reference-window-v2', row['a'], row['b'], row['w'][:400]],
                                             ensure_ascii=False).encode('utf-8')).hexdigest()


bad_k = sum(1 for r in REFS if r.get('_k') and r['_k'] != ckey(r))
print('stored cache keys recomputed identically: %s (%d mismatches)' % (bad_k == 0, bad_k))
for r in REFS: r['_k'] = ckey(r)

CACHE_MAP = {}
for ln in io.open(CACHE, encoding='utf-8'):
    try:
        d = json.loads(ln)
        if d['k'] not in CACHE_MAP: CACHE_MAP[d['k']] = d['out']
    except Exception: pass
baseline = json.load(io.open(BASELINE, encoding='utf-8'))
assert baseline.get('schema') == 'reference-cache-baseline-v2'
bound = 0
for new, old in baseline['bindings'].items():
    if new not in CACHE_MAP and old in CACHE_MAP:
        CACHE_MAP[new] = CACHE_MAP[old]; bound += 1
print('cache keys %d (baseline bindings applied %d)' % (len(CACHE_MAP), bound))

ART = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in ART['edges']}
print('shipped artifact edges %d | already has admission_filters: %s'
      % (len(AE), 'admission_filters' in ART))


def run(press_own_domain, roster_filter, identical_once):
    refs, excl = RF.apply_admission_filters(REFS, SUR, press_own_domain=press_own_domain,
                                            roster_filter=roster_filter)
    bykey = collections.defaultdict(list)
    for r in refs: bykey[(r['a'], r['b'], r['src'])].append(r)
    target_all = []
    for k, v in bykey.items():
        v.sort(key=lambda r: r['date'], reverse=True)
        target_all.extend(v[:DYAD_CAP])
    unc_pre = sum(1 for r in target_all if r['_k'] not in CACHE_MAP)
    target_all, dup_target = RF.collapse_identical(target_all, identical_once)
    unc_post = sum(1 for r in target_all if r['_k'] not in CACHE_MAP)
    todo_all = [r for g in bykey.values() for r in [x for x in g if x['_k'] in CACHE_MAP][:DYAD_CAP]]
    todo_all, dup_scored = RF.collapse_identical(todo_all, identical_once)
    edges = collections.defaultdict(lambda: {'n_raw': 0, 'n_scored': 0, 'pos': 0, 'neg': 0, 'neu': 0,
                                             'form': 0, 'sources': collections.Counter()})
    for r in refs:
        e = edges[(r['a'], r['b'])]; e['n_raw'] += 1; e['sources'][r['src']] += 1
    for r in todo_all:
        o = CACHE_MAP.get(r['_k'])
        if not o: continue
        e = edges[(r['a'], r['b'])]; e['n_scored'] += 1
        c = o['cls']
        if c == 'positive': e['pos'] += 1
        elif c == 'negative': e['neg'] += 1
        elif c == 'neutral-substantive': e['neu'] += 1
        else: e['form'] += 1
    out = {}
    for ab, e in edges.items():
        sub = e['pos'] + e['neg'] + e['neu']
        if sub == 0: continue
        out[ab] = {'n_raw': e['n_raw'], 'n_scored': e['n_scored'], 'pos': e['pos'], 'neg': e['neg'],
                   'neu': e['neu'], 'form': e['form'], 'sources': dict(e['sources']),
                   'net': round((e['pos'] - e['neg']) / max(1, sub), 3)}
    return {'edges': out, 'excluded': dict(excl), 'dup_target': dup_target, 'dup_scored': dup_scored,
            'mentions': len(refs), 'target': len(target_all),
            'paid_uncached_before': unc_pre, 'paid_uncached_after': unc_post}


def drawn(res): return sum(1 for e in res['edges'].values() if e['n_scored'] >= 2)
def signed(res): return sum(1 for e in res['edges'].values() if e['pos'] + e['neg'] > 0)
def scored(res): return sum(e['n_scored'] for e in res['edges'].values())

print()
print('=' * 92)
print('STEP 0  PARITY: all three dials at 0 must reproduce the shipped artifact exactly')
print('=' * 92)
OFF = run(False, False, False)
print('edges mine %d vs shipped %d | mine-not-shipped %d | shipped-not-mine %d'
      % (len(OFF['edges']), len(AE), len(set(OFF['edges']) - set(AE)), len(set(AE) - set(OFF['edges']))))
for field in ('n_raw', 'n_scored', 'pos', 'neg', 'neu', 'net'):
    okc = sum(1 for ab in AE if ab in OFF['edges'] and OFF['edges'][ab][field] == AE[ab][field])
    print('  %-8s EXACT MATCH %d / %d = %.3f%%' % (field, okc, len(AE), 100.0 * okc / len(AE)))
oks = sum(1 for ab in AE if ab in OFF['edges'] and OFF['edges'][ab]['sources'] == (AE[ab].get('sources') or {}))
print('  %-8s EXACT MATCH %d / %d = %.3f%%' % ('sources', oks, len(AE), 100.0 * oks / len(AE)))
print('  formality_dropped EXACT MATCH %d / %d'
      % (sum(1 for ab in AE if ab in OFF['edges'] and OFF['edges'][ab]['form'] == AE[ab].get('formality_dropped', 0)), len(AE)))
print('sum n_raw mine %d vs shipped %d | sum n_scored mine %d vs shipped %d'
      % (sum(e['n_raw'] for e in OFF['edges'].values()), sum(e['n_raw'] for e in ART['edges']),
         scored(OFF), sum(e['n_scored'] for e in ART['edges'])))
print('all dials 0 excluded nothing: %s %s' % (not OFF['excluded'], OFF['excluded']))
print('drawn (n_scored>=2) %d | signed %d' % (drawn(OFF), signed(OFF)))

print()
print('=' * 92)
print('STEP 1  ALL THREE FILTERS ON (the shipped default)')
print('=' * 92)
ON = run(True, True, True)
print('per-filter exclusions:')
print('   press_third_party_domain  %6d   (mentions, dropped before n_raw and the queue)' % ON['excluded'].get('press_third_party_domain', 0))
print('   roster_list_window        %6d   (mentions, dropped before n_raw and the queue)' % ON['excluded'].get('roster_list_window', 0))
print('   identical_window_repeat   %6d   (scored-queue windows collapsed; n_raw keeps them)' % ON['dup_scored'])
print('   ...paid target contexts collapsed %d | uncached contexts --score would pay: %d -> %d (%+d)'
      % (ON['dup_target'], ON['paid_uncached_before'], ON['paid_uncached_after'],
         ON['paid_uncached_after'] - ON['paid_uncached_before']))
print()
print('mentions       %6d -> %6d  (%+d)' % (OFF['mentions'], ON['mentions'], ON['mentions'] - OFF['mentions']))
print('sum n_scored   %6d -> %6d  (%+d)' % (scored(OFF), scored(ON), scored(ON) - scored(OFF)))
print('EDGES          %6d -> %6d  (%+d)' % (len(OFF['edges']), len(ON['edges']), len(ON['edges']) - len(OFF['edges'])))
print('DRAWN  n_sc>=2 %6d -> %6d  (%+d)' % (drawn(OFF), drawn(ON), drawn(ON) - drawn(OFF)))
print('SIGNED         %6d -> %6d  (%+d)' % (signed(OFF), signed(ON), signed(ON) - signed(OFF)))

gone = sorted(set(OFF['edges']) - set(ON['edges']))
new = sorted(set(ON['edges']) - set(OFF['edges']))
fell = sorted(ab for ab in set(OFF['edges']) & set(ON['edges'])
              if OFF['edges'][ab]['n_scored'] >= 2 > ON['edges'][ab]['n_scored'])
rose = sorted(ab for ab in set(OFF['edges']) & set(ON['edges'])
              if ON['edges'][ab]['n_scored'] >= 2 > OFF['edges'][ab]['n_scored'])
print()
print('edges REMOVED ENTIRELY: %d' % len(gone))
for ab in gone[:25]:
    e = OFF['edges'][ab]
    print('   %-27s -> %-27s n_raw=%-3d n_scored=%-2d net=%+0.2f drawn=%s sources=%s'
          % (ab[0][:27], ab[1][:27], e['n_raw'], e['n_scored'], e['net'], e['n_scored'] >= 2, e['sources']))
if len(gone) > 25: print('   ... and %d more' % (len(gone) - 25))
print('edges that APPEAR (a cap slot freed by a filtered window promoted a cached window): %d' % len(new))
for ab in new[:25]:
    e = ON['edges'][ab]
    print('   %-27s -> %-27s n_raw=%-3d n_scored=%-2d net=%+0.2f sources=%s'
          % (ab[0][:27], ab[1][:27], e['n_raw'], e['n_scored'], e['net'], e['sources']))
print()
print('edges DROPPING BELOW the consumers\' n_scored>=2 floor: %d' % len(fell))
for ab in fell[:25]:
    a, b = OFF['edges'][ab], ON['edges'][ab]
    print('   %-25s -> %-25s n_scored %d -> %d | net %+0.2f -> %+0.2f | signed=%s | %s'
          % (ab[0][:25], ab[1][:25], a['n_scored'], b['n_scored'], a['net'], b['net'],
             b['pos'] + b['neg'] > 0, b['sources']))
if len(fell) > 25: print('   ... and %d more' % (len(fell) - 25))
print('edges RISING to the floor: %d  %s' % (len(rose), [('%s->%s' % ab) for ab in rose[:6]]))
print()
print('edges whose net moves: %d | edges whose n_scored moves: %d'
      % (sum(1 for ab in set(OFF['edges']) & set(ON['edges']) if OFF['edges'][ab]['net'] != ON['edges'][ab]['net']),
         sum(1 for ab in set(OFF['edges']) & set(ON['edges']) if OFF['edges'][ab]['n_scored'] != ON['edges'][ab]['n_scored'])))
print('SIGNED edges that lose ALL scored support: %d'
      % sum(1 for ab in gone if OFF['edges'][ab]['pos'] + OFF['edges'][ab]['neg'] > 0))
print('audit_full floors still hold: >=1000 edges %s | every edge n_scored>=pos+neg %s'
      % (len(ON['edges']) >= 1000, all(e['n_scored'] >= e['pos'] + e['neg'] for e in ON['edges'].values())))

print()
print('=' * 92)
print('STEP 2  EACH DIAL OFF ON ITS OWN')
print('=' * 92)
CONFIGS = [('all three ON (shipped default)', True, True, True),
           ('REF_PRESS_OWN_DOMAIN=0', False, True, True),
           ('REF_ROSTER_FILTER=0', True, False, True),
           ('REF_IDENTICAL_ONCE=0', True, True, False),
           ('all three OFF (= shipped artifact)', False, False, False)]
print('%-36s %9s %7s %7s %7s %9s %9s %9s' % ('config', 'mentions', 'edges', 'drawn', 'signed',
                                             'n_scored', 'excl_prs', 'excl_ros'))
RES = {}
for label, p, r_, i in CONFIGS:
    res = run(p, r_, i); RES[label] = res
    print('%-36s %9d %7d %7d %7d %9d %9d %9d'
          % (label, res['mentions'], len(res['edges']), drawn(res), signed(res), scored(res),
             res['excluded'].get('press_third_party_domain', 0), res['excluded'].get('roster_list_window', 0)))
print()
print('marginal effect of each filter (default vs that filter switched off):')
base = RES['all three ON (shipped default)']
for label in ('REF_PRESS_OWN_DOMAIN=0', 'REF_ROSTER_FILTER=0', 'REF_IDENTICAL_ONCE=0'):
    a = RES[label]
    print('   %-22s edges %+d | drawn %+d | signed %+d | n_scored %+d | mentions %+d'
          % (label.split('=')[0], len(base['edges']) - len(a['edges']), drawn(base) - drawn(a),
             signed(base) - signed(a), scored(base) - scored(a), base['mentions'] - a['mentions']))

print()
print('=' * 92)
print('STEP 3  CROSS-CHECKS')
print('=' * 92)
bad = sum(1 for r in REFS if RF.is_roster_list(r.get('_raw_w') or r['w'], SUR) != RF.is_roster_list(r['w'], SUR))
print('roster detector: lane B\'s raw slice vs the producer\'s collapsed window -- %d of %d disagree'
      % (bad, len(REFS)))
hits = [r for r in REFS if RF.is_roster_list(r['w'], SUR)]
print('roster-list mentions repo-wide %d (lane B measured 749) | by source %s'
      % (len(hits), dict(collections.Counter(r['src'] for r in hits))))
print('  of those counted into n_scored by the shipped artifact: %d (lane B measured 502)'
      % sum(1 for r in hits if r.get('_counted_scored')))
press = [r for r in REFS if r['src'] == 'PRESS']
third = [r for r in press if not RF.own_official_domain(r.get('url'))]
print('PRESS mentions %d | third-party %d (lane B measured 8) | hosts %s'
      % (len(press), len(third), dict(collections.Counter((r.get('url') or '').split('/')[2] for r in third))))
print('PRESS rows with no url at all (would be excluded as third-party): %d'
      % sum(1 for r in press if not (r.get('url') or '').strip()))
pom = [r for r in REFS if r['src'] == 'PRESS_OFFICIAL_MENTION']
print('PRESS_OFFICIAL_MENTION mentions %d -- out of scope, and the gate touched none of them: %s'
      % (len(pom), base['excluded'].get('press_third_party_domain', 0) == len(third)))
grp = collections.defaultdict(list)
for r in REFS: grp[(r['a'], r['b'], RF.normalized_window(r['w']))].append(r)
split = [k for k, v in grp.items() if len({x['_k'] for x in v}) > 1]
print('normalised-identical windows on one edge that hash to DIFFERENT cache keys: %d groups' % len(split))
print('  (0 => collapsing the paid target set cannot change which window gets classified)')
mag = sorted(ab for ab in OFF['edges'] if 'Magaziner' in ab[0] + ab[1])
print('Magaziner edges: %d shipped -> %d kept' % (len(mag), sum(1 for ab in mag if ab in ON['edges'])))
for ab in mag:
    e = OFF['edges'][ab]
    print('   %-25s -> %-25s n_raw=%-2d n_scored=%-2d net=%+0.2f %s  kept=%s'
          % (ab[0][:25], ab[1][:25], e['n_raw'], e['n_scored'], e['net'], e['sources'], ab in ON['edges']))
print()
print('the block the producer writes at the default:')
print(json.dumps(RF.admission_filters_block(
    {'REF_PRESS_OWN_DOMAIN': True, 'REF_ROSTER_FILTER': True, 'REF_IDENTICAL_ONCE': True},
    dict(base['excluded'], identical_window_repeat=base['dup_scored'])), indent=1, sort_keys=True))

with io.open(os.path.join(OUT, '12_predict_from_laneB_refs.json'), 'w', encoding='utf-8') as f:
    json.dump({'source': 'laneB/refs.jsonl (53,011 mentions, 2026-09-18 23:40)',
               'shipped_edges': len(AE),
               'configs': {k: {'mentions': v['mentions'], 'edges': len(v['edges']), 'drawn': drawn(v),
                               'signed': signed(v), 'sum_n_scored': scored(v),
                               'excluded': v['excluded'], 'identical_window_repeat': v['dup_scored']}
                           for k, v in RES.items()},
               'edges_removed': [list(ab) for ab in gone],
               'edges_added': [list(ab) for ab in new],
               'edges_below_floor': [list(ab) for ab in fell],
               'edges_above_floor': [list(ab) for ab in rose]}, f, ensure_ascii=False, indent=1)
print()
print('wrote 12_predict_from_laneB_refs.json')
print('DONE 12')
