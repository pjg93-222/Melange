"""Read user-selected CSV evidence without collection, attribution, or file writes."""
from collections import defaultdict
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import math
from pathlib import Path
import re

from cross_reference_data import _source_url

MAX_BYTES = 5_000_000
MAX_ROWS = 50_000
MAX_COLUMNS = 200
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


def parse(name, text):
    if not isinstance(name, str) or not name.strip() or len(name) > 250 or Path(name).suffix.lower() != '.csv':
        raise ValueError('Choose a CSV file with a name ending in .csv.')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('The CSV file is empty.')
    if '\x00' in text or '\ufffd' in text:
        raise ValueError('Use a UTF-8 CSV file without invalid text characters.')
    encoded = text.encode('utf-8')
    if len(encoded) > MAX_BYTES:
        raise ValueError('Choose a CSV file smaller than 5 MB.')
    content = text.lstrip('\ufeff')
    try:
        try:
            dialect = csv.Sniffer().sniff(content[:32768], delimiters=',;\t')
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(content, newline=''), dialect=dialect, strict=True)
        headers = next(reader, [])
        columns = [key(value) for value in headers]
        if not headers or len(headers) > MAX_COLUMNS or not all(columns) or len(set(columns)) != len(columns):
            raise ValueError('The CSV needs unique nonempty column names, with no more than 200 columns.')
        if not set(columns).intersection(COMMITTEE_FIELDS):
            raise ValueError('The CSV needs a Committee ID, CMTE_ID, or Source Committee ID column.')
        rows = []
        for values in reader:
            if not any(value.strip() for value in values):
                continue
            if len(rows) >= MAX_ROWS:
                raise ValueError('Choose a CSV containing no more than 50,000 rows.')
            raw = {header:values[index] if index < len(values) else '' for index,header in enumerate(headers)}
            rows.append(normalize(raw, reader.line_num, columns, values[len(headers):]))
    except csv.Error as error:
        raise ValueError('The CSV could not be read. Check its quoted fields and delimiter.') from error
    names = defaultdict(set)
    for row in rows:
        if row['committee_id']:
            names[row['committee_id']].add(row['committee_name'] or row['committee_id'])
    if not names:
        raise ValueError('The CSV has no rows with one valid FEC committee ID (C followed by eight digits).')
    return {'name':Path(name).name, 'sha256':hashlib.sha256(encoded).hexdigest(),
            'text':text, 'columns':headers, 'rows':rows, 'committee_names':dict(names)}


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
            'session_only':True, 'warnings':[
                'Imported observations are not verified coverage or donor-attributed PAC spending. Duplicate and amended rows are preserved; totals may overlap.',
                'Committee names and IDs are taken from this CSV; their registration and committee type have not been independently verified.',
                'Cycle aggregates have no inferred transaction date. Missing or ambiguous amounts, dates, or types remain unsupported.',
            ]}


def select(document, committee='', selected_cycle='', offset=0, limit=200):
    source = catalog(document)
    committee = committee or source['committees'][0]['id']
    chosen = next((row for row in source['committees'] if row['id'] == committee), None)
    if chosen is None:
        raise ValueError('Choose a committee in this imported CSV.')
    if selected_cycle and selected_cycle not in source['cycles']:
        raise ValueError('Choose a cycle recorded in this CSV.')
    if isinstance(offset, bool) or isinstance(limit, bool) or not 0 <= offset <= MAX_ROWS or not 1 <= limit <= 1000:
        raise ValueError('Choose a valid CSV row page (1–1,000 rows).')
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
