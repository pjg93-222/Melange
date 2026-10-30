"""Bounded native-parent module input, before workspace writes or app imports.

There is no standalone CLI or environment-variable activation. Caller code owns
the child deadline and exits on any failure. The read worker only collects one
bounded frame; parsing, contracts and application imports run on the caller.
"""
import base64
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import queue
import re
import struct
import stat
import threading
import time
from types import MappingProxyType
import weakref

from module_application_contracts import (ApplicationContract, ModuleInputError, DataIntakeBlocked,
    application_contract, canonical, require, verify_program)

MAX_FRAME = 64 * 1024
_SOURCE_FIELDS = frozenset(('schemaVersion', 'appId', 'repository', 'catalogSequence', 'releaseTag',
                          'releaseCommit', 'pointerDigest', 'manifestSha256', 'cacheRoot'))
_FIELDS = frozenset(('schemaVersion', 'appId', 'contractId', 'programFingerprint', 'profileRoot',
                    'sourceRoot', 'originalDataRoot', 'stateRoot', 'source', 'launchNonce', 'binding'))
_REPOSITORIES = {'melange': 'pjg93-222/melange', 'mentat': 'pjg93-222/mentat'}
_BINDING_FIELDS = frozenset(('contractId', 'programFingerprint', 'sourceDigest', 'sourceFingerprint'))


def _exact(value, fields):
    require(type(value) is dict and set(value) == fields)


def _read_exact(stream, size):
    chunks = []
    remaining = size
    while remaining:
        chunk = stream.read(remaining)
        require(type(chunk) is bytes and 0 < len(chunk) <= remaining)
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def read_frame(stream, *, timeout=5.0, is_cancelled=lambda: False, maximum=MAX_FRAME):
    """Read length+payload+EOF with a finite wait even on a blocked Windows pipe.

    A timed-out daemon may remain in read until the candidate exits; it cannot
    parse/import or touch application state. Native startup must exit/kill that
    failed candidate and must not continue serving after a handoff exception.
    """
    require(type(timeout) in (int, float) and math.isfinite(timeout) and 0 < timeout <= 30
            and callable(is_cancelled) and hasattr(stream, 'read'))
    require(type(maximum) is int and MAX_FRAME <= maximum <= 2 * 1024**2)
    require(not is_cancelled())
    result = queue.Queue(maxsize=1)
    def collect():
        try:
            size, = struct.unpack('>I', _read_exact(stream, 4))
            require(2 <= size <= maximum)
            raw = _read_exact(stream, size)
            require(stream.read(1) == b'')
            result.put((raw, True))
        except Exception:
            result.put((None, False))
    threading.Thread(target=collect, name='native-module-input', daemon=True).start()
    deadline = time.monotonic() + timeout
    while True:
        require(not is_cancelled())
        remaining = deadline - time.monotonic()
        require(remaining > 0)
        try:
            raw, accepted = result.get(timeout=min(remaining, 0.05))
            require(not is_cancelled() and accepted)
            return raw
        except queue.Empty:
            pass


def _parse(raw, *, maximum=MAX_FRAME):
    def pairs(items):
        value = {}
        for key, child in items:
            require(key not in value)
            value[key] = child
        return value
    def invalid(_value):
        raise ModuleInputError()
    try:
        require(type(maximum) is int and MAX_FRAME <= maximum <= 2 * 1024**2)
        require(type(raw) is bytes and 2 <= len(raw) <= maximum)
        value = json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                           parse_constant=invalid, parse_float=invalid)
        nodes = 0
        def bounded(child, depth=0):
            nonlocal nodes
            nodes += 1
            require(nodes <= 4096 and depth <= 24)
            if type(child) is dict:
                for key, item in child.items():
                    bounded(key, depth + 1)
                    bounded(item, depth + 1)
            elif type(child) is list:
                for item in child:
                    bounded(item, depth + 1)
            elif type(child) is str:
                require(len(child) <= 8192)
                child.encode('utf-8', errors='strict')
            else:
                require(child is None or type(child) is bool or type(child) is int and abs(child) <= 2**53-1)
        bounded(value)
        require(canonical(value) == raw)
        return value
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ModuleInputError() from None


def _root(value):
    require(type(value) is str and Path(value).is_absolute())
    for current in (Path(value), *Path(value).parents):
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode) and not current.is_symlink()
                and not getattr(info, 'st_file_attributes', 0) & 0x400)
    resolved = Path(value).resolve(strict=True)
    require(resolved.is_dir())
    return os.path.normcase(str(resolved))


def _lexical_root(value):
    require(type(value) is str and 0 < len(value) <= 8192 and Path(value).is_absolute()
            and not re.search(r'(^|[\\/])\.{1,2}([\\/]|$)', value))
    path = Path(value)
    for part in path.parts[1:]:
        require(part and part == part.rstrip('. ') and not any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                and not re.fullmatch(r'(?i)(?:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?', part))
    return os.path.normcase(os.path.abspath(value))


@dataclass(frozen=True)
class PlannedOriginalRoot:
    original: str
    canonical: str
    ancestor: str
    ancestor_identity: tuple


def _planned_location(value):
    _lexical_root(value)
    path = Path(value).absolute()
    ancestor, missing = path, []
    while not os.path.lexists(ancestor):
        require(ancestor.parent != ancestor)
        missing.insert(0, ancestor.name)
        ancestor = ancestor.parent
    for current in (ancestor, *ancestor.parents):
        info = current.lstat()
        require(stat.S_ISDIR(info.st_mode) and not current.is_symlink()
                and not getattr(info, 'st_file_attributes', 0) & 0x400)
    info = ancestor.lstat()
    return ancestor.resolve(strict=True).joinpath(*missing), ancestor, info


def planned_original_root(value, approved, *, protected_roots=()):
    """Read-only planned writable root; never create it during preflight.

    Only the independently parsed CLI selection may select a path. Existing
    ancestors stay ordinary directories; missing suffixes append only after
    canonicalizing each approved root's nearest existing ancestor. This also
    compares Windows8.3 aliases in the same canonical namespace.
    """
    require(_lexical_root(value) == _lexical_root(approved))
    canonical, ancestor, info = _planned_location(approved)
    for protected in protected_roots:
        other, _parent, _info = _planned_location(str(protected))
        require(canonical != other and not canonical.is_relative_to(other) and not other.is_relative_to(canonical))
    return PlannedOriginalRoot(str(approved), os.path.normcase(str(canonical)), str(ancestor),
                               (info.st_dev, info.st_ino, info.st_mode))


def recheck_original_roots(prepared):
    require(type(prepared) is PreparedHandoff)
    protected = (prepared.roots['sourceRoot'], prepared.bootstrap_root, prepared.source['cacheRoot'])
    for old in prepared.original_root_plans:
        current = planned_original_root(old.original, old.original, protected_roots=protected)
        require(current.canonical == old.canonical)
        # A formerly missing suffix may now exist as an ordinary directory, but
        # the originally approved ancestor itself may not be swapped out.
        info = Path(old.ancestor).lstat()
        require((info.st_dev, info.st_ino, info.st_mode) == old.ancestor_identity
                and not Path(old.ancestor).is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400)
    return True


@dataclass(frozen=True, eq=False)
class PreparedHandoff:
    contract: ApplicationContract
    source: object
    roots: object
    readers: object
    binding: object
    launch_nonce: str
    bootstrap_root: str
    original_root_plans: tuple = ()


@dataclass(frozen=True)
class InstalledInputs:
    application: object
    public_readers: object
    private_boundaries: object
    verify: object = None


@dataclass(frozen=True, eq=False)
class _InstalledHandoff:
    application: object


_INSTALLED = weakref.WeakKeyDictionary()
_CONSUMED = weakref.WeakSet()


@dataclass(frozen=True, eq=False)
class ServerInstallation:
    """Opaque program-held installation latch; never serialized or accepted from JSON."""


_SERVER_INSTALLATIONS = weakref.WeakKeyDictionary()


def server_installation(prepared, capture_originals):
    require(type(prepared) is PreparedHandoff and callable(capture_originals))
    latch = ServerInstallation()
    _SERVER_INSTALLATIONS[latch] = {'prepared': prepared, 'capture': capture_originals,
                                    'used': False, 'installed': None, 'server': None}
    return latch


def complete_server_installation(latch, server):
    require(type(latch) is ServerInstallation and latch in _SERVER_INSTALLATIONS and server is not None)
    state = _SERVER_INSTALLATIONS[latch]
    require(not state['used'])
    state['used'] = True
    originals = state['capture'](server)
    installed = install_handoff(state['prepared'], server, originals)
    state['installed'], state['server'] = installed, server


def server_installed_health(latch, server):
    require(type(latch) is ServerInstallation and latch in _SERVER_INSTALLATIONS)
    state = _SERVER_INSTALLATIONS[latch]
    require(state['installed'] is not None and state['server'] is server)
    return installed_health(state['installed'])


def prepare_handoff(stream, *, app_id, profile_root, source_root, original_data_root, state_root,
                    bootstrap_root, timeout=5.0, is_cancelled=lambda: False, lookup=None):
    """lookup is a native test/compiled dependency, never a payload field."""
    prepared = None
    intake_context = None
    try:
        value = _parse(read_frame(stream, timeout=timeout, is_cancelled=is_cancelled))
        _exact(value, _FIELDS)
        require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1
                and app_id in _REPOSITORIES and value['appId'] == app_id)
        roots = {'profileRoot': str(profile_root), 'sourceRoot': str(source_root),
                 'originalDataRoot': str(original_data_root), 'stateRoot': str(state_root)}
        for key in ('profileRoot', 'sourceRoot'):
            require(_lexical_root(value[key]) == _lexical_root(roots[key])
                    and _root(value[key]) == _root(roots[key]))
        contract = (application_contract if lookup is None else lookup)(app_id, value['contractId'])
        require(type(contract) is ApplicationContract and contract.app_id == app_id
                and contract.contract_id == value['contractId'] and contract.program_fingerprint == value['programFingerprint'])
        source = value['source']
        _exact(source, _SOURCE_FIELDS)
        require(type(source['schemaVersion']) is int and source['schemaVersion'] == 1
                and source['appId'] == app_id and source['repository'] == _REPOSITORIES[app_id]
                and type(source['catalogSequence']) is int and 0 < source['catalogSequence'] <= 2**53-1
                and all(type(source[key]) is str and re.fullmatch(r'[a-f0-9]{64}', source[key]) for key in ('pointerDigest', 'manifestSha256'))
                and type(source['releaseCommit']) is str and re.fullmatch(r'[a-f0-9]{40}', source['releaseCommit'])
                and type(source['releaseTag']) is str and re.fullmatch(r'module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?', source['releaseTag'])
                and type(source['cacheRoot']) is str and Path(source['cacheRoot']).is_absolute())
        binding = {'contractId': contract.contract_id, 'programFingerprint': contract.program_fingerprint,
                   'sourceDigest': source['manifestSha256'], 'sourceFingerprint': hashlib.sha256(canonical(source)).hexdigest()}
        _exact(value['binding'], _BINDING_FIELDS)
        require(value['binding'] == binding)
        nonce = value['launchNonce']
        require(type(nonce) is str and re.fullmatch(r'[A-Za-z0-9_-]{43}', nonce)
                and len(base64.urlsafe_b64decode(nonce + '=')) == 32
                and base64.urlsafe_b64encode(base64.urlsafe_b64decode(nonce + '=')).rstrip(b'=').decode() == nonce)
        plans = tuple(planned_original_root(value[key], roots[key],
            protected_roots=(roots['sourceRoot'], str(bootstrap_root), source['cacheRoot']))
            for key in ('originalDataRoot', 'stateRoot'))
        require(not is_cancelled())
        verify_program(contract, source_root=source_root, bootstrap_root=bootstrap_root)
        require(not is_cancelled())
        intake_context = {'schemaVersion': 1, 'appId': app_id, 'launchNonce': nonce,
                          'programFingerprint': contract.program_fingerprint,
                          'sourceDigests': {'public': source['manifestSha256']}}
        prepared = contract.prepare_readers(app_id=app_id, profile=str(profile_root), source_root=str(source_root),
            original_data_root=str(original_data_root), state_root=str(state_root), source=dict(source),
            native_verified=True, required_kinds=contract.required_kinds, is_cancelled=is_cancelled)
        coverage = prepared.get('coverage') if type(prepared) is dict else None
        require(not is_cancelled() and type(prepared) is dict and prepared.get('appId') == app_id
                and prepared.get('source') == source and type(coverage) is dict
                and set(coverage) == {'completeKind', 'fullApplication'}
                and coverage['completeKind'] is True and coverage['fullApplication'] is False
                and type(prepared.get('readers')) is dict and set(prepared['readers']) == set(contract.required_kinds))
        verify_program(contract, source_root=source_root, bootstrap_root=bootstrap_root)
        require(not is_cancelled())
        return PreparedHandoff(contract, MappingProxyType(dict(source)), MappingProxyType(roots),
            MappingProxyType(dict(prepared['readers'])), MappingProxyType(binding), nonce, str(bootstrap_root), plans)
    except Exception as error:
        if type(prepared) is dict and type(prepared.get('readers')) is dict:
            for bound in prepared['readers'].values():
                reader = bound.get('reader') if type(bound) is dict else None
                if callable(getattr(reader, 'close', None)):
                    try:
                        reader.close()
                    except Exception:
                        pass
        if type(error) is DataIntakeBlocked and intake_context is not None:
            # A program replacement/import failure must never be disguised as a
            # recoverable cached-data error, even if data failed first.
            verify_program(contract, source_root=source_root, bootstrap_root=bootstrap_root)
            error.native_status = {**intake_context, 'reason': error.reason}
            raise
        raise ModuleInputError() from None


def emit_data_blocked(error, stream):
    """One bounded native diagnostic, containing no paths or exception text."""
    if type(error) is not DataIntakeBlocked or type(error.native_status) is not dict:
        return False
    value = error.native_status
    fields = {'schemaVersion', 'appId', 'launchNonce', 'programFingerprint', 'sourceDigests', 'reason'}
    if (set(value) != fields or type(value['schemaVersion']) is not int or value['schemaVersion'] != 1
            or value['appId'] not in ('melange', 'mentat') or value['reason'] not in ('integrity', 'storage')
            or type(value['launchNonce']) is not str or re.fullmatch(r'[A-Za-z0-9_-]{43}', value['launchNonce']) is None
            or type(value['programFingerprint']) is not str or re.fullmatch(r'[a-f0-9]{64}', value['programFingerprint']) is None
            or type(value['sourceDigests']) is not dict
            or set(value['sourceDigests']) not in ({'public'}, {'public', 'workspace'})
            or any(type(digest) is not str or re.fullmatch(r'[a-f0-9]{64}', digest) is None
                   for digest in value['sourceDigests'].values())):
        return False
    raw = canonical(value)
    if len(raw) > 2048:
        return False
    stream.write('DESKTOP_DATA_BLOCKED ' + raw.decode('utf-8') + '\n')
    stream.flush()
    return True


def install_handoff(prepared, server, original_private_contexts):
    """Only a fixed compiled installer may attest actual consumer installation."""
    try:
        require(type(prepared) is PreparedHandoff and prepared not in _CONSUMED and server is not None
                and type(original_private_contexts) is dict
                and set(original_private_contexts) == set(prepared.contract.private_boundaries)
                and all(value is not None for value in original_private_contexts.values()))
        originals = dict(original_private_contexts)
        _CONSUMED.add(prepared)
        recheck_original_roots(prepared)
        verify_program(prepared.contract, source_root=prepared.roots['sourceRoot'], bootstrap_root=prepared.bootstrap_root)
        result = prepared.contract.install_readers(prepared, server, MappingProxyType(originals))
        require(type(result) is InstalledInputs and result.application is server
                and type(result.public_readers) is dict and set(result.public_readers) == set(prepared.contract.public_readers)
                and all(reader is not None for reader in result.public_readers.values())
                and type(result.private_boundaries) is dict and set(result.private_boundaries) == set(originals)
                and all(result.private_boundaries[key] is original_private_contexts[key] is originals[key] for key in originals)
                and callable(result.verify) and result.verify() is True)
        verify_program(prepared.contract, source_root=prepared.roots['sourceRoot'], bootstrap_root=prepared.bootstrap_root)
        installed = _InstalledHandoff(result.application)
        coverage = {'publicReaders': sorted(result.public_readers), 'privateBoundaries': sorted(originals)}
        _INSTALLED[installed] = {'prepared': prepared, 'verify': result.verify,
            'health': {**prepared.binding, 'schemaVersion': 1, 'launchNonce': prepared.launch_nonce,
                'coverageDigest': hashlib.sha256(canonical(coverage)).hexdigest()}}
        return installed
    except Exception as error:
        if type(error) is DataIntakeBlocked and type(prepared) is PreparedHandoff:
            recheck_original_roots(prepared)
            verify_program(prepared.contract, source_root=prepared.roots['sourceRoot'], bootstrap_root=prepared.bootstrap_root)
            raise
        raise ModuleInputError() from None


def installed_health(installed):
    """Fresh scalar copy; paths, reader objects and capabilities never reach HTTP."""
    prepared = None
    try:
        require(type(installed) is _InstalledHandoff and installed in _INSTALLED)
        record = _INSTALLED[installed]
        prepared = record['prepared']
        require(record['verify']() is True)
        verify_program(prepared.contract, source_root=prepared.roots['sourceRoot'], bootstrap_root=prepared.bootstrap_root)
        return dict(record['health'])
    except Exception as error:
        if type(error) is DataIntakeBlocked and type(prepared) is PreparedHandoff:
            recheck_original_roots(prepared)
            verify_program(prepared.contract, source_root=prepared.roots['sourceRoot'], bootstrap_root=prepared.bootstrap_root)
            raise
        raise ModuleInputError() from None


def close_handoff(prepared):
    """Release only readers prepared by this failed/completed cold attempt."""
    if type(prepared) is PreparedHandoff:
        for bound in prepared.readers.values():
            reader = bound.get('reader') if type(bound) is dict else None
            if callable(getattr(reader, 'close', None)):
                reader.close()
