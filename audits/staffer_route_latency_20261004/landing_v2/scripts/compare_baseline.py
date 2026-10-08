"""Compare a suite run with the 722a55ba7 baseline file by file: python compare_baseline.py <baseline.json> <run.json>

Prints every file whose counts changed, every file new in the run, and whether any failure is new (a file or test that fails in the run
but did not fail at the baseline).
"""
import json
import sys

base = {r['file']: r for r in json.load(open(sys.argv[1]))}
run = {r['file']: r for r in json.load(open(sys.argv[2]))}


def counts(r):
    return (r['passed'], r['failed'] + r['errors'], r['skipped'])


print('%-68s %-16s %-16s' % ('file', 'baseline p/f/s', 'run p/f/s'))
new_failures = []
for name in sorted(set(base) | set(run)):
    b, r = base.get(name), run.get(name)
    if b is None:
        print('%-68s %-16s %-16s  NEW FILE' % (name, '-', '%d/%d/%d' % counts(r)))
        if counts(r)[1]:
            new_failures.append((name, r['failures']))
        continue
    if r is None:
        print('%-68s %-16s %-16s  MISSING FROM RUN' % (name, '%d/%d/%d' % counts(b), '-'))
        new_failures.append((name, ['missing']))
        continue
    note = ''
    if counts(b) != counts(r):
        note = '  count changed'
    base_fail, run_fail = set(b['failures']), set(r['failures'])
    gained = sorted(run_fail - base_fail)
    if gained:
        note += '  NEW FAILURE'
        new_failures.append((name, gained))
    elif run_fail and run_fail == base_fail:
        note += '  (same failure as the baseline)'
    if note:
        print('%-68s %-16s %-16s%s' % (name, '%d/%d/%d' % counts(b), '%d/%d/%d' % counts(r), note))


def total(rows):
    return tuple(sum(counts(r)[i] for r in rows.values()) for i in range(3))


print()
print('baseline  files %d  passed/failed/skipped %s' % (len(base), total(base)))
print('run       files %d  passed/failed/skipped %s' % (len(run), total(run)))
print('new failures:', new_failures or 'none')
