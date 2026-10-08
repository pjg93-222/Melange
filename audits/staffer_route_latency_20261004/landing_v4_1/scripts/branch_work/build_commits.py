"""Split the finished v4.1 working state into three commits (fixes 1-3, fix 4, fix 5) and prove the result equals the finished state byte for byte.

Run from anywhere; operates on the route-core worktree. Steps:
  1. copy every changed or new file to FINAL (a backup, outside the repository);
  2. restore the changed files to the branch base (git checkout -- <file>) and move the new file away;
  3. per group: apply that group's exact (old, new) pairs to the files built forward, copy the files that belong to one group whole from FINAL,
     `git add` them, commit with the group's message file;
  4. compare the worktree with FINAL: every file must be identical.
The pairs are read from the edit scripts that made the finished state (so they are the same strings), with the two later inline edits spelled out here.
"""
import os
import runpy
import shutil
import subprocess
import sys
import types

HERE = os.path.dirname(os.path.abspath(__file__))
WT = r'C:\Users\pgoff\Melange-wt\route-core'
FINAL = os.path.join(HERE, 'final_state')
MSGS = os.path.join(HERE, 'commit_messages')
sys.path.insert(0, HERE)

recorded = {}


def record(path, pairs):
    recorded.setdefault(os.path.normcase(path), []).extend(pairs)


stub = types.ModuleType('edit_lib')
stub.edit = record
stub.create = lambda *a, **k: None
sys.modules['edit_lib'] = stub
ns = {name: runpy.run_path(os.path.join(HERE, name + '.py')) for name in ('edit_closeness', 'edit_service', 'edit_page', 'edit_tests_hint')}
del sys.modules['edit_lib']
from edit_lib import edit  # the real one  # noqa: E402

rel = lambda p: os.path.relpath(p, WT).replace('\\', '/')
P = lambda r: os.path.join(WT, *r.split('/'))

CLOSE, SERVICE = 'fec/surfaces/staffer_closeness_routes.py', 'fec/surfaces/staffer_live_service.py'
README, HINT = 'fec/surfaces/staffer_live/README.md', 'fec/tests/surfaces/test_staffer_unreachable_hint.py'
c, s, p, h = ns['edit_closeness'], ns['edit_service'], ns['edit_page'], ns['edit_tests_hint']

# the closeness module docstring: one pair in the edit script, two here (the paragraph on the request scope is fix 2, the reflowed Coverage paragraph is fix 4)
doc_old, doc_new = c['DOC_OLD'], c['DOC_NEW']
cut = doc_new.index('One index per request.')
paragraph, reflowed = doc_new[cut:], doc_new[:cut - 1]
five_lines = doc_old[:-len('"""\n')]
assert doc_new == reflowed + '\n' + paragraph and doc_old.endswith('"""\n')
DOC_G1 = (doc_old, five_lines + '\n' + paragraph)
DOC_G2 = (five_lines, reflowed)

# the README sentence the explanation edit tweaked after the edit script ran
REASON = (p['README_REASON_OLD'], "or excluded), an `explanation` that is that same text (an unreachable answer with no reason keeps the generic explanation), and, like `insufficient_work_coverage`, a `suggested_objective` of `evidence_cost`;")
REASON_OLD_FULL = p['README_REASON_OLD']
README_G3 = (REASON_OLD_FULL, REASON[1])

GROUPS = [
    ('g1', 'staffer_route_v4_1_a.txt',
     {CLOSE: [(c['IMPORTS_OLD'], c['IMPORTS_NEW']), DOC_G1, (c['SCOPE_OLD'], c['SCOPE_NEW']), (c['INIT_OLD'], c['INIT_NEW']), (c['INDEX_OLD'], c['INDEX_NEW']),
              (c['STORE_OLD'], c['STORE_NEW']), (c['ROWS_OLD'], c['ROWS_NEW'])],
      SERVICE: [(s['INIT_OLD'], s['INIT_NEW']), (s['COMMENT_OLD'], s['COMMENT_NEW']), (s['RELEASE_OLD'], s['RELEASE_NEW']), (s['PREWARM_OLD'], s['PREWARM_NEW'])],
      README: [(p['README_PREWARM_OLD'], p['README_PREWARM_NEW'])]},
     ['fec/surfaces/staffer_routing.py', 'fec/tests/surfaces/test_staffer_prewarm.py', 'fec/tests/surfaces/test_staffer_request_work_index.py']),
    ('g2', 'staffer_route_v4_1_b.txt',
     {CLOSE: [DOC_G2, (c['OFFICE_OLD'], c['OFFICE_NEW'])],
      README: [(p['README_LEFT_OLD'], p['README_LEFT_NEW'])],
      HINT: [(h['FIELDS_OLD'], h['FIELDS_NEW'])]},
     ['fec/surfaces/staffer_distinct_routes.py', 'fec/surfaces/staffer_live/staffer-route.js', 'fec/tests/surfaces/test_staffer_office_covered_staff.py',
      'fec/tests/surfaces/test_staffer_left_out_staff.cjs']),
    ('g3', 'staffer_route_v4_1_c.txt',
     {SERVICE: [(s['EXPLAIN_OLD'], s['EXPLAIN_NEW'])],
      README: [README_G3],
      HINT: [(h['ANCHOR'], h['EXPLANATION'])]},
     []),
]
FORWARD = {CLOSE, SERVICE, README, HINT}
CHANGED = sorted({CLOSE, SERVICE, README, HINT} | {f for g in GROUPS for f in g[3]} - {'fec/tests/surfaces/test_staffer_request_work_index.py'})
NEW = ['fec/tests/surfaces/test_staffer_request_work_index.py']


def git(*args, check=True):
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1')
    done = subprocess.run(['git', *args], cwd=WT, capture_output=True, env=env)
    if check and done.returncode:
        raise SystemExit('git %s failed: %s' % (' '.join(args), done.stderr.decode('utf-8', 'replace')))
    return done.stdout.decode('utf-8', 'replace')


def main():
    if '--run' not in sys.argv:
        print('dry: groups', [g[0] for g in GROUPS], 'changed', CHANGED, 'new', NEW)
        return
    assert not os.path.exists(FINAL), 'FINAL exists: %s' % FINAL
    os.makedirs(FINAL)
    for r in CHANGED + NEW:
        target = os.path.join(FINAL, *r.split('/'))
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(P(r), target)
    status = git('status', '--porcelain')
    assert sorted(line[3:] for line in status.splitlines()) == sorted(CHANGED + NEW), status
    git('checkout', '--', *CHANGED)
    os.remove(P(NEW[0]))
    assert git('status', '--porcelain') == '', git('status', '--porcelain')
    for name, message, pairs, whole in GROUPS:
        for r, plist in pairs.items():
            edit(P(r), plist)
        for r in whole:
            shutil.copyfile(os.path.join(FINAL, *r.split('/')), P(r))
        git('add', '--', *sorted(set(pairs) | set(whole)))
        done = subprocess.run(['git', 'commit', '-F', os.path.join(MSGS, message)], cwd=WT, capture_output=True,
                              env=dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONDONTWRITEBYTECODE='1'))
        print(done.stdout.decode('utf-8', 'replace').strip().splitlines()[0] if done.returncode == 0 else done.stderr.decode('utf-8', 'replace'))
        if done.returncode:
            raise SystemExit(1)
    bad = [r for r in CHANGED + NEW if open(P(r), 'rb').read() != open(os.path.join(FINAL, *r.split('/')), 'rb').read()]
    print('worktree equals the finished state for %d files; differing: %s' % (len(CHANGED + NEW) - len(bad), bad))
    print(git('status', '--porcelain') or 'worktree clean')
    raise SystemExit(1 if bad else 0)


if __name__ == '__main__':
    main()
