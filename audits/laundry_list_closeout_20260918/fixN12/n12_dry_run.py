# -*- coding: utf-8 -*-
"""N12 DRY RUN against the LIVE database, READ-ONLY.

Runs fec/members/migrate_interview_turn_bleed.py in --dry-run mode over the live corpus and then
answers the questions the coordinator has to rule on before anything is applied:

  1  census: rows flagged in total and per detector class, against the measured 5,835
     (audits/laundry_list_closeout_20260918/measR1d/receipts/U2c_all_affected_ids.json)
  2  what happens to each removed segment: kept / re-attributed (to whom) / ledger-only
  3  characters moved, rows that would be INSERTed
  4  the 999 mis-attributed reference mentions -- how many the split resolves (lane B refs.jsonl
     replayed against the new split points, the same classification U5_repair_cost.py used)
  5  the 18 contaminated desk excerpts -- how many the split resolves
  6  speeches row 245771 (the in-use Risch gold interview item) before and after, verbatim
  7  a seeded (20260919) 40-row sample of planned splits
  8  LABEL SAFETY: every record that points at a speeches row by rowid, by content hash or by
     character offset, intersected with the flagged set

Opens social_media.db ONLY as file:...?mode=ro with PRAGMA query_only.  Writes only into this
packet directory.  No fec production script is imported: turn_tags.py and the migration tool are
both pure/guarded, which the registered suite proves.
"""
import collections
import csv
import hashlib
import io
import json
import os
import re
import sqlite3
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(WT, 'fec'))
from members import turn_tags as TT                      # noqa: E402
from members import migrate_interview_turn_bleed as MIG   # noqa: E402

LIVE = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
DB = LIVE + r'\social_media.db'
MEAS = os.path.join(WT, 'audits', 'laundry_list_closeout_20260918', 'measR1d', 'receipts')
REFS = (r'C:\Users\pgoff\AppData\Local\Temp\claude'
        r'\C--Users-pgoff-OneDrive-Desktop-Melange-Systems--claude-worktrees-unfinished-work-handoff-a3bbad'
        r'\5b7f7c28-909b-48f8-a495-2da7aebcc0fe\scratchpad\laneB\refs.jsonl')
CLIPS = r'C:\melange-data\member_clips\clips_manifest.jsonl'
MPR = os.path.join(LIVE, 'outputs', 'member_personal_relationships')
SPEECHDIR = os.path.join(LIVE, 'data', 'speech')


def jload(path):
    with io.open(path, encoding='utf-8') as fh:
        return json.load(fh)


print('=' * 92)
print('N12 DRY RUN -- LIVE social_media.db, READ-ONLY')
print('=' * 92)
print('db bytes: %d' % os.path.getsize(DB))

expected = set(jload(os.path.join(MEAS, 'U2c_all_affected_ids.json')))
summary, plans = MIG.run_dry(DB, HERE, roster_path=os.path.join(LIVE, 'data', 'engine',
                                                                'congestion.json'),
                             colonless=True, expected_ids=expected)
P = {p['rowid']: p for p in plans}
got = set(P)

print()
print('-' * 92)
print('1  CENSUS vs THE MEASUREMENT')
print('-' * 92)
print('INTERVIEW rows                     : %d' % summary['interview_rows'])
print('rows FLAGGED by the repaired rule  : %d' % summary['rows_flagged'])
print('measured affected rows (U2c union) : %d' % len(expected))
print('  in both                          : %d' % len(got & expected))
print('  measured but NOT flagged now     : %d' % len(expected - got))
print('  flagged now but NOT measured     : %d' % len(got - expected))

# per-class comparison against the measurement's own class files
d_u2 = {r['rowid'] for r in jload(os.path.join(MEAS, 'U2_flagged_rows.json'))}
resid = jload(os.path.join(MEAS, 'U2b_residual_rows.json'))
r_sets = {k: {r['rowid'] for r in v} for k, v in resid.items()}
r5_new = set(jload(os.path.join(MEAS, 'U2c_colonless_new_ids.json')))
MEASURED = [('D-U2 anchored ALL-CAPS', d_u2), ('R1 STOP-name + paren', r_sets.get('R1', set())),
            ('R2 unknown surname + paren', r_sets.get('R2', set())),
            ('R3 unanchored + paren', r_sets.get('R3', set())),
            ('R4 mixed-case label', r_sets.get('R4', set())),
            ('R5 colon-less (new rows)', r5_new)]
mine = collections.defaultdict(set)
for rid, plan in P.items():
    for cls in plan['foreign_classes']:
        mine[cls].add(rid)
print()
print('%-30s %9s | %-26s %9s' % ('measured class', 'rows', 'N12 class', 'rows'))
for name, ids in MEASURED:
    print('%-30s %9d |' % (name, len(ids)))
for cls in TT.CLASSES:
    print('%-30s %9s | %-26s %9d' % ('', '', cls, len(mine.get(cls, ()))))
print()
print('per measured class, how many of its rows this run flags at all:')
for name, ids in MEASURED:
    if not ids:
        continue
    print('  %-30s %5d of %5d   (missed %d)' % (name, len(ids & got), len(ids), len(ids - got)))

missed = sorted(expected - got)
extra = sorted(got - expected)
io.open(os.path.join(HERE, 'census_missed_ids.json'), 'w', encoding='utf-8').write(
    json.dumps(missed))
io.open(os.path.join(HERE, 'census_extra_ids.json'), 'w', encoding='utf-8').write(
    json.dumps(extra))

con = MIG.open_ro(DB)
TXT = {rid: (t or '') for rid, t in con.execute(
    "SELECT rowid, text FROM speeches WHERE source='INTERVIEW'")}
META = {rid: (m, d, c, p) for rid, m, d, c, p in con.execute(
    "SELECT rowid, member, date, chamber, package FROM speeches WHERE source='INTERVIEW'")}
con.close()

print()
print('a sample of rows the measurement flagged and this run does not (up to 12):')
for rid in missed[:12]:
    m, d, c, p = META.get(rid, ('?', '?', '?', '?'))
    print('  rowid=%-7s %-22s %s %-16s %s' % (rid, m[:22], d, c[:16],
                                              ' '.join(TXT.get(rid, '').split())[:110]))
print()
print('a sample of rows this run flags and the measurement did not (up to 12):')
for rid in extra[:12]:
    m, d, c, p = META.get(rid, ('?', '?', '?', '?'))
    seg = P[rid]['segments'][0]
    print('  rowid=%-7s %-20s %-14s tag=%r [%s]' % (rid, m[:20], c[:14], seg['tag'], seg['class']))
    print('        B: ...%s' % P[rid]['kept_text'][-90:])
    print('        A: %s...' % ' '.join(seg['raw'].split())[:150])

print()
print('-' * 92)
print('2/3  WHAT MOVES')
print('-' * 92)
for k, v in sorted(summary['by_disposition'].items()):
    print('  %-34s %8d' % (k, v))
print('  %-34s %8d' % ('rows that would be UPDATEd', summary['rows_would_update']))
print('  %-34s %8d' % ('rows that would be INSERTed', summary['rows_would_insert']))
print('  %-34s %8d' % ('characters removed from flagged rows', summary['chars_removed']))
print('  every ledgered row reconstructs byte for byte: %s' % summary['every_row_reconstructs'])
print()
print('top 15 members receiving re-attributed turns:')
for m, n in summary['top_reattributed_members']:
    print('  %-32s %6d' % (m, n))

kept_words = sum(p['kept_nwords'] for p in plans if not p['skip'])
orig_words = sum(p['nwords'] for p in plans if not p['skip'])
print()
print('words in flagged rows before : %d' % orig_words)
print('words kept on those rows     : %d  (%.1f%%)' % (kept_words, 100.0 * kept_words / orig_words))
print('rows with NO member words at all before the first tag (left untouched, residue): %d'
      % summary['by_disposition'].get(MIG.NO_MEMBER_WORDS, 0))

print()
print('-' * 92)
print('4  THE 999 MIS-ATTRIBUTED REFERENCE MENTIONS')
print('-' * 92)
ROSTER = [m['member'] for m in jload(os.path.join(LIVE, 'data', 'engine', 'congestion.json'))]
SUR2MEM = collections.defaultdict(set)
for m in ROSTER:
    p = TT.normalize(m).split()
    if p:
        SUR2MEM[p[-1]].add(m)
cls = collections.Counter()
scored = collections.Counter()
n_iv = 0
for line in io.open(REFS, encoding='utf-8'):
    r = json.loads(line)
    if r.get('src') != 'INTERVIEW':
        continue
    n_iv += 1
    sid = r.get('_sid')
    plan = P.get(sid)
    if plan is None or plan['skip']:
        cls['SAME (row not repaired)'] += 1
        continue
    b0 = plan['segments'][0]['start']
    pos = (r.get('_pos') or 1) - 1
    wend = pos + 200
    if pos >= b0:
        seg = None
        for s in plan['segments']:
            if s['start'] <= pos < s['end']:
                seg = s
                break
        if seg is None:
            cls['AFTER SPLIT (unclassified)'] += 1
        elif seg['disposition'] in (MIG.REATTRIBUTED, MIG.OWN_LATER_TURN):
            cls['REASSIGN (segment speaker is a roster member)'] += 1
        else:
            cls['VANISH (segment speaker off-roster -> mention drops)'] += 1
        if r.get('_counted_scored'):
            scored['after split'] += 1
    elif wend > b0:
        cls['TRUNC (window crosses the split)'] += 1
        if r.get('_counted_scored'):
            scored['trunc'] += 1
    else:
        cls['SAME (window entirely before the split)'] += 1
print('INTERVIEW mentions in lane B refs.jsonl: %d' % n_iv)
for k in sorted(cls, key=lambda x: -cls[x]):
    print('  %-52s %6d' % (k, cls[k]))
resolved = sum(v for k, v in cls.items() if k.startswith(('VANISH', 'REASSIGN')))
print('mentions no longer attributed to the wrong speaker: %d' % resolved)
print('  of which currently carry a PAID label: %d' % sum(scored.values()))

print()
print('-' * 92)
print('5  THE 18 CONTAMINATED DESK EXCERPTS (personal texture)')
print('-' * 92)
hits = jload(os.path.join(MEAS, 'U3b_personal_texture_hits.json'))
fixed = still = unpinned = 0
for h in hits:
    rows = [r for r in h.get('rows') or [] if r in P]
    if not rows:
        unpinned += 1
        continue
    ev = ' '.join((h.get('evidence') or '').split())
    tag = (h['tags_in_evidence'] or h['tags_in_claim'])[0][1]
    if all(tag not in ' '.join(P[r]['kept_text'].split()) for r in rows):
        fixed += 1
    else:
        still += 1
print('items whose displayed text carries a foreign tag : %d' % len(hits))
print('  the tag leaves the kept text after the split   : %d' % fixed)
print('  the tag is still inside the kept text          : %d' % still)
print('  not pinned to a flagged row                    : %d' % unpinned)

print()
print('-' * 92)
print('6  speeches ROW 245771 -- the in-use James Risch gold interview item')
print('-' * 92)
plan = P.get(245771)
print('BEFORE (%d words):' % (plan['nwords'] if plan else -1))
print('  %r' % TXT.get(245771))
if plan:
    print('AFTER  (%d words):' % plan['kept_nwords'])
    print('  %r' % plan['kept_text'])
    for s in plan['segments']:
        print('REMOVED [%s] tag=%r -> %s' % (s['class'], s['tag'], s['disposition']))
        print('  %r' % s['text'])
else:
    print('  NOT FLAGGED -- investigate')

print()
print('-' * 92)
print('8  LABEL SAFETY -- every record that points at a speeches row')
print('-' * 92)
RX_ROWID = re.compile(r'speeches[/.]rowid=(\d+)|sqlite:speeches:(\d+)|"source_rowid":\s*(\d+)')


def scan_rowids(path):
    ids = set()
    try:
        with io.open(path, encoding='utf-8', errors='replace') as fh:
            for line in fh:
                for m in RX_ROWID.finditer(line):
                    ids.add(int(m.group(1) or m.group(2) or m.group(3)))
    except OSError:
        return None
    return ids


targets = []
if os.path.exists(CLIPS):
    targets.append(('clips_manifest.jsonl (axe clip provenance)', CLIPS))
for root, _dirs, files in os.walk(MPR):
    for fn in sorted(files):
        if fn.endswith(('.ndjson', '.json', '.jsonl')):
            targets.append((os.path.relpath(os.path.join(root, fn), LIVE),
                            os.path.join(root, fn)))
for fn in sorted(os.listdir(SPEECHDIR)) if os.path.isdir(SPEECHDIR) else []:
    if fn.endswith(('.jsonl', '.ndjson')):
        targets.append((os.path.join('data', 'speech', fn), os.path.join(SPEECHDIR, fn)))

collisions = []
for label, path in targets:
    ids = scan_rowids(path)
    if not ids:
        continue
    hit = ids & got
    if hit:
        collisions.append((label, len(ids), sorted(hit)))
print('%-72s %8s %8s' % ('artifact', 'rowids', 'FLAGGED'))
for label, n, hit in sorted(collisions, key=lambda x: -len(x[2])):
    print('%-72s %8d %8d' % (label[:72], n, len(hit)))
    print('        %s' % (', '.join(str(i) for i in hit[:20])
                          + (' ...' if len(hit) > 20 else '')))
if not collisions:
    print('  (no artifact that stores a speeches rowid points at a flagged row)')
io.open(os.path.join(HERE, 'label_safety_rowid_collisions.json'), 'w', encoding='utf-8').write(
    json.dumps([{'artifact': a, 'n_rowids': n, 'flagged': h} for a, n, h in collisions],
               ensure_ascii=False, indent=1))

print()
print('--- interview stance gold: does each hand label still bind? ---')
CU = os.path.join(LIVE, 'data', 'stance', 'interviews_cu.csv')
rows = list(csv.DictReader(io.open(CU, encoding='utf-8-sig')))
print('interviews_cu.csv rows: %d   columns: %s' % (len(rows), ','.join(rows[0].keys())))
gq = os.path.join(LIVE, 'data', 'stance', 'interview_gold_queue.csv')
gold = {r['id']: r for r in csv.DictReader(io.open(gq, encoding='utf-8-sig'))}
BYMD = collections.defaultdict(list)
for rid, (m, d, c, p) in META.items():
    BYMD[(m, (d or '')[:10])].append(rid)
stable = gone = shifted = unpinnable = 0
detail = []
for r in rows:
    rid_hash = 'x' + hashlib.md5(('%s|%s|%s' % (r.get('bioguide', ''), r.get('date', ''),
                                                r.get('text', ''))).encode('utf-8', 'replace')
                                 ).hexdigest()[:12]
    passage = ' '.join((r.get('text') or '').split())
    src = [rid for rid in BYMD.get((r.get('member'), (r.get('date') or '')[:10]), [])
           if passage[:60] and passage[:60] in ' '.join(TXT[rid].split())]
    if not src:
        unpinnable += 1
        continue
    aff = [rid for rid in src if rid in P]
    if not aff:
        stable += 1
        continue
    survives = any(passage in ' '.join(P[rid]['kept_text'].split()) if rid in P
                   else True for rid in src)
    if survives:
        shifted += 1
        detail.append(('PASSAGE SURVIVES IN THE KEPT TEXT', rid_hash, r, aff))
    else:
        gone += 1
        detail.append(('PASSAGE DISAPPEARS -> the hand label ORPHANS', rid_hash, r, aff))
print('hand-labelled interview rows      : %d (all 37 of interview_gold_queue.csv are filled)'
      % len(gold))
print('  passage on an UNflagged row     : %d  -> id unchanged, label binds' % stable)
print('  passage survives the split      : %d' % shifted)
print('  passage disappears              : %d  -> GOLD ORPHAN' % gone)
print('  could not be pinned to a row    : %d' % unpinnable)
for what, rid_hash, r, aff in detail:
    print('  %s' % what)
    print('    id=%s  %s %s  gold=%s  rows=%s' % (rid_hash, r.get('member'), r.get('date'),
                                                  (gold.get(rid_hash) or {}).get('gold_stance'),
                                                  aff))
    print('    passage: %s' % ' '.join((r.get('text') or '').split())[:220])

print()
print('DONE N12 DRY RUN')
