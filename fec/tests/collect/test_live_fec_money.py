from pathlib import Path
import sys
from decimal import Decimal
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from collect.refresh_fec_money import aggregate,project


def transaction(identifier,amount,**changes):
    return {'sub_id':identifier,'two_year_transaction_period':2026,'committee_id':'C00000001',
            'candidate_id':'H0AA00001','disbursement_type':'24K','disbursement_amount':amount,
            'disbursement_date':'2026-08-30','memoed_subtotal':False,**changes}


def test_refunds_and_duplicate_pages_do_not_inflate_totals():
    row=transaction('1',1000)
    totals,rejected,latest=aggregate([row,row,transaction('2',-200),transaction('3',999,memoed_subtotal=True),
          transaction('4',500,candidate_id=None)],{'H0AA00001':'A000001'},{'C00000001':'cu'},2026)
    assert totals['A000001']['cu']==Decimal(800)
    assert rejected['duplicate_sub_id']==1 and latest=='2026-08-30'


def test_conflicting_duplicate_or_wrong_cycle_fails():
    args=({'H0AA00001':'A000001'},{'C00000001':'cu'},2026)
    with pytest.raises(ValueError): aggregate([transaction('1',10),transaction('1',20)],*args)
    with pytest.raises(ValueError): aggregate([transaction('1',10,two_year_transaction_period=2024)],*args)


def test_projection_replaces_money_and_preserves_unrelated_fields():
    roster=[{'member':'A','bioguide':'A000001','cu':999,'banks':5,'finserv':5,'receipts':100000,'unrelated':'keep'}]
    data=project(roster,{'A000001':{'cu':Decimal(100),'banks':Decimal(300)}},{'A000001':Decimal(200000)},{'H0AA00001':'A000001'})
    assert data[0]['cu']==100 and data[0]['banks']==300 and data[0]['total']==400
    assert data[0]['unrelated']=='keep' and data[0]['saturation']==.2
    assert data==project(data,{'A000001':{'cu':Decimal(100),'banks':Decimal(300)}},{'A000001':Decimal(200000)},{'H0AA00001':'A000001'})


def test_capacity_share_audit_accepts_zero_funding_and_rejects_wrong_normalization():
    from audit.legacy_workbook_audit import capacity_share_errors
    rows=[{'member':'A','cu':100,'banks':100,'finserv':0,'cu_adj':50,'banks_adj':50,'finserv_adj':0},
          {'member':'B','cu':0,'banks':0,'finserv':0,'cu_adj':None,'banks_adj':None,'finserv_adj':None}]
    assert capacity_share_errors(rows)==[]
    rows[0].update(cu_adj=60,banks_adj=40)
    assert capacity_share_errors(rows)==['A cu','A banks']
