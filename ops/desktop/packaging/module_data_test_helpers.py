"""Synthetic-only fixtures for the immutable module reader boundary."""
import gzip
import hashlib
import json
from pathlib import Path
from module_data_snapshot import KINDS
from melange_module_data import GRAPH_FILES, UPSTREAM, GENERATION, VERIFICATION, PAYROLL_SOURCES, PAYROLL_EVIDENCE

SOURCE=Path(__file__).resolve().parents[3]
def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()

class Fixture:
    def __init__(self,directory,kind,source=SOURCE):
        self.root=Path(directory).resolve()/'snapshot';self.root.mkdir()
        self.kind,self.app,self.roles=kind,*KINDS[kind]
        self.request={'appId':self.app,'kind':kind,'sourceRoot':str(Path(source).resolve()),'snapshotRoot':str(self.root),'files':{},'objects':[]}
        for role,(relative,_) in self.roles.items():
            path=self.root/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'fixture')
            self.request['files'][role]=str(path)
        self.refresh()
    def path(self,role):return Path(self.request['files'][role])
    def write(self,role,value,compress=False):
        raw=value if isinstance(value,bytes) else encoded(value)
        self.path(role).write_bytes(gzip.compress(raw,mtime=0) if compress else raw)
        self.refresh()
    def refresh(self):
        self.request['objects']=[]
        for role,path in self.request['files'].items():
            raw=Path(path).read_bytes();digest=sha(raw)
            self.request['objects'].append({'role':role,'bytes':len(raw),'sha256':digest,'segments':[{'asset':role+'.bin','bytes':len(raw),'sha256':digest}]})
    def spec(self,role):return next(item for item in self.request['objects'] if item['role']==role)

def graph_fixture(directory):
    f=Fixture(directory,'melange.staffer-graph-core.v1')
    for _name,(role,_leaf) in GRAPH_FILES.items():f.write(role,b'',True)
    f.write('node-scores',b'{"node_id":"person:fixture1","node_kind":"person"}\n{"node_id":"person:fixture2","node_kind":"person"}\n',True)
    f.write('edges',encoded({'subject_id':'person:fixture1','object_id':'person:fixture2','layer':'co_tenure','status':'GUARANTEED','w_tiered_lower':0.5,'edge_id':'fixture-edge'})+b'\n',True)
    for _name,(role,_tail) in UPSTREAM.items():f.write(role,b'',True)
    receipt={'schema_id':'staffer-network-social-receipt-v1','status':'PASS','canonical_employment_promotions':0,'canonical_identity_promotions':0,
        'files':[{'role':name,'path':leaf,'sha256':f.spec(role)['sha256'],'bytes':f.spec(role)['bytes']} for name,(role,leaf) in GRAPH_FILES.items()],
        'inputs':[{'role':name,'path':'/never-read-original/'+tail,'sha256':f.spec(role)['sha256'],'bytes':f.spec(role)['bytes']} for name,(role,tail) in UPSTREAM.items()],
        'dials':{'s_strength':{}},'edge_counts':{'membership':0,'policy_area_membership':0,'revolving':0,'revolving_in_operator':0}}
    f.write('graph-receipt',receipt)
    f.write('graph-verification',{'schema_id':'staffer-network-social-verification-receipt-v1','status':'PASS','failures':[],
        'twin_byte_identity':[{'path':'staffer_social_network_receipt.json','identical':True,'primary_sha256':f.spec('graph-receipt')['sha256'],'twin_sha256':f.spec('graph-receipt')['sha256']}]})
    return f

def payroll_fixture(directory):
    f=Fixture(directory,'melange.payroll-identity-core.v1')
    for role in PAYROLL_SOURCES:f.write(role,{'fixture':role})
    bundle={'version':'payroll-identity-rows-v1','sources':[{'path':'/never-read-original/'+relative,'sha256':f.spec(role)['sha256']} for role,relative in PAYROLL_SOURCES.items()],
        'episodes':[],'record_pairs':[],'counts':{'episodes':0}}
    f.write('evidence',bundle,True)
    f.write('config',{'path':PAYROLL_EVIDENCE,'sha256':f.spec('evidence')['sha256']})
    return f

def repin_payroll(f,bundle):
    f.write('evidence',bundle,True)
    f.write('config',{'path':PAYROLL_EVIDENCE,'sha256':f.spec('evidence')['sha256']})
