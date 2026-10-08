"""Assemble the remaining proof files of landing_v4 from the logs and JSON the runs left (read-only on everything but the outputs):

  proof/merge_and_commits.txt             the merge graph, the dry-run merges, the README sentences of all three branches in the merged file, the diffstat against f23a40aee
  proof/test_edits_negative_control.txt   the pre-edit hint tests against the merged code (they fail) and the edited ones (they pass)
  proof/git_history_subset.txt            the tests that skip in a clean export for want of git history, run with GIT_DIR on the tip export and on the applied tree
  proof/new_tests_three_in_a_row.txt      the new and changed tests, three runs in a row, in the worktree and in the clean tip export
  proof/ties.txt                          `python -m fec.surfaces.test_staffer_closeness_bidirectional --ties` on the tip export and on the applied tree
  proof/applied_tree_vs_tip.txt           the applied tree against the tip export, file by file
usage: python build_proof_extras.py <suites work dir> <landing_v4 dir> <landing_v4_work dir>
"""
import json
import os
import subprocess
import sys

W, NEW, WORK = sys.argv[1], sys.argv[2], sys.argv[3]
WT = r'C:/Users/pgoff/Melange-wt/route-core'
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONIOENCODING='utf-8')


def read(path):
    with open(path, encoding='utf-8', errors='replace') as handle:
        return handle.read().rstrip('\n')


def git(*args):
    return subprocess.run(['git', '-C', WT, *args], capture_output=True, env=env).stdout.decode('utf-8', 'replace').rstrip('\n')


def write(name, parts):
    with open(os.path.join(NEW, 'proof', name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(parts).rstrip('\n') + '\n')
    print('wrote', name)


def totals(path):
    rows = json.load(open(path, encoding='utf-8'))
    return len(rows), {k: sum(r[k] for r in rows) for k in ('passed', 'failed', 'errors', 'skipped')}, rows


tip = json.load(open(os.path.join(NEW, 'staffer_route_v4.summary.json'), encoding='utf-8'))['tip']
sentences = ['is answered only when the origin is not covered', 'there is no line in an `insufficient_work_coverage` answer whose origin is the person without coverage', 'a background prewarm builds the Staffer work index',
             'pairs_scored', 'committee name is searched like any other name', 'the tie window is judged within each alternative',
             'a whole bioguide id lists the staff attached to that member',
             'lack the payroll or staffer-roster coverage this model requires and were left out', 'the staff this search could use',
             'the milliseconds of the one garbage collection that precedes its first build (`gc_ms`)', 'dropped when the service installs a different mapping on the same router']
readme = subprocess.run(['git', '-C', WT, 'show', '%s:fec/surfaces/staffer_live/README.md' % tip], capture_output=True, env=env).stdout.decode('utf-8', 'replace')
write('merge_and_commits.txt', [
    '# The integration branch claude/staffer-route-v4-20261003 (worktree C:\\Users\\pgoff\\Melange-wt\\route-core), created from 1c66a85ba (claude/staffer-unreachable-hint-20261003), with',
    '# claude/staffer-coldpath-20261003 (c6c6c1c58) and claude/staffer-search-committee-names-20261003 (6a198d600) merged in. All three descend from f23a40aee, the content LIVE holds.',
    '',
    '## git log --graph from f23a40aee to the tip',
    git('log', '--graph', '--format=%h %s', 'f23a40aee..' + tip),
    '',
    '## the merges were conflict-free: `git merge-tree --write-tree --name-only` of each merge before it was made printed a tree id and no conflicted file name (rc 0)',
    '   hint + coldpath      : tree 7dfbb1cf12539e8d7f3b9356aadcd43c5dce5986, no conflict',
    '   (hint + coldpath) + committee names: tree 1cd8733b6e46f69326ceed9b89a8938712591988, no conflict',
    '   The staffer_live README was edited by all three branches in different paragraphs (the unreachable hint extends the state-model paragraph, the cold path adds the prewarm paragraph, the',
    '   committee-name restoration rewrites the identifier paragraph), so git merged it without a conflict and every sentence of all three is where its own branch put it. Present in the tip\'s README:',
    *['   %-120s %s' % (s, 'yes (%d)' % readme.count(s) if readme.count(s) else 'NO') for s in sentences],
    '',
    '## git diff --stat f23a40aee..tip',
    git('diff', '--stat', 'f23a40aee', tip),
    '',
    '## git diff --name-status f23a40aee..tip',
    git('diff', '--name-status', 'f23a40aee', tip),
])
write('test_edits_negative_control.txt', [
    '# The test edits of commit 20aefec50 are what the merge needs, and they are not weakenings.',
    '# On the merged tree (HEAD 7bf774055, before the edits) test_staffer_office_covered_staff.py and test_staffer_unreachable_hint.py as they were fail 35 of their 66 tests (33 and 2):',
    '# every comparison with the base commit sees pairs_scored on one side only, and the work counter sees pair_row where it counted pair.',
    '# The unedited files were run as zz_preedit_*.py copies beside the real ones (git show HEAD:<file>); the copies were removed afterwards.',
    '',
    read(os.path.join(WORK, 'logs', 'pre_edit_failures_on_merged.txt')),
    '',
    '# With the edits, the same two files and the route-jobs test fixed in fb3f874c2:',
    read(os.path.join(WORK, 'logs', 'after_test_edits_pytest.log')),
    '',
    '# Fix round (commit 7ce88cc52 and the tests of 453718ddc): the pair-count assertion that 20aefec50 loosened to `new_pairs <= old_pairs` is exact again, but counting only the pairs the base commit priced',
    '# between people who overlapped (work_of(..., overlapping_only=True), ExposureIndex.overlaps), so it equals the tip\'s count; the rows still equal the base commit\'s. Its negative controls, the changed expectations',
    '# of the sentences and the mutation checks are in proof/fix_round.txt.',
])
subset = []
for name in ('tip_v4', 'applied_tree'):
    subset += ['## %s' % ('clean export of the v4 tip' if name == 'tip_v4' else 'the applied tree (clean 3248a6a02 + LIVE\'s current bytes + landing_v4)'), read(os.path.join(W, 'logs', 'gitsubset_%s.log' % name)), '']
write('git_history_subset.txt', [
    '# Eight test files skip some of their tests in a clean `git archive` export, because those tests read a base commit with `git -C <root> show <sha>:<path>` and an export has no .git.',
    '# Here the same eight files run on the export and on the applied tree with GIT_DIR pointed at the shared object store (read-only: `git show` writes nothing), so nothing skips.',
    '# The numbers must equal the worktree runs (new_tests_three_in_a_row.txt), where git is available.',
    '',
    *subset])
runs = []
for label, title in (('worktree', 'the worktree itself (git available: no test skips)'), ('export', 'the clean export of the tip (no .git: the tests that read a base commit skip)')):
    runs += ['## %s' % title]
    for i in (1, 2, 3):
        path = os.path.join(W, 'new_%s_run%d.json' % (label, i))
        if not os.path.isfile(path):
            runs.append('run %d: (missing)' % i)
            continue
        n, t, rows = totals(path)
        runs.append('run %d: files %d, passed %d, failed %d, errors %d, skipped %d' % (i, n, t['passed'], t['failed'], t['errors'], t['skipped']))
    first = os.path.join(W, 'new_%s_run1.json' % label)
    if os.path.isfile(first):
        same = all(os.path.isfile(os.path.join(W, 'new_%s_run%d.json' % (label, i))) and
                   [(r['file'], r['passed'], r['failed'], r['errors'], r['skipped']) for r in json.load(open(os.path.join(W, 'new_%s_run%d.json' % (label, i)), encoding='utf-8'))] ==
                   [(r['file'], r['passed'], r['failed'], r['errors'], r['skipped']) for r in json.load(open(first, encoding='utf-8'))] for i in (2, 3))
        runs.append('the three runs agree file for file: %s' % ('yes' if same else 'NO'))
        runs += ['', 'per file (run 1; seconds of runs 1, 2, 3):']
        rows = {r['file']: r for r in json.load(open(first, encoding='utf-8'))}
        for rel, r in sorted(rows.items()):
            secs = []
            for i in (1, 2, 3):
                p = os.path.join(W, 'new_%s_run%d.json' % (label, i))
                if os.path.isfile(p):
                    secs.append(str({x['file']: x for x in json.load(open(p, encoding='utf-8'))}.get(rel, {}).get('seconds', '-')))
            runs.append('  %-72s passed %-4d failed %d skipped %-3d  %s s' % (rel, r['passed'], r['failed'], r['skipped'], ', '.join(secs)))
    runs.append('')
write('new_tests_three_in_a_row.txt', [
    '# The new and changed staffer tests of the v4 tip: every test file the three branches add and every one this integration edits, run three times in a row (scripts/run_new_tests_3x.sh,',
    '# one process per file: pytest per Python file, a file pytest collects no tests from run as a script, `node --test` per .cjs file).',
    '', *runs])
ties = []
for name in ('tip_v4', 'applied_tree'):
    p = os.path.join(W, 'logs', 'ties_%s.log' % name)
    ties += ['## %s' % ('clean export of the v4 tip' if name == 'tip_v4' else 'the applied tree'), read(p) if os.path.isfile(p) else '(not run)', '']
write('ties.txt', ['# python -m fec.surfaces.test_staffer_closeness_bidirectional --ties  (the verifier\'s tie-heavy graphs, 20,000 per mode, both modes), run from the root of each tree.', '', *ties])
write('applied_tree_vs_tip.txt', [
    '# The applied tree (clean `git archive 3248a6a02 fec` + LIVE\'s current bytes for the 34 patched files + landing_v4 by its own apply script) against the clean export of the v4 tip,',
    '# every file the tip tracks under fec/ (git ls-tree -r --name-only <tip> -- fec: 1,732 files), by live_patch.py drift. EOL_ONLY: the content is identical and the terminators are LIVE\'s own,',
    '# which the patch keeps (a file that LIVE holds CRLF or mixed stays so); CONTENT must be 0.',
    '', read(os.path.join(WORK, 'compare_trees_applied_vs_tip.txt'))])
