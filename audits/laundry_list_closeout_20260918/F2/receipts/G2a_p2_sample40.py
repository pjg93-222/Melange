# -*- coding: utf-8 -*-
"""F2 G2: draw a simple random sample of 40 of the 249 P2-A detector-hit windows (seed 20260918)
and print, for each, everything needed to grade TRUE-BLEED / GENUINE / UNCLEAR by reading:
  source id, the DB-attributed speaker, the target, the row text with >=300 chars either side of
  the relevant turn-boundary marker (every marker in the slice annotated), and the artifact's tone
  for that window if it was scored.

The detector itself is NOT reimplemented here.  The prelude of lane B's 04b_p2_colonless.py
(everything above its `refs = [...]` line: nrm, the HON/TAIL/NOCOLON/COLON/ANGLE regexes, STOP,
allcaps_row, qualifies_colon, boundaries) is read as text and exec'd, so the marker geometry is
bit-identical to the detector that produced the 249 hits.  A per-row assertion confirms the
recomputed nearest-preceding-marker tag equals the tag lane B stored.

READ-ONLY: reads social_media.db via a read-only URI; writes only into F2/receipts."""
import collections, hashlib, io, json, os, random, re, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
LB = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F2\receipts')
SEED = 20260918
N = 40
PAD = 320                      # >= 300 chars either side of the marker, as required

# ---- exec lane B's detector prelude verbatim (no fec/ import; no execution of repo code) ----
src = io.open(os.path.join(LB, '04b_p2_colonless.py'), encoding='utf-8').read()
cut = src.index('\nrefs = [json.loads(l)')
prelude = src[:cut]
G = {'__name__': '_laneB_prelude'}
exec(compile(prelude, '04b_p2_colonless.py<prelude>', 'exec'), G)
boundaries = G['boundaries']
print('exec\'d lane B prelude: %d chars, %d lines; boundaries() ready' %
      (len(prelude), prelude.count('\n') + 1))

# ---- population: the 249 P2-A hits my G1a re-run regenerated ----
hits = json.load(io.open(os.path.join(PK, '04b_p2_union_examples.json'), encoding='utf-8'))
print('P2-A population: %d hit windows' % len(hits))
assert len(hits) == 249, len(hits)

# ---- tone cache, loaded exactly as 02c_rederive.py does (cache + baseline bindings) ----
cache = {}
for ln in io.open(LIVE + r'\data\members\member_reference_cache_fable.jsonl', encoding='utf-8'):
    try:
        d = json.loads(ln)
        if d['k'] not in cache:
            cache[d['k']] = d['out']
    except Exception:
        pass
baseline = json.load(io.open(LIVE + r'\data\members\member_reference_cache_baseline_v2.json', encoding='utf-8'))
assert baseline.get('schema') == 'reference-cache-baseline-v2'
for new, old in baseline['bindings'].items():
    if new not in cache and old in cache:
        cache[new] = cache[old]
print('tone cache keys after baseline binding: %d' % len(cache))

# ---- sample ----
rnd = random.Random(SEED)
samp = rnd.sample(hits, N)
print('sample: simple random, random.Random(%d).sample(population, %d)' % (SEED, N))

sids = sorted({h['_sid'] for h in samp})
con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=180)
con.execute('PRAGMA query_only=ON')
ROW = {}
for rid, mem, date, source, pkg, text in con.execute(
        'SELECT rowid, member, date, source, package, text FROM speeches WHERE rowid IN (%s)'
        % ','.join('?' * len(sids)), sids):
    ROW[rid] = dict(member=mem, date=date, source=source, pkg=pkg, text=text or '')
con.close()
print('row texts fetched: %d distinct source ids' % len(ROW))


def annotate(text, lo, hi, marks, ment):
    """slice text[lo:hi] with every boundary marker wrapped [[ ]] and the mention wrapped {{ }}"""
    ins = []
    for s, e, tg, kind in marks:
        if e <= lo or s >= hi:
            continue
        ins.append((s, '[[%s|' % kind)); ins.append((e, ']]'))
    ins.append((ment[0], '{{')); ins.append((ment[1], '}}'))
    out, pos = [], lo
    for at, tok in sorted(ins, key=lambda x: (x[0], x[1].startswith(']]') or x[1] == '}}')):
        at = min(max(at, lo), hi)
        out.append(text[pos:at]); out.append(tok); pos = at
    out.append(text[pos:hi])
    return re.sub(r'[ \t]+', ' ', ''.join(out).replace('\n', ' \u00b6 '))


rows, mismatch = [], 0
for i, h in enumerate(samp, 1):
    r = ROW[h['_sid']]
    text = r['text']
    marks = boundaries(text)
    pos = h['_pos'] - 1                      # detector convention: _pos is into ' '+lower+' '
    ll = len(h['_lit'])
    B0 = marks[0][0] if marks else -1
    prev = [x for x in marks if x[0] <= pos]
    ptag = prev[-1][2] if prev else ''
    pk = prev[-1][3] if prev else ''
    if ' '.join(ptag.split()) != ' '.join((h['_prev_tag'] or '').split()) or pk != h['_kind']:
        mismatch += 1
    mstart = prev[-1][0] if prev else B0
    mend = prev[-1][1] if prev else B0
    lo = max(0, min(mstart, pos) - PAD)
    hi = min(len(text), max(mend, pos + ll) + PAD)
    tone = cache.get(h['_k'])
    rows.append({
        'n': i, 'sid': h['_sid'], 'src': h['src'], 'pkg': r['pkg'], 'date': r['date'],
        'db_member': r['member'], 'speaker_a': h['a'], 'target_b': h['b'],
        'literal': h['_lit'], 'mention_off': pos, 'row_len': len(text),
        'first_marker_off': B0, 'marker_off': mstart, 'marker_kind': pk, 'marker_tag': ptag,
        'names_target': h['_names_target'], 'inside_tag': h['_inside_tag'],
        'n_markers_in_row': len(marks),
        'scored': h['_counted_scored'], 'cached': h['_cached'],
        'tone_cls': (tone or {}).get('cls', ''), 'tone_reason': (tone or {}).get('reason', ''),
        'slice_lo': lo, 'slice_hi': hi,
        'context': annotate(text, lo, hi, marks, (pos, pos + ll)),
        'grade': '', 'reason': ''})
print('nearest-marker tag/kind mismatches vs lane B stored values: %d of %d' % (mismatch, N))

with io.open(os.path.join(PK, 'G2a_p2_sample40_UNGRADED.json'), 'w', encoding='utf-8') as f:
    json.dump({'detector': 'P2-A speaker-tag bleed (D-P2 union D-P2\')', 'seed': SEED,
               'population': len(hits), 'n': N, 'pad': PAD, 'rows': rows}, f,
              ensure_ascii=False, indent=1)

print()
print('=' * 100)
print('P2-A RANDOM SAMPLE OF %d HIT WINDOWS (seed %d, population %d)' % (N, SEED, len(hits)))
print('   [[KIND|...]] = a turn-boundary marker the detector found;  {{...}} = the matched mention')
print('   GRADE: TRUE-BLEED (mention sits in another person\'s turn) / GENUINE / UNCLEAR')
print('=' * 100)
for r in rows:
    print()
    print('[%02d] sid=%-7s %s  pkg=%s  date=%s  rowlen=%d  markers_in_row=%d'
          % (r['n'], r['sid'], r['src'], (r['pkg'] or '')[:46], r['date'], r['row_len'], r['n_markers_in_row']))
    print('     attributed speaker (db.speeches.member) : %s' % r['db_member'])
    print('     target                                  : %s   literal=%r @off %d'
          % (r['target_b'], r['literal'], r['mention_off']))
    print('     nearest preceding marker                : off %d [%s] %r  names_target=%s inside_tag=%s'
          % (r['marker_off'], r['marker_kind'], ' '.join(r['marker_tag'].split())[:60],
             r['names_target'], r['inside_tag']))
    print('     first marker off=%d   scored=%s  tone=%s  %s'
          % (r['first_marker_off'], r['scored'], r['tone_cls'] or '-',
             ('| ' + r['tone_reason'][:80]) if r['tone_reason'] else ''))
    print('     CTX[%d:%d] %s' % (r['slice_lo'], r['slice_hi'], r['context']))
print()
print('wrote G2a_p2_sample40_UNGRADED.json')
print('DONE G2a')
