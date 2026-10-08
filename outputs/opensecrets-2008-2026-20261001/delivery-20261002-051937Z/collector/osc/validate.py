"""Validation: unique keys, provenance, blanks-never-zero, cross-checks against independent evidence, coverage census,
reason-coded gaps, request manifest, scope registry resolution. Writes CSV/JSON next to the data tables."""
from __future__ import annotations
import csv, json, re
from collections import Counter, defaultdict
from pathlib import Path

from . import config as C
from . import parsers as P
from .util import atomic_write_csv, atomic_write_json, sha256_bytes, utc_now

REVIEW = Path('C:/melange-data/forecast-redesign-20261001-review')
OLD = Path('C:/Users/pgoff/Mentat/outputs/opensecrets-2008-2026-20261001')
BROWSER_JSON = REVIEW / 'data' / 'NATIONAL_CANDIDATE_BROWSER_SOURCES.json'
LOBBY_CSV_DIR = REVIEW / 'source-recovery' / 'lobbying'

KEYS = {
    'national_candidate_by_office': ['requested_cycle', 'office', 'party'],
    'national_candidate_giving': ['requested_cycle', 'donor_type', 'party', 'office_scope'],
    'national_election_cost': ['requested_cycle'],
    'pac_industry_breakdown': ['requested_cycle', 'industry_code'],
    'pac_industry_candidate_totals': ['scope_id', 'requested_cycle'],
    'pac_roster': ['scope_id', 'requested_cycle', 'pac_id'],
    'pac_membership_crosswalk': ['requested_cycle', 'pac_id'],
    'pac_pages': ['pac_id', 'requested_cycle'],
    'pac_chamber_party': ['pac_id', 'requested_cycle', 'chamber', 'party_group'],
    'pac_candidate_giving_industry': ['scope_id', 'requested_cycle', 'chamber', 'party_group'],
    'individual_candidate_giving_industry': ['scope_id', 'requested_cycle', 'chamber', 'party_group'],
    'legacy_candidate_combined_by_chamber_party': ['scope_id', 'requested_cycle', 'list_chamber', 'party_group'],
    'industry_totals': ['scope_id', 'requested_cycle'],
    'lobbying_annual': ['scope_id', 'requested_year'],
}
MONEY_COLS = re.compile(r'_usd$')


def _read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with open(path, encoding='utf-8-sig', newline='') as fh:
        return list(csv.DictReader(fh))


def _num(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, check_id, description, status, expected='', actual='', detail=''):
        plain = lambda v: v if isinstance(v, (str, int, float, bool)) or v is None else str(v)   # dict/tuple vectors are stored as text (JSON keys must be strings)
        self.rows.append({'check_id': check_id, 'description': description, 'status': status, 'expected': plain(expected), 'actual': plain(actual), 'detail': detail})

    def eq(self, check_id, description, expected, actual, detail=''):
        self.add(check_id, description, 'pass' if expected == actual else 'FAIL', expected, actual, detail)


def run_validation(a, ex, tables, out_dir):
    out = Path(out_dir)
    ck = Checks()
    t = tables
    # --- structural ------------------------------------------------------------------------------
    for name, keys in KEYS.items():
        seen = Counter(tuple(str(r.get(k, '')) for k in keys) for r in t[name])
        dup = [k for k, n in seen.items() if n > 1]
        ck.add(f'unique_keys:{name}', f'unique key {keys}', 'pass' if not dup else 'FAIL', 0, len(dup), str(dup[:3]))
    prov_bad = sum(1 for name, rows in t.items() if name != 'pac_membership_crosswalk' for r in rows   # crosswalk carries source_urls (plural)
                   if r.get('extraction_status') == 'parsed' and not (r.get('source_url') and r.get('retrieved_utc') and r.get('source_sha256')))
    ck.add('provenance_on_parsed_rows', 'every parsed row has source_url, retrieved_utc, source_sha256', 'pass' if prov_bad == 0 else 'FAIL', 0, prov_bad)
    zero_unavailable = sum(1 for rows in t.values() for r in rows if r.get('completeness_status') == 'unavailable'
                           for k, v in r.items() if MONEY_COLS.search(k) and str(v) == '0')
    ck.add('blanks_never_zero', 'unavailable rows carry no zero-valued money cells', 'pass' if zero_unavailable == 0 else 'FAIL', 0, zero_unavailable)
    ck.add('negative_amounts_preserved', 'negative signed net recipient amounts kept (info)', 'info', '>0 expected',
           sum(1 for r in t['pac_recipients'] if _num(r['amount_usd']) is not None and _num(r['amount_usd']) < 0))
    # --- cache integrity (every byte re-hashed) ---------------------------------------------------------
    bad = n = 0
    cache_metadata = []
    for meta_p in sorted(Path(ex.f.cache_dir).glob('*/*.meta.json')):
        meta = json.loads(meta_p.read_text(encoding='utf-8'))
        cache_metadata.append((meta_p, meta))
        body_p = meta_p.with_name(meta_p.name.replace('.meta.json', '.body'))
        if meta.get('http_status') == 200 and body_p.exists():
            n += 1
            if sha256_bytes(body_p.read_bytes()) != meta.get('sha256'):
                bad += 1
    ck.add('cache_sha256_byte_exact', f'{n} cached bodies re-hashed equal recorded sha256', 'pass' if bad == 0 else 'FAIL', 0, bad)
    national_checks(ck, t)
    pac_checks(ck, t)
    rest_checks(ck, t, ex)
    # --- outputs -----------------------------------------------------------------------------------------------
    write_census_gaps(t, out)
    write_manifest(ex, out, cache_metadata)
    write_registry(ex, out)
    atomic_write_csv(out / 'crosschecks.csv', ['check_id', 'description', 'status', 'expected', 'actual', 'detail'], ck.rows)
    summary = Counter(r['status'] for r in ck.rows)
    failed = [r['check_id'] for r in ck.rows if r['status'] == 'FAIL']
    atomic_write_json(out / 'validation.json', {'checked_utc': utc_now(), 'summary': dict(summary), 'failed': failed, 'checks': ck.rows})
    print(f'[validate] {dict(summary)}; failed={failed}', flush=True)
    return ck


def run_national_validation(tables, out_dir):
    """Standalone national-only validation (offline): writes national_crosschecks.csv next to the national CSVs."""
    ck = Checks()
    national_checks(ck, tables)
    out = Path(out_dir)
    atomic_write_csv(out / 'national_crosschecks.csv', ['check_id', 'description', 'status', 'expected', 'actual', 'detail'], ck.rows)
    print(f"[validate-national] {dict(Counter(r['status'] for r in ck.rows))}; failed={[r['check_id'] for r in ck.rows if r['status'] == 'FAIL']}", flush=True)
    return ck


def national_checks(ck, t):
    # --- national vs independent browser evidence -------------------------------------------------------
    if BROWSER_JSON.exists():
        br = json.loads(BROWSER_JSON.read_text(encoding='utf-8'))
        mine = {(r['requested_cycle'], r['office'], r['party']): r for r in t['national_candidate_by_office'] if r['extraction_status'] == 'parsed'}
        cells = mism = missing = 0
        for rec in br:
            cy = int(rec['cycle'])
            for off, tbl in zip(rec['offices'], rec['tables']):
                for row in tbl:
                    m = mine.get((cy, off, row[0]))
                    for val, col in ((row[2], 'from_pacs_usd'), (row[3], 'from_individuals_usd')):
                        cells += 1
                        if m is None:
                            missing += 1
                        elif _num(m[col]) != int(val.replace('$', '').replace(',', '')):
                            mism += 1
        ck.add('national_vs_browser_json', 'parsed overview donor cells equal independent browser capture (9 cycles/69 rows/138 cells)',
               'pass' if (mism == 0 and missing == 0 and cells == 138) else 'FAIL', '138 cells, 0 mismatch', f'{cells} cells, {mism} mismatch, {missing} missing')
    v = {(r['requested_cycle'], r['office'], r['party']): r for r in t['national_candidate_by_office']}
    if (2024, 'House', 'All') in v:
        g = lambda o, c: _num(v[(2024, o, 'All')][c])
        ck.eq('national_2024_vector', '2024 All-party PAC P/H/S then individuals P/H/S', (1187730, 422640137, 87386285, 1802512049, 1247529449, 1183616110),
              (g('Presidential', 'from_pacs_usd'), g('House', 'from_pacs_usd'), g('Senate', 'from_pacs_usd'),
               g('Presidential', 'from_individuals_usd'), g('House', 'from_individuals_usd'), g('Senate', 'from_individuals_usd')))
    if (2012, 'Presidential', 'All') in v and (2012, 'Presidential', 'Repubs') in v:
        a_, r_ = _num(v[(2012, 'Presidential', 'All')]['from_pacs_usd']), _num(v[(2012, 'Presidential', 'Repubs')]['from_pacs_usd'])
        ck.add('national_2012_pres_all_below_R_preserved', '2012 Presidential All PAC (1,681,812) < Republican PAC (1,706,312) kept unclamped',
               'pass' if (a_, r_) == (1681812, 1706312) else 'FAIL', '1681812<1706312', f'{a_} vs {r_}')
    srv = [r for r in t['national_candidate_by_office'] if r['requested_cycle'] == 2026]
    ck.add('national_2026_not_relabelled', '2026 overview request never yields 2026-labelled amounts unless the page really serves 2026', 'info',
           'mismatch/failed rows or true 2026', '; '.join(sorted({f"{r['extraction_status']}:{r['served_cycle']}" for r in srv})))
    parsed = [r for r in t['national_candidate_by_office'] if r['extraction_status'] in ('parsed', 'incomplete_inputs')]
    bad_ctl = [(r['requested_cycle'], r['office'], r['party']) for r in parsed
               if r['candidate_universe'] != 'All candidates' or r['display_type'] != 'Display totals' or not str(r['table_caption']).startswith('Financial activity for all ')]
    ck.add('national_controls_derived', 'every parsed office row carries the ACTUAL selected/default controls (All candidates, Display totals) and an all-candidates caption',
           'pass' if (parsed and not bad_ctl) else 'FAIL', '0 rows with other universe/display', f'{len(bad_ctl)} of {len(parsed)}', str(bad_ctl[:3]))
    agg = t['national_candidate_giving']
    gap26 = [r for r in agg if r['requested_cycle'] == 2026]
    ck.add('national_2026_gap_aggregate_rows', '2026 has explicit reason-coded unavailable aggregate rows (12 = 2 donors x 3 parties x ... house_senate only), no amounts',
           'pass' if (gap26 and all(r['completeness_status'] == 'unavailable' and r['amount_usd'] == '' and r['reason_code'] for r in gap26)) else 'FAIL',
           '>0 rows, all unavailable/blank/reason-coded', f'{len(gap26)} rows')
    cov = defaultdict(set)
    for r in agg:
        if r['completeness_status'] == 'complete':
            cov[(r['requested_cycle'], r['office_scope'])].add(r['offices_included'])
    wrong = [(k, v) for k, v in cov.items() if v != ({'Presidential+House+Senate'} if k[1] == 'pres_house_senate' else {'House+Senate'})]
    ck.add('national_offices_included_explicit', 'complete aggregates state actual offices (P+H+S only in presidential-year scope; H+S otherwise; midterm Presidential absent, not zero)',
           'pass' if (cov and not wrong) else 'FAIL', 0, len(wrong), str(wrong[:3]))
    ck.add('national_aggregate_cycles', 'complete house_senate aggregate covers each published cycle 2008-2024',
           'pass' if {k[0] for k in cov if k[1] == 'house_senate'} >= set(range(2008, 2025, 2)) else 'FAIL', '9 cycles', sorted({k[0] for k in cov if k[1] == 'house_senate'}))


def pac_checks(ck, t):
    # --- PAC vectors ---------------------------------------------------------------------------------
    aba = {(r['chamber'], r['party_group']): _num(r['amount_usd']) for r in t['pac_chamber_party'] if r['pac_id'] == 'C00004275' and r['requested_cycle'] == 2024}
    if aba:
        ck.eq('aba_2024_vector', 'ABA 2024 House D/R, Senate D/R', {('House', 'D'): 780500, ('House', 'R'): 1464999, ('Senate', 'D'): 57500, ('Senate', 'R'): 136000},
              {k: aba.get(k) for k in (('House', 'D'), ('House', 'R'), ('Senate', 'D'), ('Senate', 'R'))})
        other = [_num(r['recipient_rows_sum_usd']) for r in t['pac_chamber_party'] if r['pac_id'] == 'C00004275' and r['requested_cycle'] == 2024 and r['party_group'] == 'Other']
        ck.add('aba_2024_senate_independents', 'Senate non-D/R (King 10,000 + Sinema 5,000) kept as Other; D/R is not all-party', 'pass' if other == [15000] else 'FAIL', '[15000]', str(other))
    det = [r for r in t['pac_industry_candidate_totals'] if r['extraction_status'] == 'parsed']
    bad = [r for r in det if r['completeness_status'] != 'complete']
    unexplained = [r for r in bad if not r['reason_code']]
    ck.add('pac_roster_equals_headline', 'every industry-cycle roster is either complete (unique PAC count, money, D/R/total equal the headline) or carries a reason code; source discrepancies stay visible as partial',
           'pass' if not unexplained else 'FAIL', f'{len(det)} rows, 0 unexplained', f"{len(det) - len(bad)} complete, {len(bad)} partial-with-reason, {len(unexplained)} unexplained",
           str([(r['scope_id'], r['requested_cycle'], r['reason_code']) for r in bad[:6]]))
    mm = [r for r in det if str(r['breakdown_matches_detail']) == 'False']
    ck.add('breakdown_equals_detail', 'industry-breakdown row vs industry-detail headline: any difference is a source discrepancy reported here (info), never silently reconciled',
           'info', 0, len(mm), str([(r['scope_id'], r['requested_cycle']) for r in mm[:5]]))
    xw = [r for r in t['pac_membership_crosswalk'] if len(r['source_urls'].split('|')) != len(r['source_retrieved_utc'].split('|')) or not r['source_retrieved_utc']
          or len(r['source_urls'].split('|')) != len(r['source_sha256s'].split('|'))]
    ck.add('crosswalk_url_capture_pairs', 'every crosswalk source URL is paired with a capture timestamp and sha256', 'pass' if not xw else 'FAIL', 0, len(xw))
    f03 = {r['requested_cycle']: r for r in det if r['scope_id'] == 'commercial_banks'}
    if 2024 in f03:
        ck.eq('f03_2024_detail_vector', 'F03 2024 total/D/R/PACs', (11633976, 4554978, 7033998, 78),
              (_num(f03[2024]['total_usd']), _num(f03[2024]['to_democrats_usd']), _num(f03[2024]['to_republicans_usd']), _num(f03[2024]['n_pacs_headline'])))
    if 2018 in f03:
        ck.eq('f03_2018_vector_stale_href_trap', 'F03 2018 via detail/F03/2018 (breakdown row hrefs end 2024)', (13828165, 4213679, 9558486),
              (_num(f03[2018]['total_usd']), _num(f03[2018]['to_democrats_usd']), _num(f03[2018]['to_republicans_usd'])))
    ind = [r for r in t['pac_candidate_giving_industry'] if r['extraction_status'] == 'parsed' and r['party_group'] in ('D', 'R')]
    ck.add('pac_industry_chamber_completeness', 'industry chamber x party cells by completeness', 'info', '', dict(Counter(r['completeness_status'] for r in ind)))
    unrec = [r for r in ind if r['completeness_status'] == 'complete' and (r['headline_minus_chambers_incl_presidential_usd'] not in ('0', 0) or r['amount_usd'] == ''
                                                                            or r['amount_status'] != 'exact' or r['pacs_missing'] not in ('0', 0))]
    ck.add('pac_complete_cells_reconcile_headline', 'complete industry D/R cells: House+Senate+Presidential sums equal the industry headline, all PAC pages retrieved, amounts exact',
           'pass' if not unrec else 'FAIL', 0, len(unrec),
           str([(r['scope_id'], r['requested_cycle'], r['party_group'], r['headline_minus_chambers_incl_presidential_usd']) for r in unrec[:5]]))
    leak = [r for r in t['pac_candidate_giving_industry'] if r['completeness_status'] != 'complete' and r['amount_usd'] != '']
    ck.add('pac_exact_amount_only_when_complete', 'amount_usd is blank unless the cell is complete (partials live in partial_sum_usd)', 'pass' if not leak else 'FAIL', 0, len(leak))
    ck.add('pac_pages_status', 'deduplicated PAC-cycle pages by extraction status', 'info', '', dict(Counter(r['extraction_status'] for r in t['pac_pages'])))
    ck.add('pac_pages_reconcile', 'PAC pages whose House+Senate D/R equal the PAC headline', 'info', '',
           dict(Counter(str(r['reconciles_to_headline']) for r in t['pac_pages'] if r['extraction_status'] == 'parsed')))


def rest_checks(ck, t, ex):
    # --- legacy / old-collector baseline -------------------------------------------------------------------
    new_tot = {(r['opensecrets_code'], str(r['requested_cycle'])): r for r in t['industry_totals'] if r['extraction_status'] == 'parsed'}
    cmp_n = diff = 0
    for r in _read_csv(OLD / 'csv' / 'industry_totals.csv'):
        if r.get('status') in ('observed', 'source_reconciliation_difference') and r.get('total_usd'):
            n = new_tot.get((r['opensecrets_code'], str(r['cycle'])))
            if n:
                cmp_n += 1
                diff += 0 if _num(n['total_usd']) == _num(r['total_usd']) else 1
    ck.add('industry_totals_vs_old_collector', 'new legacy industry totals equal old collector observed rows', 'pass' if (cmp_n and diff == 0) else ('FAIL' if diff else 'info'),
           f'{cmp_n} rows equal', f'{cmp_n} compared, {diff} differ')
    old_c = _read_csv(OLD / 'csv' / 'candidate_combined_detail.csv')
    if old_c:
        oldn = Counter((r['opensecrets_code'], str(r['cycle']), r['chamber']) for r in old_c if r.get('status') == 'observed')
        newn = Counter((r['opensecrets_code'], str(r['requested_cycle']), r['list_chamber']) for r in t['legacy_candidate_combined'])
        same = sum(1 for k, n in oldn.items() if newn.get(k) == n)
        ck.add('legacy_candidate_rows_vs_old_collector', 'row counts per scope-cycle-chamber equal old collector', 'pass' if same == len(oldn) else 'info', len(oldn), same,
               f'old observed cells {len(oldn)}; new matching {same}')
    old_top = [r for r in _read_csv(OLD / 'csv' / 'top_contributors.csv') if r.get('status') == 'observed']
    ck.add('top_contributor_rows_vs_old', 'observed top-contributor rows (old collector true count 1238, not 1260)', 'info', 1238,
           f"old={len(old_top)} new={sum(1 for r in t['top_contributors'] if r['extraction_status'] == 'parsed')}")
    old_cost = {r['cycle']: r for r in _read_csv(OLD / 'csv' / 'national_election_cost.csv') if r.get('status') in ('observed', 'source_reconciliation_difference')}
    bad_c = sum(1 for r in t['national_election_cost'] if r['extraction_status'] == 'parsed' and str(r['requested_cycle']) in old_cost
                and _num(old_cost[str(r['requested_cycle'])]['total_usd']) != _num(r['total_usd']))
    ck.add('election_cost_vs_old', 'nominal election cost equals old collector', 'pass' if bad_c == 0 else 'FAIL', 0, bad_c)
    # --- lobbying ------------------------------------------------------------------------------------
    la = {(r['scope_id'], str(r['requested_year'])): r for r in t['lobbying_annual']}
    csv_map = {'insurance': 'insurance-annual-lobbying-spending.csv', 'commercial_banks': 'commercial-banks-annual-lobbying-spending.csv',
               'credit_unions': 'credit-unions-annual-lobbying-spending.csv', 'automotive_industry': 'automotive-annual-lobbying-spending.csv',
               'telecom_services': 'telecom-services-annual-lobbying-spending.csv'}
    for sid, fn in csv_map.items():
        rows = _read_csv(LOBBY_CSV_DIR / fn)
        if not rows:
            continue
        have = [r for r in rows if int(r['Year']) >= 2008 and (sid, r['Year']) in la and la[(sid, r['Year'])]['spend_usd'] != '']
        diffs = [(r['Year'], la[(sid, r['Year'])]['spend_usd'], r['Spending']) for r in have if _num(la[(sid, r['Year'])]['spend_usd']) != _num(r['Spending'])]
        ck.add(f'lobby_annual_vs_browser_csv:{sid}', f'annual chart years collected so far equal native Export-as-CSV ({fn}); uncollected years are gaps, not mismatches',
               'pass' if (not diffs and have) else ('FAIL' if diffs else 'info'), 0, len(diffs), f'{len(have)} years compared of {len([r for r in rows if int(r["Year"]) >= 2008])}; ' + str(diffs[:3]))
    t21 = {r.get('Year') or r.get('year'): r for r in _read_csv(LOBBY_CSV_DIR / 'T2100_annual_browser_capture.csv')}
    if t21:
        cols = list(next(iter(t21.values())).keys())
        valcol = next((c for c in cols if re.search(r'spend|amount|value|total', c, re.I)), cols[-1])
        diffs = [(y, la[('auto_manufacturers', y)]['spend_usd'], r[valcol]) for y, r in t21.items()
                 if y and y.isdigit() and int(y) >= 2008 and ('auto_manufacturers', y) in la and _num(la[('auto_manufacturers', y)]['spend_usd']) != _num(r[valcol])]
        ck.add('lobby_T2100_vs_browser_capture', 'legacy T2100 annual series equals browser capture', 'pass' if not diffs else 'FAIL', 0, len(diffs), str(diffs[:3]))
    vec = {('insurance', '2026'): (88178939, 179), ('commercial_banks', '2026'): (44990209, 96), ('credit_unions', '2026'): (4153000, 16),
           ('automotive_industry', '2026'): (64603605, 138), ('telecom_services', '2026'): (59292390, 126), ('auto_manufacturers', '2026'): (22925589, None),
           ('auto_manufacturers', '2024'): (48570667, 34)}
    for (sid, y), (sp, nc) in vec.items():
        r = la.get((sid, y))
        if r and r['spend_usd'] != '':
            if nc is not None and r['clients_active'] == '':   # main chunk not collected yet: spend checked, client count not claimed
                ck.eq(f'lobby_vector:{sid}:{y}', f'{sid} {y} spend vs coordinator-verified (client count not collected)', sp, _num(r['spend_usd']))
            else:
                ck.eq(f'lobby_vector:{sid}:{y}', f'{sid} {y} spend/clients vs coordinator-verified', (sp, nc), (_num(r['spend_usd']), _num(r['clients_active']) if nc is not None else None))
        elif r:
            ck.add(f'lobby_vector:{sid}:{y}', f'{sid} {y} not collected yet (gap, not a mismatch)', 'info', (sp, nc), r['reason_code'] or r['extraction_status'])
    sums = []
    by_client = defaultdict(int)
    for c in t['lobbying_clients']:
        if c['extraction_status'] == 'parsed' and c['source_generation'] == 'modern':
            by_client[(c['scope_id'], str(c['requested_year']))] += _num(c['spend_usd']) or 0
    for (sid, y), r in la.items():
        if r['extraction_status'] == 'parsed' and r['source_generation'] == 'modern' and r['client_rows_parsed'] not in ('', None):
            if by_client[(sid, y)] != _num(r['spend_usd']):
                sums.append((sid, y, by_client[(sid, y)] - _num(r['spend_usd'])))
    ck.add('lobby_client_sum_vs_annual', 'sum of Client/Parent rows vs chart annual spend (modern)', 'pass' if not sums else 'info', 0, len(sums), str(sums[:4]))
    ck.add('lobby_F09_label', 'F09 labelled Insurance (broad); never P&C-only', 'pass' if all('Property' not in (r['source_category_title'] or '') for r in t['lobbying_annual'] if r['scope_id'] == 'insurance') else 'FAIL', '', '')
    asof = ex.asof
    ck.add('lobby_asof_2026', '2026 lobbying as-of 2026-07-23 / period end 2026-06-30 parsed from top-industries note', 'pass' if (asof.get('as_of') == '2026-07-23' and asof.get('end') == '2026-06-30') else 'FAIL',
           '2026-07-23/2026-06-30', f"{asof.get('as_of')}/{asof.get('end')}")
    ck.add('lobby_in_house_outside_status', 'annual rows by in-house/outside status', 'info', '', dict(Counter(r['in_house_outside_status'] for r in t['lobbying_annual'])))
    ex_rows = [r for r in t['lobbying_annual'] if r['in_house_outside_status'] == 'complete_exact']
    bad_ex = [(r['scope_id'], r['requested_year']) for r in ex_rows if not (
        r['in_house_usd'] != '' and r['outside_firm_usd'] != '' and _num(r['in_house_usd']) + _num(r['outside_firm_usd']) == _num(r['spend_usd'])
        and r['clients_active'] != '' and _num(r['clients_split_reconciled']) == _num(r['clients_active']) and _num(r['client_rows_parsed']) == _num(r['clients_active'])
        and r['in_house_outside_reason'] == '')]
    ck.add('lobby_complete_exact_is_exact', 'complete_exact rows: components sum to the industry spend, every source client reconciled, no failing predicate', 'pass' if not bad_ex else 'FAIL', 0, len(bad_ex), str(bad_ex[:4]))
    leak = [(r['scope_id'], r['requested_year']) for r in t['lobbying_annual'] if r['in_house_outside_status'] != 'complete_exact' and (r['in_house_usd'] != '' or r['outside_firm_usd'] != '')]
    ck.add('lobby_exact_blank_unless_complete', 'exact in-house/outside columns are blank unless complete_exact (partial sums use separate columns)', 'pass' if not leak else 'FAIL', 0, len(leak), str(leak[:4]))
    acu = [r for r in t['lobbying_client_splits'] if r['extraction_status'] == 'parsed' and r['client_id'] == '141826' and str(r['requested_year']) == '2026']
    if acu:
        ck.eq('acu_2026_split_unreconciled', 'ACU 2026 client split in-house 2,206,000 + outside 518,000 = 2,724,000 stays unreconciled to parent 2,988,000',
              (2206000, 518000, 2724000, 2988000, 'client_total_equals_industry_amount_and_split_sums' != acu[0]['reconciliation_flag']),
              (acu[0]['in_house_usd'], acu[0]['outside_firms_usd'], acu[0]['split_sum_usd'], acu[0]['client_year_total_usd'], True))
    org_bad = [(r['org_id'], r['cycle']) for r in t['org_totals_history'] if r['completeness_status'] == 'complete' and not (
        r['by_party_row_present'] in ('True', True) and r['by_source_row_present'] in ('True', True)
        and all(r[k] != '' for k in ('total_usd', 'democrat_usd', 'republican_usd', 'individual_usd', 'pac_usd', 'soft_individual_usd', 'soft_organization_usd')))]
    ck.add('org_complete_requires_all_components', 'org history rows marked complete have every party and source component present', 'pass' if not org_bad else 'FAIL', 0, len(org_bad), str(org_bad[:4]))
    org_src = [(r['organisation'], r['requested_cycle']) for r in t['org_contribution_sources'] if r['profile_total_usd'] != '' and not (
        r['industry_source_url'] and r['industry_source_retrieved_utc'] and r['industry_source_sha256'] and r['source_url'] and r['search_url'] and r['search_sha256'])]
    ck.add('org_joined_rows_carry_both_origins', 'joined org rows keep industry-page operand URL/capture/hash separately from profile and search provenance', 'pass' if not org_src else 'FAIL', 0, len(org_src), str(org_src[:3]))
    rc = t['org_roster_crosswalk']
    ck.add('org_roster_crosswalk_census', 'roster crosswalk: one row per roster company, match outcomes preserved (exact / ambiguous / none / not collected)', 'info', 80,
           len(rc), str(dict(Counter(r['match_status'] or r['reason_code'] for r in rc))))
    # --- orgs --------------------------------------------------------------------------------------------
    d = {int(r['cycle']): r for r in t['org_totals_history'] if r['org_slug'] == 'bank-of-america'}
    if 2024 in d and 2008 in d:
        ck.eq('boa_2024_vector', 'BoA 2024 total/D/R/individual/PAC/softInd/softOrg', (4231320, 2000278, 1973367, 3308282, 710000, 212554, 484),
              tuple(_num(d[2024][k]) for k in ('total_usd', 'democrat_usd', 'republican_usd', 'individual_usd', 'pac_usd', 'soft_individual_usd', 'soft_organization_usd')))
        ck.eq('boa_2008_vector', 'BoA 2008 total/individual/PAC/softInd/softOrg', (3669164, 1657143, 1996071, 5945, 10005),
              tuple(_num(d[2008][k]) for k in ('total_usd', 'individual_usd', 'pac_usd', 'soft_individual_usd', 'soft_organization_usd')))
    ck.add('org_match_status', 'organisation exact-match outcomes (top-contributor rows)', 'info', '',
           dict(Counter(r['org_search_status'] or r['reason_code'] for r in t['org_contribution_sources'])))


def write_census_gaps(t, out):
    census, gaps = [], []
    for name, rows in t.items():
        grp = defaultdict(list)
        for r in rows:
            period = r.get('requested_cycle') or r.get('requested_year') or r.get('cycle') or ''
            grp[(r.get('scope_id', ''), str(period))].append(r)
        for (sid, per), rs in sorted(grp.items()):
            census.append({'table': name, 'scope_id': sid, 'period': per, 'rows': len(rs),
                           'extraction_status': json.dumps(dict(Counter(x.get('extraction_status', '') for x in rs))),
                           'completeness_status': json.dumps(dict(Counter(x.get('completeness_status', '') for x in rs))),
                           'reason_codes': '|'.join(sorted({x['reason_code'] for x in rs if x.get('reason_code')}))})
        for r in rows:
            if r.get('completeness_status') in ('unavailable', 'partial') or r.get('extraction_status') not in ('parsed', ''):
                item = r.get('pac_id') or r.get('organisation') or r.get('client') or r.get('office') or ''
                if r.get('chamber') or r.get('list_chamber'):
                    item = f"{r.get('chamber') or r.get('list_chamber')}/{r.get('party_group', '')}"
                gaps.append({'table': name, 'scope_id': r.get('scope_id', ''), 'period': r.get('requested_cycle') or r.get('requested_year') or r.get('cycle') or '',
                             'item': item, 'extraction_status': r.get('extraction_status', ''), 'completeness_status': r.get('completeness_status', ''),
                             'reason_code': r.get('reason_code', ''), 'source_url': r.get('source_url', ''), 'notes': r.get('notes', '')})
    atomic_write_csv(out / 'coverage_census.csv', ['table', 'scope_id', 'period', 'rows', 'extraction_status', 'completeness_status', 'reason_codes'], census)
    atomic_write_csv(out / 'gaps.csv', ['table', 'scope_id', 'period', 'item', 'extraction_status', 'completeness_status', 'reason_code', 'source_url', 'notes'], gaps)
    summ = Counter((g['table'], g['reason_code'] or g['extraction_status']) for g in gaps)
    atomic_write_csv(out / 'gap_summary.csv', ['table', 'reason_code', 'rows'], [{'table': k[0], 'reason_code': k[1], 'rows': v} for k, v in sorted(summ.items())])


def write_manifest(ex, out, cache_metadata=None):
    rows = []
    if cache_metadata is None:
        cache_metadata = [(p, json.loads(p.read_text(encoding='utf-8')))
                          for p in sorted(Path(ex.f.cache_dir).glob('*/*.meta.json'))]
    for meta_p, m in cache_metadata:
        rows.append({'source_url': m.get('source_url'), 'cache_key': meta_p.name.replace('.meta.json', ''), 'http_status': m.get('http_status'), 'bytes': m.get('bytes'),
                     'sha256': m.get('sha256'), 'retrieved_utc': m.get('retrieved_utc'), 'transport': m.get('transport'), 'family': m.get('family'),
                     'final_url': m.get('final_url'), 'transport_calls_for_url': m.get('transport_calls') or m.get('physical_requests'), 'redirect_hops': m.get('redirect_hops', ''), 'run_id': m.get('run_id', ''),
                     'resume_after_utc': m.get('resume_after_utc', ''), 'error': m.get('error'),
                     'challenge_content': m.get('challenge_content'), 'content_type': m.get('content_type')})
    atomic_write_csv(out / 'request_manifest.csv', ['source_url', 'cache_key', 'http_status', 'bytes', 'sha256', 'retrieved_utc', 'transport', 'family', 'final_url',
                                                    'transport_calls_for_url', 'redirect_hops', 'run_id', 'resume_after_utc', 'error', 'challenge_content', 'content_type'], rows)


def write_registry(ex, out):
    tax = {}
    res = ex.f.get(C.TAXONOMY_URL)
    if res.ok:
        for a in P.soup_of(res.body).select('a[href*="ind="]'):
            m = re.search(r'ind=([A-Za-z0-9]+)', a['href'])
            if m:
                tax[m.group(1)] = a.get_text(' ', strip=True)
    rows = []
    for s in ex.scopes:
        code = s.get('opensecrets_code', '')
        rows.append({'scope_id': s['scope_id'], 'scope_name': s['name'], 'opensecrets_code': code, 'classification': s.get('classification', ''),
                     'mentat_key': s.get('mentat_key', ''), 'relation': s['relation'], 'published_taxonomy_name': tax.get(code, '') if code else '',
                     'taxonomy_status': ('published' if code in tax else 'code_not_found_in_slist') if code else 'no_verified_exact_mapping_found_in_inspected_sources',
                     'lobby_category_id': s.get('lobby_category_id', ''), 'lobby_slug': s.get('lobby_slug', ''), 'scope_note': s['scope_note']})
    atomic_write_csv(out / 'scope_registry_resolved.csv', ['scope_id', 'scope_name', 'opensecrets_code', 'classification', 'mentat_key', 'relation', 'published_taxonomy_name',
                                                           'taxonomy_status', 'lobby_category_id', 'lobby_slug', 'scope_note'], rows)
    atomic_write_json(out / 'source_taxonomy.json', {'source_url': C.TAXONOMY_URL, 'retrieved_utc': res.meta.get('retrieved_utc'), 'sha256': res.meta.get('sha256'), 'industries': tax})
