# -*- coding: utf-8 -*-
"""roster.arrivals() / roster.drift(): how an artifact built before a roster refresh may differ from the sitting roster.

Only the RULED arrivals (D-278, D-279, D-330: the 533 -> 535 refresh's three, pinned by bioguide and name) may be missing,
and only before the media gate (collection_intake_receipt.json exactly REJECTED).  Every other member, including the
16-member "seated after 2025-01-03 / thin_evidence" class the old rule tolerated forever, is a real mismatch.

Fixture-only: a synthetic roster.json under tmp_path, passed as ``root``.  Nothing reads the live data plane.
"""
import json
import os
import sys

import pytest

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if FEC not in sys.path:
    sys.path.insert(0, FEC)

import roster

ROWS = [
    {'member': 'Continuing', 'bioguide': 'C000001', 'chamber': 'House', 'term_start': '2023-01-03'},
    {'member': 'Aisha Wahab', 'bioguide': 'W000832', 'chamber': 'House', 'term_start': '2026-09-02'},
    {'member': 'Everton Blair', 'bioguide': 'B001328', 'chamber': 'House', 'term_start': '2026-09-01'},
    # the old date/flag rule called these arrivals; no ruling names them
    {'member': 'Ashley Moody', 'bioguide': 'M001244', 'chamber': 'Senate', 'term_start': '2025-01-21'},
    {'member': 'Flagged Thin', 'bioguide': 'N000002', 'chamber': 'House', 'term_start': '2023-01-03', 'thin_evidence': True},
    # a ruled bioguide under another name is not the ruled member
    {'member': 'Not Darline', 'bioguide': 'G000608', 'chamber': 'Senate', 'term_start': '2026-07-14'},
]
DEPARTED = [{'member': 'Resigned', 'bioguide': 'D000001', 'departed_on': '2026-09-01'}]
CURRENT = [row['member'] for row in ROWS]
RULED_HERE = {'Aisha Wahab', 'Everton Blair'}


def receipt(root, body):
    with open(os.path.join(root, 'data', 'engine', 'collection_intake_receipt.json'), 'w', encoding='utf-8') as f:
        f.write(body if isinstance(body, str) else json.dumps(body))


@pytest.fixture(autouse=True)
def inside_the_119th(monkeypatch):
    monkeypatch.setattr(roster, '_now', lambda: roster.datetime.datetime(2026, 10, 27, tzinfo=roster.datetime.timezone.utc))


@pytest.fixture()
def root(tmp_path):
    os.makedirs(tmp_path / 'data' / 'engine')
    (tmp_path / 'data' / 'engine' / 'roster.json').write_text(json.dumps(
        {'schema': roster.SCHEMA, 'members': ROWS, 'departed': DEPARTED}), encoding='utf-8')
    receipt(str(tmp_path), {'status': 'REJECTED'})
    return str(tmp_path)


def test_the_pin_is_exactly_the_533_to_535_refresh_arrivals():
    # audits/roster_refresh/20261021_015725 roster_refresh_receipt.json delta.arrivals
    assert roster.RULED_ARRIVALS == {'B001328': 'Everton Blair', 'G000608': 'Darline Graham', 'W000832': 'Aisha Wahab'}
    assert not hasattr(roster, 'ARRIVAL_AFTER')


def test_arrivals_are_only_the_ruled_members_on_the_roster(root):
    assert roster.arrivals(root) == RULED_HERE


def test_a_ruled_arrival_missing_is_tolerated_and_departed_extras_dropped(root):
    covered = ['Continuing', 'Ashley Moody', 'Flagged Thin', 'Not Darline', 'Resigned']
    assert roster.drift(CURRENT, covered, root) == (RULED_HERE, {'Resigned'}, set(), set())


@pytest.mark.parametrize('name', ['Ashley Moody', 'Flagged Thin', 'Not Darline', 'Continuing'])
def test_a_non_ruled_member_with_missing_data_fails(root, name):
    covered = [n for n in CURRENT if n != name]
    withheld, dropped, bad_missing, bad_extra = roster.drift(CURRENT, covered, root)
    assert bad_missing == {name} and not withheld and not dropped and not bad_extra


def test_a_covered_arrival_is_not_withheld(root):
    assert roster.drift(CURRENT, CURRENT, root) == (set(), set(), set(), set())


@pytest.mark.parametrize('body', [{'status': 'ACCEPTED'}, {'status': 'PASS'}, {'status': None}, {}, ['REJECTED'],
                                  'not json', None])
def test_the_tolerance_expires_once_the_media_gate_moves_on(root, body):
    if body is None:
        os.remove(os.path.join(root, 'data', 'engine', 'collection_intake_receipt.json'))
    else:
        receipt(root, body)
    assert roster.arrivals(root) == set()
    covered = [n for n in CURRENT if n not in RULED_HERE]
    withheld, dropped, bad_missing, bad_extra = roster.drift(CURRENT, covered, root)
    assert bad_missing == RULED_HERE and not withheld


def test_an_extra_name_that_is_not_departed_is_a_real_mismatch(root):
    covered = CURRENT + ['Stranger', 'Resigned']
    withheld, dropped, bad_missing, bad_extra = roster.drift(CURRENT, covered, root)
    assert bad_extra == {'Stranger'} and dropped == {'Resigned'} and not withheld and not bad_missing


@pytest.mark.parametrize('term_start, end', [
    ('2026-09-02', '2027-01-03T17:00:00+00:00'),   # 119th
    ('2025-01-03', '2027-01-03T17:00:00+00:00'),   # opening day of the 119th
    ('2025-01-02', '2025-01-03T17:00:00+00:00'),   # last day of the 118th
    ('2027-01-03', '2029-01-03T17:00:00+00:00'),   # 120th
])
def test_first_congress_end_is_noon_et_january_3_after_the_seating_congress(term_start, end):
    assert roster.first_congress_end(term_start).isoformat() == end


def test_the_tolerance_ends_when_the_arrivals_first_congress_ends(root, monkeypatch):
    utc = roster.datetime.timezone.utc
    monkeypatch.setattr(roster, '_now', lambda: roster.datetime.datetime(2027, 1, 3, 16, 59, tzinfo=utc))
    assert roster.arrivals(root) == RULED_HERE
    monkeypatch.setattr(roster, '_now', lambda: roster.datetime.datetime(2027, 1, 3, 17, 0, tzinfo=utc))
    assert roster.arrivals(root) == set()           # the media gate is still REJECTED: the date ended it
    covered = [n for n in CURRENT if n not in RULED_HERE]
    assert roster.drift(CURRENT, covered, root)[2] == RULED_HERE


def test_a_ruled_arrival_without_a_seating_date_is_not_tolerated(tmp_path):
    os.makedirs(tmp_path / 'data' / 'engine')
    rows = [dict(r) for r in ROWS]
    del rows[1]['term_start']                        # Aisha Wahab
    (tmp_path / 'data' / 'engine' / 'roster.json').write_text(json.dumps(
        {'schema': roster.SCHEMA, 'members': rows, 'departed': DEPARTED}), encoding='utf-8')
    receipt(str(tmp_path), {'status': 'REJECTED'})
    assert roster.arrivals(str(tmp_path)) == {'Everton Blair'}
