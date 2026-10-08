"""Assemble the suite, evidence and mutation proof files of landing_v4_1 from the run logs and JSON the runs left (read-only on everything but the outputs).

  proof/test_results_79ef9f1b7_vs_tip.txt   the clean export of 79ef9f1b7 (the v4 tip that LIVE runs now) against the clean export of the v4.1 tip: every file's counts, new files, failures
  proof/applied_tree_suites.txt             the tree LIVE will hold after landing_v4_1 (clean 3366a7840 + LIVE's current bytes for the earlier landings' files + landing_v4_1 by its own apply script)
                                            against the clean export of the v4.1 tip: counts must be equal file for file
  proof/extra_tests.txt                     the six tests that mention staffer_live but are not named test_staffer_*, at the baseline, the tip and the applied tree
  proof/new_tests_three_in_a_row.txt        the new and changed test files, three runs in a row, in the worktree and in the clean export
  proof/git_history_subset.txt              the tests that skip in an export for want of git history, run with GIT_DIR at the shared object store
  proof/ties.txt                            --ties on the tip export and on the applied tree
  proof/old_tests_on_new_code.txt           the four test files as they were at 79ef9f1b7 against the new code: the intended expectation changes
  proof/mutations.txt                       the mutation checks
  proof/evidence_gc_and_rebuild.txt         publish memory, gc cost, the re-check's stress script, the directory-only scenario: before (79ef9f1b7) and after (the tip)
usage: python build_proofs.py <suites work dir> <landing_v4_1 dir>
"""
import json
import os
import subprocess
import sys

W, NEW = sys.argv[1], sys.argv[2]
BASE_RUN, TIP_RUN, APPLIED_RUN = W + '/base_v4_run.json', W + '/tip_v41_run.json', W + '/applied_tree_run.json'
BASE_EXTRA, TIP_EXTRA, APPLIED_EXTRA = W + '/base_v4_extra.json', W + '/tip_v41_extra.json', W + '/applied_tree_extra.json'


def read(path, default='(missing)'):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8', errors='replace') as handle:
        return handle.read().rstrip('\n')


def compare(base, run):
    done = subprocess.run([sys.executable, NEW + '/scripts/compare_baseline.py', base, run], capture_output=True, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return done.stdout.decode('utf-8', 'replace').rstrip('\n')


def rows(path):
    return {r['file']: r for r in json.load(open(path, encoding='utf-8'))}


def counts(r):
    return (r['passed'], r['failed'], r['errors'], r['skipped'])


def totals(path):
    data = json.load(open(path, encoding='utf-8'))
    return len(data), tuple(sum(r[k] for r in data) for k in ('passed', 'failed', 'errors', 'skipped'))


def file_for_file(a_path, b_path, a_name, b_name):
    a, b = rows(a_path), rows(b_path)
    same = [f for f in a if f in b and counts(a[f]) == counts(b[f]) and a[f]['failures'] == b[f]['failures']]
    differ = [f for f in a if f in b and f not in same]
    return ['%s and %s: %d files in %s, %d in %s; %d files with identical counts and identical failures (passed, failed, errors, skipped), %d differing, %d only in %s, %d only in %s' % (
        a_name, b_name, len(a), a_name, len(b), b_name, len(same), len(differ), len(set(a) - set(b)), a_name, len(set(b) - set(a)), b_name)] + \
        ['  DIFFERS: %s %s -> %s' % (f, counts(a[f]), counts(b[f])) for f in differ]


def write(name, parts):
    with open(os.path.join(NEW, 'proof', name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(parts).rstrip('\n') + '\n')
    print('wrote', name)


n_base, t_base = totals(BASE_RUN)
n_tip, t_tip = totals(TIP_RUN)
write('test_results_79ef9f1b7_vs_tip.txt', [
    '# Staffer suites at 79ef9f1b7 (the v4 tip: what LIVE runs now) and at the v4.1 tip (claude/staffer-route-v4-1-20261004): the same runner (scripts/run_suites.py: one process per file,',
    '# `python -m pytest <file>`, a file pytest collects no tests from is run as a script, every fec/tests/surfaces/test_*.cjs under `node --test`), a clean `git archive` export of each commit with autocrlf off',
    '# plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (scripts/export_and_run.sh). The exports have no .git, so the tests that read a base commit from git are skipped in both runs;',
    '# those ran in the worktree (proof/new_tests_three_in_a_row.txt) and with GIT_DIR at the shared object store (proof/git_history_subset.txt).',
    '',
    '## 79ef9f1b7: files %d, passed/failed/errors/skipped %s;  v4.1 tip: files %d, %s' % (n_base, t_base, n_tip, t_tip),
    '',
    '## comparison, file by file (baseline = 79ef9f1b7; only files whose counts changed, new files, missing files and failures are listed)',
    compare(BASE_RUN, TIP_RUN),
    '',
    '## the suite run at the v4.1 tip',
    read(W + '/logs/tip_v41_suites.log'),
    '',
    '## the suite run at 79ef9f1b7',
    read(W + '/logs/base_v4_suites.log'),
])
if os.path.exists(APPLIED_RUN):
    n_app, t_app = totals(APPLIED_RUN)
    write('applied_tree_suites.txt', [
        '# Staffer suites on the tree as LIVE will hold it after landing_v4_1 is applied, against the clean export of the v4.1 tip.',
        '# Applied tree: clean export of fec/ at 3366a7840 (LIVE HEAD; autocrlf off), LIVE\'s CURRENT bytes for the 45 files landing_v2, landing_v3_ids and landing_v4 touched (scripts/build_applied_tree.py: read-only copies, each',
        '# checked against the post-image of the last landing that touched it), landing_v4_1 applied with its apply_landing.py --apply (scripts/applied_tree_run.sh), the 4 gitignored data files copied read-only from LIVE',
        '# fec/surfaces (deleted afterwards). Same runner, one process per file. The tree has no .git, so the tests that read a base commit from git are skipped, as in the clean tip export. The applied tree holds this',
        '# patch\'s post-images, which keep their mixed terminators; the baseline here is the tip\'s own pure-LF blobs, so the two runs differ in bytes (terminators) and must agree in every count.',
        '',
        '## applied tree: files %d, passed/failed/errors/skipped %s;  tip export: files %d, %s' % (n_app, t_app, n_tip, t_tip),
        '',
        '## file for file',
        *file_for_file(TIP_RUN, APPLIED_RUN, 'tip export', 'applied tree'),
        '',
        '## comparison, file by file (baseline = clean export of the v4.1 tip; only files whose counts changed, new files, missing files and failures are listed)',
        compare(TIP_RUN, APPLIED_RUN),
        '',
        '## the apply log',
        read(W + '/logs/applied_tree_run.log'),
        '',
        '## the suite run on the applied tree',
        read(W + '/logs/applied_tree_suites.log'),
    ])


def extra_block(label, path):
    if not os.path.exists(path):
        return ['## %s: (not run)' % label]
    data = json.load(open(path, encoding='utf-8'))
    return ['## %s' % label] + ['%-62s rc=%-4s %-6s pass %-4d fail %-3d err %-2d skip %-2d  %s' % (r['file'], r['rc'], r['mode'], r['passed'], r['failed'], r['errors'], r['skipped'], r.get('summary', '')[:70]) for r in data]


write('extra_tests.txt', [
    '# The tests that mention staffer_live but are not named test_staffer_* (run_suites.py does not reach them): the dashboard, clean workspace, combined section, network html, edge startup and desktop tests.',
    '# Same method (scripts/run_extra.py: one process per file), at 79ef9f1b7, at the v4.1 tip, and on the applied tree.',
    '',
    *extra_block('79ef9f1b7 (the v4 tip)', BASE_EXTRA), '', *extra_block('the v4.1 tip', TIP_EXTRA), '', *extra_block('the applied tree', APPLIED_EXTRA),
])

three = []
for label, title in (('worktree', 'in the worktree (git available: the tests that read a base commit run)'), ('export', 'in the clean export of the tip (no git history: those tests skip)')):
    for i in (1, 2, 3):
        path = W + '/new_%s_run%d.json' % (label, i)
        if os.path.exists(path):
            data = json.load(open(path, encoding='utf-8'))
            three += ['## %s, run %d: files %d, passed/failed/errors/skipped %s' % (title, i, len(data), tuple(sum(r[k] for r in data) for k in ('passed', 'failed', 'errors', 'skipped')))]
            three += ['   %-62s pass %-4d fail %-3d err %-2d skip %-2d' % (r['file'], r['passed'], r['failed'], r['errors'], r['skipped']) for r in data] if i == 1 else []
write('new_tests_three_in_a_row.txt', ['# The new and changed test files of the round and the suites around them (scripts/run_new_tests_3x.sh), three runs in a row each, one process per file.', '', *three])

subset = []
for name in ('tip_v41', 'applied_tree'):
    path = W + '/gitsubset_%s_run.json' % name
    if os.path.exists(path):
        data = json.load(open(path, encoding='utf-8'))
        subset += ['## %s: files %d, passed/failed/errors/skipped %s' % (name, len(data), tuple(sum(r[k] for r in data) for k in ('passed', 'failed', 'errors', 'skipped')))]
        subset += ['   %-62s pass %-4d fail %-3d err %-2d skip %-2d' % (r['file'], r['passed'], r['failed'], r['errors'], r['skipped']) for r in data]
write('git_history_subset.txt', ['# The tests that skip in a clean export for want of git history, with GIT_DIR at the shared object store (read-only) so `git show <sha>:<path>` works without a .git in the export.', '', *subset])
write('ties.txt', ['# python -m fec.surfaces.test_staffer_closeness_bidirectional --ties (20,000 tie-heavy graphs per mode, both modes)', '',
                   '## the v4.1 tip export', read(W + '/logs/ties_tip_v41.log'), '', '## the applied tree', read(W + '/logs/ties_applied_tree.log')])
if os.path.exists(W + '/old_tests_on_tip_run.json'):
    write('old_tests_on_new_code.txt', [
        '# The four test files the round changed, as they were at 79ef9f1b7, laid over the clean export of the v4.1 tip and run against its code (scripts/old_tests_on_new_code.sh). Every test that fails here asserts',
        '# something the round changed on purpose (see the README, "Intended changes"); every other test of those files passes.', '',
        read(W + '/logs/old_tests_on_tip.log'), '',
        '## failures, by file',
        *['%s\n%s' % (r['file'], '\n'.join('    ' + f for f in r['failures']) or '    (none)') for r in json.load(open(W + '/old_tests_on_tip_run.json', encoding='utf-8'))]])
write('mutations.txt', ['# Mutation checks (scripts/mutations.py): each is one edit to production code in a scratch copy of the tip export; the named tests must fail with it.', '', read(W + '/mutations.log')])
ev = W + '/evidence'
parts = ['# The gc and rebuild evidence (scripts/evidence.sh): clean exports of 79ef9f1b7 (before) and the v4.1 tip (after), one process at a time under memrun.py with a 1000 MB cap.', '']
for name in ('base_v4', 'tip_v41'):
    parts += ['============================================================ %s' % ('BEFORE: 79ef9f1b7 (v4)' if name == 'base_v4' else 'AFTER: the v4.1 tip')]
    for n in (20000, 40000):
        parts += ['## publish_memory.py %d people: %s' % (n, read('%s/publish_memory_%s_%d.memrun' % (ev, name, n)).splitlines()[0] if os.path.exists('%s/publish_memory_%s_%d.memrun' % (ev, name, n)) else '(missing)'),
                  read('%s/publish_memory_%s_%d.log' % (ev, name, n)), '']
    parts += ['## gc_measure.py 20000: %s' % (read('%s/gc_measure_%s.memrun' % (ev, name)).splitlines()[0] if os.path.exists('%s/gc_measure_%s.memrun' % (ev, name)) else '(missing)'), read('%s/gc_measure_%s.log' % (ev, name)), '']
    parts += ['## stress_release.py: %s' % (read('%s/stress_release_%s.memrun' % (ev, name)).splitlines()[0] if os.path.exists('%s/stress_release_%s.memrun' % (ev, name)) else '(missing)'), read('%s/stress_release_%s.log' % (ev, name)), '']
    note = ('' if name == 'base_v4' else '(on v4.1 the router stress_release.py runs this part on has been released for good by its part 1, so a request on it builds one index of its own, which is what the '
            '"builds during the request=1" column says there; the next section runs the same scenario on a router that has not been released)')
    parts += ['## rebuild_between_passes.py (part 2 on a fresh warm router per strategy): %s' % (read('%s/rebuild_between_passes_%s.memrun' % (ev, name)).splitlines()[0] if os.path.exists('%s/rebuild_between_passes_%s.memrun' % (ev, name)) else '(missing)'),
              read('%s/rebuild_between_passes_%s.log' % (ev, name)), '']
    if note:
        parts.insert(len(parts) - 5, note)
    parts += ['## directory_mode.py', read('%s/directory_mode_%s.log' % (ev, name)), '']
parts += ['============================================================ gc_measure.py repeated, alternating the trees', read(ev + '/gc_measure_repeat.txt'), '']
write('evidence_gc_and_rebuild.txt', parts)
