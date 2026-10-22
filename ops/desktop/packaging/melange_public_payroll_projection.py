"""Offline, atomic JSON-lines projection of reviewed government observations.

No public production plan is registered. This component does not emit a graph,
merge people, infer dates, carry private overlays or enable application readers.
Raw upstream receipts require a reviewed normalized closure before this runs.
"""
import gzip
import hashlib
import io
import os
from pathlib import Path
import tempfile
import zlib

import melange_public_provenance as provenance
import melange_public_payroll_normalize as normalize
from melange_public_provenance import ROLE_FAMILIES, require, strict_json, canonical


MAX_LINE_BYTES = 1024 ** 2
MAX_ROLE_EXPANDED_BYTES = 4 * 1024 ** 3
MAX_TOTAL_EXPANDED_BYTES = 8 * 1024 ** 3
MAX_TOTAL_RECORDS = 3_000_000
MAX_OUTPUT_BYTES = 8 * 1024 ** 3


class _HashedRead(io.RawIOBase):
    def __init__(self, stream, expected):
        self.stream, self.expected = stream, expected
        self.hasher, self.total = hashlib.sha256(), 0

    def readable(self):
        return True

    def read(self, size=-1):
        block = self.stream.read(min(size, provenance.MiB) if size >= 0 else provenance.MiB)
        self.total += len(block)
        require(self.total <= self.expected.bytes)
        self.hasher.update(block)
        return block

    def finish(self):
        while self.read(provenance.MiB):
            pass
        require(self.total == self.expected.bytes and self.hasher.hexdigest() == self.expected.sha256,
                'Projection compressed input changed')


def _program_manifest():
    files = (Path(__file__), Path(provenance.__file__), Path(normalize.__file__))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def _program_fingerprint():
    return hashlib.sha256(canonical(_program_manifest())).hexdigest()


def _owned(path, identity, *, links=1):
    info = path.lstat()
    require(not path.is_symlink() and not getattr(info, 'st_file_attributes', 0) & 0x400
            and (info.st_dev, info.st_ino) == identity and info.st_nlink == links)
    return info


def _checked_stage(path, identity, expected_bytes, expected_hash):
    """Bind the closed output's actual bytes, not a learned post-close stamp."""
    _owned(path, identity)
    before = provenance._path_stamp(path)
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        require(provenance._handle_stamp(stream) == before)
        h, count = hashlib.sha256(), 0
        while True:
            block = stream.read(provenance.MiB)
            if not block:
                break
            count += len(block)
            require(count <= expected_bytes)
            h.update(block)
        require(count == expected_bytes and h.hexdigest() == expected_hash,
                'Staged projection bytes differ from the generated receipt')
        require(provenance._handle_stamp(stream) == before)
        _owned(path, identity)
        require(provenance._path_stamp(path) == before)
    return before


def project_observations(verified, destination):
    require(type(verified) is provenance.ValidatedInputs)
    verified.ensure_current()
    destination = Path(destination)
    require(destination.is_absolute() and destination.name not in ('', '.', '..'))
    provenance._relative(destination.name)
    parent = provenance._directory(destination.parent)
    require(not destination.is_relative_to(verified.root), 'Projection cannot write into its original input tree')
    parent_stamp = provenance._stamp(parent.lstat())[:2]
    require(not os.path.lexists(destination), 'Projection destination already exists')
    require(all(destination != verified.root.joinpath(*s.relative.split('/')) for s in
                (*verified.plan.documents, *verified.plan.receipts, *verified.plan.inputs)))
    stage, identity, stage_stamp = None, None, None
    program = _program_fingerprint()
    program_files = _program_manifest()
    require(hashlib.sha256(canonical(program_files)).hexdigest() == program)
    output_hash, output_bytes, expanded, records, seen, counts = hashlib.sha256(), 0, 0, 0, set(), {}
    normalizer = normalize.Normalizer(verified)
    try:
        descriptor, name = tempfile.mkstemp(prefix='.melange-public-', suffix='.tmp', dir=parent)
        stage = Path(name)
        opened = os.fstat(descriptor)
        identity = (opened.st_dev, opened.st_ino)
        with os.fdopen(descriptor, 'wb') as output:
            for role in ROLE_FAMILIES:
                spec = verified.inputs[role]
                source = _HashedRead(verified.input_stream(role), spec)
                count, role_expanded = 0, 0
                try:
                    with gzip.GzipFile(fileobj=source, mode='rb') as compressed:
                        while True:
                            line = compressed.readline(MAX_LINE_BYTES + 1)
                            if not line:
                                break
                            role_expanded += len(line)
                            expanded += len(line)
                            count += 1
                            records += 1
                            require(len(line) <= MAX_LINE_BYTES and line.endswith(b'\n') and line.strip()
                                    and role_expanded <= MAX_ROLE_EXPANDED_BYTES
                                    and expanded <= MAX_TOTAL_EXPANDED_BYTES
                                    and count <= spec.records and records <= MAX_TOTAL_RECORDS,
                                    'Projection record or expansion limit was exceeded')
                            key, row = normalizer.observation(role, strict_json(line))
                            require(key not in seen, 'Duplicate source-native observation was rejected')
                            seen.add(key)
                            encoded = canonical(row) + b'\n'
                            output_bytes += len(encoded)
                            require(output_bytes <= MAX_OUTPUT_BYTES)
                            output.write(encoded)
                            output_hash.update(encoded)
                    source.finish()
                except (EOFError, gzip.BadGzipFile, zlib.error) as error:
                    raise ValueError('Government observation compression was rejected') from error
                require(count == spec.records, 'Government observation record conservation failed')
                counts[role] = count
            normalization_counts = normalizer.finish()
            output.flush()
            os.fsync(output.fileno())
            require(os.fstat(output.fileno()).st_size == output_bytes)
        # Recheck retained inputs and exact staging identity after closing the
        # output handle (Windows), before the atomic, non-overwriting publish.
        verified.ensure_current()
        provenance._directory(parent)
        require(provenance._stamp(parent.lstat())[:2] == parent_stamp)
        stage_stamp = _checked_stage(stage, identity, output_bytes, output_hash.hexdigest())
        receipt = {'schemaVersion': 1, 'kind': 'melange.official-payroll-observations.v1',
            'programFingerprint': program, 'inputManifestDigest': verified.manifest_digest,
            'currentMapperFiles': program_files,
            'sourceManifest': verified.manifest, 'recordCounts': counts,
            'normalizationCounts': normalization_counts,
            'provenanceStatus': {'currentMapper': 'EXACT_CODE_CLOSURE',
                'historicalProducer': 'SEE_SOURCE_RECEIPTS_NOT_INFERRED_FROM_CURRENT_CODE',
                'sourceExtraction': 'RECEIPT_REPORTED_NOT_INDEPENDENTLY_REPLAYED'},
            'output': {'format': 'strict-utf8-ndjson', 'bytes': output_bytes,
                       'sha256': output_hash.hexdigest(), 'records': records},
            'canonicalPromotions': {'identity': 0, 'employment': 0, 'office': 0, 'date': 0},
            'coverage': {'sourceNativeObservations': True, 'fullApplication': False}}
        require(_program_fingerprint() == program, 'Projection program source changed')
        # link() fails if the final name appeared during validation. Both names
        # briefly reference this newly-created output only; originals are never
        # linked, truncated, renamed, modified or recursively removed.
        provenance._directory(parent)
        require(provenance._stamp(parent.lstat())[:2] == parent_stamp)
        _owned(stage, identity)
        require(provenance._path_stamp(stage) == stage_stamp)
        os.link(stage, destination)
        _owned(stage, identity, links=2)
        _owned(destination, identity, links=2)
        stage.unlink()
        stage = None
        return receipt
    finally:
        if stage is not None:
            try:
                provenance._directory(parent)
                require(provenance._stamp(parent.lstat())[:2] == parent_stamp)
                _owned(stage, identity)
                if stage_stamp is not None:
                    require(provenance._path_stamp(stage) == stage_stamp,
                            'Changed staged output is preserved during cleanup')
                stage.unlink()
            except (ValueError, OSError):
                # A foreign, replaced, linked or reparse path is never removed.
                pass
