"""Fixed Melange factual-input capabilities; private writable roots stay local."""
from copy import deepcopy
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import sys
import types
from urllib.parse import urlsplit,unquote,parse_qs,urlencode

from module_application_contracts import DataIntakeBlocked,require
from module_data_snapshot import Snapshot,parse
from module_workspace_inputs import WorkspaceComponent,extract_archive
from workspace_data_contract import (DASHBOARD_KIND,DISPLAY_GRAPH_KIND,INDUSTRY_PAGES_KIND,
    STAFFER_ANALYSIS_KIND,WORKSPACE_KINDS)
from workspace_graph import VerifiedDisplayInput


def _data(value):
    if not value:raise DataIntakeBlocked('integrity')


def _json(path):
    try:return parse(Path(path).read_bytes())
    except OSError:raise DataIntakeBlocked('storage') from None
    except (ValueError,UnicodeError):raise DataIntakeBlocked('integrity') from None


def _program(source,name,relative):
    expected=(Path(source)/relative).resolve(strict=True)
    before=list(sys.path)
    try:
        sys.path.insert(0,str(source));module=importlib.import_module(name)
    finally:sys.path[:]=before
    require(Path(module.__file__).resolve(strict=True)==expected)
    return module


class MelangeComponentContent:
    def __init__(self,snapshot,data,resources=()):
        self.snapshot,self.data,self.resources=snapshot,data,tuple(resources)
        self.closed=False

    def verify(self):
        if self.closed:return False
        for resource in self.resources:
            if resource.verify() is not True:raise DataIntakeBlocked('integrity')
        return True

    def close(self):
        if self.closed:return
        self.closed=True
        for resource in self.resources:resource.close()


def prepare(snapshot,*,source,profile,program_fingerprint,is_cancelled=lambda:False):
    require(type(snapshot) is Snapshot and snapshot.app=='melange' and snapshot.kind in WORKSPACE_KINDS['melange'])
    resources=[]
    try:
        if snapshot.kind==DASHBOARD_KIND:
            data={role:snapshot.json(role) for role in snapshot.files if role!='member-profiles'}
            heavy=snapshot.json('member-profiles')
            _data(all(isinstance(value,dict) for value in data.values()) and isinstance(heavy,dict)
                  and isinstance(data['members'].get('members'),list) and isinstance(heavy.get('members_heavy'),list)
                  and len(data['members']['members'])==len(heavy['members_heavy']))
            data['memberCount']=len(heavy['members_heavy'])
            del heavy
        elif snapshot.kind==DISPLAY_GRAPH_KIND:
            display=VerifiedDisplayInput(snapshot)
            module=_program(snapshot.source,'fec.surfaces.staffer_graph_snapshot','fec/surfaces/staffer_graph_snapshot.py')
            graph=module.StaticGraph(Path(profile)/'original-data-placeholder',display_input=display)
            graph.load();_data(not graph.errors)
            data={'graph':graph,'display':display}
        elif snapshot.kind=='melange.payroll-identity-core.v1':
            from melange_module_data import validate_payroll
            data={'loader':validate_payroll(snapshot)}
        elif snapshot.kind==INDUSTRY_PAGES_KIND:
            lease=extract_archive(snapshot,profile,'pages',is_cancelled=is_cancelled);resources.append(lease)
            data={'lease':lease,'pages':{name.removesuffix('.json'):lease.take_json(name) for name in lease.paths if name!='derivation.json'},
                  'derivation':lease.derivation}
        else:
            lease=extract_archive(snapshot,profile,'records',is_cancelled=is_cancelled);resources.append(lease)
            references=lease.take_json('identity/references.json')
            directory=lease.take_json('contacts/directory.json')
            _data(references.get('schemaVersion')==1 and references.get('kind')=='melange-analytical-references-v1'
                  and references.get('privateIdentityGroupsIncluded') is False
                  and set(references)=={'schemaVersion','kind','evidence','inventory','ldaEmployment','ldaSidecar','reconciliation','privateIdentityGroupsIncluded'}
                  and isinstance(references['inventory'],dict) and isinstance(references['evidence'],dict)
                  and directory.get('kind')=='melange-professional-contacts-v1' and isinstance(directory.get('records'),list))
            _data(references['inventory'].get('identity_groups') == []
                  and references['inventory'].get('identity_aliases') == {}
                  and references['evidence'].get('user_assertions') == [])
            receipts={family:lease.take_json(family+'/receipt.json') for family in ('source','lda','activity')}
            for family,receipt in receipts.items():
                _data(receipt.get('schema')=='melange-staffer-analytical-projection-v1'
                      and receipt.get('family')==family and receipt.get('status')=='PASS'
                      and isinstance(receipt.get('parent',{}).get('receipt'),dict))
            data={'lease':lease,'references':references,'directory':directory,'receipts':receipts,
                  'profileReceipt':lease.take_json('profiles/receipt.json'),
                  'profileCheckpoint':lease.take_json('profiles/checkpoint.json')}
            _data(data['profileReceipt'].get('kind')=='melange-factual-profiles-v1'
                  and data['profileReceipt'].get('status')=='PASS')
        content=MelangeComponentContent(snapshot,data,resources)
        return WorkspaceComponent(snapshot,source,profile,program_fingerprint,content,is_cancelled=is_cancelled)
    except Exception:
        for resource in resources:resource.close()
        raise


class _ReceiptPath:
    def __init__(self,path,document):self.actual,self.document=path,document
    def read_text(self,**_kwargs):return json.dumps(self.document,ensure_ascii=False,allow_nan=False)
    def is_file(self):return self.actual.is_file()
    def __str__(self):return str(self.actual)


class _InputPath:
    """One program-chosen database and its typed receipt view, no path walker."""
    def __init__(self,path,receipt_path,receipt):self.actual,self.receipt_path,self.receipt=Path(path),receipt_path,receipt
    def __fspath__(self):return str(self.actual)
    def __str__(self):return str(self.actual)
    def resolve(self,*_args,**_kwargs):return self
    def as_uri(self):return self.actual.as_uri()
    def stat(self):return self.actual.stat()
    def is_file(self):return self.actual.is_file()
    def open(self,mode='r',*args,**kwargs):
        require(not set(mode)&set('wa+'))
        return self.actual.open(mode,*args,**kwargs)
    @property
    def suffix(self):return self.actual.suffix
    @property
    def parent(self):return self.actual.parent
    def with_suffix(self,value):
        require(value in ('.receipt.json','.sqlite.receipt.json'))
        return _ReceiptPath(self.receipt_path,self.receipt)


def _constructor(function,instance,slot,*args,**kwargs):
    def fixed_path(value):
        require(value is slot)
        return slot
    scoped=types.FunctionType(function.__code__,{**function.__globals__,'Path':fixed_path},function.__name__,function.__defaults__,function.__closure__)
    scoped.__kwdefaults__=function.__kwdefaults__
    scoped(instance,slot,*args,**kwargs)
    return instance


class MelangeBinding:
    def __init__(self,server,prepared):
        self.server,self.prepared,self.service=server,prepared,server.dashboard
        self.components={kind:value['reader'] for kind,value in prepared.readers.items()}
        self._original_root=self.service.source_root
        self._profile=self.service.profiles
        self._original_profile_paths=(self._profile.raw_dir,self._profile.path)
        self._pages=None
        self._module=_program(prepared.roots['sourceRoot'],'fec.surfaces.staffer_live_service','fec/surfaces/staffer_live_service.py')
        require(type(self.service) is self._module.LiveService
                and Path(self._original_root).resolve()==Path(prepared.roots['originalDataRoot']).resolve())
        self.dashboard=self.components[DASHBOARD_KIND]
        self.industry=self.components[INDUSTRY_PAGES_KIND]
        self.analytics=self.components[STAFFER_ANALYSIS_KIND]
        self.graph=self.components[DISPLAY_GRAPH_KIND].content.data['graph']
        self.payroll=self.components['melange.payroll-identity-core.v1'].content.data['loader']
        expected_graph_root=self.service.static.root
        self.graph.root=expected_graph_root
        self.service.static=self.graph
        self.service._desktop_workspace_inputs=self
        self._install_readers()

    def _install_readers(self):
        refs=self.analytics.content.data['references']
        module=self._module
        def evidence(root,graph):
            require(Path(root).resolve()==Path(self._original_root).resolve())
            return deepcopy(refs['evidence'])
        def inventory(root,graph):
            require(Path(root).resolve()==Path(self._original_root).resolve())
            return self.public_inventory(graph)
        module.load_evidence,module.load_inventory=evidence,inventory
        module.SourceCatalog=lambda:self._catalogue('source')
        module.LdaCatalog=lambda:self._catalogue('lda')
        module.CATALOG=self._slot('source')
        module.LDA_CATALOG=self._slot('lda')
        def activity(database,nodes):
            actual=self.analytics.content.data['lease'].paths['activity/index.sqlite']
            require(Path(database).resolve()==actual.resolve())
            return self.activity_index(nodes)
        module.ActivityIndex=activity
        contact_module=_program(self.prepared.roots['sourceRoot'],'fec.surfaces.staffer_contacts','fec/surfaces/staffer_contacts.py')
        def contacts():
            result=contact_module.ContactIndex(records=deepcopy(self.analytics.content.data['directory']['records']))
            result.revision=self.analytics.content.data['directory'].get('parentSourceSha256')
            return result
        self.service.contacts=contacts();module.ContactIndex=contacts
        self.service.lda_employment=deepcopy(refs['ldaEmployment']);self.service._lda_employment_loaded=True
        self.service.lda_sidecar=deepcopy(refs['ldaSidecar']);self.service._lda_sidecar_loaded=True
        self.service.payroll_identity=self.payroll(self._original_root);self.service._payroll_identity_loaded=True
        self._bind_profiles()
        self._installed_functions={name:getattr(module,name) for name in
            ('load_evidence','load_inventory','SourceCatalog','LdaCatalog','ActivityIndex','ContactIndex')}

    def public_capabilities(self):
        _data(self.verify())
        return {'mode':'signed-public-read-only',
            'privateOverlay':{'status':'excluded_from_signed_workspace','loaded':False,'validated':False},
            'supported':{'publicModelRead':True,'peopleSearch':True,'groups':True,
                'datedEvidenceRoutes':True,'factualProfiles':True},
            'unavailable':{'privateIdentityDecisions':True,'privateRelationshipStatements':True,
                'newIdentityDiscovery':True},
            'workspaceManifestSha256':self.prepared.source['manifestSha256'],
            'notice':'Signed public model. Private decisions are not loaded; identity editing, relationship statements and new identity discovery are unavailable.'}

    def public_inventory(self,graph):
        _data(self.verify())
        inventory=self.analytics.content.data['references']['inventory']
        _data(inventory.get('identity_groups')==[] and inventory.get('identity_aliases')=={})
        result=deepcopy(inventory);result['raw_nodes']=dict(result['nodes'])
        # Apply only the signed public projection, without claiming to load or
        # validate private decisions and without reading their filesystem path.
        self._module.apply_identity_overlay(result,graph.nodes,identity_groups=inventory['identity_groups'])
        return result

    def public_identity_review(self):
        capabilities=self.public_capabilities()
        return {'status':'unavailable_in_signed_public_workspace',
            'candidate_groups':[],'records':{},'sources':[],'errors':[],
            'counts':{'candidate_groups':None,'user_confirmed_aliases':None,
                'status':'not_computed_private_decisions_excluded'},
            'capabilities':capabilities}

    def _slot(self,family):
        lease=self.analytics.content.data['lease'];receipt=deepcopy(self.analytics.content.data['receipts'][family])
        parent=receipt['parent']['receipt']
        receipt['projection_schema']=receipt['schema']
        if family=='activity':
            activity_module=_program(self.prepared.roots['sourceRoot'],'fec.surfaces.staffer_activity_index','fec/surfaces/staffer_activity_index.py')
            _data(parent.get('schema')==activity_module.SCHEMA)
            receipt['schema']=activity_module.SCHEMA
            receipt['source_receipt_sha256']=parent['source_receipt_sha256']
        else:receipt['scope']=parent['scope']
        return _InputPath(lease.paths[family+('/index.sqlite' if family=='activity' else '/catalog.sqlite')],
                          lease.paths[family+'/receipt.json'],receipt)

    def _catalogue(self,family):
        source_module=_program(self.prepared.roots['sourceRoot'],'fec.surfaces.staffer_source_catalog','fec/surfaces/staffer_source_catalog.py')
        if family=='lda':
            lda_module=_program(self.prepared.roots['sourceRoot'],'fec.surfaces.staffer_lda_catalog','fec/surfaces/staffer_lda_catalog.py')
            instance=lda_module.LdaCatalog.__new__(lda_module.LdaCatalog)
        else:instance=source_module.SourceCatalog.__new__(source_module.SourceCatalog)
        return _constructor(source_module.SourceCatalog.__init__,instance,self._slot(family))

    def activity_index(self,nodes):
        module=_program(self.prepared.roots['sourceRoot'],'fec.surfaces.staffer_activity_index','fec/surfaces/staffer_activity_index.py')
        instance=module.ActivityIndex.__new__(module.ActivityIndex)
        return _constructor(module.ActivityIndex.__init__,instance,self._slot('activity'),nodes,
                            reconciliation_release=deepcopy(self.analytics.content.data['references']['reconciliation']))

    def _bind_profiles(self):
        profile=self._profile;lease=self.analytics.content.data['lease']
        receipt=self.analytics.content.data['profileReceipt']
        _data(receipt.get('schemaVersion')==1 and type(receipt.get('records')) is int
              and isinstance(receipt.get('profiles'),dict))
        rows=[];row_digests=[];contracts={};offset=0;line_ends=[]
        try:
            receipt_sha=hashlib.sha256(lease.paths['profiles/receipt.json'].read_bytes()).hexdigest()
            with lease.paths['profiles/records.ndjson'].open('rb') as stream:
                for line in stream:
                    row=parse(line);uuid=row.get('profile_uuid')
                    _data(isinstance(uuid,str) and uuid in receipt['profiles'])
                    spec=receipt['profiles'][uuid];raw_sha=hashlib.sha256(line).hexdigest()
                    _data(spec['byteStart']==offset and spec['byteEnd']==offset+len(line)
                          and spec['projectedRawRowSha256']==raw_sha)
                    content=profile.content_digest(row);_data(content==spec['projectedContentSha256'])
                    offset+=len(line);rows.append(row);line_ends.append(offset)
                    row_digests.append({'profile_content_sha256':content,'profile_raw_line_sha256':raw_sha})
                    contracts[uuid]={'profile_uuid':uuid,'profile_content_sha256':content,'profile_row_sha256':content,
                        'raw_line_sha256':raw_sha,'byte_start':spec['byteStart'],'byte_end':spec['byteEnd'],
                        'source_path':str(lease.paths['profiles/records.ndjson']),'path':str(lease.paths['profiles/records.ndjson']),
                        'verification_receipt':str(lease.paths['profiles/receipt.json']),
                        'receipt_sha256':receipt_sha,
                        'sha256':content,'sha256_scope':'CANONICAL_PUBLISHED_FACTUAL_PROFILE_CONTENT',
                        'parent_profile_content_sha256':spec.get('parentContentSha256'),
                        'collection_integrity':'PARENT_COLLECTION_VERIFIED_PUBLISHED_FACTUAL_PROJECTION',
                        'canonical_identity_promoted':False,'prefix_binding':'SHA256_BYTE_PREFIX'}
        except OSError:raise DataIntakeBlocked('storage') from None
        _data(len(rows)==receipt['records'] and len(contracts)==len(rows) and offset==receipt['bytes'])
        checkpoint=dict(self.analytics.content.data['profileCheckpoint']['checkpoint'])
        checkpoint['queue_total']=len(rows)
        parent=receipt['parent']['receipt']
        view={**parent,'schema':'melange-factual-profiles-v1','counts':{**parent.get('counts',{}),'profiles':len(rows),'unique_profiles':len(rows)}}
        profile.rows=profile.accepted=rows;profile.row_digests=row_digests;profile.profile_contracts=contracts
        profile.profile_digests={key:value['profile_content_sha256'] for key,value in contracts.items()}
        profile.eligible_profile_digests={row['profile_uuid']:profile.profile_digests[row['profile_uuid']] for row in rows if profile.eligible(row)}
        profile.profile_revision=hashlib.sha256(json.dumps(profile.profile_digests,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        profile.profile_changes={'added':[],'changed':[],'removed':[],'unchanged_count':len(rows)}
        profile.state=checkpoint;profile.receipt=profile.accepted_receipt=view
        profile.accepted_receipt_digest=receipt_sha
        profile.accepted_prefix_sha256=receipt['sha256'];profile.verified_byte_binding=('published-factual',receipt['sha256'])
        profile.line_end_offsets=line_ends
        profile.errors=[];profile.partial_line=False;profile.exceptions=sum(not profile.eligible(row) for row in rows)
        profile.raw_updated_at=parent.get('generated_at');profile.generation=1
        def refresh(actual):
            require(actual is profile)
            self.analytics.verify()
            return actual.summary()
        profile.refresh=types.MethodType(refresh,profile)
        profile._desktop_input_path=lease.paths['profiles/records.ndjson']

    def verify(self):
        return getattr(self.server,'dashboard',None) is self.service and self.service.source_root is self._original_root \
            and self.service.static is self.graph and self.service.profiles is self._profile \
            and self._profile.raw_dir is self._original_profile_paths[0] and self._profile.path is self._original_profile_paths[1] \
            and getattr(self.service,'_desktop_workspace_inputs',None) is self \
            and all(getattr(self._module,name,None) is function for name,function in self._installed_functions.items()) \
            and all(component.verify() for component in self.components.values())

    def _render(self):
        if self._pages is None:
            from module_workspace_render import render_pages
            main={key:value for key,value in self.dashboard.content.data.items() if key!='memberCount'}
            self._pages=render_pages(main,self.industry.content.data['pages'],provenance=self._provenance(),
                                     derivation=self.industry.content.data['derivation'])
        return self._pages

    def _provenance(self):
        role_specs={role:{key:spec[key] for key in ('sha256','bytes')} for role,spec in self.dashboard.snapshot.objects.items()}
        role_specs['industry-pages']={key:self.industry.snapshot.objects['pages'][key] for key in ('sha256','bytes')}
        return {'schemaVersion':1,'appId':'melange','contractId':'melange.workspace.v1',
                'sourceDigest':self.prepared.source['manifestSha256'],'releaseTag':self.prepared.source['releaseTag'],'roles':role_specs}

    def _clean_workspace(self):
        if getattr(self,'_clean',None) is None:
            from module_workspace_clean_ui import CleanWorkspace
            main={key:value for key,value in self.dashboard.content.data.items() if key!='memberCount'}
            self._clean=CleanWorkspace(main,self._render(),self.industry.content.data['pages'],
                self._provenance(),self.industry.content.data['derivation'],
                lambda:self.dashboard.snapshot.json('member-profiles'))
        return self._clean

    def handle_request(self,handler):
        _data(self.verify())
        url=urlsplit(handler.path);path=unquote(url.path)
        if path in ('/api/staffer-capabilities','/api/staffer-assertions'):
            capability=self.public_capabilities()
            value=(capability if path=='/api/staffer-capabilities' else
                {'code':'private_overlay_unavailable','assertions':None,
                 'error':capability['notice'],'workspace_capabilities':capability})
            raw=json.dumps(value,separators=(',',':')).encode('utf-8')
            handler.send_response(200 if path=='/api/staffer-capabilities' else 409)
            handler.send_header('Content-Type','application/json; charset=utf-8')
            handler.send_header('Content-Length',str(len(raw)));handler.send_header('Cache-Control','no-store')
            handler.send_header('X-Content-Type-Options','nosniff');handler.end_headers();handler.wfile.write(raw);return True
        if path=='/' or path.startswith('/staffer-live/approved/'):
            status,raw,content_type=self._clean_workspace().response(path)
            handler.send_response(status);handler.send_header('Content-Type',content_type)
            handler.send_header('Content-Length',str(len(raw)));handler.send_header('Cache-Control','no-store')
            handler.send_header('X-Content-Type-Options','nosniff');handler.send_header('Referrer-Policy','no-referrer');handler.end_headers()
            handler.wfile.write(raw);return True
        aliases={'/Moneyball Dashboard.html':None,'/cu-member-desk.html':'m','/staffer-network.html':'s',
                 '/Moneyball.html':'legacy'}
        if path in aliases:
            field=aliases[path]
            try:query=parse_qs(url.query,keep_blank_values=True,max_num_fields=4)
            except ValueError:handler.send_error(400);return True
            selected=('m','v','s') if field=='legacy' else (field,) if field else ()
            if any(len(query.get(key,[]))>1 or any(len(value)>256 for value in query.get(key,[])) for key in selected):
                handler.send_error(400);return True
            selector=query.get(field,[''])[0] if field and field!='legacy' else ''
            values=({key:query[key][0] for key in selected if key in query} if field=='legacy'
                    else {'view':'people',**({'s':selector} if selector else {})} if field=='s'
                    else {'view':'profile','m':selector} if field=='m' and selector
                    else {'view':'members'} if field=='m' else {'view':'influence'})
            location='/'+('?' + urlencode(values) if values else '')
            handler.send_response(302);handler.send_header('Location',location)
            handler.send_header('Cache-Control','no-store');handler.send_header('Content-Length','0');handler.end_headers();return True
        if path=='/__desktop/workspace/member-profiles.json':
            if handler.headers.get('X-Melange-Workspace')!=self.prepared.source['manifestSha256']:
                handler.send_error(409,'The workspace changed; reload the app.');return True
            source=self.dashboard.snapshot.files['member-profiles']
            spec=self.dashboard.snapshot.objects['member-profiles']
            handler.send_response(200);handler.send_header('Content-Type','application/json; charset=utf-8')
            handler.send_header('Content-Length',str(spec['bytes']));handler.send_header('Cache-Control','no-store')
            handler.send_header('X-Content-Type-Options','nosniff');handler.send_header('X-Melange-Role-Sha256',spec['sha256']);handler.end_headers()
            with source.open('rb') as stream:
                for block in iter(lambda:stream.read(256*1024),b''):handler.wfile.write(block)
            self.dashboard.verify();return True
        name='Moneyball.html' if path=='/' else path.removeprefix('/')
        allowed={'Moneyball.html','lobby-network.html','lobby-champions.html','lobby-forecast.html','lobby-bills.html','lobby-screen.html','lobby-interactions.html'}
        if name not in allowed:return False
        raw=self._render()[name].encode('utf-8')
        handler.send_response(200);handler.send_header('Content-Type','text/html; charset=utf-8')
        handler.send_header('Content-Length',str(len(raw)));handler.send_header('Cache-Control','no-store')
        handler.send_header('X-Content-Type-Options','nosniff');handler.send_header('Referrer-Policy','no-referrer');handler.end_headers()
        handler.wfile.write(raw);return True


def bind(server,prepared):return MelangeBinding(server,prepared)
