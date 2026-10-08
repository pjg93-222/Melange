"""v4.1 fixes 2 and 4 in fec/surfaces/staffer_closeness_routes.py: one work index per request, a released router that stores nothing, uncovered_basis."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

PATH = r'C:\Users\pgoff\Melange-wt\route-core\fec\surfaces\staffer_closeness_routes.py'

IMPORTS_OLD = r'''from collections import OrderedDict, namedtuple
from copy import deepcopy
'''
IMPORTS_NEW = r'''from collections import OrderedDict, namedtuple
import contextlib
import contextvars
from copy import deepcopy
'''

DOC_OLD = r'''unreachable or coverage, says who was left out (uncovered_staff_count, uncovered_staff_ids, sorted; target_count still counts the
staff the request named), and an unreachable reason is judged on the covered staff. It is insufficient_work_coverage only when its
origin is uncovered or none of the office's staff is covered. An office none of whose usable staff has dated work at it says so of
"the staff this search could use" when some staff were left out (not covered) or kept out (avoided), and of "this office's current
staff" only when nobody was (SEARCHED_STAFF_MESSAGES).
"""
'''
DOC_NEW = r'''unreachable or coverage, says who was left out (uncovered_staff_count, uncovered_staff_ids, sorted; target_count still counts the
staff the request named) and which coverage they lack (uncovered_basis: payroll_or_roster, or roster alone when work_sources is
directory, which reads no payroll evidence, so none can cover anyone), and an unreachable reason is judged on the covered staff. It is
insufficient_work_coverage only when its origin is uncovered or none of the office's staff is covered. An office none of whose usable
staff has dated work at it says so of "the staff this search could use" when some staff were left out (not covered) or kept out
(avoided), and of "this office's current staff" only when nobody was (SEARCHED_STAFF_MESSAGES).

One index per request. A request that runs several passes (distinct and independent alternatives call ClosenessRoutes.route once per
pass) takes its work index at its first pass and keeps it to its last (request_work, opened by AdvocacyRouter.route_many), so a router
the service releases between two passes does not build the whole index again for the next. A released router stores no index and no
hop-row cache it builds, and still answers every request that reaches it.
"""
'''

SCOPE_OLD = r'''class ClosenessRoutes:
    """Work-time routes for one router: the closeness index, the shared hop-row caches and the search over them.
'''
SCOPE_NEW = r'''# One search request, one work index. A request with several passes (distinct and independent alternatives call ClosenessRoutes.route once
# per pass) takes the index at its first pass and keeps it to its last, whatever the router's table holds in between: a publish that
# releases the router between two passes must not make the next pass build the whole index again (tens of seconds on the live records).
# A contextvar, so a request on another thread has its own and nothing has to be passed through route_many's signature.
_REQUEST_WORK = contextvars.ContextVar('staffer_request_work', default=None)


class _RequestWork:
    """What one request has taken from the ClosenessRoutes it searches: its work indexes by key and, for a released router, the hop-row
    caches that router no longer keeps."""
    __slots__ = ('indexes', 'row_caches')

    def __init__(self):
        self.indexes, self.row_caches = {}, {}


@contextlib.contextmanager
def request_work():
    """Keep one work index (and, on a released router, one hop-row cache) for every pass of the request that runs inside.

    AdvocacyRouter.route_many opens it around distinct_routes and the Yen loop. A scope that is already open is the request's own, so a
    nested one changes nothing. It closes, and what it held is let go, when the request ends, however it ends.
    """
    if _REQUEST_WORK.get() is not None:
        yield
        return
    token = _REQUEST_WORK.set(_RequestWork())
    try:
        yield
    finally:
        _REQUEST_WORK.reset(token)


class ClosenessRoutes:
    """Work-time routes for one router: the closeness index, the shared hop-row caches and the search over them.
'''

INIT_OLD = r'''        self.row_caches = OrderedDict()
        self.row_lock = threading.Lock()
        # Tests pass _search_reference here; the server never does.
'''
INIT_NEW = r'''        self.row_caches = OrderedDict()
        self.row_lock = threading.Lock()
        # Set by release(), for good: the service has replaced this router. It stores no index and no hop-row cache from then on.
        self.released = False
        # Tests pass _search_reference here; the server never does.
'''

INDEX_OLD = r'''    def index(self, options):
        """The work index for the options that shape it, built once: concurrent callers wait for the one build.

        The lock only guards the two small tables and is never held while building, which takes tens of seconds on
        the live records. A build that fails raises in every caller then waiting on it and is retried by the next.
        """
        key = (options['include_review'], options['include_unresolved'], options['include_historical'], options['work_sources'])
        with self.index_lock:
'''
INDEX_NEW = r'''    def index(self, options):
        """The work index for the options that shape it, built once: concurrent callers wait for the one build.

        A request that holds a scope (request_work) is given the index it took first for every later pass, whatever the table holds by then.
        """
        key = (options['include_review'], options['include_unresolved'], options['include_historical'], options['work_sources'])
        scope = _REQUEST_WORK.get()
        if scope is not None:
            held = scope.indexes.get((self, key))
            if held is not None:
                return held
        index = self._shared_index(key, options)
        if scope is not None:
            scope.indexes[(self, key)] = index
        return index

    def _shared_index(self, key, options):
        """The table's index for `key` (built with `options` if it holds none): the part of index() every request shares.

        The lock only guards the two small tables and is never held while building, which takes tens of seconds on
        the live records. A build that fails raises in every caller then waiting on it and is retried by the next. A released router
        keeps nothing it builds: the callers waiting on the build still get its index, and the table stays empty.
        """
        with self.index_lock:
'''

STORE_OLD = r'''            with self.index_lock:
                if error is None:
                    self.indexes[key] = index
                    while len(self.indexes) > 4:
                        self.indexes.popitem(last=False)
                del self.index_flights[key]
            flight.finish(index, error)
'''
STORE_NEW = r'''            with self.index_lock:
                if error is None and not self.released:
                    self.indexes[key] = index
                    while len(self.indexes) > 4:
                        self.indexes.popitem(last=False)
                del self.index_flights[key]
            flight.finish(index, error)
'''

ROWS_OLD = r'''        with self.row_lock:
            cache = self.row_caches.get(key)
            if cache is None or cache.index is not index:
                cache = self.row_caches[key] = _RowCache(index)
            self.row_caches.move_to_end(key)
            while len(self.row_caches) > self.MAX_ROW_CACHES:
                self.row_caches.popitem(last=False)
            return cache

    def release(self):
        """Let go of the work indexes and hop-row caches, for a router the service has replaced (AdvocacyRouter.release_search_state).

        A search that is running keeps the index and the caches it already holds; one that asks afterwards builds them again and
        answers exactly as before, so nothing here changes an answer. The finished results (self.cache) are small and stay, as does
        the router: the two refer to each other, so the router itself is freed only by a garbage collection.
        """
        with self.index_lock:
            self.indexes.clear()
        with self.row_lock:
            self.row_caches.clear()
'''
ROWS_NEW = r'''        with self.row_lock:
            if self.released:
                # The router has been replaced: nothing is stored on it. A request with a scope shares one cache among its passes.
                return self._unstored_row_cache(key, index)
            cache = self.row_caches.get(key)
            if cache is None or cache.index is not index:
                cache = self.row_caches[key] = _RowCache(index)
            self.row_caches.move_to_end(key)
            while len(self.row_caches) > self.MAX_ROW_CACHES:
                self.row_caches.popitem(last=False)
            return cache

    def _unstored_row_cache(self, key, index):
        scope = _REQUEST_WORK.get()
        if scope is None:
            return _RowCache(index)
        cache = scope.row_caches.get((self, key))
        if cache is None or cache.index is not index:
            cache = scope.row_caches[(self, key)] = _RowCache(index)
        return cache

    def release(self):
        """Let go of the work indexes and hop-row caches, for a router the service has replaced (AdvocacyRouter.release_search_state).

        A search that is running keeps the index and the caches it already holds (a request keeps its one index for all its passes,
        request_work); one that asks afterwards builds its own and answers exactly as before, so nothing here changes an answer. From
        here on the router stores no index and no hop-row cache it builds, and an index whose build was still running is not put back
        into the emptied table. The finished results (self.cache) are small and stay, as does the router: the two refer to each other, so
        the router itself is freed only by a garbage collection.
        """
        self.released = True          # first: whatever stores after this sees it, and whatever stored before is cleared below
        with self.index_lock:
            self.indexes.clear()
        with self.row_lock:
            self.row_caches.clear()
'''

OFFICE_OLD = r'''            uncovered = [p for p in targets if not allowed(p)]
            base.update(uncovered_staff_count=len(uncovered), uncovered_staff_ids=uncovered)
'''
OFFICE_NEW = r'''            uncovered = [p for p in targets if not allowed(p)]
            # What "uncovered" means in this search: no payroll evidence and not on the staffer roster, or, where payroll evidence is not read
            # at all (a directory-only comparison), not on the roster.
            base.update(uncovered_staff_count=len(uncovered), uncovered_staff_ids=uncovered,
                        uncovered_basis='roster' if options['work_sources'] == 'directory' else 'payroll_or_roster')
'''

edit(PATH, [(IMPORTS_OLD, IMPORTS_NEW), (DOC_OLD, DOC_NEW), (SCOPE_OLD, SCOPE_NEW), (INIT_OLD, INIT_NEW), (INDEX_OLD, INDEX_NEW),
            (STORE_OLD, STORE_NEW), (ROWS_OLD, ROWS_NEW), (OFFICE_OLD, OFFICE_NEW)])
