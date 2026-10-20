"""MS NOW archive walk (fetch_interviews.run_msnow): newest-first, caught-up early stop, budget.

Incident 2026-10-18: the weekly `interviews: MS NOW` step hit its 3600 s timeout again.  The old walk
read the WHOLE WordPress archive oldest-first (215 pages, ~660 MB) on every run only to find zero new
posts, and printed nothing unless a page produced member turns, so a killed run left no diagnosis.
The walk now goes newest-first, stops at the first page that holds nothing unseen (when the previous
walk is known to have left no gap), prints one line per page, and ends on a wall-clock budget below the
callers' 3600 s with a PARTIAL receipt instead of being killed.

Everything here is offline: a scripted paged WordPress API stands in for ms.now, and the real run_msnow
runs against a private SQLite file and receipt directory.
"""
import ast
import json
import sqlite3
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit

import pytest

FEC = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(FEC))
from members import fetch_interviews as interviews

PER_PAGE = 50


class Site:
    """A scripted /wp-json/wp/v2/transcript endpoint: ids 1..n, id order == date order."""

    def __init__(self, count):
        self.posts = [self.post(i) for i in range(1, count + 1)]
        self.requests = []
        self.fail_pages = {}
        self.tick = lambda: None

    @staticmethod
    def post(i):
        return {'id': i, 'date': '2020-01-01T00:00:00' if i < 1000 else '2024-01-01T00:00:00',
                'link': 'https://www.ms.now/transcripts/post-%d' % i,
                'content': {'rendered': '<p>JANE DOE: transcript body %d</p>' % i}}

    def publish(self, *ids):
        self.posts += [self.post(i) for i in ids]

    def get(self, url, tries=3):
        self.requests.append(url)
        self.tick()
        query = parse_qs(urlsplit(url).query)
        page, descending = int(query['page'][0]), query['order'][0] == 'desc'
        if page in self.fail_pages:
            raise self.fail_pages[page]
        ordered = sorted(self.posts, key=lambda p: p['id'], reverse=descending)
        chunk = ordered[(page - 1) * PER_PAGE:page * PER_PAGE]
        if not chunk:   # WordPress answers 400 rest_post_invalid_page_number past the last page
            raise HTTPError(url, 400, 'invalid page', {}, None)
        return json.dumps(chunk)

    def pages_requested(self):
        return [int(parse_qs(urlsplit(u).query)['page'][0]) for u in self.requests]

    def orders_requested(self):
        return {parse_qs(urlsplit(u).query)['order'][0] for u in self.requests}


@pytest.fixture
def world(monkeypatch, tmp_path):
    site = Site(120)   # 3 pages of 50/50/20
    monkeypatch.setattr(interviews, 'B', str(tmp_path))
    monkeypatch.setattr(interviews, 'DB', str(tmp_path / 'media.db'))
    monkeypatch.setattr(interviews, 'PAUSE', 0)
    monkeypatch.setattr(interviews, 'get', site.get)
    monkeypatch.setattr(interviews, 'parse_turns',
                        lambda text: [('Test Member', 'a spoken sentence with plenty of words in it ok')])
    receipt = tmp_path / 'data' / 'engine' / 'interview_source_receipts' / 'msnow.json'

    def seen(*ids):
        """Pretend an earlier run already collected these post ids."""
        con = interviews.db()
        con.executemany('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)',
                        [('msnow:%d' % i, 'ok', '2026-10-16T00:00:00') for i in ids])
        con.commit(); con.close()

    def prior_receipt(status, **extra):
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(json.dumps({'schema': 'interview-source-receipt-v1', 'status': status, **extra}))

    def forget(*ids):
        """Someone deletes these posts' log rows to force a re-collect."""
        con = interviews.db()
        con.executemany('DELETE FROM iv_fetch_log WHERE key = ?', [('msnow:%d' % i,) for i in ids])
        con.commit(); con.close()

    def query(sql):
        con = sqlite3.connect(tmp_path / 'media.db')
        try:
            return con.execute(sql).fetchall()
        finally:
            con.close()

    def logged():
        return dict(query("SELECT key, status FROM iv_fetch_log WHERE key LIKE 'msnow:%'"))

    def stored_links():
        return sorted(r[0] for r in query('SELECT package FROM speeches'))

    return SimpleNamespace(site=site, seen=seen, forget=forget, prior_receipt=prior_receipt, logged=logged,
                           stored_links=stored_links, receipt_path=receipt,
                           receipt=lambda: json.loads(receipt.read_text()))


def test_walk_is_newest_first_and_stops_at_the_first_fully_seen_page(world):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE')
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1]            # was: all 3 pages, every run
    assert world.site.orders_requested() == {'desc'}
    receipt = world.receipt()
    assert (receipt['status'], receipt['archive_pages_checked'], receipt['new_posts_checked']) == ('COMPLETE', 1, 0)
    assert receipt['archive_page_failures'] == 0


def test_new_posts_on_page_one_are_still_captured_then_the_next_seen_page_ends_the_walk(world):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE')
    world.site.publish(121, 122, 123)
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2]         # page 1 held 3 unseen, page 2 held none
    assert world.stored_links() == ['https://www.ms.now/transcripts/post-%d' % i for i in (121, 122, 123)]
    assert {world.logged()['msnow:%d' % i] for i in (121, 122, 123)} == {'ok'}
    assert world.receipt()['new_posts_checked'] == 3
    assert world.receipt()['accepted_turns'] == 3


def test_every_unseen_post_is_processed_even_when_several_pages_are_new(world):
    world.seen(*range(1, 21))                              # only the oldest 20 are known
    world.prior_receipt('COMPLETE')
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2, 3]      # pages 1 and 2 are all-new; page 3 is fully seen
    assert len(world.stored_links()) == 100
    assert set(world.logged().values()) == {'ok'} and len(world.logged()) == 120


@pytest.mark.parametrize('prior', [None, 'PARTIAL'])
def test_no_proof_of_a_gap_free_previous_walk_means_a_full_walk(world, prior):
    """Early stop is only safe after a COMPLETE walk.  A missing or PARTIAL receipt can hide an
    unseen post deeper than the first seen page, so the walk must reach the end of the archive."""
    world.seen(*(i for i in range(1, 121) if i != 5))      # post 5 sits on the LAST page
    if prior:
        world.prior_receipt(prior)
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2, 3, 4]    # page 4 is the empty past-the-end probe
    assert world.stored_links() == ['https://www.ms.now/transcripts/post-5']
    assert world.receipt()['status'] == 'COMPLETE'
    # ...and that COMPLETE walk is what re-enables the cheap path next time
    world.site.requests.clear()
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1]


def test_a_failed_page_leaves_a_partial_receipt_and_the_next_run_walks_fully(world):
    world.seen(*range(1, 21))
    world.prior_receipt('COMPLETE')
    world.site.fail_pages[2] = HTTPError('u', 503, 'unavailable', {}, None)
    assert interviews.run_msnow() is False
    assert world.receipt()['status'] == 'PARTIAL' and world.receipt()['archive_page_failures'] == 1
    assert not any(world.logged().get('msnow:%d' % i) for i in range(51, 71))   # page 2's posts untouched

    world.site.fail_pages.clear()
    world.site.requests.clear()
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2, 3, 4]    # PARTIAL disabled the early stop
    assert world.logged()['msnow:60'] == 'ok'              # the page that failed is now collected


def test_receipt_counts_the_msnow_posts_the_log_holds_and_only_those(world):
    world.seen(*range(1, 11))
    con = interviews.db()   # other sources' rows share iv_fetch_log and must not inflate the count
    con.execute('INSERT OR REPLACE INTO iv_fetch_log VALUES (?,?,?)', ('cnn:abc', 'ok', '2026-10-16T00:00:00'))
    con.commit(); con.close()
    assert interviews.run_msnow() is True
    assert world.receipt()['known_ok_posts'] == 120


def test_deleted_log_rows_force_a_full_walk_that_collects_them_again(world):
    """The COMPLETE receipt proves the last walk left no gap, not that the log still holds what it
    collected.  Deleting msnow: rows to force a re-collect must not be answered by a one-page walk
    and a receipt that keeps saying COMPLETE."""
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE', known_ok_posts=120)
    world.forget(5, 60)                                    # post 5 is on the last page, post 60 on page 2
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2, 3, 4]    # was: [1] and the deleted posts never came back
    assert world.stored_links() == ['https://www.ms.now/transcripts/post-%d' % i for i in (5, 60)]
    assert {world.logged()['msnow:5'], world.logged()['msnow:60']} == {'ok'}
    assert world.receipt()['known_ok_posts'] == 120
    world.site.requests.clear()
    assert interviews.run_msnow() is True                  # the repaired log is trusted again
    assert world.site.pages_requested() == [1]


@pytest.mark.parametrize('recorded', [120, 100])
def test_a_log_holding_at_least_what_the_receipt_recorded_keeps_the_cheap_path(world, recorded):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE', known_ok_posts=recorded)
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1]
    assert world.receipt()['known_ok_posts'] == 120


def test_a_receipt_without_the_count_keeps_the_early_stop(world):
    """The live msnow.json predates known_ok_posts: it is COMPLETE and the log holds every post, so
    refusing the early stop would cost a 215-page walk on the first run after the deploy."""
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE')
    assert 'known_ok_posts' not in json.loads(world.receipt_path.read_text())
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1]
    assert world.receipt()['known_ok_posts'] == 120        # the next receipt carries it


def test_an_unreadable_count_is_not_trusted(world):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE', known_ok_posts='lots')
    assert interviews.run_msnow() is True
    assert world.site.pages_requested() == [1, 2, 3, 4]


def test_the_full_walk_names_the_missing_rows(world, capsys):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE', known_ok_posts=120)
    world.forget(7)
    assert interviews.run_msnow() is True
    out = capsys.readouterr().out
    assert 'holds 119 msnow posts' in out and 'recorded 120' in out and 'full archive' in out


@pytest.fixture
def clock(monkeypatch, world):
    """Each page request costs 40 simulated seconds; time.sleep is a no-op."""
    now = [0.0]
    monkeypatch.setattr(interviews, 'time', SimpleNamespace(monotonic=lambda: now[0], sleep=lambda s: None))
    world.site.tick = lambda: now.__setitem__(0, now[0] + 40)
    return now


def test_budget_exhaustion_stops_between_pages_with_a_partial_receipt(world, clock, capsys):
    assert interviews.run_msnow(budget=100) is False       # same contract as run_cnn(budget=): False => --strict exit 2
    assert world.site.pages_requested() == [1, 2, 3]        # t=0,40,80 are inside the budget; t=120 is not
    out = capsys.readouterr().out
    assert 'MSNOW BUDGET EXHAUSTED after 100s at page 4' in out
    receipt = world.receipt()
    assert receipt['status'] == 'PARTIAL'
    assert receipt['walk_stop'] == 'budget'
    assert receipt['archive_pages_checked'] == 3
    assert len(world.logged()) == 120                       # work done before the stop is flushed to the log


def test_a_budget_stop_is_not_trusted_by_the_next_run(world, clock):
    world.seen(*range(1, 51))                               # the first page was finished before the stop
    world.prior_receipt('PARTIAL')
    assert interviews.run_msnow(budget=10_000) is True
    assert world.site.pages_requested() == [1, 2, 3, 4]     # page 1 is fully seen but the walk goes on
    assert len(world.logged()) == 120


def test_default_budget_sits_below_every_caller_timeout(world, clock, monkeypatch):
    assert 0 < interviews.MSNOW_DEFAULT_BUDGET_S < 3600     # weekly_refresh, daily_media_refresh, refresh_table
    monkeypatch.setattr(interviews, 'MSNOW_DEFAULT_BUDGET_S', 50)
    assert interviews.run_msnow() is False                  # no argument => the default budget applies
    assert world.receipt()['walk_stop'] == 'budget'


def test_caught_up_runs_are_not_budget_limited(world, clock):
    world.seen(*range(1, 121))
    world.prior_receipt('COMPLETE')
    assert interviews.run_msnow(budget=1) is True
    assert world.receipt()['walk_stop'] == 'caught_up'


def test_every_page_prints_a_progress_line_even_when_it_adds_no_turns(world, capsys):
    world.seen(*range(1, 121))
    assert interviews.run_msnow() is True                   # no prior receipt: full walk, 3 pages
    lines = [l for l in capsys.readouterr().out.splitlines() if l.startswith('msnow page ')]
    assert len(lines) == 3, lines
    assert lines[0].startswith('msnow page 1:') and '50 posts' in lines[0] and '0 new' in lines[0]


def test_cli_passes_the_budget_flag_to_the_leg_in_both_strict_and_lenient_modes():
    tree = ast.parse((FEC / 'members' / 'fetch_interviews.py').read_text(encoding='utf-8-sig'))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'run_msnow']
    assert len(calls) == 2
    for call in calls:
        assert [k.arg for k in call.keywords] == ['budget']
        assert ast.unparse(call.keywords[0].value) == '_budget'
