"""Negative control: the render harness must FAIL on a page with a known defect.

A check that has never been seen to fail is not evidence. Each mutant below
injects one specific defect; the harness must reject every one of them, and must
still accept the unmutated page.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
PAGE = HERE / 'mentat-pocket.html'
HARNESS = HERE / 'render_harness.js'

MUTANTS = [
    ('total measure returns the record count instead of the amount',
     "{ id:'total', label:'Total giving',\n      value:function(a){ return a; }",
     "{ id:'total', label:'Total giving',\n      value:function(a, r){ return r; }"),
    ('money abbreviated with the wrong divisor (M means hundred-thousands)',
     "if (size >= 999500) return sign + '$' + (size / 1000000).toFixed(1) + 'M';",
     "if (size >= 999500) return sign + '$' + (size / 100000).toFixed(1) + 'M';"),
    ('an empty card draws a blank box instead of saying so',
     "line.textContent = 'No included receipts for ' + scopeName(industry) + ' in '\n      + cycleName(industry, state.cycle) + '.';",
     "line.textContent = '';"),
    ('the company count in the tile is off by one',
     "+ (state.company < 0 ? plural(industry.co.length, 'company', 'companies') : '1 company');",
     "+ (state.company < 0 ? plural(industry.co.length + 1, 'company', 'companies') : '1 company');"),
    ('long recipient names wrapped to the full box, with no margin for font error',
     'var NAME_WIDTH = W * 0.9;',
     'var NAME_WIDTH = W - 4;'),
    ('the value gutter is too narrow for a long value label',
     'var GUTTER = 84;',
     'var GUTTER = 10;'),
    ('the average measure is abbreviated like a large total',
     "{ id:'average', label:'Average receipt',\n      value:function(a, r){ return r ? a / r : 0; }, format:exactDollars, exact:exactDollars,",
     "{ id:'average', label:'Average receipt',\n      value:function(a, r){ return r ? a / r : 0; }, format:dollars, exact:exactDollars,"),
]


def run(page_path):
    environment = dict(os.environ, POCKET_PAGE=str(page_path))
    result = subprocess.run(['node', str(HARNESS)], capture_output=True, text=True,
                            env=environment, cwd=str(HERE))
    return result.returncode, (result.stdout + result.stderr)


def main():
    source = PAGE.read_text(encoding='utf-8')
    code, output = run(PAGE)
    print('control (unmutated page): exit={} {}'.format(
        code, 'PASSED' if code == 0 else 'FAILED -- ' + output[-300:]))
    failures = 0
    if code != 0:
        failures += 1

    for label, needle, replacement in MUTANTS:
        if needle not in source:
            print('  SETUP FAIL  mutant anchor not found: ' + label)
            failures += 1
            continue
        mutated = source.replace(needle, replacement, 1)
        with tempfile.NamedTemporaryFile('w', suffix='.html', delete=False,
                                         encoding='utf-8', dir=str(HERE)) as handle:
            handle.write(mutated)
            target = Path(handle.name)
        try:
            code, output = run(target)
            caught = code != 0
            first = next((line.strip() for line in output.splitlines()
                          if line.strip().startswith('- ')), '(no detail)')
            print('  {}  {}\n           {}'.format(
                'CAUGHT' if caught else 'MISSED', label, first if caught else 'harness passed a broken page'))
            if not caught:
                failures += 1
        finally:
            target.unlink(missing_ok=True)

    print('\n' + ('NEGATIVE CONTROL PASSED -- the harness rejects every injected defect'
                  if not failures else '{} NEGATIVE-CONTROL FAILURE(S)'.format(failures)))
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
