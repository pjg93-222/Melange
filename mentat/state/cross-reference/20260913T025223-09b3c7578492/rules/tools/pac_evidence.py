"""Collect dated, source-linked PAC legs; never label pooled money as traced dollars.

Reads the encrypted FEC key store. Cache receipts include the public query and
response hash, never credentials. New output directories force a fresh snapshot.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
import time
from functools import lru_cache
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fec_key_store import load_keys
from fec_transfer_graph import atomic_json


def money(value):
    return Decimal(str(value or 0))


def name_key(value):
    return ' '.join(re.findall(r'[A-Z0-9]+', str(value or '').upper()))


@lru_cache(maxsize=1)
def receipt_rules():
    return json.loads((Path(__file__).resolve().parents[1]/'inputs/fec_receipt_rules.json').read_text())


def is_memo(row):
    return str(row.get('memo_code') or '').strip().upper() == 'X' or any(
        str(row.get(k) or '').strip().upper() in ('TRUE','1') for k in ('memoed_subtotal','is_memo_leg'))


def receipt_role(row):
    rules = receipt_rules()
    receipt_description = name_key(str(row.get('receipt_type_full') or ''))
    memo_description = name_key(str(row.get('memo_text') or ''))
    description = (receipt_description + ' ' + memo_description).strip()
    memo = is_memo(row)
    if re.search(rules['sale_identity_pattern'],description) and re.search(rules['sale_event_pattern'],description):
        return 'asset_liquidation'
    form = str(row.get('filing_form') or '').strip().upper()
    line = re.sub(r'^SA','',re.sub(r'[() ]','',str(row.get('line_number') or '').strip().upper()))
    role = next((role for role,lines in rules['forms'].get(form,{}).items() if line in lines),'unverified_receipt_role')
    special = form == 'F3X' and line == '17' and re.search(rules['special_account_pattern'], description)
    exact_non_giving = (re.search(rules['non_giving_exact_pattern'], receipt_description)
                       or re.search(rules['non_giving_exact_pattern'], memo_description))
    non_giving = exact_non_giving or re.search(rules['non_giving_event_pattern'], description)
    # An account label describes where the receipt belongs, not what created
    # it. Explicit interest is still income in a special account. A separate
    # actual contribution description, however, conflicts with that event.
    event_description = ' '.join(re.sub(rules['special_account_pattern'], '', part)
                                 for part in (receipt_description, memo_description)
                                 if not re.search(rules['non_giving_exact_pattern'], part))
    giving_event = re.search(rules['giving_event_pattern'], event_description)
    if special:
        role = ('other_receipt' if exact_non_giving and not giving_event else
                'unverified_other_receipt' if non_giving else 'contribution')
    elif role == 'unverified_other_receipt' and non_giving:
        role = 'unverified_other_receipt' if giving_event else 'other_receipt'
    if memo and re.search(rules['disclosure_pattern'],description) and role != 'other_receipt':
        return 'unverified_disclosure_memo'
    if role == 'contribution' and re.search(rules['refund_review_pattern'], description):
        return 'unverified_refund_adjustment'
    if role == 'contribution' and re.search(r'IN KIND|NOT LIQUIDATED',description):
        return 'in_kind_contribution'
    return role


def source_link(row):
    url = row.get('pdf_url') or ''
    if url.startswith('https://docquery.fec.gov/'):
        return url
    image = str(row.get('image_number') or '')
    return 'https://docquery.fec.gov/cgi-bin/fecimg/?' + image if image.isdigit() else ''


class Client:
    def __init__(self, directory, key=None, transport=None):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.keys = [key] if key else load_keys()
        if not self.keys:
            raise ValueError('No enabled FEC key is saved.')
        self.transport = transport

    def page(self, endpoint, params):
        url = 'https://api.open.fec.gov/v1/' + endpoint + '?' + urlencode(sorted(params.items()), doseq=True)
        path = self.directory / (hashlib.sha256(url.encode()).hexdigest() + '.json')
        if path.exists():
            saved = json.loads(path.read_bytes())
            if saved.get('url') != url or hashlib.sha256(json.dumps(saved['response'], sort_keys=True).encode()).hexdigest() != saved.get('sha256'):
                raise ValueError('FEC evidence cache integrity check failed.')
            return saved['response']
        for attempt in range(4):
            try:
                if self.transport:
                    response = self.transport(endpoint, params)
                else:
                    key_index = (int(hashlib.sha256(url.encode()).hexdigest()[:8], 16) + attempt) % len(self.keys)
                    request = Request(url, headers={'X-Api-Key': self.keys[key_index], 'User-Agent': 'Mentat PAC evidence audit'})
                    with urlopen(request, timeout=60) as stream:
                        response = json.load(stream)
                break
            except HTTPError as error:
                if error.code not in (429, 500, 502, 503, 504) or attempt == 3:
                    raise ValueError(f'FEC evidence request failed: HTTP {error.code}, endpoint {endpoint}') from None
                time.sleep(min(30, 2 ** attempt * 2))
        atomic_json(path, {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                          'sha256': hashlib.sha256(json.dumps(response, sort_keys=True).encode()).hexdigest(), 'response': response})
        return response

    def rows(self, endpoint, params, max_pages=200):
        collected, ids, cursors, cursor = [], set(), set(), {}
        expected = None
        for page in range(1, max_pages + 1):
            data = self.page(endpoint, {**params, 'per_page': 100, **cursor})
            pagination = data.get('pagination', {})
            if pagination.get('is_count_exact') is not True or not isinstance(pagination.get('count'), int):
                raise ValueError('PAC evidence requires an exact FEC result count.')
            count = pagination['count']
            if expected is not None and count != expected:
                raise ValueError('FEC result count changed during collection; use a new snapshot directory.')
            expected = count
            batch = data.get('results', [])
            for row in batch:
                identifier = str(row.get('sub_id') or '')
                if not identifier or identifier in ids:
                    raise ValueError('Missing or duplicate FEC transaction identifier during pagination.')
                ids.add(identifier)
                collected.append(row)
            if len(collected) == count:
                return collected
            next_cursor = pagination.get('last_indexes') or {}
            signature = json.dumps(next_cursor, sort_keys=True)
            if not batch or not next_cursor or signature in cursors or len(collected) > count:
                raise ValueError('Incomplete or repeated FEC pagination; evidence not published.')
            cursors.add(signature)
            cursor = next_cursor
        raise ValueError('FEC evidence page limit reached; evidence not published.')


def collect_committee(client, committee, cycle):
    if not re.fullmatch(r'C\d{8}', committee) or cycle % 2:
        raise ValueError('Use FEC committee IDs and even election cycles.')
    base = {'committee_id': committee, 'two_year_transaction_period': cycle}
    receipts = client.rows('schedules/schedule_a/', base)
    disbursements = client.rows('schedules/schedule_b/', base)
    expenditures = client.rows('schedules/schedule_e/', {'committee_id': committee, 'cycle': cycle, 'is_notice': 'false'})
    if any(row.get('is_notice') is not False for row in expenditures):
        raise ValueError('Regular-report IE snapshot unexpectedly contains notice or unknown report types.')
    totals = client.page(f'committee/{committee}/totals/', {'cycle': cycle, 'per_page': 100})['results']
    if len(totals) != 1:
        raise ValueError('Expected one committee financial summary for this cycle.')
    return {'committee_id': committee, 'cycle': cycle, 'receipts': receipts,
            'disbursements': disbursements, 'expenditures': expenditures, 'totals': totals[0]}


def summarize(snapshots, company, aliases):
    """Observed network context. Candidate spend is never a donor allocation."""
    alias_keys = {name_key(value) for value in [company, *aliases] if name_key(value)}
    if not name_key(company):
        raise ValueError('Provide a nonempty canonical company name.')
    receipts, transfers, activity, finances = [], [], [], []
    for snapshot in snapshots:
        committee, cycle = snapshot['committee_id'], snapshot['cycle']
        total = snapshot['totals']
        actual_ie = sum((money(r.get('expenditure_amount')) for r in snapshot['expenditures']
                         if not r.get('memoed_subtotal') and r.get('memo_code') != 'X'), Decimal(0))
        finances.append({'committee_id': committee, 'cycle': cycle,
                         'committee_name': next(((r.get('committee') or {}).get('name') for r in snapshot['receipts'] if (r.get('committee') or {}).get('name')), committee),
                         'receipts_as_reported': total.get('receipts'), 'disbursements_as_reported': total.get('disbursements'),
                         'ending_cash_as_reported': total.get('last_cash_on_hand_end_period'),
                         'coverage_start': str(total.get('coverage_start_date') or '')[:10],
                         'coverage_end': str(total.get('coverage_end_date') or '')[:10],
                         'regular_ie_total': float(actual_ie),
                         'regular_ie_summary_total': total.get('independent_expenditures'),
                         'regular_ie_reconciles': abs(actual_ie - money(total.get('independent_expenditures'))) <= Decimal('.01'),
                         'url': f'https://www.fec.gov/data/committee/{committee}/?cycle={cycle}'})
        for row in snapshot['receipts']:
            if name_key(row.get('contributor_name')) not in alias_keys:
                continue
            role = receipt_role(row)
            receipts.append({'company': company, 'reported_name': row.get('contributor_name'),
                             'committee_id': committee, 'cycle': cycle, 'sub_id': row['sub_id'],
                             'date': row.get('contribution_receipt_date'), 'amount': row.get('contribution_receipt_amount'),
                             'role': role, 'included_company_contribution': role in ('contribution', 'in_kind_contribution') and not is_memo(row),
                             'description': row.get('receipt_type_full'), 'line_number': row.get('line_number'),
                             'transaction_id': row.get('transaction_id'), 'source_url': source_link(row)})
        for row in snapshot['disbursements']:
            destination = row.get('recipient_committee_id')
            if not destination or row.get('memoed_subtotal') or row.get('memo_code') == 'X':
                continue
            # A committee ID can also identify a vendor/refund recipient. Admit
            # contribution/transfer Schedule B lines, never all committee payees.
            if row.get('line_number') not in ('22', '23'):
                continue
            transfers.append({'cycle': cycle, 'source': committee, 'destination': destination,
                              'destination_name': row.get('recipient_name'), 'date': row.get('disbursement_date'),
                              'amount': row.get('disbursement_amount'), 'sub_id': row['sub_id'], 'source_url': source_link(row)})
        grouped = defaultdict(list)
        for row in snapshot['expenditures']:
            if row.get('memoed_subtotal') or row.get('memo_code') == 'X':
                continue
            grouped[row.get('candidate_id') or '', row.get('candidate_name') or '', row.get('support_oppose_indicator') or ''].append(row)
        for (candidate, reported_name, direction), rows in grouped.items():
            dates = sorted(str(row.get('expenditure_date') or '')[:10] for row in rows)
            activity.append({'cycle': cycle, 'committee_id': committee, 'candidate_id_as_filed': candidate,
                             'candidate_name_as_filed': reported_name, 'direction': {'S': 'Support', 'O': 'Oppose'}.get(direction, 'Unresolved'),
                             'committee_spending': float(sum((money(r.get('expenditure_amount')) for r in rows), Decimal(0))),
                             'first_date': dates[0], 'last_date': dates[-1], 'source_rows': len(rows),
                             'source_urls': sorted({source_link(row) for row in rows}),
                             'company_attributed_amount': None, 'evidence': 'Reported committee activity; donor allocation unidentifiable'})
    return {'version': 1, 'company': company, 'aliases': sorted(alias_keys),
            'method': 'Observed receipt, transfer and regular-report expenditure legs. Pooled funds do not establish donor-to-candidate attribution. No pro-rata dollar estimate is published.',
            'scope': 'Itemized Schedule A/B and regular Schedule E; 24/48-hour notices are excluded to avoid double counting. Financial summary includes unitemized and other activity.',
            'receipts': receipts, 'transfers': transfers, 'candidate_activity': activity, 'committee_finances': finances}


def temporal_routes(evidence, max_hops=3):
    """Reachability under dates, not attribution. No backwards-time edges.

    Do not spend an in-kind asset until a documented liquidation link exists.
    Same-day edges have unknown ordering and are explicitly marked as such.
    Negative flows remain in source evidence and never open a funding route.
    """
    results = []
    outbound = defaultdict(list)
    activity = defaultdict(list)
    for transfer in evidence['transfers']:
        if transfer.get('date') and money(transfer.get('amount')) > 0:
            outbound[transfer['cycle'], transfer['source']].append(transfer)
    for item in evidence['candidate_activity']:
        if money(item['committee_spending']) > 0:
            activity[item['cycle'], item['committee_id']].append(item)
    for receipt in evidence['receipts']:
        if not receipt['included_company_contribution'] or money(receipt.get('amount')) <= 0:
            continue
        initial = {'receipt_sub_id': receipt['sub_id'], 'company': receipt['company'], 'cycle': receipt['cycle'],
                   'receipt_date': receipt.get('date'), 'receipt_amount': receipt['amount'], 'company_attributed_amount': None}
        if receipt['role'] == 'in_kind_contribution':
            results.append({**initial, 'status': 'asset_liquidation_link_required', 'path': [receipt['committee_id']]})
            continue
        if not receipt.get('date'):
            results.append({**initial, 'status': 'receipt_date_missing', 'path': [receipt['committee_id']]})
            continue
        queue = [(receipt['committee_id'], receipt['date'][:10], [receipt['committee_id']], False)]
        earliest = {}
        emitted = 0
        for committee, available, path, same_day in queue:
            key = (committee, len(path), same_day)
            if earliest.get(key, '9999') <= available:
                continue
            earliest[key] = available
            for item in activity[receipt['cycle'], committee]:
                if not item['last_date'] or item['last_date'] < available:
                    continue
                status = 'dates_allow_possible_route'
                if item['first_date'] < available or same_day or item['first_date'] == available:
                    status = 'date_order_or_partial_period_review'
                results.append({**initial, 'status': status, 'path': path, 'available_no_earlier_than': available,
                                'candidate_id_as_filed': item['candidate_id_as_filed'],
                                'candidate_name_as_filed': item['candidate_name_as_filed'], 'direction': item['direction']})
                emitted += 1
            if len(path) - 1 >= max_hops:
                continue
            for transfer in outbound[receipt['cycle'], committee]:
                day = transfer['date'][:10]
                if day < available or transfer['destination'] in path:
                    continue
                queue.append((transfer['destination'], day, [*path, transfer['destination']], same_day or day == available))
        if not emitted:
            results.append({**initial, 'status': 'no_dated_route_in_observed_scope', 'path': [receipt['committee_id']]})
    return results


def reconcile_candidates(client, evidence):
    ids = sorted({row['candidate_id_as_filed'] for row in evidence['candidate_activity']
                  if re.fullmatch('[HSP][A-Z0-9]{8}', row['candidate_id_as_filed'])})
    def lookup(identifier):
        rows = client.page(f'candidate/{identifier}/', {'per_page': 100}).get('results', [])
        return identifier, rows[0].get('name', '') if len(rows) == 1 else ''
    with ThreadPoolExecutor(max_workers=3) as executor:
        catalog = dict(executor.map(lookup, ids))
    for row in evidence['candidate_activity']:
        official = catalog.get(row['candidate_id_as_filed'], '')
        row['registered_candidate_name'] = official
        row['identity_status'] = ('name_matches_registration' if official and name_key(official) == name_key(row['candidate_name_as_filed'])
                                  else 'name_id_review' if official else 'candidate_registration_unresolved')
        row['candidate_registration_url'] = 'https://www.fec.gov/data/candidate/' + row['candidate_id_as_filed'] + '/'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--committees', required=True, help='Comma-separated FEC IDs; explicitly select the network boundary')
    parser.add_argument('--cycles', default='2024')
    parser.add_argument('--company', required=True)
    parser.add_argument('--aliases', default='', help='Pipe-separated explicit aliases; transaction roles remain separate')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    committees = list(dict.fromkeys(args.committees.split(',')))
    cycles = list(dict.fromkeys(int(value) for value in args.cycles.split(',')))
    if len(committees) * len(cycles) > 30:
        raise ValueError('Collect up to 30 committee/cycle units per evidence snapshot.')
    args.output.mkdir(parents=True, exist_ok=True)
    client = Client(args.output / 'source-cache')
    work = [(committee, cycle) for committee in committees for cycle in cycles]
    with ThreadPoolExecutor(max_workers=3) as executor:
        snapshots = list(executor.map(lambda item: collect_committee(client, *item), work))
    atomic_json(args.output / 'snapshots.json', snapshots)
    result = summarize(snapshots, args.company, args.aliases.split('|'))
    reconcile_candidates(client, result)
    result['temporal_routes'] = temporal_routes(result)
    result['unexpanded_committees'] = sorted({r['destination'] for r in result['transfers']} - set(committees))
    result['retrieved_at'] = datetime.now(timezone.utc).isoformat()
    result['source_snapshot_sha256'] = hashlib.sha256((args.output / 'snapshots.json').read_bytes()).hexdigest()
    atomic_json(args.output / 'evidence.json', result)
    from pac_cash_model import write_estimates
    write_estimates(args.output)
    print(json.dumps({'committees': committees, 'cycles': cycles, 'receipt_legs': len(result['receipts']),
                      'transfer_legs': len(result['transfers']), 'candidate_activity_rows': len(result['candidate_activity']),
                      'all_regular_ie_totals_reconcile': all(r['regular_ie_reconciles'] for r in result['committee_finances'])}))


if __name__ == '__main__':
    main()
