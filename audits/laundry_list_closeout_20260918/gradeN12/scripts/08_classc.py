# -*- coding: utf-8 -*-
"""The 139 class-C rows whose kept text does not end on a sentence boundary: seeded sample of 20,
boundary shown tightly so the cut can be graded.  READ-ONLY."""
import io, json, random, re, sys

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
TERM = re.compile(r'(?:[.?!]["\u201d\']?|--|\u2014|>>|\))\s*$')

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

pool = [r for r in rows
        if not r['skip'] and not TERM.search(r['kept']['raw'].rstrip())]
pool.sort(key=lambda r: r['rowid'])
rnd = random.Random(20260919)
sample = sorted(rnd.sample(pool, 20), key=lambda r: r['rowid'])

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
out.write('pool = %d flagged rows whose kept text does not end on a sentence boundary\n' % len(pool))
out.write('seeded sample of 20 (seed 20260919), rowids: %s\n\n'
          % [r['rowid'] for r in sample])
for i, r in enumerate(sample, 1):
    seg = r['removed'][0]
    out.write('=' * 104 + '\n')
    out.write('C%02d rowid=%-7s member=%-24s show=%-16s kept_nw=%d\n'
              % (i, r['rowid'], r['member'], r['chamber'], r['kept']['nwords']))
    out.write('    KEPT tail   ...%s\n' % r['kept']['text'][-260:])
    out.write('    CUT here -> class=%-24s tag=%r disp=%s\n'
              % (seg['class'], seg['tag'][:70], seg['disposition']))
    out.write('    REMOVED     %s\n' % seg['raw'][:300])
    out.write('\n')
out.close()
print('written')
