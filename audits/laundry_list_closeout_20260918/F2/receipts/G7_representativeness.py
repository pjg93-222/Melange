# -*- coding: utf-8 -*-
"""F2: is the 40-window P2-A sample representative of the 249?  Compares the sample's marginals
against the population's on source, marker kind, names_target, inside_tag and scored.  Same for the
P3b sample against its 749.  Pure counting; READ-ONLY."""
import collections, csv, io, json, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
PK = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
      r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\F2\receipts')
LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'

pop = json.load(io.open(os.path.join(PK, '04b_p2_union_examples.json'), encoding='utf-8'))
sam = json.load(io.open(os.path.join(PK, 'G2a_p2_sample40_UNGRADED.json'), encoding='utf-8'))['rows']
print('P2-A  population %d   sample %d' % (len(pop), len(sam)))
print('  %-16s %-34s %s' % ('field', 'population', 'sample (expected at 40/249=16.06%)'))
for f, pf, sf in (('source', 'src', 'src'), ('marker kind', '_kind', 'marker_kind'),
                  ('names_target', '_names_target', 'names_target'),
                  ('inside_tag', '_inside_tag', 'inside_tag'),
                  ('scored', '_counted_scored', 'scored')):
    cp = collections.Counter(str(h[pf]) for h in pop)
    cs = collections.Counter(str(h[sf]) for h in sam)
    exp = {k: round(v * 40.0 / len(pop), 1) for k, v in cp.items()}
    print('  %-16s %-34s %s   exp %s' % (f, dict(cp), dict(cs), exp))

art = json.load(io.open(LIVE + r'\member_references.json', encoding='utf-8'))
AE = {(e['a'], e['b']): e for e in art['edges']}
print()
pop3 = json.load(io.open(os.path.join(PK, 'G3_p3b_sample40_UNGRADED.json'), encoding='utf-8'))['rows']
print('P3b  sample %d vs the 749 population (source/form marginals from lane B\'s own census)' % len(pop3))
print('  population by source {CREC: 567, PRESS_OFFICIAL_MENTION: 182}  -> expected 30.3 / 9.7 at 40/749')
print('  sample     by source %s' % dict(collections.Counter(r['src'] for r in pop3)))
print('  population by form   {BARE: 555, TITLE: 12, TYPED: 182}        -> expected 29.6 / 0.6 / 9.7')
print('  sample     by form   %s' % dict(collections.Counter(str(r['form']) for r in pop3)))
print('  sample     scored    %s' % dict(collections.Counter(str(r['scored']) for r in pop3)))
print('DONE G7')
