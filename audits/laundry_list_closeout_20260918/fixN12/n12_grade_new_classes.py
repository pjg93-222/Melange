# -*- coding: utf-8 -*-
"""N12 adversarial pass, READ-ONLY.

The measurement graded D-U2 (40/40) and residual classes R1-R4 (72/72).  It NEVER graded R5, the
colon-less class, and the N12 grammar widened R4 so the split starts at the NAME rather than mid
title.  This prints, for hand grading:

  A  every row this run flags that the measurement did not (the census difference)
  B  class D (mixed-case label): every distinct tag, with counts
  C  class E (colon-less honorific): every distinct tag with counts, a seeded sample with
     context, and a census of two shapes that look like false positives -- a POSSESSIVE tag
     ("SEN. RICHARD BLUMENTHAL'S VOICE PLAYS") and a tag inside a PARENTHETICAL stage direction
  D  the 8 rows that carry no member words before the first tag (left untouched; residue)
"""
import collections
import io
import json
import os
import random
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import turn_tags as TT                      # noqa: E402
from members import migrate_interview_turn_bleed as MIG   # noqa: E402

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'
SEED = 20260919

extra = set(json.load(io.open(os.path.join(HERE, 'census_extra_ids.json'), encoding='utf-8')))
ROSTER = [m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json',
                                                 encoding='utf-8'))]
index = TT.build_roster_index(ROSTER)
con = MIG.open_ro(DB)
lexicon = MIG.build_lexicon(con, ROSTER)
plans = MIG.plan_all(con, index, lexicon)
con.close()
P = {p['rowid']: p for p in plans}


def window(plan, seg, before=150, after=200):
    t = plan['text']
    return (' '.join(t[max(0, seg['start'] - before):seg['start']].split()),
            ' '.join(t[seg['start']:seg['start'] + after].split()))


print('=' * 92)
print('A  EVERY ROW N12 FLAGS THAT THE MEASUREMENT DID NOT  (%d rows)' % len(extra))
print('=' * 92)
for rid in sorted(extra):
    plan = P[rid]
    seg = plan['segments'][0]
    b, a = window(plan, seg)
    print('rowid=%-7s %-24s %-14s %s  [%s]' % (rid, plan['member'][:24], plan['chamber'][:14],
                                               plan['date'], seg['class']))
    print('   tag  : %r  -> %s' % (seg['tag'], seg['disposition']))
    print('   B    : ...%s' % b[-140:])
    print('   A    : %s...' % a[:200])
    print()

print('=' * 92)
print('B  CLASS D (mixed-case label): every distinct tag')
print('=' * 92)
dtags = collections.Counter()
drows = set()
for plan in plans:
    for s in plan['segments']:
        if s['class'] == TT.CLASS_D and not s['own']:
            dtags[' '.join(s['tag'].split())] += 1
            drows.add(plan['rowid'])
print('rows with a class-D foreign tag: %d ; distinct tags: %d' % (len(drows), len(dtags)))
for t, n in dtags.most_common():
    print('  %4d  %s' % (n, t[:86]))

print()
print('=' * 92)
print('C  CLASS E (colon-less honorific): distinct tags, false-marker census, graded sample')
print('=' * 92)
etags = collections.Counter()
erows = set()
ehits = []
for plan in plans:
    for s in plan['segments']:
        if s['class'] == TT.CLASS_E and not s['own']:
            etags[' '.join(s['tag'].split())] += 1
            erows.add(plan['rowid'])
            ehits.append((plan, s))
print('rows with a class-E foreign tag: %d ; distinct tags: %d' % (len(erows), len(etags)))
for t, n in etags.most_common(30):
    print('  %4d  %s' % (n, t[:86]))

POSSESSIVE = re.compile(r"[A-Z]['`]S\b")


def inside_parenthetical(text, start):
    """True when the match sits inside an unclosed '(' -- a stage direction, not a turn."""
    opened = text.rfind('(', 0, start)
    if opened < 0:
        return False
    closed = text.rfind(')', 0, start)
    return opened > closed


poss = [(p, s) for p, s in ehits if POSSESSIVE.search(s['tag'])]
paren = [(p, s) for p, s in ehits if inside_parenthetical(p['text'], s['start'])]
print()
print('FALSE-MARKER CENSUS inside class E:')
print('  hits whose tag carries a POSSESSIVE ("...\'S")      : %d  (rows %s)'
      % (len(poss), sorted({p['rowid'] for p, _s in poss})[:12]))
print('  hits sitting INSIDE a parenthetical stage direction: %d  (rows %s)'
      % (len(paren), sorted({p['rowid'] for p, _s in paren})[:12]))
onlyE = sorted({p['rowid'] for p, _s in ehits}
               - {p['rowid'] for p in plans for s in p['segments']
                  if s['class'] != TT.CLASS_E and not s['own']})
print('  rows flagged ONLY by class E (nothing else sees them): %d' % len(onlyE))
for p, s in poss + paren:
    b, a = window(p, s)
    print('  ---- rowid=%s %s [%s] tag=%r' % (p['rowid'], p['member'], s['class'], s['tag']))
    print('       B: ...%s' % b[-120:])
    print('       A: %s...' % a[:170])

rnd = random.Random(SEED)
pool = sorted({p['rowid'] for p, _s in ehits})
sample = rnd.sample(pool, 25) if len(pool) >= 25 else pool
print()
print('SEEDED (%d) SAMPLE OF 25 CLASS-E ROWS FOR GRADING:' % SEED)
for i, rid in enumerate(sorted(sample), 1):
    plan = P[rid]
    seg = [s for s in plan['segments'] if s['class'] == TT.CLASS_E and not s['own']][0]
    b, a = window(plan, seg)
    print('%2d. rowid=%-7s %-22s %-12s tag=%r -> %s'
          % (i, rid, plan['member'][:22], plan['chamber'][:12], seg['tag'], seg['disposition']))
    print('    B: ...%s' % b[-150:])
    print('    A: %s...' % a[:210])

print()
print('=' * 92)
print('D  ROWS WITH NO MEMBER WORDS BEFORE THE FIRST TAG (left untouched -- residue)')
print('=' * 92)
for plan in plans:
    if plan['skip'] == MIG.NO_MEMBER_WORDS:
        print('rowid=%-7s %-24s %-16s %s [%s]' % (plan['rowid'], plan['member'][:24],
                                                  plan['chamber'][:16], plan['date'],
                                                  ','.join(plan['classes'])))
        print('   tag: %r' % plan['segments'][0]['tag'])
        print('   %s' % ' '.join(plan['text'].split())[:240])
print('DONE')
