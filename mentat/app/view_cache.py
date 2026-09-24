"""Bounded, single-flight cache for read-only, dependency-keyed UI payloads."""
from collections import OrderedDict
import json
from pathlib import Path
import threading
import time


def file_signature(paths):
    result = []
    for path in sorted(set(map(Path, paths)), key=str):
        try:
            stat = path.stat()
            result.append((str(path.resolve()), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size))
        except FileNotFoundError:
            result.append((str(path.absolute()), None, None, None))
    return tuple(result)


class ViewCache:
    def __init__(self, entries=32, max_bytes=64 * 1024 * 1024):
        self.entries, self.max_bytes = entries, max_bytes
        self.values, self.pending = OrderedDict(), set()
        self.condition = threading.Condition()
        self.bytes = self.hits = self.misses = 0

    def get(self, key, build):
        deadline = time.monotonic() + 120
        with self.condition:
            while key in self.pending:
                left = deadline - time.monotonic()
                if left <= 0 or not self.condition.wait(left):
                    raise ValueError('This view is still being prepared. Retry shortly.')
            if key in self.values:
                self.hits += 1
                encoded = self.values[key]
                self.values.move_to_end(key)
                # Each caller owns its object; server provenance annotations
                # and client-specific changes cannot poison the shared result.
                return json.loads(encoded)
            self.pending.add(key)
            self.misses += 1
        try:
            result = build()
            encoded = json.dumps(result, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
            with self.condition:
                if len(encoded) <= self.max_bytes:
                    while self.values and (len(self.values) >= self.entries or self.bytes + len(encoded) > self.max_bytes):
                        self.bytes -= len(self.values.popitem(last=False)[1])
                    self.values[key] = encoded
                    self.bytes += len(encoded)
            return result
        finally:
            with self.condition:
                self.pending.discard(key)
                self.condition.notify_all()

    def clear(self):
        with self.condition:
            self.values.clear()
            self.bytes = self.hits = self.misses = 0

    def info(self):
        with self.condition:
            return {'entries':len(self.values), 'bytes':self.bytes, 'hits':self.hits,
                    'misses':self.misses, 'in_progress':len(self.pending)}
