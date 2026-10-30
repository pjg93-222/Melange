"""Disposable, user/profile-bound receipt for a completed public-data scan.

DPAPI supplies the same Windows-user state boundary as the desktop journals;
this is not a publisher signature against code already running as that user.
Signed object hashes and the current compiled validator closure remain required.
No downloaded path selects this record, and it never changes update authority.
"""
import hashlib
import os
from pathlib import Path
import secrets
import stat
import re

import native_access_state as protected
from module_application_contracts import canonical
from module_data_snapshot import parse, require, safe_root


KIND = 'melange-public-validation'
MAX_BYTES = 2 * 1024 ** 2
_CAPABILITY = object()


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
            info.st_size, info.st_mtime_ns)


def _regular(path):
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400)
    return info


class ValidationCache:
    def __init__(self, capability, *, profile, program_fingerprint, source):
        require(capability is _CAPABILITY and os.name == 'nt')
        self._profile = safe_root(str(profile))
        self._parent = self._profile.stat()
        self._target, self._entropy = protected._location(self._profile, KIND)
        identity = protected.describe(self._profile)
        require(type(program_fingerprint) is str and re.fullmatch(r'[a-f0-9]{64}', program_fingerprint))
        self._identity = {'appId': 'melange', 'kind': 'melange.official-payroll-observations.v1',
            **identity, 'programFingerprint': program_fingerprint,
            'sourceFingerprint': hashlib.sha256(canonical(source)).hexdigest()}

    def _check_parent(self):
        require(safe_root(str(self._profile)) == self._profile)
        current = self._profile.stat()
        require((current.st_dev, current.st_ino, current.st_mode)
                == (self._parent.st_dev, self._parent.st_ino, self._parent.st_mode))

    def _binding(self, snapshot, block):
        require(snapshot.app == self._identity['appId'] and snapshot.kind == self._identity['kind'])
        return {**self._identity, 'indexSchema': 1, 'block': block,
            'objects': {role: {'bytes': snapshot.objects[role]['bytes'],
                              'sha256': snapshot.objects[role]['sha256']}
                        for role in ('observations', 'receipt')}}

    def load(self, snapshot, *, roles, block, counts):
        """Invalid or unavailable disposable state is always a cache miss."""
        try:
            self._check_parent()
            before = _regular(self._target)
            require(0 < before.st_size <= MAX_BYTES + 65536)
            flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            with os.fdopen(os.open(self._target, flags), 'rb') as stream:
                require(_stamp(os.fstat(stream.fileno())) == _stamp(before))
                encrypted = stream.read(MAX_BYTES + 65537)
                require(len(encrypted) == before.st_size
                        and _stamp(os.fstat(stream.fileno())) == _stamp(before))
            require(_stamp(_regular(self._target)) == _stamp(before)
                    and encrypted.startswith(protected.MAGIC))
            plain = protected._crypt(encrypted[len(protected.MAGIC):], self._entropy, decrypt=True)
            require(len(plain) <= MAX_BYTES)
            value = parse(plain)
            require(type(value) is dict and set(value) == {'schemaVersion', 'binding', 'counts', 'index'}
                    and type(value['schemaVersion']) is int and value['schemaVersion'] == 1
                    and type(value['binding']) is dict
                    and canonical(value['binding']) == canonical(self._binding(snapshot, block))
                    and type(value['counts']) is dict and value['counts'] == counts
                    and all(type(value['counts'][role]) is int for role in roles)
                    and type(value['index']) is dict and set(value['index']) == set(roles))
            previous = -1
            size = snapshot.objects['observations']['bytes']
            for role in roles:
                offsets = value['index'][role]
                require(type(offsets) is list and len(offsets) == (counts[role] + block - 1) // block)
                for offset in offsets:
                    require(type(offset) is int and previous < offset < size)
                    previous = offset
            require(value['index'][roles[0]][0] == 0)
            self._check_parent()
            return value['index']
        except Exception:
            return None

    def save(self, snapshot, *, roles, block, counts, index):
        """Only a completed full scan calls this; write failure costs speed only."""
        temporary = None
        try:
            self._check_parent()
            if os.path.lexists(self._target):
                _regular(self._target)
            value = {'schemaVersion': 1, 'binding': self._binding(snapshot, block),
                     'counts': counts, 'index': {role: list(index[role]) for role in roles}}
            plain = canonical(value)
            require(len(plain) <= MAX_BYTES)
            encrypted = protected.MAGIC + protected._crypt(plain, self._entropy)
            temporary = self._profile / (self._target.name + '.' + secrets.token_hex(12) + '.tmp')
            with temporary.open('xb') as stream:
                stream.write(encrypted)
                stream.flush()
                os.fsync(stream.fileno())
            self._check_parent()
            _regular(temporary)
            if os.path.lexists(self._target):
                _regular(self._target)
            os.replace(temporary, self._target)
            self._check_parent()
        except Exception:
            pass
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass


def validation_cache(*, profile, program_fingerprint, source):
    """Fixed compiled bootstrap caller supplies already-verified launch context."""
    try:
        return ValidationCache(_CAPABILITY, profile=profile,
            program_fingerprint=program_fingerprint, source=source)
    except Exception:
        return None
