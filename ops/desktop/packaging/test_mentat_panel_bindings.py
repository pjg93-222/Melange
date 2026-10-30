"""Synthetic split validation plus actual sealed-program function isolation."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

from mentat_module_data import canonical_panel, panel_documents, bind_panel_inputs


def fixture():
    documents={}
    for sector,count,sha in [('credit_unions',16,'a'*64),('telecom',8,'b'*64)]:
        block=lambda scale:{'House':{'D':10*scale,'R':20*scale,'Other':0,'Unknown':0},
            'Senate':{'D':30*scale,'R':40*scale,'Other':0,'Unknown':0},'sum_cents':100*scale,'unresolved_office_pool':0}
        doc={'schema':'panel-cohort-party-split-v1','sector':sector,'target':2026,'count':count,
            'cohort_ids_sha256':sha,'basis':'Synthetic cent-accounting fixture','cycles':{'2024':block(2)},
            'observed':{**block(1),'through':'2026-09-26'},'sources':{'current_ledger_sha256':'c'*64,
            'history_ledger_sha256':'d'*64,'ids_sha256':sha},'note':'Synthetic fixture, not real data'}
        if sector=='telecom':doc['silent_committees']=['C00000001']
        documents[sector]={'sourceSha256':'1'*64,'documentSha256':hashlib.sha256(canonical_panel(doc)).hexdigest(),
                           'projectionProofSha256':'2'*64,'document':doc}
    return {'schemaVersion':1,'documents':documents}


class PanelValidation(unittest.TestCase):
    def test_exact_two_documents_are_canonical_immutable_copies(self):
        original=fixture();bound=panel_documents(original)
        original['documents']['credit_unions']['document']['count']=0
        self.assertEqual(json.loads(bound['credit_unions'])['count'],16)

    def test_hash_missing_unknown_count_nonfinite_and_cent_sum_fail_closed(self):
        for number,mutation in enumerate([lambda v:v['documents'].pop('telecom'),lambda v:v.update(unknown=True),
                lambda v:v['documents']['credit_unions'].update(documentSha256='0'*64),
                lambda v:v['documents']['credit_unions']['document'].update(count=True),
                lambda v:v['documents']['credit_unions']['document']['observed'].update(sum_cents=1),
                lambda v:v['documents']['telecom']['document'].update(silent_committees=[{}])]):
            value=fixture();mutation(value)
            if number!=2 and set(value.get('documents',{}))=={'credit_unions','telecom'}:
                for row in value['documents'].values():row['documentSha256']=hashlib.sha256(canonical_panel(row['document'])).hexdigest()
            with self.assertRaises(ValueError):panel_documents(value)


@unittest.skipUnless(os.environ.get('MODULE_DATA_MENTAT_SOURCE'),'Actual reviewed Mentat program source required')
class ActualPanelIsolation(unittest.TestCase):
    def giving(self):
        source=Path(os.environ['MODULE_DATA_MENTAT_SOURCE'])/'mentat/app/giving_forecast.py'
        tree=ast.parse(source.read_bytes())
        names={'_panel_block','_cohort_split'}
        nodes=[node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name in names]
        self.assertEqual(len(nodes),2)
        module=types.ModuleType('actual_isolated_panel_fixture')
        module.__dict__.update(json=json,CHAMBERS=('House','Senate'),SPLIT_SCHEMA='panel-cohort-party-split-v1',
            PANEL_COHORT={'credit_unions':'credit_unions','telecom':'telecom'},PANEL_NAMES={},_period=lambda cycle:str(cycle))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source),'exec'),module.__dict__)
        return module

    def pac(self):
        sectors=[]
        for sector,count,sha in [('credit_unions',16,'a'*64),('telecom',8,'b'*64)]:
            origin={'target':2026,'product':'ORIGIN','status':'ready','trace':{'annual':{2023:120}}}
            now={'target':2026,'product':'NOWCAST','status':'ready','cut':'2026-09-26','observed_cents':100,
                 'prediction_cents':250,'trace':{'history':[{'cycle':2024,'total_cents':200,'observed_cents':80}]}}
            sectors.append({'sector':sector,'cohort':{'count':count,'ids_sha256':sha},'current':now,'forecasts':[origin,now]})
        return types.SimpleNamespace(catalog=lambda:{'sectors':copy.deepcopy(sectors),'bundle_sha256':'e'*64})

    def test_actual_credit_union_and_telecom_pac_party_functions_use_only_bound_inputs(self):
        giving=self.giving();pac=self.pac()
        poison=types.SimpleNamespace(catalog=lambda:(_ for _ in ()).throw(AssertionError('Canonical module leaked')))
        with patch.dict(sys.modules,{'pac_giving_forecast':poison}):
            bind_panel_inputs(giving,pac,panel_documents(fixture()))
            for sector in ('credit_unions','telecom'):
                result,reason=giving._panel_block(sector,2026)
                self.assertIsNone(reason);self.assertIsNone(result['split_reason'])
                self.assertEqual(result['cycles']['2024']['to_house_senate'],2.)
                self.assertEqual(result['cycles']['2024']['House']['D'],.2)
                self.assertEqual(result['observed'][0]['Senate']['R'],.4)
                self.assertIs(sys.modules['pac_giving_forecast'],poison)

    def test_actual_pac_cohort_or_cent_mismatch_refuses_the_binding(self):
        value=fixture();value['documents']['credit_unions']['document']['count']=15
        row=value['documents']['credit_unions'];row['documentSha256']=hashlib.sha256(canonical_panel(row['document'])).hexdigest()
        with self.assertRaises(ValueError):bind_panel_inputs(self.giving(),self.pac(),panel_documents(value))


if __name__=='__main__':unittest.main()
