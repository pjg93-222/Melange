from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = root / 'osc' / 'extract.py'
s = p.read_text(encoding='utf-8')


def rep(old, new, count=1):
    global s
    assert s.count(old) >= 1, old[:70]
    s = s.replace(old, new, count)


marker = '    # ---- lobbying ----'
i = s.index(marker)
s = s[:i] + (root / 'scratch' / 'pac_new.txt').read_text(encoding='utf-8') + s[i:]
# constructor
rep("    def __init__(self, fetcher, cfg, log=print, roster_csv=None):\n", "    def __init__(self, fetcher, cfg, log=print, roster_csv=None, offline_dir=None):\n")
rep("        self.asof = {}\n", "        self.asof = {}\n        self.offline = self.load_offline(offline_dir)   # (scope_id, year) -> supplemental native-export info; {} when no directory\n")
# schemas
rep("'spending_period_start', 'spending_period_end', 'period_note'] + PROV,", "'spending_period_start', 'spending_period_end', 'period_note', 'capture_date', 'capture_timestamp_status'] + PROV,")
rep("    'lobbying_clients': ID + YR", "    'lobbying_annual_offline_export': ID + ['requested_year', 'source_category_id', 'spend_usd', 'lobbyists_count', 'lobbyists_note', 'http_annual_spend_usd',\n"
    "                                            'comparison', 'source_file', 'source_file_sha256', 'source_method', 'source_page_url', 'capture_date',\n"
    "                                            'capture_timestamp_status', 'source_as_of_note'] + PROV,\n    'lobbying_clients': ID + YR")
# modern fallback
rep("""            if an is None or spend is None:
                self.add('lobbying_annual', {**row, **self.prov(ares, None, 'modern', 'fetch_failed' if an is None else 'year_not_in_chart', 'unavailable',
                         self.fail_reason(ares) if an is None else 'year_not_in_chart', 'annual chart (annual_trends chunk)')})
""", """            if an is None or spend is None:
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
""")
# legacy fallback
rep("""            else:
                self.add('lobbying_annual', {**base, **self.prov(anres, None, 'legacy', 'year_not_in_chart', 'unavailable', 'year_not_in_chart')})
""", """            elif self.offline.get((s['scope_id'], y)):
                off = self.offline[(s['scope_id'], y)]
                self.add('lobbying_annual', {**base, 'served_year': y, 'spend_usd': off['spend'], 'in_house_outside_status': 'unavailable',
                         'capture_date': off['capture_date'], 'capture_timestamp_status': 'date_only_time_not_recorded',
                         **self.offline_prov(off, 'offline_export', 'partial', 'legacy_chart_unavailable_offline_capture_used',
                                             'exact legacy T2100 browser capture; as-of unknown; NOT the broader modern M02 Automotive')})
            else:
                self.add('lobbying_annual', {**base, **self.prov(anres, None, 'legacy', 'year_not_in_chart', 'unavailable', 'year_not_in_chart')})
""")
# build the offline table after the lobbying loop
rep("""                for y in C.YEARS:
                    self.add('lobbying_annual', {**idf, 'requested_year': y, **self.prov(None, None, '', 'not_requested', 'unavailable', 'no_published_industry_code', s['scope_note'])})
""", """                for y in C.YEARS:
                    self.add('lobbying_annual', {**idf, 'requested_year': y, **self.prov(None, None, '', 'not_requested', 'unavailable', 'no_published_industry_code', s['scope_note'])})
        self.offline_export_table()
""")
# run_extract_and_validate
rep("    ex = Extractor(fetcher, cfg, roster_csv=a.roster_csv)", "    ex = Extractor(fetcher, cfg, roster_csv=a.roster_csv, offline_dir=a.offline_lobby_dir)")
p.write_text(s, encoding='utf-8')

c = root / 'osc' / 'config.py'
t = c.read_text(encoding='utf-8')
t = t.replace("DEFAULT_ROSTER = ", "DEFAULT_OFFLINE_LOBBY = Path('C:/melange-data/forecast-redesign-20261001-review/source-recovery/lobbying')\nDEFAULT_ROSTER = ", 1)
c.write_text(t, encoding='utf-8')
c = root / 'osc' / 'cli.py'
t = c.read_text(encoding='utf-8')
t = t.replace("    p.add_argument('--concurrency'", "    p.add_argument('--offline-lobby-dir', default=str(C.DEFAULT_OFFLINE_LOBBY),\n"
              "                   help='directory with the unchanged native annual-lobbying exports + RECOVERY_NOTES.txt (supplemental, used only where the HTTP annual chart is unavailable); \"\" disables')\n"
              "    p.add_argument('--concurrency'", 1)
c.write_text(t, encoding='utf-8')
print('offline spliced')
