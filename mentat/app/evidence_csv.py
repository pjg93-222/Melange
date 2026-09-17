"""Read user-selected CSV evidence into a data-root store; no collection or attribution.

The store lives under the console data root, so an import survives a restart, a
stale-build relaunch and a launcher port hop: every console started on the same
data root lists the same imports. Nothing here contacts a network service and
nothing is attributed to a donor; the rows are the reader's own file.
"""
from collections import defaultdict
import codecs
from contextlib import closing
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import threading
import time
import uuid

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

COMMITTEE_FIELDS = ('committee_id', 'cmte_id', 'source_committee_id', 'pac_committee_id', 'pac_id', 'recipient_key')
NAME_FIELDS = ('committee_name', 'cmte_nm', 'source_committee_name', 'pac_name', 'recipient_committee')
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
    'contribution_receipt':'receipt', 'disbursement':'disbursement', 'disbursements':'disbursement',
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


_DERIVED = {'M_BYTES':bytes_message, 'M_COLUMNS':columns_message, 'M_ROWS':rows_message}


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
            'max_rows_message':rows_message()}


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
        'counterparty':first(row, ('contributor_name', 'recipient_name', 'candidate_name', 'candidate_officeholder', 'reported_name', 'name')),
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


def job_view(record):
    """The reading/ready/failed record the page polls, without store internals."""
    return {'id':record.get('id', ''), 'name':record.get('name', ''), 'state':record.get('state', 'failed'),
            'bytes':int(record.get('bytes') or 0), 'bytes_read':int(record.get('bytes_read') or 0),
            'rows_read':int(record.get('rows_read') or 0), 'message':record.get('message') or '',
            'started_at':record.get('started_at'), 'finished_at':record.get('finished_at'),
            'catalog':record.get('catalog')}


# One ingest thread per process, registered here so a record that claims to be
# reading can be told apart from one whose reader died with a restart.
_ACTIVE_LOCK = threading.Lock()
_ACTIVE = {}


class Upload:
    """One in-flight file: size-gated, UTF-8 checked and hashed as it arrives."""

    def __init__(self, store, name):
        if not isinstance(name, str) or not name.strip() or len(name) > 250 or Path(name).suffix.lower() != '.csv':
            raise ValueError(M_NAME)
        self.store = store
        self.name = Path(name).name
        self.path = store.incoming / (uuid.uuid4().hex + '.csv')
        self.bytes = 0
        self._handle = self.path.open('wb')
        self._decoder = codecs.getincrementaldecoder('utf-8')()
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
            try:
                text = self._decoder.decode(chunk)
            except UnicodeDecodeError as error:
                raise ValueError(M_UTF8) from error
            if '\x00' in text or '�' in text:
                raise ValueError(M_UTF8)
            if self._blank and text.strip():
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
        try:
            tail = self._decoder.decode(b'', True)
        except UnicodeDecodeError as error:
            self.abort()
            raise ValueError(M_UTF8) from error
        if '\x00' in tail or '�' in tail:
            self.abort()
            raise ValueError(M_UTF8)
        if self._blank and tail.strip():
            self._blank = False
        self._close()
        if self._blank:
            self.abort()
            raise ValueError(M_EMPTY)
        digest = self._digest.hexdigest()
        try:
            return self.store.adopt('csv-' + digest[:32], self.name, self.path, self.bytes, digest)
        except BaseException:
            self.abort()
            raise


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

    def source_path(self, identifier):
        return self.directory(identifier) / 'source.csv'

    def database_path(self, identifier):
        return self.directory(identifier) / 'rows.sqlite'

    def begin_upload(self, name):
        return Upload(self, name)

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
        return [value['catalog'] for value in records]

    def catalog(self, identifier):
        return self.ready(identifier)['catalog']

    def select(self, identifier, committee='', cycle='', offset=0, limit=200):
        value = self.ready(identifier)
        source = value['catalog']
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
                'warnings':list(WARNINGS)}

    def adopt(self, identifier, name, path, size, digest):
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
            os.replace(path, self.source_path(identifier))
            value = {'id':identifier, 'name':name, 'state':'reading', 'bytes':int(size), 'bytes_read':0,
                     'rows_read':0, 'message':'', 'started_at':time.time(), 'finished_at':None,
                     'catalog':None, 'columns':[], 'sha256':digest, 'imported_at':'', 'pid':os.getpid()}
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
            for path in (self.database_path(identifier), self.source_path(identifier)):
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
        source, database = self.source_path(identifier), self.database_path(identifier)
        database.unlink(missing_ok=True)
        with source.open('rb') as raw:
            head = raw.read(32768).decode('utf-8-sig', 'ignore')
        try:
            dialect = csv.Sniffer().sniff(head, delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
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
            with source.open('r', encoding='utf-8-sig', newline='') as handle:
                reader = csv.reader(handle, dialect=dialect, strict=True)
                headers = next(reader, [])
                columns = [key(item) for item in headers]
                if not headers or len(headers) > MAX_COLUMNS or not all(columns) or len(set(columns)) != len(columns):
                    raise ValueError(columns_message())
                if not set(columns).intersection(COMMITTEE_FIELDS):
                    raise ValueError(M_COMMITTEE_COLUMN)
                batch = []
                try:
                    for values in reader:
                        if not any(item.strip() for item in values):
                            continue
                        if rows_read >= MAX_ROWS:
                            raise ValueError(rows_message())
                        line_number = reader.line_num
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
                            value.update(bytes_read=handle.buffer.tell(), rows_read=rows_read)
                            try:
                                atomic_json(self.record_path(identifier), value, attempts=1)
                            except OSError:
                                pass
                except csv.Error as error:
                    raise ValueError(M_READ(reader.line_num)) from error
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
                 'bytes':int(value.get('bytes') or 0), 'warnings':list(WARNINGS)}, headers)

    def sweep(self):
        """Drop abandoned uploads and old failures. Undeletable paths wait a turn."""
        cutoff = time.time() - 3600
        for path in self.incoming.glob('*.csv'):
            try:
                if path.stat().st_mtime < cutoff:
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
                raise ValueError(M_UTF8)
            encoded = text.encode('utf-8')
            for start in range(0, len(encoded), CHUNK_BYTES):
                upload.write(encoded[start:start + CHUNK_BYTES])
        except UnicodeEncodeError as error:
            upload.abort()
            raise ValueError(M_UTF8) from error
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
            'bytes':int(document.get('bytes') or 0), 'warnings':list(WARNINGS)}


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
