# -*- coding: utf-8 -*-
"""G2/G3 sample: seed 20260919, 60 rows = 20 class E + 20 class D + 20 other.  READ-ONLY."""
import io, json, random, sys

LEDGER = (r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees'
          r'\unfinished-work-handoff-a3bbad\audits\laundry_list_closeout_20260918\fixN12'
          r'\dry_run_ledger.jsonl')
SEED = 20260919

rows = []
with io.open(LEDGER, encoding='utf-8') as fh:
    for line in fh:
        line = line.strip()
        if line:
            rows.append(json.loads(line))

pool = [r for r in rows if not r['skip']]
stratE = sorted((r for r in pool if 'E_colonless_honorific' in r['foreign_classes']),
                key=lambda r: r['rowid'])
stratD = sorted((r for r in pool if 'D_mixed_case_label' in r['foreign_classes']),
                key=lambda r: r['rowid'])
dids = {r['rowid'] for r in stratD}
eids = {r['rowid'] for r in stratE}
stratO = sorted((r for r in pool if r['rowid'] not in dids and r['rowid'] not in eids),
                key=lambda r: r['rowid'])
print('strata sizes: E=%d D=%d other=%d  (E&D overlap=%d)'
      % (len(stratE), len(stratD), len(stratO), len(eids & dids)))

rnd = random.Random(SEED)
samE = rnd.sample(stratE, 20)
samD = rnd.sample(stratD, 20)
samO = rnd.sample(stratO, 20)
sample = [('E', r) for r in samE] + [('D', r) for r in samD] + [('O', r) for r in samO]

ids = io.open(sys.argv[2], 'w', encoding='utf-8', newline='\n')
json.dump({'seed': SEED, 'strata': {'E': [r['rowid'] for r in samE],
                                    'D': [r['rowid'] for r in samD],
                                    'other': [r['rowid'] for r in samO]},
           'strata_sizes': {'E': len(stratE), 'D': len(stratD), 'other': len(stratO)}},
          ids, indent=1)
ids.close()

out = io.open(sys.argv[1], 'w', encoding='utf-8', newline='\n')
for n, (stratum, r) in enumerate(sample, 1):
    txt = r['original']['text']
    out.write('=' * 112 + '\n')
    out.write('SAMPLE %02d [stratum %s] rowid=%s member=%s date=%s show=%s\n'
              % (n, stratum, r['rowid'], r['member'], r['date'], r['chamber']))
    out.write('  original nwords=%d  kept nwords=%d  classes=%s\n'
              % (r['original']['nwords'], r['kept']['nwords'], r['classes']))
    out.write('  --- KEPT TEXT (what the member keeps) ---\n')
    kept = r['kept']['text']
    if len(kept) <= 1400:
        out.write('  %s\n' % kept)
    else:
        out.write('  [first 500] %s\n' % kept[:500])
        out.write('  [last  900] ...%s\n' % kept[-900:])
    for i, seg in enumerate(r['removed'], 1):
        out.write('  --- REMOVED seg %d/%d  class=%s own=%s speaker=%r disp=%s nwords=%d ---\n'
                  % (i, len(r['removed']), seg['class'], seg['own'], seg['speaker'],
                     seg['disposition'], seg['nwords']))
        out.write('      tag=%r\n' % seg['tag'])
        raw = seg['raw']
        if len(raw) <= 1200:
            out.write('      RAW %s\n' % raw)
        else:
            out.write('      RAW[:700] %s\n' % raw[:700])
            out.write('      RAW[-400:] ...%s\n' % raw[-400:])
    out.write('\n')
out.close()
print('sample rows written: %d' % len(sample))
