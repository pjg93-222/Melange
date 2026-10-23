import hashlib
import multiprocessing
from pathlib import Path
import tempfile
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


if __name__ == '__main__':
    unittest.main()
