"""A: release safety of AdvocacyRouter.release_search_state / ClosenessRoutes.release, on the 79ef9f1b7 export (cwd).

Part 1  concurrent stress: worker threads run every strategy (single, office, distinct, independent, ranked, avoid_people) on one
        router while a releaser empties its work state every 0-15 ms and a forgetter drops its name index; every answer is compared
        with the same request on an untouched twin router.
Part 2  deterministic: a release lands between the passes of a distinct / independent request (and inside a ranked one).
Part 3  service: the old router's prewarm build is in flight, a request waits on it, a new router is published (release of the old
        one); then a request on the old router is still running when the new prewarm collects.
"""
import gc, json, os, random, sys, threading, time, traceback, weakref
from collections import Counter, defaultdict

sys.path.insert(0, os.getcwd())
from fec.surfaces import staffer_work_sources as ws
from fec.surfaces import staffer_closeness_routes as cr
from fec.surfaces.test_staffer_closeness_bidirectional import synthetic_router, roster

TIMING = {'elapsed_ms', 'search_elapsed_ms', 'expanded', 'neighbor_checks', 'pairs_scored', 'cache_hit', 'response_elapsed_ms'}


def strip(value):
    if isinstance(value, dict):
        return {k: strip(v) for k, v in value.items() if k not in TIMING}
    if isinstance(value, list):
        return [strip(v) for v in value]
    return value


def canon(answer):
    return json.dumps(strip(answer), sort_keys=True, default=str)


real_build = ws.build_index
builds = Counter()
build_lock = threading.Lock()


def counting_build(router, options):
    with build_lock:
        builds['live' if router is live else 'twin' if router is twin else 'other'] += 1
    return real_build(router, options)


ws.build_index = counting_build
seen = threading.local()
real_index = cr.ClosenessRoutes.index


def tracking_index(self, options):
    index = real_index(self, options)
    ids = getattr(seen, 'ids', None)
    if ids is not None:
        ids.append(id(index))
    return index


cr.ClosenessRoutes.index = tracking_index

SEED, PEOPLE, OFFICES = 23, 1500, 36
twin, ids, offices = synthetic_router(SEED, people=PEOPLE, offices=OFFICES)
live, _, _ = synthetic_router(SEED, people=PEOPLE, offices=OFFICES)
rng = random.Random(5)
requests = []
for k in range(36):
    origin = rng.choice(ids)
    if k % 2:
        office = rng.choice(offices)
        staff = [p for p in roster(twin, office) if p != origin]
        if not staff:
            continue
        targets, base = staff, {'objective': 'work_time', '_target_office': office}
    else:
        target = rng.choice([p for p in ids if p != origin])
        targets, base = [target], {'objective': 'work_time'}
    kind = ['single', 'distinct', 'independent', 'ranked', 'avoid'][k % 5]
    options = dict(base)
    if kind in ('distinct', 'independent', 'ranked'):
        options.update(route_count=3, alternative_strategy=kind)
    if kind == 'avoid':
        pool = [p for p in (targets if len(targets) > 1 else ids) if p != origin and p not in targets[:1]]
        options.update(route_count=2, alternative_strategy='distinct', avoid_people=tuple(rng.sample(pool, min(2, len(pool)))))
    requests.append((kind, origin, tuple(targets), options))


def ask(router, request, offset):
    kind, origin, targets, options = request
    return router.route_many(origin, list(targets), {**options, 'offset': offset})


offset_counter = iter(range(1, 10 ** 7))
offset_lock = threading.Lock()


def next_offset():
    with offset_lock:
        return next(offset_counter)


baseline = [canon(ask(twin, r, next_offset())) for r in requests]
statuses = Counter(json.loads(b)['status'] for b in baseline)
print('part 1: %d requests %s; statuses %s; baseline builds %s' % (len(requests), dict(Counter(r[0] for r in requests)), dict(statuses), dict(builds)))

# ----------------------------------------------------------------------------------------------- part 1
stop = threading.Event()
errors, mismatches, done = [], [], Counter()
mid_request_rebuilds = Counter()
releases = Counter()


def worker(seed):
    local = random.Random(seed)
    while not stop.is_set():
        i = local.randrange(len(requests))
        seen.ids = []
        try:
            answer = ask(live, requests[i], next_offset())
        except Exception:
            errors.append(traceback.format_exc())
            continue
        finally:
            used = seen.ids
            seen.ids = None
        if len(set(used)) > 1:
            mid_request_rebuilds[requests[i][0]] += 1
        if canon(answer) != baseline[i]:
            mismatches.append((i, requests[i][0]))
        done[requests[i][0]] += 1


def releaser():
    local = random.Random(99)
    while not stop.is_set():
        time.sleep(local.uniform(0, .015))
        try:
            live.release_search_state()
            releases['release'] += 1
            if local.random() < .3:
                live.forget_contact_groups()
                releases['forget'] += 1
        except Exception:
            errors.append(traceback.format_exc())


builds.clear()
threads = [threading.Thread(target=worker, args=(s,)) for s in range(6)] + [threading.Thread(target=releaser)]
for t in threads:
    t.start()
time.sleep(float(os.environ.get('STRESS_SECONDS', '40')))
stop.set()
for t in threads:
    t.join(120)
print('part 1: requests %d %s; releases %s; index builds on the stressed router %d; errors %d; mismatches %d' % (
    sum(done.values()), dict(done), dict(releases), builds['live'], len(errors), len(mismatches)))
print('part 1: requests that used more than one index object (a rebuild between their own route() calls): %s' % dict(mid_request_rebuilds))
if errors:
    print(errors[0])
if mismatches:
    print('first mismatches', mismatches[:5])

# ----------------------------------------------------------------------------------------------- part 2
print('part 2: one release inside the first pass of the request (after its search ran), for each strategy')
real_full = cr._full_evidence
for kind in ('distinct', 'independent', 'ranked', 'single'):
    request = next(r for r in requests if r[0] == kind and json.loads(baseline[requests.index(r)])['status'] == 'found')
    for target_router in (twin, live):
        target_router.closeness().index(target_router._options({'objective': 'work_time'}))   # warm
    expected = canon(ask(twin, request, next_offset()))
    fired = []

    def releasing_full(*args, **kwargs):
        if not fired:
            fired.append(1)
            live.release_search_state()
        return real_full(*args, **kwargs)
    cr._full_evidence = releasing_full
    before = builds['live']
    seen.ids = []
    try:
        answer = ask(live, request, next_offset())
    finally:
        cr._full_evidence = real_full
    used, seen.ids = seen.ids, None
    print('  %-11s released=%s  index fetches=%d  distinct index objects=%d  builds during the request=%d  same answer=%s  routes_returned=%s' % (
        kind, bool(fired), len(used), len(set(used)), builds['live'] - before, canon(answer) == expected, answer.get('routes_returned')))

# ----------------------------------------------------------------------------------------------- part 3
print('part 3: service, in-flight prewarm build on the old router, a waiting request, a publish, and the collection')
from fec.surfaces import staffer_live_service as live_mod
from fec.tests.surfaces.test_staffer_route_latency import routed_service
from fec.tests.surfaces.test_staffer_prewarm import DEFAULT_KEY


class Gate:
    def __init__(self):
        self.started, self.release, self.calls = threading.Event(), threading.Event(), 0

    def __call__(self, router, options):
        self.calls += 1
        self.started.set()
        assert self.release.wait(30)
        return counting_build(router, options)


def settle():
    for t in [t for t in threading.enumerate() if t.name == 'staffer-prewarm']:
        t.join(30)


REQ = ('person:gordon', 'person:other-gordon')
reference = routed_service()
expected = canon(reference.route(*REQ, {'objective': 'work_time', 'limit': 500}))

for variant in ('a', 'b', 'c'):
    # a: the test holds the old router (as test_a_router_swap_during_the_prewarm_discards_it does): its table after the release
    # b: nothing holds the old router but a request on it that is still running when the new prewarm collects
    # c: nothing holds the old router once its request is done (the control for b)
    gate = Gate()
    ws.build_index = gate
    service = routed_service()
    service.prewarm_enabled = True
    old = service.router
    old_ref = weakref.ref(old)
    service._start_prewarm()
    assert gate.started.wait(10)
    answers, collected, request_done = {}, threading.Event(), threading.Event()
    real_collect = live_mod.gc.collect

    def collect(*args, **kwargs):
        if variant == 'c' and threading.current_thread().name == 'staffer-prewarm':
            request_done.wait(20)         # c: the request on the old router has finished before the collection
        result = real_collect(*args, **kwargs)
        if threading.current_thread().name == 'staffer-prewarm':
            collected.set()
        return result
    live_mod.gc.collect = collect
    real_full_evidence = cr._full_evidence
    if variant == 'b':
        def slow_full_evidence(*args, **kwargs):
            if threading.current_thread().name == 'request-on-old' and not collected.is_set():
                collected.wait(20)          # still inside the old router's search while the new prewarm collects
            return real_full_evidence(*args, **kwargs)
        cr._full_evidence = slow_full_evidence

    def request_on_old():
        try:
            answers['old'] = service.route(*REQ, {'objective': 'work_time', 'limit': 501})
        finally:
            request_done.set()
    request = threading.Thread(target=request_on_old, name='request-on-old')
    request.start()                       # captures the old router, then waits on the in-flight build
    time.sleep(.3)
    if variant != 'a':
        old = None
        gc.disable()                      # a large heap: no automatic full collection in the window
    service._refresh_profiles(force=True)   # publishes the new router: the old one is released while its build is in flight
    probe = old_ref()
    released_table_empty = probe is not None and probe.closeness_routes.indexes == {}
    probe = None
    gate.release.set()
    request.join(30)
    settle()
    cr._full_evidence = real_full_evidence
    live_mod.gc.collect = real_collect
    ws.build_index = counting_build
    probe = old_ref()
    repopulated = probe is not None and DEFAULT_KEY in probe.closeness_routes.indexes
    probe = None
    alive_after = old_ref() is not None
    real_collect()
    gc.enable()
    alive_after_collect = old_ref() is not None
    print('  %s: table empty right after the release=%s; old router alive after everything=%s, its in-flight build re-inserted into the released table=%s; '
          'builds=%d; request on the old router same answer=%s; new prewarm %s gc_ms=%s; alive after one more collect=%s' % (
              variant, released_table_empty, alive_after, repopulated, gate.calls, canon(answers.get('old', {})) == expected,
              service.metrics['prewarm']['status'], service.metrics['prewarm'].get('gc_ms'), alive_after_collect))
    old = None
