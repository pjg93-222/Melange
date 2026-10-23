"""Verified immutable chunks in a bounded, process-safe local cache.

No application roots are modified. A lease holds the cache lock for the whole
query, so another process cannot evict its files. Downloads count against the
same byte budget as installed chunks. All network locations derive from the
application's trusted repository and a validated immutable release tag.
"""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import re
import stat
import time
import urllib.parse
import urllib.request
import uuid

DEFAULT_CACHE_BYTES = 1024 ** 3
MAX_CHUNK_BYTES = 64 * 1024 ** 2
REPOSITORIES = frozenset(('pjg93-222/melange', 'pjg93-222/mentat'))
SHA = re.compile(r'[a-f0-9]{64}')
ASSET = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,179}')
TAG = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,159}')


class CacheError(ValueError):
    pass


class CacheCapacityError(CacheError):
    pass


def regular(path, directory=False):
    info = Path(path).lstat()
    if (stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400
            or not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
            or (not directory and info.st_nlink != 1)):
        raise CacheError('Cache path is not a private regular file or directory')
    return info


def safe_directory(path):
    path = Path(path).absolute()
    # Verify ancestors before mkdir; never follow a pre-existing junction.
    for parent in reversed((path, *path.parents)):
        if parent.exists():
            regular(parent, True)
        else:
            parent.mkdir()
            regular(parent, True)
    return path


def descriptor(chunk):
    if (not isinstance(chunk, dict) or not SHA.fullmatch(str(chunk.get('sha256', '')))
            or type(chunk.get('bytes')) is not int or not 0 < chunk['bytes'] <= MAX_CHUNK_BYTES
            or not ASSET.fullmatch(str(chunk.get('asset', '')))
            or chunk['asset'] in ('.', '..')):
        raise CacheError('Invalid immutable chunk descriptor')
    return chunk


def file_digest(path):
    before = regular(path)
    with Path(path).open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise CacheError('Cache file changed while opening')
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        after = os.fstat(stream.fileno())
    current = regular(path)
    stamp = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    if stamp(before) != stamp(after) or stamp(after) != stamp(current):
        raise CacheError('Cache file changed during verification')
    return digest


class _BoundedWriter:
    def __init__(self, stream, expected):
        self.stream, self.expected, self.count = stream, expected, 0
        self.digest = hashlib.sha256()

    def write(self, block):
        if self.count + len(block) > self.expected:
            raise CacheError('Download exceeded its declared byte length')
        written = self.stream.write(block)
        if written != len(block):
            raise CacheError('Incomplete cache write')
        self.count += written
        self.digest.update(block)
        return written


class _GitHubRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urllib.parse.urlsplit(newurl)
        if (parsed.scheme != 'https' or parsed.hostname not in
                ('github.com', 'release-assets.githubusercontent.com', 'objects.githubusercontent.com')
                or parsed.port not in (None, 443) or parsed.username or parsed.password or parsed.fragment):
            raise CacheError('Release redirected outside the approved asset hosts')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class GitHubReleaseFetcher:
    """Public data only: publisher credentials never enter the desktop client."""
    def __init__(self, repository, release_tag, timeout=60):
        if not isinstance(repository, str) or repository.lower() not in REPOSITORIES:
            raise CacheError('Unapproved dataset repository')
        if not isinstance(release_tag, str) or not TAG.fullmatch(release_tag):
            raise CacheError('Invalid immutable data release tag')
        self.repository, self.release_tag, self.timeout = repository, release_tag, timeout

    def __call__(self, chunk, target):
        descriptor(chunk)
        url = 'https://github.com/{}/releases/download/{}/{}'.format(
            self.repository, urllib.parse.quote(self.release_tag, safe=''),
            urllib.parse.quote(chunk['asset'], safe=''))
        request = urllib.request.Request(url, headers={'User-Agent': 'Melange-Mentat-DemandData/1',
                                                     'Accept': 'application/octet-stream'})
        opener = urllib.request.build_opener(_GitHubRedirects())
        with opener.open(request, timeout=self.timeout) as response:
            length = response.headers.get('Content-Length')
            if length is not None and int(length) != chunk['bytes']:
                raise CacheError('Release asset length differs from its manifest')
            while True:
                block = response.read(min(1024 ** 2, chunk['bytes'] + 1))
                if not block:
                    break
                target.write(block)


class ChunkCache:
    def __init__(self, root, max_bytes=DEFAULT_CACHE_BYTES, fetch=None, lock_timeout=60):
        if type(max_bytes) is not int or max_bytes <= 0 or max_bytes > 64 * 1024 ** 3:
            raise CacheError('Cache budget must be a positive bounded integer')
        self.root = safe_directory(root)
        self.max_bytes, self.fetch, self.lock_timeout = max_bytes, fetch, lock_timeout

    @contextmanager
    def _locked(self):
        regular(self.root, True)
        lock_path = self.root / 'cache.lock'
        # x+b refuses an existing path; pre-existing lock must be a single-link regular file.
        try:
            stream = lock_path.open('x+b')
            stream.write(b'0')
            stream.flush()
        except FileExistsError:
            regular(lock_path)
            stream = lock_path.open('r+b')
        try:
            expected = regular(lock_path)
            opened = os.fstat(stream.fileno())
            if (expected.st_dev, expected.st_ino) != (opened.st_dev, opened.st_ino):
                raise CacheError('Cache lock changed')
            deadline = time.monotonic() + self.lock_timeout
            while True:
                try:
                    stream.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise CacheError('Cache is busy with another query; retry shortly')
                    time.sleep(0.05)
            try:
                yield
            finally:
                stream.seek(0)
                if os.name == 'nt':
                    import msvcrt
                    msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        finally:
            stream.close()

    def _owned(self):
        files = []
        for path in self.root.iterdir():
            if path.name == 'cache.lock':
                continue
            if not (re.fullmatch(r'[a-f0-9]{64}\.blob', path.name)
                    or re.fullmatch(r'[a-f0-9]{32}\.part', path.name)):
                raise CacheError('Unexpected cache contents; use a dedicated empty cache directory')
            info = regular(path)
            files.append((path, info))
        return files

    def _trim(self, needed, protected):
        files = self._owned()
        # The global lease proves no part belongs to a live downloader now.
        for path, _ in files:
            if path.suffix == '.part':
                regular(path)
                path.unlink()
        files = [(path, info) for path, info in files if path.suffix == '.blob']
        used = sum(info.st_size for _, info in files)
        for path, info in sorted(files, key=lambda item: item[1].st_mtime_ns):
            if used + needed <= self.max_bytes:
                break
            if path.stem not in protected:
                regular(path)
                path.unlink()
                used -= info.st_size
        if used + needed > self.max_bytes:
            raise CacheCapacityError('Selected data exceeds the local cache budget')

    @contextmanager
    def acquire_many(self, chunks):
        chunks = [descriptor(dict(chunk)) for chunk in chunks]
        unique = {}
        for chunk in chunks:
            previous = unique.setdefault(chunk['sha256'], chunk)
            if previous['bytes'] != chunk['bytes']:
                raise CacheError('Conflicting chunk sizes')
        if sum(chunk['bytes'] for chunk in unique.values()) > self.max_bytes:
            raise CacheCapacityError('This query needs more data than the cache cap; narrow the filters')
        with self._locked():
            protected = set(unique)
            missing = []
            for sha, chunk in unique.items():
                path = self.root / (sha + '.blob')
                if path.exists():
                    if regular(path).st_size != chunk['bytes'] or file_digest(path) != sha:
                        regular(path)
                        path.unlink()
                        missing.append(chunk)
                else:
                    missing.append(chunk)
            self._trim(sum(chunk['bytes'] for chunk in missing), protected)
            for chunk in missing:
                if self.fetch is None:
                    raise CacheError('Requested data is not cached and no download source is configured')
                temporary = self.root / (uuid.uuid4().hex + '.part')
                try:
                    with temporary.open('xb') as stream:
                        writer = _BoundedWriter(stream, chunk['bytes'])
                        self.fetch(chunk, writer)
                        if writer.count != chunk['bytes'] or writer.digest.hexdigest() != chunk['sha256']:
                            raise CacheError('Downloaded data failed size or SHA-256 verification')
                        stream.flush()
                        os.fsync(stream.fileno())
                    regular(temporary)
                    os.replace(temporary, self.root / (chunk['sha256'] + '.blob'))
                finally:
                    if temporary.exists():
                        regular(temporary)
                        temporary.unlink()
            paths = [self.root / (chunk['sha256'] + '.blob') for chunk in chunks]
            for path in paths:
                os.utime(path, None)
            yield paths

    @contextmanager
    def acquire(self, chunk):
        with self.acquire_many([chunk]) as paths:
            yield paths[0]
