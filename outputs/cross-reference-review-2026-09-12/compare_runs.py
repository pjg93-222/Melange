"""Compare two completed cross-reference ledgers without modifying either.

The only result written is comparison.json. Indexed SQLite streams keep full
source/decision payloads out of memory; review membership uses integer masks.
Amounts ending in _cents are integers, and negative values retain their sign.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack, closing
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import heapq
import itertools
import json
from pathlib import Path
import re
import sqlite3


WORKSPACE = Path(__file__).resolve().parents[2]
OLD_RUN = '20260912T204736-ed3b2a351279'
NEW_RUN = '20260913T025223-09b3c7578492'
COVERAGE_REASONS = {'filing_relationship_evidence_missing', 'latest_filing_completeness_unproven'}


def cents(value):
    amount = Decimal(str(value or 0)) * 100
    if not amount.is_finite() or amount != amount.to_integral_value():
        raise ValueError(f'Expected a finite whole-cent amount: {value!r}')
    return int(amount)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def completed_run(directory):
    report = json.loads((directory / 'report.json').read_text(encoding='utf-8-sig'))
    progress = json.loads((directory / 'progress.json').read_text(encoding='utf-8-sig'))
    if report.get('status') != 'completed' or progress.get('status') != 'completed':
        raise ValueError(f'Run is not complete: {directory.name}')
    if report.get('run_id') != directory.name or progress.get('run_id') != directory.name:
        raise ValueError(f'Run identity mismatch: {directory}')
    path = directory / 'ledger.sqlite'
    if not path.is_file():
        raise ValueError(f'Completed run has no ledger: {directory}')
    return report, path


def readonly(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    return db


def table_exists(db, table):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def task_masks(db, table, reason_bits):
    masks = {}
    if not table_exists(db, table):
        return masks
    for (payload,) in db.execute(f'SELECT payload_json FROM {table}'):
        item = json.loads(payload)
        reason = item['reason']
        bit = reason_bits.setdefault(reason, 1 << len(reason_bits))
        ids = item.get('source_ids') or [item.get('source_id') or item.get('record_id')]
        for sid in ids:
            if sid is not None:
                sid = str(sid)
                masks[sid] = masks.get(sid, 0) | bit
    return masks


def reason_names(mask, reason_bits):
    return [reason for reason, bit in reason_bits.items() if mask & bit]


def accumulate(group, amount=0, old=0, new=0):
    group['records'] += 1
    group['source_positive_cents'] += max(amount, 0)
    group['source_negative_cents'] += min(amount, 0)
    group['before_counted_cents'] += old
    group['after_counted_cents'] += new
    delta = new - old
    group['positive_delta_cents'] += max(delta, 0)
    group['negative_delta_cents'] += min(delta, 0)
    group['net_delta_cents'] += delta


def finalized_groups(groups, key='category'):
    output = []
    for name, values in groups.items():
        item = {key: name, **dict(values)}
        item['source_gross_cents'] = values['source_positive_cents'] + abs(values['source_negative_cents'])
        output.append(item)
    return sorted(output, key=lambda r: (-abs(r['net_delta_cents']), -r['records'], str(r[key])))


def sorted_decisions(db):
    for sid, payload in db.execute('SELECT source_id,payload_json FROM decisions ORDER BY source_id'):
        yield str(sid), json.loads(payload)


def merge_records(old, new):
    left, right = iter(old), iter(new)
    a, b = next(left, None), next(right, None)
    while a is not None or b is not None:
        if b is None or (a is not None and a[0] < b[0]):
            yield a[0], a[1], None
            a = next(left, None)
        elif a is None or b[0] < a[0]:
            yield b[0], None, b[1]
            b = next(right, None)
        else:
            yield a[0], a[1], b[1]
            a, b = next(left, None), next(right, None)


def source_groups(db):
    rows = db.execute('SELECT source_id,source_table,payload_json FROM source_records ORDER BY source_id,source_table,id')
    for sid, records in itertools.groupby(rows, key=lambda row: str(row[0])):
        identities, payload_hashes = [], []
        for _, source_table, payload in records:
            row = json.loads(payload)
            identities.append((str(source_table or ''), str(row.get('company') or ''),
                str(row.get('industry') or ''), str(row.get('cycle') or ''),
                str(row.get('committee_id') or ''), str(row.get('contributor_name') or ''),
                str(row.get('contribution_receipt_date') or '')[:10],
                cents(row.get('contribution_receipt_amount')), int(row.get('current_receipt_cents') or 0)))
            payload_hashes.append(hashlib.sha256(payload.encode()).hexdigest())
        yield sid, (sorted(identities), sorted(payload_hashes))


def compare_sources(old_db, new_db):
    counts = Counter()
    samples = []
    old_hash, new_hash = hashlib.sha256(), hashlib.sha256()
    for sid, old, new in merge_records(source_groups(old_db), source_groups(new_db)):
        counts['source_ids_examined'] += 1
        if old is None or new is None:
            counts['source_id_coverage_mismatches'] += 1
        else:
            counts['old_source_observations'] += len(old[0])
            counts['new_source_observations'] += len(new[0])
            counts['financial_identity_mismatches'] += old[0] != new[0]
            counts['raw_payload_mismatches'] += old[1] != new[1]
        if old is not None:
            old_hash.update((canonical([sid, old[0]]) + '\n').encode())
        if new is not None:
            new_hash.update((canonical([sid, new[0]]) + '\n').encode())
        if old != new and len(samples) < 10:
            samples.append({'source_id': sid, 'old_financial_identity': old[0] if old else None,
                            'new_financial_identity': new[0] if new else None,
                            'raw_payload_identical': bool(old and new and old[1] == new[1])})
    return {**dict(counts), 'same_source_id_coverage': not counts['source_id_coverage_mismatches'],
            'per_record_financial_identity_unchanged': not counts['financial_identity_mismatches'] and not counts['source_id_coverage_mismatches'],
            'raw_observations_identical': not counts['raw_payload_mismatches'] and not counts['source_id_coverage_mismatches'],
            'old_financial_identity_sha256': old_hash.hexdigest(),
            'new_financial_identity_sha256': new_hash.hexdigest(), 'mismatch_examples': samples}


def source_description(db, sid):
    result = db.execute('SELECT payload_json FROM source_records WHERE source_id=? ORDER BY id LIMIT 1', (sid,)).fetchone()
    row = json.loads(result[0]) if result else {}
    remote = db.execute('SELECT payload_json FROM evidence WHERE source_id=?', (sid,)).fetchone()
    if remote:
        row.update({key: value for key, value in json.loads(remote[0]).items() if value is not None})
    url = row.get('pdf_url') or ''
    image = str(row.get('image_number') or '')
    if not url and image.isdigit():
        url = 'https://docquery.fec.gov/cgi-bin/fecimg/?' + image
    if not url:
        url = 'https://www.fec.gov/data/receipts/?data_type=processed&sub_id=' + sid
    return {'source_url': url,
            'contributor_name': row.get('contributor_name'),
            'contributor_employer': row.get('contributor_employer'),
            'receipt_date': str(row.get('contribution_receipt_date') or '')[:10],
            'receipt_type_full': row.get('receipt_type_full') or '',
            'memo_text': row.get('memo_text') or '',
            'filing_form': row.get('filing_form'), 'line_number': row.get('line_number'),
            'company_match_status_as_stored': row.get('company_match_status'),
            'company_match_reason_as_stored': row.get('company_match_reason')}


def keep_top(heap, item, limit=15):
    entry = (abs(item['delta_cents']), item['source_id'], item)
    if len(heap) < limit:
        heapq.heappush(heap, entry)
    elif entry[:2] > heap[0][:2]:
        heapq.heapreplace(heap, entry)


def compare(old_dir, new_dir):
    old_report, old_path = completed_run(old_dir)
    new_report, new_path = completed_run(new_dir)
    rules = json.loads((new_dir / 'rules/inputs/fec_receipt_rules.json').read_text(encoding='utf-8-sig'))
    income_pattern = re.compile(rules['non_giving_exact_pattern'])
    with ExitStack() as stack:
        old_db = stack.enter_context(closing(readonly(old_path)))
        new_db = stack.enter_context(closing(readonly(new_path)))
        reason_bits = {}
        old_reviews = task_masks(old_db, 'review_queue', reason_bits)
        new_reviews = task_masks(new_db, 'review_queue', reason_bits)
        new_coverage = task_masks(new_db, 'coverage_queue', reason_bits)
        print('Review and filing-coverage membership loaded.', flush=True)
        transitions, resolved_partitions, removed_reasons = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
        resolved_prior_reasons, added_reasons = defaultdict(Counter), defaultdict(Counter)
        delta_groups, delta_reason_groups = defaultdict(Counter), defaultdict(Counter)
        attribution_outcomes, attribution_rechecked_outcomes = defaultdict(Counter), defaultdict(Counter)
        totals, mismatches = Counter(), Counter()
        examples, top, employer_top, income_top = [], [], [], []
        seen_old, seen_new = None, None
        for sid, old, new in merge_records(sorted_decisions(old_db), sorted_decisions(new_db)):
            if old is None or new is None:
                mismatches['added_source_ids' if old is None else 'removed_source_ids'] += 1
                if len(examples) < 10:
                    examples.append({'source_id': sid, 'problem': 'decision_source_id_coverage_changed'})
                continue
            if sid == seen_old or sid == seen_new:
                mismatches['duplicate_decision_source_ids'] += 1
            seen_old = seen_new = sid
            totals['matched_records'] += 1
            amount, old_counted, new_counted = old['amount_cents'], old['counted_cents'], new['counted_cents']
            if any(type(value) is not int for value in (amount, old_counted, new_counted, old['baseline_cents'], new['baseline_cents'])):
                raise ValueError(f'Noninteger decision amount: {sid}')
            for field in ('amount_cents', 'baseline_cents', 'company', 'industry', 'cycle'):
                if old.get(field) != new.get(field):
                    mismatches[field + '_mismatches'] += 1
                    if len(examples) < 10:
                        examples.append({'source_id': sid, 'field': field, 'old': old.get(field), 'new': new.get(field)})
            for label, decision in (('before', old), ('after', new)):
                counted = decision['counted_cents']
                totals[label + '_counted_cents'] += counted
                totals[label + '_positive_counted_cents'] += max(counted, 0)
                totals[label + '_negative_counted_cents'] += min(counted, 0)
                totals[label + '_baseline_cents'] += decision['baseline_cents']
                totals[label + '_pac_activity_cents'] += decision.get('pac_activity_cents', 0)
            old_mask, new_mask = old_reviews.get(sid, 0), new_reviews.get(sid, 0)
            before_state, after_state = ('review' if old_mask else 'automatic'), ('review' if new_mask else 'automatic')
            accumulate(transitions[before_state + '_to_' + after_state], amount, old_counted, new_counted)
            if old.get('status') == 'held_for_attribution_review' or old.get('bucket') == 'attribution_unresolved':
                totals['old_attribution_hold_records'] += 1
                totals['old_attribution_holds_now_automatic'] += not bool(new_mask)
                totals['old_attribution_holds_still_in_review'] += bool(new_mask)
                accumulate(attribution_outcomes[after_state + ':' + new['bucket']], amount, old_counted, new_counted)
                if new.get('attribution_resolution'):
                    accumulate(attribution_rechecked_outcomes[after_state + ':' + new['bucket']], amount, old_counted, new_counted)
            old_names = reason_names(old_mask, reason_bits)
            for reason in reason_names(old_mask & ~new_mask, reason_bits):
                accumulate(removed_reasons[reason], amount, old_counted, new_counted)
            for reason in reason_names(new_mask & ~old_mask, reason_bits):
                accumulate(added_reasons[reason], amount, old_counted, new_counted)
            if old_mask and not new_mask:
                if new['bucket'] == 'non_giving':
                    partition = 'explicit_non_giving_receipt_resolved'
                elif new.get('attribution_resolution'):
                    partition = 'exact_employer_alias_recheck'
                elif set(old_names) <= COVERAGE_REASONS:
                    partition = 'filing_coverage_separated_from_receipt_review'
                else:
                    partition = 'other_automatic_resolution'
                accumulate(resolved_partitions[partition], amount, old_counted, new_counted)
                for reason in old_names:
                    accumulate(resolved_prior_reasons[reason], amount, old_counted, new_counted)
            totals['after_coverage_records'] += sid in new_coverage
            totals['after_coverage_only_records'] += sid in new_coverage and not new_mask
            delta = new_counted - old_counted
            totals['positive_delta_cents'] += max(delta, 0)
            totals['negative_delta_cents'] += min(delta, 0)
            totals['net_delta_cents'] += delta
            if not delta:
                continue
            totals['changed_counted_records'] += 1
            description = None
            if new['bucket'] == 'non_giving':
                description = source_description(new_db, sid)
                normalized = [' '.join(re.findall('[A-Z0-9]+', str(description[field]).upper()))
                              for field in ('receipt_type_full', 'memo_text')]
                category = ('explicit_interest_or_investment_income' if any(income_pattern.search(part) for part in normalized)
                            else 'other_explicit_non_giving_receipt')
            elif new.get('attribution_resolution'):
                category = 'exact_employer_alias_recheck'
            else:
                category = 'other_accounting_change'
            accumulate(delta_groups[category], amount, old_counted, new_counted)
            reason_key = '; '.join(sorted(new.get('reasons', [])))
            accumulate(delta_reason_groups[reason_key], amount, old_counted, new_counted)
            item = {'source_id': sid, 'company': new['company'], 'cycle': new['cycle'],
                    'source_amount_cents': amount, 'before_counted_cents': old_counted,
                    'after_counted_cents': new_counted, 'delta_cents': delta, 'category': category,
                    'before_bucket': old['bucket'], 'after_bucket': new['bucket'],
                    'before_review_reasons': sorted(old_names),
                    'after_review_reasons': sorted(reason_names(new_mask, reason_bits)),
                    'after_decision_reasons': new.get('reasons', []),
                    'attribution_resolution': new.get('attribution_resolution')}
            if description:
                item.update(description)
            keep_top(top, item)
            if category == 'exact_employer_alias_recheck':
                keep_top(employer_top, item, 10)
            if category == 'explicit_interest_or_investment_income':
                keep_top(income_top, item, 10)
        print('Decision changes reconciled; checking preserved source observations.', flush=True)
        source_checks = compare_sources(old_db, new_db)
        def enrich(heap):
            result = [item for _, _, item in sorted(heap, key=lambda r: (-r[0], r[1]))]
            for item in result:
                if 'source_url' not in item:
                    item.update(source_description(new_db, item['source_id']))
            return result
        sql_counts = {}
        for label, db in (('before', old_db), ('after', new_db)):
            count, distinct = db.execute('SELECT count(*),count(DISTINCT source_id) FROM decisions').fetchone()
            sql_counts[label] = {'decisions': count, 'distinct_source_ids': distinct}
        checks = {
            'same_decision_source_id_coverage': not (mismatches['added_source_ids'] or mismatches['removed_source_ids']),
            'one_decision_per_source_id': all(v['decisions'] == v['distinct_source_ids'] for v in sql_counts.values()),
            'per_record_source_amount_unchanged': not mismatches['amount_cents_mismatches'],
            'per_record_baseline_unchanged': not mismatches['baseline_cents_mismatches'],
            'per_record_company_cycle_scope_unchanged': not any(mismatches[k + '_mismatches'] for k in ('company', 'industry', 'cycle')),
            'positive_and_negative_changes_reconcile': totals['positive_delta_cents'] + totals['negative_delta_cents'] == totals['net_delta_cents'],
            'net_change_reconciles_totals': totals['before_counted_cents'] + totals['net_delta_cents'] == totals['after_counted_cents'],
            'delta_categories_reconcile': sum(v['net_delta_cents'] for v in delta_groups.values()) == totals['net_delta_cents'],
            'resolved_partition_reconciles': sum(v['records'] for v in resolved_partitions.values()) == transitions['review_to_automatic']['records'],
            'before_review_count_matches_report': len(old_reviews) == old_report['summary']['unresolved_records'],
            'after_review_count_matches_report': len(new_reviews) == new_report['summary']['unresolved_records'],
            'source_observations_preserved': source_checks['raw_observations_identical'],
            'source_financial_identity_preserved': source_checks['per_record_financial_identity_unchanged'],
            'same_source_database_hash': old_report['scope']['database_sha256'] == new_report['scope']['database_sha256'],
        }
        for label, report in (('before', old_report), ('after', new_report)):
            checks[label + '_signed_counted_amounts_reconcile'] = (totals[label + '_positive_counted_cents'] + totals[label + '_negative_counted_cents'] == totals[label + '_counted_cents'])
            checks[label + '_total_matches_stored_report'] = totals[label + '_counted_cents'] == cents(report['summary']['observed_original_giving'])
            checks[label + '_baseline_matches_stored_report'] = totals[label + '_baseline_cents'] == cents(report['summary']['baseline_amount'])
            checks[label + '_record_count_matches_stored_report'] = sql_counts[label]['decisions'] == report['summary']['input_records']
        def percent(numerator, denominator):
            return round(100 * numerator / denominator, 4) if denominator else None
        rates = {
            'old_review_records': len(old_reviews),
            'old_review_now_automatic_records': transitions['review_to_automatic']['records'],
            'old_review_now_automatic_percent': percent(transitions['review_to_automatic']['records'], len(old_reviews)),
            'old_attribution_hold_records': totals['old_attribution_hold_records'],
            'old_attribution_holds_now_automatic_records': totals['old_attribution_holds_now_automatic'],
            'old_attribution_holds_now_automatic_percent': percent(totals['old_attribution_holds_now_automatic'], totals['old_attribution_hold_records']),
            'old_attribution_holds_still_in_review_records': totals['old_attribution_holds_still_in_review'],
            'old_attribution_holds_still_in_review_percent': percent(totals['old_attribution_holds_still_in_review'], totals['old_attribution_hold_records']),
            'automatic_classification_share_before_percent': percent(old_report['summary']['automatic_decisions'], sql_counts['before']['decisions']),
            'automatic_classification_share_after_percent': percent(new_report['summary']['automatic_decisions'], sql_counts['after']['decisions']),
        }
        output = {'schema_version': 1, 'generated_at': datetime.now(timezone.utc).isoformat(),
            'status': 'verified' if all(checks.values()) else 'mismatch_requires_review',
            'before': {'run_id': old_dir.name, 'report_path': str(old_dir / 'report.json'),
                       'ledger_sha256_as_reported': old_report.get('ledger_sha256'), 'summary': old_report['summary'],
                       'unresolved_reasons': old_report.get('unresolved_reasons', [])},
            'after': {'run_id': new_dir.name, 'report_path': str(new_dir / 'report.json'),
                      'ledger_sha256_as_reported': new_report.get('ledger_sha256'), 'summary': new_report['summary'],
                      'unresolved_reasons': new_report.get('unresolved_reasons', []),
                      'coverage_reasons': new_report.get('coverage_reasons', []),
                      'attribution_recheck': new_report.get('attribution_recheck', {})},
            'scope': {'industries': new_report['scope']['industries'], 'companies': new_report['scope']['companies'],
                      'cycles': new_report['scope']['cycles'], 'source_database': new_report['scope']['database'],
                      'accounting_basis': new_report['scope']['accounting_basis']},
            'checks': checks, 'source_observation_checks': source_checks,
            'decision_identity_mismatches': dict(mismatches), 'mismatch_examples': examples,
            'decision_counts': sql_counts, 'cent_totals': dict(totals), 'workflow_rates': rates,
            'row_review_transitions': finalized_groups(transitions, 'transition'),
            'old_attribution_hold_outcomes': finalized_groups(attribution_outcomes, 'after_outcome'),
            'old_attribution_holds_rechecked_by_exact_alias_outcomes': finalized_groups(attribution_rechecked_outcomes, 'after_outcome'),
            'resolved_review_partition': finalized_groups(resolved_partitions),
            'resolved_rows_by_prior_reason_overlapping': finalized_groups(resolved_prior_reasons, 'reason'),
            'removed_review_reason_memberships_overlapping': finalized_groups(removed_reasons, 'reason'),
            'new_review_reason_memberships_overlapping': finalized_groups(added_reasons, 'reason'),
            'giving_deltas_by_mechanism': finalized_groups(delta_groups),
            'giving_deltas_by_new_decision_reasons': finalized_groups(delta_reason_groups, 'reasons'),
            'top_15_giving_changes': enrich(top),
            'top_employer_recheck_changes': enrich(employer_top), 'top_explicit_income_changes': enrich(income_top),
            'interpretation': ['The resolved review partition is disjoint; reason-membership groups overlap and must not be added.',
                'Moving filing coverage into its own queue resolves a row-level workflow demand, not collection completeness.',
                'Giving deltas compare the old and new experimental counted_cents decisions, not edits to the accepted workbook.',
                'Exact-source verification and automatic classification do not certify globally unique giving.',
                'Ledger hashes here are the completed reports\' recorded hashes; this comparison verifies source identities and all signed accounting changes directly.']}
        return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state-root', type=Path, default=WORKSPACE / 'mentat/state/cross-reference')
    parser.add_argument('--old-run', default=OLD_RUN)
    parser.add_argument('--new-run', default=NEW_RUN)
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('comparison.json'))
    args = parser.parse_args()
    result = compare(args.state_root.resolve() / args.old_run, args.state_root.resolve() / args.new_run)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'output': str(args.output.resolve()),
                      'cent_totals': result['cent_totals'], 'checks': result['checks']}), flush=True)
    if result['status'] != 'verified':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
