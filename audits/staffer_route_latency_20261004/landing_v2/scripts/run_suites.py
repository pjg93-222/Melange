"""Run the staffer suites file by file under one root and record per-file counts.

usage: python run_suites.py <root> <out.json> [--only substring ...] [--skip substring ...]
Each pytest file runs in its own process (cwd=root, no cache provider); a file pytest collects no tests from is run as a
script ('N passed, M failed' on its last line); each .cjs file runs under `node --test`.
"""
import glob
import json
import os
import re
import subprocess
import sys
import time

root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
args = sys.argv[3:]
only = [a for i, a in enumerate(args) if i and args[i - 1] == '--only']
skip = [a for i, a in enumerate(args) if i and args[i - 1] == '--skip']

py = (sorted(glob.glob(os.path.join(root, 'fec/surfaces/test_staffer_*.py')))
      + sorted(glob.glob(os.path.join(root, 'fec/tests/surfaces/test_staffer_*.py')))
      + [os.path.join(root, 'fec/tests/staffer_network/test_closeness_math.py'),
         os.path.join(root, 'fec/tests/staffer_network/test_relationship_uncertainty.py'),
         os.path.join(root, 'fec/surfaces/test_repin_staffer_live.py')])  # extra, informational: known baseline red
cjs = sorted(glob.glob(os.path.join(root, 'fec/tests/surfaces/test_*.cjs')))
files = [(f, 'py') for f in py] + [(f, 'cjs') for f in cjs]
if only:
    files = [(f, k) for f, k in files if any(o in f for o in only)]
if skip:
    files = [(f, k) for f, k in files if not any(s in f for s in skip)]

NL = chr(10)
results = []
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
env.pop('MONEYBALL_ROOT', None)


def run(cmd):
    try:
        proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
        return proc.stdout + NL + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', -9


for path, kind in files:
    rel = os.path.relpath(path, root).replace(chr(92), '/')
    started = time.time()
    row = {'file': rel, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'failures': [], 'mode': kind}
    if kind == 'py':
        text, code = run([sys.executable, '-m', 'pytest', rel, '-q', '-p', 'no:cacheprovider', '--no-header', '-rfE', '--tb=line'])
        tail = [l for l in text.splitlines() if re.search(r'\d+ (passed|failed|error|skipped|deselected)|no tests ran', l)]
        summary = tail[-1] if tail else ''
        for key, pattern in (('passed', r'(\d+) passed'), ('failed', r'(\d+) failed'), ('errors', r'(\d+) errors?'), ('skipped', r'(\d+) skipped')):
            m = re.search(pattern, summary)
            row[key] = int(m.group(1)) if m else 0
        row['summary'] = summary.strip()
        row['failures'] = [l.strip()[:300] for l in text.splitlines() if l.startswith(('FAILED ', 'ERROR '))]
        if code == 5:
            text, code = run([sys.executable, rel])
            found = re.findall(r'(\d+) passed, (\d+) failed', text)
            row.update(mode='script', passed=int(found[-1][0]) if found else 0, failed=int(found[-1][1]) if found else 0)
            row['summary'] = ('%s passed, %s failed' % found[-1]) if found else text.strip().splitlines()[-1][:200]
            row['failures'] = [l.strip()[:300] for l in text.splitlines() if l.strip().startswith(('FAIL', 'not ok', 'Traceback'))][:10]
    else:
        text, code = run(['node', '--test', rel])
        for key, pattern in (('passed', r'(?:# |ℹ )pass (\d+)'), ('failed', r'(?:# |ℹ )fail (\d+)'), ('skipped', r'(?:# |ℹ )skipped (\d+)')):
            m = re.search(pattern.replace('\\u2139', chr(0x2139)), text)
            row[key] = int(m.group(1)) if m else 0
        row['failures'] = [l.strip()[:300] for l in text.splitlines() if l.lstrip().startswith(('not ok', chr(0x2716)))]
    row['rc'], row['seconds'] = code, round(time.time() - started, 1)
    results.append(row)
    print('%-72s rc=%-3s %6.1fs  %-6s pass %-4d fail %-3d err %-2d skip %-2d' % (rel, code, row['seconds'], row['mode'], row['passed'], row['failed'], row['errors'], row['skipped']), flush=True)
    with open(out, 'w', encoding='utf-8') as handle:
        json.dump(results, handle, indent=1)

totals = {k: sum(r[k] for r in results) for k in ('passed', 'failed', 'errors', 'skipped')}
print('TOTAL', totals, 'files', len(results), flush=True)
