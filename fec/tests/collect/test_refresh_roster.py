"""fec/collect/refresh_roster.py pure logic: scope, names, cross-check, delta, the FEC money fence (synthetic data only)."""
import os
import sys

FEC = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, FEC)
import roster  # noqa: E402
from collect import refresh_roster as RR  # noqa: E402


def person(b, first, last, typ, state, start, end='2027-01-03', district=None, party='Democrat', full=None, fec=(), nick=None):
    t = {'type': typ, 'start': start, 'end': end, 'state': state, 'party': party}
    if typ == 'rep':
        t['district'] = district
    return {'id': {'bioguide': b, 'fec': list(fec)}, 'name': {'first': first, 'last': last, 'official_full': full, 'nickname': nick},
            'terms': [t]}


def test_scope_rule_keeps_dc_and_pr_and_drops_the_four_territories():
    assert roster.in_scope('sen', 'SC') and roster.in_scope('rep', 'DC') and roster.in_scope('rep', 'PR')
    assert not any(roster.in_scope('rep', s) for s in ('VI', 'AS', 'GU', 'MP'))


def test_display_names_follow_pauls_rulings_and_the_rule():
    assert RR.display_name(person('G000608', 'Darline', 'Graham Nordone', 'sen', 'SC', '2026-07-14', full='Darline Graham')) == 'Darline Graham'
    assert RR.display_name(person('B001328', 'Everton', 'Blair', 'rep', 'GA', '2026-09-01', district=13, full='Everton Blair Jr.')) == 'Everton Blair'
    assert RR.display_name(person('W000832', 'Aisha', 'Wahab', 'rep', 'CA', '2026-09-02', district=14)) == 'Aisha Wahab'
    assert RR.display_name(person('X1', 'Nicholas', 'Begich', 'rep', 'AK', '2025-01-03', district=0, full='Nicholas J. Begich III')) == 'Nicholas Begich'


def test_delta_finds_departure_arrival_and_party_change():
    installed = {'members': [
        {'member': 'Lindsey Graham', 'bioguide': 'G000359', 'chamber': 'Senate', 'state': 'SC', 'district': None, 'party': 'Republican',
         'official_full': 'Lindsey Graham'},
        {'member': 'Tina Smith', 'bioguide': 'S001203', 'chamber': 'Senate', 'state': 'MN', 'district': None, 'party': 'Democrat',
         'official_full': 'Tina Smith'}]}
    people = {'S001203': person('S001203', 'Tina', 'Smith', 'sen', 'MN', '2021-01-03', party='Independent', full='Tina Smith'),
              'G000608': person('G000608', 'Darline', 'Graham Nordone', 'sen', 'SC', '2026-07-14', party='Republican', full='Darline Graham')}
    hist = {'G000359': person('G000359', 'Lindsey', 'Graham', 'sen', 'SC', '2021-01-03', end='2026-07-11', party='Republican')}
    d = RR.compute_delta(installed, people, hist)
    assert [(x['member'], x['departed_on']) for x in d['departures']] == [('Lindsey Graham', '2026-07-11')]
    assert [(x['member'], x['term_start'], x['chamber']) for x in d['arrivals']] == [('Darline Graham', '2026-07-14', 'Senate')]
    assert d['party_changes'] == [{'member': 'Tina Smith', 'bioguide': 'S001203', 'from': 'Democrat', 'to': 'Independent'}]
    assert d['name_changes'] == [] and d['seat_changes'] == []


def test_cross_check_reports_a_member_the_clerk_does_not_list():
    people = {'A1': person('A1', 'A', 'One', 'rep', 'GA', '2025-01-03', district=1),
              'B1': person('B1', 'B', 'Two', 'sen', 'GA', '2025-01-03')}
    csv_rows = [{'bioguide_id': 'A1', 'type': 'rep', 'state': 'GA', 'fec_ids': ''},
                {'bioguide_id': 'B1', 'type': 'sen', 'state': 'GA', 'fec_ids': ''}]
    assert RR.cross_check(people, {'A1': {}}, {'B1': 'GA'}, csv_rows) == []
    bad = RR.cross_check(people, {}, {'B1': 'GA'}, csv_rows)
    assert len(bad) == 1 and 'clerk' in bad[0]
    csv_rows[0]['fec_ids'] = 'H0GA01000'
    assert any('fec_ids' in b for b in RR.cross_check(people, {'A1': {}}, {'B1': 'GA'}, csv_rows))


def test_fec_fence_holds_unapproved_changes_and_new_ids():
    old = [{'bioguide_id': 'K1', 'fec_ids': 'H2XX00001'}, {'bioguide_id': 'K2', 'fec_ids': 'H2XX00002'},
           {'bioguide_id': 'K3', 'fec_ids': 'H2XX00003'}]
    new = [{'bioguide_id': 'K1', 'fec_ids': 'H2XX00001,S6XX00001'}, {'bioguide_id': 'K2', 'fec_ids': 'H2XX00002,S6XX00002'},
           {'bioguide_id': 'K3', 'fec_ids': 'H2XX00003'}, {'bioguide_id': 'N1', 'fec_ids': 'H6XX00009', 'full_name': 'New One'}]
    approvals = {'approved': [{'bioguide': 'K1', 'fec_ids': ['H2XX00001', 'S6XX00001']}]}
    write, held = RR.fec_fence(old, new, approvals, [{'bioguide': 'N1'}])
    assert write == {'K1': 'H2XX00001,S6XX00001', 'K2': 'H2XX00002', 'K3': 'H2XX00003', 'N1': ''}
    assert sorted(h['bioguide'] for h in held) == ['K2', 'N1']


def test_congestion_and_desk_keep_departed_history():
    delta = {'departures': [{'member': 'Old', 'bioguide': 'O1', 'departed_on': '2026-07-11', 'reason': 'x'}],
             'arrivals': [{'member': 'New', 'bioguide': 'N1', 'chamber': 'House', 'state': 'GA', 'district': 13, 'party': 'Democrat',
                           'term_start': '2026-09-01'}]}
    cong = RR.new_congestion([{'member': 'Old', 'bioguide': 'O1', 'chamber': 'Senate'}, {'member': 'Kim', 'bioguide': 'K1'}], delta)
    assert [r['member'] for r in cong] == ['Kim', 'New'] and cong[1]['money_source_status'].startswith('NEW_MEMBER')
    census = [{'Geography_Level': 'Congressional District', 'State_Abbr': 'GA', 'District_Code': '13',
               'Geography_Name': 'Congressional District 13 (119th Congress), Georgia', 'Pct_OwnerOcc_With_Mortgage': 1,
               'Pct_Mortgaged_CostBurden_30plus': 2, 'Median_Household_Income': 3, 'Per_Capita_Income': 4,
               'Pct_Finance_RealEstate': 5, 'Median_Age': 6, 'Poverty_Rate_Pct': 7, 'Pop_1yr_and_over': 8, 'CBP_Establishments': 9}]
    desk = RR.new_desk_src({'weights': {}, 'members': [{'name': 'Old'}, {'name': 'Kim'}]}, delta, census)
    assert [m['name'] for m in desk['members']] == ['Kim', 'New']
    assert desk['departed'] == [{'name': 'Old', 'departed': '2026-07-11', 'departed_reason': 'x'}]
    assert desk['members'][1]['district'].startswith('Congressional District 13') and desk['members'][1]['thin_evidence']


def test_an_approved_arrival_moves_from_pending_review_to_awaiting_money():
    old = [{'member': 'New', 'bioguide': 'N1', 'money_source_status': 'NEW_MEMBER_FEC_IDS_PENDING_PAUL_REVIEW'},
           {'member': 'Held', 'bioguide': 'N2', 'money_source_status': 'NEW_MEMBER_FEC_IDS_PENDING_PAUL_REVIEW'}]
    out = RR.new_congestion(old, {'departures': [], 'arrivals': []}, {'N1': 'H6XX00009', 'N2': ''})
    assert [r['money_source_status'] for r in out] == ['NEW_MEMBER_AWAITING_FEC_MONEY_REFRESH', 'NEW_MEMBER_FEC_IDS_PENDING_PAUL_REVIEW']


def test_an_arrival_with_no_candidate_id_is_labelled_so():
    out = RR.new_congestion([{'member': 'D', 'bioguide': 'G1', 'money_source_status': 'NEW_MEMBER_FEC_IDS_PENDING_PAUL_REVIEW'}],
                            {'departures': [], 'arrivals': []}, {'G1': ''}, {'G1'})
    assert out[0]['money_source_status'] == 'NEW_MEMBER_NO_FEC_ID'


def test_every_file_the_refresh_writes_reads_back_identically_under_the_cp1252_default(tmp_path):
    """~250 readers json.load(open(path)) with no encoding= (cp1252 here).  A new or ASCII file must stay ASCII-escaped,
    and a rewrite keeps the installed file's byte style (compact / newline / CRLF)."""
    import json, csv
    doc = [{'member': 'Nydia Velázquez'}, {'member': 'Jesús García'}, {'member': 'André Carson'}]
    new = tmp_path / 'new.json'
    RR.dump_json(str(new), doc)
    assert json.load(open(new, encoding='cp1252')) == doc == json.load(open(new, encoding='utf-8'))
    compact = tmp_path / 'compact.json'
    compact.write_bytes(json.dumps([{'member': 'x'}]).encode('ascii'))           # congestion.json's installed style
    RR.dump_json(str(compact), doc)
    raw = compact.read_bytes()
    assert all(b < 128 for b in raw) and b'\n' not in raw and json.load(open(compact, encoding='cp1252')) == doc
    leg = tmp_path / 'legislators.csv'
    leg.write_bytes(b'bioguide_id,full_name\r\nX1,Old\r\n')                        # fec/legislators.csv is CRLF, UTF-8, no BOM
    RR.write_csv(str(leg), ['bioguide_id', 'full_name'], [{'bioguide_id': 'V000081', 'full_name': 'Nydia M. Velázquez'}])
    assert leg.read_bytes() == 'bioguide_id,full_name\r\nV000081,Nydia M. Velázquez\r\n'.encode('utf-8')
    assert list(csv.DictReader(open(leg, encoding='utf-8')))[0]['full_name'] == 'Nydia M. Velázquez'


def test_fence_holds_ids_on_a_row_the_installed_file_never_had():
    write, held = RR.fec_fence([{'bioguide_id': 'K1', 'fec_ids': ''}],
                               [{'bioguide_id': 'K1', 'fec_ids': ''}, {'bioguide_id': 'T9', 'fec_ids': 'H6GU00001', 'full_name': 'Terr'}],
                               {'approved': []}, [])
    assert write['T9'] == '' and [h['bioguide'] for h in held] == ['T9']


# ---- contents-API fetch (offline: urlopen is mocked) ----
SHA = '15530b7d621009eb5fc7eda67f75194d7d91f8c1'


class _Resp:
    def __init__(self, body=b'x'):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self):
        return self.body


def _capture(monkeypatch, outcome=None):
    seen = []

    def fake(req, timeout=None):
        seen.append(req)
        if isinstance(outcome, Exception):
            raise outcome
        return _Resp(b'yaml-bytes')
    monkeypatch.setattr(RR.urllib.request, 'urlopen', fake)
    monkeypatch.setattr(RR.time, 'sleep', lambda s: None)
    return seen


def test_pinned_file_uses_the_contents_api_with_raw_accept_and_the_sha(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    seen = _capture(monkeypatch)
    assert RR.fetch_pinned('committee-membership-current.yaml', SHA) == b'yaml-bytes'
    r = seen[0]
    assert r.full_url == ('https://api.github.com/repos/unitedstates/congress-legislators/contents/'
                          'committee-membership-current.yaml?ref=' + SHA)
    assert r.get_header('Accept') == 'application/vnd.github.raw'
    assert r.get_header('User-agent')
    assert not r.has_header('Authorization')


def test_token_is_sent_only_when_the_env_var_is_set_and_only_to_the_api(monkeypatch):
    monkeypatch.setenv('GITHUB_TOKEN', 'tok123')
    seen = _capture(monkeypatch)
    RR.fetch_pinned('LICENSE', SHA)
    RR.fetch(RR.URL_CLERK)
    assert seen[0].get_header('Authorization') == 'Bearer tok123'
    assert not seen[1].has_header('Authorization')


def test_rate_limit_403_raises_once_without_retry_and_classes_as_unavailable(monkeypatch):
    import email.message
    h = email.message.Message()
    h['X-RateLimit-Remaining'] = '0'
    err = RR.urllib.error.HTTPError('u', 403, 'rate limited', h, None)
    seen = _capture(monkeypatch, err)
    try:
        RR.fetch_pinned('LICENSE', SHA)
        assert False, 'expected RuntimeError'
    except RuntimeError as e:
        assert 'rate limit' in str(e)
    assert len(seen) == 1          # no retries burned on a limit that will not lift


# ---- roster staleness for the weekly status (offline, tmp root) ----
def _stale(tmp_path, as_of, receipt='SOURCE_UNAVAILABLE', raw=None):
    import datetime
    import json
    d = tmp_path / 'data' / 'engine'
    d.mkdir(parents=True)
    doc = {} if as_of is None else {'as_of': as_of}
    doc['source'] = {'commit': 'abc'}
    (d / 'roster.json').write_text(raw if raw is not None else json.dumps(doc), encoding='utf-8')
    (d / 'roster_refresh_receipt.json').write_text(json.dumps({'status': receipt}), encoding='utf-8')
    now = datetime.datetime(2026, 10, 25, tzinfo=datetime.timezone.utc)
    return roster.staleness(str(tmp_path), now=now)


def test_13_day_old_snapshot_is_not_stale(tmp_path):
    s = _stale(tmp_path, '2026-10-12T00:00:00+00:00')
    assert s['roster_stale'] is False and s['roster_snapshot_age_days'] == 13
    assert s['roster_snapshot'] == 'abc' and s['roster_refresh_receipt_status'] == 'SOURCE_UNAVAILABLE'


def test_15_day_old_snapshot_is_stale(tmp_path):
    s = _stale(tmp_path, '2026-10-10T00:00:00+00:00')
    assert s['roster_stale'] is True and s['roster_snapshot_age_days'] == 15


def test_missing_or_unparseable_date_is_stale_with_the_reason(tmp_path):
    assert 'KeyError' in _stale(tmp_path / 'a', None)['roster_stale_reason']
    s = _stale(tmp_path / 'b', 'not-a-date')
    assert s['roster_stale'] is True and 'unparseable' in s['roster_stale_reason']


# ---- csv via gh-pages contents API; unexpected source failures are SOURCE_UNAVAILABLE ----
def test_csv_is_resolved_to_a_gh_pages_sha_then_fetched_pinned(monkeypatch):
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    urls = []

    def fake_fetch(url, timeout=120, accept=None):
        urls.append((url, accept))
        return b'{"sha": "' + SHA.encode() + b'"}' if url == RR.URL_GHPAGES_HEAD else b'csv-bytes'
    monkeypatch.setattr(RR, 'fetch', fake_fetch)
    assert RR.fetch_csv() == (b'csv-bytes', SHA)
    assert urls[1] == ('https://api.github.com/repos/unitedstates/congress-legislators/contents/legislators-current.csv?ref=' + SHA,
                       'application/vnd.github.raw')
    assert not any('github.io' in u or 'githubusercontent' in u for u, _ in urls)


def test_source_unavailable_records_the_receipt_and_keeps_exit_semantics(monkeypatch):
    import datetime
    seen = []
    monkeypatch.setattr(RR, 'finish', lambda rec, run_dir, held=None: seen.append(rec))
    now = datetime.datetime.now().astimezone()
    fresh = {'built_at': (now - datetime.timedelta(days=2)).isoformat()}
    old = {'built_at': (now - datetime.timedelta(days=RR.STALE_DAYS + 5)).isoformat()}
    rec = {}
    assert RR.source_unavailable(rec, 'd', fresh, OSError('reset')) == 0
    assert rec['status'] == 'SOURCE_UNAVAILABLE' and 'reset' in rec['error'] and seen
    assert RR.source_unavailable({}, 'd', old, OSError('reset')) == 1
