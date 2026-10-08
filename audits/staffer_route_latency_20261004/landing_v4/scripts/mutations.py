"""Mutation checks for the fix round: each mutation is one edit to production code in a scratch copy of the tree; the named tests
must fail with it and pass without it.

usage: python mutations.py <scratch tree root (a copy of the worktree's fec/)> [name ...]
The tree is restored after every mutation (the original bytes are kept in memory). GIT_DIR points at the shared object store
(read-only), so the tests that read the base commit from git run instead of skipping.
"""
import os
import subprocess
import sys
import time

root = os.path.abspath(sys.argv[1])
only = set(sys.argv[2:])
GIT_DIR = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/.git'
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1', 'GIT_DIR': GIT_DIR, 'GIT_OPTIONAL_LOCKS': '0'}
env.pop('MONEYBALL_ROOT', None)

T = 'fec/tests/surfaces/'
S = 'fec/surfaces/'
PY = lambda *args: [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--no-header', '--tb=line', *args]
MUTATIONS = [
    # name, file, old, new, command, what must fail
    ('page_old_wording', S + 'staffer_live/staffer-route.js',
     "${left===1?'lacks':'lack'} the payroll or staffer-roster coverage this model requires", "${left===1?'has':'have'} no work records this model uses",
     ['node', '--test', T + 'test_staffer_left_out_staff.cjs']),
    ('explain_ignores_left_out', S + 'staffer_closeness_routes.py',
     "    if staff_left_out:\n        message = SEARCHED_STAFF_MESSAGES.get(reason, message)\n", "",
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('route_forgets_uncovered', S + 'staffer_closeness_routes.py',
     "staff_left_out = bool(uncovered or options.get('_avoided_targets'))", "staff_left_out = bool(options.get('_avoided_targets'))",
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('route_forgets_avoided', S + 'staffer_closeness_routes.py',
     "staff_left_out = bool(uncovered or options.get('_avoided_targets'))", "staff_left_out = bool(uncovered)",
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('route_many_records_nothing', S + 'staffer_routing.py',
     "if options['objective'] == 'work_time' and options['_target_office'] and len(targets) < len(named):", "if False:",
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('route_many_records_every_avoid', S + 'staffer_routing.py',
     "if options['objective'] == 'work_time' and options['_target_office'] and len(targets) < len(named):",
     "if options['objective'] == 'work_time' and options['_target_office'] and options['avoid_people']:",
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('options_drop_avoided_targets', S + 'staffer_routing.py',
     '                    "_avoided_targets": ()}', '                    }',
     PY(T + 'test_staffer_office_covered_staff.py', '-x')),
    ('pairs_priced_twice', S + 'staffer_closeness_routes.py',
     "raw = index.pair_row(*((person, other) if person < other else (other, person)))",
     "raw = index.pair_row(*((person, other) if person < other else (other, person))); index.pair_row(*((person, other) if person < other else (other, person)))",
     PY(T + 'test_staffer_unreachable_hint.py', '-x', '-k', 'checks_build or extra_pair or not_more')),
    ('service_keeps_name_index', S + 'staffer_live_service.py',
     "                self.router.forget_contact_groups()\n", "",
     PY(T + 'test_staffer_contact_group.py', '-x')),
    ('no_release_at_refresh', S + 'staffer_live_service.py',
     "            replaced, retired = retired[0], None\n            self._release_replaced_router(replaced, router)\n",
     "            replaced, retired = retired[0], None\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'publishing_a_new_router or replaced_router_is_gone or release_frees')),
    ('no_release_at_identity_rebuild', S + 'staffer_live_service.py',
     "                self._release_replaced_router(replaced, self.router)\n", "",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'identity_rebuild_releases')),
    ('no_collection', S + 'staffer_live_service.py',
     "                    gc.collect()\n", "                    pass\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'replaced_router_is_gone or one_collection or release_frees')),
    ('collection_per_stage', S + 'staffer_live_service.py',
     "                    collected, mark = True, time.perf_counter()\n", "                    collected, mark = False, time.perf_counter()\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'one_collection')),
    ('collection_when_abandoned', S + 'staffer_live_service.py',
     "            collected = False\n            for name in self.PREWARM_STAGES:\n",
     "            collected = False\n            gc.collect()\n            for name in self.PREWARM_STAGES:\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'one_collection')),
    ('release_keeps_row_caches', S + 'staffer_closeness_routes.py',
     "        with self.row_lock:\n            self.row_caches.clear()\n", "        pass\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'publishing_a_new_router')),
    ('release_keeps_indexes', S + 'staffer_closeness_routes.py',
     "        with self.index_lock:\n            self.indexes.clear()\n", "        pass\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'publishing_a_new_router')),
    ('release_keeps_name_index', S + 'staffer_routing.py',
     "            routes.release()\n        self.forget_contact_groups()\n", "            routes.release()\n",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'publishing_a_new_router')),
    ('route_asks_for_its_index_twice_again', S + 'staffer_closeness_routes.py',
     "        context = getattr(router, 'member_context', None) or MemberContext()\n        excluded_contexts",
     "        index = self.index(options)\n        context = getattr(router, 'member_context', None) or MemberContext()\n        excluded_contexts",
     PY(T + 'test_staffer_prewarm.py', '-x', '-k', 'takes_its_index_once')),
]


def run(cmd):
    started = time.time()
    done = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
    text = done.stdout + '\n' + done.stderr
    lines = [l for l in text.splitlines() if l.strip()]
    return done.returncode, round(time.time() - started, 1), (lines[-1] if lines else '')[:160]


for name, rel, old, new, command in MUTATIONS:
    if only and name not in only:
        continue
    path = os.path.join(root, *rel.split('/'))
    original = open(path, 'rb').read()
    text = original.decode('utf-8')
    crlf = '\r\n' in text
    lf = text.replace('\r\n', '\n')
    if lf.count(old) != 1:
        print('%-52s EDIT DID NOT APPLY ONCE (%d)' % (name, lf.count(old)), flush=True)
        continue
    mutated = lf.replace(old, new)
    try:
        open(path, 'wb').write((mutated.replace('\n', '\r\n') if crlf else mutated).encode('utf-8'))
        code, seconds, last = run(command)
    finally:
        open(path, 'wb').write(original)
    print('%-52s %s in %5.1fs  rc=%d  %s' % (name, 'CAUGHT ' if code else 'MISSED ', seconds, code, last), flush=True)
