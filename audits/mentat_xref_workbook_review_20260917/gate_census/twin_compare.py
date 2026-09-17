"""Compare the authoritative R classifier against the Python twin over every
distinct classifier-input tuple found in the 8 databases."""
import csv, os, sys, importlib.util
from collections import Counter

OUT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, 'C:/Users/pgoff/Mentat/mentat/tools')
spec = importlib.util.spec_from_file_location(
    'pac_evidence', 'C:/Users/pgoff/Mentat/mentat/tools/pac_evidence.py')
pac = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pac)

csv.field_size_limit(10 ** 8)
with open(os.path.join(OUT, 'twin_r_roles.csv'), newline='',
          encoding='utf-8-sig') as f:
    rows = list(csv.DictReader(f))

UNRESOLVED = lambda r: r == '' or r == 'intermediary_role_review' or r.startswith('unverified_')

diff = []
verdict_diff = []
counts = Counter()
for r in rows:
    py = pac.receipt_role(r)
    rr = r['r_role']
    counts[(rr, py)] += 1
    if py != rr:
        diff.append((rr, py, r['filing_form'], r['line_number'],
                     r['receipt_type_full'][:60], r['memo_text'][:60]))
        if UNRESOLVED(py) != UNRESOLVED(rr):
            verdict_diff.append((rr, py, r['filing_form'], r['line_number'],
                                 r['receipt_type_full'][:60], r['memo_text'][:60]))

print('tuples compared          :', len(rows))
print('role string disagreements:', len(diff))
print('REFUSE/ALLOW disagreements:', len(verdict_diff))
print()
if diff:
    print('role disagreements by (R role -> Python role):')
    for (rr, py), n in sorted(Counter((d[0], d[1]) for d in diff).items(),
                              key=lambda kv: -kv[1]):
        print('  %-32s -> %-32s %d' % (rr, py, n))
    print()
    print('examples:')
    for d in diff[:15]:
        print('  R=%-28s PY=%-24s form=%-4s line=%-5s rtf=%r memo=%r'
              % (d[0], d[1], d[2], d[3], d[4], d[5]))
print()
if verdict_diff:
    print('VERDICT disagreements (these would change the refusal set):')
    for d in verdict_diff[:25]:
        print('  R=%-28s PY=%-24s form=%-4s line=%-5s rtf=%r memo=%r'
              % (d[0], d[1], d[2], d[3], d[4], d[5]))
else:
    print('No REFUSE/ALLOW verdict disagreement: the twin would refuse the same rows.')

with open(os.path.join(OUT, 'twin_disagreements.csv'), 'w', newline='',
          encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['r_role', 'python_role', 'verdict_differs', 'filing_form',
                'line_number', 'receipt_type_full', 'memo_text'])
    for d in diff:
        w.writerow([d[0], d[1], UNRESOLVED(d[1]) != UNRESOLVED(d[0]),
                    d[2], d[3], d[4], d[5]])
print('\nwrote twin_disagreements.csv')
