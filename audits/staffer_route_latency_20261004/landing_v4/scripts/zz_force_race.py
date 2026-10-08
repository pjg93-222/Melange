"""A pytest plugin that makes the race of test_a_lost_cheapest_route_reaches_the_page_as_a_search_error_over_http happen every time instead of in 0.4 to 0.9 percent of runs.

The test starts an async search whose worker is made to fail at once (the forced guard). `LiveService.start_route_search` builds its first answer with `route_search_result(key)`, which says
queued or searching while the worker has not finished and search_error once it has. This plugin makes that first call wait until the worker has finished, which is the worker winning the race.
Loaded with `-p zz_force_race`; it changes nothing else (later polls are unchanged apart from the same wait, which is a no-op once the job is done).
"""
import pytest

from fec.surfaces import staffer_live_service as service_module


@pytest.fixture(autouse=True)
def the_worker_always_finishes_first(monkeypatch):
    original = service_module.LiveService.route_search_result

    def waiting(self, key):
        with self.lock:
            job = self.route_jobs.get(key)
        if job is not None:
            try:
                job['future'].exception(timeout=5)
            except Exception:  # a worker that raised, or a timeout: the original method reports it
                pass
        return original(self, key)
    monkeypatch.setattr(service_module.LiveService, 'route_search_result', waiting)
