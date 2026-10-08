"""v4.1 fixes 1, 3 and 5 in fec/surfaces/staffer_live_service.py: collect only when a router was replaced, the qualified memory comments, explanation = message."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\surfaces\staffer_live_service.py'

INIT_OLD = r'''        self._prewarm_seq = 0
        self._prewarm_latest = None
        self._prewarm_finished = deque(maxlen=4)
'''
INIT_NEW = r'''        self._prewarm_seq = 0
        self._prewarm_latest = None
        self._prewarm_finished = deque(maxlen=4)
        # Set when a publish replaced a router (_release_replaced_router), cleared by the prewarm that collects for it (under _prewarm_lock):
        # a collection runs only then, since at a start nothing was replaced and a collection would only stall every request thread.
        self._router_replaced = False
'''

COMMENT_OLD = r'''    # Memory is the constraint (D-087): a publish releases the replaced router's work state at once
    # (_release_replaced_router), and the prewarm runs one collection before its first build, so the old indexes and the new
    # ones are not resident together.
    PREWARM_STAGES = ('work_index', 'network_index')
'''
COMMENT_NEW = r'''    # Memory is the constraint (D-087): a publish releases the replaced router's work state at once
    # (_release_replaced_router), and the prewarm that follows a replacement runs one collection before its first build (a prewarm at a
    # start follows none, so it runs none), which is meant to keep the old indexes and the new ones from being resident together. It is not
    # guaranteed: a request that was already running on the replaced router keeps the index it holds until it ends, and a long one can
    # outlast the collection and the new router's build, so the two can be resident together for that long.
    PREWARM_STAGES = ('work_index', 'network_index')
'''

RELEASE_OLD = r'''        name index), so that they are not held while the new router's are built. A search still running on it keeps what it
        holds, one that asks afterwards builds again, and no answer changes (AdvocacyRouter.release_search_state). The router
        itself is freed by the collection that runs before the prewarm's first build. Never raises, never takes the service lock."""
        if replaced is None or replaced is current:
            return
        try:
'''
RELEASE_NEW = r'''        name index), so that they are not held while the new router's are built. A search still running on it keeps what it
        holds, one that asks afterwards builds its own (the replaced router stores nothing from then on), and no answer changes
        (AdvocacyRouter.release_search_state). The router itself is freed by the collection that the next prewarm runs, which this
        call asks for. Never raises, never takes the service lock."""
        if replaced is None or replaced is current:
            return
        with self._prewarm_lock:
            self._router_replaced = True
        try:
'''

PREWARM_OLD = r'''            failed = False
            collected = False
            for name in self.PREWARM_STAGES:
                if self.router is not router or self._stop.is_set():
                    record.update(status='abandoned', abandoned_before=name)
                    break
                if not collected:
                    # One full collection, before this prewarm builds anything: what the router the service replaced left
                    # behind (it is only reachable from itself, so only a collection frees it) is gone before the new indexes are
                    # built, and the old indexes and the new ones are never resident together.
                    collected, mark = True, time.perf_counter()
                    gc.collect()
                    record['gc_ms'] = round((time.perf_counter() - mark) * 1000, 2)
'''
PREWARM_NEW = r'''            failed = False
            checked = False
            for name in self.PREWARM_STAGES:
                if self.router is not router or self._stop.is_set():
                    record.update(status='abandoned', abandoned_before=name)
                    break
                if not checked:
                    checked = True
                    with self._prewarm_lock:
                        replaced, self._router_replaced = self._router_replaced, False
                    if replaced:
                        # One full collection, before this prewarm builds anything, and only because a publish replaced a router since
                        # the last one (a start replaced none: there was nothing to free, and the collection held every request thread
                        # for ten seconds on the live heap). What the router the service replaced left behind (it is only reachable
                        # from itself, so only a collection frees it) is gone before the new indexes are built, so the old indexes and
                        # the new ones are not resident together, unless a request that was already running on the replaced router
                        # still holds them: that request keeps its index until it ends, and no collection frees what it still refers to.
                        mark = time.perf_counter()
                        gc.collect()
                        record['gc_ms'] = round((time.perf_counter() - mark) * 1000, 2)
'''

EXPLAIN_OLD = r'''        if result['status'] == 'unknown_person':
            explanation = 'No search was run: only known people with a resolved name can be route endpoints; institutions, activities and routing hubs are evidence, not endpoints.'
        elif result['status'] == 'search_limited':
            explanation = 'Search reached its effort limit; this does not establish that no route exists. No conclusion about reachability was reached.'
        elif result['status'] == 'unreachable':
            explanation = 'No supported path exists in the currently indexed evidence under these filters. This does not establish that no real-world introduction is possible.'
        elif result['status'] == 'insufficient_work_coverage':
            explanation = result['message']
        if result.get('alternative_strategy') in ('distinct', 'independent'):
'''
EXPLAIN_NEW = r'''        # A Staffer answer that found no route says why (unreachable_reason, message): its explanation is that message, the text the page shows
        # for it, so no consumer is handed the generic sentence beside a reason it contradicts. An answer with no reason keeps the generic one.
        reasoned = result['status'] == 'unreachable' and bool(result.get('unreachable_reason') and result.get('message'))
        if result['status'] == 'unknown_person':
            explanation = 'No search was run: only known people with a resolved name can be route endpoints; institutions, activities and routing hubs are evidence, not endpoints.'
        elif result['status'] == 'search_limited':
            explanation = 'Search reached its effort limit; this does not establish that no route exists. No conclusion about reachability was reached.'
        elif result['status'] == 'unreachable':
            explanation = (result['message'] if reasoned else
                           'No supported path exists in the currently indexed evidence under these filters. This does not establish that no real-world introduction is possible.')
        elif result['status'] == 'insufficient_work_coverage':
            explanation = result['message']
        if not reasoned and result.get('alternative_strategy') in ('distinct', 'independent'):
'''

edit(PATH, [(INIT_OLD, INIT_NEW), (COMMENT_OLD, COMMENT_NEW), (RELEASE_OLD, RELEASE_NEW), (PREWARM_OLD, PREWARM_NEW), (EXPLAIN_OLD, EXPLAIN_NEW)])
