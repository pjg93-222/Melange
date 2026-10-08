"""Run the tests that mention staffer_live but are not named test_staffer_* (so run_suites.py does not reach them), file by file under one root.

usage: python run_extra.py <root> <out.json>
One process per file (cwd=root, no cache provider); a file pytest collects no tests from is run as a script ('N passed, M failed' or its own ok/FAIL lines).
"""
import json
import os
import re
import subprocess
import sys
import time

root, out = os.path.abspath(sys.argv[1]), sys.argv[2]
FILES = ['fec/tests/surfaces/test_clean_workspace_loading.py', 'fec/tests/surfaces/test_combined_staffer_section.py', 'fec/tests/surfaces/test_edge_startup.py',
         'fec/tests/surfaces/test_make_staffer_network_html.py', 'fec/tests/surfaces/test_melange_dashboard.py', 'fec/tests/surfaces/test_moneyball_desktop.py']
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1'}
env.pop('MONEYBALL_ROOT', None)
NL = chr(10)


def run(cmd):
    try:
        proc = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=3600)
        return proc.stdout + NL + proc.stderr, proc.returncode
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', -9


results = []
for rel in FILES:
    started = time.time()
    row = {'file': rel, 'passed': 0, 'failed': 0, 'errors': 0, 'skipped': 0, 'failures': [], 'mode': 'py'}
    if not os.path.isfile(os.path.join(root, rel)):
        row.update(mode='absent')
    else:
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
            ok_lines = len([l for l in text.splitlines() if l.startswith(('PASS', 'ok '))])
            bad_lines = [l.strip()[:300] for l in text.splitlines() if l.strip().startswith(('FAIL', 'not ok', 'Traceback'))]
            row.update(mode='script', passed=int(found[-1][0]) if found else ok_lines, failed=int(found[-1][1]) if found else len(bad_lines))
            row['summary'] = ('%s passed, %s failed' % found[-1]) if found else 'script: %d ok lines, %d failure lines, rc=%s' % (ok_lines, len(bad_lines), code)
            row['failures'] = bad_lines[:10]
    row['rc'], row['seconds'] = code if row['mode'] != 'absent' else None, round(time.time() - started, 1)
    results.append(row)
    print('%-62s rc=%-4s %6.1fs  %-6s pass %-4d fail %-3d err %-2d skip %-2d  %s' % (rel, row['rc'], row['seconds'], row['mode'], row['passed'], row['failed'], row['errors'], row['skipped'], row.get('summary', '')[:70]), flush=True)
    with open(out, 'w', encoding='utf-8') as handle:
        json.dump(results, handle, indent=1)
totals = {k: sum(r[k] for r in results) for k in ('passed', 'failed', 'errors', 'skipped')}
print('TOTAL', totals, 'files', len(results), flush=True)
