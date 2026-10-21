import ast
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from lobbying import industry_tiers as IT
from engine import primacy_factors as PF

def test_cu_board_uses_full_authority_instead_of_stale_desk_or_generalized_scores(monkeypatch):
    # D-157 F-20: tier and rank are the active rank_honors generation's (the board tier_util seated when it was built).
    monkeypatch.setattr(IT,'active_board',lambda root,mode:({'A':2,'B':1},{'A':14,'B':1},'a'*24))
    monkeypatch.setattr(IT.tier_util,'legislative_press_tiers',lambda *a,**k:pytest.fail('CU board must not recompute tiers'))
    rows=[{'name':'A','bioguide':'A1','chamber':'House','tier':1,'tierrank':1},
          {'name':'B','bioguide':'B1','chamber':'Senate','tier':2,'tierrank':14}]
    factors={'members':{'A':{'factor_ranked':.5,'mix':{'cu_primary':1}},
                        'B':{'factor_ranked':.8,'mix':{'cu_primary':2}}},
             '_constants':{'roster_baseline':.6}}
    result=IT._canonical_cu_board(rows,['A','B'],factors,{})
    assert [(r['member'],r['tier'],r['tierrank'],r['score']) for r in result['rows']]==[
        ('B',1,1,.8),('A',2,14,.5)]
    assert result['receipts']['authority']==IT.FACTOR_PATH
    assert result['receipts']['honors_generation']=='a'*24      # the generation the crowns were read from

def test_cu_board_fails_closed_without_an_active_honors_generation(tmp_path,monkeypatch):
    monkeypatch.setattr(IT,'MB_ROOT',str(tmp_path))
    monkeypatch.setenv('HONORS_MODE','active')
    with pytest.raises(ValueError,match='no usable active rank_honors generation'):
        IT._canonical_cu_board([],['A'],{'members':{'A':{}}},{})

@pytest.mark.parametrize('value',[float('nan'),float('inf'),-1,0])
def test_adjudicated_weight_must_be_finite_positive(tmp_path,value):
    import json
    path=tmp_path/'credits.ndjson'
    path.write_text(json.dumps({'event_id':'E','member':'A','role_weight':value,'beneficiary_class':'cu_primary'})+'\n')
    with pytest.raises(ValueError,match='positive role_weight'):PF.load_adjudicated_credits(path)

def test_duplicate_acts_cannot_double_count():
    bill={'bill':'H.R.1','congress':'119','role':'sponsor'}
    with pytest.raises(ValueError,match='duplicate primacy act'):
        PF.compute({'members':[{'name':'A','bills':[bill,bill]}]}, {'H.R.1|119':{'class':'cu_primary'}})

def test_chain_publishes_rank_honors_before_the_boards_that_read_its_crown_set():
    # D-157 F-20: champions_v2 and industry_tiers fail closed without an active generation, so the chain must publish one first.
    tree=ast.parse((Path(__file__).resolve().parents[2]/'run_pipeline.py').read_text(encoding='utf-8'))
    chain=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(getattr(t,'id',None)=='CHAIN' for t in n.targets))
    steps=[(e.elts[0].value,[a.value for a in e.elts[1].elts if isinstance(a,ast.Constant)] if len(e.elts)>1 and isinstance(e.elts[1],ast.List) else [])
           for e in chain.elts if isinstance(e,ast.Tuple) and e.elts and isinstance(e.elts[0],ast.Constant)]
    names=[name for name,_ in steps]
    publish=[i for i,(name,argv) in enumerate(steps) if name=='build_rank_honors.py' and '--publish' in argv]
    assert len(publish)==1
    for later in ('champions_v2.py','industry_tiers.py'):
        assert names.count(later)==1 and publish[0]<names.index(later),later
