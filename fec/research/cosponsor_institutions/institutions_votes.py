"""Dated, descriptive roll-call evidence on the original full forecast panels.

This producer never reads outcome columns, fitted Voteview quantities, or 119
roll calls.  It does not orient procedural Yea votes as policy endorsements.
"""
from __future__ import annotations

import ast
import collections
import datetime as dt
import gzip
import json
import os
import re
from pathlib import Path

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
              'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_name] = '2'
import numpy as np
import pandas as pd

from institutions_common import ROOT, OUT, OLD, digest, stamp, write_json

RAW = ROOT / 'audits/dashboard_repair_20260905/voteview_source'
SOURCES = OUT / 'votes_sources'
FEATURES = [
    'vote_topic_eligible_log', 'vote_topic_missing',
    'vote_topic_substantive_recorded_log', 'vote_topic_substantive_yea_share',
    'vote_topic_substantive_missing',
    'vote_topic_procedural_recorded_log', 'vote_topic_procedural_yea_share',
    'vote_topic_procedural_missing',
    'vote_topic_amendment_recorded_log', 'vote_topic_amendment_yea_share',
    'vote_topic_amendment_missing',
    'vote_topic_not_voting_share', 'vote_topic_present_share',
    'vote_topic_paired_announced_share',
    'vote_sponsor_topic_shared_recorded_log', 'vote_sponsor_topic_agreement_share',
    'vote_sponsor_topic_agreement_missing',
    'vote_same_bill_earlier_eligible_log', 'vote_same_bill_latest_substantive_yea',
    'vote_same_bill_substantive_missing',
    'vote_source_identity_missing', 'vote_calendar_eligible_log',
    'vote_days_since_calendar_eligible', 'vote_calendar_missing',
    'vote_target_topic_unmapped',
]
CATEGORIES = {'substantive': 0, 'procedural': 1, 'amendment': 2, 'other': -1}
INPUTS = {}


def bind(path):
    path = Path(path)
    key = str(path.resolve())
    value = digest(path)
    if key in INPUTS and INPUTS[key]['sha256'] != value:
        raise RuntimeError(f'Input changed: {path}')
    INPUTS[key] = {'path': key, 'sha256': value, 'bytes': path.stat().st_size,
                   'observed_at': stamp()}
    return path


def csv_read(path, columns):
    frame = pd.read_csv(bind(path), usecols=columns, keep_default_na=False)
    bind(path)
    return frame


def load_topics():
    path = bind(ROOT / 'fec/research/cosponsor_challengers/build_panel.py')
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id == 'TOPICS' for t in node.targets):
            topics = ast.literal_eval(node.value)
            break
    else:
        raise AssertionError('Frozen TOPICS mapping absent')
    patterns = [(name, re.compile(pattern, re.I)) for name, pattern in topics.items()]
    return topics, patterns


def topic_for(title, patterns):
    return next((name for name, pattern in patterns if pattern.search(title)), 'other')


def load_bills(patterns):
    result = {}
    path = bind(OLD / 'bills.jsonl')
    with path.open(encoding='utf-8') as handle:
        for line in handle:
            # Skip the held-out Congress before parsing its object.
            if re.search(r'"congress"\s*:\s*119\b', line):
                continue
            obj = json.loads(line)
            if obj['congress'] not in (116, 117, 118):
                continue
            titles = [t['text'] for t in obj['titles']
                      if 'as introduced' in t['kind'].lower()]
            assert len(titles) == len(obj['titles']), 'Non-introduction title in frozen mapping'
            intro = dt.date.fromisoformat(obj['introduced']).toordinal()
            title = ' '.join(titles)
            result[obj['key']] = {'topic': topic_for(title, patterns),
                                  'introduced_day': intro, 'title': title,
                                  'sponsor': obj['sponsor']}
    bind(path)
    return result


def bill_key(congress, raw):
    value = re.sub(r'[^A-Z0-9]', '', str(raw).upper())
    match = re.fullmatch(r'(HR|S|HRES|SRES|HJRES|SJRES|HCONRES|SCONRES)(\d+)', value)
    return f'{congress}:{match[1].lower()}:{int(match[2])}' if match else ''


def classify(question, key, title):
    q = question.lower()
    kind = key.split(':')[1] if key else ''
    if any(x in q for x in ('nomination', 'guilty', 'ratification', 'election of speaker',
                            'approving the journal', 'attendance')):
        return 'other'
    if 'certain bills' in q or 'certain resolutions' in q:
        return 'other'  # Multi-measure questions cannot be assigned to one policy.
    procedural = ('cloture', 'previous question', 'motion to proceed', 'motion to table',
                  'table motion', 'recommit', 'motion to commit', 'motion to refer',
                  'motion to discharge', 'motion to adjourn', 'motion that the committee rise',
                  'motion to reconsider', 'point of order', 'decision of the chair',
                  'instruct conferees', 'closing portions', 'go to conference',
                  'request a conference', 'motion to proceed in order', 'on the objection')
    if any(x in q for x in procedural) or q == 'on the motion':
        return 'procedural'
    if kind in ('hres', 'sres') and re.search(r'providing for (?:consideration|proceedings)|rules of the house', title, re.I):
        return 'procedural'
    if 'amendment' in q and ('agreeing to' in q or q.startswith('on the amendment')):
        return 'amendment'
    if any(x in q for x in ('passage', 'and pass', 'overriding the veto', 'conference report')):
        return 'substantive'
    if 'concur' in q and 'disagree' not in q:
        return 'substantive'
    if kind in ('hjres', 'sjres') and ('resolution' in q or 'override' in q):
        return 'substantive'
    return 'other'


def source_events(identifiers, bills, topic_names):
    members = {value: i for i, value in enumerate(identifiers['members'])}
    topic_codes = {name: i for i, name in enumerate(topic_names) if name != 'other'}
    ledgers, vote_frames, identity_by_cg, stats = [], [], {}, {}
    for cg in (116, 117, 118):
        directory = SOURCES if cg == 116 else RAW
        identities = csv_read(directory / f'HS{cg}_members.csv',
                              ['congress', 'chamber', 'icpsr', 'bioguide_id'])
        identities = identities[identities.chamber.isin(['House', 'Senate'])].copy()
        assert not identities.duplicated(['congress', 'chamber', 'icpsr']).any()
        identity_by_cg[cg] = set(identities.bioguide_id) - {''}
        rolls = csv_read(directory / f'HS{cg}_rollcalls.csv',
                         ['congress', 'chamber', 'rollnumber', 'date', 'bill_number', 'vote_question'])
        assert set(rolls.congress) == {cg}
        assert not rolls.duplicated(['congress', 'chamber', 'rollnumber']).any()
        rolls['day'] = [dt.date.fromisoformat(s).toordinal() for s in rolls.date]
        rolls['event_id'] = [f'{cg}:{c}:{r}' for c, r in zip(rolls.chamber, rolls.rollnumber)]
        rolls['bill_key'] = [bill_key(cg, x) for x in rolls.bill_number]
        intro_titles, topics, origins, categories = [], [], [], []
        for row in rolls.itertuples():
            b = bills.get(row.bill_key)
            available = b is not None and b['introduced_day'] <= row.day
            title = b['title'] if available else ''
            intro_titles.append(title)
            topics.append(b['topic'] if available else 'other')
            origins.append('frozen_introduction_title' if available else 'no_dated_introduction_match')
            categories.append(classify(row.vote_question, row.bill_key, title))
        rolls['topic'] = topics
        rolls['topic_source'] = origins
        rolls['category'] = categories
        rolls['topic_code'] = [topic_codes.get(x, -1) for x in topics]
        rolls['category_code'] = [CATEGORIES[x] for x in categories]
        rolls['introduction_title'] = intro_titles
        votes = csv_read(directory / f'HS{cg}_votes.csv',
                         ['congress', 'chamber', 'rollnumber', 'icpsr', 'cast_code'])
        assert set(votes.congress) == {cg}
        assert set(votes.cast_code).issubset(set(range(10)))
        assert not votes.duplicated(['congress', 'chamber', 'rollnumber', 'icpsr']).any()
        votes = votes.merge(identities, on=['congress', 'chamber', 'icpsr'], how='left', validate='many_to_one')
        votes = votes.merge(rolls[['congress', 'chamber', 'rollnumber', 'event_id', 'day']],
                            on=['congress', 'chamber', 'rollnumber'], how='left', validate='many_to_one')
        assert votes.event_id.notna().all()
        votes['member_code'] = votes.bioguide_id.map(members).fillna(-1).astype('int32')
        usable = votes[(votes.cast_code != 0) & (votes.member_code >= 0)]
        assert not usable.duplicated(['event_id', 'member_code']).any(), 'Ambiguous ICPSR/Bioguide cast join'
        stats[str(cg)] = {'rollcalls': len(rolls), 'raw_vote_rows': len(votes),
                         'cast_code_counts': {str(k): int(v) for k, v in votes.cast_code.value_counts().items()},
                         'panel_resolved_nonzero_vote_rows': len(usable),
                         'unknown_bioguide_rows': int(votes.bioguide_id.isna().sum()),
                         'nonpanel_vote_rows': int((votes.member_code < 0).sum()),
                         'dated_introduction_matches': int((rolls.topic_source == 'frozen_introduction_title').sum()),
                         'topic_mapped_classified_rollcalls': int(((rolls.topic_code >= 0) & (rolls.category_code >= 0)).sum()),
                         'categories': dict(collections.Counter(categories)),
                         'topics': dict(collections.Counter(topics)),
                         'first_vote_date': rolls.date.min(), 'last_vote_date': rolls.date.max()}
        ledgers.append(rolls)
        vote_frames.append(votes[['event_id', 'day', 'congress', 'chamber', 'rollnumber',
                                  'icpsr', 'bioguide_id', 'member_code', 'cast_code']])
    rollcalls = pd.concat(ledgers, ignore_index=True).sort_values(
        ['day', 'congress', 'chamber', 'rollnumber'], kind='stable').reset_index(drop=True)
    rollcalls['event_index'] = np.arange(len(rollcalls), dtype=np.int32)
    rollcalls.to_csv(OUT / 'votes_rollcalls.csv', index=False)
    all_votes = pd.concat(vote_frames, ignore_index=True)
    with gzip.open(OUT / 'votes_events.csv.gz', 'wt', encoding='utf-8', newline='') as handle:
        all_votes.to_csv(handle, index=False, chunksize=100000)
    index = dict(zip(rollcalls.event_id, rollcalls.event_index))
    matrix = np.zeros((len(rollcalls), len(members)), dtype=np.int8)
    usable = all_votes[(all_votes.member_code >= 0) & (all_votes.cast_code != 0)]
    matrix[usable.event_id.map(index).to_numpy(), usable.member_code.to_numpy()] = usable.cast_code.to_numpy(dtype=np.int8)
    return rollcalls, matrix, identity_by_cg, stats


def ratio(a, b):
    return np.divide(a, b, out=np.zeros(np.broadcast_shapes(np.shape(a), np.shape(b)), dtype=np.float64), where=np.asarray(b) > 0)


def vector_from_history(member, sponsor, target_bill, topic, forecast, rolls, casts, identity_missing):
    """Independent direct ledger scan used for sampled recounts and boundary tests."""
    output = np.zeros(len(FEATURES), dtype=np.float64)
    codes = casts[:, member]
    calendar = codes > 0
    topic_mask = (rolls.topic_code.to_numpy() == topic) & (rolls.category_code.to_numpy() >= 0) if topic >= 0 else np.zeros(len(rolls), bool)
    eligible = topic_mask & calendar
    output[0:2] = [np.log1p(eligible.sum()), not eligible.any()]
    for cat, start in ((0, 2), (1, 5), (2, 8)):
        mask = topic_mask & (rolls.category_code.to_numpy() == cat) & np.isin(codes, (1, 6))
        output[start:start+3] = [np.log1p(mask.sum()), (codes[mask] == 1).mean() if mask.any() else 0, not mask.any()]
    if eligible.any():
        output[11:14] = [(codes[eligible] == 9).mean(), np.isin(codes[eligible], (7, 8)).mean(), np.isin(codes[eligible], (2, 3, 4, 5)).mean()]
    joint = topic_mask & np.isin(codes, (1, 6)) & np.isin(casts[:, sponsor], (1, 6)) if sponsor >= 0 else np.zeros(len(rolls), bool)
    output[14:17] = [np.log1p(joint.sum()), (codes[joint] == casts[joint, sponsor]).mean() if joint.any() else 0, not joint.any()]
    same_bill = (rolls.bill_key.to_numpy() == target_bill) & calendar
    actual_sub = same_bill & (rolls.category_code.to_numpy() == 0) & np.isin(codes, (1, 6))
    output[17:20] = [np.log1p(same_bill.sum()), int(codes[np.flatnonzero(actual_sub)[-1]] == 1) if actual_sub.any() else 0, not actual_sub.any()]
    output[20:25] = [identity_missing, np.log1p(calendar.sum()), forecast-int(rolls.day.to_numpy()[calendar][-1]) if calendar.any() else 0, not calendar.any(), topic < 0]
    return output


def build_panel(cg, identifiers, bills, names, rolls, casts, identity_by_cg):
    path = bind(OLD / f'meta_{cg}.parquet')
    meta = pd.read_parquet(path, columns=['bill', 'member', 'group', 'day', 'senate'])
    bind(path)
    assert meta.index.equals(pd.RangeIndex(len(meta)))
    assert meta.member.between(0, len(identifiers['members'])-1).all()
    assert meta.bill.between(0, len(identifiers['bills'])-1).all()
    n, nt = len(identifiers['members']), len(names)-1
    member_index = {value: i for i, value in enumerate(identifiers['members'])}
    topic_index = {name: i for i, name in enumerate(names) if name != 'other'}
    bill_topics = np.full(len(identifiers['bills']), -1, dtype=np.int16)
    bill_sponsors = np.full(len(identifiers['bills']), -1, dtype=np.int32)
    target_bills = set(int(b) for b in meta.bill.unique())
    for b in target_bills:
        key = identifiers['bills'][b]
        assert int(key.split(':')[0]) == cg
        frozen = bills[key]
        bill_topics[b] = topic_index.get(frozen['topic'], -1)
        bill_sponsors[b] = member_index.get(frozen['sponsor'], -1)
    start = dt.date(2*(cg-1)+1787, 1, 3).toordinal()
    select = rolls.congress.isin([cg-1, cg]).to_numpy() & (rolls.day.to_numpy() >= start)
    history = rolls.loc[select].reset_index(drop=True)
    values = casts[select]
    days, topics, categories = (history[c].to_numpy() for c in ('day', 'topic_code', 'category_code'))
    bill_codes = np.array([{v: k for k, v in enumerate(identifiers['bills'])}.get(x, -1) for x in history.bill_key], dtype=np.int32)
    identity_missing = np.array([x not in (identity_by_cg[cg-1] | identity_by_cg[cg]) for x in identifiers['members']], dtype=np.int8)
    eligible = np.zeros((nt+1, n), dtype=np.int32)
    recorded = np.zeros((nt+1, 3, n), dtype=np.int32)
    yeas = np.zeros_like(recorded)
    unusual = np.zeros((nt+1, 3, n), dtype=np.int32)
    shared = np.zeros((nt+1, n, n), dtype=np.int16)
    agreement = np.zeros_like(shared)
    calendar = np.zeros(n, dtype=np.int32)
    last_calendar = np.zeros(n, dtype=np.int32)
    same_bill = {}
    output_path = OUT / f'votes_{cg}.f32'
    output = np.memmap(output_path, mode='w+', dtype='float32', shape=(len(meta), len(FEATURES)))
    cursor = 0
    checkpoints = []
    # Every assignment indexes ORIGINAL row positions; no filtered index is used.
    for forecast, rows in meta.groupby('day', sort=True).indices.items():
        while cursor < len(history) and days[cursor] < forecast:
            code = values[cursor]
            ix = np.flatnonzero(code > 0)
            calendar[ix] += 1
            last_calendar[ix] = days[cursor]
            topic, cat = topics[cursor], categories[cursor]
            actual = np.flatnonzero(np.isin(code, (1, 6)))
            if topic >= 0 and cat >= 0:
                eligible[topic, ix] += 1
                recorded[topic, cat, actual] += 1
                yeas[topic, cat, np.flatnonzero(code == 1)] += 1
                for j, codes in enumerate(((9,), (7, 8), (2, 3, 4, 5))):
                    unusual[topic, j, np.flatnonzero(np.isin(code, codes))] += 1
                shared[topic][np.ix_(actual, actual)] += 1
                for cast in (1, 6):
                    direction = np.flatnonzero(code == cast)
                    agreement[topic][np.ix_(direction, direction)] += 1
            b = bill_codes[cursor]
            if b in target_bills:
                counts, latest = same_bill.setdefault(b, (np.zeros(n, np.int32), np.full(n, -1, np.int8)))
                counts[ix] += 1
                if cat == 0:
                    latest[actual] = code[actual] == 1
            cursor += 1
        assert cursor == np.searchsorted(days, forecast, side='left')
        members = meta.member.to_numpy()[rows]
        bill = meta.bill.to_numpy()[rows]
        topic = bill_topics[bill]
        safe_topic = np.where(topic >= 0, topic, nt)
        sponsor = bill_sponsors[bill]
        block = np.zeros((len(rows), len(FEATURES)), dtype=np.float64)
        exp = eligible[safe_topic, members]
        block[:, 0:2] = np.column_stack((np.log1p(exp), exp == 0))
        for cat, begin in ((0, 2), (1, 5), (2, 8)):
            count = recorded[safe_topic, cat, members]
            block[:, begin:begin+3] = np.column_stack((np.log1p(count), ratio(yeas[safe_topic, cat, members], count), count == 0))
        for j in range(3):
            block[:, 11+j] = ratio(unusual[safe_topic, j, members], exp)
        pair_count = np.where(sponsor >= 0, shared[safe_topic, members, np.maximum(sponsor, 0)], 0)
        pair_agree = np.where(sponsor >= 0, agreement[safe_topic, members, np.maximum(sponsor, 0)], 0)
        block[:, 14:17] = np.column_stack((np.log1p(pair_count), ratio(pair_agree, pair_count), pair_count == 0))
        block[:, 19] = 1
        for b in np.unique(bill):
            if b in same_bill:
                pos = np.flatnonzero(bill == b)
                counts, latest = same_bill[b]
                m = members[pos]
                block[pos, 17] = np.log1p(counts[m])
                block[pos, 18] = np.maximum(latest[m], 0)
                block[pos, 19] = latest[m] < 0
        cal = calendar[members]
        block[:, 20:25] = np.column_stack((identity_missing[members], np.log1p(cal),
                    np.where(cal > 0, forecast-last_calendar[members], 0), cal == 0, topic < 0))
        assert np.isfinite(block).all()
        output[rows] = block.astype('float32')
        checkpoints.append({'forecast_day': int(forecast), 'rows': len(rows),
                            'included_rollcalls': cursor,
                            'latest_included_day': int(days[cursor-1]) if cursor else None,
                            'excluded_same_day_rollcalls': int((days == forecast).sum())})
    output.flush()
    rng = np.random.default_rng(20260905+cg)
    sampled = np.unique(np.r_[rng.choice(len(meta), min(600, len(meta)), replace=False),
                               meta.groupby('day', sort=True).head(1).index.to_numpy()[:80]])
    max_error = 0.0
    for row_idx in sampled:
        row = meta.iloc[int(row_idx)]
        stop = np.searchsorted(days, row.day, side='left')
        want = vector_from_history(int(row.member), int(bill_sponsors[row.bill]),
                    identifiers['bills'][row.bill], int(bill_topics[row.bill]), int(row.day),
                    history.iloc[:stop], values[:stop], int(identity_missing[row.member]))
        error = float(np.max(np.abs(output[row_idx]-want.astype('float32'))))
        max_error = max(max_error, error)
        assert error <= 1e-6, (cg, row_idx, error, FEATURES[int(np.argmax(np.abs(output[row_idx]-want)))])
    coverage = {}
    for chamber, flag in [('House', 0), ('Senate', 1)]:
        rows = np.flatnonzero(meta.senate.to_numpy() == flag)
        coverage[chamber] = {'rows': len(rows), 'members': int(meta.iloc[rows].member.nunique()),
            'topic_eligible_rows': int((output[rows, 0] > 0).sum()),
            'sponsor_topic_shared_rows': int((output[rows, 14] > 0).sum()),
            'same_bill_prior_rows': int((output[rows, 17] > 0).sum()),
            'calendar_eligible_rows': int((output[rows, 21] > 0).sum()),
            'identity_missing_rows': int(output[rows, 20].sum()),
            'target_topic_unmapped_rows': int(output[rows, 24].sum())}
    write_json(OUT / f'votes_{cg}_checkpoints.json', checkpoints)
    result = {'path': str(output_path), 'shape': [len(meta), len(FEATURES)],
              'dtype': 'float32', 'order': 'C', 'sha256': digest(output_path),
              'original_meta_sha256': digest(path), 'alignment': 'Original RangeIndex positions, unfiltered',
              'window_start': dt.date.fromordinal(start).isoformat(), 'forecast_days': len(checkpoints),
              'included_source_congresses': [cg-1, cg], 'coverage': coverage,
              'validation': {'direct_ledger_recount_rows': len(sampled), 'max_absolute_error': max_error,
                             'strict_boundary_checkpoints': len(checkpoints)}}
    del output
    print(f'{stamp()} Congress {cg} complete: {result["shape"]}; recount max error {max_error}', flush=True)
    return result


def self_test():
    assert bill_key(117, 'H.R. 12') == '117:hr:12'
    assert bill_key(117, 'HR12/S13') == ''
    assert classify('On the Cloture Motion', '117:hr:1', '') == 'procedural'
    assert classify('On Motion to Recommit with Instructions', '117:hr:1', '') == 'procedural'
    assert classify('On Agreeing to the Amendment', '117:hr:1', '') == 'amendment'
    assert classify('On Passage', '117:hr:1', '') == 'substantive'
    assert classify('On the Nomination', '', '') == 'other'
    days = np.array([10, 11, 11, 12])
    assert np.searchsorted(days, 11, side='left') == 1
    # Codes 2-5 express direction but are not actual votes; 0 is ineligible.
    codes = np.arange(10)
    assert np.isin(codes, (1, 6)).sum() == 2
    assert (codes > 0).sum() == 9
    return {'classifier_examples': 6, 'same_day_exclusion_example': True,
            'actual_vote_denominator_codes': [1, 6], 'ineligible_code_excluded': 0}


def main():
    began = stamp()
    tests = self_test()
    bind(Path(__file__))
    bind(Path(__file__).with_name('institutions_common.py'))
    vintage_entries = []
    for receipt_path in (SOURCES / 'votes_download_receipt.json', RAW / 'receipt.json'):
        source_receipt = json.loads(bind(receipt_path).read_text(encoding='utf-8'))
        for entry in source_receipt['files']:
            if re.fullmatch(r'HS(?:116|117|118)_(?:members|rollcalls|votes)\.csv', Path(entry['path']).name):
                assert digest(entry['path']) == entry['sha256'], 'Source differs from download receipt'
                vintage_entries.append(entry)
    assert len(vintage_entries) == 9
    ids = json.loads(bind(OLD / 'identifiers.json').read_text(encoding='utf-8'))
    topics, patterns = load_topics()
    names = list(topics)
    assert names[-1] == 'other'
    bills = load_bills(patterns)
    rolls, casts, identities, source_stats = source_events(ids, bills, names)
    outputs = {str(cg): build_panel(cg, ids, bills, names, rolls, casts, identities) for cg in (117, 118)}
    for entry in list(INPUTS.values()):
        assert digest(entry['path']) == entry['sha256'], f'Input changed during build: {entry["path"]}'
    artifacts = []
    for name in ('votes_rollcalls.csv', 'votes_events.csv.gz', 'votes_117_checkpoints.json', 'votes_118_checkpoints.json'):
        p = OUT / name
        artifacts.append({'path': str(p), 'sha256': digest(p), 'bytes': p.stat().st_size})
    receipt = {'schema': 'institutions-votes-v1', 'status': 'PASS', 'began_at': began, 'completed_at': stamp(),
        'features': FEATURES, 'ordered_features': FEATURES, 'feature_count': len(FEATURES),
        'panels': outputs, 'sources': list(INPUTS.values()), 'source_vintages': vintage_entries,
        'source_coverage': source_stats,
        'ledger_artifacts': artifacts, 'topic_patterns': topics, 'self_tests': tests,
        'source_urls': {str(cg): {kind: f'https://voteview.com/static/data/out/{kind}/HS{cg}_{kind}.csv'
                        for kind in ('members', 'rollcalls', 'votes')} for cg in (116, 117, 118)},
        'codebook_url': 'https://voteview.com/articles/data_help_votes',
        'cast_codes': {'0': 'not a chamber member at time of vote; excluded', '1': 'Yea',
                      '2': 'Paired Yea', '3': 'Announced Yea', '4': 'Announced Nay',
                      '5': 'Paired Nay', '6': 'Nay', '7': 'Present', '8': 'Present', '9': 'Not Voting'},
        'cutoff_rules': ['For each forecast: prior-Congress January 3 <= vote date < forecast date.',
                        'All same-day votes excluded; no imputed intraday ordering.',
                        'Each panel uses only prior and current Congress, never Congress 119.',
                        'Only as-introduced titles on bills introduced by vote date supply topic; unknown/other topics are not pooled.',
                        'No fitted probability, NOMINATE/whole-Congress ideology, vote result, aggregate counts or post-introduction bill labels read.'],
        'definitions': {'eligible': 'cast codes 1..9; 0 excluded, source-absent rows not converted to abstention',
            'recorded': 'codes 1 and 6 only; all Yea shares describe the literal vote question, not inferred policy direction',
            'topic': 'frozen introduction-title first-regex-match; categories substantive, procedural, amendment only',
            'topic_unusual_shares': 'code 9 / codes 7,8 / codes 2..5, each divided by topic eligible votes',
            'agreement': 'Same actual code 1/6 among candidate and sponsor jointly recorded on same topic and any of three classified categories; cross-chamber pairs normally missing',
            'same_bill': 'exact Congress/type/number, any eligible earlier vote; latest substantive actual 1/6 direction retained; latest determined by date then chamber/rollnumber',
            'calendar': 'all nonzero raw votes for member, including unclassified/nonlegislative calls; recency zero only when calendar_missing=1',
            'source_identity_missing': 'Bioguide absent from both prior/current Congress source member files; this is source coverage, not policy absence',
            'missing_values': 'shares/direction/recency zero with explicit missing flags; exposure counts log1p'},
        'limitations': ['Retrospective reconstruction: source files retrieved in 2026 and corrected September 4, 2026, not archived as-of-2021/2023 data vintages. Vote dates and contemporaneous vote questions establish event timing, not proof of exact historical bytes.',
                        'Frozen as-introduced titles lack captured historical publication timestamps; do not claim an ingestion-time holdout.',
                        'No latent support inference: Nay on an amendment or Yea on cloture is not necessarily opposition/support for the parent policy.',
                        'Topics inherit the already-frozen coarse regex mapping, including its semantic limitations.',
                        'Sponsor agreement is descriptive, sparse for cross-chamber sponsors and newcomers, and is not evidence of communication.']}
    write_json(OUT / 'votes_receipt.json', receipt)
    (OUT / 'votes_report.md').write_text(
        '# Dated roll-call features\n\n25 features; original full panel alignment; no outcome columns read.\n\n'
        + '\n'.join(f'- Congress {cg}: {p["shape"][0]:,} rows; {p["validation"]["direct_ledger_recount_rows"]} direct recounts, max error {p["validation"]["max_absolute_error"]}.' for cg,p in outputs.items())
        + '\n\nEvents must precede the forecast day. Codes 1/6 are actual Yea/Nay; codes 2–5, 7–8, and 9 have separate shares. Procedural Yea is not policy endorsement.\n\n'
        + 'Historical vote events are reconstructed from corrected 2026 Voteview files and frozen as-introduced titles; this is not a historical ingestion snapshot. Full definitions, dated source hashes, per-chamber coverage and ledger hashes are in votes_receipt.json.\n', encoding='utf-8')
    print(f'{stamp()} PASS votes_receipt.json', flush=True)


if __name__ == '__main__':
    main()
