"""Read user-selected CSV evidence into a data-root store; no collection or attribution.

The store lives under the console data root, so an import survives a restart, a
stale-build relaunch and a launcher port hop: every console started on the same
data root lists the same imports. Nothing here contacts a network service and
nothing is attributed to a donor; the rows are the reader's own file.
"""
from collections import defaultdict
import codecs
from contextlib import closing, contextmanager
import csv
from datetime import date as date_type, datetime, time as time_type, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat
import string
import tempfile
import threading
import time
import uuid
import zipfile

from cross_reference_data import _source_url

# Bytes are now the only memory-relevant gate: the reader streams the file to
# disk and the parser walks it row by row into sqlite, so neither the request
# thread nor the console ever holds the decoded file. Paul's ruling 2026-09-16
# raised the ceiling to "way past 5 or even 50" MB: the request thread only
# copies CHUNK_BYTES (64 KiB) at a time, so a bigger ceiling costs it no more
# time per chunk, and ingest itself runs off-thread with progress reported to
# the page as rows and bytes are read. MAX_BYTES is therefore a time and disk
# budget for that off-thread ingest, not a request-thread memory one.
#
# Disk is what the ceiling actually budgets, and disk is what measured
# reproducibly. On a 6,000,146-byte 20-column file of 21,759 rows (2026-09-16),
# storing every normalised field beside the cells cost 5.06x the source
# (30,343,168 bytes), because each row then repeated its header names and its
# derived values. Storing only the cells and recomputing normalize() for the
# hundred rows a page shows costs 1.58x (9,498,624 bytes), the same figure in
# every run - that is the design used here, so one import costs source plus
# 1.58x source in sqlite, about 2.6x the source in all. At the 500 MB ceiling
# that is about 1.3 GB of disk for one import. KEEP_BYTES budgets source bytes
# only (KEEP_IMPORTS stays 10); at 1,000,000,000 (1 GB) of kept sources, the
# sqlite databases behind them add roughly another 1.58 GB, about 2.6 GB kept
# on disk worst case. Lower MAX_BYTES or KEEP_BYTES if that is too much for
# the machine.
#
# Ingest time is deliberately NOT the justification, because it could not be
# pinned down here. The identical 6 MB ingest measured between 0.82 s and
# 34.66 s across runs on this host - a 40x spread on identical work, with
# 1.6 GB free of 31.5 GB and standalone runs sometimes slower than in-server
# ones. That is S0's Finding 2 environment (working-set trimming under memory
# pressure), not a property of this code, so no s/MB rate quoted here would
# survive being checked on a quiet machine; at 500 MB the honest expectation
# is minutes, not seconds. What did hold in every run is the part that
# matters: the POST returns in well under a second (0.08-0.81 s observed)
# because the request thread only copies bytes to disk, and the wait that
# follows is off-thread with rows and bytes reported to the page as they are
# read. The ceiling is therefore about how long a reader is willing to watch
# a progress line, not about blocking the console.
#
# Reading back is bounded by the page, not the file: a 100-row page measured
# 15-16 ms, and 46-47 ms at offset 7,000 of a 7,253-row committee.
#
# MAX_ROWS bounds ingest time and page offsets only - the rows themselves live
# in sqlite, not in memory - and scales with MAX_BYTES: 500 MB at roughly
# 100 bytes/row is about 5,000,000 rows.
#
# The generic 7 MB JSON body gate in server.py's do_POST (Content-Length >
# 7_000_000) still bounds the legacy in-request JSON import path only; the
# streamed CSV path above answers to MAX_BYTES.
MAX_BYTES = 500_000_000
MAX_COLUMNS = 200
MAX_ROWS = 5_000_000
CHUNK_BYTES = 65_536
KEEP_IMPORTS = 10
KEEP_BYTES = 1_000_000_000
PAGE_LIMIT = 1000

# The picker refused every name that did not end .csv, and the reader refused
# every byte that was not UTF-8, so the files Paul actually holds - a workbook,
# a tab-separated export, an openFEC .json, an FEC bulk .zip - could not be
# opened at all. Format is chosen by suffix first and content second: the
# suffix says which reader to use, and that reader then decides the encoding,
# the delimiter or the worksheet from the bytes themselves.
#
# JSON is the one format read whole, because an export is one document and
# cannot be walked row by row without a streaming parser, so it carries its own
# much smaller ceiling. A parsed document is not its bytes: every object, key
# and string becomes an interpreter object, which costs several times the file
# on disk before a single row is written, and this machine reads under the
# memory pressure S0 recorded as its Finding 2. 25 MB is therefore the ceiling
# for the one format that cannot be streamed; every other format streams, so
# MAX_BYTES still governs them.
MAX_JSON_BYTES = 25_000_000
DELIMITED_SUFFIXES = ('.csv', '.tsv', '.txt')
WORKBOOK_SUFFIXES = ('.xlsx', '.xlsm')
ACCEPTED_SUFFIXES = DELIMITED_SUFFIXES + WORKBOOK_SUFFIXES + ('.json', '.zip')
DELIMITERS = (',', ';', '\t', '|')
SNIFF_BYTES = 32768
HEADER_FIELD = re.compile(r'[A-Za-z_][A-Za-z0-9_ ]*')
INPUTS = Path(__file__).resolve().parents[1] / 'inputs'

# FEC bulk files ship without a header row, so the header has to come from
# somewhere. The order is: the header file the reader gave, then a copy under
# mentat/inputs, and only then the table below, which is the layout the
# commission publishes for each file type. A header file on disk wins over the
# table, because these layouts have changed before and the file beside the data
# is the one that describes it.
_BULK_TRANSACTION = ('CMTE_ID', 'AMNDT_IND', 'RPT_TP', 'TRANSACTION_PGI', 'IMAGE_NUM', 'TRANSACTION_TP',
                     'ENTITY_TP', 'NAME', 'CITY', 'STATE', 'ZIP_CODE', 'EMPLOYER', 'OCCUPATION',
                     'TRANSACTION_DT', 'TRANSACTION_AMT', 'OTHER_ID', 'TRAN_ID', 'FILE_NUM', 'MEMO_CD',
                     'MEMO_TEXT', 'SUB_ID')
_BULK_TO_CANDIDATE = _BULK_TRANSACTION[:16] + ('CAND_ID',) + _BULK_TRANSACTION[16:]
BULK_HEADERS = {
    # indiv26.zip is named for the layout and holds itcont.txt, named for the
    # content, so both names have to resolve to the same header.
    'indiv': _BULK_TRANSACTION,
    'itcont': _BULK_TRANSACTION,
    'itoth': _BULK_TRANSACTION,
    'oth': _BULK_TRANSACTION,
    'itpas2': _BULK_TO_CANDIDATE,
    'pas2': _BULK_TO_CANDIDATE,
    'cm': ('CMTE_ID', 'CMTE_NM', 'TRES_NM', 'CMTE_ST1', 'CMTE_ST2', 'CMTE_CITY', 'CMTE_ST', 'CMTE_ZIP',
           'CMTE_DSGN', 'CMTE_TP', 'CMTE_PTY_AFFILIATION', 'CMTE_FILING_FREQ', 'ORG_TP',
           'CONNECTED_ORG_NM', 'CAND_ID'),
    'cn': ('CAND_ID', 'CAND_NAME', 'CAND_PTY_AFFILIATION', 'CAND_ELECTION_YR', 'CAND_OFFICE_ST',
           'CAND_OFFICE', 'CAND_OFFICE_DISTRICT', 'CAND_ICI', 'CAND_STATUS', 'CAND_PCC', 'CAND_ST1',
           'CAND_ST2', 'CAND_CITY', 'CAND_ST', 'CAND_ZIP'),
    'ccl': ('CAND_ID', 'CAND_ELECTION_YR', 'FEC_ELECTION_YR', 'CMTE_ID', 'CMTE_TP', 'CMTE_DSGN', 'LINKAGE_ID'),
    'oppexp': ('CMTE_ID', 'AMNDT_IND', 'RPT_YR', 'RPT_TP', 'IMAGE_NUM', 'LINE_NUM', 'FORM_TP_CD',
               'SCHED_TP_CD', 'NAME', 'CITY', 'STATE', 'ZIP_CODE', 'TRANSACTION_DT', 'TRANSACTION_AMT',
               'TRANSACTION_PGI', 'PURPOSE', 'CATEGORY', 'CATEGORY_DESC', 'MEMO_CD', 'MEMO_TEXT',
               'ENTITY_TP', 'SUB_ID', 'FILE_NUM', 'TRAN_ID', 'BACK_REF_TRAN_ID'),
}
# Longest first, so 'itpas2' is not read as 'pas2' and 'itoth' not as 'oth'.
BULK_TYPES = tuple(sorted(BULK_HEADERS, key=len, reverse=True))

COMMITTEE_FIELDS = ('committee_id', 'cmte_id', 'source_committee_id', 'pac_committee_id', 'pac_id', 'recipient_key')
NAME_FIELDS = ('committee_name', 'cmte_nm', 'source_committee_name', 'pac_name', 'recipient_committee', 'recipient')
DATE_FIELDS = ('transaction_date', 'transaction_dt', 'date', 'payment_date')
AMOUNT_FIELDS = ('amount', 'transaction_amount', 'transaction_amt', 'net_included_amount')
CYCLE_FIELDS = ('cycle', 'election_cycle', 'two_year_transaction_period')
SCHEMAS = (
    ('receipt', ('contribution_receipt_amount', 'receipt_amount'), ('contribution_receipt_date', 'receipt_date')),
    ('disbursement', ('disbursement_amount',), ('disbursement_date',)),
    ('independent_spending', ('expenditure_amount',), ('expenditure_date',)),
)
TYPES = {
    'receipt':'receipt', 'receipts':'receipt', 'schedule_a':'receipt', 'sa':'receipt',
    'contribution_receipt':'receipt', 'contribution':'receipt', 'disbursement':'disbursement', 'disbursements':'disbursement',
    'schedule_b':'disbursement', 'sb':'disbursement', 'independent_expenditure':'independent_spending',
    'independent_spending':'independent_spending', 'schedule_e':'independent_spending', 'se':'independent_spending',
}
DIRECTIONS = {'s':'Support', 'support':'Support', 'o':'Oppose', 'oppose':'Oppose', 'opposition':'Oppose',
              'contribution_other':'Contribution / Other', 'contribution':'Contribution / Other',
              'unknown':'Unknown'}

WARNINGS = (
    'Imported observations are not verified coverage or donor-attributed PAC spending. Duplicate and amended rows are preserved; totals may overlap.',
    'Committee names and IDs are taken from this CSV; their registration and committee type have not been independently verified.',
    'Cycle aggregates have no inferred transaction date. Missing or ambiguous amounts, dates, or types remain unsupported.',
)

# Every refusal names the file or the reason, because a blank status line in
# the page is itself a defect. The three messages that quote a limit are built
# from the constants when they are raised, so a changed limit cannot leave a
# stale number in the reader's status line.
M_NAME = 'Choose a CSV file with a name ending in .csv.'
M_EMPTY = 'The CSV file is empty.'
M_UTF8 = 'Use a UTF-8 CSV file without invalid text characters.'
M_COMMITTEE_COLUMN = 'The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.'
M_NO_COMMITTEE_ROWS = 'The CSV has no rows with one valid FEC committee ID (C followed by eight digits).'
M_BUSY = 'Another CSV is still being read. Wait for it to finish.'
M_PAGE = 'Choose a valid CSV row page (1–1,000 rows).'
M_INTERRUPTED = 'Reading was interrupted by a console restart. Choose the file again.'
M_COMMITTEE = 'Choose a committee in this imported CSV.'
M_CYCLE = 'Choose a cycle recorded in this CSV.'
# M_UTF8 above is kept defined for callers that still import it, but nothing
# raises it any more: a file that is not valid UTF-8 is decoded as
# Windows-1252 and says so in the catalog, and only content that is not text at
# all (a NUL byte outside UTF-16) is refused, as M_BINARY.
M_BINARY = 'This file contains binary data and could not be read as text.'
M_JSON_SHAPE = 'The JSON must be an openFEC export ({"results": [...]}) or a list of objects.'
M_HEADER = ('This looks like an FEC bulk file without a header row and its name is not a known bulk '
            'type. Give its header file too.')
M_XLSX_READ = 'The workbook could not be opened. It may be corrupt or password-protected.'
M_ZIP_READ = 'The ZIP could not be opened. It may be corrupt.'
M_CP1252 = 'Decoded as Windows-1252 because the file is not valid UTF-8.'
STORE_DIRECTORY = 'evidence-csv'
IDENTIFIER = re.compile(r'csv-[a-f0-9]{32}')


def bytes_message():
    return f'Choose a CSV no larger than {MAX_BYTES // 1_000_000} MB.'


def columns_message():
    return f'The CSV needs unique nonempty column names, with no more than {MAX_COLUMNS} columns.'


def rows_message():
    return f'Choose a CSV containing no more than {MAX_ROWS:,} rows.'


def M_READ(row_number):
    return f'The CSV could not be read at row {row_number:,}. Check its quoted fields and delimiter.'


def M_GONE(identifier):
    return f'This CSV import is no longer on disk ({identifier}). Choose the file again.'


def M_SHORT(received, expected):
    return f'The upload ended early: {received:,} of {expected:,} bytes arrived.'


def M_TYPE(suffix):
    return (f'This file type ({suffix or "no extension"}) is not supported. '
            'Choose CSV, TSV, TXT, XLSX, JSON or an FEC bulk ZIP.')


def M_ZIP(members):
    return f'The ZIP must hold exactly one .txt or .csv file; it holds: {", ".join(members[:10])}.'


def M_SHEET(name, sheets):
    return f'Worksheet {name!r} is not in this workbook. Sheets: {", ".join(sheets)}.'


def M_PATH(path, reason):
    return f'Cannot open {path}: {reason}'


def json_size_message():
    return f'Choose a JSON file no larger than {MAX_JSON_BYTES // 1_000_000} MB, or export it as CSV.'


_DERIVED = {'M_BYTES':bytes_message, 'M_COLUMNS':columns_message, 'M_ROWS':rows_message,
            'M_JSON_SIZE':json_size_message}


def __getattr__(name):
    """Serve the three limit messages at attribute time, not at import time.

    A caller reading ``evidence_csv.M_BYTES`` gets the message for the limit
    that is in force now, which keeps a monkeypatched limit and the message the
    reader sees in agreement.
    """
    if name in _DERIVED:
        return _DERIVED[name]()
    raise AttributeError(f'module {__name__!r} has no attribute {name!r}')


def limits():
    return {'max_bytes':MAX_BYTES, 'max_columns':MAX_COLUMNS, 'max_rows':MAX_ROWS,
            'max_bytes_message':bytes_message(), 'max_columns_message':columns_message(),
            'max_rows_message':rows_message(), 'accepted_suffixes':list(ACCEPTED_SUFFIXES),
            'max_json_bytes':MAX_JSON_BYTES}


def decode_name(value):
    """Decode a percent-encoded upload name header without importing urllib here."""
    from urllib.parse import unquote
    return unquote(str(value or ''))


def page_args(offset, limit):
    if isinstance(offset, bool) or isinstance(limit, bool):
        raise ValueError(M_PAGE)
    try:
        offset, limit = int(str(offset).strip()), int(str(limit).strip())
    except (TypeError, ValueError):
        raise ValueError(M_PAGE) from None
    if not 0 <= offset <= MAX_ROWS or not 1 <= limit <= PAGE_LIMIT:
        raise ValueError(M_PAGE)
    return offset, limit


def key(value):
    return re.sub(r'[^a-z0-9]+', '_', str(value).strip().lower()).strip('_')


def first(row, names):
    return next((row[name].strip() for name in names if row.get(name, '').strip()), '')


def number(value):
    text = str(value).strip()
    negative = text.startswith('(') and text.endswith(')')
    if negative:
        text = text[1:-1].strip()
    text = text.removeprefix('$').strip()
    if negative and text.startswith(('+', '-')):
        return None
    if ',' in text and not re.fullmatch(r'[+-]?\d{1,3}(?:,\d{3})+(?:\.\d+)?', text):
        return None
    text = text.replace(',', '')
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', text):
        return None
    try:
        value = Decimal(text)
        value = -value if negative else value
        return value if value.is_finite() and abs(value) <= Decimal('1e300') and math.isfinite(float(value)) else None
    except (InvalidOperation, ValueError, OverflowError):
        return None


def date(value):
    text = value.strip()
    try:
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}(?:[T ][0-9:.+Z-]+)?', text):
            return datetime.fromisoformat(text.replace('Z', '+00:00')).date().isoformat()
        if re.fullmatch(r'\d{1,2}/\d{1,2}/\d{4}', text):
            return datetime.strptime(text, '%m/%d/%Y').date().isoformat()
        if re.fullmatch(r'\d{8}', text):
            return datetime.strptime(text, '%Y%m%d' if text[:2] in ('19','20','21') else '%m%d%Y').date().isoformat()
    except ValueError:
        pass
    return None


def cycle(value):
    match = re.fullmatch(r'(?:(\d{4})[-–])?(\d{4})', value.strip())
    if (match and 1980 <= int(match[2]) <= 2100 and int(match[2]) % 2 == 0
            and (not match[1] or int(match[1]) == int(match[2]) - 1)):
        return match[2]
    return ''


def normalize(raw, row_number, columns, extra_cells=()):
    row = dict(zip(columns, raw.values()))
    issues = []
    supplied_ids = {re.sub(r'^FEC:', '', row[name].strip().upper()) for name in COMMITTEE_FIELDS if row.get(name, '').strip()}
    valid_ids = {value for value in supplied_ids if re.fullmatch(r'C\d{8}', value)}
    committee = next(iter(valid_ids)) if len(valid_ids) == 1 and len(supplied_ids) == 1 else ''
    if not committee:
        issues.append('A unique valid FEC committee ID is missing or conflicting.')
    specific = [(kind, amount_fields, dates) for kind,amount_fields,dates in SCHEMAS if first(row, amount_fields)]
    explicit_kind = TYPES.get(key(first(row, ('record_type', 'activity_type', 'schedule', 'schedule_type', 'type', 'transaction_type'))))
    kind, amount_raw, date_raw = 'unsupported', '', ''
    basis = 'dated observation'
    if len(specific) == 1:
        kind, amount_fields, dates = specific[0]
        amount_raw, date_raw = first(row, amount_fields), first(row, dates + DATE_FIELDS)
        if explicit_kind and explicit_kind != kind:
            issues.append('The explicit row type conflicts with its amount column; no channel total was assigned.')
    elif len(specific) > 1:
        issues.append('Several receipt/activity amount columns are populated; the row cannot be assigned to one channel.')
    else:
        amount_raw, date_raw = first(row, AMOUNT_FIELDS), first(row, DATE_FIELDS)
        kind = explicit_kind or 'unsupported'
    direction_raw = first(row, ('support_oppose', 'support_oppose_indicator', 'direction'))
    direction = DIRECTIONS.get(key(direction_raw), 'Unknown')
    selected_cycle = cycle(first(row, CYCLE_FIELDS))
    if (not specific and kind == 'unsupported' and row.get('net_included_amount', '').strip()
            and row.get('source_committee_id', '').strip() and direction_raw and selected_cycle):
        kind, basis = 'reported_aggregate', 'cycle aggregate'
    amount_value = number(amount_raw)
    observed_date = date(date_raw)
    if amount_value is None:
        issues.append('The observed amount is missing or not a finite number.')
    if not observed_date and (date_raw or basis != 'cycle aggregate'):
        issues.append('The transaction date is missing or invalid; no date was inferred.')
    if direction_raw and key(direction_raw) not in DIRECTIONS and kind in ('independent_spending', 'reported_aggregate'):
        issues.append('The activity direction is not recognized; it was not assigned to support or opposition.')
    if kind == 'unsupported':
        issues.append('The CSV does not identify a supported receipt or activity type.')
    if extra_cells:
        issues.append('This row contains more values than its header.')
    channel = {'receipt':'Receipts', 'disbursement':'Disbursements'}.get(kind)
    if kind == 'independent_spending':
        channel = 'Independent spending · ' + direction.lower()
    if kind == 'reported_aggregate':
        channel = 'Reported cycle aggregate · ' + direction.lower()
    return {
        'row_number':row_number, 'raw':raw, 'extra_cells':list(extra_cells),
        'committee_id':committee, 'committee_name':first(row, NAME_FIELDS),
        'kind':kind, 'channel':channel or 'Unsupported', 'basis':basis,
        'amount':float(amount_value) if amount_value is not None else None, '_amount':amount_value,
        'date':observed_date, 'date_raw':date_raw, 'cycle':selected_cycle,
        'direction':direction if kind in ('independent_spending', 'reported_aggregate') else '',
        'counterparty':first(row, ('contributor_name', 'contributor', 'recipient_name', 'candidate_name', 'candidate_officeholder', 'reported_name', 'name')),
        'candidate_id':first(row, ('candidate_id', 'cand_id', 'candidate_id_as_filed')),
        'candidate_name':first(row, ('candidate_name', 'candidate_officeholder', 'candidate_name_as_filed')),
        'record_id':first(row, ('sub_id', 'transaction_id', 'tran_id', 'record_id')),
        'source_url':_source_url(first(row, ('source_url', 'pdf_url', 'filing_url'))),
        'status':'unsupported' if issues else 'supported', 'issues':issues,
    }


def rebuild(headers, columns, line_number, cells):
    """Rebuild one normalised row from the original cells that were stored.

    normalize() is pure - it reads only its arguments, the module tables and
    _source_url, itself a pure string check - so recomputing it here returns
    exactly what the ingest computed. Only the cells need to live on disk, and
    storing the derived fields as well would have cost several times the size
    of the file they came from.
    """
    raw = {header:cells[index] if index < len(cells) else '' for index,header in enumerate(headers)}
    return normalize(raw, line_number, columns, cells[len(headers):])


def atomic_json(path, value, attempts=6):
    """Replace a record in one step so a reader never sees a half-written file.

    attempts=1 for an advisory write, such as the progress the page polls. A
    scanner or indexer holding import.json open for a moment is common on
    Windows, and a progress update is not worth waiting on: retrying with a
    backoff inside the row loop adds its sleeps to the ingest, and raising
    would fail a perfectly good import over a counter nobody had read yet.
    """
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(attempts):
        try:
            os.replace(temporary, path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                temporary.unlink(missing_ok=True)
                raise
            time.sleep(0.05 * (attempt + 1))


def descriptive(record):
    """How this import was read, in the terms the page shows the reader.

    The same block rides on the JOB and on the CATALOG, so a listing read back
    tomorrow says what a poll of the running import said: which reader ran,
    whether the file came from a browser upload or from a path on this
    computer, which worksheet, which encoding and delimiter, and where an FEC
    bulk header came from.
    """
    name = str(record.get('name') or '')
    fmt = record.get('format') or ''
    if not fmt and Path(name).suffix.lower() in ACCEPTED_SUFFIXES:
        # An import read before these fields existed still names its format,
        # from the only evidence it kept: the file name it was stored under.
        fmt = source_format(name, record.get('header_path') or '')
    return {'format':fmt, 'source_kind':record.get('source_kind') or 'upload',
            'source_path':record.get('source_path') or '', 'sheet':record.get('sheet') or '',
            'sheets':list(record.get('sheets') or []), 'sheets_read':list(record.get('sheets_read') or []), 'encoding':record.get('encoding') or '',
            'delimiter':record.get('delimiter') or '', 'header_source':record.get('header_source') or ''}


def stored_catalog(record):
    """One stored catalog, with any descriptive field it predates filled in.

    The catalog is written once, when the import is read, so an import already
    on disk carries the S3-era shape. The record beside it is filled the same
    way for both, so the listing the page renders has one shape whether the
    file was read today or last week.
    """
    catalog = dict(record.get('catalog') or {})
    return {**descriptive(record), **catalog} if catalog else catalog


def job_view(record):
    """The reading/ready/failed record the page polls, without store internals."""
    return {'id':record.get('id', ''), 'name':record.get('name', ''), 'state':record.get('state', 'failed'),
            'bytes':int(record.get('bytes') or 0), 'bytes_read':int(record.get('bytes_read') or 0),
            'rows_read':int(record.get('rows_read') or 0), 'message':record.get('message') or '',
            'started_at':record.get('started_at'), 'finished_at':record.get('finished_at'),
            'catalog':record.get('catalog'), **descriptive(record)}


# One ingest thread per process, registered here so a record that claims to be
# reading can be told apart from one whose reader died with a restart.
_ACTIVE_LOCK = threading.Lock()
_ACTIVE = {}


def accepted_suffix(name):
    """The suffix this reader will open, or a refusal naming the one it got."""
    if not isinstance(name, str) or not name.strip() or len(name) > 250:
        raise ValueError(M_NAME)
    suffix = Path(name).suffix.lower()
    if suffix not in ACCEPTED_SUFFIXES:
        raise ValueError(M_TYPE(suffix))
    return suffix


def bulk_type(stem):
    """The FEC bulk file type a name begins with, if it begins with one."""
    lowered = str(stem or '').lower()
    return next((name for name in BULK_TYPES if lowered.startswith(name)), '')


def source_format(name, header_path=''):
    """Which reader a name asks for.

    Decided from the name alone, so the JOB the page polls can say what is
    being read from the first poll onwards. A .zip here is always an FEC bulk
    archive, and a .txt is bulk only when its name is a bulk type or the reader
    supplied a header file; every other delimited name is read as text with its
    own header row.
    """
    suffix = Path(str(name or '')).suffix.lower()
    if suffix in WORKBOOK_SUFFIXES:
        return 'xlsx'
    if suffix == '.json':
        return 'json'
    if suffix == '.zip':
        return 'fec_bulk'
    if suffix == '.txt' and bulk_type(Path(str(name or '')).stem):
        return 'fec_bulk'
    if suffix in ('.txt', '.csv') and header_path:
        return 'fec_bulk'
    return 'delimited'


def import_id(digest, sheet=''):
    """'csv-' + the content digest, with a chosen worksheet folded in after it.

    A file with no worksheet choice keeps the identifier its bytes alone gave
    it before worksheets existed, so a CSV already in the store is still found
    under the id it was stored with. Two worksheets of one workbook are two
    imports, so the sheet name has to reach the identifier for the second one
    not to dedupe onto the first.
    """
    if sheet:
        digest = digest.copy()
        digest.update(b'\x00' + sheet.encode('utf-8'))
    return 'csv-' + digest.hexdigest()[:32]


class Upload:
    """One in-flight file: size-gated, hashed and written as it arrives.

    Nothing is decoded here any more. A workbook, a zip and a UTF-16 export are
    all legitimate now and none of them is UTF-8 text, so the encoding question
    belongs to the reader that walks the file, not to the thread copying bytes
    off a socket.
    """

    def __init__(self, store, name, sheet='', header_path=''):
        self.suffix = accepted_suffix(name)
        self.store = store
        self.name = Path(name).name
        self.sheet = str(sheet or '')
        self.header_path = str(header_path or '')
        self.path = store.incoming / (uuid.uuid4().hex + self.suffix)
        self.bytes = 0
        self._handle = self.path.open('wb')
        self._digest = hashlib.sha256()
        self._blank = True
        self._closed = False

    def write(self, chunk):
        """Accept one chunk, refusing before it is written if it crosses a limit.

        A refusal closes and deletes the part-written file here rather than
        waiting for the caller to abort. An open handle keeps its directory
        undeletable on Windows, so a caller that simply stops writing after a
        refusal would strand both the file and the sweep that should remove it.
        """
        if not chunk:
            return
        try:
            if self.bytes + len(chunk) > MAX_BYTES:
                raise ValueError(bytes_message())
            if self._blank and chunk.strip():
                self._blank = False
            self._digest.update(chunk)
            self._handle.write(chunk)
            self.bytes += len(chunk)
        except BaseException:
            self.abort()
            raise

    def abort(self):
        self._close()
        try:
            self.path.unlink(missing_ok=True)
        except OSError:
            pass

    def _close(self):
        if not self._closed:
            self._closed = True
            try:
                self._handle.close()
            except OSError:
                pass

    def finish(self):
        """Name the import by its content and hand the file to a reader thread."""
        self._close()
        if self._blank:
            self.abort()
            raise ValueError(M_EMPTY)
        try:
            # The workbook is opened by the reader thread and nowhere else, so
            # a corrupt file and an unknown worksheet are reported the way
            # every other unreadable file is: on the JOB the page is polling,
            # not as a refusal of the upload that has already arrived.
            return self.store.adopt(import_id(self._digest, self.sheet), self.name, self.path, self.bytes,
                                    self._digest.hexdigest(), suffix=self.suffix, sheet=self.sheet,
                                    header_path=self.header_path)
        except BaseException:
            self.abort()
            raise


class Reader:
    """One open source: its header row, its rows, and how far reading has got.

    Every format answers with the same three things - a header list, an
    iterator of (line_number, cells) and a byte position for the progress the
    page polls - so the row loop in read_source never learns which format it is
    walking, and the per-row path (row cap, normalise, batch, totals) stays the
    one CSV imports have always used.
    """

    def __init__(self, headers, rows, tell, meta, warnings=()):
        self.headers = list(headers)
        self.rows = rows
        self.tell = tell
        self.meta = dict(meta)
        self.warnings = list(warnings)


def text_encoding(open_bytes):
    """Choose an encoding for a text source, refusing content that is not text.

    A BOM decides on its own. Otherwise the file is decoded once, incrementally,
    in CHUNK_BYTES chunks: valid UTF-8 is read as UTF-8 and anything else falls
    back to Windows-1252, which cannot fail and is what Excel writes on this
    machine. The reader is told in the catalog when that fallback was used,
    because a mangled name is a data question, not a reason to refuse the file.
    A NUL byte outside UTF-16 is not text at all, and is refused.
    """
    with open_bytes() as raw:
        head = raw.read(4)
    if head.startswith(codecs.BOM_UTF8):
        bom = 'utf-8-sig'
    elif head.startswith(codecs.BOM_UTF16_LE) or head.startswith(codecs.BOM_UTF16_BE):
        return 'utf-16'
    else:
        bom = ''
    decoder = codecs.getincrementaldecoder('utf-8')()
    valid = True
    with open_bytes() as raw:
        while True:
            chunk = raw.read(CHUNK_BYTES)
            if not chunk:
                break
            if b'\x00' in chunk:
                raise ValueError(M_BINARY)
            if valid:
                try:
                    decoder.decode(chunk)
                except UnicodeDecodeError:
                    valid = False
    if valid:
        try:
            decoder.decode(b'', True)
        except UnicodeDecodeError:
            valid = False
    return (bom or 'utf-8') if valid else 'cp1252'


def head_text(open_bytes, encoding, size=SNIFF_BYTES):
    with open_bytes() as raw:
        head = raw.read(size)
    return head.decode(encoding, 'replace')


def steady_delimiter(lines):
    """The candidate whose count repeats identically on every line, if any.

    That is what a delimiter does: 20 pipes on every row. A comma inside one
    field does not, and neither does a semicolon that appears in a note.
    Returns the steadiest candidate and the count that made it steady.
    """
    chosen, best = '', 0
    for candidate in DELIMITERS:
        counts = [line.count(candidate) for line in lines]
        if counts and counts[0] > best and all(count == counts[0] for count in counts):
            chosen, best = candidate, counts[0]
    return chosen, best


def sniff_dialect(text, suffix):
    """The delimiter a text file is written with, and the dialect to read it.

    csv.Sniffer answers first, because it settles quoting at the same time.
    It is overruled only by a candidate that is strictly steadier than the one
    it chose, because its own preference table puts the comma ahead of the
    pipe: on an FEC bulk row that holds one name like "Doe, Jane" and twenty
    pipes, Sniffer returns the comma and the row reads as two fields. When
    Sniffer cannot answer at all, the steadiest candidate stands on its own.
    """
    lines = [line for line in text.splitlines()[:20] if line.strip()]
    if suffix == '.tsv' and any('\t' in line for line in lines[:1]):
        return type('tabs', (csv.excel,), {'delimiter':'\t'})
    chosen, best = steady_delimiter(lines)
    try:
        dialect = csv.Sniffer().sniff(text, delimiters=''.join(DELIMITERS))
    except csv.Error:
        dialect = None
    if dialect is not None:
        counts = [line.count(dialect.delimiter) for line in lines]
        steady = bool(counts) and counts[0] > 0 and all(count == counts[0] for count in counts)
        if not chosen or chosen == dialect.delimiter or (steady and counts[0] >= best):
            return dialect
        return type('steadier', (csv.excel,), {'delimiter':chosen})
    if not chosen:
        totals = {candidate:sum(line.count(candidate) for line in lines) for candidate in DELIMITERS}
        chosen = (max(totals, key=lambda candidate: totals[candidate]) if any(totals.values())
                  else ('\t' if suffix == '.tsv' else ','))
    return type('sniffed', (csv.excel,), {'delimiter':chosen})


def header_like(fields):
    """True when a first line reads as column names rather than as data."""
    values = [str(field).strip() for field in fields]
    return bool(values) and all(HEADER_FIELD.fullmatch(value) for value in values)


def cell_text(value):
    """One workbook cell as the string a CSV would have carried."""
    if value is None:
        return ''
    if value is True:
        return 'TRUE'
    if value is False:
        return 'FALSE'
    if isinstance(value, float):
        return str(int(value)) if value.is_integer() and math.isfinite(value) else repr(value)
    if isinstance(value, datetime):
        return (value.date().isoformat()
                if (value.hour, value.minute, value.second, value.microsecond) == (0, 0, 0, 0)
                else value.isoformat())
    if isinstance(value, timedelta):
        return str(value)
    if isinstance(value, (date_type, time_type)):
        return value.isoformat()
    return str(value)


def json_text(value):
    """One JSON field as a cell: a nested value keeps its own JSON text."""
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def read_header_file(path):
    """One line of CSV column names, from the header file the reader gave."""
    path = Path(path)
    try:
        if not path.is_file():
            raise ValueError(M_PATH(str(path), 'no such file'))
        if path.stat().st_size > 1_000_000:
            raise ValueError(M_PATH(str(path), 'larger than 1 MB'))
        raw = path.read_bytes()
    except PermissionError as error:
        raise ValueError(M_PATH(str(path), 'permission denied')) from error
    except OSError as error:
        raise ValueError(M_PATH(str(path), 'no such file')) from error
    try:
        text = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        text = raw.decode('cp1252')
    line = next((item for item in text.splitlines() if item.strip()), '')
    fields = [field.strip() for field in next(csv.reader([line]), [])]
    if not fields or not any(fields):
        raise ValueError(M_PATH(str(path), 'it holds no column names'))
    return fields


def bulk_headers(stems, header_path=''):
    """The header row for a bulk file: given, found on disk, or bundled.

    More than one name can carry the type: the commission ships its individual
    contributions as itcont.txt inside indiv26.zip, so one name describes the
    content and the other the layout. Both are known here, and either may be
    the one a reader's own copy was renamed to, so each is tried in turn.
    """
    if header_path:
        return read_header_file(header_path), 'header_path'
    name = next((found for found in (bulk_type(stem) for stem in stems) if found), '')
    if not name:
        raise ValueError(M_HEADER)
    try:
        found = sorted(INPUTS.glob(f'**/{name}_header_file.csv'))
    except OSError:
        found = []
    if found:
        return read_header_file(found[0]), 'inputs'
    return list(BULK_HEADERS[name]), 'bundled'


@contextmanager
def delimited_reader(path, record):
    """CSV, TSV and plain text: one header row, then rows as they are read."""
    suffix = Path(str(record.get('name') or path.name)).suffix.lower()

    def open_bytes():
        return path.open('rb')

    encoding = text_encoding(open_bytes)
    dialect = sniff_dialect(head_text(open_bytes, encoding), suffix)
    warnings = [M_CP1252] if encoding == 'cp1252' else []
    meta = {'encoding':encoding, 'delimiter':dialect.delimiter, 'header_source':'row', 'sheets':[]}
    with path.open('r', encoding=encoding, newline='') as handle:
        reader = csv.reader(handle, dialect=dialect, strict=True)
        try:
            headers = next(reader, [])
        except csv.Error as error:
            raise ValueError(M_READ(reader.line_num)) from error
        if suffix == '.txt' and dialect.delimiter == '|' and not header_like(headers):
            raise ValueError(M_HEADER)

        def rows():
            try:
                for values in reader:
                    yield reader.line_num, values
            except csv.Error as error:
                raise ValueError(M_READ(reader.line_num)) from error

        yield Reader(headers, rows(), lambda: handle.buffer.tell(), meta, warnings)


@contextmanager
def bulk_reader(path, record):
    """An FEC bulk file: pipe-delimited, no header row, header from elsewhere."""
    name = str(record.get('name') or path.name)
    if Path(name).suffix.lower() == '.zip':
        try:
            archive = zipfile.ZipFile(path)
        except (OSError, ValueError, zipfile.BadZipFile) as error:
            raise ValueError(M_ZIP_READ) from error
        with archive:
            members = [item for item in archive.infolist() if not item.is_dir()]
            chosen = [item for item in members if item.filename.lower().endswith(('.txt', '.csv'))]
            if len(chosen) != 1:
                raise ValueError(M_ZIP([item.filename for item in members]))
            member = chosen[0]
            if member.file_size > MAX_BYTES:
                raise ValueError(bytes_message())
            with bulk_rows(lambda: archive.open(member), (Path(member.filename).stem, Path(name).stem),
                           record, int(member.file_size)) as reader:
                yield reader
        return
    with bulk_rows(lambda: path.open('rb'), (Path(name).stem,), record, path.stat().st_size) as reader:
        yield reader


class BoundedBytes(io.RawIOBase):
    """A byte stream that refuses to hand out more than `limit` bytes.

    A zip member's declared size is the only gate before extraction; a lying
    header could otherwise stream past MAX_BYTES into one unbounded csv line.
    The stored source files are already capped on disk, so this only matters
    for what is decompressed on the way out of an archive.
    """

    def __init__(self, raw, limit):
        super().__init__()
        self._raw, self._limit, self._count = raw, int(limit), 0

    def readable(self):
        return True

    def readinto(self, buffer):
        chunk = self._raw.read(len(buffer))
        if not chunk:
            return 0
        self._count += len(chunk)
        if self._count > self._limit:
            raise ValueError(bytes_message())
        buffer[:len(chunk)] = chunk
        return len(chunk)

    def tell(self):
        return self._count

    def close(self):
        try:
            self._raw.close()
        finally:
            super().close()


@contextmanager
def bulk_rows(open_bytes, stems, record, size):
    """The rows of one bulk file or zip member, under a resolved header."""
    encoding = text_encoding(open_bytes)
    headers, header_source = bulk_headers(stems, record.get('header_path') or '')
    warnings = [f'Header taken from {header_source}.']
    if encoding == 'cp1252':
        warnings.append(M_CP1252)
    meta = {'encoding':encoding, 'delimiter':'|', 'header_source':header_source, 'sheets':[]}
    raw = io.BufferedReader(BoundedBytes(open_bytes(), MAX_BYTES))
    # QUOTE_NONE because bulk rows are not quoted: an apostrophe or an inch
    # mark in an employer name is a character there, not an opening quote.
    stream = io.TextIOWrapper(raw, encoding=encoding, newline='')
    reader = csv.reader(stream, delimiter='|', quoting=csv.QUOTE_NONE)

    def rows():
        try:
            for values in reader:
                yield reader.line_num, values
        except csv.Error as error:
            raise ValueError(M_READ(reader.line_num)) from error

    def tell():
        try:
            return int(raw.tell())
        except (OSError, ValueError):
            return size

    try:
        yield Reader(headers, rows(), tell, meta, warnings)
    finally:
        try:
            stream.detach()
        except ValueError:
            pass
        raw.close()


COMMITTEE_KEYS = frozenset(COMMITTEE_FIELDS)
AMOUNT_KEYS = frozenset(AMOUNT_FIELDS) | frozenset(name for _, amounts, _ in SCHEMAS for name in amounts)
DATE_KEYS = frozenset(DATE_FIELDS) | frozenset(name for _, _, dates in SCHEMAS for name in dates)


def M_NO_SHEET(sheets):
    return f'No worksheet in this workbook has a Committee ID column. Sheets: {", ".join(sheets)}.'


def header_row(rows, limit=50):
    """(row index, header cells) of the first header-like row.

    Exports and Mentat's own workbooks put a title, a note and a source line
    above the header, so the header is the first row (within `limit`) whose
    cells name a committee column; failing that, the first row with three or
    more filled cells; failing that, the first row with anything in it.
    """
    wide = first = None
    for index, values in enumerate(rows, 1):
        if index > limit:
            break
        cells = [cell_text(value) for value in values]
        while cells and not cells[-1].strip():
            cells.pop()
        filled = [cell for cell in cells if cell.strip()]
        if not filled:
            continue
        if {key(cell) for cell in filled} & COMMITTEE_KEYS:
            return index, cells
        if wide is None and len(filled) >= 3:
            wide = (index, cells)
        if first is None:
            first = (index, cells)
    return wide or first or (0, [])


def sheet_grade(columns):
    """How much of a table a header describes: 3 dated amounts, 2 aggregates, 1 ids only, 0 none."""
    keys = set(columns)
    if not keys & COMMITTEE_KEYS:
        return 0
    if keys & AMOUNT_KEYS and keys & DATE_KEYS:
        return 3
    if 'net_included_amount' in keys:
        return 2
    return 1


@contextmanager
def workbook_reader(path, record):
    """The worksheets of an .xlsx/.xlsm that hold the table, read cell by cell.

    With no worksheet named, every sheet is surveyed (its first rows only): the
    best-graded header wins, ties going to the sheet with more rows, and every
    sheet whose header is identical to the winner's is read after it as one
    table. A Mentat industry workbook therefore reads its cycle sheets
    together and skips its overview, summary and list sheets; a workbook with
    one data sheet reads that one. Naming a worksheet reads only that one.
    """
    import openpyxl
    try:
        book = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile) as error:
        raise ValueError(M_XLSX_READ) from error
    try:
        sheets = list(book.sheetnames)
        # Written onto the record before anything can fail, so a refused
        # workbook still tells the reader which worksheets it has.
        record['sheets'] = sheets
        chosen = str(record.get('sheet') or '')
        if chosen and chosen not in sheets:
            raise ValueError(M_SHEET(chosen, sheets))
        survey = {}
        for name in sheets:
            sheet = book[name]
            index, headers = header_row(sheet.iter_rows(values_only=True))
            columns = [key(item) for item in headers]
            survey[name] = (index, headers, columns, sheet_grade(columns), int(sheet.max_row or 0))
        if chosen:
            group = [chosen]
        else:
            best = max(sheets, key=lambda name: (survey[name][3], survey[name][4], -sheets.index(name)))
            if survey[best][3] == 0:
                raise ValueError(M_NO_SHEET(sheets))
            group = [name for name in sheets if survey[name][2] == survey[best][2]]
        headers = list(survey[group[0]][1])
        if not headers:
            raise ValueError(M_EMPTY)
        if len(headers) > MAX_COLUMNS:
            raise ValueError(columns_message())
        size = int(record.get('bytes') or 0)
        meta = {'encoding':'', 'delimiter':'', 'header_source':'row', 'sheets':sheets,
                'sheet':group[0], 'sheets_read':list(group)}
        warnings = ([f'Read {len(group)} worksheets with the same columns: {", ".join(group)}.']
                    if len(group) > 1 else [])

        def rows():
            for name in group:
                first = survey[name][0]
                index = first
                try:
                    for index, row in enumerate(book[name].iter_rows(values_only=True), 1):
                        if index <= first:
                            continue
                        cells = [cell_text(value) for value in row]
                        # Trailing blanks past the header are the sheet's used
                        # range, not extra values: dropping them keeps a whole
                        # worksheet from being reported as ragged rows.
                        while len(cells) > len(headers) and not cells[-1].strip():
                            cells.pop()
                        yield index, cells
                except ValueError:
                    raise
                except Exception as error:
                    raise ValueError(M_READ(index)) from error

        yield Reader(headers, rows(), lambda: size, meta, warnings)
    finally:
        book.close()

@contextmanager
def json_reader(path, record):
    """An openFEC export or a list of objects, read whole under its own cap."""
    size = path.stat().st_size
    if size > MAX_JSON_BYTES:
        raise ValueError(json_size_message())

    def open_bytes():
        return path.open('rb')

    encoding = text_encoding(open_bytes)
    try:
        document = json.loads(path.read_text(encoding=encoding))
    except (ValueError, UnicodeDecodeError, OSError) as error:
        raise ValueError(M_JSON_SHAPE) from error
    items = document.get('results') if isinstance(document, dict) else document
    if not isinstance(items, list) or not all(isinstance(item, dict) for item in items):
        raise ValueError(M_JSON_SHAPE)
    if not items:
        raise ValueError(M_EMPTY)
    headers, seen = [], set()
    for item in items:
        for name in item:
            if name not in seen:
                seen.add(name)
                headers.append(str(name))
    if len(headers) > MAX_COLUMNS:
        raise ValueError(columns_message())
    warnings = [M_CP1252] if encoding == 'cp1252' else []
    meta = {'encoding':encoding, 'delimiter':'', 'header_source':'row', 'sheets':[]}

    def rows():
        for number, item in enumerate(items, 1):
            yield number, [json_text(item.get(name)) for name in headers]

    yield Reader(headers, rows(), lambda: size, meta, warnings)


@contextmanager
def open_source(path, record):
    """The reader for one stored source, chosen by the format on its record."""
    readers = {'xlsx':workbook_reader, 'json':json_reader, 'fec_bulk':bulk_reader}
    fmt = record.get('format') or source_format(record.get('name', ''), record.get('header_path', ''))
    with readers.get(fmt, delimited_reader)(path, record) as reader:
        yield reader


def drive_roots():
    """Every drive root that answers, for a picker that starts from nothing."""
    if os.name != 'nt':
        return ['/']
    roots = []
    for letter in string.ascii_uppercase:
        root = f'{letter}:\\'
        try:
            if Path(root).is_dir():
                roots.append(root)
        except OSError:
            continue
    return roots


def shortcuts():
    """The folders a reader actually keeps evidence in, when they exist."""
    home = Path.home()
    found = []
    for label, candidates in (('Downloads', (home / 'Downloads', home / 'OneDrive' / 'Downloads')),
                              ('Mentat inputs', (INPUTS,)),
                              ('Desktop', (home / 'Desktop', home / 'OneDrive' / 'Desktop'))):
        for candidate in candidates:
            try:
                if candidate.is_dir():
                    found.append({'name':label, 'path':str(candidate)})
                    break
            except OSError:
                continue
    return found


def directory_entries(directory, limit=2000):
    """One folder's children, folders first, with what the reader may open."""
    rows, truncated = [], False
    with os.scandir(directory) as scan:
        for entry in scan:
            if len(rows) >= limit:
                truncated = True
                break
            try:
                is_dir = entry.is_dir()
                info = entry.stat()
                size = None if is_dir else int(info.st_size)
                modified = datetime.fromtimestamp(info.st_mtime, timezone.utc).isoformat()
            except OSError:
                is_dir, size, modified = False, None, None
            suffix = Path(entry.name).suffix.lower()
            rows.append({'name':entry.name, 'path':str(Path(directory) / entry.name),
                         'kind':'dir' if is_dir else 'file', 'size':size, 'modified':modified,
                         'supported':(not is_dir) and suffix in ACCEPTED_SUFFIXES})
    rows.sort(key=lambda row: (row['kind'] != 'dir', row['name'].lower()))
    return rows, truncated


def browse(path=''):
    """List one folder on this computer, for the console's own file picker.

    Read-only, and answered only over an authenticated POST. Nothing is hidden
    by a hidden or system attribute: this is Paul's own machine, and a file he
    cannot see in the picker is a file he cannot import.
    """
    text = str(path or '').strip().strip('"')
    if not text:
        return {'path':'', 'parent':None, 'roots':drive_roots(), 'shortcuts':shortcuts(),
                'entries':[], 'truncated':False}
    try:
        chosen = Path(text).expanduser().resolve()
        info = os.stat(chosen)
    except PermissionError as error:
        raise ValueError(M_PATH(text, 'permission denied')) from error
    except (OSError, ValueError) as error:
        raise ValueError(M_PATH(text, 'no such file')) from error
    if not stat.S_ISDIR(info.st_mode):
        raise ValueError(M_PATH(text, 'it is not a folder'))
    try:
        entries, truncated = directory_entries(chosen)
    except PermissionError as error:
        raise ValueError(M_PATH(text, 'permission denied')) from error
    except OSError as error:
        raise ValueError(M_PATH(text, 'it could not be listed')) from error
    parent = str(chosen.parent) if chosen.parent != chosen else None
    return {'path':str(chosen), 'parent':parent, 'roots':drive_roots(), 'shortcuts':shortcuts(),
            'entries':entries, 'truncated':truncated}


class Store:
    """CSV imports kept under the console data root, one directory per file."""

    def __init__(self, data_root, evict=True):
        # evict=False for a read-only preview: it shares the data root with the
        # console that owns it, and a preview must not delete the imports the
        # reader chose in the main console. Sweeping abandoned uploads and old
        # failures is safe from either and stays on.
        self.data_root = Path(data_root)
        self.evicts = bool(evict)
        self.root = self.data_root / STORE_DIRECTORY
        self.incoming = self.root / 'incoming'
        self.incoming.mkdir(parents=True, exist_ok=True)
        self.root = self.root.resolve()
        self.incoming = self.incoming.resolve()
        self.sweep()

    def directory(self, identifier):
        return self.root / identifier

    def record_path(self, identifier):
        return self.directory(identifier) / 'import.json'

    def source_path(self, identifier, suffix=''):
        """The stored source, kept under the suffix it arrived with."""
        directory = self.directory(identifier)
        if suffix:
            return directory / ('source' + suffix)
        existing = sorted(path for path in directory.glob('source.*') if path.is_file())
        return existing[0] if existing else directory / 'source.csv'

    def database_path(self, identifier):
        return self.directory(identifier) / 'rows.sqlite'

    def begin_upload(self, name, sheet='', header_path=''):
        return Upload(self, name, sheet=sheet, header_path=header_path)

    def refusal(self, name, message, source_kind='path', source_path='', sheet='', header_path=''):
        """Record a refusal the page can poll, the way a failed read is polled.

        A path import can be refused before a byte is read - the file is not
        there, it is a folder, it is too large, it is a type this reader does
        not open - and the page is watching one channel, the JOB. Recording the
        refusal as a failed import keeps the reader's status line in one place
        instead of splitting 'could not start' from 'could not read', and the
        hourly sweep drops it like any other failure.
        """
        suffix = Path(str(name or '')).suffix.lower()
        identifier = 'csv-' + hashlib.sha256(
            ('refused\x00' + str(source_path or name) + '\x00' + str(sheet or '')).encode('utf-8')).hexdigest()[:32]
        stamp = time.time()
        value = {'id':identifier, 'name':str(name or ''), 'state':'failed', 'bytes':0, 'bytes_read':0,
                 'rows_read':0, 'message':str(message), 'started_at':stamp, 'finished_at':stamp,
                 'catalog':None, 'columns':[], 'sha256':'', 'imported_at':'', 'pid':os.getpid(),
                 'format':source_format(name, header_path) if suffix in ACCEPTED_SUFFIXES else '',
                 'source_kind':source_kind, 'source_path':str(source_path or ''), 'sheet':str(sheet or ''),
                 'sheets':[], 'encoding':'', 'delimiter':'', 'header_source':'', 'suffix':suffix,
                 'header_path':str(header_path or '')}
        self.directory(identifier).mkdir(parents=True, exist_ok=True)
        atomic_json(self.record_path(identifier), value)
        return job_view(value)

    def import_path(self, path, sheet='', header_path=''):
        """Read a file the reader chose by path, with no browser upload at all.

        The answer is a JOB either way: a file that can be read starts a reader
        thread, and one that cannot is recorded as a refusal under the same
        identifier shape, so the page polls one thing and the console's own
        message - never a Python exception - is what the reader is shown.
        """
        text = str(path or '').strip().strip('"')
        try:
            return self.read_chosen_path(text, sheet, header_path)
        except ValueError as error:
            return self.refusal(Path(text).name or text, str(error), source_path=text,
                                sheet=sheet, header_path=header_path)

    def read_chosen_path(self, text, sheet='', header_path=''):
        """Copy the chosen file into the store and start reading it.

        The copy runs in the same CHUNK_BYTES steps an upload arrives in, so
        the import reads a still snapshot rather than a file being written
        underneath it, and the identifier is the digest of exactly the bytes
        that were read.
        """
        if not text:
            raise ValueError(M_PATH(text, 'no such file'))
        try:
            chosen = Path(text).expanduser()
            info = os.stat(chosen)
        except PermissionError as error:
            raise ValueError(M_PATH(text, 'permission denied')) from error
        except (OSError, ValueError) as error:
            raise ValueError(M_PATH(text, 'no such file')) from error
        if stat.S_ISDIR(info.st_mode):
            raise ValueError(M_PATH(text, 'it is a folder'))
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(M_PATH(text, 'no such file'))
        suffix = accepted_suffix(chosen.name)
        if info.st_size > MAX_BYTES:
            raise ValueError(M_PATH(text, f'larger than {MAX_BYTES // 1_000_000} MB'))
        header_path = str(header_path or '')
        if header_path:
            read_header_file(header_path)
        sheet = str(sheet or '')
        target = self.incoming / (uuid.uuid4().hex + suffix)
        digest, total, blank = hashlib.sha256(), 0, True
        try:
            try:
                with chosen.open('rb') as raw, target.open('wb') as handle:
                    while True:
                        chunk = raw.read(CHUNK_BYTES)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_BYTES:
                            raise ValueError(M_PATH(text, f'larger than {MAX_BYTES // 1_000_000} MB'))
                        if blank and chunk.strip():
                            blank = False
                        digest.update(chunk)
                        handle.write(chunk)
            except PermissionError as error:
                raise ValueError(M_PATH(text, 'permission denied')) from error
            except OSError as error:
                raise ValueError(M_PATH(text, 'it could not be read')) from error
            if blank:
                raise ValueError(M_EMPTY)
            return self.adopt(import_id(digest, sheet), chosen.name, target, total, digest.hexdigest(),
                              suffix=suffix, sheet=sheet, source_kind='path',
                              source_path=str(chosen), header_path=header_path)
        except BaseException:
            try:
                target.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def read_record(self, identifier, attempts=5):
        """Read a record, tolerating a reader that loses a race with a writer.

        import.json is rewritten while it is being read: the ingest reports its
        progress into it every thousand rows and the page polls it twice a
        second. On Windows the reader's open can lose that race and come back
        with a sharing violation, and treating that as 'this import is not
        there' told the reader their file was gone while it sat on disk being
        read. A file that is genuinely absent still answers at once.
        """
        path = self.record_path(identifier)
        for attempt in range(attempts):
            try:
                value = json.loads(path.read_text(encoding='utf-8'))
            except FileNotFoundError:
                return None
            except (OSError, ValueError):
                if attempt == attempts - 1:
                    return None
                time.sleep(0.02 * (attempt + 1))
                continue
            return value if isinstance(value, dict) else None
        return None

    def reading(self, identifier, record):
        """True only while this process still has a live reader for the import."""
        if record.get('pid') != os.getpid():
            return False
        with _ACTIVE_LOCK:
            thread = _ACTIVE.get(str(self.directory(identifier)))
        return bool(thread is not None and thread.is_alive())

    def record(self, identifier):
        """The stored record, with a reader that died recorded as interrupted."""
        if not isinstance(identifier, str) or not IDENTIFIER.fullmatch(identifier):
            raise ValueError(M_GONE(identifier))
        value = self.read_record(identifier)
        if value is None or not self.directory(identifier).is_dir():
            raise ValueError(M_GONE(identifier))
        if value.get('state') == 'reading' and not self.reading(identifier, value):
            value['state'] = 'failed'
            value['message'] = M_INTERRUPTED
            value['finished_at'] = time.time()
            try:
                atomic_json(self.record_path(identifier), value)
            except OSError:
                pass
        return value

    def job(self, identifier):
        return job_view(self.record(identifier))

    def wait(self, identifier, timeout=None):
        """Block until the import stops reading. For the legacy route and tests."""
        with _ACTIVE_LOCK:
            thread = _ACTIVE.get(str(self.directory(identifier)))
        if thread is not None:
            thread.join(timeout)
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            current = self.job(identifier)
            if current['state'] != 'reading':
                return current
            if deadline is not None and time.monotonic() >= deadline:
                return current
            time.sleep(0.01)

    def ready(self, identifier):
        value = self.record(identifier)
        if value.get('state') == 'failed':
            raise ValueError(value.get('message') or M_GONE(identifier))
        if value.get('state') != 'ready' or not value.get('catalog'):
            raise ValueError(M_BUSY)
        return value

    def sources(self):
        records = []
        for path in sorted(self.root.glob('csv-*')):
            if not path.is_dir():
                continue
            value = self.read_record(path.name)
            if value and value.get('state') == 'ready' and value.get('catalog'):
                records.append(value)
        records.sort(key=lambda value: (str(value.get('imported_at') or ''), str(value.get('id') or '')), reverse=True)
        return [stored_catalog(value) for value in records]

    def catalog(self, identifier):
        return stored_catalog(self.ready(identifier))

    def select(self, identifier, committee='', cycle='', offset=0, limit=200):
        value = self.ready(identifier)
        source = stored_catalog(value)
        offset, limit = page_args(offset, limit)
        committee = committee or (source['committees'][0]['id'] if source['committees'] else '')
        chosen = next((item for item in source['committees'] if item['id'] == committee), None)
        if chosen is None:
            raise ValueError(M_COMMITTEE)
        if cycle and cycle not in source['cycles']:
            raise ValueError(M_CYCLE)
        database = self.database_path(identifier)
        if not database.is_file():
            raise ValueError(M_GONE(identifier))
        stored = '' if committee == 'unassigned' else committee
        where, parameters = 'committee_id = ?', [stored]
        if cycle:
            where, parameters = where + ' AND cycle = ?', parameters + [cycle]
        try:
            with closing(sqlite3.connect(database)) as connection:
                total = connection.execute(f'SELECT COUNT(*) FROM csv_rows WHERE {where}', parameters).fetchone()[0]
                supported = connection.execute(f'SELECT COUNT(*) FROM csv_rows WHERE {where} AND status = ?',
                                               parameters + ['supported']).fetchone()[0]
                page = connection.execute(f'SELECT line_num, cells FROM csv_rows WHERE {where} ORDER BY row_number LIMIT ? OFFSET ?',
                                          parameters + [limit, offset]).fetchall()
                channels = connection.execute(f'SELECT channel, amount, row_count FROM totals WHERE {where}', parameters).fetchall()
        except sqlite3.Error as error:
            raise ValueError(M_GONE(identifier)) from error
        amounts, counts = defaultdict(Decimal), defaultdict(int)
        for channel, amount, row_count in channels:
            amounts[channel] += Decimal(amount)
            counts[channel] += row_count
        headers = value.get('columns', [])
        columns = [key(item) for item in headers]
        return {'source':source, 'committee':chosen, 'committees':source['committees'],
                'cycles':source['cycles'], 'selected_cycle':cycle, 'columns':headers,
                'rows':[{name:item for name,item in rebuild(headers, columns, line_number, json.loads(cells)).items()
                         if not name.startswith('_')} for line_number,cells in page],
                'totals':[{'channel':channel, 'amount':float(amounts[channel]), 'row_count':counts[channel]}
                          for channel in sorted(amounts)],
                'supported_rows':supported, 'unsupported_rows':total - supported,
                'offset':offset, 'limit':limit, 'total_rows':total, 'has_more':offset + limit < total,
                'warnings':list(source.get('warnings') or WARNINGS)}

    def adopt(self, identifier, name, path, size, digest, suffix='.csv', sheet='',
              source_kind='upload', source_path='', header_path=''):
        """Take a finished upload: dedupe by content, else start reading it."""
        existing = self.read_record(identifier)
        if existing and existing.get('state') == 'ready' and existing.get('catalog'):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
            return job_view(existing)
        with _ACTIVE_LOCK:
            for stale in [running for running, thread in _ACTIVE.items() if not thread.is_alive()]:
                _ACTIVE.pop(stale, None)
            if _ACTIVE:
                raise ValueError(M_BUSY)
            directory = self.directory(identifier)
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True, exist_ok=True)
            os.replace(path, self.source_path(identifier, suffix))
            value = {'id':identifier, 'name':name, 'state':'reading', 'bytes':int(size), 'bytes_read':0,
                     'rows_read':0, 'message':'', 'started_at':time.time(), 'finished_at':None,
                     'catalog':None, 'columns':[], 'sha256':digest, 'imported_at':'', 'pid':os.getpid(),
                     'format':source_format(name, header_path), 'source_kind':source_kind,
                     'source_path':str(source_path or ''), 'sheet':str(sheet or ''), 'sheets':[],
                     'encoding':'', 'delimiter':'', 'header_source':'', 'suffix':suffix,
                     'header_path':str(header_path or '')}
            atomic_json(self.record_path(identifier), value)
            thread = threading.Thread(target=self.ingest, args=(identifier, value), daemon=True,
                                      name='evidence-csv-' + identifier)
            _ACTIVE[str(directory)] = thread
            thread.start()
        return job_view(value)

    def ingest(self, identifier, value):
        """Read one import to completion. No exception may leave this thread."""
        try:
            catalog, columns = self.read_source(identifier, value)
        except ValueError as error:
            value.update(state='failed', message=str(error), finished_at=time.time())
        except Exception as error:
            value.update(state='failed', message=f'The CSV could not be read: {type(error).__name__}: {error}',
                         finished_at=time.time())
        else:
            value.update(state='ready', message='', finished_at=time.time(), catalog=catalog,
                         columns=columns, imported_at=catalog['imported_at'])
        if value['state'] == 'failed':
            # Keep the directory so the page can still read the reason; drop the
            # bytes, which are now only a partial database and a refused file.
            for path in (self.database_path(identifier),
                         self.source_path(identifier, value.get('suffix', ''))):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        try:
            atomic_json(self.record_path(identifier), value)
        except OSError:
            pass
        if value['state'] == 'ready' and self.evicts:
            try:
                self.evict()
            except OSError:
                pass
        try:
            self.sweep()
        except OSError:
            pass

    def read_source(self, identifier, value):
        """Walk the file once into sqlite, accumulating exact totals as it goes."""
        source = self.source_path(identifier, value.get('suffix', ''))
        database = self.database_path(identifier)
        database.unlink(missing_ok=True)
        names = defaultdict(set)
        committee_rows, committee_supported = defaultdict(int), defaultdict(int)
        amounts, counts = defaultdict(Decimal), defaultdict(int)
        cycles = set()
        rows_read = unassigned = supported = unsupported = 0
        with closing(sqlite3.connect(database)) as connection:
            connection.execute('PRAGMA journal_mode=OFF')
            connection.execute('PRAGMA synchronous=OFF')
            # Only the original cells are stored. The columns beside them are
            # the ones a selection filters, counts or orders on; every other
            # field the page shows is recomputed by rebuild() at select time.
            connection.execute('CREATE TABLE csv_rows (row_number INTEGER PRIMARY KEY, line_num INTEGER NOT NULL, '
                               'committee_id TEXT NOT NULL, cycle TEXT NOT NULL, status TEXT NOT NULL, '
                               'channel TEXT NOT NULL, amount TEXT, cells TEXT NOT NULL)')
            connection.execute('CREATE TABLE totals (committee_id TEXT NOT NULL, cycle TEXT NOT NULL, '
                               'channel TEXT NOT NULL, amount TEXT NOT NULL, row_count INTEGER NOT NULL)')
            with open_source(source, value) as reader:
                headers = reader.headers
                columns = [key(item) for item in headers]
                if not headers or len(headers) > MAX_COLUMNS or not all(columns) or len(set(columns)) != len(columns):
                    raise ValueError(columns_message())
                if not set(columns).intersection(COMMITTEE_FIELDS):
                    raise ValueError(M_COMMITTEE_COLUMN)
                # How the file turned out to be written is recorded before the
                # first row, so a reader watching the progress line sees the
                # encoding and delimiter that were chosen, not only the count.
                value.update(reader.meta)
                extra_warnings = list(reader.warnings)
                batch = []
                for line_number, values in reader.rows:
                    if not any(item.strip() for item in values):
                        continue
                    if rows_read >= MAX_ROWS:
                        raise ValueError(rows_message())
                    row = rebuild(headers, columns, line_number, values)
                    rows_read += 1
                    committee, row_cycle = row['committee_id'], row['cycle']
                    if committee:
                        names[committee].add(row['committee_name'] or committee)
                        committee_rows[committee] += 1
                        committee_supported[committee] += row['status'] == 'supported'
                    else:
                        unassigned += 1
                    if row_cycle:
                        cycles.add(row_cycle)
                    if row['status'] == 'supported':
                        supported += 1
                        amounts[(committee, row_cycle, row['channel'])] += row['_amount']
                        counts[(committee, row_cycle, row['channel'])] += 1
                    else:
                        unsupported += 1
                    batch.append((rows_read, line_number, committee, row_cycle, row['status'], row['channel'],
                                  None if row['_amount'] is None else str(row['_amount']),
                                  json.dumps(values, ensure_ascii=False)))
                    if len(batch) >= 1000:
                        connection.executemany('INSERT INTO csv_rows VALUES (?,?,?,?,?,?,?,?)', batch)
                        connection.commit()
                        batch.clear()
                        value.update(bytes_read=reader.tell(), rows_read=rows_read)
                        try:
                            atomic_json(self.record_path(identifier), value, attempts=1)
                        except OSError:
                            pass
                if batch:
                    connection.executemany('INSERT INTO csv_rows VALUES (?,?,?,?,?,?,?,?)', batch)
            if not names:
                raise ValueError(M_NO_COMMITTEE_ROWS)
            connection.executemany('INSERT INTO totals VALUES (?,?,?,?,?)',
                                   [(committee, row_cycle, channel, str(amounts[(committee, row_cycle, channel)]),
                                     counts[(committee, row_cycle, channel)])
                                    for committee, row_cycle, channel in amounts])
            connection.execute('CREATE INDEX csv_rows_committee ON csv_rows (committee_id, cycle, row_number)')
            connection.execute('CREATE INDEX totals_committee ON totals (committee_id, cycle)')
            connection.commit()
        committees = []
        for committee in sorted(names):
            labels = sorted(name for name in names[committee] if name != committee) or [committee]
            committees.append({'id':committee, 'name':' / '.join(labels), 'rows':committee_rows[committee],
                               'supported_rows':committee_supported[committee]})
        if unassigned:
            committees.append({'id':'unassigned', 'name':'Unassigned committee rows', 'rows':unassigned, 'supported_rows':0})
        value.update(bytes_read=int(value.get('bytes') or 0), rows_read=rows_read)
        return ({'id':identifier, 'name':value['name'], 'sha256':value['sha256'], 'row_count':rows_read,
                 'committees':committees, 'cycles':sorted(cycles, reverse=True),
                 'supported_rows':supported, 'unsupported_rows':unsupported, 'unassigned_rows':unassigned,
                 'session_only':False, 'imported_at':datetime.now(timezone.utc).isoformat(),
                 'bytes':int(value.get('bytes') or 0), 'warnings':list(WARNINGS) + extra_warnings,
                 **descriptive(value)}, headers)

    def sweep(self):
        """Drop abandoned uploads and old failures. Undeletable paths wait a turn."""
        cutoff = time.time() - 3600
        for path in self.incoming.glob('*.*'):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass
        for path in self.root.glob('csv-*'):
            if not path.is_dir():
                continue
            value = self.read_record(path.name)
            if value and value.get('state') == 'failed' and float(value.get('finished_at') or 0) < cutoff:
                shutil.rmtree(path, ignore_errors=True)

    def evict(self):
        """Keep the newest imports within the file and byte budgets."""
        records = []
        for path in self.root.glob('csv-*'):
            if not path.is_dir():
                continue
            value = self.read_record(path.name)
            if value and value.get('state') == 'ready':
                records.append(value)
        records.sort(key=lambda value: (str(value.get('imported_at') or ''), str(value.get('id') or '')), reverse=True)
        kept = 0
        for index, value in enumerate(records):
            kept += int(value.get('bytes') or 0)
            if index >= KEEP_IMPORTS or kept > KEEP_BYTES:
                shutil.rmtree(self.directory(value['id']), ignore_errors=True)

    def ingest_text(self, name, text):
        """Write text through an upload so in-memory callers use the one parser."""
        upload = self.begin_upload(name)
        try:
            if not isinstance(text, str) or not text.strip():
                raise ValueError(M_EMPTY)
            if '\x00' in text or '�' in text:
                raise ValueError(M_BINARY)
            encoded = text.encode('utf-8')
            for start in range(0, len(encoded), CHUNK_BYTES):
                upload.write(encoded[start:start + CHUNK_BYTES])
        except UnicodeEncodeError as error:
            upload.abort()
            raise ValueError(M_BINARY) from error
        except BaseException:
            upload.abort()
            raise
        return upload.finish()

    def document(self, identifier, text):
        """Materialise a stored import in the in-memory shape the legacy API uses."""
        value = self.ready(identifier)
        headers = value.get('columns', [])
        columns = [key(item) for item in headers]
        rows = []
        with closing(sqlite3.connect(self.database_path(identifier))) as connection:
            for line_number, cells in connection.execute('SELECT line_num, cells FROM csv_rows ORDER BY row_number'):
                rows.append(rebuild(headers, columns, line_number, json.loads(cells)))
        names = defaultdict(set)
        for row in rows:
            if row['committee_id']:
                names[row['committee_id']].add(row['committee_name'] or row['committee_id'])
        return {'id':identifier, 'name':value['name'], 'sha256':value['sha256'], 'text':text,
                'columns':value.get('columns', []), 'rows':rows,
                'committee_names':{committee:sorted(labels) for committee,labels in names.items()},
                'imported_at':value.get('imported_at', ''), 'bytes':int(value.get('bytes') or 0)}


def parse(name, text):
    """Parse text in memory through the same streaming reader the store uses."""
    with tempfile.TemporaryDirectory(prefix='mentat-evidence-csv-') as temporary:
        store = Store(temporary)
        started = store.ingest_text(name, text)
        finished = store.wait(started['id'])
        if finished['state'] != 'ready':
            raise ValueError(finished['message'] or M_GONE(finished['id']))
        return store.document(finished['id'], text)


def catalog(document):
    rows = document['rows']
    committees = []
    counts, supported_counts = defaultdict(int), defaultdict(int)
    for row in rows:
        counts[row['committee_id']] += 1
        supported_counts[row['committee_id']] += row['status'] == 'supported'
    for identifier, names in sorted(document['committee_names'].items()):
        labels = sorted(name for name in names if name != identifier) or [identifier]
        committees.append({'id':identifier, 'name':' / '.join(labels), 'rows':counts[identifier],
                           'supported_rows':supported_counts[identifier]})
    unassigned = sum(not row['committee_id'] for row in rows)
    if unassigned:
        committees.append({'id':'unassigned', 'name':'Unassigned committee rows', 'rows':unassigned, 'supported_rows':0})
    return {'id':document['id'], 'name':document['name'], 'sha256':document['sha256'],
            'row_count':len(rows), 'committees':committees,
            'cycles':sorted({row['cycle'] for row in rows if row['cycle']}, reverse=True),
            'supported_rows':sum(row['status'] == 'supported' for row in rows),
            'unsupported_rows':sum(row['status'] != 'supported' for row in rows), 'unassigned_rows':unassigned,
            'session_only':False, 'imported_at':document.get('imported_at', ''),
            'bytes':int(document.get('bytes') or 0), 'warnings':list(WARNINGS) + list(document.get('warnings') or [])}


def select(document, committee='', selected_cycle='', offset=0, limit=200):
    source = catalog(document)
    committee = committee or source['committees'][0]['id']
    chosen = next((row for row in source['committees'] if row['id'] == committee), None)
    if chosen is None:
        raise ValueError(M_COMMITTEE)
    if selected_cycle and selected_cycle not in source['cycles']:
        raise ValueError(M_CYCLE)
    offset, limit = page_args(offset, limit)
    rows = [row for row in document['rows'] if (row['committee_id'] == committee or committee == 'unassigned' and not row['committee_id'])
            and (not selected_cycle or row['cycle'] == selected_cycle)]
    totals = defaultdict(Decimal)
    counts = defaultdict(int)
    for row in rows:
        if row['status'] == 'supported':
            totals[row['channel']] += row['_amount']
            counts[row['channel']] += 1
    return {'source':source, 'committee':chosen, 'committees':source['committees'],
            'cycles':source['cycles'], 'selected_cycle':selected_cycle, 'columns':document['columns'],
            'rows':[{k:v for k,v in row.items() if not k.startswith('_')} for row in rows[offset:offset+limit]],
            'totals':[{'channel':channel, 'amount':float(value), 'row_count':counts[channel]} for channel,value in sorted(totals.items())],
            'supported_rows':sum(row['status'] == 'supported' for row in rows),
            'unsupported_rows':sum(row['status'] != 'supported' for row in rows),
            'offset':offset, 'limit':limit, 'total_rows':len(rows), 'has_more':offset+limit < len(rows),
            'warnings':source['warnings']}
