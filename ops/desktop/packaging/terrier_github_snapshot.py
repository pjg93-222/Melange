"""Activate the real, signed public row-framework snapshot in separate local state."""
from contextlib import closing
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import sys
import tempfile

BASE_FILES = frozenset({'manifest.json', 'rows.json', 'geometry.json', 'streets.geojson',
                        'district.geojson', 'area_indices.json', 'adjacency.json'})
SNAPSHOT_KEY = re.compile(r'(?:co-cd005|or-cd005|ct-cd001)-[a-f0-9]{12}')
DERIVED_FILE = re.compile(r'[A-Za-z0-9_-]+\.json(?:\.gz)?')


def snapshot_role(role):
    parts = role.split('/') if isinstance(role, str) else []
    return (len(parts) == 3 and parts[0] == 'snapshots' and SNAPSHOT_KEY.fullmatch(parts[1])
            and parts[2] in BASE_FILES) or (len(parts) == 4 and parts[0] == 'snapshots'
            and SNAPSHOT_KEY.fullmatch(parts[1]) and parts[2] == 'derived'
            and DERIVED_FILE.fullmatch(parts[3]))


def regular_file(file, root):
    file, root = Path(file), Path(root).resolve(strict=True)
    if not file.is_relative_to(root):
        raise ValueError('Snapshot file leaves its root.')
    current = root
    for part in file.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('Snapshot links are not allowed.')
    if not file.is_file() or file.resolve(strict=True) != file:
        raise ValueError('A snapshot file is missing or unsafe.')
    return file


def select_snapshot(source, data, district):
    """Read metadata only; select by district/source and the score store's area-table hash."""
    source, data = Path(source).resolve(strict=True), Path(data).resolve(strict=True)
    if str(source) not in sys.path:
        sys.path.insert(0, str(source))
    from tools import districts
    definition = districts.get(district)
    scores = regular_file(data / 'scores.sqlite3', data)
    with closing(sqlite3.connect(scores.as_uri() + '?mode=ro&immutable=1', uri=True)) as db:
        rows = db.execute("SELECT value FROM metadata WHERE key='area_table_sha256'").fetchall()
    if len(rows) != 1:
        raise ValueError('The score store lacks its row-framework source binding.')
    area_hash = json.loads(rows[0][0])
    if not isinstance(area_hash, str) or not re.fullmatch('[a-f0-9]{64}', area_hash):
        raise ValueError('Invalid row-framework source binding.')
    root = data / 'snapshots'
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True) != root:
        raise ValueError('The verified district has no row-framework snapshots.')
    candidates = []
    directories = list(root.iterdir())
    if len(directories) > 32:
        raise ValueError('Too many public snapshot candidates.')
    for directory in directories:
        if directory.is_symlink() or not directory.is_dir() or not SNAPSHOT_KEY.fullmatch(directory.name):
            raise ValueError('Unsafe public snapshot directory.')
        file = regular_file(directory / 'manifest.json', root)
        if file.stat().st_size > 512 * 1024:
            raise ValueError('Snapshot manifest exceeds its limit.')
        manifest = json.loads(file.read_text(encoding='utf-8'))
        if manifest.get('schema') != 'cu-summary-v4':
            continue
        if (manifest.get('snapshot') != directory.name
                or not re.fullmatch(districts.snapshot_pattern(definition), directory.name)
                ):
            raise ValueError('A public snapshot belongs to another district or source.')
        if manifest.get('source_sha256') != definition['sha256'] or manifest.get('row_framework', {}).get('area_table_sha256') != area_hash:
            continue
        files = [regular_file(directory / name, directory) for name in BASE_FILES]
        if sum(file.stat().st_size for file in files) > 200 * 1024 * 1024:
            raise ValueError('Row-framework summary exceeds its import limit.')
        candidates.append((directory, manifest))
    if len(candidates) != 1:
        raise ValueError('Exactly one verified row-framework snapshot must match the score store.')
    return candidates[0]


def _fingerprint(file):
    stat = file.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


class PreparedSnapshot:
    """An actual candidate reader; active state changes only on native commit."""
    def __init__(self, key, manifest, verify, *, retain_reader=False):
        self.key, self.manifest, self.verify = key, manifest, verify
        self.committed = False
        self.retain_reader = retain_reader
        self.previous_active = None
        if retain_reader:
            from server.research.models import Snapshot
            self.previous_active = tuple(sorted(Snapshot.objects.filter(active=True).values_list('key', flat=True)))

    def commit(self):
        from django.db import transaction
        from server.research import bundles
        from server.research.models import Snapshot, AuditEvent
        self.verify()
        with transaction.atomic():
            if self.previous_active is not None:
                current = tuple(sorted(Snapshot.objects.filter(active=True).values_list('key', flat=True)))
                if current != self.previous_active and current != (self.key,):
                    raise ValueError('Another district source became active before this candidate.')
            snapshot, _ = Snapshot.objects.get_or_create(key=self.key, defaults={'manifest': self.manifest})
            if snapshot.manifest != self.manifest:
                raise ValueError('An existing snapshot row has conflicting content.')
            changed = not snapshot.active or Snapshot.objects.filter(active=True).exclude(pk=snapshot.pk).exists()
            if changed:
                Snapshot.objects.filter(active=True).exclude(pk=snapshot.pk).update(active=False)
                snapshot.active = True
                snapshot.save(update_fields=['active'])
                AuditEvent.objects.create(actor='desktop public district data', action='snapshot.import', detail={'snapshot': self.key})
            self.verify()
        self.committed = True
        if self.retain_reader:
            # Raw readers are keyed by explicit immutable snapshot key. Clear
            # the derived current-active caches without reparsing that reader.
            for clear in tuple(bundles.dependents):
                clear()
        else:
            bundles.load.cache_clear()

    def health(self):
        from server.research.models import Snapshot
        self.verify()
        if self.committed and list(Snapshot.objects.filter(active=True).values_list('key', flat=True)) != [self.key]:
            raise ValueError('The active snapshot differs from the prepared reader.')
        return {'snapshot': self.key, 'phase': 'active' if self.committed else 'prepared'}


def activate_snapshot(source, data, state, district, *, defer_activation=False):
    """Validate authentic summary data, preserve old snapshots/views, and activate transactionally."""
    from django.db import transaction
    from server.research import bundles
    from server.research.models import Snapshot, AuditEvent
    directory, manifest = select_snapshot(source, data, district)
    before = {name: _fingerprint(directory / name) for name in BASE_FILES}
    payload = {name: json.loads((directory / name).read_text(encoding='utf-8')) for name in BASE_FILES}
    manifest = bundles.validate(payload)
    key = manifest['snapshot']
    state = Path(state).resolve(strict=True)
    if state == directory or state.is_relative_to(Path(data).resolve(strict=True)):
        raise ValueError('Snapshot account state must remain separate from public data.')
    root = state / 'snapshots'
    root.mkdir(exist_ok=True)
    if root.is_symlink() or root.resolve(strict=True) != root:
        raise ValueError('Unsafe local snapshot state.')
    target = root / key
    if defer_activation:
        bundles.load.cache_clear()
    if target.exists():
        if target.is_symlink() or not target.is_dir() or target.resolve(strict=True) != target:
            raise ValueError('Unsafe existing snapshot state.')
        existing = json.loads(regular_file(target / 'manifest.json', target).read_text(encoding='utf-8'))
        if {k: v for k, v in existing.items() if k != 'created_at'} != {k: v for k, v in manifest.items() if k != 'created_at'}:
            raise ValueError('An immutable snapshot with that ID already exists.')
        for name in BASE_FILES - {'manifest.json'}:
            if json.loads(regular_file(target / name, target).read_text(encoding='utf-8')) != payload[name]:
                raise ValueError('Existing immutable snapshot contents cannot be replaced.')
        manifest = existing
    else:
        stage = Path(tempfile.mkdtemp(prefix='github-snapshot-', dir=root))
        created = _fingerprint(stage)[:2]
        try:
            for incoming in directory.rglob('*'):
                if incoming.is_dir() and not incoming.is_symlink():
                    continue
                regular_file(incoming, directory)
                relative = incoming.relative_to(directory)
                if not snapshot_role('snapshots/' + key + '/' + relative.as_posix()):
                    raise ValueError('Unexpected public snapshot file.')
                file_before = _fingerprint(incoming)
                destination = stage / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with incoming.open('rb') as reader, destination.open('xb') as writer:
                    shutil.copyfileobj(reader, writer, 1024 * 1024)
                    writer.flush()
                    os.fsync(writer.fileno())
                if _fingerprint(incoming) != file_before or destination.stat().st_size != file_before[2]:
                    raise ValueError('Public snapshot changed while preparing local state.')
            stage.rename(target)
        finally:
            if stage.exists() and not stage.is_symlink() and stage.resolve() == stage and _fingerprint(stage)[:2] == created:
                shutil.rmtree(stage)
    if any(_fingerprint(directory / name) != before[name] for name in BASE_FILES):
        raise ValueError('Public summary changed during validation or activation.')
    target_before = {name: _fingerprint(regular_file(target / name, target)) for name in BASE_FILES}
    def verify():
        if (any(_fingerprint(regular_file(directory / name, directory)) != before[name] for name in BASE_FILES)
                or any(_fingerprint(regular_file(target / name, target)) != target_before[name] for name in BASE_FILES)):
            raise ValueError('Snapshot input changed around reader activation.')
    prepared = PreparedSnapshot(key, manifest, verify, retain_reader=defer_activation)
    if defer_activation:
        # Read the explicit candidate key, never the old active database pointer.
        for name in sorted(BASE_FILES):
            actual = bundles.load(key, name)
            expected = manifest if name == 'manifest.json' else payload[name]
            if actual != expected:
                raise ValueError('The actual candidate reader differs from verified data.')
        verify()
        return prepared
    prepared.commit()
    return {'snapshot': key, 'activated': True}
