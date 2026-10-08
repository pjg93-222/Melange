"""Unit tests: parser pitfalls, fallback/served cycle, pagination, dedup, missing-vs-zero, negatives, metadata, transport politeness."""
import hashlib, json, sys
from email.utils import formatdate
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osc import parsers as P  # noqa: E402
from osc.extract import Extractor  # noqa: E402
from osc.fetch import Fetcher, is_challenge, parse_retry_after  # noqa: E402
from osc.util import atomic_write_bytes, canonical_url, count, money, pct, replace_with_retry, url_key  # noqa: E402

FIX = Path(__file__).parent / 'fixtures'
OVERVIEW = (FIX / 'national-overview-2024.html').read_bytes()
ABA = (FIX / 'aba-recipients-2024.html').read_bytes()


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def make_fetcher(tmp_path, fn, **kw):
    clk = kw.pop('clock', None) or Clock()
    f = Fetcher(tmp_path, request_fn=fn, sleep=clk.sleep, clock=clk.now, wall=lambda: 1_000_000.0, min_interval=kw.pop('min_interval', 1.0), **kw)
    return f, clk


# ---- money / counts ------------------------------------------------------------------------
def test_money_signed_blank_and_zero():
    assert money('$1,464,999') == 1464999
    assert money('-$5,400') == -5400 and money('$-5,400') == -5400 and money('($5,400)') == -5400 and money('−$12') == -12
    assert money('$0') == 0                      # published zero stays zero
    assert money('') is None and money('N/A') is None and money(None) is None and money('—') is None  # blank is never 0
    assert money('$1,234.50') == 1234.5
    with pytest.raises(ValueError):
        money('abc')
    assert count('2,795') == 2795 and count(15) == 15 and count('') is None
    assert pct('44.27%') == 44.27 and pct('N/A') is None


def test_canonical_url_dedup_key():
    a = canonical_url('https://www.opensecrets.org/industries/totals?ind=F03&cycle=2026')
    b = canonical_url('/industries/totals?cycle=2026&ind=F03#frag')
    assert a == b and url_key(a) == url_key(b)


# ---- parser pitfalls on real captured pages ------------------------------------------------------
def test_overview_fixture_values_and_metadata():
    o = P.parse_overview(OVERVIEW, 2024)
    assert o['served_cycle'] == 2024 and o['offices'] == ['Presidential', 'House', 'Senate'] and len(o['rows']) == 9
    v = {(r['office'], r['party']): r for r in o['rows']}
    assert (v['Presidential', 'All']['from_pacs_usd'], v['House', 'All']['from_pacs_usd'], v['Senate', 'All']['from_pacs_usd']) == (1187730, 422640137, 87386285)
    assert (v['Presidential', 'All']['from_individuals_usd'], v['House', 'All']['from_individuals_usd'], v['Senate', 'All']['from_individuals_usd']) == (1802512049, 1247529449, 1183616110)
    assert v['Presidential', 'All']['n_candidates'] == 15 and v['House', 'All']['n_candidates'] == 2795   # int vs '2,795'
    assert o['meta']['release_dates'] == ['September 16, 2025'] and P.iso_date(o['meta']['release_dates'][0]) == '2025-09-16'


def test_aba_recipients_hidden_label_pagination_and_independents():
    r = P.parse_pac_recipients(ABA, 'C00004275', 2024)
    assert r['served_cycle'] == 2024 and r['headline'] == {'total_usd': 2453999, 'to_democrats_usd': 838000, 'to_republicans_usd': 1600999}
    chambers = [x['chamber'] for x in r['recipients']]
    assert chambers.count('House') == 365 and chambers.count('Senate') == 29                    # UI paginates 10; data-collection has all
    assert r['recipients'][0]['candidate'] == 'Tony Gonzales (R-Texas)' and r['recipients'][0]['sort_name'] == 'Gonzales, Tony'   # hidden label not doubled
    assert r['chamber_summary'] == {'House|R': 1464999, 'House|D': 780500, 'Senate|R': 136000, 'Senate|D': 57500}
    sums = {}
    for x in r['recipients']:
        sums[(x['chamber'], x['party_group'])] = sums.get((x['chamber'], x['party_group']), 0) + x['amount_usd']
    assert sums[('Senate', 'Other')] == 15000                      # King 10,000 + Sinema 5,000: D/R is not all-party
    assert sums[('House', 'R')] == 1464999 and sums[('Senate', 'D')] == 57500
    assert any(x['amount_usd'] == 0 for x in r['recipients'])        # published $0 kept
    assert r['meta']['release_dates'] == ['February 06, 2025']


def test_data_collection_wins_over_paginated_html_and_fallback_to_html():
    rows = [{'PAC Name': f'<a href="/political-action-committees-pacs/p{i}/C0000000{i}/summary/2024">P{i}</a>', 'Total': '$1', 'To Democrats ': '$1', 'To Republicans': None}
            for i in range(1, 8)]
    visible = ''.join(f'<tr><td>P{i}</td></tr>' for i in range(1, 3))   # only 2 visible rows (pagination)
    html = ("<h2>x</h2><table data-collection='%s'><thead><tr><th>PAC Name</th><th>Total</th></tr></thead><tbody>%s</tbody></table>"
            % (json.dumps(rows).replace("'", '&#39;'), visible))
    t = P.extract_tables(P.soup_of(html))[0]
    assert t['source'] == 'data-collection' and len(t['rows']) == 7 and t['html_rows'] == 2
    assert 'To Democrats' in t['rows'][0]                              # trailing-space header key normalised
    bad = html.replace("data-collection='", "data-collection='{broken ")
    t2 = P.extract_tables(P.soup_of(bad))[0]
    assert t2['source'] == 'html' and t2['collection_error'] == 'unparseable_data_collection' and len(t2['rows']) == 2


def test_missing_cells_are_none_not_zero():
    hdr = ''.join(f'<th>{h}</th>' for h in ['Election Cycle', 'Total Contributions', 'Contributions from Individuals', 'Contributions from PACs', 'Soft/Outside Money',
                                          'Contributions to Democrats', 'Contributions to Republicans', 'Percentage to Democrats', 'Percentage to Republicans'])
    d = P.parse_legacy_totals(f'<table><thead><tr>{hdr}</tr></thead><tbody><tr><td>2008</td><td>$10</td><td>N/A</td><td></td><td>$0</td><td>$4</td><td>$6</td><td>40%</td><td>60%</td></tr></tbody></table>', 'F03')
    r = d['rows'][0]
    assert r['individual_usd'] is None and r['pac_usd'] is None and r['soft_outside_usd'] == 0 and r['democrat_pct'] == 40.0


def test_legacy_summary_negative_party_and_bold_cells():
    html = ("<select name='cycle'><option selected>2024</option></select><table data-collection='%s'><thead><tr><th>Representative</th><th>State</th><th>Amount</th></tr></thead></table>"
            % json.dumps([{'Representative': 'Quartey, Quaye (D-CA)', 'State': 'California', 'Amount': '-$5,400'},
                          {'Representative': 'Odd, Name (3-UT)', 'State': 'Utah', 'Amount': '$10'},
                          {'Representative': 'No Party', 'State': 'Utah', 'Amount': '$5'}]))
    r = P.parse_legacy_summary(html, 'F03', 2024, 'House')
    assert [x['amount_usd'] for x in r['rows']] == [-5400, 10, 5]
    assert [x['party_group'] for x in r['rows']] == ['D', 'Other', 'Unclassified'] and r['rows'][1]['party_code'] == '3'
    c = P.parse_legacy_contrib("<select name='cycle'><option selected>2024</option></select><table data-collection='%s'><thead><tr><th>Rank</th><th>Contributor</th></tr></thead></table>"
                               % json.dumps([{'Rank': 1, 'Contributor': 'X', 'Grand Total': '<b>$13,016,326</b>', 'Total to Candidates & Parties': '$365,756',
                                              'Total to Outside Spending Groups': '$12,650,400'}]), 'F03', 2024)
    assert c['rows'][0]['total_usd'] == 13016326


def test_served_cycle_not_assumed_from_request():
    html = "<select name='cycle'><option>2026</option><option selected>2024</option></select><p>numbers on this page are for the 2024 election cycle</p>"
    o = P.parse_overview(html, 2026)
    assert o['requested_cycle'] == 2026 and o['served_cycle'] == 2024 and o['meta']['cycle_menu'] == ['2026', '2024']


def test_lobby_main_widget_excluded_and_client_table_complete():
    html = ("<p>Industry spending $88,178,939 2026 reported lobbying Clients active 3</p><h2>Insurance clients by Client/Parent, 2026</h2>"
            "<table><tr><th>Client</th><th>Total spending</th></tr><tr><td>Property &amp; casualty insurance</td><td>$88,178,939</td></tr></table>"
            "<table><thead><tr><th>Client/Parent</th><th>Total</th></tr></thead><tbody>"
            "<tr><td><a href='/federal-lobbying/clients/a-b?client_id=1&amp;cycle=2026'>A B</a></td><td>$5</td></tr><tr><td>C</td><td>$7</td></tr><tr><td>D</td><td>$9</td></tr></tbody></table>")
    m = P.parse_lobby_main(html, 'F09', 2026)
    assert m['served_year'] == 2026 and m['clients_active'] == 3 and len(m['clients']) == 3
    assert m['top_client_widget']['label'] == 'Property & casualty insurance'         # captured but never a client row
    assert all(c['client'] != 'Property & casualty insurance' for c in m['clients'])
    assert m['clients'][0]['client_id'] == '1' and m['clients'][0]['client_slug'] == 'a-b'


def test_lobby_annual_and_client_split_exact_values():
    chart = json.dumps({'series': [{'name': 'Total spending', 'data': [{'category': '2025', 'value': 172752742.0}, {'category': '2026', 'value': 88178939.0}]}]})
    a = P.parse_lobby_annual(f"<div data-charts--line-chart-options-value='{chart}'></div>")
    assert a['annual'] == {2025: 172752742, 2026: 88178939}
    split = json.dumps({'series': [{'category': 'In-house operations', 'value': 2206000.0}, {'category': 'Outside firms', 'value': 518000.0}]})
    s = P.parse_client_split(f"<p>2026 total $2,988,000</p><div data-charts--single-stacked-bar-options-value='{split}'></div>")
    assert (s['in_house_usd'], s['outside_firms_usd'], s['client_year_total_usd']) == (2206000, 518000, 2988000)
    assert s['in_house_usd'] + s['outside_firms_usd'] != s['client_year_total_usd']   # preserved, not forced to reconcile


def test_org_search_exact_match_only():
    def row(n, i, oid):
        return f"<tr><td>Organization</td><td><a href='/orgs/{i}/summary?id={oid}'>{n}</a></td></tr>"
    one = P.parse_org_search('<table>' + row('Bank of America', 'boa', 'D000000090') + '<tr><td>PACs</td><td><a href="/x">Bank of America 2024</a></td></tr></table>', 'bank of AMERICA')
    assert one['status'] == 'matched_exact' and one['org_id'] == 'D000000090'
    amb = P.parse_org_search('<table>' + row('Acme', 'acme1', 'D000000001') + row('ACME', 'acme2', 'D000000002') + '</table>', 'Acme')
    assert amb['status'] == 'ambiguous_exact' and amb['org_id'] == ''
    none = P.parse_org_search('<table>' + row('Acme Corp', 'acme1', 'D000000001') + '</table>', 'Acme')
    assert none['status'] == 'no_exact_match'


# ---- fetcher: cache, bytes, dedup, failures ---------------------------------------------------------
def test_cache_byte_exact_dedup_and_rerun_costs_zero(tmp_path):
    body = b'<html>\r\nexact\xc3\xa9 bytes\n</html>'
    calls = []

    def fn(url):
        calls.append(url)
        return 200, {'Content-Type': 'text/html'}, body, url
    f, _ = make_fetcher(tmp_path, fn)
    urls = ['https://www.opensecrets.org/a?x=1&y=2', 'https://www.opensecrets.org/a?y=2&x=1', 'https://www.opensecrets.org/a?x=1&y=2#f']
    res = f.fetch_many(urls)
    assert len(calls) == 1 and len(res) == 1                       # duplicate URLs fetched once
    r = f.get(urls[0])
    assert r.body == body and r.meta['sha256'] == hashlib.sha256(body).hexdigest() and r.meta['bytes'] == len(body)   # CRLF/UTF-8 untouched
    assert (Path(tmp_path) / 'cache' / r.key[:2] / f'{r.key}.body').read_bytes() == body
    f2, _ = make_fetcher(tmp_path, lambda u: pytest.fail('network used on cached re-run'))
    assert f2.get(urls[1]).ok and f2.stats['cache_hits'] == 1 and f2.stats['transport_calls'] == 0
    (Path(tmp_path) / 'cache' / r.key[:2] / f'{r.key}.body').write_bytes(b'tampered')     # corruption detected and refetched, not trusted
    f3, _ = make_fetcher(tmp_path, fn)
    assert f3.get(urls[0]).body == body and len(calls) == 2


def test_failures_cached_refresh_and_independent(tmp_path):
    calls = []

    def fn(url):
        calls.append(url)
        return (404 if 'bad' in url else 200), {}, b'<html>ok</html>', url
    f, _ = make_fetcher(tmp_path, fn)
    res = f.fetch_many(['https://www.opensecrets.org/bad', 'https://www.opensecrets.org/good'])
    assert not res['https://www.opensecrets.org/bad'].ok and res['https://www.opensecrets.org/good'].ok   # one failure never blocks others
    f2, _ = make_fetcher(tmp_path, fn)
    assert f2.get('https://www.opensecrets.org/bad').status == 404 and len(calls) == 2    # 404 cached explicitly, not refetched
    f3, _ = make_fetcher(tmp_path, fn, refresh=True)
    f3.get('https://www.opensecrets.org/good')
    assert len(calls) == 3                                                                  # --refresh refetches


def test_transport_call_accounting_and_rate_slots(tmp_path):
    seq = iter([(503, {}, b'', 'u'), (200, {}, b'<html>ok</html>', 'u')])
    f, clk = make_fetcher(tmp_path, lambda u: next(seq), min_interval=2.0)
    r = f.get('https://www.opensecrets.org/x')
    assert r.ok and f.stats['transport_calls'] == 2 and f.stats['retries'] == 1 and f.stats['url_fetches'] == 1
    assert f.stats['status_counts'] == {'503': 1, '200': 1}
    log = [json.loads(line) for line in (Path(tmp_path) / 'request_log.jsonl').read_text().splitlines()]
    assert [x['http_status'] for x in log if x['event'] == 'transport_call'] == [503, 200]
    assert f._next_slot >= 4.0                                                              # two rate reservations of 2s each


def test_retry_after_numeric_waits_exactly_and_pauses_everyone(tmp_path):
    seq = iter([(429, {'Retry-After': '30'}, b'', 'u'), (200, {}, b'<html>ok</html>', 'u')])
    f, clk = make_fetcher(tmp_path, lambda u: next(seq), min_interval=1.0)
    r = f.get('https://www.opensecrets.org/x')
    assert r.ok and clk.t >= 30.0 and f.stats['http_429'] == 1


def test_retry_after_http_date_and_final_429_still_pauses(tmp_path):
    assert parse_retry_after(formatdate(1_000_045, usegmt=True), 1_000_000) == 45
    assert parse_retry_after('60') == 60 and parse_retry_after('garbage') is None and parse_retry_after(None) is None
    f, clk = make_fetcher(tmp_path, lambda u: (429, {'Retry-After': formatdate(1_000_045, usegmt=True)}, b'', u), max_attempts=1)
    r = f.get('https://www.opensecrets.org/x')
    assert not r.ok and r.status == 429 and f._pause_until >= 45.0                          # pause applied on the FINAL attempt too


def test_retry_after_too_long_defers_family_without_early_retry(tmp_path):
    calls = []

    def fn(url):
        calls.append(url)
        return 429, {'Retry-After': '600'}, b'', url
    f, clk = make_fetcher(tmp_path, fn, max_retry_after=300)
    r = f.get('https://www.opensecrets.org/pacs/a')
    assert not r.ok and r.meta['error'] == 'deferred_retry_after_exceeds_limit' and r.meta['resume_after_utc']
    assert len(calls) == 1 and clk.t < 300                                                   # 600s was NOT shortened to a retry
    r2 = f.get('https://www.opensecrets.org/pacs/b')                                         # same family skipped, other family unaffected
    assert r2.meta['error'] == 'deferred_family_retry_after' and len(calls) == 1


def test_waiting_worker_rechecks_pause_after_sleep(tmp_path):
    f, clk = make_fetcher(tmp_path, lambda u: (200, {}, b'<html/>', u), min_interval=1.0)
    f._next_slot = 10.0                                                                      # this worker must sleep ~10s first
    state = {'n': 0}

    def sleep_then_other_worker_gets_429(s):
        clk.sleep(s)
        if state['n'] == 0:
            f._pause_all(50.0)                                                               # another worker meanwhile got a 429
        state['n'] += 1
    f._sleep = sleep_then_other_worker_gets_429
    f._wait_slot()
    assert clk.t >= 60.0                                                                     # did not start inside the new pause


def test_challenge_200_rejected_live_and_cache_only(tmp_path):
    body = b'<html><head><title>Just a moment...</title></head></html>'
    assert is_challenge(body) and not is_challenge(b'<title>Commercial Banks Summary</title><p>access denied by policy text</p>')
    f, _ = make_fetcher(tmp_path, lambda u: (200, {}, body, u))
    r = f.get('https://www.opensecrets.org/c')
    assert not r.ok and r.status == 200 and r.failure_reason == 'http200_challenge_content' and r.body == body    # bytes kept as evidence
    cache_only = Fetcher(tmp_path, cache_only=True)
    r2 = cache_only.get('https://www.opensecrets.org/c')
    assert not r2.ok and r2.meta['challenge_content'] is True
    ex = Extractor(cache_only, {'scopes': []})
    res, parsed = ex.page('https://www.opensecrets.org/c', P.parse_legacy_totals, 'F03')
    assert parsed is None                                                                    # no observed source data, explicit gap


def test_circuit_breaker_and_budget(tmp_path):
    f, _ = make_fetcher(tmp_path, lambda u: (403, {}, b'', u), circuit_threshold=2)
    for i in range(4):
        f.get(f'https://www.opensecrets.org/blocked/{i}')
    assert f.stats['transport_calls'] == 2 and f.stats['skipped_circuit_open'] == 2        # no repeated 403 hammering
    g, _ = make_fetcher(tmp_path / 'b', lambda u: (200, {}, b'<html/>', u), budget=2)
    for i in range(4):
        g.get(f'https://www.opensecrets.org/p/{i}')
    assert g.stats['transport_calls'] == 2 and g.stats['skipped_budget'] == 2


def test_atomic_write_retries_only_transient_windows_errors(tmp_path):
    calls = {'n': 0}

    def flaky(src, dst):
        calls['n'] += 1
        if calls['n'] < 3:
            e = PermissionError('locked')
            e.winerror = 32
            raise e
        Path(src).replace(dst)
    src = tmp_path / 's'
    src.write_bytes(b'x')
    replace_with_retry(src, tmp_path / 'd', sleep=lambda s: None, replace=flaky)
    assert (tmp_path / 'd').read_bytes() == b'x' and calls['n'] == 3

    def denied(src, dst):
        e = PermissionError('nope')
        e.winerror = 1314                                                                    # not a transient sharing error -> propagates at once
        raise e
    with pytest.raises(PermissionError):
        replace_with_retry(src, tmp_path / 'd2', sleep=lambda s: None, replace=denied)
    atomic_write_bytes(tmp_path / 'w.bin', b'\r\n')
    assert (tmp_path / 'w.bin').read_bytes() == b'\r\n' and not list(tmp_path.glob('*.tmp'))


# ---- extraction semantics -------------------------------------------------------------------------
def test_extractor_national_fallback_cycle_not_relabelled_and_aggregation(tmp_path):
    def fn(url):
        if 'elections-overview?cycle=2024' in url or 'elections-overview?cycle=2026' in url:   # 2026 request is served the 2024 page
            return 200, {}, OVERVIEW, url
        return 404, {}, b'', url
    f, _ = make_fetcher(tmp_path, fn)
    ex = Extractor(f, {'scopes': []})
    ex.national()
    rows = ex.T['national_candidate_by_office']
    r26 = [r for r in rows if r['requested_cycle'] == 2026]
    assert len(r26) == 1 and r26[0]['extraction_status'] == 'served_cycle_mismatch' and r26[0]['served_cycle'] == 2024 and r26[0]['from_pacs_usd'] == ''
    r24 = [r for r in rows if r['requested_cycle'] == 2024 and r['extraction_status'] == 'parsed']
    assert len(r24) == 9
    g = {(r['donor_type'], r['party'], r['office_scope']): r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2024}
    d = g['PAC', 'D', 'pres_house_senate']
    assert d['amount_usd'] == 155464 + 200115894 + 39689298 and d['party_universe'] == 'two_party_D_R'
    allp = g['PAC', 'All', 'pres_house_senate']
    assert allp['party_universe'] == 'all_parties'
    assert allp['other_party_residual_signed_usd'] == allp['amount_usd'] - d['amount_usd'] - g['PAC', 'R', 'pres_house_senate']['amount_usd']
    assert all(r['source_url'] and r['retrieved_utc'] and r['source_sha256'] and r['source_release_date'] == '2025-09-16' for r in r24)  # vintage vs capture kept apart


def test_negative_residual_not_clamped(tmp_path):
    page = OVERVIEW.replace(b'$422,640,137', b'$1,000')                                     # All-party PAC below Dems+Repubs (like 2012 Pres)
    f, _ = make_fetcher(tmp_path, lambda u: (200, {}, page, u) if 'cycle=2024' in u else (404, {}, b'', u))
    ex = Extractor(f, {'scopes': []})
    ex.national()
    row = next(r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2024 and r['donor_type'] == 'PAC'
               and r['party'] == 'All' and r['office_scope'] == 'pres_house_senate')
    assert row['other_party_residual_signed_usd'] < 0                                         # signed, not clamped, no All>=party rule
