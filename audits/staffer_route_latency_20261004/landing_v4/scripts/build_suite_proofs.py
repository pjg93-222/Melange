"""Assemble the suite proof files of landing_v4 from the run logs and JSON the runs left (read-only on everything but the outputs).

  proof/test_results_f23a40aee_vs_tip.txt   the clean export of f23a40aee (the state LIVE runs now) against the clean export of the v4 tip: every file's counts, new files, failures
  proof/applied_tree_suites.txt             the tree LIVE will hold after landing_v4 (clean 3248a6a02 + LIVE's current bytes for the patched files + landing_v4 by its own apply script)
                                            against the clean export of the v4 tip: counts must be equal file for file
  proof/extra_tests.txt                     the six tests that mention staffer_live but are not named test_staffer_*, at the baseline, the tip and the applied tree
usage: python build_suite_proofs.py <suites work dir> <landing_v4 dir>
"""
import json
import os
import subprocess
import sys

W, NEW = sys.argv[1], sys.argv[2]
OLD_BASELINE = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad/ids_followup2/suites_work/tip_f23a40aee_run.json'
BASE_RUN, TIP_RUN, APPLIED_RUN = W + '/base_f23a40aee_run.json', W + '/tip_v4_run.json', W + '/applied_tree_run.json'
BASE_EXTRA, TIP_EXTRA, APPLIED_EXTRA = W + '/base_f23a40aee_extra.json', W + '/tip_v4_extra.json', W + '/applied_tree_extra.json'
PREV_RUN, PREV_EXTRA = W + '/base_5d4a9bd0a_run.json', W + '/base_5d4a9bd0a_extra.json'    # the tip before the fix round: the baseline the round is measured against


def read(path):
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
n_app, t_app = totals(APPLIED_RUN)
write('test_results_f23a40aee_vs_tip.txt', [
    '# Staffer suites at f23a40aee (the state LIVE runs now: landing_v2 plus landing_v3_ids) and at the v4 tip (claude/staffer-route-v4-20261003): the same runner (scripts/run_suites.py: one process per file,',
    '# `python -m pytest <file>`, a file pytest collects no tests from is run as a script, every fec/tests/surfaces/test_*.cjs under `node --test`), a clean `git archive` export of each commit with autocrlf off',
    '# plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (scripts/export_and_run.sh). The exports have no .git, so the tests that read a base commit from git are skipped in both runs;',
    '# the tests that need git ran in the worktree (proof/new_tests_three_in_a_row.txt).',
    '',
    '## baseline f23a40aee: files %d, passed/failed/errors/skipped %s;  tip: files %d, %s' % (n_base, t_base, n_tip, t_tip),
    '',
    '## the baseline of this run against the baseline recorded for landing_v3_ids (the same commit, run earlier today under a heavier load): the counts must agree',
    compare(OLD_BASELINE, BASE_RUN),
    '',
    '## comparison, file by file (baseline = f23a40aee; only files whose counts changed, new files, missing files and failures are listed)',
    compare(BASE_RUN, TIP_RUN),
    '',
    '## the one red in both runs',
    'fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification  (known baseline red; fails identically at 722a55ba7, 86631c454, f23a40aee)',
    '',
    '## the intermittent failure that appears in this session\'s f23a40aee run only',
    'fec/tests/surfaces/test_staffer_identity_api.py::IdentityHTTPTests::test_assertion_endpoint_uses_local_origin_gate failed once in the f23a40aee run (8 passed, 1 failed in 0.75 s) and passed in the other runs of that file in this session\'s tip and 5d4a9bd0a runs and in the',
    'earlier session\'s baseline. It is an intermittent failure of the test\'s own HTTP client on this host (WinError 10053 while it reads the answer to a POST the handler rejects before reading the body); the same file, run 20 times in each tree',
    '(scripts/flake_identity_api.sh, proof/flake_identity_api.txt), fails in some runs of 5d4a9bd0a, of the tip and of the applied tree as well, and in a run of f23a40aee, with the same test names. No file this patch touches is involved (the handler, fec/surfaces/staffer_live_server.py, is not edited).',
    '',
    '## the suite run at the v4 tip',
    read(W + '/logs/tip_v4_suites.log'),
    '',
    '## the suite run at f23a40aee',
    read(W + '/logs/base_f23a40aee_suites.log'),
])
n_prev, t_prev = totals(PREV_RUN)
write('test_results_5d4a9bd0a_vs_tip.txt', [
    '# Staffer suites at 5d4a9bd0a (the tip of the first cut, before the fix round) and at the new tip: the same runner (scripts/run_suites.py: one process per file), a clean `git archive` export of each commit with autocrlf off',
    '# plus the 4 gitignored data files copied read-only from LIVE fec/surfaces (scripts/export_and_run.sh, scripts/run_tip_and_bases.sh). The exports have no .git, so the tests that read a base commit from git are skipped in both runs;',
    '# those ran with GIT_DIR at the shared object store (proof/git_history_subset.txt) and in the worktree (proof/new_tests_three_in_a_row.txt). Zero new failures means: no file or test that fails here did not fail at 5d4a9bd0a.',
    '# The files whose counts moved are the five the fix round changed (proof/fix_round.txt, section 3); every other file has the same counts.',
    '',
    '## 5d4a9bd0a: files %d, passed/failed/errors/skipped %s;  new tip: files %d, %s' % (n_prev, t_prev, n_tip, t_tip),
    '',
    '## comparison, file by file (baseline = 5d4a9bd0a; only files whose counts changed, new files, missing files and failures are listed)',
    compare(PREV_RUN, TIP_RUN),
    '',
    '## the one red in both runs',
    'fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification  (known baseline red; fails identically at 722a55ba7, 86631c454, f23a40aee, 5d4a9bd0a)',
    '',
    '## the suite run at the new tip',
    read(W + '/logs/tip_v4_suites.log'),
    '',
    '## the suite run at 5d4a9bd0a',
    read(W + '/logs/base_5d4a9bd0a_suites.log'),
])
write('applied_tree_suites.txt', [
    '# Staffer suites on the tree as LIVE will hold it after landing_v4 is applied, against the clean export of the v4 tip.',
    '# Applied tree: clean export of fec/ at 3248a6a02 (autocrlf off), LIVE\'s CURRENT bytes for the 34 patched files (the 31 landing_v2 and landing_v3_ids touched, plus the 3 more v4 edits; scripts/build_applied_tree.py: read-only copies, each checked against',
    '# the post-image of the last landing that touched it, or the pre-image of v4), landing_v4 applied with its apply_landing.py --apply (scripts/applied_tree_run.sh), the 4 gitignored data files copied read-only from LIVE fec/surfaces',
    '# (deleted afterwards). Same runner, one process per file. The tree has no .git, so the tests that read a base commit from git are skipped, as in the clean tip export. The applied tree holds this patch\'s',
    '# post-images, which keep their mixed terminators; the baseline here is the tip\'s own pure-LF blobs, so the two runs differ in bytes (terminators) and must agree in every count.',
    '',
    '## applied tree: files %d, passed/failed/errors/skipped %s;  tip export: files %d, %s' % (n_app, t_app, n_tip, t_tip),
    '',
    '## file for file',
    *file_for_file(TIP_RUN, APPLIED_RUN, 'tip export', 'applied tree'),
    '',
    '## comparison, file by file (baseline = clean export of the v4 tip; only files whose counts changed, new files, missing files and failures are listed)',
    compare(TIP_RUN, APPLIED_RUN),
    '',
    '## the one file that differs: test_staffer_identity_api.py (9 passed in the tip run, 9 passed and 1 failed in the applied-tree run)',
    'The same intermittent failure as in the f23a40aee run of proof/test_results_f23a40aee_vs_tip.txt: the test\'s own HTTP client gets WinError 10053 while it reads the answer to a POST the handler rejects before reading the body. The handler',
    '(fec/surfaces/staffer_live_server.py) is not part of any patch set here. Run 20 times in each tree (scripts/flake_identity_api.sh, proof/flake_identity_api.txt) the file fails in some runs of every tree and passes in the rest; in the',
    'applied tree it passed in the two re-runs made right after the suite run and failed in the third (a different test of the same file). Every other file has identical counts and identical failures.',
    '',
    '## the apply log',
    read(W + '/logs/applied_tree_run.log'),
    '',
    '## the suite run on the applied tree',
    read(W + '/logs/applied_tree_suites.log'),
])
write('extra_tests.txt', [
    '# The tests that mention staffer_live but are not named test_staffer_* (run_suites.py does not reach them): the dashboard, clean workspace, combined section, network html, edge startup and desktop tests.',
    '# Same method (scripts/run_extra.py: one process per file), at f23a40aee, at the v4 tip, and on the applied tree.',
    '',
    '## f23a40aee',
    read(W + '/logs/base_f23a40aee_extra.log'),
    '',
    '## 5d4a9bd0a (the tip before the fix round)',
    read(W + '/logs/base_5d4a9bd0a_extra.log'),
    '',
    '## v4 tip',
    read(W + '/logs/tip_v4_extra.log'),
    '',
    '## applied tree',
    read(W + '/logs/applied_tree_extra.log'),
    '',
    '## file for file',
    *file_for_file(BASE_EXTRA, TIP_EXTRA, 'f23a40aee', 'v4 tip'),
    *file_for_file(PREV_EXTRA, TIP_EXTRA, '5d4a9bd0a', 'v4 tip'),
    *file_for_file(TIP_EXTRA, APPLIED_EXTRA, 'v4 tip', 'applied tree'),
])
print('baseline: files %d %s ; tip: files %d %s ; applied: files %d %s' % (n_base, t_base, n_tip, t_tip, n_app, t_app))
