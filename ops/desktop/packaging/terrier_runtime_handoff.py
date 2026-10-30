"""One-run native district preparation; the parent retains signed-byte handles.

No downloaded selector or settings value creates this stdin capability. Existing
district validation and real snapshot readers still run before any active write.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3

from module_application_contracts import canonical, require
from module_data_handoff import read_frame, _parse
from terrier_district import DistrictDataBlocked, verify_district_program
from terrier_github_snapshot import BASE_FILES, regular_file, snapshot_role

MAX_FRAME = 2 * 1024**2
ROLES = frozenset(('contacts.sqlite3', 'density.json', 'roads.sqlite3', 'scores.sqlite3', 'street.sqlite3', 'walk.sqlite3'))
IDS = frozenset(('co-05', 'or-05', 'ct-01'))
FIELDS = frozenset(('schemaVersion', 'appId', 'launchNonce', 'programFingerprint', 'sourceDigest',
                    'district', 'rootsDigest', 'profileRoot', 'sourceRoot', 'dataRoot', 'stateRoot', 'files', 'commitToken'))


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def fingerprint(file):
    value = file.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns


class DistrictActivationBlocked(Exception):
    def __init__(self, status):
        super().__init__('The selected district data could not be activated.')
        self.status = status


class DistrictRuntimeInput:
    def __init__(self, value, options, *, identity=None):
        require(type(value) is dict and set(value) == FIELDS)
        require(type(value['schemaVersion']) is int and value['schemaVersion'] == 1
                and value['appId'] == options.app == 'terrier' and value['district'] == options.district in IDS
                and bool(options.github_district_data))
        for name in ('launchNonce', 'commitToken'):
            require(type(value[name]) is str and re.fullmatch(r'[A-Za-z0-9_-]{43}', value[name]) is not None)
        for name in ('programFingerprint', 'sourceDigest', 'rootsDigest'):
            require(type(value[name]) is str and re.fullmatch('[a-f0-9]{64}', value[name]) is not None)
        require(value['programFingerprint'] == verify_district_program(options.source_root))
        paths = {name: str(Path(value[name]).resolve(strict=True)) for name in
                 ('profileRoot', 'sourceRoot', 'dataRoot', 'stateRoot')}
        require(all(type(value[name]) is str and Path(value[name]).is_absolute() and paths[name] == value[name] for name in paths))
        require(paths == {'profileRoot': str(options.profile_root.resolve(strict=True)),
                          'sourceRoot': str(options.source_root.resolve(strict=True)),
                          'dataRoot': str(options.data_root.resolve(strict=True)),
                          'stateRoot': str(options.state_root.resolve(strict=True))}
                and digest(paths) == value['rootsDigest'])
        source, data, state = (Path(paths[name]) for name in ('sourceRoot', 'dataRoot', 'stateRoot'))
        require(source != data and source != state and data != state
                and not data.is_relative_to(source) and not state.is_relative_to(source)
                and not source.is_relative_to(data) and not source.is_relative_to(state)
                and not data.is_relative_to(state) and not state.is_relative_to(data))
        rows = value['files']
        require(type(rows) is list and len(ROLES) <= len(rows) <= 10000)
        seen = set()
        for row in rows:
            require(type(row) is dict and set(row) == {'role', 'path', 'bytes', 'sha256'})
            role = row['role']
            require(type(role) is str and role not in seen and (role in ROLES or snapshot_role(role))
                    and row['path'] == value['district'] + '/data/' + role
                    and type(row['bytes']) is int and 0 < row['bytes'] <= 3 * 1024**3
                    and type(row['sha256']) is str and re.fullmatch('[a-f0-9]{64}', row['sha256']) is not None)
            seen.add(role)
        require(ROLES <= seen and sum(row['bytes'] for row in rows) <= 12 * 1024**3
                and rows == sorted(rows, key=lambda row: row['role'])
                and digest({'district': value['district'], 'files': rows}) == value['sourceDigest'])
        self.value, self.source, self.data, self.state = value, source, data, state
        self.reader = None
        self.used = False
        self.identity = identity
        self.principal = self.current_principal() if identity is not None else None
        self.files = self.data_call(self.capture_files)

    def current_principal(self):
        from desktop_credentials import valid_session
        value = self.identity()
        require(valid_session(value) and not value['locked'])
        return value['userSid'], value['sessionId']

    def program(self):
        require(verify_district_program(self.source) == self.value['programFingerprint'])
        if self.identity is not None:
            require(self.current_principal() == self.principal)

    def blocked(self, reason):
        self.program()
        return DistrictActivationBlocked({'schemaVersion': 1, 'appId': 'terrier',
            'launchNonce': self.value['launchNonce'], 'programFingerprint': self.value['programFingerprint'],
            'sourceDigests': {'district': self.value['sourceDigest']}, 'reason': reason})

    def data_call(self, work):
        self.program()
        try:
            return work()
        except DistrictActivationBlocked:
            raise
        except (DistrictDataBlocked, ValueError, UnicodeError, sqlite3.DatabaseError):
            raise self.blocked('integrity') from None
        except OSError:
            raise self.blocked('storage') from None

    def capture_files(self):
        result = {}
        for row in self.value['files']:
            file = regular_file(self.data / row['role'], self.data)
            value = fingerprint(file)
            if value[2] != row['bytes']:
                raise ValueError('A selected district input changed size.')
            result[row['role']] = value
        return result

    def unchanged(self):
        if self.capture_files() != self.files:
            raise ValueError('A selected district input changed before activation.')

    def prepare_snapshot(self):
        from terrier_github_snapshot import activate_snapshot
        def prepare():
            self.unchanged()
            result = activate_snapshot(self.source, self.data, self.state, self.value['district'], defer_activation=True)
            self.unchanged()
            return result
        self.reader = self.data_call(prepare)

    def health(self):
        require(self.reader is not None)
        def checked():
            self.unchanged()
            return self.reader.health()
        status = self.data_call(checked)
        return {name: self.value[name] for name in ('schemaVersion', 'appId', 'launchNonce', 'programFingerprint', 'sourceDigest', 'district', 'rootsDigest')} | status

    def commit(self, token):
        self.program()
        if (self.used or type(token) is not str or not hmac.compare_digest(token, self.value['commitToken'])
                or self.reader is None):
            return False
        self.used = True
        def commit():
            self.unchanged()
            self.reader.commit()
            self.unchanged()
        self.data_call(commit)
        return True


def prepare_district_handoff(stream, options):
    identity = None
    if options.windows_session:
        from desktop_credentials import current_windows_identity
        identity = current_windows_identity
    value = _parse(read_frame(stream, maximum=MAX_FRAME), maximum=MAX_FRAME)
    return DistrictRuntimeInput(value, options, identity=identity)


def emit_district_blocked(error, stream):
    if type(error) is not DistrictActivationBlocked:
        return False
    # The status was produced only after context/program verification. No roots,
    # commit secret, raw error or factual rows are emitted.
    stream.write('DESKTOP_DATA_BLOCKED ' + canonical(error.status).decode('utf-8') + '\n')
    stream.flush()
    return True


def abort_blocked_district(error):
    import sys
    if not emit_district_blocked(error, sys.stdout):
        raise error
    os._exit(1)
