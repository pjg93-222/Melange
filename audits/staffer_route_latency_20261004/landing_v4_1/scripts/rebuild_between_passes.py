"""The re-check's part 2 (stress_release.py), on a router that has never been released: a release lands between the passes of a distinct / independent request (and inside a ranked or single one).

stress_release.py runs this scenario on the router its part 1 has been releasing for 40 s. On v4.1 that router is released for good (the `released` flag), so a request on it builds its own index (one build for
the whole request, one index object for all its passes) and the "builds during the request" column no longer says what the release between the passes cost. This script uses a fresh warm router per strategy, so the
column is the cost of the release itself: on v4 the next pass builds the whole work index again, on v4.1 nothing is built. cwd = an export of the tree to test.
"""
import json
import os
import sys
import threading

sys.path.insert(0, os.getcwd())
from fec.surfaces import staffer_closeness_routes as cr
from fec.surfaces import staffer_work_sources as ws
from fec.surfaces.test_staffer_closeness_bidirectional import roster, synthetic_router

TIMING = {'elapsed_ms', 'search_elapsed_ms', 'expanded', 'neighbor_checks', 'pairs_scored', 'cache_hit', 'response_elapsed_ms'}


def strip(value):
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if k not in TIMING}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def canon(answer):
    return json.dumps(strip(answer), sort_keys=True, default=str)


real_build, real_index = ws.build_index, cr.ClosenessRoutes.index
builds, seen = [0], threading.local()


def counting_build(router, options):
    builds[0] += 1
    return real_build(router, options)


def tracking_index(self, options):
    found = real_index(self, options)
    if getattr(seen, 'ids', None) is not None:
        seen.ids.append(id(found))
    return found


ws.build_index = counting_build
cr.ClosenessRoutes.index = tracking_index
SEED, PEOPLE, OFFICES = 23, 1500, 36
twin, ids, offices = synthetic_router(SEED, people=PEOPLE, offices=OFFICES)
import random
rng = random.Random(5)
offset = iter(range(1, 10 ** 6))


def ask(router, request):
    origin, targets, options = request
    return router.route_many(origin, list(targets), {**options, 'offset': next(offset)})


def find_request(kind):
    for _ in range(300):
        origin = rng.choice(ids)
        office = rng.choice(offices)
        staff = [p for p in roster(twin, office) if p != origin]
        if not staff:
            continue
        options = {'objective': 'work_time', '_target_office': office}
        if kind in ('distinct', 'independent', 'ranked'):
            options.update(route_count=3, alternative_strategy=kind)
        request = (origin, tuple(staff), options)
        answer = ask(twin, request)
        if answer['status'] == 'found' and (kind in ('single', 'ranked') or answer['routes_returned'] >= 2):
            return request
    raise SystemExit('no request for ' + kind)


print('part 2 (fresh router per strategy): one release inside the request, after its first search ran')
for kind in ('distinct', 'independent', 'ranked', 'single'):
    request = find_request(kind)
    expected = canon(ask(twin, request))
    live, _, _ = synthetic_router(SEED, people=PEOPLE, offices=OFFICES)
    live.closeness().index(live._options({'objective': 'work_time'}))           # warm: the table holds the index
    fired, real_full = [], cr._full_evidence

    def releasing_full(*args, **kwargs):
        if not fired:
            fired.append(1)
            live.release_search_state()
        return real_full(*args, **kwargs)
    cr._full_evidence = releasing_full
    builds[0] = 0
    seen.ids = []
    try:
        answer = ask(live, request)
    finally:
        cr._full_evidence = real_full
        used, seen.ids = seen.ids, None
    print('  %-11s released=%s  index fetches=%d  distinct index objects=%d  builds during the request=%d  same answer=%s  routes_returned=%s' % (
        kind, bool(fired), len(used), len(set(used)), builds[0], canon(answer) == expected, answer.get('routes_returned')))
