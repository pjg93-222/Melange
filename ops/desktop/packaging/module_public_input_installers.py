"""Fixed passive public consumers; no production application is enabled here.

These adapters never replace the original application roots, models, reports or
collectors. A reviewed ApplicationContract must explicitly select the adapter,
program closure and actual-server installation before module health exists.
"""
from dataclasses import dataclass
import hashlib
import importlib
import os
from pathlib import Path
import sys
from types import MappingProxyType
import weakref

from module_application_contracts import canonical, require
from module_data_handoff import InstalledInputs, PreparedHandoff
from module_data_snapshot import KINDS, Snapshot

PUBLIC_KINDS = MappingProxyType({
    'melange': 'melange.official-payroll-observations.v1',
    'mentat': 'mentat.public-fec-tables.v1',
})
PUBLIC_IDS = MappingProxyType({
    'melange': ('melange.public-data.catalogue', 'melange.public-data.provenance', 'melange.public-data.observations'),
    'mentat': ('mentat.public-data.catalogue', 'mentat.public-data.rows', 'mentat.public-data.download', 'mentat.public-data.provenance'),
})
PRIVATE_IDS = MappingProxyType({
    'melange': ('melange.original.dashboard', 'melange.original.source-root'),
    'mentat': ('mentat.original.console', 'mentat.original.console-root', 'mentat.original.reports', 'mentat.original.report-cache'),
})


def _program_module(source, app_id, *, server=False):
    """Normal import with fixed program paths, preserving canonical class identity."""
    source = Path(source)
    if app_id == 'melange':
        name = 'fec.surfaces.staffer_live_server' if server else 'fec.surfaces.melange_public_data'
        relative = 'fec/surfaces/staffer_live_server.py' if server else 'fec/surfaces/melange_public_data.py'
        paths = (str(source),)
    else:
        require(app_id == 'mentat')
        name = 'server' if server else 'public_data'
        relative = 'mentat/app/server.py' if server else 'mentat/app/public_data.py'
        paths = (str(source/'mentat'/'app'), str(source/'mentat'/'tools'), str(source))
    expected = source/relative
    from module_data_snapshot import regular
    for parent in (expected.parent, *expected.parent.parents):
        regular(parent, True)
    regular(expected)
    expected = expected.resolve(strict=True)
    if app_id == 'melange':
        for name_prefix, relative_prefix in (('fec','fec'),('fec.surfaces','fec/surfaces')):
            parent_module = sys.modules.get(name_prefix)
            if parent_module is not None:
                require(tuple(Path(path).resolve(strict=True) for path in parent_module.__path__)
                        == ((source/relative_prefix).resolve(strict=True),))
    prior = sys.modules.get(name)
    if prior is not None:
        require(Path(prior.__file__).resolve(strict=True) == expected)
    before, bytecode = list(sys.path), sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        sys.path[:0] = paths
        module = importlib.import_module(name)
    finally:
        sys.path[:] = before
        sys.dont_write_bytecode = bytecode
    require(Path(module.__file__).resolve(strict=True) == expected)
    return module


@dataclass(frozen=True)
class PublicComponent:
    snapshot: object
    reader: object
    module: object
    source_digest: str
    source_fingerprint: str


def prepare_public_component(snapshot, *, source, is_cancelled=lambda:False):
    require(type(snapshot) is Snapshot and snapshot.kind == PUBLIC_KINDS.get(snapshot.app)
            and type(source) is dict and source.get('appId') == snapshot.app
            and callable(is_cancelled) and not is_cancelled())
    module = _program_module(snapshot.source, snapshot.app)
    digest, fingerprint = source['manifestSha256'], hashlib.sha256(canonical(source)).hexdigest()
    if snapshot.app == 'melange':
        reader = module.prepare_public_data(snapshot, cancelled=is_cancelled)
        require(type(reader) is module.PublicDataCatalogue)
    else:
        reader = module.prepare(snapshot.root, source_digest=digest, source_fingerprint=fingerprint)
        require(type(reader) is module.Catalogue)
    try:
        require(not is_cancelled())
        component = PublicComponent(snapshot, reader, module, digest, fingerprint)
        return {'appId': snapshot.app, 'kind': snapshot.kind, 'reader': reader, 'component': component,
                'coverage': {'completeKind': True, 'fullApplication': False}}
    except BaseException:
        if callable(getattr(reader, 'close', None)):
            reader.close()
        raise


def _public_receipt(module, snapshot, raw):
    """Pure metadata checks only; actual consumer preparation also parses rows."""
    if snapshot.app == 'mentat':
        _value, documents = module._receipt(raw)
        require(set(documents) == set(snapshot.objects) - {'mentat.fec.provenance'})
        for role, item in documents.items():
            require(item['memberBytes'] == snapshot.objects[role]['bytes']
                    and item['memberSha256'] == snapshot.objects[role]['sha256'])
        return
    p, exact, integer = module.p, module._exact, module._int
    receipt = p.strict_json(raw)
    exact(receipt, module._RECEIPT)
    require(receipt['kind'] == module.KIND and type(receipt['schemaVersion']) is int and receipt['schemaVersion'] == 1)
    p._hash(receipt['programFingerprint'])
    exact(receipt['currentMapperFiles'], ('melange_public_provenance.py', 'melange_public_payroll_projection.py',
                                        'melange_public_payroll_normalize.py'))
    for value in receipt['currentMapperFiles'].values():
        p._hash(value)
    require(hashlib.sha256(p.canonical(receipt['currentMapperFiles'])).hexdigest() == receipt['programFingerprint'])
    module._manifest(receipt['sourceManifest'])
    require(hashlib.sha256(p.canonical(receipt['sourceManifest'])).hexdigest() == receipt['inputManifestDigest'])
    exact(receipt['recordCounts'], module.ROLES)
    for value in receipt['recordCounts'].values():
        integer(value, p.MAX_RECORDS, 1)
    exact(receipt['output'], ('format', 'bytes', 'sha256', 'records'))
    output = receipt['output']
    require(output['format'] == 'strict-utf8-ndjson' and type(output['bytes']) is int
            and 0 < output['bytes'] <= module.MAX_BYTES and type(output['records']) is int
            and 0 < output['records'] <= module.MAX_RECORDS
            and output['bytes'] == snapshot.objects['observations']['bytes']
            and output['sha256'] == snapshot.objects['observations']['sha256']
            and hashlib.sha256(raw).hexdigest() == snapshot.objects['receipt']['sha256'])
    exact(receipt['canonicalPromotions'], ('identity', 'employment', 'office', 'date'))
    require(all(type(value) is int and value == 0 for value in receipt['canonicalPromotions'].values()))
    exact(receipt['coverage'], ('sourceNativeObservations', 'fullApplication'))
    require(receipt['coverage']['sourceNativeObservations'] is True and receipt['coverage']['fullApplication'] is False)
    exact(receipt['normalizationCounts'], ('houseCsvFieldEquivalentRows', 'housePdfCandidateJoins', 'senateAcceptedSubsequence',
        'senateRawRecords', 'senateExcludedRecords', 'senateAcceptedRepairs'))
    for value in receipt['normalizationCounts'].values():
        integer(value, p.MAX_RECORDS)
    inputs = {item['role']: item['records'] for item in receipt['sourceManifest']['inputs']}
    require(all(inputs[role] == receipt['recordCounts'][role] for role in module.ROLES))
    require(receipt['provenanceStatus'] == {'currentMapper': 'EXACT_CODE_CLOSURE',
        'historicalProducer': 'SEE_SOURCE_RECEIPTS_NOT_INFERRED_FROM_CURRENT_CODE',
        'sourceExtraction': 'RECEIPT_REPORTED_NOT_INDEPENDENTLY_REPLAYED'})


def validate_public_snapshot(snapshot, *, is_cancelled=lambda:False):
    """Stage-ready metadata/integrity probe, never installed application health.

    Hash every fixed object and validate closed-tree/receipt schema without
    constructing a Catalogue or parsing observation/table rows. The actual
    handoff still invokes the full factory before original-root writes.
    """
    require(type(snapshot) is Snapshot and snapshot.kind == PUBLIC_KINDS.get(snapshot.app)
            and callable(is_cancelled) and not is_cancelled())
    from module_data_launch import ReadView
    roles = KINDS[snapshot.kind][1]
    require(set(snapshot.files) == set(roles) and set(snapshot.objects) == set(roles))
    files = {relative for relative, _limit in roles.values()}
    directories = {parent.as_posix() for relative in files for parent in Path(relative).parents
                   if parent != Path('.')}
    view = ReadView(snapshot.root, snapshot.root)
    view.closure(snapshot.root, files, directories)
    receipt_role = 'receipt' if snapshot.app == 'melange' else 'mentat.fec.provenance'
    raw = None
    for role, (relative, limit) in roles.items():
        require(not is_cancelled() and snapshot.files[role] == snapshot.root / relative)
        spec = snapshot.objects[role]
        value = view.read(snapshot.files[role], limit, expected_bytes=spec['bytes'], expected_sha=spec['sha256'],
                          retain=role == receipt_role)
        if role == receipt_role:
            raw = value
    require(not is_cancelled())
    module = _program_module(snapshot.source, snapshot.app)
    _public_receipt(module, snapshot, raw)
    view.unchanged()
    require(not is_cancelled())


_REGISTRIES = MappingProxyType({app: MappingProxyType({kind: prepare_public_component})
                               for app, kind in PUBLIC_KINDS.items()})


def prepare_public_readers(**options):
    """Compiled contract entry: one fixed public kind, never all legacy cores."""
    app_id = options.get('app_id')
    require(app_id in PUBLIC_KINDS and tuple(options.get('required_kinds', ())) == (PUBLIC_KINDS[app_id],))
    from module_data_launch import prepare_module_readers
    return prepare_module_readers(**options, reader_registry=_REGISTRIES[app_id])


def public_reader(prepared):
    require(type(prepared) is PreparedHandoff)
    app = prepared.contract.app_id
    kind = PUBLIC_KINDS.get(app)
    require(prepared.contract.required_kinds == (kind,) and set(prepared.readers) == {kind})
    bound = prepared.readers[kind]
    component = bound.get('component') if type(bound) is dict else None
    require(type(component) is PublicComponent and type(component.snapshot) is Snapshot
            and component.snapshot.kind == kind and component.snapshot.app == app
            and bound.get('reader') is component.reader
            and component.source_digest == prepared.binding['sourceDigest']
            and component.source_fingerprint == prepared.binding['sourceFingerprint'])
    module = _program_module(prepared.roots['sourceRoot'], app)
    require(module is component.module and type(component.reader) is (
        module.PublicDataCatalogue if app == 'melange' else module.Catalogue))
    return component.reader


def private_program_guard(source):
    """Retain already-loaded original path/alias objects without reading data.

    No private module is imported or private directory/file enumerated. Mutable
    application caches are ordinary state; their contents are not a data seal.
    """
    source = Path(source).resolve(strict=True)/'mentat'
    values = []
    for module in tuple(sys.modules.values()):
        filename = getattr(module, '__file__', None)
        if not filename:
            continue
        try:
            if not Path(filename).resolve().is_relative_to(source):
                continue
        except (OSError, ValueError):
            continue
        for key, value in tuple(vars(module).items()):
            if isinstance(value, Path) or (module.__name__ == 'runtime_paths' and callable(value)
                    and key in ('data_root', 'workspace_root', 'app_data_root', 'forecast_data_root',
                                'console_root', 'report_cache_root', 'resolve_receipt')):
                values.append((module, key, value))
    require(len(values) <= 8192)
    def unchanged():
        return all(getattr(module, key, None) is value for module, key, value in values)
    return unchanged


def _same_path(value, expected):
    require(isinstance(value, Path) and Path(expected).is_absolute()
            and os.path.normcase(str(value.resolve())) == os.path.normcase(str(Path(expected).resolve())))


_CAPTURED = weakref.WeakKeyDictionary()


def capture_originals(prepared, server, *, console_root=None, reports_root=None, program_guard=lambda:True):
    """Called only by the backend's trusted actual-server callback."""
    require(type(prepared) is PreparedHandoff and prepared not in _CAPTURED and callable(program_guard)
            and program_guard() is True)
    app = prepared.contract.app_id
    module = _program_module(prepared.roots['sourceRoot'], app, server=True)
    refs, locations = [], []
    if app == 'melange':
        require(type(server) is module.WorkspaceServer)
        service = server.dashboard
        from fec.surfaces.staffer_live_service import LiveService
        from fec.surfaces.staffer_graph_snapshot import StaticGraph
        require(type(service) is LiveService and type(service.static) is StaticGraph
                and type(service.profiles) is module.IncrementalProfiles)
        _same_path(service.source_root, prepared.roots['originalDataRoot'])
        require(not Path(service.source_root).resolve().is_relative_to(Path(prepared.source['cacheRoot']).resolve()))
        originals = dict(zip(PRIVATE_IDS[app], (service, service.source_root)))
        refs = [(server, 'dashboard', service), (service, 'source_root', service.source_root)]
        refs.extend(((service,'static',service.static),(service,'profiles',service.profiles)))
        original=Path(prepared.roots['originalDataRoot'])
        graph_root=original if original.name=='staffer_network' else original/'audits/staffer_network'
        raw_profiles=original/'audits/staffer_network/politico_profile_crawl_20260903_raw'
        locations.extend(((service.static,'root',graph_root),(service.profiles,'raw_dir',raw_profiles),
                          (service.profiles,'path',raw_profiles/'profiles.ndjson')))
        for obj,key,expected in locations:
            _same_path(getattr(obj,key,None),expected)
            refs.append((obj,key,getattr(obj,key)))
    else:
        require(app == 'mentat' and type(server) is module.ThreadingHTTPServer and type(server.app) is module.Console)
        console = server.app
        _same_path(console.root, console_root)
        _same_path(console.report_directory, reports_root)
        for root in (console.root, console.report_directory):
            cache = Path(prepared.source['cacheRoot']).resolve()
            require(root.resolve() != cache and not root.resolve().is_relative_to(cache) and not cache.is_relative_to(root.resolve()))
        require(type(console.report_cache) is dict)
        originals = dict(zip(PRIVATE_IDS[app], (console, console.root, console.report_directory, console.report_cache)))
        refs = [(server, 'app', console), (console, 'root', console.root),
                (console, 'report_directory', console.report_directory), (console, 'report_cache', console.report_cache)]
    require(set(prepared.contract.private_boundaries) == set(PRIVATE_IDS[app]))
    _CAPTURED[prepared] = (server, dict(originals), tuple(refs), tuple(locations), program_guard)
    return originals


def install_public_readers(prepared, server, originals):
    """Verify the actual consumer attachment; never attach downloaded objects."""
    app = prepared.contract.app_id
    require(prepared in _CAPTURED and set(prepared.contract.public_readers) == set(PUBLIC_IDS[app]))
    actual, captured, refs, locations, program_guard = _CAPTURED[prepared]
    require(actual is server and set(originals) == set(captured)
            and all(originals[key] is captured[key] for key in captured))
    reader = public_reader(prepared)
    host = server if app == 'melange' else server.app
    require(host.public_data is reader)
    methods = ('catalogue', 'provenance', 'observations') if app == 'melange' else ('catalogue', 'rows', 'download', 'provenance')
    compiled = tuple((name, getattr(type(reader), name)) for name in methods)
    def verify():
        for obj,key,expected in locations:
            _same_path(getattr(obj,key,None),expected)
        return (host.public_data is reader and not getattr(reader, '_closed', False) and program_guard() is True
                and all(getattr(obj, name, None) is value for obj, name, value in refs)
                and all(callable(getattr(reader, name, None)) and getattr(type(reader), name) is method
                        and getattr(reader, name).__self__ is reader and getattr(reader, name).__func__ is method
                        for name, method in compiled))
    require(verify() is True)
    return InstalledInputs(server, {key: reader for key in PUBLIC_IDS[app]}, dict(captured), verify)
