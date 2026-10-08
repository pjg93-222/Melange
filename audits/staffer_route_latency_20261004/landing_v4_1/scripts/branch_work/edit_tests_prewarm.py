"""v4.1 fixes 1 and 2, the prewarm tests (fec/tests/surfaces/test_staffer_prewarm.py): no collection at a start, one after a replacement,
a released router stores nothing."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\tests\surfaces\test_staffer_prewarm.py'

SWAP_OLD = r'''    assert DEFAULT_KEY in new.closeness_routes.indexes and DEFAULT_KEY in old.closeness_routes.indexes
    assert new.closeness_routes.indexes[DEFAULT_KEY] is not old.closeness_routes.indexes[DEFAULT_KEY], 'the new router has its own index'
    assert service._explorer_index['revision'] == service.revision
'''
SWAP_NEW = r'''    assert DEFAULT_KEY in new.closeness_routes.indexes, 'the new router built its own index'
    assert old.closeness_routes.indexes == {}, 'the replaced router was released while its build ran, so the finished build was not put back into it'
    assert service._explorer_index['revision'] == service.revision
'''

HEADER_OLD = r'''# D-087: memory headroom on this host is the binding constraint. When the service publishes a new router it lets go of what the
# replaced one kept for its searches (the work indexes, the hop-row caches, the name index), and the prewarm runs one collection
# before it builds, so the old router's indexes and the new router's are not resident together. No answer changes.
'''
HEADER_NEW = r'''# D-087: memory headroom on this host is the binding constraint. When the service publishes a new router it lets go of what the
# replaced one kept for its searches (the work indexes, the hop-row caches, the name index), and the prewarm that follows a replacement
# runs one collection before it builds (a prewarm at a start follows none, and runs none: nothing is freed and a collection stalls every
# request thread), so the old router's indexes and the new router's are not meant to be resident together. No answer changes.
'''

COLLECT_OLD = r'''def test_one_collection_runs_before_the_first_build_of_a_prewarm_and_none_in_an_abandoned_one(monkeypatch):
    service = prewarmed_service()
    trace, real_collect = [], gc.collect
    real_build, real_network = staffer_work_sources.build_index, LiveService.network_index

    def collect(*args, **kwargs):
        if threading.current_thread().name == 'staffer-prewarm':
            trace.append('gc')
        return real_collect(*args, **kwargs)
    monkeypatch.setattr(live.gc, 'collect', collect)
    monkeypatch.setattr(staffer_work_sources, 'build_index', lambda router, options: trace.append('work_index') or real_build(router, options))
    monkeypatch.setattr(LiveService, 'network_index', lambda self, *a, **k: trace.append('network_index') or real_network(self, *a, **k))
    service._start_prewarm()
    settle()
    assert trace == ['gc', 'work_index', 'network_index'], 'one collection, before the first build and not between the stages'
    assert service.metrics['prewarm']['gc_ms'] >= 0
    # Several swaps while the first prewarm builds: the first prewarm's collection, and the last router's. The two in between
    # are abandoned before any build, so they collect nothing.
    trace.clear()
    gate = Gate(monkeypatch)
    monkeypatch.setattr(live.gc, 'collect', collect)
    service._refresh_profiles(force=True)
    assert gate.started.wait(10)
    for _ in range(3):
        service._refresh_profiles(force=True)
    gate.release.set()
    settle()
    assert gate.calls == 2 and trace.count('gc') == 2, trace
'''
COLLECT_NEW = r'''def traced_prewarm(monkeypatch):
    """What a prewarm does, in order: each collection (the prewarm thread's own), each work index build and each people index request."""
    trace, real_collect = [], gc.collect
    real_build, real_network = staffer_work_sources.build_index, LiveService.network_index

    def collect(*args, **kwargs):
        if threading.current_thread().name == 'staffer-prewarm':
            trace.append('gc')
        return real_collect(*args, **kwargs)
    monkeypatch.setattr(live.gc, 'collect', collect)
    monkeypatch.setattr(staffer_work_sources, 'build_index', lambda router, options: trace.append('work_index') or real_build(router, options))
    monkeypatch.setattr(LiveService, 'network_index', lambda self, *a, **k: trace.append('network_index') or real_network(self, *a, **k))
    return trace


def test_a_prewarm_at_a_start_runs_no_collection_because_no_router_was_replaced(monkeypatch):
    """At a start nothing is freed, and a full collection holds every request thread while it runs: on the live heap it held them for
    10.1 s (gc_ms on /api/staffer-performance), before the 40 s build, for nothing."""
    service = prewarmed_service()
    trace = traced_prewarm(monkeypatch)
    assert service._router_replaced is False, 'the first router the service published replaced nothing'
    service._start_prewarm()
    settle()
    assert trace == ['work_index', 'network_index'], 'the two builds, and no collection'
    state = service.metrics['prewarm']
    assert state['status'] == 'done' and 'gc_ms' not in state
    assert service._router_replaced is False


def test_the_prewarm_after_a_replacement_runs_one_collection_before_its_first_build_and_a_later_one_runs_none(monkeypatch):
    service = prewarmed_service()
    service._start_prewarm()
    settle()                                  # a start: nothing replaced, nothing collected
    trace = traced_prewarm(monkeypatch)
    service._refresh_profiles(force=True)     # publishes a new router: the old one is replaced and released, and the new one's prewarm queued
    settle()
    assert trace == ['gc', 'work_index', 'network_index'], 'one collection, before the first build and not between the stages'
    state = service.metrics['prewarm']
    assert state['seq'] == 2 and state['status'] == 'done' and state['gc_ms'] >= 0
    assert service._router_replaced is False, 'the prewarm that collected has used up the request for one'
    trace.clear()
    service._start_prewarm()                  # the same router again: nothing was replaced since, so nothing to collect
    settle()
    assert trace == ['network_index'] and 'gc_ms' not in service.metrics['prewarm'], trace


def test_prewarms_abandoned_before_they_build_collect_nothing_and_the_one_that_builds_collects_for_every_swap(monkeypatch):
    service = prewarmed_service()
    service._start_prewarm()
    settle()
    trace, real_collect = [], gc.collect

    def collect(*args, **kwargs):
        if threading.current_thread().name == 'staffer-prewarm':
            trace.append('gc')
        return real_collect(*args, **kwargs)
    gate = Gate(monkeypatch)
    monkeypatch.setattr(live.gc, 'collect', collect)
    service._refresh_profiles(force=True)     # the first replacement: its prewarm collects, then builds (held at the gate)
    assert gate.started.wait(10)
    for _ in range(3):                        # three more swaps while it builds: two prewarms are abandoned before any build
        service._refresh_profiles(force=True)
    assert service._router_replaced is True, 'the swaps since the collection are waiting for one'
    gate.release.set()
    settle()
    assert gate.calls == 2 and trace == ['gc', 'gc'], trace   # the first prewarm's, and the last router's
    assert service._router_replaced is False


def test_only_a_router_that_was_actually_replaced_asks_for_a_collection():
    service = routed_service()
    router = service.router
    service._release_replaced_router(None, router)         # the first router of a start
    service._release_replaced_router(router, router)       # the same router published again
    assert service._router_replaced is False
    other = routed_service().router
    service._release_replaced_router(other, router)
    assert service._router_replaced is True and other.closeness_routes.released
    service._router_replaced = False

    class Broken:
        def release_search_state(self):
            raise RuntimeError('release failed')
    service._release_replaced_router(Broken(), router)     # the router was replaced even if letting go of its state failed
    assert service._router_replaced is True and service.metrics['router_release_error'] == 'RuntimeError: release failed'
'''

BUILD_AGAIN_OLD = r'''def test_a_request_that_reaches_the_released_router_builds_again_and_answers_exactly_as_before():
    service = a_prewarmed_service_that_has_served_a_search()
    router = service.router
    before = work_route(service, 2)
    held = router.closeness_routes.indexes[DEFAULT_KEY]       # what a search that is running holds
    router.release_search_state()
    assert router.closeness_routes.indexes == {} and router.closeness_routes.row_caches == {}
    after = work_route(service, 3)                             # another request: not the finished result, so a search
    assert router.closeness_routes.indexes[DEFAULT_KEY] is not held, 'it built the index again'
    assert after['neighbor_checks'] > 0 and strip(after) == strip(before)
    assert json.dumps(strip(after), sort_keys=True) == json.dumps(strip(before), sort_keys=True)
'''
BUILD_AGAIN_NEW = r'''def test_a_request_that_reaches_the_released_router_builds_its_own_index_and_answers_exactly_as_before(monkeypatch):
    service = a_prewarmed_service_that_has_served_a_search()
    router = service.router
    before = work_route(service, 2)
    held = router.closeness_routes.indexes[DEFAULT_KEY]       # what a search that is running holds
    router.release_search_state()
    assert router.closeness_routes.indexes == {} and router.closeness_routes.row_caches == {}
    builds, real_build = [], staffer_work_sources.build_index
    monkeypatch.setattr(staffer_work_sources, 'build_index', lambda r, o: builds.append(1) or real_build(r, o))
    after = work_route(service, 3)                             # another request: not the finished result, so a search
    assert builds == [1], 'it built an index of its own'
    assert router.closeness_routes.indexes == {} and router.closeness_routes.row_caches == {}, 'and the released router kept neither it nor its rows'
    assert after['neighbor_checks'] > 0 and strip(after) == strip(before)
    assert json.dumps(strip(after), sort_keys=True) == json.dumps(strip(before), sort_keys=True)
    assert held is not None
'''

IDENTITY_OLD = r'''    service._rebuild_identity()
    assert held() is None, 'the identity rebuild published a new router and released the old one\'s work index'
    assert service.router.closeness_routes.indexes == {}
'''
IDENTITY_NEW = r'''    service._rebuild_identity()
    assert held() is None, 'the identity rebuild published a new router and released the old one\'s work index'
    assert service.router.closeness_routes.indexes == {}
    assert service._router_replaced is True, 'and asked for the collection that frees the router itself'
'''

edit(PATH, [(SWAP_OLD, SWAP_NEW), (HEADER_OLD, HEADER_NEW), (COLLECT_OLD, COLLECT_NEW), (BUILD_AGAIN_OLD, BUILD_AGAIN_NEW), (IDENTITY_OLD, IDENTITY_NEW)])
