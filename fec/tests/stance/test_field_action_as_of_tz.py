"""lane/as-of-tz: every comparison of a LOCAL calendar date (paths.today(), an as_of) with a UTC stamp goes through
paths.utc_instant.  M7 attempt 10b: build_rank_honors' as_of 2026-10-26 (local) met the same run's admissions
checked_at 2026-10-27T03:23Z (23:23 EDT on 10-26); slicing the stamp to its UTC date refused the run as a backtest.
US Eastern is pinned through paths.LOCAL_ZONE so the tests hold on any host."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
import paths
import audit_collection
from stance import build_field_action_evidence as FAE

EASTERN = ZoneInfo('America/New_York')
ATTEMPT_10B_STAMP = '2026-10-27T03:23:08.208756+00:00'      # 2026-10-26 23:23 EDT, this run's own admissions step
GUARD = 'As-of precedes accepted source snapshot; historical backtesting unsupported'


@pytest.fixture(autouse=True)
def eastern(monkeypatch):
    monkeypatch.setattr(paths, 'LOCAL_ZONE', EASTERN)


# ---- the helper ------------------------------------------------------------------------------------------------------

def test_local_day_maps_to_its_local_midnight_in_utc_across_dst():
    assert paths.utc_instant(date(2026, 10, 27)) == datetime(2026, 10, 27, 4, tzinfo=timezone.utc)      # EDT
    assert paths.utc_instant('2026-11-02') == datetime(2026, 11, 2, 5, tzinfo=timezone.utc)              # EST


def test_stamps_map_to_their_instant_z_and_naive_read_as_utc():
    want = datetime(2026, 10, 27, 3, 23, 8, tzinfo=timezone.utc)
    for stamp in ('2026-10-27T03:23:08+00:00', '2026-10-27T03:23:08Z', '2026-10-27T03:23:08',
                  '2026-10-26T23:23:08-04:00', datetime(2026, 10, 27, 3, 23, 8)):
        assert paths.utc_instant(stamp) == want


def test_host_zone_default_reads_local_wall_time(monkeypatch):
    monkeypatch.setattr(paths, 'LOCAL_ZONE', None)
    assert paths.utc_instant('2026-10-26') == datetime(2026, 10, 26).astimezone().astimezone(timezone.utc)


# ---- site 1: build_field_action_evidence.build_evidence (admissions -> rank honors) ----------------------------------

def build_evidence(monkeypatch, checked_at, as_of):
    """Runs build_evidence up to the guard; returns True when it got past it."""
    class Snapshot:
        def json(self, path):
            return {'cats': list(FAE.BR.CATEGORIES), 'matrix': {'Member': {}},
                    'source_contract': {'schema': 'adjudicated-label-inputs-v1', 'inputs_sha256': dict.fromkeys(
                        ('archive_leg.json', 'legislation_routing_audit.json', 'vote_category_lean.json',
                         'bill_repository_live.json'), 'ok')}}

    class PastGuard(Exception):
        pass

    def past_guard(*args, **kwargs):
        raise PastGuard

    monkeypatch.setattr(FAE, 'load_roster', lambda snapshot: {'Member': {}})
    monkeypatch.setattr(FAE, '_require_hash', lambda *args: None)
    monkeypatch.setattr(FAE, '_admissions', lambda snapshot, counts=None: {'checked_at': checked_at})
    monkeypatch.setattr(FAE, 'legislative_actions', past_guard)
    with pytest.raises(PastGuard):
        FAE.build_evidence(Snapshot(), as_of)
    return True


def test_rank_honors_at_2323_eastern_accepts_its_own_utc_next_day_snapshot(monkeypatch):
    assert build_evidence(monkeypatch, ATTEMPT_10B_STAMP, '2026-10-26')       # the exact attempt-10b values


def test_rank_honors_just_after_local_midnight_accepts_snapshots_from_either_side(monkeypatch):
    assert build_evidence(monkeypatch, ATTEMPT_10B_STAMP, '2026-10-27')                 # stamped 23:23, step at 00:05
    assert build_evidence(monkeypatch, '2026-10-27T04:05:00+00:00', '2026-10-27')       # stamped 00:05 local


@pytest.mark.parametrize('checked_at, as_of', [
    ('2026-10-27T04:05:00+00:00', '2026-10-26'),      # stamped 00:05 local on 10-27: after as_of's local day ended
    (ATTEMPT_10B_STAMP, '2026-10-25'),
    (ATTEMPT_10B_STAMP, '2026-10-01'),
    (ATTEMPT_10B_STAMP, '2025-01-03'),
])
def test_rank_honors_genuinely_old_as_of_still_raises(monkeypatch, checked_at, as_of):
    with pytest.raises(ValueError, match=GUARD):
        build_evidence(monkeypatch, checked_at, as_of)


# ---- site 2: audit_collection.audit_db historical-archive collector freshness -----------------------------------------

def archive_freshness(tmp_path, monkeypatch, completed_at):
    monkeypatch.setattr(audit_collection, 'today', lambda: date(2026, 10, 27))      # local yesterday = 10-26
    database = tmp_path / 'media.db'
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE speeches(member TEXT,date TEXT,source TEXT,chamber TEXT,'
                           'package TEXT,nwords INTEGER,text TEXT)')
        connection.execute('CREATE TABLE iv_fetch_log(key TEXT PRIMARY KEY,status TEXT,ts TEXT)')
        connection.execute('INSERT INTO speeches VALUES (?,?,?,?,?,?,?)',
                           ('Member A', '2024-09-15', 'INTERVIEW', 'fox', 'https://www.foxnews.com/transcript/a', 3, 'a b c'))
    connection.close()
    receipts = tmp_path / 'receipts'
    receipts.mkdir()
    (receipts / 'fox.json').write_text(json.dumps({
        'schema': 'interview-source-receipt-v1', 'source': 'fox', 'status': 'COMPLETE', 'completed_at': completed_at,
        'freshness_mode': 'historical_archive', 'source_terminal_date': '2024-09-15'}), encoding='utf-8')
    return audit_collection.audit_db(database, receipts)['source_coverage']['Fox News']['collector_checked_through_yesterday']


def test_archive_checked_at_2030_eastern_two_days_ago_is_not_through_yesterday(tmp_path, monkeypatch):
    # 2026-10-26T00:30Z is 20:30 EDT on 10-25: its UTC date (10-26) used to count as "checked through yesterday".
    assert archive_freshness(tmp_path, monkeypatch, '2026-10-26T00:30:00+00:00') is False


def test_archive_checked_just_after_local_midnight_yesterday_is_through_yesterday(tmp_path, monkeypatch):
    assert archive_freshness(tmp_path, monkeypatch, '2026-10-26T04:30:00+00:00') is True     # 00:30 EDT 10-26
