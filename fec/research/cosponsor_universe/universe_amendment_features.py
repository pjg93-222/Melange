"""Frozen historical amendment sponsorship; research only, no labels or current scores.

BICAM is an incomplete retrospective source. Prior-Congress submissions are
observed legislative activity, not evidence of passage, effectiveness or influence.
"""
from __future__ import annotations

import collections
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re

from universe_relational_features import ROOT, OUT, WINDOWS, load_identities, sha

SOURCE = Path('C:/melange-data/bicam_snapshot/extracted/bicam_amendments')
COUNT_COLUMNS = ['amend_sponsored_count', 'amend_parent_bill_count',
                 'amend_active_day_count', 'amend_active_month_count',
                 'amend_recent365_count', 'amend_prior_service_days']
FEATURES = [name + '_log' for name in COUNT_COLUMNS] + [
    'amend_observed', 'amend_parent_observed', 'amend_missing_parent_observed']
KEY = re.compile(r'^(hamdt|samdt)([1-9][0-9]*)-([1-9][0-9]*)$')
BILL_KEY = re.compile(r'^(hr|s|hjres|sjres|hconres|sconres|hres|sres)([1-9][0-9]*)-([1-9][0-9]*)$')


def records(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        yield from csv.DictReader(stream)


def source_receipt(path):
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size,
                mtime_utc=dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc).isoformat())


def date_for(row):
    """BICAM submitted_at is ISO timestamp, at 04/05 UTC for local calendar date."""
    value = dt.datetime.fromisoformat(row['submitted_at'])
    if value.tzinfo is None or value.utcoffset() != dt.timedelta(0):
        raise ValueError('Missing or non-UTC submitted timestamp')
    # Source sample and full selected scan establish these as midnight EST/EDT.
    # Fail rather than silently resolving an unreviewed timezone boundary.
    if value.hour not in (4, 5) or value.minute or value.second or value.microsecond:
        raise ValueError('Unexpected submitted timestamp hour')
    return value.date().isoformat()


def inside(day, start, cutoff):
    return start <= day < cutoff


def service_days(terms, start, cutoff):
    days = set()
    for term in terms:
        lo, hi = max(start, term['start']), min(cutoff, term['end'])
        if lo >= hi:
            continue
        first, last = dt.date.fromisoformat(lo), dt.date.fromisoformat(hi)
        days.update(first + dt.timedelta(days=i) for i in range((last-first).days))
    return len(days)


def build():
    output = OUT/'amendment_history.csv'
    receipt_path = OUT/'amendment_receipt.json'
    if output.exists() or receipt_path.exists():
        raise RuntimeError('Amendment features already frozen')
    people, _, identity_receipts = load_identities()
    source_paths = [SOURCE/name for name in ['amendments.csv', 'amendments_sponsors.csv',
                                             'amendments_amended_bills.csv']]
    dependency = Path(__file__).with_name('universe_relational_features.py')
    roster_paths = [OUT/f'relational_members_{cg}.csv' for cg in WINDOWS]
    rel_receipt_path = OUT/'relational_receipt.json'
    sources = [source_receipt(p) for p in source_paths+roster_paths+[rel_receipt_path, dependency]]
    sources += [source_receipt(Path(r['path'])) for r in identity_receipts]
    rel_receipt = json.loads(rel_receipt_path.read_text(encoding='utf8'))
    frozen_outputs = {Path(r['path']).name:r['sha256'] for r in rel_receipt['outputs']}
    for path in roster_paths:
        assert sha(path) == frozen_outputs[path.name], 'Historical roster changed'
    sponsors, parents = {}, {}
    validation = collections.Counter()
    for r in records(source_paths[1]):
        key, mid = r['amendment_id'], r['bioguide_id']
        if key.rsplit('-',1)[-1] not in ('116','117'):
            continue
        if key in sponsors:
            raise ValueError('Duplicate or multiple sponsor mapping: '+key)
        if not KEY.fullmatch(key) or not re.fullmatch('[A-Z][0-9]{6}', mid):
            raise ValueError('Malformed amendment/sponsor key')
        sponsors[key] = mid
    for r in records(source_paths[2]):
        key, bill = r['amendment_id'], r['bill_id']
        if key.rsplit('-',1)[-1] not in ('116','117'):
            continue
        if key in parents:
            raise ValueError('Duplicate or multiple parent-bill mapping: '+key)
        if not KEY.fullmatch(key) or not BILL_KEY.fullmatch(bill):
            raise ValueError('Malformed parent bill/amendment key')
        parents[key] = bill
    rows = {cg:[] for cg in WINDOWS}
    seen = set()
    for r in records(source_paths[0]):
        key = r['amendment_id']
        if key in seen:
            raise ValueError('Duplicate amendment ID: '+key)
        seen.add(key)
        if key.rsplit('-',1)[-1] not in ('116','117'):
            continue
        match = KEY.fullmatch(key)
        if not match:
            raise ValueError('Malformed amendment ID: '+key)
        prior = int(match.group(3))
        if prior not in (116, 117):
            continue
        cg = prior+1
        if float(r['congress']) != prior or r['amendment_type'] != match.group(1) or int(r['amendment_number']) != int(match.group(2)):
            raise ValueError('Amendment fields disagree: '+key)
        day = date_for(r)
        validation[f'{cg}_source_submissions'] += 1
        start, cutoff = WINDOWS[cg]
        if not inside(day, start, cutoff):
            validation[f'{cg}_outside_window'] += 1
            continue
        mid = sponsors.get(key)
        if not mid:
            validation[f'{cg}_missing_sponsor'] += 1
            continue
        if mid not in people:
            raise ValueError('Unknown sponsor Bioguide: '+mid)
        chamber = 'House' if match.group(1)=='hamdt' else 'Senate'
        if r['chamber'].casefold() != chamber.casefold():
            raise ValueError('Amendment chamber disagreement')
        terms = [t for t in people[mid]['terms'] if t['start'] <= day < t['end'] and t['chamber']==chamber]
        if not terms:
            raise ValueError('Sponsor not serving in chamber on submitted date: '+key)
        parent = parents.get(key)
        if parent and int(BILL_KEY.fullmatch(parent).group(3)) != prior:
            raise ValueError('Parent bill from different Congress')
        validation[f'{cg}_valid_source_submissions'] += 1
        rows[cg].append(dict(amendment_id=key, member=mid, date=day, parent_bill=parent))
    assert len(seen)==120161, 'Source snapshot row count changed; review required'
    feature_rows, split_receipts = [], {}
    for cg, events in rows.items():
        roster = sorted(r['bioguide'] for r in records(OUT/f'relational_members_{cg}.csv'))
        assert len(roster)==len(set(roster))
        start, cutoff = WINDOWS[cg]
        recent = (dt.date.fromisoformat(cutoff)-dt.timedelta(days=365)).isoformat()
        by_member = collections.defaultdict(list)
        for row in events:
            by_member[row['member']].append(row)
        for mid in roster:
            event = by_member[mid]
            parent_ids = {r['parent_bill'] for r in event if r['parent_bill']}
            raw = dict(amend_sponsored_count=len(event), amend_parent_bill_count=len(parent_ids),
                       amend_active_day_count=len({r['date'] for r in event}),
                       amend_active_month_count=len({r['date'][:7] for r in event}),
                       amend_recent365_count=sum(r['date']>=recent for r in event),
                       amend_prior_service_days=service_days(people[mid]['terms'],start,cutoff))
            feat = {name+'_log':math.log1p(raw[name]) for name in COUNT_COLUMNS}
            feat.update(amend_observed=int(bool(event)), amend_parent_observed=int(bool(parent_ids)),
                        amend_missing_parent_observed=int(any(not r['parent_bill'] for r in event)))
            feature_rows.append(dict(congress=cg,member=mid,**raw,**feat))
        dates = [r['date'] for r in events]
        selected = [r for r in events if r['member'] in set(roster)]
        split_receipts[cg] = dict(prior_congress=cg-1, start_inclusive=start,cutoff_exclusive=cutoff,
                                  source_submissions=validation[f'{cg}_source_submissions'],
                                  missing_sponsor=validation[f'{cg}_missing_sponsor'],
                                  valid_all_historical_submissions=len(events),
                                  target_roster_count=len(roster),target_sponsor_count=len({r['member'] for r in selected}),
                                  target_submissions=len(selected),non_target_submissions=len(events)-len(selected),
                                  missing_parent_events=sum(not r['parent_bill'] for r in events),
                                  min_submitted_date=min(dates),max_submitted_date=max(dates))
    # Independent recount from source eligibility ledger to every emitted raw numeric count.
    for row in feature_rows:
        cg,mid=row['congress'],row['member'];es=[e for e in rows[cg] if e['member']==mid]
        assert row['amend_sponsored_count']==len(es)
        assert row['amend_parent_bill_count']==len(set(e['parent_bill'] for e in es if e['parent_bill']))
        assert row['amend_active_day_count']==len(set(e['date'] for e in es))
        assert row['amend_active_month_count']==len(set(e['date'][:7] for e in es))
        assert all(math.isfinite(row[name]) and row[name]>=0 for name in FEATURES)
        assert row['amend_recent365_count']<=row['amend_sponsored_count']
        assert row['amend_prior_service_days']<=731
        assert row['amend_sponsored_count']==0 or row['amend_prior_service_days']>0
    checks = [inside('2019-01-03',*WINDOWS[117]),not inside('2021-01-03',*WINDOWS[117]),
              not inside('2019-01-02',*WINDOWS[117]),inside('2021-01-03',*WINDOWS[118]),
              not inside('2023-01-03',*WINDOWS[118]),not inside('2021-01-02',*WINDOWS[118])]
    assert all(checks)
    for source in sources:
        assert sha(source['path'])==source['sha256'], 'Input changed during extraction'
    ledger_paths=[]
    for cg in WINDOWS:
        path=OUT/f'amendment_events_{cg}.jsonl'
        if path.exists():raise RuntimeError('Amendment ledger already exists')
        path.write_text(''.join(json.dumps(row,sort_keys=True)+'\n' for row in sorted(rows[cg],key=lambda r:r['amendment_id'])),encoding='utf8')
        ledger_paths.append(path)
    with output.open('w',encoding='utf8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=['congress','member']+COUNT_COLUMNS+FEATURES)
        writer.writeheader();writer.writerows(feature_rows)
    receipt=dict(schema='cosponsor-amendment-history-v1',created_utc=dt.datetime.now(dt.timezone.utc).isoformat(),
                 status='FROZEN_RESEARCH_ONLY',features=FEATURES,raw_count_columns=COUNT_COLUMNS,
                 code_path=str(Path(__file__)),code_sha256=sha(__file__),sources=sources,
                 outputs=[source_receipt(p) for p in [output]+ledger_paths],splits=split_receipts,
                 validation=dict(validation),boundary_checks_passed=len(checks),
                 independent_recount='Every emitted raw count recounted from selected source rows; all identities/chambers/date windows validated; output ledger allows independent recalc.',
                 definitions={'observed':'At least one source-recorded prior-Congress sponsored amendment; zero is not proof of no underlying amendment in incomplete BICAM.',
                              'parent_observed':'At least one valid source-recorded parent bill.',
                              'missing_parent_observed':'At least one sponsored amendment lacks a parent bill mapping in source.',
                              'prior_service_days':'Union of historical House/Senate service dates within prior-Congress window; historical roster from frozen shared-broadcast extraction.',
                              'recent365':'Submission day in the365calendar days strictly before targetCongress cutoff.',
                              'logged_counts':'Natural log1p of raw observed counts/exposure days; no fitted transform.'},
                 exclusions=['No cosponsor table or cosponsor/action count; no final actions/proposed_at/passages/effectiveness/current composites/purpose text.','No119feature rows or labels; no training, model selection or promotion.'],
                 limitations=['Retrospective public-source reconstruction; exact historical first-publication or observation time unavailable.','Public export has incomplete pre119 amendment coverage; arrival run5 found57/65curated historical amendments and93.4%historical amendment text presence. These audits do not independently validate every amendment sponsor.','44prior116and92prior117source records lack sponsor mappings; cannot assign those to a person.','Source has all historical sponsors; target output uses every historical117/118service roster member, not only current survivors.'])
    receipt_path.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'receipt':str(receipt_path),'rows':len(feature_rows),'features':FEATURES,'splits':split_receipts}))


if __name__=='__main__':
    build()
