"""Read the complete saved committee network, without attributing pooled dollars.

Each committee/cycle is selected once, from its newest complete saved unit.
Traversal is cycle-safe and uncapped; absent destination snapshots are disclosed.
"""
from collections import ChainMap, OrderedDict, defaultdict
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
import hashlib
from pathlib import Path
import threading

import drawer_sidecars

ROOT = Path(__file__).resolve().parents[1] / '.cache/pac-evidence'
NOTE = ('Saved downstream committee network, counted once per committee/cycle. '
        'Includes spending by recipient PACs, not dollars attributed to the starting PAC or its donors. '
        'Coverage is limited to saved evidence; committee coverage windows may differ, and missing destination snapshots remain unresolved.')

def memo(row):
    return str(row.get('memoed_subtotal') or '').strip().upper() in ('1','TRUE') or str(row.get('memo_code') or '').strip().upper() == 'X'


def filing_record(row):
    """Carry the saved transaction's citation into views, without fetching it."""
    image = str(row.get('image_number') or '')
    value = next((row[key] for key in ('contribution_receipt_amount', 'expenditure_amount',
                                      'disbursement_amount', 'amount') if row.get(key) is not None), None)
    return {
        'source_url': row.get('source_url') or row.get('pdf_url') or (
            'https://docquery.fec.gov/cgi-bin/fecimg/?' + image if image.isdigit() else ''),
        'sub_id': str(row.get('sub_id') or ''),
        'transaction_id': str(row.get('transaction_id') or ''),
        'amount': float(amount(value)) if value is not None else None,
        'date': str(row.get('contribution_receipt_date') or row.get('expenditure_date')
                    or row.get('disbursement_date') or row.get('date') or '')[:10],
        'counterparty': row.get('contributor_name') or row.get('candidate_name') or row.get('recipient_name') or '',
        'city': row.get('contributor_city') or '',
        'state': row.get('contributor_state') or '',
        'zip': row.get('contributor_zip') or '',
        'employer': row.get('contributor_employer') or '',
        'purpose': row.get('expenditure_description') or row.get('disbursement_description') or '',
    }

def observations(unit, schedule):
    """One observation per source ID; equal dollars never identify a duplicate.

    Notices are an alternative disclosure, excluded only when explicitly marked.
    Legacy rows without IDs/notice metadata remain provisional observations.
    """
    seen = {}
    for row in unit.get(schedule) or []:
        if not isinstance(row, dict):
            raise ValueError('Invalid saved downstream observation.')
        identifier = str(row.get('sub_id') or '').strip()
        if identifier and identifier in seen:
            if row != seen[identifier]:
                raise ValueError('Conflicting saved downstream facts for one source ID.')
            continue
        if identifier:
            seen[identifier] = row
        if schedule == 'expenditures' and str(row.get('is_notice') or '').strip().lower() in ('true','1'):
            continue
        yield row

def amount(value):
    try:
        result = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Missing or invalid amount in saved downstream evidence; no zero is inferred.') from error
    if not result.is_finite() or result * 100 != (result * 100).to_integral_value():
        raise ValueError('Invalid monetary amount in saved downstream evidence.')
    return result

def inventory(root=None):
    files = sorted(Path(root or ROOT).glob('*/snapshots.json'))
    return _inventory(tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files))


def _inventory(stamps):
    """The saved units _read_inventory returns, as a mapping that reads each unit when it is first
    used (perf.md H8: that read parsed all 312 MB of snapshots, about 1.4 GB of objects at the peak
    and 700 MB kept, for the first drawer of every process, whichever committee it opened).

    The selection is _read_inventory's, made from each file's index (drawer_sidecars): the same
    validation, the same newest-coverage priority, the same order, and each file still hashed in
    full once per process. A unit is its own bytes, hashed against the index and parsed, plus the
    same _source and _sha256. A snapshot set the index cannot describe exactly (a unit that fails
    validation, one committee/cycle twice in one file, anything but plain ASCII JSON) is read by
    _read_inventory itself, which answers or raises exactly as it always has."""
    selection = _selection(stamps)
    if selection is None:
        return _read_inventory(stamps)
    return SavedUnits(stamps, *selection)


class SavedUnits(Mapping):
    """_read_inventory's dict, read lazily. get, [] and `in` read one unit; iterating (dict(...),
    items(), {**...}) reads them all and keeps them for the process, as the old dict was kept."""

    def __init__(self, stamps, entries, kept):
        self._stamps, self._entries, self._kept, self._read, self._whole = stamps, entries, kept, {}, False

    def __getitem__(self, key):
        location = self._entries[key]
        unit = self._read.get(key)
        if unit is None:
            unit = self._kept.get(key)
            if unit is None:
                path, modified, size, offset, length, digest, fingerprint = location
                try:
                    saved = drawer_sidecars.read_unit(path, modified, size, offset, length, digest)
                except ValueError:
                    _forget(self._stamps)
                    raise
                unit = {**saved, '_source': path, '_sha256': fingerprint}
                if self._whole:
                    self._kept[key] = unit
            self._read[key] = unit
        return unit

    def __iter__(self):
        self._whole = True
        return iter(self._entries)

    def __len__(self):
        return len(self._entries)

    def __contains__(self, key):
        return key in self._entries

    def __repr__(self):
        return f'SavedUnits({len(self._entries)} committee/cycles from {len(self._stamps)} snapshots)'


_SELECTIONS = OrderedDict()   # stamps -> (entries, kept) or None; bounded like the old lru_cache(4)
_SELECTION_LIMIT = 4
_selection_guard = threading.Lock()
_selection_locks = {}


def _selection(stamps):
    """(entries, kept) for these stamps, or None when _read_inventory must read them. Single flight:
    one selection per stamps at a time (DE-026: lru_cache is not single-flight)."""
    with _selection_guard:
        if stamps in _SELECTIONS:
            _SELECTIONS.move_to_end(stamps)
            return _SELECTIONS[stamps]
        lock = _selection_locks.setdefault(stamps, threading.Lock())
    with lock:
        with _selection_guard:
            if stamps in _SELECTIONS:
                return _SELECTIONS[stamps]
        try:
            entries = _select(stamps)
        except Exception as error:  # noqa: BLE001
            # A file moved or cannot be read (or the index failed): _read_inventory reads the
            # files and answers or raises exactly as before. Not remembered: the next call retries.
            if not isinstance(error, (OSError, ValueError)):
                drawer_sidecars._emit('mentat.drawer.sidecar', 'failed',
                                      f'Snapshot index skipped: {type(error).__name__}: {error}', stage='inventory')
            with _selection_guard:
                _selection_locks.pop(stamps, None)
            return None
        value = None if entries is None else (entries, {})
        with _selection_guard:
            _SELECTIONS[stamps] = value
            while len(_SELECTIONS) > _SELECTION_LIMIT:
                _SELECTIONS.popitem(last=False)
            _selection_locks.pop(stamps, None)
        return value


def _select(stamps):
    """_read_inventory's selection, from the index of each file: key -> where its unit is. None
    when any unit would fail _read_inventory's checks, or repeats in its file (compared whole
    there); _read_inventory then raises or answers itself."""
    selected = {}
    for path, modified, size in stamps:
        try:
            fingerprint, units = drawer_sidecars.snapshot_index(path, modified, size)
        except drawer_sidecars.Unindexable:
            return None
        keys = set()
        for unit in units:
            kinds = unit['kinds']
            if not all(kinds.get(field) == 'list' for field in ('receipts','disbursements','expenditures')):
                return None
            totals = unit.get('totals')
            if kinds.get('totals') != 'dict' or not totals or not totals['disbursements']:
                return None
            if 'cycle' not in unit or kinds.get('committee_id') != 'str':
                return None
            key = (str(unit['cycle']), unit['committee_id'])
            if key in keys:
                return None
            keys.add(key)
            priority = (str(totals['coverage_end_date'] or ''), modified, path)
            if key not in selected or priority > selected[key][0]:
                selected[key] = (priority, (path, modified, size, unit['offset'], unit['length'],
                                            unit['sha256'], fingerprint))
    return {key: value[1] for key, value in selected.items()}


def _forget(stamps):
    with _selection_guard:
        _SELECTIONS.pop(stamps, None)


def cache_clear():
    """Forget every selection, kept unit and snapshot index this process holds."""
    with _selection_guard:
        _SELECTIONS.clear()
    _read_inventory.cache_clear()
    drawer_sidecars.forget()


def index_inventory(root=None):
    """Build or verify the snapshot indexes the drawer reads, without reading a unit (for the
    prewarm harness). Returns {'files', 'indexed', 'units'}."""
    files = sorted(Path(root or ROOT).glob('*/snapshots.json'))
    stamps = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in files)
    selection = _selection(stamps)
    return {'files': len(stamps), 'indexed': selection is not None,
            'units': len(selection[0]) if selection is not None else None}


@lru_cache(maxsize=4)
def _read_inventory(stamps):
    selected = {}
    for path, modified, size in stamps:
        raw = Path(path).read_bytes()
        units = json.loads(raw)
        fingerprint = hashlib.sha256(raw).hexdigest()
        if not isinstance(units, list):
            raise ValueError('Saved downstream snapshot must contain committee units.')
        file_units = {}
        for unit in units:
            if not all(isinstance(unit.get(field), list) for field in ('receipts','disbursements','expenditures')):
                raise ValueError('Saved downstream unit is missing a complete schedule array.')
            if not isinstance(unit.get('totals'), dict) or 'disbursements' not in unit['totals']:
                raise ValueError('Saved downstream unit is missing its reported disbursements.')
            key = (str(unit['cycle']), unit['committee_id'])
            if key in file_units and file_units[key] != unit:
                raise ValueError('Conflicting committee/cycle units inside one saved snapshot.')
            file_units[key] = unit
            priority = (str((unit.get('totals') or {}).get('coverage_end_date') or ''), modified, path)
            if key not in selected or priority > selected[key][0]:
                selected[key] = (priority, {**unit, '_source': path, '_sha256':fingerprint})
        current = Path(path).stat()
        if (current.st_mtime_ns, current.st_size) != (modified, size):
            raise ValueError('Saved downstream evidence changed during the read. Refresh.')
    return {key: value[1] for key, value in selected.items()}

def transfers(unit):
    for row in observations(unit, 'disbursements'):
        destination = str(row.get('recipient_committee_id') or '')
        if not memo(row) and str(row.get('line_number')) in ('22', '23') and destination:
            yield destination, amount(row.get('disbursement_amount')), row

def network(roots, units=None, report_edges=()):
    units = inventory() if units is None else units
    visited, missing, edges = set(), set(), []
    pending = list(roots)
    fallback = defaultdict(dict)
    for edge in report_edges:
        key = (str(edge['cycle']), edge['source'])
        destination = edge['destination']
        value = amount(edge['amount'])
        previous = fallback[key].get(destination)
        if previous is not None and previous != value:
            raise ValueError('Saved reports disagree on a downstream transfer; select one report vintage.')
        fallback[key][destination] = value
    while pending:
        key = pending.pop()
        if key in visited:
            continue
        visited.add(key)
        unit = units.get(key)
        if unit is None:
            missing.add(key)
        destinations = defaultdict(Decimal)
        candidate_destinations = defaultdict(Decimal)
        for destination, value, row in transfers(unit or {}):
            if row.get('candidate_id'):
                candidate_destinations[destination] += value
            else:
                destinations[destination] += value
        if unit is None:
            destinations.update(fallback[key])
        for destination, value in destinations.items():
            if value <= 0:
                continue
            target = (key[0], destination)
            edges.append({'cycle':key[0], 'source':key[1], 'destination':destination, 'amount':float(value)})
            pending.append(target)
        for destination, value in candidate_destinations.items():
            if value > 0:
                edges.append({'cycle':key[0], 'source':key[1], 'destination':destination,
                              'amount':float(value), 'terminal_candidate':True})
    return {'keys':visited, 'units':{key:units[key] for key in visited if key in units},
            'missing':sorted(missing), 'edges':edges, 'note':NOTE}

def activity(network):
    grouped, labels = defaultdict(Decimal), {}
    filings = defaultdict(list)
    # A Schedule B candidate payment's FEC code (disbursement_type: 24K, 24Z,
    # ...) is kept beside the recorded 'Contribution / Other' amount, so a
    # reader can split that one bucket by code (graph_data.activity_sides:
    # Paul, 2026-09-23, "It should be two separate segments"). The grouping
    # and every existing field are unchanged.
    parts = defaultdict(lambda: defaultdict(lambda: [Decimal(0), []]))
    for (year, committee), unit in network['units'].items():
        for row in observations(unit, 'expenditures'):
            if memo(row):
                continue
            candidate = str(row.get('candidate_id') or '')
            direction = {'S':'Support', 'O':'Oppose'}.get(row.get('support_oppose_indicator'), 'Unknown')
            key = (year, committee, candidate, direction)
            grouped[key] += amount(row.get('expenditure_amount'))
            filings[key].append(filing_record(row))
            labels[key] = str(row.get('candidate_name') or candidate or 'Unidentified candidate')
        for row in observations(unit, 'disbursements'):
            if memo(row) or str(row.get('line_number')) not in ('22','23') or not row.get('candidate_id'):
                continue
            key = (year,committee,str(row['candidate_id']),'Contribution / Other')
            value, record = amount(row.get('disbursement_amount')), filing_record(row)
            grouped[key] += value
            filings[key].append(record)
            part = parts[key][str(row.get('disbursement_type') or '').strip().upper()]
            part[0] += value
            part[1].append(record)
            labels[key] = str(row.get('candidate_name') or row.get('recipient_name') or row['candidate_id'])
    return [{'cycle':k[0], 'committee':k[1], 'candidate_id':k[2], 'direction':k[3],
             'candidate':labels[k], 'party':'', 'amount':value, 'filings':filings[k],
             **({'transaction_parts':{code:{'amount':total, 'filings':records}
                                      for code,(total,records) in parts[k].items()}} if k in parts else {}),
             'source':network['units'][k[:2]]['_source']} for k,value in grouped.items()]

def merge_activity(rows, roots, units=None, report_edges=()):
    found = network(roots, units, report_edges)
    saved = activity(found)
    # Select whole schedule partitions, never a candidate-by-candidate hybrid
    # that retains a gift deleted by an amendment. Different source totals are
    # disclosed, not treated as proof that either source is wrong. This is a
    # saved-snapshot measurement, not an update to the workbook or its ledger.
    comparisons = []
    def partition(row):
        return (row['cycle'],row['committee'],
                'contributions' if row['direction'] == 'Contribution / Other' else 'independent_expenditures')
    old, new = defaultdict(Decimal), defaultdict(Decimal)
    old_details, new_details = defaultdict(lambda:defaultdict(Decimal)), defaultdict(lambda:defaultdict(Decimal))
    rows = [row for row in rows if (row['cycle'], row['committee']) in found['keys']]
    for row in rows:
        old[partition(row)] += row['amount']
        old_details[partition(row)][row['candidate_id'],row['direction']] += row['amount']
    for row in saved:
        new[partition(row)] += row['amount']
        new_details[partition(row)][row['candidate_id'],row['direction']] += row['amount']
    for key in sorted(set(old) | set(new)):
        if key[:2] in found['units'] and dict(old_details[key]) != dict(new_details[key]):
            comparisons.append({'cycle':key[0], 'committee':key[1], 'schedule':key[2],
                                'workbook_amount':float(old[key]) if key in old else None,
                                'snapshot_amount':float(new[key]),
                                'basis':'Different saved sources; coverage/filing changes are not reconciled.'})
    found['measurement_comparisons'] = comparisons
    result = [r for r in rows if (r['cycle'],r['committee']) in found['keys']
              and (r['cycle'],r['committee']) not in found['units']]
    parties = defaultdict(set)
    for row in rows:
        if row.get('party'):
            parties[row['cycle'],row['candidate_id']].add(row['party'])
    result.extend({**r,'party':' / '.join(sorted(parties[r['cycle'],r['candidate_id']]))} for r in saved)
    return result, found


def sources(found):
    return [{'cycle':key[0], 'committee':key[1], 'source':unit['_source'],
             'sha256':unit.get('_sha256',''),
             'coverage_start':unit['totals'].get('coverage_start_date'),
             'coverage_end':unit['totals'].get('coverage_end_date')}
            for key,unit in sorted(found['units'].items())]


def snapshot_view(identifier, committee, cycle='', root=None):
    """The selected snapshot owns the root; saved recipient PACs supply onward activity."""
    import re
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,99}', identifier):
        raise ValueError('Invalid evidence snapshot.')
    root = Path(root or ROOT)
    path = root / identifier / 'snapshots.json'
    raw = path.read_bytes()
    fingerprint = hashlib.sha256(raw).hexdigest()
    selected = {(str(u['cycle']), u['committee_id']):
                {**u, '_source':str(path), '_sha256':fingerprint}
                for u in json.loads(raw) if u['committee_id'] == committee
                and (not cycle or str(u['cycle']) == str(cycle))}
    if not selected:
        raise ValueError('This committee/cycle is not in the selected snapshot.')
    # The selected units first, then the saved inventory: {**inventory(root), **selected} read
    # lazily, so only the committees the traversal reaches are read.
    units = ChainMap(selected, inventory(root))
    found = network(selected, units)
    rows = relationships(activity(found), selected, found)
    names = {key[1]: next(((r.get('committee') or {}).get('name')
                          for r in unit.get('receipts') or []
                          if (r.get('committee') or {}).get('name')), key[1])
             for key, unit in found['units'].items()}
    for row in rows:
        row['route_names'] = [names.get(c, c) for c in row['route']]
    return {'relationships':rows, 'edges':found['edges'], 'sources':sources(found),
            'missing':[{'cycle':year, 'committee':c} for year,c in found['missing']],
            'note':NOTE}


def relationships(rows, roots, found):
    """Observed ties and concentration, not a claim of candidate control."""
    totals, pairs, labels = defaultdict(Decimal), defaultdict(Decimal), {}
    filings = defaultdict(list)
    paths = {key:[key[1]] for key in roots}
    queue = list(roots)
    outgoing = defaultdict(list)
    for edge in found['edges']:
        if edge.get('terminal_candidate'):
            continue
        outgoing[edge['cycle'],edge['source']].append(edge['destination'])
    for key in queue:
        for destination in outgoing[key]:
            target = (key[0],destination)
            if target not in paths:
                paths[target] = [*paths[key], destination]
                queue.append(target)
    for row in rows:
        source = (row['cycle'],row['committee'],row['direction'])
        totals[source] += row['amount']
        key = (*source,row['candidate_id'])
        pairs[key] += row['amount']
        filings[key].extend(row.get('filings') or [])
        labels[key] = row['candidate']
    result = []
    reversed_sources = {key[:3] for key,value in pairs.items() if value < 0}
    for key, value in pairs.items():
        year, committee, direction, candidate = key
        unit = found['units'].get((year,committee),{})
        name = next(((r.get('committee') or {}).get('name') for r in unit.get('receipts') or []
                     if (r.get('committee') or {}).get('name')), committee)
        result.append({'cycle':year,'committee':committee,'committee_name':name,
                       'candidate_id':candidate,'candidate':labels[key], 'direction':direction,
                       'amount':float(value), 'filings':filings[key],
                       # Signed adjustments can make a "share" misleading or
                       # greater than 100%. Keep amounts visible; suppress only
                       # the percentage when any candidate has a net reversal.
                       'share_of_pac_direction':float(value/totals[key[:3]]) if totals[key[:3]] > 0 and
                           key[:3] not in reversed_sources else None,
                       'route':paths.get((year,committee),[committee]),
                       'basis':'Observed spending; candidate control is not established'})
    return sorted(result,key=lambda r:(-r['amount'],r['committee'],r['candidate_id']))
