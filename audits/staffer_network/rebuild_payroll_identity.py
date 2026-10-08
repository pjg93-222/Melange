"""Rebuild source-bound payroll identity evidence for an explicit spine generation.

Derived from the frozen 2026-09-06 builder. Live selectors are never written.
"""
import argparse
import gzip
import itertools
import json
import re
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from fec.surfaces.staffer_identity_auto import normalized, normalized_title
from fec.surfaces.staffer_payroll_identity import VERSION, exclusive, sha_file


# These are funding/program accounts, not uniquely identified employing offices.
ACCOUNT_ONLY = {'TRANSITION AIDES', 'SALARIES OFFICERS AND EMPLOYEES',
                'CARES SUPPLEMENTAL PL 116-136', 'OTHER ADMINISTRATION', 'GOVERNMENT CONTRIBUTIONS'}


def read(path):
    with gzip.open(path, 'rt', encoding='utf-8') as stream:
        yield from map(json.loads, stream)


def money(value):
    # ABSENT/None/empty amounts are a deliberate design skip (see the
    # `if title and amount` / `amount <= 0: continue` gates below) and stay
    # Decimal(0). A NON-EMPTY string that fails to parse is data corruption
    # masquerading as a genuine zero -- that must not be coerced silently.
    if value is None:
        return Decimal(0)
    text = str(value).replace('$', '').replace(',', '').strip()
    if not text:
        return Decimal(0)
    try:
        return Decimal(text)
    except InvalidOperation:
        raise ValueError('unparseable payroll amount: %r' % (value,)) from None


def family(value):
    return re.sub(r'^FISCAL YEAR \d{4}\s+', '', value)


def run(spine, out):
    global SPINE, OUT
    SPINE, OUT = Path(spine).resolve(), Path(out).resolve()
    if OUT.exists():
        raise ValueError('Output generation already exists: ' + str(OUT))
    OUT.mkdir(parents=True)
    started = time.perf_counter()
    receipt_path = SPINE / 'hill_personnel_spine_receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    sources = [{'path': str(receipt_path.relative_to(ROOT)), 'sha256': sha_file(receipt_path)}]
    spans_path = SPINE / 'hill_person_office_spans.ndjson.gz'
    if sha_file(spans_path) != receipt['files'][spans_path.name]['sha256']:
        raise ValueError(
            '%s does not match the sha256 the spine receipt binds for it' % spans_path
        )
    sources.append({'path': str(spans_path.relative_to(ROOT)), 'sha256': sha_file(spans_path)})
    native, metadata, known = {}, {}, {}
    for s in read(spans_path):
        person = 'person:' + s['spine_person_id']
        key = (person, s['chamber'], s['office_key'])
        metadata[key] = s['container_kind']
        if s['container_kind'] != 'unresolved':
            known[s['chamber'], s['office_key']] = 'container:office:' + s['chamber'] + ':' + s['office_key']
        for row in s['source_row_ids']:
            if row in native:
                raise ValueError(
                    'duplicate source_row_id %r across office spans in %s (already bound '
                    'to %r)' % (row, spans_path, native[row])
                )
            native[row] = key
    pieces = defaultdict(list)
    candidates = defaultdict(list)
    counts = Counter()
    for role in ('house_personnel_observations', 'senate_payroll_candidates_1', 'senate_payroll_candidates_2'):
        binding = receipt['inputs'][role]
        path = ROOT / binding['path']
        if sha_file(path) != binding['sha256']:
            raise ValueError(
                '%s does not match the sha256 the spine receipt binds for input %r'
                % (path, role)
            )
        sources.append({'path': binding['path'], 'sha256': binding['sha256']})
        for r in read(path):
            counts['source_rows_read'] += 1
            house = role == 'house_personnel_observations'
            row_id = f"house-ledger:{r.get('source_file')}#{r.get('source_row_index')}" if house else r['candidate_id']
            location = native.get(row_id)
            if location is None:
                counts['rows_not_admitted_by_spine'] += 1
                continue
            person, chamber, office = location
            root = family(office)
            employer = known.get((chamber, office)) or known.get((chamber, root))
            if root in ACCOUNT_ONLY or 'INTERN COMPENSATION' in root:
                employer = None
            title = normalized_title((r.get('title_base') or r.get('title_raw') or '') if house else (r.get('title_candidate') or r.get('title_raw') or ''))
            amount = money(r.get('amount') if house else r.get('amount_paid_raw'))
            if house:
                start, stop = r.get('service_start'), r.get('service_end')
                if not start or not stop or start > stop:
                    counts['invalid_or_absent_service_dates'] += 1
                    continue
                end = exclusive(stop)
                if title and amount:
                    candidates[(normalized(r['payee_raw']), root, title)].append({
                        'person_id': person, 'row_id': row_id, 'payee': r['payee_raw'], 'office': office,
                        'ledger_account': r['office_key'], 'family': r['office_family_normalized'],
                        'title': title, 'start': start, 'end_exclusive': end,
                        'amount': str(amount), 'quarter': r['quarter'], 'source_file': r['source_file'],
                        'source_url': r['source_url'], 'source_sha256': r['source_sha256'],
                        'base_pay': r.get('compensation_class') == 'BASE', 'employer_id': employer})
                date_evidence = 'printed_service_dates'
                if r.get('compensation_class') != 'BASE':
                    continue
            else:
                # Reported compensation does not establish continuous service.
                # Keep each payment window separate; the matcher requires a
                # dated biography to cover this entire window.
                start, stop = r.get('report_period_start'), r.get('report_period_end')
                if not start or not stop or start > stop:
                    counts['invalid_or_absent_service_dates'] += 1
                    continue
                end = exclusive(stop)
                date_evidence = 'presence_within_report'
            if not employer or not title or amount <= 0:
                continue
            pieces[(person, employer, title, date_evidence)].append((start, end, row_id))
        print(role, counts['source_rows_read'], 'rows checked', flush=True)
    del native
    episodes = []
    for (person, employer, title, basis), intervals in sorted(pieces.items()):
        merged = []
        for start, end, row_id in sorted(intervals):
            overlap = merged and ((basis == 'printed_service_dates' and start <= merged[-1][1]) or
                                   (basis == 'presence_within_report' and (start, end) == tuple(merged[-1][:2])))
            if overlap:
                merged[-1][1] = max(merged[-1][1], end)
                merged[-1][2].append(row_id)
            else:
                merged.append([start, end, [row_id]])
        episodes.extend([person, employer, title, start, end, basis, ids] for start, end, ids in merged)
    del pieces
    pairs, rejected = {}, Counter()
    for (payee, account, title), group in candidates.items():
        people = {r['person_id'] for r in group}
        if len(people) < 2:
            continue
        by_person = defaultdict(list)
        for row in group:
            by_person[row['person_id']].append(row)
        for a, b in itertools.combinations(sorted(people), 2):
            for x, y in itertools.product(by_person[a], by_person[b]):
                if x['office'] == y['office'] or max(x['start'], y['start']) >= min(x['end_exclusive'], y['end_exclusive']):
                    continue
                correction = (all(x[k] == y[k] for k in ('payee', 'family', 'title', 'start', 'end_exclusive', 'quarter', 'source_file'))
                              and money(x['amount']) == -money(y['amount']) and money(x['amount']) != 0)
                same_work = (x['base_pay'] and y['base_pay'] and money(x['amount']) > 0 and money(y['amount']) > 0
                             and x['employer_id'] and x['employer_id'] == y['employer_id'] and len(title) >= 8)
                if not (correction or same_work):
                    continue
                lo, hi = max(x['start'], y['start']), min(x['end_exclusive'], y['end_exclusive'])
                if any(z['person_id'] not in (a, b) and max(lo, z['start']) < min(hi, z['end_exclusive']) for z in group):
                    rejected['competing_same_name_account_role'] += 1
                    continue
                method = 'EXACT_PAYROLL_ACCOUNT_CORRECTION' if correction else 'VERIFIED_PAYROLL_ACCOUNT_SERVICE_MATCH'
                candidate = {'node_ids': [a, b], 'method': method, 'records': [x, y],
                             'overlap': [lo, hi], 'payee_key': payee}
                prior = pairs.get((a, b))
                if prior is None or (correction and prior['method'] != method):
                    pairs[a, b] = candidate
    counts.update(episodes=len(episodes), employment_people=len({e[0] for e in episodes}), record_pairs=len(pairs))
    report = {'version': VERSION, 'sources': sources, 'episodes': episodes,
              'record_pairs': list(pairs.values()), 'counts': dict(counts)}
    target = OUT / 'payroll_identity_evidence.json.gz'
    raw = json.dumps(report, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    target.write_bytes(gzip.compress(raw, compresslevel=6, mtime=0))
    summary = {'version': VERSION, 'counts': dict(counts), 'pair_methods': dict(Counter(p['method'] for p in pairs.values())),
               'rejected': dict(rejected), 'path': str(target.relative_to(ROOT)), 'sha256': sha_file(target),
               'bytes': target.stat().st_size, 'elapsed_seconds': round(time.perf_counter() - started, 3)}
    (OUT / 'payroll_build_summary.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spine', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    run(args.spine, args.out)
