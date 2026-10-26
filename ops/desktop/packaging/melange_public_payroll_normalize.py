"""Closed source-specific payroll mapping; no production plan or classifier.

Auxiliary joins use record ordinals/candidate IDs, never person identities.
Origin receipt assertions are source-reported; current mapper code is a separate
provenance seal and never stands in for unavailable historical producer code.
"""
import csv
import gzip
import hashlib
import io
import zlib

import melange_public_provenance as p
from melange_public_provenance import canonical, require, strict_json


MAX_LINE_BYTES = 1024 ** 2
MAX_ROLE_EXPANDED_BYTES = 4 * 1024 ** 3
MAX_AUXILIARY_EXPANDED_BYTES = 4 * 1024 ** 3
HOUSE_FIELDS = frozenset('allowance_year allowance_year_kind amount amount_raw amount_sign budget_object_code canonical_eligible canonical_employment_promoted canonical_identity_decision canonical_identity_promoted canonical_office_id canonical_office_promoted canonical_person_id compensation_class container_kind data_source document family_link_candidate fiscal_or_legislative_year_column identity_status interval_vs_quarter member_bioguide member_resolution_evidence member_resolution_method observation_id office_family_normalized office_family_raw office_group_key_legacy office_key office_raw organization_code payee_parse payee_raw person_key person_key_family program quarter report_period_end report_period_start review_flags review_status row_admission rule_version schema_id service_days service_end service_end_raw service_start service_start_raw shared_employee_flag source_file source_form source_locator source_row_index source_sha256 source_url title_base title_raw title_truncated_30 transaction_date vendor_id'.split())
SENATE_FIELDS = frozenset('amount_paid_raw candidate_id canonical_employment_decision canonical_identity_decision completeness_status date_intervals date_promotion_eligible employment_claim_status evidence_quote identity_status office_raw page_number parse_status payee_name_raw promotion_gate qualifiers report_package_id report_period_end report_period_start row_ordinal_on_page schema_id source_pdf_sha256 source_pdf_url source_tier title_candidate title_raw'.split())
REPAIR_FIELDS = frozenset('pre_boundary_repair_title_raw pre_boundary_repair_payee_name_raw boundary_repair_status'.split())
COMMITTEE_FIELDS = SENATE_FIELDS | frozenset('evidence_columns extraction_engine office_attribution_basis page_label_raw parser_version review_status senate_appropriation_raw senate_funding_resolution_raw senate_report_volume'.split())
PDF_FIELDS = frozenset('amount_raw amount_source_token_raw candidate_id candidate_status canonical_eligible canonical_employing_office_id canonical_employment_episode_id canonical_employment_promoted canonical_identity_decision canonical_identity_promoted canonical_office_promoted canonical_person_id employing_office_raw payee_raw payee_reconstruction_method payee_source_slice_raw period period_end period_start review_status schema_id service_end_date_candidate_iso service_end_date_parse_status service_end_date_raw service_start_date_candidate_iso service_start_date_parse_status service_start_date_raw source_pdf_page_number source_pdf_printed_page_number source_pdf_row_y_milli source_pdf_sha256 source_url title_description_raw ytd_amount_raw'.split())
REPAIR_STATUS = 'RAW_EVIDENCE_HEURISTIC_REPAIR_REVIEW_REQUIRED'
PERSONAL_PARSE = frozenset(('HISTORICAL_REVERSE_LAYOUT_HEURISTIC_SPLIT',
    'HISTORICAL_REVERSE_LAYOUT_LINE_SPLIT', 'HEURISTIC_SPLIT'))
COMMITTEE_PARSE = frozenset(('COLUMN_COORDINATE_SPLIT', 'COLUMN_COORDINATE_SPLIT_WITH_LEADING_TITLE',
    'COLUMN_COORDINATE_SPLIT_WITH_WRAPPED_TITLE', 'COLUMN_COORDINATE_SPLIT_WITH_LEADING_TITLE_WITH_WRAPPED_TITLE',
    'COLUMN_COORDINATE_SPLIT_NO_TITLE_COLUMN_WITH_LEADING_TITLE_WITH_WRAPPED_TITLE',
    'COLUMN_COORDINATE_SPLIT_NO_TITLE_COLUMN_WITH_LEADING_TITLE'))
CSV_12 = tuple('ORGANIZATION|PROGRAM|SORT SUBTOTAL DESCRIPTION|SORT SEQUENCE|TRANSACTION DATE|DATA SOURCE|DOCUMENT|VENDOR NAME|PERFORM START DT|PERFORM END DT|DESCRIPTION|AMOUNT'.split('|'))
CSV_18 = tuple('ORGANIZATION|FISCAL YEAR OR LEGISLATIVE YEAR|ORGANIZATION CODE|PROGRAM|PROGRAM CODE|SORT SUBTOTAL DESCRIPTION|BUDGET OBJECT CLASS|SORT SEQUENCE|TRANSACTION DATE|DATA SOURCE|DOCUMENT|VENDOR NAME|VENDOR ID|PERFORM START DT|PERFORM END DT|DESCRIPTION|BUDGET OBJECT CODE|AMOUNT'.split('|'))


def text(value, maximum=4096, nullable=False):
    if value is None and nullable:
        return None
    require(type(value) is str and len(value) <= maximum and '\x00' not in value)
    value.encode('utf-8', errors='strict')
    return value


def integer(value, minimum=1):
    require(type(value) is int and minimum <= value < 2 ** 31)
    return value


def unpromoted(row):
    for key in ('canonical_eligible', 'canonical_identity_promoted', 'canonical_employment_promoted',
                'canonical_office_promoted', 'date_promotion_eligible'):
        require(key not in row or row[key] is None or row[key] is False,
                'Promoted source record is outside this observation-only projection')
    for key in ('canonical_person_id', 'canonical_office_id', 'canonical_employing_office_id',
                'canonical_employment_episode_id'):
        require(row.get(key) is None)
    for key in ('canonical_identity_decision', 'canonical_employment_decision'):
        require(key not in row or row[key] == 'NOT_ADJUDICATED')


class HashedRead(io.RawIOBase):
    def __init__(self, stream, expected):
        self.stream, self.expected = stream, expected
        self.hasher, self.total = hashlib.sha256(), 0

    def readable(self):
        return True

    def readinto(self, target):
        block = self.read(len(target))
        target[:len(block)] = block
        return len(block)

    def read(self, size=-1):
        block = self.stream.read(min(size, p.MiB) if size >= 0 else p.MiB)
        self.total += len(block)
        require(self.total <= self.expected.bytes)
        self.hasher.update(block)
        return block

    def finish(self):
        while self.read(p.MiB):
            pass
        require(self.total == self.expected.bytes and self.hasher.hexdigest() == self.expected.sha256,
                'Projection compressed input changed')


def records(verified, role, budget):
    """Bounded strict JSONL with retained-handle digest and record conservation."""
    spec = verified.inputs[role]
    source = HashedRead(verified.input_stream(role), spec)
    count, expanded = 0, 0
    try:
        with gzip.GzipFile(fileobj=source, mode='rb') as compressed:
            while True:
                line = compressed.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                expanded += len(line)
                budget[0] += len(line)
                count += 1
                require(len(line) <= MAX_LINE_BYTES and line.endswith(b'\n') and line.strip()
                        and expanded <= MAX_ROLE_EXPANDED_BYTES and budget[0] <= MAX_AUXILIARY_EXPANDED_BYTES
                        and count <= spec.records)
                yield strict_json(line)
        source.finish()
    except (EOFError, gzip.BadGzipFile, zlib.error) as error:
        raise ValueError('Government observation compression was rejected') from error
    require(count == spec.records, 'Government observation record conservation failed')


def csv_records(verified, document):
    """Reproduce the recorded column/width adapter, not person classification."""
    source = HashedRead(verified.document_stream(document.document_id), document)
    # Closing these wrappers only closes HashedRead, never the retained handle.
    with io.TextIOWrapper(io.BufferedReader(source), encoding='utf-8', errors='replace', newline='') as stream:
        def lines():
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                require(len(line) <= MAX_LINE_BYTES, 'Government CSV line budget was exceeded')
                yield line
        reader = csv.reader(lines())
        header = tuple(text(v).strip() for v in next(reader, ()))
        require(header)
        extra = header[-1] == ''
        if extra:
            header = header[:-1]
        require(header in (CSV_12, CSV_18), 'Unknown government CSV schema was rejected')
        width, vendor = len(header), header.index('VENDOR NAME')
        for ordinal, row in enumerate(reader, 1):
            require(ordinal <= 5_000_000)
            if extra and len(row) == width + 1:
                row = row[:-1] if row[-1].strip() == '' else (
                    row[:vendor] + [row[vendor] + ', ' + row[vendor + 1]] + row[vendor + 2:])
            if len(row) != width:
                continue
            value = {h: text(v).strip() for h, v in zip(header, row)}
            if value['SORT SEQUENCE'].upper() == 'DETAIL' and value['SORT SUBTOTAL DESCRIPTION'].upper() == 'PERSONNEL COMPENSATION':
                yield ordinal, value
        source.finish()


def _binding(binding, expected, count=None):
    require(type(binding) is dict and type(binding.get('bytes')) is int
            and binding['bytes'] == expected.bytes and binding.get('sha256') == expected.sha256,
            'Original receipt output/dependency binding differs')
    if count is not None:
        require(type(binding.get('rows')) is int and binding['rows'] == count)


def _zero(value, names):
    require(type(value) is dict)
    require(all(type(value.get(k)) is int and value[k] == 0 for k in names),
            'Original receipt reports canonical promotions')


def validate_documentary_bindings(verified):
    """Bind the fixed original inventory/package formats to the selected docs."""
    covered, package_seen = set(), {'senate-payroll-parser-v4': set(), 'senate-committee-payroll-parser-v2': set()}
    package_counts = {key: 0 for key in package_seen}
    package_periods = []
    docs = verified.documents
    for spec in verified.evidence.values():
        if spec.kind == 'source-inventory':
            value = strict_json(verified.evidence_stream(spec.evidence_id).read(p.MAX_JSON_BYTES + 1))
            schema = value.get('schema_id')
            choices = {
                'staffer-network-house-sod-url-inventory-v1': ('house', 'csv', 'periods', 'detail_csv_url'),
                'staffer-network-house-sod-historical-inventory-v1': ('house', 'pdf', 'house_pdf_periods', 'pdf_url'),
                'staffer-network-official-senate-report-inventory-v1': ('senate', 'pdf', 'periods', 'full_pdf_url')}
            require(schema in choices)
            family, format_name, key, url_key = choices[schema]
            require(spec.family == family and type(value.get(key)) is list)
            matched = set()
            for row in value[key]:
                require(type(row) is dict)
                found = [d for d in docs.values() if d.family == family and d.format == format_name and d.url == row.get(url_key)]
                if not found:
                    continue  # Unselected catalog entries never grant file-open authority.
                require(len(found) == 1 and found[0].document_id not in matched)
                document = found[0]
                matched.add(document.document_id)
                period = {'start': text(row['period_start'], 256), 'end': text(row['period_end'], 256)}
                require(document.document_id not in verified._document_periods
                        or verified._document_periods[document.document_id] == period)
                verified._document_periods[document.document_id] = period
            require(matched)
            covered.update(matched)
        elif spec.kind == 'source-extraction-receipts':
            require(spec.family == 'senate')
            stream = verified.evidence_stream(spec.evidence_id)
            count, parser = 0, None
            while True:
                line = stream.readline(MAX_LINE_BYTES + 1)
                if not line:
                    break
                count += 1
                require(count <= p.MAX_DOCUMENTS and len(line) <= MAX_LINE_BYTES and line.endswith(b'\n'))
                row = strict_json(line)
                current = row.get('parser_version')
                require(current in package_seen and (parser is None or parser == current))
                parser = current
                found = [d for d in docs.values() if d.family == 'senate' and d.sha256 == row.get('pdf_sha256')]
                require(len(found) == 1)
                document = found[0]
                require(document.document_id not in package_seen[parser]
                        and type(row.get('pdf_bytes')) is int and row['pdf_bytes'] == document.bytes
                        and type(row.get('page_count')) is int and row['page_count'] == document.page_count
                        and document.url == 'https://www.govinfo.gov/content/pkg/' + text(row['package_id'], 64)
                            + '/pdf/' + row['package_id'] + '.pdf')
                if parser == 'senate-payroll-parser-v4':
                    require(row.get('pdf_url') == document.url)
                count_key = 'candidate_count' if parser == 'senate-payroll-parser-v4' else 'accepted_row_count'
                count_value = row.get(count_key)
                require(type(count_value) is int and 0 <= count_value <= p.MAX_RECORDS)
                package_counts[parser] += count_value
                package_seen[parser].add(document.document_id)
                package_periods.append((document.document_id, {'start': text(row['period_start'], 256),
                                                              'end': text(row['period_end'], 256)}))
            require(count > 0)
    require(covered == set(docs), 'Selected documents lack a closed original inventory')
    require(all(verified._document_periods.get(key) == period for key, period in package_periods),
            'Package receipt periods differ from the original archive inventory')
    senate = {d.document_id for d in docs.values() if d.family == 'senate'}
    require(senate and all(seen == senate for seen in package_seen.values()),
            'Selected Senate documents lack both exact package receipt bindings')
    require(package_counts['senate-payroll-parser-v4'] == verified.inputs['senate-personal-unfiltered'].records
            and package_counts['senate-committee-payroll-parser-v2'] == verified.inputs['senate-committee-candidates'].records,
            'Package receipt record totals differ from selected observation inputs')
    # Link each original receipt's inventory/package metadata by digest and
    # size to a retained, separately validated evidence input. Never use paths.
    metadata_keys = {'house-ledger-v1': ('url_inventory',), 'house-pdf-v1': ('source_inventory',),
        'senate-full-v1': ('inventory_file', 'report_extraction_receipts_file'),
        'senate-committee-v1': ('inventory_source', 'package_receipts')}
    for receipt in verified.receipts.values():
        raw = verified._streams[receipt.relative]
        raw.seek(0)
        value = strict_json(raw.read(p.MAX_JSON_BYTES + 1))
        container = value.get('inputs', {}) if receipt.source_format == 'house-ledger-v1' else value
        for key in metadata_keys.get(receipt.source_format, ()):
            binding = container.get(key)
            require(type(binding) is dict)
            found = [verified.evidence[i] for i in receipt.dependencies if i in verified.evidence
                     and verified.evidence[i].sha256 == binding.get('sha256')]
            require(len(found) == 1)
            require(found[0].kind == ('source-extraction-receipts' if key in
                ('report_extraction_receipts_file', 'package_receipts') else 'source-inventory'))
            if 'bytes' in binding:
                _binding(binding, found[0])


def validate_origin_receipt(raw, spec, documents, receipts, inputs, evidence):
    """Fixed adapters; metadata paths are ignored and never opened or exported."""
    value = strict_json(raw)
    require(type(value) is dict and spec.producer_sha256 is None)
    kind = spec.source_format
    schemas = {'house-ledger-v1': 'staffer-network-house-personnel-ledger-receipt-v1',
        'house-pdf-v1': 'staffer-network-house-sod-complete-reparse-receipt-v1',
        'senate-scope-v1': 'staffer-network-senate-payroll-employment-scope-receipt-v1',
        'senate-full-v1': 'staffer-network-official-senate-payroll-full-archive-receipt-v1',
        'senate-committee-v1': 'staffer-network-senate-committee-payroll-receipt-v1'}
    require(kind in schemas and value.get('schema_id') == schemas[kind])
    output = inputs[spec.outputs[0]]
    zero = ('canonical_identity_promotions', 'canonical_employment_promotions')
    if kind == 'house-ledger-v1':
        require(value.get('status') == 'PASS')
        _zero(value.get('invariants'), zero + ('canonical_office_promotions', 'canonical_service_date_promotions'))
        bindings = [v for v in value.get('outputs', []) if type(v) is dict and v.get('sha256') == output.sha256]
        require(len(bindings) == 1)
        _binding(bindings[0], output, output.records)
        require(value.get('totals', {}).get('observations') == output.records)
        csv = [documents[k] for k in spec.dependencies if k in documents and documents[k].format == 'csv']
        reported = value.get('inputs', {}).get('csv_files')
        require(type(reported) is list and len(reported) == len(csv) and csv)
        seen = set()
        for item in reported:
            found = [d for d in csv if d.sha256 == item.get('sha256') and d.url == item.get('source_url')]
            require(len(found) == 1 and found[0].document_id not in seen)
            _binding(item, found[0])
            seen.add(found[0].document_id)
        require(value.get('inputs', {}).get('pdf_era', {}).get('sha256') == inputs['house-pdf-candidates'].sha256)
    elif kind == 'house-pdf-v1':
        require(value.get('status') == 'PASS' and value.get('failures') == [])
        _zero(value, zero + ('canonical_office_promotions', 'canonical_service_date_promotions'))
        bindings = [v for v in value.get('files', []) if type(v) is dict and v.get('sha256') == output.sha256]
        require(len(bindings) == 1)
        _binding(bindings[0], output, output.records)
        require(value.get('counts', {}).get('payroll_candidate_rows') == output.records)
        periods = value.get('periods')
        docs = [documents[k] for k in spec.dependencies if k in documents]
        caches = [evidence[k] for k in spec.dependencies if k in evidence and evidence[k].kind == 'source-text-cache']
        require(type(periods) is list and len(periods) == len(docs) == len(caches) and docs)
        require(len({r.get('pdf_sha256') for r in periods}) == len(docs)
                and {r.get('pdf_sha256') for r in periods} == {d.sha256 for d in docs}
                and {r.get('text_sha256') for r in periods} == {c.sha256 for c in caches})
    else:
        _zero(value, zero)
        require(type(value.get('complete_history_assertions')) is int and value['complete_history_assertions'] == 0)
        if kind == 'senate-scope-v1':
            require(value.get('status') == 'PASS'
                    and value.get('filter_version') == 'senate-payroll-employment-scope-filter-v1')
            _binding(value.get('accepted_candidates'), output)
            raw_input = inputs['senate-personal-unfiltered']
            _binding(value.get('source'), raw_input)
            require(value.get('accepted_candidate_count') == output.records
                    and value.get('input_candidate_count') == raw_input.records
                    and type(value.get('rejected_candidate_count')) is int
                    and value['rejected_candidate_count'] == raw_input.records - output.records)
        elif kind == 'senate-full-v1':
            require(value.get('parser_version') == 'senate-payroll-parser-v4'
                    and type(value.get('archive_reports_remaining')) is int and value['archive_reports_remaining'] == 0)
            _binding(value.get('candidate_file'), output)
            require(value.get('extraction', {}).get('candidate_count') == output.records)
        else:
            require(value.get('status') == 'PASS'
                    and value.get('parser_version') == 'senate-committee-payroll-parser-v2')
            _zero(value, ('date_promotions',))
            _binding(value.get('accepted_candidates'), output)
            require(value.get('accepted_row_count') == output.records)
    # All raw receipts, inventories, text caches and current source files are
    # separately retained, hash-checked inputs. They are not serialized here.


def _source_fields(row, house=False):
    return {'office': text(row['office_raw']),
        'payee': text(row['payee_raw'] if house else row['payee_name_raw']),
        'title': text(row['title_raw'], nullable=True),
        'amount': text(row['amount_raw'] if house else row['amount_paid_raw'], maximum=256, nullable=True)}


class Normalizer:
    def __init__(self, verified):
        self.verified = verified
        self.budget = [0]
        self.pdf = records(verified, 'house-pdf-candidates', self.budget) if 'house-pdf-candidates' in verified.inputs else None
        self.raw = records(verified, 'senate-personal-unfiltered', self.budget) if 'senate-personal-unfiltered' in verified.inputs else None
        self.pdf_count = self.raw_count = self.accepted = self.repairs = self.excluded = 0
        self.raw_ids = set()
        self.csv = {}
        self.csv_count = 0

    def _next(self, iterator, label):
        require(iterator is not None, label + ' auxiliary input is required')
        try:
            return next(iterator)
        except StopIteration as error:
            raise ValueError(label + ' auxiliary record conservation failed') from error

    def observation(self, role, row):
        require(type(row) is dict)
        house = role == 'house-observations'
        allowed = HOUSE_FIELDS if house else COMMITTEE_FIELDS if role == 'senate-committee-candidates' else SENATE_FIELDS | REPAIR_FIELDS
        require(set(row) <= allowed, 'Unknown or private observation field was rejected')
        required = {'office_raw', 'title_raw', 'report_period_start', 'report_period_end'}
        required |= {'source_url', 'source_sha256', 'source_row_index', 'payee_raw', 'amount_raw'} if house else {
            'source_pdf_url', 'source_pdf_sha256', 'page_number', 'row_ordinal_on_page', 'payee_name_raw', 'amount_paid_raw'}
        require(required <= set(row), 'Required source observation field is missing')
        unpromoted(row)
        fields = _source_fields(row, house)
        period = {'start': text(row['report_period_start'], maximum=256, nullable=True),
                  'end': text(row['report_period_end'], maximum=256, nullable=True)}
        literal, original, status, provenance = None, None, {}, {}
        if house:
            form = row.get('source_form')
            require(form in ('detail_csv', 'house_gov_single_volume_pdf'))
            ordinal = integer(row['source_row_index'])
            if form == 'detail_csv':
                document = self.verified.document_for(role, row['source_url'], row['source_sha256'])
                require(document.format == 'csv' and row.get('source_locator') is None)
                locator = {'kind': 'csv-data-row', 'dataRow': ordinal}
                literal = {**fields, 'serviceStart': text(row.get('service_start_raw'), 256, True),
                           'serviceEnd': text(row.get('service_end_raw'), 256, True)}
                iterator = self.csv.setdefault(document.document_id, None)
                if iterator is None:
                    iterator = self.csv[document.document_id] = csv_records(self.verified, document)
                actual_ordinal, actual = self._next(iterator, 'House CSV')
                require(actual_ordinal == ordinal and fields == {'office': actual['ORGANIZATION'],
                    'payee': actual['VENDOR NAME'], 'title': actual['DESCRIPTION'], 'amount': actual['AMOUNT']}
                    and literal['serviceStart'] == (actual['PERFORM START DT'] or None)
                    and literal['serviceEnd'] == (actual['PERFORM END DT'] or None),
                    'House CSV raw field equivalence failed')
                self.csv_count += 1
                status = {'method': 'CSV_SOURCE_COLUMN', 'literalEquivalence': 'VERIFIED_RAW_CSV_FIELDS',
                          'adapter': 'UTF8_REPLACE_CELL_STRIP_OPTIONAL_SHIFTED_VENDOR_V1'}
            else:
                candidate = self._next(self.pdf, 'House PDF')
                self.pdf_count += 1
                require(type(candidate) is dict and set(candidate) <= PDF_FIELDS)
                unpromoted(candidate)
                require(row['source_sha256'] == self.verified.inputs['house-pdf-candidates'].sha256
                        and ordinal == self.pdf_count)
                expected = {'source_pdf_page_number': candidate['source_pdf_page_number'],
                    'source_pdf_row_y_milli': candidate['source_pdf_row_y_milli'],
                    'source_pdf_sha256': candidate['source_pdf_sha256'], 'candidate_id': candidate['candidate_id']}
                require(row.get('source_locator') == expected)
                document = self.verified.document_for(role, candidate['source_url'], candidate['source_pdf_sha256'])
                require(document.format == 'pdf' and row['source_url'] == document.url)
                require(fields == {'office': candidate['employing_office_raw'], 'payee': candidate['payee_raw'],
                    'title': candidate['title_description_raw'], 'amount': candidate['amount_raw']})
                require(period == {'start': candidate['period_start'], 'end': candidate['period_end']})
                locator = {'kind': 'pdf-layout-row', 'physicalPage': integer(candidate['source_pdf_page_number']),
                           'yMilli': integer(candidate['source_pdf_row_y_milli'], 0)}
                for side in ('start', 'end'):
                    require(row.get('service_' + side + '_raw') ==
                        (candidate.get('service_' + side + '_date_candidate_iso')
                         or candidate.get('service_' + side + '_date_raw') or None))
                literal = {'payee': text(candidate['payee_source_slice_raw']),
                    'amount': text(candidate['amount_source_token_raw'], 256),
                    'serviceStart': text(candidate['service_start_date_raw'], 256),
                    'serviceEnd': text(candidate['service_end_date_raw'], 256)}
                method = candidate['payee_reconstruction_method']
                require(method in ('SOURCE_NAME', 'DITTO_FROM_PRIOR_PERSONNEL_ROW_SAME_OFFICE'))
                status = {'method': method, 'review': 'REVIEW_REQUIRED', 'literalEquivalence': 'CACHED_EXTRACTION_NOT_REPLAYED'}
                provenance = {'auxiliaryRole': 'house-pdf-candidates', 'candidateOrdinal': ordinal}
        else:
            document = self.verified.document_for(role, row['source_pdf_url'], row['source_pdf_sha256'])
            require(document.format == 'pdf')
            locator = {'kind': 'pdf-extracted-row', 'physicalPage': integer(row['page_number']),
                       'rowOrdinal': integer(row['row_ordinal_on_page'])}
            require(row.get('identity_status') == row.get('employment_claim_status') == 'UNVERIFIED_CANDIDATE')
            if role == 'senate-personal-candidates':
                require(row.get('parse_status') in PERSONAL_PARSE)
                if self.raw is not None:
                    self._accepted_subsequence(row)
                require(not (set(row) & REPAIR_FIELDS) or REPAIR_FIELDS <= set(row))
                repaired = REPAIR_FIELDS <= set(row)
                if repaired:
                    require(row['boundary_repair_status'] == REPAIR_STATUS)
                    original = {'payee': text(row['pre_boundary_repair_payee_name_raw']),
                                'title': text(row['pre_boundary_repair_title_raw'], nullable=True)}
                    self.repairs += 1
                status = {'method': row['parse_status'], 'boundaryRepair': REPAIR_STATUS if repaired else 'NONE',
                          'identity': 'UNVERIFIED_CANDIDATE', 'literalEquivalence': 'CACHED_EXTRACTION_NOT_REPLAYED'}
            else:
                require(row.get('parse_status') in COMMITTEE_PARSE
                        and row.get('parser_version') == 'senate-committee-payroll-parser-v2')
                require(row.get('office_attribution_basis') in ('PAGE_HEADER_ABBREVIATED_FUNDING_LINE_ONLY',
                    'PAGE_HEADER', 'CARRIED_FROM_PREVIOUS_VOLUME_II_PAGE'))
                status = {'method': row['parse_status'], 'parser': row['parser_version'],
                          'officeAttribution': text(row['office_attribution_basis'], 128),
                          'identity': 'UNVERIFIED_CANDIDATE', 'literalEquivalence': 'CACHED_EXTRACTION_NOT_REPLAYED'}
        if document.page_count is not None:
            require(locator.get('physicalPage', 0) <= document.page_count)
        if document.document_id in self.verified._document_periods:
            require(period == self.verified._document_periods[document.document_id],
                    'Observation report period differs from original inventory')
        identity = hashlib.sha256(canonical([role, document.sha256, locator])).digest()
        result = {'schemaVersion': 1, 'recordId': 'government-observation:' + identity.hex(),
            'sourceRole': role, 'source': {'documentId': document.document_id, 'sha256': document.sha256,
                'url': document.url, 'locator': locator, 'reportPeriod': period},
            'sourceExtracted': fields, 'literalTokens': literal, 'originalBeforeRepair': original,
            'extractionStatus': status, 'recordProvenance': provenance,
            'review': {'status': 'SOURCE_OBSERVATION_ONLY', 'identityPromoted': False,
                'employmentPromoted': False, 'officePromoted': False, 'datePromoted': False}}
        return identity, result

    def _raw_record(self):
        raw = self._next(self.raw, 'Senate personal')
        require(type(raw) is dict and set(raw) <= SENATE_FIELDS)
        unpromoted(raw)
        candidate_id = text(raw['candidate_id'], 256)
        require(candidate_id not in self.raw_ids, 'Duplicate raw Senate record was rejected')
        self.raw_ids.add(candidate_id)
        self.raw_count += 1
        return raw

    def _accepted_subsequence(self, row):
        candidate_id = text(row['candidate_id'], 256)
        while True:
            raw = self._raw_record()
            if raw['candidate_id'] == candidate_id:
                break
            self.excluded += 1
        restored = {k: v for k, v in row.items() if k not in REPAIR_FIELDS}
        if REPAIR_FIELDS <= set(row):
            restored.update(payee_name_raw=row['pre_boundary_repair_payee_name_raw'],
                            title_raw=row['pre_boundary_repair_title_raw'], title_candidate=raw.get('title_candidate'))
        require(restored == raw, 'Accepted Senate record changed outside the recorded boundary repair')
        self.accepted += 1

    def finish(self):
        for document_id in self.verified._by_role['house-observations']:
            document = self.verified.documents[document_id]
            if document.format == 'csv':
                iterator = self.csv.get(document_id)
                if iterator is None:
                    iterator = csv_records(self.verified, document)
                require(next(iterator, None) is None, 'Unused admitted House CSV rows were rejected')
        if self.pdf is not None:
            require(next(self.pdf, None) is None, 'Unused House PDF candidate records were rejected')
        if self.raw is not None:
            # Consume all excluded trailing rows without rerunning a classifier.
            for raw in self.raw:
                require(type(raw) is dict and set(raw) <= SENATE_FIELDS)
                unpromoted(raw)
                candidate_id = text(raw['candidate_id'], 256)
                require(candidate_id not in self.raw_ids)
                self.raw_ids.add(candidate_id)
                self.raw_count += 1
                self.excluded += 1
            require(self.raw_count == self.verified.inputs['senate-personal-unfiltered'].records
                    and self.accepted == self.verified.inputs['senate-personal-candidates'].records
                    and self.excluded == self.raw_count - self.accepted)
        return {'houseCsvFieldEquivalentRows': self.csv_count,
                'housePdfCandidateJoins': self.pdf_count, 'senateAcceptedSubsequence': self.accepted,
                'senateRawRecords': self.raw_count, 'senateExcludedRecords': self.excluded,
                'senateAcceptedRepairs': self.repairs}
