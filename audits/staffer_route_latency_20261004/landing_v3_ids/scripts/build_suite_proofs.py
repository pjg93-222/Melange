"""Assemble the three suite proof files of the re-cut landing_v3_ids from the run logs and JSON the two runs left (read-only on everything but the three outputs).

  proof/applied_tree_suites.txt              the applied tree (LIVE-as-it-was + landing_v2 + this patch, each by its own apply script) against the clean export of the new tip
  proof/test_results_previous_tip_vs_new_tip.txt   the clean export of the previous tip a5e33a0b2 (first cut) against the clean export of the new tip f23a40aee
  proof/extra_tests.txt                      the six extra tests that mention staffer_live, at the new tip
"""
import json
import os
import subprocess
import sys

SP = r'C:/Users/pgoff/AppData/Local/Temp/claude/C--Users-pgoff-OneDrive-Desktop-Melange-Systems/4f30368b-c2d1-47f6-a368-3d68b2892c85/scratchpad'
NEW = SP + '/landing_v3_ids'
W = SP + '/ids_followup2/suites_work'
PREV_RUN = SP + '/ids_followup/tip_run1.json'  # run_suites.py on the clean export of a5e33a0b2 (first cut)
TIP_RUN = W + '/tip_f23a40aee_run.json'
APPLIED_RUN = W + '/applied_tree_run.json'
TIP_EXTRA = W + '/tip_f23a40aee_extra.json'


def read(path):
    with open(path, encoding='utf-8', errors='replace') as handle:
        return handle.read().rstrip('\n')


def compare(base, run):
    done = subprocess.run([sys.executable, NEW + '/scripts/compare_baseline.py', base, run], capture_output=True, env=dict(os.environ, PYTHONIOENCODING='utf-8'))
    return done.stdout.decode('utf-8', 'replace').rstrip('\n')


def totals(path):
    rows = json.load(open(path, encoding='utf-8'))
    return len(rows), tuple(sum(r[k] for r in rows) for k in ('passed', 'failed', 'errors', 'skipped'))


def write(name, parts):
    with open(os.path.join(NEW, 'proof', name), 'w', encoding='utf-8', newline='\n') as handle:
        handle.write('\n'.join(parts).rstrip('\n') + '\n')
    print('wrote', name)


write('applied_tree_suites.txt', [
    '# Staffer suites on the tree as LIVE will hold it after landing_v2 and this follow-up (the second cut) are both applied, against the clean export of the new tip f23a40aee.',
    "# Applied tree: clean export of fec/ at 3248a6a02 (autocrlf off), landing_v2's 13 edited files replaced by LIVE's exact pre-image bytes, LIVE's own staffer-live.js, landing_v2 applied with its apply_landing.py --apply,",
    '# then landing_v3_ids with its apply_landing.py --apply (scripts/applied_tree_run.sh), the 4 gitignored data files copied read-only from LIVE fec/surfaces (deleted afterwards). Same runner, one process per file.',
    '# The tree has no .git, so the four negative controls that read the old code from git are skipped, as in the clean tip export. The applied tree holds this patch\'s post-images, which keep their',
    "# mixed terminators; the baseline is the tip's own pure-LF blobs, so the two runs differ in bytes (terminators) and must agree in every count.",
    '',
    '## comparison, file by file (baseline = clean export of the new tip f23a40aee; only files whose counts changed, new files, missing files and failures are listed)',
    compare(TIP_RUN, APPLIED_RUN),
    '',
    '## the apply log',
    read(W + '/logs/applied_tree_run.log'),
    '',
    '## the suite run on the applied tree',
    read(W + '/logs/applied_tree_suites.log'),
])

n_prev, t_prev = totals(PREV_RUN)
n_tip, t_tip = totals(TIP_RUN)
write('test_results_previous_tip_vs_new_tip.txt', [
    '# Staffer suites at the previous tip a5e33a0b2 (the first cut) and at the new tip f23a40aee (the same runner, one process per file, clean git archive export with autocrlf off + the 4 gitignored data files',
    '# copied read-only from LIVE fec/surfaces). The previous-tip run is the one recorded for the first cut (previous_tip_a5e33a0b2/test_results_previous_tip_vs_followup_tip.txt).',
    '# The new commit changes two files (a docstring in staffer_closeness_routes.py, one sentence in the staffer_live README); every count is expected to be the same file for file.',
    '# The export has no .git, so the four negative controls that read the old code from git are skipped in this run (they run in the worktree: see new_tests_three_in_a_row.txt).',
    '',
    '## comparison, file by file (baseline = a5e33a0b2; only files whose counts changed, new files, and failures are listed)',
    compare(PREV_RUN, TIP_RUN),
    '',
    '## the one red in both runs',
    'fec/surfaces/test_repin_staffer_live.py::VerificationDerivationTests::test_default_generation_derives_expected_default_verification  (known baseline red; fails identically at 722a55ba7, 86631c454 and a5e33a0b2)',
    '',
    '## the suite run at the new tip f23a40aee',
    read(W + '/logs/tip_f23a40aee_suites.log'),
])

write('extra_tests.txt', [
    '# The tests that mention staffer_live but are not named test_staffer_* (run_suites.py does not reach them): the dashboard, clean workspace, combined section, network html, edge startup and desktop tests.',
    '# Same method: clean git archive export with autocrlf off, one process per file (scripts/run_extra.py), at the new tip f23a40aee. The same six files at 86631c454 and a5e33a0b2 are in previous_tip_a5e33a0b2/extra_tests.txt',
    '# (287 passed, 0 failed, 2 skipped at both).',
    '',
    '## new tip f23a40aee',
    read(W + '/logs/tip_f23a40aee_extra.log'),
])
print('previous tip run: files %d %s ; new tip run: files %d %s' % (n_prev, t_prev, n_tip, t_tip))
