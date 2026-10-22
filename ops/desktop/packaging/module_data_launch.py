"""Read-only launch bridge for native-verified, incomplete module-data cores.

The parent must authorize the original owner, hold its native prepared/health
lease, run validateModuleBinding, and pass the descriptor only through its
dedicated ephemeral launch boundary. ``native_verified=True`` is a caller trust
assertion, never a field accepted from downloaded JSON. This module cannot prove
owner approval, journal high-water, or Ed25519 authenticity on its own. An
optional trusted verifier callback may additionally verify the signature. No
network, activation, persistent configuration, or filesystem writes occur here.
"""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import uuid

from module_data_snapshot import KINDS, Snapshot, exact, parse, regular, require, safe_root

MiB, GiB = 1024 ** 2, 1024 ** 3
MAX_TOTAL, MAX_SEGMENTS, MAX_MANIFEST = 32 * GiB, 256, 2 * MiB
SOURCE_FIELDS = ('schemaVersion','appId','repository','catalogSequence','releaseTag','releaseCommit','pointerDigest','manifestSha256','cacheRoot')
APPS = {'melange': ('pjg93-222/melange','melange-public-module-data'),
        'mentat': ('pjg93-222/mentat','mentat-public-module-data')}
HASH = re.compile(r'[a-f0-9]{64}\Z')
COMMIT = re.compile(r'[a-f0-9]{40}\Z')
TAG = re.compile(r'module-data-\d{4}-\d{2}-\d{2}(?:-[a-z0-9][a-z0-9.-]{0,40})?\Z')


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def integer(value, maximum=2**53-1):
    return type(value) is int and 0 <= value <= maximum


def digest(value):
    return isinstance(value,str) and HASH.fullmatch(value) is not None


def asset(value):
    return (isinstance(value,str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,150}',value)
            and not value.endswith('.') and not re.match(r'(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)',value))


def identifier(value):
    try:
        return isinstance(value,str) and str(uuid.UUID(value)) == value and uuid.UUID(value).int != 0
    except (ValueError,AttributeError):
        return False


def contains(root, target):
    return target == root or target.is_relative_to(root)


def overlap(left, right):
    left,right=left.resolve(),right.resolve()
    return contains(left,right) or contains(right,left)


def stamp(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)


def opened_identity(info):
    # Windows Python may expose creation time through lstat.st_ctime_ns but a
    # different time through fstat. Compare identity across APIs, retaining full
    # timestamp stability independently for the named path and opened handle.
    return (info.st_dev,info.st_ino,info.st_mode,info.st_nlink,info.st_size,info.st_mtime_ns)


class ReadView:
    def __init__(self, base, root):
        self.base,self.root=base,root
        self.directories,self.files={},{}

    def directory(self, path):
        require(contains(self.base,path))
        current=self.base
        for part in (None,*path.relative_to(self.base).parts):
            if part is not None:current=current/part
            info=regular(current,True)
            require(contains(self.base,current.resolve(strict=True)))
            before=self.directories.get(current)
            if before is not None:
                require(stamp(before)==stamp(info) if contains(self.root,current)
                        else (before.st_dev,before.st_ino,before.st_mode)==(info.st_dev,info.st_ino,info.st_mode))
            self.directories[current]=info

    def read(self, path, limit, *, expected_bytes=None, expected_sha=None, retain=False):
        require(contains(self.root,path) and path!=self.root)
        self.directory(path.parent)
        before=regular(path);require(before.st_nlink==1 and before.st_size<=limit)
        flags=os.O_RDONLY|getattr(os,'O_BINARY',0)|getattr(os,'O_NOFOLLOW',0)
        descriptor=os.open(path,flags)
        with os.fdopen(descriptor,'rb') as stream:
            opened=os.fstat(stream.fileno());named=regular(path)
            require(stat.S_ISREG(opened.st_mode) and opened.st_nlink==1
                    and opened_identity(before)==opened_identity(opened)==opened_identity(named) and stamp(before)==stamp(named))
            require(contains(self.root,path.resolve(strict=True)))
            if expected_bytes is not None:require(opened.st_size==expected_bytes)
            h=hashlib.sha256();parts=[];received=0
            for block in iter(lambda:stream.read(4*MiB),b''):
                received+=len(block);require(received<=opened.st_size);h.update(block)
                if retain:parts.append(block)
            after=os.fstat(stream.fileno());current=regular(path)
            require(current.st_nlink==1 and stamp(opened)==stamp(after) and stamp(named)==stamp(current)
                    and opened_identity(after)==opened_identity(current) and received==opened.st_size)
        if expected_sha is not None:require(h.hexdigest()==expected_sha)
        prior=self.files.get(path);require(prior is None or stamp(prior)==stamp(current));self.files[path]=current
        return b''.join(parts) if retain else h.hexdigest()

    def unchanged(self):
        for path,before in self.directories.items():
            after=regular(path,True);require(contains(self.base,path.resolve(strict=True)))
            require(stamp(before)==stamp(after) if contains(self.root,path)
                    else (before.st_dev,before.st_ino,before.st_mode)==(after.st_dev,after.st_ino,after.st_mode))
        for path,before in self.files.items():
            after=regular(path);require(after.st_nlink==1 and stamp(before)==stamp(after))

    def closure(self, root, files, directories):
        files,directories=set(files),set(directories)
        def walk(folder):
            self.directory(folder)
            for child in folder.iterdir():
                relative=child.relative_to(root).as_posix()
                info=child.lstat()
                require(not child.is_symlink() and not getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT)
                if stat.S_ISDIR(info.st_mode):
                    require(relative in directories);directories.remove(relative);walk(child)
                else:require(stat.S_ISREG(info.st_mode) and relative in files);files.remove(relative)
        walk(root);require(not files and not directories)


def decode(value, size=None):
    require(isinstance(value,str))
    raw=base64.b64decode(value,validate=True)
    require(base64.b64encode(raw).decode('ascii')==value and (size is None or len(raw)==size))
    return raw


def pointer_metadata(app_id, envelope, source, verify_signature):
    exact(envelope,('schemaVersion','keyId','payload','signature'))
    require(type(envelope['schemaVersion']) is int and envelope['schemaVersion']==1 and isinstance(envelope['keyId'],str)
            and 0<len(envelope['keyId'])<=256 and isinstance(envelope['payload'],str) and len(envelope['payload'])<16384)
    raw,signature=decode(envelope['payload']),decode(envelope['signature'],64)
    require(hashlib.sha256(raw).hexdigest()==source['pointerDigest'])
    if verify_signature is not None:
        require(callable(verify_signature) and verify_signature(envelope['keyId'],raw,signature) is True)
    value=parse(raw)
    exact(value,('schemaVersion','purpose','appId','repository','catalogSequence','releaseTag','releaseCommit','manifest'))
    repository,purpose=APPS[app_id]
    require(canonical(value)==raw and type(value['schemaVersion']) is int and value['schemaVersion']==1 and value['purpose']==purpose
            and value['appId']==app_id and value['repository']==repository
            and integer(value['catalogSequence']) and value['catalogSequence']>0
            and isinstance(value['releaseTag'],str) and TAG.fullmatch(value['releaseTag'])
            and isinstance(value['releaseCommit'],str) and COMMIT.fullmatch(value['releaseCommit']) and value['releaseCommit']!='0'*40)
    spec=value['manifest'];exact(spec,('asset','bytes','sha256'))
    require(spec['asset']=='manifest.json' and integer(spec['bytes'],MAX_MANIFEST) and spec['bytes']>0 and digest(spec['sha256']))
    for field in ('appId','repository','catalogSequence','releaseTag','releaseCommit'):
        require(source[field]==value[field])
    require(source['manifestSha256']==spec['sha256'])
    return value


def manifest_metadata(app_id, value, pointer, required_kinds):
    exact(value,('schemaVersion','purpose','appId','repository','releaseTag','datasets'))
    repository,purpose=APPS[app_id]
    require(type(value['schemaVersion']) is int and value['schemaVersion']==1 and value['purpose']==purpose+'sets' and value['appId']==app_id
            and value['repository']==repository and value['releaseTag']==pointer['releaseTag']
            and isinstance(value['datasets'],list) and 0<len(value['datasets'])<=32)
    ids,revisions,kinds,assets=set(),set(),set(),set();total,segments=0,0
    for dataset in value['datasets']:
        exact(dataset,('datasetId','revisionId','kind','adapterVersion','objects','counts'))
        require(identifier(dataset['datasetId']) and identifier(dataset['revisionId'])
                and dataset['datasetId'] not in ids and dataset['revisionId'] not in revisions
                and isinstance(dataset['kind'],str) and dataset['kind'] in KINDS and KINDS[dataset['kind']][0]==app_id and dataset['kind'] not in kinds
                and type(dataset['adapterVersion']) is int and dataset['adapterVersion']==1)
        ids.add(dataset['datasetId']);revisions.add(dataset['revisionId']);kinds.add(dataset['kind'])
        roles=KINDS[dataset['kind']][1];objects=dataset['objects'];exact(dataset['counts'],('files',))
        require(isinstance(objects,list) and len(objects)==len(roles) and type(dataset['counts']['files']) is int
                and dataset['counts']['files']==len(roles))
        seen=set();dataset_bytes=0
        for item in objects:
            exact(item,('role','bytes','sha256','segments'))
            require(isinstance(item['role'],str) and item['role'] in roles and item['role'] not in seen
                    and integer(item['bytes'],roles[item['role']][1]) and item['bytes']>0 and digest(item['sha256'])
                    and isinstance(item['segments'],list) and 0<len(item['segments'])<=32)
            seen.add(item['role']);raw=0
            for part in item['segments']:
                exact(part,('asset','bytes','sha256'));name=part['asset']
                require(asset(name) and name.lower() not in assets and integer(part['bytes'],GiB) and part['bytes']>0 and digest(part['sha256']))
                assets.add(name.lower());raw+=part['bytes'];segments+=1
            require(raw==item['bytes']);dataset_bytes+=item['bytes']
        require(dataset_bytes<=sum(limit for _path,limit in roles.values()));total+=dataset_bytes
    require(set(required_kinds)<=kinds and total<=MAX_TOTAL and segments<=MAX_SEGMENTS)
    return value['datasets']


def prepare_module_readers(*, app_id, profile, source_root, original_data_root, state_root, source,
                           native_verified=False, verify_signature=None, required_kinds=None, protected_roots=()):
    """Return scoped readers; caller installs them before server imports.

    Neither downloaded JSON nor a standalone CLI can establish native_verified.
    Original data/state/connection and global runtime_paths remain unchanged.
    """
    require(native_verified is True and app_id in APPS,'Native verified module launch context is required')
    require(verify_signature is None or callable(verify_signature))
    original_source=copy.deepcopy(source);exact(original_source,SOURCE_FIELDS)
    repository,_purpose=APPS[app_id]
    require(type(source['schemaVersion']) is int and source['schemaVersion']==1 and source['appId']==app_id
            and source['repository']==repository and integer(source['catalogSequence']) and source['catalogSequence']>0
            and digest(source['pointerDigest']) and digest(source['manifestSha256']))
    profile_root=safe_root(profile);code=safe_root(source_root);data=safe_root(original_data_root);state=safe_root(state_root)
    require(isinstance(source['cacheRoot'],str) and Path(source['cacheRoot']).is_absolute())
    choices=[(profile_root,profile_root/'packs/github-module-data')]
    if os.environ.get('LOCALAPPDATA'):choices.append((Path(os.environ['LOCALAPPDATA']).absolute(),Path(os.environ['LOCALAPPDATA']).absolute()/'MelangeData'/app_id/'github-module-data'))
    chosen=next(((base,root) for base,root in choices if os.path.normcase(os.path.abspath(source['cacheRoot']))==os.path.normcase(str(root))),None)
    require(chosen is not None,'Unapproved native module cache root')
    base,cache=chosen;safe_root(str(base))
    require(isinstance(protected_roots,(list,tuple)) and all(isinstance(root,str) for root in protected_roots))
    for protected in (code,data,state,profile_root/'state',*(Path(root) for root in protected_roots)):
        require(protected.is_absolute() and not overlap(cache,protected),'Module cache overlaps original or protected state')
    compiled=[kind for kind,(app,_roles) in KINDS.items() if app==app_id]
    required=compiled if required_kinds is None else required_kinds
    require(isinstance(required,(list,tuple)) and 0<len(required)<=32 and all(isinstance(kind,str) for kind in required) and len(set(required))==len(required) and all(kind in compiled for kind in required))
    require(sum(sum(limit for _path,limit in KINDS[kind][1].values()) for kind in compiled)<=MAX_TOTAL)
    view=ReadView(base,cache);view.directory(cache)
    envelope=parse(view.read(cache/'pointers'/(source['pointerDigest']+'.json'),32768,retain=True))
    pointer=pointer_metadata(app_id,envelope,source,verify_signature)
    raw=view.read(cache/'manifests'/(source['manifestSha256']+'.json'),MAX_MANIFEST,
                  expected_bytes=pointer['manifest']['bytes'],expected_sha=source['manifestSha256'],retain=True)
    datasets=manifest_metadata(app_id,parse(raw),pointer,required)
    snapshot_root=cache/'snapshots'/source['manifestSha256'];view.directory(snapshot_root)
    requests=[];entries=[];expected_files=set();expected_directories=set()
    for dataset in datasets:
        root=snapshot_root/dataset['datasetId'];view.directory(root);roles=KINDS[dataset['kind']][1];files={}
        for item in dataset['objects']:
            relative=dataset['datasetId']+'/'+roles[item['role']][0];file=snapshot_root/relative
            view.read(file,item['bytes'],expected_bytes=item['bytes'],expected_sha=item['sha256']);files[item['role']]=str(file);expected_files.add(relative)
            parent=Path(relative).parent
            while parent!=Path('.'):expected_directories.add(parent.as_posix());parent=parent.parent
        request={'appId':app_id,'kind':dataset['kind'],'sourceRoot':str(code),'snapshotRoot':str(root),'files':files,'objects':copy.deepcopy(dataset['objects'])}
        Snapshot(request);requests.append(request)
        entries.append({'kind':dataset['kind'],'datasetId':dataset['datasetId'],'revisionId':dataset['revisionId'],'root':str(root),'files':files,'objects':copy.deepcopy(dataset['objects'])})
    view.closure(snapshot_root,expected_files,expected_directories)
    previous_bytecode=sys.dont_write_bytecode
    sys.dont_write_bytecode=True
    try:
        if app_id=='melange':
            from melange_module_data import configure_readers
        else:
            from mentat_module_data import configure_readers
    finally:
        sys.dont_write_bytecode=previous_bytecode
    readers={}
    for request in requests:
        bound=configure_readers(copy.deepcopy(request))
        require(isinstance(bound,dict) and bound.get('appId')==app_id and bound.get('kind')==request['kind']
                and bound.get('coverage')=={'completeKind':True,'fullApplication':False})
        readers[request['kind']]=bound
    # Reader imports/probes are awaited work at the native boundary. Reject any
    # role replacement even if the domain reader returned a successful object.
    for entry in entries:
        for item in entry['objects']:view.read(Path(entry['files'][item['role']]),item['bytes'],expected_bytes=item['bytes'],expected_sha=item['sha256'])
    view.closure(snapshot_root,expected_files,expected_directories);view.unchanged()
    require(source==original_source,'Native module source changed during reader configuration')
    return {'schemaVersion':1,'appId':app_id,'source':copy.deepcopy(source),'snapshotRoot':str(snapshot_root),
            'datasets':entries,'readers':readers,'coverage':{'completeKind':True,'fullApplication':False},
            'signatureVerification':'python-callback' if verify_signature is not None else 'native-js'}


if __name__=='__main__':
    raise SystemExit('Native verified module launch context is required; standalone execution cannot authorize module data.')
