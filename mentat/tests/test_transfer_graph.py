import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fec_transfer_graph import allocate,reachable,transfer_index


class Transfers(unittest.TestCase):
    def test_multihop_conserves_funding_and_keeps_opposition_separate(self):
        edges=[{'source':'A','destination':'B','amount':100},{'source':'A','destination':'C','amount':100}]
        activity=[{'source':'B','candidate':'H1','direction':'Support','amount':90},
                  {'source':'B','candidate':'H2','direction':'Oppose','amount':10}]
        rows,coverage=allocate({'A':1000},edges,activity)
        values={(r['candidate_id'],r['direction']):r['estimated_amount'] for r in rows}
        self.assertEqual(values,{('H1','Support'):450,('H2','Oppose'):50})
        self.assertEqual(coverage[0]['unresolved'],500)
        self.assertEqual(coverage[0]['estimated_candidate_activity']+coverage[0]['unresolved'],1000)

    def test_cycles_and_depth_limits_become_unresolved(self):
        cycle=[{'source':'A','destination':'B','amount':100},{'source':'B','destination':'A','amount':100}]
        rows,coverage=allocate({'A':50},cycle,[])
        self.assertEqual(rows,[])
        self.assertEqual(coverage[0]['unresolved_reasons'],{'cycle':50})
        chain=[{'source':str(i),'destination':str(i+1),'amount':1} for i in range(5)]
        _,coverage=allocate({'0':50},chain,[],max_depth=2)
        self.assertEqual(coverage[0]['unresolved_reasons'],{'depth_limit':50})

    def test_candidate_transfer_is_not_counted_twice(self):
        edges=[{'source':'A','destination':'CMTE','amount':100}]
        activity=[{'source':'A','candidate':'H1','direction':'Contribution / Other','amount':100}]
        rows,coverage=allocate({'A':25},edges,activity,stop_nodes={'CMTE'})
        self.assertEqual(rows[0]['estimated_amount'],25)
        self.assertEqual(coverage[0]['unresolved'],0)

    def test_negative_funding_does_not_become_positive_estimate(self):
        rows,coverage=allocate({'A':-15},[],[])
        self.assertEqual(rows,[])
        self.assertEqual(coverage[0]['negative_net_funding_excluded'],-15)

    def test_oth_direction_amendments_memo_and_dates(self):
        def row(source='C00000001',dest='C00000002',amount='100',kind='24K',sub='1',transaction='T1',file='1',memo='',date='01022024'):
            fields=['']*21
            for index,value in {0:source,1:'N',2:'Q1',5:kind,13:date,14:amount,15:dest,16:transaction,17:file,18:memo,20:sub}.items():fields[index]=value
            return '|'.join(fields)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'itoth.txt'
            path.write_text('\n'.join([row(),row(amount='150',sub='2',file='2'),
                row(amount='150',sub='2',file='2'),row(kind='18K',transaction='IN',sub='3'),
                row(transaction='M',memo='X',sub='4'),row(transaction='IE',kind='24A',sub='5'),
                row(transaction='T1',date='01022023',sub='6')]),encoding='utf-8')
            index=transfer_index(path,2024)
            self.assertEqual(len(index['edges']),1)
            self.assertEqual(index['edges'][0]['amount'],250)
            self.assertEqual(index['edges'][0]['first_date'],'2023-01-02')
            self.assertEqual(index['counts']['memo_rows'],1)
            self.assertEqual(transfer_index(path,2024),index)


if __name__=='__main__':unittest.main()
