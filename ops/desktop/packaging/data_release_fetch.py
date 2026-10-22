"""First-run app data from the app's own GitHub data release (reader side of melange-desktop-data/v1).

Newest non-draft release tagged data-<app>-*; zip assets are resumed into <state>/data-download/<tag>/, verified against
manifest.json (bytes + sha256 per asset and per file), then extracted into the data root; members under __state__/ go to
the state root with that prefix stripped (Melange reads <state>/Melange as MELANGE_LOCAL_ROOT). Existing files in either
root are never replaced, except the bootstrap welcome/progress Moneyball.html. A marker file makes later launches a no-op."""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import shutil
import sys
import threading
import time
import urllib.request
import zipfile

SCHEMA = 'melange-desktop-data/v1'
REPOSITORIES = {'melange': 'pjg93-222/Melange', 'mentat': 'pjg93-222/Mentat'}
DEFAULT_API = 'https://api.github.com'
MARKER = '.melange-data-release.json'
EXTRACTING = 'extracting.json'  # in <state>/data-download while an extraction has started and not finished
BOOTSTRAP_TAG = 'melange-desktop-empty-workspace-v1'  # melange_bootstrap.WELCOME carries it; so does the progress page
STATE_PREFIX = '__state__/'
CHUNK, ATTEMPTS, RETRY_DELAY = 1 << 16, 4, 2.0
SPACE_MARGIN = 512 << 20
SAFE_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
WINDOWS_DEVICE = re.compile(r'^(con|prn|aux|nul|conin\$|conout\$|com[0-9¹²³]|lpt[0-9¹²³])(\..*)?$', re.I)


class DataReleaseError(RuntimeError):
    pass


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


def _download(url, part, size, sha256, report, insecure):
    error = None
    for attempt in range(ATTEMPTS + 1):
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
    """Validate every member of every archive before writing any file; main-app files are written last."""
    data, state = data.resolve(), state.resolve()
    plan, seen = [], set()
    for archive, asset in archives:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if info.is_dir():
                    continue
                relative = member_path(info.filename)
                entry = files.get(relative)
                if entry is None or entry.get('asset', asset) != asset or info.file_size != entry['bytes']:
                    raise DataReleaseError('Archive member %s does not match the manifest' % relative)
                if relative in seen:
                    raise DataReleaseError('Archive member %s appears more than once' % relative)
                seen.add(relative)
                root, inner = (state, relative[len(STATE_PREFIX):]) if relative.startswith(STATE_PREFIX) else (data, relative)
                if root is state and inner.split('/', 1)[0].casefold() == 'data-download':
                    raise DataReleaseError('Refusing archive member in the download cache: %s' % relative)
                target = (root / inner).resolve()
                if not target.is_relative_to(root):
                    raise DataReleaseError('Refusing archive member outside its folder: %s' % relative)
                plan.append((archive, info, target, entry, relative))
    if len(seen) != len(files):
        raise DataReleaseError('Data release archives lack %d file(s) listed in the manifest' % (len(files) - len(seen)))
    main = (lambda r: r == 'Moneyball.html') if app == 'melange' else (lambda r: r.startswith('reports/'))
    plan.sort(key=lambda item: main(item[4]))
    written, kept = 0, []
    for archive, info, target, entry, relative in plan:
        if target.exists() and not (relative == 'Moneyball.html' and is_bootstrap_page(target)):
            if not (target.is_file() and _sha256(target) == entry['sha256']):
                kept.append(relative)  # never replace a file the user already has
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + '.data-release-part')
        digest = hashlib.sha256()
        try:  # a failed write (disk full, file in use) leaves no partial file in the user's folders
            with zipfile.ZipFile(archive) as bundle, bundle.open(info) as source, temporary.open('wb') as out:
                while chunk := source.read(CHUNK):
                    digest.update(chunk)
                    out.write(chunk)
            if temporary.stat().st_size != entry['bytes'] or digest.hexdigest() != entry['sha256']:
                raise DataReleaseError('Extracted %s does not match the manifest' % relative)
            _replace(temporary, target)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        written += 1
    return written, kept


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


def ensure_app_data(app, data_root, state_root, repo, *, api_base=None, progress=None):
    """Download, verify and extract the newest data release once. Returns a summary dict; raises DataReleaseError.
    A second launch (or process) while one download runs gets {'status': 'busy'} and touches nothing."""
    data, state = Path(data_root), Path(state_root)
    marker = data / MARKER
    if marker.exists():
        return {'status': 'present', 'tag': json.loads(marker.read_text(encoding='utf-8')).get('tag')}
    lock = _lock(state / 'data-download' / '.lock')
    if lock is None:
        return {'status': 'busy'}
    try:
        if marker.exists():  # the launch that held the lock finished meanwhile
            return {'status': 'present', 'tag': json.loads(marker.read_text(encoding='utf-8')).get('tag')}
        return _ensure_locked(app, data, state, repo, api_base, progress, marker)
    finally:
        _unlock(lock)


def _ensure_locked(app, data, state, repo, api_base, progress, marker):
    insecure = api_base is not None and api_base.rstrip('/') != DEFAULT_API
    report = progress or (lambda **_: None)
    report(phase='checking')
    releases = json.loads(_read_json('%s/repos/%s/releases?per_page=20' % ((api_base or DEFAULT_API).rstrip('/'), repo), 4 << 20, insecure))
    listed = releases if isinstance(releases, list) else []
    extracting = state / 'data-download' / EXTRACTING  # lets launch() resume once Mentat's reports/ is partly written
    resumed = json.loads(extracting.read_text(encoding='utf-8')).get('tag') if extracting.is_file() else None
    if resumed is None:
        release = select_release(listed, app)
    else:  # an interrupted extraction finishes with its own release; files of two releases are never mixed
        release = next((r for r in listed if isinstance(r, dict) and not r.get('draft') and r.get('tag_name') == resumed), None)
        if release is None:
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
    _atomic_write(extracting, json.dumps({'tag': tag}))
    written, kept = _extract(archives, data, state, files, app)
    marker.write_text(json.dumps({'tag': tag, 'manifestSha256': hashlib.sha256(raw).hexdigest(),
                                  'extractedAt': datetime.now(timezone.utc).isoformat(timespec='seconds')}, indent=2), encoding='utf-8')
    extracting.unlink(missing_ok=True)
    shutil.rmtree(cache, ignore_errors=True)
    report(phase='done', bytesDone=total, bytesTotal=total)
    return {'status': 'installed', 'tag': tag, 'written': written, 'kept': kept}


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


def _replace(source, target):
    for attempt in range(10):  # Windows refuses a replace while the server has the file open; that is brief
        try:
            return os.replace(source, target)
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(0.2)


def _atomic_write(path, text):
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(text, encoding='utf-8')
    _replace(temporary, path)


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
    """Run ensure_app_data in a daemon thread; status goes to <state>/data-download/status.json."""
    data, state = Path(data_root), Path(state_root)
    status_file = state / 'data-download' / 'status.json'
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status, last = {'app': app, 'phase': 'starting', 'asset': None, 'bytesDone': 0, 'bytesTotal': 0, 'error': None}, [0.0]

    def update(**changes):
        phase_changed = changes.get('phase', status['phase']) != status['phase']
        status.update(changes)
        if progress:
            progress(**status)
        if not phase_changed and time.monotonic() - last[0] < 3 and status['phase'] not in ('done', 'error'):
            return
        last[0] = time.monotonic()
        page = data / 'Moneyball.html'
        try:  # status and the progress page are courtesy output; they never fail the download
            _atomic_write(status_file, json.dumps(status))
            if app == 'melange' and status['phase'] in ('downloading', 'extracting', 'error') and is_bootstrap_page(page):
                _atomic_write(page, progress_page(status))
        except OSError as error:
            print('DESKTOP_RUNTIME_WARNING: data release status not written: %s' % error, file=sys.stderr, flush=True)
        if app == 'mentat':
            print('DESKTOP_DATA_RELEASE: %s %s/%s bytes %s' % (status['phase'], status['bytesDone'], status['bytesTotal'],
                                                               status['error'] or ''), file=sys.stderr, flush=True)

    def work():
        try:
            result = ensure_app_data(app, data, state, repo, api_base=api_base, progress=update)
            if app == 'mentat' and result['status'] == 'installed':
                (data / 'reports').mkdir(parents=True, exist_ok=True)
                (data / 'reports' / 'README-first-run.txt').write_text(
                    'Mentat downloaded its starting data (%s). If reports do not appear, restart the app (close and reopen Mentat).\n' % result['tag'], encoding='utf-8')
            status['result'] = result
        except Exception as error:  # a failed first-run download never stops the app; the next launch retries
            update(phase='error', error=_redact('%s: %s' % (type(error).__name__, error), data, state)[:300])

    thread = threading.Thread(target=work, name='data-release-fetch', daemon=True)
    thread.start()
    return thread


def launch(app, data_root, state_root, *, reports_root=None, environ=os.environ):
    """Backend hook: start the first-run fetch unless disabled, already done, or the folder already holds the app's data."""
    data = Path(data_root)
    if app not in REPOSITORIES or environ.get('DESKTOP_DATA_RELEASE', '').lower() == 'off' or (data / MARKER).exists():
        return None
    if app == 'melange':
        page = data / 'Moneyball.html'
        if page.exists() and not is_bootstrap_page(page):
            return None
    else:
        reports = Path(reports_root) if reports_root else data / 'reports'
        resuming = (Path(state_root) / 'data-download' / EXTRACTING).is_file()
        if reports.resolve() != (data / 'reports').resolve() or (not resuming and reports.is_dir() and any(reports.iterdir())):
            return None
    return start_background(app, data, state_root, environ.get('DESKTOP_DATA_RELEASE_REPO') or REPOSITORIES[app],
                            api_base=environ.get('DESKTOP_DATA_RELEASE_API') or None)
