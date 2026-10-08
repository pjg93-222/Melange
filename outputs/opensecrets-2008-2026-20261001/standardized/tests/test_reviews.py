"""Targeted regressions for the late independent reviews: transport deferral/restart, owner lock, read-only status, national controls and
2026 gap rows, legacy-summary chamber evidence, client-split served year, lobbying exact predicates, PAC aggregate predicates, organisation
completeness, menu-derived cycles, configured periods and per-run benchmark labelling."""
import json, os, sys
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from osc import config as C  # noqa: E402
from osc import parsers as P  # noqa: E402
from osc import validate as V  # noqa: E402
from osc.cli import process_info  # noqa: E402
from osc.extract import Extractor  # noqa: E402
from osc.fetch import Deferred, FetchResult, Fetcher  # noqa: E402
from osc.lock import LockHeld, OwnerLock  # noqa: E402
from osc.receipt import run_segments  # noqa: E402
from osc.runner import Runner  # noqa: E402
from osc.util import canonical_url  # noqa: E402

FIX = Path(__file__).parent / 'fixtures'
OVERVIEW = (FIX / 'national-overview-2024.html').read_bytes()
ABA = (FIX / 'aba-recipients-2024.html').read_bytes()
BASE = 'https://www.opensecrets.org'


class Clock:
    def __init__(self):
        self.t = 0.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s


def mk(tmp_path, fn, wall=1_000_000.0, **kw):
    clk = kw.pop('clock', None) or Clock()
    f = Fetcher(tmp_path, request_fn=fn, sleep=clk.sleep, clock=clk.now, wall=lambda: wall, min_interval=kw.pop('min_interval', 1.0), **kw)
    return f, clk


def serve(pages):
    pages = {canonical_url(k): v for k, v in pages.items()}
    return lambda u: (200, {}, pages[u], u) if u in pages else (404, {}, b'', u)


def no_network(url):
    pytest.fail(f'unexpected network request: {url}')


# ---- transport: restart deadline, waiting workers, bounded 429, per-family ---------------------------------
def test_retry_after_deadline_survives_restart_for_same_url_and_new_family(tmp_path):
    f, _ = mk(tmp_path, lambda u: (429, {'Retry-After': '600'}, b'', u), max_retry_after=300)
    r = f.get(BASE + '/pacs/a')
    assert r.deferred and r.meta['resume_after_utc'] and f.stats['transport_calls'] == 1
    clk2 = Clock()
    f2 = Fetcher(tmp_path, request_fn=no_network, sleep=clk2.sleep, clock=clk2.now, wall=lambda: 1_000_001.0, min_interval=1.0, max_retry_after=300)
    for url in (BASE + '/pacs/a', BASE + '/other/b'):          # same cached-429 URL AND a brand-new family: both honour the stored deadline
        r2 = f2.get(url)
        assert r2.deferred and not r2.ok and r2.status is None
    assert f2.stats['transport_calls'] == 0
    f3 = Fetcher(tmp_path, request_fn=lambda u: (200, {}, b'<html>ok</html>', u), sleep=Clock().sleep, clock=Clock().now, wall=lambda: 1_000_700.0, min_interval=1.0)
    assert f3.get(BASE + '/pacs/a').ok                       # after the deadline a resume may fetch again


def test_waiting_worker_defers_instead_of_sleeping_a_long_pause(tmp_path):
    f, clk = mk(tmp_path, lambda u: (200, {}, b'<html/>', u), max_retry_after=300)
    f._next_slot = 10.0

    def sleep_then_other_worker_gets_retry_after(s):
        clk.sleep(s)
        f._pause_all(600.0)
    f._sleep = sleep_then_other_worker_gets_retry_after
    with pytest.raises(Deferred):
        f._wait_slot('x')
    assert clk.t < 100                                         # did not sit out 600 s


def test_family_deadline_stops_workers_already_in_their_retry_loop(tmp_path):
    f, _ = mk(tmp_path, lambda u: (200, {}, b'<html/>', u))
    f._defer_family('lobby', f._wall() + 900)
    with pytest.raises(Deferred) as e:
        f._wait_slot('lobby')
    assert e.value.scope == 'family_deadline'
    f._wait_slot('pacs')                                       # another family is unaffected


def test_no_header_429_is_bounded_and_defers_only_that_family(tmp_path):
    calls = []

    def fn(u):
        calls.append(u)
        if '/lobby/' in u:
            return 429, {}, b'<html><head><title>Just a moment...</title></head></html>', u
        return 200, {}, b'<html>ok</html>', u
    f, clk = mk(tmp_path, fn, family_429_limit=3, max_attempts=5, family_cooldown=900.0)
    r = f.get(BASE + '/lobby/a')
    assert r.deferred and r.meta['error'] == 'deferred_family_429_cooldown' and len(calls) == 3   # 3 attempts, not 5 x 120 s
    assert clk.t < 100
    r2 = f.get(BASE + '/lobby/b')
    assert r2.deferred and len(calls) == 3                                                         # the family receives no more traffic
    assert f.get(BASE + '/pacs/x').ok                                                              # unrelated families keep progressing
    assert f._fam_interval['lobby'] >= 3.0                                                         # that family's pace was cut, nobody else's
    f2 = Fetcher(tmp_path, request_fn=no_network, sleep=Clock().sleep, clock=Clock().now, wall=lambda: 1_000_000.0)
    assert f2.get(BASE + '/lobby/c').deferred                                                      # restart honours the cooldown


def test_transport_calls_and_redirect_hops_are_counted_separately(tmp_path):
    f, _ = mk(tmp_path, lambda u: (200, {}, b'<html/>', u))
    f._once = lambda url: (200, {}, b'<html/>', url, 2, 'curl')
    assert f.get(BASE + '/x').ok
    assert f.stats['transport_calls'] == 1 and f.stats['redirect_hops'] == 2 and f.http_requests_total == 3


# ---- process owner lock + read-only status --------------------------------------------------------------------
def test_owner_lock_blocks_a_second_owner_until_released(tmp_path):
    a = OwnerLock(tmp_path).acquire(command='collect')
    with pytest.raises(LockHeld):
        OwnerLock(tmp_path).acquire(command='discover')
    a.release()
    b = OwnerLock(tmp_path).acquire(command='discover')
    b.release()


@pytest.mark.skipif(sys.platform != 'win32', reason='os.kill(pid, 0) terminates the process on Windows only')
def test_status_probe_never_uses_os_kill(monkeypatch):
    def boom(*a, **k):
        raise AssertionError('os.kill must not be used for liveness on Windows')
    monkeypatch.setattr(os, 'kill', boom)
    me = process_info(os.getpid())
    assert me['alive'] is True and me['is_osc'] is False
    assert process_info(99999999)['alive'] is False


# ---- national controls and 2026 gap rows ------------------------------------------------------------------------
def overview_variant(type_label=None, display_label=None, cycle=None, drop_presidential=False):
    soup = BeautifulSoup(OVERVIEW.decode('utf-8', 'replace'), 'html.parser')

    def pick(name, label):
        sel = soup.select_one(f'select[name={name}]')
        for o in sel.select('option'):
            if o.has_attr('selected'):
                del o['selected']
        for o in sel.select('option'):
            if o.get_text(strip=True) == label:
                o['selected'] = 'selected'
    if type_label:
        pick('select_type', type_label)
    if display_label:
        pick('display_type', display_label)
    if cycle:
        pick('select_cycle', str(cycle))
    if drop_presidential:
        for h in soup.find_all('h2'):
            if h.get_text(strip=True) == 'Presidential':
                h.find_next('table').decompose()
                h.decompose()
    return str(soup).encode('utf-8')


def test_overview_controls_are_derived_from_the_page():
    ok = P.parse_overview(OVERVIEW, 2024)
    assert ok['universe_ok'] and ok['type_code'] == 'A' and ok['display_code'] == 'T' and ok['controls_basis'].startswith('type:first_enabled_option_default')
    members = P.parse_overview(overview_variant(type_label='Members of Congress only'), 2024)
    assert not members['universe_ok'] and members['type_selected'] == 'Members of Congress only' and 'not All candidates' in members['universe_reject_reason']
    avg = P.parse_overview(overview_variant(display_label='Display averages'), 2024)
    assert not avg['universe_ok'] and avg['display_selected'] == 'Display averages'
    soup = BeautifulSoup('<select><option disabled value="x">pick</option><option value="a">First enabled</option><option value="b">Second</option></select>', 'html.parser')
    sel = P.selected_option(soup.select_one('select'))
    assert sel['label'] == 'First enabled' and sel['how'] == 'first_enabled_option_default'


def test_wrong_universe_is_rejected_with_reason_coded_aggregate_gap_rows(tmp_path):
    page = overview_variant(type_label='Members of Congress only')
    f, _ = mk(tmp_path, lambda u: (200, {}, page, u) if 'cycle=2024' in u else (404, {}, b'', u))
    ex = Extractor(f, {'scopes': []})
    ex.national()
    off = [r for r in ex.T['national_candidate_by_office'] if r['requested_cycle'] == 2024]
    assert len(off) == 1 and off[0]['extraction_status'] == 'candidate_universe_mismatch' and off[0]['from_pacs_usd'] == ''
    agg = [r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2024]
    assert len(agg) == 12 and all(r['completeness_status'] == 'unavailable' and r['amount_usd'] == '' and r['reason_code'] == 'wrong_candidate_universe_or_display' for r in agg)


def test_2026_has_explicit_gap_aggregate_rows_and_midterm_president_is_absent_not_zero(tmp_path):
    midterm = overview_variant(cycle=2022, drop_presidential=True)
    f, _ = mk(tmp_path, lambda u: (200, {}, OVERVIEW, u) if 'cycle=2024' in u or 'cycle=2026' in u else (200, {}, midterm, u) if 'cycle=2022' in u else (404, {}, b'', u))
    ex = Extractor(f, {'scopes': []})
    ex.national()
    gap = [r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2026]
    assert len(gap) == 6 and {r['office_scope'] for r in gap} == {'house_senate'}
    assert all(r['amount_usd'] == '' and r['completeness_status'] == 'unavailable' and r['served_cycle'] == 2024 and r['reason_code'] == 'served_cycle_mismatch' for r in gap)
    assert all('absent, not zero' in r['coverage_note'] for r in gap)
    mid = [r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2022]
    assert {r['office_scope'] for r in mid} == {'house_senate'} and all(r['offices_included'] == 'House+Senate' and r['completeness_status'] == 'complete' for r in mid)
    pres = [r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2024 and r['office_scope'] == 'pres_house_senate']
    assert pres and all(r['offices_included'] == 'Presidential+House+Senate' for r in pres)


def test_missing_donor_value_keeps_the_office_row_partial_and_blank(tmp_path):
    page = OVERVIEW.replace(b'$422,640,137', b'N/A')
    f, _ = mk(tmp_path, lambda u: (200, {}, page, u) if 'cycle=2024' in u else (404, {}, b'', u))
    ex = Extractor(f, {'scopes': []})
    ex.national()
    row = next(r for r in ex.T['national_candidate_by_office'] if r['requested_cycle'] == 2024 and r['office'] == 'House' and r['party'] == 'All')
    assert row['from_pacs_usd'] == '' and row['completeness_status'] == 'partial' and row['reason_code'].startswith('donor_value_missing')
    agg = next(r for r in ex.T['national_candidate_giving'] if r['requested_cycle'] == 2024 and r['donor_type'] == 'PAC' and r['party'] == 'All' and r['office_scope'] == 'house_senate')
    assert agg['amount_usd'] == '' and agg['completeness_status'] == 'partial'


# ---- legacy summary chamber evidence / client split year -------------------------------------------------------------
def summary_page(chamber_word, mem, recip):
    rows = json.dumps([{'Representative': 'Doe, Jane (D-CA)', 'State': 'California', 'Amount': '$10'}])
    return (f"<select name='cycle'><option value='/industries/summary?cycle=2024&ind=F03&mem={mem}&recipdetail={recip}' selected>2024</option></select>"
            f"<select name='type'><option value='/industries/summary?code=F03&cycle=2024&ind=F03&mem=N&recipdetail=H'>All House Candidates</option>"
            f"<option value='/industries/summary?code=F03&cycle=2024&ind=F03&mem=Y&recipdetail=H'>All Members of the House</option></select>"
            f"<h3>Money from Commercial Banks to US {chamber_word} candidates, 2023-2024</h3>"
            f"<table data-collection='{rows}'><thead><tr><th>Representative</th><th>State</th><th>Amount</th></tr></thead></table>")


def test_legacy_summary_derives_served_chamber_and_universe_and_extractor_rejects_mismatch(tmp_path):
    house_all = P.parse_legacy_summary(summary_page('House', 'N', 'H'), 'F03', 2024, 'Senate')
    assert house_all['served_chamber'] == 'House' and house_all['served_mem'] == 'N' and house_all['chamber_evidence_agrees']
    assert house_all['served_universe_label'] == 'All House Candidates'
    scope = {'scope_id': 'commercial_banks', 'name': 'Commercial Banks', 'opensecrets_code': 'F03', 'relation': 'requested'}
    cases = {('Senate', 'House', 'N', 'H'): 'requested Senate but the page is the House list',
             ('House', 'House', 'Y', 'H'): 'member-only universe (mem=Y), not all candidates'}
    for (want, word, mem, recip) in cases:
        url = C.u_legacy_summary('F03', 2024, want)
        f, _ = mk(tmp_path / want / mem, serve({url: summary_page(word, mem, recip).encode()}))
        ex = Extractor(f, {'scopes': [scope]})
        ex._legacy_summary({**ex.idf(scope), 'requested_cycle': 2024}, 'F03', 2024, want)
        row = ex.T['legacy_candidate_combined_by_chamber_party'][0]
        assert row['extraction_status'] == 'served_universe_mismatch' and row['completeness_status'] == 'unavailable' and not ex.T['legacy_candidate_combined']


def test_client_split_reports_the_served_year():
    split = json.dumps({'series': [{'category': 'In-house operations', 'value': 1.0}, {'category': 'Outside firms', 'value': 2.0}]})
    s = P.parse_client_split(f"<p>2024 total $3</p><div data-charts--single-stacked-bar-options-value='{split}'></div>")
    assert s['served_year'] == 2024 and s['client_year_total_usd'] == 3


# ---- lobbying exact predicates ---------------------------------------------------------------------------------------
SLUG, CAT = 'insurance', 'F09'


def lobby_pages(industry, active, clients, splits, split_year=2026):
    rows = ''.join(f"<tr><td><a href='/federal-lobbying/clients/{cid}-slug?client_id={cid}&amp;cycle=2026'>{name}</a></td><td>${spend:,}</td></tr>" for name, cid, spend in clients)
    pages = {
        C.u_lobby_page(SLUG, CAT, 2026): b'<html><h1>Insurance</h1></html>',
        C.u_lobby_chunk(SLUG, CAT, 'annual_trends', 2026): ("<div data-charts--line-chart-options-value='" + json.dumps(
            {'series': [{'name': 'Total spending', 'data': [{'category': '2026', 'value': float(industry)}]}]}) + "'></div>").encode(),
        C.u_lobby_chunk(SLUG, CAT, 'main', 2026): (f"<p>Industry spending ${industry:,} 2026 reported lobbying Clients active {active}</p>"
                                                   f"<h2>Insurance clients by Client/Parent, 2026</h2><table><thead><tr><th>Client/Parent</th><th>Total</th></tr></thead><tbody>{rows}</tbody></table>").encode(),
    }
    for (name, cid, spend) in clients:
        sp = splits.get(cid)
        if sp is None:
            continue
        series = [{'category': k, 'value': float(v)} for k, v in sp['parts'].items()]
        pages[C.u_client_split(f'{cid}-slug', cid, 2026)] = (f"<p>{split_year} total ${sp['total']:,}</p><div data-charts--single-stacked-bar-options-value='"
                                                              + json.dumps({'series': series}) + "'></div>").encode()
    return pages


def run_lobby(tmp_path, monkeypatch, pages, clients):
    monkeypatch.setattr(C, 'YEARS', [2026])
    f, _ = mk(tmp_path, serve(pages))
    for name, cid, spend in clients:
        f.get(C.u_client_split(f'{cid}-slug', cid, 2026))
    scope = {'scope_id': 'ins', 'name': 'Insurance', 'opensecrets_code': 'F09', 'relation': 'requested', 'lobby_category_id': CAT, 'lobby_slug': SLUG}
    ex = Extractor(f, {'scopes': [scope]})
    ex.asof = {'as_of': '', 'start': '', 'end': '', 'note': ''}
    ex._modern_lobby(scope, ex.idf(scope), CAT, SLUG)
    return next(r for r in ex.T['lobbying_annual'] if r['requested_year'] == 2026), ex


def test_lobby_exact_requires_full_parent_roster_and_reconciled_explicit_components(tmp_path, monkeypatch):
    clients = [('A Corp', '1', 60), ('B Corp', '2', 40)]
    good = {'1': {'total': 60, 'parts': {'In-house operations': 30, 'Outside firms': 30}}, '2': {'total': 40, 'parts': {'In-house operations': 40, 'Outside firms': 0}}}
    row, ex = run_lobby(tmp_path / 'good', monkeypatch, lobby_pages(100, 2, clients, good), clients)
    assert row['in_house_outside_status'] == 'complete_exact' and (row['in_house_usd'], row['outside_firm_usd']) == (70, 30)   # a published 0 is explicit
    assert row['in_house_outside_reason'] == '' and row['clients_with_split'] == row['clients_split_reconciled'] == 2


def test_lobby_truncated_client_list_is_not_certified_exact(tmp_path, monkeypatch):
    one = [('A Corp', '1', 100)]
    sp = {'1': {'total': 100, 'parts': {'In-house operations': 60, 'Outside firms': 40}}}
    row, ex = run_lobby(tmp_path, monkeypatch, lobby_pages(200, 2, one, sp), one)     # source says 2 clients / 200, only one parsed
    assert row['in_house_outside_status'] == 'partial_unreconciled' and row['in_house_usd'] == '' and row['outside_firm_usd'] == ''
    assert 'parsed_clients_differ_from_source_count' in row['in_house_outside_reason'] and 'client_spend_sum_differs_from_industry_total' in row['in_house_outside_reason']
    assert (row['in_house_partial_sum_usd'], row['outside_partial_sum_usd']) == (60, 40)     # labelled partial sums survive


def test_lobby_absent_component_is_not_zero(tmp_path, monkeypatch):
    one = [('A Corp', '1', 100)]
    sp = {'1': {'total': 100, 'parts': {'In-house operations': 100}}}                      # outside firms series absent
    row, ex = run_lobby(tmp_path, monkeypatch, lobby_pages(100, 1, one, sp), one)
    assert row['in_house_outside_status'] == 'partial_unreconciled' and row['outside_firm_usd'] == '' and row['in_house_usd'] == ''
    assert 'split_component_not_explicit' in row['in_house_outside_reason']
    assert ex.T['lobbying_client_splits'][0]['components_explicit'] is False


def test_lobby_acu_style_split_sum_stays_unreconciled(tmp_path, monkeypatch):
    one = [("America's Credit Unions", '141826', 2988000)]
    sp = {'141826': {'total': 2988000, 'parts': {'In-house operations': 2206000, 'Outside firms': 518000}}}   # 2,724,000 != 2,988,000
    row, ex = run_lobby(tmp_path, monkeypatch, lobby_pages(2988000, 1, one, sp), one)
    assert row['in_house_outside_status'] == 'partial_unreconciled' and row['in_house_usd'] == ''
    s = ex.T['lobbying_client_splits'][0]
    assert s['split_sum_usd'] == 2724000 and s['split_sum_minus_page_total_usd'] == -264000 and s['reconciliation_flag'] == 'split_sum_differs_from_client_total'


@pytest.mark.parametrize('mutation', ['none', 'certified_exact', 'changed_amount'])
def test_acu_validation_accepts_numeric_source_mismatch_and_rejects_corruption(tmp_path, monkeypatch, mutation):
    one = [("America's Credit Unions", '141826', 2988000)]
    sp = {'141826': {'total': 2988000, 'parts': {'In-house operations': 2206000, 'Outside firms': 518000}}}
    _, ex = run_lobby(tmp_path, monkeypatch, lobby_pages(2988000, 1, one, sp), one)
    split = ex.T['lobbying_client_splits'][0]
    if mutation == 'certified_exact':
        split['reconciliation_flag'] = 'client_total_equals_industry_amount_and_split_sums'
    elif mutation == 'changed_amount':
        split['in_house_usd'] += 1
    monkeypatch.setattr(V, '_read_csv', lambda path: [])
    checks = V.Checks()
    V.rest_checks(checks, ex.T, ex)
    result = next(r for r in checks.rows if r['check_id'] == 'acu_2026_split_unreconciled')
    assert result['status'] == ('pass' if mutation == 'none' else 'FAIL')


def test_lobby_client_split_page_for_another_year_is_not_labelled_as_requested(tmp_path, monkeypatch):
    one = [('A Corp', '1', 100)]
    sp = {'1': {'total': 100, 'parts': {'In-house operations': 60, 'Outside firms': 40}}}
    row, ex = run_lobby(tmp_path, monkeypatch, lobby_pages(100, 1, one, sp, split_year=2024), one)
    assert row['in_house_outside_status'] == 'partial_unreconciled' and 'client_split_served_year_mismatch' in row['in_house_outside_reason']
    s = ex.T['lobbying_client_splits'][0]
    assert s['extraction_status'] == 'served_year_mismatch' and s['served_year'] == 2024 and s['in_house_usd'] == ''


# ---- PAC aggregate predicates ----------------------------------------------------------------------------------------
SCOPE = {'scope_id': 'commercial_banks', 'name': 'Commercial Banks', 'opensecrets_code': 'F03', 'relation': 'requested'}
ABA_URL = C.u_pac_recipients('american-bankers-assn', 'C00004275', 2024)


def pac_roster_entry(pid, d, r, total=None):
    return {'pac_id': pid, 'pac_name': pid, 'slug': '', 'affiliate': '', 'lean': '', 'total_usd': total if total is not None else d + r,
            'to_democrats_usd': d, 'to_republicans_usd': r, 'summary_url': '', 'href_cycle': 2024}


def industry_run(tmp_path, pacs, expected, headline, roster_ok=True, mutate=None):
    f, _ = mk(tmp_path, serve({ABA_URL: ABA}))
    ex = Extractor(f, {'scopes': [SCOPE]})
    ex.runner.pac_pages = lambda: {('C00004275', 2024): 'american-bankers-assn'}
    ex.pac_pages()
    if mutate:
        mutate(ex)
    stub = FetchResult(BASE + '/x', 'k', True, 200, b'x', {'retrieved_utc': '2026-10-01T00:00:00+00:00', 'sha256': 'ab'})
    ex.rosters[('commercial_banks', 2024)] = (stub, {'pacs': pacs, 'headline': {'n_pacs': expected}, 'meta': {}})
    ex.headline_eff[('commercial_banks', 2024)] = {'D': headline[0], 'R': headline[1], 'defect': False, 'roster_ok': roster_ok}
    ex.pac_industry_chambers()
    return {(r['chamber'], r['party_group']): r for r in ex.T['pac_candidate_giving_industry'] if r['requested_cycle'] == 2024}


def test_pac_page_reconciles_house_senate_and_independents_against_its_headline(tmp_path):
    f, _ = mk(tmp_path, serve({ABA_URL: ABA}))
    ex = Extractor(f, {'scopes': [SCOPE]})
    ex.runner.pac_pages = lambda: {('C00004275', 2024): 'american-bankers-assn'}
    ex.pac_pages()
    pd = ex.pac_data[('C00004275', 2024)]
    assert pd['reconciles'] is True and pd['total_reconciles'] is True and not pd['missing']      # 838000 / 1600999 / 2453999 incl. 15000 independents
    page = ex.T['pac_pages'][0]
    assert page['completeness_status'] == 'complete' and page['all_party_reconciles_to_headline_total'] is True


def test_pac_industry_cells_are_exact_only_when_everything_reconciles(tmp_path):
    cells = industry_run(tmp_path, [pac_roster_entry('C00004275', 838000, 1600999, 2453999)], 1, (838000, 1600999))
    assert cells[('House', 'D')]['amount_usd'] == 780500 and cells[('House', 'R')]['amount_usd'] == 1464999
    assert cells[('Senate', 'D')]['amount_usd'] == 57500 and cells[('Senate', 'R')]['amount_usd'] == 136000
    assert all(r['completeness_status'] == 'complete' and r['amount_status'] == 'exact' for r in cells.values())
    assert cells[('Senate', 'Other')]['amount_usd'] == 15000 and cells[('House', 'Other')]['amount_usd'] == 0   # all-party total reconciles, so House zero is proven


def test_pac_headline_gap_or_duplicate_ids_or_missing_page_never_certify(tmp_path):
    pac = pac_roster_entry('C00004275', 838000, 1600999, 2453999)
    gap = industry_run(tmp_path / 'gap', [pac], 1, (838100, 1600999), roster_ok=False)               # industry headline 100 above the roster
    assert gap[('House', 'D')]['completeness_status'] == 'partial' and gap[('House', 'D')]['amount_usd'] == '' and gap[('House', 'D')]['partial_sum_usd'] == 780500
    assert 'roster_not_reconciled_to_industry_headline' in gap[('House', 'D')]['reason_code']
    dup = industry_run(tmp_path / 'dup', [pac, dict(pac)], 2, (838000, 1600999))                      # duplicate ID satisfies the ROW count but is one PAC
    assert dup[('House', 'D')]['completeness_status'] == 'partial' and 'duplicate_roster_pac_id' in dup[('House', 'D')]['reason_code']
    assert dup[('House', 'D')]['pacs_unique_ids'] == 1 and dup[('House', 'D')]['pacs_duplicate_roster_rows'] == 1
    missing = industry_run(tmp_path / 'miss', [pac, pac_roster_entry('C00000002', 1, 1)], 2, (838001, 1601000))   # a distinct expected PAC has no page
    assert missing[('House', 'D')]['completeness_status'] == 'partial' and missing[('House', 'D')]['pacs_missing'] == 1
    assert 'pac_pages_missing' in missing[('House', 'D')]['reason_code'] and missing[('House', 'D')]['amount_usd'] == ''


def test_pac_missing_amount_is_not_zero(tmp_path):
    def blank(ex):
        pd = ex.pac_data[('C00004275', 2024)]
        pd['summ'][('House', 'D')] = None
        pd['missing'] = ['House|D']
        pd['reconciles'] = None
    cells = industry_run(tmp_path, [pac_roster_entry('C00004275', 838000, 1600999, 2453999)], 1, (838000, 1600999), mutate=blank)
    c = cells[('House', 'D')]
    assert c['amount_usd'] == '' and c['completeness_status'] == 'partial' and c['pacs_with_missing_money'] == 1 and 'pac_amount_missing_or_unproven_zero' in c['reason_code']


def test_industry_headline_includes_presidential_giving_and_is_scoped_correctly(tmp_path):
    def synth(ex):
        base = {'present': {'House', 'Senate', 'Presidential'}, 'missing': [], 'reconciles': True, 'total_reconciles': True, 'counts': {}, 'sums': {}, 'headline': (None, 100, 10)}
        ex.pac_data[('C00004275', 2024)] = {**base, 'summ': {('House', 'D'): 40, ('Senate', 'D'): 50, ('Presidential', 'D'): 10,
                                                             ('House', 'R'): 5, ('Senate', 'R'): 5, ('Presidential', 'R'): 0}}
    with_pres = industry_run(tmp_path / 'p', [pac_roster_entry('C00004275', 100, 10, 110)], 1, (100, 10), mutate=synth)
    d = with_pres[('House', 'D')]
    assert d['completeness_status'] == 'complete' and d['amount_usd'] == 40 and d['presidential_party_usd'] == 10 and d['headline_minus_chambers_incl_presidential_usd'] == 0

    def synth_gap(ex):                                    # the documented 10 gap: House 40 + Senate 50 vs headline D 100, no Presidential table
        ex.pac_data[('C00004275', 2024)] = {'present': {'House', 'Senate'}, 'missing': [], 'reconciles': False, 'total_reconciles': None, 'counts': {}, 'sums': {},
                                            'headline': (None, 100, 10), 'summ': {('House', 'D'): 40, ('Senate', 'D'): 50, ('House', 'R'): 5, ('Senate', 'R'): 5}}
    gap = industry_run(tmp_path / 'g', [pac_roster_entry('C00004275', 100, 10, 110)], 1, (100, 10), mutate=synth_gap)
    assert gap[('House', 'D')]['completeness_status'] == 'partial' and gap[('House', 'D')]['amount_usd'] == '' and gap[('House', 'D')]['partial_sum_usd'] == 40


# ---- organisations: completeness independent of numeric equality, roster crosswalk -------------------------------------
def org_search_page(*orgs):
    return '<table>' + ''.join(f"<tr><td>Organization</td><td><a href='/orgs/{slug}/summary?id={oid}'>{name}</a></td></tr>" for name, slug, oid in orgs) + '</table>'


ORG_TOTALS = ("<table><thead><tr><th>Cycle</th><th>Total</th><th>Democrats</th><th>Republicans</th><th>% to Dems</th><th>% to Repubs</th></tr></thead>"
              "<tbody><tr><td>2024</td><td>$10</td><td>$6</td><td>$4</td><td>60%</td><td>40%</td></tr></tbody></table>"
              "<table><thead><tr><th>Cycle</th><th>Individuals</th><th>PACs</th><th>Soft (Individuals)</th><th>Soft (Organization)</th></tr></thead>"
              "<tbody><tr><td>2024</td><td>$7</td><td>$3</td><td>$0</td><td>N/A</td></tr></tbody></table>")


def test_org_roster_crosswalk_preserves_ambiguous_and_partial_profiles(tmp_path):
    pages = {C.u_org_search('Acme Bank'): org_search_page(('Acme Bank', 'acme-bank', 'D000000001')).encode(),
             C.u_org_totals('acme-bank', 'D000000001'): ORG_TOTALS.encode(),
             C.u_org_search('Twin'): org_search_page(('Twin', 'twin-a', 'D000000002'), ('TWIN', 'twin-b', 'D000000003')).encode(),
             C.u_org_search('Unknown Co'): b'<html><table></table></html>'}
    f, _ = mk(tmp_path, serve(pages))
    ex = Extractor(f, {'scopes': []})
    ex.runner.roster = [{'original_company_name': n, 'source_workbook': 'W.xlsx', 'worksheet': 'Company List', 'row_number': str(i), 'scope_id': 'mentat:banking',
                         'mentat_industry': 'Banking', 'capture_utc': '2026-10-01T21:43:41Z', 'workbook_sha256': 'abc', 'snapshot_status': 'stable_before_after'}
                        for i, n in enumerate(['Acme Bank', 'Twin', 'Unknown Co'], 6)]
    for r in ex.runner.roster:   # the extractor would have these pages cached by the collector; fetch them once here
        f.get(C.u_org_search(r['original_company_name']))
    f.get(C.u_org_totals('acme-bank', 'D000000001'))
    ex.orgs()
    by = {r['original_company_name']: r for r in ex.T['org_roster_crosswalk']}
    assert by['Acme Bank']['match_status'] == 'matched_exact' and by['Acme Bank']['org_id'] == 'D000000001' and by['Acme Bank']['completeness_status'] == 'partial'
    assert by['Acme Bank']['reason_code'] == 'org_history_component_missing' and by['Acme Bank']['roster_workbook_sha256'] == 'abc'
    assert by['Twin']['match_status'] == 'ambiguous_exact' and by['Twin']['org_id'] == '' and by['Twin']['n_org_candidates'] == 2 and 'D000000003' in by['Twin']['org_candidates']
    assert by['Unknown Co']['match_status'] in ('no_organization_rows', 'no_exact_match') and by['Unknown Co']['completeness_status'] == 'unavailable'
    h = ex.T['org_totals_history']
    assert len(h) == 1 and h[0]['soft_organization_usd'] == '' and h[0]['soft_individual_usd'] == 0           # absent stays blank, published $0 stays 0
    assert h[0]['completeness_status'] == 'partial' and h[0]['reason_code'] == 'org_component_missing' and h[0]['matched_via'] == 'mentat_roster'
    assert h[0]['search_url'] and h[0]['search_retrieved_utc'] and h[0]['profile_url'] and 'ownership or parent proof' in h[0]['match_qualification']


# ---- menu-derived cycles, configured periods, runner deferral, run labelling -----------------------------------------------------
def menu_page(*cycles, selected):
    return ("<select name='select_cycle'>" + ''.join(f"<option{' selected' if c == selected else ''}>{c}</option>" for c in cycles) + '</select>').encode()


def test_available_cycles_come_from_the_source_menu_not_a_hard_coded_ceiling(tmp_path):
    cfg = {'scopes': [SCOPE]}
    f, _ = mk(tmp_path / 'a', serve({C.u_pac_breakdown(C.LAST_CYCLE): menu_page(2024, 2022, 2020, selected=2024)}))
    r = Runner(f, cfg, tmp_path / 'sa', tiers=set())
    assert r.cycles_for('pac') == [2020, 2022, 2024]
    f2, _ = mk(tmp_path / 'b', serve({C.u_pac_breakdown(C.LAST_CYCLE): menu_page(2026, 2024, 2022, selected=2026)}))
    r2 = Runner(f2, cfg, tmp_path / 'sb', tiers=set())
    assert r2.cycles_for('pac') == [2022, 2024, 2026]                    # a refreshed run after 2026 is published requests it automatically
    f3, _ = mk(tmp_path / 'c', serve({}))
    assert Runner(f3, cfg, tmp_path / 'sc', tiers=set()).cycles_for('pac') == C.CYCLES   # no menu evidence: attempt all, served-cycle guards reject fallbacks


def test_configured_periods_are_honoured_and_invalid_ones_rejected():
    default = {'cycles': {'first': 2008, 'last': 2026, 'step': 2}, 'lobbying_years': {'first': 2008, 'last': 2026}}
    try:
        C.apply_periods({'cycles': {'first': 2012, 'last': 2020, 'step': 2}, 'lobbying_years': {'first': 2014, 'last': 2018}})
        assert C.CYCLES == [2012, 2014, 2016, 2018, 2020] and C.YEARS == [2014, 2015, 2016, 2017, 2018]
        assert C.is_pres_year(2012) and not C.is_pres_year(2014)
        for bad in ({'cycles': {'first': 2009, 'last': 2020, 'step': 2}}, {'cycles': {'first': 2008, 'last': 2020, 'step': 1}}, {'cycles': {'first': 2020, 'last': 2008, 'step': 2}}):
            with pytest.raises(ValueError):
                C.apply_periods(bad)
    finally:
        C.apply_periods(default)
    assert C.CYCLES[0] == 2008 and C.CYCLES[-1] == 2026


def test_runner_defers_instead_of_hammering_and_persists_the_resume_deadline(tmp_path):
    calls = []

    def fn(u):
        calls.append(u)
        return 429, {'Retry-After': '600'}, b'', u
    f, _ = mk(tmp_path / 'data', fn, concurrency=1, max_retry_after=300)
    r = Runner(f, {'scopes': []}, tmp_path / 'state', tiers={'seeds'})
    r.run(only={'seeds_national'}, max_defer_wait=0)
    assert len(calls) == 1 and r.phase == 'collect_deferred'                   # one request, not N URLs x 5 attempts
    ds = r.deferred_summary()
    assert ds['urls'] == len(r.queue) and ds['earliest_resume_utc']
    saved = json.loads((tmp_path / 'state' / 'work_queue.json').read_text(encoding='utf-8'))
    assert all(q['state'] == 'deferred' and q['resume_after_utc'] for q in saved)   # remaining queue + deadline persisted for the resume


def test_run_segments_label_aborted_duplicates_and_count_hops_separately():
    calls = [{'utc': '2026-10-01T21:23:10+00:00', 'http_status': 429, 'bytes': 10, 'event': 'physical_request'},
             {'utc': '2026-10-01T21:24:10+00:00', 'http_status': 200, 'bytes': 20, 'event': 'physical_request'},
             {'utc': '2026-10-01T21:45:00+00:00', 'http_status': 200, 'bytes': 30, 'event': 'physical_request'},
             {'utc': '2026-10-01T22:05:00+00:00', 'http_status': 200, 'bytes': 40, 'event': 'transport_call', 'run_id': 'R1', 'redirect_hops': 2},
             {'utc': '2026-10-01T22:06:00+00:00', 'http_status': 200, 'bytes': 50, 'event': 'transport_call', 'run_id': 'R1', 'redirect_hops': 0}]
    seg = run_segments(calls)
    assert seg['archived_aborted_duplicate_runs_pre_run_id']['aborted_or_duplicate'] is True and seg['archived_aborted_duplicate_runs_pre_run_id']['transport_calls'] == 2
    assert seg['archived_run_35396_pre_run_id']['aborted_or_duplicate'] is False
    assert seg['R1']['transport_calls'] == 2 and seg['R1']['redirect_hops'] == 2 and seg['R1']['wall_seconds'] == 60.0
