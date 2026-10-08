# -*- coding: utf-8 -*-
"""N12-v2 VERIFICATION of the live dry run.  READ-ONLY.

Answers, from the v2 ledger and the v1 ledger side by side:
  1. every row gradeN12 named: what does v2 do with it, and is that what the grade asked for?
  2. the CU-extract and label-bound protections: did every protected row survive untouched?
  3. v1 vs v2: which rows moved, in which direction, and why.
  4. is the AMBIGUOUS verdict a live code path or dead code?  (census over EVERY interview row,
     not only the flagged ones -- a verdict that never fires on the corpus must be shown to fire
     for the right reason, or it is not a safety rule at all.)
  5. the rows whose kept text sits exactly ON the eight-word floor: rule (a) is '< 8', so these
     are the rows the floor does NOT save.
"""
import collections
import io
import json
import os
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import turn_tags as TT                       # noqa: E402
from members import migrate_interview_turn_bleed as MIG    # noqa: E402

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = os.path.join(LIVE, 'social_media.db')
V1 = os.path.join(WT, 'audits', 'laundry_list_closeout_20260918', 'fixN12', 'dry_run_ledger.jsonl')
SKIPSET = os.path.join(HERE, 'v2_skipset.json')
V2 = sys.argv[1]            # the v2 ledger, in SCRATCH

GRADE_ROWS = {
    80238: 'G1 chyron insert (Cassidy)', 192027: 'G1 chyron insert (Scalise)',
    226287: 'G1 chyron insert (Thompson)', 245558: 'G1 WRONG-SPEAKER (Mike Johnson x5)',
    68730: 'G1 partial foreign', 102837: 'G1 partial foreign (UNIDENTIFIED)',
    104285: 'G1 partial foreign (no-space colon)', 108647: 'G1 partial foreign x4',
    111034: 'G1 partial foreign x2', 242833: 'G1 partial foreign (BRET BAIER)',
    258736: 'G2a PBS anchor', 258820: 'G2a PBS anchor', 258130: 'G2a PBS anchor',
    257343: 'G2a PBS anchor', 258713: 'G2a PBS anchor',
    82055: 'G2b abbreviation anchor', 71147: 'G2b abbreviation anchor',
    70812: 'G2b abbreviation anchor', 205497: 'G2b abbreviation anchor',
    225986: 'G2c pre-existing wrong person', 70149: 'G2d class C name residue',
    83941: 'G2d class C name residue', 192133: 'G2d class C name residue',
    193439: 'G2d class C name residue', 83061: 'G3 member words removed',
    69544: 'G4 OK. OK. WILD', 244993: 'G4 OK. OK. WILD', 278454: 'G4 OK. Q:',
    278528: 'G4 OK. Q:', 66969: 'G4 Grassley oath', 245771: 'in-use gold / CU row',
    70117: 'class E timestamp run', 191195: 'class E possessive', 225128: 'stage direction',
}

skip = json.load(io.open(SKIPSET, encoding='utf-8'))
CU = set(skip['cu_rowids'])
LABEL = set(skip['label_rowids_interview'])

v2 = {}
with io.open(V2, encoding='utf-8') as fh:
    for line in fh:
        r = json.loads(line)
        v2[r['rowid']] = r
v1 = {}
if os.path.exists(V1):
    with io.open(V1, encoding='utf-8') as fh:
        for line in fh:
            r = json.loads(line)
            v1[r['rowid']] = r

print('=' * 100)
print('1. EVERY ROW gradeN12 NAMED')
print('=' * 100)
print('%-8s %-34s %-11s %-34s %s' % ('rowid', 'what the grade called it', 'v2', 'cut tag', 'keep/cut words'))
for rid in sorted(GRADE_ROWS):
    r = v2.get(rid)
    if r is None:
        verdict, tag, words = 'NOT FLAGGED', '-', '-'
    elif r['skip']:
        verdict, tag = 'SKIP:' + r['skip'][:9], (r['cut_tag'] or '-')
        words = '%s kept' % r['kept']['nwords']
    else:
        verdict, tag = 'TRUNCATE', r['cut_tag']
        words = '%d kept / %d cut' % (r['kept']['nwords'], r['removed']['nwords'])
    print('%-8d %-34s %-11s %-34s %s' % (rid, GRADE_ROWS[rid][:34], verdict,
                                         ' '.join(str(tag).split())[:34], words))

print()
print('=' * 100)
print('2. PROTECTION')
print('=' * 100)
touched = {rid for rid, r in v2.items() if not r['skip']}
print('CU-gate rows (rule c)                     : %d' % len(CU))
print('  of those FLAGGED                        : %d' % len(CU & set(v2)))
print('  of those TRUNCATED  (must be 0)         : %d  %s'
      % (len(CU & touched), sorted(CU & touched)[:20]))
print('label-bound INTERVIEW rows (rule b)       : %d' % len(LABEL))
print('  of those FLAGGED                        : %d' % len(LABEL & set(v2)))
print('  of those TRUNCATED  (must be 0)         : %d  %s'
      % (len(LABEL & touched), sorted(LABEL & touched)[:20]))
print('245771 (in-use gold / Risch)              : %s'
      % ('SKIPPED: ' + str(v2[245771]['skip']) if 245771 in v2 and v2[245771]['skip']
         else ('NOT FLAGGED' if 245771 not in v2 else 'TRUNCATED -- CONTRACT BREACH')))
cu_csv = os.path.join(LIVE, 'data', 'stance', 'interviews_cu.csv')
n_cu_items = sum(1 for _ in io.open(cu_csv, encoding='utf-8-sig')) - 1
print('interviews_cu.csv data rows (the CU items): %d' % n_cu_items)

print()
print('=' * 100)
print('3. V1 vs V2')
print('=' * 100)
v1ids, v2ids = set(v1), set(v2)
v1_would_write = {rid for rid, r in v1.items() if not r.get('skip')}
print('v1 flagged %d ; v2 flagged %d' % (len(v1ids), len(v2ids)))
print('v1 would WRITE %d rows (5,859 UPDATE + 64 INSERT in the grade) ; v2 would TRUNCATE %d'
      % (len(v1_would_write), len(touched)))
print('rows v2 flags that v1 did not      : %d' % len(v2ids - v1ids))
print('rows v1 flagged that v2 does not   : %d' % len(v1ids - v2ids))
print('rows v1 would have written and v2 refuses: %d' % len(v1_would_write - touched))
why = collections.Counter()
for rid in sorted(v1_would_write - touched):
    if rid not in v2:
        why['v2 finds no FOREIGN tag (lenient own rule / filler guard / stricter anchor)'] += 1
    else:
        why['v2 skip: ' + str(v2[rid]['skip'])] += 1
for k, n in why.most_common():
    print('    %-72s %6d' % (k[:72], n))
newcls = collections.Counter(v2[r]['cut_class'] for r in (v2ids - v1ids) if v2[r]['cut_class'])
print('  the %d newly flagged rows, by the class that cut them:' % len(v2ids - v1ids))
for k, n in newcls.most_common():
    print('    %-72s %6d' % (k, n))
moved = [rid for rid in (v1ids & v2ids)
         if rid in touched and rid in v1_would_write
         and v1[rid]['kept']['text'] != v2[rid]['kept']['text']]
print('  rows BOTH would change but at a DIFFERENT cut point: %d' % len(moved))
for rid in moved[:12]:
    print('    %-8d v1 keeps %4d w | v2 keeps %4d w | v2 tag=%r'
          % (rid, len(v1[rid]['kept']['text'].split()), v2[rid]['kept']['nwords'],
             ' '.join(str(v2[rid]['cut_tag']).split())[:46]))

print()
print('=' * 100)
print('4. IS THE AMBIGUOUS VERDICT A LIVE PATH?  census over EVERY interview row')
print('=' * 100)
con = MIG.open_ro(DB)
roster = [m['member'] for m in json.load(io.open(os.path.join(LIVE, 'data', 'engine',
                                                              'congestion.json'),
                                                 encoding='utf-8'))]
lex = MIG.build_lexicon(con, roster)
own = collections.Counter()
amb_examples = []
near_probe = 0
for rid, member, chamber, text in con.execute(
        "SELECT rowid,member,chamber,text FROM speeches WHERE source='INTERVIEW'"):
    for h in TT.find_turn_tags(text or '', member, lex, chamber, True):
        own[h.ownership] += 1
        if h.ownership == TT.AMBIGUOUS and len(amb_examples) < 25:
            amb_examples.append((rid, member, h.tag, h.cls))
con.close()
for k, n in own.most_common():
    print('  %-10s %8d tags' % (k, n))
print('  ambiguous examples:')
for rid, member, tag, cls in amb_examples:
    print('    %-8d %-24s %-14s %r' % (rid, str(member)[:24], cls, ' '.join(str(tag).split())[:60]))
if not amb_examples:
    print('    NONE on this corpus.  Unit proof that the path is live and correct:')
    for tag, mem in (('CHARLIES (voice-over)', 'Cy Charlie'), ('PRESIDENT AND', 'Ada Alpher'),
                     ('ALPHERS', 'Ada Alpher'), ('MURRAYS (voice-over)', 'Patty Murray')):
        print('      tag_ownership(%-24r, %-14r) = %s' % (tag, mem, TT.tag_ownership(tag, mem)))

print()
print('=' * 100)
print('5. THE EIGHT-WORD FLOOR IS "< 8": the rows sitting exactly ON it are NOT saved')
print('=' * 100)
on_floor = sorted(rid for rid, r in v2.items()
                  if not r['skip'] and r['kept']['nwords'] == TT.MIN_TURN_WORDS)
print('rows truncated to EXACTLY %d words: %d' % (TT.MIN_TURN_WORDS, len(on_floor)))
print('  83061 (the one row the grade proved loses the member own words) is here: %s'
      % (83061 in on_floor))
for rid in on_floor[:10]:
    r = v2[rid]
    print('    %-8d %-22s keeps %r' % (rid, str(r['member'])[:22], r['kept']['text'][:80]))
hist = collections.Counter(r['kept']['nwords'] for r in v2.values() if not r['skip'])
print('  kept-word distribution just above the floor: '
      + ', '.join('%dw:%d' % (w, hist.get(w, 0)) for w in range(8, 16)))

print()
print('=' * 100)
print('6. EVERY ROW V1 FLAGGED THAT V2 DOES NOT, and a seeded sample of the newly flagged')
print('=' * 100)
for rid in sorted(v1ids - v2ids):
    r1 = v1[rid]
    tags = [' '.join(str(s.get('tag')).split()) for s in r1.get('removed', [])][:3]
    print('  %-8d %-22s v1 tag(s)=%s' % (rid, str(r1.get('member'))[:22], tags))
    print('        v1 would have kept: %r' % (r1['kept']['text'][:90],))
import random                                                            # noqa: E402
rnd = random.Random(20260919)
new = sorted(v2ids - v1ids)
for rid in rnd.sample(new, min(20, len(new))):
    r = v2[rid]
    print('  NEW %-8d %-20s [%s] tag=%r' % (rid, str(r['member'])[:20], r['cut_class'],
                                            ' '.join(str(r['cut_tag']).split())[:52]))
    print('        keeps ...%r' % (r['kept']['text'][-70:],))
    print('        cuts    %r...' % (r['removed']['raw'][:100],))
print('DONE')
