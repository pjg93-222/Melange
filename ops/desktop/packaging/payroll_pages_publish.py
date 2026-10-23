"""Partition a completed verified payroll projection; publish no unrelated files."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
from types import SimpleNamespace

from demand_publish import canonical, publish_directory, PublicationError


def build(observations, receipt_path, output, *, release_tag, generation, page_bytes=16*1024**2):
    from fec.surfaces import melange_public_data as reader
    from module_public_input_installers import _public_receipt
    if (type(generation) is not int or not 0 < generation <= 2**53-1
            or type(page_bytes) is not int or not 1024 <= page_bytes <= 16*1024**2
            or not re.fullmatch(r'module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?', release_tag)):
        raise PublicationError('Invalid payroll publication generation, release or page limit')
    observations, receipt_path, output = map(lambda p: Path(p).absolute(), (observations, receipt_path, output))
    for src in (observations, receipt_path):
        reader.p._regular(src)
        for parent in src.parents:
            reader.p._directory(parent)
    receipt_raw = receipt_path.read_bytes()
    if len(receipt_raw) > 1024**2:
        raise PublicationError('Projection receipt exceeds its limit')
    receipt = reader.p.strict_json(receipt_raw)
    proxy = SimpleNamespace(app='melange', objects={'observations': receipt['output'],
        'receipt': {'sha256': hashlib.sha256(receipt_raw).hexdigest()}})
    _public_receipt(reader, proxy, receipt_raw)
    documents = reader._manifest(receipt['sourceManifest'])
    if output.exists() or output.is_relative_to(observations.parent):
        raise PublicationError('Publication staging must be a new directory outside the input tree')
    reader.p._directory(output.parent)
    output.mkdir()
    counts = dict.fromkeys(reader.ROLES, 0)
    chunks, seen, total, whole = [], set(), 0, hashlib.sha256()
    page = bytearray()
    role, start, count, position = None, 0, 0, 0

    def finish():
        nonlocal page, start, count
        if not page:
            return
        digest = hashlib.sha256(page).hexdigest()
        name = digest + '.ndjson'
        with (output / name).open('xb') as stream:
            stream.write(page); stream.flush(); os.fsync(stream.fileno())
        chunks.append({'id': role + '-' + str(start), 'sha256': digest, 'bytes': len(page), 'asset': name,
                       'selectors': {'sourceRole': role, 'start': start, 'count': count}})
        page = bytearray(); start += count; count = 0

    before = reader.p._path_stamp(observations)
    with observations.open('rb') as source:
        if reader.p._handle_stamp(source) != before:
            raise PublicationError('Projection changed before partitioning')
        while line := source.readline(reader.MAX_LINE+1):
            if len(line) > reader.MAX_LINE or not line.endswith(b'\n'):
                raise PublicationError('Projection contains a malformed or oversized record')
            value = reader.p.strict_json(line)
            next_role = reader._row(value, documents)
            next_position = reader.ROLES.index(next_role)
            if next_position < position or value['recordId'] in seen:
                raise PublicationError('Projection order or unique observation identity failed')
            if len(line) > page_bytes:
                raise PublicationError('A single observation exceeds the requested page size')
            seen.add(value['recordId']); position = next_position
            if role is not None and (role != next_role or len(page) + len(line) > page_bytes):
                finish()
            if role != next_role:
                role, start = next_role, 0
            page.extend(line); count += 1; counts[role] += 1
            whole.update(line); total += len(line)
            if total > receipt['output']['bytes'] or len(seen) > receipt['output']['records']:
                raise PublicationError('Projection exceeds its completed receipt')
        finish()
        if reader.p._handle_stamp(source) != before or reader.p._path_stamp(observations) != before:
            raise PublicationError('Projection changed during partitioning')
    if (counts != receipt['recordCounts'] or total != receipt['output']['bytes']
            or whole.hexdigest() != receipt['output']['sha256'] or len(seen) != receipt['output']['records']):
        raise PublicationError('Completed projection hash, counts or conservation failed')
    if receipt_path.read_bytes() != receipt_raw:
        raise PublicationError('Projection receipt changed')
    index = {'schemaVersion': 1, 'appId': 'melange', 'kind': 'melange.official-payroll-pages.v1',
        'repository': 'pjg93-222/Melange', 'releaseTag': release_tag, 'generation': generation,
        'receiptSha256': hashlib.sha256(receipt_raw).hexdigest(), 'format': 'strict-utf8-ndjson',
        'recordCounts': counts, 'chunks': chunks}
    (output / 'receipt.json').write_bytes(receipt_raw)
    (output / 'index.json').write_bytes(canonical(index))
    assets = [{'asset': p.name, 'bytes': p.stat().st_size,
               'sha256': hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(output.iterdir())]
    if len(assets) >= 1000:
        raise PublicationError('Dataset needs multiple immutable releases before publication')
    # Written last: absence of this seal always means incomplete staging.
    (output / 'publication.json').write_bytes(canonical({'schemaVersion': 1, 'status': 'complete',
        'repository': index['repository'], 'releaseTag': release_tag, 'assets': assets}))
    return index


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observations', required=True)
    parser.add_argument('--receipt', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--generation', type=int, required=True)
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args(argv)
    index = build(args.observations, args.receipt, args.output, release_tag=args.tag, generation=args.generation)
    if args.publish:
        print(json.dumps(publish_directory(args.output, index['repository'], args.tag)))
    else:
        print(json.dumps({'sealed': True, 'chunks': len(index['chunks']), 'output': args.output}))


if __name__ == '__main__':
    main()
