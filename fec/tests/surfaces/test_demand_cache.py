import hashlib
import multiprocessing
from pathlib import Path
import tempfile
import threading
import time
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'surfaces'))
from demand_data import ChunkCache, CacheError, CacheCapacityError


def spec(data):
    sha = hashlib.sha256(data).hexdigest()
    return {'id': sha, 'asset': sha + '.bin', 'sha256': sha, 'bytes': len(data), 'selectors': {}}


def competing(root, ready, result):
    ready.set()
    try:
        with ChunkCache(root, 8, lambda c, out: out.write(b'bbbbbbbb'), lock_timeout=.15).acquire(spec(b'bbbbbbbb')):
            result.put('acquired')
    except CacheError:
        result.put('blocked')


class CacheTests(unittest.TestCase):
    def test_cold_warm_and_lru_budget(self):
        with tempfile.TemporaryDirectory() as root:
            calls = []
            values = {spec(v)['sha256']: v for v in (b'aaaa', b'bbbb', b'cccc')}
            cache = ChunkCache(root, 8, lambda c, out: (calls.append(c['sha256']), out.write(values[c['sha256']])))
            for value in (b'aaaa', b'bbbb', b'aaaa', b'cccc'):
                with cache.acquire(spec(value)) as path:
                    self.assertEqual(path.read_bytes(), value)
                time.sleep(.005)
            self.assertEqual(len(calls), 3)
            self.assertFalse((Path(root) / (spec(b'bbbb')['sha256'] + '.blob')).exists())
            self.assertLessEqual(sum(p.stat().st_size for p in Path(root).glob('*.blob')), 8)

    def test_corruption_short_oversized_interrupted_never_installed(self):
        for kind in ('wrong', 'short', 'oversized', 'interrupted'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as root:
                def fetch(chunk, output):
                    output.write({'wrong': b'zzzz', 'short': b'a', 'oversized': b'aaaaa', 'interrupted': b'aa'}[kind])
                    if kind == 'interrupted':
                        raise OSError('disconnected')
                with self.assertRaises((CacheError, OSError)):
                    with ChunkCache(root, 4, fetch).acquire(spec(b'aaaa')):
                        pass
                self.assertFalse(list(Path(root).glob('*.blob')))
                self.assertFalse(list(Path(root).glob('*.part')))

    def test_offline_hit_and_corrupt_cache_refetched(self):
        with tempfile.TemporaryDirectory() as root:
            c = spec(b'aaaa')
            with ChunkCache(root, 4, lambda c, out: out.write(b'aaaa')).acquire(c):
                pass
            with ChunkCache(root, 4).acquire(c) as path:
                self.assertEqual(path.read_bytes(), b'aaaa')
            path.write_bytes(b'bad!')
            with self.assertRaises(CacheError):
                with ChunkCache(root, 4).acquire(c):
                    pass

    def test_capacity_is_aggregate_and_no_download(self):
        with tempfile.TemporaryDirectory() as root:
            def fail(*args):
                self.fail('download attempted')
            with self.assertRaises(CacheCapacityError):
                with ChunkCache(root, 5, fail).acquire_many([spec(b'aaaa'), spec(b'bbbb')]):
                    pass

    def test_other_process_cannot_evict_in_use(self):
        with tempfile.TemporaryDirectory() as root:
            ctx = multiprocessing.get_context('spawn')
            ready, result = ctx.Event(), ctx.Queue()
            with ChunkCache(root, 8, lambda c, out: out.write(b'aaaaaaaa')).acquire(spec(b'aaaaaaaa')) as path:
                proc = ctx.Process(target=competing, args=(root, ready, result))
                proc.start()
                self.assertTrue(ready.wait(10))
                self.assertEqual(result.get(timeout=10), 'blocked')
                proc.join(10)
                self.assertEqual(path.read_bytes(), b'aaaaaaaa')

    def test_foreign_files_and_links_preserved(self):
        with tempfile.TemporaryDirectory() as root:
            foreign = Path(root) / 'keep.txt'
            foreign.write_text('keep')
            with self.assertRaises(CacheError):
                with ChunkCache(root, 4, lambda c, out: out.write(b'aaaa')).acquire(spec(b'aaaa')):
                    pass
            self.assertEqual(foreign.read_text(), 'keep')

    def test_cache_never_exceeds_cap_under_concurrent_download_and_read(self):
        """Cache bytes stay at or under the cap at every sampled moment.

        ChunkCache holds one cross-process lock for each whole acquire (download,
        verification and the caller's read), so the four workers interleave their
        page holds rather than overlap them; the sampler thread runs unlocked.
        """
        cap, block = 64, 4
        values = [bytes([65 + n]) * (8 + 4 * (n % 3)) for n in range(12)]
        with tempfile.TemporaryDirectory() as root:
            observed, stop = [0], threading.Event()
            def used():
                total = 0
                for path in Path(root).iterdir():
                    if path.name != 'cache.lock':
                        try:
                            total += path.stat().st_size
                        except OSError:
                            pass
                observed[0] = max(observed[0], total)
            def fetch(chunk, output):
                raw = next(v for v in values if spec(v)['sha256'] == chunk['sha256'])
                for start in range(0, len(raw), block):
                    output.write(raw[start:start + block]); output.stream.flush(); used()
            def sampler():
                while not stop.is_set():
                    used()
            def worker(offset):
                try:
                    cache = ChunkCache(root, cap, fetch, lock_timeout=30)
                    for n in range(24):
                        value = values[(offset + n * 5) % len(values)]
                        with cache.acquire(spec(value)) as path:
                            used()
                            if path.read_bytes() != value:
                                raise AssertionError('wrong bytes for a leased page')
                except Exception as exc:  # a worker thread's failure must fail the test
                    errors.append(exc)
            watcher = threading.Thread(target=sampler); watcher.start()
            errors = []
            threads = [threading.Thread(target=worker, args=(n,)) for n in range(4)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(120)
            stop.set(); watcher.join(10)
            used()
            self.assertFalse(any(thread.is_alive() for thread in threads))
            self.assertEqual(errors, [])
            self.assertGreater(observed[0], 0)
            self.assertLessEqual(observed[0], cap)
            print('max observed cache bytes', observed[0], 'cap', cap)

    def test_lease_blocks_eviction_of_in_use_page_by_another_reader(self):
        with tempfile.TemporaryDirectory() as root:
            held, result = threading.Event(), []
            release = threading.Event()
            def holder():
                with ChunkCache(root, 8, lambda c, out: out.write(b'aaaaaaaa')).acquire(spec(b'aaaaaaaa')) as path:
                    held.set(); release.wait(10); result.append(path.read_bytes())
            thread = threading.Thread(target=holder); thread.start()
            self.assertTrue(held.wait(10))
            with self.assertRaisesRegex(CacheError, 'busy'):
                with ChunkCache(root, 8, lambda c, out: out.write(b'bbbbbbbb'), lock_timeout=.2).acquire(spec(b'bbbbbbbb')):
                    pass
            release.set(); thread.join(10)
            self.assertEqual(result, [b'aaaaaaaa'])

    def test_corrupt_download_is_refused_and_reported_missing(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaisesRegex(CacheError, 'verification'):
                with ChunkCache(root, 8, lambda c, out: out.write(b'zzzz')).acquire(spec(b'aaaa')):
                    pass
            with self.assertRaisesRegex(CacheError, 'not cached'):
                with ChunkCache(root, 8).acquire(spec(b'aaaa')):
                    pass


if __name__ == '__main__':
    unittest.main()
