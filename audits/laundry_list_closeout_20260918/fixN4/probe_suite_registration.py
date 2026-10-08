# -*- coding: utf-8 -*-
"""Lane N4: the new suites really are runnable BY THE RUNNER. READ-ONLY.

fec/tests/run_tests.py is the only thing that decides whether a suite exists, and its own
comment says a suite no runner invokes is indistinguishable from a deleted one. Two things
have to hold: the recursive discovery must find the file under a UNIQUE basename (a duplicate
basename is a fatal RuntimeError for the whole harness), and _suite_verdict must be able to
read the suite's output (an unrecognised verdict is a failure by design).

Both are checked here without running the 50-suite kernel: the discovery loop is replayed and
_suite_verdict is compiled out of run_tests.py by AST, the same technique
test_bill_collision_guards.py uses on the producer.
"""
import ast
import os
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
WORKTREE = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
FEC = os.path.join(WORKTREE, 'fec')
RUNNER = os.path.join(FEC, 'tests', 'run_tests.py')
P = print

# ---------------------------------------------------------------- discovery
paths = {}
duplicates = []
for directory, subdirectories, files in os.walk(os.path.join(FEC, 'tests')):
    subdirectories.sort()
    for name in sorted(files):
        if not (name.startswith('test_') and name.endswith('.py')):
            continue
        stem = os.path.splitext(name)[0]
        if stem in paths:
            duplicates.append((stem, paths[stem], os.path.join(directory, name)))
        paths[stem] = os.path.join(directory, name)
P('discovered test suites: %d' % len(paths))
P('duplicate basenames (fatal for the whole harness): %s' % (duplicates or 'NONE'))
assert not duplicates
for stem in ('test_sponsor_column', 'test_sponsor_column_producer_wiring'):
    P('%-40s discovered: %-5s  %s' % (stem, stem in paths, paths.get(stem, '(absent)')))

# ---------------------------------------------------------------- registration
source = open(RUNNER, encoding='utf-8').read()
tree = ast.parse(source)
lanes = {}
for node in tree.body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) \
            and node.targets[0].id.startswith('_LANE_'):
        try:
            lanes[node.targets[0].id] = ast.literal_eval(node.value)
        except ValueError:
            continue
registered = {name for lane in lanes.values() for name in lane}
P('')
P('lane tuples parsed: %s' % sorted(lanes))
P('registered suite names: %d' % len(registered))
for stem in ('test_sponsor_column', 'test_sponsor_column_producer_wiring'):
    where = [lane for lane, names in lanes.items() if stem in names]
    P('%-40s registered in: %s' % (stem, where or 'NOT REGISTERED'))
assert 'test_sponsor_column' in lanes['_LANE_LEGISLATION']
P('')
P('every registered name resolves to a file (an absent one is counted as a FAILURE by the')
P('runner, never skipped): %s'
  % sorted(name for name in registered if name not in paths) or 'all resolve')
missing = sorted(name for name in registered if name not in paths)
P('registered-but-absent: %s' % (missing or 'NONE'))
assert 'test_sponsor_column_producer_wiring' not in registered, (
    'the wiring suite ships inside the LIVE patch, so registering it here would make the '
    'kernel report a missing suite until that patch lands')

# ---------------------------------------------------------------- verdict parsing
verdict_node = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == '_suite_verdict')
namespace = {'_re': re}
exec(compile(ast.Module(body=[verdict_node], type_ignores=[]), RUNNER, 'exec'), namespace)
suite_verdict = namespace['_suite_verdict']

run = subprocess.run([sys.executable, paths['test_sponsor_column']],
                     capture_output=True, text=True, encoding='utf-8', errors='replace',
                     env={k: v for k, v in os.environ.items() if k != 'MONEYBALL_ROOT'})
output = (run.stdout or '') + '\n' + (run.stderr or '')
verdict = suite_verdict(output)
P('')
P('test_sponsor_column: returncode=%d  _suite_verdict=%s' % (run.returncode, verdict))
P('last line: %r' % (output.strip().splitlines()[-1],))
P("runner's own pass condition (returncode==0 and verdict is not None and failed==0 and "
  'passed>0): %s'
  % (run.returncode == 0 and verdict is not None and verdict[1] == 0 and verdict[0] > 0))
assert run.returncode == 0 and verdict is not None and verdict[1] == 0 and verdict[0] > 0
P('')
P('VERDICT: test_sponsor_column is discovered, uniquely named, registered in _LANE_LEGISLATION,')
P('         and the runner can read its verdict line. MONEYBALL_ROOT was unset for the run.')
