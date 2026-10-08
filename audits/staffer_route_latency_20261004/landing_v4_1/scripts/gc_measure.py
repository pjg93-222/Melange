"""C: what one full gc.collect() costs on a synthetic heap, with nothing to free (the startup case) and with a replaced router to
free (the publish case), per tracked object and per MB of resident set. cwd = the 79ef9f1b7 export. One world size per run."""
import gc, os, sys, time
import psutil

sys.path.insert(0, os.getcwd())
from fec.surfaces.test_staffer_closeness_bidirectional import synthetic_router

PEOPLE = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
OFFICES = max(30, PEOPLE // 60)
proc = psutil.Process()


def rss():
    return proc.memory_info().rss / 1048576


def build():
    router, _, _ = synthetic_router(3, people=PEOPLE, offices=OFFICES, tenures=(2, 6))
    router.closeness().index(router._options({'objective': 'work_time'}))
    return router


def timed_collect():
    mark = time.perf_counter()
    freed = gc.collect()
    return (time.perf_counter() - mark) * 1000, freed


gc.disable()
r1 = build()
gc.collect()
tracked = len(gc.get_objects())
steady = [timed_collect() for _ in range(3)]
print('people %d: rss %.0f MB, tracked objects %.2f M, allocated blocks %.2f M' % (PEOPLE, rss(), tracked / 1e6, sys.getallocatedblocks() / 1e6))
print('  startup case (nothing to free): %s ms  -> %.0f ns per tracked object, %.2f ms per MB rss' % (
    [round(t) for t, _ in steady], min(t for t, _ in steady) * 1e6 / tracked, min(t for t, _ in steady) / rss()))
r2 = build()
before = rss()
r1.release_search_state()
r1 = None                      # the router shell is cyclic garbage now
t, freed = timed_collect()
print('  publish case (one replaced router to free): %.0f ms, %d objects freed, rss %.0f -> %.0f MB' % (t, freed, before, rss()))
gc.enable()
