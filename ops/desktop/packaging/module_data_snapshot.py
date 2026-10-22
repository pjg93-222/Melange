"""Read-only, compiled module-data boundary. No activation or profile writes."""
from contextlib import contextmanager
import gzip
import hashlib
import importlib.util
import io
import json
import math
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import types
import uuid

MiB, GiB = 1024 ** 2, 1024 ** 3
GRAPH = {'graph-receipt': ('graph/receipt.json', MiB), 'graph-verification': ('graph/verification.json', MiB),
 'edges': ('graph/edges.bin', GiB), 'node-scores': ('graph/node-scores.bin',128*MiB), 'trajectories': ('graph/trajectories.bin',128*MiB),
 'office-moves': ('graph/office-moves.bin',32*MiB), 'membership': ('graph/membership.bin',128*MiB), 'revolving': ('graph/revolving.bin',32*MiB),
 'policy': ('graph/policy.bin',32*MiB), 'groups': ('graph/groups.bin',32*MiB), 'review': ('graph/review.bin',128*MiB), 'spine': ('graph/spine.bin',128*MiB), 'office-index': ('graph/office-index.bin',32*MiB)}
PAYROLL = {'config': ('payroll/config.json',65536), 'evidence': ('payroll/evidence.bin',128*MiB), 'spine-receipt': ('payroll/spine-receipt.json',MiB),
 'hill-spans': ('payroll/hill-spans.bin',256*MiB), 'house-observations': ('payroll/house-observations.bin',512*MiB), 'senate-employment': ('payroll/senate-employment.bin',128*MiB), 'senate-committee': ('payroll/senate-committee.bin',128*MiB)}
FORECAST = {'selection':('models/selection.json',4096), 'giving-pointer':('models/giving-models-current.json',4096), 'pac-pointer':('models/pac-giving-current.json',4096),
 'giving-model':('models/giving-model.json',16*MiB), 'pac-model':('models/pac-model.json',16*MiB), 'anchors':('anchors/snapshot.json',16*MiB), 'anchor-receipt':('anchors/receipt.json',MiB),
 **{'workbook-'+name:('reports/'+name+'.xlsx',512*MiB) for name in ('commercial-banks','credit-unions','property-casualty','telecom','community-banks')}}
PUBLIC_PAYROLL = {'observations': ('public-data/observations.ndjson', 8*GiB),
                  'receipt': ('public-data/receipt.json', MiB)}
PUBLIC_FEC = {f'mentat.fec.{table}.{cycle}': (f'fec/{cycle}/{table}.psv', 160*MiB)
              for cycle in ('2022', '2024', '2026') for table in ('cm', 'cn', 'ccl', 'pas2')}
PUBLIC_FEC['mentat.fec.provenance'] = ('fec/provenance.json', 65536)
KINDS = {'melange.staffer-graph-core.v1':('melange',GRAPH), 'melange.payroll-identity-core.v1':('melange',PAYROLL),
         'mentat.aggregate-forecast-core.v1':('mentat',FORECAST),
         'melange.official-payroll-observations.v1':('melange',PUBLIC_PAYROLL),
         'mentat.public-fec-tables.v1':('mentat',PUBLIC_FEC)}
KIND_TOTAL_LIMITS = {'mentat.public-fec-tables.v1': 512*MiB}

def require(value, message='Module data snapshot was rejected'):
    if not value: raise ValueError(message)

def exact(value, fields):
    require(isinstance(value,dict) and set(value)==set(fields))

def pairs(items):
    out={}
    for key,value in items:
        require(key not in out and key not in ('__proto__','constructor','prototype'))
        out[key]=value
    return out

def parse(raw):
    if isinstance(raw,bytes):raw=raw.decode('utf-8',errors='strict')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:require(False))
    def bound(item,depth=0):
        require(depth<=48)
        if isinstance(item,dict):
            for child in item.values():bound(child,depth+1)
        elif isinstance(item,list):
            for child in item:bound(child,depth+1)
        elif isinstance(item,float):require(math.isfinite(item))
    bound(value)
    return value

def regular(path, directory=False):
    info=path.lstat()
    require(not path.is_symlink() and not getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT)
    require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
    return info

def safe_root(value):
    require(isinstance(value,str) and Path(value).is_absolute())
    original=Path(value)
    for item in (original,*original.parents):regular(item,True)
    return original.resolve(strict=True)

def digest(path):
    before=regular(path); h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*MiB),b''):h.update(block)
    after=regular(path)
    require((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino))
    return h.hexdigest()

class Snapshot:
    def __init__(self,request):
        exact(request,('appId','kind','sourceRoot','snapshotRoot','files','objects'))
        require(request['kind'] in KINDS)
        app,self.roles=KINDS[request['kind']]
        require(request['appId']==app)
        self.app,self.kind=app,request['kind']
        self.root,self.source=safe_root(request['snapshotRoot']),safe_root(request['sourceRoot'])
        require(self.root!=self.source and not self.root.is_relative_to(self.source) and not self.source.is_relative_to(self.root))
        exact(request['files'],self.roles)
        objects=request['objects']; require(isinstance(objects,list) and len(objects)==len(self.roles))
        self.objects={}
        for item in objects:
            exact(item,('role','bytes','sha256','segments'))
            role=item['role'];require(role in self.roles and role not in self.objects and type(item['bytes']) is int and 0<item['bytes']<=self.roles[role][1])
            require(isinstance(item['sha256'],str) and len(item['sha256'])==64 and all(c in '0123456789abcdef' for c in item['sha256']))
            segments=item['segments'];require(isinstance(segments,list) and 0<len(segments)<=32)
            for part in segments:
                exact(part,('asset','bytes','sha256'));require(isinstance(part['asset'],str) and type(part['bytes']) is int and 0<part['bytes']<=GiB and isinstance(part['sha256'],str) and len(part['sha256'])==64 and all(c in '0123456789abcdef' for c in part['sha256']))
            require(sum(part['bytes'] for part in segments)==item['bytes'])
            self.objects[role]=item
        require(sum(item['bytes'] for item in self.objects.values()) <= KIND_TOTAL_LIMITS.get(
            self.kind, sum(limit for _path, limit in self.roles.values())))
        self.files={}
        for role,(relative,_limit) in self.roles.items():
            path=self.root.joinpath(*relative.split('/'))
            require(isinstance(request['files'][role],str) and os.path.normcase(os.path.abspath(request['files'][role]))==os.path.normcase(str(path)))
            for parent in path.parents:
                if parent==self.root:break
                regular(parent,True)
            info=regular(path); require(info.st_size==self.objects[role]['bytes'] and digest(path)==self.objects[role]['sha256'])
            self.files[role]=path
    def json(self,role):
        return parse(self.files[role].read_bytes())
    def matches(self,role,spec):
        require(isinstance(spec,dict) and spec.get('sha256')==self.objects[role]['sha256'])
        if 'bytes' in spec:require(type(spec['bytes']) is int and spec['bytes']==self.objects[role]['bytes'])
    def source_file(self,relative):
        path=self.source.joinpath(*relative.split('/'))
        for parent in path.parents:
            if parent==self.source:break
            regular(parent,True)
        regular(path);require(path.resolve().is_relative_to(self.source))
        return path

def load_source(path):
    # Trusted native-derived source only. Never import executable data from cache.
    name='_module_snapshot_'+uuid.uuid4().hex
    module=types.ModuleType(name);module.__file__=str(path);sys.modules[name]=module
    previous=sys.dont_write_bytecode;sys.dont_write_bytecode=True
    try:exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
    finally:sys.dont_write_bytecode=previous
    return module

class ReadAliases:
    """A closed virtual layout: metadata paths can never become filesystem I/O."""
    def __init__(self,mapping,root_label):
        self.mapping={key.replace('\\','/').strip('/'):Path(value) for key,value in mapping.items()}
        self.root_label=str(root_label)
        self.extra={}
    def alias(self,name,key):self.extra[str(name).replace('\\','/')]=key
    def path(self,value=''):
        if isinstance(value,AliasPath):return value
        name=str(value).replace('\\','/')
        if name==self.root_label.replace('\\','/'):name=''
        elif name in self.extra:name=self.extra[name]
        elif name in {str(path).replace('\\','/') for path in self.mapping.values()}:
            name=next(key for key,path in self.mapping.items() if str(path).replace('\\','/')==name)
        require(not Path(name).is_absolute() and ':' not in name and '..' not in name.split('/'))
        return AliasPath(self,name.strip('/'))

class AliasPath:
    def __init__(self,aliases,key):self.aliases,self.key=aliases,key
    def __truediv__(self,value):
        value=str(value).replace('\\','/')
        if value in self.aliases.extra:return self.aliases.path(self.aliases.extra[value])
        require(not value.startswith('/') and ':' not in value and '..' not in value.split('/'))
        return self.aliases.path('/'.join(filter(None,(self.key,value))))
    @property
    def name(self):return PurePosixPath(self.key).name
    @property
    def parent(self):return self.aliases.path(self.key.rsplit('/',1)[0] if '/' in self.key else '')
    def __str__(self):return self.key
    def __eq__(self,other):return isinstance(other,AliasPath) and self.aliases is other.aliases and self.key==other.key
    def __fspath__(self):require(self.key in self.aliases.mapping);return str(self.aliases.mapping[self.key])
    def exists(self):return self.is_file() or self.is_dir()
    def is_file(self):return self.key in self.aliases.mapping
    def is_dir(self):return any(key.startswith(self.key+'/' if self.key else '') for key in self.aliases.mapping)
    def resolve(self,strict=False):require(not strict or self.exists());return self
    def is_relative_to(self,other):return self.key==other.key or self.key.startswith(other.key+'/')
    def stat(self):return Path(self.__fspath__()).stat()
    def open(self,mode='r',*args,**kwargs):require(mode in ('r','rb','rt'));return Path(self.__fspath__()).open(mode,*args,**kwargs)
    def read_bytes(self):return Path(self.__fspath__()).read_bytes()
    def read_text(self,*args,**kwargs):return Path(self.__fspath__()).read_text(*args,**kwargs)
    def glob(self,pattern):
        import fnmatch
        children={key[len(self.key)+1:].split('/')[0] for key in self.aliases.mapping if key.startswith(self.key+'/')}
        return (self/name for name in sorted(children) if fnmatch.fnmatchcase(name,pattern))

class LimitedGzip:
    def __init__(self,path,max_bytes):self.stream=gzip.open(path,'rb');self.left=max_bytes
    def read(self,size=-1):
        data=self.stream.read(min(self.left+1,size if size>=0 else self.left+1));self.left-=len(data);require(self.left>=0,'Compressed module data exceeds its limit');return data
    def close(self):self.stream.close()
    def __enter__(self):return self
    def __exit__(self,*args):self.close()

def validate_snapshot(request):
    snapshot=Snapshot(request)
    if snapshot.kind in ('melange.official-payroll-observations.v1', 'mentat.public-fec-tables.v1'):
        from module_public_input_installers import validate_public_snapshot
        validate_public_snapshot(snapshot)
    elif snapshot.app=='melange':
        from melange_module_data import validate
        validate(snapshot)
    else:
        from mentat_module_data import validate
        validate(snapshot)
    # Rehash after reader/schema validation: caller may only commit an unchanged snapshot.
    for role,path in snapshot.files.items():require(digest(path)==snapshot.objects[role]['sha256'])
    return {'schemaVersion':1,'validated':True,'appId':snapshot.app,'kind':snapshot.kind,'coverage':{'completeKind':True,'fullApplication':False}}

def main():
    sys.dont_write_bytecode=True
    try:
        raw=sys.stdin.buffer.read(2*MiB+1);require(len(raw)<=2*MiB)
        result=validate_snapshot(parse(raw))
    except Exception:
        print(json.dumps({'schemaVersion':1,'validated':False,'error':'Module data snapshot was rejected'}));return 1
    print(json.dumps(result,separators=(',',':')));return 0

if __name__=='__main__':raise SystemExit(main())
