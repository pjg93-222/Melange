"""Automatic data bootstrap is disabled until an exact compiled public plan exists.

The private component seam retains transport/recovery tests only. It is not an
application installer, a complete reader contract or a live-update mechanism.
Downloaded HTML/code/state/accounts cannot be authorized through this module.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import threading
import time
from types import MappingProxyType
import urllib.error
import urllib.request
import zipfile

SCHEMA = 'melange-desktop-data/v1'
REPOSITORIES = {'melange': 'pjg93-222/Melange', 'mentat': 'pjg93-222/Mentat'}
DEFAULT_API = 'https://api.github.com'
MARKER = '.melange-data-release.json'
EXTRACTING = 'extracting.json'  # in <state>/data-download while an extraction has started and not finished: {tag, manifestSha256}
BOOTSTRAP_TAG = 'melange-desktop-empty-workspace-v1'  # melange_bootstrap.WELCOME carries it; so does the progress page
STATE_PREFIX = '__state__/'
CHUNK, ATTEMPTS, RETRY_DELAY = 1 << 16, 4, 2.0
SPACE_MARGIN = 512 << 20
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
WINDOWS_DEVICE = re.compile(r'^(con|prn|aux|nul|conin\$|conout\$|com[0-9Â¹Â²Â³]|lpt[0-9Â¹Â²Â³])(\..*)?$', re.I)
# No reviewed public-only application plan/installer is compiled in this build.
# Neither downloaded metadata, settings nor inherited environment can fill it.
_COMPILED_PUBLIC_PLANS = MappingProxyType({})


class DataReleaseError(RuntimeError):
    pass


def ensure_app_data(app, data_root, state_root, repo, *, api_base=None, progress=None):
    """Production entry: fail closed before paths, markers, locks or network."""
    if _COMPILED_PUBLIC_PLANS.get(app) is None:
        return {'status': 'unsupported'}
    raise DataReleaseError('The compiled public input installer is unavailable')


def _check_url(url, insecure):
    if not url.startswith('https://') and not (insecure and url.startswith('http://')):
        raise DataReleaseError('Refusing non-HTTPS data release URL')


class _HttpsRedirects(urllib.request.HTTPRedirectHandler):
    """GitHub answers asset downloads with a redirect; urllib would follow one to plain http:// silently."""
    def __init__(self, insecure):
        self.insecure = insecure

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _check_url(newurl, self.insecure)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(url, accept, headers=None, insecure=False):
    _check_url(url, insecure)
    request = urllib.request.Request(url, headers={'Accept': accept, 'User-Agent': 'melange-desktop-data', **(headers or {})})
    return urllib.request.build_opener(_HttpsRedirects(insecure)).open(request, timeout=60)


def _read_json(url, limit, insecure):
    with _open(url, 'application/vnd.github+json' if '/repos/' in url else 'application/octet-stream', insecure=insecure) as response:
        body = response.read(limit + 1)
    if len(body) > limit:
        raise DataReleaseError('Data release metadata is too large')
    return body


def select_release(releases, app):
    prefix = 'data-%s-' % app
    found = [r for r in releases if isinstance(r, dict) and not r.get('draft') and str(r.get('tag_name', '')).startswith(prefix)]
    return max(found, key=lambda r: (r.get('published_at') or r.get('created_at') or '', r['tag_name'])) if found else None


def member_path(name):
    """A zip member as a relative POSIX path; absolute, drive-letter, '..' and empty segments are refused, and so are
    names Windows would alias or treat as a device (CON, NUL.txt, trailing dot or space, wildcard/control characters)."""
    text = name.replace('\\', '/')
    segments = text.split('/')
    if not text or text.startswith('/') or ':' in text or any(s in ('', '.', '..') for s in segments) or any(
            s != s.rstrip('. ') or WINDOWS_DEVICE.match(s) or any(c in '<>"|?*' or ord(c) < 32 for c in s) for s in segments):
        raise DataReleaseError('Refusing unsafe data archive member: %r' % name)
    return '/'.join(segments)


def is_bootstrap_page(path):
    path = Path(path)
    try:
        return path.is_file() and not path.is_symlink() and path.stat().st_size < 65536 and BOOTSTRAP_TAG in path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _regular(path, *, links=1):
    info = Path(path).lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != links
            or Path(path).is_symlink() or getattr(info, 'st_file_attributes', 0) & 0x400):
        raise DataReleaseError('An independent regular component file is required')
    return info


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns if os.name != 'nt' else None)


def _handle_stamp(stream):
    result = _stamp(os.fstat(stream.fileno()))
    if os.name != 'nt':
        return result
    # Windows st_ctime is creation time; use native ChangeTime to detect an
    # in-place rewrite even when the previous mtime/bytes are restored.
    import ctypes
    from ctypes import wintypes
    import msvcrt
    class BasicInformation(ctypes.Structure):
        _fields_ = [('CreationTime', ctypes.c_longlong), ('LastAccessTime', ctypes.c_longlong),
                    ('LastWriteTime', ctypes.c_longlong), ('ChangeTime', ctypes.c_longlong),
                    ('FileAttributes', wintypes.DWORD)]
    query = ctypes.WinDLL('kernel32', use_last_error=True).GetFileInformationByHandleEx
    query.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    query.restype = wintypes.BOOL
    info = BasicInformation()
    if (not query(msvcrt.get_osfhandle(stream.fileno()), 0, ctypes.byref(info), ctypes.sizeof(info))
            or info.FileAttributes & 0x400):
        raise DataReleaseError('Windows component change identity is unavailable')
    return result + (info.ChangeTime,)


def _path_stamp(path, *, links=1):
    before = _regular(path, links=links)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        if _stamp(before) != _stamp(os.fstat(stream.fileno())):
            raise DataReleaseError('Component path identity changed')
        result = _handle_stamp(stream)
        if (_stamp(_regular(path, links=links)) != _stamp(os.fstat(stream.fileno()))
                or _handle_stamp(stream) != result):
            raise DataReleaseError('Component path stamp changed')
        return result


def _parents(root, folder, *, create=False):
    current = root
    for part in ('', *folder.relative_to(root).parts):
        if part:
            current = current / part
        if create:
            current.mkdir(exist_ok=True)
        info = current.lstat()
        if (not stat.S_ISDIR(info.st_mode) or current.is_symlink()
                or getattr(info, 'st_file_attributes', 0) & 0x400):
            raise DataReleaseError('Component folders cannot contain reparse points')


def _checked_file(path, entry, identity=None, *, links=1):
    before = _regular(path, links=links)
    if identity is not None and (before.st_dev, before.st_ino) != identity:
        raise DataReleaseError('Owned component temporary changed')
    if before.st_size != entry['bytes']:
        raise DataReleaseError('Component bytes differ from the manifest')
    stamp = _path_stamp(path, links=links)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        opened = _handle_stamp(stream)
        if opened != stamp:
            raise DataReleaseError('Component file identity changed')
        digest, received = hashlib.sha256(), 0
        while chunk := stream.read(CHUNK):
            received += len(chunk)
            if received > entry['bytes']:
                raise DataReleaseError('Component file grew during verification')
            digest.update(chunk)
        if (_handle_stamp(stream) != opened
                or _path_stamp(path, links=links) != stamp
                or received != entry['bytes'] or digest.hexdigest() != entry['sha256']):
            raise DataReleaseError('Component file checksum or identity changed')
    return stamp


def _remove_owned(path, identity, *, links=1, stamp=None):
    try:
        info = _regular(path, links=links)
        if (info.st_dev, info.st_ino) == identity and (stamp is None or _path_stamp(path, links=links) == stamp):
            Path(path).unlink()
            return True
    except (OSError, DataReleaseError):
        pass  # Never delete a foreign replacement, link or reparse point.
    return False


def _component_member(relative):
    parts = relative.split('/')
    if (relative.startswith(STATE_PREFIX) or any(part.casefold() in
            {'accounts', 'accounts.sqlite3', 'accounts.sqlite', 'keys', 'keys.json', 'credentials'} for part in parts)
            or any(part.startswith('.melange-data-') or part.endswith('.data-release-part') for part in parts)
            or Path(relative).suffix.casefold() in {'.html', '.htm', '.js', '.mjs', '.cjs', '.py', '.pyc',
                '.exe', '.dll', '.ps1', '.bat', '.cmd', '.sh', '.pfx', '.pem'}):
        raise DataReleaseError('Code, account or state members are not public component inputs')


def _download(url, part, size, sha256, report, insecure):
    error = None
    for attempt in range(ATTEMPTS + 1):
        if os.path.lexists(part):
            _regular(part)
        have = part.stat().st_size if part.exists() else 0
        if have > size:
            part.unlink()
            have = 0
        if have == size:
            break
        if attempt == ATTEMPTS:
            raise DataReleaseError('Download incomplete for %s: %s' % (part.name, error or 'short response'))
        if attempt:
            time.sleep(RETRY_DELAY * attempt)
        try:
            with _open(url, 'application/octet-stream', {'Range': 'bytes=%d-' % have} if have else None, insecure) as response:
                if have and (response.status != 206 or not str(response.headers.get('Content-Range', '')).startswith('bytes %d-' % have)):
                    have = 0  # the server ignored the range: start over
                with part.open('ab' if have else 'wb') as out:
                    while chunk := response.read(CHUNK):
                        if have + len(chunk) > size:
                            raise DataReleaseError('Asset %s is larger than its manifest entry' % part.name)
                        out.write(chunk)
                        have += len(chunk)
                        report(have)
        except (OSError, HTTPException) as failure:
            error = failure
    if _sha256(part) != sha256:
        part.unlink()
        raise DataReleaseError('Checksum mismatch for %s; nothing was extracted' % part.name)


def _extract(archives, data, state, files, app):
    """Private component transport only; never replace original inputs or UI.

    All members are staged and hashed before any new target is published. This
    does not install application readers or grant whole-application readiness.
    """
    data = Path(data).absolute()
    _parents(data, data)
    plan, seen, stages, created = [], set(), [], []
    for archive, asset in archives:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if info.is_dir():
                    continue
                relative = member_path(info.filename)
                _component_member(relative)
                entry = files.get(relative)
                if entry is None or entry.get('asset', asset) != asset or info.file_size != entry['bytes']:
                    raise DataReleaseError('Archive member %s does not match the manifest' % relative)
                if relative in seen:
                    raise DataReleaseError('Archive member %s appears more than once' % relative)
                seen.add(relative)
                target = data.joinpath(*relative.split('/'))
                if type(entry.get('bytes')) is not int or entry['bytes'] < 0 or not re.fullmatch('[a-f0-9]{64}', str(entry.get('sha256'))):
                    raise DataReleaseError('Invalid component size or checksum')
                plan.append((archive, info, target, entry, relative))
    if len(seen) != len(files):
        raise DataReleaseError('Data release archives lack %d file(s) listed in the manifest' % (len(files) - len(seen)))
    plan.sort(key=lambda item: item[4])
    # Refuse a mismatched required original before staging any missing member.
    for _archive, _info, target, entry, _relative in plan:
        parent = target.parent
        while not parent.exists() and parent != data:
            parent = parent.parent
        _parents(data, parent)
        if os.path.lexists(target):
            _checked_file(target, entry)
    try:
        for archive, info, target, entry, relative in plan:
            if os.path.lexists(target):
                _checked_file(target, entry)
                continue
            _parents(data, target.parent, create=True)
            descriptor, name = tempfile.mkstemp(prefix='.melange-data-', suffix='.part', dir=target.parent)
            temporary = Path(name)
            opened = os.fstat(descriptor)
            identity = (opened.st_dev, opened.st_ino)
            stage = [temporary, target, entry, identity, None]
            stages.append(stage)
            digest, received = hashlib.sha256(), 0
            with os.fdopen(descriptor, 'wb') as out, zipfile.ZipFile(archive) as bundle, bundle.open(info) as source:
                while chunk := source.read(CHUNK):
                    received += len(chunk)
                    if received > entry['bytes']:
                        raise DataReleaseError('Component exceeds its declared bytes')
                    digest.update(chunk)
                    out.write(chunk)
                out.flush()
                os.fsync(out.fileno())
            if received != entry['bytes'] or digest.hexdigest() != entry['sha256']:
                raise DataReleaseError('Component does not match the manifest')
            stage[4] = _checked_file(temporary, entry, identity)
        for temporary, target, entry, identity, stamp in stages:
            _parents(data, target.parent)
            if _checked_file(temporary, entry, identity) != stamp:
                raise DataReleaseError('Completed component temporary changed')
            _replace(temporary, target, identity=identity, entry=entry)
            published = [target, entry, identity, None]
            created.append(published)
            published[3] = _checked_file(target, entry, identity)
        return len(stages), []
    except BaseException:
        for target, entry, identity, stamp in created:
            try:
                _parents(data, target.parent)
                current = _checked_file(target, entry, identity)
                if stamp is None or current == stamp:
                    _remove_owned(target, identity, stamp=current)
            except (OSError, DataReleaseError):
                pass
        raise
    finally:
        for temporary, _target, _entry, identity, stamp in stages:
            try:
                _parents(data, temporary.parent)
                _remove_owned(temporary, identity, stamp=stamp)
            except (OSError, DataReleaseError):
                pass


def _lock(path):
    """An OS lock on <state>/data-download/.lock (freed when the process ends); None while another launch holds it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, 'a+b')
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _unlock(handle):
    try:
        if os.name == 'nt':
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    handle.close()


def _free_bytes(path):
    return shutil.disk_usage(path).free


def _require_space(data, state, download, files):
    """Refuse before downloading when the zips plus everything still to extract do not fit (Melange: about 12 GB)."""
    to_state = to_data = 0
    for relative, entry in files.items():
        root, inner = (state, relative[len(STATE_PREFIX):]) if relative.startswith(STATE_PREFIX) else (data, relative)
        if not (root / inner).exists():
            if root is state:
                to_state += int(entry['bytes'])
            else:
                to_data += int(entry['bytes'])
    data.mkdir(parents=True, exist_ok=True)
    same = os.stat(data).st_dev == os.stat(state).st_dev
    for root, need in ([(state, download + to_state + to_data)] if same else [(state, download + to_state), (data, to_data)]):
        free = _free_bytes(root)
        if need + SPACE_MARGIN > free:
            raise DataReleaseError('Not enough free disk space for the starting data: about %.1f GB needed, %.1f GB free'
                                   % ((need + SPACE_MARGIN) / 1e9, free / 1e9))


def _ensure_component_data(app, data_root, state_root, repo, *, api_base=None, progress=None):
    """Private transport fixture seam, not production authority. Download, verify and extract the newest data release once. Returns a summary dict; raises DataReleaseError.
    A second launch (or process) while one download runs gets {'status': 'busy'} and touches nothing."""
    data, state = Path(data_root), Path(state_root)
    marker = data / MARKER
    if marker.exists():
        return {'status': 'component-present', 'tag': json.loads(marker.read_text(encoding='utf-8')).get('tag')}
    lock = _lock(state / 'data-download' / '.lock')
    if lock is None:
        return {'status': 'busy'}
    try:
        if marker.exists():  # the launch that held the lock finished meanwhile
            return {'status': 'component-present', 'tag': json.loads(marker.read_text(encoding='utf-8')).get('tag')}
        return _ensure_locked(app, data, state, repo, api_base, progress, marker)
    finally:
        _unlock(lock)


def _ensure_locked(app, data, state, repo, api_base, progress, marker):
    insecure = api_base is not None and api_base.rstrip('/') != DEFAULT_API
    report = progress or (lambda **_: None)
    report(phase='checking')
    base = '%s/repos/%s/releases' % ((api_base or DEFAULT_API).rstrip('/'), repo)
    extracting = state / 'data-download' / EXTRACTING  # lets launch() resume once Mentat's reports/ is partly written
    record = json.loads(extracting.read_text(encoding='utf-8')) if extracting.is_file() else {}
    resumed = record.get('tag')
    if resumed is None:
        releases = json.loads(_read_json(base + '?per_page=20', 4 << 20, insecure))
        release = select_release(releases if isinstance(releases, list) else [], app)
    else:  # an interrupted extraction finishes with its own release (looked up by tag); two releases are never mixed
        if not SAFE_NAME.match(str(resumed)):
            raise DataReleaseError('Unsupported data release tag')
        try:
            release = json.loads(_read_json('%s/tags/%s' % (base, resumed), 4 << 20, insecure))
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            release = None
        if not isinstance(release, dict) or release.get('draft') or release.get('tag_name') != resumed:
            raise DataReleaseError('The interrupted data release %s is no longer published' % resumed)
    if release is None:
        report(phase='none')
        return {'status': 'none'}
    tag = release['tag_name']
    if not SAFE_NAME.match(tag):
        raise DataReleaseError('Unsupported data release tag')
    urls = {a.get('name'): a.get('browser_download_url') for a in release.get('assets') or [] if isinstance(a, dict)}
    if not urls.get('manifest.json'):
        raise DataReleaseError('Data release %s has no manifest.json' % tag)
    raw = _read_json(urls['manifest.json'], 16 << 20, insecure)
    digest = hashlib.sha256(raw).hexdigest()
    if resumed is not None and record.get('manifestSha256') != digest:  # same tag, new manifest: never mix two generations
        report(phase='error', error='manifest_changed: data release %s was replaced after its extraction started' % tag)
        return {'status': 'error', 'reason': 'manifest_changed', 'tag': tag}
    manifest = json.loads(raw)
    if not isinstance(manifest, dict) or manifest.get('schema') != SCHEMA or manifest.get('app') != app or manifest.get('tag') != tag:
        raise DataReleaseError('Data release manifest does not describe %s %s' % (app, tag))
    assets = manifest.get('assets') or []
    listed = manifest.get('files') or []
    files = {member_path(f['path']): f for f in listed}
    if len(files) != len(listed) or len({path.casefold() for path in files}) != len(files):
        raise DataReleaseError('Data release manifest lists a file twice (paths are compared case-insensitively)')
    for asset in assets:
        if not SAFE_NAME.match(str(asset.get('name'))) or asset['name'] == 'manifest.json' or not urls.get(asset['name']):
            raise DataReleaseError('Data release asset is missing or unsafe: %r' % asset.get('name'))
    for stale in (state / 'data-download').iterdir():  # an interrupted download of an older tag is never resumed
        if stale.is_dir() and not stale.is_symlink() and not stale.is_junction() and stale.name != tag:
            shutil.rmtree(stale, ignore_errors=True)
    cache = state / 'data-download' / tag
    cache.mkdir(parents=True, exist_ok=True)
    total, done = sum(int(a['bytes']) for a in assets), 0
    _require_space(data, state, total - sum((cache / a['name']).stat().st_size for a in assets if (cache / a['name']).is_file()), files)
    archives = []
    for asset in assets:
        part = cache / asset['name']
        _download(urls[asset['name']], part, int(asset['bytes']), asset['sha256'], lambda have: report(
            phase='downloading', asset=asset['name'], bytesDone=done + have, bytesTotal=total), insecure)
        done += int(asset['bytes'])
        archives.append((part, asset['name']))
    report(phase='extracting', bytesDone=total, bytesTotal=total)
    _atomic_write(extracting, json.dumps({'tag': tag, 'manifestSha256': digest}))
    written, kept = _extract(archives, data, state, files, app)
    _atomic_write(marker, json.dumps({'tag': tag, 'manifestSha256': digest,
                                    'extractedAt': datetime.now(timezone.utc).isoformat(timespec='seconds')}, indent=2))
    extracting.unlink(missing_ok=True)
    shutil.rmtree(cache, ignore_errors=True)
    report(phase='done', bytesDone=total, bytesTotal=total)
    return {'status': 'component-extracted', 'tag': tag, 'written': written, 'kept': kept}


def progress_page(status):
    total, done = status.get('bytesTotal') or 0, status.get('bytesDone') or 0
    line = ('Download failed: %s. Melange will try again next time it opens.' % status.get('error')) if status.get('phase') == 'error' \
        else 'Downloading your starting data: %d%%' % (100 * done // total if total else 0)
    line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">'
            '<title>Melange - preparing data</title><style>body{margin:0;background:#101820;color:#eef2f5;font:17px/1.6 system-ui,sans-serif}'
            'main{max-width:720px;margin:12vh auto;padding:32px}</style></head><body><main><!-- %s -->'
            '<h1>Setting up Melange</h1><p>%s</p><p>This page refreshes by itself and is replaced by your dashboard when the '
            'download finishes. If it is still here afterwards, close and reopen Melange.</p></main></body></html>\n') % (BOOTSTRAP_TAG, line)


def _replace(source, target, *, identity, entry):
    """Publish a newly owned file only if the destination is still absent."""
    _checked_file(source, entry, identity)
    os.link(source, target, follow_symlinks=False)  # atomic no-overwrite, same directory/volume
    linked_stamp = None
    try:
        for path in (source, target):
            info = _regular(path, links=2)
            if (info.st_dev, info.st_ino) != identity:
                raise DataReleaseError('Component publication identity changed')
        linked_stamp = _checked_file(target, entry, identity, links=2)
        if _path_stamp(source, links=2) != linked_stamp:
            raise DataReleaseError('Component publication changed')
        Path(source).unlink()
    except BaseException:
        try:
            # Revalidate both names before undoing only this call's new link.
            # A verified stamp must not be replaced by a changed baseline.
            current = _checked_file(target, entry, identity, links=2)
            if ((linked_stamp is None or current == linked_stamp)
                    and _path_stamp(source, links=2) == current
                    and _remove_owned(target, identity, links=2, stamp=current)):
                remaining = _checked_file(source, entry, identity)
                # Our unlink changes only link count/change time. All other
                # content identity fields must still equal the linked stamp.
                if remaining[:3] + remaining[4:6] == current[:3] + current[4:6]:
                    _remove_owned(source, identity, stamp=remaining)
        except (OSError, DataReleaseError):
            pass
        raise


def _atomic_write(path, text):
    # Component recovery records may be repeated unchanged. They never replace
    # a late/foreign record, a link, or an original user path.
    raw = text.encode('utf-8')
    entry = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    if os.path.lexists(path):
        _checked_file(path, entry)
        return
    descriptor, name = tempfile.mkstemp(prefix='.melange-data-', suffix='.part', dir=path.parent)
    temporary = Path(name)
    info = os.fstat(descriptor)
    identity = (info.st_dev, info.st_ino)
    stamp = None
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        stamp = _checked_file(temporary, entry, identity)
        _replace(temporary, path, identity=identity, entry=entry)
    finally:
        _remove_owned(temporary, identity, stamp=stamp)


def _redact(text, data, state):
    """status.json and the progress page show errors; OSError text carries the user's absolute folders."""
    forms = {}
    for path, label in ((Path.home(), '~'), (data, '<data>'), (state, '<state>')):
        for form in (str(path), str(Path(path).resolve())):
            for variant in (form, form.replace('\\', '/'), form.replace('\\', '\\\\')):  # repr() doubles backslashes
                forms[variant] = label
    for form in sorted(forms, key=len, reverse=True):
        if len(form) > 3:
            text = re.sub(re.escape(form), lambda _, label=forms[form]: label, text, flags=re.I)
    return text


def start_background(app, data_root, state_root, repo, *, api_base=None, progress=None):
    """No production thread or filesystem preparation without a compiled plan."""
    if _COMPILED_PUBLIC_PLANS.get(app) is None:
        return None
    raise DataReleaseError('The compiled public input installer is unavailable')


def launch(app, data_root, state_root, *, reports_root=None, environ=os.environ):
    """Ordinary backend hook: no inherited flag/repository/API enables a plan."""
    if _COMPILED_PUBLIC_PLANS.get(app) is None:
        return None
    raise DataReleaseError('The compiled public input installer is unavailable')
