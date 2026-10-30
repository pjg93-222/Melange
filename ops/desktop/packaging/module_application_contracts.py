"""Compiled application input contracts, verified against installed program bytes.

Source inventories are evidence, not authority. Only a reviewed compiled entry
may name consumers, installer callables and the expected installed program hash.
Old component kinds retain fullApplication:false and are not implied inputs.
"""
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import threading
from types import MappingProxyType


class ModuleInputError(ValueError):
    def __init__(self):
        super().__init__('Native module input is unavailable.')


class DataIntakeBlocked(ModuleInputError):
    """A known cached-input failure, never an import/program/factory exception."""
    def __init__(self, reason='integrity'):
        super().__init__()
        if reason not in ('integrity', 'storage'):
            raise ValueError('Invalid data intake status')
        self.reason = reason
        self.native_status = None


def require(value):
    if not value:
        raise ModuleInputError()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                      allow_nan=False).encode('utf-8', errors='strict')


def names(values, prefix=None):
    return (type(values) is tuple and 0 < len(values) <= 128
            and all(type(value) is str and re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', value)
                    and (prefix is None or value.startswith(prefix)) for value in values)
            and len(set(values)) == len(values))


@dataclass(frozen=True)
class ProgramFile:
    root: str
    path: str
    bytes: int
    sha256: str

    def __post_init__(self):
        require(self.root in ('source', 'bootstrap') and type(self.path) is str
                and 0 < len(self.path) <= 400 and all(re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9._-]{0,127}', part)
                    and not part.endswith('.') and not re.match(r'(?i)^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)',part)
                    for part in self.path.split('/'))
                and type(self.bytes) is int and 0 <= self.bytes <= 16 * 1024**2
                and type(self.sha256) is str and re.fullmatch(r'[a-f0-9]{64}', self.sha256))


def program_fingerprint(files):
    require(type(files) is tuple and 0 < len(files) <= 512
            and all(type(item) is ProgramFile for item in files)
            and sum(item.bytes for item in files) <= 64 * 1024**2)
    keys = [(item.root, item.path.casefold()) for item in files]
    require(len(set(keys)) == len(keys))
    inventory = [{'root': item.root, 'path': item.path, 'bytes': item.bytes, 'sha256': item.sha256}
                 for item in sorted(files, key=lambda item: (item.root, item.path))]
    return hashlib.sha256(canonical(inventory)).hexdigest()


@dataclass(frozen=True)
class ApplicationContract:
    app_id: str
    contract_id: str
    program_fingerprint: str
    program_files: tuple
    required_kinds: tuple
    public_readers: tuple
    private_boundaries: tuple
    prepare_readers: object
    install_readers: object
    startup_timeout_ms: int = 120000

    def __post_init__(self):
        require(self.app_id in ('melange', 'mentat') and type(self.contract_id) is str
                and re.fullmatch(r'[a-z0-9][a-z0-9._-]{0,127}', self.contract_id)
                and self.program_fingerprint == program_fingerprint(self.program_files)
                and names(self.required_kinds, self.app_id + '.')
                and names(self.public_readers) and names(self.private_boundaries)
                and callable(self.prepare_readers) and callable(self.install_readers)
                and type(self.startup_timeout_ms) is int and 1000 <= self.startup_timeout_ms <= 600000)


_FIELDS = frozenset(('schemaVersion', 'appId', 'contractId', 'programFiles', 'programFingerprint',
                     'requiredKinds', 'publicReaders', 'privateBoundaries', 'startupTimeoutMs'))
_SHARED = frozenset(('desktop_backend.py', 'desktop_workspace.py', 'module_application_contracts.py', 'module_data_handoff.py',
                     'module_data_launch.py', 'module_data_snapshot.py', 'module_public_input_installers.py',
                     'workspace_data_contract.py', 'module_workspace_handoff.py',
                     'workspace_archive.py', 'workspace_sqlite.py', 'workspace_graph.py', 'workspace_cache.py',
                     'module_workspace_inputs.py', 'workspace_melange.py', 'workspace_mentat.py', 'module_workspace_installers.py',
                     'module_workspace_render.py', 'module_workspace_ui_templates.py',
                     'module_workspace_combined_ui.py', 'module_workspace_industry_ui.py'))
_APPLICATION = MappingProxyType({
    'melange': frozenset(('fec/surfaces/melange_public_data.py', 'fec/surfaces/staffer_live_server.py',
        'fec/surfaces/melange_public_pages.py', 'fec/surfaces/demand_data.py',
        'fec/surfaces/staffer_live_service.py', 'fec/surfaces/staffer_graph_snapshot.py',
        'fec/surfaces/public_data/index.html', 'fec/surfaces/public_data/public-data.js',
        'fec/surfaces/public_data/public-data.css')),
    'mentat': frozenset(('mentat/app/public_data.py', 'mentat/app/server.py',
        'mentat/app/console_page.py', 'mentat/app/templates/view_public_data.html',
        'mentat/app/public_data.js')),
})


def application_contract(app_id, contract_id):
    """Fixed packaged declarations and factories, never downloaded selectors.

    Constructing a contract grants no launch authority. The independently bound
    installed source/bootstrap closure must still pass verify_program in the
    framed native handoff before consumer preparation or original-root writes.
    """
    paged = app_id == 'melange' and contract_id == 'melange.public-data.pages.v1'
    workspace = app_id in _APPLICATION and contract_id == app_id + '.workspace.v1'
    if app_id not in _APPLICATION or (contract_id != app_id + '.public-data.v1' and not paged and not workspace):
        return None
    from module_application_inventory import APPLICATION_SPECS
    from module_public_input_installers import PUBLIC_KINDS, PUBLIC_IDS, PRIVATE_IDS, PAGED_KIND
    from module_public_input_installers import prepare_public_readers, install_public_readers
    spec = APPLICATION_SPECS[app_id]
    require(type(spec) is MappingProxyType and set(spec) == _FIELDS
            and spec['contractId'] == app_id + '.public-data.v1'
            and spec['requiredKinds'] == (PUBLIC_KINDS[app_id],)
            and spec['publicReaders'] == PUBLIC_IDS[app_id]
            and spec['privateBoundaries'] == PRIVATE_IDS[app_id])
    # Both independently verified inputs bind the SAME installed program union.
    # Only fixed compiled metadata/factories differ, never a downloaded selector.
    kinds, readers, boundaries = (PUBLIC_KINDS[app_id],), PUBLIC_IDS[app_id], PRIVATE_IDS[app_id]
    prepare, install = prepare_public_readers, install_public_readers
    if paged:
        spec = MappingProxyType({**spec, 'contractId': contract_id, 'requiredKinds': (PAGED_KIND,)})
        kinds = (PAGED_KIND,)
    if workspace:
        from workspace_data_contract import WORKSPACE_KINDS, WORKSPACE_READERS, WORKSPACE_PRIVATE_BOUNDARIES
        from module_workspace_installers import prepare_workspace_readers, install_workspace_readers
        kinds, readers, boundaries = WORKSPACE_KINDS[app_id], WORKSPACE_READERS[app_id], WORKSPACE_PRIVATE_BOUNDARIES[app_id]
        prepare, install = prepare_workspace_readers, install_workspace_readers
        spec = MappingProxyType({**spec, 'contractId': contract_id, 'requiredKinds': kinds,
            'publicReaders': readers, 'privateBoundaries': boundaries})
    require(type(spec) is MappingProxyType and set(spec) == _FIELDS
            and type(spec['schemaVersion']) is int and spec['schemaVersion'] == 1
            and spec['appId'] == app_id and spec['contractId'] == contract_id
            and spec['requiredKinds'] == kinds
            and spec['publicReaders'] == readers and spec['privateBoundaries'] == boundaries
            and type(spec['startupTimeoutMs']) is int
            and spec['startupTimeoutMs'] == (600000 if app_id == 'melange' else 300000)
            and type(spec['programFiles']) is tuple)
    rows = spec['programFiles']
    require(all(type(row) is MappingProxyType and set(row) == {'root', 'path', 'bytes', 'sha256'} for row in rows))
    files = tuple(ProgramFile(**row) for row in rows)
    paths = {(item.root, item.path) for item in files}
    require(all(('bootstrap', path) in paths for path in _SHARED)
            and (app_id != 'melange' or all(('bootstrap', path) in paths
                 for path in ('module_catalogue_cache.py', 'native_access_state.py')))
            and all(('source', path) in paths for path in _APPLICATION[app_id])
            and not any(item.path.endswith(('module_application_inventory.py', 'module-application-inventory.cjs'))
                        for item in files))
    if workspace:
        required = ('module_workspace_installers.py', 'module_workspace_inputs.py',
                    'workspace_archive.py', 'workspace_sqlite.py', 'workspace_graph.py',
                    'workspace_cache.py', 'workspace_' + app_id + '.py')
        if app_id == 'melange':
            required += ('module_workspace_render.py', 'module_workspace_ui_templates.py',
                         'module_workspace_combined_ui.py', 'module_workspace_industry_ui.py', 'melange_module_data.py')
        else:
            required += ('mentat_module_data.py',)
        require(all(('bootstrap', path) in paths for path in required))
    return ApplicationContract(app_id, contract_id, spec['programFingerprint'], files,
        spec['requiredKinds'], spec['publicReaders'], spec['privateBoundaries'],
        prepare, install, spec['startupTimeoutMs'])


def _stamp(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def _opened(info):
    # Windows lstat/fstat can report different creation timestamps. Retain exact
    # timestamps independently for each API, exact inode/size across both.
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns)


def _regular(path, directory=False):
    info = path.lstat()
    require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0)
            & getattr(stat, 'FILE_ATTRIBUTE_REPARSE_POINT', 0x400)
            and (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode) and info.st_nlink == 1))
    return info


def verify_program(contract, *, source_root, bootstrap_root):
    """Read only the compiled table, never a downloaded inventory or import path."""
    require(type(contract) is ApplicationContract)
    return verify_compiled_files(contract.program_files, contract.program_fingerprint,
                                 source_root=source_root, bootstrap_root=bootstrap_root)


_VERIFIED, _VERIFY_LOCK = {}, threading.Lock()


def _root_ids(roots):
    return tuple((r, (lambda i: (i.st_dev, i.st_ino, i.st_mode))(_regular(Path(r), True))) for r in roots)


def verify_generation(key, roots, verify, *, full, kind):
    """One full scan per launch generation; ordinary callers only recheck root identity."""
    try:
        state = _VERIFIED.get(key)
        if not full and state:
            require(_root_ids(roots) == state)
            return True
        with _VERIFY_LOCK:  # ponytail: one process-wide lock, at most 2 generations per process
            state = _VERIFIED.get(key)
            require(state is not False)  # a poisoned generation fails closed until restart
            if not full and state:
                require(_root_ids(roots) == state)
                return True
            try:
                verify()
            except Exception:
                _VERIFIED[key] = False
                raise
            _VERIFIED[key] = _root_ids(roots)
            sys.stderr.write('DESKTOP_PROGRAM_VERIFIED kind=' + kind + '\n')  # stderr: stdout carries diagnostics
            sys.stderr.flush()
            return True
    except OSError:
        raise ModuleInputError() from None


def verify_compiled_files(files, fingerprint, *, source_root, bootstrap_root):
    """Shared byte verifier for compiled application and district-probe tables."""
    try:
        require(fingerprint == program_fingerprint(files))
        roots = {}
        for name, value in (('source', source_root), ('bootstrap', bootstrap_root)):
            path = Path(value)
            require(path.is_absolute())
            for parent in (path, *path.parents):
                _regular(parent, True)
            roots[name] = path.resolve(strict=True)
        for root in roots.values():
            _regular(root, True)
        directories = {}
        for item in files:
            root = roots[item.root]
            current = root
            for part in ('', *item.path.split('/')[:-1]):
                if part:
                    current = current / part
                before = _regular(current, True)
                require(current.resolve(strict=True).is_relative_to(root))
                prior = directories.get(current)
                require(prior is None or _stamp(prior) == _stamp(before))
                directories[current] = before
            path = current / item.path.split('/')[-1]
            before = _regular(path)
            require(before.st_size == item.bytes and path.resolve(strict=True).is_relative_to(root))
            flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
            with os.fdopen(os.open(path, flags), 'rb') as stream:
                opened = os.fstat(stream.fileno())
                require(stat.S_ISREG(opened.st_mode) and opened.st_nlink == 1 and _opened(opened) == _opened(before))
                digest = hashlib.sha256()
                received = 0
                for block in iter(lambda: stream.read(65536), b''):
                    received += len(block)
                    require(received <= item.bytes)
                    digest.update(block)
                after, named = os.fstat(stream.fileno()), _regular(path)
                require(received == item.bytes and digest.hexdigest() == item.sha256
                        and _stamp(opened) == _stamp(after) and _stamp(before) == _stamp(named)
                        and _opened(after) == _opened(named))
        for path, before in directories.items():
            require(_stamp(before) == _stamp(_regular(path, True)))
        return True
    except (OSError, ValueError, TypeError, AttributeError):
        raise ModuleInputError() from None


# Public serving inputs delivered as pages under melange.public-data.pages.v1.
# Each module is one canonical data file (or one file per partition). Pages carry
# the original bytes, split only at line ends, so Decimal lexemes and key order
# survive exactly; parsing here is for checking and never re-serializes.
# Approved-only, user and secret inputs never get an entry (see the serving
# inventory under audits/reliability_2026-10).
PAGES_CONTRACT = 'melange.public-data.pages.v1'
MAX_PAGE_BYTES = 16 * 1024**2
MAX_MODULE_INDEX_BYTES = 2 * 1024**2
MiB = 1024**2


@dataclass(frozen=True)
class PagedModule:
    module_id: str
    source: str
    format: str
    required_keys: tuple = ()
    partition_key: str = None
    partitions: tuple = ('',)
    max_source_bytes: int = MAX_PAGE_BYTES

    def __post_init__(self):
        require(re.fullmatch(r'melange\.[a-z0-9][a-z0-9.-]{0,100}\.v[0-9]+', self.module_id)
                and self.format in ('json', 'ndjson') and '..' not in self.source
                and re.fullmatch(r'data/[a-z0-9_/{}.-]{1,200}', self.source)
                and ('{partition}' in self.source) == (self.partition_key is not None)
                and (self.partition_key is None or (self.partitions and '' not in self.partitions))
                and type(self.max_source_bytes) is int and 0 < self.max_source_bytes <= 256 * MiB
                and (self.format == 'ndjson' or self.max_source_bytes <= MAX_PAGE_BYTES))

    def path(self, partition=''):
        require(partition in self.partitions)
        return self.source.replace('{partition}', partition)


def _module(module_id, source, required_keys=(), **options):
    return module_id, PagedModule(module_id, source, 'ndjson' if source.endswith('.ndjson') else 'json',
                                  tuple(required_keys), **options)


PAGED_MODULES = MappingProxyType(dict((
    _module('melange.staffer-network-section.v1', 'data/engine/staffer_network_section.json',
            ('global', 'members', 'meta'), max_source_bytes=12 * MiB),
    _module('melange.staffer-offices-section.v1', 'data/engine/staffer_offices_section.json',
            ('meta', 'offices'), max_source_bytes=12 * MiB),
    _module('melange.staffer-organisations-section.v1', 'data/engine/staffer_organisations_section.json',
            ('meta', 'organisations'), max_source_bytes=12 * MiB),
    _module('melange.staffer-clients-section.v1', 'data/engine/staffer_clients_section.json',
            ('meta',), max_source_bytes=12 * MiB),
    _module('melange.district-brief-evidence.v1', 'data/district/district_brief_evidence_v1.json',
            ('schema', 'members'), max_source_bytes=12 * MiB),
    _module('melange.district-briefs.v1', 'data/district/district_briefs_v1.json',
            ('schema', 'briefs', 'evidence_sha256'), max_source_bytes=4 * MiB),
    _module('melange.district-employers.v1', 'data/district/district_employers.json',
            ('schema', 'districts'), max_source_bytes=4 * MiB),
    _module('melange.district-community.v1', 'data/district/district_community.json',
            ('schema', 'districts'), max_source_bytes=4 * MiB),
    _module('melange.roster.v1', 'data/engine/roster.json', ('schema', 'members'), max_source_bytes=4 * MiB),
    _module('melange.responsiveness-layers.v1', 'data/engine/responsiveness_layers.json',
            ('schema', 'members'), max_source_bytes=8 * MiB),
    _module('melange.efficiency-layers.v1', 'data/engine/efficiency_layers.json',
            ('schema', 'members'), max_source_bytes=4 * MiB),
    _module('melange.holistic-sectorcache.v1', 'data/holistic/sectorcache_{partition}.ndjson', ('congress',),
            partition_key='congress', partitions=('117', '118', '119'), max_source_bytes=64 * MiB),
    _module('melange.holistic-billcache.v1', 'data/holistic/billcache_{partition}.ndjson', ('congress',),
            partition_key='congress', partitions=('117', '118', '119'), max_source_bytes=64 * MiB),
    # Collector outputs, installed by the collector itself (see COLLECTOR_MODULES).
    _module('melange.official-rollcall-manifest.v1', 'data/legislation/official_rollcall/manifest.json',
            ('schema', 'acceptance_passed', 'outputs'), max_source_bytes=4 * MiB),
    _module('melange.official-rollcall-aggregate.v1',
            'data/legislation/official_rollcall/official_rollcall_aggregate.json',
            ('schema', 'members', 'cells'), max_source_bytes=16 * MiB),
    # ponytail: one unpartitioned file (~0.5 MB per roll call); rows carry no integer partition key.
    _module('melange.official-rollcall-member-votes.v1',
            'data/legislation/official_rollcall/official_rollcall_member_votes.ndjson',
            ('schema', 'event_id', 'bioguide_id'), max_source_bytes=256 * MiB),
    _module('melange.official-rollcall-event-ledger.v1',
            'data/legislation/official_rollcall/official_rollcall_event_ledger.ndjson',
            ('schema', 'event_id'), max_source_bytes=64 * MiB),
    _module('melange.official-rollcall-measure-match-audit.v1',
            'data/legislation/official_rollcall/rollcall_measure_match_audit.ndjson',
            ('schema', 'canonical_key'), max_source_bytes=16 * MiB),
    _module('melange.official-rollcall-direction-audit.v1',
            'data/legislation/official_rollcall/rollcall_direction_audit.ndjson',
            ('schema', 'canonical_key'), max_source_bytes=16 * MiB),
    _module('melange.official-rollcall-source-snapshots.v1',
            'data/legislation/official_rollcall/source_snapshots.ndjson',
            ('schema', 'content_sha256'), max_source_bytes=16 * MiB),
    _module('melange.fec-money-refresh.v1', 'data/money/fec_refresh_current.json',
            ('schema', 'status', 'checked_at', 'cycle', 'output', 'sources'), max_source_bytes=4 * MiB),
)))

# The modules each collector installs and must publish after a completed run.
# fec/generation_publish_hook.after_collection refuses a source not named here.
COLLECTOR_MODULES = MappingProxyType({
    'official-rollcall': ('melange.official-rollcall-manifest.v1', 'melange.official-rollcall-aggregate.v1',
                          'melange.official-rollcall-member-votes.v1', 'melange.official-rollcall-event-ledger.v1',
                          'melange.official-rollcall-measure-match-audit.v1',
                          'melange.official-rollcall-direction-audit.v1',
                          'melange.official-rollcall-source-snapshots.v1'),
    'fec-money': ('melange.fec-money-refresh.v1',),
})


def paged_module(module_id):
    module = PAGED_MODULES.get(module_id)
    require(type(module) is PagedModule)
    return module


def _strict_value(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result)
            result[key] = value
        return result
    def constant(_name):
        raise ModuleInputError()
    require(type(raw) is bytes and not raw.startswith(b'\xef\xbb\xbf'))
    from decimal import Decimal
    return json.loads(raw.decode('utf-8', errors='strict'), object_pairs_hook=pairs,
                      parse_float=Decimal, parse_constant=constant)


def check_module_bytes(module, partition, raw):
    """Refuse bytes that break the module contract; return the record count."""
    require(type(module) is PagedModule and partition in module.partitions
            and type(raw) is bytes and 0 < len(raw) <= module.max_source_bytes)
    if module.format == 'json':
        value = _strict_value(raw)
        require(type(value) is dict and all(key in value for key in module.required_keys))
        return 1
    require(raw.endswith(b'\n'))
    count = 0
    for line in raw.splitlines(keepends=True):
        require(line.endswith(b'\n') and not line.endswith(b'\r\n') and len(line) <= MAX_PAGE_BYTES)
        row = _strict_value(line)
        require(type(row) is dict and all(key in row for key in module.required_keys))
        if module.partition_key is not None:
            value = row[module.partition_key]
            require(type(value) is int and str(value) == partition)
        count += 1
    return count


def split_pages(module, raw, page_bytes=MAX_PAGE_BYTES):
    """Original bytes in order; NDJSON pages end on a record boundary."""
    require(type(page_bytes) is int and 1 <= page_bytes <= MAX_PAGE_BYTES)
    if module.format == 'json':
        require(len(raw) <= page_bytes)
        return [raw]
    pages, page = [], bytearray()
    for line in raw.splitlines(keepends=True):
        require(len(line) <= page_bytes)
        if page and len(page) + len(line) > page_bytes:
            pages.append(bytes(page)); page = bytearray()
        page.extend(line)
    if page:
        pages.append(bytes(page))
    require(b''.join(pages) == raw)
    return pages
