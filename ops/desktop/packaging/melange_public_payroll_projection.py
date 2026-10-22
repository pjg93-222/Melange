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
from melange_public_provenance import ROLE_FAMILIES, require, strict_json, canonical


MAX_LINE_BYTES = 1024 ** 2
MAX_ROLE_EXPANDED_BYTES = 4 * 1024 ** 3
MAX_TOTAL_EXPANDED_BYTES = 8 * 1024 ** 3
MAX_TOTAL_RECORDS = 3_000_000
MAX_OUTPUT_BYTES = 8 * 1024 ** 3
_HOUSE = frozenset('allowance_year allowance_year_kind amount amount_raw amount_sign budget_object_code canonical_eligible canonical_employment_promoted canonical_identity_decision canonical_identity_promoted canonical_office_id canonical_office_promoted canonical_person_id compensation_class container_kind data_source document family_link_candidate fiscal_or_legislative_year_column identity_status interval_vs_quarter member_bioguide member_resolution_evidence member_resolution_method observation_id office_family_normalized office_family_raw office_group_key_legacy office_key office_raw organization_code payee_parse payee_raw person_key person_key_family program quarter report_period_end report_period_start review_flags review_status row_admission rule_version schema_id service_days service_end service_end_raw service_start service_start_raw shared_employee_flag source_file source_form source_locator source_row_index source_sha256 source_url title_base title_raw title_truncated_30 transaction_date vendor_id'.split())
_SENATE = frozenset('amount_paid_raw candidate_id canonical_employment_decision canonical_identity_decision completeness_status date_intervals date_promotion_eligible employment_claim_status evidence_quote identity_status office_raw page_number parse_status payee_name_raw promotion_gate qualifiers report_package_id report_period_end report_period_start row_ordinal_on_page schema_id source_pdf_sha256 source_pdf_url source_tier title_candidate title_raw'.split())
_COMMITTEE = _SENATE | frozenset('evidence_columns extraction_engine office_attribution_basis page_label_raw parser_version review_status senate_appropriation_raw senate_funding_resolution_raw senate_report_volume'.split())


def _text(value, *, maximum=4096, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is str and len(value) <= maximum and '\x00' not in value)
    value.encode('utf-8', errors='strict')
    return value


def _integer(value, minimum=0):
    require(type(value) is int and minimum <= value < 2 ** 31)
    return value


def _observation(verified, role, row):
    require(type(row) is dict)
    house = role == 'house-observations'
    allowed = _HOUSE if house else _COMMITTEE if role == 'senate-committee-candidates' else _SENATE
    require(set(row) <= allowed, 'Unknown or private observation field was rejected')
    required = {'office_raw', 'title_raw', 'report_period_start', 'report_period_end'}
    required |= {'source_url', 'source_sha256', 'source_row_index', 'payee_raw', 'amount_raw'} if house else {
        'source_pdf_url', 'source_pdf_sha256', 'page_number', 'row_ordinal_on_page', 'payee_name_raw', 'amount_paid_raw'}
    require(required <= set(row), 'Required printed observation field is missing')
    for key in ('canonical_eligible', 'canonical_identity_promoted', 'canonical_employment_promoted', 'canonical_office_promoted'):
        require(key not in row or row[key] is None or row[key] is False,
                'Promoted source record is outside this observation-only projection')
    for key in ('canonical_person_id', 'canonical_office_id'):
        require(row.get(key) is None, 'Canonical identity is outside this observation-only projection')
    url, sha = (row['source_url'], row['source_sha256']) if house else (row['source_pdf_url'], row['source_pdf_sha256'])
    document = verified.document_for(role, url, sha)
    locator = {'row': _integer(row['source_row_index'])} if house else {
        'page': _integer(row['page_number'], 1), 'row': _integer(row['row_ordinal_on_page'])}
    identity = hashlib.sha256(canonical([role, document.sha256, locator])).digest()
    printed = {
        'office': _text(row['office_raw']),
        'payee': _text(row['payee_raw'] if house else row['payee_name_raw']),
        'title': _text(row['title_raw'], nullable=True),
        'amount': _text(row['amount_raw'] if house else row['amount_paid_raw'], maximum=256, nullable=True),
        'periodStart': _text(row['report_period_start'], maximum=256, nullable=True),
        'periodEnd': _text(row['report_period_end'], maximum=256, nullable=True),
        # Only printed source dates are copied. Parsed/promoted intervals and
        # cross-source identity fields never become public projection columns.
        'serviceStart': _text(row.get('service_start_raw'), maximum=256, nullable=True) if house else None,
        'serviceEnd': _text(row.get('service_end_raw'), maximum=256, nullable=True) if house else None,
    }
    return identity, {'schemaVersion': 1, 'recordId': 'government-observation:' + identity.hex(),
        'sourceRole': role, 'source': {'documentId': document.document_id, 'sha256': document.sha256,
            'url': document.url, 'locator': locator}, 'printed': printed,
        'review': {'status': 'SOURCE_OBSERVATION_ONLY', 'identityPromoted': False,
                   'employmentPromoted': False, 'officePromoted': False, 'datePromoted': False}}


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


def _program_fingerprint():
    files = (Path(__file__), Path(provenance.__file__))
    return hashlib.sha256(canonical({p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})).hexdigest()


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
    output_hash, output_bytes, expanded, records, seen, counts = hashlib.sha256(), 0, 0, 0, set(), {}
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
                            key, row = _observation(verified, role, strict_json(line))
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
            'sourceManifest': verified.manifest, 'recordCounts': counts,
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
                stage.unlink()
            except (ValueError, OSError):
                # A foreign, replaced, linked or reparse path is never removed.
                pass
