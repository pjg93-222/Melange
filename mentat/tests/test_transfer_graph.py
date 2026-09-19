import json
from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import sqlite3
from contextlib import closing
import subprocess
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fec_transfer_graph import allocate,reachable,transfer_index


def transfer_row(source='C00000001',dest='C00000002',amount='100',kind='24K',sub='1',transaction='T1',file='1',memo='',date='01022024',amend='N'):
    fields=['']*21
    for index,value in {0:source,1:amend,2:'Q1',5:kind,13:date,14:amount,15:dest,16:transaction,17:file,18:memo,20:sub}.items():fields[index]=value
    return '|'.join(fields)


def header(number,original=None):
    from fec_filing_headers import parse_header
    fields=['']*15
    fields[0]='F3XA' if original else 'F3XN';fields[1]='C00000001';fields[9]='Q1'
    fields[13]='20240101';fields[14]='20240331'
    prefix=('HDR,FEC,8.5,Fixture,1,'+str(original or '')+',1\n'+','.join(fields)+'\n').encode()
    return dict(header=parse_header(prefix,number),prefix_hex=prefix.hex(),
                prefix_sha256=hashlib.sha256(prefix).hexdigest(),url=f'https://docquery.fec.gov/dcdev/posted/{number}.fec')


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
        record=dict(file_num=10,transaction_id='T1',date='2024-01-01',cents=10000,type='24K')
        edges=[{'source':'A','destination':'CMTE','amount':100,'records':[record]}]
        activity=[{'source':'A','candidate':'H1','direction':'Contribution / Other','amount':100,
                   'transfer_records':[dict(record,destination='CMTE')]}]
        rows,coverage=allocate({'A':25},edges,activity,stop_nodes={'CMTE'},candidate_links={'CMTE':{'H1'}})
        self.assertEqual(rows[0]['estimated_amount'],25)
        self.assertEqual(coverage[0]['unresolved'],0)

    def test_unmatched_candidate_transfer_retains_its_share(self):
        edges=[dict(source='A',destination='CMTE',amount=90)]
        activity=[dict(source='A',candidate='OTHER',direction='Oppose',amount=10)]
        rows,coverage=allocate({'A':100},edges,activity,stop_nodes={'CMTE'})
        self.assertEqual(rows[0]['estimated_amount'],10)
        self.assertEqual(coverage[0]['unresolved_reasons'],{'unmatched_candidate_transfer':90})

    def test_candidate_duplicate_match_preserves_signed_corrections(self):
        paid=dict(file_num=10,transaction_id='T1',date='2024-01-01',cents=10000,type='24K')
        refund=dict(paid,transaction_id='REFUND',cents=-9000)
        activity=[dict(source='A',candidate='H1',direction='Contribution / Other',amount=10,
            transfer_records=[dict(r,destination='CMTE') for r in (paid,refund)])]
        edges=[dict(source='A',destination='CMTE',amount=10,records=[paid,refund])]
        rows,coverage=allocate({'A':25},edges,activity,stop_nodes={'CMTE'},candidate_links={'CMTE':{'H1'}})
        self.assertEqual(rows[0]['estimated_amount'],25)
        self.assertEqual(coverage[0]['unresolved'],0)
        edges[0]['records']=[paid,dict(refund,transaction_id='UNMATCHED')]
        rows,coverage=allocate({'A':25},edges,activity,stop_nodes={'CMTE'},candidate_links={'CMTE':{'H1'}})
        self.assertEqual(rows,[])
        self.assertEqual(coverage[0]['unresolved'],25)

    def test_amount_and_candidate_match_do_not_prove_duplicate(self):
        record=dict(file_num=10,transaction_id='T1',date='2024-01-01',cents=10000,type='24K')
        for change in ({'transaction_id':'DIFFERENT'},{'file_num':11},{'date':'2024-01-02'},{'type':'24Z'}):
            with self.subTest(change=change):
                edges=[dict(source='A',destination='CMTE',amount=100,records=[record])]
                activity=[dict(source='A',candidate='H1',direction='Contribution / Other',amount=100,
                    transfer_records=[dict(record,destination='CMTE',**change)])]
                rows,coverage=allocate({'A':25},edges,activity,stop_nodes={'CMTE'},candidate_links={'CMTE':{'H1'}})
                self.assertEqual(rows,[])
                self.assertEqual(coverage[0]['unresolved'],25)

    def test_unresolved_descendant_does_not_renormalize_other_activity(self):
        rows,coverage=allocate({'A':100},[dict(source='A',destination='B',amount=90)],
            [dict(source='A',candidate='OTHER',direction='Oppose',amount=10)],unresolved_nodes={'B'})
        self.assertEqual(rows[0]['estimated_amount'],10)
        self.assertEqual(coverage[0]['unresolved_reasons'],{'unresolved_transfer_records':90})

    def test_negative_funding_does_not_become_positive_estimate(self):
        rows,coverage=allocate({'A':-15},[],[])
        self.assertEqual(rows,[])
        self.assertEqual(coverage[0]['negative_net_funding_excluded'],-15)

    def test_oth_direction_amendments_memo_and_dates(self):
        row=transfer_row
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'itoth.txt'
            path.write_text('\n'.join([row(),row(amount='150',sub='2',file='2',amend='A'),
                row(amount='150',sub='2',file='2',amend='A'),row(kind='18K',transaction='IN',sub='3'),
                row(transaction='M',memo='X',sub='4'),row(transaction='IE',kind='24A',sub='5'),
                row(transaction='T1',date='01022023',sub='6',file='3')]),encoding='utf-8')
            evidence=[header(1),header(2,1),header(3)]
            index=transfer_index(path,2024,evidence)
            self.assertEqual(len(index['edges']),1)
            self.assertEqual(index['edges'][0]['amount'],250)
            self.assertEqual(index['edges'][0]['first_date'],'2023-01-02')
            self.assertEqual(index['counts']['memo_rows'],1)
            self.assertEqual(transfer_index(path,2024,evidence),index)
            with closing(sqlite3.connect(index['ledger_path'])) as connection:
                self.assertEqual(connection.execute('SELECT COUNT(*) FROM records').fetchone()[0],5)
                self.assertEqual(index['counts']['source_rows'],7)

    def test_reclassification_and_new_year_amendment_require_filing_evidence(self):
        for change in ({'kind':'24Z'},{'date':'01012024'},{'dest':''},{'memo':'X'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'itoth.txt'
                original=transfer_row(date='12312023')
                amended=transfer_row(**dict(date='12312023',sub='2',file='2',amend='A',**change)) if 'date' not in change else transfer_row(date=change['date'],sub='2',file='2',amend='A')
                path.write_text(original+'\n'+amended,encoding='utf-8')
                unknown=transfer_index(path,2024)
                self.assertEqual(unknown['edges'],[])
                self.assertEqual(unknown['unresolved_sources'],['C00000001'])
                resolved=transfer_index(path,2024,[header(1),header(2,1)])
                if 'date' in change:
                    self.assertEqual(resolved['edges'][0]['amount'],100)
                    self.assertEqual(resolved['edges'][0]['first_date'],'2024-01-01')
                else:self.assertEqual(resolved['edges'],[])

    def test_invalid_amount_or_date_correction_cannot_revive_original(self):
        for change in ({'amount':'NaN'},{'amount':'0.001'},{'date':'BAD'}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'itoth.txt'
                path.write_text(transfer_row()+'\n'+transfer_row(sub='2',file='2',amend='A',**change),encoding='utf-8')
                value=transfer_index(path,2024,[header(1),header(2,1)])
                self.assertEqual(value['edges'],[])
                self.assertEqual(value['unresolved_sources'],['C00000001'])

    def test_corrupt_header_or_cached_ledger_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'itoth.txt';path.write_text(transfer_row(),encoding='utf-8')
            bad=header(1);bad['header']['original_file_num']=2
            with self.assertRaisesRegex(ValueError,'evidence'):transfer_index(path,2024,[bad])
            value=transfer_index(path,2024)
            with Path(value['ledger_path']).open('ab') as stream:stream.write(b'altered')
            with self.assertRaisesRegex(ValueError,'checksum'):transfer_index(path,2024)

    @unittest.skipUnless(Path('C:/Program Files/R/R-4.6.0/bin/Rscript.exe').is_file(),'R integration requires installed R')
    def test_r_retained_records_match_python_transfer_evidence_end_to_end(self):
        from enrich_downstream import enrich
        project=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);payload_path=root/'r-evidence.json'
            result=subprocess.run(['C:/Program Files/R/R-4.6.0/bin/Rscript.exe',
                str(project/'tests/test_transfer_evidence.R'),str(payload_path)],
                capture_output=True,text=True,timeout=60)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            path=root/'itoth.txt';path.write_text(transfer_row(date='12312023'),encoding='utf-8')
            index=transfer_index(path,2024)
            payload=json.loads(payload_path.read_text())
            payload.update(metadata=dict(industry='Fixture',transfer_coverage=[dict(cycle=2024,status='indexed',counts=index['counts'])]),
                cycles=[dict(cycle=2024)],committee_map=[],transfer_edges=index['edges'],
                raw_rows=[dict(cycle=2024,committee_id='C00000001',amount=25,include_in_analysis='Yes',receipt_role='contribution')],
                candidate_committee_links=[dict(cycle=2024,committee_id='C00000002',candidate_id='H00000001',designation='P')])
            enriched=enrich(payload,root)
            self.assertEqual(enriched['allocation_estimates'][0]['estimated_amount'],25)
            self.assertEqual(enriched['allocation_coverage'][0]['unresolved'],0)
            self.assertTrue(all(r['passed'] for r in enriched['quality_checks']))


if __name__=='__main__':unittest.main()
