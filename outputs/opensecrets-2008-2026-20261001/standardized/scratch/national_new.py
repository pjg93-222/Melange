    # ---- national ---------------------------------------------------------------------------
    def national(self):
        by_cycle, gaps = {}, []
        for c in C.CYCLES:
            res, o = self.page(C.u_overview(c), P.parse_overview, c)
            base = {'requested_cycle': c}
            want = ['Presidential', 'House', 'Senate'] if c in PRES_YEARS else ['House', 'Senate']
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
        offs = ['Presidential', 'House', 'Senate'] if c in PRES_YEARS else ['House', 'Senate']
        return ([('pres_house_senate', offs)] if c in PRES_YEARS else []) + [('house_senate', ['House', 'Senate'])]

    @staticmethod
    def _coverage_note(c, scope):
        if scope == 'house_senate':
            return 'House+Senate only: the consistent all-cycle series (Presidential excluded by construction)' + ('' if c in PRES_YEARS else '; midterm source has no Presidential table - absent, not zero')
        return 'Presidential+House+Senate, presidential-year sources only'

