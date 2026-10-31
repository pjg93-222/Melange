"""Materialize only compiled analytical members in a native profile cache.

The signed archive and its signed inner roster are the authority on EVERY
open. No marker, prior directory, original workspace or application state is
an acceptance shortcut. Domain-specific factories still validate semantics.
"""
import copy
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import sys
from types import MappingProxyType

from module_application_contracts import DataIntakeBlocked
from module_data_snapshot import parse, regular, safe_root
from workspace_archive import DomainArchive, identity, stamp
from workspace_data_contract import (ARCHIVE_MEMBERS, INDUSTRY_PAGES_KIND, INDUSTRY_MEMBERS,
    REPORT_ANALYSIS_KIND, STAFFER_ANALYSIS_KIND, MiB)
from workspace_sqlite import readonly

BLOCK = 4 * MiB
HEX = re.compile(r'[0-9a-f]{64}')
# Only JSON trees the fixed Melange preparation immediately consumes. Other
# archive types and unconsumed metadata retain their original memory behavior.
JSON_CONSUMERS = MappingProxyType({
    ('melange', INDUSTRY_PAGES_KIND, 'pages'): frozenset(INDUSTRY_MEMBERS) - {'derivation.json'},
    ('melange', STAFFER_ANALYSIS_KIND, 'records'): frozenset((
        'identity/references.json', 'contacts/directory.json', 'source/receipt.json',
        'lda/receipt.json', 'activity/receipt.json', 'profiles/receipt.json', 'profiles/checkpoint.json')),
})


def require(value):
    if not value:
        raise DataIntakeBlocked('integrity')


def directory_id(path):
    info = regular(path, True)
    return info.st_dev, info.st_ino, info.st_mode


def fixed_directory(parent, name):
    before = directory_id(parent)
    target = parent / name
    try:
        target.mkdir(mode=0o700)
    except FileExistsError:
        pass
    require(directory_id(parent) == before)
    directory_id(target)
    require(target.resolve(strict=True) == target)
    return target


def inventory(root, members):
    expected_files = set(members)
    expected_dirs = {str(parent).replace('\\', '/') for name in members
                     for parent in Path(name).parents if str(parent) != '.'}
    files, directories, seals = set(), set(), {}
    def walk(folder):
        seals[folder] = directory_id(folder)
        for path in folder.iterdir():
            name = path.relative_to(root).as_posix()
            if name in expected_dirs:
                require(name not in directories)
                directories.add(name)
                walk(path)
            else:
                require(name in expected_files and name not in files)
                info = regular(path)
                require(info.st_nlink == 1)
                files.add(name)
    walk(root)
    require(files == expected_files and directories == expected_dirs)
    return seals


def sql_family(member, *, app_id, kind, role):
    if member == 'source/catalog.sqlite':
        return 'source'
    if member == 'lda/catalog.sqlite':
        return 'lda'
    if member == 'activity/index.sqlite':
        return 'activity'
    if member.endswith('/index.sqlite'):
        if (app_id, kind, role) == ('mentat', REPORT_ANALYSIS_KIND, 'facts'):
            return 'mentat-facts'
        return 'facts'
    return None


def json_limit(member, *, app_id, kind, role):
    return 256 * MiB if (app_id, kind, role, member) == (
        'melange', STAFFER_ANALYSIS_KIND, 'records', 'identity/references.json') else 32 * MiB


def validate_type(path, member, family, limit):
    if family is not None:
        with readonly(path, family):
            pass
    elif member.endswith('.json'):
        require(path.stat().st_size <= limit)
        value = parse(path.read_bytes())
        require(type(value) in (dict, list))
        return value
    elif member.endswith('.ndjson'):
        with path.open('rb') as stream:
            count = 0
            while True:
                raw = stream.readline(8 * MiB + 1)
                if not raw:
                    break
                count += 1
                require(count <= 32_000_000 and len(raw) <= 8 * MiB and raw.endswith(b'\n'))
                require(type(parse(raw[:-1])) is dict)
    else:
        # Exact compiled supplemental XLSX names only; the report consumer
        # additionally validates the projected workbook and its model inputs.
        require(member.endswith('.xlsx'))
        with path.open('rb') as stream:
            require(stream.read(4) == b'PK\x03\x04')


class DerivedArchive:
    def __init__(self, root, source, derivation, expected, namespace_seals, families, limits, *, retain_json=()):
        self.root, self._source = root, source
        self._derivation, self._expected = derivation, expected
        self.paths = MappingProxyType({name: root / name for name in expected})
        self._directories, self._files, self._closed = {}, [], False
        self._decoded_json = {}
        try:
            self._directories = {**namespace_seals, **inventory(root, expected)}
            for member, spec in expected.items():
                path = self.paths[member]
                before = regular(path)
                require(before.st_nlink == 1 and before.st_size == spec['bytes'])
                flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
                held = os.fdopen(os.open(path, flags), 'rb')
                opened = os.fstat(held.fileno())
                self._files.append((path, held, before, opened))
                require(identity(before) == identity(opened) == identity(regular(path)))
                digest = hashlib.sha256()
                for block in iter(lambda: held.read(BLOCK), b''):
                    require(not source.cancelled())
                    digest.update(block)
                require(digest.hexdigest() == spec['sha256'])
                decoded = validate_type(path, member, families[member], limits[member])
                if member in retain_json and type(decoded) in (dict, list):
                    self._decoded_json[member] = decoded
            require(self.verify())
        except BaseException:
            self.close()
            raise

    @property
    def derivation(self):
        return copy.deepcopy(self._derivation)

    def take_json(self, member):
        """Transfer one validated JSON tree to its sole native consumer.

        The same open lease must still verify. Pop rather than share mutable
        trees between consumers, and never retain decoded data across leases.
        """
        require(member in self._decoded_json and self.verify())
        return self._decoded_json.pop(member)

    def verify(self):
        if self._closed:
            return False
        try:
            self._source._check()
            require(all(directory_id(path) == before for path, before in self._directories.items()))
            require(inventory(self.root, self._expected) == {
                path: before for path, before in self._directories.items()
                if path == self.root or self.root in path.parents})
            for path, held, named, opened in self._files:
                current, descriptor = regular(path), os.fstat(held.fileno())
                require(stamp(current) == stamp(named) and stamp(descriptor) == stamp(opened)
                        and identity(current) == identity(descriptor) and current.st_nlink == 1)
            return True
        except (OSError, ValueError):
            return False

    def close(self):
        if self._closed:
            return
        self._closed = True
        self._decoded_json.clear()
        for _path, held, _named, _opened in self._files:
            held.close()
        self._source.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


def cleanup_owned(stage, created):
    """Only this attempt's exact files/dirs; unexpected residue is preserved."""
    if stage is None:
        return
    try:
        actual = set()
        def walk(folder):
            require(folder in created and directory_id(folder) == created[folder])
            actual.add(folder)
            for path in folder.iterdir():
                require(path in created)
                if stat.S_ISDIR(created[path][2]):
                    walk(path)
                else:
                    actual.add(path)
        walk(stage)
        if actual != set(created):
            return
        for path, original in created.items():
            info = path.lstat()
            if (info.st_dev, info.st_ino, info.st_mode) != original or path.is_symlink() \
                    or getattr(info, 'st_file_attributes', 0) & 0x400:
                return
        for path in sorted(created, key=lambda value: len(value.parts), reverse=True):
            if path.is_dir():
                path.rmdir()
            else:
                if path.lstat().st_nlink != 1:
                    return
                path.unlink()
    except (OSError, ValueError):
        # Failed cleanup never authorizes deleting or replacing another cache.
        pass


def publish_owned(stage, target):
    if os.name == 'nt':
        os.rename(stage, target)  # MoveFile refuses an existing directory.
    elif sys.platform == 'linux':
        # Preserve the same no-replacement property for source/CI fixtures.
        library = ctypes.CDLL(None, use_errno=True)
        rename = getattr(library, 'renameat2', None)
        if rename is None:
            raise OSError(errno.ENOTSUP, 'Atomic directory publication unavailable')
        rename.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        if rename(-100, os.fsencode(stage), -100, os.fsencode(target), 1) != 0:
            raise OSError(ctypes.get_errno(), 'Atomic directory publication refused')
    else:
        raise OSError(errno.ENOTSUP, 'Atomic directory publication unavailable')


def prepare_cache(*, profile_root, app_id, kind, role, archive_path,
                  expected_sha256, is_cancelled=lambda: False):
    require(type(profile_root) is str and type(expected_sha256) is str
            and HEX.fullmatch(expected_sha256) and (app_id, kind, role) in ARCHIVE_MEMBERS
            and callable(is_cancelled))
    source, stage, created = None, None, {}
    try:
        profile = safe_root(profile_root)
        # Open/hash the same archive handle before creating any cache output.
        source = DomainArchive(archive_path, app_id=app_id, kind=kind, role=role,
                               expected_sha256=expected_sha256, is_cancelled=is_cancelled)
        derivation = source.json('derivation.json', limit=4 * MiB)
        members = set(source.members) - {'derivation.json'}
        require(type(derivation) is dict and type(derivation.get('schemaVersion')) is int and derivation.get('schemaVersion') == 1
                and derivation.get('kind') == kind and type(derivation.get('members')) is dict
                and set(derivation['members']) == members)
        expected = {}
        for member in sorted(members):
            spec = derivation['members'][member]
            require(type(spec) is dict and set(spec) == {'bytes', 'sha256'}
                    and type(spec['bytes']) is int and 0 <= spec['bytes'] == source.index[member][0].file_size
                    and type(spec['sha256']) is str and HEX.fullmatch(spec['sha256']))
            expected[member] = dict(spec)
        raw_derivation = b''.join(source.chunks('derivation.json'))
        expected['derivation.json'] = {'bytes': len(raw_derivation), 'sha256': hashlib.sha256(raw_derivation).hexdigest()}
        families = {member: sql_family(member, app_id=app_id, kind=kind, role=role) for member in expected}
        limits = {member: json_limit(member, app_id=app_id, kind=kind, role=role) for member in expected}
        packs = fixed_directory(profile, 'packs')
        namespace = fixed_directory(packs, 'github-workspace-derived')
        namespace_seals = {path: directory_id(path) for path in (profile, packs, namespace)}
        target = namespace / expected_sha256
        if target.exists() or target.is_symlink():
            result = DerivedArchive(target, source, derivation, expected, namespace_seals, families, limits,
                                    retain_json=JSON_CONSUMERS.get((app_id, kind, role), ()))
            source = None
            return result
        if shutil.disk_usage(namespace).free < sum(row['bytes'] for row in expected.values()) + 64 * MiB:
            raise DataIntakeBlocked('storage')
        # The signed digest identifies only the final root. A short random
        # staging name avoids adding another64 characters to Windows paths.
        stage = namespace / ('.stage-' + secrets.token_hex(16))
        stage.mkdir(mode=0o700)
        created[stage] = directory_id(stage)
        for member in sorted(expected):
            require(not is_cancelled())
            destination = stage / member
            for parent in reversed(destination.parent.parents):
                if parent == stage or stage in parent.parents:
                    if parent not in created:
                        parent.mkdir(mode=0o700)
                        created[parent] = directory_id(parent)
            if destination.parent not in created:
                destination.parent.mkdir(mode=0o700)
                created[destination.parent] = directory_id(destination.parent)
            digest, size = hashlib.sha256(), 0
            with destination.open('xb') as output:
                info = os.fstat(output.fileno())
                created[destination] = (info.st_dev, info.st_ino, info.st_mode)
                for block in source.chunks(member):
                    output.write(block)
                    digest.update(block)
                    size += len(block)
                output.flush()
                os.fsync(output.fileno())
            require(size == expected[member]['bytes'] and digest.hexdigest() == expected[member]['sha256'])
            validate_type(destination, member, families[member], limits[member])
        source._check()
        require(all(directory_id(path) == before for path, before in namespace_seals.items()))
        # Windows directory rename is atomic and refuses an existing target.
        # A concurrent legitimate creator wins; its full bytes are reverified.
        try:
            if target.exists():
                raise FileExistsError(errno.EEXIST, 'Existing derived cache')
            publish_owned(stage, target)
            stage = None
        except OSError as error:
            if error.errno not in (errno.EEXIST, errno.ENOTEMPTY) and not isinstance(error, FileExistsError):
                raise
        result = DerivedArchive(target, source, derivation, expected, namespace_seals, families, limits,
                                retain_json=JSON_CONSUMERS.get((app_id, kind, role), ()))
        source = None
        return result
    except DataIntakeBlocked:
        raise
    except OSError:
        raise DataIntakeBlocked('storage') from None
    except (ValueError, UnicodeError, OverflowError):
        raise DataIntakeBlocked('integrity') from None
    finally:
        if source is not None:
            source.close()
        cleanup_owned(stage, created)
