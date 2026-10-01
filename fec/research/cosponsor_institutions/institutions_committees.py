"""Frozen, label-free historical committee evidence for the original full panels.

Only this experiment's committees* outputs are written.  Archived rosters describe
reported assignments, not attendance.  Event-time hearing reconstruction is a
separate sensitivity group and does not claim historical operational availability.
"""
import os
import sys
sys.dont_write_bytecode = True
for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_name] = '2'

import bisect
import collections
import csv
import datetime as dt
import gc
import json
import math
import re
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from institutions_common import OUT, OLD, digest, stamp, write_json

SRC = OUT / 'committees_sources'
BICAM = Path('C:/melange-data/bicam_snapshot/extracted')
LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
START = {117: dt.date(2021, 1, 3).toordinal(), 118: dt.date(2023, 1, 3).toordinal()}
END = {117: START[118], 118: dt.date(2025, 1, 3).toordinal()}
MISSING_DAYS = 3660
FEATURES = [
    'committee_roster_chamber_available',
    'committee_member_roster_observed',
    'committee_roster_age_log1p',
    'committee_member_top_level_roster_count_log1p',
    'committee_member_sub_count_log1p',
    'committee_member_leadership_count_log1p',
    'committee_bill_prior_referred_full_count_log1p',
    'committee_bill_referral_roster_coverage',
    'committee_member_referred_any',
    'committee_member_referred_count_log1p',
    'committee_member_referred_leadership_any',
    'committee_sponsor_member_shared_top_level_count_log1p',
    'committee_sponsor_member_shared_referred_any',
    'committee_sponsor_roster_observed',
    'committee_event_record_available',
    'committee_bill_past_meeting_count_log1p',
    'committee_bill_past_markup_count_log1p',
    'committee_bill_past_meeting_last90_count_log1p',
    'committee_bill_meeting_recency_log1p',
    'committee_member_past_meeting_committee_any',
    'committee_bill_past_hearing_record_count_log1p',
    'committee_bill_verified_hearing_event_any',
    'committee_bill_verified_hearing_event_count_log1p',
    'committee_bill_verified_hearing_event_last90_count_log1p',
    'committee_bill_verified_hearing_event_recency_log1p',
]
DEFINITIONS = [
    '1 iff the latest strictly earlier same-Congress archived snapshot has any nonempty full-committee roster in the candidate chamber.',
    '1 iff the exact Bioguide has at least one reported assignment in its chamber or a joint committee in that snapshot.',
    'log1p(min(days since snapshot,3660)); log1p(3660) when no usable chamber snapshot exists.',
    'log1p(number of reported top-level four-character source roster groups, including select/joint committees, select subcommittees and task forces represented at the source top level; not a count of standing/full committees).',
    'log1p(number of reported subcommittee assignments in the candidate chamber or joint committees).',
    'log1p(number of reported full/subcommittee assignments whose title contains chair or ranking, including vice/co-chairs).',
    'log1p(number of distinct same-chamber/joint full committees referred the bill strictly before the forecast, from dated BillStatus committee activities).',
    'Fraction of prior full-committee referrals with a nonempty roster in the selected snapshot; zero with no prior referrals.',
    '1 iff candidate has a reported full-committee assignment matching a strictly prior bill referral.',
    'log1p(number of candidate full-committee assignments matching strictly prior bill referrals).',
    '1 iff candidate has a reported leadership title in a full committee matching a strictly prior referral.',
    'log1p(number of top-level source roster groups shared by candidate and bill sponsor in the archived snapshot).',
    '1 iff candidate and sponsor share a reported full committee matching a strictly prior bill referral.',
    '1 iff exact bill sponsor Bioguide has a reported assignment in the bill chamber or a joint committee.',
    '1 iff at least one usable same-Congress meeting record anywhere in this source has both its event day and latest-update day strictly before forecast; does not assert completeness.',
    'log1p(number of distinct linked bill meeting opportunities with event day AND latest-update day strictly earlier; statuses Scheduled only).',
    'log1p(number of those prior linked opportunities with source meeting_type Markup).',
    'log1p(number of those prior linked opportunities with event day in [forecast-90,forecast)).',
    'log1p(days since most recent usable prior linked meeting event); log1p(3660) if none.',
    '1 iff candidate current archived assignment overlaps a committee associated with a usable prior bill meeting; association only, never attendance.',
    'log1p(number of corroborated hearing opportunities with event day AND hearing latest-update day strictly earlier than forecast).',
    'Sensitivity only: 1 iff a BICAM hearing bill/date is corroborated by an exact-date official BillStatus Hearings held action and event day is strictly earlier.',
    'Sensitivity only: log1p(number of corroborated strictly earlier hearing opportunities), without historical publication-availability verification.',
    'Sensitivity only: log1p(number of corroborated hearing opportunities whose event day is in [forecast-90,forecast)).',
    'Sensitivity only: log1p(days since most recent corroborated prior hearing); log1p(3660) if none.',
]


def ordinal(value):
    try:
        return dt.date.fromisoformat(str(value)[:10]).toordinal()
    except (ValueError, TypeError):
        return None


def norm_code(value):
    s = str(value or '').strip().lower()
    if re.fullmatch('[hsj][a-z]{3}', s):
        return s + '00'
    if re.fullmatch('[hsj][a-z]{3}[0-9]{2}', s):
        return s
    return None


def bill_key(value):
    m = re.fullmatch(r'([a-z]+)(\d+)-(\d+)', value or '')
    return f'{m[3]}:{m[1]}:{int(m[2])}' if m else None


def full_code(code):
    return code[:4] + '00'


def rows(path, audit, quarantine=None):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.reader(handle)
        header = next(reader)
        for number, values in enumerate(reader, 2):
            audit[str(path.name) + ':records'] += 1
            if len(values) != len(header):
                audit[str(path.name) + ':malformed'] += 1
                if quarantine is not None:
                    quarantine.append({'file': str(path), 'record_number': number,
                                       'expected_fields': len(header), 'fields': values})
                continue
            yield dict(zip(header, values))


def read_bills(ids):
    requested = set(ids['bills'])
    result = {}
    for line in (OLD / 'bills.jsonl').open(encoding='utf-8'):
        b = json.loads(line)
        if b['key'] not in requested or b['congress'] not in START:
            continue
        # Deliberate projection: no cosponsor, outcome, vote or future-feature fields.
        result[b['key']] = {
            'key': b['key'], 'congress': int(b['congress']),
            'introduced_day': ordinal(b['introduced']),
            'chamber': b['chamber'].lower(), 'sponsor': b['sponsor'],
            'referrals': [a for a in b.get('committees', []) if 'referred' in a.get('activity', '').lower()],
            'hearing_actions': [(ordinal(a.get('date')), a.get('text', '')) for a in b.get('actions', [])
                                if re.search(r'hearings?\s+held', a.get('text', ''), re.I)],
        }
    return result


def build_rosters(ids, known_codes, audit):
    commits = json.loads((SRC / 'github_membership_commits_2021_2024_page1.json').read_text(encoding='utf-8'))
    member_map = {v: i for i, v in enumerate(ids['members'])}
    snapshots = {117: [], 118: []}
    manifest, ledger = [], []
    for api_index, c in enumerate(commits):
        date = max(c['commit']['author']['date'], c['commit']['committer']['date'])
        day = ordinal(date)
        cg = 117 if ordinal('2021-01-01') <= day < START[118] else 118 if START[118] <= day < END[118] else None
        if cg is None:
            continue
        path = SRC / f"membership_{c['sha']}.yaml"
        raw = yaml.load(path.read_text(encoding='utf-8'), Loader=LOADER) or {}
        definitions_path = SRC / f"definitions_{c['sha']}.yaml"
        definitions = yaml.load(definitions_path.read_text(encoding='utf-8'), Loader=LOADER)
        snapshot_codes = set()
        code_names = {}
        for definition in definitions:
            parent_code = norm_code(definition.get('thomas_id'))
            if parent_code:
                snapshot_codes.add(parent_code)
                code_names[parent_code] = definition.get('name', '')
                for child in definition.get('subcommittees', []):
                    child_id = child.get('thomas_id')
                    code = norm_code(parent_code[:4] + str(child_id).zfill(2)) if child_id is not None else None
                    if code:
                        snapshot_codes.add(code)
                        code_names[code] = child.get('name', '')
        per_member = collections.defaultdict(dict)
        available = set()
        seen = set()
        for raw_code, members in raw.items():
            code = norm_code(raw_code)
            if code not in snapshot_codes:
                audit['roster_code_absent_from_same_snapshot_definitions_rows'] += len(members or [])
                continue
            if code not in known_codes:
                audit['roster_valid_historical_code_absent_from_BICAM_dictionary_rows_retained'] += len(members or [])
            if members:
                available.add(code)
            for m in members or []:
                bid = m.get('bioguide')
                if bid not in member_map:
                    audit['roster_assignment_rows_id_outside_original_universe'] += 1
                    continue
                key = (code, bid)
                if key in seen:
                    audit['roster_duplicate_committee_member_rows'] += 1
                    continue
                seen.add(key)
                title = m.get('title') or ''
                lead = bool(re.search(r'chair|ranking', title, re.I))
                per_member[member_map[bid]][code] = lead
                ledger.append({'congress': cg, 'snapshot_sha': c['sha'], 'snapshot_day': day,
                               'bioguide': bid, 'member_index': member_map[bid], 'committee_code': code,
                               'committee_name_in_snapshot': code_names.get(code, ''),
                               'title': title, 'leadership': int(lead), 'source_rank': str(m.get('rank', ''))})
        info = {'sha': c['sha'], 'source_url': f"https://raw.githubusercontent.com/unitedstates/congress-legislators/{c['sha']}/committee-membership-current.yaml",
                'source_path': str(path), 'sha256': digest(path), 'congress': cg,
                'definitions_path': str(definitions_path), 'definitions_sha256': digest(definitions_path),
                'definitions_url': f"https://raw.githubusercontent.com/unitedstates/congress-legislators/{c['sha']}/committees-current.yaml",
                'author_date': c['commit']['author']['date'], 'committer_date': c['commit']['committer']['date'],
                'observation_date_proxy': date, 'observation_day': day, 'message': c['commit']['message'].splitlines()[0],
                'nonempty_valid_committee_rosters': len(available), 'retained_member_assignment_rows': len(seen), 'api_index': api_index}
        manifest.append(info)
        snapshots[cg].append({'day': day, 'api_index': api_index, 'sha': c['sha'],
                              'members': dict(per_member), 'available': available})
    for cg in snapshots:
        # API order is newest first. On equal timestamp days, the newer source state wins.
        snapshots[cg].sort(key=lambda s: (s['day'], -s['api_index']))
    pq.write_table(pa.Table.from_pylist(ledger), OUT / 'committees_roster_ledger.parquet', compression='zstd')
    write_json(OUT / 'committees_roster_snapshots.json', manifest)
    return snapshots


def build_events(bills, known_codes, audit):
    quarantine, ledger, referral_ledger, rejects = [], [], [], []
    meeting_dir, hearing_dir = BICAM / 'bicam_committeemeetings', BICAM / 'bicam_hearings'
    meetings, hearing_records = {}, {}
    for r in rows(meeting_dir / 'committeemeetings.csv', audit, quarantine):
        try:
            cg = int(r['congress'])
        except ValueError:
            audit['meeting_invalid_congress'] += 1
            continue
        if cg not in START:
            continue
        day, update = ordinal(r['date']), ordinal(r['updated_at'])
        reason = None
        if day is None or update is None:
            reason = 'missing_event_or_update_date'
        elif not START[cg] <= day < END[cg]:
            reason = 'event_outside_congress'
        elif r['meeting_status'] != 'Scheduled':
            reason = 'non_scheduled_status_not_backdated'
        elif r['meeting_type'] not in {'Hearing', 'Markup', 'Meeting'}:
            reason = 'unrecognized_meeting_type'
        if reason:
            audit['meeting_reject:' + reason] += 1
            rejects.append({'source': 'meeting', 'source_id': r['meeting_id'], 'reason': reason, 'row': r})
            continue
        if r['meeting_id'] in meetings:
            raise ValueError('Duplicate meeting ID needs adjudication: ' + r['meeting_id'])
        meetings[r['meeting_id']] = {'cg': cg, 'event_day': day, 'record_day': update,
                                      'kind': r['meeting_type'].lower(), 'chamber': r['chamber'].lower(),
                                      'source_id': r['meeting_id'], 'committee_codes': set()}
    for r in rows(meeting_dir / 'committeemeetings_committees.csv', audit):
        event = meetings.get(r['meeting_id'])
        code = norm_code(r['committee_code'])
        if event is not None and code in known_codes:
            event['committee_codes'].add(code)
    meeting_availability = {cg: min((max(m['event_day'], m['record_day']) for m in meetings.values() if m['cg'] == cg), default=10**9) for cg in START}
    for r in rows(meeting_dir / 'committeemeetings_associated_bills.csv', audit):
        key = bill_key(r['bill_id'])
        if key not in bills:
            continue
        m = meetings.get(r['meeting_id'])
        b = bills[key]
        if m is None:
            audit['panel_meeting_link_no_eligible_record'] += 1
            continue
        if m['cg'] != b['congress'] or m['event_day'] < b['introduced_day']:
            audit['panel_meeting_link_wrong_congress_or_before_bill'] += 1
            continue
        ledger.append({'source': 'meeting', 'source_id': m['source_id'], 'bill_key': key,
                       'congress': b['congress'], 'event_day': m['event_day'], 'record_day': m['record_day'],
                       'strict_available_day': max(m['event_day'], m['record_day']), 'kind': m['kind'],
                       'committee_codes': sorted(m['committee_codes']), 'event_corroborated': False,
                       'corroboration': '', 'status': 'Scheduled', 'title_or_attendance_used': False})
    for r in rows(hearing_dir / 'hearings.csv', audit):
        try:
            cg = int(r['congress'])
        except ValueError:
            continue
        if cg in START:
            hearing_records[r['hearing_id']] = {'cg': cg, 'record_day': ordinal(r['updated_at']), 'dates': set(), 'committee_codes': set()}
    for r in rows(hearing_dir / 'hearings_dates.csv', audit):
        h = hearing_records.get(r['hearing_id'])
        if h is None:
            continue
        day = ordinal(r['hearing_date'])
        if day is None or not START[h['cg']] <= day < END[h['cg']]:
            audit['hearing_date_rejected_outside_id_congress'] += 1
            rejects.append({'source': 'hearing', 'source_id': r['hearing_id'], 'reason': 'date_outside_id_congress_jacket_join_risk', 'row': r})
        else:
            h['dates'].add(day)
    for r in rows(hearing_dir / 'hearings_committees.csv', audit):
        h = hearing_records.get(r['hearing_id'])
        code = norm_code(r['committee_code'])
        if h is not None and code in known_codes:
            h['committee_codes'].add(code)
    for r in rows(hearing_dir / 'hearings_bills.csv', audit):
        key = bill_key(r['bill_id'])
        if key not in bills:
            continue
        h = hearing_records.get(r['hearing_id'])
        b = bills[key]
        if h is None or h['cg'] != b['congress'] or not r['hearing_id'].endswith('-' + str(b['congress'])):
            audit['panel_hearing_link_missing_or_wrong_congress'] += 1
            continue
        held = {day: text for day, text in b['hearing_actions'] if day is not None}
        for day in h['dates']:
            reason = ('event_before_bill_introduction' if day < b['introduced_day'] else
                      'no_exact_bill_date_hearings_held_action' if day not in held else
                      'missing_latest_update_date' if h['record_day'] is None else None)
            if reason:
                audit['panel_hearing_reject:' + reason] += 1
                rejects.append({'source': 'hearing', 'source_id': r['hearing_id'], 'bill_key': key,
                                'event_day': day, 'reason': reason})
                continue
            ledger.append({'source': 'hearing', 'source_id': r['hearing_id'], 'bill_key': key,
                           'congress': b['congress'], 'event_day': day, 'record_day': h['record_day'],
                           'strict_available_day': max(day, h['record_day']), 'kind': 'hearing',
                           'committee_codes': sorted(h['committee_codes']), 'event_corroborated': True,
                           'corroboration': held[day], 'status': 'printed_hearing_and_bill_action',
                           'title_or_attendance_used': False})
    grouped = {}
    for e in ledger:
        key = (e['source'], e['bill_key'], e['event_day'], e['kind'], tuple(e['committee_codes']))
        if key not in grouped:
            grouped[key] = dict(e, source_ids=[e['source_id']])
        else:
            audit['event_duplicate_bill_day_kind_committee_set'] += 1
            g = grouped[key]
            g['source_ids'].append(e['source_id'])
            # Use the latest record among duplicated parts, never an earlier part to backdate the final combined record.
            g['record_day'] = max(g['record_day'], e['record_day'])
            g['strict_available_day'] = max(g['event_day'], g['record_day'])
    by_bill = collections.defaultdict(list)
    normalized = []
    for i, e in enumerate(sorted(grouped.values(), key=lambda e: (e['bill_key'], e['event_day'], e['source'], e['source_id']))):
        e['ledger_id'] = i
        e['source_ids'] = sorted(set(e['source_ids']))
        e.pop('source_id')
        normalized.append(e)
        by_bill[e['bill_key']].append(e)
    for b in bills.values():
        valid = set()
        for r in b['referrals']:
            code, day = norm_code(r.get('code')), ordinal(r.get('date'))
            if code not in known_codes or day is None or day < b['introduced_day'] or not START[b['congress']] <= day < END[b['congress']]:
                audit['bill_referral_invalid_code_or_date'] += 1
                continue
            code = full_code(code)
            if code[0] not in {b['chamber'][0], 'j'}:
                audit['bill_referral_other_chamber_omitted'] += 1
                continue
            valid.add((day, code))
        b['referrals'] = sorted(valid)
        for day, code in b['referrals']:
            referral_ledger.append({'bill_key': b['key'], 'congress': b['congress'], 'event_day': day,
                                    'committee_code': code, 'source': 'frozen_BillStatus_committee_activity',
                                    'publication_date_verified': False})
    pq.write_table(pa.Table.from_pylist(normalized), OUT / 'committees_event_ledger.parquet', compression='zstd')
    pq.write_table(pa.Table.from_pylist(referral_ledger), OUT / 'committees_referral_ledger.parquet', compression='zstd')
    with (OUT / 'committees_quarantine.jsonl').open('w', encoding='utf-8') as handle:
        for r in quarantine:
            handle.write(json.dumps(r, ensure_ascii=False) + '\n')
    with (OUT / 'committees_rejected_records.jsonl').open('w', encoding='utf-8') as handle:
        for r in rejects:
            handle.write(json.dumps(r, ensure_ascii=False) + '\n')
    summary = {'accepted_event_ledger_rows': len(normalized), 'referral_rows': len(referral_ledger),
               'quarantined_malformed_rows': len(quarantine), 'rejected_rows_documented': len(rejects),
               'event_source_congress': dict(collections.Counter(f"{e['source']}_{e['congress']}" for e in normalized)),
               'meeting_record_first_usable_day': meeting_availability,
               'source_event_latest_record_days': {f'{source}_{cg}': {
                   'event_min': min((e['event_day'] for e in normalized if e['source'] == source and e['congress'] == cg), default=None),
                   'event_max': max((e['event_day'] for e in normalized if e['source'] == source and e['congress'] == cg), default=None),
                   'record_min': min((e['record_day'] for e in normalized if e['source'] == source and e['congress'] == cg), default=None),
                   'record_max': max((e['record_day'] for e in normalized if e['source'] == source and e['congress'] == cg), default=None)
               } for source in ['meeting', 'hearing'] for cg in START}}
    write_json(OUT / 'committees_event_audit.json', summary)
    return by_bill, meeting_availability, summary


def snapshot_vector(snapshot, chamber, n_members):
    allowed = {chamber[0], 'j'}
    available = set() if snapshot is None else {c for c in snapshot['available'] if c[0] in allowed}
    chamber_available = any(c[0] == chamber[0] and c.endswith('00') for c in available)
    member_sets, member_full, member_lead = [], [], []
    base = np.zeros((n_members, 6), dtype=np.float32)
    for i in range(n_members):
        assignments = {} if snapshot is None else {c: v for c, v in snapshot['members'].get(i, {}).items() if c[0] in allowed}
        codes = set(assignments)
        full = {c for c in codes if c.endswith('00')}
        lead = {c for c, is_lead in assignments.items() if is_lead}
        member_sets.append(codes)
        member_full.append(full)
        member_lead.append(lead)
        base[i] = [chamber_available, bool(codes), 0, math.log1p(len(full)),
                   math.log1p(len(codes - full)), math.log1p(len(lead))]
    return available, member_sets, member_full, member_lead, base


def group_matrix(b, day, snapshot, cache_value, events, meeting_available, sponsor_index, n_members):
    available, all_sets, full_sets, lead_sets, base = cache_value
    out = np.zeros((n_members, len(FEATURES)), dtype=np.float32)
    out[:, :6] = base
    usable = bool(base[0, 0])
    out[:, 2] = math.log1p(min(day - snapshot['day'], MISSING_DAYS)) if snapshot is not None and usable else math.log1p(MISSING_DAYS)
    refs = {code for event_day, code in b['referrals'] if event_day < day}
    out[:, 6] = math.log1p(len(refs))
    out[:, 7] = len(refs & available) / len(refs) if refs else 0
    sponsor = sponsor_index.get(b['sponsor'])
    sponsor_full = full_sets[sponsor] if sponsor is not None else set()
    out[:, 13] = bool(all_sets[sponsor]) if sponsor is not None else False
    past_meetings = [e for e in events if e['source'] == 'meeting' and e['strict_available_day'] < day]
    past_hearings_strict = [e for e in events if e['source'] == 'hearing' and e['strict_available_day'] < day]
    past_hearings_event = [e for e in events if e['source'] == 'hearing' and e['event_day'] < day]
    out[:, 14] = meeting_available < day
    out[:, 15] = math.log1p(len(past_meetings))
    out[:, 16] = math.log1p(sum(e['kind'] == 'markup' for e in past_meetings))
    out[:, 17] = math.log1p(sum(e['event_day'] >= day - 90 for e in past_meetings))
    out[:, 18] = math.log1p(day - max(e['event_day'] for e in past_meetings)) if past_meetings else math.log1p(MISSING_DAYS)
    out[:, 20] = math.log1p(len(past_hearings_strict))
    out[:, 21] = bool(past_hearings_event)
    out[:, 22] = math.log1p(len(past_hearings_event))
    out[:, 23] = math.log1p(sum(e['event_day'] >= day - 90 for e in past_hearings_event))
    out[:, 24] = math.log1p(day - max(e['event_day'] for e in past_hearings_event)) if past_hearings_event else math.log1p(MISSING_DAYS)
    meeting_committees = {c for e in past_meetings for c in e['committee_codes']}
    for i in range(n_members):
        matched = full_sets[i] & refs
        shared = full_sets[i] & sponsor_full
        out[i, 8] = bool(matched)
        out[i, 9] = math.log1p(len(matched))
        out[i, 10] = bool(lead_sets[i] & refs)
        out[i, 11] = math.log1p(len(shared))
        out[i, 12] = bool(shared & refs)
        out[i, 19] = bool(all_sets[i] & meeting_committees)
    return out


def write_panel(cg, ids, bills, snapshots, events, availability):
    meta_path = OLD / f'meta_{cg}.parquet'
    panel = pq.read_table(meta_path, columns=['bill', 'member', 'group', 'day', 'senate']).to_pandas()
    n = len(panel)
    dest = OUT / f'committees_{cg}.f32'
    matrix = np.memmap(dest, dtype=np.float32, mode='w+', shape=(n, len(FEATURES)))
    member_map = {v: i for i, v in enumerate(ids['members'])}
    groups = panel['group'].to_numpy()
    boundaries = np.r_[0, np.flatnonzero(groups[1:] != groups[:-1]) + 1, n]
    if len(np.unique(groups)) != len(boundaries) - 1:
        raise ValueError('Original group rows are not contiguous')
    days = [s['day'] for s in snapshots[cg]]
    cache = {}
    snapshot_counts, source_counts = collections.Counter(), collections.Counter()
    feature_nonzero = np.zeros(len(FEATURES), dtype=np.int64)
    min_values, max_values = np.full(len(FEATURES), np.inf), np.full(len(FEATURES), -np.inf)
    samples = []
    sampled_groups = set(np.linspace(0, len(boundaries) - 2, 60, dtype=int).tolist())
    for gi, (start, stop) in enumerate(zip(boundaries[:-1], boundaries[1:])):
        block = panel.iloc[start:stop]
        bill_index, day, senate = int(block.iloc[0]['bill']), int(block.iloc[0]['day']), int(block.iloc[0]['senate'])
        assert block['bill'].nunique() == block['day'].nunique() == block['senate'].nunique() == 1
        b = bills[ids['bills'][bill_index]]
        assert b['congress'] == cg and (b['chamber'] == 'senate') == bool(senate)
        si = bisect.bisect_left(days, day) - 1
        snapshot = snapshots[cg][si] if si >= 0 else None
        assert snapshot is None or snapshot['day'] < day
        cache_key = (si, b['chamber'])
        if cache_key not in cache:
            cache[cache_key] = snapshot_vector(snapshot, b['chamber'], len(ids['members']))
        computed = group_matrix(b, day, snapshot, cache[cache_key], events.get(b['key'], []), availability[cg], member_map, len(ids['members']))
        members = block['member'].to_numpy(dtype=np.int64)
        values = computed[members]
        matrix[start:stop] = values
        feature_nonzero += np.count_nonzero(values, axis=0)
        min_values = np.minimum(min_values, values.min(axis=0))
        max_values = np.maximum(max_values, values.max(axis=0))
        snapshot_counts[snapshot['sha'] if snapshot else 'missing'] += stop - start
        source_counts['roster_available_rows'] += int(np.count_nonzero(values[:, 0]))
        source_counts['member_roster_observed_rows'] += int(np.count_nonzero(values[:, 1]))
        source_counts['bill_prior_meeting_rows'] += int(np.count_nonzero(values[:, 15]))
        source_counts['bill_prior_hearing_record_rows'] += int(np.count_nonzero(values[:, 20]))
        source_counts['bill_hearing_event_reconstruction_rows'] += int(np.count_nonzero(values[:, 21]))
        if gi in sampled_groups:
            for offset in sorted(set([0, (stop-start)//2, stop-start-1])):
                idx = int(start + offset)
                samples.append({'row': idx, 'congress': cg, 'group': int(groups[idx]), 'bill_key': b['key'],
                                'member': ids['members'][int(members[offset])], 'day': day,
                                'snapshot_sha': snapshot['sha'] if snapshot else None, 'values': values[offset].astype(float).tolist()})
    matrix.flush()
    assert np.isfinite(min_values).all() and np.isfinite(max_values).all()
    del matrix
    write_json(OUT / f'committees_{cg}_alignment_samples.json', samples)
    result = {'congress': cg, 'path': str(dest), 'sha256': digest(dest), 'dtype': 'float32', 'shape': [n, len(FEATURES)],
              'n_features': len(FEATURES), 'panel_rows': n, 'panel_path': str(meta_path), 'panel_sha256': digest(meta_path),
              'panel_columns_read': ['bill', 'member', 'group', 'day', 'senate'], 'group_count': len(boundaries)-1,
              'first_day': int(panel['day'].min()), 'last_day': int(panel['day'].max()),
              'coverage': dict(source_counts), 'snapshot_rows': {k: int(v) for k, v in snapshot_counts.items()},
              'feature_nonzero_rows': dict(zip(FEATURES, map(int, feature_nonzero))),
              'feature_min': dict(zip(FEATURES, map(float, min_values))), 'feature_max': dict(zip(FEATURES, map(float, max_values))),
              'all_values_finite': True, 'original_row_order_preserved': True, 'cohort_filter_applied': False}
    del panel, cache
    gc.collect()
    print(json.dumps({'congress': cg, 'shape': result['shape'], 'coverage': result['coverage']}), flush=True)
    return result


def boundary_checks():
    b = {'sponsor': 'A', 'referrals': [(100, 'hsba00')]}
    s = {'day': 100, 'members': {0: {'hsba00': True}, 1: {'hsba00': False}}, 'available': {'hsba00'}}
    cache = snapshot_vector(s, 'house', 2)
    e = {'source': 'meeting', 'strict_available_day': 101, 'event_day': 99, 'kind': 'markup', 'committee_codes': ['hsba00']}
    h = {'source': 'hearing', 'strict_available_day': 105, 'event_day': 100, 'kind': 'hearing', 'committee_codes': ['hsba00']}
    x = group_matrix(b, 101, s, cache, [e,h], 101, {'A': 0}, 2)
    assert x[1, 8] == 1 and x[1, 15] == 0 and x[1, 14] == 0 and x[1, 20] == 0 and x[1, 21] == 1
    y = group_matrix(b, 102, s, cache, [e,h], 101, {'A': 0}, 2)
    assert y[1, 15] > 0 and y[1, 16] > 0 and y[1, 19] == 1 and y[1, 14] == 1 and y[1, 20] == 0
    z = group_matrix(b, 106, s, cache, [e,h], 101, {'A': 0}, 2)
    assert z[1, 20] > 0
    # Same-day referrals, snapshots and event days are excluded by the respective selectors.
    assert bisect.bisect_left([100, 101], 101) - 1 == 0
    a = group_matrix(b, 100, None, snapshot_vector(None, 'house', 2), [e,h], 101, {'A': 0}, 2)
    assert a[1, 6] == 0 and a[1, 21] == 0 and a[1, 0] == 0
    return {'status': 'PASS', 'checks': ['same_day_snapshot_excluded', 'same_day_referral_excluded', 'same_day_event_excluded',
                                        'same_day_latest_update_excluded', 'future_latest_update_blocks_old_event',
                                        'sensitivity_event_time_separated', 'missing_snapshot_flagged', 'exact_member_sponsor_join']}


def main():
    started = stamp()
    assert len(FEATURES) == len(DEFINITIONS) == 25
    ids = json.loads((OLD / 'identifiers.json').read_text(encoding='utf-8'))
    audit = collections.Counter()
    source_paths = [Path(__file__).resolve(), Path(__file__).with_name('institutions_common.py').resolve(),
                    OLD / 'identifiers.json', OLD / 'bills.jsonl', OLD / 'meta_117.parquet', OLD / 'meta_118.parquet',
                    BICAM / 'bicam_committees/committees.csv',
                    BICAM / 'bicam_members/members_leadership_roles.csv', BICAM / 'bicam_hearings/hearings_members.csv']
    source_paths += [BICAM / 'bicam_committeemeetings' / n for n in ['committeemeetings.csv', 'committeemeetings_associated_bills.csv', 'committeemeetings_committees.csv']]
    source_paths += [BICAM / 'bicam_hearings' / n for n in ['hearings.csv', 'hearings_dates.csv', 'hearings_bills.csv', 'hearings_committees.csv']]
    source_paths += sorted(SRC.glob('*'))
    source_hashes = [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in source_paths if p.is_file()]
    known_codes = {r['committee_code'] for r in rows(BICAM / 'bicam_committees/committees.csv', audit)}
    bills = read_bills(ids)
    snapshots = build_rosters(ids, known_codes, audit)
    events, availability, event_audit = build_events(bills, known_codes, audit)
    panels = {str(cg): write_panel(cg, ids, bills, snapshots, events, availability) for cg in [117, 118]}
    checks = boundary_checks()
    for r in source_hashes:
        assert digest(r['path']) == r['sha256'], 'Source changed during committee build: ' + r['path']
    output_paths = sorted(p for p in OUT.glob('committees*') if p.is_file() and p.name not in {'committees_receipt.json', 'committees_notes.md', 'committees_independent_checks.json'})
    receipt = {'status': 'PASS', 'started_at': started, 'completed_at': stamp(),
               'code_path': str(Path(__file__).resolve()), 'code_sha256': digest(__file__),
               'common_path': str(Path(__file__).with_name('institutions_common.py').resolve()),
               'common_sha256': digest(Path(__file__).with_name('institutions_common.py')),
               'features': FEATURES, 'feature_names': FEATURES,
               'feature_definitions': dict(zip(FEATURES, DEFINITIONS)),
               'feature_groups': {'primary': FEATURES[:21], 'archived_roster_and_referrals': FEATURES[:14],
                                  'conservative_record_dated_opportunities': FEATURES[14:21],
                                  'hearing_event_reconstruction_sensitivity_only': FEATURES[21:]},
               'panels': panels, 'sources': source_hashes, 'source_hashes_unchanged_after_build': True,
               'archive_retrieval_date': '2026-09-05',
               'bicam_vintage': 'Existing local extracted snapshot, bound by exact source bytes; original snapshot download date not independently verified. Latest-update and event ranges are reported separately.',
               'row_alignment': 'Exact original full meta_{congress}.parquet order; original identifiers.json indices; no cohort filter and no row reordering.',
               'outcome_access': 'Only bill/member/group/day/senate meta columns; no label, prediction, model fit, current psychology, hearing-member linkage or Congress119 outcome access.',
               'identity': 'Exact archived Bioguide to original identifiers.members. Exact BillStatus key cg:type:number to BICAM typeNumber-cg. Thomas four-character committee IDs normalize to lowercase plus 00; six-character subcommittee IDs remain exact. Archived roster codes must occur in committee definitions from the exact same commit; BICAM event/referral codes use its own complete dictionary. Historical select committee source IDs absent from BICAM remain valid roster/shared-group features without invented crosswalks. Unknown codes/member IDs outside original universe are counted/excluded; no fuzzy names.',
               'timing': {'forecast': 'Integer date ordinal interpreted as start of day. Every used snapshot/referral/event day is strictly less than forecast day. No same-day access.',
                          'roster': 'Latest same-Congress archived GitHub membership file; max(author date, committer date) is an archival observation proxy, not a verified historical push/publication timestamp. Empty Congress reset snapshots stay empty. No interpolation or backdating.',
                          'referrals': 'Dated official BillStatus Referred activity strictly before forecast, reconstructed from frozen later extraction. First historical API availability was not verified. This shares the existing action-reconstruction assumption.',
                          'conservative_events': 'max(event date, source latest-update date) strictly before forecast. BICAM updated_at maps to LOC updateDate (date of update in Congress.gov), not first publication or warehouse download. Final Scheduled status is used only after that update; canceled/postponed/rescheduled records are excluded, never backdated.',
                          'hearing_sensitivity': 'Event date strictly before forecast plus exact bill/date official Hearings held action corroboration. Publication/operational availability unverified. Dates outside the ID Congress rejected because source cleaner joins reused jacket numbers without Congress. Latest updates are deliberately NOT timing gates for these four columns.',
                          'future_scheduled_events': 'Excluded even when notice might have preceded forecast; no notice publication timestamps verified.'},
               'deduplication': 'Archived snapshot committee/member duplicates dropped. Events collapse on source,bill,event day,kind,sorted committee-code set; repeated printed parts/duplicate links count once and retain all source IDs and maximum latest-update day. Meeting and hearing source counts remain separate. No text or attendance used.',
               'missingness': 'Finite zero counts indicate no observed match in the captured source, not certified nonmembership or absence of activity. Roster/member/sponsor/referral coverage flags distinguish available observations; event_record_available means at least one usable record, not exhaustive source coverage. Recency uses log1p(3660) sentinel with count/availability flags; all other transformations are fixed row-local log1p or fractions, no cross-Congress normalization.',
               'interpretation': 'Observational forecast features only. Reported assignment, committee association and past bill opportunity are distinct from participation, attendance, contact, receptivity, lobbying effect or causality. Four-character source roster groups include select subcommittees and task forces as well as full committees; top-level roster counts are not counts of standing/full committees. Source-specific committee IDs without verified BICAM crosswalks support roster/shared-group features only.',
               'excluded_families': {'hearings_members.csv': '1,199,899 links have hearing/member metadata without an attendance or participation role. Entire family excluded.',
                                     'members_leadership_roles.csv': 'Congress-level party chamber leadership records lack exact effective dates and are not committee assignment records. Entire family excluded.',
                                     'current_only_rosters': 'Never used to backdate memberships; only exact historical commits enter features.',
                                     'unverified_hearing_dates': 'Require exact bill/date official Hearings held corroboration even in the sensitivity group.',
                                     'hearing_texts_and_witnesses': 'No transcript, witness or text-derived participant inference.'},
               'source_semantics_pointers': {'bicam_mapping': 'committees_sources/bicam_components.py Hearing.updated_at and CommitteeMeeting.updated_at return _update_date; cleaner preserves updated_at.',
                                           'jacket_join': 'committees_sources/bicam_hearings.py clean_hearings_dates joins only d.hearing_jacketnumber = h.hearing_jacketnumber.',
                                           'official_docs': ['https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/HearingEndpoint.md',
                                                             'https://github.com/LibraryOfCongress/api.congress.gov/blob/main/Documentation/CommitteeMeetingEndpoint.md'],
                                           'archive': 'https://github.com/unitedstates/congress-legislators'},
               'audit_counts': dict(audit), 'event_audit': event_audit, 'boundary_checks': checks,
               'outputs': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)} for p in output_paths]}
    write_json(OUT / 'committees_receipt.json', receipt)
    print(json.dumps({'status': 'PASS', 'receipt': str(OUT / 'committees_receipt.json'), 'event_audit': event_audit, 'audit_counts': dict(audit)}), flush=True)


if __name__ == '__main__':
    main()
