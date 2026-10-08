"""Cross-process owner lock: one collector process per cache directory (discover and collect must never overlap).

The OS lock (msvcrt byte-range lock on Windows, flock elsewhere) is released automatically if the owner dies, so it can never go
stale. ``owner.json`` beside it is informational (pid, argv, start time) for ``osc status``.
"""
from __future__ import annotations
import json, os, sys
from pathlib import Path

from .util import atomic_write_json, utc_now


class LockHeld(RuntimeError):
    pass


class OwnerLock:
    def __init__(self, directory, name='collector'):
        self.dir = Path(directory)
        self.lock_path = self.dir / f'{name}.lock'
        self.info_path = self.dir / f'{name}.owner.json'
        self._fh = None

    def acquire(self, **info):
        self.dir.mkdir(parents=True, exist_ok=True)
        fh = open(self.lock_path, 'a+b')
        try:
            if sys.platform == 'win32':
                import msvcrt
                fh.seek(0)
                if not fh.read(1):
                    fh.write(b'L')
                    fh.flush()
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            fh.close()
            raise LockHeld(f'another osc process owns {self.lock_path}: {self.owner()}') from exc
        self._fh = fh
        atomic_write_json(self.info_path, {'pid': os.getpid(), 'acquired_utc': utc_now(), 'argv': sys.argv, **info})
        return self

    def owner(self):
        try:
            return json.loads(self.info_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {}

    def release(self):
        if self._fh is None:
            return
        try:
            if sys.platform == 'win32':
                import msvcrt
                self._fh.seek(0)
                msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
        finally:
            self._fh.close()
            self._fh = None
            try:
                atomic_write_json(self.info_path, {**self.owner(), 'released_utc': utc_now()})
            except OSError:
                pass

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *exc):
        self.release()
