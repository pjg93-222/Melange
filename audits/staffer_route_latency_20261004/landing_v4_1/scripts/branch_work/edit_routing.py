"""v4.1 fixes 2 and 4: route_many opens the request scope around the multi-pass searches (staffer_routing.py); the distinct loop carries uncovered_basis (staffer_distinct_routes.py)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_lib import edit

ROOT = r'C:\Users\pgoff\Melange-wt\route-core\fec\surfaces'

RELEASE_OLD = r'''        For a router the service has replaced, so that its indexes are not held while the next router's are built. A search
        still running keeps what it already holds, and one that asks afterwards builds again and answers exactly as before.
        """
'''
RELEASE_NEW = r'''        For a router the service has replaced, so that its indexes are not held while the next router's are built. A search
        still running keeps what it already holds (a request with several passes keeps the one index it took first, whatever
        happens to the router between its passes), and one that asks afterwards builds its own and answers exactly as before:
        from here on the router stores nothing it builds (ClosenessRoutes.release).
        """
'''

ROUTE_OLD = r'''        if options['route_count'] > 1 and options['alternative_strategy'] != 'ranked':
            from fec.surfaces.staffer_distinct_routes import distinct_routes
            return distinct_routes(self, origin, targets, options, progress)
        if options['objective'] == 'work_time':
            return self.closeness().route(origin, targets, options, progress)
        if options['route_count'] > 1:
            return self._route_alternatives(origin, targets, options, progress)
'''
ROUTE_NEW = r'''        if options['route_count'] > 1 and options['alternative_strategy'] != 'ranked':
            from fec.surfaces.staffer_distinct_routes import distinct_routes
            with self._one_work_index():
                return distinct_routes(self, origin, targets, options, progress)
        if options['objective'] == 'work_time':
            # One call, so one index for all of its Yen loop: ClosenessRoutes.route takes it once.
            return self.closeness().route(origin, targets, options, progress)
        if options['route_count'] > 1:
            with self._one_work_index():
                return self._route_alternatives(origin, targets, options, progress)
'''

HELPER_OLD = r'''    def route_many(self, origin, targets, options=None, progress=None):
        """Find the best person path to a target set in one symmetric search.
'''
HELPER_NEW = r'''    @staticmethod
    def _one_work_index():
        """The scope of one search request (staffer_closeness_routes.request_work).

        A request that searches once per pass (distinct and independent alternatives, the Yen loop) takes the work index at its first pass
        and uses that one to its last, so a publish that releases this router between two passes costs no rebuild. Imported here, as the
        closeness search is.
        """
        from fec.surfaces.staffer_closeness_routes import request_work
        return request_work()

    def route_many(self, origin, targets, options=None, progress=None):
        """Find the best person path to a target set in one symmetric search.
'''

DISTINCT_OLD = r'''        # An office search leaves its uncovered staff out once (D-086): they stay out of every later pass, and each route
        # reports the request's count, as the first pass counted it, not the count of the staff that pass was given.
        left_out = {key: first[key] for key in ('uncovered_staff_count', 'uncovered_staff_ids') if key in first}
'''
DISTINCT_NEW = r'''        # An office search leaves its uncovered staff out once (D-086): they stay out of every later pass, and each route
        # reports the request's count, as the first pass counted it, not the count of the staff that pass was given, and the
        # basis of that count (what coverage they lack), which is the request's too.
        left_out = {key: first[key] for key in ('uncovered_staff_count', 'uncovered_staff_ids', 'uncovered_basis') if key in first}
'''

edit(os.path.join(ROOT, 'staffer_routing.py'), [(RELEASE_OLD, RELEASE_NEW), (ROUTE_OLD, ROUTE_NEW), (HELPER_OLD, HELPER_NEW)])
edit(os.path.join(ROOT, 'staffer_distinct_routes.py'), [(DISTINCT_OLD, DISTINCT_NEW)])
