"""Publish sealed dataset assets as immutable public GitHub prereleases.

Only a closed, hash-bound publication.json inventory is uploaded. The GitHub
CLI supplies server-side credentials from its existing credential store.
Current pointers are a separate final operation after all assets verify.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

REPOSITORIES = {'pjg93-222/melange', 'pjg93-222/mentat'}


class PublicationError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _hash(path):
    info = path.lstat()
    if not path.is_file() or path.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400 or info.st_nlink != 1:
        raise PublicationError('Publication assets must be single-link regular files')
    with path.open('rb') as stream:
        result = hashlib.file_digest(stream, 'sha256').hexdigest()
    after = path.stat()
    if (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
        raise PublicationError('Staged asset changed during hashing')
    return result


def sealed_inventory(staging, repository, tag):
    staging = Path(staging).absolute()
    for p in (staging, *staging.parents):
        info = p.lstat()
        if p.is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise PublicationError('Publication roots cannot traverse reparse points')
    if repository.lower() not in REPOSITORIES or not re.fullmatch(r'(?:module-)?data-[a-z0-9][a-z0-9._-]{1,150}', tag):
        raise PublicationError('Unapproved repository or data release tag')
    path = staging / 'publication.json'
    _hash(path)
    raw = path.read_bytes()
    if len(raw) > 4 * 1024 ** 2:
        raise PublicationError('Publication inventory too large')
    manifest = json.loads(raw)
    if (manifest.get('schemaVersion') != 1 or manifest.get('status') != 'complete'
            or manifest.get('repository', '').lower() != repository.lower() or manifest.get('releaseTag') != tag
            or not isinstance(manifest.get('assets'), list) or not 1 <= len(manifest['assets']) < 1000):
        raise PublicationError('A complete release-bound inventory is required')
    expected = {}
    for item in manifest['assets']:
        name = item.get('asset', '')
        if (not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,179}', name)
                or name == 'publication.json' or name in expected
                or type(item.get('bytes')) is not int or not 0 < item['bytes'] < 2 * 1024 ** 3
                or not re.fullmatch(r'[a-f0-9]{64}', str(item.get('sha256', '')))):
            raise PublicationError('Invalid publication asset inventory')
        file = staging / name
        if _hash(file) != item['sha256'] or file.stat().st_size != item['bytes']:
            raise PublicationError('Staged bytes differ from the sealed inventory')
        expected[name] = item
    if {p.name for p in staging.iterdir()} != set(expected) | {'publication.json'}:
        raise PublicationError('Unlisted files in publication staging directory')
    expected['publication.json'] = {'asset': 'publication.json', 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    return staging, expected, hashlib.sha256(raw).hexdigest()


class GitHubCLI:
    def request(self, endpoint, method='GET', data=None, missing_ok=False):
        command = ['gh', 'api', endpoint, '--method', method, '-H', 'Accept: application/vnd.github+json']
        if data is not None:
            command += ['--input', '-']
        result = subprocess.run(command, input=None if data is None else canonical(data), capture_output=True)
        if result.returncode:
            if missing_ok and b'HTTP 404' in result.stderr:
                return None
            # CLI diagnostics can contain request internals; don't copy them to clients/logs.
            raise PublicationError('GitHub publication request failed; inspect authenticated CLI status')
        return json.loads(result.stdout) if result.stdout.strip() else None

    def upload(self, repository, tag, path):
        result = subprocess.run(['gh', 'release', 'upload', tag, str(path), '--repo', repository], capture_output=True)
        if result.returncode:
            raise PublicationError('Immutable asset upload failed; completed uploads remain retryable')

    def verify(self, repository, asset, expected):
        # Read back the exact draft asset via authenticated API before publication.
        process = subprocess.Popen(['gh', 'api', 'repos/' + repository + '/releases/assets/' + str(asset['id']),
                                    '-H', 'Accept: application/octet-stream'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        count, digest = 0, hashlib.sha256()
        try:
            while True:
                block = process.stdout.read(1024 ** 2)
                if not block:
                    break
                count += len(block)
                if count > expected['bytes']:
                    raise PublicationError('Uploaded asset exceeds its sealed size')
                digest.update(block)
            if process.wait(timeout=60) or count != expected['bytes'] or digest.hexdigest() != expected['sha256']:
                raise PublicationError('Uploaded asset failed byte-for-byte verification')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            process.stdout.close()


def publish_directory(staging, repository, tag, promote_callback=None, api=None):
    staging, expected, fingerprint = sealed_inventory(staging, repository, tag)
    api = api or GitHubCLI()
    repo = 'repos/' + repository
    identity = 'Sealed application dataset publication ' + fingerprint
    release = api.request(repo + '/releases/tags/' + tag, missing_ok=True)
    if release is None:
        source = api.request(repo + '/commits/main')
        release = api.request(repo + '/releases', method='POST', data={
            'tag_name': tag, 'target_commitish': source['sha'], 'name': tag, 'body': identity,
            'draft': True, 'prerelease': True, 'make_latest': 'false'})
    if (release.get('body') != identity or release.get('tag_name') != tag
            or release.get('prerelease') is not True or type(release.get('id')) is not int):
        raise PublicationError('Existing release belongs to another publication; never overwrite it')
    release_id = release['id']
    endpoint = repo + '/releases/' + str(release_id)
    # Explicit pagination avoids treating GitHub's first 30 assets as the whole release.
    def assets():
        result = []
        for page in range(1, 12):
            batch = api.request(endpoint + '/assets?per_page=100&page=' + str(page))
            result.extend(batch)
            if len(batch) < 100:
                break
        if len(result) > 1000 or len({a['name'] for a in result}) != len(result):
            raise PublicationError('Ambiguous remote asset inventory')
        return {a['name']: a for a in result}
    remote = assets()
    if not set(remote) <= set(expected):
        raise PublicationError('Release has foreign assets; refusing adoption')
    for name, item in expected.items():
        if name not in remote:
            if not release.get('draft'):
                raise PublicationError('Published immutable release is incomplete')
            if _hash(staging / name) != item['sha256']:
                raise PublicationError('Staged asset changed before upload')
            api.upload(repository, tag, staging / name)
            remote = assets()
        asset = remote[name]
        if asset.get('size') != item['bytes'] or asset.get('state') != 'uploaded':
            raise PublicationError('Uploaded asset metadata is incomplete')
        api.verify(repository, asset, item)
    sealed_inventory(staging, repository, tag)
    if release.get('draft'):
        release = api.request(endpoint, method='PATCH', data={'draft': False, 'prerelease': True, 'make_latest': 'false'})
    if release.get('draft') or release.get('id') != release_id:
        raise PublicationError('Publication was not confirmed')
    if promote_callback is not None:
        promote_callback({'repository': repository, 'releaseTag': tag, 'releaseId': release_id,
                          'inventorySha256': fingerprint})
    return {'repository': repository, 'releaseTag': tag, 'releaseId': release_id,
            'inventorySha256': fingerprint, 'verifiedAssets': len(expected), 'published': True}
