"""Read-only aggregate forecast schemas and explicitly bound report workbooks.

Never calls forecast calculation/catalog functions, builds anchors, updates a
pointer, opens a database, or reads the user's original reports or console.
"""
from contextlib import contextmanager
from functools import lru_cache
import os
from pathlib import PurePosixPath
import re
import stat
import sys
import types
import zipfile
from datetime import date
from xml.etree import ElementTree
from module_data_snapshot import MiB, ReadAliases, Snapshot, digest, load_source, require, exact

INDUSTRIES={
 'commercial_banks':('workbook-commercial-banks','Banking Industry Spending Overview.xlsx'),
 'credit_unions':('workbook-credit-unions','Credit Union Industry Spending Overview.xlsx'),
 'property_casualty':('workbook-property-casualty','Property & Casualty Insurance Industry Spending Overview.xlsx'),
 'telecom':('workbook-telecom','Telecom Industry Spending Overview.xlsx'),
 'community_banks':('workbook-community-banks','Community Banks Industry Spending Overview.xlsx')}
MODEL_ID='pac-r12-origin-half-r8-nowcast-v1'

def program_reader(snapshot,name):
    """Load only native source programs, without their data-directory imports."""
    app_path=snapshot.source_file('mentat/app/'+name+'.py').parent
    snapshot.source_file('mentat/app/runtime_paths.py')
    old_path=list(sys.path);old_module=sys.modules.pop('runtime_paths',None)
    try:
        sys.path.insert(0,str(app_path));return load_source(app_path/(name+'.py'))
    finally:
        sys.path[:]=old_path
        sys.modules.pop('runtime_paths',None)
        if old_module is not None:sys.modules['runtime_paths']=old_module

def bind_readers(snapshot,contract,gp,pp):
    """Return isolated actual readers; never patch global runtime/state modules."""
    aliases=ReadAliases({'models/giving-models-current.json':snapshot.files['giving-pointer'],
        'models/'+gp['active']:snapshot.files['giving-model'],
        'models/pac-giving-current.json':snapshot.files['pac-pointer'],
        'models/'+pp['active']:snapshot.files['pac-model'],
        'anchors/giving-anchors-v1.json':snapshot.files['anchors'],
        **{'reports/'+name:snapshot.files[role] for role,name in INDUSTRIES.values()}},snapshot.root)
    giving=program_reader(snapshot,'giving_forecast')
    giving.MODEL_FILE=aliases.path('models/giving-models-v1.json')
    giving.MODEL_FILE_V2=aliases.path('models/giving-models-v2.json')
    giving.ANCHOR_FILE=aliases.path('anchors/giving-anchors-v1.json')
    giving._contract=lambda:contract
    def scoped(function,**overrides):
        # Clone only immutable-input loaders. Keep original module Path/os for
        # waiver and local reference readers outside this component contract.
        function=getattr(function,'__wrapped__',function)
        result=types.FunctionType(function.__code__,{**function.__globals__,**overrides},function.__name__,function.__defaults__,function.__closure__)
        result.__kwdefaults__=function.__kwdefaults__
        return result
    giving._model_selection=scoped(giving._model_selection,Path=aliases.path,os=types.SimpleNamespace(environ={}))
    giving._load=lru_cache(maxsize=4)(scoped(giving._load,Path=aliases.path))
    giving._load_anchors=lru_cache(maxsize=4)(scoped(giving._load_anchors,Path=aliases.path))
    giving.anchor_path=lambda:aliases.path('anchors/giving-anchors-v1.json')
    def workbook_path(name):
        require(name in {name for _role,name in INDUSTRIES.values()})
        return snapshot.files[next(role for role,label in INDUSTRIES.values() if label==name)]
    def published_hash(name):return digest(workbook_path(name))
    giving._published_workbook_sha256=published_hash
    # This existing display-only aggregate helper gets its sole workbook input
    # from the compiled map. No calculations run during binding or validation.
    def industry_cycle_ratio(entry):
        path=workbook_path(entry['mentat']['workbook']);info=path.stat()
        return giving._own_cycle_ratio(giving._workbook_cycle_totals(str(path),info.st_mtime_ns,info.st_size),entry['mentat']['dataset'])
    giving._industry_cycle_ratio=industry_cycle_ratio
    # _workbook_cycle_totals accepts a concrete immutable role path, not its
    # metadata-provided original filename. It never writes the report.
    original_totals=giving._workbook_cycle_totals
    def workbook_totals(path,stamp,size):
        require(path in {str(snapshot.files[role]) for role,_name in INDUSTRIES.values()})
        return original_totals(path,stamp,size)
    giving._workbook_cycle_totals=workbook_totals
    pac=program_reader(snapshot,'pac_giving_forecast')
    pac.Path=aliases.path;pac.app_data_root=lambda:aliases.path('models')
    pac.os=types.SimpleNamespace(environ={})
    return {'giving':giving,'pac':pac,'workbook_path':workbook_path}

def frame_metadata(reader,frame,sector,cohort):
    """The installed frame input contract, without its statistical calculation."""
    require(isinstance(frame,dict) and not set(frame)-reader._FRAME_KEYS and (reader._FRAME_KEYS-{'provenance'}).issubset(frame))
    require(frame['sector']==sector and frame['cohort']==cohort)
    target,product=frame['target'],frame['product']
    information,cut=reader.schedule(target,product)
    issue=reader._date(frame['issue'],'issue');available=reader._date(frame['data_available_at'],'data_available_at')
    require(reader._date(frame['information_as_of'],'information_as_of')==information)
    require((None if frame['cut'] is None else reader._date(frame['cut'],'cut'))==cut and information<=issue<=date.today() and available<=issue)
    require(frame['units']=='cents' and frame['accounting_basis']==reader.ACCOUNTING_BASIS)
    window=[target-6,target-4,target-2];require(frame['history_cycles']==window and all(type(year) is int for year in window))
    reader._years(frame['totals'],window,'totals')
    require(frame['observed'] is None or type(frame['observed']) is int)
    if product=='ORIGIN':
        require(frame['observed'] is None and frame['historical_observed'] in (None,{}))
        reader._years(frame['annual'],(target-3,target-2),'annual',allow_missing=True)
        reader._years(frame['log_growth'],(target-3,target-2,target-1),'log_growth',money=False,allow_missing=True)
    else:
        reader._years(frame['historical_observed'],window,'historical_observed')
        require(frame['annual'] is None and frame['log_growth'] is None)

def workbook_metadata(path):
    """Validate only the fixed XLSX container's metadata, never cell/person rows."""
    with zipfile.ZipFile(path) as archive:
        entries=archive.infolist();require(0<len(entries)<=20000)
        seen=set();members=set();total=0
        for info in entries:
            name=info.filename;parts=PurePosixPath(name).parts
            require(name and not name.startswith('/') and '\\' not in name and ':' not in name and not set(name.rstrip('/').split('/'))&{'','.','..'})
            require(name.casefold() not in seen and not info.flag_bits&1 and not stat.S_ISLNK(info.external_attr>>16))
            seen.add(name.casefold());members.add(name);total+=info.file_size
            require(total<=8*1024*MiB and not name.lower().startswith(('xl/externallinks/','xl/embeddings/')) and 'vbaproject' not in name.lower())
            require(PurePosixPath(name).suffix.lower() not in ('.html','.htm','.js','.mjs','.cjs','.exe','.dll','.com','.cmd','.bat','.ps1','.py','.sh'))
        documents={}
        for name in ('[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels'):
            info=archive.getinfo(name);require(info.file_size<=2*MiB)
            raw=archive.read(name);text=raw.decode('utf-8',errors='strict')
            require('\x00' not in text and '<!DOCTYPE' not in text.upper() and '<!ENTITY' not in text.upper() and 'macroenabled' not in text.lower())
            declaration=text.lstrip('\ufeff').split('?>',1)[0] if text.lstrip('\ufeff').startswith('<?xml') else ''
            encoding=re.search(r'encoding\s*=\s*[\'"]([^\'"]+)[\'"]',declaration,re.I)
            require(encoding is None or encoding[1].lower().replace('-','') in ('utf8','ascii','usascii'))
            document=ElementTree.fromstring(text);documents[name]=document
            require(all('macroenabled' not in value.lower() for node in document.iter() for value in node.attrib.values()))
            if name=='xl/workbook.xml':
                names=[node.attrib.get('name') for node in document.iter() if node.tag.rsplit('}',1)[-1]=='sheet']
                require('Spending Overview' in names,'Compiled workbook reader requires Spending Overview')
        workbook=documents['xl/workbook.xml'];relationships=documents['xl/_rels/workbook.xml.rels']
        main='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
        package='http://schemas.openxmlformats.org/package/2006/relationships'
        office='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
        require(workbook.tag=='{'+main+'}workbook' and relationships.tag=='{'+package+'}Relationships')
        require(documents['[Content_Types].xml'].tag=='{http://schemas.openxmlformats.org/package/2006/content-types}Types')
        ids={}
        for relation in relationships:
            require(relation.tag=='{'+package+'}Relationship' and relation.get('Id') not in ids)
            target=relation.get('Target');require(isinstance(target,str) and target and not target.startswith('//') and '\\' not in target and ':' not in target)
            require(relation.get('TargetMode','Internal')=='Internal')
            target=target.lstrip('/')
            require(not set(target.split('/'))&{'','.','..'})
            # Match the actual fixed workbook reader's literal ZipFile lookup;
            # normalization must not accept a different, missing ZIP member.
            resolved=target if target.startswith('xl/') else 'xl/'+target
            require(resolved in members)
            ids[relation.get('Id')]=relation
        for sheet in workbook.iter('{'+main+'}sheet'):
            relation=ids.get(sheet.get('{'+office+'}id'))
            require(relation is not None and relation.get('Type')==office+'/worksheet')

def validate(snapshot):
    require(snapshot.kind=='mentat.aggregate-forecast-core.v1')
    selection=snapshot.json('selection');exact(selection,('schemaVersion','purpose','giving','pac'))
    exact(selection['giving'],('sha256','modelVersion','modelSchemaVersion'));exact(selection['pac'],('sha256','modelId'))
    require(selection['schemaVersion']==1 and selection['purpose']=='mentat-forecast-selection' and selection['giving']['modelSchemaVersion']==2 and selection['pac']['modelId']==MODEL_ID)
    snapshot.matches('giving-model',selection['giving']);snapshot.matches('pac-model',selection['pac'])
    giving=snapshot.json('giving-model');pac=snapshot.json('pac-model')
    gp,pp=snapshot.json('giving-pointer'),snapshot.json('pac-pointer')
    require(gp.get('schema_version')==1 and gp.get('model_schema_version')==2 and gp.get('model_version')==selection['giving']['modelVersion']==giving.get('model_version'))
    require(gp.get('active')=='versions/'+selection['giving']['sha256']+'/giving-models-v2.json');snapshot.matches('giving-model',gp)
    require(pp.get('schema_version')==1 and pp.get('model_id')==MODEL_ID and pp.get('active')=='pac-versions/'+selection['pac']['sha256']+'/pac-giving-v1.json');snapshot.matches('pac-model',pp)
    contract_relative='mentat/forecast/contracts/'
    for name in ('giving-models-v2.schema.json','giving-anchors-v1.schema.json'):snapshot.source_file(contract_relative+name)
    contract=load_source(snapshot.source_file(contract_relative+'contract.py'))
    require(contract.SCHEMAS=={'models':'giving-models-v2.schema.json','anchors':'giving-anchors-v1.schema.json'})
    require(not contract.validate_kind(giving,'models') and not contract.check_model_invariants(giving),'Installed aggregate model contract rejected this snapshot')
    anchors,receipt=snapshot.json('anchors'),snapshot.json('anchor-receipt')
    require(not contract.validate_kind(anchors,'anchors') and not contract.check_anchor_invariants(anchors),'Installed aggregate anchor contract rejected this snapshot')
    require(receipt.get('schema_version')==1 and receipt.get('snapshot')=='giving-anchors-v1.json' and receipt.get('snapshot_sha256')==snapshot.objects['anchors']['sha256'])
    require(anchors.get('schema_version')==1 and anchors.get('kind')=='giving-anchors' and set(anchors.get('industries',{}))==set(INDUSTRIES))
    inputs=receipt.get('inputs');require(isinstance(inputs,list))
    for industry,(role,name) in INDUSTRIES.items():
        item=anchors['industries'][industry];binding=item.get('mentat');require(isinstance(binding,dict) and binding.get('workbook')==name)
        require(binding.get('workbook_sha256')==snapshot.objects[role]['sha256'])
        selected=[row for row in inputs if isinstance(row,dict) and row.get('role')=='workbook:'+industry];require(len(selected)==1)
        snapshot.matches(role,selected[0])
        # Receipt paths are provenance only; input I/O uses only compiled role paths.
        workbook_metadata(snapshot.files[role])
    readers=bind_readers(snapshot,contract,gp,pp)
    actual=readers['giving'].models();require(actual.get('sha256')==snapshot.objects['giving-model']['sha256'])
    require(readers['giving'].anchors()==anchors)
    # Use installed loaders only, never catalog()/calculate()/forecast methods.
    reader=readers['pac']
    bundle,digest=reader._load_bundle();require(digest==snapshot.objects['pac-model']['sha256'] and bundle==pac)
    sectors=bundle.get('sectors');require(isinstance(sectors,list) and len(sectors)==len(reader.COHORTS) and {row.get('sector') for row in sectors if isinstance(row,dict)}==set(reader.COHORTS))
    for item in sectors:
        sector=item['sector'];reader._cohort(item.get('cohort'),sector)
        frames=item.get('frames');require(isinstance(frames,list) and frames)
        seen=set()
        for frame in frames:
            frame_metadata(reader,frame,sector,item['cohort'])
            identity=(frame.get('target'),frame.get('product'),frame.get('issue'))
            require(type(identity[0]) is int and isinstance(identity[1],str) and isinstance(identity[2],str) and identity not in seen)
            seen.add(identity)
    return readers

def configure_readers(request):
    """Native-only scoped binding, after the same immutable snapshot checks.

    Root's backend hook can substitute these two isolated modules/functions
    without altering runtime_paths, selected roots, accounts, console or waiver
    state. This remains component coverage, not full application activation.
    """
    snapshot=Snapshot(request);readers=validate(snapshot)
    for role,path in snapshot.files.items():require(digest(path)==snapshot.objects[role]['sha256'])
    return {**readers,'appId':snapshot.app,'kind':snapshot.kind,
        'coverage':{'completeKind':True,'fullApplication':False}}
