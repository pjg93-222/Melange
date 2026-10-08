# -*- coding: utf-8 -*-
"""F2 G3 + G5: three more random samples (seed 20260918), all drawn from lane B's own detector code.

  G3  : 40 of the 749 P3b roster/signature-list HITS            -> ARTEFACT / GENUINE / UNCLEAR
  G5a : 40 INTERVIEW mentions the P2-A detector did NOT flag    -> TRUE-BLEED / GENUINE / UNCLEAR
  G5b : 40 CREC mentions the P3b detector did NOT flag          -> ARTEFACT / GENUINE / UNCLEAR

Lane B's code is re-used by exec'ing slices of its saved scripts, never by reimplementation:
  05b_p3_graded.py  header slice        -> imports + LIVE/SCRATCH constants
                    clopper_pearson     -> exact binomial interval
                    C/nrm/SUR/refs/art/AE/is_list slice  -> the P3b detector verbatim
  04b_p2_colonless.py prelude           -> boundaries(), the P2-A marker geometry verbatim
Contexts are hard-capped so a 100k-char CREC row cannot flood the receipt.
READ-ONLY: social_media.db opened with a read-only URI; writes only into F2/receipts."""
import io, json, os, random, re, sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

LB = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F2\receipts')
SEED = 20260918
N = 40

s5 = io.open(os.path.join(LB, '05b_p3_graded.py'), encoding='utf-8').read()
s4 = io.open(os.path.join(LB, '04b_p2_colonless.py'), encoding='utf-8').read()
G = {'__name__': '_laneB'}
exec(compile(s5[:s5.index('# --- my grades')], '05b<header>', 'exec'), G)
cp_a = s5.index('def clopper_pearson(')
cp_b = s5.index("samp = json.load(")
exec(compile(s5[cp_a:cp_b], '05b<clopper_pearson>', 'exec'), G)
d3_a = s5.index("C = {m['member']: m for m in json.load")
d3_b = s5.index("\nfor r in refs:\n    r['_list'] = is_list(")
exec(compile(s5[d3_a:d3_b], '05b<D-P3b>', 'exec'), G)
refs, AE, is_list = G['refs'], G['AE'], G['is_list']
LIVE = G['LIVE']
H = {'__name__': '_laneB2'}
exec(compile(s4[:s4.index('\nrefs = [json.loads(l)')], '04b<prelude>', 'exec'), H)
boundaries = H['boundaries']
print('re-used lane B code: is_list() from 05b, boundaries() from 04b, clopper_pearson() from 05b')
print('refs loaded: %d   artifact edges: %d' % (len(refs), len(AE)))

for r in refs:
    r['_list'] = is_list(r.get('_raw_w') or r['w'])
LHITS = [r for r in refs if r['_list']]
print('P3b hits: %d (expect 749)' % len(LHITS))
assert len(LHITS) == 749, len(LHITS)

p2 = json.load(io.open(os.path.join(PK, '04b_p2_union_examples.json'), encoding='utf-8'))
assert len(p2) == 249, len(p2)
FLAG = {(h['a'], h['b'], h['src'], h['_sid'], h['_pos'], h['_lit']) for h in p2}
P2_UNFLAGGED_INT = [r for r in refs if r['src'] == 'INTERVIEW'
                    and (r['a'], r['b'], r['src'], r['_sid'], r['_pos'], r['_lit']) not in FLAG]
P3B_UNFLAGGED_CREC = [r for r in refs if r['src'] == 'CREC' and not r['_list']]
print('P2-A unflagged INTERVIEW population : %d' % len(P2_UNFLAGGED_INT))
print('P3b unflagged CREC population       : %d' % len(P3B_UNFLAGGED_CREC))

cache = {}
for ln in io.open(LIVE + r'\data\members\member_reference_cache_fable.jsonl', encoding='utf-8'):
    try:
        d = json.loads(ln)
        cache.setdefault(d['k'], d['out'])
    except Exception:
        pass
bl = json.load(io.open(LIVE + r'\data\members\member_reference_cache_baseline_v2.json', encoding='utf-8'))
for new, old in bl['bindings'].items():
    if new not in cache and old in cache:
        cache[new] = cache[old]

s3 = random.Random(SEED).sample(LHITS, N)
s5a = random.Random(SEED).sample(P2_UNFLAGGED_INT, N)
s5b = random.Random(SEED).sample(P3B_UNFLAGGED_CREC, N)

# row texts needed for the G5a bleed judgement
need = sorted({r['_sid'] for r in s5a if r['_sid'] != ''})
con = sqlite3.connect('file:%s?mode=ro' % (LIVE + r'\social_media.db').replace('\\', '/'), uri=True, timeout=180)
con.execute('PRAGMA query_only=ON')
TXT = {}
for rid, mem, pkg, text in con.execute(
        'SELECT rowid, member, package, text FROM speeches WHERE rowid IN (%s)' % ','.join('?' * len(need)), need):
    TXT[rid] = (mem, pkg or '', text or '')
con.close()
print('row texts fetched for G5a: %d' % len(TXT))


def sq(s, n):
    return re.sub(r'\s+', ' ', s or '')[:n]


def dump(tag, rows, fn, header, render):
    out = [{'n': i, 'a': r['a'], 'b': r['b'], 'src': r['src'], 'sid': r['_sid'], 'pkg': r['_pkg'],
            'date': r['date'], 'literal': r['_lit'], 'form': r.get('_form'), 'pos': r['_pos'],
            'scored': r['_counted_scored'], 'cached': r['_cached'],
            'tone_cls': (cache.get(r['_k']) or {}).get('cls', ''),
            'tone_reason': (cache.get(r['_k']) or {}).get('reason', ''),
            'edge_shipped': (r['a'], r['b']) in AE, 'grade': '', 'reason': ''}
           for i, r in enumerate(rows, 1)]
    with io.open(os.path.join(PK, fn), 'w', encoding='utf-8') as f:
        json.dump({'seed': SEED, 'n': N, 'rows': out}, f, ensure_ascii=False, indent=1)
    print()
    print('=' * 100)
    print(header)
    print('=' * 100)
    for i, r in enumerate(rows, 1):
        render(i, r, out[i - 1])
    print()
    print('wrote %s' % fn)


def render3(i, r, o):
    print()
    print('[%02d] %-22s -> %-22s [%s] sid=%s pkg=%s date=%s form=%s lit=%r'
          % (i, r['a'][:22], r['b'][:22], r['src'][:4], r['_sid'], sq(r['_pkg'], 24), r['date'],
             r.get('_form'), r['_lit']))
    print('     scored=%s shipped=%s tone=%s %s'
          % (o['scored'], o['edge_shipped'], o['tone_cls'] or '-',
             ('| ' + sq(o['tone_reason'], 70)) if o['tone_reason'] else ''))
    print('     WINDOW: %s' % sq(r.get('_raw_w') or r['w'], 900))


def render5a(i, r, o):
    mem, pkg, text = TXT.get(r['_sid'], ('?', '', ''))
    marks = boundaries(text)
    pos = r['_pos'] - 1
    lo, hi = max(0, pos - 500), min(len(text), pos + len(r['_lit']) + 220)
    seg = text[lo:hi]
    ml = pos - lo
    seg = seg[:ml] + '{{' + seg[ml:ml + len(r['_lit'])] + '}}' + seg[ml + len(r['_lit']):]
    print()
    print('[%02d] %-22s -> %-22s sid=%s pkg=%s date=%s rowlen=%d lit=%r @off %d'
          % (i, r['a'][:22], r['b'][:22], r['_sid'], sq(pkg, 30), r['date'], len(text), r['_lit'], pos))
    print('     scored=%s shipped=%s tone=%s %s'
          % (o['scored'], o['edge_shipped'], o['tone_cls'] or '-',
             ('| ' + sq(o['tone_reason'], 70)) if o['tone_reason'] else ''))
    print('     detector markers in row: %s'
          % ('NONE' if not marks else
             '; '.join('%d[%s]%r' % (s, k, sq(t, 26)) for s, e, t, k in marks[:4])))
    print('     ROW[%d:%d]: %s' % (lo, hi, sq(seg, 780)))


def render5b(i, r, o):
    w = r.get('_raw_w') or r['w']
    toks = [t for t in re.split(r"[^A-Za-z'\-]+", w) if len(t) > 1]
    hit = [t for t in toks if G['nrm'](t) in G['SUR']]
    print()
    print('[%02d] %-22s -> %-22s sid=%s pkg=%s date=%s form=%s lit=%r'
          % (i, r['a'][:22], r['b'][:22], r['_sid'], sq(r['_pkg'], 22), r['date'], r.get('_form'), r['_lit']))
    print('     scored=%s shipped=%s tone=%s   surname_tokens=%d/%d distinct=%d  (thresholds: >=10 distinct, >=0.35)'
          % (o['scored'], o['edge_shipped'], o['tone_cls'] or '-', len(hit), len(toks),
             len({G['nrm'](t) for t in hit})))
    print('     WINDOW: %s' % sq(w, 620))


dump('G3', s3, 'G3_p3b_sample40_UNGRADED.json',
     'G3  P3b HITS: %d of %d roster/signature-list mentions (seed %d) -- ARTEFACT / GENUINE / UNCLEAR'
     % (N, len(LHITS), SEED), render3)
dump('G5a', s5a, 'G5a_p2_unflagged40_UNGRADED.json',
     'G5a  P2-A RECALL PROBE: %d of %d UNFLAGGED INTERVIEW mentions (seed %d) -- TRUE-BLEED / GENUINE / UNCLEAR'
     % (N, len(P2_UNFLAGGED_INT), SEED), render5a)
dump('G5b', s5b, 'G5b_p3b_unflagged40_UNGRADED.json',
     'G5b  P3b RECALL PROBE: %d of %d UNFLAGGED CREC mentions (seed %d) -- ARTEFACT / GENUINE / UNCLEAR'
     % (N, len(P3B_UNFLAGGED_CREC), SEED), render5b)
print('DONE G3G5')
