"""Synthetic aggregate contracts; never opens selected models or user reports.

Set MODULE_DATA_MENTAT_SOURCE to a reviewed, program-only runtime source root
for the cross-repository actual-reader/schema acceptance cases. Portable XLSX
security tests do not need a Mentat installation.
"""
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from module_data_snapshot import validate_snapshot, load_source
from module_data_test_helpers import Fixture, encoded
from mentat_module_data import INDUSTRIES, MODEL_ID, workbook_metadata,configure_readers

SOURCE=os.environ.get('MODULE_DATA_MENTAT_SOURCE')

def workbook(extra=None, sheet='Spending Overview'):
    stream=io.BytesIO()
    entries={
        '[Content_Types].xml':'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/></Types>',
        'xl/workbook.xml':'<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="'+sheet+'" sheetId="1" r:id="rId1"/></sheets></workbook>',
        'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>',
        'xl/worksheets/sheet1.xml':'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData/></worksheet>'}
    entries.update(extra or {})
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for key,value in entries.items():z.writestr(key,value)
    return stream.getvalue()

def synthetic(node,document):
    """Build neutral zero/empty schema values, never copying published models."""
    if '$ref' in node:return synthetic(document['$defs'][node['$ref'].split('/')[-1]],document)
    if 'const' in node:return node['const']
    if 'enum' in node:
        return next((v for v in node['enum'] if v in ('unavailable','previous_cycle')),node['enum'][0])
    kind=node.get('type','object')
    if isinstance(kind,list):
        if 'null' in kind:return None
        kind=kind[0]
    if kind=='object':
        result={k:synthetic(node['properties'][k],document) for k in node.get('required',[])}
        if node.get('minProperties',0)>len(result):
            key='2022' if node.get('propertyNames',{}).get('pattern')==r'^\d{4}$' else 'fixture'
            result[key]=synthetic(node.get('additionalProperties',{}),document)
        return result
    if kind=='array':return [synthetic(node['items'],document) for _ in range(node.get('minItems',0))]
    if kind=='boolean':return False
    if kind=='null':return None
    if kind in ('integer','number'):return node.get('exclusiveMinimum',node.get('minimum',0))+ (1 if 'exclusiveMinimum' in node else 0)
    pattern=node.get('pattern','')
    if '64' in pattern:return '0'*64
    if 'T' in pattern:return '2024-01-01T00:00:00Z'
    if '\\d{4}' in pattern:return '2024-01-01'
    return 'fixture'

def forecast_fixture(directory,source):
    f=Fixture(directory,'mentat.aggregate-forecast-core.v1',source)
    contracts=Path(source)/'mentat/forecast/contracts'
    models_schema=json.loads((contracts/'giving-models-v2.schema.json').read_bytes())
    anchors_schema=json.loads((contracts/'giving-anchors-v1.schema.json').read_bytes())
    giving=synthetic(models_schema,models_schema)
    anchor_schema=models_schema['properties']['anchor_contract']['properties']
    for section,field,ids in (('pac','measures',('pac_to_candidates','general_giving')),
        ('share','bases',('employee_candidate','pac_candidate')),('lobbying','series',('income_total','expenses_total'))):
        item_schema=anchor_schema[section]['properties'][field]['items']
        giving['anchor_contract'][section][field]=[{**synthetic(item_schema,models_schema),'id':ident} for ident in ids]
    option=anchor_schema['share']['properties']['anchor_options']['items']
    giving['anchor_contract']['share']['anchor_options']=[{**synthetic(option,models_schema),'id':ident,'cycle_offset':offset,'chained':chained}
        for ident,offset,chained in (('previous_cycle',2,True),('same_phase',4,False))]
    for model in giving['share_models'].values():model['terms']=['Intercept','Forecast']
    anchors=synthetic(anchors_schema,anchors_schema)
    # Every test value is fabricated; there are no selected data/model reads.
    anchors['cpi']['multipliers']={'2022':1}
    template=next(iter(anchors['industries'].values()))
    anchors['industries']={}
    inputs=[]
    for industry,(role,name) in INDUSTRIES.items():
        f.write(role,workbook())
        item=copy.deepcopy(template);item['id']=industry
        item['coverage'].update(current_cycle=2024,coverage_end='2024-01-01',rule_coverage_end='2024-01-01',collection_date='2024-01-01')
        item['mentat'].update(workbook=name,workbook_sha256=f.spec(role)['sha256'])
        anchors['industries'][industry]=item
        inputs.append({'role':'workbook:'+industry,'path':'/never-read-original/'+name,'sha256':f.spec(role)['sha256'],'bytes':f.spec(role)['bytes']})
    f.write('giving-model',giving)
    # These constants are source metadata for fixed aggregate cohort contracts,
    # not rows or inferred likelihoods. No calculate/catalog function is called.
    import sys
    old_path=list(sys.path);old=sys.modules.pop('runtime_paths',None)
    try:
        sys.path.insert(0,str(Path(source)/'mentat/app'))
        reader=load_source(Path(source)/'mentat/app/pac_giving_forecast.py')
    finally:
        sys.path[:]=old_path;sys.modules.pop('runtime_paths',None)
        if old is not None:sys.modules['runtime_paths']=old
    sectors=[]
    for sector,(count,digest) in reader.COHORTS.items():
        cohort={'id':sector,'count':count,'ids_sha256':digest}
        frame={'sector':sector,'cohort':cohort,'target':2024,'product':'ORIGIN','issue':'2024-01-01','cut':None,
            'information_as_of':'2023-01-31','data_available_at':'2024-01-01','units':'cents','accounting_basis':reader.ACCOUNTING_BASIS,
            'history_cycles':[2018,2020,2022],'totals':{'2018':0,'2020':0,'2022':0},'historical_observed':None,'observed':None,
            'annual':None,'log_growth':None}
        sectors.append({'sector':sector,'cohort':cohort,'frames':[frame]})
    pac={'schema_version':1,'model_id':MODEL_ID,'currency':'USD','accounting_basis':reader.ACCOUNTING_BASIS,'built_at':'2024-01-01T00:00:00Z','sectors':sectors}
    f.write('pac-model',pac);f.write('anchors',anchors)
    f.write('anchor-receipt',{'schema_version':1,'snapshot':'giving-anchors-v1.json','snapshot_sha256':f.spec('anchors')['sha256'],'inputs':inputs})
    repin_models(f)
    return f

def repin_models(f):
    giving=json.loads(f.path('giving-model').read_bytes())
    f.write('selection',{'schemaVersion':1,'purpose':'mentat-forecast-selection','giving':{'sha256':f.spec('giving-model')['sha256'],'modelVersion':giving['model_version'],'modelSchemaVersion':2},'pac':{'sha256':f.spec('pac-model')['sha256'],'modelId':MODEL_ID}})
    f.write('giving-pointer',{'schema_version':1,'model_schema_version':2,'model_version':giving['model_version'],'sha256':f.spec('giving-model')['sha256'],'active':'versions/'+f.spec('giving-model')['sha256']+'/giving-models-v2.json'})
    f.write('pac-pointer',{'schema_version':1,'model_id':MODEL_ID,'sha256':f.spec('pac-model')['sha256'],'active':'pac-versions/'+f.spec('pac-model')['sha256']+'/pac-giving-v1.json'})

class WorkbookTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'fixture.xlsx'
    def test_metadata_accepts_empty_synthetic_spending_sheet_without_reading_cells(self):
        self.path.write_bytes(workbook());workbook_metadata(self.path)
    def test_active_and_external_embedded_inputs_are_forbidden(self):
        for name in ('xl/vbaProject.bin','xl/embeddings/object.bin','xl/externalLinks/externalLink1.xml','../accounts.sqlite3','xl/script.js'):
            with self.subTest(name=name):
                self.path.write_bytes(workbook({name:b'fixture'}))
                with self.assertRaises(ValueError):workbook_metadata(self.path)
    def test_missing_sheet_and_entity_expansion_are_rejected(self):
        self.path.write_bytes(workbook(sheet='Unrelated'))
        with self.assertRaises(ValueError):workbook_metadata(self.path)
    def test_external_or_escaping_workbook_relations_are_refused(self):
        for attributes in ('Target="https://outside.invalid/sheet.xml" TargetMode="External"','Target="../../outside.xml"','Target="worksheets/../worksheets/sheet1.xml"','Target="worksheets/SHEET1.xml"'):
            self.path.write_bytes(workbook({'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '+attributes+'/></Relationships>'}))
            with self.assertRaises(ValueError):workbook_metadata(self.path)
    def test_root_relative_excel_member_matches_the_actual_reader(self):
        self.path.write_bytes(workbook({'xl/_rels/workbook.xml.rels':'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="/xl/worksheets/sheet1.xml"/></Relationships>'}))
        workbook_metadata(self.path)
    def test_xml_encoding_cannot_bypass_doctype_or_active_content_checks(self):
        for name,value in (
            ('xl/workbook.xml','<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE workbook [<!ENTITY fixture "x">]><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>'.encode('utf-16')),
            ('[Content_Types].xml','<?xml version="1.0" encoding="UTF-16"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macroEnabled.main+xml"/></Types>'.encode('utf-16')),
            ('[Content_Types].xml','<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Override PartName="/xl/workbook.xml" ContentType="application/vnd.ms-excel.sheet.macro&#69;nabled.main+xml"/></Types>')):
            self.path.write_bytes(workbook({name:value}))
            with self.assertRaises(ValueError):workbook_metadata(self.path)
        self.path.write_bytes(workbook({'xl/workbook.xml':'<!DOCTYPE x [<!ENTITY x "x">]><workbook>&x;</workbook>'}))
        with self.assertRaises(ValueError):workbook_metadata(self.path)
    def test_case_collisions_and_zip_symlinks_are_rejected(self):
        self.path.write_bytes(workbook({'XL/WORKBOOK.XML':b'fixture'}))
        with self.assertRaises(ValueError):workbook_metadata(self.path)
        stream=io.BytesIO(workbook())
        with zipfile.ZipFile(stream,'a') as z:
            info=zipfile.ZipInfo('xl/link');info.create_system=3;info.external_attr=0o120777<<16;z.writestr(info,'/outside')
        self.path.write_bytes(stream.getvalue())
        with self.assertRaises(ValueError):workbook_metadata(self.path)

@unittest.skipUnless(SOURCE,'Set MODULE_DATA_MENTAT_SOURCE to a reviewed program-only source root')
class AggregateReaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.f=forecast_fixture(self.temp.name,SOURCE)
    def test_real_schema_and_pointer_reader_accept_synthetic_core_without_calculating(self):
        from mentat_module_data import load_source as original
        def guarded(path):
            module=original(path)
            if Path(path).name=='pac_giving_forecast.py':
                module.calculate=lambda *_a,**_k:self.fail('Forecast execution is outside the snapshot probe')
                module.catalog=lambda *_a,**_k:self.fail('Forecast execution is outside the snapshot probe')
            return module
        with patch('mentat_module_data.load_source',side_effect=guarded),patch.dict(os.environ,{'MENTAT_PAC_GIVING_POINTER':'/outside/accounts.sqlite3'}):
            self.assertEqual(validate_snapshot(self.f.request)['coverage'],{'completeKind':True,'fullApplication':False})
    def test_scoped_readers_use_compiled_models_anchors_and_workbooks(self):
        bound=configure_readers(self.f.request)
        self.assertEqual(bound['giving'].models()['sha256'],self.f.spec('giving-model')['sha256'])
        self.assertEqual(bound['giving'].anchors()['kind'],'giving-anchors')
        for role,name in INDUSTRIES.values():self.assertEqual(bound['workbook_path'](name),self.f.path(role))
        with self.assertRaises(ValueError):bound['workbook_path']('../../accounts.sqlite3')
        self.assertFalse(bound['coverage']['fullApplication'])
    def test_scoping_keeps_owner_waiver_and_panel_path_readers_original(self):
        bound=configure_readers(self.f.request);giving=bound['giving']
        self.assertIs(giving.Path,Path);self.assertIs(giving.os,os)
        self.assertIsInstance(giving.WAIVER_FILE,Path)
        self.assertIsInstance(giving.SPLIT_FILE,Path)
        sentinel=Path(self.temp.name)/'owner-waivers.json';sentinel.write_bytes(b'{"waivers":[{"fixture":"owner-state"}]}')
        info=sentinel.stat()
        self.assertEqual(giving._load_waivers(str(sentinel),info.st_mtime_ns,info.st_size),({'fixture':'owner-state'},))
        self.assertEqual(sentinel.read_bytes(),b'{"waivers":[{"fixture":"owner-state"}]}')
    def test_pointer_traversal_and_schema_invalid_bundle_fail_after_manifest_rebinding(self):
        pp=json.loads(self.f.path('pac-pointer').read_bytes());pp['active']='../../accounts.sqlite3';self.f.write('pac-pointer',pp)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
        repin_models(self.f)
        model=json.loads(self.f.path('giving-model').read_bytes());model['schema_version']=99;self.f.write('giving-model',model);repin_models(self.f)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_workbook_freshness_and_anchor_receipt_are_mandatory(self):
        self.f.write('workbook-telecom',workbook({'fixture.txt':'changed'}))
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
        anchors=json.loads(self.f.path('anchors').read_bytes());anchors['industries']['telecom']['mentat']['workbook_sha256']=self.f.spec('workbook-telecom')['sha256'];self.f.write('anchors',anchors)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)
    def test_duplicate_frames_and_invalid_fixed_cohort_reject_without_prediction(self):
        pac=json.loads(self.f.path('pac-model').read_bytes());pac['sectors'][0]['frames']*=2;self.f.write('pac-model',pac);repin_models(self.f)
        with self.assertRaises(ValueError):validate_snapshot(self.f.request)

if __name__=='__main__':unittest.main()
