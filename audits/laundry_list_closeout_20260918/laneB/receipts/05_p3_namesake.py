# -*- coding: utf-8 -*-
"""LANE B P3: famous-namesake collision on the bare full-name scan.

member_reference_layer.py:111-114 accepts ANY 'firstname lastname' string matching a roster
(variant-first, last) pair, with no evidence the person is the member.  July example:
Angus King -> "Mike Rogers at N.S.A." (signed positive) -- Mike Rogers the NSA director, not
Rep. Mike Rogers.

DETECTOR D-P3 (UNGUARDED upper bound)
  A mention is UNGUARDED iff  _form == 'BARE'  (matched by BARE_RE, not by the title path)
  AND its window contains NO member cue, where a cue is any case-insensitive match of:
    TITLE  rep. | representative | sen. | senator | congressman | congresswoman | chair |
           chairman | chairwoman | ranking member | speaker of the house | majority/minority
           leader | whip | delegate | lawmaker | member of congress | my colleague's title forms
    PLACE  any of the 50 state names + DC/PR/VI/GU/AS/MP, or a party-dash tag ([RDI]-XX),
           or republican | democrat | democratic | independent
    PEER   my colleague | my friend | my good friend | the gentleman | the gentlewoman |
           the gentlelady | our colleague | the senator | the congressman
  Window = the same 370-char window the layer built (speeches) / title or body slice (press).
  This is an UPPER BOUND on P3: an unguarded window may still be a real member mention.
  It is calibrated by a hand-graded random sample of 30 (seed 20260918).
READ-ONLY. Consumes SCRATCH/refs.jsonl."""
import collections, io, json, os, random, re, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
SCRATCH = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
           r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
           r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\laneB\receipts')

STATES = ('alabama alaska arizona arkansas california colorado connecticut delaware florida georgia hawaii idaho '
          'illinois indiana iowa kansas kentucky louisiana maine maryland massachusetts michigan minnesota '
          'mississippi missouri montana nebraska nevada "new hampshire" "new jersey" "new mexico" "new york" '
          '"north carolina" "north dakota" ohio oklahoma oregon pennsylvania "rhode island" "south carolina" '
          '"south dakota" tennessee texas utah vermont virginia washington "west virginia" wisconsin wyoming '
          '"district of columbia" "puerto rico" guam "american samoa"').replace('"', '').split()
TITLE = (r'\b(?:rep\.|representative|sen\.|senator|congressman|congresswoman|chair|chairman|chairwoman|'
         r'ranking member|speaker of the house|majority leader|minority leader|whip|delegate|lawmaker|'
         r'member of congress|the honorable)\b')
PLACE = r'\b(?:' + '|'.join(re.escape(s) for s in STATES) + r')\b|\b[RDI]-[A-Z]{2}\b|\b(?:republican|democrat|democratic|independent)\b'
PEER = (r'\b(?:my (?:good )?(?:colleague|friend)|our colleague|the gentleman|the gentlewoman|the gentlelady|'
        r'the senator|the congressman|the congresswoman|my fellow)\b')
CUE = re.compile('(?:%s)|(?:%s)|(?:%s)' % (TITLE, PLACE, PEER), re.I)

refs = [json.loads(l) for l in io.open(os.path.join(SCRATCH, 'refs.jsonl'), encoding='utf-8')]
art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}

bare = [r for r in refs if r.get('_form') == 'BARE']
title = [r for r in refs if r.get('_form') == 'TITLE']
print('=' * 78)
print('P3 : match-form census over all %d re-derived mentions' % len(refs))
print('=' * 78)
print('by form: %s' % dict(collections.Counter(r.get('_form') for r in refs)))
print('BARE (bare full-name scan)   : %d' % len(bare))
print('TITLE (title+surname path)   : %d' % len(title))
print()
for r in refs:
    w = r.get('_raw_w') or r['w']
    r['_cue'] = bool(CUE.search(w))
ung = [r for r in bare if not r['_cue']]
print('UNGUARDED (BARE, no cue in window) : %d   = %.1f%% of BARE, %.1f%% of all mentions' %
      (len(ung), 100.0 * len(ung) / max(1, len(bare)), 100.0 * len(ung) / len(refs)))
print('  by source: %s' % dict(collections.Counter(r['src'] for r in ung)))
sc = [r for r in ung if r['_counted_scored']]
ed = {(r['a'], r['b']) for r in ung}
eda = {k for k in ed if k in AE}
eds = {(r['a'], r['b']) for r in sc if (r['a'], r['b']) in AE}
signed = {k for k in eds if AE[k]['pos'] + AE[k]['neg'] > 0}
print()
print('unguarded windows counted into n_scored           : %d' % len(sc))
print('dyads touched                                    : %d' % len(ed))
print('SHIPPED edges touched                            : %d' % len(eda))
print('shipped edges with >=1 SCORED unguarded window    : %d' % len(eds))
print('  of those SIGNED (pos+neg>0)                     : %d' % len(signed))
print('  of those drawn (n_scored>=2)                    : %d' % sum(1 for k in eds if AE[k]['n_scored'] >= 2))
only = [k for k in eds if all((r['_cue'] or r.get('_form') != 'BARE')
                              for r in [] ) ]
# edges whose ENTIRE scored support is unguarded-bare
by_edge_scored = collections.defaultdict(list)
for r in refs:
    if r['_counted_scored']: by_edge_scored[(r['a'], r['b'])].append(r)
allung = [k for k, v in by_edge_scored.items()
          if k in AE and v and all(x.get('_form') == 'BARE' and not x['_cue'] for x in v)]
print('shipped edges whose ENTIRE scored support is unguarded-bare : %d' % len(allung))
print('  of those SIGNED   : %d' % sum(1 for k in allung if AE[k]['pos'] + AE[k]['neg'] > 0))
print('  of those drawn    : %d' % sum(1 for k in allung if AE[k]['n_scored'] >= 2))

print()
print('=== 20 most frequent UNGUARDED target names ===')
cnt = collections.Counter(r['b'] for r in ung)
print('%-32s %6s %8s %s' % ('target', 'n', 'lits', 'top literal spellings'))
for b, n in cnt.most_common(20):
    lits = collections.Counter(r['_lit'] for r in ung if r['b'] == b)
    print('%-32s %6d %8d %s' % (b[:32], n, len(lits), [l for l, _ in lits.most_common(3)]))

print()
print('=== 20 most frequent UNGUARDED literal strings ===')
for l, n in collections.Counter(r['_lit'] for r in ung).most_common(20):
    print('   %-34r %6d' % (l, n))

# -------- random sample of 30 for hand grading --------
rnd = random.Random(20260918)
samp = rnd.sample(ung, 30)
rows = []
for i, r in enumerate(samp, 1):
    rows.append({'n': i, 'speaker': r['a'], 'target': r['b'], 'src': r['src'], 'sid': r['_sid'],
                 'literal': r['_lit'], 'date': r['date'], 'scored': r['_counted_scored'],
                 'edge_shipped': (r['a'], r['b']) in AE,
                 'window': ' '.join((r.get('_raw_w') or r['w']).split()),
                 'grade': ''})
with io.open(os.path.join(PK, '05_p3_sample30_ungraded.json'), 'w', encoding='utf-8') as f:
    json.dump({'seed': 20260918, 'population': len(ung), 'n': 30, 'rows': rows}, f, ensure_ascii=False, indent=1)
print()
print('=' * 78)
print('RANDOM SAMPLE OF 30 UNGUARDED WINDOWS (seed 20260918) -- for hand grading')
print('=' * 78)
for r in rows:
    print()
    print('[%02d] %s  ->  %s   (literal %r | src=%s sid=%s scored=%s shipped=%s)' %
          (r['n'], r['speaker'], r['target'], r['literal'], r['src'], r['sid'], r['scored'], r['edge_shipped']))
    print('     %s' % r['window'][:600])
print()
print('wrote receipts/05_p3_sample30_ungraded.json')
print('DONE 05')
