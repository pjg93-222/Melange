"""Seal a generation of public pages, upload it, read it back, then mark it published.

Order is fixed: seal (pages, index.json, receipt.json, then seal.json) -> upload
every sealed asset -> download every asset again and compare size and SHA-256 ->
write publication.json last. A failure at any step leaves no publication.json,
so a staging directory without it is never a published generation.

Transports: LocalDirectoryTransport (tests, offline mirrors) and
GitHubDraftTransport (assets on a draft release; promotion and pointer changes
are separate, signed steps). Payroll observation pages keep their own path
(payroll_pages_publish.build + demand_publish.publish_directory).
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess

from demand_publish import GitHubCLI, PublicationError, canonical, sealed_inventory
from module_application_contracts import (MAX_MODULE_INDEX_BYTES, MAX_PAGE_BYTES, PAGED_MODULES,
                                         PAGES_CONTRACT, check_module_bytes, paged_module, split_pages)

REPOSITORY = 'pjg93-222/Melange'


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _read_source(data_root, relative):
    path = (data_root / relative)
    info = path.lstat()
    if path.is_symlink() or not path.is_file() or info.st_nlink != 1 or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise PublicationError('Module source must be a single-link regular file: ' + relative)
    if not path.resolve(strict=True).is_relative_to(data_root):
        raise PublicationError('Module source escapes the data root')
    return path.read_bytes()


def seal_generation(data_root, staging, *, release_tag, generation, modules=None, partitions=None,
                    page_bytes=MAX_PAGE_BYTES):
    """Check and page every selected module; write seal.json only when all of it holds."""
    data_root, staging = Path(data_root).resolve(strict=True), Path(staging).absolute()
    if type(generation) is not int or not 0 < generation <= 2**53 - 1:
        raise PublicationError('Invalid generation number')
    if staging.exists() or staging.is_relative_to(data_root):
        raise PublicationError('Staging must be a new directory outside the data root')
    selected = tuple(modules or PAGED_MODULES)
    partitions = partitions or {}
    plan = []
    for module_id in selected:  # check every source before writing anything
        module = paged_module(module_id)
        for partition in tuple(partitions.get(module_id, module.partitions)):
            raw = _read_source(data_root, module.path(partition))
            records = check_module_bytes(module, partition, raw)
            plan.append((module, partition, raw, records))
    staging.parent.mkdir(parents=True, exist_ok=True)
    staging.mkdir()
    index_modules, sources = {}, {}
    for module, partition, raw, records in plan:
        pages = []
        for page in split_pages(module, raw, page_bytes):
            digest = _sha(page)
            name = digest + '.' + module.format
            target = staging / name
            if not target.exists():
                with target.open('xb') as stream:
                    stream.write(page); stream.flush(); os.fsync(stream.fileno())
            pages.append({'asset': name, 'bytes': len(page), 'sha256': digest})
        entry = index_modules.setdefault(module.module_id, {'format': module.format,
            'partitionKey': module.partition_key, 'partitions': {}})
        entry['partitions'][partition] = {'source': module.path(partition), 'bytes': len(raw),
            'sha256': _sha(raw), 'records': records, 'pages': pages}
        sources.setdefault(module.module_id, {})[partition] = {'path': module.path(partition),
            'bytes': len(raw), 'sha256': _sha(raw)}
    for module, partition, raw, _records in plan:  # sources must not move while sealing
        if _sha(_read_source(data_root, module.path(partition))) != _sha(raw):
            raise PublicationError('Module source changed while sealing')
    index = {'schemaVersion': 1, 'appId': 'melange', 'contractId': PAGES_CONTRACT, 'repository': REPOSITORY,
             'releaseTag': release_tag, 'generation': generation, 'format': 'original-bytes-pages',
             'modules': index_modules}
    index_raw = canonical(index)
    if len(index_raw) > MAX_MODULE_INDEX_BYTES:
        raise PublicationError('Generation index exceeds its limit')
    receipt_raw = canonical({'schemaVersion': 1, 'releaseTag': release_tag, 'generation': generation,
                             'indexSha256': _sha(index_raw), 'sources': sources})
    (staging / 'index.json').write_bytes(index_raw)
    (staging / 'receipt.json').write_bytes(receipt_raw)
    assets = [{'asset': p.name, 'bytes': p.stat().st_size, 'sha256': _sha(p.read_bytes())}
              for p in sorted(staging.iterdir())]
    if len(assets) >= 1000:
        raise PublicationError('Generation needs more than one release')
    (staging / 'seal.json').write_bytes(canonical({'schemaVersion': 1, 'status': 'sealed',
        'repository': REPOSITORY, 'releaseTag': release_tag, 'generation': generation,
        'indexSha256': _sha(index_raw), 'assets': assets}))
    return index


class LocalDirectoryTransport:
    """Immutable local store: an existing name must already hold identical bytes."""
    def __init__(self, root):
        self.root = Path(root).absolute()

    def describe(self):
        return {'kind': 'local', 'root': str(self.root)}

    def put(self, name, path, expected):
        self.root.mkdir(parents=True, exist_ok=True)
        target = self.root / name
        if target.exists():
            if target.stat().st_size != expected['bytes'] or _sha(target.read_bytes()) != expected['sha256']:
                raise PublicationError('Remote asset already exists with different bytes: ' + name)
            return
        temporary = self.root / ('.' + name + '.part')
        shutil.copyfile(path, temporary)
        os.replace(temporary, target)

    def get(self, name, limit):
        with (self.root / name).open('rb') as stream:
            return stream.read(limit + 1)


class GitHubDraftTransport:
    """Assets on a draft release only; this class never publishes or promotes it."""
    def __init__(self, repository, tag, api=None):
        self.repository, self.tag, self.api = repository, tag, api or GitHubCLI()
        self.endpoint = 'repos/' + repository + '/releases'
        release = self.api.request(self.endpoint + '/tags/' + tag, missing_ok=True)
        if release is None:
            # A draft is invisible to the tags endpoint, so look it up by name first.
            release = next((r for r in self.api.request(self.endpoint + '?per_page=100') or []
                            if r.get('tag_name') == tag and r.get('draft')), None)
        if release is None:
            source = self.api.request('repos/' + repository + '/commits/main')
            release = self.api.request(self.endpoint, method='POST', data={'tag_name': tag,
                'target_commitish': source['sha'], 'name': tag, 'draft': True, 'prerelease': False,
                'make_latest': 'false', 'body': 'Draft public data generation; not published.'})
        if release.get('draft') is not True or type(release.get('id')) is not int:
            raise PublicationError('Generation assets go only to a draft release')
        self.release_id = release['id']

    def describe(self):
        return {'kind': 'github-draft', 'repository': self.repository, 'releaseTag': self.tag,
                'releaseId': self.release_id}

    def _assets(self):
        assets = []
        for page in range(1, 12):  # explicit pages: GitHub returns 100 at most per call
            batch = self.api.request(self.endpoint + '/' + str(self.release_id) + '/assets?per_page=100&page=' + str(page))
            assets.extend(batch)
            if len(batch) < 100:
                break
        return {a['name']: a for a in assets}

    def put(self, name, path, expected):
        current = self._assets().get(name)
        if current is None:
            self.api.upload(self.repository, self.tag, path)
        elif current.get('size') != expected['bytes']:
            raise PublicationError('Draft asset already exists with a different size: ' + name)

    def get(self, name, limit):
        asset = self._assets().get(name)
        if asset is None:
            raise PublicationError('Uploaded asset is missing on readback: ' + name)
        result = subprocess.run(['gh', 'api', self.endpoint + '/assets/' + str(asset['id']),
                                 '-H', 'Accept: application/octet-stream'], capture_output=True)
        if result.returncode:
            raise PublicationError('Asset readback failed: ' + name)
        return result.stdout[:limit + 1]


def publish_generation(data_root, staging, transport, *, release_tag, generation, modules=None,
                       partitions=None, page_bytes=MAX_PAGE_BYTES):
    """The one publication seam. Returns publication.json's value once every readback passed."""
    seal_generation(data_root, staging, release_tag=release_tag, generation=generation,
                    modules=modules, partitions=partitions, page_bytes=page_bytes)
    staging = Path(staging).absolute()
    seal_raw = (staging / 'seal.json').read_bytes()
    seal = json.loads(seal_raw)
    expected = {item['asset']: item for item in seal['assets']}
    expected['seal.json'] = {'asset': 'seal.json', 'bytes': len(seal_raw), 'sha256': _sha(seal_raw)}
    if {p.name for p in staging.iterdir()} != set(expected):
        raise PublicationError('Unlisted files in generation staging')
    for name, item in expected.items():
        transport.put(name, staging / name, item)
    for name, item in expected.items():
        raw = transport.get(name, item['bytes'])
        if len(raw) != item['bytes'] or _sha(raw) != item['sha256']:
            raise PublicationError('Readback differs from the sealed bytes: ' + name)
    publication = {'schemaVersion': 1, 'status': 'published', 'releaseTag': release_tag,
                   'generation': generation, 'indexSha256': seal['indexSha256'],
                   'sealSha256': _sha(seal_raw), 'transport': transport.describe(),
                   'verifiedAssets': len(expected), 'staging': str(staging)}
    with (staging / 'publication.json').open('xb') as stream:
        stream.write(canonical(publication)); stream.flush(); os.fsync(stream.fileno())
    return publication
