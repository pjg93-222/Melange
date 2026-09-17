"""Disposable scheduling checks: no network, production keys or live databases."""
from __future__ import annotations

import concurrent.futures
import copy
import json
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import api_company_cycle_fanout as f
import test_merge_company_shards as fixture


class WorkerSharingTest(unittest.TestCase):
    def queue(self, root, resume=False):
        plans = f.schedule_companies([('A', 10), ('B', 1), ('C', 1), ('D', 1), ('E', 1)], (2024, 2026), 2)
        path = root / 'manifest.json'
        f.atomic_json(path, {'lanes': copy.deepcopy(plans)})
        return f.CompanyWorkQueue(plans, {p['lane']:p['tasks'] for p in plans}, path, resume=resume)

    def test_idle_worker_borrows_whole_unstarted_company_and_persists_owner(self):
        with tempfile.TemporaryDirectory() as directory:
            q = self.queue(Path(directory))
            self.assertEqual(q.claim(1)[0][0]['company'], 'A')
            self.assertEqual(q.claim(2)[0][0]['company'], 'B')
            borrowed, resuming = q.claim(1)
            self.assertEqual({t['company'] for t in borrowed}, {'E'})
            self.assertEqual({t['cycle'] for t in borrowed}, {2024, 2026})
            self.assertFalse(resuming)
            saved = f.read_json(q.manifest_path)
            self.assertIn('E', saved['lanes'][0]['claimed_companies'])
            self.assertNotIn('E', saved['lanes'][1]['companies'])
            self.assertEqual(sum(len(p['tasks']) for p in q.plans), 10)
            self.assertEqual(len({t['task_id'] for p in q.plans for t in p['tasks']}), 10)

    def test_claim_survives_crash_before_receipt_and_legacy_owners_are_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            q = self.queue(root)
            q.claim(1); q.claim(2); q.claim(1)
            restarted = f.CompanyWorkQueue(q.plans, {1:[], 2:[t for t in q.plans[1]['tasks'] if t['company']=='B']}, q.manifest_path, resume=True)
            self.assertIsNone(restarted.claim(1))
            self.assertTrue(restarted.claim(2)[1])
            legacy = self.queue(root, resume=True)
            legacy.claim(1)
            self.assertIsNone(legacy.claim(1))
            self.assertFalse(legacy.managed_initialization)
            migrated = f.CompanyWorkQueue(legacy.plans, {p['lane']:p['tasks'] for p in legacy.plans}, legacy.manifest_path, resume=True)
            self.assertFalse(migrated.managed_initialization)

    def test_failed_manifest_write_does_not_dispatch_or_lose_work(self):
        with tempfile.TemporaryDirectory() as directory:
            q = self.queue(Path(directory))
            before = copy.deepcopy(q.plans)
            with mock.patch.object(f, 'atomic_json', side_effect=PermissionError('injected')):
                with self.assertRaises(PermissionError): q.claim(1)
            self.assertEqual(q.plans, before)
            self.assertEqual(q.pending_companies(), 5)
            self.assertEqual(q.claimed, set())

    def test_resource_leases_serialize_shared_database_or_key_and_release_on_error(self):
        for same_database in (True, False):
            gate = f.LaneLimiter(3)
            active = set()
            lock = threading.Lock()
            calls = []
            def execute(run, **kwargs):
                resources = {str(run.database), run.key}
                with lock:
                    self.assertFalse(active & resources)
                    active.update(resources)
                time.sleep(.015)
                with lock: active.difference_update(resources); calls.append(run.lane)
                if run.lane == 0: raise RuntimeError('injected')
                return {}
            runs = [f.LaneRun(i, Path('shared.db' if same_database else f'{i}.db'), Path('a'), Path('r'), Path('s'), Path('l'), f'key-{i}' if same_database else 'shared-key', '', (), 1) for i in range(3)]
            with mock.patch.object(f, 'execute_lane', side_effect=execute), concurrent.futures.ThreadPoolExecutor(3) as pool:
                futures=[pool.submit(f.execute_lane_with_limit,gate,run) for run in runs]
                for i,future in enumerate(futures):
                    if i==0:
                        with self.assertRaisesRegex(RuntimeError,'injected'): future.result(timeout=3)
                    else: future.result(timeout=3)
            self.assertEqual(sorted(calls), [0,1,2])
            self.assertEqual(gate.active(),0)
            self.assertEqual(gate.resources,set())

    def test_stop_wakes_waiters_without_starting_their_work(self):
        gate=f.LaneLimiter(2)
        self.assertTrue(gate.acquire(('busy',)))
        with concurrent.futures.ThreadPoolExecutor(1) as pool:
            future=pool.submit(gate.acquire,('busy',))
            gate.stop()
            self.assertFalse(future.result(timeout=2))
        gate.release(('busy',))
        self.assertFalse(gate.acquire())

    def test_borrowed_work_merges_every_cycle_once_and_resume_skips_successes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); source=root/'source.db'; fixture.create_database(source)
            with closing(sqlite3.connect(source)) as con, con:
                con.execute('CREATE TABLE companies(industry TEXT, company TEXT, variant TEXT)')
                con.executemany("INSERT INTO companies VALUES ('Fintech', ?, ?)",
                    [('A',f'A{i}') for i in range(10)]+[(c,c) for c in 'BCDE'])
            borrowed=threading.Event(); executions=[]; fail_b=True
            def execute(run, **kwargs):
                company=run.tasks[0]['company']
                if company=='B' and run.attempt==1:
                    self.assertTrue(borrowed.wait(3), 'idle worker did not borrow pending work')
                if run.lane==1 and company!='A': borrowed.set()
                succeeded=not(fail_b and company=='B')
                assignment=f.read_json(run.assignments)
                for marker in assignment.get('initialization_markers',{}).values():
                    f.atomic_json(Path(marker), {'initialized':True})
                tasks=[{**t,'status':'succeeded' if succeeded else 'failed','wall_clock_seconds':.01} for t in run.tasks]
                if succeeded:
                    with closing(sqlite3.connect(run.database)) as con, con:
                        con.executemany('INSERT OR REPLACE INTO contributions(sub_id,company,amount) VALUES(?,?,?)',
                            [(t['task_id'],t['company'],t['cycle']) for t in tasks])
                receipt={'status':'succeeded' if succeeded else 'failed','tasks':tasks}
                f.atomic_json(run.receipt,receipt)
                executions.extend((t['company'],t['cycle']) for t in tasks)
                return {'lane':run.lane,'attempt':run.attempt,'receipt':receipt,'exit_code':0 if succeeded else 2}
            args=['--source-database',str(source),'--industry','Fintech','--cycles','2024|2026',
                '--run-directory',str(root/'run'),'--rscript-path',sys.executable,'--budget-database',str(root/'budget.db'),
                '--max-parallel','2','--initial-workers','2','--recovery-workers','2']
            before=source.read_bytes()
            with mock.patch.object(f,'discover_keys',return_value=['key-a','key-b']),mock.patch.object(f,'execute_lane',side_effect=execute):
                self.assertEqual(f.main(args),2)
                self.assertEqual(source.read_bytes(),before)
                manifest=f.read_json(root/'run/manifest.json')
                self.assertGreater(len(manifest['scheduling']['handoffs']),0)
                fail_b=False; executions.clear()
                self.assertEqual(f.main([*args,'--resume']),0)
                self.assertEqual(sorted(executions),[('B',2024),('B',2026)])
            with closing(sqlite3.connect(source)) as con:
                rows=con.execute('SELECT company,amount FROM contributions ORDER BY company,amount').fetchall()
            self.assertEqual(rows,[(c,y) for c in 'ABCDE' for y in (2024,2026)])


if __name__=='__main__': unittest.main()
