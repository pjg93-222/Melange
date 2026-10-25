"""Read the signed public payroll page index without hydrating the full corpus.

The existing source-observation validation and response shapes are retained.
Only requested pages enter the native cache; a lease protects each page while
its rows are checked and copied into the bounded response.
"""
import hashlib
from pathlib import Path
import re
import threading
from types import SimpleNamespace

from . import melange_public_data as legacy

p = legacy.p
KIND = 'melange.official-payroll-pages.v1'
MAX_INDEX_BYTES = 2 * 1024 ** 2
MAX_PAGE_BYTES = 16 * 1024 ** 2
MAX_PAGES = 16384
REPOSITORY = 'pjg93-222/Melange'
_CAPABILITY = object()


def validate_index(snapshot):
    """Metadata-only check used by native staging; never fetch a page here."""
    p.require(snapshot.app == 'melange' and snapshot.kind == KIND
              and set(snapshot.files) == set(snapshot.objects) == {'index', 'receipt'})
    raw = Path(snapshot.files['receipt']).read_bytes()
    index_raw = Path(snapshot.files['index']).read_bytes()
    p.require(len(raw) <= 1024 ** 2 and len(index_raw) <= MAX_INDEX_BYTES)
    p.require(hashlib.sha256(raw).hexdigest() == snapshot.objects['receipt']['sha256']
              and hashlib.sha256(index_raw).hexdigest() == snapshot.objects['index']['sha256'])
    receipt, index = p.strict_json(raw), p.strict_json(index_raw)
    # The old receipt still describes the complete projected corpus. Reuse its
    # strict, pure provenance checks; physical hydration is deliberately absent.
    from module_public_input_installers import _public_receipt
    p.require(type(receipt) is dict and type(receipt.get('output')) is dict)
    proxy = SimpleNamespace(app='melange', objects={
        'observations': receipt['output'], 'receipt': snapshot.objects['receipt']})
    _public_receipt(legacy, proxy, raw)
    legacy._exact(index, ('schemaVersion', 'appId', 'kind', 'repository', 'releaseTag',
                         'generation', 'receiptSha256', 'format', 'recordCounts', 'chunks'))
    p.require(type(index['schemaVersion']) is int and index['schemaVersion'] == 1
              and index['appId'] == 'melange' and index['kind'] == KIND
              and index['repository'] == REPOSITORY
              and type(index['releaseTag']) is str
              and re.fullmatch(r'module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?', index['releaseTag'])
              and type(index['generation']) is int and 0 < index['generation'] <= 2**53-1
              and index['receiptSha256'] == hashlib.sha256(raw).hexdigest()
              and index['format'] == 'strict-utf8-ndjson'
              and index['recordCounts'] == receipt['recordCounts'])
    p.require(type(index['chunks']) is list and 0 < len(index['chunks']) <= MAX_PAGES)
    counts = dict.fromkeys(legacy.ROLES, 0)
    seen, assets, size = set(), set(), 0
    for chunk in index['chunks']:
        legacy._exact(chunk, ('id', 'sha256', 'bytes', 'asset', 'selectors'))
        p._hash(chunk['sha256'])
        p.require(type(chunk['id']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,127}', chunk['id'])
                  and chunk['id'] not in seen and chunk['asset'] == chunk['sha256'] + '.ndjson'
                  and chunk['asset'] not in assets)
        seen.add(chunk['id']); assets.add(chunk['asset'])
        legacy._int(chunk['bytes'], MAX_PAGE_BYTES, 1)
        legacy._exact(chunk['selectors'], ('sourceRole', 'start', 'count'))
        select = chunk['selectors']; role = select['sourceRole']
        p.require(type(role) is str and role in counts)
        legacy._int(select['start'], legacy.MAX_RECORDS)
        legacy._int(select['count'], legacy.MAX_RECORDS, 1)
        p.require(select['start'] == counts[role], 'Public pages have a gap or overlap')
        counts[role] += select['count']; size += chunk['bytes']
    p.require(counts == receipt['recordCounts'] and size == receipt['output']['bytes'],
              'Public page totals differ from the projection receipt')
    return index, receipt, raw


class PagedPublicDataCatalogue:
    def __init__(self, capability, snapshot, source, *, cache=None, cancelled=lambda: False):
        p.require(capability is _CAPABILITY and not cancelled())
        index, receipt, raw = validate_index(snapshot)
        p.require(type(source) is dict and source.get('appId') == 'melange'
                  and str(source.get('repository', '')).lower() == REPOSITORY.lower()
                  and source.get('releaseTag') == index['releaseTag']
                  and source.get('catalogSequence') == index['generation'])
        self._lock = threading.Lock()
        self._closed = False
        self._receipt_raw = raw
        self.revision = index['receiptSha256']
        self._counts = index['recordCounts']
        self._documents = legacy._manifest(receipt['sourceManifest'])
        self._pages = {role: [c for c in index['chunks'] if c['selectors']['sourceRole'] == role]
                       for role in legacy.ROLES}
        root = Path(source['cacheRoot'])
        p.require(root.is_absolute() and root.is_dir())
        # Preparation is a read-only native handoff. Even mkdir would invalidate
        # its directory stamps, so materialize the mutable cache on first query.
        self._cache_root, self._release_tag = root / 'pages', index['releaseTag']
        self._cache = cache

    def _check(self):
        p.require(not self._closed, 'Public data is unavailable')

    def catalogue(self):
        with self._lock:
            self._check()
            return {'schemaVersion': 1, 'status': 'available', 'revision': self.revision,
                'sources': [{'id': role, 'records': self._counts[role]} for role in legacy.ROLES],
                'coverage': {'sourceNativeObservations': True, 'fullApplication': False}}

    def provenance(self):
        with self._lock:
            self._check()
            return p.strict_json(self._receipt_raw)

    def observations(self, source, offset=0, limit=100, *, revision=None):
        p.require(type(source) is str and source in legacy.ROLES)
        legacy._int(offset, self._counts[source])
        legacy._int(limit, 200, 1)
        p.require(revision is None or revision == self.revision,
                  'Public data revision changed; refresh the catalogue')
        with self._lock:
            self._check()
            end = min(offset + limit, self._counts[source])
            selected = [c for c in self._pages[source] if c['selectors']['start'] < end
                        and c['selectors']['start'] + c['selectors']['count'] > offset]
            rows = []
            if selected and self._cache is None:
                from .demand_data import ChunkCache, GitHubReleaseFetcher
                self._cache = ChunkCache(self._cache_root, max_bytes=1024 ** 3,
                    fetch=GitHubReleaseFetcher(REPOSITORY, self._release_tag))
            # One lease at a time permits even a broad sequence of page requests
            # to honor the cap. No complete corpus or second snapshot is built.
            for chunk in selected:
                with self._cache.acquire(chunk) as filename:
                    h, size, count, seen = hashlib.sha256(), 0, 0, set()
                    with Path(filename).open('rb') as stream:
                        while True:
                            line = stream.readline(legacy.MAX_LINE + 1)
                            if not line:
                                break
                            size += len(line); count += 1; h.update(line)
                            p.require(line.endswith(b'\n') and len(line) <= legacy.MAX_LINE
                                      and size <= chunk['bytes'] and count <= chunk['selectors']['count'])
                            value = p.strict_json(line)
                            p.require(legacy._row(value, self._documents) == source
                                      and value['recordId'] not in seen)
                            seen.add(value['recordId'])
                            ordinal = chunk['selectors']['start'] + count - 1
                            if offset <= ordinal < end:
                                rows.append(value)
                    p.require(size == chunk['bytes'] and h.hexdigest() == chunk['sha256']
                              and count == chunk['selectors']['count'], 'Public page integrity failed')
            p.require(len(rows) == end - offset)
            following = offset + len(rows)
            return {'schemaVersion': 1, 'revision': self.revision, 'source': source, 'offset': offset,
                'limit': limit, 'total': self._counts[source], 'records': rows,
                'nextOffset': following if following < self._counts[source] else None}

    def close(self):
        with self._lock:
            self._closed = True


def prepare_public_pages(snapshot, source, *, cancelled=lambda: False, cache=None):
    from module_data_snapshot import Snapshot
    p.require(type(snapshot) is Snapshot)
    return PagedPublicDataCatalogue(_CAPABILITY, snapshot, source, cancelled=cancelled, cache=cache)
