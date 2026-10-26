"""Served generations of the staffer-live workspace: one complete directory per build, and one pointer naming the served one.

WHY.  build_clean_workspace.py used to rewrite fec/surfaces/staffer_live/approved in place while staffer_live_server.py served
from it, so a reader could load a half-written workspace.  A chain rollback could not repair that either: the directory sits
outside the chain transaction's write set (fec/chain_transaction.py COPY_TREES) and is about 200 MB, so DE-078 recorded a partial
dashboard surviving a rollback.

HOW.
  * A build writes a complete new generation into fec/surfaces/staffer_live/generations/<id>/ and never writes into a directory a
    reader can be pointed at.  manifest.json (relative path -> sha256, size) is written LAST, so a generation without one is a
    build that did not finish, and it is never served.
  * The pointer data/system/staffer_live_active.json is then replaced atomically (temp file + lane_file_io.replace_atomic).  It
    lives in data/system, which is already one of the chain transaction's COPY_TREES, so begin() takes its before-image and
    rollback() / recover() restore it byte-exact.  A failed or killed chain therefore serves the previous generation again, and
    that directory was never written into.  The first publish on a tree creates the pointer; a rollback of that run deletes it as
    a new file in scope, and readers fall back to the legacy directory.
  * Readers resolve the served directory with served_dir(assets) / active_dir(root).  No pointer, an unreadable or malformed
    pointer, or a pointer whose generation is not sealed (manifest sha256 as recorded, every listed file byte-exact) falls back to
    the legacy fec/surfaces/staffer_live/approved directory, which nothing writes any more (a frozen last-known-good).
  * Retention mirrors the chain's KEEP=2: after a successful flip the new generation and the one the pointer named before are
    kept, together with any generation named by the pointer's before-image in an OPEN or ROLLBACK_FAILED chain journal (a later
    rollback may restore that pointer).  Everything else in generations/ is pruned, under PUBLISH_LOCK, so one publisher at a time
    owns the directory.  When those journals cannot be read, nothing is pruned (journal_generations returns None).

Stdlib only.  lane_file_io and chain_transaction are imported lazily from fec/ (both are optional for readers).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

POINTER_REL = 'data/system/staffer_live_active.json'
STAFFER_LIVE_REL = 'fec/surfaces/staffer_live'
GENERATIONS_REL = STAFFER_LIVE_REL + '/generations'
LEGACY_NAME = 'approved'
MANIFEST_NAME = 'manifest.json'
POINTER_SCHEMA = 'staffer-live-active-v1'
MANIFEST_SCHEMA = 'staffer-live-generation-v1'
KEEP = 2                                   # the served generation and the one before it, like chain_transaction.KEEP
RUN_ID_ENV = 'MELANGE_CHAIN_RUN_ID'        # optional: a caller that knows its chain run id names the generation after it
PUBLISH_LOCK = '.publish.lock'
LOCK_STALE_SECONDS = 3 * 3600              # a build takes minutes; a lock this old belongs to a publisher that died
BLOCK = 1 << 20
_GENERATION_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}')
_SHA256 = re.compile(r'[0-9a-f]{64}')
NEGATIVE_TTL_SECONDS = 30                  # a refused generation is re-checked after this long
_resolved = {}                             # _resolve() cache: one entry per root


def generations_dir(root):
    return Path(root, *GENERATIONS_REL.split('/'))


def generation_dir(root, generation):
    return generations_dir(root) / generation


def legacy_dir(root):
    return Path(root, *STAFFER_LIVE_REL.split('/')) / LEGACY_NAME


def pointer_path(root):
    return Path(root, *POINTER_REL.split('/'))


def valid_generation_id(generation):
    return isinstance(generation, str) and _GENERATION_ID.fullmatch(generation) is not None


def new_generation_id():
    """Sortable to the microsecond (like chain_transaction._stamp), suffixed with the chain run id when the caller set one."""
    now = datetime.now(timezone.utc)
    stamp = now.strftime('%Y%m%dT%H%M%S') + '%06dZ' % now.microsecond
    run = re.sub(r'[^A-Za-z0-9_.-]', '_', os.environ.get(RUN_ID_ENV, ''))[-48:]
    return stamp + ('-' + run if run else '')


def _sha_file(path):
    digest, size = hashlib.sha256(), 0
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(BLOCK), b''):
            digest.update(block)
            size += len(block)
    return digest.hexdigest(), size


# ---- readers --------------------------------------------------------------------------------------------------------------------

def read_pointer(root):
    """The pointer document when it is well formed, else None (absent, unreadable or malformed: the caller falls back)."""
    try:
        return _parse_pointer(pointer_path(root).read_bytes())
    except OSError:
        return None


def _parse_pointer(raw):
    try:
        doc = json.loads(raw.decode('utf-8'))
    except ValueError:
        return None
    if not isinstance(doc, dict) or doc.get('schema') != POINTER_SCHEMA:
        return None
    generation = doc.get('generation')
    if not valid_generation_id(generation) or doc.get('path') != GENERATIONS_REL + '/' + generation:
        return None
    if not isinstance(doc.get('sha256_manifest'), str) or not _SHA256.fullmatch(doc['sha256_manifest']):
        return None
    return doc


def _manifest_matches(root, generation, sha256):
    """True when the generation's manifest.json exists inside generations/, names this generation and hashes to sha256."""
    base = generations_dir(root)
    directory = base / generation
    manifest = directory / MANIFEST_NAME
    try:
        if not directory.resolve().is_relative_to(base.resolve()) or not manifest.is_file():
            return False
        raw = manifest.read_bytes()
        doc = json.loads(raw.decode('utf-8'))
    except (OSError, ValueError):
        return False
    return (hashlib.sha256(raw).hexdigest() == sha256 and isinstance(doc, dict) and doc.get('schema') == MANIFEST_SCHEMA
            and doc.get('generation') == generation)


def _resolve(root):
    """The generation the pointer names when it is sealed, else None (readers then use the legacy directory).

    Sealed means: the pointer is well formed, the generation's manifest.json lies inside generations/, names this generation and
    hashes to the pointer's sha256_manifest, and every file it lists still has its recorded sha256 and size with nothing unlisted
    beside them (verify_generation).  That full check runs once per pointer version and manifest stat, so after each flip,
    rollback or process start; a positive answer is cached until either changes, and a refusal is re-checked after
    NEGATIVE_TTL_SECONDS so a transient lock cannot pin readers to the legacy directory."""
    root = Path(root)
    try:
        raw = pointer_path(root).read_bytes()
    except OSError:
        return None
    key = str(root)
    cached = _resolved.get(key)
    if (cached is not None and cached[0] == raw and cached[1] == _stat_key(cached[2])
            and (cached[3] is not None or time.monotonic() - cached[4] < NEGATIVE_TTL_SECONDS)):
        return cached[3]
    doc = _parse_pointer(raw)
    manifest = (generation_dir(root, doc['generation']) if doc else generations_dir(root)) / MANIFEST_NAME
    stat_before = _stat_key(manifest)
    generation = problem = None
    if not doc:
        problem = 'pointer unreadable'
    elif not _manifest_matches(root, doc['generation'], doc['sha256_manifest']):
        problem = 'manifest does not hash to the pointer'
    else:
        problem = next(iter(verify_generation(root, doc['generation'])), None)
    if problem is None:
        generation = doc['generation']
    else:  # logged once per cache entry, not per request
        print('staffer_live_generation: refused generation %s (%s); serving legacy approved/'
              % (doc['generation'] if doc else '?', problem), file=sys.stderr, flush=True)
    _resolved[key] = (raw, stat_before, manifest, generation, time.monotonic())
    return generation


def active_generation(root):
    """The generation id the pointer names, when that generation is sealed (_resolve); else None."""
    return _resolve(root)


def _stat_key(path):
    try:
        st = os.stat(path)
    except OSError:
        return None
    return st.st_mtime_ns, st.st_size


def served_dir(assets):
    """The directory to serve /staffer-live/approved/* from, for a staffer_live assets directory.

    The pointer is consulted only when `assets` sits at <root>/fec/surfaces/staffer_live, the layout the build writes; any other
    assets directory (an installed app's bundled assets, a test fixture) serves its own approved/ exactly as before.  A flip or a
    rollback changes the pointer bytes, so it is seen on the next request (_resolve caches on them)."""
    assets = Path(assets)
    legacy = assets / LEGACY_NAME
    if (assets.name, assets.parent.name, assets.parent.parent.name) != ('staffer_live', 'surfaces', 'fec'):
        return legacy
    root = assets.parent.parent.parent
    generation = _resolve(root)
    return generation_dir(root, generation) if generation else legacy


def active_dir(root):
    """served_dir() for the repository / data root `root`."""
    return served_dir(Path(root, *STAFFER_LIVE_REL.split('/')))


def verify_generation(root, generation):
    """Problems (empty list = byte-exact): the manifest is readable and every file it lists has its recorded sha256 and size,
    and no unlisted file sits in the generation directory."""
    directory = generation_dir(root, generation)
    try:
        doc = json.loads((directory / MANIFEST_NAME).read_bytes().decode('utf-8'))
        files = doc['files']
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return ['manifest unreadable: %s: %s' % (type(exc).__name__, exc)]
    problems = []
    for rel, meta in sorted(files.items()):
        try:
            sha, size = _sha_file(directory / rel)
        except OSError as exc:
            problems.append('%s: %s' % (rel, exc))
            continue
        if (sha, size) != (meta.get('sha256'), meta.get('size')):
            problems.append('%s: bytes differ from the manifest' % rel)
    listed = set(files) | {MANIFEST_NAME}
    problems.extend('%s: not in the manifest' % rel for rel in sorted(_files(directory)) if rel not in listed)
    return problems


def _files(directory):
    out = []
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames.sort()
        for name in sorted(filenames):
            out.append(Path(dirpath, name).relative_to(directory).as_posix())
    return out


# ---- writer ---------------------------------------------------------------------------------------------------------------------

def _replace(source, target):
    try:
        from lane_file_io import replace_atomic          # retried through Windows reader / OneDrive / scanner locks
    except ImportError:
        try:
            from fec.lane_file_io import replace_atomic
        except ImportError:
            replace_atomic = os.replace
    replace_atomic(source, target)


def _write_bytes_atomic(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('%s.%d.tmp' % (path.name, os.getpid()))
    try:
        with open(tmp, 'wb') as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        _replace(tmp, path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def _json_bytes(doc):
    return (json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=True) + '\n').encode('utf-8')


def write_manifest(directory, generation):
    """Hash every file of a finished generation into its manifest.json (written last).  Returns (manifest sha256, files, bytes)."""
    files, total = {}, 0
    for rel in _files(directory):
        if rel == MANIFEST_NAME:
            continue
        path = directory / rel
        if path.is_symlink():
            raise ValueError('generation %s: %s is a link; a generation holds plain files only' % (generation, rel))
        sha, size = _sha_file(path)
        files[rel] = {'sha256': sha, 'size': size}
        total += size
    body = _json_bytes({'schema': MANIFEST_SCHEMA, 'generation': generation, 'file_count': len(files), 'bytes': total,
                        'written_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'files': files})
    _write_bytes_atomic(directory / MANIFEST_NAME, body)
    return hashlib.sha256(body).hexdigest(), len(files), total


def _remove_tree(target):
    """rmtree that clears the read-only attribute OneDrive puts on folders (build_clean_workspace.remove_tree, attempt 8)."""
    def onexc(function, path, error):
        if not isinstance(error, PermissionError):
            raise error
        os.chmod(path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
        function(path)
    shutil.rmtree(target, onexc=onexc)


@contextmanager
def _publish_lock(directory):
    """One publisher at a time owns generations/ (its writes and its pruning).  A lock older than LOCK_STALE_SECONDS belongs to a
    publisher that died and is broken once; a live one makes this publish refuse, which leaves the served generation as it is."""
    path = directory / PUBLISH_LOCK
    for attempt in (1, 2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                age = time.time() - path.stat().st_mtime
            except OSError:
                age = None                                   # released between the two calls: try again
            if attempt == 1 and (age is None or age > LOCK_STALE_SECONDS):
                if age is not None:
                    try:
                        path.unlink()
                    except OSError:
                        pass
                continue
            raise RuntimeError('another staffer-live generation publish holds %s (age %.0f s); nothing was published'
                               % (path, age or 0.0))
    try:
        os.write(fd, _json_bytes({'pid': os.getpid(), 'started': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}))
    finally:
        os.close(fd)
    try:
        yield
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def journal_generations(root):
    """Generations named by the pointer's before-image in this root's unfinished chain journals (OPEN or ROLLBACK_FAILED): a
    rollback or recover() may restore that pointer, so its generation must survive pruning.

    Fail-safe: returns None when this cannot be established -- chain_transaction cannot be imported, a staging base cannot be
    listed, a transaction's journal.json exists but cannot be read, or a journalled before-image of the pointer cannot be read.
    publish_generation() then prunes nothing.  A transaction directory with no journal.json at all is a snapshot that never
    finished; LIVE was never touched under it, so it names no generation."""
    try:
        import chain_transaction as CT
    except ImportError:
        return None
    out = set()
    want = os.path.normcase(os.path.abspath(root))
    for base in CT._recovery_bases(os.path.abspath(root)):
        try:
            names = sorted(os.listdir(base))
        except FileNotFoundError:
            continue
        except OSError:
            return None
        for name in names:
            directory = os.path.join(base, name)
            if not os.path.isdir(directory) or not os.path.exists(os.path.join(directory, 'journal.json')):
                continue
            journal = CT._read_journal(directory)
            if journal is None:
                return None
            if (journal.get('state') not in (CT.OPEN, CT.ROLLBACK_FAILED)
                    or os.path.normcase(str(journal.get('root'))) != want or POINTER_REL not in journal.get('files', {})):
                continue
            before = Path(directory, 'files', *POINTER_REL.split('/'))
            try:
                doc = json.loads(before.read_bytes().decode('utf-8'))
            except (OSError, ValueError):
                return None
            if isinstance(doc, dict) and valid_generation_id(doc.get('generation')):
                out.add(doc['generation'])
    return out


def prune_generations(root, keep, log=print):
    """Delete every generation directory not in `keep`.  Call only under _publish_lock and after the pointer flip."""
    pruned = []
    base = generations_dir(root)
    try:
        entries = sorted(base.iterdir())
    except OSError:
        return pruned
    for entry in entries:
        if entry.name in keep or entry.name.startswith('.') or entry.is_symlink() or not entry.is_dir():
            continue
        if getattr(os.path, 'isjunction', lambda _p: False)(entry):
            continue
        try:
            _remove_tree(entry)
            pruned.append(entry.name)
        except OSError as exc:
            log('  staffer-live: could not prune generation %s (%s)' % (entry.name, exc))
    return pruned


def publish_generation(root, writer, generation=None, *, log=print):
    """Write a complete generation with writer(directory), seal it with its manifest, flip the pointer to it, prune old ones.

    `writer` receives a new, empty directory that no reader is pointed at.  If it raises, the pointer is untouched and the partial
    directory is removed (best effort; a directory a dead process left behind is pruned by the next publish).  Returns the pointer
    document, plus 'previous' (the generation it replaced, or None) and 'pruned'."""
    root = Path(root)
    generation = generation or new_generation_id()
    if not valid_generation_id(generation):
        raise ValueError('invalid generation id %r' % (generation,))
    base = generations_dir(root)
    base.mkdir(parents=True, exist_ok=True)
    with _publish_lock(base):
        target = base / generation
        if os.path.lexists(target):
            raise RuntimeError('generation %s already exists; a generation is written once' % generation)
        prior = read_pointer(root)
        target.mkdir()
        try:
            writer(target)
            sha, count, size = write_manifest(target, generation)
        except BaseException:
            try:
                _remove_tree(target)
            except OSError as exc:
                log('  staffer-live: the unfinished generation %s was left in place (%s); it is never served' % (generation, exc))
            raise
        doc = {'schema': POINTER_SCHEMA, 'generation': generation, 'path': GENERATIONS_REL + '/' + generation, 'files': count,
               'bytes': size, 'sha256_manifest': sha, 'written_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
        _write_bytes_atomic(pointer_path(root), _json_bytes(doc))
        previous = prior['generation'] if prior else None
        protected = journal_generations(root)
        if protected is None:
            log('  staffer-live: the open chain journals could not be read; no generation pruned this time')
            pruned = []
        else:
            pruned = prune_generations(root, {generation} | ({previous} if previous else set()) | protected, log)
    log('  staffer-live: serving generation %s (%d files, %.1f MB); previous %s; pruned %d'
        % (generation, count, size / 1e6, previous or 'none', len(pruned)))
    return dict(doc, previous=previous, pruned=pruned)
