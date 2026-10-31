"""Offline, byte-preserving projection of the eight reviewed Mentat workbooks.

This publisher tool never saves a workbook through openpyxl. It edits only the
closed donor-location columns, compacts unreferenced shared strings, and copies
all other OOXML bytes, including namespace declarations and cached formula values.
Original files are read through one pinned handle and are never modified.
"""
from collections import Counter
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import shutil
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

from workspace_publication import PublicationProjection

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
REL = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
NAMES = frozenset(name + ' Industry Spending Overview.xlsx' for name in (
    'Banking', 'Credit Union', 'Property & Casualty Insurance', 'Telecom',
    'Community Banks', 'Credit Arms', 'Fintech', 'Crypto'))
MAX_PART = 768 * 1024 ** 2
MAX_TOTAL = 1536 * 1024 ** 2
MAX_SST = 128 * 1024 ** 2
CELL_START = re.compile(rb'<c(?=[\s>])')
ADDRESS = re.compile(rb'\br="([A-Z]{1,3})([1-9][0-9]{0,6})"')
TYPE = re.compile(rb'\bt="([A-Za-z]+)"')
VALUE = re.compile(rb'<v>([^<]*)</v>')
FORMULA = re.compile(rb'<f(?:\s[^>]*)?>.*?</f>|<f\s[^>]*/>', re.S)
SI = re.compile(rb'<si(?=[\s>/])[^>]*(?:/>|>.*?</si>)', re.S)
ZIP = re.compile(r'([0-9]{5})(?:-?[0-9]{4})?')
EMPTY_ZIP = frozenset(('', '-', '—', 'N/A', 'NA', 'Unknown', 'UNKNOWN', 'None', 'nan'))


class ProjectionError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ProjectionError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stamp(stat):
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def semantic_node(element):
    """Unambiguous parsed-node signature without per-cell XML writer setup."""
    return (element.tag, tuple(sorted(element.attrib.items())), element.text, element.tail,
            tuple(semantic_node(child) for child in element))


def column(text):
    result = 0
    for character in text:
        result = result * 26 + ord(character) - 64
    return result


def xml(raw):
    require(b'<!DOCTYPE' not in raw.upper() and b'<!ENTITY' not in raw.upper(), 'Active XML declaration refused')
    return ET.fromstring(raw)


def cell_stream(stream, callback, writer=None):
    """Bounded lexical edits preserve every byte outside complete cell elements."""
    buffer, ended = b'', False
    while buffer or not ended:
        if not ended:
            chunk = stream.read(1024 * 1024)
            ended = not chunk
            buffer += chunk
        consumed = 0
        while True:
            match = CELL_START.search(buffer, consumed)
            if match is None:
                break
            start = match.start()
            opening = buffer.find(b'>', start)
            if opening < 0:
                break
            stop = opening + 1 if buffer[opening - 1:opening] == b'/' else buffer.find(b'</c>', opening) + 4
            if stop <= opening:
                break
            if writer:
                writer.write(buffer[consumed:start])
            replacement = callback(buffer[start:stop])
            if writer:
                writer.write(replacement)
            consumed = stop
        remainder = buffer[consumed:]
        if CELL_START.search(remainder):
            require(len(remainder) <= 2 * 1024 * 1024, 'Workbook cell exceeds its bound')
            require(not ended, 'Incomplete workbook cell')
            buffer = remainder
        else:
            keep = 0 if ended else min(4, len(remainder))
            if writer:
                writer.write(remainder[:-keep] if keep else remainder)
            buffer = remainder[-keep:] if keep else b''


def shared_strings(archive):
    info = archive.getinfo('xl/sharedStrings.xml')
    require(info.file_size <= MAX_SST, 'Shared strings exceed the reviewed bound')
    raw = archive.read(info)
    xml(raw)  # Well-formedness and the original namespace scope are retained.
    entries, texts = [], []
    matches = list(SI.finditer(raw))
    require(len(matches) <= 2_000_000, 'Too many workbook strings')
    for match in matches:
        entry = match.group()
        item = xml(entry)
        entries.append(entry)
        texts.append(''.join(node.text or '' for node in item.iter() if node.tag.rsplit('}', 1)[-1] == 't'))
    require(matches, 'A shared string table is required')
    return raw[:matches[0].start()], entries, texts, raw[matches[-1].end():]


def inventory(archive):
    infos = archive.infolist()
    names = [info.filename for info in infos]
    require(len(names) == len(set(names)) and 1 <= len(names) <= 256, 'Invalid workbook member census')
    require(sum(info.file_size for info in infos) <= MAX_TOTAL, 'Workbook expands beyond its bound')
    for info in infos:
        path = PurePosixPath(info.filename)
        require(not path.is_absolute() and '..' not in path.parts and '\\' not in info.filename and
                not info.is_dir() and info.file_size <= MAX_PART and not info.flag_bits & 1,
                'Unsafe workbook member')
        lower = info.filename.lower()
        require(not any(part in lower for part in ('vbaproject', 'externallinks/', 'embeddings/', 'activex/',
                                                   'querytables/', 'connections.xml')), 'Active workbook input refused')
    return infos


def ranges(archive):
    tables, result, protected = {}, {}, {}
    for name in archive.namelist():
        if name.startswith('xl/tables/') and name.endswith('.xml'):
            require(archive.getinfo(name).file_size < 128 * 1024, 'Workbook table metadata exceeds bound')
            tables[name] = xml(archive.read(name))
    for name in archive.namelist():
        if not re.fullmatch(r'xl/worksheets/_rels/sheet[0-9]+\.xml.rels', name):
            continue
        sheet = name.replace('/_rels/', '/').removesuffix('.rels')
        for relationship in xml(archive.read(name)):
            if not relationship.get('Type', '').endswith('/table'):
                continue
            target = posixpath.normpath(posixpath.join(posixpath.dirname(sheet), relationship.get('Target', '')))
            require(target in tables, 'Worksheet table relationship is missing')
            table = tables.pop(target)
            columns = [item.get('name') for item in table.findall(NS + 'tableColumns/' + NS + 'tableColumn')]
            reference = re.fullmatch(r'([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)', table.get('ref', ''))
            require(reference is not None and len(columns) == len(set(columns)), 'Invalid reviewed table columns')
            left, first, right, last = reference.groups()
            require(column(right) - column(left) + 1 == len(columns), 'Table column bounds differ')
            first, last = int(first) + 1, int(last) - int(table.get('totalsRowCount', '0'))
            table_name = table.get('name')
            for index, label in enumerate(columns, column(left)):
                normalized = re.sub('[^a-z0-9]', '', label.lower())
                kind = None
                if table_name == 'ContributorDetailTable' and normalized in ('street1', 'street2', 'zip'):
                    require({'Company', 'Employer', 'Occupation'}.issubset(columns), 'Unknown contributor detail schema')
                    kind = 'blank' if normalized.startswith('street') else 'zip'
                elif table_name == 'EmployeeListTable' and label == 'ZIPs':
                    require({'Person', 'Person Key', 'Total Giving'}.issubset(columns), 'Unknown employee schema')
                    kind = 'zip'
                elif (re.fullmatch(r'Cycle_[0-9]{4}_[0-9]{4}', table_name or '') or table_name == 'CycleExceptionsTable') and label == 'ZIP':
                    require({'Source ID', 'Contributor', 'Record Type', 'Person Key'}.issubset(columns), 'Unknown raw contribution schema')
                    kind = 'zip'
                elif normalized in ('street1', 'street2', 'street', 'address', 'zip', 'zips', 'zipcode',
                                     'contributorzip', 'contributorzipraw', 'email', 'phone'):
                    raise ProjectionError('Unknown sensitive semantic field in table ' + str(table_name))
                if kind:
                    result.setdefault(sheet, []).append((index, first, last, kind))
                if normalized in ('sourceid', 'personkey', 'identitybasis', 'referencekey', 'fecid', 'committeeid'):
                    protected.setdefault(sheet, []).append((index, first, last, 'identity'))
    require(not tables, 'Unattached workbook table metadata')
    return result, protected


def selected(address, policies):
    found = ADDRESS.search(address.split(b'>', 1)[0])
    require(found is not None, 'Workbook cell address is missing')
    col, row = column(found[1].decode()), int(found[2])
    require(col <= 16384 and row <= 1048576, 'Workbook cell address exceeds Excel bounds')
    matches = [kind for index, first, last, kind in policies if index == col and first <= row <= last]
    require(len(matches) <= 1, 'Overlapping workbook projection policies')
    return matches[0] if matches else None


def text_value(cell, texts):
    opening = cell.split(b'>', 1)[0]
    kind = TYPE.search(opening)
    kind = kind[1] if kind else b'n'
    value = VALUE.search(cell)
    if kind == b's':
        require(value is not None and re.fullmatch(rb'[0-9]+', value[1]), 'Invalid shared string reference')
        index = int(value[1])
        require(index < len(texts), 'Shared string reference is out of bounds')
        return texts[index], index
    if kind == b'inlineStr':
        element = xml(cell)
        return ''.join(node.text or '' for node in element.iter() if node.tag.rsplit('}', 1)[-1] == 't'), None
    return value[1].decode('utf-8') if value else '', None


def zip5(value, counts=None):
    pieces = re.split(r'[;,|]\s*', value)
    result = []
    for piece in pieces:
        stripped = piece.strip()
        if stripped in EMPTY_ZIP:
            if counts is not None:
                counts['emptyTokens'] += 1
            continue
        match = ZIP.fullmatch(stripped)
        if match is not None:
            result.append(match[1])
            if counts is not None:
                counts['retainedUs5' if len(stripped) == 5 else 'truncatedUsZip4'] += 1
        elif counts is not None:
            counts['omittedNonUsOrMalformed'] += 1
    # Closed approved policy: omit foreign/malformed tokens, without guessing,
    # padding, joining people, collapsing rows or changing any identity field.
    return '; '.join(result)


def metadata_member(name, raw, projection):
    if name != 'xl/workbook.xml':
        return raw
    # Excel's optional last-editor absPath is not a calculation/source input.
    # Remove its complete AlternateContent node, never reserialize namespaces.
    opening = re.search(rb'<workbook\b[^>]*>', raw)
    require(opening is not None, 'Workbook root metadata is missing')
    namespaces = b' '.join(re.findall(rb'xmlns(?::[A-Za-z0-9_]+)?="[^"]*"', opening.group()))
    def replace(match):
        fragment = xml(b'<root ' + namespaces + b'>' + match.group() + b'</root>')[0]
        paths = list(fragment.iter('{http://schemas.microsoft.com/office/spreadsheetml/2010/11/ac}absPath'))
        if not paths:
            return match.group()
        require(len(fragment) == 1 and len(fragment[0]) == 1 and fragment[0][0] is paths[0] and
                len(paths) == 1 and set(paths[0].attrib) == {'url'} and len(paths[0]) == 0,
                'Unknown absolute-path workbook metadata structure')
        original = paths[0].get('url')
        projection.source_identifier(original, 'workbook/editor-absolute-path')
        return b''
    result = re.sub(rb'<mc:AlternateContent\b[^>]*>.*?</mc:AlternateContent>', replace, raw, flags=re.S)
    xml(result)
    return result


def inline(cell, value):
    opening = cell[:cell.find(b'>') + 1]
    opening = re.sub(rb'\s+t="[A-Za-z]+"', b'', opening)
    opening = opening[:-2] + b'>' if opening.endswith(b'/>') else opening
    return opening[:-1] + b' t="inlineStr"><is><t xml:space="preserve">' + escape(value).encode() + b'</t></is></c>'


def string_entry(entry, value):
    matches = list(re.finditer(rb'(<t(?:\s[^>]*)?>)(.*?)(</t>)', entry, re.S))
    require(len(matches) == 1, 'Private metadata in a multi-run rich string requires review')
    match = matches[0]
    return entry[:match.start(2)] + escape(value).encode() + entry[match.end(2):]


def project_workbook(source, destination, *, expected_sha256, expected_bytes):
    source, destination = Path(source), Path(destination)
    require(source.name in NAMES and destination.name == source.name, 'Only the eight reviewed workbook names are supported')
    require(re.fullmatch('[0-9a-f]{64}', expected_sha256 or '') is not None and type(expected_bytes) is int,
            'Exact reviewed source bytes are required')
    require(not source.is_symlink() and not destination.exists() and not destination.is_symlink(), 'Unsafe workbook source/destination')
    require(destination.parent.is_dir() and not destination.parent.is_symlink(), 'A private output directory is required')
    projection = PublicationProjection()
    changed, postal_counts, removed_streets, reference_count = Counter(), Counter(), set(), 0
    path_before = source.stat()
    with source.open('rb') as handle:
        before = os.fstat(handle.fileno())
        require((path_before.st_dev, path_before.st_ino, path_before.st_size, path_before.st_mtime_ns) ==
                (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns), 'Workbook path/opened identity differs')
        require(before.st_nlink == 1 and before.st_size == expected_bytes, 'Workbook source size/link identity differs')
        require(hashlib.file_digest(handle, 'sha256').hexdigest() == expected_sha256, 'Workbook source SHA differs')
        hashed = os.fstat(handle.fileno())
        require((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
                (hashed.st_dev, hashed.st_ino, hashed.st_size, hashed.st_mtime_ns), 'Workbook source changed while hashing')
        before = hashed
        handle.seek(0)
        with zipfile.ZipFile(handle) as original:
            infos = inventory(original)
            prefix, entries, texts, suffix = shared_strings(original)
            policies, protected = ranges(original)
            safe_texts = [projection.text(value, 'sharedString:' + str(index)) for index, value in enumerate(texts)]
            used = bytearray(len(entries))
            sheets = sorted(info.filename for info in infos if re.fullmatch(r'xl/worksheets/sheet[0-9]+\.xml', info.filename))

            def projected(cell, sheet, *, collect=False):
                nonlocal reference_count
                value, index = text_value(cell, texts)
                kind = selected(cell, policies.get(sheet, ()))
                if index is None:
                    require(projection.text(value, sheet + '/inline-value') == value,
                            'Private inline/cached metadata needs a separate closed projection')
                formula = FORMULA.search(cell)
                if formula:
                    require(projection.text(formula.group().decode('utf-8'), sheet + '/formula') == formula.group().decode('utf-8'),
                            'A formula contains private request/source material; semantic review required')
                if selected(cell, protected.get(sheet, ())) and index is not None:
                    require(safe_texts[index] == value, 'Metadata projection would change a stable source identity')
                if kind:
                    require(FORMULA.search(cell) is None, 'A projected donor field contains a formula; semantic review required')
                    try:
                        replacement = '' if kind == 'blank' else zip5(value, postal_counts if collect else None)
                    except ProjectionError as error:
                        address = ADDRESS.search(cell.split(b'>', 1)[0])
                        raise ProjectionError('Postal semantic review required: ' + json.dumps({
                            'sheet': sheet, 'cell': address[0].decode() if address else None,
                            'valueSha256': sha(value.encode()), 'characters': len(value),
                            'shape': re.sub('[0-9]', '#', re.sub('[A-Za-z]', 'A', value))})) from error
                    if replacement != value:
                        if collect:
                            changed[kind] += 1
                            if kind == 'blank' and value:
                                removed_streets.add(value)
                        return inline(cell, replacement)
                if index is not None:
                    if collect:
                        used[index] = 1
                        reference_count += 1
                    elif remap[index] != index:
                        match = VALUE.search(cell)
                        cell = cell[:match.start(1)] + str(remap[index]).encode() + cell[match.end(1):]
                return cell

            for sheet in sheets:
                with original.open(sheet) as stream:
                    cell_stream(stream, lambda cell, sheet=sheet: projected(cell, sheet, collect=True))
            retained = [index for index, keep in enumerate(used) if keep]
            require(not removed_streets.intersection(safe_texts[index] for index in retained),
                    'Removed donor street remains in another semantic field; review required')
            remap = {old: new for new, old in enumerate(retained)}
            prefix = re.sub(rb'\s+(?:count|uniqueCount)="[0-9]+"', b'', prefix)
            stage = destination.parent / ('.' + destination.name + '.projection-' + uuid.uuid4().hex)
            with stage.open('xb') as output:
                with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as target:
                    for info in sorted(infos, key=lambda item: item.filename):
                        entry = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
                        entry.compress_type = zipfile.ZIP_DEFLATED
                        entry.create_system = 3
                        entry.external_attr = 0o100644 << 16
                        with target.open(entry, 'w', force_zip64=True) as raw_writer:
                            with io.BufferedWriter(raw_writer, 1024 * 1024) as writer:
                                if info.filename == 'xl/sharedStrings.xml':
                                    writer.write(prefix)
                                    for index in retained:
                                        writer.write(entries[index] if safe_texts[index] == texts[index] else
                                                     string_entry(entries[index], safe_texts[index]))
                                    writer.write(suffix)
                                elif info.filename in sheets:
                                    with original.open(info) as stream:
                                        cell_stream(stream, lambda cell, sheet=info.filename: projected(cell, sheet), writer)
                                else:
                                    if info.filename == 'xl/workbook.xml':
                                        writer.write(metadata_member(info.filename, original.read(info), projection))
                                    else:
                                        with original.open(info) as stream:
                                            shutil.copyfileobj(stream, writer, 1024 * 1024)
                output.flush()
                os.fsync(output.fileno())
            # Windows path stat and CRT fstat expose different ctime semantics.
            # Compare each API against itself; both still bind the same file ID.
            require(stamp(before) == stamp(os.fstat(handle.fileno())) and
                    stamp(path_before) == stamp(source.stat()), 'Workbook source changed during projection')
        staged_before = stage.stat()
        receipt = verify_parity(source, stage, policies=policies, safe_source_texts=safe_texts)
        require(stamp(staged_before) == stamp(stage.stat()), 'Candidate changed during parity verification')
        handle.seek(0)
        require(hashlib.file_digest(handle, 'sha256').hexdigest() == expected_sha256 and
                stamp(before) == stamp(os.fstat(handle.fileno())) and stamp(path_before) == stamp(source.stat()),
                'Original changed during parity verification')
    require(not destination.exists(), 'Workbook destination appeared during projection')
    os.link(stage, destination)
    require(destination.stat().st_ino == stage.stat().st_ino and destination.stat().st_size == stage.stat().st_size,
            'Projected workbook publication identity differs')
    stage.unlink()
    with destination.open('rb') as completed:
        projected_sha = hashlib.file_digest(completed, 'sha256').hexdigest()
    receipt.update({'source': {'name': source.name, 'bytes': expected_bytes, 'sha256': expected_sha256},
                    'projected': {'name': destination.name, 'bytes': destination.stat().st_size,
                                  'sha256': projected_sha},
                    'changedDonorCells': dict(changed), 'removedOrphanSharedStrings': len(entries) - len(retained),
                    'donorPostalPolicy': {'policy': 'US5-retain-US9-or-5dash4-truncate-other-tokens-omit',
                                          'tokens': dict(postal_counts), 'stableIdentifiersChanged': False},
                    'remainingSharedStringReferences': reference_count,
                    'privateMetadataProjection': projection.receipt(), 'originalUnchanged': True,
                    'deterministicZip': {'timestamp': '1980-01-01T00:00:00', 'compressionLevel': 6},
                    'publisherOnly': True, 'publicUploadPerformed': False})
    return receipt


def verify_parity(source, candidate, *, policies, safe_source_texts):
    """Independent XML reader compares actual cached/data-only values, not edits."""
    results = []
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(candidate) as projected:
        original_infos, candidate_infos = inventory(original), inventory(projected)
        require({i.filename for i in original_infos} == {i.filename for i in candidate_infos}, 'Workbook member roster changed')
        _, _, current_texts, _ = shared_strings(projected)
        used_candidate_strings = set()
        string_check = PublicationProjection()
        for value in current_texts:
            require(string_check.text(value, 'shared-string') == value,
                    'Private request/source material remains in shared strings')
        for info in original_infos:
            name = info.filename
            if name == 'xl/sharedStrings.xml':
                continue
            if not re.fullmatch(r'xl/worksheets/sheet[0-9]+\.xml', name):
                candidate_bytes = projected.read(name)
                require(metadata_member(name, original.read(name), PublicationProjection()) == candidate_bytes,
                        'Workbook layout/relationships/metadata changed')
                if name.endswith(('.xml', '.rels')):
                    check = PublicationProjection()
                    for element in xml(candidate_bytes).iter():
                        for value in [*element.attrib.values(), element.text or '']:
                            require(check.text(value, name) == value, 'Private request/source material remains in workbook metadata')
                continue
            summaries = []
            for archive, texts, first in ((original, safe_source_texts, True), (projected, current_texts, False)):
                digest, numeric, formulas, cells = hashlib.sha256(), 0, 0, 0
                check = PublicationProjection()
                with archive.open(name) as stream:
                    for _, element in ET.iterparse(stream, events=('end',)):
                        if not first:
                            for value in [*element.attrib.values(), element.text or '']:
                                require(check.text(value, name) == value, 'Private request/source material remains in worksheet')
                        if element.tag == NS + 'c':
                            address = element.get('r', '')
                            col_match = re.fullmatch(r'([A-Z]+)([1-9][0-9]*)', address)
                            require(col_match is not None, 'Invalid cached-value cell address')
                            kinds = [kind for col, begin, end, kind in policies.get(name, ())
                                     if col == column(col_match[1]) and begin <= int(col_match[2]) <= end]
                            kind = kinds[0] if kinds else None
                            value = element.find(NS + 'v')
                            typ = element.get('t', 'n')
                            if typ == 's':
                                require(value is not None and value.text is not None and value.text.isdigit() and int(value.text) < len(texts), 'Invalid projected shared string reference')
                                text = texts[int(value.text)]
                                if not first:
                                    used_candidate_strings.add(int(value.text))
                            elif typ == 'inlineStr':
                                text = ''.join(node.text or '' for node in element.iter(NS + 't'))
                            else:
                                text = value.text if value is not None and value.text else ''
                            if kind:
                                require(element.find(NS + 'f') is None, 'Projected donor field acquired a formula')
                                expected = ('' if kind == 'blank' else zip5(text)) if first else text
                                # These are the only cells excluded from exact semantic parity.
                                attributes = sorted((key, value) for key, value in element.attrib.items() if key != 't')
                                digest.update(json.dumps([address, 'projected-donor-field', expected, attributes], ensure_ascii=False).encode() + b'\n')
                            else:
                                if typ == 's':
                                    value.text = text
                                digest.update(repr(semantic_node(element)).encode('utf-8') + b'\n')
                                if typ == 'n' and text:
                                    Decimal(text)
                                    numeric += 1
                                formulas += int(element.find(NS + 'f') is not None)
                            cells += 1
                            element.clear()
                        elif element.tag == NS + 'row':
                            element.clear()
                summaries.append({'sha256': digest.hexdigest(), 'cells': cells,
                                  'unchangedNumericCaches': numeric, 'unchangedFormulas': formulas})
            require(summaries[0] == summaries[1], 'Workbook cached/data-only semantic parity failed at ' + name)
            results.append({'sheet': name, **summaries[0]})
        require(len(used_candidate_strings) == len(current_texts), 'Projected workbook contains orphan shared strings')
    return {'schemaVersion': 1, 'status': 'passed-projected-workbook-parity',
            'bytePreservingLayoutAndRelationships': True, 'allCellsCompared': True,
            'cachedFormulaValuesPreserved': True, 'sheets': results}
