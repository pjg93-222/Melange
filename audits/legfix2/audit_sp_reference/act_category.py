# -*- coding: utf-8 -*-
"""Q5 test: is the SAME ACT sorted into the same category under each of its bill numbers?"""
import sys, collections
import pandas as pd
B = r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, r'C:\Users\pgoff\OneDrive\Desktop\Melange Systems\.claude\worktrees\legislative-data-audit-1ad63e\fec')
import bill_rules as BR

A = pd.read_excel(B + r'\congress_bills_archive_20260624_115822.xlsx', sheet_name='All Bills')
A['tnorm'] = A['Title'].astype(str).str.lower().str.replace(r'\s+', ' ', regex=True).str.strip()
A['cat'] = A['Section'].astype(str).map(lambda s: BR.canonical_category(s))
A['inst'] = A['Name'].astype(str).str.strip() + '/C' + A['Congress'].astype(str)

# per act: the set of canonical categories reached by EACH instance
act_inst_cats = collections.defaultdict(dict)
for t, inst, cat in A[['tnorm', 'inst', 'cat']].drop_duplicates().itertuples(index=False):
    act_inst_cats[t].setdefault(inst, set()).add(cat)

multi = {t: d for t, d in act_inst_cats.items() if len(d) > 1}
print('acts with >1 bill instance:', len(multi))

incons = {}
for t, d in multi.items():
    sets = list(d.values())
    if any(s != sets[0] for s in sets[1:]):
        incons[t] = d
print('acts whose instances DISAGREE on category set: %d (%.1f%% of multi-instance acts)'
      % (len(incons), 100.0*len(incons)/len(multi)))

# how many bill instances / archive rows sit under an inconsistent act
inst_ct = sum(len(d) for d in incons.values())
rows_ct = int(A[A['tnorm'].isin(incons)].shape[0])
print('bill instances involved: %d | archive rows involved: %d of %d (%.1f%%)'
      % (inst_ct, rows_ct, len(A), 100.0*rows_ct/len(A)))

print('\nWORST EXAMPLES (act -> instance: categories):')
ranked = sorted(incons.items(), key=lambda kv: -int(A[A['tnorm'] == kv[0]].shape[0]))
for t, d in ranked[:10]:
    n = int(A[A['tnorm'] == t].shape[0])
    print('\n  %-56s (%d rows)' % (t[:56], n))
    for inst, cats in sorted(d.items()):
        print('      %-16s -> %s' % (inst, sorted(c for c in cats)))
