"""Read the complete saved committee network, without attributing pooled dollars.

Each committee/cycle is selected once, from its newest complete saved unit.
Traversal is cycle-safe and uncapped; absent destination snapshots are disclosed.
"""
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from functools import lru_cache
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / '.cache/pac-evidence'
NOTE = ('Saved downstream committee network, counted once per committee/cycle. '
        'Includes spending by recipient PACs, not dollars attributed to the starting PAC or its donors. '
        'Coverage is limited to saved evidence; committee coverage windows may differ, and missing destination snapshots remain unresolved.')

def memo(row):
    return str(row.get('memoed_subtotal') or '').strip().upper() in ('1','TRUE') or str(row.get('memo_code') or '').upper() == 'X'

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

@lru_cache(maxsize=4)
def _inventory(stamps):
    selected = {}
    for path, modified, size in stamps:
        raw = Path(path).read_bytes()
        units = json.loads(raw)
        fingerprint = hashlib.sha256(raw).hexdigest()
        if not isinstance(units, list):
            raise ValueError('Saved downstream snapshot must contain committee units.')
        for unit in units:
            if not all(isinstance(unit.get(field), list) for field in ('receipts','disbursements','expenditures')):
                raise ValueError('Saved downstream unit is missing a complete schedule array.')
            if not isinstance(unit.get('totals'), dict) or 'disbursements' not in unit['totals']:
                raise ValueError('Saved downstream unit is missing its reported disbursements.')
            key = (str(unit['cycle']), unit['committee_id'])
            priority = (str((unit.get('totals') or {}).get('coverage_end_date') or ''), modified, path)
            if key not in selected or priority > selected[key][0]:
                selected[key] = (priority, {**unit, '_source': path, '_sha256':fingerprint})
        current = Path(path).stat()
        if (current.st_mtime_ns, current.st_size) != (modified, size):
            raise ValueError('Saved downstream evidence changed during the read. Refresh.')
    return {key: value[1] for key, value in selected.items()}

def transfers(unit):
    for row in unit.get('disbursements') or []:
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
        candidate_destinations = set()
        for destination, value, row in transfers(unit or {}):
            destinations[destination] += value
            if row.get('candidate_id'):
                candidate_destinations.add(destination)
        if unit is None:
            destinations.update(fallback[key])
        for destination, value in destinations.items():
            if value <= 0:
                continue
            target = (key[0], destination)
            edges.append({'cycle':key[0], 'source':key[1], 'destination':destination, 'amount':float(value)})
            if destination not in candidate_destinations:
                pending.append(target)
    return {'keys':visited, 'units':{key:units[key] for key in visited if key in units},
            'missing':sorted(missing), 'edges':edges, 'note':NOTE}

def activity(network):
    grouped, labels = defaultdict(Decimal), {}
    for (year, committee), unit in network['units'].items():
        for row in unit.get('expenditures') or []:
            if memo(row):
                continue
            candidate = str(row.get('candidate_id') or '')
            direction = {'S':'Support', 'O':'Oppose'}.get(row.get('support_oppose_indicator'), 'Unknown')
            key = (year, committee, candidate, direction)
            grouped[key] += amount(row.get('expenditure_amount'))
            labels[key] = str(row.get('candidate_name') or candidate or 'Unidentified candidate')
        for destination, value, row in transfers(unit):
            if not row.get('candidate_id'):
                continue
            key = (year,committee,str(row['candidate_id']),'Contribution / Other')
            grouped[key] += value
            labels[key] = str(row.get('candidate_name') or row.get('recipient_name') or row['candidate_id'])
    return [{'cycle':k[0], 'committee':k[1], 'candidate_id':k[2], 'direction':k[3],
             'candidate':labels[k], 'party':'', 'amount':value,
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
    for row in rows:
        old[partition(row)] += row['amount']
        old_details[partition(row)][row['candidate_id'],row['direction']] += row['amount']
    for row in saved:
        new[partition(row)] += row['amount']
        new_details[partition(row)][row['candidate_id'],row['direction']] += row['amount']
    for key, value in sorted(old.items()):
        if key[:2] in found['units'] and dict(old_details[key]) != dict(new_details[key]):
            comparisons.append({'cycle':key[0], 'committee':key[1], 'schedule':key[2],
                                'workbook_amount':float(value), 'snapshot_amount':float(new[key]),
                                'basis':'Different saved sources; coverage/filing changes are not reconciled.'})
    found['measurement_comparisons'] = comparisons
    result = [r for r in rows if (r['cycle'],r['committee']) in found['keys']
              and (r['cycle'],r['committee']) not in found['units']]
    parties = {(r['cycle'],r['candidate_id']):r.get('party','') for r in rows if r.get('party')}
    result.extend({**r,'party':parties.get((r['cycle'],r['candidate_id']),'')} for r in saved)
    return result, found


def sources(found):
    return [{'cycle':key[0], 'committee':key[1], 'source':unit['_source'],
             'sha256':unit.get('_sha256',''),
             'coverage_start':unit['totals'].get('coverage_start_date'),
             'coverage_end':unit['totals'].get('coverage_end_date')}
            for key,unit in sorted(found['units'].items())]


def relationships(rows, roots, found):
    """Observed ties and concentration, not a claim of candidate control."""
    totals, pairs, labels = defaultdict(Decimal), defaultdict(Decimal), {}
    paths = {key:[key[1]] for key in roots}
    queue = list(roots)
    outgoing = defaultdict(list)
    for edge in found['edges']:
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
                       'amount':float(value),
                       # Signed adjustments can make a "share" misleading or
                       # greater than 100%. Keep amounts visible; suppress only
                       # the percentage when any candidate has a net reversal.
                       'share_of_pac_direction':float(value/totals[key[:3]]) if totals[key[:3]] > 0 and
                           key[:3] not in reversed_sources else None,
                       'route':paths.get((year,committee),[committee]),
                       'basis':'Observed spending; candidate control is not established'})
    return sorted(result,key=lambda r:(-r['amount'],r['committee'],r['candidate_id']))
