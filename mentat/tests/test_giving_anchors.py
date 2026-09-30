"""The anchor snapshot builder (mentat/forecast/anchors): built against synthetic Mentat data with hand-computed expectations, asserted
against the shared contract (schema, invariants, negative controls), plus read-only and refusal guarantees. A run against the real
Mentat tree (ADDENDUM section F numbers) is opt-in: MENTAT_ANCHORS_REAL=1 (credit unions) or =all (banks too)."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'forecast' / 'anchors'))
sys.path.insert(0, str(ROOT / 'forecast' / 'contracts'))
import build_giving_anchors as bga  # noqa: E402
import contract  # noqa: E402
import coverage  # noqa: E402
import cpi as cpi_mod  # noqa: E402
import d049  # noqa: E402
import fec_pas2  # noqa: E402
import lda as lda_mod  # noqa: E402
import mentat_sources as ms  # noqa: E402
import openpyxl  # noqa: E402

PAS2_HEAD = ['CMTE_ID', 'AMNDT_IND', 'RPT_TP', 'TRANSACTION_PGI', 'IMAGE_NUM', 'TRANSACTION_TP', 'ENTITY_TP', 'NAME', 'CITY', 'STATE', 'ZIP_CODE',
             'EMPLOYER', 'OCCUPATION', 'TRANSACTION_DT', 'TRANSACTION_AMT', 'OTHER_ID', 'CAND_ID', 'TRAN_ID', 'FILE_NUM', 'MEMO_CD', 'MEMO_TEXT', 'SUB_ID']


def pas2_line(cmte, tp, amount, cand, dt, tran, file_num, sub, amndt='N', memo=''):
    row = dict.fromkeys(PAS2_HEAD, '')
    row.update(CMTE_ID=cmte, AMNDT_IND=amndt, RPT_TP='Q1', TRANSACTION_TP=tp, TRANSACTION_DT=dt, TRANSACTION_AMT=str(amount), CAND_ID=cand,
               TRAN_ID=tran, FILE_NUM=str(file_num), SUB_ID=str(sub), MEMO_CD=memo)
    return '|'.join(row[k] for k in PAS2_HEAD)


def write_text(path, lines):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='latin-1')


class World:
    """A synthetic Mentat project + report directory + FEC bulk files + LDA file + CPI workbook, all in one temp folder."""

    SCRAPED = '2026-07-28T03:06:03'

    def __init__(self, base, workbook_bytes=b'published workbook v1', cut_back=None, roster=('C00000001', 'C00000002')):
        self.base = Path(base)
        self.project = self.base / 'mentat'
        self.report = self.base / 'reports'
        self.fec = self.base / 'fec'
        self.report.mkdir(parents=True)
        self.workbook = self.report / 'Banking Industry Spending Overview.xlsx'
        self.workbook.write_bytes(workbook_bytes)
        self.cut_back, self.roster = cut_back, roster
        self._source_db()
        self._index()
        self._fec()
        self._lda()
        self._cpi()
        self.registry = {'schema_version': 1, 'thin_base_threshold_usd': 500, 'industries': [{
            'id': 'commercial_banks', 'label': 'Commercial banks (test)', 'forecast_industry': 'commercial_banks', 'mentat_dataset': 'Banking',
            'workbook': self.workbook.name, 'source_db_candidates': ['.cache/report-repairs/banking-*/data/mentat.db'], 'lda_sector': 'bank',
            'coverage_cut_back': cut_back, 'pac_roster': [{'id': c, 'company': 'Bank ' + c[-1]} for c in roster]}, {
            'id': 'property_casualty', 'label': 'P&C (test)', 'forecast_industry': 'property_casualty', 'mentat_dataset': 'Property & Casualty Insurance',
            'workbook': 'Property & Casualty Insurance Industry Spending Overview.xlsx', 'source_db_candidates': ['.cache/none/mentat.db'], 'lda_sector': None,
            'coverage_cut_back': None, 'pac_roster': []}]}
        self.options = dict(report_dir=self.report, fec_root=self.fec, lda_csv=self.base / 'sector_spend.csv', controls=self.base / '00_controls.xlsx', only=None, run=None)

    # (sub_id, cycle label, date, party, funding source, receipt cents, committee type)
    FACTS = [
        (1, '2023-2024', '2023-05-10', 'D', 'employee_original', 100000, 'H'),
        (2, '2023-2024', '2024-02-01', 'R', 'employee_original', 200000, 'H'),
        (3, '2023-2024', '2024-03-01', 'D', 'employee_original', 50000, 'S'),
        (4, '2023-2024', '2024-04-01', 'R', 'employee_original', 150000, 'S'),
        (5, '2023-2024', '2024-05-01', 'R', 'employee_original', 999900, 'P'),
        (6, '2023-2024', '2024-06-01', 'R', 'employee_original', 10000, 'Q'),
        (7, '2023-2024', '2024-07-01', 'D', 'employee_original', -5000, 'H'),
        (8, '2023-2024', '2024-08-01', 'I', 'non_giving', 2500, 'H'),
        (9, '2023-2024', '2024-09-01', 'D', 'employee_original', 0, 'H'),
        (10, '2021-2022', '2022-06-01', 'R', 'employee_original', 70000, 'S'),
        (11, '2025-2026', '2025-03-10', 'D', 'employee_original', 30000, 'H'),
        (12, '2025-2026', '2025-09-15', 'R', 'employee_original', 40000, 'H'),
        (13, '2025-2026', '2026-01-20', 'R', 'employee_original', 60000, 'S'),
        (14, '2025-2026', '2026-06-20', 'D', 'employee_original', 70000, 'H'),
        (15, '2025-2026', '2026-07-20', 'D', 'employee_original', 80000, 'S'),
    ]

    def _source_db(self):
        path = self.project / '.cache' / 'report-repairs' / 'banking-20260910' / 'data' / 'mentat.db'
        path.parent.mkdir(parents=True)
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE contributions(sub_id INTEGER, recipient_committee_type TEXT, scraped_at TEXT, industry TEXT)')
        db.execute('CREATE TABLE corporate_giving(sub_id INTEGER, recipient_committee_type TEXT, scraped_at TEXT, industry TEXT)')
        db.execute('CREATE TABLE api_work_progress(cycle INTEGER, fetched_complete INTEGER, stored_complete INTEGER)')
        for sub, _c, _d, _p, _s, _v, t in self.FACTS:
            db.execute('INSERT INTO contributions VALUES (?,?,?,?)', (sub, t, '2026-07-01T00:00:00', 'Banking'))
        db.execute('INSERT INTO corporate_giving VALUES (8, "H", ?, "Banking")', (self.SCRAPED,))
        for fetched, stored in ((1, 1), (1, 0), (1, 0)):
            db.execute('INSERT INTO api_work_progress VALUES (2026, ?, ?)', (fetched, stored))
        db.commit()
        db.close()
        self.source_db = path
        self.db_sha = hashlib.sha256(path.read_bytes()).hexdigest()

    def _index(self, built_at=1790000000.0, token='t' * 64):
        folder = self.project / 'state' / 'contribution-analytics'
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / (token + '.sqlite')
        db = sqlite3.connect(path)
        db.execute('CREATE TABLE facts(source_id TEXT PRIMARY KEY, cycle TEXT, date TEXT, party TEXT, recipient_category TEXT, funding_source TEXT, receipt_cents INTEGER)')
        totals = {}
        for sub, cycle, day, party, source, cents, _t in self.FACTS:
            db.execute('INSERT INTO facts VALUES (?,?,?,?,?,?,?)', (str(sub), cycle, day, party, 'Candidate', source, cents))
            totals[cycle] = totals.get(cycle, 0) + cents
        manifest = {'token': token, 'built_at': built_at, 'receipt_cycles': totals,
                    'provenance': {'workbook': self.workbook.name, 'workbook_sha256': hashlib.sha256(self.workbook.read_bytes()).hexdigest(),
                                   'database_sha256': self.db_sha, 'payload_sha256': 'b' * 64}}
        db.execute('CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL)')
        db.execute('INSERT INTO metadata VALUES (?,?)', ('manifest', json.dumps(manifest)))
        db.commit()
        db.close()
        self.index = path

    def _fec(self):
        cn = {'22': ['H2AA00001|A|DEM'], '24': ['H2AA00001|A|DEM', 'S2BB00002|B|REP', 'H2CC00003|C|IND', 'P80000001|P|REP'],
              '26': ['H2AA00001|A|DEM', 'S2BB00002|B|REP', 'H2CC00003|C|IND']}
        for yy, rows in cn.items():
            write_text(self.fec / 'fec_beneficiary' / ('cn' + yy) / 'cn.txt', [r.split('|')[0] + '|' + r.split('|')[1] + '|' + r.split('|')[2] + '|||||||||||' for r in rows])
            write_text(self.fec / 'fec_committee_master' / ('cm' + yy) / 'cm.txt', [c + '|NAME|||||||||Q||||' for c in ('C00000001', 'C00000002')])
        H, S, P = 'H2AA00001', 'S2BB00002', 'P80000001'
        pas = {
            '22': [pas2_line('C00000001', '24K', 1000, H, '03152022', 'X1', 50, 5001)],
            '24': [pas2_line('C00000001', '24K', 2000, H, '03152024', 'A1', 100, 1001),
                   pas2_line('C00000001', '24K', 2000, H, '03152024', 'A1', 100, 1001),       # exact duplicate sub_id: counted once
                   pas2_line('C00000001', '24K', 1000, S, '06202024', 'A2', 100, 1002),
                   pas2_line('C00000002', '24Z', 500, 'H2CC00003', '07012024', 'A4', 100, 1004),  # in-kind, other party
                   pas2_line('C00000001', '24A', 7000, H, '07012024', 'A5', 100, 1005),         # independent expenditure: excluded
                   pas2_line('C00000001', '24E', 6000, H, '07012024', 'A6', 100, 1006),
                   pas2_line('C00000001', '24K', -300, H, '09012024', 'A3', 101, 1003),         # refund nets out
                   pas2_line('C00000001', '24K', 100, P, '08012024', 'B1', 100, 1007),          # presidential
                   pas2_line('C00000002', '24K', 50, '', '08022024', 'B2', 100, 1008),          # no candidate id
                   pas2_line('C00000999', '24K', 5000, H, '03152024', 'Z1', 100, 1009)],        # not a roster committee
            '26': [pas2_line('C00000001', '24K', 400, H, '04102025', 'C1', 200, 2001),
                   pas2_line('C00000002', '24K', 600, S, '02102026', 'C2', 200, 2002),
                   pas2_line('C00000001', '24K', 800, H, '05202026', 'C3', 200, 2003),
                   pas2_line('C00000001', '24K', 900, S, '06152026', 'C4', 200, 2004),
                   pas2_line('C00000002', '24K', 1000, H, '07102026', 'C5', 200, 2005)]}
        for yy, lines in pas.items():
            folder = self.fec / 'fec_beneficiary' / ('pas2' + yy)
            write_text(folder / 'itpas2.txt', lines)
            sha = hashlib.sha256((folder / 'itpas2.txt').read_bytes()).hexdigest()
            (folder / 'source-receipt.json').write_text(json.dumps({'sha256': sha, 'last_modified': 'Sun, 06 Sep 2026 15:55:17 GMT'}))

    def _lda(self):
        head = 'sector,year,period,is_partial_year,distinct_organizations,filings,income_total,expenses_total'
        rows = [head]
        for year, inc, exp in ((2024, 400, 900), (2025, 500, 1000)):
            rows.append(f'bank,{year},annual,false,9,9,{inc},{exp}')
            for q in (1, 2, 3, 4):
                rows.append(f'bank,{year},Q{q},false,9,9,{inc / 4},{exp / 4}')
        rows += ['bank,2026,annual,true,9,9,300,600', 'bank,2026,Q1,true,9,9,100,200', 'bank,2026,Q2,true,9,9,200,400', 'bank,2026,Q3,true,0,0,0,0', 'bank,2026,Q4,true,0,0,0,0']
        (self.base / 'sector_spend.csv').write_text('\n'.join(rows) + '\n')

    def _cpi(self):
        book = openpyxl.Workbook()
        sheet = book.active
        sheet.title = 'data'
        sheet.append(['year', 'cpi_annual_average'])
        for year, value in ((2021, 270.0), (2022, 290.0), (2023, 300.0), (2024, 310.0), (2025, 320.0), (2026, None)):
            sheet.append([year, value])
        book.save(self.base / '00_controls.xlsx')

    def build(self, **kw):
        return bga.build_snapshot(self.project, self.registry, {**self.options, **kw})


class BuilderTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.world = World(self.tmp.name)

    # --- numbers ----------------------------------------------------------------------------------------------------------------
    def test_general_giving_is_the_included_receipt_amount_net_of_adjustments(self):
        snap, _ = self.world.build()
        g = snap['industries']['commercial_banks']['general_giving']
        # 2023-24: 1,000 + 2,000 + 500 + 1,500 + 9,999 + 100 - 50 + 25 (the zero-receipt fact is not an included receipt)
        self.assertEqual(g['cycles'], {'2022': 700.0, '2024': 15074.0, '2026': 2800.0})
        self.assertEqual(g['by_funding_source']['2024'], {'employee_original': 15049.0, 'non_giving': 25.0})
        self.assertEqual(sum(g['by_funding_source']['2024'].values()), g['cycles']['2024'])

    def test_observed_cuts_are_cumulative_month_ends_and_stop_at_the_coverage_end(self):
        snap, _ = self.world.build()
        ind = snap['industries']['commercial_banks']
        cuts = ind['general_giving']['observed']
        self.assertEqual(cuts[0], {'through': '2025-01-31', 'amount': 0.0})
        self.assertEqual(cuts[-1]['through'], '2026-06-30')
        self.assertEqual(len(cuts), 18)
        by = {c['through']: c['amount'] for c in cuts}
        self.assertEqual(by['2025-03-31'], 300.0)
        self.assertEqual(by['2025-09-30'], 700.0)
        self.assertEqual(by['2026-01-31'], 1300.0)
        self.assertEqual(by['2026-06-30'], 2000.0)           # the 2026-07-20 row is after the coverage end
        self.assertEqual(ind['general_giving']['cycles']['2026'], 2800.0)   # the open cycle holds every row to date
        self.assertTrue(any('dated after the coverage end ($800.00)' in f for f in ind['coverage']['flags']))

    def test_cut_back_moves_the_coverage_end_and_leaves_later_rows_unobserved(self):
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        world = World(self.tmp.name, cut_back={'when_rule_coverage_end': '2026-06-30', 'coverage_end': '2026-05-31', 'reason': 'June incomplete'})
        snap, _ = world.build()
        ind = snap['industries']['commercial_banks']
        self.assertEqual(ind['coverage']['rule_coverage_end'], '2026-06-30')
        self.assertEqual(ind['coverage']['coverage_end'], '2026-05-31')
        self.assertEqual(ind['coverage']['reason'], 'June incomplete')
        self.assertEqual(ind['general_giving']['observed'][-1], {'through': '2026-05-31', 'amount': 1300.0})   # the 2026-06-20 row is not observed
        self.assertEqual(ind['pac_to_candidates']['observed'][-1]['through'], '2026-05-31')
        self.assertEqual(contract.check_anchor_invariants(snap), [])

    def test_candidate_receipts_split_by_committee_type_and_party(self):
        snap, _ = self.world.build()
        c = snap['industries']['commercial_banks']['candidate_receipts']
        self.assertEqual(c['cycles']['2024']['House'], {'D': 1000.0 - 50.0, 'R': 2000.0, 'other': 25.0})     # adjustment nets; other party kept apart
        self.assertEqual(c['cycles']['2024']['Senate'], {'D': 500.0, 'R': 1500.0, 'other': 0.0})
        self.assertEqual(c['cycles']['2022']['Senate'], {'D': 0.0, 'R': 700.0, 'other': 0.0})             # no House row in 2022: only the chambers with rows exist
        last = c['observed'][-1]
        self.assertEqual(last['House'], {'D': 1000.0, 'R': 400.0, 'other': 0.0})
        self.assertEqual(last['Senate'], {'D': 0.0, 'R': 600.0, 'other': 0.0})

    def test_thin_base_flags_follow_the_threshold_per_chamber(self):
        snap, _ = self.world.build()
        thin = snap['industries']['commercial_banks']['candidate_receipts']['thin_base']
        self.assertEqual(thin['2024'], {'House': False, 'Senate': False})       # 2950 and 2000 against a $500 test threshold
        self.assertEqual(thin['2022'], {'House': True, 'Senate': False})

    def test_pac_to_candidates_follows_the_d049_rules(self):
        snap, _ = self.world.build()
        p = snap['industries']['commercial_banks']['pac_to_candidates']
        y24 = p['cycles']['2024']
        self.assertEqual(y24['House'], {'D': 2000.0 - 300.0, 'R': 0.0, 'other': 500.0})       # duplicate counted once; refund nets out; 24A/24E excluded; in-kind counted
        self.assertEqual(y24['Senate'], {'D': 0.0, 'R': 1000.0, 'other': 0.0})
        self.assertEqual(y24['presidential'], 100.0)
        self.assertEqual(y24['no_candidate'], 50.0)
        self.assertEqual(y24['to_house_senate'], 3200.0)
        self.assertEqual(y24['all_recipients'], 3350.0)
        self.assertEqual(p['cycles']['2022']['to_house_senate'], 1000.0)
        self.assertEqual(p['committee_count'], 2)
        self.assertFalse(p['single_pac'])

    def test_pac_observed_cuts_run_to_the_coverage_end_and_the_file_total_is_separate(self):
        snap, _ = self.world.build()
        p = snap['industries']['commercial_banks']['pac_to_candidates']
        last = p['observed'][-1]
        self.assertEqual(last['through'], '2026-06-30')
        self.assertEqual(last['House'], {'D': 1200.0, 'R': 0.0, 'other': 0.0})       # 2025-04-10 and 2026-05-20; the 2026-07-10 row is after the coverage end
        self.assertEqual(last['Senate'], {'D': 0.0, 'R': 1500.0, 'other': 0.0})
        self.assertEqual(last['to_house_senate'], 2700.0)
        by = {c['through']: c['to_house_senate'] for c in p['observed']}
        self.assertEqual(by['2025-04-30'], 400.0)
        self.assertEqual(by['2026-02-28'], 1000.0)
        self.assertEqual(p['cycles']['2026']['to_house_senate'], 3700.0)             # every row in the file, including July
        self.assertEqual(p['file_through']['2026'], '2026-07-10')
        self.assertEqual({i['role'] for i in p['inputs']}, {f'{f}:{c}' for f in ('pas2', 'cn', 'cm') for c in (2022, 2024, 2026)})

    def test_single_committee_roster_is_flagged_single_pac(self):
        self.tmp.cleanup()
        self.tmp = tempfile.TemporaryDirectory()
        world = World(self.tmp.name, roster=('C00000001',))
        snap, _ = world.build()
        ind = snap['industries']['commercial_banks']
        self.assertTrue(ind['pac_to_candidates']['single_pac'])
        self.assertTrue(any('one committee' in f for f in ind['flags']))

    def test_lda_levels_keep_both_series_and_the_partial_year(self):
        snap, _ = self.world.build()
        lda = snap['industries']['commercial_banks']['lda']
        self.assertEqual(lda['status'], 'ready')
        self.assertEqual(lda['series']['income_total']['annual'], {'2024': 400.0, '2025': 500.0})
        self.assertEqual(lda['series']['expenses_total']['annual'], {'2024': 900.0, '2025': 1000.0})
        self.assertEqual(lda['series']['income_total']['partial'], {'year': 2026, 'through_quarter': 'Q2', 'quarters': {'Q1': 100.0, 'Q2': 200.0}, 'total': 300.0})
        self.assertEqual(lda['series']['expenses_total']['partial']['total'], 600.0)
        self.assertEqual(lda['through'], '2026-06-30')

    def test_cpi_multiplier_exists_only_for_cycles_with_a_published_cpi(self):
        snap, _ = self.world.build()
        self.assertEqual(snap['cpi']['multipliers'], {'2022': 320.0 / 280.0, '2024': 320.0 / 305.0})
        self.assertNotIn('2026', snap['cpi']['multipliers'])
        self.assertTrue(any('No 2026 CPI exists yet' in f for f in snap['industries']['commercial_banks']['coverage']['flags']))

    def test_work_unit_progress_flags_an_incomplete_collection(self):
        snap, _ = self.world.build()
        flags = ' '.join(snap['industries']['commercial_banks']['coverage']['flags'])
        self.assertIn('1 of 3 2026 collection work units are stored_complete (3 fetched)', flags)

    def test_an_industry_without_a_published_workbook_is_reported_unavailable_not_invented(self):
        snap, _ = self.world.build()
        self.assertEqual(list(snap['industries']), ['commercial_banks'])
        self.assertIn('property_casualty', snap['unavailable'])
        self.assertIn('not in the report directory', snap['unavailable']['property_casualty'])

    def test_an_industry_with_no_lda_sector_or_roster_is_unavailable_per_measure(self):
        self.world.registry['industries'][0].update(lda_sector=None, pac_roster=[])
        snap, _ = self.world.build()
        ind = snap['industries']['commercial_banks']
        self.assertEqual(ind['lda']['status'], 'unavailable')
        self.assertIn('No Melange-LDA sector', ind['lda']['reason'])
        self.assertEqual(ind['pac_to_candidates']['status'], 'unavailable')
        self.assertEqual(ind['status']['general_giving'], 'ready')
        self.assertEqual(bga.validate_snapshot(snap), [])

    def test_a_missing_index_for_the_published_workbook_is_refused_with_a_reason(self):
        self.world.workbook.write_bytes(b'republished workbook v2')            # its sha no longer matches the index
        snap, _ = self.world.build()
        self.assertEqual(snap['industries'], {})
        self.assertIn('No contribution-analytics index matches the published workbook', snap['unavailable']['commercial_banks'])

    def test_the_newest_index_of_the_published_workbook_is_used(self):
        self.world._index(built_at=1790000100.0, token='u' * 64)
        snap, _ = self.world.build()
        self.assertEqual(snap['industries']['commercial_banks']['mentat']['index_token'], 'u' * 64)

    # --- contract ---------------------------------------------------------------------------------------------------------------
    def test_the_built_snapshot_satisfies_the_shared_schema_and_invariants(self):
        snap, _ = self.world.build()
        self.assertEqual(contract.validate_kind(snap, 'anchors'), [])
        self.assertEqual(contract.check_anchor_invariants(snap), [])

    def test_every_anchor_negative_control_fails_against_the_built_snapshot_and_the_example(self):
        snap, _ = self.world.build()
        for label, doc in (('built', snap), ('example', contract.example('anchors'))):
            for control in (c for c in contract.negative_controls() if c['target'] == 'anchors'):
                path = list(control['path'])
                ident = 'commercial_banks'
                path = [ident if step == '<industry>' else step for step in path]
                mutated = contract.apply_mutation(doc, {**control, 'path': path})
                problems = contract.validate_kind(mutated, 'anchors')
                if control['kind'] == 'invariant' and not problems:
                    problems = contract.check_anchor_invariants(mutated)
                with self.subTest(document=label, control=control['id']):
                    self.assertNotEqual(problems, [], control['why'])

    # --- guarantees -------------------------------------------------------------------------------------------------------------
    def _hashes(self):
        out = {}
        for folder in (self.world.project, self.world.report, self.world.fec):
            for path in sorted(folder.rglob('*')):
                if path.is_file():
                    out[str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        for name in ('sector_spend.csv', '00_controls.xlsx'):
            out[name] = hashlib.sha256((self.world.base / name).read_bytes()).hexdigest()
        return out

    def _run(self, out, run_id=None):
        registry_path = Path(out) / 'registry.json'
        registry_path.write_text(json.dumps(self.world.registry))
        return (self.world.project, Path(out) / 'state', None, registry_path, self.world.fec, self.world.base / 'sector_spend.csv',
                self.world.base / '00_controls.xlsx', self.world.report, run_id)

    def test_the_build_changes_no_input_file(self):
        before = self._hashes()
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {'ANCHORS_GLASSBOX_DIR': str(Path(out) / 'gb')}):
            final, receipt, snapshot = bga.run_build(*self._run(out))
            self.assertEqual(self._hashes(), before)
            self.assertEqual(receipt['snapshot_sha256'], hashlib.sha256(final.read_bytes()).hexdigest())
            self.assertEqual(json.loads(final.read_text(encoding='utf-8')), snapshot)
            self.assertEqual(sorted(p.name for p in final.parent.iterdir()), sorted([bga.RECEIPT_NAME, bga.SNAPSHOT_NAME]))   # no temp file left behind

    def test_sqlite_connections_cannot_write(self):
        db = ms.ro_connect(self.world.index)
        self.addCleanup(db.close)
        with self.assertRaises(sqlite3.OperationalError):
            db.execute('CREATE TABLE should_fail(x)')
        with self.assertRaises(sqlite3.OperationalError):
            db.execute('DELETE FROM facts')
        self.assertIn('immutable=1', ms.ro_uri(self.world.index))

    def test_an_invalid_build_leaves_the_previous_snapshot_in_place(self):
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {'ANCHORS_GLASSBOX_DIR': str(Path(out) / 'gb')}):
            args = self._run(out)
            final, _receipt, _snap = bga.run_build(*args)
            good = final.read_bytes()
            with patch.object(bga, 'validate_snapshot', return_value=['forced problem']):
                with self.assertRaises(ValueError):
                    bga.run_build(*args)
            self.assertEqual(final.read_bytes(), good)
            self.world.workbook.write_bytes(b'republished workbook v2')    # no industry can be anchored any more
            with self.assertRaises(ValueError):
                bga.run_build(*args)
            self.assertEqual(final.read_bytes(), good)

    def test_glass_box_events_are_emitted_for_a_run(self):
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {'ANCHORS_GLASSBOX_DIR': str(Path(out) / 'gb')}):
            bga.run_build(*self._run(out, 'test-run'))
            events = [json.loads(p.read_text()) for p in sorted((Path(out) / 'gb').glob('evt-*.json'))]
            self.assertEqual(events[0]['kind'], 'run.start')
            self.assertEqual(events[-1]['kind'], 'run.finish')
            self.assertEqual({e['run_id'] for e in events}, {'test-run'})
            self.assertEqual({e['source'] for e in events}, {'giving-forecast-anchors'})
            self.assertTrue(all(e['parent_id'] in ('', events[0]['id']) for e in events))

    def test_check_reports_a_republished_workbook_as_stale(self):
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {'ANCHORS_GLASSBOX_DIR': str(Path(out) / 'gb')}):
            final, _r, _s = bga.run_build(*self._run(out))
            self.assertEqual(bga.check_fresh(final, self.world.project, self.world.report), {'commercial_banks': 'fresh'})
            self.world.workbook.write_bytes(b'republished workbook v2')
            self.assertEqual(bga.check_fresh(final, self.world.project, self.world.report), {'commercial_banks': 'stale'})
            self.world.workbook.unlink()
            self.assertEqual(bga.check_fresh(final, self.world.project, self.world.report), {'commercial_banks': 'missing'})

    def test_a_fec_file_that_differs_from_its_source_receipt_makes_the_pac_measure_unavailable(self):
        (self.world.fec / 'fec_beneficiary' / 'pas224' / 'itpas2.txt').write_text('tampered\n')
        snap, _ = self.world.build()
        pac = snap['industries']['commercial_banks']['pac_to_candidates']
        self.assertEqual(pac['status'], 'unavailable')
        self.assertIn('differs from its source receipt', pac['reason'])
        self.assertEqual(snap['industries']['commercial_banks']['general_giving']['status'], 'ready')


class PartsTests(unittest.TestCase):
    def test_coverage_end_is_the_last_quarter_whose_report_deadline_passed(self):
        cases = {'2026-09-09': '2026-06-30', '2026-07-28': '2026-06-30', '2026-07-14': '2026-03-31', '2026-07-15': '2026-06-30',
                 '2026-10-14': '2026-06-30', '2026-10-15': '2026-09-30', '2027-01-14': '2026-09-30', '2027-01-15': '2026-12-31', '2026-04-15': '2026-03-31'}
        for collected, expected in cases.items():
            with self.subTest(collected=collected):
                self.assertEqual(coverage.rule_coverage_end(collected).isoformat(), expected)

    def test_cut_back_applies_only_while_the_rule_end_is_the_one_it_names(self):
        rule = {'when_rule_coverage_end': '2026-06-30', 'coverage_end': '2026-05-31', 'reason': 'June incomplete'}
        self.assertEqual(coverage.coverage('2026-07-28', rule)['coverage_end'], '2026-05-31')
        self.assertEqual(coverage.coverage('2026-10-20', rule)['coverage_end'], '2026-09-30')     # a later collection is not cut back
        self.assertIsNone(coverage.coverage('2026-10-20', rule)['reason'])

    def test_month_ends_include_leap_february_and_stop_at_the_last_date(self):
        ends = fec_pas2.month_ends(2023, '2024-03-31')
        self.assertEqual(ends[0], '2023-01-31')
        self.assertIn('2024-02-29', ends)
        self.assertEqual(ends[-1], '2024-03-31')

    def test_d049_counts_the_latest_filing_of_an_identity_once(self):
        def row(rid, sub, file_num, amount, tran='T1', memo=''):
            return dict(rid=rid, cmte_id='C1', rpt_tp='Q1', tran_id=tran, sub_id=sub, file_num=file_num, amndt_ind='N', cand_id='H1', other_id='',
                        amount_cents=amount, date='2024-03-15', transaction_tp='24K', memo_cd=memo, order=rid)
        out = d049.resolve([row(0, '1', 10, 500), row(1, '2', 11, 500), row(2, '3', 11, 700, tran='T9', memo='X')])
        included = [rid for rid, v in out.items() if v['include']]
        self.assertEqual(included, [1])                     # the same identity re-filed later supersedes; a memo row never counts
        self.assertEqual(out[0]['status'], 'superseded_filing_version')
        self.assertEqual(out[2]['status'], 'memo_only')

    def test_a_reused_transaction_id_with_a_different_identity_is_a_different_transaction(self):
        def row(rid, sub, amount, date):
            return dict(rid=rid, cmte_id='C1', rpt_tp='Q1', tran_id='SE.5', sub_id=sub, file_num=10, amndt_ind='N', cand_id='H1', other_id='',
                        amount_cents=amount, date=date, transaction_tp='24K', memo_cd='', order=rid)
        out = d049.resolve([row(0, '1', 500, '2024-03-15'), row(1, '2', 900, '2024-09-15')])
        self.assertTrue(all(v['include'] for v in out.values()))

    def test_lda_partial_year_needs_filings_and_never_adds_the_two_series(self):
        head = 'sector,year,period,is_partial_year,distinct_organizations,filings,income_total,expenses_total'
        rows = [dict(zip(head.split(','), line.split(','))) for line in (
            'x,2025,annual,false,1,4,100,900', 'x,2026,annual,true,1,2,40,80', 'x,2026,Q1,true,1,1,10,20', 'x,2026,Q2,true,1,1,30,60', 'x,2026,Q3,true,0,0,0,0')]
        levels = lda_mod.sector_levels(rows, 'x')
        self.assertEqual(levels['series']['income_total']['partial']['quarters'], {'Q1': 10.0, 'Q2': 30.0})
        self.assertEqual(levels['series']['expenses_total']['annual'], {'2025': 900.0})
        self.assertNotIn('total_both', levels['series'])
        self.assertIsNone(lda_mod.sector_levels(rows, 'missing'))


@unittest.skipUnless(os.environ.get('MENTAT_ANCHORS_REAL'), 'set MENTAT_ANCHORS_REAL=1 (credit unions) or =all (banks too) to read the real Mentat tree')
class RealMentatTests(unittest.TestCase):
    """ADDENDUM section F, reproduced from the real published workbooks, indexes and FEC files (read-only)."""
    PROJECT = Path(os.environ.get('MENTAT_PROJECT_ROOT') or r'C:\Users\pgoff\Mentat\mentat')

    def build(self, ident):
        with tempfile.TemporaryDirectory() as out, patch.dict(os.environ, {'ANCHORS_GLASSBOX_DIR': str(Path(out) / 'gb')}):
            _final, _receipt, snap = bga.run_build(self.PROJECT, Path(out) / 'state', [ident])
        return snap['industries'][ident]

    def test_credit_unions_reproduce_section_f(self):
        ind = self.build('credit_unions')
        self.assertEqual(ind['coverage']['coverage_end'], '2026-05-31')
        self.assertEqual(ind['general_giving']['cycles'], {'2022': 369423.16, '2024': 779088.35, '2026': 273494.14})
        self.assertEqual(ind['general_giving']['observed'][-1]['amount'], 272141.16)
        house, senate = ind['candidate_receipts']['cycles']['2024']['House'], ind['candidate_receipts']['cycles']['2024']['Senate']
        self.assertEqual((house['D'], house['R'], senate['D'], senate['R']), (30832.81, 24291.13, 176326.42, 16751.75))
        self.assertEqual(ind['pac_to_candidates']['cycles']['2024']['to_house_senate'], 80800.0)
        self.assertEqual(ind['pac_to_candidates']['observed'][-1]['to_house_senate'], 54500.0)

    @unittest.skipUnless(os.environ.get('MENTAT_ANCHORS_REAL') == 'all', 'banks need the 861 MB join: MENTAT_ANCHORS_REAL=all')
    def test_banks_reproduce_section_f(self):
        ind = self.build('commercial_banks')
        self.assertEqual(ind['coverage']['coverage_end'], '2026-06-30')
        self.assertEqual(ind['general_giving']['cycles']['2024'], 26107204.16)
        self.assertEqual(ind['general_giving']['observed'][-1]['amount'], 11566804.77)
        self.assertEqual(ind['pac_to_candidates']['cycles']['2024']['to_house_senate'], 5692500.0)
        self.assertEqual(ind['pac_to_candidates']['observed'][-1]['to_house_senate'], 4673000.0)


if __name__ == '__main__':
    unittest.main()
