# -*- coding: utf-8 -*-
"""Independent census of the N12 dry-run ledger.  READ-ONLY."""
import io, json, collections, sys

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

print('ledger records            : %d' % len(rows))
print('distinct rowids           : %d' % len({r['rowid'] for r in rows}))

disp = collections.Counter()
cls_rows = collections.Counter()
cls_seg = collections.Counter()
skips = collections.Counter()
recon_bad = []
chars_removed = 0
inserts = []
for r in rows:
    if r['skip']:
        skips[r['skip']] += 1
    if not r['reconstructs']:
        recon_bad.append(r['rowid'])
    for cls in r['foreign_classes']:
        cls_rows[cls] += 1
    for seg in r['removed']:
        disp[seg['disposition']] += 1
        cls_seg[seg['class']] += 1
        if not r['skip']:
            chars_removed += len(seg['raw'])
        if seg['disposition'] in ('reattributed', 'own_later_turn'):
            inserts.append((r, seg))

print('reconstruct failures      : %d %s' % (len(recon_bad), recon_bad[:20]))
print('chars removed (mine)      : %d' % chars_removed)
print('skip rows                 : %s' % dict(skips))
print('rows with a skip          : %s' % sorted(r['rowid'] for r in rows if r['skip']))
print()
print('-- dispositions (per segment) --')
for k, v in sorted(disp.items()):
    print('  %-32s %d' % (k, v))
print('  TOTAL segments                   %d' % sum(disp.values()))
print()
print('-- foreign classes (per ROW, a row can carry >1) --')
for k, v in sorted(cls_rows.items()):
    print('  %-32s %d' % (k, v))
print('  sum of per-row class counts      %d' % sum(cls_rows.values()))
print()
print('-- every class, per SEGMENT --')
for k, v in sorted(cls_seg.items()):
    print('  %-32s %d' % (k, v))
print()
print('planned INSERTs           : %d' % len(inserts))
ic = collections.Counter(seg['disposition'] for _r, seg in inserts)
print('  by disposition          : %s' % dict(ic))
icc = collections.Counter(seg['class'] for _r, seg in inserts)
print('  by detector class       : %s' % dict(icc))
print()
# rows_would_update per the tool's own definition
print('rows_would_update (mine)  : %d' % (len(rows) - skips.get('row_has_no_member_words', 0)))

# duplicate-key sanity: would two inserts collide with each other?
keys = collections.Counter()
for r, seg in inserts:
    keys[(seg['speaker'], r['date'], r['package'], seg['text'])] += 1
dups = {k: v for k, v in keys.items() if v > 1}
print('insert keys colliding     : %d' % len(dups))

# chamber values present among flagged rows
ch = collections.Counter(r['chamber'] for r in rows)
print()
print('-- chamber (the `show` arg) among flagged rows, top 25 --')
for k, v in ch.most_common(25):
    print('  %-28r %d' % (k, v))

with io.open(sys.argv[1], 'w', encoding='utf-8') as fh:
    json.dump({'n_rows': len(rows), 'dispositions': dict(disp),
               'class_rows': dict(cls_rows), 'class_segments': dict(cls_seg),
               'chars_removed': chars_removed, 'n_inserts': len(inserts),
               'recon_failures': recon_bad, 'skips': dict(skips)},
              fh, indent=1, sort_keys=True)
