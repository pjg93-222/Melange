"""Mutation checks for the v4.1 fix round: each mutation is one edit to production code in a scratch copy of the tip's tree; the named tests must fail with it (and they pass without it).

usage: python mutations.py <scratch tree root (a copy of the v4.1 tip export, with the 4 data files)> [name ...] [--check]
(--check only verifies that every edit's anchor occurs exactly once in the tree, and runs nothing)
The tree is restored after every mutation (the original bytes are kept in memory). GIT_DIR points at the shared object store (read-only), so the tests that read a base commit from git
run instead of skipping.
"""
import os
import subprocess
import sys
import time

root = os.path.abspath(sys.argv[1])
CHECK = '--check' in sys.argv
only = set(a for a in sys.argv[2:] if a != '--check')
GIT_DIR = r'C:/Users/pgoff/OneDrive/Desktop/Melange Systems/.git'
env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONUTF8': '1', 'GIT_DIR': GIT_DIR, 'GIT_OPTIONAL_LOCKS': '0'}
env.pop('MONEYBALL_ROOT', None)

T = 'fec/tests/surfaces/'
S = 'fec/surfaces/'
PY = lambda *args: [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--no-header', '--tb=line', *args]
PREWARM, REQUEST = T + 'test_staffer_prewarm.py', T + 'test_staffer_request_work_index.py'
OFFICE, HINT, LEFT = T + 'test_staffer_office_covered_staff.py', T + 'test_staffer_unreachable_hint.py', T + 'test_staffer_left_out_staff.cjs'
MUTATIONS = [
    # name, file, old, new, command (the tests that must fail)
    # ---- 1. the collection
    ('flag_never_set', S + 'staffer_live_service.py',
     "        with self._prewarm_lock:\n            self._router_replaced = True\n        try:\n            replaced.release_search_state()\n",
     "        try:\n            replaced.release_search_state()\n",
     PY(PREWARM, '-k', 'after_a_replacement or only_a_router or identity_rebuild_releases or collects_for_every_swap or replaced_router_is_gone')),
    ('collection_at_every_prewarm', S + 'staffer_live_service.py',
     "                    if replaced:\n                        # One full collection", "                    if True:\n                        # One full collection",
     PY(PREWARM, '-k', 'at_a_start_runs_no_collection')),
    ('flag_never_cleared', S + 'staffer_live_service.py',
     "                        replaced, self._router_replaced = self._router_replaced, False\n", "                        replaced = self._router_replaced\n",
     PY(PREWARM, '-k', 'and_a_later_one_runs_none or collects_for_every_swap')),
    ('flag_set_for_the_same_router', S + 'staffer_live_service.py',
     "        if replaced is None or replaced is current:\n            return\n        with self._prewarm_lock:",
     "        if replaced is None:\n            return\n        with self._prewarm_lock:",
     PY(PREWARM, '-k', 'only_a_router')),
    ('abandoned_prewarm_collects', S + 'staffer_live_service.py',
     "            checked = False\n            for name in self.PREWARM_STAGES:\n",
     "            checked = False\n            gc.collect()\n            for name in self.PREWARM_STAGES:\n",
     PY(PREWARM, '-k', 'abandoned_before_they_build or at_a_start_runs_no_collection')),
    # ---- 2. one index per request, a released router stores nothing
    ('no_scope_for_distinct', S + 'staffer_routing.py',
     "            with self._one_work_index():\n                return distinct_routes(self, origin, targets, options, progress)\n",
     "            return distinct_routes(self, origin, targets, options, progress)\n",
     PY(REQUEST, '-k', 'release_between_the_passes or request_on_a_released_router or route_many_opens')),
    ('no_scope_for_the_yen_loop', S + 'staffer_routing.py',
     "            with self._one_work_index():\n                return self._route_alternatives(origin, targets, options, progress)\n",
     "            return self._route_alternatives(origin, targets, options, progress)\n",
     PY(REQUEST, '-k', 'route_many_opens')),
    ('scope_never_closed', S + 'staffer_closeness_routes.py',
     "    finally:\n        _REQUEST_WORK.reset(token)\n", "    finally:\n        pass\n",
     PY(REQUEST, '-k', 'scope_is_per_request')),
    ('index_ignores_the_scope', S + 'staffer_closeness_routes.py',
     "            held = scope.indexes.get((self, key))\n            if held is not None:\n                return held\n",
     "            held = None\n", PY(REQUEST, '-k', 'release_between_the_passes or request_on_a_released_router')),
    ('release_does_not_mark_the_router', S + 'staffer_closeness_routes.py',
     "        self.released = True          # first: whatever stores after this sees it, and whatever stored before is cleared below\n", "",
     PY(REQUEST, PREWARM, '-k', 'released_router or in_flight or finishes_after_the_release or replaced_routers_build')),
    ('finished_build_put_back', S + 'staffer_closeness_routes.py',
     "                if error is None and not self.released:\n", "                if error is None:\n",
     PY(REQUEST, PREWARM, '-k', 'finishes_after_the_release or replaced_routers_build or swap_during_the_prewarm')),
    ('released_router_stores_hop_rows', S + 'staffer_closeness_routes.py',
     "            if self.released:\n                # The router has been replaced: nothing is stored on it. A request with a scope shares one cache among its passes.\n                return self._unstored_row_cache(key, index)\n", "",
     PY(REQUEST, '-k', 'request_on_a_released_router or every_kind_of_request')),
    ('unstored_rows_not_shared_by_the_passes', S + 'staffer_closeness_routes.py',
     "        scope = _REQUEST_WORK.get()\n        if scope is None:\n            return _RowCache(index)\n        cache = scope.row_caches.get((self, key))",
     "        scope = None\n        if scope is None:\n            return _RowCache(index)\n        cache = scope.row_caches.get((self, key))",
     PY(REQUEST, '-k', 'builds_one_index_for_all_its_passes')),
    ('release_search_state_skips_a_fresh_router', S + 'staffer_routing.py',
     "        self.closeness().release()\n        self.forget_contact_groups()\n",
     "        routes = getattr(self, 'closeness_routes', None)\n        if routes is not None:\n            routes.release()\n        self.forget_contact_groups()\n",
     PY(REQUEST, '-k', 'every_kind_of_request or builds_one_index_for_all_its_passes')),
    # ---- 4. the basis of the left-out count
    ('basis_always_payroll_or_roster', S + 'staffer_closeness_routes.py',
     "uncovered_basis='roster' if options['work_sources'] == 'directory' else 'payroll_or_roster')", "uncovered_basis='payroll_or_roster')",
     PY(OFFICE, '-k', 'basis or directory')),
    ('basis_always_roster', S + 'staffer_closeness_routes.py',
     "uncovered_basis='roster' if options['work_sources'] == 'directory' else 'payroll_or_roster')", "uncovered_basis='roster')",
     PY(OFFICE, '-k', 'basis or directory')),
    ('distinct_loop_drops_the_basis', S + 'staffer_distinct_routes.py',
     "('uncovered_staff_count', 'uncovered_staff_ids', 'uncovered_basis')", "('uncovered_staff_count', 'uncovered_staff_ids')",
     PY(OFFICE, '-k', 'basis or directory')),
    ('page_ignores_the_basis', S + 'staffer_live/staffer-route.js',
     "data.uncovered_basis==='roster'?'staffer-roster':'payroll or staffer-roster'", "'payroll or staffer-roster'",
     ['node', '--test', LEFT]),
    # ---- 5. the explanation
    ('explanation_not_the_message', S + 'staffer_live_service.py',
     "            explanation = (result['message'] if reasoned else\n", "            explanation = ('' if reasoned else\n",
     PY(HINT, '-k', 'explanation')),
    ('note_added_after_a_reasoned_explanation', S + 'staffer_live_service.py',
     "        if not reasoned and result.get('alternative_strategy') in ('distinct', 'independent'):", "        if result.get('alternative_strategy') in ('distinct', 'independent'):",
     PY(HINT, '-k', 'explanation')),
    ('reason_without_message_still_reasoned', S + 'staffer_live_service.py',
     "bool(result.get('unreachable_reason') and result.get('message'))", "bool(result.get('unreachable_reason'))",
     PY(HINT, '-k', 'no_message')),
]


def run(cmd):
    started = time.time()
    done = subprocess.run(cmd, cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
    text = done.stdout + '\n' + done.stderr
    lines = [l for l in text.splitlines() if l.strip()]
    return done.returncode, round(time.time() - started, 1), (lines[-1] if lines else '')[:160]


caught = 0
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
    if CHECK:
        print('%-52s anchor applies once' % name)
        continue
    mutated = lf.replace(old, new)
    try:
        open(path, 'wb').write((mutated.replace('\n', '\r\n') if crlf else mutated).encode('utf-8'))
        code, seconds, last = run(command)
    finally:
        open(path, 'wb').write(original)
    # pytest and node both exit 1 when a test fails; 5 is pytest's "no tests collected" (a -k that matches nothing), which proves nothing
    verdict = 'CAUGHT ' if code == 1 else 'MISSED ' if code == 0 else 'NO TEST RAN / ERROR (rc=%d) ' % code
    caught += code == 1
    print('%-52s %s in %5.1fs  rc=%d  %s' % (name, verdict, seconds, code, last), flush=True)
if not CHECK:
    print('%d of %d mutations caught' % (caught, len([m for m in MUTATIONS if not only or m[0] in only])))
