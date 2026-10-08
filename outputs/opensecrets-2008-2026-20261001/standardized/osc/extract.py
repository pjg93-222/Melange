"""Offline extraction: per-URL cache -> standardized CSV tables. Never touches the network (cache_only fetcher).

Every row carries: source_url, final_url, http_status, retrieved_utc (capture), source_sha256, cache_key, source_generation,
source_vintage / source_release_date (FEC or platform release), source_cutoff_date + basis (reporting cutoff, separate from
capture), extraction_status (did parsing work) and completeness_status (is the source complete), reason_code, notes.
Missing is blank, never zero. Signed net amounts (refunds) are preserved.
"""
from __future__ import annotations
import re
from collections import defaultdict
from pathlib import Path

from . import config as C
from . import parsers as P
from .runner import Runner
from .util import atomic_write_csv, normalized

ID = ['scope_id', 'scope_name', 'opensecrets_code', 'scope_classification', 'mentat_key', 'scope_relation']
PROV = ['source_url', 'final_url', 'http_status', 'retrieved_utc', 'source_sha256', 'cache_key', 'source_generation',
        'source_vintage', 'source_release_date', 'source_cutoff_date', 'source_cutoff_basis',
        'extraction_status', 'completeness_status', 'reason_code', 'notes']
CY = ['requested_cycle', 'served_cycle']
YR = ['requested_year', 'served_year']
CUT_NONE = 'reporting_cutoff_not_stated_on_page'

SCHEMAS = {
    'national_candidate_by_office': CY + ['office', 'party', 'n_candidates', 'total_raised_usd', 'total_spent_usd', 'cash_on_hand_usd',
                                          'from_pacs_usd', 'from_individuals_usd', 'candidate_universe', 'display_type', 'control_type_value',
                                          'control_display_value', 'controls_basis', 'table_caption'] + PROV,
    'national_candidate_giving': CY + ['donor_type', 'party', 'party_universe', 'office_scope', 'amount_usd', 'offices_included',
                                       'offices_expected', 'all_party_amount_usd', 'other_party_residual_signed_usd', 'candidate_universe',
                                       'display_type', 'controls_basis', 'coverage_note', 'money_universe'] + PROV,
    'national_election_cost': CY + ['total_usd', 'presidential_usd', 'congressional_usd', 'sum_check_delta_usd', 'asterisk_flag', 'dollar_basis'] + PROV,
    'pac_industry_breakdown': CY + ['industry_code', 'industry_name', 'classification', 'hierarchy_note', 'total_usd', 'to_democrats_usd',
                                    'to_republicans_usd', 'other_party_residual_signed_usd', 'row_detail_href', 'row_href_cycle', 'row_href_cycle_stale'] + PROV,
    'pac_industry_candidate_totals': ID + CY + ['total_usd', 'to_democrats_usd', 'to_republicans_usd', 'other_party_residual_signed_usd',
                                                'n_pacs_headline', 'n_pac_rows', 'roster_sum_total_usd', 'roster_sum_democrat_usd',
                                                'roster_sum_republican_usd', 'roster_minus_headline_democrat_usd', 'roster_minus_headline_republican_usd',
                                                'breakdown_total_usd', 'breakdown_matches_detail'] + PROV,
    'pac_roster': ID + CY + ['pac_id', 'pac_name', 'pac_slug', 'affiliate', 'lean', 'total_usd', 'to_democrats_usd', 'to_republicans_usd',
                             'other_party_residual_signed_usd', 'summary_url', 'summary_href_cycle'] + PROV,
    'pac_membership_crosswalk': ['requested_cycle', 'pac_id', 'pac_name', 'scope_ids', 'scope_codes', 'n_scopes', 'overlap_note', 'source_urls',
                                 'source_retrieved_utc', 'source_sha256s', 'source_capture_pairs', 'extraction_status', 'completeness_status', 'reason_code'],
    'pac_pages': ['pac_id', 'pac_name', 'pac_slug'] + CY + ['page_url', 'headline_total_usd', 'headline_democrat_usd', 'headline_republican_usd',
                                                         'house_recipient_rows', 'senate_recipient_rows', 'tables_seen',
                                                         'chamber_dr_sum_democrat_usd', 'chamber_dr_sum_republican_usd',
                                                         'headline_minus_chamber_democrat_usd', 'headline_minus_chamber_republican_usd',
                                                         'presidential_recipient_rows', 'missing_amount_cells', 'all_party_sum_usd',
                                                         'all_party_reconciles_to_headline_total', 'negative_amount_rows', 'reconciles_to_headline'] + PROV,
    'pac_chamber_party': ['pac_id'] + CY + ['chamber', 'party_group', 'summary_table_amount_usd', 'recipient_rows_sum_usd', 'n_recipients',
                                            'amount_usd', 'amount_basis', 'summary_minus_rows_usd'] + PROV,
    'pac_recipients': ['pac_id'] + CY + ['chamber', 'candidate', 'sort_name', 'party_code', 'party_group', 'state', 'amount_usd', 'candidate_url'] + PROV,
    'pac_candidate_giving_industry': ID + CY + ['chamber', 'party_group', 'amount_usd', 'partial_sum_usd', 'amount_status', 'pacs_expected_headline',
                                                'pacs_in_roster', 'pacs_unique_ids', 'pacs_duplicate_roster_rows', 'pacs_retrieved', 'pacs_missing',
                                                'pacs_with_missing_money', 'pacs_unreconciled', 'presidential_party_usd', 'industry_headline_party_usd',
                                                'headline_minus_chambers_incl_presidential_usd', 'chamber_sum_minus_headline_usd', 'money_universe'] + PROV,
    'individual_candidate_giving_industry': ID + CY + ['chamber', 'party_group', 'amount_usd', 'industry_individual_total_all_recipients_usd', 'money_universe'] + PROV,
    'legacy_candidate_combined': ID + CY + ['list_chamber', 'recipient', 'party_code', 'party_group', 'state_label', 'state_code',
                                            'combined_pac_individual_usd', 'chamber_basis'] + PROV,
    'legacy_candidate_combined_by_chamber_party': ID + CY + ['list_chamber', 'party_group', 'combined_pac_individual_usd', 'n_rows',
                                                             'n_negative_rows', 'money_universe', 'chamber_basis'] + PROV,
    'industry_totals': ID + CY + ['total_usd', 'individual_usd', 'pac_usd', 'soft_outside_usd', 'democrat_usd', 'republican_usd',
                                  'democrat_pct', 'republican_pct', 'party_pct_basis', 'donor_sum_minus_total_usd'] + PROV,
    'top_contributors': ID + CY + ['rank', 'organisation', 'organisation_normalized', 'total_usd', 'candidates_parties_usd', 'democrat_usd',
                                   'republican_usd', 'outside_groups_usd', 'liberal_groups_usd', 'conservative_groups_usd', 'lean',
                                   'total_minus_cp_plus_outside_usd', 'additivity_flag', 'pac_individual_split_status'] + PROV,
    'org_contribution_sources': ID + CY + ['rank', 'organisation', 'industry_page_total_usd', 'industry_source_url', 'industry_source_retrieved_utc',
                                           'industry_source_sha256', 'org_search_status', 'org_id', 'org_slug', 'profile_total_usd', 'profile_individual_usd',
                                           'profile_pac_usd', 'profile_soft_individual_usd', 'profile_soft_organization_usd', 'profile_democrat_usd',
                                           'profile_republican_usd', 'profile_minus_industry_page_usd', 'scope_mismatch_flag', 'scope_qualification',
                                           'match_qualification', 'n_affiliates_listed', 'affiliates_selected_cycle', 'profile_url', 'search_url',
                                           'search_retrieved_utc', 'search_sha256', 'source_universe'] + PROV,
    'org_totals_history': ['org_id', 'org_slug', 'org_name', 'cycle', 'total_usd', 'democrat_usd', 'republican_usd', 'individual_usd', 'pac_usd',
                           'soft_individual_usd', 'soft_organization_usd', 'by_party_row_present', 'by_source_row_present', 'matched_via', 'scope_ids',
                           'search_url', 'search_retrieved_utc', 'search_sha256', 'profile_url', 'note_527', 'match_qualification'] + PROV,
    'org_roster_crosswalk': ['roster_source_workbook', 'roster_worksheet', 'roster_row_number', 'roster_scope_id', 'roster_mentat_industry',
                             'original_company_name', 'normalized_company_name', 'roster_capture_utc', 'roster_workbook_sha256', 'roster_snapshot_status',
                             'search_url', 'match_status', 'n_org_candidates', 'org_candidates', 'org_id', 'org_slug', 'profile_url',
                             'history_first_cycle', 'history_last_cycle', 'n_history_cycles', 'profile_retrieved_utc', 'profile_sha256',
                             'scope_qualification'] + PROV,
    'lobbying_annual': ID + YR + ['spend_usd', 'source_category_id', 'source_category_title', 'clients_active', 'client_rows_parsed',
                                  'main_chunk_industry_spend_usd', 'chart_minus_main_usd', 'in_house_usd', 'outside_firm_usd',
                                  'in_house_outside_status', 'in_house_outside_reason', 'in_house_partial_sum_usd', 'outside_partial_sum_usd', 'clients_with_split',
                                  'clients_split_reconciled', 'data_as_of_date', 'spending_period_start', 'spending_period_end', 'period_note', 'capture_date', 'capture_timestamp_status'] + PROV,
    'lobbying_annual_offline_export': ID + ['requested_year', 'source_category_id', 'spend_usd', 'lobbyists_count', 'lobbyists_note', 'http_annual_spend_usd',
                                            'comparison', 'source_file', 'source_file_sha256', 'source_method', 'source_page_url', 'capture_date',
                                            'capture_timestamp_status', 'source_as_of_note'] + PROV,
    'lobbying_clients': ID + YR + ['row_order', 'client', 'client_id', 'client_slug', 'spend_usd', 'client_url', 'listing_note'] + PROV,
    'lobbying_client_splits': ID + YR + ['client', 'client_id', 'industry_table_spend_usd', 'client_year_total_usd', 'in_house_usd',
                                         'outside_firms_usd', 'components_explicit', 'split_sum_usd', 'split_sum_minus_page_total_usd',
                                         'page_total_minus_industry_table_usd', 'reconciliation_flag'] + PROV,
}

PAC_OFFICES = ['House', 'Senate', 'Presidential']
NEG_NOTE = 'signed net amounts preserved (negative = refund/net adjustment)'


def _num_eq(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def _iso(text):
    return P.iso_date(text) if text else ''


class Extractor:
    def __init__(self, fetcher, cfg, log=print, roster_csv=None, offline_dir=None, queue_path=None):
        self.f, self.cfg, self.scopes, self.log = fetcher, cfg, cfg['scopes'], log
        self.T = {k: [] for k in SCHEMAS}
        self._cache = {}
        self.runner = Runner(fetcher, cfg, Path(fetcher.data_dir) / 'extract_scratch', tiers=set(), roster_csv=roster_csv)  # planning helpers only (pac_pages/org_names)
        self.asof = {}
        self.queue = self.load_queue(queue_path)       # url -> work-queue entry (state deferred/failed/done + reason) of the last collection
        self.offline = self.load_offline(offline_dir)   # (scope_id, year) -> supplemental native-export info; {} when no directory
        self.breakdown, self.rosters, self.pac_data, self.cross, self.splits, self.headline_eff = {}, {}, {}, {}, {}, {}

    # ---- helpers --------------------------------------------------------------------------
    def idf(self, s):
        return {'scope_id': s['scope_id'], 'scope_name': s['name'], 'opensecrets_code': s.get('opensecrets_code', ''),
                'scope_classification': s.get('classification', ''), 'mentat_key': s.get('mentat_key', ''), 'scope_relation': s['relation']}

    def prov(self, res, meta=None, gen='legacy', status='parsed', complete='complete', reason='', notes='', cutoff='', basis=None):
        m = res.meta if res is not None else {}
        pm = meta or {}
        rel = (pm.get('release_dates') or [''])[0]
        if res is not None and not res.ok and status == 'parsed':
            status, complete, reason = 'fetch_failed', 'unavailable', reason or res.failure_reason
        return {'source_url': res.url if res is not None else '', 'final_url': m.get('final_url', ''), 'http_status': m.get('http_status', ''),
                'retrieved_utc': m.get('retrieved_utc', ''), 'source_sha256': m.get('sha256') or '', 'cache_key': res.key if res is not None else '',
                'source_generation': gen, 'source_vintage': pm.get('release_text', ''), 'source_release_date': _iso(rel),
                'source_cutoff_date': cutoff, 'source_cutoff_basis': basis if basis is not None else (CUT_NONE if not cutoff else ''),
                'extraction_status': status, 'completeness_status': complete, 'reason_code': reason, 'notes': notes}

    def page(self, url, parser, *args, cached_res=None):
        """get + parse once (memoised). Returns (res, parsed|None)."""
        key = (url, parser.__name__, args)
        if key not in self._cache:
            res = cached_res if cached_res is not None else self.f.get(url)
            parsed = None
            if res.ok:
                try:
                    parsed = parser(res.body, *args)
                except Exception as exc:  # noqa: BLE001 - a parser failure is a per-page gap, never a crash
                    res.meta['parse_error'] = f'{type(exc).__name__}: {exc}'[:200]
            self._cache[key] = (res, parsed)
        return self._cache[key]

    @staticmethod
    def load_queue(path):
        import json as _json
        try:
            return {q['url']: q for q in _json.loads(Path(path).read_text(encoding='utf-8'))} if path else {}
        except (OSError, ValueError, KeyError, TypeError):
            return {}

    def fail_reason(self, res):
        if res.ok:
            return 'parser_error'
        if res.meta.get('error') == 'cache_only_miss':   # never fetched: say WHY from the collection queue (deferred by rate limit) instead of a bare cache miss
            q = self.queue.get(res.url)
            return (q.get('reason') or 'deferred_by_server_rate_limit') if q and q.get('state') == 'deferred' else 'not_collected'
        return res.failure_reason or 'unavailable'

    def add(self, table, row):
        self.T[table].append({k: row.get(k, '') for k in SCHEMAS[table]})

    @staticmethod
    def served_note(parsed_cycle, requested):
        return f'page served cycle {parsed_cycle}, requested {requested}; values NOT relabelled'

    def avail(self, family):
        """Cycles the source family's own menu lists (derived from the captured probe page; no hard-coded publication ceiling)."""
        return set(self.runner.cycles_for(family))

    def menu_gap(self, family, c, gen):
        """Provenance for a requested cycle absent from the source menu: evidence is the captured probe page, nothing is requested or relabelled."""
        url = self.runner.probe_url(family)
        res = self.f.get(url) if url else None
        m = self.runner.menu_cycles(family)
        note = (f'{family} cycle menu on {url} lists {min(m)}-{max(m)}; {c} is not listed - not relabelled' if m
                else f'{family} cycle menu unavailable; {c} not attempted')
        return self.prov(res, None, gen, 'not_published', 'unavailable', 'cycle_not_in_source_menu', note)

    # ---- national ---------------------------------------------------------------------------
    def national(self):
        by_cycle, gaps = {}, []
        for c in C.CYCLES:
            res, o = self.page(C.u_overview(c), P.parse_overview, c)
            base = {'requested_cycle': c}
            want = ['Presidential', 'House', 'Senate'] if C.is_pres_year(c) else ['House', 'Senate']
            if o is None:
                reason = self.fail_reason(res)
                self.add('national_candidate_by_office', {**base, **self.prov(res, None, 'modern', 'fetch_failed', 'unavailable', reason)})
                gaps.append((c, res, None, 'fetch_failed', reason, '', ''))
                continue
            if o['served_cycle'] != c:
                note = self.served_note(o['served_cycle'], c)
                self.add('national_candidate_by_office', {**base, 'served_cycle': o['served_cycle'] or '', 'controls_basis': o['controls_basis'],
                         **self.prov(res, o['meta'], 'modern', 'served_cycle_mismatch', 'unavailable', 'served_cycle_mismatch', note)})
                gaps.append((c, res, o, 'served_cycle_mismatch', 'served_cycle_mismatch', o['served_cycle'] or '', note))
                continue
            ctl = {'candidate_universe': o['type_selected'], 'display_type': o['display_selected'], 'controls_basis': o['controls_basis'],
                   'control_type_value': o['controls']['type']['value'], 'control_display_value': o['controls']['display']['value']}
            if not o['universe_ok']:  # actual controls/captions are not All candidates + Display totals: nothing is certified
                self.add('national_candidate_by_office', {**base, 'served_cycle': c, **ctl, **self.prov(
                    res, o['meta'], 'modern', 'candidate_universe_mismatch', 'unavailable', 'wrong_candidate_universe_or_display', o['universe_reject_reason'])})
                gaps.append((c, res, o, 'candidate_universe_mismatch', 'wrong_candidate_universe_or_display', c, o['universe_reject_reason']))
                continue
            for off in want:
                rows = [r for r in o['rows'] if r['office'] == off]
                if not rows:
                    self.add('national_candidate_by_office', {**base, 'served_cycle': c, 'office': off, **ctl,
                             **self.prov(res, o['meta'], 'modern', 'table_missing', 'unavailable', 'office_table_missing')})
                for r in rows:
                    miss = [k for k in ('from_pacs_usd', 'from_individuals_usd') if r[k] is None]
                    self.add('national_candidate_by_office', {**base, 'served_cycle': c, **ctl, 'table_caption': o['captions'].get(off, ''),
                        **{k: ('' if r[k] is None else r[k]) for k in (
                            'office', 'party', 'n_candidates', 'total_raised_usd', 'total_spent_usd', 'cash_on_hand_usd', 'from_pacs_usd', 'from_individuals_usd')},
                        **self.prov(res, o['meta'], 'modern', 'parsed' if not miss else 'incomplete_inputs', 'complete' if not miss else 'partial',
                                    '' if not miss else 'donor_value_missing:' + '+'.join(miss), 'PAC/individual dollars as published; ' + NEG_NOTE)})
            by_cycle[c] = (res, o, want, ctl)
        # exact-vintage aggregation: offices from the SAME page only; explicit two-party D/R scope + all-party control
        for c, (res, o, want, ctl) in by_cycle.items():
            for scope, offs in self._national_scopes(c):
                present = [off for off in offs if any(r['office'] == off for r in o['rows'])]
                for donor, col in (('PAC', 'from_pacs_usd'), ('individual', 'from_individuals_usd')):
                    cell = {}
                    for party in ('All', 'Dems', 'Repubs'):
                        vals = [next((r[col] for r in o['rows'] if r['office'] == off and r['party'] == party), None) for off in offs]
                        cell[party] = sum(vals) if None not in vals else None
                    resid = None if None in cell.values() else cell['All'] - cell['Dems'] - cell['Repubs']
                    for party, label, universe in (('Dems', 'D', 'two_party_D_R'), ('Repubs', 'R', 'two_party_D_R'), ('All', 'All', 'all_parties')):
                        amt = cell[party]
                        self.add('national_candidate_giving', {
                            'requested_cycle': c, 'served_cycle': c, 'donor_type': donor, 'party': label, 'party_universe': universe,
                            'office_scope': scope, 'amount_usd': amt if amt is not None else '', 'offices_included': '+'.join(present),
                            'offices_expected': '+'.join(offs), 'all_party_amount_usd': cell['All'] if cell['All'] is not None else '',
                            'other_party_residual_signed_usd': resid if resid is not None else '', 'controls_basis': ctl['controls_basis'],
                            'candidate_universe': ctl['candidate_universe'], 'display_type': ctl['display_type'],
                            'coverage_note': self._coverage_note(c, scope),
                            'money_universe': 'All candidates as published on elections-overview; sum of office tables from ONE page vintage; '
                                              'D/R rows are two-party only; residual may be negative (not clamped)',
                            **self.prov(res, o['meta'], 'modern', 'parsed' if amt is not None else 'incomplete_inputs',
                                        'complete' if (amt is not None and present == offs) else 'partial', '' if amt is not None else 'office_value_missing')})
        # explicit reason-coded aggregate gap rows: a requested cycle with no usable page is never silently absent (e.g. 2026)
        for c, res, o, status, reason, served, note in gaps:
            for scope, offs in self._national_scopes(c):
                for donor in ('PAC', 'individual'):
                    for label, universe in (('D', 'two_party_D_R'), ('R', 'two_party_D_R'), ('All', 'all_parties')):
                        self.add('national_candidate_giving', {
                            'requested_cycle': c, 'served_cycle': served, 'donor_type': donor, 'party': label, 'party_universe': universe,
                            'office_scope': scope, 'offices_included': '', 'offices_expected': '+'.join(offs),
                            'controls_basis': o['controls_basis'] if o else '', 'candidate_universe': o['type_selected'] if o else '',
                            'display_type': o['display_selected'] if o else '', 'coverage_note': self._coverage_note(c, scope),
                            'money_universe': 'unavailable: no usable All-candidates/Display-totals page for this requested cycle; no amount is inferred or relabelled',
                            **self.prov(res, o['meta'] if o else None, 'modern', status, 'unavailable', reason, note)})

    @staticmethod
    def _national_scopes(c):
        offs = ['Presidential', 'House', 'Senate'] if C.is_pres_year(c) else ['House', 'Senate']
        return ([('pres_house_senate', offs)] if C.is_pres_year(c) else []) + [('house_senate', ['House', 'Senate'])]

    @staticmethod
    def _coverage_note(c, scope):
        if scope == 'house_senate':
            return 'House+Senate only: the consistent all-cycle series (Presidential excluded by construction)' + ('' if C.is_pres_year(c) else '; midterm source has no Presidential table - absent, not zero')
        return 'Presidential+House+Senate, presidential-year sources only'

    def election_cost(self):
        res, d = self.page(C.COST_URL, P.parse_cost_of_election)
        found = {r['cycle']: r for r in d['rows']} if d else {}
        for c in C.CYCLES:
            base = {'requested_cycle': c}
            if d is None:
                self.add('national_election_cost', {**base, **self.prov(res, None, 'legacy', 'fetch_failed', 'unavailable', self.fail_reason(res))})
            elif c in found:
                r = found[c]
                delta = None if None in (r['total_usd'], r['congressional_usd']) else r['total_usd'] - r['congressional_usd'] - (r['presidential_usd'] or 0)
                ok = d['nominal_verified']
                self.add('national_election_cost', {**base, 'served_cycle': c, 'total_usd': r['total_usd'], 'presidential_usd': r['presidential_usd'] if r['presidential_usd'] is not None else '',
                         'congressional_usd': r['congressional_usd'], 'sum_check_delta_usd': delta if delta is not None else '',
                         'asterisk_flag': r['asterisk'], 'dollar_basis': 'nominal USD (?infl=N; infl input verified unchecked)' if ok else 'UNVERIFIED (infl input not confirmed nominal)',
                         **self.prov(res, d['meta'], 'legacy', 'parsed' if ok else 'dollar_basis_unverified', 'complete' if ok else 'partial',
                                     '' if ok else 'infl_input_not_verified', 'presidential blank in midterm cycles (not applicable), never zero')})
            else:
                self.add('national_election_cost', {**base, **self.prov(res, d['meta'], 'legacy', 'not_published', 'unavailable', 'cycle_not_published',
                         f"table spans {min(found) if found else ''}-{max(found) if found else ''}")})

    # ---- PAC ------------------------------------------------------------------------------------
    def pac_breakdown(self):
        for c in C.CYCLES:
            res, b = self.page(C.u_pac_breakdown(c), P.parse_pac_breakdown, c)
            base = {'requested_cycle': c}
            if b is None:
                self.add('pac_industry_breakdown', {**base, **self.prov(res, None, 'modern', 'fetch_failed', 'unavailable', self.fail_reason(res))})
            elif b['served_cycle'] != c:
                self.add('pac_industry_breakdown', {**base, 'served_cycle': b['served_cycle'] or '', **self.prov(
                    res, b['meta'], 'modern', 'served_cycle_mismatch', 'unavailable', 'served_cycle_mismatch', self.served_note(b['served_cycle'], c))})
            else:
                for r in b['rows']:
                    stale = r['href_cycle'] is not None and r['href_cycle'] != c
                    self.breakdown[(c, r['code'])] = r
                    self.add('pac_industry_breakdown', {**base, 'served_cycle': c, 'industry_code': r['code'], 'industry_name': r['name'],
                             'classification': r['classification'],
                             'hierarchy_note': f"{r['classification']} row; sectors contain industries which contain categories - never sum across classifications",
                             'total_usd': '' if r['total_usd'] is None else r['total_usd'], 'to_democrats_usd': '' if r['to_democrats_usd'] is None else r['to_democrats_usd'],
                             'to_republicans_usd': '' if r['to_republicans_usd'] is None else r['to_republicans_usd'],
                             'other_party_residual_signed_usd': r['other_party_residual_usd'] if r['other_party_residual_usd'] is not None else '',
                             'row_detail_href': r['detail_url'], 'row_href_cycle': r['href_cycle'] or '', 'row_href_cycle_stale': stale,
                             **self.prov(res, b['meta'], 'modern', notes='row href year is stale on historical pages; industry detail was requested for the row cycle and its served cycle verified' if stale else '')})

    def pac_industries(self):
        cross = defaultdict(lambda: {'scopes': [], 'codes': [], 'name': '', 'urls': []})
        for s in self.scopes:
            if not s.get('opensecrets_code'):
                for c in C.CYCLES:
                    self.add('pac_industry_candidate_totals', {**self.idf(s), 'requested_cycle': c, **self.prov(
                        None, None, '', 'not_requested', 'unavailable', 'no_published_industry_code', s['scope_note'])})
                continue
            code = s['opensecrets_code']
            for c in C.CYCLES:
                if c not in self.avail('pac'):
                    self.add('pac_industry_candidate_totals', {**self.idf(s), 'requested_cycle': c, **self.menu_gap('pac', c, 'modern')})
                    continue
                res, d = self.page(C.u_industry_detail(code, c), P.parse_industry_detail, code, c)
                base = {**self.idf(s), 'requested_cycle': c}
                if d is None:
                    self.add('pac_industry_candidate_totals', {**base, **self.prov(res, None, 'modern', 'fetch_failed', 'unavailable', self.fail_reason(res))})
                    continue
                if d['served_cycle'] != c:
                    self.add('pac_industry_candidate_totals', {**base, 'served_cycle': d['served_cycle'] or '', **self.prov(
                        res, d['meta'], 'modern', 'served_cycle_mismatch', 'unavailable', 'served_cycle_mismatch', self.served_note(d['served_cycle'], c))})
                    continue
                self.rosters[(s['scope_id'], c)] = (res, d)
                h, pacs = d['headline'], d['pacs']
                uniq = list({p['pac_id']: p for p in reversed(pacs) if p['pac_id']}.values())[::-1]   # one row per PAC ID (first kept); never dedup by name
                dup_rows = sum(1 for p in pacs if p['pac_id']) - len(uniq)
                no_id = sum(1 for p in pacs if not p['pac_id'])
                money_missing = any(None in (p['total_usd'], p['to_democrats_usd'], p['to_republicans_usd']) for p in uniq)
                sd = sum(p['to_democrats_usd'] or 0 for p in uniq)
                sr = sum(p['to_republicans_usd'] or 0 for p in uniq)
                st = sum(p['total_usd'] or 0 for p in uniq)
                tot, dd, rr = h.get('total_usd'), h.get('to_democrats_usd'), h.get('to_republicans_usd')
                bk = self.breakdown.get((c, code))
                # Category pages (e.g. T2100) publish a $0 headline card while listing PACs with money: source defect -> headline blank,
                # roster checked against the industry-breakdown row instead.
                defect = (tot == 0 and dd == 0 and rr == 0 and st > 0)
                if defect:
                    tot = dd = rr = None
                ref_d = dd if dd is not None else (bk['to_democrats_usd'] if bk else None)
                ref_r = rr if rr is not None else (bk['to_republicans_usd'] if bk else None)
                match = '' if bk is None or defect else (bk['total_usd'] == tot and bk['to_democrats_usd'] == dd and bk['to_republicans_usd'] == rr)
                why = []
                if h.get('n_pacs') != len(uniq):
                    why.append('unique_pac_count_differs_from_headline')
                if dup_rows:
                    why.append('duplicate_roster_pac_id')
                if no_id:
                    why.append('roster_row_without_pac_id')
                if money_missing:
                    why.append('roster_money_missing')
                if ref_d is None or ref_r is None:
                    why.append('industry_headline_unavailable')
                else:
                    if sd != ref_d or sr != ref_r:
                        why.append('roster_dr_sums_differ_from_headline')
                if tot is not None and st != tot:
                    why.append('roster_total_differs_from_headline')
                full = not why
                self.headline_eff[(s['scope_id'], c)] = {'D': ref_d, 'R': ref_r, 'defect': defect, 'roster_ok': full}
                self.add('pac_industry_candidate_totals', {**base, 'served_cycle': c, 'total_usd': tot if tot is not None else '',
                         'to_democrats_usd': dd if dd is not None else '', 'to_republicans_usd': rr if rr is not None else '',
                         'other_party_residual_signed_usd': (tot - dd - rr) if None not in (tot, dd, rr) else '',
                         'n_pacs_headline': h.get('n_pacs', ''), 'n_pac_rows': len(pacs), 'roster_sum_total_usd': st, 'roster_sum_democrat_usd': sd,
                         'roster_sum_republican_usd': sr, 'roster_minus_headline_democrat_usd': (sd - dd) if dd is not None else '',
                         'roster_minus_headline_republican_usd': (sr - rr) if rr is not None else '',
                         'breakdown_total_usd': bk['total_usd'] if bk and bk['total_usd'] is not None else '', 'breakdown_matches_detail': match,
                         **self.prov(res, d['meta'], 'modern', 'parsed', 'complete' if full else 'partial',
                                     ('source_headline_zero_defect_roster_matches_breakdown' if defect else '') if full else ';'.join(why),
                                     'full roster from data-collection (HTML pagination shows 25 only)' + ('; page headline card published $0 despite listed PAC money (source defect), left blank' if defect else ''))})
                for p in pacs:
                    tot_p, d_p, r_p = p['total_usd'], p['to_democrats_usd'], p['to_republicans_usd']
                    self.add('pac_roster', {**base, 'served_cycle': c, 'pac_id': p['pac_id'], 'pac_name': p['pac_name'], 'pac_slug': p['slug'],
                             'affiliate': p['affiliate'], 'lean': p['lean'], 'total_usd': tot_p if tot_p is not None else '',
                             'to_democrats_usd': d_p if d_p is not None else '', 'to_republicans_usd': r_p if r_p is not None else '',
                             'other_party_residual_signed_usd': (tot_p - d_p - r_p) if None not in (tot_p, d_p, r_p) else '',
                             'summary_url': p['summary_url'], 'summary_href_cycle': p['href_cycle'] or '',
                             **self.prov(res, d['meta'], 'modern', 'parsed' if p['pac_id'] else 'pac_id_missing', 'complete' if p['pac_id'] else 'partial',
                                         '' if p['pac_id'] else 'pac_link_unparsed')})
                    x = cross[(p['pac_id'], c)]
                    x['scopes'].append(s['scope_id']); x['codes'].append(code); x['name'] = x['name'] or p['pac_name']; x['urls'].append((res.url, res.meta.get('retrieved_utc', ''), res.meta.get('sha256') or ''))
        for (pid, c), x in sorted(cross.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            srcs = list(dict.fromkeys(x['urls']))     # one (url, capture_utc, sha256) triple per distinct source page, kept paired
            self.add('pac_membership_crosswalk', {'requested_cycle': c, 'pac_id': pid, 'pac_name': x['name'], 'scope_ids': '|'.join(x['scopes']),
                     'scope_codes': '|'.join(x['codes']), 'n_scopes': len(x['scopes']),
                     'overlap_note': 'PAC fetched once in pac_pages; present in several scopes (taxonomy parent/child overlap) - scope totals are NOT additive' if len(x['scopes']) > 1 else '',
                     'source_urls': '|'.join(u for u, _, _ in srcs), 'source_retrieved_utc': '|'.join(t for _, t, _ in srcs),
                     'source_sha256s': '|'.join(h for _, _, h in srcs), 'source_capture_pairs': ' | '.join(f'{u} @ {t}' for u, t, _ in srcs),
                     'extraction_status': 'parsed', 'completeness_status': 'complete', 'reason_code': ''})
        self.cross = cross

    def pac_pages(self):
        """Per-PAC-cycle pages (deduplicated across scopes) -> pac_pages / pac_chamber_party / pac_recipients.
        A missing amount is never zero: a (office, party) cell is exact only if the page's summary table or its recipient rows state it;
        the PAC headline D/R/total are reconciled against ALL office tables (Presidential included - the headline is all federal candidates)."""
        names = {k: v['name'] for k, v in self.cross.items()}
        for (pid, c), slug in sorted(self.runner.pac_pages().items(), key=lambda kv: (kv[0][1], kv[0][0])):
            url = C.u_pac_recipients(slug, pid, c)
            res, r = self.page(url, P.parse_pac_recipients, pid, c)
            base = {'pac_id': pid, 'requested_cycle': c}
            head = {'pac_name': names.get((pid, c), ''), 'pac_slug': slug, 'page_url': url}
            if r is None:
                self.add('pac_pages', {**base, **head, **self.prov(res, None, 'modern', 'fetch_failed', 'unavailable', self.fail_reason(res))})
                continue
            if r['served_cycle'] != c:
                self.add('pac_pages', {**base, **head, 'served_cycle': r['served_cycle'] or '',
                         **self.prov(res, r['meta'], 'modern', 'served_cycle_mismatch', 'unavailable', 'served_cycle_mismatch', self.served_note(r['served_cycle'], c))})
                continue
            h, rec = r['headline'], r['recipients']
            present = set(r['tables_seen'])
            sums, counts, row_missing = defaultdict(int), defaultdict(int), defaultdict(int)
            for x in rec:
                if x['amount_usd'] is not None:
                    sums[(x['chamber'], x['party_group'])] += x['amount_usd']
                else:
                    row_missing[(x['chamber'], x['party_group'])] += 1
                counts[(x['chamber'], x['party_group'])] += 1
                self.add('pac_recipients', {**base, 'served_cycle': c, 'chamber': x['chamber'], 'candidate': x['candidate'], 'sort_name': x['sort_name'],
                         'party_code': x['party_code'], 'party_group': x['party_group'], 'state': x['state'],
                         'amount_usd': x['amount_usd'] if x['amount_usd'] is not None else '', 'candidate_url': x['candidate_url'],
                         **self.prov(res, r['meta'], 'modern', notes=NEG_NOTE if (x['amount_usd'] or 0) < 0 else '')})
            summ, missing = {}, []
            for ch in PAC_OFFICES:
                for g in ('D', 'R', 'Other', 'Unclassified'):
                    n = counts.get((ch, g), 0)
                    s_amt = r['chamber_summary'].get(f'{ch}|{g}')
                    if g in ('Other', 'Unclassified') and not n and s_amt is None:
                        continue
                    if ch not in present:
                        if ch in C.CHAMBERS:
                            self.add('pac_chamber_party', {**base, 'served_cycle': c, 'chamber': ch, 'party_group': g, **self.prov(
                                res, r['meta'], 'modern', 'chamber_table_absent', 'partial', 'chamber_table_absent_on_page')})
                        continue
                    rows_ok = n > 0 and not row_missing.get((ch, g))
                    row_amt = sums.get((ch, g)) if rows_ok else None
                    amt, basis = (s_amt, 'page_summary_table') if s_amt is not None else (row_amt, 'recipient_rows_sum' if row_amt is not None else '')
                    summ[(ch, g)] = amt
                    if amt is None:
                        missing.append(f'{ch}|{g}')
                    self.add('pac_chamber_party', {**base, 'served_cycle': c, 'chamber': ch, 'party_group': g,
                             'summary_table_amount_usd': s_amt if s_amt is not None else '', 'recipient_rows_sum_usd': row_amt if row_amt is not None else '',
                             'n_recipients': n, 'amount_usd': amt if amt is not None else '', 'amount_basis': basis,
                             'summary_minus_rows_usd': (s_amt - row_amt) if None not in (s_amt, row_amt) else '',
                             **self.prov(res, r['meta'], 'modern', 'parsed', 'complete' if amt is not None else 'partial',
                                         '' if amt is not None else 'no_amount_for_party_in_office')})
            hd, hr, ht = h.get('to_democrats_usd'), h.get('to_republicans_usd'), h.get('total_usd')
            dsum = sum(v for (ch, g), v in summ.items() if g == 'D' and v is not None)
            rsum = sum(v for (ch, g), v in summ.items() if g == 'R' and v is not None)
            allsum = sum(v for v in summ.values() if v is not None)
            # D/R reconcile only when every needed cell is source-observed (None is not zero) and the headline is present
            rec_ok = None if (None in (hd, hr) or not present) else (not missing and dsum == hd and rsum == hr)
            total_ok = None if (ht is None or not present) else (not missing and allsum == ht)
            self.pac_data[(pid, c)] = {'present': present, 'summ': summ, 'missing': missing, 'reconciles': rec_ok, 'total_reconciles': total_ok,
                                       'counts': counts, 'sums': sums, 'headline': (ht, hd, hr)}
            reason = ''
            if missing:
                reason = 'missing_office_party_amount'
            elif rec_ok is None:
                reason = 'headline_or_tables_missing'
            elif not rec_ok:
                reason = 'office_sums_differ_from_headline'
            self.add('pac_pages', {**base, **head, 'served_cycle': c,
                     'headline_total_usd': ht if ht is not None else '',
                     'headline_democrat_usd': hd if hd is not None else '', 'headline_republican_usd': hr if hr is not None else '',
                     'house_recipient_rows': sum(n for (ch, g), n in counts.items() if ch == 'House'),
                     'senate_recipient_rows': sum(n for (ch, g), n in counts.items() if ch == 'Senate'),
                     'presidential_recipient_rows': sum(n for (ch, g), n in counts.items() if ch == 'Presidential'),
                     'tables_seen': '|'.join(r['tables_seen']),
                     'chamber_dr_sum_democrat_usd': dsum if not missing else '', 'chamber_dr_sum_republican_usd': rsum if not missing else '',
                     'headline_minus_chamber_democrat_usd': (hd - dsum) if (hd is not None and not missing) else '',
                     'headline_minus_chamber_republican_usd': (hr - rsum) if (hr is not None and not missing) else '',
                     'missing_amount_cells': '|'.join(missing), 'all_party_sum_usd': allsum if not missing else '',
                     'all_party_reconciles_to_headline_total': total_ok if total_ok is not None else '',
                     'negative_amount_rows': sum(1 for x in rec if (x['amount_usd'] or 0) < 0),
                     'reconciles_to_headline': rec_ok if rec_ok is not None else '',
                     **self.prov(res, r['meta'], 'modern', 'parsed', 'complete' if rec_ok else 'partial', reason,
                                 'headline is all federal candidates: House+Senate+Presidential tables are summed against it; D/R exclude other parties')})

    def pac_industry_chambers(self):
        """Industry x chamber x party PAC giving = sum of per-PAC page amounts over the cycle-specific roster.
        EXACT (amount_usd, status 'complete') only if: unique PAC IDs == headline n_pacs and no duplicate roster IDs, every PAC page retrieved,
        every needed amount source-observed (or an absent chamber table proven zero by that PAC's own headline reconciliation), every PAC page
        reconciles to its own headline (D/R incl. Presidential; all-party total for 'Other'), per-PAC roster D/R equal the PAC page headline,
        the roster reconciles to the industry headline, and House+Senate+Presidential sums equal the industry headline. Otherwise
        amount_usd is blank and the numeric partial sum is kept separately, labelled partial."""
        for s in self.scopes:
            for c in C.CYCLES:
                base = {**self.idf(s), 'requested_cycle': c}
                if not s.get('opensecrets_code') or c not in self.avail('pac') or (s['scope_id'], c) not in self.rosters:
                    reason = 'no_published_industry_code' if not s.get('opensecrets_code') else ('cycle_not_in_source_menu' if c not in self.avail('pac') else 'industry_roster_unavailable')
                    status = 'not_requested' if reason == 'no_published_industry_code' else ('not_published' if reason == 'cycle_not_in_source_menu' else 'source_unavailable')
                    for ch in C.CHAMBERS:
                        for g in ('D', 'R'):
                            self.add('pac_candidate_giving_industry', {**base, 'chamber': ch, 'party_group': g,
                                     **self.prov(None, None, 'modern', status, 'unavailable', reason)})
                    continue
                res, d = self.rosters[(s['scope_id'], c)]
                pacs = [p for p in d['pacs'] if p['pac_id']]
                ids = list(dict.fromkeys(p['pac_id'] for p in pacs))           # unique expected PAC IDs, never names
                dup = len(pacs) - len(ids)
                expected = d['headline'].get('n_pacs')
                ok_ids = [i for i in ids if (i, c) in self.pac_data]
                missing_pages = len(ids) - len(ok_ids)
                he = self.headline_eff[(s['scope_id'], c)]
                industry_ok = bool(he.get('roster_ok'))                       # roster totals/D/R/count reconcile with the industry headline
                roster = {}
                for p in pacs:
                    roster.setdefault(p['pac_id'], p)
                headline = {'D': he['D'], 'R': he['R']}
                parties = ['D', 'R']
                if any(self.pac_data[(i, c)]['counts'].get((ch, g)) for i in ok_ids for ch in C.CHAMBERS for g in ('Other', 'Unclassified')):
                    parties.append('Other')
                id_ok = (expected == len(ids)) and dup == 0
                for g in parties:
                    cells = {}
                    for ch in C.CHAMBERS:
                        total, miss_money, unrec = 0, 0, 0
                        for i in ok_ids:
                            pd = self.pac_data[(i, c)]
                            own_ok = pd['reconciles'] is True and (g != 'Other' or pd['total_reconciles'] is True)
                            if g == 'Other':
                                oth_missing = any(m.split('|')[0] == ch and m.split('|')[1] in ('Other', 'Unclassified') for m in pd['missing'])
                                if ch in pd['present']:
                                    v = None if oth_missing else sum(x for (cc, gg), x in pd['sums'].items() if cc == ch and gg in ('Other', 'Unclassified'))
                                else:    # absent chamber table: zero only if the all-party headline total reconciles without it
                                    v = 0 if pd['total_reconciles'] is True else None
                            elif ch in pd['present']:
                                v = pd['summ'].get((ch, g))
                            else:   # absent chamber table: zero only if the PAC's own headline reconciliation proves it
                                v = 0 if pd['reconciles'] is True else None
                            if v is None:
                                miss_money += 1
                            else:
                                total += v
                            if not own_ok:
                                unrec += 1
                            rp = roster[i]
                            if g != 'Other' and None not in (rp['to_democrats_usd'], rp['to_republicans_usd']) and pd['headline'][1:] != (rp['to_democrats_usd'], rp['to_republicans_usd']):
                                unrec += 1    # roster row D/R differ from the PAC's own page headline
                        cells[ch] = (total, miss_money, unrec)
                    pres = sum((self.pac_data[(i, c)]['summ'].get(('Presidential', g)) or 0) for i in ok_ids) if (g != 'Other' and ok_ids) else None
                    hv = headline.get(g)
                    hs = sum(cells[ch][0] for ch in C.CHAMBERS)
                    delta = (hv - hs - (pres or 0)) if (hv is not None and pres is not None) else None
                    for ch in C.CHAMBERS:
                        total, miss_money, unrec = cells[ch]
                        reasons = []
                        if not id_ok:
                            reasons.append('duplicate_roster_pac_id' if dup else 'unique_pac_count_differs_from_headline')
                        if missing_pages:
                            reasons.append('pac_pages_missing')
                        if miss_money:
                            reasons.append('pac_amount_missing_or_unproven_zero')
                        if unrec:
                            reasons.append('pac_page_not_reconciled_to_own_headline_or_roster')
                        if not industry_ok:
                            reasons.append('roster_not_reconciled_to_industry_headline')
                        if g != 'Other' and hv is None:
                            reasons.append('industry_headline_unavailable')
                        elif g != 'Other' and delta not in (0, None) and not missing_pages:   # with PAC pages missing the gap is explained by them
                            reasons.append('chambers_plus_presidential_differ_from_industry_headline')
                        have_any = bool(ok_ids)
                        complete = have_any and not reasons
                        self.add('pac_candidate_giving_industry', {**base, 'served_cycle': c, 'chamber': ch, 'party_group': g,
                                 'amount_usd': total if complete else '', 'partial_sum_usd': total if (have_any and not complete) else '',
                                 'amount_status': 'exact' if complete else ('partial_sum' if have_any else 'unavailable'),
                                 'pacs_expected_headline': expected if expected is not None else '', 'pacs_in_roster': len(pacs),
                                 'pacs_unique_ids': len(ids), 'pacs_duplicate_roster_rows': dup, 'pacs_retrieved': len(ok_ids), 'pacs_missing': missing_pages,
                                 'pacs_with_missing_money': miss_money, 'pacs_unreconciled': unrec,
                                 'presidential_party_usd': pres if pres is not None else '',
                                 'industry_headline_party_usd': hv if hv is not None else '',
                                 'headline_minus_chambers_incl_presidential_usd': delta if delta is not None else '',
                                 'chamber_sum_minus_headline_usd': (hv - hs) if hv is not None else '',
                                 'money_universe': 'PAC contributions to federal candidates (House/Senate recipient tables), nominal USD, signed nets; sum of per-PAC '
                                                   'chamber-party aggregates over the cycle-specific industry roster; D/R exclude other parties; the industry headline '
                                                   'also includes any Presidential giving (reported separately)',
                                 **self.prov(res, d['meta'], 'modern', 'parsed' if have_any else 'pac_pages_unavailable',
                                             'complete' if complete else ('partial' if have_any else 'unavailable'), ';'.join(reasons) if reasons else ('' if have_any else 'no_pac_pages'),
                                             f'missing PAC pages: {missing_pages}' if missing_pages else '')})

    def individual_gap(self):
        for s in self.scopes:
            for c in C.CYCLES:
                tot = ''
                if s.get('opensecrets_code') and c in self.avail('legacy'):
                    res, lt = self.page(C.u_legacy_totals(s['opensecrets_code']), P.parse_legacy_totals, s['opensecrets_code'])
                    row = next((r for r in lt['rows'] if r['cycle'] == c), None) if lt else None
                    tot = row['individual_usd'] if row and row['individual_usd'] is not None else ''
                for ch in C.CHAMBERS:
                    for g in ('D', 'R'):
                        self.add('individual_candidate_giving_industry', {**self.idf(s), 'requested_cycle': c, 'chamber': ch, 'party_group': g,
                                 'industry_individual_total_all_recipients_usd': tot,
                                 'money_universe': 'industry-attributed itemized individual giving (>$200; employee/owner/family); not available by chamber x party from any aggregate page',
                                 **self.prov(None, None, 'modern', 'source_not_found', 'unavailable', 'no_direct_industry_individual_by_chamber_source',
                                             'legacy mem=N lists combine PAC+individual with unsafe chamber labels; modern candidate pages need a full candidate-roster crawl (see receipt workplan); never subtract unmatched vintages')})

    # ---- legacy industry pages ---------------------------------------------------------------------
    def legacy(self):
        for s in self.scopes:
            code = s.get('opensecrets_code')
            for c in C.CYCLES:
                base = {**self.idf(s), 'requested_cycle': c}
                if not code:
                    for t in ('industry_totals', 'legacy_candidate_combined_by_chamber_party', 'top_contributors'):
                        self.add(t, {**base, **self.prov(None, None, '', 'not_requested', 'unavailable', 'no_published_industry_code', s['scope_note'])})
                    continue
                self._legacy_totals(s, base, code, c)
                if c not in self.avail('legacy'):
                    for t in ('legacy_candidate_combined_by_chamber_party', 'top_contributors'):
                        self.add(t, {**base, **self.menu_gap('legacy', c, 'legacy')})
                    continue
                self._legacy_contrib(base, code, c)
                for ch in C.CHAMBERS:
                    self._legacy_summary(base, code, c, ch)

    def _legacy_totals(self, s, base, code, c):
        tres, lt = self.page(C.u_legacy_totals(code), P.parse_legacy_totals, code)
        if lt is None:
            self.add('industry_totals', {**base, **self.prov(tres, None, 'legacy', 'fetch_failed', 'unavailable', self.fail_reason(tres))})
            return
        row = next((r for r in lt['rows'] if r['cycle'] == c), None)
        if row is None:
            self.add('industry_totals', {**base, **self.prov(tres, lt['meta'], 'legacy', 'not_published', 'unavailable', 'cycle_not_published',
                     f"requested via ?cycle=2026 probe; table ends {lt['latest_cycle']}; not relabelled")})
            return
        parts = [row['individual_usd'], row['pac_usd'], row['soft_outside_usd']]
        delta = None if None in parts or row['total_usd'] is None else sum(parts) - row['total_usd']
        self.add('industry_totals', {**base, 'served_cycle': c, **{k: ('' if row[k] is None else row[k]) for k in (
            'total_usd', 'individual_usd', 'pac_usd', 'soft_outside_usd', 'democrat_usd', 'republican_usd', 'democrat_pct', 'republican_pct')},
            'party_pct_basis': 'candidates and parties only; outside spending excluded', 'donor_sum_minus_total_usd': delta if delta is not None else '',
            **self.prov(tres, lt['meta'], 'legacy', 'parsed', 'complete' if delta == 0 else 'partial', '' if delta == 0 else 'donor_columns_not_additive',
                        'published columns preserved unadjusted; additivity not assumed')})

    def _legacy_contrib(self, base, code, c):
        cres, lc = self.page(C.u_legacy_contrib(code, c), P.parse_legacy_contrib, code, c)
        if lc is None:
            self.add('top_contributors', {**base, **self.prov(cres, None, 'legacy', 'fetch_failed', 'unavailable', self.fail_reason(cres))})
            return
        if lc['served_cycle'] != c or not lc['rows']:
            mism = lc['served_cycle'] != c
            self.add('top_contributors', {**base, 'served_cycle': lc['served_cycle'] or '', **self.prov(
                cres, lc['meta'], 'legacy', 'served_cycle_mismatch' if mism else 'table_missing', 'unavailable',
                'served_cycle_mismatch' if mism else 'contributor_table_missing')})
            return
        for r in lc['rows']:
            parts = (r['candidates_parties_usd'], r['outside_groups_usd'])
            delta = None if None in parts or r['total_usd'] is None else r['total_usd'] - sum(parts)
            self.add('top_contributors', {**base, 'served_cycle': c, **{k: ('' if r[k] is None else r[k]) for k in (
                'rank', 'organisation', 'organisation_normalized', 'total_usd', 'candidates_parties_usd', 'democrat_usd', 'republican_usd',
                'outside_groups_usd', 'liberal_groups_usd', 'conservative_groups_usd', 'lean')},
                'total_minus_cp_plus_outside_usd': delta if delta is not None else '',
                'additivity_flag': 'not_checkable' if delta is None else ('consistent' if delta == 0 else 'not_additive_review'),
                'pac_individual_split_status': 'not_published_on_contributor_page',
                **self.prov(cres, lc['meta'], 'legacy', 'parsed', 'partial', 'top_list_only_no_pac_individual_split',
                            'published top-contributor list (not all organisations); Grand Total is not a PAC/individual split; individual attribution includes employees/owners/family')})

    def _legacy_summary(self, base, code, c, ch):
        sres, ls = self.page(C.u_legacy_summary(code, c, ch), P.parse_legacy_summary, code, c, ch)
        if ls is None or ls['served_cycle'] != c:
            reason = self.fail_reason(sres) if ls is None else 'served_cycle_mismatch'
            self.add('legacy_candidate_combined_by_chamber_party', {**base, 'served_cycle': (ls['served_cycle'] or '') if ls else '', 'list_chamber': ch,
                     **self.prov(sres, ls['meta'] if ls else None, 'legacy', 'fetch_failed' if ls is None else 'served_cycle_mismatch', 'unavailable', reason)})
            return
        # served chamber / candidate universe come from the page (cycle-menu option values + 'to US <chamber> candidates' heading), never the URL
        if not ls['chamber_evidence_agrees'] or ls['served_chamber'] != ch or ls['served_mem'] != 'N':
            why = (f"requested {ch} all-candidates (mem=N); page evidence: chamber={ls['served_chamber']!r} heading={ls['heading_chamber']!r} "
                   f"mem={ls['served_mem']!r} universe={ls['served_universe_label']!r}")
            self.add('legacy_candidate_combined_by_chamber_party', {**base, 'served_cycle': c, 'list_chamber': ch,
                     **self.prov(sres, ls['meta'], 'legacy', 'served_universe_mismatch', 'unavailable', 'served_chamber_or_universe_mismatch', why)})
            return
        agg = {}
        for r in ls['rows']:
            self.add('legacy_candidate_combined', {**base, 'served_cycle': c, 'list_chamber': ch, 'recipient': r['recipient'], 'party_code': r['party_code'],
                     'party_group': r['party_group'], 'state_label': r['state_label'], 'state_code': r['state_code'],
                     'combined_pac_individual_usd': r['amount_usd'] if r['amount_usd'] is not None else '',
                     'chamber_basis': f"page-verified served universe {ls['served_universe_label']!r} ({ls['served_chamber']} list, mem={ls['served_mem']}); OpenSecrets list classification, not verified office sought",
                     **self.prov(sres, ls['meta'], 'legacy', 'parsed', 'partial', 'combined_pac_individual_not_a_donor_split', NEG_NOTE if (r['amount_usd'] or 0) < 0 else '')})
            a = agg.setdefault(r['party_group'], [0, 0, 0])
            a[0] += r['amount_usd'] or 0
            a[1] += 1
            a[2] += 1 if (r['amount_usd'] or 0) < 0 else 0
        for g in ('D', 'R', 'Other', 'Unclassified'):
            a = agg.get(g)
            if a is None and g in ('Other', 'Unclassified'):
                continue
            self.add('legacy_candidate_combined_by_chamber_party', {**base, 'served_cycle': c, 'list_chamber': ch, 'party_group': g,
                     'combined_pac_individual_usd': a[0] if a else '', 'n_rows': a[1] if a else 0, 'n_negative_rows': a[2] if a else 0,
                     'money_universe': 'combined PAC + individual (>$200 itemized) to ALL candidates (mem=N), as classified by OpenSecrets list',
                     'chamber_basis': 'list label is not office sought; presidential overlap and wrong-chamber labels possible',
                     **self.prov(sres, ls['meta'], 'legacy', 'parsed', 'partial', 'combined_pac_individual_not_a_donor_split')})

    # ---- offline supplemental annual lobbying exports (already-captured primary files; never a proxy, never Lobbyists-as-Clients) ----
    NATIVE_FILES = {'insurance-annual-lobbying-spending.csv': 'insurance', 'commercial-banks-annual-lobbying-spending.csv': 'commercial_banks',
                    'credit-unions-annual-lobbying-spending.csv': 'credit_unions', 'automotive-annual-lobbying-spending.csv': 'automotive_industry',
                    'telecom-services-annual-lobbying-spending.csv': 'telecom_services'}
    T2100_FILE = 'T2100_annual_browser_capture.csv'

    def load_offline(self, directory):
        """{(scope_id, year): info} from the native 'Export as CSV' files (+ the exact legacy T2100 chart capture). Capture DATE only: the capture
        time of day is not recorded, so none is invented. Files are read unchanged; their sha256 is recorded."""
        import csv as _csv, hashlib
        out, d = {}, Path(directory) if directory else None
        if not d or not d.exists():
            return out
        urls, cap_date = {}, ''
        notes = d / 'RECOVERY_NOTES.txt'
        if notes.exists():
            txt = notes.read_text(encoding='utf-8', errors='replace')
            m = re.search(r'capture date (\d{4}-\d{2}-\d{2})', txt)
            cap_date = m.group(1) if m else ''
            for line in txt.splitlines():
                if '.csv' in line and ' — http' in line:
                    name, url = line.split(' — ', 1)
                    urls[name.strip()] = url.strip()
        for fname, sid in self.NATIVE_FILES.items():
            p = d / fname
            if not p.exists():
                continue
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            with open(p, encoding='utf-8-sig', newline='') as fh:
                for r in _csv.DictReader(fh):
                    out[(sid, int(r['Year']))] = {'spend': int(r['Spending']), 'lobbyists': int(r['Lobbyists']) if (r.get('Lobbyists') or '').strip() else None,
                                                  'category': r['Category ID'], 'file': fname, 'sha': sha, 'page_url': urls.get(fname, ''), 'capture_date': cap_date,
                                                  'method': 'native browser Export as CSV (modern annual export; headers Year,Category ID,Spending,Lobbyists)',
                                                  'generation': 'modern', 'as_of_note': 'modern lobbying about-data: downloaded 2026-07-23, 2026 = Jan 1-Jun 30'}
        p = d / self.T2100_FILE
        if p.exists():
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            with open(p, encoding='utf-8-sig', newline='') as fh:
                for r in _csv.DictReader(fh):
                    if (r.get('spending') or '').strip():
                        out[('auto_manufacturers', int(r['year']))] = {
                            'spend': int(r['spending']), 'lobbyists': None, 'category': r['category_id'], 'file': self.T2100_FILE, 'sha': sha,
                            'page_url': r.get('page_url', ''), 'capture_date': r.get('capture_date', ''),
                            'method': 'browser capture of the legacy chart [data-chart=column2d][data-source] JSON', 'generation': 'legacy',
                            'as_of_note': 'legacy T2100 chart: source cutoff unknown/stale footer; the modern M02 cutoff is NOT inherited'}
        return out

    def offline_prov(self, off, status, complete, reason, notes=''):
        return {**self.prov(None, None, 'offline_native_export', status, complete, reason, notes),
                'source_url': off['page_url'], 'cache_key': 'offline:' + off['file'], 'source_sha256': off['sha'], 'retrieved_utc': '',
                'source_vintage': f"{off['method']}; capture_date {off['capture_date']} (time of day not recorded)"}

    def offline_export_table(self):
        """Every supplied export row for the configured years, compared with the HTTP-derived annual rows (HTTP preferred when it exists)."""
        http = {(r['scope_id'], r['requested_year']): r for r in self.T['lobbying_annual'] if r['source_generation'] in ('modern', 'legacy')}
        names = {s['scope_id']: s for s in self.scopes}
        for (sid, y), off in sorted(self.offline.items()):
            if y not in C.YEARS or sid not in names:
                continue
            h = http.get((sid, y))
            hv = _num_eq(h['spend_usd']) if h and h['spend_usd'] != '' else None
            cmp_state = 'http_absent_offline_only' if hv is None else ('equal_to_http' if hv == off['spend'] else 'differs_from_http')
            self.add('lobbying_annual_offline_export', {**self.idf(names[sid]), 'requested_year': y, 'source_category_id': off['category'], 'spend_usd': off['spend'],
                     'lobbyists_count': off['lobbyists'] if off['lobbyists'] is not None else '',
                     'lobbyists_note': 'Lobbyists is a lobbyist headcount from the export, NOT a client count' if off['lobbyists'] is not None else '',
                     'http_annual_spend_usd': hv if hv is not None else '', 'comparison': cmp_state, 'source_file': off['file'], 'source_file_sha256': off['sha'],
                     'source_method': off['method'], 'source_page_url': off['page_url'], 'capture_date': off['capture_date'],
                     'capture_timestamp_status': 'date_only_time_not_recorded', 'source_as_of_note': off['as_of_note'],
                     **self.offline_prov(off, 'offline_export_ingested', 'complete' if cmp_state == 'equal_to_http' else 'partial',
                                         '' if cmp_state == 'equal_to_http' else ('http_capture_unavailable_offline_export_used' if hv is None else 'offline_differs_from_http_capture'),
                                         'unchanged supplemental source; HTTP capture preferred when present')})

    # ---- lobbying ---------------------------------------------------------------------------------
    def lobby_asof(self):
        res = self.f.get(C.LOBBY_ASOF_URL)
        out = {'res': res, 'as_of': '', 'start': '', 'end': '', 'note': ''}
        if res.ok:
            text = P.soup_of(res.body).get_text(' ', strip=True)
            m = re.search(r'downloaded on ((?:%s) \d{1,2}, \d{4}) and includes spending from ((?:%s) \d{1,2}) - ((?:%s) \d{1,2})' % (P.MONTHS, P.MONTHS, P.MONTHS), text)
            if m:
                yr = m.group(1)[-4:]
                out.update(as_of=P.iso_date(m.group(1)), start=P.iso_date(f'{m.group(2)}, {yr}'), end=P.iso_date(f'{m.group(3)}, {yr}'),
                           note=f'page note: most recent year downloaded {m.group(1)}, includes spending {m.group(2)} - {m.group(3)}; prior years Jan-Dec')
        self.asof = out

    def lobbying(self):
        self.lobby_asof()
        for s in self.scopes:
            idf = self.idf(s)
            cat, slug = s.get('lobby_category_id'), s.get('lobby_slug')
            if cat:
                self._modern_lobby(s, idf, cat, slug)
            elif s.get('opensecrets_code'):
                self._legacy_lobby(s)
            else:
                for y in C.YEARS:
                    self.add('lobbying_annual', {**idf, 'requested_year': y, **self.prov(None, None, '', 'not_requested', 'unavailable', 'no_published_industry_code', s['scope_note'])})
        self.offline_export_table()

    def _modern_lobby(self, s, idf, cat, slug):
        bres, bh = self.page(C.u_lobby_page(slug, cat, 2026), P.parse_lobby_heading)
        ares, an = self.page(C.u_lobby_chunk(slug, cat, 'annual_trends', 2026), P.parse_lobby_annual)
        title = bh['h1'] if bh else ''
        for y in C.YEARS:
            base = {**idf, 'requested_year': y, 'source_category_id': cat, 'source_category_title': title}
            mres, mn = self.page(C.u_lobby_chunk(slug, cat, 'main', y), P.parse_lobby_main, cat, y)
            row, ck = {**base}, {}
            if y == 2026:
                row.update(data_as_of_date=self.asof['as_of'], spending_period_start=self.asof['start'], spending_period_end=self.asof['end'], period_note=self.asof['note'])
                if self.asof['end']:
                    ck = dict(cutoff=self.asof['end'], basis='spending_period_end per top-industries about-data note')
            else:
                row.update(spending_period_start=f'{y}-01-01', spending_period_end=f'{y}-12-31', period_note='full calendar year (per page note)')
            spend = an['annual'].get(y) if an else None
            mm = mn if (mn and mn['served_year'] == y) else None
            if an is None or spend is None:
                off = self.offline.get((s['scope_id'], y))
                if off:   # HTTP annual chart unavailable (e.g. managed challenge): the unchanged native export fills the gap, explicitly labelled
                    self.add('lobbying_annual', {**row, 'served_year': y, 'spend_usd': off['spend'],
                             'clients_active': mm['clients_active'] if mm and mm['clients_active'] is not None else '',
                             'client_rows_parsed': len(mm['clients']) if mm else '', 'capture_date': off['capture_date'],
                             'capture_timestamp_status': 'date_only_time_not_recorded',
                             **self.offline_prov(off, 'offline_export', 'partial', 'http_annual_chart_unavailable_offline_native_export_used',
                                                 'supplemental native Export-as-CSV (spend only; Lobbyists is not a client count); HTTP annual chart preferred when present')})
                else:
                    self.add('lobbying_annual', {**row, **self.prov(ares, None, 'modern', 'fetch_failed' if an is None else 'year_not_in_chart', 'unavailable',
                             self.fail_reason(ares) if an is None else 'year_not_in_chart', 'annual chart (annual_trends chunk)')})
            else:
                diff = (spend - mm['industry_spend_usd']) if (mm and mm['industry_spend_usd'] is not None) else None
                good = mm is not None and diff == 0
                self.add('lobbying_annual', {**row, 'served_year': y, 'spend_usd': spend,
                         'clients_active': mm['clients_active'] if mm and mm['clients_active'] is not None else '',
                         'client_rows_parsed': len(mm['clients']) if mm else '',
                         'main_chunk_industry_spend_usd': mm['industry_spend_usd'] if mm and mm['industry_spend_usd'] is not None else '',
                         'chart_minus_main_usd': diff if diff is not None else '',
                         **self.prov(ares, None, 'modern', 'parsed', 'complete' if good else 'partial', '' if good else 'main_chunk_missing_or_differs',
                                     'spend from annual chart; clients_active from the year-specific main chunk; label per source title (the F09 widget label '
                                     '"Property & casualty insurance" is erroneous and not adopted)', **ck)})
            if mm is None:
                self.add('lobbying_clients', {**base, **self.prov(mres, None, 'modern', 'fetch_failed' if mn is None else 'served_year_mismatch', 'unavailable',
                         self.fail_reason(mres) if mn is None else 'served_year_mismatch')})
            else:
                for i, cl in enumerate(mm['clients'], 1):
                    self.add('lobbying_clients', {**base, 'served_year': y, 'row_order': i, 'client': cl['client'], 'client_id': cl['client_id'],
                             'client_slug': cl['client_slug'], 'spend_usd': cl['spend_usd'] if cl['spend_usd'] is not None else '',
                             'client_url': cl['client_url'], 'listing_note': 'Client/Parent table (full static HTML); first widget table excluded (category aggregate, wrong label)',
                             **self.prov(mres, None, 'modern', 'parsed', 'complete', **ck)})
        self._split_rows(s, idf, cat, slug)

    def _legacy_lobby(self, s):
        idf, code = self.idf(s), s['opensecrets_code']
        annual, anres, anmeta, title = {}, None, None, ''
        ll = self.avail('legacy_lobbying')
        for c in [c for c in C.CYCLES if c in ll]:
            res, d = self.page(C.u_legacy_lobbying(code, c), P.parse_legacy_lobbying, code, c)
            if d is not None and len(d['annual']) > len(annual):
                annual, anres, anmeta, title = d['annual'], res, d['meta'], d['title']
        for y in C.YEARS:
            base = {**idf, 'requested_year': y, 'source_category_id': code, 'source_category_title': title.replace(' • OpenSecrets', ''),
                    'spending_period_start': f'{y}-01-01', 'spending_period_end': f'{y}-12-31', 'period_note': 'legacy chart; period not stated on page'}
            if y == 2026:
                base.update(spending_period_end='', period_note='legacy chart carries a 2026 value but states no as-of/cutoff (page footer FEC Feb 6 2025 is stale); modern M02 cutoff NOT inherited')
            use_page = y % 2 == 0 and y in ll
            res_c, dc = self.page(C.u_legacy_lobbying(code, y), P.parse_legacy_lobbying, code, y) if use_page else (None, None)
            good_c = dc is not None and dc['served_year'] == y
            if annual.get(y) is not None:
                self.add('lobbying_annual', {**base, 'served_year': y, 'spend_usd': annual[y],
                         'clients_active': (dc['n_clients'] if good_c and dc['n_clients'] is not None else ''),
                         'client_rows_parsed': len(dc['clients']) if good_c else '', 'in_house_outside_status': 'unavailable',
                         **self.prov(anres, anmeta, 'legacy', 'parsed', 'partial', 'legacy_source_no_in_house_outside_no_cutoff',
                                     'exact legacy series for the narrow category; NOT the broader modern M02 Automotive')})
            elif self.offline.get((s['scope_id'], y)):
                off = self.offline[(s['scope_id'], y)]
                self.add('lobbying_annual', {**base, 'served_year': y, 'spend_usd': off['spend'], 'in_house_outside_status': 'unavailable',
                         'capture_date': off['capture_date'], 'capture_timestamp_status': 'date_only_time_not_recorded',
                         **self.offline_prov(off, 'offline_export', 'partial', 'legacy_chart_unavailable_offline_capture_used',
                                             'exact legacy T2100 browser capture; as-of unknown; NOT the broader modern M02 Automotive')})
            else:
                self.add('lobbying_annual', {**base, **self.prov(anres, None, 'legacy', 'year_not_in_chart', 'unavailable', 'year_not_in_chart')})
            if good_c:
                for i, cl in enumerate(dc['clients'], 1):
                    self.add('lobbying_clients', {**base, 'served_year': y, 'row_order': i, 'client': cl['client'],
                             'spend_usd': cl['spend_usd'] if cl['spend_usd'] is not None else '',
                             'listing_note': 'legacy Client/Parent Organization table of the even-cycle page', **self.prov(res_c, dc['meta'], 'legacy', 'parsed', 'complete')})
            else:
                nopub = not use_page
                self.add('lobbying_clients', {**base, **self.prov(res_c, None, 'legacy', 'not_published' if nopub else 'fetch_failed', 'unavailable',
                         'legacy_clients_only_for_even_cycles_on_source_menu' if nopub else self.fail_reason(res_c))})

    def _split_rows(self, s, idf, cat, slug):
        """lobbying_client_splits (only where split pages were collected) + in-house/outside aggregation per year.
        EXACT in_house_usd / outside_firm_usd (status complete_exact) only if ALL hold for the year: the main chunk served that year; every
        parent client has an ID+slug and parent IDs are unique; parsed client count == the source's active-client count; every client spend
        cell is present and sums to the industry total, which equals the annual-chart spend; every client split page is cached, served the
        requested year, has BOTH components explicitly numeric (a published 0 is fine, absence is not), components sum to the client page total,
        and that total equals the client's industry-table amount; hence accepted components sum to the industry total. Otherwise the exact
        fields stay blank, labelled partial sums are kept and the failing predicates are listed in in_house_outside_reason."""
        splits = {}
        annual = {r['requested_year']: r for r in self.T['lobbying_annual'] if r['scope_id'] == s['scope_id']}
        for y in C.YEARS:
            mres, mn = self.page(C.u_lobby_chunk(slug, cat, 'main', y), P.parse_lobby_main, cat, y)
            if mn is None or mn['served_year'] != y:
                continue
            clients = mn['clients']
            reasons = set()
            ids = [cl['client_id'] for cl in clients if cl['client_id']]
            if any(not (cl['client_id'] and cl['client_slug']) for cl in clients):
                reasons.add('client_identity_missing')
            if len(set(ids)) != len(ids):
                reasons.add('duplicate_parent_client_id')
            if mn['clients_active'] is None:
                reasons.add('source_client_count_missing')
            elif mn['clients_active'] != len(clients):
                reasons.add('parsed_clients_differ_from_source_count')
            spends = [cl['spend_usd'] for cl in clients]
            ind_total = mn['industry_spend_usd']
            if any(v is None for v in spends):
                reasons.add('client_spend_missing')
            elif ind_total is None or sum(spends) != ind_total:
                reasons.add('client_spend_sum_differs_from_industry_total')
            chart = annual.get(y, {}).get('spend_usd', '')
            if chart in ('', None) or ind_total is None or _num_eq(chart) != ind_total:
                reasons.add('annual_chart_spend_differs_from_main_total')
            n_split = n_rec = n_cached = 0
            ih_partial = ou_partial = 0
            ih_sum = ou_sum = 0
            all_cached = True
            for cl in clients:
                if not (cl['client_id'] and cl['client_slug']):
                    all_cached = False
                    continue
                url = C.u_client_split(cl['client_slug'], cl['client_id'], y)
                cached = self.f.load_cached(url)
                if cached is None:
                    all_cached = False
                    continue
                n_cached += 1
                # load_cached has already checked the body hash and challenge status.
                # Reuse that result instead of reading and hashing the same file again.
                res, sp = self.page(url, P.parse_client_split, cached_res=cached)
                if sp is None or not sp['split_found']:
                    all_cached = False
                    reasons.add('client_split_page_unusable')
                    self.add('lobbying_client_splits', {**idf, 'requested_year': y, 'client': cl['client'], 'client_id': cl['client_id'],
                             **self.prov(res, None, 'modern', 'fetch_failed' if sp is None else 'split_not_found', 'unavailable',
                                         self.fail_reason(res) if sp is None else 'in_house_outside_chart_absent')})
                    continue
                if sp['served_year'] != y:   # the page's own 'YYYY total' year, never the request parameter
                    all_cached = False
                    reasons.add('client_split_served_year_mismatch')
                    self.add('lobbying_client_splits', {**idf, 'requested_year': y, 'served_year': sp['served_year'] if sp['served_year'] else '',
                             'client': cl['client'], 'client_id': cl['client_id'],
                             **self.prov(res, None, 'modern', 'served_year_mismatch', 'unavailable', 'client_split_served_year_mismatch',
                                         f"page reports year {sp['served_year']}, requested {y}; values NOT relabelled")})
                    continue
                ihv, ouv = sp['in_house_usd'], sp['outside_firms_usd']
                explicit = ihv is not None and ouv is not None
                ssum = (ihv + ouv) if explicit else None
                tot, ind = sp['client_year_total_usd'], cl['spend_usd']
                scope_eq = tot is not None and ind is not None and tot == ind
                recon = explicit and tot is not None and ssum == tot
                accepted = explicit and recon and scope_eq
                if not explicit:
                    reasons.add('split_component_not_explicit')
                if not recon:
                    reasons.add('split_sum_differs_from_client_total')
                if not scope_eq:
                    reasons.add('client_total_differs_from_industry_amount_other_industries_or_children')
                flag = ('client_total_equals_industry_amount_and_split_sums' if accepted else
                        'split_component_not_explicit' if not explicit else
                        'split_sum_differs_from_client_total' if not recon else 'client_total_differs_from_industry_amount_other_industries_or_children')
                n_split += 1
                n_rec += 1 if accepted else 0
                ih_partial += ihv or 0
                ou_partial += ouv or 0
                if accepted:
                    ih_sum += ihv
                    ou_sum += ouv
                self.add('lobbying_client_splits', {**idf, 'requested_year': y, 'served_year': sp['served_year'], 'client': cl['client'], 'client_id': cl['client_id'],
                         'industry_table_spend_usd': ind if ind is not None else '', 'client_year_total_usd': tot if tot is not None else '',
                         'in_house_usd': ihv if ihv is not None else '', 'outside_firms_usd': ouv if ouv is not None else '',
                         'components_explicit': explicit, 'split_sum_usd': ssum if ssum is not None else '',
                         'split_sum_minus_page_total_usd': (ssum - tot) if (ssum is not None and tot is not None) else '',
                         'page_total_minus_industry_table_usd': (tot - ind) if None not in (tot, ind) else '', 'reconciliation_flag': flag,
                         **self.prov(res, None, 'modern', 'parsed', 'complete' if accepted else 'partial', '' if accepted else flag,
                                     'cycle_snapshot chunk of the selected year; direct-vs-subsidiary labels are NOT in-house vs outside; parent-level scope')})
            if clients and n_rec == len(clients) and all_cached and not reasons and ind_total is not None and ih_sum + ou_sum != ind_total:
                reasons.add('accepted_components_differ_from_industry_total')
            if not all_cached:
                reasons.add('client_split_pages_not_all_collected')
            splits[y] = {'n_split': n_split, 'n_cached': n_cached, 'n_rec': n_rec, 'ih': ih_sum, 'ou': ou_sum, 'ih_partial': ih_partial, 'ou_partial': ou_partial,
                         'n_clients': len(clients), 'ok': bool(clients) and not reasons, 'reasons': sorted(reasons)}
        for row in self.T['lobbying_annual']:
            if row['scope_id'] != s['scope_id']:
                continue
            sp = splits.get(row['requested_year'])
            if sp is None or sp['n_cached'] == 0:
                row['in_house_outside_status'] = 'not_collected' if row['extraction_status'] == 'parsed' else 'unavailable'
                row['in_house_outside_reason'] = 'no_client_split_pages_collected' if row['extraction_status'] == 'parsed' else 'annual_row_unavailable'
                continue
            row['clients_with_split'], row['clients_split_reconciled'] = sp['n_split'], sp['n_rec']
            row['in_house_outside_reason'] = ';'.join(sp['reasons'])
            if sp['ok']:
                row['in_house_usd'], row['outside_firm_usd'], row['in_house_outside_status'] = sp['ih'], sp['ou'], 'complete_exact'
            else:
                row['in_house_partial_sum_usd'], row['outside_partial_sum_usd'] = sp['ih_partial'], sp['ou_partial']
                row['in_house_outside_status'] = 'partial_unreconciled'

    # ---- organisation profiles (exact-name lookup: top contributors + read-only Mentat roster) ---------------------
    ORG_SCOPE_NOTE = ('industry top-contributor page (candidates+parties+outside, industry-coded, vintage of that page) vs org profile (all affiliates; '
                      '$200+ PAC/individual to candidates plus soft money, FEC release of the profile page) - universes are not shown equal even when numbers agree')
    ORG_MATCH_NOTE = 'exact normalised-name match to ONE Organization row; the profile may include broader affiliates - a name match is not an ownership or parent proof'

    def orgs(self):
        names = self.runner.org_names()
        match = {key: self.page(C.u_org_search(name), P.parse_org_search, name) for key, name in names.items()}
        roster_by_key = defaultdict(list)
        for r in self.runner.roster:
            roster_by_key[normalized(r['original_company_name'])].append(r)
        via, scopes_by_org, seen = defaultdict(set), defaultdict(set), {}
        top_keys = set()
        for s in self.scopes:
            if s['relation'] != 'requested' or not s.get('opensecrets_code'):
                continue
            for c in [c for c in C.CYCLES if c in self.avail('legacy')]:
                cres, lc = self.page(C.u_legacy_contrib(s['opensecrets_code'], c), P.parse_legacy_contrib, s['opensecrets_code'], c)
                if lc is None or lc['served_cycle'] != c:
                    continue
                for r in lc['rows']:
                    top_keys.add(normalized(r['organisation']))
                    sres, o = match.get(normalized(r['organisation']), (None, None))
                    base = {**self.idf(s), 'requested_cycle': c, 'served_cycle': c, 'rank': r['rank'], 'organisation': r['organisation'],
                            'industry_page_total_usd': r['total_usd'] if r['total_usd'] is not None else '',
                            'industry_source_url': cres.url, 'industry_source_retrieved_utc': cres.meta.get('retrieved_utc', ''),
                            'industry_source_sha256': cres.meta.get('sha256') or '', 'source_universe': self.ORG_SCOPE_NOTE}
                    if o is None:
                        miss = sres is None or sres.meta.get('error') == 'cache_only_miss'
                        self.add('org_contribution_sources', {**base, **self.prov(sres, None, 'legacy', 'not_attempted' if miss else 'fetch_failed', 'unavailable',
                                 'org_search_not_collected' if miss else self.fail_reason(sres))})
                        continue
                    sinfo = {'search_url': sres.url, 'search_retrieved_utc': sres.meta.get('retrieved_utc', ''), 'search_sha256': sres.meta.get('sha256') or ''}
                    if o['status'] != 'matched_exact':
                        self.add('org_contribution_sources', {**base, **sinfo, 'org_search_status': o['status'],
                                 **self.prov(sres, o['meta'], 'legacy', 'parsed', 'unavailable', 'org_' + o['status'],
                                             'exact normalised name match required; ambiguous/none stays candidate-only, never first-result')})
                        continue
                    turl = C.u_org_totals(o['slug'], o['org_id'])
                    tres, t = self.page(turl, P.parse_org_totals)
                    ident = {**sinfo, 'org_search_status': o['status'], 'org_id': o['org_id'], 'org_slug': o['slug'], 'profile_url': turl, 'match_qualification': self.ORG_MATCH_NOTE}
                    if t is None:
                        miss = tres.meta.get('error') == 'cache_only_miss'
                        self.add('org_contribution_sources', {**base, **ident, **self.prov(tres, None, 'legacy', 'not_attempted' if miss else 'fetch_failed', 'unavailable',
                                 'org_totals_not_collected' if miss else self.fail_reason(tres))})
                        continue
                    bp, bs = t['by_party'].get(c), t['by_source'].get(c)
                    if not bp or not bs:
                        self.add('org_contribution_sources', {**base, **ident, **self.prov(tres, t['meta'], 'legacy', 'cycle_row_missing', 'unavailable', 'cycle_not_in_org_history')})
                        continue
                    need = [bp.get('total_usd'), bp.get('democrat_usd'), bp.get('republican_usd'), bs.get('individual_usd'), bs.get('pac_usd'),
                            bs.get('soft_individual_usd'), bs.get('soft_organization_usd')]
                    complete_data = None not in need
                    diff = (bp['total_usd'] - r['total_usd']) if None not in (bp['total_usd'], r['total_usd']) else None
                    g = lambda d, k: ('' if d.get(k) is None else d[k])
                    # data completeness (all profile components present) is independent of the cross-universe comparison
                    cmp_state = 'not_comparable' if diff is None else ('numeric_differs' if diff else 'numeric_equal_universe_not_proven')
                    self.add('org_contribution_sources', {**base, **ident, 'profile_total_usd': g(bp, 'total_usd'), 'profile_individual_usd': g(bs, 'individual_usd'),
                             'profile_pac_usd': g(bs, 'pac_usd'), 'profile_soft_individual_usd': g(bs, 'soft_individual_usd'),
                             'profile_soft_organization_usd': g(bs, 'soft_organization_usd'), 'profile_democrat_usd': g(bp, 'democrat_usd'),
                             'profile_republican_usd': g(bp, 'republican_usd'), 'profile_minus_industry_page_usd': diff if diff is not None else '',
                             'scope_mismatch_flag': cmp_state, 'scope_qualification': 'org_profile_universe_not_shown_equal_to_industry_coded_total',
                             'n_affiliates_listed': len(t['affiliates']), 'affiliates_selected_cycle': t['affiliates_cycle'],
                             **self.prov(tres, t['meta'], 'legacy', 'parsed' if complete_data else 'incomplete_inputs', 'complete' if complete_data else 'partial',
                                         '' if complete_data else 'org_profile_component_missing',
                                         'profile PAC/individual split is exact for the ORG profile universe; it does not split the industry top-contributor total')})
                    seen.setdefault(o['org_id'], (o, t, tres, sres))
                    via[o['org_id']].add('top_contributor_page')
                    scopes_by_org[o['org_id']].add(s['scope_id'])
        # roster rows: every roster company is searched by exact name; unmatched / ambiguous / candidate lists are preserved, no parent invented
        for key, rows in roster_by_key.items():
            sres, o = match.get(key, (None, None))
            for rr in rows:
                rbase = {'roster_source_workbook': rr.get('source_workbook', ''), 'roster_worksheet': rr.get('worksheet', ''), 'roster_row_number': rr.get('row_number', ''),
                         'roster_scope_id': rr.get('scope_id', ''), 'roster_mentat_industry': rr.get('mentat_industry', ''),
                         'original_company_name': rr['original_company_name'], 'normalized_company_name': key, 'roster_capture_utc': rr.get('capture_utc', ''),
                         'roster_workbook_sha256': rr.get('workbook_sha256', ''), 'roster_snapshot_status': rr.get('snapshot_status', ''),
                         'scope_qualification': 'current Mentat top-10 roster snapshot (not a historical census); name match only; affiliates/parents not inferred'}
                if o is None:
                    miss = sres is None or sres.meta.get('error') == 'cache_only_miss'
                    self.add('org_roster_crosswalk', {**rbase, 'match_status': 'not_attempted' if miss else 'search_failed',
                             **self.prov(sres, None, 'legacy', 'not_attempted' if miss else 'fetch_failed', 'unavailable', 'org_search_not_collected' if miss else self.fail_reason(sres))})
                    continue
                cand = '|'.join(f"{x['name']}={x['org_id']}" for x in o['candidates'])
                row = {**rbase, 'search_url': sres.url, 'match_status': o['status'], 'n_org_candidates': len(o['candidates']), 'org_candidates': cand}
                if o['status'] != 'matched_exact':
                    self.add('org_roster_crosswalk', {**row, **self.prov(sres, o['meta'], 'legacy', 'parsed', 'unavailable', 'org_' + o['status'],
                             'candidate organisations preserved; no exact unique normalised-name match, nothing assigned')})
                    continue
                turl = C.u_org_totals(o['slug'], o['org_id'])
                tres, t = self.page(turl, P.parse_org_totals)
                row.update(org_id=o['org_id'], org_slug=o['slug'], profile_url=turl)
                via[o['org_id']].add('mentat_roster')
                scopes_by_org[o['org_id']].add(rr.get('scope_id', ''))
                if t is None:
                    miss = tres.meta.get('error') == 'cache_only_miss'
                    self.add('org_roster_crosswalk', {**row, **self.prov(tres, None, 'legacy', 'matched_profile_not_collected' if miss else 'fetch_failed', 'partial',
                             'org_totals_not_collected' if miss else self.fail_reason(tres), 'exact name match found; profile page not yet collected')})
                    continue
                cycles = sorted(set(t['by_party']) | set(t['by_source']))
                full = bool(cycles) and all(t['by_party'].get(cy) and t['by_source'].get(cy) and None not in (
                    *(t['by_party'][cy].get(k) for k in ('total_usd', 'democrat_usd', 'republican_usd')),
                    *(t['by_source'][cy].get(k) for k in ('individual_usd', 'pac_usd', 'soft_individual_usd', 'soft_organization_usd'))) for cy in cycles)
                self.add('org_roster_crosswalk', {**row, 'history_first_cycle': cycles[0] if cycles else '', 'history_last_cycle': cycles[-1] if cycles else '',
                         'n_history_cycles': len(cycles), 'profile_retrieved_utc': tres.meta.get('retrieved_utc', ''), 'profile_sha256': tres.meta.get('sha256') or '',
                         **self.prov(tres, t['meta'], 'legacy', 'parsed', 'complete' if full else 'partial', '' if full else 'org_history_component_missing',
                                     'history rows are in org_totals_history; ' + self.ORG_MATCH_NOTE)})
                seen.setdefault(o['org_id'], (o, t, tres, sres))
        for oid, (o, t, tres, sres) in seen.items():
            for cy in sorted(set(t['by_party']) | set(t['by_source'])):
                bp, bs = t['by_party'].get(cy, {}), t['by_source'].get(cy, {})
                g = lambda d, k: ('' if d.get(k) is None else d[k])
                comps = [bp.get('total_usd'), bp.get('democrat_usd'), bp.get('republican_usd'), bs.get('individual_usd'), bs.get('pac_usd'),
                         bs.get('soft_individual_usd'), bs.get('soft_organization_usd')]
                ok = bool(bp) and bool(bs) and None not in comps
                why = ('party_table_row_missing;' if not bp else '') + ('source_table_row_missing;' if not bs else '') + ('org_component_missing;' if (bp and bs and None in comps) else '')
                self.add('org_totals_history', {'org_id': oid, 'org_slug': o['slug'], 'org_name': t['org_name'], 'cycle': cy, 'total_usd': g(bp, 'total_usd'),
                         'democrat_usd': g(bp, 'democrat_usd'), 'republican_usd': g(bp, 'republican_usd'), 'individual_usd': g(bs, 'individual_usd'),
                         'pac_usd': g(bs, 'pac_usd'), 'soft_individual_usd': g(bs, 'soft_individual_usd'), 'soft_organization_usd': g(bs, 'soft_organization_usd'),
                         'by_party_row_present': bool(bp), 'by_source_row_present': bool(bs), 'matched_via': '+'.join(sorted(via[oid])),
                         'scope_ids': '|'.join(sorted(x for x in scopes_by_org[oid] if x)), 'search_url': sres.url if sres is not None else '',
                         'search_retrieved_utc': sres.meta.get('retrieved_utc', '') if sres is not None else '', 'search_sha256': (sres.meta.get('sha256') or '') if sres is not None else '',
                         'profile_url': tres.url, 'note_527': t['note_527'][:200], 'match_qualification': self.ORG_MATCH_NOTE,
                         **self.prov(tres, t['meta'], 'legacy', 'parsed' if ok else 'incomplete_inputs', 'complete' if ok else 'partial', why.rstrip(';'),
                                     'N/A in source -> blank (never zero)')})

    def build(self, only=None):
        for name, fn in [('national', self.national), ('election_cost', self.election_cost), ('pac_breakdown', self.pac_breakdown),
                         ('pac_industries', self.pac_industries), ('pac_pages', self.pac_pages), ('pac_industry_chambers', self.pac_industry_chambers),
                         ('individual_gap', self.individual_gap), ('legacy', self.legacy), ('lobbying', self.lobbying), ('orgs', self.orgs)]:
            if only and name not in only:
                continue
            fn()
            self.log(f'[extract] {name} done')
        return self.T


def write_tables(tables, out_dir, only_nonempty=False):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, rows in tables.items():
        if only_nonempty and not rows:
            continue
        atomic_write_csv(out / f'{name}.csv', SCHEMAS[name], rows)


def run_extract_and_validate(a, fetcher, do_extract=True, do_validate=True):
    from . import validate as V
    cfg = C.load_scopes(a.scopes)
    ex = Extractor(fetcher, cfg, roster_csv=a.roster_csv, offline_dir=a.offline_lobby_dir, queue_path=Path(a.state_dir) / 'work_queue.json')
    only = {x.strip() for x in a.extract_only.split(',') if x.strip()}
    tables = ex.build(only or None)
    out = Path(a.out_dir)
    if do_extract:
        write_tables(tables, out, only_nonempty=bool(only))
        print('[extract] wrote ' + ', '.join(f'{k}={len(v)}' for k, v in tables.items() if v or not only), flush=True)
    if only:   # partial extraction: only the checks that apply to the extracted builders
        if 'national' in only:
            V.run_national_validation(tables, out)
        return
    if do_validate:
        V.run_validation(a, ex, tables, out)
