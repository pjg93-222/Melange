"""Vote-source coverage gate: recorded floor votes in BILLSTATUS vs the Voteview snapshot. Offline, tiny fixtures."""
import csv
import os
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from legislation import vote_coverage as VC

XML = ('<?xml version="1.0"?><billStatus><bill><actions><recordedVotes>{votes}</recordedVotes></actions></bill></billStatus>')
VOTE = ('<recordedVote><rollNumber>{roll}</rollNumber><chamber>{chamber}</chamber><congress>119</congress>'
        '<date>{date}</date><sessionNumber>{session}</sessionNumber></recordedVote>')


def raw_root(tmp_path, bills):
    """bills: {'119:hr:5': [(chamber, roll, date, session), ...]} -> BILLSTATUS zip tree; a None value = file missing."""
    root = tmp_path / 'raw'
    (root / 'billstatus119').mkdir(parents=True)
    with zipfile.ZipFile(root / 'billstatus119' / 'BILLSTATUS-119-hr.zip', 'w') as z:
        for key, votes in bills.items():
            if votes is None:
                continue
            body = ''.join(VOTE.format(chamber=c, roll=r, date=d, session=s) for c, r, d, s in votes)
            z.writestr(f'BILLSTATUS-119hr{key.split(":")[2]}.xml', XML.format(votes=body))
    return str(root)


def snapshot(tmp_path, house='2026-09-16', senate='2026-09-30', house_roll=362, senate_roll=659):
    src = tmp_path / 'src'
    src.mkdir(exist_ok=True)
    with (src / 'HS119_rollcalls.csv').open('w', newline='') as h:
        w = csv.writer(h)
        w.writerow(['congress', 'chamber', 'rollnumber', 'date', 'session', 'clerk_rollnumber'])
        w.writerow([119, 'House', 1, '2026-01-05', 2, house_roll]); w.writerow([119, 'House', 2, house, 2, 1])
        w.writerow([119, 'Senate', 1, '2026-01-05', 2, senate_roll]); w.writerow([119, 'Senate', 2, senate, 2, 1])
    return src


def run(tmp_path, bills, **snap):
    src = snapshot(tmp_path, **snap)
    return VC.evaluate(src, sorted(bills), raw_root(tmp_path, bills))


def test_recess_no_newer_recorded_votes_passes(tmp_path):
    msg, uncovered, unverifiable = run(tmp_path, {'119:hr:1': [('House', '300', '2026-09-16T15:00:00Z', '2'),
                                                              ('Senate', '600', '2026-09-30T20:00:00Z', '2')]})
    assert msg is None and not uncovered and not unverifiable


def test_newer_house_vote_fails_and_names_it(tmp_path):
    msg, uncovered, _ = run(tmp_path, {'119:hr:1': [('House', '363', '2026-10-20T15:00:00Z', '2')]})
    assert 'newest uncovered: 119:hr:1 House roll 363 2026-10-20' in msg and '1 recorded' in msg


def test_per_chamber_independence(tmp_path):
    (tmp_path / 'a').mkdir(); (tmp_path / 'b').mkdir()
    house, _, _ = run(tmp_path / 'a', {'119:hr:1': [('House', '363', '2026-10-20T15:00:00Z', '2'),
                                                    ('Senate', '600', '2026-09-30T20:00:00Z', '2')]})
    assert house and 'House' in house and 'Senate roll' not in house
    senate, _, _ = run(tmp_path / 'b', {'119:hr:1': [('Senate', '700', '2026-10-21T15:00:00Z', '2'),
                                                     ('House', '300', '2026-09-16T15:00:00Z', '2')]})
    assert senate and 'newest uncovered: 119:hr:1 Senate roll 700' in senate


def test_roll_number_cross_check_flags_even_when_date_is_covered(tmp_path):
    msg, uncovered, _ = run(tmp_path, {'119:hr:1': [('House', '400', '2026-09-10T15:00:00Z', '2')]})
    assert msg and uncovered[0]['roll'] == '400'


def test_utc_instant_is_compared_as_eastern_day(tmp_path):
    # 2026-09-17T02:00Z is the evening of 09-16 Eastern: covered, not newer.
    msg, _, _ = run(tmp_path, {'119:hr:1': [('House', '300', '2026-09-17T02:00:00Z', '2')]})
    assert msg is None


def test_mtime_is_ignored(tmp_path):
    for name, vote, expect_stale in (('stale', ('House', '363', '2026-10-20T15:00:00Z', '2'), True),
                                     ('fresh', ('House', '300', '2026-09-16T15:00:00Z', '2'), False)):
        base = tmp_path / name
        base.mkdir()
        src, raw = snapshot(base), raw_root(base, {'119:hr:1': [vote]})
        for stamp in (4_000_000_000, 1_000_000_000):
            for p in list(src.iterdir()) + list(Path(raw).rglob('*.zip')):
                os.utime(p, (stamp, stamp))
            assert bool(VC.evaluate(src, ['119:hr:1'], raw)[0]) is expect_stale


def test_voice_vote_only_bill_passes(tmp_path):
    msg, uncovered, unverifiable = run(tmp_path, {'119:hr:1': []})
    assert msg is None and not uncovered and not unverifiable


def test_missing_billstatus_is_unverifiable_not_stale(tmp_path):
    msg, uncovered, unverifiable = run(tmp_path, {'119:hr:1': None, '119:hr:2': []})
    assert msg is None and unverifiable == ['119:hr:1']


def test_duplicate_entries_dedupe_per_bill_chamber_roll(tmp_path):
    msg, uncovered, _ = run(tmp_path, {'119:hr:1': [('House', '363', '2026-10-20T15:00:00Z', '2')] * 3})
    assert len(uncovered) == 1


def test_archive_bill_keys_dedupe_and_restrict_to_covered_congresses():
    import pandas as pd
    from legislation.build_vote_category import measure
    frame = pd.DataFrame([{'Name': 'H.R.1', 'Congress': 119}, {'Name': 'H.R.1', 'Congress': 119}, {'Name': 'S.9', 'Congress': 116}])
    assert VC.archive_bill_keys(frame, measure) == ['119:hr:1']
