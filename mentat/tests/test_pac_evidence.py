import sys
from pathlib import Path
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from pac_evidence import Client, receipt_role, summarize, temporal_routes


class EvidenceTests(unittest.TestCase):
    def test_sale_and_memo_are_not_new_donations_even_with_contribution_code(self):
        sale = {'contributor_name': 'EXAMPLE EXCHANGE', 'receipt_type': '10', 'filing_form': 'F3X', 'line_number': '17',
                'receipt_type_full': '25,000,000 USDC SOLD VIA EXCHANGE - PURCHASER UNKNOWN'}
        self.assertEqual(receipt_role(sale), 'asset_liquidation')
        self.assertEqual(receipt_role({**sale, 'memo_code': 'X', 'receipt_type_full': 'CONTRIBUTION PREVIOUSLY DISCLOSED'}), 'previously_disclosed_memo')
        self.assertEqual(receipt_role({'filing_form':'F3X', 'line_number':'11AI', 'receipt_type_full':'IN-KIND - BITCOIN NOT LIQUIDATED'}), 'in_kind_contribution')

    def test_cash_contribution_and_other_receipt_are_distinct(self):
        self.assertEqual(receipt_role({'filing_form':'F3X', 'line_number':'11AI'}), 'contribution')
        self.assertEqual(receipt_role({'filing_form':'F3X', 'line_number':'17'}), 'other_receipt')
        self.assertEqual(receipt_role({'contributor_name':'Acme'}), 'unverified_receipt_role')

    def test_count_cursor_integrity_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def transport(endpoint, params):
                calls.append(params)
                i = len(calls)
                return {'results':[{'sub_id':str(i)}], 'pagination':{'count':2, 'is_count_exact':True, 'last_indexes':{'last_index':str(i)}}}
            client = Client(directory, key='fixture-secret', transport=transport)
            self.assertEqual(len(client.rows('schedules/schedule_a/', {})), 2)
            self.assertEqual(calls[1]['last_index'], '1')
            self.assertEqual(len(client.rows('schedules/schedule_a/', {})), 2)
            self.assertEqual(len(calls), 2)
            self.assertNotIn('fixture-secret', ''.join(p.read_text() for p in Path(directory).glob('*.json')))

    def test_incomplete_pagination_does_not_publish_success(self):
        with tempfile.TemporaryDirectory() as directory:
            client = Client(directory, key='fixture', transport=lambda *_: {'results':[{'sub_id':'1'}], 'pagination':{'count':2,'is_count_exact':True,'last_indexes':{}}})
            with self.assertRaisesRegex(ValueError, 'Incomplete'):
                client.rows('schedules/schedule_a/', {})

    def test_company_funding_personal_money_and_committee_activity_stay_separate(self):
        snapshot = {'committee_id':'C00000001','cycle':2024,'totals':{'independent_expenditures':100},
                    'receipts':[{'sub_id':'1','contributor_name':'Acme', 'filing_form':'F3X','line_number':'11AI','contribution_receipt_amount':50},
                                {'sub_id':'2','contributor_name':'CEO, JANE', 'filing_form':'F3X','line_number':'11AI','contribution_receipt_amount':100}],
                    'disbursements':[], 'expenditures':[{'sub_id':'3','expenditure_amount':100,'candidate_id':'H00000001','candidate_name':'DOE, JANE','support_oppose_indicator':'O'}]}
        result = summarize([snapshot], 'Acme', [])
        self.assertEqual(len(result['receipts']), 1)
        self.assertEqual(result['candidate_activity'][0]['direction'], 'Oppose')
        self.assertIsNone(result['candidate_activity'][0]['company_attributed_amount'])
        self.assertTrue(result['committee_finances'][0]['regular_ie_reconciles'])

    def test_dates_block_retroactive_spending_and_unliquidated_assets(self):
        receipt = {'sub_id':'late', 'company':'Acme', 'committee_id':'C1', 'cycle':2024,
                   'included_company_contribution':True, 'date':'2024-12-20', 'amount':23000000, 'role':'contribution'}
        activity = {'cycle':2024,'committee_id':'C2','candidate_id_as_filed':'H00000001','candidate_name_as_filed':'DOE, JANE',
                    'direction':'Support','committee_spending':100,'first_date':'2024-10-01','last_date':'2024-10-31'}
        evidence = {'receipts':[receipt], 'transfers':[{'cycle':2024,'source':'C1','destination':'C2','date':'2024-09-01','amount':100}],
                    'candidate_activity':[activity]}
        self.assertEqual(temporal_routes(evidence)[0]['status'], 'no_dated_route_in_observed_scope')
        receipt['date'] = '2024-08-01'
        self.assertEqual(temporal_routes(evidence)[0]['path'], ['C1','C2'])
        self.assertIsNone(temporal_routes(evidence)[0]['company_attributed_amount'])
        receipt['role'] = 'in_kind_contribution'
        self.assertEqual(temporal_routes(evidence)[0]['status'], 'asset_liquidation_link_required')


if __name__ == '__main__':
    unittest.main()
