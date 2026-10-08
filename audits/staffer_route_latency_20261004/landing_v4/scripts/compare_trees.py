"""Compare two scratch trees file by file, with live_patch's drift verdict: IDENTICAL_BYTES, EOL_ONLY (the same content, other terminators) or CONTENT.

usage: python compare_trees.py <tree A> <tree B> [--tracked <file listing one repo path per line>] [--list]
Used to prove that the applied tree (clean 3248a6a02 + LIVE's current bytes for the patched files + landing_v4) holds exactly the content of the clean export of the v4 tip.
With --tracked, the files compared are the ones listed (the tip's `git ls-tree -r --name-only <tip> -- fec`), each of which must exist in both trees; any other file a tree has
(a test run's leftovers) is counted and shown, and does not fail the comparison. Without it every file of both trees is compared and a file only one tree has fails it.
The 4 gitignored data files and __pycache__ are never compared. Read-only.   exit 0 when there is no CONTENT difference and no missing file; 1 otherwise.
"""
import os
import sys

LIVE = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems'
sys.path.insert(0, os.path.join(LIVE, 'fec', 'tools'))
import live_patch as lp  # noqa: E402

DATA = {'staffer_identity_reference_seeds.json', 'staffer_named_filing_evidence.json', 'staffer_payroll_inventory_exceptions.json', 'staffer_user_assertions.json'}


def listing(root):
    found = {}
    for folder, dirs, names in os.walk(root):
        dirs[:] = [d for d in dirs if d != '__pycache__']
        for name in names:
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root).replace(os.sep, '/')
            if rel.startswith('fec/surfaces/') and name in DATA and rel.count('/') == 2:
                continue
            found[rel] = path
    return found


args = [x for x in sys.argv[1:] if not x.startswith('--')]
a_root, b_root = args[0], args[1]
tracked = None
if '--tracked' in sys.argv:
    path = sys.argv[sys.argv.index('--tracked') + 1]
    args = [x for x in args if x != path]
    a_root, b_root = args[0], args[1]
    tracked = {line.strip() for line in open(path, encoding='utf-8') if line.strip()}
a, b = listing(a_root), listing(b_root)
wanted = sorted(tracked) if tracked is not None else sorted(set(a) | set(b))
verdicts = {'IDENTICAL_BYTES': [], 'EOL_ONLY': [], 'CONTENT': []}
missing_a, missing_b = [], []
for rel in wanted:
    if rel not in a:
        missing_a.append(rel)
    if rel not in b:
        missing_b.append(rel)
    if rel in a and rel in b:
        report = lp.drift_report(open(a[rel], 'rb').read(), open(b[rel], 'rb').read())
        verdicts[report['verdict']].append(rel)
extra_a = sorted(set(a) - set(wanted)) if tracked is not None else []
extra_b = sorted(set(b) - set(wanted)) if tracked is not None else []
print('A %s: %d files; B %s: %d files; %d files compared%s' % (a_root, len(a), b_root, len(b), len(wanted), ' (the tracked list)' if tracked is not None else ' (every file of either tree)'))
print('IDENTICAL_BYTES %d, EOL_ONLY %d, CONTENT %d; missing from A %d, missing from B %d; not in the list: in A %d, in B %d' % (
    len(verdicts['IDENTICAL_BYTES']), len(verdicts['EOL_ONLY']), len(verdicts['CONTENT']), len(missing_a), len(missing_b), len(extra_a), len(extra_b)))
for rel in verdicts['CONTENT']:
    print('CONTENT      ', rel)
for rel in missing_a:
    print('MISSING IN A ', rel)
for rel in missing_b:
    print('MISSING IN B ', rel)
for rel in extra_a:
    print('EXTRA IN A   ', rel)
for rel in extra_b:
    print('EXTRA IN B   ', rel)
if '--list' in sys.argv:
    for rel in verdicts['EOL_ONLY']:
        print('EOL_ONLY     ', rel)
sys.exit(1 if verdicts['CONTENT'] or missing_a or missing_b else 0)
