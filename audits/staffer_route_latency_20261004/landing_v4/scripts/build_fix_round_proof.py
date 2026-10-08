"""Assemble proof/fix_round.txt of landing_v4: what the fix round after the verifier's findings changed and the evidence for each part (read-only on everything but the output).

  1. the five findings, the commits that fix them and the exact new sentences
  2. the five test files the fix round changed, as they were at 5d4a9bd0a, run against the new code: every failure is an intended change of an expectation (the intended string changes)
  3. test counts of the changed files at 5d4a9bd0a and at the new tip, and the suites compared file by file
  4. the mutation checks: one edit to production code each, the named tests must fail
  5. peak memory of a router publish plus its prewarm, before and after, on synthetic worlds

usage: python build_fix_round_proof.py <suites work dir> <landing_v4 dir> <mutations log> <mutations rerun log>
"""
import json
import os
import subprocess
import sys

W, NEW, MUT, MUT_RERUN = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
WT = r'C:/Users/pgoff/Melange-wt/route-core'
env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', PYTHONIOENCODING='utf-8')
CHANGED = ['fec/tests/surfaces/test_staffer_contact_group.py', 'fec/tests/surfaces/test_staffer_left_out_staff.cjs', 'fec/tests/surfaces/test_staffer_office_covered_staff.py',
           'fec/tests/surfaces/test_staffer_prewarm.py', 'fec/tests/surfaces/test_staffer_unreachable_hint.py']


def read(path):
    with open(path, encoding='utf-8', errors='replace') as handle:
        return handle.read().rstrip('\n')


def git(*args):
    return subprocess.run(['git', '-C', WT, *args], capture_output=True, env=env).stdout.decode('utf-8', 'replace').rstrip('\n')


def rows(path):
    return {r['file']: r for r in json.load(open(path, encoding='utf-8'))}


tip = json.load(open(os.path.join(NEW, 'staffer_route_v4.summary.json'), encoding='utf-8'))['tip']
out = []
out += ['# The fix round on landing_v4 (2026-10-03): the verifier\'s findings, what changed, and the evidence.', '',
        '## 1. commits (git log 5d4a9bd0a..tip)', git('log', '--format=%h %s', '5d4a9bd0a..' + tip), '',
        '## the exact new sentences',
        '  page, left-out line, plural   : N of this office\'s current staff lack the payroll or staffer-roster coverage this model requires and were left out.',
        '  page, left-out line, singular : 1 of this office\'s current staff lacks the payroll or staffer-roster coverage this model requires and was left out.',
        '  office_without_work_records, when staff were left out or avoided : No Staffer route: none of the staff this search could use have dated employment at this office in the records this model uses.',
        '  office_without_work_records, when nobody was (unchanged)         : No Staffer route: none of this office\'s current staff have dated employment at this office in the records this model uses.',
        '', '## diffstat 5d4a9bd0a..tip', git('diff', '--stat', '5d4a9bd0a', tip), '']
old_log = os.path.join(W, 'logs', 'old_tests_on_tip.log')
if os.path.isfile(old_log):
    old = rows(os.path.join(W, 'old_tests_on_tip_run.json'))
    out += ['## 2. the intended string changes: the changed test files as they were at 5d4a9bd0a, run against the new tip\'s code',
            '# (a copy of the clean tip export with those five files from 5d4a9bd0a laid over it, GIT_DIR at the shared object store so nothing skips; scripts/old_tests_on_new_code.sh).',
            '# A test that fails here asserts a sentence or a count the fix round changed on purpose; the tests that pass are unchanged in meaning.', '']
    for rel, r in sorted(old.items()):
        out.append('%-72s passed %-3d failed %-3d errors %d skipped %d' % (rel, r['passed'], r['failed'], r['errors'], r['skipped']))
        seen = []
        for f in r['failures']:   # `node --test` lists each failure twice, once in the stream and once under "failing tests:"
            if 'failing tests:' not in f and f not in seen:
                seen.append(f)
        out += ['    ' + f for f in seen]
    out += ['', read(old_log), '']
base, tipr = rows(os.path.join(W, 'base_5d4a9bd0a_run.json')), rows(os.path.join(W, 'tip_v4_run.json'))
out += ['## 3. the changed test files, counts at 5d4a9bd0a and at the new tip (clean exports without .git, so tests that read a base commit skip in both)']
for rel in CHANGED:
    b, t = base.get(rel), tipr.get(rel)
    out.append('%-72s 5d4a9bd0a: passed %-3d skipped %-3d   tip: passed %-3d skipped %-3d' % (rel, b['passed'], b['skipped'], t['passed'], t['skipped']))
out += ['']
for title, path in (('## 4. mutation checks (scripts/mutations.py: one edit to production code in a scratch copy of the tip\'s fec/, then the named tests; CAUGHT means a test failed)', MUT),
                    ('## the one mutation whose first edit was malformed (a no-op) and was corrected, rerun alone', MUT_RERUN)):
    out += [title, read(path), '']
mem = os.path.join(W, 'memory_runs.jsonl')
if os.path.isfile(mem):
    out += ['## 5. peak memory of a router publish plus its prewarm (scripts/publish_memory.py; scripts/run_memory.sh)',
            '# One process per run, capped at 1000 MB. A synthetic world of people with payroll-shaped episodes; router R1 is built and prewarmed (work index I1); an equal router R2 is built while R1 serves',
            '# (phase 1), swapped in the way LiveService does (release of the replaced router where the tree has it), and its prewarm builds I2 (phase 2). The people index stage is left out. RSS sampled every 20 ms.',
            '# before = the 5d4a9bd0a export, after = the new tip\'s export. Peaks in MB of resident set; blocks = sys.getallocatedblocks() in millions at the phase-2 peak.', '']
    runs = [json.loads(line) for line in open(mem, encoding='utf-8') if line.strip()]
    out.append('%-7s %-7s %-10s %-9s %-10s %-9s %-9s %-9s %-10s %-9s %s' % ('label', 'people', 'R1+I1 MB', 'R2 built', 'swapped', 'peak ph1', 'peak ph2', 'end MB', 'blocks pk', 'gc_ms', 'peak_wset'))
    for r in runs:
        out.append('%-7s %-7d %-10d %-9d %-10d %-9d %-9d %-9d %-10.2f %-9s %d' % (r['label'], r['people'], r['rss_r1_i1_mb'], r['rss_r2_built_mb'], r['rss_swapped_mb'], r['peak_phase1_mb'], r['peak_phase2_mb'],
                                                                           r['rss_end_mb'], r['peak_blocks_phase2_m'], r['prewarm2'].get('gc_ms'), r['peak_wset_mb']))
    out += ['']
with open(os.path.join(NEW, 'proof', 'fix_round.txt'), 'w', encoding='utf-8', newline='\n') as handle:
    handle.write('\n'.join(out).rstrip('\n') + '\n')
print('wrote proof/fix_round.txt')
