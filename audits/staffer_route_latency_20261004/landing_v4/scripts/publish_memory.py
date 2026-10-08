"""Peak memory of a router publish plus its prewarm, on a synthetic world (fix round 2026-10-03, D-087).

Run with cwd = a tree root (an export of a commit):  python -B publish_memory.py <people> <episodes_per_person> <offices> [--label X]

One process: build router R1 and publish it, prewarm the work index (I1); then build a second, equal router R2, swap it in the way
LiveService._refresh_profiles_locked does (replace the router, release the replaced one where this tree has that, drop the local,
queue the prewarm) and let the prewarm build the work index (I2). The people index stage is left out (PREWARM_STAGES is the work
index only): the fix concerns the router's work state.  RSS is sampled every 20 ms.

Prints one JSON line: rss at each point and the peak of the two phases (building R2 and swapping; prewarm after the swap).
"""
import gc
import json
import os
import random
import sys
import threading
import time
from datetime import date, timedelta
from types import SimpleNamespace

sys.path.insert(0, os.getcwd())
import psutil

from fec.surfaces.staffer_live_service import LiveService
from fec.surfaces.staffer_routing import AdvocacyRouter

people, per, offices = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
label = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else ''
proc = psutil.Process()
MB = 2 ** 20


def make_router(revision):
    rng = random.Random(7)
    nodes = {}
    for i in range(offices):
        oid = 'container:office:house:OFFICE %04d' % i
        nodes[oid] = {'id': oid, 'kind': 'container', 'container_kind': 'member_office', 'chamber': 'house', 'label': 'Office %d' % i,
                      'member_bioguide': 'M%06d' % i}
    proof = {'path': 'C:/x/payroll_identity.json.gz', 'sha256': 'f' * 64, 'method': 'payroll-identity-rows-v1'}
    episodes = []
    d0 = date(2001, 1, 1)
    for i in range(people):
        p = 'person:hill:%064x' % i
        nodes[p] = {'id': p, 'kind': 'person', 'label': 'Person %d' % i, 'member_ids': [], 'committee_ids': [], 'policy_ids': []}
        home = rng.randrange(offices)
        n = max(1, int(rng.expovariate(1 / per)))
        t = d0 + timedelta(days=rng.randrange(9000))
        for k in range(n):
            c = home if rng.random() < .6 else (home + rng.randint(-5, 5)) % offices
            length = rng.choice([90, 180, 365, 700, 1400])
            start, end = t, t + timedelta(days=length)
            t = end + timedelta(days=rng.choice([0, 0, 30, 200]))
            episodes.append({'person_id': p, 'employer_id': 'container:office:house:OFFICE %04d' % c,
                             'title': rng.choice(['STAFF ASSISTANT', 'LEGISLATIVE ASSISTANT', 'CHIEF OF STAFF']),
                             'start': start.isoformat(), 'end_exclusive': end.isoformat(), 'employment_verified': True,
                             'date_evidence': rng.choice(['observed_interval', 'presence_within_report']),
                             'provenance': {**proof, 'source_row_ids': [rng.randrange(10 ** 7)], 'date_method': 'x', 'native_person_id': p}})
    router = AdvocacyRouter(nodes, episodes, revision, '2026-10-03')
    del episodes, nodes
    router.operational_staffer_ids = None
    router.closeness()          # as the service does before it publishes a router
    return router


class Sampler(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.stop_flag, self.peak, self.blocks = threading.Event(), 0, 0
        self.marks = {}

    def run(self):
        while not self.stop_flag.is_set():
            rss = proc.memory_info().rss
            self.peak = max(self.peak, rss)
            self.blocks = max(self.blocks, sys.getallocatedblocks())
            time.sleep(0.02)

    def reset(self):
        peak, blocks = self.peak, self.blocks
        self.peak, self.blocks = 0, 0
        return peak, blocks


def prewarm_threads():
    return [t for t in threading.enumerate() if t.name == 'staffer-prewarm']


def wait_for_prewarm():
    for thread in prewarm_threads():
        thread.join(600)


service = LiveService('fixture', SimpleNamespace(nodes={}))
service.ready, service.stage = True, 'Ready'
service.prewarm_enabled = True
service.PREWARM_STAGES = ('work_index',)
out = {'label': label, 'people': people, 'episodes_per_person': per, 'offices': offices,
       'has_release': hasattr(service, '_release_replaced_router')}

rss0 = proc.memory_info().rss
r1 = make_router('r1')
service.router, service.revision = r1, r1.revision
del r1
service._start_prewarm()
wait_for_prewarm()
out['prewarm1'] = {k: v for k, v in service.metrics['prewarm'].items() if k in ('status', 'total_ms', 'gc_ms')}
index1_present = len(service.router.closeness_routes.indexes)
out['rss_start_mb'] = round(rss0 / MB)
out['rss_r1_i1_mb'] = round(proc.memory_info().rss / MB)       # R1 and its work index resident
out['blocks_r1_i1_m'] = round(sys.getallocatedblocks() / 1e6, 2)

sampler = Sampler()
sampler.start()
sampler.reset()
# phase 1: the new router is built while the old one serves, then swapped in
r2 = make_router('r2')
out['rss_r2_built_mb'] = round(proc.memory_info().rss / MB)
out['blocks_r2_built_m'] = round(sys.getallocatedblocks() / 1e6, 2)
peak1, blocks1 = sampler.reset()
replaced = service.router
service.router, service.revision = r2, r2.revision
del r2
release = getattr(service, '_release_replaced_router', None)
if release is not None:
    release(replaced, service.router)
replaced = None
out['rss_swapped_mb'] = round(proc.memory_info().rss / MB)
out['blocks_swapped_m'] = round(sys.getallocatedblocks() / 1e6, 2)
# phase 2: the prewarm of the new router
started = time.perf_counter()
service._start_prewarm()
wait_for_prewarm()
out['phase2_seconds'] = round(time.perf_counter() - started, 1)
peak2, blocks2 = sampler.reset()
sampler.stop_flag.set()
out['rss_end_mb'] = round(proc.memory_info().rss / MB)
out['blocks_end_m'] = round(sys.getallocatedblocks() / 1e6, 2)
out['peak_phase1_mb'] = round(peak1 / MB)            # building R2 and swapping it in
out['peak_phase2_mb'] = round(peak2 / MB)            # the prewarm that builds I2
out['peak_blocks_phase2_m'] = round(blocks2 / 1e6, 2)
out['peak_wset_mb'] = round(getattr(proc.memory_info(), 'peak_wset', 0) / MB)
state = service.metrics['prewarm']
out['prewarm2'] = {k: state.get(k) for k in ('status', 'total_ms', 'gc_ms')}
out['indexes_on_current_router'] = len(service.router.closeness_routes.indexes)
print(json.dumps(out))
