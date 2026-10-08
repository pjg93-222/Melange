# -*- coding: utf-8 -*-
"""N12: every row the migration would INSERT, verbatim, plus the class of every census extra.
READ-ONLY."""
import collections
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import turn_tags as TT                      # noqa: E402
from members import migrate_interview_turn_bleed as MIG   # noqa: E402

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
ROSTER = [m['member'] for m in json.load(io.open(LIVE + r'\data\engine\congestion.json',
                                                 encoding='utf-8'))]
index = TT.build_roster_index(ROSTER)
con = MIG.open_ro(LIVE + r'\social_media.db')
lexicon = MIG.build_lexicon(con, ROSTER)
plans = MIG.plan_all(con, index, lexicon)
seen = MIG.existing_row_keys(con)
con.close()
P = {p['rowid']: p for p in plans}

extra = set(json.load(io.open(os.path.join(HERE, 'census_extra_ids.json'), encoding='utf-8')))
print('census extras by detector class:')
c = collections.Counter()
for rid in extra:
    for cls in P[rid]['foreign_classes']:
        c[cls] += 1
for k, v in c.most_common():
    print('  %-26s %4d' % (k, v))

print()
print('=' * 92)
print('EVERY ROW THE MIGRATION WOULD INSERT (source member -> new row member), verbatim')
print('=' * 92)
n = 0
byclass = collections.Counter()
dup = set()
for plan in sorted(plans, key=lambda p: p['rowid']):
    if plan['skip']:
        continue
    for s in plan['segments']:
        if s['disposition'] not in (MIG.REATTRIBUTED, MIG.OWN_LATER_TURN):
            continue
        key = (s['speaker'], plan['date'], plan['package'], s['text'])
        if key in seen or key in dup:
            continue
        dup.add(key)
        n += 1
        byclass[(s['class'], s['disposition'])] += 1
        print('%2d. from rowid=%-7s %-22s -> %-22s %s %s [%s/%s]'
              % (n, plan['rowid'], plan['member'][:22], s['speaker'][:22], plan['date'],
                 plan['chamber'][:14], s['class'], s['disposition']))
        print('    tag  : %r' % s['tag'])
        print('    text : %s' % s['text'][:300])
print()
print('inserted rows by (class, disposition):')
for k, v in sorted(byclass.items()):
    print('  %-46s %4d' % (str(k), v))
print('total inserts: %d' % n)

print()
print('=' * 92)
print('DOES ANY INSERTED / LEDGERED SEGMENT START WITH TAG RESIDUE (an ALL-CAPS role tail)?')
print('=' * 92)


def residue(text):
    toks = text.split(' ')[:6]
    run = []
    for t in toks:
        core = t.strip(",.;:()")
        if core and not any(ch.islower() for ch in core) and any(ch.isalpha() for ch in core):
            run.append(t)
        else:
            break
    return ' '.join(run)


ins_res = 0
led_res = 0
for plan in plans:
    if plan['skip']:
        continue
    for s in plan['segments']:
        r = residue(s['text'])
        if len(r.split()) < 2:
            continue
        if s['disposition'] in (MIG.REATTRIBUTED, MIG.OWN_LATER_TURN):
            ins_res += 1
            print('  INSERT rowid=%-7s %-20s tag=%r' % (plan['rowid'], s['speaker'][:20], s['tag']))
            print('     residue: %r' % r)
            print('     text   : %s' % s['text'][:160])
        else:
            led_res += 1
print('inserted segments starting with >=2 ALL-CAPS tokens : %d' % ins_res)
print('ledger-only segments starting with >=2 ALL-CAPS tokens: %d (ledger only, never displayed)'
      % led_res)
print('DONE')
