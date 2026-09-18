"""Where a PAC's money came from and where it went, by congressional district.

S8 of the PAC evidence lane. One route, `/api/evidence-geo`, answers for one
pane: a committee, a cycle and a direction (raised or spent). The geography
itself is district_geo's job (boundaries, the ZIP crosswalk, the FEC candidate
and committee masters); this module decides which rows are which KIND of money
and which basis places each one, then reconciles located plus unlocated back to
the total the committee reported.

Nothing here invents a location. A row the bases cannot place keeps its amount
and joins `unlocated` with the reason, because a map that quietly drops money
is worse than a map with a gap in it (S6_DESIGN, Paul 2026-09-17).

The four spend kinds and their bases, Paul's ruling:
  candidates   Schedule E independent spending and Schedule B line 23 gifts,
               by the candidate's own seat; support and oppose kept apart.
  transfers    Schedule B line 22 to another committee, by that committee's
               registered state IN THAT CYCLE'S master - where the paperwork
               lived, not where the money finally went.
  operating    Schedule B line 21B, by the payee's state (and ZIP when it has
               one that resolves).
  conversions  the in-kind crypto the committee received and liquidated, filed
               as an operating payment back to the contributor. Its own kind,
               always in the total, off the heat by default (ruling 12).
"""
from __future__ import annotations

from collections import defaultdict
from contextlib import closing
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import sqlite3

import district_geo
import evidence_csv
import geocode

# The legend's real stops, in dollars. The client draws a log ramp between
# them; they are published so the page never invents its own scale.
STOPS = (1000, 10000, 100000, 1000000, 10000000)

DISTRICT_KEY = re.compile(r'^[A-Z]{2}-(\d{2}|AL|SEN)$')
STATE_KEY = re.compile(r'^[A-Z]{2}$')
DIRECTIONS = ('raised', 'spent')
SOURCES = ('csv', 'snapshot')
IDENTIFIER = re.compile(r'[a-z0-9][a-z0-9_-]{0,99}')
COMMITTEE = re.compile(r'C\d{8}')
CENT = Decimal('0.01')

# An in-kind asset the committee never converted to cash reads the same on
# both sides of the ledger; the receipt says it arrived, the 21B row says it
# was sold back. Both phrasings appear in the real filings.
CONVERSION_TEXT = re.compile(r'IN[- ]?KIND|NOT LIQUIDATED|NOT LIQ\b')

M_SOURCE = 'Choose an imported file or a saved snapshot.'
M_DIRECTION = 'Choose Raised or Spent.'
M_COMMITTEE = 'Choose a committee in this source.'
M_SNAPSHOT = 'That saved snapshot is unavailable.'
M_CYCLE = 'Choose a cycle this source records.'


def M_BLANK_CYCLE(cycles):
    """Ruling A (Paul, 2026-09-18): "There should be no all cycles" on the map.

    A district map is drawn on ONE Congress's boundaries, so a blank cycle has
    no vintage and would draw an empty country. The refusal names the cycles
    this source actually carries rather than answering with a blank map, and
    choosing one of them is the client's job.
    """
    known = ', '.join(str(value) for value in cycles if str(value or '').strip())
    return ('A map is drawn on one Congress, so it needs one cycle, not all of them. '
            + (f'Choose {known}.' if known else 'This source records no cycle to draw.'))
M_NO_OUTBOUND = ('This import records money this committee RECEIVED, not money it sent, so it '
                 'carries no outbound rows to place on a map. Open a saved FEC snapshot for '
                 'this committee to see where it spent.')

KIND_LABELS = {
    'candidates': ('Candidates', "by the candidate's district"),
    'transfers': ('Transfers to committees', "by the committee's registered state"),
    'operating': ('Operating', "by the payee's state"),
    'conversions': ('Asset conversions', 'in-kind assets liquidated back to the contributor'),
    'contributors': ('Contributors', 'by the contributor ZIP, then the state'),
}
DEFAULT_OFF = frozenset({'conversions'})


def money(value):
    """A Decimal for anything the filings write, and zero for anything else."""
    try:
        result = Decimal(str(value if value not in (None, '') else 0))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal(0)
    return result if result.is_finite() else Decimal(0)


def cash(value):
    return float(money(value).quantize(CENT))


def name_key(value):
    return ' '.join(re.findall(r'[A-Z0-9]+', str(value or '').upper()))


def is_memo(row):
    """Exactly tools/pac_evidence.py's test, so the same rows are excluded."""
    return bool(row.get('memoed_subtotal')) or str(row.get('memo_code') or '').strip().upper() == 'X'


def line_of(row):
    """'21B', '22', '23' - the Schedule B line, punctuation removed."""
    return re.sub(r'[^0-9A-Z]', '', str(row.get('line_number') or '').strip().upper())


def zip5(value):
    digits = re.sub(r'\D', '', str(value or ''))
    return digits[:5] if len(digits) >= 5 else ''


def state_of(value):
    text = str(value or '').strip().upper()
    return text if STATE_KEY.fullmatch(text) else ''


# ---------------------------------------------------------------- the buckets

class Bucket:
    """One kind's districts, states and the rows it could not place.

    `add_district` and `add_state` take an already-decided key; deciding is the
    caller's job, because each kind has its own basis and its own reason for
    failing. Shares are computed at the end, over the kind's own total, so a
    kind that is toggled off never changes another kind's numbers.
    """

    def __init__(self, kind):
        self.kind = kind
        self.districts = defaultdict(lambda: {'amount': Decimal(0), 'rows': 0, 'support': Decimal(0),
                                              'oppose': Decimal(0), 'who': {}, 'split': False,
                                              'bases': set()})
        self.states = defaultdict(lambda: {'amount': Decimal(0), 'rows': 0, 'support': Decimal(0),
                                           'oppose': Decimal(0), 'who': {}, 'split': False,
                                           'bases': set()})

    def _add(self, table, key, amount, rows=1, who='', direction='', split=False, basis=''):
        entry = table[key]
        entry['amount'] += amount
        entry['rows'] += rows
        entry['split'] = entry['split'] or split
        if basis:
            entry['bases'].add(basis)
        if direction == 'support':
            entry['support'] += amount
        elif direction == 'oppose':
            entry['oppose'] += amount
        if who:
            entry['who'][who] = entry['who'].get(who, Decimal(0)) + amount

    def add_district(self, key, amount, **fields):
        self._add(self.districts, key, amount, **fields)

    def add_state(self, key, amount, **fields):
        self._add(self.states, key, amount, **fields)

    def total(self):
        return (sum((entry['amount'] for entry in self.districts.values()), Decimal(0))
                + sum((entry['amount'] for entry in self.states.values()), Decimal(0)))

    def payload(self, basis):
        total = self.total()
        label, basis_note = KIND_LABELS.get(self.kind, (self.kind.title(), basis))
        return {'kind': self.kind, 'label': label, 'total': cash(total),
                'rows': sum(entry['rows'] for entry in list(self.districts.values()) + list(self.states.values())),
                'basis': basis or basis_note, 'default_on': self.kind not in DEFAULT_OFF,
                'districts': _rank(self.districts, total, DISTRICT_KEY),
                'states': _rank(self.states, total, STATE_KEY)}


def basis_of(bases):
    """One word for how a row's district was decided: street, zip or zip_split.

    S8b. '' for a row no contributor basis placed - every SPENT kind, whose
    basis is the candidate's seat or the payee's state and has nothing to do
    with a contributor address. A district reached only by street matches is
    exact, so it carries neither the split mark nor the ZIP caveat.
    """
    if not bases:
        return ''
    if bases == {'street'}:
        return 'street'
    if 'zip_split' in bases:
        return 'zip_split'
    return 'zip'


def _rank(table, total, pattern):
    rows = []
    for key, entry in table.items():
        if not pattern.fullmatch(key):
            # Never silently drop: a key the map cannot draw is still money, and
            # the caller put it here, so it is a bug worth seeing in the list.
            continue
        who = sorted(entry['who'].items(), key=lambda item: (-item[1], item[0]))
        rows.append({'key': key, 'amount': cash(entry['amount']), 'rows': entry['rows'],
                     'basis': basis_of(entry['bases']),
                     'share': float((entry['amount'] / total).quantize(Decimal('0.000001')))
                              if total > 0 else 0.0,
                     'support': cash(entry['support']), 'oppose': cash(entry['oppose']),
                     'split': bool(entry['split']),
                     'who': ', '.join(name for name, _ in who[:3]) + (' and others' if len(who) > 3 else '')})
    return sorted(rows, key=lambda row: (-row['amount'], row['key']))


class Unlocated:
    """Money no basis could place, grouped by the reason it could not."""

    def __init__(self):
        self.rows = defaultdict(lambda: {'amount': Decimal(0), 'rows': 0})

    def add(self, reason, amount, rows=1):
        entry = self.rows[reason]
        entry['amount'] += amount
        entry['rows'] += rows

    def total(self):
        return sum((entry['amount'] for entry in self.rows.values()), Decimal(0))

    def payload(self):
        return sorted(({'reason': reason, 'amount': cash(entry['amount']), 'rows': entry['rows']}
                       for reason, entry in self.rows.items()),
                      key=lambda row: (-abs(row['amount']), row['reason']))


class Mix:
    """How many raised rows each basis placed - S8b's honesty counter.

    The three counts are DISJOINT and add to every row the raised side read:

      geocoded  the address was in the geocode cache and resolved to a seat
      pending   the row has an address this console could geocode, but has not
                yet; it is placed by ZIP today and would sharpen if Start ran
      zip       everything else: no usable address at all, or a cached answer
                the service could not place, or a census tract that straddles
                two districts. Never dropped - S6_DESIGN's rule stands.

    A Spent map reads no contributor address, so its Mix stays all zero and
    the page shows no geocoding line for it.
    """

    def __init__(self):
        self.geocoded = 0
        self.pending = 0
        self.zip = 0

    def street(self, cache, values, cycle, bucket, unlocated, amount, who):
        """Place one raised row by street if the cache can, counting either way.

        True when the row was placed here and the caller must not place it
        again. False leaves the row to the ZIP path, with the count already
        recorded, so no row can be counted twice or not at all.
        """
        parts = geocode.normalise(*geocode.address_of(values))
        if parts is None:
            self.zip += 1
            return False
        if cache is None:
            self.pending += 1
            return False
        row = cache.get(parts[0])
        if row is None:
            self.pending += 1
            return False
        key = geocode.district_of(row, cycle)
        if not key:
            self.zip += 1
            return False
        if place_by_street(bucket, unlocated, amount, key, who=who):
            self.geocoded += 1
            return True
        self.geocoded += 1
        return True

    def payload(self):
        return {'geocoded_rows': self.geocoded, 'zip_rows': self.zip,
                'pending_rows': self.pending}


# ------------------------------------------------------------ shared placing

def place_by_zip(bucket, unlocated, amount, zip_value, state_value, cycle, who='', reason_prefix=''):
    """A contributor's ZIP into districts by share, else the state, else nowhere."""
    digits = zip5(zip_value)
    parts = district_geo.district_for_zip(digits, cycle) if digits else []
    if parts:
        split = len(parts) > 1
        for key, share in parts:
            if not DISTRICT_KEY.fullmatch(key):
                unlocated.add(f'ZIP {digits} is in {key}, which this map has no seat for',
                              amount * money(share))
                continue
            bucket.add_district(key, amount * money(share), rows=1 if key == parts[0][0] else 0,
                                who=who, split=split,
                                basis='zip_split' if split else 'zip')
        return
    state = state_of(state_value)
    if state:
        reason = ('the ZIP was missing or unknown' if not digits or not parts else '')
        bucket.add_state(state, amount, who=who or reason, basis='zip')
        return
    problem = district_geo.last_problem or 'no usable ZIP or state on the row'
    unlocated.add(f'{reason_prefix}{problem}', amount)


def place_by_street(bucket, unlocated, amount, key, who=''):
    """An address the geocoder matched: one district, no share, no caveat.

    S8b's precise layer. The key has already been read off the cache for this
    cycle's boundary vintage, so this function only records it - and refuses a
    key the map has no line for rather than drawing a seat that does not exist.
    """
    if DISTRICT_KEY.fullmatch(str(key or '')):
        bucket.add_district(key, amount, who=who, basis='street')
        return True
    unlocated.add(f'a geocoded address resolved to {key!r}, which this map has no seat for', amount)
    return False


def place_by_state(bucket, unlocated, amount, zip_value, state_value, cycle, who='',
                   reason_prefix=''):
    """A payee's STATE, recovering it from the ZIP when the column is blank.

    Transfers, operating payments and asset conversions heat the whole state
    (S6_DESIGN): the payee's street address says where a vendor banks, not
    which electorate the money was aimed at, so colouring a district by it
    would claim more than the filing supports. The ZIP is still read, but only
    to recover a state the filer left blank.
    """
    state = state_of(state_value)
    if not state:
        digits = zip5(zip_value)
        parts = district_geo.district_for_zip(digits, cycle) if digits else []
        state = parts[0][0][:2] if parts else ''
    if state and state_exists(state, cycle):
        bucket.add_state(state, amount, who=who)
        return
    if state:
        unlocated.add(f'{state} is not a state this map draws', amount)
        return
    unlocated.add(f'{reason_prefix}the row carries no usable state or ZIP', amount)


def state_exists(state, cycle):
    payload = district_geo.load_vintage(cycle)
    return bool(payload) and state in (payload.get('states') or {})


def place_candidate(bucket, unlocated, amount, candidate_id, cycle, who='', direction=''):
    """A candidate's own seat; a seat this map has no line for stays unlocated.

    A Senate race has no district of its own: its key is '<ST>-SEN' and the
    client heats the whole state, so it is kept as a district row (that is what
    the ranked list reads as 'CA, Senate') and only its state has to exist.
    """
    key = district_geo.district_for_candidate(candidate_id, cycle)
    senate = bool(key) and key.endswith('-' + district_geo.OFFICE_SENATE)
    drawable = (state_exists(key[:2], cycle) if senate
                else bool(key) and district_geo.district_exists(key, cycle))
    if key and DISTRICT_KEY.fullmatch(key) and drawable:
        bucket.add_district(key, amount, who=who, direction=direction)
        return
    if key == district_geo.OFFICE_PRESIDENT:
        unlocated.add('presidential race: national, with no district or state of its own', amount)
        return
    if key:
        unlocated.add(f'{candidate_id} is filed in {key}, a seat this cycle\'s map has no line for',
                      amount)
        return
    unlocated.add(district_geo.last_problem
                  or f'{candidate_id or "an unnamed candidate"} is in no FEC candidate master', amount)


# -------------------------------------------------------------- the snapshots

def snapshot_units(root, identifier):
    directory = Path(root) / identifier
    try:
        payload = json.loads((directory / 'snapshots.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise ValueError(M_SNAPSHOT) from error
    if not isinstance(payload, list) or not payload:
        raise ValueError(M_SNAPSHOT)
    try:
        evidence = json.loads((directory / 'evidence.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        evidence = {}
    return payload, evidence


def company_keys(evidence):
    """The snapshot's own contributor company and its aliases, as name keys."""
    names = [evidence.get('company') or '', *(evidence.get('aliases') or [])]
    return {name_key(name) for name in names if name_key(name)}


def snapshot_unit(units, committee, cycle):
    year = district_geo.normalise_cycle(cycle)
    for unit in units:
        if str(unit.get('committee_id') or '').upper() != committee:
            continue
        if year is None or district_geo.normalise_cycle(unit.get('cycle')) == year:
            return unit
    raise ValueError(M_CYCLE if any(str(unit.get('committee_id') or '').upper() == committee
                                    for unit in units) else M_COMMITTEE)


def snapshot_spent(unit, evidence, cycle):
    """All disbursements, in four kinds, reconciled to the reported total."""
    buckets = {name: Bucket(name) for name in ('candidates', 'transfers', 'operating', 'conversions')}
    unlocated = Unlocated()
    aliases = company_keys(evidence)

    for row in unit.get('expenditures') or []:
        if is_memo(row):
            continue
        amount = money(row.get('expenditure_amount'))
        direction = {'S': 'support', 'O': 'oppose'}.get(
            str(row.get('support_oppose_indicator') or '').strip().upper(), '')
        place_candidate(buckets['candidates'], unlocated, amount, row.get('candidate_id'), cycle,
                        who=str(row.get('candidate_name') or row.get('candidate_id') or ''),
                        direction=direction)

    for row in unit.get('disbursements') or []:
        if is_memo(row):
            continue
        amount = money(row.get('disbursement_amount'))
        line = line_of(row)
        recipient = str(row.get('recipient_committee_id') or '').strip().upper()
        name = str(row.get('recipient_name') or row.get('recipient_committee') or '')
        if line in ('22', '23'):
            if not COMMITTEE.fullmatch(recipient):
                unlocated.add(f'a line {line} payment with no recipient committee id', amount)
                continue
            seat = district_geo.district_for_candidate(row.get('candidate_id'), cycle) if row.get('candidate_id') else None
            if seat:
                place_candidate(buckets['candidates'], unlocated, amount, row.get('candidate_id'),
                                cycle, who=name, direction='support')
                continue
            state = district_geo.committee_state(recipient, cycle)
            if state:
                buckets['transfers'].add_state(state, amount, who=name)
            else:
                unlocated.add(district_geo.last_problem
                              or f'{recipient} is in no FEC committee master', amount)
            continue
        if line != '21B':
            unlocated.add(f'Schedule B line {line or "(blank)"} carries no recipient geography', amount)
            continue
        description = str(row.get('disbursement_description') or '')
        conversion = bool(aliases and name_key(name) in aliases and CONVERSION_TEXT.search(description.upper()))
        bucket = buckets['conversions'] if conversion else buckets['operating']
        place_by_state(bucket, unlocated, amount, row.get('recipient_zip'), row.get('recipient_state'),
                       cycle, who=name, reason_prefix='an operating payment could not be placed: ')

    reported = money((unit.get('totals') or {}).get('disbursements'))
    return buckets, unlocated, reported


def snapshot_raised(unit, cycle, cache=None):
    bucket = Bucket('contributors')
    unlocated = Unlocated()
    mix = Mix()
    for row in unit.get('receipts') or []:
        if is_memo(row):
            continue
        amount = money(row.get('contribution_receipt_amount'))
        who = str(row.get('contributor_name') or '')
        # The cache is content-addressed by ADDRESS, so a snapshot receipt is
        # placed by street whenever some import already paid for that lookup.
        if mix.street(cache, row, cycle, bucket, unlocated, amount, who):
            continue
        place_by_zip(bucket, unlocated, amount, row.get('contributor_zip'),
                     row.get('contributor_state'), cycle, who=who,
                     reason_prefix='a receipt could not be placed: ')
    reported = money((unit.get('totals') or {}).get('receipts'))
    return {'contributors': bucket}, unlocated, reported, mix


# ---------------------------------------------------------------- the imports

ZIP_FIELDS = ('contributor_zip', 'zip', 'zip_code', 'contributor_zip_code', 'zip5', 'postal_code')
STATE_FIELDS = ('contributor_state', 'state', 'contributor_st', 'st')


def import_rows(store, identifier, committee, cycle):
    """(headers, columns, [(line_num, cells)]) for one committee's counted rows.

    Only SUPPORTED rows: an excluded row is out of the workbook's own totals
    (S7), so putting it on the map would place money the file says not to count.
    """
    value = store.ready(identifier)
    catalog = evidence_csv.stored_catalog(value)
    committee = committee or (catalog['committees'][0]['id'] if catalog['committees'] else '')
    chosen = next((item for item in catalog['committees'] if item['id'] == committee), None)
    if chosen is None:
        raise ValueError(M_COMMITTEE)
    if cycle and cycle not in catalog['cycles']:
        raise ValueError(M_CYCLE)
    database = store.database_path(identifier)
    if not database.is_file():
        raise ValueError(evidence_csv.M_GONE(identifier))
    stored = '' if committee == 'unassigned' else committee
    where, parameters = 'committee_id = ?', [stored]
    if cycle:
        where, parameters = where + ' AND cycle = ?', parameters + [cycle]
    try:
        with closing(sqlite3.connect(database)) as connection:
            rows = connection.execute(
                f'SELECT line_num, cells FROM csv_rows WHERE {where} AND status = ? ORDER BY row_number',
                parameters + ['supported']).fetchall()
    except sqlite3.Error as error:
        raise ValueError(evidence_csv.M_GONE(identifier)) from error
    headers = value.get('columns', [])
    return catalog, chosen, headers, [evidence_csv.key(item) for item in headers], rows


def import_raised(store, identifier, committee, cycle, cache=None):
    catalog, chosen, headers, columns, rows = import_rows(store, identifier, committee, cycle)
    bucket, unlocated, reported = Bucket('contributors'), Unlocated(), Decimal(0)
    mix = Mix()
    for line_number, cells in rows:
        row = evidence_csv.rebuild(headers, columns, line_number, json.loads(cells))
        values = dict(zip(columns, row['raw'].values()))
        amount = row['_amount'] or Decimal(0)
        reported += amount
        who = row['counterparty'] or evidence_csv.BLANK_COUNTERPARTY
        if mix.street(cache, values, cycle, bucket, unlocated, amount, who):
            continue
        place_by_zip(bucket, unlocated, amount,
                     evidence_csv.first(values, ZIP_FIELDS), evidence_csv.first(values, STATE_FIELDS),
                     cycle, who=who,
                     reason_prefix='a contributor row could not be placed: ')
    return catalog, chosen, {'contributors': bucket}, unlocated, reported, mix


def import_spent(store, identifier, committee, cycle):
    """The workbook's own Downstream Activity sheet, read by Graph's reader.

    The imported cycle sheets are RECEIPT rows: every row's committee id is the
    recipient and every contributor is a person or a company, so a committee is
    never the source there. The same workbook's Downstream Activity sheet is
    the PAC-to-candidate ledger, and graph_data already streams exactly the
    seven columns needed, so it is reused rather than reimplemented. A file
    without that sheet honestly has no outbound rows and says so.
    """
    catalog, chosen, _headers, _columns, _rows = import_rows(store, identifier, committee, cycle)
    committee = chosen['id']
    bucket, unlocated, reported = Bucket('candidates'), Unlocated(), Decimal(0)
    try:
        import graph_data
        source = store.source_path(identifier)
        activity = list(graph_data.activity_xml_rows(str(source), {}))
    except Exception as error:  # a CSV, a workbook without the sheet, a bad zip
        return catalog, chosen, {}, Unlocated(), Decimal(0), f'{M_NO_OUTBOUND} ({error})'
    year = district_geo.normalise_cycle(cycle)
    seen = False
    for row in activity:
        if str(row.get('source_committee_id') or '').strip().upper() != committee:
            continue
        if year is not None and district_geo.normalise_cycle(row.get('cycle')) != year:
            continue
        seen = True
        amount = money(row.get('net_included_amount'))
        reported += amount
        direction = {'support': 'support', 'oppose': 'oppose'}.get(
            str(row.get('support_oppose') or '').strip().lower(), '')
        place_candidate(bucket, unlocated, amount, row.get('candidate_id'), cycle,
                        who=str(row.get('candidate_officeholder') or row.get('candidate_id') or ''),
                        direction=direction)
    if not seen:
        return catalog, chosen, {}, Unlocated(), Decimal(0), M_NO_OUTBOUND
    return catalog, chosen, {'candidates': bucket}, unlocated, reported, ''


# ------------------------------------------------------------------ the route

def source_cycles(source, identifier, committee='', store=None, snapshot_root=None):
    """The concrete cycles this pane's source records, newest first.

    Ruling A's other half: the refusal has to be able to NAME them, and the
    client's newest-cycle fallback reads the same list off the pane.
    """
    years = set()
    if source == 'snapshot':
        units, _evidence = snapshot_units(snapshot_root, identifier)
        for unit in units:
            if committee and str(unit.get('committee_id') or '').upper() != committee:
                continue
            year = district_geo.normalise_cycle(unit.get('cycle'))
            if year:
                years.add(year)
    elif store is not None:
        catalog = evidence_csv.stored_catalog(store.ready(identifier))
        for value in catalog.get('cycles') or []:
            year = district_geo.normalise_cycle(value)
            if year:
                years.add(year)
    return sorted(years, reverse=True)


def geography(source, identifier, committee='', cycle='', direction='spent',
              store=None, snapshot_root=None, data_root=None):
    """The map payload for one pane. Raises ValueError with a reader's message."""
    source = str(source or '').strip().lower()
    direction = str(direction or 'spent').strip().lower()
    committee = str(committee or '').strip().upper()
    cycle = str(cycle or '').strip()
    if source not in SOURCES:
        raise ValueError(M_SOURCE)
    if direction not in DIRECTIONS:
        raise ValueError(M_DIRECTION)
    if not IDENTIFIER.fullmatch(str(identifier or '')):
        raise ValueError(M_SOURCE)
    # RULING A. A blank cycle is refused HERE, before any reading, and the
    # refusal names the cycles this source will accept. It is deliberately not
    # a quiet fallback to the newest cycle: the map would then disagree with
    # the pane that opened it without saying so.
    if not cycle:
        raise ValueError(M_BLANK_CYCLE(source_cycles(source, identifier, committee, store,
                                                     snapshot_root)))

    cache = None
    if data_root is None and store is not None:
        data_root = getattr(store, 'data_root', None)
    if data_root is not None:
        try:
            # create=False: reading a map never writes into the data root, so a
            # read-only preview sharing another console's root stays read-only.
            cache = geocode.Cache(data_root, create=False)
        except (OSError, sqlite3.Error):
            # No cache yet, or one this console cannot open: that costs
            # precision, never a map. Every row stays ZIP-based and is counted.
            cache = None

    reason, label, name = '', '', ''
    mix = Mix()
    if source == 'snapshot':
        if not COMMITTEE.fullmatch(committee):
            raise ValueError(M_COMMITTEE)
        units, evidence = snapshot_units(snapshot_root, identifier)
        unit = snapshot_unit(units, committee, cycle)
        cycle = str(district_geo.normalise_cycle(unit.get('cycle')) or cycle)
        name = next((item.get('committee_name') for item in evidence.get('committee_finances') or []
                     if str(item.get('committee_id') or '').upper() == committee), '') or committee
        label = str(evidence.get('company') or identifier)
        if direction == 'spent':
            buckets, unlocated, reported = snapshot_spent(unit, evidence, cycle)
        else:
            buckets, unlocated, reported, mix = snapshot_raised(unit, cycle, cache)
    else:
        if store is None:
            raise ValueError(M_SOURCE)
        if direction == 'raised':
            catalog, chosen, buckets, unlocated, reported, mix = import_raised(
                store, identifier, committee, cycle, cache)
        else:
            catalog, chosen, buckets, unlocated, reported, reason = import_spent(
                store, identifier, committee, cycle)
        committee, name = chosen['id'], chosen.get('name') or chosen['id']
        label = catalog.get('industry') or catalog.get('name') or identifier

    located = sum((bucket.total() for bucket in buckets.values()), Decimal(0))
    residual = money(reported) - located - unlocated.total()
    if residual.copy_abs() > CENT:
        unlocated.add(_residual_reason(residual), residual)

    vintage = district_geo.vintage_for_cycle(cycle) if cycle else None
    basis = district_geo.zip_basis(cycle) if cycle else None
    index = district_geo.index() or {}
    entry = ((index.get('vintages') or {}).get(vintage) or {}) if vintage else {}
    kinds = [buckets[name_].payload('') for name_ in
             ('candidates', 'transfers', 'operating', 'conversions', 'contributors')
             if name_ in buckets]
    payload = {
        'source': source, 'id': identifier, 'direction': direction, 'cycle': cycle,
        'committee': {'id': committee, 'name': name}, 'label': label,
        'vintage': vintage, 'congress': entry.get('congress') or '',
        'canvas': {'width': index.get('width') or 975, 'height': index.get('height') or 610},
        'boundary_file': entry.get('file') or '',
        'zip_basis': basis['basis'] if basis else '',
        'reported_total': cash(reported), 'located_total': cash(located),
        'unlocated_total': cash(unlocated.total()),
        'reconciles': (money(reported) - located - unlocated.total()).copy_abs() <= CENT,
        'kinds': kinds, 'unlocated': unlocated.payload(), 'stops': list(STOPS),
        'tract_basis': (district_geo.tract_basis(cycle) or {}).get('basis') or '',
        **mix.payload()}
    if reason:
        payload['reason'] = reason
    if not vintage and cycle:
        payload['reason'] = payload.get('reason') or (district_geo.last_problem or '')
    return payload


def _residual_reason(residual):
    if residual > 0:
        return ('the committee reported more than its itemised rows add to '
                '(unitemised and other activity)')
    return ('the itemised rows add to more than the committee reported; '
            'the FEC summary and the schedules disagree')


# ----------------------------------------------------------- contract support

def contract_problems(payload):
    """Every way a payload breaks the evidence-geo contract, as plain sentences.

    Used by the contract test on both the recorded examples and the negative
    controls, and by the real producer output, so an example that drifts from
    what the producer emits fails in the same place a bad payload does.
    """
    problems = []
    if not isinstance(payload, dict):
        return ['the payload is not an object']
    for field in ('direction', 'cycle', 'reported_total', 'located_total',
                  'unlocated_total', 'kinds', 'unlocated', 'stops',
                  'geocoded_rows', 'zip_rows', 'pending_rows'):
        if field not in payload:
            problems.append(f'the payload has no {field}')
    if payload.get('direction') not in DIRECTIONS:
        problems.append('direction must be raised or spent')
    if not str(payload.get('cycle') or '').strip():
        problems.append('a map payload states no cycle; a map is drawn on one Congress')
    for field in ('geocoded_rows', 'zip_rows', 'pending_rows'):
        count = payload.get(field)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            problems.append(f'{field} is not a row count')
    if not isinstance(payload.get('kinds'), list):
        problems.append('kinds must be a list')
        return problems
    located = Decimal(0)
    for kind in payload['kinds']:
        if not isinstance(kind, dict):
            problems.append('a kind is not an object')
            continue
        for field in ('kind', 'label', 'total', 'basis', 'default_on', 'districts', 'states'):
            if field not in kind:
                problems.append(f'kind {kind.get("kind")!r} has no {field}')
        if not kind.get('basis'):
            problems.append(f'kind {kind.get("kind")!r} states no basis')
        entries = list(kind.get('districts') or []) + list(kind.get('states') or [])
        inner = Decimal(0)
        for row in entries:
            if not isinstance(row, dict):
                problems.append(f'kind {kind.get("kind")!r} has a row that is not an object')
                continue
            key = str(row.get('key') or '')
            pattern = DISTRICT_KEY if row in (kind.get('districts') or []) else STATE_KEY
            if pattern is DISTRICT_KEY and not DISTRICT_KEY.fullmatch(key):
                problems.append(f'district key {key!r} is not a district')
            if pattern is STATE_KEY and not STATE_KEY.fullmatch(key):
                problems.append(f'state key {key!r} is not a state')
            share = row.get('share')
            if not isinstance(share, (int, float)) or not 0.0 <= float(share) <= 1.0:
                problems.append(f'share {share!r} on {key} is outside 0..1')
            if row.get('basis') not in ('', 'street', 'zip', 'zip_split'):
                problems.append(f'basis {row.get("basis")!r} on {key} is not a placing basis')
            if row.get('basis') == 'street' and row.get('split'):
                problems.append(f'{key} is street-matched and still marked split')
            inner += money(row.get('amount'))
        if (inner - money(kind.get('total'))).copy_abs() > CENT:
            problems.append(f'kind {kind.get("kind")!r} does not add to its own total')
        located += money(kind.get('total'))
    unlocated = Decimal(0)
    for item in payload.get('unlocated') or []:
        if not isinstance(item, dict) or not item.get('reason'):
            problems.append('an unlocated bucket states no reason')
            continue
        unlocated += money(item.get('amount'))
    if (located - money(payload.get('located_total'))).copy_abs() > CENT:
        problems.append('located_total does not add up from the kinds')
    if (unlocated - money(payload.get('unlocated_total'))).copy_abs() > CENT:
        problems.append('unlocated_total does not add up from the unlocated buckets')
    if (located + unlocated - money(payload.get('reported_total'))).copy_abs() > CENT:
        problems.append('located plus unlocated does not reconcile to the reported total')
    if list(payload.get('stops') or []) != list(STOPS):
        problems.append('the legend stops are not the published stops')
    return problems
