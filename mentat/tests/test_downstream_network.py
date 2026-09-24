"""Saved routes must survive diamonds, cycles, duplicate snapshots and gaps."""
from decimal import Decimal
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
import downstream
import evidence_geo


def unit(committee, destinations=(), spend=0, year='2026'):
    return {'committee_id':committee, 'cycle':year, '_source':'fixture', 'receipts':[],
            'disbursements':[{'line_number':'22','recipient_committee_id':d,'disbursement_amount':a}
                             for d,a in destinations],
            'expenditures':[{'candidate_id':'H0KY06104','candidate_name':'BARR, GARLAND ANDY',
                             'expenditure_amount':spend,'support_oppose_indicator':'S'}] if spend else [],
            'totals':{'disbursements':sum(a for _,a in destinations)+spend}}


class NetworkTests(unittest.TestCase):
    def test_selected_snapshot_root_reaches_saved_recipient_pacs_once(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            # A newer root-only capture must still reach the older saved
            # recipient. The selected root owns its outgoing route partition.
            old=root/'old'; old.mkdir()
            recent=root/'recent'; recent.mkdir()
            raw=[unit('A',[('B',30),('C',20)]),unit('B',[('D',10)]),
                 unit('C',[('D',10)]),unit('D',[('A',1),('MISSING',2)],31)]
            (old/'snapshots.json').write_text(json.dumps(raw))
            (recent/'snapshots.json').write_text(json.dumps([unit('A',[('B',30),('C',20)])]))
            result=downstream.snapshot_view('recent','A','2026',root)
            self.assertEqual(len(result['relationships']),1)
            row=result['relationships'][0]
            self.assertEqual(row['amount'],31)
            self.assertEqual(row['candidate_id'],'H0KY06104')
            self.assertEqual(row['route'][0],'A')
            self.assertEqual(row['route'][-1],'D')
            self.assertEqual(result['missing'],[{'cycle':'2026','committee':'MISSING'}])
            self.assertEqual(len(result['sources']),4)
            self.assertTrue(all(len(s['sha256'])==64 for s in result['sources']))
            root_source=next(s for s in result['sources'] if s['committee']=='A')
            self.assertEqual(root_source['source'],str(recent/'snapshots.json'))
            # No implicit cycle spillover or substitution of another root.
            with self.assertRaisesRegex(ValueError,'not in the selected'):
                downstream.snapshot_view('recent','A','2024',root)
            with self.assertRaisesRegex(ValueError,'Invalid evidence'):
                downstream.snapshot_view('../old','A','2026',root)

    def test_saved_snapshot_route_partition_overrides_report_routes(self):
        edges=[{'cycle':'2026','source':'A','destination':'OLD','amount':10},
               {'cycle':'2026','source':'B','destination':'D','amount':5}]
        units={('2026','A'):unit('A',[('B',3)])}
        found=downstream.network([('2026','A')],units,edges)
        self.assertNotIn(('2026','OLD'),found['keys'])
        self.assertIn(('2026','D'),found['keys'])
        with self.assertRaisesRegex(ValueError,'disagree'):
            downstream.network([('2026','B')],{},edges+[dict(edges[1],amount=6)])

    def test_diamond_cycle_missing_and_cycle_isolation(self):
        units = {('2026',c):u for c,u in {
            'A':unit('A',[('B',20),('C',20)]), 'B':unit('B',[('D',10)]),
            'C':unit('C',[('D',10)]), 'D':unit('D',[('A',1),('MISSING',2)],30)}.items()}
        units['2024','D'] = unit('D',spend=999,year='2024')
        found = downstream.network([('2026','A')],units)
        self.assertEqual(set(found['units']),{('2026',c) for c in 'ABCD'})
        self.assertEqual(found['missing'],[('2026','MISSING')])
        self.assertEqual(sum(r['amount'] for r in downstream.activity(found)),30)
        ties = downstream.relationships(downstream.activity(found),[('2026','A')],found)
        self.assertEqual(len(ties),1)
        self.assertEqual(len(ties[0]['route']),3)
        self.assertEqual(ties[0]['share_of_pac_direction'],1)

    def test_snapshot_candidate_payments_keep_their_transaction_codes(self):
        # Paul, 2026-09-23, on Graph's "Contributions / Other" segment: "It
        # should be two separate segments". A snapshot's Schedule B candidate
        # payments keep their FEC code (disbursement_type) beside the one
        # recorded direction, so graph_data can split the bucket by code; the
        # grouping and the recorded direction are unchanged.
        import graph_data
        payment = lambda candidate, code, value: {'line_number':'23','candidate_id':candidate,'candidate_name':candidate,
                                                  'disbursement_type':code,'disbursement_amount':value}
        a = unit('A')
        a['disbursements'] = [payment('H0CA00001','24K',100), payment('H0CA00001','24C',40),
                              payment('H0CA00001','24Z',5), payment('H0CA00002',None,7)]
        found = downstream.network([('2026','A')],{('2026','A'):a})
        rows = downstream.activity(found)
        self.assertEqual(sorted((r['candidate_id'],r['direction'],r['amount']) for r in rows),
                         [('H0CA00001','Contribution / Other',145),('H0CA00002','Contribution / Other',7)])
        one = next(r for r in rows if r['candidate_id'] == 'H0CA00001')
        self.assertEqual({code:part['amount'] for code,part in one['transaction_parts'].items()},{'24K':100,'24C':40,'24Z':5})
        self.assertEqual(len(one['filings']),3)
        sides = graph_data.activity_sides(rows)
        self.assertEqual(sorted((r['candidate_id'],r['direction'],r['amount'],len(r['filings'])) for r in sides),
                         [('H0CA00001','Contribution',105,2),('H0CA00001','Other',40,1),
                          ('H0CA00002','Contribution / Other',7,1)])
        # Shares are of the side shown: Candidate One is all of A's Other.
        ties = downstream.relationships(sides,[('2026','A')],found)
        self.assertEqual({(t['direction'],t['candidate_id']):t['share_of_pac_direction'] for t in ties},
                         {('Contribution','H0CA00001'):1,('Other','H0CA00001'):1,('Contribution / Other','H0CA00002'):1})

    def test_snapshot_replaces_partition_without_duplicating_workbook_gifts(self):
        units = {('2026','A'):unit('A',[('B',3)]),('2026','B'):unit('B',spend=7)}
        rows = [{'cycle':'2026','committee':'B','candidate_id':'H0KY06104','candidate':'Barr',
                 'party':'R','direction':direction,'amount':Decimal(value)}
                for direction,value in [('Support','2'),('Contribution / Other','1')]]
        merged,found = downstream.merge_activity(rows,[('2026','A')],units)
        self.assertEqual(sum(r['amount'] for r in merged),7)
        self.assertEqual(len(merged),1)
        self.assertEqual(len(downstream.relationships(merged,[('2026','A')],found)),1)
        self.assertEqual(len(found['measurement_comparisons']),2)
        self.assertEqual(found['measurement_comparisons'][0]['workbook_amount'],1)

    def test_missing_amount_is_not_zero_and_false_string_is_not_memo(self):
        for value in (None, '', 'NaN', 'Infinity', '1.001'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                downstream.amount(value)
        for value in ('false', '0', 0, False):
            self.assertFalse(downstream.memo({'memoed_subtotal':value}))
        self.assertTrue(downstream.memo({'memoed_subtotal':'true'}))
        self.assertFalse(evidence_geo.is_memo({'memoed_subtotal':'false'}))
        broken=unit('A',spend=7)
        broken['expenditures'][0]['expenditure_amount']=None
        with self.assertRaises(ValueError):
            evidence_geo.snapshot_spent(broken,{},'2026')

    def test_equal_totals_with_different_candidates_are_still_disclosed(self):
        prior=[{'cycle':'2026','committee':'A','candidate_id':'OTHER','candidate':'Other',
                'direction':'Support','amount':Decimal(7)}]
        _,found=downstream.merge_activity(prior,[('2026','A')],{('2026','A'):unit('A',spend=7)})
        self.assertEqual(len(found['measurement_comparisons']),1)

    def test_concentration_uses_net_amounts_without_clamping_refunds(self):
        rows=[{'cycle':'2026','committee':'A','candidate_id':candidate,'candidate':candidate,
               'direction':'Support','amount':Decimal(value)}
              for candidate,value in [('X',100),('X',-20),('Y',20)]]
        found=downstream.network([('2026','A')],{('2026','A'):unit('A')})
        ties=downstream.relationships(rows,[('2026','A')],found)
        self.assertEqual([r['share_of_pac_direction'] for r in ties],[.8,.2])
        rows[-1]['amount']=Decimal(-20)
        ties=downstream.relationships(rows,[('2026','A')],found)
        self.assertTrue(all(r['share_of_pac_direction'] is None for r in ties))
        self.assertEqual(ties[-1]['amount'],-20)

    def test_consolidated_outflow_does_not_count_internal_transfers_twice(self):
        units = {('2026','A'):unit('A',[('B',3)]),('2026','B'):unit('B',spend=7)}
        with patch.object(evidence_geo.district_geo,'district_for_candidate',return_value='KY-06'), \
             patch.object(evidence_geo.district_geo,'district_exists',return_value=True):
            buckets,missing,total = evidence_geo.network_spent(downstream.network([('2026','A')],units),{},'2026')
        self.assertEqual(total,7)
        self.assertEqual(buckets['candidates'].total(),7)
        self.assertEqual(buckets['transfers'].total(),0)
        self.assertEqual(missing.total(),0)

    def test_newest_coverage_wins_once_and_file_change_invalidates_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name,coverage,spend in [('old','2026-03-31',2),('new','2026-06-30',7)]:
                folder=root/name; folder.mkdir()
                data=unit('A',spend=spend); data['totals']['coverage_end_date']=coverage
                (folder/'snapshots.json').write_text(json.dumps([data]))
            found=downstream.network([('2026','A')],downstream.inventory(root))
            self.assertEqual(downstream.activity(found)[0]['amount'],7)
            data['expenditures'][0]['expenditure_amount']=11
            (root/'new/snapshots.json').write_text(json.dumps([data]))
            found=downstream.network([('2026','A')],downstream.inventory(root))
            self.assertEqual(downstream.activity(found)[0]['amount'],11)

    def test_filed_senate_office_overrides_a_retained_house_candidate_id(self):
        saved=unit('A',spend=7)
        saved['expenditures'][0].update(candidate_office='S',candidate_office_state='KY',candidate_office_district='00')
        with patch.object(evidence_geo.district_geo,'district_for_candidate',return_value='KY-06'), \
             patch.object(evidence_geo,'state_exists',return_value=True):
            buckets,missing,total=evidence_geo.snapshot_spent(saved,{},'2026')
        self.assertEqual(set(buckets['candidates'].districts),{'KY-SEN'})
        self.assertEqual(buckets['candidates'].districts['KY-SEN']['amount'],7)
        self.assertEqual(missing.total(),0)

    def test_explicit_candidate_gift_is_a_terminal_tie_not_a_missing_pac(self):
        saved=unit('A',[('PCC',5)])
        saved['disbursements'][0].update(candidate_id='H0KY06104',candidate_name='BARR',line_number='23')
        prior=[{'cycle':'2026','committee':'A','candidate_id':'H0KY06104','candidate':'BARR',
                'direction':'Contribution / Other','amount':Decimal(3),'party':'R'}]
        merged,found=downstream.merge_activity(prior,[('2026','A')],{('2026','A'):saved})
        self.assertEqual(found['missing'],[])
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['amount'],5)

if __name__ == '__main__':
    unittest.main()
